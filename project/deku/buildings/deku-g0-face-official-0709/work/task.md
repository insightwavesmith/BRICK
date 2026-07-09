# Deku G0 Face — official Building

## Objective
Close G0 Face Exit for project:deku on code at /Users/smith/projects/deku.

## Deliverables
1. Catalog context_window=40960 and truncation_policy.limit=40960 (not 10000).
2. Full message parse + session bind + no blank answers.
3. Trajectory C9.1 every turn.
4. Multi-turn still injects policy/wiki into conduct history (not hist-only).
5. `python3 -m unittest discover -s tests -v` green for G0 suite.

## Hard constraints
Write scope: deku_core/, deku_server.py, deku.py, tests/, docs/DEKU_STATUS.md only.
No wiki product beyond G0 inject path. No G1+ feature expansion.
Mock profile OK for harness; do not require paid workers for G0 Exit.

## Evidence
Record commands_run, changed_files, not_proven honestly.
