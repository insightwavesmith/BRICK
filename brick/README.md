# brick/ — Brick 축 (WHAT / 일 그 자체)

**한 줄 정체:** Brick = **WHAT** — 작업계약 / 템플릿 / 플랜 / 반환형 / 그래프
(BRICK-CONSTITUTION.md 3축 절과 정합).

**비개발자 비유:** Brick은 "무엇을 만들지 적은 **작업 주문서**와, 그 주문서를 찍어내는
**양식 서랍**"이다. 누가 만들지(Agent)도, 어떻게 옮길지(Link)도 아닌, *만들 대상*만 여기 산다.

## 폴더 지도 (git ls-files 실측)

| 경로 | 한 줄 |
| --- | --- |
| `spec.py` | Brick 단일 출처 선언 계약 API — `BRICK_ROW_ALLOWED_KEYS`, `WriteScope`, write-NEED 해석 |
| `work.py` · `work.yaml` | work Brick 축(작업계약)과 그 기계 반환형 |
| `building.py` · `building.yaml` | 빌딩(작업 묶음) 축과 반환형 |
| `comparison.py` · `comparison.yaml` | written-vs-scope 비교 축과 반환형 |
| `templates/` | 물리 양식 선반 — kind별 brick.md/return.yaml, 체인 프리셋, tasks·shapes·skills·blocks·graph-decls (자체 README 있음) |
| `building_plans/` | 손으로 선언한 빌딩 플랜 라이브러리 (도그푸드기 유산 · 프로파일 핀으로 보존) |
| `__init__.py` | 패키지 마커 |

## 낯선 사람이 처음 열 것

`templates/README.md`(양식 서랍 지도) → 그다음 `work.yaml`(가장 기본이 되는 작업 반환형).
축 전체 개념 지도는 `support/docs/references/architecture-map.md`.

## 오해 방지

- **development KIND는 코드를 짜지 않는다.** 코드를 짜는 것은 *work*이다. development는
  브릭 프로토콜 자체를 바꾸는 작업계약 종류의 이름일 뿐, 별도의 코딩 엔진이 아니다.
- `templates/skills/`와 `agent/skills/`의 중복은 실수가 아니라 **의도된 3면 동기화**
  (레포 원본 ↔ 운영자 설치본 등). 동기 규칙은 `brick/templates/skills/APPLY-LIST.md` 참조.
- README는 **안내 표면**이지 새 권위가 아니다. 정책·판정·계약은 여기서 발명하지 않고
  기존 정본(헌법·템플릿·spec)을 가리킨다.

> support evidence only. not source truth · not success judgment · not quality
> judgment · not Movement authority.
