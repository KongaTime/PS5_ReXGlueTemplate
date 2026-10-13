#!/usr/bin/env python3
"""PS5 ReXGlue Template - a game's home-screen art, kept out of git.

    tools/title-art.py games/<name>

The art is usually the game's own (its cover, its key art), so like the game's
files it stays on the machine that builds the title: games/<name>/title-art/ is
ignored by git, and tools/link-title.sh lays its sce_sys/ over the game's
sce_sys/ in the title folder. Put the sources there, run this, and build:

- title-art/icon-source.*        -> sce_sys/icon0.png, 512x512
- title-art/background-source.*  -> sce_sys/pic0.dds and pic1.dds, the
  background the home screen shows behind the title, 3840x2160 (scaled to
  cover, centred), as the console takes it: DDS with a DX10 header, BC7_UNORM,
  one level, straight alpha

Needs Pillow and etcpak (pip install etcpak).

The console keeps the name and art it read when the title was registered
(ShadowMountPlus registers a /data/homebrew title once), so changing sce_sys/
in place does not show on the home screen. What works: upload a folder named
after the title ID, holding only the new sce_sys/, with ps5upload, overriding
the installed title; the title registers again with the new name and art, and
the rest of its folder stays as it was.

Copyright (C) 2026 KongaTime
SPDX-License-Identifier: MIT
"""

import struct
import sys
from pathlib import Path

import etcpak
from PIL import Image

if len(sys.argv) != 2 or not (Path(sys.argv[1]) / "game.cmake").exists():
    sys.exit("usage: tools/title-art.py games/<name>")
ART = Path(sys.argv[1]).resolve() / "title-art"
SCE_SYS = ART / "sce_sys"

WIDTH, HEIGHT = 3840, 2160


def source(stem):
    found = sorted(ART.glob(stem + ".*"))
    if not found:
        sys.exit(f"title-art.py: no {ART / stem}.* (a .png, .jpg or .webp)")
    return found[0]


def cover(image, width, height):
    """Scaled to fill width x height, the overflow cut evenly from both sides."""
    scale = max(width / image.width, height / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def dds_bc7(image):
    rgba = image.convert("RGBA")
    blocks = etcpak.compress_bc7(rgba.tobytes(), rgba.width, rgba.height)
    linear_size = (rgba.width // 4) * (rgba.height // 4) * 16
    assert len(blocks) == linear_size

    flags = 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | 0x80000  # caps, height, width, pixel format, mip count, linear size
    header = struct.pack("<4sIIIIIII11I", b"DDS ", 124, flags, rgba.height, rgba.width, linear_size, 1, 1, *([0] * 11))
    pixel_format = struct.pack("<II4sIIIII", 32, 0x4, b"DX10", 0, 0, 0, 0, 0)
    caps = struct.pack("<IIIII", 0x1000, 0, 0, 0, 0)
    dx10 = struct.pack("<IIIII", 98, 3, 0, 1, 1)  # BC7_UNORM, 2D, no flags, one image, straight alpha
    return header + pixel_format + caps + dx10 + blocks


def main():
    SCE_SYS.mkdir(parents=True, exist_ok=True)
    icon = cover(Image.open(source("icon-source")).convert("RGB"), 512, 512)
    icon.save(SCE_SYS / "icon0.png", optimize=True)
    print(f"wrote {SCE_SYS / 'icon0.png'}")

    background = cover(Image.open(source("background-source")).convert("RGB"), WIDTH, HEIGHT)
    data = dds_bc7(background)
    for name in ("pic0.dds", "pic1.dds"):
        (SCE_SYS / name).write_bytes(data)
        print(f"wrote {SCE_SYS / name} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
