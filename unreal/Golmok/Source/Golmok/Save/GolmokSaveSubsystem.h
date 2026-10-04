#pragma once

#include "CoreMinimal.h"
#include "Map/GolmokTravelMath.h"
#include "Save/GolmokSaveGame.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "TimerManager.h"
#include "GolmokSaveSubsystem.generated.h"

class FViewport;
class UGameViewportClient;
class UWorld;
struct FGolmokCharacterRoster;

/** The saved WP-18 character (R91-1). Pure, so Golmok.Save.RoundTrip checks it without a pawn or roster assets. */
namespace GolmokSaveCharacter
{
	/**
	 * True for a save written before UGolmokSaveGame::CharacterIdRule (rule 0) whose id is a roster default (`default` or
	 * a `default_by_anim_mode` value): such saves also kept automatic picks, so Restore leaves the mode default in place
	 * instead of pinning that id with SelectCharacter. A legacy non-default id (e.g. quinn) was chosen and is restored as
	 * an explicit choice; a rule 1 id is always explicit.
	 */
	bool IsLegacyDefault(int32 Rule, const FString& SavedId, const FGolmokCharacterRoster& Roster);
} // namespace GolmokSaveCharacter

/**
 * Automatic save (WP-15a, D-017; docs/plan/WP-15-zone-travel-save.md §3). Game instance subsystem: one slot
 * (SlotName, user index 0), UGolmokSaveGame, written with UGameplayStatics::AsyncSaveGameToSlot while playing and with
 * the synchronous SaveGameToSlot when the world ends (an async write during shutdown can be lost).
 *
 * Triggers: travel arrival (UGolmokTravelSubsystem::OnTraveled), first visit (a loaded zone's footprint contains the
 * player for the first time; polled every VisitPollSeconds, never per frame), photo saved (WP-12 OnPhotoSaved hook),
 * every AutosaveIntervalSeconds when something changed, world end and FCoreDelegates::OnPreExit (synchronous). The
 * synchronous end saves write a snapshot refreshed when the game viewport is asked to close (PIE stop / exit, game window
 * closed: the engine then removes the local player, destroying its controller, before the world tears down) and at
 * FWorldDelegates::OnWorldBeginTearDown (-game quit / map change: actors still valid there), not the last poll.
 *
 * Restore (bRestoreOnBeginPlay; the command line switch -GolmokNoRestore turns it off for runbooks / automation): the
 * travel subsystem's OnWorldBeginPlay calls HandleWorldBeginPlay, which loads the visit / photo index and, one tick
 * later (retried until a pawn exists), applies the spec §3 rules through GolmokTravelMath::DecideRestore:
 * ① saved zone in the level / index with the same version -> the saved position (preloaded through
 * UGolmokTravelSubsystem::TravelToLocation) ② another version -> that zone's spawn; zone gone -> HomeZoneId's spawn
 * ③ otherwise nothing (PlayerStart). Then the time of day (WP-14a {Minutes, Mode} per mode, instant; a save without
 * minutes -> its preset) and the WP-18 character are applied. Only an explicit character selection is saved (R91-1,
 * UGolmokSaveGame::CharacterIdRule); a legacy save's roster default is not re-applied; an explicit id this world refuses
 * stays in the save (UnappliedCharacterId).
 * GameMode / PlayerController are not touched (hot-spot rule).
 *
 * While automation tests run (GIsAutomationTesting) nothing is written or restored automatically, so a developer's
 * save never changes a test and a test never overwrites it; tests call SetAutomaticEnabled / SaveNow / Restore on
 * their own slot.
 * Console: golmok.save | golmok.save status | golmok.save reset | golmok.load
 * Config: [/Script/Golmok.GolmokSaveSubsystem] (defaults in code; no DefaultGame.ini keys needed).
 */
