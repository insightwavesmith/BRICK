# 프리셋 재편 기획 v2 (0705) — 메뉴판에서 부품함으로

출처: Smith 질문(0705 오후) → 조사자 기획 v1 → **지피티 검수 "GO — but amend before
construction"(위험 8) → 조사자 교차검증(수용 5 · 조정 2 · 기각 1) 반영한 v2.**
작업x — 발주-준비 문서, 시공은 형제 COO. graph-sizing-doctrine-refresh-0705.md의 R5.
source truth 아님.

## 0. 원칙

**프리셋은 사고(思考)의 어휘가 되게 하고, 메뉴가 되지 않게 한다.**
**블록도 메뉴가 아니다 — 블록은 질문의 답이 나온 뒤 호출하는 어휘다. 발주는
블록명/프리셋명으로 시작하지 않는다.** (지피티 위험1 반영)

실측 근거: selection_hint 29/29 완비·anti-hint 0건·전부 완성-그래프 단위·진입 순서
미규정(0705 측정) — 이대로 "잘 쓰게"만 만들면 메뉴 고착으로 기운다. 0703 단일-레인
고착 사고는 프리셋 없이도 났다 — 위험의 본체는 진입 방식이다(헌법 Rule 4 계승).

## 1. 3층 구조

### 1층 — 부품(블록) 카탈로그 신설

재사용 단위를 완성 그래프에서 **스테이지 블록**으로 한 층 내린다. 위치: `brick/templates/blocks/*.md`.
**블록 = 문서 + DSL 스니펫이다. 실행 표면이 아니다** — support/operator·materializer·CLI는
blocks/를 읽지 않는다(부재 검사로 증명). 엔진·CLI 변경 없음(Rule 3·9·10 보존).

**블록 문서 규격(지피티 위험2 반영)** — 자유 산문 금지, 고정 front matter 의무:

```
schema: brick-block/v1
block_id: B1..B8          # 필수
title / summary            # 필수
when: [...]                # 필수, 비어있으면 반입 불가
anti_hint: [...]           # 필수, 비어있으면 반입 불가
dsl_snippet: 본문에 실존    # 필수 (assemble/build/fan 조각)
axis_notes: brick/agent/link/support 각 1줄
related_presets: [...]
proof_limits: "block is documentation only, not executable, not a recommendation engine" 포함 필수
```

| 블록 | DSL 뼈대 | 언제 | 언제 아님(anti) |
|---|---|---|---|
| B1 존-파티션 fan | `fan([read-only 존리더×K]) → 수렴` | 대형 읽기(레인당 ~1k줄), 존 경계를 계약에 박음 | 같은 파일에 쓰는 가지들(직렬로) · 존 경계 불명확 |
| B2 검증 렌즈 fan | `fan(code-attack-qa · axis-attack-qa · evidence-integrity) → closure` | 저신뢰/계약·정책·보안 접촉 | 고신뢰 read-only(렌즈 0~1) |
| B3 심사 패널 | `fan(design×N 관점) → review(비교표·반증·tradeoff 기록 = evidence) → 채택은 human/COO 또는 선언된 Brick 계약` | 설계 선택지가 넓고 반증 불가한 판단 | 반증 가능한 사실 추출(1두뇌+반증 1렌즈). **review 점수/비교표는 evidence일 뿐 품질·성공 판단이 아니다**(지피티 위험4) |
| B4 완결성 비평 꼬리 | closure 직전 `review("빠진 것 전수 — 모달리티·미검증 주장 + 주장→증거 대응표, 증거 없는 주장 적발")` | 대형 조사/전수 감사/증거-먼저 조사 | 소형 단건 |
| B5 고신뢰 소형 직렬 (구 "무인 척추" — 개명, 지피티 위험5) | `design→work→closure, gates=()` | 고신뢰 소형, read-only 또는 단일 영역 소형 write | **계약·헌장·고객표면·보안을 건드리는 write · 다중 파일/영역 · 실패 비용 큼 · 크기 미상 · 결과를 사람이 설명해야 함.** write가 있으면 렌즈 1 동승 권장 |
| B6 사람게이트 마감 | `gates=("human-review",)` — **DSL 개념 토큰(assembly.py:1287은 human-review/coo-review만 수용) → materialize 시 canonical `link-gate:human`/`link-gate:coo`**(gate.yaml). HOLD 후 공식 approve-from-hold(gap2 v2)로 재개 | 헌장·계약·고객 표면 변경 | 무인으로 닫아도 되는 read-only |
| B7 미지수 확장 【**status: gated**】 | 출생 `expansion_node_budgets` 선언 → HOLD+승인 T10 확장 | 끝 모양이 불확실한 일. **live 사용은 묶음1잔여+묶음5(T10 hardening) green 후 — 그 전엔 설계 패턴 문서로만**(지피티 위험6) | 모양이 확정된 일(예산 선언은 소음) |
| B8 마를-때까지 라운드 | 계약 종료선 "연속 2라운드 신규 발견 0 = 종료". **엔진 루프 금지, 각 라운드는 COO가 새 발주로 저작, 이전 라운드 evidence가 다음 라운드 source_facts**(지피티 위험7) | 미지수 크기 탐색(버그 사냥·전수 스윕) | 산출물이 정해진 제작 작업 |

완성 프리셋 29개는 폐기하지 않는다 — **블록 조립 예시로 강등**(예: recon-fleet = B1+B2+B4).

### 2층 — 질문-우선 진입 규율 (지피티 위험1로 강화)

