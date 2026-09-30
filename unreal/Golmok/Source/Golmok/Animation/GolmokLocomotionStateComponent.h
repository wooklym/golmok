#pragma once

#include "CoreMinimal.h"
#include "Animation/GolmokLocomotionMath.h"
#include "Components/ActorComponent.h"
#include "Engine/EngineTypes.h"
#include "Engine/HitResult.h"
#include "GolmokLocomotionStateComponent.generated.h"

class ACharacter;

/** Our locomotion enums (design section 2); the 19b Blueprint maps them to the GASP ones by name, never by order. */
UENUM(BlueprintType)
enum class EGolmokMovementMode : uint8
{
	OnGround,
	InAir,
};

UENUM(BlueprintType)
enum class EGolmokGait : uint8
{
	Walk,
	Run,
};

/** Always Stand: no crouch (WP-19 design section 18). */
UENUM(BlueprintType)
enum class EGolmokStance : uint8
{
	Stand,
};

/** Always OrientToMovement: D-021 keeps turning toward movement and it is not configurable. */
UENUM(BlueprintType)
enum class EGolmokRotationMode : uint8
{
	OrientToMovement,
};

UENUM(BlueprintType)
enum class EGolmokMovingState : uint8
{
	Idle,
	Moving,
};

UENUM(BlueprintType)
enum class EGolmokFootEvent : uint8
{
	Step,
	Land,
};

/** One tick of locomotion state, computed once in TG_PrePhysics after the CharacterMovementComponent. */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokLocomotionState
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Golmok|Locomotion")
	EGolmokMovementMode MovementMode = EGolmokMovementMode::OnGround;

	UPROPERTY(BlueprintReadOnly, Category = "Golmok|Locomotion")
	EGolmokGait Gait = EGolmokGait::Walk;

	UPROPERTY(BlueprintReadOnly, Category = "Golmok|Locomotion")
	EGolmokStance Stance = EGolmokStance::Stand;

	UPROPERTY(BlueprintReadOnly, Category = "Golmok|Locomotion")
	EGolmokRotationMode RotationMode = EGolmokRotationMode::OrientToMovement;

	UPROPERTY(BlueprintReadOnly, Category = "Golmok|Locomotion")
	EGolmokMovingState MovingState = EGolmokMovingState::Idle;

	/** Horizontal acceleration / max acceleration (length <= 1, analog size kept; 0 below the dead zone). Z = 0. */
	UPROPERTY(BlueprintReadOnly, Category = "Golmok|Locomotion")
	FVector InputIntent = FVector::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "Golmok|Locomotion")
	FVector Acceleration = FVector::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "Golmok|Locomotion")
	FVector Velocity = FVector::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "Golmok|Locomotion")
	float Speed2D = 0.f;

	/** True for gasp.state.just_landed_seconds after landing (a new jump or fall ends it early). */
	UPROPERTY(BlueprintReadOnly, Category = "Golmok|Locomotion")
	bool bJustLanded = false;

	/** Velocity at the last landing (Z < 0). */
	UPROPERTY(BlueprintReadOnly, Category = "Golmok|Locomotion")
	FVector LandVelocity = FVector::ZeroVector;

	/** The capsule jumped further than speed x dt + gasp.state.teleport_jump_cm this tick (portal, travel, load). */
	UPROPERTY(BlueprintReadOnly, Category = "Golmok|Locomotion")
	bool bTeleportedThisFrame = false;
};

DECLARE_MULTICAST_DELEGATE_TwoParams(FGolmokFootEventDelegate, EGolmokFootEvent /*Kind*/, bool /*bLeft*/);

/**
 * WP-19 design section 3: the locomotion state the GASP animation Blueprint reads through the 19b pawn interface
 * Blueprint. Ticks in TG_PrePhysics after the owner's CharacterMovementComponent and before its mesh, computes
 * FGolmokLocomotionState with GolmokLocomotionMath and caches it; every getter only copies the cache (safe from
 * the animation Blueprint's thread-safe update). Landing and movement-mode changes come from ACharacter's
 * LandedDelegate / MovementModeChangedDelegate (bound in OnRegister, unbound in OnUnregister). A teleport sets
 * bTeleportedThisFrame and, with gasp.state.reinit_anim_on_teleport, calls GetMesh()->InitAnim(true) on the next
 * tick. Foot events from the 19b Blueprint (GASP foley notify path) are re-broadcast on OnFootEvent (19c T13).
 */
