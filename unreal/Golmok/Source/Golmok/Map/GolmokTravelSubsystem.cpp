#include "Map/GolmokTravelSubsystem.h"

#include "Golmok.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Geo/GolmokGeoSubsystem.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformTime.h"
#include "Kismet/GameplayStatics.h"
#include "Map/GolmokTravelMath.h"
#include "Photo/GolmokPhotoModeSubsystem.h"
#include "Portals/GolmokPortal.h"
#include "Save/GolmokSaveSubsystem.h"
#include "TimerManager.h"
#include "Zones/GolmokZone.h"
#include "Zones/GolmokZoneIndex.h"
#include "Zones/GolmokZoneManifest.h"
#include "Zones/GolmokZoneSubsystem.h"

namespace GolmokTravelPrivate
{
	/** Capsule half height when the pawn is not an ACharacter (the default ACharacter capsule). */
	constexpr double DefaultHalfHeightCm = 88.0;
	/** The HUD keeps a failure visible this long (real seconds). */
	constexpr double ErrorHudSeconds = 10.0;

	const TCHAR* StateName(EGolmokTravelState State)
	{
		switch (State)
		{
		case EGolmokTravelState::Loading:
			return TEXT("loading");
		case EGolmokTravelState::Arriving:
			return TEXT("arriving");
		case EGolmokTravelState::Idle:
		default:
			return TEXT("idle");
		}
	}

	/** Timer rate > 0 (SetTimer with 0 only clears the handle). */
	float TimerRate(float Seconds) { return FMath::Max(Seconds, 0.01f); }
} // namespace GolmokTravelPrivate

// ---- lifecycle ------------------------------------------------------------------------------------------------

bool UGolmokTravelSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UGolmokTravelSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	TravelTimeoutSeconds = FMath::Max(0.1f, TravelTimeoutSeconds);
	FadeSeconds = FMath::Max(0.f, FadeSeconds);
	PollSeconds = FMath::Max(0.01f, PollSeconds);
	MaxRegionDistanceKm = FMath::Max(0.f, MaxRegionDistanceKm);
	// Save restore (spec §3) hangs off this world's begin play: GameMode / PlayerController stay untouched (hot-spot).
	if (UGolmokSaveSubsystem* Save = UGolmokSaveSubsystem::Get(&InWorld))
	{
		Save->HandleWorldBeginPlay(InWorld);
	}
}

void UGolmokTravelSubsystem::Deinitialize()
{
	UWorld* World = GetWorld();
	if (World)
	{
		World->GetTimerManager().ClearTimer(PollTimer);
		World->GetTimerManager().ClearTimer(ArrivalTimer);
		if (UGolmokSaveSubsystem* Save = UGolmokSaveSubsystem::Get(World))
		{
			Save->HandleWorldEnd(World);
		}
	}
	State = EGolmokTravelState::Idle;
	Super::Deinitialize();
}

UGolmokTravelSubsystem* UGolmokTravelSubsystem::Get(const UWorld* World)
{
	return World ? World->GetSubsystem<UGolmokTravelSubsystem>() : nullptr;
}

// ---- helpers --------------------------------------------------------------------------------------------------

UGolmokZoneSubsystem* UGolmokTravelSubsystem::GetZones() const
{
	UWorld* World = GetWorld();
	return World ? World->GetSubsystem<UGolmokZoneSubsystem>() : nullptr;
}

APlayerController* UGolmokTravelSubsystem::GetPlayerController() const
{
	UWorld* World = GetWorld();
	return World ? UGameplayStatics::GetPlayerController(World, 0) : nullptr;
}

APawn* UGolmokTravelSubsystem::GetPlayerPawn() const
{
	UWorld* World = GetWorld();
	return World ? UGameplayStatics::GetPlayerPawn(World, 0) : nullptr;
}

bool UGolmokTravelSubsystem::IsAnyPortalBusy() const
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return false;
	}
	for (TActorIterator<AGolmokPortal> It(World); It; ++It)
	{
		if (It->State != EGolmokPortalState::Idle)
		{
			return true;
		}
	}
	return false;
}

