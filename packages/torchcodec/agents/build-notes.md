# torchcodec Build Notes

Status: candidate.
Research date: 2026-10-14.

## Status

The CPU build targets TorchCodec 0.10.0 with Torch 2.10.0, including Linux
aarch64. Compatibility is tied closely to Torch; build completion alone does
not qualify a wheel for publication.

## Local Build Entry Point

- Package descriptor: `pai-package.toml`
- Build script: `packages/torchcodec/build.sh`

## Upstream Sources

- Upstream repository: <https://github.com/meta-pytorch/torchcodec>
- Contributing/build docs: <https://github.com/meta-pytorch/torchcodec/blob/main/CONTRIBUTING.md>
- PyPI: <https://pypi.org/project/torchcodec/0.10.0/>

## Version Constraints

Local package version is `0.10.0`. The `cpu` dependency group pins CPU Torch
2.10.0 in the package lock. Qualify Python 3.12 and 3.13 independently.

```bash
PAI_DEPS_DOCKER_CUDA_VERSION=cpu \
PAI_DEPS_BUILD_ENV='CMAKE_BUILD_PARALLEL_LEVEL=2 MAX_JOBS=2' \
    just build package torchcodec 0.10.0 3.12 2.10
```

Repeat with Python `3.13`. CPU builds use Ubuntu 22.04 without NVIDIA runtime
access and produce the `+cpu.torch210` local version. They still require
FFmpeg shared libraries at runtime; these are not bundled into the wheel.
Do not relabel the resulting Linux wheel as manylinux without ABI auditing.

## Build Environment

The package descriptor supplies the FFmpeg development package inventory for
Docker image preparation. The non-root build script sets `pybind11_DIR`, sets
`I_CONFIRM_THIS_IS_NOT_A_LICENSE_VIOLATION=1`, sets `ENABLE_CUDA=0` for CPU builds
(`1` otherwise), and builds
from `git+https://github.com/meta-pytorch/torchcodec.git`.

The package descriptor marks this as requiring license review so agents cannot
silently carry the acknowledgement flag without a visible release-review note.

## OOM Controls

Use CMake's standard throttle:

```dotenv
CMAKE_BUILD_PARALLEL_LEVEL=1
MAX_JOBS=1
TORCH_CUDA_ARCH_LIST=9.0
```

## Smoke Test

Generate a tiny MP4, then:

```bash
python - <<'PY'
from torchcodec.decoders import VideoDecoder
d = VideoDecoder("tiny.mp4", device="cpu")
frame = d[0]
print(frame.shape)
PY
```

Add CUDA decode smoke only when the wheel is intended to expose CUDA decode.

## Known Risks

- Existing index coverage is narrow and aarch64-focused.
- Root dev Torch can differ from the Torch version intended for torchcodec
  build compatibility; do not treat a lock update as build proof.
- The compiler, FFmpeg libraries, and base image come from the build image;
  only Python build dependencies are locked. Inspect ELF dependencies and run
  actual decoding on each target Python before publishing.

## Future Fixes

- Add package docs for the legal/license acknowledgement.
- Add a generated tiny-video fixture for smoke tests.

## Research Notes

Imported from upstream docs/source and read-only package research on
2026-06-27. No Docker builds or package builds were run.
