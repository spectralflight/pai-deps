# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from pai_deps.cli.package_info import print_system_packages


def test_prints_validated_system_packages(capsys) -> None:
    assert print_system_packages("torchcodec") == 0

    output = capsys.readouterr()
    assert output.err == ""
    assert output.out.split() == [
        "libavdevice-dev",
        "libavfilter-dev",
        "libavformat-dev",
        "libavcodec-dev",
        "libavutil-dev",
        "libswresample-dev",
        "libswscale-dev",
        "pkg-config",
        "python3-dev",
    ]
