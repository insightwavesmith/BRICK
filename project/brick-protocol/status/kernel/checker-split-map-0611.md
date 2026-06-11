# 체커 분리 지도 (REPO-SPLIT 사전 감사, 0611)

Status: SUPPORT RECORD — 레포 스플릿 집행용 분류 지도. 이 문서는 source truth /
success judgment / Movement authority가 아니며, 체커를 변경하지 않는다. 집행은
REPO-SPLIT 단계에서 별도 빌드로 한다.

조사 방법: 워크플로우 3-reader가 13개 프로파일의 모든 규칙 단위(93행)를
PRODUCT-LAW / DOGFOOD-HISTORY / DEV-PROCESS / MIXED로 분류 + 분리 처분 기록.
S1(PROJECT-0)과 동시 편집된 4파일의 행은 provisional로 표시했고, S1이
cf06e7b로 랜딩한 결과(스캔루트 per-vessel 파생·admission per-vessel 술어)는
해당 행들의 "메커니즘은 SHIP" 처분과 일치한다.

## 0. 합계

| 분류 | 행 수 | 의미 |
| --- | --- | --- |
| PRODUCT-LAW | 41 | 제품 법 — 그대로 SHIP |
| MIXED | 29 | 법은 SHIP + 도그푸드 증거핀은 HISTORY-SIDE (대부분 fixture 대체 필요) |
| DOGFOOD-HISTORY | 11 | 1호 역사 기념 — HISTORY-SIDE |
| DEV-PROCESS | 12 | 개발과정 가드 — 대부분 SHIP(싸고 무해), 2건 HISTORY-SIDE |

핵심 패턴: **메커니즘/케이스러너는 거의 전부 제품 법**(인라인 합성 픽스처로 실행됨).
도그푸드 색은 주로 **증거 핀**(0526–0531 빌딩 path_exists / CWC text_contains /
json_required_paths)에 몰려 있다. 분리 = "법은 가져가고, 증거 핀은 픽스처 쌍둥이로
바꿔치기"가 표준 수술이다.

## 1. ⚠ SEVERITY FLAGS — 스플릿에서 조용히 잃으면 안 되는 것 5건

1. **session-id redaction (kernel_checks.run_agent_session_id_redaction)** —
   메커니즘+per-vessel 파생 스캔루트는 제품 SHIP, **allowlist는 비워서** 가져간다
   (6파일/8줄해시 동결 allowlist + archive/support-docs-reviews 정적 루트는 역사행).
   역사 쪽으로 통째 이동시키면 새 사용자 증거가 세션ID 누출에 무방비.
   픽스처: 가짜 UUID 박힌 합성 빌딩파일 1개 RED 단언.
2. **strict plan-boundary (no-retired-adapter)** — core의 전수 sweep은 의도적으로
   관용(allow_retired=True)이라, **strict 변종은 per-profile 행에만 단일 소싱**되어
   있고 지금은 도그푸드 plan 3장 위에서 돈다. 핀을 plan과 함께 버리면 제품 불변식이
   조용히 약화. 픽스처 3종으로 대체: 유효 linear plan / retired adapter ref plan
   strict-RED / allow_retired=true 허용경로 1행.

   **`brick/building_plans/` 처분 명문화 (Smith 0611 "잘 기재해놓고"):** 이 디렉토리의
   옛 플랜 ~16장(authoring 가이드 4 + compact 도그푸드 plan 12)은 **더 이상 입구가
   아니다** — 현행 입구는 preset 단일화(task 문장+preset → 기계가 플랜 생성,
   declared-building-plan.json으로 빌딩 증거 안에 박제; materializer는 명시 preset
   없으면 거부, 옛 문법은 L-LEGACY가 시끄럽게 거부). 남아 있는 이유는 (a) 도그푸드
   역사 (b) 체커 픽스처 — 위 strict 검사가 이 중 3장 위에서만 돈다.
   **순서 강제: 합성 픽스처 쌍둥이를 먼저 만들고 strict 검사를 재지정한 뒤에만
   역사 repo로 이동. 그 전에 지우면 검사 하나가 조용히 죽는다 (가짜 green).**
   (`bricks/plan/`은 동음이의 — 기획 '일감' 브릭 종류라 제품에 남는다.)
3. **link_routing auto_repair_replay_case** — 도그푸드 증거를 가리키는 부분은
   re-point(픽스처 repair/replay plan + trace)로 살린다. 드랍 금지.
4. **native_dispatch posA 증거모양 핀** — 드랍하면 backstop 상실. close-case seam이
   신선 트리를 생성하므로 그걸로 픽스처 재생성 가능.
5. **yaml_subset duplicate-key raise + 러너 무결성 핀** — SHIP (파서 무결성).

## 2. 처분별 지도

### A. SHIP — 그대로 제품행 (41 PRODUCT-LAW + DEV-PROCESS 대부분)

- write-authority 4중게이트 18케이스, hook-registry advisory-only, model-selection
  문법, write-scope default-exclude, provider_preflight no-raise,
  bounded-loop/zeta6/zeta7 가드, driver/onboard/intake 케이스 패밀리,
  materialize/compose/gate_sequence/step_output 케이스, role×lane 매트릭스,
  영수증: 위 행들은 전부 인라인 픽스처 실행 — 도그푸드 의존 0.
- AGENTS.md 헌법 핀 + 엔진 seam text_contains/text_absent 가족 (live 소스 핀).
- DEV-PROCESS 중 SHIP: profiles 디렉토리 allowlist(스플릿 시 13이름 재단),
  legacy tombstone path_absent(재생장 가드, 싸다), check_profile self-pins/self-test,
  install_script_lint(+install.sh와 동행), retired-module 부활가드
  (link/route_templates·route_bindings 부재 = 축모양 규칙이라 여기서만 커버).
