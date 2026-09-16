from __future__ import annotations

from collections import defaultdict
from pathlib import Path

CLASS_ORDER = {"must-fix": 0, "recommended": 1, "consider": 2}
WORKSTREAM_ORDER = {
    "build-test": 0,
    "github-actions": 1,
    "documentation": 2,
    "license": 3,
    "repository-hygiene": 4,
    "other": 5,
}
MAX_FINDINGS_PER_STEP = 4


def _workstream(area: str) -> str:
    if area in {"build", "tests", "versions"}:
        return "build-test"
    if area in {"readme", "documentation"}:
        return "documentation"
    if area == "github-actions":
        return "github-actions"
    if area == "license":
        return "license"
    if area == "repository-hygiene":
        return "repository-hygiene"
    return "other"


WORKSTREAM_META = {
    "build-test": (
        "Korrigera build, tester och runtime",
        "Gör projektets build-, test- och versionskonfiguration konsekvent med verifierade repositoryfakta.",
        "Build/test-fel påverkar verifierbarheten och bör stabiliseras före CI som bygger på samma kommandon.",
    ),
    "github-actions": (
        "Korrigera GitHub Actions",
        "Se till att CI bygger och testar relevanta komponenter med repositoryts faktiska kommandon och runtime.",
        "CI ska återspegla projektets verifierade build- och testflöde.",
    ),
    "documentation": (
        "Synkronisera dokumentationen",
        "Uppdatera README och övrig Markdown så att den stämmer med repositoryts faktiska implementation och konfiguration.",
        "Felaktig eller saknad dokumentation gör projektet svårare att använda och underhålla.",
    ),
    "license": (
        "Hantera licensinformationen",
        "Gör licensfil och dokumentation konsekventa utan att fatta licensbeslut åt användaren.",
        "Licensinformation ska vara konsekvent och juridiska eller ägarspecifika val måste bekräftas av användaren.",
    ),
    "repository-hygiene": (
        "Städa repositoryt försiktigt",
        "Åtgärda verifierade hygieneproblem utan att radera osäkra eller avsiktliga filer automatiskt.",
        "Genererade eller oavsiktliga filer skapar brus, men tveksamma filer kräver försiktighet.",
    ),
    "other": (
        "Åtgärda övriga repositoryproblem",
        "Åtgärda återstående verifierade problem som inte hör naturligt till ett annat arbetsområde.",
        "Dessa fynd behöver hanteras men ska inte blandas in i orelaterade förändringar.",
    ),
}


def _unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _likely_files(findings: list[dict]) -> list[str]:
    files: list[str] = []
    for finding in findings:
        for evidence in finding.get("evidence") or []:
            if evidence.get("path"):
                files.append(evidence["path"])
            files.extend(evidence.get("related_paths") or [])
    return _unique(files)


def _planned_changes(findings: list[dict]) -> list[str]:
    changes = []
    for finding in findings:
        action = finding.get("recommended_action")
        changes.append(action or f"Åtgärda {finding['id']}: {finding['title']} utan att utöka ändringens omfattning.")
    return _unique(changes)


def _decisions(findings: list[dict]) -> list[dict]:
    return [
        {"finding_id": f["id"], "question": f.get("decision_reason") or "Användarbeslut krävs innan ändringen kan genomföras."}
        for f in findings if f.get("decision_required")
    ]


def _verification(findings: list[dict], workstream: str) -> list[str]:
    checks = [f["verification"] for f in findings if f.get("verification")]
    if not checks:
        defaults = {
            "documentation": "Jämför ändrad dokumentation med aktuell implementation och konfiguration.",
            "build-test": "Kör relevanta build- och testkommandon när miljön tillåter och redovisa annars not-verified.",
            "github-actions": "Validera workflow-syntax och kontrollera att relevanta build-/teststeg täcks.",
            "license": "Kontrollera att LICENSE och licensreferenser är konsekventa efter användarens beslut.",
            "repository-hygiene": "Kontrollera diffen och att borttagna filer inte längre refereras.",
            "other": "Verifiera att respektive fynds evidens inte längre visar problemet.",
        }
        checks = [defaults[workstream]]
    return _unique(checks)


def _risk(findings: list[dict], workstream: str) -> str:
    if any(f.get("decision_required") for f in findings):
        return "medium"
    if workstream in {"build-test", "github-actions", "license", "repository-hygiene"}:
        return "medium"
    return "low"


