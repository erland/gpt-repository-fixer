from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTRUCTION = ROOT / "src" / "instructions" / "system.md"


def text() -> str:
    return INSTRUCTION.read_text(encoding="utf-8")


def test_analysis_precedes_changes():
    t = text()
    assert "Analys före ändring" in t
    assert "Gör inga repositoryändringar innan" in t
    assert "repository-analysis.md" in t
    assert "repository-fix-plan.md" in t


def test_real_user_decisions_only():
    t = text()
    assert "Ställ inte frågor för sådant du kan avgöra säkert" in t
    assert "Fråga bara när svaret materiellt påverkar korrektheten" in t
    assert "licensval" in t
    assert "osäker" in t


def test_minimum_change_and_no_unrelated_refactoring():
    t = text()
    assert "Minimum necessary change" in t
    assert "Utför inte orelaterad refaktorering" in t
    assert "inte en generell kodrefaktorerare" in t


def test_github_pr_lifecycle_is_explicit():
    t = text()
    assert "kontrollera PR-status före varje nytt GitHub-ändringssteg" in t
    assert "om föregående PR har mergats" in t
    assert "ett naturligt plansteg per commit" in t


def test_license_is_not_auto_selected():
    t = text()
    assert "du ska inte själv välja eller ersätta licens" in t
    assert "copyright-innehavare" in t


def test_full_analysis_must_be_exhaustive_before_final_plan():
    t = text()
    assert "Fullständig analys och completeness-gate" in t
    assert "Begränsa aldrig den fullständiga fyndlistan till de viktigaste fyra eller fem fynden" in t
    assert "alla identifierade öppna fynd ska bevaras" in t
    assert "Slutlig fix-plan skapas normalt först när analysen är komplett" in t
    assert "analys ofullständig → fortsätt" in t


def test_missing_license_is_always_visible():
    t = text()
    assert "LICENSE-kontrollen ska alltid ge ett synligt resultat" in t
    assert "explicit **Överväg**-fynd" in t
