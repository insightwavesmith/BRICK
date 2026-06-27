---
preset_ref: building-chain-preset:four-llm-standard-graph
catalog_scope: brick_protocol_dogfood
common_basis_ref: building-chain-preset:triage-fanout-3
selected_shape_ref: building-shape:design-needed
intent: Weekend Codex/Gemini dogfood graph -- one Codex implementation root fans out to two review lenses (Codex structure QA, Gemini broad review via adapter:gemini-local) that fan in to one Codex COO closure synthesis. Exactly one write root; review writes only open where the Brick declares write NEED. NOTE 0627 -- Claude is temporarily out of active performer rotation until Monday token capacity returns; the preset_ref/filename keep the 'four-llm' name for reference stability.
selection_hint: Use for Brick Protocol weekend dogfood work that needs one implementation lane followed by Codex and Gemini review lenses converging on a single Codex closure synthesis. Declares the graph explicitly via graph_topology; the work node carries write need, so the caller declares write_scope at intake.
steps:
  - step_template_ref: building-step-template:work
    brick_spec_ref: brick/templates/bricks/work/brick.md
    target_word: three_llm_review
    selected_adapter_ref: adapter:codex-local
    selected_model_ref: model:codex:default
  - step_template_ref: building-step-template:review
    step_alias: codex-structure-qa
    brick_spec_ref: brick/templates/bricks/review/brick.md
    target_word: closure
    selected_adapter_ref: adapter:codex-local
    selected_model_ref: model:codex:default
  - step_template_ref: building-step-template:inspect
    step_alias: gemini-broad-review
    brick_spec_ref: brick/templates/bricks/inspect/brick.md
    target_word: closure
    selected_adapter_ref: adapter:gemini-local
    selected_model_ref: model:gemini:default
  - step_template_ref: building-step-template:closure
    step_alias: closure
    brick_spec_ref: brick/templates/bricks/closure/brick.md
    target_word: closure
    # selected closure stays Codex while Claude is outside the weekend active pool.
    selected_adapter_ref: adapter:codex-local
    selected_model_ref: model:codex:default
# DECLARED graph_topology (E1 full-lego): one Codex work root fans out TWO
# review lenses (Codex structure QA, Gemini broad review via gemini-local) that
# all fan in to a single Codex closure synthesis. Node identity =
# step_alias; the work ROOT carries NO alias, so its handle is its
# step_template_ref (building-step-template:work) -- this mirrors the proven
# triage-fanout-3 root and lets the closure implementation_gap target
# (target_step_template_ref: building-step-template:work) resolve to the work
# node. One fan_in_group (single convergence) whose converge_on is the declared
# terminal (closure).
# Edge/group endpoints use from/to/converge_on handles (never the Link-owned bare
# key 'target') so the Brick-template axis-owned-field scan stays green.
# target_word stays a local descriptive hint -- the declared topology drives the
# shape, not positional inference. The work root carries write need
# (requires_brick_write_scope: yes in brick/templates/bricks/work/brick.md), so
# the preset embeds NO write_scope; the caller declares a narrow write_scope on
# the work node at run intake (same rule as one-brick-do). The two lenses and
# closure are not implementation lanes; Gemini write capability remains governed
# by Brick write_scope NEED plus Agent policy. WRITE-NEED CONSTRAINT
# (measured): the attack-QA templates (code-attack-qa, axis-attack-qa,
# evidence-integrity) all carry requires_brick_write_scope: yes, so they would
# receive write_scope and are NOT used for the read-only lens nodes. Instead:
# Codex uses the read-only review template and Gemini uses the read-only inspect
# template. Thus the work root is the only implementation node; the lens nodes
# and closure remain declared review / synthesis work while their step_alias
# names preserve their review intent. (The Fugu axis-attack lane is outside this
# weekend graph because of token capacity; Claude can return by explicit override
# when tokens are available.)
graph_topology:
  edges:
    - { from: building-step-template:work, to: codex-structure-qa }
    - { from: building-step-template:work, to: gemini-broad-review }
    - { from: codex-structure-qa, to: closure }
    - { from: gemini-broad-review, to: closure }
  fan_out_groups:
    - from: building-step-template:work
      branches:
        - codex-structure-qa
        - gemini-broad-review
  fan_in_groups:
    - converge_on: closure
      sources:
        - codex-structure-qa
        - gemini-broad-review
      closure_transition_target_policy:
        implementation_gap:
          action: target
          target_step_template_ref: building-step-template:work
        verification_gap:
          action: hold
  terminal: closure
node_reroute_budgets:
  building-step-template:work: 1
gate_concept_profile:
  - strict-evidence
  - fan-in-wait-all
proof_limits:
  - declared weekend Codex/Gemini single-convergence graph example only
  - the work step carries write need, so the caller must declare write_scope at intake
  - fan-in closure synthesis is support evidence, not success or quality judgment
  - provider/model selection remains declared routing data, not provider availability proof
  - live Codex/Gemini execution and runtime parallel fan-out are not proven
  - preset is not runtime parallel execution
---

# four-llm-standard-graph

## Route

The weekend multi-LLM dogfood board (Codex + Gemini, with Claude preserved as a
launch-time override option when tokens return). One Codex work root performs the
declared implementation inside its caller-declared write scope, then fans out to
two independent review lenses: Codex structure QA and Gemini broad review (via
adapter:gemini-local). Both lenses fan in to one Codex COO closure synthesis. A
single-convergence board modeled on triage-fanout-3, but with explicit
Codex/Gemini lane casting and a write root instead of a read-only recon. The lens
nodes use review/inspect templates so provider review lanes do not silently
inherit implementation authority.

Exactly one implementation write node (work-codex); the two lenses and closure
remain review / synthesis nodes.
Effective write opens only at the intersection of the Brick write_scope NEED, the
Agent tool policy, and an observed-write adapter. On an implementation gap the
closure reroutes back to the work root (budgeted, work:1); a verification gap
holds for caller/COO disposition. The closing building boundary attaches to the
declared terminal (closure).

The Fugu/sakana axis-attack lane is outside this weekend graph because of token
capacity; Claude is outside the weekend active performer pool only because of
token capacity, not because the adapter/ref is retired.

Run the smaller read-only smoke first (compose + materialize the plan with no live
providers, then a one-file-per-provider read-only pass) before any full write
graph run.
