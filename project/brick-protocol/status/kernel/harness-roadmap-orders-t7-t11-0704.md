# 하네싱 로드맵 T7~T11 — 전략 개선 발주 준비 문서 (0704)

T1~T6(harness-roadmap-orders-0704.md, 발주 품질·에이전트 검증 축)에 이은 전략
개선 5건 = 시스템으로서 브릭에 필요한 것. 5개 설계 에이전트가 실물 정독 후 설계,
정합 검사자 1개가 상호 충돌·T1~T6 중복을 대조(중복 0 확인). 각 항목은 COO
발주-준비 상태이며 0702~0704 실측·코드 실물에 앵커된다. 독립 렌즈 앵커 검증 완료.

**저자 = 조사자 세션(브릭 외부 메타인지 전문가). 실행 = 형제 COO 세션 몫**
(0704 Smith 확정: "넌 작업자가 아니라 조사자다. 작업은 형제세션이 한다").
이 문서는 발주 준비 산출물이며 source truth·성공 판정·품질 판정이 아니다.

## 공통 발주 규율 (T1~T6과 동일 — 상속)

- 모델: fable5 레인 금지. codex=구현·마감·code QA / claude sonnet(xhigh)=조사·축·증거 QA / gemini=저위험 review 렌즈만.
- 규범 계약(Deliverables·종료선·리터럴 프로브)은 work_statement 인라인. 참고문서는 커밋된 트리 경로로 source_facts(발사 전 test -f).
- reason_refs엔 스텝 주소·불투명 토큰만. file:line은 observed_evidence로.
- 레인 물리 불가능 수용기준은 "COO 게이트 항목"으로 분리. 기계 게이트 원하는 D는 proof_obligations로.
- Deliverables에 명시적 종료선(DONE). proof는 수신 렌즈 환경에서 실행가능한 것만.
- 엔진 불가침: `_run_dynamic_graph_walker`(support/operator/walker_kernel.py:970) 수정 금지. walker/support 핵심 수정 슬라이스는 "엔진 — Smith 게이트" 라벨 필수.

## 발주 순서 (정합 검사 산출)

```text
1순위(즉시, 엔진 무수정): T9-Sa(체커-동반 원칙 선언) · T7-Sa/Sb(복구 조사·순서교정)
2순위: T11-Sa(교훈 원장 파일) · T8-Sa(reporter 패킷에 결정필드 확장)
3순위: T6(홀드 자기서술 — T7-Sb 재현 결과 흡수 후) · T8-Sb(패킷 과잉주장 체커) · T10-S1/S3(순수함수·Link 선언 표면, 비엔진)
Smith 게이트(후행): T7 엔진 수리들 · T10-S2/S4(walker_resume 표면 — revision 읽기·확장 분기)
```

**0704 Smith 재정의 반영**: T8 = 신설 렌더러 ❌ → reporter 패킷 확장(출구는 기존 sink).
T9 = 이식성 문제 ❌ → 체커-동반 개발 원칙(크게 축소, T11 흡수 가능). T10 = 0704 저녁
Smith 3결정 확정(선언시점 결정권 설정 · Link 게이트 승인 · revision 개정) 반영 완료,
발주 가능 — S2·S4만 Smith 게이트.

---

## T7. 실패 복구 경로 — resume·홀드·WIP 4결함

**실측/현재 기전**:
- 결함① raise 예산 미반영: 처분의 budget_increment는 support가 읽어 budget_delta로 엔진에 넘긴다(walker_resume.py:265-272, ResumeSeed로 :343-359). 총량 반영은 walker_kernel.py 내부 — **미확인**.
- 결함② 처분 자기잠금: `_require_budget_exhaustion_raise`(walker_resume.py:365-425)는 두 경로에서 호출된다 — 저작 경로(onboard.py:3409)는 raw/link.jsonl append(:3461-3462) **이전**에 선-검증하나(양호), **resume 실행 경로**(walker_resume.py:175 → `_read_disposition_row`:137)는 **이미 저장된** disposition 행을 읽은 뒤 검증한다. 후자가 자기잠금 원인 — 오염 행이 원장에 남아 반복 재거부. S-b는 이 resume 실행 경로를 겨냥(저작 경로엔 이미 선-검증 존재).
- 결함③ 원장 불일치: pre-resume 대조 가드가 **이미 존재**(walker_resume.py:245-259 + walker_resume_seed.py:189-195). 두 원장이 다른 트랜잭션 경계(step-output 즉시쓰기 vs raw-return 걸음종료 일괄) — 스텝완료 직후·걸음종료 전 프로세스 사망 시 항상 불일치. 백로그 "미해결" 서술은 stale.
- 결함④ WIP 앵커: worktree 경로는 finally로 보존(driver.py:988-999) but temp_dir 격리 모드(driver.py:889-903)는 wip_anchor_ref="" 하드코딩, 구조적 미보존.

