// Movement smoke test for AGolmokCharacter on L_Dev (create it first with golmok.setup_dev_level).
//
// Presses the real keys through APlayerController::InputKey, so the C++ mapping context is exercised
// end to end: walk (W/A/S/D), run (hold Shift), jump (Space), mouse look, and the camera boom pulling
// in against the alley wall.
//
// Headless: .\tools\ue\test.ps1   (or in the editor console: Automation RunTests Golmok.)

#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Camera/CameraComponent.h"
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

namespace GolmokCharacterTest
{
	const TCHAR* DevMap = TEXT("/Game/Golmok/Maps/L_Dev");

	// L_Dev alley: walls centered at y = +-300 and 100 cm thick, so the inner faces are at y = +-250.
	constexpr double AlleyWallInnerY = 250.0;

	enum class EPhase : uint8
	{
		WaitForPawn,
		Walk,
		StrafeRight,
		StrafeLeft,
		WalkBack,
		Run,
		RunReleased,
		Stop,
		Jump,
		CameraFree,
		CameraAgainstWall,
		MouseLook,
		Done,
	};

	class FMovementScenario : public IAutomationLatentCommand
	{
	public:
		explicit FMovementScenario(FAutomationTestBase* InTest) : Test(InTest), CreatedAt(FPlatformTime::Seconds()) {}

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

			PC = World->GetFirstPlayerController();
			Character = PC ? Cast<AGolmokCharacter>(PC->GetPawn()) : nullptr;
			if (!Character && Phase != EPhase::WaitForPawn)
			{
				return Fail(TEXT("player character disappeared"), 0.0);
			}

