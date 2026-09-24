// Portal tests (WP-05 design section 8-6).
//
// Golmok.Portal.SpawnFromManifest: on L_Dev a z_synthetic_001 zone actor is spawned and loaded (no assets: wire boxes
// only); its Load() must spawn one AGolmokPortal from the manifest with the fixture's values (door_1 ->
// z_synthetic_001_interior, 150 cm, entry, relative (500, -950, 0) cm / yaw -90, sublevel package path), and Unload()
// must destroy it again.
// Golmok.Portal.RoundTrip: on L_ZoneTest (only when synthetic_zone.run(interior=True) built it; otherwise skipped)
// the entry portal is driven through EnterInterior / LeaveInterior without walking: sublevel streamed in, interior
// zone loaded, lighting overlay on; then overlay off and, after UnloadDelaySeconds, sublevel and zone unloaded.
// Both pass under -nullrhi.
//
// Headless: .\tools\ue\test.ps1 -Filter Golmok.Portal   (or in the editor console: Automation RunTests Golmok.Portal)

#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Components/BoxComponent.h"
#include "Editor.h"
#include "Engine/World.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Misc/PackageName.h"
#include "Portals/GolmokPortal.h"
#include "Tests/AutomationEditorCommon.h"
#include "Zones/GolmokZone.h"
#include "Zones/GolmokZoneSubsystem.h"

namespace GolmokPortalTest
{
	const TCHAR* DevMap = TEXT("/Game/Golmok/Maps/L_Dev");
	const TCHAR* ZoneTestMap = TEXT("/Game/Golmok/Maps/L_ZoneTest");
	const TCHAR* ExteriorZoneId = TEXT("z_synthetic_001");
	const TCHAR* InteriorZoneId = TEXT("z_synthetic_001_interior");
	const TCHAR* EntryPortalId = TEXT("door_1");
	const TCHAR* ExpectedSublevel = TEXT("/Game/Golmok/Zones/z_synthetic_001_interior/v1/L_z_synthetic_001_interior");

	/** Shared latent-command scaffolding: PIE world lookup, phase timing, timeout failure (as in GolmokCharacterTest). */
	class FPortalScenarioBase : public IAutomationLatentCommand
	{
	public:
		explicit FPortalScenarioBase(FAutomationTestBase* InTest) : Test(InTest), CreatedAt(FPlatformTime::Seconds()) {}

	protected:
		/** Null until PIE is running; fails the test after 60 s of waiting. Sets Now / Elapsed for the current phase. */
		UWorld* BeginUpdate(bool& bOutDone)
		{
			bOutDone = false;
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			if (!World)
			{
				bOutDone = Fail(TEXT("PIE world not running"), 60.0, FPlatformTime::Seconds() - CreatedAt);
				return nullptr;
			}
			Now = World->GetTimeSeconds();
			if (PhaseStart < 0.0)
			{
				PhaseStart = Now;
			}
			Elapsed = Now - PhaseStart;
			return World;
		}

		bool Next(int32 NextPhase)
		{
			Phase = NextPhase;
			PhaseStart = Now;
			return false;
		}

		/** Keeps waiting until Timeout (seconds of game time in this phase), then records the error and stops. */
		bool Fail(const TCHAR* What, double Timeout, double InElapsed)
		{
			if (InElapsed < Timeout)
			{
				return false;
			}
			Test->AddError(FString::Printf(TEXT("%s (phase %d, %.1f s)"), What, Phase, InElapsed));
			return true;
		}

		FAutomationTestBase* Test;
		double CreatedAt;
		int32 Phase = 0;
		double PhaseStart = -1.0;
		double Now = 0.0;
		double Elapsed = 0.0;
	};

	// ---- Golmok.Portal.SpawnFromManifest -------------------------------------------------------------------------

	class FSpawnFromManifestScenario : public FPortalScenarioBase
	{
	public:
		explicit FSpawnFromManifestScenario(FAutomationTestBase* InTest) : FPortalScenarioBase(InTest) {}

