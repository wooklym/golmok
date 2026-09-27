#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GolmokTimeOfDay.generated.h"

class APostProcessVolume;
class UDirectionalLightComponent;
class UExponentialHeightFogComponent;
class USkyLightComponent;

/**
 * One preset from Config/Golmok/lighting_presets.json (WP-05 design section 2). Plain struct: a bHas* group that is
 * false keeps the current value (partial preset such as "interior"). The cycle presets are complete.
 */
struct FGolmokLightingPreset
{
	FName Name;
	bool bHasSun = false;
	double PitchDeg = 0.0;
	double YawDeg = 0.0;
	double Lux = 0.0;
	double Kelvin = 6500.0;
	bool bHasSky = false;
	double Sky = 1.0;
	bool bHasFog = false;
	double Fog = 0.0;
	double FogHeightFalloff = 0.2;
	bool bHasVolumetric = false;
	bool bVolumetric = false;
	bool bHasExposure = false;
	double ExposureBias = 0.0;

	bool IsComplete() const { return bHasSun && bHasSky && bHasFog && bHasVolumetric && bHasExposure; }
};

/**
 * Actual values read from / applied to the lighting actors (transition end points). The two override flags record
 * whether the sun's colour temperature and the volume's exposure bias are in use at all: a level authored without
 * them (the default InitialPreset= keeps the level's lighting) gets them switched off again when the base preset
 * is None, instead of being left with the raw property values written as overrides.
 */
struct FGolmokLightingState
{
	FRotator SunRotation = FRotator::ZeroRotator;
	double Lux = 0.0;
	/** DirectionalLight bUseTemperature; presets with a sun group turn it on. */
	bool bUseTemperature = false;
	double Kelvin = 6500.0;
	double Sky = 1.0;
	double Fog = 0.0;
	double FogHeightFalloff = 0.2;
	/** PostProcessVolume bOverride_AutoExposureBias; presets with exposure_bias turn it on. */
	bool bExposureOverridden = false;
	/** Effective bias: the volume's value when overridden, else the engine default (r.DefaultFeature.AutoExposure.Bias). */
	double ExposureBias = 0.0;
	bool bVolumetric = false;
};

/**
 * Time-of-day lighting (one per level; AGolmokPlayerController spawns a transient one when the level has none).
 *
 * Drives the DirectionalLight / SkyLight / ExponentialHeightFog / unbound PostProcessVolume tagged LightingActorTag
 * (or the first of each class) with the presets of Config/Golmok/lighting_presets.json, the same file the editor
 * Python golmok.lighting reads. ApplyPreset() changes the base preset; EnterInterior()/ExitInterior() overlay the
 * partial InteriorPreset (fog / exposure) while at least one source (a portal id) is inside. Transitions
 * interpolate over TransitionSeconds and Tick runs only while a transition is in progress.
 */
UCLASS(Config = Game, HideCategories = (Rendering, Replication, Collision, Input, LOD, Cooking, Physics, Networking))
class GOLMOK_API AGolmokTimeOfDay : public AActor
{
	GENERATED_BODY()

public:
	AGolmokTimeOfDay();

	/** Seconds for preset / interior-overlay transitions (0 = instant). Tick runs only while transitioning. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Lighting", meta = (ClampMin = "0.0"))
	float TransitionSeconds = 2.f;

	/** Relative to <Project>/Config unless absolute. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Lighting")
	FString PresetsFile = TEXT("Golmok/lighting_presets.json");

	/** Applied instantly at BeginPlay; empty = keep the level's authored lighting. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Lighting")
	FName InitialPreset;

	/** Partial preset overlaid while inside an interior (EnterInterior / ExitInterior). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Lighting")
	FName InteriorPreset = TEXT("interior");

	/** Actor tag that pins which DirectionalLight / SkyLight / ExponentialHeightFog / PostProcessVolume the presets drive. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Lighting")
	FName LightingActorTag = TEXT("GolmokLighting");

	/** Base preset (NAME_None = the level's authored lighting). */
	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Lighting|State")
	FName CurrentPreset;

	/** Base preset a running transition is heading to. */
	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Lighting|State")
	FName TargetPreset;

	/** Interior overlay is on while this is not empty (one entry per source, e.g. a portal id). */
	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Lighting|State")
	TArray<FName> InteriorSources;

	/** Last presets / apply error (empty when fine). */
	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Lighting|State")
	FString LastError;

