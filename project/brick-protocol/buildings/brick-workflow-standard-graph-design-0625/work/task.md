Design-first Building: define the standard BRICK-style Claude Workflow graph after the recent P0 stabilizations.

Objective:
Produce a design report for the standard operating graph that makes BRICK feel like Claude Workflow while preserving Brick/Agent/Link law.

Must cover:
1. Workflow UX: user asks task -> COO draws graph -> design/work/QA/closure execute.
2. BAL mapping: every node is a Brick, every performer is an Agent, every edge is a Link.
3. Design-first policy: when to run Design before Work; when direct Work is allowed.
4. Recommended graph:
   - Design Brick (Fugu or Claude)
   - COO middle review/gate
   - Work Brick (Codex/execution-capable)
   - QA fan-out (Claude reasoning QA + Codex execution QA + Gemini/Fugu as needed)
   - Closure Brick (COO)
5. How to use Claude now that ec43f0b fixed --allowedTools: where Claude can be execution QA, where still read-only/design is safer.
6. Link/HOLD/reroute policy for QA concerns and reroute replay.
7. Checker/profile expectations per phase: quick/core vs dogfood/heavy.
8. Concrete next Building plan from here to P7 customer dogfood capstone.

Constraints:
- Read-only design/report; no source edits.
- No success/quality/source-truth claims.
- Return observed evidence, recommended graph, not_proven, and next movement candidates.
