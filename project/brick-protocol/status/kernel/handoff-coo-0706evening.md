# COO 인수인계 — 0706 저녁 세션 마감

세션 종료 사유: Smith 지시(세션 이전 준비). **모델이 06:36:12Z(KST 15:36)에 fable5 → opus-4-8로 자동 폴백됨** — 아래 §모델 전환 참조. 산출 손실 0.

## 진입 정본 (새 세션이 먼저 읽을 것, 이 순서)
1. 이 문서 (§즉시 첫 작업 · §트랙 A 발사대기 · §모델 전환)
2. project/brick-protocol/status/kernel/goal-phases-consolidated-0702.md §마스터 잔여 큐 + §잔여 페이즈 스냅샷 (P0~P5, 처분 단일소스)
3. 메모리: brick-coo-operating-rules (특히 --land/--ship 규율, 병행 세션 수칙)

## git 상태 (마감 시점)
로컬 HEAD = origin/main = **b94a77b3** (SHIP 완료 — 라이브 스윕 rc=0 47프로파일, push 봉인됨 16:xx KST). **미push 0건** — 오늘 밤 17커밋 전량 원격 봉인 완료. firehunk가 벽시계 flake를 제거하니 스윕이 깨끗이 통과.
이 핸드오프 문서 커밋만 미push일 수 있음(아래 참조) — 새 세션 첫 작업 = `--ship`으로 이 문서 push 확인.
**머지·push 수동 금지 — --land(harvest 머지)/--ship(이미-main 커밋) 전용.**

## 미push 17커밋 요약 (오늘 밤 랜딩분, 로컬 main에 안착·push만 대기)
- **R3 (ccb73b44)** 팬 사망 감지 — Case 9 무유서 동결 봉합
- **R5R8 (e4cf700d)** 부재-주장 도메인 라벨 기계 강제 — 1차 VACUOUS 반증(변이 2종 RED)
- **R1 (6ae9f3f4)** repo 정체성 가드 2모드(소스/설치) — wheel 즉사 수리
- **r3margin (2eb79b40)** R3 데드라인 여유 마진 + 병렬 자식별 예산
- **firehunk (b94a77b3)** ★중요★ r3margin이 남긴 벽시계 상한(elapsed>=1.85) 제거→증거-형태 판정. **이게 오늘 밤 push를 5회+ 막은 근본원인**(머지된 main이 부하 0에서도 자기 스윕에 RED). 변이 RED-confirmed, --all 47 green.
- **fugu451obit (d25b89ce)** 푸구 451 유서 — content_policy 분류 + stdout JSONL 발췌 + 걷는-vessel full 유서 + 문서 정정
- **러너 --land/--ship 교정, 골문서 갱신, 인체공학 표 19** 등

## 즉시 첫 작업
1. `--ship`으로 이 핸드오프 문서 커밋 push 확인 (오늘 밤 17커밋은 이미 봉인됨)
2. **트랙 A 3빌딩 + cpath 병렬 발주** (§트랙 A) — Smith 지시 "CPU 여유, 병렬로 달려라"

## 트랙 A — 발사 대기 (decl 작성·검증 완료, push 후 즉시 발사)
Smith 지시: "CPU 여유 많으니 병렬로 달려라." walker 안 건드리는 트랙은 전부 병렬.
**모두 사전검증 통과(assemble_graph_declaration OK). action=forward 이미 박음.**
발사 = `cd /Users/smith/projects/BRICK && set -a && source ~/.brick/report.env && set +a && .venv/bin/brick build --non-interactive --json --repo /Users/smith/projects/BRICK --graph-decl <decl> --output-root /Users/smith/.brick/project/brick-protocol/buildings`
**주의(0706 실측): output-root는 반드시 ~/.brick (repo-안이면 proposed-building-graph.json이 path-shape 체커와 충돌 = graphdecl-fix가 고칠 결함①). 발사 후 vessel 워크트리 HEAD가 현행 main인지 조기검증(표16).**

- **/private/tmp/r9-modellane-0706e-decl.json** — R9 모델-레인 규율 선언을 0705/0706 실정책과 정합 (agent/disciplines·objects·checkers). 결함 = 선언이 0702 고정('fable5 never lane'), 실정책은 design-lead fable5 기본·code-attack-qa/closure 위험비례 승격·푸구 work 티어로 진화.
- **/private/tmp/graphdecl-fix-0706e-decl.json** — 발주-표면 결함 2종 (support/operator·checkers·connection). ①proposed-building-graph.json이 building 루트에 남아 path-shape 체커(work/capture/raw/evidence만 허용)와 충돌 = 오늘 밤 3회 vessel 주차. ②model_ref 생략 시 model:default 하드주입이 codex-fugu-local 즉사(어댑터 default 상속이 옳음). 시공지점 = assembly.py:1402, agent_resources model 해석.
- **/private/tmp/fugupacket-0706e-decl.json** — ★푸구 실사용 개방★ sakana wire packet 재성형(A안). 시공지점 = **support/connection/agent_resources.py:627-640 (_text_resources)**의 리소스 행 `"path": path.relative_to(repo)` — sakana 라우팅일 때만 역할-프롬프트 path 라벨 제거/불투명화, 로컬 매핑 보존, 비-sakana byte-identical. **D3 검증선 = /private/tmp/fugu-failing-prompt.json(19KB 실패 packet)이 재성형 후 sakana 통과** (하네스 /private/tmp/fugu-bisect.sh). attack-QA에 "자격증명 verbatim 인용 금지" 인라인(fugu451obit QA가 그걸로 죽어서 예방).

