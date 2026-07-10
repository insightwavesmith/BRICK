# 발주 체인 · 캐스팅 · 어휘 봉인 — 설계 확정안 (0710)

| 항목 | 값 |
|---|---|
| 작성 | 2026-07-10 · Claude COO — Smith·COO 설계 대화(0710 오후)의 확정 기록 |
| 지위 | Smith 최종 승인 시 **WO-3의 스펙**으로 효력. 개발 인계 = `AUDIT-full-consolidated-dev-handoff-0710.md` WO-3이 이 문서를 참조 |
| 착수 조건 | **WO-1(#2 lifecycle)·WO-2(#24 admission) 착지 후** — cli.py/onboard.py가 두 작업의 공통 수술 파일이라 병렬 금지 (§5) |
| 근거 | 0710 전면 감사 + 발사 시퀀스 추적 실측 (좌표는 HEAD `dce5160d0` 기준) |
| 성격 | COO support evidence. source truth·성공·품질·Movement 권위 아님 |

---

## 0. 한 장 요약

```text
철학 한 줄: 결정은 전부 선언·검토 표면에. 기계는 환산·제안·굳히기만.

Smith: task 한 문장 + (게이트에서만) 결재
  ↓
COO: intake → 과중 판단(8답류 확답) 작성
  ↓                                      ┌ 프리셋 지름길 (quick_check/quick_fix만,
  ├──────────────────────────────────────┤  명시 확정 필수, 히든디폴트 없음)
  ↓
발주빌딩: [order-author 5단계 초안(역할까지만)] → [기계 lowering(캐스팅표 해석)]
  ├─ 미결 있음 → 질문 들고 홀드 (fail-closed)
  └─ 완결 → 얼린 발주서 + 근거서 + 캐스팅표 + 확인 체크리스트 (한 패킷)
  ↓
COO: 검수 1회 (수정 = 초안 고침 → 재-lowering → diff) → 명시 forward = 발사
  ↓
본 빌딩: 봉인된 어휘(v1)의 부품·봉인된 캐스팅표의 배역으로만 실행

세 결정의 관계: ③이 부품 목록을 닫고 → ①이 부품별 배역을 닫고
             → ②가 그 닫힌 재료로 조립·검수·발사 순서를 닫는다. 하나라도 열리면 샌다.
```

---

## 1. 결정 ① — 캐스팅 규칙: "환경은 캐스팅을 고르지 못한다"

### 규칙 (불변식)

```text
performer(어댑터/모델/effort)는 캐스팅표(선언)가 고른다.
기계는 표를 '해석'만 한다. 표에 없거나 선언 어댑터가 미준비면
→ 대체 금지, 시끄럽게 정지(어느 행이 비었는지/무엇이 미준비인지 명시).
```

### 죽이는 것 (환경이 고르던 자동 — 전부 실측 좌표)

| # | 대상 | 좌표 (HEAD) | 처분 |
|---|---|---|---|
| 1 | `--real-provider` 첫-준비 프로브 → 전부 미준비 시 adapter:local **조용 폴백** | cli.py:373-402, 순서 :105-110 | fail-closed 거부 or 명시 확인 요구 |
| 2 | 폴백이 프리셋 히든디폴트와 결합해 **루트째 뒤바뀜** (fast-fix→onboarding-example) | cli.py:319-325 결합 | ②의 프리셋 명시 확정으로 함께 소멸 |
| 3 | 레인 선호 어댑터 미준비 시 **첫-준비 어댑터로 performer 조용 교체** | plan_rendering.py:544-558 | 교체 금지 → 정지+보고 |
| 4 | onboard.build의 codex-local **하드코딩** | onboard.py:2290/:2736 | 제거 → 명시 선언 요구 |
| 5 | init 예제의 어댑터 자동선택 | onboard.py:617 | 예제 명시 캐스팅으로 |

### 살리는 것 (선언 해석 — 자동화가 아니라 표의 기계적 조회)

- 레인 캐스팅표: `agent/objects/*.yaml`의 preferred adapter/model/effort (Smith 소유·직접 개정 — 0710 recast가 그 행위)
- 캐스팅 티어/렌즈 사다리의 **선언된 해석** (readiness '대체'만 제거, 해석 자체는 유지)
- verdict 노드 non-local 강제 (plan_rendering.py:562-576) — 유지
- 해석 결과(캐스팅표)는 반드시 **검수 패킷에 노출** (②의 얼린 발주서에 동봉)

### 수용 기준

```text
C1 같은 명령·같은 발주서 = 머신 로그인 상태와 무관하게 같은 performer (재현 프로브)
C2 선언 어댑터 미준비 → 실행 0 + 정지 사유 패킷 (조용한 교체 0)
C3 검수 패킷에 노드별 selected_adapter/model/effort 표 필수 동봉
```

---

## 2. 결정 ② — 발주빌딩 체인 (최종형: 검수 1회 접이식)

### 흐름

```text
입력(내가 태울 때 내는 것): task 본문 + intake 확답
  · intake 확답 = 현행 8답(크기/난이도/쪼개짐/파일충돌/실패비용/인간승인/종료모양/워커인접)을
    발주 요청 필드로 흡수. 8답은 STEP1이 아니라 발주빌딩 진입 전 COO 입력물.

발주빌딩 내부 (2스텝):
  [1] order-author 에이전트 — 계약서(bricks/building-call-authoring/brick.md) 그대로
      STEP1 scope → STEP2 과중(easy~critical) → STEP3 구조그리기
      → STEP4 브릭별 과중 → STEP5 역할 후보
      · STEP3의 그리기 도구 = graph_draft 환산 규칙 (별도 공개 입구에서 내부 도구로 강등)
      · STEP5는 프로바이더 중립(역할+강도만) — 모델 실명 금지 (계약 유지)
      · 확정·lowering·발사·판정 금지 (계약 유지)
  [2] 기계 lowering (결정적 빌더 스텝 — 에이전트 아님)
      확정 초안 + 캐스팅표 → 얼린 발주서 (배역 실명 채움 + EASY-tier 자동충전 전부 가시화)
      ★안전핀 1 (fail-closed): remaining_delta에 미결 결정이 남으면 lowering 불가
        → 질문 목록 들고 홀드 반환 (이때만 왕복 +1)

반환 패킷 (한 번에): 얼린 발주서 + rationale(근거서) + 노드별 캐스팅표
  + 확인 체크리스트 (예: 팬 병렬 폭 N — held_for_coo_review 계약 의무가 여기로 이동)

COO 검수 1회 (기존 stop 게이트 자리):
  · 통과 → 명시 forward = 발사
  · 수정 → ★안전핀 2: 얼린 JSON 직접 수정 금지 — 사람용 초안을 고침
    → 기계 재-lowering → diff 제시(draft-diff가 계량기) → 재검수
```

### 접점 수

| | 이전안 | 확정안 |
|---|---|---|
| COO 접점 | 발주→초안확정→검수/발사 = 3회 고정 | 발주→검수/발사 = **2회** (미결 시만 +1) |

### 프리셋 지름길

- **quick_check / quick_fix만** (building_call.py:203-274의 기존 정책 그대로) + fast_confirm + **명시 프리셋 확정** 필수.
- "task 있고 write 가능하면 fast-fix" 히든디폴트(cli.py:319-325) 제거.
- 프리셋 레인에도 캐스팅표 노출은 유지(C3).

### 함께 닫는 함정 3종 (시퀀스 추적 실측)

1. `gates:["human-review"]` 자동배치가 final_transition 전용인 것 — 중간 게이트는 STEP3에서 명시 배치, 미배치 시 발사 전 경고.
2. stop→forward 재발사의 `--overwrite-existing` 마찰 — 검수 후 forward가 자연 동선이 되게 수리.
3. 타임아웃 비대칭 — 프리셋 레인 기본 120초 vs draft deep 10800초: 과중 판정이 타임아웃을 정하도록 통일.

### 구현 재료 (전부 실존 — 배선이 일)

```text
브릭/레인/프리셋: bricks/building-call-authoring/ (계약+return.yaml) ·
  agent/objects/order-author.yaml · presets/building-call-authoring.md
분류/lowering:   building_call.py:24-35/126-175(lowering) · :203-274(quick 정책)
그리기 환산기:    graph_draft.py (8답→모양 규칙, RED-1~6 기형 거부, rationale 생성)
검수 게이트:     기존 graph-decl stop→forward 이중열쇠 (assembly.py:891-921)
편집 계량:       draft-diff (cli.py:1982-2012, append-only ledger)
미배선(=할 일):  발주빌딩 상시 수직 경로 (큐 #20/#22 OPEN) + lowering 스텝의 빌딩 내 배치
```

### 수용 기준

```text
O1 task+확답 → 발주빌딩 → 얼린 발주서 패킷 → forward → 본 빌딩 완주 E2E 1회 green
O2 미결 유도 사례: lowering 전 홀드 + 질문 목록 반환 (조용한 추측 0)
O3 수정 루프: 초안 수정 → 재-lowering → diff 제시 실측
O4 quick 외 task가 프리셋 지름길로 진입 불가 (fail-closed)
```

---

## 3. 결정 ③ — 어휘 봉인: "만들 수 있다. 단, 발주 도중에 몰래는 아니다"

### 두 평면

```text
운영 평면: 발주빌딩의 구조그리기·에이전트넣기는 OPERATING VOCABULARY vN 안에서만.
          봉인 밖 kind/레인 참조 → fail-closed HOLD ("어휘 개정으로 보내라").
진화 평면: 새 브릭/레인/게이트 = 어휘 개정 행위.
          make-a-brick / make-an-agent / make-a-gate 스킬 그대로 쓰되(scaffold→register→checker),
          + Smith 승인 1회 + 어휘 버전 bump(vN→vN+1)가 추가될 뿐.
          발주 저작 중 인라인 생성 금지.
예시: "UX 디자이너 필요" → 개정 행위 1번(브릭+레인+캐스팅표 행+v2 스탬프) → 이후 모든
     발주서가 v2로 자유 사용. 금지가 아니라 결재.
```

### OPERATING VOCABULARY v1 스냅샷 (2026-07-10 실측 — 승인 시 이 목록이 v1)

```text
에이전트 레인 (9):
  coo · cto-lead · design-lead · dev · inspector · order-author · pm-lead · qa-lead · qa

브릭 kind (12):
  plan · design · deep-design · work · development · review ·
  code-attack-qa · axis-attack-qa · evidence-integrity · inspect ·
  building-call-authoring · closure

체인 프리셋 (30):
  quick-check · fast-fix · one-brick-do · docs-simple-review ·
  app-feature-basic · app-feature-inspected · design-build-parallel · design-contract-only ·
  four-llm-standard-graph · two-fan-in-graph · triage-fanout-3 ·
  governed-change-review · high-risk-change-inspected ·
  recon-fleet-light · recon-fleet · review-fleet · postmortem · postmortem-fleet ·
  repair-loop · research-report · portfolio-sequence · portfolio-reviewed ·
  building-call-authoring · onboarding-example-graph ·
  brick-protocol-engine-feature-hard · brick-protocol-constitution-change ·
  brick-protocol-dashboard-dev-basic · brick-protocol-dashboard-dev-inspected ·
  brick-protocol-portfolio-driver · brick-protocol-post-d-cleanup

이미 봉인돼 있는 어휘 (선례 — 이 설계는 같은 수를 브릭/레인에 확장하는 것):
  Movement 2종 · disposition 4종 · gate 레지스트리(단일소스) · concern 8종 ·
  adoption 2종 (리라우트 v2가 12종 concern 제안을 깎고 살아남은 그 수)
```

### 구현 요구

```text
V1 어휘 버전 문서(이 §3 스냅샷)를 단일소스로 — 발주빌딩 STEP3/5와 lowering이 이 목록 대조
V2 봉인 체커: 발주서가 목록 밖 kind/레인 참조 → RED/HOLD (신규 체커, 신규 파일)
V3 개정 절차: make-a-* 산출 + Smith 승인 기록 + 버전 bump를 한 행위로 묶는 절차 문서
V4 프리셋 30종의 v1 포함 범위는 미결(§6) — 승인 시 확정
```

---

## 4. 이 설계가 기존 구조와 싸우지 않는 근거 (실측)

```text
- 어휘 3계층(gate-policy→disposition→Movement)은 이미 순차·기계강제 계층 (0710 실측)
  — 이 설계는 그 위에 아무 새 어휘도 얹지 않는다.
- order-author 브릭 계약이 이미 "draft-only, 캐스팅 실명 금지"로 봉인돼 있어
  ②의 에이전트/기계 분업과 정확히 일치.
- stop→forward 이중열쇠·rationale·draft-diff·RED-1~6 기형 거부 전부 기존 부품.
- 리라우트 v2의 생존 전략(어휘 봉인·신규 엔진 거부)과 동일 철학 — 선례 검증됨.
```

## 5. 순서·병렬 규칙

```text
지금(WO-1/2 진행 중): 이 문서의 확정 + 어휘 v1 스냅샷 승인까지만. 코드 착수 금지
  — cli.py/onboard.py가 WO-1/2와 공통 수술 파일 (0710 실측: 코덱스가 live 수정 중).
WO-1/2 착지 후: 이 문서 = WO-3 스펙으로 코덱스 발주.
WO-3 착지 후: WO-4 (n2 재증명)에서 이 체인의 O1 E2E가 함께 증명됨.
```

## 6. 미결 (정직 — 승인 전 Smith 결정 필요)

```text
1. 프리셋 30종 중 운영 v1 포함 범위 — 전부? quick류+표준 그래프만? (정리 후보:
   onboarding-example-graph는 예제 전용 표기, 중복 성격 프리셋 통폐합 여부)
2. intake 확답 양식 — 현행 8답 그대로 v1로 갈지, 발주 요청 필드로 개명·확장할지
3. 발주빌딩의 그래프 모양 — 단일 order-author 브릭(기본형)으로 시작할지,
   critical급은 deep-design을 앞에 붙일지
4. lowering 스텝의 기계 표면 — 빌딩 내 결정적 스텝 vs 반환 후 CLI측 굳히기 (구현 설계 시 확정)
5. "8답 후보를 기계가 제안"(task 원문→확답 초안)은 v1 범위 밖 — advisory로 후속 검토
```
