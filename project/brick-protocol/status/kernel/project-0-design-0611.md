# PROJECT-0 — "프로젝트" 개념 설계 (0611, Smith 결정 반영)

Status: DESIGN — Smith가 답한 4결정 반영, 빌드 전. 이 문서는 설계 기록(support record)이며
source truth / success judgment / Movement authority가 아니다.

## 0. 발견과 결정 (Smith, 0611)

발견: task→building 사슬은 완성됐는데, 빌딩이 쌓이는 그릇(프로젝트)을 **만드는 개념이 없다.**
전부 `project/brick-protocol/` 단일 하드코딩 — 도그푸드(자기개발) 시절의 흔적.

Smith 결정 4개:
1. 프로젝트 = **폴더 + 선언 레코드** (`project/<id>/project.json` — 방향성·참여자·라벨).
2. **한 repo 안에 여러 프로젝트** (`project/<id>/` 병렬). 미래의 "repo=프로젝트 1개" 전환이
   가능하도록 경로 유도는 한 곳에 모은다.
3. **task 앞에 프로젝트 체크** + **프로젝트 생성 스킬**: 큰 방향성 정의가 먼저다.
4. 기존 `project/brick-protocol/` = 1호 프로젝트로 동결(마이그레이션 없음).
   BAR-v2 부모목표 = 프로젝트 방향성과 **연결**(흡수 아님). portfolio = 프로젝트 내 실행 패턴으로 존치.

## 1. 모델 (0611 보강 — Smith: "목적부터. 프로젝트의 README가 필요하다")

브릭의 기존 2층 패턴(.md=사람 / 기계 선언)을 프로젝트에도 동형 적용한다:
brick.md+return.yaml ≅ README.md+project.json. "왜"가 먼저, 기계 선언은 그 그림자.

```
프로젝트 (동네)
 ├ README.md           ★프로젝트 헌장 — 사람+에이전트가 읽는 글 (엔진 비파싱, task.md 지위)
 │   목적(왜 존재) / 생성 이유(왜 지금, 배경·문제) / 방향성(어디로, 서사) /
 │   완료·진척의 기준 / 범위 밖(안 하는 것) / 관리자(사람 owner만 — Smith 0611:
 │   에이전트는 계속 바뀌므로 헌장에 안 적음; 누가 일했나는 AgentBinding 증거가 투영)
 │   이 동네에서 일하는 모든 에이전트가 먼저 읽는 문서.
 ├ project.json        ← 기계 선언 (헌장에서 추출된 사실 요약; 생성 동사가 박제)
 │   project_ref: project:<id>, label,
 │   direction(방향성 한 문장 = BAR-v2 parent goal의 공식 자리),
 │   done_means, out_of_scope, managers[](사람만), declared_by, declared_at,
 │   charter_ref: project/<id>/README.md
 ├ buildings/<building_id>/...   ← 기존 빌딩 증거 구조 그대로
 ├ status/                       ← per-project (inbox 등)
 └ _portfolio-projections/       ← per-project
```

- 빌딩의 프로젝트 소속 = **경로가 1차 사실**(어느 동네에 물리적으로 있나) + 레저가 project.json을
  읽어 라벨/방향성을 투영. 빌딩 패킷에 새 필드를 박지 않는다(스키마 불변, 체커 핀 비용 0).
- closure의 parent_goal_delta_status가 보고하는 "부모 목표" = 그 동네 project.json의 direction.
  (이미 있는 장치에 빈자리였던 선언처를 제공 — 연결만, 새 발명 없음)
- building_id 유일성 = 프로젝트 내. 대시보드 delta/detail 키 = (project_ref, building_id) 복합.

## 2. 흐름 (Smith #3 반영)

