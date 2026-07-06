# 0707 완주 3빌딩 채택 정본 — 사고법 v2 합의 + Smith 판정 6건 + 후속 발주 근거

> 지위: 0706n 3빌딩(graph-thinking-design·compress-s1·onboard-seq-audit) 완주 산출의
> **채택된 부분**만 정리한 발주 근거 문서. 원문 전체는 각 빌딩 vessel의
> `work/step-outputs/*/step-output.json` (brick home `project/brick-protocol/buildings/` 하위).
> 이 문서는 support 증거이며 판정 권위가 아니다. 판정(채택)은 Smith 0707 확정.

## A. 사고법 v2 — 3인 이종 설계(fable5∥푸구∥codex, 상호 열람 금지) 합의

### A1. 3/3 만장일치 (전원 독립 도달)
1. **신규 프리미티브 불요** — 기존 build/fan/hold/expand/resume 프리미티브 안에서 해결. 신규 조립기·런타임 상태·Movement 리터럴·자동발사 없음.
2. **fan 폭은 발사 전 리터럴 확정 + 상한 3.** 폭 = min(신호 사다리, 비충돌 파티션 수, 겹침(κ) 하향, 3). 사다리는 천장이지 바닥이 아님. write-set 겹침 → 폭 1로 붕괴.
3. **2단 발주 표준형** = build1(설계 → 수렴 홀드) → 사람/COO 판독 → 2단은 새 선언(build/resume). `expand()`는 dry-run 증거 전용 — 발사·승인·걷기·Movement 선택 금지.
4. **partition_plan은 design/deep-design 반환 계약 필드** (런타임 숨은 상태 금지). 현 return 템플릿엔 아직 없음 — 이번 A 조각이 추가한다.
5. **채택 전 체커 동반 필수** — graph_draft/plan_expansion/return-shape drift/profile 기존 메커니즘으로 핀.

### A2. 채택된 partition_plan 스키마 (fable5 D3 원안 채택, deep-design 먼저)
`brick/templates/bricks/deep-design/return.yaml`에 사전 선언되는 신규 필드:
```
partition_plan:
  width_decision: {n: int(<=3), rationale_signals: [...], partition_count: int,
                   kappa_proxy: {overlapping_write_pairs: int, shared_contract_files: [...]}}
  branches: [{branch_id, concern_key, objective, output_format,
              write_set: {allowed: [...], forbidden: [...]}, returns_field,
              sibling_independent: bool,
              casting: {adapter, model, effort, timeout_seconds}}]
  done_line: str
  residual_owner: str
  qa_plan: {lenses: [...], second_verdict_path: str, max_concurrent_xhigh: int(기본2), stagger: bool}
  env_plan: {preflight_probe: bool, provider_risk: str}
  expansion: {attach_to_step_ref, budget_mode: 'per-node'|'aggregate' (XOR), budgets: {...}}
```
일반 design 확장은 실측 후(단계적 — Smith 판정 1). codex Q7 스키마와 실질 동형(필드명 차이만) — 충돌 시 위 원안이 정본.

### A3. 채택된 초안기/체커 규칙 증분 (D5, fable5·푸구 공통안)
draft-time 하드 RED: RED-1 폭>3 · RED-2 branch write-set 교차 · RED-3 deep-티어 캐스팅 timeout<10800s · RED-4 fan branch에 concern_key/objective 부재 · RED-5 2단 초안에 done_line/residual_owner 부재 · RED-6 expansion budget 혼합 모드.
소프트 WARN: WARN-1 xhigh급 QA 동시>2 · WARN-2 얽힘/walker-인접 표면+저티어 work.
각 규칙은 픽스처+변이 RED로 핀(변이가 규칙 삭제 시 프로브가 발화해야 함).

### A4. Smith 판정 (0707 확정)
1. partition_plan 홈 = **deep-design 먼저**(단계적). 2. 첫 조각 = **체커-우선**. 3. held-node 직접 확장 = **봉쇄 유지** + resume 근본 해결 트랙(아래 D절)이 검증기 포함 근본 수리 — 통과 전 2단은 항상 새 선언. 메타지시: 3다이얼(시간→공간→권위)은 COO 실사고 절차, sizing 스킬이 그릇.

## B. compress-S1 — 전제 충돌 실측 (무변경 정직 반환, 2라운드)

- census: `support/checkers/check_*.py` 56파일 중 **32파일**에 모듈-로드 부트스트랩 블록. P2형(ROOT+import_identity 삽입) 10파일, P1형(ROOT만) 7파일. **do-not-touch: `check_import_identity_modes.py`, `check_profile.py`.**
- 공유 헬퍼 좌표: `support/checkers/lib/yaml_subset.py:38-41`의 `_ensure_import_identity`는 repo 루트가 이미 sys.path에 있어야 import 가능 → **부트스트랩 블록을 그 헬퍼로 접는 것은 원천 불가**(닭·달걀). "신규 모듈 금지" 제약 하에서 S1 원안은 성립 안 함이 증명됨.
- baseline `--all` rc=1은 격리 스냅샷의 handoff 문서 UUID(이후 main에서 마스킹 완료) 기인으로 추정 — 라이브 재발 아님.
- **Smith 판정 4 = ⓐ 신규 부트스트랩 모듈 1개 허용**(제약 완화). 사다리 S2~S5 원안 유지. 후속: 신설 모듈은 각 체커 파일 잔여 부트스트랩이 2~3줄이 되도록(자기 위치 기준 sys.path 삽입 → 공유 모듈 import → 나머지 위임). 판단 로직·핀·프로파일 불변, 바이트 감소는 부트스트랩 블록에서만.

