# PS5 ReXGlue Template - the title's build (tools/build.sh drives it).
#
# Configured with the payload SDK's toolchain (toolchain/prospero.cmake). It
# compiles the title's start-up (src/: the platform layer, volk, the entry that
# runs the ReXGlue app) and either a game (TITLE_GAME, a folder such as
# games/edgeoftime with its game.cmake and sce_sys/) or, without one, the test
# app (src/test_app.cpp). tools/link-title.sh then links them with the ReXGlue
# runtime and RADV and packages the title folder, dist/<TITLE_ID>/.
#
# Copyright (C) 2026 Mihawk, KongaTime
# SPDX-License-Identifier: MIT

cmake_minimum_required(VERSION 3.20)
project(ps5_rexglue_title C CXX)

set(ROOT ${CMAKE_CURRENT_SOURCE_DIR})
set(PS5_VULKAN_DIR "${ROOT}/../PS5_Vulkan" CACHE PATH "the PS5_Vulkan checkout (RADV archive, link recipe, packaging)")
# PS5_PAYLOAD_SDK: the SDK the toolchain file came from (tools/setup-sdk.sh's pin)

# The game: its folder holds game.cmake (what it builds) and sce_sys/ (its title
# ID, name and art). Without one the title runs the test app, as ReXGlue Test.
set(TITLE_GAME "" CACHE PATH "the game's folder (games/<name>); empty builds the test app")
if(TITLE_GAME)
	get_filename_component(TITLE_DIR "${TITLE_GAME}" ABSOLUTE BASE_DIR ${ROOT})
	if(NOT EXISTS ${TITLE_DIR}/game.cmake OR NOT EXISTS ${TITLE_DIR}/sce_sys/param.json)
		message(FATAL_ERROR "${TITLE_DIR} is not a game folder: it needs game.cmake and sce_sys/param.json")
	endif()
else()
	set(TITLE_DIR ${ROOT})
endif()
file(READ ${TITLE_DIR}/sce_sys/param.json param_json)
string(JSON TITLE_NAME GET "${param_json}" localizedParameters en-US titleName)
string(JSON TITLE_ID GET "${param_json}" titleId)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${TITLE_DIR}/sce_sys/param.json)
message(STATUS "Title: ${TITLE_NAME} (${TITLE_ID}), from ${TITLE_DIR}")

# What the title writes its start-up lines to (readable over FTP), and the
# arguments it gives the app; a game's game.cmake may set either
set(TITLE_RESULTS_FILE /app0/title-results.txt)
set(TITLE_ARGS --log_level=info)

# The start-up: the platform layer, volk, and the entry that runs the app
add_library(title OBJECT src/platform.c third_party/volk/volk.c src/entry.cpp src/title_main.cpp)
target_include_directories(title PRIVATE third_party/volk src)
set_target_properties(title PROPERTIES CXX_STANDARD 20 CXX_STANDARD_REQUIRED ON C_STANDARD 11)
# Every unit sees volk's declarations first: the Vulkan commands are volk's
# pointers, filled from the RADV linked into the title.
# -fno-omit-frame-pointer: the console's crash backtraces are frame-pointer walks.
target_compile_options(title PRIVATE -O2 -g1 -ffunction-sections -fdata-sections -fno-omit-frame-pointer
	"SHELL:-include ${ROOT}/third_party/volk/volk.h")
set_source_files_properties(third_party/volk/volk.c PROPERTIES COMPILE_OPTIONS "-w")

# The ReXGlue runtime, and the helpers a game builds with (rex_ps5_*)
include(cmake/rexglue-ps5.cmake)
# volk's Vulkan headers: the runtime's
target_include_directories(title PRIVATE ${REXGLUE_SRC}/thirdparty/vulkan-headers/include)

if(TITLE_GAME)
	include(${TITLE_DIR}/game.cmake)
else()
	add_library(title_test_app OBJECT src/test_app.cpp)
	rex_ps5_settings(title_test_app)
	target_include_directories(title_test_app PRIVATE ${REXGLUE_SRC}/thirdparty/vulkan-headers/include)
	target_compile_options(title_test_app PRIVATE -fno-char8_t)
	rex_ps5_link_objects(title_test_app)
endif()

# The start-up's settings, now that the game has had its say
string(JOIN "\", \"" title_args_joined ${TITLE_ARGS})
list(LENGTH TITLE_ARGS title_argc)
target_compile_definitions(title PRIVATE VK_NO_PROTOTYPES NDEBUG "PS5_TITLE_NAME=\"${TITLE_NAME}\""
	"TITLE_RESULTS=\"${TITLE_RESULTS_FILE}\"" "TITLE_ARGS=\"${title_args_joined}\"" TITLE_ARGC=${title_argc})

# Link, sign and package: the title folder in dist/<TITLE_ID>/
get_property(title_link_inputs GLOBAL PROPERTY TITLE_LINK_INPUTS)
get_property(title_link_depends GLOBAL PROPERTY TITLE_LINK_DEPENDS)
rex_ps5_link_inputs(rex_link_inputs rex_link_depends)
add_custom_command(
	OUTPUT ${CMAKE_BINARY_DIR}/eboot.elf
	COMMAND bash ${ROOT}/tools/link-title.sh ${CMAKE_BINARY_DIR} ${PS5_VULKAN_DIR} ${PS5_PAYLOAD_SDK} ${TITLE_DIR}
		"$<TARGET_OBJECTS:title>" ${title_link_inputs} ${rex_link_inputs}
	DEPENDS title "$<TARGET_OBJECTS:title>" ${ROOT}/tools/link-title.sh ${title_link_depends}
		${rex_link_depends}
	COMMAND_EXPAND_LISTS
	VERBATIM)
add_custom_target(link ALL DEPENDS ${CMAKE_BINARY_DIR}/eboot.elf)
