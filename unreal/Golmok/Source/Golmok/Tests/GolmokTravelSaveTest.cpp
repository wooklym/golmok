// Zone travel and save tests (WP-15a, docs/plan/WP-15-zone-travel-save.md §6). Both run in PIE on L_ZoneTest (skipped
// with an Info line when the map is missing) and pass under -nullrhi (no collision assets: the pawn may fall after a
// teleport, so arrivals are checked with GetLastArrivalLocationUE(), the location set before any movement tick).
//
// Golmok.Travel.Teleport: an unknown zone is refused; photo mode refuses a travel (skipped when Enter() is refused);
// z_synthetic_001_interior is redirected to its parent z_synthetic_001 and arrives at the manifest spawn (feet + capsule
// half height + clearance, UE Yaw from yaw_deg) with the pin released a tick later and OnTraveled fired once; a portal
// that is not Idle refuses; a second request while traveling is refused; z_synthetic_002 (spawned from the index when
// not discovered yet) arrives at its spawn; without a spawn GetSpawnUE falls back to the zone origin's XY with the
// zone's +x heading; with bSimulateLoadStall and a 0.3 s timeout the travel fails with "timeout", the pin released and
// no arrival counted.
// Golmok.Save.RoundTrip: on the test slot golmok_test_wp15a (automatic saves off) an empty slot restores nothing (rule
// 3); a synchronous save -> LoadSlot keeps lat / lon of the pawn exactly (1 mm after LonLatToLevelUE), the ENU yaw
// (= -UE Yaw), the visit and both photo entries; Restore puts the pawn back within 1 mm / 0.01 deg and drops the photo
// whose file is missing; a saved version 99 restores to the zone's spawn (rule 2); a zone that is gone restores
// nothing without HomeZoneId and to HomeZoneId's spawn with it (rule 2). Then, with automatic saves on for that step only,
// golmok.save reset while standing in a zone (R49-1): direct and timer visit polls neither record that zone nor recreate
// the slot; after leaving it and coming back it is a first visit again and the slot is written. The slot and the test
// photo are deleted at the end.
//
// Headless: .\tools\ue\test.ps1 -Filter Golmok.Travel   /   -Filter Golmok.Save

#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Components/CapsuleComponent.h"
#include "Editor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Geo/GolmokGeo.h"
#include "Geo/GolmokGeoSubsystem.h"
#include "HAL/FileManager.h"
#include "Kismet/GameplayStatics.h"
#include "Map/GolmokTravelMath.h"
#include "Map/GolmokTravelSubsystem.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Photo/GolmokPhotoModeSubsystem.h"
#include "Portals/GolmokPortal.h"
#include "Save/GolmokSaveGame.h"
#include "Save/GolmokSaveSubsystem.h"
#include "Tests/AutomationEditorCommon.h"
#include "Zones/GolmokZone.h"
#include "Zones/GolmokZoneSubsystem.h"

namespace GolmokTravelSaveTest
{
	const TCHAR* ZoneTestMap = TEXT("/Game/Golmok/Maps/L_ZoneTest");
	const TCHAR* ExteriorZoneId = TEXT("z_synthetic_001");
	const TCHAR* InteriorZoneId = TEXT("z_synthetic_001_interior");
	const TCHAR* SecondZoneId = TEXT("z_synthetic_002");
	const TCHAR* TestSlot = TEXT("golmok_test_wp15a");
	const TCHAR* TestPhotoRel = TEXT("Screenshots/Golmok/photo/wp15a_test.png");
	const TCHAR* MissingPhotoRel = TEXT("Screenshots/Golmok/photo/wp15a_missing.png");
	constexpr double TravelWaitSeconds = 25.0; // TravelTimeoutSeconds (20) + margin
	constexpr double ToleranceCm = 0.1;        // 1 mm

	/** Expected standing location / yaw for a zone's spawn (what UGolmokTravelSubsystem::Arrive computes). */
	bool ExpectedArrival(AGolmokZone& Zone, APawn* Pawn, FVector& OutLocation, float& OutYaw)
	{
		FVector Feet = FVector::ZeroVector;
		if (!Zone.GetSpawnUE(Feet, OutYaw))
		{
			return false;
		}
		double Half = 88.0;
		if (const ACharacter* Character = Cast<ACharacter>(Pawn))
		{
			Half = Character->GetCapsuleComponent() ? Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() : Half;
		}
		const GolmokTravelMath::Vec3 S = GolmokTravelMath::StandingLocationUE(GolmokTravelMath::Vec3{Feet.X, Feet.Y, Feet.Z}, Half);
		OutLocation = FVector(S[0], S[1], S[2]);
		return true;
	}