## C. onboard-seq-audit — S0~S5 검수 결과 (무변경, 검수표 완성)

- **확정 균열(S0)**: `README.md:45`·`support/docs/references/quickstart.md:107`은 성공 문구 `"5) 설치 점검 완료"`를 기대, `support/onboarding/install.sh`(161-186 영역) 실제 출력은 `"5) brick 진입점 설치 완료 ✅"` — `설치 점검 완료` 문자열은 미출력.
- README(41-73)의 축약 체크리스트 vs quickstart(98-164)의 S0~S5 전체 체크리스트 불일치 — 부분집합 명시 또는 정합 필요.
- README readiness 명령이 `onboard codex` vs `onboard doctor` 중 어느 쪽이 정본인지 미확정 — 구현 실물(`support/operator/cli.py:934-955,1536`) 기준으로 정합할 것.
- 발급 절차 갭 B-G1~G7 + 발급자 의무 8항목 초안은 work step-output에 실재.
- **Smith 판정 5 = 고객 배포는 본 repo 초대 경로**(별도 채널 없음), **발급자 = Smith**. **판정 6 = install.sh를 문서 의도에 정렬**: 설치 후 점검을 실제 수행하고 `"5) 설치 점검 완료"`를 출력하도록 스크립트를 고친다(문서를 스크립트에 맞추는 게 아님). 성공 문자열은 체커로 핀.

## D. resume 근본 해결 트랙 대상 4묶음 (Smith 판정 3 "근본 해결, 구조 잡아라")

1. **resume 엔진 결함 3종**(0702 실측, `resume-defect-mechanisms-0702.md` 정본): ①raise 예산 주입 행을 재개가 안 읽음(소비경로는 실존, 총량 반영 미확정) ②거부된 처분 시도가 원장에 남아 자기잠금(옳은 검증이 persist 이후 실행되는 순서 문제) ③step-output 즉시쓰기 vs raw-return 일괄쓰기 별개 트랜잭션 → 재개 자체 거부(가드는 실존, "거부 후 정정 경로" 선언 부재).
2. **수취 장부 꼬리(T10 클래스)**: agent-received.jsonl 부재 vs agent-return N행 → evidence_incomplete로 원장 종결 불가(fail-closed 자체는 정당). 원장 3+기 실측.
3. **홀드 체인 순환**: 처분 체인이 스텝별 홀드를 다회 통과해야 하는 구조(erg3: 4회 forward)의 근본 정리.
4. **held-node 직접 확장 검증기**: HELD 수렴 노드 위 expand→resume의 append-only 안전성(re-route 차단 여부) — 검증 실험 통과 시 2단 표준형을 직결형으로 단순화하는 반전 경로(사고법 v2 합의의 유일한 엔진 실측 의존점).

부수 대상(같은 가족, 설계 판단에 포함): 증명-예산 HOLD 경로의 WIP 앵커 부재 갭, fake_landing_write_scope_diff_absent의 다회 forward 인체공학.

## E. 초안기 제안측 부재 — 실측 (0707, #15 규칙표 증분 후속 발주의 갭 증거)

resume-rootfix-design-0707a 발주에서 `brick draft`에 준 8답과 초안기 반응 실측 원문:

- 8답: walker_adjacent=yes · size=large · **splittable=yes · file_conflict=no** · failure_cost=high · human_approval=no · termination_shape=doc · difficulty=entangled — 폭 신호가 최대치로 켜진 조합.
- 초안기 산출 모양: **단일 work**(+deep-design 자동 삽입) → QA fan → closure. 병렬 팬은 제안하지 않음.
- rationale 원문 행(그대로 인용): `note-split-candidate | graph shape unchanged (single work node) | 분할 후보: 별도 빌딩 발주 검토 — operator Movement-adjacent`
- 운영자 조치: 선언 파일의 nodes를 fan[design fable5 ∥ 푸구 ∥ codex] → closure(codex)로 수동 교체 후 발사(0707, 정상 개시).

판독: 현행 초안기는 분할 가능성을 **감지**(note-split-candidate)하되 **제안하지 않는다** — 폭 계산(min 규칙)·병렬 설계/시공 팬·2단 표준형 1단 그래프의 자동 제안이 전부 부재(제안측 갭). 거부측(안티패턴 RED-2~6·WARN-1~2)은 gt-checker-slice-0707a 계약분. 수리처 = #15 규칙표 증분 후속 발주(방아쇠 = gt-checker-slice 랜딩): 폭 신호용 9번째 답 + min() 폭 계산 + fan 자동 제안 행. 인체공학 표 등재 = operator-ergonomics-wave-0705.md 행 20.
