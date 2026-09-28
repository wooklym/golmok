// Zone manifest schema 2 test (WP-15a, docs/plan/WP-15-zone-travel-save.md §6).
//
// Golmok.Zone.ManifestV2: no PIE. The committed fixture Content/Golmok/Zones/z_synthetic_001/v1/manifest.json (schema 2
// since WP-15a) is parsed and turned into variants in memory: the v1 form (schema_version 1, no spawn / display_name)
// parses to the same zone with bHasSpawn false and GetDisplayName() == zone_id; v1 carrying a spawn ignores it (one
// "unknown top-level key" Warning line is expected); v2 without spawn falls back; a spawn without yaw_deg, with two
// numbers, or not an object, and schema_version 3 are errors. The spawn / fallback / yaw-sign / restore-rule math of
// Map/GolmokTravelMath.h is checked on a few fixed values (the full table is the g++ cross-check in
// tools/tests/test_ue_travel_math.py). Passes under -nullrhi. Skipped (Info) when the fixture file is missing.
//
// Headless: .\tools\ue\test.ps1 -Filter Golmok.Zone.ManifestV2

#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Map/GolmokTravelMath.h"
#include "Misc/FileHelper.h"
#include "Zones/GolmokZoneManifest.h"

namespace GolmokZoneManifestV2Test
{
	const TCHAR* FixtureZoneId = TEXT("z_synthetic_001");

	// Variants are made by text edits of the fixture (golmok_tools.zone.manifest.dumps layout: two-space indent, one
	// top-level key per line) instead of a JSON round trip, so the 17-digit transform is never re-printed.

	/** Text without the top-level "spawn": { ... } block. Empty when the block is not found. */
	FString WithoutSpawn(const FString& Text)
	{
		const int32 Begin = Text.Find(TEXT("\n  \"spawn\": {"));
		const int32 End = Begin == INDEX_NONE ? INDEX_NONE : Text.Find(TEXT("\n  },"), ESearchCase::CaseSensitive, ESearchDir::FromStart, Begin);
		return End == INDEX_NONE ? FString() : Text.Left(Begin) + Text.Mid(End + 5); // "\n  }," is 5 characters
	}

	/** Text without the "display_name" line. Empty when the line is not found. */
	FString WithoutDisplayName(const FString& Text)
	{
		const int32 Begin = Text.Find(TEXT("\n  \"display_name\": "));
		const int32 End = Begin == INDEX_NONE ? INDEX_NONE : Text.Find(TEXT("\n"), ESearchCase::CaseSensitive, ESearchDir::FromStart, Begin + 1);
		return End == INDEX_NONE ? FString() : Text.Left(Begin) + Text.Mid(End);
	}

	FString WithSchemaVersion(const FString& Text, int32 InVersion)
	{
		return Text.Replace(TEXT("\"schema_version\": 2,"), *FString::Printf(TEXT("\"schema_version\": %d,"), InVersion));
	}

