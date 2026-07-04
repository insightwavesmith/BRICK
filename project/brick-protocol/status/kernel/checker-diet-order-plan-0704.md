# §4-4 체커다이어트 순서안 (0704 — s44-orderplan-0704a 수확, Smith 확정 게이트 입력)

Status: support evidence only. 87라벨 전수 재계수 + 배치 순서 제안 — 실행은 Smith 확정
후. 원문(전수 인벤토리·패밀리 매핑 포함): buildings/s44-orderplan-0704a work 반환
handoff_refs. source truth·성공 판정·품질 판정·Movement 권한 아님.

## 재계수 결과 (독립 검증 — QA 렌즈 2 통과)

- **정본 87 CONFIRMED**: hardening.yaml 라벨 행 99 − split 사본 12(builder_composition
  8 + intake_adapter_gate 4, 전부 원본과 교집합·drift-check 부재) = 원본 전용 87.
  agent_resource_boundary의 1개는 원본에 없는 신규 라벨.
- LOC 미세 drift 정정 2건(hardening 4243행 등 — 라벨 수는 전부 정확).
- 정본 §3 "mutation-RED 기구 없음"은 **STALE 정정**: adapter_error_check.py:1591
  probe_mutation_red 선례 실재. 단 러너별(.py 엔트리포인트 poison) 기구라 "라벨별"
  요구와 입도가 다름(아래 Smith 결정 1).

## 핵심 전략 판단 — §4-2 본대와의 창 배타 (실측 근거)

파일 레벨은 비충돌(§4-4=프로파일 YAML, §4-2=case_runners.py)이나, **87라벨 러너 전량이
case_runners.py에 정의**(18 패밀리 grep 실측) → §4-2가 러너 패밀리를 이동/재클러스터하면
라벨 이동의 mutation-RED 베이스라인이 흔들린다. **권고: §4-2 본대 선행, §4-4 라벨-이동
검증 창은 해당 러너 패밀리 안정화 이후로 직렬화.** 특히 Batch 3~5(carry/materialize/
compose)가 §4-2 최다 접촉 러너군.

## 배치 순서안 (저위험 선행)

| Batch | 내용 | 위험 |
|---|---|---|
| 0 | 이미이동 12라벨의 RED witness + drift-check 확보 → 그 후에만 원본 삭제 | 최저(신규 표면 0) |
| 1 | agent_packets 5 + small_intake 3 → 신규 agent_packet_boundary + intake 확장 | 저 |
| 2 | declared_step_template 16 → 신규 step_template_boundary | 중 |
| 3 | carry_engine 14(고아 후보) → 신규 carry_boundary | 중고 — §4-2 배타 민감 |
| 4 | materialize_engine 20 → builder_composition 확장 | 고 |
| 5 | compose_BAL 31(최심부·최대군) → 신규 compose_boundary | 최고 — 최후 |

- 게이트(매 Batch): 신규/확장 프로파일 green + --all 캐리 증명 + 이동 라벨별
  mutation-RED witness + **삭제와 core.yaml:77-80 allowlist 제거는 동일 변경으로 직렬**.
- 병행 원칙: 신규 프로파일 저작=병행 가능(서로 다른 새 파일) / 원본 삭제+allowlist=직렬.

## Smith 결정 지점

1. **라벨별 RED probe 기구**: 선례는 러너별 poison — 라벨별 요구를 충족하려면 케이스
   픽스처/기대치 수준 poison 기구를 새로 설계해야 함. (러너별로 완화 vs 기구 신설)
2. **창 배타 방식**: §4-4 전면 직렬(§4-2 본대 완주 후) vs 패밀리별 게이팅(안정화된
   패밀리부터 Batch 진입). Batch 0~1은 §4-2 민감도 낮아 조기 진입 후보.

## not_proven (레인 정직 선언)

이동/중복 라벨들이 실제로 "이빨을 가진다"(행동 검증력)는 것 — 이 조사는 소속·수치·러너
위치의 실측이며 라벨별 검증력은 Batch 0의 witness 확보가 증명한다.