double UGolmokTravelSubsystem::RegionDistanceKm(const FString& ZoneId) const
{
	UWorld* World = GetWorld();
	const UGolmokZoneSubsystem* Zones = GetZones();
	UGolmokGeoSubsystem* Geo = World ? World->GetSubsystem<UGolmokGeoSubsystem>() : nullptr;
	const FGolmokZoneIndexEntry* Entry = Zones ? Zones->GetIndex().FindZone(ZoneId) : nullptr;
	FVector CenterUE = FVector::ZeroVector;
	if (!Entry || !Geo || !Geo->LonLatToLevelUE((Entry->West + Entry->East) * 0.5, (Entry->South + Entry->North) * 0.5, 0.0, CenterUE))
	{
		return 0.0; // placed-only zones and levels without a geo origin are always "this region"
	}
	return GolmokTravelMath::HorizontalDistanceM(GolmokTravelMath::Vec3{CenterUE.X, CenterUE.Y, 0.0}, GolmokTravelMath::Vec3{0.0, 0.0, 0.0})
		   / 1000.0;
}

FString UGolmokTravelSubsystem::ResolveDisplayName(const FString& ZoneId)
{
	UGolmokZoneSubsystem* Zones = GetZones();
	if (!Zones)
	{
		return ZoneId;
	}
	if (AGolmokZone* Zone = Zones->FindZone(ZoneId))
	{
		return Zone->EnsureManifest() ? Zone->Manifest.GetDisplayName() : ZoneId;
	}
	if (const FGolmokZoneIndexEntry* Entry = Zones->GetIndex().FindZone(ZoneId))
	{
		// No actor yet (far away): read the small manifest file once per list call.
		FGolmokZoneManifest Manifest;
		FString Error;
		if (GolmokZoneManifest::LoadManifest(GolmokZoneManifest::ManifestFilePath(Entry->Id, Entry->Version), Manifest, Error))
		{
			return Manifest.GetDisplayName();
		}
	}
	return ZoneId;
}

void UGolmokTravelSubsystem::StartFade(float FromAlpha, float ToAlpha)
{
	APlayerController* PC = GetPlayerController();
	APlayerCameraManager* Camera = PC ? PC->PlayerCameraManager.Get() : nullptr;
	if (!Camera)
	{
		return;
	}
	if (FadeSeconds <= 0.f)
	{
		Camera->StopCameraFade();
		return;
	}
	// No asset: the camera manager's own fade (hold the black until the fade in starts).
	Camera->StartCameraFade(FromAlpha, ToAlpha, FadeSeconds, FLinearColor::Black, /*bShouldFadeAudio*/ false, /*bHoldWhenFinished*/ ToAlpha > 0.5f);
}

// ---- travel ---------------------------------------------------------------------------------------------------

bool UGolmokTravelSubsystem::TravelToZone(const FString& ZoneId, FString& OutMessage)
{
	return StartTravel(ZoneId, /*bInHasDestination*/ false, FVector::ZeroVector, 0.f, OutMessage);
}

bool UGolmokTravelSubsystem::TravelToLocation(const FString& ZoneId, const FVector& InDestinationUE, float InDestinationYawUE, FString& OutMessage)
{
	return StartTravel(ZoneId, /*bInHasDestination*/ true, InDestinationUE, InDestinationYawUE, OutMessage);
}

