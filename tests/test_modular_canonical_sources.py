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


def test_legacy_runtime_remains_the_active_configuration():
    config = (ROOT / "gpt-project.yaml").read_text(encoding="utf-8")
    assert "canonical: src/instructions/system.md" in config
    assert "mode: modular_skills" not in config
