# F16b — paper-stop predicate must recognize LEGACY adapter-error holds

## Operator pre-analysis (VERIFIED — design is PRESCRIBED; confirm, don't explore)
Read ONLY:
1. support/operator/walker_resume.py — _adapter_error_hold_without_return: currently
   `return _optional_text_value(hold_record.get("hold_reason")) == "adapter_error_frontier"`
   (operator-verified). NEW-engine holds carry that flat field; LEGACY 0612 holds do NOT.
2. ONE real legacy hold row (READ-ONLY, copy the shape into your fixture):
   project/brick-protocol/buildings/dashboard-productization-0612/raw/link.jsonl —
   its hold row carries transition_lifecycle_reason_refs INCLUDING
   "observation:reroute-hold-reason-adapter_error_frontier" (and an adapter-error
   observation ref), but NO flat hold_reason field.
3. The adapter_error_path_hardening checker family in support/checkers/lib/kernel_checks.py
   (your pin extends it).
Do NOT survey other modules.

## Reproduced fact (operator FIRE, 2026-06-13)
Paper-stop verified green on new-engine fixtures, but a stop disposition on a /tmp COPY
of the REAL dashboard-productization-0612 root attempted a LIVE adapter call (tripwire
command_runner fired at probe_local_cli_adapter). The builder's own fixture passed while
the real entry surface failed.

## Objective (invariant)
A stop disposition on ANY adapter-error hold — new-engine flat hold_reason OR legacy
reason_refs shape — paper-closes with ZERO adapter invocations.

## Deliverables (prescribed)
1. Broaden _adapter_error_hold_without_return: true when the flat hold_reason matches
   OR any transition_lifecycle_reason_refs entry contains "adapter_error_frontier"
   (text containment on the ref string; keep it narrow — no other reason families).
2. Checker pin: a LEGACY-SHAPED fixture row (copied field-for-field from the real 0612
   shape, synthetic ids) -> stop paper-closes with a captured runner asserting zero
   invocations; mutation probe (revert to flat-field-only predicate) -> RED.
3. Full gate --all exit 0 in temp source copy (bake first).

## Proof required (run yourself, honestly)
- compileall + git diff --check; focused pin green + mutation RED (show both).
- Full gate in TEMP SOURCE COPY (state copy path).

## Hard constraints (law)
- write_scope support/* only; forbidden link/*, agent/*, brick/*, project/*, .git/*,
  AGENTS.md, pyproject.toml, uv.lock. Do not touch real project roots (copies only).
- No pin weakening; no scheduler; no new deps; no packet echo; no npm/node.
