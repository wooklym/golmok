#include "Geo/GolmokGeoSubsystem.h"

#include "Golmok.h"

#include "Engine/World.h"
#include "Geo/GolmokGeo.h"
#include "Geo/GolmokGeoOrigin.h"
#include "HAL/IConsoleManager.h"

void UGolmokGeoSubsystem::Deinitialize()
{
	CachedOrigin.Reset();
	Super::Deinitialize();
}

AGolmokGeoOrigin* UGolmokGeoSubsystem::FindOrigin()
{
	if (!CachedOrigin.IsValid())
	{
		CachedOrigin = AGolmokGeoOrigin::Find(GetWorld());
	}
	AGolmokGeoOrigin* Origin = CachedOrigin.Get();
	const bool bHas = Origin != nullptr;
	if (bHas != bLastHadOrigin)
	{
		bLastHadOrigin = bHas;
		++PresenceRevision;
	}
	return Origin;
}

void UGolmokGeoSubsystem::WarnNoOriginOnce()
{
	if (!bWarnedNoOrigin)
	{
		bWarnedNoOrigin = true;
		UE_LOG(LogGolmok, Warning,
			TEXT("No AGolmokGeoOrigin in %s: zones are placed with their own origin at the level origin (dev level mode). "
				 "Place one AGolmokGeoOrigin at (0,0,0) with the basemap area origin for geo-referenced placement."),
			GetWorld() ? *GetWorld()->GetName() : TEXT("(null world)"));
	}
}

bool UGolmokGeoSubsystem::HasOrigin()
{
	return FindOrigin() != nullptr;
}

bool UGolmokGeoSubsystem::GetOrigin(double& OutLatDeg, double& OutLonDeg, double& OutHeightEllipsoidal)
{
	if (const AGolmokGeoOrigin* Origin = FindOrigin())
	{
		OutLatDeg = Origin->Latitude;
		OutLonDeg = Origin->Longitude;
		OutHeightEllipsoidal = Origin->HeightEllipsoidal;
		return true;
	}
	OutLatDeg = 0.0;
	OutLonDeg = 0.0;
	OutHeightEllipsoidal = 0.0;
	return false;
}

int32 UGolmokGeoSubsystem::GetOriginRevision()
{
	const AGolmokGeoOrigin* Origin = FindOrigin();
	// Presence changes shift the value by a large step so an edit count of the new actor cannot collide.
	return PresenceRevision * 100000 + (Origin ? Origin->GetRevision() : 0);
}

GolmokGeoMath::Mat4 UGolmokGeoSubsystem::EcefToAreaMatrix(double FallbackLatDeg, double FallbackLonDeg, double FallbackH)
{
	double Lat = FallbackLatDeg, Lon = FallbackLonDeg, H = FallbackH;
	if (!GetOrigin(Lat, Lon, H))
	{
		WarnNoOriginOnce();
		Lat = FallbackLatDeg;
		Lon = FallbackLonDeg;
		H = FallbackH;
	}
	return GolmokGeoMath::RigidInverse(GolmokGeoMath::EnuFrame(Lat, Lon, H));
}

bool UGolmokGeoSubsystem::ZoneToAreaMatrix(const TArray<double>& ZoneToEcefRowMajor, GolmokGeoMath::Mat4& OutZoneToArea)
{
	GolmokGeoMath::Mat4 ZoneToEcef;
	if (!GolmokGeo::ToMat4(ZoneToEcefRowMajor, ZoneToEcef))
	{
		UE_LOG(LogGolmok, Error, TEXT("Zone transform needs 16 numbers, got %d."), ZoneToEcefRowMajor.Num());
		OutZoneToArea = GolmokGeoMath::Identity();
		return false;
	}
	// Fallback area origin = the zone's own origin (translation of the transform), so a dev level without an
	// AGolmokGeoOrigin shows the zone at the level origin.
	double ZoneLat = 0.0, ZoneLon = 0.0, ZoneH = 0.0;
	GolmokGeoMath::EcefToGeodetic(GolmokGeoMath::Translation(ZoneToEcef), ZoneLat, ZoneLon, ZoneH);
	OutZoneToArea = GolmokGeoMath::Multiply(EcefToAreaMatrix(ZoneLat, ZoneLon, ZoneH), ZoneToEcef);
	return true;
}

