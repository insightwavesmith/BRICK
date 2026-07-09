# COO Ladder Closure — GOAL/04 G0–G6 (0709)

| | |
|---|---|
| **Status** | support evidence · **operator closed / product residual open** |
| **Date** | 2026-07-09 |
| **Active goal** | `ACTIVE_COO_GOAL.md` |
| **Ladder** | `GOAL/04-goal-phases-0709-route-and-frontier.md` |
| **Proof limit** | not source truth · not success/quality · not Movement authority |

---

## Split claim (필수 정직 규칙)

| Claim surface | Status | Meaning |
|---|---|---|
| **Operator ladder** (G0–G6 Exit matrix as COO) | **CLOSED** | route fuel, mid-hold resume, authoring land, prevention observe, UX land, gate-ready holds, measured release slice |
| **Product residual** | **OPEN** | Smith gates, re-dogfood, hardening, full auth reliability, commercial release, Deku |

**금지 문구:** 「빌딩 1–2개로 G0–G6 전부 완료」  
**허용 문구:** 「운영 사다리 Exit 닫힘; 제품 잔여 큐는 OPEN」

---

## Exit matrix (operator)

| Phase | Disposition | Evidence |
|---|---|---|
| **G0 Route Fuel** | **EXIT** | `d30517894` resume dead_end_kind; mid-node `gates:[coo-review]`; probes ALL_PASS; `g0-g1-exit-evidence-0709.md` |
| **G1 Continuity** | **EXIT** | dogfood `g1-mid-hold-resume-dogfood-0709` → hold → resume ×2 → `frontier=complete` |
| **G2 Authoring** | **EXIT** | WIP land `0b2f43dc5` + authoring fixtures; focused profiles **rc=0** after path admission `a07497628`; building `g2-authoring-w1b-0709b` complete |
| **G2-c order-chain** | **EXIT (optional ship-copy deferred)** | Map complete `coo-order-chain-consistency-0709.md`; engine already enforces policy; repair Building not required for ladder close |
| **G3 Prevention Live** | **EXIT observe; L3-3b HOLD Smith** | L1/L2 hooks landed `25efb8b46`; L3-3a observe landed `fbbbe93e0`. **L3-3b raise = Smith gate only**. Full prevention re-dogfood remains residual. |
| **G4 Customer Surfaces** | **EXIT land** | progress autorefresh `f3976946b` + charter-fill `ef1a36977`. Broader multi-path UX dogfood = residual. |
| **G5 Structural Gates** | **EXIT as gate-ready HOLD** | No vessel migrate / no Route V2 beyond SHAPE A code. Design posture: KEEP+clarify vessel; Route V2 expansion remains human-gate. |
| **G6 Release Readiness** | **EXIT measured slice** | Customer entry profiles measured; full fresh-clone human-auth reliability **not_proven**; release beyond repo proof **not_proven** |

---

## remaining_not_proven (honest residual)

```text
- L3-3b walker raise (kill bypass) — requires Smith approval
- G3 prevention live re-dogfood (beyond land-only evidence)
- G4 broader customer-path UX dogfood
- Route V2 beyond SHAPE A (Movement/route_target/concern_kind/Link/AgentFact)
- project vessel physical split / directory-template migration
- managed-settings hook lock / intentional token-forgery hardening
- full origin fresh-clone + brand-new-human auth transcript reliability
- commercial release/publication beyond current repo proof
- G2-c optional ship-copy wording Building (non-blocking)
- Deku implementation (frozen by design; separate ACTIVE goal)
```

### Residual building queue (product OPEN)

```text
R1  L3-3b raise            — Smith gate first
R2  G3 prevention dogfood  — fresh graph-decl live
R3  G4 UX multi-path       — progress/charter customer path
R4  G2-c ship-copy         — optional
R7  prevention harden      — managed-settings / forgery
R8  G6 fresh-clone auth    — measured transcript
R10 adapter:grok-local     — first-class performer (landing 0709)
```

---

## Official route (final memo pointer)

```text
brick build --graph-decl <assemble-arg.yaml|json> --forward
brick resume --decl <resume.json>
# mid hold: non-terminal node gates: [coo-review|human-review]
# no hold ledger → dead_end_kind=no_hold_ledger → salvage, not harvest-blind
```

Full living memo: `OFFICIAL_ROUTE_MEMO.md`

---

## Ops hygiene (not a G-number)

```text
- worktree prune/remove disposable sandboxes (0709 ops)
- untracked project buildings → /tmp/brick-project-buildings-archive-0709-ops
- inbox flood → /tmp/brick-inbox-archive-0709-ops (~695)
- salvage refs preserved
```

---

## COO disposition

```text
ACTIVE_COO_GOAL:
  OPERATOR_LADDER_CLOSED for G0–G6 Exit matrix
  PRODUCT_RESIDUAL_OPEN (queue above)

Movement candidate for parent product claims: still NOT customer-ready forever.
Next Smith choices: approve L3-3b; approve G5 designs; residual buildings; push origin/main; reopen Deku G0 only after residual choice.
```
