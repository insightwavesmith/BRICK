# 그래프 사이징 독트린 재배치 기획 (0705) — COO가 워크플로처럼 그리게

출처: Smith 지시(0705 오후) — "COO가 업무 가중치에 따라 그래프를 워크플로처럼 유연하게
그려야 하는데, 스킬·설명문서가 골에 업데이트돼 있나? 아니면 과거 실수+워크플로 레퍼런스로
구조를 기획하라." 조사자 재검토 수행 → **구조는 반쪽 존재** → 본 기획. **작업x — 발주-준비
문서일 뿐, 시공·발주는 형제 COO.** source truth 아님.

## 0. 재검토 결론 (한 줄)

**사이징 독트린 자체는 building-sizing-method 스킬에 충실히 있다**(5차원 결정표 · 4축
난이도→다이얼 카드 · 과소-폭 금지 0703 각인 · fan-in 소화력 상한). 문제는 골 문서가 이미
진단해 둔 **배치**다 — goal-phases-consolidated-0702.md:65-66: "워크플로 독트린은 호출부
상주, 브릭 폭 독트린은 스킬에 잠듦". 워크플로 도구는 폭/패턴 독트린이 도구 설명(호출부)에
붙어 **매 호출마다 강제로 보이는데**, BRICK은 스킬을 열어야 보인다(풀 방식) — 실수는 스킬을
안 연 호출 순간에 난다. 이 진단이 0703에 적혔는데 배치 수리는 미집행이다.

## 1. 갭 6건 (전부 0705 실측)

| id | 갭 | 실측 근거 |
|---|---|---|
| G1 | **독트린 배치 미수리** — COO 상주 표면(agent/prompts/coo.md 헌장)에 사이징/폭 조항 0건 | coo.md grep: 워크플로·사이징·폭·가중치 0히트(fan() 명명 규칙 1건뿐). goal-phases:65-66 자기 진단 미집행 |
| G2 | **신규 엔진 능력 미반영** — 출생 확장예산(c89f1732 랜딩)·approve-from-hold 공식화(df9feb6c)가 사이징 다이얼에 없음 | 스킬 2종에서 expansion_budget grep 0건. 감독 다이얼은 아직 gates=("human-review") 서술뿐. fan-in wait-all은 랜딩 여부 자체 미확인(assembly/plan_graph grep 0 — 발주 전 확인) |
| G3 | **워크플로 품질 패턴 대응표 부재** — loop-until-dry·completeness critic·no-silent-caps·judge panel의 BRICK 번역이 어디에도 없음 | 스킬 §결정표는 parallel/렌즈/교차LLM까지만 커버 |
| G4 | **종료선 원칙 미각인** — "Deliverables에 명시적 종료선 없으면 수리 루프가 안 끝난다"(0703 reason-refs 6라운드 실측)가 스킬·헌장 어디에도 없음 | 종료선 grep: task-author·sizing·coo.md 전부 0건. 발사-전 실수 체크(인라인 계약·test -f·레인-가능 D…)는 task-author 곳곳에 분산돼 통합 체크리스트 없음 |
| G5 | **스킬 양 사본 드리프트** — agent/skills vs brick/templates/skills | sizing: 템플릿 쪽에만 "P3 운영자 기본은 build()만" 신규 문단(방향 역전 — 템플릿이 더 새것). task-author: 5행 차이 |
| G6 | 소수치 드리프트 — 스킬 내 "28개 프리셋"(실물 29) 등 | 묶음8/W4 계열 — **중복 발주 금지**(수치 재생성은 그쪽 몫) |

## 2. 처방 4건 (기획 — 시공은 형제)

### R1 — 헌장 상주 핀 【G1 수리, 가장 중요】
coo.md에 **사이징 핀 1개(≤6줄)** 신설 — T5 pin-diet(0705, 327줄) 직후이므로 핀 추가는
최소·단일로. 문안 초안:

```
사이징 핀(발주 전 강제 질문): ①분할 가능한가 ②파티션이 파일-비충돌인가 — 둘 다 yes면
기본형 fan(work×N)→수렴→fan(렌즈)→closure. fan은 범용 병렬이지 렌즈 전용이 아니다.
다이얼 4축(분량→팬폭 / 판단분산→교차LLM / 오답파급→게이트 / 결합도→세로vs팬)과
미지수형 확장예산은 building-sizing-method 스킬. Deliverables에 종료선 없으면 발주 금지.
크기는 토큰이 아니라 "업무를 종료시킬 수 있는가"로 잰다.
```

### R2 — building-sizing-method v2 증보 【G2·G3】
1. 결정표에 다이얼 추가: **⑦ 미지수형 확장 여지 ⇒ 출생 `expansion_node_budgets` 선언**
   (일의 끝 모양이 불확실하면 노드 예산을 출생 시 선언 — 걷다가 HOLD+승인으로 T10 확장.
   워크플로 budget-scaling의 BRICK 번역).
