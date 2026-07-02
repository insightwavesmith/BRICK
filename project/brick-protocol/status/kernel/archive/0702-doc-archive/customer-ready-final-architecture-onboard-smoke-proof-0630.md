# Customer-Ready FINAL Architecture — onboard_smoke leaf extraction proof — 0630

Status: FORWARD candidate / support evidence only. Not source truth, not success
judgment, not quality judgment, and not Link Movement authority.

## What moved

Fourth `kernel_checks.py` leaf. The onboarding smoke checker cluster moved
VERBATIM into a new flat checker-lib sibling:

```text
support/checkers/lib/onboard_smoke_check.py   (new, 215 lines)
```

Moved symbols:

```text
_ONBOARD_SMOKE_REQUIRED_KEYS
run_onboard_smoke
_onboard_smoke_assert_shape
```

`kernel_checks.py` keeps a re-export block so `check_profile.py` import and
`KERNEL_DISPATCH['onboard_smoke']` stay unchanged.

## Building evidence

```text
building_id = g3-onboard-smoke-leaf-0630b
frontier_kind = complete
sandbox commit = aa8dbccc204e5a1b8705ce36913193f9f219df0b
route = main-agent drawn fire(graph) over work -> fan(code-attack-qa, axis-attack-qa) -> closure
```

Earlier failed attempts are intentionally not integrated:

```text
g3-onboard-smoke-leaf-0630 attempt 1 = link_paused (missing typing.Any in generated sibling)
g3-onboard-smoke-leaf-0630 attempt 2 = agent_incomplete (process/work no-edit state)
g3-onboard-smoke-leaf-0630b = complete and integrated
```

## Conservation result

```text
kernel_checks.py: 11017 -> 10814 LOC (net -203)
onboard_smoke_check.py: new flat sibling, byte-identical bodies
cumulative kernel_checks.py decomposition: 11452 -> 10814 (net -638 across 4 leaves)
```

## COO independent verification

```text
byte-identical moved body vs pre-move kernel_checks span 3917-4122 = True
compileall changed modules = PASS
re-export identity: kernel_checks.run_onboard_smoke IS onboard_smoke_check.run_onboard_smoke = True
dispatch identity: KERNEL_DISPATCH['onboard_smoke'] IS onboard_smoke_check.run_onboard_smoke = True
mutation-RED: malformed onboard_smoke result -> ProfileError fired
focused profile building_operator_driver0 = rc=0, includes onboard_smoke PASS
REAL HOME check_profile.py --all = 28 profile passed, 0 failure markers
```

## Three-axis attribution

```text
Brick evidence: declared G3 leaf-extraction work and checker boundary shrink.
Agent evidence: real provider Building produced the work; earlier failed attempts remain support evidence only.
Link evidence: only the complete Building output is integrated; paused/incomplete attempts were not forwarded into main.
Support surface: checker-lib module + module_registry row; support records facts only.
```

## Not proven / caveats

```text
- This is one leaf; kernel_checks.py (10814) remains a large godmodule.
- G3 STOP CONDITION is still undeclared.
- Future provider behavior / future Building correctness / source truth / success / quality / Movement authority remain not_proven.
```

## Next Movement candidate

Forward this leaf. Then declare a G3 STOP CONDITION before continuing more leaf
work, or move to G2 provider-backed fresh export proof if Smith prioritizes
customer-release evidence.
