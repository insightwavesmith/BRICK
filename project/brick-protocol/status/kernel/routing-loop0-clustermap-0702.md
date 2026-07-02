# routing_loop0 클러스터맵 — 첫 분해타당성 조사 (0702)

Status: support evidence only. Not source truth / success / quality / Movement authority.
갓모듈 정본(godmodule-checker-cleanup-synthesis-0701.md) §4 항목 3의 "missing first step"을
수행한 조사 빌딩의 산출 기록. 대상: `support/checkers/check_bounded_agent_proposed_routing_loop0.py`
(7,176줄, 조사 시점 HEAD `6e7a35e`, 파일 최종변경 커밋 `4f0d147`).

## 조사 빌딩 (공식 build() 경로, read-only)

- building_id `task-statement-1520f0071f1f-node`, evidence root
  `~/.brick/goal-runs/task-statement-1520f0071f1f-node-20260702T013222482674Z/task-statement-1520f0071f1f-node/`
- 모양: fan(정독 7레인, claude-local/sonnet) → review 반증(qa-lead, gemini-local) →
  closure 합성(coo, claude-local/opus). 9걸음 전부 완료, 반환 영수증 9행, 최종 forward.
- 레인 스팬(refute가 디스크 대조로 확정): L1 1–1536 / L2 1537–2423 / L3 2424–3211 /
  L4 3212–3957 / L5 3958–5013 / L6 5014–5893 / L7 5894–7176.
  **합집합 = 1–7176, 겹침 0, 빈틈 0. 표본 심볼 10개 디스크 검증 통과.**

## 클러스터맵 (15 패밀리)

| 클러스터 | 스팬(≈줄) | 내용 | 분리판정 |
|---|---|---|---|
| C1 HELPER-ZONE | 1–1536 (1536) | 모듈 최상위 `_*` def **52개**: 플랜빌더/러너/어서션/증거리더/reroute callable/carry·budget/스레딩 풀(`_run_with_fanout_pool` 등)+타임드 callable+정규화 | **extractable** (이미 함수 경계) |
| C2 BUDGET-HOLD-CORE | 1537–1978 (442) | G5-1, Invariant A–D | entangled |
| C3 FAN-IN-SERIAL | 1980–2009 + 2351–2423 (103) | Invariant E–H | entangled |
| C4 CONCURRENCY-POOL | 2011–2349 (339) | P6-C 바이트동일 fanout, P4 resume-fanout, F1 — **스레딩 소비 집중지** (기계는 C1) | entangled |
| C5 REPLAY-CASCADE | 2424–2566 (143) | B5-C3 full-chain replay, BUG3/Lane3 | entangled |
| C6 GATE-ONBOARD-DISPOSITION | 2568–3025 (458) | C5 human-gate, ONBOARD approve fire, HUMAN-REROUTE | entangled |
| C7 NESTED-BUDGET | 3026–3064 (39) | C7 nested per-node budget | entangled |
| C8 KNOT-4/FIX-A (비연속) | 3066–3210 + 3212–3773 + 3958–4383 (1133) | classify/self-reroute/resolver/RESUME PARITY, lazy import `_classify_reroute_target`@≈3364 | entangled |
| C9 QA-CONCERN-EMISSION | 3775–3957 (183) | `validate_transition_concern_evidence`, lazy import @3781 | entangled |
| C10 REGRESSIONS | 4384–4483 (100) | malformed-concern, adapter-interruption, B5-C10 | entangled |
| C11 KNOT-3-COHORT | 4485–5394 (910) | fan-in cohort 재검증 (a)–(g), vouch, nested floor FIX#2 | entangled |
| C12 RESUME-FAIL-CLOSED | 5395–5776 (382) | resume gaps 1–6 fail-closed | entangled |
| C13 MAIL-REPAIR | 5778–7084 (1307) | `_mail_*` 중첩 def(5778–5893) + mail-1~7 | entangled |
| C14 ZETA7-SOURCE-GUARD | 7085–7093 (9) | Invariant I (dynamic_walker.py 텍스트 리드) | entangled |
| C15 CHECK-RETURN+MAIN | 7093–7176 (84) | `return violations` + main() | **extractable** |

핵심 구조 판정: **C2–C14 전부가 단일 `check()` 함수(1537–7093) 안의 인라인 블록**이고
하나의 공유 `violations` 누산기에 append한다 — 패밀리 단위 추출은 "파일 분리"가 아니라
**check() 함수 분해가 선행 문제**다. extractable/entangled는 "현재 def 경계 유무"의
구조 관찰이지 safe-to-split 판정이 아니다(빌딩 스스로 명기).

## COO 직접 검증 (빌딩 자기보고 아님 — 실행 결과)

- ✔ 헬퍼 52개 (`awk NR52-1536 | grep -c '^def '` = 52. 이전 COO 실측 "53"은 오산).
- ✔ `violations.append` 436건 — 공유 누산기 주장 강하게 성립.
- ✔ lazy import 2건 좌표 (@3364 walker_transition_concern, @3781 validate_transition_concern_evidence).
- ✘ **정정 1건**: 합성의 "check() 내부 def 경계 없음"은 부정확 — `sed 1537,7093 | grep -c '^\s+def '` =
  **중첩 def 25개**(클로저; C13 `_mail_*` 등에 집중). top-level 경계가 없다는 뜻으로는 참이나,
  분해 난이도 평가에는 "중첩 클로저 25개 존재"가 실측이다. walker의
  `_run_dynamic_graph_walker` 패턴(중첩 클로저 7개)보다 수는 많고 공유 mutable 상태
  구조는 미조사.

## not_proven / 후속 (빌딩 보고 유지)

1. **case_runners.py 공유기계 여부 — 미수행** (레인 바운디드 제약이 타 파일 정독을 막음;
   closure가 non-binding `verification_gap` concern으로 정확히 보고). 후속: C1 헬퍼존 vs
   case_runners.py 픽스처 기계 diff 전용 1레인 조사.
2. 52-vs-53 헬퍼 카운트 기준 미조정 (중첩 클로저 포함 여부).
3. 런타임 pass/fail 미실행 (전부 정적 구조 읽기).
4. 레인들이 task.md 반환스키마 표를 못 찾고 required_return_shape로 폴백 — one-call
   `build()`에서 goal→task.md가 레인 프롬프트에 노출되는지 엔진 확인 필요 (운영 교훈 후보).

## §4 항목 1/2 순서에 주는 함의 (COO 판단)

- 항목3의 산출이 항목2(case_runners 분해) 설계의 전제라는 가설은 **아직 미증명** —
  공유기계 비교 후속 레인이 먼저다 (반나절급 1레인).
- 이 파일의 실분해는 "check() 5.5k줄 함수 분해" 문제로 재정의됨 — 정본 문서 §4-3의
  다음 단계 설계 시 C1/C15 선추출 + C2–C14는 패밀리별 함수 캐빙이 별도 설계 대상.
