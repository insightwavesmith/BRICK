---
name: protocol-boundary-watch
description: Use when a Brick Protocol task may blur Brick, Agent, Link, support, provider, or graph responsibilities.
---

Before choosing a repair surface, run the three-axis check:

```text
Evidence first:
Brick candidate:
Agent candidate:
Link candidate:
Support surface:
Rejected shortcut:
Chosen repair surface:
Verification before Movement:
```

Start from function, not from a file or tool name.

```text
Brick owns work contracts, Building Plans, comparison rules, required return shape, and source facts.
Agent owns performer resources, receipt, performance, and closed AgentFact(received_work, returned).
Link owns transfer, carry, Gate sufficiency facts, Movement, transition, reroute, and route_replay_plan handoff refs.
```

For current COO judgment, carry MOVEMENT-BINARY-0:

```text
forward = continue on the current declared road
reroute = move to any other declared Brick boundary
```

`replay` belongs inside `route_replay_plan`; `return` is superseded shorthand
for reroute; `hold` and `stop` are Building lifecycle states, not Link Movement.

Support mechanics may record, prepare, or project evidence. They do not become
Brick, Agent, Link, source truth, quality judgment, or Movement authority.

Graph is support projection for later three-axis improvement analysis. It may
show Brick attempts, Agent bindings, and Link edges, but it must not own meaning
or replace raw evidence and claim_trace facts.

Provider surfaces, MCP, toolkits, Codex-native skills, Claude-native files,
Gemini, hooks, adapters, and generated output are projection or support
surfaces unless a later admitted slice says otherwise. `agent/` remains the
Agent resource source; Codex/Claude files are generated projections; MCP is a
read-only call door. They must not store setup tokens, raw session ids,
credential bodies, or provider request bodies in repo evidence.
