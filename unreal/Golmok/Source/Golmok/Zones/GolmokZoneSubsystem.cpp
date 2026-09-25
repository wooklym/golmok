#include "Zones/GolmokZoneSubsystem.h"

#include "Golmok.h"

#include "Camera/PlayerCameraManager.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "Geo/GolmokGeoMath.h"
#include "Geo/GolmokGeoSubsystem.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "Zones/GolmokZone.h"

namespace
{
	/**
	 * RAII guard for UGolmokZoneSubsystem::PointerHoldDepth: while alive, Evaluate() holds FGolmokZoneRecord pointers
	 * into Zones across Load() / Unload(), so RegisterZone / UnregisterZone / RequestLoad / RequestUnload /
	 * DiscoverZones / the async finish step must not run (they would reallocate the array or re-grab records).
	 */
	struct FPointerHoldScope
	{
		explicit FPointerHoldScope(int32& InDepth) : Depth(InDepth) { ++Depth; }
		~FPointerHoldScope() { --Depth; }
		FPointerHoldScope(const FPointerHoldScope&) = delete;
		FPointerHoldScope& operator=(const FPointerHoldScope&) = delete;
		int32& Depth;
	};
} // namespace

// ---- lifecycle ------------------------------------------------------------------------------------------------

bool UGolmokZoneSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	// Runtime streaming only. Editor worlds use AGolmokZone::RebuildInEditor explicitly.
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UGolmokZoneSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	if (UnloadRadiusM <= LoadRadiusM)
	{
		UE_LOG(LogGolmok, Warning, TEXT("GolmokZoneSubsystem: UnloadRadiusM (%.0f) must exceed LoadRadiusM (%.0f); using LoadRadiusM + 100."),
			UnloadRadiusM, LoadRadiusM);
		UnloadRadiusM = LoadRadiusM + 100.f;
	}
	UpdateIntervalSeconds = FMath::Max(0.1f, UpdateIntervalSeconds);
	MaxLoadsPerUpdate = FMath::Max(1, MaxLoadsPerUpdate);
	MaxUnloadsPerUpdate = FMath::Max(1, MaxUnloadsPerUpdate);
	// WP-09 discovery keys: never look up the index more often than the evaluation itself; a despawn distance inside
	// the unload radius would destroy zones the distance rule still wants (0 keeps "2 x UnloadRadiusM").
	DiscoveryIntervalSeconds = FMath::Max(DiscoveryIntervalSeconds, UpdateIntervalSeconds);
	if (DespawnDistanceM > 0.f && DespawnDistanceM < UnloadRadiusM)
	{
		UE_LOG(LogGolmok, Warning, TEXT("GolmokZoneSubsystem: DespawnDistanceM (%.0f) must not be inside UnloadRadiusM (%.0f); using UnloadRadiusM."),
			DespawnDistanceM, UnloadRadiusM);
		DespawnDistanceM = UnloadRadiusM;
	}
	DespawnGraceSeconds = FMath::Max(0.f, DespawnGraceSeconds);
	const UWorld* World = GetWorld();
	Streamable.SetManagerName(FString::Printf(TEXT("GolmokZones:%s"), World ? *World->GetName() : TEXT("?")));
	// Streamed sublevels bring basemap actors in and out: rescan the tagged-actor cache when that happens.
	LevelAddedHandle = FWorldDelegates::LevelAddedToWorld.AddUObject(this, &UGolmokZoneSubsystem::OnLevelChanged);
	LevelRemovedHandle = FWorldDelegates::LevelRemovedFromWorld.AddUObject(this, &UGolmokZoneSubsystem::OnLevelChanged);
}

void UGolmokZoneSubsystem::Deinitialize()
{
	// First: no streamable handle may outlive the manager (value member, destroyed with this object at GC).
	for (FGolmokZoneRecord& R : Zones)
	{
		if (AGolmokZone* Zone = R.Zone.Get())
		{
			Zone->CancelAsyncLoad();
		}
	}
	FWorldDelegates::LevelAddedToWorld.Remove(LevelAddedHandle);
	FWorldDelegates::LevelRemovedFromWorld.Remove(LevelRemovedHandle);
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(EvaluateTimer);
	}
	RestoreAllBasemap();
	Zones.Empty(); // discovered actors are not destroyed here: the world tears them down
	Basemap.Empty();
	Index.Reset();
	Super::Deinitialize();
}

void UGolmokZoneSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	// Level-placed zones register themselves in BeginPlay; sweep once in case any BeginPlay ran before ours.
	for (TActorIterator<AGolmokZone> It(&InWorld); It; ++It)
	{
		RegisterZone(*It);
	}
	bBasemapDirty = true;
	if (bDiscoverFromIndex)
	{
		const FString IndexDir = FGolmokZoneIndex::DefaultIndexDir();
		IndexLoadError.Reset();
		if (!Index.Load(IndexDir, IndexLoadError))
		{
			if (IndexLoadError.IsEmpty())
			{
				UE_LOG(LogGolmok, Log, TEXT("GolmokZoneSubsystem: no zone index at %s; discovery off"), *IndexDir);
			}
			else
			{
				UE_LOG(LogGolmok, Warning, TEXT("GolmokZoneSubsystem: zone index %s: %s; discovery off"), *IndexDir, *IndexLoadError);
			}
		}
		else
		{
			UE_LOG(LogGolmok, Log, TEXT("GolmokZoneSubsystem: zone index %s: %d zones; discovery every %.1f s"), *IndexDir, Index.NumZones(),
				DiscoveryIntervalSeconds);
		}
	}
	NextDiscoverySeconds = 0.0;
	InWorld.GetTimerManager().SetTimer(EvaluateTimer, this, &UGolmokZoneSubsystem::OnEvaluateTimer, UpdateIntervalSeconds, /*bLoop*/ true);
	UE_LOG(LogGolmok, Log, TEXT("GolmokZoneSubsystem: %d zones registered; load < %.0f m, unload > %.0f m, every %.2f s"), Zones.Num(),
		LoadRadiusM, UnloadRadiusM, UpdateIntervalSeconds);
}

void UGolmokZoneSubsystem::OnEvaluateTimer()
{
	const double Now = GetWorld()->GetTimeSeconds();
	if (IsDiscoveryActive() && Now >= NextDiscoverySeconds)
	{
		NextDiscoverySeconds = Now + DiscoveryIntervalSeconds;
		DiscoverZones();
	}
	Evaluate();
}

