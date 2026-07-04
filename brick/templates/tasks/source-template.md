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

## 기계 검사 항목 (프리플라이트 린트)

작성자는 발사 전 독립 프리플라이트 린트가 확인할 수 있도록 아래 항목을 명시한다:

- L1: `work` / `development` 노드의 `work_statement`에는 `Done`, `종료선`, `완료선`, 또는 `DONE Criteria` 같은 종료선 마커가 있어야 한다.
- L2: `proof_obligations` / `Proof required`는 대상 Brick kind의 `capability_class`와 모순되면 안 된다. read 렌즈에는 source mutation, `git commit`, `git push`, 전체 `--all` 재실행 같은 proof를 배정하지 않는다.
- L3: `work_statement`는 `reason_refs`를 `file:line` 형식으로 유도하거나 `related_boundary_refs`를 구형 `brick:` / `brick-instance:` / `brick-boundary:` 형식으로 유도하지 않는다.
- L4: `## Deliverables` 아래에 `D1:` 같은 번호형 deliverable을 두고, deliverable에 적은 literal repo path가 선언된 `write_scope.allowed_paths`와 맞아야 한다.

## Proof Limits

This template is Brick-owned input only. It is not source truth, success
judgment, quality judgment, Movement authority, provider configuration, or
automatic shape selection.
