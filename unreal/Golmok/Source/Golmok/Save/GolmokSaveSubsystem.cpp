#include "Save/GolmokSaveSubsystem.h"

#include "Golmok.h"

#include "Characters/GolmokCharacterSubsystem.h"
#include "CoreGlobals.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Geo/GolmokGeoSubsystem.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformTime.h"
#include "Kismet/GameplayStatics.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Map/GolmokTravelSubsystem.h"
#include "Misc/CommandLine.h"
#include "Misc/CoreDelegates.h"
#include "Misc/DateTime.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Photo/GolmokPhotoModeSubsystem.h"
#include "TimerManager.h"
#include "Zones/GolmokZone.h"
#include "Zones/GolmokZoneSubsystem.h"

namespace GolmokSavePrivate
{
	constexpr int32 UserIndex = 0;
	/** Restore waits for a pawn this many ticks of RestoreRetrySeconds (about 3 s), then applies what it can. */
	constexpr int32 MaxRestoreAttempts = 60;
	constexpr float RestoreRetrySeconds = 0.05f;

	/** Photo index entries are paths relative to <Project>/Saved/; anything absolute or climbing out is dropped. */
	bool IsSafeSavedRelative(const FString& Rel)
	{
		return !Rel.IsEmpty() && FPaths::IsRelative(Rel) && !Rel.Contains(TEXT("..")) && !Rel.Contains(TEXT(":"));
	}

	bool PhotoExists(const FString& Rel)
	{
		return IsSafeSavedRelative(Rel) && IFileManager::Get().FileExists(*FPaths::Combine(FPaths::ProjectSavedDir(), Rel));
	}

	APawn* PlayerPawn(UWorld* World) { return World ? UGameplayStatics::GetPlayerPawn(World, 0) : nullptr; }
} // namespace GolmokSavePrivate

// ---- lifecycle ------------------------------------------------------------------------------------------------

void UGolmokSaveSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	// A developer's slot never changes an automation test and a test never overwrites it (tests opt in on their own slot).
	bAutomatic = !GIsAutomationTesting;
	AutosaveIntervalSeconds = FMath::Max(0.f, AutosaveIntervalSeconds);
	VisitPollSeconds = FMath::Max(0.1f, VisitPollSeconds);
	PreExitHandle = FCoreDelegates::OnPreExit.AddUObject(this, &UGolmokSaveSubsystem::OnPreExit);
}

void UGolmokSaveSubsystem::Deinitialize()
{
	FCoreDelegates::OnPreExit.Remove(PreExitHandle);
	PreExitHandle.Reset();
	HandleWorldEnd(ActiveWorld.Get());
	Super::Deinitialize();
}

UGolmokSaveSubsystem* UGolmokSaveSubsystem::Get(const UWorld* World)
{
	const UGameInstance* GameInstance = World ? World->GetGameInstance() : nullptr;
	return GameInstance ? GameInstance->GetSubsystem<UGolmokSaveSubsystem>() : nullptr;
}

void UGolmokSaveSubsystem::HandleWorldBeginPlay(UWorld& InWorld)
{
	if (!InWorld.IsGameWorld())
	{
		return;
	}
	if (ActiveWorld.IsValid() && ActiveWorld.Get() != &InWorld)
	{
		HandleWorldEnd(ActiveWorld.Get());
	}
	ActiveWorld = &InWorld;
	Snapshot = FSnapshot();
	RestoreAttempts = 0;
	bBaselineSet = false;
	LastSaveSeconds = FPlatformTime::Seconds(); // the periodic autosave never fires before an interval has passed
	LoadIndexFromSlot();

	if (UGolmokTravelSubsystem* Travel = UGolmokTravelSubsystem::Get(&InWorld))
	{
		TraveledHandle = Travel->OnTraveled.AddUObject(this, &UGolmokSaveSubsystem::OnTraveled);
	}
	if (UGolmokPhotoModeSubsystem* Photo = InWorld.GetSubsystem<UGolmokPhotoModeSubsystem>())
	{
		PhotoHandle = Photo->OnPhotoSaved.AddUObject(this, &UGolmokSaveSubsystem::OnPhotoSaved);
	}
	InWorld.GetTimerManager().SetTimer(VisitTimer, FTimerDelegate::CreateUObject(this, &UGolmokSaveSubsystem::OnVisitPoll), VisitPollSeconds,
		/*bLoop*/ true);

	const bool bNoRestoreSwitch = FParse::Param(FCommandLine::Get(), TEXT("GolmokNoRestore"));
	if (bAutomatic && bRestoreOnBeginPlay && !bNoRestoreSwitch)
	{
		// One tick after BeginPlay (spec §3): the pawn is possessed and the geo origin found by then; retried until a pawn exists.
		RestoreTimer = InWorld.GetTimerManager().SetTimerForNextTick(FTimerDelegate::CreateUObject(this, &UGolmokSaveSubsystem::OnRestoreTick));
	}
	else
	{
		UE_LOG(LogGolmok, Log, TEXT("GolmokSave: restore skipped (%s)"),
			!bAutomatic ? TEXT("automatic saves off (automation)") : (bNoRestoreSwitch ? TEXT("-GolmokNoRestore") : TEXT("bRestoreOnBeginPlay=False")));
	}
}

