"""Dashboard productization projection kernel-check leaf.

Pure relocation sibling of kernel_checks. Support checker mechanics only: it
observes the support-only dashboard projection/productization guard; it owns no
axis crossing, decides no Movement, and judges no success or quality.
"""

from __future__ import annotations

import argparse
import ast
import base64
import hmac
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from support.checkers.lib.chat_session_park_check import (
    _chat_session_write_temp_project_declaration,
)
from support.checkers.lib.no_smith_residue_check import _SMITH_USER_HOME_LITERAL
from support.checkers.lib.yaml_subset import KernelResult, ProfileError, to_posix

_DASHBOARD_PRODUCTIZATION_TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".mjs",
    ".yml",
    ".yaml",
}
_DASHBOARD_PRODUCTIZATION_SKIP_PARTS = {"dist", "node_modules"}
_DASHBOARD_PRODUCTIZATION_SKIP_RELATIVES = {
    "support/dashboard/package-lock.json",
    "support/dashboard/public/dashboard-data.json",
}
_DASHBOARD_PUBLIC_DATA_RELATIVE = "support/dashboard/public/dashboard-data.json"
_DASHBOARD_ALLOWED_URL_PREFIXES = (
    "https://fonts.googleapis.com",
    "https://fonts.gstatic.com",
    "http://brick_dashboard_upstream",
)
_DASHBOARD_ABSOLUTE_URL_RE = re.compile(r"https?://[^\s`'\"<>]+")
_DASHBOARD_PROJECT_FLAG_RE = re.compile(r"--project(?:=|\s+)(?P<value>[\"']?[^\s\\]+)")
_DASHBOARD_ARTIFACT_IMAGE_RE = re.compile(
    r"\b[A-Za-z0-9-]+-docker\.pkg\.dev/(?P<project>[^/\s`'\"<>]+)/"
)
_DASHBOARD_RESOURCE_PROJECT_RE = re.compile(r"\bprojects/(?P<project>[^/\s`'\"<>]+)/")
_DASHBOARD_ORG_RE = re.compile(r"\borganizations/[0-9]{4,}\b")
_DASHBOARD_USER_HOME_RE = re.compile(r"/Users/[^\s`'\"]+")


def _dashboard_placeholder_value(value: str) -> bool:
    cleaned = value.strip().strip("'\"").strip(",;")
    return (
        not cleaned
        or cleaned.startswith("$")
        or cleaned.startswith("<")
        or cleaned.startswith("{")
        or "${" in cleaned
        or cleaned.isupper()
    )


def _dashboard_url_allowed(value: str) -> bool:
    cleaned = value.strip().rstrip(".,);")
    return cleaned.startswith(_DASHBOARD_ALLOWED_URL_PREFIXES) or "${" in cleaned or "<" in cleaned


def _dashboard_productization_server_violations(text: str) -> list[str]:
    required_snippets = {
        "production env branch": "const IS_PRODUCTION = process.env.NODE_ENV === 'production'",
        "raw env-only ingest value": "const RAW_INGEST_SECRET = process.env.INGEST_SECRET",
        "normalized ingest env": "const NORMALIZED_INGEST_SECRET = RAW_INGEST_SECRET && RAW_INGEST_SECRET.trim()",
        "production dev fallback reject": "IS_PRODUCTION && (!NORMALIZED_INGEST_SECRET || NORMALIZED_INGEST_SECRET === 'dev-secret')",
        "fail-closed helper": "function ingestRefusesInProduction()",
        "POST fail-closed guard": "if (ingestRefusesInProduction())",
        "HMAC verifier": "function verifyIngestSignature(req, body)",
        "HMAC construction": "createHmac('sha256', INGEST_SECRET)",
        "timestamp skew window": "INGEST_TIMESTAMP_SKEW_SECONDS",
        "event replay cache": "seenEventIds.has(eventId)",
        "event replay record": "function rememberEventId(eventId)",
        "signed event id body match": "msg.event_id !== signatureCheck.eventId",
        "sequence rollback guard": "function rejectSequenceRollback(ref, msg)",
        "per-participant sequence table": "participantSequences.set(ref, sequence)",
    }
    violations = [
        f"server/index.mjs missing {label}: {snippet!r}"
        for label, snippet in required_snippets.items()
        if snippet not in text
    ]
    post_marker = "if (url === '/ingest' && req.method === 'POST')"
    fail_guard = "if (ingestRefusesInProduction())"
    signature_guard = "const signatureCheck = verifyIngestSignature(req, body)"
    try:
        post_idx = text.index(post_marker)
        fail_idx = text.index(fail_guard, post_idx)
        signature_idx = text.index(signature_guard, post_idx)
    except ValueError:
        return violations
    if not (post_idx < fail_idx < signature_idx):
        violations.append("server/index.mjs POST /ingest fail-closed guard must run before signature verification")
    if "req.headers['x-ingest-secret'] !== INGEST_SECRET" in text:
        violations.append("server/index.mjs must not authenticate ingest with raw x-ingest-secret equality")
    if "process.env.INGEST_SECRET || 'dev-secret'" in text:
        violations.append("server/index.mjs must not default directly from process.env.INGEST_SECRET to dev-secret")
    return violations


def _dashboard_productization_validate_server_text(text: str) -> None:
    violations = _dashboard_productization_server_violations(text)
    if violations:
        raise ProfileError(
            "dashboard_productization_projection server lint rejected evidence:\n"
            + "\n".join(f"- {violation}" for violation in violations)
        )


def _dashboard_productization_assert_mutated_server_rejects(text: str) -> int:
    mutations: tuple[tuple[str, Callable[[str], str]], ...] = (
        (
            "missing dev fallback rejection",
            lambda source: source.replace(
                "NORMALIZED_INGEST_SECRET === 'dev-secret'",
                "false",
                1,
            ),
        ),
        (
            "POST guard disabled",
            lambda source: source.replace(
                "if (ingestRefusesInProduction())",
                "if (false)",
                1,
            ),
        ),
        (
            "signature verifier removed",
            lambda source: source.replace(
                "function verifyIngestSignature(req, body)",
                "function verifyIngestSignature_removed(req, body)",
                1,
            ),
        ),
        (
            "replay cache disabled",
            lambda source: source.replace(
                "seenEventIds.has(eventId)",
                "false",
                1,
            ),
        ),
        (
            "signed event id body match removed",
            lambda source: source.replace(
                "msg.event_id !== signatureCheck.eventId",
                "false",
                1,
            ),
        ),
        (
            "sequence rollback guard removed",
            lambda source: source.replace(
                "function rejectSequenceRollback(ref, msg)",
                "function rejectSequenceRollback_removed(ref, msg)",
                1,
            ),
        ),
    )
    inspected = 0
    for label, mutate in mutations:
        inspected += 1
        mutated = mutate(text)
        if mutated == text:
            raise ProfileError(f"dashboard_productization_projection mutation did not apply: {label}")
        if not _dashboard_productization_server_violations(mutated):
            raise ProfileError(
                "dashboard_productization_projection FIRE probe did NOT fire for "
                f"mutated server copy: {label}"
            )
    return inspected


