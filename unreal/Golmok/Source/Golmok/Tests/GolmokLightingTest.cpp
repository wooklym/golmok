// Lighting preset tests (WP-05 design section 8-6).
//
// Golmok.Lighting.PresetsFile: Config/Golmok/lighting_presets.json loads through AGolmokTimeOfDay::LoadPresetsFile
// with the same rules as tools/tests/test_lighting_presets.py; broken texts fail with an error message.
// Golmok.Lighting.PresetApply: on L_Dev (golmok.setup_dev_level tags the lighting actors GolmokLighting) a preset is
// applied instantly, then transitions, the interior overlay and NextPreset() are checked on the component values.
// Both pass under -nullrhi (no rendering is inspected).
//
// Headless: .\tools\ue\test.ps1 -Filter Golmok.Lighting   (or in the editor console: Automation RunTests Golmok.Lighting)

#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Components/DirectionalLightComponent.h"
#include "Editor.h"
#include "Engine/DirectionalLight.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Tests/AutomationEditorCommon.h"

namespace GolmokLightingTest
{
	const TCHAR* DevMap = TEXT("/Game/Golmok/Maps/L_Dev");
	const TCHAR* LightingTag = TEXT("GolmokLighting");

	// One complete preset body (the overcast_morning values) for synthetic JSON texts.
	const TCHAR* CompleteBody = TEXT("\"pitch\": -35.0, \"yaw\": 110.0, \"lux\": 2.5, \"kelvin\": 6500.0, \"sky\": 1.4, ")
								 TEXT("\"fog\": 0.035, \"fog_height_falloff\": 0.15, \"volumetric\": false, \"exposure_bias\": 0.3");

	FString MakeJson(int32 SchemaVersion, const TCHAR* InteriorFog)
	{
		return FString::Printf(TEXT("{\"schema_version\": %d, \"cycle\": [\"a\", \"b\", \"c\", \"d\"], \"presets\": {")
								   TEXT("\"a\": {%s}, \"b\": {%s}, \"c\": {%s}, \"d\": {%s}, ")
								   TEXT("\"interior\": {\"fog\": %s, \"fog_height_falloff\": 0.2, \"volumetric\": false, \"exposure_bias\": 1.0}}}"),
			SchemaVersion, CompleteBody, CompleteBody, CompleteBody, CompleteBody, InteriorFog);
	}

	const FGolmokLightingPreset* FindPreset(const TArray<FGolmokLightingPreset>& Presets, const TCHAR* Name)
	{
		const FName Key(Name);
		for (const FGolmokLightingPreset& P : Presets)
		{
			if (P.Name == Key)
			{
				return &P;
			}
		}
		return nullptr;
	}

	/** The tagged (or first) DirectionalLight component of the PIE world, for the visibility check. */
	UDirectionalLightComponent* SunComponent(UWorld* World)
	{
		UDirectionalLightComponent* First = nullptr;
		for (TActorIterator<ADirectionalLight> It(World); It; ++It)
		{
			UDirectionalLightComponent* Component = (*It)->FindComponentByClass<UDirectionalLightComponent>();
			if (!Component)
			{
				continue;
			}
			if ((*It)->ActorHasTag(LightingTag))
			{
				return Component;
			}
			if (!First)
			{
				First = Component;
			}
		}
		return First;
	}

	enum class EPhase : uint8
	{
		Start,
		NightDone,
		InteriorDone,
		InteriorNoonDone,
		ExitDone,
		Done,
	};

	// Transitions run with TransitionSeconds = 0.2 and only the end values (0.6 s later) are asserted.
	constexpr float ShortTransition = 0.2f;
	constexpr double SettleSeconds = 0.6;

	class FPresetApplyScenario : public IAutomationLatentCommand
	{
	public:
		explicit FPresetApplyScenario(FAutomationTestBase* InTest) : Test(InTest), CreatedAt(FPlatformTime::Seconds()) {}

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