void UGolmokSaveSubsystem::HandleWorldEnd(UWorld* InWorld)
{
	if (!InWorld || InWorld != ActiveWorld.Get())
	{
		return;
	}
	// Synchronous: an async write during shutdown can be lost (spec §3). The snapshot is refreshed while actors exist.
	if (bAutomatic && Snapshot.bValid)
	{
		SaveNow(/*bSync*/ true, TEXT("world end"));
	}
	InWorld->GetTimerManager().ClearTimer(VisitTimer);
	InWorld->GetTimerManager().ClearTimer(RestoreTimer);
	if (UGolmokTravelSubsystem* Travel = UGolmokTravelSubsystem::Get(InWorld))
	{
		Travel->OnTraveled.Remove(TraveledHandle);
	}
	if (UGolmokPhotoModeSubsystem* Photo = InWorld->GetSubsystem<UGolmokPhotoModeSubsystem>())
	{
		Photo->OnPhotoSaved.Remove(PhotoHandle);
	}
	TraveledHandle.Reset();
	PhotoHandle.Reset();
	ActiveWorld.Reset();
}

void UGolmokSaveSubsystem::OnPreExit()
{
	if (bAutomatic && Snapshot.bValid)
	{
		SaveNow(/*bSync*/ true, TEXT("pre-exit"));
	}
}

// ---- snapshot / index -----------------------------------------------------------------------------------------

bool UGolmokSaveSubsystem::TakeSnapshot(UWorld& InWorld)
{
	if (InWorld.bIsTearingDown)
	{
		return Snapshot.bValid; // keep the last one: actors are going away
	}
	APawn* Pawn = GolmokSavePrivate::PlayerPawn(&InWorld);
	if (!Pawn)
	{
		return Snapshot.bValid;
	}
	FSnapshot S;
	S.bValid = true;
	S.LocationUE = Pawn->GetActorLocation();
	const APlayerController* PC = Cast<APlayerController>(Pawn->GetController());
	S.YawUE = PC ? PC->GetControlRotation().Yaw : Pawn->GetActorRotation().Yaw;
	S.YawDeg = GolmokTravelMath::UEYawToEnuYaw(S.YawUE);
	if (UGolmokGeoSubsystem* Geo = InWorld.GetSubsystem<UGolmokGeoSubsystem>())
	{
		// Only with a real origin actor: the no-origin fallback frame is not a geodetic position.
		S.bHasPosition = Geo->HasOrigin() && Geo->LevelUEToLonLat(S.LocationUE, S.Lat, S.Lon, S.HeightEllipsoidal);
	}
	if (const UGolmokZoneSubsystem* Zones = InWorld.GetSubsystem<UGolmokZoneSubsystem>())
	{
		if (const AGolmokZone* Zone = Zones->FindLoadedZoneAt(FVector2D(S.LocationUE.X, S.LocationUE.Y)))
		{
			S.ZoneId = Zone->ZoneId;
			S.ZoneVersion = Zone->Version;
		}
	}
	if (const AGolmokTimeOfDay* Tod = AGolmokTimeOfDay::Find(&InWorld))
	{
		S.TodPreset = Tod->CurrentPreset.IsNone() ? FString() : Tod->CurrentPreset.ToString();
	}
	if (const UGolmokCharacterSubsystem* Characters = InWorld.GetSubsystem<UGolmokCharacterSubsystem>())
	{
		S.CharacterId = Characters->GetCurrentId();
	}
	Snapshot = MoveTemp(S);
	return true;
}

