# SAM2 Build Notes

Status: maintained.
Research date: 2026-06-27.

## Status

SAM2 is an active TransferBench dependency for video object tracking and
segmentation metrics. Package code and CUDA extensions as wheels; keep model
checkpoints external.

## Local Build Entry Point

- Package descriptor: `pai-package.toml`
- Build script: `packages/sam2/build.sh`
- Generic recipe: `just build package sam2 <version> <python> <torch> <output>`

## Upstream Sources

- Upstream repository: <https://github.com/facebookresearch/sam2>
- Install docs: <https://github.com/facebookresearch/sam2/blob/main/INSTALL.md>
- Upstream setup: <https://github.com/facebookresearch/sam2/blob/main/setup.py>

## Version Constraints

The public scorer uses the official PyPI 1.1.0 source archive, pinned by SHA256
in `build.sh`. Other source versions fail explicitly. The shared builder selects
the latest patch within the requested Torch major/minor and derives CUDA targets
from that Torch installation; do not override the architecture list.

## Build Environment

Important variables:

- `SAM2_BUILD_CUDA`: set `1` for TransferBench CUDA wheels.
- `SAM2_BUILD_ALLOW_ERRORS`: keep `0` for real builds.
- `CUDA_HOME`: expected by upstream CUDA extension discovery.
- `MAX_JOBS`: PyTorch extension parallelism throttle.

## OOM Controls

Start with:

```dotenv
MAX_JOBS=4
SAM2_BUILD_CUDA=1
SAM2_BUILD_ALLOW_ERRORS=0
```

`SAM2_BUILD_CUDA=0` can prove the Python packaging shape, but it is not a
TransferBench scorer proof.

## Smoke Test

After building a wheel in a matching Torch/CUDA environment:

```bash
python -m zipfile -l <wheel> | rg 'sam2/_C\\.so|sam2/configs/.+\\.yaml'
python -c "import sam2; print(sam2)"
```

The import smoke needs runtime dependencies such as Hydra installed from the
wheel metadata.

## Known Risks

- The default script revision is a pinned commit, so `PACKAGE_VERSION` and
  upstream source revision can drift if changed independently.
- A Python-only smoke wheel is easy to build but does not prove the CUDA
  extension used by TransferBench.

## Future Fixes

- Decide whether SAM2 should map versions to exact upstream tags/commits in the
  descriptor once the release cadence stabilizes.
- Add a small scorer-level fixture after the Grounded-SAM-2 helper path is wired
  into the eval project.

## Research Notes

Imported from official upstream docs and local transfer-wheel notes on
2026-06-27. A prior smoke build used single-arch `TORCH_CUDA_ARCH_LIST=12.0`
with `MAX_JOBS=4`.
