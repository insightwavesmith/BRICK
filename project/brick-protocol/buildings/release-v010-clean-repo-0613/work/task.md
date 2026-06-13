# Release v0.1.0 prep — clean-repo export verb + deploy buttons + AI-runnable onboarding

## Operator pre-analysis (VERIFIED inventory, 0613 — bounded)
Read ONLY: README.md, support/onboarding/install.sh, support/dashboard/DEPLOY.md,
support/dashboard/Dockerfile + server/index.mjs (env contract), support/docs/references/
(quickstart/setup), and support/checkers/check_profile.py --help surface.
VERIFIED facts you may rely on (do not re-derive):
- 동네 = project/ (3,801 tracked files, 27MB incl. status inbox) — EXCLUDED from release.
- No tracked secrets/.env (operator-verified scan). brick_protocol.egg-info = build artifact.
- Checkers tolerate an EMPTY project/: building_lifecycle_path_shape (require_candidate
  =False, missing dir -> []), project_declaration (absent dir -> 0 inspected),
  evidence_spine (empty roots), pin estate (0 blocks), dashboard bake (buildings: []).
- install.sh is parametric (BRICK_REPO env; insightwavesmith/BRICK appears in COMMENTS
  + README examples only). Dockerfile = 2-stage node:22-slim, port 8080;
  server env: NODE_ENV=production + INGEST_SECRET required for real ingest; PORT opt.
- Smith decisions: release form = CLEAN PUBLIC REPO; tag v0.1.0; deploy buttons 2종
  (Vercel=static photo / Docker host=realtime); 배포판=동네 제외.

## Objective
A single operator-runnable EXPORT VERB produces a clean release tree (no 동네), and the
docs let an OPERATOR AI go clone -> install -> first building -> dashboard from text
alone (commands + expected outputs + failure signals).

## Deliverables
1. support/onboarding/release_export.sh (or .py under support/operator/ — pick one,
   justify): builds a CLEAN TREE from HEAD excluding project/** and
   brick_protocol.egg-info/**, initializes a fresh git repo in an output dir with a
   single initial commit, ready to push to a NEW public repo + tag v0.1.0. It must
   create an EMPTY project/ scaffold? NO — decide: ship WITHOUT project/ entirely
   (checkers tolerate absence — verified above) and let the first onboard run create
   the vessel; document this in DEPLOY/README. The verb prints the follow-up commands
   (git remote add / push / tag) but does NOT push anything itself.
2. README.md: add a Deploy section with the two buttons/paths — (a) Vercel static
   (photo mode: bake -> vite build -> deploy dist; no server) and (b) Docker realtime
   (Dockerfile; NODE_ENV=production, INGEST_SECRET, optional IAP note pointing to
   support/dashboard/DEPLOY.md). Replace bare insightwavesmith examples with {OWNER}
   placeholders (keep ONE 'working example' line — Smith's allowance). Korean voice
   consistent with the existing README.
3. AI-runnable onboarding pass: README quickstart + support/docs/references/quickstart.md
   — every step gains (command / expected output line / failure signal). Include the
   operator-session standard: inbox watch loop (운영자 세션 = status inbox 감시 장착)
   per the wake-loop standard.
4. Checker pins: install_script_lint stays green; product_no_smith_residue stays green
   (the {OWNER} substitution must not break the working-example allowance); a NEW small
   pin asserting the export verb's exclusion list contains project/ (mutation: drop the
   exclusion -> RED).
5. The export verb is OPERATOR-run after merge (your proof uses a temp output dir).

## Proof required (run yourself, honestly)
- Run the export verb to a TEMP dir; in that exported tree run: bake_dashboard_data_json()
  then check_profile.py --all -> exit 0 WITH NO project/ present (this proves the
  clean-clone gate story end-to-end). State the temp paths.
- Focused: install_script_lint + product_no_smith_residue green; new exclusion pin
  mutation RED.
- Full gate in TEMP SOURCE COPY of this worktree (bake first, --all exit 0).

## Hard constraints (law)
- write_scope: README.md + support/* ONLY. Forbidden: link/*, agent/*, brick/*,
  project/*, .git/*, AGENTS.md, pyproject.toml, uv.lock.
- The verb never pushes/tags by itself; no network in checkers; no scheduler; no new
  deps; no secrets in any output; no packet echo; no npm/node execution IN THE WORKTREE
  (the Vercel build instructions are DOCS — do not run npm yourself).
