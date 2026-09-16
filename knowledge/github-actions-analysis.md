# GitHub Actions-analys

## Syfte

Repository Fixer ska bedöma om GitHub Actions faktiskt verifierar projektet. Att en fil finns under `.github/workflows/` är inte i sig en godkänd CI-kontroll.

## Arbetsordning

1. Inventera alla `.github/workflows/*.yml` och `*.yaml`.
2. Tolka workflowstruktur och triggers. Ogiltig YAML är ett konkret fel.
3. Återanvänd build-/testanalysens härledda kommandon per komponent.
4. Kontrollera om workflowen kör motsvarande build och tester för relevanta komponenter.
5. Jämför runtime-versioner mot repositoryts verifierbara versionskällor.
6. Jämför package manager mot entydiga lockfiler.
7. Kontrollera att lokala scripts/filer som körs faktiskt finns.
8. Leta efter uppenbara dubletter.
9. Bedöm action-versioners aktualitet bara när aktuell major har verifierats mot en tillförlitlig källa vid analysen.

## Klassificering

- Saknad GitHub Actions när GitHub CI ingår i granskningsmålet: normalt `Rekommenderas`.
- Ogiltig workflow-YAML, fel package manager, verifierad runtime-konflikt eller referens till saknad scriptfil: `Bör åtgärdas`.
- Tester som finns i projektet men inte körs i CI: `Bör åtgärdas`.
- Härlett buildsteg som inte körs i CI: normalt `Rekommenderas`, om inte projektets egna krav gör det kritiskt.
- Saknad `pull_request` eller `push`: normalt `Rekommenderas`.
- Uppenbart duplicerade workflows: `Rekommenderas`.
- Äldre action-major: `Rekommenderas` endast när aktuell major är separat verifierad. Gissa aldrig från modellminne.

## Komponenttäckning

I monorepo/fullstack ska varje relevant komponent bedömas separat. Ett frontend-test räknas inte som backend-test. `working-directory`, uttryckliga sökvägar och faktiska kommandon får användas som evidens.

Om två komponenter använder samma kommando ska de ändå ha separata coverage-poster.

## Runtime och package manager

Jämför bara när repositoryt ger ett rimligt canonical facit, exempelvis `.java-version`, Maven-property, `.node-version`, `.nvmrc`, `package.json engines`, `.python-version` eller entydig lockfil.

Om versionsuttryck är komplexa och inte kan jämföras säkert: markera osäkerhet i stället för att skapa ett felaktigt fynd.

## Action-versioner

Versionspåståenden om externa actions blir snabbt inaktuella. Kontrollera därför aktuell version från officiell action/repository-källa när webbtillgång finns. Utan sådan verifiering får Repository Fixer beskriva den observerade referensen men inte påstå att den är föråldrad.

## PASS

`Godkänd kontroll` får bara ges när parsebara workflows har relevanta triggers, härledda build/test-behov är täckta och inga verifierade konflikter hittats. Det betyder inte att en verklig GitHub-körning har lyckats; en körning får bara kallas passerad om körresultatet faktiskt är känt.
