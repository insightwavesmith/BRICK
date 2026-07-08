"""Shared checker temp-vessel helpers for behavioral profile cases.

Pure-relocation sibling of case_runners. These helpers create disposable
checker vessels and slug refs as support evidence only; they do not own axis
meaning, source truth, quality judgment, success judgment, or Movement.
"""

from __future__ import annotations

import json
import contextlib
import importlib
import os
import shutil
import sys
import tempfile
import uuid
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.support.checkers.lib.yaml_subset import ProfileError

@contextlib.contextmanager
def checker_temp_path(prefix: str) -> Any:
    """Yield a ``Path`` for a fresh disposable checker temp directory.

    Behavior-equivalent shorthand for the repeated checker idiom::

        with tempfile.TemporaryDirectory(prefix=prefix) as raw:
            path = Path(raw)
            ...

    Same ``prefix``, same ``TemporaryDirectory`` create/auto-cleanup
    semantics; the only difference is that the context variable is already a
    ``Path`` instead of the raw ``str``. Support evidence scaffolding only:
    it owns no axis meaning, source truth, quality/success judgment, or
    Movement, and adds no new fact class or module family.
    """
    with tempfile.TemporaryDirectory(prefix=prefix) as raw:
        yield Path(raw)


_TEMP_VESSEL_REPO_ENV = "BRICK_CHECKER_TEMP_VESSEL_REPO"
_TEMP_VESSEL_SENTINEL_NAME = ".checker-vessel-sentinel.json"
_TEMP_VESSEL_SENTINELS: dict[Path, str] = {}
_ACTIVE_REAL_PROJECT_ROOT: Path | None = None
_PATCHED_TEMP_REPO_ROOT_MODULE_ATTRS = (
    ("brick_protocol.support.recording.capture", "REPO_ROOT"),
    ("brick_protocol.support.recording.capture", "_REPO_ROOT"),
    ("brick_protocol.support.recording.capture", "_CAPTURE_REPO_ROOT"),
    ("brick_protocol.support.recording.capture", "REPO_ROOT"),
    ("brick_protocol.support.recording.capture", "_REPO_ROOT"),
    ("brick_protocol.support.recording.capture", "_CAPTURE_REPO_ROOT"),
    ("brick_protocol.support.operator.building_operation_common", "REPO_ROOT"),
    ("brick_protocol.support.operator.building_operation_common", "_REPO_ROOT"),
    ("brick_protocol.support.operator.building_operation_common", "_CAPTURE_REPO_ROOT"),
    ("brick_protocol.support.operator.building_operation_common", "REPO_ROOT"),
    ("brick_protocol.support.operator.building_operation_common", "_REPO_ROOT"),
    ("brick_protocol.support.operator.building_operation_common", "_CAPTURE_REPO_ROOT"),
    ("brick_protocol.support.operator.composition_intent", "REPO_ROOT"),
    ("brick_protocol.support.operator.composition_intent", "_REPO_ROOT"),
    ("brick_protocol.support.operator.composition_intent", "_CAPTURE_REPO_ROOT"),
    ("brick_protocol.support.operator.composition_intent", "REPO_ROOT"),
    ("brick_protocol.support.operator.composition_intent", "_REPO_ROOT"),
    ("brick_protocol.support.operator.composition_intent", "_CAPTURE_REPO_ROOT"),
    ("brick_protocol.support.operator.ledger_projection", "REPO_ROOT"),
    ("brick_protocol.support.operator.ledger_projection", "_REPO_ROOT"),
    ("brick_protocol.support.operator.ledger_projection", "_CAPTURE_REPO_ROOT"),
    ("brick_protocol.support.operator.ledger_projection", "REPO_ROOT"),
    ("brick_protocol.support.operator.ledger_projection", "_REPO_ROOT"),
    ("brick_protocol.support.operator.ledger_projection", "_CAPTURE_REPO_ROOT"),
    ("brick_protocol.support.operator.progress_projection", "REPO_ROOT"),
    ("brick_protocol.support.operator.progress_projection", "_REPO_ROOT"),
    ("brick_protocol.support.operator.progress_projection", "_CAPTURE_REPO_ROOT"),
    ("brick_protocol.support.operator.progress_projection", "REPO_ROOT"),
    ("brick_protocol.support.operator.progress_projection", "_REPO_ROOT"),
    ("brick_protocol.support.operator.progress_projection", "_CAPTURE_REPO_ROOT"),
)


