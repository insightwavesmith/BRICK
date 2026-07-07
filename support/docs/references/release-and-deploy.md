# Release export, release gate, and deploy

This page covers release-manager procedures: building a clean public-release
tree, running the pre-release local gate, and deploying the dashboard
projection (Vercel static or Docker realtime). It moved out of `README.md`
(split 0701, see
`project/brick-protocol/status/kernel/brick-followon-doc-skill-checker-catalog-0701.md`)
because these are release/deploy-operator procedures, not first-clone
quickstart material. For getting started, see [quickstart](quickstart.md) and
[setup](setup.md).

## Release Export

릴리스용 공개 repo는 이 checkout에서 `project/` 동네와
`brick_protocol.egg-info/` 빌드 산출물을 빼고 새로 만듭니다. export는 새
output dir 안에서만 initial commit을 만들고, remote/push/tag는 출력만 합니다.
이 export 트리가 고객이 클론하는 **클린 배포 저장소**(`{OWNER}/BRICK-dist`)가
됩니다. 내부 작업 checkout(원장·빌딩 증거를 담은 이 repo)은 그대로 두고, 신규
고객 온보딩만 클린 배포 저장소를 가리킵니다.

```bash
sh support/onboarding/release_export.sh --output /tmp/BRICK-v0.1.0
```

```text
expected: "release export ready", "excluded roots: project/, brick_protocol.egg-info/", "initial commit:".
failure signal: output dir가 비어 있지 않음, source checkout 밖 output이 아님, git/python3 없음, 또는 commit 생성 실패.
```

export tree에는 `project/`가 없습니다. 첫 onboard/run 이 로컬 vessel과 status
inbox를 만듭니다.

## Release Gate

릴리스 전에 로컬 게이트를 먼저 실행합니다. 이 게이트는 Python compileall,
`check_profile.py --all`, release export dry-run을 순서대로 실행하고 첫 실패에서
멈춥니다.

```bash
sh support/onboarding/release_gate.sh
```

```text
expected: compileall, checker gate, release export dry-run이 모두 끝나고 "release gate passed"가 출력된다.
failure signal: compile error, profile rejection, release export rejection, 또는 uv sync/lock 불일치.
```

GitHub Actions workflow도 같은 로컬 게이트를 호출합니다. GitHub branch protection
설정은 이 repo 파일로 바뀌지 않습니다. branch protection required-check 연결은
Smith/operator가 GitHub repository settings에서 별도로 켜야 하는 pending action입니다.
게이트와 workflow는 support evidence only이며 source truth, 성공/품질 판단,
Movement authority, 실제 release publication을 증명하지 않습니다.

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
[`support/dashboard/DEPLOY.md`](../../dashboard/DEPLOY.md)를 보세요.
