# Historiska testankare som ersatts vid fem-runtime-migrering

Detta är spårbarhetsunderlag, **inte aktiva körbara tester**. De tre
ursprungliga testfilerna har ersatts med tester för canonical 1.6.33 och
exakt fem aktiva runtimes. Regres­sionsinventeringen pekar hit för att
bevara namn och avsikt. De aktiva kontrollernas styrka ska värderas
separat före slutligt migrationsgodkännande.

## Historiska tester i tests/test_release_readiness.py

- `test_release_readiness_detects_instruction_divergence`:
  Ändrade Custom GPT:s `builder/instructions.md` till avvikande text
  och krävde att äldre release readiness underkände paketet.
  Ersättning för canonical-migreringen behöver testa motsvarande
  instruktionsintegritet i aktiva runtimepaket, inte bara rubriknärvaro.
- `test_release_readiness_detects_knowledge_divergence`:
  Ändrade `chat/knowledge/finding-model.md` och krävde upptäckt av
  innehållsavvikelse. Canonical Knowledge-filtäckning och resursparitet
  finns nu som aktiva gates, men på annat urval/distributionsformat.

## Historiskt test i tests/test_custom_gpt_distribution.py

- `test_custom_gpt_uses_all_canonical_knowledge`:
  Kontrollerade att historisk Custom GPT inte tappade Knowledge och
  att instruktionen rymdes inom dess gamla maxlängd. Custom GPT är nu
  avsiktligt inaktiverad; ersättande Knowledge-kontroll gäller fem
  aktiva runtimes och bygger inte på Custom GPT:s gräns.

## Varför detta inte är en verifieringsrapport

Att historiska testnamn finns här bevisar enbart spårbarhet.
Inventeringens `replacement` och `canonical_gate` avgör separat
vilka skydd som ännu saknar funktionell, negativ verifiering.
