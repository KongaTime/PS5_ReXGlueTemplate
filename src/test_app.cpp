/*
 * PS5 ReXGlue Template - the test app: the runtime on the console, no game.
 *
 * What the title runs when it is built without a game (tools/build.sh with no
 * GAME). It checks that the PS5 side of the stack works before a game is
 * brought up on it, in order:
 *
 * 1. the window: the display surface's size;
 * 2. the guest memory: Memory::Initialize, and a read of this app's code;
 * 3. the sound: a one-second 440 Hz tone through the PS5 sound driver
 *    (sceAudioOut);
 *
 * then quits through the app context. Every line goes to the results file
 * before its step (title_note), so a file that stops says where.
 *
 * Copyright (C) 2026 KongaTime
 * SPDX-License-Identifier: MIT
 */

#include <atomic>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <memory>
#include <thread>

#include <rex/audio/prospero/prospero_audio_driver.h>
#include <rex/system/xmemory.h>
#include <rex/thread.h>
#include <rex/ui/window.h>
#include <rex/ui/windowed_app.h>
#include <rex/ui/windowed_app_context.h>

extern "C" void title_note(const char *format, ...) __attribute__((format(printf, 1, 2)));

namespace
{
uint32_t BigEndianFloat(float value)
{
	return __builtin_bswap32(std::bit_cast<uint32_t>(value));
}

class RexTestApp final : public rex::ui::WindowedApp {
    public:
	static std::unique_ptr<rex::ui::WindowedApp> Create(rex::ui::WindowedAppContext &context)
	{
		return std::unique_ptr<rex::ui::WindowedApp>(new RexTestApp(context));
	}

	bool OnInitialize() override
	{
		title_note("==== the test app: the ReXGlue runtime on the PS5 ====");
		title_note("window: creating it");
		window_ = rex::ui::Window::Create(app_context(), "ReXGlue Test");
		if (!window_ || !window_->Open()) {
			title_note("window: FAILED to create or open");
			return false;
		}
		title_note("window: open, %ux%u", window_->GetActualPhysicalWidth(),
			   window_->GetActualPhysicalHeight());
		worker_ = std::thread([this] { Run(); });
		return true;
	}

	void OnDestroy() override
	{
		stopping_ = true;
		if (worker_.joinable())
			worker_.join();
		window_.reset();
		memory_.reset();
		title_note("==== the test app: done ====");
	}

    private:
	explicit RexTestApp(rex::ui::WindowedAppContext &context) : WindowedApp(context, "rexglue_test") {}

	void Run()
	{
		if (TestMemory())
			TestSound();
		title_note("quitting through the app context");
		app_context().CallInUIThread([this] { app_context().QuitFromUIThread(); });
	}

	bool TestMemory()
	{
		title_note("memory: Memory::Initialize (the 4.5 GiB guest arena, the MMIO handler)");
		memory_ = std::make_unique<rex::memory::Memory>();
		if (!memory_->Initialize()) {
			title_note("memory: FAILED to initialize");
			return false;
		}
		title_note("memory: initialized");
		const volatile uint8_t *code = reinterpret_cast<const volatile uint8_t *>(&RexTestApp::Create);
		uint8_t bytes[4];
		for (int i = 0; i < 4; i++)
			bytes[i] = code[i];
		title_note("code: readable: %02x %02x %02x %02x", bytes[0], bytes[1], bytes[2], bytes[3]);
		return true;
	}

	void TestSound()
	{
		using rex::audio::prospero::kSamplesPerFrame;
		constexpr size_t kGuestChannels = 6;
		constexpr int kFrames = 188; // a second of 256-sample periods at 48 kHz
		title_note("sound: a one-second beep through the PS5 driver (sceAudioOut)");
		auto semaphore = rex::thread::Semaphore::Create(64, 64);
		auto driver = std::make_unique<rex::audio::prospero::ProsperoAudioDriver>(memory_.get(),
											   semaphore.get());
		if (!driver->Initialize()) {
			title_note("sound: FAILED to open the driver");
			return;
		}
		const uint32_t frame = memory_->SystemHeapAlloc(uint32_t(kSamplesPerFrame * kGuestChannels * 4));
		auto *planes = memory_->TranslateVirtual<uint32_t *>(frame);
		double phase = 0;
		int submitted = 0;
		for (; submitted < kFrames && !stopping_; submitted++) {
			if (rex::thread::Wait(semaphore.get(), false, std::chrono::milliseconds(1000)) !=
			    rex::thread::WaitResult::kSuccess)
				break;
			for (size_t i = 0; i < kSamplesPerFrame; i++) {
				const float value = float(0.25 * std::sin(phase));
				phase += 2.0 * 3.14159265358979 * 440.0 / 48000.0;
				for (size_t channel = 0; channel < kGuestChannels; channel++)
					planes[channel * kSamplesPerFrame + i] =
						BigEndianFloat(channel < 2 ? value : 0.0f);
			}
			driver->SubmitFrame(frame);
		}
		driver->Shutdown();
		memory_->SystemHeapFree(frame);
		title_note("sound: %d frames played", submitted);
	}

	std::unique_ptr<rex::ui::Window> window_;
	std::unique_ptr<rex::memory::Memory> memory_;
	std::thread worker_;
	std::atomic<bool> stopping_{false};
};
} // namespace

REX_DEFINE_APP(rexglue_test, RexTestApp::Create);
