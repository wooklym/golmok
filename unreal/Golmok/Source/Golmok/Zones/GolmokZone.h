#pragma once

#include "CoreMinimal.h"
#include "Engine/StreamableManager.h"
#include "GameFramework/Actor.h"
#include "UObject/SoftObjectPath.h"
#include "Zones/GolmokZoneManifest.h"
#include "GolmokZone.generated.h"

class UBoxComponent;
class UGolmokZoneSubsystem;
class UMaterialInterface;
class UStaticMesh;
class UStaticMeshComponent;

UENUM(BlueprintType)
enum class EGolmokZoneState : uint8
{
	Unloaded,
	Loaded,
	Failed,
	/** WP-09: chunk / collision assets are streaming (FStreamableManager); the components are built next tick after completion. */
	Loading
};

/**
 * One Zone (docs/spec/zone-manifest.md) placed in a level. ZoneId + Version locate the manifest
 * (Content/Golmok/Zones/<id>/v<n>/manifest.json) and the imported assets (/Game/Golmok/Zones/<id>/v<n>/SM_*).
 *
 * Load() reads the manifest once, places the actor with UGolmokGeoSubsystem (zone-local -> area ENU -> UE), then
 * creates transient components: one UStaticMeshComponent per visual chunk (no collision), the collision mesh(es)
 * (hidden, BlockAll), and one UBoxComponent per blocker plane (hidden, BlockAll). A chunk whose SM_<id> asset is
 * missing gets a visible wire box the size of its bbox so placement can be checked before assets exist.
 *
 * With bAsyncLoad (WP-09) the assets whose package exists are streamed through UGolmokZoneSubsystem's
 * FStreamableManager (state Loading); the completion only schedules FinishAsyncLoad() for the next tick, which builds
 * the components from the resident assets. Nothing is ever built on the Load() / Evaluate() stack that way.
 *
 * UGolmokZoneSubsystem (game / PIE worlds only) loads and unloads zones by distance and discovers zones from the
 * Zone Index (bSpawnedFromIndex); in the editor use the "Rebuild In Editor" button (WP-06 zone_import.py calls it
 * after importing), which always loads synchronously.
 */
UCLASS(Config = Game, HideCategories = (Rendering, Replication, Input, LOD, Cooking, Physics, Networking))
class GOLMOK_API AGolmokZone : public AActor
{
	GENERATED_BODY()

public:
	AGolmokZone();

	/** zone_id, e.g. z_synthetic_001. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString ZoneId;

	/** Manifest version (folder v<Version>). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Golmok|Zone", meta = (ClampMin = "1"))
	int32 Version = 1;

	/** Let UGolmokZoneSubsystem load/unload this zone by player distance. Interior zones are driven by portals (WP-05). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	bool bAutoManaged = true;

	/** Stream chunk / collision assets through UGolmokZoneSubsystem's FStreamableManager (state Loading; components built next tick after completion). False = WP-04 synchronous StaticLoadObject path. Editor worlds are always synchronous. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone|Streaming")
	bool bAsyncLoad = true;

	/** Show a wire box (bbox_enu) for chunks whose static mesh asset is missing. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone|Debug")
	bool bDrawMissingAssetBoxes = true;

	/** Thickness of blocker collision boxes, cm. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone|Collision", meta = (ClampMin = "1.0"))
	double BlockerThicknessCm = 10.0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category = "Golmok|Zone|State")
	EGolmokZoneState State = EGolmokZoneState::Unloaded;

	/** Chunk / collision assets that were missing during the last Load() (wire boxes stand in for chunks). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category = "Golmok|Zone|State")
	int32 MissingAssetCount = 0;

	/** Last manifest / load error (empty when fine). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category = "Golmok|Zone|State")
	FString LastError;

	/** Parsed manifest (kept between load cycles; disk is read once per ZoneId/Version). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category = "Golmok|Zone|State")
	FGolmokZoneManifest Manifest;

	/** Parsed blockers.json (empty when the manifest has no blockers layer). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category = "Golmok|Zone|State")
	FGolmokBlockers Blockers;

	/** Spawned by UGolmokZoneSubsystem::DiscoverZones from the Zone Index (transient; a level-placed actor with the same id wins). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category = "Golmok|Zone|State")
	bool bSpawnedFromIndex = false;

	/** Asynchronous loads completed since BeginPlay (test hook). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category = "Golmok|Zone|State")
	int32 AsyncLoadCount = 0;

	/**
	 * Read the manifest (if needed), place the actor and create chunk / collision / blocker components.
	 * True = Loaded, or Loading started (async); false = Failed (LastError). A Loading zone returns true (no-op).
	 */
	UFUNCTION(BlueprintCallable, Category = "Golmok|Zone")
	bool Load();

