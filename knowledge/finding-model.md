# Fyndmodell och evidens

Repository Fixer använder en gemensam fyndmodell så att analysen blir spårbar och jämförbar mellan repositoryn.

## Klassificering

| Intern kod | Rapportetikett | Använd när |
| --- | --- | --- |
| `must-fix` | **Bör åtgärdas** | Det finns ett konkret fel, saknad viktig information eller verifierad inkonsistens. |
| `recommended` | **Rekommenderas** | Evidensen visar en tydlig kvalitetsförbättring, men repositoryt är inte direkt felaktigt. |
| `consider` | **Överväg** | Frågan är projekt-, organisations- eller preferensberoende. Presentera inte detta som ett fel. |
| `passed` | **Godkänd kontroll** | Området har faktiskt kontrollerats och inget relevant problem hittades. |

Klassificeringen är **inte en generell severity-skala**. Ett `must-fix` betyder att något verifierbart bör korrigeras inom Repository Fixers uppdrag; det betyder inte automatiskt säkerhetskritisk eller produktionsblockerande.

## Evidenskrav

Negativa fynd (`must-fix` och `recommended`) måste ha minst ett konkret evidensobjekt. `consider` ska också ha evidens när observationen bygger på repositoryt, men kan användas för ett uttryckligt design- eller policyval där repositoryt inte ensamt kan avgöra rätt svar.

Evidens ska beskriva **vad som observerats**, inte bara slutsatsen. Använd så specifik källa som rimligt:

- `file` – innehåll i en enskild fil
- `configuration` – build-, package-, runtime- eller annan konfiguration
- `command` – resultat från build/test/lint eller motsvarande kommando
- `runtime` – verifiering från körning i tillgänglig miljö
- `cross-file` – verifierad inkonsistens mellan två eller flera filer
- `absence` – något som rimligen borde finnas men saknas, exempelvis README eller CI för ett byggbart projekt

`path` ska anges när evidensen hör till en fil. Radnummer är frivilliga och ska bara anges när de är kända; hitta inte på dem. För `cross-file` kan `related_paths` användas.

Bra evidens:

> `README.md` instruerar `npm run dev`, medan `package.json` saknar scriptet `dev`.

Dålig evidens:

> README är dålig.

## Confidence

- `high` – direkt och entydig evidens, exempelvis konkret filinnehåll eller verifierat kommandoutfall.
- `medium` – stark slutsats men viss projektspecifik tolkning krävs.
- `low` – osäker observation. Använd normalt `consider` eller dokumentera osäkerheten i stället för att formulera ett starkt fel.

Confidence får aldrig användas för att dölja ett antagande som om det vore verifierat.

## Beslutspunkter

Sätt `decision_required=true` när en åtgärd kräver ett verkligt användarval, exempelvis licens, copyright-innehavare, osäker filborttagning eller en större beteendeförändring i CI. `decision_reason` ska då förklara exakt vad användaren behöver besluta.

## Godkända kontroller

`passed` ska bara användas när kontrollen faktiskt utförts. Skriv inte generiska PASS-poster för områden som inte varit relevanta eller inte kunnat verifieras. `recommended_action` ska vara `null` för godkända kontroller.

## Stabil identifiering

Fynd-id följer `RF-<AREA>-NNN`, exempelvis `RF-README-001` eller `RF-CI-002`. Behåll samma id inom samma analys-/åtgärdsflöde så att plan, progress och slutrapport kan referera till fyndet.

Det maskinläsbara kontraktet finns i `repository-finding.schema.json`.
