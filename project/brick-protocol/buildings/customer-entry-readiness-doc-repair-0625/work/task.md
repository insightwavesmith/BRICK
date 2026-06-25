# G1b customer-entry/readiness doc repair
Implement the smallest customer-entry readiness repair from Wave1.
Write scope is intentionally narrow.
Required work:
1. Update support/docs/references/setup.md line that says 13 profiles so it reflects the current measured 24 profile files, without editing AGENTS.md.
2. Add a status record project/brick-protocol/status/kernel/customer-entry-readiness-reconciliation-0625.md that records: current counts profiles=24 presets=28; AGENTS.md count drift is intentionally not edited because AGENTS mutation is high-impact and needs explicit Smith disposition; checker-split-map-0611 is historical evidence; remaining readiness blockers for P12.
3. Run only narrow checks appropriate to docs/status edit: git diff --check and any targeted grep/count checks. Avoid broad --all.
4. Return changed_files, commands_run, observed_evidence, not_proven, and remaining_delta.
