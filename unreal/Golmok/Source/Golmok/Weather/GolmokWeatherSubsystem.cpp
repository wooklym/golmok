#include "Weather/GolmokWeatherSubsystem.h"

#include "Golmok.h"

#include "Camera/PlayerCameraManager.h"
#include "Debug/GolmokDebugSubsystem.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Lighting/GolmokClockMath.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Map/GolmokTravelSubsystem.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Misc/PackageName.h"
#include "Photo/GolmokPhotoModeSubsystem.h"
#include "UObject/SoftObjectPath.h"
#include "Weather/GolmokWeatherRainFx.h"

// WP-16a weather runtime (docs/plan/WP-16-weather.md "16a 설계 (확정)" sections 2-4, 7-11, 13). The pure rules live in
// GolmokWeatherMath.h; this file owns the state machine, the writes (time of day, MPC, rain fx), the console and the HUD.

namespace GolmokWeather
{
	// The UENUM and the pure enum share their values (UHT headers do not carry static_asserts).
	static_assert(static_cast<uint8>(EGolmokWeather::Clear) == static_cast<uint8>(GolmokWeatherMath::State::Clear), "EGolmokWeather order");
	static_assert(static_cast<uint8>(EGolmokWeather::Overcast) == static_cast<uint8>(GolmokWeatherMath::State::Overcast), "EGolmokWeather order");
	static_assert(static_cast<uint8>(EGolmokWeather::Rain) == static_cast<uint8>(GolmokWeatherMath::State::Rain), "EGolmokWeather order");
	static_assert(GolmokWeatherMath::StateCount == 3, "EGolmokWeather has three values");

	// Named sub-namespace: GolmokWeatherConfig.cpp keeps its parser helpers in GolmokWeather::ConfigJson (unity build).
	namespace Runtime
	{
		const TCHAR* PhotoRefusal = TEXT("weather: photo mode is active - change the weather before entering photo mode");
		/** Two targets with intensities this close are the same target (a float console value vs a double schedule value). */
		constexpr double SameIntensityTolerance = 1e-5;
		/** World seconds between AGolmokTimeOfDay::Find calls while none is cached (the player controller may spawn one later). */
		constexpr double TimeOfDaySearchSeconds = 0.5;
		/**
		 * The missing-asset notes are written once per process (design 7-6), not once per PIE world, and at Display level
		 * while automation runs: before V-16 commits the two assets every Game / PIE world would otherwise add two
		 * Warnings to the existing automation and runbook warning counts (default clear = no change, section 19).
		 */
		bool bMpcMissingNoted = false;
		bool bFxMissingNoted = false;

		GolmokWeatherMath::State ToMath(EGolmokWeather Weather)
		{
			return static_cast<GolmokWeatherMath::State>(static_cast<uint8>(Weather));
		}

		EGolmokWeather FromMath(GolmokWeatherMath::State State)
		{
			return static_cast<EGolmokWeather>(static_cast<uint8>(State));
		}

		bool SameModifier(const GolmokWeatherMath::Modifier& A, const GolmokWeatherMath::Modifier& B)
		{
			return A.LuxScale == B.LuxScale && A.SkyScale == B.SkyScale && A.FogScale == B.FogScale && A.FogHeightFalloffScale == B.FogHeightFalloffScale &&
				A.KelvinTarget == B.KelvinTarget && A.KelvinWeight == B.KelvinWeight && A.ExposureOffset == B.ExposureOffset;
		}

		/**
		 * MPC / Niagara write rule (design 7-2, 8): never written (Last < 0), moved more than ValueEpsilon, or reached an
		 * end point (0 / 1) exactly - so a settled clear writes 0, not the last 0.0008 of the ramp.
		 */
		bool ShouldWrite(double Last, double Value)
		{
			if (Last < 0.0 || FMath::Abs(Value - Last) > GolmokWeatherMath::ValueEpsilon)
			{
				return true;
			}
			return Value != Last && (Value == 0.0 || Value == 1.0);
		}

		FString Hhmm(double Minutes)
		{
			TCHAR Text[6];
			GolmokClockMath::FormatHHMM(Minutes, Text);
			return FString(Text);
		}

		/** "rain 0.60" | "overcast" | "clear". */
		FString TargetText(EGolmokWeather Weather, double Intensity)
		{
			return Weather == EGolmokWeather::Rain ? FString::Printf(TEXT("rain %.2f"), Intensity) : FString(UGolmokWeatherSubsystem::WeatherName(Weather));
		}

		/** "15:00 rain 0.60" | "13:00 overcast". */
		FString SlotText(const FScheduleSlot& Slot)
		{
			return Hhmm(Slot.Minutes) + TEXT(" ") + TargetText(FromMath(Slot.State), Slot.Intensity);
		}

		/** Strict decimal number (FCString::IsNumeric: optional sign, digits, one dot) that is finite. */
		bool ParseNumber(const FString& Text, double& Out)
		{
			if (Text.IsEmpty() || !FCString::IsNumeric(*Text))
			{
				return false;
			}
			Out = FCString::Atod(*Text);
			return FMath::IsFinite(Out);
		}
	} // namespace Runtime
} // namespace GolmokWeather

// ---- static helpers ---------------------------------------------------------------------------------------------

