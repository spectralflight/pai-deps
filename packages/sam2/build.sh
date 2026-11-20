#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# https://github.com/facebookresearch/sam2/blob/main/INSTALL.md

: "${SAM2_GIT_REF:=2b90b9f5ceec907a1c18123530e92e794ad901a4}"
export SAM2_BUILD_CUDA="${SAM2_BUILD_CUDA:-1}"
export SAM2_BUILD_ALLOW_ERRORS="${SAM2_BUILD_ALLOW_ERRORS:-0}"

pai_deps_pip_wheel \
	"${SAM2_BUILD_SOURCE:-git+https://github.com/facebookresearch/sam2.git@${SAM2_GIT_REF}}" \
	"$@"
