// WP-19a (D-021) automation: Golmok.Animation.Config / StateProvider / Fallback / GaspSmoke (design section 12).
//
// All four pass without GASP content: Config needs no PIE, StateProvider spawns the native AGolmokGaspCharacter on
// L_Dev (no GASP asset involved), Fallback asks for gasp with a missing pawn class through FScopedConfigOverride (the
// same result on a PC that has GASP), and GaspSmoke skips with Info "GASP not installed — skipped" until add-gasp and
// the 19b Blueprint exist. Keys go through APlayerController::InputKey like Golmok.Player.Movement.
//
// Headless: .\tools\ue\test.ps1 -Filter Golmok.Animation   (L_Dev: -SetupDevLevel)

#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Animation/AnimInstance.h"
#include "Animation/GolmokAnimationConfig.h"
#include "Animation/GolmokAnimationSubsystem.h"
#include "Animation/GolmokGaspCharacter.h"
#include "Animation/GolmokLocomotionMath.h"
#include "Animation/GolmokLocomotionStateComponent.h"
#include "Characters/GolmokCharacterSubsystem.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Debug/GolmokDebugSubsystem.h"
#include "Dom/JsonObject.h"
#include "Editor.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/LocalPlayer.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "InputCoreTypes.h"
#include "InputKeyEventArgs.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Player/GolmokCharacter.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Tests/AutomationEditorCommon.h"

namespace GolmokAnimationTest
{
	const TCHAR* DevMap = TEXT("/Game/Golmok/Maps/L_Dev");
	const TCHAR* MannyMesh = TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple");
	const TCHAR* MannyAnim = TEXT("/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed.ABP_Unarmed_C");
	const TCHAR* FallbackWarning = TEXT("anim: falling back to ABP pawn (GASP pawn class missing");
	// Open L_Dev floor (golmok.setup_dev_level: 200 m plane, course objects at x > -600 or y > -2300).
	constexpr double OpenFloorX = -6500.0;
	constexpr double OpenFloorY = -3000.0;
	// Independent contract values (D-021 keeps them; do not derive them from the live components).
	constexpr double WalkCmS = 180.0;
	constexpr double RunCmS = 500.0;
	constexpr double JumpCm = 90.0;

