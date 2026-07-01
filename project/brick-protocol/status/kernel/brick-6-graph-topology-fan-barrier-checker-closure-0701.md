# Global Operating Rule 8 closure evidence — graph-topology fan-barrier checker (0701)

Status: support evidence for Global Operating Rule 8 (goal doc commit
`e571947`). Not source truth, success judgment, quality judgment, or
Movement authority.

## Attempt history

| Attempt | Result | Disposition |
|---|---|---|
| 0701a | `frontier_kind=complete` in-sandbox, but independent detached-worktree `check_profile.py --all` found a real `pin_estate_integrity` rejection: a decorative `path_exists`-only pin on a history-doc fixture file, added to `building_skill_preset_builder_composition.yaml` | not adopted |
| 0701b | Declared as a "small correction" to 0701a, but COO (Claude) had never actually adopted 0701a's sandbox output onto main — only its graph declaration was committed. 0701b's own work/QA/closure honestly discovered the target file didn't exist and returned `implementation_gap` twice, reroute budget exhausted, `link_paused` | not adopted (COO process error, not a Building defect) |
| **0701c** | Full redo from clean main, task_statement explicitly named the 0701a mistake to avoid it. `frontier_kind=complete`, single attempt on every node, zero transition concerns | **adopted** (this document) |

## 0701c observed evidence

- Declaration commit: `d5f68e6`.
- Sandbox output commit: `5ab4c7d737237eb26702c8235367be62b94178bf`.
- Adopted to main as: `2405a9d`.
- Changed files: `support/checkers/check_profile.py`,
  `support/checkers/lib/graph_topology_fan_barrier.py` (new),
  `support/checkers/lib/kernel_checks.py`,
  `support/checkers/module_registry.yaml`,
  `support/checkers/profiles/core.yaml`,
  `support/checkers/profiles/graph_topology_fan_barrier.yaml` (new).
- Unlike 0701a, this attempt used a dedicated new profile
  (`graph_topology_fan_barrier.yaml`) rather than adding a pin to an
  unrelated existing profile, and did not reference fixture files via a
  bare `path_exists` rule — the fixtures are consumed directly by the
  checker module's own Python source.

## Independent verification performed before adoption (Claude, detached worktree)

```text
py_compile (check_profile.py, graph_topology_fan_barrier.py, kernel_checks.py): PASS
check_profile.py --profile graph_topology_fan_barrier.yaml: PASS
  "negative no-barrier fixture RED-fired and positive explicit-barrier
   fixture was accepted"
git diff --check: PASS
check_profile.py --all: EXIT=0, 30/30 profiles passed to completion,
  including pin_estate_integrity ("0 history-doc pin block(s)" -- confirms
  the 0701a mistake was not repeated)
Re-verified again after cherry-pick onto current main: py_compile PASS,
  focused profile PASS, git diff --check PASS
```

## Narrowly proven

- A graph_packet whose `fan_in` group's target node is also the direct
  source of an immediately-following `fan_out` group with no intervening
  barrier node is now rejected by `graph_topology_fan_barrier`, using the
  actual P7d (negative) and P7d2/P7d3 (positive) committed fixture graphs
  as real fixture material.
- The checker is registered in `check_profile.py` / `module_registry.yaml`
  / `core.yaml` per existing conventions.
- `pin_estate_integrity` accepts the new profile with zero decorative-pin
  violations.

## Not proven

- **Live admission-time blocking is not proven.** This checker is a
  `check_profile.py --all` / focused-profile detector. It is NOT wired
  into the actual `brick build --graph` admission path
  (`support/operator/composition_compose.py` / `driver.py` /
  `plan_validation.py`) -- a malformed graph packet can still be fired
  through the real CLI and only gets caught if the COO runs the checker
  sweep first (a discipline-dependent habit, not an automatic gate). This
  matches the not_proven items 0701a's own closure already recorded
  ("Live brick build --graph admission rejection is not proven";
  "Integration with plan_graph.py / composition_graph_validate.py is not
  proven") and remains open. True admission-time enforcement is a
  separate, larger follow-on (would require hooking the graph-topology
  check into the materializer before `walker_kernel.py` ever starts
  walking), not scoped into this closure.
- Complete malformed-graph-topology coverage beyond the specific
  fan-in-immediately-fan-out shape.
- P8/P9 readiness, provider reliability, customer comprehension.
- Checker/profile green remains support evidence only.

## Next Movement candidate

Global Operating Rule 8's *detector* half is closed. The *admission-gate*
half (reject before a real Building runs, not just detect via a separate
sweep) remains open and should be folded into task #8
(`brick-6-graph-route-missing-default-write-scope-finding-0701.md`) scope,
since both live in the same materialization stage
(`composition_compose.py` / `plan_rendering.py`, before `walker_kernel.py`)
and are natural to fix together. Proceed to tasks #6/#7/#8 (engine-level
fixes) before P8.
