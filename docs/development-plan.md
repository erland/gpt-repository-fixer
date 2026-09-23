# Repository Fixer – Development Plan

**Projekt:** Repository Fixer  
**Profil:** `zip_first_advanced`  
**Schema:** 1  
**Status:** Planerad  

## 1. Syfte och målbild

Repository Fixer ska kunna ta emot ett källkodsrepository som ZIP-fil eller GitHub-länk, analysera repositoryts skick och producera två primära artefakter:

- `repository-analysis.md` – evidensbaserad analys av brister och kontroller som passerat.
- `repository-fix-plan.md` – prioriterad steg-för-steg-plan för hur en LLM kan åtgärda problemen.

Efter analysen ska användaren frivilligt kunna gå vidare med åtgärderna ett steg i taget. Varje steg ska först förklaras och användaren ska kunna genomföra, hoppa över eller justera steget. Beslut som inte rimligen bör tas automatiskt, exempelvis val av licens och copyright-innehavare, ska kräva användarens bekräftelse.

Vid ZIP-input ska Repository Fixer lämna en uppdaterad komplett ZIP efter genomförda ändringar. Vid GitHub-input ska ändringar göras i en arbetsbranch och PR. Samma öppna PR återanvänds tills den mergas; om den är mergad skapas en ny branch/PR innan ytterligare ändringar görs.

## 2. Styrande principer

1. **Analys före ändring.** Inga korrigeringar görs innan analys och fix-plan finns.
2. **Evidens före antaganden.** Fynd ska kopplas till konkreta filer, konfigurationer eller observerade inkonsekvenser.
3. **Minimum necessary change.** Repository Fixer ska inte utföra orelaterad refaktorering eller beteendeförändringar.
4. **Mänskligt beslut när det behövs.** Osäkra borttagningar, licensval och andra verksamhets-/juridiska val ska bekräftas av användaren.
5. **Verifiera efter ändring.** Relevanta builds, tester och statiska kontroller ska köras när miljön tillåter.
6. **Ett naturligt steg per commit i GitHub-läget.** Detta ska göra PR:en lätt att granska och återställa.
7. **Portabel status i ZIP-läget.** Pågående analys, plan och progress ska kunna följa med repository-ZIP:en.
8. **Slutverifiering från början.** Efter genomförda steg ska repositoryt analyseras på nytt, inte bara antas vara korrigerat.

## 3. V1 – analysomfång

Version 1 ska kontrollera minst följande områden:

- repositorystruktur och projekttyp/teknikstack
- README.md och dess relevans för projektet
- Markdown-dokumentation kontra faktisk implementation och konfiguration
- LICENSE och inkonsekvenser mellan licensfil och dokumentation
- `.gitignore` och repository hygiene
- sannolikt temporära, gamla eller överflödiga arbetsfiler
- build-konfiguration
- testkonfiguration och möjlighet att köra tester
- GitHub Actions för build och test
- uppenbara inkonsekvenser i runtime-/verktygsversioner
- slutverifiering och kvarstående fynd

Fördjupad dependency modernization, generell säkerhetsskanning, release automation, CODEOWNERS, CONTRIBUTING, SECURITY.md, Dependabot/Renovate och omfattande Docker-optimering är möjliga senare utbyggnader men ska inte blockera v1.

---

# Utvecklingssteg

## Steg 1 – Skapa projektets canonical grundstruktur

**Mål:** Skapa ett komplett GPT-projekt med canonical source, projektmetadata, status och utvecklingsplan.

**Varför nu:** Alla senare distributioner och tester behöver en gemensam källa och spårbar projektstatus.

**Output:**
- `gpt-project.yaml`
- `project-status.yaml`
- `PROJECT.md`
- `STATUS.md`
- `README.md`
- `docs/development-plan.md`
- canonical katalogstruktur för instruktioner, policies, schemas, templates och tester

**Validering:**
- projektstrukturen följer GPT Byggarens projektkonventioner
- utvecklingsplanen finns i projektet
- projektstatus anger nästa planerade steg

**Hygiene:**
- inga genererade distributionsfiler blandas med canonical source
- inga onödiga temporära filer inkluderas

**Klart när:**
- projektet kan byggas till en komplett projekt-ZIP
- status och plan pekar på steg 2

