# Evidence postmortem — 3-axis fault attribution, 0612 incidents

(템플릿: project/brick-protocol/status/kernel/evidence-postmortem-task-template-0612.md)

## Targets (building roots, READ-ONLY — never modify; copy to temp if needed)
- project/brick-protocol/buildings/f14-claim-trace-manifest-adapter-error-0612
  (incidents: design stall x2 60min-timeouts -> bounded statement walked 2min; F15 trace)
- project/brick-protocol/buildings/iap-dashboard-sink-passport-0612
  (incidents: closure return forbidden 'status' key x2; F14 inconsistency->reconciled history)
- project/brick-protocol/buildings/provider-ladder-fleet-presets-0612 (afternoon adapter-error hold, abandoned)
- project/brick-protocol/buildings/dashboard-productization-0612 (afternoon adapter-error hold)
- project/brick-protocol/buildings/dashboard-productization-0612b (RETRY of the same task erroring again — the retry pattern itself is evidence)
- project/brick-protocol/buildings/adapter-30-s1-park (adapter-error casualty mislabeled as park)
- CONTROL: project/brick-protocol/buildings/f13-frontier-declared-edge-fallback-0612
  (same preset, same day, clean walk — the baseline)
- f10-grounding-demand-record-unify-0612 (dashboard shows 멈춤 — establish WHY from its ledger)

## Evidence sources / Attribution method / Output shape / Hard constraints
EXACTLY as the template (read it first). Per incident: owning_axis(Brick|Agent|Link|support)
+ evidence_refs + repair_candidate + not_proven. Frequency patterns synthesized separately.
Operator notes (NOT ledger evidence — appendix only): fleet-preset design stalled 25/29min
twice on 2026-06-12 night with ZERO output (no rollout retained — adapter --ephemeral, F18);
small probes stayed fast; notify-v3 design also timed out. Late-night big-session provider
degradation is a candidate Agent-axis attribution the ledgers alone cannot prove.