```
0. 프로젝트 생성 스킬 (COO 스킬, project-creation) — 헌장 우선 (Smith 0611)
   대화로 헌장(README.md)을 함께 작성한다. 질문은 헌장의 칸을 채우기 위한 것:
     목적(왜 존재) / 생성 이유(왜 지금) / 방향성(어디로) /
     완료·진척 기준 / 범위 밖 / 관리자·이름 (에이전트 명단 X)
   (ChatPRD 메모0610 철학 준수: 잘-쓰는-법 처방 금지 — 칸을 채우는 질문만)
   → 사람이 헌장 확정 → 기계가 헌장에서 선언(project.json) 추출·박제
   → buildings/ 등 동네 골격 생성
1. task intake — 프로젝트 체크 선행: "어느 프로젝트?" 없으면 생성 스킬로 안내.
   intent에 project_ref 추가(선택→이후 필수화 단계적). output_root가 그 동네로 유도.
2. 빌딩 실행/증거 = 기존 그대로, 동네만 달라짐.
3. 대시보드 = 동네별 (UI는 이미 복수 렌더 가능; 소스만 다중화).
```

## 3. 6문 (phase-start 의무)

1) 축 모듈인가? — 아니다. 프로젝트는 support 차원의 **증거 조직 + 선언 레코드**.
   Brick/Agent/Link 의미 불변. project.json은 Movement/품질/성공 판단 0.
2) support인가? — 그렇다. 생성 동사·레저 투영·경로 유도 전부 support. 판단 없음(기록만).
3) 기존 주인이 있나? — 경로 유도의 주인 = capture.py(DEFAULT_BUILDINGS_ROOT).
   확장: `buildings_root_for(project_ref)` 단일 함수로 — root-anchor 체커 핀이 따라간다.
   방향성의 주인 = BAR-v2 parent goal 장치(이미 존재) — 선언처만 연결.
4) 왜 축에 못 사나? — 프로젝트는 일(Brick)도 수행자(Agent)도 이동(Link)도 아닌 **그릇**.
   세 축의 어느 계약에도 속하지 않는 조직 개념이므로 support가 정위치.
5) 체커 먼저인가? — 그렇다. 빌드 슬라이스 1 = 체커부터:
   a. 선언 없는 동네 거부: `project/<id>/`가 있는데 README.md(헌장) 또는 project.json이
      없거나 direction이 비면 RED — 헌장 없는 동네도, 선언 없는 동네도 불허
      (무침묵 원칙의 프로젝트판 — Smith #3의 "체크 먼저"가 체커로도 강제됨)
   b. 침묵 갭 3곳 일반화(접지에서 발견): building_map_graph 스캔 글롭,
      catalog_restructure 입력 루트, 세션ID 스캔 루트 — project/* 전체를 쓸도록.
      (지금은 새 동네가 생기면 조용히 안 보는 상태 = 가짜 green)
   c. admission: project/<id>/{project.json,buildings/**,status/**,_portfolio-projections/**}
      클래스 일반화(현재 brick-protocol 리터럴 핀들).
6) impl closed인가? — 생성은 선언 동사로만(스킬→기계 박제), 폴더 손생성은 a로 거부.
   1호 동네는 project.json을 소급 박제(동결 원칙 위반 아님 — 새 선언 추가일 뿐).

## 4. 빌드 슬라이스 (모놀리식 금지)

S1 체커+선언: project.json 스키마/로더 + 위 5-a/b/c + 1호 동네 선언 박제. (--all green)
S2 생성 동사: support/operator/project_creation.py(기계 박제) + COO project-creation 스킬(질문 4개)
   + projection 재생성. FIRE: 선언 없는 폴더 RED / 생성 동사 산출물 green / 중복 id 거부.
S3 intake 연결: intent.project_ref(선택) → buildings_root_for 유도; task-by-text(R3)와 합류;
   프로젝트 체크 안내문. FIRE: project_ref 있는 intake가 그 동네에 빌딩 생성.
S4 레저/대시보드 다중화: ledger가 project.json들을 읽어 다중 프로젝트 패킷;
   delta/seed에 project_ref·participant_ref 태깅; UI 복합키(클로버 방지).
   1호 동네 기본값 문자열 제거(선언에서 읽음).
S5 codex 적대검토 + 신선-클론 재감사에 "프로젝트 생성→task→빌딩→대시보드" 여정 추가.

## 5. 안 하는 것 / not proven

- 빌딩 패킷 스키마 변경 없음(소속=경로 사실). cross-repo 집계 없음(미래, repo=프로젝트 전환 시).
- portfolio/BAR-v2 기계 자체는 불변(연결만). 1호 동네 역사 불변.
- not proven: 다중 참여자 동시 운영, 프로젝트 간 이동/병합, 대시보드 실서버 다중 프로젝트 표시.
