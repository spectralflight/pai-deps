#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# The public scorer consumes the PyPI 1.1.0 source release.
[[ "$PACKAGE_VERSION" == "1.1.0" ]] || {
	echo "Unsupported SAM2 version: $PACKAGE_VERSION" >&2
	exit 1
}
export SAM2_BUILD_CUDA="${SAM2_BUILD_CUDA:-1}"
export SAM2_BUILD_ALLOW_ERRORS="${SAM2_BUILD_ALLOW_ERRORS:-0}"
pai_deps_pip_wheel \
	"https://files.pythonhosted.org/packages/ce/11/d07fc96688f731a85de6d5260e98b709051eded2b7b5667ae292530bcf90/sam2-1.1.0.tar.gz#sha256=7e0ea252d43c10d853e3acfce0b5770ac683c30481bd6de311300e9d44f45b74" \
	"$@"
