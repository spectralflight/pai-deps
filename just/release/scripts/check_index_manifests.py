# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Check stable index manifests for append-only release references."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

from pai_deps.index_manifest import IndexManifest, load_index_manifest_text


@dataclass(frozen=True)
class ManifestError:
    path: str
    message: str


def _manifest_path_index_name(path: str) -> str:
    return Path(path).parent.name


def _load_manifest_from_text(path: str, text: str) -> IndexManifest:
    manifest = load_index_manifest_text(text, source=path)
    expected_index_name = _manifest_path_index_name(path)
    if manifest.index_name != expected_index_name:
        raise ValueError(f"{path} index_name must match its directory name: {expected_index_name}")
    return manifest


def _git_manifest_paths(ref: str) -> set[str]:
    cmd = ["git", "ls-tree", "-r", "--name-only", ref, "--", "indices"]
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
    return {path for path in result.stdout.splitlines() if path.endswith("/manifest.json")}


def _worktree_manifest_paths(indices_dir: Path = Path("indices")) -> set[str]:
    return {str(path) for path in indices_dir.glob("*/manifest.json")}


def _git_show(ref: str, path: str) -> str | None:
    cmd = ["git", "show", f"{ref}:{path}"]
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return None
    return result.stdout


def check_manifest_change(
    path: str,
    *,
    old_text: str | None,
    new_text: str | None,
) -> list[ManifestError]:
    errors: list[ManifestError] = []
    try:
        old_manifest = _load_manifest_from_text(path, old_text) if old_text is not None else None
    except ValueError as exc:
        return [ManifestError(path=path, message=str(exc))]
    try:
        new_manifest = _load_manifest_from_text(path, new_text) if new_text is not None else None
    except ValueError as exc:
        return [ManifestError(path=path, message=str(exc))]

    if old_manifest is None:
        return errors

    if old_manifest.stability != "stable":
        return errors

    if new_manifest is None:
        return [ManifestError(path=path, message="stable manifest was deleted")]

    if new_manifest.stability != "stable":
        errors.append(ManifestError(path=path, message="stable manifest cannot become unstable"))

    if new_manifest.default_repo != old_manifest.default_repo:
        errors.append(
            ManifestError(
                path=path,
                message=(
                    "stable manifest default_repo cannot change "
                    f"from {old_manifest.default_repo} to {new_manifest.default_repo}"
                ),
            )
        )

    old_releases = set(old_manifest.releases)
    new_releases = set(new_manifest.releases)
    removed_releases = sorted(old_releases - new_releases)
    for release in removed_releases:
        errors.append(
            ManifestError(
                path=path,
                message=f"stable manifest removed release {release.repo} {release.tag}",
            )
        )
    return errors


def check_manifests_against_base(base: str) -> list[ManifestError]:
    paths = _git_manifest_paths(base) | _worktree_manifest_paths()
    errors: list[ManifestError] = []
    for path in sorted(paths):
        old_text = _git_show(base, path)
        new_path = Path(path)
        new_text = new_path.read_text() if new_path.exists() else None
        errors.extend(check_manifest_change(path, old_text=old_text, new_text=new_text))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Git ref to compare against, such as origin/main.")
    args = parser.parse_args()

    errors = check_manifests_against_base(args.base)
    if not errors:
        return 0

    print("Stable index manifests are append-only. Forbidden changes:")
    for error in errors:
        print(f"  {error.path}: {error.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
