# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Package descriptor discovery for build agents."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomllib

REPO = Path(__file__).resolve().parents[1]
PACKAGES_DIR = REPO / "packages"
DESCRIPTOR_NAME = "pai-package.toml"
VALID_BACKENDS = {"pip-wheel-git", "uv-build"}
VALID_STATUSES = {"maintained", "smoke", "historical", "unknown"}
VALID_GPU_RISKS = {"none", "low", "medium", "high"}
VALID_LICENSE_CONFIDENCES = {"high", "medium", "low", "unknown"}
SYSTEM_PACKAGE_PATTERN = re.compile(r"[a-z0-9][a-z0-9+.-]*(?::[a-z0-9][a-z0-9-]*)?")


@dataclass(frozen=True, slots=True)
class SourceDescriptor:
    url: str = ""
    revision: str = ""
    subdirectory: str = ""


@dataclass(frozen=True, slots=True)
class LicenseReviewDescriptor:
    required: bool = False
    url: str = ""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class LicenseDescriptor:
    expression: str = "NOASSERTION"
    files: tuple[str, ...] = ()
    confidence: str = "unknown"
    notes: str = ""


@dataclass(frozen=True, slots=True)
class BuildDescriptor:
    backend: str
    script: str = "build.sh"
    common_pip_flags: bool = False
    local: bool = False
    requires_torch: bool = True
    prebuild_scripts: tuple[str, ...] = ()
    system_packages: tuple[str, ...] = ()
    revision_overrides: dict[str, str] = field(default_factory=dict)
    env_exports: tuple[str, ...] = ()
    env_defaults: dict[str, str] = field(default_factory=dict)
    source: SourceDescriptor = field(default_factory=SourceDescriptor)


@dataclass(frozen=True, slots=True)
class PackageDescriptor:
    name: str
    project_name: str
    status: str
    upstream: str
    gpu_risk: str
    docs: str
    license: LicenseDescriptor
    license_review: LicenseReviewDescriptor
    directory: Path
    descriptor_path: Path
    build: BuildDescriptor

    @property
    def build_script_path(self) -> Path:
        return self.directory / self.build.script

    @property
    def docs_path(self) -> Path:
        return self.directory / self.docs


def _string_tuple(data: dict[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a list of strings")
    return tuple(value)


def _system_package_tuple(data: dict[str, Any]) -> tuple[str, ...]:
    packages = _string_tuple(data, "system_packages")
    invalid = [package for package in packages if SYSTEM_PACKAGE_PATTERN.fullmatch(package) is None]
    if invalid:
        raise ValueError(f"system_packages contains invalid Debian package names: {invalid!r}")
    return packages


def _string_dict(data: dict[str, Any], key: str) -> dict[str, str]:
    value = data.get(key, {})
    if not isinstance(value, dict) or not all(isinstance(item_key, str) for item_key in value):
        raise ValueError(f"{key} must be a string-keyed table")
    if not all(isinstance(item_value, str) for item_value in value.values()):
        raise ValueError(f"{key} values must be strings")
    return dict(value)


def _require_string(data: dict[str, Any], key: str, *, source: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{source}: missing non-empty string field {key}")
    return value


def load_package_descriptor(descriptor_path: Path) -> PackageDescriptor:
    data = tomllib.loads(descriptor_path.read_text())
    if data.get("schema_version") != 1:
        raise ValueError(f"{descriptor_path}: schema_version must be 1")

    build_data = data.get("build")
    if not isinstance(build_data, dict):
        raise ValueError(f"{descriptor_path}: missing [build] table")
    source_data = build_data.get("source", {})
    if not isinstance(source_data, dict):
        raise ValueError(f"{descriptor_path}: build.source must be a table")
    env_data = build_data.get("env", {})
    if not isinstance(env_data, dict):
        raise ValueError(f"{descriptor_path}: build.env must be a table")
    license_review_data = data.get("license_review", {})
    if not isinstance(license_review_data, dict):
        raise ValueError(f"{descriptor_path}: license_review must be a table")
    license_data = data.get("license", {})
    if not isinstance(license_data, dict):
        raise ValueError(f"{descriptor_path}: license must be a table")

    build = BuildDescriptor(
        backend=_require_string(build_data, "backend", source=descriptor_path),
        script=str(build_data.get("script", "build.sh")),
        common_pip_flags=bool(build_data.get("common_pip_flags", False)),
        local=bool(build_data.get("local", False)),
        requires_torch=bool(build_data.get("requires_torch", True)),
        prebuild_scripts=_string_tuple(build_data, "prebuild_scripts"),
        system_packages=_system_package_tuple(build_data),
        revision_overrides=_string_dict(build_data, "revision_overrides"),
        env_exports=_string_tuple(env_data, "exports"),
        env_defaults=_string_dict(env_data, "defaults"),
        source=SourceDescriptor(
            url=str(source_data.get("url", "")),
            revision=str(source_data.get("revision", "")),
            subdirectory=str(source_data.get("subdirectory", "")),
        ),
    )
    return PackageDescriptor(
        name=_require_string(data, "name", source=descriptor_path),
        project_name=str(data.get("project_name") or data.get("name")),
        status=_require_string(data, "status", source=descriptor_path),
        upstream=_require_string(data, "upstream", source=descriptor_path),
        gpu_risk=_require_string(data, "gpu_risk", source=descriptor_path),
        docs=str(data.get("docs", "agents/build-notes.md")),
        license=LicenseDescriptor(
            expression=str(license_data.get("expression", "NOASSERTION")),
            files=_string_tuple(license_data, "files"),
            confidence=str(license_data.get("confidence", "unknown")),
            notes=str(license_data.get("notes", "")),
        ),
        license_review=LicenseReviewDescriptor(
            required=bool(license_review_data.get("required", False)),
            url=str(license_review_data.get("url", "")),
            notes=str(license_review_data.get("notes", "")),
        ),
        directory=descriptor_path.parent,
        descriptor_path=descriptor_path,
        build=build,
    )


def discover_package_descriptors(packages_dir: Path = PACKAGES_DIR) -> list[PackageDescriptor]:
    descriptors = [load_package_descriptor(path) for path in packages_dir.glob(f"*/{DESCRIPTOR_NAME}")]
    return sorted(descriptors, key=lambda descriptor: descriptor.name)