**근본 원인**: 4결함 모두 "실패/중단 시 무엇을 보존·검증하는가" 선언 부재. fail-closed는 다 구현됐으나 "막힌 후 정정 경로"가 없다.

**슬라이스**:
- **S-a (조사)**: ① 브리지 증명 — budget_increment=3 처분 → resume → node_reroute_budgets가 +3인가 재현 픽스처. rc=0(브리지 존재) 또는 rc=1(갭 확정 → S-a2 엔진 수리로 이관). 착지: status/kernel/resume-raise-budget-bridge-0705.md. 비엔진(읽기 재현). 종료선: 조사 문서 + rc 확정 기록.
- **S-b (수리, 비엔진)**: ② resume 실행 경로의 검증-후-저장 순서 문제 교정. 저작 경로(onboard.py:3409)엔 이미 선-검증이 있으니 — resume 진입(walker_resume.py:175) 시 오염 disposition 행이 원장에 남기 전에 걸러지도록, 저작 시점 선-검증을 강화하거나 오염 행 정리 경로를 추가. `_require_budget_exhaustion_raise`(옳은 로직)는 무변경 재사용. 착지: design이 저작 경로 강화 vs resume측 정리 중 확정. 증명: 오염 처분 시도 시 raw/link.jsonl 라인수 불변 + 사전거부. 종료선: 원장 불변 + green.
- **S-c (선언)**: ③ "거부 후 정정 경로" 문서 — hold_reason처럼 "이 불일치 발생 시 사람이 할 수 있는 것" 선언. 착지: status/kernel/resume-ledger-mismatch-recovery-0705.md. 비엔진. 종료선: 문서 + 기존 두 가드 file:line 정합 확인.
- **S-d (선언+확정)**: ④ "미완 처분 보존 원칙" 선언 + temp_dir 경로가 예외인지 결함인지 확정. 착지: status/kernel/wip-preservation-principle-0705.md. temp_dir 수리가 필요하면 driver.py(walker 인접) — **엔진 Smith 게이트**.

**Smith 게이트**: S-a2(budget_delta 총량 반영 수리, walker_kernel.py), S-d 수리(temp_dir WIP, driver.py).

**함정**: ③을 "미해결 백로그"로 오인해 가드를 재작업하면 무효 발주 — 발주문에 "가드 실존, 잔여는 정정경로 선언뿐" 명시. ②의 저작 경로가 support/link 어느 축 소유인지 design 선결(잘못 배치 시 support가 처분을 "판단"하는 축 침범).

---

## T8. 의사결정자 증거 투영 — 인간 게이트 처리량

**실측/현재 기전**: closure 구조화 필드(narrowly_proven·remaining_delta·deferred_smith_review_queue·deliverable_crosscheck)가 step-output.json .returned에 **실제로 채워진다**(실물: caserunners-c1-0703a closure step-output — narrowly_proven 7건·remaining_delta 4건·deferred_smith_review_queue 2건·deliverable_crosscheck 3건 파싱 확인). 읽기전용 투영 선례 존재(ledger_projection.py, progress_projection.py:12 "NO judgment vocabulary" docstring, reporter.py 슬랙 벨) — 대부분 "빌딩이 어디 있나(위치)"만 렌더한다. **부분 예외(0704 검증 정정)**: onboard.py:2295-2320 `_summary_latest_closure()`는 closure .returned에서 `deliverable_crosscheck`는 이미 읽어 요약에 편입한다. 그러나 `narrowly_proven`/`remaining_delta`/`deferred_smith_review_queue` 3필드를 읽는 코드는 여전히 0건 — 의사결정자용 통합 투영은 이 3필드에 대해 미존재.

**근본 원인**: 투영이 "위치"에서 멈추고 "내용"(3필드)으로 못 간다. closure step-output 특정 경로는 이미 있음 — onboard.py:2323-2329 `_summary_is_closure_packet`(`step_ref.endswith("-closure")`). (검증 정정: building_map.py에는 closure 특정 로직 0건, onboard.py에 있음.)

