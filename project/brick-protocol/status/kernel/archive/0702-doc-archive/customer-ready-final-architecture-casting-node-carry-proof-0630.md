# Customer-Ready FINAL Architecture — Casting Node Carry Leaf Proof — 0630

Status: FORWARD / integrated candidate. Support evidence only; not source truth,
not success judgment, not quality judgment, and not Link Movement authority.

## Building and route observation

Building:

```text
final-casting-node-carry-extraction-0630a
```

Declared packet:

```text
project/brick-protocol/status/kernel/GOAL/final-casting-node-carry-extraction-0630a.json
```

Evidence root:

```text
/Users/smith/.brick/project/brick-protocol/buildings/final-casting-node-carry-extraction-0630a
```

Observed frontier:

```text
frontier_kind = complete
frontier_reason = declared closed boundary observed after paused frontier disposition
```

Important correction: the Building completed as `forward` because the graph
packet declared every edge as `movement: forward` and carried no route policy,
reroute budget, max-attempt budget, or replay plan. That is an operator graph
declaration mistake for this verification shape, not proof that the official
customer build route defaults to `forward`, and not a preset limitation. QA
blockers should surface as blocking evidence / transition concern evidence;
Link/COO then adopts `reroute` or `HOLD` under declared policy. In this run the
closure returned no transition concern and the declared Link rows were all
forward, so the support walker walked the road it was given.

## Integrated code candidate

Sandbox commit produced by the Building:

```text
0cfde8da2442c3d82d8d413fe7575ca25cb6777f
```

Integrated into main as:

```text
4ac4b9d BRICK building output: final-casting-node-carry-extraction-0630a
```

Changed files:

```text
M support/checkers/lib/case_runners.py
A support/checkers/lib/casting_node_carry_check.py
M support/checkers/module_registry.yaml
```

Delta:

```text
3 files changed, 183 insertions(+), 160 deletions(-)
```

The leaf moves the casting-node carry behavioral checker out of the
`case_runners.py` godmodule into a flat checker-lib sibling:

```text
support/checkers/lib/casting_node_carry_check.py
```

`case_runners.py` keeps a re-export import, so the public checker import surface
used by `check_profile.py` remains unchanged.

## REAL HOME verification

Verification was run in a disposable verification worktree with the sandbox diff
applied on top of current `main`:

```text
/Users/smith/.brick/worktrees/verify-casting-node-carry-0630-79559
```

Commands / results:

```bash
TMPDIR=/Users/smith/.brick/tmp/real-home-checks-1782778381 \
PYTHONPATH=support/import_identity:. \
python3 -m compileall -q \
  support/checkers/lib/case_runners.py \
  support/checkers/lib/casting_node_carry_check.py
# PASS

git diff --cached --check
# PASS

TMPDIR=/Users/smith/.brick/tmp/real-home-checks-1782778381 \
PYTHONPATH=support/import_identity:. \
python3 support/checkers/check_profile.py \
  --profile support/checkers/profiles/agent_axis_behavioral.yaml
# PASS: profile passed: agent-axis-behavioral
# Includes kernel_check=casting_node_carry PASS.

TMPDIR=/Users/smith/.brick/tmp/real-home-checks-all-1782778394 \
PYTHONPATH=support/import_identity:. \
python3 support/checkers/check_profile.py --all
# PASS: all OK
```

The full profile PASS is support evidence only. It does not prove source truth,
success judgment, quality judgment, Movement authority, provider behavior, or
complete future coverage.

## Claude read-only code QA lens

Claude Opus local read-only review was run against the staged verification
worktree diff with explicit no-edit constraints.

Result:

```text
VERDICT: FORWARD
BLOCKERS: none
```

Claude-observed support points:

```text
- moved functions were rehomed behavior-preservingly into casting_node_carry_check.py
- import closure remained intact
- case_runners.py re-export preserved public name compatibility
- module_registry row matched checker-lib sibling convention
- no Movement / target-selection / success / quality authority was introduced
```

Minor only:

```text
A carried-over docstring says the fixture is composed through the real
compose_building front door while it actually uses _graph_test_plan_from_linear;
this wording pre-existed the move and is not a blocker for the pure relocation.
```

## Three-axis attribution

Evidence first:

```text
Brick evidence: declared Building graph packet and work contract targeted a
checker-lib leaf extraction.
Agent evidence: work/QA/closure returned step-output facts under the Building
evidence root; QA/closure limits were support evidence, not authority.
Link evidence: declared graph Link rows were all `forward`; no route policy or
reroute budget was declared.
Support surface: checkers, Claude, git diff, and profile runs supplied evidence
only.
```

Rejected shortcut:

```text
Do not blame the preset or official route. The observed forward result came from
the declared graph Link rows and missing route policy/budget.
```

Chosen movement candidate:

```text
FORWARD for code integration of this leaf, because the verification gap that
QA/closure reported was closed by REAL HOME profile checks and read-only code QA.
```

Future graph-authoring correction:

```text
Important FINAL leaves should not be authored as decorative all-forward graphs
when QA may block. The desired shape is work -> fan(Codex execution QA, Claude
code review QA, Gemini axis QA) -> closure/route-decision, with QA blockers
surfacing concern evidence and Link/COO adopting reroute or HOLD under declared
policy.
```

## Not proven

```text
- Mutation-RED was not re-run in this turn for this leaf; the live
  casting_node_carry kernel check itself documents the mutation witness.
- Future provider behavior.
- Future Building correctness.
- Source truth / success judgment / quality judgment / Movement authority.
```
