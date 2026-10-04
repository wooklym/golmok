#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Weather/GolmokWeatherConfig.h"
#include "Weather/GolmokWeatherMath.h"
#include "GolmokWeatherSubsystem.generated.h"

class AActor;
class AGolmokTimeOfDay;
class UFXSystemComponent;
class UGolmokDebugSubsystem;
class UGolmokTravelSubsystem;
class UMaterialParameterCollection;

/** WP-16a design section 2. Same order as GolmokWeatherMath::State (static_assert in GolmokWeatherSubsystem.cpp). */
UENUM(BlueprintType)
enum class EGolmokWeather : uint8
{
	Clear,
	Overcast,
	Rain,
};

/** Design section 4: Fixed (default) changes only by command / save / initial; Schedule follows weather.json "schedule" on the time-of-day clock. */
UENUM(BlueprintType)
enum class EGolmokWeatherMode : uint8
{
	Fixed,
	Schedule,
};

/**
 * Fired once when the weather TARGET changes (command, schedule boundary, restore - restore with bInstant true); never
 * during an intensity ramp and not for the BeginPlay initial value. Inside the callback GetTarget*() already return
 * the new target while GetRainIntensity() still returns the pre-ramp value (R51-5 "target first").
 */
DECLARE_MULTICAST_DELEGATE_ThreeParams(FGolmokOnWeatherChanged, EGolmokWeather /*Target*/, float /*TargetIntensity*/, bool /*bInstant*/);

/**
 * WP-16a weather (docs/plan/WP-16-weather.md "16a 설계 (확정)"), Game and PIE worlds only.
 *
 * State machine clear / overcast / rain(intensity) with a world-seconds smoothstep transition (accumulated delta, so
 * pauses need no correction) where rain starts after the sky's first half and stops in the first half. Feeds
 * AGolmokTimeOfDay::SetWeatherModifier (composition base -> weather -> interior -> ToD transition), integrates
 * wetness / puddles into MPC_GolmokWeather, drives the camera-following Niagara rain (GolmokWeatherRainFx), freezes
 * while photo mode is active, and serves golmok.weather and the "weather:" HUD line (UGolmokDebugSubsystem provider).
 *
 * Audio (Astra lane) reads GetRainIntensity() on its own tick and subscribes to OnWeatherChanged; this class does not
 * know about audio. Without weather.json (parse error) the weather is off: clear identity, commands report the error.
 */
UCLASS()
class GOLMOK_API UGolmokWeatherSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	// ---- audio / save / photo contract (design section 9) --------------------------------------------------------

	/** Game / PIE world subsystem; nullptr otherwise (editor worlds, no world). */
	static UGolmokWeatherSubsystem* Get(const UWorld* World);

	EGolmokWeather GetTargetWeather() const { return Target; }
	/** [0.05, 1] for rain, 0 for clear / overcast. */
	float GetTargetIntensity() const { return static_cast<float>(TargetIntensity); }
	/** RainNow: the rain seen and heard now, 0..1 (lags the sky going up, leads it going down); 0 once settled on clear / overcast. */
	float GetRainIntensity() const { return static_cast<float>(RainNow); }
	float GetWetness() const { return static_cast<float>(SurfaceNow.Wetness); }
	float GetPuddleAmount() const { return static_cast<float>(SurfaceNow.Puddle); }
	bool IsTransitioning() const { return bTransitioning; }
	/** Photo mode is active: transition, rain, surface and schedule are held. */
	bool IsFrozen() const;
	/** "clear" | "overcast" | "rain". */
	static const TCHAR* WeatherName(EGolmokWeather Weather);
	static bool ParseWeather(const FString& Text, EGolmokWeather& Out);
	/** "fixed" | "schedule". */
	static const TCHAR* ModeName(EGolmokWeatherMode Mode);
	static bool ParseMode(const FString& Text, EGolmokWeatherMode& Out);

	FGolmokOnWeatherChanged OnWeatherChanged;

	// ---- control (console, save restore, tests) -----------------------------------------------------------------

	/** weather.json parsed (false = weather off, GetConfigError() says why). */
	bool IsEnabled() const { return bConfigLoaded; }
	const FString& GetConfigError() const { return ConfigError; }
	const GolmokWeather::FConfig& GetConfig() const { return Config; }

	/**
	 * New target (transition unless bInstant or transition_seconds is 0). Intensity is used for rain only and must be in
	 * [0.05, 1]. A Schedule mode switches to Fixed (log "weather: <state> in schedule mode -> fixed"). Refused while the
	 * weather is off or photo mode is active (OutMessage says why). The same target again is a no-op (true, no event).
	 */
	bool SetWeather(EGolmokWeather Weather, float Intensity, bool bInstant, FString& OutMessage);
	/** Schedule evaluates the schedule at once (transition when its slot differs). Refused while off / in photo mode. */
	bool SetMode(EGolmokWeatherMode Mode, FString& OutMessage);
	EGolmokWeatherMode GetMode() const { return Mode; }
	/** Immediate wetness / puddle (clamped, puddle <= wetness); integration continues from there. Refused while off / in photo mode. */
	bool SetSurface(float Wetness, float Puddle, FString& OutMessage);
	/** golmok.weather fx on|off (performance A/B, not saved). */
	void SetFxEnabled(bool bEnabled);
	bool IsFxEnabled() const { return bFxEnabled; }
	/** ResetSystem() on the rain component (travel arrival, save position restore): no teleport streaks. */
	void ResetRainFx();

	/** golmok.weather arguments (without the command name) -> true on success; OutMessage is the console reply. */
	bool RunCommand(const TArray<FString>& Args, FString& OutMessage);

	/** One state-machine step of DeltaSeconds world seconds (Tick calls it; tests drive it by hand). No-op while frozen. */
	void StepWeather(double DeltaSeconds);

	/** 0..1 progress of the running transition (1 when none). */
	float GetTransitionAlpha() const;
	const GolmokWeatherMath::Modifier& GetCurrentModifier() const { return ModifierNow; }
	/** Schedule slot in force at the clock now (-1 without a clock / schedule). */
	int32 GetScheduleIndexNow() const;

	/** "ok" | "missing" | "off" (weather off). */
	FString DescribeMpc() const;
	/** "on" | "off" | "idle" | "interior" | "missing" | "disabled". */
	FString DescribeFx() const;
	/** The rain Niagara component (nullptr when missing / disabled); Niagara types stay inside GolmokWeatherRainFx.cpp. */
	UFXSystemComponent* GetRainFxComponent() const;

	/** golmok.weather status (several lines). */
	FString DescribeStatus() const;
	/** golmok.weather list (schedule slots, the current one marked). */
	FString DescribeList() const;
	/** "weather: rain 0.60 (from clear 35%) | now 0.12 wet 0.05 puddle 0.00 | fixed | fx on" (+ " | schedule next 15:00 rain 0.60", + " | frozen"). */
	FString BuildHudLine() const;

	// ---- UTickableWorldSubsystem ----------------------------------------------------------------------------------
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	/** Ticks only after OnWorldBeginPlay and with weather.json loaded. */
	virtual bool IsTickable() const override;
	virtual bool IsTickableWhenPaused() const override { return false; }
	virtual TStatId GetStatId() const override;