bool UGolmokTravelSubsystem::StartTravel(
	const FString& RequestedZoneId, bool bInHasDestination, const FVector& InDestinationUE, float InDestinationYawUE, FString& OutMessage)
{
	UWorld* World = GetWorld();
	UGolmokZoneSubsystem* Zones = GetZones();
	if (!World || !Zones)
	{
		OutMessage = TEXT("travel: no zone subsystem (game / PIE world only)");
		return false;
	}
	FString ZoneId = RequestedZoneId.TrimStartAndEnd();
	bool bDestination = bInHasDestination;
	FString Note;
	bool bKnown = ZoneId.IsEmpty() ? bDestination : (Zones->FindZone(ZoneId) != nullptr || Zones->IsZoneInIndex(ZoneId));

	// Interior zones are never a direct target (spec §2): their parent exterior's spawn instead (a saved position inside
	// an interior too: the room needs its portal for the sublevel and the lighting overlay).
	if (!ZoneId.IsEmpty() && bKnown)
	{
		bool bInterior = false;
		FString Parent;
		if (AGolmokZone* Zone = Zones->FindZone(ZoneId))
		{
			if (Zone->EnsureManifest())
			{
				bInterior = Zone->IsInterior();
				Parent = Zone->GetParentZoneId();
			}
		}
		else if (const FGolmokZoneIndexEntry* Entry = Zones->GetIndex().FindZone(ZoneId))
		{
			if (Entry->Kind == EGolmokZoneKind::Interior)
			{
				bInterior = true;
				FGolmokZoneManifest Manifest;
				FString Error;
				if (GolmokZoneManifest::LoadManifest(GolmokZoneManifest::ManifestFilePath(Entry->Id, Entry->Version), Manifest, Error))
				{
					Parent = Manifest.ParentZone;
				}
			}
		}
		if (bInterior)
		{
			if (Parent.IsEmpty())
			{
				OutMessage = FString::Printf(TEXT("travel to %s refused: interior zone without a readable parent_zone"), *ZoneId);
				LastError = OutMessage;
				LastErrorSeconds = FPlatformTime::Seconds();
				return false;
			}
			Note = FString::Printf(TEXT("%s is an interior: going to its parent %s's spawn"), *ZoneId, *Parent);
			ZoneId = Parent;
			bDestination = false;
			bKnown = Zones->FindZone(ZoneId) != nullptr || Zones->IsZoneInIndex(ZoneId);
		}
	}

	const GolmokTravelMath::ERefusal Refusal = GolmokTravelMath::CheckTravel(IsTraveling(), UGolmokPhotoModeSubsystem::IsActiveIn(World),
		IsAnyPortalBusy(), bKnown, GetPlayerPawn() != nullptr, ZoneId.IsEmpty() ? 0.0 : RegionDistanceKm(ZoneId),
		static_cast<double>(MaxRegionDistanceKm));
	if (Refusal != GolmokTravelMath::ERefusal::None)
	{
		OutMessage = FString::Printf(TEXT("travel to %s refused: %s"), ZoneId.IsEmpty() ? TEXT("(location)") : *ZoneId,
			ANSI_TO_TCHAR(GolmokTravelMath::RefusalName(Refusal)));
		// A refusal because a travel runs must not overwrite that travel's status.
		if (Refusal != GolmokTravelMath::ERefusal::AlreadyTraveling)
		{
			LastError = OutMessage;
			LastErrorSeconds = FPlatformTime::Seconds();
		}
		UE_LOG(LogGolmok, Log, TEXT("GolmokTravel: %s"), *OutMessage);
		return false;
	}

	LastNote = Note;
	bHasDestination = bDestination;
	DestinationUE = InDestinationUE;
	DestinationYawUE = InDestinationYawUE;
	LastError.Reset();
	LastErrorSeconds = -1.0;

	if (ZoneId.IsEmpty())
	{
		// A saved basemap position: no zone to wait for, placed at once (no fade).
		TargetZoneId.Reset();
		APawn* Pawn = GetPlayerPawn();
		if (ACharacter* Character = Cast<ACharacter>(Pawn))
		{
			if (UCharacterMovementComponent* Movement = Character->GetCharacterMovement())
			{
				Movement->StopMovementImmediately();
			}
		}
		Pawn->SetActorLocation(DestinationUE, /*bSweep*/ false, nullptr, ETeleportType::TeleportPhysics);
		const FRotator Rotation(0.0, DestinationYawUE, 0.0);
		Pawn->SetActorRotation(Rotation);
		if (APlayerController* PC = GetPlayerController())
		{
			PC->SetControlRotation(Rotation);
		}
		LastArrivalLocationUE = Pawn->GetActorLocation();
		LastArrivalYawUE = DestinationYawUE;
		OutMessage = FString::Printf(TEXT("placed at the saved position (no zone) UE (%.0f, %.0f, %.0f) yaw %.1f"), LastArrivalLocationUE.X,
			LastArrivalLocationUE.Y, LastArrivalLocationUE.Z, DestinationYawUE);
		UE_LOG(LogGolmok, Log, TEXT("GolmokTravel: %s"), *OutMessage);
		return true;
	}

	FString LoadMessage;
	if (!Zones->RequestLoad(ZoneId, /*bPin*/ true, LoadMessage, EGolmokZoneRequestSource::Travel))
	{
		OutMessage = FString::Printf(TEXT("travel to %s failed: %s"), *ZoneId, *LoadMessage);
		LastError = OutMessage;
		LastErrorSeconds = FPlatformTime::Seconds();
		UE_LOG(LogGolmok, Warning, TEXT("GolmokTravel: %s"), *OutMessage);
		return false;
	}
	TargetZoneId = ZoneId;
	State = EGolmokTravelState::Loading;
	StartSeconds = FPlatformTime::Seconds();
	StartFade(0.f, 1.f);
	World->GetTimerManager().SetTimer(PollTimer, FTimerDelegate::CreateUObject(this, &UGolmokTravelSubsystem::OnPoll),
		GolmokTravelPrivate::TimerRate(PollSeconds), /*bLoop*/ true);
	OutMessage = FString::Printf(TEXT("traveling to %s (%s)%s%s"), *ZoneId, *LoadMessage, Note.IsEmpty() ? TEXT("") : TEXT("; "), *Note);
	UE_LOG(LogGolmok, Log, TEXT("GolmokTravel: %s%s"), *OutMessage, bDestination ? TEXT(" [saved position]") : TEXT(""));
	return true;
}

