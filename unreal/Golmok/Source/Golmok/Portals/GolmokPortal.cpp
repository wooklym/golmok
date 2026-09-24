#include "Portals/GolmokPortal.h"

#include "Golmok.h"

#include "Components/BoxComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Controller.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Portals/GolmokLevelStreaming.h"
#include "TimerManager.h"
#include "Zones/GolmokZone.h"
#include "Zones/GolmokZoneSubsystem.h"

namespace
{
	const TCHAR* StateName(EGolmokPortalState State)
	{
		switch (State)
		{
		case EGolmokPortalState::Pending:
			return TEXT("pending");
		case EGolmokPortalState::Active:
			return TEXT("active");
		case EGolmokPortalState::Leaving:
			return TEXT("leaving");
		case EGolmokPortalState::Idle:
		default:
			return TEXT("idle");
		}
	}

	const TCHAR* ModeName(EGolmokInteriorStreamingMode Mode)
	{
		return Mode == EGolmokInteriorStreamingMode::NamedStreamingLevel ? TEXT("NamedStreamingLevel") : TEXT("LevelInstance");
	}

	/** FTimerManager::SetTimer with a rate <= 0 only clears the handle, so a zero delay still fires on the next timer tick. */
	float TimerRate(float Seconds)
	{
		return FMath::Max(Seconds, 0.001f);
	}
} // namespace

AGolmokPortal::AGolmokPortal()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;

	// A scene root keeps the actor location on the portal point (manifest position) while the box is raised by
	// TriggerHeightCm / 2 so it stands on the floor.
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("PortalRoot"));
	SetRootComponent(Root);
	Root->SetMobility(EComponentMobility::Movable);

	Trigger = CreateDefaultSubobject<UBoxComponent>(TEXT("Trigger"));
	Trigger->SetupAttachment(Root);
	Trigger->SetMobility(EComponentMobility::Movable);
	Trigger->InitBoxExtent(FVector(RadiusCm, RadiusCm, TriggerHeightCm * 0.5));
	Trigger->SetRelativeLocation(FVector(0.0, 0.0, TriggerHeightCm * 0.5));
	Trigger->SetCollisionProfileName(TEXT("OverlapOnlyPawn"));
	Trigger->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Trigger->SetGenerateOverlapEvents(true);
	Trigger->SetHiddenInGame(true);
	Trigger->ShapeColor = FColor::Green;
	Trigger->bDrawOnlyIfSelected = false;
	Trigger->SetLineThickness(2.0f);
	Trigger->SetCanEverAffectNavigation(false);
}

// ---- configuration --------------------------------------------------------------------------------------------

void AGolmokPortal::Configure(const AGolmokZone& OwnerZone, const FGolmokZonePortal& P)
{
	PortalId = P.Id;
	OwnerZoneId = OwnerZone.ZoneId;
	TargetZoneId = P.ToZone;
	Kind = P.Kind;
	RadiusCm = AGolmokZone::PortalRadiusCm(P);
	bIsEntry = !OwnerZone.IsInterior();
	SublevelPackagePath.Reset();
	if (bIsEntry)
	{
		// Version of the interior: the placed zone actor's Version when it is in this level, else 1 (editor worlds
		// have no zone subsystem).
		int32 TargetVersion = 1;
		UWorld* World = OwnerZone.GetWorld();
		UGolmokZoneSubsystem* Subsystem = World ? World->GetSubsystem<UGolmokZoneSubsystem>() : nullptr;
		if (Subsystem)
		{
			if (const AGolmokZone* Target = Subsystem->FindZone(P.ToZone))
			{
				TargetVersion = FMath::Max(1, Target->Version);
			}
		}
		SublevelPackagePath = GolmokZoneManifest::SublevelPackagePath(P.ToZone, TargetVersion);
	}
	if (Trigger)
	{
		const double HalfHeight = static_cast<double>(TriggerHeightCm) * 0.5;
		Trigger->SetBoxExtent(FVector(RadiusCm, RadiusCm, HalfHeight));
		Trigger->SetRelativeLocation(FVector(0.0, 0.0, HalfHeight));
	}
}

