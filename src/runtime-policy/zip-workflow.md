# ZIP workflow policy

Canonical instruktionen styr beteendet. Denna policy fördjupar ZIP-flödet.

- Bevara hela repositorystrukturen och okända filer om det inte finns ett uttryckligt beslut att ändra dem.
- Packa alltid upp input till en separat arbetskopia; ändra aldrig den inkommande ZIP-filen.
- Avvisa path traversal, absoluta/drive-baserade sökvägar och symboliska länkar som inte kan hanteras säkert.
- Bevara en eventuell wrapper-katalog, doldfiler och exekverbara filrättigheter.
- Efter varje genomfört plansteg ska en komplett uppdaterad ZIP produceras, inte ett deltaarkiv.
- `.repository-fixer/` används som portabel arbetsstatus med analys, plan, progress och vid behov strukturerade JSON-varianter.
- Om portabel status finns vid återupptagning ska den läsas först och sedan verifieras mot aktuell repositoryversion.
- Arbetsmetadata ska inte blandas ihop med användarens ursprungliga projektfiler och får rensas inför slutleverans om användaren önskar det.
- En ZIP-leverans ska spegla exakt den repositoryversion som analyserats/ändrats, inte en rekonstruerad delmängd.