**⚠️ Smith 재정의(0704) — 신설 렌더러가 아니라 reporter 패킷 확장**: "결과를 어디에 띄우냐(슬랙/대시보드/md)"는 이미 reporter가 푼 문제다. reporter.py는 sink 팬아웃 구조를 이미 가짐 — report_sinks.py의 ADMITTED_SINK_REFS = {local-inbox, operator-wake-local, slack, dashboard}(report_sinks.py:67-68), reporter.py가 sink_refs 정책으로 어느 출구로 보낼지 결정(:258-265). 즉 T8의 진짜 갭은 "새 투영 파일 신설"이 아니라 **reporter 패킷이 담는 게 위치(current_brick_ref/frontier)뿐이고 closure 결정 내용(3필드)을 안 담는 것**. 출구는 기존 sink가 정한다.

**슬라이스 (재설계)**:
- **S-a (패킷 확장)**: reporter의 report packet 렌더(render_building_event_report_packet :375 / render_report_packet :630)에 closure 결정 필드를 추가 — narrowly_proven·remaining_delta·deferred_smith_review_queue(+deliverable_crosscheck 선례). onboard.py:2295-2320이 이미 deliverable_crosscheck를 읽는 그 경로를 reporter로 끌어와 재사용. 출구는 기존 sink_refs가 결정(신규 sink 불필요). progress_projection.py:12 "NO judgment vocabulary" 원칙 계승. 착지: support/operator/reporter.py(+report_sinks.py의 SINK_FORBIDDEN_PACKET_FIELDS 정합). 데이터 실존 → **엔진·스키마 무수정**. 증명: 실제 building 1개 패킷 렌더 → 3필드 포함 + dry-run sink 출력 리터럴. 종료선: 패킷에 결정필드 포함 + 판정어 0건 + 기존 sink 테스트 green.
- **S-b (체커)**: 패킷 과잉주장 방지 — reporter의 기존 validate_report_packet(:778)·SINK_FORBIDDEN_PACKET_FIELDS(report_sinks.py:98) 어휘 재사용. S-a 완료 후.

**Smith 게이트**: 없음(전 슬라이스 비엔진, reporter는 read-side 투영 계층).

**함정**: 신규 sink/신규 렌더러 파일 만들지 마라 — 출구는 이미 4개 있다(재제안 금지). T11(교훈 원장)과 저장구조 통합 유혹 — 데이터 소스가 다르다(T8=building 실시간 패킷, T11=사후 append). closure 스키마는 건드리지 않는다(읽기만).

---

## T9. 체커-동반 개발 원칙 (구 "이식성" — Smith 0704 재정의)

**⚠️ Smith 재정의(0704) — "이식성 문제"가 아니다**: 브릭은 로컬 설치해서 쓰는 도구고,
쓸 때 체커가 딸려온다. 즉 "고객 repo에서 체커가 안 돈다"는 애초에 문제가 아니라
**설계 의도**다 — 브릭을 쓰는 곳엔 항상 브릭 체커가 있다. 초안이 이걸 "기생/갭"으로
부정 프레이밍한 게 틀렸다. 진짜 통찰은 반대 방향: **새 기능을 만들 때 그 기능을
검사하는 체커를 같이 만들어 규칙을 닫는(못박는) 것** = 브릭이 "축 분리+에비던스"로
스스로를 지키는 방식. 따라서 T9는 "고객 이식 대비"가 아니라 **"체커-동반 개발"을
규율로 선언**하는 것.

**실측 (여전히 유효한 부분만)**:
- 체커는 물리적 repo-내장(check_profile.py:46 _REPO_ROOT 자기위치) — 이건 갭이 아니라 로컬 설치 도구의 정상.
- discipline은 매 dispatch 파일 재조립, 부재 시 하드크래시(agent_resources.py:290-293) — fail-closed 정상.
- source-template.md 8항목은 이미 계약 그 자체지만 "체커-동반 개발" 원칙이 선언된 표면 없음.

**근본 원인 (재정의)**: 브릭의 자기방어 방식("기능 만들 때 체커도 만든다")이 관행으로만
존재하고 규율로 선언된 표면이 없다. make-a-brick/make-a-gate 스킬이 개별 절차는 있으나,
"모든 신규 기능은 검사 체커를 동반해 닫는다"는 상위 원칙이 명문화 안 됨.

