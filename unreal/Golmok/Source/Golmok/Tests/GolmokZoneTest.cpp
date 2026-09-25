// Zone index / async load tests (WP-09 design section 8-2).
//
// Golmok.Zone.IndexParse: no PIE. FGolmokZoneIndex::ParseZonesText / ParseCellText on the spec section 6 example
// (the committed fixture index: three zones, cell 16/55874/25379), eight error cases, CellFileName, the cell formula,
// and an in-memory reader (TMap<FString, FString> + read counter) proving "one file read per cell, a missing file is an
// empty cell, cached", CollectAround(55873, 25380, 1) == [001_interior, 001, 002] without duplicates, and a
// version-mismatched cell row reported once and skipped. Content/Golmok/Zones/index is loaded too when present.
// Golmok.Zone.IndexDiscover: on L_ZoneTest (skipped when the map is missing) discovery must spawn the transient
// z_synthetic_002 actor from the index within DiscoveryIntervalSeconds + 1 s while the placed z_synthetic_001 stays
// the only actor with its id; golmok.zone.list shows [index] / [placed] and the "discovered" header column;
// golmok.zone.index runs; then the pawn is moved 3 km east and, with DespawnGraceSeconds = 0, two discovery passes
// destroy z_synthetic_002 again. GetReentrancyViolations() must stay 0.
// Golmok.Zone.AsyncLoad: on L_Dev (skipped when missing) a z_synthetic_001 actor with bAsyncLoad is spawned. With
// existing asset packages (PC) Load() must go Loading (no portals yet), RequestLoad must report "loading", and within
// 5 s the zone is Loaded with AsyncLoadCount == 1 and one portal; without assets the synchronous fallback loads at once
// (MissingAssetCount == chunks + collision, AsyncLoadCount == 0). Unload() empties everything either way.
// Golmok.Zone.AsyncCancel: same spawn; with assets Load() then Unload() in the same tick cancels the request (Unloaded,
// no pending finish, no components 1 s later, AsyncLoadCount == 0), a new Load() completes (AsyncLoadCount == 1), and
// Destroy() while Loading produces no error. Without assets there is no cancel path (info, pass).
// Golmok.Zone.InteriorNotBlocked: on L_ZoneTest (skipped without an interior zone actor, placed or discovered) a
// portal-sourced RequestLoad / RequestUnload of z_synthetic_001_interior marks the row " portal" and never " blocked",
// Evaluate() does not reload it, a console RequestUnload marks " blocked" (regression) and a console RequestLoad drops
// " portal".
// All pass under -nullrhi.
//
// Headless: .\tools\ue\test.ps1 -Filter Golmok.Zone   (or in the editor console: Automation RunTests Golmok.Zone)

#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Components/PrimitiveComponent.h"
#include "Editor.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "Geo/GolmokGeoMath.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"
#include "Zones/GolmokZone.h"
#include "Zones/GolmokZoneIndex.h"
#include "Zones/GolmokZoneSubsystem.h"

namespace GolmokZoneTest
{
	const TCHAR* DevMap = TEXT("/Game/Golmok/Maps/L_Dev");
	const TCHAR* ZoneTestMap = TEXT("/Game/Golmok/Maps/L_ZoneTest");
	const TCHAR* ExteriorZoneId = TEXT("z_synthetic_001");
	const TCHAR* InteriorZoneId = TEXT("z_synthetic_001_interior");
	const TCHAR* SecondZoneId = TEXT("z_synthetic_002");
	const TCHAR* MemIndexDir = TEXT("mem:/index");
	constexpr double AsyncTimeoutSeconds = 5.0;

	// ---- spec section 6 example texts (the committed fixture index, one zone entry per line) ------------------------

	const TCHAR* ZonesJson = TEXT("{\"schema_version\": 1, \"cell_zoom\": 16, \"zones\": [\n")
							 TEXT("{\"id\": \"z_synthetic_001\", \"version\": 1, \"kind\": \"exterior\", \"priority\": 10, ")
							 TEXT("\"bbox_wgs84\": [126.924773635, 37.561909901, 126.925226365, 37.562090099], \"manifest\": \"z_synthetic_001/v1/manifest.json\"},\n")
							 TEXT("{\"id\": \"z_synthetic_001_interior\", \"version\": 1, \"kind\": \"interior\", \"priority\": 20, ")
							 TEXT("\"bbox_wgs84\": [126.925011318, 37.562090099, 126.925101865, 37.562144159], \"manifest\": \"z_synthetic_001_interior/v1/manifest.json\"},\n")
							 TEXT("{\"id\": \"z_synthetic_002\", \"version\": 1, \"kind\": \"exterior\", \"priority\": 10, ")
							 TEXT("\"bbox_wgs84\": [126.927082506, 37.56199099, 126.927444694, 37.562144159], \"manifest\": \"z_synthetic_002/v1/manifest.json\"}\n")
							 TEXT("]}");

	/** One "zones" row of a cell file (aggregate, so a brace list of rows needs no TPair constructor). */
	struct FCellRow
	{
		const TCHAR* Id;
		int32 Version;
	};

