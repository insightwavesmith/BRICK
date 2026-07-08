# Route V2 ⑥d/⑥e Human Gate Approval — 0709

Status: support evidence only. This records Smith's human-gate decision for the
Route V2 post-R2 sequence. It does not implement Route V2, does not choose Link
Movement, does not judge success or quality, and does not make runtime/source
truth claims.

## 0. Decision

Smith approved the COO-recommended option:

```text
Approved option: Option B — ⑥d then ⑥e sequence
Approval text: "휴먼게이트 너의 의견대로한다."
Recorded interpretation:
  1. Open ⑥d route_materialization review first.
  2. Keep ⑥e walker integration HOLD until ⑥d evidence is green or ⑥d is
     explicitly deemed unnecessary.
  3. Do not implement walker integration immediately from this approval alone.
```

Source packet:

```text
project/brick-protocol/status/kernel/route-v2-human-gate-packet-0709.md
```

## 1. Approved next Building candidate

```text
building_candidate: route-v2-6d-route-materialization-review-0709
phase: ⑥d
purpose: review whether route_materialization view/provenance needs a narrow
  extension for Route V2 post-R2 before walker integration.
```

Candidate write scope after declared Building intake:

```text
- brick_protocol/support/operator/route_materialization.py
- brick_protocol/support/checkers/check_route_v2_views.py or a narrowly admitted
  existing checker if checker coverage is required
- brick_protocol/support/checkers/profiles/route_v2_sealed_materialization.yaml
- project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
- follow-up support evidence under project/brick-protocol/status/kernel/
```

## 2. Still held

```text
⑥e walker integration remains HOLD until ⑥d closes green or ⑥d is explicitly
recorded as unnecessary.

Still not approved by this packet:
- direct walker_kernel.py / walker_resume.py implementation now
- link/** changes
- agent/return_fact.py changes
- new route_scope.py
- new route_v2_engine.py
- new concern_kind
- verification_gap reroute eligibility
- support-chosen Movement or route target
- success/quality/movement_choice/route_target authority fields
```

## 3. Required proof for ⑥d

The ⑥d Building must preserve the constraints from the human-gate packet and
produce at least:

```text
- changed_files
- deleted_files or explicit none
- moved_files or explicit none
- source_facts
- allowed_scope / forbidden_scope evidence
- whether route_materialization.py changed or was deemed sufficient as-is
- negative probes for forbidden authority fields and forbidden new surfaces
- python3 -m compileall -q brick_protocol
- python3 brick_protocol/support/checkers/check_route_v2_views.py
- python3 brick_protocol/support/checkers/check_profile.py --profile route_v2_sealed_materialization
- clean detached worktree: python3 brick_protocol/support/checkers/check_profile.py --all
- git diff --check
- GOAL/status update with remaining_delta and next gate
```

## 4. Three-axis boundary

```text
Brick:
  ⑥d is a declared review/implementation Building over route materialization
  evidence and its proof obligations. It is not a generic cleanup or walker task.

Agent:
  Any performer returns closed AgentFact(received_work, returned). Agent does not
  author success/quality/Movement, and no provider/model/adapter identity becomes
  the decision authority.

Link:
  Link owns Movement and route replay facts. ⑥d may prepare evidence for later
  Link transition handling, but support code must not choose Movement or target.
```

## 5. Not proven

```text
- ⑥d has not yet been run.
- ⑥e has not yet been approved for implementation.
- route_materialization changes are not proven necessary.
- walker integration behavior is not proven.
- automatic repair/replay execution remains not approved.
```
