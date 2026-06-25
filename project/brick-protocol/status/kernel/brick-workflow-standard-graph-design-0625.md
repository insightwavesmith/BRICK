## 1. Workflow UX

BRICK should present the standard workflow as a Claude Workflow-style board, but
with Brick / Agent / Link meaning visible at every boundary:

- Every workflow node is a Brick: the node declares work, required return shape,
  performer lane need, write need, and comparison rule.
- Every performer is an Agent: the node binds an Agent Object, adapter ref,
  tool-policy refs, discipline refs, and a closed AgentFact return.
- Every edge is Link: transfer, carry, gate sufficiency, Movement, transition,
  HOLD, and reroute are Link-owned facts, never provider or checker decisions.
- Every run leaves Building evidence: `capture/`, `raw/`, `evidence/`, and
  `work/step-outputs/` remain the support record for what was walked.

The product rule is: no naked prompt, no naked agent, no naked checker, no naked
script, and no naked workflow. A user may experience a workflow board, but the
board is only a support projection over declared Brick nodes, Agent performers,
and Link edges.

This report is support evidence only. It is not source truth, not a success
judgment, not a quality judgment, and not Movement authority.

## 2. BAL mapping table

| Workflow surface | Brick mapping | Agent mapping | Link mapping | Support/evidence mapping |
| --- | --- | --- | --- | --- |
| Node | Brick work boundary with `step_template_ref`, contract, source facts, and return template | Selected Agent Object, adapter, model ref, prompt, disciplines, tool policy | Incoming/outgoing Link rows name the declared Movement and target | Building map, declared plan, step output, raw Brick work |
| Performer | Brick declares lane and write need only | Agent owns receipt and returned fact | Agent return may carry non-binding transition concern evidence only | Adapter usage and raw Agent return records |
| Edge | No route authority | No route authority | Transfer, carry, GateFact sufficiency, MovementFact, TransitionFact | `raw/link.jsonl`, claim trace, spine projection |
| Gate | Brick contract is checked as public fact input | Agent does not self-classify | Gate reports sufficiency only; it does not judge quality or choose among undeclared targets | Gate receipt and sufficiency claim traces |
| HOLD/reroute | Brick boundary is the target of any declared reroute | Agent may describe concern, not choose route | Link lifecycle pauses/resumes and uses only `forward` / `reroute` Movement | Frontier observation and transition lifecycle evidence |
| Report/dashboard | Not source truth | Not Agent source truth | Not Movement authority | Read-side support projection over recorded evidence |

## 3. Design-first policy

Use design-first when the task needs structure before implementation: new
workflow shape, new customer path, admission-risky protocol wording, provider
lane changes, or unclear fan-out/fan-in behavior. Use task-first presets when
the task is already clear and the write scope is narrow.

The completed `brick-workflow-standard-graph-design-0625` Building bounded this
design direction but did not author this file in the visible checkout. Its
status inbox records show the Building walked plan, review, and closure steps,
but the shared Building root named in those events was not present in this
worktree filesystem during this authoring pass. That absence is a proof limit,
so this report relies on current repo-local status records, presets, checker
profiles, and commit evidence.

Design output remains proposal/support evidence until a later Building admits
changes to active contracts, presets, checkers, docs, or code.

## 4. Recommended standard graph

The standard graph for BRICK-style Claude Workflow should be:

```text
Design Brick -> COO middle review/gate -> Work Brick -> QA fan-out -> Closure Brick
```

Recommended node responsibilities:

- Design Brick: writes the proposed workflow contract, BAL boundaries, write
  scope needs, QA lanes, reroute concerns, and checker expectations. It does no
  implementation unless the Brick kind explicitly admits it.
- COO middle review/gate: records caller/COO adoption, narrowing, or HOLD before
  any write Brick opens. This is the human/COO disposition point for high-impact
  design changes.
- Work Brick: performs the scoped implementation or document edit inside the
  declared write scope. It is the only default write node.
- QA fan-out: independent read-only review lenses inspect structure, broad
  behavior, and axis/boundary risk. Fan-out sibling evidence must be independent.
- Closure Brick: synthesizes recorded evidence, unresolved deltas, and declared
  next-Building candidates without judging quality or choosing undeclared routes.

Current repo evidence already has a nearby declared graph example in
`brick/templates/presets/four-llm-standard-graph.md`: one Codex work root fans
out to Claude, Gemini, and Fugu read-only review lenses, then fans in to closure.
That preset is useful evidence, but it is not the whole recommended standard
because this report adds the explicit design and COO middle-gate front half.

## 5. Claude execution-QA placement after ec43f0b

