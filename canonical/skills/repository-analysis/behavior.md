# Repository Analysis – canonical Skill-beteende

## Repository-inventering

Börja en full analys med en konservativ inventering av rotfiler, byggmanifest, lockfiler, moduler, containerkonfiguration och CI. Följ `repository-inventory.md`: varje stack-/projekttypspåstående ska ha observerbar evidens, konflikter ska redovisas och okänd teknik ska förbli okänd.

## Fullständig analys och completeness-gate

En första inventering är inte samma sak som en full analys. Följ `analysis-completeness.md`.

Analysera minst, när relevant: repositorystruktur/stack, README, övrig Markdown, LICENSE/licensreferenser, `.gitignore` och hygiene, temporära/genererade/överflödiga filer, lockfiler/package manager, build, tester, GitHub Actions, runtime-/verktygsversioner, Docker/Compose, konfiguration/miljövariabler, uppenbara checkade-in secrets, manifest/dependency-inkonsistenser, döda scripts/config och releasekonfiguration.

En full analys får inte markeras komplett förrän varje relevant kontrollområde är `checked`, `not-applicable` eller tydligt `not-verified`. `partial` och `not-checked` betyder att analysen är ofullständig. Begränsa aldrig den fullständiga fyndlistan till de viktigaste fyra eller fem fynden. Sammanfattningen får prioritera, men alla identifierade öppna fynd ska bevaras.

LICENSE-kontrollen ska alltid ge ett synligt resultat. Om varken licensfil eller licensreferens finns ska ett explicit **Överväg**-fynd skapas; du ska inte själv välja eller ersätta licens.

Om full analys inte ryms i aktuell körning: bevara fynd och stabila ID:n, markera analysen ofullständig och ange återstående kontrollområden. Fortsätt därifrån i nästa analysomgång. Slutlig fix-plan skapas normalt först när analysen är komplett. Om användaren vill börja tidigare får planen märkas preliminär.

## `repository-analysis.md`

Rapporten ska minst innehålla projektsammanfattning/detekterad stack, analysstatus komplett/ofullständig, kontrollöversikt, klassificerade fynd, konkret evidens per negativt fynd, godkända kontroller, build/test-verifiering, osäkerheter/begränsningar och rekommenderat nästa steg.

Använd fyndklasserna:

- **Bör åtgärdas** – konkret fel, saknad viktig information eller verifierad inkonsistens
- **Rekommenderas** – tydlig kvalitetsförbättring utan att vara direkt fel
- **Överväg** – projekt- eller preferensberoende förbättring
- **Godkänd kontroll** – området har faktiskt granskats och ser rimligt ut

Följ `finding-model.md`, `repository-finding.schema.json` och `analysis-report.md`. Sätt inte radnummer du inte känner till. Behåll fynd-ID stabila genom analys, plan, progress och slutrapport.
