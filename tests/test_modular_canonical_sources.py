"""Guard staged modular canonical behavior against accidental loss of legacy rules."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "src/instructions/system.md"
CORE = ROOT / "canonical/core.md"
ANALYSIS = ROOT / "canonical/skills/repository-analysis/behavior.md"
REMEDIATION = ROOT / "canonical/skills/repository-remediation/behavior.md"
VERIFICATION = ROOT / "canonical/skills/repository-verification/behavior.md"


def sections(text):
    blocks = {}
    for block in text.split("\n## "):
        if block.startswith("# "):
            continue
        heading, _, body = block.partition("\n")
        blocks[heading.strip()] = body.strip()
    return blocks


def test_every_original_behavior_block_is_preserved_in_modular_sources():
    original = sections(LEGACY.read_text(encoding="utf-8"))
    destinations = {
        "Kärnprinciper": CORE,
        "Repository-inventering": ANALYSIS,
        "Fullständig analys och completeness-gate": ANALYSIS,
        "`repository-analysis.md`": ANALYSIS,
        "`repository-fix-plan.md`": REMEDIATION,
        "Fasmedvetet nästa steg": CORE,
        "Interaktivt åtgärdsflöde": REMEDIATION,
        "ZIP-flöde": REMEDIATION,
        "GitHub-flöde": REMEDIATION,
        "Licenspolicy": CORE,
        "Policy för borttagning av filer": CORE,
        "Operativ kärna": CORE,
    }
    assert set(original) == set(destinations) | {"Frågor, slutverifiering och avgränsning"}
    for heading, destination in destinations.items():
        assert original[heading] in sections(destination.read_text(encoding="utf-8"))[heading], heading

    split = original["Frågor, slutverifiering och avgränsning"]
    a = "Fråga bara när svaret materiellt påverkar korrektheten eller kräver ett verkligt användarbeslut."
    b = "När åtgärdsarbetet avslutas ska repositoryt analyseras om från början och `repository-final-report.md` redovisa lösta, hoppade, kvarstående och nya fynd samt verifieringar och osäkerheter."
    c = "Repository Fixer är inte en generell kodrefaktorerare. Utöka inte arbetet till ny funktionalitet eller större arkitekturarbete; dokumentera sådant separat."
    assert split == " ".join((a, b, c))
    core = CORE.read_text(encoding="utf-8")
    verification = VERIFICATION.read_text(encoding="utf-8")
    assert a in core and c in core and b in verification


def test_modular_skills_is_the_active_configuration():
    import yaml
    parsed = yaml.safe_load((ROOT / "gpt-project.yaml").read_text(encoding="utf-8"))
    assert parsed["instructions"]["mode"] == "modular_skills"
    assert parsed["instructions"]["canonical"] == "canonical/core.md"
    assert parsed["instructions"]["core"] == "canonical/core.md"
    assert parsed["runtime"]["custom_gpt"]["enabled"] is False
    assert parsed["runtime"]["claude"]["enabled"] is True
    assert set(parsed["build_system"]["runtime_targets"]) == {"chat", "plugin", "claude_project", "claude_skills", "opencode"}
    assert set(parsed["build_system"]["targets"]) == {"project", "chat", "plugin", "claude_project", "claude_skills", "opencode"}
    skills = parsed["skills"]["definitions"]
    assert {skill["id"] for skill in skills} == {"repository-analysis", "repository-remediation", "repository-verification"}
    for skill in skills:
        assert (ROOT / skill["source"]).is_file()


def test_explicit_skill_resources_exist_and_are_scoped():
    import yaml

    cfg = yaml.safe_load((ROOT / "gpt-project.yaml").read_text(encoding="utf-8"))
    assert cfg["skills"]["resource_policy"] == "explicit"
    skills = cfg["skills"]["definitions"]
    for skill in skills:
        for kind in ("references", "assets", "scripts"):
            paths = skill[kind]
            assert isinstance(paths, list), (skill["id"], kind)
            assert len(paths) == len(set(paths)), (skill["id"], kind)
            for relative in paths:
                assert not relative.startswith("/") and ".." not in Path(relative).parts
                assert (ROOT / relative).is_file(), (skill["id"], relative)
        assert skill["scripts"], skill["id"]
        assert skill["references"], skill["id"]
    assert "scripts/lib/github_actions_analysis.py" in skills[0]["scripts"]
    assert "scripts/lib/build_test_analysis.py" in skills[0]["scripts"]
