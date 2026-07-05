---
schema: brick-block/v1
block_id: B6
title: Human Gate Close
summary: A declared human or COO gate closes high-impact changes before further movement.
when:
  - The work changes constitution, contracts, customer-facing control, credentials, or approval-sensitive policy.
  - A formal human or COO disposition is required before the next boundary.
anti_hint:
  - Do not use for read-only work or low-impact changes that can close through ordinary declared gates.
dsl_snippet: "gates=(\"human-review\",) -> canonical link-gate:human; gates=(\"coo-review\",) -> canonical link-gate:coo"
axis_notes:
  brick: Brick declares the work and why the gate is part of the contract.
  agent: Agent returns evidence; it does not approve the gate.
  link: Link owns gate sufficiency and canonical gate refs.
  support: Support records the alias and canonical gate evidence it is given.
related_presets:
  - brick-protocol-constitution-change
  - governed-change-review
  - high-risk-change-inspected
proof_limits:
  - block is documentation only, not executable, not a recommendation engine
  - human-review/coo-review aliases materialize as link-gate:human/link-gate:coo only where admitted elsewhere
---

# B6 Human Gate Close

Use this vocabulary when a declared human or COO gate is part of the contract.
The DSL concept tokens `human-review` and `coo-review` are aliases; the
canonical gate refs are `link-gate:human` and `link-gate:coo`.

```text
gates=("human-review",) -> canonical link-gate:human; gates=("coo-review",) -> canonical link-gate:coo
```

The block is a corpus entry for authoring. It is not an operator surface.
