P0 reroute after HOLD: close the implementation gap from Building adapter-timeout-frontier-lifecycle-hardening-0625.

Carry-forward evidence:
- Current worktree has uncommitted partial patch from adapter-timeout-frontier-lifecycle-hardening-0625 in:
  - support/recording/adapter_error_frontier.py
  - support/checkers/lib/kernel_checks.py
- That Building paused with frontier_kind=link_paused.
- QA transition concern: transition-concern:adapter-timeout-frontier-lifecycle-hardening-0625-code-attack-qa:partial-write-risk-coverage-gap.

QA concern summary to address:
1. The patch only admits clean declaration+report roots. A genuine partial-write root containing non-declaration artifacts still makes _root_holds_only_declaration_chain_artifacts return False, so capture.py can still raise FileExistsError and no frontier is recorded.
2. No positive structured evidence marker was added for partial-write-risk / root-exists-without-frontier state.
3. Existing-root predicates diverge: adapter_error_frontier.py widened predicate differs from run.py/walker_kernel.py preflight predicate.
4. report-thread identity check uses substring matching of expected_building_id in report_id and can falsely admit substring-collision ids.
5. Runtime checker execution was not observed by QA because python was blocked in that sandbox; this follow-on should run targeted checkers if possible.

Brick objective:
Produce the smallest root fix that satisfies the original acceptance criteria, especially partial-write-risk observability, without overwriting unrelated evidence or adding runtime scheduler/queue/retry behavior.

Required behavior / acceptance evidence:
1. Timeout/interruption before AgentFact return must produce observable adapter-error/frontier evidence even when the Building root already exists from declaration/report artifacts.
2. If the root has possible partial write/non-declaration artifacts and safe overwrite is not allowed, the system must still leave an observable frontier/evidence marker for adapter_error/interrupted/partial-write-risk or equivalent; do not simply raise FileExistsError with no frontier. Preserve unrelated evidence.
3. Operator can distinguish complete frontier, adapter-error frontier, root exists without frontier, and partial-write-risk from admitted evidence/static files.
4. Align or explicitly document the relationship between existing-root predicates used by adapter_error_frontier and preflight/walker paths so they do not silently drift.
5. Tighten report-thread identity so substring-collision building ids are rejected.
6. Add/update narrow checker coverage that exercises clean declaration+report root, wrong-building report rows including substring collision, and partial-write-risk root observability. Run the targeted checker/case, git diff --check, and compile/import smoke if possible. Avoid broad --all loop.
7. Preserve BRICK law: support evidence only; no source truth/success/quality/Movement authority; no new Movement literal; no hidden target selector; no scheduler/queue/retry runtime; no credential/session bodies.

Grounding files:
- project/brick-protocol/buildings/adapter-timeout-frontier-lifecycle-hardening-0625/work/step-outputs/*/step-output.json
- project/brick-protocol/buildings/adapter-timeout-frontier-lifecycle-hardening-0625/evidence/spine/events/0024-Frontier.json
- support/recording/adapter_error_frontier.py
- support/recording/capture.py
- support/operator/run.py
- support/operator/walker_kernel.py
- support/operator/walker_frontier.py
- support/checkers/lib/kernel_checks.py
- support/checkers/profiles/building_automation.yaml

Return shape:
made_changes, changed_files, observed_evidence, commands_run, blocked_or_missing_evidence, handoff_refs, not_proven.
