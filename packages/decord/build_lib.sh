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

# https://github.com/dmlc/decord?tab=readme-ov-file#installation
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
interface_dir="${DECORD_VIDEO_CODEC_INTERFACE_DIR:-${script_dir}/video-codec-interface-13.0.19/include}"

if [[ $# -ne 1 ]]; then
	echo "Usage: $0 NATIVE_INSTALL_PREFIX" >&2
	exit 1
fi
native_prefix="$1"

arch="$(uname -m)"
case "${arch}" in
x86_64)
	debian_arch="x86_64-linux-gnu"
	;;
aarch64)
	debian_arch="aarch64-linux-gnu"
	;;
*)
	debian_arch="${arch}-linux-gnu"
	;;
esac

_has_video_codec_libs() {
	local lib_dir="$1"
	[[ -f "${lib_dir}/libnvcuvid.so" && -f "${lib_dir}/libnvidia-encode.so" ]]
}

_find_video_codec_lib_dir() {
	local lib_dir
	if [[ -n "${DECORD_VIDEO_CODEC_LIB_DIR:-}" ]]; then
		if _has_video_codec_libs "${DECORD_VIDEO_CODEC_LIB_DIR}"; then
			printf "%s" "${DECORD_VIDEO_CODEC_LIB_DIR}"
			return 0
		fi
		echo "Error: DECORD_VIDEO_CODEC_LIB_DIR must contain libnvcuvid.so and libnvidia-encode.so: ${DECORD_VIDEO_CODEC_LIB_DIR}" >&2
		return 1
	fi

	for lib_dir in \
		"/usr/local/cuda/lib64/stubs" \
		"/usr/local/cuda/lib64" \
		"/usr/local/nvidia/lib64" \
		"/usr/lib/${debian_arch}" \
		"/usr/lib64"; do
		if _has_video_codec_libs "${lib_dir}"; then
			printf "%s" "${lib_dir}"
			return 0
		fi
	done

	cat >&2 <<EOF
Error: decord requires NVIDIA Video Codec link libraries.
Set DECORD_VIDEO_CODEC_LIB_DIR to a directory containing libnvcuvid.so and
libnvidia-encode.so, for example a locally downloaded Video Codec SDK
Lib/linux/stubs/${arch} directory or a driver library directory mounted by the
NVIDIA container runtime.
EOF
	return 1
}

if [[ ! -f "${interface_dir}/nvcuvid.h" || ! -f "${interface_dir}/cuviddec.h" || ! -f "${interface_dir}/nvEncodeAPI.h" ]]; then
	echo "Error: DECORD_VIDEO_CODEC_INTERFACE_DIR must contain the NVIDIA Video Codec interface headers: ${interface_dir}" >&2
	exit 1
fi

video_codec_lib_dir="$(_find_video_codec_lib_dir)"

temp_dir="$(mktemp -d)"
trap 'rm -rf "${temp_dir}"' EXIT
cd "${temp_dir}"
git clone --depth 1 --branch "v${PACKAGE_VERSION}" --recursive https://github.com/dmlc/decord
cd decord

# Fix to work with ffmpeg 6.0
find . -type f -exec sed -i "s/AVInputFormat \*/const AVInputFormat \*/g" {} \;
sed -i "s/[[:space:]]AVCodec \*dec/const AVCodec \*dec/" src/video/video_reader.cc
sed -i "s/avcodec\.h>/avcodec\.h>\n#include <libavcodec\/bsf\.h>/" src/video/ffmpeg/ffmpeg_common.h

mkdir build
cd build
cmake_args=(
	..
	-DUSE_CUDA=ON
	-DCMAKE_BUILD_TYPE=Release
	"-DCMAKE_CXX_FLAGS=-I${interface_dir}"
	"-DCUDA_NVCUVID_LIBRARY=${video_codec_lib_dir}/libnvcuvid.so"
)
if [[ -n "${DECORD_CUDA_ARCHITECTURES:-}" ]]; then
	cmake_args+=("-DCMAKE_CUDA_ARCHITECTURES=${DECORD_CUDA_ARCHITECTURES}")
fi
cmake "${cmake_args[@]}"
cmake --build . --parallel "${DECORD_BUILD_JOBS:-$(nproc)}"
cmake --install . --prefix "${native_prefix}"
