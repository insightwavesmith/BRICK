# 운영자 인체공학 웨이브 (0705 심야 Smith 독트린) — "구조만 짜게 하라"

Status: 발주-준비 상위 재료. source truth·성공 판정 아님. 시공은 착수 게이트 후 슬라이스 발주.

## 독트린 (Smith 0705 심야 원문 취지)

**build()가 엔진 스키마를 숨기듯, 오늘 밤 COO가 실측으로 저지른 실수 전 클래스를 표면이
흡수한다. 운영자 몫 = Agent/Brick/Link 그래프(구조) 저작뿐 — 축 디폴트는 표기 없이도
옳게 채워지되, 게이트(홀드 등)만은 명시 필수다.** 근거 계보: 0703 "COO의 사고 한계 =
공식 경로의 표현력 한계 = 도그푸드 사각" → 0705 "빌딩 하나 태울 때 고생하면 애초에
의미가 없다"(expand() 등재) → 본 독트린(일반화).

## 실수→자동화 후보 매핑 (0705 심야 전수 실측 — incident-corpus-0705night.md 대응)

| # | 실측 실수/함정 | 자동화 후보 (표면이 흡수) |
|---|---|---|
| 1 | 처분 building_ref 상대 경로 → goal-runs 유령 해석 → evidence_incomplete 오진(봉쇄 착시 다수) | approve/resume/correction 표면이 repo-상대 경로를 repo 기준 해석 + **부재 루트는 "building not found" 명시 거부**(오진 금지) |
| 2 | proposal JSON이 vessel 루트에 잔류 → path-shape RED | build()가 proposal을 vessel 밖 전용 자리에 persist(또는 완주 시 자동 회수) |
| 3 | 캐스팅 철자 "claude:claude-fable-5" 거부(정식 ref만 수용) | 다이얼이 관용형 정규화 또는 에러에 올바른 철자 제시("model:claude:<id>로 쓰라") |
| 4 | 셸 & 고아 발사(2회째 클래스 — 0705 Batch5 선례 있음) | 발사 전용 표면(런처 스크립트 관행 → CLI/헬퍼로: 조립 assert+report.env+백그라운드+proposal 회수 내장) |
| 5 | 계약 D 리터럴 부족(gap2a 4단 누락)·레인-불가능 D 배정(t7-recovery 언트래킹 vessel) — 둘 다 기왕 각인 규칙의 재발 | T1 린트 패턴 확장: 계약이 buildings/ 언트래킹 경로를 레인 D로 참조하면 경고 / 확장 조각 계약엔 "4단 dry-run" 문구 요구 |
| 6 | 확장 조각 수작업 접기(rows 자리·write_scope 자리 — 지피티 FATAL의 발생 지점) | **expand() DSL**(기등재 백로그) — brick()/fan() 재사용→조각 materialize+4단 dry-run 내장 |
| 7 | 미지-발견→파괴 시공 사이 게이트 누락 위험(ATT-004) | 구조 저작 표면이 파괴적 write 노드 앞 게이트 부재 시 경고/기본 삽입 — **"게이트는 필수" 원칙의 기계화**(B6 패턴 표면화) |
| 8 | adapter_cwd 세션ID 경로 함정(기왕 각인, 수동 관례로 회피 중) | 처분/재개 표면이 중립 temp cwd 자동 생성 |
| 9 | resume adapter_cwd에 **빈** 중립 dir 전달 → 확장 레인이 빈 작업장에서 걷고 정직-blocked 반환(T10 rev-1 실측 — typed 계약·QA가 적발) | 재개 표면이 adapter_cwd 미지정/비-repo면 **중립 경로의 detached 워크트리를 자동 생성**(세션ID 없는 경로 + 실제 체크아웃 — 표 8과 합본) |

## 착수 형태 (후보 — 확정은 발주 시)

expand() 슬라이스와 묶어 **인체공학 웨이브 1개**로: W-erg1(주소·오진 — 표 1) → W-erg2(발사
표면 — 표 2·4·8) → W-erg3(캐스팅·린트 — 표 3·5) → expand()(표 6·7). A+ 웨이브와 표면
겹침 대조 후 슬롯(W1 Contract Kernel과 1번이 인접). 각 슬라이스는 체커-동반(T9 원칙).

증거 한계: 매핑은 0705 실측 기반. 발주 시점 앵커 재확인. 처방 확정·우선순위는 사람 몫.
