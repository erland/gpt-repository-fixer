# Aktiveringsgate – Repository Fixer → GPT Byggaren 1.6.33

Datum: 2026-10-27  
Branch: `migration/gpt-builder-1.6.33-modular-sources` / PR #7  
Aktuell fas: **Aktiv canonical motor och fem runtime-mål i projektroten; dokumentation, hygiene och slutverifiering återstår.**

## Varför migrationen inte är färdig

Aktiva `gpt-project.yaml` använder nu `modular_skills`, fem runtime-mål och
`custom_gpt.enabled: false`. CI och release-workflow installerar originalmotorn
1.6.33. Både push och PR var gröna vid aktiveringscommit `741e3c7`.
Dokumentation och äldre skript måste granskas, och ingen release är gjord.

## Verifierat inom migrationsspåret

- Canonical `core.md` och tre ansvarsmässigt separerade Skills finns.
- Originalmotorn 1.6.33 laddas versionsbundet och klarar sitt självtest.
- Motorns installation, byggning och distributionsvalidering passerar i isolerad kopia.
- Fem distributioner byggs: Chat, Plugin, Claude Projects, Claude Skills och OpenCode.
- Paketerade resurser, Knowledge, tillståndsövergångar och grundläggande runtimekontrakt valideras deterministiskt.
- De gamla testerna körs fortfarande mot legacy-läget och ska inte ses som bevis för den nya aktiva byggkedjan.
- Preflightens installation/build/validate/innehållskontroll är nu en **blockerande CI-gate**, inte bara loggad diagnostik.

## Återstående arbete

1. **Hygiene och dokumentation:** README, PROJECT, STATUS, utvecklingsplan och
   migrationschecklista ska visa aktiva fem runtimes och korrekt status. Gamla
   skript ska inventeras, och bara tas bort efter verifierad funktionsersättning.
2. **Slutverifiering:** Kontrollera domän- och canonical-validering, genererade
   projekt- och runtime-ZIP, motorversion, bruten filreferens och workflow-paritet.
3. **Merge/release:** Efter grön slutgate bedöm merge av PR #7 och eventuell
   release utan att blanda ihop domänversion 1.0.0 och motorversion 1.6.33.

## Skilj på verifieringsnivåer

**Grönt i projektets aktiva CI** betyder att originalmotorn kan bygga och validera fem distributioner från den aktiva konfigureringen. Det bevisar inte att Plugins/Claude har exekveringsbehörighet i användarens host eller att full funktionell hostparitet är uppnådd.

Historisk aktiveringsprovning (`307521a`) gav 188 PASS och 5 FAIL i legacy-tester
som fortfarande förutsatte gamla runtime-listan. Vi ska därför utföra
en samordnad aktivering av både projektkonfiguration och CI/testprofil,
inte enbart slå om `instructions.mode`.

Nästa konkreta steg: **genomför hygiene-/legacyinventering och slutverifiering på PR #7 före merge.**