void UGolmokSaveSubsystem::LoadIndexFromSlot()
{
	// The visit / photo index always continues from the slot (also with -GolmokNoRestore), so a later save never drops history.
	if (!bAutomatic)
	{
		return;
	}
	if (const UGolmokSaveGame* Saved = LoadSlot())
	{
		Visited = Saved->Visited;
		Photos = Saved->Photos;
	}
}

UGolmokSaveGame* UGolmokSaveSubsystem::BuildSaveObject()
{
	UGolmokSaveGame* Out = Cast<UGolmokSaveGame>(UGameplayStatics::CreateSaveGameObject(UGolmokSaveGame::StaticClass()));
	if (!Out)
	{
		return nullptr;
	}
	Out->SaveSchemaVersion = UGolmokSaveGame::CurrentSchemaVersion;
	Out->bHasPosition = Snapshot.bValid && Snapshot.bHasPosition;
	Out->Lat = Out->bHasPosition ? Snapshot.Lat : 0.0;
	Out->Lon = Out->bHasPosition ? Snapshot.Lon : 0.0;
	Out->HeightEllipsoidal = Out->bHasPosition ? Snapshot.HeightEllipsoidal : 0.0;
	Out->YawDeg = Snapshot.YawDeg;
	Out->ZoneId = Snapshot.ZoneId;
	Out->ZoneVersion = Snapshot.ZoneId.IsEmpty() ? 0 : Snapshot.ZoneVersion;
	Out->TimeOfDay.PresetName = Snapshot.TodPreset;
	Out->Visited = Visited;
	Out->Photos = Photos;
	Out->CharacterId = Snapshot.CharacterId;
	Out->SavedAtUtc = FDateTime::UtcNow().ToIso8601();
	return Out;
}

bool UGolmokSaveSubsystem::HasSave() const
{
	return UGameplayStatics::DoesSaveGameExist(SlotName, GolmokSavePrivate::UserIndex);
}

UGolmokSaveGame* UGolmokSaveSubsystem::LoadSlot() const
{
	if (!HasSave())
	{
		return nullptr;
	}
	USaveGame* Loaded = UGameplayStatics::LoadGameFromSlot(SlotName, GolmokSavePrivate::UserIndex);
	UGolmokSaveGame* Save = Cast<UGolmokSaveGame>(Loaded);
	if (Loaded && !Save)
	{
		UE_LOG(LogGolmok, Warning, TEXT("GolmokSave: slot %s holds a %s, not a GolmokSaveGame; ignored"), *SlotName, *Loaded->GetClass()->GetName());
	}
	return Save;
}

// ---- writing --------------------------------------------------------------------------------------------------

bool UGolmokSaveSubsystem::SaveNow(bool bSync, const TCHAR* Reason, FString* OutMessage)
{
	if (UWorld* World = ActiveWorld.Get())
	{
		TakeSnapshot(*World);
	}
	if (!bSync && PendingAsync > 0)
	{
		// One write at a time per slot: the next one follows the pending completion.
		bSaveQueued = true;
		MarkDirty();
		if (OutMessage)
		{
			*OutMessage = TEXT("queued behind a pending async save");
		}
		return true;
	}
	UGolmokSaveGame* Save = BuildSaveObject();
	if (!Save)
	{
		if (OutMessage)
		{
			*OutMessage = TEXT("could not create the save object");
		}
		return false;
	}
	LastSaveSeconds = FPlatformTime::Seconds();
	LastSavedLocationUE = Snapshot.LocationUE;
	LastSavedYawUE = Snapshot.YawUE;
	bBaselineSet = Snapshot.bValid;
	bDirty = false;
	bSaveQueued = false;
	FString Message;
	bool bOk = true;
	if (bSync)
	{
		bOk = UGameplayStatics::SaveGameToSlot(Save, SlotName, GolmokSavePrivate::UserIndex);
		if (bOk)
		{
			++CompletedSaves;
		}
		Message = FString::Printf(TEXT("saved %s (sync, %s)%s"), *SlotName, Reason, bOk ? TEXT("") : TEXT(" FAILED"));
	}
	else
	{
		++PendingAsync;
		UGameplayStatics::AsyncSaveGameToSlot(Save, SlotName, GolmokSavePrivate::UserIndex,
			FAsyncSaveGameToSlotDelegate::CreateUObject(this, &UGolmokSaveSubsystem::OnAsyncSaved));
		Message = FString::Printf(TEXT("saving %s (async, %s)"), *SlotName, Reason);
	}
	UE_LOG(LogGolmok, Log, TEXT("GolmokSave: %s: zone %s, visited %d, photos %d, position %s"), *Message,
		Save->ZoneId.IsEmpty() ? TEXT("-") : *Save->ZoneId, Save->Visited.Num(), Save->Photos.Num(), Save->bHasPosition ? TEXT("yes") : TEXT("no"));
	LastMessage = Message;
	if (OutMessage)
	{
		*OutMessage = Message;
	}
	return bOk;
}

