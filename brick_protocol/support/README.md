# brick_protocol/support/ — 지원 표면 (사실만 기록, 아무것도 판단하지 않음)

**한 줄 정체:** support는 **사실만 기록하고 아무것도 판단하지 않는다**
(BRICK-CONSTITUTION.md 3축 절). 충분성+Movement 판정은 Link 게이트, 품질+성공 판정 권한은
Smith가 배분한다(기본 소재: 사람). support는 3축(Brick/Agent/Link)이 아니라 그 셋을
**떠받치는 지원 표면**이다.

**비개발자 비유:** support는 "공장을 돌리는 **운영 데스크·검사소·기록실**"이다. 물건을
만들지도(Brick), 작업자도(Agent), 컨베이어도(Link) 아니다 — 실행을 굴리고 사실을 적을 뿐이다.

## 폴더 지도 (git ls-files 실측)

| 경로 | 한 줄 |
| --- | --- |
| `operator/` | 운영자 CLI·빌더·엔진(플랜을 걷는 기록자)·읽기측 투영 — 진입/실행 표면 |
| `checkers/` | 프로파일 러너 + 커널 체커 + 선언형 프로파일 + `module_registry.yaml` census |
| `connection/` | Agent-brain / 어댑터 / MCP / 동기화 연결 표면 |
| `recording/` | 결정적 증거 기록기(capture · raw · claims · spine) |
| `docs/` | 참조 문서 — spec · reviews · references(architecture-map 등) · projection |
| `onboarding/` | 설치 스크립트 + provider-native open/close 훅 템플릿 |
| `dashboard/` | 벤더링된 읽기-측 대시보드 표면(React + SSE) |
| `import_identity/` | `brick_protocol.*` 네임스페이스 마커가 사는 곳 |
| `__init__.py` | 패키지 마커 |

## 낯선 사람이 처음 열 것

`docs/references/architecture-map.md`(모듈이 뭘 하고 실행이 어떻게 흐르는지) →
`operator/`(진입점). 모듈 census의 정본은 `checkers/module_registry.yaml`.

## 오해 방지

- `operator/run.py`·`operator/dynamic_walker.py`는 **스케줄러·2차 엔진이 아니다** — 선언된
  플랜을 걷고 증거를 남기는 **기록자**다. 큐·재시도 권위·Movement 판정은 여기 없다.
- `dashboard/`는 **읽기-측 투영**일 뿐 — 이미 쓰인 증거를 보여줄 뿐 성공·품질을 판정하지 않는다.
- `module_registry.yaml`은 **법이 아니라 지켜지는 census** — 온-디스크 모듈과 양방향으로
  묶여(G4 엘레강스 가드) 조용히 드리프트하지 못한다. 축의 법은 `BRICK-CONSTITUTION.md`.
- `brick_protocol.*` 네임스페이스 마커가 `import_identity/` 아래 사는 이유: import 정체성을
  단일 지점에 고정해, 축 코드가 물리 경로와 무관하게 한 이름으로 임포트되도록 하기 위해서다.

> support evidence only. not source truth · not success judgment · not quality
> judgment · not Movement authority.