	/**
	 * Independent expectation for a manifest spawn (not GetSpawnUE's matrix path): the zone root FTransform applied to
	 * GolmokGeo::EnuToUE(position_enu), heading = root yaw + (-yaw_deg) (the zone roots are level: tilt << 0.01 deg).
	 */
	bool IndependentSpawn(const AGolmokZone& Zone, FVector& OutFeet, float& OutYaw)
	{
		if (!Zone.Manifest.bHasSpawn)
		{
			return false;
		}
		OutFeet = Zone.GetActorTransform().TransformPosition(GolmokGeo::EnuToUE(Zone.Manifest.SpawnPositionEnu));
		OutYaw = static_cast<float>(FRotator::NormalizeAxis(Zone.GetActorRotation().Yaw - Zone.Manifest.SpawnYawDeg));
		return true;
	}

	/** Latent scaffolding: PIE world lookup, phase timing, timeout failure (the GolmokZoneTest pattern). */
	class FScenarioBase : public IAutomationLatentCommand
	{
	public:
		explicit FScenarioBase(FAutomationTestBase* InTest) : Test(InTest), CreatedAt(FPlatformTime::Seconds()) {}

	protected:
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

		bool Fail(const TCHAR* What, double Timeout, double InElapsed)
		{
			if (InElapsed < Timeout)
			{
				return false;
			}
			Test->AddError(FString::Printf(TEXT("%s (phase %d, %.1f s)"), What, Phase, InElapsed));
			return true;
		}

		void CheckArrival(UGolmokTravelSubsystem* Travel, AGolmokZone* Zone, APawn* Pawn, const TCHAR* What)
		{
			FVector Expected = FVector::ZeroVector;
			float ExpectedYaw = 0.f;
			if (!Zone || !Test->TestTrue(FString::Printf(TEXT("%s: GetSpawnUE"), What), ExpectedArrival(*Zone, Pawn, Expected, ExpectedYaw)))
			{
				return;
			}
			const FVector Got = Travel->GetLastArrivalLocationUE();
			Test->TestTrue(FString::Printf(TEXT("%s: arrival (%.2f, %.2f, %.2f) = spawn (%.2f, %.2f, %.2f) within 1 mm"), What, Got.X, Got.Y, Got.Z,
							   Expected.X, Expected.Y, Expected.Z),
				Got.Equals(Expected, ToleranceCm));
			Test->TestTrue(FString::Printf(TEXT("%s: yaw %.3f = %.3f"), What, Travel->GetLastArrivalYawUE(), ExpectedYaw),
				FMath::IsNearlyEqual(FRotator::NormalizeAxis(Travel->GetLastArrivalYawUE() - ExpectedYaw), 0.f, 0.01f));
			FVector Feet = FVector::ZeroVector;
			float Yaw = 0.f;
			if (IndependentSpawn(*Zone, Feet, Yaw))
			{
				Test->TestTrue(FString::Printf(TEXT("%s: arrival XY = root transform * EnuToUE(spawn) (%.2f, %.2f)"), What, Feet.X, Feet.Y),
					FMath::IsNearlyEqual(Got.X, Feet.X, ToleranceCm) && FMath::IsNearlyEqual(Got.Y, Feet.Y, ToleranceCm));
				Test->TestTrue(FString::Printf(TEXT("%s: yaw = root yaw - yaw_deg (%.3f)"), What, Yaw),
					FMath::IsNearlyEqual(FRotator::NormalizeAxis(Travel->GetLastArrivalYawUE() - Yaw), 0.f, 0.01f));
			}
		}

		FAutomationTestBase* Test;
		double CreatedAt;
		int32 Phase = 0;
		double PhaseStart = -1.0;
		double Now = 0.0;
		double Elapsed = 0.0;
	};

	// ---- Golmok.Travel.Teleport -----------------------------------------------------------------------------------

	class FTeleportScenario : public FScenarioBase
	{
	public:
		explicit FTeleportScenario(FAutomationTestBase* InTest) : FScenarioBase(InTest) {}

