Read-only triage Building: identify remaining checker/profile drift after recent P0 repairs.

Context:
Recent work closed building_automation profile and Claude QA execution smoke. A separate broad profile drift was mentioned: building_skill_preset_agent_tool_hardening preset-count expected 27 vs observed 28 or similar. We need know whether this blocks P7 or can be deferred.

Objective:
Produce a read-only triage report listing remaining checker/profile drift that could block 4-LLM workflow validation or P7 customer dogfood.

Must inspect:
- support/checkers/profiles/*.yaml relevant to building_skill_preset_agent_tool_hardening and profile diet
- support/checkers/check_profile.py
- support/checkers/lib/kernel_checks.py
- brick/templates/presets/*.md and catalog yaml
- recent status/building evidence where this drift is reported: claude-qa-execution-fresh-smoke-0625 closure, checker-profile-diet guide, P5/P6 records.

Return:
- observed evidence with exact paths/check names
- which profile(s) are blockers for P7 vs deferrable
- minimal next repair Building if any
- not_proven

Constraints:
- Read-only; no source edits.
- No source truth/success/quality/Movement claims.