		virtual bool Update() override
		{
			bool bDone = false;
			UWorld* World = BeginUpdate(bDone);
			if (!World)
			{
				return bDone;
			}
			switch (Phase)
			{
			case 0: // let PIE settle (player spawned, subsystems up)
				if (Elapsed < 0.5)
				{
					return false;
				}
				return Next(1);

			case 1:
			{
				AGolmokZone* Zone = World->SpawnActorDeferred<AGolmokZone>(AGolmokZone::StaticClass(), FTransform::Identity);
				if (!Zone)
				{
					Test->AddError(TEXT("could not spawn AGolmokZone"));
					return true;
				}
				Zone->ZoneId = ExteriorZoneId;
				Zone->Version = 1;
				Zone->bAutoManaged = false; // the test drives Load / Unload itself
				Zone->FinishSpawning(FTransform::Identity);

				Test->TestTrue(TEXT("Load() succeeds without assets (wire boxes only)"), Zone->Load());
				Test->AddInfo(FString::Printf(TEXT("zone state %d, missing assets %d, last error '%s'"), static_cast<int32>(Zone->State),
					Zone->MissingAssetCount, *Zone->LastError));
				const TArray<TObjectPtr<AActor>>& Portals = Zone->GetPortalActors();
				if (!Test->TestEqual(TEXT("one portal spawned from the manifest"), Portals.Num(), 1))
				{
					Zone->Destroy();
					return true;
				}
				AGolmokPortal* Portal = Cast<AGolmokPortal>(Portals[0].Get());
				if (!Test->TestNotNull(TEXT("portal actor is an AGolmokPortal"), Portal))
				{
					Zone->Destroy();
					return true;
				}
				PortalActor = Portal;
				Test->AddInfo(Portal->Describe());
				Test->TestEqual(TEXT("PortalId"), Portal->PortalId, FString(EntryPortalId));
				Test->TestEqual(TEXT("OwnerZoneId"), Portal->OwnerZoneId, FString(ExteriorZoneId));
				Test->TestEqual(TEXT("TargetZoneId"), Portal->TargetZoneId, FString(InteriorZoneId));
				Test->TestEqual(TEXT("Kind"), Portal->Kind, FString(TEXT("door")));
				Test->TestTrue(TEXT("RadiusCm == 150"), FMath::IsNearlyEqual(Portal->RadiusCm, 150.0, 1e-6));
				Test->TestTrue(TEXT("exterior zone spawns an entry portal"), Portal->bIsEntry);
				Test->TestEqual(TEXT("SublevelPackagePath"), Portal->SublevelPackagePath, FString(ExpectedSublevel));

				// Relative placement: ENU (5, 9.5, 0) m -> UE (500, -950, 0) cm, UE Yaw = -yaw_deg = -90.
				const FTransform Rel = Portal->GetActorTransform().GetRelativeTransform(Zone->GetActorTransform());
				const FVector RelLoc = Rel.GetLocation();
				const double RelYaw = Rel.Rotator().Yaw;
				Test->AddInfo(FString::Printf(TEXT("portal relative to zone: (%.3f, %.3f, %.3f) cm yaw %.3f"), RelLoc.X, RelLoc.Y, RelLoc.Z, RelYaw));
				Test->TestTrue(TEXT("portal relative location (500, -950, 0)"), RelLoc.Equals(FVector(500.0, -950.0, 0.0), 1e-3));
				Test->TestTrue(TEXT("portal relative yaw -90"), FMath::Abs(FRotator::NormalizeAxis(RelYaw - (-90.0))) < 1e-3);

				UBoxComponent* Trigger = Portal->GetTrigger();
				if (Test->TestNotNull(TEXT("trigger box"), Trigger))
				{
					const FVector Extent = Trigger->GetUnscaledBoxExtent();
					Test->AddInfo(FString::Printf(TEXT("trigger extent (%.1f, %.1f, %.1f)"), Extent.X, Extent.Y, Extent.Z));
					Test->TestTrue(TEXT("trigger extent (150, 150, 125)"), Extent.Equals(FVector(150.0, 150.0, 125.0), 1e-3));
				}

				Zone->Unload();
				Test->TestEqual(TEXT("Unload() empties the portal list"), Zone->GetPortalActors().Num(), 0);
				AActor* Raw = PortalActor.Get(/*bEvenIfPendingKill*/ true);
				Test->TestTrue(TEXT("portal actor is being destroyed after Unload()"), Raw == nullptr || Raw->IsPendingKillPending());
				Zone->Destroy();
				return true;
			}

			default:
				return true;
			}
		}

	private:
		TWeakObjectPtr<AGolmokPortal> PortalActor;
	};

	// ---- Golmok.Portal.RoundTrip --------------------------------------------------------------------------------

	class FRoundTripScenario : public FPortalScenarioBase
	{
	public:
		explicit FRoundTripScenario(FAutomationTestBase* InTest) : FPortalScenarioBase(InTest) {}

