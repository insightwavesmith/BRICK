#!/usr/bin/env sh
# Local release gate for Brick Protocol support evidence.
#
# Runs the same local checks the CI workflow calls before a release:
#   1. Python compileall over active source/support roots
#   2. check_profile.py --all
#   3. brick verify --self-test
#   4. support/dashboard npm ci + build
#   5. release_export.sh negative denylist probe
#   6. release_export.sh into a temporary dry-run tree
#
# This script does not tag, push, choose Movement, judge quality, or change
# GitHub repository settings. It exits non-zero on the first failed command.

set -eu

usage() {
    printf '%s\n' \
        "Usage: sh support/onboarding/release_gate.sh" \
        "" \
        "Runs compileall, check_profile.py --all, brick verify --self-test, dashboard build, release_export negative probe, and a release-export dry-run."
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

    printf '%s\n' "3) CLI self-test: brick verify --self-test"
    ( cd "$repo_root" && uv run brick verify --self-test )

    printf '%s\n' "4) dashboard build: support/dashboard npm ci + build"
    if ! command -v node >/dev/null 2>&1; then
        printf '%s\n' "release_gate: node is required for the dashboard build" >&2
        return 1
    fi
    if ! command -v npm >/dev/null 2>&1; then
        printf '%s\n' "release_gate: npm is required for the dashboard build" >&2
        return 1
    fi
    ( cd "$repo_root/support/dashboard" && npm ci )
    ( cd "$repo_root/support/dashboard" && npm run build )

    tmp_parent="${TMPDIR:-/tmp}"
    export_dir="$(mktemp -d "$tmp_parent/brick-release-gate.XXXXXX")"
    negative_export_dir="$(mktemp -d "$tmp_parent/brick-release-gate-negative.XXXXXX")"
    deny_probe_path="$repo_root/.env.release-export-deny-probe"
    cleanup() {
        rm -rf "$export_dir"
        rm -rf "$negative_export_dir"
        rm -f "$deny_probe_path"
    }
    trap cleanup EXIT HUP INT TERM

    printf '%s\n' "5) release_export negative probe: deny forbidden local/provider path"
    printf '%s\n' "synthetic probe path: local release_export denylist input" > "$deny_probe_path"
    if (
        cd "$repo_root" &&
        sh support/onboarding/release_export.sh --output "$negative_export_dir/export" --include-untracked --allow-dirty
    ) > "$negative_export_dir/stdout.log" 2> "$negative_export_dir/stderr.log"; then
        printf '%s\n' "release_gate: release_export negative probe unexpectedly passed" >&2
        cat "$negative_export_dir/stdout.log" >&2
        cat "$negative_export_dir/stderr.log" >&2
        return 1
    fi
    if ! grep -q "secret/local/provider/session path denylist matched export input" "$negative_export_dir/stderr.log"; then
        printf '%s\n' "release_gate: release_export negative probe failed for the wrong reason" >&2
        cat "$negative_export_dir/stdout.log" >&2
        cat "$negative_export_dir/stderr.log" >&2
        return 1
    fi
    rm -f "$deny_probe_path"
    printf '%s\n' "release_export negative probe rejected forbidden file as expected"

    printf '%s\n' "6) release export dry-run"
    ( cd "$repo_root" && sh support/onboarding/release_export.sh --output "$export_dir/export" )

    printf '%s\n' \
        "release gate passed as support evidence only." \
        "proof limit: this does not prove source truth, success, quality, Movement authority, branch protection, or real publication."
}

main "$@"
