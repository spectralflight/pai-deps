set shell := ["bash", "-c"]

build_dir := source_directory()
repo := build_dir + "/../.."
scripts := build_dir + "/scripts"

# Show build recipes.
default:
    @just --justfile "{{ source_file() }}" --list

# Build a package inside Docker; PAI_DEPS_DOCKER_CUDA_VERSION=cpu selects CPU.
package package_name package_version python_version torch_version output_dir='tmp/build':
    cd "{{ repo }}" && mise exec -- "{{ scripts }}/docker-build-package.sh" {{ quote(package_name) }} {{ quote(package_version) }} {{ quote(python_version) }} {{ quote(torch_version) }} {{ quote(output_dir) }}

# Build the dummy package inside Docker.
dummy: (package "cosmos-dummy" "0.1.0" "3.12" "2.9" "tmp/build")

# Build natten inside Docker.
natten package_version='0.21.6.dev6' python_version='3.12' torch_version='2.9':
    cd "{{ repo }}" && mise exec -- "{{ scripts }}/docker-build-package.sh" natten {{ quote(package_version) }} {{ quote(python_version) }} {{ quote(torch_version) }} tmp/build

# Check Docker tool pins against mise.lock.
tool-versions-check:
    cd "{{ repo }}" && mise exec -- uv run --frozen python just/check/scripts/check_toolchain.py --docker-only

# Run the docker container for a CUDA version.
docker-shell cuda_version='12.8.1':
    cd "{{ repo }}" && mise exec -- "{{ scripts }}/docker-run.sh" --cuda-version {{ quote(cuda_version) }}

# Run the CUDA 12.6 docker container.
cu126:
    just --justfile "{{ source_file() }}" docker-shell 12.6.3

# Run the CUDA 12.8 docker container.
cu128:
    just --justfile "{{ source_file() }}" docker-shell 12.8.1

# Run the CUDA 12.9 docker container.
cu129:
    just --justfile "{{ source_file() }}" docker-shell 12.9.1

# Run the CUDA 13.0 docker container.
cu130:
    just --justfile "{{ source_file() }}" docker-shell 13.0.2
