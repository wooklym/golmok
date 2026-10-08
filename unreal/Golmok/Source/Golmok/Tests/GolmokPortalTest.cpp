// Portal tests (WP-05 design section 8-6).
//
// Golmok.Portal.SpawnFromManifest: on L_Dev a z_synthetic_001 zone actor is spawned and loaded (no assets: wire boxes
// only); its Load() must spawn one AGolmokPortal from the manifest with the fixture's values (door_1 ->
// z_synthetic_001_interior, 150 cm, entry, relative (500, -950, 0) cm / yaw -90, sublevel package path), and Unload()
// must destroy it again.
// Golmok.Portal.RoundTrip: on L_ZoneTest (only when synthetic_zone.run(interior=True) built the interior sublevel
// package; otherwise skipped) the entry portal is driven through EnterInterior / LeaveInterior without walking:
// sublevel streamed in, interior zone loaded, lighting overlay on; then overlay off and, after UnloadDelaySeconds,
// sublevel and zone unloaded. The cycle runs twice (a stream-out must not drop a registered NamedStreamingLevel
// entry), then the exterior zone is unloaded while the portal is Active: the destroyed portal must release the
// pinned interior zone, the sublevel and the overlay by itself.
// Golmok.Portal.PawnSwap: on L_ZoneTest (same skip) the character is put 6 m outside door_1, EnterInterior forces
// the interior, then player controller 0 possesses a pawn standing 5 m inside the room and possesses the character
// again (what path playback start / end does; AController::Possess broadcasts (Old, nullptr) then (Old, New)): the
// portal must drop the overlay and start its unload delay because the new player pawn stands on the exterior side,
// and release everything after UnloadDelaySeconds.
// Golmok.Portal.SharedInterior: on L_ZoneTest (same skip) a second entry portal door_2 into the same interior is
// spawned 10 m beside door_1; Enter on door_1, Enter + Leave on door_2 (walked in by one door, out by the other):
// the overlay must go off at once (door_1's lighting source released), both portals Leaving, and after
// UnloadDelaySeconds the sublevel and the zone unloaded with both portals Idle. Then the pending-sibling branch of
// OnUnloadDelayElapsed (review R3-state-01), twice: Enter + Leave on door_1 while door_2 is Pending without an
// interior request (the player debouncing in its box); door_1's unload delay must end in "unload postponed" with
// door_1 still Leaving and the interior loaded. Step 1: door_2 activates before the retry -> door_1 Idle with the
// interior and the sublevel kept, released after Leave on door_2. Step 2: door_2 goes Idle -> the retry unloads.
// All pass under -nullrhi.
//
// Headless: .\tools\ue\test.ps1 -Filter Golmok.Portal   (or in the editor console: Automation RunTests Golmok.Portal)

#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Components/BoxComponent.h"
#include "Editor.h"
#include "Engine/World.h"
#include "GameFramework/DefaultPawn.h"
#include "GameFramework/PlayerController.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Misc/PackageName.h"
#include "Portals/GolmokLevelStreaming.h"
#include "Portals/GolmokPortal.h"
#include "Tests/AutomationEditorCommon.h"
#include "Zones/GolmokZone.h"
#include "Zones/GolmokZoneManifest.h"
#include "Zones/GolmokZoneSubsystem.h"

namespace GolmokPortalTest
{
	const TCHAR* DevMap = TEXT("/Game/Golmok/Maps/L_Dev");
	const TCHAR* ZoneTestMap = TEXT("/Game/Golmok/Maps/L_ZoneTest");
	const TCHAR* ExteriorZoneId = TEXT("z_synthetic_001");
	const TCHAR* InteriorZoneId = TEXT("z_synthetic_001_interior");
	const TCHAR* EntryPortalId = TEXT("door_1");
	const TCHAR* SecondPortalId = TEXT("door_2");
	const TCHAR* ExpectedSublevel = TEXT("/Game/Golmok/Zones/z_synthetic_001_interior/v1/L_z_synthetic_001_interior");
	/** AGolmokPortal::LastEvent of OnUnloadDelayElapsed's postpone and keep branches (SharedInterior pending steps). */
	const TCHAR* PostponedEvent = TEXT("unload postponed; another portal is pending");
	const TCHAR* KeptEvent = TEXT("released; interior kept by another portal");

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
				Zone->bAsyncLoad = false; // WP-09: this test keeps the synchronous path (Golmok.Zone.AsyncLoad covers async)
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

