# CLOSURE 보고 — 0710e Fable5 개발 세션 (Codex→Fable5 인계 소화)

| 항목 | 값 |
|---|---|
| 기록 | 2026-07-10 오후 · Claude COO (Smith 지시로 개발 수행 — COO read-only 규율의 명시 예외) |
| 진입정본 | `HANDOFF-session-0710d-codex-to-fable5.md` |
| HEAD | 작성 시점 `dce5160d0` → Smith GO(0710 오후)로 커밋: recast `7b25eb0d5` · dev패치 `f71d67db2` · 커널문서(본 커밋). deku 제외 |
| 활성 골 | `019f47f9-…` **ACTIVE 유지** (complete 전환 안 함) |
| 보호앵커 | `refs/brick/wip/main-dirty-dev-0710d` = `052c008db` — **전체 dev 패치 164파일 +20,388/−1,506 소실 불가** |
| 성격 | support evidence. source truth·성공·품질·Movement 권위 아님 |

## 1. live2 종료 회수 판정 (핸드오프 §2 소화)

```text
프로세스: 종료 확인(PID 소멸). 걷기 자체는 완주 — work-2/QA-2(실디스패치 189초)/
  axis-QA-2/closure-2 step-output 전부 생성, 11:55:02 close.
사인: HOLD 재생 후처리(_stamp_resumed_lifecycle_on_held_source →
  walker_hold 재생 fixture)가 source_fact 문맥(building_root)을 잃어
  run.py:2366 "missing step-output source_fact body/evidence"로 land 직전 사망.
  (Codex 진단 4좌표 전부 실측 일치. raw 원장 1행은 원인이 아니라
   최종 기록기 미도달의 결과 — 이것도 실측으로 확인)
보존: 새 WIP 세대 305f794df가 route-byte.txt 포함 — 바이트 무손실.
  worktree 처분됨, landed 없음(fail-closed가 옳게 거부).
빌딩 자체는 evidence_incomplete dead-end → 재현은 아래 회귀잠금으로 대체,
  실빌딩 정리는 Smith 처분 대기.
```

## 2. 이 세션이 수리한 것 (전부 기계채점 검증)

| # | 수리 | 파일 | 검증 |
|---|---|---|---|
| 1 | **소실문맥 수리**: 선언 building_root를 source-fact 루트 스캔 1순위로 + hold 재생 fixture에 실root 탑재 + kernel→seed→hold 3층 스레딩 (재생 결과의 lifecycle_write.root는 빈 값이라 스레딩이 유일해) | run.py · walker_hold.py · walker_resume_seed.py · walker_kernel.py | 함수레벨 RED→GREEN + 회귀잠금(아래 3) GREEN |
| 2 | **live2 회귀 영구잠금**: 커스텀 root + adapter-error hold + 공식 disposition + resume → RED(수리 전 동작 모조 = 크래시 재현 필수) / GREEN(frontier complete + 원장 정합 필수) 2모드 프로브 | check_building_operator_driver0.py `_holdstamp_source_fact_context_fire` | driver0 focused **PASS** (exit 0) |
| 3 | **O1–O3 배선 완성**: 8답 fixture 생성 · kernel check 등록 · profile 신설 · admission seed 등재 · 변이 RED 발화 증명 | fixtures/building_call_order_chain/ · check_profile.py · profiles/building_call_order_chain.yaml · check_package_path_admission.py | 계약 체크 GREEN (6 inspected, 내장 RED 프로브 2종) |
| 4 | **CLI 수직 배선** (새 입구 0): `--order-freeze/--order-answers/--order-forward` — freeze→질문HOLD/검수패킷(캐스팅표), forward는 digest 검증 후 기존 --graph-decl 경로로, **launch 이중열쇠 보존**(기본 stop) | cli.py `_run_order_chain_build` | 스모크 4종: 질문HOLD·검수패킷(캐스팅 4행 "readiness not consulted")·stop 보존·변조 typed 거부 |
| 5 | **체커 오염 수리**: 버전 프로브(cwd=라이브repo)에서 fixture 쓰기 차단 + 오염물 바이트 검증 후 제거 | check_building_operator_driver0.py `_write_then_complete` | driver0 재실행 PASS + **재오염 없음 실측** |
| 6 | parents[N] 바인딩 등록 (WO-3 잔여 — building_call_authoring.py:95 parents[2]) | check_import_identity_modes.py | focused **PASS** (89 targets) |
| 7 | route-replay 선택 + SHAPE 원장 4행 | `route-replay-choice-shape-ledger-0710.md` | 문서 확정 |