double AGolmokPortal::SignedDistanceAlongForward(const FVector& WorldPos) const
{
	return FVector::DotProduct(WorldPos - GetActorLocation(), GetActorForwardVector());
}

// ---- lifecycle ------------------------------------------------------------------------------------------------

void AGolmokPortal::BeginPlay()
{
	Super::BeginPlay();
	UWorld* World = GetWorld();
	TimeOfDay = AGolmokTimeOfDay::Find(World);
	State = EGolmokPortalState::Idle;
	if (!bIsEntry)
	{
		// Marker: no events, no state changes; shown by the collision debug view only.
		if (Trigger)
		{
			Trigger->SetGenerateOverlapEvents(false);
		}
		return;
	}
	if (!Trigger)
	{
		return;
	}
	Trigger->OnComponentBeginOverlap.AddDynamic(this, &AGolmokPortal::OnTriggerBeginOverlap);
	Trigger->OnComponentEndOverlap.AddDynamic(this, &AGolmokPortal::OnTriggerEndOverlap);
	// Path playback possesses another pawn (UGolmokDebugSubsystem::StartPlayback / EndPlayback) without the trigger
	// seeing an overlap change: follow the possessed pawn instead of re-querying "is this the player" per event.
	if (APlayerController* PC = World ? UGameplayStatics::GetPlayerController(World, 0) : nullptr)
	{
		PC->OnPossessedPawnChanged.AddDynamic(this, &AGolmokPortal::OnPlayerPawnChanged);
		BoundController = PC;
	}
	// A pawn already standing in the box when the zone loads gets no BeginOverlap event: enter the same path by hand.
	APawn* Pawn = World ? UGameplayStatics::GetPlayerPawn(World, 0) : nullptr;
	if (Pawn && Trigger->IsOverlappingActor(Pawn))
	{
		BeginPlayerOverlap(Pawn);
	}
}

void AGolmokPortal::EndPlay(const EEndPlayReason::Type Reason)
{
	UWorld* World = GetWorld();
	if (World)
	{
		World->GetTimerManager().ClearTimer(DebounceTimer);
		World->GetTimerManager().ClearTimer(UnloadTimer);
	}
	if (AController* PC = BoundController.Get())
	{
		PC->OnPossessedPawnChanged.RemoveDynamic(this, &AGolmokPortal::OnPlayerPawnChanged);
	}
	BoundController.Reset();
	if (bIsEntry)
	{
		const bool bWorldAlive =
			World && !World->bIsTearingDown && Reason != EEndPlayReason::EndPlayInEditor && Reason != EEndPlayReason::Quit;
		if (State == EGolmokPortalState::Active || State == EGolmokPortalState::Leaving)
		{
			FString Msg;
			StreamOut(Msg);
			// The interior zone was loaded pinned, which the Evaluate() orphan-interior rule skips, so the unload is
			// ours. It runs next tick: EndPlay is reached from AGolmokZone::Unload() -> DestroyPortals(), possibly
			// inside Evaluate(), and nothing must re-enter the subsystem from there (design section 3-1).
			UGolmokZoneSubsystem* Subsystem = GetZoneSubsystem();
			if (bWorldAlive && Subsystem && Subsystem->FindZone(TargetZoneId))
			{
				auto UnloadInterior = [Subsystem, ZoneId = TargetZoneId, Portal = PortalId]()
				{
					if (IsInteriorZoneInUse(Subsystem->GetWorld(), ZoneId, nullptr))
					{
						UE_LOG(LogGolmok, Log, TEXT("Portal %s: gone; %s kept (another portal is active)"), *Portal, *ZoneId);
						return;
					}
					// The interior is not distance-managed, so the bBlocked flag RequestUnload sets is harmless.
					FString ZoneMsg;
					Subsystem->RequestUnload(ZoneId, ZoneMsg);
					UE_LOG(LogGolmok, Log, TEXT("Portal %s: gone -> %s"), *Portal, *ZoneMsg);
				};
				World->GetTimerManager().SetTimerForNextTick(FTimerDelegate::CreateWeakLambda(Subsystem, MoveTemp(UnloadInterior)));
				Msg += TEXT("; zone unload scheduled");
			}
			UE_LOG(LogGolmok, Log, TEXT("Portal %s: end play while %s -> %s"), *PortalId, StateName(State), *Msg);
		}
		// Always drop our lighting source (a plane crossing can happen while still Pending, and ExitInterior is a
		// no-op for an unknown source) so no orphan overlay survives the portal.
		AGolmokTimeOfDay* Tod = TimeOfDay.IsValid() ? TimeOfDay.Get() : AGolmokTimeOfDay::Find(World);
		if (Tod)
		{
			Tod->ExitInterior(FName(*PortalId));
		}
	}
	State = EGolmokPortalState::Idle;
	bPlayerOverlapping = false;
	bPlayerInside = false;
	OverlappingPawn.Reset();
	Super::EndPlay(Reason);
}

