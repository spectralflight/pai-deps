#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fail when a stable package index under docs/ is changed unsafely.

New index files and unstable indices are allowed. Stable package index files
are append-only because downstream lockfiles can rely on their wheel URLs and
hashes.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import urllib.parse
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

from pai_deps.index_manifest import load_index_manifests

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ChangedPath:
    status: str
    path: str
    old_path: str | None = None


def _is_package_index(path: str) -> bool:
    posix_path = PurePosixPath(path)
    return (
        len(posix_path.parts) >= 3
        and posix_path.parts[0] == "docs"
        and posix_path.parts[1] != "dev"
        and posix_path.name == "index.html"
    )


def _index_version(path: str) -> str | None:
    posix_path = PurePosixPath(path)
    if not _is_package_index(path):
        return None
    return posix_path.parts[1]


def parse_name_status(output: str) -> list[ChangedPath]:
    changes: list[ChangedPath] = []
    for line in output.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith(("R", "C")):
            if len(parts) != 3:
                raise ValueError(f"Unexpected git name-status line: {line!r}")
            changes.append(ChangedPath(status=status, old_path=parts[1], path=parts[2]))
        else:
            if len(parts) != 2:
                raise ValueError(f"Unexpected git name-status line: {line!r}")
            changes.append(ChangedPath(status=status, path=parts[1]))
    return changes


def _normalized_html_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _is_anchor_line(line: str) -> bool:
    return line.startswith("<a ") and line.endswith("</a><br>")


@dataclass(frozen=True)
class Anchor:
    attrs: dict[str, str]
    text: str


class AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[Anchor] = []
        self._current_attrs: dict[str, str] | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        self._current_attrs = {name: value or "" for name, value in attrs}
        self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_attrs is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._current_attrs is None:
            return
        self.anchors.append(Anchor(attrs=self._current_attrs, text="".join(self._current_text)))
        self._current_attrs = None
        self._current_text = []


def _anchors(line: str) -> list[Anchor]:
    parser = AnchorParser()
    parser.feed(line)
    parser.close()
    return parser.anchors


def _has_sha256_fragment(url: str) -> bool:
    fragment = urllib.parse.urlparse(url).fragment
    fragments = urllib.parse.parse_qs(fragment, keep_blank_values=True)
    return any(SHA256_RE.fullmatch(value) for value in fragments.get("sha256", []))


def _is_github_release_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme == "https" and parsed.netloc == "github.com" and "/releases/download/" in parsed.path


def _line_is_root_package_link(path: str, anchors: list[Anchor]) -> bool:
    posix_path = PurePosixPath(path)
    if len(posix_path.parts) != 3 or len(anchors) != 1:
        return False
    href = anchors[0].attrs.get("href", "")
    parsed = urllib.parse.urlparse(href)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        return False
    if not href.endswith("/") or "/" in href.rstrip("/"):
        return False
    return anchors[0].text == href.rstrip("/")


def _line_is_package_wheel_link(path: str, anchors: list[Anchor]) -> bool:
    posix_path = PurePosixPath(path)
    if len(posix_path.parts) < 4 or not anchors:
        return False

    primary_href = anchors[0].attrs.get("href", "")
    primary_filename = urllib.parse.unquote(urllib.parse.urlparse(primary_href).path.rsplit("/", 1)[-1])
    if not primary_filename.endswith(".whl"):
        return False
    if anchors[0].text != primary_filename:
        return False
    if not _is_github_release_url(primary_href) or not _has_sha256_fragment(primary_href):
        return False

    for sidecar in anchors[1:]:
        sidecar_href = sidecar.attrs.get("href", "")
        if sidecar.attrs.get("data-pai-artifact") != "true":
            return False
        if not _is_github_release_url(sidecar_href) or not _has_sha256_fragment(sidecar_href):
            return False
    return True


def _is_allowed_stable_addition(path: str, line: str) -> bool:
    if not _is_anchor_line(line):
        return False
    anchors = _anchors(line)
    return _line_is_root_package_link(path, anchors) or _line_is_package_wheel_link(path, anchors)


