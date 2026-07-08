# 발주 아키텍처 기획서 — COO 피드백 (codex 개정용, 0708)

> C3 status note: C2 import-unify is now landed on origin/main (`7b99b8f7f`, --all rc=0). This order/발주 architecture feedback is next active design input for operator-safe launch envelope v1. Route policy remains out of scope for this track.


대상 문서: `BRICK_order_architecture_implementation_plan.md` (13장)
검증: Explore 10항목 코드 대조 @ C1 (`af60198cb`). 원장 §T-정정 동반.
성격: **문서 개정 요청. codex가 이 피드백으로 기획서를 고친다. COO 임의 재설계 아님.**

---

## 총평

문서의 **방향은 옳다** — 외부 표면 단순화(one command → Plan Card → Run → Gate Digest → COO action) + 내부 반려를 공통 route_concern로 통일 + AI 앵커링을 입력격리로. 축 경계도 정확.

**그러나 "기존 자산 위에 얹힌다"는 전제가 실측과 어긋난다.** 문서가 신규로 제안한 것의 대부분이 이미 리포에 존재하고, 기존 쪽이 대체로 더 성숙하다. 문서는 이들을 **인용하지 않고 평행 재구현/재명명**한다 → 얹는 게 아니라 **이중 어휘·이중 잠금·봉인 분열**.

개정 방향 한 줄: **"새로 만든다"를 "기존 X를 확장한다"로 재정위**하고, 아래 봉인·기존구현과의 관계를 문서에 명시하라.

---

## 시공 전 필수 해소 4건 (이게 안 되면 채택 불가)

### 1. concern_kind 봉인 8종과 정합 (고위험 — human gate)

**봉인 실물 (3중 단일소스):**
- `brick_protocol/agent/return_fact.py:10-21` — `TRANSITION_CONCERN_KINDS` 8종: design_gap, implementation_gap, upstream_gap, boundary_mismatch, insufficient_input, replay_needed, verification_gap, unknown
- `brick_protocol/brick/templates/bricks/transition-concern-return.yaml:10`
- `brick_protocol/link/route_policies/basic_qa_repair.yaml:38-50` (concern→route 매핑)
- `validate_transition_concern_evidence` (return_fact.py:250-251) 가 enum 밖 fail-closed

**문제:** 문서 §4.7/§4.8/§4.9가 서로 다른 concern_kind 목록을 쓴다(문서 내부 3곳 불일치). 봉인 8종 중 upstream_gap·replay_needed·unknown을 조용히 버리고, evidence_gap·integration_gap·qa_defect·closure_gap 4종을 신규 추가.

**개정 요청:**
- 문서 §4.7/4.8/4.9의 concern_kind를 **하나로 통일**하라.
- 봉인 8종을 유지하되 필요한 신규(evidence_gap 등)만 **명시적 확장 절차**로: 3중 단일소스(return_fact.py + transition-concern-return.yaml + basic_qa_repair.yaml) + validate + 체커를 동시에 여는 절차를 문서에 담아라. 이건 fact-class shape 변경(AGENTS.md:453) = human gate 대상임을 명시.
- 버릴 3종(upstream_gap 등)이 정말 불필요한지 논증하거나 유지하라.

### 2. Blind Pack이 현재 fake-landing 방어를 안 깨뜨린다는 증명 (치명)

**충돌 실물:** `brick_protocol/brick/templates/bricks/code-attack-qa/brick.md`:
- L31-34: QA 입력 = **"the prior Brick's report (carried via Link edge) + changed files + evidence the upstream Brick returned"** — QA는 producer 반환을 **의도적으로 본다.**
- L43-48: QA 핵심 임무 = **"upstream work node의 self-reported made_changes/changed_files를 실제 diff와 대조"** (0702 fake-landing 부검 근거)
- L50-54: Outer-lens duty — 앵커링은 **fixture 재사용 금지**로 막고, producer 주장은 **공격 대상으로 노출**

**문제:** 문서 §4.6 Blind Pack은 producer_final_summary를 verifier 입력에서 **제거**하라 한다. 그러나 현재 code-attack-qa는 그 report를 받아 "made_changes:true인데 diff 없음"을 잡는 게 임무. 문서 적용 시 **지금 잡도록 설계된 가짜 착지를 못 잡는다.** 두 앵커링 철학이 양립 불가:
- 현재: 주장 노출 + 독립 재현 강제(fixture 금지)로 앵커링 방어
- 문서: 주장 은닉으로 앵커링 방어

**개정 요청:** 둘 중 하나 —
- (a) Blind Pack에서 producer의 **결론/verdict는 숨기되 사실주장(made_changes/changed_files/diff)은 노출**하는 것으로 세분화 — 그러면 fake-landing 대조가 살아남는다. 이게 유력.
- (b) fake-landing을 다른 방식(예: 엔진이 diff를 직접 첨부)으로 잡는다는 설계 제시.
- 어느 쪽이든 "code-attack-qa/brick.md의 주장-diff 대조 임무가 유지된다"를 문서에 증명하라.

### 3. Plan Lock ↔ 기존 declared-plan revision chain 관계 명시

