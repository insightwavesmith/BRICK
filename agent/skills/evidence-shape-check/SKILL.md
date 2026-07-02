---
name: evidence-shape-check
description: Use when checking that an artifact follows the declared structure AND when finding missing evidence, unresolved questions, remaining_delta, and not_proven items. Also the home of the absorbed observation lenses — code-change evidence reading (code-analyzer), evidence-first QA (zero-script-qa), and design depth inspection (design-depth-check). Return observations only; do not judge quality or choose Movement.
---

# Evidence Shape Check

관찰 렌즈 통합 스킬 — 전부 순수 관찰 방출기다: 본 것을 반환하고, 판정은 절대 하지 않는다.
(구성: structure-validator + gap-detector 접합에 0702 리사이즈로 code-analyzer /
zero-script-qa / design-depth-check 3렌즈 흡수.)

## Structure pass — does the artifact follow its declared shape?

```text
required sections
required fields
forbidden fields
reference shape
row shape
```

Return matched / missing / mismatched observations.

## Gap pass — what evidence is missing or unresolved?

```text
blocked_or_missing_evidence
open_questions
not_proven
remaining_delta
review_needed
```

Return the gaps as observations.

## Code-change lens (구 code-analyzer)

Read code as evidence for an assigned Brick. Report:

```text
observed_evidence
changed_surface_notes
verification_refs
blocked_or_missing_evidence
not_proven
remaining_delta
```

Do not edit files.

## Evidence-first QA lens (구 zero-script-qa)

Start with existing evidence before asking for extra scripts or broad tool execution:

```text
changed files
declared verification refs
step outputs
raw refs
claim_trace refs
Building map refs
```

Request extra commands only when the Brick work contract needs them. Do not run mutation.

## Design depth lens (구 design-depth-check)

Inspect design evidence for:

```text
objective fit
required sources
user/workflow constraints
missing decisions
handoff clarity
review questions
```

Do not treat design preference as proof or approval.

## Discipline (전 렌즈 공통)

Do not approve quality, do not convert gaps into failure verdicts, and do not
choose Movement, route target, success, failure, or approval. Findings are
observations the Link Gate and the human read; they are not judgments this
skill makes.
