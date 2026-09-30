#pragma once

#include "CoreMinimal.h"
#include "Animation/GolmokLocomotionMath.h"
#include "Player/GolmokCharacter.h"
#include "Templates/SubclassOf.h"
#include "GolmokGaspCharacter.generated.h"

class UAnimInstance;
class USkeletalMesh;
class USkeletalMeshComponent;
class UGolmokLocomotionStateComponent;

/**
 * WP-19 design sections 1, 5, 6: the C++ parent of the local 19b Blueprint BP_GolmokCharacter_GASP, which adds the
 * GASP pawn interface (a Blueprint interface C++ cannot implement) and forwards GetLocomotionState() values.
 * Movement meaning is AGolmokCharacter's (walk 180 / run 500, roster speeds, orient-to-movement 540 deg/s, jump
 * 90 cm, CMC); only the acceleration profile (animation.json gasp.movement_profile) is applied on top.
 *
 * The roster keeps treating GetMesh() as "the mesh the animation Blueprint runs on" (the GASP source mesh + ABP).
 * VisualMesh, a child of GetMesh() and empty by default, shows the retargeted mesh: SetVisualOverride hides
 * GetMesh() from rendering (not its children) while it keeps posing (AlwaysTickPoseAndRefreshBones).
 */
UCLASS(Blueprintable)
class GOLMOK_API AGolmokGaspCharacter : public AGolmokCharacter
{
	GENERATED_BODY()

public:
	AGolmokGaspCharacter();

	virtual void PostInitializeComponents() override;

	UFUNCTION(BlueprintPure, Category = "Golmok|Locomotion")
	UGolmokLocomotionStateComponent* GetLocomotionStateComponent() const { return LocomotionState; }

	UFUNCTION(BlueprintPure, Category = "Golmok|Locomotion")
	USkeletalMeshComponent* GetVisualMesh() const { return VisualMesh; }

	/** Shows InMesh with the retarget anim class on VisualMesh and hides GetMesh() (which keeps posing). */
	bool SetVisualOverride(USkeletalMesh* InMesh, TSubclassOf<UAnimInstance> InAnimClass, FString& OutError);

	/** Empties VisualMesh and shows GetMesh() with its previous tick option again. No-op without an override. */
	void ClearVisualOverride();

	bool HasVisualOverride() const { return bVisualOverride; }

	/** Writes the profile to the CMC (acceleration / braking / friction only). False (unchanged) when out of range. */
	bool ApplyMovementProfile(const FString& Id, const GolmokLocomotionMath::MovementProfile& Profile);

	/** Id of the last applied profile; empty before PostInitializeComponents or when animation.json is invalid. */
	const FString& GetAppliedProfileId() const { return AppliedProfileId; }

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Locomotion")
	TObjectPtr<UGolmokLocomotionStateComponent> LocomotionState;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Locomotion")
	TObjectPtr<USkeletalMeshComponent> VisualMesh;

private:
	bool bVisualOverride = false;
	uint8 SavedTickOption = 0; // EVisibilityBasedAnimTickOption of GetMesh() before the override
	FString AppliedProfileId;
};
