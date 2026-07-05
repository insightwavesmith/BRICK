# status/kernel archive classification - 0705

Status: support evidence only. This record documents the legacy-refgraph-0705
kernel archive move. It is not source truth, not success judgment, not quality
judgment, and not Link Movement authority.

## Scope

| Surface | Action | Evidence |
|---|---|---|
| `project/brick-protocol/status/kernel/goal-loop-progress-0702night-0703am.md` | MOVE to `archive/0705-legacy-refgraph/goal-loop-progress-0702night-0703am.md` | `legacy-refgraph-census-0705.md` lists this root kernel record as an archive candidate; carried cleanup-wave-a design proposal requested archive with movement ledger. |
| `project/brick-protocol/status/kernel/handoff-0704-t10-dynamic-graph.md` | MOVE to `archive/0705-legacy-refgraph/handoff-0704-t10-dynamic-graph.md` | `legacy-refgraph-census-0705.md` lists this root kernel record as an archive candidate; carried cleanup-wave-a design proposal requested archive with movement ledger. |
| `project/brick-protocol/status/kernel/discipline-audit-0618.md` | MOVE to `archive/0705-legacy-refgraph/discipline-audit-0618.md` | `legacy-refgraph-census-0705.md` lists this root kernel record as an archive candidate; carried cleanup-wave-a design proposal requested archive with movement ledger. |
| `project/brick-protocol/status/kernel/reroute-adoption-hold-cases-0703.md` | STAY | `legacy-refgraph-census-0705.md` names this file as STAY because live citations exist. |
| `project/brick-protocol/status/kernel/session-continuity-mechanism-0703.md` | STAY | `legacy-refgraph-census-0705.md` names this file as STAY because live citations exist. |

## Moved Records

| From | To | Basis |
|---|---|---|
| `project/brick-protocol/status/kernel/goal-loop-progress-0702night-0703am.md` | `project/brick-protocol/status/kernel/archive/0705-legacy-refgraph/goal-loop-progress-0702night-0703am.md` | Archive candidate in `legacy-refgraph-census-0705.md`; cleanup-wave-a carried proposal required ledgered archive movement. |
| `project/brick-protocol/status/kernel/handoff-0704-t10-dynamic-graph.md` | `project/brick-protocol/status/kernel/archive/0705-legacy-refgraph/handoff-0704-t10-dynamic-graph.md` | Archive candidate in `legacy-refgraph-census-0705.md`; cleanup-wave-a carried proposal required ledgered archive movement. |
| `project/brick-protocol/status/kernel/discipline-audit-0618.md` | `project/brick-protocol/status/kernel/archive/0705-legacy-refgraph/discipline-audit-0618.md` | Archive candidate in `legacy-refgraph-census-0705.md`; cleanup-wave-a carried proposal required ledgered archive movement. |

## STAY Root Docs

| File | Reason |
|---|---|
| `reroute-adoption-hold-cases-0703.md` | `legacy-refgraph-census-0705.md` marks the file STAY because citations exist. |
| `session-continuity-mechanism-0703.md` | `legacy-refgraph-census-0705.md` marks the file STAY because citations exist. |

## Commands Evidence

```text
mkdir -p project/brick-protocol/status/kernel/archive/0705-legacy-refgraph
git mv ...  # attempted; blocked by index.lock permission outside writable root
mv ...      # filesystem move inside declared write scope
test -f ... # archive path and former root path checks
grep ...    # STAY rows in this ledger
git status --short -- project/brick-protocol/status/kernel
```

## Proof Limits

- Plain filesystem moves were used after `git mv` could not create the parent
  worktree index lock from this sandbox.
- The cleanup-wave-a design proposal is carried work-statement evidence in this
  step, not an independently observed in-scope kernel document.
- This record is an interpretation layer over moved archive documents; it does
  not rewrite the moved documents' contents.

## Fourth z6 candidate verdict (T10 first-drive discovery)

Status: `unresolvable-by-evidence`.

The fourth archive candidate from `legacy-refgraph-census-0705.md:30-33` is
recorded as evidence-unresolvable because the original z6 row identifying the
specific file is no longer present in the carried evidence. No filename is
inferred here, and no archive movement is authorized by this record.

Basis: `legacy-refgraph-census-0705.md:30-33` lists four kernel archive
candidates, names three moved records, and leaves the fourth only as "기타 z6
판정분". The same census rows state that
`reroute-adoption-hold-cases-0703.md` and
`session-continuity-mechanism-0703.md` are STAY because live citations exist, so
they are not the unresolved fourth archive candidate. The T10 first-drive record
in `t10-drive-runbook-0705.md` section 5 records the rev-1 discovery lane result
as: fourth z6 candidate = evidence cannot identify it; original z6 row is lost;
do not guess.

Proof limits: this section records the unresolved verdict only. It does not
move files, select a substitute candidate, rewrite the three moved-record rows,
rewrite the two STAY rows, judge cleanup success or quality, or choose Link
Movement.