	FString CellJson(int32 X, int32 Y, const TArray<FCellRow>& Rows, int32 Z = 16)
	{
		FString Out = FString::Printf(TEXT("{\"schema_version\": 1, \"z\": %d, \"x\": %d, \"y\": %d, \"zones\": ["), Z, X, Y);
		for (int32 i = 0; i < Rows.Num(); ++i)
		{
			Out += FString::Printf(TEXT("%s{\"id\": \"%s\", \"version\": %d}"), i > 0 ? TEXT(", ") : TEXT(""), Rows[i].Id, Rows[i].Version);
		}
		return Out + TEXT("]}");
	}

	/** golmok.zone.list row of ZoneId ("  <id padded> v.."), empty when absent. */
	FString ZoneRow(UGolmokZoneSubsystem* Subsystem, const TCHAR* ZoneId)
	{
		TArray<FString> Lines;
		Subsystem->DescribeZones().ParseIntoArrayLines(Lines, /*bCullEmpty*/ true);
		const FString Prefix = FString::Printf(TEXT("  %s "), ZoneId);
		for (const FString& Line : Lines)
		{
			if (Line.StartsWith(Prefix))
			{
				return Line;
			}
		}
		return FString();
	}

	/** Deferred-spawned z_synthetic_001 actor the AsyncLoad / AsyncCancel scenarios drive by hand. */
	AGolmokZone* SpawnTestZone(FAutomationTestBase* Test, UWorld* World)
	{
		AGolmokZone* Zone = World->SpawnActorDeferred<AGolmokZone>(AGolmokZone::StaticClass(), FTransform::Identity);
		if (!Zone)
		{
			Test->AddError(TEXT("could not spawn AGolmokZone"));
			return nullptr;
		}
		Zone->ZoneId = ExteriorZoneId;
		Zone->Version = 1;
		Zone->bAutoManaged = false; // the test drives Load / Unload itself
		Zone->bAsyncLoad = true;
		Zone->FinishSpawning(FTransform::Identity);
		return Zone;
	}

	int32 NumPrimitiveComponents(const AGolmokZone* Zone)
	{
		TInlineComponentArray<UPrimitiveComponent*> Primitives;
		Zone->GetComponents(Primitives);
		return Primitives.Num();
	}

	/** Shared latent-command scaffolding: PIE world lookup, phase timing, timeout failure (as in GolmokPortalTest). */
	class FZoneScenarioBase : public IAutomationLatentCommand
	{
	public:
		explicit FZoneScenarioBase(FAutomationTestBase* InTest) : Test(InTest), CreatedAt(FPlatformTime::Seconds()) {}

	protected:
		/** Null until PIE is running; fails the test after 60 s of waiting. Sets Now / Elapsed for the current phase. */
		UWorld* BeginUpdate(bool& bOutDone)
		{
			bOutDone = false;
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			if (!World)
			{
				bOutDone = Fail(TEXT("PIE world not running"), 60.0, FPlatformTime::Seconds() - CreatedAt);
				return nullptr;
			}
			Now = World->GetTimeSeconds();
			if (PhaseStart < 0.0)
			{
				PhaseStart = Now;
			}
			Elapsed = Now - PhaseStart;
			return World;
		}

		bool Next(int32 NextPhase)
		{
			Phase = NextPhase;
			PhaseStart = Now;
			return false;
		}

		/** Keeps waiting until Timeout (seconds of game time in this phase), then records the error and stops. */
		bool Fail(const TCHAR* What, double Timeout, double InElapsed)
		{
			if (InElapsed < Timeout)
			{
				return false;
			}
			Test->AddError(FString::Printf(TEXT("%s (phase %d, %.1f s)"), What, Phase, InElapsed));
			return true;
		}

		FAutomationTestBase* Test;
		double CreatedAt;
		int32 Phase = 0;
		double PhaseStart = -1.0;
		double Now = 0.0;
		double Elapsed = 0.0;
	};

	// ---- Golmok.Zone.IndexDiscover -------------------------------------------------------------------------------

	class FIndexDiscoverScenario : public FZoneScenarioBase
	{
	public:
		explicit FIndexDiscoverScenario(FAutomationTestBase* InTest) : FZoneScenarioBase(InTest) {}

