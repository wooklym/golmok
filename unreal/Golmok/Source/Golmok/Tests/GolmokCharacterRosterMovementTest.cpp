// Functional movement through the real Enhanced Input mapping, not a visual animation verdict.
#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
#include "Camera/CameraComponent.h"
#include "Characters/GolmokCharacterSubsystem.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Editor.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputCoreTypes.h"
#include "InputKeyEventArgs.h"
#include "Misc/PackageName.h"
#include "Player/GolmokCharacter.h"
#include "Tests/AutomationEditorCommon.h"

namespace GolmokCharacterRosterMovementTest
{
	const TCHAR* Map = TEXT("/Game/Golmok/Maps/L_Dev");
	const TCHAR* Ids[] = {TEXT("manny"), TEXT("quinn"), TEXT("proxy135"), TEXT("proxy110")};
	// Independent contract values: do not derive the expected result from the live movement component.
	constexpr float WalkSpeeds[] = {180.f, 180.f, 145.f, 120.f};
	constexpr float RunSpeeds[] = {500.f, 500.f, 380.f, 310.f};

	enum class EPhase : uint8
	{
		Prepare, Ready, SourceRun, SwitchedRun, Walk, Stop, Jump, Curb, Block,
		Corridor, StairsUp, StairsDown, CameraWall, CameraFree
	};

	class FScenario : public IAutomationLatentCommand
	{
	public:
		explicit FScenario(FAutomationTestBase* InTest) : Test(InTest), Started(FPlatformTime::Seconds()) {}
		virtual ~FScenario() override { Cleanup(); }

		virtual bool Update() override
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			APlayerController* LivePC = World ? World->GetFirstPlayerController() : nullptr;
			AGolmokCharacter* LiveCharacter = LivePC ? Cast<AGolmokCharacter>(LivePC->GetPawn()) : nullptr;
			UGolmokCharacterSubsystem* Roster = World ? World->GetSubsystem<UGolmokCharacterSubsystem>() : nullptr;
			if (FPlatformTime::Seconds() - Started > 180.0) return Fail(TEXT("scenario timeout"));
			if (!World || !LivePC || !LiveCharacter || !Roster) return false;
			if (Character.IsValid() && (Character.Get() != LiveCharacter || PC.Get() != LivePC))
				return Fail(TEXT("character/controller unexpectedly replaced"));
			PC = LivePC;
			Character = LiveCharacter;
			if (World->GetTimeSeconds() < 0.6f) return false;
			const double Now = World->GetTimeSeconds();
			const double Elapsed = Now - PhaseAt;
			if (Phase != EPhase::Prepare && Elapsed > 12.0) return Fail(TEXT("phase timeout"));
			FString Message;