		virtual bool Update() override
		{
			bool bDone = false;
			UWorld* World = BeginUpdate(bDone);
			if (!World)
			{
				return bDone;
			}
			UGolmokTravelSubsystem* Travel = UGolmokTravelSubsystem::Get(World);
			UGolmokZoneSubsystem* Zones = World->GetSubsystem<UGolmokZoneSubsystem>();
			APawn* Pawn = UGameplayStatics::GetPlayerPawn(World, 0);
			if (!Travel || !Zones)
			{
				Test->AddError(TEXT("no UGolmokTravelSubsystem / UGolmokZoneSubsystem in the PIE world"));
				return true;
			}

			switch (Phase)
			{
			case 0: // settle; refusals; interior -> parent
			{
				if (Elapsed < 0.5 || !Pawn)
				{
					return Fail(TEXT("no player pawn"), 10.0, Elapsed);
				}
				FString Message;
				Test->TestFalse(TEXT("unknown zone refused"), Travel->TravelToZone(TEXT("z_does_not_exist"), Message));
				Test->TestTrue(FString::Printf(TEXT("unknown zone message (%s)"), *Message), Message.Contains(TEXT("not in the index")));

				if (UGolmokPhotoModeSubsystem* Photo = World->GetSubsystem<UGolmokPhotoModeSubsystem>())
				{
					FString PhotoMessage;
					if (Photo->Enter(PhotoMessage))
					{
						Test->TestFalse(TEXT("travel refused in photo mode"), Travel->TravelToZone(SecondZoneId, Message));
						Test->TestTrue(FString::Printf(TEXT("photo refusal message (%s)"), *Message), Message.Contains(TEXT("photo")));
						Test->TestFalse(TEXT("no travel started in photo mode"), Travel->IsTraveling());
						Photo->Exit(TEXT("travel test"));
					}
					else
					{
						Test->AddInfo(FString::Printf(TEXT("photo refusal not checked: Enter() refused (%s)"), *PhotoMessage));
					}
				}
				ArrivalsBefore = Travel->GetArrivalCount();
				// Shared array, captured by value: safe even if this command is gone before Restore() unbinds it.
				TraveledHandle = Travel->OnTraveled.AddLambda([Log = Traveled](const FString& ZoneId) { Log->Add(ZoneId); });
				if (!Test->TestTrue(TEXT("travel to the interior starts"), Travel->TravelToZone(InteriorZoneId, Message)))
				{
					Test->AddError(Message);
					return true;
				}
				Test->AddInfo(Message);
				Test->TestTrue(FString::Printf(TEXT("interior redirect named (%s)"), *Message), Message.Contains(TEXT("interior")));
				Test->TestEqual(TEXT("interior redirected to the parent"), Travel->GetTargetZoneId(), FString(ExteriorZoneId));
				Test->TestTrue(TEXT("parent pinned while traveling"), Zones->IsZonePinned(ExteriorZoneId));
				return Next(1);
			}

			case 1: // arrived at z_synthetic_001; portal / busy refusals; travel to z_synthetic_002
			{
				if (Travel->IsTraveling())
				{
					return Fail(TEXT("travel to z_synthetic_001 did not finish"), TravelWaitSeconds, Elapsed);
				}
				Test->TestTrue(FString::Printf(TEXT("no error (%s)"), *Travel->GetLastError()), Travel->GetLastError().IsEmpty());
				Test->TestEqual(TEXT("arrived at z_synthetic_001"), Travel->GetLastArrivedZoneId(), FString(ExteriorZoneId));
				Test->TestEqual(TEXT("one arrival"), Travel->GetArrivalCount(), ArrivalsBefore + 1);
				Test->TestTrue(TEXT("OnTraveled(z_synthetic_001) once"), Traveled->Num() == 1 && (*Traveled)[0] == ExteriorZoneId);
				Test->TestFalse(TEXT("pin released after arrival"), Zones->IsZonePinned(ExteriorZoneId));
				CheckArrival(Travel, Zones->FindZone(ExteriorZoneId), Pawn, TEXT("z_synthetic_001"));
				Test->AddInfo(Travel->DescribeStatus());
				Test->AddInfo(Travel->DescribeList());

				FString Message;
				AGolmokPortal* Portal = nullptr;
				for (TActorIterator<AGolmokPortal> It(World); It; ++It)
				{
					if (It->State == EGolmokPortalState::Idle)
					{
						Portal = *It;
						break;
					}
				}
				if (Portal)
				{
					Portal->State = EGolmokPortalState::Pending; // simulated transition; restored at once (no timer runs)
					Test->TestFalse(TEXT("travel refused while a portal is not Idle"), Travel->TravelToZone(SecondZoneId, Message));
					Test->TestTrue(FString::Printf(TEXT("portal refusal message (%s)"), *Message), Message.Contains(TEXT("portal")));
					Portal->State = EGolmokPortalState::Idle;
				}
				else
				{
					Test->AddInfo(TEXT("portal refusal not checked: no idle AGolmokPortal in the world"));
				}

				if (!Test->TestTrue(TEXT("travel to z_synthetic_002 starts"), Travel->TravelToZone(SecondZoneId, Message)))
				{
					Test->AddError(Message);
					return true;
				}
				Test->AddInfo(Message);
				FString Busy;
				Test->TestFalse(TEXT("second request while traveling refused"), Travel->TravelToZone(ExteriorZoneId, Busy));
				Test->TestTrue(FString::Printf(TEXT("busy message (%s)"), *Busy), Busy.Contains(TEXT("already")));
				Test->TestNotNull(TEXT("z_synthetic_002 actor exists (placed, discovered or spawned for the travel)"), Zones->FindZone(SecondZoneId));
				return Next(2);
			}

			case 2: // arrived at z_synthetic_002; fallback; timeout
			{
				if (Travel->IsTraveling())
				{
					return Fail(TEXT("travel to z_synthetic_002 did not finish"), TravelWaitSeconds, Elapsed);
				}
				Test->TestEqual(TEXT("arrived at z_synthetic_002"), Travel->GetLastArrivedZoneId(), FString(SecondZoneId));
				Test->TestEqual(TEXT("two arrivals"), Travel->GetArrivalCount(), ArrivalsBefore + 2);
				Test->TestFalse(TEXT("z_synthetic_002 pin released"), Zones->IsZonePinned(SecondZoneId));
				AGolmokZone* Second = Zones->FindZone(SecondZoneId);
				CheckArrival(Travel, Second, Pawn, TEXT("z_synthetic_002"));
				if (Second && Second->HasManifest() && Second->Manifest.bHasSpawn)
				{
					// A root turned by 30 deg (the synthetic roots are almost unrotated, so a transposed matrix would hide):
					// GetSpawnUE must still agree with the independent FTransform path. The root is put back at once.
					const FTransform Original = Second->GetActorTransform();
					Second->SetActorRotation(Original.Rotator() + FRotator(0.0, 30.0, 0.0));
					FVector Feet = FVector::ZeroVector, Independent = FVector::ZeroVector;
					float Yaw = 0.f, IndependentYaw = 0.f;
					Test->TestTrue(TEXT("rotated root: GetSpawnUE"), Second->GetSpawnUE(Feet, Yaw));
					IndependentSpawn(*Second, Independent, IndependentYaw);
					Test->TestTrue(FString::Printf(TEXT("rotated root: spawn (%.2f, %.2f, %.2f) = (%.2f, %.2f, %.2f)"), Feet.X, Feet.Y, Feet.Z, Independent.X,
									   Independent.Y, Independent.Z),
						Feet.Equals(Independent, ToleranceCm));
					Test->TestTrue(FString::Printf(TEXT("rotated root: yaw %.3f = %.3f"), Yaw, IndependentYaw),
						FMath::IsNearlyEqual(FRotator::NormalizeAxis(Yaw - IndependentYaw), 0.f, 0.01f));
					Second->SetActorTransform(Original);
				}
				if (Second && Second->HasManifest())
				{
					const bool bHadSpawn = Second->Manifest.bHasSpawn;
					Second->Manifest.bHasSpawn = false; // spec §1 fallback on the same zone
					FVector Feet = FVector::ZeroVector;
					float Yaw = 0.f;
					bool bFromManifest = true;
					Test->TestTrue(TEXT("fallback GetSpawnUE"), Second->GetSpawnUE(Feet, Yaw, &bFromManifest));
					Test->TestFalse(TEXT("fallback not from the manifest"), bFromManifest);
					const FVector Origin = Second->GetActorLocation();
					Test->TestTrue(FString::Printf(TEXT("fallback XY (%.2f, %.2f) = zone origin (%.2f, %.2f)"), Feet.X, Feet.Y, Origin.X, Origin.Y),
						FMath::IsNearlyEqual(Feet.X, Origin.X, ToleranceCm) && FMath::IsNearlyEqual(Feet.Y, Origin.Y, ToleranceCm));
					Test->TestTrue(TEXT("fallback Z within [origin - 50 m, origin + 3 m]"), Feet.Z <= Origin.Z + 300.0 + ToleranceCm && Feet.Z >= Origin.Z - 5000.0);
					Test->TestTrue(FString::Printf(TEXT("fallback yaw %.3f = zone +x heading %.3f"), Yaw, Second->GetActorRotation().Yaw),
						FMath::IsNearlyEqual(FRotator::NormalizeAxis(Yaw - static_cast<float>(Second->GetActorRotation().Yaw)), 0.f, 0.05f));
					Second->Manifest.bHasSpawn = bHadSpawn;
				}

				SavedTimeout = Travel->TravelTimeoutSeconds;
				Travel->TravelTimeoutSeconds = 0.3f;
				Travel->bSimulateLoadStall = true;
				FString Message;
				if (!Test->TestTrue(TEXT("stalled travel starts"), Travel->TravelToZone(ExteriorZoneId, Message)))
				{
					Test->AddError(Message);
					Restore(Travel);
					return true;
				}
				return Next(3);
			}

			case 3: // timeout
			{
				if (Travel->IsTraveling())
				{
					if (Fail(TEXT("stalled travel did not time out"), 5.0, Elapsed))
					{
						Restore(Travel);
						return true;
					}
					return false;
				}
				Test->TestTrue(FString::Printf(TEXT("timeout error (%s)"), *Travel->GetLastError()), Travel->GetLastError().Contains(TEXT("timeout")));
				Test->TestFalse(TEXT("pin released after the timeout"), Zones->IsZonePinned(ExteriorZoneId));
				Test->TestEqual(TEXT("no arrival counted for the timeout"), Travel->GetArrivalCount(), ArrivalsBefore + 2);
				Test->TestTrue(TEXT("HUD shows the failure"), Travel->DescribeHudLine().Contains(TEXT("timeout")));
				Restore(Travel);
				return true;
			}

			default:
				return true;
			}
		}

