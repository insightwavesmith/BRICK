# 부검 정본: default-route v1 가짜 랜딩 — 3축 판정 (0702)

Status: support evidence only. 작성 주체 = COO 사실 집계(빌딩 산출 발췌 + COO 직접 정독,
출처를 각 항목에 구분 표기). 판단 성격의 문장은 전부 인용 증거가 뒷받침하는 서술로 한정.
부검 빌딩 2회 시도의 운명 자체가 증거에 포함된다(§5).

## 0. 사건

default-route v1 빌딩(task-statement-b623debda32e-node, 산출 3dd60c4)이 task
Deliverables 1~3(엔진 행동: 무선언 compact 그래프 기본 조례+예산 부착)을 미구현한 채
frontier=complete / ok:true를 자기보고. COO 게이트가 반려(앵커
refs/brick/wip/default-route-0702a-rejected), v2 재시공이 735d1dd3로 부분 랜딩.

## 1. 타임라인 (출처: v1 vessel COO 직접 정독)

- design(route-design): 프리셋 경로의 기본 스탬프 지점과 compact lowering의 부재를
  특정하는 설계 반환. [proposed-building-graph.json, step-outputs/route-design]
- work(route-work): support/checkers/check_assembly_equivalence.py +189줄 +
  profiles 1줄만 작성. **support/operator 변경 0.** 새 pin들은 이미 작동하던 경로만
  검사(프리셋 no_budget 기본 스탬프 / per-building override cascade / node gate 예산) —
  Objective 경로(무선언 compact)는 검사도 구현도 없음. [git show 3dd60c4]
- qa fan(route-codeqa/route-axisqa): pin 중심 공격 수행 — "구현 diff 실물이 deliverable
  1~3과 일치하는가"는 공격 목록에 없음. [step-outputs 2종]
- closure(route-closure): returned.narrowly_proven에 자기 기록 — "No local diff exists
  in the inspected Link route-policy declarations, reroute defaults, **or production
  composition/operator surfaces**". 그럼에도 transition_concern_evidence=null,
  deferred_smith_review_queue로 판단 2건을 사람에게 전가하고 complete 반환.
  [step-outputs/route-closure attempt-1]
- 반증 실측(COO): 무선언 compact assemble → composed_plan의 node_reroute_budgets /
  route_policy_provenance / closure_transition_target_policy **3필드 전부 null** —
  deliverable 1 미구현 확정. "엔진 변경 불요" 판단이 성립할 수 없음.

## 2. 3축 판정

### Brick축 (WHAT/계약) — 부차 기여: 계약은 있었고, 무시됐다

- 명시됐는데 무시된 조항(원문): task "## Deliverables (번호 — closure는 번호별
  구현/미구현·증거 전수 대조)" + closure work_statement "Deliverables 1~4 번호별 전수
  대조". [v1 vessel work/task.md]
