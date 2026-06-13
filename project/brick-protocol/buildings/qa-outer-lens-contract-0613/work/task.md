# QA outer-lens contract — symptom reproduction duty for attack-QA bricks

## Operator pre-analysis (VERIFIED — bounded reading list)
Read ONLY:
1. brick/templates/bricks/code-attack-qa/brick.md (+return.yaml) — current contract:
   attack implementation/regression/negative-probe vs declared work contract; must
   include inspected repository artifact references; forbidden verdict keys listed.
2. brick/templates/bricks/axis-attack-qa/brick.md (+return.yaml) — same shape for
   3-axis boundary inspection.
3. support/checkers/check_bricks_spec_completeness.py — the gate your edits must keep
   green: REQUIRED_FRONTMATTER 8 fields (lines ~33-42); non-empty body (~137); every
   return.yaml field named in body prose (PROSE<->YAML drift, ~216-219);
   required_return_template_refs resolve (~158-198).
Do NOT survey other modules.

## Reproduced fact (why — F9 half-green, operator-verified 0612)
F9's mid-walk-closed misprojection survived TWO same-lens QA passes because QA reused
the builder's own fixtures and lens; the real entry surface (bake_dashboard_data_json
over a real root) was never independently driven. Smith decision 0612: QA bricks gain
an OUTER-LENS contract.

## Objective (invariant)
Every code-attack-qa / axis-attack-qa performance must (a) independently REPRODUCE the
reported symptom from the task source (not from the builder's fixtures), (b) build its
OWN probes (builder fixture reuse forbidden), (c) drive at least ONE real entry surface
(the verb/projection a real caller uses), and name all three in its return.

## Deliverables
1. Revise BOTH brick.md bodies (and return.yaml if a field is added — keep PROSE<->YAML
   sync): add the three duties above as explicit instructions with a required return
   evidence triple: symptom_reproduction (what was independently reproduced + how),
   own_probes (probes built by QA, distinct from builder fixtures), real_entry_surface
   (which real verb/surface was driven + observed output). Decide whether these are new
   return.yaml fields or structured items under observed_evidence — pick the shape that
   keeps existing closed-AgentFact discipline and justify in design.
2. Keep ALL existing prohibitions (no mutation, no verdict keys) intact.
3. Gate: check_bricks_spec_completeness green; full gate --all exit 0 in temp copy.

## Proof required (run yourself, honestly)
- Focused run: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3
  support/checkers/check_profile.py --profile core (bricks_spec_completeness family) green.
- Full gate in TEMP SOURCE COPY (bake first, --all exit 0, state copy path).

## Hard constraints (law)
- write_scope brick/templates/* + support/checkers/* ONLY (checker sync if field set
  pins exist). Forbidden: link/*, agent/*, project/*, support/operator/*,
  support/connection/*, support/recording/*, brick/building.py, brick/work.py,
  brick/comparison.py, .git/*, AGENTS.md, pyproject.toml, uv.lock.
- No pin weakening; append-only; no scheduler; no new deps; no packet echo; no npm/node.