def _dashboard_productization_text_paths(repo: Path) -> list[Path]:
    root = repo / "support" / "dashboard"
    paths: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = to_posix(path.relative_to(repo))
        if any(part in _DASHBOARD_PRODUCTIZATION_SKIP_PARTS for part in path.relative_to(root).parts):
            continue
        if rel in _DASHBOARD_PRODUCTIZATION_SKIP_RELATIVES:
            continue
        if path.suffix in _DASHBOARD_PRODUCTIZATION_TEXT_SUFFIXES or path.name.startswith("."):
            paths.append(path)
    return paths


def _dashboard_productization_forbidden_literal_violations(repo: Path) -> tuple[list[str], int]:
    violations: list[str] = []
    inspected = 0
    for path in _dashboard_productization_text_paths(repo):
        rel = to_posix(path.relative_to(repo))
        text = path.read_text(encoding="utf-8")
        inspected += 1
        for lineno, line in enumerate(text.splitlines(), start=1):
            for match in _DASHBOARD_ABSOLUTE_URL_RE.finditer(line):
                if not _dashboard_url_allowed(match.group(0)):
                    violations.append(f"{rel}:{lineno}: hardcoded absolute URL literal: {match.group(0)!r}")
            for match in _DASHBOARD_PROJECT_FLAG_RE.finditer(line):
                value = match.group("value")
                if not _dashboard_placeholder_value(value):
                    violations.append(f"{rel}:{lineno}: hardcoded --project value: {value!r}")
            for match in _DASHBOARD_ARTIFACT_IMAGE_RE.finditer(line):
                project = match.group("project")
                if not _dashboard_placeholder_value(project):
                    violations.append(f"{rel}:{lineno}: hardcoded Artifact Registry project segment: {project!r}")
            for match in _DASHBOARD_RESOURCE_PROJECT_RE.finditer(line):
                project = match.group("project")
                if not _dashboard_placeholder_value(project):
                    violations.append(f"{rel}:{lineno}: hardcoded resource project segment: {project!r}")
            if _DASHBOARD_ORG_RE.search(line):
                violations.append(f"{rel}:{lineno}: hardcoded organization literal")
            if _DASHBOARD_USER_HOME_RE.search(line):
                violations.append(f"{rel}:{lineno}: hardcoded user-home path literal")
    return violations, inspected


def _dashboard_productization_assert_literal_fire_probe() -> int:
    probe_dir = Path("support/dashboard/DEPLOY.md")
    probe_lines = {
        "absolute-url": "gcloud run services describe --format='value(status.url)' https://service-hash-region.a.run.app",
        "project-flag": "gcloud run deploy service --project hardcoded-project",
        "artifact-project": "IMAGE=us-docker.pkg.dev/hardcoded-project/repo/service:tag",
        "resource-project": "projects/hardcoded-project/locations/region/services/service",
        "organization": "organizations/1234567890",
        "user-home": _SMITH_USER_HOME_LITERAL + "/project",
    }
    inspected = 0
    for label, line in probe_lines.items():
        inspected += 1
        with tempfile.TemporaryDirectory(prefix="bp-dashboard-literal-fire-") as tmp:
            probe_repo = Path(tmp)
            target = probe_repo / probe_dir
            target.parent.mkdir(parents=True)
            target.write_text(line + "\n", encoding="utf-8")
            violations, _ = _dashboard_productization_forbidden_literal_violations(probe_repo)
            if not violations:
                raise ProfileError(
                    "dashboard_productization_projection literal FIRE probe did "
                    f"NOT fire for {label}: {line!r}"
                )
    return inspected


def _dashboard_productization_assert_bake_shape_probe(repo: Path) -> int:
    from support.operator import dashboard_export

    inspected = 0
    with tempfile.TemporaryDirectory(prefix="bp-dashboard-bake-") as tmp:
        out_path = Path(tmp) / "dashboard-data.json"
        observation = dashboard_export.bake_dashboard_data_json(repo_root=repo, out_path=out_path)
        packet = json.loads(out_path.read_text(encoding="utf-8"))
        inspected += 1
        if observation.get("source_truth") is not False or packet.get("source_truth") is not False:
            raise ProfileError("dashboard bake probe wrote a source_truth true/non-false packet")
        if not isinstance(packet.get("buildings"), list):
            raise ProfileError("dashboard bake probe wrote a packet without a buildings list")
        if observation.get("buildings") != len(packet.get("buildings", [])):
            raise ProfileError("dashboard bake probe observation did not match written buildings length")

        original = dashboard_export.dashboard_export_packet

        def bad_packet(**_: Any) -> Mapping[str, Any]:
            return {"source_truth": True, "buildings": []}

        dashboard_export.dashboard_export_packet = bad_packet
        try:
            try:
                dashboard_export.bake_dashboard_data_json(repo_root=repo, out_path=out_path)
            except ValueError as exc:
                if "source_truth" not in str(exc):
                    raise ProfileError(
                        "dashboard bake FIRE probe rejected bad packet for the wrong reason: "
                        f"{exc}"
                    ) from exc
            else:
                raise ProfileError(
                    "dashboard bake FIRE probe did NOT reject a mutated source_truth true packet"
                )
        finally:
            dashboard_export.dashboard_export_packet = original
        inspected += 1
    return inspected


def _dashboard_productization_validate_public_seed_packet(packet: Any, *, label: str) -> None:
    if not isinstance(packet, Mapping):
        raise ProfileError(f"dashboard public seed {label} must be a JSON object")
    if packet.get("source_truth") is not False:
        raise ProfileError(f"dashboard public seed {label} source_truth must be false")
    if not isinstance(packet.get("buildings"), list):
        raise ProfileError(f"dashboard public seed {label} must carry a buildings list")


