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
| 4 | 셸 & 고아 발사(2회째 클래스 — 0705 Batch5 선례 있음) + CLI build `--timeout` 미지정 발사(기본 120초 → 부검 fleet codex 렌즈 local_cli_timeout 주차, 0705 실측) | 발사 전용 표면(런처 스크립트 관행 → CLI/헬퍼로: 조립 assert+report.env+백그라운드+proposal 회수+**정독-레인 안전 타임아웃 기본값** 내장) |
| 5 | 계약 D 리터럴 부족(gap2a 4단 누락)·레인-불가능 D 배정(t7-recovery 언트래킹 vessel) — 둘 다 기왕 각인 규칙의 재발 | T1 린트 패턴 확장: 계약이 buildings/ 언트래킹 경로를 레인 D로 참조하면 경고 / 확장 조각 계약엔 "4단 dry-run" 문구 요구 |
| 6 | 확장 조각 수작업 접기(rows 자리·write_scope 자리 — 지피티 FATAL의 발생 지점) | **expand() DSL**(기등재 백로그) — brick()/fan() 재사용→조각 materialize+4단 dry-run 내장 |
| 7 | 미지-발견→파괴 시공 사이 게이트 누락 위험(ATT-004) | 구조 저작 표면이 파괴적 write 노드 앞 게이트 부재 시 경고/기본 삽입 — **"게이트는 필수" 원칙의 기계화**(B6 패턴 표면화) |
| 8 | adapter_cwd 세션ID 경로 함정(기왕 각인, 수동 관례로 회피 중) | 처분/재개 표면이 중립 temp cwd 자동 생성 |
| 9 | resume adapter_cwd에 **빈** 중립 dir 전달 → 확장 레인이 빈 작업장에서 걷고 정직-blocked 반환(T10 rev-1 실측 — typed 계약·QA가 적발) | 재개 표면이 adapter_cwd 미지정/비-repo면 **중립 경로의 detached 워크트리를 자동 생성**(세션ID 없는 경로 + 실제 체크아웃 — 표 8과 합본) |
| 10 | resume이 fan/하류 노드의 step-output source_fact 해소 실패("missing step-output source_fact body/evidence" — bundle10-0705b·0705c **2회 재현**, 처분은 수용되나 재개가 죽음) | 재개 경로의 vessel-상대 source_fact를 vessel 루트 기준으로 해석(경로 해석 가족 — 표 1과 동족) |
| 12 | T10 운전이 만든 rev-N.json·expansion-approvals.jsonl이 package_path_admission 세트 밖 → 라이브 스윕 rc=1(오늘 밤 push 2회 차단, 잔해 클래스 — 코드 무관) | 운전/확장 산출물(rev·approval)을 admission 세트에 자동 편입하거나 seed admission이 buildings/**/work 정규 산출 파일명을 인지(표 2 proposal 잔해와 동족) |
| 11 | 같은 빌딩 순차 처분 2회를 resume replay가 미지원("already-disposed recorded HOLD ... unsupported prior disposition" — t10-0705a 실측) | replay 체인이 처분 이력 다중화를 수용(0702 결함 가족 ② 소비 시공— T7 계열) |
| 13 | COO dispo 워크트리를 adapter_cwd로 쓴 walk가 **완주해도 산출 커밋/WIP 앵커가 안 생김** — 세션 파손 시 미커밋 잔류(0706 실측: erg3 완주 산출이 dangling에도 refs에도 없고 dispo 워크트리에 미커밋으로만 존재, 게다가 11B v1 잔출과 **한 워크트리에 혼합** — 회수에 fsck 전수 + 워크트리 법의학 + blob-exact 훅 분할 필요) | walk 완주/정지 시점에 adapter_cwd가 엔진 관리 밖 워크트리면 **자동 WIP 앵커**(refs/brick/wip) 생성 + 발사 표면이 이미 dirty한 cwd 재사용 시 경고(빌딩 간 산출 혼합 방지) |
| 14 | 긴 스윕(--all 7분+)이 멈췄는지 도는지 표면이 말 안 해줌 — provider 렌즈 무한대기(0705 부검 fleet 실측)를 프로세스 CPU·로그 증가량으로 손수 갈라야 했다. per-profile START/DONE·heartbeat=60s 로그는 실존하나 **스윕 전체 진행률·무진행 스톨 감지 부재** — 자율운행에서 멈춘 걸 모르면 세션이 죽는다 | 스윕 러너에 전체 진행률(k/N 프로파일)+무진행 스톨 감지(하트비트 초과 시 현재 프로파일 지목 경고, 옵션 타임아웃) |
| 15 | 발주 표면 표현력 갭(0706 t7b 발주 실측): 커스텀 fan 모양·per-node 위험-비례 캐스팅(0705 모델정책)·per-node work_statement·source_facts·확장 조각이 CLI로 표현 불가 + 공개 build()는 `(*args,**kwargs)` 불투명 래퍼·one-call은 task=goal 접힘 → COO가 **밑줄-프라이빗 헬퍼 임포트 미러링**으로 발사(런처 파이썬의 근본 원인 — 골 문서 "무마찰 발주" 절의 실측 근거) | CLI/선언 표면이 그래프 선언(모양+per-node 캐스팅+source_facts+전문 task) 1개를 통째로 받아 발사 — 런처 파이썬 소멸이 판정선 |
| 17 | **입구별 기본 캐스팅 비대칭**(0706 기전 정정): 동일 플래그(CLI --real-provider, 무-adapter)에서 fast-fix work=claude-local vs engine-feature-hard work=codex — 프리셋/스텝템플릿별 해석 경로가 달라 생기는 비대칭(초기 가설 '첫-프로바이더 전역 견인'은 부분 오판, engine-feature work=codex 실측으로 정정). 운영자는 codex 기본으로 인지, Smith 혼동 실사례 | CLI도 role별 오브젝트-해석 사용(--real-provider는 스텁→실물 전환만) 또는 발사 응답에 해석된 캐스팅 표 첫-출력(표 16 repo_root 동족). 당장 회피 = CLI에 --adapter 명시 |
| 18 | **모델 별칭의 조용한 증발**: 오브젝트가 model:claude:sonnet(별칭)을 선언해도 어댑터 디스패치에 --model 미전달 → CLI **계정 기본 모델로 무언 폴백**(0706 실측: erg6 QA 레인 --model 부재, 완전-수식 claude-fable-5는 전달됨 — 소넷-지정 QA 전부가 계정 기본(오푸스4.8)으로 주행, 비용 초과+정책-실측 불일치, Smith 적발) | 어댑터가 별칭을 카탈로그(LLM_ALIAS_DECLARATIONS)로 해석해 --model 명시 전달, 해석 불능 ref는 **loud 거부**(조용한 폴백 금지) + 디스패치 usage 행에 실모델 기록 |
| 16 | **pipx-설치 `brick`이 낡은 제2 체크아웃(~/BRICK, 편집-설치 바인딩)을 repo_root로 조용히 채택** — cwd(정 repo의 워크트리)도 무시, --repo 미지정 시 경고 없음. 0706 실측: CLI 발주 3건이 이틀 낡은 트리(75a96e26) 위를 걸음 — 1건은 수리 대상 파일이 존재하지도 않는 트리에서 완주(산출 무효), 2건은 design 홀드에서 폐기, 레인 비용 전액 손실 | 발사 표면이 ①resolved repo_root를 발사 응답 첫 줄에 출력 ②repo_root ≠ cwd-repo면 경고 ③repo_root HEAD가 origin 대비 N커밋 뒤면 경고/거부. 운영 규율: 항상 repo 자신의 `.venv/bin/brick` + `--repo` 명시 |
| 19 | **부하-타이밍 flake 체커 클래스**(0706 저녁 실측, Smith 등재 지시): 절대 벽시계 상한을 가진 걸음-fixture 단언이 라이브 스윕의 부하(병행 걸음 3기+조사 레인)에서만 간헐 RED — ①preset 완주 fixture(engine-feature-hard) agent_incomplete ②R3 신규 FIRE의 elapsed<2.25s 상한 초과(데드라인은 발화했는데 스톱워치가 늦음). 둘 다 격리 게이트에선 green, 라이브에서만 RED — push 2회 차단. 잔해 클래스(표 12)와 별개: 이쪽은 코드가 아니라 '판정 형태'가 원인 | 걸음-fixture 판정을 절대시간이 아니라 **증거-형태**(dispatch-child-timeout 행 실재·paused 홀드 행·frontier 종류·변이 시 그 부재)로 — 벽시계 상한 금지, **숫자 키우기 금지**(Smith 0706 저녁 원문). 수리처 = r3margin 재파견분. 생산측 데드라인 마진(+30s 플로어)은 preset flake 쪽을 흡수 |

