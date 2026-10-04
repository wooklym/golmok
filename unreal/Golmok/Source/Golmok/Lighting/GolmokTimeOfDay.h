#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Weather/GolmokWeatherMath.h"
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
	/** Keyframe time (schema 2 "time", cycle presets only); minutes of the day. */
	bool bHasTime = false;
	double TimeMinutes = 0.0;
	/** WP-14a design 2a: "hold_minutes" (cycle presets only, optional): the keyframe state is held this long from TimeMinutes. */
	bool bHasHold = false;
	double HoldMinutes = 0.0;

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

/** WP-14a design section 4: how TimeOfDayMinutes moves. Fixed = the WP-05 behavior (the clock stands still). */
UENUM(BlueprintType)
enum class EGolmokClockMode : uint8
{
	Fixed,
	Clock,
	Realtime,
};

/**
 * Time-of-day lighting (one per level; AGolmokPlayerController spawns a transient one when the level has none).
 *
 * Drives the DirectionalLight / SkyLight / ExponentialHeightFog / unbound PostProcessVolume tagged LightingActorTag
 * (or the first of each class) with the presets of Config/Golmok/lighting_presets.json, the same file the editor
 * Python golmok.lighting reads. ApplyPreset() changes the base preset; EnterInterior()/ExitInterior() overlay the
 * partial InteriorPreset (fog / exposure) while at least one source (a portal id) is inside. Transitions
 * interpolate over TransitionSeconds and Tick runs only while a transition is in progress or the clock runs.
 *
 * WP-14a: the cycle presets are keyframes at their "time"; TimeOfDayMinutes (0..1440) picks the interpolation of
 * the two keyframes around it (GolmokClockMath). ClockMode Fixed (default) keeps the WP-05 behavior: the clock
 * stands still and ApplyPreset() moves it to the preset's keyframe. Clock advances it by ClockMinutesPerRealSecond
 * per world second, Realtime follows the PC's local time. CurrentPreset is always the nearest keyframe.
 * Design 2a: a keyframe with "hold_minutes" keeps its state that long from its time, then ramps to the next keyframe
 * (the default night holds 21:30 -> 05:30); the nearest-keyframe midpoint is the ramp's.
 *
 * Event contract (PR #51 R51-5, Fable): CurrentPreset and IsNight() describe the TARGET state from the moment a jump
 * starts (ApplyPreset, SetTimeOfDay, a mode switch, a Realtime re-sync), not after its transition has finished. Inside
 * an OnPresetChanged callback IsNight() already returns the new value; OnNightChanged fires after OnPresetChanged.
 */
