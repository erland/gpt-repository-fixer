from __future__ import annotations

import fnmatch
import re
from pathlib import PurePosixPath

HIGH_CONFIDENCE_FILES = {".DS_Store", "Thumbs.db", ".coverage"}
HIGH_CONFIDENCE_DIRS = {
    "node_modules", ".pytest_cache", "__pycache__", ".mypy_cache", ".ruff_cache",
    "coverage", "htmlcov", ".gradle",
}
TEMP_SUFFIXES = {".log", ".tmp", ".temp", ".swp", ".swo", ".pyc", ".pyo"}
HISTORICAL_RE = re.compile(
    r"(^|[-_.])(old|backup|bak|previous|copy|final2|final-final)([-_.]|$)",
    re.IGNORECASE,
)
LOCK_FILES = {"package-lock.json": "npm", "pnpm-lock.yaml": "pnpm", "yarn.lock": "yarn"}


def _norm(path: str) -> str:
    p = path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def _evidence(kind: str, path: str | None, observation: str, related_paths: list[str] | None = None) -> dict:
    item = {"kind": kind, "path": path, "observation": observation}
    if related_paths:
        item["related_paths"] = related_paths
    return item


def _finding(
    fid: str,
    classification: str,
    title: str,
    summary: str,
    evidence: list[dict],
    recommended_action: str | None,
    *,
    confidence: str = "high",
    decision_required: bool = False,
    decision_reason: str | None = None,
    verification: str | None = None,
    notes: list[str] | None = None,
) -> dict:
    return {
        "id": fid,
        "area": "repository-hygiene",
        "classification": classification,
        "title": title,
        "summary": summary,
        "evidence": evidence,
        "confidence": confidence,
        "recommended_action": recommended_action,
        "decision_required": decision_required,
        "decision_reason": decision_reason,
        "verification": verification,
        "notes": notes or [],
    }


def _parse_gitignore(text: str) -> list[str]:
    rules = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        rules.append(line.lstrip("/"))
    return rules


def _ignored(path: str, rules: list[str]) -> bool:
    p = _norm(path)
    parts = p.split("/")
    for raw in rules:
        rule = raw.rstrip("/")
        if not rule:
            continue
        if fnmatch.fnmatch(p, rule) or fnmatch.fnmatch(PurePosixPath(p).name, rule):
            return True
        if "/" not in rule and rule in parts:
            return True
        if p == rule or p.startswith(rule + "/"):
            return True
    return False


def _referenced(path: str, files: dict[str, str]) -> bool:
    """Conservative text-reference check for ambiguous files."""
    name = PurePosixPath(path).name
    for other, text in files.items():
        if other == path or other.startswith(".git/"):
            continue
        # Avoid treating binary-ish/huge payloads as text evidence in this deterministic helper.
        if not isinstance(text, str) or len(text) > 1_000_000:
            continue
        if path in text or (name and name in text):
            return True
    return False


def _is_high_confidence_artifact(path: str) -> bool:
    p = PurePosixPath(path)
    if p.name in HIGH_CONFIDENCE_FILES or p.suffix.lower() in TEMP_SUFFIXES:
        return True
    if any(part in HIGH_CONFIDENCE_DIRS for part in p.parts):
        return True
    # Maven target is strong only when nested as a directory segment.
    if "target" in p.parts:
        return True
    return False


def _historical_candidate(path: str) -> bool:
    p = PurePosixPath(path)
    lower = p.name.lower()
    if p.suffix.lower() in {".patch", ".diff", ".zip"}:
        return True
    return bool(HISTORICAL_RE.search(p.stem)) or lower.endswith("~")