void AGolmokPortal::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bIsEntry || !bPlayerOverlapping)
	{
		SetActorTickEnabled(false);
		return;
	}
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	APawn* Pawn = OverlappingPawn.Get();
	APawn* Player = UGameplayStatics::GetPlayerPawn(World, 0);
	if (!Pawn || Pawn != Player || !Trigger || !Trigger->IsOverlappingActor(Pawn))
	{
		// Possession changed or an EndOverlap was missed: resync (may end the overlap and disable Tick).
		RefreshOverlap(Player);
		return;
	}
	const double Now = World->GetTimeSeconds();
	if (Now - LastCrossingSeconds < static_cast<double>(MinCrossingIntervalSeconds))
	{
		return;
	}
	// One dot product per frame, only while overlapping.
	const double D = SignedDistanceAlongForward(Pawn->GetActorLocation());
	if (!bPlayerInside && D > static_cast<double>(CrossingHysteresisCm))
	{
		SetInside(true);
	}
	else if (bPlayerInside && D < -static_cast<double>(CrossingHysteresisCm))
	{
		SetInside(false);
	}
}

// ---- overlap handlers (deferred: nothing loads, streams or re-lights from inside these) ---------------------------

void AGolmokPortal::OnTriggerBeginOverlap(UPrimitiveComponent* OverlappedComp, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	if (!IsValid(this) || IsActorBeingDestroyed() || !bIsEntry || !IsPlayerPawn(OtherActor))
	{
		return;
	}
	BeginPlayerOverlap(Cast<APawn>(OtherActor));
}

void AGolmokPortal::OnTriggerEndOverlap(UPrimitiveComponent* OverlappedComp, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex)
{
	// Matched against the pawn that began the overlap, not "the player pawn now": after a possession swap the old
	// pawn's EndOverlap (or the path pawn's on destruction) must still close the overlap.
	if (!IsValid(this) || IsActorBeingDestroyed() || !bIsEntry || !bPlayerOverlapping || !OtherActor
		|| OtherActor != OverlappingPawn.Get())
	{
		return;
	}
	EndPlayerOverlap();
}

void AGolmokPortal::OnPlayerPawnChanged(APawn* OldPawn, APawn* NewPawn)
{
	if (!IsValid(this) || IsActorBeingDestroyed() || !bIsEntry)
	{
		return;
	}
	RefreshOverlap(NewPawn);
}

void AGolmokPortal::BeginPlayerOverlap(APawn* Pawn)
{
	UWorld* World = GetWorld();
	if (!World || !Pawn)
	{
		return;
	}
	OverlappingPawn = Pawn;
	bPlayerOverlapping = true;
	SetActorTickEnabled(true);
	// Re-entry during the unload delay keeps the interior loaded (no thrash).
	World->GetTimerManager().ClearTimer(UnloadTimer);
	if (State == EGolmokPortalState::Leaving)
	{
		State = EGolmokPortalState::Active;
		LastEvent = TEXT("re-entered trigger; unload cancelled");
	}
	if (State == EGolmokPortalState::Idle)
	{
		State = EGolmokPortalState::Pending;
		LastEvent = TEXT("entered trigger");
		World->GetTimerManager().SetTimer(DebounceTimer, this, &AGolmokPortal::OnDebounceElapsed, TimerRate(DebounceSeconds), false);
	}
}

