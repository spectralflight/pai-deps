set shell := ["bash", "-c"]

check_dir := source_directory()
repo := check_dir + "/../.."
version := `awk -F'"' '/^version = / { print $2; exit }' ../../pyproject.toml`
tag := "v" + version
export UV_CACHE_DIR := env_var_or_default("UV_CACHE_DIR", repo + "/tmp/uv-cache")

# Show check recipes.
default:
    @just --justfile "{{ source_file() }}" --list

# Install system tools and the Python version specified in .python-version.
setup:
    cd "{{ repo }}" && mise install --locked
    cd "{{ repo }}" && mise exec -- uv python install

# Setup pre-commit hooks.
hooks: setup
    cd "{{ repo }}" && mise exec -- pre-commit install

# Run minimal Git safety pre-commit hooks.
pre-commit:
    cd "{{ repo }}" && mise exec -- pre-commit run -a

# Run linting and formatting hooks.
lint: docs shell shell-format ruff format

# Lint agent Markdown docs.
docs:
    cd "{{ repo }}" && mise exec -- just docs::lint

# Run shell checks on maintained shell scripts.
shell:
    cd "{{ repo }}" && mise exec -- shellcheck just/build/scripts/*.sh just/check/scripts/*.sh just/docs/scripts/*.sh just/release/scripts/*.sh just/deps/scripts/*.sh just/license/scripts/*.sh docker/entrypoint.sh

# Check shell script formatting.
shell-format:
    cd "{{ repo }}" && mise exec -- shfmt -d just/build/scripts/*.sh just/check/scripts/*.sh just/docs/scripts/*.sh just/release/scripts/*.sh just/deps/scripts/*.sh just/license/scripts/*.sh docker/entrypoint.sh

# Run Python linting.
ruff:
    cd "{{ repo }}" && mise exec -- ruff check just pai_deps

# Check Python formatting.
format:
    cd "{{ repo }}" && mise exec -- ruff format --check just pai_deps

# Check locked toolchain policy and Docker tool pins.
toolchain:
    cd "{{ repo }}" && mise exec -- uv run --frozen python just/check/scripts/check_toolchain.py

# Check package descriptors and package-local agent docs.
package-docs:
    cd "{{ repo }}" && mise exec -- uv run --frozen python just/package/scripts/check_package_docs.py

# Check package descriptors against package-local build scripts.
package-contracts:
    cd "{{ repo }}" && mise exec -- uv run --frozen python just/package/scripts/check_package_build_contracts.py

# Check release artifact sidecar schema on any staged wheel artifacts.
release-artifacts:
    cd "{{ repo }}" && mise exec -- uv run --frozen python just/license/scripts/write_wheel_legal_sidecars.py --allow-empty 'tmp/build/**/*.whl'
    cd "{{ repo }}" && mise exec -- uv run --frozen python just/release/scripts/check_release_artifacts.py --allow-empty 'tmp/build/**/*.whl'

# Check attribution drift and staged wheel license metadata.
legal:
    cd "{{ repo }}" && mise exec -- just license::audit

# Type-check maintained Python code.
typecheck:
    cd "{{ repo }}" && mise exec -- uv run --frozen pyrefly check

# Run focused unit tests.
unit:
    cd "{{ repo }}" && mise exec -- uv run --frozen python -m pytest just/build/scripts/build-package_test.py just/build/scripts/docker-build-package_test.py just/build/scripts/docker-entrypoint_test.py just/build/scripts/docker-run_test.py just/check/scripts/check_toolchain_test.py just/deps/scripts/uv-audit_test.py just/package/scripts/check_package_build_contracts_test.py just/package/scripts/check_package_docs_test.py just/release/scripts/check_docs_indices_test.py just/release/scripts/check_index_manifests_test.py just/release/scripts/check_release_artifacts_test.py just/release/scripts/scan_release_artifacts_test.py just/release/scripts/write_release_ledger_test.py just/license/scripts/write_wheel_legal_sidecars_test.py pai_deps/build_test.py pai_deps/package_metadata_test.py pai_deps/cli/copy_release_assets_test.py pai_deps/cli/create_index_test.py pai_deps/cli/package_info_test.py pai_deps/build_tools/write_build_provenance_test.py

# Check that existing package indices were not modified.
index-guard base='origin/main':
    cd "{{ repo }}" && mise exec -- uv run --frozen python just/release/scripts/check_docs_indices.py --base {{ quote(base) }}

# Check that stable index manifests are append-only.
manifest-guard base='origin/main':
    cd "{{ repo }}" && mise exec -- uv run --frozen python just/release/scripts/check_index_manifests.py --base {{ quote(base) }}

# Generate a temporary package index.
index-smoke index_name=tag:
    cd "{{ repo }}" && mise exec -- uv run --frozen pai-deps-create-index --wheels-file=wheels.txt -o "tmp/docs/{{ index_name }}" --index-name {{ quote(index_name) }}

# Run the standard local test lane.
test: lint toolchain package-docs package-contracts typecheck unit index-smoke

# Run fast local checks without mutating hooks.
fast: shell shell-format ruff format toolchain package-docs package-contracts legal typecheck unit index-guard manifest-guard

# Scan tracked source files for leaked secrets.
secrets:
    cd "{{ repo }}" && mise exec -- ./just/check/scripts/gitleaks-tracked.sh

# Scan Git history for leaked secrets.
history-secrets:
    cd "{{ repo }}" && mise exec -- gitleaks git --redact --no-banner --log-opts=--all .

# Run dependency and secret security checks.
security: secrets
    cd "{{ repo }}" && mise exec -- ./just/deps/scripts/uv-audit.sh --frozen

# Run the full local check ladder.
all: fast security index-smoke

# Run checks that do not start Docker containers, package builds, or GPU work.
no-gpu: fast security index-smoke
