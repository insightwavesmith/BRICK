#!/usr/bin/env bash
# COO gate runner — deterministic mechanics of the landing gate.
# Judgment stays with the operator: design approval BEFORE this script,
# mutation spec authored BY the operator (passed as a python file that must
# exit 0 only when its mutations are RED-confirmed and restored), and the
# final merge decision AFTER reading the VERDICT block. This script never
# merges to main and never pushes.
#
# usage: coo_gate_runner.sh <building_id> <vessel_root_abs> "<profile1 profile2 ...>" [mutspec.py]
set -uo pipefail

REPO=/Users/smith/projects/BRICK
PY="$REPO/.venv/bin/python"
B="$1"; VESSEL="$2"; PROFILES="$3"; MUTSPEC="${4:-}"
WT="/Users/smith/.brick/worktrees/$B"
GATE="/private/tmp/coo-gate-$B"
SNAP="/tmp/coo-gate-$B-snapshot.patch"
FAIL=0

say() { printf '%s\n' "$*"; }

say "== COO GATE RUNNER: $B"

# 1) snapshot (loss-proof before any disposition)
if [ -d "$WT" ]; then
  git -C "$WT" diff > "$SNAP" 2>/dev/null
  say "snapshot: $(wc -l < "$SNAP" | tr -d ' ') lines -> $SNAP"
  git -C "$WT" status --short | sed 's/^/  wt /'
fi

# 2) forward-close (fallback: explicit engine worktree cwd)
CLOSE=$(PYTHONPATH="$REPO/support/import_identity:$REPO" "$PY" - "$VESSEL" "$WT" <<'EOF'
import json, sys
from brick_protocol.support.operator.onboard import run_approve_entry
vessel, wt = sys.argv[1], sys.argv[2]
kw = dict(action="forward", author_ref="coo:smith",
          repo_root="/Users/smith/projects/BRICK", adapter_timeout_seconds=600)
r = run_approve_entry(vessel, **kw)
if r.get("error_kind") == "resume_requires_isolated_adapter_cwd":
    r = run_approve_entry(vessel, adapter_cwd=wt, **kw)
print(json.dumps({k: str(r.get(k))[:80] for k in ("ok", "frontier_kind", "error_kind")}))
EOF
)
say "close: $CLOSE"
case "$CLOSE" in *'"frontier_kind": "complete"'*) ;; *) say "VERDICT: CLOSE-NOT-COMPLETE (operator review needed)"; FAIL=1;; esac

# 3) harvest commit
HARVEST=""
if [ -d "$WT" ] && [ -n "$(git -C "$WT" status --porcelain)" ]; then
  git -C "$WT" add -A brick link support >/dev/null 2>&1 || git -C "$WT" add -A >/dev/null
  git -C "$WT" commit -q -m "BRICK building output (COO harvest via gate runner): $B"
fi
[ -d "$WT" ] && HARVEST=$(git -C "$WT" rev-parse HEAD 2>/dev/null)
say "harvest: ${HARVEST:-<none>}"

# 4) gate worktree at current main + merge
git -C "$REPO" worktree remove --force "$GATE" >/dev/null 2>&1
git -C "$REPO" worktree add "$GATE" --detach main >/dev/null 2>&1 || { say "VERDICT: GATE-WORKTREE-FAILED"; exit 1; }
if [ -n "$HARVEST" ]; then
  if ! git -C "$GATE" merge --no-commit --no-ff "$HARVEST" >/dev/null 2>&1; then
    say "VERDICT: MERGE-CONFLICT (operator resolution needed)"
    git -C "$GATE" status --short | head -12 | sed 's/^/  /'
    exit 1
  fi
  git -C "$GATE" commit -q -m "GATE-LOCAL $B"
fi

# 5) focused profiles
for P in $PROFILES; do
  PYTHONPATH="$GATE/support/import_identity:$GATE" python3 "$GATE/support/checkers/check_profile.py" --profile "$P" > "/tmp/coo-gate-$B-$P.log" 2>&1
  RC=$?
  say "profile $P: rc=$RC"
  [ $RC -ne 0 ] && { FAIL=1; tail -3 "/tmp/coo-gate-$B-$P.log" | sed 's/^/  /'; }
done

# 6) operator-authored mutation spec (must self-restore; exit 0 = RED confirmed)
if [ -n "$MUTSPEC" ]; then
  ( cd "$GATE" && PYTHONPATH="$GATE/support/import_identity:$GATE" python3 "$MUTSPEC" ) > "/tmp/coo-gate-$B-mut.log" 2>&1
  RC=$?
  say "mutation-spec: rc=$RC $([ $RC -eq 0 ] && echo RED-CONFIRMED || echo FAILED)"
  [ $RC -ne 0 ] && { FAIL=1; tail -5 "/tmp/coo-gate-$B-mut.log" | sed 's/^/  /'; }
  git -C "$GATE" diff --quiet || { say "mutation-spec: RESTORE FAILED (tree dirty)"; FAIL=1; }
fi

# 7) isolated full sweep
PYTHONPATH="$GATE/support/import_identity" python3 "$GATE/support/checkers/check_profile.py" --all > "/tmp/coo-gate-$B-all.log" 2>&1
RC=$?
CNT=$(grep -c '^profile passed' "/tmp/coo-gate-$B-all.log")
say "isolated --all: rc=$RC profiles=$CNT"
[ $RC -ne 0 ] && { FAIL=1; grep -m2 'rejected\|Error' "/tmp/coo-gate-$B-all.log" | sed 's/^/  /'; }

GATESHA=$(git -C "$GATE" rev-parse HEAD 2>/dev/null)
say "== VERDICT: $([ $FAIL -eq 0 ] && echo GREEN || echo NEEDS-OPERATOR) harvest=$HARVEST gate=$GATESHA"
say "   merge cmd (operator decision): git -C $REPO merge --no-ff $HARVEST -m '<verdict message>'"
exit $FAIL
