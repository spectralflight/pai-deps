# shellcheck shell=bash
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

case "$PACKAGE_VERSION" in
1.2.0.post20260710)
	PACKAGE_REVISION="43fa1effc9baf329c5b365bcf06ddb2ef6627662"
	;;
*)
	echo "Unsupported ViPE build version: $PACKAGE_VERSION" >&2
	exit 1
	;;
esac

export MAX_JOBS="${MAX_JOBS:-2}"
export USE_SYSTEM_EIGEN=1
pai_deps_pip_wheel \
	"git+https://github.com/ashawkey/vipe.git@${PACKAGE_REVISION}" \
	"$@"
