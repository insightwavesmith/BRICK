# BRICK 6-Surface Audit - Readiness Tuples - 2026-06-30

## Scope

- Target checkout: `/Users/smith/projects/BRICK`.
- Commit: `17eaade696998cd0de7bbd85ceb7525f349588e9`.
- Mode: audit aggregation only.
- Source/code repair: none.

This file replaces the practical use of a flat `6/6 ISSUE` label. The flat
label remains a findings-inventory summary, but implementation priority must
use per-surface tuples.

## Tuple Fields

Each surface is scored with these fields:

- `core_sound`: whether the core surface concept still appears structurally
  sound at this static audit depth.
- `axis_integrity_blockers`: blockers that can blur Brick / Agent / Link
  ownership or let support evidence become authority.
- `ship_safety_blockers`: blockers that can make a customer/public release
  unsafe, misleading, or unreproducible.
- `dynamic_runtime_not_proven`: whether static audit/checkers are insufficient
  to certify the relevant live behavior.
- `worst_severity`: highest repair urgency in that surface.
- `product_confusion_risk`: risk that a customer/operator will misunderstand
  the public route, state, next action, proof limit, or authority boundary.
- `ai_blame_prevention_impact`: how strongly the surface affects BRICK's
  product promise: do not end with "AI failed"; show the condition and evidence.
- `shared_protocol_impact`: how strongly the surface affects "everyone works
  under the same Brick / Agent / Link protocol."

This tuple is still support/audit evidence. It is not source truth, not success
judgment, not quality judgment, and not Link Movement.

## Summary Table

| Surface | Core sound | Axis blockers | Ship blockers | Dynamic not proven | Worst severity | Product confusion | AI-blame impact | Shared-protocol impact |
|---|---:|---:|---:|---:|---|---|---|---|
| S1 Brick | partial | 4 | 1 | yes | high | medium | high | high |
| S2 Agent | partial | 4 | 2 | yes | high | medium | high | high |
| S3 Link | partial | 4 | 1 | yes | high | medium | high | high |
| S4 Support | partial | 3 | 8 | yes | high | high | high | medium-high |
| S5 Checker | partial/strong-with-gaps | 2 | 5 | yes | high | high | medium-high | high |
| S6 Product | partial | 3 | 9 | yes | high | high | high | high |

Interpretation:

- BRICK core is not collapsed.
- Customer-ready is not proven.
- The strongest immediate blockers are not "AI is bad." They are attribution,
  evidence integrity, resume isolation, product route clarity, release/export
  cleanliness, dashboard integrity, and checker-governance truth.

## S1 - Brick Axis Tuple

```yaml
surface: S1 Brick
core_sound: partial
axis_integrity_blockers:
  count: 4
  examples:
    - Brick return-shape truth can be shrunk outside template return.yaml.
    - Link carry/filtering pressure can mutate Brick return contract.
    - Brick templates/presets carry Agent and Link selection metadata.
    - Brick-side skills contain role/provider/verdict wording.
ship_safety_blockers:
  count: 1
  examples:
    - P3 graph-packet confusion can make customer/operator declarations carry internal template authority fields.
dynamic_runtime_not_proven: yes
worst_severity: high
product_confusion_risk: medium
ai_blame_prevention_impact: high
shared_protocol_impact: high
```

Judgment:

S1 shows a real Brick contract truth problem, not a need for a new engine. If a
fan-in source Brick has its return shape reduced to serve handoff/carry needs,
the product can no longer cleanly say whether the blocker came from the work
contract, the Agent return, or Link carry. That directly damages BRICK's
accountability promise.

First repair candidates:

1. Restore template-full return shapes from `brick/templates/bricks/<kind>/return.yaml`.
2. Move fan-in carry filtering to Link carry/closure policy.
3. Add negative probes for `observed_evidence, not_proven` shrink on work/QA/axis QA rows.
4. Add parser/materializer equivalence probes for `brick/work.py` and composition strip logic.

## S2 - Agent Axis Tuple

```yaml
surface: S2 Agent
core_sound: partial
axis_integrity_blockers:
  count: 4
  examples:
    - Chat-session intake can persist returned payloads AgentFact later rejects.
    - AgentFact closure is not enforced at the first disk-admission boundary.
    - Agent skill/taxonomy wording still lags read/probe_write/source_write.
    - Prompt/skill projection can leak Brick/Link authority language.
ship_safety_blockers:
  count: 2
  examples:
    - Poisoned submission can wedge a Building.
    - Provider/write capability strength is not yet customer-visible enough.
dynamic_runtime_not_proven: yes
worst_severity: high
product_confusion_risk: medium
ai_blame_prevention_impact: high
shared_protocol_impact: high
```

