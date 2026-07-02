---
name: building-sizing-method
description: BRICK 빌딩 사이징 — 일의 크기/모양을 그래프 모양(노드 KIND·팬·QA깊이·감독)으로 환산하는 방법. "이 일은 빌딩 몇 단계로, 누가 병렬로, QA 몇 렌즈로?"를 정할 때. 워크플로 사이징의 거울. 모양만 산출하고 발사는 brick-task-author로 넘긴다.
---

# 빌딩 사이징 방법 (워크플로 사이징의 거울)

> 이 스킬은 **모양만** 만든다(노드 KIND·팬·QA깊이·감독 다이얼). 만든 compact graph / graph packet shape나
> `GraphSpec` 재료를 **brick-task-author**에 넘긴다. 공식 launch interface는 **`assemble()`/`build()`/`fan()`
> DSL**이다(Rule 10). `fan()`은 `build()` 안의 병렬 재료이고, `fire()`는 내부 구현/debug 용어다.
> 손-작성 `graph_packet` JSON(`brick build --graph <packet>`) CLI 입력은 retired다. DSL이
> 이제 `sibling_independence`, 노드별 explicit `write_scope` 좁히기, mid-graph human/coo gates를
> 표현한다. 이 스킬은 발사하지 않는다.

## 한 줄 핵심 — 워크플로는 에이전트를 사이징, 빌딩은 KIND를 사이징

빌딩 사이징은 고정 `work -> QA -> closure` 찍기가 아니다. task마다 사용 가능한 LLM을
두뇌로, Brick KIND를 손발로, Graph를 신경망으로 배치한다. 이 배치 판단 자체가 BRICK dogfood다.
쓰기 손발이 필요한 모양이면 `work` KIND를 고르는 것에서 끝나지 않는다. 산출 GraphSpec에
`write=True` 필요를 표시하고, 발사 단계(brick-task-author)에서 bounded `write_scope`를 함께
넘기게 해야 한다. `write_scope`만 넘기는 모양은 read-only smoke가 되어 변경을 만들지 않는다.

워크플로에선 **에이전트를 직접 사이징**한다(몇 명·어느 모델·병렬·적대·스케일이 독립 다이얼).
빌딩에선 **KIND를 사이징**하고, **KIND가 에이전트를 데려온다**. 너는 에이전트를 절대 지목하지 않는다.

실측 확인된 KIND→에이전트 바인딩 (노드의 kind를 고르면 role/provider/write/verdict가 자동 결정):

```
  work            → agent-object:dev    (codex,  write=yes)   ← 유일한 구현자
  design          → design-lead         (codex, write=no)     ← 범위 바운딩
  closure         → coo                 (codex, verdict)      ← 종합+판정
  review          → qa-lead             (read-only return-shape/evidence review)
  inspect         → inspector           (read-only axis/evidence/policy inspection)
  code-attack-qa  → qa                  (codex/gemini, write=yes 코드 재현/회귀 공격)
  axis-attack-qa  → inspector           (write=yes 축/권위 누수 공격)
```

## 결정표 — 5차원을 빌딩 원시로 번역 (척추)

| 워크플로 다이얼 | 빌딩 원시 | 사이징 규칙 |
|---|---|---|
| **1. 일 분해 ⇒ 에이전트 수** | **노드 수 + KIND** | 일관된 일 한 단위 = 노드 1개. **KIND가 그 단위의 정체를 명명**한다: 바운디드 읽기목록=`design`; 구현=`work`(codex, write); 읽기전용 평가=`inspect`/`review`; 종합+판정=`closure`. 작은 요청은 한-브릭(`one-brick-do`/`quick-check`)으로 접고, 큰 요청은 척추를 늘린다. |
| **2. 독립 ⇒ 팬** | `fan([a, b, …])` | 상호의존 없는 가지 = `fan()` 블록. 앞 노드=소스, 뒤 노드=수렴. 워크플로 `parallel()`과 정확히 같다. |
| **3. 의존 ⇒ 세로** | `build()` 척추 순서 | 인접 N→N+1 이 **곧 forward edge이자 데이터 운반**(`_auto_declare_chained_carry`). 운영자는 edge·id·carry를 안 쓴다. |
| **4. 저신뢰 ⇒ 검증 렌즈** | 리뷰어 KIND 노드 (`review`/`inspect`/`code-attack-qa`/`axis-attack-qa`/`evidence-integrity`), 보통 fan → `closure` | `QA`를 한 덩어리로 고르지 말고 렌즈를 고른다: 코드 정확성/회귀=`code-attack-qa`; Brick/Agent/Link 권위 경계=`axis-attack-qa`; 증거 루트/증명 한계=`evidence-integrity`; 읽기전용 반환/근거 대조=`review`; 읽기전용 구조/정책 점검=`inspect`. 고신뢰=**0**렌즈(`design→work→closure`); 중신뢰=**1**렌즈; 저신뢰/계약·정책·보안·권위를 건드리면=**2~3**렌즈 fan→closure. |
| **5. 스케일 ⇒ 깊이/폭** | 두 레버 | (a) **모양 사다리**: 한-브릭 → `design+work+closure` → +검증 fan → 포트폴리오/부모-골. (b) **감독 다이얼**(`assemble()` 입력서): `gates=()` 완전 무인 vs `gates=("human-review",)` 머지 경계서 HOLD — 강한 요청을 사람 체크포인트로 올리는 빌딩 버전. |
| **6. 재작업 가능성 ⇒ Link 정책** | `route=` / declared route policy / closure concern | `build()`/`fan()`의 기본 edge는 **forward**다. 사용자는 Link row를 직접 쓰지 않지만 support가 forward Link row를 materialize한다. blocker가 나올 수 있으면 QA fan 뒤에 closure-synthesis를 두고, closure만 Link-facing `transition_concern_evidence`를 반환하게 하며, Link/COO가 declared policy로 reroute/HOLD를 채택하게 만든다. |

