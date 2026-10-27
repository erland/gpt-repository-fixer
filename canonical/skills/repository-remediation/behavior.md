# Repository Remediation – canonical Skill-beteende

## `repository-fix-plan.md`

Planen ska byggas från **samtliga öppna fynd** i den kompletta analysen. Prioritering påverkar ordning, inte om fynd tas med. Varje öppet fynd ska finnas i planens källfynd och ett naturligt plansteg, eller redovisas som utanför scope med motivering. Dela stora grupper i små steg som normalt ryms i en användarprompt. Följ `fix-plan.md` och `repository-fix-plan.schema.json`.

## Interaktivt åtgärdsflöde

Före varje plansteg visar du kort mål, skäl, filer, risk och beslut. Användaren kan göra steget, hoppa över, be om detaljer eller ändra förslaget. I åtgärdsfasen ska "Gör nästa steg" återuppta `in-progress`, annars välja första säkert genomförbara steg; ett blockerat steg får inte dölja senare oberoende arbete. Starta aldrig ett blockerat steg.

## ZIP-flöde

ZIP: arbeta i separat säker arbetskopia, bevara hela strukturen och lämna komplett uppdaterad ZIP efter ändringssteg. Håll portabel status i `.repository-fixer/`. Vid återupptagning: läs status först och verifiera den mot repositoryt. Radera inte tveksamma filer utan evidens och vid osäkerhet godkännande.

## GitHub-flöde

När input är en GitHub-länk och skrivåtkomst finns:

1. analysera repositoryt före ändringar,
2. kontrollera default branch och aktuell repository-/PR-status,
3. skapa eller återanvänd en Repository Fixer-arbetsbranch och PR när åtgärdsfasen börjar,
4. återanvänd samma öppna PR så länge den är relevant,
5. gör normalt ett naturligt plansteg per commit,
6. kontrollera PR-status före varje nytt GitHub-ändringssteg,
7. om föregående PR har mergats, utgå från aktuell default branch och skapa ny branch/PR,
8. fortsätt inte blint på stängd, divergerad eller olämplig PR.

Skriv inte direkt till default branch som standard. Om skrivåtkomst saknas får du fortfarande analysera, men låtsas inte att du kan skapa branch, commit eller PR.
