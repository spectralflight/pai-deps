# decord Build Notes

Status: historical.
Research date: 2026-06-27.

## Status

`decord` is retained for historical GPU/NVDEC wheel documentation. It is not a
Torch extension; the Torch suffix is this repo's index convention.

## Local Build Entry Point

- Package descriptor: `pai-package.toml`
- Build script: `packages/decord/build.sh`
- Native library helper: `packages/decord/build_lib.sh`

## Upstream Sources

- Upstream repository: <https://github.com/dmlc/decord>
- PyPI: <https://pypi.org/project/decord/0.6.0/>
- NVIDIA Video Codec SDK: <https://developer.nvidia.com/video-codec-sdk>
- NVIDIA Video Codec SDK license page:
  <https://developer.nvidia.com/nvidia-video-codec-sdk-license-agreement>

## Version Constraints

Local package environment requires Python `>=3.10`. Upstream PyPI wheels are
CPU-only; GPU/NVDEC support requires source builds with FFmpeg and CUDA/Video
Codec SDK pieces. `pai-package.toml` sets `requires_torch = false`; the Torch
version argument is retained only for this repo's wheel local-version naming.

## Build Environment

Local helper uses the checked-in Video Codec interface headers, locates
`libnvcuvid.so` and `libnvidia-encode.so` from a caller-provided or system
library directory, configures CMake with `-DUSE_CUDA=ON
-DCMAKE_BUILD_TYPE=Release`, installs `libdecord.so` into a temporary user-owned
prefix, then wheels the Python package from the upstream `python` subdirectory.

Upstream build knobs include `-DUSE_CUDA=ON`, optional CUDA path,
`-DCMAKE_CUDA_COMPILER`, and optional `-DFFMPEG_DIR`.

Local wrapper variables:

- `DECORD_BUILD_JOBS`: passed to `make -j`.
- `DECORD_CUDA_ARCHITECTURES`: passed to CMake as
  `CMAKE_CUDA_ARCHITECTURES`.
- `DECORD_VIDEO_CODEC_INTERFACE_DIR`: optional override for the directory
  containing `cuviddec.h`, `nvcuvid.h`, and `nvEncodeAPI.h`. Defaults to the
  package-local `video-codec-interface-13.0.19/include`.
- `DECORD_VIDEO_CODEC_LIB_DIR`: optional directory containing
  `libnvcuvid.so` and `libnvidia-encode.so`. If unset, the script checks common
  CUDA, NVIDIA container runtime, and distro driver library directories.

## OOM Controls

Start with:

```dotenv
DECORD_BUILD_JOBS=4
DECORD_CUDA_ARCHITECTURES=120
```

Use `DECORD_CUDA_ARCHITECTURES` rather than `TORCH_CUDA_ARCH_LIST`; Decord is a
CMake/CUDA build, not a PyTorch extension build.

## Smoke Test

Generate a tiny MP4 with FFmpeg, then:

```bash
python - <<'PY'
from decord import VideoReader, cpu
vr = VideoReader("tiny.mp4", ctx=cpu(0))
assert len(vr)
assert vr[0].asnumpy().ndim == 3
PY
```

Use GPU/NVDEC smoke only on a host with driver/video decode support.

## Known Risks

- FFmpeg 6 source patches in `build_lib.sh` are brittle against newer decord or
  FFmpeg changes.
- The package-specific Docker image installs the descriptor's system packages
  before the non-root package build starts.
- The repo intentionally vendors only the NVIDIA Video Codec interface headers.
  The full Video Codec SDK archive and binary stubs are not checked in because
  the SDK license restricts stand-alone redistribution of SDK portions.

## Future Fixes

- Replace the link-library discovery with a base image or setup phase that
  provides explicit Video Codec SDK stubs without committing SDK binaries to
  this public repository.

## Research Notes

Imported from upstream docs/source and package research on 2026-06-27. A
Docker smoke on 2026-06-28 used
`PAI_DEPS_BUILD_ENV='DECORD_BUILD_JOBS=1 DECORD_CUDA_ARCHITECTURES=120'`
and built `decord==0.6.0` for Python 3.12/CUDA 12.8/Torch-name 2.9 in about a
minute after skipping an unnecessary Torch install. The CPU decode smoke read a
two-frame 16x16 MP4 and returned a nonempty `uint8` frame with shape
`(16, 16, 6)`.

NVIDIA's public Video Codec SDK page provides a separate gated download for the
full SDK and a separate interface header download. The local SDK license permits
only limited SDK distribution as incorporated object code and prohibits
distributing the SDK as a stand-alone product, so this package keeps only the
header files whose file-local notices permit redistribution.
