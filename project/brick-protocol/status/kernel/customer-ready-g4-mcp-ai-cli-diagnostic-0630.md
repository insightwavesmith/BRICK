# Customer-Ready G4 — MCP ai-cli diagnostic — 0630

Status: support evidence only / operator measurement. Not source truth, not
success judgment, not quality judgment, and not Link Movement authority.

## Purpose

The closeout plan reserves G4 for an MCP ai-cli diagnostic, separate from the
closeout mainline. The plan rule is explicit: do NOT use ai-cli / ai-cli-backed
helpers / subagents as a work path; only OBSERVE the ai-cli / MCP wrapper state
as evidence and classify whether it is a closeout blocker or a later diagnostic.

This diagnostic was performed by read-only observation. No ai-cli MCP tool was
invoked, and no ai-cli-backed Claude/Gemini/Codex helper or subagent was used.

## Observed wrapper state (read-only)

Codex MCP config (`~/.codex/config.toml`) declares the ai-cli MCP server as
DISABLED:

```text
[mcp_servers.ai-cli]
enabled = false
command = "npx"
args = ["-y", "ai-cli-mcp@2.21.0"]
```

PATH / launcher observation:

```text
ai-cli binary on PATH = not present
npx on PATH = /opt/homebrew/bin/npx
node on PATH = /opt/homebrew/bin/node (v26.3.0)
```

Interpretation: the ai-cli MCP server is configured but turned off, and there is
no standalone `ai-cli` binary on PATH. The wrapper would only launch on demand
via `npx ai-cli-mcp@2.21.0`, and it is currently `enabled = false`.

## Does BRICK closeout depend on ai-cli?

Dependency scan over the runtime-bearing surfaces:

```text
grep ai-cli in support/connection, support/operator, agent = no matches
```

The admitted provider-backed adapter runtime path uses the provider CLIs
directly (codex / claude / gemini), not ai-cli:

```text
support/connection/adapter_subprocess.py: adapter:codex-local, adapter:claude-local, adapter:gemini-local
support/connection/adapter_constants.py: ADAPTER_CODEX_LOCAL = "adapter:codex-local"
```

The G2 provider-backed fresh export build proof
(`customer-ready-g2-provider-backed-frontier-proof-0630.md`) reached
`frontier_kind=complete` using `adapter:claude-local` / `adapter:codex-local` /
`adapter:gemini-local`, with NO ai-cli involvement. That is direct evidence that
the customer-facing build path does not require ai-cli.

## Classification

```text
ai-cli MCP wrapper = DISABLED in config, no PATH binary, launch-on-demand via npx only.
BRICK runtime dependency on ai-cli = none observed in connection/operator/agent surfaces.
Customer build path (G2) = provider CLIs, ai-cli not involved.

=> ai-cli MCP is NOT a customer-ready closeout blocker.
=> It is a LATER / optional diagnostic surface, correctly kept off the closeout mainline.
```

This matches the goal's diagnostic-path restriction: because the wrapper is
unstable/disabled, the closeout mainline continues to avoid ai-cli / subagent /
helper routes, and the MCP question is parked as a separate later diagnostic.

## Narrowly proven

```text
- The ai-cli MCP server is declared enabled=false in the Codex config.
- There is no ai-cli binary on PATH; it would only launch via npx on demand.
- No ai-cli dependency appears in BRICK's connection/operator/agent runtime surfaces.
- The G2 provider-backed build reached frontier_kind=complete without ai-cli.
- Therefore ai-cli is not a closeout-mainline blocker; it is a later diagnostic.
```

## Not proven / caveats

```text
- This is a read-only config/runtime observation, not a live ai-cli health run
  (deliberately: the plan forbids using ai-cli as a work path).
- Whether ai-cli-mcp@2.21.0 would actually start, authenticate, or function if
  enabled is NOT tested here and remains not_proven.
- Future config changes could re-enable ai-cli; this observation is point-in-time.
- This is direct operator measurement, not a Building-produced patch.
- Support evidence only; not source truth, success, quality, or Movement authority.
```

## Next Movement candidate

```text
Movement candidate = forward
next = final closeout audit (G5)
```

G4 is closed as a parked later-diagnostic classification. Remaining closeout work
is the G5 final audit: reconcile the dirty main worktree, prove a clean repo
state, finalize push/merge target, and reach main=origin/main — all gated on
explicit Smith disposition for any push / merge / external action.
