#include "Save/GolmokSaveSubsystem.h"

#include "Golmok.h"

#include "Characters/GolmokCharacterSubsystem.h"
#include "CoreGlobals.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Geo/GolmokGeoSubsystem.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformTime.h"
#include "Kismet/GameplayStatics.h"
#include "Lighting/GolmokClockMath.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Map/GolmokTravelSubsystem.h"
#include "Misc/CommandLine.h"
#include "Misc/CoreDelegates.h"
#include "Misc/DateTime.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Photo/GolmokPhotoModeSubsystem.h"
#include "TimerManager.h"
#include "UObject/Package.h"
#include "EngineUtils.h"
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

	/** Ids of the zones whose footprint contains the level XY point, loaded or not (the manifest footprint is enough). */
	TSet<FString> ZonesContaining(UWorld& World, const FVector2D& PointUE)
	{
		TSet<FString> Out;
		for (TActorIterator<AGolmokZone> It(&World); It; ++It)
		{
			AGolmokZone* Zone = *It;
			if (Zone && !Zone->ZoneId.IsEmpty() && Zone->FootprintContains(PointUE))
			{
				Out.Add(Zone->ZoneId);
			}
		}
		return Out;
	}

	/** "; no first visit for a, b until you leave" (sorted) or empty: golmok.save reset / status. */
	FString ResetPresentNote(const TSet<FString>& ZoneIds)
	{
		if (ZoneIds.Num() == 0)
		{
			return FString();
		}
		TArray<FString> Sorted = ZoneIds.Array();
		Sorted.Sort();
		return FString::Printf(TEXT("; no first visit for %s until you leave"), *FString::Join(Sorted, TEXT(", ")));
	}

	// ---- time of day (WP-14a clock; only AGolmokTimeOfDay's public API) ----

	/** The saved uint8 back to EGolmokClockMode; an unknown value restores as Fixed. */
	EGolmokClockMode SavedClockMode(uint8 Raw)
	{
		return Raw <= static_cast<uint8>(EGolmokClockMode::Realtime) ? static_cast<EGolmokClockMode>(Raw) : EGolmokClockMode::Fixed;
	}

	FString HhmmText(double Minutes)
	{
		TCHAR Hhmm[6];
		GolmokClockMath::FormatHHMM(Minutes, Hhmm);
		return FString(Hhmm);
	}

	/**
	 * Minutes to save (spec §3): the clock time, or -1 when there is no time to restore - the level's own lighting
	 * (HasTimeOfDay() false) or, in Fixed mode, a base preset without a keyframe time (e.g. "interior" applied as a base).
	 * Those restore by PresetName (ApplyPreset), as before WP-14a.
	 */
	float TodMinutesToSave(const AGolmokTimeOfDay& Tod)
	{
		if (!Tod.HasTimeOfDay())
		{
			return -1.f;
		}
		FGolmokLightingPreset Preset;
		if (Tod.GetClockMode() == EGolmokClockMode::Fixed && !Tod.CurrentPreset.IsNone() && Tod.FindPreset(Tod.CurrentPreset, Preset) && !Preset.bHasTime)
		{
			return -1.f;
		}
		return Tod.GetTimeOfDayMinutes();
	}

	/** "13:07 clock (clear_noon)" | "night" (no minutes: restored by name) | "-": save log and golmok.save status. */
	FString DescribeSavedTod(const FGolmokSaveTimeOfDay& Tod)
	{
		if (Tod.Minutes >= 0.f && FMath::IsFinite(Tod.Minutes))
		{
			const FString Preset = Tod.PresetName.IsEmpty() ? FString() : FString::Printf(TEXT(" (%s)"), *Tod.PresetName);
			return FString::Printf(TEXT("%s %s%s"), *HhmmText(Tod.Minutes), AGolmokTimeOfDay::ClockModeName(SavedClockMode(Tod.Mode)), *Preset);
		}
		return Tod.PresetName.IsEmpty() ? FString(TEXT("-")) : Tod.PresetName;
	}

	/**
	 * Applies a saved time of day instantly (spec §3 / §4) and returns ", tod ..." for the restore message.
	 * Minutes >= 0: the clock is stopped first (SetClockMode(Fixed); SetClockMode(Clock) from a preset base and
	 * SetClockMode(Realtime) would each start a transition, and SetTimeOfDay in Realtime falls back to Fixed), so
	 * SetTimeOfDay(time, bInstant) is the one jump; then the saved mode: Fixed stays, Clock runs on from the saved minutes
	 * (already on the clock: SetClockMode does not jump again), Realtime uses the PC's local time instead of the saved
	 * minutes (SetClockMode(Realtime) re-syncs to that same time). Minutes < 0 (a save from before WP-14a) or no keyframes:
	 * ApplyPreset(PresetName, true), the WP-15a path.
	 */
	FString RestoreTimeOfDay(AGolmokTimeOfDay& Tod, const FGolmokSaveTimeOfDay& Saved)
	{
		FString Note;
		if (Saved.Minutes >= 0.f && FMath::IsFinite(Saved.Minutes))
		{
			const EGolmokClockMode Mode = SavedClockMode(Saved.Mode);
			Tod.SetClockMode(EGolmokClockMode::Fixed);
			const double Minutes = Mode == EGolmokClockMode::Realtime ? Tod.RealtimeTargetMinutes() : static_cast<double>(Saved.Minutes);
			if (Tod.SetTimeOfDay(static_cast<float>(Minutes), /*bInstant*/ true) && (Mode == EGolmokClockMode::Fixed || Tod.SetClockMode(Mode)))
			{
				return FString::Printf(TEXT(", tod %s %s%s"), *HhmmText(Tod.GetTimeOfDayMinutes()), AGolmokTimeOfDay::ClockModeName(Tod.GetClockMode()),
					Mode == EGolmokClockMode::Realtime ? TEXT(" (local time)") : TEXT(""));
			}
			Note = FString::Printf(TEXT(" (%s %s not applied: %s)"), *HhmmText(Saved.Minutes), AGolmokTimeOfDay::ClockModeName(Mode), *Tod.LastError);
		}
		if (Saved.PresetName.IsEmpty())
		{
			return Note.IsEmpty() ? FString() : FString::Printf(TEXT(", tod -%s"), *Note);
		}
		const bool bApplied = Tod.ApplyPreset(FName(*Saved.PresetName), /*bInstant*/ true);
		return FString::Printf(TEXT(", tod %s%s%s"), *Saved.PresetName, bApplied ? TEXT("") : TEXT(" (unknown preset)"), *Note);
	}

	/** "quinn" (explicit) | "- (automatic)" (rule 1, nothing pinned) | "manny (legacy)" / "-" (rule 0): golmok.save status. */
	FString DescribeSavedCharacter(const UGolmokSaveGame& Save)
	{
		if (Save.CharacterIdRule >= UGolmokSaveGame::CharacterIdRuleExplicit)
		{
			return Save.CharacterId.IsEmpty() ? FString(TEXT("- (automatic)")) : Save.CharacterId;
		}
		return Save.CharacterId.IsEmpty() ? FString(TEXT("-")) : FString::Printf(TEXT("%s (legacy)"), *Save.CharacterId);
	}
} // namespace GolmokSavePrivate

