# status/kernel archive classification - 0702

Status: support evidence only. This record documents the doc-archive-0702e
work step's file movement and reference-string updates. It is not source truth,
not success judgment, not quality judgment, and not Link Movement authority.

## Scope

| Surface | Action | Evidence |
|---|---|---|
| `project/brick-protocol/status/kernel/*.md` | 127 closed/superseded root records moved to `archive/0702-doc-archive/` | Filesystem move inside declared write scope; `git mv` was attempted but the sandbox could not create the parent worktree index lock. |
| `project/brick-protocol/status/kernel/research-0626/*.md` | 6 research/support records moved under `archive/0702-doc-archive/research-0626/` | Old research records are retained as archive evidence, not active root status. |
| `project/brick-protocol/status/kernel/GOAL/*.json` | STAY | Design invariant: graph packets/GOAL JSON are not moved. |
| `project/brick-protocol/status/kernel/GOAL/*.md` symlinks | STAY, verified resolving | Targets remain active status docs. |
| `project/brick-protocol/status/inbox/*.json` | STAY / held | The carried design required consumer confirmation before moving inbox event streams; this work step did not prove that confirmation. |

## STAY root docs

| File | Reason |
|---|---|
| `brick-followon-doc-skill-checker-catalog-0701.md` | Caller-carried STAY candidate; current doc/skill catalog reference. |
| `brick-onboarding-provider-registration-redesign-0701.md` | Caller-carried STAY candidate; current onboarding/provider registration design. |
| `brick-p2-engine-dsl-3gap-design-synthesis-0702.md` | 0702 current synthesis. |
| `brick-workflow-standard-graph-design-0625.md` | Caller-carried STAY candidate; workflow standard design reference. |
| `checker-split-map-0611.md` | Caller-carried STAY candidate. |
| `customer-ready-closeout-goal-0630.md` | Active closeout/reload-chain anchor. |
| `customer-ready-goal-anchor-v01.md` | Compact reload anchor. |
| `customer-ready-goal-current-definition-0627.md` | Goal-of-record target for GOAL symlinks. |
| `customer-ready-goal-phases-0629.md` | Goal phase index and GOAL symlink target. |
| `customer-ready-p2-capability-taxonomy-plan-0628.md` | GOAL symlink target. |
| `customer-ready-p3-easy-building-official-route-plan-0628.md` | GOAL symlink target. |
| `customer-ready-p4-resume-fanout-plan-0628.md` | GOAL symlink target. |
| `customer-ready-p5-first-run-official-route-plan-0628.md` | GOAL symlink target. |
| `customer-ready-p6-cleanup-godmodule-plan-0628.md` | GOAL symlink target. |
| `customer-ready-p7-p8-pass-criteria-0629.md` | GOAL symlink target. |
| `customer-ready-plan-audit-roadmap-0629.md` | GOAL audit symlink target and active audit index. |
| `discipline-audit-0618.md` | Caller-carried STAY candidate. |
| `evidence-postmortem-task-template-0612.md` | Caller-carried STAY candidate. |
| `goal-phases-consolidated-0702.md` | 0702 current operating order. |
| `godmodule-checker-cleanup-synthesis-0701.md` | Current godmodule cleanup synthesis. |
| `install-ux-design-0618.md` | Caller-carried STAY candidate. |
| `onecall-worktree-loss-incident-0702.md` | 0702 active incident evidence. |
| `project-0-design-0611.md` | Caller-carried STAY candidate. |
| `routing-loop0-clustermap-0702.md` | 0702 current clustermap. |
| `skill-doc-resize-audit-0702.md` | 0702 audit/current resize evidence. |
| `toothless-profile-survey-0702.md` | 0702 current survey. |

## MOVE buckets

| Bucket | Count | Destination |
|---|---:|---|
| BRICK-6 closure/finding/audit/disposition/status records | 51 | `archive/0702-doc-archive/` |
| Customer-ready final-architecture proof/ledger records | 23 | `archive/0702-doc-archive/` |
| Customer-ready G-track proof/diagnostic records | 8 | `archive/0702-doc-archive/` |
| Customer-ready closeout records | 3 | `archive/0702-doc-archive/` |
| Customer-ready release records | 3 | `archive/0702-doc-archive/` |
| Old P2/P3/P4/P5/P7/P8 phase detail/proof records not targeted by GOAL symlinks | 17 | `archive/0702-doc-archive/` |
| 0612-0625 support records/checker diet/Gemini/Slack/GAP records | 18 | `archive/0702-doc-archive/` |
| Other superseded/follow-on status records | 4 | `archive/0702-doc-archive/` |
| 0626 research support records | 6 | `archive/0702-doc-archive/research-0626/` |

## Reference updates

| Update | Evidence |
|---|---|
| Live status Markdown references to moved root files now use `archive/0702-doc-archive/<file>`. | Bounded grep over live status Markdown found no stale bare moved filename references. |
| Live status Markdown references to moved `research-0626` files now use `archive/0702-doc-archive/research-0626/<file>`. | Bounded grep over live status Markdown found no stale `project/brick-protocol/status/kernel/research-0626/...` references. |
| `GOAL/` symlinks remain connected. | Symlink verification emitted no broken target rows. |

## Not moved

| Surface | Reason |
|---|---|
| `project/brick-protocol/status/kernel/GOAL/*.json` | Declared invariant: GOAL graph packets stay. |
| `project/brick-protocol/status/inbox/*.json` | Consumer-confirmation gate not proven in this Brick. |

## Commands evidence

```text
find project/brick-protocol/status/kernel -maxdepth 1 -type f -name '*.md' ...
ls -la project/brick-protocol/status/kernel/GOAL
git mv ...  # attempted; blocked by index.lock permission outside writable root
mv ...      # filesystem move inside declared write scope
rg ...      # stale live-reference checks
find project/brick-protocol/status/kernel/GOAL -maxdepth 1 -type l ... # symlink check
```

## Proof limits

- Plain filesystem moves were used because `git mv` could not write the parent
  repository worktree index lock from this sandbox.
- Counts are filesystem observations after the move, not source-truth or quality
  judgments.
- Inbox event-stream safety is not proven; inbox JSON files remain in place.
