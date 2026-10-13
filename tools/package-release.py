#!/usr/bin/env python3
"""PS5 ReXGlue Template - a game's release zip, ready for players.

    tools/package-release.py games/<name> VERSION

Zips the built title folder (dist/<TITLE_ID>/, from tools/build.sh) as players
install it: release/<zip name>, holding

  HOW-TO-INSTALL.txt          the game folder's HOW-TO-INSTALL.txt ({version} filled in)
  <TITLE_ID>/                 the title folder: eboot.bin, sce_sys/, sce_module/, the notices
  <TITLE_ID>/<file>...        the files the game lists beside eboot.bin (release.json)
  <TITLE_ID>/gamedata/        empty but for the game folder's gamedata-note.txt, which
                              tells players what to put there from their own copy

The game folder's release.json names the zip and the extra files:

  {"zip": "MyGame-PS5-{version}.zip",
   "files": [["MyGameRecomp/generated/shader-cache.zst", "shader-cache.zst"]]}

(file sources relative to the folder this repository is in). No game files go
in: the title folder never holds any, and gamedata/ gets only the note.

Copyright (C) 2026 KongaTime
SPDX-License-Identifier: MIT
"""
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: tools/package-release.py games/<name> VERSION")
    game, version = Path(sys.argv[1]).resolve(), sys.argv[2]
    param = json.loads((game / "sce_sys/param.json").read_text())
    title_id = param["titleId"]
    app = ROOT / "dist" / title_id
    if not (app / "eboot.bin").exists():
        sys.exit(f"no {app}/eboot.bin: run GAME={sys.argv[1]} tools/build.sh first")
    if (app / "gamedata").exists():
        sys.exit(f"{app} holds a gamedata/ folder: the title folder must hold no game files")
    release = json.loads((game / "release.json").read_text())
    for name in ("HOW-TO-INSTALL.txt", "gamedata-note.txt"):
        if not (game / name).exists():
            sys.exit(f"no {game / name}")
    components = json.loads((app / "licenses/components.json").read_text())
    dirty = [p["id"] for p in components if p["source"].get("dirty")]
    if dirty:
        print(f"warning: built from uncommitted changes in: {', '.join(dirty)}; commit and build again "
              "so the notices name the source a release ships", file=sys.stderr)

    out = ROOT / "release" / release["zip"].format(version=version)
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        how_to = (game / "HOW-TO-INSTALL.txt").read_text().replace("{version}", version)
        z.writestr("HOW-TO-INSTALL.txt", how_to)
        for path in sorted(app.rglob("*")):
            if path.is_file():
                z.write(path, f"{title_id}/{path.relative_to(app)}")
        for source, name in release.get("files", []):
            source = (ROOT.parent / source).resolve()
            if not source.exists():
                sys.exit(f"no {source}, which release.json lists")
            # Already compressed files are stored as they are
            kind = zipfile.ZIP_STORED if source.suffix in (".zst", ".zip", ".png", ".dds") else zipfile.ZIP_DEFLATED
            z.write(source, f"{title_id}/{name}", compress_type=kind)
        z.writestr(f"{title_id}/gamedata/PUT-YOUR-GAME-FILES-HERE.txt", (game / "gamedata-note.txt").read_text())
    print(f"==> {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