UCLASS(ClassGroup = (Golmok), meta = (BlueprintSpawnableComponent))
class GOLMOK_API UGolmokLocomotionStateComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGolmokLocomotionStateComponent();

	virtual void OnRegister() override;
	virtual void OnUnregister() override;
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	UFUNCTION(BlueprintPure, Category = "Golmok|Locomotion", meta = (BlueprintThreadSafe))
	FGolmokLocomotionState GetLocomotionState() const { return State; }

	UFUNCTION(BlueprintPure, Category = "Golmok|Locomotion", meta = (BlueprintThreadSafe))
	EGolmokMovementMode GetMovementMode() const { return State.MovementMode; }

	UFUNCTION(BlueprintPure, Category = "Golmok|Locomotion", meta = (BlueprintThreadSafe))
	EGolmokGait GetGait() const { return State.Gait; }

	UFUNCTION(BlueprintPure, Category = "Golmok|Locomotion", meta = (BlueprintThreadSafe))
	EGolmokStance GetStance() const { return State.Stance; }

	UFUNCTION(BlueprintPure, Category = "Golmok|Locomotion", meta = (BlueprintThreadSafe))
	EGolmokRotationMode GetRotationMode() const { return State.RotationMode; }

	UFUNCTION(BlueprintPure, Category = "Golmok|Locomotion", meta = (BlueprintThreadSafe))
	EGolmokMovingState GetMovingState() const { return State.MovingState; }

	UFUNCTION(BlueprintPure, Category = "Golmok|Locomotion", meta = (BlueprintThreadSafe))
	FVector GetInputIntent() const { return State.InputIntent; }

	UFUNCTION(BlueprintPure, Category = "Golmok|Locomotion", meta = (BlueprintThreadSafe))
	FVector GetLocomotionAcceleration() const { return State.Acceleration; }

	UFUNCTION(BlueprintPure, Category = "Golmok|Locomotion", meta = (BlueprintThreadSafe))
	FVector GetLocomotionVelocity() const { return State.Velocity; }

	UFUNCTION(BlueprintPure, Category = "Golmok|Locomotion", meta = (BlueprintThreadSafe))
	float GetSpeed2D() const { return State.Speed2D; }

	UFUNCTION(BlueprintPure, Category = "Golmok|Locomotion", meta = (BlueprintThreadSafe))
	bool IsJustLanded() const { return State.bJustLanded; }

	UFUNCTION(BlueprintPure, Category = "Golmok|Locomotion", meta = (BlueprintThreadSafe))
	FVector GetLandVelocity() const { return State.LandVelocity; }

	UFUNCTION(BlueprintPure, Category = "Golmok|Locomotion", meta = (BlueprintThreadSafe))
	bool WasTeleportedThisFrame() const { return State.bTeleportedThisFrame; }

	/** Called by the 19b Blueprint from the GASP foley notify path; broadcasts OnFootEvent. */
	UFUNCTION(BlueprintCallable, Category = "Golmok|Locomotion")
	void NotifyFootEvent(EGolmokFootEvent Kind, bool bLeft);

	/** Native foot events (19c T13 subscribes; no subscriber = no behaviour change). */
	FGolmokFootEventDelegate OnFootEvent;

	/** animation.json gasp.state (AGolmokGaspCharacter::PostInitializeComponents). Out-of-range values are ignored. */
	void ApplySettings(double InJustLandedSeconds, double InTeleportJumpCm, bool bInReinitAnimOnTeleport);

	/** Seconds since the last landing in world time, -1 before the first one (HUD "land" column). */
	double GetSecondsSinceLanding() const;
	int32 GetFootEventCount() const { return FootEventCount; }
	int32 GetAnimReinitCount() const { return AnimReinitCount; }
	int32 GetTeleportCount() const { return TeleportCount; }
	double GetJustLandedSeconds() const { return JustLandedSeconds; }

private:
	UFUNCTION()
	void HandleLanded(const FHitResult& Hit);

	UFUNCTION()
	void HandleMovementModeChanged(ACharacter* InCharacter, EMovementMode PrevMovementMode, uint8 PreviousCustomMode);

	FGolmokLocomotionState State;
	GolmokLocomotionMath::LandingWindow Landing;
	TWeakObjectPtr<ACharacter> BoundCharacter;
	FVector PreviousLocation = FVector::ZeroVector;
	double PreviousSpeed2D = 0.0;
	bool bHasPrevious = false;
	bool bReinitPending = false;
	double JustLandedSeconds = GolmokLocomotionMath::DefaultJustLandedSeconds;
	double TeleportJumpCm = GolmokLocomotionMath::DefaultTeleportSlackCm;
	bool bReinitAnimOnTeleport = true;
	int32 FootEventCount = 0;
	int32 AnimReinitCount = 0;
	int32 TeleportCount = 0;
};
