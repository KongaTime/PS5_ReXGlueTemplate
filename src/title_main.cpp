/*
 * PS5 ReXGlue Template - the title's program.
 *
 * Runs the ReXGlue app the link holds (REX_DEFINE_APP: the game's, or the test
 * app's) through the fork's PS5 entry, rex_ps5_app_main, on this thread, with
 * the arguments the build gives it (TITLE_ARGS).
 *
 * The title gives the runtime its startup log (prospero_startup_log, which the
 * fork defines weakly): each marker is a line of TITLE_RESULTS (by default
 * /app0/title-results.txt, the title's folder, readable over FTP) and of klog,
 * written before the step it names, so a run that stops says where. A line
 * every five seconds says whether a run that went quiet was still alive (a
 * hang) or not (it died).
 *
 * Copyright (C) 2026 KongaTime
 * SPDX-License-Identifier: MIT
 */

#include <chrono>
#include <cstdarg>
#include <cstdio>
#include <thread>

#include <sys/stat.h>

#include "platform.h"

extern "C" int rex_ps5_app_main(int argc, char **argv);

extern "C" void title_note(const char *format, ...) __attribute__((format(printf, 1, 2)));
extern "C" void title_note(const char *format, ...)
{
	char line[512];
	va_list args;
	va_start(args, format);
	vsnprintf(line, sizeof line, format, args);
	va_end(args);
	say("%s", line);
	if (FILE *file = fopen(TITLE_RESULTS, "a")) {
		fprintf(file, "%s\n", line);
		fclose(file);
	}
}

extern "C" void prospero_startup_log(const char *message)
{
	title_note("startup: %s", message ? message : "(null)");
}

extern "C" int title_main(void)
{
	// A fresh results file each run, readable and writable over FTP
	if (FILE *file = fopen(TITLE_RESULTS, "w")) {
		fclose(file);
		chmod(TITLE_RESULTS, 0666);
	}
	std::thread([] {
		for (int seconds = 5;; seconds += 5) {
			std::this_thread::sleep_for(std::chrono::seconds(5));
			title_note("alive: %d s", seconds);
		}
	}).detach();
	static const char *const args[] = {"/app0/eboot.bin", TITLE_ARGS};
	char *argv[TITLE_ARGC + 2];
	for (int i = 0; i <= TITLE_ARGC; i++)
		argv[i] = const_cast<char *>(args[i]);
	argv[TITLE_ARGC + 1] = nullptr;
	const int status = rex_ps5_app_main(TITLE_ARGC + 1, argv);
	title_note("rex_ps5_app_main returned %d", status);
	return status;
}
