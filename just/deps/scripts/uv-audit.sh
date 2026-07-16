#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Audit the root project and package build environments with uv.

set -euo pipefail

args=("$@")
if [ "${#args[@]}" -eq 0 ]; then
	args=(--frozen)
fi

if [ "${PAI_DEPS_AUDIT_STRICT:-0}" = "1" ]; then
	args+=(--no-config)
else
	# Temporary until all project locks can move to setuptools >=83.0.0.
	args+=(--ignore PYSEC-2026-3447)
fi

_audit_project() {
	local project_dir="$1"
	local audit_args=(--preview-features audit-command "${args[@]}")

	if [ "${project_dir}" = "." ]; then
		uv audit "${audit_args[@]}"
	else
		uv audit --project "${project_dir}" "${audit_args[@]}"
	fi
}

status=0

echo "Auditing root project" >&2
_audit_project "." || status=1

for project_dir in packages/*; do
	if [ ! -f "${project_dir}/pyproject.toml" ]; then
		continue
	fi
	echo "Auditing ${project_dir}" >&2
	_audit_project "${project_dir}" || status=1
done

exit "${status}"