			switch (Phase)
			{
			case EPhase::Prepare:
				if (Case == 0 && Fixtures.IsEmpty())
				{
					// Transient collision-only fixtures on empty L_Dev floor, never saved to an asset.
					Box(World, FVector(-4700, -4000, 12.5), FVector(300, 200, 12.5));
					Box(World, FVector(-4700, -4700, 20), FVector(300, 200, 20));
					Box(World, FVector(-4700, -5565, 125), FVector(300, 25, 125));
					Box(World, FVector(-4700, -5435, 125), FVector(300, 25, 125));
					if (Fixtures.Num() != 4) return Fail(TEXT("could not create course fixtures"));
				}
				ReleaseAll();
				ResetAt(-6500, -3000);
				if (!Roster->SelectCharacter(Ids[(Case + 3) % 4], Message)) return Fail(*Message);
				return Next(EPhase::Ready, Now);

			case EPhase::Ready:
				// Let released keys be processed before pressing them again; same-frame release/press
				// does not represent a continuous key hold in the player input event queue.
				if (Elapsed < 0.3 || Movement()->IsFalling()) return false;
				Key(EKeys::W, true);
				Key(EKeys::LeftShift, true);
				return Next(EPhase::SourceRun, Now);

			case EPhase::SourceRun:
				if (Elapsed < 1.2) return false;
				CheckSpeed(TEXT("source held Shift+W"), RunSpeeds[(Case + 3) % 4]);
				{
					const FVector Before = Character->GetActorLocation();
					const double BeforeFeet = Feet();
					if (!Roster->SelectCharacter(Ids[Case], Message)) return Fail(*Message);
					Check(TEXT("running swap preserves XY"), FVector::Dist2D(Before, Character->GetActorLocation()) < 0.01);
					Check(TEXT("running swap preserves capsule bottom"), FMath::Abs(Feet() - BeforeFeet) < 0.01);
					Check(TEXT("running swap preserves pawn"), PC->GetPawn() == Character.Get());
					Check(TEXT("running swap active speed"), FMath::IsNearlyEqual(Movement()->MaxWalkSpeed, RunSpeeds[Case]));
					Check(TEXT("running swap selected id"), Roster->GetCurrentId() == Ids[Case]);
				}
				return Next(EPhase::SwitchedRun, Now);

			case EPhase::SwitchedRun:
				if (Elapsed < 1.2) return false;
				CheckSpeed(TEXT("target held Shift+W"), RunSpeeds[Case]);
				Check(TEXT("held run advances"), Character->GetActorLocation().X - PhasePosition.X > RunSpeeds[Case] * 0.8);
				Key(EKeys::LeftShift, false);
				return Next(EPhase::Walk, Now);

			case EPhase::Walk:
				if (Elapsed < 1.2) return false;
				CheckSpeed(TEXT("Shift released, W still held"), WalkSpeeds[Case]);
				Check(TEXT("held walk advances"), Character->GetActorLocation().X - PhasePosition.X > WalkSpeeds[Case] * 0.8);
				Key(EKeys::W, false);
				return Next(EPhase::Stop, Now);

			case EPhase::Stop:
				if (Elapsed < 0.4) return false;
				Check(TEXT("released input stops movement"), Character->GetVelocity().Size2D() < 1.0);
				JumpBase = Character->GetActorLocation().Z;
				JumpApex = JumpBase;
				bAirborne = false;
				bJumpReleased = false;
				Key(EKeys::SpaceBar, true);
				return Next(EPhase::Jump, Now);

			case EPhase::Jump:
				JumpApex = FMath::Max(JumpApex, Character->GetActorLocation().Z);
				bAirborne |= Movement()->IsFalling();
				if (Elapsed > 0.15 && !bJumpReleased) { Key(EKeys::SpaceBar, false); bJumpReleased = true; }
				if (!bAirborne || Movement()->IsFalling()) return false;
				Check(TEXT("jump apex exceeds 50 cm"), JumpApex - JumpBase >= 50.0);
				Info(FString::Printf(TEXT("jump apex %.2f cm"), JumpApex - JumpBase));
				ResetAt(-5150, -4000);
				Key(EKeys::W, true);
				return Next(EPhase::Curb, Now);

			case EPhase::Curb:
				if (Character->GetActorLocation().X < -4875) return false;
				Check(TEXT("25 cm curb reached on foot"), Movement()->IsMovingOnGround() && FMath::Abs(Feet() - 25.0) < 3.0);
				Check(TEXT("step height remains 25 cm"), FMath::IsNearlyEqual(Movement()->MaxStepHeight, 25.f));
				Info(FString::Printf(TEXT("25 cm curb crossed; capsule bottom %.2f cm"), Feet()));
				ResetAt(-5150, -4700);
				return Next(EPhase::Block, Now);

			case EPhase::Block:
				if (Elapsed < 2.5) return false;
				Check(TEXT("40 cm block face was reached"), Character->GetActorLocation().X > -5075);
				Check(TEXT("40 cm block is not climbed"), Character->GetActorLocation().X < -5000 && FMath::Abs(Feet()) < 3.0);
				Check(TEXT("40 cm block actually stops forward movement"), Character->GetVelocity().Size2D() < 1.0);
				ResetAt(-5150, -5500);
				return Next(EPhase::Corridor, Now);

			case EPhase::Corridor:
				if (Elapsed < 3.0) return false;
				if (Case < 2)
				{
					Check(TEXT("adult reached corridor entrance"), Character->GetActorLocation().X > -5050);
					Check(TEXT("84 cm adult capsule cannot enter 80 cm corridor"), Character->GetActorLocation().X < -4980);
					Check(TEXT("narrow corridor actually stops adult"), Character->GetVelocity().Size2D() < 1.0);
				}
				else
				{
					Check(TEXT("67.2 cm proxy passes 80 cm corridor"), Character->GetActorLocation().X > -4875);
					const FVector Before = Character->GetActorLocation();
					Check(TEXT("growth inside narrow corridor rejected"), !Roster->SelectCharacter(TEXT("manny"), Message));
					Check(TEXT("blocked growth preserves selection"), Roster->GetCurrentId() == Ids[Case]);
					Check(TEXT("blocked growth preserves position"), Character->GetActorLocation().Equals(Before, 0.01));
					CheckSpeed(TEXT("proxy walks inside corridor"), WalkSpeeds[Case]);
				}
				Check(TEXT("corridor traversal stays centered and grounded"),
					FMath::Abs(Character->GetActorLocation().Y + 5500.0) < 3.0 && FMath::Abs(Feet()) < 3.0);
				Info(FString::Printf(TEXT("80 cm corridor x=%.2f cm"), Character->GetActorLocation().X));
				ResetAt(400, -1500);
				return Next(EPhase::StairsUp, Now);

			case EPhase::StairsUp:
				if (Character->GetActorLocation().X < 900) return false;
				Check(TEXT("10 x 17 cm stairs reach 170 cm landing"), Movement()->IsMovingOnGround() && FMath::Abs(Feet() - 170.0) < 3.0);
				Check(TEXT("stairs remain inside 2 m width"), FMath::Abs(Character->GetActorLocation().Y + 1500.0) < 3.0);
				Info(FString::Printf(TEXT("stairs up capsule bottom %.2f cm"), Feet()));
				Key(EKeys::W, false);
				Key(EKeys::S, true);
				return Next(EPhase::StairsDown, Now);

			case EPhase::StairsDown:
				if (Character->GetActorLocation().X > 380 || Movement()->IsFalling()) return false;
				Check(TEXT("stairs descend back to ground"), FMath::Abs(Feet()) < 3.0);
				Info(FString::Printf(TEXT("stairs down capsule bottom %.2f cm"), Feet()));
				ReleaseAll();
				ResetAt(1500, 100);
				PC->SetControlRotation(FRotator(0, -90, 0));
				return Next(EPhase::CameraWall, Now);

			case EPhase::CameraWall:
				if (Elapsed < 0.7) return false;
				Check(TEXT("boom retracts at alley wall"), Character->GetCameraBoom()->IsCollisionFixApplied());
				Check(TEXT("camera remains inside wall y=250"), Character->GetFollowCamera()->GetComponentLocation().Y < 250.0);
				PC->SetControlRotation(FRotator::ZeroRotator);
				return Next(EPhase::CameraFree, Now);

			case EPhase::CameraFree:
				if (Elapsed < 0.7) return false;
				Check(TEXT("boom recovers in open direction"), !Character->GetCameraBoom()->IsCollisionFixApplied());
				Info(TEXT("EXECUTED held-key swap/run/walk/stop/jump/curb/block/corridor/stairs/camera"));
				if (++Case == 4) { Cleanup(); return true; }
				return Next(EPhase::Prepare, Now);
			}
			return Fail(TEXT("unknown phase"));
		}

