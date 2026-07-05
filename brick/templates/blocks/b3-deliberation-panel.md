---
schema: brick-block/v1
block_id: B3
title: Deliberation Panel
summary: Multiple design perspectives produce comparison evidence; adoption remains human, COO, or declared Brick contract work.
when:
  - Design choices are broad, tradeoffs are real, and no single factual check can settle the direction.
  - A comparison table, counterarguments, and tradeoff record are useful evidence.
anti_hint:
  - Do not use for falsifiable fact extraction that one brain plus one counter-lens can check.
dsl_snippet: "fan(design x N perspectives) -> review(comparison evidence) -> adopted by human/COO or declared Brick contract"
axis_notes:
  brick: Brick declares the design question and comparison evidence shape.
  agent: Agent design lanes provide perspectives and tradeoffs without binding adoption.
  link: Link carries comparison evidence without converting it into Movement authority.
  support: Support records the panel evidence; it does not score alternatives.
related_presets:
  - design-contract-only
  - app-feature-inspected
  - governed-change-review
proof_limits:
  - block is documentation only, not executable, not a recommendation engine
  - comparison evidence is not quality, success, or adoption judgment
---

# B3 Deliberation Panel

Use this vocabulary when design direction needs competing perspectives and an
evidence record before a separate adoption decision.

```text
fan(design x N perspectives) -> review(comparison evidence) -> adopted by human/COO or declared Brick contract
```

The block is a corpus entry for authoring. It is not an operator surface.
