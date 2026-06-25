# Checker Profile Diet Selector Guide (P5 Slice)

Generated at: 2026-06-25

## Scope

- This is a support status note for `checker-module-diet-codex-slice-0625`.
- It narrows operator use of existing checker profiles so COO work does not default to `--all`.
- It reads the existing measurement table at `project/brick-protocol/status/kernel/checker-profile-diet-measurement-0625-profile-table.md`.
- It does not rename, delete, or weaken any profile.
- It is not source truth, not success judgment, not quality judgment, and not Movement authority.

## Boundary Check

```text
Evidence first: use the measured profile table before choosing a checker run.
Brick candidate: no Brick contract or Building Plan change in this slice.
Agent candidate: no Agent resource change in this slice.
Link candidate: no Link Movement, gate, or route change in this slice.
Support surface: status/kernel operator selector guidance only.
Rejected shortcut: profile YAML taxonomy metadata, because check_profile.py rejects unknown top-level keys.
Chosen repair surface: support status note that preserves the measured candidate buckets as non-authoritative evidence.
Verification before Movement: run targeted profiles plus git diff --check when edits occur.
```

## Selector Lanes

Use these lanes as an operator shortcut over the measured candidate buckets.
They are not an admitted taxonomy and do not change checker behavior.

| Lane | Use when | Profiles from current measurement |
|---|---|---|
| quick/core | Need cheap axis, profile, and single-source guard evidence before ordinary support edits. | `core`, `adapter-usage-meter`, `agent-object-schema-single-source`, `chained-carry-dependency`, `charter-injection`, `cli-runner-stdin-devnull`, `driver-public-intake-seal`, `gate-registry-single-source`, `return-field-merge-set-parity`, `tier-a-three-axis-conformance` |
| dogfood/behavioral | Need Building evidence, routing loop, assembly, or template behavior evidence for operator/dogfood work. | `assembly-equivalence`, `bounded-agent-proposed-routing-loop`, `building-automation`, `coo-operating-chain`, `link-routing-behavioral`, `native-dispatch-brick-backstop`, `structure-template-integrity` |
| live-heavy/provider | Need provider, onboarding, MCP, dashboard, projection, or environment-seam evidence and have chosen to pay that cost. | `agent-axis-behavioral`, `brick-cli-entrypoint`, `building-operator-driver0`, `mcp-dispatch-wire`, `read-side-projection-boundary`, `report-env-autoload` |
| oversized/history | Need the consolidated historical/template hardening slice specifically. | `building-skill-preset-agent-tool-hardening` |

## Default Commands

For a small checker/profile diet or support-only edit, prefer:

```bash
PYTHONPATH=.:support/import_identity python3 support/checkers/check_profile.py --profile core
PYTHONPATH=.:support/import_identity python3 support/checkers/check_profile.py --profile return_field_merge_set_parity
git diff --check
```

For routing or Building behavior work, add the relevant dogfood profile instead
of `--all`, for example:

```bash
PYTHONPATH=.:support/import_identity python3 support/checkers/check_profile.py --profile link_routing_behavioral
PYTHONPATH=.:support/import_identity python3 support/checkers/check_profile.py --profile bounded_agent_proposed_routing_loop
```

Run `--all` only when the task explicitly needs broad consolidation evidence,
live/provider seam evidence, or release-style support proof. A green `--all`
run remains support evidence only.

## Not Proven

- These lanes are not admitted profile schema fields.
- Runtime cost is not measured here.
- Selector references outside the measurement table were not re-scanned here.
- Full checker consolidation is not proven.
- `--all` green is not proven by this note.
