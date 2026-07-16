#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Check package descriptors against package-local build scripts."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from pai_deps.package_metadata import PackageDescriptor, discover_package_descriptors

REPO = Path(__file__).resolve().parents[3]
BUILD_HELPERS = REPO / "just/build/scripts/build-helpers.sh"
COMMON_PIP_WHEEL_HELPER_TOKENS = [
    "pip wheel",
    "--no-deps",
    "--no-build-isolation",
    "--check-build-dependencies",
    "--wheel-dir",
    '"$@"',
]
UV_BUILD_HELPER_TOKENS = ["uv build", "--wheel", "-o", '"$@"']
LICENSE_CONFIRMATION_ENV_VARS = ("I_CONFIRM_THIS_IS_NOT_A_LICENSE_VIOLATION",)
PRIVILEGED_BUILD_COMMAND = re.compile(r"\b(?:apt|apt-get|chown|dpkg|sudo)\b")
SYSTEM_PREFIX_WRITE = re.compile(
    r"(?:\b(?:cp|install|ln|mkdir|mv|rm|tee|touch)\b[^\n]*|>{1,2}\s*)(?:/etc|/opt|/usr)(?:/|\s|$)",
    re.MULTILINE,
)


def _script_text(package: PackageDescriptor) -> str:
    parts = [package.build_script_path.read_text()]
    for script in package.build.prebuild_scripts:
        parts.append((package.directory / script).read_text())
    return "\n".join(parts)


def _executable_shell_text(source: str) -> str:
    return "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))


def _check_contains(source: str, token: str, *, label: str) -> list[str]:
    if token not in source:
        return [f"{label}: missing {token!r}"]
    return []


def _check_build_helpers() -> list[str]:
    errors: list[str] = []
    text = BUILD_HELPERS.read_text()
    for token in COMMON_PIP_WHEEL_HELPER_TOKENS:
        errors.extend(_check_contains(text, token, label=BUILD_HELPERS.relative_to(REPO).as_posix()))
    for token in UV_BUILD_HELPER_TOKENS:
        errors.extend(_check_contains(text, token, label=BUILD_HELPERS.relative_to(REPO).as_posix()))
    return errors


def _check_package(package: PackageDescriptor) -> list[str]:
    errors: list[str] = []
    text = _script_text(package)
    label = package.descriptor_path.relative_to(package.descriptor_path.parents[2]).as_posix()

    match package.build.backend:
        case "pip-wheel-git":
            if package.build.common_pip_flags:
                errors.extend(_check_contains(text, "pai_deps_pip_wheel", label=label))
            errors.extend(_check_contains(text, package.build.source.url, label=label))
            if package.build.source.subdirectory:
                errors.extend(_check_contains(text, f"#subdirectory={package.build.source.subdirectory}", label=label))
        case "uv-build":
            errors.extend(_check_contains(text, "pai_deps_uv_build_wheel", label=label))
        case _:
            errors.append(f"{label}: unsupported backend {package.build.backend!r}")

    for version, revision in package.build.revision_overrides.items():
        errors.extend(_check_contains(text, version, label=label))
        errors.extend(_check_contains(text, revision, label=label))
    for env_name in sorted(set(package.build.env_exports) | set(package.build.env_defaults)):
        errors.extend(_check_contains(text, env_name, label=label))
    executable_text = _executable_shell_text(text)
    if PRIVILEGED_BUILD_COMMAND.search(executable_text):
        errors.append(f"{label}: package build scripts must not run privileged system commands")
    if SYSTEM_PREFIX_WRITE.search(executable_text):
        errors.append(f"{label}: package build scripts must not write to system prefixes")
    for script in package.build.prebuild_scripts:
        if not (package.directory / script).is_file():
            errors.append(f"{label}: missing prebuild script {script}")
        errors.extend(_check_contains(package.build_script_path.read_text(), script, label=label))
    if "cat >setup.py" in text:
        errors.extend(_check_contains(text, "pai_deps_copy_license_files_py", label=label))
        errors.extend(_check_contains(text, "license_files=", label=label))
    for env_name in LICENSE_CONFIRMATION_ENV_VARS:
        if env_name in text:
            if not package.license_review.required:
                errors.append(f"{label}: {env_name} requires [license_review].required = true")
            if not package.license_review.url:
                errors.append(f"{label}: {env_name} requires license_review.url")
            if not package.license_review.notes:
                errors.append(f"{label}: {env_name} requires license_review.notes")
    return errors


def check_packages(packages: list[PackageDescriptor] | None = None) -> list[str]:
    errors: list[str] = _check_build_helpers() if packages is None else []
    for package in packages or discover_package_descriptors():
        errors.extend(_check_package(package))
    return errors


def main() -> int:
    errors = check_packages()
    if errors:
        for error in errors:
            print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
