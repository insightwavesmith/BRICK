# resume 결함 3종 기전 정본 (0702 심야 — 조사 빌딩 착지 집계)

Status: support evidence aggregation. 출처: resume-corrupt-investigation-0702a(트리거 확정)
/-0702b(기전 규명) vessel closure 구조화 필드 + COO 좌표 직접 재검증(0702 심야).
**목적: 격리 샌드박스에서 걷는 레인이 읽을 수 있는 커밋된 정본** — 조사 원본은 untracked
vessel에만 있어 레인 워크트리에서 보이지 않는다(0702 실측). 판단 없음, 사실만.

## #15 — raise 예산 미소비

- raise 처분은 `support/operator/walker_hold.py:164-190`에서 lifecycle 행에
  `budget_increment`를 기록한다(:187-190 `_positive_int` 검증).
- 재개 걸음이 그 행을 예산 지도에 싣지 않아 `support/operator/walker_resume.py:190-200`
  "reroute budget ... EMPTY; refusing to resume with no budget map" 가드에 걸린다.
- 소비 경로 후보(현존 메커니즘): `support/operator/walker_resume_seed.py:291-308,384`
  (`resume_seed.budget_delta` → `budget_increment=` 스탬프).
- **가드는 옳다** — 수리 지점은 상류 브리지(raise 행 → 예산 지도)다.

## #19 — 처분 자기잠금

- 잘못된 클래스 처분(비예산 홀드에 raise)은 `walker_resume.py:405-415`
  `_require_budget_exhaustion_raise`가 명시 거부한다(**이 가드도 옳다**).
- 그러나 거부된 시도 행이 원장에 남아 `walker_resume.py:127`
  "dynamic Building already has an applied resume disposition" 계열로 후속 정정
  (forward)·재개까지 막는다. 처분 행 읽기는 :130 `_read_disposition_row`.
- 수리 후보: 클래스 검증을 persist **전**으로 이동(원장 청결 유지) 또는 리더가
  거부-확정 행을 스킵 — 단순한 쪽을 design이 근거와 함께 확정.

## #21 — 원장 불일치 (완주 스텝-출력 > raw 반환)

- step-output은 스텝 종료 **즉시** 기록: `support/operator/run.py:1189-1193` →
  `support/recording/step_outputs.py:58 write_step_output` → `:505 _write_json`.
- raw/agent-return.jsonl은 걸음 루프 **종료 후 일괄** 기록:
  `support/operator/walker_kernel.py:2405-2415 write_accumulated` →
  `support/recording/raw_claim_trace.py:21 write_raw_and_claim_trace` → `:381 _write_jsonl`.
- 조사 narrowly_proven 원문: "not written by one function, one transaction, or one
  shared lock/rollback wrapper". 걸음 중단 시 "완주 스텝-출력 frontier > raw 반환 수"
  도달 가능 → `walker_resume_seed.py:185-195`가 replay 채택 시점에 거부
  ("no recorded Agent return to replay").
- 처방 후보(조사 remaining_delta 원문 요지): ①기록면은 비수리 유지 + 명시 체커 +
  선언된 수리 슬라이스 ②**pre-resume 정합성 대조**(step-output frontier vs
  raw/agent-return + claim_trace 존재, replay 채택 전) — ②가 유력.
- 기록면 트랜잭션 재설계는 범위 밖: 코드 주석 자체가 torn-pair를 "별도 수리
  슬라이스의 검출 가능 이상"으로 취급(`support/recording/spine.py:852-904, 953-977` —
  파일별 원자 교체는 있으나 쌍 단위 원자성은 의도적으로 없음).

## 재현 선례

- 0702b 조사의 L5 렌즈가 **내부 유닛 직접 호출**로 #15/#19 거동을 재현했다
  (비예산 홀드 raise 거부 / 정당 예산소진 raise 수용 / 착지 부족 소진 주장 거부).
- 원본 vessel(라이브 repo 전용, 워크트리에선 부재):
  `project/brick-protocol/buildings/resume-corrupt-investigation-0702b/task-statement-22b172b10966-node/`
  (closure = `work/step-outputs/task-statement-22b172b10966-node-ri2-closure-attempt-1/step-output.json`)
