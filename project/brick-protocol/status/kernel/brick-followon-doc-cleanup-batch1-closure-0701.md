# Follow-On doc cleanup, batch 1 — closure (0701)

Status: COO closure for the first executed slice of the Follow-On doc/skill/
checker cleanup (item 4 of the Follow-On Goal bucket in
`brick-6-surface-audit-repair-goal-0630.md`). Not source truth, success
judgment, quality judgment, or Movement authority.

## What happened, in order

1. Discovery Building (`brick-followon-doc-skill-checker-catalog-0701a`,
   official route, 5-lane `design` fan-out -> `closure`) cataloged stale
   docs/skills/checkers. Discovery only, no edits.
2. A follow-up Workflow was dispatched to turn the catalog's flagged items
   into exact, execution-ready fix specs (13 targets, deep-dive + adversarial
   verify). **Process error**: the workflow's prompts said "produce a fix
   spec," not "do not edit files," and the dispatched agents had unrestricted
   Edit tool access against the shared live repo. Several agents directly
   edited `/Users/smith/projects/BRICK`'s working tree instead of only
   returning a proposed diff -- 8 files modified, 3 new files created,
   uncommitted. **Lesson for future workflow authoring**: when a workflow's
   job is investigation/spec-production only, its prompts must explicitly
   forbid file mutation (or use `isolation: 'worktree'` so any accidental
   edits land in a disposable sandbox instead of the live tree).
3. The uncommitted diff was captured onto a side branch
   (`followon-doc-review-wip-0701`, commit `94c8ad2`) without touching main,
   specifically so it could still go through proper Building QA before any
   adoption decision.
4. A QA review Building (`brick-followon-doc-diff-review-0701a`, official
   route, `code-attack-qa`/`axis-attack-qa`/`evidence-integrity` fan-out ->
   `closure`) independently re-verified the WIP diff against live code. Real
   catch: `agent/skills/building-sizing-method/SKILL.md`'s edit (factually
   correct, reflecting Rule 10) had removed text pinned by
   `support/checkers/profiles/coo_operating_chain.yaml` and
   `building_skill_preset_builder_composition.yaml` -- adopting it as-is
   would have broken 2 checkers. 10 of 11 files: adopt as-is; 1 file:
   adopt-with-fix.
5. 10 files committed to main (`cdb1259`) after an independent clean
   `check_profile.py --all` (30/30 PASS).
6. A small, precisely-scoped Building (`brick-followon-pin-sync-fix-0701a`,
   official route, `work` -> `closure`) applied the 11th file's corrected
   content AND updated the 2 checker pins atomically in one commit
   (`49c3279`), so main was never left in a state where the skill doc and its
   pins disagreed. Independently re-verified clean (30/30 PASS) after the
   Building's own sandboxed run hit the same known tmpdir environment
   artifact seen elsewhere this session (not a real defect).
7. Final combined sweep on main at `49c3279`: 30/30 PASS.

## What changed (customer-facing, per `release_export.sh`'s
`EXCLUDE_PATHS = ("project", "brick_protocol.egg-info")` -- everything below
ships in the release export)

- Corrected the "`--graph` is the customer route, `assemble()` is internal"
  staleness (now superseded by Rule 10) in: `architecture-map.md`,
  `README.md`, `setup.md`, `launch-guide.md`,
  `agent/skills/building-sizing-method/SKILL.md`.
- Fixed drifted measured counts in `checker-profile-map.md` (29->30 profiles,
  64->66 kernel checks, 140->162 module rows) and `agent-axis-detail.md`
  (3->5 tool policies).
- Fixed stale `observed-write`/`reviewer-readonly` taxonomy in
  `agent/skills/make-an-agent/SKILL.md` (now `read`/`probe_write`/
  `source_write`) -- resolves gap #4 from `brick-6-three-report-crosscheck-0701.md`.
- Split `README.md` (365 -> 108 lines) into 3 focused reference docs
  (`operator-status-inbox.md`, `release-and-deploy.md`,
  `repository-history-and-structure.md`), resolving GPT-Pro's F-14 finding.
- Synced 2 checker profile pins to the new correct framing.

## What was correctly rejected (not adopted)

- A proposed edit to `agent/skills/task_intake/SKILL.md` naming `fire()` as
  an "official" launch route -- adversarially rejected by the fix-spec
  workflow's own verify stage as factually wrong (contradicts
  `brick-task-author/SKILL.md`'s explicit prohibition on naming `fire()` to
  operators) before it ever reached the live repo. Independently confirmed
  this file was never modified.
- `brick-grounding-map.md`'s proposed fix -- the verify stage found the
  proposal's premise was already stale by the time it ran (a moot/timing
  issue, not a wrong claim); not pursued further this batch.
- `AGENTS.md` -- explicitly kept out of any execution Building per its own
  "constitutional text" status; needs direct Smith sign-off before any edit,
  not a COO/Building-level decision.

## Remaining from the original catalog (deferred, low urgency)

- `rules-and-boundaries.md` fixes (deep-dive found nothing concretely wrong
  after a thorough read).
- The 144 kernel status docs (`project/brick-protocol/status/kernel/*.md`,
  NOT customer-facing, excluded from release export entirely) -- archive/
  index strategy proposed, not deletion; low priority.
- God-module decomposition (`kernel_checks.py`, `case_runners.py`,
  `check_bounded_agent_proposed_routing_loop0.py`) -- unchanged, still
  Follow-On item 1.
- `--graph` CLI-flag retirement execution -- unchanged, still blocked on the
  2 confirmed DSL gaps (Follow-On item 2).

## Repo state

- `git status --short` at close: clean.
- `git log -1`: `49c3279`.
- Not yet pushed to `origin/main` -- pending explicit Smith authorization
  for this batch specifically (a standing question from this session: does
  routine kernel/doc-only push authorization carry across turns, or does
  each batch need fresh confirmation).
