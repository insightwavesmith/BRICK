# Frontier evidence honesty — breakdown buildings must write valid, resumable, fact-only evidence

## Objective
Three reproduced/observed defects in the adapter-error frontier path make honest breakdown evidence either LOST, SELF-INVALID, or UNRESUMABLE. Fix them so a broken building's evidence (a) always gets written, (b) passes the repo's own checkers, and (c) leaves the building disposable/resumable. This is prerequisite work for the upcoming chat-session park seam (S1), whose park recording is modeled on this same frontier writer.

## Defect A (reproduced on clean HEAD, fresh-intake path): first-step adapter error → frontier evidence LOST
- `support/operator/run.py` (~line 431) calls `write_adapter_error_frontier_evidence(..., overwrite_existing=overwrite_existing or bool(step_results))` — the guard assumes "root already exists ⇒ prior step evidence exists".
- The 0611 task-first intake (`driver.run_building_intake`) pre-writes `declared-building-plan.json` into the building root BEFORE walking, so the root ALWAYS exists. A FIRST-step adapter error (step_results empty, overwrite False) then hits the root-exists guard in `support/recording/capture.py` (~line 447) → FileExistsError → NO capture/, NO raw/ (no adapter-error.jsonl), NO evidence/ written at all. The honest breakdown record is lost and the caller sees only a crash.
- Observed repro artifact: /tmp/brick-frontier-repro/frontier-map-repro-0612 contains ONLY declared-building-plan.json after a deliberate out-of-scope write rejection at the first step.
- Required: the frontier writer must treat a pre-existing root that holds ONLY declaration-chain artifacts (declared-building-plan.json etc.) as NOT a collision and write the frontier evidence. A root holding ANOTHER building's lifecycle evidence must still fail closed. No blanket overwrite.

## Defect B (observed on the dynamic resume path; diagnose precisely before fixing): frontier building-map references phantom facts
- `project/brick-protocol/buildings/adapter-30-s1-park/work/building-map.json` (rewritten by the dynamic-walker frontier path when a resumed work step was voided) currently FAILS check_building_map_graph with, among others:
  * brick `brick-adapter-30-s1-park-work` lists `agent_binding_refs` naming a binding row that does not exist in the map;
  * link edges toward unwalked QA steps carry prefix-only `target_brick_instance_ref` text;
  * fan-out/fan-in `groups` reference edge ids that do not resolve.
- The linear-path composer `_adapter_error_frontier_building_map_packet` (support/recording/building_map_emit.py) appends the failed brick AND its binding row consistently — the dynamic path (support/operator/walker_frontier.py / walker_kernel.py map composition) is the suspect. Diagnose exactly where the phantom refs enter before changing anything.
- Required: on ANY frontier write (linear or dynamic, fresh or resume), the building-map must reference ONLY realized facts — completed steps' rows, plus the failed step's brick+binding pair recorded consistently — and must NOT emit edges/groups for unwalked declared topology. The result must PASS check_building_map_graph as-is. Do NOT weaken or exempt the checker to get there.
- Do NOT modify anything under project/ — the existing adapter-30-s1-park evidence is append-only history; your fix changes only how FUTURE frontier writes compose.

## Defect C (observed on building adapter-30-s1-park): a crashed resume leaves the building unresumable
- The resume path rewrites raw/link.jsonl (write_text, documented); when the resumed step hits the adapter-error frontier, the rewritten ledger carries NO transition_lifecycle hold row at all (the prior gate-hold and disposition rows are gone, replaced by nothing addressable). Result: there is no hold identity a future human/COO disposition row can reference → the building is permanently stuck.
- Required: when the frontier writer fires during a resume (and on the fresh path too, if the same gap exists there), the post-write ledger must carry an addressable record for the failed occurrence — whatever row shape the existing resume/disposition machinery (walker_resume._read_disposition_row + hold identity) needs to accept a future caller/COO disposition for that failed step. Reuse the existing hold/disposition vocabulary; invent no new Link vocabulary.

## Proof required (run, report honestly — claims only from execution)
1. Repro A fixed: in a TEMP output_root (never project/), declare a building via run_building_intake with a deliberately child-excluding write_scope (dir-form entry such as allowed_paths ["support/checkers/"]) and a trivial write task, using whatever adapter is simplest to make fail (a raising local callable through adapter:local is fine — any adapter exception exercises the same writer). After the expected AdapterFrontierEvidenceWritten, the temp building root must contain capture/events.jsonl, raw/adapter-error.jsonl, evidence/ claim traces, and the step-output adapter-error capsule.
2. Repro B fixed: drive the dynamic frontier path in TEMP (gate hold → disposition row → resume → adapter error at the resumed step — mirror the adapter-30-s1-park sequence); the resulting building-map.json must pass the building_map_graph kernel check.
3. Repro C fixed: after (2), append a caller/COO disposition row addressed to the new hold identity and show that resume accepts it (or fail-closes for a stated, principled reason — report exactly which).
4. FIRE: mutate a fixed map copy to re-introduce a phantom binding ref → the map checker must go RED (prove the pin still bites).
5. Full gate: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all → report the exit code honestly. KNOWN BASELINE: the yard carries adapter-30-s1-park whose OLD map still fails the map checker — do not exempt it; if that single known item keeps the gate at exit 1, say exactly that and list anything else that is red.

## Constraints
- No scheduler / queue / retry / timer. Fails-closed everywhere. Do not edit link/ or add Link vocabulary.
- Do not weaken, bypass, or special-case existing checker pins (especially check_building_map_graph and the lifecycle path-shape checker).
- Append-only history: never rewrite existing evidence under project/.
- Write scope: support/* and brick/building_plans/* only.

## Desired Output
Fixed frontier writers (linear + dynamic) with the precise diagnosis of where phantom refs entered, results of reproductions 1–3, the FIRE result, and the exact remaining-red statement for the full gate.
