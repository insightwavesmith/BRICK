# Brick Protocol

Brick Protocol is a three-axis work protocol for human-agent work: Brick = the work, Agent = the performer, Link = the transfer/carry/movement between work boundaries.

## 시작하기 (2분)

```bash
# 1) 받기 + 설치 -- 내 gh 로그인 사용 (호스팅된 설치 URL은 없어요)
# ⚠️ 먼저 아래 {OWNER}를 네 GitHub 계정(org/user)으로 바꾸세요 — 안 바꾸고 그대로
#    복붙하면 바로 이 첫 줄에서 실패해요. (BRICK은 포크해서 쓰는 구조라 계정이
#    사람마다 달라요. 현재 동작 예: insightwavesmith/BRICK)
#    기본 위치는 $HOME/BRICK; 다른 곳에 받았다면 BRICK_HOME=/path/to/clone 지정
gh repo clone {OWNER}/BRICK ~/BRICK && sh ~/BRICK/support/onboarding/install.sh
# 2) 온보딩 위자드 (codex | claude | gemini | local)
cd ~/BRICK && uv run python3 -m brick_protocol.support.operator.onboard codex
# 3) 공식 고객 실행 표면은 하나입니다: brick build.
#    표준 작업은 preset_task 경로(`--task`/`--preset`)로 말하고,
#    caller/COO가 이미 선언한 그래프는 graph_packet 경로(`--graph`)로 넘깁니다.
cd ~/BRICK && brick build --task "첫 실행을 support evidence only로 기록해 주세요." --preset building-chain-preset:design-contract-only --adapter adapter:local --timeout 20
#    실제 저장소를 바꾸는 작업은 auth 뒤에 --real-provider 를 붙이거나,
#    명시적인 observed-write adapter를 고른 다음 실행하세요.
#    run_building_intake, assemble, launch_assembled_building, goal-approve 는
#    support/operator helper 또는 고급/내부 경로이지 별도 고객 실행 루트가 아닙니다.
```

AI/운영자가 그대로 확인할 줄:

```text
command: gh repo clone {OWNER}/BRICK ~/BRICK && sh ~/BRICK/support/onboarding/install.sh
expected: "5) 설치 점검 완료" 와 다음 온보딩 한 줄이 출력된다.
failure signal: "BRICK_REPO={OWNER}/BRICK" 요청, "gh auth login" 요청, python3/uv 진단, 또는 git clone/pull 실패.

command: cd ~/BRICK && uv run python3 -m brick_protocol.support.operator.onboard codex
expected: provider 준비 상태 표와 첫 예제 Building support evidence가 출력된다. provider가 아직 준비되지 않았으면 frontier_kind=agent_incomplete/not_ready일 수 있다.
failure signal: local_cli_missing, provider login 진단, FileExistsError, 또는 adapter-error frontier 안내.

command: cd ~/BRICK && brick build --task "첫 실행을 support evidence only로 기록해 주세요." --preset building-chain-preset:design-contract-only --adapter adapter:local --timeout 20
expected: build_input_mode=preset_task, building_id, evidence_root, frontier_kind가 출력된다. provider 준비 전 local/support-only 확인은 frontier_kind=agent_incomplete/not_ready일 수 있으며, customer-visible closure는 frontier_kind=complete일 때뿐이다. brick build exit 0은 CLI가 support evidence를 반환했다는 뜻이지 phase PASS가 아니다. complete가 아닌 frontier는 not_ready로 보고 evidence_root를 inspect한다. graph_packet은 `brick build --graph <packet.json>`로 같은 표면을 통과한다.
failure signal: FileExistsError이면 building_id를 새로 정한다; ModuleNotFoundError이면 루트에서 uv run python3 -c 로 호출했는지 확인한다; frontier가 complete가 아니라는 안내.

command: cd ~/BRICK && PYTHONPATH=support/import_identity uv run python3 support/checkers/check_profile.py --all
expected: "profile passed:" 줄들이 나오고 마지막 proof-limit 줄 뒤 exit 0.
failure signal: "profile runner rejected evidence:" 뒤의 첫 거절 문장.
```

설치가 끝나면 위자드가 다음 단계를 알아서 안내해요. provider 없이도 `brick verify`와
doctor/readiness 확인은 가능합니다. 다만 `brick build`는 design/review/closure 같은
verdict-bearing 노드에서 provider-backed adapter가 필요할 수 있어, provider 준비 전에는
`agent_incomplete`/`not_ready` support evidence를 반환할 수 있습니다. 막히면
`uv run python3 -m brick_protocol.support.operator.onboard doctor` 가 증상→처방
진단표를 보여줘요. 받은 게 멀쩡한지 확인(초록불 = exit 0):
`PYTHONPATH=support/import_identity uv run python3 support/checkers/check_profile.py --all`
이 checker 초록불도 support evidence일 뿐이고, phase PASS나 Building closure를
혼자 증명하지 않습니다.

운영자 세션 표준은 status inbox 감시를 같이 켜는 것입니다. export 직후에는
`project/`가 없고, 첫 onboard/run 이 로컬 vessel을 만들 수 있어요.

