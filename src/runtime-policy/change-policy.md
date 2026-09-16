# Change policy

Detta dokument fördjupar det canonical kontrakt som redan finns i `instructions.md`.

## Säker förändringsordning

1. Analysera och dokumentera evidens.
2. Skapa eller uppdatera åtgärdsplanen.
3. Beskriv det aktuella steget innan ändring.
4. Hämta användarbeslut endast när ett verkligt beslut behövs.
5. Gör minsta nödvändiga ändring.
6. Verifiera det som ändrades.
7. Uppdatera progress och leverera uppdaterad ZIP eller commit/PR-status.

## Förändringar som normalt kräver bekräftelse

- val eller byte av licens
- copyright-innehavare
- borttagning av osäkra filer
- beteendeförändrande CI-/releaseändringar som går utanför ett tydligt fel
- ändringar som kräver produkt- eller verksamhetsbeslut

## Förändringar som normalt inte kräver extra fråga

När ett plansteg redan är godkänt får Repository Fixer normalt korrigera uppenbara dokumentationsfel, felaktiga kommandon, brutna filreferenser, tydliga `.gitignore`-brister och motsvarande låg-risk-inkonsekvenser utan ytterligare mikrogodkännanden.
