# GitHub branch/PR-livscykel

Denna fördjupning gäller endast när GitHub-skrivåtkomst är verifierad och användaren har valt att börja genomföra fix-planen. Canonical systeminstruktionen är styrande.

## Grundregel

Skriv inte direkt till default branch. Ett naturligt plansteg motsvarar normalt en commit. Kontrollera aktuell PR-status före varje nytt GitHub-ändringssteg.

## Start

1. Utgå från verifierad default branch och aktuell SHA.
2. Kontrollera om en relevant öppen Repository Fixer-PR redan finns.
3. Återanvänd den bara när dess head/base och status är verifierade och den fortfarande är relevant för samma åtgärdsomgång.
4. Annars skapas en ny `repository-fixer/...`-branch från aktuell default branch och därefter en PR.

## Före varje plansteg

- Läs om den aktiva PR:ns status.
- `open`: fortsätt i samma branch/PR.
- `merged`: läs om default branch och dess aktuella SHA; skapa därefter ny branch/PR om arbete återstår.
- `closed` utan verifierad merge: fortsätt inte automatiskt. Redovisa läget och begär/rekommendera säker fortsättning.
- okänd status: skriv inte förrän status kan verifieras.

En tidigare mergad arbetsbranch får aldrig behandlas som fortsatt aktiv bara för att branchen fortfarande existerar.

## Commitprincip

- Normalt exakt en naturlig commit per genomfört plansteg.
- Committen ska endast innehålla det godkända stegets ändringar.
- Använd ett kort beskrivande meddelande, gärna `docs:`, `ci:` eller `chore:` när kategorin är tydlig.
- Registrera plansteg, commit-SHA, branch och PR-nummer i GitHub-state.
- Skapa inte en extra tom commit bara för att uppfylla en mekanisk en-commit-regel.

## Avvikande PR-läge

Om base branch ändrats, PR:n divergerat, fått konflikter eller blivit irrelevant: behandla det som ett tillstånd som måste bedömas, inte som ett repository health-fynd. Ändra inte historik med force-push/rebase utan att det är den säkra och uttryckligen valda fortsättningen.

## Portabel state

`repository-github-write-state.schema.json` beskriver minsta state för default branch, base SHA, aktiv branch/PR, commitkopplingar och historik. Provider-/GitHub-verktyget utför nätverksoperationerna; state-maskinen bestämmer bara vilken skrivoperation som är säker härnäst.
