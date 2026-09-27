#pragma once

#include "CoreMinimal.h"
#include "Engine/EngineTypes.h"
#include "Engine/StreamableManager.h"
#include "Subsystems/WorldSubsystem.h"
#include "Zones/GolmokZoneIndex.h"
#include "GolmokZoneSubsystem.generated.h"

class AActor;
class AGolmokZone;
class ULevel;

/** Who asked for RequestLoad / RequestUnload: portals own their interior zones (never distance-managed, never "blocked"). */
UENUM()
enum class EGolmokZoneRequestSource : uint8
{
	Console,
	Portal,
	/** Reserved (logs only). */
	Discovery
};

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

	/** A portal loaded / unloaded this zone: excluded from the distance rules and shown as "portal" instead of "blocked". */
	bool bPortalManaged = false;

	/** Discovered zone with a level-placed twin (same id): destroyed by the next DiscoverZones() once Unloaded and not pinned. */
	bool bRetirePending = false;

	/** World time when this discovered zone first met every despawn condition; < 0 while it does not. */
	double DespawnEligibleSince = -1.0;
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
 *    exclusion happens at basemap build time);
 *  - WP-09: discovers zones from Content/Golmok/Zones/index (the 3x3 Web Mercator z16 cells around the player) and
 *    spawns transient AGolmokZone actors for them, destroying them again far away; a level-placed actor with the
 *    same id always wins. Discovery runs in the timer callback before Evaluate(), never inside it;
 *  - WP-09: owns the FStreamableManager that AGolmokZone::LoadAsync() streams through.
 * Console: golmok.zone.list | golmok.zone.load <id> | golmok.zone.unload <id> | golmok.zone.refresh |
 *          golmok.zone.radius <load_m> <unload_m> | golmok.zone.index [reload]
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

	/** Loads (requests) per evaluation, to spread hitches when several zones come into range at once. */
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

	// ---- WP-09 Zone Index discovery (two-line declarations, 1:1 with the ini keys) -----------------------------------

	/** Discover zones from Content/Golmok/Zones/index around the player (WP-09). Silently off when zones.json is missing or the level has no AGolmokGeoOrigin. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone|Index")
	bool bDiscoverFromIndex = true;

	/** Seconds between index lookups (inside the Evaluate timer, before Evaluate; never per frame). Minimum UpdateIntervalSeconds. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone|Index")
	float DiscoveryIntervalSeconds = 2.f;

	/** A discovered, unloaded zone outside the 3x3 cells and farther than this (m) is destroyed. 0 = 2 x UnloadRadiusM (computed when used). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone|Index")
	float DespawnDistanceM = 0.f;

	/** The despawn conditions must hold this long (s) before a discovered zone is destroyed (no spawn / destroy thrash at cell borders). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone|Index")
	float DespawnGraceSeconds = 10.f;

	void RegisterZone(AGolmokZone* Zone);
	void UnregisterZone(AGolmokZone* Zone);

	/** Console / portal entry points. bPin keeps the zone loaded regardless of distance; Source = Portal marks the record bPortalManaged. */
	bool RequestLoad(const FString& ZoneId, bool bPin, FString& OutMessage, EGolmokZoneRequestSource Source = EGolmokZoneRequestSource::Console);
	bool RequestUnload(const FString& ZoneId, FString& OutMessage, EGolmokZoneRequestSource Source = EGolmokZoneRequestSource::Console);

	/** Called by AGolmokZone after a successful Load() / Unload() (any caller): re-resolve overlaps and basemap. */
	void NotifyZoneLoaded(AGolmokZone* Zone);
	void NotifyZoneUnloaded(AGolmokZone* Zone);

	/** Re-scan the level for basemap actors and re-apply hiding for loaded zones. */
	void RefreshBasemap();

	/** Change the hysteresis radii at runtime (console golmok.zone.radius <load_m> <unload_m>; runbook use). */
	void SetRadii(float NewLoadRadiusM, float NewUnloadRadiusM);

	/** One evaluation step (distance rules). Public so tests and console commands can force it. Never spawns, destroys or registers. */
	void Evaluate();

	/** One discovery step (spawn / despawn / retire from the index). Public for golmok.zone.index and tests; never called from Evaluate(). */
	void DiscoverZones();

	/** Re-read zones.json, drop the cell cache, discover now (golmok.zone.index reload). */
	void ReloadIndex();

	/** bDiscoverFromIndex && zones.json parsed && the world is a game world. */
	bool IsDiscoveryActive() const;

	/** Version for ZoneId: a registered actor's Version (placed first), else the index entry's, else 0 (AGolmokPortal::Configure). */
	int32 ResolveZoneVersion(const FString& ZoneId) const;

	bool IsZoneInIndex(const FString& ZoneId) const { return Index.FindZone(ZoneId) != nullptr; }
	float GetDespawnDistanceM() const { return DespawnDistanceM > 0.f ? DespawnDistanceM : 2.f * UnloadRadiusM; }
	FStreamableManager& GetStreamable() { return Streamable; }
	const FGolmokZoneIndex& GetIndex() const { return Index; }

	int32 NumDiscovered() const; // records whose zone has bSpawnedFromIndex
	int32 NumLoading() const;    // records whose zone IsLoading()

	/** True while Evaluate() / RequestLoad() / RequestUnload() hold FGolmokZoneRecord pointers across Load() / Unload(). */
	bool IsHoldingRecordPointers() const { return PointerHoldDepth > 0; }

	/** Forbidden entries (RegisterZone / UnregisterZone / RequestLoad / RequestUnload / DiscoverZones / async finish) seen while holding pointers. Tests assert 0. */
	int32 GetReentrancyViolations() const { return ReentrancyViolations; }

	/** AGolmokZone::FinishAsyncLoad() calls this first: counts a violation (Error log) when pointers are held. */
	void NoteAsyncFinish(const AGolmokZone* Zone);

	/** golmok.zone.list body: header line, then one row per zone. */
	FString DescribeZones();

	/** golmok.zone.index body (WP-09 design section 6). */
	FString DescribeIndex();

	/** Highest-version level-placed actor with this id, else the first discovered one (placed wins). */
	AGolmokZone* FindZone(const FString& ZoneId) const;
	int32 NumZones() const { return Zones.Num(); }

	/** Loaded zone whose footprint contains the level XY point; several -> ZoneWins order (interior 20 before its parent 10). Null when none. Read-only. */
	AGolmokZone* FindLoadedZoneAt(const FVector2D& LevelUEPointCm) const;

