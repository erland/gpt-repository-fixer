# Kanonisk motor – verifieringsgate (1.6.33)

Datum: 2026-10-27.

PR #7 inför en fristående `canonical-engine-preflight` i `.github/workflows/ci.yml`. Den hämtar exakt `v1.6.33` via release-URL och kör **originalets** `scripts/selftest_distribution_engine.py --source /tmp/gpt-builder-engine`.

## Avsikt och begränsning

- Originalmotorns integritet, installation och smoke-build av sex arkiv kontrolleras utan alternativ paketerare.
- Existerande projektunika tester, byggscript och distributionsvalidatorer körs fortsatt i det gamla jobbet. Ingen test tas bort eller markeras som överförd.
- Preflight använder den publika versionslåsta releaseartefakten; den säger **inte** att Repository Fixer kan byggas som modulär 1.6.33-kandidat.
- Aktuell `gpt-project.yaml` behåller gammal `instructions.canonical` och anger en `migration_target`; **ingen aktivering** av `modular_skills`.
- Att motor-selftest går igenom är en separat gate, inte tillräckligt för att verifiera `scripts/lib/`, GitHub/ZIP-workflow, hoststöd eller runtimeparitet.

## Nästa steg

1. Säkerställ att GitHub Actions-jobbet `canonical-engine-preflight` passerar.
2. Skapa en CI-körbar migrationskopia som installerar originalmotorn och använder de fem aktiva runtime-nycklarna, utan att störa legacy-jobbet.
3. Migrera varje unik gammal testassertion till aktuella runtime-testfall; ingen skip för att uppnå PASS.
4. Aktivera modular skills och byt slutligen ordinarie build/release-jobb först när migreringskopian passerar projektunika pytest samt originalmotor-lint, build och distributionsvalidering.