void UGolmokZoneSubsystem::OnLevelChanged(ULevel* Level, UWorld* World)
{
	if (World == GetWorld())
	{
		bBasemapDirty = true;
	}
}

// ---- registration ---------------------------------------------------------------------------------------------

void UGolmokZoneSubsystem::CheckNotHoldingPointers(const TCHAR* Op)
{
	if (PointerHoldDepth > 0)
	{
		++ReentrancyViolations;
		UE_LOG(LogGolmok, Error, TEXT("GolmokZoneSubsystem: %s called while zone record pointers are held (depth %d, violation %d)"), Op,
			PointerHoldDepth, ReentrancyViolations);
	}
}

void UGolmokZoneSubsystem::NoteAsyncFinish(const AGolmokZone* Zone)
{
	if (PointerHoldDepth > 0)
	{
		++ReentrancyViolations;
		UE_LOG(LogGolmok, Error, TEXT("GolmokZoneSubsystem: async finish of zone %s called while zone record pointers are held (depth %d, violation %d)"),
			Zone ? *Zone->ZoneId : TEXT("?"), PointerHoldDepth, ReentrancyViolations);
	}
}

void UGolmokZoneSubsystem::RegisterZone(AGolmokZone* Zone)
{
	if (!IsValid(Zone) || FindRecord(Zone))
	{
		return;
	}
	CheckNotHoldingPointers(TEXT("RegisterZone"));
	for (FGolmokZoneRecord& Other : Zones)
	{
		AGolmokZone* OtherZone = Other.Zone.Get();
		if (!OtherZone || OtherZone->ZoneId != Zone->ZoneId)
		{
			continue;
		}
		if (OtherZone->bSpawnedFromIndex == Zone->bSpawnedFromIndex)
		{
			if (OtherZone->Version == Zone->Version)
			{
				UE_LOG(LogGolmok, Warning, TEXT("GolmokZoneSubsystem: zone %s v%d is placed twice ('%s' and '%s')."), *Zone->ZoneId, Zone->Version,
					*OtherZone->GetName(), *Zone->GetName());
			}
		}
		else if (!Zone->bSpawnedFromIndex)
		{
			// A level-placed actor arrives after its discovered twin (streamed sublevel): the discovered one retires in
			// the next discovery pass. No array change and no actor destruction here (BeginPlay stack).
			Other.bRetirePending = true;
		}
	}
	FGolmokZoneRecord Record;
	Record.Zone = Zone;
	Zones.Add(Record);
	bBasemapDirty = true;
}

void UGolmokZoneSubsystem::UnregisterZone(AGolmokZone* Zone)
{
	CheckNotHoldingPointers(TEXT("UnregisterZone"));
	const int32 RecordIndex = Zones.IndexOfByPredicate([Zone](const FGolmokZoneRecord& R) { return R.Zone.Get() == Zone; });
	if (RecordIndex != INDEX_NONE)
	{
		Zones.RemoveAt(RecordIndex);
		bBasemapDirty = true;
	}
}

FGolmokZoneRecord* UGolmokZoneSubsystem::FindRecord(const AGolmokZone* Zone)
{
	return Zones.FindByPredicate([Zone](const FGolmokZoneRecord& R) { return R.Zone.Get() == Zone; });
}

AGolmokZone* UGolmokZoneSubsystem::FindZone(const FString& ZoneId) const
{
	// Level-placed actors win over discovered ones. Several versions of one zone may be placed while tuning; the
	// console addresses the highest placed version.
	AGolmokZone* Placed = nullptr;
	AGolmokZone* Discovered = nullptr;
	for (const FGolmokZoneRecord& R : Zones)
	{
		AGolmokZone* Zone = R.Zone.Get();
		if (!Zone || Zone->ZoneId != ZoneId)
		{
			continue;
		}
		if (!Zone->bSpawnedFromIndex)
		{
			if (!Placed || Zone->Version > Placed->Version)
			{
				Placed = Zone;
			}
		}
		else if (!Discovered)
		{
			Discovered = Zone;
		}
	}
	return Placed ? Placed : Discovered;
}

void UGolmokZoneSubsystem::PruneInvalid()
{
	const int32 Before = Zones.Num();
	Zones.RemoveAll([](const FGolmokZoneRecord& R) { return !R.Zone.IsValid(); });
	if (Zones.Num() != Before)
	{
		bBasemapDirty = true;
	}
}

int32 UGolmokZoneSubsystem::NumDiscovered() const
{
	int32 Count = 0;
	for (const FGolmokZoneRecord& R : Zones)
	{
		if (R.Zone.IsValid() && R.Zone->bSpawnedFromIndex)
		{
			++Count;
		}
	}
	return Count;
}

int32 UGolmokZoneSubsystem::NumLoading() const
{
	int32 Count = 0;
	for (const FGolmokZoneRecord& R : Zones)
	{
		if (R.Zone.IsValid() && R.Zone->IsLoading())
		{
			++Count;
		}
	}
	return Count;
}

int32 UGolmokZoneSubsystem::ResolveZoneVersion(const FString& ZoneId) const
{
	if (const AGolmokZone* Zone = FindZone(ZoneId))
	{
		return Zone->Version;
	}
	if (const FGolmokZoneIndexEntry* Entry = Index.FindZone(ZoneId))
	{
		return Entry->Version;
	}
	return 0;
}

// ---- evaluation -----------------------------------------------------------------------------------------------

bool UGolmokZoneSubsystem::GetPlayerLocation(FVector& OutLocation) const
{
	const UWorld* World = GetWorld();
	if (!World)
	{
		return false;
	}
	if (const APawn* Pawn = UGameplayStatics::GetPlayerPawn(World, 0))
	{
		OutLocation = Pawn->GetActorLocation();
		return true;
	}
	if (const APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(World, 0))
	{
		OutLocation = Camera->GetCameraLocation();
		return true;
	}
	return false;
}

