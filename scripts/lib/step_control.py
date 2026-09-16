from __future__ import annotations

from copy import deepcopy

TERMINAL = {"completed", "skipped"}
ACTIVE = {"planned", "in-progress", "blocked"}


def _event(progress: dict, action: str, step_id: str | None = None, note: str | None = None) -> None:
    event = {"sequence": len(progress["history"]) + 1, "action": action}
    if step_id:
        event["step_id"] = step_id
    if note:
        event["note"] = note
    progress["history"].append(event)


def initialize_progress(plan: dict) -> dict:
    steps = []
    for source in plan.get("steps", []):
        decisions = [
            {
                "finding_id": d["finding_id"],
                "question": d["question"],
                "status": "pending",
            }
            for d in source.get("decisions", [])
        ]
        steps.append({
            "id": source["id"],
            "status": "planned",
            "skip_reason": None,
            "blockers": [],
            "overrides": [],
            "decisions": decisions,
            "verification_status": "pending",
        })
    progress = {
        "repository_name": plan["repository_name"],
        "source_finding_ids": list(plan.get("source_finding_ids", [])),
        "steps": steps,
        "history": [],
    }
    _event(progress, "initialized", note="Interaktiv åtgärdsprogress skapad från aktuell fix-plan.")
    _sync_blockers(plan, progress)
    return progress


def _plan_index(plan: dict) -> dict[str, dict]:
    return {step["id"]: step for step in plan.get("steps", [])}


def _progress_index(progress: dict) -> dict[str, dict]:
    return {step["id"]: step for step in progress.get("steps", [])}


def _sync_blockers(plan: dict, progress: dict) -> None:
    source = _plan_index(plan)
    states = _progress_index(progress)
    for step in progress.get("steps", []):
        if step["status"] in TERMINAL or step["status"] == "in-progress":
            continue
        preserved = [b for b in step.get("blockers", []) if b.get("type") in {"execution", "verification"}]
        computed = list(preserved)
        plan_step = source[step["id"]]
        for dependency in plan_step.get("dependencies", []):
            dependency_state = states.get(dependency)
            if not dependency_state or dependency_state.get("status") != "completed":
                computed.append({
                    "type": "dependency",
                    "related_id": dependency,
                    "message": f"Beroendet {dependency} måste vara completed innan steget kan utföras.",
                })
        for decision in step.get("decisions", []):
            if decision.get("status") != "resolved":
                computed.append({
                    "type": "decision",
                    "related_id": decision["finding_id"],
                    "message": decision["question"],
                })
        step["blockers"] = computed
        step["status"] = "blocked" if computed else "planned"


def select_next_action(plan: dict, progress: dict) -> dict:
    _sync_blockers(plan, progress)
    source = _plan_index(plan)

    for state in progress.get("steps", []):
        if state["status"] == "in-progress":
            return {"action": "resume-execution", "step_id": state["id"], "reason": "Steget är redan påbörjat och ska avslutas eller blockeras före ett nytt steg."}

    # A blocked earlier step must not hide a later independent executable step.
    # Verification failures are regressions and take priority over ordinary plan work.
    for state in progress.get("steps", []):
        verification_blockers = [b for b in state.get("blockers", []) if b.get("type") == "verification"]
        if state["status"] == "blocked" and verification_blockers:
            return {
                "action": "correct-step",
                "step_id": state["id"],
                "blockers": deepcopy(verification_blockers),
                "reason": "Stegets verifiering failade; minimal korrigering och ny verifiering prioriteras före nästa ordinarie steg.",
            }

    for plan_step in plan.get("steps", []):
        state = next(s for s in progress["steps"] if s["id"] == plan_step["id"])
        if state["status"] == "planned" and not state.get("blockers"):
            return {"action": "execute", "step_id": state["id"], "reason": "Första genomförbara steget enligt faktisk status och beroenden."}

    for state in progress.get("steps", []):
        pending = [d for d in state.get("decisions", []) if d.get("status") != "resolved"]
        if state["status"] == "blocked" and pending:
            return {
                "action": "request-decision",
                "step_id": state["id"],
                "finding_id": pending[0]["finding_id"],
                "question": pending[0]["question"],
                "reason": "Inget annat steg kan genomföras innan ett användarbeslut fattas.",
            }

    for state in progress.get("steps", []):
        if state["status"] == "blocked":
            return {"action": "review-blocker", "step_id": state["id"], "blockers": deepcopy(state.get("blockers", [])), "reason": "Återstående arbete är blockerat och kräver hantering innan det kan fortsätta."}

    if all(step["status"] in TERMINAL for step in progress.get("steps", [])):
        return {"action": "complete", "reason": "Alla plansteg är completed eller skipped."}

    return {"action": "no-action", "reason": "Ingen säker nästa åtgärd kunde härledas från aktuell status."}