```bash
cd ~/BRICK
while true; do
  if [ -d project/brick-protocol/status/inbox ]; then
    find project/brick-protocol/status/inbox -maxdepth 1 -type f -name '*.json' -print | tail -20
  else
    printf '%s\n' 'status inbox not created yet'
  fi
  sleep 5
done
```

예상 출력은 알림 packet이 없으면 빈 줄 또는 `status inbox not created yet`,
알림이 생기면 `project/brick-protocol/status/inbox/*.json` 경로입니다. 실패
신호는 `No such file or directory`를 숨기지 않은 watch, 또는 repo 루트가 아닌
곳에서 실행한 경우입니다.

Start here: [quickstart](support/docs/references/quickstart.md) · [setup](support/docs/references/setup.md) · [three-axis overview](support/docs/references/three-axis-overview.md)

You do not author task files for the common path: SPEAK your task as text
through `brick build --task`. That is the official public first-run surface.
Preset task runs use `brick build --task ... --preset ...`; caller/COO-declared
graph packets use `brick build --graph <packet.json>`. The support helpers
`run_building_intake`, `assemble`, `launch_assembled_building`, and
`goal-approve` remain helper or advanced/internal paths, not separate customer
execution routes.

For bigger work, the easy route is still the same public surface. Say the work
as `brick build --task` when a declared preset fits. When the work needs
design, review, split implementation, lane QA, final QA, and closure, the
caller/COO first declares that road as a graph packet, then runs it with
`brick build --graph <packet.json>`. There is no separate `--large` mode and no
support-owned route chooser.

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

## Release Export

릴리스용 공개 repo는 이 checkout에서 `project/` 동네와
`brick_protocol.egg-info/` 빌드 산출물을 빼고 새로 만듭니다. export는 새
output dir 안에서만 initial commit을 만들고, remote/push/tag는 출력만 합니다.

```bash
sh support/onboarding/release_export.sh --output /tmp/BRICK-v0.1.0
```

```text
expected: "release export ready", "excluded roots: project/, brick_protocol.egg-info/", "initial commit:".
failure signal: output dir가 비어 있지 않음, source checkout 밖 output이 아님, git/python3 없음, 또는 commit 생성 실패.
```

export tree에는 `project/`가 없습니다. 첫 onboard/run 이 로컬 vessel과 status
inbox를 만듭니다.

## Deploy

대시보드는 support projection입니다. source truth, 성공/품질 판단, Movement
권한, scheduler/queue/retry/runtime이 아닙니다.

### Vercel Static Photo

정적 사진 모드입니다. `/ingest`와 SSE 없이 bake된 `dashboard-data.json`만
보여줍니다.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity \
  python3 support/operator/dashboard_export.py --bake-public
cd support/dashboard
npm ci
npm run build
# Vercel: root=support/dashboard, build=npm run build, output=dist
```

```text
expected: "baked ... dashboard-data.json | buildings N | source_truth False" 뒤 Vercel build가 dist/를 만든다.
failure signal: dashboard-data.json 없음, source_truth가 False가 아님, npm build 실패, 또는 Vercel root/output 설정 불일치.
```

### Docker Realtime

실시간 모드는 Dockerfile을 쓰고 operator-controlled host 또는 Cloud Run/IAP 뒤에
둡니다. production ingest에는 `INGEST_SECRET`가 필요하고 `PORT`는 선택입니다.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity \
  python3 support/operator/dashboard_export.py --bake-public
docker build -t brick-dashboard:local support/dashboard
docker run --rm \
  -e NODE_ENV=production \
  -e INGEST_SECRET="${INGEST_SECRET_VALUE}" \
  -p 127.0.0.1:8080:8080 \
  brick-dashboard:local
```

```text
expected: server logs "[surface-server] :8080 (ingest configured)" and /healthz returns ok.
failure signal: production에서 INGEST_SECRET 없음, port 충돌, 또는 reverse proxy/IAP 인증 설정 누락.
```

자세한 Cloud Run + IAP, Docker host, bare Node 경로는
[`support/dashboard/DEPLOY.md`](support/dashboard/DEPLOY.md)를 보세요.

## Repository Role

This repository is a clean-room protocol repository.

It starts from the closed Brick / Agent / Link specification package and the
physical blueprint, not from the legacy Brick Engine implementation tree.

The current governed work is completion audit for the governed TSK / dogfood
roadmap. The next possible work is:

```text
Smith Movement on whether to mark the active goal complete
```

DASH-0 creates dashboard projection guidance and read-only viewer boundary
guidance for the external starter-kit project and records project-local
Building evidence for both. It does not create a dashboard application, sync,
runtime/provider/scheduler/storage surfaces, central storage, adoption proof,
dashboard-need proof, projection-correctness proof, or new protocol contracts.

## Source Boundary

Brick Protocol defines:

```text
rules
contracts
structure
boundaries
```

Brick Engine remains:

```text
legacy runtime evidence
reference implementation material
measurement source
contamination sample
```

Brick Engine is not the source of truth for this repository.

