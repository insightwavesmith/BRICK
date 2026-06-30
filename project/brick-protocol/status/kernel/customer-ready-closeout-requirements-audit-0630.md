# Customer-Ready Closeout — requirement audit matrix — 0630

Status: operator audit / support evidence only. Not source truth, not success
judgment, not quality judgment, and not Link Movement authority.

Goal of record: `customer-ready-closeout-goal-0630.md`.

This audit independently re-derives the active closeout requirements and records
what current evidence proves, contradicts, or leaves missing. It is deliberately
stricter than the latest green checks: checker/profile pass is evidence only and
must be matched to the requirement it covers.

## Requirement matrix

| ID | Requirement / edge case | Current evidence | Status |
| --- | --- | --- | --- |
| R0 | Preserve COO/operator role: COO declares/observes, does not become worker/success/quality/Movement authority. | Goal anchor + closeout goal carry role language; current G3/G2 proof docs mark direct operator maintenance as exception and support evidence only. | narrowly_proven for docs; ongoing discipline required |
| R1 | Preserve Building-first workflow; direct patches must be exceptional and recorded honestly. | Closeout goal composition-first rule; no_smith_residue and install/release leaf ledgers explicitly record direct operator maintenance exception. | partially_proven; next implementation slice must return to Building-first |
| R1a | Main agent must actually draw and fire Buildings for G1/G2/G3 implementation slices so the main-agent building-running skill chain is exercised end to end. | `customer-ready-closeout-goal-0630.md` 0c (`ec380ca`); FIRST real main-agent fire landed: building `g3-provider-preflight-leaf-0630`, official `fire(graph)` route, real Codex/Claude/Gemini lanes, frontier=complete, sandbox commit `3ec6502` cherry-picked to main; proof `customer-ready-final-architecture-provider-preflight-proof-0630.md`. | narrowly_proven (one real fired Building); ongoing rule for remaining slices |
| R1b | Main agent must preserve token-cost discipline: avoid broad raw/evidence/check-log reads, use field extraction + short verdicts, and delegate broad investigations to single diagnostic Buildings when useful. | `customer-ready-closeout-goal-0630.md` 0d; `hook:token-cost-discipline` added as Agent-axis advisory intent (`execution_opened:false`); coo/qa/inspector prompts + evidence/authoring skills updated; coo/agent-axis profiles pin the wording. A delegated investigation found current executable hooks are recording-only and cannot safely block shell reads without a new admitted command-inspection surface. Smith corrected that broad 실측 진단 should be routed as a single Building, not as a Codex Ultra/subagent assumption. | narrowly_proven as prompt/advisory/checker discipline; real blocking hook intentionally not_proven/deferred |
| R2 | Preserve evidence-first reporting vocabulary: observed / narrowly_proven / not_proven / next Movement candidate. | New proof docs use those categories; status docs name not_proven items. | narrowly_proven for current docs |
| R3 | Carry documented lessons from prior mistakes/misjudgments. | `customer-ready-closeout-goal-0630.md` lists over-reads: explicit forward edges vs no-link policy, P8 repeat not route-default proof, fixed graph ritual, stale main pointers, support evidence vs judgment. | narrowly_proven as written policy |
| G1.1 | User/COO can draw graph without authoring Link rows at compact surface; support materializes rows. | G1 skill/doc sync (`customer-ready-g1-no-link-policy-docs-skill-sync-0630.md`). | narrowly_proven as docs/skill sync |
| G1.2 | Concern evidence can become reroute/HOLD candidate under declared/adopted Link policy. | `building_operator_driver0` `live_qa_reroute_to_work_n2` measured: fan-in QA concern -> Link reroute -> work replay -> closure. | narrowly_proven for n2 single-reroute |
| G1.3 | Deep L2 cascade replay beyond measured n2 works. | `customer-ready-g1-deep-l2-cascade-proof-0630.md` records `bounded-agent-proposed-routing-loop` PASS with nested different-node cascade requiring two adopted landings and `cascade_depths=[1, 2]`. | narrowly_proven as support evidence |
| G1.4 | Fresh customer understands no-link/materialized-forward/reroute distinction. | No customer comprehension test. | not_proven |
| G2.1 | Release export excludes internal evidence/status and build metadata. | Fresh export smoke + parity proof: no `project/`, no `brick_protocol.egg-info/`. | narrowly_proven |
| G2.2 | Export has no Smith-local/operator-local literals outside allowed README working example. | Fresh export smoke + parity proof: zero `/Users/smith` / `insightwavesmith` outside README allowance. | narrowly_proven |
| G2.3 | Export payload is deterministic/byte-identical across repeated runs. | `customer-ready-g2-release-export-parity-proof-0630.md`: identical file list and SHA-256 manifest across two exports. | narrowly_proven for payload excluding `.git/` metadata |
| G2.4 | Provider-free first-run docs honestly describe possible `agent_incomplete`/`not_ready`. | `customer-ready-g2-fresh-export-cli-smoke-0630.md` corrected README/quickstart/launch-guide. | narrowly_proven as docs |
| G2.5 | Real provider-backed fresh export build reaches `frontier_kind=complete`. | `customer-ready-g2-provider-backed-frontier-proof-0630.md`: fresh export installed + CLI + `build --real-provider` => `frontier_kind=complete`, `customer_visible_frontier_state=frontier_complete`, evidence root present. | narrowly_proven as support evidence |
| G2.6 | Full customer comprehension / first-run UX validated by a fresh reader. | No customer comprehension run. | not_proven |
| G3.1 | Godmodules shrink without new axes/runtimes/judges. | Four kernel_checks leaves moved to flat checker-lib siblings: no_smith_residue, install_release_export_lint, provider_preflight, onboard_smoke. Registry rows have no crossings/axis imports. Latest leaf was produced by main-agent-fired Building `g3-provider-preflight-leaf-0630`. | narrowly_proven for three leaves |
| G3.2 | Every G3 leaf uses conservation ledger, byte-identical where possible, mutation-RED, compile/checker/REAL HOME gates. | no_smith_residue proof + install/release proof + provider_preflight proof + onboard_smoke proof satisfy this. Latest proof: `customer-ready-final-architecture-provider-preflight-proof-0630.md`, REAL HOME --all rc=0 / 28 profiles. | narrowly_proven for three leaves |
| G3.3 | `kernel_checks.py` no longer remains largest godmodule or remaining debt is accepted by declared stop condition. | Main now carries the G3 split (commit `0d18b79`): `kernel_checks.py` = 9931 LOC (< 10000), and `customer-ready-g3-stop-condition-0630.md` additionally defers all 13 remaining >=200 LOC candidates with reason/owner. Stop condition met. | narrowly_proven as support evidence |
| G3.4 | FINAL architecture cleanup stop condition declared with Smith/COO. | Declared by COO in `customer-ready-g3-stop-condition-0630.md`; still needs Smith disposition if stricter/lighter threshold desired. | narrowly_proven as COO declaration; Smith disposition pending |
| C1 | `main = origin/main`, worktree clean, final closeout record written before goal complete. | Current main is ahead of origin; goal still active. | not_proven / incomplete |
| C2 | REAL HOME `check_profile.py --all` GREEN before closeout. | Re-run on main after the G3 split cherry-pick (`0d18b79`): 28 profiles all passed, 0 failed / 0 Traceback. Must be re-run once more immediately before any push disposition. | currently_green; re-verify at push time |

