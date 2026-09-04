# shellcheck shell=bash
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

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root_dir="$(pwd)"
package_dir="${root_dir}/packages/${PACKAGE_NAME}"
export PAI_DEPS_REPO_ROOT="${root_dir}"

# shellcheck source=just/build/scripts/build-helpers.sh
source "${script_dir}/build-helpers.sh"

CUDA_VERSION=$(nvcc --version | sed -n 's/^.*release \([0-9]\+\.[0-9]\+\).*$/\1/p')
CUDA_NAME="${CUDA_VERSION//./}"
TORCH_NAME="${TORCH_VERSION//./}"

echo "Building ${PACKAGE_NAME}=${PACKAGE_VERSION} python=${PYTHON_VERSION} torch=${TORCH_VERSION} cuda=${CUDA_VERSION}" "$@"
requires_torch=1
if grep -Eq '^[[:space:]]*requires_torch[[:space:]]*=[[:space:]]*false' "${package_dir}/pai-package.toml"; then
	requires_torch=0
fi
preinstalled_torch=0
if grep -Eq '^[[:space:]]*preinstalled_torch[[:space:]]*=[[:space:]]*true' "${package_dir}/pai-package.toml"; then
	preinstalled_torch=1
fi
if [[ "${requires_torch}" == "0" && "${preinstalled_torch}" == "1" ]]; then
	echo "Error: preinstalled_torch requires requires_torch = true." >&2
	exit 1
fi

_print_build_environment() {
	local name
	local names=(
		PACKAGE_NAME
		PACKAGE_VERSION
		PYTHON_VERSION
		TORCH_VERSION
		LOCAL_VERSION_SUFFIX
		OUTPUT_NAME
		OUTPUT_DIR
		CUDA_HOME
		CUDA_VERSION
		XDG_CACHE_HOME
		XDG_DATA_HOME
		XDG_BIN_HOME
		UV_CACHE_DIR
		UV_PYTHON_CACHE_DIR
		UV_PROJECT_ENVIRONMENT
		CCACHE_DIR
	)

	for name in "${names[@]}"; do
		if [[ -v "${name}" ]]; then
			printf "%s=%q\n" "${name}" "${!name}"
		fi
	done
}

# Print system information.
date
uname -a
cat /etc/os-release
ldd --version
gcc --version
_print_build_environment

# Set CUDA environment variables
export CUDA_HOME="/usr/local/cuda"
# Check if CUDA_HOME is valid.
if [ ! -d "${CUDA_HOME}/bin" ]; then
	echo "CUDA ${CUDA_VERSION} is not installed."
	exit 1
fi
export PATH="${CUDA_HOME}/bin:${PATH:-}"
export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH:-}"
nvcc --version

# Install build dependencies
pushd "${package_dir}"
venv_dir="$(uv cache dir)/pai-deps/${OUTPUT_NAME}"
if [[ "${preinstalled_torch}" == "1" ]]; then
	system_python="$(command -v python3)"
	if [[ "$("${system_python}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" != "${PYTHON_VERSION}" ]]; then
		echo "Error: preinstalled Python does not match requested ${PYTHON_VERSION}." >&2
		exit 1
	fi
	venv_args=(--python "${system_python}" --system-site-packages)
else
	uv python install "${PYTHON_VERSION}"
	venv_args=(--python "${PYTHON_VERSION}")
fi
uv venv "${venv_args[@]}" "${venv_dir}"
# shellcheck source=/dev/null
source "${venv_dir}/bin/activate"
uv sync --active

if [[ "${requires_torch}" == "1" ]]; then
	if [[ "${preinstalled_torch}" == "1" ]]; then
		python -c '
import torch
import os
expected = os.environ["TORCH_VERSION"] + "."
if not torch.__version__.startswith(expected):
    raise SystemExit(f"preinstalled torch {torch.__version__!r} does not match {expected!r}")
print(f"Using preinstalled torch={torch.__version__} cuda={torch.version.cuda}")
'
	else
		uv pip install "torch==${TORCH_VERSION}.*" --index-url "https://download.pytorch.org/whl/cu${CUDA_NAME}"
	fi

	# Set Torch-derived build environment variables.
	eval "$(PYTHONPATH="${root_dir}" python -c "
from pai_deps.build import build_env
build_env()
")"
else
	echo "Skipping torch install for ${PACKAGE_NAME}; pai-package.toml declares requires_torch = false."
fi

# Configure ccache
ccache --zero-stats
export CCACHE_NOHASHDIR="true"

# Build the package.
# shellcheck source=/dev/null
source "${package_dir}/build.sh" "$@"
deactivate
rm -rf "${venv_dir}"
popd || exit 1

ccache --show-stats

# Fix wheel filenames.
# Optionally append a build-variant suffix to the local version (e.g. LOCAL_VERSION_SUFFIX=gb300
# -> '...+cu130.torch210.gb300') to distinguish a custom build from the upstream wheel.
LOCAL_VERSION="cu${CUDA_NAME}.torch${TORCH_NAME}${LOCAL_VERSION_SUFFIX:+.${LOCAL_VERSION_SUFFIX}}"
uv run --frozen --no-dev pai-deps-fix-wheel -i "${OUTPUT_DIR}"/*.whl --version="${PACKAGE_VERSION}" --local-version="${LOCAL_VERSION}"
