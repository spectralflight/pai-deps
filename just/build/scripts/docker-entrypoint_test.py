# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import subprocess
import textwrap
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
ENTRYPOINT = ROOT_DIR / "docker" / "entrypoint.sh"


def test_entrypoint_creates_configured_home_for_existing_uid(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    install_args = tmp_path / "install-args.txt"
    build_home = tmp_path / "home" / "paideps"

    _write_executable(fake_bin / "id", "printf '0\n'")
    _write_executable(
        fake_bin / "getent",
        """
        case "$1" in
          group) printf 'existing:x:1234:\n' ;;
          passwd) printf 'existing:x:1234:1234::/existing:/bin/bash\n' ;;
        esac
        """,
    )
    _write_executable(fake_bin / "groupadd", "exit 99")
    _write_executable(fake_bin / "useradd", "exit 99")
    _write_executable(
        fake_bin / "install",
        """
        printf '%s\n' "$@" > "${FAKE_INSTALL_ARGS}"
        destination="${!#}"
        /usr/bin/mkdir -p "${destination}"
        """,
    )
    _write_executable(fake_bin / "gosu", 'shift; exec "$@"')

    result = subprocess.run(
        [str(ENTRYPOINT), "true"],
        env={
            "FAKE_INSTALL_ARGS": str(install_args),
            "HOME": str(tmp_path / "initial-home"),
            "PAI_DEPS_BUILD_GID": "1234",
            "PAI_DEPS_BUILD_HOME": str(build_home),
            "PAI_DEPS_BUILD_UID": "1234",
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        },
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert build_home.is_dir()
    assert install_args.read_text().splitlines() == [
        "-d",
        "-o",
        "1234",
        "-g",
        "1234",
        str(build_home),
    ]


def _write_executable(path: Path, body: str) -> None:
    path.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            set -euo pipefail
            {body}
            """
        )
    )
    path.chmod(0o755)
