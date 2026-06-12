# Dashboard productization — third-party deployable, auth-delegated, env-clean

## Objective
Make support/dashboard/ shippable to ANOTHER COMPANY: anyone can deploy it behind THEIR OWN auth wall with a documented recipe, no Smith/GCP specifics baked in. The app itself stays credential-free (protocol law: no credential store) — authentication is DELEGATED to deployment infrastructure.

## Auth structure (operator judgment, validate in your design return)
The app must NOT grow a login system. Document and support the delegation pattern:
- our reference deploy: Cloud Run + IAP (Google accounts) — works today;
- alternatives a company may use: Cloudflare Access, VPN/Tailscale, any authenticating reverse proxy;
- the only app-level credential stays the x-ingest-secret header for POST /ingest.
If you find any place the app assumes Google/GCP/IAP specifically, make it deployment-neutral.

## Verified current state (recon — re-verify yourself)
- server: support/dashboard/server/index.mjs — POST /ingest (x-ingest-secret), GET /events (SSE), GET /dashboard-data.json fallback, baked snapshot dist/dashboard-data.json loaded at boot as default participant; PORT/INGEST_SECRET/DIST_DIR envs; secret default 'dev-secret'.
- UI: Korean label layer complete (src/data/labels.js), pages 프로젝트/빌딩/브릭/에이전트/링크, participant picker (multi-member viewing).
- Dockerfile: 2-stage (vite build → bare node), self-contained.
- Deploy reality used today: gcloud run deploy from support/dashboard source; seed via baked public/dashboard-data.json at build time (programmatic ingest is blocked by IAP for service accounts — that is FINE for the reference deploy; document it).

## Deliverables
1. **Deploy recipe doc** (support/dashboard/DEPLOY.md or docs/): from clone to serving, for (a) Cloud Run + IAP (our reference, exact commands), (b) generic Docker behind any reverse proxy (nginx example snippet), (c) bare node. Include: how to bake a seed snapshot (the dashboard_export_packet → public/dashboard-data.json path), how to rotate INGEST_SECRET, scale-to-zero data semantics (in-memory + baked snapshot = projection, source of truth is the repo ledger — re-bake any time).
2. **Env hygiene**: secret default 'dev-secret' must FAIL CLOSED in production mode (NODE_ENV=production + missing/dev secret → refuse to serve /ingest; static viewing may proceed). No hardcoded URLs/org/project ids anywhere in app or docs (parameterize).
3. **Operator bake verb**: a small support function/CLI (support side, not dashboard) that computes dashboard_export_packet and writes it to support/dashboard/public/dashboard-data.json in one step (today the operator does it by hand) — synchronous, no scheduler.
4. **UI polish for adopters**: any remaining protocol-jargon leaks in UI surfaces (raw refs shown as headline where a labels.js word exists) — fix only clear cases, no redesign.
5. **Checker pins + FIRE**: (a) production-mode dev-secret refusal probe → mutated tolerant server = RED... pin what is pinnable from the python side (e.g., a checker that lints index.mjs for the fail-closed branch presence + forbidden hardcoded literals in support/dashboard config surfaces); (b) bake verb writes valid JSON consumable by the server's baked-snapshot loader (shape probe); (c) full gate: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all → exit 0 (say which checkout/copy).

## Hard constraints
- NO login/account/session system in the app. NO credential storage beyond the single ingest secret env.
- No scheduler/queue/retry/polling additions. SSE stays as-is.
- Append-only project/ untouched; no link/, agent/, brick/ edits; no pin weakening.
- Write scope: support/* only (dashboard lives under support/).
- Korean UI stays primary; do not build i18n machinery — just avoid burying labels in logic.

## Proof required (run, report honestly)
- npm build succeeds in the worktree (or state exactly why not runnable in sandbox).
- Bake verb round-trip: compute → write → node loads it (or a node -e shape check).
- Production fail-closed probe output. All FIRE outputs. Full gate exit code.
