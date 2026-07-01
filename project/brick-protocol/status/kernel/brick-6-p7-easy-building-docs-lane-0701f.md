# BRICK 6 P7d Easy Building docs lane - 2026-07-01

## Scope

- Phase: P7 product-route / Easy Building declaration ergonomics slice.
- Lane: docs/product work only.
- Write scope: `README.md`, `support/docs/references/*.md`, and
  `project/brick-protocol/status/kernel/**`.
- No CLI mode, checker code, engine, scheduler/queue/retry runtime, or route
  selection behavior was added in this lane.

## Observed Evidence

Docs now describe the bigger-work route as a declared road over the existing
public build surface:

```text
make X
  -> task intake
  -> design fan-out / review
  -> plan confirm
  -> parallel dev lanes
  -> lane QA
  -> final QA
  -> closure
  -> brick build --graph <declared-graph-packet.json>
```

The wording keeps two public input modes:

```text
preset_task  = brick build --task ... --preset ...
graph_packet = brick build --graph <packet.json>
```

It classifies `assemble()`, `run_building_intake`, `run_building_plan`,
`launch_assembled_building`, `goal-approve`, and full internal Building Plan
runner calls as helper or advanced/internal surfaces, not ordinary customer
routes.

## Narrowly Proven

- The docs lane did not add a new public CLI mode.
- The docs lane did not revive `--large`, `_p3_easy_large`, `--dev-lanes`, or
  `lane_return`.
- The docs lane states that support validates and walks declared Brick / Agent /
  Link rows; it does not choose route targets, invent Movement, judge success,
  or judge quality.
- The docs lane points invalid graph-packet operator wording at product-safe
  taxonomy (`graph_packet_invalid`) rather than raw traceback / raw exception
  wording.

## Not Proven

- This docs lane does not independently re-prove a fresh external `brick build
  --graph <packet>` dynamic-design pipeline end to end.
- Customer comprehension, provider reliability, semantic graph quality, source
  truth, success judgment, quality judgment, and Movement authority remain not
  proven by documentation or checker/profile green.

## Next Movement Candidate

Carry this docs/product evidence to the declared lane QA/final QA boundary for
P7d. Any further dynamic-design proof remains a later explicitly declared
slice, not this docs lane.
