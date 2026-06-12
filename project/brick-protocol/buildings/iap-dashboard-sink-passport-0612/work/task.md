# IAP 통행증 — dashboard 싱크 Authorization 헤더 배선

## Reproduced facts (operator-verified, 2026-06-12)
1. Cloud Run integrated IAP (service brick-dashboard, asia-northeast3) REJECTS machine
   POST /ingest unless the request carries Authorization: Bearer <JWT> where the JWT is
   signed DIRECTLY with the service account private key (RS256; header kid=private_key_id;
   claims iss=sub=email=SA client_email) and aud equals the EXACT endpoint URL INCLUDING
   PATH (aud=https://.../ingest for POST /ingest; root aud gets 401 "Audience specified
   does not match requested endpoint"). gcloud print-identity-token is rejected with 401
   for EVERY audience (Google-managed OAuth client, not allowlisted for that flow).
2. Operator E2E proof exists today (manual probe): signed JWT + x-ingest-secret header ->
   POST /ingest HTTP 200 {"ok":true,...}; live browsers received the delta instantly.
3. Current code: support/operator/report_sinks.py _post_dashboard_projection builds the
   request with ONLY Content-Type + x-ingest-secret. Both send_dashboard_building_delta
   and send_dashboard_seed flow through this ONE seam. Result: every sink POST to an
   IAP-enabled deployment fails closed -> dashboard auto-update is dead unless an
   operator pushes by hand.
4. The SA key JSON (fields client_email / private_key_id / private_key) lives MACHINE-LOCAL
   (operator keeps it outside the repo). The operator probe signed with the openssl CLI
   (subprocess) — zero new python dependencies.

## Objective
report-sink:dashboard attaches the IAP passport (Authorization: Bearer <SA-signed JWT>)
when (and ONLY when) a key-path environment variable is present, so an IAP-enabled
dashboard accepts machine pushes end-to-end. Stateless per-send signing; behavior with
the env absent stays byte-identical to today.

## Deliverables
1. Env contract: new BRICK_DASHBOARD_SA_KEY_PATH (filesystem path to the SA key JSON;
   machine-local layer; the VALUE never appears in repo files, fixtures, logs, or
   returns). Absent -> request headers UNCHANGED vs today (no Authorization; IAP-off
   deployments keep working). Present -> add Authorization: Bearer <JWT>:
   header {alg:RS256, typ:JWT, kid:<private_key_id>}, claims {iss=sub=email=<client_email>,
   aud=<EXACT value of BRICK_DASHBOARD_INGEST_URL>, iat=now, exp=now+600}, signature via
   openssl subprocess (openssl dgst -sha256 -sign <keyfile>) over header.claims —
   NO new python dependency, NO IAM/network call for signing, NO token caching.
2. Extend _dashboard_environment_presence with the new env key (record "present"/"absent"
   strings only — never values).
3. Checker pin (extend the existing dashboard/reporter kernel-check family, OFFLINE only —
   checkers must NOT touch the network): drive the request-building path with a captured
   transport (the same monkeypatch/sender seam the existing reporter checks use) and a
   THROWAWAY RSA key GENERATED at check time in a temp dir (openssl genrsa; never commit
   any key material):
   a. key env present -> Authorization header present; JWT has 3 dot-segments; decoded
      header kid == throwaway key id; decoded claims aud == the configured ingest URL.
   b. key env absent -> NO Authorization header and the header set equals today's
      (regression parity).
   c. Mutation probe: with the Authorization-attachment removed, the pin fires RED.
4. Secrets discipline: never log/record/return private key bytes, JWT strings, or env
   values; observations carry only env presence + HTTP status classes (existing rule).

## Proof required (run yourself, report honestly — claims only from execution)
- python compileall on changed files; git diff --check.
- Focused run of the kernel check family containing the new pin: green; mutation -> RED
  (show both observations).
- Full gate in a TEMP SOURCE COPY of this worktree (state the copy path):
  bake_dashboard_data_json() in the copy first, then
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity python3
  support/checkers/check_profile.py --all -> exit 0.
- Do NOT call the real dashboard or any network from checkers or from your proof runs.
  The real IAP E2E send is the OPERATOR's FIRE after merge, not yours.

## Hard constraints (law)
- write_scope support/* only; no link/, agent/, brick/, project/ edits; append-only
  history; no pin weakening or relocation.
- No scheduler / queue / retry / timer / token cache; stateless per-send signing only.
- No new dependencies (stdlib + openssl subprocess only).
- Plain-text refs only in returns — never echo packet structures (handoff_refs etc.)
  into report fields. No npm/node execution inside the worktree.
