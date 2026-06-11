# Task Source Template

template_ref: brick_task_source_template
owner_axis: Brick
template_kind: task_source

## Objective

What should be finished?

## First-Line Contract

State the whole task in one controlling sentence:

```text
This task must [finish target], using [required sources], producing [exact
output shape], preserving [Brick / Agent / Link boundary], and must not
[known forbidden authority or verdict].
```

## Context / Why Now

What background, constraints, prior decisions, or evidence should the Building
designer read? Why is this task being opened now?

## Deep Intake Result

Record the extracted values from COO deep intake. These fields are the Building
instruction evidence, not automatic decisions:

```text
Trigger Event:
User Context:
Desired Information / Outcome:
Current Workaround:
Pain Points:
Blocked Decisions:
Primary Signals:
Status Vocabulary:
Required Actions:
Forbidden Actions:
```

## Required Sources

Which files, specs, support records, Building evidence roots, or current
context entries must be read before design or execution?

## Desired Output

What artifact, decision packet, code change, document, closure report, or
evidence root should exist at the end?

## Brick / Agent / Link Boundary

What does Brick own as the work contract?

What does Agent receive and return through `AgentFact(received_work, returned)`?

What may Link record as declared Movement / target / handoff after review?

## Read Scope / Write Scope

What may be read?

What may be written?

What must not be written?

## Constraints / Out of Scope

What must not change? Include write scope, provider limits, forbidden surfaces,
credential/session constraints, and relevant proof limits.

## Human / Review Gate

Human Gate alias: this section replaces the older Human Gate heading while
keeping the same review-boundary meaning.

What must Smith or another named reviewer inspect before or after execution?

What can be recorded in a deferred review queue while COO proceeds?

## Honest Report Contract

The Agent returned report should use observation language only:

```text
observed_evidence
made_changes
blocked_or_missing_evidence
open_questions
not_proven
remaining_delta
review_needed
transition_concern_evidence
```

`transition_concern_evidence` is non-binding Agent concern evidence only. It
is not Link Movement and must not include movement or route target choice.

The Agent returned report must not include:

```text
success
failure
approved
good_enough
quality score
route_target
movement_choice
```

## Done Criteria

What observable files, commands, evidence roots, or returned sections must be
present before closure?

## Risk

What is ambiguous, high impact, reversible only with care, or outside the
current proof target?

## Proof Limits

This template is Brick-owned input only. It is not source truth, success
judgment, quality judgment, Movement authority, provider configuration, or
automatic shape selection.
