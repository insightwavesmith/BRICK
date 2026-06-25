# G5 checker/profile diet implementation plan
Read-only design Building for the actual P9 diet implementation after B1 reference doc.
Required analyses:
1. Use support/docs/references/checker-profile-map.md as the current reference.
2. Design B2 and B3 as one implementation Building with internal serial order: B2 split building_skill_preset_agent_tool_hardening, then B3 provider runtime smoke split.
3. Identify exact write scopes and core.yaml/path_allowlist changes.
4. Name the checker-first verifier plan and FIRE/mutation expectations.
5. State which parts must not be parallelized because of core.yaml/checker-lib chokepoints.
6. Do not edit files in this Building.
Return a precise implementation plan, stop conditions, not_proven, and next proposed write Building.
