#!/usr/bin/env sh
# Local release gate for Brick Protocol support evidence.
#
# Runs the same local checks the CI workflow calls before a release:
#   1. Python compileall over active source/support roots
#   2. check_profile.py --all
#   3. release_export.sh into a temporary dry-run tree
#
# This script does not tag, push, choose Movement, judge quality, or change
# GitHub repository settings. It exits non-zero on the first failed command.

set -eu

usage() {
    printf '%s\n' \
        "Usage: sh support/onboarding/release_gate.sh" \
        "" \
        "Runs compileall, check_profile.py --all, and a release-export dry-run."
}

main() {
    case "${1:-}" in
        --help | -h)
            usage
            return 0
            ;;
        "")
            ;;
        *)
            printf '%s\n' "release_gate: unknown argument: $1" >&2
            usage >&2
            return 2
            ;;
    esac

    repo_root="$(git rev-parse --show-toplevel)"
    export PYTHONPATH="$repo_root/support/import_identity${PYTHONPATH:+:$PYTHONPATH}"

    printf '%s\n' "1) compileall: brick agent link support"
    ( cd "$repo_root" && uv run python3 -m compileall -q brick agent link support )

    printf '%s\n' "2) checker gate: check_profile.py --all"
    ( cd "$repo_root" && uv run python3 support/checkers/check_profile.py --all )

    tmp_parent="${TMPDIR:-/tmp}"
    export_dir="$(mktemp -d "$tmp_parent/brick-release-gate.XXXXXX")"
    cleanup() {
        rm -rf "$export_dir"
    }
    trap cleanup EXIT HUP INT TERM

    printf '%s\n' "3) release export dry-run"
    ( cd "$repo_root" && sh support/onboarding/release_export.sh --output "$export_dir/export" )

    printf '%s\n' \
        "release gate passed as support evidence only." \
        "proof limit: this does not prove source truth, success, quality, Movement authority, branch protection, or real publication."
}

main "$@"
