#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Zones/GolmokZoneManifest.h"
#include "GolmokZone.generated.h"

class UBoxComponent;
class UGolmokZoneSubsystem;
class UStaticMesh;
class UStaticMeshComponent;

UENUM(BlueprintType)
enum class EGolmokZoneState : uint8
{
	Unloaded,
	Loaded,
	Failed
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
 * UGolmokZoneSubsystem (game / PIE worlds only) loads and unloads zones by distance; in the editor use the
 * "Rebuild In Editor" button (WP-06 zone_import.py calls it after importing).
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

	/**
	 * Reserved: asynchronous asset loading. Loads synchronously for now.
	 * TODO(WP-05+): UGolmokZoneSubsystem owns one FStreamableManager; LoadAsync() collects the chunk / collision
	 * FSoftObjectPaths, sets a Loading state, builds `FStreamableDelegate Done = FStreamableDelegate::CreateUObject(this,
	 * &AGolmokZone::OnAssetsLoaded)` as a named variable (a temporary is overload-ambiguous on 5.4+) and keeps the
	 * TSharedPtr<FStreamableHandle>; Unload() cancels it; OnAssetsLoaded runs BuildVisualLayer/BuildCollisionLayer/
	 * BuildBlockers only while still Loading (StaticLoadObject then returns the already resident assets).
	 */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone|Streaming")
	bool bAsyncLoad = false;

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

	/** Read the manifest (if needed), place the actor and create chunk / collision / blocker components. */
	UFUNCTION(BlueprintCallable, Category = "Golmok|Zone")
	bool Load();

	/** Destroy every component created by Load(). The manifest and footprint cache are kept. */
	UFUNCTION(BlueprintCallable, Category = "Golmok|Zone")
	void Unload();

	UFUNCTION(BlueprintCallable, Category = "Golmok|Zone")
	bool IsLoaded() const { return State == EGolmokZoneState::Loaded; }

	/** Spike layer toggle: show / hide the visual chunks (and placeholder boxes). Collision is untouched. */
	UFUNCTION(BlueprintCallable, Category = "Golmok|Zone")
	void SetVisualVisible(bool bVisible);

	/** Spike layer toggle: enable / disable collision meshes and blockers. */
	UFUNCTION(BlueprintCallable, Category = "Golmok|Zone")
	void SetCollisionEnabled(bool bEnabled);

	bool IsVisualVisible() const { return bVisualVisible; }

	/** Editor button: re-read the manifest from disk, then Unload + Load. Components are transient (not saved). */
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
	/** Called at the end of Load(); WP-05 spawns AGolmokPortal actors from Manifest.Portals here. */
	virtual void SpawnPortals();
	/** Called at the start of Unload(). */
	virtual void DestroyPortals();

	UPROPERTY(Transient)
	TArray<TObjectPtr<AActor>> PortalActors;

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

	UStaticMeshComponent* MakeMeshComponent(const FName& Name, UStaticMesh* Mesh, bool bVisual);
	UBoxComponent* MakeBoxComponent(const FName& Name, const FVector& RelativeLocation, const FRotator& RelativeRotation,
		const FVector& Extent, bool bCollide, const FColor& Color);
	static UStaticMesh* LoadMeshAsset(const FString& ObjectPath);

private:
	bool ApplyRootTransform();
	bool BuildFootprintCache();
	UGolmokZoneSubsystem* GetZoneSubsystem() const;
	void DestroyOwnedComponents();

	UPROPERTY(VisibleAnywhere, Category = "Golmok|Zone")
	TObjectPtr<USceneComponent> Root;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> ChunkComponents;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> CollisionComponents;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UBoxComponent>> PlaceholderBoxes;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UBoxComponent>> BlockerComponents;

	TArray<FVector2D> FootprintUE;
	TArray<double> FootprintXs;
	TArray<double> FootprintYs;
	FBox2D FootprintBoundsUE = FBox2D(ForceInit);
	int32 FootprintOriginRevision = INDEX_NONE;

	bool bManifestLoaded = false;
	bool bVisualVisible = true;
	bool bCollisionOn = true;
	bool bWarnedAsync = false;
};
