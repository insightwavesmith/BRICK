# P6-C: 독립 fan-out 가지 동시 디스패치 (전진 병렬, pool=1 기본=byte-identical, pool=N 옵트인=증명)

## Operator pre-analysis (VERIFIED — bounded reading list)
A(running신호 da49aae)·B0(process_one_node 493df63)·B1(_FrontierDriver f31e000) 완료. Read ONLY:
- support/operator/walker_kernel.py:
  - 123-200 (`_FrontierDriver`: _items/_cursor/_scheduled_fan_steps, next_item() 현재 front 1개, append/defer/splice_after_current/splice_declared_successors_after_current)
  - 1995-2010 (루프 `while (item := frontier_driver.next_item())`) + 그 안 fan-in wait(_fan_in_wait_all_state, running_fan_steps 인자 이미 받음) + process_one_node 호출 + outcome 적용 결정부
  - completed_fan_steps/held_fan_steps/running_fan_steps 선언부 + resume_seed/replay_consumed(되감기)
- support/operator/walker_fan_in.py:_fan_in_wait_all_state(running_fan_steps 분기 이미 있음, A에서 깜)
- support/recording: 각 Brick이 자기 증거를 (step_ref,attempt_index) 경로에 따로 쓰는지(병렬 안전 확인)

## Reproduced facts (operator-verified, 설계 w3br8mkmh)
모델은 이미 병렬(Brick=독립단위·Link=의존). walker만 직렬. _FrontierDriver.next_item이 "다음 1개"를 주는 seam. 각 Brick은 자기 증거 자기가 디스크에 씀(병렬 안전). 핵심 원칙: **일(process_one_node)은 여럿이 동시, 결정/변이(outcome 적용·budget소비·번호·hold)는 드라이버가 정해진 순서로 직렬.** 되감기(resume replay)는 본질 직렬 — 동시화 안 함.

## Objective (invariant)
독립 fan-out 가지(서로 다른 step_ref, 의존 충족된 ready 노드)의 **process_one_node를 동시 실행**한다. 단:
- **pool 크기 설정 가능, 기본=1.** pool=1이면 동작이 B1과 **byte-identical**(--all 회귀 0). pool>1만 동시.
- **결정/변이는 직렬 드라이버**가 outcome을 **정해진 순서(frontier 등록 순/(step_ref,cascade_depth) 정렬)로** 적용 — wall-clock 도착순 아님(deterministic drain). budget 소비·adoption_sequence_number·hold·번호 전부 여기서 직렬.
- **running_fan_steps 라이브**: 노드 dispatch 시 add((step_ref,depth)), 완료 시 remove. (A에서 깐 fan-in 거짓HOLD 방지 분기가 비로소 살아남.)
- **resume/replay는 직렬 유지**(pool=1 강제). replay_consumed FIFO·disposition once-only·held_occurrence_index 불변.
- adoption_sequence_number는 동시 increment 금지 → 드라이버 직렬 적용에서만.

## Deliverables (번호)
1. **_FrontierDriver 동시 모드**: ready-batch 반환(ready_items() — 의존충족·미스케줄 독립노드 집합) + pool(worker) 디스패치. process_one_node를 batch에 대해 동시 실행(ThreadPoolExecutor 등, pool=1이면 1개=직렬). 워커는 순수(outcome 반환, 공유상태 변이 0).
2. **deterministic drain**: 완료 outcome을 도착순이 아니라 **canonical 순서**(frontier 등록 index 또는 (step_ref,cascade_depth) 정렬)로 버퍼링했다 직렬 적용. outcome 적용 결정부(기존 2011-2720 로직)는 불변, 호출 순서만 canonical 보장.
3. **running_fan_steps 배선** + **pool size seam**(설정·기본1). resume 경로는 pool=1 강제.
4. **FIRE 증명 프로브(체커)**: fan-out fixture를 pool=1과 pool=N(예: 4)로 각각 walk → evidence-manifest/spine/building-map을 정규화(timestamp/tempdir) 후 **byte-equal** 단언. + 다중-reroute-into-shared-fan-in fixture 포함(설계가 "직렬검증이 자동 이전 안 되는 유일 케이스"라 명시). support/checkers에 추가.

## Proof required (run yourself, report honestly — claims only from execution)
- **pool=1 기본 byte-identical**: 편집 전/후 `--all` 정규화 byte-diff = 빈 출력(기본 pool=1이라 직렬 FIRE 빌딩들 동작 불변, 회귀 0).
- `python -m compileall` + `git diff --check`.
- `check_profile.py --all` exit 0 (12 프로파일 + 새 동시성 FIRE 프로브).
- **동시성 정확성**: 새 FIRE 프로브가 pool=1 vs pool=N evidence byte-equal 단언하며 green. 다중-reroute-fan-in fixture가 byte-equal 안 되면 STOP+보고(정규화로 덮지 말 것).
- **변이 RED**: drain을 wall-clock 도착순으로 바꾸면(canonical 깨기) 동시성 FIRE가 RED → 복원. deterministic drain이 load-bearing임 증명.

## Hard constraints (law)
- write_scope: support/operator/walker_kernel.py, support/operator/walker_fan_in.py, support/checkers/**. (composition/driver/recording 읽기만.)
- **pool=1 기본 byte-identical 필수.** resume/replay 동시화 절대 금지(pool=1 강제). 결정/변이는 직렬 드라이버만(워커 순수). deterministic drain(canonical 순서) 필수 — wall-clock 적용 금지. 스케줄러/큐/retry 신규 의존성 외 금지(ThreadPool은 stdlib 허용). 기존 결정 로직 불변.
- 깨끗이 안 되거나 byte-equal 증명 안 되면 STOP 하고 file:line 보고(강행·정규화-덮기 금지).