namespace GolmokSaveCharacter
{
	bool IsLegacyDefault(int32 Rule, const FString& SavedId, const FGolmokCharacterRoster& Roster)
	{
		if (Rule >= UGolmokSaveGame::CharacterIdRuleExplicit || SavedId.IsEmpty())
		{
			return false;
		}
		return SavedId == Roster.DefaultId || Roster.DefaultByAnimMode.FindKey(SavedId) != nullptr;
	}
} // namespace GolmokSaveCharacter

// ---- lifecycle ------------------------------------------------------------------------------------------------

void UGolmokSaveSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	// A developer's slot never changes an automation test and a test never overwrites it (tests opt in on their own slot).
	bAutomatic = !GIsAutomationTesting;
	AutosaveIntervalSeconds = FMath::Max(0.f, AutosaveIntervalSeconds);
	VisitPollSeconds = FMath::Max(0.1f, VisitPollSeconds);
	PreExitHandle = FCoreDelegates::OnPreExit.AddUObject(this, &UGolmokSaveSubsystem::OnPreExit);
	TearDownHandle = FWorldDelegates::OnWorldBeginTearDown.AddUObject(this, &UGolmokSaveSubsystem::OnWorldBeginTearDown);
}

void UGolmokSaveSubsystem::Deinitialize()
{
	FCoreDelegates::OnPreExit.Remove(PreExitHandle);
	PreExitHandle.Reset();
	FWorldDelegates::OnWorldBeginTearDown.Remove(TearDownHandle);
	TearDownHandle.Reset();
	HandleWorldEnd(ActiveWorld.Get());
	UnbindViewportClose();
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
	bHoldSlotPosition = false;
	bRestorePending = false;
	ResetPresentZoneIds.Reset(); // a golmok.save reset in another world: that world's zones say nothing about this one
	UnappliedCharacterId.Reset(); // a refusal in another world (its pawn / mode): this world's restore decides again
	LoadIndexFromSlot();

	if (UGolmokTravelSubsystem* Travel = UGolmokTravelSubsystem::Get(&InWorld))
	{
		TraveledHandle = Travel->OnTraveled.AddUObject(this, &UGolmokSaveSubsystem::OnTraveled);
	}
	if (UGolmokPhotoModeSubsystem* Photo = InWorld.GetSubsystem<UGolmokPhotoModeSubsystem>())
	{
		PhotoHandle = Photo->OnPhotoSaved.AddUObject(this, &UGolmokSaveSubsystem::OnPhotoSaved);
	}
	UnbindViewportClose();
	if (UGameViewportClient* Viewport = InWorld.GetGameViewport())
	{
		ViewportCloseHandle = Viewport->OnCloseRequested().AddUObject(this, &UGolmokSaveSubsystem::OnViewportCloseRequested);
		CloseViewport = Viewport;
	}
	InWorld.GetTimerManager().SetTimer(VisitTimer, FTimerDelegate::CreateUObject(this, &UGolmokSaveSubsystem::OnVisitPoll), VisitPollSeconds,
		/*bLoop*/ true);

	const bool bNoRestoreSwitch = FParse::Param(FCommandLine::Get(), TEXT("GolmokNoRestore"));
	const bool bPieBlocked = InWorld.WorldType == EWorldType::PIE && !bRestoreInPIE;
	if (bAutomatic && bRestoreOnBeginPlay && !bNoRestoreSwitch && !bPieBlocked)
	{
		// One tick after BeginPlay (spec §3): the pawn is possessed and the geo origin found by then; retried until a pawn exists.
		// Until it has run, the slot's position is held so no visit / periodic save can overwrite it with the PlayerStart.
		bRestorePending = true;
		if (const UGolmokSaveGame* Saved = LoadSlot())
		{
			HoldSlotPosition(*Saved);
		}
		RestoreTimer = InWorld.GetTimerManager().SetTimerForNextTick(FTimerDelegate::CreateUObject(this, &UGolmokSaveSubsystem::OnRestoreTick));
	}
	else
	{
		UE_LOG(LogGolmok, Log, TEXT("GolmokSave: restore skipped (%s)"),
			!bAutomatic ? TEXT("automatic saves off (automation)")
						: (bNoRestoreSwitch ? TEXT("-GolmokNoRestore")
											: (bPieBlocked ? TEXT("PIE, bRestoreInPIE=False; golmok.load restores") : TEXT("bRestoreOnBeginPlay=False"))));
	}
}

