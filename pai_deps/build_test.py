# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
import torch

import pai_deps.build as build


def test_parse_torch_cuda_arch():
    assert build._parse_torch_cuda_arch("sm_80") == (8, 0)
    assert build._parse_torch_cuda_arch("sm_86") == (8, 6)
    assert build._parse_torch_cuda_arch("sm_120") == (12, 0)


def test_get_torch_cuda_arch_list(monkeypatch):
    monkeypatch.setattr(
        torch.cuda,
        "get_arch_list",
        lambda: ["sm_75", "sm_80", "compute_90", "sm_86", "sm_90", "sm_100", "sm_120"],
    )
    assert build._get_torch_cuda_arch_list() == [(8, 0), (8, 6), (9, 0), (10, 0), (12, 0)]


def test_build_env(monkeypatch):
    monkeypatch.delenv("TORCH_CUDA_ARCH_LIST", raising=False)
    monkeypatch.setattr(build, "_get_torch_cuda_arch_list", lambda: [(8, 0), (8, 6), (9, 0), (10, 0), (12, 0)])
    monkeypatch.setattr(torch, "compiled_with_cxx11_abi", lambda: True)

    assert build._format_build_env() == [
        "export _GLIBCXX_USE_CXX11_ABI=1",
        "export TORCH_CUDA_ARCH_LIST='8.0;8.6;9.0;10.0;12.0'",
    ]


def test_build_env_respects_torch_cuda_arch_list(monkeypatch):
    monkeypatch.setenv("TORCH_CUDA_ARCH_LIST", "9.0")
    monkeypatch.setattr(torch, "compiled_with_cxx11_abi", lambda: True)
    assert build._format_build_env() == [
        "export _GLIBCXX_USE_CXX11_ABI=1",
        "export TORCH_CUDA_ARCH_LIST=9.0",
    ]


def test_compiled_targets_without_available_gpu(monkeypatch):
    monkeypatch.setattr(torch.cuda, "get_arch_list", lambda: [])
    monkeypatch.setattr(torch.version, "cuda", "12.8")
    monkeypatch.setattr(torch._C, "_cuda_getArchFlags", lambda: "sm_75 sm_80 sm_90 sm_100 sm_120")
    assert build._get_torch_cuda_arch_list() == [(8, 0), (9, 0), (10, 0), (12, 0)]


def test_cuda_build_rejects_missing_compiled_targets(monkeypatch):
    monkeypatch.setattr(torch.cuda, "get_arch_list", lambda: [])
    monkeypatch.setattr(torch.version, "cuda", "12.8")
    monkeypatch.setattr(torch._C, "_cuda_getArchFlags", lambda: None)
    with pytest.raises(RuntimeError, match="compiled architecture"):
        build._get_torch_cuda_arch_list()


def test_cpu_torch_does_not_query_cuda_targets(monkeypatch):
    monkeypatch.setattr(torch.cuda, "get_arch_list", lambda: [])
    monkeypatch.setattr(torch.version, "cuda", None)

    def unexpected_cuda_query():
        raise AssertionError("CPU Torch must not query CUDA targets")

    monkeypatch.setattr(torch._C, "_cuda_getArchFlags", unexpected_cuda_query)
    assert build._get_torch_cuda_arch_list() == []
