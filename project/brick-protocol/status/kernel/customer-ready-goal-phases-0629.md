# Customer-Ready BRICK — Goal Phases Index — 0629

Status: support evidence only (operator index). Not source truth / success / Movement authority.
THE phase index: each phase → its detail doc. Goal-of-record (full spec) =
`customer-ready-goal-current-definition-0627.md`. Consolidation / audit / decisions / standard shapes
= `customer-ready-plan-audit-roadmap-0629.md`. Browse: the `GOAL/` folder carries P0–P8 symlinks to the detail docs below.

## Goal (one line)
A customer installs BRICK, connects their LLMs, says `make X`; an AGENT (COO) drives the official
`brick build` route (Brick / Agent / Link) and returns artifact + evidence. Final proof = self-dogfood
through that same customer path.

## GOAL PROMPT (operator discipline — must survive context compression)
```
GOAL: customer installs BRICK -> connects LLMs -> says `make X`. YOU (operator) drive the official
`brick build` route; Brick/Agent/Link declare the work, performers run it, evidence returns.
Final proof = BRICK self-dogfoods that same customer path.

YOU = OPERATOR / COO (never a worker lane):
- You JUDGE — define the dev decomposition from the design; disposition closure (forward/reroute).
  Judgment is yours, never auto-pilot.
- You do NOT become the worker. Implementation/QA/closure run through Building Agents.
- Claude/Codex/Gemini output = support evidence ONLY — never source truth / success / quality / Movement.

OFFICIAL ROUTE ONLY: implementation/QA/closure go through `brick build` -> cli/driver -> Builder ->
declared Building Plan -> run.py/walker -> evidence. No bypass (no direct build()/helper/hand-runner
calls; no operator-injected return-shape/ref/carry).

WHEN SOMETHING IS WRONG — think in AXES, not in modules:
 1. ASK WHICH AXIS first — Brick (work contract/template/plan/return-shape/graph) · Agent (performer/
    policy/capability/receipt/AgentFact) · Link (Movement/target/carry/gate/reroute).
    NOT "patch the nearest visible support noun."
 2. FIND YOUR OWN ERROR FIRST — is it your operating mistake or a contaminated measurement (wrong HOME/
    env), not a code defect? Re-measure in the REAL environment before calling it a bug.
 3. CHECK IT ALREADY EXISTS — the mechanism is probably already built; FIND it before adding anything.
 4. DERIVE THE REAL FIX — root cause; fix size = cause size. NO band-aid, NO module proliferation, NO
    feature-adding reflex. Prefer SIMPLIFY / DELETE over add — the complexity itself makes the holes.
 5. PER THE 3-AXIS CONSTITUTION — support records FACTS, judges nothing. Sufficiency + Movement = Link
    gate. Quality + success = human. Brick = WHAT, Agent = WHO/HOW, Link = Movement.

MEASURE, DON'T INFER. Execution results only, in the real environment. Verify your own output
adversarially before committing.
```

## Phases — each → detail doc
| Phase | What | Status (measured) | Detail doc |
|---|---|---|---|
| P0 | freeze + evidence inventory | DONE | goal-def §P0 (inline) |
| P1 | adapter authority (gemini-local intersection) | DONE | goal-def §P1 (inline) |
| P2 | capability taxonomy (read / probe_write / source_write) | DONE | `customer-ready-p2-capability-taxonomy-plan-0628.md` |
| **P3** | **Easy Building official route (CORE)** | **READY-NOW** (spine verified, NOT end-to-end) | `customer-ready-p3-easy-building-official-route-plan-0628.md` |
| P4 | resume fan-out | DONE | `customer-ready-p4-resume-fanout-plan-0628.md` |
| P5 | first-run / onboarding | BLOCKED (needs P3) | `customer-ready-p5-first-run-official-route-plan-0628.md` |
| P6 | cleanup / godmodule | BLOCKED (off critical path) | `customer-ready-p6-cleanup-godmodule-plan-0628.md` |
| P7 | fresh-machine proof | BLOCKED | `customer-ready-p7-p8-pass-criteria-0629.md` |
| P8 | dogfood capstone = GOAL | BLOCKED | `customer-ready-p7-p8-pass-criteria-0629.md` |

Critical path: P3 (close) → P5 → P7 → P8. P4 done; P6 off-path. (Details + decisions: audit-roadmap-0629.)

## Building patterns (how each item runs)
**개발 큰것 (BIG) — TWO buildings, the COO (Claude) judges between:**
```
빌딩1: design (Fugu ∥ Claude → 종합)          → [COO reads design, DEFINES N parallel devs + what each]
빌딩2: fan([dev → qa] × N) → closure          → [COO disposition: forward / reroute]
```
The design→dev decomposition (how many, what) is a COO JUDGMENT (not automatic) — so design is cut as its own building.

**개발 작은것 (SMALL) — ONE building:**
```
design → dev → qa → closure → COO 보고
```

Both run via the official `brick build` route (P3 sealed-fluent). Capability layers stay clean:
read (design/closure) · probe_write (qa) · source_write (dev).

## P3 casting-pick (workflow-style performer selection)
When the COO launches workflow-style, it can PICK the performer per node — Fugu / Gemini / Claude / Codex —
not only the default cast.
- **Default**: list the standard cast (design = Fugu ∥ Claude, dev = Codex, qa = Codex + Gemini, closure = Codex/COO).
- **Override (경우의 수)**: the COO picks per node — especially 개발 큰것, where the design's needs drive the casting.
- This belongs to P3's "sealed + fluent" launch = draw the shape + pick the cast + fire once; the official route swallows the plumbing.

## Stale — do NOT use as current
- `customer-ready-goal-plan-2track-0626.md` (old 2-track framing)
- the 11 `customer-ready-*-0627.md` sub-docs (C6-era HOLD chain — historical, superseded by the 0629 rechecks)
- `GOAL/` folder's old `00-…`–`06-…` symlinks (0626) — refreshed to P0–P8 here. The `GOAL/*.json` graph packets are current (keep).