void AGolmokPortal::EndPlayerOverlap()
{
	UWorld* World = GetWorld();
	bPlayerOverlapping = false;
	OverlappingPawn.Reset();
	SetActorTickEnabled(false);
	if (State == EGolmokPortalState::Pending)
	{
		if (bPlayerInside)
		{
			// Crossed the plane inside the debounce window and walked on into the room: the pending debounce still
			// loads the interior (OnDebounceElapsed activates when inside), so the overlay never runs without it.
			LastEvent = TEXT("left trigger inward before debounce");
			return;
		}
		if (World)
		{
			World->GetTimerManager().ClearTimer(DebounceTimer);
		}
		State = EGolmokPortalState::Idle;
		LastEvent = TEXT("left trigger before debounce");
		return;
	}
	if (bPlayerInside)
	{
		// Left the box on the interior side: keep everything loaded.
		LastEvent = TEXT("left trigger inward");
		return;
	}
	if (State == EGolmokPortalState::Active && World)
	{
		State = EGolmokPortalState::Leaving;
		LastEvent = TEXT("left trigger outward");
		World->GetTimerManager().SetTimer(UnloadTimer, this, &AGolmokPortal::OnUnloadDelayElapsed, TimerRate(UnloadDelaySeconds), false);
	}
}

void AGolmokPortal::RefreshOverlap(APawn* Pawn)
{
	if (!bIsEntry || !Trigger)
	{
		return;
	}
	const bool bOverlaps = Pawn != nullptr && Trigger->IsOverlappingActor(Pawn);
	if (bPlayerOverlapping)
	{
		if (bOverlaps)
		{
			// The new pawn stands in the box too (playback started at the door): swap it in, keep the state.
			OverlappingPawn = Pawn;
			return;
		}
		// The new pawn is elsewhere (the hidden character outside while the path pawn was in the room): a pawn on
		// the exterior side leaves the door outward, so the overlay goes off and the unload delay starts.
		if (bPlayerInside && Pawn && SignedDistanceAlongForward(Pawn->GetActorLocation()) < 0.0)
		{
			SetInside(false);
		}
		EndPlayerOverlap();
		return;
	}
	if (bOverlaps)
	{
		BeginPlayerOverlap(Pawn);
	}
}

bool AGolmokPortal::IsPlayerPawn(const AActor* Other) const
{
	if (!Other)
	{
		return false;
	}
	const APawn* Player = UGameplayStatics::GetPlayerPawn(GetWorld(), 0);
	return Player != nullptr && Player == Other;
}

bool AGolmokPortal::IsInteriorZoneInUse(UWorld* World, const FString& ZoneId, const AGolmokPortal* Except)
{
	if (!World)
	{
		return false;
	}
	for (TActorIterator<AGolmokPortal> It(World); It; ++It)
	{
		const AGolmokPortal* Other = *It;
		if (Other == Except || !IsValid(Other) || Other->IsActorBeingDestroyed() || !Other->bIsEntry)
		{
			continue;
		}
		if (Other->TargetZoneId == ZoneId && (Other->State == EGolmokPortalState::Active || Other->State == EGolmokPortalState::Leaving))
		{
			return true;
		}
	}
	return false;
}

// ---- timers ----------------------------------------------------------------------------------------------------

void AGolmokPortal::OnDebounceElapsed()
{
	if (State != EGolmokPortalState::Pending)
	{
		return;
	}
	// A pawn that already crossed the plane and left the box inward still needs its interior loaded.
	if (!bPlayerOverlapping && !bPlayerInside)
	{
		State = EGolmokPortalState::Idle;
		return;
	}
	FString Msg;
	Activate(Msg);
}

