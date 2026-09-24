// Debug tool tests (WP-05 design section 8-6).
//
// Golmok.Debug.StatsMath:     the pure header numbers (window, avg fps, 1% low = numpy 'linear', formatting).
// Golmok.Debug.PathFormat:    FormatPathJson matches the design section 4-4 layout byte for byte and round-trips
//                             through ParsePathJson and Save/LoadPathFile.
// Golmok.Debug.PathRoundTrip: on L_Dev, record 1.2 s of camera path, play it back on the AGolmokPathPawn and check
//                             possession / view target / hidden character / restoration.
// Golmok.Debug.HudStats:      on L_Dev, the OnEndFrame sampler feeds the ring (Frames >= 10 after 1 s, also under
//                             -nullrhi), FormatStatsLine() reports a known 1% low, golmok.hud / golmok.stats work.
//
// Headless: .\tools\ue\test.ps1 -Filter Golmok.Debug   (or in the editor console: Automation RunTests Golmok.Debug)

#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "CoreGlobals.h"
#include "Debug/GolmokDebugSubsystem.h"
#include "Debug/GolmokHUD.h"
#include "Debug/GolmokPathPawn.h"
#include "Debug/GolmokStatsMath.h"
#include "Editor.h"
#include "Engine/World.h"
#include "GameFramework/HUD.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Player/GolmokCharacter.h"
#include "Tests/AutomationEditorCommon.h"

namespace GolmokDebugTest
{
	const TCHAR* DevMap = TEXT("/Game/Golmok/Maps/L_Dev");

	FString FromStd(const std::string& S)
	{
		return FString(UTF8_TO_TCHAR(S.c_str()));
	}

	GolmokStatsMath::PoseSample MakeSample(double T, double X, double Y, double Z, double Pitch, double Yaw, double Roll)
	{
		GolmokStatsMath::PoseSample S;
		S.T = T;
		S.P[0] = X;
		S.P[1] = Y;
		S.P[2] = Z;
		S.R[0] = Pitch;
		S.R[1] = Yaw;
		S.R[2] = Roll;
		return S;
	}

	bool SamplesEqual(const GolmokStatsMath::PoseSample& A, const GolmokStatsMath::PoseSample& B)
	{
		if (!FMath::IsNearlyEqual(A.T, B.T, 1e-9))
		{
			return false;
		}
		for (std::size_t i = 0; i < 3; ++i)
		{
			if (!FMath::IsNearlyEqual(A.P[i], B.P[i], 1e-9) || !FMath::IsNearlyEqual(A.R[i], B.R[i], 1e-9))
			{
				return false;
			}
		}
		return true;
	}

	/** The design section 4-4 example extended to three samples; every value sits on the output decimal grid. */
	GolmokStatsMath::CameraPath ExamplePath()
	{
		GolmokStatsMath::CameraPath Path;
		Path.Version = 1;
		Path.Name = "walk_01";
		Path.Level = "L_ZoneTest";
		Path.Hz = 10;
		Path.Created = "2026-09-25T10:11:12Z";
		Path.Samples.push_back(MakeSample(0.0, 17670.59, -22698.00, 1190.00, -5.0, 90.0, 0.0));
		Path.Samples.push_back(MakeSample(0.1, 17670.59, -22690.12, 1190.00, -5.0, 90.0, 0.0));
		Path.Samples.push_back(MakeSample(0.2, 17670.59, -22682.25, 1190.00, -5.0, 90.5, 0.0));
		return Path;
	}

	const TCHAR* ExampleJson = TEXT("{\"version\": 1, \"name\": \"walk_01\", \"level\": \"L_ZoneTest\", \"hz\": 10, \"created\": \"2026-09-25T10:11:12Z\", \"samples\": [\n")
							   TEXT("{\"t\": 0.000, \"p\": [17670.59, -22698.00, 1190.00], \"r\": [-5.000, 90.000, 0.000]},\n")
							   TEXT("{\"t\": 0.100, \"p\": [17670.59, -22690.12, 1190.00], \"r\": [-5.000, 90.000, 0.000]},\n")
							   TEXT("{\"t\": 0.200, \"p\": [17670.59, -22682.25, 1190.00], \"r\": [-5.000, 90.500, 0.000]}\n")
							   TEXT("]}\n");

