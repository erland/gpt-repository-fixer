# Analysrapport

`repository-analysis.md` är Repository Fixers första obligatoriska användarartefakt. Den ska vara användbar även när användaren inte vill genomföra några ändringar.

Följ även `analysis-completeness.md`. En snabb första inventering är inte samma sak som en full analys.

## Rapportprinciper

- Rapportera vad som faktiskt har kontrollerats, inte bara problem.
- Separera `Bör åtgärdas`, `Rekommenderas`, `Överväg` och `Godkänd kontroll`.
- Visa konkret evidens under varje negativt fynd. Undvik radnummer som inte är verifierade.
- Behåll fynd-id oförändrade så att nästa plan och slutrapport kan referera till samma fynd.
- Redovisa build/test som `verified`, `failing` eller `not-verified`. `not-verified` får aldrig formuleras som ett misslyckande.
- Redovisa osäkerheter och områden som inte kunde kontrolleras.
- Sammanfattningen ska prioritera faktiska problem framför kosmetiska förbättringar men får inte dölja godkända kontroller eller öppna fynd.
- Begränsa aldrig den fullständiga fyndlistan till de viktigaste fyra eller fem fynden. Alla identifierade öppna fynd ska finnas kvar i rapporten.
- Rapporten ska uttryckligen ange om analysen är **komplett** eller **ofullständig**.
- En full analys får inte markeras komplett så länge ett relevant kontrollområde är `partial` eller `not-checked`.
- Rapporten ska bara rekommendera att slutlig `repository-fix-plan.md` skapas när analysen är komplett. Om analysen är ofullständig ska nästa steg normalt vara fortsatt fyndinsamling.

## Kontrollöversikt och completeness-gate

Kontrollöversikten ska täcka kontrollmatrisen i `analysis-completeness.md`. Varje relevant område ska ha en uttrycklig status, exempelvis:

- `checked` – området har granskats tillräckligt för aktuell fullanalys,
- `partial` – granskning har påbörjats men mer arbete återstår,
- `not-applicable` – området är inte relevant för repositoryt och orsaken bör vara begriplig,
- `not-verified` – området är relevant men kunde inte verifieras i aktuell miljö,
- `not-checked` – området har ännu inte granskats.

`partial` och `not-checked` innebär att analysen är ofullständig. `not-verified` ska redovisas som en begränsning, inte döljas eller behandlas som godkänt.

Om analysen kräver ytterligare en prompt ska rapporten ange vilka områden som återstår och låta nästa analysomgång fortsätta därifrån. Redan identifierade fynd och fynd-ID:n ska bevaras.

## Minimiinnehåll

1. sammanfattning med antal fynd per klass och analysstatus komplett/ofullständig
2. detekterad projekttyp och stack
3. kontrollöversikt för samtliga relevanta kontrollområden
4. fullständig lista över negativa/öppna fynd med evidens och rekommenderad åtgärd
5. godkända kontroller
6. build/test-verifiering
7. begränsningar, `not-verified` och kvarvarande kontrollområden
8. rekommenderat nästa steg utifrån aktuell fas

Om inga negativa fynd finns ska rapporten uttryckligen säga det, men fortfarande redovisa verifieringar, kontrollmatris och begränsningar.

## Nästa steg

- Om analysen är ofullständig: fortsätt analysen och leta efter fler fynd.
- Om analysen är komplett: skapa `repository-fix-plan.md` från **samtliga** öppna fynd.
- Om användaren uttryckligen vill börja innan analysen är komplett får en preliminär plan skapas, men den ska tydligt märkas som preliminär och får inte beskrivas som en total repository-plan.
