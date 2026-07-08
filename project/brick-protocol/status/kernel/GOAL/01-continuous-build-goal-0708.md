# 연속 시공 골 — 남은 페이즈 (0708)

Status: support evidence only. 이 문서는 source truth·성공/품질 판정·Movement 권한이
아니다. Smith가 0708에 지시한 "지금 있는 작업들 빌딩으로 쭉 이어서, 골로 잡고 완료될
때까지"의 연속 시공 트랙을, 원장(walk-results-adopted-0707.md §T/§V/§R/§S-v2/§T-v2)에
이미 확정된 순서 그대로 기록만 한 것이다. 판정·채택은 Smith 몫이고, 개헌 문안은 human
gate다.

## 정본 관계

- **source truth = 원장** `walk-results-adopted-0707.md` (§R 개헌, §T-v2 발주 v2, §S-v2 route v2, §V 병렬 전략).
- 이 문서는 원장의 파생 support 문서. 원장과 충돌 시 원장이 이긴다.
- 0627 고객-준비 골(`00-GOAL-OF-RECORD.md`, P0~P8 + 주말 Codex/Gemini 캐스팅)과는 **다른 축**이다. 그건 역사 보존, 이건 지금 살아있는 연속 시공 트랙. 섞지 않는다.

## 골 한 줄

resume 근본(import 이중신원)을 개헌급 구조통일로 없애고, 그 위에 발주/route 아키텍처
v2를 신규 파일 위주로 시공해 팬아웃(병렬 시공)을 근거 기반으로 되살린다. 각 빌딩 착지
후 다음 발주, origin 착지·격차0 확인하며 단일 연속 트랙으로 완료까지.

## 현행 캐스팅 (원장 §M·§W 최종형)

```text
기획(design/deep-design): 기본 opus-4.8 xhigh (§W — fable5는 명시 캐스팅 클래스로만 잔존, 토큰 소진 임박)
work(시공):               opus-4.8 xhigh (단순~중간) + fugu (복잡·얽힘·엔진급)
QA:                       전부 opus-4.8 xhigh (code-attack/axis/evidence) + code QA·closure는 codex 렌즈
review:                   gemini
```

- fugu 캐스팅 = **timeout 최소 10800초(3h) 세트**로 발주 (§U — 푸구는 품질 상위지만 느려서 성급한 timeout이 레인 사망).

## 병렬 규율 (원장 §V)

- 병렬의 진짜 창 = **§T Phase 1~5** (신규 파일이 축별로 흩어져 비충돌). 여기서 fugu 느림을 회수.
- 병렬 발사 전 `write_scope` 교집합 실측 필수. `brick_protocol/support/checkers/` 겹침이 최빈 충돌 — 겹치면 순차.
- **착지는 push 직렬화** — 병렬 시공해도 착지는 한 줄. 병렬은 시공 벽시계만 절약.
- 억지 병렬 = 착지 게이트 지문 오염 리스크(0702 실측)가 이득 초과. 비충돌 확인된 것만 병렬.

---

## 연속 골 순서 (0708) — 상태판

원장 §V:279 "현 연속 골 순서"를 페이즈로 고정. ✓=착지(origin 또는 로컬 main), ▶=진행중, ☐=대기.

| # | 페이즈 | 상태 | 근거 |
|---|--------|------|------|
| ① | 워크트리/repo 정리 | ✓ | (위생, 0708) |
| ② | 소형 필수 (게이트 .DS_Store 영구수리 + Rule13 durable evidence 체커) | ✓ | `03b6588c4` origin |
| ③ | fable5→opus 캐스팅 전환 | ✓ | `1bd459e2d` origin, §W 격리 --all 55 green |
| ④a | **개헌 이주 C1** (런타임층 최상위 import 캐노니컬화) | ✓ | `af60198cb` 포함, origin/main 착지 |
| ④b | **개헌 이주 C2** (물리구조=패키지구조 통일, 축 4루트 git mv) | ✓ | `7b99b8f7f` origin/main, `--all` rc=0, top-level import 4종 실패 확인 |
| ④c | **개헌 이주 C3** + 문서/개헌/human gate 정리 | ▶ | C2 코드 착지 완료. GOAL/handoff/order/route 상태문서 갱신 중. Smith human gate 남음 |
| ⑤ | **§T Phase 1~5** (발주 v2 신규 파일 — ★병렬 창) | ☐ | 개헌 착지 후 |
| ⑥ | **§T Phase 6~8** (walker v2, =§S-v2 흡수 — 최고위험) | ☐ | Phase 1~5 후 |