	// ---- PathRoundTrip scenario -------------------------------------------------------------------------------

	const TCHAR* RecordName = TEXT("_automation_rec");
	constexpr double RecordSeconds = 1.2;

	enum class ERoundTripPhase : uint8
	{
		WaitForPawn,
		Recording,
		Playing,
		Done,
	};

	class FPathRoundTripScenario : public IAutomationLatentCommand
	{
	public:
		explicit FPathRoundTripScenario(FAutomationTestBase* InTest) : Test(InTest), CreatedAt(FPlatformTime::Seconds()) {}

		virtual bool Update() override
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			if (!World)
			{
				return Fail(TEXT("PIE world not running"), 60.0, FPlatformTime::Seconds() - CreatedAt);
			}
			const double Now = World->GetTimeSeconds();
			if (PhaseStart < 0.0)
			{
				PhaseStart = Now;
			}
			const double Elapsed = Now - PhaseStart;

			UGolmokDebugSubsystem* Debug = World->GetSubsystem<UGolmokDebugSubsystem>();
			APlayerController* PC = World->GetFirstPlayerController();
			if (!Debug || !PC)
			{
				return Fail(TEXT("no UGolmokDebugSubsystem / player controller in the PIE world"), 10.0, Elapsed);
			}

			switch (Phase)
			{
			case ERoundTripPhase::WaitForPawn:
			{
				if (Elapsed < 0.5 || !Cast<AGolmokCharacter>(PC->GetPawn()))
				{
					return Fail(TEXT("no AGolmokCharacter possessed by the first player controller"), 20.0, Elapsed);
				}
				FString Message;
				if (!Test->TestTrue(TEXT("StartRecording(_automation_rec)"), Debug->StartRecording(RecordName, Message)))
				{
					Test->AddError(Message);
					return true;
				}
				Test->TestTrue(TEXT("IsRecording()"), Debug->IsRecording());
				return Next(ERoundTripPhase::Recording, Now);
			}

			case ERoundTripPhase::Playing:
			{
				if (Elapsed < PlaybackWait)
				{
					if (Elapsed > 0.2 && Debug->IsPlaying() && !bCheckedMidPlayback)
					{
						bCheckedMidPlayback = true;
						AGolmokPathPawn* Pawn = Cast<AGolmokPathPawn>(PC->GetPawn());
						Test->TestNotNull(TEXT("player controller possesses an AGolmokPathPawn during playback"), Pawn);
						if (Pawn)
						{
							PathPawn = Pawn;
							Test->TestTrue(TEXT("view target is the path pawn"), PC->GetViewTarget() == Pawn);
							double T = 0.0;
							double Duration = 0.0;
							Debug->GetPlaybackProgress(T, Duration);
							Test->AddInfo(FString::Printf(TEXT("playback %.2f/%.2f s, pawn at %s"), T, Duration, *Pawn->GetActorLocation().ToString()));
						}
						if (Character.IsValid())
						{
							Test->TestTrue(TEXT("character hidden during playback"), Character->IsHidden());
						}
					}
					return false;
				}
				Test->TestFalse(TEXT("playback finished (IsPlaying == false)"), Debug->IsPlaying());
				Test->TestTrue(TEXT("mid-playback checks ran"), bCheckedMidPlayback);
				Test->TestNotNull(TEXT("player controller possesses the AGolmokCharacter again"), Cast<AGolmokCharacter>(PC->GetPawn()));
				if (Character.IsValid())
				{
					Test->TestFalse(TEXT("character visible again"), Character->IsHidden());
				}
				else
				{
					Test->AddError(TEXT("the original character disappeared"));
				}
				Test->TestTrue(TEXT("path pawn destroyed (or pending kill)"), !PathPawn.IsValid() || PathPawn->IsPendingKillPending());
				IFileManager::Get().Delete(*FilePath, /*RequireExists*/ false, /*EvenReadOnly*/ true, /*Quiet*/ true);
				return Next(ERoundTripPhase::Done, Now);
			}

			case ERoundTripPhase::Recording:
			{
				if (Elapsed < RecordSeconds)
				{
					return false;
				}
				FString Message;
				const bool bSaved = Debug->StopRecording(Message);
				Test->AddInfo(Message);
				if (!Test->TestTrue(TEXT("StopRecording saves the path"), bSaved))
				{
					return true;
				}
				FilePath = Debug->PathFilePath(RecordName);
				Test->TestTrue(TEXT("path file exists"), IFileManager::Get().FileExists(*FilePath));
				GolmokStatsMath::CameraPath Path;
				FString Error;
				if (!Test->TestTrue(TEXT("LoadPathFile"), UGolmokDebugSubsystem::LoadPathFile(FilePath, Path, Error)))
				{
					Test->AddError(Error);
					return true;
				}
				Test->TestTrue(TEXT("at least 10 samples at 10 Hz over 1.2 s"), Path.Samples.size() >= 10);
				Test->TestTrue(TEXT("Duration() >= 1.0 s"), Path.Duration() >= 1.0);
				Test->TestEqual(TEXT("LastPathName"), Debug->GetLastPathName(), FString(RecordName));
				PlaybackWait = Path.Duration() + 0.5;

				Character = Cast<AGolmokCharacter>(PC->GetPawn());
				if (!Test->TestTrue(TEXT("StartPlayback(_automation_rec, csv off)"), Debug->StartPlayback(RecordName, /*bCsv*/ false, Message)))
				{
					Test->AddError(Message);
					return true;
				}
				Test->AddInfo(Message);
				Test->TestTrue(TEXT("IsPlaying()"), Debug->IsPlaying());
				return Next(ERoundTripPhase::Playing, Now);
			}

			case ERoundTripPhase::Done:
				return true;
			}
			return true;
		}