// [WP-13 hook] Native notifications for audio subscribers.
DECLARE_MULTICAST_DELEGATE_TwoParams(FGolmokOnPresetChanged, FName, bool);
DECLARE_MULTICAST_DELEGATE_OneParam(FGolmokOnInteriorChanged, bool);
// [/WP-13 hook]
DECLARE_MULTICAST_DELEGATE_OneParam(FGolmokOnNightChanged, bool);
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

	/** WP-14a: minutes of the day [0, 1440) (the clock; start time when the mode is Clock and no InitialPreset is set). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Lighting|Clock", meta = (ClampMin = "0.0", ClampMax = "1439.999"))
	float TimeOfDayMinutes = 450.f;

	/** Fixed (default, WP-05 behavior) | Clock | Realtime. Code default only; DefaultGame.ini does not set it. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Lighting|Clock")
	EGolmokClockMode ClockMode = EGolmokClockMode::Fixed;

	/** Clock mode: game minutes per world second (0.5 = a day in 48 minutes). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Lighting|Clock", meta = (ClampMin = "0.001", ClampMax = "1440.0"))
	float ClockMinutesPerRealSecond = 0.5f;

	/** Realtime mode: added to the PC's local time (no time-zone conversion). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Lighting|Clock")
	float RealtimeOffsetMinutes = 0.f;

	/** IsNight(): base lux below this. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Lighting|Clock", meta = (ClampMin = "0.0"))
	float NightLuxThreshold = 0.1f;

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

	/**
	 * Next cycle preset after CurrentPreset (cycle[0] when none or last). On the clock (after SetTimeOfDay, Clock /
	 * Realtime) the next keyframe after the clock time instead (R51-4): 10:01 -> clear_noon 12:30, not the one after
	 * the nearest keyframe; at a keyframe time the one after it.
	 */
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

	// ---- WP-14a clock ---------------------------------------------------------------------------------------

	/** Jump to Minutes (wrapped into the day): transition unless bInstant. The base follows the clock from then on. False without keyframes. */
	UFUNCTION(BlueprintCallable, Category = "Golmok|Lighting")
	bool SetTimeOfDay(float Minutes, bool bInstant = false);

	UFUNCTION(BlueprintCallable, Category = "Golmok|Lighting")
	float GetTimeOfDayMinutes() const { return TimeOfDayMinutes; }

	/** Fixed stops the clock where it is; Clock runs from the current time; Realtime jumps (transition) to the local time. */
	UFUNCTION(BlueprintCallable, Category = "Golmok|Lighting")
	bool SetClockMode(EGolmokClockMode Mode);

	UFUNCTION(BlueprintCallable, Category = "Golmok|Lighting")
	EGolmokClockMode GetClockMode() const { return ClockMode; }

	/** Base lighting lux < NightLuxThreshold (the interpolated TARGET state: already the new value inside OnPresetChanged; OnNightChanged fires after it when this flips). */
	UFUNCTION(BlueprintCallable, Category = "Golmok|Lighting")
	bool IsNight() const { return bNight; }

	/** One clock step (Tick calls it; tests call it directly): Clock adds rate x DeltaSeconds, Realtime reads the local time. No-op in Fixed. */
	void AdvanceClock(double DeltaSeconds);

	/** Keyframe times of GetCycle() in minutes (empty until the presets are loaded). */
	const TArray<double>& GetCycleTimes() const { return CycleTimes; }

	/** Design 2a: keyframe holds of GetCycle() in minutes (0 = none; same order and length as GetCycleTimes()). */
	const TArray<double>& GetCycleHolds() const { return CycleHolds; }

	/** Base state the clock gives at Minutes (keyframe interpolation with holds, no interior overlay); false without keyframes. */
	bool EvaluateClock(double Minutes, FGolmokLightingState& Out) const;

	/** PC local time + RealtimeOffsetMinutes, wrapped (Realtime mode target). */
	double RealtimeTargetMinutes() const;

	/** " 12:30 fixed" | " 13:02 clock x10" | " 21:40 realtime" | " --:-- fixed" (level lighting) - appended to the HUD tod: line. */
	FString DescribeClock() const;

	/** False while the base is the level's authored lighting (no preset, not on the clock): the HUD and golmok.tod status show --:--. */
	bool HasTimeOfDay() const { return !CurrentPreset.IsNone() || bBaseFromClock; }

	/** "fixed" | "clock" | "realtime". */
	static const TCHAR* ClockModeName(EGolmokClockMode Mode);
	static bool ParseClockMode(const FString& Text, EGolmokClockMode& Out);

	// ---- WP-16a weather -------------------------------------------------------------------------------------

	/**
	 * Design 5-4: the weather's lighting modifier, applied after the base and before the interior overlay
	 * (ComposeTarget). Before BeginPlay it is only stored; a running transition heads for the new target; a running
	 * clock picks it up on its next tick; otherwise it is written at once. bSettled = last write of a weather change
	 * (visibility / volumetric / sky recapture happen then); false while the weather is still moving.
	 */
	void SetWeatherModifier(const GolmokWeatherMath::Modifier& M, bool bSettled);

	/** Identity (clear) until UGolmokWeatherSubsystem sets one. */
	const GolmokWeatherMath::Modifier& GetWeatherModifier() const { return WeatherModifier; }

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

	// WP-14a clock helpers.
	FGolmokLightingState ComposeBase() const;
	FName NearestKeyframe(double Minutes) const;
	void UpdateTickEnabled();
	/** Recomputes IsNight() from the base (target) state; true when it flipped. Callers set it before OnPresetChanged and broadcast OnNightChanged after it (R51-5). */
	bool UpdateNight();
	void ApplyClockState(const FGolmokLightingState& S);
	bool IsPhotoModeActive() const;
	/** The clock at full precision: PreciseMinutes while it still matches the float property, else the property (set from outside). */
	double ClockMinutesNow() const;
	/** Wraps Minutes and stores it in PreciseMinutes and TimeOfDayMinutes. */
	void StoreMinutes(double Minutes);
	/** SetTimeOfDay without the Realtime -> Fixed fallback (the clock's own jumps: mode switch, re-sync, BeginPlay). */
	bool JumpTo(double Minutes, bool bInstant);
	/** WP-16a: S with WeatherModifier applied (GolmokWeatherMath::Apply on the fields it has); S unchanged for the identity. */
	FGolmokLightingState ApplyWeather(const FGolmokLightingState& S) const;

	TArray<FGolmokLightingPreset> Presets;
	TArray<FName> Cycle;
	/** Keyframe minutes of Cycle (same order). */
	TArray<double> CycleTimes;
	/** Keyframe hold minutes of Cycle (same order; design 2a). */
	TArray<double> CycleHolds;
	/** True while the base lighting is the clock interpolation at TimeOfDayMinutes (SetTimeOfDay, Clock / Realtime); false = CurrentPreset's values (ApplyPreset in Fixed, WP-05). */
	bool bBaseFromClock = false;
	bool bNight = false;
	/** Realtime: photo mode held the clock; the next free tick re-syncs with a transition. */
	bool bRealtimeHeld = false;
	/** Realtime: UWorld::GetRealTimeSeconds() of the previous clock step (-1 = none). A GamePause photo mode stops the tick, so a gap longer than the transition re-syncs with one (R51-6). */
	double LastRealtimeStepSeconds = -1.0;
	/** A static sky light is recaptured when the nearest keyframe changes on the clock (not every tick). */
	bool bRecapturePending = false;
	/** Double copy of TimeOfDayMinutes so a slow rate / high frame rate still advances (a float step near 1440 rounds away). */
	double PreciseMinutes = 0.0;
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
	/** WP-16a: weather lighting modifier (identity = clear, the WP-05 / WP-14a behavior). */
	GolmokWeatherMath::Modifier WeatherModifier;
	// [WP-13 hook] Public subscription API; no subscriber means no behavior change.
public:
	FGolmokOnPresetChanged OnPresetChanged;
	FGolmokOnInteriorChanged OnInteriorChanged;
	// [/WP-13 hook]
	/** WP-14a: base lighting crossed NightLuxThreshold (true = night), fired after OnPresetChanged when both change. No subscriber yet (14b emissives, audio optional). */
	FGolmokOnNightChanged OnNightChanged;
};
