# 부검-딥 0706a 종합 정본 (closure 수확 — 이종 3두뇌 fable5/codex/fugu-ultra, 대조 회수율 2/3)

Smith 0706 채택: R1~R8 전량 개선 큐 편입(골 문서 마스터 큐 반영). source truth·판정 아님.

===== adapter_ref =====
adapter:claude-local

===== agent_object_ref =====
agent-object:coo

===== brain_surface_ref =====
brain-surface:claude-code-local-cli

===== cli_call_ref =====
support-cli-call:adapter:claude-local:postmortem-deep-0706a

===== cli_version_text =====
2.1.201 (Claude Code)

===== deferred_smith_review_queue =====
[0] 모델-레인 이탈 표면화: design 및 closure lane이 model:claude:claude-fable-5로 디스패치됨 — discipline:model-lane-matching은 fable5를 lane 모델에서 제외 선언; 프리셋/어댑터 기본값 점검 요망.
[1] Case 6: 어느 kernel 문서가 처분을 지배하는가 (goal-phases-consolidated-0702.md:726 closed vs autopsy-corpus-0706.md reopened).
[2] Case 8: 인간실수 vs 미착지 엔진갭 — 착지 레코드 수색 결과에 따른 처분.
[3] R1-R8 처방 행의 채택·우선순위 및 인체공학 표/골 문서 반영 여부.
[4] Case 4 재개 여부 (원 /tmp 증거 소실 상태에서 재현 시도 가치 판단).

===== deliverable_crosscheck =====
[0] {'deliverable_ref': '1-합의-충돌-고유발견-분리', 'diff_artifact_refs': [], 'evidence_refs': ['this-return:observed_evidence[2-5]'], 'implementation_status': 'not_applicable_read_only'}
[1] {'deliverable_ref': '2-반복-패턴-표-클래스별-사건-축귀속', 'diff_artifact_refs': [], 'evidence_refs': ['this-return:observed_evidence[6]'], 'implementation_status': 'not_applicable_read_only'}
[2] {'deliverable_ref': '3-유령-실재-분리', 'diff_artifact_refs': [], 'evidence_refs': ['this-return:observed_evidence[7]'], 'implementation_status': 'not_applicable_read_only'}
[3] {'deliverable_ref': '4-대조사건-회수율-및-할인표기', 'diff_artifact_refs': [], 'evidence_refs': ['this-return:observed_evidence[1]'], 'implementation_status': 'not_applicable_read_only'}
[4] {'deliverable_ref': '5-처방후보-표행-골문서행-형태', 'diff_artifact_refs': [], 'evidence_refs': ['this-return:observed_evidence[8]'], 'implementation_status': 'not_applicable_read_only'}
[5] {'deliverable_ref': '6-억지-클래스화-금지-준수', 'diff_artifact_refs': [], 'evidence_refs': ['this-return:observed_evidence[6] (Case 4/5/6/8/9 단독 유지, 4·7은 후보 표기만)'], 'implementation_status': 'not_applicable_read_only'}
[6] {'deliverable_ref': '7-판정금지-미해결-concern-처리', 'diff_artifact_refs': [], 'evidence_refs': ['this-return:transition_concern_evidence'], 'implementation_status': 'not_applicable_read_only'}

===== evidence_refs =====
[0] support-packet:postmortem-deep-0706a:agent-object:coo:output

===== narrowly_proven =====
[0] 세 진단 반환문이 각각 ledger에 존재하고 본문이 위 종합과 일치함 (세 step-output.json 직접 읽음).
[1] 대조-사건 자력 회수는 A·C 2건에서 반환문 내 코드 좌표·실측 서술로 뒷받침되고, B는 자신의 반환문에서 '독립 재증명 아님'을 스스로 기록함 — 회수율 2/3은 반환문 텍스트 기준으로 좁게 증명됨.
[2] '19:03 동시' 기각은 3개 반환문 모두에 독립 기재됨(C는 3개 타임스탬프 전부 인용).
[3] B의 5aeaeea 부정 주장과 C·review의 긍정 소재 기록이 동일 빌딩 ledger 안에서 상호 모순됨(도메인 라벨 부재가 공통 원인 후보라는 점까지가 관측; 원인 확정 아님).
[4] 이 closure는 파일을 쓰지 않았고 write_scope는 {}임.