			switch (Phase)
			{
			case EPhase::WaitForPawn:
				if (!Character)
				{
					return Fail(TEXT("no AGolmokCharacter possessed by the first player controller"), 20.0, Elapsed);
				}
				if (Elapsed < 0.5 || Movement()->IsFalling())
				{
					return Fail(TEXT("character never landed on the floor"), 10.0, Elapsed);
				}
				PC->SetControlRotation(FRotator::ZeroRotator);
				Press(EKeys::W);
				return Next(EPhase::Walk, Now);

			case EPhase::Walk:
				if (Elapsed < 1.5)
				{
					return false;
				}
				CheckSpeed(TEXT("walk (W)"), Character->GetWalkSpeed(), FVector::ForwardVector);
				Release(EKeys::W);
				Press(EKeys::D);
				return Next(EPhase::StrafeRight, Now);

			case EPhase::StrafeRight:
				if (Elapsed < 0.6)
				{
					return false;
				}
				CheckSpeed(TEXT("strafe right (D)"), Character->GetWalkSpeed(), FVector::RightVector);
				Release(EKeys::D);
				Press(EKeys::A);
				return Next(EPhase::StrafeLeft, Now);

			case EPhase::StrafeLeft:
				if (Elapsed < 0.6)
				{
					return false;
				}
				CheckSpeed(TEXT("strafe left (A)"), Character->GetWalkSpeed(), -FVector::RightVector);
				Release(EKeys::A);
				Press(EKeys::S);
				return Next(EPhase::WalkBack, Now);

			case EPhase::WalkBack:
				if (Elapsed < 0.6)
				{
					return false;
				}
				CheckSpeed(TEXT("walk back (S)"), Character->GetWalkSpeed(), -FVector::ForwardVector);
				Release(EKeys::S);
				Press(EKeys::W);
				Press(EKeys::LeftShift);
				return Next(EPhase::Run, Now);

			case EPhase::Run:
				if (Elapsed < 2.0)
				{
					return false;
				}
				CheckSpeed(TEXT("run (Shift+W)"), Character->GetRunSpeed(), FVector::ForwardVector);
				Release(EKeys::LeftShift);
				return Next(EPhase::RunReleased, Now);

			case EPhase::RunReleased:
				if (Elapsed < 1.5)
				{
					return false;
				}
				CheckSpeed(TEXT("back to walk after releasing Shift"), Character->GetWalkSpeed(), FVector::ForwardVector);
				Release(EKeys::W);
				return Next(EPhase::Stop, Now);

			case EPhase::Stop:
				if (Character->GetVelocity().Size2D() > 1.0)
				{
					return Fail(TEXT("character did not stop after releasing all keys"), 3.0, Elapsed);
				}
				JumpStartZ = Character->GetActorLocation().Z;
				JumpApexZ = JumpStartZ;
				bLeftGround = false;
				Press(EKeys::SpaceBar);
				return Next(EPhase::Jump, Now);

			case EPhase::Jump:
				JumpApexZ = FMath::Max(JumpApexZ, Character->GetActorLocation().Z);
				bLeftGround |= Movement()->IsFalling();
				if (Elapsed >= 0.15 && !bSpaceReleased)
				{
					Release(EKeys::SpaceBar);
					bSpaceReleased = true;
				}
				if (!bLeftGround || Movement()->IsFalling())
				{
					return Fail(TEXT("jump (Space) did not leave the ground and land again"), 3.0, Elapsed);
				}
				{
					const double Height = JumpApexZ - JumpStartZ;
					Test->AddInfo(FString::Printf(TEXT("jump (Space): apex %.0f cm, airborne %.2f s"), Height, Elapsed));
					Test->TestTrue(TEXT("jump apex is at least 50 cm"), Height >= 50.0);
				}
				// Look along the alley: the boom points back down the open alley and must not be shortened.
				PC->SetControlRotation(FRotator::ZeroRotator);
				return Next(EPhase::CameraFree, Now);

			case EPhase::CameraFree:
				if (Elapsed < 1.0)
				{
					return false;
				}
				Test->TestFalse(TEXT("camera boom is not shortened when nothing is behind the character"),
					Character->GetCameraBoom()->IsCollisionFixApplied());
				// Look at the right wall: the boom now points into the left wall and has to pull in.
				PC->SetControlRotation(FRotator(0.0, 90.0, 0.0));
				return Next(EPhase::CameraAgainstWall, Now);

			case EPhase::CameraAgainstWall:
				if (Elapsed < 1.0)
				{
					return false;
				}
				{
					const FVector CharacterLocation = Character->GetActorLocation();
					const FVector CameraLocation = Character->GetFollowCamera()->GetComponentLocation();
					Test->AddInfo(FString::Printf(TEXT("camera vs wall: character y=%.0f, camera y=%.0f, wall face y=%.0f"),
						CharacterLocation.Y, CameraLocation.Y, -AlleyWallInnerY));
					Test->TestTrue(TEXT("character is inside the alley for the camera check"),
						FMath::Abs(CharacterLocation.Y) < AlleyWallInnerY - 50.0 && CharacterLocation.X > 0.0);
					Test->TestTrue(TEXT("camera boom collision fix is applied against the alley wall"),
						Character->GetCameraBoom()->IsCollisionFixApplied());
					Test->TestTrue(TEXT("camera stays on the alley side of the wall"), CameraLocation.Y > -AlleyWallInnerY);
				}
				PC->SetControlRotation(FRotator::ZeroRotator);
				StartRotation = PC->GetControlRotation();
				return Next(EPhase::MouseLook, Now);

			case EPhase::MouseLook:
				// Mouse right and up for a few frames, like a real mouse sending MouseX/MouseY deltas.
				// A fixed frame count keeps the total turn small (no yaw wrap-around) at any frame rate.
				if (MouseFrames < 3)
				{
					PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::MouseX, IE_Axis, 2.f));
					PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::MouseY, IE_Axis, 2.f));
					++MouseFrames;
					return false;
				}
				if (Elapsed < 0.2)
				{
					return false;
				}
				{
					const FRotator Rotation = PC->GetControlRotation();
					const double DeltaYaw = FRotator::NormalizeAxis(Rotation.Yaw - StartRotation.Yaw);
					const double DeltaPitch = FRotator::NormalizeAxis(Rotation.Pitch - StartRotation.Pitch);
					Test->AddInfo(FString::Printf(TEXT("mouse look: yaw %+.1f deg, pitch %+.1f deg"), DeltaYaw, DeltaPitch));
					// Only the sign matters; the amount depends on mouse smoothing and frame timing.
					Test->TestTrue(TEXT("mouse right turns the camera right"), DeltaYaw > 0.1);
					Test->TestTrue(TEXT("mouse up looks up (not inverted)"), DeltaPitch > 0.1);
				}
				return Next(EPhase::Done, Now);

			case EPhase::Done:
				return true;
			}
			return true;
		}

	private:
		UCharacterMovementComponent* Movement() const { return Character->GetCharacterMovement(); }

		void Press(const FKey& Key) const { PC->InputKey(FInputKeyEventArgs::CreateSimulated(Key, IE_Pressed, 1.f)); }
		void Release(const FKey& Key) const { PC->InputKey(FInputKeyEventArgs::CreateSimulated(Key, IE_Released, 0.f)); }

		bool Next(EPhase NextPhase, double Now)
		{
			Phase = NextPhase;
			PhaseStart = Now;
			return false;
		}

		/** Keeps waiting until Timeout (seconds of game time in this phase), then records the error and stops. */
		bool Fail(const TCHAR* What, double Timeout, double Elapsed = 0.0)
		{
			if (Elapsed < Timeout)
			{
				return false;
			}
			Test->AddError(FString::Printf(TEXT("%s (phase %d, %.1f s)"), What, static_cast<int32>(Phase), Elapsed));
			return true;
		}

		/** Velocity should be at the expected speed (+-10%) and point along Direction relative to the control yaw. */
		void CheckSpeed(const TCHAR* What, double ExpectedSpeed, const FVector& Direction) const
		{
			const FVector Velocity = Character->GetVelocity();
			const double Speed = Velocity.Size2D();
			const FVector WorldDirection = FRotator(0.0, PC->GetControlRotation().Yaw, 0.0).RotateVector(Direction);
			const double Alignment = FVector::DotProduct(Velocity.GetSafeNormal2D(), WorldDirection);
			Test->AddInfo(FString::Printf(TEXT("%s: %.0f cm/s (expected %.0f), direction match %.2f"), What, Speed, ExpectedSpeed, Alignment));
			Test->TestTrue(FString::Printf(TEXT("%s speed within 10%%"), What), FMath::Abs(Speed - ExpectedSpeed) <= 0.1 * ExpectedSpeed);
			Test->TestTrue(FString::Printf(TEXT("%s direction"), What), Alignment > 0.95);
		}

		FAutomationTestBase* Test;
		double CreatedAt;
		EPhase Phase = EPhase::WaitForPawn;
		double PhaseStart = -1.0;
		APlayerController* PC = nullptr;
		AGolmokCharacter* Character = nullptr;
		double JumpStartZ = 0.0;
		double JumpApexZ = 0.0;
		bool bLeftGround = false;
		bool bSpaceReleased = false;
		FRotator StartRotation = FRotator::ZeroRotator;
		int32 MouseFrames = 0;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokCharacterMovementTest, "Golmok.Player.Movement",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokCharacterMovementTest::RunTest(const FString& Parameters)
{
	using namespace GolmokCharacterTest;

	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddError(FString::Printf(TEXT("%s is missing. Run golmok.setup_dev_level in the editor first."), DevMap));
		return false;
	}

	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FMovementScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

#endif
