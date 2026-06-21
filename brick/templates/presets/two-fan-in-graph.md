---
preset_ref: building-chain-preset:two-fan-in-graph
catalog_scope: common
selected_shape_ref: building-shape:design-needed
intent: Two-convergence (Y-shape) review fleet -- paired code lenses fan in to a mid synthesis, paired axis lenses fan in to the closing synthesis, exercising TWO distinct fan-in targets that positional inference cannot express.
selection_hint: Use only as the E1 full-lego example -- it DECLARES an explicit graph_topology with two fan-in groups (two convergence points) and an explicit terminal. No existing preset is changed; this is the multi-fan-in parity exhibit.
steps:
  - step_template_ref: building-step-template:inspect
    brick_spec_ref: brick/templates/bricks/inspect/brick.md
    target_word: recon
    selected_adapter_ref: adapter:codex-local
  - step_template_ref: building-step-template:code-attack-qa
    step_alias: code-lens-a
    brick_spec_ref: brick/templates/bricks/code-attack-qa/brick.md
    target_word: code_review
    selected_adapter_ref: adapter:codex-local
  - step_template_ref: building-step-template:code-attack-qa
    step_alias: code-lens-b
    brick_spec_ref: brick/templates/bricks/code-attack-qa/brick.md
    target_word: code_review
    selected_adapter_ref: adapter:codex-local
  - step_template_ref: building-step-template:axis-attack-qa
    step_alias: axis-lens-a
    brick_spec_ref: brick/templates/bricks/axis-attack-qa/brick.md
    target_word: axis_review
    selected_adapter_ref: adapter:codex-local
  - step_template_ref: building-step-template:axis-attack-qa
    step_alias: axis-lens-b
    brick_spec_ref: brick/templates/bricks/axis-attack-qa/brick.md
    target_word: axis_review
    selected_adapter_ref: adapter:codex-local
  - step_template_ref: building-step-template:closure
    step_alias: mid-closure
    brick_spec_ref: brick/templates/bricks/closure/brick.md
    target_word: mid_synthesis
    selected_adapter_ref: adapter:codex-local
  - step_template_ref: building-step-template:closure
    step_alias: final-closure
    brick_spec_ref: brick/templates/bricks/closure/brick.md
    target_word: final_synthesis
    selected_adapter_ref: adapter:codex-local
# E1 FULL-LEGO: the preset DECLARES the graph topology explicitly. The
# materializer emits EXACTLY these groups+edges (no positional inference): the
# per-step target_word stays a local descriptive hint and is NOT a
# parallel/fan_in inference marker, so the positional fan-out detector is never
# consulted -- the declared graph_topology drives the shape. Node identity =
# step_alias (the inspect root has no alias -> its step_template_ref is the
# handle). Two distinct fan_in_groups => two convergence points (mid-closure,
# final-closure); final-closure is the declared terminal. The plain
# mid-closure -> final-closure edge is NOT a fan_in member, so mid-closure is a
# linear (concern-bearing) node on its outgoing side, never a fan-in source.
# Edge/group endpoints use from/to/converge_on handles (never the Link-owned
# bare key 'target') so the Brick-template axis-owned-field scan stays green.
graph_topology:
  edges:
    - { from: building-step-template:inspect, to: code-lens-a }
    - { from: building-step-template:inspect, to: code-lens-b }
    - { from: building-step-template:inspect, to: axis-lens-a }
    - { from: building-step-template:inspect, to: axis-lens-b }
    - { from: code-lens-a, to: mid-closure }
    - { from: code-lens-b, to: mid-closure }
    - { from: mid-closure, to: final-closure }
    - { from: axis-lens-a, to: final-closure }
    - { from: axis-lens-b, to: final-closure }
  fan_out_groups:
    - from: building-step-template:inspect
      branches:
        - code-lens-a
        - code-lens-b
        - axis-lens-a
        - axis-lens-b
  fan_in_groups:
    - converge_on: mid-closure
      sources:
        - code-lens-a
        - code-lens-b
      closure_transition_target_policy:
        implementation_gap:
          action: target
          target_step_template_ref: building-step-template:inspect
        verification_gap:
          action: hold
    - converge_on: final-closure
      sources:
        - axis-lens-a
        - axis-lens-b
      closure_transition_target_policy:
        implementation_gap:
          action: target
          target_step_template_ref: building-step-template:inspect
        verification_gap:
          action: hold
  terminal: final-closure
node_reroute_budgets:
  building-step-template:inspect: 1
gate_concept_profile:
  - strict-evidence
  - fan-in-wait-all
proof_limits:
  - declared two-fan-in graph example only
  - fan-in closure synthesis is support evidence, not success or quality judgment
  - provider/model selection remains declared routing data, not provider availability proof
  - preset is not runtime parallel execution
---

# two-fan-in-graph

## Route

E1 full-lego exhibit. Inspect the boundary, fan out two code-attack lenses and two
axis-attack lenses. The two code lenses fan in to a MID closure synthesis; the two
axis lenses fan in to the FINAL closure synthesis, which the mid closure also feeds
through a plain forward edge. Two distinct fan-in targets (two convergence points)
make a Y-shape that positional inference cannot express -- the preset declares the
topology explicitly through graph_topology, and the materializer emits exactly those
groups and edges. The closing building boundary attaches to the declared terminal
(final-closure).
