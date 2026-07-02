# Customer-Ready G2 — provider-backed fresh export frontier proof — 0630

Status: support evidence only / operator measurement. Not source truth, not
success judgment, not quality judgment, and not Link Movement authority.

## Purpose

Close the explicit G2 gap left by prior fresh-export measurements:

```text
A real provider-backed fresh export build reaching frontier_kind=complete was
not re-run here.
```

This proof measures a fresh release export, installs it, runs the public CLI, and
then runs an actual provider-backed `build()` using the exported tree. It does
not push, publish, merge, tag, or perform external repository delivery.

## Measurement base

```text
source checkout = /Users/smith/projects/BRICK
source branch = main
source HEAD = 2b8006e
source state = dirty tracked WIP present before export; export is current working-tree evidence
export base = /Users/smith/.brick/tmp/g2-provider-backed-20260630173157
export tree = /Users/smith/.brick/tmp/g2-provider-backed-20260630173157/export
release export command = sh support/onboarding/release_export.sh --output <export tree>
```

Source dirty state was recorded in:

```text
/Users/smith/.brick/tmp/g2-provider-backed-20260630173157/source-status.txt
```

## Fresh export observation

```text
release export ready: /Users/smith/.brick/tmp/g2-provider-backed-20260630173157/export
copied files: 384
excluded paths matched: 4314
excluded roots: project/, brick_protocol.egg-info/
initial commit: ddf47f7
project scaffold: omitted; first onboard run creates project/
export top-level: AGENTS.md README.md agent/ brick/ link/ pyproject.toml support/
```

## Install / import / CLI smoke

Inside the fresh export:

```text
uv sync --quiet = PASS
brick_protocol import = PASS
python -m brick_protocol.support.operator.cli --help = PASS
```

The public `build` command exposed `--real-provider`, with the CLI help stating
that it uses the first ready provider-backed observed-write adapter unless an
explicit adapter is supplied.

## Provider readiness observation

Command:

```bash
PYTHONPATH=support/import_identity:. uv run python3 -m brick_protocol.support.operator.cli auth --json --non-interactive
```

Observed:

```text
doctor.all_ok = true
codex installed = ok, authed unknown
claude installed = ok, authed unknown
gemini CLI + API key env present = ok, credential_validity not_proven
local = ok
```

Proof limit: auth/doctor readiness is support evidence only; future provider
reliability and credential validity remain not_proven until a real run succeeds.

## Provider-backed build command

Executed in the fresh export:

```bash
PYTHONPATH=support/import_identity:. uv run python3 -m brick_protocol.support.operator.cli build \
  --json --non-interactive --real-provider \
  --building-id g2-provider-backed-fresh-export-20260630173226 \
  --task "Fresh export provider-backed first-run proof: return support evidence only and keep the result concise." \
  --preset building-chain-preset:design-contract-only \
  --timeout 180
```

Raw command output was saved at:

```text
/Users/smith/.brick/tmp/g2-provider-backed-20260630173157/provider-build.out
```

## Provider-backed build observation

```text
frontier_kind = complete
customer_visible_frontier_state = frontier_complete
customer_visible_not_ready = false
customer_visible_frontier_message = frontier complete: evidence closed for this Building. This remains support evidence, not source truth or quality judgment.
adapter_choice_basis = real-provider omitted --adapter; first ready observed-write adapter in declared order selected: adapter:claude-local
adapter_ref = adapter:claude-local
building_id = g2-provider-backed-fresh-export-20260630173226
chain_preset_ref = building-chain-preset:design-contract-only
repo_root = /Users/smith/.brick/tmp/g2-provider-backed-20260630173157/export
worktree_disposed = true
```

Materialized step adapters:

```text
design  = adapter:codex-local / model:codex:default
review  = adapter:gemini-local / model:gemini:default
closure = adapter:codex-local / model:codex:default
```

The evidence root exists at:

```text
/Users/smith/.brick/project/brick-protocol/buildings/g2-provider-backed-fresh-export-20260630173226
```

Observed evidence files include:

```text
capture/events.jsonl
evidence/evidence-manifest.json
raw/agent-return.jsonl
raw/brick-work.jsonl
raw/link.jsonl
raw/report-delivery.jsonl
raw/report-thread.jsonl
work/declared-building-plan.json
```

## Report / Slack observation

`raw/report-delivery.jsonl` records local-inbox delivery and Slack delivery
observations for the Building. The final `building_finished` event has both:

```text
sink_ref = report-sink:local-inbox, delivered = true
sink_ref = report-sink:slack, delivered = true, delivery_status_class = http_2xx,
provider_response_status_class = slack_ok_true
```

`raw/report-thread.jsonl` records a Slack parent observation with a channel ref
and message timestamp. This is support evidence only; reader notice and future
external delivery reliability remain not_proven.

## Narrowly proven

```text
- A fresh release export from the current checkout can install dependencies,
  import brick_protocol, and expose the public CLI.
- A real provider-backed `build()` run from that fresh export reached
  frontier_kind=complete.
- The first-run CLI result carried customer-visible frontier state/message:
  customer_visible_frontier_state=frontier_complete and customer_visible_not_ready=false.
- The run produced a Building evidence root with raw/evidence/work records.
- Slack delivery was observed for this run with http_2xx / slack_ok_true status
  classes, but only as support delivery evidence.
```

## Not proven / caveats

```text
- Full independent customer reading-comprehension is not proven; this proof only
  records customer-visible CLI output fields and evidence artifacts.
- Future provider reliability is not proven.
- Semantic quality of Agent returns is not proven.
- Production runtime behavior is not proven.
- The source checkout was dirty when exported; this is current working-tree
  evidence, not a clean-main release candidate.
- The proof used direct operator measurement, not a separate Building-produced
  patch.
- Source truth / success / quality / Movement authority remain not_proven.
```

## Next Movement candidate

Forward G2 provider-backed frontier proof as narrowly closed for the named
`frontier_kind=complete` gap. Remaining closeout work should proceed to G1 deep
L2 cascade replay / route comprehension, then MCP ai-cli diagnostic Building,
then final closeout once repo cleanliness, final audit, push/merge target, and
main=origin/main are proven.
