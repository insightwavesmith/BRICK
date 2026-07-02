# BRICK 6-Surface 감사 — Claude 검증·의견 종합 보고 — 2026-06-30

> 이 파일 = 워크플로우 보고서(요약). 상세는 옆 두 파일:
> - `brick-6-surface-audit-claude-review-addenda-0630.md` — 수정(C1~C19) + 추가(ADD-1~20), file:line 표
> - `brick-6-surface-audit-claude-opinion-0630.md` — 방법론·구조 의견 6개
> 감사 원본 7개(s1~s6 + synthesis)는 **편집하지 않음**. 이건 별도 리뷰 문서.

---

## 0. 무엇을 했나

Smith 지시: "워크플로우로 6-surface 감사보고서에 추가/수정할 것 + 내 의견(별도파일) 작성·보고."
효율보다 **브릭 평가 우선**.

Codex가 쓴 6표면 아키텍처 감사를, Claude가 **독립적으로 코드와 1:1 대조**해서
(1) 고칠 것, (2) 빠진 것, (3) 감사 방법 자체에 대한 의견을 산출.

---

## 1. 방법 (감사관을 감사하는 검사단)

```
   7개 감사보고서 (S1~S6 + 종합)
          │
   ┌──────┴──────┐  검증관 7명 (packet당 1)
   │  [검증]      │   인용 줄번호·정량·동작주장·축귀속·내부모순 전부 코드대조
   │             │   + "이 표면에서 안 본 것(추가거리)" 발굴
   └──────┬──────┘
   ┌──────┴──────┐  독립 회의론자 7명 (packet당 1)
   │ [적대 재검증] │   검증관 지적을 기본 '기각'에서 출발해 다시 침
   │             │   → "원래 감사가 맞고 검증관이 틀린 것"을 솎아냄
   └──────┬──────┘   (내가 만든 결과를 내가 검증 안 함 = Smith 규율)
   ┌──────┴──────┐  교차 2명 (병렬)
   │ [표면 사이]   │   6표면 어디도 안 본 빈틈(동시성·예외·resume·기록물 비밀유출)
   │ [방법론 비평] │   + 감사 방법/구조 자체 비평
   └──────┬──────┘
          ▼
   살아남은 지적만 → Claude가 직접 집필 + 헤드라인 4건은 손으로 재확인
```

- 16 에이전트 / 1.5M 토큰 / 612 tool 호출 / ~13분. 전부 **read-only**.
- BRICK HEAD가 감사 커밋과 **동일**(`17eaade`) → 줄번호 1:1 대조 가능, 어긋나면 진짜 오류.
- 적대 재검증이 **2건 기각**. weakened(좁혀짐)는 좁힌 형태로만 반영.
- 검증 태그: `[self]`=내가 이번 세션에 직접 명령 실행 / `[wf]`=워크플로 에이전트 first-hand + 적대 통과.

---

## 2. 감사 품질 판정

**높음. 신뢰할 만한 소견 목록이다.**

- 정량 주장 전부 재현: 프리셋 28 / 프로파일 28 / `.github` 0개 / kernel_checks 9931줄 / case_runners 8503줄.
- 인용 ~95% 정확. 빗나간 것도 "몇 줄 오차"지 지어낸 게 아님.
- "체커 green = 보조증거일 뿐" 규율을 일관되게 지킴.
- 매 packet의 Rejected-Shortcuts가 자기 쉬운결론에 스스로 반박(정직).

단, 결론란(평탄 6/6 ISSUE)과 우선순위 스택은 손봐야 함 → §5 의견.

---

## 3. 수정거리 (고칠 것)

### 진짜 사실오류 — 1건
- **S4-F8** `[self]`: "`~/.brick/builds`가 CLI/status/init 메타에 있다"는 **틀림**.
  repo 전체에서 그 문자열은 딱 1곳 — `kernel_checks.py:8541`, 그것도 **부활 차단** 체커 메시지.
  실제 기본값은 `~/.brick/goal-runs`(`onboard.py:2081/2104/2404`).
  출처가 "subagent 말"이지 직접 read가 아니었음 = 출처약점.

