// WP-18 / V-11: resize the real player across the synthetic portal's overlap/streaming lifecycle.
// Uses capsule teleports with movement disabled; visual animation and walking collision remain GUI checks.
#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
#include "Characters/GolmokCharacterSubsystem.h"
#include "Components/CapsuleComponent.h"
#include "Editor.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Misc/PackageName.h"
#include "Player/GolmokCharacter.h"
#include "Portals/GolmokPortal.h"
#include "Tests/AutomationEditorCommon.h"
#include "Zones/GolmokZone.h"
#include "Zones/GolmokZoneSubsystem.h"

namespace GolmokCharacterRosterPortalTest
{
	const TCHAR* Map = TEXT("/Game/Golmok/Maps/L_ZoneTest");
	const TCHAR* InteriorMap = TEXT("/Game/Golmok/Zones/z_synthetic_001_interior/v1/L_z_synthetic_001_interior");
	const TCHAR* ExteriorId = TEXT("z_synthetic_001");
	const TCHAR* InteriorId = TEXT("z_synthetic_001_interior");

	class FScenario : public IAutomationLatentCommand
	{
	public:
		explicit FScenario(FAutomationTestBase* InTest) : Test(InTest), CreatedAt(FPlatformTime::Seconds()) {}

		virtual bool Update() override
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			const double WallTime = FPlatformTime::Seconds();
			if (WallTime - CreatedAt > 90.0)
			{
				Test->AddError(FString::Printf(TEXT("roster portal scenario timed out (phase %d, cycle %d)"), Phase, Cycle));
				return true;
			}
			if (!World)
			{
				return false;
			}
			Now = World->GetTimeSeconds();
			if (PhaseStart < 0.0)
			{
				PhaseStart = Now;
			}
			const double Elapsed = Now - PhaseStart;
			UGolmokCharacterSubsystem* Roster = World->GetSubsystem<UGolmokCharacterSubsystem>();
			UGolmokZoneSubsystem* Zones = World->GetSubsystem<UGolmokZoneSubsystem>();
			AGolmokTimeOfDay* Lighting = AGolmokTimeOfDay::Find(World);
			APlayerController* Controller = World->GetFirstPlayerController();
			AGolmokCharacter* Character = Controller ? Cast<AGolmokCharacter>(Controller->GetPawn()) : nullptr;
			if (!Roster || !Zones || !Lighting || !Character)
			{
				return WaitOrFail(Elapsed, TEXT("player, roster, zones or lighting missing"));
			}
			if (Phase == 0)
			{
				if (Elapsed < 0.5)
				{
					return false;
				}
				OriginalCharacter = Character;
				OriginalController = Controller;
				Character->GetCharacterMovement()->DisableMovement();
				FString Message;
				if (!Test->TestTrue(TEXT("load exterior for roster portal test"), Zones->RequestLoad(ExteriorId, true, Message)))
				{
					Test->AddError(Message);
					return true;
				}
				return Next(1);
			}
			AGolmokPortal* Portal = AGolmokPortal::FindPortal(World, TEXT("door_1"));
			if (!Portal)
			{
				return WaitOrFail(Elapsed, TEXT("door_1 missing"));
			}
			AGolmokZone* Interior = Zones->FindZone(InteriorId);
			const bool bReady = Portal->State == EGolmokPortalState::Active && Portal->IsSublevelVisible()
				&& Interior && Interior->IsLoaded();
			switch (Phase)
			{
			case 1:
				Move(Character, Portal, -300.0);
				if (!Select(Roster, Character, Portal, TEXT("proxy135"))) { return true; }
				Move(Character, Portal, -80.0);
				return Next(2);
			case 2:
				if (!bReady || !Portal->bPlayerOverlapping)
				{
					return WaitOrFail(Elapsed, TEXT("approach did not preload the interior"));
				}
				Test->TestFalse(TEXT("approach stays outside"), Portal->bPlayerInside);
				Test->TestFalse(TEXT("approach keeps exterior lighting"), Lighting->IsInterior());
				if (!Select(Roster, Character, Portal, TEXT("manny"))) { return true; }
				return Next(3);
			case 3:
				if (Elapsed < 0.4) { return false; }
				Test->TestTrue(TEXT("resize outside keeps interior preloaded"), bReady);
				Test->TestTrue(TEXT("resize outside retains trigger overlap"), Portal->bPlayerOverlapping);
				Test->TestFalse(TEXT("resize alone does not cross the door"), Portal->bPlayerInside);
				Test->TestFalse(TEXT("resize alone does not change lighting"), Lighting->IsInterior());
				Move(Character, Portal, 80.0);
				return Next(4);
			case 4:
				if (!bReady || !Portal->bPlayerInside || !Lighting->IsInterior())
				{
					return WaitOrFail(Elapsed, TEXT("inward crossing did not enter the interior"));
				}
				if (!Select(Roster, Character, Portal, TEXT("proxy110"))) { return true; }
				return Next(5);
			case 5:
				if (Elapsed < 0.4) { return false; }
				Test->TestTrue(TEXT("shrink inside retains streamed interior"), bReady);
				Test->TestTrue(TEXT("shrink inside retains plane side"), Portal->bPlayerInside);
				Test->TestTrue(TEXT("shrink inside retains lighting"), Lighting->IsInterior());
				Move(Character, Portal, 300.0);
				return Next(6);
			case 6:
				if (Portal->bPlayerOverlapping)
				{
					return WaitOrFail(Elapsed, TEXT("player did not leave the trigger inward"));
				}
				Test->TestTrue(TEXT("room retains interior while away from trigger"), bReady && Portal->bPlayerInside);
				{
					// The fixture's 50 cm marker cube hangs 125..175 cm above the floor, 350 cm
					// from this door. proxy110 fits below it; Quinn at distance 300 must be refused.
					const FVector Before = Character->GetActorLocation();
					FString Message;
					Test->TestFalse(TEXT("room marker blocks expansion"), Roster->SelectCharacter(TEXT("quinn"), Message));
					Test->TestTrue(TEXT("blocked expansion explains collision"), Message.Contains(TEXT("blocked")));
					Test->TestEqual(TEXT("blocked room expansion retains id"), Roster->GetCurrentId(), FString(TEXT("proxy110")));
					Test->TestTrue(TEXT("blocked room expansion retains position"), Character->GetActorLocation().Equals(Before, 0.01));
					Test->TestTrue(TEXT("blocked room expansion retains interior side"), Portal->bPlayerInside);
					Test->TestTrue(TEXT("blocked room expansion retains lighting"), Lighting->IsInterior());
				}
				// Keep the same depth but stand beside the room's marker for the successful case.
				Move(Character, Portal, 300.0, 150.0);
				if (!Select(Roster, Character, Portal, TEXT("quinn"))) { return true; }
				return Next(7);
			case 7:
				// Stay inside longer than the unload delay to detect a resize-induced release.
				if (Elapsed < static_cast<double>(Portal->UnloadDelaySeconds) + 0.2) { return false; }
				Test->TestTrue(TEXT("room resize keeps interior beyond unload delay"), bReady && Portal->bPlayerInside);
				Test->TestTrue(TEXT("room resize keeps interior lighting"), Lighting->IsInterior());
				Move(Character, Portal, 80.0);
				return Next(8);
			case 8:
				if (Elapsed < 0.4) { return false; }
				if (!Portal->bPlayerOverlapping)
				{
					return WaitOrFail(Elapsed, TEXT("return did not reenter the trigger"));
				}
				Move(Character, Portal, -80.0);
				return Next(9);
			case 9:
				if (Portal->bPlayerInside || Lighting->IsInterior())
				{
					return WaitOrFail(Elapsed, TEXT("outward crossing did not release lighting"));
				}
				if (!Select(Roster, Character, Portal, TEXT("proxy135"))) { return true; }
				Move(Character, Portal, -300.0);
				return Next(10);
			case 10:
				if (Portal->State != EGolmokPortalState::Idle || Portal->IsSublevelLoaded() || (Interior && Interior->IsLoaded()))
				{
					return WaitOrFail(Elapsed, TEXT("outward exit did not unload interior"), Portal->UnloadDelaySeconds + 2.0);
				}
				Test->TestFalse(TEXT("finished cycle outside trigger"), Portal->bPlayerOverlapping);
				Test->TestFalse(TEXT("finished cycle outside interior"), Portal->bPlayerInside);
				Test->TestFalse(TEXT("finished cycle exterior lighting"), Lighting->IsInterior());
				Test->AddInfo(FString::Printf(TEXT("roster resize + real portal cycle %d/3 complete: %s"), Cycle, *Portal->Describe()));
				if (++Cycle <= 3) { return Next(1); }
				return true;
			default:
				Test->AddError(TEXT("unexpected roster portal test phase"));
				return true;
			}
		}

