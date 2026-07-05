# T10 첫 실전 확장 운전 runbook (0705 밤) — S14 채택 + COO 재검증 정본

출처: 지피티 S14 보고(T10 확장 운전 절차 공격, Smith 전달 0705 밤) → COO 현행 HEAD
재검증(4a5c16d4). 발주-준비/운전-절차 문서이며 source truth·성공 판정 아님.
G3(A+ 착수 게이트 마지막 항목 = T10 첫 실전 확장 운전 1회)의 절차 정본.

## 1. S14 발견 6건 검수 이력 — 재발주 금지 목록 포함

지피티 감사는 업로드 아카이브 기준이라 Phase1(fc7dd571)·묶음6(1ce52761) 랜딩분이
미반영이다. **아래 스테일 2건을 S14 근거로 재발주하지 마라** (phases §0 원칙과 동일).

| id | 지피티 판정 | COO 처분 | 현행 HEAD 실물 근거 |
|---|---|---|---|
| S14-T10-001 홀드 identity 재사용 | MAJOR·CONFIRMED | **스테일 — 반증** | 제안 수리가 이미 시공됨: revision packet에 approval_hold_ref 기록(declaration_packets.py:352), _verify_approval_not_consumed가 hold identity도 거부(:737-755, 호출 :732), RED 픽스처 same-hold-new-approval-reuse 실재(check_plan_revision_chain.py:561-574). Phase1 묶음1잔여 산출 |
| S14-T10-002 bool 예산 | MAJOR·CONFIRMED | **스테일 — 3표면 반증** | _verify_expansion_budget_available bool 명시 거부 / _positive_int_mapping bool 거부 / plan_expansion._validate_expansion_node_budgets는 require_positive_int(묶음6 헬퍼) 경유. writer-reader 패리티(Rule 11) 성립 |
| S14-T10-003 strict checker 필수 | MINOR | **수용 — 단계 5로 각인** | reader가 corrupt 최신 rev를 직전 rev로 조용히 후퇴시키는 기전 실물 그대로(declaration_packets.py:369-399). "실행됨"≠"최신 rev 정상" |
| S14-T10-004 approval-only crash retry | MINOR·OK | 수용(문서화) | retry 프로브 실재(check_plan_revision_chain.py:309-312) |
| S14-T10-005 fan-in member_refs | OK | 유지 | plan_expansion.py에서 reject 실측 |
| S14-T10-006 approval 부재/스테일/재사용 | OK | 유지 | 3종 reject 실측 |

## 2. 운전 대상 결정 (0705 밤 실측)

- **cleanup-wave-a-0705 부적격**: base plan `expansion_budget: None`(갭1 c89f1732 랜딩
  이전 출생) — _verify_expansion_budget_available가 fail-closed 거부. 출생 선언 없는
  판에 소급 부여 경로는 없음(의도된 설계).
- **채택: 신규 목적 빌딩** — 출생 시 `expansion_budget=1` 선언(갭1 kwarg), 소형
  design(전제 재확인) → coo 게이트 홀드 → 그 hold identity로 확장 승인 → 조각 이식 →
  resume 완주.
- **조각 v1 폐기(0705 밤)**: 리허설 초안(cleanup-wave-a design 산출)의 커널 아카이브
  이동 3건은 cleanup-wave-b(73673bf9)가 이미 집행 — 지피티 감사 세션의 정합성 발견을
  COO 로컬 재검증으로 확정. 부수 발견 2건: 초안은 엔진 스키마(Brick+Agent rows) 불일치
  + QA 완료 edge 누락 — 그대로 운전했으면 단계 2 거부. **조각 v2** = 잔여 실작업 재단:
  ①census '기타 z6 판정분' 4번째 후보 확정+이동 원장(미확정 경로도 원장 행 diff 강제 —
  fake-landing 가드 정합) ②buildings-residue 분류(제안-전용). 4노드(design×2·work·qa
  fan-in), assemble_expanded_graph_plan dry-run PASS. **교훈: 조각/발주문의 앵커 재확인은
  스키마 dry-run만이 아니라 작업 실존(이미 랜딩됐는가)까지.**
- 운전 직전 확장 조각 지피티 공격 예약(외부감사 핸드오프 §5) — 조각은 미커밋 증거,
  COO가 추출·전달.

## 3. 운전 절차 (S14 §3 채택, 단계 3 주석 1건 정정)

단계 0 — 대상 빌딩 HOLD identity 확인 (evidence-manifest의 dynamic_walker_evidence:
held / hold_reason / paused_at_ref / pending_target_ref).
단계 1 — latest valid plan hash 확인 (latest_valid_declared_plan_packet, declaration_packets.py:370).
단계 2 — expansion fragment dry-run (assemble_expanded_graph_plan 순수함수 — 예산
int 여부·new step_ref 전수 budget map·fan-in member_refs·completed frontier 무침범).
단계 3 — approval row 수동 검사 (work/expansion-approvals.jsonl: 새 approval_evidence_ref /
gate_ref=link-gate:expansion-approval / hold_paused_at_ref = 현재 hold identity).
**정정: 동일 hold identity 재소비는 이제 기계가 막는다**(declaration_packets.py:749-755)
— S14 원문의 "사람이 봐야 함"은 이중 안전으로 강등.
단계 4 — write_declared_plan_revision (declaration_packets.py, exclusive link 쓰기).
단계 5 — **strict checker 필수**: `PYTHONPATH=support/import_identity:. python3
support/checkers/check_plan_revision_chain.py --repo .` (reader fallback 때문에 생략 불가).
단계 6 — resume (run.py:621 resume_building_plan, adapter_cwd는 세션ID 없는 중립 경로).

증거 한계: 이 문서는 support evidence이며 성공 판정 아님. 검증은 0705 밤 HEAD 기준 —
운전 시점에 단계 1~2로 재확인. 처분·품질 판정은 사람 몫.