void UGolmokSaveSubsystem::OnAsyncSaved(const FString& InSlotName, const int32 InUserIndex, bool bSuccess)
{
	PendingAsync = FMath::Max(0, PendingAsync - 1);
	if (bSuccess)
	{
		++CompletedSaves;
	}
	else
	{
		UE_LOG(LogGolmok, Warning, TEXT("GolmokSave: async save to %s (user %d) failed"), *InSlotName, InUserIndex);
		MarkDirty();
	}
	if (bSaveQueued && PendingAsync == 0)
	{
		SaveNow(/*bSync*/ false, TEXT("queued"));
	}
}

// ---- triggers -------------------------------------------------------------------------------------------------

bool UGolmokSaveSubsystem::IsVisited(const FString& ZoneId) const
{
	return Visited.ContainsByPredicate([&ZoneId](const FGolmokSaveVisit& V) { return V.ZoneId == ZoneId; });
}

bool UGolmokSaveSubsystem::NoteVisit(const FString& ZoneId, int32 Version, const TCHAR* Why)
{
	if (ZoneId.IsEmpty() || IsVisited(ZoneId))
	{
		return false;
	}
	FGolmokSaveVisit Visit;
	Visit.ZoneId = ZoneId;
	Visit.Version = Version;
	Visit.FirstVisitUtc = FDateTime::UtcNow().ToIso8601();
	Visited.Add(MoveTemp(Visit));
	MarkDirty();
	UE_LOG(LogGolmok, Log, TEXT("GolmokSave: first visit %s v%d (%s)"), *ZoneId, Version, Why);
	if (bAutomatic)
	{
		SaveNow(/*bSync*/ false, TEXT("first visit"));
	}
	return true;
}

void UGolmokSaveSubsystem::NotePhoto(const FString& RelativePath)
{
	if (!GolmokSavePrivate::IsSafeSavedRelative(RelativePath) || Photos.Contains(RelativePath))
	{
		return;
	}
	Photos.Add(RelativePath);
	MarkDirty();
	if (bAutomatic)
	{
		SaveNow(/*bSync*/ false, TEXT("photo"));
	}
}

void UGolmokSaveSubsystem::OnTraveled(const FString& ZoneId)
{
	UWorld* World = ActiveWorld.Get();
	const UGolmokZoneSubsystem* Zones = World ? World->GetSubsystem<UGolmokZoneSubsystem>() : nullptr;
	const int32 Version = Zones ? Zones->ResolveZoneVersion(ZoneId) : 0;
	const bool bAutomaticNow = bAutomatic;
	bAutomatic = false; // one write below for both the visit and the travel
	NoteVisit(ZoneId, Version, TEXT("travel"));
	bAutomatic = bAutomaticNow;
	MarkDirty();
	if (bAutomatic)
	{
		SaveNow(/*bSync*/ false, TEXT("travel"));
	}
}

void UGolmokSaveSubsystem::OnPhotoSaved(const FString& RelativePath)
{
	NotePhoto(RelativePath);
}

