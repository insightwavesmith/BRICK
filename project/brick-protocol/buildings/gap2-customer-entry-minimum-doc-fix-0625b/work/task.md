P6 follow-on completion after adapter-timeout partial write from gap2-customer-entry-minimum-doc-fix-0625.

Context:
A prior official Building attempt timed out before AgentFact return, but left in-scope draft changes in:
- support/docs/references/quickstart.md
- project/brick-protocol/status/kernel/gap2-customer-entry-readiness-0625.md

Brick objective:
Review those draft changes against the P6 readiness gap, adjust only if necessary, run minimal verification, and return a proper AgentFact.

Grounding evidence to read first:
- git diff for the two draft files above
- project/brick-protocol/buildings/gap2-customer-entry-readiness-0625/work/step-outputs/*/step-output.json
- project/brick-protocol/status/kernel/gap2-customer-entry-readiness-0624.md
- support/docs/references/quickstart.md
- support/docs/references/launch-guide.md
- support/docs/references/setup.md
- support/operator/first_use.py
- support/operator/cli.py
- support/connection/coo_sync.py
- support/connection/mcp_projection.py
- support/connection/agent_resources.py
- README.md, AGENTS.md, project/brick-protocol/README.md if present

Required deliverable:
1. Ensure a populated customer-entry readiness matrix exists and covers:
   - what a fresh session reads first
   - how to distinguish active worktree / customer checkout from frozen/history repo
   - official Building launch route: run_building_intake / quickstart path
   - Slack expectation: when Slack is expected vs direct check not expected
   - evidence-root expectation: project/brick-protocol/buildings/<building-id>/...
   - not_proven / proof limits
2. Keep edits narrow and inside write_scope. Do not change AGENTS.md constitution. Do not change runtime behavior unless absolutely necessary.
3. Run `git diff --check`. Run a narrow relevant checker/profile only if clearly discoverable without opening a long --all loop; otherwise mark checker coverage not_proven.
4. Return only required support evidence fields; no success/failure/quality/Movement verdict.
