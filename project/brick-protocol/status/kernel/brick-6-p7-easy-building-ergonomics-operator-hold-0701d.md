# BRICK 6 P7d Easy Building ergonomics - operator HOLD / not adopted - 2026-07-01

## Scope

- Phase: revised P7 — product route / P3 Easy Building surface.
- Slice: S6-F4 Easy Building declaration ergonomics.
- Building: `brick-6-p7-easy-building-ergonomics-0701d`.
- Declaration commits:
  - `d86f9de P7: declare Easy Building ergonomics graph`
  - `8ee849b P7: fix Easy Building graph fan-out refs`
- Follow-up operator/source commits during/after run:
  - `93658ec P7: hotfix multi-stage Building structure diagram rendering`
  - `1095bb7 P7: record fan barrier discipline in Building coordination skill`
- Evidence root: `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p7-easy-building-ergonomics-0701d`.

## Frontier observation

`observe_building_frontier` reports:

```text
frontier_kind = complete
frontier_reason = declared closed boundary observed after paused frontier disposition
agent_return_records = 12
link_records = 30
building_map_link_edges = 18
```

This is support frontier evidence only. It is not source truth, success judgment,
quality judgment, or Movement authority.

## Output commit

The Building produced sandbox output commit:

```text
a4581fbb3955e9808895faad1a06c2f94705c803
BRICK building output: brick-6-p7-easy-building-ergonomics-0701d
parent = 8ee849b
```

Changed files in that output commit:

```text
README.md
project/brick-protocol/status/kernel/GOAL/brick-6-p7-easy-building-ergonomics-0701d.json
project/brick-protocol/status/kernel/brick-6-p7-easy-building-ergonomics-docs-0701d.md
support/checkers/lib/kernel_checks.py
support/checkers/profiles/brick_cli_entrypoint.yaml
support/docs/references/architecture-map.md
support/docs/references/launch-guide.md
support/docs/references/quickstart.md
support/docs/references/setup.md
support/operator/cli.py
```

Operator disposition: **not adopted to main** in this checkpoint.

Reasons:

1. The output commit parent is `8ee849b`, while current main has later operator
   commits `93658ec` and `1095bb7`.
2. Closure returned a Link-facing candidate concern, not a clean closure claim.
3. The declared graph shape has a known final-QA modeling issue: final QA lanes
   were modeled as multiple fan-in targets from both lane QA nodes, not as a
   single barrier followed by one final-QA fan-out cohort.

## Graph shape issue observed

Declared graph shape in P7d:

```text
task-intake
  -> fan([design-codex, design-claude])
  -> design-synthesis
  -> fan([work-docs, work-checker])
  -> docs-lane-qa / checker-lane-qa

then:

docs-lane-qa    -> final-code-qa / final-axis-qa / final-evidence-qa
checker-lane-qa -> final-code-qa / final-axis-qa / final-evidence-qa

then:

final-code-qa / final-axis-qa / final-evidence-qa -> closure
```

This made the final QA stage act like three fan-in targets rather than one clear
parallel final-QA cohort. The better graph is:

```text
docs-lane-qa
checker-lane-qa
  -> lane-qa-fanin-confirm
      -> fan([final-code-qa, final-axis-qa, final-evidence-qa])
          -> closure
```

The rule was recorded in `agent/skills/building-coordination/SKILL.md` at
`1095bb7`: fan-in and fan-out must not be the same event; insert a barrier Brick
before launching a new fan-out cohort.

## QA / closure concerns

`docs-lane-qa` returned non-binding concern evidence:

```text
concern_kind = boundary_mismatch
concern_ref = transition-concern:brick-6-p7-easy-building-ergonomics-0701d-docs-lane-qa-boundary-mismatch
related_boundary_refs = [brick-6-p7-easy-building-ergonomics-0701d-work-docs]
```

Reason: lane attribution ambiguity — the docs lane output reported changes in
`support/operator/cli.py` and checker files, which belong more naturally to the
checker/CLI lane.

`closure` returned non-binding concern evidence:

```text
concern_kind = verification_gap
concern_ref = transition-concern:brick-6-p7-easy-building-ergonomics-0701d-closure-graph-proof-gap
not_proven:
  - fresh successful real brick build --graph execution through an externally supplied valid declared graph packet
  - full check_profile.py --all green
```

Closure did carry the final QA gaps instead of smoothing them into a false clean
PASS.

## Narrowly proven

- P7d ran through the official `brick build --graph` route and reached a recorded
  closed boundary / frontier complete state.
- The Building produced real step outputs for all 12 declared nodes.
- Initial design and work lanes did run with real fan-out behavior:
  - `work-docs` and `work-checker` both recorded at `2026-07-01T02:27:41Z`.
  - `checker-lane-qa` and `docs-lane-qa` recorded at `2026-07-01T02:32:54Z` / `02:32:55Z`.
- Final QA was not declared with the clean barrier -> fan-out shape; do not reuse
  this graph shape as-is.
- Focused evidence inside the run supports the product-route wording/checker-pin
  direction: ordinary route `brick build`, input modes `preset_task` and
  `graph_packet`, no public `--large` / `_p3_easy_large` / `--dev-lanes` /
  `lane_return` / new-engine path.

## Not proven

- P7d output commit correctness on current main.
- Full `check_profile.py --all` green after the P7d output.
- A fresh valid external `brick build --graph <packet>` proof through the actual
  materializer, independent of this Building's own launch.
- Customer comprehension of the natural-language big-work route.
- Fresh-machine install/run behavior.
- Provider reliability.
- P8 ship-safety hardening.
- P9 current-main dynamic/customer replay.
- Whole customer-ready closeout.

## Next Movement candidate

Do not adopt `a4581fb` directly as the P7d closure commit.

Recommended next declared Building:

```text
P7d2: Easy Building graph correction + verification-gap closure
```

Shape:

```text
task-intake
  -> fan([design-codex, design-claude])
  -> design-synthesis / plan-confirm
  -> fan([work-docs, work-checker])
  -> fan([docs-lane-qa, checker-lane-qa])
  -> lane-qa-fanin-confirm
  -> fan([final-code-qa, final-axis-qa, final-evidence-qa])
  -> closure
```

Required closure evidence for P7d2:

- lane attribution cleanly separated or explicitly synthesized at the barrier.
- fresh valid external `brick build --graph <packet>` proof, or an explicit
  operator decision to scope S6-F4 to route wording/checker pins only.
- current-main focused checks and `check_profile.py --all` either green or
  explicitly classified with exact unrelated evidence before any adoption.
- no whole P8/P9/customer-ready completion claim.

Do not push without Smith OK.
