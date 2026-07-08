# Route V2 ⑥d Route Materialization Review — 0709

Status: support evidence only. This review does not change
`route_materialization.py`, does not implement walker integration, does not
choose Link Movement, does not judge success or quality, and does not make Route
V2 source truth.

## 0. Gate / approval context

Smith approved the COO-recommended human-gate sequence in:

```text
project/brick-protocol/status/kernel/route-v2-human-gate-approval-0709.md
```

Approved sequence:

```text
1. Review ⑥d route_materialization first.
2. Keep ⑥e walker integration HOLD until ⑥d evidence is green or ⑥d is
   explicitly deemed unnecessary.
3. Do not implement walker integration immediately from the approval alone.
```

This document is the ⑥d review disposition. It is a review/support evidence
record, not an implementation Building output with source changes.

## 1. Surfaces inspected

```text
brick_protocol/support/operator/route_materialization.py
brick_protocol/support/operator/route_v2_views.py
brick_protocol/support/checkers/check_route_v2_views.py
brick_protocol/link/route_policies/basic_qa_repair.yaml
brick_protocol/agent/return_fact.py
project/brick-protocol/status/kernel/route-v2-human-gate-packet-0709.md
project/brick-protocol/status/kernel/route-v2-human-gate-approval-0709.md
```

No source/code files were changed by this ⑥d review.

## 2. Current route_materialization behavior observed

A focused one-off probe used the live helper:

```text
brick_protocol.support.operator.route_materialization.materialize_transition_concern_disposition
brick_protocol.support.operator.route_v2_views.render_route_v2_view
```

### 2.1 implementation_gap materialization

Input:

```text
transition_concern_evidence.concern_kind = implementation_gap
route_policy = brick_protocol/link/route_policies/basic_qa_repair.yaml
declared_route_replay_plan.author_ref = coo:route-v2-6d-review
immediate_target_ref = brick-work
replay_segment_refs = [brick-work, brick-qa]
```

Observed:

```text
materialized = true
movement = reroute
target_ref = brick-work
source_transition_concern_ref = transition-concern:6d-review-implementation-gap
input mappings unchanged = true
```

The materialized view contains:

```text
link_row keys:
  axis
  movement
  next_brick_instance_ref
  route_replay_plan
  target_ref

link_decision_packet keys:
  evidence_view_of
  fact_class_admission
  link_decision_packet_ref
  materialized_link_row
  movement
  not_proven
  owner_axis
  proof_limits
  resource_kind
  route_path_ref
  route_policy_ref
  route_replay_plan
  route_request_binding
  source_request_ref
  source_transition_concern_ref
  target_ref
  transition_concern_binding
```

Interpretation:

```text
The existing helper already exposes provenance sufficient for Route V2's R2
read-only view: source concern ref, policy ref/path, route replay plan, evidence
view flag, proof limits, and materialized Link row.
```

### 2.2 verification_gap non-materialization

Input:

```text
transition_concern_evidence.concern_kind = verification_gap
route_policy = brick_protocol/link/route_policies/basic_qa_repair.yaml
declared_route_replay_plan supplied anyway
```

Observed:

```text
materialized = false
match_state = missing
materialization_state = disposition_required
materialization_reason = transition_concern_kind_not_listed
required_disposition_owner = caller-or-coo
```

Interpretation:

```text
verification_gap remains non-reroute even when a replay plan is supplied. This
matches the R0/R1/R2 rule: verification_gap is evidence for review/gate, not a
reroute address.
```

### 2.3 Route V2 view boundary

Input:

```text
implementation_gap + route_policy + declared_route_replay_plan
gate_state = paused
movement_candidate = reroute
delta_qa_fact = made_changes/changed_files/diff_refs/evidence_refs
```

Observed:

```text
route_v2_view has materialization_view = true
route_v2_view top-level movement key = absent
gate_state = paused
movement_candidate = reroute
```

