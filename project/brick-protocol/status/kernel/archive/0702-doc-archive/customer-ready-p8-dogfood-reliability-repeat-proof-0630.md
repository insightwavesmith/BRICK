# Customer-Ready P8 Dogfood Reliability Repeat Proof — 0630

Status: support evidence only. Not source truth, not success judgment, not quality judgment, and not Link Movement authority.

## Repeat result

A second P8-style dogfood run reached `frontier_kind=complete` through the official customer graph route.

```text
building_id = p8-dogfood-reliability-repeat-20260630T004057Z
base_sha = d22ff9ff1ef318bd9f5d41d41b09abfef626e01e
official route = uv run python3 -m brick_protocol.support.operator.cli build --json --non-interactive --graph <packet> --timeout 900
graph packet = /tmp/p8-dogfood-reliability-repeat-20260630T004057Z.json
evidence_root = /Users/smith/.brick/project/brick-protocol/buildings/p8-dogfood-reliability-repeat-20260630T004057Z
frontier_kind = complete
customer_visible_frontier_state = frontier_complete
sandbox commit = 379c3b1a2c1264252c17f7de497dfd79f927e9e3
artifact = support/docs/references/p8-dogfood-reliability-repeat-20260630T004057Z.md
```

This is a reliability-repeat sample after the first P8 proof `p8-dogfood-required-shape-20260629T182113Z`.
It strengthens provider/route repeat evidence but still does not prove future reliability in general.

## Declared shape

The run used the current P8 casting shape:

```text
Codex work
  -> Codex code-attack QA
  -> Gemini axis-attack QA
  -> Codex closure
  -> building-boundary:closed
```

Important proof limit: this repeat used an explicit lower-level graph JSON packet with `movement: forward`
inside edges. That is valid official `brick build --graph` evidence, but it is NOT proof that the higher-level
P3 no-link fluent surface has route/HOLD default policy fully hidden and automatic. The route-authoring lesson
from `final-casting-node-carry` still stands: QA blockers must surface concern evidence and Link/COO must adopt
reroute/HOLD under declared policy.

## Real artifact

Sandbox commit `379c3b1a2c1264252c17f7de497dfd79f927e9e3` contains exactly one file change:

```text
A support/docs/references/p8-dogfood-reliability-repeat-20260630T004057Z.md
```

Artifact content:

```text
This is a repeat dogfood sample for P8 reliability-repeat observation.
The official route is `brick build --graph`.
`frontier_kind=complete` is the relevant closure evidence.
Raw and spine evidence is checked by the operator.
Evidence is not source truth.
Repeated provider success is measured over runs, not assumed.
```

## Operator verification after the run

```text
Frontier event = evidence/spine/events/0044-Frontier.json
frontier_kind = complete
observed_counts.adapter_error_records = 0
observed_counts.agent_return_records = 4
observed_counts.building_map_link_edges = 5
raw/agent-return.jsonl rows = 4
raw/adapter-usage.jsonl codex rows = work, code-qa, closure
axis QA step-output adapter = adapter:gemini-local
raw/link.jsonl rows = 9, forward movements to code QA, axis QA, closure, and boundary
spine event count = 44
spine hash chain = OK
forbidden top-level return keys from checked set = []
```

Checked forbidden key set:

```text
success, failure, approved, quality, movement_choice, route_target, status, verdict, score, result
```

## Narrowly proven

```text
- A second official-route P8-shaped graph ran to `frontier_kind=complete`.
- The run included Codex work, Codex code QA, Gemini axis QA, and Codex closure.
- The produced artifact is real, bounded, and operator-readable in the sandbox commit.
- Raw records and spine records exist; spine hash chain passed operator verification.
- No checked forbidden top-level Agent return keys appeared in step-output returned payloads.
```

## Not proven / caveats

```text
- Future provider reliability remains not_proven; this is one repeat sample, not a statistical reliability campaign.
- The sandbox artifact is not merged into `main`; it remains evidence via sandbox commit `379c3b1`.
- This run does not prove customer comprehension, release export parity, or final release pruning.
- This run does not prove P3 high-level fluent route/HOLD defaults; it used explicit lower-level graph edges.
- Source truth, success judgment, quality judgment, Movement authority, and future Building correctness remain not_proven by support evidence.
```

## Three-axis attribution

```text
Brick evidence: declared graph packet and work/QA/closure Brick rows for one real documentation artifact.
Agent evidence: four Agent returns; Codex for work/code QA/closure and Gemini for axis QA.
Link evidence: forward Movement rows and final Frontier event with `frontier_kind=complete`.
Support evidence: CLI JSON, sandbox commit, raw records, spine, and this proof record. Support does not judge success, quality, or Movement.
```

## Next target candidates

```text
1. Customer release pruning expansion: keep customer-facing install/onboard/build/verify/docs/examples/templates/skills; exclude/archive stale internal evidence/status/cruft.
2. Continue FINAL architecture cleanup under conservation-ledger + mutation-RED + net-negative LOC.
3. If Smith wants stronger reliability, define a bounded N-run provider reliability campaign separately; do not overclaim from two successful P8 samples.
```