def analyze_repository_hygiene(files: dict[str, str]) -> list[dict]:
    """Return conservative repository-hygiene findings for a path->text snapshot."""
    normalized = {_norm(k): v for k, v in files.items() if not _norm(k).startswith(".git/")}
    user_files = {k: v for k, v in normalized.items() if not k.startswith(".repository-fixer/")}
    gitignore_text = user_files.get(".gitignore", "")
    ignore_rules = _parse_gitignore(gitignore_text)
    findings: list[dict] = []
    counter = 1

    def add(**kwargs):
        nonlocal counter
        kwargs["fid"] = f"RF-HYGIENE-{counter:03d}"
        findings.append(_finding(**kwargs))
        counter += 1

    # Multiple lock files in the same directory are ambiguous and require an explicit choice.
    by_dir: dict[str, list[str]] = {}
    for path in user_files:
        name = PurePosixPath(path).name
        if name in LOCK_FILES:
            parent = str(PurePosixPath(path).parent)
            by_dir.setdefault(parent, []).append(path)
    for parent, paths in sorted(by_dir.items()):
        if len(paths) > 1:
            managers = [LOCK_FILES[PurePosixPath(p).name] for p in sorted(paths)]
            add(
                classification="recommended",
                title="Flera package-manager-lockfiler i samma projektrot",
                summary=f"{parent or '.'} innehåller lockfiler för {', '.join(managers)}.",
                evidence=[_evidence("cross-file", sorted(paths)[0], "Flera olika package-manager-lockfiler hittades i samma katalog.", sorted(paths)[1:])],
                recommended_action="Bekräfta avsedd package manager och behåll endast den lockfil som hör till den verifierade byggkedjan.",
                decision_required=True,
                decision_reason="Repository Fixer får inte välja package manager eller radera en konkurrerande lockfil på gissning.",
                verification="Verifiera att build, CI och dokumentation använder samma package manager och att endast avsedd lockfil återstår.",
            )

    # High-confidence local/generated artifacts.
    artifacts = sorted(p for p in user_files if _is_high_confidence_artifact(p))
    for path in artifacts:
        ignored = _ignored(path, ignore_rules)
        notes = []
        if ignored:
            notes.append("Filen matchar redan .gitignore men finns ändå i den analyserade repository-snapshoten; kontrollera om den är versionshanterad eller bara följde med ZIP-inputen.")
        add(
            classification="recommended",
            title="Sannolikt genererad eller lokal artefakt",
            summary=f"{path} ser ut som en genererad, cache-, logg- eller lokal systemfil som normalt inte hör hemma i källrepositoryt.",
            evidence=[_evidence("file", path, "Sökvägen matchar en hög-confidence-regel för genererade/lokala artefakter.")],
            recommended_action="Ta bort artefakten från den versionshanterade källan om den inte är avsiktlig och säkerställ relevant .gitignore-regel.",
            verification="Kontrollera att filen inte längre ingår i repositoryt och att den kan återskapas av verktyget vid behov.",
            notes=notes,
        )

    # Ambiguous historical/archive/work files require explicit decision before deletion.
    ambiguous = sorted(p for p in user_files if _historical_candidate(p) and not _is_high_confidence_artifact(p))
    for path in ambiguous:
        is_ref = _referenced(path, user_files)
        add(
            classification="consider",
            title="Filnamn tyder på historisk eller temporär arbetsfil",
            summary=f"{path} ser ut som en backup, äldre kopia, patch/diff eller arkiverad arbetsfil, men syftet kan inte avgöras säkert från namnet.",
            evidence=[_evidence("file", path, "Filnamn eller filtyp matchar en konservativ heuristik för historiska/tillfälliga arbetsfiler.")],
            recommended_action="Granska filens syfte och ta endast bort den efter användarens bekräftelse.",
            confidence="medium",
            decision_required=True,
            decision_reason="En historiskt namngiven eller arkiverad fil kan vara avsiktlig dokumentation eller återställningsmaterial och får inte raderas automatiskt.",
            verification="Bekräfta att filen saknar nödvändig funktion och att inga relevanta referenser bryts efter eventuell borttagning.",
            notes=["Filen verkar refereras av annat textinnehåll i repositoryt och kräver extra granskning."] if is_ref else [],
        )

    # Missing/insufficient .gitignore only when evidence shows a concrete need.
    uncovered = [p for p in artifacts if not _ignored(p, ignore_rules)]
    if uncovered:
        if ".gitignore" not in user_files:
            obs = ".gitignore saknas trots observerade genererade/lokala artefakter."
            evidence = [_evidence("absence", ".gitignore", obs, uncovered[:10])]
        else:
            obs = "Observerade genererade/lokala artefakter täcks inte av nuvarande .gitignore-regler."
            evidence = [_evidence("configuration", ".gitignore", obs, uncovered[:10])]
        add(
            classification="recommended",
            title=".gitignore täcker inte observerade artefakter",
            summary=f"{len(uncovered)} observerade artefakt(er) saknar matchande ignore-regel.",
            evidence=evidence,
            recommended_action="Lägg till minsta relevanta ignore-regler för de verifierade verktygen/artefakterna; undvik en generell mall som inte motsvarar projektet.",
            verification="Kontrollera att de observerade artefakterna matchas av .gitignore utan att avsedda källfiler ignoreras.",
        )

    if not findings:
        findings.append(_finding(
            "RF-HYGIENE-001",
            "passed",
            "Repository hygiene utan tydliga problem",
            "Inga tydliga genererade skräpfiler, historiska arbetsfiler eller package-manager-lockkonflikter hittades i den analyserade snapshoten.",
            [_evidence("runtime", None, "Repository hygiene-kontrollerna kördes utan relevanta fynd.")],
            None,
            verification="Ingen hygiene-åtgärd behövs utifrån de verifierade kontrollerna.",
        ))

    return findings