		virtual bool Update() override
		{
			bool bDone = false;
			UWorld* World = BeginUpdate(bDone);
			if (!World)
			{
				return bDone;
			}
			UGolmokZoneSubsystem* Subsystem = World->GetSubsystem<UGolmokZoneSubsystem>();
			if (!Subsystem)
			{
				Test->AddError(TEXT("no UGolmokZoneSubsystem in the PIE world"));
				return true;
			}

			switch (Phase)
			{
			case 0: // let PIE settle (player spawned, index loaded in OnWorldBeginPlay)
				if (Elapsed < 0.5)
				{
					return false;
				}
				Test->AddInfo(Subsystem->DescribeIndex());
				if (!Test->TestTrue(TEXT("discovery active (bDiscoverFromIndex, Content/Golmok/Zones/index/zones.json parsed, game world)"),
						Subsystem->IsDiscoveryActive()))
				{
					return true;
				}
				Deadline = static_cast<double>(Subsystem->DiscoveryIntervalSeconds) + 1.0;
				return Next(1);

			case 1: // z_synthetic_002 discovered (its cell is in the 3x3 around the level origin)
			{
				AGolmokZone* Second = Subsystem->FindZone(SecondZoneId);
				if (!Second)
				{
					return Fail(TEXT("z_synthetic_002 not discovered from the index (is Content/Golmok/Zones/index synced and the level origin at 126.923 / 37.560?)"),
						Deadline, Elapsed);
				}
				Test->AddInfo(FString::Printf(TEXT("z_synthetic_002 discovered after %.2f s"), Elapsed));
				Test->TestTrue(TEXT("discovered actor has bSpawnedFromIndex"), Second->bSpawnedFromIndex);
				Test->TestTrue(TEXT("discovered actor is RF_Transient"), Second->HasAnyFlags(RF_Transient));
				int32 NumExterior = 0;
				bool bExteriorPlaced = true;
				for (TActorIterator<AGolmokZone> It(World); It; ++It)
				{
					if (It->ZoneId == ExteriorZoneId)
					{
						++NumExterior;
						bExteriorPlaced = bExteriorPlaced && !It->bSpawnedFromIndex;
					}
				}
				Test->TestEqual(TEXT("exactly one z_synthetic_001 actor (the placed one wins; no discovered twin)"), NumExterior, 1);
				Test->TestTrue(TEXT("z_synthetic_001 actor is the level-placed one"), bExteriorPlaced);
				Test->TestTrue(TEXT("NumDiscovered() >= 1"), Subsystem->NumDiscovered() >= 1);
				const FString List = Subsystem->DescribeZones();
				Test->AddInfo(List);
				Test->TestTrue(TEXT("golmok.zone.list marks discovered rows [index]"), List.Contains(TEXT(" [index]")));
				Test->TestTrue(TEXT("golmok.zone.list marks placed rows [placed]"), List.Contains(TEXT(" [placed]")));
				Test->TestTrue(TEXT("golmok.zone.list header has the discovered column"), List.Contains(TEXT(" discovered, ")));
				const bool bExec = GEngine && GEngine->Exec(World, TEXT("golmok.zone.index"));
				Test->AddInfo(FString::Printf(TEXT("golmok.zone.index via GEngine->Exec: %s"), bExec ? TEXT("handled") : TEXT("not handled")));
				Test->AddInfo(Subsystem->DescribeIndex());

				// Walk away: 3 km east is outside the 3x3 cells and farther than 2 x UnloadRadiusM (500 m); no grace.
				Subsystem->DespawnGraceSeconds = 0.f;
				if (APawn* Pawn = UGameplayStatics::GetPlayerPawn(World, 0))
				{
					Pawn->SetActorLocation(Pawn->GetActorLocation() + FVector(300000.0, 0.0, 0.0), false, nullptr, ETeleportType::TeleportPhysics);
				}
				else
				{
					Test->AddError(TEXT("no player pawn to move"));
					return true;
				}
				Subsystem->Evaluate();
				Subsystem->DiscoverZones(); // first pass: the despawn conditions start holding
				return Next(2);
			}

			case 2: // next tick: second pass destroys the far discovered zone
			{
				Subsystem->DiscoverZones();
				Test->AddInfo(Subsystem->DescribeZones());
				Test->TestNull(TEXT("z_synthetic_002 despawned after two discovery passes 3 km away"), Subsystem->FindZone(SecondZoneId));
				Test->TestNotNull(TEXT("placed z_synthetic_001 kept"), Subsystem->FindZone(ExteriorZoneId));
				Test->TestEqual(TEXT("no re-entrancy violations"), Subsystem->GetReentrancyViolations(), 0);
				return true;
			}

			default:
				return true;
			}
		}

	private:
		double Deadline = 3.0;
	};

	// ---- Golmok.Zone.AsyncLoad ----------------------------------------------------------------------------------

	class FAsyncLoadScenario : public FZoneScenarioBase
	{
	public:
		explicit FAsyncLoadScenario(FAutomationTestBase* InTest) : FZoneScenarioBase(InTest) {}

