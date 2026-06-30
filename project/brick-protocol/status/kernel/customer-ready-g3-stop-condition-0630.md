# Customer-Ready G3 — FINAL architecture cleanup stop condition — 0630

Status: COO stop-condition declaration / support evidence only. Not source truth,
not success judgment, not quality judgment, and not Link Movement authority.

## Purpose

Closeout G3 must not become endless godmodule cleanup. This document declares the
minimum stop condition for the customer-ready closeout track after four verified
kernel_checks.py leaves landed.

## Current measured state

```text
support/checkers/lib/kernel_checks.py = 10814 LOC
support/checkers/lib/case_runners.py   = 8503 LOC
```

Largest remaining `run_*` clusters in kernel_checks.py (AST summary, no body dump):

```text
run_adapter_error_path_hardening             387 LOC
run_codex_connect_stall_classification       358 LOC
run_chat_session_park_seam                   332 LOC
run_design_ai_text_seams                     317 LOC
run_agent_adapter_return_shape               248 LOC
run_reporter_notification_projection         243 LOC
run_claude_projection_native                 230 LOC
run_gemini_local_only_adapter                209 LOC
run_codex_projection_native                  203 LOC
```

## Stop condition for this closeout

G3 is closeout-complete when ALL of these are true:

```text
1. kernel_checks.py is below 10000 LOC, OR every remaining >=200 LOC candidate is
   explicitly deferred with reason and owner.
2. Every implementation leaf landed after 0c is produced by a real main-agent
   drawn/fired Building, not direct operator patch.
3. Each landed leaf has conservation proof: byte-identical where possible,
   re-export/dispatch identity, module_registry row, mutation-RED/focused profile,
   and REAL HOME check_profile.py --all GREEN.
4. Remaining architecture debt is named in the closeout audit; checker/profile
   green is treated as support evidence only.
```

## Next recommended leaves

To reach <10000 LOC without over-expanding scope, prefer true-leaf candidates in
this order after AST dependency audit:

```text
1. run_codex_connect_stall_classification
2. run_design_ai_text_seams
3. run_gemini_local_only_adapter
4. run_codex_projection_native / run_claude_projection_native if still needed
```

`run_adapter_error_path_hardening` and `run_chat_session_park_seam` are larger
but likely cross-cutting; only extract them after a bounded dependency audit.

## Not proven

```text
- This stop condition does not itself extract more code.
- It does not prove all future G3 leaves are true leaves.
- It does not close G1 or G2.
```