def build_fix_plan_model(repository_name: str, findings: list[dict], notes: list[str] | None = None) -> dict:
    open_findings = [f for f in findings if f.get("classification") in CLASS_ORDER]
    open_findings.sort(key=lambda f: (CLASS_ORDER[f["classification"]], WORKSTREAM_ORDER[_workstream(f["area"])], f["id"]))

    grouped: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for finding in open_findings:
        grouped[(CLASS_ORDER[finding["classification"]], _workstream(finding["area"]))].append(finding)

    raw_steps: list[tuple[int, str, list[dict]]] = []
    for (priority, workstream), items in sorted(grouped.items(), key=lambda x: (x[0][0], WORKSTREAM_ORDER[x[0][1]])):
        for start in range(0, len(items), MAX_FINDINGS_PER_STEP):
            raw_steps.append((priority, workstream, items[start:start + MAX_FINDINGS_PER_STEP]))

    steps = []
    last_build_step = None
    for index, (_, workstream, items) in enumerate(raw_steps, start=1):
        step_id = f"STEP-{index:02d}"
        title, goal, why = WORKSTREAM_META[workstream]
        if len([s for s in raw_steps if s[1] == workstream]) > 1:
            title += f" – del {1 + sum(1 for _, ws, _ in raw_steps[:index-1] if ws == workstream)}"
        dependencies: list[str] = []
        if workstream == "github-actions" and last_build_step:
            dependencies.append(last_build_step)
        step = {
            "id": step_id,
            "title": title,
            "goal": goal,
            "why": why,
            "finding_ids": [f["id"] for f in items],
            "likely_files": _likely_files(items),
            "planned_changes": _planned_changes(items),
            "decisions": _decisions(items),
            "verification": _verification(items, workstream),
            "risk": _risk(items, workstream),
            "dependencies": dependencies,
            "status": "planned",
        }
        steps.append(step)
        if workstream == "build-test":
            last_build_step = step_id

    return {
        "repository_name": repository_name,
        "source_finding_ids": [f["id"] for f in open_findings],
        "steps": steps,
        "notes": notes or [],
    }


def _render_step(step: dict) -> str:
    files = "\n".join(f"- `{p}`" for p in step["likely_files"]) or "- Inga exakta filer kan ännu fastställas; begränsa ändringen till evidensen för fynden."
    changes = "\n".join(f"- {x}" for x in step["planned_changes"])
    verification = "\n".join(f"- {x}" for x in step["verification"])
    deps = ", ".join(f"`{x}`" for x in step["dependencies"]) or "Inga"
    if step["decisions"]:
        decisions = "\n".join(f"- **{d['finding_id']}**: {d['question']}" for d in step["decisions"])
    else:
        decisions = "- Inga uttryckliga användarbeslut krävs före steget."
    return "\n".join([
        f"### {step['id']} – {step['title']}",
        "",
        f"**Status:** {step['status']}  ",
        f"**Risk:** {step['risk']}  ",
        f"**Beroenden:** {deps}",
        "",
        f"**Mål:** {step['goal']}",
        "",
        f"**Varför:** {step['why']}",
        "",
        f"**Fynd som åtgärdas:** {', '.join(step['finding_ids'])}",
        "",
        "**Sannolikt berörda filer**",
        "",
        files,
        "",
        "**Planerade ändringar**",
        "",
        changes,
        "",
        "**Användarbeslut**",
        "",
        decisions,
        "",
        "**Verifiering efter steget**",
        "",
        verification,
    ])


def render_fix_plan(model: dict, template_text: str | None = None) -> str:
    count = len(model["steps"])
    finding_count = len(model["source_finding_ids"])
    if count:
        summary = f"Planen omfattar **{finding_count} öppna fynd** fördelade på **{count} genomförbara steg**. Alla steg startar som `planned`."
        steps = "\n\n".join(_render_step(step) for step in model["steps"])
        next_step = f"Börja med `{model['steps'][0]['id']}` efter att användaren har fått en kort översikt och valt att genomföra steget."
    else:
        summary = "Analysen innehåller inga öppna fynd som kräver en åtgärdsplan."
        steps = "Inga åtgärdssteg behövs utifrån nuvarande analys."
        next_step = "Erbjud slutverifiering eller avslut; gör inga repositoryändringar utan ett nytt verifierat fynd."
    notes = "\n".join(f"- {n}" for n in model.get("notes") or []) or "- Inga särskilda noter."
    template = template_text or Path(__file__).resolve().parents[2].joinpath("templates/repository-fix-plan.md.tpl").read_text(encoding="utf-8")
    replacements = {
        "REPOSITORY_NAME": model["repository_name"],
        "SUMMARY": summary,
        "STEPS": steps,
        "NOTES": notes,
        "NEXT_STEP": next_step,
    }
    for key, value in replacements.items():
        template = template.replace("{{" + key + "}}", value)
    return template.rstrip() + "\n"
