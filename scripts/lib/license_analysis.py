from __future__ import annotations

import re
from pathlib import PurePosixPath

LICENSE_NAMES = {
    "license", "license.txt", "license.md", "licence", "licence.txt", "licence.md", "copying", "copying.txt"
}

LICENSE_SIGNATURES = [
    ("MIT", [r"permission is hereby granted, free of charge", r"the software is provided [\"“]?as is"]),
    ("Apache-2.0", [r"apache license", r"version 2\.0", r"http://www\.apache\.org/licenses/license-2\.0"]),
    ("GPL-3.0", [r"gnu general public license", r"version 3"]),
    ("GPL-2.0", [r"gnu general public license", r"version 2"]),
    ("BSD-3-Clause", [r"redistribution and use in source and binary forms", r"neither the name of"]),
    ("BSD-2-Clause", [r"redistribution and use in source and binary forms", r"this software is provided by the copyright holders"]),
    ("MPL-2.0", [r"mozilla public license", r"version 2\.0"]),
    ("Unlicense", [r"this is free and unencumbered software released into the public domain"]),
]

README_LICENSE_ALIASES = {
    "MIT": [r"\bMIT(?: License)?\b"],
    "Apache-2.0": [r"\bApache(?: License)?(?:,? Version)?\s*2(?:\.0)?\b", r"\bApache-2\.0\b"],
    "GPL-3.0": [r"\bGPL(?:v|[- ]?)3(?:\.0)?\b", r"\bGNU GPL(?:v|[- ]?)3\b"],
    "GPL-2.0": [r"\bGPL(?:v|[- ]?)2(?:\.0)?\b", r"\bGNU GPL(?:v|[- ]?)2\b"],
    "BSD-3-Clause": [r"\bBSD[- ]3[- ]Clause\b", r"\b3-Clause BSD\b"],
    "BSD-2-Clause": [r"\bBSD[- ]2[- ]Clause\b", r"\b2-Clause BSD\b"],
    "MPL-2.0": [r"\bMPL[- ]?2(?:\.0)?\b", r"\bMozilla Public License(?: Version)? 2(?:\.0)?\b"],
    "Unlicense": [r"\bUnlicense\b"],
}

PLACEHOLDER_PATTERNS = [
    r"<\s*year\s*>", r"\[\s*year\s*\]", r"yyyy", r"<\s*copyright holders?\s*>",
    r"\[\s*fullname\s*\]", r"<\s*fullname\s*>", r"your name", r"copyright holder",
]


def _evidence(kind: str, path: str | None, observation: str, related_paths: list[str] | None = None) -> dict:
    item = {"kind": kind, "observation": observation}
    if path:
        item["path"] = path
    if related_paths:
        item["related_paths"] = related_paths
    return item


def _finding(fid: str, classification: str, title: str, summary: str, evidence: list[dict], action: str | None,
             confidence: str = "high", verification: str | None = None,
             decision_required: bool = False, decision_reason: str | None = None, notes: list[str] | None = None) -> dict:
    return {
        "id": fid,
        "area": "license",
        "classification": classification,
        "title": title,
        "summary": summary,
        "evidence": evidence,
        "confidence": confidence,
        "recommended_action": action,
        "decision_required": decision_required,
        "decision_reason": decision_reason,
        "verification": verification,
        "notes": notes or [],
    }


def _license_files(files: dict[str, str]) -> list[tuple[str, str]]:
    found = []
    for path, text in files.items():
        p = PurePosixPath(path)
        if len(p.parts) == 1 and p.name.lower() in LICENSE_NAMES:
            found.append((path, text))
    return sorted(found)


def _readmes(files: dict[str, str]) -> list[tuple[str, str]]:
    found = []
    for path, text in files.items():
        p = PurePosixPath(path)
        if p.name.lower() in {"readme.md", "readme.markdown"}:
            found.append((path, text))
    return sorted(found, key=lambda x: (len(PurePosixPath(x[0]).parts), x[0]))


