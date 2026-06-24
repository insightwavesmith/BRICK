BRICK COO declared P2 measurement Building: checker/profile diet measurement.

Context:
- The long goal says after QA concern emission policy root fix, next is checker/profile diet measurement.
- 426594d (checker progress/timebox guard) is classified as mitigation, not root diet.
- Recent --all attempt showed progress heartbeat works, but onboard_seam_case can run for 5+ minutes because it touches real provider/onboarding paths; this reinforces the need to split core/dogfood/heavy/historical profiles.

Required read-only work:
1. Inventory current support/checkers/profiles/*.yaml and support/checkers/check_profile.py behavior.
2. Identify which profiles/rules are core invariant checks versus dogfood/live-provider/heavy/historical checks.
3. Identify duplicate or over-broad checker mechanisms and any dead/stale profile names.
4. Produce a measurement report with exact evidence refs/file paths/commands that a later implementation Building can use.
5. Keep BRICK boundaries explicit:
   - Brick = checker/profile diet measurement work.
   - Agent = returned evidence/report only.
   - Link = next Movement candidate only, not chosen by the report.
   - support/checkers = support evidence only, not source truth/quality/success/Movement authority.

Do not edit files. Do not run git commit or push. Avoid --all. Use bounded direct measurements only.