UGolmokWeatherSubsystem* UGolmokWeatherSubsystem::Get(const UWorld* World)
{
	// DoesSupportWorldType keeps the subsystem out of editor / preview worlds, so GetSubsystem is nullptr there.
	return World ? World->GetSubsystem<UGolmokWeatherSubsystem>() : nullptr;
}

const TCHAR* UGolmokWeatherSubsystem::WeatherName(EGolmokWeather Weather)
{
	switch (Weather)
	{
	case EGolmokWeather::Overcast:
		return TEXT("overcast");
	case EGolmokWeather::Rain:
		return TEXT("rain");
	case EGolmokWeather::Clear:
	default:
		return TEXT("clear");
	}
}

bool UGolmokWeatherSubsystem::ParseWeather(const FString& Text, EGolmokWeather& Out)
{
	GolmokWeatherMath::State State = GolmokWeatherMath::State::Clear;
	if (!GolmokWeatherMath::ParseState(*Text, State))
	{
		return false;
	}
	Out = GolmokWeather::Runtime::FromMath(State);
	return true;
}

const TCHAR* UGolmokWeatherSubsystem::ModeName(EGolmokWeatherMode InMode)
{
	return InMode == EGolmokWeatherMode::Schedule ? TEXT("schedule") : TEXT("fixed");
}

bool UGolmokWeatherSubsystem::ParseMode(const FString& Text, EGolmokWeatherMode& Out)
{
	if (Text.Equals(TEXT("fixed"), ESearchCase::CaseSensitive))
	{
		Out = EGolmokWeatherMode::Fixed;
		return true;
	}
	if (Text.Equals(TEXT("schedule"), ESearchCase::CaseSensitive))
	{
		Out = EGolmokWeatherMode::Schedule;
		return true;
	}
	return false;
}

bool UGolmokWeatherSubsystem::IsFrozen() const
{
	return UGolmokPhotoModeSubsystem::IsActiveIn(GetWorld());
}

// ---- lifecycle --------------------------------------------------------------------------------------------------

bool UGolmokWeatherSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UGolmokWeatherSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Collection.InitializeDependency<UGolmokDebugSubsystem>();
	Super::Initialize(Collection);
	MpcRainName = FName(GolmokWeatherMath::MpcRainIntensity);
	MpcWetnessName = FName(GolmokWeatherMath::MpcWetness);
	MpcPuddleName = FName(GolmokWeatherMath::MpcPuddleAmount);

	FString Error;
	bConfigLoaded = GolmokWeather::LoadConfigFile(GolmokWeather::DefaultConfigPath(), Config, Error);
	if (!bConfigLoaded)
	{
		// Weather off: clear identity, no tick, commands reply with this error.
		ConfigError = Error.IsEmpty() ? FString(TEXT("weather.json: root: unreadable")) : Error;
		if (!bConfigErrorLogged)
		{
			bConfigErrorLogged = true;
			UE_LOG(LogGolmok, Error, TEXT("weather: off - %s"), *ConfigError);
		}
	}

	Debug = GetWorld()->GetSubsystem<UGolmokDebugSubsystem>();
	if (Debug.IsValid())
	{
		const TWeakObjectPtr<UGolmokWeatherSubsystem> WeakThis(this);
		HudHandle = Debug->AddExtraHudLineProvider([WeakThis]() { return WeakThis.IsValid() ? WeakThis->BuildHudLine() : FString(); });
	}
}

void UGolmokWeatherSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	if (!bConfigLoaded)
	{
		return;
	}
	bBegunPlay = true;

	// MPC_GolmokWeather by soft path; the package check keeps an absent asset (clones before V-16, CI) quiet.
	const FSoftObjectPath MpcPath(Config.Mpc);
	const FString MpcPackage = MpcPath.GetLongPackageName();
	if (MpcPath.IsValid() && !MpcPackage.IsEmpty() && FPackageName::DoesPackageExist(MpcPackage))
	{
		Mpc = Cast<UMaterialParameterCollection>(MpcPath.TryLoad());
	}
	if (!Mpc && !bMpcMissingWarned)
	{
		bMpcMissingWarned = true;
		if (!GolmokWeather::Runtime::bMpcMissingNoted)
		{
			GolmokWeather::Runtime::bMpcMissingNoted = true;
			if (GIsAutomationTesting)
			{
				UE_LOG(LogGolmok, Display, TEXT("weather: MPC missing (%s) - wetness / puddles stay in the subsystem only"), *Config.Mpc);
			}
			else
			{
				UE_LOG(LogGolmok, Warning, TEXT("weather: MPC missing (%s) - wetness / puddles stay in the subsystem only"), *Config.Mpc);
			}
		}
	}

	if (UGolmokTravelSubsystem* TravelSubsystem = UGolmokTravelSubsystem::Get(&InWorld))
	{
		Travel = TravelSubsystem;
		TraveledHandle = TravelSubsystem->OnTraveled.AddUObject(this, &UGolmokWeatherSubsystem::Traveled);
	}

	GolmokWeatherRainFx::ELoad Load = GolmokWeatherRainFx::ELoad::Missing;
	RainFxActor = GolmokWeatherRainFx::Spawn(&InWorld, Config, Load);
	RainFxLoad = static_cast<uint8>(Load);
	if (Load == GolmokWeatherRainFx::ELoad::Disabled)
	{
		UE_LOG(LogGolmok, Log, TEXT("weather: rain fx disabled in weather.json - rain is lighting/MPC/audio only"));
	}
	else if (Load == GolmokWeatherRainFx::ELoad::Missing && !bFxMissingWarned)
	{
		bFxMissingWarned = true;
		if (!GolmokWeather::Runtime::bFxMissingNoted)
		{
			GolmokWeather::Runtime::bFxMissingNoted = true;
			if (GIsAutomationTesting)
			{
				UE_LOG(LogGolmok, Display, TEXT("weather: rain fx missing (%s) - rain is lighting/MPC/audio only"), *Config.RainFxSystem);
			}
			else
			{
				UE_LOG(LogGolmok, Warning, TEXT("weather: rain fx missing (%s) - rain is lighting/MPC/audio only"), *Config.RainFxSystem);
			}
		}
	}

	// The level's time of day exists before actors begin play (its BeginPlay applies a modifier stored now); one the
	// player controller spawns later is picked up by the tick.
	ResolveTimeOfDay(/*bForce*/ true);

	// Initial value: instant, no event (nobody has subscribed yet - design section 9).
	StartTarget(GolmokWeather::Runtime::FromMath(Config.InitialState), Config.InitialIntensity, /*bInstant*/ true, /*bBroadcast*/ false);
	Mode = Config.bInitialSchedule ? EGolmokWeatherMode::Schedule : EGolmokWeatherMode::Fixed;
	if (Mode == EGolmokWeatherMode::Schedule)
	{
		// The clock usually is not up yet (the time of day applies its preset in its own BeginPlay): the first step
		// that has one evaluates instantly instead.
		bInitialSchedulePending = !EvaluateSchedule(/*bInstant*/ true, /*bBroadcast*/ false);
	}
	PushModifier(/*bSettled*/ true);
	WriteMpc(/*bForce*/ true);
	UpdateRainFx();
	UE_LOG(LogGolmok, Log, TEXT("weather: %s %s, transition %.1f s, %d schedule slots, mpc %s, fx %s"), *GolmokWeather::Runtime::TargetText(Target, TargetIntensity),
		ModeName(Mode), Config.TransitionSeconds, Config.Schedule.Num(), *DescribeMpc(), *DescribeFx());
}

void UGolmokWeatherSubsystem::Deinitialize()
{
	UnbindTimeOfDay();
	if (Travel.IsValid())
	{
		Travel->OnTraveled.Remove(TraveledHandle);
	}
	TraveledHandle.Reset();
	Travel.Reset();
	if (Debug.IsValid())
	{
		Debug->RemoveExtraHudLineProvider(HudHandle);
	}
	HudHandle.Reset();
	Debug.Reset();
	const UWorld* World = GetWorld();
	if (World && !World->bIsTearingDown)
	{
		GolmokWeatherRainFx::Destroy(RainFxActor);
	}
	RainFxActor = nullptr;
	Mpc = nullptr;
	bBegunPlay = false;
	Super::Deinitialize();
}

bool UGolmokWeatherSubsystem::IsTickable() const
{
	return bBegunPlay && bConfigLoaded;
}

void UGolmokWeatherSubsystem::Tick(float DeltaTime)
{
	// [미확인 §17 #11] IsTickableWhenPaused false already stops a GamePause photo mode; IsFrozen also covers TimeDilation.
	if (!IsTickable() || IsFrozen())
	{
		return;
	}
	StepWeather(static_cast<double>(DeltaTime));
}

TStatId UGolmokWeatherSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UGolmokWeatherSubsystem, STATGROUP_Tickables);
}

// ---- state machine ----------------------------------------------------------------------------------------------

void UGolmokWeatherSubsystem::StepWeather(double DeltaSeconds)
{
	if (!bConfigLoaded || IsFrozen())
	{
		return;
	}
	const double Dt = (FMath::IsFinite(DeltaSeconds) && DeltaSeconds > 0.0) ? DeltaSeconds : 0.0;
	TimeOfDaySearchCooldown -= Dt;
	ResolveTimeOfDay();

	if (Mode == EGolmokWeatherMode::Schedule)
	{
		// initial.mode schedule waits for the clock, then lands on its slot instantly without an event.
		const bool bInitial = bInitialSchedulePending;
		if (EvaluateSchedule(/*bInstant*/ bInitial, /*bBroadcast*/ !bInitial))
		{
			bInitialSchedulePending = false;
		}
	}

	if (bTransitioning)
	{
		TransitionElapsed += Dt;
		const double Alpha = Config.TransitionSeconds > 0.0 ? TransitionElapsed / Config.TransitionSeconds : 1.0;
		ModifierNow = GolmokWeatherMath::ModifierAt(ModifierStart, ModifierTarget, Alpha);
		RainNow = GolmokWeatherMath::PrecipAt(RainStart, RainTarget, Alpha);
		if (Alpha >= 1.0)
		{
			bTransitioning = false;
		}
	}
	SurfaceNow = GolmokWeatherMath::StepSurface(SurfaceNow, RainNow, Dt, Config.Surface);

	PushModifier(/*bSettled*/ !bTransitioning);
	WriteMpc(/*bForce*/ false);
	UpdateRainFx();
}

