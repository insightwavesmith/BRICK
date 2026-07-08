#!/usr/bin/env sh
# Local release gate for Brick Protocol support evidence.
#
# Runs the same local checks the CI workflow calls before a release:
#   1. Python compileall over active source/support roots
#   2. check_profile.py --all
#   3. brick verify --self-test
#   4. wheel smoke: build wheel and verify installed brick console entry
#   5. brick_protocol/support/dashboard npm ci + build
#   6. release_export.sh negative denylist probe
#   7. release_export.sh into a temporary dry-run tree + clean-boundary output scan
#   8. release_product_manifest negative probe when the manifest is present
#
# This script does not tag, push, choose Movement, judge quality, or change
# GitHub repository settings. It exits non-zero on the first failed command.

set -eu

usage() {
    printf '%s\n' \
        "Usage: sh brick_protocol/support/onboarding/release_gate.sh" \
        "" \
        "Runs compileall, check_profile.py --all, brick verify --self-test, wheel smoke, dashboard build, release_export negative probe, a release-export dry-run with clean-boundary output scan, and the release_product_manifest leak-scan dry-run when the manifest is present."
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
    ( cd "$repo_root" && uv run python3 brick_protocol/support/checkers/check_profile.py --all )

    printf '%s\n' "3) CLI self-test: brick verify --self-test"
    ( cd "$repo_root" && uv run brick verify --self-test )

    tmp_parent="${TMPDIR:-/tmp}"
    wheel_dist="$(mktemp -d "$tmp_parent/brick-release-gate-wheel-dist.XXXXXX")"
    wheel_venv="$(mktemp -d "$tmp_parent/brick-release-gate-wheel-venv.XXXXXX")"
    cleanup() {
        rm -rf "$wheel_dist"
        rm -rf "$wheel_venv"
        rm -rf "$repo_root/build"
        rm -rf "${export_dir:-}"
        rm -rf "${negative_export_dir:-}"
        rm -rf "${manifest_negative_export_dir:-}"
        rm -rf "${manifest_probe_repo:-}"
        rm -f "${deny_probe_path:-}"
    }
    trap cleanup EXIT HUP INT TERM

    printf '%s\n' "4) wheel smoke: build wheel and verify installed brick console entry"
    # wheel hygiene (0706): this developer gate builds the wheel IN its own
    # working tree, so a stale setuptools build/ intermediate could seed the
    # wheel and mask a pyproject packages-list regression, and an in-tree build
    # would otherwise leave a build/ residue in the repo. Rationale for the
    # chosen technique (of the two allowed for a developer gate -- clear-own-tree
    # vs isolated-copy): as a developer gate (NOT the read-only checker) this
    # script may clear its OWN tree's build/, which is the simpler pollution-
    # proof option here -- it removes any stale build/ before the build so the
    # wheel reflects only the declared packages, and the trap removes the build/
    # residue on exit so the tree stays clean.
    printf '%s\n' "   wheel hygiene: cleared stale build/ before build; build/ residue removed on exit (developer-gate clear-own-tree technique)"
    rm -rf "$repo_root/build"
    ( cd "$repo_root" && PYTHONPATH= uv build --wheel --out-dir "$wheel_dist" )
    PYTHONPATH= python3 -m venv "$wheel_venv"
    # Contract pin literals: pip install --no-index --no-deps; brick --help.
    PYTHONPATH= "$wheel_venv/bin/pip" install --no-index --no-deps "$wheel_dist"/*.whl
    PYTHONPATH= "$wheel_venv/bin/brick" --help >/dev/null

    printf '%s\n' "5) dashboard build: brick_protocol/support/dashboard npm ci + build"
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

    export_dir="$(mktemp -d "$tmp_parent/brick-release-gate.XXXXXX")"
    negative_export_dir="$(mktemp -d "$tmp_parent/brick-release-gate-negative.XXXXXX")"
    deny_probe_path="$repo_root/.env.release-export-deny-probe"

    printf '%s\n' "6) release_export negative probe: deny forbidden local/provider path"
    printf '%s\n' "synthetic probe path: local release_export denylist input" > "$deny_probe_path"
    if (
        cd "$repo_root" &&
        sh brick_protocol/support/onboarding/release_export.sh --output "$negative_export_dir/export" --include-untracked --allow-dirty
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

    printf '%s\n' "7) release export dry-run + clean-boundary output scan"
    if ! (
        cd "$repo_root" &&
        sh brick_protocol/support/onboarding/release_export.sh --output "$export_dir/export"
    ) > "$export_dir/stdout.log" 2> "$export_dir/stderr.log"; then
        printf '%s\n' "release_gate: release_export dry-run failed" >&2
        cat "$export_dir/stdout.log" >&2
        cat "$export_dir/stderr.log" >&2
        return 1
    fi
    cat "$export_dir/stdout.log"
    if [ -s "$export_dir/stderr.log" ]; then
        cat "$export_dir/stderr.log" >&2
    fi
    if [ -e "$export_dir/export/project" ]; then
        printf '%s\n' "release_gate: release_export dry-run created forbidden project/ path" >&2
        return 1
    fi
    if [ ! -f "$export_dir/export/support/onboarding/release_product_manifest.json" ]; then
        printf '%s\n' "release_gate: release_export dry-run did not ship the product manifest" >&2
        return 1
    fi
    if ! grep -Fq "manifest violations: 0" "$export_dir/stdout.log"; then
        printf '%s\n' "release_gate: release_export dry-run did not report manifest violations: 0" >&2
        return 1
    fi
    if ! grep -Fq "git remote add origin git@github.com:{OWNER}/BRICK-dist.git" "$export_dir/stdout.log"; then
        printf '%s\n' "release_gate: release_export dry-run did not report the BRICK-dist follow-up target" >&2
        return 1
    fi
    if grep -Fq "git remote add origin git@github.com:{OWNER}/BRICK.git" "$export_dir/stdout.log"; then
        printf '%s\n' "release_gate: release_export dry-run reported the legacy BRICK follow-up target" >&2
        return 1
    fi

    manifest_path="$repo_root/support/onboarding/release_product_manifest.json"
    manifest_negative_export_dir="$(mktemp -d "$tmp_parent/brick-release-gate-manifest-negative.XXXXXX")"
    manifest_probe_repo="$(mktemp -d "$tmp_parent/brick-release-gate-manifest-probe-repo.XXXXXX")"

    # Clean-boundary manifest probing stays a local dry-run leak scan only; it
    # uses a disposable temp git repo rather than writing byproducts into the
    # live checkout root. It does not publish, tag, push, or mutate GitHub settings.
    printf '%s\n' "8) release_product_manifest negative probe: leak-scan dry-run only"
    if [ ! -f "$manifest_path" ]; then
        printf '%s\n' "release_product_manifest negative probe skipped: manifest not present"
    else
        mkdir -p "$manifest_probe_repo/support/onboarding"
        cp "$repo_root/support/onboarding/release_export.sh" "$manifest_probe_repo/support/onboarding/release_export.sh"
        cp "$manifest_path" "$manifest_probe_repo/support/onboarding/release_product_manifest.json"
        cp "$repo_root/README.md" "$manifest_probe_repo/README.md"
        (
            cd "$manifest_probe_repo" &&
            git init -q &&
            git checkout -q -B main &&
            git config user.name "Brick Protocol Release Gate Probe" &&
            git config user.email "release-gate-probe@example.invalid" &&
            git add README.md brick_protocol/support/onboarding/release_export.sh brick_protocol/support/onboarding/release_product_manifest.json &&
            git commit -q -m "manifest negative probe base"
        )
        printf '%s\n' "synthetic probe path: release_product_manifest non-whitelisted input" > "$manifest_probe_repo/internal-notes.release-manifest-probe.txt"
        if (
            cd "$manifest_probe_repo" &&
            sh brick_protocol/support/onboarding/release_export.sh --output "$manifest_negative_export_dir/export" --include-untracked --allow-dirty
        ) > "$manifest_negative_export_dir/stdout.log" 2> "$manifest_negative_export_dir/stderr.log"; then
            printf '%s\n' "release_gate: release_product_manifest negative probe unexpectedly passed" >&2
            cat "$manifest_negative_export_dir/stdout.log" >&2
            cat "$manifest_negative_export_dir/stderr.log" >&2
            return 1
        fi
        if ! grep -Fq "release product manifest violation: export input outside whitelist" "$manifest_negative_export_dir/stderr.log"; then
            printf '%s\n' "release_gate: release_product_manifest negative probe failed for the wrong reason" >&2
            cat "$manifest_negative_export_dir/stdout.log" >&2
            cat "$manifest_negative_export_dir/stderr.log" >&2
            return 1
        fi
        printf '%s\n' "release_product_manifest negative probe rejected non-whitelisted file as expected"
    fi

    printf '%s\n' \
        "release gate passed as support evidence only." \
        "proof limit: this does not prove source truth, success, quality, Movement authority, branch protection, or real publication."
}

main "$@"