def step_preview(plan: dict, progress: dict, step_id: str | None = None) -> dict:
    _sync_blockers(plan, progress)
    selected = step_id or select_next_action(plan, progress).get("step_id")
    if not selected:
        return {"step_id": None, "status": "none", "available_actions": []}
    pstep = _plan_index(plan)[selected]
    state = _progress_index(progress)[selected]
    actions = ["details", "modify", "skip"]
    if not state.get("blockers") and state["status"] == "planned":
        actions.insert(0, "do")
    if any(d.get("status") == "pending" for d in state.get("decisions", [])):
        actions.append("decide")
    return {
        "step_id": selected,
        "title": pstep["title"],
        "status": state["status"],
        "goal": pstep["goal"],
        "why": pstep["why"],
        "likely_files": list(pstep.get("likely_files", [])),
        "risk": pstep.get("risk", "low"),
        "planned_changes": list(pstep.get("planned_changes", [])),
        "decisions": deepcopy(state.get("decisions", [])),
        "blockers": deepcopy(state.get("blockers", [])),
        "overrides": list(state.get("overrides", [])),
        "available_actions": actions,
    }


def apply_user_action(
    plan: dict,
    progress: dict,
    action: str,
    step_id: str,
    *,
    note: str | None = None,
    finding_id: str | None = None,
    answer: str | None = None,
) -> dict:
    _sync_blockers(plan, progress)
    states = _progress_index(progress)
    if step_id not in states:
        raise ValueError(f"Okänt steg: {step_id}")
    step = states[step_id]

    if action == "details":
        _event(progress, "details", step_id, note or "Användaren bad om mer detaljer.")
        return progress

    if action == "modify":
        if not note or not note.strip():
            raise ValueError("Ändra förslaget kräver en konkret ändringsinstruktion.")
        step["overrides"].append(note.strip())
        step["blockers"] = [b for b in step.get("blockers", []) if b.get("type") not in {"execution", "verification"}]
        if step["status"] not in TERMINAL:
            step["status"] = "planned"
        _event(progress, "modified", step_id, note.strip())
        _sync_blockers(plan, progress)
        return progress

    if action == "skip":
        if step["status"] == "completed":
            raise ValueError("Ett redan completed steg kan inte hoppas över.")
        step["status"] = "skipped"
        step["skip_reason"] = (note or "Hoppades över av användaren.").strip()
        step["blockers"] = []
        step["verification_status"] = "not-verified"
        _event(progress, "skipped", step_id, step["skip_reason"])
        _sync_blockers(plan, progress)
        return progress

    if action == "decide":
        if not finding_id or answer is None or not str(answer).strip():
            raise ValueError("Beslut kräver finding_id och ett uttryckligt svar.")
        for decision in step.get("decisions", []):
            if decision["finding_id"] == finding_id:
                decision["status"] = "resolved"
                decision["answer"] = str(answer).strip()
                _event(progress, "decision-resolved", step_id, f"{finding_id}: {decision['answer']}")
                _sync_blockers(plan, progress)
                return progress
        raise ValueError(f"Ingen beslutspunkt för {finding_id} i {step_id}")

    if action == "do":
        if step["status"] in TERMINAL:
            raise ValueError(f"Steget är redan {step['status']}.")
        if step.get("blockers"):
            raise ValueError("Steget är blockerat och får inte startas innan blockerarna är lösta.")
        step["status"] = "in-progress"
        _event(progress, "started", step_id, note or "Användaren godkände att steget genomförs.")
        return progress

    raise ValueError(f"Okänd användaråtgärd: {action}")


