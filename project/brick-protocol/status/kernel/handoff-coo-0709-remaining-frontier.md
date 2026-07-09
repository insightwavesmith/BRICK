# 핸드오프 — COO 0709 Remaining-Frontier GOAL

작성: 2026-07-09 KST. 이전 세션이 `course` 생성 폭주(Claude 결함)로 중단 → 새 세션 진입정본.
진입 즉시 이 문서 하나로 맥락 복원. Proof limit: support evidence only.

## 지금 어디까지 왔나 (한 줄)

골 03(남은 7 프론티어) 활성 · W1 #1 authoring 구현 진행 중 · **W1a 구현 빌딩이 라이브로 돌고 있음** · 방지책 설계 완료(발주 대기) · 발주서=authoring 규율 항구화 대기.

## 골 상태

```text
활성 골: project/brick-protocol/status/kernel/GOAL/03-remaining-frontier-goal-0709.md (Stop hook 걸림, paused 아님)
부모: 02-unified §11 parent closure의 remaining_not_proven 7항목
HEAD == origin/main == 71c4ddd56, tracked clean
```

7 프론티어 / 4 물결: W1(#1 authoring +#3 cleanup) → W2(#5·#6 UX) → W3(#4 vessel·#2 RouteV2, human gate) → W4(#7 릴리스).

## 진행 완료 (커밋 근거)

```text
515596515  골 03 개시 (7항목, W1-W4)
71c4ddd56  W1 설계리뷰 + G2 게이트 = Candidate B 확정(Smith 승인)
```

W1 설계리뷰: `authoring-w1-design-review-0709.md`. G2 = "C/D 구조가 confirmed-request를 통과할 경로" → **Candidate B(선언 structure_plan 필드) 채택.** cap 정책 = N 파라미터 + fan-out 실행 직전 held_for_coo_review hold + COO가 실행시점 N 확정.

## 지금 라이브로 도는 것 ★★★

```text
W1a 구현 빌딩: buildings/w1a-structure-plan-schema-0709
  발사 = 정식 CLI: brick build --preset building-chain-preset:design-build-parallel --real-provider --timeout 3600
  워크트리: ~/.brick/worktrees/w1a-structure-plan-schema-0709 (detached 71c4ddd56, 격리)
  진행: design✓ work✓(attempt-2) code-attack-qa✓ axis-attack-qa✓ closure — running 41min+
  발주서: scratchpad/w1a-structure-plan-schema-task.md (COO 수동작성 — 부트스트랩)
  스코프: building_call.py(structure_plan optional 수용+lowering) + support/checkers/(fan-out 불변식 checker) + 하위호환(structure_plan 없으면 기존 building_case→chain_preset_ref 그대로)
```

**완주 시 게이트 방법(자기검증 금지):** codex/claude green 안 믿음 → clean detached worktree에서 `check_profile.py --all` RC0 + deliverable(D1~D3) 번호별 전수 대조 + 변이 RED 직접 확인 → 별도 commit/push → origin==HEAD 외부 재확인.
**홀드/미완 시:** `resume` 또는 재발주(0708 부검: proposal-approval 최초발사 미완=작업물 소멸, 워크트리 실존부터 확인).

## 다음 (W1a 후)

```text
W1b: authoring STEP3 방출 + 스킬 노출 + cap-hold enforcement
     → building-call-authoring 프리셋으로 발주서 뽑아 검토 후 태운다 (아래 규율)
#3 cleanup-10e (소형, W1 병렬 가능)
```

## Smith 핵심 교정 (이번 세션, 반드시 준수)

```text
1. 정식 루트만: 구현은 정식 CLI(brick build --preset)로 태운다. python 런처 스크립트 금지.
   (이번 세션 위반: launch_w1a.py 짰다가 Smith 교정, 폐기함)
2. COO는 검토자다 실무자 아님: 안쉬운 발주는 building-call-authoring 프리셋을 태워
   발주서(scope/structure=그래프/per_brick_intensity=캐스팅/agent_candidates)를 뽑고,
   COO는 3축(Brick계약/Agent캐스팅/Link이동)·그래프·스코프로 재검토 후 엔진에 태우기만.
   (이번 세션 위반: architecture-plan 빌딩=의견서를 발주서로 착각→손으로 task.md 씀→실무자화)
3. 발주서 빌딩 실체 = building-call-authoring 프리셋(brick/templates/presets/building-call-authoring.md).
   이미 제품으로 존재. architecture-plan 빌딩은 "의견서 산출기"라 발주서가 안 나온 것.
4. 스킬 로드≠준수: brick-task-author 로드하고 본문 안 읽고 편식→실패. 원문 읽어라.
```

★ 미착지 규율: 위 교정 2·3(발주서=authoring 프리셋 산출, COO=재검토+태우기)을 골 03에 규율로
박아야 함(아직 커밋 안 됨 — W1a 라이브 중 커밋하면 검증 baseline 흔들림, W1a 착지 후 넣기).

## 방지책 설계 완료 (별도 발주 대기 — "어떤 AI도 실무자화 못 하게")

워크플로(wf_4a0326c9-78a) 4렌즈 적대검증 결과. 문서추가는 답 아님(이미 있었고 안 읽힘) → hard forcing.

```text
실측 핵심: 모든 발사경로가 _run_dynamic_graph_walker(walker_kernel.py:1313) 단일 초크포인트로 합류.
  - 사람 앞문 = brick build(CLI) + resume 2개뿐. build()/launch_assembled_building/run_building_once는
    발사'루트'가 아니라 CLI 내부부품·체커용(Smith 지적으로 확정).
  - declaration_provenance 필드 이미 존재(check_tier_a_three_axis_conformance.py:424).
  - .claude/settings.json 없음(hook 슬롯 빔). BRICK_ROLE 스탬프 0건.
발주 후보:
  A(최우선) walker 진입에 provenance 필수 게이트+raise. 리스크=walker 직접호출 하네스 ~82곳 마이그레이션.
    → Smith 미결정: A를 [마이그레이션 선행 → 게이트 후행] 2단으로 쪼갤지 vs 한 발주. (COO 추천: 2단)
  B(동시) .claude/settings.json hook: 발사seam 직접 import/python런처 거부.
  C draft_diff advisory→gate 승격. D 역할 write-scope 런타임 assert(신규구축, 후순위).
한계: 게으른 우회는 A+B로 봉함. 고의 스탬프 위조는 별건(AI격리서명).
발주 시점 미결정: 지금 vs W1 착지 후. (COO 추천: W1 착지 후 — 방지책은 골 밖 메타개선)
```

## Smith 미결정 사항 (새 세션이 물어봐야 할 것)

```text
1. 방지책 발주 A: 2단 쪼개기 vs 한 발주?
2. 방지책 발주 시점: 지금 vs W1 착지 후?
3. 발주서=authoring 규율을 골 03에 넣는 문구 확정 (W1a 착지 후)
```

## 운영 규율 (상시)

```text
- COO 모든 결정·판단은 sequentialthinking 커넥터로 사고 후 (Smith 0709 지시).
- 착지 = clean worktree --all RC0 + 별도 commit/push + origin==HEAD. 자기검증 금지, 실행결과만 근거.
- 대작업 통짜 발사 금지(0708 부검: fugu 3h 500파일 소멸). 슬라이스 + 완주감시 or 격리경로.
- 애매하면 물어라. 무단 파괴적 행동 금지. 확장은 human gate.
```

## 참고 아티팩트

```text
골 체크리스트: https://claude.ai/code/artifact/8f7781ef-47a5-4432-bd5b-08f54c8ff1f0
방지책 워크플로 journal: subagents/workflows/wf_4a0326c9-78a/journal.jsonl
```
