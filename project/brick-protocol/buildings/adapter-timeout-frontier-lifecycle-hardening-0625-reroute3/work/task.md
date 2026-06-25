P0 reroute3 after HOLD: close the remaining report-id suffix-collision in adapter-error frontier lifecycle hardening.

Current dirty patch spans:
- support/recording/adapter_error_frontier.py
- support/checkers/lib/kernel_checks.py
- support/operator/run.py
- support/operator/walker_kernel.py

Carry-forward evidence to read first:
- project/brick-protocol/buildings/adapter-timeout-frontier-lifecycle-hardening-0625-reroute2/work/step-outputs/*/step-output.json
- project/brick-protocol/buildings/adapter-timeout-frontier-lifecycle-hardening-0625-reroute2/evidence/spine/events/0024-Frontier.json
- current git diff for the four changed files

Exact QA concern to close:
- transition-concern:adapter-timeout-frontier-lifecycle-hardening-0625-reroute2-code-attack-qa:report-id-suffix-collision-residual
- support/recording/adapter_error_frontier.py report_id matcher still has an `endswith(f'-{expected}')` style fallback that admits an unrelated building id such as `rogue-prefix-<expected>` / `totally-other-<expected>-building-started` when report-thread rows have no `building_id` field.

Required fix:
1. Make report-thread/report_id matching exact for admitted known shapes. The matcher must admit legitimate same-building forms actually emitted by report-thread rows, but reject both prefix and suffix/infix collisions.
2. If same-building live vessel form needs a project/vessel prefix such as `brick-protocol-<building_id>-...`, encode that shape explicitly or derive it safely from known report packet shape; do not use broad suffix matching.
3. Update checker coverage to include:
   - legitimate live vessel-form report_id for the same building
   - prefix collision `<expected>-reroute1` rejected
   - suffix collision `rogue-prefix-<expected>` rejected
   - legacy `report:<building_id>:...` exact admitted and `report:<other>:...` rejected
4. Keep previously fixed partial-write-risk/root-state behavior intact.
5. Run targeted checker/case if possible, git diff --check, and compile/import smoke if possible. If execution is blocked, record not_proven, but keep the checker code precise.
6. Preserve BRICK law: no source truth/success/quality/Movement authority, no scheduler/queue/retry runtime, no credential/session bodies, no AGENTS.md edits.

Return shape:
made_changes, changed_files, observed_evidence, commands_run, blocked_or_missing_evidence, handoff_refs, not_proven.
