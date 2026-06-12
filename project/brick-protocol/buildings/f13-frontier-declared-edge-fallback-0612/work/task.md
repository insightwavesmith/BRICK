# F13 — frontier 폴백이 그래프 선언행을 실행 증거로 오독 (보행중 빌딩이 closed로 투영)

## Reproduced fact (operator-verified, 2026-06-12T08:31Z)
Building notify-v2-vessel-guard-voice was MID-WALK (walk process alive, code-attack-qa step
in flight) yet bake_dashboard_data_json projected it state=closed/disp=closed.
Root cause chain, verified by hand on the real ledger:
1. Graph plan declaration writes ALL declared plan edges into raw/link.jsonl at intake time,
   INCLUDING the terminal edge {source_step_ref: ...-closure, target: building-boundary:<id>-closed}.
   These rows carry declared_graph_edge: true, movement_source: "declared graph Building Plan
   Link edge", raw_ref: "raw:link-graph:NN:...", and NO building_lifecycle_state.
2. support/operator/frontier_observation.py observe_building_frontier falls through (no pause,
   received==returned between steps) to _closed_boundary_observed(), which scans ALL raw link
   records for a closed-boundary target WITHOUT filtering declared rows -> returns True from
   the building's first minute -> frontier_kind=complete -> board closed -> dashboard closed.
3. The SIBLING helper _closed_boundary_raw_record_after_latest_pause already has the correct
   discipline: it skips records whose raw_ref does not start with "raw:link:" (declared graph
   edges are "raw:link-graph:"). The fallback lacks exactly this filter.
4. A REAL executed closure row (see f9-projection-states-0612 raw/link.jsonl last row) carries
   building_lifecycle_state: "closed" and raw_ref "raw:link:NN". That is the true closure signal.

## History (why this is F13, third strike on the same surface)
F9 fixed two-way misprojection (crashed->running, midwalk->closed). F9B keyed closure on
executed Link boundary evidence AFTER the latest pause. F13 is the remaining NO-PAUSE fallback
path. Same-lens QA has missed this surface twice; the repair MUST land an independent negative
checker pin, not just the code fix.

## Objective
A mid-walk graph Building whose raw/link.jsonl contains ONLY declared plan edges (plus
non-terminal executed rows) must NEVER observe frontier_kind=complete. Closure observation must
key on EXECUTED closure evidence only.

## Deliverables
1. Fix _closed_boundary_observed in support/operator/frontier_observation.py to ignore declared
   plan-edge rows. Design decision (justify in design step): filter by raw_ref "raw:link:"
   prefix mirroring the sibling helper, by declared_graph_edge truthy, or require
   building_lifecycle_state=="closed" on the closing record — pick the key that is structural
   (present on every executed closure row, absent on every declared row) and apply the SAME
   discipline to both helpers so they cannot drift apart.
2. Checker pin (extend the existing frontier/projection checker family): a fixture graph
   building with declared terminal edge + zero executed closure row -> frontier_kind MUST be
   closure_pending (or another non-complete kind); mutate the filter out -> RED. A fixture with
   a real executed closure row -> complete stays complete (no over-tightening).
3. The fix must keep the S1 park / S2 submit / chat_session_parked / agent_incomplete /
   link_paused branch behavior byte-identical (those branches precede the fallback).

## Proof required (run, report honestly — claims only from execution)
- Temp drive: declare a graph building in a temp output_root, walk ZERO steps, observe frontier
  -> NOT complete (today it would be complete; show before/after).
- Real-ledger FIRE: run observe_building_frontier against the REAL
  project/brick-protocol/buildings/notify-v2-vessel-guard-voice root (READ-ONLY — do not write
  into it) and report the observed frontier_kind before/after the fix.
- Truly-closed regression: observe f9-projection-states-0612 (executed closure row present) ->
  still complete.
- Full gate: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3
  support/checkers/check_profile.py --all -> exit 0, in a TEMP SOURCE COPY (say which copy).

## Hard constraints (law)
- write_scope support/* only; no link/, agent/, brick/, project/ edits; no pin weakening;
  append-only history. No scheduler/queue/retry/timer. Plain-text refs only in returns — never
  echo packet structures (handoff_refs etc.) into report fields.
- Do not modify the in-flight notify-v2 building's evidence in any way.