2. 감독 다이얼 갱신: 사람 게이트 = HOLD 후 **공식 CLI approve-from-hold**(gap2 v2)로 전진
   — "게이트 걸면 죽는 게 아니라 승인으로 잇는다"를 명시(과소-게이트 방지).
3. §3 대응표(아래) 편입 + "28개 프리셋"→측정 지시로 교체 + 게이트 어휘 현행화
   (link-gate:human/coo/expansion-approval).

### R3 — brick-task-author 발사-전 프리플라이트 § 신설 【G4】
분산된 실수 각인을 **체크리스트 한 절**로 통합(각 항 실측 앵커 유지):
①Deliverables에 명시적 종료선(0703 6라운드) ②증명은 렌즈별 환경-실행가능한 것만
③레인-가능 D만 — 라이브 상태·커밋-의존 증명은 "COO 게이트 항목"으로 분리(0703 #14 ·
0704 goodenough) ④규범 계약 work_statement 인라인 ⑤source_facts 발사 전 `test -f`
⑥"file:line만 반환" 금지 — reason_refs엔 스텝 주소/불투명 토큰 ⑦런처는 전문 작성+핵심
마커 assert(0704 슬라이스5 사고) ⑧처분/재개 adapter_cwd는 세션ID 없는 중립 경로
⑨워크트리 조작 전 커밋 ⑩홀드 처분 전 4갈래+처분 클래스(§3.0 기존 유지) ⑪범위를
절단(top-N·샘플링)했으면 not_proven에 기재(no-silent-caps).

### R4 — 각인 유지 장치 【G5·G6】
양 사본(agent/skills ↔ brick/templates/skills) 동기 — 이번 증보를 양쪽 동시 랜딩 + diff 0
종료선. 수치/앵커의 상시 검증은 묶음8(수동 정정)·A+ W4(generated docs)와 합류 — 여기서
재발주하지 않는다.

## 3. 워크플로 패턴 → BRICK 그래프 번역표 (R2 편입 재료)

| 워크플로 패턴 | BRICK 번역 | 비고 |
|---|---|---|
| parallel() | `fan([...])` → 수렴 노드 | 동일물(기존 결정표 2행) |
| pipeline(무장벽 흐름) | **없음 — 의도된 비목표**(무정지 동적 팬 금지, 헌법 Rule 3 계열) | 대체: 척추 직렬 + 미지수는 T10 확장 |
| adversarial verify(반박자 N) | `fan(code-attack-qa·axis-attack-qa·evidence-integrity)` → closure 종합 | 렌즈 fan(기존) |
| perspective-diverse judge | 교차 LLM 렌즈(codex+claude+gemini) | 기존 0702 기본 |
| judge panel(N안 생성→심사) | `fan(design×N 관점)` → review 채점 → closure 채택 | 프리셋 후보(신규 모양) |
| loop-until-dry | **엔진 루프 아님** — COO가 라운드 발주, 계약 종료선에 "연속 2라운드 신규 발견 0 = 종료" 명시 | R3-①과 결합 |
| completeness critic | closure 직전 review 노드에 "빠진 것 전수(모달리티·미검증 주장)" 계약 | 대형 조사 기본 동승 권장 |
| no-silent-caps | 계약이 범위 절단을 `not_proven`/proof_limits 기재로 강제 | R3-⑪ |
| budget scaling | 출생 `expansion_node_budgets` 선언 → HOLD+승인 확장(T10) | R2-1 |
| resume/캐시 프리픽스 | 빌딩 resume + T10 revision | 기존 |

## 4. 발주 모양 제안 (형제용 참고 — 사이징 스킬 자기적용)

소형 1빌딩, **1차 웨이브 코드 시공과 파일 비충돌(스킬·헌장 md만)이라 즉시 병행 발주 가능**:
```
work(R1+R2+R3+R4 증보, write=True,
     write_scope: agent/skills/building-sizing-method/** · agent/skills/brick-task-author/**
                  · brick/templates/skills/(양 사본 동일 2종) · agent/prompts/coo.md)
→ fan( review(증보 문안 vs 이 기획서 §2·§3 대조), inspect(축·핀 다이어트 규율 점검) )
→ closure
```
- coo.md는 헌장 표면이므로 `gates=("human-review",)` 권장 — 핀 문안은 Smith 눈으로 확인 후 merge.
- 종료선: 핀 실존(grep) · 종료선 원칙 실존(grep "종료선") · 양 사본 diff 0 · 신규 다이얼
  문안 실존 · 격리 --all green. 발주 전 확인 1건: fan-in wait-all 랜딩 여부(d5-faninwaitall
  빌딩 산출 vs assembly 실물).

증거 한계: 발주-준비 문서. 실측 앵커는 0705 오후 기준(HEAD 64d50be6) — 발주 시점 재확인.
처분 확정·품질 판정은 사람 몫.
