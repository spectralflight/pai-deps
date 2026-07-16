#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

usage() {
	cat >&2 <<'EOF'
Usage: just/build/scripts/docker-run.sh [OPTIONS] [-- COMMAND...]

Build the CUDA Docker image and run it with the repository mounted at /app.

Options:
  --cuda-version VERSION   CUDA image version to build, default: 12.8.1
  --no-tty                Do not allocate an interactive TTY
  --tty                   Force an interactive TTY
  --build-arg ARG         Extra docker build argument, e.g. FOO=bar
  --run-arg ARG           Extra docker run argument
  -h, --help              Show this help
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../../.." && pwd)"
cuda_version="${PAI_DEPS_DOCKER_CUDA_VERSION:-12.8.1}"
host_cache_home="${XDG_CACHE_HOME:-${HOME}/.cache}"
uv_cache_dir="${UV_CACHE_DIR:-${host_cache_home}/uv}"
uv_python_cache_dir="${UV_PYTHON_CACHE_DIR:-${host_cache_home}/uv-python}"
ccache_dir="${CCACHE_DIR:-${host_cache_home}/ccache}"
tty_mode="auto"
build_args=()
run_args=()
command=()

while [[ $# -gt 0 ]]; do
	case "$1" in
	--cuda-version)
		cuda_version="$2"
		shift 2
		;;
	--no-tty)
		tty_mode="never"
		shift
		;;
	--tty)
		tty_mode="always"
		shift
		;;
	--build-arg)
		build_args+=("--build-arg=$2")
		shift 2
		;;
	--run-arg)
		run_args+=("$2")
		shift 2
		;;
	-h | --help)
		usage
		exit 0
		;;
	--)
		shift
		command=("$@")
		break
		;;
	*)
		command=("$@")
		break
		;;
	esac
done

env_file="${PAI_DEPS_BUILD_ENV_FILE:-}"
if [[ -n "${env_file}" ]]; then
	if [[ ! -f "${env_file}" ]]; then
		echo "Error: PAI_DEPS_BUILD_ENV_FILE does not exist: ${env_file}" >&2
		exit 1
	fi
	env_file_abs="$(realpath "${env_file}")"
	case "${env_file_abs}" in
	"${repo_root}"/*)
		env_file="${env_file_abs#"${repo_root}/"}"
		;;
	*)
		echo "Error: PAI_DEPS_BUILD_ENV_FILE must be inside the repository mounted at /app: ${env_file}" >&2
		exit 1
		;;
	esac
fi

tty_args=()
case "${tty_mode}" in
always)
	tty_args=(-it)
	;;
auto)
	if [[ -t 0 && -t 1 ]]; then
		tty_args=(-it)
	fi
	;;
never) ;;
*)
	echo "Error: invalid tty mode: ${tty_mode}" >&2
	exit 1
	;;
esac

mkdir -p "${uv_cache_dir}" "${uv_python_cache_dir}" "${ccache_dir}"
uv_cache_dir="$(realpath "${uv_cache_dir}")"
uv_python_cache_dir="$(realpath "${uv_python_cache_dir}")"
ccache_dir="$(realpath "${ccache_dir}")"
cache_args=(
	-v "${uv_cache_dir}:/cache/uv"
	-v "${uv_python_cache_dir}:/cache/uv-python"
	-v "${ccache_dir}:/cache/ccache"
)

image_tag="$(docker build --build-arg="CUDA_VERSION=${cuda_version}" "${build_args[@]}" -q "${repo_root}")"

docker run \
	"${tty_args[@]}" \
	--rm \
	--runtime=nvidia \
	-e PAI_DEPS_BUILD_UID="$(id -u)" \
	-e PAI_DEPS_BUILD_GID="$(id -g)" \
	-e PAI_DEPS_BUILD_HOME="/home/paideps" \
	-e UV_CACHE_DIR="/cache/uv" \
	-e UV_PYTHON_CACHE_DIR="/cache/uv-python" \
	-e CCACHE_DIR="/cache/ccache" \
	-e PAI_DEPS_DOCKER_IMAGE="${image_tag}" \
	-e PAI_DEPS_BUILD_ENV_FILE="${env_file}" \
	-e PAI_DEPS_BUILD_ENV="${PAI_DEPS_BUILD_ENV:-}" \
	-v "${repo_root}:/app" \
	"${cache_args[@]}" \
	"${run_args[@]}" \
	"${image_tag}" \
	"${command[@]}"
