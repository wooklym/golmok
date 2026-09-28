#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "GolmokSaveGame.generated.h"

/** One visited zone (WP-15a spec §3): the version seen first and when (UTC, ISO 8601). */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokSaveVisit
{
	GENERATED_BODY()

	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	FString ZoneId;

	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	int32 Version = 0;

	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	FString FirstVisitUtc;
};

/**
 * Time of day (spec §3 / §4). WP-14a clock: Minutes (AGolmokTimeOfDay::GetTimeOfDayMinutes) and Mode
 * (EGolmokClockMode as uint8, so the save format does not depend on the Lighting header) are restored first, per mode
 * and instantly: Fixed / Clock -> that time (Clock runs on from it), Realtime -> the PC's local time (Minutes ignored).
 * Minutes < 0 (a save from before WP-14a, the level's own lighting, or a base preset without a keyframe time) falls
 * back to PresetName with ApplyPreset(Name, true) as before. Added fields default when missing: save schema stays 1.
 */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokSaveTimeOfDay
{
	GENERATED_BODY()

	/** AGolmokTimeOfDay::CurrentPreset (the nearest keyframe on the clock); the restore fallback when Minutes < 0. */
	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	FString PresetName;

	/** Minutes of the day [0, 1440) (WP-14a); -1 = not saved (restore by PresetName). */
	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	float Minutes = -1.f;

	/** EGolmokClockMode as uint8: 0 Fixed (default, also for old saves), 1 Clock, 2 Realtime; anything else restores as Fixed. */
	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	uint8 Mode = 0;
};

/**
 * The one automatic save (WP-15a, D-017; docs/plan/WP-15-zone-travel-save.md §3), slot "golmok_auto", user index 0.
 * Game coordinates only: the position is WGS84 lat / lon / ellipsoidal height of the player in the game world plus
 * an ENU heading. No UE coordinates (they change with the level origin), no real-world location, no personal data.
 * Written and read by UGolmokSaveSubsystem. Field additions keep SaveSchemaVersion 1 (new fields default).
 */
UCLASS()
class GOLMOK_API UGolmokSaveGame : public USaveGame
{
	GENERATED_BODY()

public:
	static constexpr int32 CurrentSchemaVersion = 1;

	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	int32 SaveSchemaVersion = CurrentSchemaVersion;

	/** False when the level had no AGolmokGeoOrigin (or no pawn) at save time: Lat / Lon / HeightEllipsoidal unused. */
	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	bool bHasPosition = false;

	/** Player capsule center, WGS84 degrees / meters (game world position). */
	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	double Lat = 0.0;

	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	double Lon = 0.0;

	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	double HeightEllipsoidal = 0.0;

	/** Heading in the area ENU frame, CCW from east (deg; = -UE Yaw). Not a UE yaw. */
	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	double YawDeg = 0.0;

	/** Authoritative loaded zone the player stood in (UGolmokZoneSubsystem::FindLoadedZoneAt); empty = none (basemap). */
	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	FString ZoneId;

	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	int32 ZoneVersion = 0;

	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	FGolmokSaveTimeOfDay TimeOfDay;

	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	TArray<FGolmokSaveVisit> Visited;

	/** Photos (WP-12) as paths relative to <Project>/Saved/. The file system is the source of truth: missing files are dropped on restore. */
	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	TArray<FString> Photos;

	/** WP-18 roster id (UGolmokCharacterSubsystem::GetCurrentId); empty when unknown. */
	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	FString CharacterId;

	/** Map package the save was made in (PIE prefix removed, e.g. /Game/Golmok/Maps/L_ZoneTest): a save is restored only in that level. */
	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	FString LevelName;

	/** UTC, ISO 8601. */
	UPROPERTY(SaveGame, VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Save")
	FString SavedAtUtc;

	const FGolmokSaveVisit* FindVisit(const FString& InZoneId) const;
};