### 인용 좌표 빗나감 — 8건 (내용 맞음, 위치만)
`spec.py:566`(실제 `brick()`=569) · `coo.md:39-40→40-41` · `reroute:158→161` ·
`index.mjs:14-17→14-16` · run_chat_session 경로 'lib' 오분류 · 종합 C7 "S5-F1~F11"(실제 F1~F13) ·
route_policies `*.yaml`(파일 1개뿐) · `make_agent_fact` 키워드전용(위치인자 호출불가).

### 톤 보정 — 과대/과소/축귀속
- **S4-F2 과대** `[wf]`: 프론티어 큐가 "헌법위반/충돌"이라 했지만, walker 자기 문구는
  "scheduler/queue를 **증명 안 함**"이라는 proof-limit일 뿐. 금지 문구는 리포터/projection 버스에 있음.
  → "walker가 진짜 내부큐+스레드풀을 가지며, no-queue 규칙이 안 덮고, 본인은 증명만 유보"로 재서술.
- **S3-F1 'high' 톤다운** `[wf]`: 헌법(`AGENTS.md:450-452`)이 default-transition 자동진행을 **이미 허용**("autonomy dial"). seam은 실재하나 동작은 합헌 → 톤다운 또는 헌법 화해문 추가.
- **S3-F5 'medium' 과대** `[wf]`: 두 stale 문자열 다 런타임은 `reroute` 정상 수용 → 순수 표시문 버그, 행동위험 0.
- **과소(강화)**: S4-F1(승인 기본 action/identity가 누수, 게다가 post-HOLD 경로는 샌드박스 밖) ·
  S4-F11(완화책 인정하고 잔여=프로바이더 키 2개만 global os.environ) ·
  S6-F11(ingest가 비상수시간 `!==` + 미설정시 `'dev-secret'` 기본수용) ·
  S4/S6-F9(release 스크립트 자체 denylist도 project/만 제외) · S1-F6(GOAL 10중 8이 non-catalog).

---

## 4. 추가거리 (빠진 것)

### 출시 타이밍과 무관하게 지금 손볼 3건 (전부 [self] 직접 재확인)
1. **ADD-2 원시 전사 비밀/PII 비스크럽** — 에이전트 응답 원문(`raw/agent-received.jsonl` 등)이
   비밀 스크럽 0회로 저장됨. 가드 `contains_raw_secret_text`는 단 3곳, 원시 writer(`raw_claim_trace.py`)는
   맨 `path.write_text`. denylist도 ~8패턴(AWS·bearer·DB·PII 누락). 감사는 `.env`/`.key` '파일'만 봤고,
   엔진이 장부에 **써넣는** 비밀은 안 봄. 표면 사이 영역(Support씀/Product보냄/Checker가드없음).
2. **ADD-1 resume/HOLD승인이 워크트리 샌드박스 밖** — `run_approve_entry`가
   `resume_building_plan`을 격리래퍼 없이 직접 호출(`onboard.py:2545`), 원래 워크트리는 이미 폐기됨.
   감사가 "격리된다"고 적은 통제가 정작 이 경로를 안 덮음 = 격리회귀 seam.
3. **ADD-3 죽은 pytest 설정** — `pyproject`가 pytest를 선언하지만 테스트 0개,
   체커 내부 `def test_` 2개 중 하나는 `repo` fixture 없어 bare pytest 돌리면 **에러**.
   즉 BRICK 자가검증 = 정적 체커뿐 → §5 동적맹점의 직접 증거.

