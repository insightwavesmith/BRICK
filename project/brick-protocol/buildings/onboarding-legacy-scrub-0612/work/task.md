# C3: Onboarding + legacy scrub — product ships clean to a stranger's machine

## Objective
A new company (or a fresh machine) must go clone -> install -> first building with zero Smith-environment residue. Recon (operator-verified) found a SHORT scrub list — fix exactly these, then prove the journey.

## Scrub list (verified)
1. README.md (root): hardcoded 'insightwavesmith' org in clone instructions -> parameterize ({OWNER} placeholder + one-line note), keep the working example.
2. support/docs/spec/README.md: 11 occurrences of /Users/smith/... absolute paths -> relative or placeholder paths.
3. agent/prompts/coo.md (~lines 58-68): Korean-only operational phrases block non-Korean operators -> keep Korean, ADD concise English equivalents alongside (bilingual; do not delete the Korean).
4. Vessel charter template: project/brick-protocol/README.md is Smith's Korean dogfood charter (KEEP, do not edit — it is declared history). ADD a company-neutral English charter TEMPLATE as a new file under brick/templates/ or support/docs/ (follow where project-creation expects templates) covering the 6 charter slots (why_exists, why_now, direction, done_means, out_of_scope, managers).

## Install journey proof (read-only walkthrough, no destructive ops)
Walk support/onboarding/install.sh + support/operator/onboard.py top to bottom and verify the documented journey matches the code (prereqs, idempotency, failure messages). Fix any doc/code mismatch you find (docs side preferred). Do NOT run the installer against the live machine; a temp-dir dry walkthrough of its pure functions is fine.

## Pins + FIRE
- No-Smith-residue pin: a checker probe that scans shipped product surfaces (README.md, support/docs/spec, agent/prompts) for /Users/smith literals and the hardcoded org outside honest-history allowances -> RED on a mutated copy that reintroduces one.
- Full gate: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all -> exit 0 (say which checkout/copy).

## Constraints
Write scope: support/*, README.md, agent/prompts/*, brick/templates/*. NEVER touch project/ (append-only), link/, agent/objects/. No npm/node. Keep Korean primary where it exists; bilingual not replacement. No pin weakening.