		virtual bool Update() override
		{
			bool bDone = false;
			UWorld* World = BeginUpdate(bDone);
			if (!World)
			{
				return bDone;
			}
			UGolmokZoneSubsystem* Subsystem = World->GetSubsystem<UGolmokZoneSubsystem>();
			if (!Subsystem)
			{
				Test->AddError(TEXT("no UGolmokZoneSubsystem in the PIE world"));
				return true;
			}

			switch (Phase)
			{
			case 0: // settle
				if (Elapsed < 0.5)
				{
					return false;
				}
				return Next(1);

			case 1: // spawn + Load: async (assets exist) or synchronous fallback (no assets)
			{
				AGolmokZone* Zone = SpawnTestZone(Test, World);
				if (!Zone)
				{
					return true;
				}
				ZoneActor = Zone;
				Test->TestTrue(TEXT("manifest parsed"), Zone->EnsureManifest());
				int32 Missing = 0;
				const int32 NumAssets = Zone->CollectAssetPaths(Missing).Num();
				Test->AddInfo(FString::Printf(TEXT("asset packages: %d existing, %d missing"), NumAssets, Missing));
				Test->TestTrue(TEXT("Load() returns true"), Zone->Load());
				if (NumAssets > 0)
				{
					Test->TestTrue(TEXT("Load() went Loading (async)"), Zone->IsLoading());
					Test->TestEqual(TEXT("no portals while Loading"), Zone->GetPortalActors().Num(), 0);
					FString Msg;
					Test->TestTrue(TEXT("RequestLoad while Loading"), Subsystem->RequestLoad(ExteriorZoneId, /*bPin*/ false, Msg));
					Test->AddInfo(Msg);
					Test->TestTrue(TEXT("RequestLoad reports 'loading'"), Msg.Contains(TEXT("loading")));
					return Next(2);
				}
				const int32 Wanted = Zone->Manifest.Layers.Visual.Chunks.Num() + FMath::Max(1, Zone->Manifest.Layers.Collision.Chunks.Num());
				Test->AddInfo(TEXT("no assets: synchronous fallback exercised"));
				Test->TestTrue(TEXT("Load() went Loaded at once (synchronous fallback)"), Zone->IsLoaded());
				Test->TestEqual(TEXT("MissingAssetCount == chunks + collision"), Zone->MissingAssetCount, Wanted);
				Test->TestEqual(TEXT("MissingAssetCount == CollectAssetPaths missing"), Zone->MissingAssetCount, Missing);
				Test->TestEqual(TEXT("AsyncLoadCount == 0"), Zone->AsyncLoadCount, 0);
				return Next(3);
			}

			case 2: // async completion within AsyncTimeoutSeconds
			{
				AGolmokZone* Zone = ZoneActor.Get();
				if (!Zone)
				{
					Test->AddError(TEXT("zone actor disappeared while Loading"));
					return true;
				}
				if (!Zone->IsLoaded())
				{
					return Fail(TEXT("zone still not Loaded after the async request"), AsyncTimeoutSeconds, Elapsed);
				}
				Test->AddInfo(FString::Printf(TEXT("async load finished after %.2f s: missing %d, error '%s'"), Elapsed, Zone->MissingAssetCount, *Zone->LastError));
				Test->TestEqual(TEXT("AsyncLoadCount == 1"), Zone->AsyncLoadCount, 1);
				Test->TestEqual(TEXT("one portal spawned by FinishAsyncLoad"), Zone->GetPortalActors().Num(), 1);
				Test->TestTrue(TEXT("GetLoadingSeconds() == 0 once Loaded"), Zone->GetLoadingSeconds() == 0.0);
				Test->TestFalse(TEXT("no finish pending"), Zone->IsFinishPending());
				Test->TestTrue(TEXT("golmok.zone.list shows loaded"), ZoneRow(Subsystem, ExteriorZoneId).Contains(TEXT(" loaded ")));
				return Next(3);
			}

			case 3: // unload
			{
				AGolmokZone* Zone = ZoneActor.Get();
				if (!Zone)
				{
					Test->AddError(TEXT("zone actor disappeared"));
					return true;
				}
				Zone->Unload();
				Test->TestTrue(TEXT("Unloaded after Unload()"), Zone->State == EGolmokZoneState::Unloaded);
				Test->TestEqual(TEXT("Unload() empties the portal list"), Zone->GetPortalActors().Num(), 0);
				Test->TestEqual(TEXT("no re-entrancy violations"), Subsystem->GetReentrancyViolations(), 0);
				Zone->Destroy();
				return true;
			}

			default:
				return true;
			}
		}

	private:
		TWeakObjectPtr<AGolmokZone> ZoneActor;
	};

	// ---- Golmok.Zone.AsyncCancel --------------------------------------------------------------------------------

	class FAsyncCancelScenario : public FZoneScenarioBase
	{
	public:
		explicit FAsyncCancelScenario(FAutomationTestBase* InTest) : FZoneScenarioBase(InTest) {}

