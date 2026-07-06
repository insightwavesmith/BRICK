---
brick_kind: deep-design
brick_word: deep-design
performer_word: design
requires_brick_write_scope: no
capability_class: read
performer_lane_need: leader
agent_object_hint_ref: agent-object:design-lead
required_return_template_refs:
  - brick/templates/bricks/deep-design/return.yaml
  - brick/templates/bricks/transition-concern-return.yaml
link_movement_literal: forward
brick_contract: Deep-Design Brick closes EVERY open decision itself and hands the work lane a transcription-narrow implementation plan — per-deliverable file:line plans, a decision ledger, hunk sketches, mutation designs, and a forbidden-drift list.
---

## Deep Design

Design at full depth and CLOSE every open decision — this kind exists so the downstream work lane's freedom narrows to transcribe-and-verify (a deliberately cheap-brain-friendly shape). Study the relevant current structure first, then return: `design_summary` (the shape of the change in a paragraph); `per_deliverable_plan` (one entry per numbered deliverable with exact file:line anchors and ordered edit steps); `decision_ledger` (EVERY decision this design closed, each with rationale and a reversal note — an undecidable point is NOT forwarded as an open question: pick a safe default, record it here, and mark its reversal path); `hunk_sketches` (near-literal sketches of the key hunks anchored at file:line — sketches, not full patches, but concrete enough to transcribe); `mutation_designs` (for each new guard: what to break, the exact command, and the literal RED text expected); `forbidden_drift` (files, behaviors, and pins the work lane must NOT touch); `candidate_file_changes` (proposed targets only — do not edit, create, or mutate any file); `reading_scope_map` (ordered, most-important-first read list); `invariants` (what must stay true after the change); `partition_plan` (the §A2 fan-partition proposal for the next stage — width_decision with an n≤3 ceiling, branches carrying disjoint write_set + casting, done_line, residual_owner, qa_plan, env_plan, and expansion; a design that proposes no fan returns width_decision.n: 1 with branches: []); `observed_evidence` (file:line facts you actually read); `evidence_refs`; and `not_proven` (facts you could not establish — environment limits only, never design decisions left open).

Parallel design and `partition_plan` (§A2, walk-results-adopted-0707): when `partition_plan.width_decision.n` ≥ 2, the proposed sibling lanes run mutually blind (상호 열람 금지 — `sibling_independent: true`; a branch must not read sibling evidence), and the field spine quotes the landed return template exactly: `width_decision` carries `n` (hard ceiling 3), `rationale_signals`, `partition_count`, and `kappa_proxy` with `overlapping_write_pairs` and `shared_contract_files`; each entry of `branches` carries `branch_id`, `concern_key`, `objective`, `output_format`, `write_set` (`allowed`/`forbidden`, pairwise disjoint), `returns_field`, `sibling_independent`, and `casting` (`adapter`, `model`, `effort`, `timeout_seconds`); then `done_line`, `residual_owner`, `qa_plan` (`lenses`, `second_verdict_path`, `max_concurrent_xhigh` 기본 2, `stagger`), `env_plan` (`preflight_probe`, `provider_risk`), and `expansion` (`attach_to_step_ref`, `budget_mode` 'per-node' XOR 'aggregate', `budgets`). Draft-time teeth for these fields live in `support/operator/graph_draft.py` (`draft_rule_violations`).

Return: fill the `required_return_shape` from the return_template (`brick/templates/bricks/deep-design/return.yaml`): `design_summary`, `per_deliverable_plan`, `decision_ledger`, `hunk_sketches`, `mutation_designs`, `forbidden_drift`, `candidate_file_changes`, `reading_scope_map`, `invariants`, `partition_plan`, `observed_evidence`, `evidence_refs`, `not_proven`.

Do NOT return success / failure / approved / quality / movement_choice / route_target — sufficiency + movement are the Link gate's; quality/success are the human's.