**슬라이스 (재설계)**:
- **S-a (원칙 선언)**: "체커-동반 개발" 규율 명문화 — 신규 기능/선언 표면을 추가할 때 그것을 게이트하는 체커(또는 mutation-RED 프로브)를 같이 랜딩한다는 원칙. 착지: AGENTS.md 또는 make-a-brick/make-a-gate 스킬의 상위 원칙 절. 비엔진. 종료선: 원칙 선언 + 기존 make-a-* 스킬과 정합.
- **S-b (선택)**: T3(선언-집행 패리티)·T11(교훈 원장)과 연동 — "집행자 없는 선언"(good_enough 같은 케이스)을 체커-동반 원칙 위반으로 자동 열거. T3/T11 랜딩 후.

**Smith 게이트**: 없음(전 슬라이스 비엔진 선언).

**함정**: 고객 repo 이식·P8 통과기준 재검토·"repo-무관 2분류" 초안 방향은 **폐기**(Smith
0704: 로컬 설치가 맞다). 온보드/verify 분리를 갭으로 재제안 금지(이미 존재). T9는 크게
축소됐고 T11(교훈 원장)에 흡수될 여지 있음 — 발주 전 T11과 통합 여부 판단.

---

## T10. 그래프 동적 표현력 — 홀드-후 신규 노드 편입 (Smith 3결정 반영, 발주 가능)

**Smith 방향 확정(0704 낮 — 재론 금지)**: "브릭은 바둑이다. 한 빌딩=한 판, 그 판 안에서
홀드 후 다음 수(신규 노드)를 둔다. **판을 새로 안 깐다.**" 팬인/아웃 그룹핑은 이미 가능
(multi-fan-in 실존, composition_graph_emit.py:264·689)이라 T10 밖. 진짜 T10 = 직렬/체인을
홀드-후 신규 노드 편입으로 넓히기. (구 초안의 근사형 프리셋/K-of-N/런타임 팬 3단계안은
이 방향 확정으로 폐기 — 재제안 금지.)

**Smith 3결정 확정(0704 저녁 — 발주 전제)**:
1. **결정권(편입 판단)**: 빌딩을 세울 때 Smith가 정한다 — 홀드에 휴먼게이트를 안 건
   빌딩은 COO 자체 판단, 휴먼게이트가 걸린 빌딩은 공동 판단. 즉 결정권 배분은 선언
   시점 설정이며 런타임 재량이 아니다.
2. **승인 주체**: 확장 plan 승인은 **Link 게이트**. Agent는 제안만 한다. 게이트
   행위자는 COO/human/자동판단(미래 로컬 LLM 등)으로 플러그블 — 전부 게이트의 일종.
3. **birth-certificate 개정**: 덮어쓰기 ❌ → **새 revision 파일**(원본 보존, 개정 역사
   전부 파일로). extends_plan_hash 계보 필드는 revision과 병행(지문+실물 둘 다 남긴다).

**실측/현재 기전 (0704 저녁 6레인 병렬 재조사 — 독립 sonnet 렌즈, 읽기 전용, 전부 실물 file:line)**:
- **walk 도중 plan 갱신 경로 전무 확정**: declared_plan/declared_bricks 쓰기류는
  ①발주 조립(compose_building — walker 계열에서 미임포트) ②resume의 예산 재부착
  (walker_resume.py:173·183 — node_reroute_budgets만, 위상 무변경) ③read-projection뿐.
  처분 4종 전부 기존 노드 집합 안: raise 가드(walker_resume.py:270 ValueError), reroute
  가드(:533-534 ValueError + _classify_reroute_target unresolvable→HOLD,
  walker_transition_concern.py:129), stop=building-boundary 종결(:584), forward는 별도
  경로 없음. T10은 순수 신규 여백이다.
- **진짜 갭 = 편입 정당성 증명 층 부재(핵심 발견 — 검증 렌즈 정정 반영)**: birth-certificate에
  위상(nodes/edges)을 바꾸는 코드 경로는 전무(개정 API 부재)하고, resume은 내용 무결성
  검사 없이 읽는다(walker_resume.py:925-951 — plan_shape=="graph"만 확인). 위상 해시
  자체는 이미 실존한다 — plan_hash(declaration_packets.py:403, _pure_declared_plan_copy
  정본의 canonical sha256; evidence-manifest용 :968 별도). **갭의 정확한 모양 3가지:
  ①기록된 plan_hash를 resume이 재계산·대조하는 코드 0건(파일을 통째 갈아치워도 미탐지)
  ②원본↔확장 계보 연결 필드(extends_plan_hash류) 부재 ③편입 승인 증거 표면 부재.**
  Smith 결정 ②③(게이트 승인 + revision + 해시 체인)이 정확히 이 세 빈자리의 처방이다.
