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


def test_docker_run_mounts_only_the_fixed_output_destination(tmp_path: Path) -> None:
    output_dir = tmp_path / "wheelhouse"
    output_dir.mkdir()

    args = _run_with_fake_docker(tmp_path, output_dir=output_dir)

    assert f"{output_dir}:/pai-deps-output" in _mounts(args)


def test_docker_run_rejects_root_host_identity(tmp_path: Path) -> None:
    result, args_path = _invoke_with_fake_docker(tmp_path, uid=0)

    assert result.returncode != 0
    assert "require a non-root host UID and GID" in result.stderr
    assert not args_path.exists()


def test_docker_run_treats_removed_raw_passthrough_as_container_command(tmp_path: Path) -> None:
    result, args_path = _invoke_with_fake_docker(
        tmp_path,
        raw_arguments=["--run-arg", "--entrypoint", "/bin/bash"],
    )

    assert result.returncode == 0, result.stdout + result.stderr
    args = args_path.read_text().splitlines()
    image_index = args.index("sha256:test-image")
    assert args[image_index + 1 :] == ["--run-arg", "--entrypoint", "/bin/bash"]


def _run_with_fake_docker(
    tmp_path: Path,
    *,
    cache_dirs: dict[str, Path] | None = None,
    output_dir: Path | None = None,
) -> list[str]:
    result, args_path = _invoke_with_fake_docker(tmp_path, cache_dirs=cache_dirs, output_dir=output_dir)

    assert result.returncode == 0, result.stdout + result.stderr
    return args_path.read_text().splitlines()


def _invoke_with_fake_docker(
    tmp_path: Path,
    *,
    cache_dirs: dict[str, Path] | None = None,
    output_dir: Path | None = None,
    uid: int = 1234,
    gid: int = 1234,
    raw_arguments: list[str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
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
    fake_id = fake_bin / "id"
    fake_id.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail
            case "$1" in
              -u) printf '%s\n' "${FAKE_UID}" ;;
              -g) printf '%s\n' "${FAKE_GID}" ;;
              *) exit 2 ;;
            esac
            """
        )
    )
    fake_id.chmod(0o755)

    env = {
        "FAKE_DOCKER_ARGS": str(args_path),
        "FAKE_GID": str(gid),
        "FAKE_UID": str(uid),
        "HOME": str(tmp_path / "home"),
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
    }
    if cache_dirs is not None:
        env.update({name: str(path) for name, path in cache_dirs.items()})

    command = [str(DOCKER_RUN_SCRIPT), "--no-tty"]
    if output_dir is not None:
        command.extend(["--output-dir", str(output_dir)])
    if raw_arguments is None:
        command.extend(["--", "true"])
    else:
        command.extend(raw_arguments)
    result = subprocess.run(
        command,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    return result, args_path


def _mounts(args: list[str]) -> list[str]:
    return [args[index + 1] for index, arg in enumerate(args) if arg == "-v"]


def _environment(args: list[str]) -> set[str]:
    return {args[index + 1] for index, arg in enumerate(args) if arg == "-e"}