			case 1: // find the entry portal and enter (cycle 1, 2 and the final one before the exterior unload)
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
				Test->TestTrue(FString::Printf(TEXT("EnterInterior (cycle %d)"), Cycle), Portal->EnterInterior(Msg));
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
				bool bReady = false;
				if (CheckInteriorReady(World, Subsystem, Portal, bReady))
				{
					return true;
				}
				if (!bReady)
				{
					return false;
				}
				if (Cycle > RoundTripCycles)
				{
					// Last activation: unload the exterior while the portal is Active. Its EndPlay must release the
					// pinned interior zone, the sublevel and the overlay (nothing else does: the orphan-interior rule
					// skips pinned zones).
					FString Msg;
					Test->TestTrue(TEXT("RequestUnload(exterior) while the portal is Active"), Subsystem->RequestUnload(ExteriorZoneId, Msg));
					Test->AddInfo(Msg);
					return Next(4);
				}
				AGolmokTimeOfDay* Tod = AGolmokTimeOfDay::Find(World);
				FString Msg;
				Test->TestTrue(FString::Printf(TEXT("LeaveInterior (cycle %d)"), Cycle), Portal->LeaveInterior(Msg));
				Test->AddInfo(Msg);
				Test->TestFalse(TEXT("interior lighting overlay off right after LeaveInterior"), Tod && Tod->IsInterior());
				UnloadDeadline = static_cast<double>(Portal->UnloadDelaySeconds) + 1.0;
				return Next(3);
			}

			case 3: // within UnloadDelaySeconds + 1: sublevel unloaded, zone unloaded, portal Idle; then the next cycle
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
				Test->AddInfo(FString::Printf(TEXT("cycle %d: interior released after %.2f s: %s"), Cycle, Elapsed, *Portal->Describe()));
				// Cycle 2 catches a stream-out that drops a registered NamedStreamingLevel entry (re-entry then fails).
				++Cycle;
				return Next(1);
			}

			case 4: // within StreamInTimeoutSeconds: portal destroyed with the exterior; interior zone, sublevel, overlay released
			{
				AGolmokZone* Interior = Subsystem->FindZone(InteriorZoneId);
				AGolmokTimeOfDay* Tod = AGolmokTimeOfDay::Find(World);
				const bool bPortalGone = !PortalActor.IsValid();
				const bool bZoneGone = !Interior || !Interior->IsLoaded();
				const bool bSublevelGone = !GolmokLevelStreaming::IsLoaded(World, ExpectedSublevel);
				const bool bOverlayOff = !Tod || !Tod->IsInterior();
				if (!(bPortalGone && bZoneGone && bSublevelGone && bOverlayOff))
				{
					if (Elapsed < StreamInTimeoutSeconds)
					{
						return false;
					}
					Test->TestTrue(TEXT("portal destroyed with its exterior zone"), bPortalGone);
					Test->TestTrue(TEXT("pinned interior zone unloaded after the portal's EndPlay"), bZoneGone);
					Test->TestTrue(TEXT("sublevel unloaded after the portal's EndPlay"), bSublevelGone);
					Test->TestTrue(TEXT("interior lighting overlay off after the portal's EndPlay"), bOverlayOff);
					return true;
				}
				Test->AddInfo(FString::Printf(TEXT("exterior unload released the interior after %.2f s"), Elapsed));
				return true;
			}

			default:
				return true;
			}
		}

	private:
		/** True when the phase must end (timeout failures recorded); otherwise bOutReady says whether the interior is up. */
		bool CheckInteriorReady(UWorld* World, UGolmokZoneSubsystem* Subsystem, AGolmokPortal* Portal, bool& bOutReady)
		{
			bOutReady = false;
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
				Test->TestTrue(FString::Printf(TEXT("sublevel visible after EnterInterior (cycle %d)"), Cycle), bSublevel);
				Test->TestNotNull(TEXT("interior zone actor placed in L_ZoneTest"), Interior);
				Test->TestTrue(FString::Printf(TEXT("interior zone loaded after EnterInterior (cycle %d)"), Cycle), bZone);
				Test->TestNotNull(TEXT("AGolmokTimeOfDay present"), Tod);
				Test->TestTrue(FString::Printf(TEXT("interior lighting overlay on after EnterInterior (cycle %d)"), Cycle), bOverlay);
				return true;
			}
			Test->AddInfo(FString::Printf(TEXT("cycle %d: interior ready after %.2f s: %s"), Cycle, Elapsed, *Portal->Describe()));
			Test->TestEqual(TEXT("portal state Active"), static_cast<int32>(Portal->State), static_cast<int32>(EGolmokPortalState::Active));
			bOutReady = true;
			return false;
		}

		static constexpr double StreamInTimeoutSeconds = 5.0; // WP-09: async interior load + sublevel streaming (upper bound only)
		/** Full Enter / Leave cycles before the final Enter + exterior unload. */
		static constexpr int32 RoundTripCycles = 2;
		TWeakObjectPtr<AGolmokPortal> PortalActor;
		double UnloadDeadline = 4.0;
		int32 Cycle = 1;
	};

	// ---- shared steps of the PawnSwap / SharedInterior scenarios ---------------------------------------------------

	/** Interior up: sublevel visible, interior zone loaded, overlay on (records the failures once Timeout passed). */
	bool InteriorReady(FAutomationTestBase* Test, UWorld* World, UGolmokZoneSubsystem* Subsystem, AGolmokPortal* Portal, double Elapsed,
		double Timeout, bool& bOutDone)
	{
		bOutDone = false;
		AGolmokZone* Interior = Subsystem->FindZone(InteriorZoneId);
		AGolmokTimeOfDay* Tod = AGolmokTimeOfDay::Find(World);
		const bool bSublevel = Portal->IsSublevelVisible();
		const bool bZone = Interior && Interior->IsLoaded();
		const bool bOverlay = Tod && Tod->IsInterior();
		if (bSublevel && bZone && bOverlay)
		{
			return true;
		}
		if (Elapsed >= Timeout)
		{
			Test->AddInfo(Portal->Describe());
			Test->TestTrue(TEXT("sublevel visible after EnterInterior"), bSublevel);
			Test->TestTrue(TEXT("interior zone loaded after EnterInterior"), bZone);
			Test->TestTrue(TEXT("interior lighting overlay on after EnterInterior"), bOverlay);
			bOutDone = true;
		}
		return false;
	}

	/** Interior down: sublevel unloaded, zone unloaded, Portal Idle (records the failures once Timeout passed). */
	bool InteriorReleased(FAutomationTestBase* Test, UWorld* World, UGolmokZoneSubsystem* Subsystem, AGolmokPortal* Portal, double Elapsed,
		double Timeout, bool& bOutDone)
	{
		bOutDone = false;
		AGolmokZone* Interior = Subsystem->FindZone(InteriorZoneId);
		const bool bSublevelGone = !GolmokLevelStreaming::IsLoaded(World, ExpectedSublevel);
		const bool bZoneGone = !Interior || !Interior->IsLoaded();
		const bool bIdle = Portal->State == EGolmokPortalState::Idle;
		if (bSublevelGone && bZoneGone && bIdle)
		{
			return true;
		}
		if (Elapsed >= Timeout)
		{
			Test->AddInfo(Portal->Describe());
			Test->TestTrue(TEXT("sublevel unloaded after the unload delay"), bSublevelGone);
			Test->TestTrue(TEXT("interior zone unloaded after the unload delay"), bZoneGone);
			Test->TestTrue(TEXT("portal back to Idle after the unload delay"), bIdle);
			bOutDone = true;
		}
		return false;
	}

	/** Point Meters along the door's forward axis (+ = interior side), 1 m up so a pawn stands rather than sinks. */
	FVector PointAlongDoor(const AGolmokPortal* Portal, double Meters)
	{
		return Portal->GetActorLocation() + Portal->GetActorForwardVector() * (Meters * 100.0) + FVector(0.0, 0.0, 100.0);
	}

	// ---- Golmok.Portal.PawnSwap ---------------------------------------------------------------------------------

	class FPawnSwapScenario : public FPortalScenarioBase
	{
	public:
		explicit FPawnSwapScenario(FAutomationTestBase* InTest) : FPortalScenarioBase(InTest) {}

		virtual bool Update() override
		{
			bool bDone = false;
			UWorld* World = BeginUpdate(bDone);
			if (!World)
			{
				return bDone;
			}
			UGolmokZoneSubsystem* Subsystem = World->GetSubsystem<UGolmokZoneSubsystem>();
			APlayerController* PC = World->GetFirstPlayerController();
			if (!Subsystem || !PC)
			{
				Test->AddError(TEXT("no UGolmokZoneSubsystem / player controller in the PIE world"));
				return true;
			}

			switch (Phase)
			{
			case 0: // settle, load the exterior zone (spawns door_1)
				if (Elapsed < 0.5)
				{
					return false;
				}
				{
					FString Msg;
					if (!Subsystem->RequestLoad(ExteriorZoneId, /*bPin*/ true, Msg))
					{
						Test->AddError(FString::Printf(TEXT("exterior zone %s could not be loaded: %s"), ExteriorZoneId, *Msg));
						return true;
					}
				}
				return Next(1);

			case 1: // character 6 m outside the door (not in the 1.5 m box), EnterInterior by console path
			{
				AGolmokPortal* Portal = AGolmokPortal::FindPortal(World, EntryPortalId);
				APawn* Pawn = PC->GetPawn();
				if (!Portal || !Pawn)
				{
					return Fail(TEXT("entry portal door_1 / player pawn not found"), 10.0, Elapsed);
				}
				PortalActor = Portal;
				Character = Pawn;
				Pawn->SetActorLocation(PointAlongDoor(Portal, -6.0), false, nullptr, ETeleportType::TeleportPhysics);
				Test->TestTrue(TEXT("character stands on the exterior side"), Portal->SignedDistanceAlongForward(Pawn->GetActorLocation()) < 0.0);
				Test->TestFalse(TEXT("character does not overlap the trigger"), Portal->bPlayerOverlapping);
				FString Msg;
				Test->TestTrue(TEXT("EnterInterior"), Portal->EnterInterior(Msg));
				Test->AddInfo(Msg);
				return Next(2);
			}

			case 2: // interior up, then possess a pawn inside the room and the character again (playback start / end)
			{
				AGolmokPortal* Portal = PortalActor.Get();
				if (!Portal)
				{
					Test->AddError(TEXT("portal disappeared after EnterInterior"));
					return true;
				}
				if (!InteriorReady(Test, World, Subsystem, Portal, Elapsed, StreamInTimeoutSeconds, bDone))
				{
					return bDone;
				}
				Test->TestTrue(TEXT("portal inside after EnterInterior"), Portal->bPlayerInside);
				FActorSpawnParameters Params;
				Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
				ADefaultPawn* Inside = World->SpawnActor<ADefaultPawn>(ADefaultPawn::StaticClass(), PointAlongDoor(Portal, 5.0), FRotator::ZeroRotator, Params);
				if (!Test->TestNotNull(TEXT("pawn spawned 5 m inside the room"), Inside))
				{
					return true;
				}
				InsidePawn = Inside;
				AGolmokTimeOfDay* Tod = AGolmokTimeOfDay::Find(World);
				// Playback start: the possessed pawn is in the room -> nothing changes.
				PC->Possess(Inside);
				Test->TestTrue(TEXT("player pawn is the inside pawn"), PC->GetPawn() == Inside);
				Test->TestTrue(TEXT("still inside after possessing a pawn in the room"), Portal->bPlayerInside);
				Test->TestTrue(TEXT("overlay still on after possessing a pawn in the room"), Tod && Tod->IsInterior());
				Test->TestEqual(TEXT("portal still Active"), static_cast<int32>(Portal->State), static_cast<int32>(EGolmokPortalState::Active));
				// Playback end: the character outside is possessed again -> the overlay goes off, the unload delay starts.
				PC->Possess(Character.Get());
				Test->TestTrue(TEXT("player pawn is the character again"), PC->GetPawn() == Character.Get());
				Test->AddInfo(Portal->Describe());
				Test->TestFalse(TEXT("portal outside after the character (outside) is possessed"), Portal->bPlayerInside);
				Test->TestFalse(TEXT("interior lighting overlay off after the swap back"), Tod && Tod->IsInterior());
				Test->TestEqual(TEXT("portal Leaving after the swap back"), static_cast<int32>(Portal->State), static_cast<int32>(EGolmokPortalState::Leaving));
				UnloadDeadline = static_cast<double>(Portal->UnloadDelaySeconds) + 1.0;
				return Next(3);
			}

			case 3: // released after the unload delay
			{
				AGolmokPortal* Portal = PortalActor.Get();
				if (!Portal)
				{
					Test->AddError(TEXT("portal disappeared during the unload delay"));
					return true;
				}
				if (!InteriorReleased(Test, World, Subsystem, Portal, Elapsed, UnloadDeadline, bDone))
				{
					if (bDone)
					{
						Cleanup();
					}
					return bDone;
				}
				Test->AddInfo(FString::Printf(TEXT("interior released after %.2f s: %s"), Elapsed, *Portal->Describe()));
				Cleanup();
				return true;
			}

			default:
				return true;
			}
		}

	private:
		void Cleanup()
		{
			if (InsidePawn.IsValid())
			{
				InsidePawn->Destroy();
			}
		}

		static constexpr double StreamInTimeoutSeconds = 5.0; // WP-09: async interior load + sublevel streaming (upper bound only)
		TWeakObjectPtr<AGolmokPortal> PortalActor;
		TWeakObjectPtr<APawn> Character;
		TWeakObjectPtr<ADefaultPawn> InsidePawn;
		double UnloadDeadline = 4.0;
	};

	// ---- Golmok.Portal.SharedInterior ---------------------------------------------------------------------------

	class FSharedInteriorScenario : public FPortalScenarioBase
	{
	public:
		explicit FSharedInteriorScenario(FAutomationTestBase* InTest) : FPortalScenarioBase(InTest) {}

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
			case 0: // settle, load the exterior zone (spawns door_1)
				if (Elapsed < 0.5)
				{
					return false;
				}
				{
					FString Msg;
					if (!Subsystem->RequestLoad(ExteriorZoneId, /*bPin*/ true, Msg))
					{
						Test->AddError(FString::Printf(TEXT("exterior zone %s could not be loaded: %s"), ExteriorZoneId, *Msg));
						return true;
					}
				}
				return Next(1);

			case 1: // spawn door_2 (same interior) 10 m beside door_1, then Enter on door_1
			{
				AGolmokPortal* A = AGolmokPortal::FindPortal(World, EntryPortalId);
				if (!A)
				{
					return Fail(TEXT("entry portal door_1 not found"), 10.0, Elapsed);
				}
				PortalA = A;
				FTransform T = A->GetActorTransform();
				T.SetLocation(T.GetLocation() + A->GetActorRightVector() * 1000.0);
				FActorSpawnParameters Params;
				Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
				Params.ObjectFlags = EObjectFlags(Params.ObjectFlags | RF_Transient);
				Params.bDeferConstruction = true;
				AGolmokPortal* B = World->SpawnActor<AGolmokPortal>(AGolmokPortal::StaticClass(), T, Params);
				if (!Test->TestNotNull(TEXT("second entry portal spawned"), B))
				{
					return true;
				}
				// The manifest fields Configure() would fill, copied from door_1 (same interior, same sublevel).
				B->PortalId = SecondPortalId;
				B->OwnerZoneId = A->OwnerZoneId;
				B->TargetZoneId = A->TargetZoneId;
				B->Kind = A->Kind;
				B->RadiusCm = A->RadiusCm;
				B->bIsEntry = true;
				B->SublevelPackagePath = A->SublevelPackagePath;
				B->FinishSpawning(T);
				PortalB = B;
				Test->TestTrue(TEXT("door_2 is an entry portal into the same interior"), B->bIsEntry && B->TargetZoneId == A->TargetZoneId);
				FString Msg;
				Test->TestTrue(TEXT("EnterInterior(door_1)"), A->EnterInterior(Msg));
				Test->AddInfo(Msg);
				return Next(2);
			}

			case 2: // interior up through door_1; Enter + Leave on door_2
			{
				AGolmokPortal* A = PortalA.Get();
				AGolmokPortal* B = PortalB.Get();
				if (!A || !B)
				{
					Test->AddError(TEXT("a portal disappeared after EnterInterior"));
					Cleanup();
					return true;
				}
				if (!InteriorReady(Test, World, Subsystem, A, Elapsed, StreamInTimeoutSeconds, bDone))
				{
					if (bDone)
					{
						Cleanup();
					}
					return bDone;
				}
				AGolmokTimeOfDay* Tod = AGolmokTimeOfDay::Find(World);
				FString Msg;
				Test->TestTrue(TEXT("EnterInterior(door_2) (already loaded through door_1)"), B->EnterInterior(Msg));
				Test->AddInfo(Msg);
				Test->TestTrue(TEXT("overlay on with both doors inside"), Tod && Tod->IsInterior());
				Test->TestTrue(TEXT("LeaveInterior(door_2)"), B->LeaveInterior(Msg));
				Test->AddInfo(Msg);
				Test->AddInfo(A->Describe());
				Test->AddInfo(B->Describe());
				Test->TestFalse(TEXT("overlay off right after leaving through door_2 (door_1's source released)"), Tod && Tod->IsInterior());
				Test->TestFalse(TEXT("door_1 outside after the player left through door_2"), A->bPlayerInside);
				Test->TestEqual(TEXT("door_1 Leaving"), static_cast<int32>(A->State), static_cast<int32>(EGolmokPortalState::Leaving));
				Test->TestEqual(TEXT("door_2 Leaving"), static_cast<int32>(B->State), static_cast<int32>(EGolmokPortalState::Leaving));
				UnloadDeadline = static_cast<double>(FMath::Max(A->UnloadDelaySeconds, B->UnloadDelaySeconds)) + 1.0;
				return Next(3);
			}

			case 3: // both Idle, interior released once (the two-door pass, then the end of each pending-sibling step)
			{
				AGolmokPortal* A = PortalA.Get();
				AGolmokPortal* B = PortalB.Get();
				if (!A || !B)
				{
					Test->AddError(TEXT("a portal disappeared during the unload delay"));
					Cleanup();
					return true;
				}
				if (!InteriorReleased(Test, World, Subsystem, A, Elapsed, UnloadDeadline, bDone))
				{
					if (bDone)
					{
						Test->TestEqual(TEXT("door_2 Idle after the unload delay"), static_cast<int32>(B->State), static_cast<int32>(EGolmokPortalState::Idle));
						Cleanup();
					}
					return bDone;
				}
				if (B->State != EGolmokPortalState::Idle)
				{
					if (Elapsed < UnloadDeadline)
					{
						return false;
					}
					Test->AddInfo(B->Describe());
					Test->TestEqual(TEXT("door_2 Idle after the unload delay"), static_cast<int32>(B->State), static_cast<int32>(EGolmokPortalState::Idle));
					Cleanup();
					return true;
				}
				Test->AddInfo(FString::Printf(TEXT("%sinterior released after %.2f s: %s | %s"), StepPrefix(), Elapsed, *A->Describe(), *B->Describe()));
				if (PendingStep < 2)
				{
					++PendingStep;
					return Next(4);
				}
				Cleanup();
				return true;
			}

			case 4: // pending-sibling step: enter through door_1 again (one update after the release, as RoundTrip's next cycle)
			{
				AGolmokPortal* A = PortalA.Get();
				if (!A || !PortalB.IsValid())
				{
					Test->AddError(TEXT("a portal disappeared after the release"));
					Cleanup();
					return true;
				}
				FString Msg;
				Test->TestTrue(FString::Printf(TEXT("EnterInterior(door_1) (step %d)"), PendingStep), A->EnterInterior(Msg));
				Test->AddInfo(Msg);
				return Next(5);
			}

			case 5: // interior up through door_1; Leave on door_1 while door_2 is Pending without an interior request
			{
				AGolmokPortal* A = PortalA.Get();
				AGolmokPortal* B = PortalB.Get();
				if (!A || !B)
				{
					Test->AddError(TEXT("a portal disappeared after EnterInterior"));
					Cleanup();
					return true;
				}
				if (!InteriorReady(Test, World, Subsystem, A, Elapsed, StreamInTimeoutSeconds, bDone))
				{
					if (bDone)
					{
						Cleanup();
					}
					return bDone;
				}
				FString Msg;
				Test->TestTrue(FString::Printf(TEXT("LeaveInterior(door_1) (step %d)"), PendingStep), A->LeaveInterior(Msg));
				Test->AddInfo(Msg);
				Test->TestEqual(TEXT("door_1 Leaving"), static_cast<int32>(A->State), static_cast<int32>(EGolmokPortalState::Leaving));
				Test->TestEqual(TEXT("door_2 Idle before it turns Pending"), static_cast<int32>(B->State), static_cast<int32>(EGolmokPortalState::Idle));
				// door_2 as BeginPlayerOverlap leaves an Idle portal until its next-tick preload: Pending, interior not
				// requested, the only state HasPendingSibling counts. The WP-09 preload shortens that window to one tick,
				// so the state is set here (as Travel.Teleport does for its portal check) instead of walking a pawn into
				// door_2's box. No timer runs on door_2; the step decides how its debounce ends (phase 6).
				B->State = EGolmokPortalState::Pending;
				B->bInteriorRequested = false;
				Test->AddInfo(B->Describe());
				UnloadDeadline = static_cast<double>(A->UnloadDelaySeconds) + 1.0;
				return Next(6);
			}

			case 6: // door_1's unload delay ends while door_2 is Pending: postponed, door_1 still Leaving, interior loaded
			{
				AGolmokPortal* A = PortalA.Get();
				AGolmokPortal* B = PortalB.Get();
				if (!A || !B)
				{
					Test->AddError(TEXT("a portal disappeared during the unload delay"));
					Cleanup();
					return true;
				}
				if (A->LastEvent != PostponedEvent)
				{
					if (A->State == EGolmokPortalState::Leaving && Elapsed < UnloadDeadline)
					{
						return false;
					}
					Test->AddInfo(A->Describe());
					Test->TestEqual(TEXT("door_1 postponed its unload while door_2 was pending"), A->LastEvent, FString(PostponedEvent));
					Cleanup();
					return true;
				}
				AGolmokZone* Interior = Subsystem->FindZone(InteriorZoneId);
				Test->AddInfo(FString::Printf(TEXT("%sunload postponed after %.2f s: %s | %s"), StepPrefix(), Elapsed, *A->Describe(), *B->Describe()));
				Test->TestEqual(TEXT("door_1 still Leaving while the unload is postponed"), static_cast<int32>(A->State),
					static_cast<int32>(EGolmokPortalState::Leaving));
				Test->TestTrue(TEXT("interior zone still loaded while the unload is postponed"), Interior && Interior->IsLoaded());
				Test->TestTrue(TEXT("sublevel still loaded while the unload is postponed"), A->IsSublevelLoaded());
				// door_1 asks again after DebounceSeconds + 0.05 (OnUnloadDelayElapsed); door_2's debounce ends before that.
				UnloadDeadline = static_cast<double>(A->DebounceSeconds) + 0.05 + 1.0;
				if (PendingStep == 1)
				{
					// Debounce over with the player in door_2's box: door_2 requests the (still loaded) interior and activates.
					FString Msg;
					Test->TestTrue(TEXT("EnterInterior(door_2) while door_1's unload is postponed"), B->EnterInterior(Msg));
					Test->AddInfo(Msg);
					return Next(7);
				}
				// Debounce over with the player gone and nothing requested: OnDebounceElapsed's plain Idle.
				B->State = EGolmokPortalState::Idle;
				return Next(3);
			}

			case 7: // step 1: door_1's retry finds door_2 Active -> door_1 Idle, interior and sublevel kept; then Leave on door_2
			{
				AGolmokPortal* A = PortalA.Get();
				AGolmokPortal* B = PortalB.Get();
				if (!A || !B)
				{
					Test->AddError(TEXT("a portal disappeared during the postponed unload"));
					Cleanup();
					return true;
				}
				if (A->State != EGolmokPortalState::Idle)
				{
					if (Elapsed < UnloadDeadline)
					{
						return false;
					}
					Test->AddInfo(A->Describe());
					Test->TestEqual(TEXT("door_1 Idle after the postponed unload"), static_cast<int32>(A->State), static_cast<int32>(EGolmokPortalState::Idle));
					Cleanup();
					return true;
				}
				AGolmokZone* Interior = Subsystem->FindZone(InteriorZoneId);
				AGolmokTimeOfDay* Tod = AGolmokTimeOfDay::Find(World);
				Test->AddInfo(FString::Printf(TEXT("%sinterior kept after %.2f s: %s | %s"), StepPrefix(), Elapsed, *A->Describe(), *B->Describe()));
				Test->TestEqual(TEXT("door_1 released with the interior kept by door_2"), A->LastEvent, FString(KeptEvent));
				Test->TestEqual(TEXT("door_2 Active"), static_cast<int32>(B->State), static_cast<int32>(EGolmokPortalState::Active));
				Test->TestTrue(TEXT("interior zone kept loaded by door_2"), Interior && Interior->IsLoaded());
				Test->TestTrue(TEXT("sublevel kept visible by door_2"), B->IsSublevelVisible());
				FString Msg;
				Test->TestTrue(TEXT("LeaveInterior(door_2) (step 1)"), B->LeaveInterior(Msg));
				Test->AddInfo(Msg);
				Test->TestFalse(TEXT("overlay off right after leaving through door_2 (step 1)"), Tod && Tod->IsInterior());
				Test->TestEqual(TEXT("door_2 Leaving (step 1)"), static_cast<int32>(B->State), static_cast<int32>(EGolmokPortalState::Leaving));
				UnloadDeadline = static_cast<double>(B->UnloadDelaySeconds) + 1.0;
				return Next(3);
			}

			default:
				return true;
			}
		}

	private:
		void Cleanup()
		{
			if (PortalB.IsValid())
			{
				PortalB->Destroy();
			}
		}

		/** Info-line prefix: none for the two-door pass (runbook line unchanged), the step for the pending-sibling steps. */
		const TCHAR* StepPrefix() const
		{
			return PendingStep == 1 ? TEXT("step 1 (pending door_2 activates): ")
				   : PendingStep == 2 ? TEXT("step 2 (pending door_2 goes idle): ")
									  : TEXT("");
		}

		static constexpr double StreamInTimeoutSeconds = 5.0; // WP-09: async interior load + sublevel streaming (upper bound only)
		TWeakObjectPtr<AGolmokPortal> PortalA;
		TWeakObjectPtr<AGolmokPortal> PortalB;
		double UnloadDeadline = 4.0;
		/** 0 = two-door pass; 1 = pending door_2 activates (interior kept); 2 = pending door_2 goes idle (interior unloaded). */
		int32 PendingStep = 0;
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

	// L_ZoneTest exists from WP-04 already (built without interior=True); the interior sublevel package is what
	// run(interior=True) adds, so the skip keys on that (design section 8-6 / runbook step 1).
	const FString InteriorSublevel = GolmokZoneManifest::SublevelPackagePath(InteriorZoneId, 1);
	if (!FPackageName::DoesPackageExist(ZoneTestMap) || !FPackageName::DoesPackageExist(InteriorSublevel))
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

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokPortalPawnSwapTest, "Golmok.Portal.PawnSwap",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokPortalPawnSwapTest::RunTest(const FString& Parameters)
{
	using namespace GolmokPortalTest;

	if (!FPackageName::DoesPackageExist(ZoneTestMap) || !FPackageName::DoesPackageExist(GolmokZoneManifest::SublevelPackagePath(InteriorZoneId, 1)))
	{
		AddInfo(TEXT("skipped: run synthetic_zone.run(interior=True)"));
		return true;
	}

	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(ZoneTestMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FPawnSwapScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokPortalSharedInteriorTest, "Golmok.Portal.SharedInterior",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokPortalSharedInteriorTest::RunTest(const FString& Parameters)
{
	using namespace GolmokPortalTest;

	if (!FPackageName::DoesPackageExist(ZoneTestMap) || !FPackageName::DoesPackageExist(GolmokZoneManifest::SublevelPackagePath(InteriorZoneId, 1)))
	{
		AddInfo(TEXT("skipped: run synthetic_zone.run(interior=True)"));
		return true;
	}

	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(ZoneTestMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FSharedInteriorScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

#endif
