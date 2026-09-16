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

Projektet genererar två jämbördiga runtime-distributioner från samma canonical kontrakt:

- Chat ZIP
- Custom GPT

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
