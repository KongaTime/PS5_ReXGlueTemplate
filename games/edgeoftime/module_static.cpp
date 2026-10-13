/*
 * Spider-Man: Edge of Time - the game logic module, linked into the title.
 *
 * The desktop opens GameLogic.dll's recompiled code as a shared library
 * (reeot_GameLogic) and looks up ReXModule_Register and ReXModule_GetImageInfo in
 * it. A title cannot load code of its own that way, so the module is linked in
 * (rex_ps5_module's PREFIX, which gives its names the reeot_GameLogic_ prefix),
 * and this registers its two entry points under the library's name, where the
 * runtime's DynamicLibrary finds them on the PS5. A game with modules of its
 * own registers each the same way, under the name its PC build opens.
 *
 * Copyright (C) 2026 KongaTime
 * SPDX-License-Identifier: MIT
 */

#include <rex/platform/dynlib.h>

extern "C" void reeot_GameLogic_ReXModule_Register(void *registrar);
extern "C" const void *reeot_GameLogic_ReXModule_GetImageInfo();

namespace
{
const bool registered = [] {
	static const rex::platform::StaticSymbol symbols[] = {
		{"ReXModule_Register", reinterpret_cast<void *>(&reeot_GameLogic_ReXModule_Register)},
		{"ReXModule_GetImageInfo", reinterpret_cast<void *>(&reeot_GameLogic_ReXModule_GetImageInfo)},
	};
	rex::platform::RegisterStaticLibrary("reeot_GameLogic", symbols, 2);
	return true;
}();
} // namespace
