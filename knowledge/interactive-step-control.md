# Interaktiv stegkontroll

Repository Fixer ska styra arbetet från faktisk analys-, plan- och progressstatus, inte genom att mekaniskt öka ett stegnummer.

## Fasmedveten nästa åtgärd

`Gör nästa steg` ska först avgöra vilken fas arbetet befinner sig i:

1. om fullanalysen är ofullständig: fortsätt med nästa `partial`/`not-checked` kontrollområde enligt `analysis-completeness.md`,
2. om fullanalysen är komplett men slutlig fix-plan saknas: skapa `repository-fix-plan.md` från samtliga öppna fynd,
3. om fix-plan finns: använd den ordinarie stegkontrollen nedan,
4. om alla relevanta plansteg är avslutade: erbjud/gör ny full analys och slutrapport enligt slutverifieringsreglerna.

Hoppa inte från en ofullständig analys direkt till implementation bara för att några fynd redan har hittats. Om användaren uttryckligen väljer att börja från en preliminär plan får det ske, men planen och statusen ska då tydligt beskrivas som preliminära.

## Tillstånd i åtgärdsfasen

Varje plansteg har ett av tillstånden `planned`, `in-progress`, `completed`, `skipped` eller `blocked`. Ett steg får bara startas när dess beroenden är `completed` och alla obligatoriska beslutspunkter är lösta. Ett misslyckat genomförande eller verifiering blockerar steget tills problemet hanterats.

## Före ett steg

Visa kort:

- mål och varför steget behövs
- planerade ändringar och sannolikt berörda filer
- risk
- eventuella blockerare och beslut
- användarens val: **Gör steget**, **Hoppa över**, **Visa mer detaljer**, **Ändra förslaget**

Om ett verkligt beslut krävs, exempelvis licensval, ska beslutet lösas uttryckligen innan steget får starta.

## Nästa steg i åtgärdsfasen

När en fix-plan finns ska `Gör nästa steg`:

1. återuppta ett redan `in-progress`-steg före nytt arbete,
2. annars välja första genomförbara plansteget vars beroenden och beslut är lösta,
3. hoppa förbi blockerade steg om ett senare oberoende steg kan genomföras säkert,
4. begära beslut först när inget annat säkert plansteg kan genomföras,
5. redovisa blockerare om återstående arbete inte kan fortsätta.

Ett `skipped` steg ska sparas med orsak och tas med i slutrapporten. Ett steg som beror på ett hoppat steg blir inte automatiskt godkänt; beroendet måste hanteras eller planen justeras.

## Ändra förslaget

En ändringsinstruktion sparas som override för steget. Den får inte kringgå olösta beslut eller beroenden. Om en tidigare exekvering blockerats kan en relevant ändring återställa steget till planerat läge, men det måste verifieras på nytt när det körs.

## Efter genomförande

Markera inte steget `completed` förrän ändringen är genomförd och rimlig verifiering har registrerats som `verified` eller `not-verified`. Vid faktiskt fel används `failing` och steget förblir blockerat. `not-verified` betyder endast att verifieringen inte kunde utföras; det är inte samma sak som PASS.

Progress ska kunna uttryckas enligt `repository-progress.schema.json` så ZIP-läget senare kan bära samma status i `.repository-fixer/progress.md`/maskinläsbar motsvarighet och GitHub-läget kan använda samma logik över flera commits/PR:er.
