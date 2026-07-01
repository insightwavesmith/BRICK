---
name: evidence-verification
description: Use when verifying Brick Protocol work through local commands, fixtures, and support evidence records.
---

Verify as support evidence only.

Separate:

```text
observed evidence
narrowly proven
not proven
next Movement candidate
```

Inspect the evidence layers by function:

```text
Brick evidence = work_statement, comparison_rule, required_return_shape, source_facts, Building Plan step shape
Agent evidence = Agent Object refs, received_work, returned, closed AgentFact shape
Link evidence = declared Movement, target, transfer/carry/gate/transition refs, reroute or replay handoff refs
Graph projection = Brick execution instances, Agent bindings, Link edges, proof_limits, not_proven
Raw / claim_trace = the evidence plane used to resolve references and support later analysis
```

## Token-Cost Discipline

Use bounded evidence extraction by default:

```text
- Prefer plan/frontier/result fields, manifests, specific step-output refs, and exact raw row keys.
- Avoid broad `cat raw/*.jsonl`, `grep -R raw capture`, or full evidence-folder dumps.
- For check_profile.py --all, redirect output to /tmp and report only rc, passed count, failure-marker count, and tail -2 unless debugging a concrete failure.
- Use wc/tail/jq/python field extraction before reading raw bodies.
- Delegate broad scans to a single diagnostic Building when useful; assign a Codex lane if appropriate, but do not name non-existent model tiers such as Codex Ultra.
```

Run the relevant checker set and report concrete command outcomes. A checker
result, model review, graph import, or local CLI smoke is support evidence only;
it is not source truth, not success judgment, not quality judgment, and not
Movement authority.

When verification finds a repairable issue, surface the candidate Brick
boundary and Link transition for COO/Link review, along with the evidence refs
that must be carried forward. Carry MOVEMENT-BINARY-0 as the current COO
judgment language:

```text
forward = continue on the current declared road
reroute = move to any other declared Brick boundary
```

`return` is superseded shorthand, `replay` is part of reroute, and `hold` /
`stop` are Building lifecycle states. Do not patch directly before the Building
has collected the declared verification lanes.
