# {{GPT_NAME}} – OpenCode-distribution

Detta paket är en basruntime för OpenCode.

## Användning

1. Packa upp ZIP-filen som ett OpenCode-workspace för GPT Byggaren.
2. Öppna workspace-roten i OpenCode.
3. OpenCode läser root `AGENTS.md` som projektinstruktion.
4. Lägg det GPT-projekt som ska analyseras eller ändras som en underkatalog i workspace, exempelvis `project/`, eller använd en annan relativ sökväg från workspace-roten.
5. När ett genererat GPT Byggaren-tool körs mot ett målprojekt, ange `projectRoot` för målprojektet, exempelvis `project`. Om `projectRoot` utelämnas används workspace-roten.
6. `.opencode/runtime-contract.json` dokumenterar hur adaptern realiserar canonical kontrakt.
7. `knowledge/` innehåller portabelt referensmaterial som agenten kan läsa vid behov.

## Viktigt om målprojektet

OpenCode-ZIP:en är GPT Byggarens runtime, inte det GPT-projekt som ska bearbetas. Runtimepaketet innehåller därför inte automatiskt målprojektets `gpt-project.yaml`, `project-status.yaml` eller övriga canonical projektfiler.

Tools som `gpt_lint_project`, `gpt_recommend_next_step`, `gpt_project_hygiene`, `gpt_build_distributions` och `gpt_validate_distributions` arbetar mot den katalog som anges med `projectRoot`.

## Avgränsning i denna version

- Återanvändbara Skills finns under `.opencode/skills/` och laddas av OpenCode vid behov.
- Canonical runtime-tools finns som projektlokala custom tools under `.opencode/tools/`.
- `opencode.json` styr godkännande för muterande respektive icke-muternade tools.
- `CLAUDE.md` används inte; OpenCode V2 använder `AGENTS.md` för projektinstruktioner.

## Version

{{VERSION}}