	// A valid config, independent of the committed file (the file itself is checked separately).
	const TCHAR* BaseConfig = TEXT(R"JSON({
  "schema_version": 1,
  "mode": "abp",
  "gasp": {
    "content_root": "/Game/GASP",
    "pawn_class": "/Game/GolmokLocal/GASP/BP_GolmokCharacter_GASP.BP_GolmokCharacter_GASP_C",
    "pawn_interface": "Blueprints/Interfaces/BPI_SandboxCharacter_Pawn.BPI_SandboxCharacter_Pawn_C",
    "anim_class": "Blueprints/SandboxCharacter_CMC_ABP.SandboxCharacter_CMC_ABP_C",
    "preview": {"source_mesh": "Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin.SKM_UEFN_Mannequin", "visual_mesh": null, "visual_anim_class": null},
    "movement_profile": "p0",
    "state": {"just_landed_seconds": 0.3, "teleport_jump_cm": 100, "reinit_anim_on_teleport": true}
  },
  "movement_profiles": {
    "p0": {"max_acceleration": 2048, "braking_deceleration_walking": 2000, "ground_friction": 8, "braking_friction_factor": 2, "use_separate_braking_friction": false, "braking_friction": 0},
    "p1": null,
    "p2": null
  }
})JSON");

	FString Variant(const TCHAR* From, const TCHAR* To)
	{
		return FString(BaseConfig).Replace(From, To, ESearchCase::CaseSensitive);
	}

	FString GaspModeConfig(const TCHAR* PawnClass)
	{
		return Variant(TEXT("\"mode\": \"abp\""), TEXT("\"mode\": \"gasp\""))
			.Replace(TEXT("/Game/GolmokLocal/GASP/BP_GolmokCharacter_GASP.BP_GolmokCharacter_GASP_C"), PawnClass, ESearchCase::CaseSensitive);
	}

	/**
	 * The committed animation.json with "mode" set (and optionally gasp.movement_profile forced to p0), so the
	 * tests keep their meaning after 19b fills p1 / p2 or picks another profile. Empty when the file does not parse.
	 */
	FString CommittedConfigWith(const TCHAR* Mode, bool bForceP0)
	{
		FString Text;
		TSharedPtr<FJsonObject> Root;
		if (!FFileHelper::LoadFileToString(Text, *GolmokAnimation::ConfigFilePath()))
		{
			return FString();
		}
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
		if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
		{
			return FString();
		}
		Root->SetStringField(TEXT("mode"), Mode);
		const TSharedPtr<FJsonObject>* Gasp = nullptr;
		if (bForceP0 && Root->TryGetObjectField(TEXT("gasp"), Gasp) && Gasp && Gasp->IsValid())
		{
			(*Gasp)->SetStringField(TEXT("movement_profile"), TEXT("p0"));
		}
		FString Out;
		const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Out);
		return FJsonSerializer::Serialize(Root.ToSharedRef(), Writer) ? Out : FString();
	}

	bool SameMovementAsAbpPawn(FAutomationTestBase* Test, const UCharacterMovementComponent* Movement, const TCHAR* What)
	{
		const UCharacterMovementComponent* Cdo = GetDefault<AGolmokCharacter>()->GetCharacterMovement();
		if (!Test->TestNotNull(TEXT("AGolmokCharacter CDO movement"), Cdo) || !Movement)
		{
			return false;
		}
		const bool bSame = FMath::IsNearlyEqual(Movement->MaxAcceleration, Cdo->MaxAcceleration)
			&& FMath::IsNearlyEqual(Movement->BrakingDecelerationWalking, Cdo->BrakingDecelerationWalking)
			&& FMath::IsNearlyEqual(Movement->GroundFriction, Cdo->GroundFriction)
			&& FMath::IsNearlyEqual(Movement->BrakingFrictionFactor, Cdo->BrakingFrictionFactor)
			&& Movement->bUseSeparateBrakingFriction == Cdo->bUseSeparateBrakingFriction
			&& FMath::IsNearlyEqual(Movement->BrakingFriction, Cdo->BrakingFriction)
			&& FMath::IsNearlyEqual(Movement->JumpZVelocity, Cdo->JumpZVelocity)
			&& FMath::IsNearlyEqual(Movement->RotationRate.Yaw, Cdo->RotationRate.Yaw)
			&& Movement->bOrientRotationToMovement == Cdo->bOrientRotationToMovement;
		Test->AddInfo(FString::Printf(TEXT("%s: accel %.0f/%.0f braking %.0f/%.0f friction %.2f/%.2f factor %.2f/%.2f separate %d/%d braking friction %.2f/%.2f (pawn/CDO)"),
			What, Movement->MaxAcceleration, Cdo->MaxAcceleration, Movement->BrakingDecelerationWalking, Cdo->BrakingDecelerationWalking,
			Movement->GroundFriction, Cdo->GroundFriction, Movement->BrakingFrictionFactor, Cdo->BrakingFrictionFactor,
			Movement->bUseSeparateBrakingFriction ? 1 : 0, Cdo->bUseSeparateBrakingFriction ? 1 : 0, Movement->BrakingFriction, Cdo->BrakingFriction));
		return Test->TestTrue(FString::Printf(TEXT("%s: movement values equal the AGolmokCharacter CDO"), What), bSame);
	}

	/** Shared latent helpers: phase clock, keys, timeouts. */
	class FScenarioBase : public IAutomationLatentCommand
	{
	public:
		explicit FScenarioBase(FAutomationTestBase* InTest) : Test(InTest), CreatedAt(FPlatformTime::Seconds()) {}

	protected:
		void Press(const FKey& Key) const { PC->InputKey(FInputKeyEventArgs::CreateSimulated(Key, IE_Pressed, 1.f)); }
		void Release(const FKey& Key) const { PC->InputKey(FInputKeyEventArgs::CreateSimulated(Key, IE_Released, 0.f)); }

		/** Keeps waiting until Timeout (seconds of game time in this phase), then records the error and stops. */
		bool Fail(const FString& What, double Timeout = 0.0, double Elapsed = 0.0)
		{
			if (Elapsed < Timeout)
			{
				return false;
			}
			Test->AddError(FString::Printf(TEXT("%s (phase %d, %.1f s)"), *What, Phase, Elapsed));
			return true;
		}

		bool Next(int32 NextPhase, double Now)
		{
			Phase = NextPhase;
			PhaseStart = Now;
			return false;
		}

		void CheckSpeed(const TCHAR* What, double Expected) const
		{
			const double Speed = Character->GetVelocity().Size2D();
			Test->AddInfo(FString::Printf(TEXT("%s: %.0f cm/s (expected %.0f)"), What, Speed, Expected));
			Test->TestTrue(FString::Printf(TEXT("%s speed within 10%%"), What), FMath::Abs(Speed - Expected) <= 0.1 * Expected);
		}

		void ResetAt(double X, double Y) const
		{
			Character->GetCharacterMovement()->StopMovementImmediately();
			Character->SetActorLocation(FVector(X, Y, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 2.0), false, nullptr,
				ETeleportType::TeleportPhysics);
			Character->SetActorRotation(FRotator::ZeroRotator);
			PC->SetControlRotation(FRotator::ZeroRotator);
		}

		FAutomationTestBase* Test;
		double CreatedAt;
		int32 Phase = 0;
		double PhaseStart = -1.0;
		APlayerController* PC = nullptr;
		AGolmokCharacter* Character = nullptr;
	};

	// ---- Golmok.Animation.StateProvider ----------------------------------------------------------------------------

	class FStateProviderScenario : public FScenarioBase
	{
	public:
		FStateProviderScenario(FAutomationTestBase* InTest, TSharedPtr<GolmokAnimation::FScopedConfigOverride> InOverride)
			: FScenarioBase(InTest), Override(MoveTemp(InOverride)) {}

		virtual ~FStateProviderScenario() override
		{
			if (UGolmokLocomotionStateComponent* Component = State())
			{
				Component->OnFootEvent.Remove(FootHandle);
			}
		}

		enum EPhase : int32 { WaitForPawn, Possess, Settle, Idle, Walk, Run, RosterSpeeds, RestoreSpeeds, RunReleased, Stopping,
			Jump, LandingWindow, FootEvent, Teleport, TeleportCheck, Visual, Done };

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
			if (!Character)
			{
				return Fail(TEXT("no AGolmokCharacter possessed by the first player controller"), 20.0, Elapsed);
			}
			if (Phase > Possess && Character != Gasp.Get())
			{
				return Fail(TEXT("the GASP pawn was replaced"));
			}
			UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
			UGolmokLocomotionStateComponent* Component = State();
			const FGolmokLocomotionState S = Component ? Component->GetLocomotionState() : FGolmokLocomotionState();

			switch (Phase)
			{
			case WaitForPawn:
				if (Elapsed < 0.5 || Movement->IsFalling())
				{
					return Fail(TEXT("default pawn never landed"), 10.0, Elapsed);
				}
				{
					FActorSpawnParameters Params;
					Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
					AGolmokGaspCharacter* Spawned = World->SpawnActor<AGolmokGaspCharacter>(AGolmokGaspCharacter::StaticClass(),
						FVector(OpenFloorX, OpenFloorY, 120.0), FRotator::ZeroRotator, Params);
					if (!Spawned)
					{
						return Fail(TEXT("could not spawn the native AGolmokGaspCharacter"));
					}
					Gasp = Spawned;
					APawn* Old = PC->GetPawn();
					// The old pawn's IMC_Default stays in the subsystem at the same priority and could consume
					// W / Shift / Space first; the new pawn re-adds its own context in NotifyControllerChanged.
					if (UEnhancedInputLocalPlayerSubsystem* Input =
							ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
					{
						Input->ClearAllMappings();
					}
					PC->Possess(Spawned);
					if (Old && Old != Spawned)
					{
						Old->Destroy();
					}
				}
				return Next(Possess, Now);

			case Possess:
				if (Character != Gasp.Get() || Elapsed < 0.5 || Movement->IsFalling())
				{
					return Fail(TEXT("the GASP pawn was not possessed or never landed"), 10.0, Elapsed);
				}
				if (!Test->TestNotNull(TEXT("locomotion state component"), Component))
				{
					return true;
				}
				FootHandle = Component->OnFootEvent.AddLambda([this](EGolmokFootEvent, bool) { ++FootEvents; });
				Test->TestEqual(TEXT("p0 applied by PostInitializeComponents"), Gasp->GetAppliedProfileId(), FString(TEXT("p0")));
				SameMovementAsAbpPawn(Test, Movement, TEXT("GASP pawn after p0"));
				Test->TestTrue(TEXT("walk speed unchanged"), FMath::IsNearlyEqual(static_cast<double>(Character->GetWalkSpeed()), WalkCmS));
				Test->TestTrue(TEXT("run speed unchanged"), FMath::IsNearlyEqual(static_cast<double>(Character->GetRunSpeed()), RunCmS));
				ResetAt(OpenFloorX, OpenFloorY);
				return Next(Settle, Now);

			case Settle:
				if (Elapsed < 0.6 || Movement->IsFalling())
				{
					return Fail(TEXT("GASP pawn did not settle"), 5.0, Elapsed);
				}
				return Next(Idle, Now);

			case Idle:
				Test->TestTrue(TEXT("standing: Idle"), S.MovingState == EGolmokMovingState::Idle);
				Test->TestTrue(TEXT("standing: OnGround"), S.MovementMode == EGolmokMovementMode::OnGround);
				Test->TestTrue(TEXT("standing: Walk gait"), S.Gait == EGolmokGait::Walk);
				Test->TestTrue(TEXT("standing: no intent"), S.InputIntent.IsNearlyZero());
				Test->TestTrue(TEXT("stance and rotation mode are fixed"),
					S.Stance == EGolmokStance::Stand && S.RotationMode == EGolmokRotationMode::OrientToMovement);
				Press(EKeys::W);
				return Next(Walk, Now);

			case Walk:
				if (Elapsed < 1.5)
				{
					return false;
				}
				CheckSpeed(TEXT("GASP pawn walk (W)"), WalkCmS);
				Test->TestTrue(TEXT("W: Walk"), S.Gait == EGolmokGait::Walk);
				Test->TestTrue(TEXT("W: Moving"), S.MovingState == EGolmokMovingState::Moving);
				{
					const FVector Forward = FRotator(0.0, PC->GetControlRotation().Yaw, 0.0).Vector();
					Test->AddInfo(FString::Printf(TEXT("W intent (%.3f, %.3f) length %.3f"), S.InputIntent.X, S.InputIntent.Y, S.InputIntent.Size2D()));
					Test->TestTrue(TEXT("W: intent is about the forward unit vector"),
						FMath::Abs(S.InputIntent.Size2D() - 1.0) < 0.05 && FVector::DotProduct(S.InputIntent.GetSafeNormal2D(), Forward) > 0.95);
				}
				Press(EKeys::LeftShift);
				return Next(Run, Now);

			case Run:
				if (Elapsed < 2.0)
				{
					return false;
				}
				CheckSpeed(TEXT("GASP pawn run (Shift+W)"), RunCmS);
				Test->TestTrue(TEXT("Shift: Run"), S.Gait == EGolmokGait::Run);
				Character->SetMovementSpeeds(145.f, 380.f); // WP-18 roster proxy135 speeds while Shift is held
				return Next(RosterSpeeds, Now);

			case RosterSpeeds:
				if (Elapsed < 1.5)
				{
					return false;
				}
				CheckSpeed(TEXT("roster 145/380 while running"), 380.0);
				Test->TestTrue(TEXT("SetMovementSpeeds(145, 380) keeps Run"), S.Gait == EGolmokGait::Run);
				Character->SetMovementSpeeds(static_cast<float>(WalkCmS), static_cast<float>(RunCmS));
				return Next(RestoreSpeeds, Now);

			case RestoreSpeeds:
				if (Elapsed < 0.5)
				{
					return false;
				}
				Test->TestTrue(TEXT("back to 180/500 keeps Run"), S.Gait == EGolmokGait::Run);
				Release(EKeys::LeftShift);
				return Next(RunReleased, Now);

			case RunReleased:
				if (Elapsed < 1.5)
				{
					return false;
				}
				CheckSpeed(TEXT("GASP pawn walk after Shift"), WalkCmS);
				Test->TestTrue(TEXT("Shift released: Walk"), S.Gait == EGolmokGait::Walk);
				Release(EKeys::W);
				bSawMovingWhileBraking = false;
				return Next(Stopping, Now);

			case Stopping:
				bSawMovingWhileBraking |= S.MovingState == EGolmokMovingState::Moving && S.Speed2D < 10.f;
				if (S.MovingState != EGolmokMovingState::Idle || Character->GetVelocity().Size2D() > 1.0)
				{
					return Fail(TEXT("state did not return to Idle after releasing W"), 3.0, Elapsed);
				}
				Test->AddInfo(FString::Printf(TEXT("Idle after %.2f s (hysteresis seen while braking: %s)"), Elapsed,
					bSawMovingWhileBraking ? TEXT("yes") : TEXT("no")));
				Test->TestTrue(TEXT("released: no intent"), S.InputIntent.IsNearlyZero());
				JumpStartZ = JumpApexZ = Character->GetActorLocation().Z;
				bLeftGround = bSawInAir = bSpaceReleased = false;
				Press(EKeys::SpaceBar);
				return Next(Jump, Now);

			case Jump:
				JumpApexZ = FMath::Max(JumpApexZ, Character->GetActorLocation().Z);
				bLeftGround |= Movement->IsFalling();
				bSawInAir |= S.MovementMode == EGolmokMovementMode::InAir;
				if (Elapsed >= 0.15 && !bSpaceReleased)
				{
					Release(EKeys::SpaceBar);
					bSpaceReleased = true;
				}
				if (!bLeftGround || Movement->IsFalling())
				{
					return Fail(TEXT("jump (Space) did not leave the ground and land again"), 3.0, Elapsed);
				}
				{
					const double Height = JumpApexZ - JumpStartZ;
					Test->AddInfo(FString::Printf(TEXT("GASP pawn jump apex %.1f cm; land velocity z %.0f; just landed %d (%.3f s ago)"), Height,
						S.LandVelocity.Z, S.bJustLanded ? 1 : 0, Component->GetSecondsSinceLanding()));
					Test->TestTrue(TEXT("jump apex about 90 cm"), FMath::Abs(Height - JumpCm) <= 10.0);
					Test->TestTrue(TEXT("Space: InAir while falling"), bSawInAir);
					Test->TestTrue(TEXT("landing: bJustLanded"), S.bJustLanded);
					Test->TestTrue(TEXT("landing: LandVelocity.Z < -300"), S.LandVelocity.Z < -300.0);
				}
				return Next(LandingWindow, Now);

			case LandingWindow:
				if (Component->GetSecondsSinceLanding() < Component->GetJustLandedSeconds() + 0.1)
				{
					return Fail(TEXT("landing time never advanced"), 3.0, Elapsed);
				}
				Test->TestFalse(TEXT("0.3 s after landing: bJustLanded false"), S.bJustLanded);
				Test->TestTrue(TEXT("back on the ground"), S.MovementMode == EGolmokMovementMode::OnGround);
				return Next(FootEvent, Now);

			case FootEvent:
				FootEvents = 0;
				Component->NotifyFootEvent(EGolmokFootEvent::Step, true);
				Test->TestEqual(TEXT("NotifyFootEvent once -> OnFootEvent once"), FootEvents, 1);
				TeleportsBefore = Component->GetTeleportCount();
				ReinitBefore = Component->GetAnimReinitCount();
				TeleportFrom = Character->GetActorLocation();
				Character->SetActorLocation(TeleportFrom + FVector(400.0, 0.0, 0.0), false, nullptr, ETeleportType::TeleportPhysics);
				return Next(Teleport, Now);

			case Teleport:
				if (Elapsed < 0.3)
				{
					return false;
				}
				Test->TestTrue(TEXT("400 cm jump detected as a teleport"), Component->GetTeleportCount() > TeleportsBefore);
				Test->TestTrue(TEXT("reinit_anim_on_teleport re-initialised the anim instance"), Component->GetAnimReinitCount() > ReinitBefore);
				Character->SetActorLocation(TeleportFrom, false, nullptr, ETeleportType::TeleportPhysics);
				return Next(TeleportCheck, Now);

			case TeleportCheck:
				if (Elapsed < 0.3)
				{
					return false;
				}
				if (UGolmokAnimationSubsystem* Anim = World->GetSubsystem<UGolmokAnimationSubsystem>())
				{
					const FString Line = Anim->BuildHudLine();
					Test->AddInfo(Line);
					Test->TestTrue(TEXT("HUD line reports the GASP pawn state"), Line.StartsWith(TEXT("anim: gasp p0 | ground walk idle | intent 0.00")));
					IConsoleManager::Get().ProcessUserConsoleInput(TEXT("golmok.anim status"), *GLog, World);
				}
				else
				{
					Test->AddError(TEXT("UGolmokAnimationSubsystem missing in PIE"));
				}
				if (UGolmokDebugSubsystem* Debug = World->GetSubsystem<UGolmokDebugSubsystem>())
				{
					Test->TestTrue(TEXT("HUD has one anim: line"),
						Debug->GetHudLines().FilterByPredicate([](const FString& Line) { return Line.StartsWith(TEXT("anim: ")); }).Num() == 1);
				}
				return Next(Visual, Now);

			case Visual:
				if (!FPackageName::DoesPackageExist(FSoftObjectPath(MannyMesh).GetLongPackageName()))
				{
					Test->AddInfo(TEXT("mannequin pack missing (tools/ue/add-mannequin.ps1): visual override check skipped"));
					return Next(Done, Now);
				}
				{
					USkeletalMesh* Manny = Cast<USkeletalMesh>(FSoftObjectPath(MannyMesh).TryLoad());
					UClass* Anim = FSoftClassPath(MannyAnim).TryLoadClass<UAnimInstance>();
					USkeletalMeshComponent* Source = Gasp->GetMesh();
					USkeletalMeshComponent* VisualMesh = Gasp->GetVisualMesh();
					FString Error;
					if (!Test->TestTrue(TEXT("SetVisualOverride(Manny, ABP_Unarmed)"), Gasp->SetVisualOverride(Manny, Anim, Error)))
					{
						Test->AddError(Error);
						return true;
					}
					Test->TestTrue(TEXT("override hides GetMesh() from rendering"), Source->bHiddenInGame);
					Test->TestTrue(TEXT("override keeps GetMesh() posing"),
						Source->VisibilityBasedAnimTickOption == EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones);
					Test->TestTrue(TEXT("visual mesh visible with Manny"), !VisualMesh->bHiddenInGame && VisualMesh->GetSkeletalMeshAsset() == Manny);
					Test->TestTrue(TEXT("visual mesh is attached to GetMesh()"), VisualMesh->GetAttachParent() == Source);
					Gasp->ClearVisualOverride();
					Test->TestFalse(TEXT("clear shows GetMesh() again"), Source->bHiddenInGame);
					Test->TestNull(TEXT("clear empties the visual mesh"), VisualMesh->GetSkeletalMeshAsset());
					Test->TestFalse(TEXT("clear restores the override flag"), Gasp->HasVisualOverride());
				}
				return Next(Done, Now);

			case Done:
			default:
				return true;
			}
		}

	private:
		UGolmokLocomotionStateComponent* State() const
		{
			return Gasp.IsValid() ? Gasp->GetLocomotionStateComponent() : nullptr;
		}

		TSharedPtr<GolmokAnimation::FScopedConfigOverride> Override; // mode abp, no -GolmokAnim / console influence
		TWeakObjectPtr<AGolmokGaspCharacter> Gasp;
		FDelegateHandle FootHandle;
		int32 FootEvents = 0;
		int32 TeleportsBefore = 0;
		int32 ReinitBefore = 0;
		FVector TeleportFrom = FVector::ZeroVector;
		double JumpStartZ = 0.0;
		double JumpApexZ = 0.0;
		bool bLeftGround = false;
		bool bSawInAir = false;
		bool bSpaceReleased = false;
		bool bSawMovingWhileBraking = false;
	};

	// ---- Golmok.Animation.Fallback ---------------------------------------------------------------------------------

	class FFallbackScenario : public FScenarioBase
	{
	public:
		FFallbackScenario(FAutomationTestBase* InTest, TSharedPtr<GolmokAnimation::FScopedConfigOverride> InOverride)
			: FScenarioBase(InTest), Override(MoveTemp(InOverride)) {}

		enum EPhase : int32 { WaitForPawn, Walk, Run, Done };

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
			APawn* Pawn = PC ? PC->GetPawn() : nullptr;
			Character = Cast<AGolmokCharacter>(Pawn);
			if (!Character)
			{
				return Fail(TEXT("no AGolmokCharacter possessed by the first player controller"), 20.0, Elapsed);
			}
			UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
			switch (Phase)
			{
			case WaitForPawn:
				if (Elapsed < 0.5 || Movement->IsFalling())
				{
					return Fail(TEXT("fallback pawn never landed"), 10.0, Elapsed);
				}
				Test->TestTrue(TEXT("mode gasp + missing pawn_class spawns exactly AGolmokCharacter"), Pawn->GetClass() == AGolmokCharacter::StaticClass());
				if (UGolmokAnimationSubsystem* Anim = World->GetSubsystem<UGolmokAnimationSubsystem>())
				{
					Test->TestEqual(TEXT("one fallback Warning in this world"), Anim->GetFallbackWarningCount(), 1);
					Test->TestTrue(TEXT("fallback reason names the missing pawn class"),
						Anim->GetLastFallbackReason().StartsWith(TEXT("GASP pawn class missing — add-gasp / 19b (/Game/GolmokLocal/GASP/BP_Missing")));
					Test->TestTrue(TEXT("HUD line shows the fallback"), Anim->BuildHudLine().StartsWith(TEXT("anim: abp (fallback: GASP pawn class missing")));
				}
				else
				{
					Test->AddError(TEXT("UGolmokAnimationSubsystem missing in PIE"));
				}
				if (UGolmokCharacterSubsystem* Roster = World->GetSubsystem<UGolmokCharacterSubsystem>())
				{
					if (FPackageName::DoesPackageExist(FSoftObjectPath(MannyMesh).GetLongPackageName()))
					{
						Test->TestEqual(TEXT("roster applied manny to the fallback pawn"), Roster->GetCurrentId(), FString(TEXT("manny")));
					}
					else
					{
						Test->AddInfo(TEXT("mannequin pack missing: roster manny check skipped"));
					}
				}
				SameMovementAsAbpPawn(Test, Movement, TEXT("fallback pawn"));
				Test->TestTrue(TEXT("no locomotion state component on the ABP pawn"), !Character->FindComponentByClass<UGolmokLocomotionStateComponent>());
				ResetAt(OpenFloorX, OpenFloorY);
				Press(EKeys::W);
				return Next(Walk, Now);

			case Walk:
				if (Elapsed < 1.5)
				{
					return false;
				}
				CheckSpeed(TEXT("fallback pawn walk"), WalkCmS);
				Press(EKeys::LeftShift);
				return Next(Run, Now);

			case Run:
				if (Elapsed < 2.0)
				{
					return false;
				}
				CheckSpeed(TEXT("fallback pawn run"), RunCmS);
				Release(EKeys::LeftShift);
				Release(EKeys::W);
				return Next(Done, Now);

			case Done:
			default:
				return true;
			}
		}

	private:
		TSharedPtr<GolmokAnimation::FScopedConfigOverride> Override; // alive from RunTest until the scenario ends
	};

	// ---- Golmok.Animation.GaspSmoke --------------------------------------------------------------------------------

	struct FFootTrack
	{
		FName Bone;
		TArray<GolmokLocomotionMath::FootSample> Samples;
		FVector Min = FVector(UE_BIG_NUMBER);
		FVector Max = FVector(-UE_BIG_NUMBER);
	};

	class FGaspSmokeScenario : public FScenarioBase
	{
	public:
		FGaspSmokeScenario(FAutomationTestBase* InTest, TSharedPtr<GolmokAnimation::FScopedConfigOverride> InOverride,
			const GolmokAnimation::FConfig& InConfig)
			: FScenarioBase(InTest), Override(MoveTemp(InOverride)), Config(InConfig) {}

		enum EPhase : int32 { WaitForPawn, Settle, Walk, Run, Done };

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
			AGolmokGaspCharacter* Gasp = Cast<AGolmokGaspCharacter>(Character);
			if (!Gasp)
			{
				return Fail(TEXT("the resolved GASP pawn was not spawned (see the anim: fallback Warning)"), 20.0, Elapsed);
			}
			UGolmokLocomotionStateComponent* Component = Gasp->GetLocomotionStateComponent();
			USkeletalMeshComponent* Mesh = Gasp->GetMesh();
			switch (Phase)
			{
			case WaitForPawn:
			{
				if (Elapsed < 0.5 || Gasp->GetCharacterMovement()->IsFalling())
				{
					return Fail(TEXT("GASP pawn never landed"), 10.0, Elapsed);
				}
				Test->AddInfo(FString::Printf(TEXT("resolved pawn %s"), *Gasp->GetClass()->GetPathName()));
				UGolmokAnimationSubsystem* Anim = World->GetSubsystem<UGolmokAnimationSubsystem>();
				FString Message;
				if (!Anim || !Anim->ApplyPreview(true, Message))
				{
					return Fail(FString::Printf(TEXT("golmok.anim preview failed: %s"), *Message));
				}
				Test->AddInfo(Message);
				Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones; // -nullrhi bones
				const FString AnimPath = Config.AssetPath(Config.AnimClass);
				UAnimInstance* Instance = Mesh->GetAnimInstance();
				bool bGaspAnim = false;
				for (const UClass* Class = Instance ? Instance->GetClass() : nullptr; Class; Class = Class->GetSuperClass())
				{
					bGaspAnim |= Class->GetPathName() == AnimPath;
				}
				Test->TestTrue(TEXT("anim class is gasp.anim_class"), bGaspAnim);
				for (const TCHAR* Bone : {TEXT("foot_l"), TEXT("foot_r"), TEXT("ball_l"), TEXT("ball_r")})
				{
					if (!Test->TestTrue(FString::Printf(TEXT("bone %s exists"), Bone), Mesh->GetBoneIndex(FName(Bone)) != INDEX_NONE))
					{
						return true;
					}
					Feet.Add({FName(Bone)});
				}
				ResetAt(OpenFloorX, OpenFloorY);
				return Next(Settle, Now);
			}

			case Settle:
				if (Elapsed < 1.0 || Gasp->GetCharacterMovement()->IsFalling())
				{
					return Fail(TEXT("GASP pawn did not settle"), 5.0, Elapsed);
				}
				Press(EKeys::W);
				StartSegment();
				return Next(Walk, Now);

			case Walk:
				Sample(Mesh, Component);
				if (Elapsed < 3.0)
				{
					return false;
				}
				FinishSegment(TEXT("walk 3 s"), EGolmokGait::Walk);
				Press(EKeys::LeftShift);
				StartSegment();
				return Next(Run, Now);

			case Run:
				Sample(Mesh, Component);
				if (Elapsed < 3.0)
				{
					return false;
				}
				FinishSegment(TEXT("run 3 s"), EGolmokGait::Run);
				Release(EKeys::LeftShift);
				Release(EKeys::W);
				return Next(Done, Now);

			case Done:
			default:
				return true;
			}
		}

	private:
		void StartSegment()
		{
			for (FFootTrack& Foot : Feet)
			{
				Foot.Samples.Reset();
				Foot.Min = FVector(UE_BIG_NUMBER);
				Foot.Max = FVector(-UE_BIG_NUMBER);
			}
			CapsuleTravel = 0.0;
			GaitSeen[0] = GaitSeen[1] = GaitSamples = 0;
			bHasLast = false;
		}

		void Sample(USkeletalMeshComponent* Mesh, const UGolmokLocomotionStateComponent* Component)
		{
			const FVector Capsule = Character->GetActorLocation();
			const bool bOnGround = Character->GetCharacterMovement()->IsMovingOnGround();
			if (bHasLast)
			{
				CapsuleTravel += FVector::Dist2D(Capsule, LastCapsule);
			}
			LastCapsule = Capsule;
			bHasLast = true;
			for (FFootTrack& Foot : Feet)
			{
				const FVector P = Mesh->GetBoneLocation(Foot.Bone, EBoneSpaces::WorldSpace);
				Foot.Samples.Add({P.X, P.Y, P.Z, bOnGround});
				Foot.Min = Foot.Min.ComponentMin(P);
				Foot.Max = Foot.Max.ComponentMax(P);
			}
			++GaitSamples;
			if (Component)
			{
				GaitSeen[Component->GetGait() == EGolmokGait::Run ? 1 : 0] += 1;
			}
		}

		void FinishSegment(const TCHAR* What, EGolmokGait Expected)
		{
			double Planted = 0.0;
			for (const FFootTrack& Foot : Feet)
			{
				const double Travel = GolmokLocomotionMath::PlantedTravelCm(Foot.Samples.GetData(), Foot.Samples.Num());
				const double Range = (Foot.Max - Foot.Min).Size();
				Test->AddInfo(FString::Printf(TEXT("%s %s: planted travel %.1f cm, range %.1f cm, %d samples"), What, *Foot.Bone.ToString(), Travel, Range,
					Foot.Samples.Num()));
				Test->TestTrue(FString::Printf(TEXT("%s: %s moves"), What, *Foot.Bone.ToString()), Range > 10.0);
				if (Foot.Bone == FName(TEXT("foot_l")) || Foot.Bone == FName(TEXT("foot_r")))
				{
					Planted += Travel;
				}
			}
			// A pawn that did not move would pass the slip test with 0: require >= 80 % of 3 s at the gait speed.
			const double MinTravel = 0.8 * 3.0 * (Expected == EGolmokGait::Run ? RunCmS : WalkCmS);
			Test->TestTrue(FString::Printf(TEXT("%s: capsule travelled %.0f cm (>= %.0f)"), What, CapsuleTravel, MinTravel), CapsuleTravel >= MinTravel);
			const double Slip = GolmokLocomotionMath::PlantedSlipCmPerM(Planted, CapsuleTravel);
			Test->AddInfo(FString::Printf(TEXT("%s: PlantedSlip %.1f cm/m over %.1f m (V-08: ① 8-21, ②a 81-100)"), What, Slip, CapsuleTravel / 100.0));
			Test->TestTrue(FString::Printf(TEXT("%s: PlantedSlip <= 30 cm/m"), What), Slip <= 30.0);
			Test->TestTrue(FString::Printf(TEXT("%s: state reports %s"), What, Expected == EGolmokGait::Run ? TEXT("Run") : TEXT("Walk")),
				GaitSamples > 0 && GaitSeen[Expected == EGolmokGait::Run ? 1 : 0] * 2 > GaitSamples);
		}

		TSharedPtr<GolmokAnimation::FScopedConfigOverride> Override;
		GolmokAnimation::FConfig Config;
		TArray<FFootTrack> Feet;
		double CapsuleTravel = 0.0;
		FVector LastCapsule = FVector::ZeroVector;
		bool bHasLast = false;
		int32 GaitSeen[2] = {0, 0}; // samples reporting Walk / Run (a missing component counts for neither)
		int32 GaitSamples = 0;
	};
}