def identify_license(text: str) -> str | None:
    low = text.lower()
    for license_id, patterns in LICENSE_SIGNATURES:
        matches = sum(1 for pattern in patterns if re.search(pattern, low, re.I))
        required = 2 if len(patterns) > 1 else 1
        if matches >= required:
            return license_id
    # SPDX-only license files are uncommon but valid in tiny repos.
    spdx = re.search(r"SPDX-License-Identifier:\s*([A-Za-z0-9.+-]+)", text, re.I)
    return spdx.group(1) if spdx else None


def declared_readme_licenses(files: dict[str, str]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for path, text in _readmes(files):
        # Limit declarations to license-ish context to avoid dependency references.
        chunks = []
        for match in re.finditer(r"(?im)^#{1,6}\s*(licen[cs]e|licens)\b.*$", text):
            chunks.append(text[match.start(): match.start() + 900])
        if not chunks:
            for line in text.splitlines():
                if re.search(r"(?i)\b(licen[cs]e|licensierad|licensed)\b", line):
                    chunks.append(line)
        context = "\n".join(chunks)
        for license_id, patterns in README_LICENSE_ALIASES.items():
            if any(re.search(pattern, context, re.I) for pattern in patterns):
                result.append((license_id, path))
    # stable unique
    seen = set()
    out = []
    for item in result:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _placeholders(text: str) -> list[str]:
    found = []
    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, text, re.I):
            found.append(pattern)
    return found


