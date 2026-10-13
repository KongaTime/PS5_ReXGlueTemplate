/*
 * PS5 ReXGlue Template - the title's main.
 *
 * Starts the console's side (klog, the splash, the pad) through the platform
 * layer, points volk at the RADV linked into the title, then runs the ReXGlue
 * app (src/title_main.cpp).
 *
 * Copyright (C) 2026 KongaTime
 * SPDX-License-Identifier: MIT
 */

#include <iostream>

#include "platform.h"

extern "C" VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL vk_icdGetInstanceProcAddr(VkInstance instance, const char *name);
extern "C" int title_main(void);

int main()
{
	platform_init(PS5_TITLE_NAME);
	std::cout.rdbuf(std::cerr.rdbuf());
	pad_open();
	// Vulkan's commands come from the RADV linked into the title, through volk
	volkInitializeCustom(vk_icdGetInstanceProcAddr);
	const int status = title_main();
	say("ends: status %d", status);
	return status;
}
