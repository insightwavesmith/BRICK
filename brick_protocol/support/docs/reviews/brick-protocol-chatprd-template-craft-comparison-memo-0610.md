# Brick Protocol ChatPRD Template Craft Comparison Memo

Date: 2026-06-10

Status: Comparison memo support record, support evidence only. This document does not create or modify Agent prompts, skills, checkers, contracts, fields, runtime/storage/wiki, source truth, success judgment, quality judgment, or Movement authority. No repository code or Agent resource was changed by this memo.

## 1. Physical Surface Admission Rows

| Field | Required value |
| --- | --- |
| Physical surface | `brick_protocol/support/docs/reviews/brick-protocol-chatprd-template-craft-comparison-memo-0610.md` |
| Type | Markdown comparison memo: external product-tool template craft (ChatPRD) versus current Brick Agent prompt/skill surface. |
| BAL owner | Support residue with Brick comparison-memo work, Agent returned read evidence, and Link support-only disposition attribution. |
| Module | none as axis module; comparison memo support only. |
| Contract | Record observed differences between ChatPRD templates and Brick prompts/skills, list already-covered items, list candidate-only items, and record a hold recommendation without becoming source truth, success judgment, quality judgment, or Movement authority. |
| Derives from | Brick `brick_protocol/agent/prompts/{dev,pm-lead,cto-lead,design-lead}.md`, `brick_protocol/agent/skills/{software-architecture,scoped-implementation,code-analyzer,gap-detector,design-depth-check}/SKILL.md`, and an external read of the ChatPRD in-app template bodies. |
| Input | Read evidence from Brick Agent prompt/skill surface and ChatPRD template bodies. |
| Output | Comparison observations, already-covered list, candidate-only list, and hold recommendation. |
| Allowed | Record observed craft differences, identify overlap with existing Brick mechanisms, mark a single future candidate, and record a support-only hold consistent with the active TSK / dogfood completion posture. |
| Forbidden | Become source truth, success judgment, quality judgment, Movement authority; add or edit prompts, skills, checkers, contracts, or return fields; copy stack-specific external content into the protocol; open new implementation surface. |
| Allowed imports | none; markdown support comparison only. |
| Forbidden imports | runtime authority, storage/wiki authority, external template text as contract, checker pass as source truth, review as Movement authority, cross-axis ownership, new return-field admission, or commit/push permission. |
| Support residue reason, if any | This is support residue because it records an external craft comparison without owning Brick / Agent / Link meaning or choosing Movement. |
| Checker / verifier | Not run; this memo admits no physical contract change and requests none. |
| Not proven | source truth, success judgment, quality judgment, Movement authority, candidate necessity, future checker correctness, dogfood friction reality, or commit/staging state. |
| Movement | hold. |

## 2. Compared Surfaces

Brick side (read directly):
- `brick_protocol/agent/prompts/dev.md`, `brick_protocol/agent/prompts/pm-lead.md`, `brick_protocol/agent/prompts/cto-lead.md`, `brick_protocol/agent/prompts/design-lead.md`
- `brick_protocol/agent/skills/software-architecture/SKILL.md`, `brick_protocol/agent/skills/scoped-implementation/SKILL.md`, `brick_protocol/agent/skills/code-analyzer/SKILL.md`, `brick_protocol/agent/skills/gap-detector/SKILL.md`, `brick_protocol/agent/skills/design-depth-check/SKILL.md`

External side (read out-of-repo, not imported):
- ChatPRD built-in template bodies (planning + development family), captured separately for reference only.

## 3. Direct Verification Evidence

1. Brick Agent prompts encode role boundary and epistemic discipline (`Owns` / `Does Not Own`, `not_proven`, `remaining_delta`, `open_questions`, `review_needed`), not work-product craft. This is consistent across dev, pm-lead, cto-lead, and design-lead.
2. Brick craft skills (software-architecture, scoped-implementation, code-analyzer, gap-detector, design-depth-check) are intentionally thin and describe required return shapes and boundaries, not prescriptive how-to-author content.
3. ChatPRD templates instead bake "anti-mistake" instructions into the artifact itself (e.g. "always propose a smaller team," "be honest about weaknesses relative to competitors," "be specific: name tools, not categories," "timebox the effort," "self-contained so the reader needs no follow-up question").
4. Several ChatPRD craft intentions are already covered by Brick mechanisms through a different layer:
   - "Self-contained / no follow-up" overlaps with pm-lead "receive without guessing."
   - "Be honest about weaknesses" is a weaker form of Brick `not_proven` / `remaining_delta`.
   - "Completeness bar" is served by the review gate and evidence-verification, not by prompt prescription.
5. ChatPRD prescribes craft up front because it has no downstream verification stage. Brick has a downstream verification stage (evidence + review gate + Smith Movement). The two are different control philosophies, not the same layer.

## 4. Memo

### Memo 1: Single future candidate — rejected-approach capture
The one ChatPRD craft idea with no current Brick equivalent is explicit capture of a *considered-but-rejected wrong approach and the reason* (source: ChatPRD "Bug Investigation & Fix Plan" — "include what NOT to do if there are tempting but wrong fixes"). Brick records missing evidence and gaps, but not rejected wrong paths, which can let a downstream Agent re-enter the same trap. If admitted later, the natural home is an optional `rejected_approach_notes` observation in `code-analyzer` or `gap-detector` output. Not admitted by this memo.

### Memo 2: Specificity craft already weakly covered
ChatPRD "App Architecture" prescribes "name specific tools, not categories." Brick `software-architecture` already requires `module_boundaries` and `write_scope_notes`, and vague handoffs are caught downstream by the review gate. Net new value is low. No candidate raised.

### Memo 3: Philosophy-dilution risk
Adding ChatPRD-style up-front craft to Brick prompts would shift quality control from downstream verification toward up-front prescription, diluting the protocol's deliberate minimal-prompt identity. This memo recommends against importing external craft on an "it exists elsewhere" basis; any future addition should be driven by observed dogfood friction, not by external presence.

## 5. Held Boundaries

Still held:
- No prompt, skill, checker, contract, or return field was added or modified.
- No new return-field contract (`rejected_approach_notes`) is admitted; it is recorded as a future candidate only.
- The active TSK / dogfood roadmap completion posture is unaffected by this memo.
- External template text is not copied into the protocol and is not a contract.

## 6. Movement

Movement:
```text
hold
```

Target:
```text
ChatPRD template craft was reviewed against the current Brick Agent prompt/skill
surface. Most craft intentions are already covered by Brick's downstream
verification mechanisms. One future candidate (rejected-approach capture) is
recorded as memo only and is not admitted. No code or contract change is
requested. Smith remains closure authority and Movement authority on whether the
candidate is ever opened.
```
