# HANDOFF — Codex → Claude Fable 5 (0710d)

| 항목 | 값 |
|---|---|
| 기록 시각 | 2026-07-10 11:51 KST |
| checkout | `/Users/smith/projects/BRICK` |
| HEAD | `dce5160d0850588742564c0b2c95d43778613c29` |
| origin/main | `1367adb5f0f1451f0663e2f4f279e6b9d68f5997` (main ahead 8) |
| 활성 골 | `019f47f9-e09b-73d1-b038-38ee8d12fc71` — **ACTIVE, 완료 처리 금지** |
| 커밋/푸시 | 없음. Smith 지시 전 금지 |
| 전체 정직 진척 | 구현 약 85%, focused 검증 약 80%, 감사 Exit E1–E6 약 74% |

## 0. 정본과 경계

계속 읽을 정본:

1. `project/brick-protocol/status/kernel/AUDIT-full-consolidated-dev-handoff-0710.md`
2. `project/brick-protocol/status/kernel/DESIGN-order-chain-casting-vocabulary-0710.md`
3. 이 핸드오프

절대 경계:

- `project/deku/**`와 `project/brick-protocol/status/inbox/deku-*`를 수정·정리·커밋하지 않는다.
- Smith의 선행 model-lane recast(fable-5 pm-lead, gpt-5.6-sol dev, xhigh) 파일을 되돌리거나 이 작업의 착지 단위로 간주하지 않는다.
- 오래된 worktree/WIP/salvage/stash를 일괄 삭제하지 않는다.
- 현재 dirty checkout을 보존한다. reset/checkout/clean 금지.
- checker green, frontier complete, Slack delivered를 제품 성공/품질 판정으로 과장하지 않는다.

## 1. 이번 세션에서 닫힌 것

### WO-1 lifecycle

- anchor 실패 시 dispose 금지, ignored/submodule fail-closed, write-capable temp fallback 거부.
- WIP owner/base/tree 검증, 세대 백업, exact resume, process lease, safe reaper.
- preset/graph/resume 공통 recovery handle과 landed ref.
- 별도 writer 프로세스 HOLD → 프로세스 종료 → 새 공식 `brick resume --decl` 프로세스 → exact binary bytes → complete → landed → WIP release → dispose 증명.
- durable process proof:
  `/private/var/folders/hm/3b5ry_rn3y18jk6bgy7w7z140000gn/T/brick-wo4-process-proof-hx7ribgw/proof-summary.json`
- `building_operator_driver0` 최신 focused 결과: PASS, 194 declarative / 46 kernel.

추가로 live3에서 발견된 완료 후 WIP 잔존을 `driver.py`에서 수리했다. 같은-run close anchor는 landed tree와 byte-identical일 때만 CAS release하며, resume 중 새 final WIP 세대도 landed tree와 동일할 때만 release한다. live3 잔존 ref `31e5703a...`는 landed tree와 동일함을 확인한 뒤 제품 helper로 해제했다. 다만 이 exact same-run 회귀 프로브는 별도 고정이 아직 필요하다.

### WO-2 official launch admission

- checkout identity/provenance/nonce 기반 정식 루트 admission과 비정식 진입 lethal deny 유지.
- 다섯 공식 route와 off-route deny focused 검증 완료.

### WO-3 입구/캐스팅/어휘

- 공개 실행 입구는 `brick build`, `brick resume --decl`, 명시 예제 `brick init`로 봉인.
- onboard module CLI 퇴역, portfolio/repair/replay는 declared plan kind/Builder 내부 표면으로 정리.
- quick-check/quick-fix만 `--fast-confirm` direct; non-quick preset은 authoring으로 보냄.
- `--real-provider` 첫-ready 및 local fallback 제거. 선언 provider 미준비는 dispatch 0 typed stop.
- non-quick provider timeout 명시, stop→forward proposal 재사용, reroute declaration 지원.
- `brick init --example-adapter`: 기본도 명시된 `adapter:local`; non-local은 exact readiness 검증만 하며 substitution 0.
- CLI/FIRST_USE 검수 증거에 adapter/model/`selected_reasoning_effort_ref` 노출.
- init closure 검증: `brick_cli_entrypoint` PASS 151/57, `building_operator_driver0` PASS 194/46, onboard seam/smoke + FIRST_USE PASS.
- `operating-vocabulary-v1.yaml`: 9 lanes, 12 Brick kinds, 30 presets. authoring/lowering 모두 봉인 밖 참조 fail-closed.
- `operating_vocabulary_v1` profile PASS 21 rules / 1 kernel.

