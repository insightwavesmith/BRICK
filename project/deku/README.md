# Deku — Fugu-Ultra 재현 오케스트레이터 — 프로젝트 헌장

이 문서는 이 동네(project/deku/)의 헌장이다. 여기서 일하는 모든 사람과
에이전트가 먼저 읽는다. 기계 선언은 project.json(이 헌장의 그림자)에 있다.

## 목적 (왜 존재하는가)

Sakana Fugu-Ultra의 작은 지휘자 + 거대 워커 오케스트레이션을, Smith의 구독 워커와 로컬 8B로 재현하기 위해

## 생성 이유 (왜 지금)

학습된 Nemotron-Orchestrator-8B를 로컬 확보했고, codex provider 배선까지 성공해 재현의 마지막 단계(지휘자 컨텍스트 관리)만 남음

## 방향성 (어디로)

로컬 Nemotron-8B 지휘자가 구독 워커(Opus/GPT-5.5/Grok)를 지휘해, 재학습 없이 Fugu-Ultra를 완전 재현한다

## 완료·진척의 기준

1차 목표: 현재 8B로 재학습 없이 Fugu-Ultra를 완전 재현 — codex에서 대화하며 지휘→워커→답변이 안정 작동하고 지휘자 컨텍스트가 제대로 관리됨

## 범위 밖 (안 하는 것)

지휘자 재학습/파인튜닝, rope 컨텍스트 확장, 새 지휘자 모델 개발 (모두 1차 목표 밖)

## 관리자

- Smith

(사람 owner만 기록한다. 에이전트는 계속 바뀌므로 헌장에 적지 않는다 —
누가 일했나는 AgentBinding 증거가 투영한다.)

## 어디까지 왔나

PROGRESS.md 참조 — 기계가 빌딩 증거로부터 생성하는 사실 투영이다(생성 전이면
아직 없음). buildings/의 증거가 원본 사실 기록이다.

## 활성 골 (0709)

구현은 **BRICK COO + buildings only** (G0→G4).  
코드 동네 골 문서 (정본 프롬프트 포함):

- `/Users/smith/projects/deku/docs/COO_ACTIVE_GOAL_G0_G4.md`
- `/Users/smith/projects/deku/docs/ARCHITECTURE.md`
- `/Users/smith/projects/deku/docs/DEKU_STATUS.md`

재개 = **G0 Face** 첫 빌딩. wiki/llmwiki는 **G3-K 빌딩**에서 co-dev.

## HARD RULE — 빌딩 종료 = commit + push (Smith)

```text
building frontier complete / D(n) Exit
  → git commit (code: /Users/smith/projects/deku + vessel: this tree)
  → git push both remotes
  → only then D(n+1)
```

생략·나중에 묶기 금지. remote 없으면 만들고 push. push 실패는 즉시 보고.
정본: `/Users/smith/projects/deku/AGENTS.md`, `docs/COO_ACTIVE_GOAL_FUGU_ROUTER.md` §COO 규율 7.

## 처음 온 사람은

1. 이 헌장을 먼저 읽는다.
2. 활성 골 `COO_ACTIVE_GOAL_FUGU_ROUTER.md` (코드 동네 docs/) — paste prompt 포함.
3. 코드 동네 `AGENTS.md` — 이 동네에서 일하는 규칙 (commit/push 룰 포함).
4. project.json — 이 헌장의 기계 선언(그림자).
5. buildings/ — 모든 작업의 증거가 쌓이는 곳. 빌딩 하나가 작업 하나다.
