#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# https://github.com/DepthAnything/Video-Depth-Anything

temp_dir="$(mktemp -d)"
trap 'rm -rf "${temp_dir}"' EXIT

git init -q "${temp_dir}/src"
git -C "${temp_dir}/src" fetch --depth 1 https://github.com/DepthAnything/Video-Depth-Anything.git "${VDA_GIT_REF:-v${PACKAGE_VERSION}}"
git -C "${temp_dir}/src" checkout --quiet FETCH_HEAD
cd "${temp_dir}/src"

license_files_py="$(pai_deps_copy_license_files_py "${PWD}" "${PWD}")"

# The inference library imports this helper from a generic top-level utils package.
# Ship it in the library namespace so that installed benchmarks cannot shadow it.
if [[ "${VDA_INFERENCE_ONLY:-0}" == "1" ]]; then
    cp utils/util.py video_depth_anything/util/frames.py
    sed -i 's/from utils.util import /from .util.frames import /' video_depth_anything/{video_depth,video_depth_stream}.py
fi

touch \
	video_depth_anything/__init__.py \
	video_depth_anything/motion_module/__init__.py \
	video_depth_anything/util/__init__.py \
	utils/__init__.py \
	loss/__init__.py \
	benchmark/dataset_extract/__init__.py \
	benchmark/eval/__init__.py \
	benchmark/infer/__init__.py

cat >setup.py <<EOF
import os
from setuptools import find_packages, setup

inference_only = os.environ.get("VDA_INFERENCE_ONLY") == "1"

setup(
    name="video-depth-anything",
    version="${PACKAGE_VERSION}",
    description="Packaged import surface for Video-Depth-Anything",
    license_files=${license_files_py},
    packages=find_packages(include=["video_depth_anything", "video_depth_anything.*"]) if inference_only else find_packages(include=["video_depth_anything", "video_depth_anything.*", "utils", "utils.*", "loss", "loss.*", "benchmark", "benchmark.*"]),
    py_modules=[] if inference_only else ["run", "run_streaming"],
    python_requires=">=3.10",
    install_requires=[
        "einops",
        "numpy",
        "opencv-python-headless",
        "pillow",
        "torch",
        "torchvision",
        "tqdm",
    ],
)
EOF

pai_deps_pip_wheel \
	. \
	"$@"