void UGolmokSaveSubsystem::OnVisitPoll()
{
	UWorld* World = ActiveWorld.Get();
	const UGolmokTravelSubsystem* Travel = UGolmokTravelSubsystem::Get(World);
	if (!World || (Travel && Travel->IsTraveling()) || !TakeSnapshot(*World))
	{
		return; // mid-travel (restore included) the pawn is still at the old place: neither a visit nor a position to save
	}
	if (!bBaselineSet)
	{
		// "Changed" is measured from the first snapshot of this world, not from (0,0,0).
		LastSavedLocationUE = Snapshot.LocationUE;
		LastSavedYawUE = Snapshot.YawUE;
		bBaselineSet = true;
	}
	if (!Snapshot.ZoneId.IsEmpty() && !IsVisited(Snapshot.ZoneId))
	{
		NoteVisit(Snapshot.ZoneId, Snapshot.ZoneVersion, TEXT("entered"));
	}
	if (!bAutomatic)
	{
		return;
	}
	const double MovedM = FVector::Dist2D(Snapshot.LocationUE, LastSavedLocationUE) / 100.0;
	const double TurnedDeg = Snapshot.YawUE - LastSavedYawUE;
	if (GolmokTravelMath::ShouldAutosave(FPlatformTime::Seconds(), LastSaveSeconds, AutosaveIntervalSeconds, bDirty, MovedM, TurnedDeg))
	{
		SaveNow(/*bSync*/ false, TEXT("periodic"));
	}
}

// ---- restore --------------------------------------------------------------------------------------------------

void UGolmokSaveSubsystem::OnRestoreTick()
{
	UWorld* World = ActiveWorld.Get();
	if (!World)
	{
		return;
	}
	if (!GolmokSavePrivate::PlayerPawn(World) && ++RestoreAttempts < GolmokSavePrivate::MaxRestoreAttempts)
	{
		World->GetTimerManager().SetTimer(RestoreTimer, FTimerDelegate::CreateUObject(this, &UGolmokSaveSubsystem::OnRestoreTick),
			GolmokSavePrivate::RestoreRetrySeconds, false);
		return;
	}
	FString Message;
	Restore(Message);
	UE_LOG(LogGolmok, Log, TEXT("GolmokSave: restore on begin play: %s"), *Message);
}

