# D1 Real Face — project:deku (Fugu router real path)

## Objective
Close **D1 Real Face** for Deku conversational router. Mock OFF. Real Nemotron load on shipped `deku_server`.

## Done means (all required)
1. `python3 deku_server` path without `DEKU_FORCE_MOCK`; `/healthz` → `loaded=true`
2. `/v1/models` → `context_window=40960` and `truncation_policy.limit=40960`
3. ≥20 hello/short turns non-blank on **real** `/v1/responses` (Nemotron loaded)
4. multi-turn 2+ reference non-blank on mock-off path
5. Capture logs under DEKU_PROBE_SCRATCH or building work/ evidence
6. Update `/Users/smith/projects/deku/docs/DEKU_STATUS.md` D1 Exit + remaining_not_proven
7. Keep existing unittest suite green: use `/Users/smith/projects/deku/.venv/bin/python -m unittest discover -s tests -v`

## Environment (declared)
- Code root: `/Users/smith/projects/deku`
- Weights: `artifacts/nemotron-8b`
- Interpreter for probes: **`/Users/smith/projects/deku/.venv/bin/python`** (system python lacks transformers)
- `DEKU_WORKER_MODE=local_double` allowed (declared local doubles via shipped `dispatch_worker` — not a reimplemented loop)
- `DEKU_HOME` may be building-local temp under work/

## Hard constraints
- Implement only inside write_scope. No fine-tune, no RoPE, no wiki-first, no G4 paid Dominate.
- Do not claim D1 Exit on mock-only (`DEKU_FORCE_MOCK=1`).
- If MPS OOM/load fails: record honest failure evidence; do not fake loaded=true.
- Free-form WorkflowPlan stays OFF.

## Suggested command
```
cd /Users/smith/projects/deku
export DEKU_WORKER_MODE=local_double
export DEKU_PROBE_SCRATCH=work/d1-scratch   # or absolute under building root
/Users/smith/projects/deku/.venv/bin/python probes/real_path_probe.py --phase d1 --hellos 20
```
If probe missing/broken, fix shipped code then re-run. Return commands_run, changed_files, observed_evidence, not_proven.
