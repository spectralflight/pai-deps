# vLLM-Omni Build Notes

Status: candidate.
Research date: 2026-11-03.

## Status

Local-source pure Python wheel build; runtime validation is separate.

## Local Build Entry Point

`build.sh` uses the shared uv wheel helper. Pin the source checkout before invoking it.

## Upstream Sources

https://github.com/vllm-project/vllm-omni

## Version Constraints

The selected source owns Python and runtime requirements. This build environment pins setuptools below 81 and setuptools-scm 10.2.1.

## Build Environment

Set `PAI_DEPS_SOURCE_DIR` to the pinned checkout inside the Docker repository mount. The script selects CUDA dependency metadata and the requested package version.

## OOM Controls

The package has no compiled extensions. Native dependencies require separate resource limits.

## Smoke Test

Install the wheel into the matching runtime. Verify imports, native dependency operators, and a small model-layer forward pass.

## Known Risks

A pure Python wheel does not establish CUDA architecture coverage of its dependencies. Local source contents and provenance require review before publication.

## Future Fixes

Record runtime validation for each target platform before treating the package as verified.

## Research Notes

Candidate source packaging path; no full-model inference claim.
