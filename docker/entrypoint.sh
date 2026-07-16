#!/usr/bin/env bash
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

# Docker entrypoint script.

set -euo pipefail

export HOME="${HOME:-/root}"
export PATH="${PATH-}:${HOME}/.local/bin"
build_uid="${PAI_DEPS_BUILD_UID:-1000}"
build_gid="${PAI_DEPS_BUILD_GID:-${build_uid}}"

if [[ ! "${build_uid}" =~ ^[1-9][0-9]*$ || ! "${build_gid}" =~ ^[1-9][0-9]*$ ]]; then
	echo "Error: PAI_DEPS_BUILD_UID and PAI_DEPS_BUILD_GID must be non-root numeric IDs." >&2
	exit 1
fi

if [ "$(id -u)" -eq 0 ]; then
	build_home="${PAI_DEPS_BUILD_HOME:-/home/paideps}"

	if ! getent group "${build_gid}" >/dev/null; then
		groupadd --gid "${build_gid}" paideps
	fi
	if ! getent passwd "${build_uid}" >/dev/null; then
		useradd --uid "${build_uid}" --gid "${build_gid}" --home-dir "${build_home}" --create-home --shell /bin/bash paideps
	fi
	build_user="$(getent passwd "${build_uid}" | cut -d: -f1)"
	install -d -o "${build_uid}" -g "${build_gid}" "${build_home}"

	export HOME="${build_home}"
	export USER="${build_user}"
	export XDG_CACHE_HOME="${XDG_CACHE_HOME:-${HOME}/.cache}"
	export XDG_DATA_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}"
	export XDG_BIN_HOME="${XDG_BIN_HOME:-${HOME}/.local/bin}"
	export UV_CACHE_DIR="${UV_CACHE_DIR:-${XDG_CACHE_HOME}/uv}"
	export UV_PYTHON_CACHE_DIR="${UV_PYTHON_CACHE_DIR:-${XDG_CACHE_HOME}/uv-python}"
	export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-${HOME}/.venv/pai-deps}"
	export CCACHE_DIR="${CCACHE_DIR:-${XDG_CACHE_HOME}/ccache}"
	export PATH="${PATH}:${XDG_BIN_HOME}"

	gosu "${build_uid}:${build_gid}" mkdir -p \
		"${XDG_CACHE_HOME}" \
		"${XDG_DATA_HOME}" \
		"${XDG_BIN_HOME}" \
		"${UV_CACHE_DIR}" \
		"${UV_PYTHON_CACHE_DIR}" \
		"$(dirname "${UV_PROJECT_ENVIRONMENT}")" \
		"${CCACHE_DIR}"

	exec gosu "${build_uid}:${build_gid}" "$@"
fi

exec "$@"
