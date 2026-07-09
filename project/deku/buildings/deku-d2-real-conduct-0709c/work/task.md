# D2 Real Conduct (retry 0709c) — project:deku

## Prior attempt
`deku-d2-real-conduct-0709` frontier=`evidence_incomplete`. Live probe measured only ~2 turns before adapter error; temp sandbox wiped `d2-session.log`. Partial: pin+state present after multi-round seed (calls=6, local_double). **Not Exit.**

## Root causes to fix in this building
1. **Durable scratch** — MUST set `DEKU_PROBE_SCRATCH` to **this building** `raw/d2-scratch` (absolute under BRICK), never only ephemeral codex sandbox.
2. **Probe speed** — after 1 multi-round non-greeting seed (proves tool_call→worker), follow-ups must be **greeting** (`hello`/`안녕`) on `previous_response_id` so pin/state accumulate without 15× full Nemotron MAX_ROUNDS hangs.
3. **Full gates** — blank_turns=0, pin_ok, state turn≥5, timeout graceful non-blank, log ≥10 turns; CallBudget violations recorded (0 expected on path).

## Done means
1. Multi-round seed on real Nemotron path (mock OFF) via shipped `/v1/responses` + `dispatch_worker` (`DEKU_WORKER_MODE=local_double` OK)
2. 10–20 turn session log with pin/state survival
3. Timeout → non-blank body, process survives
4. `raw/d2-scratch/d2-session.log` on building root
5. `docs/DEKU_STATUS.md` D2 EXIT + remaining_not_proven
6. unittest 27 green

## Environment
- Code: `/Users/smith/projects/deku`
- Python: `/Users/smith/projects/deku/.venv/bin/python` only
- NO `DEKU_FORCE_MOCK=1`
- Prefer patch `probes/real_path_probe.py` phase_d2 if write works; else write harness under building `raw/d2_harness.py` that still imports shipped `deku_server`

## Command sketch
```
export DEKU_WORKER_MODE=local_double
export DEKU_PROBE_SCRATCH=/Users/smith/projects/BRICK/project/deku/buildings/deku-d2-real-conduct-0709c/raw/d2-scratch
mkdir -p "$DEKU_PROBE_SCRATCH"
cd /Users/smith/projects/deku
.venv/bin/python probes/real_path_probe.py --phase d2
# or building-local harness if probe patch blocked
```
Do not claim D3 Exit.
