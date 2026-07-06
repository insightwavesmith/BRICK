#!/usr/bin/env bash
# COO gate runner — deterministic mechanics of the landing gate.
# Judgment stays with the operator: design approval BEFORE this script,
# mutation spec authored BY the operator (passed as a python file that must
# exit 0 only when its mutations are RED-confirmed and restored), and the
# final merge decision AFTER reading the VERDICT block. This script never
# merges to main and never pushes.
#
# usage (gate): coo_gate_runner.sh <building_id> <vessel_root_abs> "<profiles...>" [mutspec.py]
# usage (land): coo_gate_runner.sh --land <harvest_sha> <merge_msg_file>
#   --land is the post-VERDICT mechanical tail the operator fires AFTER deciding
#   to merge: merge --no-ff && LIVE sweep && push, all-or-stop — any failure
#   halts the chain and prints the fingerprint (never pushes over a red sweep).
# usage (ship): coo_gate_runner.sh --ship
#   --ship is the NO-MERGE tail for commits already on main (doc/tool commits):
#   LIVE sweep && push only. The operator never hand-runs git push — already-on-
#   main commits go through --ship, harvest commits through --land (Smith 0706).
set -uo pipefail

REPO="${BRICK_REPO_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}"
PY="$REPO/.venv/bin/python"

if [ "${1:-}" = "--ship" ]; then
  say() { printf '%s\n' "$*"; }
  git -C "$REPO" fetch origin >/dev/null 2>&1
  AHEAD=$(git -C "$REPO" rev-list --count origin/main..main 2>/dev/null)
  if [ "${AHEAD:-0}" -eq 0 ]; then
    say "NOTHING TO SHIP: main is not ahead of origin/main"
    exit 1
  fi
  say "== COO SHIP: $AHEAD commit(s) ahead — live sweep then push"
  ( cd "$REPO" && PYTHONPATH="$REPO/support/import_identity" python3 support/checkers/check_profile.py --all ) > /tmp/coo-ship-sweep.log 2>&1
  RC=$?
  CNT=$(grep -c '^profile passed' /tmp/coo-ship-sweep.log)
  say "live sweep: rc=$RC profiles=$CNT"
  if [ $RC -ne 0 ]; then
    say "SHIP: SWEEP RED — push blocked (fingerprint below)"
    grep -m3 'rejected\|Error' /tmp/coo-ship-sweep.log | sed 's/^/  /'
    exit 1
  fi
  git -C "$REPO" push origin main 2>&1 | tail -2
  say "== SHIP: PUSHED $(git -C "$REPO" rev-parse --short origin/main 2>/dev/null)"
  exit 0
fi

if [ "${1:-}" = "--land" ]; then
  SHA="$2"; MSGF="$3"
  say() { printf '%s\n' "$*"; }
  # SHA accepts a comma-separated list: each merged in order (msgfile may hold
  # multiple messages separated by lines of exactly '---'), ONE sweep+push tail.
  IFS=',' read -r -a SHAS <<< "$SHA"
  i=0
  for ONE in "${SHAS[@]}"; do
    i=$((i+1))
    # REFUSE meaningless input (0706 Smith correction): a sha already contained
    # in main merges as a silent no-op ("already up to date") — that is NOT a
    # landing. --land exists ONLY to bring a gate-worktree harvest commit onto
    # main. Already-on-main commits take the sweep&&push path instead.
    if git -C "$REPO" merge-base --is-ancestor "$ONE" HEAD 2>/dev/null; then
      say "NOTHING TO LAND: $ONE is already on main. --land가 아니라 --ship을 써라:"
      say "  $0 --ship"
      exit 1
    fi
    MSG_PART="/tmp/coo-land-msg-$i.txt"
    awk -v n="$i" 'BEGIN{c=1} /^---$/{c++; next} c==n{print}' "$MSGF" > "$MSG_PART"
    [ -s "$MSG_PART" ] || cp "$MSGF" "$MSG_PART"
    say "== COO LAND: merge $ONE"
    git -C "$REPO" merge --no-ff "$ONE" -F "$MSG_PART" || { say "LAND: MERGE FAILED at $ONE"; exit 1; }
    say "merged: $(git -C "$REPO" log -1 --format=%h)"
  done
  ( cd "$REPO" && PYTHONPATH="$REPO/support/import_identity" python3 support/checkers/check_profile.py --all ) > /tmp/coo-land-sweep.log 2>&1
  RC=$?
  CNT=$(grep -c '^profile passed' /tmp/coo-land-sweep.log)
  say "live sweep: rc=$RC profiles=$CNT"
  if [ $RC -ne 0 ]; then
    say "LAND: SWEEP RED — push blocked (fingerprint below)"
    grep -m3 'rejected\|Error' /tmp/coo-land-sweep.log | sed 's/^/  /'
    exit 1
  fi
  git -C "$REPO" push origin main 2>&1 | tail -2
  say "== LAND: PUSHED $(git -C "$REPO" rev-parse --short origin/main 2>/dev/null)"
  exit 0
