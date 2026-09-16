# {{GPT_NAME}} – Custom GPT-distribution

Detta paket innehåller Builder-underlaget för **{{GPT_NAME}}**.

## Installera

1. Öppna GPT Builder och skapa en ny GPT.
2. Klistra in hela `builder/instructions.md` som Instructions.
3. Lägg in innehållet i `builder/conversation-starters.md` som conversation starters.
4. Aktivera capabilities enligt `builder/capabilities.md` och kontrollera `builder/capabilities.json`.
5. Ladda upp **alla** filer i `builder/knowledge-package/` som Knowledge.
6. Läs `COMPATIBILITY.md` innan GitHub-skrivflöde aktiveras.
7. Testa minst ett ZIP-repository och ett läsbart GitHub-repository innan publicering.

## Viktigt om GitHub

Publik/läsbar GitHub-kod kan analyseras när GPT:n har webbtillgång eller annan läskapabilitet. Branch, commit och PR kräver däremot en separat autentiserad GitHub-integration/Action med skrivbehörighet. Utan den ska GPT:n arbeta read-only och aldrig simulera en skapad PR.

## Distribuerade filer

- `builder/instructions.md` – canonical kärnkontrakt anpassat till Builder-gränsen.
- `builder/knowledge-package/` – analys- och workflowregler.
- `builder/capabilities.md` – mänsklig capability-konfiguration.
- `builder/capabilities.json` – maskinläsbar capability-profil.
- `builder/compilation-report.json` – verifierar instruktionens storlek och Knowledge-urval.
- `COMPATIBILITY.md` – faktisk paritet och plattformsbegränsningar mot Chat ZIP.

## Version

{{VERSION}}