| 20 | **초안기 제안측 부재 — 분할을 감지해도 팬을 안 그린다**(0707 실측, resume-rootfix-design-0707a 초안, Smith 등재 지시): 8답이 entangled·splittable=yes·file_conflict=no·failure_cost=high인데 초안기는 단일 work(+deep-design 삽입) 모양을 유지하고 rationale에 `note-split-candidate | graph shape unchanged (single work node) | 분할 후보: 별도 빌딩 발주 검토 — operator Movement-adjacent` 한 행만 남김 — 운영자가 선언 파일을 fan[design×3 이종]→closure로 수동 교체 후 발사. 거부측(안티패턴 RED)은 gt-checker-slice-0707a가 박는 중이나 **제안측**(폭 N=min(신호 사다리, 파티션 수, κ 하향, 3) 계산·병렬 설계/시공 팬 자동 제안·2단 표준형 1단 그래프 제안)은 부재 | #15 규칙표 증분 후속 발주(방아쇠=gt-checker-slice 랜딩): 폭 신호용 9번째 답 신설 + min() 폭 계산 + fan 자동 제안 결정표 행. 실측 원문 = walk-results-adopted-0707.md §E |

| 21 | **걷는 함대 헬스 체크기 부재**(0707 실측, 4기 병행 주행 점검에서 Smith 질문으로 표면화): 걷는 빌딩들의 건강 판정에 운영자 손 프로브 7종이 필요했다 — ①observe_building_frontier(증거 정적 뷰 — docstring이 프로세스 비관측 명시) ②walker 프로세스 실존 ③claude 레인 pgrep+lsof 소켓 ④codex 레인 프로세스+worktree 매칭 ⑤adapter-error.jsonl 부재 ⑥report-delivery 이벤트 카운트 ⑦CLI 산출 캡처(bp-codex-cli-*) 크기. `brick status`는 어댑터 경계 행렬만 반환, 걷는 빌딩 섹션 없음. 종료-레인 판정("프로세스 종료+adapter-error 무 = 정상 반환")도 운영자 추론에 의존 | `brick status`(또는 `brick watch`)에 걷는-빌딩 절: vessel별 frontier_kind + 레인 종류별 생존(codex=proc, claude=proc+socket) + received/returned/error 카운트 + 최근 이벤트 시각을 한 표로. 레인 종류별 개시·생존 잣대(0707 교훈)를 표면이 내장 |