void UGolmokZoneSubsystem::Evaluate()
{
	// Record pointers into Zones are held below across Load / Unload: nothing on that stack may register, unregister,
	// request, discover, spawn or destroy (WP-04 contract; counted by CheckNotHoldingPointers).
	FPointerHoldScope Hold(PointerHoldDepth);
	PruneInvalid();
	FVector Player;
	if (!GetPlayerLocation(Player))
	{
		if (!bWarnedNoPlayer)
		{
			bWarnedNoPlayer = true;
			UE_LOG(LogGolmok, Warning, TEXT("GolmokZoneSubsystem: no player pawn or camera yet; zones stay as they are."));
		}
		return;
	}
	bWarnedNoPlayer = false;
	const FVector2D PlayerXY(Player.X, Player.Y);

	TArray<FGolmokZoneRecord*> ToLoad;
	TArray<FGolmokZoneRecord*> ToUnload;
	bool bChanged = false;
	for (FGolmokZoneRecord& R : Zones)
	{
		AGolmokZone* Zone = R.Zone.Get();
		if (!Zone)
		{
			continue;
		}
		if (!Zone->HasManifest())
		{
			if (R.bLoadFailed)
			{
				continue;
			}
			if (!Zone->EnsureManifest())
			{
				R.bLoadFailed = true;
				UE_LOG(LogGolmok, Error, TEXT("GolmokZoneSubsystem: zone %s manifest failed: %s"), *Zone->ZoneId, *Zone->LastError);
				continue;
			}
		}
		// Cheap bounds distance first (a lower bound of the polygon distance); the polygon is only measured in the
		// ring where it can change the decision.
		const double BoundsM = Zone->DistanceToBoundsM(PlayerXY);
		R.LastDistanceM = BoundsM;
		R.bDistanceIsLowerBound = true;
		// Portal-managed interiors and discovered zones waiting to retire are outside the distance rules.
		const bool bManaged = Zone->bAutoManaged && (!Zone->IsInterior() || bAutoManageInterior) && !R.bLoadFailed && !R.bPortalManaged
							  && !R.bRetirePending;
		if (Zone->IsLoadedOrLoading())
		{
			// Loaded: distance bookkeeping and unload candidates. Loading (WP-09): the same bookkeeping; an unload of a
			// loading zone cancels its request.
			bool bFar = BoundsM >= UnloadRadiusM;
			if (!bFar)
			{
				R.LastDistanceM = Zone->DistanceToFootprintM(PlayerXY);
				R.bDistanceIsLowerBound = false;
				bFar = R.LastDistanceM >= UnloadRadiusM;
			}
			if (R.bBlocked && bFar)
			{
				R.bBlocked = false; // the player left; a console unload no longer sticks
			}
			// An interior zone whose parent exterior zone is registered but unloaded is cleaned up too (no portal left).
			bool bOrphanInterior = false;
			if (Zone->IsInterior() && !Zone->GetParentZoneId().IsEmpty())
			{
				if (const AGolmokZone* Parent = FindZone(Zone->GetParentZoneId()))
				{
					bOrphanInterior = !Parent->IsLoadedOrLoading();
				}
			}
			if (!R.bPinned && ((bManaged && bFar) || bOrphanInterior))
			{
				ToUnload.Add(&R);
			}
		}
		else
		{
			if (BoundsM > LoadRadiusM)
			{
				if (R.bBlocked && BoundsM >= UnloadRadiusM)
				{
					R.bBlocked = false;
				}
				continue; // far away: polygon not needed
			}
			R.LastDistanceM = Zone->DistanceToFootprintM(PlayerXY);
			R.bDistanceIsLowerBound = false;
			if (R.bBlocked && R.LastDistanceM >= UnloadRadiusM)
			{
				R.bBlocked = false;
			}
			if (bManaged && !R.bBlocked && R.LastDistanceM <= LoadRadiusM)
			{
				ToLoad.Add(&R);
			}
		}
	}

	// Farthest first, at most MaxUnloadsPerUpdate per step.
	ToUnload.Sort([](const FGolmokZoneRecord& A, const FGolmokZoneRecord& B) { return A.LastDistanceM > B.LastDistanceM; });
	for (int32 i = 0; i < ToUnload.Num() && i < MaxUnloadsPerUpdate; ++i)
	{
		if (AGolmokZone* Zone = ToUnload[i]->Zone.Get())
		{
			Zone->Unload();
			bChanged = true;
		}
	}

	// Nearest first, at most MaxLoadsPerUpdate loads (requests) per step; distance loads use the default priority.
	ToLoad.Sort([](const FGolmokZoneRecord& A, const FGolmokZoneRecord& B) { return A.LastDistanceM < B.LastDistanceM; });
	for (int32 i = 0; i < ToLoad.Num() && i < MaxLoadsPerUpdate; ++i)
	{
		AGolmokZone* Zone = ToLoad[i]->Zone.Get();
		if (!Zone)
		{
			continue;
		}
		Zone->SetAsyncLoadPriority(FStreamableManager::DefaultAsyncLoadPriority);
		if (Zone->Load())
		{
			bChanged = true; // Loaded, or Loading started (ResolveOverlaps only looks at IsLoaded)
		}
		else
		{
			ToLoad[i]->bLoadFailed = true;
			UE_LOG(LogGolmok, Error, TEXT("GolmokZoneSubsystem: zone %s failed to load: %s"), *Zone->ZoneId, *Zone->LastError);
		}
	}

	// Notify* already re-resolved on each change; a periodic rescan catches basemap actors from streamed sublevels.
	const double Now = FPlatformTime::Seconds();
	const bool bRescanDue = BasemapRescanSeconds > 0.f && (Now - LastBasemapScanSeconds) >= BasemapRescanSeconds;
	if (bChanged || bBasemapDirty || bRescanDue)
	{
		ResolveOverlaps();
		UpdateBasemapHiding();
	}
}

void UGolmokZoneSubsystem::NotifyZoneLoaded(AGolmokZone* Zone)
{
	if (FGolmokZoneRecord* R = FindRecord(Zone))
	{
		R->bLoadFailed = false;
	}
	ResolveOverlaps();
	UpdateBasemapHiding();
}

void UGolmokZoneSubsystem::NotifyZoneUnloaded(AGolmokZone* Zone)
{
	if (FGolmokZoneRecord* R = FindRecord(Zone))
	{
		R->bSuppressed = false;
	}
	ResolveOverlaps();
	UpdateBasemapHiding();
}

