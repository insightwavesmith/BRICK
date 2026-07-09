# adapter:grok-local land evidence (0709)

| | |
|---|---|
| **Status** | support evidence · land record |
| **Date** | 2026-07-09 |
| **Adapter** | `adapter:grok-local` |
| **CLI** | `grok` (Grok Build TUI/CLI, observed `grok 0.2.93`) |
| **Proof limit** | not source truth · not success/quality · not Movement authority |

---

## What landed

First-class local CLI adapter so Grok joins BRICK as a performer alongside codex/claude/gemini.

| Surface | Change |
|---|---|
| `adapter_constants` | `ADAPTER_GROK_LOCAL`, model refs, capabilities, observed-write, boundary row |
| `agent_adapter` | `LocalCliSpec` (`invocation_args_kind=grok-single-turn`), model examples, read-tier, install/login hints |
| `adapter_local_cli` | headless `grok -p` argv: sandbox, tools, isolation flags, casting model/effort |
| `adapter_subprocess` | executable allowlist `grok`; preflight message list |
| `agent/spec` | model flag `-m`, effort `--reasoning-effort`, `EFFORT_SCOPE` |
| `provider_registry` | default model, provider map, LLM alias `grok` (+ `fast`) |
| `onboard` / `cli` | host `grok`, real-provider selection order |

---

## Invocation shape (support only)

```text
# read-tier (reviewer-readonly etc.)
grok -p <prompt> --output-format plain --sandbox read-only --cwd <cwd>
     --always-approve --tools read_file,grep,list_dir
     [--no-subagents --no-memory --disallowed-tools Agent]  # isolation on
     -m <model> [--reasoning-effort <level>]

# write-tier (Brick write_scope + write-tier policy + observed-write)
grok -p <prompt> --output-format plain --sandbox workspace --cwd <cwd>
     --always-approve
     [--no-subagents --no-memory --disallowed-tools Agent]
     -m <model> [--reasoning-effort <level>]
```

Write authority is still Brick write_scope + tool policy + observed-write admission — not the adapter ref alone.

---

## Probes (executed 0709)

| Probe | Result |
|---|---|
| `probe_local_cli_adapter(adapter:grok-local)` | version `grok 0.2.93 … [stable]` |
| `preflight_provider(adapter:grok-local)` | `ok=True`, installed |
| Live `connect_agent_brain` read-tier | `adapter_ref=adapter:grok-local`, excerpt contains `pong` |
| Mock write argv | `--sandbox workspace` + `--always-approve`, no `--tools` allowlist |
| `provider_registry_ladder` profile | **passed** |
| py_compile on touched modules | ok |

### Known CLI constraint (observed)

Including `open_page,web_search` in a headless `--tools` allowlist on grok 0.2.93 tripped agent-build schema error on `run_terminal_cmd` (`auto_background_on_timeout` constraint). Read-tier allowlist intentionally limited to `read_file,grep,list_dir`.

---

## not_proven

```text
- long multi-step Building dogfood with preferred_adapter_ref=adapter:grok-local
- write-tier live file mutation under full write_observation path
- brick MCP wiring for grok (not in this land; codex/claude only today)
- credential validity beyond preflight/version (OAuth body outside Brick)
```

---

## Operator note

```text
brick onboard  # can register grok host after preflight
# graph-decl casting: preferred_adapter_ref: adapter:grok-local
# or llm alias: grok
```
