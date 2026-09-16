# Fix-planering

`repository-fix-plan.md` är den andra obligatoriska artefakten efter analysrapporten. Den ska byggas från öppna fynd i analysen och behålla fyndens stabila ID:n.

## Regler

- Ta inte med `Godkänd kontroll` som åtgärdssteg.
- Prioritera `Bör åtgärdas` före `Rekommenderas` och `Överväg` när inget beroende kräver annat.
- Gruppera endast fynd som hör till samma naturliga arbetsområde och kan verifieras tillsammans.
- Dela stora grupper i mindre steg; ett steg ska normalt gå att utföra i en användarprompt.
- Ett plansteg ska beskriva mål, varför, fynd-ID:n, sannolikt berörda filer, planerade ändringar, eventuella beslut, verifiering, risk, beroenden och status.
- Om ett fynd kräver användarbeslut ska beslutet synas explicit i planen och steget får inte genomföras förbi beslutet.
- Härled sannolikt berörda filer från evidensen. Hitta inte på exakta filer som saknar stöd; använd en generell komponent-/områdesbeskrivning när filen ännu inte kan bestämmas.
- Använd fyndets `recommended_action` som grund för planerad ändring, men expandera inte omfattningen utanför fyndets evidens.
- GitHub Actions-steg kan bero på build/test-steg när CI ska spegla eller använda de korrigerade kommandona.
- Risk är låg för rena dokumentationsändringar, normalt medium för build/CI, filborttagning och licensrelaterade ändringar, och high endast när evidensen visar tydlig risk för beteendeförändring eller irreversibel påverkan.

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