---

## Steg 2 – Definiera canonical beteende- och capability-kontrakt

**Mål:** Specificera exakt vad Repository Fixer ska och inte ska göra.

**Output:**
- canonical systeminstruktion
- capability-kontrakt för ZIP, GitHub, filgenerering och verifiering
- policy för `minimum necessary change`
- policy för osäkra/riskfyllda förändringar

**Viktiga beteenden:**
- analys före fix
- evidensbaserade fynd
- inga automatiska licensbeslut
- inga osäkra filborttagningar utan godkännande
- inga orelaterade kodrefaktoreringar
- kontroll av aktuell PR-status före GitHub-ändring

**Tester:**
- instruktionstest för att GPT:n inte börjar ändra repositoryt direkt
- test att en fråga endast ställs när ett verkligt användarbeslut krävs

**Klart när:**
- samma canonical kontrakt kan användas för både Chat ZIP och Custom GPT
- centrala säkerhets- och arbetsflödesregler inte kräver knowledge-fil för att fungera

**Beror på:** Steg 1

---

## Steg 3 – Definiera repository-inventering och projekttypdetektion

**Mål:** Ge Repository Fixer en konsekvent första passering av ett okänt repository.

**Output:**
- schema för repository inventory
- regler för stack-/projekttypdetektion
- analyschecklista för rotfiler, kataloger, buildfiler och CI

**Detektion bör omfatta exempelvis:**
- språk
- frontend/backend/monorepo/library/documentation project
- React/Vite/Node/pnpm/npm/yarn
- Java/Maven/Gradle/Quarkus/Spring
- Python
- Go
- Rust
- Docker/Docker Compose
- GitHub Actions

**Validering:**
- testprojekt med olika stackar klassificeras rimligt
- okända stackar leder till generell analys, inte fabricerade antaganden

**Klart när:**
- inventeringen kan beskriva projektets relevanta struktur och tekniska byggblock

**Beror på:** Steg 2

---

## Steg 4 – Definiera fyndmodell, evidens och allvarlighetsnivåer

**Mål:** Göra analyserna konsekventa, begripliga och spårbara.

**Output:**
- schema för analysfynd
- klassificering av fynd
- evidensmodell med filreferens och observation

**Fyndklasser:**
- **Bör åtgärdas** – konkret fel, saknad kritisk information eller verifierad inkonsistens
- **Rekommenderas** – tydlig kvalitetsförbättring utan att vara ett direkt fel
- **Överväg** – projekt-/preferensberoende förbättring
- **Godkänd kontroll** – område har kontrollerats och ser rimligt ut

**Klart när:**
- varje negativt fynd kräver konkret evidens
- rapporten även kan visa kontroller som passerat

**Beror på:** Steg 3

---

## Steg 5 – Implementera README-analys

**Mål:** Bedöma om README beskriver det faktiska projektet och ger relevant användarinformation.

**Kontroller:**
- vad projektet gör
- förutsättningar
- hur man bygger
- hur man kör lokalt
- hur tester körs
- relevanta miljövariabler/konfigurationer
- deployment-info när den är relevant
- teknikstack när det tillför värde
- länkning till fördjupad dokumentation
- licensinformation
- kommandon, portar och filnamn mot faktisk konfiguration

**Tester:**
- README med gammalt `npm`-kommando när projektet använder `pnpm`
- fel Java-version
- fel port
- README som saknar centrala körinstruktioner

**Klart när:**
- Repository Fixer kan skilja mellan saknad README-information och information som faktiskt strider mot repositoryt

**Beror på:** Steg 4

---

## Steg 6 – Implementera dokumentationskonsistens för Markdown

**Mål:** Jämföra `.md`-dokumentation med källkod, buildfiler och konfiguration.

**Kontroller:**
- kommandon och scripts
- runtime-/verktygsversioner
- portar
- konfigurationsnamn och miljövariabler
- katalog-/filreferenser
- endpoints när de kan verifieras rimligt
- funktioner som dokumenteras men inte längre finns
- tydliga nya centrala funktioner som dokumentationen missar

**Begränsning:**
- GPT:n ska markera osäkerhet när full semantisk verifiering inte går att göra

