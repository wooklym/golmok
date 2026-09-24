#pragma once

#include "CoreMinimal.h"
#include "Engine/EngineTypes.h"
#include "GameFramework/Actor.h"
#include "Zones/GolmokZoneManifest.h"
#include "GolmokPortal.generated.h"

class AController;
class AGolmokTimeOfDay;
class AGolmokZone;
class APawn;
class UBoxComponent;
class UGolmokZoneSubsystem;
class UPrimitiveComponent;

/** How an entry portal streams its interior sublevel (Config: [/Script/Golmok.GolmokPortal] InteriorStreamingMode). */
UENUM()
enum class EGolmokInteriorStreamingMode : uint8
{
	/** ULevelStreamingDynamic::LoadLevelInstance by package path (default; no map registration needed). */
	LevelInstance,
	/** A ULevelStreaming registered in the persistent level (Window > Levels) is switched on and off. */
	NamedStreamingLevel
};

/** Pending = debounce wait, Active = interior load requested, Leaving = unload delay running. */
UENUM(BlueprintType)
enum class EGolmokPortalState : uint8
{
	Idle,
	Pending,
	Active,
	Leaving
};

/**
 * One door of a zone (manifest portals[]), spawned transiently by AGolmokZone::SpawnPortals() (WP-05 design section 3).
 *
 * An entry portal (bIsEntry, spawned by an exterior zone) is a pawn-only overlap box. Its reactions are deferred to
 * timers so nothing re-enters UGolmokZoneSubsystem::Evaluate() from inside a zone Load(): overlap -> Pending ->
 * (DebounceSeconds) -> RequestLoad(TargetZoneId, pinned) + sublevel stream in -> Active. While the player overlaps,
 * Tick checks the door plane (actor forward = entering direction, UE Yaw = -yaw_deg) and toggles the interior
 * lighting overlay (AGolmokTimeOfDay::EnterInterior / ExitInterior with this PortalId as source). Leaving the box
 * outward -> Leaving -> (UnloadDelaySeconds) -> sublevel stream out + RequestUnload -> Idle.
 *
 * The portal an interior manifest lists to go back out (bIsEntry = false) is a passive marker: no overlap events,
 * shown by the collision debug view only. A round trip (outside -> inside -> outside) is decided by the single entry
 * portal's plane crossing, so the two overlapping doors never toggle the lighting twice.
 *
 * Console: golmok.portal list | golmok.portal enter <portal_id> | golmok.portal leave <portal_id>
 * Config: [/Script/Golmok.GolmokPortal] in DefaultGame.ini.
 */
UCLASS(Config = Game, HideCategories = (Rendering, Replication, Input, LOD, Cooking, Physics, Networking))
class GOLMOK_API AGolmokPortal : public AActor
{
	GENERATED_BODY()

public:
	AGolmokPortal();

	// ---- manifest values (filled by Configure() before FinishSpawning) ---------------------------------------------

	/** portals[].id, e.g. door_1. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Portal")
	FString PortalId;

	/** Zone that spawned this portal. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Portal")
	FString OwnerZoneId;

	/** portals[].to_zone */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Portal")
	FString TargetZoneId;

	/** true: exterior -> interior active trigger. false: the way-back marker an interior zone spawns (passive). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Portal")
	bool bIsEntry = true;

	/** /Game/Golmok/Zones/<interior>/v<n>/L_<interior> (entry portals only; empty for markers). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Portal")
	FString SublevelPackagePath;

	/** portals[].radius_m in cm (trigger half extent in X and Y). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Portal")
	double RadiusCm = 150.0;

	/** portals[].kind, e.g. door. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Portal")
	FString Kind;

	// ---- Config (1:1 with the ini keys; keep the two-line declarations) ---------------------------------------------

	/** LevelInstance: ULevelStreamingDynamic::LoadLevelInstance by package path (default). NamedStreamingLevel: ULevelStreaming registered in the persistent level. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Portal")
	EGolmokInteriorStreamingMode InteriorStreamingMode = EGolmokInteriorStreamingMode::LevelInstance;

	/** Delay between the first pawn overlap and the interior load (debounces capsule jitter; keeps loads off the overlap stack). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Portal", meta = (ClampMin = "0.0"))
	float DebounceSeconds = 0.25f;

	/** Delay between leaving the trigger outward and the interior unload (no load/unload thrash when loitering at the door). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Portal", meta = (ClampMin = "0.0"))
	float UnloadDelaySeconds = 3.f;

	/** Trigger box height, cm (the box stands on the portal point: Z from 0 to TriggerHeightCm). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Portal", meta = (ClampMin = "50.0"))
	float TriggerHeightCm = 250.f;

	/** Distance past the door plane (cm) before a crossing counts, in either direction. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Portal", meta = (ClampMin = "0.0"))
	float CrossingHysteresisCm = 10.f;

	/** Minimum seconds between two plane crossings. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Portal", meta = (ClampMin = "0.0"))
	float MinCrossingIntervalSeconds = 0.25f;

	/** Stream the interior sublevel (SublevelPackagePath) in and out. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Portal")
	bool bStreamSublevel = true;

	/** Toggle the AGolmokTimeOfDay interior overlay on plane crossings. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Portal")
	bool bSwitchLighting = true;

	// ---- state --------------------------------------------------------------------------------------------------

	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Portal|State")
	EGolmokPortalState State = EGolmokPortalState::Idle;

	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Portal|State")
	bool bPlayerOverlapping = false;

	/** Player is on the interior side of the door plane. */
	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Portal|State")
	bool bPlayerInside = false;

	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Portal|State")
	FString LastEvent;