void AGolmokPortal::OnUnloadDelayElapsed()
{
	if (State != EGolmokPortalState::Leaving)
	{
		return;
	}
	FString StreamMsg;
	StreamOut(StreamMsg);
	FString ZoneMsg;
	if (UGolmokZoneSubsystem* Subsystem = GetZoneSubsystem())
	{
		if (Subsystem->FindZone(TargetZoneId))
		{
			// The interior is not distance-managed, so the bBlocked flag RequestUnload sets is harmless.
			Subsystem->RequestUnload(TargetZoneId, ZoneMsg);
		}
	}
	State = EGolmokPortalState::Idle;
	LastEvent = TEXT("unloaded");
	UE_LOG(LogGolmok, Log, TEXT("Portal %s: player left -> unload %s; %s"), *PortalId, *TargetZoneId, *StreamMsg);
}

bool AGolmokPortal::Activate(FString& OutMessage)
{
	FString ZoneMsg;
	if (UGolmokZoneSubsystem* Subsystem = GetZoneSubsystem())
	{
		if (Subsystem->FindZone(TargetZoneId))
		{
			Subsystem->RequestLoad(TargetZoneId, /*bPin*/ true, ZoneMsg);
		}
		else
		{
			ZoneMsg = FString::Printf(TEXT("no AGolmokZone '%s' in this level; sublevel only"), *TargetZoneId);
			if (!bWarnedNoTargetZone)
			{
				bWarnedNoTargetZone = true;
				UE_LOG(LogGolmok, Warning, TEXT("Portal %s: %s"), *PortalId, *ZoneMsg);
			}
		}
	}
	else
	{
		ZoneMsg = TEXT("no zone subsystem in this world");
	}

	FString SublevelMsg;
	if (bStreamSublevel && !SublevelPackagePath.IsEmpty())
	{
		FString StreamMsg;
		if (StreamIn(StreamMsg))
		{
			SublevelMsg = FString::Printf(TEXT("sublevel %s (%s)"), *SublevelPackagePath, ModeName(InteriorStreamingMode));
		}
		else
		{
			SublevelMsg = FString::Printf(TEXT("sublevel %s: %s"), *SublevelPackagePath, *StreamMsg);
		}
	}
	else
	{
		SublevelMsg = TEXT("sublevel skipped");
	}

	State = EGolmokPortalState::Active;
	LastEvent = TEXT("interior loaded");
	OutMessage = FString::Printf(TEXT("Portal %s (%s -> %s): player within %.0f cm -> load [%s]; %s"), *PortalId, *OwnerZoneId, *TargetZoneId,
		RadiusCm, *ZoneMsg, *SublevelMsg);
	UE_LOG(LogGolmok, Log, TEXT("%s"), *OutMessage);
	return true;
}

// ---- streaming --------------------------------------------------------------------------------------------------

bool AGolmokPortal::StreamIn(FString& Msg)
{
	return GolmokLevelStreaming::StreamIn(GetWorld(), SublevelPackagePath, InteriorStreamingMode, Msg);
}

bool AGolmokPortal::StreamOut(FString& Msg)
{
	UWorld* World = GetWorld();
	if (!World || SublevelPackagePath.IsEmpty())
	{
		Msg = TEXT("no sublevel");
		return false;
	}
	// Another door into the same interior still in use: keep the sublevel (one traversal, unload time only).
	for (TActorIterator<AGolmokPortal> It(World); It; ++It)
	{
		const AGolmokPortal* Other = *It;
		if (Other == this || !IsValid(Other) || Other->IsActorBeingDestroyed() || !Other->bIsEntry)
		{
			continue;
		}
		if (Other->SublevelPackagePath == SublevelPackagePath
			&& (Other->State == EGolmokPortalState::Active || Other->State == EGolmokPortalState::Leaving))
		{
			Msg = FString::Printf(TEXT("sublevel kept (portal %s is %s)"), *Other->PortalId, StateName(Other->State));
			return false;
		}
	}
	return GolmokLevelStreaming::StreamOut(World, SublevelPackagePath, Msg);
}

