# Fan-out node latency is not independently recorded — finding (0701)

Status: operator-discovered finding, support/evidence-integrity only. Not
source truth, success judgment, quality judgment, or Movement authority.
Routed as a P8 (ship-safety / evidence-integrity) candidate item.

## How this was found

While reviewing P7d (`brick-6-p7-easy-building-ergonomics-0701d`) evidence,
Smith noticed `work-docs` and `work-checker` are declared as independent
parallel fan-out lanes (each 1:1 into its own lane-QA node, no merge
between them) but their recorded `time` / `generatedAtTime` / `recorded_at`
timestamps in `raw/adapter-usage.jsonl` and their `step-output.json` files
were within the same second of each other
(`2026-07-01T02:27:41.052711Z` vs `2026-07-01T02:27:41.779547Z`, 0.73s
apart), which is implausibly close for two independent real Codex CLI
agent calls that each edit files and run checker/verification commands.

## Root cause (source-confirmed)

`support/operator/walker_kernel.py:1086-1119`, `_dispatch_ready_batch`:

```python
with ThreadPoolExecutor(max_workers=worker_count) as executor:
    futures = [
        (item, executor.submit(_process_item, item,
            record_step_output_immediately=False,
            defer_frontier_writes=True))
        for item in items
    ]
    return [(item, future.result()) for item, future in futures]
```

Fan-out dispatch IS real concurrent execution (genuine `ThreadPoolExecutor`
with `max_workers=worker_count`, not sequential-disguised-as-parallel).
But `record_step_output_immediately=False` defers recording: the batch
blocks on `future.result()` for every item, then
`_drain_pending_outcomes_before_terminal` (`walker_kernel.py:1192-1202`)
pops `pending_outcomes` one at a time in list order and calls
`_record_deferred_step_output`, which is what actually timestamps and
writes `step-output.json`. So the recorded timestamp reflects "when this
item's turn came up in the sequential post-batch drain queue," not "when
this item's own Agent call actually finished." Two lanes that took very
different real wall-clock durations can still land within well under a
second of each other in the recorded evidence, because the drain queue
itself is fast even though the underlying work was not.

A related, likely-connected symptom: both `work-docs` and `work-checker`
reported the identical full `changed_files` list (all files touched by
both lanes combined), which is consistent with each lane's own
`changed_files` extraction reading a shared-sandbox `git status`/`diff`
rather than a lane-scoped diff. This is the same root class of issue that
produced the `docs-lane-qa` `boundary_mismatch` concern investigated
earlier in P7d.

## What this does NOT prove

- Does not prove fan-out is fake or that dispatch is secretly sequential —
  the `ThreadPoolExecutor` dispatch code is real.
- Does not prove any Building's `frontier_kind`/closure result was wrong.

## What this DOES establish

- Current persisted evidence (`raw/adapter-usage.jsonl`, `step-output.json`)
  has no per-node `latency_ms` / `duration_ms` / `started_at`/`ended_at`
  field, so real per-lane execution duration and true concurrency cannot be
  independently verified from evidence alone — only inferred from the
  dispatch code path.
- `changed_files` as currently reported by a fan-out work lane is not
  reliably lane-scoped when lanes share one sandbox worktree.

## Recommended P8 scope addition (evidence-integrity)

1. Record real per-node call duration (`latency_ms` or `started_at`/
   `ended_at`) in the adapter dispatch path (`_process_item` /
   `AgentAdapterRequest` response handling) and thread it through to the
   persisted `raw/adapter-usage.jsonl` and `step-output.json`, so fan-out
   concurrency and per-lane cost are independently auditable evidence, not
   only inferable from source code.
2. Either lane-scope `changed_files` reporting (diff against the git state
   at that lane's own dispatch time, or restrict to paths inside the
   node's declared `write_scope.allowed_paths`) or explicitly document that
   `changed_files` on a shared-sandbox fan-out lane is a whole-sandbox
   snapshot, not a lane-exclusive diff, so QA lanes stop raising
   `boundary_mismatch` on legitimate sibling-lane pass-through.

## Proof limits

- No source mutation was performed to investigate this; read-only source
  and raw-evidence inspection only.
- Not scoped/estimated as a Building yet; recorded here so it is not lost
  before P8 graph declaration.
