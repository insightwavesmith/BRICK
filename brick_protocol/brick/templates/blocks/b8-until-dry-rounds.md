---
schema: brick-block/v1
block_id: B8
title: Until Dry Rounds
summary: Human-authored repeated exploration rounds continue until the declared no-new-findings line is met.
when:
  - Unknown-size exploration, bug hunting, audit sweeps, or exhaustive search needs repeated rounds.
  - Each new round can be authored by COO using prior evidence as source facts.
anti_hint:
  - Do not use for production work with a known output; declare the finished graph instead.
dsl_snippet: "round N evidence -> COO authors round N+1; stop line: two consecutive rounds with zero new findings"
axis_notes:
  brick: Brick declares each round as its own work contract.
  agent: Agent reports findings for the current round only.
  link: Link carries prior-round evidence into the next declared round.
  support: Support walks each declared round; no engine loop is opened.
related_presets:
  - postmortem-fleet
  - review-fleet
  - recon-fleet
proof_limits:
  - block is documentation only, not executable, not a recommendation engine
  - no engine loop; each round is authored by COO from previous evidence
---

# B8 Until Dry Rounds

Use this vocabulary for exploration that repeats until the contract line is met.
Engine loops are prohibited; COO authors each round, and prior-round evidence
becomes the next round source facts.

```text
round N evidence -> COO authors round N+1
stop line: two consecutive rounds with zero new findings
```

The block is a corpus entry for authoring. It is not an operator surface.