		virtual bool Update() override
		{
			bool bDone = false;
			UWorld* World = BeginUpdate(bDone);
			if (!World)
			{
				return bDone;
			}
			UGolmokZoneSubsystem* Subsystem = World->GetSubsystem<UGolmokZoneSubsystem>();
			if (!Subsystem)
			{
				Test->AddError(TEXT("no UGolmokZoneSubsystem in the PIE world"));
				return true;
			}

			switch (Phase)
			{
			case 0: // settle
				if (Elapsed < 0.5)
				{
					return false;
				}
				return Next(1);

			case 1: // Load then Unload in the same tick = cancel
			{
				AGolmokZone* Zone = SpawnTestZone(Test, World);
				if (!Zone)
				{
					return true;
				}
				ZoneActor = Zone;
				Test->TestTrue(TEXT("manifest parsed"), Zone->EnsureManifest());
				int32 Missing = 0;
				const int32 NumAssets = Zone->CollectAssetPaths(Missing).Num();
				Test->AddInfo(FString::Printf(TEXT("asset packages: %d existing, %d missing"), NumAssets, Missing));
				if (NumAssets == 0)
				{
					Test->AddInfo(TEXT("no assets: synchronous fallback, no cancel path to exercise"));
					Test->TestTrue(TEXT("Load() (synchronous fallback)"), Zone->Load());
					Zone->Unload();
					Test->TestEqual(TEXT("no re-entrancy violations"), Subsystem->GetReentrancyViolations(), 0);
					Zone->Destroy();
					return true;
				}
				Test->TestTrue(TEXT("Load() returns true"), Zone->Load());
				Test->TestTrue(TEXT("Load() went Loading"), Zone->IsLoading());
				Zone->Unload();
				Test->TestTrue(TEXT("Unload() while Loading -> Unloaded (cancelled)"), Zone->State == EGolmokZoneState::Unloaded);
				Test->TestFalse(TEXT("no finish pending after the cancel"), Zone->IsFinishPending());
				return Next(2);
			}

			case 2: // 1 s later nothing arrived from the cancelled request; load again
			{
				if (Elapsed < 1.0)
				{
					return false;
				}
				AGolmokZone* Zone = ZoneActor.Get();
				if (!Zone)
				{
					Test->AddError(TEXT("zone actor disappeared"));
					return true;
				}
				Test->TestTrue(TEXT("still Unloaded 1 s after the cancel"), Zone->State == EGolmokZoneState::Unloaded);
				Test->TestEqual(TEXT("no components built from the cancelled request"), NumPrimitiveComponents(Zone), 0);
				Test->TestEqual(TEXT("AsyncLoadCount == 0 after the cancel"), Zone->AsyncLoadCount, 0);
				Test->TestTrue(TEXT("Load() again"), Zone->Load());
				Test->TestTrue(TEXT("Loading again (new serial)"), Zone->IsLoading());
				return Next(3);
			}

			case 3: // the second request completes; then Destroy() while Loading
			{
				AGolmokZone* Zone = ZoneActor.Get();
				if (!Zone)
				{
					Test->AddError(TEXT("zone actor disappeared while Loading"));
					return true;
				}
				if (!Zone->IsLoaded())
				{
					return Fail(TEXT("zone not Loaded after the second async request"), AsyncTimeoutSeconds, Elapsed);
				}
				Test->AddInfo(FString::Printf(TEXT("second request finished after %.2f s"), Elapsed));
				Test->TestEqual(TEXT("AsyncLoadCount == 1 (the cancelled request never finished)"), Zone->AsyncLoadCount, 1);
				Zone->Unload();
				Test->TestTrue(TEXT("Load() a third time"), Zone->Load());
				Test->TestTrue(TEXT("Loading before Destroy()"), Zone->IsLoading());
				Zone->Destroy(); // EndPlay -> UnregisterZone + Unload() (cancel) while the request is in flight
				return Next(4);
			}

			case 4: // 1 s later: no error / ensure from the destroyed zone's request
			{
				if (Elapsed < 1.0)
				{
					return false;
				}
				Test->TestFalse(TEXT("destroyed zone actor is gone"), ZoneActor.IsValid());
				Test->TestEqual(TEXT("no re-entrancy violations"), Subsystem->GetReentrancyViolations(), 0);
				return true;
			}

			default:
				return true;
			}
		}

	private:
		TWeakObjectPtr<AGolmokZone> ZoneActor;
	};

	// ---- Golmok.Zone.InteriorNotBlocked -------------------------------------------------------------------------

	class FInteriorNotBlockedScenario : public FZoneScenarioBase
	{
	public:
		explicit FInteriorNotBlockedScenario(FAutomationTestBase* InTest) : FZoneScenarioBase(InTest) {}

		virtual bool Update() override
		{
			bool bDone = false;
			UWorld* World = BeginUpdate(bDone);
			if (!World)
			{
				return bDone;
			}
			UGolmokZoneSubsystem* Subsystem = World->GetSubsystem<UGolmokZoneSubsystem>();
			if (!Subsystem)
			{
				Test->AddError(TEXT("no UGolmokZoneSubsystem in the PIE world"));
				return true;
			}

			switch (Phase)
			{
			case 0: // settle, discover, request the interior as a portal would
			{
				if (Elapsed < 0.5)
				{
					return false;
				}
				Subsystem->DiscoverZones();
				AGolmokZone* Interior = Subsystem->FindZone(InteriorZoneId);
				if (!Interior)
				{
					Test->AddInfo(TEXT("skipped: no z_synthetic_001_interior actor (placed or discovered from the index)"));
					return true;
				}
				InteriorActor = Interior;
				FString Msg;
				Test->TestTrue(TEXT("RequestLoad(interior, pinned, Portal)"),
					Subsystem->RequestLoad(InteriorZoneId, /*bPin*/ true, Msg, EGolmokZoneRequestSource::Portal));
				Test->AddInfo(Msg);
				return Next(1);
			}

			case 1: // loaded within AsyncTimeoutSeconds, then the portal-sourced unload
			{
				AGolmokZone* Interior = InteriorActor.Get();
				if (!Interior)
				{
					Test->AddError(TEXT("interior zone actor disappeared"));
					return true;
				}
				if (!Interior->IsLoaded())
				{
					return Fail(TEXT("interior not Loaded after RequestLoad"), AsyncTimeoutSeconds, Elapsed);
				}
				FString Msg;
				Test->TestTrue(TEXT("RequestUnload(interior, Portal)"), Subsystem->RequestUnload(InteriorZoneId, Msg, EGolmokZoneRequestSource::Portal));
				Test->AddInfo(Msg);
				FString Row = ZoneRow(Subsystem, InteriorZoneId);
				Test->AddInfo(Row);
				Test->TestTrue(TEXT("row shows ' portal' after a portal unload"), Row.Contains(TEXT(" portal")));
				Test->TestFalse(TEXT("row never shows ' blocked' after a portal unload"), Row.Contains(TEXT(" blocked")));
				Test->TestTrue(TEXT("row shows ' [placed]' or ' [index]'"), Row.Contains(TEXT(" [placed]")) || Row.Contains(TEXT(" [index]")));
				for (int32 i = 0; i < 3; ++i)
				{
					Subsystem->Evaluate();
				}
				Test->TestFalse(TEXT("Evaluate() leaves a portal-managed interior alone (no automatic reload)"), Interior->IsLoadedOrLoading());

				// Regression: the console path still blocks, and a console load clears the portal mark.
				Test->TestTrue(TEXT("RequestUnload(interior, Console)"), Subsystem->RequestUnload(InteriorZoneId, Msg, EGolmokZoneRequestSource::Console));
				Row = ZoneRow(Subsystem, InteriorZoneId);
				Test->AddInfo(Row);
				Test->TestTrue(TEXT("row shows ' blocked' after a console unload"), Row.Contains(TEXT(" blocked")));
				Test->TestFalse(TEXT("row drops ' portal' after a console unload"), Row.Contains(TEXT(" portal")));
				Test->TestTrue(TEXT("RequestLoad(interior, Console)"),
					Subsystem->RequestLoad(InteriorZoneId, /*bPin*/ false, Msg, EGolmokZoneRequestSource::Console));
				Test->AddInfo(Msg);
				Row = ZoneRow(Subsystem, InteriorZoneId);
				Test->AddInfo(Row);
				Test->TestFalse(TEXT("row has no ' portal' after a console load"), Row.Contains(TEXT(" portal")));
				Test->TestFalse(TEXT("row has no ' blocked' after a console load"), Row.Contains(TEXT(" blocked")));
				Subsystem->RequestUnload(InteriorZoneId, Msg, EGolmokZoneRequestSource::Console);
				Test->TestEqual(TEXT("no re-entrancy violations"), Subsystem->GetReentrancyViolations(), 0);
				return true;
			}

			default:
				return true;
			}
		}