def _dashboard_productization_public_seed_observation(repo: Path) -> tuple[int, str]:
    seed_path = repo / _DASHBOARD_PUBLIC_DATA_RELATIVE
    if not seed_path.exists():
        return (
            0,
            f"{_DASHBOARD_PUBLIC_DATA_RELATIVE} absent; static dashboard seed validation skipped as generated-artifact advisory.",
        )
    try:
        packet = json.loads(seed_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProfileError(
            f"dashboard public seed {to_posix(seed_path.relative_to(repo))} is invalid JSON: {exc}"
        ) from exc
    _dashboard_productization_validate_public_seed_packet(
        packet,
        label=to_posix(seed_path.relative_to(repo)),
    )
    return (1, f"{_DASHBOARD_PUBLIC_DATA_RELATIVE} present; static dashboard seed shape validated.")


def _dashboard_productization_assert_public_seed_optional_probe() -> int:
    inspected = 0
    with tempfile.TemporaryDirectory(prefix="bp-dashboard-seed-optional-") as tmp:
        probe_repo = Path(tmp)
        missing_inspected, missing_observation = _dashboard_productization_public_seed_observation(probe_repo)
        inspected += 1
        if missing_inspected != 0 or "absent" not in missing_observation:
            raise ProfileError("dashboard public seed absent probe did not skip as advisory")

        seed_path = probe_repo / _DASHBOARD_PUBLIC_DATA_RELATIVE
        seed_path.parent.mkdir(parents=True)
        seed_path.write_text(
            json.dumps({"source_truth": False, "buildings": []}) + "\n",
            encoding="utf-8",
        )
        present_inspected, _ = _dashboard_productization_public_seed_observation(probe_repo)
        inspected += present_inspected
        if present_inspected != 1:
            raise ProfileError("dashboard public seed present probe did not inspect the seed")

        seed_path.write_text(
            json.dumps({"source_truth": True, "buildings": []}) + "\n",
            encoding="utf-8",
        )
        try:
            _dashboard_productization_public_seed_observation(probe_repo)
        except ProfileError:
            inspected += 1
        else:
            raise ProfileError("dashboard public seed FIRE probe did NOT fire for source_truth true")

        seed_path.write_text(
            json.dumps({"source_truth": False, "buildings": {}}) + "\n",
            encoding="utf-8",
        )
        try:
            _dashboard_productization_public_seed_observation(probe_repo)
        except ProfileError:
            inspected += 1
        else:
            raise ProfileError("dashboard public seed FIRE probe did NOT fire for non-list buildings")
    return inspected


def _dashboard_productization_captured_dashboard_request(
    report_sinks: Any,
    env: Mapping[str, str],
) -> urllib.request.Request:
    captured: list[urllib.request.Request] = []

    def capture_sender(request: urllib.request.Request, timeout_seconds: float) -> tuple[int, bytes]:
        if timeout_seconds <= 0:
            raise ProfileError("dashboard IAP passport probe received non-positive timeout")
        captured.append(request)
        return (200, b'{"ok":true}')

    presence = report_sinks._dashboard_environment_presence(env)
    observation = report_sinks._post_dashboard_projection(
        {"source_truth": False, "probe": "dashboard-iap-passport"},
        url=env[report_sinks.DASHBOARD_INGEST_URL_ENV],
        secret=env[report_sinks.DASHBOARD_INGEST_SECRET_ENV],
        packet_ref="dashboard-iap-passport-probe",
        proof_limits=("dashboard IAP passport offline checker probe only",),
        environment_presence=presence,
        env=env,
        timeout_seconds=1.0,
        sender=capture_sender,
    )
    if observation.delivery_status_class != "http_2xx":
        raise ProfileError("dashboard IAP passport probe did not observe captured http_2xx")
    if observation.environment_presence != presence:
        raise ProfileError("dashboard IAP passport probe did not preserve env presence-only packet")
    if len(captured) != 1:
        raise ProfileError(f"dashboard IAP passport probe expected one captured request, observed {len(captured)}")
    return captured[0]


def _dashboard_productization_request_headers(request: urllib.request.Request) -> Mapping[str, str]:
    return {key.lower(): value for key, value in request.header_items()}


def _dashboard_productization_decode_jwt_segment(segment: str) -> Mapping[str, Any]:
    padding = "=" * (-len(segment) % 4)
    decoded = json.loads(base64.urlsafe_b64decode((segment + padding).encode("ascii")).decode("utf-8"))
    if not isinstance(decoded, Mapping):
        raise ProfileError("dashboard IAP passport JWT segment did not decode to an object")
    return decoded


def _dashboard_productization_assert_authorization_header(
    headers: Mapping[str, str],
    *,
    expected_kid: str,
    expected_audience: str,
) -> None:
    authorization = headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        raise ProfileError("dashboard IAP passport probe missing Bearer Authorization header")
    token = authorization.removeprefix("Bearer ")
    segments = token.split(".")
    if len(segments) != 3 or any(not segment for segment in segments):
        raise ProfileError("dashboard IAP passport JWT must have three non-empty dot segments")
    header = _dashboard_productization_decode_jwt_segment(segments[0])
    claims = _dashboard_productization_decode_jwt_segment(segments[1])
    if header.get("kid") != expected_kid:
        raise ProfileError("dashboard IAP passport JWT header kid did not match throwaway key id")
    if header.get("alg") != "RS256" or header.get("typ") != "JWT":
        raise ProfileError("dashboard IAP passport JWT header must be RS256 JWT")
    if claims.get("aud") != expected_audience:
        raise ProfileError("dashboard IAP passport JWT audience did not match exact ingest URL")
    if claims.get("iss") != claims.get("sub") or claims.get("iss") != claims.get("email"):
        raise ProfileError("dashboard IAP passport JWT iss/sub/email claims must match")
    if not isinstance(claims.get("iat"), int) or not isinstance(claims.get("exp"), int):
        raise ProfileError("dashboard IAP passport JWT iat/exp claims must be integer seconds")
    if claims["exp"] - claims["iat"] != 600:
        raise ProfileError("dashboard IAP passport JWT expiration must be iat+600")


def _dashboard_productization_assert_absent_passport_headers(headers: Mapping[str, str]) -> None:
    required = {
        "content-type",
        "x-ingest-secret",
        "x-ingest-timestamp",
        "x-ingest-event-id",
        "x-ingest-signature",
    }
    missing = required - set(headers)
    if missing:
        raise ProfileError(
            "dashboard IAP passport absent-env headers missed signed ingest header(s): "
            f"{sorted(missing)}"
        )
    if headers.get("content-type") != "application/json; charset=utf-8":
        raise ProfileError("dashboard IAP passport absent-env content-type drifted")
    if headers.get("x-ingest-secret") != "probe-secret":
        raise ProfileError("dashboard IAP passport absent-env ingest secret header drifted")
    if not headers.get("x-ingest-signature", "").startswith("sha256="):
        raise ProfileError("dashboard IAP passport absent-env signature must use sha256= prefix")


def _dashboard_productization_assert_signed_ingest_request(request: urllib.request.Request) -> None:
    from support.operator import report_sinks

    headers = _dashboard_productization_request_headers(request)
    body = request.data
    if not isinstance(body, bytes):
        raise ProfileError("dashboard signed ingest probe captured non-bytes body")
    packet = json.loads(body.decode("utf-8"))
    for key in ("event_id", "event_timestamp", "sequence"):
        if key not in packet:
            raise ProfileError(f"dashboard signed ingest probe body missing {key}")
    if headers.get("x-ingest-event-id") != packet["event_id"]:
        raise ProfileError("dashboard signed ingest probe event id header/body mismatch")
    if headers.get("x-ingest-timestamp") != str(packet["event_timestamp"]):
        raise ProfileError("dashboard signed ingest probe timestamp header/body mismatch")
    expected = report_sinks._dashboard_projection_signature(
        secret="probe-secret",
        body=body,
        event_id=headers["x-ingest-event-id"],
        timestamp=headers["x-ingest-timestamp"],
    )
    if not hmac.compare_digest(headers.get("x-ingest-signature", ""), expected):
        raise ProfileError("dashboard signed ingest probe HMAC did not match captured body")


def _dashboard_productization_throwaway_sa_env(report_sinks: Any, root: Path) -> tuple[Mapping[str, str], str, str]:
    private_key_path = root / "throwaway-dashboard-iap.pem"
    key_json_path = root / "throwaway-dashboard-iap.json"
    generated = subprocess.run(
        ["openssl", "genrsa", "-out", str(private_key_path), "2048"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if generated.returncode != 0:
        raise ProfileError("dashboard IAP passport probe could not generate throwaway RSA key")
    private_key = private_key_path.read_text(encoding="utf-8")
    key_id = "throwaway-dashboard-iap-kid"
    client_email = "dashboard-iap-passport-probe@example.invalid"
    key_json_path.write_text(
        json.dumps(
            {
                "client_email": client_email,
                "private_key_id": key_id,
                "private_key": private_key,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    ingest_url = "https://brick-dashboard-probe.example.invalid/ingest"
    env = {
        report_sinks.DASHBOARD_INGEST_URL_ENV: ingest_url,
        report_sinks.DASHBOARD_INGEST_SECRET_ENV: "probe-secret",
        report_sinks.DASHBOARD_SA_KEY_PATH_ENV: str(key_json_path),
    }
    return env, key_id, ingest_url


def _dashboard_productization_assert_iap_passport_probe() -> int:
    from support.operator import report_sinks

    inspected = 0
    with tempfile.TemporaryDirectory(prefix="bp-dashboard-iap-passport-") as tmp:
        env, key_id, ingest_url = _dashboard_productization_throwaway_sa_env(report_sinks, Path(tmp))

        request = _dashboard_productization_captured_dashboard_request(report_sinks, env)
        headers = _dashboard_productization_request_headers(request)
        _dashboard_productization_assert_signed_ingest_request(request)
        _dashboard_productization_assert_authorization_header(
            headers,
            expected_kid=key_id,
            expected_audience=ingest_url,
        )
        inspected += 1

        absent_env = {
            report_sinks.DASHBOARD_INGEST_URL_ENV: ingest_url,
            report_sinks.DASHBOARD_INGEST_SECRET_ENV: "probe-secret",
        }
        absent_request = _dashboard_productization_captured_dashboard_request(report_sinks, absent_env)
        _dashboard_productization_assert_signed_ingest_request(absent_request)
        _dashboard_productization_assert_absent_passport_headers(
            _dashboard_productization_request_headers(absent_request)
        )
        inspected += 1

        original_authorization = report_sinks._dashboard_iap_authorization_header

        def removed_authorization(audience: str, env: Mapping[str, str]) -> str:
            return ""

        report_sinks._dashboard_iap_authorization_header = removed_authorization
        try:
            mutated_request = _dashboard_productization_captured_dashboard_request(report_sinks, env)
            mutated_headers = _dashboard_productization_request_headers(mutated_request)
            if mutated_headers.get("authorization") == headers.get("authorization"):
                raise ProfileError("dashboard IAP passport mutation did not alter Authorization attachment")
            try:
                _dashboard_productization_assert_authorization_header(
                    mutated_headers,
                    expected_kid=key_id,
                    expected_audience=ingest_url,
                )
            except ProfileError:
                inspected += 1
            else:
                raise ProfileError("dashboard IAP passport FIRE probe did NOT fire when Authorization was removed")
        finally:
            report_sinks._dashboard_iap_authorization_header = original_authorization
    return inspected


def _dashboard_productization_assert_openssl_subprocess_scope(repo: Path) -> int:
    report_sinks_path = repo / "support/operator/report_sinks.py"
    tree = ast.parse(report_sinks_path.read_text(encoding="utf-8"))
    subprocess_attrs: list[str] = []
    run_calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "subprocess":
            subprocess_attrs.append(node.attr)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
            and node.func.attr == "run"
        ):
            run_calls.append(node)
    unexpected_attrs = sorted(set(subprocess_attrs) - {"PIPE", "run"})
    if unexpected_attrs:
        raise ProfileError(
            "dashboard IAP passport subprocess scope admitted only subprocess.run/PIPE, "
            f"observed {unexpected_attrs}"
        )
    if len(run_calls) != 1:
        raise ProfileError(f"dashboard IAP passport expected exactly one subprocess.run, observed {len(run_calls)}")
    call = run_calls[0]
    command = call.args[0] if call.args else None
    if not isinstance(command, ast.List) or len(command.elts) != 5:
        raise ProfileError("dashboard IAP passport subprocess command must be a five-item argv list")
    expected_prefix = ("openssl", "dgst", "-sha256", "-sign")
    for index, expected in enumerate(expected_prefix):
        item = command.elts[index]
        if not isinstance(item, ast.Constant) or item.value != expected:
            raise ProfileError("dashboard IAP passport subprocess command must be openssl dgst -sha256 -sign")
    if not isinstance(command.elts[4], ast.Name) or command.elts[4].id != "key_file_path":
        raise ProfileError("dashboard IAP passport subprocess key argument must be the local temp key file")
    for keyword in call.keywords:
        if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
            raise ProfileError("dashboard IAP passport subprocess must not use shell=True")
    return 1


_DASHBOARD_STATE_CASE_EXPECTED: Mapping[str, Mapping[str, str]] = {
    "projection-closed": {
        "frontier_kind": "complete",
        "board_state": "closed",
        "disp": "closed",
    },
    "projection-mid-walk": {
        "frontier_kind": "closure_pending",
        "board_state": "observed_running",
        "disp": "running",
    },
    "projection-declared-edge-mid-walk": {
        "frontier_kind": "closure_pending",
        "board_state": "observed_running",
        "disp": "running",
    },
    "projection-adapter-error": {
        "frontier_kind": "agent_incomplete",
        "board_state": "link_paused",
        "disp": "stopped",
    },
    "projection-fossil": {
        "frontier_kind": "closure_pending",
        "board_state": "unknown",
        "disp": "unknown",
    },
    "projection-parked": {
        "frontier_kind": "chat_session_parked",
        "board_state": "waiting_review",
        "disp": "review",
    },
}


def _dashboard_productization_assert_state_projection_cases(
    repo: Path,
) -> tuple[int, str]:
    """Pin non-happy read-side state derivation over generated fixture roots.

    The fixture roots are support-checker inputs only. They exercise already
    admitted ledger/dashboard projections and do not write project evidence.
    """

    from brick_protocol.support.operator import frontier_observation
    from support.operator import dashboard_export, ledger_projection

    inspected = 0
    with tempfile.TemporaryDirectory(prefix="bp-dashboard-state-projection-") as tmp:
        temp_repo = Path(tmp) / "repo"
        buildings_root = temp_repo / "project" / "brick-protocol" / "buildings"
        buildings_root.mkdir(parents=True)
        _chat_session_write_temp_project_declaration(temp_repo)
        for case_id in _DASHBOARD_STATE_CASE_EXPECTED:
            _dashboard_state_write_fixture(buildings_root / case_id, case_id)

        ledger = ledger_projection.project_orchestration_ledger_packet(repo_root=temp_repo)
        dashboard = dashboard_export.dashboard_export_packet(repo_root=temp_repo)
        table = _dashboard_state_projection_table(ledger, dashboard)
        _dashboard_state_assert_expected(table, label="fixture")
        inspected += len(table)

        original_board_state = ledger_projection._project_ledger_board_state
        original_dashboard_packet = dashboard_export.project_orchestration_ledger_packet

        def bad_board_state(frontier_kind: str, *args: Any, **kwargs: Any) -> str:
            if frontier_kind == "agent_incomplete":
                return "observed_running"
            return original_board_state(frontier_kind, *args, **kwargs)

        ledger_projection._project_ledger_board_state = bad_board_state
        try:
            mutated_ledger = ledger_projection.project_orchestration_ledger_packet(
                repo_root=temp_repo
            )
            dashboard_export.project_orchestration_ledger_packet = (
                lambda **_: mutated_ledger
            )
            mutated_dashboard = dashboard_export.dashboard_export_packet(repo_root=temp_repo)
            mutated_table = _dashboard_state_projection_table(
                mutated_ledger,
                mutated_dashboard,
            )
            adapter_row = {
                str(row.get("building_id")): row for row in mutated_table
            }.get("projection-adapter-error")
            if not adapter_row or adapter_row.get("disp") != "running":
                raise ProfileError(
                    "dashboard_productization_projection FIRE mutation did not apply: "
                    f"adapter-error row was {adapter_row!r}"
                )
            try:
                _dashboard_state_assert_expected(mutated_table, label="mutated")
            except ProfileError:
                inspected += 1
            else:
                raise ProfileError(
                    "dashboard_productization_projection FIRE probe did NOT fire "
                    "for breakdown->running board-state mutation"
                )
        finally:
            ledger_projection._project_ledger_board_state = original_board_state
            dashboard_export.project_orchestration_ledger_packet = original_dashboard_packet

        original_closed_boundary_observed = frontier_observation._closed_boundary_observed

        def bad_closed_boundary_observed(
            link_records: Sequence[Mapping[str, Any]],
            building_map: Mapping[str, Any],
        ) -> bool:
            if original_closed_boundary_observed(link_records, building_map):
                return True
            for record in reversed(link_records):
                target = str(
                    record.get("target_brick_instance_ref")
                    or record.get("target")
                    or ""
                )
                if frontier_observation._is_closed_boundary_ref(target):
                    return True
            link_edges = building_map.get("link_edges")
            if isinstance(link_edges, list):
                for edge in link_edges:
                    if not isinstance(edge, Mapping):
                        continue
                    target = str(edge.get("target_brick_instance_ref") or "")
                    if frontier_observation._is_closed_boundary_ref(target):
                        return True
            return False

        frontier_observation._closed_boundary_observed = bad_closed_boundary_observed
        try:
            mutated_ledger = ledger_projection.project_orchestration_ledger_packet(
                repo_root=temp_repo
            )
            dashboard_export.project_orchestration_ledger_packet = (
                lambda **_: mutated_ledger
            )
            mutated_dashboard = dashboard_export.dashboard_export_packet(repo_root=temp_repo)
            mutated_table = _dashboard_state_projection_table(
                mutated_ledger,
                mutated_dashboard,
            )
            mid_walk_row = {
                str(row.get("building_id")): row for row in mutated_table
            }.get("projection-mid-walk")
            if not mid_walk_row or mid_walk_row.get("disp") != "closed":
                raise ProfileError(
                    "dashboard_productization_projection FIRE mutation did not apply: "
                    f"mid-walk row was {mid_walk_row!r}"
                )
            declared_edge_row = {
                str(row.get("building_id")): row for row in mutated_table
            }.get("projection-declared-edge-mid-walk")
            if not declared_edge_row or declared_edge_row.get("disp") != "closed":
                raise ProfileError(
                    "dashboard_productization_projection FIRE mutation did not apply: "
                    f"declared-edge mid-walk row was {declared_edge_row!r}"
                )
            try:
                _dashboard_state_assert_expected(mutated_table, label="closed-boundary-mutated")
            except ProfileError:
                inspected += 1
            else:
                raise ProfileError(
                    "dashboard_productization_projection FIRE probe did NOT fire "
                    "for closed-without-boundary mutation"
                )
        finally:
            frontier_observation._closed_boundary_observed = original_closed_boundary_observed
            dashboard_export.project_orchestration_ledger_packet = original_dashboard_packet

    return inspected, _dashboard_state_format_table(table)


def _dashboard_state_projection_table(
    ledger: Mapping[str, Any],
    dashboard: Mapping[str, Any],
) -> list[Mapping[str, str]]:
    dashboard_rows = {
        str(row.get("id")): row
        for row in dashboard.get("buildings", [])
        if isinstance(row, Mapping)
    }
    table: list[Mapping[str, str]] = []
    for row in ledger.get("rows", []):
        if not isinstance(row, Mapping):
            continue
        building_id = str(row.get("building_id") or "")
        if building_id not in _DASHBOARD_STATE_CASE_EXPECTED:
            continue
        dashboard_row = dashboard_rows.get(building_id, {})
        table.append(
            {
                "building_id": building_id,
                "frontier_kind": str(row.get("frontier_kind") or ""),
                "board_state": str(row.get("board_state") or ""),
                "disp": str(dashboard_row.get("disp") or ""),
            }
        )
    return sorted(table, key=lambda item: item["building_id"])


def _dashboard_state_assert_expected(
    table: Sequence[Mapping[str, str]],
    *,
    label: str,
) -> None:
    rows = {str(row.get("building_id")): row for row in table}
    missing = sorted(set(_DASHBOARD_STATE_CASE_EXPECTED) - set(rows))
    if missing:
        raise ProfileError(
            f"dashboard_productization_projection {label} state table missing "
            f"case(s): {', '.join(missing)}"
        )
    violations: list[str] = []
    for building_id, expected in _DASHBOARD_STATE_CASE_EXPECTED.items():
        row = rows[building_id]
        for key, expected_value in expected.items():
            if row.get(key) != expected_value:
                violations.append(
                    f"{building_id}.{key}: expected {expected_value!r}, "
                    f"observed {row.get(key)!r}"
                )
    if violations:
        raise ProfileError(
            f"dashboard_productization_projection {label} state table rejected:\n"
            + "\n".join(f"- {violation}" for violation in violations)
        )


def _dashboard_state_format_table(table: Sequence[Mapping[str, str]]) -> str:
    lines = ["building_id\tfrontier_kind\tboard_state\tdisp"]
    for row in table:
        lines.append(
            "\t".join(
                str(row.get(key, ""))
                for key in ("building_id", "frontier_kind", "board_state", "disp")
            )
        )
    return "\n".join(lines)


def _dashboard_state_write_fixture(building_root: Path, case_id: str) -> None:
    if case_id == "projection-closed":
        _dashboard_state_write_complete_fixture(
            building_root,
            raw_link_records=[
                _dashboard_state_link_record(
                    case_id,
                    target_ref=f"building-boundary:{case_id}-closed",
                    building_lifecycle_state="closed",
                )
            ],
            map_target_ref=f"building-boundary:{case_id}-closed",
        )
        return
    if case_id == "projection-mid-walk":
        _dashboard_state_write_complete_fixture(
            building_root,
            raw_link_records=[
                _dashboard_state_link_record(
                    case_id,
                    target_ref=f"brick:{case_id}:next",
                )
            ],
            map_target_ref=f"building-boundary:{case_id}-closed",
        )
        return
    if case_id == "projection-declared-edge-mid-walk":
        _dashboard_state_write_complete_fixture(
            building_root,
            raw_link_records=[
                _dashboard_state_link_record(
                    case_id,
                    target_ref=f"brick:{case_id}:next",
                ),
                _dashboard_state_declared_graph_link_record(
                    case_id,
                    target_ref=f"building-boundary:{case_id}-closed",
                ),
            ],
            map_target_ref=f"building-boundary:{case_id}-closed",
        )
        return
    if case_id == "projection-adapter-error":
        _dashboard_state_write_frontier_fixture(building_root, case_id)
        return
    if case_id == "projection-fossil":
        _dashboard_state_write_complete_fixture(
            building_root,
            raw_agent_return_records=[],
            raw_link_records=[],
            map_target_ref=f"brick:{case_id}:unknown-next",
        )
        return
    if case_id == "projection-parked":
        _dashboard_state_write_parked_fixture(building_root, case_id)
        return
    raise ProfileError(f"unknown dashboard state fixture case: {case_id}")


def _dashboard_state_write_complete_fixture(
    building_root: Path,
    *,
    raw_link_records: Sequence[Mapping[str, Any]],
    map_target_ref: str,
    raw_agent_return_records: Sequence[Mapping[str, Any]] | None = None,
) -> None:
    case_id = building_root.name
    _dashboard_state_write_common_files(
        building_root,
        case_id,
        map_target_ref=map_target_ref,
    )
    raw = building_root / "raw"
    agent_returns = (
        raw_agent_return_records
        if raw_agent_return_records is not None
        else [_dashboard_state_agent_return_record(case_id)]
    )
    _dashboard_state_write_jsonl(raw / "agent-return.jsonl", agent_returns)
    _dashboard_state_write_jsonl(raw / "link.jsonl", raw_link_records)
    for rel in (
        "evidence/claim_trace/agent/returned_claims.json",
        "evidence/claim_trace/link/transfer_trace.json",
        "evidence/claim_trace/link/carry_trace.json",
        "evidence/claim_trace/link/sufficiency_trace.json",
        "evidence/claim_trace/link/movement_trace.json",
    ):
        _dashboard_state_write_json(
            building_root / rel,
            {"facts": [{"ref": f"{case_id}:{rel}"}]},
        )


def _dashboard_state_write_frontier_fixture(building_root: Path, case_id: str) -> None:
    _dashboard_state_write_common_files(
        building_root,
        case_id,
        map_target_ref=f"brick:{case_id}:blocked-next",
    )
    raw = building_root / "raw"
    _dashboard_state_write_jsonl(
        raw / "agent-received.jsonl",
        [{"received_work_ref": f"work:{case_id}"}],
    )
    _dashboard_state_write_jsonl(
        raw / "adapter-error.jsonl",
        [{"adapter_error_ref": f"adapter-error:{case_id}"}],
    )
    _dashboard_state_write_jsonl(
        raw / "link.jsonl",
        [
            _dashboard_state_link_record(
                case_id,
                target_ref=f"brick:{case_id}:blocked-next",
            )
        ],
    )
    step_dir = building_root / "work" / "step-outputs" / f"{case_id}-attempt-1"
    _dashboard_state_write_json(
        step_dir / "adapter-error.json",
        {"adapter_error_ref": f"adapter-error:{case_id}"},
    )
    for rel in (
        "evidence/claim_trace/agent/receipt_trace.json",
        "evidence/claim_trace/link/frontier_trace.json",
    ):
        _dashboard_state_write_json(
            building_root / rel,
            {"facts": [{"ref": f"{case_id}:{rel}"}]},
        )


def _dashboard_state_write_parked_fixture(building_root: Path, case_id: str) -> None:
    _dashboard_state_write_common_files(
        building_root,
        case_id,
        map_target_ref=f"brick:{case_id}:parked-next",
    )
    raw = building_root / "raw"
    _dashboard_state_write_jsonl(
        raw / "agent-received.jsonl",
        [{"received_work_ref": f"work:{case_id}"}],
    )
    _dashboard_state_write_jsonl(
        raw / "chat-session-park.jsonl",
        [{"parked_ref": f"parked:{case_id}"}],
    )
    _dashboard_state_write_jsonl(
        raw / "link.jsonl",
        [
            {
                **_dashboard_state_link_record(
                    case_id,
                    target_ref=f"brick:{case_id}:parked-next",
                ),
                "frontier_kind": "chat_session_parked",
                "transition_lifecycle_state": "paused",
                "transition_lifecycle_progress_state": "in_progress",
                "transition_lifecycle_paused_at_ref": f"raw:link:{case_id}:parked",
                "transition_lifecycle_required_disposition_owner": "caller-or-coo",
            }
        ],
    )
    step_dir = building_root / "work" / "step-outputs" / f"{case_id}-attempt-1"
    _dashboard_state_write_json(
        step_dir / "work-envelope.json",
        {"adapter_ref": "adapter:chat-session"},
    )
    _dashboard_state_write_json(step_dir / "parked.json", {"parked_ref": f"parked:{case_id}"})
    for rel in (
        "evidence/claim_trace/agent/receipt_trace.json",
        "evidence/claim_trace/link/frontier_trace.json",
    ):
        _dashboard_state_write_json(
            building_root / rel,
            {"facts": [{"ref": f"{case_id}:{rel}"}]},
        )


def _dashboard_state_write_common_files(
    building_root: Path,
    case_id: str,
    *,
    map_target_ref: str,
) -> None:
    _dashboard_state_write_jsonl(
        building_root / "capture" / "events.jsonl",
        [{"event_ref": f"event:{case_id}:fixture"}],
    )
    _dashboard_state_write_json(
        building_root / "raw" / "raw-manifest.json",
        {"kind": "raw_manifest"},
    )
    _dashboard_state_write_jsonl(
        building_root / "raw" / "brick-work.jsonl",
        [{"brick_work_ref": f"work:{case_id}"}],
    )
    _dashboard_state_write_json(
        building_root / "evidence" / "evidence-manifest.json",
        {"kind": "evidence_manifest"},
    )
    _dashboard_state_write_json(
        building_root / "evidence" / "claim_trace" / "brick" / "work_contract.json",
        {"facts": [{"brick_work_ref": f"work:{case_id}"}]},
    )
    _dashboard_state_write_json(
        building_root / "work" / "building-work.json",
        {
            "plan_ref": f"building-plan:{case_id}",
            "task_source_ref": f"task-source:{case_id}",
        },
    )
    _dashboard_state_write_json(
        building_root / "work" / "building-map.json",
        {
            "kind": "building_map",
            "task_source_ref": f"task-source:{case_id}",
            "brick_instances": [
                {
                    "brick_instance_ref": f"brick:{case_id}:work",
                    "brick_instance_id": f"brick:{case_id}:work",
                    "attempt_index": 1,
                }
            ],
            "agent_bindings": [
                {
                    "agent_binding_id": f"agent-binding:{case_id}",
                    "brick_instance_ref": f"brick:{case_id}:work",
                    "agent_performer_ref": "agent-object:dev",
                    "step_output_ref": f"work/step-outputs/{case_id}-attempt-1/step-output.json",
                }
            ],
            "link_edges": [
                {
                    "link_edge_id": f"link-edge:{case_id}",
                    "source_brick_instance_ref": f"brick:{case_id}:work",
                    "target_brick_instance_ref": map_target_ref,
                    "edge_role": "fixture",
                }
            ],
            "groups": [],
        },
    )


def _dashboard_state_agent_return_record(case_id: str) -> Mapping[str, Any]:
    return {
        "received_work": {"received_work_ref": f"work:{case_id}"},
        "returned": {"observed_evidence": [f"fixture:{case_id}"]},
    }


def _dashboard_state_recent_recorded_at() -> str:
    """Relative-recent fixture timestamp (DETERMINISM FIX 0619).

    Previously hardcoded "2026-06-12T00:00:00Z"; the dashboard staleness
    projection (dashboard_export._disp_state: age_days >= stale_days=7 ->
    archived_stale) compares last-evidence vs now(), so a fixed fixture date
    aged past the 7-day window and flipped projection-mid-walk from the expected
    'running' to 'archived_stale' (a time-bomb that turned --all RED on 0619 = the
    fixture date + 7d). A recent (now - 1 day) timestamp keeps the mid-walk fixture
    inside the live window deterministically -> always 'running'.
    """

    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dashboard_state_link_record(
    case_id: str,
    *,
    target_ref: str,
    building_lifecycle_state: str = "",
) -> Mapping[str, Any]:
    record = {
        "raw_ref": f"raw:link:{case_id}",
        "recorded_at": _dashboard_state_recent_recorded_at(),
        "step_ref": f"step:{case_id}",
        "source_brick_instance_ref": f"brick:{case_id}:work",
        "target_brick_instance_ref": target_ref,
        "movement": "forward",
    }
    if building_lifecycle_state:
        record["building_lifecycle_state"] = building_lifecycle_state
    return record


def _dashboard_state_declared_graph_link_record(
    case_id: str,
    *,
    target_ref: str,
) -> Mapping[str, Any]:
    return {
        "raw_ref": f"raw:link-graph:01:edge-{case_id}-closure-to-boundary",
        "raw_refs": [f"raw:link-graph:01:edge-{case_id}-closure-to-boundary"],
        "recorded_at": _dashboard_state_recent_recorded_at(),
        "step_ref": f"step:{case_id}:closure",
        "source_step_ref": f"step:{case_id}:closure",
        "source_brick_instance_ref": f"brick:{case_id}:closure",
        "target_brick_instance_ref": target_ref,
        "target": target_ref,
        "movement": "forward",
        "movement_source": "declared graph Building Plan Link edge",
        "declared_graph_edge": True,
        "is_completion_edge": True,
    }


def _dashboard_state_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _dashboard_state_write_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(dict(record), sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def run_dashboard_productization_projection(repo: Path) -> KernelResult:
    """Dashboard deploy/env/bake guard for the support-only dashboard surface."""

    required_paths = (
        repo / "support/dashboard/DEPLOY.md",
        repo / "support/dashboard/server/index.mjs",
    )
    missing = [to_posix(path.relative_to(repo)) for path in required_paths if not path.exists()]
    if missing:
        raise ProfileError(
            "dashboard_productization_projection missing required path(s): "
            + ", ".join(missing)
        )

    inspected = 0
    seed_inspected, seed_observation = _dashboard_productization_public_seed_observation(repo)
    inspected += seed_inspected
    inspected += _dashboard_productization_assert_public_seed_optional_probe()

    server_text = (repo / "support/dashboard/server/index.mjs").read_text(encoding="utf-8")
    _dashboard_productization_validate_server_text(server_text)
    inspected += 1
    inspected += _dashboard_productization_assert_mutated_server_rejects(server_text)

    literal_violations, literal_inspected = _dashboard_productization_forbidden_literal_violations(repo)
    inspected += literal_inspected
    if literal_violations:
        raise ProfileError(
            "dashboard_productization_projection hardcoded-literal lint rejected evidence:\n"
            + "\n".join(f"- {violation}" for violation in literal_violations)
        )
    inspected += _dashboard_productization_assert_literal_fire_probe()
    inspected += _dashboard_productization_assert_bake_shape_probe(repo)
    inspected += _dashboard_productization_assert_openssl_subprocess_scope(repo)
    inspected += _dashboard_productization_assert_iap_passport_probe()
    state_inspected, state_table = _dashboard_productization_assert_state_projection_cases(repo)
    inspected += state_inspected

    return KernelResult(
        check_id="dashboard_productization_projection",
        inspected=inspected,
        output=(
            "dashboard productization projection passed: production POST /ingest "
            "fails closed when INGEST_SECRET is missing or dev-secret, static/SSE "
            "routes remain outside that guard, hardcoded deploy URL/project/org "
            "literals are rejected with FIRE probes, and bake_dashboard_data_json "
            "round-tripped a source_truth false packet with buildings list while "
            "a mutated source_truth true packet fired RED. "
            f"{seed_observation} "
            "The dashboard IAP "
            "passport pin observed Authorization only when BRICK_DASHBOARD_SA_KEY_PATH "
            "was present, pinned the subprocess surface to openssl dgst -sha256 -sign, "
            "and fired RED when Authorization attachment was removed. "
            "State projection table:\n"
            f"{state_table}\n"
            "A mutated breakdown->running board-state derivation and a mutated "
            "closed-without-boundary derivation both fired RED."
        ),
    )

def _run_read_side_projection_boundary_profile(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "support/checkers/check_profile.py",
            "--repo",
            ".",
            "--profile",
            "read_side_projection_boundary",
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def probe_mutation_red(repo: Path) -> list[str]:
    source = Path(__file__).resolve()
    original = source.read_text(encoding="utf-8")
    needle = "def run_dashboard_productization_projection(repo: Path) -> KernelResult:"
    poisoned = "def run_dashboard_productization_projection_disabled(repo: Path) -> KernelResult:"
    if needle not in original:
        raise ProfileError(
            "dashboard_productization_projection mutation probe could not find entrypoint"
        )

    backup = tempfile.NamedTemporaryFile(
        prefix=".dashboard-productization-projection-check.",
        suffix=".bak",
        dir=source.parent,
        delete=False,
    )
    backup_path = Path(backup.name)
    backup.close()
    shutil.copyfile(source, backup_path)
    try:
        source.write_text(original.replace(needle, poisoned, 1), encoding="utf-8")
        red = _run_read_side_projection_boundary_profile(repo)
        if red.returncode == 0:
            raise ProfileError(
                "dashboard_productization_projection mutation probe did not turn "
                "read_side_projection_boundary profile RED"
            )
    finally:
        shutil.copyfile(backup_path, source)
        backup_path.unlink(missing_ok=True)

    green = _run_read_side_projection_boundary_profile(repo)
    if green.returncode != 0:
        excerpt = "\n".join(green.stdout.splitlines()[-20:])
        raise ProfileError(
            "dashboard_productization_projection mutation probe restored source but "
            f"read_side_projection_boundary remained RED:\n{excerpt}"
        )

    return [
        "dashboard productization projection mutation RED probe passed: disabling "
        "the moved run_dashboard_productization_projection entrypoint made "
        "check_profile.py --profile read_side_projection_boundary exit non-zero, "
        "then restoring the temp-backed self file returned "
        "read_side_projection_boundary to exit 0."
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence checker leaf for dashboard productization projection."
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument(
        "--probe-mutation-red",
        action="store_true",
        help=(
            "temporarily disable this leaf's moved "
            "run_dashboard_productization_projection entrypoint, assert "
            "read_side_projection_boundary profile exits RED, restore from a "
            "temp backup, then assert read_side_projection_boundary GREEN"
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = (
            probe_mutation_red(repo)
            if args.probe_mutation_red
            else [run_dashboard_productization_projection(repo).output]
        )
    except ProfileError as exc:
        print("dashboard productization projection rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