	/** Fill the manifest fields and size the trigger. Called by AGolmokZone::SpawnPortals() before FinishSpawning(). */
	void Configure(const AGolmokZone& OwnerZone, const FGolmokZonePortal& P);

	/** dot(WorldPos - portal location, actor forward) in cm; positive = interior side. */
	double SignedDistanceAlongForward(const FVector& WorldPos) const;

	/** Console / test entry: force Active (RequestLoad + stream in) and mark the player inside. Idempotent. */
	bool EnterInterior(FString& OutMessage);

	/**
	 * Console / test entry: mark the player outside and start the unload delay. Idempotent. Issued while the player
	 * still stands in the trigger, the unload re-arms the debounce (Pending) instead of leaving an Idle portal with a
	 * tracked overlap, so the interior comes back after DebounceSeconds.
	 */
	bool LeaveInterior(FString& OutMessage);

	bool IsSublevelLoaded() const;
	bool IsSublevelVisible() const;

	/** Show / hide the trigger box in game (collision debug view). */
	void SetDebugVisible(bool bVisible);

	/** "door_1 (z_synthetic_001 -> z_synthetic_001_interior) active inside; sublevel visible (LevelInstance)". */
	FString Describe() const;

	UBoxComponent* GetTrigger() const { return Trigger; }

	/** First portal with this id (entry portals preferred over markers). */
	static AGolmokPortal* FindPortal(UWorld* World, const FString& PortalId);

	/** One Describe() line per portal (golmok.portal list). */
	static FString DescribeAll(UWorld* World);

	/** Extension points (door animation etc.); the defaults only log. */
	virtual void OnInteriorEntered();
	virtual void OnInteriorExited();

protected:
	virtual void BeginPlay() override;

	/**
	 * Timers cleared. An entry portal always drops its lighting source (ExitInterior(PortalId) is a no-op when the
	 * source is absent); while Active / Leaving it also streams the sublevel out and, unless the world is tearing down,
	 * schedules UnloadInteriorAfterEndPlay() for the next tick (off the Evaluate() stack; skipped when another Active /
	 * Leaving portal targets the same interior, retried after DebounceSeconds while one is Pending).
	 */
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

	/** Runs only while the player overlaps the trigger: door plane crossing check. */
	virtual void Tick(float DeltaSeconds) override;

	UFUNCTION()
	void OnTriggerBeginOverlap(UPrimitiveComponent* OverlappedComp, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex,
		bool bFromSweep, const FHitResult& SweepResult);

	UFUNCTION()
	void OnTriggerEndOverlap(UPrimitiveComponent* OverlappedComp, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex);

	/**
	 * Player controller 0 possessed another pawn (path playback swaps character <-> AGolmokPathPawn): re-check the
	 * overlap. AController::Possess() first broadcasts (Old, nullptr) from its UnPossess() and then (Old, New) in the
	 * same call; the nullptr broadcast is ignored (a pawn that really goes away ends the overlap through
	 * OnTriggerEndOverlap).
	 */
	UFUNCTION()
	void OnPlayerPawnChanged(APawn* OldPawn, APawn* NewPawn);

private:
	/** UGameplayStatics::GetPlayerPawn(World, 0) == Other (the playback pawn passes too once possessed). */
	bool IsPlayerPawn(const AActor* Other) const;

	/** Overlap bookkeeping for the tracked pawn (no identity check; the handlers and RefreshOverlap() call these). */
	void BeginPlayerOverlap(APawn* Pawn);
	void EndPlayerOverlap();

