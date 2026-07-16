#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

usage() {
	cat >&2 <<'EOF'
Usage: just/build/scripts/docker-build-package.sh PACKAGE VERSION PYTHON_VERSION TORCH_VERSION BUILD_DIR [BUILD_ARGS...]

Run a package build inside Docker. Set PAI_DEPS_BUILD_ATTEMPTS to retry
transient network failures while reusing Docker and uv caches.
EOF
}

if [[ $# -lt 5 ]]; then
	usage
	exit 1
fi

package_name="$1"
package_version="$2"
python_version="$3"
torch_version="$4"
build_dir="$5"
shift 5

attempts="${PAI_DEPS_BUILD_ATTEMPTS:-1}"
retry_delay="${PAI_DEPS_BUILD_RETRY_DELAY:-30}"
cuda_version="${PAI_DEPS_DOCKER_CUDA_VERSION:-12.8.1}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exit_code=0
docker_run_args=()
system_packages="$(uv run --frozen --no-dev pai-deps-package-info system-packages "${package_name}")"
docker_run_args+=("--build-arg" "PAI_DEPS_SYSTEM_PACKAGES=${system_packages}")

if [[ "${build_dir}" = /* ]]; then
	mkdir -p "${build_dir}"
	host_build_dir="$(cd "${build_dir}" && pwd)"
	build_dir="/pai-deps-output"
	docker_run_args+=("--run-arg" "-v" "--run-arg" "${host_build_dir}:${build_dir}")
fi
if [[ ! "${attempts}" =~ ^[1-9][0-9]*$ ]]; then
	echo "Error: PAI_DEPS_BUILD_ATTEMPTS must be a positive integer." >&2
	exit 1
fi

for ((attempt = 1; attempt <= attempts; attempt++)); do
	echo "Docker build attempt ${attempt}/${attempts}: ${package_name} ${package_version} py${python_version} torch${torch_version} cuda${cuda_version}"
	if "${script_dir}/docker-run.sh" --cuda-version "${cuda_version}" --no-tty "${docker_run_args[@]}" -- \
		just/build/scripts/build-package.sh "${package_name}" "${package_version}" "${python_version}" "${torch_version}" "${build_dir}" "$@"; then
		exit 0
	else
		exit_code=$?
	fi
	if ((attempt < attempts)); then
		echo "Build attempt ${attempt} failed with exit code ${exit_code}; retrying in ${retry_delay}s." >&2
		sleep "${retry_delay}"
	fi
done

exit "${exit_code}"