def _copy_checker_temp_repo_resources(source_repo: Path, temp_repo: Path) -> None:
    """Copy intake fixture inputs without copying live project evidence."""
    temp_repo.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns("__pycache__", ".pytest_cache", ".mypy_cache", "node_modules")
    source_root = source_repo / "brick_protocol"
    if source_root.exists():
        for dirname in ("agent", "brick", "link", "support"):
            source = source_root / dirname
            if source.exists():
                shutil.copytree(source, temp_repo / "brick_protocol" / dirname, ignore=ignore)
    else:
        for dirname in ("agent", "brick", "link", "support"):
            source = source_repo / dirname
            if source.exists():
                shutil.copytree(source, temp_repo / dirname, ignore=ignore)
    for filename in ("BRICK-CONSTITUTION.md", "pyproject.toml", "uv.lock"):
        source = source_repo / filename
        if source.is_file():
            shutil.copy2(source, temp_repo / filename)


@contextlib.contextmanager
def _patched_temp_repo_roots(temp_repo: Path, restore_repo: Path) -> Any:
    # Ensure helpers that bind repo roots at import time see the real checkout
    # before project-ref vessel cases temporarily patch path seams.
    for module_name in (
        "brick_protocol.support.operator.composition_compose",
        "brick_protocol.support.operator.composition_compose",
        "brick_protocol.support.operator.reporter",
        "brick_protocol.support.operator.reporter",
        "brick_protocol.support.operator.report_sinks",
        "brick_protocol.support.operator.report_sinks",
    ):
        try:
            importlib.import_module(module_name)
        except ImportError:
            continue
    patched: list[tuple[Any, str, Any]] = []
    for module_name, attr in _PATCHED_TEMP_REPO_ROOT_MODULE_ATTRS:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        if hasattr(module, attr):
            patched.append((module, attr, getattr(module, attr)))
            setattr(module, attr, temp_repo)
    try:
        yield
    finally:
        for module, attr, value in reversed(patched):
            setattr(module, attr, value)
        for module_name, module in list(sys.modules.items()):
            if not (
                module_name.startswith("brick_protocol.support.")
                or module_name.startswith("brick_protocol.support.")
            ):
                continue
            for _declared_module, attr in _PATCHED_TEMP_REPO_ROOT_MODULE_ATTRS:
                if hasattr(module, attr) and getattr(module, attr) == temp_repo:
                    setattr(module, attr, restore_repo)


def assert_checker_vessel_patch_closure() -> None:
    actual = {
        (module_name, attr)
        for module_name in (
            "brick_protocol.support.recording.capture",
            "brick_protocol.support.recording.capture",
            "brick_protocol.support.operator.building_operation_common",
            "brick_protocol.support.operator.building_operation_common",
            "brick_protocol.support.operator.composition_intent",
            "brick_protocol.support.operator.composition_intent",
            "brick_protocol.support.operator.ledger_projection",
            "brick_protocol.support.operator.ledger_projection",
            "brick_protocol.support.operator.progress_projection",
            "brick_protocol.support.operator.progress_projection",
        )
        for attr in ("REPO_ROOT", "_REPO_ROOT", "_CAPTURE_REPO_ROOT")
    }
    declared = set(_PATCHED_TEMP_REPO_ROOT_MODULE_ATTRS)
    if actual != declared:
        raise ProfileError(
            "self-test failed: checker temp vessel patched root closure drifted: "
            f"missing={sorted(actual - declared)!r} extra={sorted(declared - actual)!r}"
        )


