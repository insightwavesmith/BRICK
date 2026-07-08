# Link axis detail

Link is the third axis of Brick Protocol:

```text
Brick = work
Agent = performer
Link = transfer / carry / movement
```

This page is a deep dive on Link: how public facts move from one Brick boundary to the next, how the gate measures sufficiency, what carries forward, and the transition/disposition vocabulary that bounds a paused step. For the wider model, see `three-axis-overview.md`; for a runnable example, see `quickstart.md`.

Every claim below is grounded in the Link contract projections (`brick_protocol/link/movement.yaml`, `brick_protocol/link/gate.yaml`, `brick_protocol/link/transfer.yaml`, `brick_protocol/link/carry.yaml`, `brick_protocol/link/transition.yaml`) and the constitution (`AGENTS.md`).

## What Link owns

Link owns transfer, carry, gate sufficiency, movement, transition, route policy, fan-out/fan-in transition meaning, and portfolio adoption policy (`AGENTS.md`, Link Axis). The active Link surfaces are:

```text
brick_protocol/link/movement.py
brick_protocol/link/transfer.py
brick_protocol/link/carry.py
brick_protocol/link/gate.py
brick_protocol/link/transition.py
brick_protocol/link/route_policies/*.yaml
```

Each `brick_protocol/link/*.yaml` is a `projection_only` contract that declares the public fact a Link module owns, its allowed fields, and its forbidden ownership.

## The gate measures sufficiency, not quality

`GateFact` (`brick_protocol/link/gate.yaml`) records Link-side **sufficiency** for public facts. Its fields are:

```text
stage
sufficiency
checked_public_fact
required_public_facts
missing_required_facts
reason
evidence_reference
```

The gate runs at one of three declared stages (`stage_literals`):

```text
transfer
carry
movement
```

And it reports exactly one of three sufficiency values (`sufficiency_literals`):

```text
sufficient
insufficient
missing_required_facts
```

That is the gate's entire job. Its declared `proof_limits` are explicit:

```text
GateFact reports sufficiency only
GateFact does not choose Movement
GateFact is not source truth
GateFact is not success judgment
GateFact is not quality judgment
```

The gate's `forbidden_ownership` (`brick_protocol/link/gate.yaml`) is even broader: it must not own Movement authority, destination choice, route choice, rollback choice, retry choice, hold choice, next-target choice, or any quality / success / failure / outcome judgment. So the gate answers one question — "are the required public facts present and sufficient?" — and nothing else. A separate, declared Link row or policy reads that sufficiency and decides what happens next. The gate does **not** decide whether the work was good; quality judgment is a separate human layer (see `three-axis-overview.md`, "Truth vs quality").

### Declared gate refs

A Building step references a gate by name. The currently declared gate refs (`brick_protocol/link/gate.yaml`, `declared_gate_refs`; also `AGENTS.md`) are:

```text
link-gate:default-transition   work-contract return shape + honest report channel sufficiency (default for compact preset)
link-gate:strict               stricter mechanical evidence fields before transition
link-gate:human                human disposition evidence required before transition resumes
link-gate:coo                  COO disposition evidence required before transition resumes
```

`link-gate:default-transition` is structural honest-return sufficiency. Per the `post_d_base_gate_matrix`, it (and the strict variant) `must_not` judge quality, judge success, or choose a target / select among multiple candidate Buildings. `link-gate:human` `base_default` is `false` — it is exceptional only and must not become the default preset gate or a support authority.

Two related concepts in the matrix deliberately have **no** GateFact literal (`gatefact_literal: none`): `fan-in-wait-all` lives in declared graph fan-in observation / frontier, and `portfolio-policy` lives in `brick_protocol/support/operator/driver.py` declared portfolio policy. They are not new gate authority.

## Movement literals are exactly forward | reroute

After sufficiency is known, a declared Link row records Movement. The Movement literals are **exactly two** (`brick_protocol/link/movement.yaml`, `movement_literals`; confirmed in `AGENTS.md`, Link Axis):

```text
forward
reroute
```

Their meaning (`brick_protocol/link/movement.yaml` `connection_route_rule`; `AGENTS.md`):

```text
forward = continue on the current declared road (default connection between declared Brick boundaries)
reroute = move to another declared Brick boundary (the exception route)
```

`MovementFact` (`brick_protocol/link/movement.yaml`) carries:

```text
movement
reason
handoff_target_fact
gatefact_reference
transition_history_reference
```

Important boundaries from the same file:

