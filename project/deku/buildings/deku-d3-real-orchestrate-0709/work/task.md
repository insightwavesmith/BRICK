# D3 Real Orchestrate — project:deku

## Prerequisite
D2 Real Conduct EXIT (product gates via `deku-d2-real-conduct-0709c` work harness + d2-session.log; unit 27 green).

## Objective
Close **D3 Real Orchestrate** on shipped real path (mock OFF).

## Done means
1. Hard query produces multi-step strategy trajectory log on shipped dispatch path
2. Greeting stays **1 call** (strategy greeting)
3. verify/replan≤1 fires ≥1 on real-path fixture
4. free-form WorkflowPlan remains **OFF**
5. Capture `raw/d3-scratch/d3-orchestrate.log` under this building
6. Update `/Users/smith/projects/deku/docs/DEKU_STATUS.md` D3 Exit + remaining_not_proven
7. unittest 27 green

## Environment
- Code: `/Users/smith/projects/deku`
- Python: `/Users/smith/projects/deku/.venv/bin/python` only
- `DEKU_WORKER_MODE=local_double` allowed (declared doubles; shipped dispatch)
- NO `DEKU_FORCE_MOCK=1`
- Durable scratch: this building `raw/d3-scratch` absolute under BRICK
- Prefer patch `probes/real_path_probe.py --phase d3` or building-local harness importing shipped deku_server
- Avoid putting raw `sess_*` session tokens in Agent return bodies (QA redaction trap from D2)

## Command sketch
```
export DEKU_WORKER_MODE=local_double
export DEKU_PROBE_SCRATCH=/Users/smith/projects/BRICK/project/deku/buildings/deku-d3-real-orchestrate-0709/raw/d3-scratch
mkdir -p "$DEKU_PROBE_SCRATCH"
cd /Users/smith/projects/deku
.venv/bin/python probes/real_path_probe.py --phase d3
```
Do not claim D4 Exit.
