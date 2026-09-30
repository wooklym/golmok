#pragma once
#include "CoreMinimal.h"
#include "Audio/GolmokAudioMath.h"
#include "Components/ActorComponent.h"
#include "GolmokFootstepComponent.generated.h"

struct FGolmokAudioConfig;
class UGolmokLocomotionStateComponent;
enum class EGolmokFootEvent : uint8;

/** One selected trigger driver: distance or locomotion foot events, isolated from playback. */
UCLASS()
class GOLMOK_API UGolmokFootstepComponent : public UActorComponent
{
	GENERATED_BODY()
public:
	UGolmokFootstepComponent();
	virtual void OnRegister() override;
	virtual void OnUnregister() override;
	/** Diagnostic only. 19b disables original GASP foot foley unconditionally, independent of this query/driver. */
	UFUNCTION(BlueprintPure, Category = "Golmok|Audio")
	bool UsesNotifyDriver() const;
	uint64 GetFootEventCount() const { return FootEventCount; }
#if WITH_DEV_AUTOMATION_TESTS
	uint32 GetAnimContractEvaluationsForTest() const { return AnimContractEvaluations; }
#endif
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	void TriggerFootstep(bool bLanding);
	static FString SurfaceDiagnostic(const FGolmokAudioConfig& Config, int32 Surface);
	static FString ResolveSurfaceSet(const FGolmokAudioConfig& Config, int32 Surface, bool bStairs, const FString* Diagnostic = nullptr);
private:
	void RefreshFootEventBinding();
	void OnFootEvent(EGolmokFootEvent Kind, bool bLeft);
	bool IsActivePlayer() const;
	TWeakObjectPtr<UGolmokLocomotionStateComponent> FootEvents;
	FDelegateHandle FootEventHandle;
	uint64 FootEventCount = 0; // Valid Step/Land events received, including events filtered out by driver/pause/possession.
	mutable TWeakObjectPtr<const UClass> CachedAnimClass;
	mutable uint32 CachedModeGeneration = 0;
#if WITH_DEV_AUTOMATION_TESTS
	mutable uint32 AnimContractEvaluations = 0;
#endif
	mutable bool bAnimClassCached = false, bCachedRequiresGasp = false;
	GolmokAudioMath::DistanceStepper Stepper;
	FString LastRosterId;
	FVector Previous = FVector::ZeroVector;
	bool bHasPrevious = false;
};