		virtual bool Update() override
		{
			bool bDone = false;
			UWorld* World = BeginUpdate(bDone);
			if (!World)
			{
				return bDone;
			}
			UGolmokZoneSubsystem* Subsystem = World->GetSubsystem<UGolmokZoneSubsystem>();
			if (!Subsystem)
			{
				Test->AddError(TEXT("no UGolmokZoneSubsystem in the PIE world"));
				return true;
			}

			switch (Phase)
			{
			case 0: // settle, then make sure the exterior zone (which spawns door_1) is loaded
				if (Elapsed < 0.5)
				{
					return false;
				}
				{
					FString Msg;
					const bool bOk = Subsystem->RequestLoad(ExteriorZoneId, /*bPin*/ true, Msg);
					Test->AddInfo(FString::Printf(TEXT("RequestLoad(%s): %s"), ExteriorZoneId, *Msg));
					if (!bOk)
					{
						Test->AddError(FString::Printf(TEXT("exterior zone %s could not be loaded: %s"), ExteriorZoneId, *Msg));
						return true;
					}
				}
				return Next(1);

			case 1: // find the entry portal
			{
				AGolmokPortal* Portal = AGolmokPortal::FindPortal(World, EntryPortalId);
				if (!Portal)
				{
					return Fail(TEXT("entry portal door_1 not found (is z_synthetic_001 loaded with its manifest portal?)"), 10.0, Elapsed);
				}
				PortalActor = Portal;
				Test->TestTrue(TEXT("door_1 is an entry portal"), Portal->bIsEntry);
				Test->AddInfo(Portal->Describe());
				FString Msg;
				Test->TestTrue(TEXT("EnterInterior"), Portal->EnterInterior(Msg));
				Test->AddInfo(Msg);
				return Next(2);
			}

			case 2: // within StreamInTimeoutSeconds: sublevel visible, interior zone loaded, overlay on
			{
				AGolmokPortal* Portal = PortalActor.Get();
				if (!Portal)
				{
					Test->AddError(TEXT("portal disappeared after EnterInterior"));
					return true;
				}
				AGolmokZone* Interior = Subsystem->FindZone(InteriorZoneId);
				AGolmokTimeOfDay* Tod = AGolmokTimeOfDay::Find(World);
				const bool bSublevel = Portal->IsSublevelVisible();
				const bool bZone = Interior && Interior->IsLoaded();
				const bool bOverlay = Tod && Tod->IsInterior();
				if (!(bSublevel && bZone && bOverlay))
				{
					if (Elapsed < StreamInTimeoutSeconds)
					{
						return false;
					}
					Test->AddInfo(Portal->Describe());
					Test->TestTrue(TEXT("sublevel visible after EnterInterior"), bSublevel);
					Test->TestNotNull(TEXT("interior zone actor placed in L_ZoneTest"), Interior);
					Test->TestTrue(TEXT("interior zone loaded after EnterInterior"), bZone);
					Test->TestNotNull(TEXT("AGolmokTimeOfDay present"), Tod);
					Test->TestTrue(TEXT("interior lighting overlay on after EnterInterior"), bOverlay);
					return true;
				}
				Test->AddInfo(FString::Printf(TEXT("interior ready after %.2f s: %s"), Elapsed, *Portal->Describe()));
				Test->TestEqual(TEXT("portal state Active"), static_cast<int32>(Portal->State), static_cast<int32>(EGolmokPortalState::Active));
				FString Msg;
				Test->TestTrue(TEXT("LeaveInterior"), Portal->LeaveInterior(Msg));
				Test->AddInfo(Msg);
				Test->TestFalse(TEXT("interior lighting overlay off right after LeaveInterior"), Tod->IsInterior());
				UnloadDeadline = static_cast<double>(Portal->UnloadDelaySeconds) + 1.0;
				return Next(3);
			}

			case 3: // within UnloadDelaySeconds + 1: sublevel unloaded, zone unloaded, portal Idle
			{
				AGolmokPortal* Portal = PortalActor.Get();
				if (!Portal)
				{
					Test->AddError(TEXT("portal disappeared after LeaveInterior"));
					return true;
				}
				AGolmokZone* Interior = Subsystem->FindZone(InteriorZoneId);
				const bool bSublevelGone = !Portal->IsSublevelLoaded();
				const bool bZoneGone = !Interior || !Interior->IsLoaded();
				const bool bIdle = Portal->State == EGolmokPortalState::Idle;
				if (!(bSublevelGone && bZoneGone && bIdle))
				{
					if (Elapsed < UnloadDeadline)
					{
						return false;
					}
					Test->AddInfo(Portal->Describe());
					Test->TestTrue(TEXT("sublevel unloaded after the unload delay"), bSublevelGone);
					Test->TestTrue(TEXT("interior zone unloaded after the unload delay"), bZoneGone);
					Test->TestTrue(TEXT("portal back to Idle after the unload delay"), bIdle);
					return true;
				}
				Test->AddInfo(FString::Printf(TEXT("interior released after %.2f s: %s"), Elapsed, *Portal->Describe()));
				return true;
			}

			default:
				return true;
			}
		}

	private:
		static constexpr double StreamInTimeoutSeconds = 2.0;
		TWeakObjectPtr<AGolmokPortal> PortalActor;
		double UnloadDeadline = 4.0;
	};
} // namespace GolmokPortalTest

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokPortalSpawnFromManifestTest, "Golmok.Portal.SpawnFromManifest",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokPortalSpawnFromManifestTest::RunTest(const FString& Parameters)
{
	using namespace GolmokPortalTest;

	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddError(FString::Printf(TEXT("%s is missing. Run golmok.setup_dev_level in the editor first."), DevMap));
		return false;
	}

	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FSpawnFromManifestScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokPortalRoundTripTest, "Golmok.Portal.RoundTrip",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokPortalRoundTripTest::RunTest(const FString& Parameters)
{
	using namespace GolmokPortalTest;

	if (!FPackageName::DoesPackageExist(ZoneTestMap))
	{
		AddInfo(TEXT("skipped: run synthetic_zone.run(interior=True)"));
		return true;
	}

	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(ZoneTestMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FRoundTripScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

#endif
