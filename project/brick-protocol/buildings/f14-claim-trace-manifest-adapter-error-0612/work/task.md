# F14 — adapter-error 경유 폐장 빌딩의 claim_trace/manifest 불일치 (게이트 RED)

## Operator pre-analysis (VERIFIED — your design step must CONFIRM, not re-discover)
The operator already did the cross-file root-cause. BOUNDED READING LIST — read ONLY:
1. support/recording/adapter_error_frontier.py — error-time writers:
   _adapter_error_frontier_trace_packet (~line 1265) appends packets into
   evidence/claim_trace/link/frontier_trace.json (~lines 1177, 1238);
   _adapter_error_frontier_raw_manifest (~984) + _merge_or_append_raw_manifest_entry
   (~1118) merge raw:link-frontier:NN / raw:agent-received:NN entries into
   raw/raw-manifest.json AT ERROR TIME.
2. support/recording/raw_claim_trace.py — write_raw_and_claim_trace (line 17):
   happy-path FINAL writer; rebuilds raw/*.jsonl + claim_trace from IN-MEMORY step
   results (which do NOT contain the error-frontier rows).
3. support/recording/lifecycle_emit.py — _accumulated_raw_manifest (~172): FINAL
   manifest rebuilt from final rows only.
4. support/operator/run.py — resume_building_plan -> write_accumulated_building_evidence
   (the caller seam on successful closure after error holds).
5. The broken REAL root (READ-ONLY; copy to temp for experiments):
   project/brick-protocol/buildings/iap-dashboard-sink-passport-0612
Do NOT survey other modules; the operator already verified the defect is confined to
the disagreement between (1)'s error-time appends and (2)+(3)'s final rewrites.

## Reproduced defect (operator-verified on the real root)
After adapter-error holds at closure followed by a successful coo-forward closure:
- evidence/claim_trace/link/frontier_trace.json still references raw:link-frontier:06,
  but final raw/link.jsonl no longer contains that row and raw-manifest has no entry.
- evidence/claim_trace/agent/receipt_trace.json references raw:agent-received:06;
  raw/agent-received.jsonl HAS 6 rows but raw-manifest lists no such entry.
- building_lifecycle_path_shape correctly rejects ("raw_ref does not resolve through
  raw manifest") -> full gate RED; the building evidence cannot be committed.
Buildings with only gate-holds (f9, f13) are consistent — the hole is ONLY the
adapter-error-then-closure path.

## Objective (invariant)
Every raw_ref referenced by any evidence/claim_trace/* file resolves through
raw/raw-manifest.json for EVERY walk history, including adapter-error holds followed
by successful closure.

## Deliverables
1. Fix the writers so the final state is consistent. Design decision (justify briefly,
   pick ONE discipline for both trace families): EITHER final rewrite preserves
   error-frontier rows in raw/link.jsonl + manifest, OR final rewrite also rewrites
   frontier_trace/receipt_trace from the final rows. Keep append-only history semantics.
2. Reconciliation verb (support/*) for ALREADY-written broken roots: re-derive the
   inconsistent claim_trace/manifest entries purely from the root's own raw/*.jsonl.
   Refuse non-derivable repairs; write nothing outside the given root. Prove on a TEMP
   COPY of the real iap root: after reconciliation the path-shape invariant holds
   (run the same resolve check the checker does). Do NOT touch the real root.
3. Checker pin: fixture reproducing adapter-error->closure evidence -> invariant holds;
   mutation probe (drop the consistency step) -> RED.

## Proof required (run yourself, report honestly)
- compileall + git diff --check.
- Focused checker green + mutation RED (show both observations).
- Reconciled temp copy of the iap root passes the invariant (state copy path).
- Full gate in a TEMP SOURCE COPY: bake_dashboard_data_json() first, then
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3
  support/checkers/check_profile.py --all -> exit 0.

## Hard constraints (law)
- write_scope support/* only; no link/, agent/, brick/, project/ edits; append-only;
  no pin weakening (the path-shape rejection is CORRECT).
- Do not modify the real iap root or any project/ root.
- No scheduler/queue/retry; no new dependencies.
- Plain-text refs only in returns; never echo packet structures into report fields.
- No npm/node execution inside the worktree.
