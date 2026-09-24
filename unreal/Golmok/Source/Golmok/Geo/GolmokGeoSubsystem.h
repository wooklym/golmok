#pragma once

#include "CoreMinimal.h"
#include "Geo/GolmokGeoMath.h"
#include "Subsystems/WorldSubsystem.h"
#include "GolmokGeoSubsystem.generated.h"

class AGolmokGeoOrigin;

/**
 * Per-world geodesy: finds the AGolmokGeoOrigin actor and converts between zone-local / geodetic coordinates and
 * level UE coordinates (cm). Created for every world type (editor, PIE, game) so AGolmokZone::RebuildInEditor works.
 *
 * Without an origin actor every conversion falls back to "the zone's own origin is the area origin" (a zone lands
 * at the level origin, rotated only by its yaw) and a warning is logged once per world (development levels).
 */
UCLASS()
class GOLMOK_API UGolmokGeoSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual void Deinitialize() override;

	/** True when the level has an AGolmokGeoOrigin. */
	bool HasOrigin();

	/** Geodetic coordinates of the level origin. False (and zeros) when no origin actor exists. */
	bool GetOrigin(double& OutLatDeg, double& OutLonDeg, double& OutHeightEllipsoidal);

	/** Bumps when the origin actor appears, disappears or is edited; consumers key cached data by it. */
	int32 GetOriginRevision();

	/**
	 * zone-local (m) -> area ENU (m) 4x4 for a manifest "transform" (zone-local -> ECEF, row-major 16).
	 * Without an origin the zone's own origin is used as area origin (M reduces to the zone's yaw rotation).
	 * Returns false only when the transform is malformed (Out = identity).
	 */
	bool ZoneToAreaMatrix(const TArray<double>& ZoneToEcefRowMajor, GolmokGeoMath::Mat4& OutZoneToArea);

	/**
	 * Root actor transform (level UE, cm) for a zone whose chunk meshes carry vertices already in UE cm:
	 * S * M * S^-1 (spec §5 "zone 루트 actor 변환"). Identity when the transform is malformed.
	 */
	FTransform ZoneLocalToWorld(const TArray<double>& ZoneToEcefRowMajor);
	FTransform ZoneLocalToWorld(const GolmokGeoMath::Mat4& ZoneToEcef);

	/** Geodetic point -> level UE (cm). Uses the fallback origin (see class comment) when no origin actor exists. */
	FVector LonLatToLevelUE(double LonDeg, double LatDeg, double HeightEllipsoidal);

	/** Geodetic point -> level UE with an explicit area frame (ECEF -> area ENU); no origin lookup. */
	static FVector LonLatToLevelUE(const GolmokGeoMath::Mat4& EcefToArea, double LonDeg, double LatDeg, double HeightEllipsoidal);

	/** Level UE (cm) -> geodetic. False when no origin actor exists. */
	bool LevelUEToLonLat(const FVector& LevelUE, double& OutLatDeg, double& OutLonDeg, double& OutHeightEllipsoidal);

	/** ECEF -> area ENU frame for the current origin (or the given fallback geodetic origin when none exists). */
	GolmokGeoMath::Mat4 EcefToAreaMatrix(double FallbackLatDeg, double FallbackLonDeg, double FallbackH);

private:
	AGolmokGeoOrigin* FindOrigin();
	void WarnNoOriginOnce();

	TWeakObjectPtr<AGolmokGeoOrigin> CachedOrigin;
	bool bWarnedNoOrigin = false;
	int32 PresenceRevision = 0;
	bool bLastHadOrigin = false;
};
