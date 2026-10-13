# PS5 ReXGlue Template

A starting point for putting ReXGlue recompilations of Xbox 360 games on jailbroken
PS5 consoles, as native homebrew titles. It is what
[Spider-Man: Edge of Time for PS5](https://github.com/KongaTime/PS5_EdgeOfTimeTitle)
was built with, made reusable. That game is included as the worked example,
`games/edgeoftime/`.

The game's PowerPC code is recompiled ahead of time to x86-64 by ReXGlue. The ReXGlue
runtime, with its PS5 target ([KongaTime/rexglue-sdk](https://github.com/KongaTime/rexglue-sdk)),
runs it on the console. Graphics go through Vulkan on RADV, and sound and the
DualSense through the console's own services.

## What it gives you

- **The title:**
  - the console start-up (klog, the pad, the splash);
  - the entry that runs a ReXGlue app;
  - start-up lines in a results file you can read over FTP;
  - a heartbeat that tells a hang from a crash;
  - crash reports with backtraces, from the runtime.
- **The build:** one command builds a game into a title folder.
  - It links the runtime, RADV and the platform layer.
  - It links DLL modules into the title (the console can't load them).
  - It binds the C library names the console lacks and refuses imports that would
    be null at run time.
  - It stages every part's licence beside `eboot.bin`.
- **A test app** that checks the window, guest memory and sound on the console before
  any game is involved.
- **Tools** for title art, deploying over FTP and packaging a release zip for
  players.
- **[PORTING.md](PORTING.md):** how to bring a game over, with everything Edge of Time
  ran into along the way.

## What works today

| | |
| --- | --- |
| Games with their own renderer (plume and XenosRecomp shaders, like Edge of Time) | yes: Edge of Time is playable from beginning to end |
| Games on ReXGlue's emulated Xbox 360 GPU (most ReXGlue projects) | **not yet**: the runtime's emulated GPU still needs its PS5 changes (see PORTING.md) |

## Quick start

Check out the stack beside this repository and build it once:

```bash
git clone https://github.com/KongaTime/PS5_ReXGlueTemplate
PS5_ReXGlueTemplate/tools/bootstrap.sh     # clones rexglue-sdk, PS5_Vulkan, PS5_Mesa, PS5_PayloadSDK beside it
cd PS5_ReXGlueTemplate
tools/build-rexglue.sh                     # the ReXGlue runtime for the PS5
tools/build.sh                             # the test app, into dist/PPSA99001/
```

Copy `dist/PPSA99001/` to `/data/homebrew/` on the console. Launch **ReXGlue Test**
and read `title-results.txt` in its folder. Then follow [PORTING.md](PORTING.md) for
your game:

```bash
GAME=games/<name> tools/build.sh                 # the game, into dist/<TITLE_ID>/
tools/package-release.py games/<name> v1.0.0     # the zip players download
```

**What you need:**
- **To build:** a Linux machine (built on Ubuntu) with clang 20 or later and lld,
  CMake, Ninja and Python 3, plus ReXGlue's host tools at
  `nightly-20261002-bd833a2a` for codegen.
- **On the console:** etaHEN, [ShadowMountPlus](https://github.com/drakmor/ShadowMountPlus)
  (to put `/data/homebrew` titles on the home screen) and an FTP server.

## Layout

```
CMakeLists.txt          the title's build
cmake/rexglue-ps5.cmake the runtime, and the helpers a game builds with
src/                    the start-up, the platform layer, the test app
sce_sys/                the test app's title ID, name and icon
games/<name>/           a game: game.cmake, sce_sys/, notices.json, its release files
tools/                  build, link, deploy, title art, release, the runtime build
```

## Credits

- **[ReXGlue SDK](https://github.com/rexglue/rexglue-sdk):** the Xbox 360 recompiler
  and runtime.
- **The Simpsons Game PS5 port:**
  [LoZazaMastro's TheSimpsonsGame-PS5-Builder](https://github.com/LoZazaMastro/TheSimpsonsGame-PS5-Builder),
  built on YesterMester's [TheSimpsonsGameRecomp](https://github.com/YesterMester/TheSimpsonsGameRecomp).
  It was the first ReXGlue game on the PS5, and the runtime's PS5 app layer is ported
  from it.
- **[EdgeOfTimeRecompiled](https://github.com/goliathret/EdgeOfTimeRecomp)** (created
  by Graine25): the recompilation the worked example is built from.
- **[Xenia](https://github.com/xenia-project/xenia):** the Xbox 360 work under all of
  this.
- **[PS5 Vulkan Template](https://github.com/mihawk-99/PS5_VulkanTemplate)**
  (mihawk-99): the platform layer, the link and the console tools this template
  started from. With it: PS5_Vulkan, PS5_Mesa (Mesa's RADV) and the
  [PS5 payload SDK](https://github.com/ps5-payload-dev/sdk).
- **[etaHEN](https://github.com/etaHEN/etaHEN)** and
  **[ShadowMountPlus](https://github.com/drakmor/ShadowMountPlus)** (drakmor).

Template: [KongaTime](https://github.com/KongaTime). Made with Claude Code, an AI
coding assistant from Anthropic, which wrote most of the code. It was tested on a
real PS5 throughout.

## Licence

The template's own code is MIT (`LICENSE.md`). A built title links the PS5 platform
layer and PS5_Vulkan, which are GPL-3.0-or-later, so a title as distributed is under
GPL-3.0-or-later as a whole. `licenses/` beside each `eboot.bin` lists every part.

Not affiliated with or endorsed by Sony Interactive Entertainment, Microsoft or any
game's publisher. Use only games you own.
