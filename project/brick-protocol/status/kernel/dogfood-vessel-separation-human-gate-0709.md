# ⑩g Dogfood Vessel Separation Human-Gate Packet — 0709

Status: support/human-gate design evidence only. This packet does not move,
delete, rename, archive, migrate, implement, run a Building, choose Link
Movement, judge success/quality, or make source truth. It prepares the human /
Smith decision required before any `project/brick-protocol` dogfood vessel
separation work.

## 0. Gate question

The cleanup/customer-UX track identified that `project/brick-protocol/` is both:

```text
1. the current active dogfood project vessel, and
2. easy to confuse with product/source protocol surfaces.
```

The gate question is therefore:

```text
Should we open a declared Building to separate / clarify the dogfood evidence
vessel from product/source surfaces, and if yes, what separation shape is allowed?
```

Default state remains HOLD for any move/delete/migration until Smith chooses an
option in this packet or a later replacement packet.

## 1. Current live vessel facts

Observed live on 2026-07-09 KST at repo HEAD after ⑩f design:

```text
project/brick-protocol/project.json exists
project/brick-protocol/README.md exists
project/brick-protocol/PROGRESS.md exists
project/brick-protocol/buildings/ immediate entries: 58
project/brick-protocol/status/kernel/ files: 94
project/brick-protocol/status/inbox/ event files: 929
```

Current declaration:

```text
project_ref: project:brick-protocol
label: Brick Protocol (1호 — 자기개발 도그푸드)
direction: 3축 프로토콜로 사람+AI 협업을 증거 기반으로 만드는 엔진을 제품화한다
done_means: 체커 전체 green을 유지한 채 외부 팀이 이 프로토콜로 실제 일을 굴릴 수 있는 제품화 상태
charter_ref: project/brick-protocol/README.md
```

README also states the historical reason:

```text
The protocol was dogfooded before PROJECT-0. `project/brick-protocol/` was later
retroactively declared as project #1; history is frozen, migration absent,
declaration added.
```

Interpretation: this is not an accidental stray directory. It is an active,
declared vessel carrying current GOAL/status/building evidence.

## 2. Why immediate removal or move is forbidden

```text
- Active GOAL docs live under project/brick-protocol/status/kernel/.
- Building evidence roots live under project/brick-protocol/buildings/.
- Inbox events live under project/brick-protocol/status/inbox/.
- PROGRESS.md is a generated projection from buildings/ evidence.
- README.md + project.json form the charter/declaration pair guarded by
  project_declaration checks.
```

A simple `git mv project/brick-protocol ...` or deleting the vessel would break
current evidence references, status continuity, and project declaration meaning.
Any real move is a migration Building, not cleanup.

## 3. Separation options

### Option A — KEEP vessel, clarify language only (recommended now)

```text
action: no filesystem migration
allowed work: docs/status wording only
result: preserve project/brick-protocol as active dogfood vessel; add/maintain
  clear wording that it is project-local evidence/status, not product source.
```

Pros:

```text
- zero evidence migration risk
- preserves current GOAL/status/inbox continuity
- aligns with ⑩a invariant: no project vessel move before human gate
- lets ⑩f implementation and ⑥e/⑦ route-walker work proceed without evidence churn
```

Cons:

```text
- the path still visually resembles a product/source namespace
- future users may still ask why product source appears under project/
```

### Option B — DESIGN a future vessel split, no move yet

```text
action: produce a migration design with path inventory, reference map, checker
  scope, and rollback plan
allowed work: docs/checker planning only
forbidden: moving project/brick-protocol or rewriting evidence refs
```

Pros:

```text
- prepares a safer future move
- can estimate reference blast radius before any migration
```

Cons:

```text
- still costs attention while the active GOAL has ⑥e/⑦ and ⑩f implementation open
- design may go stale if more GOAL/status evidence lands first
```

### Option C — OPEN migration Building now (not recommended)

```text
action: declared Building to move or split current project vessel
requires: exact target path, reference rewrite plan, checker/profile coverage,
  PROGRESS/status/inbox/buildings continuity plan, rollback plan
```

Pros:

```text
- resolves naming confusion physically
```

Cons:

```text
- high risk while active GOAL/status/inbox/buildings are changing
- likely large reference rewrite
- may conflict with ⑩f implementation and ⑥e route/walker proof work
```

### Option D — ARCHIVE/DELETE historical evidence (forbidden)

```text
action: delete/archive active project vessel evidence
status: rejected
```

Reason:

```text
Active evidence/status cannot be deleted or archived as cleanup. Archive can be
considered only after a future closure/migration Building proves replacement
refs and preservation.
```

## 4. COO recommendation

Recommended human-gate choice:

```text
Option A now.
Keep project/brick-protocol as the active dogfood vessel and clarify language in
GOAL/status docs only. Do not move, delete, archive, or split it while ⑥e/⑦ and
⑩f implementation remain open.
```