// ---- Golmok.Animation.Config ---------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokAnimationConfigTest, "Golmok.Animation.Config",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokAnimationConfigTest::RunTest(const FString& Parameters)
{
	using namespace GolmokAnimationTest;
	using GolmokAnimation::EMode;

	// The committed file: mode abp (D-021: main stays ① before V-15), p0 = the constructor + engine defaults.
	{
		FString Text;
		GolmokAnimation::FConfig Config;
		FString Error;
		TestTrue(TEXT("Config/Golmok/animation.json readable"), FFileHelper::LoadFileToString(Text, *GolmokAnimation::ConfigFilePath()));
		if (TestTrue(TEXT("committed animation.json parses"), GolmokAnimation::ParseConfig(Text, Config, Error)))
		{
			TestTrue(TEXT("committed mode is abp"), Config.Mode == EMode::Abp);
			TestNotNull(TEXT("selected movement_profile is defined"), Config.FindProfile(Config.MovementProfileId));
			const GolmokAnimation::FMovementProfile* P0 = Config.FindProfile(TEXT("p0"));
			if (TestNotNull(TEXT("p0 defined"), P0))
			{
				TestTrue(TEXT("p0 = 2048 / 2000 / 8 / 2 / false / 0"), P0->MaxAcceleration == 2048.0 && P0->BrakingDecelerationWalking == 2000.0
					&& P0->GroundFriction == 8.0 && P0->BrakingFrictionFactor == 2.0 && !P0->bUseSeparateBrakingFriction && P0->BrakingFriction == 0.0);
			}
			// p1 / p2 are null until 19b fills them (V-08b); the parser already range-checked any defined profile.
			TestEqual(TEXT("three profiles p0 / p1 / p2"), Config.Profiles.Num(), 3);
			TestTrue(TEXT("p1 and p2 are declared"), Config.Profiles.ContainsByPredicate([](const GolmokAnimation::FNamedProfile& P) { return P.Id == TEXT("p1"); })
				&& Config.Profiles.ContainsByPredicate([](const GolmokAnimation::FNamedProfile& P) { return P.Id == TEXT("p2"); }));
			TestEqual(TEXT("asset path joins content_root"), Config.AssetPath(Config.AnimClass), Config.ContentRoot + TEXT("/") + Config.AnimClass);
		}
		else
		{
			AddError(Error);
		}
	}

	// All-or-nothing: every broken variant fails and leaves the output untouched.
	{
		GolmokAnimation::FConfig Base;
		FString Error;
		TestTrue(TEXT("test base config parses"), GolmokAnimation::ParseConfig(BaseConfig, Base, Error));
		struct FCase { const TCHAR* Name; FString Text; };
		const FCase Cases[] = {
			{TEXT("schema_version 2"), Variant(TEXT("\"schema_version\": 1"), TEXT("\"schema_version\": 2"))},
			{TEXT("missing mode"), Variant(TEXT("\"mode\": \"abp\",\n"), TEXT(""))},
			{TEXT("extra root key"), Variant(TEXT("\"schema_version\": 1,"), TEXT("\"schema_version\": 1, \"extra\": 1,"))},
			{TEXT("extra gasp key"), Variant(TEXT("\"content_root\": \"/Game/GASP\","), TEXT("\"content_root\": \"/Game/GASP\", \"x\": 1,"))},
			{TEXT("missing state key"), Variant(TEXT("\"reinit_anim_on_teleport\": true"), TEXT("\"reinit\": true"))},
			{TEXT("mode motion"), Variant(TEXT("\"mode\": \"abp\""), TEXT("\"mode\": \"motion\""))},
			{TEXT("mode ABP (the file is exact, like the pytest schema)"), Variant(TEXT("\"mode\": \"abp\""), TEXT("\"mode\": \"ABP\""))},
			{TEXT("pawn_class without _C"), Variant(TEXT("BP_GolmokCharacter_GASP.BP_GolmokCharacter_GASP_C\""), TEXT("BP_GolmokCharacter_GASP.BP_GolmokCharacter_GASP\""))},
			{TEXT("pawn_class outside /Game"), Variant(TEXT("\"/Game/GolmokLocal/GASP/"), TEXT("\"/Engine/GolmokLocal/GASP/"))},
			{TEXT("anim_class absolute"), Variant(TEXT("\"anim_class\": \"Blueprints/"), TEXT("\"anim_class\": \"/Blueprints/"))},
			{TEXT("path with a space"), Variant(TEXT("Blueprints/Interfaces/"), TEXT("Blueprints/Inter faces/"))},
			{TEXT("content_root /Game/Other"), Variant(TEXT("\"content_root\": \"/Game/GASP\""), TEXT("\"content_root\": \"/Game/Other\""))},
			{TEXT("max_acceleration 99"), Variant(TEXT("\"max_acceleration\": 2048"), TEXT("\"max_acceleration\": 99"))},
			{TEXT("ground_friction 21"), Variant(TEXT("\"ground_friction\": 8"), TEXT("\"ground_friction\": 21"))},
			{TEXT("braking flag as number"), Variant(TEXT("\"use_separate_braking_friction\": false"), TEXT("\"use_separate_braking_friction\": 0"))},
			{TEXT("just_landed_seconds 3"), Variant(TEXT("\"just_landed_seconds\": 0.3"), TEXT("\"just_landed_seconds\": 3"))},
			{TEXT("teleport_jump_cm 5"), Variant(TEXT("\"teleport_jump_cm\": 100"), TEXT("\"teleport_jump_cm\": 5"))},
			{TEXT("null profile selected"), Variant(TEXT("\"movement_profile\": \"p0\""), TEXT("\"movement_profile\": \"p1\""))},
			{TEXT("unknown profile selected"), Variant(TEXT("\"movement_profile\": \"p0\""), TEXT("\"movement_profile\": \"p9\""))},
			{TEXT("visual mesh without anim"), Variant(TEXT("\"visual_mesh\": null"), TEXT("\"visual_mesh\": \"Characters/X/SKM_X.SKM_X\""))},
			{TEXT("not JSON"), FString(TEXT("{"))},
		};
		for (const FCase& Case : Cases)
		{
			TestTrue(*FString::Printf(TEXT("%s: variant differs from the base"), Case.Name), Case.Text != FString(BaseConfig));
			GolmokAnimation::FConfig Out = Base;
			Out.PawnClass = TEXT("sentinel");
			FString CaseError;
			TestFalse(*FString::Printf(TEXT("%s is rejected"), Case.Name), GolmokAnimation::ParseConfig(Case.Text, Out, CaseError));
			TestTrue(*FString::Printf(TEXT("%s: output unchanged"), Case.Name), Out.PawnClass == TEXT("sentinel") && Out.Mode == Base.Mode);
			TestTrue(*FString::Printf(TEXT("%s: error names the file"), Case.Name), CaseError.StartsWith(TEXT("animation.json: ")));
		}
		GolmokAnimation::FConfig Visual;
		TestTrue(TEXT("both visual fields set (absolute /Game) parse"), GolmokAnimation::ParseConfig(
			Variant(TEXT("\"visual_mesh\": null, \"visual_anim_class\": null"),
				TEXT("\"visual_mesh\": \"/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple\", \"visual_anim_class\": \"Characters/UE5_Mannequins/Rigs/RTG_Retarget.RTG_Retarget_C\"")),
			Visual, Error));
		TestEqual(TEXT("absolute visual path kept"), Visual.AssetPath(Visual.PreviewVisualMesh),
			FString(TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple")));
		GolmokAnimation::FConfig Root;
		TestTrue(TEXT("content_root /Game parses"), GolmokAnimation::ParseConfig(
			Variant(TEXT("\"content_root\": \"/Game/GASP\""), TEXT("\"content_root\": \"/Game\"")), Root, Error));
		TestEqual(TEXT("content_root /Game joins without GASP"), Root.AssetPath(Root.AnimClass),
			FString(TEXT("/Game/Blueprints/SandboxCharacter_CMC_ABP.SandboxCharacter_CMC_ABP_C")));
	}

	// Release -> Idle hysteresis (PIE brakes through 10..3 cm/s within a frame, so check the rule itself).
	TestTrue(TEXT("hysteresis: braking at 5 cm/s without intent stays Moving"), GolmokLocomotionMath::UpdateMoving(
		GolmokLocomotionMath::MovingState::Moving, 5.0, 0.0) == GolmokLocomotionMath::MovingState::Moving);
	TestTrue(TEXT("hysteresis: below 3 cm/s without intent is Idle"), GolmokLocomotionMath::UpdateMoving(
		GolmokLocomotionMath::MovingState::Moving, 2.0, 0.0) == GolmokLocomotionMath::MovingState::Idle);

	// Effective mode priority: command line > console > animation.json.
	{
		using GolmokAnimation::ComputeEffectiveMode;
		const auto M = ComputeEffectiveMode(TEXT("-GolmokAnim=gasp"), TOptional<EMode>(EMode::Abp), true, EMode::Abp);
		TestTrue(TEXT("command line wins"), M.Mode == EMode::Gasp && M.Source == TEXT("command line"));
		const auto C = ComputeEffectiveMode(TEXT("-log"), TOptional<EMode>(EMode::Gasp), true, EMode::Abp);
		TestTrue(TEXT("console beats the file"), C.Mode == EMode::Gasp && C.Source == TEXT("console"));
		const auto F = ComputeEffectiveMode(TEXT(""), TOptional<EMode>(), true, EMode::Gasp);
		TestTrue(TEXT("file mode without overrides"), F.Mode == EMode::Gasp && F.Source == TEXT("animation.json"));
		const auto B = ComputeEffectiveMode(TEXT("-GolmokAnim=bogus"), TOptional<EMode>(EMode::Abp), true, EMode::Gasp);
		TestTrue(TEXT("invalid command line value is ignored"), B.Mode == EMode::Abp && B.Source == TEXT("console"));
		TestEqual(TEXT("invalid command line value is reported (Warning once)"), B.InvalidCommandLineValue, FString(TEXT("bogus")));
		const auto U = ComputeEffectiveMode(TEXT("-GolmokAnim=GASP"), TOptional<EMode>(), true, EMode::Abp);
		TestTrue(TEXT("command line mode ignores case"), U.Mode == EMode::Gasp && U.Source == TEXT("command line") && U.InvalidCommandLineValue.IsEmpty());
		EMode Argument = EMode::Abp;
		TestTrue(TEXT("console mode argument ignores case and spaces"), GolmokAnimation::ParseModeArgument(TEXT(" Gasp "), Argument) && Argument == EMode::Gasp);
		TestFalse(TEXT("console mode argument rejects other words"), GolmokAnimation::ParseModeArgument(TEXT("motion"), Argument));
		const auto I = ComputeEffectiveMode(nullptr, TOptional<EMode>(), false, EMode::Gasp);
		TestTrue(TEXT("invalid config reads as abp"), I.Mode == EMode::Abp && I.Source == TEXT("animation.json invalid"));

		const TOptional<EMode> SavedConsole = GolmokAnimation::GetConsoleModeOverride();
		GolmokAnimation::SetConsoleModeOverride(TOptional<EMode>(EMode::Abp));
		{
			GolmokAnimation::FScopedConfigOverride Scoped(GaspModeConfig(TEXT("/Game/GolmokLocal/GASP/BP_Missing.BP_Missing_C")));
			const auto Isolated = GolmokAnimation::GetEffectiveMode();
			TestTrue(TEXT("scoped override isolates the console / command line"), Isolated.Mode == EMode::Gasp && Isolated.Source == TEXT("animation.json"));
		}
		GolmokAnimation::SetConsoleModeOverride(SavedConsole);
	}

	// Pawn resolution rules 1-5 (6 needs the 19b Blueprint: Golmok.Animation.GaspSmoke).
	{
		UClass* SuperClass = AGolmokCharacter::StaticClass();
		{
			GolmokAnimation::FScopedConfigOverride Scoped(BaseConfig);
			const auto R = GolmokAnimation::ResolvePawn(true, SuperClass);
			TestTrue(TEXT("rule 1: mode abp -> SuperClass, no fallback"), R.PawnClass == SuperClass && !R.bFallback);
		}
		{
			GolmokAnimation::FScopedConfigOverride Scoped(GaspModeConfig(TEXT("/Game/GolmokLocal/GASP/BP_Missing.BP_Missing_C")));
			const auto NotPlayer = GolmokAnimation::ResolvePawn(false, SuperClass);
			TestTrue(TEXT("rule 1: not a player controller -> SuperClass, no fallback"), NotPlayer.PawnClass == SuperClass && !NotPlayer.bFallback);
			const auto Missing = GolmokAnimation::ResolvePawn(true, SuperClass);
			TestTrue(TEXT("rule 3: missing pawn_class -> ①"), Missing.PawnClass == SuperClass && Missing.bFallback);
			TestEqual(TEXT("rule 3 reason"), Missing.Reason,
				FString(TEXT("GASP pawn class missing — add-gasp / 19b (/Game/GolmokLocal/GASP/BP_Missing.BP_Missing_C)")));
		}
		{
			GolmokAnimation::FScopedConfigOverride Scoped(TEXT("{"));
			const auto Broken = GolmokAnimation::ResolvePawn(true, SuperClass);
			TestTrue(TEXT("rule 2: parse failure -> ① with the parser error"), Broken.PawnClass == SuperClass && Broken.bFallback
				&& Broken.Reason.StartsWith(TEXT("animation.json: ")));
		}
		{
			GolmokAnimation::FScopedConfigOverride Scoped(GaspModeConfig(TEXT("/Script/Golmok.GolmokCharacter")));
			const auto NotGasp = GolmokAnimation::ResolvePawn(true, SuperClass);
			TestTrue(TEXT("rule 4: AGolmokCharacter is not a GASP pawn -> ①"), NotGasp.PawnClass == SuperClass && NotGasp.bFallback);
			TestEqual(TEXT("rule 4 reason"), NotGasp.Reason, FString(TEXT("pawn class /Script/Golmok.GolmokCharacter is not an AGolmokGaspCharacter")));
		}
		{
			// A BPI path that never exists: the same reason on a PC where add-gasp installed the real one.
			GolmokAnimation::FScopedConfigOverride Scoped(GaspModeConfig(TEXT("/Script/Golmok.GolmokGaspCharacter")).Replace(
				TEXT("Interfaces/BPI_SandboxCharacter_Pawn.BPI_SandboxCharacter_Pawn_C"), TEXT("Interfaces/BPI_Missing.BPI_Missing_C"),
				ESearchCase::CaseSensitive));
			const auto NoInterface = GolmokAnimation::ResolvePawn(true, SuperClass);
			TestTrue(TEXT("rule 5: native pawn without the GASP interface -> ①"), NoInterface.PawnClass == SuperClass && NoInterface.bFallback);
			TestEqual(TEXT("rule 5 reason"), NoInterface.Reason, FString(TEXT(
				"GASP pawn interface missing (/Game/GASP/Blueprints/Interfaces/BPI_Missing.BPI_Missing_C)")));
			TestFalse(TEXT("PawnSupportsGasp(native CDO) is false"), GolmokAnimation::PawnSupportsGasp(GetDefault<AGolmokGaspCharacter>()));
		}
		TestFalse(TEXT("RequiresGaspPawn(nullptr)"), GolmokAnimation::RequiresGaspPawn(nullptr));
		TestFalse(TEXT("RequiresGaspPawn(UAnimInstance)"), GolmokAnimation::RequiresGaspPawn(UAnimInstance::StaticClass()));
	}

	// Local DDCvars: parsing (3 types, DDCvar / DDCVar spellings) and "only names that do not exist yet".
	{
		const FString Good = TEXT(R"JSON({"schema_version": 1, "source": "test", "cvars": [
			{"name": "Golmok.Test.AnimDDCvarInt", "type": "int", "default": 2, "help": "int"},
			{"name": "Golmok.Test.AnimDDCVarFloat", "type": "float", "default": 0.5, "help": ""},
			{"name": "Golmok.Test.AnimDDCvarBool", "type": "bool", "default": true, "help": "bool"}]})JSON");
		TArray<GolmokAnimation::FDDCvar> Vars;
		FString Error;
		if (TestTrue(TEXT("DDCvar file parses"), GolmokAnimation::ParseDDCvars(Good, Vars, Error)) && TestEqual(TEXT("three DDCvars"), Vars.Num(), 3))
		{
			int32 Present = 0;
			TestEqual(TEXT("first registration adds all"), GolmokAnimation::RegisterDDCvars(Vars, Present), 3);
			TestEqual(TEXT("all present"), Present, 3);
			TestEqual(TEXT("second registration skips existing names"), GolmokAnimation::RegisterDDCvars(Vars, Present), 0);
			IConsoleVariable* IntVar = IConsoleManager::Get().FindConsoleVariable(TEXT("Golmok.Test.AnimDDCvarInt"));
			TestTrue(TEXT("int default"), IntVar && IntVar->GetInt() == 2);
			IConsoleVariable* BoolVar = IConsoleManager::Get().FindConsoleVariable(TEXT("Golmok.Test.AnimDDCvarBool"));
			TestTrue(TEXT("bool default"), BoolVar && BoolVar->GetBool());
			for (const GolmokAnimation::FDDCvar& Var : Vars)
			{
				if (IConsoleObject* Object = IConsoleManager::Get().FindConsoleObject(*Var.Name))
				{
					IConsoleManager::Get().UnregisterConsoleObject(Object, false);
				}
			}
		}
		TArray<GolmokAnimation::FDDCvar> Untouched;
		for (const TCHAR* Bad : {TEXT("{\"schema_version\": 1, \"source\": \"x\", \"cvars\": [{\"name\": \"A\", \"type\": \"string\", \"default\": \"x\", \"help\": \"\"}]}"),
				TEXT("{\"schema_version\": 1, \"source\": \"x\", \"cvars\": [{\"name\": \"A\", \"type\": \"bool\", \"default\": 1, \"help\": \"\"}]}"),
				TEXT("{\"schema_version\": 1, \"source\": \"x\", \"cvars\": [{\"name\": \"A B\", \"type\": \"int\", \"default\": 1, \"help\": \"\"}]}"),
				TEXT("{\"schema_version\": 1, \"source\": \"x\", \"cvars\": [{\"name\": \"A\", \"type\": \"int\", \"default\": 1, \"help\": \"\"}, {\"name\": \"a\", \"type\": \"int\", \"default\": 1, \"help\": \"\"}]}"),
				TEXT("{\"schema_version\": 2, \"source\": \"x\", \"cvars\": []}")})
		{
			TestFalse(*FString::Printf(TEXT("bad DDCvar file rejected: %s"), Bad), GolmokAnimation::ParseDDCvars(Bad, Untouched, Error));
		}
		TestEqual(TEXT("bad DDCvar files leave the output untouched"), Untouched.Num(), 0);
	}
	return true;
}

