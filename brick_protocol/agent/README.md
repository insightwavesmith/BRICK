# brick_protocol/agent/ — Agent 축 (WHO/HOW / 수행자)

**한 줄 정체:** Agent = **WHO/HOW** — 수행자 / 정책 / 능력 / 영수증 / AgentFact
(BRICK-CONSTITUTION.md 3축 절과 정합).

**비개발자 비유:** Agent는 "일을 실제로 하는 **작업자와 그 사원증·업무규칙**"이다. 무엇을
할지(Brick)는 받아오고, 어디로 넘길지(Link)는 정하지 않는다. *누가·어떤 규칙으로* 하느냐만 여기 산다.

## 폴더 지도 (git ls-files 실측)

| 경로 | 한 줄 |
| --- | --- |
| `objects/` | Agent Object 선언(YAML) — 역할별 캐스팅 대상 |
| `prompts/` | 역할별 프롬프트 자원(.md) |
| `disciplines/` | 반환 규율 문서(closed-agentfact · proof-limits · model-lane-matching 등) |
| `skills/` | 역할이 fetch-on-demand로 당겨 쓰는 스킬 매니페스트(폴더별 SKILL.md) |
| `tool_policies/` | 도구 정책(read-write-scoped 등) — 의미 능력 클래스 선언 |
| `hooks/` | 어드바이저리/가드레일 훅 레지스트리와 바인딩(registry.yaml · bindings.yaml) |
| `spec.py` | Agent 단일 출처 캐스팅 API — `CastingField`, `selected_*` 투영 |
| `return_fact.py` · `return_fact.yaml` | AgentFact 반환 축과 반환형 |
| `receipt.py` · `receipt.yaml` | 수행 영수증 축과 반환형 |
| `performance.py` · `performance.yaml` | 수행 관측 축과 반환형 |
| `__init__.py` | 패키지 마커 |

## 낯선 사람이 처음 열 것

`objects/`(역할이 무엇인지) → `prompts/`(그 역할이 받는 지시) → `return_fact.yaml`(무엇을
돌려주는지). 축 전체 개념 지도는 `brick_protocol/support/docs/references/architecture-map.md`.

## 오해 방지

- `brick_protocol/agent/skills/`와 `brick_protocol/brick/templates/skills/`의 중복은 실수가 아니라 **의도된 3면 동기화**.
  동기 규칙은 `brick_protocol/brick/templates/skills/APPLY-LIST.md` 참조.
- 스킬 매니페스트는 **오퍼 목록**이다 — 여기 실린 스킬을 에이전트가 실제로 fetch했는지는
  이 폴더가 증명하지 않는다(런타임 관측 별개).
- Agent는 **성공·품질·Movement를 판정하지 않는다.** 충분성+Movement는 Link 게이트,
  품질+성공 판정 권한은 Smith가 배분한다(기본 소재: 사람). 이 폴더의 어떤 파일도
  판정 권위를 만들지 않는다.

> support evidence only. not source truth · not success judgment · not quality
> judgment · not Movement authority.
