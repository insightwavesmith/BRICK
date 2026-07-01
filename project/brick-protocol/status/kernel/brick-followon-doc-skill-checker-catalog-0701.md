# Follow-On doc/skill/checker discovery catalog (0701)

Status: COO adoption of a 5-lane discovery Building
(`brick-followon-doc-skill-checker-catalog-0701a`, `frontier_kind=complete`).
Discovery only, no source mutation (no write=True node in this graph). Not
source truth, success judgment, quality judgment, or Movement authority.
Written to inform the Follow-On goal's phase structure before it is authored.

## Building

- `assemble()`/`build()`/`fan()`, official route, per Rule 10.
- Shape: `fan([5 independent design-kind lanes]) -> closure`.
- Evidence root: `/Users/smith/.brick/project/brick-protocol/buildings/brick-followon-doc-skill-checker-catalog-0701a`.
- 6/6 nodes returned, `frontier_kind=complete`.

## Lane 1 — Skills (`agent/skills/*`, 17 files)

5 flagged `update_needed`: **brick-task-author**, **building-sizing-method**,
**evidence-verification**, **make-an-agent**, **task_intake**.

New measurements beyond what was already known:
- Active preset count is **28**, not 26 (some skill docs cite the old number).
- `support/operator/assembly.py` defines `build()`, `fan()`, `assemble()`,
  AND `fire()` — some skill docs list an incomplete surface.
- `support/operator/building_operation_common.py` indexes
  `DECLARED_GATE_REFS[0..3]` for `DEFAULT_LINK_GATE_REF`/
  `COMPACT_LINK_GATE_TOKENS` — worth confirming this stays in sync with
  `link/gate.py`'s derivation if gate refs ever change count.
- A path mismatch: `status/kernel/evidence-postmortem-task-template-0612.md`
  (cited in a skill) does not exist; the real path has a `project/`
  prefix. Small but a real broken reference.

## Lane 2 — References (`support/docs/references/*.md`, 13 files)

5 `update_needed`, 2 `no_update_observed` sampled explicitly, rest not
individually flagged as urgent:
- **architecture-map.md**: confirmed stale as expected (lines 154-184,
  `--graph`-as-customer-route framing) -- **plus a NEW finding**: the file is
  internally self-contradictory. Line 63 calls `assembly.py` "the refined
  3-axis `assemble()` customer front door," while lines 180-184 call
  `assemble()` "helper/advanced/internal." Both cannot be true; today's Rule
  10 resolves this in favor of line 63's framing, meaning lines 180-184 (not
  line 63) are the part to fix.
- **agent-axis-detail.md**: lines 42-63 say 3 tool policies exist; actual
  current count is 5 (`agent/tool_policies/*.yaml`).
- **brick-grounding-map.md**: several embedded line-number citations have
  drifted from actual current file positions (grep-recipe approach is still
  useful, exact line coordinates are not).
- **checker-profile-map.md**: says 29 profiles / 64 kernel checks / 140
  module rows; actual current counts are **30 / 66 / 162**. Also contains a
  stale claim that `bounded_agent_proposed_routing_loop` has only
  `package_path_admission` coverage -- the live profile has more.
- **rules-and-boundaries.md**: flagged update_needed (specifics in full
  Building evidence).
- **launch-guide.md**: does NOT have the architecture-map staleness in the
  same way -- lines 12-32 already correctly identify `brick build` as the
  one customer surface and classify `assemble`/`run_building_intake` as
  internal, matching the OLD (pre-Rule-10) framing -- so this file is
  internally consistent with itself, just now outdated by Rule 10, same as
  architecture-map.md's lines 180-184.

## Lane 3 — Kernel status docs (`project/brick-protocol/status/kernel/*.md`, 144 files)