// ---- Golmok.Animation.StateProvider --------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokAnimationStateProviderTest, "Golmok.Animation.StateProvider",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokAnimationStateProviderTest::RunTest(const FString& Parameters)
{
	using namespace GolmokAnimationTest;
	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddError(FString::Printf(TEXT("%s is missing. Run golmok.setup_dev_level in the editor first."), DevMap));
		return false;
	}
	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	// The committed file with mode abp and profile p0 (the test compares p0 with the ABP pawn), command line /
	// console override isolated: the default pawn is ①.
	FString Committed = CommittedConfigWith(TEXT("abp"), true);
	if (Committed.IsEmpty())
	{
		Committed = BaseConfig;
	}
	TSharedPtr<GolmokAnimation::FScopedConfigOverride> Override = MakeShared<GolmokAnimation::FScopedConfigOverride>(Committed);
	ADD_LATENT_AUTOMATION_COMMAND(FStateProviderScenario(this, Override));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

// ---- Golmok.Animation.Fallback -------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokAnimationFallbackTest, "Golmok.Animation.Fallback",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokAnimationFallbackTest::RunTest(const FString& Parameters)
{
	using namespace GolmokAnimationTest;
	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddError(FString::Printf(TEXT("%s is missing. Run golmok.setup_dev_level in the editor first."), DevMap));
		return false;
	}
	// Mode gasp with a pawn class that never exists: the same ① result on a PC with GASP installed.
	TSharedPtr<GolmokAnimation::FScopedConfigOverride> Override = MakeShared<GolmokAnimation::FScopedConfigOverride>(
		GaspModeConfig(TEXT("/Game/GolmokLocal/GASP/BP_Missing.BP_Missing_C")));
	AddExpectedMessagePlain(FallbackWarning, ELogVerbosity::Warning, EAutomationExpectedMessageFlags::Contains, 1);
	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FFallbackScenario(this, Override));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

