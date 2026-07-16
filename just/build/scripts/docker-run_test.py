# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import subprocess
import textwrap
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
DOCKER_RUN_SCRIPT = ROOT_DIR / "just" / "build" / "scripts" / "docker-run.sh"


def test_docker_run_selectively_mounts_user_build_caches(tmp_path: Path) -> None:
    args = _run_with_fake_docker(tmp_path)
    cache_home = tmp_path / "home" / ".cache"

    assert _mounts(args) == [
        f"{ROOT_DIR}:/app",
        f"{cache_home / 'uv'}:/cache/uv",
        f"{cache_home / 'uv-python'}:/cache/uv-python",
        f"{cache_home / 'ccache'}:/cache/ccache",
    ]
    assert _environment(args) >= {
        "UV_CACHE_DIR=/cache/uv",
        "UV_PYTHON_CACHE_DIR=/cache/uv-python",
        "CCACHE_DIR=/cache/ccache",
    }
    assert not any("huggingface" in arg.lower() for arg in args)
    assert "--rm" in args


def test_docker_run_honors_explicit_host_cache_directories(tmp_path: Path) -> None:
    cache_dirs = {
        "UV_CACHE_DIR": tmp_path / "shared-uv",
        "UV_PYTHON_CACHE_DIR": tmp_path / "shared-uv-python",
        "CCACHE_DIR": tmp_path / "shared-ccache",
    }
    args = _run_with_fake_docker(tmp_path, cache_dirs=cache_dirs)

    assert _mounts(args) == [
        f"{ROOT_DIR}:/app",
        f"{cache_dirs['UV_CACHE_DIR']}:/cache/uv",
        f"{cache_dirs['UV_PYTHON_CACHE_DIR']}:/cache/uv-python",
        f"{cache_dirs['CCACHE_DIR']}:/cache/ccache",
    ]
    assert all(path.is_dir() for path in cache_dirs.values())


def test_docker_run_uses_disposable_caches_as_root(tmp_path: Path) -> None:
    args = _run_with_fake_docker(tmp_path, root=True)

    assert _mounts(args) == [
        f"{ROOT_DIR}:/app",
        "/cache/uv",
        "/cache/uv-python",
        "/cache/ccache",
    ]


def _run_with_fake_docker(
    tmp_path: Path,
    *,
    cache_dirs: dict[str, Path] | None = None,
    root: bool = False,
) -> list[str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    args_path = tmp_path / "docker-args.txt"
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail
            if [[ "$1" == "build" ]]; then
                printf 'sha256:test-image\n'
                exit 0
            fi
            [[ "$1" == "run" ]]
            shift
            printf '%s\n' "$@" > "${FAKE_DOCKER_ARGS}"
            """
        )
    )
    fake_docker.chmod(0o755)

    env = {
        "FAKE_DOCKER_ARGS": str(args_path),
        "HOME": str(tmp_path / "home"),
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
    }
    if cache_dirs is not None:
        env.update({name: str(path) for name, path in cache_dirs.items()})

    command = [str(DOCKER_RUN_SCRIPT), "--no-tty"]
    if root:
        command.append("--root")
    command.extend(["--", "true"])
    result = subprocess.run(
        command,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    return args_path.read_text().splitlines()


def _mounts(args: list[str]) -> list[str]:
    return [args[index + 1] for index, arg in enumerate(args) if arg == "-v"]


def _environment(args: list[str]) -> set[str]:
    return {args[index + 1] for index, arg in enumerate(args) if arg == "-e"}
