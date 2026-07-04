# raise 예산 브리지 재현 조사 (0704 — T7 S-a 수확, t7sa-budgetbridge-0704a)

Status: support evidence only. 0702 resume 결함① "raise가 쓴 예산 주입 행을 재개가
안 읽음"의 현재 상태를 끝-대-끝 재현으로 확정한 조사 산출. COO 수확·커밋
(레인 계약이 repo 무수정이라 산출은 구조화 반환으로 돌아옴 — 원문:
buildings/t7sa-budgetbridge-0704a work/step-outputs). source truth·성공 판정·품질
판정·Movement 권한 아님.

## 판정: 브리지 완결 (결함① stale — S-a2 엔진 수리 불필요)

/tmp 격리 adapter:local 픽스처 빌딩으로 재현: reroute 예산 소진 →
budget_exhaustion HOLD → `run_approve_entry(action="raise", budget_increment=3)`
→ resume. 관측:

- `after_node_reroute_budgets`: 대상 노드 **4** (원예산+주입분 반영)
- `after_node_reroute_landings`: **2** (주입 후 추가 재파견이 실제 허용됨)
- `after_frontier_kind`: complete
- classification: `bridge_observed_budget_increment_reached_kernel_evidence`

## 전달 사슬 (D2 — 전 구간 file:line 실측)

1. `walker_resume.py:265` raise 액션 읽기 → `:266-272` budget_increment 검증 +
   `budget_delta[pending_target]` 기록 → `:312-317` ResumeSeed에 탑재.
2. `walker_kernel.py:1099` 선언 node_reroute_budgets 읽기 → `:1105-1108`
   **resume_seed.budget_delta를 node_budget에 가산** (0704 설계조사의 유일
   미확인 지점 — 이번 재현으로 확정) → `:2361-2363` reroute 기록·예산·랜딩을
   dynamic_walker_evidence로 기록.
3. 부수: `walker_resume_seed.py:291-293`·`:360-362`가 같은 budget_delta를
   resumed lifecycle/관측 필드에 소비.

## not_proven (레인 정직 선언 그대로)

- 중첩(nested) reroute 경로의 예산 거동
- fan/fan-in 노드 예산 거동
- 주입 슬롯 전량 소진(3/3)은 관측 안 함 — 증분 반영과 추가 랜딩 허용까지 실측

## 운영 처분 (0704 COO)

- 백로그 "resume 엔진 결함 3종"의 ①은 stale 처리 — 총량 반영까지 실측 확정.
  잔여는 ②(검증이 persist 이후 발화 — T7 S-b 좌표)와 ③의 "거부 후 정정 경로"
  선언(T7 S-c)뿐.
- 빌딩 자체 기록 1건: repo-무수정 조사 빌딩의 no-diff complete가
  `fake_landing_write_scope_diff_absent` 가드에 걸려 human_review_waiting으로
  주차 — **가드가 설계대로 작동한 것**(0702 가짜 랜딩 방어). 검수 후 forward로
  종결. 교훈: 조사(무수정) 발주는 이 가드 홀드가 정상 경로임을 발주 시점에
  예상하라.
