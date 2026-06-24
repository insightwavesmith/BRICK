BRICK COO declared root-fix Building: close the remaining partial patch around QA concern emission policy.

Context:
- 88cd2cc proves Link can adopt a valid QA transition_concern_evidence and reroute/replay work.
- That proof is partial: it does not define or enforce when QA must emit transition_concern_evidence versus when QA must record not_proven only.
- Previous Building qa-concern-emission-policy-fix-0625 reached design/COO gate, then resume exposed an operator declaration error: write_scope.allowed_paths used bare directories. This v2 uses globbed write scopes.

Required work:
1. Inspect current Brick templates, QA return contracts, Link route policy, walker transition concern handling, and checker coverage relevant to transition_concern_evidence.
2. Implement the minimal root fix so QA policy is explicit and covered:
   - Real upstream implementation/design/boundary defect with an upstream work target should produce non-binding transition_concern_evidence that Link may adopt under declared policy.
   - Environment/runtime/provider/read-only/no-temp/live-not-run/missing-probe cases should be recorded as not_proven or verification gap evidence without automatically requesting reroute.
   - Preserve truth-before-quality: QA does not judge success/failure/approval, and support/checkers remain support evidence only.
3. Add or adjust checker/profile coverage so the invariant is locked with positive and negative evidence.
4. Keep Brick/Agent/Link/support ownership separated; do not add a new Movement literal, fact class, scheduler, provider runtime, success judge, or quality judge.
5. Return exact changed files, commands/checkers run, narrowly_proven, not_proven, and next Movement candidate.

Operating constraints:
- Use the existing checker/profile framework where possible.
- Do not store credential/session/provider bodies.
- Do not run git commit or push.
