#include "Geo/GolmokGeo.h"

#include "Golmok.h"

namespace GolmokGeo
{
	bool ToMat4(const TArray<double>& RowMajor16, GolmokGeoMath::Mat4& Out)
	{
		Out = GolmokGeoMath::Identity();
		if (RowMajor16.Num() != 16)
		{
			return false;
		}
		for (int32 i = 0; i < 16; ++i)
		{
			Out[static_cast<std::size_t>(i)] = RowMajor16[i];
		}
		return true;
	}

	FVector ToFVector(const GolmokGeoMath::Vec3& V)
	{
		return FVector(V[0], V[1], V[2]);
	}

	GolmokGeoMath::Vec3 ToVec3(const FVector& V)
	{
		return GolmokGeoMath::Vec3{static_cast<double>(V.X), static_cast<double>(V.Y), static_cast<double>(V.Z)};
	}

	FMatrix ToFMatrix(const GolmokGeoMath::Mat4& A)
	{
		FMatrix M = FMatrix::Identity;
		for (int32 i = 0; i < 3; ++i)
		{
			for (int32 j = 0; j < 3; ++j)
			{
				// Unreal row-vector convention: M.M[row][col] with basis vectors in rows, so transpose the 3x3 part.
				M.M[i][j] = GolmokGeoMath::At(A, static_cast<std::size_t>(j), static_cast<std::size_t>(i));
			}
			M.M[3][i] = GolmokGeoMath::At(A, static_cast<std::size_t>(i), 3);
			M.M[i][3] = 0.0;
		}
		M.M[3][3] = 1.0;
		return M;
	}

	FTransform ToFTransform(const GolmokGeoMath::Mat4& UEMatrix)
	{
		FMatrix Rot = ToFMatrix(UEMatrix);
		const FVector Location(Rot.M[3][0], Rot.M[3][1], Rot.M[3][2]);
		Rot.M[3][0] = 0.0;
		Rot.M[3][1] = 0.0;
		Rot.M[3][2] = 0.0;
		FQuat Q = Rot.ToQuat();
		Q.Normalize();
		return FTransform(Q, Location, FVector::OneVector);
	}

	FVector EnuToUE(const FVector& EnuMeters)
	{
		return ToFVector(GolmokGeoMath::EnuToUE(ToVec3(EnuMeters)));
	}

	FVector UEToEnu(const FVector& UECentimeters)
	{
		return ToFVector(GolmokGeoMath::UEToEnu(ToVec3(UECentimeters)));
	}

	FVector EnuDirToUE(const FVector& EnuDir)
	{
		return FVector(EnuDir.X, -EnuDir.Y, EnuDir.Z);
	}

	FBox EnuBoxToUE(const FVector& MinEnu, const FVector& MaxEnu)
	{
		const FVector A = EnuToUE(MinEnu);
		const FVector B = EnuToUE(MaxEnu);
		return FBox(A.ComponentMin(B), A.ComponentMax(B));
	}

	double UEYawDeg(const GolmokGeoMath::Mat4& ZoneToArea)
	{
		return GolmokGeoMath::UEYawDegFromZoneToArea(ZoneToArea);
	}

	bool RunSpecSelfTest(FString& OutReport)
	{
		using namespace GolmokGeoMath;
		// docs/spec/zone-manifest.md §4: zone origin (37.5620, 126.9250, 50), area origin (37.5600, 126.9230, 40).
		struct FCase
		{
			double Yaw;
			Vec3 Local;
			Vec3 Ecef;   // table B
			Vec3 UELevel; // table C (cm)
		};
		const FCase Cases[] = {
			{0.0, {0, 0, 0}, {-3041244.8025, 4046878.9767, 3867051.5610}, {17670.59, -22198.00, 999.37}},
			{0.0, {10, 0, 0}, {-3041252.7967, 4046872.9690, 3867051.5610}, {18670.59, -22198.02, 999.34}},
			{0.0, {0, 10, 0}, {-3041241.1401, 4046874.1032, 3867059.4880}, {17670.57, -23198.00, 999.33}},
			{30.0, {10, 0, 0}, {-3041249.8945, 4046871.3371, 3867055.5245}, {18536.61, -22698.02, 999.33}},
			{30.0, {0, 10, 0}, {-3041237.6337, 4046877.7600, 3867058.4259}, {17170.58, -23064.01, 999.35}},
		};
		bool bOk = true;
		OutReport.Reset();
		for (const FCase& C : Cases)
		{
			const Mat4 Zone = ZoneTransform(37.5620, 126.9250, 50.0, C.Yaw);
			const Vec3 Ecef = ApplyPoint(Zone, C.Local);
			const Mat4 ToArea = ZoneLocalToAreaEnu(Zone, 37.5600, 126.9230, 40.0);
			const Vec3 UEPos = GolmokGeoMath::EnuToUE(ApplyPoint(ToArea, C.Local));
			// The actor matrix applied to a vertex already in UE cm must give the same level position.
			const Vec3 ViaActor = ApplyPoint(UEActorMatrix(ToArea), GolmokGeoMath::EnuToUE(C.Local));
			double ErrEcef = 0.0, ErrUE = 0.0, ErrActor = 0.0;
			for (int32 i = 0; i < 3; ++i)
			{
				ErrEcef = FMath::Max(ErrEcef, FMath::Abs(Ecef[i] - C.Ecef[i]));
				ErrUE = FMath::Max(ErrUE, FMath::Abs(UEPos[i] - C.UELevel[i]));
				ErrActor = FMath::Max(ErrActor, FMath::Abs(ViaActor[i] - UEPos[i]));
			}
			const bool bCaseOk = ErrEcef < 1e-4 && ErrUE < 0.01 && ErrActor < 1e-6;
			bOk = bOk && bCaseOk;
			OutReport += FString::Printf(TEXT("%s yaw=%.0f local=(%.0f,%.0f,%.0f) ecef_err=%.2e m ue=(%.2f,%.2f,%.2f) cm ue_err=%.4f cm actor_err=%.2e\n"),
				bCaseOk ? TEXT("OK  ") : TEXT("FAIL"), C.Yaw, C.Local[0], C.Local[1], C.Local[2], ErrEcef, UEPos[0], UEPos[1], UEPos[2], ErrUE,
				ErrActor);
		}
		const Mat4 ToArea30 = ZoneLocalToAreaEnu(ZoneTransform(37.5620, 126.9250, 50.0, 30.0), 37.5600, 126.9230, 40.0);
		const double Yaw = UEYawDeg(ToArea30);
		const bool bYawOk = FMath::Abs(Yaw + 30.0) < 0.01;
		bOk = bOk && bYawOk;
		OutReport += FString::Printf(TEXT("%s UE yaw for yaw_deg=30: %.4f (expected -30)\n"), bYawOk ? TEXT("OK  ") : TEXT("FAIL"), Yaw);
		return bOk;
	}
} // namespace GolmokGeo
