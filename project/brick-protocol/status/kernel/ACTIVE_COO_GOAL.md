# ACTIVE COO GOAL — 04 골문서 완벽 완료

| | |
|---|---|
| **Status** | **ACTIVE** · operator (COO) goal |
| **Set** | 2026-07-09 |
| **Authority ladder** | `GOAL/04-goal-phases-0709-route-and-frontier.md` |
| **Living route memo** | `OFFICIAL_ROUTE_MEMO.md` (Exit마다 갱신 필수) |
| **Proof limit** | support evidence only · not source truth / success / quality / Movement |

---

## 골 한 줄 (완료 정의)

```text
운영자(COO)로서 GOAL/04 의 능력 계단 G0→G6 을
각 Exit 체크리스트 + 측정 규율로 전부 닫고,
OFFICIAL_ROUTE_MEMO 와 04 마스터 큐를 Exit 로그와 함께
「완벽 완료」 상태로 고정한다.
```

**「완벽 완료」≠ 커밋만 있음.**  
각 G의 Exit 전부가 측정으로 채워지고, 남은 not_proven 이 문서에 정직히 남은 상태.

---

## 범위 = 04 계단 전부

| Phase | 이름 | 완료 조건 (요약) | 현재 |
|---|---|---|---|
| **G0** | Route Fuel | mid-hold 문법·resume dead_end 정직·한 루트 유지 | **EXIT** (d30517894 + probes) |
| **G1** | Official Continuity | graph-decl → hold → resume → complete dogfood | **EXIT** (g1-mid-hold-resume-dogfood-0709) |
| **G2** | Authoring Product | W1a defer fixtures + W1b 제품 + #3 order-chain; focused profile green | **IN PROGRESS** (building complete + WIP land 0b2f43dc5; Exit 미확정) |
| **G3** | Prevention Live | L1/L2/L3-3a observe live on official path; L3-3b only after Smith | **OPEN** |
| **G4** | Customer Surfaces | #5 progress auto-refresh + #6 charter-fill + residual #3 | **OPEN** |
| **G5** | Structural Gates | #4 vessel + #2 Route V2 beyond A — 설계+human gate only until approved | **OPEN** |
| **G6** | Release Readiness | #7; customer path re-proof; remaining_not_proven list frozen | **OPEN** |

---

## 운영 규칙 (이 골 동안 고정)

1. **사람 앞문 하나:** `brick build --graph-decl` / `brick resume --decl` (memo 준수).  
2. **G1 이후 제품 구현 = BRICK Building only** (COO live 구현 금지).  
3. **Exit마다** `OFFICIAL_ROUTE_MEMO.md` Exit log + 04 마스터 큐 갱신.  
4. **Success is measured:** REAL HOME / clean worktree profile 또는 dogfood frontier 실측.  
5. hold 없으면 resume 금지 → salvage. hold 있으면 resume.  
6. G5 구조/Route V2 확장은 human gate 전 코드 확장 금지.  
7. Deku 구현은 이 골 완료(또는 G0–G1 유지) 전까지 **FROZEN** (`deku/docs/DEKU_STATUS.md`).

---

## 완료 시 산출물

```text
[ ] 04 문서: G0–G6 Exit 전부 [x] + 마스터 큐 비움(또는 not_proven만 잔존)
[ ] OFFICIAL_ROUTE_MEMO: Exit log G0–G6 + 공식 명령 최신
[ ] ACTIVE_COO_GOAL: Status=COMPLETED + final evidence refs
[ ] parent-style closure note (support): remaining_not_proven 정직 목록
[ ] origin/main 착지 여부는 Smith 푸시 판단 (골 완료 ≠ 자동 push)
```

---

## 진행 스냅샷 (설정 시점)

```text
HEAD ladder: d30517894 (G0/G1) → 0b2f43dc5 (G2 WIP land) → fd10b8ae5 (G2 records)
G0 EXIT · G1 EXIT · G2 building complete / product Exit pending focused green
Next operator move: close G2 Exit (profiles) → G3 prevention official fire → G4 → G5 gates → G6
```

---

## COO disposition on set

```text
Movement for this meta-goal: forward (execute the ladder to completion).
This record is the operator goal charter, not Movement authority over Buildings.
```
