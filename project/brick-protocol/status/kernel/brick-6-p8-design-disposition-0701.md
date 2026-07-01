# P8 design Building disposition (0701)

Status: COO disposition on a paused design-only Building. Not source truth,
success judgment, quality judgment, or Movement authority.

## Building result

`brick-6-p8-ship-safety-design-0701a`, `frontier_kind=link_paused` (not
complete). Dual-design (Codex + Claude) produced a well-grounded 5-lane
implementation recommendation (file:line citations for every current-state
claim) and gemini-local design-QA correctly flagged a non-binding
`design_gap` concern: the proposed Lane 3 (dashboard ingest) and Lane 4
(dashboard deploy/container) both potentially touch
`support/dashboard/server/index.mjs`, which would make them unsafe to run
as fully parallel work lanes without merge coordination -- unless the
in-app-auth-vs-external-wall question is resolved first. The design's own
`not_proven` list correctly named this and two other open policy questions
(matching the phase doc's own anticipated "Operator Questions").

## COO decisions (resolving the 3 open policy questions)

1. **uv.lock: commit it.** Standard reproducibility practice for a shipped
   product (not a library). Remove the `.gitignore` exclusion. Small,
   low-risk, well-understood.
2. **CI/branch-protection: build the workflow FILE + a local release-gate
   script now; do NOT enable actual GitHub branch-protection settings in
   this Building.** Turning on required-status-checks is a GitHub repo
   admin action affecting shared infrastructure -- outside a Building's
   autonomous scope. The `.github/workflows/*.yaml` file plus a callable
   local gate script gets built; "branch protection actually enforced" stays
   explicitly `not_proven` pending a separate Smith action.
3. **Dashboard viewer auth: required EXTERNAL WALL, not in-app auth.**
   BRICK is not yet a mature multi-tenant hosted product; building real
   in-app authentication is a nontrivial security-sensitive scope expansion
   this phase should not absorb. Document it as a required external
   precondition (reverse proxy / VPN / firewall) instead. This resolves the
   Lane 3/4 file-overlap concern directly: Lane 4 does not touch
   `index.mjs` at all under this disposition.

## Resulting corrected 5-lane breakdown (file-disjoint, confirmed)

1. Release export hardening -- `support/onboarding/release_export.sh`,
   `support/checkers/lib/install_release_export_lint_check.py`.
2. Dependency/install/release-gate evidence -- `.gitignore`, `uv.lock`,
   `support/onboarding/install.sh`, `README.md`/`support/docs/references/*.md`,
   new `.github/workflows/*.yaml` + local gate script.
3. Dashboard ingest integrity -- `support/dashboard/server/index.mjs`,
   `support/operator/report_sinks.py` (delivery side), checker coverage.
4. Dashboard deploy/container hardening -- `support/dashboard/Dockerfile`,
   `support/dashboard/DEPLOY.md` only (external-wall documentation, no
   `index.mjs` touch per decision 3 above).
5. Provider boundary/customer matrix + CLI projection --
   `support/operator/cli.py`, `support/connection/adapter_constants.py`,
   `support/connection/adapter_local_cli.py`, `support/connection/agent_adapter.py`,
   matching checker/profile coverage.

## Not proven (carried forward from design, still open)

Fresh-machine install behavior, runtime behavior of the 3 hardened scripts,
credential validity, provider availability, Slack/dashboard real delivery,
customer comprehension of the revised docs, checker green after
implementation. All explicit per-lane in the follow-on Building.

## Next Movement candidate

Declare and fire the corrected 5-lane implementation Building
(`brick-6-p8-ship-safety-impl-0701a`), work lanes only (design already
done here) -> QA fan-out (code-attack-qa / axis-attack-qa / evidence-integrity)
-> closure, using the `assemble()` DSL per Global Operating Rule 10.
