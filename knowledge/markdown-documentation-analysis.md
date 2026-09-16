# Konsistensanalys för övrig Markdown-dokumentation

Den här kontrollen gäller Markdown-filer utöver repositoryts primära README. Syftet är att hitta dokumentation som inte längre motsvarar källkod, build, konfiguration eller repositorystruktur utan att fabricera semantiska avvikelser.

## Grundregel

Skilj mellan **maskinellt verifierbara påståenden** och **semantiska påståenden**.

Maskinellt verifierbara påståenden kan normalt jämföras direkt mot repositoryt, exempelvis scripts, runtimeversioner, lokala portar, filreferenser och vissa miljövariabler. En tydlig motsägelse kan klassas som **Bör åtgärdas**.

Semantiska påståenden, exempelvis att en funktion "inte längre finns" eller att en ny central funktion "saknas i dokumentationen", kräver bredare läsning av relevant källkod. Markera osäkerhet när implementationen inte ger ett entydigt facit.

## Kontrollområden

Granska när de förekommer:

- `npm`/`pnpm`/`yarn`-scripts mot `package.json`
- Java/JDK- och andra runtime-/verktygsversioner mot buildfiler och CI
- `localhost`-portar mot runtime- och Compose-konfiguration
- miljövariabler mot env-exempel, Compose, properties och källkod
- relativa fil- och katalogreferenser mot faktisk repositorystruktur
- dokumenterade API-endpoints mot controllers/routers när routingen kan verifieras rimligt
- arkitektur- och modulnamn mot faktisk katalog-/modulstruktur
- funktioner eller kommandon som beskrivs men inte längre kan beläggas i implementationen
- nya centrala användar- eller driftfunktioner som implementationen tydligt innehåller men dokumentationen fortfarande beskriver en äldre helhetsbild av

## Evidensnivåer

### Hög confidence

Använd normalt **Bör åtgärdas** när två tydliga källor motsäger varandra, exempelvis:

- `docs/setup.md` säger Java 17 medan `pom.xml` kräver 21
- `docs/development.md` säger `pnpm run serve` men `package.json` saknar `serve`
- dokumentet länkar till `docs/old-api.md` som inte finns
- dokumentet anger `localhost:8080` och repositoryts enda relevanta portkonfiguration är 8081

### Medium confidence

Använd normalt **Rekommenderas** när kontrollen är stark men inte fullständig, exempelvis:

- en dokumenterad env-variabel saknas i de konfigurationskällor som kontrollerats men kan läsas dynamiskt i kod
- en dokumenterad endpoint matchar inte direkt någon route men routing kan byggas av klassprefix eller ramverkskonfiguration
- ett funktionsnamn saknas från kodsökning men kan ha bytt namn utan att beteendet försvunnit

Beskriv då vad som behöver verifieras innan någon ändring görs.

## Semantisk funktionskonsistens

För att avgöra om dokumentationen beskriver borttagna eller saknade funktioner:

1. Identifiera konkreta funktionspåståenden i dokumentet.
2. Leta efter implementation, routes, UI-komponenter, use cases, konfiguration eller tester som stöder påståendet.
3. Om ingen evidens hittas, sök efter namnbyte eller ersättande beteende innan fynd skapas.
4. Klassificera som **Bör åtgärdas** endast när frånvaron är väl belagd.
5. Om en central ny funktion tydligt finns i koden men dokumentationen gör ett direkt påstående som blivit ofullständigt eller felaktigt, skapa fynd. Kräv inte att varje funktion måste dokumenteras.

Repository Fixer ska inte skapa en generell feature inventory bara för att fylla dokumentationen. Dokumentationsbehovet ska vara relevant för dokumentets uttalade syfte.

## Exkluderingar

- Primär README hanteras av README-analysen.
- `.repository-fixer/*.md` är arbetsmetadata och ska inte analyseras som projektets egen dokumentation.
- Externa länkar verifieras inte som repositoryfiler i denna kontroll.
- Generiska ord som `PATH`, `HOME` eller `JAVA_HOME` ska inte automatiskt behandlas som projektspecifika miljövariabler utan relevant kontext.

## Verifiering

Kör dokumenterade kommandon och tester när miljön tillåter. För API- eller runtimepåståenden bör dynamisk verifiering användas när statisk analys inte räcker. Om kontrollen bara är statisk ska det framgå i fyndet eller rapportens osäkerhetsdel.