Breadth catalog, not deep-read of all 144. **No file group was found safe
for outright deletion.** Recommendation: archive/index separation (a
museum/history convention, matching this repo's own prior pattern of
freezing old material rather than deleting it), not removal. Groups
identified include the 11-file P0-P9 goal closure series (keep as the audit
trail of the just-closed goal), the original 6-surface audit series, and
several standalone finding docs. Full group breakdown is in the Building's
own evidence (kernel-status-lane step output) given its size.

## Lane 4 — Checkers (`support/checkers/`)

Confirms `godmodule-checker-cleanup-synthesis-0701.md`'s DIRECTION is still
correct, but its exact numbers have drifted (expected, since P0-P8 touched
some of these files):
- `kernel_checks.py`: 10201 -> **10320** LOC.
- `case_runners.py`: 8507 -> **8512** LOC.
- `check_bounded_agent_proposed_routing_loop0.py`: 7087 -> **7176** LOC (not
  under `support/checkers/lib/`, a separate top-level checker file).
- `graph_topology_fan_barrier.py` (task #5, added 0701) is confirmed present
  and fully wired (lib file, profile, `check_profile.py` dispatch,
  `module_registry.yaml` row) -- no cleanup needed there.
- **New finding**: a phantom `checker_strict_validation` reference still
  exists in `module_registry.yaml` and checker comments/docs, but
  `support/checkers/profiles/checker_strict_validation.yaml` does not exist
  -- a real dead/orphaned reference.
- `support/checkers/profiles/*.yaml` count is **30** (confirms Lane 2's
  finding that `checker-profile-map.md`'s "29" is stale).
- Checker-diet split-copy measurements (from the synthesis doc) remain
  aligned with current state: `building_skill_preset_agent_tool_hardening.yaml`
  4237 LOC / 99 labels; split copies 320/8, 131/4, 259/1.

## Lane 5 — Top-level docs (`README.md` 365 lines, `AGENTS.md` 984 lines)

- **README.md mixes at least 4 audiences**: first-time installer (lines
  5-24), operator status-inbox watch loop (56-74), release-manager
  procedures (114-151), dashboard/Vercel/Docker deployment (153-199), plus
  historical notes (327-365). Confirms GPT-Pro's F-14 finding directly.
- **AGENTS.md's constitutional core is clean** (lines 13-94: fixed identity,
  three axes, current operating rule, support non-authority, movement/
  source-truth prohibitions) but operational/how-to content has crept in:
  native-dispatch hook wiring (107-117), a support/operator module map and
  recording-folder glossary (572-605), a historical phase procedure
  (751-810), and a reporting checklist (969-984). These read as runbook
  material, not constitutional law.
- **Blast radius of the `--graph`-as-customer-route staleness is WIDER than
  previously known**: README.md (78-91), `setup.md` (5-10), and
  `launch-guide.md` (12-32) all carry the same now-outdated framing, not
  just `architecture-map.md`.

## Cross-lane synthesis (from the Building's own closure)

- Rough shape: ~5 skill files, ~5 reference docs need wording/measured-fact
  refresh; 0 kernel status docs proven safe for deletion (archive strategy
  instead); 1 checker phantom-reference repair; checker decomposition
  already scoped elsewhere; 1 root-doc (README) split proposal, AGENTS.md
  reduction flagged as high-impact/needs explicit human disposition before
  touching.
- Recommended order: **low/medium-impact misleading-doc repairs first**
  (skills + references + the `--graph` framing wherever it appears), **before**
  checker decomposition or any AGENTS.md boundary change.
- Explicit proof limit: no actual edits were made, no checker was run by
  this closure, no full duplicate/dead/orphan profile audit across all 30
  profiles was performed (only spot checks), and no semantic-fitness proof
  exists for any specific proposed wording change until a follow-on edit +
  verification Building actually runs.

## Next Movement candidate

Not adopted as its own Building work (nothing to adopt, discovery only).
This catalog is the input for authoring the actual Follow-On goal document
(mirroring the P0-P9 phase-doc pattern), which is a separate COO action.
