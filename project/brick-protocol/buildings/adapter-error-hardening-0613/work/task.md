# Adapter-error path hardening — F15/F16/F17/F18/F19 (postmortem-fed)

## Operator pre-analysis (VERIFIED coordinates — bounded; confirm, don't survey)
Postmortem postmortem-0612-incidents (closed, 3dbd7d3) attributed ALL 0612 afternoon
failures to Agent-axis violations correctly rejected by guards; the remaining engine
gaps are the FIVE below, each operator-reproduced:

F15 — birth certificate written too late. A walk whose FIRST step errors leaves a root
  WITHOUT declared-building-plan.json -> resume refuses (walker_resume.py:133 raise).
  Reproduced 3x (f14 run1, fleet run1, notify-v3 run1). FIX: run_building_plan
  (support/operator/run.py) must write the root + declared-building-plan.json (and the
  intake artifacts that materialize already carries) BEFORE the first adapter call, so
  every walk leaves a ledger trace from minute zero.
F16 — no paper-stop at adapter-error holds. walker_kernel.py ~1655-1685: the stop
  disposition path replays the held step's recorded return; an adapter-error hold has
  NO recorded return so stop RE-RUNS the held step LIVE (operator-reproduced on a /tmp
  copy: codex spawned with workspace-write). FIX: at an adapter-error hold, stop must
  stamp resumed->closed (ended-by-disposition) WITHOUT any adapter call, recording that
  the held step never returned.
F17 — building_started delta has no root to project. run.py ~1226 emits started BEFORE
  root files exist -> dashboard delta silently not_attempted (operator-observed 23:18).
  FIX: with F15 in place the root exists first; ensure the started emit happens after
  the initial root write (ordering only; no retry/queue).
F18 — codex sessions leave NO transcript anywhere. support/connection/agent_adapter.py
  passes --ephemeral unconditionally (stall sessions unanalyzable; operator-verified
  ~/.codex/sessions has rollouts ONLY for non-ephemeral runs). FIX: env dial
  BRICK_CODEX_EPHEMERAL ("1" -> current behavior; default/absent -> DROP --ephemeral so
  machine-local rollouts persist). Repo evidence keeps NO session bodies (redaction law
  unchanged — rollouts stay machine-local under ~/.codex).
F19 — overwrite relaunch leaves stale claim_trace. run_building_plan(overwrite_existing
  =True) re-lays raw/* but evidence/claim_trace/link/frontier_trace.json kept a
  raw:link-frontier ref from the PREVIOUS attempt (operator-reproduced on notify-v3;
  reconciled by hand with reconcile_claim_trace_raw_manifest_from_raw). FIX: the
  overwrite path must clear/rewrite prior claim_trace + manifest so the fresh walk
  starts consistent (reuse the F14 writers/reconcile discipline — one discipline, no fork).

## Objective (invariants)
1. EVERY walk leaves a root with its birth certificate before any adapter runs (F15/F17).
2. stop at any hold is a paper act — never a live adapter run (F16).
3. Overwrite restarts begin claim_trace-consistent (F19).
4. codex transcripts persist machine-local unless explicitly disabled (F18).

## Deliverables
1. The five fixes above (support/* only; smallest diffs that satisfy the invariants).
2. Checker pins (extend existing families; no weakening):
   a. F15: temp fixture — root exists with declared-building-plan.json after a
      first-step adapter error; resume on it proceeds (no birth-certificate refusal).
   b. F16: stop disposition on an adapter-error hold fixture completes with ZERO
      adapter invocations (captured runner asserts no call) -> ended-by-disposition
      boundary; mutation probe restoring the live re-run -> RED.
   c. F19: overwrite fixture — relaunch over an error-holding root passes the
      claim_trace->manifest resolve invariant; mutation (skip the clear) -> RED.
   d. F18: unit probe — adapter argv contains --ephemeral IFF BRICK_CODEX_EPHEMERAL=1.
3. After-merge operator note (in your return): the three stale holds
   (provider-ladder-fleet-presets-0612, dashboard-productization-0612, -0612b,
   adapter-30-s1-park, f10-grounding-demand-record-unify-0612) become paper-stoppable.

## Proof required (run yourself, honestly)
- compileall + git diff --check; focused pins green + the two mutation REDs (show).
- Full gate in TEMP SOURCE COPY (bake first, --all exit 0, state copy path).
- Do NOT touch real project/ roots; fixtures in temp only.

## Hard constraints (law)
- write_scope support/* only; forbidden link/*, agent/*, brick/*, project/*, .git/*,
  AGENTS.md, pyproject.toml, uv.lock. No scheduler/queue/retry; no new deps; no pin
  weakening; append-only; plain-text refs only; no packet echo; no npm/node.
