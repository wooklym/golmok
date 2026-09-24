#pragma once

#include "CoreMinimal.h"
#include "GolmokZoneManifest.generated.h"

/**
 * In-memory form of a Zone manifest (docs/spec/zone-manifest.md §3, schema_version 1) and of its blockers file
 * (§3.1). Structures mirror the JSON 1:1 (snake_case key -> PascalCase member; JSON null -> empty string / bHas*).
 * Values are kept in the manifest's units: *_Enu is zone-local meters (x=east, y=north, z=up); nothing is
 * converted to UE units here (see Geo/GolmokGeo.h).
 *
 * The parser is a runtime guard, not the validator: `golmok-zone validate` (Python) is authoritative. Here an Error
 * stops the load (missing required field, malformed transform, unsafe uri); soft problems only warn.
 */

UENUM(BlueprintType)
enum class EGolmokZoneKind : uint8
{
	Exterior,
	Interior
};

/** layers.visual.format. The loader implements NaniteMesh; the others are reserved until D-010. */
UENUM(BlueprintType)
enum class EGolmokVisualFormat : uint8
{
	NaniteMesh,
	SplatPly,
	Splat3DTiles,
	SplatLcc,
	Unknown
};

/** blockers.json plane kind: glass (visible in the scan, impassable) or no_entry (invisible wall). */
UENUM(BlueprintType)
enum class EGolmokBlockerKind : uint8
{
	Glass,
	NoEntry
};

/** layers.visual.chunks[] and layers.collision.chunks[] (collision chunks carry only id / uri). */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokZoneChunk
{
	GENERATED_BODY()

	/** "id": opaque; becomes the asset name SM_<id> (real zones: c_e000_n000, fixture: chunk_00). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Id;

	/** "uri": file relative to the manifest folder (visual/<id>.obj); informational at runtime. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Uri;

	/** "bbox_enu"[0], zone-local meters. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FVector BboxMinEnu = FVector::ZeroVector;

	/** "bbox_enu"[1], zone-local meters. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FVector BboxMaxEnu = FVector::ZeroVector;

	/** False for collision chunks and for visual chunks without bbox_enu (init state before golmok-mesh ran). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	bool bHasBbox = false;

	/** "tris" (optional). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	int32 Tris = 0;
};

/** layers.visual.textures[] (only when textures are not embedded). */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokZoneTexture
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Uri;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString ChunkId;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Role;
};

/** layers.visual */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokZoneVisualLayer
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	EGolmokVisualFormat Format = EGolmokVisualFormat::NaniteMesh;

	/** "format" as written (for logs; Unknown formats keep their text here). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString FormatString;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	TArray<FGolmokZoneChunk> Chunks;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	TArray<FGolmokZoneTexture> Textures;
};

/** layers.collision */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokZoneCollisionLayer
{
	GENERATED_BODY()

	/** "format": "glb" in v1. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Format;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Uri;

	/** Optional per-chunk collision: asset SM_<zone_id>_collision_<chunk_id>. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	TArray<FGolmokZoneChunk> Chunks;
};

/** layers.blockers (optional) */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokZoneBlockersLayer
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	bool bPresent = false;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Uri;
};

/** layers.navmesh (optional; unused at runtime, UE builds its own navmesh from the collision layer). */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokZoneNavmeshLayer
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	bool bPresent = false;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Format;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Uri;
};

/** "layers" */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokZoneLayers
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FGolmokZoneVisualLayer Visual;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FGolmokZoneCollisionLayer Collision;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FGolmokZoneBlockersLayer Blockers;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FGolmokZoneNavmeshLayer Navmesh;
};

/** portals[] (consumed by WP-05 AGolmokZone::SpawnPortals). */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokZonePortal
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Id;

	/** "to_zone": zone_id of the other side (version resolved through the Zone Index). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString ToZone;

	/** pose_enu.position, zone-local meters. UE location = S * position. */
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