**Klart när:**
- rapporten kan peka ut konkreta dokumentationsavvikelser med stöd i repositoryts filer

**Beror på:** Steg 5

---

## Steg 7 – Implementera LICENSE-analys och beslutspunkt

**Mål:** Kontrollera licensstatus utan att fatta juridiska/verksamhetsmässiga beslut åt användaren.

**Kontroller:**
- finns LICENSE/licensfil
- identifierbar licenstyp
- README kontra LICENSE
- uppenbara placeholders eller saknad copyright-information

**Interaktivt beslut vid behov:**
- föreslagen licenstyp, med neutral kort beskrivning av alternativ
- copyright-innehavare
- årtal

**Tester:**
- LICENSE saknas
- README säger MIT medan LICENSE är Apache-2.0
- befintlig licens är korrekt och ska lämnas orörd

**Klart när:**
- GPT:n aldrig väljer eller ersätter licens utan nödvändig användarbekräftelse

**Beror på:** Steg 4

---

## Steg 8 – Implementera repository hygiene och temporära filer

**Mål:** Identifiera sannolikt överflödiga eller oavsiktligt versionshanterade filer.

**Kontroller:**
- `.gitignore`
- `.DS_Store`
- IDE-/editorfiler
- loggar
- build-output
- coverage-output
- gamla ZIP-filer
- patch/diff-filer
- backup-/old-/final2-liknande filer
- tillfälliga analys-/arbetsfiler
- flera lock-filer för olika package managers när det tyder på inkonsekvens

**Säkerhetsregel:**
- osäker fil får inte raderas automatiskt
- plan och steg ska förklara varför filen tros vara överflödig

**Klart när:**
- tydligt skräp kan föreslås för borttagning
- tveksamma filer blir beslutspunkter eller rekommendationer

**Beror på:** Steg 4

---

## Steg 9 – Implementera build- och testanalys

**Mål:** Kontrollera att repositoryt har begriplig och fungerande build-/teststruktur.

**Kontroller:**
- buildverktyg och scripts
- runtime-versioner
- frontend/backend-kommandon
- testkommandon
- saknade eller brutna referenser
- möjlighet att faktiskt köra build/test när exekveringsmiljön stödjer det

**Regel:**
- ett testfel ska inte automatiskt leda till godtycklig kodrefaktorering; orsaken analyseras och läggs i fix-planen

**Klart när:**
- build/test-status kan redovisas separat som verifierad, ej verifierbar eller felande

**Beror på:** Steg 3

---

## Steg 10 – Implementera GitHub Actions-analys

**Mål:** Bedöma om CI faktiskt bygger och testar relevanta delar av projektet.

**Kontroller:**
- workflows finns när GitHub CI är relevant
- relevanta triggers för PR/push
- korrekt runtime-version
- korrekt package manager/buildverktyg
- frontend och backend täcks när båda finns
- teststeg finns
- actions refererar till existerande scripts/filer
- uppenbart duplicerade eller inaktuella workflows
- tydligt föråldrade action-referenser när det kan verifieras

**Klart när:**
- GPT:n kan skilja mellan "workflow finns" och "workflow verifierar faktiskt projektet"

**Beror på:** Steg 9

---

## Steg 11 – Skapa analysrapportgenerator

**Mål:** Generera den första obligatoriska användarartefakten.

**Output:** `repository-analysis.md`

**Rapportstruktur:**
- sammanfattning
- detekterad projekttyp/stack
- kontrollöversikt
- fynd per område
- evidens
- prioritet/klassificering
- godkända kontroller
- build/test-verifiering
- begränsningar/osäkerheter
- rekommenderat nästa steg

**Klart när:**
- rapporten är användbar även om användaren inte vill låta GPT:n ändra något
- rapporten är nedladdningsbar Markdown

**Beror på:** Steg 5–10

---

## Steg 12 – Skapa fix-plan-generator

**Mål:** Generera den andra obligatoriska användarartefakten utifrån analysen.

**Output:** `repository-fix-plan.md`

**Varje plansteg ska innehålla:**
- mål
- varför steget behövs
- fynd som åtgärdas
- filer som sannolikt berörs
- planerade ändringar
- användarbeslut som krävs
- verifiering efter steget
- risknivå
- beroenden
- status: planerad/genomförd/hoppad över/blockerad

