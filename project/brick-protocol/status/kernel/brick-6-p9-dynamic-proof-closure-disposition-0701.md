# P9 dynamic-proof Building disposition (0701)

Status: COO disposition on a two-attempt Building sequence. Not source
truth, success judgment, quality judgment, or Movement authority.

## Attempt history

| Attempt | Result | Disposition |
|---|---|---|
| `brick-6-p9-dynamic-proof-run-0701a` | `frontier_kind=link_paused`. Only 2 of 11 nodes ran (`p9-proof-intake`, then `p9-artifact-repair` immediately after -- the entire fan-out/fan-in/barrier/second-fan-out sequence was skipped). | **Not adopted.** Root cause confirmed via a forensic workflow (parallel diagnosis + adversarial verify): the graph declared `p9-artifact-repair` as reachable ONLY via a conditional `reroute()`, with zero normal incoming edges. This engine's `execution_order` is pure node-declaration order (`composition_compose.py:675`, no topological sort), and the walker's root-seeding (`walker_fan_in.py:60-73`) queues every zero-incoming-edge node as an immediately-executable root, unconditionally -- there is no "wait for a concern to route here" gate. The node was front-loaded into position 2 and the Building paused forever waiting on two fan-in sources that were never reached. |
| `brick-6-p9-dynamic-proof-run-0701b` | `frontier_kind=link_paused` (non-binding, advisory concern -- see below), but **all 10 declared nodes executed in the intended order**: intake -> artifact-work -> fan-out(3 QA) -> fan-in -> explicit barrier -> second fan-out(2 lanes) -> fan-in -> closure. | **Adopted** (commit `46d02e4`, cherry-picked after the base diverged during the run). Corrected graph: the reroute target is `p9-customer-run-artifact` itself (a node with real existing edges), matching this codebase's own proven `check_assembly_equivalence.py` fixture pattern (`engine-feature-hard`, `two-fan-in-graph`) -- reroute targets must always be pre-existing, normally-reachable nodes, never a bespoke orphan. |

## What attempt 2 actually proved (independently verified, 0701)

A second workflow (3 parallel verification angles + adversarial synthesis)
independently re-checked attempt 2's own evidence before adoption:

- **Checker sweep**: the Building's own final-closure step reported
  `check_profile.py --all` exit 1 with "No usable temporary directory found".
  Independently re-run correctly (`HOME=$(mktemp -d)
  PYTHONPATH=support/import_identity`) in the same worktree: **exit 0, 30/30
  profiles passed, 0 failed.** The Building's report was its own sandbox's
  environment artifact, not a real defect.
- **Reroute/advisory mechanism**: `p9-reroute-trigger-qa` emitted a real,
  non-scripted, non-binding `implementation_gap` concern (the artifact was
  genuinely missing a dedicated stub-vs-real-provider heading at that point).
  It did NOT auto-adopt into a reroute. Confirmed as CORRECT, by-design
  behavior: this Building's own declared plan classified that node under
  `fan_in_source_transition_concern_adoption=advisory` (a Human/COO-level
  plan choice, not a support default), which routes the concern to an
  observation-only record and never reaches `_classify_reroute_target` at
  all -- `gates=()` is irrelevant to this path. Lesson recorded in the goal
  document: a QA node's task prose should not promise an auto-reroute
  outcome its declared plan topology structurally forecloses.
- **Evidence honesty audit**: all 10 steps show real, non-zero
  `adapter_dispatch_timing` (genuine multi-minute CLI calls, not fabricated).
  Fan-out QA lanes show disjoint, non-copy-pasted evidence bodies. One real
  issue found: `p9-code-qa`, `p9-axis-qa`, and `p9-final-closure` reported
  THREE different results for the same `check_profile.py --all` command
  (rc=1-ambiguous / unhedged "100% green" / rc=1-tmpdir-error) and nothing in
  the Building's own QA-barrier layer caught the contradiction.

## COO dispositions made at adoption (recorded directly in the adopted artifact)

1. **`p9-axis-qa`'s "100% green" claim is NOT credited.** It contradicts the
   other two lanes' honest hedging and does not match the independently
   re-run ground truth. Documented in the artifact as an explicit
   discrepancy, not silently accepted.
2. **The non-binding reroute concern is resolved by direct COO documentation
   edit**, not a third real-provider Building cycle: the missing
   stub-vs-real-provider disposition heading was added directly to the
   adopted artifact. This is a doc-completeness fix, not a functional defect,
   and Rule 2's goal/phase-documentation exemption covers it.
3. **Repo-state values** (`git status`/`HEAD`/branch/upstream) were observed
   by final-closure but never written back (closure nodes are probe_write
   only by this goal's QA discipline) -- filled in by the COO directly at
   adoption time, sourced from the same worktree the Building actually ran
   in.

## Scope note (explicit, not overclaimed)

This proof-run exercises reroute/replay by re-visiting the original work
node, matching this codebase's own proven pattern. **It does not re-validate
task #7's exact one-hop fan-in-cohort blind spot** (that fix has its own
separate closure evidence, `brick-6-fanout-latency-and-fanin-cohort-closure-0701.md`).
The forensic workflow concluded that exact scenario (a bespoke node reached
only by reroute, one hop from the real cohort trigger) is not constructible
as a single declared Building graph in this engine's current linear-walker
model -- recorded as a genuine, confirmed engine-authoring landmine in the
goal document (Rule 10 section), not attempted further here.

## Not proven

Real-provider/fresh-machine reliability, customer comprehension by a fresh
external reader (explicitly recorded as not_proven by the comprehension-
observation lane itself), task #7's specific cohort scenario, repo push/
remote adoption (not attempted, requires separate Smith authorization).

## Next Movement candidate

P9's live dynamic proof is demonstrated and adopted. Proceed to the goal's
overall Completion Definition final check (task #4) -- this does not by
itself declare the whole goal complete; that is a separate, final COO/Smith
review pass across all of P0-P9 plus Rules 8/9/10.
