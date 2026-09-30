#include "Audio/GolmokAmbienceSubsystem.h"

#include "Audio/GolmokFootstepComponent.h"
#include "Components/AudioComponent.h"
#include "Debug/GolmokDebugSubsystem.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Golmok.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Misc/PackageName.h"
#include "Photo/GolmokPhotoModeSubsystem.h"
#include "Player/GolmokCharacter.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundConcurrency.h"
#include "Sound/SoundWave.h"

bool UGolmokAmbienceSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UGolmokAmbienceSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Collection.InitializeDependency<UGolmokDebugSubsystem>();
	Super::Initialize(Collection);
	bReady = GolmokAudio::LoadConfig(Config, LoadError);
	Channels.SetNum(2);
	PhotoGain.Set(1, 0);
	LastRealTime = FPlatformTime::Seconds();
	Debug = GetWorld()->GetSubsystem<UGolmokDebugSubsystem>();
	if (Debug.IsValid())
	{
		const TWeakObjectPtr<UGolmokAmbienceSubsystem> WeakThis(this);
		HudHandle = Debug->AddExtraHudLineProvider([WeakThis]() { return WeakThis.IsValid() ? WeakThis->Describe() : FString(); });
	}
	// Reserved for future nonlocal sources; local footsteps use 2D playback.
	Attenuation = NewObject<USoundAttenuation>(this);
	Attenuation->Attenuation.bAttenuate = true;
	Attenuation->Attenuation.AttenuationShapeExtents = FVector(100.f, 0.f, 0.f);
	Attenuation->Attenuation.FalloffDistance = 600.f;
	Concurrency = NewObject<USoundConcurrency>(this);
	Concurrency->Concurrency.MaxCount = 8;
	Concurrency->Concurrency.ResolutionRule = EMaxConcurrentResolutionRule::StopOldest;
}

void UGolmokAmbienceSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	if (!bReady) return;
	for (const auto& Pair : Config.Assets)
	{
		// Generated SoundWaves may not have been imported in this checkout yet.
		const FString Package = FPackageName::ObjectPathToPackageName(Pair.Value.Path);
		USoundWave* Sound = FPackageName::DoesPackageExist(Package) ? LoadObject<USoundWave>(nullptr, *Pair.Value.Path) : nullptr;
		if (Sound)
		{
			Sound->VirtualizationMode = EVirtualizationMode::PlayWhenSilent;
			Sounds.Add(Pair.Key, Sound);
		}
		else LoadError = TEXT("missing SoundWave; run golmok.audio_import then restart PIE");
	}
	RefreshBindings();
	ResolveState(true);
}

void UGolmokAmbienceSubsystem::Deinitialize()
{
	if (Lighting.IsValid())
	{
		Lighting->OnPresetChanged.Remove(PresetHandle);
		Lighting->OnInteriorChanged.Remove(InteriorHandle);
	}
	if (Controller.IsValid()) Controller->OnPossessedPawnChanged.RemoveDynamic(this, &UGolmokAmbienceSubsystem::PawnChanged);
	if (Debug.IsValid()) Debug->RemoveExtraHudLineProvider(HudHandle);
	HudHandle.Reset();
	for (UAudioComponent* Channel : Channels) if (IsValid(Channel)) { Channel->Stop(); Channel->DestroyComponent(); }
	for (UAudioComponent* Shot : OneShots) if (IsValid(Shot)) Shot->Stop();
	OneShots.Empty();
	Channels.Empty(); Sounds.Empty(); bReady = false;
	Super::Deinitialize();
}

TStatId UGolmokAmbienceSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UGolmokAmbienceSubsystem, STATGROUP_Tickables);
}

