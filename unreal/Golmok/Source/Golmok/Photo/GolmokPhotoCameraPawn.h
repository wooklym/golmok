#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "GolmokPhotoCameraPawn.generated.h"

class UCameraComponent;
class UGolmokPhotoModeSubsystem;
class USphereComponent;

/**
 * Free camera of the photo mode (WP-12 design section 3-3 / 6). UGolmokPhotoModeSubsystem::Enter spawns one at the
 * current camera pose and makes it the view target WITHOUT possessing it (the character stays the controlled pawn,
 * so portal triggers and the zone subsystem never see a pawn change). The subsystem's input handlers write the raw
 * input (SetMoveInput / AddLookMouse / ...) and Tick consumes it; Tick runs while the game is paused
 * (bTickEvenWhenPaused) and measures time with FApp::GetDeltaTime() because the world clock stands still.
 *
 * The root is a small sweep sphere (CollisionRadiusCm): it blocks against WorldStatic / WorldDynamic geometry and
 * ignores pawns, camera probes and visibility traces, so the character capsule, the spring-arm probe and the portal
 * triggers (OverlapOnlyPawn) never interact with it. Every move goes through GolmokPhotoMath::Constrain (sphere around
 * the character, then the loaded zone footprint) and one blocking sweep (no slide, design section 6-3).
 *
 * Optics (FOV, exposure bias, DOF, motion blur, roll) live on the camera component only: destroying the pawn restores
 * everything (no post-process volume is touched).
 */
UCLASS(NotPlaceable, NotBlueprintable)
class GOLMOK_API AGolmokPhotoCameraPawn : public APawn
{
	GENERATED_BODY()

public:
	AGolmokPhotoCameraPawn();
	// PrimaryActorTick.bCanEverTick = bStartWithTickEnabled = bTickEvenWhenPaused = true; AutoPossessPlayer = Disabled.
	// Sphere (root): radius set in Init, QueryOnly, ObjectType ECC_WorldDynamic, all channels Ignore then WorldStatic / WorldDynamic Block
	//   (Pawn / Camera / Visibility Ignore), bGenerateOverlapEvents = false, hidden. Camera: attached to Sphere, bUsePawnControlRotation = false,
	//   PostProcessBlendWeight = 1. bFindCameraComponentWhenViewTarget stays true (view target without possession, design section 10 #17).

	/** Owner, start pose (roll starts at 0), FOV and sweep radius. Resets the input buffers and the tick counter. */
	void Init(UGolmokPhotoModeSubsystem* InOwner, const FVector& InLocation, const FRotator& InLookRotation, float InFov, float InRadiusCm);
	UCameraComponent* GetCamera() const { return Camera; }

	// raw input written by the subsystem's handlers; Tick consumes it. Ignored while Owner->IsCapturing().
	void SetMoveInput(const FVector2D& InLocal);
	void SetUpDownInput(float InAxis);
	void AddLookMouse(const FVector2D& InDelta);
	void SetLookPad(const FVector2D& InStick);
	void SetFast(bool bInFast);

	/** Pitch / yaw actor rotation (pitch clamped +-89), roll on the camera component only. */
	void ApplyLook(const FRotator& InLook);
	/** SetFieldOfView + PostProcessSettings overrides (design section 6-4): exposure bias, DOF (focal 0 when off), motion blur 0. */
	void ApplyOptics(float InFov, double InExposureBias, bool bInDof, double InFocusM, double InFstop);
	FRotator GetLook() const { return Look; }
	void SetRoll(float InRollDeg);

	/** One constraint + sweep step toward InDesired (public test hook; Tick calls it with Location + Velocity * dt). */
	void MoveConstrained(const FVector& InDesired);
	int32 GetTickCount() const { return TickCount; }
	/** dt = clamp(FApp::GetDeltaTime(), 0, 0.1) (design section 10 #2): DeltaSeconds may be 0 while paused. */
	virtual void Tick(float DeltaSeconds) override;
	/** Owner->OnPhotoPawnEndPlay(this, Reason): the subsystem decides between a normal Exit and a dead-world teardown. */
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	UPROPERTY(VisibleAnywhere, Category = "Golmok|Photo")
	TObjectPtr<USphereComponent> Sphere;

	UPROPERTY(VisibleAnywhere, Category = "Golmok|Photo")
	TObjectPtr<UCameraComponent> Camera;

	/** The photo mode subsystem (not the actor owner: AActor's Owner is private and unrelated). */
	TWeakObjectPtr<UGolmokPhotoModeSubsystem> Owner;
	/** Pitch / yaw of the actor; roll is never in here (RollDeg, camera component). */
	FRotator Look = FRotator::ZeroRotator;
	float RollDeg = 0.f;
	/** X = right, Y = forward (local, -1..1). */
	FVector2D MoveInput = FVector2D::ZeroVector;
	float UpDownInput = 0.f;
	/** Accumulated mouse delta (consumed and zeroed every Tick). */
	FVector2D MouseDelta = FVector2D::ZeroVector;
	/** Right-stick value (held until the next Look event). */
	FVector2D PadStick = FVector2D::ZeroVector;
	bool bFast = false;
	float RadiusCm = 15.f;
	int32 TickCount = 0;
};
