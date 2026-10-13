#!/usr/bin/env bash
# PS5 ReXGlue Template - build the title into dist/<TITLE_ID>/.
#
#   tools/build.sh                         the test app (no game): ReXGlue Test
#   GAME=games/<name> tools/build.sh       a game, from its folder
#
# Configures the title with the payload SDK's CMake toolchain (once per game,
# in build/title-<name>), compiles what changed, links with the ReXGlue
# runtime and RADV, and packages the title folder (tools/link-title.sh).
#
#   PS5_VULKAN_DIR   the PS5_Vulkan checkout (default ../PS5_Vulkan): the RADV
#                    release archive, the link recipe, the native tool and libc.prx
#   PS5_CLANG        the host clang the compiler wrappers drive (default: clang)
#
# The runtime must be built first (tools/build-rexglue.sh).
#
# Copyright (C) 2026 Mihawk, KongaTime
# SPDX-License-Identifier: MIT
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
vulkan=$(cd -- "${PS5_VULKAN_DIR:-$root/../PS5_Vulkan}" && pwd)
sdk=$(bash "$root/tools/setup-sdk.sh")
game=${GAME:-}
if [[ -n $game ]]; then
    game=$(cd -- "$game" 2>/dev/null && pwd) || { echo "no game folder: $GAME" >&2; exit 2; }
    build="$root/build/title-$(basename "$game")"
else
    build="$root/build/title-test-app"
fi
ninja=$(command -v ninja || echo "$HOME/.local/bin/ninja")
export PS5_CLANG=${PS5_CLANG:-$(command -v clang || true)}
if [[ ! -f $build/build.ninja ]]; then
    mkdir -p "$build"
    cmake -S "$root" -B "$build" -G Ninja -DCMAKE_MAKE_PROGRAM="$ninja" \
        -DCMAKE_TOOLCHAIN_FILE="$sdk/toolchain/prospero.cmake" -DTITLE_GAME="$game" \
        -DPS5_VULKAN_DIR="$vulkan" -DCMAKE_BUILD_TYPE=Release -DCMAKE_VERBOSE_MAKEFILE=OFF > "$build.configure.log" 2>&1 \
        || { cat "$build.configure.log" >&2; exit 1; }
fi
"$ninja" -C "$build" link
