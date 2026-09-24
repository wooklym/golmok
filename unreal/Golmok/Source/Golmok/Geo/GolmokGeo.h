#pragma once

#include "CoreMinimal.h"
#include "Geo/GolmokGeoMath.h"

/**
 * Unreal-facing wrappers around the pure math in Geo/GolmokGeoMath.h (double everywhere; UE5's FVector, FMatrix and
 * FTransform are already double precision). Conventions: docs/spec/zone-manifest.md §1 and §5.
 *
 *   ENU (m, x=east y=north z=up)  --S = diag(100,-100,100)-->  UE (cm, X=east Y=south Z=up)
 *   zone-local -> ECEF: manifest "transform" (16 doubles, row-major, points are column vectors)
 *   zone root actor:    S * M * S^-1  with M = inv(T_area) * T_zone  (rotation D R D, translation S t)
 */
namespace GolmokGeo
{
	/** Manifest "transform" (row-major 16) -> Mat4. False (and identity) when the array does not have 16 values. */
	GOLMOK_API bool ToMat4(const TArray<double>& RowMajor16, GolmokGeoMath::Mat4& Out);

	GOLMOK_API FVector ToFVector(const GolmokGeoMath::Vec3& V);
	GOLMOK_API GolmokGeoMath::Vec3 ToVec3(const FVector& V);

	/**
	 * Row-major column-vector Mat4 -> FMatrix (Unreal uses row vectors: v' = v * M, translation in M.M[3][0..2]).
	 * The 3x3 part is transposed and the translation moves to the last row.
	 */
	GOLMOK_API FMatrix ToFMatrix(const GolmokGeoMath::Mat4& A);

	/** Rigid UE-space matrix (cm) -> FTransform with unit scale. Rotation is taken from the orthonormal 3x3 part. */
	GOLMOK_API FTransform ToFTransform(const GolmokGeoMath::Mat4& UEMatrix);

	/** ENU point (m) -> UE (cm). */
	GOLMOK_API FVector EnuToUE(const FVector& EnuMeters);
	/** UE point (cm) -> ENU (m). */
	GOLMOK_API FVector UEToEnu(const FVector& UECentimeters);
	/** ENU direction -> UE direction (D = diag(1,-1,1); length unchanged). */
	GOLMOK_API FVector EnuDirToUE(const FVector& EnuDir);

	/** ENU bbox (m) -> UE box (cm); min/max are re-sorted because Y flips sign (spec §5 "bbox"). */
	GOLMOK_API FBox EnuBoxToUE(const FVector& MinEnu, const FVector& MaxEnu);

	/** UE Yaw (degrees) of the zone +x axis for a zone-local -> area ENU matrix: -yaw_deg (spec §1). */
	GOLMOK_API double UEYawDeg(const GolmokGeoMath::Mat4& ZoneToArea);

	/**
	 * Recomputes docs/spec/zone-manifest.md §4 tables B and C with the C++ math and compares against the published
	 * numbers (1e-4 m). Used by the console command golmok.geo.selftest (runbook pc-verify-wp04 item 6).
	 */
	GOLMOK_API bool RunSpecSelfTest(FString& OutReport);
} // namespace GolmokGeo
