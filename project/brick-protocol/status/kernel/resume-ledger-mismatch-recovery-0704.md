# 거부-후-정정 경로 선언 — resume 원장 불일치 fail-closed 이후 사람이 할 수 있는 것 (0704 — T7 S-c 수확)

Status: support evidence only. T7 S-c 수확(t7scsd-recovery-decl-0704a, 레인 초안을
COO가 렌더·커밋 — 원문: 해당 vessel work/step-outputs). source truth·성공 판정·품질
판정·Movement 권한 아님.

## 가드 실존 정합 (레인 재확인)

{
 "gating": "두 가드 모두 resume 경로에서만 도달 — walker_resume_seed.py:179 (resume_seed is None → 즉시 return, 라이브) / walker_kernel.py:1068 (resume_seed is None 분기). _require_return_frontier_consistency는 resume seed-build 경로에서만 호출(walker_resume.py:246). fresh forward walk는 도달 불가.",
 "guard_1": "support/operator/walker_resume.py:245-259 — expected_replay_counts=_completed_step_frontier(root)(:245) → _require_return_frontier_consistency(:246-250) + per-step len(returns)>completed raise(:253-259). 실존 확인.",
 "guard_1_impl": "support/operator/walker_resume.py:1231-1253 — _require_return_frontier_consistency: completed>recorded 이면 raise('step-output frontier is ahead of raw/agent-return.jsonl -- refusing to resume before replay adoption', :1240-1245); 추가로 completed 의무 존재 시 evidence/claim_trace/agent/returned_claims.json 부재도 raise(:1246-1253).",
 "guard_2": "support/operator/walker_resume_seed.py:189-195 — 프런티어 이전(index<expected) 점유의 recorded 반환 부재 시 raise('completed before the HOLD ... has no recorded Agent return to replay; refusing to silently run it live'). 실존 확인.",
 "verdict_note": "가드는 전부 실존하며 fail-closed로 설계대로 작동. 재작업 제안 없음(law)."
}

## what the deny is

resume은 두 원장을 대조해 계속한다: (a) work/step-outputs/<slug>-attempt-N (스텝 완료 즉시쓰기 원장, _completed_step_frontier), (b) raw/agent-return.jsonl + evidence/claim_trace/agent/returned_claims.json (걸음-종료 시점 기록). (a)의 프런티어가 (b)보다 앞서면(또는 claim_trace 부재면) resume은 'corrupt evidence'로 raise하고 재개를 거부한다(walker_resume.py:1240-1253, :253-259, walker_resume_seed.py:190-195).

## why mismatch happens

step-output은 각 스텝 완료 시 즉시 append되고, raw/agent-return.jsonl은 별개 트랜잭션(걸음 종료 일괄)이다. 스텝 완료 즉시쓰기 직후·걸음종료 기록 전에 프로세스가 사망하면 (a)>(b)로 원장이 어긋난다 — 이는 fail-closed 설계의 정탐이며, 오염 원장을 라이브 재실행으로 둔갑시키지 않으려는 방어다(walker_resume.py:238-243 주석).

## observation command

거부 직면 시 사람이 읽어 불일치를 확인하는 것: (1) work/step-outputs/*/step-output.json 중 step_ref별 개수 = (a) 프런티어; (2) raw/agent-return.jsonl 의 해당 step_ref 라인 수 = (b); (3) evidence/claim_trace/agent/returned_claims.json 존재 여부. (a)>(b) 또는 (3) 부재가 거부 사유. 어느 step_ref가 앞섰는지가 에러 메시지에 이미 인용된다.

## legal path

정본 회복 경로 = FRESH 재발주(새 building 발주). 신규 building은 replay 의무가 없어(expected_replay_counts 전부 0, walker_resume_seed.py:179·184 → 라이브) 불일치 가드가 발화하지 않는다. 이는 정본 우회가 아니라 정본 경로다 — 중단된 building의 원장은 durable 증거로 잔류(감사용). 0704 t7sa 선례(repo-무수정 조사 = fresh building, fake-landing 홀드가 정상)와 정합.

## forbidden path

원장 손편집 금지: step-output 디렉터리 삭제/추가, raw/agent-return.jsonl 가짜 라인 append, returned_claims.json 위조 — (a)와 (b)를 인위로 맞추면 fail-closed 보장을 무력화하고 HOLD 이전 스텝을 provider에 라이브 재실행시켜 원본 walk와 발산한다(walker_resume.py:242-243, walker_resume_seed.py:192-195의 정확한 방지 대상). 절대 금지.

## hold reason branch

이 거부는 disposition HOLD가 아니라 resume seed-build 무결성 거부다. _require_return_frontier_consistency는 action(raise/forward/stop/reroute)과 무관하게 seed 조립 시 발화(walker_resume.py:246, budget_delta 분기 :264-272 이전). 따라서 정정 경로는 hold_reason별 분기 불요 — 모든 재개 시도에 균일. (단, budget_increment raise 검증 :266-272는 별개 층이며 이 무결성 거부와 독립.)
