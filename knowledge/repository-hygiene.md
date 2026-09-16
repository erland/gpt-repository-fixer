# Repository hygiene och temporära filer

Repository Fixer ska identifiera oavsiktligt versionshanterade eller sannolikt överflödiga filer utan att förväxla en ovanlig projektstruktur med skräp. Analysen är därför konservativ: **hög säkerhet om att en fil är genererad är inte samma sak som tillåtelse att radera den**.

## Grundregler

1. Utgå från observerade filer och kataloger, inte namnassociationer ensamma.
2. Skilj mellan **säkert genererade artefakter** och **historiska/tveksamma arbetsfiler**.
3. En tveksam fil ska aldrig föreslås för automatisk borttagning utan användarbeslut.
4. Kontrollera `.gitignore` mot de artefakter som faktiskt finns eller mot entydiga verktygssignaler i repositoryt.
5. Flera package-manager-lockfiler ska redovisas som en konflikt, men Repository Fixer får inte själv välja vilken som ska behållas.
6. Undanta Repository Fixers egen portabla arbetsmetadata under `.repository-fixer/` från skräpklassificering medan ett ZIP-arbetsflöde pågår.
7. En fil som refereras från build, CI, scripts eller dokumentation får inte behandlas som säkert överflödig enbart på grund av sitt namn.

## Signaler med hög säkerhet

Följande är normalt genererade eller lokala artefakter när de förekommer i ett källkodsrepository:

- `.DS_Store`
- `Thumbs.db`
- editor-/IDE-state som `.idea/`, `.vscode/` (bedöm konfigurationsfiler separat; vissa team versionshanterar avsiktligt delar av dem)
- `node_modules/`
- `.pytest_cache/`, `__pycache__/`, `.mypy_cache/`, `.ruff_cache/`
- `coverage/`, `.coverage`, `htmlcov/`
- `target/` för Maven
- `.gradle/`
- loggfiler som `*.log`
- temporära filer som `*.tmp`, `*.temp`, swapfiler och editor-backuper

För `dist/`, `build/` och liknande kataloger krävs mer försiktighet eftersom namnen också kan användas för avsiktligt källinnehåll. Använd projektets byggverktyg, scripts och referenser som stöd.

## Historiska och tveksamma filer

Namn som följande är endast heuristik:

- `*-old.*`
- `*-backup.*`, `*.bak`
- `*-copy.*`
- `*-final2.*`, `*-final-final.*`
- patch-/diff-filer
- gamla ZIP-arkiv
- tillfälliga analysrapporter eller migrationsanteckningar

Sådana filer ska normalt klassas som `consider` eller `recommended` med `decision_required: true` om borttagning är den föreslagna åtgärden. Förklara exakt varför filen verkar överflödig och kontrollera om den refereras någonstans.

## `.gitignore`

Kontrollera:

- om `.gitignore` saknas trots tydliga genererade artefakter
- om observerade artefakter inte täcks av befintliga ignore-regler
- om vanliga ignore-regler saknas för entydigt detekterade verktyg, men undvik att kräva en generell mall bara för sakens skull

En ignore-brist är normalt `recommended`. En redan versionshanterad artefakt behöver dessutom tas bort från repositoryt i ett senare, godkänt fix-steg; att lägga till ignore-regel räcker inte i sig.

## Package-manager-lockfiler

I samma JavaScript/TypeScript-projektrot är flera av följande normalt en inkonsekvens:

- `package-lock.json`
- `pnpm-lock.yaml`
- `yarn.lock`

Rapportera konflikten med hög confidence. Själva valet av package manager och vilken lockfil som ska tas bort kräver användarbeslut om repositoryt inte redan ger ett entydigt facit genom CI, `packageManager` i `package.json` eller dokumentation som stöds av faktisk buildkonfiguration.

## Klassificering

- `recommended`: tydligt lokalt/genererat skräp eller konkret `.gitignore`-brist.
- `consider`: historisk/tveksam fil där avsikten inte kan beläggas.
- `must-fix`: reserveras för verifierade konflikter som faktiskt gör repositoryt inkonsekvent; använd sparsamt.
- `passed`: hygiene-kontrollerna har körts och inga relevanta problem hittades.

## Fix-policy

Repository Fixer får i ett senare godkänt plansteg ta bort artefakter med mycket hög säkerhet, exempelvis `.DS_Store` eller cacheoutput, när ingen referens eller projektregel talar emot det. Historiska filer, arkiv, patchar, IDE-konfiguration och andra potentiellt avsiktliga filer kräver uttryckligt användarbeslut innan borttagning.
