# shellcheck shell=bash
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

case "$PACKAGE_VERSION" in
0.0.post20261116)
	PACKAGE_REVISION="eb42fee2d71449efb0aa5c10549752b5d75384d8"
	;;
*)
	echo "Unsupported LightGlue build version: $PACKAGE_VERSION" >&2
	exit 1
	;;
esac
pai_deps_pip_wheel \
	"git+https://github.com/cvg/LightGlue.git@${PACKAGE_REVISION}" \
	"$@"
