#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

source_dir="$(mktemp -d)"
git clone --filter=blob:none --no-checkout https://github.com/open-mmlab/mmcv.git "${source_dir}/mmcv"
git -C "${source_dir}/mmcv" checkout --detach fc038a386a42d1f36d9ec49169d5817a52c70b8e

# PyTorch 2.13 requires C++17; MMCV 2.0.1 predates that compiler baseline.
sed -i 's/-std=c++14/-std=c++17/g' "${source_dir}/mmcv/setup.py"

export FORCE_CUDA="${FORCE_CUDA:-1}"
export MAX_JOBS="${MAX_JOBS:-8}"
export MMCV_WITH_OPS="${MMCV_WITH_OPS:-1}"
python -m build --wheel --no-isolation --outdir "${OUTPUT_DIR}" "${source_dir}/mmcv"