void UGolmokWeatherSubsystem::StartTarget(EGolmokWeather Weather, double Intensity, bool bInstant, bool bBroadcast)
{
	const GolmokWeatherMath::State State = GolmokWeather::Runtime::ToMath(Weather);
	const double NewIntensity = GolmokWeatherMath::TargetRain(State, Intensity);
	const bool bImmediate = bInstant || Config.TransitionSeconds <= 0.0;
	if (Target == Weather && FMath::Abs(TargetIntensity - NewIntensity) <= GolmokWeather::Runtime::SameIntensityTolerance)
	{
		// Same target: no event. "instant" still lands a running transition on it at once.
		if (bImmediate && bTransitioning)
		{
			FinishTransition();
		}
		return;
	}

	FromWeather = Target;
	FromIntensity = TargetIntensity;
	Target = Weather;
	TargetIntensity = NewIntensity;
	// Retarget mid-transition starts from the values seen now (no jump, design section 3).
	ModifierStart = ModifierNow;
	RainStart = RainNow;
	ModifierTarget = GolmokWeatherMath::ForState(State, NewIntensity, Config.Overcast, Config.Rain);
	RainTarget = NewIntensity;
	TransitionElapsed = 0.0;
	bTransitioning = !bImmediate;

	// R51-5 "target first": GetTarget*() are new inside the callback, GetRainIntensity() has not moved yet.
	if (bBroadcast)
	{
		// One line per event (runbook V-16 §4 / §6: one per schedule slot).
		UE_LOG(LogGolmok, Log, TEXT("weather: OnWeatherChanged %s (%s)"), *GolmokWeather::Runtime::TargetText(Target, TargetIntensity),
			bImmediate ? TEXT("instant") : TEXT("transition"));
		OnWeatherChanged.Broadcast(Target, static_cast<float>(TargetIntensity), bImmediate);
	}
	if (bImmediate)
	{
		FinishTransition(); // lands it and pushes the settled modifier exactly once
	}
}

void UGolmokWeatherSubsystem::FinishTransition()
{
	ModifierNow = ModifierTarget;
	RainNow = RainTarget;
	TransitionElapsed = Config.TransitionSeconds;
	bTransitioning = false;
	ResolveTimeOfDay();
	PushModifier(/*bSettled*/ true);
	WriteMpc(/*bForce*/ false);
	UpdateRainFx();
}

bool UGolmokWeatherSubsystem::EvaluateSchedule(bool bInstant, bool bBroadcast)
{
	const AGolmokTimeOfDay* Tod = TimeOfDay.Get();
	const int32 Index = GetScheduleIndexNow();
	if (!Tod || Index < 0)
	{
		bScheduleNoClock = true; // level lighting / no time of day: keep the current target
		return false;
	}
	bScheduleNoClock = false;
	const GolmokWeather::FScheduleSlot& Slot = Config.Schedule[Index];
	StartTarget(GolmokWeather::Runtime::FromMath(Slot.State), Slot.Intensity, bInstant, bBroadcast);
	return true;
}

int32 UGolmokWeatherSubsystem::GetScheduleIndexNow() const
{
	const AGolmokTimeOfDay* Tod = TimeOfDay.Get();
	if (!bConfigLoaded || !Tod || !Tod->HasTimeOfDay() || Config.ScheduleTimes.Num() == 0)
	{
		return -1;
	}
	return GolmokWeatherMath::ScheduleIndexAt(static_cast<double>(Tod->GetTimeOfDayMinutes()), Config.ScheduleTimes.GetData(), Config.ScheduleTimes.Num());
}

float UGolmokWeatherSubsystem::GetTransitionAlpha() const
{
	if (!bTransitioning || Config.TransitionSeconds <= 0.0)
	{
		return 1.f;
	}
	return static_cast<float>(GolmokWeatherMath::Clamp01(TransitionElapsed / Config.TransitionSeconds));
}

// ---- writes -----------------------------------------------------------------------------------------------------

AGolmokTimeOfDay* UGolmokWeatherSubsystem::ResolveTimeOfDay(bool bForce)
{
	if (AGolmokTimeOfDay* Cached = TimeOfDay.Get())
	{
		return Cached;
	}
	if (InteriorHandle.IsValid())
	{
		// The cached one was destroyed: forget its binding and its interior state.
		UnbindTimeOfDay();
		UpdateRainFx();
	}
	if (!bForce && TimeOfDaySearchCooldown > 0.0)
	{
		return nullptr;
	}
	TimeOfDaySearchCooldown = GolmokWeather::Runtime::TimeOfDaySearchSeconds;
	AGolmokTimeOfDay* Found = AGolmokTimeOfDay::Find(GetWorld());
	if (Found)
	{
		TimeOfDay = Found;
		InteriorHandle = Found->OnInteriorChanged.AddUObject(this, &UGolmokWeatherSubsystem::InteriorChanged);
		bInterior = Found->IsInterior();
		bPushedSettled = true; // a time of day we never talked to is settled; PushModifier compares its modifier
		PushModifier(/*bSettled*/ !bTransitioning);
		UpdateRainFx();
	}
	return Found;
}

