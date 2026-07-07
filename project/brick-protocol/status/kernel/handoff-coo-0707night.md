# COO 핸드오프 — 0707 심야 (앱 업데이트 재시작용)

> 진입 정본. 이 문서 + 원장(walk-results-adopted-0707.md §M~§R)이 세션 상태의 단일 출처.
> 재시작 후 이 파일부터 읽고 "미결 3건"을 순서대로 이어라.

## 0. 지금 상태 한 줄
오늘 밤 캐스팅 대개편·클린배포·프리셋티어를 처리했고, **끝에 대표님이 import 이중신원 근본해결(개헌급 수준3)을 판정**했다. 앱 업데이트로 재시작. origin은 깨끗(격차 0), 도는 프로세스 0.

## 1. origin 상태 (실측, 6aa3f71ec 시점)
- 로컬-origin 격차 **0** — 어정쩡한 미push 없음.
- 오늘 입고 완료: 캐스팅 상수(M7r)·별칭수리·앵커링방어·**클린배포-단일(c010f49df)**·원장 §M~§R.
- **미입고 1건**: preset-tier-single (WIP 앵커 `3e502f843`, 게이트 GREEN, **착지 스윕 RED로 push 막힘**).

## 2. 미결 3건 (재시작 후 순서대로)

### ① 프리셋티어 재착지 [즉시, 별건 — import 무관]
- 상태: 게이트 GREEN(fail-closed 변이 2종 RED 확인), 로컬 머지했으나 **라이브 스윕 rc=1로 push 차단**(정상 안전장치 작동 → 로컬·origin 둘 다 깨끗).
- 스윕 RED 원인 **추정**: 환경 모드(.DS_Store 크래시 / gemini CLI). 개별 프로파일(provider_preflight 등)은 전부 passed — **이중신원과 무관**. 부검으로 확정할 것.
- 회수: WIP `3e502f843`에서 재수확 → 스윕 RED 원인 격리(detached 워크트리에서 재현, .DS_Store 제거 후 재측정) → 재착지.
- 착지 메시지: `/private/tmp/brick-coo-tasks-0707/land-pt-single-msg.txt`, 변이 스펙: `mutspec-pt-single.py`.

### ② 개헌 설계 — import 구조 통일 (수준3) [Smith 동행, 설계 먼저]
- 판정: 원장 §R. Smith "땜빵 하지 말자. import가 문제면 나중에 또 문제 된다" → 앨리어싱(수준1) 거부, **물리구조=패키지구조 통일**. 정당화 = 리포 클론 배포 + 다른 고객 소비.
- 실측 재현: `PYTHONPATH=support/import_identity:. python3 -c "import link.movement as a; import brick_protocol.link.movement as b; print(a.__file__==b.__file__, a is b)"` → True, **False**(이중신원 확정).
- **바로 시공 금지** — 축 폴더(brick/agent/link)를 brick_protocol/ 밑으로 이동 + 셔임·finder·allowlist·이중sys.path 철거는 개헌급. 마이그레이션 자체가 새 "for now" 다리를 낳는 게 최대 위험(리포 4세대 이사 연혁이 증거).
- 처분: **deep-design(fable5) 발주로 마이그레이션 설계 먼저** — 경계 매니페스트·철거 순서·경로체커 26,800 이동·헌법/AGENTS 개정안·롤백선·partition_plan. 설계 반환 후 Smith에게 "이 방향?" 판독 받고 시공.
- 교차확인(다른 세션 GPT-5.5 검수): 이중신원 외 4건 동시 실증 — brick→agent private import, Agent 어휘 support 상주, Rule13 체커 부재, no_axis_judgment 협소커버. + support materialization 클러스터(native_dispatch:284·plan_rendering:217-218·composition_route_policy).

### ③ 고객 도착 전 소형 필수 [개헌과 분리, COO 발주 가능 — Smith 발주여부 확인]
- **게이트 .DS_Store 수리**: macOS 고객 클론 직후 .DS_Store 생성 → `--all` 크래시 → 뒤 프로파일 무실행(안전망 부분 커버). .DS_Store 격리 + 프로파일 예외 격리 + blocked(환경결핍)/red(소스) 구분 기록.
- **Rule 13 체커 신설**: durable evidence에 절대경로·사용자명 금지가 헌법인데 강제 장치 없음. 고객 환경이면 고객 경로·식별자가 증거에 박혀 유출. 기계 차단 필요.
- 이 둘은 import 문제와 무관하게 고객 첫 실행(클론→게이트→증거생성)에서 필요 → ②(개헌)보다 먼저 착지 가능.

## 3. 오늘 확립된 규율 (메모리 반영 완료 — 재확인용)
- **캐스팅 최종형**: 기획=fable5 xhigh / 시공·QA=opus-4.8 xhigh(복잡 work만 푸구) / code QA·closure=codex / review=gemini. **fable5는 기획 전용**(QA·work 금지). 원장 §M.
- **팬아웃(공유 워크트리 work 3갈래) 금지 → 단일 선형**: work@푸구 → code-attack-qa@claude(opus-4.8) → closure@codex. 팬아웃은 라우트 무한반복(갈래 겹침·워크트리 격리 부재). 홀드 산물은 cherry-pick -n 승계 base. 메모리 brick-coo-operating-rules 등재.
- **설계 끝났으면 시공에 design 노드 넣지 마라** (관성 부착 금지).
- **발사 겹침 금지**: 발사 후 declared-plan 생성+첫 레인 개시(에코3) 확인 뒤 다음 발사.
- **자기보고 불신 + 실측 우선**: 오늘 여러 번 "확인 전에 말해서 번복" 실수. 결론 전에 실측 완료. (모델 오인·슬랙 멈춤·겹침 착시 등)
- **3축 코드 봉인 확인**: QA는 Movement 채택 경로 물리적 부재(driver.py:98), transition_concern 스키마에 귀속 필드 없음 → QA는 "누구 잘못" 못 씀.

## 4. 도구·경로
- brew·env: `set -a; source ~/.brick/report.env; set +a` (벨+대시보드).
- 발사: `PYTHONPATH=support/import_identity:. python3 -m brick_protocol.support.operator.cli build --graph-decl <decl>` (설치된 `brick` 셰임은 낡아 --graph-decl 모름).
- 게이트: `support/onboarding/coo_gate_runner.sh <id> - "<profile>" <mutspec>` / 착지 `--land <sha> <msgfile>`.
- decl/mutspec/land-msg: `/private/tmp/brick-coo-tasks-0707/` (42 decl 보존).
- cwd 리셋 트랩: 항상 `cd /Users/smith/projects/BRICK` 또는 `git -C` 명시. 착지 유령(로컬 머지 후 push 끊김) 주의 — origin 포함 실측으로 확인.

## 5. 배포 컨텍스트 (Smith 확정)
- 고객 소비 = **리포 클론** 우선(pip wheel 아님).
- 클린 배포 repo = `insightwavesmith/BRICK---One-for-All`(오늘 생성, 빈 repo). 클린배포 시공이 install.sh·문서에 `{OWNER}/BRICK-dist` 플레이스홀더로 박음 — **배포 시점에 실제값 자동주입**(no-smith-residue 체커가 실명 하드코딩 차단하므로 소스 하드코딩 금지). "새 repo에 제품만 올리기"는 클린배포 착지 후 다음 단계(Smith "올려" 대기).
