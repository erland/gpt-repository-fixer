# Deterministiska E2E-repositories

Fixture-setet täcker utvecklingsplanens steg 19:

1. `clean-node` – litet välskött Node/Vite-repository.
2. `stale-react-readme` – pnpm-repo med gammal npm-instruktion.
3. `java-wrong-version` – Maven/Java 21 med README som anger Java 17.
4. `partial-ci-fullstack` – frontend + backend där CI bara täcker frontend.
5. `no-license` – repository utan uttalad licens.
6. `license-conflict` – README anger MIT medan LICENSE är Apache-2.0.
7. `temporary-files` – tydligt lokalt/genererat skräp.
8. `ambiguous-old-file` – historisk fil som fortfarande refereras och inte får raderas automatiskt.

`tests/test_e2e_scenarios.py` återanvänder dessa även för fler-stegs ZIP-flöde och GitHub-PR-livscykler. Alla fixtures är lokala och deterministiska; testerna kräver inget nätverk.
