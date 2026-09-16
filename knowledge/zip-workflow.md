# ZIP-arbetsflöde och portabel progress

Den här filen fördjupar canonical instruktionens ZIP-regler.

## Säker arbetskopia

- Ändra aldrig användarens inkommande ZIP direkt. Packa upp till en separat arbetskopia.
- Avvisa ZIP-poster som försöker lämna arbetskatalogen (`..`), använder absolut/drive-baserad sökväg eller är symboliska länkar som inte kan hanteras säkert.
- Bevara repositoryts kompletta struktur, doldfiler och exekverbara filrättigheter.
- Om input-ZIP:en har en enda wrapper-katalog ska samma wrapper behållas i levererad ZIP.

## Portabel status

Under pågående ZIP-arbete används `.repository-fixer/` i repositoryroten. Minst följande mänskligt läsbara filer ska finnas när materialet finns:

- `analysis.md` – aktuell analysrapport
- `plan.md` – aktuell åtgärdsplan
- `progress.md` – faktisk åtgärdsstatus

För säker återupptagning får motsvarande `analysis.json`, `plan.json`, `progress.json` och en liten `state.json` också lagras. JSON är maskinkällan när den finns; Markdown är granskningsbar representation.

När en ny konversation får en ZIP med `.repository-fixer/state.json`, läs portabel status innan en ny analys eller plan skapas. Verifiera därefter att statusen fortfarande motsvarar repositoryt; anta inte att filer är oförändrade bara för att progress finns.

## Efter ett godkänt steg

1. gör endast det godkända stegets ändringar i arbetskopian
2. verifiera steget
3. uppdatera progress och eventuella rapport-/planartefakter
4. skriv om `.repository-fixer/` atomärt så långt det är praktiskt
5. paketera hela repositoryt, inte bara ändrade filer
6. leverera den nya ZIP:en

En misslyckad verifiering får fortfarande sparas som blockerad progress, men ZIP:en ska tydligt bära den statusen.

## Slutleverans

Vid slutleverans ska användaren kunna välja att behålla `.repository-fixer/` för spårbarhet eller ta bort katalogen för en ren repository-ZIP. Ta bara bort själva arbetsmetadatan; ändra inte projektfiler som en bieffekt av städningen.