Commit `ec43f0b` repaired the Claude local adapter boundary by passing
`--allowedTools` alongside `--tools` for allowed Claude tool sets. The current
code in `support/connection/adapter_local_cli.py` appends
`--allowedTools <allowed_tools>` when `allowed_tools` is present, and
`support/checkers/lib/kernel_checks.py` rejects omission or drift between
`--tools` and `--allowedTools`, including absence of `Bash`.

Commit `ac73c86` added the fresh support record
`project/brick-protocol/status/kernel/claude-qa-execution-fresh-smoke-0625.md`.
That record states the target failure mode: Claude QA had reported harmless
shell/checker execution as approval-gated even when effective write scope and
Bash were intended to be available. It also records local command observations
and keeps provider behavior as not proven.

Therefore Claude execution-QA belongs in the QA fan-out after the Work Brick,
not as a naked checker or naked Claude prompt. It should be one declared QA node
with Agent, adapter, tool-policy, and Link boundaries recorded. Its evidence can
support adapter/runtime observations; it must not become provider proof,
success judgment, quality judgment, or Movement authority.

## 6. Link/HOLD/reroute policy

The standard graph should use Link-owned transition language only:

- `forward`: continue on the current declared road.
- `reroute`: move to another declared Brick boundary.
- `paused` / `resumed`: lifecycle states for transition holds.
- `raise`, `forward`, `stop`, `reroute`: disposition actions only when recorded
  by human/COO disposition rows.

GateFact reports sufficiency for required public facts. It does not select
among multiple candidate Buildings, invent targets, judge quality, or classify
Agent returns as success/failure.

Recommended graph policy:

- Design -> COO middle review uses a human/COO gate for adoption before any
  write scope opens.
- Work -> QA fan-out uses strict/default declared gates over recorded work
  evidence.
- QA fan-out -> Closure waits for all declared QA branches or records HOLD with
  explicit frontier evidence.
- Closure may propose next Building candidates as support evidence, but any
  reroute must target a declared Brick boundary and obey bounded budgets.
- Implementation gaps reroute to the Work Brick only when declared by route
  policy; verification gaps HOLD for caller/COO disposition.

## 7. Per-phase checker/profile expectations

Checker/profile output is support evidence only. It is not source truth, not
success judgment, not quality judgment, and not Movement authority.

Expected per-phase checks:

| Phase | Minimum verifier expectation |
| --- | --- |
| Design Brick | Read governing preset/shape/checker surfaces; run targeted profile only if design edits touch a checked support surface; otherwise record current repo evidence and proof limits. |
| COO middle review/gate | Verify no active contracts, AGENTS.md, Movement, gate, adapter, or checker profile changed without explicit human/COO disposition. |
| Work Brick | Run `git diff --check`; run the narrow profile that covers the touched surface; for workflow/preset changes include `building-skill-preset-agent-tool-hardening` or the relevant graph/routing profile. |
| QA fan-out | Each branch runs its declared lens checks independently and records missing provider/tool evidence as proof limits, not verdicts. |
| Closure Brick | Re-read changed files, status records, and step outputs; record remaining not-proven items and any declared next-Building candidates. |

Current evidence: `broad-profile-drift-triage-0625` found preset-count drift
after the preset catalog reached 28 files. Commit `9858c72` repaired fixture
coverage in `support/checkers/lib/case_runners.py` and
`support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml`,
keeping strict completion behavior instead of accepting `agent_incomplete` as
closure for the preset fixture gap. The current checkout has 28 preset markdown
files under `brick/templates/presets/`.

## 8. Concrete next-Building plan to P7 customer dogfood

Use this report as the support design input for the next declared Building
sequence:

1. Design-adoption Building: COO/human reviews this report and either adopts the
   standard graph, narrows it, or records HOLD. No code changes.
2. Preset-design Building: draft a standard graph preset or preset delta for
   `Design Brick -> COO middle review/gate -> Work Brick -> QA fan-out ->
   Closure Brick`, reusing the existing `four-llm-standard-graph` evidence where
   possible. Write scope should be limited to the admitted preset/status files.
3. Checker-first Building: update or select the profile coverage before any
   active preset change lands. Include negative probes for naked prompt/agent/
   checker/script/workflow shortcuts if a checker gap is found.
4. Customer dogfood Building: run a narrow customer-like task through the adopted
   graph with one Work Brick and QA fan-out. Record Building evidence and keep
   provider availability, provider quality, customer comprehension, and Slack
   delivery as not proven unless separately observed.
5. Closure Building: synthesize evidence for P7 customer dogfood, listing
   changed files, commands, frontier state, unresolved proof limits, and any
   declared follow-on Building candidates.

The next plan should not mutate `AGENTS.md`, active BAL contracts, adapter
behavior, Movement literals, or checker profiles without an explicit admitted
Building and human/COO disposition.
