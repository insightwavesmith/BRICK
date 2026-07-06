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

## Fourth z6 candidate verdict — rev-1 re-investigation (t10rev1-0706n)

Status: `unresolvable-by-evidence` — CONFIRMED at rev-1. No file is moved by
this record; no substitute candidate is guessed.

Searched domains (뒤진 곳):

- Full kernel root enumeration: all 74 `*.md` under
  `project/brick-protocol/status/kernel/`.
- Fresh whole-repo reference re-census: `grep -rIl` (excluding `.git`,
  `__pycache__`) per kernel basename, self-mention excluded.
- `archive/0705-legacy-refgraph/` — confirms the three already-moved records
  are present.
- `t10-drive-runbook-0705.md` §5 — prior rev-1 discovery result ("evidence
  cannot identify it").
- `legacy-refgraph-census-0705.md:30-34` — candidate #2 rows.

Domains not searched / absent (안 뒤진 곳):

- `project/brick-protocol/buildings/legacy-refgraph-0705/` evidence tree —
  ABSENT in this worktree (`test -d` = MISSING). This tree holds the 380-row z6
  atomic inventory whose row named the fourth candidate; it is not present here.
- git history, other worktrees, and building-session step-output raw data —
  outside the declared write_scope and not locally present.

Why a fresh re-census cannot substitute (measured): (a) repo state drifted
since 0705 — the three candidates were already moved out of the kernel root and
new 0706 docs were added; (b) the original z6 inventory is absent.

No-guess compliance: the fresh re-census found 7 zero-reference kernel docs
(`bundle11b-order-draft-0705`, `fixture-graph-helpers-spec-0704`,
`handoff-coo-0705night-continuous`, `handoff-coo-0706afternoon`,
`handoff-coo-0706evening`, `handoff-external-audit-track-0705`,
`onboarding-minimal-set-0702`); these are recent 0705/0706 live handoffs or
active drafts, not completed-history archive profile, so none is nominated as
the fourth candidate.

Move execution: none. Any archive move of a fourth candidate remains rev-2's
(follow-on v2b approval building) responsibility; this record is
discovery-only.

Proof limits: rev-1 re-investigation note only. Does not move files, select a
substitute candidate, rewrite prior rows, judge success or quality, or choose
Link Movement.
