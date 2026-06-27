---
preset_ref: building-chain-preset:four-llm-standard-graph
catalog_scope: brick_protocol_dogfood
common_basis_ref: building-chain-preset:triage-fanout-3
selected_shape_ref: building-shape:design-needed
intent: Weekend Codex/Gemini dogfood graph -- one Codex implementation root fans out to two attack lenses (Codex code-attack QA and Gemini axis-attack QA via adapter:gemini-local) that fan in to one Codex COO closure synthesis. Exactly one implementation root; attack-QA work-area writes only open where the Brick declares write NEED. NOTE 0627 -- Claude is temporarily out of active performer rotation until Monday token capacity returns; the preset_ref/filename keep the 'four-llm' name for reference stability.
selection_hint: Use for Brick Protocol weekend dogfood work that needs one implementation lane followed by Codex code QA and Gemini axis/evidence QA converging on a single Codex closure synthesis. Declares the graph explicitly via graph_topology; the work and attack-QA nodes carry write need, so the caller declares write_scope at intake.
steps:
  - step_template_ref: building-step-template:work
    brick_spec_ref: brick/templates/bricks/work/brick.md
    target_word: three_llm_review
    selected_adapter_ref: adapter:codex-local
    selected_model_ref: model:codex:default
  - step_template_ref: building-step-template:code-attack-qa
    step_alias: codex-code-attack-qa
    brick_spec_ref: brick/templates/bricks/code-attack-qa/brick.md
    target_word: closure
    selected_adapter_ref: adapter:codex-local
    selected_model_ref: model:codex:default
  - step_template_ref: building-step-template:axis-attack-qa
    step_alias: gemini-axis-attack-qa
    brick_spec_ref: brick/templates/bricks/axis-attack-qa/brick.md
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
# attack lenses (Codex code-attack QA, Gemini axis-attack QA via gemini-local)
# that all fan in to a single Codex closure synthesis. Node identity =
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
# (requires_brick_write_scope: yes in brick/templates/bricks/work/brick.md), and
# both attack-QA lens templates also carry write need for sandboxed probes. The
# preset embeds NO write_scope; the caller declares a narrow write_scope at run
# intake and effective write still opens only at Brick write_scope NEED + Agent
# policy + observed-write adapter. The work root is the only implementation
# source-truth mutation lane; attack-QA writes only the disposable W1 work-area
# to run probes and record evidence. Closure remains synthesis work. Claude can
# return by explicit override when tokens are available.
graph_topology:
  edges:
    - { from: building-step-template:work, to: codex-code-attack-qa }
    - { from: building-step-template:work, to: gemini-axis-attack-qa }
    - { from: codex-code-attack-qa, to: closure }
    - { from: gemini-axis-attack-qa, to: closure }
  fan_out_groups:
    - from: building-step-template:work
      branches:
        - codex-code-attack-qa
        - gemini-axis-attack-qa
  fan_in_groups:
    - converge_on: closure
      sources:
        - codex-code-attack-qa
        - gemini-axis-attack-qa
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
  - the work and attack-QA steps carry write need, so the caller must declare write_scope at intake
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
two independent attack lenses: Codex code-attack QA and Gemini axis-attack QA
(via adapter:gemini-local). Both lenses fan in to one Codex COO closure synthesis. A
single-convergence board modeled on triage-fanout-3, but with explicit
Codex/Gemini lane casting and a write root instead of a read-only recon. The lens
nodes use attack-QA Brick kinds so they must inspect real sources and run probes
instead of treating packet summaries as QA.

Exactly one implementation source-truth write node (work-codex); the two
attack-QA lenses may write only their disposable W1 work-area for probes, and
closure remains synthesis work.
Effective write opens only at the intersection of the Brick write_scope NEED, the
Agent tool policy, and an observed-write adapter. On an implementation gap the
closure reroutes back to the work root (budgeted, work:1); a verification gap
holds for caller/COO disposition. The closing building boundary attaches to the
declared terminal (closure).

Claude is outside the weekend active performer pool only because of token
capacity, not because the adapter/ref is retired.

Run the smaller read-only smoke first (compose + materialize the plan with no live
providers, then a one-file-per-provider read-only pass) before any full write
graph run.
