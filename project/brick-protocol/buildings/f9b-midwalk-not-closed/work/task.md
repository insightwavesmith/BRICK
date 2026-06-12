# F9B: mid-walk buildings still project 'closed' (the remaining half of F9)

PRIOR BUILDING (f9-projection-states-0612, closed): fixed the breakdown direction — fossils and
adapter-error buildings now project 'stopped' (operator-verified on the real yard). But the
OTHER direction the task demanded is still broken, operator-reproduced JUST NOW on the live
yard via dashboard_export_packet: buildings that are MID-WALK (onboarding-legacy-scrub-0612 and
provider-ladder-fleet-presets-0612 — both had a codex step ACTIVELY RUNNING at probe time, with
completed early steps and NO closure boundary recorded) projected display state 'closed'.

REQUIRED: a building whose evidence shows completed steps but NO closure boundary fact and NO
breakdown frontier must project as the running/in-progress family — NEVER closed. Find where the
closed-state derivation keys (support/operator/ledger_projection.py and/or dashboard_export.py —
suspect: it may infer closed from last forward movement or from step-output presence instead of
an explicit closure boundary fact) and key it on the EXPLICIT closure boundary evidence only.
Do not regress the breakdown->stopped fix or parked->waiting_review.

PROOF: build a temp mid-walk-shaped fixture (completed step outputs, no closure boundary, no
breakdown) -> projection must print running family; re-run the four-state table (closed /
breakdown / fossil / parked) unchanged. FIRE: a mutated derivation inferring closed without the
closure boundary -> RED (extend the projection pin). Full gate -> exit 0 (say which checkout).
Constraints: support/* only; closed vocabulary; no pin weakening; plain-text refs only in your
return (no packet echo).
