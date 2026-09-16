# Slutverifiering och final report

Slutverifieringen är en **ny full analys av repositoryts aktuella innehåll**. Progressloggen beskriver vad Repository Fixer försökte göra men är aldrig facit för slutstatus.

## Arbetsordning

1. Läs den ursprungliga `repository-analysis.md`/analysmodellen och progress endast som historik.
2. Inventera det aktuella repositoryt på nytt.
3. Kör samma relevanta README-, Markdown-, LICENSE-, hygiene-, build/test- och GitHub Actions-kontroller på nytt.
4. Bygg en färsk analysmodell innan jämförelse görs.
5. Jämför ursprungliga negativa fynd mot den färska analysen. Matcha stabilt fynd-ID först; använd bara konservativ area/titel/evidens-matchning om ID har ändrats.
6. Klassificera resultat som löst, kvarstående eller nytt utifrån färsk observation. Ett plansteg markerat `completed` bevisar inte att fyndet är löst.
7. Redovisa hoppade/avvisade fynd separat som arbetshistorik och ange om de fortfarande observeras.
8. Skapa `repository-final-report.md`.

## Viktiga regler

- Ett ursprungligt fynd är **löst** när motsvarande problem inte längre observeras i den nya analysen.
- Ett fynd är **kvarstående** när samma problem fortfarande observeras, även om progress säger `completed`.
- Ett **nytt fynd** är ett negativt fynd i slutanalysen som inte konservativt kan matchas mot ett ursprungligt fynd.
- Ett hoppat fynd kan samtidigt vara löst eller kvarstående; rapportera både historiken och aktuell observation.
- Build/test ska tas från färsk verifiering och behålla `verified`, `failing` eller `not-verified`.
- README, dokumentation, LICENSE, GitHub Actions och hygiene får bara få PASS om området faktiskt kontrollerats och inga negativa fynd återstår där.
- Om ett område inte kunde kontrolleras ska det vara `partial` eller `not-checked`, aldrig PASS.
- Behåll begränsningar och osäkerheter från den färska analysen.

## Output

Slutrapporten ska minst visa initiala fyndantal, lösta fynd, hoppade/avvisade fynd, kvarstående fynd, nya fynd, build/test-status, status för README/dokumentation/LICENSE/GitHub Actions/hygiene och kvarstående begränsningar eller rekommendationer.
