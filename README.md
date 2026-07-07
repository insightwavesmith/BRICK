# Brick Protocol

Brick Protocol is a three-axis work protocol for human-agent work: Brick = the work, Agent = the performer, Link = the transfer/carry/movement between work boundaries.

## 시작하기 (2분)

초대를 수락했다면 아래 명령을 **그대로 복사해** 실행하세요. 신규 고객이 받는
곳은 제품 파일만 담긴 **클린 배포 저장소**(`{OWNER}/BRICK-dist` — 내부 `project/`
원장과 빌딩 산출물이 빠진 릴리스 트리)입니다. 소유자 자리에는 언제나 배포
저장소 소유자(초대받은 바로 그 저장소)가 들어갑니다 — 네 자신의 GitHub 계정이
아닙니다. 소유자를 네 계정으로 바꾸면 미초대·미포크라 clone이 not-found로
실패합니다. 기본 위치는 `$HOME/BRICK`입니다. 다른 위치에 받았다면 설치 전에
`BRICK_HOME=/path/to/clone`을 지정하세요.

받기 + 설치:

```bash
gh repo clone {OWNER}/BRICK-dist ~/BRICK && sh ~/BRICK/support/onboarding/install.sh  # 클린 배포 저장소 예 — 배포 저장소 소유자, 초대받은 그대로
```

기존 작업-repo를 이미 클론한 사용자는 그대로 동작하고, 신규 고객은 위 클린 배포 저장소(`{OWNER}/BRICK-dist`)를 클론합니다.

준비 상태 진단은 설치된 `brick` 진입점으로 실행합니다.

```bash
cd ~/BRICK && brick doctor
```

공식 고객 실행 표면은 하나입니다: `brick build`. 표준 작업은
`--task`/`--preset`으로 말합니다. design-first 또는 multi-lane 그래프는
`assemble()` / `build()` / `fan()` DSL로 선언하고 실행합니다. 손으로 작성한
raw `graph_packet` JSON을 CLI에 넘기던 `--graph`/`--graph-packet` 입력은
retired입니다.

```bash
cd ~/BRICK && brick build --task "첫 실행을 support evidence only로 기록해 주세요." --preset building-chain-preset:design-contract-only --adapter adapter:local --timeout 20
```

실제 저장소를 바꾸는 작업은 auth 뒤에 `--real-provider`를 붙이거나,
명시적인 observed-write adapter를 고른 다음 실행하세요.
`run_building_intake`, `assemble`, `launch_assembled_building`, `goal-approve`는
support/operator helper 또는 고급/내부 경로이지 별도 고객 실행 루트가
아닙니다.

AI/운영자가 그대로 확인할 줄입니다. 이 표는 quickstart의 S0~S5 전체
체크리스트 중 고객 첫 실행에 필요한 축약 부분집합입니다.

```text
command: gh repo clone {OWNER}/BRICK-dist ~/BRICK && sh ~/BRICK/support/onboarding/install.sh  # 클린 배포 저장소 예 — 배포 저장소 소유자, 초대받은 그대로
expected: 먼저 "선검사 (preflight):" 체크리스트가 전부 ✓로 출력되고, 이어 "5) 설치 점검 완료" 와 다음 온보딩 한 줄이 출력된다.
failure signal: 선검사 단계에서 나오는 "지금 치세요" 한 줄 처방(pipx/git/uv/python3.11+/디스크/gh 로그인 중 하나), 소유자를 네 계정으로 바꿔 미초대·미포크로 인한 not-found, 또는 이후 git clone/pull 실패.

command: cd ~/BRICK && brick doctor
expected: provider별 준비 상태 표와 증상 -> 처방 표가 출력되고 exit 0.
failure signal: doctor 자체 stack trace, 또는 repo 루트가 아닌 곳에서 실행한 import 실패.

command: cd ~/BRICK && brick build --task "첫 실행을 support evidence only로 기록해 주세요." --preset building-chain-preset:design-contract-only --adapter adapter:local --timeout 20
expected: build_input_mode=preset_task, building_id, evidence_root, frontier_kind가 출력된다. provider 준비 전 local/support-only 확인은 frontier_kind=agent_incomplete/not_ready일 수 있으며, customer-visible closure는 frontier_kind=complete일 때뿐이다. brick build exit 0은 CLI가 support evidence를 반환했다는 뜻이지 phase PASS가 아니다. complete가 아닌 frontier는 not_ready로 보고 evidence_root를 inspect한다. raw graph_packet CLI 입력은 retired이고, 그래프형 작업은 DSL로 선언한다.
failure signal: FileExistsError이면 building_id를 새로 정한다; ModuleNotFoundError이면 루트에서 uv run python3 -c 로 호출했는지 확인한다; frontier가 complete가 아니라는 안내.

command: cd ~/BRICK && brick verify --all
expected: "profile passed:" 줄들이 나오고 마지막 proof-limit 줄 뒤 exit 0.
failure signal: "profile runner rejected evidence:" 뒤의 첫 거절 문장.
```