	private:
		void Restore(UGolmokTravelSubsystem* Travel)
		{
			Travel->bSimulateLoadStall = false;
			if (SavedTimeout > 0.f)
			{
				Travel->TravelTimeoutSeconds = SavedTimeout;
			}
			Travel->OnTraveled.Remove(TraveledHandle);
		}

		TSharedRef<TArray<FString>> Traveled = MakeShared<TArray<FString>>();
		FDelegateHandle TraveledHandle;
		int32 ArrivalsBefore = 0;
		float SavedTimeout = 0.f;
	};

	// ---- Golmok.Save.RoundTrip ------------------------------------------------------------------------------------

	class FSaveRoundTripScenario : public FScenarioBase
	{
	public:
		explicit FSaveRoundTripScenario(FAutomationTestBase* InTest) : FScenarioBase(InTest) {}

		virtual bool Update() override
		{
			bool bDone = false;
			UWorld* World = BeginUpdate(bDone);
			if (!World)
			{
				return bDone;
			}
			UGolmokSaveSubsystem* Save = UGolmokSaveSubsystem::Get(World);
			UGolmokTravelSubsystem* Travel = UGolmokTravelSubsystem::Get(World);
			UGolmokZoneSubsystem* Zones = World->GetSubsystem<UGolmokZoneSubsystem>();
			UGolmokGeoSubsystem* Geo = World->GetSubsystem<UGolmokGeoSubsystem>();
			APawn* Pawn = UGameplayStatics::GetPlayerPawn(World, 0);
			APlayerController* PC = UGameplayStatics::GetPlayerController(World, 0);
			if (!Save || !Travel || !Zones || !Geo)
			{
				Test->AddError(TEXT("no save / travel / zone / geo subsystem in the PIE world"));
				return true;
			}

			switch (Phase)
			{
			case 0: // empty slot; save; slot contents; restore
			{
				if (Elapsed < 1.0 || !Pawn || !PC)
				{
					return Fail(TEXT("no player pawn / controller"), 10.0, Elapsed);
				}
				if (!Geo->HasOrigin())
				{
					Test->AddInfo(TEXT("skipped: L_ZoneTest has no AGolmokGeoOrigin (saves need geodetic positions)"));
					return true;
				}
				OriginalSlot = Save->SlotName;
				OriginalHome = Save->HomeZoneId;
				bOriginalAutomatic = Save->IsAutomaticEnabled();
				bArmed = true;
				Save->SlotName = TestSlot;
				Save->SetAutomaticEnabled(false);
				FString Message;
				Save->ResetSlot(Message);
				Test->TestFalse(TEXT("test slot empty"), Save->HasSave());
				Test->TestFalse(TEXT("empty slot: nothing restored"), Save->Restore(Message));
				Test->TestTrue(TEXT("empty slot: rule 3 (none)"), Save->GetLastRestoreDecision() == GolmokTravelMath::ERestore::None);

				// Index entries: one real file, one missing.
				const FString PhotoFile = FPaths::Combine(FPaths::ProjectSavedDir(), TestPhotoRel);
				TArray<uint8> Bytes = {0x89, 0x50, 0x4E, 0x47};
				Test->TestTrue(TEXT("test photo written"), FFileHelper::SaveArrayToFile(Bytes, *PhotoFile));
				IFileManager::Get().Delete(*FPaths::Combine(FPaths::ProjectSavedDir(), MissingPhotoRel));
				Save->NotePhoto(TestPhotoRel);
				Save->NotePhoto(MissingPhotoRel);
				Save->NoteVisit(SecondZoneId, 1, TEXT("test"));

				PC->SetControlRotation(FRotator(0.0, 37.5, 0.0));
				SavedLocation = Pawn->GetActorLocation();
				if (!Test->TestTrue(TEXT("SaveNow(sync)"), Save->SaveNow(/*bSync*/ true, TEXT("test"), &Message)))
				{
					Test->AddError(Message);
					return Cleanup(Save);
				}
				const UGolmokSaveGame* Slot = Save->LoadSlot();
				if (!Test->TestNotNull(TEXT("LoadSlot"), Slot))
				{
					return Cleanup(Save);
				}
				double Lat = 0.0, Lon = 0.0, H = 0.0;
				Geo->LevelUEToLonLat(SavedLocation, Lat, Lon, H);
				Test->TestEqual(TEXT("SaveSchemaVersion 1"), Slot->SaveSchemaVersion, 1);
				Test->TestTrue(TEXT("bHasPosition"), Slot->bHasPosition);
				Test->TestTrue(FString::Printf(TEXT("lat %.9f / lon %.9f / h %.4f kept"), Slot->Lat, Slot->Lon, Slot->HeightEllipsoidal),
					FMath::IsNearlyEqual(Slot->Lat, Lat, 1e-12) && FMath::IsNearlyEqual(Slot->Lon, Lon, 1e-12) && FMath::IsNearlyEqual(Slot->HeightEllipsoidal, H, 1e-6));
				FVector Back = FVector::ZeroVector;
				Geo->LonLatToLevelUE(Slot->Lon, Slot->Lat, Slot->HeightEllipsoidal, Back);
				Test->TestTrue(FString::Printf(TEXT("lat/lon -> UE within 1 mm (%.4f cm)"), FVector::Dist(Back, SavedLocation)), Back.Equals(SavedLocation, ToleranceCm));
				Test->TestTrue(FString::Printf(TEXT("ENU yaw %.3f = -37.5"), Slot->YawDeg), FMath::IsNearlyEqual(Slot->YawDeg, -37.5, 1e-3));
				const AGolmokZone* Here = Zones->FindLoadedZoneAt(FVector2D(SavedLocation.X, SavedLocation.Y));
				Test->TestEqual(TEXT("zone = loaded zone at the pawn"), Slot->ZoneId, Here ? Here->ZoneId : FString());
				Test->TestNotNull(TEXT("visit kept"), Slot->FindVisit(SecondZoneId));
				Test->TestTrue(TEXT("both photo entries kept"), Slot->Photos.Contains(TestPhotoRel) && Slot->Photos.Contains(MissingPhotoRel));
				Test->TestFalse(TEXT("SavedAtUtc set"), Slot->SavedAtUtc.IsEmpty());
				Test->AddInfo(Save->DescribeStatus());

				// Move away and restore rule 1.
				Pawn->SetActorLocation(SavedLocation + FVector(5000.0, 0.0, 0.0), false, nullptr, ETeleportType::TeleportPhysics);
				PC->SetControlRotation(FRotator::ZeroRotator);
				if (!Test->TestTrue(TEXT("restore (rule 1) starts"), Save->Restore(Message)))
				{
					Test->AddError(Message);
					return Cleanup(Save);
				}
				Test->AddInfo(Message);
				Test->TestTrue(TEXT("rule 1: saved position"), Save->GetLastRestoreDecision() == GolmokTravelMath::ERestore::SavedPosition);
				Test->TestEqual(TEXT("missing photo dropped"), Save->GetPhotos().Num(), 1);
				return Next(1);
			}

			case 1: // rule 1 arrived; rule 2 (version)
			{
				if (Travel->IsTraveling())
				{
					return Fail(TEXT("rule 1 restore travel did not finish"), TravelWaitSeconds, Elapsed) ? Cleanup(Save) : false;
				}
				const FVector Got = Travel->GetLastArrivalLocationUE();
				Test->TestTrue(FString::Printf(TEXT("restored within 1 mm (%.4f cm)"), FVector::Dist(Got, SavedLocation)), Got.Equals(SavedLocation, ToleranceCm));
				Test->TestTrue(FString::Printf(TEXT("restored yaw %.3f = 37.5"), Travel->GetLastArrivalYawUE()),
					FMath::IsNearlyEqual(Travel->GetLastArrivalYawUE(), 37.5f, 0.01f));

				UGolmokSaveGame* Slot = Save->LoadSlot();
				if (!Slot)
				{
					Test->AddError(TEXT("slot vanished"));
					return Cleanup(Save);
				}
				Slot->ZoneId = ExteriorZoneId;
				Slot->ZoneVersion = 99;
				UGameplayStatics::SaveGameToSlot(Slot, Save->SlotName, 0);
				FString Message;
				Test->TestTrue(TEXT("restore (rule 2, version 99) starts"), Save->Restore(Message));
				Test->AddInfo(Message);
				Test->TestTrue(TEXT("rule 2: saved zone spawn"), Save->GetLastRestoreDecision() == GolmokTravelMath::ERestore::SavedZoneSpawn);
				return Next(2);
			}

			case 2: // rule 2 arrived; zone gone without / with HomeZoneId
			{
				if (Travel->IsTraveling())
				{
					return Fail(TEXT("rule 2 restore travel did not finish"), TravelWaitSeconds, Elapsed) ? Cleanup(Save) : false;
				}
				Test->TestEqual(TEXT("rule 2 arrived at z_synthetic_001"), Travel->GetLastArrivedZoneId(), FString(ExteriorZoneId));
				CheckArrival(Travel, Zones->FindZone(ExteriorZoneId), Pawn, TEXT("rule 2 spawn"));

				UGolmokSaveGame* Slot = Save->LoadSlot();
				if (!Slot)
				{
					Test->AddError(TEXT("slot vanished"));
					return Cleanup(Save);
				}
				Slot->ZoneId = TEXT("z_gone_zone");
				Slot->ZoneVersion = 1;
				UGameplayStatics::SaveGameToSlot(Slot, Save->SlotName, 0);
				FString Message;
				Save->HomeZoneId.Reset();
				Test->TestFalse(TEXT("zone gone, no HomeZoneId: nothing restored"), Save->Restore(Message));
				Test->TestTrue(TEXT("rule 3"), Save->GetLastRestoreDecision() == GolmokTravelMath::ERestore::None);
				Save->HomeZoneId = SecondZoneId;
				Test->TestTrue(TEXT("zone gone, HomeZoneId set: restore starts"), Save->Restore(Message));
				Test->AddInfo(Message);
				Test->TestTrue(TEXT("rule 2: home zone spawn"), Save->GetLastRestoreDecision() == GolmokTravelMath::ERestore::HomeZoneSpawn);
				return Next(3);
			}

			case 3:
			{
				if (Travel->IsTraveling())
				{
					return Fail(TEXT("home restore travel did not finish"), TravelWaitSeconds, Elapsed) ? Cleanup(Save) : false;
				}
				Test->TestEqual(TEXT("home restore arrived at z_synthetic_002"), Travel->GetLastArrivedZoneId(), FString(SecondZoneId));
				CheckArrival(Travel, Zones->FindZone(SecondZoneId), Pawn, TEXT("home spawn"));
				return Next(4);
			}

			case 4: // R49-1: golmok.save reset while standing in a zone, automatic saves on: the visit poll must not recreate the slot
			{
				const FVector Here = Pawn ? Pawn->GetActorLocation() : FVector::ZeroVector;
				const AGolmokZone* Present = Pawn ? Zones->FindLoadedZoneAt(FVector2D(Here.X, Here.Y)) : nullptr;
				if (!Present)
				{
					Test->AddInfo(TEXT("reset / visit poll step skipped: the pawn stands in no loaded zone"));
					return Cleanup(Save);
				}
				PresentZoneId = Present->ZoneId;
				PresentLocation = Here;
				Save->SetAutomaticEnabled(true); // this step only: Cleanup puts back the original (off under automation)
				FString Message;
				Save->ResetSlot(Message);
				Test->AddInfo(Message);
				Test->TestFalse(TEXT("reset: slot deleted"), Save->HasSave());
				Test->TestTrue(FString::Printf(TEXT("reset: %s held as the zone the player stands in"), *PresentZoneId),
					Save->GetResetPresentZoneIds().Contains(PresentZoneId));
				Save->PollVisitsNow();
				Save->PollVisitsNow();
				Test->TestFalse(FString::Printf(TEXT("reset: %s is no first visit while the player stays"), *PresentZoneId), Save->IsVisited(PresentZoneId));
				Test->TestEqual(TEXT("reset: the visit poll started no write"), Save->GetPendingAsyncSaves(), 0);
				Test->TestFalse(TEXT("reset: the visit poll did not recreate the slot"), Save->HasSave());
				return Next(5);
			}

			case 5: // the timer polls too; then leave the zone and come back: a normal first visit again
			{
				if (Elapsed < Save->VisitPollSeconds * 2.5)
				{
					return false;
				}
				Test->TestFalse(TEXT("reset: the timer visit polls did not recreate the slot"), Save->HasSave());
				Test->TestFalse(FString::Printf(TEXT("reset: %s still no first visit"), *PresentZoneId), Save->IsVisited(PresentZoneId));
				if (!Pawn)
				{
					Test->AddError(TEXT("no player pawn for the leave / re-enter step"));
					return Cleanup(Save);
				}
				Pawn->SetActorLocation(PresentLocation + FVector(1.0e6, 0.0, 0.0), false, nullptr, ETeleportType::TeleportPhysics); // 10 km away
				Save->PollVisitsNow();
				Test->TestFalse(TEXT("left the zone: no longer held"), Save->GetResetPresentZoneIds().Contains(PresentZoneId));
				Test->TestFalse(TEXT("left the zone: still no slot"), Save->HasSave() || Save->GetPendingAsyncSaves() > 0);
				Pawn->SetActorLocation(PresentLocation, false, nullptr, ETeleportType::TeleportPhysics);
				Save->PollVisitsNow();
				Test->TestTrue(FString::Printf(TEXT("re-entered: %s is a first visit"), *PresentZoneId), Save->IsVisited(PresentZoneId));
				Test->TestTrue(TEXT("re-entered: the slot is written again"), Save->GetPendingAsyncSaves() > 0 || Save->HasSave());
				return Next(6);
			}

			case 6: // the re-entry's async write completes
			{
				if (Save->GetPendingAsyncSaves() > 0)
				{
					return Fail(TEXT("async save after the re-entry did not complete"), 10.0, Elapsed) ? Cleanup(Save) : false;
				}
				Test->TestTrue(TEXT("re-entered: slot exists"), Save->HasSave());
				return Cleanup(Save);
			}

			default:
				return Cleanup(Save);
			}
		}

