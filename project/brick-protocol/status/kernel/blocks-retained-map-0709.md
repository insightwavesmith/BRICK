# ⑩b Blocks Retained / Archive / Superseded Map — 0709

Status: support evidence only. This document does not delete, move, archive,
rename, or edit any block file. It records a live-evidence retained/archive/
superseded map for `brick_protocol/brick/templates/blocks/` so a later declared
Building (or a direct-preset docs edit, if trivially proven) can act without
deleting load-bearing corpus by assumption. It is not source truth, success
judgment, quality judgment, or Movement authority.

## 0. Scope

This is phase ⑩b from:

```text
project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
```

It builds on ⑩a:

```text
project/brick-protocol/status/kernel/cleanup-scope-invariants-0709.md
```

⑩a invariant for this surface:

```text
templates/blocks: do not delete; first create retained/archive/superseded map
and prove no load-bearing refs. Prefer archive/superseded labels over deletion.
```

This document is that map.

## 1. What a block is (measured)

Evidence from `brick_protocol/support/checkers/check_package_path_admission.py`:

```text
lines 1051-1057 (dir branch):
  parts == ["brick", "templates", "blocks"] is admitted as the blocks corpus
  directory under the existing Brick template family.

lines 1122-1127 (file branch):
  brick/templates/blocks entries are documentation corpus only, admitted as
  Brick template docs. They may carry front matter and a DSL snippet for
  human/COO authoring vocabulary, but "no operator/CLI/materializer reads this
  directory."
```

Evidence from a block file (`b1-zone-partition-fan.md` front matter):

```text
schema: brick-block/v1
proof_limits:
  - block is documentation only, not executable, not a recommendation engine
  - zone count and zone boundaries remain caller or COO declarations
```

Conclusion: blocks are an authoring-vocabulary corpus. They are load-bearing
for the admission checker (which explicitly admits the directory and its slugged
`.md` docs), but they are not consumed by any runtime/materializer surface.

## 2. Reference measurement (0709 snapshot)

Directory contents:

```text
brick_protocol/brick/templates/blocks/ files=8
  b1-zone-partition-fan.md
  b2-verification-lens-fan.md
  b3-deliberation-panel.md
  b4-completeness-critique-tail.md
  b5-high-trust-small-serial.md
  b6-human-gate-close.md
  b7-unknown-size-expansion.md
  b8-until-dry-rounds.md
```

Inbound reference scan (git grep over `brick_protocol`, `project`, `AGENTS.md`,
`README.md`):

```text
- No operator/CLI/materializer/preset/shape/catalog file references any block
  file path or block_id.
- Presets do NOT back-reference blocks (block_id B1..B8 / block titles absent
  from presets and shapes).
- Only status/kernel planning docs and the block files themselves mention the
  blocks corpus.
- check_package_path_admission.py is the one code surface that admits the
  directory; it reads no block content at runtime.
```

Outbound reference integrity (each block `related_presets` -> existing preset):

```text
b1 zone-partition-fan     -> recon-fleet, recon-fleet-light, triage-fanout-3     [all exist]
b2 verification-lens-fan  -> design-build-parallel, governed-change-review, high-risk-change-inspected  [all exist]
b3 deliberation-panel     -> design-contract-only, app-feature-inspected, governed-change-review        [all exist]
b4 completeness-critique  -> research-report, recon-fleet, postmortem            [all exist]
b5 high-trust-small-serial-> fast-fix, one-brick-do, quick-check                 [all exist]
b6 human-gate-close       -> brick-protocol-constitution-change, governed-change-review, high-risk-change-inspected [all exist]
b7 unknown-size-expansion -> brick-protocol-post-d-cleanup, high-risk-change-inspected                  [all exist]
b8 until-dry-rounds       -> postmortem-fleet, review-fleet, recon-fleet         [all exist]

dangling related_presets: NONE (every referenced preset file exists under
brick_protocol/brick/templates/presets/).
```

Measurement commands used:

```text
ls brick_protocol/brick/templates/blocks/
git grep -n -E "templates/blocks|block_id|B[1-8]" over brick_protocol/project/AGENTS.md/README.md
python3 front-matter related_presets vs presets/*.md set-difference
```

Proof limit: this is a 0709 snapshot, not a permanent dependency graph.

## 3. Retained / archive / superseded decision

| Block | Motif | related_presets valid | Runtime reader | Decision |
|---|---|---|---|---|
| b1-zone-partition-fan.md | read-only zone fan | yes | none | RETAIN |
| b2-verification-lens-fan.md | verification lens fan | yes | none | RETAIN |
| b3-deliberation-panel.md | deliberation panel | yes | none | RETAIN |
| b4-completeness-critique-tail.md | completeness critique tail | yes | none | RETAIN |
| b5-high-trust-small-serial.md | high-trust small serial | yes | none | RETAIN |
| b6-human-gate-close.md | human gate close | yes | none | RETAIN |
| b7-unknown-size-expansion.md | unknown-size expansion | yes | none | RETAIN |
| b8-until-dry-rounds.md | until-dry rounds | yes | none | RETAIN |

Summary:

```text
RETAIN:     8
ARCHIVE:    0
SUPERSEDE:  0
DELETE:     0
```

Rationale:

```text
- Every block is a distinct authoring motif with no duplicate motif observed.
- Every block's related_presets resolve to existing presets, so the corpus is
  coherent with the current preset catalog.
- The admission checker actively admits the directory and its slugged docs, so
  deleting a block would require a coordinated admission/checker change, not a
  cleanup convenience.
- No runtime surface reads blocks, so there is no stale-runtime-coupling reason
  to remove them either.
```

## 4. What ⑩b does NOT conclude

```text
- It does not mark any block for deletion.
- It does not merge or rename any block.
- It does not change the admission checker.
- It does not prove the motif content is high quality; it proves the corpus is
  coherent and load-bearing for admission, with valid preset links.
```

## 5. Follow-up conditions (only if a future change is requested)

If Smith later wants to remove or rename a block, the required evidence is:

```text
- Which motif is genuinely duplicated or dead (name the duplicate pair).
- A coordinated edit of check_package_path_admission.py admission expectations.
- Update of any block that shares the motif and of related_presets integrity.
- clean detached worktree: check_profile.py --all rc=0.
- git diff --check rc=0.
- GOAL/status update with remaining_delta.
```

Because that is a checker + admission coordinated change, it is Building work,
not a direct-preset docs edit.

## 6. Next operational candidate

```text
blocks decision: 8 retained, 0 archive/supersede/delete — no block cleanup Building needed now.
next cleanup candidate: ⑩d skills ship-copy drift map (agent/skills source vs templates/skills ship copy),
  or ⑩e COO order-chain skill/prompt/hook consistency.
route_v2_gate_state: ⑥d/⑥e remain held_for_human_gate until Smith/human approval
  (packet: project/brick-protocol/status/kernel/route-v2-human-gate-packet-0709.md).
```

## 7. Not proven

```text
- No blocks file was changed by this document.
- Motif quality/usefulness is not judged here.
- Future preset-catalog changes could later orphan a block; re-run the
  related_presets integrity scan when presets change.
```
