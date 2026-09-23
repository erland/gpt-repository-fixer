# Repository Fixer – migrering till GPT Byggaren 1.5.0

## Sammanfattning

Repository Fixer har migrerats till GPT Byggaren 1.5.0 utan att ändra projektets domänbeteende.

## Viktigaste förändringar

- stateful modellrobust workflow med strukturerad status som auktoritativ källa
- plattformsneutrala capability-, artifact-, workspace/state- och tool-kontrakt
- explicit bedömning av ChatGPT Chat, ChatGPT Custom, Claude Projects, OpenCode och OpenAI Plugin
- Chat ZIP och Custom GPT behålls som aktiva distributionsmål
- OpenCode tillkommer som aktiv peer-runtime
- Claude Projects och OpenAI Plugin är bedömda men inte aktiverade
- generaliserad runtime parity är både egen CI-gate och del av release-readiness
- CI och release bygger samma runtime-mål och kör samma valideringsgates
- deterministiska tester verifierar workflow-paritet mellan CI och release

## Aktiva distributionsmål

- project ZIP
- Chat ZIP
- Custom GPT ZIP
- OpenCode ZIP

## Releasekedja

GitHub Release-taggen är fortsatt versionskälla. Release-workflowet kör tester, lint, hygiene, bygger samtliga aktiva distributioner, validerar distributionerna, verifierar runtime parity och release-readiness samt publicerar ZIP-filer, checksummer och delivery manifest.
