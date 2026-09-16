# Ändringsverifiering per plansteg

Verifiering är en separat fas efter att ett godkänt plansteg har ändrat repositoryt. Ett steg får inte betraktas som lyckat enbart för att filer kunde skrivas.

## Minimikrav

Granska alltid faktisk diff. Välj sedan relevanta kontroller utifrån ändringen:

- **diff-review** – kontrollera att ändringen motsvarar godkänt steg och `Minimum necessary change`.
- **syntax-config** – parse/validera ändrade konfigurationsfiler och workflows där det går deterministiskt.
- **build** – kör relevant build när källkod/buildkonfiguration ändrats eller planen kräver det.
- **tests** – kör relevanta tester när kod ändrats eller planen kräver det.
- **docs-consistency** – kontrollera dokumentation mot nuvarande implementation när Markdown ändrats eller dokumentationsfynd åtgärdats.
- **deleted-references** – kontrollera att borttagna filer inte fortfarande refereras.

Alla kontrollresultat ska uttryckas som `verified`, `failing` eller `not-verified`. Att en kontroll inte går att köra är `not-verified`, aldrig automatiskt `verified` eller `failing`.

## Resultatregler

- Minst ett `failing` ger steget verifieringsstatus `failing` och blockerar slutförande/fortsättning tills felet hanterats.
- Inga fel men minst ett relevant `not-verified` ger `not-verified`; ange exakt vad som inte kunde verifieras och varför.
- Endast när alla relevanta kontroller är verifierade blir status `verified`.
- Ett utfört frivilligt verifieringstest som faktiskt failar är en regressionssignal även om det inte var ett minimikrav.

## Korrigering före nästa ordinarie steg

Om verifieringen failar ska problemet analyseras och en minimal korrigering av samma plansteg prioriteras före nästa ordinarie steg. Expandera inte korrigeringen till orelaterad refaktorering. Uppdatera progress först efter ny verifiering.

## Diff-scope

`likely_files` i planen är vägledning, inte en garanti. Filer utanför angivet scope kräver explicit diff-granskning och ska inte automatiskt kallas fel. Ingen faktisk diff för ett steg som påstås vara genomfört är däremot en verifieringssignal som ska behandlas som fel.
