# Analysrapport

`repository-analysis.md` är Repository Fixers första obligatoriska användarartefakt. Den ska vara användbar även när användaren inte vill genomföra några ändringar.

## Rapportprinciper

- Rapportera vad som faktiskt har kontrollerats, inte bara problem.
- Separera `Bör åtgärdas`, `Rekommenderas`, `Överväg` och `Godkänd kontroll`.
- Visa konkret evidens under varje negativt fynd. Undvik radnummer som inte är verifierade.
- Behåll fynd-id oförändrade så att nästa plan och slutrapport kan referera till samma fynd.
- Redovisa build/test som `verified`, `failing` eller `not-verified`. `not-verified` får aldrig formuleras som ett misslyckande.
- Redovisa osäkerheter och områden som inte kunde kontrolleras.
- Sammanfattningen ska prioritera faktiska problem framför kosmetiska förbättringar men får inte dölja godkända kontroller.
- Rapporten ska avslutas med att rekommendera att `repository-fix-plan.md` skapas; den ska inte börja göra ändringar.

## Minimiinnehåll

1. sammanfattning med antal fynd per klass
2. detekterad projekttyp och stack
3. kontrollöversikt
4. negativa/öppna fynd med evidens och rekommenderad åtgärd
5. godkända kontroller
6. build/test-verifiering
7. begränsningar och osäkerheter
8. rekommenderat nästa steg

Om inga negativa fynd finns ska rapporten uttryckligen säga det, men fortfarande redovisa verifieringar och begränsningar.