	private:
		bool Next(ERoundTripPhase NextPhase, double Now)
		{
			Phase = NextPhase;
			PhaseStart = Now;
			return false;
		}

		bool Fail(const TCHAR* What, double Timeout, double Elapsed = 0.0)
		{
			if (Elapsed < Timeout)
			{
				return false;
			}
			Test->AddError(FString::Printf(TEXT("%s (phase %d, %.1f s)"), What, static_cast<int32>(Phase), Elapsed));
			return true;
		}

		FAutomationTestBase* Test;
		double CreatedAt;
		ERoundTripPhase Phase = ERoundTripPhase::WaitForPawn;
		double PhaseStart = -1.0;
		double PlaybackWait = 2.0;
		bool bCheckedMidPlayback = false;
		FString FilePath;
		TWeakObjectPtr<AGolmokCharacter> Character;
		TWeakObjectPtr<AGolmokPathPawn> PathPawn;
	};

	// ---- HudStats scenario ------------------------------------------------------------------------------------

	enum class EHudPhase : uint8
	{
		Start,
		Sampling,
		Done,
	};

	class FHudStatsScenario : public IAutomationLatentCommand
	{
	public:
		explicit FHudStatsScenario(FAutomationTestBase* InTest) : Test(InTest), CreatedAt(FPlatformTime::Seconds()) {}

		virtual bool Update() override
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			if (!World)
			{
				return Fail(TEXT("PIE world not running"), 60.0, FPlatformTime::Seconds() - CreatedAt);
			}
			const double Now = World->GetTimeSeconds();
			if (PhaseStart < 0.0)
			{
				PhaseStart = Now;
			}
			const double Elapsed = Now - PhaseStart;

			UGolmokDebugSubsystem* Debug = World->GetSubsystem<UGolmokDebugSubsystem>();
			APlayerController* PC = World->GetFirstPlayerController();
			if (!Debug || !PC)
			{
				return Fail(TEXT("no UGolmokDebugSubsystem / player controller in the PIE world"), 10.0, Elapsed);
			}

			switch (Phase)
			{
			case EHudPhase::Start:
			{
				if (Elapsed < 0.5)
				{
					return false;
				}
				AHUD* Hud = PC->GetHUD();
				Test->TestNotNull(TEXT("player controller has a HUD"), Hud);
				Test->TestTrue(TEXT("HUD is an AGolmokHUD (AGolmokGameMode::HUDClass)"), Hud && Hud->IsA<AGolmokHUD>());
				Debug->SetHudVisible(true);
				Test->TestTrue(TEXT("IsHudVisible() after SetHudVisible(true)"), Debug->IsHudVisible());
				Test->TestTrue(TEXT("sampler bound while the HUD is visible"), Debug->IsSamplerBound());
				return Next(EHudPhase::Sampling, Now);
			}

			case EHudPhase::Sampling:
			{
				if (Elapsed < 1.0)
				{
					return false;
				}
				GolmokStatsMath::Stats S;
				Test->TestTrue(TEXT("GetStats has samples"), Debug->GetStats(S));
				Test->AddInfo(FString::Printf(TEXT("stats after 1 s: %s"), *Debug->FormatStatsLine()));
				Test->TestTrue(TEXT("Frames >= 10 (OnEndFrame fires under -nullrhi too)"), S.Frames >= 10);
				Test->TestTrue(TEXT("AvgFps > 0"), S.AvgFps > 0.0);
				Test->TestTrue(TEXT("0 < OnePercentLowFps <= AvgFps * 1.001"), S.OnePercentLowFps > 0.0 && S.OnePercentLowFps <= S.AvgFps * 1.001);
				Test->TestTrue(TEXT("AvgGameMs >= 0"), S.AvgGameMs >= 0.0);
				Test->TestTrue(TEXT("AvgRenderMs >= 0"), S.AvgRenderMs >= 0.0);
				Test->TestTrue(TEXT("AvgGpuMs >= 0"), S.AvgGpuMs >= 0.0);
				Test->TestTrue(TEXT("values finite"), FMath::IsFinite(S.AvgFps) && FMath::IsFinite(S.OnePercentLowFps) && FMath::IsFinite(S.AvgGameMs) &&
															FMath::IsFinite(S.AvgRenderMs) && FMath::IsFinite(S.AvgGpuMs));
				Test->AddInfo(FString::Printf(TEXT("HasGpu = %s (not asserted: -nullrhi reports 0)"), S.HasGpu ? TEXT("true") : TEXT("false")));

				// Known pattern: one 100 ms hitch followed by 19 frames at 1/60 s, pushed 6 times (2.5 s) so the 2 s window
				// holds only pattern samples: newest-first it takes 4 whole blocks (4 x 0.4167 s) plus the 19 normal frames of
				// the next one (1.9833 s <= 2), i.e. 4 hitches + 95 normals = 99 frames. Sorted fps [10 x4, 60 x95], numpy
				// 'linear' 1st percentile: h = 0.98 -> 10 + 0.98 * (10 - 10) = 10.0; avg = 99 / 1.9833 = 49.9.
				Debug->StatsWindowSeconds = 2.f;
				for (int32 Block = 0; Block < 6; ++Block)
				{
					Debug->PushFrameSample(0.1, 2.0, 3.0, 0.0);
					for (int32 i = 0; i < 19; ++i)
					{
						Debug->PushFrameSample(1.0 / 60.0, 1.0, 2.0, 0.0);
					}
				}
				GolmokStatsMath::Stats P;
				Test->TestTrue(TEXT("GetStats after the pattern"), Debug->GetStats(P));
				Test->TestEqual(TEXT("pattern window holds 99 frames"), static_cast<int32>(P.Frames), 99);
				const FString Line = Debug->FormatStatsLine();
				Test->AddInfo(FString::Printf(TEXT("pattern line: %s"), *Line));
				Test->TestTrue(TEXT("FormatStatsLine reports '1% low 10.0'"), Line.Contains(TEXT("1% low 10.0")));
				Test->TestTrue(TEXT("FormatStatsLine reports 'fps 49.9'"), Line.Contains(TEXT("fps 49.9")));
				Test->TestTrue(TEXT("FormatStatsLine reports 'gpu n/a' without GPU samples"), Line.Contains(TEXT("gpu n/a")));

				IConsoleManager::Get().ProcessUserConsoleInput(TEXT("golmok.hud 0"), *GLog, World);
				Test->TestFalse(TEXT("golmok.hud 0 hides the HUD"), Debug->IsHudVisible());
				IConsoleManager::Get().ProcessUserConsoleInput(TEXT("golmok.stats"), *GLog, World);
				Test->TestFalse(TEXT("FormatStatsLine() is not empty (golmok.stats logs it)"), Debug->FormatStatsLine().IsEmpty());
				Test->TestTrue(TEXT("FormatStatsLine() starts with 'fps '"), Debug->FormatStatsLine().StartsWith(TEXT("fps ")));
				return Next(EHudPhase::Done, Now);
			}

			case EHudPhase::Done:
				return true;
			}
			return true;
		}

	private:
		bool Next(EHudPhase NextPhase, double Now)
		{
			Phase = NextPhase;
			PhaseStart = Now;
			return false;
		}

		bool Fail(const TCHAR* What, double Timeout, double Elapsed = 0.0)
		{
			if (Elapsed < Timeout)
			{
				return false;
			}
			Test->AddError(FString::Printf(TEXT("%s (phase %d, %.1f s)"), What, static_cast<int32>(Phase), Elapsed));
			return true;
		}

		FAutomationTestBase* Test;
		double CreatedAt;
		EHudPhase Phase = EHudPhase::Start;
		double PhaseStart = -1.0;
	};
} // namespace GolmokDebugTest

