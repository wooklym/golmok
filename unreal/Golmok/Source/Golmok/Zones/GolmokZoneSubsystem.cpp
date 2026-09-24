#include "Zones/GolmokZoneSubsystem.h"

#include "Golmok.h"

#include "Camera/PlayerCameraManager.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "Zones/GolmokZone.h"

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
}

void UGolmokZoneSubsystem::Deinitialize()
{
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(EvaluateTimer);
	}
	RestoreAllBasemap();
	Zones.Empty();
	Basemap.Empty();
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
	InWorld.GetTimerManager().SetTimer(EvaluateTimer, this, &UGolmokZoneSubsystem::Evaluate, UpdateIntervalSeconds, /*bLoop*/ true);
	UE_LOG(LogGolmok, Log, TEXT("GolmokZoneSubsystem: %d zones registered; load < %.0f m, unload > %.0f m, every %.2f s"), Zones.Num(),
		LoadRadiusM, UnloadRadiusM, UpdateIntervalSeconds);
}

// ---- registration ---------------------------------------------------------------------------------------------

void UGolmokZoneSubsystem::RegisterZone(AGolmokZone* Zone)
{
	if (!IsValid(Zone) || FindRecord(Zone))
	{
		return;
	}
	for (const FGolmokZoneRecord& Other : Zones)
	{
		if (Other.Zone.IsValid() && Other.Zone->ZoneId == Zone->ZoneId && Other.Zone->Version == Zone->Version)
		{
			UE_LOG(LogGolmok, Warning, TEXT("GolmokZoneSubsystem: zone %s v%d is placed twice ('%s' and '%s')."), *Zone->ZoneId, Zone->Version,
				*Other.Zone->GetName(), *Zone->GetName());
		}
	}
	FGolmokZoneRecord Record;
	Record.Zone = Zone;
	Zones.Add(Record);
}

void UGolmokZoneSubsystem::UnregisterZone(AGolmokZone* Zone)
{
	const int32 Index = Zones.IndexOfByPredicate([Zone](const FGolmokZoneRecord& R) { return R.Zone.Get() == Zone; });
	if (Index != INDEX_NONE)
	{
		Zones.RemoveAt(Index);
		bBasemapDirty = true;
	}
}

FGolmokZoneRecord* UGolmokZoneSubsystem::FindRecord(const AGolmokZone* Zone)
{
	return Zones.FindByPredicate([Zone](const FGolmokZoneRecord& R) { return R.Zone.Get() == Zone; });
}

AGolmokZone* UGolmokZoneSubsystem::FindZone(const FString& ZoneId) const
{
	for (const FGolmokZoneRecord& R : Zones)
	{
		if (R.Zone.IsValid() && R.Zone->ZoneId == ZoneId)
		{
			return R.Zone.Get();
		}
	}
	return nullptr;
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
				continue;
			}
		}
		const double DistanceM = Zone->DistanceToFootprintM(PlayerXY);
		R.LastDistanceM = DistanceM;
		if (!Zone->bAutoManaged || (Zone->IsInterior() && !bAutoManageInterior))
		{
			continue;
		}
		if (R.bBlocked && DistanceM >= UnloadRadiusM)
		{
			R.bBlocked = false; // the player left; console unload no longer sticks
		}
		if (Zone->IsLoaded())
		{
			if (!R.bPinned && DistanceM >= UnloadRadiusM)
			{
				Zone->Unload();
				bChanged = true;
			}
		}
		else if (!R.bLoadFailed && !R.bBlocked && DistanceM <= LoadRadiusM)
		{
			ToLoad.Add(&R);
		}
	}

	// Nearest first, at most MaxLoadsPerUpdate synchronous loads per step.
	ToLoad.Sort([](const FGolmokZoneRecord& A, const FGolmokZoneRecord& B) { return A.LastDistanceM < B.LastDistanceM; });
	for (int32 i = 0; i < ToLoad.Num() && i < MaxLoadsPerUpdate; ++i)
	{
		AGolmokZone* Zone = ToLoad[i]->Zone.Get();
		if (Zone && !Zone->Load())
		{
			ToLoad[i]->bLoadFailed = true;
			UE_LOG(LogGolmok, Error, TEXT("GolmokZoneSubsystem: zone %s failed to load: %s"), *Zone->ZoneId, *Zone->LastError);
		}
		else
		{
			bChanged = true;
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

bool UGolmokZoneSubsystem::RequestLoad(const FString& ZoneId, bool bPin, FString& OutMessage)
{
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
	if (!Zone->Load())
	{
		R->bLoadFailed = true;
		OutMessage = FString::Printf(TEXT("zone %s failed: %s"), *ZoneId, *Zone->LastError);
		return false;
	}
	OutMessage = FString::Printf(TEXT("zone %s loaded%s"), *ZoneId, bPin ? TEXT(" (pinned)") : TEXT(""));
	return true;
}

bool UGolmokZoneSubsystem::RequestUnload(const FString& ZoneId, FString& OutMessage)
{
	AGolmokZone* Zone = FindZone(ZoneId);
	FGolmokZoneRecord* R = Zone ? FindRecord(Zone) : nullptr;
	if (!Zone || !R)
	{
		OutMessage = FString::Printf(TEXT("zone '%s' is not in this level"), *ZoneId);
		return false;
	}
	R->bPinned = false;
	R->bBlocked = true;
	Zone->Unload();
	OutMessage = FString::Printf(TEXT("zone %s unloaded (auto-load resumes after leaving the unload radius)"), *ZoneId);
	return true;
}

// ---- overlap priority -----------------------------------------------------------------------------------------

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
			if (!A || !B || !A->FootprintOverlaps(*B))
			{
				continue;
			}
			// Higher priority wins, then higher version, then zone id (deterministic).
			bool bAWins;
			if (A->GetPriority() != B->GetPriority())
			{
				bAWins = A->GetPriority() > B->GetPriority();
			}
			else if (A->Version != B->Version)
			{
				bAWins = A->Version > B->Version;
			}
			else
			{
				bAWins = A->ZoneId < B->ZoneId;
			}
			(bAWins ? Loaded[j] : Loaded[i])->bSuppressed = true;
		}
	}
	for (FGolmokZoneRecord* R : Loaded)
	{
		AGolmokZone* Zone = R->Zone.Get();
		if (Zone && Zone->IsVisualVisible() == R->bSuppressed)
		{
			Zone->SetVisualVisible(!R->bSuppressed);
			UE_LOG(LogGolmok, Log, TEXT("GolmokZoneSubsystem: zone %s visual %s (overlap priority)"), *Zone->ZoneId,
				R->bSuppressed ? TEXT("hidden") : TEXT("shown"));
		}
	}
}