/** "replaces" */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokZoneReplaces
{
	GENERATED_BODY()

	/** Basemap building ids (GIS건물통합정보 keys) this zone replaces; recorded only (D-012: build-time exclude). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	TArray<FString> BuildingIds;

	/** Hide basemap terrain inside the footprint. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	bool bTerrainClip = false;
};

/** "quality" (values may be null; extra keys are kept as JSON text). */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokZoneQuality
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	bool bHasIcpRmseM = false;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	double IcpRmseM = 0.0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	bool bHasFootprintIou = false;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	double FootprintIou = 0.0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString ReviewedBy;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString ReviewedAt;

	/** Any additional keys, re-serialized as a JSON object string (spec allows extra keys here only). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString ExtraJson;
};

/** "consent" */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokZoneConsent
{
	GENERATED_BODY()

	/** public_street | owner_consent */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Type;

	/** Empty when null. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString RecordId;
};

/** sources[] */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokZoneSource
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString CaptureId;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Note;
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

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	EGolmokZoneKind Kind = EGolmokZoneKind::Exterior;

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

	/** footprint_wgs84 outer ring as (X=lon, Y=lat) degrees, closing vertex removed. Holes are ignored. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	TArray<FVector2D> FootprintLonLat;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FGolmokZoneReplaces Replaces;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FGolmokZoneLayers Layers;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	TArray<FGolmokZonePortal> Portals;

	/** "priority": higher wins where zones overlap; ties go to the higher version. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	int32 Priority = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FGolmokZoneQuality Quality;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FGolmokZoneConsent Consent;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	TArray<FString> Attribution;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	TArray<FGolmokZoneSource> Sources;

	bool IsInterior() const { return Kind == EGolmokZoneKind::Interior; }

	/** "<zone_id>@v<version>" for logs. */
	FString Key() const { return FString::Printf(TEXT("%s@v%d"), *ZoneId, Version); }
};

/** blockers.json planes[] (spec §3.1). */
USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokBlockerPlane
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FString Id;

	/** "center_enu", zone-local meters. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FVector CenterEnu = FVector::ZeroVector;

	/** "normal_enu", zone-local, not necessarily unit length. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FVector NormalEnu = FVector(0.0, -1.0, 0.0);

	/** "size_m": [width, height]. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	FVector2D SizeM = FVector2D(1.0, 1.0);

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	EGolmokBlockerKind Kind = EGolmokBlockerKind::NoEntry;
};

USTRUCT(BlueprintType)
struct GOLMOK_API FGolmokBlockers
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Zone")
	TArray<FGolmokBlockerPlane> Planes;
};

namespace GolmokZoneManifest
{
	/** Parse manifest JSON text. On failure Error names the offending field; Out may be partially filled. */
	GOLMOK_API bool ParseManifestText(const FString& JsonText, FGolmokZoneManifest& Out, FString& Error);

	/** Read + parse a manifest file (FFileHelper, so UFS-staged files inside a .pak work too). */
	GOLMOK_API bool LoadManifest(const FString& FilePath, FGolmokZoneManifest& Out, FString& Error);

	GOLMOK_API bool ParseBlockersText(const FString& JsonText, FGolmokBlockers& Out, FString& Error);
	GOLMOK_API bool LoadBlockers(const FString& FilePath, FGolmokBlockers& Out, FString& Error);

	/** Spec §2 uri rule: non-empty, '/' separated, relative, no "..", no backslash, no scheme. */
	GOLMOK_API bool IsSafeRelativeUri(const FString& Uri);

	/** Spec §2 zone_id rule: ^z_[a-z0-9]+(_[a-z0-9]+)*$ and at most 64 characters. */
	GOLMOK_API bool IsValidZoneId(const FString& ZoneId);

	/** "nanite_mesh" -> NaniteMesh etc.; anything else -> Unknown. */
	GOLMOK_API EGolmokVisualFormat ParseVisualFormat(const FString& Text);

	/** Manifest file on disk: <ProjectContentDir>/Golmok/Zones/<zone_id>/v<version>/manifest.json (spec §5). */
	GOLMOK_API FString ManifestFilePath(const FString& ZoneId, int32 Version);

	/** Package folder: /Game/Golmok/Zones/<zone_id>/v<version> */
	GOLMOK_API FString AssetFolder(const FString& ZoneId, int32 Version);

	/** /Game/Golmok/Zones/<zone_id>/v<version>/SM_<chunk_id>.SM_<chunk_id> */
	GOLMOK_API FString ChunkAssetPath(const FString& ZoneId, int32 Version, const FString& ChunkId);

	/** SM_<zone_id>_collision, or SM_<zone_id>_collision_<chunk_id> when ChunkId is not empty. */
	GOLMOK_API FString CollisionAssetPath(const FString& ZoneId, int32 Version, const FString& ChunkId);
} // namespace GolmokZoneManifest
