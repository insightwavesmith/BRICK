"""Onboarding install-script + release-gate/export structural/safety lints.

FINAL architecture leaf (0630): the install_script_lint + release_export_exclusion
cluster moved VERBATIM out of kernel_checks.py into this flat checker-lib sibling
(conservation ledger
customer-ready-final-architecture-install-release-export-lint-ledger-0630.md).
Support checker mechanics only: it reads onboarding shell verbs and asserts their
STRUCTURE/SAFETY shape; it authors no axis crossing and decides nothing. The
bodies below are byte-identical to the pre-move kernel_checks.py spans; only this
module header and the imports differ.
"""

from __future__ import annotations

import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from brick_protocol.support.checkers.lib.yaml_subset import (
    KernelResult,
    ProfileError,
)


_INSTALL_SCRIPT_REL = "brick_protocol/support/onboarding/install.sh"
_RELEASE_EXPORT_REL = "brick_protocol/support/onboarding/release_export.sh"
_RELEASE_GATE_REL = "brick_protocol/support/onboarding/release_gate.sh"
_RELEASE_PRODUCT_MANIFEST_REL = "brick_protocol/support/onboarding/release_product_manifest.json"
_RELEASE_PRODUCT_MANIFEST_SCHEMA = "release-product-manifest/v1"
_RELEASE_PRODUCT_MANIFEST_VIOLATION_LITERAL = (
    "release product manifest violation: export input outside whitelist"
)
_RELEASE_PRODUCT_MANIFEST_REPORT_LINES = (
    f"manifest: {_RELEASE_PRODUCT_MANIFEST_REL}",
    "manifest violations: 0",
)
_RELEASE_PRODUCT_MANIFEST_REQUIRED_ROOTS = (
    ".github",
    "agent",
    "brick",
    "link",
    "support",
)
_RELEASE_PRODUCT_MANIFEST_REQUIRED_FILES = (
    ".gitignore",
    "AGENTS.md",
    "BRICK-CONSTITUTION.md",
    "README.md",
    "pyproject.toml",
    "uv.lock",
)
_WHEEL_SMOKE_REQUIRED_PACKAGE_PATHS = {
    "operator": "brick_protocol/support/operator/",
    "checkers": "brick_protocol/support/checkers/",
    "connection": "brick_protocol/support/connection/",
}
_RELEASE_EXPORT_REQUIRED_EXCLUSIONS = (
    "project",
    "brick_protocol.egg-info",
)
_RELEASE_EXPORT_REQUIRED_DENY_PATTERNS = (
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

# Secret-shaped patterns the one-line installer must NEVER carry inline. The
# script relies on the teammate's OWN gh/git login as the access grant; nothing
# here may embed a literal credential. These are substring/structure probes, not
# a cryptographic secret scanner.
_INSTALL_SCRIPT_SECRET_PATTERNS = (
    "ghp_",
    "github_pat_",
    "gho_",
    "token=",
    "Bearer ",
    "BRICK_TOKEN=",
    "AWS_SECRET",
    "PRIVATE KEY",
)


def run_install_script_lint(repo: Path) -> KernelResult:
    """ONBOARDING-INSTALL-SCRIPT-0 structural / safety lint.

    Reads ``brick_protocol/support/onboarding/install.sh`` (the one-line installer) and asserts
    its STRUCTURE and SAFETY shape:
      (a) the file exists and is non-empty;
      (b) it sets ``set -eu`` (fail-fast, fail-on-unset);
      (c) ALL logic is wrapped in a ``main()`` function AND ``main`` is invoked
          as the LAST non-empty line (anti-truncation: a cut-off download leaves
          main undefined / never called, so a partial file cannot run a
          half-baked install);
      (d) it contains NO ``http://`` (HTTPS only);
      (e) it contains NO ``/Users/`` literal (no hardcoded user-home path);
      (f) it contains NO obvious inline secret pattern (the script relies on the
          teammate's own gh/git login, never an embedded token);
      (g) it references the onboard wizard entry as the next step;
      (h) it checks for ``pipx`` before Python, clone, or dependency-install
          work, so a missing entrypoint installer fails upfront.

    LIMIT (stated in the output and honestly here): this is a STRUCTURE/SAFETY
    lint. It does NOT prove the script actually installs on a real fresh machine
    (network clone, uv sync, provider auth, etc.) -- that proof is manual /
    Phase-4 infra, not gated here. A violation makes main() return non-zero and
    raises ProfileError, so --all EXITs non-zero.
    """

    script_path = repo / _INSTALL_SCRIPT_REL
    if not script_path.is_file():
        raise ProfileError(
            f"install_script_lint: installer missing: {_INSTALL_SCRIPT_REL}"
        )

    text = script_path.read_text(encoding="utf-8")
    if not text.strip():
        raise ProfileError(
            f"install_script_lint: {_INSTALL_SCRIPT_REL} is empty"
        )

    violations: list[str] = []

    # (b) fail-fast options.
    if "set -eu" not in text:
        violations.append("missing 'set -eu' (fail-fast / fail-on-unset)")

    # (c) main() defined AND invoked as the LAST non-empty line.
    if "main(" not in text:
        violations.append("no main( function defined")
    non_empty_lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    last_line = non_empty_lines[-1] if non_empty_lines else ""
    if last_line.strip() != 'main "$@"':
        violations.append(
            "last non-empty line must be exactly 'main \"$@\"' (anti-truncation), "
            f"got: {last_line.strip()!r}"
        )

    # (d) HTTPS only -- no plaintext http:// scheme anywhere.
    if "http://" in text:
        violations.append("contains 'http://' (HTTPS only)")

    # (e) no hardcoded user-home literal.
    if "/Users/" in text:
        violations.append("contains a hardcoded '/Users/' path (no user-home literal)")

    # (f) no inline secret patterns.
    for pattern in _INSTALL_SCRIPT_SECRET_PATTERNS:
        if pattern in text:
            violations.append(f"contains a secret-shaped pattern: {pattern!r}")

    # (g) references the onboard wizard entry (the next-step pointer).
    if "brick_protocol.support.operator.onboard" not in text:
        violations.append(
            "does not reference the onboard wizard entry "
            "(brick_protocol.support.operator.onboard)"
        )

    pipx_check_index = text.find("command -v pipx")
    if pipx_check_index == -1:
        violations.append("missing upfront pipx presence check")
    else:
        ordering_needles = {
            "python3 presence check": "command -v python3",
            "repository clone": '\n        gh repo clone "$REPO_SLUG" "$target"',
            "dependency install": '\n    ( cd "$target" && uv sync )',
            "pipx install action": '\n    pipx install --force --editable "$target"',
        }
        for label, needle in ordering_needles.items():
            needle_index = text.find(needle)
            if needle_index != -1 and pipx_check_index > needle_index:
                violations.append(
                    f"pipx presence check must run before {label} ({needle!r})"
                )

    if violations:
        raise ProfileError(
            "install_script_lint: "
            f"{_INSTALL_SCRIPT_REL} failed structural/safety lint: "
            + "; ".join(violations)
        )

    return KernelResult(
        check_id="install_script_lint",
        inspected=1,
        output=(
            "install script lint passed: "
            f"{_INSTALL_SCRIPT_REL} sets 'set -eu', wraps all logic in main() "
            "invoked as 'main \"$@\"' on the last non-empty line (anti-truncation), "
            "carries no http:// (HTTPS only), no /Users/ literal, no inline "
            "secret pattern, references the onboard wizard entry, and checks pipx "
            "upfront before Python/clone/dependency work. "
            "PROOF LIMIT: this is a STRUCTURE/SAFETY lint only -- it does NOT "
            "prove the script actually installs on a real fresh machine (network "
            "clone, uv sync, provider auth); that is manual / Phase-4 infra, not "
            "gated here."
        ),
    )


def _release_export_exclusions(text: str) -> set[str]:
    match = re.search(r"EXCLUDE_PATHS\s*=\s*\((?P<body>.*?)\)", text, re.DOTALL)
    if not match:
        return set()
    return set(re.findall(r"""["']([^"']+)["']""", match.group("body")))


def _release_export_deny_patterns(text: str) -> set[str]:
    match = re.search(r"DENY_PATH_PATTERNS\s*=\s*\((?P<body>.*?)\)", text, re.DOTALL)
    if not match:
        return set()
    return set(re.findall(r"""["']([^"']+)["']""", match.group("body")))


def _release_product_manifest_data_violations(manifest_text: str) -> list[str]:
    violations: list[str] = []
    try:
        data = json.loads(manifest_text)
    except json.JSONDecodeError as exc:
        return [f"release product manifest is not parseable JSON: {exc}"]

    if not isinstance(data, dict):
        return ["release product manifest root must be a JSON object"]

    if data.get("schema") != _RELEASE_PRODUCT_MANIFEST_SCHEMA:
        violations.append(
            "release product manifest schema must be "
            f"{_RELEASE_PRODUCT_MANIFEST_SCHEMA!r}"
        )

    for key in ("allowed_roots", "allowed_files", "allowed_globs"):
        value = data.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            violations.append(f"release product manifest {key} must be a list of strings")

    allowed_roots = set(data.get("allowed_roots", []))
    for required in _RELEASE_PRODUCT_MANIFEST_REQUIRED_ROOTS:
        if required not in allowed_roots:
            violations.append(
                f"release product manifest missing allowed root: {required}"
            )

    allowed_files = set(data.get("allowed_files", []))
    for required in _RELEASE_PRODUCT_MANIFEST_REQUIRED_FILES:
        if required not in allowed_files:
            violations.append(
                f"release product manifest missing allowed file: {required}"
            )

    return violations


def _release_export_exclusion_violations(text: str) -> list[str]:
    exclusions = _release_export_exclusions(text)
    deny_patterns = _release_export_deny_patterns(text)
    violations: list[str] = []
    if not exclusions:
        violations.append("missing literal EXCLUDE_PATHS tuple")
    for required in _RELEASE_EXPORT_REQUIRED_EXCLUSIONS:
        if required not in exclusions:
            violations.append(f"missing required exclusion: {required}/")
    if not deny_patterns:
        violations.append("missing literal DENY_PATH_PATTERNS tuple")
    for required in _RELEASE_EXPORT_REQUIRED_DENY_PATTERNS:
        if required not in deny_patterns:
            violations.append(f"missing required deny path pattern: {required}")
    if "--include-untracked" not in text:
        violations.append("missing explicit --include-untracked opt-in flag")
    if "--allow-dirty" not in text:
        violations.append("missing explicit --allow-dirty override flag")
    if '"ls-files", "-z", "--cached"' not in text:
        violations.append("release input must default to tracked files via git ls-files --cached")
    if 'ls_files_cmd.extend(["--others", "--exclude-standard"])' not in text:
        violations.append("untracked files must only be added behind include_untracked")
    if "if MANIFEST_PATH not in rel_files and (source / MANIFEST_PATH).is_file():" not in text:
        violations.append("required product manifest must be added to export input when present")
    if '"status", "--porcelain", "--untracked-files=all"' not in text:
        violations.append("missing dirty-checkout status probe")
    if "if dirty_entries and not allow_dirty:" not in text:
        violations.append("dirty checkout must fail closed unless --allow-dirty is set")
    if f'MANIFEST_PATH = "{_RELEASE_PRODUCT_MANIFEST_REL}"' not in text:
        violations.append("missing release product manifest path literal")
    if "load_release_product_manifest(source)" not in text:
        violations.append("release export must load the product manifest")
    if "manifest_allowed_path(raw_rel, manifest)" not in text:
        violations.append("export inputs must pass the product manifest before copy")
    if _RELEASE_PRODUCT_MANIFEST_VIOLATION_LITERAL not in text:
        violations.append("missing product manifest whitelist violation literal")
    for report_line in _RELEASE_PRODUCT_MANIFEST_REPORT_LINES:
        if report_line not in text:
            violations.append(f"missing product manifest report line: {report_line}")
    if "clean == root or clean.startswith(root + '/')" not in text:
        violations.append("manifest root matching must use explicit dir-prefix semantics")
    if "fnmatch.fnmatchcase(clean, pattern)" not in text:
        violations.append("manifest globs must use fnmatchcase")
    if "denied_path_pattern(raw_rel)" not in text:
        violations.append("export inputs must pass the denylist before copy")
    if "secret/local/provider/session path denylist matched export input" not in text:
        violations.append("denylist failure must name secret/local/provider/session path class")
    if "target.relative_to(source)" not in text:
        violations.append("symlink target must be resolved and contained inside checkout")
    if "refusing symlink with target outside checkout" not in text:
        violations.append("symlink escape refusal must be explicit")
    for report_line in (
        "input mode:",
        "dirty checkout override:",
        "dirty entries observed:",
        "excluded paths matched:",
        "denylist roots/patterns:",
        "denylist matches: 0",
        "skipped missing inputs:",
    ):
        if report_line not in text:
            violations.append(f"missing exclusion/export report line: {report_line}")
    if "git remote add origin git@github.com:{OWNER}/BRICK-dist.git" not in text:
        violations.append("missing placeholder remote follow-up command")
    if "git tag v0.1.0" not in text:
        violations.append("missing v0.1.0 tag follow-up command")
    if "git push -u origin main" not in text or "git push origin v0.1.0" not in text:
        violations.append("missing manual push follow-up commands")
    return violations


def _release_export_exclusion_fire_probe(text: str) -> int:
    fired = 0

    without_project = text.replace('    "project",\n', "", 1)
    violations = _release_export_exclusion_violations(without_project)
    if not any("missing required exclusion: project/" in violation for violation in violations):
        raise ProfileError(
            "release_export_exclusion FIRE probe did NOT fire when project/ "
            "was removed from the export exclusion list"
        )
    fired += 1

    without_dirty_guard = text.replace("if dirty_entries and not allow_dirty:", "if False:", 1)
    violations = _release_export_exclusion_violations(without_dirty_guard)
    if not any("dirty checkout must fail closed" in violation for violation in violations):
        raise ProfileError(
            "release_export_exclusion FIRE probe did NOT fire when the dirty "
            "checkout fail-closed guard was removed"
        )
    fired += 1

    without_secret_path = text.replace('    ".env",\n', "", 1)
    violations = _release_export_exclusion_violations(without_secret_path)
    if not any("missing required deny path pattern: .env" in violation for violation in violations):
        raise ProfileError(
            "release_export_exclusion FIRE probe did NOT fire when the .env "
            "secret-path deny pattern was removed"
        )
    fired += 1

    without_deny_call = text.replace("denied_path_pattern(raw_rel)", "None", 1)
    violations = _release_export_exclusion_violations(without_deny_call)
    if not any("export inputs must pass the denylist" in violation for violation in violations):
        raise ProfileError(
            "release_export_exclusion FIRE probe did NOT fire when the denylist "
            "copy-time check was removed"
        )
    fired += 1

    without_symlink_target_check = text.replace("target.relative_to(source)", "target", 1)
    violations = _release_export_exclusion_violations(without_symlink_target_check)
    if not any("symlink target must be resolved" in violation for violation in violations):
        raise ProfileError(
            "release_export_exclusion FIRE probe did NOT fire when the symlink "
            "target containment check was removed"
        )
    fired += 1

    without_manifest_call = text.replace(
        "manifest_allowed_path(raw_rel, manifest)", "True", 1
    )
    violations = _release_export_exclusion_violations(without_manifest_call)
    if not any("product manifest" in violation for violation in violations):
        raise ProfileError(
            "release_export_exclusion FIRE probe did NOT fire when the product "
            "manifest copy-time check was removed"
        )
    fired += 1

    without_manifest_input_fallback = text.replace(
        "if MANIFEST_PATH not in rel_files and (source / MANIFEST_PATH).is_file():",
        "if False:",
        1,
    )
    violations = _release_export_exclusion_violations(without_manifest_input_fallback)
    if not any("required product manifest" in violation for violation in violations):
        raise ProfileError(
            "release_export_exclusion FIRE probe did NOT fire when the product "
            "manifest export-input fallback was removed"
        )
    fired += 1

    without_manifest_violation_literal = text.replace(
        _RELEASE_PRODUCT_MANIFEST_VIOLATION_LITERAL,
        "release product manifest drifted message",
        1,
    )
    violations = _release_export_exclusion_violations(without_manifest_violation_literal)
    if not any("whitelist violation literal" in violation for violation in violations):
        raise ProfileError(
            "release_export_exclusion FIRE probe did NOT fire when the product "
            "manifest violation literal was changed"
        )
    fired += 1

    return fired


def run_release_export_exclusion(repo: Path) -> KernelResult:
    """Pin the clean-repo export verb's local-evidence exclusion list.

    The release export is allowed to prepare a public tree, but it must not ship
    the local project evidence vessel or Python build metadata. This check only
    inspects the support verb's literal exclusion contract and publication
    follow-up shape. It does not push, tag, run the export, judge release
    quality, or prove future operator behavior.
    """

    script_path = repo / _RELEASE_EXPORT_REL
    if not script_path.is_file():
        raise ProfileError(
            f"release_export_exclusion: export verb missing: {_RELEASE_EXPORT_REL}"
        )
    manifest_path = repo / _RELEASE_PRODUCT_MANIFEST_REL
    if not manifest_path.is_file():
        raise ProfileError(
            "release_export_exclusion: product manifest missing: "
            f"{_RELEASE_PRODUCT_MANIFEST_REL}"
        )
    text = script_path.read_text(encoding="utf-8")
    violations = _release_export_exclusion_violations(text)
    violations.extend(
        _release_product_manifest_data_violations(
            manifest_path.read_text(encoding="utf-8")
        )
    )
    if violations:
        raise ProfileError(
            "release_export_exclusion rejected export verb:\n"
            + "\n".join(f"- {violation}" for violation in violations)
        )
    inspected = 1 + _release_export_exclusion_fire_probe(text)
    return KernelResult(
        check_id="release_export_exclusion",
        inspected=inspected,
        output=(
            "release export exclusion pin passed: brick_protocol/support/onboarding/release_export.sh "
            "carries literal exclusions for project/ and brick_protocol.egg-info/, "
            "defaults to tracked-only input with explicit --include-untracked, "
            "fails closed on dirty checkout unless --allow-dirty is recorded, "
            "carries a secret/local/provider/session path denylist, resolves "
            "symlink targets inside the checkout, loads the product manifest "
            f"{_RELEASE_PRODUCT_MANIFEST_REL} as a default-deny whitelist after "
            "exclusion/denylist filters, prints manifest/exclusion/export report "
            "lines plus manual remote/tag/push follow-up commands with {OWNER}, "
            "and FIRE probes for exclusion, dirty guard, denylist, symlink "
            "containment, and manifest governance fired RED. PROOF LIMIT: this is "
            "support evidence only; it does not run publication, choose Movement, "
            "or judge release quality."
        ),
    )


def _command_output(completed: subprocess.CompletedProcess[str]) -> str:
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    return output.strip()


def _without_repo_pythonpath() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    return env


def _is_environment_build_constraint(output: str) -> bool:
    env_fragments = (
        "Cannot import 'setuptools.build_meta'",
        "BackendUnavailable",
        "No module named 'setuptools'",
        "No module named setuptools",
        "No solution found",
        "failed to resolve",
        "network",
        "offline",
        "Temporary failure in name resolution",
    )
    return any(fragment in output for fragment in env_fragments)


def _environment_report(reason: str) -> KernelResult:
    return KernelResult(
        check_id="wheel_smoke",
        inspected=1,
        output=(
            "wheel smoke environment report: "
            f"{reason}. The checker did not mark this environment RED before a "
            "wheel artifact existed; a complete build-capable environment still "
            "runs the wheel content and console-entry smoke. PROOF LIMIT: support "
            "evidence only; this does not prove source truth, success, quality, "
            "Movement authority, or real publication."
        ),
    )


def _wheel_path_counts(wheel_path: Path) -> dict[str, int]:
    with zipfile.ZipFile(wheel_path) as archive:
        names = archive.namelist()
    return {
        label: sum(required_path in name for name in names)
        for label, required_path in _WHEEL_SMOKE_REQUIRED_PACKAGE_PATHS.items()
    }


# Directory / file names the wheel build must never seed from or write into.
# The smoke builds from an ISOLATED copy of the source tree (not the repo
# working tree itself) for two reasons:
#   (1) a stale in-tree setuptools ``build/`` intermediate (or ``*.egg-info``)
#       left by a previous build would otherwise be reused and leak files into
#       the wheel, MASKING a pyproject packages-list regression (0706: removing
#       "brick_protocol.support.operator" from packages still shipped 68
#       operator files while a stale build/lib was present);
#   (2) building in-tree writes a ``build/`` residue into the repo, and this
#       checker must stay read-only over the repo working tree.
# The skipped names are VCS / build / cache / env artifacts plus ``project``
# (the local evidence vessel already excluded from release_export); none is a
# declared wheel package source, so excluding them cannot change the declared
# wheel contents -- it only removes stale/irrelevant trees before the build.
_WHEEL_SMOKE_COPY_IGNORE_NAMES = frozenset(
    {
        ".git",
        "build",
        "dist",
        "__pycache__",
        ".venv",
        "node_modules",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "project",
        ".DS_Store",
    }
)


def _wheel_smoke_copy_ignore(_directory: str, names: list[str]) -> list[str]:
    return [
        name
        for name in names
        if name in _WHEEL_SMOKE_COPY_IGNORE_NAMES
        or name.endswith(".egg-info")
        or name.endswith(".pyc")
    ]


def run_wheel_smoke(repo: Path) -> KernelResult:
    """Build a wheel and smoke the shipped console entry from an isolated venv.

    The wheel is built from an ISOLATED copy of the source tree (see
    ``_WHEEL_SMOKE_COPY_IGNORE_NAMES``): the copy omits any stale in-tree
    ``build/`` intermediate, so a leftover setuptools build cannot seed the
    wheel and mask a pyproject packages-list regression, and the build writes no
    ``build/`` residue into the repo working tree. The smoke then installs the
    built local wheel into a temp venv with ``--no-index --no-deps`` so it
    observes the release artifact's own package contents without reaching a
    remote index for declared runtime dependencies. Missing build backend /
    offline build setup is reported as an environment observation before a wheel
    exists; malformed wheel contents or console import failure after a wheel
    exists are RED.
    """

    with tempfile.TemporaryDirectory(prefix="bp-wheel-smoke-src-") as src_raw, \
            tempfile.TemporaryDirectory(prefix="bp-wheel-smoke-dist-") as dist_raw, \
            tempfile.TemporaryDirectory(prefix="bp-wheel-smoke-venv-") as venv_raw:
        build_root = Path(src_raw) / "tree"
        shutil.copytree(
            repo,
            build_root,
            ignore=_wheel_smoke_copy_ignore,
            symlinks=False,
            ignore_dangling_symlinks=True,
        )
        dist_dir = Path(dist_raw)
        venv_dir = Path(venv_raw)
        build = subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(dist_dir)],
            cwd=build_root,
            env=_without_repo_pythonpath(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
            check=False,
        )
        if build.returncode != 0:
            output = _command_output(build)
            if _is_environment_build_constraint(output):
                return _environment_report(
                    "uv build --wheel could not create an artifact in this "
                    "environment"
                )
            raise ProfileError(
                "wheel_smoke: uv build --wheel failed:\n" + output
            )

        wheels = sorted(dist_dir.glob("*.whl"))
        if len(wheels) != 1:
            raise ProfileError(
                "wheel_smoke: expected exactly one wheel in temp dist, "
                f"observed {len(wheels)}"
            )
        wheel_path = wheels[0]
        counts = _wheel_path_counts(wheel_path)
        missing = {label: count for label, count in counts.items() if count <= 0}
        if missing:
            raise ProfileError(
                "wheel_smoke: wheel missing required support package contents: "
                + ", ".join(f"{label}={count}" for label, count in missing.items())
            )

        venv = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            cwd=repo,
            env=_without_repo_pythonpath(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )
        if venv.returncode != 0:
            return _environment_report("python venv creation failed in this environment")

        python_bin = venv_dir / (
            "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
        )
        brick_bin = venv_dir / (
            "Scripts/brick.exe" if sys.platform == "win32" else "bin/brick"
        )
        install = subprocess.run(
            [
                str(python_bin),
                "-m",
                "pip",
                "install",
                "--no-index",
                "--no-deps",
                str(wheel_path),
            ],
            cwd=repo,
            env=_without_repo_pythonpath(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
            check=False,
        )
        if install.returncode != 0:
            raise ProfileError(
                "wheel_smoke: no-index wheel install failed after wheel build:\n"
                + _command_output(install)
            )

        help_run = subprocess.run(
            [str(brick_bin), "--help"],
            cwd=repo,
            env=_without_repo_pythonpath(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            check=False,
        )
        if help_run.returncode != 0:
            raise ProfileError(
                "wheel_smoke: installed brick --help failed after wheel install:\n"
                + _command_output(help_run)
            )

        return KernelResult(
            check_id="wheel_smoke",
            inspected=4,
            output=(
                "wheel smoke passed: uv build --wheel built from an isolated "
                "source copy (no stale in-tree build/ seed, no repo build/ "
                "residue) and wrote one temp wheel, "
                f"wheel contents included operator={counts['operator']}, "
                f"checkers={counts['checkers']}, connection={counts['connection']}, "
                "a temp venv installed the local wheel with --no-index --no-deps, "
                "and the installed brick --help entrypoint exited 0. PROOF LIMIT: "
                "support evidence only; this does not prove source truth, success, "
                "quality, Movement authority, dependency-index availability, or "
                "real publication."
            ),
        )


def run_release_gate_contract(repo: Path) -> KernelResult:
    """Pin the local release gate's support-only command contract.

    The gate may sequence already-admitted support checks and a release-export
    dry-run. It must not publish, tag, push, mutate GitHub settings, choose
    Movement, or judge quality/success.
    """

    script_path = repo / _RELEASE_GATE_REL
    workflow_path = repo / ".github/workflows/release-gate.yaml"
    if not script_path.is_file():
        raise ProfileError(
            f"release_gate_contract: release gate missing: {_RELEASE_GATE_REL}"
        )
    if not workflow_path.is_file():
        raise ProfileError(
            "release_gate_contract: workflow missing: "
            ".github/workflows/release-gate.yaml"
        )

    text = script_path.read_text(encoding="utf-8")
    workflow = workflow_path.read_text(encoding="utf-8")
    violations: list[str] = []

    required_script_texts = (
        "set -eu",
        "uv run python3 -m compileall -q brick agent link support",
        "uv run python3 brick_protocol/support/checkers/check_profile.py --all",
        "uv run brick verify --self-test",
        "printf '%s\\n' \"4) wheel smoke: build wheel and verify installed brick console entry\"",
        "rm -rf \"$repo_root/build\"",
        "( cd \"$repo_root\" && PYTHONPATH= uv build --wheel --out-dir \"$wheel_dist\" )",
        "PYTHONPATH= python3 -m venv \"$wheel_venv\"",
        "PYTHONPATH= \"$wheel_venv/bin/pip\" install --no-index --no-deps \"$wheel_dist\"/*.whl",
        "PYTHONPATH= \"$wheel_venv/bin/brick\" --help >/dev/null",
        "command -v node",
        "command -v npm",
        "( cd \"$repo_root/support/dashboard\" && npm ci )",
        "( cd \"$repo_root/support/dashboard\" && npm run build )",
        "sh brick_protocol/support/onboarding/release_export.sh --output",
        "release_export negative probe",
        ".env.release-export-deny-probe",
        "--include-untracked --allow-dirty",
        "secret/local/provider/session path denylist matched export input",
        "release export dry-run + clean-boundary output scan",
        "release_export dry-run did not ship the product manifest",
        "manifest violations: 0",
        "git remote add origin git@github.com:{OWNER}/BRICK-dist.git",
        "release_product_manifest negative probe: leak-scan dry-run only",
        "brick-release-gate-manifest-probe-repo",
        "release_product_manifest non-whitelisted input",
        "git commit -q -m \"manifest negative probe base\"",
        "release product manifest violation: export input outside whitelist",
        "uses a disposable temp git repo rather than writing byproducts into the",
        "does not publish, tag, push, or mutate GitHub settings",
        "mktemp -d",
        "trap cleanup EXIT HUP INT TERM",
        "does not prove source truth, success, quality, Movement authority, "
        "branch protection, or real publication",
    )
    for required in required_script_texts:
        if required not in text:
            violations.append(f"release gate missing required text: {required!r}")

    forbidden_script_texts = (
        "git push",
        "git tag",
        "gh api",
        "gh repo edit",
        "branch protection",
        "success judgment",
        "quality judgment",
    )
    for forbidden in forbidden_script_texts:
        if forbidden in text and forbidden not in (
            "branch protection",
            "success judgment",
            "quality judgment",
        ):
            violations.append(
                "release gate contains forbidden publish/settings verb: "
                f"{forbidden!r}"
            )
    if 'manifest_probe_path="$repo_root/' in text:
        violations.append(
            "release gate manifest negative probe must not write byproducts into "
            "the live checkout root"
        )

    required_workflow_texts = (
        "actions/setup-node@v4",
        "node-version:",
        "cache-dependency-path: brick_protocol/support/dashboard/package-lock.json",
        "uv sync --locked",
        "brick verify --self-test",
        "dashboard build",
        "release_export negative probe",
        "clean-boundary output scan",
        "release_product_manifest negative probe",
        "sh brick_protocol/support/onboarding/release_gate.sh",
        "permissions:",
        "contents: read",
    )
    for required in required_workflow_texts:
        if required not in workflow:
            violations.append(f"workflow missing required text: {required!r}")
    for forbidden in ("git push", "gh api", "gh repo edit"):
        if forbidden in workflow:
            violations.append(f"workflow contains forbidden publish/settings verb: {forbidden!r}")

    if violations:
        raise ProfileError(
            "release_gate_contract rejected local release gate:\n"
            + "\n".join(f"- {violation}" for violation in violations)
        )

    return KernelResult(
        check_id="release_gate_contract",
        inspected=2,
        output=(
            "release gate contract passed: brick_protocol/support/onboarding/release_gate.sh "
            "runs compileall, check_profile.py --all, brick verify --self-test, "
            "a hard-fail dashboard npm ci/build, a release-export negative probe, "
            "a release-export dry-run with clean-boundary output scan, and a "
            "release_product_manifest negative leak-scan dry-run; "
            "the GitHub workflow invokes that local gate after uv sync --locked "
            "with read-only contents permission and an explicit Node setup for the "
            "dashboard build. PROOF LIMIT: support evidence "
            "only; this does not prove branch protection, publication, source "
            "truth, success, quality, or Movement authority."
        ),
    )