void UGolmokTravelSubsystem::OnPoll()
{
	if (State != EGolmokTravelState::Loading)
	{
		return;
	}
	UGolmokZoneSubsystem* Zones = GetZones();
	AGolmokZone* Zone = Zones ? Zones->FindZone(TargetZoneId) : nullptr;
	if (!Zone)
	{
		Fail(FString::Printf(TEXT("zone %s disappeared while loading"), *TargetZoneId));
		return;
	}
	const double Elapsed = FPlatformTime::Seconds() - StartSeconds;
	const bool bLoaded = Zone->IsLoaded() && !bSimulateLoadStall;
	const bool bFailed = Zone->State == EGolmokZoneState::Failed;
	switch (GolmokTravelMath::PollTravel(bLoaded, bFailed, Elapsed, static_cast<double>(FadeSeconds), static_cast<double>(TravelTimeoutSeconds)))
	{
	case GolmokTravelMath::EPoll::Arrive:
		Arrive(*Zone);
		break;
	case GolmokTravelMath::EPoll::TimedOut:
		Fail(FString::Printf(TEXT("timeout: %s not loaded after %.1f s (state %s)"), *TargetZoneId, Elapsed,
			Zone->IsLoading() ? TEXT("loading") : (Zone->IsLoaded() ? TEXT("loaded") : TEXT("unloaded"))));
		break;
	case GolmokTravelMath::EPoll::LoadFailed:
		Fail(FString::Printf(TEXT("zone %s failed to load: %s"), *TargetZoneId, *Zone->LastError));
		break;
	case GolmokTravelMath::EPoll::Wait:
	default:
		break;
	}
}

