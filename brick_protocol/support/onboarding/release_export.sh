#!/usr/bin/env sh
# Build a clean public-release tree from this checkout.
#
# The exported tree intentionally omits project/ and brick_protocol.egg-info/.
# project/ is local vessel/status evidence; the first onboard run creates the
# release clone's vessel. The script creates a fresh git repository with one
# initial commit, then prints the remote/push/tag commands for the operator to
# run manually. It never pushes or tags by itself.

set -eu

usage() {
    printf '%s\n' \
        "Usage: sh brick_protocol/support/onboarding/release_export.sh --output /tmp/brick-release-v0.1.0 [--include-untracked] [--allow-dirty]" \
        "" \
        "Creates a clean export tree without project/ or brick_protocol.egg-info/." \
        "Default export input is tracked files only." \
        "--include-untracked explicitly adds untracked-unignored files." \
        "--allow-dirty records an explicit dirty-checkout override in the output report." \
        "The output directory must be absent or empty and must be outside this checkout."
}

output_dir=""
include_untracked=0
allow_dirty=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --output | -o)
            if [ "$#" -lt 2 ]; then
                printf '%s\n' "release_export: --output requires a path" >&2
                exit 2
            fi
            output_dir="$2"
            shift 2
            ;;
        --include-untracked)
            include_untracked=1
            shift
            ;;
        --allow-dirty)
            allow_dirty=1
            shift
            ;;
        --help | -h)
            usage
            exit 0
            ;;
        *)
            printf '%s\n' "release_export: unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [ -z "$output_dir" ]; then
    usage >&2
    exit 2
fi

source_root="$(git rev-parse --show-toplevel)"

python3 - "$source_root" "$output_dir" "$include_untracked" "$allow_dirty" <<'PY'
from __future__ import annotations

import fnmatch
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


EXCLUDE_PATHS = (
    "project",
    "brick_protocol.egg-info",
)

DENY_PATH_PATTERNS = (
    ".env",
    ".env.*",
    "credentials.env",
    "report.env",
    ".claude",
    ".claude/**",
    ".codex",
    ".codex/**",
    ".gemini",
    ".gemini/**",
    ".mcp.json",
    ".ssh",
    ".ssh/**",
    "secrets",
    "secrets/**",
    "tokens",
    "tokens/**",
    "sessions",
    "sessions/**",
)

MANIFEST_PATH = "brick_protocol/support/onboarding/release_product_manifest.json"
MANIFEST_SCHEMA = "release-product-manifest/v1"
MANIFEST_VIOLATION_LITERAL = "release product manifest violation: export input outside whitelist"

INITIAL_COMMIT_MESSAGE = "Initial clean Brick Protocol v0.1.0 export"


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def fail(message: str) -> None:
    print(f"release_export: {message}", file=sys.stderr)
    raise SystemExit(1)


def is_excluded(rel: str) -> bool:
    clean = rel.strip("/")
    return any(clean == root or clean.startswith(root + "/") for root in EXCLUDE_PATHS)


def denied_path_pattern(rel: str) -> str | None:
    clean = rel.strip("/")
    for pattern in DENY_PATH_PATTERNS:
        if fnmatch.fnmatchcase(clean, pattern):
            return pattern
    return None


def load_release_product_manifest(source: Path) -> dict[str, object]:
    manifest_file = source / MANIFEST_PATH
    try:
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"release product manifest missing: {MANIFEST_PATH}")
    except json.JSONDecodeError as exc:
        fail(f"release product manifest is not valid JSON: {exc}")
    if not isinstance(data, dict):
        fail("release product manifest root must be a JSON object")
    if data.get("schema") != MANIFEST_SCHEMA:
        fail(f"release product manifest schema must be {MANIFEST_SCHEMA!r}")
    for key in ("allowed_roots", "allowed_files", "allowed_globs"):
        value = data.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            fail(f"release product manifest {key} must be a list of strings")
    return data


def manifest_allowed_path(rel: str, manifest: dict[str, object]) -> bool:
    clean = rel.strip("/")
    allowed_roots = manifest["allowed_roots"]
    allowed_files = manifest["allowed_files"]
    allowed_globs = manifest["allowed_globs"]
    assert isinstance(allowed_roots, list)
    assert isinstance(allowed_files, list)
    assert isinstance(allowed_globs, list)
    for root in allowed_roots:
        assert isinstance(root, str)
        root = root.strip("/")
        if clean == root or clean.startswith(root + '/'):
            return True
    for filename in allowed_files:
        assert isinstance(filename, str)
        if clean == filename.strip("/"):
            return True
    for pattern in allowed_globs:
        assert isinstance(pattern, str)
        if fnmatch.fnmatchcase(clean, pattern):
            return True
    return False


def safe_rel_path(raw: str) -> Path:
    rel = Path(raw)
    if rel.is_absolute() or ".." in rel.parts:
        fail(f"refusing unsafe git path: {raw!r}")
    return rel


source = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).expanduser().resolve()
include_untracked = sys.argv[3] == "1"
allow_dirty = sys.argv[4] == "1"