	private:
		TWeakObjectPtr<AGolmokZone> InteriorActor;
	};
} // namespace GolmokZoneTest

// ---- Golmok.Zone.IndexParse (no PIE) ------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokZoneIndexParseTest, "Golmok.Zone.IndexParse",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokZoneIndexParseTest::RunTest(const FString& Parameters)
{
	using namespace GolmokZoneTest;

	// 1) zones.json example: every field.
	{
		TArray<FGolmokZoneIndexEntry> Entries;
		FString Error;
		TestTrue(TEXT("ParseZonesText(example)"), FGolmokZoneIndex::ParseZonesText(ZonesJson, Entries, Error));
		TestTrue(TEXT("no error"), Error.IsEmpty());
		if (TestEqual(TEXT("three entries"), Entries.Num(), 3))
		{
			TestEqual(TEXT("[0].Id"), Entries[0].Id, FString(ExteriorZoneId));
			TestEqual(TEXT("[0].Version"), Entries[0].Version, 1);
			TestTrue(TEXT("[0].Kind exterior"), Entries[0].Kind == EGolmokZoneKind::Exterior);
			TestEqual(TEXT("[0].Priority"), Entries[0].Priority, 10);
			TestTrue(TEXT("[0].West"), FMath::IsNearlyEqual(Entries[0].West, 126.924773635, 1e-12));
			TestTrue(TEXT("[0].South"), FMath::IsNearlyEqual(Entries[0].South, 37.561909901, 1e-12));
			TestTrue(TEXT("[0].East"), FMath::IsNearlyEqual(Entries[0].East, 126.925226365, 1e-12));
			TestTrue(TEXT("[0].North"), FMath::IsNearlyEqual(Entries[0].North, 37.562090099, 1e-12));
			TestEqual(TEXT("[0].ManifestRel"), Entries[0].ManifestRel, FString(TEXT("z_synthetic_001/v1/manifest.json")));
			TestEqual(TEXT("[1].Id"), Entries[1].Id, FString(InteriorZoneId));
			TestTrue(TEXT("[1].Kind interior"), Entries[1].Kind == EGolmokZoneKind::Interior);
			TestEqual(TEXT("[1].Priority"), Entries[1].Priority, 20);
			TestEqual(TEXT("[2].Id"), Entries[2].Id, FString(SecondZoneId));
			TestEqual(TEXT("[2].ManifestRel"), Entries[2].ManifestRel, FString(TEXT("z_synthetic_002/v1/manifest.json")));
		}
	}

	// 2) cell example (16/55874/25379): every field, winning order kept.
	{
		FGolmokZoneIndexCell Cell;
		FString Error;
		const FString Text = CellJson(55874, 25379, {{InteriorZoneId, 1}, {ExteriorZoneId, 1}, {SecondZoneId, 1}});
		TestTrue(TEXT("ParseCellText(example)"), FGolmokZoneIndex::ParseCellText(Text, Cell, Error));
		TestTrue(TEXT("no error"), Error.IsEmpty());
		TestEqual(TEXT("cell zoom"), Cell.Zoom, 16);
		TestEqual(TEXT("cell x"), Cell.X, 55874);
		TestEqual(TEXT("cell y"), Cell.Y, 25379);
		TestTrue(TEXT("cell bFromFile"), Cell.bFromFile);
		if (TestEqual(TEXT("three rows"), Cell.Zones.Num(), 3))
		{
			TestEqual(TEXT("row 0 = interior (priority 20 first)"), Cell.Zones[0].Id, FString(InteriorZoneId));
			TestEqual(TEXT("row 1 = 001"), Cell.Zones[1].Id, FString(ExteriorZoneId));
			TestEqual(TEXT("row 2 = 002"), Cell.Zones[2].Id, FString(SecondZoneId));
			TestEqual(TEXT("row 2 version"), Cell.Zones[2].Version, 1);
		}
	}

	// 3) eight error cases: false + non-empty error.
	{
		const FString Base(ZonesJson);
		const TCHAR* Bbox002 = TEXT("[126.927082506, 37.56199099, 126.927444694, 37.562144159]");
		struct FCase
		{
			const TCHAR* Name;
			FString Text;
		};
		const FCase Cases[] = {
			{TEXT("schema_version 2"), Base.Replace(TEXT("\"schema_version\": 1"), TEXT("\"schema_version\": 2"))},
			{TEXT("cell_zoom 15"), Base.Replace(TEXT("\"cell_zoom\": 16"), TEXT("\"cell_zoom\": 15"))},
			{TEXT("bad id"), Base.Replace(TEXT("\"id\": \"z_synthetic_002\""), TEXT("\"id\": \"Bad-Id\""))},
			{TEXT("bbox with 3 numbers"), Base.Replace(Bbox002, TEXT("[126.927082506, 37.56199099, 126.927444694]"))},
			{TEXT("west > east"), Base.Replace(Bbox002, TEXT("[126.928, 37.56199099, 126.927, 37.562144159]"))},
			{TEXT("version 0"), Base.Replace(TEXT("\"id\": \"z_synthetic_002\", \"version\": 1"), TEXT("\"id\": \"z_synthetic_002\", \"version\": 0"))},
			{TEXT("duplicate id"), Base.Replace(TEXT("z_synthetic_002"), TEXT("z_synthetic_001"))},
		};
		for (const FCase& Case : Cases)
		{
			TArray<FGolmokZoneIndexEntry> Entries;
			FString Error;
			TestFalse(FString::Printf(TEXT("ParseZonesText rejects: %s"), Case.Name), FGolmokZoneIndex::ParseZonesText(Case.Text, Entries, Error));
			TestFalse(FString::Printf(TEXT("error text set: %s"), Case.Name), Error.IsEmpty());
			AddInfo(FString::Printf(TEXT("%s -> %s"), Case.Name, *Error));
		}
		FGolmokZoneIndexCell Cell;
		FString Error;
		TestFalse(TEXT("ParseCellText rejects z != 16"), FGolmokZoneIndex::ParseCellText(CellJson(1, 2, {{ExteriorZoneId, 1}}, /*Z*/ 15), Cell, Error));
		TestFalse(TEXT("error text set: cell z 15"), Error.IsEmpty());
		AddInfo(FString::Printf(TEXT("cell z 15 -> %s"), *Error));
	}

	// 4) file name + cell formula (spec section 6 example values).
	TestEqual(TEXT("CellFileName(55873, 25379)"), FGolmokZoneIndex::CellFileName(55873, 25379), FString(TEXT("16_55873_25379.json")));
	{
		int32 X = 0, Y = 0;
		GolmokGeoMath::LonLatToCell(126.9250, 37.5620, 16, X, Y);
		TestEqual(TEXT("cell x of the 001 origin"), X, 55873);
		TestEqual(TEXT("cell y of the 001 origin"), Y, 25379);
		GolmokGeoMath::LonLatToCell(126.9272636, 37.5620, 16, X, Y);
		TestEqual(TEXT("cell x 200 m east (next cell)"), X, 55874);
		TestEqual(TEXT("cell y 200 m east"), Y, 25379);
	}

	// 5) in-memory reader: one read per cell, missing file = empty cell, cached; CollectAround; version mismatch.
	{
		TMap<FString, FString> Files;
		Files.Add(FGolmokZoneIndex::CellFilePath(MemIndexDir, 55873, 25379), CellJson(55873, 25379, {{InteriorZoneId, 1}, {ExteriorZoneId, 1}}));
		Files.Add(FGolmokZoneIndex::CellFilePath(MemIndexDir, 55873, 25380), CellJson(55873, 25380, {{ExteriorZoneId, 1}}));
		Files.Add(FGolmokZoneIndex::CellFilePath(MemIndexDir, 55874, 25379), CellJson(55874, 25379, {{InteriorZoneId, 1}, {ExteriorZoneId, 1}, {SecondZoneId, 1}}));
		Files.Add(FGolmokZoneIndex::CellFilePath(MemIndexDir, 55874, 25380), CellJson(55874, 25380, {{ExteriorZoneId, 1}, {SecondZoneId, 1}}));
		// A cell whose only row names a version zones.json does not have: reported once, skipped.
		Files.Add(FGolmokZoneIndex::CellFilePath(MemIndexDir, 55872, 25381), CellJson(55872, 25381, {{SecondZoneId, 2}}));
		int32 Reads = 0;
		FGolmokZoneIndex Index([&Files, &Reads](const FString& InFilePath, FString& OutText)
		{
			++Reads;
			if (const FString* Text = Files.Find(InFilePath))
			{
				OutText = *Text;
				return true;
			}
			return false;
		});
		FString Error;
		TestTrue(TEXT("LoadFromText(mem:/index)"), Index.LoadFromText(MemIndexDir, ZonesJson, Error));
		TestTrue(TEXT("index available"), Index.IsAvailable());
		TestEqual(TEXT("NumZones"), Index.NumZones(), 3);
		TestNotNull(TEXT("FindZone(002)"), Index.FindZone(SecondZoneId));
		TestNull(TEXT("FindZone(unknown)"), Index.FindZone(TEXT("z_nope")));
		TestEqual(TEXT("LoadFromText reads no file"), Index.NumFileReads(), 0);

		const FGolmokZoneIndexCell& A = Index.GetCell(55873, 25379);
		TestTrue(TEXT("cell from file"), A.bFromFile);
		TestEqual(TEXT("cell rows"), A.Zones.Num(), 2);
		Index.GetCell(55873, 25379);
		TestEqual(TEXT("GetCell twice == one read"), Index.NumFileReads(), 1);
		TestEqual(TEXT("reader called once"), Reads, 1);

		const FGolmokZoneIndexCell& Missing = Index.GetCell(55870, 25370);
		TestFalse(TEXT("missing cell: bFromFile == false"), Missing.bFromFile);
		TestEqual(TEXT("missing cell: no zones"), Missing.Zones.Num(), 0);
		TestTrue(TEXT("missing cell: no error (a missing file is a normal empty cell)"), Missing.Error.IsEmpty());
		TestEqual(TEXT("missing cell read once"), Index.NumFileReads(), 2);
		Index.GetCell(55870, 25370);
		TestEqual(TEXT("missing cell cached (no second read)"), Index.NumFileReads(), 2);
		TestEqual(TEXT("NumMissingCells"), Index.NumMissingCells(), 1);

		TArray<FGolmokZoneIndexCellRef> Near;
		TArray<FString> Warnings;
		Index.CollectAround(55873, 25380, 1, Near, &Warnings);
		if (TestEqual(TEXT("CollectAround(55873, 25380, 1): three zones, no duplicates"), Near.Num(), 3))
		{
			TestEqual(TEXT("near[0]"), Near[0].Id, FString(InteriorZoneId));
			TestEqual(TEXT("near[1]"), Near[1].Id, FString(ExteriorZoneId));
			TestEqual(TEXT("near[2]"), Near[2].Id, FString(SecondZoneId));
		}
		TestEqual(TEXT("no warnings in the 3x3 around the level origin"), Warnings.Num(), 0);
		AddInfo(Index.Describe(55873, 25380, 1));

		TArray<FGolmokZoneIndexCellRef> Mismatched;
		TArray<FString> MismatchWarnings;
		Index.CollectAround(55872, 25381, 0, Mismatched, &MismatchWarnings);
		TestEqual(TEXT("version-mismatched row skipped"), Mismatched.Num(), 0);
		TestEqual(TEXT("version-mismatched row reported once"), MismatchWarnings.Num(), 1);
		Index.CollectAround(55872, 25381, 0, Mismatched, &MismatchWarnings);
		TestEqual(TEXT("not reported again"), MismatchWarnings.Num(), 1);
		for (const FString& Warning : MismatchWarnings)
		{
			AddInfo(Warning);
		}
	}

	// 6) the committed Content index, when present.
	{
		FGolmokZoneIndex Disk;
		FString Error;
		if (Disk.Load(FGolmokZoneIndex::DefaultIndexDir(), Error))
		{
			TestEqual(TEXT("Content/Golmok/Zones/index/zones.json: 3 zones"), Disk.NumZones(), 3);
			AddInfo(FString::Printf(TEXT("content index %s: %d zones"), *Disk.GetIndexDir(), Disk.NumZones()));
		}
		else
		{
			TestTrue(TEXT("a missing content index is silent (empty error)"), Error.IsEmpty());
			AddInfo(FString::Printf(TEXT("no content index at %s (run zone_index.sync)"), *FGolmokZoneIndex::DefaultIndexDir()));
		}
	}
	return true;
}

