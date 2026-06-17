---
preset_ref: building-chain-preset:triage-fanout-3
catalog_scope: common
selected_shape_ref: building-shape:design-needed
intent: Three independent read-only review lenses (code, axis, evidence) fan out from one recon and fan in to a single closure synthesis -- a 3-way parallel review board that positional inference cannot express (it caps at the design-build-parallel 2-way).
selection_hint: Use when one read-only recon should split into THREE distinct review lenses (code-attack, axis-attack, evidence-integrity) that converge on one closure. Wider than design-build-parallel (2 lenses); declares the 3-branch fan explicitly via graph_topology.
steps:
  - step_template_ref: building-step-template:inspect
    brick_spec_ref: brick/templates/bricks/inspect/brick.md
    target_word: recon
    selected_adapter_ref: adapter:codex-local
    selected_model_ref: model:default
  - step_template_ref: building-step-template:code-attack-qa
    step_alias: code-lens
    brick_spec_ref: brick/templates/bricks/code-attack-qa/brick.md
    target_word: code_review
    selected_adapter_ref: adapter:codex-local
    selected_model_ref: model:default
  - step_template_ref: building-step-template:axis-attack-qa
    step_alias: axis-lens
    brick_spec_ref: brick/templates/bricks/axis-attack-qa/brick.md
    target_word: axis_review
    selected_adapter_ref: adapter:codex-local
    selected_model_ref: model:default
  - step_template_ref: building-step-template:evidence-integrity
    step_alias: evidence-lens
    brick_spec_ref: brick/templates/bricks/evidence-integrity/brick.md
    target_word: evidence_review
    selected_adapter_ref: adapter:codex-local
    selected_model_ref: model:default
  - step_template_ref: building-step-template:closure
    step_alias: triage-closure
    brick_spec_ref: brick/templates/bricks/closure/brick.md
    target_word: triage_synthesis
    selected_adapter_ref: adapter:codex-local
    selected_model_ref: model:default
# DECLARED graph_topology (E1 full-lego): one recon fans out THREE read-only lenses
# that all fan in to a single closure. Node identity = step_alias (the inspect root
# has no alias -> its step_template_ref is the handle). One fan_in_group (single
# convergence) whose converge_on is the declared terminal. Edge/group endpoints use
# from/to/converge_on handles (never the Link-owned bare 'target') so the
# Brick-template axis-owned-field scan stays green. target_word stays a local
# descriptive hint -- the declared topology drives the shape, not positional inference.
graph_topology:
  edges:
    - { from: building-step-template:inspect, to: code-lens }
    - { from: building-step-template:inspect, to: axis-lens }
    - { from: building-step-template:inspect, to: evidence-lens }
    - { from: code-lens, to: triage-closure }
    - { from: axis-lens, to: triage-closure }
    - { from: evidence-lens, to: triage-closure }
  fan_out_groups:
    - from: building-step-template:inspect
      branches:
        - code-lens
        - axis-lens
        - evidence-lens
  fan_in_groups:
    - converge_on: triage-closure
      sources:
        - code-lens
        - axis-lens
        - evidence-lens
      closure_transition_target_policy:
        implementation_gap:
          action: target
          target_step_template_ref: building-step-template:inspect
        verification_gap:
          action: hold
  terminal: triage-closure
node_reroute_budgets:
  building-step-template:inspect: 1
gate_concept_profile:
  - strict-evidence
  - fan-in-wait-all
proof_limits:
  - declared three-way single-convergence graph example only
  - fan-in closure synthesis is support evidence, not success or quality judgment
  - provider/model selection remains declared routing data, not provider availability proof
  - preset is not runtime parallel execution
---

# triage-fanout-3

## Route

One recon inspects the boundary, then fans out THREE independent read-only review
lenses -- code-attack, axis-attack, and evidence-integrity -- which all fan in to a
single closure synthesis. A 3-way single-convergence board: wider than the positional
2-way (design-build-parallel) and simpler than the Y-shape two-fan-in-graph. The
preset declares the topology explicitly through graph_topology; the materializer emits
exactly these groups and edges. On an implementation gap the closure reroutes back to
the recon root (budgeted); a verification gap holds for caller/COO disposition.
