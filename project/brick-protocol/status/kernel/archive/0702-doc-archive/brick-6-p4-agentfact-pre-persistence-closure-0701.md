# BRICK 6 P4 AgentFact pre-persistence closure evidence - 2026-07-01

## Scope

- Phase: P4 - AgentFact top-level forbidden keys before persistence.
- Repo: `/Users/smith/projects/BRICK`.
- Base before P4 sequence: `0354a8f`.
- Current adopted HEAD after P4 sequence: `e72f59e`.
- P4 evidence roots:
  - `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p4-agentfact-pre-persistence-0701a` — paused implementation/evidence diagnostic.
  - `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p4-agentfact-pre-persistence-0701c` — final complete AgentFact pre-persistence Building.
  - `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p4-sensitive-source-path-unblock-0701a` — support classifier unblocker required before P4 could be committed.

## Adopted commits

```text
0c15f21 P4: declare sensitive source-path unblock graph
45d8aa4 BRICK building output: brick-6-p4-sensitive-source-path-unblock-0701a
c85f368 P4: declare AgentFact pre-persistence graphs
e72f59e BRICK building output: brick-6-p4-agentfact-pre-persistence-0701c
```

P4a/P4b graph declarations are kept as routing evidence: P4a reached implementation but paused on evidence/log/template-ref concerns; P4b exposed the P2 sensitive-path classifier false positive that blocked committing `support/operator/run_chat_session.py`.

## Observed evidence

- P4c Building result: `frontier_kind=complete`.
- P4c sandbox commit: `2e2b5f328e07eeead47644b54eaff3cbfc3a47bb`, adopted to main as `e72f59e`.
- P4c changed files:
  - `support/operator/run_chat_session.py`
  - `support/checkers/lib/kernel_checks.py`
  - `support/checkers/check_building_lifecycle_path_shape.py`
- P4 unblocker Building result: `frontier_kind=complete`.
- P4 unblocker changed files:
  - `support/operator/write_observation.py`
  - `support/checkers/check_building_operator_driver0.py`
- Direct current probe observed `make_agent_fact` rejects top-level `status`, `result`, `success`, `movement`, `target`, and `verdict`, while accepting nested ordinary `observed_evidence[].status` and `evidence.result`.

## Narrowly proven

- Chat-session submission intake now runs closed AgentFact validation before `submission.json` is written.
- Top-level AgentFact authority/verdict/Movement keys are rejected before chat-session persistence.
- Nested ordinary evidence keys named `status` / `result` remain legal and are not recursively banned.
- Poisoned top-level chat-session submission cannot create the prior write-exclusive `submission.json` wedge in the focused `chat_session_park_seam` probe.
- AgentFact shape remains `received_work` + `returned`; support did not gain success, quality, or Movement authority.
- Sensitive-path commit blocking no longer treats the source file `support/operator/run_chat_session.py` as a provider-session payload path, while provider-session-like payload paths and `.env` remain covered by focused checker evidence.

## Verification commands after adoption

Run on main at/after `e72f59e`:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 -m py_compile support/operator/run_chat_session.py support/checkers/lib/kernel_checks.py support/checkers/check_building_lifecycle_path_shape.py support/operator/write_observation.py support/checkers/check_building_operator_driver0.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile support/checkers/profiles/building_automation.yaml
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile support/checkers/profiles/building_operator_driver0.yaml
git diff --check HEAD~5..HEAD
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
```

Observed result: all commands exited 0. The full profile ended with registered profile passes including `building-automation`, `building-operator-driver0`, `core`, `read-side-projection-boundary`, `structure-template-integrity`, and `tier-a-three-axis-conformance`.

## Not proven / proof limits

- This does not prove P5-P8 or whole customer-ready closeout.
- This does not prove future provider reliability, credential validity, quality, success, source truth, or Link Movement authority.
- This does not prove semantic completeness for every future chat-session schema; it proves the named P4 top-level-vs-nested boundary and wedge class.
- Checker/profile green is support evidence only.

## Next Movement candidate

Proceed to P5: `declared_gate_refs` law + invalid concern target safety, unless Smith/COO explicitly requests more P4 replay evidence.
