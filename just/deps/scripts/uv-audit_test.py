# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
AUDIT_SCRIPT = ROOT_DIR / "just" / "deps" / "scripts" / "uv-audit.sh"


def test_audit_applies_repository_allowlist_to_every_project(tmp_path: Path) -> None:
    calls = _run_audit(tmp_path)

    assert calls == [
        "audit --preview-features audit-command --frozen --ignore PYSEC-2026-3447",
        "audit --project packages/example --preview-features audit-command --frozen --ignore PYSEC-2026-3447",
    ]


def test_strict_audit_bypasses_repository_allowlist(tmp_path: Path) -> None:
    calls = _run_audit(tmp_path, strict=True)

    assert calls == [
        "audit --preview-features audit-command --frozen --no-config",
        "audit --project packages/example --preview-features audit-command --frozen --no-config",
    ]


def _run_audit(tmp_path: Path, *, strict: bool = False) -> list[str]:
    package_dir = tmp_path / "packages" / "example"
    package_dir.mkdir(parents=True)
    (package_dir / "pyproject.toml").write_text("[project]\nname = 'example'\nversion = '0'\n")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls_path = tmp_path / "uv-calls.txt"
    fake_uv = fake_bin / "uv"
    fake_uv.write_text('#!/usr/bin/env bash\nset -euo pipefail\nprintf \'%s\\n\' "$*" >> "${UV_AUDIT_CALLS}"\n')
    fake_uv.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}:{env['PATH']}",
            "PAI_DEPS_AUDIT_STRICT": "1" if strict else "0",
            "UV_AUDIT_CALLS": str(calls_path),
        }
    )
    result = subprocess.run(
        [str(AUDIT_SCRIPT), "--frozen"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    return calls_path.read_text().splitlines()
