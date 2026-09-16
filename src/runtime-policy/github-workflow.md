# GitHub workflow policy

Canonical instruktionen styr beteendet. Denna policy fördjupar GitHub-flödet.

- Läs aktuell default branch och PR-status innan skrivning.
- Skapa arbetsbranch först när användaren har valt att börja åtgärda planen.
- Återanvänd samma öppna Repository Fixer-PR under en sammanhängande åtgärdsomgång.
- Ett naturligt plansteg bör normalt motsvara en commit.
- Efter merge: synka mot aktuell default branch och skapa ny branch/PR innan ytterligare ändringar.
- Vid stängd, konfliktdrabbad eller irrelevant PR: välj inte automatiskt samma branch; bedöm säker fortsättning utifrån aktuellt repositoryläge.
- Skriv inte direkt till default branch som standard.
## Läsflöde

- Normalisera GitHub-länken till owner/repository och läs repositorymetadata; gissa inte analyserad ref från URL-text.
- Fastställ default branch, faktisk analyserad ref och commit SHA när verktyget exponerar den.
- Samla in samma repositoryunderlag som ZIP-läget behöver och använd samma inventory-/analyslogik.
- Identifiera möjliga befintliga Repository Fixer-PR:er endast från konkreta signaler, exempelvis `repository-fixer/`-branch eller tydlig titel.
- Om skrivåtkomst saknas eller är okänd ska analysen fortsätta, men skrivförmåga får inte antas.
## Skriv-state och PR-livscykel

- Följ `github-write-workflow.md` för deterministisk branch-/PR-status och commitkoppling.
- Skriv-state ska kunna uttryckas enligt `repository-github-write-state.schema.json`.
- Providerverktyget utför GitHub-operationerna; planeringslogiken får inte anta att en branch, commit eller PR skapats innan verktygsresultatet bekräftar det.

