# Model-Lane Matching Discipline

Declared model-aptitude policy for lane dispatch (Smith, 0702; reconciled
0705/0706):

```text
codex = default implementation, finishing, and code QA lane
claude sonnet (xhigh effort) = default investigation, axis analysis, and evidence QA lane
gemini = default low-risk review lens; never assign heavy work by default
claude-fable-5 = admitted design/synthesis casting when explicitly cast, not an absolute lane-model ban; design-lead default is now model:claude:claude-opus-4-8 xhigh (0708 fable5 토큰 소진 — 기본만 opus 전환, fable5 클래스 명시 캐스팅은 유지)
codex-fugu-local / model:sakana:fugu-ultra = admitted high-depth work/design tier when explicitly cast
```

`preferred_model_ref` / `preferred_adapter_ref` on an Agent Object are
preferences for the normal case; this discipline is the aptitude constraint
those preferences must stay inside. A dispatch that steps outside it is an
Agent-axis deviation to surface, not a silent adjustment.

Code-attack-QA and closure may escalate by declared, risk-proportional casting
when the Building Plan carries the adapter/model selection explicitly. The
defaults above still control omitted casting: work and code QA start on Codex,
investigation/evidence QA start on Claude Sonnet, and broad low-risk review
stays Gemini-shaped. Fable-class use is admitted only through declared
Agent/Building casting such as the design-lead default or an explicit
code-attack-QA / closure elevation; it is not a blanket replacement for the
work/review defaults.

This discipline records dispatch-aptitude declarations only. It does not judge
the work, grants no write or Movement authority, and does not choose providers.

## 0707 tier reconciliation (Smith; walk-results-adopted-0707 §K·§G·§I)

The 0705/0706 defaults above stay recorded verbatim; the 0707 casting-tier
judgments below refine them without deleting any prior clause. They transcribe
the adopted §K, §G, and §I text and add no new policy.

```text
development work/repair lane (0707 §K) = codex excluded from development; opus-4.8 xhigh for simple-to-medium work, fugu (codex-fugu-local / model:sakana:fugu-ultra) for complex, entangled, or engine-grade work
codex development retirement (0707 §K) = codex leaves the work and repair lanes only and finishes walking its current building; QA lens and closure keep codex
claude QA two-tier (0707 §G) = engine-side or very-important claude QA on claude-fable-5 xhigh; other claude QA on model:claude:claude-opus-4-8 xhigh, replacing the prior sonnet QA default
claude-local throttle-window rule (0707 §I) = claude-local concurrency 1 is the safe line; route new dispatch onto codex or gemini lenses to avoid it, and attach-QA recovery is the standard salvage
```

0707 대체: the claude QA two-tier row supersedes the claude-sonnet QA default in
the 0705/0706 block for the QA-lens case, and the codex development-retirement
row narrows the codex work/finishing default to code QA and closure only. Both
superseded clauses are kept above for continuity and are not deleted. These rows
record 0707 dispatch-aptitude declarations only; they do not judge the work,
grant no write or Movement authority, and do not choose providers.
