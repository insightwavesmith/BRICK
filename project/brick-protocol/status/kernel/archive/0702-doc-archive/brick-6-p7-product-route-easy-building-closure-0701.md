# BRICK 6 P7 Product route / Easy Building ergonomics closure evidence - 2026-07-01

Status: support evidence for phase:P7. Not source truth, not success/quality
judgment, not Movement authority, not whole-goal completion.

## Objective context

P7 of the BRICK 6-surface audit repair goal = product route / P3 Easy
Building declaration ergonomics (S6-F4). Implementation ran through official
`build()` / `brick build` declared graph Buildings, operated by Claude as
acting COO (the Fugu/Codex session originally driving P7 stopped on token
exhaustion; Smith authorized Claude to continue).

## Attempt history (all recorded, only the last is adopted)

| Attempt | Graph shape | Result | Disposition |
|---|---|---|---|
| P7a | `brick build --graph`, but declared topology was linear | interrupted twice, partial support evidence only | not adopted |
| P7b | corrected to fan-out/fan-in | rerouted once, then reroute budget exhausted, HOLD | not adopted |
| P7c | narrowed scope: status/build-root alignment only | `frontier_kind=complete`, clean closure | **adopted** (`ff1961e`) |
| P7d | Easy Building ergonomics slice (0701d) | `frontier_kind=complete` but graph-shape bug: two lane-QA nodes fanned directly into three final-QA nodes with no barrier (fan-in/fan-out same event, violates `agent/skills/building-coordination/SKILL.md`) | not adopted, recorded in `brick-6-p7-easy-building-ergonomics-operator-hold-0701d.md` |
| P7d2 (0701e) | barrier node (`lane-qa-fanin-confirm`) inserted; lane boundary_mismatch judged against each lane's own `write_scope` only | closure rerouted `work-docs` on a legitimate `boundary_mismatch` concern; `docs-lane-qa` re-verified clean, but sibling `checker-lane-qa` held a stale attempt-1 result and the barrier correctly refused to accept it without a declared vouch | not adopted; resume via `onboard approve --action forward` failed cleanly (`resume divergence... refusing to silently claim the disposition was applied`) -- wrong mechanism, not a graph fix |
| **P7d3 (0701f)** | same barrier shape, plus an explicit COO-declared `sibling_independence` vouch on the `lane-qa-fanin` group (`docs-lane-qa`, `checker-lane-qa` mutually vouched independent, based on their fully disjoint declared `write_scope.allowed_paths`) | `frontier_kind=complete`, single attempt on every node, **no transition_concern_evidence from any lane or closure** | **adopted** (this document) |

## P7d3 observed evidence

- Build route: official `brick build --graph` /
  `support/operator/cli.py build --graph`.
- Declaration commit: `b3c9ec0` (`P7: declare Easy Building ergonomics graph
  with honest sibling_independence vouch (P7d3)`).
- Base: `b3c9ec0c44cd992f1886185796209411a594b48f`.
- Sandbox output commit: `577109cd7abbcf3f92a22f971d502cc17a37e741`.
- Adopted to main as: `d568d1e`.
- Evidence root: `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p7-easy-building-ergonomics-0701f`.
- Every declared node (task-intake, design-codex, design-claude,
  design-synthesis, work-docs, work-checker, docs-lane-qa, checker-lane-qa,
  lane-qa-fanin-confirm, final-code-qa, final-axis-qa, final-evidence-qa,
  closure) ran exactly once (`attempt-1`), no reroute needed.
- Closure `narrowly_proven`: public route wording represented as
  `brick build` / `brick build --graph` over declared task or graph packets
  (not `--large` or preset-only); negative evidence against `--large`,
  `--dev-lanes`, public `onboard` route exposure, hidden `_p3_easy_large`,
  `lane_return`, and raw exception leakage for invalid graph packets; bare
  `brick` JSON behavior observed as status support evidence only (not a
  route selector); focused `brick_cli_entrypoint` checker green; lane-QA
  fan-in barrier and final-QA fan-out recorded as separate declared
  boundaries; no final QA lane returned binding or non-binding transition
  concern for a scoped P7 product-route defect.
- Adoption side-effect: the diff also cleaned a stale local-machine-only
  `source_evidence_refs` entry (`/Users/smith/.codex/attachments/...`) out
  of the P7d/P7d2/P7d3 graph declaration files, replacing it with a
  `support-packet:` ref.