bool UGolmokZoneSubsystem::RequestLoad(const FString& ZoneId, bool bPin, FString& OutMessage, EGolmokZoneRequestSource Source)
{
	CheckNotHoldingPointers(TEXT("RequestLoad"));
	AGolmokZone* Zone = FindZone(ZoneId);
	FGolmokZoneRecord* R = Zone ? FindRecord(Zone) : nullptr;
	if (!Zone || !R)
	{
		OutMessage = FString::Printf(TEXT("zone '%s' is not in this level"), *ZoneId);
		return false;
	}
	R->bBlocked = false;
	R->bLoadFailed = false;
	R->bPinned = bPin;
	R->bPortalManaged = Source == EGolmokZoneRequestSource::Portal;
	Zone->SetAsyncLoadPriority(bPin ? static_cast<int32>(FStreamableManager::AsyncLoadHighPriority) : static_cast<int32>(FStreamableManager::DefaultAsyncLoadPriority));
	++PointerHoldDepth;
	const bool bOk = Zone->Load();
	--PointerHoldDepth;
	if (!bOk)
	{
		R->bLoadFailed = true;
		OutMessage = FString::Printf(TEXT("zone %s failed: %s"), *ZoneId, *Zone->LastError);
		return false;
	}
	OutMessage = FString::Printf(TEXT("zone %s %s%s"), *ZoneId, Zone->IsLoading() ? TEXT("loading") : TEXT("loaded"), bPin ? TEXT(" (pinned)") : TEXT(""));
	return true;
}

bool UGolmokZoneSubsystem::RequestUnload(const FString& ZoneId, FString& OutMessage, EGolmokZoneRequestSource Source)
{
	CheckNotHoldingPointers(TEXT("RequestUnload"));
	AGolmokZone* Zone = FindZone(ZoneId);
	FGolmokZoneRecord* R = Zone ? FindRecord(Zone) : nullptr;
	if (!Zone || !R)
	{
		OutMessage = FString::Printf(TEXT("zone '%s' is not in this level"), *ZoneId);
		return false;
	}
	R->bPinned = false;
	if (Source == EGolmokZoneRequestSource::Portal)
	{
		// The portal owns this zone: not distance-managed, and not "blocked" (that rule is for console unloads).
		R->bPortalManaged = true;
	}
	else
	{
		R->bBlocked = true;
		R->bPortalManaged = false;
	}
	const bool bWasLoading = Zone->IsLoading();
	++PointerHoldDepth;
	Zone->Unload();
	--PointerHoldDepth;
	if (bWasLoading)
	{
		OutMessage = FString::Printf(TEXT("zone %s load cancelled"), *ZoneId);
	}
	else if (Source == EGolmokZoneRequestSource::Portal)
	{
		OutMessage = FString::Printf(TEXT("zone %s unloaded (portal)"), *ZoneId);
	}
	else
	{
		OutMessage = FString::Printf(TEXT("zone %s unloaded (auto-load resumes after leaving the unload radius)"), *ZoneId);
	}
	return true;
}

// ---- WP-09 discovery from the zone index ------------------------------------------------------------------------

bool UGolmokZoneSubsystem::IsDiscoveryActive() const
{
	const UWorld* World = GetWorld();
	return bDiscoverFromIndex && Index.IsAvailable() && World && World->IsGameWorld();
}

bool UGolmokZoneSubsystem::GetPlayerCell(int32& OutX, int32& OutY, double& OutLon, double& OutLat) const
{
	OutX = -1;
	OutY = -1;
	OutLon = 0.0;
	OutLat = 0.0;
	FVector Player;
	if (!GetPlayerLocation(Player))
	{
		return false;
	}
	UWorld* World = GetWorld();
	UGolmokGeoSubsystem* Geo = World ? World->GetSubsystem<UGolmokGeoSubsystem>() : nullptr;
	double Height = 0.0;
	if (!Geo || !Geo->LevelUEToLonLat(Player, OutLat, OutLon, Height))
	{
		return false;
	}
	GolmokGeoMath::LonLatToCell(OutLon, OutLat, FGolmokZoneIndex::CellZoom, OutX, OutY);
	return true;
}

AGolmokZone* UGolmokZoneSubsystem::SpawnDiscoveredZone(const FString& InZoneId, int32 InVersion)
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return nullptr;
	}
	// Same recipe as AGolmokZone::SpawnPortals: deferred so ZoneId / Version are set before BeginPlay registers the
	// actor; transient so it is never saved; no Params.Name (a respawn would collide with the dying actor's name).
	FActorSpawnParameters Params;
	Params.ObjectFlags = EObjectFlags(Params.ObjectFlags | RF_Transient);
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	Params.bDeferConstruction = true;
	AGolmokZone* Zone = World->SpawnActor<AGolmokZone>(AGolmokZone::StaticClass(), FTransform::Identity, Params);
	if (!Zone)
	{
		UE_LOG(LogGolmok, Warning, TEXT("GolmokZoneSubsystem: zone %s v%d could not be spawned from the index"), *InZoneId, InVersion);
		return nullptr;
	}
	Zone->ZoneId = InZoneId;
	Zone->Version = FMath::Max(1, InVersion);
	Zone->bSpawnedFromIndex = true;
#if WITH_EDITOR
	Zone->SetActorLabel(FString::Printf(TEXT("Zone_%s (index)"), *InZoneId), /*bMarkDirty*/ false);
	Zone->SetFolderPath(TEXT("Golmok/Zones/Discovered"));
#endif
	Zone->FinishSpawning(FTransform::Identity); // BeginPlay -> RegisterZone (outside the evaluation stack)
	UE_LOG(LogGolmok, Log, TEXT("GolmokZoneSubsystem: zone %s v%d discovered from index (cell %d/%d/%d)"), *InZoneId, Zone->Version,
		FGolmokZoneIndex::CellZoom, LastCellX, LastCellY);
	return Zone;
}

