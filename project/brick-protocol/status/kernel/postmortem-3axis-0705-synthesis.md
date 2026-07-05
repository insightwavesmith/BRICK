# 0705 심야 부검 — 3축 귀속 종합 (postmortem-fleet v2 산출 회수)

Status: support evidence — 부검 fleet(inspect→codex 코드렌즈→gemini 축·증거 렌즈→closure)
3렌즈 산출을 COO가 정본 회수. 원 vessel = ~/.brick/.../postmortem-3axis-0705b(link_paused,
장부꼬리 — 산출은 완결). read-only 계약이나 axis-lens 레인이 격리 워크트리에서
check_building_operator_driver0.py 수정(closure가 정직 적발, 메인 무유출 — COO 확인).
처방은 후보이며 채택·우선순위는 Smith/COO 몫. 이하 evidence-lens 렌즈 보고 본문:

---

# 0705 심야 부검 보고서 — 3축 귀속 및 사건 귀속 분석 v2

## 1. 12개 사건 심층 분석 (3축 귀속 + 최초 이탈점 + 작동 방어 + 처방 후보)

### 사건 1: bundle9 vessel (task-statement-c76328d20b68-node)
* **축 귀속**: Brick (계약/체크) + Engine (런처)
  * 근거: `building_lifecycle_path_shape RED: "building root allows only work/, capture/, raw/, and evidence/"`
* **최초 이탈점**: 런처가 vessel 루트에 `proposed-building-graph.json` 잔여물을 남겨둠 (Engine).
* **작동한 방어**: Brick 축 (엄격한 파일 구조 체커인 `building_lifecycle_path_shape`가 잔해 감지 및 즉시 차단).
* **처방 후보**: Engine (Launcher가 `proposal` 파일을 vessel 밖 지정 경로에 쓰도록 보호하거나, 실행 완료 시 자동 제거 기계화).

### 사건 2: 주차장 5기 forward 시도 (t5-pin-diet·engine-smalls·gap2v1·wsallow-repair·t1s2v3)
* **축 귀속**: Link (이동) + Engine (호출/해석)
  * 근거: `"승인 대상 hold 상태가 아니에요" / frontier=evidence_incomplete` 및 사후정정 분석
* **최초 이탈점**: COO 처분 스크립트가 `building_ref`를 상대 경로로 전달 (Engine).
* **작동한 방어**: Link 축 (`run_approve_entry` 가드가 존재하지 않는 경로를 `evidence_incomplete`로 반환하여 무변경 거부).
* **처방 후보**: Engine / Link (처분/재개 표면이 상대 경로를 repo 기준으로 자동 정규화하며, 미존재 시 `building not found`로 명확히 에러 분류).

### 사건 3: bundle10-wheel-0705a·bundle11a-0705a·gap1b-0705a
* **축 귀속**: Agent (수행 환경)
  * 근거: `code-attack-qa 스텝 adapter-error local_cli_nonzero rc=1 (You've hit your monthly spend limit)`
* **최초 이탈점**: 외부 Provider API 월별 지출 예산 한도 도달 (Agent).
* **작동한 방어**: Agent 축 / Engine (어댑터가 nonzero rc=1을 반환하고 step-output이 생성되지 않아 fan-in 미충족 상태로 후속 이동 전 차단 및 주차).
* **처방 후보**: Agent / Engine (지출 한도 초과 오류를 특정하여 명시적인 로깅/알림 기능 또는 fallback을 어댑터에 연동).

### 사건 4: 위 3기 stop 시도
* **축 귀속**: Link (이동) + Engine (호출/해석)
  * 근거: `"승인 대상 hold 상태가 아니에요" / evidence_incomplete` 및 상대 경로 전달.
* **최초 이탈점**: COO 처분 스크립트의 `building_ref` 상대 경로 사용 (Engine).
* **작동한 방어**: Link 축 (상대 경로로 인한 `evidence_incomplete` 유령 봉쇄 작동).
* **처방 후보**: Engine / Link (상대 경로의 정규화 보완 및 오진 제거).

### 사건 5: bundle10-wheel-0705b
* **축 귀속**: Agent (수행) + Link (이동) + Engine (해석)
  * 근거: `hold_reason=no_resolving_reroute_address` (QA/Review 우려: setuptools 누락 환경 RED, build/ 잔해) 및 `raw/agent-received.jsonl` 유실(returns=4)
* **최초 이탈점**: 수행 레인의 환경 미비 및 빌드 잔해 발생 + Agent 반환 영수증 파일 유실.
* **작동한 방어**: Agent/Link 축 (미해결 reroute 홀드 발화 및 forward 시 실제 `evidence_incomplete` 거부 작동).
* **처방 후보**:
  - Brick (필수 개발 의존성을 계약 preflight 세션에 의무화).
  - Checker (빌드 부산물 또는 필수 영수증 유실 사전 감지).
  - Engine (returns 유효성 검증 체인 보완).

