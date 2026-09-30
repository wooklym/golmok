#include "Animation/GolmokLocomotionStateComponent.h"

#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Player/GolmokCharacter.h"

namespace GolmokAnimation
{
	EGolmokMovementMode ToMovementModeEnum(GolmokLocomotionMath::MovementMode Mode)
	{
		return Mode == GolmokLocomotionMath::MovementMode::InAir ? EGolmokMovementMode::InAir : EGolmokMovementMode::OnGround;
	}

	EGolmokGait ToGaitEnum(GolmokLocomotionMath::Gait Gait)
	{
		return Gait == GolmokLocomotionMath::Gait::Run ? EGolmokGait::Run : EGolmokGait::Walk;
	}

	EGolmokMovingState ToMovingStateEnum(GolmokLocomotionMath::MovingState Moving)
	{
		return Moving == GolmokLocomotionMath::MovingState::Moving ? EGolmokMovingState::Moving : EGolmokMovingState::Idle;
	}

	GolmokLocomotionMath::MovingState FromMovingStateEnum(EGolmokMovingState Moving)
	{
		return Moving == EGolmokMovingState::Moving ? GolmokLocomotionMath::MovingState::Moving : GolmokLocomotionMath::MovingState::Idle;
	}
}

UGolmokLocomotionStateComponent::UGolmokLocomotionStateComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = true;
	PrimaryComponentTick.TickGroup = TG_PrePhysics;
	bAutoActivate = true;
}

void UGolmokLocomotionStateComponent::OnRegister()
{
	Super::OnRegister();
	ACharacter* Character = Cast<ACharacter>(GetOwner());
	if (!Character)
	{
		return;
	}
	BoundCharacter = Character;
	Character->LandedDelegate.AddUniqueDynamic(this, &UGolmokLocomotionStateComponent::HandleLanded);
	Character->MovementModeChangedDelegate.AddUniqueDynamic(this, &UGolmokLocomotionStateComponent::HandleMovementModeChanged);
	// Movement -> this state -> animation: the state is read by the mesh's anim update in the same frame.
	if (UCharacterMovementComponent* Movement = Character->GetCharacterMovement())
	{
		AddTickPrerequisiteComponent(Movement);
	}
	if (USkeletalMeshComponent* Mesh = Character->GetMesh())
	{
		Mesh->AddTickPrerequisiteComponent(this);
	}
	bHasPrevious = false;
	bReinitPending = false;
	bLandingPending = false;
}

void UGolmokLocomotionStateComponent::OnUnregister()
{
	if (ACharacter* Character = BoundCharacter.Get())
	{
		Character->LandedDelegate.RemoveDynamic(this, &UGolmokLocomotionStateComponent::HandleLanded);
		Character->MovementModeChangedDelegate.RemoveDynamic(this, &UGolmokLocomotionStateComponent::HandleMovementModeChanged);
		if (UCharacterMovementComponent* Movement = Character->GetCharacterMovement())
		{
			RemoveTickPrerequisiteComponent(Movement);
		}
		if (USkeletalMeshComponent* Mesh = Character->GetMesh())
		{
			Mesh->RemoveTickPrerequisiteComponent(this);
		}
	}
	BoundCharacter.Reset();
	Super::OnUnregister();
}

void UGolmokLocomotionStateComponent::ApplySettings(double InJustLandedSeconds, double InTeleportJumpCm, bool bInReinitAnimOnTeleport)
{
	if (GolmokLocomotionMath::ValidateStateSettings(InJustLandedSeconds, InTeleportJumpCm))
	{
		JustLandedSeconds = InJustLandedSeconds;
		TeleportJumpCm = InTeleportJumpCm;
	}
	bReinitAnimOnTeleport = bInReinitAnimOnTeleport;
}

double UGolmokLocomotionStateComponent::GetSecondsSinceLanding() const
{
	const UWorld* World = GetWorld();
	return World ? Landing.SecondsSinceLanding(World->GetTimeSeconds()) : -1.0;
}

void UGolmokLocomotionStateComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	ACharacter* Character = BoundCharacter.Get();
	UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	const UWorld* World = GetWorld();
	if (!Movement || !World)
	{
		return;
	}

	// Detected on the previous tick: rebuild the anim instance so Offset Root Bone does not keep the old location.
	if (bReinitPending)
	{
		bReinitPending = false;
		if (USkeletalMeshComponent* Mesh = Character->GetMesh())
		{
			Mesh->InitAnim(true);
			++AnimReinitCount;
		}
	}

	const double Now = World->GetTimeSeconds();
	const FVector Location = Character->GetActorLocation();
	const FVector Velocity = Movement->Velocity;
	const FVector Acceleration = Movement->GetCurrentAcceleration();

	double Walk = Movement->MaxWalkSpeed;
	double Run = Walk; // not a Golmok character: always Walk
	if (const AGolmokCharacter* Golmok = Cast<AGolmokCharacter>(Character))
	{
		Walk = Golmok->GetWalkSpeed();
		Run = Golmok->GetRunSpeed();
	}

	FGolmokLocomotionState Next;
	Next.MovementMode = GolmokAnimation::ToMovementModeEnum(
		GolmokLocomotionMath::MapMovementMode(static_cast<int>(Movement->MovementMode.GetValue())));
	Next.Gait = GolmokAnimation::ToGaitEnum(GolmokLocomotionMath::ClassifyGait(Movement->MaxWalkSpeed, Walk, Run));
	Next.Stance = EGolmokStance::Stand;
	Next.RotationMode = EGolmokRotationMode::OrientToMovement;
	const std::array<double, 2> IntentXY = GolmokLocomotionMath::Intent(Acceleration.X, Acceleration.Y,
		Movement->GetMaxAcceleration(), GolmokLocomotionMath::IntentDeadzone);
	Next.InputIntent = FVector(IntentXY[0], IntentXY[1], 0.0);
	Next.Acceleration = Acceleration;
	Next.Velocity = Velocity;
	const double Speed2D = Velocity.Size2D();
	Next.Speed2D = static_cast<float>(Speed2D);
	Next.MovingState = GolmokAnimation::ToMovingStateEnum(GolmokLocomotionMath::UpdateMoving(
		GolmokAnimation::FromMovingStateEnum(State.MovingState), Speed2D, GolmokLocomotionMath::Length2(IntentXY)));
	Next.bJustLanded = Landing.IsJustLanded(Now, JustLandedSeconds);
	Next.LandVelocity = bLandingPending ? PendingLandVelocity : State.LandVelocity;
	bLandingPending = false;
	Next.bTeleportedThisFrame = bHasPrevious && GolmokLocomotionMath::IsTeleportJump(PreviousLocation.X, PreviousLocation.Y,
		Location.X, Location.Y, FMath::Max(PreviousSpeed2D, Speed2D), DeltaTime, TeleportJumpCm);
	if (Next.bTeleportedThisFrame)
	{
		++TeleportCount;
		bReinitPending = bReinitAnimOnTeleport;
	}

	PreviousLocation = Location;
	PreviousSpeed2D = Speed2D;
	bHasPrevious = true;
	State = Next;
}

void UGolmokLocomotionStateComponent::HandleLanded(const FHitResult& Hit)
{
	// LandedDelegate fires from ProcessLanded before the walking mode zeroes Velocity.Z (GASP reads it the same way).
	const ACharacter* Character = BoundCharacter.Get();
	const UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	const UWorld* World = GetWorld();
	if (!Movement || !World)
	{
		return;
	}
	Landing.OnLanded(Movement->Velocity.Z, World->GetTimeSeconds());
	PendingLandVelocity = Movement->Velocity; // applied by the next TickComponent (same frame: it ticks after the CMC)
	bLandingPending = true;
}

void UGolmokLocomotionStateComponent::HandleMovementModeChanged(ACharacter* InCharacter, EMovementMode PrevMovementMode, uint8 PreviousCustomMode)
{
	// A new jump or a fall ends the just-landed window at once.
	const UCharacterMovementComponent* Movement = InCharacter ? InCharacter->GetCharacterMovement() : nullptr;
	if (Movement && Movement->MovementMode == MOVE_Falling)
	{
		Landing.Clear();
	}
}

void UGolmokLocomotionStateComponent::NotifyFootEvent(EGolmokFootEvent Kind, bool bLeft)
{
	++FootEventCount;
	OnFootEvent.Broadcast(Kind, bLeft);
}