**Planeringsprincip:**
- gruppera relaterade ändringar i naturliga steg
- prioritera blockerare och konsistensproblem före kosmetiska förbättringar
- undvik jättesteg

**Klart när:**
- planen normalt kan genomföras ett steg per användarprompt

**Beror på:** Steg 11

---

## Steg 13 – Implementera interaktiv stegkontroll

**Mål:** Göra åtgärdsdelen kontrollerad och begriplig.

**Inför varje steg ska GPT:n visa:**
- vad som ska ändras
- varför
- berörda filer
- eventuell risk
- eventuell rekommendation
- beslut som behöver bekräftas

**Användaren ska kunna:**
- göra steget
- hoppa över steget
- be om mer detaljer
- ändra förslaget

**Regel:**
- "Gör nästa steg" ska utgå från faktisk status och blockerare, inte mekaniskt nästa nummer

**Klart när:**
- hoppade steg sparas i progress och tas med i slutrapporten
- blockerade steg hanteras utan att övrig möjlig progression tappas bort

**Beror på:** Steg 12

---

## Steg 14 – Implementera ZIP-arbetsflöde och portabel progress

**Mål:** Fullt stöd för analys och korrigering när repositoryt lämnas som ZIP.

**Arbetsflöde:**
1. packa upp och inventera säkert
2. analysera
3. skapa rapport + plan
4. genomför godkänt steg
5. verifiera
6. uppdatera progress
7. bygg en ny komplett ZIP

**Intern arbetsmetadata:**
- `.repository-fixer/analysis.md`
- `.repository-fixer/plan.md`
- `.repository-fixer/progress.md` eller strukturerad motsvarighet

**Krav:**
- användarens projektfiler behålls med korrekt struktur
- originalet ändras inte destruktivt
- komplett uppdaterad ZIP levereras efter genomfört steg

**Slutsteg:**
- användaren kan välja om `.repository-fixer/` ska behållas eller tas bort från slutleveransen

**Klart när:**
- en ny konversation kan återuppta arbetet från den uppdaterade ZIP:en

**Beror på:** Steg 13

---

## Steg 15 – Implementera GitHub-läsflöde

**Mål:** Kunna analysera ett GitHub-repository från länk med samma analysmodell som ZIP-läget.

**Kontroller:**
- repositoryt kan hämtas/läsas
- default branch identifieras
- aktuell struktur analyseras
- eventuell befintlig Repository Fixer-branch/PR kan identifieras när relevant

**Fallback:**
- om skrivåtkomst saknas ska analys och rapport fortfarande fungera och GitHub-ändringar ersättas av tydlig begränsningsinformation

**Klart när:**
- analysresultat för GitHub och ZIP är semantiskt jämförbara

**Beror på:** Steg 12

---

## Steg 16 – Implementera GitHub branch/PR-livscykel

**Mål:** Göra GitHub-ändringar säkert och fortlöpande i PR.

**Arbetsflöde:**
1. kontrollera om aktiv Repository Fixer-PR finns
2. om ingen finns: skapa branch från aktuell default branch
3. skapa PR
4. genomför godkänt plansteg
5. skapa en naturlig commit för steget
6. fortsätt i samma PR så länge den är öppen
7. före nästa ändring: kontrollera PR-status
8. om PR är mergad: uppdatera från default branch och skapa ny branch/PR
9. om PR är stängd utan merge: fråga eller rekommendera hur arbetet ska fortsätta

**Commitprincip:**
- normalt en commit per naturligt plansteg
- tydliga konventionella commitmeddelanden när det passar

**Klart när:**
- Repository Fixer aldrig fortsätter committa till en redan mergad arbetsbranch som om PR:n vore öppen

**Beror på:** Steg 15

---

## Steg 17 – Implementera ändringsverifiering per steg

**Mål:** Säkerställa att varje utfört steg ger avsett resultat utan regressionssignaler.

**Verifieringar kan omfatta:**
- diff-granskning
- build
- tester
- syntax-/konfigurationskontroll
- kontroll att dokumentationsreferenser nu stämmer
- kontroll att borttagna filer inte fortfarande refereras

