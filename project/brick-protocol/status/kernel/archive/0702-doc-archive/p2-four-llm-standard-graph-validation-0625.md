# P2 Four-LLM Standard Graph Validation

This report is provider-neutral Brick Protocol support evidence only. It is not
source truth, not a quality judgment, not a success judgment, and not Movement
authority.

## Current Repo Evidence

- HEAD observed before writing this report:
  `14862a89bbc3ac2ebfa78001a5e9bb379a8ab295`
- `git status --porcelain` before writing this report: no output observed.
- Declared write target for this Work Brick:
  `project/brick-protocol/status/kernel/p2-four-llm-standard-graph-validation-0625.md`
- Declared constraints for this Work Brick allowed exactly this status file and
  forbade code, checker/profile, `AGENTS.md`, `brick/`, `agent/`, `link/`, and
  `support/` edits.

## Graph / Preset Used

Exact graph/preset observed and planned:

```text
building-chain-preset:four-llm-standard-graph
brick/templates/presets/four-llm-standard-graph.md
```

Current preset frontmatter declares:

- common basis: `building-chain-preset:triage-fanout-3`
- shape: `building-shape:design-needed`
- intent: one Codex implementation root fans out to three read-only review
  lenses, then fans in to one closure synthesis.
- graph topology:
  - `building-step-template:work -> claude-structure-qa`
  - `building-step-template:work -> gemini-broad-review`
  - `building-step-template:work -> fugu-axis-attack`
  - `claude-structure-qa -> closure`
  - `gemini-broad-review -> closure`
  - `fugu-axis-attack -> closure`
- fan-out group: work root to the three review/inspect lanes.
- fan-in group: the three review/inspect lanes converge on `closure`.
- terminal: `closure`.
- node reroute budget: `building-step-template:work: 1`.
- gate concept profile: `strict-evidence`, `fan-in-wait-all`.

Repo-local prior smoke evidence exists at:

```text
project/brick-protocol/buildings/four-llm-standard-graph-readonly-smoke-0625/
```

Its declared plan records `chain_preset_ref:
building-chain-preset:four-llm-standard-graph`, execution order
`work`, `claude-structure-qa`, `gemini-broad-review`, `fugu-axis-attack`,
`closure`, a fan-out link group from work to the three lenses, and a fan-in link
group from the three lenses to closure.

## BAL Mapping Observed / Planned

| Node | Brick row | Agent row | Link row | Write/read tier observation |
| --- | --- | --- | --- | --- |
| `work` | `building-step-template:work`; `requires_brick_write_scope: true`; return shape `made_changes, observed_evidence, not_proven` | `agent-object:dev`; `tool-policy:read-write-scoped`; selected adapter `adapter:codex-local`; model `model:codex:default` | declared forward edges to `claude-structure-qa`, `gemini-broad-review`, and `fugu-axis-attack`; `link-gate:default-transition` | This Work Brick has a declared write scope limited to this status file; with read-write policy and `adapter:codex-local`, effective write is observed for this file only. |
| `claude-structure-qa` | `building-step-template:review`; read-only review contract; return shape includes checked work/sources, matches/mismatches, boundary observations, evidence used, narrowly proven, not proven | `agent-object:qa-lead`; `tool-policy:leader-coordination` plus `tool-policy:read-write-scoped`; selected adapter `adapter:claude-local`; model `model:claude:inherit` | forward edge to `closure`; `link-gate:default-transition` | No Brick write scope is declared for this node in the preset/readonly smoke plan; write-capable policy remains capability only, so read-only tier is the planned/observed tier. |
| `gemini-broad-review` | `building-step-template:inspect`; read-only inspect contract; return shape includes inspected scope, matched/missing/mismatched facts, boundary findings, observed evidence, not proven | `agent-object:inspector`; `tool-policy:read-write-scoped`; selected adapter `adapter:gemini-local`; model `model:gemini:default` | forward edge to `closure`; declared gates include `link-gate:default-transition` and, in smoke plan, `link-gate:strict` from strict-evidence provenance | Gemini is described by AGENTS as a read/review adapter sibling, not a write adapter. No Brick write scope is declared for this node; read-only tier only. |
| `fugu-axis-attack` | `building-step-template:inspect`; read-only inspect contract; return shape includes inspected scope, matched/missing/mismatched facts, boundary findings, observed evidence, not proven | `agent-object:inspector`; `tool-policy:read-write-scoped`; selected adapter `adapter:codex-fugu-local`; model `model:sakana:fugu` | forward edge to `closure`; declared gates include `link-gate:default-transition` and, in smoke plan, `link-gate:strict` from strict-evidence provenance | `adapter:codex-fugu-local` is write-capable as technical capability, but no Brick write scope is declared for this read-only inspect node; read-only tier only. |
| `closure` | `building-step-template:closure`; closure synthesis contract; return shape includes observed evidence, narrowly proven, not proven, remaining delta, parent goal delta status, next target candidates, deferred review queue, non-binding transition concern evidence | `agent-object:coo`; `tool-policy:leader-coordination`; selected adapter `adapter:claude-local`; model `model:claude:inherit` | forward edge to `building-boundary:<building-id>-closed`; `link-gate:default-transition`; lifecycle state may close the declared boundary | COO carries no read-write-scoped policy in `agent/objects/coo.yaml`; closure is read-only synthesis and may not judge quality, choose Movement, or author routes. |

## Permission Matrix

Effective write is the intersection of Brick write need, Agent tool policy,
adapter capability, and write observation. Adapter identity alone is not enough.

