# Repository Fixer

Repository Fixer är ett GPT-projekt som analyserar ett källkodsrepository, identifierar dokumentations- och repository-hygienproblem och producerar en evidensbaserad rapport samt en stegvis åtgärdsplan.

Version **1.0.0** är den första stabila releasen. Canonical source finns under `src/`; genererade distributioner ska endast ligga under `build/` och `dist/` och ingår inte i projektets canonical source.

## Projektstatus

**Steg 1–27 är genomförda**. Repository Fixer 1.0.0 är fortsatt stabil. Migreringen till GPT Byggaren 1.5.0 har verifierat steg 25–26: stateful 1.5-kontrakt är införda och Chat ZIP, Custom GPT samt OpenCode byggs från samma canonical projekt. GitHub Actions reproducerar den lokala test-, build- och releasekedjan. Runtime parity och generaliserad release readiness är nu verifierade. Nästa migrationssteg är full slutvalidering av migreringen och releasekedjan.

## Viktiga filer

- `gpt-project.yaml` – deklarativ projektkonfiguration
- `project-status.yaml` – maskinläsbar projektstatus
- `PROJECT.md` – målbild och avgränsning
- `STATUS.md` – mänskligt läsbar status
- `docs/development-plan.md` – full utvecklingsplan
- `src/instructions/system.md` – canonical runtimeinstruktion
- `schemas/repository-inventory.schema.json` – inventeringskontrakt
- `schemas/repository-finding.schema.json` – fynd- och evidenskontrakt
- `knowledge/finding-model.md` – regler för klassificering, evidens och beslutspunkter
- `knowledge/readme-analysis.md` – regler för evidensbaserad README-granskning
- `knowledge/markdown-documentation-analysis.md` – regler för konsistensanalys av övrig Markdown
- `knowledge/license-analysis.md` – regler för licenskontroll och användarbeslut
- `knowledge/repository-hygiene.md` – regler för `.gitignore`, genererade artefakter, historiska arbetsfiler och lockfilskonflikter
- `knowledge/build-test-analysis.md` – regler för build-/testkommandon och verifieringsstatus
- `schemas/build-test-verification.schema.json` – maskinläsbar modell för build/test-verifiering
- `knowledge/github-actions-analysis.md` – regler för faktisk CI-täckning, triggers, runtime, package manager och action-versioner
- `schemas/github-actions-analysis.schema.json` – maskinläsbar modell för workflow- och build/test-täckning
- `schemas/license-decision.schema.json` – maskinläsbart kontrakt för licensbeslut
- `knowledge/analysis-report.md` – regler för den fristående analysrapporten
- `schemas/repository-analysis.schema.json` – maskinläsbar modell för analysrapporten
- `templates/repository-analysis.md.tpl` – canonical Markdown-mall för rapporten
- `knowledge/fix-plan.md` – regler för prioritering, gruppering, risk, beslut och genomförbara åtgärdssteg
- `schemas/repository-fix-plan.schema.json` – maskinläsbar modell för åtgärdsplanen
- `templates/repository-fix-plan.md.tpl` – canonical Markdown-mall för åtgärdsplanen
- `knowledge/zip-workflow.md` – regler för säker ZIP-hantering och portabel återupptagning
- `schemas/repository-zip-state.schema.json` – maskinläsbar portabel ZIP-state
- `scripts/lib/zip_workflow.py` – säker uppackning, state-lagring och komplett ompaketering
- `knowledge/github-read-workflow.md` – regler för GitHub-källor, semantisk ZIP-paritet och read-only fallback
- `schemas/repository-github-source.schema.json` – maskinläsbar GitHub-källkontext
- `scripts/lib/github_read_workflow.py` – URL-normalisering, snapshot-materialisering och GitHub read-context
- `knowledge/github-write-workflow.md` – regler för säker branch/PR-livscykel, merge/close och commitgränser
- `schemas/repository-github-write-state.schema.json` – maskinläsbar GitHub write-state
- `scripts/lib/github_write_workflow.py` – deterministisk branch/PR-state och commitkoppling per plansteg
- `knowledge/step-verification.md` – regler för diff-, build/test-, syntax-, referens- och dokumentationsverifiering efter ändring
- `schemas/repository-step-verification.schema.json` – maskinläsbart kontrakt för verifieringsresultat per steg
- `scripts/lib/step_verification.py` – deterministiska verifieringskontroller och aggregering
- `knowledge/final-verification.md` – regler för full nyanalys, fyndjämförelse och slutrapport
- `schemas/repository-final-report.schema.json` – maskinläsbar modell för slutrapporten
- `templates/repository-final-report.md.tpl` – canonical mall för `repository-final-report.md`
- `scripts/lib/final_report.py` – jämförelse- och renderingslogik för slutverifiering
- `scripts/validate_chat_runtime.py` – fristående smoke-validering av Chat ZIP för analys, filoutput och återupptagning
- `scripts/validate_custom_gpt_runtime.py` – fristående kontroll av Custom GPT-instruktion, Knowledge-paritet, capabilities och plattformsbegränsningar
- `scripts/validate_release_readiness.py` – samlad kontroll av runtime-paritet, canonical source, plattformsbegränsningar och release readiness

## Lokal validering

```bash
python -m pytest -q
python scripts/lint_gpt_project.py --project-root .
python scripts/project_hygiene.py --project-root .
python scripts/build_distributions.py --project-root . --version 1.0.0
python scripts/validate_distributions.py --project-root .
python scripts/validate_release_readiness.py --project-root .
```

## GitHub Actions

CI kör tester, lint, final hygiene, build, distributionsvalidering och release readiness vid push och pull request. En publicerad GitHub Release använder release-taggen som versionskälla och publicerar samtliga distributionsartefakter.
