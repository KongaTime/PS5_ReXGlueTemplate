#!/usr/bin/env python3
"""PS5 ReXGlue Template - one recompiled DLL module as one object a title links.

On the desktop each of a game's DLL modules (Edge of Time's GameLogic.dll) is a shared library
of its own, so its names never meet the executable's: both define PPCImageConfig
and PPCFuncMappings, for one. A title links everything into one executable, so
this joins a module's objects into one relocatable object (ld -r) and gives every
name it defines a prefix of its own. The module's references to those names
follow them; what it refers to elsewhere (the runtime, the executable's exports)
and the C++ it defines weakly (inline functions, templates, shared alike) keep
their names. ReXModule_Register and ReXModule_GetImageInfo, the two names
the runtime looks up in a module (kernel_state.cpp), take the prefix too: the
game's registration (games/edgeoftime/module_static.cpp) gives them back to it
by their own names (rex::platform::RegisterStaticLibrary).

cmake/rexglue-ps5.cmake runs it for a module built with rex_ps5_module(... PREFIX).

usage: prelink_module.py --bin <SDK bin> --prefix <prefix> --out <object> <objects...>

Copyright (C) 2026 KongaTime
SPDX-License-Identifier: MIT
"""
import argparse
import os
import subprocess
import sys


# Weak names a module shares with the rest of the title: C++ inline functions,
# templates and their guards, and the compiler's helpers
SHARED_WEAK = ("_Z", "DW.ref.", "__clang_", "__cxa_", "__gxx_")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin", required=True, help="the payload SDK's bin (ld.lld, llvm-nm, llvm-objcopy)")
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("objects", nargs="+")
    args = parser.parse_args()

    joined = args.out + ".joined.o"
    subprocess.run([os.path.join(args.bin, "ld.lld"), "-r", "-o", joined, *args.objects], check=True)

    symbols = subprocess.run([os.path.join(args.bin, "llvm-nm"), "-g", "--defined-only", joined],
                             check=True, capture_output=True, text=True).stdout
    renames = []
    for line in symbols.splitlines():
        fields = line.split()
        # value, type, name: every strong definition (T D B R and the like), and
        # every weak one but C++'s. A recompiled function's plain name is a weak
        # alias of its __imp__ name (DEFINE_REX_FUNC), so hooks can replace it,
        # and names the executable shares (xstart, the CRT's entry) would
        # otherwise resolve to the executable's: GameLogic.dll's entry ran
        # Default.xex's startup again, and its constructors reset the game's
        # globals.
        if len(fields) != 3:
            continue
        value, kind, name = fields
        if kind in "TDBRSACG" or (kind in "WV" and not name.startswith(SHARED_WEAK)):
            renames.append(f"{name} {args.prefix}{name}")
    if not any(r.startswith("ReXModule_Register ") for r in renames):
        sys.exit("prelink_module.py: the module defines no ReXModule_Register")

    rename_file = args.out + ".renames"
    with open(rename_file, "w") as f:
        f.write("\n".join(renames) + "\n")
    subprocess.run([os.path.join(args.bin, "llvm-objcopy"), f"--redefine-syms={rename_file}", joined, args.out],
                   check=True)
    os.remove(joined)
    print(f"prelink_module.py: {len(args.objects)} objects, {len(renames)} names given {args.prefix}")


if __name__ == "__main__":
    main()