FString UGolmokSaveSubsystem::LevelNameOf(const UWorld& InWorld)
{
	const UPackage* Package = InWorld.GetPackage();
	return Package ? UWorld::RemovePIEPrefix(Package->GetName()) : FString();
}

void UGolmokSaveSubsystem::HoldSlotPosition(const UGolmokSaveGame& Save)
{
	Held = FSnapshot();
	Held.bValid = true;
	Held.bHasPosition = Save.bHasPosition;
	Held.Lat = Save.Lat;
	Held.Lon = Save.Lon;
	Held.HeightEllipsoidal = Save.HeightEllipsoidal;
	Held.YawDeg = Save.YawDeg;
	Held.ZoneId = Save.ZoneId;
	Held.ZoneVersion = Save.ZoneVersion;
	bHoldSlotPosition = true;
	bHoldAnchorSet = false;
	if (!Snapshot.bValid)
	{
		// Nothing sampled yet: the held slot values are what a world-end save would write.
		Snapshot.bValid = true;
		Snapshot.bHasPosition = Held.bHasPosition;
		Snapshot.Lat = Held.Lat;
		Snapshot.Lon = Held.Lon;
		Snapshot.HeightEllipsoidal = Held.HeightEllipsoidal;
		Snapshot.YawDeg = Held.YawDeg;
		Snapshot.ZoneId = Held.ZoneId;
		Snapshot.ZoneVersion = Held.ZoneVersion;
		Snapshot.TodPreset = Save.TimeOfDay.PresetName;
		Snapshot.TodMinutes = Save.TimeOfDay.Minutes;
		Snapshot.TodMode = Save.TimeOfDay.Mode;
		// The slot's character passes through with its own rule (a legacy automatic id must not become rule 1); the
		// first pawn snapshot replaces both with the live explicit selection.
		Snapshot.CharacterId = Save.CharacterId;
		Snapshot.CharacterIdRule = Save.CharacterIdRule;
	}
}

