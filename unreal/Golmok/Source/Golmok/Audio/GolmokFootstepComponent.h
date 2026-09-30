#pragma once
#include "CoreMinimal.h"
#include "Audio/GolmokAudioMath.h"
#include "Animation/GolmokLocomotionStateComponent.h"
#include "Components/ActorComponent.h"
#include "GolmokFootstepComponent.generated.h"

struct FGolmokAudioConfig;

/** One selected trigger driver: distance or locomotion foot events, isolated from playback. */
UCLASS()
class GOLMOK_API UGolmokFootstepComponent : public UActorComponent
{
	GENERATED_BODY()
public:
	UGolmokFootstepComponent();
	virtual void OnRegister() override;
	virtual void OnUnregister() override;
	/** 19b may use this config hook to suppress original GASP foley after its notify route is verified. */
	UFUNCTION(BlueprintPure, Category = "Golmok|Audio")
	bool UsesNotifyDriver() const;
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
	GolmokAudioMath::DistanceStepper Stepper;
	FString LastRosterId;
	FVector Previous = FVector::ZeroVector;
	bool bHasPrevious = false;
};
