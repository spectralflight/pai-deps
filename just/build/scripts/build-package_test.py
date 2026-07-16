# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import subprocess
import textwrap
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
BUILD_SCRIPT = ROOT_DIR / "just" / "build" / "scripts" / "build-package.sh"


def _write_fake_build_script(work_dir: Path) -> Path:
    scripts_dir = work_dir / "just" / "build" / "scripts"
    scripts_dir.mkdir(parents=True)
    build_script = scripts_dir / "build-package.sh"
    build_script.write_text(BUILD_SCRIPT.read_text())
    build_script.chmod(0o755)
    fake_build = scripts_dir / "build-package-inner.sh"
    fake_build.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail
            env | sort > "${OUTPUT_DIR}/env.txt"
            printf "%s\\n" "$@" > "${OUTPUT_DIR}/args.txt"
            printf "fake wheel" > "${OUTPUT_DIR}/cosmos_dummy-0.1.0+cu128.torch29-py3-none-any.whl"
            """
        )
    )
    fake_build.chmod(0o755)
    return build_script


def _run_build_script(
    work_dir: Path,
    env_file: Path | None = None,
    inline_env: str | None = None,
) -> subprocess.CompletedProcess[str]:
    build_script = _write_fake_build_script(work_dir)
    env = {
        "CUDA_VERSION": "12.8",
        "HOST_ONLY_VARIABLE": "must-not-leak",
        "HOME": str(work_dir / "home"),
        "NATTEN_N_WORKERS": "99",
        "PATH": os.environ["PATH"],
        "PYTHONPATH": str(ROOT_DIR),
        "UV_PYTHON_CACHE_DIR": str(work_dir / "uv-python-cache"),
        "USER": "tester",
    }
    if env_file is not None:
        env["PAI_DEPS_BUILD_ENV_FILE"] = str(env_file)
    if inline_env is not None:
        env["PAI_DEPS_BUILD_ENV"] = inline_env
    return subprocess.run(
        [
            str(build_script),
            "cosmos-dummy",
            "0.1.0",
            "3.12",
            "2.9",
            "build",
            "--config-settings=--dummy",
        ],
        cwd=work_dir,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )


def _read_build_env(work_dir: Path) -> str:
    env_files = list((work_dir / "build").glob("*/env.txt"))
    assert len(env_files) == 1
    return env_files[0].read_text()


def test_build_script_loads_explicit_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / "natten.env"
    env_file.write_text(
        textwrap.dedent(
            """\
            # Small local smoke settings.
            MAX_JOBS=1
            export NATTEN_N_WORKERS="2"
            TORCH_CUDA_ARCH_LIST='9.0'
            NATTEN_CUDA_ARCH=9.0
            SPACED_VALUE="hello world"
            """
        )
    )

    result = _run_build_script(tmp_path, env_file)

    assert result.returncode == 0, result.stdout + result.stderr
    build_env = _read_build_env(tmp_path)
    assert "MAX_JOBS=1\n" in build_env
    assert "NATTEN_N_WORKERS=2\n" in build_env
    assert "NATTEN_N_WORKERS=99\n" not in build_env
    assert "TORCH_CUDA_ARCH_LIST=9.0\n" in build_env
    assert "NATTEN_CUDA_ARCH=9.0\n" in build_env
    assert "SPACED_VALUE=hello world\n" in build_env
    assert f"UV_PYTHON_CACHE_DIR={tmp_path / 'uv-python-cache'}\n" in build_env
    assert "HOST_ONLY_VARIABLE=must-not-leak\n" not in build_env
    assert "CUDA_VERSION=12.8\n" not in build_env


def test_build_script_writes_wheel_sidecars(tmp_path: Path) -> None:
    result = _run_build_script(tmp_path, inline_env="MAX_JOBS=1 NATTEN_N_WORKERS=2")

    assert result.returncode == 0, result.stdout + result.stderr
    wheel = next((tmp_path / "build").glob("*/cosmos_dummy-0.1.0+cu128.torch29-py3-none-any.whl"))
    sidecar = Path(f"{wheel}.build.json")
    build_log = Path(f"{wheel}.build.log")
    assert sidecar.exists()
    assert build_log.exists()
    provenance = json.loads(sidecar.read_text())
    assert provenance["package"] == "cosmos-dummy"
    assert provenance["build_env"] == {"MAX_JOBS": "1", "NATTEN_N_WORKERS": "2"}
    assert provenance["wheel"]["filename"] == wheel.name


def test_build_script_loads_inline_build_env(tmp_path: Path) -> None:
    result = _run_build_script(
        tmp_path,
        inline_env='MAX_JOBS=1 NATTEN_N_WORKERS="2" TORCH_CUDA_ARCH_LIST=9.0',
    )

    assert result.returncode == 0, result.stdout + result.stderr
    build_env = _read_build_env(tmp_path)
    assert "MAX_JOBS=1\n" in build_env
    assert "NATTEN_N_WORKERS=2\n" in build_env
    assert "TORCH_CUDA_ARCH_LIST=9.0\n" in build_env
    assert "NATTEN_N_WORKERS=99\n" not in build_env


def test_build_script_rejects_reserved_env_file_variables(tmp_path: Path) -> None:
    env_file = tmp_path / "bad.env"
    env_file.write_text("PACKAGE_NAME=other\n")

    result = _run_build_script(tmp_path, env_file)

    assert result.returncode != 0
    assert "PACKAGE_NAME is controlled by just/build/scripts/build-package.sh" in result.stderr
    assert not (tmp_path / "build").exists()


def test_build_script_rejects_reserved_inline_env_variables(tmp_path: Path) -> None:
    result = _run_build_script(tmp_path, inline_env="PACKAGE_NAME=other")

    assert result.returncode != 0
    assert "PACKAGE_NAME is controlled by just/build/scripts/build-package.sh" in result.stderr
    assert not (tmp_path / "build").exists()