void UGolmokWeatherSubsystem::UnbindTimeOfDay()
{
	if (AGolmokTimeOfDay* Tod = TimeOfDay.Get())
	{
		Tod->OnInteriorChanged.Remove(InteriorHandle);
	}
	InteriorHandle.Reset();
	TimeOfDay.Reset();
	bInterior = false;
}

void UGolmokWeatherSubsystem::PushModifier(bool bSettled)
{
	AGolmokTimeOfDay* Tod = TimeOfDay.Get();
	if (!Tod)
	{
		return;
	}
	// Skip when nothing changed; bSettled true reaches the time of day exactly once per landing (design 5-4).
	const bool bChanged = !GolmokWeather::Runtime::SameModifier(Tod->GetWeatherModifier(), ModifierNow);
	if (!bChanged && (bPushedSettled || !bSettled))
	{
		return;
	}
	Tod->SetWeatherModifier(ModifierNow, bSettled);
	bPushedSettled = bSettled;
}

void UGolmokWeatherSubsystem::WriteMpc(bool bForce)
{
	UWorld* World = GetWorld();
	if (!Mpc || !World)
	{
		return;
	}
	// [미확인 §17 #10] the instance exists for a collection loaded after the world (UMaterialParameterCollection::PostLoad adds it).
	UMaterialParameterCollectionInstance* Instance = World->GetParameterCollectionInstance(Mpc);
	if (!Instance)
	{
		return;
	}
	using GolmokWeather::Runtime::ShouldWrite;
	if (bForce || ShouldWrite(MpcRain, RainNow))
	{
		Instance->SetScalarParameterValue(MpcRainName, static_cast<float>(RainNow));
		MpcRain = RainNow;
	}
	if (bForce || ShouldWrite(MpcWetness, SurfaceNow.Wetness))
	{
		Instance->SetScalarParameterValue(MpcWetnessName, static_cast<float>(SurfaceNow.Wetness));
		MpcWetness = SurfaceNow.Wetness;
	}
	if (bForce || ShouldWrite(MpcPuddle, SurfaceNow.Puddle))
	{
		Instance->SetScalarParameterValue(MpcPuddleName, static_cast<float>(SurfaceNow.Puddle));
		MpcPuddle = SurfaceNow.Puddle;
	}
}

void UGolmokWeatherSubsystem::UpdateRainFx()
{
	AActor* FxActor = RainFxActor.Get();
	if (!IsValid(FxActor))
	{
		return;
	}
	using GolmokWeather::Runtime::ShouldWrite;
	// Parameters follow RainNow even while inactive, so a read-back always matches GetRainIntensity().
	if (ShouldWrite(FxRain, RainNow))
	{
		FxRain = RainNow;
		FxSpawnRate = RainNow * Config.MaxSpawnRate;
		GolmokWeatherRainFx::WriteRain(FxActor, static_cast<float>(FxRain), static_cast<float>(FxSpawnRate));
	}
	const bool bWant = bFxEnabled && !bInterior && RainNow > GolmokWeatherMath::ValueEpsilon;
	if (bWant)
	{
		// Follow the camera (one frame late is harmless: the particles simulate in world space); none while indoors.
		if (const APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(GetWorld(), 0))
		{
			GolmokWeatherRainFx::Follow(FxActor, Camera->GetCameraLocation() + FVector(0.0, 0.0, Config.HeightOffsetCm));
		}
		if (!bFxActive)
		{
			GolmokWeatherRainFx::SetActive(FxActor, true);
			bFxActive = true;
		}
	}
	else if (bFxActive)
	{
		GolmokWeatherRainFx::SetActive(FxActor, false);
		bFxActive = false;
	}
}

void UGolmokWeatherSubsystem::InteriorChanged(bool bInInterior)
{
	bInterior = bInInterior;
	UpdateRainFx();
}

void UGolmokWeatherSubsystem::Traveled(const FString& ZoneId)
{
	ResetRainFx();
}

void UGolmokWeatherSubsystem::ResetRainFx()
{
	AActor* FxActor = RainFxActor.Get();
	if (!IsValid(FxActor))
	{
		return;
	}
	// Move to the camera first so the restarted system does not simulate one frame at the old place.
	if (bFxActive)
	{
		if (const APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(GetWorld(), 0))
		{
			GolmokWeatherRainFx::Follow(FxActor, Camera->GetCameraLocation() + FVector(0.0, 0.0, Config.HeightOffsetCm));
		}
	}
	GolmokWeatherRainFx::Reset(FxActor, bFxActive);
}

void UGolmokWeatherSubsystem::SetFxEnabled(bool bEnabled)
{
	bFxEnabled = bEnabled;
	UpdateRainFx();
}

UFXSystemComponent* UGolmokWeatherSubsystem::GetRainFxComponent() const
{
	return GolmokWeatherRainFx::GetComponent(RainFxActor.Get());
}

// ---- control ----------------------------------------------------------------------------------------------------

bool UGolmokWeatherSubsystem::CheckCanChange(FString& OutMessage) const
{
	if (!bConfigLoaded)
	{
		OutMessage = FString::Printf(TEXT("weather: off - %s"), *ConfigError);
		return false;
	}
	if (IsFrozen())
	{
		OutMessage = GolmokWeather::Runtime::PhotoRefusal;
		return false;
	}
	return true;
}

