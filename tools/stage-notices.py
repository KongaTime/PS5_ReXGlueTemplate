#!/usr/bin/env python3
"""PS5 ReXGlue Template - the notices a title folder carries: LEGAL.txt and licenses/.

    stage-notices.py APP_DIR VULKAN_DIR RADV_ARCHIVE TITLE_DIR

Called by tools/link-title.sh after it packages the title. It writes, beside
eboot.bin:

  LEGAL.txt                 no piracy; what the title is licensed under; trademarks
  licenses/README.txt       the same notice, then every part: its licence, copyright and source
  licenses/components.json  the same parts as data, each with the revision it was built from
  licenses/<part>/...       the licence texts each part requires

The parts are the template's own code, the ReXGlue runtime and the libraries it
links, the PS5 platform layer, PS5_Vulkan, RADV and the LLVM runtime, then the
game's own (TITLE_DIR/notices.json, when the game has one). Every text is read
at the revision the title was built from (git show), not from a working tree,
except a submodule's, which is read from its checkout and recorded with its
revision. A part whose repository has uncommitted changes is recorded as "dirty".

A game's notices.json is a list of parts:

  [{"id": "game", "name": "...", "licence": "...", "copyright": ["..."],
    "repo": "../MyGameRecomp",            (relative to this repository's folder)
    "texts": [["LICENSE", "LICENSE"]],    (path in the repository, name in licenses/<id>/)
    "submodule_texts": [["thirdparty/lib/LICENSE", "lib-LICENSE"]]}]

Copyright (C) 2026 Mihawk, KongaTime
SPDX-License-Identifier: MIT
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


def revision(repo):
    """The repository's HEAD, its remote, and whether its tracked files differ from it."""
    try:
        rev = git(repo, "rev-parse", "HEAD")
    except subprocess.CalledProcessError:
        rev = None  # a repository with no commit yet
    dirty = rev is None or bool(git(repo, "status", "--porcelain", "--untracked-files=no"))
    remotes = git(repo, "remote").split()
    name = "origin" if "origin" in remotes else (remotes[0] if remotes else None)
    remote = git(repo, "remote", "get-url", name) if name else "(no remote yet)"
    return rev, dirty, remote.removesuffix(".git")


def pinned(script, name):
    """A revision a setup script pins ("name=<sha>")."""
    m = re.search(rf"^{name}=([0-9a-f]{{40}})", (ROOT / script).read_text(), re.M)
    return m.group(1) if m else None


def write_text(dest, repo, rev, path):
    """A file of a repository at a revision, into the licenses folder."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = subprocess.run(["git", "-C", str(repo), "show", f"{rev}:{path}"], capture_output=True, check=True).stdout
    dest.write_bytes(data)


def submodule_revision(repo, path):
    """The revision a repository's submodule is checked out at."""
    parts = Path(path).parts
    for i in range(len(parts), 0, -1):
        sub = Path(repo, *parts[:i])
        if (sub / ".git").exists():
            return str(Path(*parts[:i])), git(sub, "rev-parse", "HEAD")
    return None, None


def copy_text(dest, source):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)


def write_tree(dest, repo, rev, path):
    """A folder of a repository at a revision (Mesa's licenses/)."""
    dest.mkdir(parents=True, exist_ok=True)
    tar = subprocess.run(["git", "-C", str(repo), "archive", rev, path], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(dest), "--strip-components", str(len(Path(path).parts))], input=tar, check=True)


LEGAL = """{name} - legal use
{rule}

PIRACY IS NOT CONDONED. No game files, BIOS files, console firmware or
decryption keys come with this title, and none will ever be provided or
linked to. A game's data comes from your own copy of it. Use only games you
own and files from hardware you own. Downloading or sharing games, BIOS files,
firmware or keys you do not own is piracy: do not do it, and do not ask for
help with it.

Licences: the title's own code is MIT. The ReXGlue runtime is BSD-3-Clause,
and links libraries under their own licences, FFmpeg and libmspack under the
LGPL. It links the PS5 platform layer and PS5_Vulkan, which are
GPL-3.0-or-later, so the title as distributed is under GPL-3.0-or-later as a
whole, and its complete source is offered with it. Every part, its licence and
its source are listed in licenses/README.txt.

Not affiliated with or endorsed by Sony Interactive Entertainment.
"PlayStation" and "PS5" are trademarks of Sony Interactive Entertainment Inc.
Vulkan is a registered trademark of the Khronos Group Inc.; the RADV port is
not a conformant product (its conformanceVersion is 0.0.0.0).
"""