### WO-4 route/lifecycle proof

- deterministic n2: first closure `implementation_gap` → work attempt 2 → QA siblings attempt 2 → second closure concern null. budget 부재 HOLD도 검증.
- real provider live3 complete evidence:
  `/private/tmp/brick-wo4-live3.EQ3xu5/buildings/wo4-n2-closure-reroute-e2e-0710-live3`
- live3 landed ref:
  `refs/brick/landed/wo4-n2-closure-reroute-e2e-0710-live3-acd85f4148b3`
- live3는 route/lifecycle E2E 증거일 뿐이다. code-attack QA attempt-2 body가 stale notification wrapper였으므로 품질 성공 증거로 쓰지 않는다.

### Slack 원인과 실증

- `/tmp --output-root`는 reporter가 Slack/dashboard sink를 의도적으로 제거한다. 앞선 Slack 미수신의 원인이다.
- 실제 기본 vessel에서 공식 probe 완료:
  `/Users/smith/.brick/project/brick-protocol/buildings/slack-official-route-probe-0710-codex1`
- Slack 8개 이벤트(`building_started` … `building_finished`) 전부 `delivered=true`, `http_2xx`, `slack_ok_true`.
- probe frontier complete, worktree disposed, WIP 없음, landed ref:
  `refs/brick/landed/slack-official-route-probe-0710-codex1-caa2209de990`

## 2. 지금 실행 중 — 종료하지 말 것

adapter-error frontier의 공식 forward resume live2가 새 프로세스로 실행 중이다.

- building id: `wo4-n2-closure-reroute-e2e-0710`
- evidence root: `/private/tmp/brick-wo4-live2.UcDcWn/buildings/wo4-n2-closure-reroute-e2e-0710`
- declaration: `/private/tmp/brick-wo4-live2.UcDcWn/resume-forward.json`
- starting WIP: `refs/brick/wip/wo4-n2-closure-reroute-e2e-0710`
- starting SHA: `5397d6b7c61c3a289cd47e8e4ae9d17f63867b22`
- Codex unified exec session: `51724`
- 시작 시 PID: uv `10859`, brick Python `10876`; 마지막 관측 provider child `17406` (closure Codex)
- 명령:
  `PATH=/Applications/ChatGPT.app/Contents/Resources:$PATH uv run brick resume --decl /private/tmp/brick-wo4-live2.UcDcWn/resume-forward.json --json`

해야 할 일: 프로세스를 죽이지 말고 종료를 회수한다. 종료 뒤 JSON/exit, exact WIP 및 landed refs, building-id worktree 부재, landed commit의 `route-byte.txt`, frontier와 attempt count를 확인한다. temp evidence나 refs를 삭제하지 않는다.

## 3. 부분 구현 — 다음 담당자가 먼저 닫을 것

### O1–O3 발주 체인

변경 파일:

- `brick_protocol/support/operator/building_call.py`
- `brick_protocol/support/checkers/lib/kernel_checks.py`

현재 구현:

- `freeze_building_call_order_v1`
- `forward_frozen_building_call_order_v1`
- `relower_building_call_order_v1`
- exact 8-answer 검증
- unresolved `remaining_delta` → 질문 목록 HOLD
- 노드별 adapter/model/effort casting table
- digest와 frozen JSON 직접편집 거부

현재 검증:

- 두 파일 `py_compile` GREEN.
- 두 파일 `git diff --check` GREEN.
- 임시 호출에서 freeze→held review, explicit forward, unresolved HOLD GREEN.

