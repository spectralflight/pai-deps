# Agent Contract

Mode: yellowfield agent-only. Simplify aggressively, but preserve wheel output,
package-index, and release-asset contracts.

## Hard Rules

- Do not modify, delete, rewrite, reformat, or regenerate published package
  index files under `docs/**/index.html`.
- The only freely editable package index docs are indices whose
  `indices/<index-name>/manifest.json` has `stability: "unstable"`.
- Do not alter existing GitHub releases or replace existing release assets for
  stable indices.
- Publish new wheels for stable indices only as new release assets with unique
  filenames and hashes.
- Run wheel builds inside Docker. Do not build packages on the host.
- Do not start Docker containers, package builds, or GPU work while another
  package-build thread is active on the same one-GPU machine.
- Use committed lockfiles for tool and Python dependency resolution. Do not add
  committed workflows that use `uvx`, `uv tool install`, `uv run --with ...`,
  curl-piped installers, or `eget`.
- Use `spectralflight/...` branches for public GitHub work.

## Package Boundary

- Package-specific truth belongs under `packages/<name>`.
- Each package owns `pai-package.toml`, `build.sh`, `pyproject.toml`,
  `uv.lock`, and `agents/build-notes.md`.
- Shared importable code belongs in `pai_deps/`. Command implementations belong
  under the owning `just/*/scripts` module, and CI must call public `just`
  recipes rather than implementation scripts directly.
- Prefer shared parametrized tests over per-package boilerplate.

## Useful Commands

- `mise install --locked`: install pinned standalone tools.
- `pre-commit install`: install minimal local Git safety hooks for secrets,
  submodules, and large files.
- `just help`: list root and module recipes.
- `just no-gpu-check`: safe lane with no Docker, package build, or GPU use.
- `just check fast`: shell, Python, type, package, release, index, and manifest
  checks without audit or index smoke.
- `just check package-contracts`: validate package descriptors against
  package-local build scripts.
- `just deps lock-all` and `just deps upgrade-all`: refresh root and package
  lockfiles.
- `just package list` and `just package show <name>`: inspect package-local
  descriptors and agent docs.
- `just release create <index>`: generate a temporary package index.
- `just check history-secrets`: scan Git history before publishing a public
  cleanup branch.
- Release uploads generate legal/SBOM sidecars, write a release ledger, and scan
  wheels plus all sidecars for secrets before any GitHub writes.
- `just license::audit`: check attribution drift and staged wheel license
  metadata.

## Pointers

- `agents/agent-workflow.md`: locked tools, no-GPU checks, package workflow.
- `agents/agent-guide.md`: Docker build loop and package-build notes.
- `agents/legal-audit.md`: attribution, wheel-license, and package legal
  review checks.
- `agents/release-safety.md`: index and release invariants.
