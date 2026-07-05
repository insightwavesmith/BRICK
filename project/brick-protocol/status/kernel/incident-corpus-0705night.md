# 0705 심야 반려·홀드·봉쇄 사건 코퍼스 (부검 원자료)

Status: support evidence only — 사실 발췌. 귀속·패턴·처방은 부검 빌딩 몫. 원자료는 각
vessel(언트래킹)의 raw/link.jsonl·adapter-error.jsonl·step-outputs — 레인 접근 불가라
COO가 리터럴 발췌. 시각은 KST 0705 저녁~심야.

## 사건 목록 (시간순)

| # | 대상 | 관측 리터럴 | 결과 |
|---|---|---|---|
| 1 | bundle9 vessel (task-statement-c76328d20b68-node) | building_lifecycle_path_shape RED: "building root allows only work/, capture/, raw/, and evidence/" — 런처 output_root가 vessel 루트에 proposed-building-graph.json 잔류 | 잔해 회수로 해소. 런처 자동회수 단계 신설 |
| 2 | 주차장 5기(t5-pin-diet·engine-smalls·gap2v1·wsallow-repair·t1s2v3) forward 시도 | 전건 "승인 대상 hold 상태가 아니에요" / frontier=evidence_incomplete | 상태 무변경 거부 5건 |
| 3 | bundle10-wheel-0705a·bundle11a-0705a·gap1b-0705a | code-attack-qa 스텝 adapter-error `local_cli_nonzero` adapter:claude-local rc=1, step-output 無 — 직접 재현: "You've hit your monthly spend limit" | 3빌딩 fan-in 미충족 주차. 계정 재로그인으로 원인 해소 |
| 4 | 위 3기 stop 시도 | 전건 "승인 대상 hold 상태가 아니에요" / evidence_incomplete | 거부 — fresh 0705b 재발주 |
| 5 | bundle10-wheel-0705b | 4레인 전원 반환 후 hold_reason=`no_resolving_reroute_address` (pending=review). QA concern="wheel-smoke-all-red-under-uv-run"(setuptools 부재 env RED), review concern="root-build-artifact-residue"(build/·egg-info 루트 잔해) | forward 시도 → "승인 대상 hold 상태가 아니에요"/evidence_incomplete. **raw/agent-received.jsonl 파일 자체 부재, returns=4** — 0705c 재발주(concern 2건 계약 반영) |
| 6 | t10-first-drive-0705a | design 완주 후 hold_reason=`gate_sequence_missing_required_facts:link-gate:coo` — 설계된 홀드#1 | 정상 (운전 대기) |
| 7 | T10 단계2 dry-run | assemble_expanded_graph_plan → "gate_sequence_policy reroute target requires finite node_reroute_budget" — plan_graph.py:162 부재→{} 정규화 vs 출생 구성 검증의 None-스킵 (비대칭). 수리 후 같은 에러가 plan_validation.py:907(사본 2)에서 재발 | t10gap2(8909b968 앵커, 미머지)→t10gap2b(d52aea38 머지)로 사본 전수 통일 |
| 8 | t10gap2 런처 1차 | brick() 캐스팅 "model must be bare text or an admitted ref" — "claude:claude-fable-5" 불량형. 2차: 셸 & 고아 발사로 cwd 오염 import 즉사(COO 실수, 규칙 위반) | 정식 ref(`model:claude:claude-fable-5`)+정식 백그라운드 재발사 |
| 9 | t7-recovery-0705a | 4레인 반환 후 hold_reason=`runtime_handoff_address_unresolved_in_ledger:work/step-outputs/...-work-attempt-1` (pending=work). QA·review concern="D2 실물 vessel이 W1 워크트리에서 관측 불가"(언트래킹) | forward 시도 → evidence_incomplete 거부(10례째). WIP 앵커 수확 + COO 전체 게이트로 부트스트랩 예외 랜딩(18b3089a) |
| 10 | bundle10-0705b 정정 후 처분(수리판 코드) | disposition_written=True(봉쇄 돌파) → resume이 "missing step-output source_fact body/evidence: work/step-outputs/task-statement-0371620753..." 에러 | 별개 클래스 신규 관측 — main 코드 재시도 미실시 |

## COO 계약·운영 실수 (자가 기록 — 부검 대상에 포함하라)

- gap2a 계약 D2가 "조립 통과"만 리터럴 명시(4단 전체 누락) → 사본 2 미포착, 후속 발주 비용.
- t7-recovery 계약 D2가 언트래킹 vessel 실증을 레인에 배정(0702 각인 "레인-불가능 D 분리" 위반 재발).
- 스윕 rc=1인데 push 발화 1회(체인을 스윕 rc가 아닌 cat에 걸음) — 잔해 클래스라 무해 판명.
- 셸 & 고아 발사 1회(사건 #8).

## 참조 (커밋됨 — 레인 접근 가능)

goal-phases-consolidated-0702.md §자율운행 판·§월 지출 한도 사건·§T10 운전 경과 /
t10-drive-runbook-0705.md §검수 이력·§4 / 처분 어휘 hold-disposition-vocabulary-0704.md /
정정 선언 resume-ledger-mismatch-recovery-0704.md·wip-preservation-principle-0704.md.

증거 한계: COO 발췌본 — 원자료 재확인은 각 vessel 경로. 판정·귀속 없음(부검 빌딩 몫).


## ⚠ 사후 정정 (0705 심야 3차 — 부검 착수 후 발견, 산출 해석 시 필독)

**사건 2·4·5(forward/stop 거부)·9(forward 거부)의 "evidence_incomplete 봉쇄"는 상당수 유령이었다.**
COO 처분 스크립트가 building_ref를 **상대 경로**로 넘겼고, run_approve_entry는 이를 repo가
아니라 기본 출력 루트(~/.brick/goal-runs)로 해석 — **존재하지 않는 유령 경로를 관찰**해
"required evidence files are missing"→evidence_incomplete→거부가 나온 것(실물 반환:
building_root가 goal-runs 하위로 찍힘). 절대 경로를 쓴 호출(t7-recovery D2 실증)만 통했다.
- 실재 확인된 진짜 꼬리: bundle10-0705b(직접 observe로 evidence_incomplete 재현 — 수취
  파일 부재+resume 영수증 꼬리). t7-recovery 수리는 이 실재 클래스에 유효(3면 fail-closed 실증).
- 미재검: 주차장 5기·0705a 3기 — 절대 경로 재시도 전까지 봉쇄 여부 미확정.
- 신규 결함 후보: run_approve_entry가 부재 루트를 "building not found"가 아니라
  evidence_incomplete로 분류(유령-해석이 오진 기계가 됨) — 소형 수리 후보.
- COO 실수 5호로 등재: 처분 building_ref는 항상 절대 경로(evidence_root 원문)로.

## 추가 사건 (심야 4차)

| 11 | t10-first-drive-0705a 재파견 replay | disposition_written=True 후 "resume replay encountered an already-disposed recorded HOLD for '...-design' with unsupported prior disposition" — 같은 빌딩에 순차 처분 2회(reroute→reroute)를 replay 체인이 미지원 | 0702 결함 가족 ②의 신 구성원(다중-처분 replay 한계). fresh 재운전(0705b)으로 우회 — T7 계열 백로그 보강 |