- **가드 정합은 조건부 자동(직전 인계의 "자동 통과" 판정 정정)**: target-existence
  게이트들과 declared_bricks는 전부 "그 walk에 넘겨진 plan"(resume이면 birth-certificate,
  walker_resume.py:150→:937)에서 파생된다(walker_kernel.py:1047-1099). 따라서 **개정이
  먼저 랜딩되어 resume이 확장 plan을 읽으면 가드 무수정으로 신규 노드 자동 인식**,
  개정 없이 신규 노드를 처분 target으로 쓰면 명시 거부. **순서 제약: revision 랜딩 →
  신규 노드 참조 처분.** 이 순서를 발주 계약에 박아라.
- **replay 호환 확인(재작업 불필요)**: 완료 프론티어는 step_ref별 독립 카운터
  (walker_resume_seed.py:181-187) — 신규 step_ref는 expected=0이라 자연히 live 실행.
  이는 T10이 원하는 동작과 정확히 일치(신규 노드는 이력이 없으니 처음부터 실행). 두
  원장 대조 가드(walker_resume.py:1231-1253)도 기존 노드만 봐서 간섭 없음.
- **예산 통로**: budget_delta는 이중 잠금(hold_record 유래 + declared_plan 존재성
  재검증)이라 신규 키 주입 불가(walker_resume.py:264-272·519, 소비처 walker_kernel.py:1106은
  검증 우회 — 생성측이 유일 방어선) — **신규 노드 예산은 확장 plan(revision)의
  node_reroute_budgets에 실어야 한다.**
- **게이트/플래그 착지 표면**: GATE_REGISTRY 4행(GateRegistryRow 6필드: ref/concept_token/
  required_return_fields/placement/placement_order/disposition, link/spec.py:89-137),
  신설 행 등록 시 병렬 표면 4곳 동기화 필수(make-a-gate SKILL.md:42,
  check_gate_registry_single_source RULE1·2). 빌딩 단위 정책 플래그 선례 =
  transition_concern_adoption(composition_compose.py:751-752 → link/spec.py:252
  ADOPTION_LITERALS → walker_kernel.py:1934 소비) — 동형 패턴 사용 가능. 명명 시
  _BUILDING_PLAN_FORBIDDEN_KEYS(rule_runners.py:588 — movement/route 암시어) 회피.

**슬라이스 (3결정 반영 재설계)**:
- **S1 (확장 plan 조립 순수함수, 비엔진)**: 기존 plan + 신규 brick_steps/link_edges/
  execution_order/groups.member_refs를 **일관 병합**하는 순수함수 신설 — 넷 중 하나라도
  빠지면 plan_graph.py:237(execution_order 전수 일치)·:391(fan-in 정합)이 거부한다(의도된
  안전망, 재사용). 위상검사 _validate_graph_plan_topology(:323-394) 재사용 — 사이클 주입만
  거부, 리프 추가·fan-in 소스 추가는 통과. extends_plan_hash 계보 필드 부착(plan_hash는
  순수 함수라 새 해시 자동 생성). 종료선: 순수함수 + 병합 픽스처 green + 사이클 주입
  거부 확인 + member_refs 누락 시 거부 확인.
- **S2 (revision 표면 + 동반 체커 — 엔진 인접, Smith 게이트)**: ①revision 쓰기 API
  (declaration_packets.py — 파일 명명 규칙은 design 확정, 후보: declared-building-plan.rev-N.json)
  ②walker_resume.py:937 읽기 경로를 최신-revision-aware로(단일 파일명 하드코딩 해제)
  ③**동반 체커 신설(T9 체커-동반 원칙 적용)**: revision 체인 검증 — 추가-only diff(기존
  노드/엣지 변경·삭제 거부), extends_plan_hash 정합, 승인 증거(게이트 발화 기록) 없는
  revision 거부. 이 체커가 위 "편입 정당성 증명 층 부재" 갭의 직접 처방이다.