Judgment:

S2's core contract remains right: Agent owns performer identity and the closed
`received_work` / `returned` fact. The blocker is admission timing. If an Agent
return can be parked to disk before the AgentFact top-level verdict-key rule is
enforced, the later failure looks like a runtime/replay problem instead of a
clear Agent-return contract violation. That is exactly the kind of "AI failed"
blur BRICK is supposed to prevent.

First repair candidates:

1. Add top-level-only pre-persistence validation for AgentFact-forbidden keys.
2. Make poisoned chat-session submission fail before write-exclusive disk admission.
3. Update Agent skill/taxonomy wording to `read / probe_write / source_write-artifact_write`.
4. Keep nested ordinary words such as `status` or `result` legal where they are data, not Agent authority.

## S3 - Link Axis Tuple

```yaml
surface: S3 Link
core_sound: partial
axis_integrity_blockers:
  count: 4
  examples:
    - Missing declared_gate_refs can be normalized into default behavior without a visible materialization boundary.
    - Invalid transition concern evidence can shape a HOLD pending target.
    - Fan-in/adoption/carry checks are not fully unified across raw graph and composition paths.
    - Link carry runtime surface was not fully inspected.
ship_safety_blockers:
  count: 1
  examples:
    - Product/operator may mistake HOLD pending target for an adopted reroute.
dynamic_runtime_not_proven: yes
worst_severity: high
product_confusion_risk: medium
ai_blame_prevention_impact: high
shared_protocol_impact: high
```

Judgment:

S3 is not "Link is broken." The key distinction is preserved: `forward` and
`reroute` are Movement; HOLD/pause is lifecycle. The remaining issue is
materialization clarity. If raw absence becomes default gate adoption later, or
invalid Agent concern evidence shapes the target a human sees, the product can
still show a route-like fact without enough Link-owned basis.

First repair candidates:

1. Either reject missing `declared_gate_refs` on active rows or explicitly materialize `default-transition` before runtime.
2. Prevent invalid concern evidence from setting pending targets unless a declared disposition row supplies one.
3. Audit `walker_carry.py` before carry repair.
4. Add portfolio adoption negative probes comparable to single-Building gate probes.

## S4 - Support Machine Tuple

```yaml
surface: S4 Support
core_sound: partial
axis_integrity_blockers:
  count: 3
  examples:
    - `onboard approve` carries default disposition action/identity.
    - Absent report policy can default to external sink refs with delivery flags.
    - Multiple official-route wrapper surfaces create authority confusion.
ship_safety_blockers:
  count: 8
  examples:
    - Raw evidence streams lack uniform secret/PII scrub.
    - Resume/post-HOLD approval is not proven to preserve customer worktree isolation.
    - Release export can include untracked unignored local files.
    - Dashboard ingest lacks HMAC/timestamp/event_id/sequence integrity.
    - Provider keys enter parent os.environ for Gemini.
    - Sensitive path writes do not block or mark sandbox output commit.
    - Dashboard container/viewer access depends on deployment hardening.
    - Native child-dispatch recording is not active/proven in this checkout.
dynamic_runtime_not_proven: yes
worst_severity: high
product_confusion_risk: high
ai_blame_prevention_impact: high
shared_protocol_impact: medium-high
```

Judgment:

S4 is the highest pressure surface because support records and replays the
evidence customers will read. Support is not a fourth axis, but weak evidence
integrity can still damage the accountability protocol. Raw stream scrub,
resume isolation, release export, dashboard ingest, and sensitive-write commit
handling should be treated as evidence/publication integrity, not as new
Movement or source-truth authority.

First repair candidates:

1. Raw-stream scrub/redaction or explicit guard before JSONL persistence.
2. Post-HOLD resume isolation equivalent to fresh customer run isolation.
3. Release export clean-room: tracked-only default, dirty-tree guard, denylist, explicit opt-in for untracked.
4. Dashboard ingest signing/replay/sequence hardening.
5. Sensitive-write commit block/mark.

## S5 - Checker System Tuple