private:
	/** Timer callback: DiscoverZones() when due, then Evaluate(). The only place both run in one stack, discovery first. */
	void OnEvaluateTimer();
	AGolmokZone* SpawnDiscoveredZone(const FString& InZoneId, int32 InVersion);
	/** GetPlayerLocation + Geo->LevelUEToLonLat + GolmokGeoMath::LonLatToCell. False without a player or an AGolmokGeoOrigin. */
	bool GetPlayerCell(int32& OutX, int32& OutY, double& OutLon, double& OutLat) const;
	/** ++ReentrancyViolations + UE_LOG Error "<Op> called while zone record pointers are held" when PointerHoldDepth > 0. */
	void CheckNotHoldingPointers(const TCHAR* Op);

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

	FStreamableManager Streamable; // value member (UAssetManager pattern); handles cancelled in Deinitialize before it dies
	FGolmokZoneIndex Index;
	FString IndexLoadError;        // last zones.json parse error (golmok.zone.index "index: error ...")
	double NextDiscoverySeconds = 0.0;
	int32 LastCellX = -1;
	int32 LastCellY = -1;
	int32 PointerHoldDepth = 0;
	int32 ReentrancyViolations = 0;
	bool bWarnedNoGeoOrigin = false;
	TSet<FString> WarnedShadowedIds; // "placed v1 shadows index v2" once per id
	static constexpr int32 MaxSpawnsPerDiscovery = 8;
	static constexpr int32 MaxDestroysPerDiscovery = 4;
	static constexpr int32 MaxCachedCells = 64;

	FTimerHandle EvaluateTimer;
	FDelegateHandle LevelAddedHandle;
	FDelegateHandle LevelRemovedHandle;
	double LastBasemapScanSeconds = -1.0;
	bool bBasemapDirty = true;
	bool bWarnedNoPlayer = false;
};