**착지 결과(0708 C3 갱신)**: C1+C2는 `7b99b8f7f`로 origin/main에 착지 완료. 과거 “1랜딩 대기” 문구는 C2 착지 전 운영 계획이었고, 현재는 C3 문서/human-gate 정리만 남았다.

---

## ④ 개헌 이주 (§R) — C1/C2 착지 완료, C3 문서/human gate 진행

**목표**: 축 4루트(brick/ agent/ link/ support/)를 `brick_protocol/` 밑으로 이동 + 코드·프로파일·데이터·문서의 축 경로 참조를 전부 `brick_protocol/` 프리픽스로 정합 → `--all` 55 green. **이중신원 소멸(최상위 import 실패)이 성공 기준**. 0708 현재 C1/C2는 `7b99b8f7f`로 완료.

**성공 기준 (완주 시 COO 게이트 검증 항목)**:
1. 격리 `--all` 55 green 독립 재실행 (work 자기보고 불신)
2. 이중신원 소멸 = 최상위 `import support/brick/agent/link` 전부 시끄럽게 실패
3. `import_identity_modes` 프로파일 green
4. `check_package_path_admission` strip 방식 정합 (상수 프리픽스 오염 없음)
5. git mv 이력 보존 (rename detection)


### C3 용어 메모 — 개헌 / human gate

```text
개헌 = BRICK의 운영법/기본 문서가 새 현실을 공식으로 인정하게 고치는 것.
human gate = 자동으로 확정하지 않고 Smith가 “이 문구/방향 맞다” 하고 확인해야 넘어가는 문.
```

C3의 성격은 코드 이동이 아니라 문서와 운영 언어 정리다. C2에서 실제 active root가
`brick_protocol/brick`, `brick_protocol/agent`, `brick_protocol/link`, `brick_protocol/support`로
바뀌었으므로, 골/핸드오프/개헌 문안도 이 현실을 따라야 한다.

### C1/C2 착지 증거 (0708)

```text
commit: 7b99b8f7fd4e00a94d797620c4905afd9f957f7c
origin/main: pushed
post-C2 code status: clean before C3 docs were restored
compileall brick_protocol: rc=0
import brick_protocol.support.operator.cli: rc=0
top-level import support/agent/brick/link: rc=1 each (expected fail)
check_profile.py --all: rc=0, passed_count=55
```

남은 C3 human gate 후보:
1. AGENTS.md의 Active physical roots 조항은 현재 코드와 맞는다.
2. BRICK-CONSTITUTION.md에 별도 물리 루트 조항을 추가할지 여부는 Smith 확인 필요.
3. 이 GOAL 문서와 handoff 문서가 C2 이전 실패 기록을 보존하면서도 현재 완료 상태를 분명히 말하는지 Smith 확인 필요.

**개헌 문안 = human gate**: AGENTS.md:76-88 물리루트 조항 반전 + path rebase 표, BRICK-CONSTITUTION.md 물리 언급 — 빌딩은 **초안만**, 채택은 Smith.

**3시도 이력 (교훈)**:
1. COO 직접(격리본 일괄+--all): 경로 개정 3000+건 상호 간섭 → 층간 진동 실패.
2. fugu 0708a→0708b: 531파일 대부분 green, 그러나 QA가 --all rc1 잡아 미완처분 → **작업물 소멸 2회**.
3. **작업물 소멸 근본 = `cli build --graph-decl`의 proposal-approval 분기가 미완 시 WIP 앵커 없이 워크트리 자동처분** (§X-결함). run_building_plan park/stop 경로에만 앵커 있음. 스킬(brick-task-author §6)이 "완료 시 워크트리 자동처분 — 반드시 회수"를 명시 경고했으나 COO가 무시.
4. **0708c = 소멸방지 감시 걸고 재발주 (현재).** patch 스냅샷 `/private/tmp/migrate-0708c-snapshots/` — ★절대 삭제 금지.

---

## ⑤ §T Phase 1~5 (발주 아키텍처 v2, 신규 파일 위주) — ★병렬 창

원장 §T-v2 채택. 출처 `BRICK_order_architecture_v2_existing_overlay.md` (codex, COO 코드대조 재검증 완료 — 인용 file:line 전수 실측 일치, 피드백 4건 해소).

