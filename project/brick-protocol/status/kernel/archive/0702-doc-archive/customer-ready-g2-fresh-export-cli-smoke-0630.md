# Customer-Ready G2 — Fresh export CLI smoke — 0630

Status: support evidence only / operator measurement. Not source truth, not
success judgment, not quality judgment, and not Link Movement authority.

## Why this slice exists

The closeout goal requires customer release pruning finalization. Earlier G2
checks proved export structure and literal cleanliness. This slice measures the
current public release export from `origin/main` after the G1 skill/doc sync,
then checks whether the exported tree can install, import, verify, and run the
first documented build path.

## Export measurement

Fresh export path:

```text
/Users/smith/.brick/tmp/g2-fresh-export-0630/export
```

Observed:

```text
copied files: 380
excluded roots: project/, brick_protocol.egg-info/
excluded path matches: 4303
top-level: AGENTS.md README.md agent/ brick/ link/ pyproject.toml support/
operator literal grep outside README: clean
```

## Install / import / verify smoke

Inside the fresh export:

```bash
uv sync --quiet
PYTHONPATH=support/import_identity:. uv run python3 - <<'PY' ... import brick_protocol ... PY
PYTHONPATH=support/import_identity:. uv run python3 -m brick_protocol.support.operator.cli --help
PYTHONPATH=support/import_identity:. uv run python3 -m brick_protocol.support.operator.cli verify --non-interactive --profile support/checkers/profiles/read_side_projection_boundary.yaml --json
```

Observed:

```text
uv sync: PASS
brick_protocol import: PASS
CLI help: PASS
brick verify read_side_projection_boundary: checker_exit_code=0
```

## Build smoke finding

The README/quickstart first-build path was measured in the same fresh export:

```bash
brick build --task "첫 실행을 support evidence only로 기록해 주세요." \
  --preset building-chain-preset:design-contract-only \
  --adapter adapter:local \
  --timeout 20
```

Observed structured result:

```text
frontier_kind = agent_incomplete
customer_visible_frontier_state = not_ready
materialized_step_adapters = codex-local / gemini-local / codex-local
```

The onboarding local preset variant was also measured:

```bash
brick build --preset building-chain-preset:onboarding-example-graph \
  --adapter adapter:local --timeout 30
```

Observed:

```text
frontier_kind = agent_incomplete
customer_visible_frontier_state = not_ready
materialized_step_adapters = codex-local / gemini-local / codex-local
```

Interpretation: current materialization correctly refuses `adapter:local` for
verdict-bearing design/review/closure lanes and floors them to provider-backed
adapters. Therefore the previous docs were too green when they implied a
provider-free local first build would complete quickly. The honest customer story
is:

```text
provider-free: uv sync / import / brick verify / doctor readiness can pass
provider-free build with verdict lanes: may return agent_incomplete/not_ready
provider-backed build: requires auth/readiness and remains separate proof
```

## Changed docs

To align customer-facing docs with the measurement, this slice updates:

```text
README.md
support/docs/references/quickstart.md
support/docs/references/launch-guide.md
```

The docs now teach that `adapter:local --timeout 20` is a support-evidence check
and can return `agent_incomplete`/`not_ready`; only `frontier_kind=complete` is a
customer-visible closure. `brick verify` is the provider-free green check.

## Narrowly proven

- Current release export can sync dependencies, import `brick_protocol`, show CLI
  help, and run `brick verify` for `read_side_projection_boundary` successfully.
- Export structure/literal cleanliness still holds.
- Customer docs no longer overclaim provider-free build completion.

## Not proven / remaining G2 work

```text
- A real provider-backed fresh export build reaching frontier_kind=complete was
  not re-run here.
- Full customer comprehension remains not_proven.
- This was direct operator maintenance, not a Building-produced patch.
```

## Next Movement candidate

Forward this G2 docs/measurement slice after verification. Remaining closeout
work should proceed to G3 FINAL architecture leaf extraction or a provider-backed
fresh-export build proof if Smith wants G2 fully closed before G3.