	private:
		void Move(AGolmokCharacter* Character, AGolmokPortal* Portal, double Distance, double Lateral = 0.0)
		{
			FVector Position = Portal->GetActorLocation() + Portal->GetActorForwardVector() * Distance + Portal->GetActorRightVector() * Lateral;
			Position.Z += Character->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight() + 3.0;
			Character->SetActorLocation(Position, false, nullptr, ETeleportType::TeleportPhysics);
		}

		bool Select(UGolmokCharacterSubsystem* Roster, AGolmokCharacter* Character, AGolmokPortal* Portal, const TCHAR* Id)
		{
			const FVector Before = Character->GetActorLocation();
			const double FeetBefore = Before.Z - Character->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight();
			const double PlaneBefore = Portal->SignedDistanceAlongForward(Before);
			const bool bInsideBefore = Portal->bPlayerInside;
			FString Message;
			if (!Test->TestTrue(FString::Printf(TEXT("select %s in portal phase %d"), Id, Phase), Roster->SelectCharacter(Id, Message)))
			{
				Test->AddError(Message);
				return false;
			}
			const FVector After = Character->GetActorLocation();
			Test->TestEqual(TEXT("selected id committed"), Roster->GetCurrentId(), FString(Id));
			Test->TestTrue(TEXT("same character pawn"), Character == OriginalCharacter.Get());
			Test->TestTrue(TEXT("same controller"), Character->GetController() == OriginalController.Get());
			Test->TestTrue(TEXT("resize keeps feet"), FMath::IsNearlyEqual(After.Z - Character->GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight(), FeetBefore, 0.01));
			Test->TestTrue(TEXT("resize keeps XY"), FMath::IsNearlyEqual(After.X, Before.X, 0.01) && FMath::IsNearlyEqual(After.Y, Before.Y, 0.01));
			Test->TestTrue(TEXT("resize keeps door-plane distance"), FMath::IsNearlyEqual(Portal->SignedDistanceAlongForward(After), PlaneBefore, 0.01));
			Test->TestEqual(TEXT("resize keeps immediate portal side"), Portal->bPlayerInside, bInsideBefore);
			return true;
		}

		bool Next(int32 NextPhase) { Phase = NextPhase; PhaseStart = Now; return false; }
		bool WaitOrFail(double Elapsed, const TCHAR* Message, double Timeout = 10.0)
		{
			if (Elapsed < Timeout) { return false; }
			Test->AddError(FString::Printf(TEXT("%s (phase %d, cycle %d)"), Message, Phase, Cycle));
			return true;
		}
		FAutomationTestBase* Test;
		double CreatedAt;
		double PhaseStart = -1.0;
		double Now = 0.0;
		int32 Phase = 0;
		int32 Cycle = 1;
		TWeakObjectPtr<AGolmokCharacter> OriginalCharacter;
		TWeakObjectPtr<APlayerController> OriginalController;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokCharacterRosterPortalTest, "Golmok.Character.PortalRoundTrip",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokCharacterRosterPortalTest::RunTest(const FString& Parameters)
{
	using namespace GolmokCharacterRosterPortalTest;
	if (!FPackageName::DoesPackageExist(Map) || !FPackageName::DoesPackageExist(InteriorMap))
	{
		AddWarning(TEXT("NOT EXECUTED: run synthetic_zone.run(interior=True) before claiming roster portal integration passed"));
		return true;
	}
	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(Map));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}
#endif
