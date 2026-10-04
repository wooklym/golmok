// Zone travel and save tests (WP-15a, docs/plan/WP-15-zone-travel-save.md §6). Both run in PIE on L_ZoneTest (skipped
// with an Info line when the map is missing) and pass under -nullrhi (no collision assets: the pawn may fall after a
// teleport, so arrivals are checked with GetLastArrivalLocationUE(), the location set before any movement tick).
//
// Golmok.Travel.Teleport: an unknown zone is refused; photo mode refuses a travel (skipped when Enter() is refused);
// z_synthetic_001_interior is redirected to its parent z_synthetic_001 and arrives at the manifest spawn (feet + capsule
// half height + clearance, UE Yaw from yaw_deg) with the pin released a tick later and OnTraveled fired once; a portal
// that is not Idle refuses; a second request while traveling is refused; z_synthetic_002 (spawned from the index when
// not discovered yet) arrives at its spawn with the camera already there (the spring arm socket within the arm's reach
// of the pawn at OnTraveled time, P14-2: no lag sweep from the previous zone); without a spawn GetSpawnUE falls back
// to the zone origin's XY with the zone's +x heading; with bSimulateLoadStall and a 0.3 s timeout the travel fails with
// "timeout", the pin released and no arrival counted.
// Golmok.Save.RoundTrip: on the test slot golmok_test_wp15a (automatic saves off) an empty slot restores nothing (rule
// 3); a synchronous save -> LoadSlot keeps lat / lon of the pawn exactly (1 mm after LonLatToLevelUE), the ENU yaw
// (= -UE Yaw), the visit and both photo entries; Restore puts the pawn back within 1 mm / 0.01 deg and drops the photo
// whose file is missing; a saved version 99 restores to the zone's spawn (rule 2); a zone that is gone restores
// nothing without HomeZoneId and to HomeZoneId's spawn with it (rule 2). Time of day (WP-14a, skipped with an Info line
// without an AGolmokTimeOfDay with keyframes): Clock mode at 13:07 is saved as {Minutes 787, Mode Clock} and restored
// instantly after changing both (minutes within 0.01, mode Clock); a saved Realtime restores the mode only (the clock is
// the PC's local time, not the saved minutes); a saved Fixed 16:40 restores time and mode; a save from before WP-14a
// (Minutes -1) falls back to ApplyPreset(PresetName). Then, with automatic saves on for that step only,
// golmok.save reset while standing in a zone (R49-1): direct and timer visit polls neither record that zone nor recreate
// the slot; after leaving it and coming back it is a first visit again and the slot is written. The slot and the test
// photo are deleted at the end.
// Character (R91-1; skipped with an Info line without an automatically applied roster character and a 'quinn' entry):
// the automatic pick is saved as an empty id with CharacterIdRule 1; after SelectCharacter(quinn) the slot holds quinn
// (rule 1). Restores of a slot without position / zone / home (rule 3, only the character step runs): a legacy (rule 0)
// roster default does not call SelectCharacter while the automatic pick differs (current id and explicit flag kept), the
// same id with rule 1 is applied as explicit, a legacy non-default id is restored as explicit, a rule 1 id that is only
// applied automatically becomes explicit, an empty rule 1 id changes nothing. A rule 1 id that SelectCharacter refuses
// (a test-only copy of quinn whose mesh does not exist) is kept by the next save with rule 1 until a new explicit pick;
// an id not in the roster is dropped; a later legacy-default restore, golmok.save reset, or an explicit pick (also
// once the selection is automatic again) leaves no trace of it. GolmokSaveCharacter::IsLegacyDefault is also checked on
// a literal roster before the map check (runs without the map or assets), including a DefaultId that no mode uses.
// Weather (WP-16a design section 12; skipped with an Info line without UGolmokWeatherSubsystem or with weather.json
// off): rain 0.60 fixed with wetness 0.42 / puddle 0.10 is saved as rule 1 with those five values and shown on the
// golmok.save status slot line; a weather change marks the save dirty, the restore's own change does not. Restores of a
// slot without position / zone / home (rule 3): rule 1 brings the five values back instantly; a rule 0 slot keeps the
// current weather ("weather - (not in save)"); an unknown state name restores as clear with "(unknown weather 'snow')";
// an intensity of 3 is clamped to 1 and a mode of 7 restores as fixed. With an AGolmokTimeOfDay with keyframes, a saved
// Schedule mode is applied after the saved time of day: the slot of the restored time (not of the time before the
// restore) becomes the target, by a transition from the saved weather, and marks the save dirty.
//
// Headless: .\tools\ue\test.ps1 -Filter Golmok.Travel   /   -Filter Golmok.Save

