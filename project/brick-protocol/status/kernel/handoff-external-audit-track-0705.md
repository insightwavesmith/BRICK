# 핸드오프 — 외부(GPT) 아키텍처 감사 트랙 (0705, 세션 이관)

다음 세션(조사자)이 감사~교정 루프를 무손실로 이어받기 위한 인계 정본. 역할 경계는
brick-coo-operating-rules.md 그대로: 조사자는 감사 수신·교차검증·발주-준비까지, 시공은
형제 COO 세션 몫. 이 문서 + external-audit-repair-orders-0705.md 두 개면 트랙 전체 복원.

## 0. 한 줄 상태

**전 배치(S1~S17) 발사·교차검증·정본 증보 완료(0705 낮)** — 4차분(S15~S17)은 orders 문서
"0705 낮 증보" + constitution-amendment-draft-0705.md 신설 + harness-roadmap-orders-0704.md
실효 스탬프로 반영. 발주 차단 결정 0건(헌법 비준은 각인 단계에서 Smith 대기). T10 첫 확장
운전은 형제의 bundle5+bundle1잔여 랜딩 대기 중. 남은 것 = 형제 시공 + §5 예약 후속.
0705 오후: 지피티 종합보고 수신 — **실행 순서 정본 = external-audit-repair-phases-0705.md**
(페이즈 1~5, 신설 묶음9 free-green·묶음10 wheel·묶음11 gate-consumer 포함). 트랙 복원은
이제 이 문서 + orders + phases 세 개(+2차 웨이브는 aplus-wave-plan-0705.md).
0705 오후 Smith 결정 3건 처리: 헌법 Rules 11~13 비준·개정 반영(+역사 문단 삭제) /
묶음9 verify 계층화 승인 / A+ 2차 웨이브 채택(착수 게이트 = Phase 1·묶음2 랜딩 + T10 운전).

## 1. 운영 루프 (불변 — 이 규율로 계속)

```
지피티 감사 산출 → 조사자 로컬 실물 교차검증(그대로 믿지 않음) → 정본 증보 →
형제 COO 통보(피어) → 형제 시공 → 조사자 게이트 보고
```
- 지피티는 클론 불가 환경 — 커넥터/업로드 아카이브로 읽는다. 앵커가 밀릴 수 있어
  **교차검증이 필수**(오늘까지 소음 0). 발견 ID는 BRICK-AUD-*/S##-* 연번 유지(회귀 추적).
- 마스터 프롬프트(정신 모델 + 소음 금지 목록 + 출력 계약)는 매 배치 앞에 고정으로 붙인다
  — 아래 §3.

## 2. 완료 배치와 처분 (정본: external-audit-repair-orders-0705.md, HEAD b1d328f2)

| 배치 | 스코프 | 핵심 발견 | 상태 |
|---|---|---|---|
| 1·2차 | S1~S10 전체 | MAJOR 5(S1 support홀드저작·S4 write_scope반쪽집행·S6 경로유출·S9 bool·S5 체커갭) | 발주 완료 |
| 3차 | S13 홀드생애주기·S14 T10운전 | adapter-error 막다른골목 규명(내 no-op 백로그 종결)·홀드신원 이중소비·운전 runbook | 발주 완료 |
| 4차 | S11 체커커버리지·S12 writer-reader | **구조 결함 2: WR-001 위조개정판 reader통과 · WR-006 게이트replay 어휘무검증** + bool 위생 다수 | 발주 완료 |

**형제 랜딩 완료**: bundle1(bool seal 125bfcff)·bundle3(handoff 91e4005f)·T10 gap1(예산
kwarg c89f1732). **걷는 중**: bundle2(S4+S1 재배선). **발주 대기**: bundle5(구조·최우선)·
bundle1잔여(base expansion_budget bool)·bundle4(A안 확정)·bundle6·7.

**Smith 확정 사항(재론 금지)**: S1=재배선(저자/권한만, guard 제거 아님) / S4=실제 집행결함
(구조부채 아님) / bundle4=A안(adapter-error는 승인홀드 아님, stop-only+공개에러, 엔진 무수정).

**T10 운전 선결**: bundle5(WR-001 reader 재검증 + WR-006 게이트 어휘) + bundle1잔여. 이 둘
랜딩되면 조사자가 첫 확장 운전(리허설 조각 = cleanup-wave-a design 산출물, 6단계 runbook =
S14). 위조 개정판이 운전 중 latest로 읽히면 상류 편입 금지가 무력화되므로 반드시 선행.

## 3. 마스터 프롬프트 (S15~S17 앞에 고정으로 붙일 것)