def record_execution_result(
    plan: dict,
    progress: dict,
    step_id: str,
    *,
    success: bool,
    verification_status: str,
    note: str | None = None,
) -> dict:
    if verification_status not in {"verified", "failing", "not-verified"}:
        raise ValueError("verification_status måste vara verified, failing eller not-verified.")
    step = _progress_index(progress).get(step_id)
    if not step:
        raise ValueError(f"Okänt steg: {step_id}")
    if step["status"] != "in-progress":
        raise ValueError("Endast ett in-progress-steg kan avslutas.")

    step["verification_status"] = verification_status
    # A failing verification is a regression signal and may never be recorded as completed,
    # even if file modification itself succeeded. not-verified remains a truthful completion
    # state when relevant checks were attempted/assessed but unavailable in the environment.
    if verification_status == "failing":
        success = False
    if success:
        step["status"] = "completed"
        step["blockers"] = []
        _event(progress, "completed", step_id, note or f"Steget genomfördes; verifiering={verification_status}.")
    else:
        step["status"] = "blocked"
        step["blockers"] = [{
            "type": "verification" if verification_status == "failing" else "execution",
            "related_id": step_id,
            "message": note or "Genomförandet eller verifieringen misslyckades och kräver åtgärd innan steget kan slutföras.",
        }]
        _event(progress, "failed", step_id, note or f"Steget blockerades; verifiering={verification_status}.")
    _sync_blockers(plan, progress)
    return progress


def render_progress(plan: dict, progress: dict, template_text: str | None = None) -> str:
    from pathlib import Path

    _sync_blockers(plan, progress)
    counts = {}
    for step in progress.get("steps", []):
        counts[step["status"]] = counts.get(step["status"], 0) + 1
    summary = ", ".join(f"{key}: **{value}**" for key, value in sorted(counts.items())) or "Inga plansteg."

    lines = []
    for step in progress.get("steps", []):
        reason = f" — {step['skip_reason']}" if step.get("skip_reason") else ""
        lines.append(f"- `{step['id']}`: **{step['status']}**; verifiering: `{step['verification_status']}`{reason}")
    steps_text = "\n".join(lines) or "Inga steg."

    blocker_lines = []
    for step in progress.get("steps", []):
        for blocker in step.get("blockers", []):
            blocker_lines.append(f"- `{step['id']}` [{blocker['type']}]: {blocker['message']}")
        for decision in step.get("decisions", []):
            if decision.get("status") == "resolved":
                blocker_lines.append(f"- `{step['id']}` beslut `{decision['finding_id']}`: löst — {decision.get('answer', '')}")
    blockers_text = "\n".join(blocker_lines) or "Inga aktiva blockerare eller särskilda beslut."

    history_text = "\n".join(
        f"- {event['sequence']}. `{event['action']}`"
        + (f" för `{event['step_id']}`" if event.get("step_id") else "")
        + (f": {event['note']}" if event.get("note") else "")
        for event in progress.get("history", [])
    ) or "Ingen historik."

    nxt = select_next_action(plan, progress)
    if nxt.get("step_id"):
        next_text = f"`{nxt['action']}` för `{nxt['step_id']}` — {nxt['reason']}"
    else:
        next_text = f"`{nxt['action']}` — {nxt['reason']}"

    template = template_text or Path(__file__).resolve().parents[2].joinpath("templates/repository-progress.md.tpl").read_text(encoding="utf-8")
    replacements = {
        "REPOSITORY_NAME": progress["repository_name"],
        "SUMMARY": summary,
        "STEPS": steps_text,
        "BLOCKERS": blockers_text,
        "HISTORY": history_text,
        "NEXT_ACTION": next_text,
    }
    for key, value in replacements.items():
        template = template.replace("{{" + key + "}}", value)
    return template.rstrip() + "\n"