```yaml
surface: S5 Checker
core_sound: partial/strong-with-gaps
axis_integrity_blockers:
  count: 2
  examples:
    - Checker green can preserve bad invariants such as fan-in return-shape shrink.
    - Checker/profiles can accidentally pin source-truth/pass/done wording.
ship_safety_blockers:
  count: 5
  examples:
    - Declared pytest surface is misleading.
    - Checker sweep is not proven as CI/release governance.
    - Deployment hardening lacks behavioral negative probes.
    - Fixture/probe writes can touch live repo project paths.
    - Fixed fixture vessel is non-reentrant if cleanup is interrupted.
dynamic_runtime_not_proven: yes
worst_severity: high
product_confusion_risk: high
ai_blame_prevention_impact: medium-high
shared_protocol_impact: high
```

Judgment:

The checker system has teeth, but the issue is what it proves. A green sweep can
be valuable support evidence while still preserving the wrong invariant. For
ordinary customer product runs, detailed checker machinery should be translated
into product status: state, reason, next action, evidence refs, and proof
limits.

First repair candidates:

1. Add negative probes for P0 seams before checker diet.
2. Correct or remove the dead/misleading pytest declaration.
3. Add release/export/dashboard/sensitive-write behavioral probes.
4. Make fixture/probe writes isolated and reentrant.
5. Separate internal BRICK development checker detail from customer-facing product status.

## S6 - Product Surface Tuple

```yaml
surface: S6 Product
core_sound: partial
axis_integrity_blockers:
  count: 3
  examples:
    - Public route docs blur CLI, official wrapper, advanced helper, and historical seam.
    - Graph packet docs can lead operators to internal Building Plan/template-authority fields.
    - Product surface does not yet fully display protocol compliance/readiness concepts.
ship_safety_blockers:
  count: 9
  examples:
    - Fresh-machine customer-ready proof is not current-main proven.
    - Release/export path can carry untracked unignored files.
    - Dashboard ingest/container/viewer hardening incomplete.
    - Provider write-boundary matrix missing from customer-visible docs.
    - CI/branch-protection release gate not proven.
    - Dependency/release reproducibility policy unclear.
    - Install/init/onboard docs drift.
    - CLI raw error message taxonomy not hardened.
    - Slack/reporting reliability not proven.
dynamic_runtime_not_proven: yes
worst_severity: high
product_confusion_risk: high
ai_blame_prevention_impact: high
shared_protocol_impact: high
```

Judgment:

S6 is where BRICK's product philosophy must become visible. The product should
not ask users to infer from checker logs or Agent prose. It should show:

- current state
- reason
- next action
- decision owner
- evidence refs
- proof limits
- not-proven facts
- provider boundary strength
- human approval versus product readiness separation

First repair candidates:

1. P3 Easy Building declaration surface over official `brick build`, no `--large`.
2. CLI/dashboard readiness and protocol-compliance observation.
3. Docs cleanup for install/init/onboard/FIRST_USE.
4. Provider boundary matrix.
5. Customer-facing checker-result mapping.

## Protocol-Live Priority Order

Use this order when the next work is BRICK dogfood, internal customer-run
correctness, or protocol integrity:

1. Raw evidence stream secret/PII scrub.
2. Resume/post-HOLD isolation.
3. Brick return-shape truth versus Link carry filtering.
4. AgentFact forbidden top-level keys at pre-persistence intake.
5. `declared_gate_refs` absence/default materialization law.
6. Invalid transition concern cannot set pending target without disposition.
7. Declared pytest/test surface honesty.
8. Sensitive path write commit block/mark.

## Ship-Imminent Priority Order

Use this order only if public release/customer install is imminent:

1. Release export clean-room.
2. Dashboard ingest HMAC/timestamp/event_id/sequence hardening.
3. CI/release gate for compileall, checker sweep, `brick verify`, dashboard build, and release-export probes.
4. Provider boundary matrix.
5. Dashboard container/viewer hardening.
6. Then run the protocol-live order before broad customer-ready language.

## Product Philosophy Verdict

BRICK is best framed as:

```text
AI work accountability protocol
+
shared operating protocol for humans and agents
```

This audit therefore should not close by saying "AI succeeded" or "AI failed."
It should close by showing:

- what work contract was declared,
- which Agent performed it,
- what was returned,
- what Link movement or lifecycle evidence exists,
- what proof limits remain,
- what human/COO disposition is required,
- what next declared repair or route is available.

## Final Readiness Judgment

```yaml
architecture_core: viable_but_mixed
customer_ready: not_proven
public_ship_ready: not_proven
official_route: exists_but_product_surface_needs_clarity
checker_system: meaningful_but_not_complete_release_governance
dynamic_runtime: not_certified_by_this_static_audit
next_best_step: select_protocol_live_or_ship_imminent_order_then_start_first_repair_slice
```
