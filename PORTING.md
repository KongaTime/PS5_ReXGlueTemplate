# Porting a ReXGlue game to the PS5

This is how to bring a game that already has a ReXGlue recompilation for PC onto the
PS5 with this template. Spider-Man: Edge of Time (`games/edgeoftime/`) went this way
and is the worked example throughout.

You need your own copy of the game. Its files never go into a repository or a
release.

## 0. Is the game a good fit?

- **It needs a ReXGlue recompilation.** That means a PC project whose code comes from
  `rexglue codegen` and runs on the ReXGlue runtime. Recompilations built on other
  toolchains (XenonRecomp, N64Recomp) need their own runtime brought to the PS5
  first.
- **Graphics: check how the game draws.**
  - *Its own renderer* (like Edge of Time: plume, with the game's shaders recompiled
    by XenosRecomp): works today. Apply the PS5 patch to plume
    (`EdgeOfTimeRecomp/ps5/patches/plume-ps5.patch`).
  - *ReXGlue's emulated Xbox 360 GPU* (most ReXGlue projects): **not yet supported.**
    The fork's runtime leaves the emulated GPU out on the PS5. The Simpsons Game's
    PS5 port ([TheSimpsonsGame-PS5-Builder](https://github.com/LoZazaMastro/TheSimpsonsGame-PS5-Builder))
    has it working, with changes in about ten of ReXGlue's graphics files. Porting
    those into the fork is the next step for this template.
- **The codegen version must match the runtime.** Use ReXGlue's host tools at
  `nightly-20261002-bd833a2a`. The PS5 runtime runs only the code this version
  generates. A PC project on another version needs its manifest and code brought to
  this one.

## 1. Set up and run the test app

```bash
tools/bootstrap.sh          # checks the host, clones the stack beside this repository
tools/build-rexglue.sh      # the ReXGlue runtime for the PS5
tools/build.sh              # the test app: dist/PPSA99001/
tools/deploy.sh             # or copy dist/PPSA99001/ to /data/homebrew/ yourself
```

Launch **ReXGlue Test** from the home screen. When it closes,
`/data/homebrew/PPSA99001/title-results.txt` should show the window, the guest memory
and a one-second tone, each marked as passed. If those work, the console side of the
stack works.

## 2. Make the game's folder

Copy `games/edgeoftime/` to `games/<name>/`, and change:

- **`sce_sys/param.json`:**
  - `titleId`: a new ID, like `PPSA99xxx`. Two titles with the same ID overwrite
    each other on the console.
  - `contentId`: keep the format `UP9000-<titleId>_00-<16 capital letters or
    digits>`.
  - `conceptId`: the ID's digits.
  - `titleName`: the home-screen name.
- **`game.cmake`:** what the game builds (step 3).
- **`notices.json`:** the game's licences, so every build carries them.
- **`release.json`, `HOW-TO-INSTALL.txt`, `gamedata-note.txt`:** what the release
  zip holds (step 6).
- **`module_static.cpp`:** only if the game has DLL modules (below).
- **Optional art:** put `icon-source.*` and `background-source.*` in
  `games/<name>/title-art/` and run `tools/title-art.py games/<name>`. Git ignores
  that folder, so art taken from the game stays with you.

Then build with `GAME=games/<name> tools/build.sh`.

## 3. game.cmake

`cmake/rexglue-ps5.cmake` gives a game four things:

| | |
| --- | --- |
| `rex_ps5_module(<target> GENERATED <dir> [PREFIX <p>] [SOURCES ...] [INCLUDES ...])` | builds `rexglue codegen`'s output for one module (its `sources.cmake`), with the settings ReXGlue uses and the PS5's memory offset in its precompiled header |
| `rex_ps5_settings(<target>)` | the runtime's headers, defines and options, for the game's own sources |
| `rex_ps5_link_objects(<target>...)` | an object library's objects into the title |
| `REX_APP_SOURCE` | ReXApp's source, which a ReXGlue game builds as part of itself |

A typical game:

```cmake
set(MYGAME_SRC ${ROOT}/../MyGameRecomp)
rex_ps5_module(mygame_recomp GENERATED ${MYGAME_SRC}/generated/default INCLUDES ${MYGAME_SRC}/src)
add_library(mygame OBJECT ${MYGAME_SRC}/src/main.cpp ${REX_APP_SOURCE})
target_include_directories(mygame PRIVATE ${MYGAME_SRC}/src)
rex_ps5_settings(mygame)
rex_ps5_link_objects(mygame)
```

Optional settings:
- `TITLE_RESULTS_FILE`: the startup-lines file.
- `TITLE_ARGS`: the arguments the app gets. The default is `--log_level=info`.
- `TITLE_LIBC_BINDINGS`: more libc names to bind (step 4).

**DLL modules.** A PS5 title can't load code of its own as a library. If the PC build
opens a recompiled DLL, build it with `PREFIX`:
1. Its objects become one.
2. Every name is given the prefix, so its names can't collide with the executable's.
3. `module_static.cpp` registers its entry points under the library's name, where the
   runtime's `DynamicLibrary` finds them.

The prefixing covers weak names too. Before it did, Edge of Time's module picked up
the executable's `xstart`, which re-ran its C runtime start-up and crashed with a
null device.

## 4. Bring the game's code to the PS5

Most of the work is in the PC project's own code, under `#if defined(__PROSPERO__)`
(or `REX_PLATFORM_PS5`). These are the things Edge of Time needed, in the order they
came up:

- **Where things are.** The runtime's ReXApp reads the game from `/app0/gamedata`, the
  title folder's `gamedata/`. It keeps logs and saves in the title folder. Players
  copy the game folder from a PC install of the recompilation into `gamedata/`.
- **No desktop pieces.** Drop the installer, file dialogs, the PC's windowing and
  launching other programs from the PS5 build. Edge of Time's
  `ps5/reeot-sources.cmake` is its PC source list minus those.
- **Memory.** A title has about 448 MiB of flexible memory (`malloc`) and much more
  direct memory. Put anything large in direct memory with
  `rex::memory::AllocFixed`, never the heap: Edge of Time's 519 MB shader cache
  lives there.
- **Large data goes beside `eboot.bin`,** not inside it. That keeps the binary
  small and uploads quick. Edge of Time's shaders are `shader-cache.zst`, checked
  against the binary by size so a mismatched pair can't load.
- **Imports.** `link-title.sh` refuses any C library name that no module a title
  loads exports, because it would be null at run time. Bind it to the platform
  layer's `ps5_` version with `TITLE_LIBC_BINDINGS`.
- **No weak undefined symbols.** The console's tool rejects them. Give a weak
  default definition instead (Edge of Time's `reeot_spirv_cache_external`).
- **Ending the title.** Never call `exit()` or `_Exit()`: the console reports that
  as a crash. Call `sceSystemServiceLoadExec("exit", nullptr)` and wait.
- **Threads.** The fork runs a thread's `thread_local` destructors before it exits
  (`ps5_pthread_exit`). Without that, the game crashed after 43 minutes on freed
  thread storage. Don't rely on pthread key destructors running in any order.
- **Shaders, for a game with its own renderer.**
  1. The first launch of a build with no shaders finds them: from the game's
     files, and from inside the executable's memory, where Edge of Time keeps 165
     of its own.
  2. It writes them to a file and closes.
  3. XenosRecomp recompiles them on the PC, and the next build carries them.
  4. Shaders the game uses but the cache lacks are appended to `shader-misses.bin`
     as a safety net.
  
  EdgeOfTimeRecomp's `src/gpu/shaders/` has all of it.

## 5. Debugging on the console

- **`title-results.txt`** (or the game's `TITLE_RESULTS_FILE`) gets each start-up
  stage before it runs, so a file that stops says where.
- **The `alive: N s` line** appears every five seconds, so a quiet run tells a hang
  from a crash.
- **`logs/`** in the title folder has the runtime's log, at `--log_level=info`.
  Debug level logs a few MB a minute.
- **`logs/fault.log`** has a crash's report with a backtrace. Builds keep frame
  pointers for it; match the addresses against the linked ELF in
  `build/title-<name>/link/`.
- **One build per test.** Change one thing, build, copy `eboot.bin`, launch, and
  read the results.

## 6. Ship it

```bash
GAME=games/<name> tools/build.sh
tools/package-release.py games/<name> v1.0.0     # release/<zip>
```

The zip holds:
- `HOW-TO-INSTALL.txt`;
- the title folder, with the files `release.json` lists (such as the shader cache);
- an empty `gamedata/` folder with the note telling players what goes there from
  their own copy.

It holds no game files. It refuses a title folder with a `gamedata/` in it, and
warns when the build came from uncommitted changes.

Before you publish:
- Credit everyone the port is built on.
- Say plainly that players need their own copy of the game.