- **S3 (게이트+결정권 표면, Link 선언, 비엔진)**: link-gate:expansion-approval 등록
  (make-a-gate 절차, 병렬 표면 4곳 동기화). 결정권(결정 1)의 기계 표현은 design 선결
  2안 — (기본 후보) 기존 휴먼게이트 선언 여부에서 파생(신규 표면 최소: 휴먼게이트 걸린
  빌딩=공동, 아니면 COO 단독) vs (대안) 명시 플래그(composition_compose.py:655 형제 키
  + link/spec.py 어휘 선언, transition_concern_adoption 동형). 추가 design 선결: 신설
  게이트의 placement/disposition이 기존 리터럴(qa/final_transition/none ·
  auto/plain/human/coo) 안에 드는지, 확장 plan(그래프 조각)을 required_return_fields로
  어떻게 나르는지.
- **S4 (resume 확장 분기 — 엔진 인접, Smith 게이트)**: walker_resume.py 오케스트레이션에
  확장-plan-resume 분기 — 최신 revision 읽기 → S1 병합 결과로 walk 재진입. 엔진 핵심
  루프(walker_kernel.py:970)·정지 알고리즘(:2070 카운터 if) 무수정 유지. 무한루프 방지는
  (A)노드 고정 + (B)예산 유한의 결합이므로, 확장 후에도 "그 시점 노드 집합 유한 + 예산
  유한"이 유지된다는 서술을 dynamic_walker.py docstring(:23-25)에 개정 반영.

**Smith 게이트**: S2·S4(walker_resume/recording 표면 수정). S1·S3는 비엔진.

**함정**:
- **순서 제약 위반 금지**: revision 랜딩 전에 신규 노드를 처분 target으로 쓰는 계약을
  만들지 마라 — 가드가 명시 거부한다(위 실측). 편입 = "게이트 승인 → revision 랜딩 →
  처분/재개" 순서로만.
- **fan-in 조기완료 리스크(정적 추론, 런타임 미검증)**: 기존 fan-in 그룹에 신규 소스
  추가 시 groups.member_refs 미갱신이면 wait-all이 신규 소스를 안 기다리고 조기 완료할
  위험 — S1 병합 규칙에 member_refs 포함(위 종료선) + 런타임 wait-all 행동 검증을 S4
  D항목으로 배정.
- **재실체화 덮어쓰기 함정(검증 렌즈 발견)**: `_write_declaration_work_evidence`엔
  write-once 가드가 없다 — 매 walk 진입(정방향·resume 공통, walker_kernel.py:1036 경유)마다
  무조건 write_text 덮어쓰기이며, 오늘 내용이 안 변하는 건 resume이 같은 plan을
  되돌려주기 때문일 뿐(walker_resume.py:150·165-183). S4가 확장 plan으로 재진입하면 이
  경로가 **원본 birth-certificate를 확장본으로 덮어쓸 수 있다** — S2 계약에 "원본/revision
  파일 분리 + 재실체화 시 원본 보존" 요구를 명시하라(Smith 결정 ③의 집행 지점).
- **budget_delta 재사용 금지**(위 실측 — 이중 잠금, 열려고 하지 마라).
- **잔여 미확인(발주 내 조사 D 또는 후속)**: walker_fan_in.py cohort 함수(:270 이후)
  전수 정독, walk 종료 후 recording 계열의 declared-building-plan.json 재직렬화 여부,
  _validate_gate_sequence_action 본문(plan_validation.py)의 추가 거부 조건.

---

## T11. 교훈의 구조화 축적 — 실측 원장

**실측/현재 기전**: 교훈이 3곳 분산 — kernel 산문 부검(postmortem-*.md), 각인 커밋 메시지(bbfdc492 git log만), 골플랜 부록(harness-roadmap-orders-0704.md:213-218 스키마 없는 자유목록). kernel-archive-classification-0702.md는 파일 이동 원장이라 **직교**(대체 아님). §3.0 4갈래 질문은 입력 틀로 재사용.

**근본 원인**: 사건(부검) → 처방(랜딩 diff) → 등재(골플랜)가 3개 자유형 매체를 거치며 매번 수작업 재서술 → 손번역 지점에서 Gap 누락(0704 실사례). 엔진 문제 아님(전 슬라이스 선언-먼저).

