# Dashboard productization (attempt 3) — docs/env-hygiene/bake-verb/labels, NO node execution

PRIOR ATTEMPTS (honest record): attempts 1 and 2 were both VOIDED by the same guard — the agent ran npm under the working tree and a build artifact named node_modules/.../token-map.js tripped the always-forbidden path-segment word guard ('token'). THIS attempt therefore has a MECHANICAL rule:
- Do NOT execute npm, npx, node, or vite ANYWHERE under the working tree. Not for builds, not for version probes.
- Build proof is NOT required and NOT wanted: the operator has already deployed this exact Dockerfile to Cloud Run twice today (build proven operationally). Skip all build verification.
- JSON shape checks: use python3 only.
- Do not create files whose path segments contain auth/token/secret/credential words.

## Objective
Make support/dashboard/ shippable to ANOTHER COMPANY behind THEIR OWN access wall: documented deploy recipes, env hygiene, an operator bake verb, and label polish. App stays credential-free (protocol law) — the only app-level secret is env-only x-ingest-secret for POST /ingest.

## Deliverables
1. support/dashboard/DEPLOY.md — deploy recipes: (a) Cloud Run + IAP reference (exact commands, parameterized org/project); (b) generic Docker behind any authenticating reverse proxy (nginx snippet); (c) bare node. Include: seed baking (dashboard_export_packet → support/dashboard/public/dashboard-data.json), INGEST_SECRET rotation, scale-to-zero semantics (projection only; source of truth = repo ledger; re-bake any time). A prior draft existed; write it fresh and completely.
2. Env hygiene in server/index.mjs: NODE_ENV=production + missing-or-'dev-secret' INGEST_SECRET → POST /ingest refuses (fail closed); static viewing + SSE still serve. No hardcoded org/project/URL literals in app code or docs.
3. Operator bake verb (support side, python): one function computing dashboard_export_packet and writing support/dashboard/public/dashboard-data.json in one step. Synchronous, no scheduler. Validate output with python3 json round-trip (shape keys present: source_truth false, buildings list).
4. UI label polish: fix clear protocol-jargon leaks where a labels.js word exists (no redesign).
5. Checker pins + FIRE: (a) lint pin asserting the fail-closed branch exists in server/index.mjs + no forbidden hardcoded literals in support/dashboard surfaces (mutated copy = RED); (b) bake verb output shape probe; (c) full gate PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all → exit 0 (say which checkout/copy).

## Hard constraints
- NO login/account/session system; no credential storage beyond the single env secret.
- No scheduler/queue/retry/polling. Append-only project/ untouched. No link/, agent/, brick/ edits. No pin weakening.
- Write scope: support/* only. Korean UI primary; no i18n machinery.

## Proof required (run, report honestly)
- Bake verb round-trip via python3 (no node).
- Production fail-closed: prove by reading the code branch + a focused unit-style probe if executable without node; otherwise state the static proof precisely.
- All FIRE outputs. Full gate exit code.