### 사건 6: t10-first-drive-0705a
* **축 귀속**: Link (게이트)
  * 근거: `hold_reason=gate_sequence_missing_required_facts:link-gate:coo`
* **최초 이탈점**: 없음 (계약에 의해 명시적으로 설계된 홀드#1).
* **작동한 방어**: Link 축 (계약상 필수적인 COO 게이트 조건 미충족에 따라 정상 대기).
* **처방 후보**: 없음 (설계대로 완벽 작동).

### 사건 7: T10 단계2 dry-run
* **축 귀속**: Engine (설계 및 그래프 빌더)
  * 근거: `assemble_expanded_graph_plan` 중 budget normalization 비대칭성 및 `plan_validation.py:907` 사본 2 재발
* **최초 이탈점**: 코드 중복 및 예산 정규화 처리의 비대칭성 결함 (Engine).
* **작동한 방어**: Engine (Plan 검증 단계에서 예산 오류 거부 발화).
* **처방 후보**: Engine / Checker (중복 파일 완전 제거 및 단일화, 그래프 투영과 탄생 유효성 검증 로직 대칭성 통일. 파일 중복 정적 체커 추가).

### 사건 8: t10gap2 런처 1차 및 2차
* **축 귀속**: Brick (계약) + Engine (런처)
  * 근거: `brick() 캐스팅 모델 ref 철자 오류` 및 `셸 & 고아 발사로 인한 CWD 오염 import 즉사`
* **최초 이탈점**: 잘못된 모델 식별자 기재 및 셸 백그라운드 수동 구동으로 인한 오염 (Operator / Engine).
* **작동한 방어**: Brick 축 (모델 캐스팅 규칙 가드) 및 Engine (CWD 오염 수동 가드 즉사).
* **처방 후보**:
  - Brick (잘못된 표기 입력 시 올바른 ref 형태를 추천하는 피드백 린트).
  - Engine (CLI 및 조립 어서트, 자동 타임아웃, 백그라운드 구동을 하나로 묶은 런처 헬퍼 패키지화).

### 사건 9: t7-recovery-0705a
* **축 귀속**: Agent (수행) + Link (이동)
  * 근거: `hold_reason=runtime_handoff_address_unresolved_in_ledger` 및 `D2 실물 vessel W1 워크트리 부재(언트래킹)`
* **최초 이탈점**: 언트래킹 경로인 실증 요소를 레인 D에 잘못 지정한 계약 구성 (Operator) 및 상대 경로 forward 오류.
* **작동한 방어**: Link 축 (handoff 주소 미해결 홀드 및 `evidence_incomplete` 거부 작동).
* **처방 후보**:
  - Brick/Checker (계약 내 언트래킹 경로를 레인 D에 배정 시 사전에 잡는 린트 규칙).
  - Engine (vessel-상대 경로 해석 강화 및 detached 워크트리 자동 생성 자동화).

### 사건 10: bundle10-0705b 정정 후 처분
* **축 귀속**: Engine (재개 해석)
  * 근거: `disposition_written=True` 후 resume이 vessel-상대 step-output 경로 해석 실패 (`missing step-output source_fact body/evidence`)
* **최초 이탈점**: 재개 시 vessel-상대 경로의 `source_fact`를 vessel 루트 기준으로 제대로 해소하지 못함 (Engine).
* **작동한 방어**: Engine (재개 중 증거 무결성 오류 발화).
* **처방 후보**: Engine (vessel-상대 경로의 `source_fact`를 vessel 루트 기준으로 번역하도록 재개 해석 표면 보완).

### 사건 11: t10-first-drive-0705a 재파견 replay
* **축 귀속**: Engine (Replay 한계)
  * 근거: `already-disposed recorded HOLD ... unsupported prior disposition` (순차 처분 2회 리플레이 미지원)
* **최초 이탈점**: 동일 빌딩에 대해 연속 처분(reroute -> reroute) 시 리플레이 체인이 크래시되는 Engine 한계.
* **작동한 방어**: Engine (Replay 과정에서 이중 처분 기록 발견 시 안전 차단).
* **처방 후보**: Engine (Replay 엔진이 다중 처분 및 이력 누적을 안전하게 처리할 수 있도록 이력 다중화 확장 수리).

### 사건 12: erg1 게이트
* **축 귀속**: Brick (계약) + Checker (검증)
  * 근거: `커밋 메시지에 RED 허위 기재 (D1 변이가 rc=0 무발화인데 로그 오독 병합). 체커가 D1 커버 안 함 (공허 프로브).`
* **최초 이탈점**: 인간 로그 오독 및 체커의 공허 프로브/빈 경로 필터링 부재.
* **작동한 방어**: 없음 (그대로 머지되어 실증 단계에 이르러서야 확인됨).
* **처방 후보**: Checker (실제 변이 테스트 시 프로브가 무효화되거나 실행되지 않는 공허 상태 `rc=0`를 감지하여 RED 경고를 발생시키는 가드 강화).

---

## 2. COO 계약 및 운영 실수 6건 분석 및 매핑

1. **gap2a 계약 D2 리터럴 부족**: D2 조립 통과만 명시하여 4단 전체 누락.
   * **귀속**: Brick (계약 불완전).
   * **이탈점**: 계약 설계 단계.
   * **처방**: Checker (확장 계약 조각에 "4단 dry-run" 명시를 요구하는 린트 자동화).
2. **t7-recovery 계약 D2 언트래킹 배정**: 레인 불가 사양인 언트래킹 vessel 실증을 레인 D에 배정.
   * **귀속**: Brick/Agent (레인 불가 사양 배정).
   * **이탈점**: 계약 설계 단계.
   * **처방**: Checker (buildings/ 내의 언트래킹 경로가 레인 D에 직접 할당될 시 경고하는 계약 린터 확장).
3. **스윕 rc=1 상황에서 push 발화 1회**: 체인을 스윕 rc가 아닌 cat에 걸어 무해하나 잔해 발생.
   * **귀속**: Engine (스크립트 훅 누수).
   * **이탈점**: 스윕 트리거 설정 단계.
   * **처방**: Engine (스크립트 리턴 코드의 엄격한 상속 및 유효성 검증).
4. **셸 & 고아 발사 1회**: 백그라운드 수동 실행 및 CLI 타임아웃 미지정.
   * **귀속**: Engine (실행 환경).
   * **이탈점**: 수동 백그라운드 발사.
   * **처방**: Engine (CLI 어서트 및 정독 레인 안전 타임아웃 기본값, 백그라운드 관리를 패키징한 전용 런처 구비).
5. **처분 building_ref 상대 경로 사용**: `run_approve_entry`에 상대 경로를 전달해 ~/.brick/goal-runs 유령 경로 해석으로 유령 봉쇄 발생 (사후정정).
   * **귀속**: Link/Engine (경로 해석).
   * **이탈점**: 처분/재개 도구 실행 단계.
   * **처방**: Engine/Link (상대 경로를 repo-상대로 자동 정규화하며, 부재 경로는 "building not found"로 명시 거부).
6. **erg1 게이트 로그 오독 및 허위 기재**: D1 rc=0 무발화를 RED 실패로 오독하고 잘못 커밋/병합.
   * **귀속**: Checker / Operator.
   * **이탈점**: 수동 검수 및 병합 승인 단계.
   * **처방**: Checker (공허 프로브 자동 차단 및 실무 테스트 실행 여부 엄격 검증).

---

## 3. 반복 패턴 집계 (Aggregated Patterns)

1. **유령 경로 및 해석 오진 패턴 (Ghost Path Interpretation Family)**: 총 4회 (사건 2, 4, 5, 9). 처분/재개 표면의 상대 경로 기재가 유령 디렉토리(~/.brick/goal-runs) 해석으로 번역되어 가짜 봉쇄를 생성한 동족 결함.
2. **공허 변이 프로브 패턴 (Empty/Silent Mutation RED Family)**: 총 1회 (사건 12, COO 실수 6). 실행 결과가 rc=0(변이 없음) 임에도 오독되어 반영되거나 무효화되는 검증 공백 패턴.
3. **코드/검증 중복 및 유효성 비대칭 패턴 (Asymmetric Validation Family)**: 총 1회 (사건 7). 예산 정규화 로직이 복수의 검증 파일(`plan_graph.py`, `plan_validation.py`)에 사본으로 산재하여 일방적 수정만으로 해결되지 않고 비대칭 설계 오류를 남긴 패턴.
4. **다중 연속 처분 리플레이 제한 (Multi-disposition Replay Limit)**: 총 1회 (사건 11). 동일 빌딩에 순차 처분이 가해졌을 때 리플레이 엔진이 단일 처분 이력 가정으로 인해 거부하는 한계 패턴.

---

## 4. 유령(경로 실수)과 실재 결함의 명확한 분리

* **유령 봉쇄 (Ghost Blockades)**: 사건 2, 4, 그리고 사건 5 및 9의 forward 거부 중 상당수는 처분 빌딩 주소로 '상대 경로'를 넘겨 오진 기계가 `evidence_incomplete`를 오발한 가짜 봉쇄임. 절대 경로 구동 시 정상적으로 상태 확인 가능성 높음.
* **실재 결함 (Real Blockades)**: 
  * **사건 5 (bundle10-wheel-0705b)**: `raw/agent-received.jsonl`이 실제로 유실되었고, setuptools 누락 환경 및 build 잔해가 실제로 발생한 실재 봉쇄임.
  * **사건 9 (t7-recovery-0705a)**: D2 실물 vessel이 실제로 W1 워크트리에서 관측 불가(untracked) 상태였던 실재 결함임.
  * **사건 10**: resume 시 vessel-상대 step-output `source_fact` 해석 오동작은 엔진의 실재 결함임.
  * **사건 11**: 다중 순차 처분 리플레이 한계는 리플레이 엔진의 실재 제약임.