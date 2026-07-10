<!-- machine-generated: brick_protocol/support/operator/progress_projection.py — do not hand-edit. 빌딩 증거에서 기계가 다시 생성한다 (generate_project_progress). 같은 증거면 같은 바이트(본문에 생성시각 없음). -->

# Deku — Fugu-Ultra 재현 오케스트레이터 — PROGRESS (기계 투영)

이 파일은 buildings/ 의 빌딩 증거에서 기계가 생성한 사실 투영이다. 성공/품질/완성도 판단은 여기 없다 — 판단은 사람이 다른 곳에 따로 적는다 (TRUTH-before-QUALITY).

## 방향성 (선언 echo — project.json direction)

로컬 Nemotron-8B 지휘자가 구독 워커(Opus/GPT-5.5/Grok)를 지휘해, 재학습 없이 Fugu-Ultra를 완전 재현한다

## 빌딩 집계 — 총 14개

board_state 기준:
- closed: 3
- evidence_incomplete: 9
- link_paused: 2

frontier_kind 기준:
- agent_incomplete: 2
- complete: 3
- evidence_incomplete: 9

## 최근 증거 빌딩 (last_evidence_at 상위 10)

- deku-d3-real-orchestrate-0709 — 2026-07-09T15:25:38Z — link_paused
- deku-d2-real-conduct-0709c — 2026-07-09T15:04:12Z — link_paused
- deku-d1-real-face-0709b — 2026-07-09T14:14:40Z — closed
- deku-g1-g4-verify-official-0709 — 2026-07-09T13:21:48Z — closed
- deku-g0-face-official-0709 — 2026-07-09T13:21:43Z — closed
- (타임스탬프 없는 빌딩 9개는 이 목록에서 제외 — 집계에는 포함)

## 이 파일이 증명하지 않는 것

- 빌딩 작업의 의미적 올바름 (개수·상태는 frontier 관측 사실일 뿐)
- 프로세스 생존 여부 (last_evidence_at 은 기록된 증거 시각이지 심장박동이 아님)
- source truth 아님 / Movement 권한 없음 / 성공·품질 판단 없음