## 3. 최종 검증 — `check_profile.py --all` delta 판정

```text
실측: TRUE_EXIT=1 · profile passed 36 · red 관측 93 (전체 로그 6,788줄 캡처)
클래스 분해 (기준선 HEAD dce5160d0 worktree 실측 대조):
  A. deku 잔재      : package_path_admission ×13 프로파일 + building_lifecycle_path_shape 등
                      전부 project/deku/** untracked — 기준선·불가침 (처분=Smith)
  B. L3 admission   : "official launch token absent" — allowlist(9 진입점) 밖 체커들
                      (building-automation resume계열 4종·agent_axis·tier-a·interactive-intake·
                       assembly_equivalence 내부 등) — 15ccd10ac 회귀의 잔여 = WO-2 후속
                      (체커 allowlist 확장), 이 세션 변경과 무관 (기준선 HEAD에서도 동일 RED 실측)
  C. 기타 기준선    : mutation-red-manifest(기준선 RED 실측·신규 코드 언급 0) ·
                      graphdecl-fix(assembly/mutation 연쇄)
  D. ★신규 RED     : import_identity_modes 1건 → 수리 완료 → PASS
∴ delta-green: 이 세션 변경발 신규 RED = 0 (D 수리 후).
  focused 재확인: driver0 · brick_cli_entrypoint · resume_declaration ·
  import_identity_modes · building_call_order_chain(계약) 전부 PASS.
```

## 4. 남은 것 (정직 — 골 Exit 미충족분)

```text
1. O1 라이브 E2E: freeze→forward→--forward 실발사 1회 (실프로바이더 비용 — Smith GO 대기.
   frozen fixture 캐스팅 = opus/claude 계열이므로 발사 시 실비용)
2. L3 admission 잔여: allowlist 밖 체커들의 admission 확장 (위 클래스 B 소거) = WO-2 후속 발주
3. same-run WIP release 전용 회귀핀 (live3 실측+CAS 코드 driver.py:1330-1370 검증으로 갈음 중)
4. 기준선 RED 소거: deku 잔재 처분(Smith) · assembly_equivalence의
   "default-root forward approval did not reuse proposal root"(stop→forward 재사용 결함,
   WO-3 항목과 연결 확인 필요) · mutation manifest 정리
5. 커밋/푸시/골 전환: 전부 Smith 지시 대기. 커밋 시 분리 원칙:
   ①model-lane recast 11파일 ②커널문서 ③dev 패치(코덱스+파블) ④deku 제외
6. 프로세스 재시작+실파일수정+reroute까지 겹친 단일 공식 E2E(핸드오프 §3 잠금 문구의 완전형)
   — 회귀잠금(2절)이 in-process로 커버, 프로세스 경계 겹침은 wo4-process 픽스처가 커버,
   둘을 하나로 겹친 단판은 미실시
```

## 5. 좌표

```text
수리 diff: git diff (미커밋) — 보호앵커 052c008db로 전량 보존
회귀잠금: check_building_operator_driver0.py::_holdstamp_source_fact_context_fire
전수 로그: <session scratchpad>/all-sweep-0710e.log (6,788줄)
live2 증거: /private/tmp/brick-wo4-live2.UcDcWn/buildings/wo4-n2-closure-reroute-e2e-0710
  (보존 — 삭제 금지, WIP 305f794df)
```