void UGolmokZoneSubsystem::DiscoverZones()
{
	UWorld* World = GetWorld();
	if (!IsDiscoveryActive() || !World || World->bIsTearingDown || !World->HasBegunPlay())
	{
		return;
	}
	CheckNotHoldingPointers(TEXT("DiscoverZones"));
	int32 CX = 0, CY = 0;
	double Lon = 0.0, Lat = 0.0;
	if (!GetPlayerCell(CX, CY, Lon, Lat))
	{
		if (!bWarnedNoGeoOrigin)
		{
			bWarnedNoGeoOrigin = true;
			UE_LOG(LogGolmok, Warning, TEXT("GolmokZoneSubsystem: discovery needs a player and an AGolmokGeoOrigin in the level; off until then"));
		}
		return;
	}
	LastCellX = CX;
	LastCellY = CY;
	Index.TrimCache(CX, CY, MaxCachedCells);
	TArray<FGolmokZoneIndexCellRef> Near;
	TArray<FString> Warnings;
	Index.CollectAround(CX, CY, 1, Near, &Warnings);
	for (const FString& Line : Warnings)
	{
		UE_LOG(LogGolmok, Log, TEXT("GolmokZoneSubsystem: index: %s"), *Line);
	}
	PruneInvalid();

	// 1) Collect candidates. Zones is only read here: no pointer is held past the loop and nothing is spawned or
	//    destroyed inside it.
	TSet<FString> NearIds;
	for (const FGolmokZoneIndexCellRef& Ref : Near)
	{
		NearIds.Add(Ref.Id);
	}
	TArray<TWeakObjectPtr<AGolmokZone>> ToRetire;
	TArray<TWeakObjectPtr<AGolmokZone>> ToDespawn;
	TArray<FGolmokZoneIndexCellRef> ToSpawn;
	const double Now = World->GetTimeSeconds();
	FVector Player = FVector::ZeroVector;
	GetPlayerLocation(Player);
	const FVector2D PlayerXY(Player.X, Player.Y);
	const float DespawnM = GetDespawnDistanceM();
	for (FGolmokZoneRecord& R : Zones)
	{
		AGolmokZone* Zone = R.Zone.Get();
		if (!Zone || !Zone->bSpawnedFromIndex)
		{
			continue;
		}
		bool bTwin = R.bRetirePending;
		if (!bTwin)
		{
			for (const FGolmokZoneRecord& Other : Zones)
			{
				if (Other.Zone.IsValid() && !Other.Zone->bSpawnedFromIndex && Other.Zone->ZoneId == Zone->ZoneId)
				{
					bTwin = true;
					break;
				}
			}
		}
		const bool bIdle = Zone->State == EGolmokZoneState::Unloaded && !R.bPinned;
		if (bTwin)
		{
			// A placed actor with the same id exists: retire the discovered one, but only once it is idle.
			R.bRetirePending = true;
			if (bIdle)
			{
				ToRetire.Add(Zone);
			}
			continue;
		}
		bool bParentBusy = false;
		if (Zone->IsInterior() && !Zone->GetParentZoneId().IsEmpty())
		{
			if (const AGolmokZone* Parent = FindZone(Zone->GetParentZoneId()))
			{
				bParentBusy = Parent->IsLoadedOrLoading();
			}
		}
		const double DistanceM = Zone->HasManifest() ? Zone->DistanceToFootprintM(PlayerXY) : 1.0e9;
		const bool bEligible = bIdle && !NearIds.Contains(Zone->ZoneId) && DistanceM > static_cast<double>(DespawnM) && !bParentBusy;
		if (!bEligible)
		{
			R.DespawnEligibleSince = -1.0;
			continue;
		}
		if (R.DespawnEligibleSince < 0.0)
		{
			R.DespawnEligibleSince = Now;
			continue;
		}
		if (Now - R.DespawnEligibleSince >= static_cast<double>(DespawnGraceSeconds))
		{
			ToDespawn.Add(Zone);
		}
	}
	for (const FGolmokZoneIndexCellRef& Ref : Near)
	{
		const AGolmokZone* Existing = FindZone(Ref.Id);
		if (!Existing)
		{
			ToSpawn.Add(Ref);
		}
		else if (!Existing->bSpawnedFromIndex && Existing->Version != Ref.Version && !WarnedShadowedIds.Contains(Ref.Id))
		{
			WarnedShadowedIds.Add(Ref.Id);
			UE_LOG(LogGolmok, Log, TEXT("GolmokZoneSubsystem: zone %s: placed v%d shadows index v%d"), *Ref.Id, Existing->Version, Ref.Version);
		}
	}

	// 2) Execute on the snapshots (no Zones iteration: each call may change the array, no pointer is held).
	for (const TWeakObjectPtr<AGolmokZone>& Weak : ToRetire)
	{
		if (AGolmokZone* Zone = Weak.Get())
		{
			UE_LOG(LogGolmok, Log, TEXT("GolmokZoneSubsystem: zone %s: placed actor wins; discovered actor destroyed"), *Zone->ZoneId);
			Zone->Destroy();
		}
	}
	int32 Destroyed = 0;
	for (const TWeakObjectPtr<AGolmokZone>& Weak : ToDespawn)
	{
		if (Destroyed >= MaxDestroysPerDiscovery)
		{
			break;
		}
		if (AGolmokZone* Zone = Weak.Get())
		{
			UE_LOG(LogGolmok, Log, TEXT("GolmokZoneSubsystem: zone %s despawned (index; %.0f m, cells far)"), *Zone->ZoneId,
				Zone->HasManifest() ? Zone->DistanceToFootprintM(PlayerXY) : -1.0);
			Zone->Destroy();
			++Destroyed;
		}
	}
	int32 Spawned = 0;
	for (const FGolmokZoneIndexCellRef& Ref : ToSpawn)
	{
		if (Spawned >= MaxSpawnsPerDiscovery)
		{
			break;
		}
		if (SpawnDiscoveredZone(Ref.Id, Ref.Version))
		{
			++Spawned;
		}
	}
	if (Spawned > 0 || Destroyed > 0 || ToRetire.Num() > 0)
	{
		UE_LOG(LogGolmok, Log, TEXT("GolmokZoneSubsystem: discovery: cell %d/%d/%d, 3x3 zones %d, spawned %d, destroyed %d, retired %d, actors %d"),
			FGolmokZoneIndex::CellZoom, CX, CY, Near.Num(), Spawned, Destroyed, ToRetire.Num(), Zones.Num());
	}
}

void UGolmokZoneSubsystem::ReloadIndex()
{
	const FString IndexDir = FGolmokZoneIndex::DefaultIndexDir();
	IndexLoadError.Reset();
	if (!Index.Load(IndexDir, IndexLoadError))
	{
		if (IndexLoadError.IsEmpty())
		{
			UE_LOG(LogGolmok, Log, TEXT("GolmokZoneSubsystem: no zone index at %s; discovery off"), *IndexDir);
		}
		else
		{
			UE_LOG(LogGolmok, Warning, TEXT("GolmokZoneSubsystem: zone index %s: %s; discovery off"), *IndexDir, *IndexLoadError);
		}
	}
	else
	{
		UE_LOG(LogGolmok, Log, TEXT("GolmokZoneSubsystem: index reloaded: %d zones"), Index.NumZones());
	}
	WarnedShadowedIds.Empty();
	NextDiscoverySeconds = 0.0;
	DiscoverZones();
}