**Vid fel:**
- steget markeras inte klart
- felet analyseras
- korrigeringssteg prioriteras före nästa ordinarie plansteg

**Klart när:**
- status speglar faktisk verifiering, inte bara att filer har modifierats

**Beror på:** Steg 14 och 16

---

## Steg 18 – Implementera slutverifiering och final report

**Mål:** Köra om analysen från början efter genomförda åtgärder.

**Output:** `repository-final-report.md`

**Rapporten ska visa:**
- initialt antal/typ av fynd
- lösta fynd
- hoppade fynd
- kvarstående fynd
- nya fynd efter ändringar
- build-status
- test-status
- README-status
- dokumentationskonsistens
- LICENSE-status
- GitHub Actions-status
- hygiene-status
- eventuella kvarstående rekommendationer

**Klart när:**
- final report baseras på ny observation av repositoryt, inte enbart progressloggen

**Beror på:** Steg 17

---

## Steg 19 – Skapa deterministiska testrepositories och E2E-scenarier

**Mål:** Testa beteendet på realistiska men kontrollerade repositories.

**Minsta scenario-set:**
1. rent litet repository som ska få få eller inga fynd
2. React/Vite-projekt med gammal README och fel package-manager-instruktion
3. Java/Quarkus-projekt med fel Java-version i dokumentationen
4. frontend + backend där CI bara bygger ena delen
5. repository utan LICENSE
6. repository med README/LICENSE-konflikt
7. repository med tydliga temporära filer
8. repository med tveksam fil som inte får raderas automatiskt
9. ZIP-flöde över flera steg
10. GitHub-flöde med öppen PR
11. GitHub-flöde där tidigare PR redan är mergad

**Klart när:**
- kärnflödena har reproducerbara E2E-testfall
- kritiska säkerhetsregler testas explicit

**Beror på:** Steg 18

---

## Steg 20 – Bygg Chat ZIP-distribution

**Mål:** Skapa portabel Chat-runtime från canonical projekt.

**Output:**
- Chat ZIP med instruktioner, policies, schemas, templates och nödvändiga runtimefiler
- `START-HERE.md`
- versionsinformation

**Validering:**
- ZIP kan användas i en ny ChatGPT-konversation
- ZIP-baserat repositoryflöde fungerar
- rapport + plan kan produceras som filer
- återupptagning fungerar från projektstatus

**Klart när:**
- Chat ZIP passerar distributionsvalideringen

**Beror på:** Steg 19

---

## Steg 21 – Bygg Custom GPT-distribution och dokumentera capability-skillnader

**Mål:** Generera Custom GPT-konfiguration från samma canonical kontrakt.

**Output:**
- Custom GPT-instruktion
- knowledge-/schema-paket där relevant
- capability-konfiguration
- README för installation/konfiguration
- tydlig dokumentation av GitHub-skrivåtkomst och andra plattformsberoenden

**Krav:**
- beteendet ska semantiskt motsvara Chat ZIP där plattformen tillåter
- verkliga begränsningar ska dokumenteras i stället för att döljas

**Klart när:**
- Custom GPT-distributionen passerar instruktion-, storleks- och capability-valideringar

**Beror på:** Steg 20

---

## Steg 22 – Runtime parity, project hygiene och release readiness

**Mål:** Säkerställa att projektet är konsekvent och releasebart.

**Kontroller:**
- canonical source är enda sanningskällan
- Chat ZIP och Custom GPT har semantiskt samma kärnbeteende
- genererade filer ligger rätt
- temporära utvecklingsfiler är borttagna
- README och projektstatus är aktuella
- lint/test/E2E passerar
- final hygiene passerar
- kända plattformsbegränsningar är dokumenterade

**Klart när:**
- inga blockerande release readiness-fynd återstår

**Beror på:** Steg 20–21

---

## Steg 23 – GitHub Actions för CI och release

**Mål:** Göra GPT-projektet självbärande för validering och releasebyggen.

**CI ska minst:**
- validera projektstruktur/schemas
- köra lint
- köra deterministiska tester
- köra relevanta E2E-scenarier
- validera distributionerna

**Release workflow ska:**
- triggas av release/tag enligt projektets conventions
- låta GitHub Release-taggen styra artefakternas version
- bygga kompletta Chat ZIP- och Custom GPT-artefakter
- paketera projekt-ZIP vid behov