void UGolmokSaveSubsystem::ReleaseHold(const TCHAR* Why)
{
	if (bHoldSlotPosition)
	{
		bHoldSlotPosition = false;
		UE_LOG(LogGolmok, Log, TEXT("GolmokSave: saved position no longer held (%s)"), Why);
	}
}

void UGolmokSaveSubsystem::HandleWorldEnd(UWorld* InWorld)
{
	if (!InWorld || InWorld != ActiveWorld.Get())
	{
		return;
	}
	// Synchronous: an async write during shutdown can be lost (spec §3). The snapshot was refreshed when the game viewport was
	// asked to close (PIE stop / exit, window closed: before the engine destroys the local player's controller) or at
	// OnWorldBeginTearDown (-game quit / map change: actors still valid; TakeSnapshot keeps it once bIsTearingDown is set or
	// the pawn is gone), or is taken now when the world is not tearing down.
	if (bAutomatic && Snapshot.bValid && !bSuppressWrites)
	{
		SaveNow(/*bSync*/ true, TEXT("world end"));
	}
	InWorld->GetTimerManager().ClearTimer(VisitTimer);
	InWorld->GetTimerManager().ClearTimer(RestoreTimer);
	bSaveQueued = false; // the sync save above holds the newest state; a late async completion must not write again
	bRestorePending = false;
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
	UnbindViewportClose();
	ActiveWorld.Reset();
}

void UGolmokSaveSubsystem::OnPreExit()
{
	if (bAutomatic && Snapshot.bValid && !bSuppressWrites)
	{
		SaveNow(/*bSync*/ true, TEXT("pre-exit"));
	}
}

void UGolmokSaveSubsystem::OnWorldBeginTearDown(UWorld* InWorld)
{
	// Map change and the -game quit command set bIsTearingDown here, before EndPlay and before the game instance shuts down:
	// the pawn is still valid, so the world-end / pre-exit sync save writes where the player is now, not the last poll (up to
	// VisitPollSeconds old). PIE stop / PIE exit and a closed game window get here with the local player already removed (no
	// pawn: TakeSnapshot keeps what OnViewportCloseRequested took).
	if (InWorld && InWorld == ActiveWorld.Get())
	{
		TakeSnapshot(*InWorld, /*bForce*/ true);
	}
}