			switch (Phase)
			{
			case EPhase::Start:
			{
				if (Elapsed < 0.5)
				{
					return false; // let the level actors finish BeginPlay
				}
				TimeOfDay = AGolmokTimeOfDay::FindOrSpawn(World);
				if (!TimeOfDay.IsValid())
				{
					Test->AddError(TEXT("AGolmokTimeOfDay::FindOrSpawn returned null in the PIE world"));
					return true;
				}
				AGolmokTimeOfDay* Tod = TimeOfDay.Get();
				Tod->TransitionSeconds = ShortTransition;
				if (!Test->TestTrue(TEXT("ApplyPreset(clear_noon, instant)"), Tod->ApplyPreset(TEXT("clear_noon"), /*bInstant*/ true)))
				{
					Test->AddError(FString::Printf(TEXT("LastError: %s"), *Tod->LastError));
					return true;
				}
				FGolmokLightingState S;
				Test->TestTrue(TEXT("CaptureState finds lighting actors on L_Dev"), Tod->CaptureState(S));
				Test->TestTrue(TEXT("clear_noon Lux ~ 10"), FMath::IsNearlyEqual(S.Lux, 10.0, 1e-3));
				Test->TestTrue(TEXT("clear_noon Kelvin ~ 5600"), FMath::IsNearlyEqual(S.Kelvin, 5600.0, 1e-2));
				Test->TestTrue(TEXT("clear_noon Fog ~ 0.015"), FMath::IsNearlyEqual(S.Fog, 0.015, 1e-4));
				Test->TestTrue(TEXT("clear_noon ExposureBias ~ 0"), FMath::IsNearlyEqual(S.ExposureBias, 0.0, 1e-4));
				Test->TestTrue(TEXT("clear_noon SunRotation.Pitch ~ -62"), FMath::IsNearlyEqual(S.SunRotation.Pitch, -62.0, 1e-2));
				Test->TestFalse(TEXT("instant apply leaves no transition"), Tod->IsTransitioning());
				Test->AddInfo(FString::Printf(TEXT("after clear_noon: %s"), *Tod->Describe()));

				Test->TestTrue(TEXT("ApplyPreset(night) with transition"), Tod->ApplyPreset(TEXT("night")));
				Test->TestTrue(TEXT("night transition started (tick enabled)"), Tod->IsTransitioning() && Tod->IsActorTickEnabled());
				return Next(EPhase::NightDone, Now);
			}

			case EPhase::NightDone:
			{
				if (Elapsed < SettleSeconds)
				{
					return false;
				}
				AGolmokTimeOfDay* Tod = Get();
				if (!Tod)
				{
					return true;
				}
				FGolmokLightingState S;
				Tod->CaptureState(S);
				Test->TestTrue(TEXT("night Lux == 0"), S.Lux == 0.0);
				Test->TestTrue(TEXT("night bVolumetric"), S.bVolumetric);
				Test->TestFalse(TEXT("night transition finished"), Tod->IsTransitioning());
				Test->TestFalse(TEXT("tick disabled after the transition"), Tod->IsActorTickEnabled());
				if (UDirectionalLightComponent* Sun = SunComponent(World))
				{
					Test->TestFalse(TEXT("sun hidden when Lux == 0"), Sun->GetVisibleFlag());
				}
				else
				{
					Test->AddError(TEXT("no DirectionalLight on L_Dev"));
				}
				NightPitch = S.SunRotation.Pitch;
				Tod->EnterInterior(TEXT("t"));
				return Next(EPhase::InteriorDone, Now);
			}

			case EPhase::InteriorDone:
			{
				if (Elapsed < SettleSeconds)
				{
					return false;
				}
				AGolmokTimeOfDay* Tod = Get();
				if (!Tod)
				{
					return true;
				}
				FGolmokLightingState S;
				Tod->CaptureState(S);
				Test->TestTrue(TEXT("interior overlay Fog == 0"), S.Fog == 0.0);
				Test->TestTrue(TEXT("interior overlay ExposureBias == 1.0"), FMath::IsNearlyEqual(S.ExposureBias, 1.0, 1e-4));
				Test->TestTrue(TEXT("interior keeps the night sun rotation"), FMath::IsNearlyEqual(S.SunRotation.Pitch, NightPitch, 1e-2));
				Test->TestTrue(TEXT("IsInterior()"), Tod->IsInterior());
				Test->AddInfo(FString::Printf(TEXT("interior: %s"), *Tod->Describe()));
				Test->TestTrue(TEXT("ApplyPreset(clear_noon) while interior"), Tod->ApplyPreset(TEXT("clear_noon")));
				return Next(EPhase::InteriorNoonDone, Now);
			}

			case EPhase::InteriorNoonDone:
			{
				if (Elapsed < SettleSeconds)
				{
					return false;
				}
				AGolmokTimeOfDay* Tod = Get();
				if (!Tod)
				{
					return true;
				}
				FGolmokLightingState S;
				Tod->CaptureState(S);
				Test->TestTrue(TEXT("base change while interior: Lux ~ 10"), FMath::IsNearlyEqual(S.Lux, 10.0, 1e-3));
				Test->TestTrue(TEXT("base change while interior keeps Fog == 0"), S.Fog == 0.0);
				Test->TestTrue(TEXT("still interior"), Tod->IsInterior());
				Tod->ExitInterior(TEXT("t"));
				return Next(EPhase::ExitDone, Now);
			}

			case EPhase::ExitDone:
			{
				if (Elapsed < SettleSeconds)
				{
					return false;
				}
				AGolmokTimeOfDay* Tod = Get();
				if (!Tod)
				{
					return true;
				}
				FGolmokLightingState S;
				Tod->CaptureState(S);
				Test->TestFalse(TEXT("ExitInterior clears the overlay"), Tod->IsInterior());
				Test->TestTrue(TEXT("after exit Fog ~ 0.015 (clear_noon)"), FMath::IsNearlyEqual(S.Fog, 0.015, 1e-4));
				Test->TestTrue(TEXT("NextPreset()"), Tod->NextPreset());
				Test->TestEqual(TEXT("NextPreset after clear_noon is golden_evening"), Tod->CurrentPreset.ToString(), FString(TEXT("golden_evening")));
				Test->AddInfo(FString::Printf(TEXT("end: %s"), *Tod->Describe()));
				return Next(EPhase::Done, Now);
			}

			case EPhase::Done:
				return true;
			}
			return true;
		}