// ---- overlap priority -----------------------------------------------------------------------------------------

bool UGolmokZoneSubsystem::ZoneWins(const AGolmokZone& A, const AGolmokZone& B)
{
	// Higher priority wins, then higher version, then zone id (deterministic).
	if (A.GetPriority() != B.GetPriority())
	{
		return A.GetPriority() > B.GetPriority();
	}
	if (A.Version != B.Version)
	{
		return A.Version > B.Version;
	}
	return A.ZoneId < B.ZoneId;
}

void UGolmokZoneSubsystem::ResolveOverlaps()
{
	TArray<FGolmokZoneRecord*> Loaded;
	for (FGolmokZoneRecord& R : Zones)
	{
		if (R.Zone.IsValid() && R.Zone->IsLoaded())
		{
			R.bSuppressed = false;
			Loaded.Add(&R);
		}
	}
	for (int32 i = 0; i < Loaded.Num(); ++i)
	{
		for (int32 j = i + 1; j < Loaded.Num(); ++j)
		{
			AGolmokZone* A = Loaded[i]->Zone.Get();
			AGolmokZone* B = Loaded[j]->Zone.Get();
			if (!A || !B)
			{
				continue;
			}
			// Only exterior zones compete for the street; interiors are separate spaces under their parent.
			if (A->IsInterior() || B->IsInterior())
			{
				continue;
			}
			// Two versions of the same zone always compete; otherwise test the footprints.
			const bool bOverlap = (A->ZoneId == B->ZoneId) || A->FootprintOverlaps(*B);
			if (!bOverlap)
			{
				continue;
			}
			(ZoneWins(*A, *B) ? Loaded[j] : Loaded[i])->bSuppressed = true;
		}
	}
	for (FGolmokZoneRecord* R : Loaded)
	{
		AGolmokZone* Zone = R->Zone.Get();
		if (Zone && Zone->IsVisualVisible() == R->bSuppressed)
		{
			Zone->SetVisualVisible(!R->bSuppressed);
			if (bSuppressLoserCollision)
			{
				Zone->SetCollisionEnabled(!R->bSuppressed);
			}
			UE_LOG(LogGolmok, Log, TEXT("GolmokZoneSubsystem: zone %s visual %s (overlap priority)"), *Zone->ZoneId,
				R->bSuppressed ? TEXT("hidden") : TEXT("shown"));
		}
	}
}

// ---- basemap hiding -------------------------------------------------------------------------------------------

void UGolmokZoneSubsystem::RefreshBasemap()
{
	for (FGolmokZoneRecord& R : Zones)
	{
		R.bLoadFailed = false; // give failed zones another chance (e.g. after assets were imported)
	}
	bBasemapDirty = true;
	UpdateBasemapHiding();
}

void UGolmokZoneSubsystem::SetRadii(float NewLoadRadiusM, float NewUnloadRadiusM)
{
	LoadRadiusM = FMath::Max(1.f, NewLoadRadiusM);
	UnloadRadiusM = (NewUnloadRadiusM > LoadRadiusM) ? NewUnloadRadiusM : LoadRadiusM + 10.f;
	UE_LOG(LogGolmok, Log, TEXT("GolmokZoneSubsystem: radii now load < %.0f m, unload > %.0f m"), LoadRadiusM, UnloadRadiusM);
}

void UGolmokZoneSubsystem::ApplyBasemapEntryState(FGolmokBasemapEntry& Entry, bool bHidden)
{
	AActor* Actor = Entry.Actor.Get();
	if (!Actor)
	{
		return;
	}
	if (bHidden)
	{
		Actor->SetActorHiddenInGame(true);
		Actor->SetActorEnableCollision(false);
	}
	else
	{
		Actor->SetActorHiddenInGame(Entry.bOriginalHidden);
		Actor->SetActorEnableCollision(Entry.bOriginalCollision);
	}
}

void UGolmokZoneSubsystem::UpdateBasemapHiding()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	if (!bHideBasemap)
	{
		RestoreAllBasemap();
		return;
	}

	// 1) Refresh the actor cache when asked (BeginPlay, console, sublevel changes, periodic rescan).
	const double Now = FPlatformTime::Seconds();
	if (bBasemapDirty || (BasemapRescanSeconds > 0.f && (Now - LastBasemapScanSeconds) >= BasemapRescanSeconds))
	{
		LastBasemapScanSeconds = Now;
		bBasemapDirty = false;
		// Drop entries whose actor is gone; keep live ones (their hidden state and HiddenBy list survive).
		Basemap.RemoveAll([](const FGolmokBasemapEntry& E) { return !E.Actor.IsValid(); });
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			AActor* Actor = *It;
			if (!IsValid(Actor) || !Actor->ActorHasTag(BasemapTag))
			{
				continue;
			}
			if (Basemap.ContainsByPredicate([Actor](const FGolmokBasemapEntry& E) { return E.Actor.Get() == Actor; }))
			{
				continue;
			}
			FVector Origin, Extent;
			Actor->GetActorBounds(false, Origin, Extent);
			FGolmokBasemapEntry Entry;
			Entry.Actor = Actor;
			Entry.CenterUE = FVector2D(Origin.X, Origin.Y);
			Entry.bIsTerrain = Actor->ActorHasTag(BasemapTerrainTag);
			Entry.bOriginalHidden = Actor->IsHidden();
			Entry.bOriginalCollision = Actor->GetActorEnableCollision();
			Basemap.Add(Entry);
		}
	}

	// 2) Recompute which loaded, non-suppressed zones cover each actor (bounds pre-test, then point in polygon).
	TArray<AGolmokZone*> Loaded;
	for (const FGolmokZoneRecord& R : Zones)
	{
		if (R.Zone.IsValid() && R.Zone->IsLoaded() && !R.bSuppressed)
		{
			Loaded.Add(R.Zone.Get());
		}
	}
	int32 NewlyHidden = 0, Restored = 0;
	for (FGolmokBasemapEntry& Entry : Basemap)
	{
		if (!Entry.Actor.IsValid())
		{
			continue;
		}
		TArray<FName> Covering;
		for (AGolmokZone* Zone : Loaded)
		{
			if (Entry.bIsTerrain && !Zone->Manifest.Replaces.bTerrainClip)
			{
				continue;
			}
			if (Zone->FootprintContains(Entry.CenterUE))
			{
				Covering.Add(FName(*Zone->ZoneId));
			}
		}
		const bool bWasHidden = Entry.HiddenBy.Num() > 0;
		const bool bHidden = Covering.Num() > 0;
		Entry.HiddenBy = MoveTemp(Covering);
		if (bHidden && !bWasHidden)
		{
			ApplyBasemapEntryState(Entry, true);
			++NewlyHidden;
		}
		else if (!bHidden && bWasHidden)
		{
			ApplyBasemapEntryState(Entry, false);
			++Restored;
		}
	}
	if (NewlyHidden > 0 || Restored > 0)
	{
		UE_LOG(LogGolmok, Log, TEXT("GolmokZoneSubsystem: basemap actors hidden +%d, restored %d (tagged %d, zones loaded %d)"), NewlyHidden,
			Restored, Basemap.Num(), Loaded.Num());
	}
}

