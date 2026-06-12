# 3축 증거 부검 발주서 템플릿 (evidence-postmortem) — Smith·운영자 합의 0612

짝: 이 task.md 템플릿 + `building-chain-preset:recon-fleet` (읽기전용 함대: inspect →
코드/축/증거 3렌즈 → fan-in 폐장 종합). 빌딩이 실패/보류/스톨을 겪으면 운영자 직감이
아니라 **이 빌딩이 증거에서 3축 귀속을 추론**한다.

사용법: 아래 본문을 task_statement로, 대상 빌딩 id들을 [TARGETS]에 채워
materialize_building_intent(chain_preset_ref="building-chain-preset:recon-fleet",
selected_adapter_ref="adapter:codex-local", write_scope 없음=읽기전용)로 발주.

---

# Evidence postmortem — 3-axis fault attribution for [TARGETS]

## Targets (building roots, READ-ONLY — never modify; copy to temp if needed)
- project/brick-protocol/buildings/[TARGET-1]
- (… 분석 대상 빌딩 루트 나열; 실패·보류·스톨·재시도가 있었던 빌딩)

## Evidence sources per root (read these, nothing else outside the roots + named templates)
1. raw/link.jsonl — transitions, gates, holds (reason_refs), dispositions, lifecycle rows
2. raw/agent-return.jsonl + raw/agent-received.jsonl + raw/adapter-error.jsonl —
   performer receipts/returns/errors (message_excerpt only; bodies are scrubbed by law)
3. work/task.md + work/declared-building-plan.json — the declared work contract
4. work/step-outputs/* (mtime timeline) + capture/events.jsonl — walk rhythm, stalls, retries
5. The brick spec + return.yaml of any step that failed its return
   (brick/templates/bricks/<kind>/) — what shape the contract demanded

## Attribution method (the inference discipline — apply per incident found)
For EVERY failure/hold/stall/retry incident in the targets, answer in order:
- **Brick(계약) 귀속인가?** 지시문이 모호·과중·유도결함이었나? 요구 반환 모양이
  수행자가 지키기 어렵게 쓰여 있나? 신호: 같은 스텝이 다른 문장에서는 빨랐다 /
  같은 양식 위반이 수행자를 바꿔도 반복된다 / 템플릿 prose가 금지 키를 사실상 유도한다.
- **Agent(수행자) 귀속인가?** 반환 양식 위반, 어댑터 에러/타임아웃, provider 스톨?
  신호: 같은 입력 재시도에서 결과가 달라진다(비결정 흔들림) / 초소형 건강 프로브와
  대조했을 때 provider는 멀쩡하다.
- **Link(이동) 귀속인가?** 게이트가 잘못 막았나(거짓 홀드), 열어줬나(거짓 통과)?
  처분·전환 기록이 실제 걸음과 어긋나나? reroute/예산이 잘못 소비됐나?
- **support(기록기) 귀속인가?** 위 셋이 아니라 증거 자체의 불일치인가
  (트레이스↔매니페스트, 투영 오독, 직렬화 순서)? 신호: 체커가 RED를 무는데
  걸음 자체는 건전했다.
한 사건이 두 축에 걸치면 1차 귀속(근본)과 2차(증상)를 나눠 적는다. 추측 금지 —
모든 귀속 주장에 evidence ref(파일+행/raw_ref)를 단다.

## Required output shape (closure synthesis; per incident)
- incident: 한 줄 사실 (무엇이 언제 어디서)
- owning_axis: Brick | Agent | Link | support  (+ secondary_axis 있으면)
- evidence_refs: raw_ref / 파일경로 목록 (주장당 1개 이상)
- repair_candidate: 처방 후보 한 줄 (수리 빌딩감인지, 템플릿 소수선감인지, 재시도감인지)
- not_proven: 이 분석이 증명하지 않는 것
incident가 0이면 "incident 없음"을 명시. 빈도 패턴(같은 가족 반복)은 별도 줄로 종합.

## Hard constraints (law)
- READ-ONLY: 대상 루트·repo 어떤 파일도 수정 금지. write_scope 미선언(읽기 함대).
- success/failure/quality/approved/movement_choice 금지 — 귀속은 사실+근거,
  판정은 사람/coo의 몫.
- 패킷 구조 되울림 금지; plain-text refs만. npm/node 실행 금지.
- 새 귀속 가족을 발견하면 그 정의를 output에 명시 (운영자가 분류표·체커로 승격 판단).

---

## 비고 (운영 맥락)
- 이 템플릿은 운영자 스킬(brick-hold-triage, 즉석 분류)의 **공장판**이다: 스킬=벨 울린
  순간의 응급 분류, 부검 빌딩=장부에 남는 정식 원인 규명. 응급 분류가 끝난 사건도
  부검 빌딩이 재검하면 귀속이 뒤집힐 수 있다 (예: "task.md 무게"(Brick)로 본 스톨이
  부검에서 Agent(provider 흔들림)로 재귀속될 수 있음 — 증거가 결정).
- 첫 발주 후보: 0612 밤 사건들 (F14 설계 스톨 2회, 폐장 반환 양식 위반 2회,
  F14/F15/F16 증거 구멍) — 대기열 ⑥(마당 회고 함대)의 선행 실전.
