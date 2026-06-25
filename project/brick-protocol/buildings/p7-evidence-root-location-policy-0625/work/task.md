# P7 evidence root location policy cleanup

Resolve the recurring confusion where Building evidence roots land under `/Users/smith/.brick/project/brick-protocol/buildings` while status outputs are committed from the active worktree.

Question to answer first:
Is this an engine code change? Current evidence suggests the first cause is BRICK_HOME/output_root configuration: when BRICK_HOME is unset, DEFAULT_BUILDINGS_ROOT resolves to ~/.brick/project/brick-protocol/buildings. But the system may still need docs or reporter/status clarity.

Required work:
1. Measure current root derivation from support/recording/capture.py, support/operator/driver.py, and environment (`BRICK_HOME`, explicit output_root behavior).
2. Determine minimal fix category:
   A. no engine code: use explicit output_root/BRICK_HOME in dogfood building launch and document it;
   B. small support/reporting fix: make reports/status clearly show out-of-worktree evidence roots;
   C. engine change only if code evidence proves current behavior violates admitted contract.
3. Implement the minimal accepted fix. Prefer docs/status/operator guidance over core engine changes unless necessary.
4. Write a concise report to project/brick-protocol/status/kernel/p7-evidence-root-location-policy-0625.md.
5. Run compact checks for touched files. If code changed, run py_compile and a targeted profile/checker if applicable.

Allowed writes:
- support/docs/**
- support/operator/reporter.py
- support/operator/driver.py
- support/recording/capture.py
- project/brick-protocol/status/kernel/p7-evidence-root-location-policy-0625.md

Forbidden:
- Do not edit support/checkers/** in this Building.
- Do not edit AGENTS.md, agent/, brick/templates/presets/four-llm-standard-graph.md, or provider credentials.
- Do not change source truth, quality judgment, success judgment, or Movement authority semantics.

Return support evidence only.