- A backward, sideways, or repair move is represented **as `reroute`** — there is no separate "back" or "repair" literal (`allowed`: "represent any backward, sideways, or repair move as reroute").
- A `route_replay_plan` is carried **inside** a reroute when supplied by the Link row.
- Transition **pause / resume** is NOT a Movement literal — it is represented through `transition_lifecycle` evidence (covered below).
- Building **wait / close** is NOT a Movement literal — it is Building lifecycle evidence.
- Movement `forbidden_ownership` includes automatic route selection, support-chosen route target, and any Korean or noncanonical movement value. Route selection is caller-declared (or later-admitted policy/template) only; support does not choose it.

`return`, `hold`, `stop`, `pass`, `complete`, and `paused` are **superseded or non-Movement words** (`AGENTS.md`, Link Axis): `return` is historical shorthand for `reroute`; `hold` is a Building-lifecycle / review-wait / frontier state; `stop` is a lifecycle close state or disposition action; `pass` is judgment wording; `complete` / `paused` are lifecycle or frontier states.

## What transfers, and what carries

Transfer and carry are the two public facts that describe what moves between Brick boundaries. Both are `closed_shape` with `extra_keys_allowed: false`.

### TransferFact

`TransferFact` (`brick_protocol/link/transfer.yaml`) describes a transfer between a source and target boundary:

```text
source_boundary_ref       (required brick boundary ref)
target_boundary_ref       (required brick boundary ref)
public_fact_refs          (required text tuple)
work_context_ref          (required text ref)
required_public_facts     (required text tuple)
transfer_gate_reference   (optional text ref)
proof_limits              (required text tuple)
not_proven                (text tuple)
evidence_reference        (required text ref)
```

It records caller-supplied public-fact references, the source and target Building boundaries, the work context, the required public facts, an optional transfer-gate reference, proof limits, not-proven facts, and an evidence reference. Its `proof_limits` state it is a Link public fact only: it does not execute transfer mechanics, does not create default GateFacts, does not choose Movement, and is not source/success/quality truth. Its `forbidden_ownership` explicitly excludes `movement_gate_reference` — a TransferFact cannot smuggle in a movement gate.

### CarryFact

`CarryFact` (`brick_protocol/link/carry.yaml`) describes which facts carry forward to the next step, **preserving the axis that originally owned them**:

```text
carried_fact_refs        (required text tuple)
source_owner_axis        (required owner-axis literal)
target_boundary_ref      (required brick boundary ref)
carry_gate_reference     (optional text ref)
proof_limits             (required text tuple)
not_proven               (text tuple)
evidence_reference       (required text ref)
```

`source_owner_axis` is one of (`source_owner_axis_literals`):

```text
Brick
Agent
Link
```

The key property: CarryFact **preserves the source owner axis without rewriting it** (`proof_limits`). Carrying a fact forward does not relabel who owns it. Its `forbidden_ownership` lists "owner-axis rewrite" and "Support owner axis" first — carry cannot turn a Brick/Agent/Link fact into a support-owned fact, and (like TransferFact) it cannot choose Movement, destination, or quality.

In short: **transfer** names the facts moving from a source boundary to a target boundary; **carry** names which already-owned facts continue forward, keeping their original axis label intact.

## Transition and disposition vocabulary

`TransitionFact` (`brick_protocol/link/transition.yaml`) is the connection-level fact between Brick boundaries:

```text
movement
target_fact
topology_fact
merge_rule_fact
handoff_reference
not_proven
```

Its `connection_route_rule` restates the binary model in transition terms:

```text
default_forward_connection = movement forward to the declared target_fact
exception_reroute          = movement reroute to another declared target_fact
```

It is explicit that `route_replay_plan`, `route_decision_basis`, and `transition_lifecycle` (paused/resumed) are **Link row evidence, not TransitionFact fields**, and that `transition_lifecycle` paused/resumed is **not a Movement literal**. It also notes the `transition_concern_boundary`: Agent-returned concern evidence may inform a later Link disposition but does not choose Movement. TransitionFact's `forbidden_ownership` includes executing the handoff, owning performer launch timing, judging quality, choosing the route target, and choosing the replay segment.

### Hold and resume: the disposition shape

When a step pauses, Link records `transition_lifecycle` evidence. The active shape (`AGENTS.md`, Binding Safety Schemas) is:

```text
transition_lifecycle:
  state: paused | resumed
  progress_state: in_progress
  required_disposition_owner: caller | coo | caller-or-coo
  pending_target_ref: <declared Brick boundary ref>
  disposition_action: raise | forward | stop | reroute
  budget_increment: <finite positive integer, required only for raise>
```

`disposition_action` is one of these values:

```text
raise     extend only the declared bounded budget for the paused boundary
          (requires a finite positive budget_increment)
forward   resume forward (must not carry budget_increment)
stop      close (must not carry budget_increment)
reroute   resume onto a declared route target (must not carry budget_increment)
```

Ownership and authoring rules (`AGENTS.md`):

- `paused` and `resumed` are **lifecycle states, not Movement literals** — Link Movement remains `forward` / `reroute`.
- A `disposition_action` may appear **only on a `human:`- or `coo:`-authored disposition row**. `human:` / `coo:` / `caller:` are author **prefixes**, not owner values; current validation admits the `human:` and `coo:` author prefixes only.
- Support may **observe and record** the disposition, but it must not author the disposition or choose the target.

Note a wording distinction: the disposition row carries `disposition_action: raise | forward | stop | reroute`, while the gate concepts `link-gate:human` / `link-gate:coo` describe **who** must supply disposition evidence before a paused transition resumes. The `required_disposition_owner` enum (`caller | coo | caller-or-coo`) is separate again from the `human:`/`coo:` author prefixes admitted for the row itself. These three vocabularies travel together but are not the same field.

## One step, drawn

```text
Declared Building step
=================================================================

  Brick row
  work_statement + required_return_shape          (the work being asked)
        |
        v
  Agent row
  agent_object_ref receives the Brick work        (the performer)
        |
        v
  AgentFact
  received_work + returned                        (what came back)
        |
        v
  Link row
  ---------------------------------------------------------------
   GateFact: sufficient?  ----> sufficiency in { sufficient,
   (stage: transfer/             insufficient, missing_required_facts }
    carry/movement)              (measures sufficiency ONLY — no quality)
        |
        |  declared Link row / policy reads sufficiency and records:
        v
   +-------------------+-------------------+--------------------------+
   |                   |                   |                          |
 forward             reroute         transition_lifecycle:
 (continue the       (go to another   state = paused
  declared road)      declared Brick   required_disposition_owner +
                      boundary)        disposition_action raise|forward|stop
                                       (human:/coo:-authored; later
                                        resumes to forward or stop)
   |                   |                          |
   v                   v                          v
 Next declared      Another declared      Hold for caller/COO/human
 Brick boundary     Brick boundary        disposition; not a Movement
 (or closed                               literal
  Building boundary)

  TransferFact / CarryFact ride along the Link row:
    TransferFact = which public facts move source -> target boundary
    CarryFact    = which already-owned facts continue forward,
                   keeping their source_owner_axis (Brick|Agent|Link)
```

Note that `forward` and `reroute` are the only two Movement literals. The "paused" branch is `transition_lifecycle` evidence, **not** a third Movement value — it eventually resolves back to a `disposition_action` (`forward` or `stop`) once a `human:`/`coo:` disposition row is authored.

## What Link must not do

Across every Link contract file the same forbidden ownership recurs. Link facts must not:

```text
choose quality / success / failure / outcome verdicts
become source truth
own runtime execution, storage mutation, or wiki mutation
let support choose the route target or Movement
use a noncanonical (e.g. Korean) Movement value
rewrite the owner axis of a carried fact
create default GateFacts implicitly
```

The gate measures sufficiency; the declared Link row (or admitted policy/template) records Movement; transfer and carry name what moves; transition lifecycle bounds a pause. None of it judges quality.

## Limitations and not-proven

These are stated for accuracy and are grounded in the source files:

- The `brick_protocol/link/*.yaml` files are **contract projections** (`projection_only: true`), not the executable Link modules. The executable surfaces are `brick_protocol/link/*.py`; this page describes the declared contracts, not a verified runtime.
- `transfer.yaml` and `carry.yaml` note that residual contract guards are "tracked in checker-consolidation-and-builder-plan-0602.md (not all built yet)" — i.e. not every declared rule has a checker behind it yet.
- `AGENTS.md`, "Current Not Proven", lists `semantic correctness of Agent transition_concern_evidence` and `caller/COO disposition after portfolio HOLD` among the items that remain not proven. Disposition and concern-handling behavior beyond the declared shape is not proven here.
- This page does not document command-line usage for Link directly; for a runnable Building (which exercises the Link row) see `quickstart.md`.