## 큰 일 P3 기본형

크거나 번질 가능성이 큰 task는 한 `work` Brick으로 바로 사이징하지 않는다.
사용자-facing 축약은:

> this is big; design first, split it, and run the lanes in parallel.

기본 모양은 다음 순서다:

```
task intake
→ design
→ design QA / axis inspection
→ closure confirms execution plan
→ parallel dev lanes
→ each lane dev then QA
→ fan-in integration/summary
→ Codex code/regression QA + Gemini-local axis/evidence QA
→ Codex closure
```

이 모양은 design-first fan-out 또는 DSL graph로 표현한다. 그래도 Link가
Movement authority를 소유하고, support/model/checker/Slack은 source truth나
quality/success judge가 아니다.

## KIND 카탈로그 = 사이징 메뉴 (실측 set)

```
design          codex 리더, 범위 바운딩, write 없음
work            codex 워커, 유일한 구현자, write=yes
closure         codex/coo, 판정+종합
review          qa-lead, 읽기전용 반환/근거 대조
inspect         inspector, 읽기전용 축/구조/정책 점검
code-attack-qa  qa, write=yes 코드 재현/회귀 공격
axis-attack-qa  inspector, write=yes 축/권위 누수 공격
evidence-integrity  inspector, write=yes 증거 무결성 공격
plan/development    리더 변형
```

**제약(brick-task-author §알아둘 것에서):** verdict/추론 KIND(design/closure/review/inspect)에
`adapter:local` 사용 금지(스텁이라 verdict 못 냄). 현재 dogfood 기본(0702)은
**codex=구현+closure+code-attack-qa · claude(sonnet·xhigh)=inspect/axis-attack-qa/evidence-integrity · gemini=review(qa-lead) · 검증 fan=codex+claude+gemini 교차**다.
어댑터 풀·effort 어휘의 정본은 brick-task-author §알아둘 것 (0702: claude active, inspector 기본).
**codex-FUGU(Sakana fugu-ultra·high)는 design 노드에 허용한다** — Fugu의 깊은 설계가
표준 구조의 한 축이고, 운영자가 명시 채택(Smith 0624). Fugu는 가두지 않는다: 깊은 설계를 직접
*생산*한다. (fugu-on-design 스모크 통과; 간헐 이슈가 실재하면 도그푸딩이 잡는다.)

## 공식 경로와 graph packet 재료

공식 실행 경로는 하나다:

```
brick build / support.operator.cli build
→ Builder/materializer
→ declared Building Plan
→ support/operator/run.py walker
→ active vessel evidence root
→ reporter / Slack / frontier
```

공식 authoring/launch interface는 `assemble()`/`build()`/`fan()` Python DSL이다(Smith 0701 결정,
Rule 10). 프리셋 모드와 DSL 그래프 모드는 이 DSL을 통해 같은 공식 build surface(엔진은 여전히
`compose_building()`, Rule 9)로 들어간다 — 같은 공식 build surface로 들어가는 두 입력 모드다.
P3 운영자-facing 기본은 **`build()`만**이다. `build()`, `fan()`, `assemble()`,
`launch_assembled_building`은 이 공식 DSL의 부분이고 `compose_building()`은 그 아래 엔진이다.
실행 안내는 helper나 `fire()`가 아니라 운영자-facing `build()`/`assemble()`로 보내라. 손-작성
`graph_packet` JSON(`brick build --graph <packet>` / `support.operator.cli build --graph <packet>`)은
public CLI 입력에서 retired다. 공식 route처럼 일반 안내하지 마라.
Profile compatibility note: the old phrase "graph packet / materialization / official-route 내부 sugar" is retained here only as historical checker text, not current operating guidance.

## 난이도→다이얼 환산 (4축 카드 — 0702)

"난이도"는 스칼라가 아니라 4개 축이고, 축마다 다이얼이 정확히 하나 대응한다.
사이징 전에 4문항에 답하고, 각 답을 **해당 다이얼에만** 반영한다. 축 하나의 문제를
다른 축의 다이얼로 푸는 것이 오버/언더사이징의 본체다.