void UGolmokSaveSubsystem::OnViewportCloseRequested(FViewport* InViewport)
{
	// PIE stop / PIE exit (UEditorEngine::EndPlayMap, ULocalPlayer::HandleExitCommand) and closing the game window
	// (UGameEngine::OnGameWindowClosed) close the game viewport first; the engine then removes the local player, destroying
	// its controller (the pawn is unpossessed, so GetPlayerPawn finds none), before the primary world's BeginTearingDown -
	// OnWorldBeginTearDown would keep the last poll (up to VisitPollSeconds old). Here the pawn still stands where the
	// player stopped (R49-2, V-14). Not while a restore is pending (the slot's held values stay, as in OnVisitPoll) and not
	// before the first snapshot of this world (closing at once writes nothing, as before).
	UWorld* World = ActiveWorld.Get();
	if (World && !bRestorePending && Snapshot.bValid)
	{
		TakeSnapshot(*World, /*bForce*/ true);
	}
}

void UGolmokSaveSubsystem::UnbindViewportClose()
{
	if (UGameViewportClient* Viewport = CloseViewport.Get())
	{
		Viewport->OnCloseRequested().Remove(ViewportCloseHandle);
	}
	CloseViewport.Reset();
	ViewportCloseHandle.Reset();
}

// ---- snapshot / index -----------------------------------------------------------------------------------------

