# torchcodec Build Notes

Status: historical.
Research date: 2026-06-27.

## Status

`torchcodec` is retained for historical media wheel documentation. Version
compatibility is tied closely to Torch.

## Local Build Entry Point

- Package descriptor: `pai-package.toml`
- Build script: `packages/torchcodec/build.sh`

## Upstream Sources

- Upstream repository: <https://github.com/meta-pytorch/torchcodec>
- Contributing/build docs: <https://github.com/meta-pytorch/torchcodec/blob/main/CONTRIBUTING.md>
- PyPI: <https://pypi.org/project/torchcodec/0.9.1/>

## Version Constraints

Local package version is `0.9.1`. Upstream compatibility notes pair
torchcodec `0.9` with Torch `2.9` and Python `>=3.10, <=3.14`.

## Build Environment

The package descriptor supplies the FFmpeg development package inventory for
Docker image preparation. The non-root build script sets `pybind11_DIR`, sets
`I_CONFIRM_THIS_IS_NOT_A_LICENSE_VIOLATION=1`, sets `ENABLE_CUDA=1`, and builds
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

## Future Fixes

- Add package docs for the legal/license acknowledgement.
- Add a generated tiny-video fixture for smoke tests.

## Research Notes

Imported from upstream docs/source and read-only package research on
2026-06-27. No Docker builds or package builds were run.
