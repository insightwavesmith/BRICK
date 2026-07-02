# BRICK 6-Surface Architecture Audit - S3 Link Axis - 2026-06-30

## Surface

- Surface: Link axis.
- Target checkout: `/Users/smith/projects/BRICK`.
- Commit: `17eaade696998cd0de7bbd85ceb7525f349588e9`.
- Mode: audit only. No source repair was performed.
- Verdict: `ISSUE`.

## Map

Link owns transfer, carry, gate sufficiency, movement, transition, route policy,
fan-out/fan-in transition meaning, and portfolio adoption policy.

Primary Link-owned surfaces inspected:

- `link/movement.py`
- `link/transfer.py`
- `link/carry.py`
- `link/gate.py`
- `link/transition.py`
- `link/spec.py`
- `link/route_policies/basic_qa_repair.yaml`

Main support/projection consumers inspected:

- `support/operator/plan_validation.py`
- `support/operator/plan_graph.py`
- `support/operator/gate_sequence.py`
- `support/operator/route_materialization.py`
- `support/operator/walker_kernel.py`
- `support/operator/walker_transition_concern.py`
- `support/operator/walker_hold.py`
- `support/operator/walker_fan_in.py`
- `support/operator/frontier_observation.py`
- `support/operator/driver.py`
- `support/recording/*`

Observed Link flow:

1. Building Plan rows carry exactly one Link row per boundary.
2. Link row declares `movement` and `target_ref` / target boundary.
3. Plan validation rejects non-active Movement words.
4. GateFact records sufficiency only.
5. Agent `transition_concern_evidence` is non-binding evidence.
6. Declared Link gate/policy may adopt a concern into reroute or pause/HOLD.
7. Support walks the declared road and records raw/projection/frontier evidence.

## Evidence

Parallel attack review used 9 lanes:

- `S3-map`
- `S3-godmodule`
- `S3-dup-dead`
- `S3-axis-leak`
- `S3-contract`
- `S3-runtime`
- `S3-checker`
- `S3-simplicity`
- `S3-adversarial`

Codex operator direct checks:

- `git status --branch --short`
- `find link -maxdepth 3 -type f`
- `wc -l link/spec.py link/gate.py support/operator/walker_kernel.py support/operator/driver.py support/operator/run.py support/operator/gate_sequence.py support/operator/route_materialization.py support/operator/plan_graph.py`
- Targeted reads of `AGENTS.md`, `link/*.py`, `support/operator/plan_validation.py`, `support/operator/gate_sequence.py`, `support/operator/walker_kernel.py`, `support/operator/walker_transition_concern.py`, `support/operator/walker_hold.py`, `support/operator/walker_fan_in.py`, `support/operator/route_materialization.py`, `support/operator/frontier_observation.py`, and `support/operator/driver.py`.
- Read-only Python probe proving missing `declared_gate_refs` is accepted and later maps to default template adoption:

```text
{'validation': 'accepted_missing_declared_gate_refs',
 'gate_disposition': 'adopt',
 'adopted_by': 'template:default-transition'}
```