**슬라이스**:
- **S-a (스키마+파일)**: lessons-ledger.yaml 신설, 7필드(id / date / axis[brick|agent|link|engine|cross] / prescription / landing_commit / pin_location / unresolved). 처방 1건=1행(복수축은 같은 id 재사용). 착지: status/kernel/lessons-ledger.yaml. 증명: `python3 -c "import yaml; assert isinstance(yaml.safe_load(open(...)), list)"` rc=0. 종료선: 스키마 문서 + bbfdc492 사건 실제 1행 + rc=0.
- **S-b (쓰기 규율)**: "처방 랜딩 커밋에 원장 1행 동반" 관행을 brick-task-author SKILL.md §3.0 말미에 선언(게이트는 차후). 증명: grep rc=0.
- **S-c (소비 포인터)**: goal-phases 상단에 "교훈 계보: lessons-ledger.yaml" 1줄(표 승격 아님).

**Smith 게이트**: 없음.

**함정**: 기존 ledger_projection.py("orchestration-ledger")와 이름 충돌 — 발주문에 "T3=금지어 패리티 원장, T11=처방 계보 원장, ledger_projection=오케스트레이션 상태 뷰" 3자 구분 명시. 소급 등재(기존 kernel 산문 수십 건)는 별도 발주로 분리.

---

## 부록 — 관리 항목

- **T1~T6 부록 stale 처리 필요**: harness-roadmap-orders-0704.md:213-218 "골플랜 등재 대기"(Gap 1·3)는 GP-H 편입(goal-phases-consolidated-0702.md, 커밋 80cea30d)으로 이미 처분 완료. 그 부록에 "편입 완료, 이력 보존용" 각주 추가 권고 — 안 하면 이 stale 목록을 근거로 무효 발주 위험.
- **Gap 1 랜딩 확인**: good_enough 집행 동기화는 형제 세션이 랜딩 완료(return_fact.py:58, merge 529c76d0).

## 독립 앵커 검증

이 문서의 file:line 앵커·"이미 존재" 판정·"부재 확인"은 0704 설계조사(5 병렬 설계 +
정합 검사)의 실물 정독 산출이며, 정합 검사자가 T1~T6과의 중복 0·상호 충돌 해소를
확인했다. 발주 시점에 각 앵커를 재확인하라(코드는 형제 세션이 계속 변경 중).

**0704 저녁 T10 전면 재작성 검증**: T10 섹션은 Smith 3결정 확정 직후 전면 재작성됐고,
앵커·기전 서술은 6레인 병렬 재조사(독립 sonnet 렌즈, 읽기 전용 — walk중 갱신경로 /
예산통로 / 완료이력·replay / invariant 가드 / 기존 앵커 12종 / 게이트·선언 표면)의 실물
정독 산출이다. 기존 앵커 12종 전부 HOLDS 재확인. 직전 인계(handoff-0704-t10-dynamic-graph.md)
의 "가드 자동 통과" 판정은 "조건부 자동(revision 선행 랜딩 시)"으로 정정됨.

**0704 독립 앵커 검증 정정 이력** (별도 sonnet 렌즈, 자기검증 금지): 초안의 앵커
6건이 "인접 함수로 줄번호가 밀린" 오류로 확인돼 정정 반영 — T8 3건(reporter.py:1600-1621
→ closure 특정은 onboard.py:2323-2329, closure .returned 읽는 코드 "0건"은 부분 반증:
onboard.py:2295-2320이 deliverable_crosscheck는 이미 읽음, building_map엔 closure 로직
0건), T10 2건(link/gate.py:30-42는 stop 코드 아니라 GATE_REGISTRY 상수 — stop은
walker_resume.py:568-631; branches 관련 1건은 아래 재정정 참조), T7 1건 뉘앙스(결함②
저작 경로엔 선-검증 존재, S-b는 resume 실행 경로 겨냥). T9·T11·부록은 전 항목 PASS.
**0704 저녁 재정정**: 위 T10 2건은 구 T10 섹션(전면 재작성으로 대체) 대상이었고, 그중
"branches 정적 리스트는 :952-954" 서술은 그 자체가 오기로 재판정 —
walker_resume.py:952-954는 step_ref_by_brick_from_declared 시그니처이고, branches 처리는
composition_graph_emit.py:953-954(동적 파싱이라 "정적 리스트" 규정도 부정확)다.

증거 한계: 발주 준비 기획. source truth·성공 판정·품질 판정·Movement 권한 아님.