**Klart när:**
- samma build kan reproduceras lokalt och i GitHub Actions

**Beror på:** Steg 22

---

## Steg 24 – Release candidate och stabil v1

**Mål:** Köra en fullständig referensvalidering och producera första stabila versionen.

**Releasekriterier:**
- analysrapport fungerar för både ZIP och GitHub-input
- fix-plan fungerar och är stegvis genomförbar
- användarbeslut hanteras säkert
- ZIP kan uppdateras och återupptas
- GitHub PR-livscykel fungerar
- slutverifiering producerar final report
- kritiska E2E-tester passerar
- Chat ZIP och Custom GPT validerade
- project hygiene godkänd

**Output:**
- versionssatt projekt-ZIP
- versionssatt Chat ZIP
- Custom GPT-distribution
- release notes

**Klart när:**
- v1 är reproducerbart byggd och inga blockerande valideringsfel återstår

**Beror på:** Steg 23

---

# Senare möjliga förbättringar efter v1

Följande bör behandlas som separata vidareutvecklingar och inte smygas in i v1:

- dependency health och kontrollerade dependency-uppgraderingar
- säkerhetsskanning
- Dependabot/Renovate
- `SECURITY.md`
- `CONTRIBUTING.md`
- `CODEOWNERS`
- changelog/release hygiene
- semantic versioning-kontroller
- Dockerfile/container best practices
- deploymentkonfiguration
- coverage-trösklar
- projektspecifika plugin-/regelpaket
- organisationspolicyer för repository-standarder

# Definition of Done för varje utvecklingssteg

Ett steg i denna plan markeras inte klart förrän:

1. avsedd leverans finns,
2. relevanta tester/valideringar har körts,
3. blockerande fel är lösta eller uttryckligen dokumenterade som blockerare,
4. project hygiene har bedömts,
5. `project-status.yaml` och mänskligt läsbar status är uppdaterade,
6. nästa steg har beräknats från faktisk projektstatus,
7. en ny komplett projekt-ZIP kan byggas.

# Nästa steg

Nästa genomförandesteg är **Steg 1 – Skapa projektets canonical grundstruktur**. Det är då den första faktiska Repository Fixer-projekt-ZIP:en ska skapas.


---

# Migrering till GPT Byggaren 1.5.0

Migreringen ska bevara Repository Fixer 1.0.0:s domänbeteende och genomföras som separata verifierbara steg.

## Steg 25 – Inför 1.5-kontrakt och modellrobust workflow

**Mål:** Införa plattformsneutrala capability-, artifact-, workspace/state- och runtimekontrakt samt explicit stateful operativ kärna.

**Klart när:**
- canonical instruktion innehåller operativ kärna och auktoritativ statusregel
- alla fem registrerade runtimes är bedömda
- Chat, Custom GPT och OpenCode är valda som default-aktiva mål
- modellkompatibilitet har minst fyra scenarios
- befintlig v1-CI är fortfarande grön

## Steg 26 – Migrera buildsystemet till 1.5 och bygg OpenCode

**Mål:** Byta till 1.5:s generiska build-/lint-/distributionsmotor och lägga till faktisk OpenCode-adapter.

**Klart när:**
- project, Chat, Custom GPT och OpenCode byggs deterministiskt
- OpenCode innehåller AGENTS.md, runtime-kontrakt och relevanta skills/tools
- distributionsvalidering passerar

## Steg 27 – Generalisera runtime parity och release readiness

**Mål:** Bedöma aktiverade runtimes mot canonical behavior/capability/artifact/workspace_state/tool-kontrakt.

**Klart när:**
- parity omfattar Chat, Custom GPT och OpenCode
- Claude Projects och OpenAI Plugin redovisas som bedömda men ej aktiverade
- CI stoppar progression vid blockerande valideringsfel

## Steg 28 – Slutvalidera migreringen och releasekedjan

**Mål:** Köra full test, lint, modellrobusthet, hygiene, build och release readiness.

**Klart när:**
- samtliga aktiverade distributioner passerar
- GitHub release bygger samma mål som lokal/CI-build
- status och dokumentation beskriver 1.5-arkitekturen
