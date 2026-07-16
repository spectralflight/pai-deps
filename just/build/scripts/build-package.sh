#!/usr/bin/env -S bash -euxo pipefail
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

# CUDA 12.8 requires gcc<=14: `/usr/local/cuda-12.8/targets/x86_64-linux/include/crt/host_config.h`

# Build a package.

if [[ $# -lt 5 ]]; then
	echo "Usage: $0 <package_name> <package_version> <python_version> <torch_version> <build_dir>" >&2
	exit 1
fi
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PACKAGE_NAME="${1}"
shift
export PACKAGE_VERSION="${1}"
shift
export PYTHON_VERSION="${1}"
shift
export TORCH_VERSION="${1}"
shift
export BUILD_DIR="${1}"
shift

if [[ ! "${PYTHON_VERSION}" =~ ^[0-9]+\.[0-9]+$ ]]; then
	echo "Error: Python version must be '<major>.<minor>'." >&2
	exit 1
fi
if [[ ! "${TORCH_VERSION}" =~ ^[0-9]+\.[0-9]+$ ]]; then
	echo "Error: Torch version must be '<major>.<minor>'" >&2
	exit 1
fi

_trim() {
	local value="$1"
	value="${value#"${value%%[![:space:]]*}"}"
	value="${value%"${value##*[![:space:]]}"}"
	printf "%s" "${value}"
}

_is_reserved_env_name() {
	local name="$1"
	local reserved_name
	local reserved_env_names=(
		PACKAGE_NAME
		PACKAGE_VERSION
		PYTHON_VERSION
		TORCH_VERSION
		LOCAL_VERSION_SUFFIX
		OUTPUT_NAME
		OUTPUT_DIR
		PATH
		HOME
		USER
		XDG_CACHE_HOME
		XDG_DATA_HOME
		XDG_BIN_HOME
		UV_CACHE_DIR
		UV_PYTHON_CACHE_DIR
		UV_PROJECT_ENVIRONMENT
		CCACHE_DIR
		CUDA_HOME
		LD_LIBRARY_PATH
		CUDA_VERSION
	)
	for reserved_name in "${reserved_env_names[@]}"; do
		if [[ "${name}" == "${reserved_name}" ]]; then
			return 0
		fi
	done
	return 1
}

_strip_matching_quotes() {
	local value="$1"
	local first_char
	local last_char
	if [[ "${#value}" -lt 2 ]]; then
		printf "%s" "${value}"
		return
	fi
	first_char="${value:0:1}"
	last_char="${value: -1}"
	if [[ "${first_char}" == "${last_char}" && ("${first_char}" == "'" || "${first_char}" == '"') ]]; then
		printf "%s" "${value:1:${#value}-2}"
		return
	fi
	printf "%s" "${value}"
}

_append_build_env_assignment() {
	local source="$1"
	local assignment="$2"
	local key
	local value

	assignment="$(_trim "${assignment}")"
	if [[ ! "${assignment}" =~ ^([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=(.*)$ ]]; then
		echo "Error: ${source}: expected KEY=VALUE" >&2
		exit 1
	fi
	key="${BASH_REMATCH[1]}"
	value="$(_trim "${BASH_REMATCH[2]}")"
	value="$(_strip_matching_quotes "${value}")"
	if _is_reserved_env_name "${key}"; then
		echo "Error: ${source}: ${key} is controlled by just/build/scripts/build-package.sh and cannot be set in PAI_DEPS_BUILD_ENV_FILE or PAI_DEPS_BUILD_ENV" >&2
		exit 1
	fi
	build_env_extra_args+=("${key}=${value}")
}

_load_env_file() {
	local env_file="$1"
	local env_line
	local line_no=0

	if [[ -z "${env_file}" ]]; then
		return
	fi
	if [[ ! -f "${env_file}" ]]; then
		echo "Error: PAI_DEPS_BUILD_ENV_FILE does not exist: ${env_file}" >&2
		exit 1
	fi

	while IFS= read -r env_line || [[ -n "${env_line}" ]]; do
		line_no=$((line_no + 1))
		env_line="${env_line%$'\r'}"
		env_line="$(_trim "${env_line}")"
		if [[ -z "${env_line}" || "${env_line:0:1}" == "#" ]]; then
			continue
		fi
		if [[ "${env_line}" == export[[:space:]]* ]]; then
			env_line="$(_trim "${env_line#export}")"
		fi
		_append_build_env_assignment "${env_file}:${line_no}" "${env_line}"
	done <"${env_file}"
}

_load_inline_env() {
	local inline_env="$1"
	local inline_token
	local inline_tokens=()

	if [[ -z "${inline_env}" ]]; then
		return
	fi

	read -r -a inline_tokens <<<"${inline_env}"
	for inline_token in "${inline_tokens[@]}"; do
		if [[ "${inline_token}" == "export" ]]; then
			continue
		fi
		_append_build_env_assignment "PAI_DEPS_BUILD_ENV token '${inline_token}'" "${inline_token}"
	done
}

build_env_extra_args=()
_load_env_file "${PAI_DEPS_BUILD_ENV_FILE:-}"
_load_inline_env "${PAI_DEPS_BUILD_ENV:-}"

_git_commit() {
	git -c safe.directory=/app rev-parse HEAD 2>/dev/null || git rev-parse HEAD 2>/dev/null || printf "unknown"
}

_git_dirty() {
	if git -c safe.directory=/app diff --quiet 2>/dev/null &&
		git -c safe.directory=/app diff --cached --quiet 2>/dev/null; then
		printf "false"
	elif git diff --quiet 2>/dev/null && git diff --cached --quiet 2>/dev/null; then
		printf "false"
	else
		printf "true"
	fi
}

_write_wheel_sidecars() {
	local build_env_arg
	local provenance_args=()
	local provenance_cmd=()
	local wheel
	local wheels=()

	for build_env_arg in "${build_env_extra_args[@]}"; do
		provenance_args+=("--build-env" "${build_env_arg}")
	done

	shopt -s nullglob
	wheels=("${OUTPUT_DIR}"/*.whl)
	shopt -u nullglob

	if command -v python >/dev/null 2>&1; then
		provenance_cmd=(python)
	elif command -v python3 >/dev/null 2>&1; then
		provenance_cmd=(python3)
	else
		provenance_cmd=(uv run --frozen python)
	fi

	for wheel in "${wheels[@]}"; do
		cp "${log_file}" "${wheel}.build.log"
		"${provenance_cmd[@]}" -m pai_deps.build_tools.write_build_provenance \
			--wheel "${wheel}" \
			--build-log "${wheel}.build.log" \
			--output "${wheel}.build.json" \
			--package-name "${PACKAGE_NAME}" \
			--package-version "${PACKAGE_VERSION}" \
			--python-version "${PYTHON_VERSION}" \
			--torch-version "${TORCH_VERSION}" \
			--cuda-version "${CUDA_VERSION}" \
			--local-version-suffix "${LOCAL_VERSION_SUFFIX:-}" \
			--output-name "${OUTPUT_NAME}" \
			--git-commit "$(_git_commit)" \
			--git-dirty "$(_git_dirty)" \
			--docker-image "${PAI_DEPS_DOCKER_IMAGE:-}" \
			"${provenance_args[@]}"
	done
}

timestamp=$(date +%Y%m%d%H%M%S)
export OUTPUT_NAME="${timestamp}-${PACKAGE_NAME//-/_}-${PACKAGE_VERSION}-py${PYTHON_VERSION}-cu${CUDA_VERSION}-torch${TORCH_VERSION}"
OUTPUT_DIR="${BUILD_DIR}/${OUTPUT_NAME}"
rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"
OUTPUT_DIR="$(realpath "${OUTPUT_DIR}")"
export OUTPUT_DIR="${OUTPUT_DIR}"
log_file="${OUTPUT_DIR}/build.log"
echo "Logging to ${log_file}"

export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_BIN_HOME="${XDG_BIN_HOME:-$XDG_DATA_HOME/../bin}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$XDG_CACHE_HOME/uv}"
export UV_PYTHON_CACHE_DIR="${UV_PYTHON_CACHE_DIR:-$XDG_CACHE_HOME/uv-python}"
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-$XDG_DATA_HOME/pai-deps/project-venv}"
export CCACHE_DIR="${CCACHE_DIR:-$HOME/.ccache}"
build_env_args=(
	PACKAGE_NAME="${PACKAGE_NAME}"
	PACKAGE_VERSION="${PACKAGE_VERSION}"
	PYTHON_VERSION="${PYTHON_VERSION}"
	TORCH_VERSION="${TORCH_VERSION}"
	LOCAL_VERSION_SUFFIX="${LOCAL_VERSION_SUFFIX:-}"
	OUTPUT_NAME="${OUTPUT_NAME}"
	OUTPUT_DIR="${OUTPUT_DIR}"
	PATH="${PATH:-}"
	HOME="${HOME:-}"
	USER="${USER:-}"
	XDG_CACHE_HOME="${XDG_CACHE_HOME}"
	XDG_DATA_HOME="${XDG_DATA_HOME}"
	XDG_BIN_HOME="${XDG_BIN_HOME}"
	UV_CACHE_DIR="${UV_CACHE_DIR}"
	UV_PYTHON_CACHE_DIR="${UV_PYTHON_CACHE_DIR}"
	UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT}"
	CCACHE_DIR="${CCACHE_DIR}"
)
env -i "${build_env_args[@]}" "${build_env_extra_args[@]}" bash -euxo pipefail "${script_dir}/build-package-inner.sh" "$@" |& tee "${log_file}"
_write_wheel_sidecars
