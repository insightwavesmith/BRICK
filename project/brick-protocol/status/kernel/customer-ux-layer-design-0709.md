# ⑩f Customer UX Layer Design — 0709

Status: support/design evidence only. This document does not implement code,
create files outside itself + the GOAL status update, run a Building, choose Link
Movement, judge success/quality, or make source truth. It is the ⑩f design-first
note required by the 0708 unified GOAL before any declared customer-UX Building.

## 0. Scope and lineage

```text
GOAL: project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
phase: ⑩f customer UX layer (design-first)
prior cleanup evidence:
  ⑩a project/brick-protocol/status/kernel/cleanup-scope-invariants-0709.md
  ⑩c project/brick-protocol/status/kernel/building-plans-location-decision-0709.md
prior UX evidence:
  project/brick-protocol/status/kernel/install-ux-design-0618.md
```

GOAL ⑩f requirement (verbatim intent):

```text
install -> create project -> buildings -> progress board -> project definition
flow; first-run copy/spec/checker plan. 이미 있는 project-creation/progress_projection
위에 UX 층을 얹는다. 새 runtime/queue/scheduler 금지.
```

This design obeys the ⑩a invariant: customer UX is added by a design-first
Building only, reusing existing project_creation and progress_projection, with no
scheduler/queue/retry/runtime platform and no source-truth layer.

## 1. Independent requirement re-derivation

The GOAL names a five-stage customer journey. Re-deriving each stage against live
code (not the stale 0618 doc) gives the true state:

```text
Stage 1 install        -> EXISTS. pyproject.toml [project.scripts] now declares
                           brick = brick_protocol.support.operator.cli:main
                           (the 0618 doc's "no [project.scripts]" claim is STALE).
Stage 2 create project -> BACKEND EXISTS, NOT REACHABLE FROM CLI.
                           brick_protocol/support/operator/project_creation.py
                           create_project (CHARTER -> SHADOW -> SKELETON) works,
                           but the brick CLI has no `project` subcommand.
Stage 3 buildings      -> EXISTS. brick build + the buildings/ vessel skeleton.
Stage 4 progress board -> BACKEND EXISTS, NOT REACHABLE FROM CLI.
                           brick_protocol/support/operator/progress_projection.py
                           generate_project_progress writes project/<vessel>/PROGRESS.md,
                           but the brick CLI has no command that invokes it.
Stage 5 project defn   -> BACKEND EXISTS (README.md charter + project.json shadow),
                           produced by create_project; only the CLI entry is missing.
```

Conclusion: ⑩f is NOT greenfield and is NOT an install-flow rewrite. The single
real customer-facing gap is that the vessel lifecycle (create project + progress
board) has no reachable `brick` CLI surface, so a customer who installs the CLI
cannot create a project or see a progress board without calling internal Python.

## 2. Live-code evidence for the gap

```text
pyproject.toml:22-23
  [project.scripts]
  brick = "brick_protocol.support.operator.cli:main"

brick CLI subcommands present (brick_protocol/support/operator/cli.py):
  init, build, draft, draft-diff, resume, verify, doctor, status,
  auth (login), provider (add), sink (add)

brick CLI subcommands ABSENT:
  project (create/list/show)     <- Stage 2 + Stage 5 not reachable
  progress / board               <- Stage 4 not reachable

create_project callers (excluding its own module):
  only skills/checkers/docs reference it; NO cli.py caller.
generate_project_progress callers (excluding its own module):
  only checkers reference it; NO cli.py caller.
```

So the customer journey breaks between "install" (works) and "create project"
(only internal API), and "progress board" is likewise internal-only.

## 3. Design: thin CLI tie over existing verbs

⑩f adds a thin CLI surface only. It must not re-implement vessel logic. Following
the existing cli.py orchestrator discipline (subcommand -> existing support verb,
no concern logic in the CLI), the ⑩f Building should add:

```text
brick project new [--id <slug>] [--label <name>]
  -> conversational charter fill (project-creation SKILL Step 1 slots) then
     project_creation.create_project(...) AFTER human charter confirmation.
  -> NEVER stamp before charter confirmation (project_declaration kernel check).
  -> non-TTY / CI: refuse to auto-stamp; print the required charter slots and exit
     non-zero with guidance (no silent vessel creation).

brick project list
  -> read-only enumeration of existing project vessels under project/*/project.json.

brick project show [<id>]
  -> read-only print of the vessel charter (README.md) + declaration (project.json)
     direction/done_means; secrets never printed (parity with brick status masking).

brick progress [<id>] [--write]
  -> render_project_progress(...) read-only by default;
     --write calls generate_project_progress(...) to refresh project/<vessel>/PROGRESS.md.
  -> board projection only: counts by board_state / frontier_kind from buildings/
     evidence. No scheduler, no queue, no live provider calls.
```

CLI orchestrator invariant (must be checker-enforced, like brick init):

```text
The new project / progress subcommands only sequence existing support verbs.
They contain no vessel-creation logic, no board computation, and no Movement,
success, or quality judgment of their own.
```

