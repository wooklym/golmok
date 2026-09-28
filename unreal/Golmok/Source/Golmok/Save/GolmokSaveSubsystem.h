#pragma once

#include "CoreMinimal.h"
#include "Map/GolmokTravelMath.h"
#include "Save/GolmokSaveGame.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "GolmokSaveSubsystem.generated.h"

class UWorld;

/**
 * Automatic save (WP-15a, D-017; docs/plan/WP-15-zone-travel-save.md §3). Game instance subsystem: one slot
 * (SlotName, user index 0), UGolmokSaveGame, written with UGameplayStatics::AsyncSaveGameToSlot while playing and with
 * the synchronous SaveGameToSlot when the world ends (an async write during shutdown can be lost).
 *
 * Triggers: travel arrival (UGolmokTravelSubsystem::OnTraveled), first visit (a loaded zone's footprint contains the
 * player for the first time; polled every VisitPollSeconds, never per frame), photo saved (WP-12 OnPhotoSaved hook),
 * every AutosaveIntervalSeconds when something changed, world end and FCoreDelegates::OnPreExit (synchronous).
 *
 * Restore (bRestoreOnBeginPlay; the command line switch -GolmokNoRestore turns it off for runbooks / automation): the
 * travel subsystem's OnWorldBeginPlay calls HandleWorldBeginPlay, which loads the visit / photo index and, one tick
 * later (retried until a pawn exists), applies the spec §3 rules through GolmokTravelMath::DecideRestore:
 * ① saved zone in the level / index with the same version -> the saved position (preloaded through
 * UGolmokTravelSubsystem::TravelToLocation) ② another version -> that zone's spawn; zone gone -> HomeZoneId's spawn
 * ③ otherwise nothing (PlayerStart). Then the time-of-day preset and the WP-18 character are applied.
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

	/** Delete the slot and clear the in-memory visit / photo index (golmok.save reset). */
	bool ResetSlot(FString& OutMessage);

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
		FString CharacterId;
		FVector LocationUE = FVector::ZeroVector;
		double YawUE = 0.0;
	};

	bool TakeSnapshot(UWorld& InWorld);
	void LoadIndexFromSlot();
	void OnTraveled(const FString& ZoneId);
	void OnPhotoSaved(const FString& RelativePath);
	void OnVisitPoll();
	void OnRestoreTick();
	void OnPreExit();
	void OnAsyncSaved(const FString& InSlotName, const int32 InUserIndex, bool bSuccess);
	void MarkDirty() { bDirty = true; }

	TWeakObjectPtr<UWorld> ActiveWorld;
	FTimerHandle VisitTimer;
	FTimerHandle RestoreTimer;
	FDelegateHandle TraveledHandle;
	FDelegateHandle PhotoHandle;
	FDelegateHandle PreExitHandle;

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
};
