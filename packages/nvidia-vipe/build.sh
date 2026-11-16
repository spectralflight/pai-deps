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
# Include the upstream third-party notices in the wheel as well as the sdist.
source_dir="$(mktemp -d)"
git clone --filter=blob:none https://github.com/ashawkey/vipe.git "$source_dir"
git -C "$source_dir" checkout --detach "$PACKAGE_REVISION"
python - "$source_dir/pyproject.toml" <<'PYTHON'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
original = 'license-files = ["LICENSE"]'
if text.count(original) != 1:
    raise SystemExit("Expected upstream license-files declaration changed")
path.write_text(text.replace(original, 'license-files = ["LICENSE", "THIRD_PARTY_LICENSES.md"]'))
PYTHON
pai_deps_pip_wheel "$source_dir" "$@"
rm -rf "$source_dir"