## Requirement-derived edge cases

```text
- Do not use all-forward graph completion as route-default proof.
- Do not treat checker/profile green as success, quality, Movement, or source truth.
- Do not treat direct operator maintenance as the default work mode; record it and
  return to Building-first for implementation slices with behavior risk.
- Do not let the main agent outsource or bypass the graph-drawing step for
  implementation slices: the main agent must draw + fire the Building so the
  building-running skill chain is exercised and updated from real firings.
- Do not assert `.git/` byte parity for release exports; payload parity excludes
  generated git metadata.
- Do not close G3 without a declared stop condition or named remaining debt.
- Do not close the whole goal while local commits are unpushed if the release/P7
  proof requires origin/main as customer clone source.
```

## Current closeout disposition

```text
G1 = route/reroute n2 proven + deep L2 cascade support-proven; only fresh customer comprehension remains not_proven.
G2 = export exclusion/literal/deterministic payload proven + provider-backed build reached frontier_kind=complete; only fresh customer comprehension remains not_proven.
G3 = kernel split landed on main (kernel_checks.py 9931 < 10000) + 13 remaining candidates deferred with reason/owner; stop condition met as support evidence.
G4 = ai-cli MCP classified as later diagnostic (enabled=false, no runtime dependency), not a closeout blocker.
G5 = main worktree clean, REAL HOME --all green, final audit recorded.
Remaining genuinely-open items: fresh customer comprehension (G1.4, G2.6) and the human-gate external close (C1: push / merge / main=origin/main).
Goal = ACTIVE, not complete: blocked on human-gate external action + a fresh-customer comprehension study.
```

## Next Movement candidates

```text
1. (DONE) G2 provider-backed fresh export build reached frontier_kind=complete.
2. (DONE) G3 stop condition met on main: kernel_checks.py 9931 < 10000 + 13 deferred candidates.
3. (DONE) G1 deep L2 cascade replay support proof recorded.
4. Remaining operator-doable: none on the closeout mainline without external/human input.
5. Human-gate (Smith disposition required): push local commits, choose merge/release target, reach main=origin/main.
6. External-dependency: a fresh-customer comprehension study for G1.4 / G2.6 (cannot be self-certified by the operator).
```
