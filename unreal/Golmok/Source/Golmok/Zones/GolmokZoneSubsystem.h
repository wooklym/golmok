#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "GolmokZoneSubsystem.generated.h"

class AActor;
class AGolmokZone;
class ULevel;

/** Bookkeeping for one registered zone. */
USTRUCT()
struct FGolmokZoneRecord
{
	GENERATED_BODY()

	UPROPERTY()
	TWeakObjectPtr<AGolmokZone> Zone;

	/** Loaded through the console (golmok.zone.load): never auto-unloaded by distance. */
	bool bPinned = false;

	/** Unloaded through the console: not auto-loaded again until the player leaves the unload radius. */
	bool bBlocked = false;

	/** Lost an overlap against a higher priority / newer zone: visual hidden, collision kept. */
	bool bSuppressed = false;

	/** Load() failed; not retried until golmok.zone.load / golmok.zone.refresh / RebuildInEditor (keeps the log quiet). */
	bool bLoadFailed = false;

	/** Last evaluated distance (m). When bDistanceIsLowerBound only the cheap bounds distance was computed. */
	double LastDistanceM = 1.0e9;
	bool bDistanceIsLowerBound = false;
};

/** A basemap actor (tag GolmokBasemap) the subsystem may hide while zones cover it. */
USTRUCT()
struct FGolmokBasemapEntry
{
	GENERATED_BODY()

	UPROPERTY()
	TWeakObjectPtr<AActor> Actor;

	/** Bounds center in level XY (cm); the point tested against zone footprints. */
	FVector2D CenterUE = FVector2D::ZeroVector;

	bool bIsTerrain = false;
	bool bOriginalHidden = false;
	bool bOriginalCollision = true;

	/** Zones currently hiding this actor (reference count): restored when it becomes empty. */
	TArray<FName> HiddenBy;
};

/**
 * World subsystem (game and PIE worlds only) that drives AGolmokZone actors:
 *  - loads a zone when the player is within LoadRadiusM of its footprint and unloads beyond UnloadRadiusM
 *    (hysteresis), evaluated every UpdateIntervalSeconds with a timer, never per frame;
 *  - where loaded footprints overlap, the higher priority (then higher version) zone wins and the loser's visual
 *    layer is hidden (collision stays so nobody falls through);
 *  - hides basemap actors (tag GolmokBasemap) whose bounds center lies inside a loaded zone's footprint, collision
 *    off too, and restores them when the last covering zone unloads (D-012: this is the runtime fallback, the real
 *    exclusion happens at basemap build time).
 * Console: golmok.zone.list | golmok.zone.load <id> | golmok.zone.unload <id> | golmok.zone.refresh |
 *          golmok.zone.radius <load_m> <unload_m>
 * Config: [/Script/Golmok.GolmokZoneSubsystem] in DefaultGame.ini.
 */
UCLASS(Config = Game)
class GOLMOK_API UGolmokZoneSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;

	/** Load when the player is within this distance (m) of the footprint. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone")
	float LoadRadiusM = 150.f;

	/** Unload when the player is farther than this (m). Must exceed LoadRadiusM. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone")
	float UnloadRadiusM = 250.f;

	/** Seconds between evaluations (distance, overlaps, basemap hiding). Minimum 0.1. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone")
	float UpdateIntervalSeconds = 0.5f;

	/** Synchronous loads per evaluation, to spread hitches when several zones come into range at once. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone")
	int32 MaxLoadsPerUpdate = 1;

	/** Unloads per evaluation. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone")
	int32 MaxUnloadsPerUpdate = 2;

	/** Also manage interior zones by distance (normally WP-05 portals drive them). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone")
	bool bAutoManageInterior = false;

	/** Overlap loser: spec says hide the visual layer only. Opt in to also disable its collision. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone")
	bool bSuppressLoserCollision = false;

	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Basemap")
	bool bHideBasemap = true;

	/** Actor tag that marks basemap actors (basemap_import.py adds it to every tile actor). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Basemap")
	FName BasemapTag = TEXT("GolmokBasemap");

	/** Optional second tag on terrain tiles: those stay visible for zones with replaces.terrain_clip = false. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Basemap")
	FName BasemapTerrainTag = TEXT("GolmokBasemapTerrain");

	/** Optional periodic re-scan of the level for basemap actors (s). 0 = only at BeginPlay, sublevel changes and refresh. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Basemap")
	float BasemapRescanSeconds = 0.f;

	void RegisterZone(AGolmokZone* Zone);
	void UnregisterZone(AGolmokZone* Zone);

	/** Console / portal entry points. bPin keeps the zone loaded regardless of distance. */
	bool RequestLoad(const FString& ZoneId, bool bPin, FString& OutMessage);
	bool RequestUnload(const FString& ZoneId, FString& OutMessage);

	/** Called by AGolmokZone after a successful Load() / Unload() (any caller): re-resolve overlaps and basemap. */
	void NotifyZoneLoaded(AGolmokZone* Zone);
	void NotifyZoneUnloaded(AGolmokZone* Zone);

	/** Re-scan the level for basemap actors and re-apply hiding for loaded zones. */
	void RefreshBasemap();

	/** Change the hysteresis radii at runtime (console golmok.zone.radius <load_m> <unload_m>; runbook use). */
	void SetRadii(float NewLoadRadiusM, float NewUnloadRadiusM);

	/** One evaluation step (the timer callback). Public so tests and console commands can force it. */
	void Evaluate();

	FString DescribeZones();
	AGolmokZone* FindZone(const FString& ZoneId) const;
	int32 NumZones() const { return Zones.Num(); }

private:
	bool GetPlayerLocation(FVector& OutLocation) const;
	void PruneInvalid();
	FGolmokZoneRecord* FindRecord(const AGolmokZone* Zone);
	void ResolveOverlaps();
	void UpdateBasemapHiding();
	void RestoreAllBasemap();
	void ApplyBasemapEntryState(FGolmokBasemapEntry& Entry, bool bHidden);
	void OnLevelChanged(ULevel* Level, UWorld* World);
	static bool ZoneWins(const AGolmokZone& A, const AGolmokZone& B);

	UPROPERTY(Transient)
	TArray<FGolmokZoneRecord> Zones;

	UPROPERTY(Transient)
	TArray<FGolmokBasemapEntry> Basemap;

	FTimerHandle EvaluateTimer;
	FDelegateHandle LevelAddedHandle;
	FDelegateHandle LevelRemovedHandle;
	double LastBasemapScanSeconds = -1.0;
	bool bBasemapDirty = true;
	bool bWarnedNoPlayer = false;
};