UCLASS(Config = Game)
class GOLMOK_API UGolmokSaveSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	/** Restore the saved state after the world begins play (off with -GolmokNoRestore). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Save")
	bool bRestoreOnBeginPlay = true;

	/** Also restore at PIE begin play. Off by default so the existing PIE runbooks (V-03/V-07/V-09/V-10) always start at the PlayerStart; golmok.load and standalone -game runs restore. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Save")
	bool bRestoreInPIE = false;

	/** Fallback zone (spec §3 ②) when the saved zone is gone. Empty = keep the PlayerStart. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Save")
	FString HomeZoneId;

	/** Periodic autosave interval (s); only writes when something changed. 0 = off. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Save", meta = (ClampMin = "0.0"))
	float AutosaveIntervalSeconds = 60.f;

	/** First-visit / snapshot poll interval (s). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Save", meta = (ClampMin = "0.1"))
	float VisitPollSeconds = 1.f;

	/** The automatic slot (user index 0). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Save")
	FString SlotName = TEXT("golmok_auto");

	// ---- world hooks (UGolmokTravelSubsystem::OnWorldBeginPlay / Deinitialize) -----------------------------------

	void HandleWorldBeginPlay(UWorld& InWorld);
	void HandleWorldEnd(UWorld* InWorld);

	// ---- API (console, tests) ------------------------------------------------------------------------------------

	/** Snapshot the world (when there is one) and write. bSync = SaveGameToSlot, else AsyncSaveGameToSlot. */
	bool SaveNow(bool bSync, const TCHAR* Reason, FString* OutMessage = nullptr);

	/** Apply the spec §3 rules to the slot now (golmok.load). False + message when nothing was restored. */
	bool Restore(FString& OutMessage);

	/**
	 * Delete the slot and clear the in-memory visit / photo index and UnappliedCharacterId (golmok.save reset). No
	 * automatic write follows until a new visit / photo / travel or golmok.save; the zones the player stands in at the
	 * reset are no "first visit" until the player has left them (else the next poll would write the slot again at once).
	 */
	bool ResetSlot(FString& OutMessage);

	/** Stop holding the slot's position (see HoldSlotPosition): golmok.save calls it, an explicit save means "here". */
	void ReleaseHold(const TCHAR* Why);

	bool HasSave() const;
	/** Read the slot (nullptr when there is none or it is not a UGolmokSaveGame). */
	UGolmokSaveGame* LoadSlot() const;
	/** A UGolmokSaveGame from the current snapshot and index (not written). */
	UGolmokSaveGame* BuildSaveObject();

	bool IsVisited(const FString& ZoneId) const;
	/** Record a visit (first time only) and, when automatic, save. True when it was new. */
	bool NoteVisit(const FString& ZoneId, int32 Version, const TCHAR* Why);
	/** Record a photo path (relative to <Project>/Saved/) and, when automatic, save. */
	void NotePhoto(const FString& RelativePath);

	const TArray<FGolmokSaveVisit>& GetVisited() const { return Visited; }
	const TArray<FString>& GetPhotos() const { return Photos; }
	GolmokTravelMath::ERestore GetLastRestoreDecision() const { return LastRestoreDecision; }
	int32 GetCompletedSaves() const { return CompletedSaves; }
	int32 GetPendingAsyncSaves() const { return PendingAsync; }

	/** Automatic triggers (restore at begin play, autosaves). Default: on, off while GIsAutomationTesting. */
	void SetAutomaticEnabled(bool bEnabled) { bAutomatic = bEnabled; }
	bool IsAutomaticEnabled() const { return bAutomatic; }

	/** Test hook (Golmok.Save.RoundTrip): run one first-visit / periodic-autosave poll now instead of waiting for the timer. */
	void PollVisitsNow() { OnVisitPoll(); }
	/** Zones the player stood in at the last golmok.save reset and has not left yet (no first visit for them). */
	const TSet<FString>& GetResetPresentZoneIds() const { return ResetPresentZoneIds; }

	FString DescribeStatus() const;

	static UGolmokSaveSubsystem* Get(const UWorld* World);