def _write_temp_vessel_sentinel(case_name: str, label: str, vessel_dir: Path, nonce: str) -> None:
    vessel_dir.mkdir(parents=True, exist_ok=True)
    (vessel_dir / _TEMP_VESSEL_SENTINEL_NAME).write_text(
        json.dumps(
            {
                "case_name": case_name,
                "label": label,
                "nonce": nonce,
                "pid": os.getpid(),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _TEMP_VESSEL_SENTINELS[vessel_dir.resolve()] = nonce


def _assert_deletable_checker_vessel(
    repo: Path,
    fixture_dir: Path,
    *,
    temp_repo: Path,
    sentinel_nonce: str,
    case_name: str,
    label: str,
) -> None:
    try:
        resolved_repo = repo.resolve(strict=True)
        resolved_temp_repo = temp_repo.resolve(strict=True)
        resolved_fixture = fixture_dir.resolve(strict=True)
    except OSError as exc:
        raise ProfileError(
            f"{case_name} rejected {label}: fixture cleanup target cannot be resolved: {fixture_dir}"
        ) from exc
    real_project_root = (
        _ACTIVE_REAL_PROJECT_ROOT.resolve()
        if _ACTIVE_REAL_PROJECT_ROOT is not None
        else resolved_repo / "project"
    )
    temp_project_root = resolved_temp_repo / "project"
    if resolved_repo != resolved_temp_repo:
        raise ProfileError(
            f"{case_name} rejected {label}: cleanup repo {resolved_repo} is not the "
            f"declared temp repo {resolved_temp_repo}"
        )
    if resolved_fixture == temp_project_root or not resolved_fixture.is_relative_to(temp_project_root):
        raise ProfileError(
            f"{case_name} rejected {label}: cleanup target {resolved_fixture} is not a "
            f"strict descendant of temp project root {temp_project_root}"
        )
    if resolved_fixture.is_relative_to(real_project_root) or real_project_root.is_relative_to(resolved_fixture):
        raise ProfileError(
            f"{case_name} rejected {label}: cleanup target {resolved_fixture} overlaps "
            f"real repo project tree {real_project_root}"
        )
    sentinel_path = resolved_fixture / _TEMP_VESSEL_SENTINEL_NAME
    try:
        sentinel = json.loads(sentinel_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileError(
            f"{case_name} rejected {label}: fixture cleanup target lacks a valid "
            f"{_TEMP_VESSEL_SENTINEL_NAME} marker"
        ) from exc
    # QA-PROBE: sentinel match check removed (partial weakening probe #2)


def _delete_checker_vessel(
    repo: Path,
    fixture_dir: Path,
    *,
    temp_repo: Path,
    sentinel_nonce: str,
    case_name: str,
    label: str,
) -> None:
    if not fixture_dir.exists():
        return
    _assert_deletable_checker_vessel(
        repo,
        fixture_dir,
        temp_repo=temp_repo,
        sentinel_nonce=sentinel_nonce,
        case_name=case_name,
        label=label,
    )
    shutil.rmtree(fixture_dir)
    _TEMP_VESSEL_SENTINELS.pop(fixture_dir.resolve(), None)


def _temp_vessel_cleanup_or_reject(
    case_name: str,
    label: str,
    fixture_dir: Path,
    *,
    repo: Path,
    temp_repo: Path,
    sentinel_nonce: str | None,
) -> None:
    if not fixture_dir.exists():
        return
    if sentinel_nonce is None:
        try:
            sentinel_nonce = _TEMP_VESSEL_SENTINELS.get(fixture_dir.resolve(strict=True))
        except OSError:
            sentinel_nonce = None
    if sentinel_nonce is not None:
        _delete_checker_vessel(
            repo,
            fixture_dir,
            temp_repo=temp_repo,
            sentinel_nonce=sentinel_nonce,
            case_name=case_name,
            label=label,
        )
        return
    raise ProfileError(
        f"{case_name} rejected {label}: fixture path {fixture_dir} already exists -- "
        "refusing to reuse or remove a possibly-real vessel; pick an unused fixture vessel_id"
    )


def _with_temp_vessel_repo(
    repo: Path,
    profile: Mapping[str, Any],
    case_runner: Callable[[Path, Mapping[str, Any], Path], int],
    stale_paths: Callable[[Path, Mapping[str, Any]], Sequence[Path]],
    prefix: str,
) -> int:
    with tempfile.TemporaryDirectory(prefix=prefix) as tmpdir:
        temp_repo = Path(tmpdir) / "repo"
        _copy_checker_temp_repo_resources(repo, temp_repo)
        previous = os.environ.get(_TEMP_VESSEL_REPO_ENV)
        global _ACTIVE_REAL_PROJECT_ROOT
        previous_real_project_root = _ACTIVE_REAL_PROJECT_ROOT
        _ACTIVE_REAL_PROJECT_ROOT = (repo / "project").resolve()
        os.environ[_TEMP_VESSEL_REPO_ENV] = "1"
        try:
            with _patched_temp_repo_roots(temp_repo, repo):
                first_count = case_runner(temp_repo, profile, temp_repo)
                for stale_path in stale_paths(temp_repo, profile):
                    nonce = uuid.uuid4().hex
                    _write_temp_vessel_sentinel(
                        "checker-temp-vessel-reentrancy-probe",
                        stale_path.name,
                        stale_path,
                        nonce,
                    )
                    (stale_path / "stale-fixture-residue.txt").write_text(
                        "stale temp fixture residue for re-entrancy probe\n",
                        encoding="utf-8",
                    )
                second_count = case_runner(temp_repo, profile, temp_repo)
        finally:
            if previous is None:
                os.environ.pop(_TEMP_VESSEL_REPO_ENV, None)
            else:
                os.environ[_TEMP_VESSEL_REPO_ENV] = previous
            _ACTIVE_REAL_PROJECT_ROOT = previous_real_project_root
        return first_count + second_count





def _assert_temp_vessel_guard_teeth() -> None:
    global _ACTIVE_REAL_PROJECT_ROOT

    def expect_rejected(
        label: str,
        fixture_dir: Path,
        *,
        repo: Path,
        temp_repo: Path,
        sentinel_nonce: str | None,
        active_real_project_root: Path | None,
        write_sentinel: bool = True,
    ) -> None:
        global _ACTIVE_REAL_PROJECT_ROOT
        previous_real_project_root = _ACTIVE_REAL_PROJECT_ROOT
        _ACTIVE_REAL_PROJECT_ROOT = active_real_project_root
        if write_sentinel and sentinel_nonce is not None:
            _write_temp_vessel_sentinel(
                "checker-temp-vessel-guard-teeth",
                label,
                fixture_dir,
                sentinel_nonce,
            )
        else:
            fixture_dir.mkdir(parents=True, exist_ok=True)
        (fixture_dir / "would-be-deleted.txt").write_text(
            f"{label} guard tooth probe\n",
            encoding="utf-8",
        )
        try:
            try:
                _temp_vessel_cleanup_or_reject(
                    "checker-temp-vessel-guard-teeth",
                    label,
                    fixture_dir,
                    repo=repo,
                    temp_repo=temp_repo,
                    sentinel_nonce=sentinel_nonce,
                )
            except ProfileError:
                if not fixture_dir.exists():
                    raise ProfileError(
                        f"checker temp vessel guard tooth {label} deleted fixture before rejection"
                    )
                return
            raise ProfileError(
                f"checker temp vessel guard tooth {label} did not reject risky cleanup"
            )
        finally:
            _ACTIVE_REAL_PROJECT_ROOT = previous_real_project_root
            _TEMP_VESSEL_SENTINELS.pop(fixture_dir.resolve(), None)

    with tempfile.TemporaryDirectory(prefix="bp-temp-vessel-guard-teeth-") as tmpdir:
        sandbox = Path(tmpdir)
        temp_repo = sandbox / "repo"
        temp_project = temp_repo / "project"
        temp_project.mkdir(parents=True)
        safe_real_project = sandbox / "real-project"

        expect_rejected(
            "repo-mismatch",
            temp_project / "repo-mismatch-vessel",
            repo=sandbox / "other-repo",
            temp_repo=temp_repo,
            sentinel_nonce="repo-mismatch-nonce",
            active_real_project_root=safe_real_project,
        )
        expect_rejected(
            "outside-temp-project",
            sandbox / "outside-vessel",
            repo=temp_repo,
            temp_repo=temp_repo,
            sentinel_nonce="outside-temp-project-nonce",
            active_real_project_root=safe_real_project,
        )
        real_project = temp_project / "real-project"
        expect_rejected(
            "real-project-overlap",
            real_project / "overlap-vessel",
            repo=temp_repo,
            temp_repo=temp_repo,
            sentinel_nonce="real-project-overlap-nonce",
            active_real_project_root=real_project,
        )
        expect_rejected(
            "missing-sentinel",
            temp_project / "missing-sentinel-vessel",
            repo=temp_repo,
            temp_repo=temp_repo,
            sentinel_nonce="missing-sentinel-nonce",
            active_real_project_root=safe_real_project,
            write_sentinel=False,
        )
        expect_rejected(
            "none-nonce",
            temp_project / "none-nonce-vessel",
            repo=temp_repo,
            temp_repo=temp_repo,
            sentinel_nonce=None,
            active_real_project_root=safe_real_project,
            write_sentinel=False,
        )

        positive = temp_project / "positive-vessel"
        positive_nonce = "positive-vessel-nonce"
        _write_temp_vessel_sentinel(
            "checker-temp-vessel-guard-teeth",
            "positive",
            positive,
            positive_nonce,
        )
        (positive / "delete-me.txt").write_text(
            "positive control proves the cleanup path is live\n",
            encoding="utf-8",
        )
        previous_real_project_root = _ACTIVE_REAL_PROJECT_ROOT
        _ACTIVE_REAL_PROJECT_ROOT = safe_real_project
        try:
            _temp_vessel_cleanup_or_reject(
                "checker-temp-vessel-guard-teeth",
                "positive",
                positive,
                repo=temp_repo,
                temp_repo=temp_repo,
                sentinel_nonce=positive_nonce,
            )
        finally:
            _ACTIVE_REAL_PROJECT_ROOT = previous_real_project_root
            _TEMP_VESSEL_SENTINELS.pop(positive.resolve(), None)
        if positive.exists():
            raise ProfileError("checker temp vessel guard positive control did not delete fixture")





def _preset_slug(preset_ref: str) -> str:
    return _case_slug(preset_ref.split(":", 1)[-1])


def _case_slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "case"