bool UGolmokSaveSubsystem::TakeSnapshot(UWorld& InWorld, bool bForce)
{
	if (InWorld.bIsTearingDown && !bForce)
	{
		return Snapshot.bValid; // keep the last one (refreshed at OnViewportCloseRequested / OnWorldBeginTearDown): actors are going away
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
		S.TodMinutes = GolmokSavePrivate::TodMinutesToSave(*Tod); // WP-14a clock
		S.TodMode = static_cast<uint8>(Tod->GetClockMode());
	}
	// R91-1: only an explicit selection is saved (S.CharacterIdRule 1). An automatic mode default / fallback is not, so
	// the next run picks its own mode default (manny_gasp on a GASP pawn) instead of pinning this one; while automatic,
	// an explicit id whose restore this world refused is saved instead (empty when there is none), until a new pick.
	const UGolmokCharacterSubsystem* Characters = InWorld.GetSubsystem<UGolmokCharacterSubsystem>();
	if (Characters && Characters->IsExplicitSelection())
	{
		S.CharacterId = Characters->GetCurrentId();
		UnappliedCharacterId.Reset();
	}
	else if (bRestorePending && Snapshot.bValid)
	{
		// The begin-play restore has not decided yet: keep the slot's character and rule (HoldSlotPosition's pass-through),
		// so a write in that window (world end, travel arrival, golmok.save) does not drop it.
		S.CharacterId = Snapshot.CharacterId;
		S.CharacterIdRule = Snapshot.CharacterIdRule;
	}
	else
	{
		S.CharacterId = UnappliedCharacterId;
	}
	if (bHoldSlotPosition)
	{
		if (!bHoldAnchorSet)
		{
			HoldAnchorUE = S.LocationUE;
			bHoldAnchorSet = true;
		}
		else if (FVector::Dist(HoldAnchorUE, S.LocationUE) > HoldReleaseCm)
		{
			ReleaseHold(TEXT("the player walked away"));
		}
	}
	if (bHoldSlotPosition)
	{
		// Restore pending / refused / timed out: keep writing the slot's position, not the PlayerStart.
		S.bHasPosition = Held.bHasPosition;
		S.Lat = Held.Lat;
		S.Lon = Held.Lon;
		S.HeightEllipsoidal = Held.HeightEllipsoidal;
		S.YawDeg = Held.YawDeg;
		S.ZoneId = Held.ZoneId;
		S.ZoneVersion = Held.ZoneVersion;
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
	Out->TimeOfDay.Minutes = Snapshot.TodMinutes;
	Out->TimeOfDay.Mode = Snapshot.TodMode;
	Out->Visited = Visited;
	Out->Photos = Photos;
	Out->CharacterId = Snapshot.CharacterId;
	Out->CharacterIdRule = Snapshot.CharacterIdRule;
	if (const UWorld* World = ActiveWorld.Get())
	{
		Out->LevelName = LevelNameOf(*World);
	}
	else if (const UGolmokSaveGame* Previous = LoadSlot())
	{
		Out->LevelName = Previous->LevelName; // pre-exit without a world: keep the level of the last save
	}
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
	bSuppressWrites = false; // any real write ends a golmok.save reset
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
		// An async write still in flight may land after this one with older data: write again once it completes.
		bSyncAfterAsync = PendingAsync > 0;
		Message = FString::Printf(TEXT("saved %s (sync, %s)%s"), *SlotName, Reason, bOk ? TEXT("") : TEXT(" FAILED"));
	}
	else
	{
		++PendingAsync;
		UGameplayStatics::AsyncSaveGameToSlot(Save, SlotName, GolmokSavePrivate::UserIndex,
			FAsyncSaveGameToSlotDelegate::CreateUObject(this, &UGolmokSaveSubsystem::OnAsyncSaved));
		Message = FString::Printf(TEXT("saving %s (async, %s)"), *SlotName, Reason);
	}
	UE_LOG(LogGolmok, Log, TEXT("GolmokSave: %s: zone %s, visited %d, photos %d, position %s, tod %s"), *Message,
		Save->ZoneId.IsEmpty() ? TEXT("-") : *Save->ZoneId, Save->Visited.Num(), Save->Photos.Num(), Save->bHasPosition ? TEXT("yes") : TEXT("no"),
		*GolmokSavePrivate::DescribeSavedTod(Save->TimeOfDay));
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
	if (PendingAsync > 0)
	{
		return;
	}
	if (bSuppressWrites)
	{
		// golmok.save reset happened while this write was in flight: delete what it wrote (its own slot: SlotName may have
		// been switched back since, e.g. by a test's cleanup, and must never lose the developer's slot).
		UGameplayStatics::DeleteGameInSlot(InSlotName, InUserIndex);
		bSaveQueued = false;
		bSyncAfterAsync = false;
		return;
	}
	if (bSyncAfterAsync)
	{
		bSyncAfterAsync = false;
		SaveNow(/*bSync*/ true, TEXT("rewrite after async"));
	}
	else if (bSaveQueued && ActiveWorld.IsValid())
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
	bSuppressWrites = false;
	UE_LOG(LogGolmok, Log, TEXT("GolmokSave: first visit %s v%d (%s)"), *ZoneId, Version, Why);
	if (bAutomatic && !bRestorePending)
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
	bSuppressWrites = false;
	if (bAutomatic && !bRestorePending)
	{
		SaveNow(/*bSync*/ false, TEXT("photo"));
	}
}

