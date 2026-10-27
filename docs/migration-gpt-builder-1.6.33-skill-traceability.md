# Spårbarhets- och resursplan för modulära Skills

Status: **migrationsunderlag, ej aktiverad implementation**. Källa: `src/instructions/system.md` på `main` 2026-10-27. Inga runtime- eller projektkontrakt har ännu ändrats.

## 1. Spårbarhet från varje instruktionavsnitt

| Avsnitt i `src/instructions/system.md` | Ny auktoritativ plats | Viktig funktion att bevara |
| --- | --- | --- |
| Introduktion/leveransordning | `canonical/core.md` | ZIP/GitHub som ingång; analys följd av plan, godkända ändringar sist |
| Kärnprinciper / Analys före ändring | `canonical/core.md` | Avgränsad korrigering tillåten utan att påstå full granskning |
| Evidens före antaganden | `canonical/core.md` | Negativa fynd kräver observation; skilj osäkerhet |
| Minimum necessary change | `canonical/core.md` | Förhindra orelaterad förändring |
| Mänskligt beslut när det behövs | `canonical/core.md` | Juridiska/irreversibla/osäkra val till användaren |
| Verifiera efter ändring | `canonical/core.md` | Failing blockerar; not-verified är inte PASS |
| Repository-inventering | `canonical/skills/repository-analysis/behavior.md` | Konservativ, evidensbaserad stackidentifiering |
| Fullständig analys och completeness-gate | `canonical/skills/repository-analysis/behavior.md` | Alla relevanta kontrollområden, synligt LICENSE-resultat, bevarade fynd |
| repository-analysis.md | `canonical/skills/repository-analysis/behavior.md` | Struktur, fyndklasser, stabila ID och verifieringar |
| repository-fix-plan.md | `canonical/skills/repository-remediation/behavior.md` | Alla öppna fynd i plan, täckning och små steg |
| Fasmedvetet nästa steg | `canonical/core.md` | Analys före plan före åtgärder före slutrapport |
| Interaktivt åtgärdsflöde | `canonical/skills/repository-remediation/behavior.md` | In-progress, blockering och användarval |
| ZIP-flöde | `canonical/skills/repository-remediation/behavior.md` | Säker arbetskopia, portabel state, komplett ZIP |
| GitHub-flöde | `canonical/skills/repository-remediation/behavior.md` | Säker branch/PR-livscykel; inte direkt main |
| Licenspolicy | `canonical/core.md` | Aldrig välja licens/copyright åt användaren |
| Policy för borttagning av filer | `canonical/core.md` | Stark evidens eller användargodkännande |
| Frågor, slutverifiering och avgränsning | `canonical/core.md` (frågor/scope), `canonical/skills/repository-verification/behavior.md` (slutverifiering) | En avsiktlig delning utan dubbel auktoritativ regel |
| Operativ kärna | `canonical/core.md` | Läs status → avgränsat mål → verifiera → korrigera |
| Auktoritativ status | `canonical/core.md` | Statusfil över chattminne; failing CI blockerar |

**Inget avsnitt utelämnas.** För det enda uppdelade originalavsnittet ovan måste dess två underdelar granskas semantiskt vid implementation.

## 2. Skill-gränser och aktivering

| Skill | Aktiveras när | Äger utdata | Äger inte |
| --- | --- | --- | --- |
| `repository-analysis` | användaren vill inventera/analysera eller fortsätta ofullständig analys | repository-analysis och kontrolltäckning | ändring i repository |
| `repository-remediation` | komplett analys ska bli plan eller användaren genomför ett godkänt plansteg | repository-fix-plan, stegprogress, ZIP/PR-ändringar | full slutrapport |
| `repository-verification` | ett ändringssteg ska verifieras eller åtgärdsarbetet slutgranskas | stegverifiering, full nyanalys och repository-final-report | beslut att ändra/merga |

**Tvärgående handoff:** remediation måste anropa/utföra samma deterministiska verifieringsgates även när verification-Skill inte kan aktiveras separat av hosten. Gemensam kärna föreskriver gate; verification äger detaljer och rapportformat. Inget steg får bli klart utifrån enbart språkmodellens bedömning.

## 3. Preliminär resursägarmappning

