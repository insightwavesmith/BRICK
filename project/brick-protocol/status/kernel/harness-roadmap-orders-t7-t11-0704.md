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
3순위: T6(홀드 자기서술 — T7-Sb 재현 결과 흡수 후) · T8-Sb(패킷 과잉주장 체커)
Smith 게이트(후행): T7 엔진 수리들
논의 대기(발주 금지): T10 전체 — 워크플로 표현력 이식, 감사가능성 경계 미확정(Smith 논의)
```

**0704 Smith 재정의 반영**: T8 = 신설 렌더러 ❌ → reporter 패킷 확장(출구는 기존 sink).
T9 = 이식성 문제 ❌ → 체커-동반 개발 원칙(크게 축소, T11 흡수 가능). T10 = 발주 금지,
워크플로 패리티 vs 감사가능성 경계 논의 필요.

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

## T10. 그래프 동적 표현력 — 선언 원칙 보존 확장

**🚧 발주 금지 — Smith 논의 필요(0704)**: 이 항목은 아직 발주하지 마라. Smith 방향
전환: 초안의 "정적 그래프에 동적 흉내 3단계(근사형→K-of-N→런타임)"가 소심하다.
Smith 판정 = **브릭 그래프 DSL을 Claude 워크플로 수준 표현력으로 끌어올린다**
(loop-until-dry, 예산-비례 팬, 데이터-의존 분기를 워크플로처럼 선언). 근거: 이번
하네싱 감사도 브릭이 아니라 워크플로로 돌았다(동적 팬을 브릭으로 못 그림). Smith 0703
메모리와 동일선 — "빌딩 그래프 = 워크플로 스크립트 동급 조합 언어".

**미결 설계 논점 (발주 전 Smith와 확정)**: 워크플로는 "코드로 돌아가는" 유연함이
GOAT의 이유인데, 브릭 정체성은 "선언+게이트+에비던스(감사가능성)"다. **워크플로
표현력을 가져오되 브릭의 감사가능성을 안 잃는 경계를 어디에 긋냐** — 자유로운 코드 실행
vs 선언적 감사가능성, 이 둘의 화해점이 T10의 핵심. 이게 박히기 전엔 슬라이스 발주 무효.

아래 원래 조사 내용은 참고용 실물 근거로만 보존(발주 설계 아님):


**실측/현재 기전**: 원시 부품 전부 CONFIRMED — 선언 그래프 위상(composition_graph_emit.py:553-587), edge 게이트(:1277-1356, 단 movement 필드가 항상 "forward" 고정이라 이진), reroute-budget 캐스케이드(:339-345). per-node coo-gate는 link/gate.py의 GATE_REGISTRY 파생(DECLARED_GATE_REFS/COO_GATE_REF, :30-42 — 상수 정의), stop 처분 실행은 walker_resume.py:568-631 `_paper_stop_adapter_error_hold`(`disposition_action="stop"`). (검증 정정: link/gate.py에는 "stop" 문자열 0건 — gate는 sufficiency만 기록, 처분 실행은 walker_resume 소관. 두 파일을 구분해 인용.) 부재 확인 — fan-in wait-any/K-of-N(grep 0), loop-until-dry(grep 0), 예산-비례 함대(branches가 정적 리스트, 실제 처리 :952-954 `raw_group.get("branches")`).

**근본 원인**: DSL 팬은 "저자가 미리 아는 병렬"만 표현, "엔진이 실행 중 알아내는 폭"은 불가. 엔진 로직 부재가 아니라 선언 표면 표현력 부재.

**슬라이스**:
- **S-a (근사형, 엔진 무수정, 즉시)**: candidate-survival-fanout 프리셋 — recon → 후보 N개(code-attack-qa 재사용) → closure fan-in. 후보별 implementation_gap이 독립 HOLD(node_reroute_budgets=0), COO가 가지마다 forward(생존)/stop(탈락) 개별 처분. **프리셋 YAML 초안 이미 작성됨**(설계 산출물 참조). 착지: brick/templates/presets/candidate-survival-fanout.md. 증명: cli build --preset 후 격리 실행, 후보 3개 중 1개만 gap 반환하는 픽스처로 1 HOLD·2 forward 관측 + --all. 종료선: 프리셋 + 실행 로그 + green.
  - **필수 proof_limits**: "가지 수는 발주시점 고정, 개방/폐쇄는 HOLD 후 처분 시점 — 런타임 팬 크기 변경 아님". 누락 시 과장 주장.
- **S-b (K-of-N 게이트)**: 어휘 등록(make-a-gate, link/spec.py GATE_REGISTRY) = 선언 비엔진. 디스패치 억제(walker_kernel.py _dispatch_ready_batch) = **엔진 Smith 게이트**.
- **S-c (런타임 데이터-의존 팬)**: 순수 엔진 — 런타임 노드 인스턴스화는 reroute "기존 노드만"(dynamic_walker.py:19-24)과 근본 상충. **Smith 게이트**, S-a/S-b로 갭 재확인 후에만.

**Smith 게이트**: S-b 소비 슬라이스, S-c 전체.

**함정**: S-a를 "진짜 조건부 개방"으로 과장 금지(사후 처분 흉내). S-b의 K-of-N 판정 근거를 GateFact가 계산할지 상류 반환 필드를 읽을지 축경계(Link=sufficiency만) design 선결.

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

**0704 독립 앵커 검증 정정 이력** (별도 sonnet 렌즈, 자기검증 금지): 초안의 앵커
6건이 "인접 함수로 줄번호가 밀린" 오류로 확인돼 정정 반영 — T8 3건(reporter.py:1600-1621
→ closure 특정은 onboard.py:2323-2329, closure .returned 읽는 코드 "0건"은 부분 반증:
onboard.py:2295-2320이 deliverable_crosscheck는 이미 읽음, building_map엔 closure 로직
0건), T10 2건(link/gate.py:30-42는 stop 코드 아니라 GATE_REGISTRY 상수 — stop은
walker_resume.py:568-631; branches 정적 리스트는 :952-954), T7 1건 뉘앙스(결함② 저작
경로엔 선-검증 존재, S-b는 resume 실행 경로 겨냥). T9·T11·부록은 전 항목 PASS.

증거 한계: 발주 준비 기획. source truth·성공 판정·품질 판정·Movement 권한 아님.