private:
	/** Starts a transition (or applies instantly) to a new target; broadcasts OnWeatherChanged when the target changed and bBroadcast. */
	void StartTarget(EGolmokWeather Weather, double Intensity, bool bInstant, bool bBroadcast);
	/** Evaluates the schedule at the clock; starts a transition when its slot differs from the target. False = no clock (target kept). */
	bool EvaluateSchedule(bool bInstant, bool bBroadcast);
	/** Ends a running transition at its target now (same target asked again with instant). */
	void FinishTransition();
	/** The cached time of day, or (bForce, or the search cooldown is over) AGolmokTimeOfDay::Find with OnInteriorChanged rebound. */
	AGolmokTimeOfDay* ResolveTimeOfDay(bool bForce = false);
	void UnbindTimeOfDay();
	/** Sends ModifierNow to the time of day when it changed (or when a new time-of-day actor appeared). */
	void PushModifier(bool bSettled);
	void WriteMpc(bool bForce);
	void UpdateRainFx();
	void InteriorChanged(bool bInterior);
	void Traveled(const FString& ZoneId);
	bool CheckCanChange(FString& OutMessage) const;

	GolmokWeather::FConfig Config;
	FString ConfigError;
	bool bConfigLoaded = false;
	bool bConfigErrorLogged = false;

	EGolmokWeather Target = EGolmokWeather::Clear;
	double TargetIntensity = 0.0;
	EGolmokWeatherMode Mode = EGolmokWeatherMode::Fixed;

	GolmokWeatherMath::Modifier ModifierStart;
	GolmokWeatherMath::Modifier ModifierTarget;
	GolmokWeatherMath::Modifier ModifierNow;
	double RainStart = 0.0;
	double RainTarget = 0.0;
	double RainNow = 0.0;
	GolmokWeatherMath::Surface SurfaceNow;
	/** Accumulated world seconds of the running transition (design section 3). */
	double TransitionElapsed = 0.0;
	bool bTransitioning = false;
	/** Weather name the running transition started from (HUD "from clear 35%"). */
	EGolmokWeather FromWeather = EGolmokWeather::Clear;
	double FromIntensity = 0.0;

	bool bFxEnabled = true;
	bool bInterior = false;
	bool bFxMissingWarned = false;
	bool bMpcMissingWarned = false;
	bool bBegunPlay = false;

	/** Last values written to the MPC (written when they move more than ValueEpsilon). */
	double MpcRain = -1.0;
	double MpcWetness = -1.0;
	double MpcPuddle = -1.0;
	/** Last values written to the Niagara user parameters. */
	double FxRain = -1.0;
	double FxSpawnRate = -1.0;
	bool bFxActive = false;
	/** The last SetWeatherModifier call to TimeOfDay had bSettled true (a newly found time of day counts as settled). */
	bool bPushedSettled = true;
	/** Schedule mode found no clock at its last evaluation (status "schedule: no clock"). */
	bool bScheduleNoClock = false;
	/** initial.mode schedule before the clock was available: the first evaluation with a clock is instant, without an event. */
	bool bInitialSchedulePending = false;
	/** World seconds (StepWeather deltas) until the next AGolmokTimeOfDay::Find while none is cached. */
	double TimeOfDaySearchCooldown = 0.0;
	/** MPC parameter names (GolmokWeatherMath::Mpc*), built once in Initialize. */
	FName MpcRainName;
	FName MpcWetnessName;
	FName MpcPuddleName;

	TWeakObjectPtr<AGolmokTimeOfDay> TimeOfDay;
	TWeakObjectPtr<UGolmokDebugSubsystem> Debug;
	TWeakObjectPtr<UGolmokTravelSubsystem> Travel;
	FDelegateHandle InteriorHandle;
	FDelegateHandle TraveledHandle;
	FDelegateHandle HudHandle;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialParameterCollection> Mpc;

	/** The transient actor owning the rain UNiagaraComponent (GolmokWeatherRainFx). */
	UPROPERTY(Transient)
	TObjectPtr<AActor> RainFxActor;
	/** Rain fx load result: 0 ok, 1 disabled in weather.json, 2 asset missing / failed. */
	uint8 RainFxLoad = 0;
};