# The libraries the runtime's archives carry (tools/build-rexglue.sh), each
# with its licence text in the fork's thirdparty/
REXGLUE_LIBRARIES = [
    ("fmt", "MIT", "thirdparty/fmt/LICENSE"),
    ("spdlog", "MIT", "thirdparty/spdlog/LICENSE"),
    ("FFmpeg (libavcodec, libavutil)", "LGPL-2.1-or-later", "thirdparty/FFmpeg/COPYING.LGPLv2.1"),
    ("libmspack", "LGPL-2.1", "thirdparty/libmspack/libmspack/COPYING.LIB"),
    ("o1heap", "MIT", "thirdparty/o1heap/LICENSE"),
    ("xxHash", "BSD-2-Clause", "thirdparty/xxHash/LICENSE"),
    ("aes_128", "MIT", "thirdparty/aes_128/LICENSE"),
    ("Dear ImGui", "MIT", "thirdparty/imgui/LICENSE.txt"),
    ("toml++", "MIT", "thirdparty/tomlplusplus/LICENSE"),
    ("UTF8-CPP", "BSL-1.0", "thirdparty/utfcpp/LICENSE"),
    ("SIMDe", "MIT", "thirdparty/simde/COPYING"),
]


def main():
    app, vulkan, archive, title = (Path(a).resolve() for a in sys.argv[1:5])
    name = json.loads((title / "sce_sys/param.json").read_text())["localizedParameters"]["en-US"]["titleName"]
    out = app / "licenses"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    parts = []

    # The title: the template's own code (the start-up, the platform layer's
    # C side, the build) and volk
    rev, dirty, remote = revision(ROOT)
    for path, dest in (("LICENSE.md", "LICENSE.md"), ("third_party/volk/LICENSE.md", "volk-LICENSE.md")):
        if rev:
            write_text(out / "title" / dest, ROOT, rev, path)
        else:
            copy_text(out / "title" / dest, ROOT / path)
    parts.append(dict(
        id="title", name=f"{name}: the title's start-up and build (PS5 ReXGlue Template), with volk",
        licence="MIT", copyright=["Copyright (C) 2026 Mihawk", "Copyright (C) 2026 KongaTime", "volk's authors"],
        artifacts=["eboot.bin"], texts="licenses/title/",
        source=dict(kind="git", path=str(ROOT), remote=remote, revision=rev, dirty=dirty)))

    # The ReXGlue runtime, the fork with the PS5 target, and what it links
    rexglue = Path(os.environ.get("REXGLUE_SRC") or ROOT.parent / "rexglue-sdk").resolve()
    rrev, rdirty, rremote = revision(rexglue)
    write_text(out / "rexglue/LICENSE", rexglue, rrev, "LICENSE")
    submodules = {}
    for library, licence, path in REXGLUE_LIBRARIES:
        sub, sub_rev = submodule_revision(rexglue, path)
        copy_text(out / "rexglue" / (Path(path).parts[1] + "-" + Path(path).name), rexglue / path)
        if sub:
            submodules[sub] = dict(revision=sub_rev)
    parts.append(dict(
        id="rexglue", name="the ReXGlue runtime (KongaTime/rexglue-sdk, ReXGlue with the PS5 target), with "
                           + ", ".join(f"{lib} ({lic})" for lib, lic, _ in REXGLUE_LIBRARIES),
        licence="BSD-3-Clause (ReXGlue, with portions from Xenia); each library under its own, as listed",
        copyright=["Copyright (c) 2026 Tom Clay and the ReXGlue contributors", "the Xenia project",
                   "and each library's authors"],
        artifacts=["eboot.bin"], texts="licenses/rexglue/",
        source=dict(kind="git", path=str(rexglue), remote=rremote, revision=rrev, dirty=rdirty,
                    submodules=submodules)))

    # The payload SDK fork: its platform layer and headers
    sdk = Path(ROOT.parent / "PS5_PayloadSDK")
    sdk_rev = pinned("tools/setup-sdk.sh", "sdk_revision")
    write_text(out / "platform/GPL-3.0.txt", sdk, sdk_rev, "LICENSE")
    write_text(out / "platform/musl-regex-COPYRIGHT.txt", sdk, sdk_rev, "platform/src/regex/COPYRIGHT.musl")
    write_text(out / "platform/dlmalloc-SOURCE.txt", sdk, sdk_rev, "platform/src/dlmalloc/SOURCE")
    parts.append(dict(
        id="platform", name="the PS5 platform layer (libps5platform.a) and the SDK headers, from my payload SDK fork, "
                            "with musl's regex and dlmalloc",
        licence="GPL-3.0-or-later; musl's regex MIT; dlmalloc public domain",
        copyright=["Copyright (C) John Törnblom and the ps5-payload-dev contributors", "Copyright (C) 2026 Mihawk"],
        artifacts=["eboot.bin"], texts="licenses/platform/",
        source=dict(kind="git", path=str(sdk), remote="https://github.com/mihawk-99/PS5_PayloadSDK", revision=sdk_rev,
                    dirty=False)))

    # PS5_Vulkan: the link recipe, the CRT and its startup, the AGC imports, libc.prx
    vrev, vdirty, vremote = revision(vulkan)
    write_text(out / "ps5-vulkan/GPL-3.0.txt", vulkan, vrev, "LICENSE")
    parts.append(dict(
        id="ps5-vulkan", name="PS5_Vulkan: the RADV link recipe, the C runtime start-up, the AGC import stubs and "
                              "sce_module/libc.prx",
        licence="GPL-3.0-or-later", copyright=["Copyright (C) 2026 Mihawk"],
        artifacts=["eboot.bin", "sce_module/libc.prx"], texts="licenses/ps5-vulkan/",
        source=dict(kind="git", path=str(vulkan), remote=vremote, revision=vrev, dirty=vdirty)))

    # RADV: Mesa's Vulkan driver, from my PS5_Mesa fork, built by PS5_Vulkan
    provenance = (archive.parent.parent / "PROVENANCE.txt").read_text()
    mesa_rev = re.search(r"^revision: ([0-9a-f]{40})", provenance, re.M).group(1)
    radv_sdk = re.search(r"^sdk: ([0-9a-f]{40})", provenance, re.M)
    mesa = Path(ROOT.parent / "PS5_Mesa")
    write_text(out / "radv/Mesa-license.rst", mesa, mesa_rev, "docs/license.rst")
    write_tree(out / "radv/licenses", mesa, mesa_rev, "licenses")
    parts.append(dict(
        id="radv", name="RADV, Mesa's Vulkan driver (with ACO, NIR and Mesa's Vulkan runtime), from my PS5_Mesa fork",
        licence="MIT, with other licences stated per file (licenses/radv/Mesa-license.rst)",
        copyright=["Copyright the Mesa contributors (per-file notices in the source)"],
        artifacts=["eboot.bin"], texts="licenses/radv/",
        source=dict(kind="git", path=str(mesa), remote="https://github.com/mihawk-99/PS5_Mesa", revision=mesa_rev,
                    dirty=False, built_with_sdk=radv_sdk.group(1) if radv_sdk else None)))

    # The LLVM runtime the SDK links in
    llvm = ROOT.parent / "PS5_LLVM/llvm/LICENSE.TXT"
    if llvm.exists():
        (out / "llvm-runtime").mkdir()
        shutil.copy2(llvm, out / "llvm-runtime/LICENSE.TXT")
    parts.append(dict(
        id="llvm-runtime", name="LLVM libc++, libc++abi, libunwind and compiler-rt builtins (linked into eboot.bin)",
        licence="Apache-2.0 WITH LLVM-exception",
        copyright=["Copyright (c) 2003-2026 University of Illinois at Urbana-Champaign and the LLVM project contributors"],
        artifacts=["eboot.bin"], texts="licenses/llvm-runtime/",
        source=dict(kind="fixed", revision="ps5-payload-dev SDK v0.42 release archives",
                    url="https://github.com/ps5-payload-dev/sdk/releases/tag/v0.42")))

    # The game's own parts
    notices = title / "notices.json"
    if notices.exists():
        for part in json.loads(notices.read_text()):
            repo = (ROOT.parent / part["repo"]).resolve() if not Path(part["repo"]).is_absolute() else Path(part["repo"])
            grev, gdirty, gremote = revision(repo)
            for path, dest in part.get("texts", []):
                write_text(out / part["id"] / dest, repo, grev, path)
            submodules = {}
            for path, dest in part.get("submodule_texts", []):
                sub, sub_rev = submodule_revision(repo, path)
                copy_text(out / part["id"] / dest, repo / path)
                if sub:
                    submodules[sub] = dict(revision=sub_rev)
            parts.append(dict(
                id=part["id"], name=part["name"], licence=part["licence"], copyright=part["copyright"],
                artifacts=part.get("artifacts", ["eboot.bin"]), texts=f'licenses/{part["id"]}/',
                source=dict(kind="git", path=str(repo), remote=gremote, revision=grev, dirty=gdirty,
                            submodules=submodules)))

    (out / "components.json").write_text(json.dumps(parts, indent=1, ensure_ascii=False) + "\n")
    legal = LEGAL.format(name=name, rule="=" * (len(name) + 12))
    (app / "LEGAL.txt").write_text(legal)
    lines = [legal, "", "The parts of this title", "=======================", ""]
    for p in parts:
        src = p["source"]
        where = f'{src["remote"]} at {src["revision"]}' if src["kind"] == "git" else f'{src["revision"]}: {src["url"]}'
        lines += [p["name"], f'  licence:   {p["licence"]}', f'  copyright: {"; ".join(p["copyright"])}',
                  f'  in:        {", ".join(p["artifacts"])}', f'  texts:     {p["texts"]}', f'  source:    {where}', ""]
    (out / "README.txt").write_text("\n".join(lines) + "\n")
    dirty = [p["id"] for p in parts if p["source"].get("dirty")]
    print(f"==> notices: LEGAL.txt, licenses/ ({len(parts)} parts{'; dirty: ' + ', '.join(dirty) if dirty else ''})")


if __name__ == "__main__":
    main()