bool UGolmokWeatherSubsystem::SetWeather(EGolmokWeather Weather, float Intensity, bool bInstant, FString& OutMessage)
{
	if (!CheckCanChange(OutMessage))
	{
		return false;
	}
	const double Value = static_cast<double>(Intensity);
	if (Weather == EGolmokWeather::Rain && !GolmokWeatherMath::IsValidRainIntensity(Value))
	{
		OutMessage = FString::Printf(TEXT("weather: rain intensity must be in [%.2f, %.2f], got %g"), GolmokWeatherMath::MinRainIntensity,
			GolmokWeatherMath::MaxRainIntensity, Value);
		return false;
	}
	const FString Text = GolmokWeather::Runtime::TargetText(Weather, Weather == EGolmokWeather::Rain ? Value : 0.0);
	if (Mode == EGolmokWeatherMode::Schedule)
	{
		Mode = EGolmokWeatherMode::Fixed; // WP-14a judgement #3: an explicit choice leaves the automatic mode
		UE_LOG(LogGolmok, Display, TEXT("weather: %s in schedule mode -> fixed"), WeatherName(Weather));
	}
	bInitialSchedulePending = false;
	bScheduleNoClock = false;
	ResolveTimeOfDay(/*bForce*/ true);

	const bool bSame = Target == Weather &&
		FMath::Abs(TargetIntensity - GolmokWeatherMath::TargetRain(GolmokWeather::Runtime::ToMath(Weather), Value)) <= GolmokWeather::Runtime::SameIntensityTolerance;
	const bool bWasTransitioning = bTransitioning;
	StartTarget(Weather, Value, bInstant, /*bBroadcast*/ true);
	if (bSame)
	{
		OutMessage = bInstant && bWasTransitioning ? FString::Printf(TEXT("weather: %s (transition finished now)"), *Text)
			: FString::Printf(TEXT("weather: already %s"), *Text);
	}
	else if (bTransitioning)
	{
		OutMessage = FString::Printf(TEXT("weather: %s over %.1f s"), *Text, Config.TransitionSeconds);
	}
	else
	{
		OutMessage = FString::Printf(TEXT("weather: %s (instant)"), *Text);
	}
	return true;
}

bool UGolmokWeatherSubsystem::SetMode(EGolmokWeatherMode NewMode, FString& OutMessage)
{
	if (!CheckCanChange(OutMessage))
	{
		return false;
	}
	const EGolmokWeatherMode Before = Mode;
	Mode = NewMode;
	bInitialSchedulePending = false;
	bScheduleNoClock = false;
	if (Mode == EGolmokWeatherMode::Fixed)
	{
		OutMessage = FString::Printf(TEXT("weather: mode %s -> fixed (%s kept)"), ModeName(Before), *GolmokWeather::Runtime::TargetText(Target, TargetIntensity));
		return true;
	}
	ResolveTimeOfDay(/*bForce*/ true);
	if (!EvaluateSchedule(/*bInstant*/ false, /*bBroadcast*/ true))
	{
		OutMessage = FString::Printf(TEXT("weather: mode %s -> schedule (no clock - %s kept until the time of day has one)"), ModeName(Before),
			*GolmokWeather::Runtime::TargetText(Target, TargetIntensity));
		return true;
	}
	const int32 Index = GetScheduleIndexNow();
	OutMessage = FString::Printf(TEXT("weather: mode %s -> schedule, slot %s%s"), ModeName(Before),
		Index >= 0 ? *GolmokWeather::Runtime::SlotText(Config.Schedule[Index]) : TEXT("-"), bTransitioning ? TEXT(" (transition)") : TEXT(""));
	return true;
}

bool UGolmokWeatherSubsystem::SetSurface(float Wetness, float Puddle, FString& OutMessage)
{
	if (!CheckCanChange(OutMessage))
	{
		return false;
	}
	SurfaceNow = GolmokWeatherMath::ClampSurface(static_cast<double>(Wetness), static_cast<double>(Puddle));
	WriteMpc(/*bForce*/ false);
	OutMessage = FString::Printf(TEXT("weather: surface wet %.2f puddle %.2f"), SurfaceNow.Wetness, SurfaceNow.Puddle);
	return true;
}