## cpath 미러 수술 (⑤, walker 트랙 — 트랙 A와 병렬 발사 가능)
골문서 727행 정본. gate-sequence 경로 완전 미러 + concern-path 5사이트 loud-거부(최소 슬라이스). Smith 기판정 = COO-직접('ex walker', 픽스처 게이트 기랜딩). R3 랜딩으로 선행 충족. **⑤⑥⑦(cpath→R2→자기잠금)끼리만 walker_kernel 충돌로 랜딩 순서 직렬** — 걷기는 병렬 가능, 랜딩만 순차. decl 미작성(다음 세션이 작성).

## 푸구 근본원인 정정 (오늘 저녁 확정 — 인계 정본 갱신)
0706 오후 인계문의 "도구 불일치(image_generation)" 진단은 **부분 오판**이었다. 그 수리는 이미 0624(e4466b2b)에 랜딩돼 있었고, 실사인 = **Sakana가 HTTP 451(content policy)로 발주 packet 차단**(서버측). 어댑터 스택은 green(작은 pong 실반환). 방아쇠 = 역할-프롬프트 파일 경로 의미(프로브 9발 확정). → fugupacket 빌딩이 회피. 슬롯 되돌리기·Sakana 문의는 Smith가 packet 재성형 결과 후 재론으로 보류.

## 잔여 페이즈 (골문서 §잔여 페이즈 스냅샷과 동기 — 두 트랙 병렬)
- **트랙 A (walker 무접촉, 병렬)**: ② fugupacket · ③ (attack-QA는 fugupacket QA에 흡수) · ④ P3(R9·graphdecl-fix·Case 8 정찰) · ⑧ 그래프 초안기#15+build()통일#12(대형, R웨이브 후)
- **트랙 B (walker_kernel, 랜딩 순차)**: ⑤ cpath → ⑥ R2 carry헬퍼 → ⑦ 자기잠금 가족②
- **저우선**: T10 fresh 0705c
- **Case 8 정찰**: 착지-레코드 읽기전용 정찰(P3 병렬). **graph-decl 결함 2종은 graphdecl-fix로 이미 트랙 A 발사대기**.

## Smith 결정 대기 = 0건
wheel A/B = 이미 0706 오전 위임 판정 B 채택·랜딩(낡은 행이 오보 유발했던 것, 정정됨). 푸구 계정측 = packet 재성형 결과 후 재론.

## 모델 전환 (Smith 지시로 조사)
- **전환 시각: 2026-07-06T06:36:12Z (KST 15:36:12)**. 이전 = claude-fable-5(04:57Z부터), 이후 = **claude-opus-4-8**.
- **원인: 하네스 자동 모델 폴백**. 전환 직전 이벤트(06:36:05Z)는 평범한 tool_result(fugu451obit 게이트 판독 중 Bash 결과)와 task_reminder attachment 뿐 — 사용자 /model 명령도, 콘텐츠 파손도 아님. fable5 부하/용량 조건에서 하네스가 자동으로 opus-4-8로 내림.
- **함의**: 06:36Z 이후 응답은 opus-4-8 산출. 세션-말 도구문법 파손 클래스(0705/0706오후 반복)와 다름 — 이번엔 파손 없이 폴백만. 다음 세션은 원하는 모델을 명시 확인 후 시작 권장(Smith가 /model로 fable5 재지정 가능).
- (16:xx경 Smith가 /model claude-fable-5 재지정 시도 로그 있음 — 세션 로그상 opus 상태에서 재지정 명령 관측. 새 세션 시작 시 실효 모델 재확인 필요.)

## 콘솔 Artifact
claude.ai/code/artifact/b7c11b80-**** (전문 URL은 메모리 brick-session-0706afternoon-closeout). 상태 바뀔 때 재배포(favicon 🧱, url 파라미터로 같은 주소).

## 각인
- 머지·push 수동 금지 → --land/--ship 전용. already-on-main은 --ship, harvest는 --land.
- 게이트: 포커스 green + 변이 RED + 격리 --all. WIP 앵커(refs/brick/wip/<id>)에서 harvest, 게이트 워크트리는 현행 main에 머지(stale-base 착시 주의 — merge-base 기준으로 diff 읽기).
- 완주 vessel이 repo-안 output-root면 path-shape 스윕 RED → 주차(/private/tmp/brick-parked-vessels-0706e). graphdecl-fix가 근본수리.
- CLI 발주 = repo 자신 .venv/bin/brick + --repo 명시 + graph-decl에 action=forward.