	/** Text whose spawn block is replaced by `"spawn": <Json>,`. */
	FString WithSpawn(const FString& Text, const TCHAR* Json)
	{
		const FString Stripped = WithoutSpawn(Text);
		const int32 Priority = Stripped.Find(TEXT("\n  \"priority\": "));
		return Priority == INDEX_NONE ? FString() : Stripped.Left(Priority) + FString::Printf(TEXT("\n  \"spawn\": %s,"), Json) + Stripped.Mid(Priority);
	}
} // namespace GolmokZoneManifestV2Test

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokZoneManifestV2Test, "Golmok.Zone.ManifestV2",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokZoneManifestV2Test::RunTest(const FString& Parameters)
{
	using namespace GolmokZoneManifestV2Test;
	namespace TM = GolmokTravelMath;

	// ---- pure math (Map/GolmokTravelMath.h) -------------------------------------------------------------------
	{
		TM::Mat4 I{};
		I[0] = I[5] = I[10] = I[15] = 1.0;
		const TM::Vec3 Feet = TM::SpawnFeetUE(I, TM::Vec3{1.0, 2.0, 3.0});
		TestTrue(TEXT("ENU (1,2,3) m -> UE (100,-200,300) cm"),
			FMath::IsNearlyEqual(Feet[0], 100.0, 1e-9) && FMath::IsNearlyEqual(Feet[1], -200.0, 1e-9) && FMath::IsNearlyEqual(Feet[2], 300.0, 1e-9));
		TestTrue(TEXT("yaw_deg 90 (north) -> UE Yaw -90"), FMath::IsNearlyEqual(TM::SpawnYawUE(I, 90.0), -90.0, 1e-9));
		TestTrue(TEXT("yaw_deg 0 (east) -> UE Yaw 0"), FMath::IsNearlyEqual(TM::SpawnYawUE(I, 0.0), 0.0, 1e-9));
		// Root turned by UE Yaw +30 (zone yaw_deg -30): a spawn facing north ends at UE Yaw -60.
		TM::Mat4 R = I;
		const double C = FMath::Cos(FMath::DegreesToRadians(30.0));
		const double S = FMath::Sin(FMath::DegreesToRadians(30.0));
		R[0] = C;
		R[1] = -S;
		R[4] = S;
		R[5] = C;
		R[3] = 1000.0;
		TestTrue(TEXT("root UE Yaw 30 + spawn yaw_deg 90 -> UE Yaw -60"), FMath::IsNearlyEqual(TM::SpawnYawUE(R, 90.0), -60.0, 1e-9));
		const TM::Vec3 Fallback = TM::FallbackFeetUE(R, false, TM::Vec3{0.0, 0.0, 0.0});
		TestTrue(TEXT("fallback without a hit = zone origin"), FMath::IsNearlyEqual(Fallback[0], 1000.0, 1e-9) && FMath::IsNearlyEqual(Fallback[1], 0.0, 1e-9));
		TM::Vec3 Start{}, End{};
		TM::FallbackTrace(R, Start, End);
		TestTrue(TEXT("fallback probe starts 3 m above the origin"), FMath::IsNearlyEqual(Start[2], 300.0, 1e-9) && End[2] < 0.0);
		const TM::Vec3 Standing = TM::StandingLocationUE(TM::Vec3{0.0, 0.0, 100.0}, 88.0);
		TestTrue(TEXT("standing = feet + half height + clearance"), FMath::IsNearlyEqual(Standing[2], 100.0 + 88.0 + TM::ArrivalClearanceCm, 1e-9));
		TestTrue(TEXT("save yaw: UE -90 -> ENU 90"), FMath::IsNearlyEqual(TM::UEYawToEnuYaw(-90.0), 90.0, 1e-9));
		TestTrue(TEXT("save yaw round trip"), FMath::IsNearlyEqual(TM::EnuYawToUEYaw(TM::UEYawToEnuYaw(123.4)), 123.4, 1e-9));
		TestTrue(TEXT("restore rule 1"), TM::DecideRestore(true, true, false, 1, 1, false) == TM::ERestore::SavedPosition);
		TestTrue(TEXT("restore rule 2 (version)"), TM::DecideRestore(true, true, false, 1, 2, true) == TM::ERestore::SavedZoneSpawn);
		TestTrue(TEXT("restore rule 2 (home)"), TM::DecideRestore(true, true, false, 1, 0, true) == TM::ERestore::HomeZoneSpawn);
		TestTrue(TEXT("restore rule 3"), TM::DecideRestore(true, true, false, 1, 0, false) == TM::ERestore::None);
		TestTrue(TEXT("restore: no slot"), TM::DecideRestore(false, true, true, 0, 0, true) == TM::ERestore::None);
	}

	// ---- fixture manifest -------------------------------------------------------------------------------------
	const FString Path = GolmokZoneManifest::ManifestFilePath(FixtureZoneId, 1);
	FString Original;
	if (!FFileHelper::LoadFileToString(Original, *Path))
	{
		AddInfo(FString::Printf(TEXT("skipped: fixture manifest %s missing"), *Path));
		return true;
	}

	FGolmokZoneManifest V2;
	FString Error;
	if (!TestTrue(FString::Printf(TEXT("fixture parses (%s)"), *Error), GolmokZoneManifest::ParseManifestText(Original, V2, Error)))
	{
		AddError(Error);
		return true;
	}
	TestEqual(TEXT("fixture is schema_version 2"), V2.SchemaVersion, 2);
	TestTrue(TEXT("fixture has a spawn"), V2.bHasSpawn);
	TestTrue(TEXT("fixture spawn position (5, 4, 0)"), V2.SpawnPositionEnu.Equals(FVector(5.0, 4.0, 0.0), 1e-9));
	TestTrue(TEXT("fixture spawn yaw 90"), FMath::IsNearlyEqual(V2.SpawnYawDeg, 90.0, 1e-9));
	TestFalse(TEXT("fixture display_name set"), V2.DisplayName.IsEmpty());
	TestTrue(TEXT("GetDisplayName() = display_name"), V2.GetDisplayName() == V2.DisplayName);

	// v1 form of the same zone.
	{
		const FString Text = WithSchemaVersion(WithoutDisplayName(WithoutSpawn(Original)), 1);
		FGolmokZoneManifest V1;
		Error.Reset();
		TestTrue(FString::Printf(TEXT("v1 parses (%s)"), *Error), GolmokZoneManifest::ParseManifestText(Text, V1, Error));
		TestEqual(TEXT("v1 schema_version"), V1.SchemaVersion, 1);
		TestFalse(TEXT("v1: no spawn (fallback)"), V1.bHasSpawn);
		TestEqual(TEXT("v1: display name = zone_id"), V1.GetDisplayName(), FString(FixtureZoneId));
		TestTrue(TEXT("v1: same transform"), V1.Transform == V2.Transform);
		TestEqual(TEXT("v1: same footprint"), V1.FootprintLonLat.Num(), V2.FootprintLonLat.Num());
		TestEqual(TEXT("v1: same portals"), V1.Portals.Num(), V2.Portals.Num());
		TestEqual(TEXT("v1: same chunks"), V1.Layers.Visual.Chunks.Num(), V2.Layers.Visual.Chunks.Num());
	}
	// v1 carrying spawn: validator error, runtime ignores it (one Warning line).
	{
		const FString Text = WithSchemaVersion(WithoutDisplayName(Original), 1);
		FGolmokZoneManifest M;
		Error.Reset();
		TestTrue(TEXT("v1 + spawn still parses"), GolmokZoneManifest::ParseManifestText(Text, M, Error));
		TestFalse(TEXT("v1 + spawn: spawn ignored"), M.bHasSpawn);
	}
	// v2 without spawn / display_name.
	{
		const FString Text = WithoutDisplayName(WithoutSpawn(Original));
		FGolmokZoneManifest M;
		Error.Reset();
		TestTrue(TEXT("v2 without spawn parses"), GolmokZoneManifest::ParseManifestText(Text, M, Error));
		TestFalse(TEXT("v2 without spawn: fallback"), M.bHasSpawn);
		TestEqual(TEXT("v2 without display_name: zone_id"), M.GetDisplayName(), FString(FixtureZoneId));
	}
	// Errors.
	struct FErrorCase
	{
		const TCHAR* Name;
		FString Text;
		const TCHAR* Expect;
	};
	const TArray<FErrorCase> Cases = {
		{TEXT("spawn without yaw_deg"), WithSpawn(Original, TEXT("{\"position_enu\": [1.0, 2.0, 0.0]}")), TEXT("spawn")},
		{TEXT("spawn position with two numbers"), WithSpawn(Original, TEXT("{\"position_enu\": [1.0, 2.0], \"yaw_deg\": 0.0}")), TEXT("position_enu")},
		{TEXT("spawn not an object"), WithSpawn(Original, TEXT("3")), TEXT("spawn")},
		{TEXT("schema_version 3"), WithSchemaVersion(Original, 3), TEXT("schema_version")},
	};
	for (const FErrorCase& Case : Cases)
	{
		if (!TestFalse(FString::Printf(TEXT("%s: variant built"), Case.Name), Case.Text.IsEmpty() || Case.Text == Original))
		{
			continue;
		}
		FGolmokZoneManifest M;
		FString CaseError;
		const bool bOk = GolmokZoneManifest::ParseManifestText(Case.Text, M, CaseError);
		TestFalse(FString::Printf(TEXT("%s is an error"), Case.Name), bOk);
		TestTrue(FString::Printf(TEXT("%s: error names '%s' (%s)"), Case.Name, Case.Expect, *CaseError), CaseError.Contains(Case.Expect));
	}
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