| Node | Brick write_scope need | Agent tool_policy_refs | Adapter capability observation | Effective tier |
| --- | --- | --- | --- | --- |
| `work` | yes, this Work Brick only: one allowed status file | `tool-policy:read-write-scoped` | `adapter:codex-local` is in the observed-write-capable set in support connection logic | effective write for the declared status file; read allowed for repo evidence |
| `claude-structure-qa` | no write scope in preset/readonly smoke plan | `tool-policy:leader-coordination`, `tool-policy:read-write-scoped` | `adapter:claude-local` may be write-capable only when effective-write gates open | read-only tier because Brick write need is absent |
| `gemini-broad-review` | no write scope | `tool-policy:read-write-scoped` | `adapter:gemini-local` is read/review; Gemini is not the write lane | read-only tier |
| `fugu-axis-attack` | no write scope | `tool-policy:read-write-scoped` | `adapter:codex-fugu-local` is write-capable technical capability | read-only tier because Brick write need is absent |
| `closure` | no write scope | `tool-policy:leader-coordination` | `adapter:claude-local`; COO object does not carry read-write-scoped | read-only tier |

## Commands / Checks Run

```text
pwd && rg --files -g 'SKILL.md' agent/skills | sort
```

Observed: repo root `/Users/smith/.brick/worktrees/struct-surgery-0623`; declared
skills `agent/skills/scoped-implementation/SKILL.md` and
`agent/skills/protocol-boundary-watch/SKILL.md` were present and read.

```text
git status --porcelain && git rev-parse HEAD
```

Observed: no porcelain output; HEAD
`14862a89bbc3ac2ebfa78001a5e9bb379a8ab295`.

```text
git diff --check
```

Observed: no output; command exited `0`.

```text
uv run python3 support/checkers/check_profile.py --profile building_skill_preset_agent_tool_hardening
```

Observed: command exited `1`. The profile runner reached
`preset_building_completion_case` and reported:

```text
profile runner rejected evidence: preset_building_completion_case rejected all-current-presets-slack-alert/building-chain-preset:four-llm-standard-graph: frontier_kind expected 'complete', observed 'agent_incomplete'
proof limit: profile runner support evidence only; checker/profile pass does not prove source truth, success judgment, quality judgment, Movement authority, provider behavior, or complete checker consolidation.
```

This is recorded as current support evidence for a missing/incomplete fixture
closure around `building-chain-preset:four-llm-standard-graph`, not as a quality
or Movement judgment.

Additional repo reads used for this report:

- `brick/templates/presets/four-llm-standard-graph.md`
- `project/brick-protocol/buildings/four-llm-standard-graph-readonly-smoke-0625/work/declared-building-plan.json`
- `project/brick-protocol/status/kernel/brick-workflow-standard-graph-design-0625.md`
- `agent/tool_policies/read-write-scoped.yaml`
- `agent/objects/dev.yaml`
- `agent/objects/qa-lead.yaml`
- `agent/objects/inspector.yaml`
- `agent/objects/coo.yaml`
- support connection references found by `rg` for effective-write and adapter capability wording.

## Claude Execution-QA Placement Observation

`project/brick-protocol/status/kernel/brick-workflow-standard-graph-design-0625.md`
records that after commits `ec43f0b` and `ac73c86`, Claude execution-QA belongs
inside the QA fan-out after the Work Brick, as a declared QA/review node with
Agent, adapter, tool-policy, and Link boundaries. It should not be treated as a
naked checker or naked Claude prompt.

This description remains consistent with the current `four-llm-standard-graph`
pattern: Claude structure QA is a declared read-only review lane after the Work
Brick and before closure. The current Work Brick did not execute Claude provider
QA directly; provider execution behavior remains not proven here.

## Known Proof Limits / Not Proven

- The required `building_skill_preset_agent_tool_hardening` profile did not exit
  green in this run; it reported `agent_incomplete` for
  `building-chain-preset:four-llm-standard-graph`.
- Current work did not run live Claude, Gemini, or Sakana/Fugu provider calls.
- Current work did not run the full graph through `support/operator/run.py` or
  `support/operator/dynamic_walker.py` from intake to closure; it inspected the
  current preset and existing readonly smoke evidence.
- Existing smoke evidence proves repo-local declared plan shape and recorded
  step-output files exist; it does not prove provider quality, provider
  reliability, scheduler behavior, or real parallel fan-out.
- Checker/profile output is support evidence only and does not prove source
  truth, quality, success, Movement authority, or complete coverage.
- The current report does not resolve the profile fixture/frontier mismatch; the
  Building write scope forbids checker/profile changes.
- `transition_concern_evidence` semantics from future provider returns remain
  not proven.
- Slack/dashboard/report sink delivery reliability remains not proven.

## Next Phase Recommendation Toward P3 / P4 / P7

- P3: Treat the observed profile rejection as a concrete support-evidence item:
  inspect `preset_building_completion_case` and the current-preset fixture path
  for `building-chain-preset:four-llm-standard-graph`, then decide whether a
  checker fixture, completion evidence, or preset evidence update is the admitted
  next work. Keep the change checker-first and scoped.
- P4: If the standard graph is adopted for broader dogfood, run a declared
  repair/validation Building that either records complete frontier evidence for
  the four-LLM preset or narrows the profile expectation. Do not silently relax
  strict completion behavior.
- P7: Use `building-chain-preset:four-llm-standard-graph` for a customer-like
  dogfood only after the profile evidence gap is addressed or explicitly carried
  as a proof limit. The graph should keep exactly one write node, independent
  read-only QA fan-out, and closure synthesis without quality/success/Movement
  authority.
