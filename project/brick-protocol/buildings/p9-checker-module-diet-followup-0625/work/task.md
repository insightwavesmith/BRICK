# P9 checker/module diet follow-up

Read-only follow-up to the prior P9 HOLD. Complete the missing six-family classification and extend the diet plan to include module cleanup without performing implementation.

Goal:
Produce a concrete, phaseable checker/profile/module cleanup plan that can safely run before P12 customer capstone without becoming a giant rewrite.

Required analysis:
1. Deliver the explicit six-family checker/profile map:
   - admission
   - boundary
   - runtime smoke
   - deterministic fixture
   - customer proof
   - reporter/dashboard/product projection
2. Include module cleanup angle: use support/docs/references/architecture-map.md and support/checkers/module_registry.yaml to identify god modules, duplicate support families, stale/dead surfaces, and module-boundary risks.
3. Separate what can be deleted/merged now vs what needs an admission/checker first.
4. Identify write-scope conflicts (especially support/checkers/profiles/core.yaml / module_registry.yaml / case_runners.py) and propose sequential vs parallel Buildings.
5. Produce 3-6 concrete follow-on Buildings with write_scope, stop condition, and checker gates.
6. State not_proven and proof limits.

Constraints:
- Read-only. Do not edit files.
- Do not run broad `--all`.
- Do not claim success, quality, source truth, or Movement authority.
- Treat module/checker output as support evidence only.