	/** First AGolmokTimeOfDay in the world (warns once when there are several). */
	static AGolmokTimeOfDay* Find(UWorld* World);

	/** Find() or, in a game / PIE world only, spawn a transient one. */
	static AGolmokTimeOfDay* FindOrSpawn(UWorld* World);

	static bool ParsePresetsText(const FString& Json, TArray<FGolmokLightingPreset>& Out, TArray<FName>& OutCycle, FString& Error);
	static bool LoadPresetsFile(const FString& FilePath, TArray<FGolmokLightingPreset>& Out, TArray<FName>& OutCycle, FString& Error);

	/** FPaths::ProjectConfigDir() / PresetsFile (PresetsFile as-is when absolute). */
	FString ResolvePresetsPath() const;

	/** Loads the presets once; on failure logs an Error once and keeps LastError. */
	bool EnsurePresets();

	/** Change the base preset (transition unless bInstant). Unknown name -> false. */
	UFUNCTION(BlueprintCallable, Category = "Golmok|Lighting")
	bool ApplyPreset(FName Name, bool bInstant = false);

	/** Next cycle preset after CurrentPreset (cycle[0] when none or last). */
	UFUNCTION(BlueprintCallable, Category = "Golmok|Lighting")
	bool NextPreset();

	/** Adds Source; the first source starts the interior overlay transition. */
	UFUNCTION(BlueprintCallable, Category = "Golmok|Lighting")
	void EnterInterior(FName Source);

	/** Removes Source; the last source removed transitions back to the base preset. */
	UFUNCTION(BlueprintCallable, Category = "Golmok|Lighting")
	void ExitInterior(FName Source);

	UFUNCTION(BlueprintCallable, Category = "Golmok|Lighting")
	bool IsInterior() const;

	/** All preset names in file order (cycle presets + partial ones). */
	UFUNCTION(BlueprintCallable, Category = "Golmok|Lighting")
	TArray<FName> GetPresetNames() const;

	const TArray<FName>& GetCycle() const { return Cycle; }
	bool FindPreset(FName Name, FGolmokLightingPreset& Out) const;
	bool IsTransitioning() const { return bTransitioning; }

	/** 0..1 progress of the running transition (1 when none). */
	float GetTransitionAlpha() const;

	/** Moves a running transition's start forward by DeltaSeconds (photo mode: world time that passed while paused). No-op when not transitioning. */
	void ShiftTransitionStart(double DeltaSeconds);

	/** Reads the current values off the lighting actors (tests). False when no target actor was found. */
	bool CaptureState(FGolmokLightingState& Out) const;

	/** r.DefaultFeature.AutoExposure.Bias (the bias a volume without the override contributes); 1.0 when the cvar is missing. */
	static double DefaultAutoExposureBias();

	/** "overcast_morning" | "overcast_morning -> night 45%" | + " [interior: door_1]" | "(no presets)". */
	FString Describe() const;

	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

	/** Writes S to the actors. bFinal = last write of a transition (visibility / volumetric / sky recapture happen here). */
	virtual void ApplyState(const FGolmokLightingState& S, bool bFinal);

private:
	bool ResolveTargets(bool bForce = false);
	FGolmokLightingState ComposeTarget() const;
	FGolmokLightingState StateFromPreset(const FGolmokLightingPreset& P, const FGolmokLightingState& Current) const;
	void StartTransition(const FGolmokLightingState& InTo, bool bInstant);
	static FGolmokLightingState Lerp(const FGolmokLightingState& A, const FGolmokLightingState& B, float Alpha);
	FString BaseName() const;

	TArray<FGolmokLightingPreset> Presets;
	TArray<FName> Cycle;
	bool bPresetsLoaded = false;
	bool bPresetsFailed = false;
	bool bTransitioning = false;
	bool bWarnedTargets = false;
	FGolmokLightingState Initial;
	FGolmokLightingState Applied;
	FGolmokLightingState From;
	FGolmokLightingState To;
	double TransitionStart = 0.0;
	/** Base preset the running transition started from (Describe()). */
	FName FromPreset;

	TWeakObjectPtr<UDirectionalLightComponent> Sun;
	TWeakObjectPtr<AActor> SunActor;
	TWeakObjectPtr<USkyLightComponent> Sky;
	TWeakObjectPtr<UExponentialHeightFogComponent> Fog;
	TWeakObjectPtr<APostProcessVolume> PostProcess;
};
