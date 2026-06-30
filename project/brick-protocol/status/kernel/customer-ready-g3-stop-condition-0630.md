# Customer-Ready G3 — FINAL architecture cleanup stop condition — 0630

Status: COO stop-condition declaration / support evidence only. Not source truth,
not success judgment, not quality judgment, and not Link Movement authority.

## Purpose

Closeout G3 must not become endless godmodule cleanup. This document declares the
minimum stop condition for the customer-ready closeout track after four verified
kernel_checks.py leaves landed.

## Current measured state

Measured in `/Users/smith/.brick/worktrees/g3-stop-condition-leaves-0630a`
after the in-flight checker-leaf split:

```text
support/checkers/lib/kernel_checks.py = 9931 LOC
support/checkers/lib/case_runners.py   = 8503 LOC
```

Extracted checker-lib leaves in this G3 worktree:

```text
support/checkers/lib/design_ai_text_seams_check.py
support/checkers/lib/codex_connect_stall_classification_check.py
support/checkers/lib/gemini_local_only_adapter_check.py
```

`kernel_checks.py` is now below the 10000 LOC stop-condition threshold.
Remaining >=200 LOC AST candidates are explicitly deferred for later bounded
work; they are not G3 closeout blockers because the LOC threshold is met and
each remaining candidate needs its own dependency/conservation audit before any
future extraction:

| candidate | LOC | defer reason | owner |
| --- | ---: | --- | --- |
| `_agent_read_tier_probe` | 864 | broad Agent adapter/read-tier probe with many shared assertions | future checker-leaf Building |
| `_assert_reporter_brick_grain_threading` | 663 | reporter/threading assertion cluster spans rendering and sink-shape semantics | future checker-leaf Building |
| `_assert_brick_cli_customer_task_intent` | 555 | customer CLI intent guard spans task text, launcher, and product language checks | future checker-leaf Building |
| `_agent_effective_write_probe` | 492 | crosses Brick write need, Agent policy, adapter capability, and write observation | future checker-leaf Building |
| `_artifact_grounding_probe` | 464 | spans evidence, report, and projection seams | future checker-leaf Building |
| `run_adapter_error_path_hardening` | 387 | cross-cutting adapter/run/frontier report-root hardening | future checker-leaf Building |
| `run_chat_session_park_seam` | 332 | parked chat-session handoff seam crosses Agent resources and support adapter behavior | future checker-leaf Building |
| `run_agent_adapter_return_shape` | 248 | central adapter contract evidence requiring stronger conservation proof before extraction | future checker-leaf Building |
| `run_reporter_notification_projection` | 243 | spans admitted sinks and no-scheduler/no-queue/no-retry discipline | future checker-leaf Building |
| `_assert_adapter_error_frontier_report_root_admission` | 234 | couples frontier evidence and report-root shape | future checker-leaf Building |
| `run_claude_projection_native` | 230 | provider-native projection proof should move with Codex projection as a bounded pair | future checker-leaf Building |
| `run_codex_projection_native` | 203 | provider-native projection proof should move with Claude projection as a bounded pair | future checker-leaf Building |
| `_assert_reporter_auto_wiring` | 200 | couples sink admission and render packet discipline | future checker-leaf Building |

## Stop condition for this closeout

G3 is closeout-complete when ALL of these are true:

```text
1. kernel_checks.py is below 10000 LOC, OR every remaining >=200 LOC candidate is
   explicitly deferred with reason and owner.
2. Every implementation leaf landed after 0c is produced by a real main-agent
   build() Building, not direct operator patch.
3. Each landed leaf has conservation proof: byte-identical where possible,
   re-export/dispatch identity, module_registry row, mutation-RED/focused profile,
   and REAL HOME check_profile.py --all GREEN.
4. Remaining architecture debt is named in the closeout audit; checker/profile
   green is treated as support evidence only.
```

## Next recommended leaves

The closeout LOC threshold no longer requires more extraction in this G3 slice.
If future bounded checker-leaf Buildings continue cleanup, prefer these next
candidates only after AST dependency audit:

```text
1. run_codex_projection_native / run_claude_projection_native as a provider-projection pair
2. run_agent_adapter_return_shape only with strong adapter-contract conservation proof
3. run_adapter_error_path_hardening only after frontier/report-root dependency audit
```

`run_adapter_error_path_hardening` and `run_chat_session_park_seam` are larger
but likely cross-cutting; only extract them after a bounded dependency audit.

## Not proven

```text
- This status record is support evidence only.
- It does not prove that the in-flight leaf split came from official build() evidence.
- It does not prove Slack notification, sandbox commit, conservation proof, or
  REAL HOME --all for this G3 slice.
- It does not prove all deferred future G3 leaves are true leaves.
- It does not close G1 or G2.
```
