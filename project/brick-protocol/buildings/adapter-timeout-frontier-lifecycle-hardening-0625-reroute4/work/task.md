P0 reroute4 after HOLD: close the remaining report_id infix event-marker collision.

Current dirty patch spans:
- support/recording/adapter_error_frontier.py
- support/checkers/lib/kernel_checks.py
- support/operator/run.py
- support/operator/walker_kernel.py

Carry-forward evidence to read first:
- project/brick-protocol/buildings/adapter-timeout-frontier-lifecycle-hardening-0625-reroute3/work/step-outputs/*/step-output.json
- project/brick-protocol/buildings/adapter-timeout-frontier-lifecycle-hardening-0625-reroute3/evidence/spine/events/0025-Frontier.json
- current git diff for the four changed files

Exact QA concern to close:
- transition-concern:adapter-timeout-frontier-lifecycle-hardening-0625-reroute3-code-attack-qa:report-id-infix-marker-collision-residual
- _report_id_source_id uses `marker in report_id` + leftmost str.partition over unordered _REPORT_EVENT_SUFFIXES. It must parse the trailing reporter event suffix, not any marker inside a building id.

Required fix:
1. Make _report_id_source_id parse report ids by a deterministic right-anchored known suffix/timestamp shape. It must not split on event-kind markers embedded inside the building/source id.
2. Reject crafted IDs like `brick-protocol-<expected>-gate-passed-event-evil-building-started-event-<timestamp>` for expected `<expected>`.
3. Preserve legitimate same-building emitted forms and legacy `report:<building_id>:...` exact matching.
4. Add checker coverage for the embedded event-marker collision and deterministic parsing. Keep previous prefix/suffix collision tests.
5. Run targeted adapter_error_path_hardening checker or direct kernel check if possible, git diff --check, compile/import smoke if possible. If execution is blocked, record not_proven but keep checker precise.
6. Preserve BRICK law: support evidence only; no source truth/success/quality/Movement authority; no scheduler/queue/retry runtime; no credential/session bodies; no AGENTS.md edits.

Return shape:
made_changes, changed_files, observed_evidence, commands_run, blocked_or_missing_evidence, handoff_refs, not_proven.
