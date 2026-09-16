# Build- och testanalys

Repository Fixer ska skilja mellan **strukturen för build/test** och **resultatet av att faktiskt köra kommandona**.

## Grundregel

Att ett build- eller testkommando kan härledas ur repositoryt betyder inte att det har körts. Redovisa därför alltid ett av tre verifieringsutfall:

- `verified` – kommandot kördes i aktuell miljö och gav exit-kod 0.
- `failing` – kommandot kördes och gav en verifierbar icke-noll exit-kod.
- `not-verified` – kommandot har inte körts eller kunde inte köras i aktuell miljö.

`not-verified` är inte ett fel och får aldrig beskrivas som om build/test misslyckats.

## Härledning av standardkommandon

Använd repositoryts egna manifest och wrappers som evidens. Föredra wrapper när den finns.

- Node: använd repositoryts entydiga package manager och `scripts.build` / `scripts.test`.
- Maven: `./mvnw` när wrapper finns, annars `mvn`; build kan verifieras med `-DskipTests package` och test med `test`.
- Gradle: `./gradlew` när wrapper finns, annars `gradle`; build `assemble`, test `test`.
- Python: härled bara standardbuild när `pyproject.toml` faktiskt beskriver ett build-backend; pytest kan användas när pytest/teststruktur är tydlig.
- Go: `go build ./...` och `go test ./...`.
- Rust: `cargo build` och `cargo test`.

För okända eller projektspecifika verktyg ska Repository Fixer inte hitta på kommandon.

## Strukturella fynd

Exempel på relevanta fynd:

- testfiler finns men Node-projektet saknar `scripts.test`
- projektet har ett tydligt byggsteg men saknar ett standardiserat build-script
- två canonical runtimefiler motsäger varandra, exempelvis Maven Java-version kontra `.java-version`
- build eller test har faktiskt körts och misslyckats

Ett misslyckat test eller build ska leda till analys av den konkreta orsaken och ett avgränsat steg i fix-planen. Det är inte tillåtelse att refaktorera produktionskod eller försvaga tester godtyckligt för att få grönt.

## Multikomponentprojekt

I monorepon/fullstackprojekt ska build/test redovisas per upptäckt komponent när det går att härleda säkert. Ett grönt frontendkommando innebär inte att backend är verifierad, och tvärtom.

## Rapportering

Rapporten ska kunna visa build och test separat med kommando, källa och verifieringsstatus. Om exekvering inte stöds ska orsaken anges kort, exempelvis saknad runtime, nätverksbegränsning eller att kommandot inte har körts ännu.