void UGolmokAmbienceSubsystem::RefreshBindings()
{
	if (!bReady) return;
	AGolmokTimeOfDay* Tod = AGolmokTimeOfDay::Find(GetWorld());
	// A destroyed weak target reads null; the retained handle detects that transition.
	if (Tod != Lighting.Get() || (!Tod && PresetHandle.IsValid()))
	{
		if (Lighting.IsValid())
		{
			Lighting->OnPresetChanged.Remove(PresetHandle);
			Lighting->OnInteriorChanged.Remove(InteriorHandle);
		}
		PresetHandle.Reset(); InteriorHandle.Reset();
		Preset.Empty(); bInterior = false;
		Lighting = Tod;
		if (Tod)
		{
			Preset = Tod->CurrentPreset.ToString(); bInterior = Tod->InteriorSources.Num() > 0;
			PresetHandle = Tod->OnPresetChanged.AddUObject(this, &UGolmokAmbienceSubsystem::PresetChanged);
			InteriorHandle = Tod->OnInteriorChanged.AddUObject(this, &UGolmokAmbienceSubsystem::InteriorChanged);
		}
		ResolveState();
	}
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	if (Controller.Get() != PC)
	{
		if (Controller.IsValid()) Controller->OnPossessedPawnChanged.RemoveDynamic(this, &UGolmokAmbienceSubsystem::PawnChanged);
		Controller = PC;
		if (PC)
		{
			PC->OnPossessedPawnChanged.AddDynamic(this, &UGolmokAmbienceSubsystem::PawnChanged);
			PawnChanged(nullptr, PC->GetPawn());
		}
	}
}

void UGolmokAmbienceSubsystem::PawnChanged(APawn* OldPawn, APawn* NewPawn)
{
	if (AGolmokCharacter* Character = Cast<AGolmokCharacter>(NewPawn))
	{
		if (!Character->FindComponentByClass<UGolmokFootstepComponent>())
		{
			UGolmokFootstepComponent* Steps = NewObject<UGolmokFootstepComponent>(Character);
			Character->AddInstanceComponent(Steps); Steps->RegisterComponent();
		}
	}
}

void UGolmokAmbienceSubsystem::PresetChanged(FName Name, bool bInstant) { Preset = Name.ToString(); ResolveState(bInstant); }
void UGolmokAmbienceSubsystem::InteriorChanged(bool bValue) { bInterior = bValue; ResolveState(); }

void UGolmokAmbienceSubsystem::ResolveState(bool bInstant)
{
	const FString* Outdoor = Config.Presets.Find(Preset);
	const TCHAR* States[] = {TEXT("outdoor_day"), TEXT("outdoor_night"), TEXT("interior")};
	SetState(!ForcedState.IsEmpty() ? ForcedState : States[GolmokAudioMath::State(bInterior, Outdoor && *Outdoor == TEXT("outdoor_night"))], bInstant);
}

bool UGolmokAmbienceSubsystem::ForceState(const FString& InState)
{
	if (!InState.IsEmpty() && InState != TEXT("auto") && !Config.Ambience.Contains(InState)) return false;
	ForcedState = InState == TEXT("auto") ? FString() : InState;
	ResolveState(); return true;
}

void UGolmokAmbienceSubsystem::SetState(const FString& InState, bool bInstant)
{
	if (!bReady || !Config.Ambience.Contains(InState) || (State == InState && !bInstant)) return;
	State = InState;
	const FString AssetId = Config.Ambience[State];
	PendingSlot = INDEX_NONE; PendingAsset.Empty();
	for (int32 Slot = 0; Slot < 2; ++Slot)
	{
		if (SlotIds[Slot] == AssetId)
		{
			Gains[Slot].Set(1, bInstant ? 0 : Config.FadeSeconds(State));
			Gains[1 - Slot].Set(0, bInstant ? 0 : Config.FadeSeconds(State));
			return;
		}
	}
	const int32 Slot = Gains[0].Value <= Gains[1].Value ? 0 : 1;
	if (!bInstant && Gains[Slot].Value > 0.0001 && Config.FadeSeconds(State) > 0)
	{
		// Two channels cannot keep three clips alive. Ramp the quieter slot to zero before replacement.
		PendingSlot = Slot; PendingAsset = AssetId;
		Gains[Slot].Set(0, FMath::Min(.05, Config.FadeSeconds(State)));
		Gains[1 - Slot].Set(Gains[1 - Slot].Value, 0);
	}
	else StartSlot(Slot, AssetId, bInstant);
}