private:
	/** Cached world state (what the next save writes). UE location / yaw are kept in memory only, never saved. */
	struct FSnapshot
	{
		bool bValid = false;
		bool bHasPosition = false;
		double Lat = 0.0;
		double Lon = 0.0;
		double HeightEllipsoidal = 0.0;
		double YawDeg = 0.0;
		FString ZoneId;
		int32 ZoneVersion = 0;
		FString TodPreset;
		float TodMinutes = -1.f; // WP-14a clock minutes; -1 = restore by TodPreset
		uint8 TodMode = 0;       // EGolmokClockMode as uint8
		FString CharacterId;     // explicit WP-18 selection or UnappliedCharacterId (R91-1); empty = automatic / unknown
		int32 CharacterIdRule = UGolmokSaveGame::CharacterIdRuleExplicit; // the slot's own rule only while HoldSlotPosition passes its id through
		FGolmokSaveWeather Weather; // WP-16a: rule 1 from UGolmokWeatherSubsystem; rule 0 = weather off / none (the slot's own while held)
		FVector LocationUE = FVector::ZeroVector;
		double YawUE = 0.0;
	};

	/** bForce: also while the world is tearing down (OnViewportCloseRequested / OnWorldBeginTearDown); without a pawn the last snapshot is kept. */
	bool TakeSnapshot(UWorld& InWorld, bool bForce = false);
	/** The slot's position / zone become the snapshot and are held (not overwritten by the pawn at the PlayerStart) until a
	 *  travel arrives or the pawn walks more than HoldReleaseCm from where it stood: a failed / pending restore never loses the save. */
	void HoldSlotPosition(const UGolmokSaveGame& Save);
	static FString LevelNameOf(const UWorld& InWorld);
	void LoadIndexFromSlot();
	void OnTraveled(const FString& ZoneId);
	void OnPhotoSaved(const FString& RelativePath);
	void OnVisitPoll();
	void OnRestoreTick();
	void OnPreExit();
	void OnWorldBeginTearDown(UWorld* InWorld);
	void OnViewportCloseRequested(FViewport* InViewport);
	void UnbindViewportClose();
	void OnAsyncSaved(const FString& InSlotName, const int32 InUserIndex, bool bSuccess);
	void MarkDirty() { bDirty = true; }
	/** WP-16a: a weather target change makes the next periodic autosave write (not while Restore applies the saved weather). */
	void OnWeatherChanged();
	/** Applies the slot's weather (WP-16a design section 12) after the time of day; returns ", weather ..." for the restore message. */
	FString RestoreWeather(const FGolmokSaveWeather& Saved);

	TWeakObjectPtr<UWorld> ActiveWorld;
	FTimerHandle VisitTimer;
	FTimerHandle RestoreTimer;
	FDelegateHandle TraveledHandle;
	FDelegateHandle PhotoHandle;
	FDelegateHandle PreExitHandle;
	FDelegateHandle TearDownHandle;
	TWeakObjectPtr<UGameViewportClient> CloseViewport; // the active world's game viewport (OnCloseRequested bound)
	FDelegateHandle ViewportCloseHandle;
	FDelegateHandle WeatherHandle; // UGolmokWeatherSubsystem::OnWeatherChanged of ActiveWorld (WP-16a)
	bool bRestoringWeather = false; // Restore is applying the saved weather: its own OnWeatherChanged is no change to save

	TArray<FGolmokSaveVisit> Visited;
	TArray<FString> Photos;
	FSnapshot Snapshot;
	FVector LastSavedLocationUE = FVector::ZeroVector;
	double LastSavedYawUE = 0.0;
	double LastSaveSeconds = -1.0e9;
	GolmokTravelMath::ERestore LastRestoreDecision = GolmokTravelMath::ERestore::None;
	FString LastMessage;
	int32 RestoreAttempts = 0;
	int32 PendingAsync = 0;
	int32 CompletedSaves = 0;
	bool bAutomatic = true;
	bool bDirty = false;
	bool bSaveQueued = false;
	bool bBaselineSet = false;
	FSnapshot Held;              // slot position while bHoldSlotPosition
	FVector HoldAnchorUE = FVector::ZeroVector;
	bool bHoldSlotPosition = false;
	bool bHoldAnchorSet = false;
	bool bRestorePending = false; // restore scheduled, not run yet: no visit saves / autosaves before it
	bool bSuppressWrites = false; // after golmok.save reset: no automatic write until a new visit / photo / travel or golmok.save
	TSet<FString> ResetPresentZoneIds; // zones the player stood in at golmok.save reset: no first visit until left (transient)
	bool bSyncAfterAsync = false; // a sync write happened while an async one was in flight: rewrite once it completes
	/** An explicit id whose restore was refused in this world (R91-1 follow-up V1), kept until a new explicit pick: while the
	 *  selection is automatic, TakeSnapshot saves it (rule 1) so a failed restore never loses the save. Reset per world. */
	FString UnappliedCharacterId;
	static constexpr double HoldReleaseCm = 200.0;
};