	private:
		bool Cleanup(UGolmokSaveSubsystem* Save)
		{
			if (bArmed && Save)
			{
				FString Message;
				Save->ResetSlot(Message);
				Save->SlotName = OriginalSlot;
				Save->HomeZoneId = OriginalHome;
				Save->SetAutomaticEnabled(bOriginalAutomatic);
				bArmed = false;
			}
			IFileManager::Get().Delete(*FPaths::Combine(FPaths::ProjectSavedDir(), TestPhotoRel));
			return true;
		}

		FString OriginalSlot;
		FString OriginalHome;
		FString PresentZoneId;
		FVector SavedLocation = FVector::ZeroVector;
		FVector PresentLocation = FVector::ZeroVector;
		bool bOriginalAutomatic = false;
		bool bArmed = false;
	};

	bool SkipWithoutMap(FAutomationTestBase* Test)
	{
		if (!FPackageName::DoesPackageExist(ZoneTestMap))
		{
			Test->AddInfo(TEXT("skipped: /Game/Golmok/Maps/L_ZoneTest missing (run golmok.synthetic_zone.run())"));
			return true;
		}
		return false;
	}
} // namespace GolmokTravelSaveTest

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokTravelTeleportTest, "Golmok.Travel.Teleport",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokTravelTeleportTest::RunTest(const FString& Parameters)
{
	using namespace GolmokTravelSaveTest;
	if (SkipWithoutMap(this))
	{
		return true;
	}
	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(ZoneTestMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FTeleportScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokSaveRoundTripTest, "Golmok.Save.RoundTrip",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokSaveRoundTripTest::RunTest(const FString& Parameters)
{
	using namespace GolmokTravelSaveTest;
	if (SkipWithoutMap(this))
	{
		return true;
	}
	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(ZoneTestMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FSaveRoundTripScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
