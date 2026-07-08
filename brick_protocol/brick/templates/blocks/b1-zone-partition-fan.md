---
schema: brick-block/v1
block_id: B1
title: Zone Partition Fan
summary: Read-only zone lanes fan out over declared repository or evidence zones, then converge.
when:
  - Large reading work where each lane can own about one thousand lines or one bounded evidence zone.
  - Zone boundaries are clear enough to declare in the contract before dispatch.
anti_hint:
  - Do not use when sibling lanes need to write the same file or the zone boundary is unclear.
dsl_snippet: "fan([read-only zone-reader x K]) -> convergence"
axis_notes:
  brick: Brick declares each read zone and the convergence work.
  agent: Agent lanes return observed evidence for their declared zone only.
  link: Link carries independent sibling evidence to the convergence boundary.
  support: Support records the declared fan shape and evidence; it does not pick zones.
related_presets:
  - recon-fleet
  - recon-fleet-light
  - triage-fanout-3
proof_limits:
  - block is documentation only, not executable, not a recommendation engine
  - zone count and zone boundaries remain caller or COO declarations
---

# B1 Zone Partition Fan

Use this vocabulary when a task is mostly reading and the partition can be
declared before work starts.

```text
fan([read-only zone-reader x K]) -> convergence
```

The block is a corpus entry for authoring. It is not an operator surface.
