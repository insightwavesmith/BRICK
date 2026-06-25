P6 GAP2 customer-entry readiness Building.

Objective: verify whether a fresh/customer-like session can discover and use the BRICK COO/operator path without the agent re-reading the whole repo or starting from frozen brick-protocol. This is read-only readiness first; do not edit files.

Check bounded surfaces:
- agent/objects/coo.yaml and generated/projection skill surfaces if present
- agent/skills/building-coordination and/or brick-task-author/task_intake surfaces
- support/connection/coo_sync.py, mcp_projection.py, agent_resources.py if needed
- onboarding/first-use/operator entry docs if present
- latest evidence: ea82b7d, bf407a1, 023cefe, 6faf3a0 and their building roots

Deliverable: a customer-entry readiness matrix with: what a new session reads first, how it identifies active worktree vs frozen repo, how it launches official Building route, what Slack/evidence root expectation is, what remains not_proven, and the minimum implementation Building needed if gaps exist.

Do not claim source truth/success/quality/Movement authority. Checker/model/Slack outputs are support evidence only.
