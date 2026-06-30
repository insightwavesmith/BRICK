"""Onboarding install-script + release-export exclusion structural/safety lints.

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
_RELEASE_EXPORT_REQUIRED_EXCLUSIONS = (
    "project",
    "brick_protocol.egg-info",
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
      (g) it references the onboard wizard entry as the next step.

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
            "secret pattern, and references the onboard wizard entry. "
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


def _release_export_exclusion_violations(text: str) -> list[str]:
    exclusions = _release_export_exclusions(text)
    violations: list[str] = []
    if not exclusions:
        violations.append("missing literal EXCLUDE_PATHS tuple")
    for required in _RELEASE_EXPORT_REQUIRED_EXCLUSIONS:
        if required not in exclusions:
            violations.append(f"missing required exclusion: {required}/")
    if "git remote add origin git@github.com:{OWNER}/BRICK.git" not in text:
        violations.append("missing placeholder remote follow-up command")
    if "git tag v0.1.0" not in text:
        violations.append("missing v0.1.0 tag follow-up command")
    if "git push -u origin main" not in text or "git push origin v0.1.0" not in text:
        violations.append("missing manual push follow-up commands")
    return violations


def _release_export_exclusion_fire_probe(text: str) -> int:
    mutated = text.replace('    "project",\n', "", 1)
    violations = _release_export_exclusion_violations(mutated)
    if not any("missing required exclusion: project/" in violation for violation in violations):
        raise ProfileError(
            "release_export_exclusion FIRE probe did NOT fire when project/ "
            "was removed from the export exclusion list"
        )
    return 1


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
            "prints manual remote/tag/push follow-up commands with {OWNER}, and "
            "the temp mutation removing project/ fired RED. PROOF LIMIT: this is "
            "support evidence only; it does not run publication, choose Movement, "
            "or judge release quality."
        ),
    )
