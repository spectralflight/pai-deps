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

import os
import shlex

import torch

MIN_CUDA_ARCH = (8, 0)  # Ampere


def _parse_torch_cuda_arch(name: str) -> tuple[int, int]:
    """Parse CUDA architecture from a string of the form sm_<major><minor>."""
    name = name.removeprefix("sm_")
    major = int(name[:-1])
    minor = int(name[-1])
    return major, minor


def _get_torch_cuda_arch_list() -> list[tuple[int, int]]:
    """Get the list of CUDA architectures supported by PyTorch."""
    targets = torch.cuda.get_arch_list()
    if not targets and torch.version.cuda is not None:
        # get_arch_list() hides the compiled targets when driver initialization
        # fails. Cross-compilation needs the wheel's targets, not a working GPU.
        targets = (torch._C._cuda_getArchFlags() or "").split()
        if not targets:
            raise RuntimeError("CUDA Torch does not report compiled architecture targets")
    arch_list = []
    for arch in targets:
        if not arch.startswith("sm_"):
            continue
        ver = _parse_torch_cuda_arch(arch)
        if ver < MIN_CUDA_ARCH:
            # Only support Ampere and later.
            continue
        arch_list.append(ver)
    return arch_list


def _format_build_env() -> list[str]:
    """Print the build environment variables."""
    lines: list[str] = []
    _GLIBCXX_USE_CXX11_ABI = 1 if torch.compiled_with_cxx11_abi() else 0
    lines.append(f"export _GLIBCXX_USE_CXX11_ABI={_GLIBCXX_USE_CXX11_ABI}")
    torch_cuda_arch_list = os.environ.get("TORCH_CUDA_ARCH_LIST")
    if not torch_cuda_arch_list:
        torch_cuda_arch_list = ";".join([f"{major}.{minor}" for major, minor in _get_torch_cuda_arch_list()])
    lines.append(f"export TORCH_CUDA_ARCH_LIST={shlex.quote(torch_cuda_arch_list)}")
    return lines


def build_env() -> None:
    for line in _format_build_env():
        print(line)
