# Task #9 implementation Building closure — mixed disposition (0701)

Status: support evidence for the `brick-6-dual-producer-impl-0701a` Building
(3 parallel work lanes: A=stale text, B=doc reconciliation, C=dead-code
chain deletion). Not source truth, success judgment, quality judgment, or
Movement authority. `frontier_kind=complete` at the Building level, but this
closure applies a PARTIAL adoption -- do not read Building-level completion
as "all 3 lanes landed."

## Why partial adoption

Global Operating Rule 10 (assemble() DSL becomes official, `--graph`
discarded) landed in the goal document WHILE this Building was already
in flight. Lane B's task instructions were written before Rule 10 and
encode the now-superseded framing ("`--graph` is the customer route,
`assemble()` is operator-only, not customer-facing"). Rather than kill the
running process (judged riskier given today's repeated process-management
incidents), the Building was allowed to finish naturally; this document
records the resulting per-lane adoption decision.

## Lane A -- ADOPTED

- Scope: retire the stale "future assembly.py lowering" framing in
  `support/checkers/check_assembly_equivalence.py` (module docstring +
  argparse `--help` text) and `support/checkers/profiles/assembly_equivalence.yaml`.
- Result: clean, small, exactly in scope. Independently re-verified
  (Claude): `py_compile` PASS, focused `assembly_equivalence.yaml` profile
  PASS (both in the sandbox worktree and again after copying to main),
  `git diff --check` PASS.
- Adopted to main as commit `b1619c2`.
- Not affected by Rule 10 (this lane is about engine canonicity, settled
  separately by Rule 9 / `brick-6-dual-producer-reconciliation-synthesis-0701.md`).

## Lane B -- REJECTED, not adopted

- Scope (as originally instructed, now stale): reconcile
  `agent/skills/brick-task-author/SKILL.md` /
  `brick/templates/skills/brick-task-author/SKILL.md` /
  `support/docs/references/launch-guide.md` to state `brick build --graph`
  is the customer route and `assemble()`/`build()` is operator-only, not
  customer-facing.
- Why rejected: this directly contradicts Global Operating Rule 10 (Smith
  0701, landed mid-flight): `assemble()`/`build()`/`fan()` is now the
  OFFICIAL construction/launch interface; `--graph` is headed for
  retirement (execution deferred, see rule 10's own text and the
  "Follow-On Goal" section). Adopting Lane B's diff would enshrine the
  wrong hierarchy into exactly the skill file this session used to learn
  the correct one.
- Disposition: worktree discarded after extracting only Lane A's files.
  Lane B's actual diff was never copied to main -- nothing to revert.
- Follow-on: when the "Follow-On Goal" architecture-cleanup pass (deferred
  to post-deployment, same bucket as god-module decomposition and the
  `--graph` retirement execution) picks this up, redo this reconciliation
  with the CORRECT framing: `assemble()`/`build()`/`fan()` is the official
  authoring/launch interface; `--graph` is being phased out (blocked on
  the DSL's `sibling_independence` gap closing first).

## Lane C -- STOPPED HONESTLY, not adopted, no changes made

- Scope: delete the confirmed-dead 3-function chain
  `render_declared_building_plan()` -> `render_declared_step_template_plan()`
  -> `coo_run_orchestration_packet()`, plus re-exports, checker self-tests,
  and the MCP projection string reference.
- Result: `made_changes=false`. The lane independently re-ran the
  repo-wide grep (as explicitly instructed, checker-first) and found MORE
  references than the task premise accounted for -- not live code callers,
  but textual references in `agent/prompts/coo.md:124`,
  `agent/skills/building-coordination/SKILL.md:188`,
  `agent/skills/task_intake/SKILL.md:355`,
  `support/checkers/profiles/coo_operating_chain.yaml:303,316,321`,
  `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:4129,4153`,
  `support/checkers/module_registry.yaml:991,1367`,
  `support/connection/mcp_projection.py:338`,
  `support/operator/native_dispatch.py:777`,
  `support/operator/composition_compose.py:91`. It correctly returned
  `implementation_gap` and stopped rather than deleting on an incomplete
  premise -- this is the checker-first discipline working as designed, not
  a Building defect.
- **The Building's own closure step's classification of this evidence is
  NOT independently confirmed and should not be trusted as-is**: closure
  claimed "`render_declared_building_plan` is not dead code... remains
  imported/called/exported in active support surfaces" and
  "`render_declared_step_template_plan` has active references across
  projection, case runners, and guides" -- but closure also mislabeled
  which lane was which (called Lane A's file set "Lane B" and vice versa
  in its own narrative), so its reasoning quality here is suspect. Most of
  Lane C's own found references (prompts, SKILL.md, checker-profile YAML
  string literals, a native_dispatch.py comment, a composition_compose.py
  comment) LOOK like textual mentions, not actual `import`/call dependents
  -- but this needs independent re-verification, not COO assumption
  either way, before any future deletion attempt.
- Follow-on: a corrected Lane C attempt needs to (a) independently classify
  each of the 13 newly-found references as a real dependency vs. a
  harmless textual mention, (b) clean up the harmless mentions alongside
  the deletion if proceeding, (c) re-confirm `coo_run_orchestration_packet`
  specifically (closure's own text agreed this one has no active internal
  callers) as the safest partial-scope starting point if a narrower first
  cut is preferred over the full 3-function chain at once.

## Proof limits

- Building-level `frontier_kind=complete` reflects the graph's own
  termination, not "all lane objectives achieved" -- read per-lane
  disposition above, not the Building-level status alone.
- No claim of task #9 or Global Operating Rule 9/10 full closure. Rule 9
  (engine canonicity) remains resolved separately. Rule 10 (DSL becomes
  official) direction is decided but execution (including Lane B/C
  follow-ups) remains explicitly deferred per Smith's 0701 disposition.