bool AGolmokPortal::IsSublevelLoaded() const
{
	return !SublevelPackagePath.IsEmpty() && GolmokLevelStreaming::IsLoaded(GetWorld(), SublevelPackagePath);
}

bool AGolmokPortal::IsSublevelVisible() const
{
	return !SublevelPackagePath.IsEmpty() && GolmokLevelStreaming::IsVisible(GetWorld(), SublevelPackagePath);
}

// ---- lighting ---------------------------------------------------------------------------------------------------

void AGolmokPortal::SetInside(bool bInside)
{
	if (bPlayerInside == bInside)
	{
		return;
	}
	bPlayerInside = bInside;
	UWorld* World = GetWorld();
	LastCrossingSeconds = World ? World->GetTimeSeconds() : 0.0;
	if (bSwitchLighting)
	{
		if (AGolmokTimeOfDay* Tod = GetTimeOfDay())
		{
			if (bInside)
			{
				Tod->EnterInterior(FName(*PortalId));
			}
			else
			{
				Tod->ExitInterior(FName(*PortalId));
			}
		}
	}
	LastEvent = bInside ? TEXT("crossed inward") : TEXT("crossed outward");
	UE_LOG(LogGolmok, Log, TEXT("Portal %s: %s"), *PortalId, *LastEvent);
	if (bInside)
	{
		OnInteriorEntered();
	}
	else
	{
		OnInteriorExited();
	}
}

void AGolmokPortal::OnInteriorEntered()
{
	UE_LOG(LogGolmok, Verbose, TEXT("Portal %s: OnInteriorEntered"), *PortalId);
}

void AGolmokPortal::OnInteriorExited()
{
	UE_LOG(LogGolmok, Verbose, TEXT("Portal %s: OnInteriorExited"), *PortalId);
}

UGolmokZoneSubsystem* AGolmokPortal::GetZoneSubsystem() const
{
	UWorld* World = GetWorld();
	return World ? World->GetSubsystem<UGolmokZoneSubsystem>() : nullptr;
}

AGolmokTimeOfDay* AGolmokPortal::GetTimeOfDay()
{
	if (!TimeOfDay.IsValid())
	{
		TimeOfDay = AGolmokTimeOfDay::FindOrSpawn(GetWorld());
	}
	return TimeOfDay.Get();
}

// ---- console / test entry points -------------------------------------------------------------------------------

bool AGolmokPortal::EnterInterior(FString& OutMessage)
{
	if (!bIsEntry)
	{
		OutMessage = FString::Printf(TEXT("portal %s is a marker (bIsEntry=false); use the entry portal of zone %s"), *PortalId, *TargetZoneId);
		return false;
	}
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(UnloadTimer);
		World->GetTimerManager().ClearTimer(DebounceTimer);
	}
	if (State != EGolmokPortalState::Active)
	{
		Activate(OutMessage);
	}
	else
	{
		OutMessage = FString::Printf(TEXT("portal %s is already active"), *PortalId);
	}
	SetInside(true);
	return true;
}

bool AGolmokPortal::LeaveInterior(FString& OutMessage)
{
	if (!bIsEntry)
	{
		OutMessage = FString::Printf(TEXT("portal %s is a marker (bIsEntry=false); use the entry portal of zone %s"), *PortalId, *TargetZoneId);
		return false;
	}
	SetInside(false);
	if (State == EGolmokPortalState::Active)
	{
		UWorld* World = GetWorld();
		if (!World)
		{
			OutMessage = TEXT("no world");
			return false;
		}
		State = EGolmokPortalState::Leaving;
		LastEvent = TEXT("leave requested");
		World->GetTimerManager().SetTimer(UnloadTimer, this, &AGolmokPortal::OnUnloadDelayElapsed, TimerRate(UnloadDelaySeconds), false);
		OutMessage = FString::Printf(TEXT("portal %s leaving; %s unloads in %.1f s"), *PortalId, *TargetZoneId, UnloadDelaySeconds);
	}
	else
	{
		OutMessage = FString::Printf(TEXT("portal %s is %s; nothing to unload"), *PortalId, StateName(State));
	}
	return true;
}

