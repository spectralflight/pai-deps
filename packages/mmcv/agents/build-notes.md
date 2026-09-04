# MMCV Build Notes

Status: smoke.
Research date: 2026-09-03.

## Status

This runtime-specific recipe supports OmniHD PointPillars inference in the
Imaginaire4 LiDARBench image. It is not a general MMCV compatibility promise.

## Local Build Entry Point

- Package descriptor: `packages/mmcv/pai-package.toml`
- Build script: `packages/mmcv/build.sh`
- Build through `just build package` with an exact NGC base image.

## Upstream Sources

- Repository: <https://github.com/open-mmlab/mmcv>
- Revision: `fc038a386a42d1f36d9ec49169d5817a52c70b8e` (`v2.0.1`)
- License: Apache-2.0

## Version Constraints

The current consumer is CPython 3.12, PyTorch
`2.13.0a0+8145d630e8.nv26.06`, and CUDA 13.3 from NVIDIA PyTorch 26.06.
MMDetection3D 1.4 requires MMCV `<2.2.0`.

## Build Environment

Set `PAI_DEPS_DOCKER_BASE_IMAGE` to the immutable NGC image digest,
`PAI_DEPS_DOCKER_CUDA_VERSION=13.3.0`, and
`PAI_DEPS_DOCKER_INSTALL_FFMPEG=0`. The descriptor selects preinstalled Torch.

## OOM Controls

`MAX_JOBS=8` is the proven desktop setting. Reduce it if compilation exhausts
host memory. `TORCH_CUDA_ARCH_LIST` is derived from the preinstalled Torch build
unless explicitly supplied.

## Smoke Test

Install the wheel in the exact LiDARBench image and execute real CUDA calls for
`mmcv.ops.Voxelization` and `mmcv.ops.nms_rotated`, then strict-load all 132
OmniHD checkpoint tensors and run a known MADS frame.

## Known Risks

- Python wheel tags do not encode the PyTorch ABI.
- The recipe changes MMCV's language flag from C++14 to C++17 because PyTorch
  2.13 rejects C++14 extensions.
- A successful import is insufficient; both required CUDA operators must run.

## Future Fixes

Remove the wheel when the consumer image moves to a supported OpenMMLab stack
or no longer uses OmniHD PointPillars.

## Research Notes

The exact stack and C++17 patch were established through bounded A100 and H200
experiments on 2026-09-03. No upstream source is vendored.