### 스코프 빈틈 (M-tier, 표는 addenda 파일)
`brick/work.py` 반환shape 파서 미검사 · `walker_carry.py`(669줄, carry는 Link 1순위) 미검사 ·
fan-in 분류 에러경로 미검사(권한누수면) · verdict-key 검증기 재귀/최상위 비대칭(S2-F1 고침의 함정) ·
poisoned submission이 빌딩 wedge · 체커 fixture 고정ID로 SIGKILL시 영구RED · make-an-agent 스킬 stale taxonomy(최고레버리지) · CLI 에러가 raw 예외문 노출 · `setup.md`에 "24 profiles" 박힘(실제28, 첫사용 모순) · 포트폴리오 adoption 권한경계 미탐 · 두 registry 미검사. (총 ADD-1~20)

---

## 5. 내 의견 (방법론·구조) — 별도파일 핵심 6

1. **평탄 6/6 ISSUE가 그라데이션을 버림** (27 high / 19 med / 11 med-high / 2 low-med / **1 positive**).
   S6은 긍정 소견까지 있는데 Link축과 같은 도장. → 표면별 readiness 튜플 도입.
2. **두 목표를 한 도장에 섞음**: 축청결(Goal A)과 출시안전(Goal B). 증상 — S2-F2(순수 문서드리프트)와
   S4-F9(비밀 유출경로)가 **둘 다 'high'**. → 2축 점수(축무결성 / 출시안전).
3. **P0가 배포보안(출시 후)과 프로토콜정합성(지금 라이브)을 동급으로**. 게다가 감사가 "출시 임박은
   증명 안 됨"이라면서 보안하드닝을 1순위 둔 **순환**. → "출시 임박?" 결정으로 게이트, 두 순서 제시.
4. **축 렌즈가 배포발견에 과적용** — 보안발견의 축귀속이 그냥 "support"인 형식. → infra 하드닝 별도 범주.
5. **proof-limit가 대체로 엄격하나, 가끔 read로 이미 끝난 결론까지 hedge**. → Proof status를
   '구조적 주장'과 '실증/라이브 주장'으로 분리.
6. **방법이 동적/동시성/resume 실패계열에 구조적 맹점**(정적read + 체커green + 단일운영자).
   균형: 내가 그 맹점(fan-in 스레드풀)을 실제 파보니 **설계상 안전 + 체커검증돼 있었음**.
   → "엔진이 racy"가 아니라 "감사 방법이 그걸 보증 못 함"이 결론. 핵심소견 전 e2e 라이브빌드 1회 + 축렌즈 안 든 2차 리뷰어.

---

## 6. 산출물 인덱스

| 파일 | 내용 | 언어 |
|------|------|------|
| `brick-6-surface-audit-claude-report-0630.md` (이 파일) | 종합 보고 | KO |
| `brick-6-surface-audit-claude-review-addenda-0630.md` | 수정 C1~C19 + 추가 ADD-1~20 (file:line 표) | EN |
| `brick-6-surface-audit-claude-opinion-0630.md` | 방법론·구조 의견 6 | EN |

(상세 두 파일이 영어인 건 감사 원본 7개가 영어라 Codex가 그대로 패치 가능하게 하려는 것.
이 보고는 Smith용 한국어.)

---

## 7. 한계 / 안 한 것 (정직히)

- 감사 7개 원본 **편집 안 함** — 패치 적용은 Smith/Codex 판단. 이건 리뷰노트.
- 워크플로 **read-only** — 실빌드·라이브 프로바이더·`check_profile --all` 안 돌림.
  ADD-2/3은 정적으로 확정이지만 "실제 유출/실제 충돌"은 라이브로 안 침.
- 적대 재검증 **2건 기각**(채팅세션 severity 통째 강등 / ADD-10과 중복된 에러경로 발견)은 의도적 제외.
- 헤드라인 4건만 [self], 나머지는 [wf](워크플로 first-hand + 적대 통과). 두 상세파일에 항목마다 태그.

## 8. 다음 제안
P0 재정렬(출시 임박? 결정) + 2축 점수로 결론란 재발행. 출시 무관 즉시 3건(ADD-1/2/3)은 별도 수리 빌딩 후보.
