# Model-Lane Matching Discipline

Declared model-aptitude policy for lane dispatch (Smith, 0702; reconciled
0705/0706):

```text
codex = default implementation, finishing, and code QA lane
claude sonnet (xhigh effort) = default investigation, axis analysis, and evidence QA lane
gemini = default low-risk review lens; never assign heavy work by default
claude-fable-5 = admitted design-lead default for design/synthesis depth, not an absolute lane-model ban
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
