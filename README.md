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
# 3) 할 일을 한 줄로 — AI가 보드를 보고 빌딩을 알아서 구성해 격리 샌드박스에서 실행
#    (프리셋을 직접 안 골라도 돼요. 실제 작업 트리는 절대 안 건드려요.)
cd ~/BRICK && uv run python3 -m brick_protocol.support.operator.onboard goal "내 할 일을 한 줄로 적기"
#    실행 브레인 고르기(선택): --brain codex|claude|local (기본 local)
```

AI/운영자가 그대로 확인할 줄:

```text
command: gh repo clone {OWNER}/BRICK ~/BRICK && sh ~/BRICK/support/onboarding/install.sh
expected: "5) 설치 점검 완료" 와 다음 온보딩 한 줄이 출력된다.
failure signal: "BRICK_REPO={OWNER}/BRICK" 요청, "gh auth login" 요청, python3/uv 진단, 또는 git clone/pull 실패.

command: cd ~/BRICK && uv run python3 -m brick_protocol.support.operator.onboard codex
expected: provider 준비 상태 표와 adapter:local 첫 예제 Building 결과가 출력된다.
failure signal: local_cli_missing, provider login 진단, FileExistsError, 또는 adapter-error frontier 안내.

command: cd ~/BRICK && uv run python3 -m brick_protocol.support.operator.onboard goal "내 할 일을 한 줄로 적기"
expected: "AI가 합성한 빌딩(노드)" 목록과 frontier: complete, 그리고 증거 저장 위치(~/.brick/goal-runs 아래)가 출력된다. 작업 트리는 안 건드린다.
failure signal: AI 합성/실행 실패 안내(에러 종류·내용), GEMINI_API_KEY/GOOGLE_API_KEY 요청, 또는 frontier가 complete 가 아니라는 안내.

command: cd ~/BRICK && PYTHONPATH=support/import_identity uv run python3 support/checkers/check_profile.py --all
expected: "profile passed:" 줄들이 나오고 마지막 proof-limit 줄 뒤 exit 0.
failure signal: "profile runner rejected evidence:" 뒤의 첫 거절 문장.
```

설치가 끝나면 위자드가 다음 단계를 알아서 안내해요. provider 없이도 첫 예제
빌딩이 30초 안에 돕니다 (이 저장소 실측 약 1.6초, `adapter:local`). 막히면
`uv run python3 -m brick_protocol.support.operator.onboard doctor` 가 증상→처방
진단표를 보여줘요. 받은 게 멀쩡한지 확인(초록불 = exit 0):
`PYTHONPATH=support/import_identity uv run python3 support/checkers/check_profile.py --all`

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

You do not author task files: SPEAK your task as text. Pass `task_statement`
to the intake seam (see the quickstart's one-liner) and the machine records it
as the Building's task evidence (`work/task.md`). File-based `task_source_ref`
remains the automation path.

- Brick = work
- Agent = performer
- Link = transfer / carry / movement

Brick Protocol is not a runtime engine.
Brick Engine remains legacy/reference runtime evidence, not the source of
truth.

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

## Next Movement

```text
Movement: pass
Target: Smith Movement on whether to mark the active governed TSK / dogfood
roadmap goal complete.

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