	/** Cancel an in-flight async load, then destroy every component created by Load(). The manifest and footprint cache are kept. */
	UFUNCTION(BlueprintCallable, Category = "Golmok|Zone")
	void Unload();

	UFUNCTION(BlueprintCallable, Category = "Golmok|Zone")
	bool IsLoaded() const { return State == EGolmokZoneState::Loaded; }

	UFUNCTION(BlueprintCallable, Category = "Golmok|Zone")
	bool IsLoading() const { return State == EGolmokZoneState::Loading; }

	bool IsLoadedOrLoading() const { return State == EGolmokZoneState::Loaded || State == EGolmokZoneState::Loading; }

	/** Seconds since LoadAsync() issued the request; 0 when not loading. */
	double GetLoadingSeconds() const;

	/** Priority for the next LoadAsync(): FStreamableManager::AsyncLoadHighPriority for pinned (portal / console) loads. */
	void SetAsyncLoadPriority(int32 InPriority) { AsyncPriority = InPriority; }

	/** Cancel an in-flight async load (no-op otherwise): timer cleared, serial bumped, handle cancelled, Loading -> Unloaded. */
	void CancelAsyncLoad();

	/** Chunk (nanite_mesh) / collision object paths whose package exists (FPackageName::DoesPackageExist); OutMissing counts the rest. */
	TArray<FSoftObjectPath> CollectAssetPaths(int32& OutMissing) const;

	bool IsFinishPending() const { return bFinishPending; }

	/** Spike layer toggle: show / hide the visual chunks (and placeholder boxes). Collision is untouched. */
	UFUNCTION(BlueprintCallable, Category = "Golmok|Zone")
	void SetVisualVisible(bool bVisible);

	/** Spike layer toggle: enable / disable collision meshes and blockers. */
	UFUNCTION(BlueprintCallable, Category = "Golmok|Zone")
	void SetCollisionEnabled(bool bEnabled);

	bool IsVisualVisible() const { return bVisualVisible; }

	/**
	 * WP-05 collision debug view: show the (normally hidden) collision meshes with WireMaterial on every slot (nullptr
	 * restores the mesh materials), unhide the blocker boxes; placeholder boxes stay visible either way.
	 */
	void SetCollisionDebugVisible(bool bVisible, UMaterialInterface* WireMaterial);

	/** Editor button: re-read the manifest from disk, then Unload + Load (synchronous: no zone subsystem in editor worlds). */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Golmok|Zone")
	void RebuildInEditor();

	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Golmok|Zone")
	void UnloadInEditor();

	/** Parse the manifest (and blockers) and place the actor. Returns false with LastError set. */
	bool EnsureManifest(bool bForceReload = false);

	/** True when the manifest has been parsed successfully. */
	bool HasManifest() const { return bManifestLoaded; }

	/** Footprint in level UE XY (cm), cached per geo-origin revision. Empty when the manifest is not loaded. */
	const TArray<FVector2D>& GetFootprintUE();
	const FBox2D& GetFootprintBoundsUE();

	/** Horizontal distance (m) from a level UE point to the footprint polygon; 0 inside. Huge when unknown. */
	double DistanceToFootprintM(const FVector2D& LevelUEPointCm);

	/** Distance (m) to the footprint's 2D bounds: a cheap lower bound of DistanceToFootprintM (0 inside the box). */
	double DistanceToBoundsM(const FVector2D& LevelUEPointCm);

	/** True when the two footprints overlap in level XY. */
	bool FootprintOverlaps(AGolmokZone& Other);

	/** True when the level XY point lies inside the footprint. */
	bool FootprintContains(const FVector2D& LevelUEPointCm);

	int32 GetPriority() const { return Manifest.Priority; }
	bool IsInterior() const { return Manifest.IsInterior(); }
	const FString& GetParentZoneId() const { return Manifest.ParentZone; }

	/** Portal helpers for WP-05: world transform (S * position, Yaw = -yaw_deg) and radius in cm. */
	FTransform GetPortalWorldTransform(const FGolmokZonePortal& Portal) const;
	static double PortalRadiusCm(const FGolmokZonePortal& Portal) { return Portal.RadiusM * 100.0; }

	/** Path helpers exposed for tools and tests (spec §5). */
	FString GetManifestFilePath() const;