void UGolmokAmbienceSubsystem::StartSlot(int32 Slot, const FString& AssetId, bool bInstant)
{
	if (IsValid(Channels[Slot])) { Channels[Slot]->SetVolumeMultiplier(0); Channels[Slot]->Stop(); Channels[Slot]->DestroyComponent(); Channels[Slot] = nullptr; }
	SlotIds[Slot] = AssetId;
	Gains[Slot].Value = 0;
	Gains[Slot].Set(1, bInstant ? 0 : Config.FadeSeconds(State));
	Gains[1 - Slot].Set(0, bInstant ? 0 : Config.FadeSeconds(State));
	if (USoundWave* Sound = Sounds.FindRef(AssetId))
	{
		Channels[Slot] = UGameplayStatics::SpawnSound2D(this, Sound, 0.f, 1.f, 0.f, nullptr, false, false);
		// SpawnSound2D sets UI sound before playback; Photo policy is applied below.
	}
}

bool UGolmokAmbienceSubsystem::IsMuted() const
{
	return bMuted || (Config.bMuteInPhoto && UGolmokPhotoModeSubsystem::IsActiveIn(GetWorld()));
}

void UGolmokAmbienceSubsystem::Tick(float DeltaTime)
{
	if (!bReady || !HasCalledBeginPlay()) return;
	const double Now = FPlatformTime::Seconds();
	const double Dt = FMath::Clamp(Now - LastRealTime, 0.0, 0.1); LastRealTime = Now;
	if (Now >= NextBindingTime) { RefreshBindings(); NextBindingTime = Now + .25; }
	const bool bPhotoNow = Config.bMuteInPhoto && UGolmokPhotoModeSubsystem::IsActiveIn(GetWorld());
	if (bPhotoNow != bPhotoMuted)
	{
		bPhotoMuted = bPhotoNow;
		PhotoGain.Set(bPhotoMuted ? 0 : 1, Config.PhotoMuteFadeSeconds);
		if (bPhotoMuted) for (UAudioComponent* Shot : OneShots) if (IsValid(Shot))
		{
			if (Config.PhotoMuteFadeSeconds > 0) Shot->FadeOut(static_cast<float>(Config.PhotoMuteFadeSeconds), 0.f, EAudioFaderCurve::SCurve);
			else Shot->Stop();
		}
	}
	PhotoGain.Advance(Dt);
	for (auto& Gain : Gains) Gain.Advance(Dt);
	if (PendingSlot != INDEX_NONE && Gains[PendingSlot].Done())
	{
		const int32 Slot = PendingSlot; const FString AssetId = PendingAsset;
		PendingSlot = INDEX_NONE; PendingAsset.Empty(); StartSlot(Slot, AssetId, false);
	}
	for (int32 Slot = 0; Slot < 2; ++Slot)
	{
		if (IsValid(Channels[Slot])) Channels[Slot]->SetVolumeMultiplier(static_cast<float>((bMuted ? 0 : Config.MasterVolume * PhotoGain.Value) * Gains[Slot].Value));
	}
	if (bMuted) for (UAudioComponent* Shot : OneShots) if (IsValid(Shot)) Shot->Stop();
	OneShots.RemoveAll([](const TObjectPtr<UAudioComponent>& Shot) { return !IsValid(Shot) || !Shot->IsPlaying(); });
}