def _read_index_stabilities(indices_dir: Path = Path("indices")) -> dict[str, str]:
    return {index_name: manifest.stability for index_name, manifest in load_index_manifests(indices_dir).items()}


def _is_unstable_index_path(path: str, index_stabilities: dict[str, str]) -> bool:
    version = _index_version(path)
    return version is not None and index_stabilities.get(version) == "unstable"


def _append_only_html_change(
    path: str,
    *,
    old_texts: dict[str, str],
    new_texts: dict[str, str],
) -> bool:
    old_text = old_texts.get(path)
    new_text = new_texts.get(path)
    if old_text is None or new_text is None:
        return False
    old_lines = _normalized_html_lines(old_text)
    new_lines = _normalized_html_lines(new_text)
    old_line_set = set(old_lines)
    if not old_line_set <= set(new_lines):
        return False
    added_lines = [line for line in new_lines if line not in old_line_set]
    return all(_is_allowed_stable_addition(path, line) for line in added_lines)


def forbidden_index_changes(
    changes: list[ChangedPath],
    *,
    index_stabilities: dict[str, str] | None = None,
    old_texts: dict[str, str] | None = None,
    new_texts: dict[str, str] | None = None,
) -> list[ChangedPath]:
    index_stabilities = index_stabilities or {}
    old_texts = old_texts or {}
    new_texts = new_texts or {}
    forbidden: list[ChangedPath] = []
    for change in changes:
        status = change.status[0]
        if status == "A":
            continue

        changed_index_paths = [
            path for path in (change.path, change.old_path) if path is not None and _is_package_index(path)
        ]
        if not changed_index_paths:
            continue
        if all(_is_unstable_index_path(path, index_stabilities) for path in changed_index_paths):
            continue
        if (
            status == "M"
            and change.old_path is None
            and _is_package_index(change.path)
            and _append_only_html_change(change.path, old_texts=old_texts, new_texts=new_texts)
        ):
            continue
        else:
            forbidden.append(change)
    return forbidden


def _git_name_status(base: str) -> str:
    cmd = [
        "git",
        "diff",
        "--name-status",
        "--find-renames",
        f"{base}...HEAD",
        "--",
        "docs",
    ]
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
    return result.stdout


def _changed_paths(base: str) -> list[ChangedPath]:
    return parse_name_status(_git_name_status(base))


def _git_show(ref: str, path: str) -> str | None:
    cmd = ["git", "show", f"{ref}:{path}"]
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return None
    return result.stdout


def _read_changed_index_texts(changes: list[ChangedPath], *, base: str) -> tuple[dict[str, str], dict[str, str]]:
    old_texts: dict[str, str] = {}
    new_texts: dict[str, str] = {}
    for change in changes:
        for path in (change.path, change.old_path):
            if path is None or not _is_package_index(path):
                continue
            if path not in old_texts:
                old_text = _git_show(base, path)
                if old_text is not None:
                    old_texts[path] = old_text
            if path not in new_texts:
                new_path = Path(path)
                if new_path.exists():
                    new_texts[path] = new_path.read_text()
    return old_texts, new_texts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Git ref to compare against, such as origin/main.")
    args = parser.parse_args()

    changes = _changed_paths(args.base)
    old_texts, new_texts = _read_changed_index_texts(changes, base=args.base)
    forbidden = forbidden_index_changes(
        changes,
        index_stabilities=_read_index_stabilities(),
        old_texts=old_texts,
        new_texts=new_texts,
    )
    if not forbidden:
        return 0

    print("Stable package index files are append-only. Forbidden changes:")
    for change in forbidden:
        if change.old_path is not None:
            print(f"  {change.status}\t{change.old_path}\t{change.path}")
        else:
            print(f"  {change.status}\t{change.path}")
    print()
    print("Add links without changing existing links, or use an index manifest with stability 'unstable'.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