## Independent verification performed before adoption (Claude, detached worktree)

```text
git worktree add --detach /tmp/p7d3-verify 577109c...
py_compile support/operator/cli.py support/checkers/lib/kernel_checks.py: PASS
check_profile.py --profile brick_cli_entrypoint.yaml: PASS (94 rule observations, 18 kernel targets)
git diff --check b3c9ec0..577109c: PASS
check_profile.py --all: EXIT=0, 29/29 profiles passed, including
  read_side_projection_boundary (which had shown rc=1 /
  intake_evidence_projection_case / frontier=agent_incomplete INSIDE the
  Building's own internal QA sandbox runs during P7d2 and P7d3 -- same
  sandbox-local-noise pattern already identified in the P6 closure; an
  independent clean detached-worktree run shows it is NOT a real regression
  on the delivered diff)
Re-verified again after cherry-pick onto current main (0079ea9 -> d568d1e):
  py_compile PASS, focused brick_cli_entrypoint PASS, git diff --check PASS
```

## Narrowly proven (whole P7)

- The official `brick build` / `brick build --graph` route is real,
  checker-covered, and does not require `--large` or a hidden route.
- `graph_packet` input mode correctly rejects customer-authored
  `required_return_shape` / `carries_forward_fields` / `brick_template_refs`.
- Public first-use docs (`README.md`, `quickstart.md`, `launch-guide.md`,
  `architecture-map.md`) now describe the declared route without teaching
  internal-only helpers (`run_building_plan`, `assembly.fire`,
  `launch_assembled_building`) as customer routes.
- CLI raw exception leakage is guarded by negative pin.
- `--large` / `_p3_easy_large` / `--dev-lanes` / `lane_return` revival is
  actively rejected, not merely absent.
- Fan-in and fan-out placement discipline (barrier required between them)
  is now recorded as a durable rule in
  `agent/skills/building-coordination/SKILL.md` and as Global Operating
  Rule 8 in the repair goal document, backed by a required-but-not-yet-built
  checker-first admission guard (tracked separately, see Not Proven).
- `sibling_independence` is a real, working, COO-declared mechanism for
  honestly vouching disjoint-write-scope fan-in siblings without coaching
  any Agent to misreport a reroute target.

## Not proven

- Full external `brick build --graph <packet>` dynamic-design ergonomics
  pipeline (natural-language "make X" -> automatic task intake -> sizing ->
  design -> parallel lanes) -- explicitly deferred to a later slice per
  P7b/P7c/P7d/P7d2/P7d3 task scoping throughout. Only the achievable part
  (route wording, CLI safety, checker negative pins, declaration shape
  discipline) closes here.
- Whole-repo `check_profile.py --all` "always green" is not a standing
  guarantee -- it is green on this delivered diff as independently verified
  above; the in-sandbox flake pattern (`read_side_projection_boundary` /
  `intake_evidence_projection_case`) recurred across P6, P7d2, and P7d3 and
  remains unexplained at the root-cause level (not investigated further in
  this closure; low urgency since clean detached-worktree verification has
  now cleared it three times in a row).
- The graph-topology admission checker (Global Operating Rule 8) that would
  have prevented the P7a/P7b/P7d shape mistakes from costing real Building
  cycles does not exist yet -- tracked as a required next Building before P8.
- Two engine-level findings discovered while operating P7 remain unfixed:
  fan-out node latency not independently recorded
  (`brick-6-fanout-node-latency-not-recorded-finding-0701.md`) and the
  fan-in cohort re-verify one-hop blind spot
  (`brick-6-fan-in-cohort-reverify-one-hop-blindspot-finding-0701.md`) --
  both tracked as required next Buildings before P8.
- P8 ship-safety, P9 dynamic customer replay, fresh-machine install,
  real-provider reliability, customer comprehension, and whole
  customer-ready closeout.
- Checker/profile green remains support evidence only.

## Next Movement candidate

Proceed to the required engine/checker hardening Buildings discovered while
operating P7 (graph-topology admission checker; fan-out latency recording;
fan-in cohort blind-spot fix) before P8, per Global Operating Rule 8 and
Smith's explicit direction that these are required, not optional polish.
Do not push without Smith OK. Do not claim whole-goal completion.
