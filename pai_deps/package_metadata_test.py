# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from pai_deps.package_metadata import discover_package_descriptors, load_package_descriptor


def test_discovers_repository_packages() -> None:
    packages = discover_package_descriptors()

    assert [package.name for package in packages] == sorted(package.name for package in packages)
    assert {package.name for package in packages} >= {"cosmos-dummy", "natten"}
    assert all(package.descriptor_path.name == "pai-package.toml" for package in packages)


def test_loads_descriptor_defaults(tmp_path: Path) -> None:
    package_dir = tmp_path / "sample"
    package_dir.mkdir()
    descriptor = package_dir / "pai-package.toml"
    descriptor.write_text(
        """
schema_version = 1
name = "sample"
status = "smoke"
upstream = "local"
gpu_risk = "none"

[build]
backend = "uv-build"
"""
    )

    package = load_package_descriptor(descriptor)

    assert package.name == "sample"
    assert package.project_name == "sample"
    assert package.build.script == "build.sh"
    assert package.build.requires_torch is True
    assert package.build.system_packages == ()
    assert package.docs == "agents/build-notes.md"
    assert package.license.expression == "NOASSERTION"


def test_loads_license_descriptor(tmp_path: Path) -> None:
    package_dir = tmp_path / "sample"
    package_dir.mkdir()
    descriptor = package_dir / "pai-package.toml"
    descriptor.write_text(
        """
schema_version = 1
name = "sample"
status = "smoke"
upstream = "https://example.test/sample"
gpu_risk = "none"

[license]
expression = "Apache-2.0"
files = ["LICENSE"]
confidence = "high"
notes = "Synthetic test package."

[build]
backend = "uv-build"
"""
    )

    package = load_package_descriptor(descriptor)

    assert package.license.expression == "Apache-2.0"
    assert package.license.files == ("LICENSE",)
    assert package.license.confidence == "high"


def test_loads_system_packages(tmp_path: Path) -> None:
    descriptor = _write_descriptor(
        tmp_path,
        'system_packages = ["python3-dev", "libavcodec-dev:amd64"]',
    )

    package = load_package_descriptor(descriptor)

    assert package.build.system_packages == ("python3-dev", "libavcodec-dev:amd64")


def test_rejects_unsafe_system_package_name(tmp_path: Path) -> None:
    descriptor = _write_descriptor(tmp_path, 'system_packages = ["python3-dev;whoami"]')

    try:
        load_package_descriptor(descriptor)
    except ValueError as error:
        assert "invalid Debian package names" in str(error)
    else:
        raise AssertionError("unsafe system package name was accepted")


def _write_descriptor(tmp_path: Path, build_fields: str) -> Path:
    package_dir = tmp_path / "sample"
    package_dir.mkdir()
    descriptor = package_dir / "pai-package.toml"
    descriptor.write_text(
        f"""
schema_version = 1
name = "sample"
status = "smoke"
upstream = "local"
gpu_risk = "none"

[build]
backend = "uv-build"
{build_fields}
"""
    )
    return descriptor