**발주는 블록명/프리셋명으로 시작하지 않는다.** 항상 아래 답을 먼저 쓴다:
①분할 가능한가 ②읽기/쓰기/검증/설계 중 무엇인가 ③파일·영역 충돌 있는가 ④실패 비용
큰가 ⑤사람 승인 없이 닫아도 되나 ⑥끝 모양 확정인가(아니면 B7 클래스) ⑦미지수
탐색인가 제작인가(탐색이면 B8 클래스) ⑧**종료선은 무엇인가** — 그 뒤에 블록/프리셋 대조.

배치: 전체 질문표는 building-sizing-method(R2)·brick-task-author 프리플라이트(R3)에 각인.
헌장 핀(R1)은 6줄 제한 유지 — "프리셋/블록은 다이얼 답이 나온 뒤 고른다. 메뉴에서 시작
금지" 1줄만 병합.

### 3층 — 프리셋 위생 (29개 전수)

1. **anti_hint 의무화 + 품질 조건**(지피티 반영): generic 상용구 금지 — 각 anti_hint는
   **구체적 오선택 조건 1개 이상**(파티션 가능/쓰기 충돌/보안 접촉/사람게이트 필요/크기
   미상 등)을 포함, 최소 40자.
2. **blocks 표기는 YAML 리스트**(기존 steps 관례와 동형): `blocks:` + `- B1` … 허용값 B1~B8만.
3. **기존 포맷에 additive만**(조사자 조정 — 지피티의 schema 전면 교체는 기각): 프리셋은
   이미 엔진·체커가 파싱하는 구조화 포맷(preset_ref/steps/selection_hint — plan_rendering·
   building_design_toolkit·agent_packets_check 실측). anti_hint·blocks **2필드 추가만** 하고,
   **로더·프리셋 체커가 신규 키를 거부하지 않는지 같은 슬라이스에서 스모크** — 거부하면
   키 admission을 함께 선언.
4. **도그푸드 신호(축 순화 — 지피티 반영)**: support는 `build_input_mode`(preset_task vs
   graph) 비율을 **기록만** 한다. "~100%=사고 정지 / ~0%=부패" 판독은 사람/COO 운영 판단.
   측정은 수동 명령(스케줄러 금지, Rule 3).

## 2. 하지 않는 것 (경계)

- 블록 실행기·블록 CLI·프리셋 추천 엔진 신설 금지 — 블록은 코퍼스다.
- 프리셋 29개 통폐합은 이번 범위 아님 — anti_hint를 달면 중복이 드러난다. 그 측정 후 별도 판단.
- 블록 고착에도 Rule 4(축 보존 최소 그래프)가 상위법. 정식 RED manifest는 A+ W2에 합류
  하되, **이번 웨이브 종료선에 최소 shape 스모크는 포함한다**(지피티 위험8 — "나중에"로
  밀면 체커 없이 문서만 들어간다).

## 3. 발주 모양 (형제용 — 문서만, 1차 웨이브 코드와 비충돌)

```
S1: work(블록 8건 신설 + 프리셋 29건 anti_hint·blocks 추가(additive),
        write_scope: brick/templates/blocks/** · brick/templates/presets/**)
    → fan( review(본 기획 §1 표·규격과 전수 대조),
           inspect(§2 경계 — 실행 표면 신설 0·additive 확인) )
    → closure
S2: 진입 규율 1줄·질문 8종 각인은 graph-sizing R1·R2·R3 발주에 합류(중복 발주 금지).
```

**종료선(지피티 10항 흡수 + 조사자 조정)**:
1. `ls brick/templates/blocks/*.md | wc -l` = 8 · 각 md에 brick-block/v1 front matter 필수
   필드 전부(스모크 스크립트로 8/8)
2. 블록 anti_hint 8/8 · DSL 스니펫 8/8 · proof_limits "not executable" 8/8
3. 프리셋 anti_hint 29/29 **non-generic**(구체 오선택 조건 포함) · blocks 리스트 29/29 ·
   참조 블록 ID 전부 실존(B1~B8 밖 금지)
4. **부재 검사**: support/·link/·agent/ 코드에 `templates/blocks` 참조 0 · 신규 CLI 서브커맨드 0 ·
   materializer 변경 0
5. 프리셋 로더·체커가 신규 2키를 수용(스모크; 거부 시 admission 동반 선언)
6. B6에 alias→canonical 병기 실존 · B7 gated 문구 실존 · B8 "엔진 루프 금지·COO 라운드 저작" 실존
7. 격리 워크트리 `--all` green — **유지**(조사자 조정: 지피티의 core-only 대체안은 기각.
   P7 hermetic 문제는 무-provider fresh 머신 이슈고 우리 게이트 환경은 provider 보유.
   3중 게이트 규율 완화 금지)

## 4. 검수 이력 (투명성)

지피티 위험 8 처분: **수용** 1(블록도 메뉴)·2(schema+이번 웨이브 스모크)·4(B3 채점→
비교표 evidence)·6(B7 gated)·7(B8 강화)·8(최소 스모크) + anti_hint 품질조건·B4 증거표
흡수·채택률 판독 사람 몫. **조정** 5(B5 — "write 있으면 금지"는 과잉: fast-fix 프리셋 등
소형 무인 write는 확립된 도그푸드. 계약·다중영역·고비용 write만 금지 + 개명) ·
프리셋 헤더(전면 교체 → additive 2필드). **기각** 3(human-review 드리프트 주장 —
실물 반증: assembly.py:1287 DSL 개념 토큰 실재 + translate_gate_concept canonical 변환.
단 병기 표기 관례는 채택).

증거 한계: 발주-준비 문서. 측정 앵커 0705 오후(HEAD f381faf4 이후) — 발주 시 재확인.
프리셋 통폐합·채택률 판독은 사람 몫.
