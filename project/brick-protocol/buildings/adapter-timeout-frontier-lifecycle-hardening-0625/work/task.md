P0 repair: harden Building adapter-timeout and frontier lifecycle handling.

Trigger evidence:
During P6 follow-on, official Building `gap2-customer-entry-minimum-doc-fix-0625` invoked `adapter:codex-local`. Codex made in-scope partial doc changes, but the adapter timed out before an AgentFact returned. The runner then tried to write adapter-error frontier evidence, but failed with FileExistsError because the Building lifecycle root already existed. Result: no Frontier.json, no adapter-error record, partial write remained, and the operator could not cleanly distinguish running vs failed vs partial-write-unclosed. The partial failed root was preserved outside the repo at /tmp/brick-partial-gap2-customer-entry-minimum-doc-fix-0625-20260625-114400 for local evidence only.

Brick objective:
Implement the smallest root fix so timeout/interruption after a Building root exists always records observable lifecycle/frontier evidence instead of raising FileExistsError or leaving an ambiguous root.

Required behavior / acceptance evidence:
1. If a local CLI adapter times out or is interrupted before AgentFact return, the Building evidence root must get an adapter-error frontier or equivalent observable frontier, even if the root already exists from intake/materialization/report records.
2. Existing-root handling for adapter-error/frontier writes must not use the same collision rule as creating a brand-new Building root. It should append/update admitted lifecycle evidence safely without overwriting unrelated evidence.
3. If a timeout happens after possible writes, evidence should make the state distinguishable as adapter_error / interrupted / partial-write-risk or equivalent; do not classify it as success/failure/quality.
4. The operator must be able to distinguish at least: complete frontier, adapter-error frontier, root exists without frontier, and partial write risk from evidence/static files.
5. Preserve BRICK law: support records evidence only; no support success/quality judgment; no new Movement literal; no hidden route target selector; no scheduler/queue/retry runtime.
6. Add or update a narrow checker/fixture if an admitted checker surface exists; otherwise add the minimum checker profile/case required to pin this failure mode. Avoid a broad `--all` loop during implementation; run targeted checker(s), `git diff --check`, and compile/import smoke if relevant.

Grounding files to inspect first:
- support/operator/run.py
- support/operator/walker_kernel.py
- support/operator/walker_frontier.py
- support/recording/adapter_error_frontier.py
- support/recording/capture.py
- support/operator/driver.py
- support/connection/adapter_subprocess.py
- support/connection/adapter_local_cli.py
- support/checkers/check_profile.py
- support/checkers/lib/case_runners.py
- support/checkers/profiles/*.yaml relevant to adapter error, lifecycle, dynamic walker, building intake
- project/brick-protocol/buildings/gap2-customer-entry-minimum-doc-fix-0625b/work/step-outputs/*/step-output.json for the observed P6 context

Write scope:
Keep edits narrow to support operator/recording/connection/checker/profile/docs status surfaces needed for the root fix. Do not edit AGENTS.md. Do not add scheduler/queue/retry runtime. Do not store provider request bodies or credentials.

Return shape:
made_changes, changed_files, observed_evidence, commands_run, blocked_or_missing_evidence, handoff_refs, not_proven.
