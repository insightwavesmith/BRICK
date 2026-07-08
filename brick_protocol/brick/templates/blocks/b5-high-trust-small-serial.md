---
schema: brick-block/v1
block_id: B5
title: High Trust Small Serial
summary: A compact design-to-work-to-closure chain for high-trust, bounded work.
when:
  - The task is small, high-trust, and read-only or a single-domain low-risk write.
  - The result can close without a separate human explanation of risk or tradeoffs.
anti_hint:
  - Do not use when writing contracts, constitutions, customer surfaces, security paths, many domains, unknown-size work, or high-cost failures.
dsl_snippet: "design -> work -> closure, gates=()"
axis_notes:
  brick: Brick declares the small serial work and any bounded write scope.
  agent: Agent performs the compact lane and reports factual evidence only.
  link: Link follows declared forward or reroute edges only.
  support: Support walks the declared serial chain without adding gates.
related_presets:
  - fast-fix
  - one-brick-do
  - quick-check
proof_limits:
  - block is documentation only, not executable, not a recommendation engine
  - high trust is caller or COO context, not support proof
---

# B5 High Trust Small Serial

Use this vocabulary when the task is bounded enough that a compact serial chain
fits the risk.

```text
design -> work -> closure, gates=()
```

The block is a corpus entry for authoring. It is not an operator surface.
