#!/usr/bin/env python3
"""Pin the onboarding install success literal across docs and installer.

Support evidence only: this checker reads repository files and local temporary
copies. It does not execute the installer, call providers, choose Movement, or
judge quality.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


SUCCESS_LITERAL = "5) 설치 점검 완료"
FAILURE_LITERAL = "5) 설치 점검 실패"
STALE_VERIFY_STEP_LITERAL = "7) 설치 점검"
STALE_ENTRYPOINT_STEP_LITERAL = "5) brick 진입점"
STALE_INIT_STEP_LITERAL = "6) brick init"

# Preflight-first contract: every precondition must be diagnosed (and, where
# possible, auto-resolved -- including a uv-managed Python for a too-old/missing
# system Python) BEFORE any network download/sync. These needles pin that block
# in the installer; removing the preflight block turns this checker RED.
PREFLIGHT_NEEDLES = (
    "선검사 (preflight):",
    "preflight_all",
    "uv python install",
)

TARGETS = (
    "README.md",
    "support/docs/references/quickstart.md",
    "support/onboarding/install.sh",
)


class OnboardingSuccessLiteralError(ValueError):
    """Raised when the onboarding success literal contract drifts."""


def _read(repo: Path, rel_path: str) -> str:
    path = repo / rel_path
    if not path.is_file():
        raise OnboardingSuccessLiteralError(f"missing required file: {rel_path}")
    return path.read_text(encoding="utf-8")


def check_repo(repo: Path) -> None:
    texts = {rel_path: _read(repo, rel_path) for rel_path in TARGETS}

    missing = [
        rel_path
        for rel_path, text in texts.items()
        if SUCCESS_LITERAL not in text
    ]
    if missing:
        raise OnboardingSuccessLiteralError(
            f"success literal {SUCCESS_LITERAL!r} missing from: {', '.join(missing)}"
        )

    install_text = texts["support/onboarding/install.sh"]
    install_needles = (
        '"$brick_entry" verify',
        FAILURE_LITERAL,
    )
    missing_install_needles = [
        needle for needle in install_needles if needle not in install_text
    ]
    if missing_install_needles:
        raise OnboardingSuccessLiteralError(
            "installer does not pin the existing verify path and failure signal: "
            + ", ".join(repr(needle) for needle in missing_install_needles)
        )
    stale_label_needles = (
        STALE_VERIFY_STEP_LITERAL,
        STALE_ENTRYPOINT_STEP_LITERAL,
        STALE_INIT_STEP_LITERAL,
    )
    stale_label_hits = [needle for needle in stale_label_needles if needle in install_text]
    if stale_label_hits:
        raise OnboardingSuccessLiteralError(
            "installer still carries stale or competing install labels: "
            + ", ".join(repr(needle) for needle in stale_label_hits)
        )
    missing_preflight_needles = [
        needle for needle in PREFLIGHT_NEEDLES if needle not in install_text
    ]
    if missing_preflight_needles:
        raise OnboardingSuccessLiteralError(
            "installer dropped the preflight-first block (all preconditions must "
            "be diagnosed before any download/sync): "
            + ", ".join(repr(needle) for needle in missing_preflight_needles)
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        default=".",
        help="Repository root to inspect. Defaults to the current working directory.",
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    try:
        check_repo(repo)
    except OnboardingSuccessLiteralError as exc:
        print(f"onboarding_success_literal rejected evidence: {exc}", file=sys.stderr)
        return 1

    print(
        "onboarding_success_literal passed: README.md, "
        "support/docs/references/quickstart.md, and support/onboarding/install.sh "
        f"all carry {SUCCESS_LITERAL!r}; installer also carries "
        f"{FAILURE_LITERAL!r} and invokes the existing brick verify path. "
        "It does not carry stale or competing install labels "
        f"{STALE_VERIFY_STEP_LITERAL!r}, {STALE_ENTRYPOINT_STEP_LITERAL!r}, "
        f"or {STALE_INIT_STEP_LITERAL!r}. "
        "It also carries the preflight-first block "
        f"({', '.join(repr(needle) for needle in PREFLIGHT_NEEDLES)}). "
        "PROOF LIMIT: this checker does not execute install.sh or prove a fresh "
        "machine install; it pins the declared docs/script literal contract only."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
