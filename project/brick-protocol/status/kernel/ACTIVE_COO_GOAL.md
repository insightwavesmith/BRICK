# ACTIVE GOAL — residual 전부 밀기 (≤3KB)

| | |
|---|---|
| **Status** | **ACTIVE** · 2026-07-09 |
| **Parent** | GOAL/04 CLOSED · residual OPEN→push |
| **Proof** | support only · not success/quality/Movement |
| **Route** | `OFFICIAL_ROUTE_MEMO.md` |
| **Freeze** | `residual-push-exit-0709.md` (on EXIT) |

## 한 줄
```text
R1–R11 terminal disposition. Smith=HOLD. Buildings via graph-decl only.
not_proven ok. never customer-ready forever.
```

## Exit (all)
```text
1) R1–R11 ∈ {DONE,SMITH_HOLD,DEFERRED_WITH_REASON,NOT_PROVEN}+pointer
2) product DONE rows cite graph-decl building (not live-checkout land alone)
3) no overclaim
4) Status=EXIT + freeze doc
```

## Board

| # | Item | Disp | Pointer |
|---|---|---|---|
| R1 | L3-3b raise | **SMITH_HOLD** | design Stage3b; no Smith approve |
| R2 | G3 prevent re-dogfood | **ACTIVE_BUILD** | graph-decl building in flight |
| R3 | G4 UX dogfood | **ACTIVE_BUILD** | graph-decl building in flight |
| R4 | G2-c ship-copy | **DEFERRED_WITH_REASON** | optional; map coo-order-chain-0709 |
| R5 | Route V2 >A | **SMITH_HOLD** | route-v2-human-gate-approval-0709 |
| R6 | vessel split | **SMITH_HOLD** | dogfood-vessel-human-gate-0709 KEEP |
| R7 | harden hooks/token | **DEFERRED_WITH_REASON** | org/Smith out-of-band design |
| R8 | G6 fresh-clone auth | **NOT_PROVEN** | no transcript |
| R9 | commercial release | **NOT_PROVEN** | not attempted |
| R10 | adapter:grok-local | **ACTIVE_BUILD** | official graph-decl dogfood (not solo land) |
| R11 | Deku | **DEFERRED_WITH_REASON** | design frozen |

## Route
```text
brick build --graph-decl <decl> --forward
brick resume --decl <resume.json>
```

## Next
```text
1) finish R10→R2→R3 buildings frontier=complete
2) flip board DONE/defer; EXIT
```

## COO
```text
ACTIVE=push via buildings. NOT already-done overclaim.
```