#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Characters/GolmokCharacterSubsystem.h"
#include "Components/CapsuleComponent.h"
#include "Editor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "Geo/GolmokGeo.h"
#include "Geo/GolmokGeoSubsystem.h"
#include "HAL/FileManager.h"
#include "Kismet/GameplayStatics.h"
#include "Lighting/GolmokClockMath.h"
#include "Lighting/GolmokTimeOfDay.h"
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
#include "Weather/GolmokWeatherSubsystem.h"
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
	const TCHAR* QuinnId = TEXT("quinn"); // a non-default roster entry (characters.json)
	const TCHAR* UnloadableId = TEXT("wp15a_unloadable"); // test-only roster entry: quinn with MissingMeshPath (SelectCharacter refuses it)
	const TCHAR* MissingMeshPath = TEXT("/Game/GolmokTests/Absent.Absent");
	const TCHAR* UnknownId = TEXT("wp15a_not_in_roster");
	constexpr double TravelWaitSeconds = 25.0; // TravelTimeoutSeconds (20) + margin
	constexpr double ToleranceCm = 0.1;        // 1 mm
	constexpr float TodClockMinutes = 787.f;   // 13:07, saved in Clock mode
	constexpr float TodFixedMinutes = 1000.f;  // 16:40, saved in Fixed mode
	constexpr float TodMinutesTolerance = 0.01f;
	constexpr float WeatherTolerance = 1e-4f; // WP-16a saved floats (rain intensity, wetness, puddle)

	/** "id 'quinn' rule 1": a slot's character as one string, so one TestEqual shows both fields (R91-1 follow-up). */
	FString SlotCharacter(const FString& Id, int32 Rule)
	{
		return FString::Printf(TEXT("id '%s' rule %d"), *Id, Rule);
	}

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
				CheckCameraSnapped(Pawn);
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
		/**
		 * P14-2: the arm end (the camera socket) is at the pawn right after the arrival. This runs on the first update
		 * that sees the travel finished, i.e. at OnTraveled time (FinishArrival, one tick after Arrive), so the arm has
		 * ticked at least once since the teleport. Without SnapCameraAfterTeleport the arm's lag reference stays at
		 * z_synthetic_001's spawn, 192 m away, and one lagged tick (CameraLagSpeed 12, ~1/60 s) moves it only ~20 % of
		 * the way: the socket would still be ~150 m behind. The bound is the arm's own reach plus where the arm sits on the
		 * pawn plus 50 cm. The lagged point is checked before collision (GetUnfixedCameraPosition): the CameraBoom probes
		 * (bDoCollisionTest), and a probe from the pawn back toward 001 that hits zone geometry would pull the socket in and
		 * hide a regression. The socket is checked too. One frame cannot hide a regression: with the default lag
		 * substepping the arm is still >= ~30 m behind even at the 0.4 s world delta cap. The runbook's 60 fps recording
		 * is the visual check.
		 */
		void CheckCameraSnapped(APawn* Pawn)
		{
			USpringArmComponent* Arm = Pawn ? Pawn->FindComponentByClass<USpringArmComponent>() : nullptr;
			if (!Arm)
			{
				Test->AddInfo(TEXT("camera snap not checked: the player pawn has no USpringArmComponent"));
				return;
			}
			const FVector PawnLocation = Pawn->GetActorLocation();
			const double Reach = Arm->TargetArmLength + Arm->SocketOffset.Size() + Arm->TargetOffset.Size()
								 + FVector::Dist(Arm->GetComponentLocation(), PawnLocation) + 50.0;
			const double Unfixed = FVector::Dist(Arm->GetUnfixedCameraPosition(), PawnLocation);
			const double Distance = FVector::Dist(Arm->GetSocketLocation(USpringArmComponent::SocketName), PawnLocation);
			Test->AddInfo(FString::Printf(TEXT("camera at arrival: unfixed %.1f cm, socket %.1f cm, reach %.1f cm"), Unfixed, Distance, Reach));
			Test->TestTrue(
				FString::Printf(TEXT("camera snapped at arrival: pre-collision arm end %.1f cm from the pawn <= %.1f cm"), Unfixed, Reach),
				Unfixed <= Reach);
			Test->TestTrue(
				FString::Printf(TEXT("camera snapped at arrival: arm socket %.1f cm from the pawn <= %.1f cm"), Distance, Reach),
				Distance <= Reach);
		}

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

				// WP-14a time of day: Clock mode at 13:07 (instant) is what the save below must keep.
				AGolmokTimeOfDay* Tod = AGolmokTimeOfDay::Find(World);
				bTodReady = Tod && Tod->EnsurePresets() && Tod->GetCycleTimes().Num() > 0;
				if (bTodReady)
				{
					Tod->SetClockMode(EGolmokClockMode::Clock);
					Tod->SetTimeOfDay(TodClockMinutes, /*bInstant*/ true);
				}
				else
				{
					Test->AddInfo(TEXT("time-of-day steps skipped: no AGolmokTimeOfDay with keyframes in the PIE world"));
				}

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
				// R91-1: every write records the rule; the automatic pick of this fresh PIE world is not saved (explicit: phase 3).
				Test->TestEqual(TEXT("CharacterIdRule 1 (explicit selections only)"), Slot->CharacterIdRule, 1);
				const UGolmokCharacterSubsystem* Characters = World->GetSubsystem<UGolmokCharacterSubsystem>();
				bCharacterReady = Characters && Characters->GetLoadError().IsEmpty() && !Characters->GetCurrentId().IsEmpty()
					&& Characters->GetCurrentId() != QuinnId && Characters->GetRoster().Find(QuinnId) != nullptr;
				if (bCharacterReady)
				{
					Test->TestFalse(FString::Printf(TEXT("character %s applied automatically (precondition)"), *Characters->GetCurrentId()),
						Characters->IsExplicitSelection());
					Test->TestTrue(FString::Printf(TEXT("automatic character %s not saved (CharacterId '%s')"), *Characters->GetCurrentId(), *Slot->CharacterId),
						Slot->CharacterId.IsEmpty());
					Test->TestTrue(TEXT("golmok.save status: character - (automatic)"), Save->DescribeStatus().Contains(TEXT("character - (automatic)")));
				}
				else
				{
					Test->AddInfo(TEXT("character steps skipped: no automatically applied WP-18 roster character other than quinn, or no quinn entry (mannequin: tools/ue/add-mannequin.ps1)"));
				}
				if (bTodReady)
				{
					Test->TestTrue(FString::Printf(TEXT("tod minutes %.3f saved (13:07)"), Slot->TimeOfDay.Minutes),
						FMath::IsNearlyEqual(Slot->TimeOfDay.Minutes, TodClockMinutes, TodMinutesTolerance));
					Test->TestEqual(TEXT("tod mode saved as Clock"), static_cast<int32>(Slot->TimeOfDay.Mode), static_cast<int32>(EGolmokClockMode::Clock));
					Test->TestEqual(TEXT("tod preset name kept (nearest keyframe)"), Slot->TimeOfDay.PresetName, Tod->CurrentPreset.ToString());
					// Change both before the restore: Fixed at 05:00.
					Tod->SetClockMode(EGolmokClockMode::Fixed);
					Tod->SetTimeOfDay(300.f, /*bInstant*/ true);
				}
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
				if (bTodReady)
				{
					// Restored in the same frame (no clock tick in between) and instantly.
					Test->TestEqual(TEXT("restore: tod mode Clock"), static_cast<int32>(Tod->GetClockMode()), static_cast<int32>(EGolmokClockMode::Clock));
					Test->TestTrue(FString::Printf(TEXT("restore: tod minutes %.3f = 13:07"), Tod->GetTimeOfDayMinutes()),
						FMath::IsNearlyEqual(Tod->GetTimeOfDayMinutes(), TodClockMinutes, TodMinutesTolerance));
					Test->TestFalse(TEXT("restore: tod jump is instant (no transition)"), Tod->IsTransitioning());
				}
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
				if (bTodReady)
				{
					// Realtime: only the mode is restored; the clock is the PC's local time, not the saved 01:40.
					Slot->TimeOfDay.Mode = static_cast<uint8>(EGolmokClockMode::Realtime);
					Slot->TimeOfDay.Minutes = 100.f;
				}
				UGameplayStatics::SaveGameToSlot(Slot, Save->SlotName, 0);
				FString Message;
				Test->TestTrue(TEXT("restore (rule 2, version 99) starts"), Save->Restore(Message));
				Test->AddInfo(Message);
				Test->TestTrue(TEXT("rule 2: saved zone spawn"), Save->GetLastRestoreDecision() == GolmokTravelMath::ERestore::SavedZoneSpawn);
				if (AGolmokTimeOfDay* Tod = bTodReady ? AGolmokTimeOfDay::Find(World) : nullptr)
				{
					Test->TestEqual(TEXT("restore: tod mode Realtime"), static_cast<int32>(Tod->GetClockMode()), static_cast<int32>(EGolmokClockMode::Realtime));
					const double FromLocal = GolmokClockMath::CircularDistance(Tod->GetTimeOfDayMinutes(), Tod->RealtimeTargetMinutes());
					Test->TestTrue(FString::Printf(TEXT("restore: realtime clock %.3f is the local time (%.3f min off), saved minutes ignored"),
									   Tod->GetTimeOfDayMinutes(), FromLocal),
						FromLocal < GolmokClockMath::ResyncMinutes);
				}
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
				AGolmokTimeOfDay* Tod = bTodReady ? AGolmokTimeOfDay::Find(World) : nullptr;
				if (Tod)
				{
					// Fixed 16:40 (the time of day is applied even when no position is restored).
					Slot->TimeOfDay.Mode = static_cast<uint8>(EGolmokClockMode::Fixed);
					Slot->TimeOfDay.Minutes = TodFixedMinutes;
				}
				UGameplayStatics::SaveGameToSlot(Slot, Save->SlotName, 0);
				FString Message;
				Save->HomeZoneId.Reset();
				Test->TestFalse(TEXT("zone gone, no HomeZoneId: nothing restored"), Save->Restore(Message));
				Test->TestTrue(TEXT("rule 3"), Save->GetLastRestoreDecision() == GolmokTravelMath::ERestore::None);
				FName LegacyPreset;
				if (Tod)
				{
					Test->TestEqual(TEXT("restore: tod mode Fixed"), static_cast<int32>(Tod->GetClockMode()), static_cast<int32>(EGolmokClockMode::Fixed));
					Test->TestTrue(FString::Printf(TEXT("restore: tod minutes %.3f = 16:40"), Tod->GetTimeOfDayMinutes()),
						FMath::IsNearlyEqual(Tod->GetTimeOfDayMinutes(), TodFixedMinutes, TodMinutesTolerance));
					// A save from before WP-14a: default {Minutes -1, Mode 0} + a cycle preset other than the current one.
					for (const FName& Name : Tod->GetCycle())
					{
						if (Name != Tod->CurrentPreset)
						{
							LegacyPreset = Name;
							break;
						}
					}
					Slot->TimeOfDay = FGolmokSaveTimeOfDay();
					Slot->TimeOfDay.PresetName = LegacyPreset.ToString();
					UGameplayStatics::SaveGameToSlot(Slot, Save->SlotName, 0);
				}
				Save->HomeZoneId = SecondZoneId;
				Test->TestTrue(TEXT("zone gone, HomeZoneId set: restore starts"), Save->Restore(Message));
				Test->AddInfo(Message);
				Test->TestTrue(TEXT("rule 2: home zone spawn"), Save->GetLastRestoreDecision() == GolmokTravelMath::ERestore::HomeZoneSpawn);
				if (Tod && !LegacyPreset.IsNone())
				{
					Test->TestEqual(TEXT("legacy save (Minutes -1): preset applied by name"), Tod->CurrentPreset.ToString(), LegacyPreset.ToString());
					Test->TestEqual(TEXT("legacy save: mode stays Fixed"), static_cast<int32>(Tod->GetClockMode()), static_cast<int32>(EGolmokClockMode::Fixed));
				}
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
				CheckCharacterRule(World, Save, Pawn);
				CheckWeatherRule(World, Save);
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
		/**
		 * R91-1, synchronous (no tick, no GC: the roster override is restored before returning). The restores use a slot
		 * without position / zone and no HomeZoneId (rule 3: no travel), so only Restore's character step acts.
		 */
		void CheckCharacterRule(UWorld* World, UGolmokSaveSubsystem* Save, APawn* Pawn)
		{
			UGolmokCharacterSubsystem* Characters = World->GetSubsystem<UGolmokCharacterSubsystem>();
			if (!bCharacterReady || !Characters || !Pawn)
			{
				return; // phase 0 said why
			}
			FString Message;
			if (!Test->TestTrue(TEXT("character: SelectCharacter(quinn)"), Characters->SelectCharacter(QuinnId, Message)))
			{
				Test->AddError(Message);
				return;
			}
			Test->TestTrue(TEXT("character: quinn is an explicit selection"), Characters->IsExplicitSelection());
			Test->TestTrue(TEXT("character: SaveNow(sync)"), Save->SaveNow(/*bSync*/ true, TEXT("test character"), &Message));
			UGolmokSaveGame* Slot = Save->LoadSlot();
			if (!Test->TestNotNull(TEXT("character: LoadSlot"), Slot))
			{
				return;
			}
			Test->TestEqual(TEXT("explicit selection saved: CharacterId quinn"), Slot->CharacterId, FString(QuinnId));
			Test->TestEqual(TEXT("explicit selection saved: CharacterIdRule 1"), Slot->CharacterIdRule, 1);

			TGuardValue<FString> NoHome(Save->HomeZoneId, FString());
			Slot->bHasPosition = false;
			Slot->ZoneId.Reset();
			Slot->ZoneVersion = 0;
			Slot->TimeOfDay = FGolmokSaveTimeOfDay();
			const FString DefaultId = Characters->GetRoster().DefaultId;
			{
				// The automatic pick differs from the roster default, as manny_gasp does on a GASP pawn: every mode default -> quinn.
				FGolmokCharacterRoster& Roster = Characters->MutableRosterForTest();
				TGuardValue<TMap<FString, FString>> ModeGuard(Roster.DefaultByAnimMode, Roster.DefaultByAnimMode);
				for (TPair<FString, FString>& Mode : Roster.DefaultByAnimMode)
				{
					Mode.Value = QuinnId;
				}
				Characters->ApplyDefaultForTest(Pawn);
				Test->TestEqual(TEXT("character: automatic mode default quinn (precondition)"), Characters->GetCurrentId(), FString(QuinnId));
				Test->TestFalse(TEXT("character: quinn is automatic (precondition)"), Characters->IsExplicitSelection());

				Slot->CharacterIdRule = 0; // a save from before the rule, holding the roster default
				Slot->CharacterId = DefaultId;
				UGameplayStatics::SaveGameToSlot(Slot, Save->SlotName, 0);
				Test->TestTrue(TEXT("golmok.save status marks the legacy character"),
					Save->DescribeStatus().Contains(FString::Printf(TEXT("character %s (legacy)"), *DefaultId)));
				Save->Restore(Message);
				Test->AddInfo(Message);
				Test->TestEqual(FString::Printf(TEXT("legacy default %s: no SelectCharacter, automatic quinn kept"), *DefaultId), Characters->GetCurrentId(),
					FString(QuinnId));
				Test->TestFalse(FString::Printf(TEXT("legacy default %s: selection stays automatic"), *DefaultId), Characters->IsExplicitSelection());
				Test->TestTrue(FString::Printf(TEXT("legacy default named in the restore message (%s)"), *Message), Message.Contains(TEXT("(legacy default, not pinned)")));

				Slot->CharacterIdRule = 1; // the same id chosen explicitly
				UGameplayStatics::SaveGameToSlot(Slot, Save->SlotName, 0);
				Save->Restore(Message);
				Test->TestEqual(FString::Printf(TEXT("rule 1 %s: restored"), *DefaultId), Characters->GetCurrentId(), DefaultId);
				Test->TestTrue(FString::Printf(TEXT("rule 1 %s: explicit"), *DefaultId), Characters->IsExplicitSelection());
			}

			Characters->ApplyDefaultForTest(Pawn); // the real roster again
			const FString AutoId = Characters->GetCurrentId();
			Test->TestFalse(FString::Printf(TEXT("character: %s automatic again (precondition)"), *AutoId), Characters->IsExplicitSelection());
			Slot->CharacterIdRule = 0; // a legacy non-default id: chosen, so restored as explicit
			Slot->CharacterId = QuinnId;
			UGameplayStatics::SaveGameToSlot(Slot, Save->SlotName, 0);
			Save->Restore(Message);
			Test->AddInfo(Message);
			Test->TestEqual(TEXT("legacy non-default quinn: restored"), Characters->GetCurrentId(), FString(QuinnId));
			Test->TestTrue(TEXT("legacy non-default quinn: explicit"), Characters->IsExplicitSelection());

			Characters->ApplyDefaultForTest(Pawn);
			Slot->CharacterIdRule = 1; // an explicit id that this run has only applied automatically
			Slot->CharacterId = AutoId;
			UGameplayStatics::SaveGameToSlot(Slot, Save->SlotName, 0);
			Save->Restore(Message);
			Test->TestEqual(FString::Printf(TEXT("rule 1 %s (same as the automatic pick): kept"), *AutoId), Characters->GetCurrentId(), AutoId);
			Test->TestTrue(FString::Printf(TEXT("rule 1 %s (same as the automatic pick): now explicit"), *AutoId), Characters->IsExplicitSelection());

			Characters->ApplyDefaultForTest(Pawn);
			Slot->CharacterId.Reset(); // rule 1, automatic at save time
			UGameplayStatics::SaveGameToSlot(Slot, Save->SlotName, 0);
			Save->Restore(Message);
			Test->TestEqual(TEXT("rule 1 empty id: current character unchanged"), Characters->GetCurrentId(), AutoId);
			Test->TestFalse(TEXT("rule 1 empty id: still automatic"), Characters->IsExplicitSelection());
			Test->TestFalse(FString::Printf(TEXT("rule 1 empty id: no character step (%s)"), *Message), Message.Contains(TEXT(", character")));

			// R91-1 follow-up V1: an explicit id this world refuses stays in the slot until a new explicit pick (a failed
			// restore never loses the save). The refused entry is quinn with a mesh that does not exist: ApplyEntry refuses
			// it before touching the pawn ("mesh/animation missing ..."). The roster entries are put back on return.
			FGolmokCharacterRoster& Roster = Characters->MutableRosterForTest();
			const FGolmokCharacterEntry* Quinn = Roster.Find(QuinnId);
			if (!Test->TestNotNull(TEXT("character: quinn entry"), Quinn))
			{
				return;
			}
			FGolmokCharacterEntry Unloadable = *Quinn; // copied before the array grows
			Unloadable.Id = UnloadableId;
			Unloadable.MeshPath = MissingMeshPath;
			TGuardValue<TArray<FGolmokCharacterEntry>> EntriesGuard(Roster.Entries, Roster.Entries);
			Roster.Entries.Add(MoveTemp(Unloadable));
			const auto RestoreSlot = [&](const FString& Id, int32 Rule)
			{
				Slot->CharacterIdRule = Rule;
				Slot->CharacterId = Id;
				UGameplayStatics::SaveGameToSlot(Slot, Save->SlotName, 0);
				Save->Restore(Message);
				Test->AddInfo(Message);
			};
			// The character the next save writes (the snapshot of this pawn, then the slot read back).
			const auto SaveAndRead = [&](const TCHAR* Why) -> FString
			{
				FString SaveMessage;
				if (!Save->SaveNow(/*bSync*/ true, Why, &SaveMessage))
				{
					return FString::Printf(TEXT("save failed: %s"), *SaveMessage);
				}
				const UGolmokSaveGame* Written = Save->LoadSlot();
				return Written ? SlotCharacter(Written->CharacterId, Written->CharacterIdRule) : FString(TEXT("no slot"));
			};
			const FString AutomaticInSlot = SlotCharacter(FString(), 1);

			RestoreSlot(UnloadableId, 1);
			Test->TestTrue(FString::Printf(TEXT("%s: refused, %s still current and automatic (precondition)"), UnloadableId, *AutoId),
				Characters->GetCurrentId() == AutoId && !Characters->IsExplicitSelection());
			Test->TestTrue(FString::Printf(TEXT("%s: restore message says kept (%s)"), UnloadableId, *Message),
				Message.Contains(TEXT("(not applied, kept for the next save)")));
			Test->TestEqual(TEXT("refused explicit id: the next save keeps it with rule 1"), SaveAndRead(TEXT("test refused character")),
				SlotCharacter(UnloadableId, 1));

			RestoreSlot(UnknownId, 1);
			Test->TestEqual(TEXT("id not in the roster: dropped by the next save"), SaveAndRead(TEXT("test unknown character")), AutomaticInSlot);

			RestoreSlot(UnloadableId, 1); // pending again, then a restore that pins nothing
			RestoreSlot(DefaultId, 0);
			Test->TestTrue(FString::Printf(TEXT("legacy default after a refusal: not pinned (precondition: %s)"), *Message),
				Message.Contains(TEXT("(legacy default, not pinned)")));
			Test->TestEqual(TEXT("legacy default after a refusal: the refused id is not saved"), SaveAndRead(TEXT("test legacy after refusal")), AutomaticInSlot);

			RestoreSlot(UnloadableId, 1); // pending again, then golmok.save reset
			Save->ResetSlot(Message);
			Test->TestEqual(TEXT("golmok.save reset after a refusal: the refused id is not saved"), SaveAndRead(TEXT("test reset after refusal")), AutomaticInSlot);

			RestoreSlot(UnloadableId, 1); // pending again, then a new explicit pick
			if (!Test->TestTrue(TEXT("refused, then SelectCharacter(quinn)"), Characters->SelectCharacter(QuinnId, Message)))
			{
				Test->AddError(Message);
				return;
			}
			Test->TestEqual(TEXT("a new explicit pick replaces the refused id"), SaveAndRead(TEXT("test pick after refusal")), SlotCharacter(QuinnId, 1));
			Characters->ApplyDefaultForTest(Pawn);
			Test->TestEqual(TEXT("automatic again after that pick: the refused id does not come back"), SaveAndRead(TEXT("test automatic after pick")),
				AutomaticInSlot);
		}

		/** "rain 0.60 wet 0.42 puddle 0.10 fixed": the weather now as one string, so one TestEqual shows every field. */
		static FString LiveWeather(const UGolmokWeatherSubsystem& Weather)
		{
			return FString::Printf(TEXT("%s %.2f wet %.2f puddle %.2f %s"), UGolmokWeatherSubsystem::WeatherName(Weather.GetTargetWeather()),
				Weather.GetTargetIntensity(), Weather.GetWetness(), Weather.GetPuddleAmount(), UGolmokWeatherSubsystem::ModeName(Weather.GetMode()));
		}

		/**
		 * WP-16a design section 12, synchronous (no weather tick in between). The restores use a slot without position / zone,
		 * time of day and character and no HomeZoneId (rule 3: no travel), so only Restore's weather step acts, except the
		 * Schedule step, which also restores a time of day.
		 */
		void CheckWeatherRule(UWorld* World, UGolmokSaveSubsystem* Save)
		{
			UGolmokWeatherSubsystem* Weather = UGolmokWeatherSubsystem::Get(World);
			if (!Weather || !Weather->IsEnabled())
			{
				const FString Why = Weather ? FString::Printf(TEXT("weather off - %s"), *Weather->GetConfigError()) : FString(TEXT("no UGolmokWeatherSubsystem in the PIE world"));
				Test->AddInfo(FString::Printf(TEXT("weather steps skipped: %s"), *Why));
				return;
			}
			FString Message;
			const bool bSetUp = Weather->SetMode(EGolmokWeatherMode::Fixed, Message) && Weather->SetWeather(EGolmokWeather::Rain, 0.6f, /*bInstant*/ true, Message)
				&& Weather->SetSurface(0.42f, 0.10f, Message);
			if (!Test->TestTrue(TEXT("weather: rain 0.60 fixed, wet 0.42 puddle 0.10 (setup)"), bSetUp))
			{
				Test->AddError(Message);
				return;
			}
			Test->TestTrue(TEXT("weather: SaveNow(sync)"), Save->SaveNow(/*bSync*/ true, TEXT("test weather"), &Message));
			UGolmokSaveGame* Slot = Save->LoadSlot();
			if (!Test->TestNotNull(TEXT("weather: LoadSlot"), Slot))
			{
				return;
			}
			Test->TestEqual(TEXT("weather saved: rule 1"), Slot->Weather.Rule, UGolmokSaveGame::WeatherRuleV1);
			Test->TestEqual(TEXT("weather saved: state rain"), Slot->Weather.State, FString(TEXT("rain")));
			Test->TestTrue(FString::Printf(TEXT("weather saved: intensity %.4f = 0.60"), Slot->Weather.Intensity), FMath::IsNearlyEqual(Slot->Weather.Intensity, 0.6f, WeatherTolerance));
			Test->TestEqual(TEXT("weather saved: mode fixed (0)"), static_cast<int32>(Slot->Weather.Mode), 0);
			Test->TestTrue(FString::Printf(TEXT("weather saved: wetness %.4f = 0.42"), Slot->Weather.Wetness), FMath::IsNearlyEqual(Slot->Weather.Wetness, 0.42f, WeatherTolerance));
			Test->TestTrue(FString::Printf(TEXT("weather saved: puddle %.4f = 0.10"), Slot->Weather.Puddle), FMath::IsNearlyEqual(Slot->Weather.Puddle, 0.10f, WeatherTolerance));
			Test->TestTrue(TEXT("golmok.save status: slot line carries the weather"),
				Save->DescribeStatus().Contains(TEXT("weather rain 0.60 wet 0.42 puddle 0.10 fixed")));
			Test->TestTrue(TEXT("weather: a fresh save is not dirty (precondition)"), Save->DescribeStatus().Contains(TEXT("dirty no")));

			// The live weather changes (OnWeatherChanged marks the save dirty); the restore brings the five values back instantly.
			Weather->SetWeather(EGolmokWeather::Clear, 0.f, /*bInstant*/ true, Message);
			Weather->SetSurface(0.f, 0.f, Message);
			Test->TestTrue(TEXT("weather: a weather change marks the save dirty"), Save->DescribeStatus().Contains(TEXT("dirty yes")));
			TGuardValue<FString> NoHome(Save->HomeZoneId, FString());
			Slot->bHasPosition = false;
			Slot->ZoneId.Reset();
			Slot->ZoneVersion = 0;
			Slot->TimeOfDay = FGolmokSaveTimeOfDay();
			Slot->CharacterId.Reset();
			Slot->CharacterIdRule = UGolmokSaveGame::CharacterIdRuleExplicit;
			// SaveNow first clears the dirty flag (it writes the live state), then the edited slot replaces that write.
			auto RestoreSlot = [this, Save, Slot](const TCHAR* What) -> FString
			{
				Save->SaveNow(/*bSync*/ true, TEXT("test weather baseline"));
				UGameplayStatics::SaveGameToSlot(Slot, Save->SlotName, 0);
				FString RestoreMessage;
				Save->Restore(RestoreMessage);
				Test->AddInfo(FString::Printf(TEXT("%s: %s"), What, *RestoreMessage));
				return RestoreMessage;
			};
			FString Restored = RestoreSlot(TEXT("weather rule 1"));
			Test->TestTrue(TEXT("weather rule 1: restore message"), Restored.Contains(TEXT(", weather rain 0.60 wet 0.42 puddle 0.10 fixed")));
			Test->TestEqual(TEXT("weather rule 1: five values restored"), LiveWeather(*Weather), FString(TEXT("rain 0.60 wet 0.42 puddle 0.10 fixed")));
			Test->TestFalse(TEXT("weather rule 1: instant (no transition)"), Weather->IsTransitioning());
			Test->TestTrue(FString::Printf(TEXT("weather rule 1: rain now %.3f = 0.60 (instant)"), Weather->GetRainIntensity()),
				FMath::IsNearlyEqual(Weather->GetRainIntensity(), 0.6f, WeatherTolerance));
			Test->TestTrue(TEXT("weather rule 1: the restore's own change is not dirty"), Save->DescribeStatus().Contains(TEXT("dirty no")));

			// Rule 0 (a save from before WP-16a): the current weather stays.
			Weather->SetWeather(EGolmokWeather::Overcast, 0.f, /*bInstant*/ true, Message);
			const FGolmokSaveWeather Saved = Slot->Weather;
			Slot->Weather = FGolmokSaveWeather();
			Restored = RestoreSlot(TEXT("weather rule 0"));
			Test->TestTrue(TEXT("weather rule 0: message 'weather - (not in save)'"), Restored.Contains(TEXT(", weather - (not in save)")));
			Test->TestEqual(TEXT("weather rule 0: current weather kept (overcast)"), static_cast<int32>(Weather->GetTargetWeather()), static_cast<int32>(EGolmokWeather::Overcast));
			Test->TestTrue(TEXT("golmok.save status: rule 0 slot line 'weather - (not in save)'"), Save->DescribeStatus().Contains(TEXT("weather - (not in save)")));

			// An unknown state name restores as clear (surface and mode still applied).
			Weather->SetWeather(EGolmokWeather::Rain, 1.f, /*bInstant*/ true, Message);
			Slot->Weather = Saved;
			Slot->Weather.State = TEXT("snow");
			Slot->Weather.Wetness = 0.2f;
			Slot->Weather.Puddle = 0.05f;
			Restored = RestoreSlot(TEXT("weather unknown state"));
			Test->TestTrue(TEXT("weather unknown state: message"), Restored.Contains(TEXT("(unknown weather 'snow')")));
			Test->TestEqual(TEXT("weather unknown state: clear"), LiveWeather(*Weather), FString(TEXT("clear 0.00 wet 0.20 puddle 0.05 fixed")));

			// Out-of-range values of a damaged save: intensity clamped into [0.05, 1], an unknown mode is fixed.
			Slot->Weather = Saved;
			Slot->Weather.Intensity = 3.f;
			Slot->Weather.Mode = 7;
			Restored = RestoreSlot(TEXT("weather clamp"));
			Test->TestEqual(TEXT("weather clamp: intensity 3 -> 1, mode 7 -> fixed"), LiveWeather(*Weather), FString(TEXT("rain 1.00 wet 0.42 puddle 0.10 fixed")));

			CheckWeatherSchedule(World, Save, *Weather, *Slot, RestoreSlot);
			Weather->SetMode(EGolmokWeatherMode::Fixed, Message);
			Weather->SetWeather(EGolmokWeather::Clear, 0.f, /*bInstant*/ true, Message);
			Weather->SetSurface(0.f, 0.f, Message);
		}

		/**
		 * A saved Schedule mode is applied after the saved time of day (design section 12): two schedule slots with different
		 * states, the clock set to the first before the restore and saved at the second; the restored target must be the
		 * second's (a weather restore before the time of day would pick the first), reached by a transition from the saved
		 * weather (a state other than that slot's), and that change marks the save dirty.
		 */
		template <typename FRestoreSlot>
		void CheckWeatherSchedule(UWorld* World, UGolmokSaveSubsystem* Save, UGolmokWeatherSubsystem& Weather, UGolmokSaveGame& Slot, FRestoreSlot& RestoreSlot)
		{
			AGolmokTimeOfDay* Tod = bTodReady ? AGolmokTimeOfDay::Find(World) : nullptr;
			const TArray<GolmokWeather::FScheduleSlot>& Schedule = Weather.GetConfig().Schedule;
			int32 Before = INDEX_NONE;
			int32 After = INDEX_NONE;
			for (int32 i = 0; i + 1 < Schedule.Num() && After == INDEX_NONE; ++i)
			{
				if (Schedule[i].State != Schedule[i + 1].State)
				{
					Before = i;
					After = i + 1;
				}
			}
			if (!Tod || After == INDEX_NONE)
			{
				Test->AddInfo(TEXT("weather schedule step skipped: no AGolmokTimeOfDay with keyframes, or no two schedule slots with different states"));
				return;
			}
			const EGolmokWeather AfterState = static_cast<EGolmokWeather>(static_cast<uint8>(Schedule[After].State));
			// The saved target differs from the slot of the saved time: clear unless that slot is clear, then overcast.
			const EGolmokWeather SavedState = AfterState == EGolmokWeather::Clear ? EGolmokWeather::Overcast : EGolmokWeather::Clear;
			const float SavedMinutes = static_cast<float>(Schedule[After].Minutes) + 1.f;
			Tod->SetClockMode(EGolmokClockMode::Fixed);
			Tod->SetTimeOfDay(static_cast<float>(Schedule[Before].Minutes) + 1.f, /*bInstant*/ true);
			Slot.TimeOfDay = FGolmokSaveTimeOfDay();
			Slot.TimeOfDay.Minutes = SavedMinutes;
			Slot.TimeOfDay.Mode = static_cast<uint8>(EGolmokClockMode::Fixed);
			Slot.Weather.Rule = UGolmokSaveGame::WeatherRuleV1;
			Slot.Weather.State = UGolmokWeatherSubsystem::WeatherName(SavedState);
			Slot.Weather.Intensity = 0.f;
			Slot.Weather.Mode = static_cast<uint8>(EGolmokWeatherMode::Schedule);
			const FString Restored = RestoreSlot(TEXT("weather schedule"));
			Test->TestTrue(FString::Printf(TEXT("weather schedule: tod restored first (%.3f min)"), Tod->GetTimeOfDayMinutes()),
				FMath::IsNearlyEqual(Tod->GetTimeOfDayMinutes(), SavedMinutes, TodMinutesTolerance));
			Test->TestEqual(TEXT("weather schedule: mode schedule"), static_cast<int32>(Weather.GetMode()), static_cast<int32>(EGolmokWeatherMode::Schedule));
			Test->TestEqual(TEXT("weather schedule: slot of the restored time"), Weather.GetScheduleIndexNow(), After);
			Test->TestEqual(TEXT("weather schedule: target = that slot's state"), static_cast<int32>(Weather.GetTargetWeather()), static_cast<int32>(AfterState));
			Test->TestTrue(FString::Printf(TEXT("weather schedule: target intensity %.3f = the slot's"), Weather.GetTargetIntensity()),
				FMath::IsNearlyEqual(Weather.GetTargetIntensity(), static_cast<float>(Schedule[After].Intensity), WeatherTolerance));
			if (Weather.GetConfig().TransitionSeconds > 0.0)
			{
				Test->TestTrue(TEXT("weather schedule: a transition from the saved weather"), Weather.IsTransitioning());
			}
			Test->TestTrue(TEXT("weather schedule: restore message names the schedule mode"), Restored.Contains(TEXT(" schedule")));
			Test->TestTrue(TEXT("weather schedule: the slot change is dirty"), Save->DescribeStatus().Contains(TEXT("dirty yes")));
		}

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
		bool bTodReady = false; // an AGolmokTimeOfDay with keyframes: the WP-14a time-of-day steps run
		bool bCharacterReady = false; // an automatic roster pick other than quinn and a quinn entry: the R91-1 character steps run
	};

	/** R91-1 pure rule on a literal roster (the characters.json defaults): no map, pawn or roster assets needed. */
	void CheckLegacyDefaultRule(FAutomationTestBase* Test)
	{
		FGolmokCharacterRoster Roster;
		Roster.DefaultId = TEXT("manny");
		Roster.DefaultByAnimMode.Add(TEXT("abp"), TEXT("manny"));
		Roster.DefaultByAnimMode.Add(TEXT("gasp"), TEXT("manny_gasp"));
		Test->TestTrue(TEXT("rule 0: roster default manny is a legacy default (not pinned)"), GolmokSaveCharacter::IsLegacyDefault(0, TEXT("manny"), Roster));
		Test->TestTrue(TEXT("rule 0: GASP mode default manny_gasp is a legacy default (not pinned)"),
			GolmokSaveCharacter::IsLegacyDefault(0, TEXT("manny_gasp"), Roster));
		Test->TestFalse(TEXT("rule 0: non-default quinn is restored"), GolmokSaveCharacter::IsLegacyDefault(0, QuinnId, Roster));
		Test->TestFalse(TEXT("rule 1: an explicit manny is restored"), GolmokSaveCharacter::IsLegacyDefault(1, TEXT("manny"), Roster));
		Test->TestFalse(TEXT("rule 0: an empty id is no legacy default"), GolmokSaveCharacter::IsLegacyDefault(0, FString(), Roster));
		Roster.DefaultByAnimMode[TEXT("abp")] = QuinnId; // manny is now `default` only, no mode's value
		Test->TestTrue(TEXT("rule 0: DefaultId alone is a legacy default"), GolmokSaveCharacter::IsLegacyDefault(0, TEXT("manny"), Roster));
	}

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
	CheckLegacyDefaultRule(this);
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
