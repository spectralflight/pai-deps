#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

repo="$(git rev-parse --show-toplevel)"
cd "${repo}"

markdown_files=()

if [[ -f AGENTS.md ]]; then
	markdown_files+=("AGENTS.md")
fi

if [[ -d agents ]]; then
	while IFS= read -r -d '' markdown_file; do
		markdown_files+=("${markdown_file}")
	done < <(find agents -type f -name '*.md' -print0)
fi

if [[ -d packages ]]; then
	while IFS= read -r -d '' markdown_file; do
		markdown_files+=("${markdown_file}")
	done < <(find packages -path '*/agents/*.md' -type f -print0)
fi

while IFS= read -r -d '' markdown_file; do
	markdown_files+=("${markdown_file#./}")
done < <(
	find . \
		-path './.git' -prune -o \
		-path './.venv' -prune -o \
		-path './tmp' -prune -o \
		-name SKILL.md -type f -print0
)

if ((${#markdown_files[@]} == 0)); then
	exit 0
fi

mise exec -- rumdl --no-config check "${markdown_files[@]}"
