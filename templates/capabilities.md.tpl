# Rekommenderade Builder-capabilities

{{CAPABILITY_RECOMMENDATIONS}}

## Extern GitHub-skrivåtkomst

Repository Fixers branch/commit/PR-flöde kräver en **separat autentiserad GitHub-integration eller Action med skrivbehörighet**. Det är inte en vanlig Builder-toggle och följer inte automatiskt med detta paket.

Om sådan skrivåtkomst saknas ska GPT:n fortfarande analysera ett läsbart repository och producera rapport + plan, men den får inte påstå att branch, commit eller PR har skapats.

## Princip

Aktivera bara capabilities som behövs för arbetsflödet. Bildgenerering behövs inte för Repository Fixers kärnfunktion.