| 22 | **발사 이중 열쇠**(0707 실측, Smith 지적: "넌 구조만 그려야 하는데"): 초안 기본 action=stop은 법(Rule 3 자동발사 금지)대로 옳으나, 발사하려면 선언 파일 내부 action 필드를 손-편집해야 함(CLI 오버라이드 부재 실측) — `brick build --graph-decl`를 치는 행위 자체가 명시 승인인데 파일 편집을 또 요구. 0707 실사례: COO가 action 세팅을 빠뜨려 동결-정지(무해) 후 --overwrite-existing 재발사 2회전. 운영자의 decl JSON 손-편집(캐스팅 재조정·하향 교정 포함)이 상시화된 것 자체가 증상 | CLI `--forward`(또는 --action) 플래그 — 파일 무편집 발사. 초안 손질류(QA 재캐스팅·하향)는 draft 재호출 인자로 흡수 |
| 23 | **초안기 캐스팅 하드코딩**(0707 실측, Smith 지적: "다른 유저는 다른 LLM 쓴다"): graph_draft.py:62-92에 fugu-ultra·fable-5·opus-4-8·codex·gemini 리터럴 직박 — 자가 운영 독트린을 코드에 새겨 제품 이식성 파괴(타 provider 고객에게 무의미/오작동) | 초안기는 캐스팅-**티어**(기본/승격/기획/경량검증)만 발화하고, 티어→모델 해석은 agent/objects·discipline:model-lane-matching 선언층 + provider 준비상태(brick auth)에서 단일 해석(#12 원칙의 초안기 적용). 중형 후속 발주 후보 |

| 24 | **재개-시점 캐스팅 오버레이 부재**(0707 Smith 등재 지시: "홀드 치고 디자인 봤다, 개구리다 — 소넷5에서 페이블5로 바꿔 이어가기"): 홀드에서 새로 잇는 가지의 캐스팅은 자유(개정 가지별 casting — 사다리 2단 실증)이나, **이미 선언된 기존 하류 노드의 캐스팅 교체는 불가** — 개정이 add-only라 기존 행 수정 금지, 우회는 새-선언뿐. 도면 판독 결과 난이도가 상향 재평가되는 경우가 정확히 2단 표준형의 정상 사용례라 마찰이 구조적 | **재개-시점 캐스팅 오버레이**: walker_resume가 개정 체인에서 expansion_node_budgets를 오버레이로 읽는 기존 메커니즘(walker_resume.py:1238)과 동형으로, 노드별 casting 오버레이(원본 행 불변·재개 시 겹쳐 읽기)를 개정 팩킷에 수용. 백로그(직결 1회 실증 후) |

## 착수 — Smith 0705 심야 2차 지시로 승격

**"build()도 재시작(resume/approve)도 동일하게, 미친듯이 깎는다 — 엔진 교정과 동급."**
후보가 아니라 즉시 착수 웨이브다. 슬라이스 1(재개·처분 표면: 표 1·8·9·10) 발주됨 —
0705 심야 실측 4클래스의 단일 표면 봉합. 이후: 발사 표면(표 2·4) → 캐스팅·린트(표 3·5)
→ replay 다중화(표 11, T7 계열 엔진) → expand()(표 6·7).

## 착수 형태 (원안 기록)

expand() 슬라이스와 묶어 **인체공학 웨이브 1개**로: W-erg1(주소·오진 — 표 1) → W-erg2(발사
표면 — 표 2·4·8) → W-erg3(캐스팅·린트 — 표 3·5) → expand()(표 6·7). A+ 웨이브와 표면
겹침 대조 후 슬롯(W1 Contract Kernel과 1번이 인접). 각 슬라이스는 체커-동반(T9 원칙).

증거 한계: 매핑은 0705 실측 기반. 발주 시점 앵커 재확인. 처방 확정·우선순위는 사람 몫.