===== next_target_candidates =====
[0] Case 9 증거-포착 빌딩: 팬 수신→자식 터미널 이음새의 driver 사망 신호·liveness 관측 + loud HOLD (R3; watchdog 설계는 그 뒤).
[1] checker 갭 점수리 빌딩: check_building_operator_driver0.py에 _report_event_observations 생존 단언 추가 + run.py carry 루프 공용 헬퍼화 (R2).
[2] parents[N] 바인딩 가드/레지스트리 체커 빌딩 (R1; 선행으로 31 vs 44 재실측 겸함).
[3] Case 8 착지-레코드 수색 (git 실측 가용 — 가벼운 read-only 정찰로 가능).
[4] 부재-주장 도메인 라벨 verifier를 lens 반환 계약에 반영 (R5) + lane 지시문에서 'git 도구 없음' 제거 (R8).
[5] Case 6 처분 단일소스 선언 kernel 문서 행 (R7) — 스미스 처분 후 문서 빌딩.

===== not_proven =====
[0] brain surface behavior
[1] credential validity
[2] tool or hook execution
[3] runtime or scheduler behavior
[4] quality of returned work
[5] Case 9 driver-process 사망 근인 (freeze 경계·회수만 관측됨).
[6] Case 4 근인 (/tmp coo-gate-erg5 로그 계열 재독 불가).
[7] Case 2 계정전환 인과 (확정도 배제도 안 됨).
[8] Case 6 어느 kernel 문서가 처분을 지배하는지; Case 8 인간실수 vs 미착지 엔진갭 경계.
[9] A의 31 vs C의 44 수치 차이의 정확한 원인(패턴 상이 추정, 본 패스에서 재실측 안 함 — 이 closure는 carried evidence 종합만 수행).
[10] R1-R8 처방 행의 구현 준비도·의미 적합성 (전부 미채택 후보).
[11] B의 어댑터-오류 직접 실측 항목들 자체의 신뢰성 문제는 관측되지 않았음 — 할인 표기는 코퍼스 규칙 적용 기록이지 품질 판정이 아님.
[12] 환경 제약: 이 closure lane은 read-only이며 종합 아티팩트 파일(B가 후보로 지목한 status/kernel/postmortem-deep-0706a-diagnosis-synthesis.md)은 작성되지 않음 — write_scope {} 제약, 결함 아님.
[13] source truth, 성공/품질 판정, Movement 권한 — 본 반환은 어느 것도 보유·행사하지 않음.

