# REPORTER-NOTIFICATION-PROJECTION-0 Support Record

Date: 2026-05-31

Status: P5 reapplication slice admitting the first support-only local status inbox projection. This follows the P8 candidate plan and the current
AXIS-VOCAB-FIRST cleanup; it does not admit Slack, webhook, dashboard server,
thread wake, scheduler, queue, retry, provider runtime, database, source truth,
success judgment, quality judgment, Movement authority, route input, or target
selection.

This record is support evidence only. It does not make the reporter packet,
local inbox, checker profile, model output, or this status record source truth,
success judgment, quality judgment, Movement authority, target selection, route
input, or delivery reliability proof.

Do not describe this reporter packet as source truth.

## Six Questions

### 1. Brick

The reapplication work is support projection over existing Building / portfolio
evidence. It does not add a Brick fact class, new Building Plan family, or new
work-composition authority.

### 2. Agent

No Agent Object shape changes are opened by the reporter. AgentFact remains
closed to `received_work` and `returned`. Report packets are not AgentFacts.

### 3. Link

Reporter packets may cite observed Link/frontier evidence but must not create
GateFact, write MovementFact, adopt a transition concern, choose a target, or
resume a route.

### 4. Support

Admitted support surfaces in this slice:

```text
support/operator/reporter.py
support/operator/report_sinks.py
project/brick-protocol/status/inbox/
support/checkers/profiles/reporter_notification_projection.yaml
```

`support/operator/reporter.py` reads evidence roots, renders report packets, and
coordinates one-shot sink fan-out. `support/operator/report_sinks.py` admits
only `report-sink:local-inbox` and writes projection JSON under the local status
inbox.

Closed support surfaces:

```text
Slack delivery
webhook delivery
thread wake delivery
live dashboard runtime
scheduler / queue / retry runtime
database
provider-native config
driver.py route input behavior
```

### 5. Evidence

Created local inbox packet:

```text
project/brick-protocol/status/inbox/run-surface-authority-boundary-codex-multistep-0-0529-building-frontier.json
```

The packet observes existing evidence root:

```text
project/brick-protocol/buildings/run-surface-authority-boundary-codex-multistep-0-0529
```

The preserved dirty worktree evidence for
`reporter-notification-projection-0-0531` was read as support evidence only and
was not blindly copied into this checkout.

### 6. Admission

The checker/profile surface for this slice is:

```text
support/checkers/profiles/reporter_notification_projection.yaml
```

The profile pins:

```text
report packet required fields
source_truth: false
local inbox sink ref only
reporter validator and negative probe execution
reporter/sink absence of runner, driver, AgentFact, GateFact, MovementFact, Slack, webhook, server, and thread/queue imports
driver.py not reading status/inbox or reporter sink symbols
```

The reporter slice is wired into package-path admission, core profile allowlist,
the superseded P8 candidate profile, and a focused reporter profile kernel:

```text
support/checkers/check_profile.py::run_reporter_notification_projection
support/checkers/check_package_path_admission.py
support/checkers/profiles/core.yaml
support/checkers/profiles/post_d_surface_recompile_p8.yaml
```

This wiring is support checker evidence only. It does not make the reporter
packet source truth, success judgment, quality judgment, Movement authority, or
route input.

## Negative Probes

`reporter_negative_probe_observations()` rejects these invalid report packets:

```text
bad_source_truth_true
bad_movement_choice_field
bad_target_choice_field
bad_success_field
bad_complete_field
bad_complete_state
bad_driver_input_field
```

The reporter profile kernel executes reporter negative probes, a valid local
inbox write, forbidden-field sink rejection, and unadmitted-sink rejection. It
does not merely assert that the probe function text exists.

## P5 Frontier Repairs

The preserved follow-up also exposed support/runner blind spots carried into
this P5 reapplication:

```text
1. Invalid transition_concern_evidence must pause with
   invalid_transition_concern_evidence instead of becoming an adopted Movement
   or crashing late step-output recording.
2. Dynamic adapter interruption before AgentFact exists must write the same
   agent_incomplete frontier evidence as the linear walker.
3. Resume disposition evidence must not emit dangling observation refs.
4. Flattened transition_lifecycle_reason_refs are declared lifecycle reference
   fields for checker purposes.
```

All four are support/runner/checker repairs. They do not make support source
truth, success judgment, quality judgment, Movement authority, or route target
selector.

## Proof Limits

```text
support evidence only
local inbox projection only
not source truth
not success judgment
not quality judgment
not Movement authority
not route input
not delivery reliability proof
not stale-read race proof
not external notification behavior
```
