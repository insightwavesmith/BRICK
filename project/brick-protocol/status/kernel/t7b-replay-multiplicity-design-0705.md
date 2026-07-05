# t7b 설계 초안 — resume replay 다중-처분 한계 (엔진 불가침면, Smith 게이트)

Status: 설계 조사·발주-준비 초안. **레인 발주 불가 — walker_kernel.py 불가침면**. source truth
아님. 수리 방향·위험만 제시, 시공 방식(엔진 직접 vs 인접 우회)은 Smith 결정.

## 결함 (0705 심야 실측 3회 재현)

resume replay가 처분 이력이 있는 빌딩의 재개를 거부한다:
```
walker_kernel.py:1749-1753 (_write_deferred_frontier 내부)
  previous_disposition = _resume_observation_for_hold(resume_seed, prospective_hold)
  if previous_disposition is not None:
      if previous_disposition.get("disposition_action") != "forward":
          raise ValueError("resume replay encountered an already-disposed recorded HOLD
                            for {step_ref!r} with unsupported prior disposition {...}")
```
= 이전 처분이 **forward가 아니면**(reroute·stop 등) 재개 replay가 무조건 거부.

## 봉쇄 실측 (이 결함이 막는 것 — 전부 산출·증명은 확보, "완주 도장"만 미완)

| vessel | 상태 | 산출 확보 |
|---|---|---|
| t10-first-drive-0705b | rev-2 재파견 거부(사건 11) | 기계 전 체인 실증·발견 산출·개정 2장 체인 (runbook §5) |
| bundle11b-walkeradj-0705a | reroute 이력 → 재개 거부, 정정경로도 옳게 거부(걸음-중 갭) | endline 게이트 체커 + onboard 내용검사 (샌드박스 diff, D1·D3 impl) |
| t1s2v3-shapefilter-0704a | resume divergence(seeded walk가 처분 미적용 완료) | 대체됨(v4) — 종결만 필요 |
| wsallow·engine-smalls | 처분 이력 + 장부꼬리 | 대체·수확 완료 — 종결만 필요 |

## 수리 방향 후보 (Smith 판정 — 위험 병기)

- **A. 멱등 재적용(권장 후보)**: forward-외 처분(reroute/stop)도 replay가 **이미 적용된 것으로 인지하고 통과**(재적용 없이 continue). 근거: forward 분기(:1755-)가 이미 splice+continue 하는데, 비-forward는 그 관측을 "미지원"으로 거부만 함 — 관측 자체는 있으니 "재적용 스킵" 대칭 확장. 위험: stop/reroute의 의미가 forward와 달라 splice 로직이 비-forward에 부적합할 수 있음(설계 검증 필수).
- **B. 처분 이력 스냅샷 분리**: replay 시드에 처분 이력을 명시 상태로 넣어 "이미 처분됨"을 정상 종료로. 위험: resume_seed 스키마 변경(광범위).
- **C. 우회(비-엔진)**: 처분 이력 있는 빌딩은 fresh 재발주만 — 현행 관행 유지, 엔진 무접촉. 위험: 산출 폐기·재주행 비용(오늘 밤 실측 비용).

## 경계 (엔진 수리 시)

`_run_dynamic_graph_walker` 및 그 상태기계 불가침 원칙 하에서, 이 수리는 **_write_deferred_frontier의
replay 관측 분기 1점**이라 국소적이나, walker 재개 정합성의 심장부다 — 기계 게이트(비-forward
처분 replay RED→GREEN 쌍 + 격리 --all) + Smith 복귀 조건 필수. 0702 결함 가족 ②(자기잠금)와
동족이라 함께 볼 것.

## Smith 결정 요청
①수리 착수 여부 ②방향(A/B/C) ③엔진 직접 시공을 COO 게이트 하에 허용할지 vs 설계만 확정하고
시공은 별도. 권고: A방향, 엔진 국소 수리(walker_kernel:1749 분기)를 COO 기계게이트+Smith 복귀
조건 하에 — 이게 오늘 밤 최다 봉쇄를 뚫는다.


## 착수 재판단 (0705 심야 — COO 정밀 판독 후)

Smith "열쇠 해제" 하에 A방향 직접 시공을 착수했으나, walker_kernel 정밀 판독으로 **A방향이
국소 1점 수리가 아님**을 확정:
- forward-disposed replay는 "선언 후속 splice+continue"(walker_kernel:1755-1760).
- 그러나 실측 봉쇄는 전부 **reroute×2**(0705a·0705b 원장 확인). reroute 적용(원 분기 :1826)은
  forward와 다르게 **reroute-타깃 노드를 splice_after_current로 삽입 + node_landings 증가 +
  reroute-adoption 레코드 생성**. 즉 replay 미러링은 forward 분기 재사용이 아니라 reroute
  적용의 정합 재현이 필요 — 상태기계 다지점.
- 위험: 잘못 미러링하면 walker가 조용히 오작동(중복 splice·landing 카운트 오류·adoption
  레코드 불일치). 불가침면에서 이 리스크는 규율상 "3라운드 진동 전 중단"보다 앞서 회피 대상.

**COO 처분: A방향 직접 시공 중단, C방향(fresh 재발주 우회) 채택** — 봉쇄 5기는 fresh 재운전
(T10)·재발주(11B·주차)로 우회. 오늘 밤 실측 비용은 재주행뿐이고 산출·증명은 이미 확보됨.
A/B방향 엔진 수리는 **별도 세션의 전용 설계 슬라이스**로 이월(walker_kernel 상태기계 정밀
설계 — reroute replay 재적용 정합 + RED/GREEN + Smith 복귀). 이 판단은 "원인 크기 = 수리
크기"(헌법 진단 4)와 "resume 반복 실패 시 fresh 우회"(운영 규칙) 정합.