void UGolmokSaveSubsystem::OnTraveled(const FString& ZoneId)
{
	ReleaseHold(TEXT("travel arrived"));
	bSuppressWrites = false;
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
	if (!World || bRestorePending || (Travel && Travel->IsTraveling()) || !TakeSnapshot(*World))
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
	// First visit (spec §3): every loaded zone whose footprint contains the player, not only the winning one.
	const FVector2D PlayerXY(Snapshot.LocationUE.X, Snapshot.LocationUE.Y);
	// After golmok.save reset the zones the player stood in are no first visit (it would end the reset and write the slot
	// again at once) until the player has left them, or until another event (photo / travel / golmok.save) wrote the slot.
	if (ResetPresentZoneIds.Num() > 0)
	{
		if (bSuppressWrites)
		{
			ResetPresentZoneIds = ResetPresentZoneIds.Intersect(GolmokSavePrivate::ZonesContaining(*World, PlayerXY));
		}
		else
		{
			ResetPresentZoneIds.Reset();
		}
	}
	TArray<TPair<FString, int32>> Entered;
	for (TActorIterator<AGolmokZone> It(World); It; ++It)
	{
		AGolmokZone* Zone = *It;
		if (Zone && Zone->IsLoaded() && !IsVisited(Zone->ZoneId) && !ResetPresentZoneIds.Contains(Zone->ZoneId) && Zone->FootprintContains(PlayerXY))
		{
			Entered.Emplace(Zone->ZoneId, Zone->Version);
		}
	}
	for (const TPair<FString, int32>& Zone : Entered)
	{
		NoteVisit(Zone.Key, Zone.Value, TEXT("entered"));
	}
	if (!bAutomatic || bSuppressWrites)
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
	bRestorePending = false;
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

	const FString Level = LevelNameOf(*World);
	if (!Save->LevelName.IsEmpty() && Save->LevelName != Level)
	{
		// One slot, several dev / spike levels: never apply a position from another level.
		ReleaseHold(TEXT("the save belongs to another level"));
		LastRestoreDecision = GolmokTravelMath::ERestore::None;
		OutMessage = FString::Printf(TEXT("slot %s was saved in %s, this level is %s: position not restored (visit / photo index kept)"), *SlotName,
			*Save->LevelName, *Level);
		LastMessage = OutMessage;
		return false;
	}
	const int32 IndexVersion = Save->ZoneId.IsEmpty() ? 0 : Zones->ResolveZoneVersion(Save->ZoneId);
	const bool bHomeKnown = !HomeZoneId.IsEmpty() && Zones->ResolveZoneVersion(HomeZoneId) > 0;
	const bool bHasPosition = Save->bHasPosition && Geo && Geo->HasOrigin();
	LastRestoreDecision = GolmokTravelMath::DecideRestore(true, bHasPosition, Save->ZoneId.IsEmpty(), Save->ZoneVersion, IndexVersion, bHomeKnown);

	if (LastRestoreDecision != GolmokTravelMath::ERestore::None)
	{
		HoldSlotPosition(*Save); // until the restore travel arrives (or the player walks away after a failure)
	}
	else
	{
		ReleaseHold(TEXT("nothing to restore"));
	}
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
		if (bOk && Save->ZoneId.IsEmpty())
		{
			ReleaseHold(TEXT("placed at the saved basemap position"));
		}
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

	// Time of day (spec §3 / §4: WP-14a {Minutes, Mode} per mode, instant; a save without minutes by its preset) and
	// character (WP-18 public API; Astra files unchanged). Character (R91-1): an empty id (rule 1: the selection was
	// automatic) restores nothing; a legacy save's roster default is left to the mode default instead of being pinned;
	// any other id is an explicit choice and comes back as one (SelectCharacter also when the same id is only applied
	// automatically, so the next save keeps it). A refused explicit id (e.g. a GASP entry on an abp pawn, no character
	// view yet) stays in UnappliedCharacterId for the next save; an id the roster does not know is dropped. It is cleared
	// first: a restore that pins nothing (empty id, legacy default) or applies the id leaves none, so an earlier refusal
	// never leaks into the next save.
	FString Extras;
	if (Save->TimeOfDay.Minutes >= 0.f || !Save->TimeOfDay.PresetName.IsEmpty())
	{
		if (AGolmokTimeOfDay* Tod = AGolmokTimeOfDay::Find(World))
		{
			Extras += GolmokSavePrivate::RestoreTimeOfDay(*Tod, Save->TimeOfDay);
		}
	}
	UnappliedCharacterId.Reset();
	if (!Save->CharacterId.IsEmpty())
	{
		if (UGolmokCharacterSubsystem* Characters = World->GetSubsystem<UGolmokCharacterSubsystem>())
		{
			if (GolmokSaveCharacter::IsLegacyDefault(Save->CharacterIdRule, Save->CharacterId, Characters->GetRoster()))
			{
				Extras += FString::Printf(TEXT(", character %s (legacy default, not pinned)"), *Save->CharacterId);
			}
			else if (Characters->GetCurrentId() != Save->CharacterId || !Characters->IsExplicitSelection())
			{
				FString CharacterMessage;
				const bool bSelected = Characters->SelectCharacter(Save->CharacterId, CharacterMessage);
				// A refused id is kept for the next save when the roster knows it; with a broken roster (load error) a rule-1 id
				// is still the user's explicit choice and is kept too, while a legacy (rule 0) id is dropped, since its legacy
				// defaults cannot be told apart and it must not be promoted to rule 1.
				const bool bKnownId = Characters->GetRoster().Find(Save->CharacterId) != nullptr;
				const bool bKeepOnBrokenRoster =
					!Characters->GetLoadError().IsEmpty() && Save->CharacterIdRule >= UGolmokSaveGame::CharacterIdRuleExplicit;
				UnappliedCharacterId = (!bSelected && (bKnownId || bKeepOnBrokenRoster)) ? Save->CharacterId : FString();
				const TCHAR* Applied = bSelected ? TEXT("")
					: (UnappliedCharacterId.IsEmpty() ? TEXT(" (not applied, not in the roster)") : TEXT(" (not applied, kept for the next save)"));
				Extras += FString::Printf(TEXT(", character %s%s"), *Save->CharacterId, Applied);
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
	UnappliedCharacterId.Reset(); // came from the deleted slot: the next write must not bring it back
	bDirty = false;
	bSaveQueued = false;
	bSyncAfterAsync = false;
	bSuppressWrites = true; // world end / pre-exit / in-flight async must not recreate the slot
	ReleaseHold(TEXT("slot reset"));
	// The zones the player stands in now: the next visit poll must not record them as a first visit (that ends the reset
	// and writes the slot again); OnVisitPoll drops each one once the player has left it.
	ResetPresentZoneIds.Reset();
	if (UWorld* World = ActiveWorld.Get())
	{
		if (const APawn* Pawn = GolmokSavePrivate::PlayerPawn(World))
		{
			const FVector PawnAt = Pawn->GetActorLocation();
			ResetPresentZoneIds = GolmokSavePrivate::ZonesContaining(*World, FVector2D(PawnAt.X, PawnAt.Y));
		}
	}
	OutMessage = FString::Printf(TEXT("slot %s %s; visit / photo index cleared%s"), *SlotName,
		!bHad ? TEXT("was empty") : (bDeleted ? TEXT("deleted") : TEXT("could NOT be deleted")), *GolmokSavePrivate::ResetPresentNote(ResetPresentZoneIds));
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
	if (bSuppressWrites)
	{
		Out += FString::Printf(TEXT("\n  reset: no automatic write until a new visit / photo / travel / golmok.save%s"),
			*GolmokSavePrivate::ResetPresentNote(ResetPresentZoneIds));
	}
	if (const UGolmokSaveGame* Save = LoadSlot())
	{
		Out += FString::Printf(TEXT("\n  slot: schema %d, saved %s, zone %s v%d, position %s (lat %.7f lon %.7f h %.2f, yaw %.1f), tod %s, character %s, visited %d, photos %d"),
			Save->SaveSchemaVersion, *Save->SavedAtUtc, Save->ZoneId.IsEmpty() ? TEXT("-") : *Save->ZoneId, Save->ZoneVersion,
			Save->bHasPosition ? TEXT("yes") : TEXT("no"), Save->Lat, Save->Lon, Save->HeightEllipsoidal, Save->YawDeg,
			*GolmokSavePrivate::DescribeSavedTod(Save->TimeOfDay), *GolmokSavePrivate::DescribeSavedCharacter(*Save),
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
			Save->ReleaseHold(TEXT("console save")); // an explicit save means "here", not the held slot position
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
