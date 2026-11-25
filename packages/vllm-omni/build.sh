export VLLM_OMNI_TARGET_DEVICE=cuda
export VLLM_OMNI_VERSION_OVERRIDE="${PACKAGE_VERSION}"
pai_deps_uv_build_wheel --python "${VIRTUAL_ENV}/bin/python" --no-build-isolation "${PAI_DEPS_SOURCE_DIR:?Set a pinned local source directory}" "$@"