## 4. First-run copy / spec plan

The 0618 install-ux design already specifies the first-green funnel
(doctor -> build example -> verify -> FIRST_USE.md). ⑩f extends the AFTER-first-green
"이제 진짜로 만들래?" upsell with the vessel lifecycle, so a customer's second act
is creating their own project:

```text
first run (0618, unchanged): brick -> init funnel -> adapter:local green -> FIRST_USE.md
second act (⑩f):             brick project new -> charter Q&A -> confirm -> stamp
                             brick build --task ... (into the new vessel)
                             brick progress -> read PROGRESS.md board
```

First-run copy requirements for ⑩f:

```text
- After the first green, point the customer at `brick project new`, not at raw
  create_project python.
- `brick project new` copy must state the charter-first / stamp-second law in one
  line so the customer knows the human confirms the charter before stamping.
- `brick progress` copy must state it is a read-only fact projection from
  buildings/ evidence (same byte for same evidence; no live run).
```

## 5. Checker plan for the ⑩f Building

A future ⑩f implementation Building must add/extend checker coverage:

```text
- CLI orchestrator purity: a profile rule pinning that the project/progress
  subcommands call only the declared support verbs and hold no vessel/board logic
  (mirror the existing brick init "no concern logic" discipline).
- project new non-TTY safety: a rule/fixture proving non-TTY invocation does not
  silently stamp a vessel (must refuse + guide, never auto-create).
- progress read-only: a rule/fixture proving `brick progress` without --write does
  not mutate PROGRESS.md, and with --write reproduces generate_project_progress
  byte output for the same evidence.
- secret masking parity: project show / progress print no secrets (reuse the
  brick status mask_secret contract).
- existing kernel checks must stay green: project_declaration (core),
  intake_project_vessel, intake_evidence_projection, and the progress projection
  record shape.
```

## 6. Hard boundaries (⑩a invariants preserved)

```text
Do NOT create a new runtime, scheduler, queue, retry service, or storage platform.
Do NOT move/rename project_creation.py or progress_projection.py in ⑩f.
Do NOT change project.json / README.md charter schema as part of the CLI tie.
Do NOT let the CLI author success/quality/Movement or bypass charter confirmation.
Do NOT touch project/brick-protocol vessel separation here (that is ⑩g, human gate).
Do NOT run a Building on the live checkout; use a declared worktree sandbox.
Do NOT print secrets in project show / status / progress.
```

Candidate write scope for the FUTURE ⑩f implementation Building (after approval):

```text
- brick_protocol/support/operator/cli.py            (thin project/progress subcommands)
- narrowly required checker/profile/fixture files
- brick_protocol/support/docs/references/*.md        (first-run/second-act copy)
- project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
- a follow-up dogfood / status evidence note
```

Reuse project_creation.py and progress_projection.py as-is; do not modify them
for the CLI tie unless a proven signature gap appears.

## 7. Three-axis attribution

```text
Brick evidence:
  ⑩f is a work-contract to expose existing vessel-lifecycle verbs through the
  customer CLI. The work definition is "tie", not "re-implement". Project vessel,
  charter, and board projection remain the existing Brick/support surfaces.

Agent evidence:
  The project-creation SKILL (agent/skills/project-creation) already guides the
  charter Q&A performer behavior. No new AgentFact field, adapter, model, or
  provider identity becomes authority. The CLI is a caller, not a performer.

Link evidence:
  No new Movement, gate, or route is authored. The board projection reads
  buildings/ evidence; it does not choose forward/reroute or judge closure.

Support surface:
  cli.py, project_creation.py, progress_projection.py are support surfaces. The
  ⑩f tie keeps them support: no source truth, success/quality judgment, Movement
  authority, scheduler, or queue is introduced.

Rejected shortcut:
  Do not treat "install-ux-design-0618 exists" as proof ⑩f is done. That doc
  predates the current CLI and its "no [project.scripts]" claim is stale; the
  real remaining gap is the missing project/progress CLI tie proven in section 2.
```

## 8. Disposition

```text
⑩f design state: design note produced (this file). Implementation still pending.
core finding: the only real customer-facing gap is the missing `brick project`
  and `brick progress` CLI tie over existing create_project / progress_projection.
next gate: open a declared ⑩f Building (design-build path) to add the thin CLI
  subcommands + checker coverage in a worktree sandbox, then land serially.
```

## 9. Not proven

```text
- No ⑩f CLI code is implemented or proven.
- The exact conversational charter-fill UX inside `brick project new` is not yet
  designed to the prompt level (project-creation SKILL Step 1 is the source).
- Whether `brick progress` should auto-refresh on `brick build` completion is not
  decided; default here is explicit --write only.
- install-ux-design-0618 first-green funnel implementation status is not audited
  by this ⑩f note; ⑩f assumes it and only adds the second-act vessel lifecycle.
```

## 10. Movement language

This note authors no Link Movement. Operationally the cleanup/UX track may
continue on the current declared road:

```text
next_movement_candidate: forward
reason: ⑩f is evidence-only design; no reroute target is opened by this doc.
```
