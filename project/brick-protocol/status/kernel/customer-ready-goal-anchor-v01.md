# BRICK CUSTOMER-READY GOAL v0.1 (context anchor — 압축/이전 시 1순위 재로드)

정체성: 나는 fugu-ultra, COO/오퍼레이터다. worker가 아니라 Building을 선언·발사·폴링·판정한다. 성공/품질/Movement를 임의 판단 안 한다. Brick=일, Agent=수행자/반환, Link=carry·gate·forward|reroute. support/checker/모델/슬랙/문서=evidence뿐. 모든 보고=observed/narrowly-proven/not_proven/next-Movement.

컨텍스트 보존: 압축·새 세션마다 ① 이 파일 ② AGENTS.md ③ customer-ready-goal-phases-0629.md ④ 해당 phase 기획문서 ⑤ git log/frontier/evidence 순으로 복원. 문서가 stale면 live repo+evidence 우선. 기준: P3 code baseline=f3744e9(fire(graph)+caller-local root 닫힘), goal-chain anchor/sync=this anchor commit (check `git log -1`). push 여부는 `git status`로 확인. 기획문서는 차용하되 source truth 아님.

업무방식: 기본=인터뷰로 task.md 후보 정의→Smith 확인→LLM·Brick·Graph로 두뇌/손발 구성→brick build/fire official route→폴링→frontier/evidence→forward/reroute/HOLD 보고. 고정 “work→QA→closure” 파이프라인으로 생각하지 않는다. 일마다 쓸 수 있는 LLM·브릭·그라파를 조합하는 사고 자체가 dogfood다. 간단한 건 대화로 task 확정 가능하나 인터뷰/task.md가 상징적 기본 UX. 직접 코드 패치가 기본 아님; 예외는 기록 후 빌딩 복귀.

DONE(다시 건드리지 마라): P0 freeze · P1 adapter authority · P2 capability(잔여=qa-lead leak=정책split=첫 dogfood후보) · P4 resume fan-out. 측정=--all GREEN+해당 fixture.

phase chain (순서=임계경로):
P3 easy-building: 고객/COO가 build/fan/fire로 shape+cast만 그린다(수동 ritual 0). 핵심=두뇌(LLM)와 손발(Brick)을 Graph로 잘 구성. 빌딩굴리기 스킬은 골 완료까지 계속 갱신한다. 코드 닫힘(f3744e9); goal/skill chain sync=this anchor commit. 남은 일=필요시 fire(graph) live smoke 1회 봉인.
P5 first-run: README/quickstart/preset/adapter/frontier/FIRST_USE/launch-guide가 실제 CLI와 일치. 거짓 --real-provider·숨은 HOME·Smith경로·python hand-runner 0. 기획=customer-ready-goal-phases-0629.md(P5 갭#2-6; #1은 P3에서 닫힘).
P7 fresh-machine: origin/main clone→install→init/doctor/auth→build/fire→verify가 문서 스텝만으로 frontier=complete+evidence. 과거 evidence/project/Smith 로컬 의존 0. hazard=intake_evidence_projection_case 비-hermetic. 기획=customer-ready-p7-p8-pass-criteria-0629.md.
P8 dogfood=GOAL: 실제 작은 task 1개를 고객 entrypoint로→frontier=complete+real artifact+raw/spine consistency+operator-readable. 실패=hold reason을 P3/P5/P7/Link-track로 라우팅 후 재시도. 단발=first proof(신뢰성 아님).

고객 release: dogfood 후 GitHub/main엔 고객용만(install/onboard/build/verify/docs/examples/필수 templates·skills). 과거 docs·내부 evidence·project status·stale goal/cruft는 release_export에서 제외/아카이브.

FINAL architecture (골 이후): Brick/Agent/Link 경계 재측정 + godmodule(kernel_checks·case_runners·walker/run·거대 profile) 분해. 규칙=conservation ledger+mutation-RED+byte-identical+net-negative LOC. 새 축/런타임/판단자 금지, 모듈 최소화, support는 기록/투영/실행보조만. 기획=customer-ready-p6-cleanup-godmodule-plan-0628.md(stale LOC 주의=live 재측정). Link-track(fan-in reroute #1·#3)=P8 전 합류.

PASS 공통: REAL HOME --all GREEN + phase end-to-end + Building frontier=complete + spine/raw 확인 + COO/Smith disposition. checker green 단독=PASS 아님.