void UGolmokTravelSubsystem::Arrive(AGolmokZone& Zone)
{
	UWorld* World = GetWorld();
	APawn* Pawn = GetPlayerPawn();
	if (!World || !Pawn)
	{
		Fail(TEXT("no player pawn at arrival"));
		return;
	}
	World->GetTimerManager().ClearTimer(PollTimer);

	FVector Location = DestinationUE;
	float YawUE = DestinationYawUE;
	FString Source = TEXT("saved position");
	if (!bHasDestination)
	{
		FVector FeetUE = FVector::ZeroVector;
		bool bFromManifest = false;
		if (!Zone.GetSpawnUE(FeetUE, YawUE, &bFromManifest))
		{
			Fail(FString::Printf(TEXT("zone %s has no readable manifest: %s"), *Zone.ZoneId, *Zone.LastError));
			return;
		}
		double HalfHeight = GolmokTravelPrivate::DefaultHalfHeightCm;
		if (const ACharacter* Character = Cast<ACharacter>(Pawn))
		{
			if (const UCapsuleComponent* Capsule = Character->GetCapsuleComponent())
			{
				HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
			}
		}
		const GolmokTravelMath::Vec3 Standing = GolmokTravelMath::StandingLocationUE(GolmokTravelMath::Vec3{FeetUE.X, FeetUE.Y, FeetUE.Z}, HalfHeight);
		Location = FVector(Standing[0], Standing[1], Standing[2]);
		Source = bFromManifest ? TEXT("manifest spawn") : TEXT("fallback (no spawn)");
	}

	// ⑥ teleport: no sweep (the target may overlap geometry by the clearance only), velocity dropped, yaw via the controller.
	if (ACharacter* Character = Cast<ACharacter>(Pawn))
	{
		if (UCharacterMovementComponent* Movement = Character->GetCharacterMovement())
		{
			Movement->StopMovementImmediately();
		}
	}
	Pawn->SetActorLocation(Location, /*bSweep*/ false, nullptr, ETeleportType::TeleportPhysics);
	const FRotator Rotation(0.0, YawUE, 0.0);
	Pawn->SetActorRotation(Rotation);
	if (APlayerController* PC = GetPlayerController())
	{
		PC->SetControlRotation(Rotation);
	}
	LastArrivalLocationUE = Pawn->GetActorLocation();
	LastArrivalYawUE = YawUE;
	State = EGolmokTravelState::Arriving;
	UE_LOG(LogGolmok, Log, TEXT("GolmokTravel: arrived at %s (%s) UE (%.1f, %.1f, %.1f) yaw %.2f after %.2f s"), *Zone.ZoneId, *Source,
		LastArrivalLocationUE.X, LastArrivalLocationUE.Y, LastArrivalLocationUE.Z, YawUE, FPlatformTime::Seconds() - StartSeconds);
	// ⑦ the pin is released one tick later (the zone subsystem has seen the pawn inside the footprint by then).
	ArrivalTimer = World->GetTimerManager().SetTimerForNextTick(FTimerDelegate::CreateUObject(this, &UGolmokTravelSubsystem::FinishArrival));
}

void UGolmokTravelSubsystem::FinishArrival()
{
	if (State != EGolmokTravelState::Arriving)
	{
		return;
	}
	const FString Arrived = TargetZoneId;
	if (UGolmokZoneSubsystem* Zones = GetZones())
	{
		Zones->ReleasePin(Arrived); // distance rules take over; never RequestUnload
	}
	StartFade(1.f, 0.f);
	State = EGolmokTravelState::Idle;
	LastArrivedZoneId = Arrived;
	TargetZoneId.Reset();
	++ArrivalCount;
	// ⑧ listeners (the save subsystem records the visit and saves).
	OnTraveled.Broadcast(Arrived);
}

void UGolmokTravelSubsystem::Fail(const FString& Reason)
{
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(PollTimer);
		World->GetTimerManager().ClearTimer(ArrivalTimer);
	}
	if (!TargetZoneId.IsEmpty())
	{
		if (UGolmokZoneSubsystem* Zones = GetZones())
		{
			Zones->ReleasePin(TargetZoneId);
		}
	}
	if (State != EGolmokTravelState::Idle)
	{
		StartFade(1.f, 0.f);
	}
	State = EGolmokTravelState::Idle;
	LastError = FString::Printf(TEXT("travel to %s failed: %s"), *TargetZoneId, *Reason);
	LastErrorSeconds = FPlatformTime::Seconds();
	TargetZoneId.Reset();
	UE_LOG(LogGolmok, Warning, TEXT("GolmokTravel: %s"), *LastError);
}