// ---- basemap hiding -------------------------------------------------------------------------------------------

void UGolmokZoneSubsystem::RefreshBasemap()
{
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

	// 2) Recompute which loaded zones cover each actor (bounds pre-test, then point in polygon).
	TArray<AGolmokZone*> Loaded;
	for (const FGolmokZoneRecord& R : Zones)
	{
		if (R.Zone.IsValid() && R.Zone->IsLoaded())
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
			if (Entry.bIsTerrain && !Zone->Manifest.bTerrainClip)
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
	FString Out = FString::Printf(TEXT("%d zones (load < %.0f m, unload > %.0f m), %d basemap actors tagged\n"), Zones.Num(), LoadRadiusM,
		UnloadRadiusM, Basemap.Num());
	for (const FGolmokZoneRecord& R : Zones)
	{
		const AGolmokZone* Zone = R.Zone.Get();
		if (!Zone)
		{
			continue;
		}
		const TCHAR* StateText = Zone->State == EGolmokZoneState::Loaded ? TEXT("loaded")
								 : Zone->State == EGolmokZoneState::Failed ? TEXT("FAILED")
																		   : TEXT("unloaded");
		Out += FString::Printf(TEXT("  %-28s v%-3d prio %-4d %-9s dist %8.1f m%s%s%s%s%s\n"), *Zone->ZoneId, Zone->Version, Zone->GetPriority(),
			StateText, R.LastDistanceM, R.bPinned ? TEXT(" pinned") : TEXT(""), R.bBlocked ? TEXT(" blocked") : TEXT(""),
			R.bSuppressed ? TEXT(" visual-off(overlap)") : TEXT(""), Zone->bAutoManaged ? TEXT("") : TEXT(" manual"),
			Zone->LastError.IsEmpty() ? TEXT("") : *FString::Printf(TEXT(" error: %s"), *Zone->LastError));
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
			Subsystem->Evaluate();
			UE_LOG(LogGolmok, Log, TEXT("golmok.zone.refresh: basemap rescanned and zones re-evaluated"));
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

	FAutoConsoleCommandWithWorldAndArgs GCmdZoneList(TEXT("golmok.zone.list"), TEXT("List registered zones with state and distance."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdZoneList));
	FAutoConsoleCommandWithWorldAndArgs GCmdZoneLoad(TEXT("golmok.zone.load"), TEXT("golmok.zone.load <zone_id>: load and pin a zone."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdZoneLoad));
	FAutoConsoleCommandWithWorldAndArgs GCmdZoneUnload(TEXT("golmok.zone.unload"), TEXT("golmok.zone.unload <zone_id>: unload a zone."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdZoneUnload));
	FAutoConsoleCommandWithWorldAndArgs GCmdZoneRefresh(TEXT("golmok.zone.refresh"),
		TEXT("Rescan basemap actors (tag GolmokBasemap) and re-evaluate zones now."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdZoneRefresh));
	FAutoConsoleCommandWithWorldAndArgs GCmdZoneRadius(TEXT("golmok.zone.radius"),
		TEXT("golmok.zone.radius <load_m> <unload_m>: change the load/unload hysteresis radii and re-evaluate."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdZoneRadius));
} // namespace
