# Repository Fixer

## Syfte

Repository Fixer är ett GPT-projekt för kvalitetsgranskning och kontrollerad upprustning av källkodsrepositoryn.

Det ska kunna arbeta med två ingångar:

- komplett repository som ZIP-fil
- GitHub-repository via länk

Den primära leveransen är först en analys och en åtgärdsplan. Faktiska ändringar sker därefter endast när användaren väljer att genomföra respektive steg.

## V1-omfång

V1 fokuserar på README och övrig Markdown-dokumentation, LICENSE, repository hygiene, bygg- och testkonfiguration, GitHub Actions, versions-/verktygsinkonsekvenser och slutverifiering.

## Distributioner

Projektets aktiva byggkedja använder **GPT Byggaren Engine 1.6.33** och fem jämställda distributionsmål:

- Chat ZIP
- OpenAI Plugin – Skills-first, med beroende av hostens skrivbara/persistenta workspace och kompatibel exekvering
- Claude Projects – instruktioner och Knowledge, reducerad lokal verktygsexekvering
- Claude Skills – paketerade Skills och tillhörande resurser
- OpenCode – workspace-baserad distribution

Historisk Custom GPT är inaktiverad och inte en sjätte runtime. `canonical/core.md` samt tre separata Skills är aktiva källor. Version 1.0.0 betecknar domänreleasen, inte byggmotorns version. Migrations-PR #7 är ännu inte mergad eller releasad.

## Profil

`zip_first_advanced`

## Styrande principer

- Analys före ändring.
- Evidens före antaganden.
- Minimum necessary change.
- Mänskligt beslut när det behövs.
- Verifiera efter ändring.
- ZIP-arbete ska ge tillbaka en komplett uppdaterad ZIP.
- GitHub-arbete ska använda en kontrollerad branch/PR-process.