void AGolmokPortal::SetDebugVisible(bool bVisible)
{
	if (Trigger)
	{
		Trigger->SetHiddenInGame(!bVisible);
	}
}

FString AGolmokPortal::Describe() const
{
	if (!bIsEntry)
	{
		return FString::Printf(TEXT("%s (%s -> %s) (marker)"), *PortalId, *OwnerZoneId, *TargetZoneId);
	}
	return FString::Printf(TEXT("%s (%s -> %s) %s %s; sublevel %s (%s)"), *PortalId, *OwnerZoneId, *TargetZoneId, StateName(State),
		bPlayerInside ? TEXT("inside") : TEXT("outside"), *GolmokLevelStreaming::Describe(GetWorld(), SublevelPackagePath),
		ModeName(InteriorStreamingMode));
}

AGolmokPortal* AGolmokPortal::FindPortal(UWorld* World, const FString& PortalId)
{
	if (!World)
	{
		return nullptr;
	}
	AGolmokPortal* Marker = nullptr;
	for (TActorIterator<AGolmokPortal> It(World); It; ++It)
	{
		AGolmokPortal* Portal = *It;
		if (!IsValid(Portal) || Portal->IsActorBeingDestroyed() || Portal->PortalId != PortalId)
		{
			continue;
		}
		if (Portal->bIsEntry)
		{
			return Portal;
		}
		if (!Marker)
		{
			Marker = Portal;
		}
	}
	return Marker;
}

FString AGolmokPortal::DescribeAll(UWorld* World)
{
	TArray<FString> Lines;
	if (World)
	{
		for (TActorIterator<AGolmokPortal> It(World); It; ++It)
		{
			const AGolmokPortal* Portal = *It;
			if (IsValid(Portal) && !Portal->IsActorBeingDestroyed())
			{
				Lines.Add(Portal->Describe());
			}
		}
	}
	return Lines.Num() > 0 ? FString::Join(Lines, TEXT("\n")) : FString(TEXT("no portals (load a zone with portals first: golmok.zone.list)"));
}

// ---- console: golmok.portal list | enter <id> | leave <id> ----------------------------------------------------------

namespace
{
	void CmdPortal(const TArray<FString>& Args, UWorld* World)
	{
		if (!World)
		{
			UE_LOG(LogGolmok, Warning, TEXT("golmok.portal: no world."));
			return;
		}
		const FString Sub = Args.Num() > 0 ? Args[0].ToLower() : FString(TEXT("list"));
		if (Sub == TEXT("list"))
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.portal list\n%s"), *AGolmokPortal::DescribeAll(World));
			return;
		}
		if (Sub == TEXT("enter") || Sub == TEXT("leave"))
		{
			if (Args.Num() < 2)
			{
				UE_LOG(LogGolmok, Warning, TEXT("usage: golmok.portal %s <portal_id>"), *Sub);
				return;
			}
			AGolmokPortal* Portal = AGolmokPortal::FindPortal(World, Args[1]);
			if (!Portal)
			{
				UE_LOG(LogGolmok, Log, TEXT("golmok.portal %s: ERROR no portal '%s' (is its zone loaded? golmok.zone.list)"), *Sub, *Args[1]);
				return;
			}
			FString Message;
			const bool bOk = Sub == TEXT("enter") ? Portal->EnterInterior(Message) : Portal->LeaveInterior(Message);
			UE_LOG(LogGolmok, Log, TEXT("golmok.portal %s: %s%s"), *Sub, bOk ? TEXT("") : TEXT("ERROR "), *Message);
			return;
		}
		UE_LOG(LogGolmok, Warning, TEXT("usage: golmok.portal list | golmok.portal enter <portal_id> | golmok.portal leave <portal_id>"));
	}

	FAutoConsoleCommandWithWorldAndArgs GCmdPortal(TEXT("golmok.portal"),
		TEXT("golmok.portal list | enter <portal_id> | leave <portal_id>: list portals, or force the interior load / unload of an entry portal."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdPortal));
} // namespace