Interpretation:

```text
Route V2 can show a materialization view without authoring a top-level Movement.
The gate/lifecycle field and movement_candidate remain separate.
```

## 3. Negative probes observed

The following authority or forbidden-author inputs were rejected:

```text
transition_concern.success_judgment
  -> ValueError: transition_concern contains forbidden key success_judgment

route_policy.support_chosen_movement
  -> ValueError: route_policy contains forbidden key support_chosen_movement

declared_route_replay_plan.provider_endpoint
  -> ValueError: declared_route_replay_plan contains forbidden key provider_endpoint

declared_route_replay_plan.author_ref = agent:qa
  -> ValueError: author_ref must not name support, Agent, provider, session,
     tool, hook, credential, or token refs
```

Interpretation:

```text
The existing materialization helper already rejects success/quality-style
authority keys, support-chosen Movement keys, provider endpoints, and Agent
/provider/session/tool/credential author refs.
```

## 4. Three-axis attribution

```text
Brick evidence:
  ⑥d asked whether the existing materialization view/provenance needed extension
  before ⑥e. The review work contract is satisfied by exact behavioral probes
  and no source change if current behavior is sufficient.

Agent evidence:
  The consumed Agent-facing evidence remains transition_concern_evidence with a
  sealed concern_kind. No AgentFact shape, Agent Object, provider/model/adapter,
  or singleton runtime_profile was changed.

Link evidence:
  Link owns Movement and route replay facts. The helper materializes a Link row
  only from a matching route policy plus caller/COO-declared route_replay_plan.
  verification_gap does not materialize. Movement remains a Link-row field, not
  Route V2 top-level authority.

Support surface:
  route_materialization.py is evidence plumbing. This review does not promote it
  to source truth, success/quality judgment, Movement authority, target selector,
  scheduler, queue, or runtime repair executor.
```

## 5. ⑥d disposition

```text
changed_files: none for route_materialization/support code
source_change_needed: no, not for the current R2 -> ⑥e design input
route_materialization.py disposition: sufficient as-is for R2 Route V2 view/provenance
⑥e gate: may proceed to walker integration design Building, but walker implementation
  remains constrained by the ⑥e acceptance evidence in the human-gate packet.
```

Rationale:

```text
The existing helper already provides:
- literal concern -> route policy scope matching
- caller/COO-declared route_replay_plan consumption
- link_row materialization
- link_decision_packet evidence view
- source_transition_concern_ref / transition_concern_binding provenance
- proof_limits and not_proven preservation
- verification_gap non-materialization
- forbidden authority key rejection
- forbidden author_ref prefix rejection
```

Therefore no ⑥d code patch is warranted before moving to ⑥e design.

## 6. Required next gate for ⑥e

⑥e may now move from generic HOLD to the next declared planning step:

```text
next_candidate: route-v2-6e-walker-integration-design-0709
```

But ⑥e implementation still requires a declared Building/worktree sandbox and
must prove at least:

```text
- walker consumes declared route/movement evidence only
- walker does not choose Movement or route target by itself
- verification_gap cannot reroute
- hold/paused/held_for_coo_review cannot become Movement
- success/quality/movement_choice/route_target authority fields cannot be emitted
  as walker decision fields
- delta-QA facts are preserved:
  made_changes, changed_files, diff_refs, evidence_refs
- python3 -m compileall -q brick_protocol
- focused route/walker checker profile(s)
- clean detached worktree: python3 brick_protocol/support/checkers/check_profile.py --all
- git diff --check
```

## 7. Not proven

```text
- ⑥e walker integration behavior is not proven.
- No walker code has been changed.
- Automatic repair/replay execution remains not approved.
- Future semantic correctness of Agent concerns remains not proven.
- Future route_materialization requirements may change if ⑥e design discovers a
  concrete missing provenance field; that would require a new ⑥d/⑥e repair loop.
```