bool UGolmokSaveSubsystem::Restore(FString& OutMessage)
{
	UWorld* World = ActiveWorld.Get();
	UGolmokZoneSubsystem* Zones = World ? World->GetSubsystem<UGolmokZoneSubsystem>() : nullptr;
	UGolmokTravelSubsystem* Travel = UGolmokTravelSubsystem::Get(World);
	UGolmokGeoSubsystem* Geo = World ? World->GetSubsystem<UGolmokGeoSubsystem>() : nullptr;
	LastRestoreDecision = GolmokTravelMath::ERestore::None;
	if (!World || !Zones || !Travel)
	{
		OutMessage = TEXT("no game world");
		return false;
	}
	const UGolmokSaveGame* Save = LoadSlot();
	if (!Save)
	{
		OutMessage = FString::Printf(TEXT("no save in slot %s: nothing restored (PlayerStart kept)"), *SlotName);
		return false;
	}
	if (Save->SaveSchemaVersion != UGolmokSaveGame::CurrentSchemaVersion)
	{
		OutMessage = FString::Printf(TEXT("slot %s has save schema %d (expected %d): nothing restored"), *SlotName, Save->SaveSchemaVersion,
			UGolmokSaveGame::CurrentSchemaVersion);
		return false;
	}

	// Index: the file system is the source of truth for photos.
	Visited = Save->Visited;
	Photos.Reset();
	int32 Dropped = 0;
	for (const FString& Rel : Save->Photos)
	{
		if (GolmokSavePrivate::PhotoExists(Rel))
		{
			Photos.AddUnique(Rel);
		}
		else
		{
			++Dropped;
		}
	}

	const int32 IndexVersion = Save->ZoneId.IsEmpty() ? 0 : Zones->ResolveZoneVersion(Save->ZoneId);
	const bool bHomeKnown = !HomeZoneId.IsEmpty() && Zones->ResolveZoneVersion(HomeZoneId) > 0;
	const bool bHasPosition = Save->bHasPosition && Geo && Geo->HasOrigin();
	LastRestoreDecision = GolmokTravelMath::DecideRestore(true, bHasPosition, Save->ZoneId.IsEmpty(), Save->ZoneVersion, IndexVersion, bHomeKnown);

	bool bOk = true;
	FString TravelMessage;
	switch (LastRestoreDecision)
	{
	case GolmokTravelMath::ERestore::SavedPosition:
	{
		FVector LocationUE = FVector::ZeroVector;
		Geo->LonLatToLevelUE(Save->Lon, Save->Lat, Save->HeightEllipsoidal, LocationUE);
		const float YawUE = static_cast<float>(GolmokTravelMath::EnuYawToUEYaw(Save->YawDeg));
		bOk = Travel->TravelToLocation(Save->ZoneId, LocationUE, YawUE, TravelMessage);
		break;
	}
	case GolmokTravelMath::ERestore::SavedZoneSpawn:
		bOk = Travel->TravelToZone(Save->ZoneId, TravelMessage);
		break;
	case GolmokTravelMath::ERestore::HomeZoneSpawn:
		bOk = Travel->TravelToZone(HomeZoneId, TravelMessage);
		break;
	case GolmokTravelMath::ERestore::None:
	default:
		bOk = false;
		TravelMessage = TEXT("no usable position / zone (PlayerStart kept)");
		break;
	}

	// Time of day (spec §4: preset name until WP-14a) and character (WP-18 public API; Astra files unchanged).
	FString Extras;
	if (!Save->TimeOfDay.PresetName.IsEmpty())
	{
		if (AGolmokTimeOfDay* Tod = AGolmokTimeOfDay::Find(World))
		{
			const bool bApplied = Tod->ApplyPreset(FName(*Save->TimeOfDay.PresetName), /*bInstant*/ true);
			Extras += FString::Printf(TEXT(", tod %s%s"), *Save->TimeOfDay.PresetName, bApplied ? TEXT("") : TEXT(" (unknown preset)"));
		}
	}
	if (!Save->CharacterId.IsEmpty())
	{
		if (UGolmokCharacterSubsystem* Characters = World->GetSubsystem<UGolmokCharacterSubsystem>())
		{
			if (Characters->GetCurrentId() != Save->CharacterId)
			{
				FString CharacterMessage;
				const bool bSelected = Characters->SelectCharacter(Save->CharacterId, CharacterMessage);
				Extras += FString::Printf(TEXT(", character %s%s"), *Save->CharacterId, bSelected ? TEXT("") : TEXT(" (not applied)"));
			}
		}
	}
	OutMessage = FString::Printf(TEXT("restore %s from slot %s (saved %s, zone %s v%d, index v%d): %s%s; visited %d, photos %d (%d missing dropped)"),
		ANSI_TO_TCHAR(GolmokTravelMath::RestoreName(LastRestoreDecision)), *SlotName, *Save->SavedAtUtc,
		Save->ZoneId.IsEmpty() ? TEXT("-") : *Save->ZoneId, Save->ZoneVersion, IndexVersion, *TravelMessage, *Extras, Visited.Num(), Photos.Num(),
		Dropped);
	LastMessage = OutMessage;
	if (Dropped > 0)
	{
		MarkDirty();
	}
	return bOk;
}

bool UGolmokSaveSubsystem::ResetSlot(FString& OutMessage)
{
	const bool bHad = HasSave();
	const bool bDeleted = !bHad || UGameplayStatics::DeleteGameInSlot(SlotName, GolmokSavePrivate::UserIndex);
	Visited.Reset();
	Photos.Reset();
	bDirty = false;
	OutMessage = FString::Printf(TEXT("slot %s %s; visit / photo index cleared"), *SlotName,
		!bHad ? TEXT("was empty") : (bDeleted ? TEXT("deleted") : TEXT("could NOT be deleted")));
	LastMessage = OutMessage;
	return bDeleted;
}

