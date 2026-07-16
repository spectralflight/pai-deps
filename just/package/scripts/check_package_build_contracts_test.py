# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import importlib.util
import sys
from pathlib import Path

from pai_deps.package_metadata import discover_package_descriptors


def _load_check_package_build_contracts():
    module_path = Path(__file__).with_name("check_package_build_contracts.py")
    spec = importlib.util.spec_from_file_location("check_package_build_contracts", module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


check_package_build_contracts = _load_check_package_build_contracts()


def test_repository_package_contracts_match_build_scripts() -> None:
    assert check_package_build_contracts.check_packages() == []


def test_detects_missing_source_url(tmp_path: Path) -> None:
    package_dir = tmp_path / "pkg"
    package_dir.mkdir()
    (package_dir / "pai-package.toml").write_text(
        """
schema_version = 1
name = "pkg"
status = "smoke"
upstream = "https://example.invalid/pkg"
gpu_risk = "none"

[build]
backend = "pip-wheel-git"
script = "build.sh"
common_pip_flags = true

[build.source]
url = "https://example.invalid/pkg.git"
revision = "v{package_version}"
"""
    )
    (package_dir / "build.sh").write_text('pai_deps_pip_wheel "$@"\n')

    packages = discover_package_descriptors(tmp_path)

    errors = check_package_build_contracts.check_packages(packages)

    assert any("https://example.invalid/pkg.git" in error for error in errors)


def test_detects_generated_setup_without_license_files(tmp_path: Path) -> None:
    package_dir = tmp_path / "pkg"
    package_dir.mkdir()
    (package_dir / "pai-package.toml").write_text(
        """
schema_version = 1
name = "pkg"
status = "smoke"
upstream = "https://example.invalid/pkg"
gpu_risk = "none"

[build]
backend = "pip-wheel-git"
script = "build.sh"
common_pip_flags = true

[build.source]
url = "https://example.invalid/pkg.git"
revision = "v{package_version}"
"""
    )
    (package_dir / "build.sh").write_text(
        'git clone https://example.invalid/pkg.git src\ncat >setup.py <<EOF\nsetup()\nEOF\npai_deps_pip_wheel "$@"\n'
    )

    packages = discover_package_descriptors(tmp_path)

    errors = check_package_build_contracts.check_packages(packages)

    assert any("pai_deps_copy_license_files_py" in error for error in errors)
    assert any("license_files=" in error for error in errors)


def test_detects_privileged_package_build_command(tmp_path: Path) -> None:
    package_dir = tmp_path / "pkg"
    package_dir.mkdir()
    (package_dir / "pai-package.toml").write_text(
        """
schema_version = 1
name = "pkg"
status = "smoke"
upstream = "https://example.invalid/pkg"
gpu_risk = "none"

[build]
backend = "uv-build"
script = "build.sh"
system_packages = ["python3-dev"]
"""
    )
    (package_dir / "build.sh").write_text('apt-get install python3-dev\npai_deps_uv_build_wheel "$@"\n')

    packages = discover_package_descriptors(tmp_path)

    errors = check_package_build_contracts.check_packages(packages)

    assert any("must not run privileged system commands" in error for error in errors)


def test_detects_package_build_write_to_system_prefix(tmp_path: Path) -> None:
    package_dir = tmp_path / "pkg"
    package_dir.mkdir()
    (package_dir / "pai-package.toml").write_text(
        """
schema_version = 1
name = "pkg"
status = "smoke"
upstream = "https://example.invalid/pkg"
gpu_risk = "none"

[build]
backend = "uv-build"
script = "build.sh"
"""
    )
    (package_dir / "build.sh").write_text(
        'ln -sf build/libpkg.so /usr/local/lib/libpkg.so\npai_deps_uv_build_wheel "$@"\n'
    )

    packages = discover_package_descriptors(tmp_path)

    errors = check_package_build_contracts.check_packages(packages)

    assert any("must not write to system prefixes" in error for error in errors)


def test_detects_license_confirmation_without_review_metadata(tmp_path: Path) -> None:
    package_dir = tmp_path / "pkg"
    package_dir.mkdir()
    (package_dir / "pai-package.toml").write_text(
        """
schema_version = 1
name = "pkg"
status = "smoke"
upstream = "https://example.invalid/pkg"
gpu_risk = "none"

[build]
backend = "pip-wheel-git"
script = "build.sh"
common_pip_flags = true

[build.source]
url = "https://example.invalid/pkg.git"
revision = "v{package_version}"
"""
    )
    (package_dir / "build.sh").write_text(
        "export I_CONFIRM_THIS_IS_NOT_A_LICENSE_VIOLATION=1\n"
        'pai_deps_pip_wheel "git+https://example.invalid/pkg.git@v1.0.0" "$@"\n'
    )

    packages = discover_package_descriptors(tmp_path)

    errors = check_package_build_contracts.check_packages(packages)

    assert any("[license_review].required" in error for error in errors)
    assert any("license_review.url" in error for error in errors)
    assert any("license_review.notes" in error for error in errors)
