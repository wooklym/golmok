#pragma once
#include "CoreMinimal.h"
#include "Audio/GolmokAudioMath.h"
#include "Components/ActorComponent.h"
#include "GolmokFootstepComponent.generated.h"

struct FGolmokAudioConfig;

/** Distance-based trigger isolated from playback, ready for a later animation-notify driver. */
UCLASS()
class GOLMOK_API UGolmokFootstepComponent : public UActorComponent
{
	GENERATED_BODY()
public:
	UGolmokFootstepComponent();
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	void TriggerFootstep(bool bLanding);
	static FString ResolveSurfaceSet(const FGolmokAudioConfig& Config, int32 Surface, bool bStairs);
private:
	GolmokAudioMath::DistanceStepper Stepper;
	FVector Previous = FVector::ZeroVector;
	bool bHasPrevious = false;
};
