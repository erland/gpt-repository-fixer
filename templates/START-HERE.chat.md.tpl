# {{GPT_NAME}} – Chat ZIP

Den här ZIP-filen är den portabla Chat-runtime-distributionen för **{{GPT_NAME}}**.

## Starta i en ny konversation

1. Bifoga denna ZIP i en ny ChatGPT-konversation.
2. Skriv exempelvis: `Använd denna zip som GPT i denna konversation`.
3. Ge därefter Repository Fixer ett källkodsrepository som ZIP eller GitHub-länk.

`assistant/instructions.md` är det canonical runtimekontrakt som ska följas. Knowledge, policies, schemas, scripts och templates i ZIP-filen är stödmaterial för samma beteende.

## Första analysen

Repository Fixer ska analysera repositoryt innan ändringar görs och producera två nedladdningsbara Markdown-filer:

- `repository-analysis.md` – evidensbaserad analys av repositoryts skick.
- `repository-fix-plan.md` – stegvis plan för de öppna fynd som bör eller kan åtgärdas.

Analysen ska använda repositoryts faktiska innehåll som evidens och tydligt skilja mellan verifierade fel, rekommendationer, överväganden och godkända kontroller.

## ZIP-arbetsflöde och återupptagning

När källkoden lämnas som ZIP arbetar Repository Fixer i en separat arbetskopia och kan lägga portabel status i `.repository-fixer/`, bland annat analys, plan och progress. Efter ett genomfört steg ska hela det uppdaterade repositoryt kunna lämnas tillbaka som en ny ZIP.

Om en senare uppladdad repository-ZIP redan innehåller `.repository-fixer/` ska Repository Fixer läsa den statusen och **återuppta** arbetet där det slutade i stället för att anta att planen börjar om från början.

## GitHub-läge

En publik GitHub-länk kan analyseras när repositoryinnehållet kan läsas. Skrivande GitHub-flöden, såsom branch, commit och PR, kräver att den aktuella ChatGPT-miljön faktiskt har verifierad GitHub-skrivåtkomst. Utan sådan åtkomst ska analys och plan fortfarande fungera, men Repository Fixer får inte låtsas att en PR har skapats.

## Viktiga delar

- `assistant/instructions.md` – runtimeinstruktion och kärnkontrakt
- `assistant/policies/` – fördjupade runtimepolicies
- `knowledge/` – analys- och workflowregler
- `schemas/` – maskinläsbara modeller
- `scripts/` – deterministiska analys-, rapport- och workflowhjälpare
- `templates/` – mallar för rapport, plan, progress och slutrapport

## Version

{{VERSION}}

## Entry point

Detta dokument är den mänskliga entrypointen. `MANIFEST.json` beskriver distributionens maskinläsbara innehåll.
