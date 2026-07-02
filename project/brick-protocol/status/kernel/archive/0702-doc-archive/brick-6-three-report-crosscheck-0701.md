# Three-Report Architecture Audit Cross-Check (0701)

Status: COO cross-check synthesis. Not source truth, success judgment, quality
judgment, or Movement authority. Read against current main HEAD `877c764`.

## What this is

Smith uploaded a GPT-Pro-authored `.docx` architecture audit and asked whether
it, plus the two other architecture audit reports already in the repo (one
Workflow/Claude-authored, one Codex-authored), are fully reflected in the
current (post-P0-P9-repair) goal state, or whether anything is missing.

## The three reports, located

1. **GPT-Pro** (uploaded 2026-07-01): `BRICK_main_static_architecture_deployment_review.docx`.
   MD5 `6c567cd797aaa0c8c36588582a2763b1` -- **byte-identical** to
   `/Users/smith/Desktop/BRICK_main_static_architecture_deployment_review.docx`,
   which was already reviewed and routed into the audit on 2026-06-30 (see
   `brick-6-surface-audit-final-synthesis-0630.md` Scope section and
   `brick-6-surface-audit-final-coverage-matrix-0630.md`'s "External
   Architecture Report Coverage" table). **This is not a new report** -- it is
   the same file, already cross-checked once.
2. **Codex-authored** (2026-06-30, the original 6-surface audit):
   `brick-6-surface-audit-s1..s6-0630.md` + `final-synthesis-0630.md` +
   `readiness-tuples-0630.md` + `final-coverage-matrix-0630.md`.
3. **Workflow/Claude-authored** (2026-06-30, 16-agent independent review of
   the Codex audit): `brick-6-surface-audit-claude-report-0630.md` +
   `claude-review-addenda-0630.md` (C1-C19, ADD-1-ADD-20) +
   `claude-opinion-0630.md`.

Both non-GPT reports found successfully; nothing was unlocatable.

## Method

`readiness-tuples-0630.md`'s "Protocol-Live Priority Order" (8 items) and
"Ship-Imminent Priority Order" (6 items) map 1:1 onto goal phases P0-P9 by
design (confirmed by direct text match against
`brick-6-surface-audit-repair-goal-0630.md`'s phase list and "Phase Scope
Additions" section). GPT-Pro's own "Section 19: 최종 우선순위" (6 items) and
"Finding Register" (F-01..F-15) were checked the same way. Below that
top-priority layer, the coverage matrix's `embedded-as-coverage-gap` /
`embedded-as-repair-candidate` rows (ADD-1..ADD-20) were spot-checked with 3
parallel Explore-agent direct code reads plus my own direct reads of
`brick-6-graph-topology-fan-barrier-checker-closure-0701.md` and
`brick-6-graph-write-scope-default-closure-0701.md`.

## Confirmed CLOSED (top-priority items, all 14 protocol-live + ship-imminent
priorities, all embedded-theme rows in the External Architecture Report
Coverage table)

P0-P9 as executed this session (0701) close every item in both readiness-tuple
priority orders and every GPT-Pro Section-19 priority. No gap at the top
layer.

## Confirmed GAPS (genuine, evidence-backed, ranked)

**1. Global Operating Rule 8 is only half-resolved, and the goal doc's own
Completion Definition does not yet say so.** The `graph_topology_fan_barrier`
checker (task #5) *detects* a malformed fan-in-immediately-fan-out shape, but
is not wired into the live `brick build --graph` admission path
(`composition_compose.py` / `driver.py` / `plan_validation.py`) -- a malformed
packet can still fire through the real CLI and is only caught if the COO runs
the checker sweep first. Both `brick-6-graph-topology-fan-barrier-checker-closure-0701.md`
("Not proven" section) and `brick-6-graph-write-scope-default-closure-0701.md`
("Not proven" section) say this explicitly and recommend a follow-on, but the
goal doc's Completion Definition bullet ("Global Operating Rules 8 and 9 ...
resolved or explicitly deferred with Smith/COO disposition") has not been
updated with this half-open state. This is the sharpest gap found -- a
REQUIRED-marked rule with no recorded disposition in the goal document itself.

**2. `support/operator/walker_carry.py` (Link carry runtime) was never
inspected or given a dedicated checker**, despite P3 being specifically
scoped as "Brick return-shape truth AND Link carry filtering." Direct read
(this session) shows the logic looks sound -- carry filtering is cleanly
separated from the Brick return contract -- but no probe tests it, so this
remains formally unverified, not formally safe.

**3. `brick/work.py`'s return-shape parser was never directly inspected or
probed.** P3 added `materialized_return_shape_guards.py`, which checks
materializer-level equivalence, but the parser itself has no direct negative
probe.

**4. `agent/skills/make-an-agent/SKILL.md` still teaches the stale
read/write taxonomy** (`observed-write`, `reviewer-readonly`) instead of the
`read/probe_write/source_write` vocabulary the rest of the repaired system
now uses.

**5. Dashboard `participants` object (`support/dashboard/server/index.mjs:21`)
has no TTL/pruning and grows unbounded.** P8 Lane 3 added HMAC/replay/
sequence-rollback guards and *did* add cleanup for the `clients` Set
(SSE connections, line 226), but not for `participants`.

**6. Native child-dispatch recording** (`support/operator/native_dispatch.py`)
exists and is wired via skill hooks, but its live-activation proof remains
unresolved. P8 did not touch it; it is not named in the Follow-On bucket
either.

**7. Dashboard frontend/UI concerns from GPT-Pro F-10 (Movement/historical-
alias label confusion) and F-11 (client-side delta-ordering)** were not
addressed by any P-phase. P8 Lane 3 hardened server-side ingest security
(HMAC/sequence/replay) but not the frontend rendering/labeling layer.

**8. Provider write-boundary was disclosed, not asymmetrically hardened.**
GPT-Pro's Section-19 priority #3 asked for Claude/Gemini write to default to
worktree-only, stricter than Codex. P8 Lane 5 (`adapter_constants.py`)
exposed `boundary_strength`/`write_boundary` fields for transparency, but all
providers currently carry the identical write_boundary condition -- no
differentiated Claude/Gemini restriction was implemented.

**9. GPT-Pro F-12 (Agent adapter catalog physical-location debt, "move
catalog to Agent axis") and F-15 (install.sh pinned-installer option)** --
neither touched by any P-phase nor named in the Follow-On bucket. F-15 was
partially addressed (P8 Lane 2 documented the curl|sh trust limit) but the
"pinned installer option" itself was not implemented.

## Minor / low-urgency (not requiring immediate action)

- C1 (`brick/spec.py` "Brick godmodule/coupling candidate") was never given
  an explicit disposition, but at 642 lines it is far smaller than the true
  god-modules named in the Follow-On bucket (7,000-10,000+ LOC) -- low
  urgency, just an unclosed loop.
- `driver.py` portfolio-adoption probe exists (rejects support-authored
  adoption) but is narrower than the audit's ask ("comparable to
  single-Building gate probes").
- GPT-Pro F-13 ("checker text-pin-heavy, needs more behavioral fixtures") is
  a generic quality note that naturally belongs in the Follow-On
  checker-diet bucket but is not explicitly named there.

## Confirmed NOT gaps (checked, false leads)

- `assembly.py`'s fan-in guard (ADD-16, "naive substring matching"): direct
  read of line ~1209 shows exact string equality (`!= "fan_in"`), not
  substring matching. The original audit's characterization does not hold;
  no bug here.
- `brick/building.py` (audit worried this was an uninspected coupling risk):
  read in full, 65 lines, a thin frozen-dataclass container, no coupling
  concern.
- GPT-Pro F-06 (Gemini provider key landing in parent `os.environ`): already
  assessed on 0630 and credited with "existing env mitigations" in the
  coverage matrix -- reviewed and accepted, not silently dropped.
- The 7 high-level themes in the coverage matrix's "External Architecture
  Report Coverage" table: genuinely all embedded, as claimed.

## Next Movement candidate

Not a new Building by itself. Smith should decide, per item, which of gaps
1-9 get folded into: (a) the Rule 8 admission-gate follow-on already named in
two closure docs, (b) the existing post-P9 Follow-On Goal bucket, or (c) a
new small named follow-on item. Recommend at minimum: update the goal doc's
Completion Definition/Rule-8 text with gap #1's explicit disposition before
declaring the goal fully complete, since it is the one REQUIRED-marked rule
with no recorded COO disposition.
