---
preset_ref: building-chain-preset:postmortem
catalog_scope: common
selected_shape_ref: building-shape:design-needed
intent: "Postmortem cause-analysis route for incident evidence: work investigation without source mutation, fan out reproduction and evidence-claim review, then close with cause attribution and prevention candidates."
selection_hint: "Use when the task asks for 부검, postmortem, incident postmortem, postmortem 발주, root cause, root-cause analysis, cause analysis, evidence postmortem, stalled Building attribution, or 원인 규명 from existing evidence."
steps:
  - step_template_ref: building-step-template:work
    brick_spec_ref: brick/templates/bricks/work/brick.md
    target_word: parallel_recon
    selected_adapter_ref: adapter:codex-local
  - step_template_ref: building-step-template:code-attack-qa
    step_alias: reproduction-lens
    brick_spec_ref: brick/templates/bricks/code-attack-qa/brick.md
    target_word: fan_in_final_gate
    selected_adapter_ref: adapter:codex-local
  - step_template_ref: building-step-template:review
    step_alias: evidence-claim-review
    brick_spec_ref: brick/templates/bricks/review/brick.md
    target_word: fan_in_final_gate
    selected_adapter_ref: adapter:codex-local
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick/templates/bricks/closure/brick.md
    target_word: closure
    selected_adapter_ref: adapter:codex-local
gate_concept_profile:
  - strict-evidence
  - fan-in-wait-all
node_reroute_budgets:
  building-step-template:work: 1
closure_transition_target_policy:
  implementation_gap:
    action: target
    target_step_template_ref: building-step-template:work
  verification_gap:
    action: hold
proof_limits:
  - postmortem preset is a caller / COO selection candidate only
  - work investigation and review steps are read-only by task contract; code-attack reproduction may use only admitted disposable probe or verification writes
  - fan-in closure synthesis records evidence-backed cause attribution candidates, not success or quality judgment
  - preset text promotes the evidence-postmortem task skeleton but does not copy or mutate the historical status template
  - not automatic shape selection
  - not Building Plan authoring from task text
anti_hint: Do not use for planned production work or when source mutation is required instead of cause analysis from evidence.
blocks:
  - B4
  - B8
---

# postmortem

## Route

Postmortem route: run a work investigation over the incident evidence without source mutation, fan out one reproduction lens and one evidence-claim review lens, then fan in to closure synthesis for cause attribution and recurrence-prevention candidates. The route declares graph shape only; the engine may still walk the declared graph sequentially.

## Work Statement Skeleton

Use the evidence-postmortem task structure when authoring the concrete task statement:

1. Targets: list the Building roots or incident records to inspect.
2. Evidence sources per root: name raw Link rows, Agent receipt and return rows, task and plan inputs, step outputs, capture events, and relevant Brick specs.
3. Attribution method: test Brick, Agent, Link, and support ownership for each incident before proposing a primary and secondary axis.
4. Required output shape: incident, owning_axis, evidence_refs, repair_candidate, and not_proven.
5. Hard constraints: read incident roots as evidence, avoid success / quality / approval / Movement claims, and keep refs in admitted forms.
6. Operating context: distinguish emergency triage from recorded postmortem evidence.
7. Pattern synthesis: summarize repeated incident families separately from individual incidents.
8. Proof limits: state what the postmortem does not prove about provider behavior, future Building correctness, source truth, success, quality, or Movement.
