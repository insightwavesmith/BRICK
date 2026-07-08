"""Building-plan graph kernel-check leaf.

Pure relocation sibling of kernel_checks. Support checker mechanics only: it
observes building map graph packets and Building Plan boundary shape; it owns
no axis crossing, decides no Movement, and judges no success or quality.
"""

from __future__ import annotations

import argparse
import importlib
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from brick_protocol.support.checkers.lib.yaml_subset import KernelResult, ProfileError, to_posix


def run_building_map_graph(repo: Path) -> KernelResult:
    module = importlib.import_module("brick_protocol.support.checkers.check_building_map_graph")
    map_paths = sorted(repo.glob("project/*/buildings/*/work/building-map.json"))
    if not map_paths:
        return KernelResult(
            check_id="building_map_graph",
            inspected=0,
            output="building map graph skipped: no project/*/buildings/*/work/building-map.json maps present.",
        )
    all_violations: list[str] = []
    historical = 0
    for map_path in map_paths:
        _, violations, historical_map = module.check_one(map_path, fixture_mode=False)
        if historical_map:
            historical += 1
        all_violations.extend(violations)
    if all_violations:
        detail = "\n".join(f"- {violation}" for violation in all_violations)
        raise ProfileError(f"kernel check building_map_graph rejected evidence:\n{detail}")
    return KernelResult(
        check_id="building_map_graph",
        inspected=len(map_paths),
        output=(
            "building map graph passed: "
            f"{len(map_paths)} map(s) inspected, {historical} historical support map(s) preserved."
        ),
    )


def run_building_plans_boundary_sweep(repo: Path) -> KernelResult:
    """Global building-plan boundary sweep (checker consolidation, pass-1).

    REHOME target: the per-profile ``building_plan_boundary`` pins (bar_v2,
    real_route_repair, provider_json_return_smoke, current_context_prune, ...)
    each pinned ONE frozen/live plan because no global walk existed. This sweep
    runs the SAME ``validate_building_plan_boundary`` over EVERY linear and
    graph plan in brick_protocol/brick/building_plans/, so those single-sourced per-plan
    structural guards survive as one general kernel-check and the per-profile
    pins can retire.

    Stepless / non-Building-plan fixtures are skipped; their count is reported,
    never silently absorbed. A real boundary violation on any linear or graph
    plan raises ProfileError -> --all RED.

    HARDENED (guard-before-retire): when the linear yaml-subset parser fails on a
    plan, fall back to PyYAML (yaml.safe_load). If PyYAML yields a dict with a
    non-empty ``steps`` list or ``plan_shape: graph``, the plan is a real
    Building Plan that the subset parser merely could not read, so it is
    validated via the SAME ``validate_building_plan_boundary`` (no silent skip).
    Only truly stepless / non-Building-plan fixtures are skipped. A now-included
    plan that genuinely fails validation is surfaced (--all RED), never hidden.
    The number of PyYAML-recovered plans is reported separately.
    """
    plans_dir = repo / "brick_protocol" / "brick" / "building_plans"
    if not plans_dir.is_dir():
        raise ProfileError("brick_protocol/brick/building_plans must exist for the boundary sweep")
    import yaml
    from brick_protocol.support.checkers.lib.yaml_subset import load_yaml_subset_file
    from brick_protocol.support.checkers.lib.rule_runners import (
        validate_building_plan_boundary,
        _admitted_agent_object_refs,
    )

    admitted = _admitted_agent_object_refs(repo)
    linear_validated = 0
    graph_validated = 0
    skipped = 0
    pyyaml_recovered = 0
    for path in sorted(plans_dir.glob("*.yaml")):
        rel = to_posix(path.relative_to(repo))
        try:
            plan = load_yaml_subset_file(repo, rel)
        except Exception:
            # Subset parser could not read it. Fall back to PyYAML: a real LINEAR
            # plan (dict with non-empty steps) must still be covered, not skipped.
            recovered = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(recovered, Mapping):
                skipped += 1
                continue
            recovered_steps = recovered.get("steps")
            recovered_is_linear = isinstance(recovered_steps, list) and bool(recovered_steps)
            recovered_is_graph = recovered.get("plan_shape") == "graph"
            if not (recovered_is_linear or recovered_is_graph):
                skipped += 1  # stepless / non-Building-plan fixture
                continue
            # Real linear/graph plan the subset parser missed; validate it
            # (surface any genuine failure rather than hiding it). This is
            # STRUCTURAL validation of historical plans, so retired write-adapter
            # refs are tolerated here (adapter activeness is enforced at run time,
            # not in the boundary sweep).
            validate_building_plan_boundary(
                recovered, rel, admitted, repo, allow_retired_write_adapter_refs=True
            )
            if recovered_is_graph:
                graph_validated += 1
            else:
                linear_validated += 1
            pyyaml_recovered += 1
            continue
        steps = plan.get("steps")
        is_linear = isinstance(steps, list) and bool(steps)
        is_graph = plan.get("plan_shape") == "graph"
        if not (is_linear or is_graph):
            skipped += 1  # stepless / non-Building-plan fixture
            continue
        # Reuses the EXACT per-profile boundary validator; a violation raises
        # ProfileError, which fails the check (no swallowing of real failures).
        # Structural sweep over historical plans: retired write-adapter refs are
        # tolerated here (adapter activeness is enforced at run time, not here).
        validate_building_plan_boundary(
            plan, rel, admitted, repo, allow_retired_write_adapter_refs=True
        )
        if is_graph:
            graph_validated += 1
        else:
            linear_validated += 1
    validated = linear_validated + graph_validated
    return KernelResult(
        check_id="building_plans_boundary_sweep",
        inspected=validated,
        output=(
            f"building plans boundary sweep passed: {validated} building "
            f"plan(s) validated (Brick owner_axis + plan_ref + non-empty steps + "
            f"declared-plan validation + per-step rows; {linear_validated} linear, "
            f"{graph_validated} graph via declared graph projection; {pyyaml_recovered} "
            f"PyYAML-recovered from subset-parse failure); {skipped} stepless / "
            f"non-Building-plan fixture(s) skipped."
        ),
    )