| 축 (질문) | 다이얼 | 규칙 |
|---|---|---|
| ① 분량 — 한 컨텍스트가 정독 가능한 양인가? | 팬 폭 (재료 분할) | 밀도 높은 코드 레인당 ~1,000줄 기준. ceil(분량/1k)=레인 수. 같은 두뇌, 다른 구간. |
| ② 판단 분산 — 유능한 둘이 같은 입력에서 다른 답을 낼 확률이 유의미한가? | LLM 다양화/렌즈 수 (두뇌 중복) | 반증 가능한 사실 추출=1두뇌+반증 실행 1렌즈. 반증 불가한 판단(설계 선택)=2~3 교차 LLM. 같은 재료, 다른 두뇌. |
| ③ 오답 파급 — 틀리면 뭐가 부서지나? | 게이트/사람검토 | read-only 조사=무인+산출물 사람검토. 소스변경=QA fan. 계약·권위·보안=human-review HOLD. |
| ④ 결합도 — 조각이 서로의 결과를 필요로 하나? | 세로 vs 팬 | 의존 없으면 fan. 경계를 미리 박아 의존을 제거할 수 있으면 제거하고 fan. |

**법칙: 사실은 쪼개고, 판단은 겹친다.** 분량 문제(①)를 교차 LLM(②의 다이얼)로 풀면
같은 구간을 여러 번 읽는 낭비. 판단 문제(②)를 재료 분할(①의 다이얼)로 풀면 부분만 보고
판단해 품질이 떨어진다. "llm별로 쪼개기"와 "조사 레인 늘리기"는 다른 축이다.

**팬 폭의 진짜 상한 = fan-in 수렴 노드의 소화력.** 모든 레인 반환이 수렴 노드 컨텍스트에
들어가야 한다. 레인 반환 스키마를 고정(항목·표 형식 강제)하고 팬이 넓을수록 반환을 압축해라.
토큰이 남아도 수렴이 익사하면 오버사이징이다.

적용 예 (7,176줄 체커 파일 조사): ① 7,176줄 → 7레인 ② 정독=반증 가능한 사실 추출이라
단일 LLM+반증 review 1렌즈, 클러스터 경계 판정(합성)만 상위 모델 ③ read-only라 무인+맵
사람검토 ④ 스팬을 발사 전에 박아 레인 간 의존 0 → fan.

## 과대-사이징 금지 규칙 (단순+완전 신조)

- 읽기목록이 이미 바운디드면 **`design` 노드를 더하지 마라.**
- 신뢰필요가 낮으면 **검증 fan을 더하지 마라.**
- 한 스텝이면 충분하면 **한-브릭으로 접어라**(`one-brick-do`/`quick-check`/`fast-fix`).

## 한 일을 두 가지로 사이징한 예 (다이얼을 느껴라)

**저위험** (신뢰 높음, 계약 안 건드림):
```python
from brick_protocol.support.operator.assembly import assemble, build, Authority
from brick_protocol.brick.spec import brick
graph = build([
    brick("design",  "범위를 좁혀라(바운디드 읽기목록)"),
    brick("work",    "변경하라", write=True),  # 발사 시 write_scope도 함께 넘길 것
    brick("closure", "검증·보고하라"),
])
# gates=() — 완전 무인
```

**고위험** (계약·정책·보안 건드림, 신뢰 낮음):
```python
from brick_protocol.support.operator.assembly import assemble, build, fan, Authority
from brick_protocol.brick.spec import brick
graph = build([
    brick("design",  "범위를 좁혀라(바운디드 읽기목록)"),
    brick("work",    "변경하라", write=True),
    fan([
        brick("code-attack-qa",    "구현을 공격하라"),
        brick("axis-attack-qa",    "축 위반을 공격하라"),
        brick("evidence-integrity", "증거 무결성을 공격하라"),
    ]),
    brick("closure", "종합·판정하라"),
])
# gates=("human-review",) — 머지 경계서 HOLD
```

## 재사용하라, 다시 짓지 마라

`brick/templates/presets/*.md`(28개 프리셋)은 **미리-사이징된 참조 모양**이고, 그 안의
`selection_hint` 줄이 **"언제 이렇게 사이징하나" 코퍼스**다. 이 사이징 방법은 프리셋 고르기의
생성형 보완이다 — 맞는 프리셋이 있으면 brick-task-author의 PRESET 입력 모드로, 없으면 이 스킬로
GRAPH 모양을 사이징한 뒤 brick-task-author가 공식 DSL build surface로 넘긴다.

## 산출물

이 스킬의 산출물 = **graph packet shape**(또는 그 shape를 설명하는 `GraphSpec`,
`build([...])`/`fan([...])` helper 호출).
brick-task-author가 그 모양을 `assemble()`/`build()`/`fan()` 공식 DSL 호출로 받아 제출하고,
Builder/materializer → declared Building Plan →
`support/operator/run.py` walker → active vessel evidence root → reporter/Slack/frontier로 보낸다.
(손-작성 `graph_packet` JSON CLI 경로는 retired다.)