===== observed_evidence =====
[0] INPUTS READ IN FULL: work/step-outputs/postmortem-deep-0706a-design-attempt-1/step-output.json (A, adapter:claude-local), work/step-outputs/postmortem-deep-0706a-design-2-attempt-1/step-output.json (B, adapter:codex-local), work/step-outputs/postmortem-deep-0706a-design-3-attempt-1/step-output.json (C, adapter:codex-fugu-local), plus the upstream merge map work/step-outputs/postmortem-deep-0706a-review-attempt-1/step-output.json.
[1] 대조-사건 회수율 (control-case Case 3, corpus discount rule): 2/3 자력 회수. A = 자력 회수(코드 실측: run.py:585 replace() strip, 3개 side channel, fingerprint, repair 위치 — git 없이). C = 자력 회수(코드 + git show cc4ac292 실측; 추가로 checker 2-of-3 커버리지 갭 신규 실측). B = 코퍼스 전달 회수만('recovered as a corpus claim; not independently re-proven from primary logs') → 코퍼스의 할인 규칙에 따라 B의 신규 진단 주장에 할인 표기. 실측 결과 B 단독 신규 주장만으로 지탱되는 처방 행은 없음(B 주도 R4행은 C의 타임스탬프 실측으로 교차 지지).
[2] 합의 (3/3): (i) Case 1 repo-root binding은 실재, cli.py:13 코드 좌표 일치, 클래스 폭 실측(A: parents[ 31곳, C: parents[2] 44파일 — 서로 다른 grep 패턴, 모두 실측); (ii) Case 2 '19:03 동시 클러스터'는 유령 — 실측 19:06:02Z/19:07:41Z(C만)/19:10:35Z, rc=1 레코드 자체는 실재; (iii) 부재 주장에 탐색 도메인 라벨 의무(A-P6/M1, B-rc-e, C 도메인 라벨) ; (iv) Case 9 freeze 경계는 실재(work 반환 후·팬 수신 3건 후·QA 자식 터미널 없음), root cause 미확정, 증거-포착 선행 처방; (v) Case 6·Case 8 충돌은 3진단 모두 비판정 보존.
[3] 충돌 (진단 간): (i) Case 2 축 귀속 — C는 provider spend-limit(Agent/provider-runtime) 단정 쪽, A는 per-dispatch로 계정전환 단일원인 약화·미확정 유지, B는 분류불능(어댑터 불투명)으로 보존; (ii) 5aeaeea vessel 소재 — B는 'tracked checkout·runtime root 모두 미발견'(부정 주장), C는 canonical tree /Users/smith/projects/BRICK에서 2회 발견, review는 tracked tree에서 2회 확인 → B의 부정 주장은 도메인 드리프트 클래스의 이번-패스 재발 사례; (iii) git 가용성 — A·B는 커밋 내용을 'git 도구 없음'으로 not_proven 처리, C는 git show 실행 실측으로 함대 공통 맹점을 반증; (iv) 클래스 폭 수치 31 vs 44 (패턴 상이, 미조정).
[4] 고유발견: A = M1(진단 장치 내부의 R1 재발 프레임), partial-replace 감사 후보 좌표(walker_kernel.py:917/950/1375, walker_hold.py:263/399-401 — carry 루프 부재 실측), 점수리 클래스 미폐쇄 프레임. B = 축 소유권 표(Admission/Agent/Brick/Evidence/Link/Support), erg6 3중 참조 동일성 보존, 어댑터 불투명성 분류 처방. C = checker 2-of-3 갭(check_building_operator_driver0.py:2786/2791에 _report_event_observations 단언 부재 — 살아있는 강제 갭 신규 실측), 'git 도구 없음' 반증, Case 2 중간 타임스탬프 19:07:41Z, Case 9 'lane 미실행' 축소(work lane은 실행·반환됨), 5aeaeea canonical tree 소재.
[5] 클로저 교차 관측 (A의 M-예측 대조): A가 '타 진단자가 놓쳤을 것'으로 예측한 M1(도메인 규율)·M3(유령 동시성)은 B·C 모두 잡아 예측 불성립; M2(점수리 클래스 미폐쇄)는 부분 성립 — B는 미감사, C는 오히려 더 정밀한 checker 갭을 실측.
[6] 반복 패턴 표 (클래스 → 사건 → 축 귀속 후보; 억지 클래스화 금지 적용): [K1 암묵적 파일시스템-정체성 바인딩] 합의 구성원 = Case 1; Case 4·7 은 A 단독 편입 후보(B·C는 별건 유지 → 후보 표기만); 축 후보 = Support 툴링(B·C 표현) / Engine(A 표현), 동일 이음새. [K2 frozen-replace side-channel strip] Case 3(대조, 점수리 착지) + 미감사 remint 좌표들; 축 = Support/operator; 잔존 = checker 2-of-3 갭(C 실측). [K3 탐색/증거 도메인 드리프트] Case 6 소재 주장 + 진단 함대 자체 6/8 드리프트 + B의 이번-패스 부정 주장(살아있는 재발); 축 = 진단 규율/Support 증거 투영. [K4 어댑터 rc=1 불투명] Case 2 3건; 축 귀속 자체가 열린 충돌. [단독 유지] Case 5(c59d1745 착지, K2에 강제 편입 안 함), Case 6 처분 문서 충돌(문서 거버넌스 별건), Case 8(인간 vs 엔진 이중 후보 열림), Case 9(사망 기전 증거 부재 시까지 단독), Case 4(증거 부족 — /tmp 로그 소실).
[7] 유령/실재 분리: [실재] Case 3 기전·수리, Case 1 바인딩, Case 5 착지, Case 2 rc=1 레코드 3건, Case 9 freeze 경계·work 반환, 5aeaeea vessel 존재. [유령] '19:03 동시'(3/3 기각), 'git 도구 없음'(C 반증), 'not found anywhere'(review+C 반증), Case 9 '전 lane 미실행'(C가 QA/fan 자식으로 축소). [미확정] Case 8 경계, Case 6 처분, Case 2 인과, Case 4 근인, Case 9 사망 기전.
[8] 처방 후보 표 행 (인체공학 표 행·골 문서 행 후보 — 채택 아님): R1[엔진] repo-root 정체성 가드 + parents[N] 바인딩 레지스트리 체커 (3/3, Case 1·후보 4/7). R2[엔진] 공용 side-channel carry 헬퍼 + 전 채널(_report_event_observations 포함) 체커 (A+C, C 실측 갭, Case 3 클래스). R3[엔진/증거] 팬 이음새 driver-사망 증거 포착 + 수신-후-터미널-부재 시 loud HOLD (3/3, Case 9 — watchdog 이전에 증거 선행). R4[어댑터 증거] 비밀 아닌 오류 분류 + alias 해석 증거 + 레코드별 타임스탬프 보존 (B 주도 + C 실측 교차지지, Case 2). R5[진단 규율] 부재 주장 탐색 도메인 라벨 의무 (3/3, K3). R6[운영 규율] 처방-착지 추적 레코드 (A+C, Case 8). R7[운영/kernel doc] 사건 처분 단일소스 문서 선언 (A, Case 6). R8[함대 방법] lane 지시문에서 거짓 'git 도구 없음' 자기제한 제거 (C 단독, C 실측 근거).
[9] 차량 관측 (모델-레인): design lane과 이 closure lane의 selected_model_ref = model:claude:claude-fable-5; discipline:model-lane-matching은 fable5를 Building lane 모델에서 제외 선언 — Agent축 이탈로 표면화(스미스 큐 참조), 판정 아님.

===== parent_goal_delta_status =====
{'closed_delta_refs': ['work-statement:합의-충돌-고유발견-분리', 'work-statement:반복-패턴-표', 'work-statement:유령-실재-분리', 'work-statement:대조-사건-회수율-명시-할인표기', 'work-statement:처방-후보-표행-형태', 'work-statement:억지-클래스화-금지'], 'evidence_refs': ['work/step-outputs/postmortem-deep-0706a-design-attempt-1/step-output.json', 'work/step-outputs/postmortem-deep-0706a-design-2-attempt-1/step-output.json', 'work/step-outputs/postmortem-deep-0706a-design-3-attempt-1/step-output.json', 'work/step-outputs/postmortem-deep-0706a-review-attempt-1/step-output.json'], 'matched_delta_refs': ['work-statement:합의-충돌-고유발견-분리', 'work-statement:반복-패턴-표', 'work-statement:유령-실재-분리', 'work-statement:대조-사건-회수율-명시-할인표기', 'work-statement:처방-후보-표행-형태', 'work-statement:억지-클래스화-금지', 'work-statement:판정금지-미해결-concern'], 'missing_delta_refs': [], 'open_delta_refs': ['case-9-root-cause', 'case-8-attribution', 'case-6-disposition', 'case-2-causality', 'case-4-root', 'prescription-rows-adoption', 'synthesis-artifact-landing'], 'unknown_delta_refs': ['31-vs-44-count-divergence-cause', 'erg6-triple-reference-identity']}

===== proof_limits =====
[0] support evidence only
[1] not source truth
[2] not success judgment
[3] not quality judgment
[4] not Movement authority

===== remaining_delta =====
[0] 종합 아티팩트의 kernel 문서 착지(후보 경로: project/brick-protocol/status/kernel/postmortem-deep-0706a-diagnosis-synthesis.md) — 쓰기 스코프 가진 후속 빌딩 필요.
[1] R1-R8 처방 행의 채택/우선순위 처분 (인간/Link 소관).
[2] Case 9 사망-신호 증거 포착 슬라이스 (3/3 합의 선행 항목).
[3] Case 8 착지 레코드 수색 (git 가용성 실측됨 — 즉시 수행 가능해진 갭).
[4] Case 6 처분 단일소스 선언; erg6 3중 참조 동일성 해소.
[5] checker 2-of-3 갭 점수리 (C 실측, 좁고 구체적).

===== returned_summary =====
local CLI Agent Adapter returned support evidence

===== selected_adapter_ref =====
adapter:claude-local

===== selected_model_ref =====
model:claude:claude-fable-5

===== transition_concern_evidence =====
{'binding': False, 'concern_kind': 'verification_gap', 'concern_ref': 'transition-concern:postmortem-deep-0706a-closure-open-conflicts', 'not_proven': ['Case 9 사망 기전·Case 4 근인·Case 2 인과는 현 증거로 검증 불가 (증거-포착 선행 필요).', 'Case 6·Case 8 처분 충돌은 진단 3건과 merge map 모두에서 비판정 보존됨 — 인간/Link 처분 대기.', 'B의 대조-사건 미자력회수와 5aeaeea 부정 주장은 도메인-드리프트 클래스의 재발 관측이며, 상류 결함 재현으로 확정된 것은 아님.'], 'proof_limits': ['support evidence only', 'not source truth', 'not success judgment', 'not quality judgment', 'not Movement authority'], 'reason_refs': ['work/step-outputs/postmortem-deep-0706a-design-attempt-1/step-output.json', 'work/step-outputs/postmortem-deep-0706a-design-2-attempt-1/step-output.json', 'work/step-outputs/postmortem-deep-0706a-design-3-attempt-1/step-output.json', 'work/step-outputs/postmortem-deep-0706a-review-attempt-1/step-output.json'], 'related_boundary_refs': []}