	private:
		UCharacterMovementComponent* Movement() const { return Character->GetCharacterMovement(); }
		double Feet() const { return Character->GetActorLocation().Z - Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(); }
		void Key(const FKey& InKey, bool bPressed) const
		{
			if (PC.IsValid()) PC->InputKey(FInputKeyEventArgs::CreateSimulated(InKey, bPressed ? IE_Pressed : IE_Released, bPressed ? 1.f : 0.f));
		}
		void ReleaseAll() const
		{
			Key(EKeys::W, false); Key(EKeys::S, false); Key(EKeys::LeftShift, false); Key(EKeys::SpaceBar, false);
		}
		void Cleanup()
		{
			ReleaseAll();
			for (const TWeakObjectPtr<AActor>& Fixture : Fixtures) if (Fixture.IsValid()) Fixture->Destroy();
			Fixtures.Reset();
		}
		void ResetAt(double X, double Y) const
		{
			// Teleport only to set up each course. All measured traversal uses held input and world ticks.
			Movement()->StopMovementImmediately();
			Character->SetActorLocation(FVector(X, Y, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 2), false, nullptr, ETeleportType::TeleportPhysics);
			Character->SetActorRotation(FRotator::ZeroRotator);
			PC->SetControlRotation(FRotator::ZeroRotator);
		}
		void Box(UWorld* World, const FVector& Center, const FVector& Extent)
		{
			AActor* Actor = World->SpawnActor<AActor>();
			if (!Actor) return;
			Fixtures.Add(Actor);
			UBoxComponent* Shape = NewObject<UBoxComponent>(Actor);
			Actor->SetRootComponent(Shape);
			Shape->SetBoxExtent(Extent);
			Shape->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
			Shape->SetCollisionObjectType(ECC_WorldStatic);
			Shape->SetCollisionResponseToAllChannels(ECR_Block);
			Shape->CanCharacterStepUpOn = ECB_Yes;
			Shape->RegisterComponent();
			Actor->SetActorLocation(Center);
		}
		bool Next(EPhase NextPhase, double Now)
		{
			Phase = NextPhase; PhaseAt = Now; PhasePosition = Character->GetActorLocation(); return false;
		}
		void Check(const TCHAR* What, bool bPassed) const { Test->TestTrue(FString::Printf(TEXT("%s: %s"), Ids[Case], What), bPassed); }
		void Info(const FString& What) const { Test->AddInfo(FString::Printf(TEXT("%s: %s"), Ids[Case], *What)); }
		void CheckSpeed(const TCHAR* What, float Expected) const
		{
			const FVector Velocity = Character->GetVelocity();
			Check(What, FMath::Abs(Velocity.Size2D() - Expected) <= Expected * 0.1 && Velocity.GetSafeNormal2D().X > 0.95);
			Info(FString::Printf(TEXT("%s: %.2f cm/s (expected %.0f)"), What, Velocity.Size2D(), Expected));
		}
		bool Fail(const TCHAR* What)
		{
			Test->AddError(FString::Printf(TEXT("%s phase %d: %s"), Ids[Case], static_cast<int32>(Phase), What));
			Cleanup(); return true;
		}

		FAutomationTestBase* Test;
		double Started;
		double PhaseAt = 0.0;
		int32 Case = 0;
		EPhase Phase = EPhase::Prepare;
		TWeakObjectPtr<APlayerController> PC;
		TWeakObjectPtr<AGolmokCharacter> Character;
		TArray<TWeakObjectPtr<AActor>> Fixtures;
		FVector PhasePosition = FVector::ZeroVector;
		double JumpBase = 0.0;
		double JumpApex = 0.0;
		bool bAirborne = false;
		bool bJumpReleased = false;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokCharacterRosterMovementTest, "Golmok.Character.Locomotion",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokCharacterRosterMovementTest::RunTest(const FString& Parameters)
{
	using namespace GolmokCharacterRosterMovementTest;
	if (!FPackageName::DoesPackageExist(Map))
	{
		AddError(TEXT("L_Dev missing; run test.ps1 -SetupDevLevel"));
		return false;
	}
	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(Map));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}
#endif
