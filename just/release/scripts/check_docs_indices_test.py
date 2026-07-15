# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import importlib.util
import sys
from pathlib import Path


def _load_check_docs_indices():
    module_path = Path(__file__).with_name("check_docs_indices.py")
    spec = importlib.util.spec_from_file_location("check_docs_indices", module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


check_docs_indices = _load_check_docs_indices()
ChangedPath = check_docs_indices.ChangedPath
forbidden_index_changes = check_docs_indices.forbidden_index_changes
parse_name_status = check_docs_indices.parse_name_status

SHA_A = "a" * 64
SHA_B = "b" * 64


def test_parse_name_status():
    assert parse_name_status(
        "M\tdocs/v1.5.0/index.html\nR100\tdocs/simple/index.html\tdocs/simple-old/index.html\n"
    ) == [
        ChangedPath(status="M", path="docs/v1.5.0/index.html"),
        ChangedPath(status="R100", old_path="docs/simple/index.html", path="docs/simple-old/index.html"),
    ]


def test_forbidden_index_changes_allows_new_index_files():
    changes = [
        ChangedPath(status="A", path="docs/v1.6.0/index.html"),
        ChangedPath(status="A", path="docs/v1.6.0/natten/index.html"),
        ChangedPath(status="M", path="agents/agent-guide.md"),
    ]

    assert forbidden_index_changes(changes) == []


def test_forbidden_index_changes_blocks_existing_index_edits():
    changes = [
        ChangedPath(status="M", path="docs/v1.5.0/index.html"),
        ChangedPath(status="D", path="docs/simple/natten/index.html"),
        ChangedPath(status="R100", old_path="docs/v1.4.0/index.html", path="docs/v1.4.0-old/index.html"),
    ]

    assert forbidden_index_changes(changes) == changes


def test_forbidden_index_changes_allows_unstable_index_edits():
    changes = [
        ChangedPath(status="M", path="docs/cosmos3-scratch/index.html"),
        ChangedPath(status="D", path="docs/cosmos3-scratch/natten/index.html"),
        ChangedPath(
            status="R100",
            old_path="docs/cosmos3-scratch/flash-attn/index.html",
            path="docs/cosmos3-scratch/fa/index.html",
        ),
    ]

    assert forbidden_index_changes(changes, index_stabilities={"cosmos3-scratch": "unstable"}) == []


def test_forbidden_index_changes_blocks_renames_from_stable_to_unstable():
    change = ChangedPath(status="R100", old_path="docs/v1.5.0/index.html", path="docs/cosmos3-scratch/index.html")

    assert forbidden_index_changes([change], index_stabilities={"cosmos3-scratch": "unstable"}) == [change]


def test_forbidden_index_changes_allows_append_only_stable_index_edits():
    change = ChangedPath(status="M", path="docs/cosmos3/natten/index.html")
    old_text = f"<a href='https://github.com/example/repo/releases/download/a/natten-1.whl#sha256={SHA_A}'>natten-1.whl</a><br>"
    new_text = (
        old_text
        + f"\n<a href='https://github.com/example/repo/releases/download/b/natten-2.whl#sha256={SHA_B}'>natten-2.whl</a><br>\n"
    )

    assert (
        forbidden_index_changes(
            [change],
            index_stabilities={"cosmos3": "stable"},
            old_texts={change.path: old_text},
            new_texts={change.path: new_text},
        )
        == []
    )


def test_forbidden_index_changes_allows_append_only_stable_root_index_edits():
    change = ChangedPath(status="M", path="docs/cosmos3/index.html")
    old_text = "<a href='natten/'>natten</a><br>"
    new_text = old_text + "\n<a href='decord/'>decord</a><br>\n"

    assert (
        forbidden_index_changes(
            [change],
            index_stabilities={"cosmos3": "stable"},
            old_texts={change.path: old_text},
            new_texts={change.path: new_text},
        )
        == []
    )


def test_forbidden_index_changes_blocks_hashless_stable_index_additions():
    change = ChangedPath(status="M", path="docs/cosmos3/natten/index.html")
    old_text = f"<a href='https://github.com/example/repo/releases/download/a/natten-1.whl#sha256={SHA_A}'>natten-1.whl</a><br>"
    new_text = (
        old_text + "\n<a href='https://github.com/example/repo/releases/download/b/natten-2.whl'>natten-2.whl</a><br>\n"
    )

    assert forbidden_index_changes(
        [change],
        index_stabilities={"cosmos3": "stable"},
        old_texts={change.path: old_text},
        new_texts={change.path: new_text},
    ) == [change]


def test_forbidden_index_changes_blocks_non_release_host_stable_index_additions():
    change = ChangedPath(status="M", path="docs/cosmos3/natten/index.html")
    old_text = f"<a href='https://github.com/example/repo/releases/download/a/natten-1.whl#sha256={SHA_A}'>natten-1.whl</a><br>"
    new_text = old_text + f"\n<a href='https://example.invalid/natten-2.whl#sha256={SHA_B}'>natten-2.whl</a><br>\n"

    assert forbidden_index_changes(
        [change],
        index_stabilities={"cosmos3": "stable"},
        old_texts={change.path: old_text},
        new_texts={change.path: new_text},
    ) == [change]


def test_forbidden_index_changes_blocks_changed_stable_index_links():
    change = ChangedPath(status="M", path="docs/cosmos3/natten/index.html")
    old_text = f"<a href='https://github.com/example/repo/releases/download/a/natten-1.whl#sha256={SHA_A}'>natten-1.whl</a><br>"
    new_text = f"<a href='https://github.com/example/repo/releases/download/a/natten-1.whl#sha256={SHA_B}'>natten-1.whl</a><br>"

    assert forbidden_index_changes(
        [change],
        index_stabilities={"cosmos3": "stable"},
        old_texts={change.path: old_text},
        new_texts={change.path: new_text},
    ) == [change]


def test_forbidden_index_changes_blocks_changed_stable_index_text():
    change = ChangedPath(status="M", path="docs/cosmos3/natten/index.html")
    old_text = f"<a href='https://github.com/example/repo/releases/download/a/natten-1.whl#sha256={SHA_A}'>natten-1.whl</a><br>"
    new_text = (
        f"<a href='https://github.com/example/repo/releases/download/a/natten-1.whl#sha256={SHA_A}'>changed</a><br>"
    )

    assert forbidden_index_changes(
        [change],
        index_stabilities={"cosmos3": "stable"},
        old_texts={change.path: old_text},
        new_texts={change.path: new_text},
    ) == [change]


def test_forbidden_index_changes_blocks_non_anchor_stable_index_additions():
    change = ChangedPath(status="M", path="docs/cosmos3/natten/index.html")
    old_text = f"<a href='https://github.com/example/repo/releases/download/a/natten-1.whl#sha256={SHA_A}'>natten-1.whl</a><br>"
    new_text = old_text + "<script>alert('no')</script>\n"

    assert forbidden_index_changes(
        [change],
        index_stabilities={"cosmos3": "stable"},
        old_texts={change.path: old_text},
        new_texts={change.path: new_text},
    ) == [change]
