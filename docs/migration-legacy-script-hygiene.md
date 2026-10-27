# Legacy-byggskript – hygieneinventering inför merge av PR #7

Datum: 2026-10-27. Den aktiva bygg- och releasekedjan installerar den
versionslåsta originalmotorn från GPT Byggaren 1.6.33. Detta dokument
beskriver **kandidater för senare borttagning**, inte en utförd radering.

| Äldre komponent | Bedömning | Åtgärd |
| --- | --- | --- |
| `scripts/build_distributions.py` | Äldre egen distributionsbyggare, ersatt i aktiv CI av installerad 1.6.33-motor. Kan fortfarande behövas av äldre tester och lokala instruktioner. | **Behåll tills alla anrop är migrerade.** |
| `scripts/validate_distributions.py` | Äldre validator med projektspecifika historiska antaganden. Installerad 1.6.33-validator används i aktiv CI. | **Behåll tills anrop/spårbarhet är kartlagda.** |
| `scripts/lint_gpt_project.py` | Äldre projektlint. Nytt motorbygge i CI är inte i sig bevis att samma projektunika lint täcks. | **Behåll, granska unik kontrolltäckning.** |
| `scripts/project_hygiene.py` | Projektspecifik hygiene och releasekontroller. | **Behåll och kör i slutgaten.** |
| `scripts/validate_runtime_parity.py` | Kräver historisk runtime-lista med Custom GPT. | **Behåll som historisk källa tills ny paritetsrapport och hostbegränsningar är dokumenterade.** |
| `scripts/validate_release_readiness.py` | Historiska releasekrav, inklusive Custom GPT. | **Behåll tills canonical releasegates har bevisad motsvarighet.** |
| `scripts/validate_chat_runtime.py`, `scripts/validate_openai_plugin_runtime.py`, `scripts/validate_custom_gpt_runtime.py`, `scripts/validate_opencode_runtime.py` | Äldre runtime-specifika kontroller som delvis ersatts av ZIP- och regressionstester. | **Behåll tills varje unik kontroll täcks.** |
| `scripts/lib/*.py` | Repository Fixers egen körbara domänlogik, refereras av de tre canonical Skills. | **Bevara; inte del av motorstädningen.** |
| `src/instructions/system.md` | Ursprunglig instruktion som används i historiska spårbarhetstester. | **Bevara som historiskt underlag**, inte aktiv canonical source. |
| `scripts/preview_canonical_migration.py` | Isolerad migration/preflight; har varit viktig för att visa fem-runtime-paritet. | **Behåll tills slutgaten och aktiv CI kan ersätta den.** |

## Bedömning

Den aktiva CI/releasekedjan är migrerad, men ett säkert raderingsbeslut
kräver både verifierad likvärdighet och kontroll av kvarvarande lokala
anrop/tester. **Inga legacy-skript raderas i detta steg.**

Före merge: kontrollera `README.md`, `PROJECT.md`, `STATUS.md`,
`project-status.yaml`, utvecklingsplan och aktiveringsgate mot CI-resultat.
Verifiera länkar, versionsuppgifter, lint/hygiene, fem artefakter samt
att release från migrerad tagg inte påstås ha provkörts om den inte har det.