void UGolmokZoneSubsystem::RestoreAllBasemap()
{
	for (FGolmokBasemapEntry& Entry : Basemap)
	{
		if (Entry.HiddenBy.Num() > 0)
		{
			Entry.HiddenBy.Empty();
			ApplyBasemapEntryState(Entry, false);
		}
	}
}

// ---- console --------------------------------------------------------------------------------------------------

FString UGolmokZoneSubsystem::DescribeZones()
{
	// Header prefix is a WP-04 contract (tests and runbooks parse it); WP-09 only appends ", N discovered, M loading".
	FString Out = FString::Printf(TEXT("%d zones (load < %.0f m, unload > %.0f m), %d basemap actors tagged, %d discovered, %d loading\n"), Zones.Num(),
		LoadRadiusM, UnloadRadiusM, Basemap.Num(), NumDiscovered(), NumLoading());
	for (const FGolmokZoneRecord& R : Zones)
	{
		const AGolmokZone* Zone = R.Zone.Get();
		if (!Zone)
		{
			continue;
		}
		const TCHAR* StateText = Zone->State == EGolmokZoneState::Loaded    ? TEXT("loaded")
								 : Zone->State == EGolmokZoneState::Loading ? TEXT("loading")
								 : Zone->State == EGolmokZoneState::Failed  ? TEXT("FAILED")
																			: TEXT("unloaded");
		Out += FString::Printf(TEXT("  %-28s v%-3d prio %-4d %-9s dist %s%8.1f m%s%s%s%s%s%s%s%s\n"), *Zone->ZoneId, Zone->Version, Zone->GetPriority(),
			StateText, R.bDistanceIsLowerBound ? TEXT(">=") : TEXT("  "), R.LastDistanceM, R.bPinned ? TEXT(" pinned") : TEXT(""),
			R.bBlocked ? TEXT(" blocked") : TEXT(""),
			R.bSuppressed ? TEXT(" visual-off(overlap)") : TEXT(""), Zone->bAutoManaged ? TEXT("") : TEXT(" manual"),
			Zone->LastError.IsEmpty() ? TEXT("") : *FString::Printf(TEXT(" error: %s"), *Zone->LastError),
			R.bPortalManaged ? TEXT(" portal") : TEXT(""),
			Zone->IsLoading() ? *FString::Printf(TEXT(" (loading %.1f s)"), Zone->GetLoadingSeconds()) : TEXT(""),
			Zone->bSpawnedFromIndex ? TEXT(" [index]") : TEXT(" [placed]"));
	}
	return Out;
}

FString UGolmokZoneSubsystem::DescribeIndex()
{
	FString Out;
	// index: ...
	if (!bDiscoverFromIndex)
	{
		Out += TEXT("index: disabled (bDiscoverFromIndex=False)\n");
	}
	else if (Index.IsAvailable())
	{
		Out += FString::Printf(TEXT("index: %s (%d zones, %d cells cached, %d missing cell files)\n"), *Index.GetIndexDir(), Index.NumZones(),
			Index.NumCachedCells(), Index.NumMissingCells());
	}
	else if (!IndexLoadError.IsEmpty())
	{
		Out += FString::Printf(TEXT("index: error %s\n"), *IndexLoadError);
	}
	else
	{
		Out += FString::Printf(TEXT("index: not found (%s) - discovery off\n"), *FGolmokZoneIndex::ZonesFilePath(FGolmokZoneIndex::DefaultIndexDir()));
	}

	// discovery: ...
	int32 CX = -1, CY = -1;
	double Lon = 0.0, Lat = 0.0;
	const bool bHaveCell = GetPlayerCell(CX, CY, Lon, Lat);
	if (!IsDiscoveryActive())
	{
		Out += TEXT("discovery: off (no index)\n");
	}
	else if (!bHaveCell)
	{
		FVector Player;
		Out += GetPlayerLocation(Player) ? TEXT("discovery: off (no AGolmokGeoOrigin)\n") : TEXT("discovery: off (no player)\n");
	}
	else
	{
		Out += FString::Printf(TEXT("discovery: on every %.1f s, despawn > %.0f m after %.0f s, %d discovered actors, %d loading\n"),
			DiscoveryIntervalSeconds, GetDespawnDistanceM(), DespawnGraceSeconds, NumDiscovered(), NumLoading());
	}

	// player: ...
	if (bHaveCell)
	{
		double West = 0.0, South = 0.0, East = 0.0, North = 0.0;
		GolmokGeoMath::CellBounds(CX, CY, FGolmokZoneIndex::CellZoom, West, South, East, North);
		Out += FString::Printf(TEXT("player: lon %.6f lat %.6f -> cell %d/%d/%d (W %.4f E %.4f S %.4f N %.4f)\n"), Lon, Lat, FGolmokZoneIndex::CellZoom, CX,
			CY, West, East, South, North);
	}
	else
	{
		Out += TEXT("player: cell unknown (no player pawn / camera or no AGolmokGeoOrigin)\n");
	}

	// cells / near: ...
	if (Index.IsAvailable() && bHaveCell)
	{
		Out += Index.Describe(CX, CY, 1);
		Out += TEXT("\n");
		TArray<FGolmokZoneIndexCellRef> Near;
		Index.CollectAround(CX, CY, 1, Near, nullptr);
		Out += TEXT("near:");
		for (const FGolmokZoneIndexCellRef& Ref : Near)
		{
			const AGolmokZone* Zone = FindZone(Ref.Id);
			if (!Zone)
			{
				Out += FString::Printf(TEXT(" %s@v%d [absent]"), *Ref.Id, Ref.Version);
				continue;
			}
			const TCHAR* StateText = Zone->State == EGolmokZoneState::Loaded    ? TEXT("loaded")
									 : Zone->State == EGolmokZoneState::Loading ? TEXT("loading")
									 : Zone->State == EGolmokZoneState::Failed  ? TEXT("FAILED")
																				: TEXT("unloaded");
			const FGolmokZoneRecord* R = Zones.FindByPredicate([Zone](const FGolmokZoneRecord& Rec) { return Rec.Zone.Get() == Zone; });
			Out += FString::Printf(TEXT("  %s@v%d [%s, %s%s]"), *Ref.Id, Zone->Version, Zone->bSpawnedFromIndex ? TEXT("index") : TEXT("placed"), StateText,
				(R && R->bPortalManaged) ? TEXT(" portal") : TEXT(""));
		}
		if (Near.Num() == 0)
		{
			Out += TEXT(" (none)");
		}
		Out += TEXT("\n");
	}
	return Out;
}

