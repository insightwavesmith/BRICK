---
preset_ref: building-chain-preset:building-call-authoring
catalog_scope: common
intent: Draft a Building call order through the five-step authoring sequence, then close with observed evidence.
selection_hint: Use when the request needs order authoring before any Building launch, lowering, or execution.
steps:
  - step_template_ref: building-step-template:building-call-authoring
    brick_spec_ref: brick_protocol/brick/templates/bricks/building-call-authoring/brick.md
    target_word: closure
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick_protocol/brick/templates/bricks/closure/brick.md
    target_word: closure
proof_limits:
  - chain preset is a caller / COO selection candidate only
  - not automatic shape selection
  - not Building Plan authoring from task text
  - not launch authorization
  - not lowering
  - not source truth
  - not success judgment
  - not quality judgment
  - not Movement authority
anti_hint: Do not use when a direct quick_check or quick_fix path has already been admitted and fast-confirmed, or when human_gate_first is required before drafting.
blocks:
  - GOAL-0708-5e
---

# building-call-authoring

## Route

Draft-only order-authoring route: the first Brick records a provider-neutral Building call draft using STEP1 scope, STEP2 whole-building intensity/routing, STEP3 structure, STEP4 per-Brick intensity, and STEP5 Agent candidates/strength in that exact order. Closure then records the observed draft evidence and remaining delta. This preset does not confirm, lower, launch, select a route, expose provider casting, or judge outcome.