미완:

- O3의 실제 draft 변경 → non-zero diff 검증.
- `fixtures/building_call_order_chain/sizing_answers.json`가 아직 없음.
- profile/check_profile 등록이 없음. `kernel_checks.py`의 신규 함수는 현재 실행 불가 초안.
- CLI 수직 배선이 없음. 새 subcommand를 만들지 말고 기존 `brick build` authoring 결과 → frozen packet/graph-decl → 기존 `--graph-decl --forward` 경로로 연결한다.
- O1 실제 E2E가 아직 없음.

### adapter_error resume

- `walker_resume.py`에서 adapter-error hold의 허용 disposition을 `{forward, stop}`으로 수리했다.
- stop은 paper-close 유지, forward만 persisted held target 재실행.
- focused resume profile은 agent 보고상 GREEN.
- 최종 판정은 위 live2가 끝난 뒤에만 한다.

### process-proof checker 오염

현재 untracked:

- `project/brick-protocol/wo4-probe/process-boundary.bin`

이 파일의 mtime은 subprocess proof의 hold-result와 정확히 `11:36:11`로 같고 bytes도 checker fixture와 같다. 제품 실행 누수가 아니라 checker command runner가 provider version probe에서도 `_REPO_ROOT`를 받아 매 호출마다 write한 테스트 오염이다. `check_building_operator_driver0.py`의 `_write_then_complete`가 실제 sandbox invocation일 때만 쓰도록 고친 뒤, 이 파일이 이번 checker 산출물임을 다시 확인하고 제거한다. 무작정 `git clean` 금지.

## 4. 아직 닫히지 않은 감사 Exit

1. O1–O3 fixture/profile/CLI/E2E.
2. 같은-run close anchor → landed 후 WIP release 전용 회귀 프로브.
3. live2 완료 회수와 adapter-error resume 정식 증거.
4. WO-4 item 3 선택 기록: 신규 transition lifecycle 파라미터를 만들지 말고 기존 declared-plan revision/expansion chain을 공식 write 방향으로 선택하는 것이 현재 COO 권고. 구현/상태원장 확정 필요.
5. SHAPE ledger 4행:
   - SHAPE A runtime boundary = IMPLEMENTED
   - shared eligibility observation helper = PRESENT / observation-only
   - SHAPE B target/control integration = NOT_IMPLEMENTED
   - beyond-A = NOT_IMPLEMENTED / FROZEN
6. `check_profile.py --all` delta-green. 기존 Deku/dirty baseline과 신규 RED를 분리한다.
7. `ACTIVE_COO_GOAL.md`, master queue, 최종 closure report 갱신.
8. 모델 선언 별도 잔여: `run_provider_register_step`와 `_validated_model_ref_for_alias`가 invalid model을 registry/alias default로 치환한다. 이번 init adapter 범위에서는 건드리지 않았다.

## 5. 권장 재개 순서

1. live2 프로세스 종료 회수. 실패해도 WIP/worktree/evidence를 보존하고 원인을 기록한다.
2. `git diff --check`와 `py_compile`로 현재 dirty patch의 최소 건전성 재확인.
3. O1–O3 fixture/profile/check_profile 배선을 완성하고 focused RED→GREEN.
4. 기존 `brick build` 안에만 authoring→frozen review packet 배선. 새 입구 금지.
5. process-proof checker 오염 수리 + same-run WIP-release 회귀 고정.
6. focused profiles를 순차 실행(병렬 worktree lease 충돌 금지).
7. route-replay 선택 및 SHAPE ledger 기록.
8. 마지막에만 `check_profile.py --all`, delta 비교, 최종 감사 보고서.
9. 모든 Exit가 증명되기 전 활성 골을 complete로 바꾸지 않는다.

## 6. 커밋 상태

커밋/푸시 없음. 이 핸드오프도 untracked 신규 파일이다. Smith가 명시하기 전 커밋하지 않는다.
