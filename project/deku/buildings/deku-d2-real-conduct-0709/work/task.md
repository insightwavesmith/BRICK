# D2 Real Conduct — project:deku

## Prerequisite
D1 Real Face EXIT via building `deku-d1-real-face-0709b` (frontier complete). Evidence: Nemotron load, hello≥20, multi-turn.

## Objective
Close **D2 Real Conduct** on shipped real path (mock OFF).

## Done means
1. Multi-round tool_call → worker (or **declared** `DEKU_WORKER_MODE=local_double` via shipped `dispatch_worker`) → answer on real Nemotron path
2. CallBudget violations = 0 on measured runs
3. Worker timeout leaves server alive with non-blank force body (shipped path)
4. **10–20 turn session log** showing pin/state survival from live server path (not unit Pinboard alone)
5. Capture under building raw/ or DEKU_PROBE_SCRATCH: `d2-session.log`
6. Update `/Users/smith/projects/deku/docs/DEKU_STATUS.md` D2 Exit + remaining_not_proven
7. Regression: `/Users/smith/projects/deku/.venv/bin/python -m unittest discover -s tests -v` green

## Environment
- Code: `/Users/smith/projects/deku`
- Python: `/Users/smith/projects/deku/.venv/bin/python` only
- `DEKU_WORKER_MODE=local_double` allowed (declared doubles; must use shipped dispatch)
- NO `DEKU_FORCE_MOCK=1` for Exit proof
- Note: absolute writes to deku tree may be blocked by worktree sandbox — prefer probe/log evidence; if source fix required and blocked, record honestly under blocked_or_missing_evidence (do not fake)

## Command
```
cd /Users/smith/projects/deku
export DEKU_WORKER_MODE=local_double
export DEKU_PROBE_SCRATCH=<building-absolute>/raw/d2-scratch
.venv/bin/python probes/real_path_probe.py --phase d2
```
Fix probe/code only if D2 gates fail and write_scope permits. Do not claim D3 Exit.