namespace
{
	UGolmokZoneSubsystem* ZoneSubsystemFor(UWorld* World)
	{
		UGolmokZoneSubsystem* Subsystem = World ? World->GetSubsystem<UGolmokZoneSubsystem>() : nullptr;
		if (!Subsystem)
		{
			UE_LOG(LogGolmok, Warning, TEXT("golmok.zone.*: no zone subsystem in this world (game / PIE only)."));
		}
		return Subsystem;
	}

	void CmdZoneList(const TArray<FString>& Args, UWorld* World)
	{
		if (UGolmokZoneSubsystem* Subsystem = ZoneSubsystemFor(World))
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.zone.list\n%s"), *Subsystem->DescribeZones());
		}
	}

	void CmdZoneLoad(const TArray<FString>& Args, UWorld* World)
	{
		UGolmokZoneSubsystem* Subsystem = ZoneSubsystemFor(World);
		if (!Subsystem)
		{
			return;
		}
		if (Args.Num() < 1)
		{
			UE_LOG(LogGolmok, Warning, TEXT("usage: golmok.zone.load <zone_id>"));
			return;
		}
		FString Message;
		const bool bOk = Subsystem->RequestLoad(Args[0], /*bPin*/ true, Message);
		UE_LOG(LogGolmok, Log, TEXT("golmok.zone.load: %s%s"), bOk ? TEXT("") : TEXT("ERROR "), *Message);
	}

	void CmdZoneUnload(const TArray<FString>& Args, UWorld* World)
	{
		UGolmokZoneSubsystem* Subsystem = ZoneSubsystemFor(World);
		if (!Subsystem)
		{
			return;
		}
		if (Args.Num() < 1)
		{
			UE_LOG(LogGolmok, Warning, TEXT("usage: golmok.zone.unload <zone_id>"));
			return;
		}
		FString Message;
		const bool bOk = Subsystem->RequestUnload(Args[0], Message);
		UE_LOG(LogGolmok, Log, TEXT("golmok.zone.unload: %s%s"), bOk ? TEXT("") : TEXT("ERROR "), *Message);
	}

	void CmdZoneRefresh(const TArray<FString>& Args, UWorld* World)
	{
		if (UGolmokZoneSubsystem* Subsystem = ZoneSubsystemFor(World))
		{
			Subsystem->RefreshBasemap();
			Subsystem->DiscoverZones();
			Subsystem->Evaluate();
			UE_LOG(LogGolmok, Log, TEXT("golmok.zone.refresh: basemap rescanned, index discovery run and zones re-evaluated"));
		}
	}

	void CmdZoneRadius(const TArray<FString>& Args, UWorld* World)
	{
		UGolmokZoneSubsystem* Subsystem = ZoneSubsystemFor(World);
		if (!Subsystem)
		{
			return;
		}
		if (Args.Num() < 2)
		{
			UE_LOG(LogGolmok, Warning, TEXT("usage: golmok.zone.radius <load_m> <unload_m>"));
			return;
		}
		Subsystem->SetRadii(FCString::Atof(*Args[0]), FCString::Atof(*Args[1]));
		Subsystem->Evaluate();
	}

	void CmdZoneIndex(const TArray<FString>& Args, UWorld* World)
	{
		UGolmokZoneSubsystem* Subsystem = ZoneSubsystemFor(World);
		if (!Subsystem)
		{
			return;
		}
		if (Args.Num() > 0 && Args[0].Equals(TEXT("reload"), ESearchCase::IgnoreCase))
		{
			Subsystem->ReloadIndex();
		}
		else if (Args.Num() > 0)
		{
			UE_LOG(LogGolmok, Warning, TEXT("usage: golmok.zone.index [reload]"));
			return;
		}
		UE_LOG(LogGolmok, Log, TEXT("golmok.zone.index\n%s"), *Subsystem->DescribeIndex());
	}

	FAutoConsoleCommandWithWorldAndArgs GCmdZoneList(TEXT("golmok.zone.list"), TEXT("List registered zones with state and distance."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdZoneList));
	FAutoConsoleCommandWithWorldAndArgs GCmdZoneLoad(TEXT("golmok.zone.load"), TEXT("golmok.zone.load <zone_id>: load and pin a zone."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdZoneLoad));
	FAutoConsoleCommandWithWorldAndArgs GCmdZoneUnload(TEXT("golmok.zone.unload"), TEXT("golmok.zone.unload <zone_id>: unload a zone."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdZoneUnload));
	FAutoConsoleCommandWithWorldAndArgs GCmdZoneRefresh(TEXT("golmok.zone.refresh"),
		TEXT("Rescan basemap actors (tag GolmokBasemap), run index discovery and re-evaluate zones now."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdZoneRefresh));
	FAutoConsoleCommandWithWorldAndArgs GCmdZoneRadius(TEXT("golmok.zone.radius"),
		TEXT("golmok.zone.radius <load_m> <unload_m>: change the load/unload hysteresis radii and re-evaluate."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdZoneRadius));
	FAutoConsoleCommandWithWorldAndArgs GCmdZoneIndex(TEXT("golmok.zone.index"),
		TEXT("golmok.zone.index [reload]: show the zone index state, the player's 3x3 cells and the nearby zones; reload re-reads zones.json and discovers now."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdZoneIndex));
} // namespace
