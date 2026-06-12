# F9: ledger/dashboard projection misstates non-happy buildings (both directions)

Reproduced by the operator on the live dashboard snapshot:
- BREAKDOWN/FOSSIL buildings project as '진행 중'(running): adapter-30-s1-park (crashed-resume fossil), dashboard-productization-0612 and 0612b (adapter-error voided attempts) all showed running.
- A MID-WALK building (dashboard-productization-0612c at 4/6 steps) projected as 'closed'.
A dashboard whose job is 'show where hands are needed' pointing backwards is a top-grade defect.

REQUIRED: in support/operator/ledger_projection.py (+ dashboard_export.py if it derives separately), fix the frontier/board-state derivation so:
1. adapter-error / agent_incomplete breakdown evidence -> the existing stopped/멈춤 family (closed vocabulary only — reuse existing literals).
2. A building with NO recognizable frontier and no closure (pre-repair fossil shape) -> stopped/unknown family, NEVER running.
3. A building with completed steps but NO closure boundary and NO breakdown -> running/in-progress (must NOT read closed).
4. chat_session_parked stays waiting_review (existing mapping — do not regress).
PROOF: drive each state in temp fixtures (a closed one, a mid-walk-shaped one, an adapter-error one, a fossil-shaped one, a parked one) through the projection and print the table; FIRE: a mutated derivation that maps breakdown->running must be RED in the relevant checker pin (extend the read-side projection pin if needed).
Full gate: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all -> exit 0 (say which checkout/copy).
Constraints: support/* only; closed vocabulary; no new judgment words; no link/, agent/, brick/, project/ edits; no pin weakening.
