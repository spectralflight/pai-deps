#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Inspect package build metadata from package-local descriptors."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pai_deps.package_metadata import PackageDescriptor, discover_package_descriptors

REPO = Path(__file__).resolve().parents[2]


def _descriptor_to_dict(package: PackageDescriptor) -> dict[str, object]:
    return {
        "name": package.name,
        "project_name": package.project_name,
        "status": package.status,
        "directory": package.directory.relative_to(REPO).as_posix(),
        "descriptor": package.descriptor_path.relative_to(REPO).as_posix(),
        "build_script": package.build_script_path.relative_to(REPO).as_posix(),
        "docs": package.docs_path.relative_to(REPO).as_posix(),
        "upstream": package.upstream,
        "gpu_risk": package.gpu_risk,
        "license_review": {
            "required": package.license_review.required,
            "url": package.license_review.url,
            "notes": package.license_review.notes,
        },
        "build": {
            "backend": package.build.backend,
            "requires_torch": package.build.requires_torch,
            "source": {
                "url": package.build.source.url,
                "revision": package.build.source.revision,
                "subdirectory": package.build.source.subdirectory,
            },
            "revision_overrides": package.build.revision_overrides,
            "env_exports": list(package.build.env_exports),
            "env_defaults": package.build.env_defaults,
            "prebuild_scripts": list(package.build.prebuild_scripts),
            "system_packages": list(package.build.system_packages),
        },
    }


def _load_packages() -> list[PackageDescriptor]:
    return discover_package_descriptors()


def _find_package(name: str) -> PackageDescriptor:
    for package in _load_packages():
        if package.name == name:
            return package
    raise KeyError(name)


def _print_table(packages: list[PackageDescriptor]) -> None:
    rows = [
        (
            package.name,
            package.status,
            package.directory.relative_to(REPO).as_posix(),
            package.upstream,
        )
        for package in packages
    ]
    widths = [
        max(len(row[index]) for row in rows + [("name", "status", "directory", "upstream")]) for index in range(4)
    ]
    print(f"{'name':<{widths[0]}}  {'status':<{widths[1]}}  {'directory':<{widths[2]}}  upstream")
    print(f"{'-' * widths[0]}  {'-' * widths[1]}  {'-' * widths[2]}  {'-' * widths[3]}")
    for row in rows:
        print(f"{row[0]:<{widths[0]}}  {row[1]:<{widths[1]}}  {row[2]:<{widths[2]}}  {row[3]}")


def list_packages(*, json_output: bool) -> int:
    packages = _load_packages()
    if json_output:
        print(json.dumps([_descriptor_to_dict(package) for package in packages], indent=2, sort_keys=True))
    else:
        _print_table(packages)
    return 0


def show_package(name: str, *, json_output: bool) -> int:
    try:
        package = _find_package(name)
    except KeyError:
        print(f"Error: unknown package: {name}", file=sys.stderr)
        return 1
    if json_output:
        print(json.dumps(_descriptor_to_dict(package), indent=2, sort_keys=True))
        return 0

    print(f"name: {package.name}")
    print(f"status: {package.status}")
    print(f"directory: {package.directory.relative_to(REPO).as_posix()}")
    print(f"project_name: {package.project_name}")
    print(f"descriptor: {package.descriptor_path.relative_to(REPO).as_posix()}")
    print(f"build_script: {package.build_script_path.relative_to(REPO).as_posix()}")
    print(f"docs: {package.docs_path.relative_to(REPO).as_posix()}")
    print(f"upstream: {package.upstream}")
    print(f"gpu_risk: {package.gpu_risk}")
    print(f"license_review_required: {package.license_review.required}")
    if package.license_review.url:
        print(f"license_review_url: {package.license_review.url}")
    print(f"build_backend: {package.build.backend}")
    print(f"requires_torch: {package.build.requires_torch}")
    if package.build.source.url:
        print(f"source_url: {package.build.source.url}")
    print(f"docs_exists: {package.docs_path.is_file()}")
    return 0


def print_system_packages(name: str) -> int:
    try:
        package = _find_package(name)
    except KeyError:
        print(f"Error: unknown package: {name}", file=sys.stderr)
        return 1
    print(" ".join(package.build.system_packages))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List packages.")
    list_parser.add_argument("--json", action="store_true", help="Print JSON.")

    show_parser = subparsers.add_parser("show", help="Show one package.")
    show_parser.add_argument("name")
    show_parser.add_argument("--json", action="store_true", help="Print JSON.")

    system_packages_parser = subparsers.add_parser(
        "system-packages",
        help="Print the validated Docker system-package build argument.",
    )
    system_packages_parser.add_argument("name")

    args = parser.parse_args()
    if args.command == "list":
        return list_packages(json_output=args.json)
    if args.command == "show":
        return show_package(args.name, json_output=args.json)
    if args.command == "system-packages":
        return print_system_packages(args.name)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