```
너는 BRICK 프로토콜 저장소의 외부 아키텍처 감사관이다. 목표는 칭찬이 아니라 결함 적발이다.

정신 모델: 3축이 헌법 — Brick=WHAT(계약) / Agent=WHO·HOW(수행) / Link=MOVEMENT(이동·게이트)
/ support=사실 기록만(판단 금지). 충분성+Movement=Link, 품질+성공=사람. 공식 실행 경로는
하나: brick build → materializer → declared plan → run.py walker → evidence root → reporter.
발주 언어는 assemble()/build()/fan() DSL뿐.

의도된 제약(이걸 결함이라 보고하면 0점): ①스케줄러·큐·재시도·2차엔진 금지(헌법 Rule3)
②support 무판단은 설계 ③로컬 설치 도구 — 이식성 부족은 결함 아님 ④install.sh의 curl|sh
한계는 자인됨 ⑤처분 어휘 4종 고정, walker 핵심루프·정지알고리즘 불가침 ⑥레인 git commit
불가는 정상 ⑦무정지 동적 팬 없음은 의도(확장은 홀드+승인 경유 T10).

감사 규율: 모든 발견에 file:line+실물 인용. 발견마다 스스로 반증 시도하고 결과 기록
(생존=CONFIRMED, 정황뿐=PLAUSIBLE). 수리는 최소 크기 1줄(대형 리팩토링·"테스트 늘려라"
금지). 스타일·명명 취향·칭찬 금지. 모르면 UNKNOWN. 발견 ID는 S##-* 연번.

출력 계약(발견마다): id | 축 | 심각도(FATAL/MAJOR/MINOR) | 주장 한 문장 | 증거(file:line)
| 반증 결과(CONFIRMED/PLAUSIBLE) | 최소 수리 1줄. 마지막에 심각도 집계 + "이 감사가
못 본 곳" 자백.
```

## 4. 감사 3개 — 0705 낮 발사·교차검증·정본 증보 완료 (프롬프트는 회귀 재감사용 보존)

집행 기록: 지피티가 S15·S16·S17을 한 번에 산출(아카이브에 project/** 부재 → S15 잔여
status/kernel 대조는 조사자 로컬 스윕으로 수행). 판정·처분 정본 = orders "0705 낮 증보".

```
S15 문서-실물 드리프트 전수: BRICK-CONSTITUTION.md, README.md, AGENTS.md,
    project/brick-protocol/status/kernel/의 정본 문서(goal-phases, 발주-준비, 스킬이
    인용하는 것)에 담긴 명령어·기대출력·file:line 앵커·함수명을 현재 코드 실물과 전수
    대조하라. 선례: README expected "5) 설치 점검 완료" vs 실출력 불일치(CONFIRMED).
    산출: 문서별 드리프트 표(문서 인용 vs 실물 vs 심각도). 이건 헌법·문서 개정 웨이브의
    입력이 된다. archive/ 밑 이동 문서는 역사 기록이니 제외.

S16 무개발 고객 여정 시뮬레이션: onboarding-zero-dev-plan-draft-0704.md(v2)를 정본으로,
    "터미널을 열어본 적 없는 고객"이 첫 성공(무료 초록불)까지 가는 여정을 문서·스크립트
    실물만으로 단계 재구성하라. v2의 14관문 인벤토리에 아직 빠진 숨은 전제를 사냥하고
    (선례: npm·brew·Xcode CLT·초대 수락이 초안에서 누락됐다), L2(에이전트 동반 설치)의
    에이전트 대본이 갖춰야 할 단계·질문·금지행위 목록 초안을 제안하라. 산출: 관문
    인벤토리 증보 + L2 대본 초안 + P0 실측(3~5명) 관찰 항목 체크리스트.

S17 헌법 개정 초안: BRICK-CONSTITUTION.md 현행본과 0704~0705 확정 사항 — T10(홀드-후
    편입, 확장예산 fail-closed, revision 원본보존), support 홀드저작의 Link 재배선 결정,
    체커-동반 개발 원칙 — 을 대조해, 헌법에 승격할 불변 조항 후보와 개정 문안을 제안하라.
    헌법 원칙 준수: "변화하지 않는 규칙만", 상태·절차 제외. 산출: 조항별 현행 vs 개정안
    vs 승격 근거(어느 실측이 근거인지). 제안일 뿐 비준은 Smith 몫임을 명시.
```

## 5. 예약된 후속 감사 (트리거 시 프롬프트 작성)

- bundle2 형제 초안 나오면 → 지피티 독립 리뷰(7항 수용기준 심사관)
- 조사자 T10 운전 직전 → 확장 조각 실물 공격(조각 JSON은 미커밋 증거라 조사자가 추출·전달)
- 묶음들 랜딩 후 → 동일 S1~S10 프롬프트 회귀 재감사(B- 점수 델타 측정 — 외부 감사를
  1회 행사가 아니라 반복 게이트로 제도화)
- **회귀 재감사 아카이브에는 project/brick-protocol/status/kernel 포함**(4차분 공백 재발
  방지): 기존 tar 명령에 `project/brick-protocol/status/kernel` 경로 한 줄 추가
  (buildings/·public/은 계속 제외)

## 6. 미결·주의

- S13-HOLD-003(coo 게이트 forward 통과) = 외부 실측 vs 조사자 wave-A 실측 상충 →
  "대화형 승인 갭" 발주에 픽스처 재검 D항목으로 편입됨. 확정 전 어느 쪽도 단정 금지.
- 모델 폴백 주의(0704·0705 각 1회): fable5 도구호출 실패 시 opus 자동 폴백. 도구 인자는
  평문 위주, 이모지·미이스케이프 백슬래시 회피.

증거 한계: 인계·발주-준비 문서. source truth·성공 판정·Movement 권한 아님.
