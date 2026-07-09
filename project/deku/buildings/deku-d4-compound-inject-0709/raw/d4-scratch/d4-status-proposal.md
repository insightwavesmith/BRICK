# D4 status proposal

Proposed `docs/DEKU_STATUS.md` ladder row:

| **D4 Compound inject** | **EXIT** | `deku-d4-compound-inject-0709` work + `d4-inject.txt` | next-turn conduct history contains policy marker + wiki_slice text; shipped `/v1/responses`/`_handle_turn`; unit 27 green; BRICK docs update blocked by sandbox |

## D4 evidence

| Gate | Result |
|---|---|
| policy hints real strings in next-turn conduct history | true (`[policy]`, `policy.v-d4`, `d4_policy_marker`) |
| lesson compile then next-turn wiki_slice in history | true (`[wiki]`, `concepts/d4-lesson.md`, `write_scope`) |
| Hermes llm-wiki skill not source | true by existing unit `test_no_hermes_skill_as_source_in_core` in 27-test run |
| shipped path | `/v1/responses` through `_handle_turn`, mock off, Nemotron loaded |
| regression | unittest 27 OK |
| durable logs | `raw/d4-scratch/d4-inject.txt`, `raw/d4-scratch/d4-dogfood.log`, `raw/d4-scratch/probe-summary.json` |

## D4 remaining_not_proven

```text
- Paid worker bodies were not exercised; DEKU_WORKER_MODE=local_double was used as declared OK.
- The D4 probe captures conduct history through a patch wrapper around deku_server.run_conduct while still using the shipped /v1/responses and _handle_turn path.
- docs/DEKU_STATUS.md in /Users/smith/projects/deku was not edited by this agent because the active filesystem sandbox allows writes only inside the BRICK worktree and temp roots.
- No git commit or push was run because this Agent packet forbids git commit and git push.
```
