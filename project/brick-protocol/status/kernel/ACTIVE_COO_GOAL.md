# ACTIVE COO GOAL — residual 전부 밀기

| | |
|---|---|
| **Status** | **ACTIVE** · 2026-07-09 |
| **Parent** | GOAL/04 운영사다리 = CLOSED · 제품잔여 was OPEN → 이 골로 push |
| **Authority** | `GOAL/04-goal-phases-0709-route-and-frontier.md` · `GOAL/05-coo-ladder-closure-0709.md` |
| **Route memo** | `OFFICIAL_ROUTE_MEMO.md` |
| **Proof limit** | support only · not success/quality/Movement |

---

## 한 줄

```text
PRODUCT_RESIDUAL 큐(R1–R11)를 숨기지 않고 끝까지 밀어
  Smith 게이트는 게이트로 닫고,
  Building 가능 항목은 공식 route 위 dogfood/land로 닫고,
  not_proven 만 남긴 채 이 골을 Exit 한다.
```

---

## Exit 정의 (모두 충족)

```text
1) residual 표 전 행 disposition ∈ {DONE, SMITH_HOLD, DEFERRED_WITH_REASON, NOT_PROVEN}
2) OFFICIAL_ROUTE 유지: brick build --graph-decl + brick resume --decl
3) overclaim 금지: operator closed ≠ customer-ready forever
4) 이 문서가 표+증거 포인터로 최종 갱신된 뒤 Status=EXIT
```

---

## Residual push board (순서 고정)

| # | Item | How | Exit / disposition |
|---|---|---|---|
| R1 | L3-3b walker raise | **Smith gate only** | approve→Building / **SMITH_HOLD** |
| R2 | G3 prevention live re-dogfood | graph-decl Building | frontier complete or salvage+reroute |
| R3 | G4 UX multi-path dogfood | progress/charter 고객경로 | measured transcript |
| R4 | G2-c ship-copy (optional) | 소형 Building or DEFER | copy land or **DEFERRED_WITH_REASON** |
| R5 | Route V2 beyond A | **Smith design gate** | **SMITH_HOLD** until design |
| R6 | vessel physical split | **Smith design gate** | **SMITH_HOLD** until design |
| R7 | prevention harden (hooks/token) | Building | land+probe |
| R8 | G6 fresh-clone auth reliability | measured run | transcript or **NOT_PROVEN** |
| R9 | commercial release | after R1–R8 choice | **NOT_PROVEN** ok if honest |
| R10 | adapter:grok-local | land `dfc0c751b` | **DONE** (long dogfood=optional) |
| R11 | Deku impl | frozen until residual choice | **DEFERRED** default |

---

## 실행 규율

```text
- 제품 구현: BRICK Building only (live checkout 직접 구현 금지)
- pause: mid-node gates:[coo-review|human-review] → brick resume --decl
- walk-on dead_end: salvage · harvest-blind 금지
- parallel OK: R2/R3/R7 동시 worktree; R1/R5/R6 = Smith 대기 큐
- hygiene: salvage ref 유지 · archive 재오염 금지
- Grok 사용 가능: preferred_adapter_ref: adapter:grok-local
```

## Official route (불변)

```text
brick build --graph-decl <decl> --forward
brick resume --decl <resume.json>
```

## 지금 다음 3수

```text
1) Smith: R1 / R5 / R6 disposition (approve | hold)
2) COO: R2 + R3 발주 (brick-task-author → graph-decl)
3) R7 probe 스코프 확정 → Building
```

## remaining_not_proven (골 안 허용)

```text
full commercial release · brand-new-human auth forever
Route V2 code without design · vessel migrate without gate
Deku runtime (별 골)
```

## COO disposition

```text
ACTIVE = push ALL residual to terminal disposition
NOT = “이미 다 끝” 재주장
board 전 행 terminal → 이 골 EXIT → memo freeze

prior: OPERATOR_LADDER_CLOSED (04 G0–G6 Exit matrix) remains true.
this goal owns only PRODUCT_RESIDUAL push-to-terminal.
```
