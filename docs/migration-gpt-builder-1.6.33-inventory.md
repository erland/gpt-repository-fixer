# Migrationsinventering: GPT Byggaren 1.5.0 → 1.6.33

Datum: 2026-10-27  
Källa: `main` i `erland/gpt-repository-fixer`, inventerat via GitHub-träd och riktad källfilsgranskning.  
Migrationsfas: **1/6 – inventering**. Detta dokument ändrar inte aktiva distributioner.

## 1. Nuläge och bevis

- 164 versionshanterade filer i inventerat träd.
- `README.md`, `PROJECT.md`, `STATUS.md` och `project-status.yaml` redovisar v1.0.0 och en *slutförd tidigare migrering* till GPT Byggaren 1.5.0; uppgifterna gäller inte 1.6.33.
- `gpt-project.yaml` använder `src/instructions/system.md` som monolitisk canonical instruktion och har runtime-mål för projektpaket, Chat, Custom GPT, OpenCode och Plugin.
- Claude Projects är bedömd men avaktiverad. Claude Skills är inte uttryckligen ett eget byggmål. 1.6.33 har fem mål: Chat, Plugin, Claude Projects, Claude Skills, OpenCode; historiska Custom GPT ska inte fortsätta som aktiv sjätte runtime.
- `.github/workflows/ci.yml` kör pytest, lokala lint/hygiene-/build-/paritetskontroller vid både push och pull_request (kan ge dubbelkörning). `release.yml` bygger på release-taggen med samma äldre skript.
- Den bifogade `gpt-byggaren-engine-1.6.33(2).zip` är separat från Repository Fixers egen exekveringslogik. Engine-version ska versionspinnas i CI; domänversionen 1.0.0 ändras inte automatiskt.

## 2. Bevara: projektspecifik exekveringskod

Följande `scripts/lib/` är **domänkod, inte ersättningsbar av GPT Byggarens generiska distributionsmotor**:

| Moduler | Funktion och migreringsbeslut |
| --- | --- |
| `repository_inventory.py`, `readme_analysis.py`, `markdown_analysis.py`, `license_analysis.py`, `hygiene_analysis.py`, `github_actions_analysis.py`, `build_test_analysis.py` | Repo-inventering och evidensbaserade kontrollområden: **bevara**. |
| `finding_model.py`, `analysis_report.py`, `fix_plan.py`, `final_report.py` | Fynd, rapport, komplett åtgärdsplan och slutrapport: **bevara**. |
| `zip_workflow.py`, `github_read_workflow.py`, `github_write_workflow.py` | Säker ZIP-inläsning, portabel `.repository-fixer/`-state samt GitHub branch/PR-livscykel: **bevara**. |
| `step_control.py`, `step_verification.py`, `e2e_analysis.py` | Interaktiv progression, stegverifiering och E2E-funktioner: **bevara**. |
| `project_model.py`, `__init__.py` | Projektspecifika stödkomponenter: **behåll tills beroendegranskning visar annat**. |

`src/runtime-policy/`, `knowledge/` (18 ämnesfiler plus index), `schemas/` (20 JSON-scheman plus README), `templates/` och `evals/model-compatibility/` utgör kompletterande domänkontrakt och resurser. De får inte raderas enbart för att en ny Skill-struktur införs. Behåll beteendet från `src/instructions/system.md` oförändrat tills spårbar omstrukturering godkänts.

## 3. Kandidater för ersättning (ingen borttagning nu)

| Befintlig fil | Rekommenderad hantering | Krav före borttagning |
| --- | --- | --- |
| `scripts/build_distributions.py` | Kandidat att ersättas av kanonisk 1.6.33-distributionsmotor | Verifiera projektunik kopiering, manus, ZIP-utdata och checksummor mot den nya motorn. |
| `scripts/lint_gpt_project.py`, `scripts/project_hygiene.py` | Kandidater att ersättas eller delas upp | Identifiera projektspecifika kontroller som behöver behållas separat; jämför resultat på samma projekt. |
| `scripts/validate_distributions.py`, `scripts/validate_runtime_parity.py`, `scripts/validate_release_readiness.py` | Kandidater för ny kanonisk validering | Bevisa motsvarande semantik och fem runtime-kontroller, inte bara scriptnamn. |
| `scripts/validate_chat_runtime.py`, `scripts/validate_openai_plugin_runtime.py`, `scripts/validate_opencode_runtime.py` | **Utred:** kan innehålla domänspecifika smoke-fall | Kör befintliga tester mot nya paketen och flytta unika assertioner till projektets tester vid behov. |
| `scripts/validate_custom_gpt_runtime.py`, `tests/test_custom_gpt_distribution.py`, `templates/README.custom-gpt.md.tpl` | Historisk kompatibilitet | Avveckla aktivt runtime-mål först efter att historiken dokumenterats och relevanta tester migrerats. |
| `.github/workflows/ci.yml`, `.github/workflows/release.yml` | Pinna originalmotorn till `v1.6.33` och välj tydlig CI-triggerpolicy | Kontrollera verkligt installationstest, testkedja och release-tag-baserad version. |

