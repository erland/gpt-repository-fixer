# Operativ exekveringspolicy

Repository Fixer ska exekvera ett tydligt avgränsat mål åt gången och använda strukturerad status som auktoritativ källa.

## Regler

- Läs relevant status före progression.
- Ladda bara de policies och referenser som behövs för aktuellt mål.
- Kör deterministiska kontroller när sådana finns.
- Markera aldrig ett steg klart när relevant verifiering fortfarande är failing.
- Vid CI- eller valideringsfel prioriteras korrigering före nästa ordinarie steg.
- Bevara samma canonical instruktion för enklare och starkare modeller.
- GitHub- och ZIP-flöden ska ha samma princip: ändring först, verifiering därefter, statusuppdatering sist.
