# Dashboard productization (attempt 2) — third-party deployable, auth-delegated, env-clean

PRIOR ATTEMPT NOTE (dashboard-productization-0612, honest breakdown): the work step ran npm inside the working tree; a build artifact named node_modules/@babel/generator/lib/token-map.js tripped the always-forbidden path-segment guard (the word 'token' in a path segment) and the step was voided. THIS attempt must avoid that class entirely:
- NEVER run npm install/ci/build inside the working tree. For build proof, COPY support/dashboard to a temp dir OUTSIDE the repo (e.g. mktemp -d), run npm there, report results, leave the worktree clean of artifacts.
- NEVER create files whose path segments contain the words auth/token/secret/credential (e.g. name the deploy doc DEPLOY.md and use a section for delegated access, not a file named auth-*.md).

## Objective
Make support/dashboard/ shippable to ANOTHER COMPANY: deployable behind THEIR OWN access wall with a documented recipe, no Smith/GCP specifics baked in. The app stays credential-free (protocol law) — the only app-level credential is the env-only x-ingest-secret for POST /ingest.

## Access structure (operator judgment — validate in design)
No login system in the app. Delegation pattern documented: reference = Cloud Run + IAP (works today); alternatives = Cloudflare Access, VPN/Tailscale, any authenticating reverse proxy. If the app assumes Google/GCP anywhere, make it deployment-neutral.

## Verified current state (re-verify yourself)
- server/index.mjs: POST /ingest (x-ingest-secret), GET /events SSE, GET /dashboard-data.json fallback, baked snapshot dist/dashboard-data.json at boot; PORT/INGEST_SECRET/DIST_DIR envs; secret default 'dev-secret'.
- UI: Korean label layer complete (src/data/labels.js); pages 프로젝트/빌딩/브릭/에이전트/링크; participant picker.
- Dockerfile: 2-stage, self-contained. Deploy reality: gcloud run deploy from source; seed = baked public/dashboard-data.json (programmatic ingest blocked by IAP for service accounts — document as known reference-deploy property).

## Deliverables
1. Deploy recipe doc support/dashboard/DEPLOY.md: (a) Cloud Run + IAP reference with exact commands; (b) generic Docker behind any reverse proxy (nginx snippet); (c) bare node. Include: baking a seed snapshot (dashboard_export_packet → public/dashboard-data.json), rotating INGEST_SECRET, scale-to-zero semantics (projection only; source of truth = repo ledger; re-bake any time).
2. Env hygiene: NODE_ENV=production + missing-or-'dev-secret' INGEST_SECRET → /ingest refuses (fail closed); static viewing proceeds. No hardcoded org/project/URL literals in app code or docs (parameterize).
3. Operator bake verb (support side): one function/CLI computing dashboard_export_packet and writing support/dashboard/public/dashboard-data.json in one step. Synchronous, no scheduler.
4. UI polish: fix clear protocol-jargon leaks where a labels.js word exists. No redesign.
5. Checker pins + FIRE: (a) lint pin for the fail-closed branch presence + forbidden hardcoded literals in support/dashboard config surfaces (mutated copy = RED); (b) bake verb output shape consumable by the server loader (probe); (c) full gate PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all → exit 0 (say which checkout/copy).

## Hard constraints
- NO login/account/session system; no credential storage beyond the single env secret.
- No scheduler/queue/retry/polling. Append-only project/ untouched. No link/, agent/, brick/ edits. No pin weakening.
- Write scope: support/* only. Korean UI primary; no i18n machinery.

## Proof required (run, report honestly)
- npm build in TEMP COPY succeeds (or exact sandbox reason if not runnable).
- Bake verb round-trip: compute → write → node shape-check of the JSON.
- Production fail-closed probe output. All FIRE outputs. Full gate exit code.