	/**
	 * Make the overlap state follow Pawn (the current player pawn): enter, leave or swap the tracked pawn in place.
	 * A pawn that does not overlap and stands on the exterior side while bPlayerInside (the hidden character outside
	 * after the path pawn walked into the room, or the reverse) drops the overlay and, when Active, starts the unload
	 * delay, whether or not the previous pawn was still tracked in the box.
	 */
	void RefreshOverlap(APawn* Pawn);

	/** Active -> Leaving with the unload timer (EndPlayerOverlap outward, LeaveInterior, RefreshOverlap, ReleaseSiblings). */
	void StartLeaving(const TCHAR* Event);

	/**
	 * The player left this interior through this door: other entry portals into the same TargetZoneId that still hold
	 * bPlayerInside without an overlap (the door the player came in by) drop their lighting source and start their
	 * own unload delay, so every source is released and OnUnloadDelayElapsed() of the last one unloads the interior.
	 */
	void ReleaseSiblings();

	/** Any entry portal (not Except) targeting ZoneId that is valid, not being destroyed, and passes Pred. */
	static bool AnyEntryPortal(UWorld* World, const FString& ZoneId, const AGolmokPortal* Except, TFunctionRef<bool(const AGolmokPortal&)> Pred);

	/** Another entry portal (not Except) targeting ZoneId is Active / Leaving. */
	static bool IsInteriorZoneInUse(UWorld* World, const FString& ZoneId, const AGolmokPortal* Except);

	/**
	 * Another entry portal (not Except) targeting ZoneId is Pending: the player stands in its box with the debounce
	 * running, so within DebounceSeconds it either Activates (the interior stays in use) or goes Idle. Unloading the
	 * interior in that window would have the sibling reload it right after (load/unload thrash); the unload waits.
	 * Pending itself never counts as "in use": a Pending portal the player leaves goes Idle without unloading, which
	 * would pin the interior forever.
	 */
	static bool HasPendingSibling(UWorld* World, const FString& ZoneId, const AGolmokPortal* Except);

	/**
	 * The RequestUnload(ZoneId) an entry portal owed when it was destroyed while Active / Leaving (EndPlay defers it to
	 * the next tick): skipped when another entry portal targeting ZoneId is Active / Leaving, retried after RetrySeconds
	 * while one is Pending (a re-loaded exterior's fresh portal with the player already in its box), else unloads.
	 */
	static void UnloadInteriorAfterEndPlay(UGolmokZoneSubsystem* Subsystem, const FString& ZoneId, const FString& PortalId, float RetrySeconds);

	/** Pending -> Active: RequestLoad + StreamIn (also when the pawn already left the box on the interior side). */
	void OnDebounceElapsed();

	/**
	 * Leaving -> Idle: StreamOut + RequestUnload, both skipped while another Active / Leaving portal targets the same
	 * interior (the last one out unloads). While another portal is Pending the portal stays Leaving and re-arms its
	 * unload timer for DebounceSeconds (the sibling decides first). With the player still in the trigger (LeaveInterior
	 * at the door) the portal goes Pending with a fresh debounce instead of Idle.
	 */
	void OnUnloadDelayElapsed();

	/** The load step shared by OnDebounceElapsed() and EnterInterior(): zone RequestLoad + sublevel StreamIn, State = Active. */
	bool Activate(FString& OutMessage);

	bool StreamIn(FString& Msg);

	/** Skipped when another Active / Leaving portal uses the same sublevel. */
	bool StreamOut(FString& Msg);

	/** bSwitchLighting -> TimeOfDay EnterInterior / ExitInterior(PortalId) + OnInterior* hook + log. */
	void SetInside(bool bInside);

	UGolmokZoneSubsystem* GetZoneSubsystem() const;
	AGolmokTimeOfDay* GetTimeOfDay();

	UPROPERTY(VisibleAnywhere, Category = "Golmok|Portal")
	TObjectPtr<USceneComponent> Root;

	/** Pawn-only overlap box, standing on the portal point (relative Z = TriggerHeightCm / 2). */
	UPROPERTY(VisibleAnywhere, Category = "Golmok|Portal")
	TObjectPtr<UBoxComponent> Trigger;

	TWeakObjectPtr<AGolmokTimeOfDay> TimeOfDay;

	/** The pawn whose overlap set bPlayerOverlapping; matched on EndOverlap regardless of who is possessed by then. */
	TWeakObjectPtr<APawn> OverlappingPawn;

	/** Player controller whose OnPossessedPawnChanged we bound in BeginPlay (unbound in EndPlay). */
	TWeakObjectPtr<AController> BoundController;

	FTimerHandle DebounceTimer;
	FTimerHandle UnloadTimer;
	double LastCrossingSeconds = -1.0e9;
	bool bWarnedNoTargetZone = false;
};
