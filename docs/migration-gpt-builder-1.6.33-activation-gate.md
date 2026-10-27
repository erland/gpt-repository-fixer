# Aktiveringsgate – GPT Byggaren 1.6.33

Datum: 2026-10-27  
Gren: `migration/gpt-builder-1.6.33-modular-sources` (PR #7).  
Status: **BLOCKERAD för aktivering; staged canonical Skills kan granskas och testas i legacy-läge.**

## Utförd aktiveringskontroll

En tillfällig konfigurationsändring satte `instructions.mode: modular_skills`, nya `instructions.core`/`canonical`, inaktiverade historisk Custom GPT och registrerade `chat`, `plugin`, `claude_project`, `claude_skills`, `opencode` som fem aktiva runtime-mål.

GitHub Actions körning för commit `307521a5863bb11115cdb96b4005836e65a93727`: **188 PASS, 5 FAIL**. Detaljer: [workflowkörning](https://github.com/erland/gpt-repository-fixer/actions/runs/40451277554).

| Fallerande kontroll | Faktisk orsak / nästa åtgärd |
| --- | --- |
| `tests/test_custom_gpt_distribution.py` | Historiskt Custom GPT-test bygger och validerar en gammal runtime. Flytta relevanta domänassertioner till Chat/Plugin/Claude Skills innan det pensioneras. |
| `tests/test_modular_canonical_sources.py` | Övergångsgard krävde legacy-config; ändra gard först när hela nya byggkedjan ersatts. |
| `tests/test_release_readiness.py` | Legacy-validator förutsätter exakt den gamla peer-listan inklusive Custom GPT. Ersätt med kanonisk 1.6.33-releasekontroll. |
| `tests/test_runtime_parity.py` (två fall) | Legacy-paritetsvalidator kräver gammal runtime-lista; den nya listan innehåller Claude Skills. Ersätt med canonical parity och explicita hostbegränsningar. |

**Åtgärd:** Aktiv konfiguration och testgard återställdes till senaste gröna tillstånd (commit `815681d`) på samma PR. Canonical core, tre Skill-beteenden och explicita preliminära resurser behålls. Dokumentet markerar inte de nya distributionerna som verifierade.

## Säker genomförandeordning

1. Kör originalmotorn 1.6.33:s `scripts/selftest_distribution_engine.py --source <engine-root>` med verifierad versionslåst motor.
2. Uppdatera/ersätt de äldre verktygstesterna så att de verifierar samma domänbeteenden i de fem aktuella distributionerna, utan att dölja fel med skip eller ändrade förväntningar.
3. Ändra `gpt-project.yaml` atomärt för fem fullständiga runtime-mål, `modular_skills`, core och explicita verifierade resurser.
4. Kör motorns oförändrade `install_distribution_engine.py`, lint, build, `validate_distributions.py`, `validate_portable_skills.py` samt projektspecifik pytest. Kontrollera Python-importer och filer i isolerade Skill-arkiv.
5. Kontrollera hostkrav separat: Plugin/Claude kan sakna nödvändig Python-exekvering eller skrivbar/persistent arbetsyta; paketvalidering bevisar inte full funktionell paritet.
6. Först efter gröna gates: CI/release-omläggning, README/PROJECT/STATUS/plan och säker städning av faktiskt ersatta scripts.

## Viktig avgränsning

Den separata GPT Byggaren-motorn är ett byggberoende och får inte ersätta `scripts/lib/` (Repository Fixers analys- och åtgärdskod). Originalets föråldrade tester ska inte raderas eller hoppas över förrän motsvarande regressionsskydd finns.
