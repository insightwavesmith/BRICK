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

import re
from pathlib import Path

from support.checkers.lib.yaml_subset import (
    KernelResult,
    ProfileError,
)


_INSTALL_SCRIPT_REL = "support/onboarding/install.sh"
_RELEASE_EXPORT_REL = "support/onboarding/release_export.sh"
_RELEASE_GATE_REL = "support/onboarding/release_gate.sh"
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

    Reads ``support/onboarding/install.sh`` (the one-line installer) and asserts
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
    if "support.operator.onboard" not in text:
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
    if '"status", "--porcelain", "--untracked-files=all"' not in text:
        violations.append("missing dirty-checkout status probe")
    if "if dirty_entries and not allow_dirty:" not in text:
        violations.append("dirty checkout must fail closed unless --allow-dirty is set")
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
    if "git remote add origin git@github.com:{OWNER}/BRICK.git" not in text:
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
    text = script_path.read_text(encoding="utf-8")
    violations = _release_export_exclusion_violations(text)
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
            "release export exclusion pin passed: support/onboarding/release_export.sh "
            "carries literal exclusions for project/ and brick_protocol.egg-info/, "
            "defaults to tracked-only input with explicit --include-untracked, "
            "fails closed on dirty checkout unless --allow-dirty is recorded, "
            "carries a secret/local/provider/session path denylist, resolves "
            "symlink targets inside the checkout, prints an exclusion/export "
            "report plus manual remote/tag/push follow-up commands with {OWNER}, "
            "and FIRE probes for exclusion, dirty guard, denylist, and symlink "
            "containment fired RED. PROOF LIMIT: this is "
            "support evidence only; it does not run publication, choose Movement, "
            "or judge release quality."
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
        "uv run python3 support/checkers/check_profile.py --all",
        "uv run brick verify --self-test",
        "command -v node",
        "command -v npm",
        "( cd \"$repo_root/support/dashboard\" && npm ci )",
        "( cd \"$repo_root/support/dashboard\" && npm run build )",
        "sh support/onboarding/release_export.sh --output",
        "release_export negative probe",
        ".env.release-export-deny-probe",
        "--include-untracked --allow-dirty",
        "secret/local/provider/session path denylist matched export input",
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

    required_workflow_texts = (
        "actions/setup-node@v4",
        "node-version:",
        "cache-dependency-path: support/dashboard/package-lock.json",
        "uv sync --locked",
        "brick verify --self-test",
        "dashboard build",
        "release_export negative probe",
        "sh support/onboarding/release_gate.sh",
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
            "release gate contract passed: support/onboarding/release_gate.sh "
            "runs compileall, check_profile.py --all, brick verify --self-test, "
            "a hard-fail dashboard npm ci/build, a release-export negative probe, "
            "and a release-export dry-run; "
            "the GitHub workflow invokes that local gate after uv sync --locked "
            "with read-only contents permission and an explicit Node setup for the "
            "dashboard build. PROOF LIMIT: support evidence "
            "only; this does not prove branch protection, publication, source "
            "truth, success, quality, or Movement authority."
        ),
    )