void UGolmokTravelSubsystem::CancelTravel(const FString& Reason)
{
	if (IsTraveling())
	{
		Fail(FString::Printf(TEXT("cancelled (%s)"), *Reason));
	}
}

// ---- describe -------------------------------------------------------------------------------------------------

FString UGolmokTravelSubsystem::DescribeList()
{
	UWorld* World = GetWorld();
	UGolmokZoneSubsystem* Zones = GetZones();
	if (!World || !Zones)
	{
		return TEXT("golmok.travel list: no zone subsystem");
	}
	const UGolmokSaveSubsystem* Save = UGolmokSaveSubsystem::Get(World);
	FVector Player = FVector::ZeroVector;
	const APawn* Pawn = GetPlayerPawn();
	if (Pawn)
	{
		Player = Pawn->GetActorLocation();
	}
	UGolmokGeoSubsystem* Geo = World->GetSubsystem<UGolmokGeoSubsystem>();

	auto DistanceText = [&](const FString& Id) -> FString
	{
		if (!Pawn)
		{
			return TEXT("-");
		}
		if (AGolmokZone* Zone = Zones->FindZone(Id))
		{
			if (Zone->HasManifest())
			{
				return FString::Printf(TEXT("%.0f m"), Zone->DistanceToFootprintM(FVector2D(Player.X, Player.Y)));
			}
		}
		if (const FGolmokZoneIndexEntry* Entry = Zones->GetIndex().FindZone(Id))
		{
			FVector CenterUE = FVector::ZeroVector;
			if (Geo && Geo->LonLatToLevelUE((Entry->West + Entry->East) * 0.5, (Entry->South + Entry->North) * 0.5, 0.0, CenterUE))
			{
				return FString::Printf(TEXT("~%.0f m"), GolmokTravelMath::HorizontalDistanceM(GolmokTravelMath::Vec3{CenterUE.X, CenterUE.Y, 0.0},
															  GolmokTravelMath::Vec3{Player.X, Player.Y, 0.0}));
			}
		}
		return TEXT("-");
	};

	const TArray<FGolmokZoneIndexEntry>& Entries = Zones->GetIndex().GetEntries();
	FString Out = FString::Printf(TEXT("golmok.travel list: %d index zones%s"), Entries.Num(),
		Zones->GetIndex().IsAvailable() ? TEXT("") : TEXT(" (no zone index)"));
	TSet<FString> Listed;
	for (const FGolmokZoneIndexEntry& Entry : Entries)
	{
		Listed.Add(Entry.Id);
		const double RegionKm = RegionDistanceKm(Entry.Id);
		const bool bOtherRegion = MaxRegionDistanceKm > 0.f && RegionKm > static_cast<double>(MaxRegionDistanceKm);
		Out += FString::Printf(TEXT("\n  %-28s v%-3d %-8s %-10s %-9s \"%s\"%s"), *Entry.Id, Entry.Version,
			Entry.Kind == EGolmokZoneKind::Interior ? TEXT("interior") : TEXT("exterior"), Save && Save->IsVisited(Entry.Id) ? TEXT("visited") : TEXT("new"),
			*DistanceText(Entry.Id), *ResolveDisplayName(Entry.Id),
			bOtherRegion ? TEXT("  [other region: not supported]") : (Entry.Kind == EGolmokZoneKind::Interior ? TEXT("  [-> parent spawn]") : TEXT("")));
	}
	// Level-placed zones the index does not list (dev levels).
	for (TActorIterator<AGolmokZone> It(World); It; ++It)
	{
		AGolmokZone* Zone = *It;
		if (!Zone || Zone->ZoneId.IsEmpty() || Listed.Contains(Zone->ZoneId))
		{
			continue;
		}
		Listed.Add(Zone->ZoneId);
		const bool bInterior = Zone->EnsureManifest() && Zone->IsInterior();
		Out += FString::Printf(TEXT("\n  %-28s v%-3d %-8s %-10s %-9s \"%s\"  [placed]"), *Zone->ZoneId, Zone->Version,
			bInterior ? TEXT("interior") : TEXT("exterior"), Save && Save->IsVisited(Zone->ZoneId) ? TEXT("visited") : TEXT("new"),
			*DistanceText(Zone->ZoneId), *ResolveDisplayName(Zone->ZoneId));
	}
	return Out;
}