## Current Physical Surfaces

FSR-0 reorganizes the working tree around five protocol surfaces:

```text
brick/    Brick axis physical surface
agent/    Agent axis physical surface
link/     Link axis physical surface
support/  support machine location only
project/  project-local evidence destination only
```

The import identity is retained under support:

```text
support/import_identity/brick_protocol/
  Python import identity marker only
```

Root-level `brick_protocol/` is no longer an active repository root. The Python
namespace remains `brick_protocol`; only the address marker moved under
`support/`.

`architecture-review-site/` is no longer an active repository root. Root-level
public docs site / Vercel projection surfaces are removed from the active repo
shape and must not be recreated without a later explicit admission.

Support is not an axis, module family, source truth, success judgment,
Movement authority, runtime, storage, or wiki. Project evidence under
`project/brick-protocol/building-evidence/` is an evidence destination only,
not source truth.

The v0.1 internal candidate freeze preserves BAL semantics and the public
`brick_protocol.*` import API. FSR-0 changes physical locations only; it does
not mutate the `v0.1-internal-candidate-20260518` tag.

## Active Records

Current control surfaces:

```text
AGENTS.md
project/brick-protocol/PROGRESS.md
support/docs/spec/
support/docs/reviews/
support/docs/projection/
support/checkers/
```

Current Building automation chain:

```text
BUILDING-METHOD-0
-> COO-IDENTITY-SKILL-0
-> AGENT-RESOURCE-TOOLKIT-0
-> COO-SYNC-0
-> MCP-PROJECTION-0
-> BUILDING-GRAPH-NEED-0
```

COO-SYNC-0 writes only local COO projection files for Codex and Claude from the
Agent-axis resource source. Projection files are not source truth and do not
replace `agent/`.

MCP-PROJECTION-0 exposes the admitted Agent resource renderer through a
read-only support call door for local apps. MCP is projection only; it is not a
fourth axis, runtime, provider owner, storage/wiki surface, source truth, or
Movement authority.

BUILDING-GRAPH-NEED-0 closes why graph projection is required for three-axis
problem analysis before graph/multi-lane runner implementation.

Historical dev log (FSR-0 / TSK-0..4 / TEAM-0..1 / DASH-0 phase records,
review dispositions, and superseded spec history from 0518-0531) lives in the
HISTORY repository (`brick-protocol`, the repo this product repo was split
from at REPO-SPLIT 0611), under its top-level `archive/` productization
museum. This product repo ships NO archive/ tree at all (CLEAN-YARD v3,
0611): the engine repo starts at project zero, and a check that needs
building evidence generates it with the real engine at check time and
removes it. Archived records are historical support evidence only -- not
source truth, not success judgment, not Movement authority. The live,
checker-pinned records stay under `support/docs/` and
`project/brick-protocol/status/kernel/`.

## Historical Support Note

```text
Historical disposition wording: pass
Target: Smith disposition on whether to mark the historical governed TSK /
dogfood roadmap goal complete.

TSK-0 recorded the starter-kit / dogfood phase sequence after MIA-0. TSK-1
defined the future external project boundary only. TSK-2 created only the
admitted starter-kit wrapper guidance/templates. TSK-3 records the first real
starter-kit Building, `FIRST_USE.md`, project-local Building evidence, local
verification, Opus review, Gemini 3.5 review, Codex disposition, and accepted
wording repairs as support evidence. TSK-4 records repeated self-dogfood work
products, two project-local Building evidence packets, local verification, Opus
review, Gemini 3.5 review, Codex disposition, and accepted no-patch disposition
as support evidence. TEAM-0 now records local-trial and privacy-boundary
guidance, evidence, local verification, Opus review, Gemini 3.5 review, Codex
disposition, and accepted no-patch disposition as support evidence. It does not
create TEAM-1, runtime, provider adapters, sync, dashboard, storage/wiki,
source truth, success judgment, quality judgment, team adoption proof, dashboard
need proof, mandatory raw transcript sharing, or Movement authority.
TEAM-1 now records claim-trace export and multi-local projection guidance and
evidence, and does not create DASH-0, runtime, provider adapters, sync,
dashboard, storage/wiki, central storage, source truth, success judgment,
quality judgment, team adoption proof, dashboard need proof, projection
correctness proof, mandatory raw transcript sharing, or Movement authority.
Opus and Gemini 3.5 returned PASS with no BLOCKER or MINOR findings; Codex
recorded no-patch support notes for future DASH-0/table-shape risks.
DASH-0 now records dashboard projection and read-only viewer boundary guidance
and evidence, and does not create a dashboard application, runtime, provider
adapters, sync, storage/wiki, central storage, source truth, success judgment,
quality judgment, team adoption proof, dashboard need proof, projection
correctness proof, mandatory raw transcript sharing, or Movement authority.
Opus and Gemini 3.5 returned PASS with no BLOCKER or MINOR findings; Codex
accepted the completion-audit-surface memo and recorded this completion audit.

Reviews and checkers are not source truth and not Movement authority. Smith
remains closure authority and commit/push authority.
```
