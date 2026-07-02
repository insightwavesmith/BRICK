# GAP2 Customer Entry Readiness Support Record (0625)

Status: SUPPORT RECORD. This document records customer-entry readiness evidence
for the GAP2 follow-on. It is not source truth, not a success judgment, not a
quality judgment, and not Movement authority.

## Scope

This record closes the minimum documentation gap identified by
`gap2-customer-entry-readiness-0625`: a fresh/customer-like session needed one
populated matrix that ties the first-read path, active-checkout discriminator,
official Building launch route, Slack expectation, evidence root, and proof
limits together without sending the reader through the frozen/history repo.

## Readiness Matrix

| Cell | Current answer | Observed evidence | Not proven |
| --- | --- | --- | --- |
| Fresh session reads first | Repo-root `README.md` is the first landing page. It links to `support/docs/references/quickstart.md`, `support/docs/references/setup.md`, and `support/docs/references/three-axis-overview.md`. `quickstart.md` now carries the customer-entry readiness matrix. After `brick init`, the generated `FIRST_USE.md` is the first local output-root file to read. | `README.md`; `support/docs/references/quickstart.md`; `support/operator/first_use.py`; `project/brick-protocol/status/kernel/gap2-customer-entry-readiness-0624.md`. | Whether a new customer follows the sequence without human help. |
| Active worktree / customer checkout vs frozen history repo | Active work happens in this product checkout or a release export. The HISTORY repository named in `README.md` is archive/productization museum evidence only. `brick status` reports `repo_root`, `cwd`, `entrypoint_file`, `python_executable`, `brick_home`, and the default builds root so the customer can see which checkout is active. Release exports omit `project/`; first onboard/run may create local project evidence. | `README.md` release export and HISTORY sections; `support/operator/cli.py::_status_packet`; `support/docs/references/architecture-map.md` history note. | Fresh-machine release export parity; whether a confused customer always notices they are in the history repo. |
| Official Building launch route | Customer route for a clear preset task is `run_building_intake` with `task_statement`. Route for new structure is main-agent `assemble` -> persisted frozen proposal -> human/COO `onboard goal-approve` -> `run_building_plan`. The onboarding wizard also walks the same intake seam for the first local example. | `support/docs/references/quickstart.md`; `support/docs/references/launch-guide.md`; `support/operator/driver.py`; `support/operator/cli.py::_cmd_init`. | Provider-backed run behavior; semantic correctness of any chosen shape; customer quality/success. |
| Slack expectation | Slack is optional and not expected for the first local example or direct readiness check. Operator notification can use `~/.brick/report.env` after provisioning/source. Real Slack delivery remains gated by credentials and caller-declared delivery flags; default posture is no real delivery. | `support/docs/references/launch-guide.md`; `project/brick-protocol/status/kernel/install-ux-design-0618.md`; `AGENTS.md` reporter admission wording. | Real Slack delivery reliability, workspace permission state, and credential readiness. |
| Evidence root expectation | Repo-local Building evidence defaults to `project/brick-protocol/buildings/<building_id>/`. Important children are `capture/`, `raw/`, `evidence/`, and `work/step-outputs/`. Customer CLI packets report `evidence_root`; `FIRST_USE.md` repeats it for the local example. | `support/docs/references/quickstart.md`; `support/docs/references/setup.md`; `support/operator/cli.py::_render_build`; `support/operator/first_use.py`. | External transcript from clone/install/pipx/brick init/FIRST_USE/brick verify on a fresh customer machine. |
| Proof limits | Docs, checkers, dashboards, `FIRST_USE.md`, and status records are support evidence only. They do not decide source truth, success, quality, Movement, route target, provider readiness, or future Building correctness. | `AGENTS.md`; `support/docs/references/quickstart.md`; `support/docs/references/setup.md`; 0624 and 0625 GAP2 Building step outputs. | Human comprehension and real-world customer adoption. |

## Observed Evidence

- `project/brick-protocol/buildings/gap2-customer-entry-readiness-0625/work/step-outputs/*/step-output.json`
  recorded the gap: the populated matrix had not been authored, and the
  active-worktree-vs-frozen discriminator was still unconfirmed.
- `project/brick-protocol/status/kernel/gap2-customer-entry-readiness-0624.md`
  already mapped the source-level entry chain:
  install script -> `brick` console entrypoint -> `brick init` ->
  local example -> `FIRST_USE.md` -> `brick verify`.
- `support/operator/cli.py` exposes `brick status`, `brick init`, `brick build`,
  `brick verify`, `brick doctor`, and `brick auth login` support evidence
  commands. The status command is the smallest explicit active-checkout signal
  currently available to a customer-like session.
- `support/operator/first_use.py` renders `FIRST_USE.md` with the local example
  Building id, adapter, preset, frontier kind, evidence root, doctor
  observations, and real-provider next steps.
- `support/docs/references/quickstart.md` now contains the customer-entry
  readiness matrix as the first support-doc surface after the opening rule.

## P6 Follow-On Observation

- `support/docs/references/quickstart.md` was re-read after the adapter-timeout
  partial write. It contains a populated customer-entry readiness matrix with
  cells for first-read order, active checkout vs frozen/history repo,
  official Building launch route, Slack expectation, evidence root, and proof
  limits.
- The matrix stays in support documentation only: it does not change runtime
  behavior, Brick / Agent / Link contracts, `AGENTS.md`, gates, Movement, or
  customer Slack delivery behavior.
- `git diff --check` returned exit 0.
- `PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py
  --profile brick_cli_entrypoint` returned exit 0 and observed the `brick`
  entrypoint smoke plus `FIRST_USE.md` wizard path. This profile covers the
  customer-entry CLI/FIRST_USE surface, not the exact new matrix prose.

## Remaining Delta

1. Capture a fresh-machine or release-export transcript:
   clone -> install -> `brick init` -> `FIRST_USE.md` -> `brick verify`.
2. Measure provider-backed customer path behavior after provider-native auth.
3. Observe whether a new customer distinguishes this active checkout/release
   export from the HISTORY repository without human correction.
4. Keep Slack as optional unless a later Building admits a customer Slack setup
   flow with separate delivery evidence.

## Commands Recorded For This Follow-On

```text
sed -n '1,220p' agent/skills/scoped-implementation/SKILL.md
sed -n '1,220p' agent/skills/protocol-boundary-watch/SKILL.md
git status --short
rg --files project/brick-protocol/buildings/gap2-customer-entry-readiness-0625/work/step-outputs
sed -n '1,220p' project/brick-protocol/status/kernel/gap2-customer-entry-readiness-0624.md
sed -n '1,520p' support/docs/references/quickstart.md
sed -n '1,240p' support/docs/references/setup.md
sed -n '1,260p' support/operator/first_use.py
sed -n '1,620p' support/operator/cli.py
sed -n '1,260p' support/connection/coo_sync.py
sed -n '1,240p' support/connection/mcp_projection.py
sed -n '1,240p' support/connection/agent_resources.py
rg -n "Slack|slack|report.env|frozen|history|active worktree|customer checkout|FIRST_USE|run_building_intake|quickstart" README.md support/docs/references project/brick-protocol/status/kernel -g '*.md'
```

## Proof Limits

- This record is support evidence only.
- This record does not mutate `AGENTS.md`, Brick / Agent / Link contracts,
  runtime behavior, gate behavior, or Movement literals.
- This record does not prove provider behavior, Slack delivery, release export
  parity, customer comprehension, success, quality, source truth, or Movement
  authority.
