#pragma once

#include "CoreMinimal.h"
#include "Weather/GolmokWeatherConfig.h"

class AActor;
class UFXSystemComponent;
class UWorld;

/**
 * WP-16a design section 7: the camera-following Niagara rain. GolmokWeatherRainFx.cpp is the only file that includes
 * Niagara headers; this header has no Niagara types, so UGolmokWeatherSubsystem (and the tests) only hold the
 * transient actor that owns the UNiagaraComponent. Every function accepts a null / destroyed actor (no-op, false).
 */
namespace GolmokWeatherRainFx
{
	/** Spawn result, stored by the subsystem as uint8. */
	enum class ELoad : uint8
	{
		Ok = 0,
		/** rain_fx.enabled false in weather.json. */
		Disabled = 1,
		/** The system asset does not exist or failed to load (or the spawn failed). */
		Missing = 2,
	};

	/**
	 * Loads Config.RainFxSystem (soft object path) and spawns one transient actor "GolmokWeatherFx" (not saved, not
	 * replicated) whose root is an inactive UNiagaraComponent with User.BoxHalfExtent set. nullptr unless OutLoad is Ok.
	 */
	GOLMOK_API AActor* Spawn(UWorld* World, const GolmokWeather::FConfig& Config, ELoad& OutLoad);

	/** The actor's UNiagaraComponent as its engine base class (nullptr when none). */
	GOLMOK_API UFXSystemComponent* GetComponent(const AActor* FxActor);

	/** Moves the actor to Location; no rotation (world-axis box). */
	GOLMOK_API void Follow(AActor* FxActor, const FVector& Location);

	/** User.RainIntensity and User.SpawnRate (the caller writes only values that moved). */
	GOLMOK_API void WriteRain(AActor* FxActor, float RainIntensity, float SpawnRate);

	/** User.BoxHalfExtent in cm. */
	GOLMOK_API void WriteBoxHalfExtent(AActor* FxActor, const FVector& HalfExtentCm);

	/** true -> Activate(true) (the asset's warmup gives falling rain at once), false -> Deactivate() (live particles finish). */
	GOLMOK_API void SetActive(AActor* FxActor, bool bActive);

	GOLMOK_API bool IsActive(const AActor* FxActor);

	/** Travel arrival / save position restore: ResetSystem() when bActive, else DeactivateImmediate() (no teleport streaks either way). */
	GOLMOK_API void Reset(AActor* FxActor, bool bActive);

	/** Reads the three user parameters back from the component's override parameter store (tests). False when the component or a parameter is missing. */
	GOLMOK_API bool ReadUserParameters(const AActor* FxActor, float& OutRainIntensity, float& OutSpawnRate, FVector& OutBoxHalfExtent);

	/** The rain asset (NS_GolmokRain) itself exposes the three user parameters (tests; the override store cannot prove it). */
	GOLMOK_API bool HasUserParameters(const AActor* FxActor);

	/** Destroys the actor (subsystem Deinitialize outside world teardown). */
	GOLMOK_API void Destroy(AActor* FxActor);
} // namespace GolmokWeatherRainFx
