# LightGlue Build Notes

Status: candidate.
Research date: 2026-11-16.

## Status

Pure-Python wheel for the pinned public LightGlue source. Building does not load
torch or use a GPU. Model execution requires the declared runtime dependencies.

## Local Build Entry Point

```bash
just build package lightglue 0.0.post20261116 3.12 2.9
```

Descriptor: `pai-package.toml`. Script: `build.sh`.

## Upstream Sources

- <https://github.com/cvg/LightGlue/tree/eb42fee2d71449efb0aa5c10549752b5d75384d8>

## Version Constraints

Upstream calls this source version `0.0`. Packaging revision `0.0.post20261116`
distinguishes the pinned wheel. The shared builder appends its build-context
CUDA/torch suffix; the resulting wheel is pure Python and not ABI-specific.

## Build Environment

Use the Docker builder with locked setuptools and wheel. The package declares
`requires_torch = false`; scientific dependencies remain runtime dependencies.

## OOM Controls

No CUDA compilation or model loading occurs in this build.

## Smoke Test

Check wheel metadata, license and `lightglue` source files. In the locked runtime,
import `lightglue` and instantiate its model using the provider checkpoint cache.
Model inference is separate qualification, not a wheel-build side effect.

## Known Risks

The source dependency previously installed from Git must be replaced with this
exact wheel version/hash in consumer locks; do not leave the Git source override.

## Future Fixes

Record the build result and separately qualify model execution after packaging.

## Research Notes

Read upstream metadata and Apache-2.0 license at the pinned revision. No package
source modifications are required. Model checkpoints are not included in wheels.