if output == source or source in output.parents:
    fail("output directory must be outside the source checkout")

try:
    inside = run(["git", "-C", str(source), "rev-parse", "--is-inside-work-tree"]).stdout.strip()
except subprocess.CalledProcessError as exc:
    fail(f"source is not a git worktree: {exc.stderr.strip()}")
if inside != "true":
    fail(f"source is not a git worktree: {source}")

dirty_status = run(
    ["git", "-C", str(source), "status", "--porcelain", "--untracked-files=all"]
).stdout
dirty_entries = [line for line in dirty_status.splitlines() if line.strip()]
if dirty_entries and not allow_dirty:
    fail(
        "source checkout is dirty; commit/stash changes or rerun with --allow-dirty "
        "to record the override"
    )

if output.exists() and any(output.iterdir()):
    fail(f"output directory is not empty: {output}")
output.mkdir(parents=True, exist_ok=True)

ls_files_cmd = ["git", "-C", str(source), "ls-files", "-z", "--cached"]
if include_untracked:
    ls_files_cmd.extend(["--others", "--exclude-standard"])
raw_files = run(ls_files_cmd).stdout
rel_files = [item for item in raw_files.split("\0") if item]
if MANIFEST_PATH not in rel_files and (source / MANIFEST_PATH).is_file():
    # The manifest is the release boundary contract itself. In normal clean
    # release commits it is tracked and already present in git ls-files; the
    # fallback keeps dirty support-evidence dry-runs from exporting a tree that
    # cannot re-run its own manifest-governed release verb.
    rel_files.append(MANIFEST_PATH)
if not rel_files:
    fail("git reported no files to export")

manifest = load_release_product_manifest(source)
export_rel_files: list[str] = []
excluded = 0
denied: list[str] = []
manifest_violations: list[str] = []
for raw_rel in rel_files:
    if is_excluded(raw_rel):
        excluded += 1
        continue
    deny_pattern = denied_path_pattern(raw_rel)
    if deny_pattern is not None:
        denied.append(f"{raw_rel} (matched {deny_pattern})")
        continue
    if not manifest_allowed_path(raw_rel, manifest):
        manifest_violations.append(raw_rel)
        continue
    export_rel_files.append(raw_rel)

if denied:
    fail(
        "secret/local/provider/session path denylist matched export input:\n"
        + "\n".join(f"- {item}" for item in denied)
    )

if manifest_violations:
    fail(
        MANIFEST_VIOLATION_LITERAL
        + ":\n"
        + "\n".join(f"- {item}" for item in manifest_violations)
    )

copied = 0
skipped_missing = 0
for raw_rel in export_rel_files:
    rel = safe_rel_path(raw_rel)
    src = source / rel
    dst = output / rel
    if not src.exists() and not src.is_symlink():
        skipped_missing += 1
        continue
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_symlink():
        target = (src.parent / os.readlink(src)).resolve()
        try:
            target.relative_to(source)
        except ValueError:
            fail(f"refusing symlink with target outside checkout: {raw_rel}")
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        os.symlink(os.readlink(src), dst)
    elif src.is_file():
        shutil.copy2(src, dst)
    copied += 1

for forbidden in EXCLUDE_PATHS:
    if (output / forbidden).exists():
        fail(f"forbidden export path was created: {forbidden}/")

run(["git", "init", "-q"], cwd=output)
run(["git", "checkout", "-q", "-B", "main"], cwd=output)
run(["git", "config", "user.name", "Brick Protocol Release Export"], cwd=output)
run(["git", "config", "user.email", "release-export@example.invalid"], cwd=output)
run(["git", "add", "-A"], cwd=output)
run(["git", "commit", "-q", "-m", INITIAL_COMMIT_MESSAGE], cwd=output)

head = run(["git", "rev-parse", "--short", "HEAD"], cwd=output).stdout.strip()

print(f"release export ready: {output}")
print("input mode: tracked files only" + (" + explicit untracked opt-in" if include_untracked else ""))
print(
    "dirty checkout override: "
    + ("allowed and recorded" if allow_dirty and dirty_entries else "not used")
)
print(f"dirty entries observed: {len(dirty_entries)}")
print(f"copied files: {copied}")
print(f"excluded paths matched: {excluded}")
print("excluded roots: " + ", ".join(root + "/" for root in EXCLUDE_PATHS))
print("denylist roots/patterns: " + ", ".join(DENY_PATH_PATTERNS))
print("denylist matches: 0")
print("manifest: brick_protocol/support/onboarding/release_product_manifest.json")
print("manifest violations: 0")
print(f"skipped missing inputs: {skipped_missing}")
print(f"initial commit: {head}")
print("project scaffold: omitted; first onboard run creates project/")
print("")
print("Follow-up commands for the operator, after creating the new public repo:")
print(f"  cd {output}")
print("  git remote add origin git@github.com:{OWNER}/BRICK-dist.git")
print("  git tag v0.1.0")
print("  git push -u origin main")
print("  git push origin v0.1.0")
PY