// ---- Golmok.Debug.StatsMath -----------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokDebugStatsMathTest, "Golmok.Debug.StatsMath", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokDebugStatsMathTest::RunTest(const FString& Parameters)
{
	using namespace GolmokStatsMath;

	// 590 frames at 60 fps and 10 at 30 fps: avg = 600 / (590/60 + 10/30) = 59.02, 1% low: sorted fps has ten 30s first,
	// h = 0.01 * 599 = 5.99 -> x[5] + 0.99 * (x[6] - x[5]) = 30 exactly (same hand computation as numpy).
	RingBuffer Ring(4096);
	for (int32 i = 0; i < 590; ++i)
	{
		Ring.Push(FrameSample{1.0 / 60.0, 1.0, 2.0, 3.0});
	}
	for (int32 i = 0; i < 10; ++i)
	{
		Ring.Push(FrameSample{1.0 / 30.0, 1.0, 2.0, 3.0});
	}
	const GolmokStatsMath::Stats S = Compute(Ring, 100.0);
	TestEqual(TEXT("Frames"), static_cast<int32>(S.Frames), 600);
	TestTrue(TEXT("AvgFps ~ 59.0"), FMath::IsNearlyEqual(S.AvgFps, 600.0 / (590.0 / 60.0 + 10.0 / 30.0), 1e-9) && FMath::Abs(S.AvgFps - 59.0) < 0.05);
	TestTrue(TEXT("OnePercentLowFps == 30"), FMath::IsNearlyEqual(S.OnePercentLowFps, 30.0, 1e-9));
	TestTrue(TEXT("AvgGameMs == 1"), FMath::IsNearlyEqual(S.AvgGameMs, 1.0, 1e-9));
	TestTrue(TEXT("AvgRenderMs == 2"), FMath::IsNearlyEqual(S.AvgRenderMs, 2.0, 1e-9));
	TestTrue(TEXT("AvgGpuMs == 3, HasGpu"), FMath::IsNearlyEqual(S.AvgGpuMs, 3.0, 1e-9) && S.HasGpu);

	TestTrue(TEXT("Percentile n=1"), FMath::IsNearlyEqual(Percentile({42.0}, 1.0), 42.0, 1e-12));
	TestTrue(TEXT("Percentile n=2 P=50 -> midpoint"), FMath::IsNearlyEqual(Percentile({20.0, 10.0}, 50.0), 15.0, 1e-12));
	TestTrue(TEXT("Percentile n=0 -> 0"), Percentile({}, 50.0) == 0.0);

	// Window truncation: ten 0.5 s frames, window 2 s -> the newest four (0.5 + 0.5 + 0.5 + 0.5 == 2.0 exactly).
	RingBuffer Short(16);
	for (int32 i = 0; i < 10; ++i)
	{
		Short.Push(FrameSample{0.5, 0.0, 0.0, 0.0});
	}
	const GolmokStatsMath::Stats W = Compute(Short, 2.0);
	TestEqual(TEXT("window keeps 4 frames"), static_cast<int32>(W.Frames), 4);
	TestTrue(TEXT("window AvgFps == 2"), FMath::IsNearlyEqual(W.AvgFps, 2.0, 1e-12));
	TestFalse(TEXT("window HasGpu false without GPU samples"), W.HasGpu);

	// Ring overwrite: capacity 4, five pushes -> size 4, newest first 5, 4, 3, 2.
	RingBuffer Small(4);
	for (int32 i = 1; i <= 5; ++i)
	{
		Small.Push(FrameSample{static_cast<double>(i), 0.0, 0.0, 0.0});
	}
	TestEqual(TEXT("ring size after overflow"), static_cast<int32>(Small.Size()), 4);
	TestTrue(TEXT("ring newest is 5, oldest kept is 2"), Small.FromNewest(0).DtSec == 5.0 && Small.FromNewest(3).DtSec == 2.0);

	TestTrue(TEXT("CyclesToMs(1000, 1e-6) == 1"), FMath::IsNearlyEqual(CyclesToMs(1000, 1e-6), 1.0, 1e-9));
	TestEqual(TEXT("FormatFixed(-0.004, 2)"), GolmokDebugTest::FromStd(FormatFixed(-0.004, 2)), FString(TEXT("0.00")));
	TestEqual(TEXT("FormatFixed(1234.5678, 2)"), GolmokDebugTest::FromStd(FormatFixed(1234.5678, 2)), FString(TEXT("1234.57")));
	TestEqual(TEXT("FormatFixed(-5, 3)"), GolmokDebugTest::FromStd(FormatFixed(-5.0, 3)), FString(TEXT("-5.000")));
	TestTrue(TEXT("LerpAngleDeg(170, -170, 0.5) == 180 (shortest arc)"), FMath::IsNearlyEqual(LerpAngleDeg(170.0, -170.0, 0.5), 180.0, 1e-9));
	return true;
}

