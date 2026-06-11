# Chat-session adapter S1 — PARK seam (adapter #30, implementation order 1 of 8)

## Objective
Implement seam S1 of the chat-session adapter, per the Smith-approved design (v2, 2026-06-11): when a plan step's declared adapter is `adapter:chat-session`, the engine must PARK — record a work envelope + a park record (support-only records), then stop fails-closed. Parked state must be observable (frontier) and must ring the reporter bell. S2 (submit) and S3 (resume) are OUT OF SCOPE for this building.

## Why (context you need, self-contained)
Live chat sessions (human+AI) are being adopted as formal performers. The engine does NOT call a CLI for them; it records a work envelope and stops (no polling, no scheduler). A session later picks the envelope up, works, submits (S2), and the engine recomputes gates on re-entry (S3). Those later seams land in later buildings. The engine today has NO pre-step parking: every existing stop happens AFTER a step completes (adapter-error frontier is the closest precedent). S1 is therefore a NEW seam, not a reuse.

## Deliverables (all of them, in this building)
1. **Typed parked signal**: a new adapter kind `chat-session` in `support/connection/agent_adapter.py` (registered like the existing local CLI adapters) that does NOT invoke any CLI and returns/raises a TYPED 'parked' outcome (no AgentFact, no fabricated return). Follow the existing typed-exception pattern used by the adapter-error path.
2. **Park recording**: when the walk meets a chat-session step, support writes
   (a) the **work envelope** = the serialized `AgentAdapterRequest` projection for that step — NO invented fields, closed shape; and
   (b) a **park record** — modeled on `support/recording/adapter_error_frontier.py` but with a DISTINCT record shape/kind, because breakdown (adapter error) and waiting (parked) must be distinguishable downstream. The walk then stops for this lane, fails-closed. Integration point is the runner walk in `support/operator/run.py`.
3. **Frontier observation branch**: parked is a DERIVED observation, not a stored judgment. Add a park branch to the frontier observation logic (see `support/recording/adapter_error_frontier.py`, `support/recording/contracts.py`, `support/operator/ledger_projection.py`) ordered BEFORE the `agent_incomplete` branch — otherwise a parked building is misread as incomplete/running.
4. **Reporter bell**: update the two closed maps in `support/operator/reporter.py` (`_FRONTIER_TO_OBSERVED_STATE`, and `BUILDING_EVENT_FRONTIER_KINDS` + `BUILDING_EVENT_KINDS` frozensets) so a parked building emits a delivery/wake event. Candidate mapping: the needs_disposition / intervention_required family. Without this the bell never rings and a parked building projects as in-progress — that is a blocker, not a nice-to-have.
5. **Checker pins + FIRE fixtures** (each pin must be demonstrated RED on a mutated copy, then green):
   - envelope shape pin: closed keys; a UUID/ULID-shaped token or free-text session id appearing in the envelope = RED (Claude session ids are UUIDs; they must never enter the ledger).
   - park record vs adapter-error distinction case: a park record that is shape-indistinguishable from adapter-error = RED.
   - observer branch order case: a parked building observed as incomplete/running = RED.
   - reporter case: parked building emitting NO wake event = RED (mapping removal must fire).
   - path admission: the envelope/park-record paths must be added to BOTH path checkers' allowlists (`support/checkers/check_package_path_admission.py` admission AND `support/checkers/check_building_lifecycle_path_shape.py` shape/records) — fail-closed if either is missed.
6. **All 12 checker profiles stay green**: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all` must exit 0. Do not weaken, relocate, or bypass any existing pin to get there.

## Hard constraints (law — violations are rejects, not style notes)
- NO scheduler / queue / retry / timer anywhere. Parking stops the walk; nothing polls, nothing wakes itself.
- Link closed vocabulary stays CLOSED: park is a support record + derived frontier branch. Do not add Link movement literals, Link states, or transition vocabulary. Do not edit `link/`.
- Fails-closed everywhere: malformed park state, missing envelope, unknown adapter kind → loud reject, never silent fallback.
- Support records facts only: no success/failure/quality/judgment keys in any new record; no credential/session text in evidence; respect existing forbidden-key sets.
- Distinct shapes: park record ≠ adapter-error record (a dashboard must be able to tell "broken" from "waiting" without guessing).
- Append-only history: never rewrite existing evidence or fixtures' recorded facts.

## Desired Output
Working S1 seam (typed parked signal → envelope + park record → frontier branch → reporter bell) + the checker pins above, with `check_profile.py --all` exit 0 and each new pin demonstrated to FIRE (RED) on a mutated copy. State plainly in your return what is proven by execution and what remains not_proven.

## Honesty bar
Claim only what you executed. If a deliverable is partial, say which one and why — a parked-but-honest return beats a green-looking lie. Reviewers will attack exactly that gap.
