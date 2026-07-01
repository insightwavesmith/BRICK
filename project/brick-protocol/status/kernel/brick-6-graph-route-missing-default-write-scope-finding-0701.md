# Official graph route silently drops to zero-write when write_scope is omitted — finding (0701)

Status: operator-discovered finding, support/evidence-integrity only. Not
source truth, success judgment, quality judgment, or Movement authority.
Routed as a P8 (ship-safety / evidence-integrity) candidate item.

## Adversarial re-verification (0701, same day, Smith-requested)

Smith asked "이거 그럴리가 없는데" (this shouldn't be possible) and requested a
workflow-based sequential re-check rather than accepting the single
Explore-agent conclusion below at face value. A 4-agent workflow ran: (1) an
independent from-scratch call-chain re-trace, (2) an exhaustive repo-wide
search for every call site of `assemble()` / `derived_worktree_write_scope`
/ `_validated_write_scope` to rule out a missed reachability path, (3) a
**live empirical reproduction** -- actually running `brick build --graph`
against a minimal real graph_packet with one `building-step-template:work`
node carrying no `write_scope`, and (4) an adversarial judge instructed to
try to refute the claim using all three bodies of evidence.

**Result: CONFIRMED at high confidence by all four agents, with a live
empirical reproduction, not just static code reading.**

Live reproduction evidence (graph_packet committed at `3b2ceaf`, evidence
root `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-write-scope-repro-0701z`):
- `brick build --graph` exited 0, `frontier_kind=complete`, `adapter_error_records=0`,
  zero HOLD/pause disposition events (independently confirmed from the raw
  `evidence/spine/events/0024-Frontier.json` file on disk, not only the
  Agent's self-report).
- The work node's own step-output: `made_changes=false`, `changed_files=[]`,
  and verbatim `no_changes_reason`: "Write was DENIED by
  capability/tool-policy/adapter grant before any filesystem write attempt
  because this node has no declared write_scope and
  native_grant.write_effective is false. Exact denial instruction returned
  to this Agent: \"Do not edit, create, delete, or write files.\""
- Filesystem directly checked (not just the Agent's claim): the test file
  the work node was instructed to write does not exist anywhere in the repo
  or under `~/.brick`.
- Root mechanism, one layer more precise than originally found:
  `support/connection/adapter_grant_policy.py` derives
  `write_effective = bool(request.write_scope)` -- a simple truthiness
  check. And `brick/spec.py:398-406`
  (`validate_brick_row_write_need_for_scope`): `if raw_write_scope is None:
  return` -- the strict admission gate (`require_write_need_marker=True`,
  active on the `--graph` path per `walker_kernel.py:849-858`)
  short-circuits with no error when write_scope is absent entirely; its
  `ValueError` only fires for a *different* case (write_scope present but
  the write-need marker missing), which does not apply here.
- The denial IS communicated clearly to the Agent itself (explicit
  `write_effective: false` and a "do not write" instruction) -- so the
  Agent is not confused. The gap is entirely at the Building/operator
  level: nothing in `frontier_kind`, `customer_visible_frontier_message`,
  or the closure surfaces this silently-denied capability as worth
  stopping for. A Building can report `complete` while a node it declared
  as write-needed never got to write anything, and no operator-facing
  signal distinguishes that from "the node genuinely needed no writes."

This section supersedes any residual uncertainty in the original finding
below; treat the finding as confirmed, not merely proposed.

## How this was found

While declaring `brick-6-graph-topology-fan-barrier-checker-0701a`, Claude
(acting COO) omitted an explicit `write_scope` block on the `code-attack-qa`
node. At runtime, that QA lane reported "read-only effective capability"
and could not run `check_profile.py --all` / `py_compile` to completion
(both need disposable writes: temp fixture vessels, bytecode cache) --
even though its own Brick template (`code-attack-qa`) declares
`requires_brick_write_scope: yes` / `capability_class: probe_write`, and
its Agent Object (`agent-object:qa`) declares `tool-policy:probe-write-scoped`.
Smith asked whether the graph author should really need to hand-supply
write_scope on every node when the Brick/Agent templates already declare
the capability, and separately asked whether the code path exhibiting this
gap (`plan_rendering.py` / `composition_graph_emit.py`, reached via
`brick build --graph`) is even the official route. Two focused
investigations (Explore agent, read-only) confirmed both questions.

## Root cause (source-confirmed)

There are two separate plan-materialization code paths in BRICK, and only
one of them applies a sensible default `write_scope`:

- `support/operator/assembly.py::assemble()` (~line 1122) calls
  `_validated_write_scope()` (~line 1326), which falls back to
  `brick/spec.py::derived_worktree_write_scope()` (~line 150) --
  `{"allowed_paths": ["."], "forbidden_paths": [".git/**"]}` -- whenever a
  write-needed Brick's node omits an explicit `write_scope`.
- `support/operator/plan_rendering.py`'s declared-step renderer (~line 1485)
  and `support/operator/composition_compose.py::compose_building()`
  (~line 982) only CARRY a `write_scope` if the graph node explicitly
  supplies one; there is no fallback, no default generation.
- `support/operator/composition_graph_emit.py` (~line 1205, used by the
  PRESET materializer only) at least fails LOUDLY
  (`raise ValueError("write_scope is required for write-needed Brick...")`)
  when a preset-declared write-needed Brick has no write_scope.
- The GRAPH_PACKET path (`brick build --graph`) does NEITHER: it neither
  applies a default NOR raises an error. `walker_kernel.py`'s runtime
  admission gate (`_run_dynamic_graph_walker`, `require_write_need_marker=True`
  via `plan_validation.py`) only checks internal consistency (if a
  write_scope IS present, `requires_brick_write_scope` must also be true);
  it does not require write_scope to be present at all. A write-needed
  Brick with no declared write_scope simply proceeds through the whole
  Building with zero effective write capability, with no error and no
  default -- the gap is silent.

## Which path is "official" (source-confirmed, not assumed)

Full call chain traced for `brick build --graph <packet>`:

```
pyproject.toml:23 (console script) -> support/operator/cli.py:383
(_run_build, --graph mode) -> support/operator/driver.py:714
(run_customer_graph_building_in_sandbox) -> driver.py:508
(run_composed_graph_intake) -> driver.py:572 (compose_building)
-> driver.py:616 (_write_and_run_declared_graph_plan) -> driver.py:346
(run_building_plan) -> support/operator/run.py:589
(_run_dynamic_graph_walker) -> support/operator/walker_kernel.py
```

`assembly.py::assemble()` -- the ONLY place with the good default -- is
called exclusively from `support/operator/onboard.py:1640` (the onboard
wizard flow). It has zero call sites in driver.py, run.py, walker_kernel.py,
or plan_graph.py. `AGENTS.md:585` itself labels assembly.py an "operator
surface," not the customer CLI route.

**Verdict: `brick build --graph` (the actual official customer/operator
route used throughout this session) is exactly the path with NO default
write_scope. The good default logic lives in a separate, non-canonical,
bypassable entry point (`assemble()`/onboard wizard) that the official
route never reaches.** This is not a defect in a side path someone can
choose to avoid -- it is a defect in the primary route.

## Why this matters beyond the one QA lane

This is a second, distinct instance of the same failure SHAPE already
documented this session (`brick-6-fan-in-cohort-reverify-one-hop-blindspot-finding-0701.md`,
and the S5-F7 audit finding about support wording blurring sufficiency
with pass/done language): **a Building can report `frontier_kind=complete`
while a real capability was silently degraded underneath, with nothing in
the evidence trail flagging it as a defect** -- the QA lane's own
`blocked_or_missing_evidence` field DID honestly report the gap ("read-only
effective capability... py_compile writes bytecode"), which is why this
was caught, but nothing in the closure/frontier language distinguishes
"this QA lane could not verify because it was denied capability it should
have had" from "this QA lane verified and found nothing wrong."

## What this does NOT prove

- Does not prove every write-needed Brick across every prior Building this
  session was affected -- most WORK nodes in this session's graphs (P7's
  work-docs/work-checker, etc.) had explicit hand-authored write_scope
  blocks and were unaffected. QA/review-role nodes, which are less often
  given explicit write_scope because their write need is usually assumed
  to be none, are the likely blast radius.
- Does not prove `assemble()`'s default (whole-worktree-minus-.git) is the
  *correct* default for a probe_write QA role specifically -- it may be
  too broad; a narrower default (temp/fixture-vessel paths only) may be
  more appropriate for `capability_class: probe_write` specifically.

## Recommended P8 scope addition (own item, not folded into #6/#7)

Distinct from the walker_kernel.py/walker_fan_in.py reroute-cascade fixes
(tasks #6/#7) -- this lives one stage earlier, in plan materialization
(`composition_compose.py` / `plan_rendering.py`), not in dynamic walking.

1. Port (not necessarily copy verbatim) `derived_worktree_write_scope()`'s
   default-on-omission behavior into the graph_packet materialization path
   (`composition_compose.py::compose_building()` and/or
   `plan_rendering.py`'s declared-step renderer), gated the same way
   assembly.py gates it: only when the Brick template declares
   `requires_brick_write_scope: yes` / a non-`read` `capability_class`.
2. Decide and document the correct default scope per capability_class --
   `probe_write` roles likely want a narrower default (temp/fixture-vessel
   paths, not the whole worktree) than `source_write` roles.
3. Checker-first: add a negative probe reproducing this exact scenario (a
   write-needed Brick node with no declared write_scope, run through
   `brick build --graph`) -- must currently silently succeed with zero
   write (the bug), must RED-fire or receive the correct default after the
   fix.
4. Consider whether the graph_packet path should match the preset path's
   fail-loud behavior (`composition_graph_emit.py`'s `raise ValueError`)
   as a stopgap even before the full default-application fix lands --
   silent degradation is worse than a loud rejection.

## Proof limits

- No source mutation performed to investigate; two independent read-only
  Explore-agent investigations plus direct source citation checks.
- Not yet scoped as a Building; recorded here so it is not lost before P8.
