# NVIDIA ViPE Build Notes

Status: candidate.
Research date: 2026-11-16.

## Status

Builds the public ashawkey ViPE fork with the `pose_only` pipeline. The upstream
PyPI 1.2.0 source does not include this pipeline. No internal source is used.

## Local Build Entry Point

```bash
PAI_DEPS_BUILD_ENV='MAX_JOBS=2 TORCH_CUDA_ARCH_LIST=9.0;12.0' \
  just build package nvidia-vipe 1.2.0.post20260710 3.12 2.9
```

The package descriptor is `pai-package.toml`; compilation is in `build.sh`.

## Upstream Sources

- Public fork: <https://github.com/ashawkey/vipe>
- Pinned source: <https://github.com/ashawkey/vipe/tree/43fa1effc9baf329c5b365bcf06ddb2ef6627662>
- Original project: <https://github.com/nv-tlabs/vipe>

## Version Constraints

The fork identifies itself as 1.2.0. The packaging version
`1.2.0.post20260710` distinguishes this pinned fork from the PyPI source.
The builder appends the CUDA and torch compatibility suffix. Initial target:
CPython 3.12, torch 2.9, CUDA 12.8, Linux x86_64.

## Build Environment

Uses the shared Docker builder, setuptools>=77, wheel, ninja, CUDA torch and
nvcc. The single `vipe_ext` extension includes bundled LieTorch sources.
`USE_SYSTEM_EIGEN=1` uses the builder's `libeigen3-dev` instead of downloading
headers during compilation. Runtime installation needs the wheel's declared
Python dependencies, model checkpoints and a compatible NVIDIA driver.

## OOM Controls

`MAX_JOBS` defaults to two. Initial architecture targets are Hopper 9.0 and
Blackwell 12.0. Reduce the architecture list before widening concurrency.

## Smoke Test

In a fresh, matching runtime environment, import `vipe_ext`, run `vipe --help`,
and check that `vipe/_configs/pipeline/pose_only.yaml` is packaged. GPU
qualification must run `vipe infer VIDEO --pipeline pose_only --output OUTPUT`
and verify its pose archive; imports alone do not establish inference support.

## Known Risks

- Compiled extensions are tied to the selected torch/CUDA ABI.
- The fork includes third-party model code; retain license and notice files.
- Checkpoint downloads are separate from the wheel and use provider caches.
- A wheel build does not establish equality with another runtime environment.

## Future Fixes

Record verified build and runtime results after the candidate is exercised.

## Research Notes

Read the pinned public source and its `pose_only` pipeline. PyPI 1.2.0 has an
sdist only and lacks this fork's pipeline. No build or inference is claimed yet.