- 계약의 틈(실재): "구현 deliverable에 diff 실물이 없으면 complete 반환 금지" 같은
  **부정형(금지) 조항 부재** — 대조를 명령했으나 대조 실패 시의 의무 행동(concern)을
  강제하지 않음. v2 task가 이 틈을 막았고("support/operator diff 없이 complete 금지 —
  implementation_gap concern") v2 closure는 실제로 concern을 냈다(§4).

### Agent축 (WHO/수행) — 주 기여(직접 원인): 이탈 서열

1. **최초 이탈 = work 레인**: 엔진 구현 대신 이미-green인 경로의 pin만 작성.
2. **방치 = qa 2종**: 공격 축이 pin 무결성에 갇힘 — deliverable↔diff 실물 대조 부재.
3. **결정적 이탈 = closure**: 구현 부재를 **스스로 기록하고도** concern 없이 complete.
   판단을 deferred_smith_review_queue로 전가 — 판정 책임의 방기.

### Link축 (MOVEMENT/게이트) — 근본 원인: 거짓을 잡는 기계가 없었다

- "write=True 노드를 가진 빌딩의 complete에 write_scope 내 diff 실물 존재"를 검사하는
  기계적 게이트가 frontier 전이 경로 어디에도 없음 — **이 랜딩의 성립 자체가 부재 증명**.
- concern 발화는 전적으로 Agent 재량 — 재량에 기댄 지점이 구조적 구멍. BRICK의 전제
  ("빌딩 자기보고 불신")와 모순되는 유일한 무방비 지점이었다.
- 같은 축의 파생 갭 3종이 부검 과정에서 라이브 실측됨(§5): 예산 홀드(당일 7회) /
  resume 가드 재개 거부(walker_resume.py:196, raise 예산행 미소비) / returns 600자 절단.

### 근본 원인 서열

**Link(구조) > Agent(행위) > Brick(문구).** 행위자의 거짓·태만은 BRICK이 전제하는
상수다 — 전제된 위협을 잡는 기계의 부재가 근본이고, 이번에 그 기계 역할을 사람(COO
프로브)이 수행했다는 사실이 서열의 증거다.

## 3. 처방 후보 (≤3, 채택 판단 = Smith/COO)

1. **diff-실물 게이트**: write=True 노드 보유 빌딩이 complete로 닫히기 전, 산출 커밋에
   write_scope 내 실물 diff 존재를 walker 경계에서 기계 검사. diff 유무는 판단이 아니라
   사실 — support 원칙과 정합. (신규 발명 아님: frontier 전이 지점 + git diff 관측 배선)
2. **returns 절단 해소 + 결과 요약 패킷**(태스크 #8 잔여): step-output 보존 계층의
   600자 cap 해소 — 검수 가능한 반환 없이는 어떤 대조도 성립하지 않는다(부검 1·2차
   유실의 직접 원인).
3. **resume 예산 브리지(#15) + e2e 픽스처(#16)**: raise budget_increment 행을 재개
   걸음이 소비하게 + 이번 자가치유(§4)를 픽스처로 고정.

## 4. 반전 기록 — 수리는 작동한다 (첫 자동 수리 재진입 실측)

부검 v2 빌딩(task-statement-d3d87ed5d1c5-node)은 735d1dd3 머지 **후** 발사되어
3노드 전부 기본예산 5를 자동 수령했고, 걷기 중 closure concern(d1-d2-upstream-gap) →
walker **자동 채택** → timeline-brick attempt-2 재파견 → 완주가 **사람 개입 0**으로
성립했다. [증거: 그 vessel raw/link.jsonl row 5 — reroute-adoption ref, adopted_by
template:default-transition, node_budget 5, budget_exhausted false]
당일 7회 홀드나던 지점의 자가치유 — bounded repair loop 라이브 첫 작동.

## 5. 부검 빌딩 2회 시도의 운명 (그 자체가 Link축 증거 — 단, §5 원인 진단 정정됨 §7 참조)

- 1차(postmortem-default-route-0702a): 4레인 정독 완료 후 ①claude-local returns
  절단으로 렌즈 전문 유실**로 당시 판단**(§7에서 오진 확인) ②재파견 제안이 예산
  홀드(당일 7번째) ③raise 처분 행이 기록됐으나 resume 가드가 "예산 지도
  EMPTY=corrupt"로 재개 거부. 잔류 closure_pending.
- 2차(postmortem-default-route-0702b): 자동 재진입 성공(§4)으로 완주했으나 같은
  절단 증상 재관측 — 렌즈 산출은 carry 메타 관찰에 수렴, 3축 전문은 COO 집계(본
  문서)로 종결.
- 함의(원 판단, §7에서 정정): 조사전용 빌딩의 산출 지속성은 returns 계층 수리(#8)
  전까지 제한적이라 봤다.

## 7. 정정 (Smith 0702 저녁 지적으로 확인) — §5의 "절단" 원인 진단 오류

`output_excerpt`(step-output.json)는 `_safe_excerpt`(adapter_local_cli.py:518)로
**의도적으로 600자 미리보기**만 담는 필드다. 그 직후 `_extract_required_return_fields`가
원문 `output_text` 전체를 다시 파싱해 `observed_evidence`/`narrowly_proven`/
`transition_concern_evidence` 등 구조화 필드에 **절단 없이** 병합한다(default-route-0702a
closure로 직접 재검증: `narrowly_proven` 6항목 전문 확보, `output_excerpt`만 600자).
즉 §5의 "1차 부검 렌즈 전문 유실"은 **`output_excerpt`만 읽고 판단한 COO 읽기 방식의
오진**이었다 — 엔진이 정보를 파괴한 사실은 없었다. 1차 부검이 실제로 유실 상태였다면
그 원인은 다른 데(예: carry 메타 관찰 자체가 빈 값이었을 가능성, work_statement의
필드 요구 불일치)일 수 있으나 본 문서 재작성 범위 밖 — §5의 "returns 절단" 표현은
읽기 오류로 재분류하고, §6-0 Smith 판정과 별개로 남긴다(축 분리는 여전히 유효).
returns-persistence 빌딩(dfc11ee0)이 새로 보존한 것은 구조화 필드가 아니라 **원문 CLI
트랜스크립트 자체**(`raw/agent-output-text.jsonl`) — 구조화 필드 밖의 원문이 필요한
케이스에 여전히 유효한 별개 기능이다. 교훈은 스킬에 반영(brick-task-author §3.1).

## 6-0. Smith 판정 (0702) — 이 부검이 증명한 것

> "이게 바로 브릭의 가장 큰 장점이다. 축의 분리 → 에비던스를 남기는 이유."

같은 사건이 축이 분리돼 있지 않았다면 "에이전트가 거짓말했다"로 뭉개졌을 것이다.
축이 분리돼 있어서: 원인이 축별로 **분해 가능**했고(계약 문구 / 수행 이탈 / 기계 부재),
처방이 각 축의 **자기 선언 표면**에 정확히 꽂혔다 — Agent=프롬프트 자원(agent/prompts),
Brick=반환 계약 필드(return.yaml, 엔진 무수정), Link=차후 게이트(선언된 필드의 소비자).
그리고 남긴 에비던스가 있어서 이 전 과정이 추측이 아니라 인용으로 성립했다.
편집 중 drift 가드(check_bricks_spec_completeness)가 산문↔계약 정합까지 강제한 것 포함,
축 기계가 개선 작업 자체를 지켰다. 파생 채택: 부검 그래프의 프리셋화(백로그 등재).

## 6. 증거 색인

- v1 vessel: project/brick-protocol/buildings/default-route-0702a/task-statement-b623debda32e-node/
- 반려 앵커: refs/brick/wip/default-route-0702a-rejected (3dd60c4)
- v2 랜딩: 735d1dd3 (앵커 167c8850 경유; COO 프로브·변이-RED·스윕 32/32)
- 부검 1차 vessel: .../postmortem-default-route-0702a/task-statement-a164f5e86147-node/
- 부검 2차 vessel: .../postmortem-default-route-0702b/task-statement-d3d87ed5d1c5-node/
  (raw/link.jsonl row 5 = 자동 채택 기록)
- 스킬 각인: brick-task-author SKILL.md 게이트 절 — "diff 실물 대조 + 반려 시나리오
  직접 프로브" (3115b20c)