Secondary allowed choice:

```text
Option B if Smith wants a future split map next.
Produce design only; do not migrate.
```

Not recommended:

```text
Option C migration now.
```

Rejected:

```text
Option D archive/delete.
```

## 5. If Smith approves Option B or C later: required migration Building scope

Candidate Building:

```text
building_candidate: cleanup-10g-dogfood-vessel-separation
route_family: governed-change-review or high-risk-change-inspected
worktree_required: true
live_checkout_run_building_intake: forbidden
```

Candidate read scope:

```text
project/brick-protocol/**
brick_protocol/support/operator/project_creation.py
brick_protocol/support/operator/progress_projection.py
brick_protocol/support/recording/capture.py
brick_protocol/support/checkers/check_project_declaration.py
brick_protocol/support/checkers/profiles/core.yaml
brick_protocol/support/checkers/**project*.*
project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
```

Candidate write scope for design-only Option B:

```text
project/brick-protocol/status/kernel/*dogfood-vessel*0709*.md
project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
```

Candidate write scope for implementation Option C (only after explicit approval):

```text
project/brick-protocol/** or new target vessel path
brick_protocol/support/recording/capture.py only if buildings_root_for/project_ref mapping must change
brick_protocol/support/operator/progress_projection.py only if vessel path derivation must change
brick_protocol/support/checkers/check_project_declaration.py
brick_protocol/support/checkers/profiles/*.yaml
brick_protocol/support/docs/references/*.md
project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
```

Required proof for any migration implementation:

```text
- changed_files, moved_files, deleted_files explicit
- old path policy: retained alias vs removed vs archived clearly stated
- project.json + README charter/declaration pair preserved
- PROGRESS.md regeneration behavior proven
- building evidence roots preserved or remapped with proof
- status/kernel and status/inbox continuity preserved or explicitly frozen
- project_declaration kernel green
- progress projection check green
- python3 -m compileall -q brick_protocol
- python3 brick_protocol/support/checkers/check_profile.py --profile core
- clean detached worktree: python3 brick_protocol/support/checkers/check_profile.py --all
- git diff --check
- follow-up human approval before deleting any old vessel path
```

## 6. Three-axis attribution

```text
Brick evidence:
  `project/brick-protocol` is project-local evidence/status vessel for the Brick
  Protocol dogfood work. It carries task/GOAL/status/building evidence. It is not
  Brick-axis source code, but it is active Brick work evidence.

Agent evidence:
  Vessel separation does not change Agent Objects, Agent skills, performer
  casting, adapter/model/provider refs, or closed AgentFact shape. Any future
  Building performer is chosen by declared Agent rows, not by this packet.

Link evidence:
  This packet chooses no Link Movement. Any future migration Building would carry
  declared Link rows and gates, but this human gate is lifecycle/review state,
  not forward/reroute Movement.

Support surface:
  project_creation, progress_projection, capture, check_project_declaration, and
  checker profiles are support surfaces that record/project/validate the vessel.
  They do not own source truth, success, quality, or Movement.

Rejected shortcut:
  Do not treat path confusion as proof that a filesystem move is safe. Current
  evidence volume (58 buildings, 94 kernel docs, 929 inbox events) makes this an
  evidence migration problem.
```

## 7. Human decision options

```text
Option A — KEEP + clarify wording only (COO recommended)
  Keep `project/brick-protocol` as active dogfood vessel. No migration Building
  now. Continue with ⑩f implementation or ⑥e/⑦ route-walker work.

Option B — DESIGN split map only
  Open docs-only Building/design note for future vessel split. No move/delete.

Option C — OPEN migration Building now
  High-risk migration. Requires explicit target path and full proof plan.

Option D — DELETE/ARCHIVE current vessel
  Rejected / not admissible while active evidence lives here.
```

## 8. Current disposition

```text
phase: ⑩g dogfood vessel separation
state: held_for_human_gate
recommended: Option A
moved_files: none
deleted_files: none
changed_files: this packet + GOAL status only
next allowed actions:
  - Smith approves Option A: record approval and keep vessel; ⑩g closes as KEEP.
  - Smith chooses Option B: open design-only split map.
  - Smith explicitly chooses Option C: open high-risk migration Building.
```

## 9. Not proven

```text
- No vessel split is implemented.
- No migration target path is selected.
- No reference rewrite is proven.
- No deletion/archive is approved.
- Whether ⑩g can close as KEEP depends on Smith/human decision.
- Parent GOAL remains open: ⑩f implementation and ⑥e/⑦ remain pending.
```

## 10. Movement language

This packet authors no Link Movement. Its current state is a human gate:

```text
gate_state: held_for_human_gate
movement_candidate: none supplied by this packet
```
