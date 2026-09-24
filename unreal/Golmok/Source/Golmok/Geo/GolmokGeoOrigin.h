#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GolmokGeoOrigin.generated.h"

/**
 * Geodetic coordinates of the level origin (0,0,0): the basemap "area origin" = CesiumGeoreference origin.
 * Exactly one per level, always placed at (0,0,0). UGolmokGeoSubsystem finds it with TActorIterator; when missing
 * the subsystem warns and treats each zone's own origin as the area origin (development levels).
 *
 * Convention for editor Python (WP-06 zone_import / basemap_import "FindOrSpawn"): find the first AGolmokGeoOrigin
 * in the level, else spawn one at (0,0,0) with label "GeoOrigin"; then set latitude / longitude / height_ellipsoidal
 * from the basemap manifest "origin". Defaults are the spec §4 area origin so the synthetic fixture reproduces
 * table C without any setup.
 */
UCLASS(HideCategories = (Rendering, Replication, Collision, Input, LOD, Cooking, Physics, Networking))
class GOLMOK_API AGolmokGeoOrigin : public AActor
{
	GENERATED_BODY()

public:
	AGolmokGeoOrigin();

	/** WGS84 latitude of the level origin, degrees. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Golmok|Geo")
	double Latitude = 37.5600;

	/** WGS84 longitude of the level origin, degrees. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Golmok|Geo")
	double Longitude = 126.9230;

	/** Ellipsoidal (not orthometric) height of the level origin, meters. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Golmok|Geo")
	double HeightEllipsoidal = 40.0;

	/** Finds the level's origin actor (first one in iteration order; warns once per world when there are several). */
	static AGolmokGeoOrigin* Find(UWorld* World);

	/** Changes every time the coordinates are edited; consumers cache derived data keyed by this value. */
	int32 GetRevision() const { return Revision; }

#if WITH_EDITOR
	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;
#endif

private:
	UPROPERTY(VisibleAnywhere, Category = "Golmok|Geo")
	TObjectPtr<USceneComponent> Root;

	UPROPERTY(Transient)
	int32 Revision = 0;
};
