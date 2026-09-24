#pragma once

#include "CoreMinimal.h"
#include "GolmokZoneManifest.generated.h"

/**
 * In-memory form of a Zone manifest (docs/spec/zone-manifest.md §3, schema_version 1) and of its blockers file
 * (§3.1). Field names follow the JSON keys exactly (snake_case -> PascalCase). Only what the runtime needs is
 * parsed: quality / consent / attribution / sources are validated by `golmok-zone validate` (Python), not here.
 *
 * Units: *_Enu values are zone-local meters (x=east, y=north, z=up). Nothing here is converted to UE units;
 * see Geo/GolmokGeo.h for the conversions.
 */

/** layers.visual.chunks[] (and layers.collision.chunks[], which only fills Id / Uri). */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokZoneChunk
{
	GENERATED_BODY()

	/** "id": becomes the asset name SM_<id>; opaque string (real zones use c_e000_n000, the fixture chunk_00). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Id;

	/** "uri": file relative to the manifest folder (visual/<id>.obj); informational at runtime. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Uri;

	/** "bbox_enu"[0]: zone-local meters. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FVector BboxMinEnu = FVector::ZeroVector;

	/** "bbox_enu"[1]: zone-local meters. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FVector BboxMaxEnu = FVector::ZeroVector;

	/** False for collision chunks and for visual chunks whose bbox is missing. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	bool bHasBbox = false;

	/** "tris" (optional). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	int32 Tris = 0;
};

/** "layers" */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokZoneLayers
{
	GENERATED_BODY()

	/** layers.visual.format: nanite_mesh | splat_ply | splat_3dtiles | splat_lcc. The loader implements nanite_mesh. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString VisualFormat;

	/** layers.visual.chunks[] */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	TArray<FGolmokZoneChunk> VisualChunks;

	/** layers.collision.format (always "glb" in v1). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString CollisionFormat;

	/** layers.collision.uri */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString CollisionUri;

	/** layers.collision.chunks[] (optional): when present the collision asset is SM_<zone_id>_collision_<chunk_id>. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	TArray<FGolmokZoneChunk> CollisionChunks;

	/** layers.blockers.uri (optional; empty when absent). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString BlockersUri;

	/** layers.navmesh.uri (optional; unused by the runtime, UE builds its own navmesh from the collision). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString NavmeshUri;
};

/** portals[] — consumed by WP-05 (AGolmokZone::SpawnPortals). */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokZonePortal
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Id;

	/** "to_zone": zone_id of the other side (version resolved through the Zone Index). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString ToZone;

	/** pose_enu.position: zone-local meters. UE location = S * position. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FVector PositionEnu = FVector::ZeroVector;

	/** pose_enu.yaw_deg: entering direction, CCW from east. UE Yaw = -yaw_deg. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	double YawDeg = 0.0;

	/** "radius_m" */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	double RadiusM = 1.0;

	/** "kind": "door" */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Kind;
};

/** blockers.json planes[] (spec §3.1). */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokBlockerPlane
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Id;

	/** "center_enu": zone-local meters. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FVector CenterEnu = FVector::ZeroVector;

	/** "normal_enu": zone-local, not necessarily unit length. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FVector NormalEnu = FVector(0.0, -1.0, 0.0);

	/** "size_m": [width, height]. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FVector2D SizeM = FVector2D(1.0, 1.0);

	/** "kind": glass (visible, impassable) | no_entry (invisible wall). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Kind;
};

USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokBlockers
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	TArray<FGolmokBlockerPlane> Planes;
};

/** manifest.json (schema_version 1). */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokZoneManifest
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	int32 SchemaVersion = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString ZoneId;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	int32 Version = 0;

	/** "kind": exterior | interior */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Kind;

	/** "parent_zone": zone_id for interior zones, empty for exterior (JSON null). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString ParentZone;

	/** origin.lat (deg) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	double OriginLat = 0.0;

	/** origin.lon (deg) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	double OriginLon = 0.0;

	/** origin.height_ellipsoidal (m) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	double OriginHeightEllipsoidal = 0.0;

	/** "origin_ecef" (m) */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FVector OriginEcef = FVector::ZeroVector;

	/** "transform": zone-local ENU (m) -> ECEF, 16 doubles row-major, rigid (checked at parse time). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	TArray<double> Transform;

	/** footprint_wgs84 outer ring as (lon, lat) in degrees, closing vertex removed. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	TArray<FVector2D> FootprintLonLat;

	/** replaces.building_ids */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	TArray<FString> ReplacesBuildingIds;

	/** replaces.terrain_clip */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	bool bTerrainClip = false;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FGolmokZoneLayers Layers;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	TArray<FGolmokZonePortal> Portals;

	/** "priority": higher wins where zones overlap; ties go to the higher version. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	int32 Priority = 0;

	bool IsInterior() const { return Kind == TEXT("interior"); }
};

namespace GolmokZoneManifest
{
	/** Parse manifest JSON text. On failure Error names the offending field and Out is left partially filled. */
	GOLMOK_API bool ParseManifestText(const FString& JsonText, FGolmokZoneManifest& Out, FString& Error);

	/** Read + parse a manifest file (FFileHelper, so staged UFS files inside a .pak work too). */
	GOLMOK_API bool LoadManifest(const FString& FilePath, FGolmokZoneManifest& Out, FString& Error);

	GOLMOK_API bool ParseBlockersText(const FString& JsonText, FGolmokBlockers& Out, FString& Error);
	GOLMOK_API bool LoadBlockers(const FString& FilePath, FGolmokBlockers& Out, FString& Error);

	/** Manifest file on disk: <ProjectContentDir>/Golmok/Zones/<zone_id>/v<version>/manifest.json (spec §5). */
	GOLMOK_API FString ManifestFilePath(const FString& ZoneId, int32 Version);

	/** Package folder: /Game/Golmok/Zones/<zone_id>/v<version> */
	GOLMOK_API FString AssetFolder(const FString& ZoneId, int32 Version);

	/** /Game/Golmok/Zones/<zone_id>/v<version>/SM_<chunk_id>.SM_<chunk_id> */
	GOLMOK_API FString ChunkAssetPath(const FString& ZoneId, int32 Version, const FString& ChunkId);

	/** SM_<zone_id>_collision, or SM_<zone_id>_collision_<chunk_id> when ChunkId is not empty. */
	GOLMOK_API FString CollisionAssetPath(const FString& ZoneId, int32 Version, const FString& ChunkId);
} // namespace GolmokZoneManifest
