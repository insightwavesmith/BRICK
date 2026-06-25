P0 reroute2 after HOLD: close the remaining adapter-error frontier lifecycle gaps from adapter-timeout-frontier-lifecycle-hardening-0625-reroute1.

Current dirty patch:
- support/recording/adapter_error_frontier.py
- support/checkers/lib/kernel_checks.py
It already includes declaration/report root admission and a partial-write-risk marker, but QA found residual implementation gaps.

Carry-forward evidence to read first:
- project/brick-protocol/buildings/adapter-timeout-frontier-lifecycle-hardening-0625-reroute1/work/step-outputs/*/step-output.json
- project/brick-protocol/buildings/adapter-timeout-frontier-lifecycle-hardening-0625-reroute1/evidence/spine/events/0024-Frontier.json
- project/brick-protocol/buildings/adapter-timeout-frontier-lifecycle-hardening-0625/work/step-outputs/*/step-output.json
- current git diff for support/recording/adapter_error_frontier.py and support/checkers/lib/kernel_checks.py

QA concern to close exactly:
1. Live vessel/legacy report_id branch still false-admits prefix-related building ids. Example: expected base id `adapter-timeout-frontier-lifecycle-hardening-0625` wrongly matches live reroute id `brick-protocol-adapter-timeout-frontier-lifecycle-hardening-0625-reroute1-building-started-event-...` because the branch uses startswith/in substring with dash delimiters. Fix report_id matching so same-building is exact under known report-id shapes and prefix/infix collisions are rejected. Preserve legitimate live report IDs for the same building.
2. Partial-write-risk preservation currently only fires when `not overwrite_existing`; resume/overwrite path can clobber existing partial artifacts with no marker. Preserve partial-write-risk artifacts or explicitly refuse overwrite with an observable marker even when overwrite_existing=True; do not silently clobber unrelated evidence.
3. `root_exists_without_frontier` / empty-root / not-directory states produce no positive marker and can fall through to capture.py FileExistsError with no frontier. Add admitted observable marker/evidence for these states or otherwise make them distinguishable without raw exception only.
4. Checker coverage must exercise live vessel-form report IDs, prefix-collision IDs, empty/root-exists-without-frontier marker, and partial_write_risk through write_adapter_error_frontier_evidence end-to-end (not only direct helper calls). Keep it narrow in adapter_error_path_hardening/kernel_checks.
5. If run.py/walker_kernel preflight predicates intentionally remain narrower, add a reciprocal comment/checker note that makes the relationship explicit and prevents silent drift; do not add scheduler/queue/retry runtime.

Acceptance evidence:
- targeted checker/case runs if possible: `python3 support/checkers/check_profile.py --case adapter_error_path_hardening` or the project-correct equivalent.
- `git diff --check`.
- compile/import smoke for changed modules if possible.
- no AGENTS.md, .git, credential/token/secret edits.
- no source truth/success/quality/Movement authority claims.

Return shape:
made_changes, changed_files, observed_evidence, commands_run, blocked_or_missing_evidence, handoff_refs, not_proven.
