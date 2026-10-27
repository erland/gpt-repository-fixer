# {{GPT_NAME}} – OpenCode-distribution

Detta paket är en fristående OpenCode-runtime för **Repository Fixer**, inte en GPT Byggaren-utvecklingsmiljö.

## Användning

1. Packa upp ZIP-filen i en arbetskatalog och öppna katalogen i OpenCode.
2. Läs `AGENTS.md`, som innehåller Repository Fixers instruktioner.
3. Ge agenten ett repository som ZIP, en tillgänglig GitHub-länk eller en lokal katalog att analysera.
4. Repository Fixers tre Skills finns under `.opencode/skills/`. Deras Python-resurser finns i respektive Skills `scripts/`, och rapportmallar i `assets/`.
5. Begär analys och åtgärdsplan innan några ändringar görs. Skrivande GitHub-arbete kräver separat verifierad behörighet.

## Verktyg och förutsättningar

Denna distribution deklarerar **inga projektlokala OpenCode custom tools**. Katalogen `.opencode/tools/` och GPT Byggaren-verktyg som `gpt_build_distributions` ingår därför inte.

Skill-skripten är återanvändbara Python-resurser, **inte automatiskt registrerade OpenCode-tools**. De kan köras om hosten erbjuder Python, filsystemsåtkomst och nödvändiga beroenden. Om exekvering saknas ska agenten redovisa vad som inte verifierats, inte påstå att ett skript har körts.

`.opencode/runtime-contract.json` beskriver runtimekontraktet. `opencode.json` är OpenCode-konfigurationen. `knowledge/` innehåller referensmaterial.

## Version

{{VERSION}}
