Narrow self-consistency repair (operator-reproduced via check_profile.py --all): the lane-tooling grounding feature records a required public fact ref 'BrickComparisonFact.comparison_evidence.returned_field.evidence_used.repository_artifact_ref' in link sufficiency traces (appended by run.py/gate_sequence for review/design shapes), but check_building_lifecycle_path_shape's public-fact reference RESOLVER cannot resolve that dotted path — evidence_used is a LIST OF STRINGS, so the trailing '.repository_artifact_ref' leaf does not exist structurally. Result: the two newest buildings (lane-tooling-adversarial-review-0612, read-tier-unknown-token-guard-0612) turn the yard RED:
'public fact reference does not resolve: ...evidence_used.repository_artifact_ref'.

ROOT CAUSE: the gate CHECKS grounding by scanning evidence_used strings for repository-artifact shapes, but the RECORDED ref is named like a structural field — two organs, two standards.

REQUIRED (single-source the predicate):
1. Extract ONE shared helper (single source) for 'does this evidence_used list contain at least one repository-artifact-shaped reference' — used BY BOTH the gate-side grounding requirement AND the checker-side resolver.
2. Teach the lifecycle checker's public-fact resolver to resolve the virtual leaf '*.evidence_used.repository_artifact_ref' via that shared predicate: it RESOLVES iff the evidence_used list exists and the predicate finds an artifact-shaped entry; otherwise it stays an unresolved reference (RED) — do NOT blanket-admit the ref name.
3. FIRE both directions on mutated copies: (a) a sufficiency trace carrying the grounding ref while the return's evidence_used has NO artifact-shaped entry -> still RED; (b) with a real artifact-shaped entry -> resolves green. (c) the existing real evidence of the two RED buildings must pass after the fix (their evidence_used genuinely cites repo files).
4. Full gate: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all -> report the real exit code (temp copy acceptable; say which).

Constraints: support/* only; no link/, agent/, brick/ edits; fails-closed; no pin weakening; append-only project/ untouched.
