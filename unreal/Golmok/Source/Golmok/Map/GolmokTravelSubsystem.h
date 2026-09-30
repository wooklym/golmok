#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "TimerManager.h"
#include "GolmokTravelSubsystem.generated.h"

class AGolmokZone;
class APawn;
class APlayerController;
class UGolmokZoneSubsystem;

/** WP-15a: fired after a travel arrived (the pin is released and the fade-in started). ZoneId = the zone arrived at. */
DECLARE_MULTICAST_DELEGATE_OneParam(FGolmokOnTraveled, const FString& /*ZoneId*/);

/** Travel state (spec §2): Idle -> Loading (fade out + pinned preload) -> Arriving (teleported, pin released next tick) -> Idle. */
UENUM()
enum class EGolmokTravelState : uint8
{
	Idle,
	Loading,
	Arriving
};

/**
 * Zone travel (WP-15a, D-014; docs/plan/WP-15-zone-travel-save.md §2). World subsystem, game and PIE worlds only.
 *
 * TravelToZone(ZoneId): ① refused while photo mode is active, while any portal is not Idle (transition / interior), while
 * a travel runs, for a zone neither in the level nor in the Zone Index, for a zone farther than MaxRegionDistanceKm
 * from the level origin ("another region", not supported in 15a; a radius heuristic around the level origin) and for a
 * Zone Index zone (not placed in the level) when the level has no AGolmokGeoOrigin (nowhere to put it, no region test).
 * An interior zone is redirected to its parent exterior's spawn. ② RequestLoad(ZoneId, pinned, Travel) (spawns the
 * actor from the index when needed) ③ camera fade out (APlayerCameraManager::StartCameraFade, no asset) ④ poll
 * IsLoaded() every PollSeconds, at most TravelTimeoutSeconds (failure: pin released, fade in, LastError)
 * ⑤ AGolmokZone::GetSpawnUE (manifest spawn or the spec §1 fallback) ⑥ SetActorLocation without sweep (+ capsule half
 * height) and the controller yaw ⑦ next tick the pin is released (distance rules take over, never RequestUnload)
 * ⑧ fade in, OnTraveled(ZoneId).
 *
 * The save subsystem restores through TravelToLocation() (same preload / fade, a saved destination instead of the spawn).
 * Console: golmok.travel <zone_id> | golmok.travel list | golmok.travel status. HUD line "travel: ..." (debug HUD).
 * Config: [/Script/Golmok.GolmokTravelSubsystem] (defaults in code; no DefaultGame.ini keys needed).
 */
UCLASS(Config = Game)
class GOLMOK_API UGolmokTravelSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;

	/** Give up waiting for the target zone after this long (s): pin released, fade in, error. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Travel", meta = (ClampMin = "0.1"))
	float TravelTimeoutSeconds = 20.f;

	/** Camera fade out / in duration (s). 0 = no fade. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Travel", meta = (ClampMin = "0.0"))
	float FadeSeconds = 0.35f;

	/** IsLoaded() poll interval while traveling (s). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Travel", meta = (ClampMin = "0.01"))
	float PollSeconds = 0.05f;

	/** A zone whose index bbox center is farther than this from the level origin is "another region" (km). 0 = no limit. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Travel", meta = (ClampMin = "0.0"))
	float MaxRegionDistanceKm = 30.f;

	/** Test hook (Golmok.Travel.Teleport): the poll never sees the zone loaded, so the timeout path runs. */
	bool bSimulateLoadStall = false;

	/** Start a travel to ZoneId's spawn. False + OutMessage when refused (nothing changed). */
	bool TravelToZone(const FString& ZoneId, FString& OutMessage);

	/**
	 * Save restore (spec §3 ①): preload ZoneId like TravelToZone, then put the pawn at InDestinationUE (capsule center, cm)
	 * facing InDestinationYawUE instead of the spawn. Empty ZoneId = no zone to wait for (basemap position): immediate.
	 */
	bool TravelToLocation(const FString& ZoneId, const FVector& InDestinationUE, float InDestinationYawUE, FString& OutMessage);

	/** Abort a running travel (pin released, fade in). */
	void CancelTravel(const FString& Reason);

	bool IsTraveling() const { return State != EGolmokTravelState::Idle; }
	EGolmokTravelState GetState() const { return State; }
	const FString& GetTargetZoneId() const { return TargetZoneId; }
	const FString& GetLastError() const { return LastError; }
	const FString& GetLastArrivedZoneId() const { return LastArrivedZoneId; }
	/** Pawn location / yaw set by the last arrival (before any movement tick): tests compare against GetSpawnUE. */
	const FVector& GetLastArrivalLocationUE() const { return LastArrivalLocationUE; }
	float GetLastArrivalYawUE() const { return LastArrivalYawUE; }
	int32 GetArrivalCount() const { return ArrivalCount; }

	/** golmok.travel list: index zones (id, display name, visited, distance m) + level-only zones. */
	FString DescribeList();
	/** golmok.travel status. */
	FString DescribeStatus() const;
	/** Debug HUD line "travel: ...". */
	FString DescribeHudLine() const;

	/** display_name of ZoneId (manifest of the registered actor, else the index manifest file), else the id. */
	FString ResolveDisplayName(const FString& ZoneId);

	FGolmokOnTraveled OnTraveled;

	static UGolmokTravelSubsystem* Get(const UWorld* World);

private:
	bool StartTravel(const FString& RequestedZoneId, bool bInHasDestination, const FVector& InDestinationUE, float InDestinationYawUE, FString& OutMessage);
	void OnPoll();
	void Arrive(AGolmokZone& Zone);
	void FinishArrival();
	void Fail(const FString& Reason);
	void StartFade(float FromAlpha, float ToAlpha);
	/** Movement input is ignored while the screen is black (Loading / Arriving); SetIgnoreMoveInput is a counter, so paired once. */
	void SetMoveInputBlocked(bool bBlocked);
	bool IsAnyPortalBusy() const;
	APawn* GetPlayerPawn() const;
	APlayerController* GetPlayerController() const;
	UGolmokZoneSubsystem* GetZones() const;
	/** Horizontal distance (km) of the index bbox center from the level origin; 0 without an index entry / geo origin. */
	double RegionDistanceKm(const FString& ZoneId) const;

	EGolmokTravelState State = EGolmokTravelState::Idle;
	FString TargetZoneId;
	FString LastError;
	FString LastArrivedZoneId;
	FString LastNote;          // redirect notes ("interior -> parent") for status / HUD
	bool bHasDestination = false;
	FVector DestinationUE = FVector::ZeroVector;
	float DestinationYawUE = 0.f;
	double StartSeconds = 0.0; // real seconds (fade / timeout do not stop while the world is slowed)
	double LastErrorSeconds = -1.0;
	FVector LastArrivalLocationUE = FVector::ZeroVector;
	float LastArrivalYawUE = 0.f;
	int32 ArrivalCount = 0;
	bool bMoveInputBlocked = false;
	bool bTargetWasPinned = false; // a console / portal pin that existed before the travel is kept
	FTimerHandle PollTimer;
	FTimerHandle ArrivalTimer;
};
