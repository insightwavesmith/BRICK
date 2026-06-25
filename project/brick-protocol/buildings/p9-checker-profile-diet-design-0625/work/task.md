# P9 checker/profile diet design

Read-only design/investigation for reducing checker/profile complexity after P5/P7.

Goal:
Produce a concrete diet plan without editing files. The plan should classify existing checker/profile surfaces by function and propose next Buildings with disjoint write scopes.

Required analysis:
1. Classify checker/profile families into: admission, boundary, runtime smoke, fixture, customer proof, reporter/dashboard/product projection.
2. Identify likely heavy/duplicative profiles and why they are heavy.
3. Separate deterministic fixture checks from live provider checks, especially around gemini-api vs gemini-local.
4. Identify which profile(s) should own four-llm preset completion and which should not.
5. Propose 3-5 concrete follow-on Buildings with write scopes and stop conditions.
6. State not_proven and proof limits.

Read scope suggestions:
- support/checkers/profiles/*.yaml list/count only
- support/checkers/check_profile.py
- support/checkers/lib/case_runners.py high-level rules only
- support/checkers/lib/kernel_checks.py high-level kernel_check list only
- support/docs/references/architecture-map.md if needed

Constraints:
- Do not modify files.
- Do not run broad `--all`.
- Keep output as support evidence only; no success/quality/source-truth/Movement claims.
