# {{GPT_NAME}} – OpenAI Plugin

Version: {{VERSION}}

Denna skills-first-distribution innehåller tre Skills: `repository-analysis`, `repository-remediation` och `repository-verification`. Python-skript och rapportmallar ligger i respektive Skills `scripts/` och `assets/`.

## Installation och användning

Installera ZIP-paketet i en kompatibel ChatGPT/Plugin-miljö. Skill-skripten är resurser som kan köras **om hosten stöder Python och nödvändiga filsystemsrättigheter**. Ingen MCP-server eller automatiskt registrerad exekveringsfunktion ingår. GitHub-skrivning är alltid beroende av separat verifierad behörighet.

## Tolkning av runtimekontraktet

`runtime-contract.json` innehåller två olika nivåer av krav:

- `capabilities.requirements.code_execution.level: required` beskriver vad **hela Repository Fixers funktionella arbetsflöde** kräver för full paritet.
- `adapter.runtime_requirements.code_execution.level: not_required` beskriver endast **deklarerade tool-script-integrationer**. Inga sådana tools deklareras i denna version, så fältet betyder inte att de medföljande Skill-skripten kan köras utan Python.
- `adapter.script_resources.packaged: []` inventerar endast deklarerade tool-script-integrationer, **inte** Python-filerna under `skills/*/scripts/`. Se faktiska ZIP-filer för dessa resurser.

Hostmiljöer utan kodexekvering kan använda instruktioner och referenser men får inte påstå att deterministiska skript körts eller att full funktionalitet verifierats.

## Begränsningar

Plugin v1 genererar inte MCP-servrar, UI-komponenter, lifecycle hooks eller marketplace-metadata. Skill-skript kräver kompatibel hostexekvering och eventuella Python-beroenden.
