# route-replay 공식 write 방향 선택 + SHAPE 상태원장 (0710d)

| 항목 | 값 |
|---|---|
| 기록 | 2026-07-10 · Claude COO (Smith 지시로 개발 수행 세션) |
| 근거 | AUDIT-full-consolidated-dev-handoff-0710.md §2.4 · HANDOFF-session-0710d-codex-to-fable5.md §4-4/§4-5 |
| 성격 | support evidence. 구현 착지 전까지 선언 기록일 뿐 — source truth·성공·Movement 권위 아님 |

## 1. route-replay 선택 (WO-4 item 3 확정)

```text
선택: 신규 transition-lifecycle 파라미터(예: disposition seam에 route_replay_plan 키 추가)를
     만들지 않는다. 기존 declared-plan revision/expansion chain을 공식 write 방향으로 선택한다.

근거 (0710 실측):
  - 읽기측은 이미 live: walker_resume.py:1223이 최신 승인 리비전으로 재수화,
    확장노드 budget 오버레이 :1246-1292 → 모든 graph resume에서 작동 중.
  - 쓰기측 계약 기존재: write_declared_plan_revision(declaration_packets.py:287) —
    승인증거(:691-757) + 확장예산(:774-780) + add-only(:783-830) + 예산불변(:858-871).
  - 어휘 봉인 정신과 정합: TRANSITION_LIFECYCLE_ALLOWED_KEYS에 새 키를 늘리지 않고,
    이미 봉인된 계약(리비전 체인)을 승격 — "새 엔진 대신 기존 확장" (Route V2 생존 전략과 동일).

후속(별도 발주, 이 세션 범위 밖):
  - 쓰기측 공식 경로 승격: 현재 checker-only인 write_declared_plan_revision을
    caller/COO 선언 표면(brick resume --decl의 확장 선언 또는 발주빌딩 relower 산출)에 연결.
  - repair 노드+budget add-only 추가 → 같은 frontier에서 resume하는 E2E 프로브.
```

## 2. SHAPE 상태원장 (감사 Exit 5 — 4행 확정)

```text
SHAPE A runtime boundary            = IMPLEMENTED
  (route_v2_views 읽기전용 뷰 + walker advisory 관측 7사이트 + resume 재주입,
   adopted_as_movement=False — 0710 감사 PR-1 적대검증 CONFIRMED)
shared eligibility observation helper = PRESENT / observation-only
  (classify_route_v2_concern_eligibility + "shape_b_shared_helper" 라벨은
   pure-dev D1 트랙 산출물. 기능적으로 관측 공유만 — 런타임 결정 경로 무접촉.
   라벨-승인 장부 정합은 이 행으로 해소: 본 원장이 "observation-only 승인 슬라이스"로 명기)
SHAPE B target/control integration  = NOT_IMPLEMENTED
  (walker_transition_concern.py에 route_v2 참조 0건 — 기획 유예 그대로)
beyond-A full engine                = NOT_IMPLEMENTED / FROZEN
  (재개 조건: 새 설계 Building + 별도 Smith 승인 + WO-1/2 green 위에서 n2 재증명이
   정책 부족 RED를 보일 때만 — route-v2-beyond-a-smith-close-0709.md 유지)
```
