---
name: evidence-shape-check
description: Use when checking that an artifact follows the declared structure AND when finding missing evidence, unresolved questions, remaining_delta, and not_proven items. Return observations only; do not judge quality or choose Movement.
---

# Evidence Shape Check

This skill folds two observation passes (structure-validator + gap-detector) into
one. Both are pure observation emitters: return what you see, never a verdict.

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

## Discipline

Do not approve quality, do not convert gaps into failure verdicts, and do not
choose Movement, route target, success, failure, or approval. Structure and gap
findings are observations the Link Gate and the human read; they are not
judgments this skill makes.
