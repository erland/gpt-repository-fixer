# Repository inventory och projekttypdetektion

Detta dokument definierar den första tekniska passeringen av ett okänt repository. Inventeringen ska beskriva vad som faktiskt kan beläggas innan README, dokumentation, CI eller repository hygiene bedöms.

## Grundregel

Detektera genom **positiv evidens i repositoryt**. Ett filnamn eller en katalog är en signal, inte alltid ett slutligt bevis. Kombinera signaler när det går och ange osäkerhet vid tvetydighet.

Fabricera aldrig en stack, projekttyp, package manager, runtime eller framework som inte stöds av evidens. Om tekniken är okänd: klassificera den som `unknown` och fortsätt med generell repository-analys.

## Första passeringen

Inventera minst:

1. rotfiler och rotkataloger
2. build- och dependency-filer
3. lockfiler och package manager
4. språk- och framework-signaler
5. applikationsdelar/moduler
6. container-/compose-konfiguration
7. CI/workflows
8. teststruktur
9. dokumentationsstruktur
10. möjliga monorepo-signaler

Begränsa djupet initialt. För mycket filuppräkning gör analysen sämre. Börja med rot + karakteristiska filer och gå djupare där evidensen kräver det.

## Projekttyp

Tillåt flera typer när repositoryt faktiskt innehåller flera delar.

- `frontend`: web/UI-app eller motsvarande klientdel
- `backend`: server/API/service
- `fullstack`: tydligt sammanhållen frontend + backend
- `monorepo`: flera självständigt byggbara paket/appar i gemensamt repo
- `library`: återanvändbart bibliotek/package snarare än fristående app
- `documentation`: huvudsakligen dokumentation
- `cli`: kommandoradsverktyg
- `infrastructure`: huvudsakligen IaC/deploy/runtime-konfiguration
- `unknown`: otillräcklig evidens

`monorepo` är en strukturklass och kan kombineras med exempelvis frontend/backend.

## Evidenssignaler

### JavaScript / TypeScript / frontend

- `package.json` => Node-ekosystem finns
- `pnpm-lock.yaml` => pnpm
- `package-lock.json` => npm
- `yarn.lock` => Yarn
- `vite.config.*` => Vite
- `src/main.tsx`, `src/main.jsx` eller React dependency i `package.json` => React-signal
- `tsconfig.json` => TypeScript-signal

Om flera lockfiler finns: rapportera konflikten; välj inte package manager genom gissning.

### Java

- `pom.xml` => Maven
- `build.gradle` / `build.gradle.kts` => Gradle
- Quarkus dependencies/plugins eller `quarkus.*`-konfiguration => Quarkus
- Spring Boot dependencies/plugins eller typiska Spring Boot entrypoints => Spring Boot

`pom.xml` ensam betyder Java/Maven, inte Quarkus eller Spring.

### Python

Signaler inkluderar `pyproject.toml`, `requirements.txt`, `setup.py`, `setup.cfg`, `Pipfile` och Python-källfiler. Identifiera framework bara när dependency/config ger stöd.

### Go

`go.mod` är primär Go-modulsignal. `go.work` kan indikera workspace/flera moduler.

### Rust

`Cargo.toml` är primär Rust-signal. Workspace-sektion och flera crates kan indikera monorepo/workspace.

### Docker

- `Dockerfile` / `*.Dockerfile` => container build
- `compose.yaml`, `compose.yml`, `docker-compose.yml`, `docker-compose.yaml` => Compose

Docker betyder inte automatiskt att projektet är en backend.

### GitHub Actions

`.github/workflows/*.yml` och `.github/workflows/*.yaml` => GitHub Actions finns. Inventera workflowfilernas namn och senare deras syfte; anta inte att de bygger eller testar förrän innehållet verifierats.

### Monorepo

Starka signaler är exempelvis:

- `pnpm-workspace.yaml`
- root `package.json` med workspaces
- Maven multi-module (`<modules>`)
- Gradle multi-project settings
- Cargo workspace
- Go workspace
- flera tydligt självständiga byggfiler under `apps/`, `packages/`, `services/`, `frontend/`, `backend/` eller motsvarande

Enbart mapparna `frontend/` och `backend/` räcker inte alltid; verifiera byggsignaler i dem.

## Inventory-output

Inventeringen ska följa `schemas/repository-inventory.schema.json` när strukturerad output används och minst innehålla:

- projekttyper
- språk
- frameworks
- buildverktyg/package managers
- container/compose
- CI-system
- moduler/komponenter
- detektions-evidens
- konflikter/osäkerheter
- confidence: `high`, `medium` eller `low`

Varje detekterat påstående ska kunna spåras till minst en evidenspost med fil/signal. Confidence ska avspegla evidensens styrka, inte modellens magkänsla.

## Okänd eller ovanlig stack

Om kända signaler inte räcker:

1. ange `unknown` där det behövs
2. lista observerade bygg-/källfiler utan att namnge okänt framework
3. fortsätt generella kontroller: README, LICENSE, `.gitignore`, dokumentation, CI och tydliga tempfiler
4. gå djupare i relevanta manifest/configfiler innan användaren tillfrågas

Fråga inte användaren vilken stack projektet använder om repositoryt självt rimligen kan besvara frågan.