Kategorierna nedan är **undersökningsunderlag**, inte klara `skills.resource_policy: explicit`-deklarationer. Faktisk importkedja, transitive beroenden och paketering behöver verifieras innan explicit isolation slås på.

| Skill | Kunskapsfiler (kandidater) | Skript (kandidater) | Kontrakt och mallar |
| --- | --- | --- | --- |
| Analys | `repository-inventory.md`, `analysis-completeness.md`, `finding-model.md`, `readme-analysis.md`, `markdown-documentation-analysis.md`, `license-analysis.md`, `repository-hygiene.md`, `build-test-analysis.md`, `github-actions-analysis.md`, `analysis-report.md`, `github-read-workflow.md`, `zip-workflow.md` | `scripts/lib/repository_inventory.py`, `readme_analysis.py`, `markdown_analysis.py`, `license_analysis.py`, `hygiene_analysis.py`, `build_test_analysis.py`, `github_actions_analysis.py`, `finding_model.py`, `analysis_report.py`, `github_read_workflow.py`, `zip_workflow.py` | `schemas/repository-*.schema.json` (relevanta), `schemas/build-test-verification.schema.json`, `schemas/github-actions-analysis.schema.json`, `templates/repository-analysis.md.tpl` |
| Åtgärder | `fix-plan.md`, `interactive-step-control.md`, `github-write-workflow.md`, `zip-workflow.md`, `step-verification.md` | `scripts/lib/fix_plan.py`, `step_control.py`, `github_write_workflow.py`, `zip_workflow.py`, `step_verification.py` | `schemas/repository-fix-plan.schema.json`, `schemas/repository-progress.schema.json`, `schemas/repository-github-write-state.schema.json`, `schemas/repository-zip-state.schema.json`, `templates/repository-fix-plan.md.tpl`, `templates/repository-progress.md.tpl` |
| Verifiering | `step-verification.md`, `final-verification.md`, `analysis-completeness.md` | `scripts/lib/step_verification.py`, `final_report.py`, `e2e_analysis.py` och nödvändiga återanalysmoduler | `schemas/repository-step-verification.schema.json`, `schemas/repository-final-report.schema.json`, `templates/repository-final-report.md.tpl` |

**Gemensamt kontrakt:** `gpt-project.yaml`, `project-status.yaml`, `src/runtime-policy/`, `schemas/capability-contract.schema.json`, `schemas/artifact-contract.schema.json`, `schemas/workspace-state-contract.schema.json`, `schemas/tool-contract.schema.json`. Övriga `schemas/` och `knowledge/KNOWLEDGE.md` ska placeras efter konsumtionsanalys, inte kopieras blint till alla paket. `scripts/lib/project_model.py` och `scripts/lib/__init__.py` är möjliga gemensamma Python-beroenden.

## 4. Säker verifieringsordning för följande implementations-PR

1. Fastställ faktisk importgraf för `scripts/lib/*.py` och alla test- och validator-anrop. Bevara alla transitiva beroenden.
2. Skapa `canonical/core.md` och de tre behavior-filerna som exakta, spårbara beteendeprojektioner; granska undantagen till reglerna.
3. Sätt `instructions.mode: modular_skills`, `instructions.core`, `instructions.canonical` och `skills.definitions[].source` när källorna finns. Aktivera `skills.resource_policy: explicit` först när listor för `references`, `assets`, `scripts` är verifierade för varje Skill.
4. Kör tester mot originalbeteenden; verifiera canonical installer/build med bifogad exakt 1.6.33-motor och samtliga fem distributioner separat. Redovisa hostbegränsningar och verklig körbarhet.
5. Först därefter: ersätt tidigare bygg- och lint-skript med dokumenterad funktionsparitet, uppdatera CI/release och alla status-/README-/planreferenser. Ingen radering utan substitutionsbevis.

## 5. Status för detta underlag

- [x] Samtliga top-level-instruktionsavsnitt har en ny ansvarig plats.
- [x] Identifierade tvärgående regler och risk för dubbel ägare.
- [x] Dokumenterade preliminära resurskandidater och verifieringsordning.
- [ ] Importgraf och verklig resursminimalitet verifierad med körning.
- [ ] Nya canonical-filer skapade, byggda och runtimevaliderade.

Detta är en **designgranskning**, inte runtimeverifiering. Varken 1.6.33-aktivering eller release readiness får härledas av dokumentet.