**기존 실물 (문서 미언급):** `work/declared-building-plan.json` = birth certificate + `declared-building-plan.rev-N.json` **append-only 해시 체인**:
- `check_plan_revision_chain.py` — 부모 해시 검증, extends_plan_hash 일치 강제, step add-only, budget 필드 불변
- 확장은 `expansion-approvals.jsonl` + `link-gate:expansion-approval` 게이트 필수

**문제:** 문서 §4.5 Plan Lock(graph/lens/profile lock + mutation은 route_concern/COO disposition 필요)은 **이 revision chain이 이미, 더 엄격하게 하는 일**이다. 두 잠금 메커니즘 공존 시 어느 게 진실인지 불명. "새 엔진 금지"(§10.1)와도 상충(Plan Lock은 새 lifecycle 상태).

**개정 요청:** Plan Lock이 revision chain을 **대체/공존/폐기** 중 무엇인지 택1하고 명시. 권장: Plan Lock을 신규 상태로 만들지 말고 **기존 declared-plan + revision chain 위의 얇은 read 뷰**로 재정의(birth cert가 이미 lock이다).

### 4. route_scope ↔ 기존 route_materialization 관계 명시

**기존 실물 (문서 미언급):**
- `brick_protocol/link/route_policies/basic_qa_repair.yaml`: 이미 owner_axis=Link, concern_kind→requested_route_scope 매핑, **verification_gap 의도적 제외 명시**(L51-54)
- `brick_protocol/support/operator/route_materialization.py:78` `materialize_transition_concern_disposition` — concern→route_scope를 **이미 실행**. author_ref 금지 프리픽스(support:/agent:/provider:) L457-461에서 **이미 봉인**(brick_protocol/link/spec 단일소스)

**문제:** 문서 §4.9 route_scope + §8 check_route_scope_authority가 route_materialization + link/spec 봉인과 **중복 재구현**. 기존이 더 성숙(literal-match state machine, link_decision_packet evidence view).

**개정 요청:** route_scope를 신규 파일로 만들지 말고 **route_materialization 확장**으로 재정위. 문서의 route_scope 필드(carry_forward_refs, affected_verification_refs, recompute_join_refs 등)를 기존 route_replay_plan(brick_protocol/support/operator/route_materialization.py:305) 구조에 **매핑**해서 제시. §S(코덱스 route 설계)도 이 재정위에 종속.

---

## 그 외 재발명 (중복 — 문서가 인용하고 재정위할 것)

| 문서 신규 주장 | 기존 실물 | 조치 |
|---|---|---|
| §4.2 profile 4종 | 프리셋 30종(brick_protocol/brick/templates/presets/) + high-risk-change-inspected.md·quick-check.md 등이 거의 동일 + casting_tier/lens 축(b16552bb0) | profile을 프리셋 위 뷰로. **casting tier/lens 축을 반드시 통합**(문서 전무 = 공백) |
| §4.10 Gate Digest | reporter.py + coo_operating_chain.py projection | 기존 projection 위 blocker-first 재정렬 레이어로 |
| §4.7 verification_return 어휘 | review/return.yaml:8-17 (observed_evidence·narrowly_proven·not_proven 존재), kind별 tailored shape + forbidden_return_keys 봉인 | 단일 universal return로 flatten 말 것 — kind별 shape 존중 |
| §5.2 verification_gap 비리라우트 | return_fact.py:22 + basic_qa_repair.yaml:51-54 + brick.md:84-87 (3중 봉인) | "새로 만든다" 삭제, "이미 봉인됨" 인용 |
| §4.1 write_scope.mode | Brick write_scope + Agent tool policy 이중 봉인(AGENTS.md:191-196) | 단일 mode 어휘 재발명 말 것 |

---

## 위험 Phase (개정 후 시공 순서 참고)

- **Phase 7 (최고위험)**: walker_kernel.py 3053줄 / **26개 모듈 의존** + walker_resume.py 1793줄 수정. routing rule = high-impact(AGENTS.md:451), MAG-0/human 게이트. 개헌 이주(§R) 착지 후에만.
- **Phase 1 (고위험)**: concern_kind/return 스키마 = 3중 봉인 분열, fact-class shape = human 게이트.
- **Phase 6 (중복위험)**: route policy 재구현 — 4번 해소가 선행.
- **Phase 2~5 (재발명)**: 기존 프리셋/reporter/coo_operating_chain 위 얇은 레이어로 재작성 가능한데 문서는 처음부터 새로 짬 — 개정으로 반경 축소.

---

## 개정 산출물 요청

codex는 위 4건 해소 + 재발명 5건 재정위를 반영한 **기획서 v2**를 낸다. v2는:
1. 각 신규 제안 앞에 "기존 X(file:line)를 확장/재정위"를 명시
2. concern_kind 통일 목록 + 봉인 확장 절차
3. Blind Pack 세분화(verdict 은닉 / 사실주장 노출) 설계
4. Plan Lock·route_scope의 기존 메커니즘 관계 택1
5. casting tier/lens 축 통합

v2 도착 후 COO 재검증 → Smith 채택 판정.
