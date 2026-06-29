# Finding: brick build exit 0 is intentional 3-axis design, NOT a false-success bug — 0626

Source: workflow `why-build-exit-zero` (wf_60ab002b), measured @ 3d22955. Corrects an earlier inference error — the "false-success = bug, fix it first" framing was wrong (an unmeasured assumption).

## What was measured
- `cli.py:_cmd_build` (241-247) returns literal 0 unconditionally; the packet carries frontier_kind (printed at :164) but it NEVER drives the exit code.
- This is the documented 3-axis rule "support records facts, never judges success/quality": AGENTS.md:57-67/173-175, rules-and-boundaries.md:115-139, cli.py PROOF_LIMITS (42-49); the `brick_cli_entrypoint` checker (yaml:44-52) bans `success_judgment`/`quality_judgment` tokens in cli.py.
- frontier_kind is a support FACT; the completion VERDICT is Link (link/spec.py:862 frontier_sufficiency_verdict) + a human COO disposition. An exit code derived from frontier = the forbidden "this passed" verdict.
- Contrast (deliberate asymmetry): `brick verify` returns the checker exit code (non-zero on RED, cli.py:259/278); `brick init` gates on build_error + verify-RED (H3 comment "otherwise brick init would exit 0 over a RED tree = a fake green", cli.py:403-412) — but NOT on frontier_kind.

## Implication for the goal
- **Do NOT change brick build's exit code** (would violate the design + trip the checker guard).
- The **dogfood/automation must read `frontier_kind=="complete"`** (from `--json`) or run `verify` for a gating code. Fact is published; the reader judges.
- Folded into change **C6** ([[build-fluency-roadmap-0626]]): a one-call custom-graph launcher CAN gate on `frontier_kind=='complete'` for an honest exit — that is the launcher's job, distinct from build CLI's report-only contract.
- Earlier plan item "1층 = 정직(거짓성공 닫기)" is therefore RETIRED as a build-CLI fix; it survives only as the launcher honesty in C6.

## Live corroboration
Building `godmodule-design-0626`: my launcher printed `frontier: ?` (wrong result attribute name in MY script) while the LEDGER honestly recorded frontier=complete + 5 returns. Lesson reaffirmed: read the ledger, not a launcher's print/exit. (This was a print typo, NOT the 3-axis exit-0 issue — distinct.)