void UGolmokAmbienceSubsystem::PlayFootstep(const FString& Set, bool bLanding)
{
#if WITH_DEV_AUTOMATION_TESTS
	if (bLanding) ++LandingRequests; else ++FootstepRequests;
#endif
	LastFootstepSet = Config.Sets.Contains(Set) ? Set : TEXT("default");
	if (!bReady || IsMuted()) return;
	const TArray<FString>* Samples = Config.Sets.Find(LastFootstepSet);
	if (!Samples) Samples = Config.Sets.Find(TEXT("default"));
	if (!Samples || Samples->IsEmpty()) return;
	const FString Key = bLanding ? Config.Landing : (*Samples)[FMath::RandHelper(Samples->Num())];
	if (USoundWave* Sound = Sounds.FindRef(Key))
	{
		// The local player's own steps must not vary with camera boom length.
		UAudioComponent* Shot = UGameplayStatics::SpawnSound2D(this, Sound,
			static_cast<float>(Config.MasterVolume * PhotoGain.Value * FMath::FRandRange(Config.VolumeMin, Config.VolumeMax)),
			static_cast<float>(FMath::FRandRange(Config.PitchMin, Config.PitchMax)), 0.f, Concurrency, false, true);
		if (Shot) OneShots.Add(Shot);
	}
}

void UGolmokAmbienceSubsystem::SetSurfaceDiagnostic(int32 Surface, const FString& Message)
{
	SurfaceError = Message;
	if (!Message.IsEmpty() && !WarnedSurfaces.Contains(Surface))
	{
		WarnedSurfaces.Add(Surface);
		UE_LOG(LogGolmok, Warning, TEXT("audio: %s"), *Message);
	}
}

FString UGolmokAmbienceSubsystem::Describe() const
{
	return FString::Printf(TEXT("audio: %s [%s / %s] vol %.2f steps=%s photo_gain=%.2f%s%s%s"), *State, *SlotIds[0], *SlotIds[1],
		Config.MasterVolume, *LastFootstepSet, PhotoGain.Value, IsMuted() ? TEXT(" muted") : TEXT(""), LoadError.IsEmpty() ? TEXT("") : *FString(TEXT(" error: ") + LoadError), SurfaceError.IsEmpty() ? TEXT("") : *FString(TEXT(" error: ") + SurfaceError));
}

namespace GolmokAudioConsole
{
	void Status(const TArray<FString>& Args, UWorld* World)
	{
		if (auto* Audio = World ? World->GetSubsystem<UGolmokAmbienceSubsystem>() : nullptr)
			UE_LOG(LogGolmok, Log, TEXT("%s"), Args.Num() == 1 && Args[0] == TEXT("credits") ? *Audio->GetCredits() : *Audio->Describe());
	}
	void Mute(const TArray<FString>& Args, UWorld* World)
	{
		if (auto* Audio = World ? World->GetSubsystem<UGolmokAmbienceSubsystem>() : nullptr)
		{
			if (Args.Num() == 1 && (Args[0] == TEXT("0") || Args[0] == TEXT("1"))) Audio->SetMuted(Args[0] == TEXT("1"));
			UE_LOG(LogGolmok, Log, TEXT("%s"), *Audio->Describe());
		}
	}
	void State(const TArray<FString>& Args, UWorld* World)
	{
		if (auto* Audio = World ? World->GetSubsystem<UGolmokAmbienceSubsystem>() : nullptr)
		{
			if (Args.Num() != 1 || !Audio->ForceState(Args[0])) { UE_LOG(LogGolmok, Log, TEXT("golmok.audio.state <outdoor_day|outdoor_night|interior|auto>")); }
			else { UE_LOG(LogGolmok, Log, TEXT("%s"), *Audio->Describe()); }
		}
	}
	FAutoConsoleCommandWithWorldAndArgs GCmdAudioStatus(TEXT("golmok.audio"), TEXT("Audio status; credits prints source attribution"), FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&Status));
	FAutoConsoleCommandWithWorldAndArgs GCmdAudioMute(TEXT("golmok.audio.mute"), TEXT("Mute 0|1"), FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&Mute));
	FAutoConsoleCommandWithWorldAndArgs GCmdAudioState(TEXT("golmok.audio.state"), TEXT("Force audio state or auto"), FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&State));
}