def analyze_license(files: dict[str, str]) -> list[dict]:
    """Analyze top-level license status without choosing a license for the user."""
    findings: list[dict] = []
    license_files = _license_files(files)
    declarations = declared_readme_licenses(files)
    declared_ids = {x[0] for x in declarations}

    if not license_files:
        if declared_ids:
            decl_paths = sorted({x[1] for x in declarations})
            named = ", ".join(sorted(declared_ids))
            findings.append(_finding(
                "RF-LICENSE-001", "must-fix", "Dokumenterad licens saknar licensfil",
                f"README anger {named}, men repositoryt saknar en toppnivåfil för LICENSE/LICENCE.",
                [_evidence("cross-file", decl_paths[0], f"Dokumentationen anger {named}, men ingen licensfil hittades.", decl_paths[1:])],
                "Lägg till den licensfil som användaren bekräftar, eller korrigera README om licensangivelsen är fel.",
                verification="Kontrollera att README och licensfil anger samma licens.",
                decision_required=True,
                decision_reason="Repository Fixer får inte själv välja eller anta vilken licens projektägaren avser att använda.",
            ))
        else:
            findings.append(_finding(
                "RF-LICENSE-001", "consider", "Ingen licensfil hittades",
                "Repositoryt saknar en toppnivåfil för LICENSE/LICENCE och dokumentationen anger ingen identifierbar licens.",
                [_evidence("absence", None, "Ingen toppnivåfil med standardnamn för licens hittades och README gav ingen tydlig licensdeklaration.")],
                "Om projektet ska licensieras för återanvändning: välj licens och metadata tillsammans med användaren innan någon fil skapas.",
                confidence="high",
                verification="Efter ett användarbeslut: kontrollera att licensfil och README är konsekventa.",
                decision_required=True,
                decision_reason="Om och hur projektet ska licensieras är ett juridiskt/verksamhetsmässigt val som användaren måste fatta.",
                notes=["Avsaknad av licens är inte i sig bevis på att repositoryt är felkonfigurerat; projektets avsikt är okänd."],
            ))
        return findings

    # Multiple top-level license files are ambiguous unless they clearly identify the same license.
    identified = [(identify_license(text), path, text) for path, text in license_files]
    known_ids = {license_id for license_id, _, _ in identified if license_id}
    if len(license_files) > 1 and len(known_ids) > 1:
        findings.append(_finding(
            "RF-LICENSE-001", "must-fix", "Flera motstridiga licensfiler",
            f"Repositoryt innehåller flera toppnivålicensfiler som identifieras som {', '.join(sorted(known_ids))}.",
            [_evidence("cross-file", license_files[0][0], "Flera licensfiler identifierades med olika licenstyper.", [p for p, _ in license_files[1:]])],
            "Fastställ med användaren vilken licenssituation som är avsedd innan någon licensfil ändras eller tas bort.",
            decision_required=True,
            decision_reason="Repository Fixer får inte avgöra vilken av motstridiga licenser som ska gälla.",
            verification="Verifiera den beslutade licensstrukturen och dokumentationen.",
        ))
        return findings

    primary_id, primary_path, primary_text = identified[0]

    if primary_id and declared_ids and primary_id not in declared_ids:
        findings.append(_finding(
            "RF-LICENSE-001", "must-fix", "README och LICENSE anger olika licens",
            f"Licensfilen identifieras som {primary_id}, medan README anger {', '.join(sorted(declared_ids))}.",
            [_evidence("cross-file", primary_path, f"Licensfilen identifieras som {primary_id} men dokumentationen anger en annan licens.", sorted({p for _, p in declarations}))],
            "Korrigera inkonsistensen efter att användaren bekräftat vilken licens som faktiskt ska gälla.",
            decision_required=True,
            decision_reason="Att välja vilken av två motstridiga licensangivelser som ska gälla kräver användarens beslut.",
            verification="Kontrollera att LICENSE och README anger samma licens.",
        ))

    placeholders = _placeholders(primary_text)
    if placeholders:
        findings.append(_finding(
            f"RF-LICENSE-{len(findings)+1:03d}", "recommended", "Licensfilen innehåller placeholders",
            "Licensfilen ser ut att innehålla malltext för årtal eller copyright-innehavare som inte har fyllts i.",
            [_evidence("file", primary_path, "Placeholder-liknande text hittades i licensfilens metadata.")],
            "Bekräfta copyright-innehavare och relevant årtal med användaren innan placeholders ersätts.",
            decision_required=True,
            decision_reason="Repository Fixer ska inte hitta på copyright-innehavare eller årtal.",
            verification="Kontrollera att den slutliga licensfilen inte innehåller kvarvarande mallfält.",
        ))

    if primary_id is None:
        findings.append(_finding(
            f"RF-LICENSE-{len(findings)+1:03d}", "consider", "Licenstyp kunde inte identifieras säkert",
            "En licensfil finns, men den matchar inte någon av Repository Fixers konservativa standardidentifierare.",
            [_evidence("file", primary_path, "Licensfil finns men licenstypen kunde inte identifieras deterministiskt.")],
            "Granska licenstexten manuellt och be användaren bekräfta licenstyp innan den ändras.",
            confidence="medium",
            decision_required=True,
            decision_reason="Okänd eller anpassad licenstext får inte klassificeras eller ersättas på gissning.",
            verification="Bekräfta licenstypen mot en auktoritativ licenstext eller projektägarens beslut.",
        ))

    if not findings:
        findings.append(_finding(
            "RF-LICENSE-001", "passed", "Licensinformationen är konsekvent",
            f"Repositoryt har en identifierbar {primary_id}-licens och ingen motstridig README-angivelse eller uppenbar placeholder hittades.",
            [_evidence("file", primary_path, f"Licensfilen identifierades som {primary_id} och kontrollerades mot README-angivelser.")],
            None,
            verification="Ingen licensändring behövs utifrån de verifierade kontrollerna.",
        ))

    return findings


def license_decision_prompt(finding: dict) -> dict:
    """Return a structured decision request; never select a license automatically."""
    if not finding.get("decision_required"):
        raise ValueError("finding does not require a user decision")
    return {
        "decision_type": "license",
        "finding_id": finding["id"],
        "required": True,
        "questions": [
            {
                "id": "license_type",
                "label": "Vilken licens ska projektet använda?",
                "required": True,
                "guidance": "Ange en licens som MIT, Apache-2.0 eller annan avsedd licens. Repository Fixer väljer inte åt dig.",
            },
            {
                "id": "copyright_holder",
                "label": "Vem ska anges som copyright-innehavare om licenstexten kräver det?",
                "required": False,
                "guidance": "Använd det namn eller den organisation som faktiskt ska stå i licensfilen.",
            },
            {
                "id": "copyright_year",
                "label": "Vilket årtal eller årintervall ska anges om licenstexten kräver det?",
                "required": False,
                "guidance": "Bekräfta årtal i stället för att låta Repository Fixer gissa.",
            },
        ],
    }