```text
P1 Schema        brick_protocol/brick/order·plan_card·plan_lock·profile, brick_protocol/agent/verification, brick_protocol/link/route_scope
                 (신규 파일, 개헌 비충돌 / 단 concern_kind 봉인 8종은 v2가 유지 — detail_code는 observed_evidence 안)
P2 Profile Registry + Shape Compiler   brick_protocol/support/operator/workflow_profiles·building_shape_compiler
P3 Plan Card + Plan Lock               (declared-plan revision chain read view — 새 상태 아님)
P4 Blind Pack Builder                  brick_protocol/support/operator/blind_pack
                                       (verdict 은닉 / 사실주장 made_changes·changed_files·diff 노출 — code-attack-qa fake-landing 방어 유지)
P5 Gate Digest Builder                 brick_protocol/support/operator/gate_digest·coo_gate_view
```

**병렬 규율**: P1~P5는 축별 신규 파일이라 격리 워크트리 3~5개 동시 발사 가능(§V). 단 P4~P5는 brick_protocol/support/operator 만지므로 겹침 점검. 시공 캐스팅 work=fugu/opus-4.8.

**v2 핵심 성과** (v1 대비): casting tier/lens 통합(v1 공백), §15 작업자 금지 14개(재발명 명문 차단). v1은 인용 틀림(§T-정정), v2는 코드 읽고 씀.

---

## ⑥ §T Phase 6~8 (route v2 + walker v2) — 최고위험

원장 §S-v2 = §T Phase 6~7로 흡수. 출처 `BRICK_common_route_architecture_v2_existing_extension.md`.

```text
P6 Common Route Policy (=§S 흡수)   brick_protocol/link/route_policy·default_common_route·default_targeted_repair
P7 COO Disposition + HOLD 연결      brick_protocol/link/transition·walker_resume·walker_kernel = ★13모듈 SCC 접촉 (최고위험)
P8 Checkers (10종)                  concern seal parity·blind pack partition·fake-landing preservation·
                                    carry-forward basis·route_scope authority·no_dev_reroute_on_verification_gap 등
```

**순서 제약 (실측)**: P7이 walker_kernel(3053줄/26모듈 의존)/walker_resume 접촉 = arch 검수의 13모듈 SCC 한복판 → **개헌 이주 착지 후**가 안전선. walker v2는 checker green + human gate 후 최고위험 격리.

**§S-v2 4핀 (시공 입력 승계)**:
1. 자동화 상한 낮음 — walker_fan_in 자인(data-dependency graph 부재) → 초기 목표 = Level 2(COO 승인 부분재실행), 전자동 아님.
2. concern_kind = 봉인 8종 유지 + detail_code는 1급 승격 human gate.
3. delta QA = verdict 은닉/factual 노출 + **머지 직전 빌딩은 full-QA 백스톱**.
4. 개헌과 순서 = 개헌 착지 후.

**남은 시공검증(설계결함 아님)**: route_replay_plan 신규필드(live_retry_refs·automation_level·requires_coo_approval)를 route_materialization `_reject_forbidden_keys`가 unknown key로 막는지 = Phase 2에서 확인.

---

## 대기열 곁가지 (연속 트랙 밖, 개헌 착지 후 별건)

원장 §O:168 — 착지 열차 소진 후 발주:
- preset-host-autodetect (소형, init 기본 host first-ready 자동감지 + pre-walk fail-fast)
- P1 recon → 수리 2단 (TCC/claude 신뢰, HOME 격리 신선상태 재현)
- §N 배포 경계 deep-design (클린배포 repo, 캐스팅 재지정 — fable5 부재)
- P2b 프리셋 티어 어휘 deep-design (프리셋 리터럴 49행 제거, 캐스팅 재지정)

## 다음 세션 판정 대기 꼬리

- **fable5 은퇴**: 토큰 소진 임박 → "기획=fable5" 조항 재지정 (§W에서 기본값은 이미 opus 이동, 명시 클래스만 잔존).
- **§T-정정 → v2 채택**: v1의 표면평가 실수 교훈 = "코드 안 읽고 문서 믿기" 금지. v2는 코드대조 완료.

## Proof Limits

이 문서는 다음을 증명하지 않는다:
```text
개헌 이주 C2 완주 (완료 — `7b99b8f7f`, origin/main, `--all` rc=0)
발주/route v2 시공 성공 (설계 채택일 뿐, 시공은 개헌 착지 후)
Phase 6~8 walker v2 안전성 (13모듈 SCC 최고위험, human gate 필요)
각 페이즈의 FORWARD/HOLD 판정 (판정은 Smith·게이트 실측 몫, 이 문서는 순서 기록만)
```