## 4. Förslag till modulär instruktion (kräver spårbarhetsgranskning)

- `canonical/core.md`: analys före ändring, evidenskrav, minimum necessary change, användarbeslut, verifiering, statusauktoritet, nästa-steg-kontrakt.
- `canonical/skills/repository-analysis/behavior.md`: inventering, completeness-gate, kontrollområden, fynd- och analysrapport.
- `canonical/skills/repository-remediation/behavior.md`: komplett fixplan, stegkontroll, säkert ZIP- och GitHub-flöde, beslut före förändring.
- `canonical/skills/repository-verification/behavior.md`: diff/build/test-kontroll efter ändring, slutlig nyanalys och slutrapport.

**Risk att hantera:** verifiering per ändringssteg finns även i remediation; dela ansvar tydligt så en Skill inte förutsätter outtalad aktivering av en annan. Kartlägg samtliga avsnitt i gamla `system.md` mot core eller exakt en ägande Skill; föreslå förenkling, inte automatisk splitting baserad på rubriker. Resurser bör deklareras per Skill med `skills.resource_policy: explicit` först när faktiska filberoenden är kartlagda.

## 5. Kompatibilitets- och distributionsmatris

| Mål 1.6.33 | Nuläge | Risk / verifiering |
| --- | --- | --- |
| Chat | Aktiv | ZIP, portabel state, Python och återupptagning måste smoke-testas. |
| Plugin | Aktiv, `equivalent_runtime_dependent` | Körbar Python, skrivbar arbetsyta och persistent state krävs för hela fix-flödet; deklarativ paketering är inte likvärdig exekvering. |
| Claude Projects | Avaktiverad | Utvärdera om hosten kan stödja faktiska verktyg, state och binära artefakter; märk annars reducerad kompatibilitet. |
| Claude Skills | Ej definierad | Ny skillprojektion och explicit resurshantering; verifiera hostkraven. |
| OpenCode | Aktiv | Behåll arbetsyta, scriptkörning och GitHub/ZIP-funktion; verifiera adaptern. |
| Custom GPT (historisk) | Aktiv i 1.5.0 | Får inte räknas som sjätte aktiv runtime i 1.6.33. |

## 6. Test- och dokumentationsinventering

- `tests/` omfattar testkontrakt, analyser, fynd, planer, ZIP, GitHub read/write, PR-flöde, E2E, peer-distributioner, parity, release och workflow-kontroller samt scenariefixtures. **Behåll dessa som regressionsbaslinje.**
- Utgå från `python -m pytest -q -p no:cacheprovider`; komplettera senare med 1.6.33-lint, kanoniskt build, fem distributionsvalideringar och runtime-specifika smoke-fall.
- Vid aktiv migrering uppdateras tillsammans: `gpt-project.yaml`, `project-status.yaml`, `PROJECT.md`, `STATUS.md`, `README.md`, `docs/development-plan.md`, workflow-filer och eventuella filhänvisningar. Nuvarande historiska 1.5.0-release-notering behålls.
- Ingen release- eller parity-status får markeras PASS förrän faktiska kommandoresultat finns.

## 7. Risker, gränser och nästa steg

1. **Hög:** Förlorad domänfunktion vid utbyte av scripts. Bevara `scripts/lib/` och projektspecifika asserts.
2. **Hög:** Falsk runtimeparitet vid endast ZIP-bygge. Testa körning och hostbegränsningar individuellt.
3. **Medel:** Resursförlust vid modulära Skills. Gör full avsnitt→core/Skill- och resurs→Skill-mappning.
4. **Medel:** Dubbla CI-körningar och gammalt Custom GPT-beroende. Inventera beroenden innan workflowbyte.
5. **Medel:** Statusdokument som felaktigt redovisar 1.6.33 som klar. Behåll separat migrationsstatus tills slutverifiering.

### Definition of done – detta inventeringssteg

- [x] Inventerat repositoryträd, konfiguration, status, canonical instruktion, relevanta skript och workflows.
- [x] Klassificerat domänmoduler respektive bygg-/valideringskandidater.
- [x] Föreslagit Skill-gränser, fem runtime-mål och nästa verifieringsgates.
- [ ] Byte-level test och full beroendegraf över alla Python-moduler (nästa steg).
- [ ] Ny motorinstallation, rebuild och runtime-tester mot Repository Fixer (senare steg).

**Nästa steg (2/6):** bygg en spårbarhetsmatris för varje avsnitt i `src/instructions/system.md` och resursberoenden per föreslagen Skill. Gör därefter en separat PR med `canonical/core.md`, Skill-beteendefiler och projektmodell, utan att radera äldre scripts. Verifiera mot befintliga tester före statusändring.
