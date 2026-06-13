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
        "Usage: sh support/onboarding/release_export.sh --output /tmp/brick-release-v0.1.0" \
        "" \
        "Creates a clean export tree without project/ or brick_protocol.egg-info/." \
        "The output directory must be absent or empty and must be outside this checkout."
}

output_dir=""

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

python3 - "$source_root" "$output_dir" <<'PY'
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


EXCLUDE_PATHS = (
    "project",
    "brick_protocol.egg-info",
)

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


def safe_rel_path(raw: str) -> Path:
    rel = Path(raw)
    if rel.is_absolute() or ".." in rel.parts:
        fail(f"refusing unsafe git path: {raw!r}")
    return rel


source = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).expanduser().resolve()

if output == source or source in output.parents:
    fail("output directory must be outside the source checkout")

if output.exists() and any(output.iterdir()):
    fail(f"output directory is not empty: {output}")
output.mkdir(parents=True, exist_ok=True)

try:
    inside = run(["git", "-C", str(source), "rev-parse", "--is-inside-work-tree"]).stdout.strip()
except subprocess.CalledProcessError as exc:
    fail(f"source is not a git worktree: {exc.stderr.strip()}")
if inside != "true":
    fail(f"source is not a git worktree: {source}")

raw_files = run(
    [
        "git",
        "-C",
        str(source),
        "ls-files",
        "-z",
        "--cached",
        "--others",
        "--exclude-standard",
    ]
).stdout
rel_files = [item for item in raw_files.split("\0") if item]
if not rel_files:
    fail("git reported no tracked or unignored files to export")

copied = 0
excluded = 0
for raw_rel in rel_files:
    if is_excluded(raw_rel):
        excluded += 1
        continue
    rel = safe_rel_path(raw_rel)
    src = source / rel
    dst = output / rel
    if not src.exists() and not src.is_symlink():
        continue
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_symlink():
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
print(f"copied files: {copied}")
print(f"excluded paths matched: {excluded}")
print("excluded roots: " + ", ".join(root + "/" for root in EXCLUDE_PATHS))
print(f"initial commit: {head}")
print("project scaffold: omitted; first onboard run creates project/")
print("")
print("Follow-up commands for the operator, after creating the new public repo:")
print(f"  cd {output}")
print("  git remote add origin git@github.com:{OWNER}/BRICK.git")
print("  git tag v0.1.0")
print("  git push -u origin main")
print("  git push origin v0.1.0")
PY
