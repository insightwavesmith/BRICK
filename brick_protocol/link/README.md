# brick_protocol/link/ — Link 축 (MOVEMENT / 이동·운반·전달)

**한 줄 정체:** Link = **MOVEMENT** — 이동 / 타깃 / carry / 게이트 / reroute
(BRICK-CONSTITUTION.md 3축 절과 정합).

**비개발자 비유:** Link은 "작업물을 다음 자리로 **옮기는 컨베이어와, 통과 여부를 재는
게이트**"다. 무엇을 만들지(Brick)도, 누가 하는지(Agent)도 아닌, *어디로·통과하는가*만 여기 산다.
게이트는 충분성 사실만 기록한다. 이미 선언된 forward/reroute Movement를 운반·기록하는
계약은 Link에 있지만, 게이트 사실 자체가 Movement를 고르지는 않는다.

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

- **Movement 의미와 기록 계약은 Link만의 것.** Brick·Agent·support는 게이트 사실만으로
  forward/reroute를 추론하거나 새로 고르지 못한다.
- 게이트는 **충분성만 측정**한다. 부족하다는 사실은 이후 caller/COO disposition 또는 선언된
  Link 정책의 입력이지, 그 자체가 reroute 결정은 아니다.
- gate·transfer·carry는 **독립 최상위 경로로 존재하지 않는다** — 축(brick_protocol/brick/agent/link) 아래
  선언된 파일로만 산다(루트 `gate.py`·`transfer.py`류는 admission이 거부).
- README는 **안내 표면**이지 판정이 아니다. forward/reroute 채택에는 선언된 정책 또는
  caller/COO disposition과 실행 증거가 함께 필요하다.

> support evidence only. not source truth · not success judgment · not quality
> judgment · not Movement authority.