// ---- Golmok.Animation.GaspSmoke ------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokAnimationGaspSmokeTest, "Golmok.Animation.GaspSmoke",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokAnimationGaspSmokeTest::RunTest(const FString& Parameters)
{
	using namespace GolmokAnimationTest;
	GolmokAnimation::FConfig Config;
	FString Error;
	const FString GaspText = CommittedConfigWith(TEXT("gasp"), false); // the profile 19b selected
	const bool bConfig = !GaspText.IsEmpty() && GolmokAnimation::ParseConfig(GaspText, Config, Error);
	const bool bManifest = FPaths::FileExists(GolmokAnimation::ManifestFilePath());
	UClass* Pawn = bConfig ? GolmokAnimation::LoadClassIfPresent(Config.PawnClass, nullptr) : nullptr; // wrong parent = error below
	FString Reason;
	if (!bConfig || !bManifest || !Pawn)
	{
		AddInfo(FString::Printf(TEXT("GASP not installed — skipped (config %s, manifest %s, pawn class %s)"), bConfig ? TEXT("ok") : *Error,
			bManifest ? TEXT("yes") : TEXT("no"), Pawn ? TEXT("loaded") : TEXT("missing")));
		return true;
	}
	if (!GolmokAnimation::PawnClassSupportsGasp(Config, Pawn, Reason))
	{
		AddError(FString::Printf(TEXT("GASP installed but the pawn Blueprint is not bound: %s"), *Reason));
		return false;
	}
	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddError(FString::Printf(TEXT("%s is missing. Run golmok.setup_dev_level in the editor first."), DevMap));
		return false;
	}
	AddInfo(TEXT("GASP installed: EXECUTED"));
	TSharedPtr<GolmokAnimation::FScopedConfigOverride> Override = MakeShared<GolmokAnimation::FScopedConfigOverride>(GaspText);
	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FGaspSmokeScenario(this, Override, Config));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

#endif
