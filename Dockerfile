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

ARG CUDA_VERSION="12.8.1"
ARG BASE_IMAGE="nvidia/cuda:${CUDA_VERSION}-cudnn-devel-ubuntu22.04"
FROM ${BASE_IMAGE}

ARG TARGETARCH
ARG PAI_DEPS_UV_VERSION="0.11.23"
ARG PAI_DEPS_UV_LINUX_ARM64_SHA256="80efb615b78c1e5721e5858135cd3499609b26741220332c843bd58936053bc6"
ARG PAI_DEPS_UV_LINUX_X64_SHA256="6be47081100ff1ce0ac7e85ba2ac12e32f2ffa6f946d78bf7f24ee9ce3a46181"
ARG PAI_DEPS_JUST_VERSION="1.53.0"
ARG PAI_DEPS_JUST_LINUX_ARM64_SHA256="f29d8e72380bc144465f632c7d59da311205eef2923d57511708b05b82f2e64f"
ARG PAI_DEPS_JUST_LINUX_X64_SHA256="7fedeb22c7e14d9ef1551e8b793700866d80f409f9884b0e80ebb65c11d4874d"

# Set the DEBIAN_FRONTEND environment variable to avoid interactive prompts during apt operations.
ENV DEBIAN_FRONTEND=noninteractive

# Update apt and install essential build dependencies in a single layer.
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        ccache \
        curl \
        gosu \
        software-properties-common \
        git-lfs \
        tree \
        wget

# Install ffmpeg 6
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    add-apt-repository ppa:ubuntuhandbook1/ffmpeg6 && \
    apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg

ENV PATH="/usr/lib/ccache:/usr/local/bin:$PATH"

# Tool versions and checksums are mirrored from mise.lock. Run
# `just build tool-versions-check` before building after tool upgrades.
RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64) \
            uv_arch="x86_64-unknown-linux-musl"; \
            uv_sha256="${PAI_DEPS_UV_LINUX_X64_SHA256}"; \
            just_arch="x86_64-unknown-linux-musl"; \
            just_sha256="${PAI_DEPS_JUST_LINUX_X64_SHA256}"; \
            ;; \
        arm64) \
            uv_arch="aarch64-unknown-linux-musl"; \
            uv_sha256="${PAI_DEPS_UV_LINUX_ARM64_SHA256}"; \
            just_arch="aarch64-unknown-linux-musl"; \
            just_sha256="${PAI_DEPS_JUST_LINUX_ARM64_SHA256}"; \
            ;; \
        *) \
            echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; \
            exit 1; \
            ;; \
    esac; \
    curl -fsSLo /tmp/uv.tar.gz "https://github.com/astral-sh/uv/releases/download/${PAI_DEPS_UV_VERSION}/uv-${uv_arch}.tar.gz"; \
    echo "${uv_sha256}  /tmp/uv.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/uv.tar.gz -C /tmp; \
    install -m 0755 "/tmp/uv-${uv_arch}/uv" /usr/local/bin/uv; \
    install -m 0755 "/tmp/uv-${uv_arch}/uvx" /usr/local/bin/uvx; \
    curl -fsSLo /tmp/just.tar.gz "https://github.com/casey/just/releases/download/${PAI_DEPS_JUST_VERSION}/just-${PAI_DEPS_JUST_VERSION}-${just_arch}.tar.gz"; \
    echo "${just_sha256}  /tmp/just.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/just.tar.gz -C /tmp just; \
    install -m 0755 /tmp/just /usr/local/bin/just; \
    rm -rf /tmp/uv.tar.gz "/tmp/uv-${uv_arch}" /tmp/just.tar.gz /tmp/just

# Package descriptors provide this validated inventory. Installing it while
# constructing the image keeps package compilation and upstream build code unprivileged.
ARG PAI_DEPS_SYSTEM_PACKAGES=""
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    if [ -n "${PAI_DEPS_SYSTEM_PACKAGES}" ]; then \
        apt-get update && \
        apt-get install -y --no-install-recommends ${PAI_DEPS_SYSTEM_PACKAGES}; \
    fi

# Set the working directory for the application.
WORKDIR /app

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["/bin/bash"]
