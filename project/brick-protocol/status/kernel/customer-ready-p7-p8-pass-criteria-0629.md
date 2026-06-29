# Customer-Ready BRICK — P7/P8 PASS Criteria (minimal) — 0629

Status: support evidence only. Not source truth / success / quality / Movement authority.
Defines the PASS TARGET for P7 (fresh-machine) and P8 (dogfood) so the bounded dogfood
probe has a concrete target and its gaps are measured. The probe RESULT is a gap
extractor, NOT a success verdict. Movement: FORWARD to the probe; broad customer-ready
stays HOLD / NOT PROVEN.

## P7 — Fresh-machine proof — PASS target
A clean machine shape (no pre-existing project state beyond what a documented install
creates) can, using documented steps only:
1. clone the repo
2. install
3. onboard / connect available providers (Codex / Gemini / Claude) per FIRST_USE
4. run ONE `brick build` via the official route (`--task/--preset/--graph`)
5. inspect evidence + frontier

PASS = steps 1–5 complete from clone; the build reaches `frontier=complete`; evidence is
operator-readable; ZERO undocumented manual steps; NO hidden machine-local dependency
(no `~/.brick` pre-state assumed).

Known P7 hazard (must be fixed or explicitly documented before P7 can pass):
`intake_evidence_projection_case` is non-hermetic — it generates a building needing real
`~/.brick` HOME state, so on a fresh/empty HOME it false-REDs. A true fresh machine hits this.

## P8 — Dogfood capstone — PASS target
BRICK runs ONE real meaningful task through the customer entrypoint:
1. a real task stated as a customer would (`make X`, or "this is big — design first, split, run lanes")
2. entered ONLY through the official route (`brick build --task/--preset/--graph`) — no hand-built runner calls, no operator return-shape/ref injection
3. declared shape (current casting): Codex work → Codex code-attack-qa → Gemini axis-attack-qa → Codex closure (Claude may join as a second-eye support-evidence lane)
4. evidence returned; raw/spine consistency checked (hash chain intact; no forbidden success/quality key)
5. `frontier=complete`

PASS = building reaches `frontier=complete` via the official route; raw/spine consistent;
the produced artifact is real + operator-readable.

## Bounded dogfood probe (the forcing run)
- Scope: ONE small-but-real task; the result is measured against the P8 PASS target above.
- Each UNMET criterion → a NAMED repair surface (P3 route / P5 onboarding / P7 hermeticity / …). That named gap list is the probe's deliverable.
- The task should be real enough to exercise work + QA lanes, but not so hard that task-difficulty masks path-gaps.

Candidate first tasks (Smith picks one):
- **(recommended, meta)** Make `intake_evidence_projection_case` hermetic — provide its own HOME/config so it no longer needs real `~/.brick` state. Real, in-scope, closes the known P7 hazard, and is a clean "BRICK improves itself through its own customer path." Scope tightly (don't refactor the case_runners god-module).
- (alt) A small documented skill/doc change pushed through the official route.
- (alt) A focused repair drawn from the existing backlog.

## Exit of the probe
- If the probe reaches `frontier=complete` and raw/spine is consistent → record as the FIRST official-route dogfood evidence (still NOT "P8 complete" — single run, not reliability).
- If it holds/fails → the hold reason is the next repair surface; route it to its phase (P3/P5/P7) and re-run.
