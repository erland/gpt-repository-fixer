# GitHub-läsflöde

Den här filen fördjupar canonical kontraktet för GitHub som analyskälla. Den ändrar inte kravet att analysera före ändring.

## 1. Normalisera källan

För en GitHub-länk ska repositoryts identitet fastställas som `owner/repository`. Navigeringsdelar som `/tree/...` får inte användas för att gissa vilken ref som faktiskt analyseras. Läs repositorymetadata och fastställ explicit:

- canonical repository-URL
- default branch
- den branch/ref som faktiskt analyseras
- commit SHA när verktyget exponerar den
- om skrivåtkomst är verifierad, saknas eller är okänd

Om repositoryt inte kan läsas ska det rapporteras som en källbegränsning, inte som ett repository-fynd.

## 2. Läs samma underlag som ZIP-läget

GitHub-läget ska samla in repositoryfilernas aktuella innehåll och göra dem tillgängliga för samma inventory- och analyslogik som ZIP-läget. Analysen får inte bli ytligare enbart därför att källan är GitHub.

Minimikravet är att kunna läsa de filer som behövs för aktuell analys, inklusive relevanta manifests, källkod, Markdown, LICENSE, `.gitignore` och `.github/workflows` när de finns. Om verktyget inte kan läsa hela trädet ska begränsningen redovisas och inga saknade filer antas vara frånvarande.

## 3. Semantisk likvärdighet

Samma repositorytillstånd ska så långt verktygen medger ge semantiskt samma:

- projekttyp och teknikstack
- fynd och klassificering
- build/test-bedömning
- analysrapport
- fix-plan

Skillnader får bero på faktisk GitHub-metadata, exempelvis default branch, commit SHA, PR-status eller behörighet, inte på olika analysregler.

## 4. Befintligt Repository Fixer-arbete

Vid läsning får öppna PR:er identifieras som möjliga Repository Fixer-PR:er när det finns konkret signal, exempelvis branchprefix `repository-fixer/` eller tydlig titel. En träff innebär inte automatiskt att PR:n ska återanvändas; relevans och status bedöms i skrivflödet.

## 5. Read-only fallback

Om skrivåtkomst saknas eller inte kan verifieras:

- fullfölj analys, `repository-analysis.md` och `repository-fix-plan.md`
- påstå inte att branch, commit eller PR kan skapas
- markera begränsningen separat från repositoryts hälsa
- erbjud ZIP-baserad ändring eller annan faktisk leveransväg när användaren vill genomföra planen

Skrivbehörighet får aldrig antas från att repositoryt är publikt eller läsbart.
