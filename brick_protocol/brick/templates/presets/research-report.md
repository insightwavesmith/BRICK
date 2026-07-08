---
preset_ref: building-chain-preset:research-report
catalog_scope: common
intent: Read-only investigation that bounds a question, checks the gathered evidence, and closes with a cited report.
selection_hint: Use when the task is research or investigation only and nothing on disk may change.
steps:
  - step_template_ref: building-step-template:plan
    brick_spec_ref: brick_protocol/brick/templates/bricks/plan/brick.md
    target_word: review
  - step_template_ref: building-step-template:review
    brick_spec_ref: brick_protocol/brick/templates/bricks/review/brick.md
    target_word: closure
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick_protocol/brick/templates/bricks/closure/brick.md
    target_word: closure
proof_limits:
  - chain preset is a caller / COO selection candidate only
  - not automatic shape selection
  - not Building Plan authoring from task text
  - no write-need step exists on this route, so no caller write_scope is required
anti_hint: Do not use when disk mutation is expected or when the research question lacks a bounded evidence target.
blocks:
  - B4
---

# research-report

## Route

Read-only research route: plan bounds the question and names the evidence to gather, review reads the sources and checks the gathered evidence against the declared question, closure returns the evidence-cited report. No step carries write need, so the route materializes without any caller write_scope and mutates no file anywhere.
