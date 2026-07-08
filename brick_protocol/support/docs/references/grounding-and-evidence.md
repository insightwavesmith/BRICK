# 외부 레퍼런스: Grounding / 증거추적 (영감 backlog)

목적: 외부에서 관찰한 **"grounding"**(출력을 검증 가능한 출처 앵커에 묶기) 자료를 모아 Brick 포지셔닝(정직 증거장부)과 매핑한다.

> ⚠️ **이건 축 코드가 아니라 문서다.** `brick_protocol/brick/agent/link/support` 로직·체커에 0 영향. `grep grounding`으로 재발견하기 위한 노트. (축 코드에 심으면 off-axis 노이즈·second-spec 냄새 → 일부러 문서로만 둠.)

---

## 1. ePapyrus — "문서 데이터 추출에서의 Grounding" (PyMuPDF)
- **URL:** https://epapyrus.tistory.com/462 (PyTorch Korea 경유)
- **기법:** PyMuPDF `search_for()` → PDF 페이지에서 텍스트 위치를 **Rect/Quad 좌표**로 반환. 추출값을 그 좌표에 묶어(=grounding) 환각이 아닌 **결정론적 출처**로 되짚음.
- **해결 문제:** AI 추출은 정확해도 "이 값이 원본 어디서 왔나"를 검증 못 함 → 좌표 앵커로 visual 검증 / RAG 검증 / human-in-the-loop.

### Brick 매핑 (도메인만 다름, 원리는 동형)
| | ePapyrus (PDF grounding) | Brick (evidence ledger) |
|---|---|---|
| 묶는 대상 | 추출 텍스트/값 | Agent/Brick/Link 공개 fact |
| 앵커 | 페이지 좌표(Rect/Quad) | `raw_refs` / `claim_trace` / evidence 파일 |
| 목적 | "원본 어디(where)" | "누가·무엇을(who/what)" 축 귀속 |
| 환각 방지 | 좌표 = ground truth | "support evidence only, no judgment" |
| 사람 검토 | 하이라이트 visual | human gate / proof_limits |

- **차이 한 줄:** PDF 그라운딩은 *where*(원본 위치)만, Brick은 *who/what*(축 귀속) + **`not_proven`(안 증명된 것까지 명시)** 으로 한 발 더.
- **활용:** Brick 포지셔닝에서 *"grounding/추적가능성은 업계가 가치 있게 보는 원리"* 의 외부 증거로 인용 가능.
- **우리 코드 보유 여부:** **없음** — `pymupdf`/`fitz`/`search_for`/PDF 추출 의존성 0 (2026-05-30 grep 실측 확인).

---

## 2. 우리 것 — Brick 자체의 grounding 지도 (실측 67앵커)

→ **`brick_protocol/support/docs/references/brick-grounding-map.md`** (별도 파일, ~70KB)

ePapyrus가 PDF에 하는 grounding을, Brick은 **agent-work 증거**에 한다. 그 *"어디서·어떻게"* 를 **67개 앵커**로 실측 정리 — 8영역(comparison / raw_refs / building_map / agent_fact / link_movement / proof_limits / capture_contract / evidence_assembly).

- 좌표 = 줄번호가 아니라 **심볼 + 토큰 + grep 레시피** → 코드 고쳐도 안 썩고, 못 찾으면 그게 드리프트 신호(미니 체커).
- 생성: workflow `wquj6xu7n` (catalog→독립 verify→코드 렌더). 67개 전부 **grep 2회 교차검증 + 사후 live 재실행(67/67 resolve)**, 추측 0. LLM 산문 아니라 검증 데이터에서 코드로 렌더.
- 갱신: 코드 대변경 시 동일 워크플로 재실행(resume). 개별 위치는 각 항목 `재파생` grep으로 즉시 확인.

---

_(다음 grounding/traceability 레퍼런스는 아래에 계속 누적)_
