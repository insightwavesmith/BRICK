# brick_protocol/link/ — Link 축 (MOVEMENT / 이동·운반·전달)

**한 줄 정체:** Link = **MOVEMENT** — 이동 / 타깃 / carry / 게이트 / reroute
(BRICK-CONSTITUTION.md 3축 절과 정합).

**비개발자 비유:** Link은 "작업물을 다음 자리로 **옮기는 컨베이어와, 통과 여부를 재는
게이트**"다. 무엇을 만들지(Brick)도, 누가 하는지(Agent)도 아닌, *어디로·통과하는가*만 여기 산다.
충분성+Movement 판정 권위는 오직 이 축(Link 게이트)에 있다.

## 폴더 지도 (git ls-files 실측)

| 경로 | 한 줄 |
| --- | --- |
| `spec.py` | Link 단일 출처 플랜-문법 API — 게이트 개념 번역표, `translate_gate_concept` |
| `movement.py` · `movement.yaml` | Movement(forward/reroute) 축과 반환형 |
| `gate.py` · `gate.yaml` | 게이트(충분성 측정) 축과 반환형 |
| `transfer.py` · `transfer.yaml` | 엣지 전달(transfer) 축과 반환형 |
| `carry.py` · `carry.yaml` | carry(엣지 위 운반 메타) 축과 반환형 |
| `transition.py` · `transition.yaml` | 전이(transition) 축과 반환형 |
| `route_policies/` | 라우트 정책 선언(YAML) |
| `__init__.py` | 패키지 마커 |

## 낯선 사람이 처음 열 것

`movement.yaml`(무엇이 움직임의 결과인지) → `gate.yaml`(무엇이 통과를 재는지).
축 전체 개념 지도는 `brick_protocol/support/docs/references/architecture-map.md`.

## 오해 방지

- **Movement 권위는 Link만의 것.** Brick·Agent·support 어느 축도 forward/reroute를 고르지
  못한다. 게이트가 충분성을 재고 Movement를 정한다.
- gate·transfer·carry는 **독립 최상위 경로로 존재하지 않는다** — 축(brick_protocol/brick/agent/link) 아래
  선언된 파일로만 산다(루트 `gate.py`·`transfer.py`류는 admission이 거부).
- README는 **안내 표면**이지 판정이 아니다. 통과·재라우팅 결정은 실행된 게이트 증거가 근거다.

> support evidence only. not source truth · not success judgment · not quality
> judgment · not Movement authority.