- axis_contract_projection 오라클: SHIP하되 ACTIVE_SEQUENCE_CONTROL_DOCS를
  **AGENTS.md만으로 re-point** (CWC·0522 spec 행은 역사행).
- package_path_admission: 법+per-vessel 매처+금지세그먼트 SHIP; brick-protocol
  리터럴 admitted 행·도그푸드 status 가족·archive 박물관 루트는 **데이터 테이블로
  추출해 역사행** (제품 사본은 빈 legacy 테이블).
- check_building_map_graph: 법 SHIP; grandfather 리스트 2개는 역사행(제품=빈 리스트).

### B. SHIP-WITH-FIXTURES — 법은 가져가되 증거핀을 픽스처 쌍둥이로 (MIXED 대부분)

| 표면 | 픽스처 처방 |
| --- | --- |
| strict plan-boundary | ⚠ §1-2 픽스처 3종 |
| session-id redaction | ⚠ §1-1 빈 allowlist + 합성누출 RED |
| building_lifecycle_path_shape | 완전한 빌딩루트 1 + 위반루트 1 RED; cap-boot allowlist :77-99는 역사행 |
| building_map_graph json블록 | 유효 building-map 1 + support-authority 주장 map RED |
| coo_operating_chain 0527핀 | adapter:local로 물질화한 coo-chain 픽스처 빌딩+compact plan |
| preset_building_completion | expected_preset_refs를 공통 11종으로 재단 + human-gated ≥1 + portfolio ≥1 유지 |
| link_routing 0526/0527핀 | 픽스처 repair/replay plan + trace (⚠ §1-3) |
| native_dispatch posA | close-case seam으로 신선 재생성 (⚠ §1-4) |
| read_side_projection 0526/0528/0531핀 | wake-bus 픽스처 빌딩 + ledger/inbox 최소셋 |
| tier_a 풀루트 | tier-a-3axis-conformance-0 전체 루트 픽스처 or 엔진 재생성(빌딩id 파라미터화) |
| structure_template_integrity 도그푸드 픽스처 | p9-dogfood-0601 + prune-0527의 work/*.json 쌍둥이 |

**최소 픽스처 선적 세트 = 부하지지(load-bearing) 빌딩 루트 14개** + status
project-orchestration-ledger.json + inbox 패킷 3 + 도그푸드 plan 파일들 +
basic_qa_repair.yaml. 그 외 1호 빌딩 전부(~140)는 역사 repo행.

### C. HISTORY-SIDE — 역사 repo로 이동

- 0526–0531 도그푸드 빌딩/플랜/CWC 핀 전부 (agent_axis 0528 repair 증거,
  coo-chain 0527, BAR-V2 CWC 핀, p7 archive 핀, museum 스윕 등).
- **pin_estate_integrity + pin_estate_baseline.yaml 통째로** — 피사체(역사핀)가
  전부 역사행이라 제품에선 빈 껍데기. 역사 repo에서 re-baseline.
  (제품 repo에 역사접두 핀을 하나라도 남기면 거기도 re-baseline 사본 유지.)
- 세션ID 동결 allowlist 6건 — 파일과 동행, 제품 사본에서는 **삭제**(이월 금지).
- AGENTS.md "P7 admits the matrix direction" 문장 — 헌법 속 페이즈 기록.
  repoint or 이동 (스플릿 시 Smith 결정 1건).
- cap-boot-4-conversation-dogfood-0521, run-surface-authority-boundary-0529 루트
  (inbox 패킷만 픽스처 선적 or 재생성).

### D. RETIRE-CANDIDATE — 중복 증명 있는 은퇴 후보 (스플릿 전에도 가능)

1. **post_d_surface_recompile_p7의 preset path_exists 10행** — structure_template_
   integrity.yaml:24-37이 같은 10파일+8파일을 핀, 카탈로그 체커가 행동적으로도 강제.
   정확한 중복.
2. **p7 프로파일 자체** — gate.yaml 매트릭스 핀+preset canonical-ref 니들을
   structure_template_integrity로 접고 프로파일 삭제 (페이즈명 프로파일 소멸).
3. **per-profile building_plan_boundary 행들(link_routing 3장, structure 12장)** —
   core 전수 sweep이 같은 validator를 모든 linear plan에 돌림. 단 ⚠ §1-2
   strict-mode 단일소싱 때문에 **픽스처 대체 후에만** 은퇴.
4. catalog_restructure의 p10-delete/old-registry 호환모드 — old registry 경로가
   path_absent로 강제됨을 증명한 후에만.

### E. 이름 청소 (기능 무변경, 페이즈명 → 의미명)

- `post_d_surface_recompile_p7` → (D-2로 소멸이 우선)
- `building_automation` → 도그푸드 빌딩명 유래 — 의미명으로
- `check_brick_template_catalog_restructure` → 카탈로그 법 이름으로
- `tier_a_three_axis_conformance` → 프로파일명에 tier 잔재
- AGENTS.md amendment 명칭(AGENT-PROJECTION-SYNC-0 등)은 헌법 개정 기록이라 유지.

## 3. 집행 순서 제안 (REPO-SPLIT 빌드에서)

1. D(은퇴 후보) 중 1·2 먼저 — 스플릿 무관하게 지금 트리에서 가능, 핀estate 처분 동반.
2. B(픽스처 제작) — 제품 repo 시드 만들 때 1회.
3. A/C 분리 집행 + 양쪽 --all green + ⚠ 5건 생존 확인 FIRE.
4. E 이름 청소는 마지막 (체커 핀 follow-rehome 규칙 적용).

원자료: 워크플로우 wf_017256ed-7ea 결과 93행 (full text는 세션 산출물;
이 문서가 집행용 정본 요약).
