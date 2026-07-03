# P8 바운디드 도그푸드 프로브 (0703 — 현행 엔진 첫 증거)

Status: support evidence only. COO 운영자 프로브(프레시 clone HEAD=e69ef935, 프레시 HOME/BRICK_HOME,
codex 자격 복사 캐비앗은 P7과 동일). 0630 캡스톤(폐기된 --graph 경로) 이후 현행 공식 DSL 경로의
첫 P8 증거. 목적 = 갭 추출.

## 주문 3건 결과

| 주문 | 모양 | 결과 | 판정 |
|---|---|---|---|
| 1. 필수 형상 재현 | 조사(work)→fan(code-attack-qa, axis-attack-qa)→closure | 4레인 완주 → #17 게이트 HOLD(work kind=쓰기 계약인데 무diff) → **고객 forward 처분 → complete** | 기계는 설계대로. **UX 갭 G-1** |
| 2. write 실무 | work(write=True)→closure, 아티팩트 문서 산출 | **complete** + 커밋 83497c72(support/docs/references/p8-dogfood-0703.md +20줄) | ✅ 순수 통과 |
| 3. 증명 사이클 | work에 proof_obligations 2건(1건 고의 불가능) | support 실측 → **기계 반려(transition-concern:proof-obligation:...) → 자동 재파견 ×5(예산) → 소진 후 사람 HOLD** | ✅ 오늘 랜딩한 사다리 전체가 설계 그대로 라이브 작동. **UX 갭 G-2** |

엔진 결함: **0건.** 세 프론티어(HOLD/complete/paused)가 전부 의도된 상태였고, 고객 처분으로 풀렸다.

## 추출된 갭 (P8의 산출물)

- **G-1 (UX/문서)**: 읽기 전용 주문을 `work` kind로 내는 것이 자연스러운데, work kind는 계약상
  쓰기 선언이라 무diff 완주가 게이트 HOLD로 선다. 고객 문서(quickstart)가 조사용 kind 또는
  forward 처분 절차를 안내해야 한다. 엔진 수정 불요.
- **G-2 (UX/문서)**: 예산 소진 HOLD에서 고객이 할 일(raise/stop/선언 수정)이 안내 표면에 없다.
  결과 요약 패킷 또는 문서에 처분 안내 노출 후보. 엔진 수정 불요.
- 캐비앗 지속(P7 동일): 브랜뉴 인간 auth transcript·provider 신뢰성 반복은 미증명.

## 운영자 대조

- 요약 패킷(summarize_building_result — 0703 랜딩분) 실전 사용: 3 vessel 판독 전부 이 한 호출로.
- 주문 2 diff 실물: +20줄 1파일(선언 스코프 안). 주문 3 재파견 횟수: work attempt 6(=초회+예산5).
- 프로브 루트: /tmp/brick-p8-dogfood-20260703T175429 (tmp — 로그 원문 보존 중, 재부팅 시 소실).