// ---- PIE tests -----------------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokZoneIndexDiscoverTest, "Golmok.Zone.IndexDiscover",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokZoneIndexDiscoverTest::RunTest(const FString& Parameters)
{
	using namespace GolmokZoneTest;

	if (!FPackageName::DoesPackageExist(ZoneTestMap))
	{
		AddInfo(TEXT("skipped: run synthetic_zone.run()"));
		return true;
	}

	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(ZoneTestMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FIndexDiscoverScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokZoneAsyncLoadTest, "Golmok.Zone.AsyncLoad",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokZoneAsyncLoadTest::RunTest(const FString& Parameters)
{
	using namespace GolmokZoneTest;

	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddInfo(TEXT("skipped: run golmok.setup_dev_level in the editor first"));
		return true;
	}

	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FAsyncLoadScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokZoneAsyncCancelTest, "Golmok.Zone.AsyncCancel",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokZoneAsyncCancelTest::RunTest(const FString& Parameters)
{
	using namespace GolmokZoneTest;

	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddInfo(TEXT("skipped: run golmok.setup_dev_level in the editor first"));
		return true;
	}

	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FAsyncCancelScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokZoneInteriorNotBlockedTest, "Golmok.Zone.InteriorNotBlocked",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokZoneInteriorNotBlockedTest::RunTest(const FString& Parameters)
{
	using namespace GolmokZoneTest;

	if (!FPackageName::DoesPackageExist(ZoneTestMap))
	{
		AddInfo(TEXT("skipped: run synthetic_zone.run()"));
		return true;
	}

	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(ZoneTestMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FInteriorNotBlockedScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

#endif
