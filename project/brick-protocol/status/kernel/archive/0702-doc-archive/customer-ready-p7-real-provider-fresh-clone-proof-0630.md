# Customer-Ready P7 Real-Provider Fresh-Clone Probe — 0630

Status: support evidence only. Not source truth / success / quality / Movement authority.

## Probe result

P7 minimal real-provider fresh-clone route reached `frontier_kind=complete`.

- probe work dir: `/tmp/brick-p7-min-codex-20260629T180942Z-PZyo0j`
- fresh clone repo: `/tmp/brick-p7-min-codex-20260629T180942Z-PZyo0j/BRICK`
- fresh HOME / evidence home: `/tmp/brick-p7-min-codex-20260629T180942Z-PZyo0j/home/.brick`
- origin/main HEAD cloned: `ebf59308c228bfb5fb3dc54ef2fd970bbda57b5f`
- official route: `uv run python3 -m brick_protocol.support.operator.cli build --graph <packet>`
- graph packet: `/tmp/brick-p7-min-codex-20260629T180942Z-PZyo0j/p7-min-graph.json`
- building id: `p7-min-graph-codex-fresh-clone-20260629T180942Z`
- evidence root: `/tmp/brick-p7-min-codex-20260629T180942Z-PZyo0j/home/.brick/project/brick-protocol/buildings/p7-min-graph-codex-fresh-clone-20260629T180942Z`
- frontier: `complete`
- sandbox commit: `f6d33aadab38bff57f42e257760a8876907004ce`

## Shape used

Composition-first smoke, not the heavy fixed `work -> QA -> closure` chain:

```text
work(adapter:codex-local, write_scope one file)
  -> closure(adapter:codex-local)
  -> building-boundary:closed
```

Why: the prior `fast-fix` preset path proved clone/install/provider dispatch but timed out at the QA node. For P7's route proof, the smallest graph preserving real provider work + closure was the right dogfood shape.

## Observed evidence

- Network clone succeeded from GitHub into a temp checkout using noninteractive GitHub auth; no BRICK project/evidence state was reused.
- `uv sync` succeeded in the fresh clone.
- `brick status` under the temp HOME resolved `brick_home` to the temp `.brick` path and `default_builds_root_exists=false` before the run.
- `brick auth login --json` with GitHub auth available returned `doctor.all_ok=true`; `adapter:codex-local` was installed/ready at preflight level.
- `onboard codex --no-example` exited 0.
- The declared graph packet materialized two codex-local nodes: `p7-min-work` and `p7-min-closure`.
- `raw/adapter-usage.jsonl` contains codex-local usage rows for both nodes.
- `raw/agent-return.jsonl` contains returned AgentFacts for both nodes.
- `raw/link.jsonl` contains only `forward` rows: work -> closure and closure -> `building-boundary:closed`.
- `evidence/spine/spine.json` contains 24 chained events ending in `Frontier`.
- Sandbox commit `f6d33aad...` contains exactly one file change: `project/brick-protocol/status/kernel/p7-min-graph-codex-fresh-clone-20260629T180942Z.md` with the declared three bullet lines.

## Narrowly proven

- P7's post-clone official graph route can run from `origin/main` content in a fresh temp HOME/evidence home.
- A real provider-backed adapter (`adapter:codex-local`) can perform the work node and closure node through the official CLI graph route.
- The run reached customer-visible `frontier_kind=complete` and produced operator-readable raw/evidence/spine records.
- P3/P5 route repairs are sufficient for this minimal fresh-clone graph proof.

## Not proven / caveats

- This is a minimal graph proof, not a broad reliability proof.
- GitHub private clone used existing authenticated credentials noninteractively; a brand-new human machine still must run the documented GitHub auth step.
- The temp HOME was seeded with Codex auth files to simulate documented `codex login`; credential bodies were not recorded.
- Gemini is not ready on this machine: live Gemini CLI probe returned `API_KEY_INVALID`, despite preflight seeing an API-key env var.
- The heavier `fast-fix` preset path is not P7-green here: `adapter:codex-local` completed the work node but QA timed out; `adapter:gemini-local` failed at the work node due invalid API key.
- Closure returned a non-binding `verification_gap` note about evidence files it did not see during its own inspection; final evidence generation did write those claim-trace/raw files, and Link still recorded forward/complete.

## Next target candidate

P8 dogfood capstone can start using the same composition-first rule: choose the smallest LLM + Brick + graph shape that proves the user task through the customer entrypoint. If P8 needs broad QA, split it as a deliberate graph choice rather than defaulting to the heavy `fast-fix` preset.
