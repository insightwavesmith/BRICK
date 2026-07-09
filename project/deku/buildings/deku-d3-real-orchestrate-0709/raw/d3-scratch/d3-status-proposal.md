# D3 Real Orchestrate status proposal

Measured on 2026-07-10 by building `deku-d3-real-orchestrate-0709`.

Suggested `docs/DEKU_STATUS.md` D3 row update:

```text
| **D3 Real Orchestrate** | **EXIT evidence recorded** | `deku-d3-real-orchestrate-0709` work evidence | mock OFF; Nemotron load true; free-form plan OFF; greeting=1 call; hard strategy trajectory calls=3; verify/replan<=1 with replans=0; unittest 27 OK |
```

Evidence:

- `raw/d3-scratch/d1-load-ok.txt`: Nemotron load completed, profile `deku-1`, worker `local_double`.
- `raw/d3-scratch/d3-orchestrate.log`: `free_form_off=true`, `greeting_calls=1`, `greeting_blank=false`, `hard_calls=3`, `hard_kind=strategy`, `verify_replans=0`.
- `raw/d3-scratch/unittest.log`: `.venv/bin/python -m unittest discover -s tests -v` ran 27 tests, OK.

Not patched directly:

- `/Users/smith/projects/deku/docs/DEKU_STATUS.md` is outside this sandbox's writable roots.
