"""Provider preflight checker-library kernel check.

Pure relocation sibling of kernel_checks. Support checker mechanics only: it
observes adapter preflight shape and no-raise behavior; it owns no axis crossing,
decides no Movement, and judges no success or quality.
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from support.checkers.lib.yaml_subset import (
    KernelResult,
    ProfileError,
    _ensure_import_identity,
)


_PROVIDER_PREFLIGHT_REQUIRED_KEYS = (
    "adapter_ref",
    "cli",
    "installed",
    "authed",
    "ok",
    "message_ko",
)
_PROVIDER_PREFLIGHT_AUTHED_LITERALS = ("yes", "no", "unknown")


def _provider_preflight_assert_shape(label: str, status: Any) -> None:
    if not isinstance(status, Mapping):
        raise ProfileError(
            f"provider_preflight: {label} must return a status mapping, got {type(status).__name__}"
        )
    missing = [key for key in _PROVIDER_PREFLIGHT_REQUIRED_KEYS if key not in status]
    if missing:
        raise ProfileError(
            f"provider_preflight: {label} status missing required key(s): {', '.join(missing)}"
        )
    if not isinstance(status["installed"], bool):
        raise ProfileError(f"provider_preflight: {label} 'installed' must be a bool")
    if not isinstance(status["ok"], bool):
        raise ProfileError(f"provider_preflight: {label} 'ok' must be a bool")
    if status["authed"] not in _PROVIDER_PREFLIGHT_AUTHED_LITERALS:
        raise ProfileError(
            f"provider_preflight: {label} 'authed' must be one of "
            f"{_PROVIDER_PREFLIGHT_AUTHED_LITERALS}, got {status['authed']!r}"
        )
    message = status["message_ko"]
    if not isinstance(message, str) or not message.strip():
        raise ProfileError(f"provider_preflight: {label} 'message_ko' must be non-empty text")


def run_provider_preflight(repo: Path) -> KernelResult:
    """ONBOARDING-PROVIDER-PREFLIGHT-0 execution checker.

    Imports preflight_provider from the Agent Adapter and asserts it (a) returns a
    status dict with the required keys for an ACTIVE adapter and adapter:local,
    (b) NEVER raises -- including for a deliberately bogus/retired adapter ref,
    where it must return ok False with a friendly message instead of raising, and
    (c) always carries a non-empty message_ko. This is the no-raise guard: if
    preflight_provider EVER raises (e.g. on a missing CLI), this checker goes RED.
    """

    _ensure_import_identity(repo)
    adapter = importlib.import_module("brick_protocol.support.connection.agent_adapter")
    adapter_constants = importlib.import_module("brick_protocol.support.connection.adapter_constants")
    adapter_subprocess = importlib.import_module("brick_protocol.support.connection.adapter_subprocess")
    from support.checkers.lib.case_runners import _preset_completion_command_runner

    command_runner = _preset_completion_command_runner(adapter.LocalCliCompleted)

    inspected = 0

    # (a) Active local CLI adapter + in-process adapter:local must each return a
    #     well-shaped status. preflight_provider must NOT raise for either.
    for label in (adapter_constants.ADAPTER_CODEX_LOCAL, adapter_constants.ADAPTER_LOCAL):
        try:
            status = adapter_subprocess.preflight_provider(label, command_runner=command_runner)
        except Exception as exc:  # noqa: BLE001 -- no-raise is the invariant under test
            raise ProfileError(
                f"provider_preflight: preflight_provider({label!r}) raised {type(exc).__name__}: {exc}"
            ) from exc
        _provider_preflight_assert_shape(label, status)
        if status["adapter_ref"] != label:
            raise ProfileError(
                f"provider_preflight: {label} status adapter_ref must echo the input"
            )
        inspected += 1

    # adapter:local has no CLI: it must report ready.
    local_status = adapter_subprocess.preflight_provider(
        adapter_constants.ADAPTER_LOCAL, command_runner=command_runner
    )
    if not (local_status["installed"] and local_status["ok"] and local_status["authed"] == "yes"):
        raise ProfileError(
            "provider_preflight: adapter:local must report installed/authed/ok ready"
        )

    # Gemini local API-key paths are never live-called by preflight; they must expose
    # key-presence evidence separately from credential validity so doctor/onboard
    # cannot turn a present-but-invalid key into an auth proof.
    gemini_status = adapter_subprocess.preflight_provider(
        adapter_constants.ADAPTER_GEMINI_LOCAL, command_runner=command_runner
    )
    _provider_preflight_assert_shape(adapter_constants.ADAPTER_GEMINI_LOCAL, gemini_status)
    if "api_key_env_present" not in gemini_status or not isinstance(
        gemini_status.get("api_key_env_present"), bool
    ):
        raise ProfileError(
            "provider_preflight: adapter:gemini-local must expose boolean api_key_env_present"
        )
    if gemini_status.get("credential_validity") != "not_proven":
        raise ProfileError(
            "provider_preflight: adapter:gemini-local must mark credential_validity=not_proven"
        )
    inspected += 1

    # (b) Deliberately bogus + retired refs must return ok False WITHOUT raising.
    for bogus_ref in (
        "adapter:bogus-not-a-real-provider",
        "adapter:codex-write-local",  # retired write adapter
        "",
    ):
        try:
            status = adapter_subprocess.preflight_provider(
                bogus_ref, command_runner=command_runner
            )
        except Exception as exc:  # noqa: BLE001 -- no-raise is the invariant under test
            raise ProfileError(
                "provider_preflight: preflight_provider must not raise for a bogus/retired "
                f"ref {bogus_ref!r}; raised {type(exc).__name__}: {exc}"
            ) from exc
        _provider_preflight_assert_shape(f"bogus={bogus_ref!r}", status)
        if status["ok"] is not False:
            raise ProfileError(
                f"provider_preflight: bogus/retired ref {bogus_ref!r} must return ok False"
            )
        inspected += 1

    return KernelResult(
        check_id="provider_preflight",
        inspected=inspected,
        output=(
            "provider preflight passed: preflight_provider returns a well-shaped "
            "status dict for active + in-process adapters, reports adapter:local "
            "ready, keeps Gemini API-key presence separate from credential validity, "
            "and returns ok False (never raises) for bogus/retired refs "
            f"({inspected} ref(s) inspected)."
        ),
    )
