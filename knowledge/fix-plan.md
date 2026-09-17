# Fix-planering

`repository-fix-plan.md` är den andra obligatoriska artefakten efter analysrapporten. Den ska byggas från öppna fynd i analysen och behålla fyndens stabila ID:n.

Följ `analysis-completeness.md`: en slutlig fix-plan ska normalt inte skapas förrän fullanalysen är komplett.

## Regler

- Ta inte med `Godkänd kontroll` som åtgärdssteg.
- Ta med **samtliga öppna fynd** (`Bör åtgärdas`, `Rekommenderas`, `Överväg`) från den kompletta analysen. Prioritering påverkar ordningen, inte om fyndet tas med.
- Varje öppet fynd ska förekomma i planens `source_finding_ids` och i exakt ett naturligt plansteg, om det inte uttryckligen dokumenteras som utanför scope eller inte åtgärdsbart med motivering.
- Begränsa aldrig den totala planen till de viktigaste fyra eller fem fynden. Det är däremot korrekt att dela många fynd i flera prompt-stora steg.
- Prioritera `Bör åtgärdas` före `Rekommenderas` och `Överväg` när inget beroende kräver annat.
- Gruppera endast fynd som hör till samma naturliga arbetsområde och kan verifieras tillsammans.
- Dela stora grupper i mindre steg; ett steg ska normalt gå att utföra i en användarprompt.
- Ett plansteg ska beskriva mål, varför, fynd-ID:n, sannolikt berörda filer, planerade ändringar, eventuella beslut, verifiering, risk, beroenden och status.
- Om ett fynd kräver användarbeslut ska beslutet synas explicit i planen och steget får inte genomföras förbi beslutet.
- Härled sannolikt berörda filer från evidensen. Hitta inte på exakta filer som saknar stöd; använd en generell komponent-/områdesbeskrivning när filen ännu inte kan bestämmas.
- Använd fyndets `recommended_action` som grund för planerad ändring, men expandera inte omfattningen utanför fyndets evidens.
- GitHub Actions-steg kan bero på build/test-steg när CI ska spegla eller använda de korrigerade kommandona.
- Risk är låg för rena dokumentationsändringar, normalt medium för build/CI, filborttagning och licensrelaterade ändringar, och high endast när evidensen visar tydlig risk för beteendeförändring eller irreversibel påverkan.

## Completeness-kontroll före planering

Innan en slutlig plan levereras:

1. verifiera att analysen är markerad komplett,
2. jämför alla öppna fynd-ID:n i analysen mot `source_finding_ids`,
3. verifiera att inget öppet fynd tappats bort när steg grupperats eller delats,
4. redovisa uttryckligen om något fynd lämnas utanför planen och varför.

Om analysen fortfarande är ofullständig ska användaren normalt erbjudas **Fortsätt leta efter fler fynd**. Om användaren uttryckligen väljer att börja åtgärda ändå får en preliminär plan skapas, men den ska märkas tydligt och får inte beskrivas som fullständig.

## Arbetsområden

Följande gruppering är en standard, inte ett krav när evidensen talar för en bättre uppdelning:

- `readme` + `documentation` → Dokumentation
- `build` + `tests` + `versions` → Build, test och runtime
- `github-actions` → GitHub Actions
- `license` → Licens
- `repository-hygiene` → Repository hygiene
- `inventory` + `other` → Repositorystruktur/övrigt

## Status

Nya steg startar som `planned`. Senare interaktivt arbete får ändra status till `completed`, `skipped` eller `blocked`. Fix-plan-generatorn ska inte markera ett steg färdigt bara för att planen skapats.
