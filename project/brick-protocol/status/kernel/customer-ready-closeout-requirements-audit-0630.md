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
| R1b | Main agent must preserve token-cost discipline: avoid broad raw/evidence/check-log reads, use field extraction + short verdicts, and delegate broad investigations to Codex subagents when useful. | `customer-ready-closeout-goal-0630.md` 0d; `hook:token-cost-discipline` added as Agent-axis advisory intent (`execution_opened:false`); coo/qa/inspector prompts + evidence/authoring skills updated; coo/agent-axis profiles pin the wording. Codex 5.5 investigation found current executable hooks are recording-only and cannot safely block shell reads without a new admitted command-inspection surface. | narrowly_proven as prompt/advisory/checker discipline; real blocking hook intentionally not_proven/deferred |
| R2 | Preserve evidence-first reporting vocabulary: observed / narrowly_proven / not_proven / next Movement candidate. | New proof docs use those categories; status docs name not_proven items. | narrowly_proven for current docs |
| R3 | Carry documented lessons from prior mistakes/misjudgments. | `customer-ready-closeout-goal-0630.md` lists over-reads: explicit forward edges vs no-link policy, P8 repeat not route-default proof, fixed graph ritual, stale main pointers, support evidence vs judgment. | narrowly_proven as written policy |
| G1.1 | User/COO can draw graph without authoring Link rows at compact surface; support materializes rows. | G1 skill/doc sync (`customer-ready-g1-no-link-policy-docs-skill-sync-0630.md`). | narrowly_proven as docs/skill sync |
| G1.2 | Concern evidence can become reroute/HOLD candidate under declared/adopted Link policy. | `building_operator_driver0` `live_qa_reroute_to_work_n2` measured: fan-in QA concern -> Link reroute -> work replay -> closure. | narrowly_proven for n2 single-reroute |
| G1.3 | Deep L2 cascade replay beyond measured n2 works. | No live proof recorded. | not_proven |
| G1.4 | Fresh customer understands no-link/materialized-forward/reroute distinction. | No customer comprehension test. | not_proven |
| G2.1 | Release export excludes internal evidence/status and build metadata. | Fresh export smoke + parity proof: no `project/`, no `brick_protocol.egg-info/`. | narrowly_proven |
| G2.2 | Export has no Smith-local/operator-local literals outside allowed README working example. | Fresh export smoke + parity proof: zero `/Users/smith` / `insightwavesmith` outside README allowance. | narrowly_proven |
| G2.3 | Export payload is deterministic/byte-identical across repeated runs. | `customer-ready-g2-release-export-parity-proof-0630.md`: identical file list and SHA-256 manifest across two exports. | narrowly_proven for payload excluding `.git/` metadata |
| G2.4 | Provider-free first-run docs honestly describe possible `agent_incomplete`/`not_ready`. | `customer-ready-g2-fresh-export-cli-smoke-0630.md` corrected README/quickstart/launch-guide. | narrowly_proven as docs |
| G2.5 | Real provider-backed fresh export build reaches `frontier_kind=complete`. | Not re-run after closeout docs/G3 commits. | not_proven |
| G2.6 | Full customer comprehension / first-run UX validated by a fresh reader. | No customer comprehension run. | not_proven |
| G3.1 | Godmodules shrink without new axes/runtimes/judges. | Four kernel_checks leaves moved to flat checker-lib siblings: no_smith_residue, install_release_export_lint, provider_preflight, onboard_smoke. Registry rows have no crossings/axis imports. Latest leaf was produced by main-agent-fired Building `g3-provider-preflight-leaf-0630`. | narrowly_proven for three leaves |
| G3.2 | Every G3 leaf uses conservation ledger, byte-identical where possible, mutation-RED, compile/checker/REAL HOME gates. | no_smith_residue proof + install/release proof + provider_preflight proof + onboard_smoke proof satisfy this. Latest proof: `customer-ready-final-architecture-provider-preflight-proof-0630.md`, REAL HOME --all rc=0 / 28 profiles. | narrowly_proven for three leaves |
| G3.3 | `kernel_checks.py` no longer remains largest godmodule or remaining debt is accepted by declared stop condition. | Live LOC after four leaves: `kernel_checks.py` 10814; no stop condition declared. | not_proven |
| G3.4 | FINAL architecture cleanup stop condition declared with Smith/COO. | Not declared. | not_proven |
| C1 | `main = origin/main`, worktree clean, final closeout record written before goal complete. | Current main is ahead of origin; goal still active. | not_proven / incomplete |
| C2 | REAL HOME `check_profile.py --all` GREEN before closeout. | Latest G3 leaf proof measured rc=0 / 28 profiles; must be re-run at final close. | currently_green, not final proof |

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
G1 = partial/narrow: route/reroute n2 proven, deep cascade + customer comprehension not_proven.
G2 = stronger after parity proof: export exclusion/literal/deterministic payload proven, provider-backed complete build + comprehension not_proven.
G3 = partial/narrow: four leaves proven (latest onboard_smoke via main-agent fire(graph)), kernel_checks still large/largest + stop condition not_proven.
Goal = ACTIVE, not complete.
```

## Next Movement candidates

```text
1. G2 provider-backed fresh export build -> frontier_kind=complete.
2. G3 declare stop condition, then continue next leaf by the main agent drawing and firing a real Building (not direct patch).
3. G1 deep L2 cascade replay proof if route-default closeout is prioritized.
4. Push local commits only after Smith OK.
```
