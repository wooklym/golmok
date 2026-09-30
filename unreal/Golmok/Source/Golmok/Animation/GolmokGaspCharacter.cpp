#include "Animation/GolmokGaspCharacter.h"

#include "Golmok.h"
#include "Animation/AnimInstance.h"
#include "Animation/GolmokAnimationConfig.h"
#include "Animation/GolmokLocomotionStateComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/CharacterMovementComponent.h"

AGolmokGaspCharacter::AGolmokGaspCharacter()
{
	LocomotionState = CreateDefaultSubobject<UGolmokLocomotionStateComponent>(TEXT("LocomotionState"));

	VisualMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("VisualMesh"));
	VisualMesh->SetupAttachment(GetMesh());
	VisualMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	VisualMesh->SetGenerateOverlapEvents(false);
	VisualMesh->PrimaryComponentTick.bStartWithTickEnabled = false; // empty until SetVisualOverride
}

void AGolmokGaspCharacter::PostInitializeComponents()
{
	Super::PostInitializeComponents();

	GolmokAnimation::FConfig Config;
	FString Error;
	if (!GolmokAnimation::LoadConfig(Config, Error))
	{
		UE_LOG(LogGolmok, Warning, TEXT("anim: %s; %s keeps the AGolmokCharacter movement values"), *Error, *GetName());
		return;
	}
	if (const GolmokAnimation::FMovementProfile* Profile = Config.FindProfile(Config.MovementProfileId))
	{
		ApplyMovementProfile(Config.MovementProfileId, *Profile);
	}
	LocomotionState->ApplySettings(Config.JustLandedSeconds, Config.TeleportJumpCm, Config.bReinitAnimOnTeleport);
}

bool AGolmokGaspCharacter::ApplyMovementProfile(const FString& Id, const GolmokLocomotionMath::MovementProfile& Profile)
{
	if (!GolmokLocomotionMath::ValidateProfile(Profile))
	{
		return false;
	}
	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->MaxAcceleration = static_cast<float>(Profile.MaxAcceleration);
	Movement->BrakingDecelerationWalking = static_cast<float>(Profile.BrakingDecelerationWalking);
	Movement->GroundFriction = static_cast<float>(Profile.GroundFriction);
	Movement->BrakingFrictionFactor = static_cast<float>(Profile.BrakingFrictionFactor);
	Movement->bUseSeparateBrakingFriction = Profile.bUseSeparateBrakingFriction;
	Movement->BrakingFriction = static_cast<float>(Profile.BrakingFriction);
	AppliedProfileId = Id;
	return true;
}

bool AGolmokGaspCharacter::SetVisualOverride(USkeletalMesh* InMesh, TSubclassOf<UAnimInstance> InAnimClass, FString& OutError)
{
	if (!InMesh || !InAnimClass)
	{
		OutError = TEXT("visual override needs a skeletal mesh and an anim class");
		return false;
	}
	USkeletalMeshComponent* Source = GetMesh();
	if (!bVisualOverride)
	{
		SavedTickOption = static_cast<uint8>(Source->VisibilityBasedAnimTickOption);
	}
	VisualMesh->SetSkeletalMesh(InMesh);
	VisualMesh->SetAnimInstanceClass(InAnimClass);
	VisualMesh->SetHiddenInGame(false);
	VisualMesh->SetCastShadow(true);
	// The retarget pose is read from the source mesh: pose the source first.
	VisualMesh->AddTickPrerequisiteComponent(Source);
	VisualMesh->SetComponentTickEnabled(true);
	// Hidden from rendering only (children keep their own visibility); it still has to pose for the retarget.
	Source->SetHiddenInGame(true, /*bPropagateToChildren*/ false);
	Source->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	bVisualOverride = true;
	OutError.Reset();
	return true;
}

void AGolmokGaspCharacter::ClearVisualOverride()
{
	if (!bVisualOverride)
	{
		return;
	}
	USkeletalMeshComponent* Source = GetMesh();
	VisualMesh->SetAnimInstanceClass(nullptr);
	VisualMesh->SetSkeletalMesh(nullptr);
	VisualMesh->RemoveTickPrerequisiteComponent(Source);
	VisualMesh->SetComponentTickEnabled(false);
	Source->SetHiddenInGame(false, /*bPropagateToChildren*/ false);
	Source->VisibilityBasedAnimTickOption = static_cast<EVisibilityBasedAnimTickOption>(SavedTickOption);
	bVisualOverride = false;
}