FTransform UGolmokGeoSubsystem::ZoneLocalToWorld(const GolmokGeoMath::Mat4& ZoneToEcef)
{
	TArray<double> RowMajor;
	RowMajor.Reserve(16);
	for (double V : ZoneToEcef)
	{
		RowMajor.Add(V);
	}
	return ZoneLocalToWorld(RowMajor);
}

FTransform UGolmokGeoSubsystem::ZoneLocalToWorld(const TArray<double>& ZoneToEcefRowMajor)
{
	GolmokGeoMath::Mat4 ZoneToArea;
	if (!ZoneToAreaMatrix(ZoneToEcefRowMajor, ZoneToArea))
	{
		return FTransform::Identity;
	}
	return GolmokGeo::ToFTransform(GolmokGeoMath::UEActorMatrix(ZoneToArea));
}

FVector UGolmokGeoSubsystem::LonLatToLevelUE(const GolmokGeoMath::Mat4& EcefToArea, double LonDeg, double LatDeg, double HeightEllipsoidal)
{
	const GolmokGeoMath::Vec3 Ecef = GolmokGeoMath::GeodeticToEcef(LatDeg, LonDeg, HeightEllipsoidal);
	return GolmokGeo::ToFVector(GolmokGeoMath::EnuToUE(GolmokGeoMath::ApplyPoint(EcefToArea, Ecef)));
}

FVector UGolmokGeoSubsystem::LonLatToLevelUE(double LonDeg, double LatDeg, double HeightEllipsoidal)
{
	return LonLatToLevelUE(EcefToAreaMatrix(LatDeg, LonDeg, HeightEllipsoidal), LonDeg, LatDeg, HeightEllipsoidal);
}

bool UGolmokGeoSubsystem::LevelUEToLonLat(const FVector& LevelUE, double& OutLatDeg, double& OutLonDeg, double& OutHeightEllipsoidal)
{
	double Lat = 0.0, Lon = 0.0, H = 0.0;
	if (!GetOrigin(Lat, Lon, H))
	{
		WarnNoOriginOnce();
		OutLatDeg = 0.0;
		OutLonDeg = 0.0;
		OutHeightEllipsoidal = 0.0;
		return false;
	}
	const GolmokGeoMath::Mat4 AreaToEcef = GolmokGeoMath::EnuFrame(Lat, Lon, H);
	const GolmokGeoMath::Vec3 Ecef = GolmokGeoMath::ApplyPoint(AreaToEcef, GolmokGeoMath::UEToEnu(GolmokGeo::ToVec3(LevelUE)));
	GolmokGeoMath::EcefToGeodetic(Ecef, OutLatDeg, OutLonDeg, OutHeightEllipsoidal);
	return true;
}

// ---- console commands -------------------------------------------------------------------------------------------

static void GolmokGeoSelfTest(const TArray<FString>& Args, UWorld* World)
{
	FString Report;
	const bool bOk = GolmokGeo::RunSpecSelfTest(Report);
	UE_LOG(LogGolmok, Log, TEXT("golmok.geo.selftest (spec zone-manifest.md §4 B/C): %s\n%s"), bOk ? TEXT("PASS") : TEXT("FAIL"), *Report);
	if (World)
	{
		if (UGolmokGeoSubsystem* Geo = World->GetSubsystem<UGolmokGeoSubsystem>())
		{
			double Lat = 0.0, Lon = 0.0, H = 0.0;
			if (Geo->GetOrigin(Lat, Lon, H))
			{
				UE_LOG(LogGolmok, Log, TEXT("Level origin: lat=%.7f lon=%.7f h=%.3f (ellipsoidal)"), Lat, Lon, H);
			}
			else
			{
				UE_LOG(LogGolmok, Log, TEXT("Level origin: none (AGolmokGeoOrigin missing; zones use their own origin)"));
			}
		}
	}
}

static FAutoConsoleCommandWithWorldAndArgs GGolmokGeoSelfTestCmd(
	TEXT("golmok.geo.selftest"),
	TEXT("Recompute the spec §4 coordinate examples with the C++ geodesy and print PASS/FAIL plus the level origin."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&GolmokGeoSelfTest));