FString UGolmokSaveSubsystem::DescribeStatus() const
{
	FString Out = FString::Printf(TEXT("golmok.save: slot %s (%s), automatic %s, restore %s%s, home '%s', autosave %.0f s, pending async %d, saves %d"),
		*SlotName, HasSave() ? TEXT("exists") : TEXT("empty"), bAutomatic ? TEXT("on") : TEXT("off"), bRestoreOnBeginPlay ? TEXT("on") : TEXT("off"),
		FParse::Param(FCommandLine::Get(), TEXT("GolmokNoRestore")) ? TEXT(" (-GolmokNoRestore)") : TEXT(""), *HomeZoneId,
		AutosaveIntervalSeconds, PendingAsync, CompletedSaves);
	Out += FString::Printf(TEXT("\n  memory: visited %d, photos %d, dirty %s, last restore: %s"), Visited.Num(), Photos.Num(),
		bDirty ? TEXT("yes") : TEXT("no"), ANSI_TO_TCHAR(GolmokTravelMath::RestoreName(LastRestoreDecision)));
	if (const UGolmokSaveGame* Save = LoadSlot())
	{
		Out += FString::Printf(TEXT("\n  slot: schema %d, saved %s, zone %s v%d, position %s (lat %.7f lon %.7f h %.2f, yaw %.1f), tod %s, character %s, visited %d, photos %d"),
			Save->SaveSchemaVersion, *Save->SavedAtUtc, Save->ZoneId.IsEmpty() ? TEXT("-") : *Save->ZoneId, Save->ZoneVersion,
			Save->bHasPosition ? TEXT("yes") : TEXT("no"), Save->Lat, Save->Lon, Save->HeightEllipsoidal, Save->YawDeg,
			Save->TimeOfDay.PresetName.IsEmpty() ? TEXT("-") : *Save->TimeOfDay.PresetName, Save->CharacterId.IsEmpty() ? TEXT("-") : *Save->CharacterId,
			Save->Visited.Num(), Save->Photos.Num());
	}
	if (!LastMessage.IsEmpty())
	{
		Out += FString::Printf(TEXT("\n  last: %s"), *LastMessage);
	}
	return Out;
}

// ---- console --------------------------------------------------------------------------------------------------

namespace GolmokSaveConsole
{
	UGolmokSaveSubsystem* SaveFor(UWorld* World)
	{
		UGolmokSaveSubsystem* Save = UGolmokSaveSubsystem::Get(World);
		if (!Save)
		{
			UE_LOG(LogGolmok, Warning, TEXT("golmok.save: no game instance (game / PIE world only)"));
		}
		return Save;
	}

	void CmdSave(const TArray<FString>& Args, UWorld* World)
	{
		UGolmokSaveSubsystem* Save = SaveFor(World);
		if (!Save)
		{
			return;
		}
		const FString Sub = Args.Num() > 0 ? Args[0] : FString();
		if (Sub.IsEmpty())
		{
			FString Message;
			const bool bOk = Save->SaveNow(/*bSync*/ true, TEXT("console"), &Message);
			UE_LOG(LogGolmok, Log, TEXT("golmok.save: %s%s"), bOk ? TEXT("") : TEXT("ERROR "), *Message);
		}
		else if (Sub.Equals(TEXT("status"), ESearchCase::IgnoreCase))
		{
			UE_LOG(LogGolmok, Log, TEXT("%s"), *Save->DescribeStatus());
		}
		else if (Sub.Equals(TEXT("reset"), ESearchCase::IgnoreCase))
		{
			FString Message;
			const bool bOk = Save->ResetSlot(Message);
			UE_LOG(LogGolmok, Log, TEXT("golmok.save reset: %s%s"), bOk ? TEXT("") : TEXT("ERROR "), *Message);
		}
		else
		{
			UE_LOG(LogGolmok, Warning, TEXT("usage: golmok.save [status|reset]"));
		}
	}

	void CmdLoad(const TArray<FString>& Args, UWorld* World)
	{
		if (UGolmokSaveSubsystem* Save = SaveFor(World))
		{
			FString Message;
			const bool bOk = Save->Restore(Message);
			UE_LOG(LogGolmok, Log, TEXT("golmok.load: %s%s"), bOk ? TEXT("") : TEXT("(nothing restored) "), *Message);
		}
	}

	FAutoConsoleCommandWithWorldAndArgs GCmdSave(TEXT("golmok.save"),
		TEXT("golmok.save [status|reset]: save now (synchronous) / show the slot / delete the slot and the visit-photo index."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdSave));
	FAutoConsoleCommandWithWorldAndArgs GCmdLoad(TEXT("golmok.load"), TEXT("golmok.load: restore the automatic save now (spec rules 1-3)."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdLoad));
} // namespace GolmokSaveConsole
