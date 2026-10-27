# Aktiveringsgate – Repository Fixer → GPT Byggaren 1.6.33

Datum: 2026-10-27  
Branch: `migration/gpt-builder-1.6.33-modular-sources` / PR #7  
Aktuell fas: **Aktiveringsförberedelse (motor och fem distributioner verifierade i separat kopia; originalkonfigurationen ännu legacy).**

## Varför migrationen inte är färdig

Den aktiva `gpt-project.yaml` pekar fortfarande på `src/instructions/system.md`,
registrerar historisk Custom GPT och använder äldre distributions-/paritetsvalidatorer.
Den kanoniska motorn från GPT Byggaren 1.6.33 används ännu endast mot den
isolerade kopian i jobbet `canonical-engine-preflight`.

## Verifierat inom migrationsspåret

- Canonical `core.md` och tre ansvarsmässigt separerade Skills finns.
- Originalmotorn 1.6.33 laddas versionsbundet och klarar sitt självtest.
- Motorns installation, byggning och distributionsvalidering passerar i isolerad kopia.
- Fem distributioner byggs: Chat, Plugin, Claude Projects, Claude Skills och OpenCode.
- Paketerade resurser, Knowledge, tillståndsövergångar och grundläggande runtimekontrakt valideras deterministiskt.
- De gamla testerna körs fortfarande mot legacy-läget och ska inte ses som bevis för den nya aktiva byggkedjan.
- Preflightens installation/build/validate/innehållskontroll är nu en **blockerande CI-gate**, inte bara loggad diagnostik.

## Återstående arbete – håll detta som migrationsplan

1. **Aktivera projektmodellen:** Flytta den prövade isolerade konfigurationen till
   aktiva `gpt-project.yaml`: `instructions.mode: modular_skills`,
   `canonical/core.md`, fem runtime-mål, `custom_gpt.enabled: false`.
   Utgå från redan beprövade inställningar i
   `scripts/preview_canonical_migration.py`; skapa ingen ny builder.
2. **Byt aktiv CI- och byggkedja:** Installera den pinade originalmotorn 1.6.33
   och låt lint, build och validatorer köra på **projektroten**, inte bara kopian.
   Flytta/ersätt legacy-tester som förutsätter historisk Custom GPT och äldre
   runtime-lista, men bevara domän- och regressionsskydd.
3. **Verifiera aktiv leverans:** Kräva grön pytest, kanonisk lint, fem ZIP,
   distributionsvalidering och innehållsgates. Dokumentera begränsningar hos
   faktiska hostmiljöer; pakettest är inte värdmiljötest.
4. **Dokumentation och hygiene:** Uppdatera README, PROJECT/STATUS/plan där de
   finns, CI-/versionsreferenser och migrationschecklista; inventera gamla
   builder/lint/validation-skript och ta bara bort de faktiskt ersatta.
5. **Slutverifiering:** Kontrollera att exakt fem aktuella runtime-artefakter,
   ett komplett projekt och verifieringsrapport kan levereras. Först därefter
   rekommenderas merge/release.

## Skilj på verifieringsnivåer

**Grönt i isolerad kopia** betyder att canonical-motorn kan producera och
validera de fem distributionerna med tillfällig migration-konfiguration.
Det betyder inte att den gamla byggkedjan ersatts i projektet, att hostens
Plugins/Claude kan köra Python eller att full funktionell paritet är bevisad.

Historisk aktiveringsprovning (`307521a`) gav 188 PASS och 5 FAIL i legacy-tester
som fortfarande förutsatte gamla runtime-listan. Vi ska därför utföra
en samordnad aktivering av både projektkonfiguration och CI/testprofil,
inte enbart slå om `instructions.mode`.

Nästa konkreta steg: **genomför punkt 1–2 på PR #7 och rätta faktiskt
påvisade CI-fel innan aktivering betraktas som genomförd.**
