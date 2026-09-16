# README-analys

Repository Fixer ska bedöma README utifrån det faktiska repositoryt, inte utifrån en universell mall. En README för ett bibliotek, en backendtjänst och ett monorepo behöver inte ha samma rubriker.

## Kontrollordning

1. Hitta repositoryts primära README. Föredra toppnivån framför README-filer i underkataloger.
2. Identifiera vilka uppgifter som kan verifieras mot repositoryt.
3. Markera konkreta motsägelser som **Bör åtgärdas**.
4. Markera viktig men saknad användarinformation som **Bör åtgärdas** eller **Rekommenderas** beroende på hur central den är.
5. Använd **Överväg** för projektspecifika förbättringar där repositoryt inte ger ett entydigt facit.
6. Använd **Godkänd kontroll** bara för kontroller som faktiskt jämförts mot evidens.

## Centrala kontroller

Kontrollera när de är relevanta:

- vad projektet gör och vem README hjälper
- förutsättningar som Java-, Node-, Python- eller annan runtimeversion
- package manager
- installation/build
- lokal körning
- tester
- relevanta miljövariabler och konfigurationsfiler
- lokal port och URL
- deployment när repositoryt innehåller tydlig deploymentkonfiguration
- teknikstack när den hjälper användaren
- länkar till fördjupad dokumentation
- licensinformation

## Hårda inkonsekvenser

Följande är typiska `must-fix` när repositoryt ger tydlig evidens:

- README visar `npm` men en ensam `pnpm-lock.yaml` visar att projektet använder pnpm
- README anger Java 17 medan `pom.xml` eller Gradle uttryckligen kräver Java 21
- README anger `localhost:8080` medan entydig runtime-/compose-konfiguration exponerar 8081
- README refererar till ett script eller en fil som inte finns
- ett byggbart projekt saknar helt konkreta build-/körinstruktioner

Var försiktig när flera konfigurationer kan vara korrekta samtidigt, exempelvis olika portar bakom reverse proxy eller flera package managers avsiktligt. Rapportera då osäkerheten i stället för en falsk konflikt.

## Saknad information

Saknade centrala start-/buildinstruktioner kan vara **Bör åtgärdas** eftersom README annars inte fyller sin grundfunktion. Testinstruktioner, deploymentöversikt eller stackbeskrivning är normalt **Rekommenderas** om de är relevanta men inte nödvändiga för att börja använda projektet.

README behöver inte duplicera detaljerad dokumentation. Det räcker ofta med en kort översikt och en korrekt länk.

## Verifiering

När miljön tillåter bör dokumenterade kommandon köras. Om de inte kan köras ska Repository Fixer uttryckligen säga att kontrollen är statisk. Hitta inte på fungerande kommandon enbart från konventioner; härled dem från manifest, scripts, wrappers och annan repositoryevidens.