	private:
		AGolmokTimeOfDay* Get()
		{
			if (!TimeOfDay.IsValid())
			{
				Test->AddError(FString::Printf(TEXT("AGolmokTimeOfDay disappeared (phase %d)"), static_cast<int32>(Phase)));
				return nullptr;
			}
			return TimeOfDay.Get();
		}

		bool Next(EPhase NextPhase, double Now)
		{
			Phase = NextPhase;
			PhaseStart = Now;
			return false;
		}

		/** Keeps waiting until Timeout, then records the error and stops. */
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
		EPhase Phase = EPhase::Start;
		double PhaseStart = -1.0;
		TWeakObjectPtr<AGolmokTimeOfDay> TimeOfDay;
		double NightPitch = 0.0;
	};
} // namespace GolmokLightingTest

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokLightingPresetsFileTest, "Golmok.Lighting.PresetsFile",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokLightingPresetsFileTest::RunTest(const FString& Parameters)
{
	using namespace GolmokLightingTest;

	const FString Path = FPaths::Combine(FPaths::ProjectConfigDir(), TEXT("Golmok"), TEXT("lighting_presets.json"));
	TArray<FGolmokLightingPreset> Presets;
	TArray<FName> Cycle;
	FString Error;
	if (!AGolmokTimeOfDay::LoadPresetsFile(Path, Presets, Cycle, Error))
	{
		AddError(FString::Printf(TEXT("LoadPresetsFile(%s) failed: %s"), *Path, *Error));
		return false;
	}
	TestEqual(TEXT("5 presets"), Presets.Num(), 5);
	TestEqual(TEXT("4 cycle presets"), Cycle.Num(), 4);
	if (Cycle.Num() == 4)
	{
		TestEqual(TEXT("cycle[0]"), Cycle[0].ToString(), FString(TEXT("overcast_morning")));
		TestEqual(TEXT("cycle[3]"), Cycle[3].ToString(), FString(TEXT("night")));
	}
	if (const FGolmokLightingPreset* Morning = FindPreset(Presets, TEXT("overcast_morning")))
	{
		TestTrue(TEXT("overcast_morning.Lux == 2.5"), FMath::IsNearlyEqual(Morning->Lux, 2.5, 1e-9));
		TestTrue(TEXT("overcast_morning.IsComplete()"), Morning->IsComplete());
	}
	else
	{
		AddError(TEXT("preset overcast_morning missing"));
	}
	if (const FGolmokLightingPreset* Interior = FindPreset(Presets, TEXT("interior")))
	{
		TestFalse(TEXT("interior.bHasSun == false (partial overlay)"), Interior->bHasSun);
		TestTrue(TEXT("interior.bHasFog"), Interior->bHasFog);
		TestTrue(TEXT("interior.Fog == 0"), Interior->Fog == 0.0);
		TestFalse(TEXT("interior is not complete"), Interior->IsComplete());
	}
	else
	{
		AddError(TEXT("preset interior missing"));
	}

	// Broken inputs fail with a non-empty error.
	TArray<FGolmokLightingPreset> Bad;
	TArray<FName> BadCycle;
	FString BadError;
	TestFalse(TEXT("truncated text fails"), AGolmokTimeOfDay::ParsePresetsText(TEXT("{\"schema_version\": 1, \"cycle\": ["), Bad, BadCycle, BadError));
	TestFalse(TEXT("truncated text has an error message"), BadError.IsEmpty());
	TestTrue(TEXT("synthetic text with schema_version 1 parses"), AGolmokTimeOfDay::ParsePresetsText(MakeJson(1, TEXT("0.0")), Bad, BadCycle, BadError));
	TestFalse(TEXT("schema_version 2 fails"), AGolmokTimeOfDay::ParsePresetsText(MakeJson(2, TEXT("0.0")), Bad, BadCycle, BadError));
	TestTrue(TEXT("schema_version 2 error names the key"), BadError.Contains(TEXT("schema_version")));
	TestFalse(TEXT("interior.fog 0.1 fails"), AGolmokTimeOfDay::ParsePresetsText(MakeJson(1, TEXT("0.1")), Bad, BadCycle, BadError));
	TestTrue(TEXT("interior.fog error names preset and key"), BadError.Contains(TEXT("interior")) && BadError.Contains(TEXT("fog")));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokLightingPresetApplyTest, "Golmok.Lighting.PresetApply",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokLightingPresetApplyTest::RunTest(const FString& Parameters)
{
	using namespace GolmokLightingTest;

	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddError(FString::Printf(TEXT("%s is missing. Run golmok.setup_dev_level in the editor first."), DevMap));
		return false;
	}

	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FPresetApplyScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

#endif
