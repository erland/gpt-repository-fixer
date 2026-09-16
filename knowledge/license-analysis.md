# LICENSE-analys

Repository Fixer ska kontrollera licensstatus utan att fatta licensbeslut åt användaren.

## Kontrollordning

1. Leta efter toppnivåfiler med standardnamn som `LICENSE`, `LICENSE.txt`, `LICENSE.md`, `LICENCE` eller `COPYING`.
2. Identifiera endast licenstyp när texten ger tillräckligt tydliga standardmarkörer.
3. Jämför identifierad licenstyp med licensangivelse i README.
4. Leta efter tydliga mallfält/placeholders för årtal eller copyright-innehavare.
5. Om licensen saknas, är okänd, motsäger README eller innehåller metadata som måste fyllas i: skapa en explicit användarbeslutspunkt innan någon licensfil skapas eller ändras.

## Klassificering

- README anger en licens men licensfil saknas: **Bör åtgärdas**, eftersom repositoryt är internt inkonsekvent.
- LICENSE och README anger olika licenser: **Bör åtgärdas** och användarbeslut krävs.
- Ingen licens nämns någonstans: **Överväg**. Avsaknaden är inte automatiskt ett fel eftersom projektets avsikt är okänd.
- Okänd/anpassad licenstext: **Överväg** med `medium` confidence; gissa inte.
- Placeholders i licensmetadata: **Rekommenderas** och användarbeslut krävs innan ersättning.
- Identifierbar licens utan motsägelser/placeholders: **Godkänd kontroll**.

## Beslutsregel

Repository Fixer får ge en neutral kort beskrivning av vanliga licensalternativ när användaren behöver fatta beslut, men får inte själv välja licens, copyright-innehavare eller årtal. Ändra inte en befintlig licens bara för att en annan licens skulle kunna vara mer lämplig.
