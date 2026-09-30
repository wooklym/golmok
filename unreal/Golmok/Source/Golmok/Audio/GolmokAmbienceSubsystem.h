#pragma once
#include "CoreMinimal.h"
#include "Audio/GolmokAudioConfig.h"
#include "Audio/GolmokAudioMath.h"
#include "Subsystems/WorldSubsystem.h"
#include "GolmokAmbienceSubsystem.generated.h"

class AGolmokTimeOfDay;
class APlayerController;
class APawn;
class UAudioComponent;
class UGolmokDebugSubsystem;
class USoundWave;
class USoundAttenuation;
class USoundConcurrency;

/** Per-world audio state, sourced from audio.json; event driven lighting/interior changes. */
UCLASS()
class GOLMOK_API UGolmokAmbienceSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()
public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual bool IsTickableWhenPaused() const override { return true; }
	virtual TStatId GetStatId() const override;
	const FGolmokAudioConfig& GetConfig() const { return Config; }
	FString GetState() const { return State; }
	FString Describe() const;
	const FString& GetCredits() const { return Config.Credits; }
	bool ForceState(const FString& InState);
	void SetMuted(bool bValue) { bMuted = bValue; }
	bool IsMuted() const;
	void PlayFootstep(const FString& Set, bool bLanding);
	void RefreshBindings();
#if WITH_DEV_AUTOMATION_TESTS
	int32 GetFootstepRequests() const { return FootstepRequests; }
	int32 GetLandingRequests() const { return LandingRequests; }
#endif
	double GetPhotoGain() const { return PhotoGain.Value; }
	void SetSurfaceDiagnostic(int32 Surface, const FString& Message);
private:
	void PresetChanged(FName Name, bool bInstant);
	void InteriorChanged(bool bValue);
	void ResolveState(bool bInstant = false);
	void SetState(const FString& InState, bool bInstant);
	void StartSlot(int32 Slot, const FString& AssetId, bool bInstant);
	UFUNCTION()
	void PawnChanged(APawn* OldPawn, APawn* NewPawn);
#if WITH_DEV_AUTOMATION_TESTS
	int32 FootstepRequests = 0, LandingRequests = 0;
#endif
	FGolmokAudioConfig Config;
	FString LoadError, State, ForcedState, Preset, PendingAsset, LastFootstepSet = TEXT("none"), SurfaceError;
	bool bInterior = false, bMuted = false, bReady = false, bPhotoMuted = false;
	int32 PendingSlot = INDEX_NONE;
	double LastRealTime = 0.0, NextBindingTime = 0.0;
	FString SlotIds[2];
	GolmokAudioMath::Envelope Gains[2];
	GolmokAudioMath::Envelope PhotoGain{false};
	TSet<int32> WarnedSurfaces;
	TWeakObjectPtr<AGolmokTimeOfDay> Lighting;
	TWeakObjectPtr<APlayerController> Controller;
	TWeakObjectPtr<UGolmokDebugSubsystem> Debug;
	FDelegateHandle PresetHandle, InteriorHandle, HudHandle;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UAudioComponent>> Channels;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UAudioComponent>> OneShots;
	UPROPERTY(Transient)
	TMap<FString, TObjectPtr<USoundWave>> Sounds;
	UPROPERTY(Transient)
	TObjectPtr<USoundAttenuation> Attenuation;
	UPROPERTY(Transient)
	TObjectPtr<USoundConcurrency> Concurrency;
};