FString UGolmokTravelSubsystem::DescribeStatus() const
{
	FString Out = FString::Printf(TEXT("golmok.travel status: %s"), GolmokTravelPrivate::StateName(State));
	if (IsTraveling())
	{
		Out += FString::Printf(TEXT(" -> %s (%.1f s%s)"), *TargetZoneId, FPlatformTime::Seconds() - StartSeconds,
			bHasDestination ? TEXT(", saved position") : TEXT(""));
	}
	Out += FString::Printf(TEXT("; arrivals %d, last %s"), ArrivalCount, LastArrivedZoneId.IsEmpty() ? TEXT("-") : *LastArrivedZoneId);
	if (!LastNote.IsEmpty())
	{
		Out += FString::Printf(TEXT("; note: %s"), *LastNote);
	}
	if (!LastError.IsEmpty())
	{
		Out += FString::Printf(TEXT("; last error: %s"), *LastError);
	}
	Out += FString::Printf(TEXT("; timeout %.1f s, fade %.2f s, poll %.2f s, region %.0f km"), TravelTimeoutSeconds, FadeSeconds, PollSeconds,
		MaxRegionDistanceKm);
	return Out;
}

FString UGolmokTravelSubsystem::DescribeHudLine() const
{
	if (State == EGolmokTravelState::Loading)
	{
		return FString::Printf(TEXT("travel: -> %s loading %.1f / %.0f s"), *TargetZoneId, FPlatformTime::Seconds() - StartSeconds, TravelTimeoutSeconds);
	}
	if (State == EGolmokTravelState::Arriving)
	{
		return FString::Printf(TEXT("travel: arriving %s"), *TargetZoneId);
	}
	if (!LastError.IsEmpty() && LastErrorSeconds >= 0.0 && FPlatformTime::Seconds() - LastErrorSeconds < GolmokTravelPrivate::ErrorHudSeconds)
	{
		return FString::Printf(TEXT("travel: %s"), *LastError);
	}
	return LastArrivedZoneId.IsEmpty() ? FString(TEXT("travel: idle")) : FString::Printf(TEXT("travel: idle (last %s)"), *LastArrivedZoneId);
}

// ---- console --------------------------------------------------------------------------------------------------

namespace GolmokTravelConsole
{
	void CmdTravel(const TArray<FString>& Args, UWorld* World)
	{
		UGolmokTravelSubsystem* Travel = UGolmokTravelSubsystem::Get(World);
		if (!Travel)
		{
			UE_LOG(LogGolmok, Warning, TEXT("golmok.travel: no travel subsystem (game / PIE world only)"));
			return;
		}
		if (Args.Num() < 1)
		{
			UE_LOG(LogGolmok, Warning, TEXT("usage: golmok.travel <zone_id> | list | status"));
			return;
		}
		if (Args[0].Equals(TEXT("list"), ESearchCase::IgnoreCase))
		{
			UE_LOG(LogGolmok, Log, TEXT("%s"), *Travel->DescribeList());
			return;
		}
		if (Args[0].Equals(TEXT("status"), ESearchCase::IgnoreCase))
		{
			UE_LOG(LogGolmok, Log, TEXT("%s"), *Travel->DescribeStatus());
			return;
		}
		FString Message;
		const bool bOk = Travel->TravelToZone(Args[0], Message);
		UE_LOG(LogGolmok, Log, TEXT("golmok.travel: %s%s"), bOk ? TEXT("") : TEXT("ERROR "), *Message);
	}

	FAutoConsoleCommandWithWorldAndArgs GCmdTravel(TEXT("golmok.travel"),
		TEXT("golmok.travel <zone_id> | list | status: preload a zone, fade, teleport to its spawn (WP-15a)."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdTravel));
} // namespace GolmokTravelConsole
