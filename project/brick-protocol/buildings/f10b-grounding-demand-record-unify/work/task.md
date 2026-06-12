# F10 (attempt 2): review gates RECORD the grounding fact ref without DEMANDING it

PRIOR ATTEMPT NOTE (f10-grounding-demand-record-unify-0612, voided): the work return echoed
link handoff packet structures into returned_value (handoff_refs carrying 'movement') and the
closed AgentFact discipline rejected it. THIS attempt: NEVER echo packet/handoff/link structures
into your return — describe findings as plain text refs only (e.g. 'edge probe-design-to-build').

FINDING (operator-verified): notify-customer-language-autowire-0612 closed with review QA
returns whose evidence_used carried NO repository artifacts, yet its sufficiency traces RECORD
'BrickComparisonFact...evidence_used.repository_artifact_ref' — the gate forwarded (no demand)
while the lifecycle resolver cannot resolve the recorded ref. Two dated registry entries
(PRE_GROUNDING_LAW_BUILDING_IDS in check_building_lifecycle_path_shape.py) grandfather this;
YOUR repair closes the class so no third entry is ever needed.

REQUIRED: unify demand and record through ONE shared function both sides call: a gate that
RECORDS the grounding fact ref must have DEMANDED it (missing artifacts -> missing required
facts -> declared gate behavior fires), and a gate that does not demand for a return shape must
NOT record the ref. Inspect support/operator/run.py (~1545-1574), gate_sequence.py (~80-83,
250-255), plan_validation.py (~78-87, 596-656).

PROOF (run, report honestly, plain-text refs only): (a) review return WITHOUT artifacts -> gate
reports missing required fact, no unresolvable ref recorded; (b) WITH artifacts -> forwards and
recorded ref resolves; (c) non-review shape -> no demand, no record. FIRE: mutate the shared
predicate out of one side -> RED. Full gate: PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all -> exit 0
(say which checkout/copy). Constraints: support/* only; fails-closed; no pin weakening; do not
touch the two dated registry entries.
