---
schema: brick-block/v1
block_id: B4
title: Completeness Critique Tail
summary: A final read-only critique checks missing modalities, unverified claims, and claim-to-evidence mapping.
when:
  - Large research, audit, or evidence-first investigation needs a missing-coverage pass before closure.
  - Claims should be mapped back to evidence and unsupported claims called out.
anti_hint:
  - Do not use for a small single-file or single-question task with a short evidence chain.
dsl_snippet: "review(\"missing coverage: modalities, unverified claims, claim-to-evidence table\") -> closure"
axis_notes:
  brick: Brick declares the critique target and required evidence mapping.
  agent: Agent returns missing items and unsupported claims as observations.
  link: Link carries critique evidence to closure without judging quality.
  support: Support preserves the claim-to-evidence table as evidence only.
related_presets:
  - research-report
  - recon-fleet
  - postmortem
proof_limits:
  - block is documentation only, not executable, not a recommendation engine
  - absence findings remain support evidence, not proof of complete coverage
---

# B4 Completeness Critique Tail

Use this vocabulary just before closure when the work needs a last pass over
missing modalities and unsupported claims.

```text
review("missing coverage: modalities, unverified claims, claim-to-evidence table") -> closure
```

The block is a corpus entry for authoring. It is not an operator surface.
