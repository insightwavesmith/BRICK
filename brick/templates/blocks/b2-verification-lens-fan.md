---
schema: brick-block/v1
block_id: B2
title: Verification Lens Fan
summary: Parallel read-only attack lenses check code, axis boundaries, and evidence integrity before closure.
when:
  - The task touches contracts, policy, security, source mutation, or low-trust evidence.
  - More than one verification modality should inspect the same produced work.
anti_hint:
  - Do not use for high-trust read-only work where zero or one review lens is enough.
dsl_snippet: "fan(code-attack-qa, axis-attack-qa, evidence-integrity) -> closure"
axis_notes:
  brick: Brick declares each verification lens as work with a narrow return shape.
  agent: Agent reviewers return observations and concerns, not approval or quality verdicts.
  link: Link carries lens evidence to the declared closure or gate boundary.
  support: Support records lens returns; it does not judge which lens won.
related_presets:
  - design-build-parallel
  - governed-change-review
  - high-risk-change-inspected
proof_limits:
  - block is documentation only, not executable, not a recommendation engine
  - review evidence is not success, quality, or approval judgment
---

# B2 Verification Lens Fan

Use this vocabulary when the contract needs several independent read-only
verification lenses before closure.

```text
fan(code-attack-qa, axis-attack-qa, evidence-integrity) -> closure
```

The block is a corpus entry for authoring. It is not an operator surface.