fi
B="$1"; VESSEL="$2"; PROFILES="$3"; MUTSPEC="${4:-}"
WT="$HOME/.brick/worktrees/$B"
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
# orphan-harvest mode: VESSEL="-" skips the close (walk died mid-flight, no
# hold to dispose — outputs are harvested and gated; ledger disposition is a
# separate operator decision).
if [ "$VESSEL" = "-" ]; then
  say "close: SKIPPED (orphan-harvest mode)"
else
CLOSE=$(BRICK_GATE_REPO="$REPO" PYTHONPATH="$REPO/support/import_identity:$REPO" "$PY" - "$VESSEL" "$WT" <<'EOF'
import json, os, sys
from brick_protocol.support.operator.onboard import run_approve_entry
vessel, wt = sys.argv[1], sys.argv[2]
kw = dict(action="forward", author_ref="coo:smith",
          repo_root=os.environ["BRICK_GATE_REPO"], adapter_timeout_seconds=600)
r = run_approve_entry(vessel, **kw)
if r.get("error_kind") == "resume_requires_isolated_adapter_cwd":
    r = run_approve_entry(vessel, adapter_cwd=wt, **kw)
print(json.dumps({k: str(r.get(k))[:80] for k in ("ok", "frontier_kind", "error_kind")}))
EOF
)
say "close: $CLOSE"
case "$CLOSE" in *'"frontier_kind": "complete"'*) ;; *) say "VERDICT: CLOSE-NOT-COMPLETE (operator review needed)"; FAIL=1;; esac
fi

# 3) harvest commit
# COO_GATE_HARVEST_SHA overrides worktree harvest — for single-call completed
# walks whose worktree is already disposed and whose output lives in a
# dangling "BRICK building output" commit.
HARVEST="${COO_GATE_HARVEST_SHA:-}"
if [ -z "$HARVEST" ]; then
HARVEST=""
if [ -d "$WT" ] && [ -n "$(git -C "$WT" status --porcelain)" ]; then
  git -C "$WT" add -A brick link support >/dev/null 2>&1 || git -C "$WT" add -A >/dev/null
  git -C "$WT" commit -q -m "BRICK building output (COO harvest via gate runner): $B"
fi
[ -d "$WT" ] && HARVEST=$(git -C "$WT" rev-parse HEAD 2>/dev/null)
fi
if [ -z "$HARVEST" ]; then
  say "VERDICT: NO-HARVEST (no worktree output and no COO_GATE_HARVEST_SHA — refusing a bare-main vacuous gate)"
  exit 1
fi
say "harvest: $HARVEST"

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
  ( cd "$GATE" && PYTHONPATH="$GATE/support/import_identity:$GATE" python3 support/checkers/check_profile.py --profile "$P" ) > "/tmp/coo-gate-$B-$P.log" 2>&1
  RC=$?
  say "profile $P: rc=$RC"
  [ $RC -ne 0 ] && { FAIL=1; tail -3 "/tmp/coo-gate-$B-$P.log" | sed 's/^/  /'; }
done

# 6) operator-authored mutation spec (must self-restore; exit 0 = RED confirmed)
# skipped when any focused profile already failed — mutations against a red
# baseline prove nothing (red-for-the-wrong-reason class).
if [ -n "$MUTSPEC" ] && [ $FAIL -ne 0 ]; then
  say "mutation-spec: SKIPPED (focused baseline not green)"
elif [ -n "$MUTSPEC" ]; then
  ( cd "$GATE" && PYTHONPATH="$GATE/support/import_identity:$GATE" python3 "$MUTSPEC" ) > "/tmp/coo-gate-$B-mut.log" 2>&1
  RC=$?
  say "mutation-spec: rc=$RC $([ $RC -eq 0 ] && echo RED-CONFIRMED || echo FAILED)"
  [ $RC -ne 0 ] && { FAIL=1; tail -5 "/tmp/coo-gate-$B-mut.log" | sed 's/^/  /'; }
  git -C "$GATE" diff --quiet || { say "mutation-spec: RESTORE FAILED (tree dirty)"; FAIL=1; }
fi

# 7) isolated full sweep
( cd "$GATE" && PYTHONPATH="$GATE/support/import_identity" python3 support/checkers/check_profile.py --all ) > "/tmp/coo-gate-$B-all.log" 2>&1
RC=$?
CNT=$(grep -c '^profile passed' "/tmp/coo-gate-$B-all.log")
say "isolated --all: rc=$RC profiles=$CNT"
[ $RC -ne 0 ] && { FAIL=1; grep -m2 'rejected\|Error' "/tmp/coo-gate-$B-all.log" | sed 's/^/  /'; }

GATESHA=$(git -C "$GATE" rev-parse HEAD 2>/dev/null)
say "== VERDICT: $([ $FAIL -eq 0 ] && echo GREEN || echo NEEDS-OPERATOR) harvest=$HARVEST gate=$GATESHA"
say "   merge cmd (operator decision): git -C $REPO merge --no-ff $HARVEST -m '<verdict message>'"
exit $FAIL
