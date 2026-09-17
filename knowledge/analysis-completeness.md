# Fullständig repository-analys

Repository Fixer ska skilja mellan **inventering**, **fyndinsamling** och **planering**. En snabb första inventering får vara grund, men en full analys får inte avslutas efter ett godtyckligt litet antal fynd.

## Complete-findings rule

En full analys är komplett först när varje relevant kontrollområde har status `checked`, `not-applicable` eller `not-verified`. `partial` och `not-checked` betyder att analysen fortfarande är ofullständig.

Begränsa aldrig den fullständiga fyndlistan till de viktigaste fyra eller fem fynden. Sammanfattningen får lyfta de viktigaste problemen, men `repository-analysis.md` ska behålla **alla identifierade öppna fynd** och alla utförda godkända kontroller.

Planering får inte användas som en genväg för att avsluta fyndinsamlingen. `repository-fix-plan.md` ska normalt skapas först när analysen är komplett.

## Obligatorisk kontrollmatris

Kontrollera minst följande områden när de är relevanta för repositoryt:

1. repositorystruktur, projekttyp, moduler och teknikstack
2. README: syfte, prerequisites, build, lokal körning, tester, konfiguration, portar och kommandon
3. övrig Markdown-dokumentation mot faktisk implementation och konfiguration
4. LICENSE/licensstatus och licensreferenser i dokumentationen
5. `.gitignore` och repository hygiene
6. temporära, genererade, gamla eller sannolikt överflödiga filer
7. package-manager- och lockfilskonsistens
8. buildkonfiguration och buildkommandon
9. testkonfiguration, teststruktur och testkommandon
10. GitHub Actions och faktisk build-/testtäckning
11. runtime-, verktygs- och package-manager-versioner
12. Docker/Compose och annan tydlig container-/runtimekonfiguration
13. konfigurationsfiler, exempelkonfiguration och dokumenterade miljövariabler
14. uppenbara secrets/credentials eller lokala hemligheter som råkat versionshanteras, utan att expandera till en full säkerhetsrevision
15. dependency-/manifestinkonsistenser som kan beläggas från repositoryt
16. uppenbart döda eller föråldrade scripts/config-filer när evidensen är tillräcklig
17. interna fil-, script- och länkreferenser i dokumentationen
18. versions-/releasekonfiguration när repositoryt faktiskt använder releaseflöden

Ett område som inte är relevant ska markeras `not-applicable`; det får inte bara hoppas över. Ett område som inte kan verifieras i aktuell miljö ska markeras `not-verified` eller motsvarande tydligt redovisad begränsning.

## Särskilt om LICENSE

LICENSE-kontrollen ska alltid lämna ett synligt resultat. Om ingen licensfil eller licensreferens finns ska det skapas ett explicit fynd av typen `Överväg`; frånvaron får inte försvinna bara för att den inte automatiskt är ett fel. Repository Fixer får fortfarande inte välja licens åt användaren.

## Analysmättnad och flera promptar

För stora repositoryn kan full analys kräva flera användarpromptar. I så fall:

1. bevara redan identifierade fynd och deras stabila ID:n,
2. markera analysen som ofullständig,
3. redovisa vilka kontrollområden som återstår eller endast är delvis granskade,
4. fortsätt nästa analysomgång från dessa områden i stället för att börja om,
5. skapa inte en slutlig fix-plan förrän analysen är komplett, om inte användaren uttryckligen väljer att börja arbeta från en preliminär plan.

När en fortsatt analys kräver en ny prompt ska användaren få ett enkelt val: **Fortsätt leta efter fler fynd** eller **Börja åtgärda den preliminära planen**. Rekommendera fortsatt analys när målet uttryckligen är en fullständig repository-genomgång.

## Fasmedvetet "Gör nästa steg"

Tolka kommandot utifrån aktuell fas:

- analys ofullständig -> fortsätt med nästa `partial`/`not-checked` kontrollområde,
- analys komplett men fix-plan saknas -> skapa den kompletta fix-planen,
- fix-plan finns -> följ ordinarie interaktiva stegkontroll,
- alla relevanta plansteg är avslutade -> gör ny full analys och slutrapport enligt slutverifieringsreglerna.

Detta gör att användaren kan fortsätta med samma kommando utan att Repository Fixer hoppar från en ofullständig analys direkt till implementation.
