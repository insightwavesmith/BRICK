# Customer-Ready P3 W1 Sandbox Dispose And Marker Filter - 0627

Status: support evidence only.

This record is not source truth, success judgment, quality judgment, or Movement
authority.

## Phase

P3 - C6 One-Call Launch Close.

## Evidence Roots

```text
project/brick-protocol/buildings/c6-one-call-launch-0627-weekend-recast-6
project/brick-protocol/buildings/c6-one-call-launch-0627-weekend-recast-7
```

## Observed Problem

`recast-6` produced Building evidence but the customer CLI wrapper exited with:

```text
WorktreeSandboxError:
refusing to force-remove a non-engine worktree path:
/Users/smith/.brick/worktrees/c6-one-call-launch-0627-weekend-recast-6
```

The sandbox path was an engine-created active worktree, but the in-worktree
`.brick-engine-worktree` marker had been removed before disposal. The stale
reaper must remain marker-gated, but active disposal can also prove ownership
from the live `WorktreeSandbox` object plus `git worktree list --porcelain`.

`recast-7` then closed the wrapper without the cleanup error:

```text
frontier_kind: link_paused
worktree_disposed: true
customer_visible_frontier_state: not_ready
```

`recast-7` also showed that package path admission can false-red inside a W1
worktree when it sees the untracked `.brick-engine-worktree` marker. That marker
is support residue, not a source surface.

## Three-Axis Attribution

Brick:

```text
The declared P3 C6 work remains the customer launch proof. The work statement is
not source truth and did not close customer readiness.
```

Agent:

```text
Codex work, Codex code-attack-qa, Gemini axis-attack-qa, and Codex closure all
returned AgentFacts in recast-7.
```

Link:

```text
The final frontier stayed link_paused. Closure returned non-binding
transition_concern_evidence with concern_kind insufficient_input.
```

Support:

```text
The repaired surface is support/operator/worktree_sandbox.py active disposal and
support/checkers/check_package_path_admission.py residue filtering.
```

Rejected one-axis shortcut:

```text
This was not treated as a Gemini failure, Codex quality failure, or Link
Movement decision. The cleanup failure was support mechanics. The final P3 HOLD
remains a separate customer-proof frontier issue.
```

## Patch

```text
support/operator/worktree_sandbox.py
  Active disposal may remove the just-created sandbox when either the marker is
  present or the path is under the engine worktree root and still listed by git
  as a worktree for the same repo. Stale reaping remains marker-gated.

support/checkers/check_building_operator_driver0.py
  Adds W1 marker-loss FIRE coverage: a deterministic provider deletes the
  in-worktree marker, completion still commits, live tree remains untouched, and
  the active worktree is disposed.

support/checkers/check_package_path_admission.py
  Treats `.brick-engine-worktree` as support residue so sandbox-local profile
  runs do not false-red on the marker file.
```

## Verification

```text
PYTHONPATH=support/import_identity:. python3 -m support.checkers.check_building_operator_driver0
PYTHONPATH=support/import_identity:. python3 -m support.checkers.check_building_lifecycle_path_shape --target project/brick-protocol/buildings/c6-one-call-launch-0627-weekend-recast-7
PYTHONPATH=support/import_identity:. python3 -m support.checkers.check_building_map_graph --target project/brick-protocol/buildings/c6-one-call-launch-0627-weekend-recast-7/work/building-map.json
PYTHONPATH=support/import_identity:. python3 -m support.checkers.check_package_path_admission --fixture <temp fixture containing .brick-engine-worktree>
python3 -m compileall -q support/checkers/check_package_path_admission.py support/operator/worktree_sandbox.py support/checkers/check_building_operator_driver0.py
git diff --check -- support/checkers/check_package_path_admission.py support/operator/worktree_sandbox.py support/checkers/check_building_operator_driver0.py
```

Observed:

```text
all targeted checks passed
```

## Current Movement

```text
P3 remains HOLD.
```

Next admissible movement:

```text
REROUTE / rematerialize another P3 run from a committed base that contains the
W1 cleanup and marker-residue fixes. The next run should bound same-goal nested
launching so child Building evidence remains support evidence and does not
replace the parent P3 proof frontier.
```

## Not Proven

```text
customer-ready C6 closure
semantic correctness of Agent edits from recast-7
Gemini provider usage metering
full profile green on the dirty live checkout
fresh-machine proof
production runtime behavior
```