bool UGolmokWeatherSubsystem::RunCommand(const TArray<FString>& Args, FString& OutMessage)
{
	using GolmokWeather::Runtime::ParseNumber;
	const FString Usage = TEXT("weather: usage: golmok.weather [status] | clear|overcast [instant] | rain [light|moderate|heavy|<0.05~1>] [instant] | "
							   "mode fixed|schedule | list | surface <wetness> [puddle] | fx on|off");
	const FString Verb = Args.Num() > 0 ? Args[0] : FString(TEXT("status"));

	if (Verb == TEXT("status") && Args.Num() <= 1)
	{
		OutMessage = DescribeStatus();
		return true;
	}
	if (Verb == TEXT("list") && Args.Num() == 1)
	{
		OutMessage = DescribeList();
		return true;
	}
	if (Verb == TEXT("clear") || Verb == TEXT("overcast"))
	{
		if (Args.Num() > 2 || (Args.Num() == 2 && Args[1] != TEXT("instant")))
		{
			const FString& Word = Args[1] != TEXT("instant") ? Args[1] : Args[2];
			OutMessage = FString::Printf(TEXT("weather: unknown word '%s' (golmok.weather %s [instant])"), *Word, *Verb);
			return false;
		}
		EGolmokWeather Weather = EGolmokWeather::Clear;
		ParseWeather(Verb, Weather);
		return SetWeather(Weather, 0.f, Args.Num() == 2, OutMessage);
	}
	if (Verb == TEXT("rain"))
	{
		if (!bConfigLoaded)
		{
			return CheckCanChange(OutMessage);
		}
		double Intensity = Config.RainModerate;
		int32 Next = 1;
		if (Args.Num() > Next && Args[Next] != TEXT("instant"))
		{
			double Number = 0.0;
			if (!GolmokWeather::ResolveRainLevel(Config, Args[Next], Intensity))
			{
				if (!ParseNumber(Args[Next], Number) || !GolmokWeatherMath::IsValidRainIntensity(Number))
				{
					OutMessage = FString::Printf(TEXT("weather: rain intensity must be light|moderate|heavy or a number in [0.05, 1], got '%s'"), *Args[Next]);
					return false;
				}
				Intensity = Number;
			}
			++Next;
		}
		bool bInstant = false;
		if (Args.Num() > Next && Args[Next] == TEXT("instant"))
		{
			bInstant = true;
			++Next;
		}
		if (Args.Num() > Next)
		{
			OutMessage = FString::Printf(TEXT("weather: unknown word '%s' (golmok.weather rain [light|moderate|heavy|<0.05~1>] [instant])"), *Args[Next]);
			return false;
		}
		return SetWeather(EGolmokWeather::Rain, static_cast<float>(Intensity), bInstant, OutMessage);
	}
	if (Verb == TEXT("mode"))
	{
		EGolmokWeatherMode NewMode = EGolmokWeatherMode::Fixed;
		if (Args.Num() != 2 || !ParseMode(Args[1], NewMode))
		{
			OutMessage = FString::Printf(TEXT("weather: mode must be fixed|schedule, got '%s'"), Args.Num() >= 2 ? *Args[1] : TEXT(""));
			return false;
		}
		return SetMode(NewMode, OutMessage);
	}
	if (Verb == TEXT("surface"))
	{
		double Wetness = 0.0;
		double Puddle = SurfaceNow.Puddle; // omitted: keep the current puddle (clamped to the new wetness)
		const bool bWetOk = Args.Num() >= 2 && Args.Num() <= 3 && ParseNumber(Args[1], Wetness) && Wetness >= 0.0 && Wetness <= 1.0;
		const bool bPuddleOk = Args.Num() < 3 || (ParseNumber(Args[2], Puddle) && Puddle >= 0.0 && Puddle <= 1.0);
		if (!bWetOk || !bPuddleOk)
		{
			OutMessage = TEXT("weather: surface takes <wetness> [puddle], numbers in [0, 1]");
			return false;
		}
		return SetSurface(static_cast<float>(Wetness), static_cast<float>(Puddle), OutMessage);
	}
	if (Verb == TEXT("fx"))
	{
		if (Args.Num() != 2 || (Args[1] != TEXT("on") && Args[1] != TEXT("off")))
		{
			OutMessage = FString::Printf(TEXT("weather: fx must be on|off, got '%s'"), Args.Num() >= 2 ? *Args[1] : TEXT(""));
			return false;
		}
		// Design 7-3 / 10: no rain fx calls while photo mode holds the frozen rain.
		if (!CheckCanChange(OutMessage))
		{
			return false;
		}
		SetFxEnabled(Args[1] == TEXT("on"));
		OutMessage = FString::Printf(TEXT("weather: fx %s"), *DescribeFx());
		return true;
	}
	OutMessage = FString::Printf(TEXT("weather: unknown command '%s'\n%s"), *FString::Join(Args, TEXT(" ")), *Usage);
	return false;
}

// ---- descriptions -----------------------------------------------------------------------------------------------

FString UGolmokWeatherSubsystem::DescribeMpc() const
{
	if (!bConfigLoaded)
	{
		return TEXT("off");
	}
	return Mpc ? TEXT("ok") : TEXT("missing");
}

FString UGolmokWeatherSubsystem::DescribeFx() const
{
	switch (static_cast<GolmokWeatherRainFx::ELoad>(RainFxLoad))
	{
	case GolmokWeatherRainFx::ELoad::Disabled:
		return TEXT("disabled");
	case GolmokWeatherRainFx::ELoad::Missing:
		return TEXT("missing");
	default:
		break;
	}
	if (!bConfigLoaded)
	{
		return TEXT("disabled");
	}
	if (!bFxEnabled)
	{
		return TEXT("off");
	}
	if (bInterior)
	{
		return TEXT("interior");
	}
	return bFxActive ? TEXT("on") : TEXT("idle");
}