	// ---- WP-05 hooks -------------------------------------------------------------------------------------------
	/** Called at the end of Load() (or FinishAsyncLoad()); WP-05 spawns AGolmokPortal actors from Manifest.Portals here. */
	virtual void SpawnPortals();
	/** Called at the start of Unload(). */
	virtual void DestroyPortals();

	UPROPERTY(Transient)
	TArray<TObjectPtr<AActor>> PortalActors;

	/** AGolmokPortal actors spawned by the last Load() (empty while unloaded). */
	const TArray<TObjectPtr<AActor>>& GetPortalActors() const { return PortalActors; }

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
#if WITH_EDITOR
	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;
#endif

	/** Load() steps, overridable for other visual formats (D-010). Each returns the number of components created. */
	virtual int32 BuildVisualLayer();
	virtual int32 BuildCollisionLayer();
	virtual int32 BuildBlockers();

	/**
	 * Mesh for a manifest object path. Inside FinishAsyncLoad (bAssetsPreloaded) FSoftObjectPath::ResolveObject() first;
	 * otherwise nullptr when the package does not exist (no StaticLoadObject probe, no flush), else LoadMeshAsset().
	 * Virtual for D-010 formats.
	 */
	virtual UStaticMesh* AcquireMeshAsset(const FString& ObjectPath);

	/** Issue the streamable request. False when nothing can be requested (no existing package / no handle): Load() continues synchronously. */
	bool LoadAsync();

	/** Streamable completion (weak lambda target). Only records bFinishPending and schedules FinishAsyncLoad for the next tick. */
	void OnStreamableComplete(uint32 InSerial);

	/** Next-tick timer target, the ONLY Loading -> Loaded path: build the layers from resident assets, SpawnPortals, NotifyZoneLoaded. */
	void FinishAsyncLoad();

	/** Name for a new runtime component: Base, or Base__<n> if that name is still taken (duplicate ids in a manifest). */
	FName UniqueComponentName(const FName& Base) const;
	UStaticMeshComponent* MakeMeshComponent(const FName& Name, UStaticMesh* Mesh, bool bVisual, const FString& Tag);
	UBoxComponent* MakeBoxComponent(const FName& Name, const FVector& RelativeLocation, const FRotator& RelativeRotation,
		const FVector& Extent, bool bCollide, const FColor& Color, const FString& Tag);
	static UStaticMesh* LoadMeshAsset(const FString& ObjectPath);

private:
	bool ApplyRootTransform();
	bool BuildFootprintCache();
	UGolmokZoneSubsystem* GetZoneSubsystem() const;
	void DestroyOwnedComponents();

	UPROPERTY(VisibleAnywhere, Category = "Golmok|Zone")
	TObjectPtr<USceneComponent> Root;

	// VisibleAnywhere so the runtime-created (native, transient) components show up in the details panel for the
	// PC verifier; each component also carries its manifest id as a component tag.
	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Zone|State")
	TArray<TObjectPtr<UStaticMeshComponent>> ChunkComponents;

	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Zone|State")
	TArray<TObjectPtr<UStaticMeshComponent>> CollisionComponents;

	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Zone|State")
	TArray<TObjectPtr<UBoxComponent>> PlaceholderBoxes;

	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Zone|State")
	TArray<TObjectPtr<UBoxComponent>> BlockerComponents;

	TArray<FVector2D> FootprintUE;
	TArray<double> FootprintXs;
	TArray<double> FootprintYs;
	FBox2D FootprintBoundsUE = FBox2D(ForceInit);
	int32 FootprintOriginRevision = INDEX_NONE;

	// ---- async load (WP-09 design section 3-4 / 5) ----------------------------------------------------------------
	TSharedPtr<FStreamableHandle> LoadHandle;
	FTimerHandle AsyncFinishTimer;
	uint32 AsyncSerial = 0;            // bumped by every request and every cancel
	uint32 PendingFinishSerial = 0;    // serial the pending FinishAsyncLoad belongs to
	int32 AsyncPriority = 0;           // FStreamableManager::DefaultAsyncLoadPriority
	double AsyncStartSeconds = 0.0;
	bool bFinishPending = false;       // OnStreamableComplete ran, FinishAsyncLoad not yet
	bool bAssetsPreloaded = false;     // true only during FinishAsyncLoad's Build* calls
	bool bWarnedHandleIncomplete = false;

	bool bManifestLoaded = false;
	bool bVisualVisible = true;
	bool bCollisionOn = true;
};