설치가 끝나면 installer가 다음 단계를 안내해요. provider 없이도 `brick verify`와
doctor/readiness 확인은 가능합니다. 다만 `brick build`는 design/review/closure 같은
verdict-bearing 노드에서 provider-backed adapter가 필요할 수 있어, provider 준비 전에는
`agent_incomplete`/`not_ready` support evidence를 반환할 수 있습니다. 막히면
`brick doctor` 가 증상→처방
진단표를 보여줘요. 받은 게 멀쩡한지 확인(초록불 = exit 0):
`brick verify --all`
이 checker 초록불도 support evidence일 뿐이고, phase PASS나 Building closure를
혼자 증명하지 않습니다.

Start here: [quickstart](support/docs/references/quickstart.md) · [setup](support/docs/references/setup.md) · [repository invite issuance](support/docs/references/repo-invite-issuance.md) · [three-axis overview](support/docs/references/three-axis-overview.md)

You do not author task files for the common path: SPEAK your task as text
through `brick build --task`. That is the official public first-run surface.
Preset task runs use `brick build --task ... --preset ...`. For design-first or
multi-lane work, the official way to construct and launch a Building is the
`assemble()` / `build()` / `fan()` Python DSL (`support/operator/assembly.py`)
plus `run_building_plan()`. Hand-authored `graph_packet` JSON via
`brick build --graph <packet.json>` is retired from the public customer CLI
surface now that sibling independence, per-node `write_scope`, and mid-graph
human/COO gates are expressible in the DSL. `run_building_intake`,
`launch_assembled_building`, and
`goal-approve` remain helper or advanced/internal paths, not separate customer
execution routes.

For bigger work, the easy route is still the same public surface. Say the work
as `brick build --task` when a declared preset fits. When the work needs
design, review, split implementation, lane QA, final QA, and closure, the
caller/COO declares that road with the `assemble()`/`build()`/`fan()` DSL and
runs it with `run_building_plan()`. There is no separate `--large` mode, no
raw `--graph` packet input, and no support-owned route chooser.

Use the first-run example with `building-chain-preset:design-contract-only` and
`--adapter adapter:local --timeout 20` only as a support-evidence check: it may
return `agent_incomplete`/`not_ready` until provider-backed verdict lanes are
ready. For a provider-free green check, run `brick verify`. For real
repository-changing work, authenticate first and use `--real-provider`, or choose
an explicit observed-write adapter.

- Brick = work
- Agent = performer
- Link = transfer / carry / movement

Brick Protocol is not a runtime engine.
Brick Engine remains legacy/reference runtime evidence, not the source of
truth.

Docs and CLI output are support evidence only. They do not prove provider
reliability, customer comprehension, success, quality, source truth, or
Movement authority.

Axes: Brick / Agent / Link only.

## More

- Release export, release gate, and dashboard deploy (Vercel static / Docker
  realtime): [release-and-deploy.md](support/docs/references/release-and-deploy.md)
- Operator session status-inbox watch loop: [operator-status-inbox.md](support/docs/references/operator-status-inbox.md)
- Repository role, source boundary, physical-surface history, and the
  historical governed-goal disposition note: [repository-history-and-structure.md](support/docs/references/repository-history-and-structure.md)
- Full architecture / module map: [architecture-map.md](support/docs/references/architecture-map.md)
- Rules and contributor boundaries: [rules-and-boundaries.md](support/docs/references/rules-and-boundaries.md)
