#!/usr/bin/env bash
# PS5 ReXGlue Template - copy the built title folder to the console over FTP.
#
#   tools/deploy.sh                    the test app
#   GAME=games/<name> tools/deploy.sh  a game
#
# Uploads dist/<TITLE_ID>/ to /data/homebrew/<TITLE_ID>/ through PS5_Vulkan's
# tools/deploy-title-folder.py, which reads the console's address from
# PS5_Vulkan's .env (PS5_HOST, FTP_PORT). Files already there and unchanged are
# skipped; eboot.bin is always sent. A game's own files (gamedata/, its saves)
# are never touched.
#
# Copyright (C) 2026 Mihawk, KongaTime
# SPDX-License-Identifier: MIT
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
vulkan=$(cd -- "${PS5_VULKAN_DIR:-$root/../PS5_Vulkan}" && pwd)
title=${GAME:-$root}
title_id=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["titleId"])' "$title/sce_sys/param.json")
[[ -d $root/dist/$title_id ]] || { echo "no dist/$title_id: run tools/build.sh first" >&2; exit 2; }
exec python3 "$vulkan/tools/deploy-title-folder.py" --always eboot.bin "$root/dist/$title_id" "$@"
