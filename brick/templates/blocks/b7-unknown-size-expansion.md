---
schema: brick-block/v1
block_id: B7
title: Unknown Size Expansion
summary: Gated expansion pattern for work whose final shape is not yet known.
when:
  - The end shape is uncertain and expansion budgets must be declared before additional work exists.
  - The task needs a HOLD and later explicit disposition before live expansion.
anti_hint:
  - Do not use when the desired output shape is already known and a fixed graph can be declared.
dsl_snippet: "expansion_node_budgets declared -> HOLD + approval -> bounded expansion"
axis_notes:
  brick: Brick declares the unknown-size boundary and finite expansion budgets.
  agent: Agent may surface gaps but does not create live route targets.
  link: Link owns pause, disposition, and resumed movement over declared boundaries.
  support: Support records expansion evidence without inventing child work.
related_presets:
  - brick-protocol-post-d-cleanup
  - high-risk-change-inspected
proof_limits:
  - block is documentation only, not executable, not a recommendation engine
  - status gated; live use waits for T10 hardening green before this is more than a design pattern
---

# B7 Unknown Size Expansion

Status: gated. Live use waits for T10 hardening green; before that, this block
is only a design-pattern document.

```text
expansion_node_budgets declared -> HOLD + approval -> bounded expansion
```

The block is a corpus entry for authoring. It is not an operator surface.