Direct green support evidence:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile support/checkers/profiles/link_routing_behavioral.yaml`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile support/checkers/profiles/gate_registry_single_source.yaml`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile support/checkers/profiles/chained_carry_dependency.yaml`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile support/checkers/profiles/building_operator_driver0.yaml`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile support/checkers/profiles/driver_public_intake_seal.yaml`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile support/checkers/profiles/tier_a_three_axis_conformance.yaml`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile support/checkers/profiles/bounded_agent_proposed_routing_loop.yaml`

Additional subagent support evidence reported green for `assembly_equivalence`
and `core`, but this packet does not treat that as source truth.

Proof limit: checker green proves only checked structural/runtime-local
invariants. It does not prove semantic correctness of future Agent concerns,
provider behavior, customer readiness, or absence of future authority leaks.

## Findings

### S3-F1 - Missing `declared_gate_refs` can be admitted and later interpreted as template/default adoption

- Severity: medium-high.
- Axis attribution: Link declaration boundary, with support validation/runtime fallback.
- Evidence:
  - `AGENTS.md:88-94` says support may walk/validate/record/project/observe, but must not choose Movement, invent route targets, or create undeclared GateFacts.
  - `AGENTS.md:485-494` says `run.py` and `dynamic_walker.py` preserve declared rows and support authors no route or Movement.
  - `support/operator/plan_validation.py:1194-1196` returns without error when `declared_gate_refs` is absent.
  - `support/operator/walker_step_fixture.py:165-198` falls through to `adopt` when no gate authority is declared.
  - `support/operator/walker_step_fixture.py:201-213` emits `template:default-transition` when no author is present.
  - `support/operator/walker_kernel.py:1859-1866` treats default/template gate as auto-adopt when target budget exists.
  - `support/operator/walker_kernel.py:2088-2094` records `adopted_by` using `_adopted_by_ref(step)` if no human disposition author is present.
- Meaning: the raw plan validator allows a missing Link gate declaration, and a later support helper gives that absence default adoption semantics. Claude review C10 correctly narrows the finding: default-transition auto-advance is constitutionally admitted for static order or exactly one eligible next target, so this is not proof of a forbidden arbitrary route. The remaining issue is the admission seam: absence is normalized into an admitted default without a visible materialization/normalization boundary.
- Proof status: confirmed by code inspection and read-only probe.

### S3-F2 - Invalid Agent transition concern can still shape a HOLD pending target

- Severity: high.
- Axis attribution: Agent non-binding evidence crossing into Link lifecycle pause target.
- Evidence:
  - `AGENTS.md:673-675` says `transition_concern_evidence` may describe a concern or proposed transition, but does not choose Movement or route target.
  - `agent/return_fact.py:128-156` requires valid concern shape and `binding: false`.
  - `support/operator/walker_transition_concern.py:231-238` records invalid concern evidence after validation failure.
  - `support/operator/walker_transition_concern.py:257-270` reads the raw invalid concern and resolves a single proposed target, falling back to the source brick only when no single declared target resolves.
  - `support/operator/walker_transition_concern.py:283-300` returns a single target only when exactly one declared Brick ref resolves.
  - `support/operator/walker_hold.py:70-85` writes that target as `immediate_target_ref`, `target_brick`, and `pending_target_ref`.
- Meaning: malformed Agent output does not adopt Movement, but it can still populate the Link pause target when it contains a single resolvable declared target. Claude review C18 adds the required mitigation: this path produces a HOLD/pause requiring human/COO disposition; it does not autonomously execute reroute. The remaining issue is that invalid Agent evidence can shape the pending target the human/COO sees.
- Proof status: confirmed by direct code inspection. Full dynamic-run reproduction not performed.

### S3-F3 - Raw graph admission does not consistently carry composition-level fan-in adoption policy checks

- Severity: medium-high.
- Axis attribution: Link fan-in/adoption policy, with support graph admission split.
- Evidence:
  - `AGENTS.md:385-388` assigns fan-out/fan-in transition meaning and portfolio adoption policy to Link.
  - `support/operator/composition_graph_validate.py:75-124` and `:352-441` provide strong composition-path rules for fan-in target/adoption.
  - `support/operator/walker_kernel.py:844-859` linearizes raw graph input and calls declared plan validation.
  - `support/operator/plan_graph.py:323-395` checks topology roots, cycles, fan groups, and target references.
  - `support/operator/walker_fan_in.py:277-424` applies cohort replay/reverify behavior in support, including the human-vouched sibling-independence exception.
  - `support/operator/walker_kernel.py:2036-2075` appends sibling replay scope from that support policy.
- Meaning: this is declared-node-only and not a confirmed hidden target selector, but the policy is not uniformly admitted as Link declaration when raw graph admission bypasses the composition validator path.
- Proof status: partially confirmed as a boundary split. Semantic correctness of the fan-in replay policy is `NOT_PROVEN`.

### S3-F4 - `re_instruction` is active in code but absent from the visible AGENTS lifecycle shape

- Severity: medium-high.
- Axis attribution: Link lifecycle field carrying Brick/Agent instruction text through support prompt transport.
- Evidence:
  - `AGENTS.md:677-687` lists the active `transition_lifecycle` shape and does not list `re_instruction`.
  - `link/transition.py:20-44` includes `re_instruction` in `TRANSITION_LIFECYCLE_ALLOWED_KEYS`.
  - `link/spec.py:663-697` admits the same field in the Link envelope schema.
  - `support/operator/walker_resume.py:334-352`, `support/operator/walker_kernel.py:550-554`, and `support/operator/run.py:2050` carry it through resume/run packets.
  - `support/connection/adapter_grant_policy.py:347-348` injects it into the Agent prompt packet.
- Meaning: a Link lifecycle field is carrying corrected how-to text into the next Brick/Agent prompt. It may be intended, but the visible constitution does not currently admit it in the active shape.
- Proof status: confirmed as code/constitution drift, not a runtime failure proof.

### S3-F5 - Stale disposition-action error text omits `reroute`

- Severity: low.
- Axis attribution: Link lifecycle diagnostic contract drift.
- Evidence:
  - `AGENTS.md:685` and `link/transition.py:10` admit `raise`, `forward`, `stop`, and `reroute` as disposition actions.
  - `support/operator/plan_validation.py:1825-1828` still says the action must be `raise`, `forward`, or `stop`.
  - Claude review C3 corrected the `support/operator/walker_reroute_budget.py` locator to line 161.
  - Claude review C11 verified both stale-string sites still accept `reroute`
    at runtime through the active disposition action set.
- Meaning: runtime admits `reroute`, but error output teaches the older three-action contract. This is a cosmetic/product-diagnostic defect, not a behavioral Link defect.
- Proof status: confirmed as wording drift.

### S3-F6 - Link/support godmodule pressure is real but not a deletion instruction

- Severity: medium.
- Axis attribution: Link grammar concentration plus support runtime concentration.
- Evidence:
  - `link/spec.py` is 908 lines and owns gate registry, gate placement, row keys, route replay forbidden keys, envelope schema, transition lifecycle schema, and frontier sufficiency precedence.
  - `link/spec.py:804-908` explicitly moves a support observer frontier ladder into Link as sufficiency verdict logic.
  - `support/operator/walker_kernel.py` is 2306 lines and mixes step execution, gate sequence, transition concern adoption, fan-in, HOLD injection, evidence writing, and reporting.
  - `support/operator/run.py` is 2240 lines and `support/operator/driver.py` is 1722 lines.
- Meaning: size alone is not an authority leak, but Link/support changes here are high-risk and should be checker-first before any split or deletion.
- Proof status: confirmed as architecture risk, not safe cleanup permission.

## External Review Incorporation

Claude review and Smith/operator follow-up sharpened S3 in six ways.

1. Default-transition is admitted, but absence normalization still needs a
   declared seam.
   - C10 down-calibrates S3-F1: default adoption is not itself
     unconstitutional.
   - The actionable issue is whether a raw row missing `declared_gate_refs`
     should be rejected or explicitly materialized into a default-transition
     declaration before runtime.

2. HOLD is lifecycle; reroute is Link Movement.
   - Smith's correction is reflected here: Agent concern evidence can lead to a
     pause/HOLD for human/COO disposition, but the Movement vocabulary remains
     `forward` / `reroute`.
   - Do not describe HOLD as the route itself.
   - A human/COO disposition may choose `forward`, `stop`, `raise`, or `reroute`
     according to the admitted lifecycle action surface.

3. Invalid concern target shaping is narrower than autonomous reroute.
   - C18 confirms invalid concern evidence produces a paused/HOLD state, not an
     executed reroute.
   - The concern remains high enough to repair because invalid Agent evidence
     can still shape the pending target that the disposition owner sees.

4. Carry runtime remains an uninspected first-class Link seam.
   - Claude ADD-5 notes `walker_carry.py` was not inspected even though carry is
     the first Link scope item.
   - The missing question is whether support can synthesize carry, rewrite
     `source_owner_axis`, or advance write nodes with empty/weak carry gates.
   - This is a coverage gap, not a demonstrated defect.

5. Portfolio adoption authority needs the same treatment as single-Building
   gate adoption.
   - Claude ADD-14 notes the portfolio adoption seam in `driver.py` was not
     probed for forbidden adopter prefixes and Link-owned adoption boundaries.
   - Existing guards may be adequate, but the audit did not prove them through a
     negative case.

6. Resume target-divergence has controls that should be credited.
   - Claude ADD-20 notes existing static guards in resume path reject
     building-boundary/self-reroute and require the pending target in the
     declared plan, while `re_instruction` binds only to the matching declared
     step.
   - Keep these as Controls That Hold, while still leaving dynamic interleaving
     proof `NOT_PROVEN`.

## Controls That Hold

- Active Movement is only `forward` / `reroute`: `AGENTS.md:401-412`, `link/movement.py:12-18`, and `link/movement.py:37-39`.
- Plan validation requires exactly one Movement and target and rejects non-active Movement words: `support/operator/plan_validation.py:1165-1192`.
- GateFact shape remains sufficiency-only: `link/gate.py:59-80`; the evaluator returns GateFact evidence, not Movement.
- Gate registry is single-sourced through `link/spec.py::GATE_REGISTRY`, with `link/gate.py` deriving declared refs.
- Agent returned facts reject top-level Movement/verdict/success/failure keys: `agent/return_fact.py:42-67`.
- Gate sequence policy actions such as `hold` and `next` are not Link Movement literals; they are runtime policy/lifecycle controls.
- Route materialization is constrained by declared route policy/plan checks. No arbitrary support-invented target was proven.
- Resume target-divergence is partially controlled by static guards that require
  pending targets to be declared and prevent self/boundary misuse. Dynamic
  interleaving proof remains not proven.

## Rejected Shortcuts

- "Link is broken" was rejected. Core Movement/GateFact contracts still hold under checked paths.
- "QA can route by itself" was rejected. Agent concerns are non-binding, and adoption still passes through declared gate/policy/budget paths.
- "GateFact is the runtime halt/adoption authority" was rejected. GateFact records sufficiency; HOLD/adoption comes from declared gate sequence or disposition policy.
- "Support route materialization proves support invented the route" was rejected. The route materializer builds rows from declared policy/replay inputs, but remains a high-risk support surface.
- "Checker green proves semantic routing correctness" was rejected. The checks prove structural and local runtime invariants, not future concern semantics or provider behavior.
- "Stale docs/literals are dead code" was rejected. Several old Movement words remain intentionally as negative probes or historical evidence.

## Verdict

`ISSUE`.

The Link core is not collapsed: Movement is binary, GateFact is sufficiency-only,
and checked runtime paths generally walk declared Link rows. The surface is not
clear because raw plan admission can omit `declared_gate_refs` and later receive
default adoption semantics; invalid Agent concern evidence can still set a HOLD
pending target; raw graph admission does not uniformly carry composition-level
fan-in adoption policy checks; `re_instruction` exists in code without visible
AGENTS shape admission; stale error text omits `reroute`; and Link/support
godmodule pressure is concentrated in high-risk files.

Readiness tuple: use `brick-6-surface-audit-readiness-tuples-0630.md` for implementation priority. S3 is `core_sound: partial`, `axis_integrity_blockers: 4`, `ship_safety_blockers: 1`, `dynamic_runtime_not_proven: yes`, and `worst_severity: high`. The flat `ISSUE` label is only a findings-inventory label; it is not Link Movement.

## Next Work Candidates

1. Add a checker-first negative case where a raw Link row without
   `declared_gate_refs` is rejected or explicitly normalized by an admitted
   Brick/Link declaration path before runtime.
2. Ensure invalid `transition_concern_evidence` cannot supply a pending target;
   an invalid concern should HOLD at the source boundary unless a declared
   Link/caller/COO disposition supplies the target.
3. Decide whether `re_instruction` is admitted Link lifecycle evidence or should
   be removed/relocated; update constitution/checkers before code changes.
4. Bring raw graph admission and composition graph validation into the same
   Link fan-in/adoption policy contract, or explicitly document and checker-pin
   the split.
5. Add carry-runtime negative probes around source-owner, carry gate, and write-node advancement.
6. Add portfolio adoption negative probes for forbidden adopter prefixes and undeclared adoption authority.
7. Fix stale disposition-action error text to include `reroute`.
8. Treat `link/spec.py` and `walker_kernel.py` splits as later cleanup only,
   with conservation ledgers and mutation-RED coverage.

## Not Proven

- Semantic correctness of future `transition_concern_evidence`.
- Real provider/runtime behavior under live `brick build`.
- Complete absence of support-authority leaks outside audited paths.
- Safe deletion or split of `link/spec.py`, `walker_kernel.py`, `driver.py`, or `run.py`.
- Persisted production Building evidence for every route-policy path.
