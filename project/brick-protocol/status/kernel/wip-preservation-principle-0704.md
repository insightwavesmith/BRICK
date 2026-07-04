# 미완 처분 보존 원칙 선언 — 중단 시 WIP 보존 정지 클래스별 계약 (0704 — T7 S-d 수확)

Status: support evidence only. T7 S-d 수확(t7scsd-recovery-decl-0704a, 레인 초안을
COO가 렌더·커밋 — 원문: 해당 vessel work/step-outputs). source truth·성공 판정·품질
판정·Movement 권한 아님.

## principle

walk가 complete가 아닌 상태로 종료(HOLD/incomplete/중단)될 때, provider가 disposable 작업공간에 남긴 미완 파일 변경(WIP)은 disposal 전에 보존되어야 한다 — durable 증거(step-outputs/holds, output_root 외부)는 이미 항상 살아남지만, 작업공간 파일 바이트는 별도 보존 장치가 없으면 소실된다(anchor_wip_snapshot 독스트링 worktree_sandbox.py:230-235).

## two isolation modes

{'temp_dir_mode': "비-git/dirty/no-git/probe실패 폴백(driver.py:830-905, 912·922 진입). 반환 시 wip_anchor_ref='' 하드코딩(:898), worktree_disposed=False, base_sha=''/worktree_path=''(:893-894), finally temp_dir.cleanup()(:904-905)가 파일 변경 전부 폐기. 주석: 'a temp dir is not a repo: no commit, by design'(:897). 이 모드엔 non-complete WIP 앵커 경로가 전무.", 'worktree_mode': "정상 git repo. driver.py:988-1004 finally — commit_sha 없으면(비-complete) anchor_wip_snapshot으로 refs/brick/wip/<building>에 WIP 커밋-트리 앵커, reclaim_wip_anchor로 회수 후 dispose. 어떤 비-complete 프런티어든 균일 앵커(hold_reason별 분기 없음). anchor는 git status 비면 ''(보존물 없음) 반환(worktree_sandbox.py:244-245)."}

## temp dir judgment both sides

{'as_defect': "정지 시 보존 보장이 격리 모드에 따라 비대칭이다: worktree 중단은 파일 WIP 회수 가능, temp_dir 중단은 동일 상황에서 파일 WIP 소실. 구현 building이 temp_dir 모드에서 중간에 사망/HOLD되면 재개·감사용 파일 바이트가 사라진다. '미완 처분 보존 원칙'이 원칙이라면 모드 무관 최소 보존(예: temp_dir 트리를 durable 위치로 스냅샷)이 없는 것은 원칙 위반. goal-phases-consolidated-0702.md:306·110-111이 이를 '엔진 갭, 소형'으로 등재.", 'as_design_exception': "temp_dir 모드는 git이 없는 환경의 degraded 폴백이다. 앵커할 git object store/base_sha가 없으므로 WIP 커밋 앵커가 물리적으로 불가. 라이브 트리를 절대 쓰지 않는 격리 보장이 목적이고, 폐기는 그 격리의 귀결. durable 증거(evidence_root, output_root 외부)는 보존되므로 '처분 기록'은 남는다 — 소실되는 것은 파일 WIP뿐. 주석이 명시적으로 by-design.", 'decision_owner': '이 예외/결함 판정은 Smith/COO 몫 — 본 반환은 논거 양쪽만 제시하고 단정하지 않음(law).'}

## preservation matrix

{'columns': '정지 클래스 | 보존물 | 실측/코드 근거 | 비고', 'rows': [{'evidence': 'driver.py:979-987', 'note': '정상 완료 경로(본 계약과 무관)', 'preserved': 'commit_sandbox_output로 refs 커밋 + durable 증거', 'stop_class': 'worktree 모드, frontier=complete'}, {'evidence': 'driver.py:988-1004 + worktree_sandbox.py:224-276·279-287', 'note': '코드상 hold_reason별 분기 없이 균일 앵커; git status 비면 앵커 물리적으로 없음(보존물 0)', 'preserved': 'durable 증거(항상) + 파일 WIP → refs/brick/wip/<building> 앵커(회수 가능)', 'stop_class': 'worktree 모드, 비-complete(HOLD/incomplete/렌즈-정지/link_paused)'}, {'evidence': "driver.py:889-905 (wip_anchor_ref='' 하드코딩 + temp_dir.cleanup)", 'note': 'S-d 판정 대상; 격리 보장의 귀결 vs 원칙 위반 — Smith 게이트', 'preserved': 'durable 증거(evidence_root, 외부)만 — 파일 WIP는 폐기', 'stop_class': 'temp_dir 모드, 비-complete(모든 hold_reason)'}, {'evidence': 'driver.py:876-903·962-978, _record_fake_landing_hold(:1119)', 'note': 'repo-무수정 계약의 정상 홀드 — 보존할 파일 WIP가 없음이 정상', 'preserved': 'durable 증거 + (worktree면) 파일 WIP 앵커; no-diff이므로 앵커 보존물 대개 0', 'stop_class': 'fake-landing no-diff HOLD (worktree/temp_dir 공통)'}, {'evidence': 'goal-phases-consolidated-0702.md:110-111·306 (인용, 미재현)', 'note': '★불일치 신호: driver.py worktree finally는 hold_reason 무관 균일 앵커이므로 budget-HOLD만 미보존이라는 per-reason 차이는 내가 읽은 코드에 안 보임 → not_proven 참조. 격리 모드(temp_dir) 또는 미독 경로 소산 가능성. Smith/COO 판정 필요', 'preserved': "goal-phases 등재상 'WIP 앵커 미보존'(렌즈-정지는 보존)", 'stop_class': '증명-예산 HOLD (budget_exhaustion) — 0702/0704 실측 인용'}]}

## repair coordinates only

{'coord_1': 'temp_dir 비-complete 시 트리를 durable 위치(output_root 인접)로 tar/스냅샷하는 최소 보존 훅 위치 = driver.py:889-903 반환 직전 (또는 :904 finally cleanup 이전). ★엔진 Smith 게이트(driver.py는 walker 인접 핵심).', 'coord_2': "budget-HOLD vs 렌즈-정지 보존 차이의 실제 소산점 규명 = worktree_sandbox.anchor_wip_snapshot 진입 조건(:238-245 git status 비면 '') + budget-HOLD building의 격리 모드 확인. ★조사 선행(별도 발주), 본 계약 범위 밖.", 'coord_3': "'미완 처분 보존 원칙' 원칙문 착지 위치 = AGENTS.md 또는 status/kernel 선언 파일(COO 저작·커밋 몫).", 'note': '구현 금지 — 좌표만.'}

## 미판정 (레인 정직 선언)

temp_dir wip_anchor_ref='' 이 '설계 예외'인지 '결함'인지 — 판정 안 함(Smith/COO 몫). 수리 좌표는 §repair coordinates only 절 참조 — 구현은 엔진 Smith 게이트.