// ---- Golmok.Debug.PathFormat ----------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokDebugPathFormatTest, "Golmok.Debug.PathFormat", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokDebugPathFormatTest::RunTest(const FString& Parameters)
{
	using namespace GolmokDebugTest;

	const GolmokStatsMath::CameraPath Path = ExamplePath();
	const std::string Json = GolmokStatsMath::FormatPathJson(Path);
	TestEqual(TEXT("FormatPathJson matches the design section 4-4 layout"), FromStd(Json), FString(ExampleJson));

	GolmokStatsMath::CameraPath Parsed;
	std::string Error;
	if (!TestTrue(TEXT("ParsePathJson(FormatPathJson(path))"), GolmokStatsMath::ParsePathJson(Json, Parsed, Error)))
	{
		AddError(FromStd(Error));
		return false;
	}
	TestEqual(TEXT("version"), Parsed.Version, 1);
	TestEqual(TEXT("hz"), Parsed.Hz, 10);
	TestEqual(TEXT("name"), FromStd(Parsed.Name), FString(TEXT("walk_01")));
	TestEqual(TEXT("level"), FromStd(Parsed.Level), FString(TEXT("L_ZoneTest")));
	TestEqual(TEXT("created"), FromStd(Parsed.Created), FString(TEXT("2026-09-25T10:11:12Z")));
	TestEqual(TEXT("sample count"), static_cast<int32>(Parsed.Samples.size()), 3);
	for (std::size_t i = 0; i < Parsed.Samples.size() && i < Path.Samples.size(); ++i)
	{
		TestTrue(FString::Printf(TEXT("sample %d round-trips exactly"), static_cast<int32>(i)), SamplesEqual(Parsed.Samples[i], Path.Samples[i]));
	}
	TestTrue(TEXT("Duration() == 0.2"), FMath::IsNearlyEqual(Parsed.Duration(), 0.2, 1e-9));

	GolmokStatsMath::CameraPath Bad;
	std::string BadError;
	TestFalse(TEXT("version 2 fails"), GolmokStatsMath::ParsePathJson("{\"version\": 2, \"samples\": []}", Bad, BadError));
	TestTrue(TEXT("version 2 error is prefixed 'path json:'"), FromStd(BadError).StartsWith(TEXT("path json:")));
	TestFalse(TEXT("missing samples fails"), GolmokStatsMath::ParsePathJson("{\"version\": 1}", Bad, BadError));
	TestFalse(TEXT("non-monotonic t fails"),
		GolmokStatsMath::ParsePathJson("{\"version\": 1, \"samples\": [{\"t\": 1, \"p\": [0,0,0], \"r\": [0,0,0]}, {\"t\": 0.5, \"p\": [0,0,0], \"r\": [0,0,0]}]}", Bad, BadError));
	TestFalse(TEXT("truncated text fails"), GolmokStatsMath::ParsePathJson("{\"version\": 1, \"samples\": [", Bad, BadError));

	// File round trip through the subsystem's static helpers (no world needed).
	const FString Dir = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Golmok"), TEXT("Paths")));
	IFileManager::Get().MakeDirectory(*Dir, /*Tree*/ true);
	const FString FilePath = FPaths::Combine(Dir, TEXT("_automation_fmt.json"));
	FString FileError;
	if (TestTrue(TEXT("SavePathFile"), UGolmokDebugSubsystem::SavePathFile(FilePath, Path, FileError)))
	{
		GolmokStatsMath::CameraPath Loaded;
		if (TestTrue(TEXT("LoadPathFile"), UGolmokDebugSubsystem::LoadPathFile(FilePath, Loaded, FileError)))
		{
			TestEqual(TEXT("file round trip: sample count"), static_cast<int32>(Loaded.Samples.size()), 3);
			TestEqual(TEXT("file round trip: name"), FromStd(Loaded.Name), FString(TEXT("walk_01")));
			for (std::size_t i = 0; i < Loaded.Samples.size() && i < Path.Samples.size(); ++i)
			{
				TestTrue(FString::Printf(TEXT("file sample %d round-trips exactly"), static_cast<int32>(i)), SamplesEqual(Loaded.Samples[i], Path.Samples[i]));
			}
		}
		else
		{
			AddError(FileError);
		}
	}
	else
	{
		AddError(FileError);
	}
	IFileManager::Get().Delete(*FilePath, /*RequireExists*/ false, /*EvenReadOnly*/ true, /*Quiet*/ true);

	TestTrue(TEXT("IsValidPathName(walk_01)"), UGolmokDebugSubsystem::IsValidPathName(TEXT("walk_01")));
	TestFalse(TEXT("IsValidPathName rejects spaces"), UGolmokDebugSubsystem::IsValidPathName(TEXT("walk 01")));
	TestFalse(TEXT("IsValidPathName rejects empty"), UGolmokDebugSubsystem::IsValidPathName(TEXT("")));
	TestFalse(TEXT("IsValidPathName rejects path separators"), UGolmokDebugSubsystem::IsValidPathName(TEXT("../x")));
	return true;
}

// ---- Golmok.Debug.PathRoundTrip -------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokDebugPathRoundTripTest, "Golmok.Debug.PathRoundTrip", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokDebugPathRoundTripTest::RunTest(const FString& Parameters)
{
	using namespace GolmokDebugTest;

	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddError(FString::Printf(TEXT("%s is missing. Run golmok.setup_dev_level in the editor first."), DevMap));
		return false;
	}

	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FPathRoundTripScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

// ---- Golmok.Debug.HudStats ------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokDebugHudStatsTest, "Golmok.Debug.HudStats", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokDebugHudStatsTest::RunTest(const FString& Parameters)
{
	using namespace GolmokDebugTest;

	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddError(FString::Printf(TEXT("%s is missing. Run golmok.setup_dev_level in the editor first."), DevMap));
		return false;
	}

	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FHudStatsScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

#endif