def _run_core_profile(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "brick_protocol/support/checkers/check_profile.py",
            "--repo",
            ".",
            "--profile",
            "core",
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
    needle = "def run_building_map_graph(repo: Path) -> KernelResult:"
    poisoned = "def run_building_map_graph_disabled(repo: Path) -> KernelResult:"
    if needle not in original:
        raise ProfileError("building_plan_graph mutation probe could not find map graph entrypoint")

    backup = tempfile.NamedTemporaryFile(
        prefix=".building-plan-graph-check.",
        suffix=".bak",
        dir=source.parent,
        delete=False,
    )
    backup_path = Path(backup.name)
    backup.close()
    shutil.copyfile(source, backup_path)
    try:
        source.write_text(original.replace(needle, poisoned, 1), encoding="utf-8")
        red = _run_core_profile(repo)
        if red.returncode == 0:
            raise ProfileError(
                "building_plan_graph mutation probe did not turn core profile RED"
            )
    finally:
        shutil.copyfile(backup_path, source)
        backup_path.unlink(missing_ok=True)

    green = _run_core_profile(repo)
    if green.returncode != 0:
        excerpt = "\n".join(green.stdout.splitlines()[-20:])
        raise ProfileError(
            "building_plan_graph mutation probe restored source but core profile "
            f"remained RED:\n{excerpt}"
        )

    return [
        "building-plan graph mutation RED probe passed: disabling the moved "
        "run_building_map_graph entrypoint made check_profile.py --profile core "
        "exit non-zero, then restoring the temp-backed self file returned core "
        "to exit 0."
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence checker leaf for building-plan graph checks."
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument(
        "--probe-mutation-red",
        action="store_true",
        help=(
            "temporarily disable this leaf's moved run_building_map_graph entrypoint, "
            "assert core profile exits RED, restore from a temp backup, then assert "
            "core GREEN"
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
            else [
                run_building_map_graph(repo).output,
                run_building_plans_boundary_sweep(repo).output,
            ]
        )
    except ProfileError as exc:
        print("building-plan graph check rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
