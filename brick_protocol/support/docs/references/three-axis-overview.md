# Three-axis overview

Brick Protocol has three axes:

```text
Brick = work
Agent = performer
Link = transfer / carry / movement
```

Everything else is support, evidence, projection, or local project material. The three axes are the meaning model; support code only helps record and verify what the axes already declared.

## Brick: the work

A Brick says what work is being asked. In a Building step, the Brick row carries the `work_statement` and the `required_return_shape`. The required return shape is a comma-separated list of fields the Agent return is expected to expose, such as:

```text
observed_evidence, not_proven
```

Brick owns the work contract. It does not name the provider, choose a route, or judge whether the returned work is good.

## Agent: the performer

An Agent says who receives the work. In a Building step, the Agent row names an Agent Object, for example:

```yaml
axis: Agent
agent_object_ref: agent-object:coo
```

The Agent Object is provider-neutral. It can reference prompts, skills, hooks, tool policies, disciplines, callable performers, and adapter refs, but those refs are contract data, not provider credentials and not source truth. When the step runs, Agent records a closed AgentFact shape:

```text
received_work
returned
```

Agent does not classify its own return as success, failure, done, approved, or quality.

## Link: transfer, carry, and movement

Link says how public facts move from one Brick boundary to the next. Link owns transfer facts, carry facts, gate sufficiency facts, Movement facts, transition facts, and route policy meaning.

Active Link Movement literals are:

```text
forward
reroute
```

A GateFact records sufficiency against public facts, such as whether required returned fields were present. Gate sufficiency does not itself choose the next target. A declared Link row or declared policy may carry the Building forward, reroute to another declared Brick boundary, or leave a hold/wait frontier for caller or COO disposition. `hold` is a lifecycle/frontier state, not an active Movement literal.

## One-step flow

```text
Declared Building step

  Brick row
  work_statement + required_return_shape
        |
        v
  Agent row
  agent_object_ref receives the Brick work
        |
        v
  AgentFact
  received_work + returned
        |
        v
  Link row
  gate sufficiency + transfer/carry + movement + target
        |
        v
  Next declared Brick boundary or closed Building boundary
```

Support may walk this declared flow and record evidence. It must not invent the Brick work, replace the Agent performer, choose Movement, choose a target, or judge success or quality.

## What is not an axis

`brick_protocol/support/` is not an axis. It contains runner, adapter, recording, projection, and checker mechanics. Those mechanics can validate shape, connect an admitted adapter, write evidence, and render projections, but they do not own Brick / Agent / Link meaning.

Checkers are not axes. A checker can report whether a surface matches an admitted rule. Checker green is support evidence, not source truth, not success, not quality, and not Movement authority.

`project/` is not an axis. It is the repository-local destination for status and Building evidence. Files under `project/brick-protocol/buildings/` record what was observed during a run; they do not become the protocol owner.

## Project vessel (프로젝트 그릇)

A project is the vessel buildings accumulate in. It is not a fourth axis: it owns no work meaning, no performer meaning, and no movement meaning. It declares direction and collects evidence.

```text
project/<id>/
  README.md      human charter (purpose, direction, done-means, out-of-scope, managers)
  project.json   machine declaration (direction facts extracted from the charter)
  buildings/     Building evidence accumulates here
```

`README.md` is the charter humans and agents read first. `project.json` is its machine shadow: a closed set of direction facts (`project_ref`, `direction`, `done_means`, `managers`, ...). Judgment keys such as success or quality are rejected by name.

Vessels are created by the creation verb (`brick_protocol/support/operator/project_creation.py`, surfaced as the `project-creation` skill). A hand-assembled vessel missing the charter or the declaration is checker-RED.

A building's vessel membership is its path. The building packet gains no project field; the read side reads the vessel's `project.json` to label what the path already says.

```text
task (+ project_ref)
      |
      v
intake (fail-closed: the referenced vessel must exist and load)
      |
      v
declared Building plan
      |
      v
engine walk
      |
      v
evidence under project/<id>/buildings/<building_id>/
      |
      v
ledger / dashboard per vessel + machine PROGRESS.md
```

## Truth vs quality

Support records facts and proof limits. A support record can say what was declared, what returned, which fields were missing, and where evidence landed. It does not decide whether the work is good. Quality judgment is a separate human layer.
