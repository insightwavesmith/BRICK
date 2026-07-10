# Model-Lane Matching Discipline

Declared model-aptitude policy for lane dispatch (Smith, 0702; reconciled
0705/0706; Smith 0710 direct recast):

```text
pm-lead planning/synthesis = adapter:claude-local / model:claude:claude-fable-5 / effort:xhigh
development work/repair = adapter:codex-local / model:codex:gpt-5.6-sol / effort:xhigh
claude sonnet (xhigh effort) = default investigation, axis analysis, and evidence QA lane
gemini = default low-risk review lens; never assign heavy work by default
claude design and important Claude QA = model:claude:claude-opus-4-8 / effort:xhigh
codex-fugu-local / model:sakana:fugu-ultra = admitted high-depth work/design tier when explicitly cast
```

`preferred_model_ref` / `preferred_adapter_ref` on an Agent Object are
preferences for the normal case; this discipline is the aptitude constraint
those preferences must stay inside. A dispatch that steps outside it is an
Agent-axis deviation to surface, not a silent adjustment.

Code-attack-QA and closure may escalate by declared, risk-proportional casting
when the Building Plan carries the adapter/model selection explicitly. The
defaults above still control omitted casting: PM planning/synthesis starts on
Fable5 xhigh, GPT-5.6-sol xhigh is the active dev work/repair default,
investigation/evidence QA start on Claude Sonnet, broad low-risk review
stays Gemini-shaped, and Claude design / important QA casting uses
model:claude:claude-opus-4-8 xhigh. Fable5 is active only as the pm-lead
planning/synthesis default or an explicit planning cast. Fable5 remains
excluded from work and QA promotion.

This discipline records dispatch-aptitude declarations only. It does not judge
the work, grants no write or Movement authority, and does not choose providers.

## 0710 active recast over the 0707/0708 lineage (Smith)

The Smith 0710 direct recast supersedes the 0708 Fable5 active-dispatch
retirement. It supersedes the 0707 Codex development-retirement row. The older
rows remain historical evidence only; they do not control active dispatch.

```text
active PM lane (0710) = pm-lead uses model:claude:claude-fable-5 xhigh
active development lane (0710) = dev uses model:codex:gpt-5.6-sol xhigh
active high-depth exception = fugu remains available when explicitly cast for complex, entangled, or engine-grade work/design
claude QA active target = engine-side or very-important claude QA on model:claude:claude-opus-4-8 xhigh; Fable5 remains excluded from work and QA promotion
claude-local throttle-window rule (0707 §I) = claude-local concurrency 1 is the safe line; route new dispatch onto codex or gemini lenses to avoid it, and attach-QA recovery is the standard salvage
```

These rows record dispatch-aptitude declarations only. They do not prove live
provider availability or quality, judge the work, grant write or Movement
authority, or choose providers outside declared casting.
