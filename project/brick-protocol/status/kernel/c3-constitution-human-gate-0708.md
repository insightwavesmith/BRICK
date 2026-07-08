# C3 개헌 / Human Gate 후보 — 0708

Status: support evidence only. 이 문서는 source truth, 성공/품질 판정, Movement 권한이 아니다.
Smith가 C2 import-unify 이후 문서/운영 언어를 확정하기 전에 보는 human gate 후보이다.

## 쉬운 설명

```text
개헌 = BRICK의 운영법/기본 문서가 새 현실을 공식으로 인정하게 고치는 것.
human gate = 자동으로 확정하지 않고 Smith가 “이 문구/방향 맞다” 하고 확인해야 넘어가는 문.
```

이번 C3에서 “새 현실”은 다음이다.

```text
예전 active physical roots:
  brick/
  agent/
  link/
  support/

현재 active physical roots:
  brick_protocol/brick/
  brick_protocol/agent/
  brick_protocol/link/
  brick_protocol/support/
```

## 이미 증명된 것

```text
commit: 7b99b8f7fd4e00a94d797620c4905afd9f957f7c
origin/main: pushed
post-C2 code status: clean before C3 docs were restored
compileall brick_protocol: rc=0
import brick_protocol.support.operator.cli: rc=0
top-level import support/agent/brick/link: rc=1 each, expected fail
check_profile.py --all: rc=0, passed_count=55
```

## 현재 문서 상태

- `AGENTS.md`는 이미 현재 active physical roots를 `brick_protocol/...`로 설명한다.
- `GOAL/01-continuous-build-goal-0708.md`는 C1/C2 완료와 C3 진행 상태로 갱신했다.
- `handoff-coo-0708.md`는 과거 C2 실패 기록 앞에 C3 현재 상태를 추가했다.
- `order-architecture-feedback-0708.md`는 다음 주력 입력으로 표시했다.
- `route-architecture-feedback-0708.md`는 route v2 HOLD로 표시했다.

## Smith human gate 질문

### Gate 1 — BRICK-CONSTITUTION.md에 물리 루트 조항을 넣을까?

선택 A — 넣는다.

```text
Active physical roots are:
- brick_protocol/brick/ for the Brick axis physical surface.
- brick_protocol/agent/ for the Agent axis physical surface.
- brick_protocol/link/ for the Link axis physical surface.
- brick_protocol/support/ for support mechanics only.

The legacy top-level brick/, agent/, link/, and support/ roots are not active
import roots. Canonical Python imports use the brick_protocol.* namespace.
```

장점: 헌법/기본법에서도 C2 현실이 명확하다.
위험: 헌법이 물리 경로를 너무 구체적으로 품게 된다.

선택 B — 넣지 않는다.

```text
AGENTS.md and checkers carry physical-root operational details.
BRICK-CONSTITUTION.md stays focused on axis law and support non-authority.
```

장점: 헌법을 추상 법으로 유지한다.
위험: 새 세션이 AGENTS.md를 안 보면 물리 루트 확정이 덜 보일 수 있다.

### Gate 2 — C3 완료 기준

C3를 완료로 보려면 Smith가 아래 중 하나를 택한다.

```text
A. GOAL/handoff/order/route 상태문서 갱신만으로 C3 완료.
B. BRICK-CONSTITUTION.md에 위 물리 루트 조항까지 넣고 C3 완료.
C. 추가 문서/원장(walk-results-adopted-0707.md)까지 갱신 후 C3 완료.
```

## COO 권고

```text
권고: A로 C3 문서 상태는 닫고, BRICK-CONSTITUTION.md 물리 루트 조항은 Smith 확인 후 별도 소형 패치로 처리.
이유: C2 코드/검증은 이미 완료됐고, 지금 오래 붙잡으면 다음 주력인 발주 v2가 늦어진다.
```

## 다음 주력 후보

```text
발주 v2 / operator-safe launch envelope v1
```

Route v2 / walker v2는 아직 HOLD.


---

### 0709 landing update

Smith 승인 후 `BRICK-CONSTITUTION.md`에 active physical roots 조항을 추가하는 방향으로 처리한다.
적용 표면은 `BRICK-CONSTITUTION.md`이며, 기존 `AGENTS.md`의 active physical roots와 정합해야 한다.
Legacy top-level `brick/`, `agent/`, `link/`, `support/` roots는 C2 이후 active import roots가 아니다.

Proof limit: 이 문서는 support status evidence이며 source truth·성공/품질·Movement 권한이 아니다.