FString UGolmokWeatherSubsystem::BuildHudLine() const
{
	using GolmokWeather::Runtime::TargetText;
	if (!bConfigLoaded)
	{
		return FString::Printf(TEXT("weather: off - %s"), *ConfigError);
	}
	// clear / overcast carry no intensity number: "weather: clear | now 0.00 ...".
	FString Line = TEXT("weather: ") + TargetText(Target, TargetIntensity);
	if (bTransitioning)
	{
		Line += FString::Printf(TEXT(" (from %s %d%%)"), *TargetText(FromWeather, FromIntensity), FMath::RoundToInt(GetTransitionAlpha() * 100.f));
	}
	Line += FString::Printf(TEXT(" | now %.2f wet %.2f puddle %.2f | %s | fx %s"), RainNow, SurfaceNow.Wetness, SurfaceNow.Puddle, ModeName(Mode), *DescribeFx());
	if (Mode == EGolmokWeatherMode::Schedule)
	{
		const int32 Index = GetScheduleIndexNow();
		if (Index >= 0)
		{
			Line += TEXT(" | schedule next ") + GolmokWeather::Runtime::SlotText(Config.Schedule[(Index + 1) % Config.Schedule.Num()]);
		}
		else
		{
			Line += TEXT(" | schedule no clock");
		}
	}
	if (IsFrozen())
	{
		Line += TEXT(" | frozen");
	}
	return Line;
}

FString UGolmokWeatherSubsystem::DescribeStatus() const
{
	using GolmokWeather::Runtime::SlotText;
	using GolmokWeather::Runtime::TargetText;
	if (!bConfigLoaded)
	{
		return FString::Printf(TEXT("weather: off - %s"), *ConfigError);
	}
	FString Out = FString::Printf(TEXT("weather: target %s | current %s"), *TargetText(Target, TargetIntensity),
		bTransitioning ? *FString::Printf(TEXT("from %s, alpha %.2f (%.1f / %.1f s)"), *TargetText(FromWeather, FromIntensity), GetTransitionAlpha(),
							 TransitionElapsed, Config.TransitionSeconds)
					   : TEXT("settled"));
	const GolmokWeatherMath::Modifier& M = ModifierNow;
	Out += FString::Printf(TEXT("\n  modifier lux %.3f sky %.3f fog %.3f falloff %.3f kelvin %.0f weight %.2f exposure %.2f"), M.LuxScale, M.SkyScale,
		M.FogScale, M.FogHeightFalloffScale, M.KelvinTarget, M.KelvinWeight, M.ExposureOffset);
	Out += FString::Printf(TEXT("\n  rain now %.3f | wet %.3f | puddle %.3f"), RainNow, SurfaceNow.Wetness, SurfaceNow.Puddle);
	Out += FString::Printf(TEXT("\n  mode %s"), ModeName(Mode));
	const int32 Index = GetScheduleIndexNow();
	if (Index >= 0)
	{
		Out += FString::Printf(TEXT(" | schedule: now %s, next %s"), *SlotText(Config.Schedule[Index]),
			*SlotText(Config.Schedule[(Index + 1) % Config.Schedule.Num()]));
	}
	else
	{
		Out += TEXT(" | schedule: no clock");
	}
	Out += FString::Printf(TEXT("\n  mpc %s | fx %s | interior %s | frozen %s"), *DescribeMpc(), *DescribeFx(), bInterior ? TEXT("yes") : TEXT("no"),
		IsFrozen() ? TEXT("yes") : TEXT("no"));
	return Out;
}

FString UGolmokWeatherSubsystem::DescribeList() const
{
	if (!bConfigLoaded)
	{
		return FString::Printf(TEXT("weather: off - %s"), *ConfigError);
	}
	const int32 Current = GetScheduleIndexNow();
	FString Out = FString::Printf(TEXT("weather: schedule (%d slots, mode %s%s)"), Config.Schedule.Num(), ModeName(Mode),
		Current < 0 ? TEXT(", no clock") : TEXT(""));
	for (int32 I = 0; I < Config.Schedule.Num(); ++I)
	{
		Out += FString::Printf(TEXT("\n  %s %s"), I == Current ? TEXT("*") : TEXT(" "), *GolmokWeather::Runtime::SlotText(Config.Schedule[I]));
	}
	return Out;
}

// ---- console ----------------------------------------------------------------------------------------------------

namespace GolmokWeather
{
	void CmdWeather(const TArray<FString>& Args, UWorld* World)
	{
		UGolmokWeatherSubsystem* Weather = UGolmokWeatherSubsystem::Get(World);
		if (!Weather)
		{
			UE_LOG(LogGolmok, Warning, TEXT("golmok.weather: no game world"));
			return;
		}
		FString Message;
		if (Weather->RunCommand(Args, Message))
		{
			UE_LOG(LogGolmok, Log, TEXT("%s"), *Message);
		}
		else
		{
			UE_LOG(LogGolmok, Warning, TEXT("%s"), *Message);
		}
	}

	FAutoConsoleCommandWithWorldAndArgs GCmdWeather(TEXT("golmok.weather"),
		TEXT("golmok.weather [status] | clear|overcast [instant] | rain [light|moderate|heavy|<0.05~1>] [instant] | mode fixed|schedule | list | "
			 "surface <wetness> [puddle] | fx on|off: weather (WP-16a)."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdWeather));
} // namespace GolmokWeather
