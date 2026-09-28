#include "Lighting/GolmokTimeOfDay.h"

#include "Golmok.h"

#include "Lighting/GolmokClockMath.h"
#include "Photo/GolmokPhotoModeSubsystem.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkyLightComponent.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/SkyLight.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Internationalization/Regex.h"
#include "Misc/DateTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

// ---- presets JSON ---------------------------------------------------------------------------------------------

// Named (not anonymous) so a unity build that concatenates this file with Zones/GolmokZoneManifest.cpp, which has
// its own Fail(FString&, const FString&) in an unnamed namespace, never sees two bodies for the same function.
namespace GolmokLightingJson
{
	// Keys are passed as FString objects (never TCHAR literals) so the FJsonObject::TryGet*Field overloads that
	// exist in 5.x (const FString& and, since 5.4, FStringView) never become ambiguous (WP-04 rule).
	using FJsonObjectPtr = TSharedPtr<FJsonObject>;
	using FJsonArray = TArray<TSharedPtr<FJsonValue>>;

	// WP-14a: schema 2 adds the keyframe "time" of the cycle presets; a schema 1 file is an error (single source).
	constexpr int32 SchemaVersion = 2;
	constexpr int32 CycleLength = 4;
	const TCHAR* InteriorName = TEXT("interior");

	/** Numeric preset keys with their allowed range (same table as lighting_presets.RANGES / test_lighting_presets.py). */
	struct FNumberKey
	{
		const TCHAR* Name;
		double Lo;
		double Hi;
		bool bHalfOpen; // lo <= v < hi
	};

	const FNumberKey NumberKeys[] = {
		{TEXT("pitch"), -90.0, 90.0, false},
		{TEXT("yaw"), 0.0, 360.0, true},
		{TEXT("lux"), 0.0, 150000.0, false},
		{TEXT("kelvin"), 1700.0, 12000.0, false},
		{TEXT("sky"), 0.0, 10.0, false},
		{TEXT("fog"), 0.0, 1.0, false},
		{TEXT("fog_height_falloff"), 0.001, 2.0, false},
		{TEXT("exposure_bias"), -5.0, 5.0, false},
	};
	constexpr int32 NumberKeyCount = 8;
	static_assert(UE_ARRAY_COUNT(NumberKeys) == NumberKeyCount, "NumberKeys table size");
	const TCHAR* VolumetricKey = TEXT("volumetric");
	const TCHAR* TimeKey = TEXT("time");

	bool Fail(FString& Error, const FString& Message)
	{
		Error = FString::Printf(TEXT("lighting_presets.json: %s"), *Message);
		return false;
	}

	bool FailPreset(FString& Error, const FString& Preset, const FString& Message)
	{
		return Fail(Error, FString::Printf(TEXT("preset %s: %s"), *Preset, *Message));
	}

	bool IsKnownPresetKey(const FString& Key)
	{
		if (Key == VolumetricKey || Key == TimeKey)
		{
			return true;
		}
		for (const FNumberKey& K : NumberKeys)
		{
			if (Key == K.Name)
			{
				return true;
			}
		}
		return false;
	}

	/** Present-and-typed number lookup (a JSON bool / string is not accepted as a number, like Python). */
	bool ReadNumber(const FJsonObjectPtr& Obj, const FString& Key, bool& bOutPresent, double& OutValue)
	{
		OutValue = 0.0;
		// UE 5.8: FJsonObject::Values is keyed by UE::FSharedString, so look the field up by view instead of FString.
		const TSharedPtr<FJsonValue> Found = Obj->TryGetField(Key);
		bOutPresent = Found.IsValid();
		if (!bOutPresent)
		{
			return true;
		}
		if (Found->Type != EJson::Number)
		{
			return false;
		}
		OutValue = Found->AsNumber();
		return true;
	}

	bool ReadBool(const FJsonObjectPtr& Obj, const FString& Key, bool& bOutPresent, bool& bOutValue)
	{
		bOutValue = false;
		const TSharedPtr<FJsonValue> Found = Obj->TryGetField(Key);
		bOutPresent = Found.IsValid();
		if (!bOutPresent)
		{
			return true;
		}
		if (Found->Type != EJson::Boolean)
		{
			return false;
		}
		bOutValue = Found->AsBool();
		return true;
	}

	bool ParsePreset(const FString& Name, const FJsonObjectPtr& Obj, FGolmokLightingPreset& Out, FString& Error)
	{
		const FRegexPattern NamePattern(TEXT("^[a-z][a-z0-9_]*$"));
		FRegexMatcher Matcher(NamePattern, Name);
		if (!Matcher.FindNext())
		{
			return FailPreset(Error, Name, TEXT("name must match ^[a-z][a-z0-9_]*$"));
		}
		if (!Obj.IsValid())
		{
			return FailPreset(Error, Name, TEXT("preset must be an object"));
		}
		for (const auto& Pair : Obj->Values)
		{
			const FString Key(*Pair.Key); // UE::FSharedString key -> FString
			if (!IsKnownPresetKey(Key))
			{
				return FailPreset(Error, Name, FString::Printf(TEXT("unknown key '%s'"), *Key));
			}
		}

		Out = FGolmokLightingPreset();
		Out.Name = FName(*Name);
		double Values[NumberKeyCount] = {};
		bool bPresent[NumberKeyCount] = {};
		for (int32 i = 0; i < NumberKeyCount; ++i)
		{
			const FNumberKey& K = NumberKeys[i];
			const FString Key(K.Name);
			if (!ReadNumber(Obj, Key, bPresent[i], Values[i]))
			{
				return FailPreset(Error, Name, FString::Printf(TEXT("%s must be a number"), K.Name));
			}
			if (!bPresent[i])
			{
				continue;
			}
			const double V = Values[i];
			const bool bInside = K.bHalfOpen ? (V >= K.Lo && V < K.Hi) : (V >= K.Lo && V <= K.Hi);
			if (!bInside)
			{
				return FailPreset(Error, Name,
					FString::Printf(TEXT("%s %g out of range [%g, %g%s"), K.Name, V, K.Lo, K.Hi, K.bHalfOpen ? TEXT(")") : TEXT("]")));
			}
		}
		bool bHasVolumetric = false;
		bool bVolumetric = false;
		if (!ReadBool(Obj, FString(VolumetricKey), bHasVolumetric, bVolumetric))
		{
			return FailPreset(Error, Name, TEXT("volumetric must be a bool"));
		}
		int TimeMinutes = 0;
		const TSharedPtr<FJsonValue> TimeValue = Obj->TryGetField(FString(TimeKey));
		if (TimeValue.IsValid())
		{
			const FString TimeText = TimeValue->Type == EJson::String ? TimeValue->AsString() : FString();
			if (!GolmokClockMath::ParseHHMM(*TimeText, TimeMinutes))
			{
				return FailPreset(Error, Name, TEXT("time must be HH:MM (00:00-23:59)"));
			}
		}

		// Index into NumberKeys: 0 pitch, 1 yaw, 2 lux, 3 kelvin, 4 sky, 5 fog, 6 fog_height_falloff, 7 exposure_bias.
		auto GroupComplete = [&](const int32* Indices, int32 Count, FString& OutMissing) -> bool
		{
			int32 Have = 0;
			for (int32 i = 0; i < Count; ++i)
			{
				Have += bPresent[Indices[i]] ? 1 : 0;
			}
			if (Have != 0 && Have != Count)
			{
				for (int32 i = 0; i < Count; ++i)
				{
					if (!bPresent[Indices[i]])
					{
						OutMissing = NumberKeys[Indices[i]].Name;
						break;
					}
				}
				return false;
			}
			return true;
		};
		const int32 SunGroup[] = {0, 1, 2, 3};
		const int32 FogGroup[] = {5, 6};
		FString Missing;
		if (!GroupComplete(SunGroup, 4, Missing))
		{
			return FailPreset(Error, Name, FString::Printf(TEXT("missing key '%s' (pitch, yaw, lux, kelvin are set together)"), *Missing));
		}
		if (!GroupComplete(FogGroup, 2, Missing))
		{
			return FailPreset(Error, Name, FString::Printf(TEXT("missing key '%s' (fog, fog_height_falloff are set together)"), *Missing));
		}

		Out.bHasSun = bPresent[0];
		Out.PitchDeg = Values[0];
		Out.YawDeg = Values[1];
		Out.Lux = Values[2];
		Out.Kelvin = bPresent[3] ? Values[3] : Out.Kelvin;
		Out.bHasSky = bPresent[4];
		Out.Sky = bPresent[4] ? Values[4] : Out.Sky;
		Out.bHasFog = bPresent[5];
		Out.Fog = Values[5];
		Out.FogHeightFalloff = bPresent[6] ? Values[6] : Out.FogHeightFalloff;
		Out.bHasVolumetric = bHasVolumetric;
		Out.bVolumetric = bVolumetric;
		Out.bHasExposure = bPresent[7];
		Out.ExposureBias = Values[7];
		Out.bHasTime = TimeValue.IsValid();
		Out.TimeMinutes = static_cast<double>(TimeMinutes);
		return true;
	}

	const FGolmokLightingPreset* FindByName(const TArray<FGolmokLightingPreset>& Presets, FName Name)
	{
		for (const FGolmokLightingPreset& P : Presets)
		{
			if (P.Name == Name)
			{
				return &P;
			}
		}
		return nullptr;
	}

	/** Missing key of a preset that must be complete (cycle), in REQUIRED_KEYS order; empty when complete. */
	FString FirstMissingKey(const FGolmokLightingPreset& P)
	{
		if (!P.bHasSun)
		{
			return TEXT("pitch");
		}
		if (!P.bHasSky)
		{
			return TEXT("sky");
		}
		if (!P.bHasFog)
		{
			return TEXT("fog");
		}
		if (!P.bHasVolumetric)
		{
			return TEXT("volumetric");
		}
		if (!P.bHasExposure)
		{
			return TEXT("exposure_bias");
		}
		return FString();
	}
} // namespace GolmokLightingJson

bool AGolmokTimeOfDay::ParsePresetsText(const FString& Json, TArray<FGolmokLightingPreset>& Out, TArray<FName>& OutCycle, FString& Error)
{
	using namespace GolmokLightingJson;
	Out.Reset();
	OutCycle.Reset();
	Error.Reset();

	FJsonObjectPtr Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Json);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		return Fail(Error, FString::Printf(TEXT("invalid JSON: %s"), *Reader->GetErrorMessage()));
	}

	const FString KeySchemaVersion(TEXT("schema_version"));
	const FString KeyCycle(TEXT("cycle"));
	const FString KeyPresets(TEXT("presets"));

	double Version = 0.0;
	bool bHasVersion = false;
	if (!ReadNumber(Root, KeySchemaVersion, bHasVersion, Version) || !bHasVersion || Version != static_cast<double>(SchemaVersion))
	{
		return Fail(Error, FString::Printf(TEXT("schema_version %g (expected %d)"), Version, SchemaVersion));
	}
	for (const auto& Pair : Root->Values)
	{
		const FString Key(*Pair.Key); // UE::FSharedString key -> FString
		if (Key != KeySchemaVersion && Key != KeyCycle && Key != KeyPresets)
		{
			return Fail(Error, FString::Printf(TEXT("unknown top-level key '%s'"), *Key));
		}
	}

	const FJsonObjectPtr* PresetsObj = nullptr;
	if (!Root->TryGetObjectField(KeyPresets, PresetsObj) || !PresetsObj || !PresetsObj->IsValid() || (*PresetsObj)->Values.Num() == 0)
	{
		return Fail(Error, TEXT("presets must be a non-empty object"));
	}
	for (const auto& Pair : (*PresetsObj)->Values)
	{
		const FJsonObjectPtr* PresetObj = nullptr;
		FJsonObjectPtr PresetPtr;
		if (Pair.Value.IsValid() && Pair.Value->TryGetObject(PresetObj) && PresetObj)
		{
			PresetPtr = *PresetObj;
		}
		FGolmokLightingPreset Preset;
		if (!ParsePreset(FString(*Pair.Key), PresetPtr, Preset, Error))
		{
			return false;
		}
		Out.Add(MoveTemp(Preset));
	}

	const FJsonArray* CycleArr = nullptr;
	if (!Root->TryGetArrayField(KeyCycle, CycleArr) || !CycleArr || CycleArr->Num() != CycleLength)
	{
		return Fail(Error, FString::Printf(TEXT("cycle must be a list of exactly %d preset names"), CycleLength));
	}
	for (const TSharedPtr<FJsonValue>& V : *CycleArr)
	{
		FString NameText;
		if (!V.IsValid() || V->Type != EJson::String || !V->TryGetString(NameText))
		{
			return Fail(Error, TEXT("cycle entries must be strings"));
		}
		const FName Name(*NameText);
		if (OutCycle.Contains(Name))
		{
			return Fail(Error, TEXT("cycle has duplicate names"));
		}
		const FGolmokLightingPreset* P = FindByName(Out, Name);
		if (!P)
		{
			return Fail(Error, FString::Printf(TEXT("cycle names unknown preset '%s'"), *NameText));
		}
		if (!P->IsComplete())
		{
			return FailPreset(Error, NameText, FString::Printf(TEXT("missing key '%s' (cycle presets need all 9 keys)"), *FirstMissingKey(*P)));
		}
		if (!P->bHasTime)
		{
			return FailPreset(Error, NameText, TEXT("missing key 'time' (cycle presets need a keyframe time HH:MM)"));
		}
		OutCycle.Add(Name);
	}
	for (const FGolmokLightingPreset& P : Out)
	{
		if (P.bHasTime && !OutCycle.Contains(P.Name))
		{
			return FailPreset(Error, P.Name.ToString(), TEXT("time is only allowed on cycle presets"));
		}
	}
	{
		double Times[CycleLength] = {};
		for (int32 i = 0; i < CycleLength; ++i)
		{
			Times[i] = FindByName(Out, OutCycle[i])->TimeMinutes;
		}
		int Bad = -1;
		const int Order = GolmokClockMath::CheckKeyframeOrder(Times, CycleLength, Bad);
		if (Order != 0)
		{
			TCHAR Before[6];
			TCHAR After[6];
			GolmokClockMath::FormatHHMM(Times[Bad - 1], Before);
			GolmokClockMath::FormatHHMM(Times[Bad], After);
			return Order == 1
				? Fail(Error, FString::Printf(TEXT("cycle has duplicate time %s (%s, %s)"), After, *OutCycle[Bad - 1].ToString(), *OutCycle[Bad].ToString()))
				: Fail(Error, FString::Printf(TEXT("cycle times must increase (%s %s is before %s %s)"), *OutCycle[Bad].ToString(), After,
					  *OutCycle[Bad - 1].ToString(), Before));
		}
	}

	const FName Interior(InteriorName);
	const FGolmokLightingPreset* InteriorEntry = FindByName(Out, Interior);
	if (!InteriorEntry)
	{
		return Fail(Error, FString::Printf(TEXT("missing preset '%s'"), InteriorName));
	}
	if (OutCycle.Contains(Interior))
	{
		return FailPreset(Error, InteriorName, TEXT("must not be in cycle"));
	}
	if (!InteriorEntry->bHasFog || InteriorEntry->Fog != 0.0)
	{
		return FailPreset(Error, InteriorName, FString::Printf(TEXT("fog must be 0 (got %g)"), InteriorEntry->bHasFog ? InteriorEntry->Fog : 0.0));
	}
	if (!InteriorEntry->bHasExposure || InteriorEntry->ExposureBias <= 0.0)
	{
		return FailPreset(Error, InteriorName, TEXT("exposure_bias must be > 0"));
	}
	return true;
}

bool AGolmokTimeOfDay::LoadPresetsFile(const FString& FilePath, TArray<FGolmokLightingPreset>& Out, TArray<FName>& OutCycle, FString& Error)
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *FilePath))
	{
		Out.Reset();
		OutCycle.Reset();
		Error = FString::Printf(TEXT("cannot read %s"), *FilePath);
		return false;
	}
	return ParsePresetsText(Text, Out, OutCycle, Error);
}

// ---- lifecycle ------------------------------------------------------------------------------------------------

AGolmokTimeOfDay::AGolmokTimeOfDay()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("TimeOfDayRoot"));
	SetRootComponent(Root);
}

void AGolmokTimeOfDay::BeginPlay()
{
	Super::BeginPlay();
	EnsurePresets();
	ResolveTargets(/*bForce*/ true);
	// The level's authored values (including whether the exposure / temperature overrides were on) are the
	// return point while the base preset is None.
	CaptureState(Initial);
	Applied = Initial;
	TimeOfDayMinutes = static_cast<float>(GolmokClockMath::WrapMinutes(TimeOfDayMinutes));
	if (!InitialPreset.IsNone())
	{
		ApplyPreset(InitialPreset, /*bInstant*/ true);
	}
	// WP-14a: a Clock / Realtime mode from the config starts on the clock state at once (Fixed = WP-05 as before).
	if (ClockMode != EGolmokClockMode::Fixed && CycleTimes.Num() > 0)
	{
		SetTimeOfDay(static_cast<float>(ClockMode == EGolmokClockMode::Realtime ? RealtimeTargetMinutes() : TimeOfDayMinutes), /*bInstant*/ true);
	}
	RefreshNight(/*bBroadcast*/ false);
	UpdateTickEnabled();
}

void AGolmokTimeOfDay::EndPlay(const EEndPlayReason::Type Reason)
{
	InteriorSources.Empty();
	bTransitioning = false;
	bRealtimeHeld = false;
	SetActorTickEnabled(false);
	Super::EndPlay(Reason);
}

AGolmokTimeOfDay* AGolmokTimeOfDay::Find(UWorld* World)
{
	if (!World)
	{
		return nullptr;
	}
	static bool bWarnedMultiple = false;
	AGolmokTimeOfDay* First = nullptr;
	int32 Count = 0;
	for (TActorIterator<AGolmokTimeOfDay> It(World); It; ++It)
	{
		AGolmokTimeOfDay* Actor = *It;
		if (!IsValid(Actor))
		{
			continue;
		}
		if (!First)
		{
			First = Actor;
		}
		++Count;
	}
	if (Count > 1 && !bWarnedMultiple)
	{
		bWarnedMultiple = true;
		UE_LOG(LogGolmok, Warning, TEXT("TimeOfDay: %d AGolmokTimeOfDay actors in %s; using %s (one per level)."), Count, *World->GetMapName(),
			*First->GetName());
	}
	return First;
}

AGolmokTimeOfDay* AGolmokTimeOfDay::FindOrSpawn(UWorld* World)
{
	if (AGolmokTimeOfDay* Existing = Find(World))
	{
		return Existing;
	}
	if (!World || !World->IsGameWorld())
	{
		return nullptr;
	}
	FActorSpawnParameters Params;
	Params.ObjectFlags = RF_Transient;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	AGolmokTimeOfDay* Spawned = World->SpawnActor<AGolmokTimeOfDay>(AGolmokTimeOfDay::StaticClass(), FTransform::Identity, Params);
	if (Spawned)
	{
		UE_LOG(LogGolmok, Log, TEXT("TimeOfDay: spawned a transient AGolmokTimeOfDay in %s (none placed in the level)."), *World->GetMapName());
	}
	return Spawned;
}

// ---- presets --------------------------------------------------------------------------------------------------

FString AGolmokTimeOfDay::ResolvePresetsPath() const
{
	if (FPaths::IsRelative(PresetsFile))
	{
		return FPaths::Combine(FPaths::ProjectConfigDir(), PresetsFile);
	}
	return PresetsFile;
}

bool AGolmokTimeOfDay::EnsurePresets()
{
	if (bPresetsLoaded)
	{
		return true;
	}
	if (bPresetsFailed)
	{
		return false;
	}
	const FString Path = ResolvePresetsPath();
	FString Error;
	if (!LoadPresetsFile(Path, Presets, Cycle, Error))
	{
		bPresetsFailed = true;
		LastError = Error;
		UE_LOG(LogGolmok, Error, TEXT("TimeOfDay: presets not loaded from %s: %s"), *Path, *Error);
		return false;
	}
	bPresetsLoaded = true;
	CycleTimes.Reset();
	for (const FName& Name : Cycle)
	{
		const FGolmokLightingPreset* P = GolmokLightingJson::FindByName(Presets, Name);
		CycleTimes.Add(P ? P->TimeMinutes : 0.0);
	}
	UE_LOG(LogGolmok, Log, TEXT("TimeOfDay: presets loaded (%d) from %s"), Presets.Num(), *Path);
	return true;
}

bool AGolmokTimeOfDay::FindPreset(FName Name, FGolmokLightingPreset& Out) const
{
	if (const FGolmokLightingPreset* P = GolmokLightingJson::FindByName(Presets, Name))
	{
		Out = *P;
		return true;
	}
	return false;
}

TArray<FName> AGolmokTimeOfDay::GetPresetNames() const
{
	TArray<FName> Names;
	Names.Reserve(Presets.Num());
	for (const FGolmokLightingPreset& P : Presets)
	{
		Names.Add(P.Name);
	}
	return Names;
}

bool AGolmokTimeOfDay::IsInterior() const
{
	return InteriorSources.Num() > 0;
}

FString AGolmokTimeOfDay::BaseName() const
{
	return CurrentPreset.IsNone() ? FString(TEXT("(level)")) : CurrentPreset.ToString();
}

bool AGolmokTimeOfDay::ApplyPreset(FName Name, bool bInstant)
{
	if (!EnsurePresets())
	{
		return false;
	}
	FGolmokLightingPreset Preset;
	if (!FindPreset(Name, Preset))
	{
		LastError = FString::Printf(TEXT("unknown preset '%s'"), *Name.ToString());
		return false;
	}
	// WP-14a: a preset without a keyframe time (interior as a base) cannot live on a running clock; Realtime would
	// pull a keyframe straight back to the local time. Both fall back to Fixed, which keeps the preset (WP-05).
	if (ClockMode == EGolmokClockMode::Realtime || (ClockMode != EGolmokClockMode::Fixed && !Preset.bHasTime))
	{
		UE_LOG(LogGolmok, Log, TEXT("TimeOfDay: preset %s in %s mode -> fixed"), *Name.ToString(), ClockModeName(ClockMode));
		ClockMode = EGolmokClockMode::Fixed;
		bRealtimeHeld = false;
	}
	if (Preset.bHasTime)
	{
		TimeOfDayMinutes = static_cast<float>(Preset.TimeMinutes);
	}
	// Fixed: CurrentPreset's own values exactly as in WP-05; Clock: the interpolation at the keyframe (same values)
	// that the running clock then moves on from.
	bBaseFromClock = ClockMode != EGolmokClockMode::Fixed;
	FromPreset = CurrentPreset;
	CurrentPreset = Name;
	TargetPreset = Name;
	StartTransition(ComposeTarget(), bInstant);
	// [WP-13 hook]
	OnPresetChanged.Broadcast(Name, bInstant);
	// [/WP-13 hook]
	RefreshNight(/*bBroadcast*/ true);
	return true;
}

bool AGolmokTimeOfDay::NextPreset()
{
	if (!EnsurePresets() || Cycle.Num() == 0)
	{
		return false;
	}
	const int32 Index = Cycle.IndexOfByKey(CurrentPreset);
	const FName Next = (Index == INDEX_NONE || Index + 1 >= Cycle.Num()) ? Cycle[0] : Cycle[Index + 1];
	return ApplyPreset(Next);
}

void AGolmokTimeOfDay::EnterInterior(FName Source)
{
	const int32 Before = InteriorSources.Num();
	InteriorSources.AddUnique(Source);
	if (Before == 0 && InteriorSources.Num() == 1 && EnsurePresets())
	{
		UE_LOG(LogGolmok, Log, TEXT("TimeOfDay: interior overlay on (source %s, base %s)"), *Source.ToString(), *BaseName());
		FromPreset = CurrentPreset;
		TargetPreset = CurrentPreset;
		StartTransition(ComposeTarget(), /*bInstant*/ false);
		// [WP-13 hook]
		OnInteriorChanged.Broadcast(true);
		// [/WP-13 hook]
	}
}

void AGolmokTimeOfDay::ExitInterior(FName Source)
{
	const int32 Before = InteriorSources.Num();
	InteriorSources.Remove(Source);
	if (Before > 0 && InteriorSources.Num() == 0 && EnsurePresets())
	{
		UE_LOG(LogGolmok, Log, TEXT("TimeOfDay: interior overlay off -> %s"), *BaseName());
		FromPreset = CurrentPreset;
		TargetPreset = CurrentPreset;
		StartTransition(ComposeTarget(), /*bInstant*/ false);
		// [WP-13 hook]
		OnInteriorChanged.Broadcast(false);
		// [/WP-13 hook]
	}
}

// ---- targets --------------------------------------------------------------------------------------------------

bool AGolmokTimeOfDay::ResolveTargets(bool bForce)
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return false;
	}
	const bool bAllValid = SunActor.IsValid() && Sun.IsValid() && Sky.IsValid() && Fog.IsValid() && PostProcess.IsValid();
	if (bAllValid && !bForce)
	{
		return true;
	}

	// Tagged actors win; otherwise the first actor of each class (an unbound volume for the post process).
	AActor* TaggedSun = nullptr;
	AActor* FirstSun = nullptr;
	AActor* TaggedSky = nullptr;
	AActor* FirstSky = nullptr;
	AActor* TaggedFog = nullptr;
	AActor* FirstFog = nullptr;
	AActor* TaggedVolume = nullptr;
	AActor* FirstVolume = nullptr;
	auto Consider = [](AActor*& Tagged, AActor*& First, AActor* Actor, bool bTagged)
	{
		if (bTagged && !Tagged)
		{
			Tagged = Actor;
		}
		if (!First)
		{
			First = Actor;
		}
	};
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		AActor* Actor = *It;
		if (!IsValid(Actor))
		{
			continue;
		}
		const bool bTagged = Actor->ActorHasTag(LightingActorTag);
		if (Actor->IsA<ADirectionalLight>())
		{
			Consider(TaggedSun, FirstSun, Actor, bTagged);
		}
		else if (Actor->IsA<ASkyLight>())
		{
			Consider(TaggedSky, FirstSky, Actor, bTagged);
		}
		else if (Actor->IsA<AExponentialHeightFog>())
		{
			Consider(TaggedFog, FirstFog, Actor, bTagged);
		}
		else if (const APostProcessVolume* Volume = Cast<APostProcessVolume>(Actor))
		{
			if (Volume->bUnbound)
			{
				Consider(TaggedVolume, FirstVolume, Actor, bTagged);
			}
		}
	}

	AActor* SunPick = TaggedSun ? TaggedSun : FirstSun;
	AActor* SkyPick = TaggedSky ? TaggedSky : FirstSky;
	AActor* FogPick = TaggedFog ? TaggedFog : FirstFog;
	AActor* VolumePick = TaggedVolume ? TaggedVolume : FirstVolume;

	// Components through FindComponentByClass so no per-actor accessor name is needed.
	SunActor.Reset();
	Sun.Reset();
	Sky.Reset();
	Fog.Reset();
	PostProcess.Reset();
	if (SunPick)
	{
		SunActor = SunPick;
		if (UDirectionalLightComponent* Component = SunPick->FindComponentByClass<UDirectionalLightComponent>())
		{
			Sun = Component;
		}
	}
	if (SkyPick)
	{
		if (USkyLightComponent* Component = SkyPick->FindComponentByClass<USkyLightComponent>())
		{
			Sky = Component;
		}
	}
	if (FogPick)
	{
		if (UExponentialHeightFogComponent* Component = FogPick->FindComponentByClass<UExponentialHeightFogComponent>())
		{
			Fog = Component;
		}
	}
	if (APostProcessVolume* Volume = Cast<APostProcessVolume>(VolumePick))
	{
		PostProcess = Volume;
	}

	const bool bAnyMissing = !Sun.IsValid() || !Sky.IsValid() || !Fog.IsValid() || !PostProcess.IsValid();
	if (bAnyMissing && !bWarnedTargets)
	{
		bWarnedTargets = true;
		UE_LOG(LogGolmok, Warning,
			TEXT("TimeOfDay: lighting targets missing in %s (sun %d, sky %d, fog %d, post process %d); presets skip them. Tag them '%s' or add them (setup_dev_level)."),
			*World->GetMapName(), Sun.IsValid() ? 1 : 0, Sky.IsValid() ? 1 : 0, Fog.IsValid() ? 1 : 0, PostProcess.IsValid() ? 1 : 0,
			*LightingActorTag.ToString());
	}
	return Sun.IsValid() || Sky.IsValid() || Fog.IsValid() || PostProcess.IsValid();
}

bool AGolmokTimeOfDay::CaptureState(FGolmokLightingState& Out) const
{
	Out = FGolmokLightingState();
	bool bAny = false;
	if (const AActor* Actor = SunActor.Get())
	{
		Out.SunRotation = Actor->GetActorRotation();
		bAny = true;
	}
	if (const UDirectionalLightComponent* Component = Sun.Get())
	{
		Out.Lux = Component->Intensity;
		Out.bUseTemperature = Component->bUseTemperature != 0;
		Out.Kelvin = Component->Temperature;
		bAny = true;
	}
	if (const USkyLightComponent* Component = Sky.Get())
	{
		Out.Sky = Component->Intensity;
		bAny = true;
	}
	if (const UExponentialHeightFogComponent* Component = Fog.Get())
	{
		Out.Fog = Component->FogDensity;
		Out.FogHeightFalloff = Component->FogHeightFalloff;
		Out.bVolumetric = Component->bEnableVolumetricFog != 0;
		bAny = true;
	}
	if (const APostProcessVolume* Volume = PostProcess.Get())
	{
		Out.bExposureOverridden = Volume->Settings.bOverride_AutoExposureBias != 0;
		// A volume whose override is off contributes nothing: the effective bias is the engine default
		// (r.DefaultFeature.AutoExposure.Bias, 1.0 in UE5), so a transition starts from what is on screen.
		Out.ExposureBias = Out.bExposureOverridden ? Volume->Settings.AutoExposureBias : DefaultAutoExposureBias();
		bAny = true;
	}
	return bAny;
}

double AGolmokTimeOfDay::DefaultAutoExposureBias()
{
	static const IConsoleVariable* CVar = IConsoleManager::Get().FindConsoleVariable(TEXT("r.DefaultFeature.AutoExposure.Bias"));
	return CVar ? static_cast<double>(CVar->GetFloat()) : 1.0;
}

// ---- transitions ----------------------------------------------------------------------------------------------

FGolmokLightingState AGolmokTimeOfDay::StateFromPreset(const FGolmokLightingPreset& P, const FGolmokLightingState& Current) const
{
	FGolmokLightingState S = Current;
	if (P.bHasSun)
	{
		// C++ FRotator(Pitch, Yaw, Roll); the editor Python uses unreal.Rotator(roll, pitch, yaw) for the same rotation.
		S.SunRotation = FRotator(P.PitchDeg, P.YawDeg, 0.0);
		S.Lux = P.Lux;
		S.bUseTemperature = true;
		S.Kelvin = P.Kelvin;
	}
	if (P.bHasSky)
	{
		S.Sky = P.Sky;
	}
	if (P.bHasFog)
	{
		S.Fog = P.Fog;
		S.FogHeightFalloff = P.FogHeightFalloff;
	}
	if (P.bHasVolumetric)
	{
		S.bVolumetric = P.bVolumetric;
	}
	if (P.bHasExposure)
	{
		S.bExposureOverridden = true;
		S.ExposureBias = P.ExposureBias;
	}
	return S;
}

FGolmokLightingState AGolmokTimeOfDay::ComposeBase() const
{
	FGolmokLightingState Base = Initial;
	if (bBaseFromClock && EvaluateClock(TimeOfDayMinutes, Base))
	{
		return Base;
	}
	FGolmokLightingPreset Preset;
	if (!CurrentPreset.IsNone() && FindPreset(CurrentPreset, Preset))
	{
		Base = StateFromPreset(Preset, Initial);
	}
	return Base;
}

FGolmokLightingState AGolmokTimeOfDay::ComposeTarget() const
{
	FGolmokLightingState Base = ComposeBase();
	if (IsInterior())
	{
		FGolmokLightingPreset Overlay;
		if (FindPreset(InteriorPreset, Overlay))
		{
			Base = StateFromPreset(Overlay, Base);
		}
	}
	return Base;
}

FGolmokLightingState AGolmokTimeOfDay::Lerp(const FGolmokLightingState& A, const FGolmokLightingState& B, float Alpha)
{
	const double T = static_cast<double>(Alpha);
	FGolmokLightingState R;
	R.SunRotation = FQuat::Slerp(A.SunRotation.Quaternion(), B.SunRotation.Quaternion(), T).Rotator();
	R.Lux = FMath::Lerp(A.Lux, B.Lux, T);
	R.Kelvin = FMath::Lerp(A.Kelvin, B.Kelvin, T);
	R.Sky = FMath::Lerp(A.Sky, B.Sky, T);
	R.Fog = FMath::Lerp(A.Fog, B.Fog, T);
	R.FogHeightFalloff = FMath::Lerp(A.FogHeightFalloff, B.FogHeightFalloff, T);
	R.ExposureBias = FMath::Lerp(A.ExposureBias, B.ExposureBias, T);
	R.bVolumetric = Alpha >= 0.5f ? B.bVolumetric : A.bVolumetric;
	// Mid-transition values are only visible through the overrides, so they stay on while either end uses them;
	// the final ApplyState(To) then restores the level's own flag.
	R.bUseTemperature = A.bUseTemperature || B.bUseTemperature;
	R.bExposureOverridden = A.bExposureOverridden || B.bExposureOverridden;
	return R;
}

void AGolmokTimeOfDay::StartTransition(const FGolmokLightingState& InTo, bool bInstant)
{
	ResolveTargets();
	UWorld* World = GetWorld();
	To = InTo;
	const bool bImmediate = bInstant || TransitionSeconds <= 0.f || !World || !World->IsGameWorld();
	if (bImmediate)
	{
		bTransitioning = false;
		UpdateTickEnabled();
		ApplyState(To, /*bFinal*/ true);
		if (ClockMode != EGolmokClockMode::Fixed)
		{
			ApplyClockState(To);
		}
		return;
	}
	// From the currently applied (possibly mid-transition) values so a new request never jumps.
	From = Applied;
	TransitionStart = World->GetTimeSeconds();
	bTransitioning = true;
	// Cache-invalidating toggles happen once: switching on at the start (off happens at the end, in ApplyState).
	if (UDirectionalLightComponent* Component = Sun.Get())
	{
		if (To.Lux > 0.0)
		{
			Component->SetVisibility(true);
		}
	}
	if (UExponentialHeightFogComponent* Component = Fog.Get())
	{
		if (To.bVolumetric)
		{
			Component->SetVolumetricFog(true);
		}
	}
	SetActorTickEnabled(true);
}

float AGolmokTimeOfDay::GetTransitionAlpha() const
{
	if (!bTransitioning || TransitionSeconds <= 0.f)
	{
		return 1.f;
	}
	const UWorld* World = GetWorld();
	if (!World)
	{
		return 1.f;
	}
	const double Elapsed = World->GetTimeSeconds() - TransitionStart;
	return FMath::Clamp(static_cast<float>(Elapsed / TransitionSeconds), 0.f, 1.f);
}

void AGolmokTimeOfDay::ShiftTransitionStart(double DeltaSeconds)
{
	// GetTransitionAlpha() = (World->GetTimeSeconds() - TransitionStart) / TransitionSeconds: moving the start forward
	// by the world time that passed while photo mode held the game keeps the alpha where it was (WP-12 design 0 #4).
	if (!bTransitioning)
	{
		return;
	}
	TransitionStart += DeltaSeconds;
}

void AGolmokTimeOfDay::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	// WP-14a: the clock moves first (no-op in Fixed); while no transition runs it applies its state itself.
	AdvanceClock(static_cast<double>(DeltaSeconds));
	if (!bTransitioning)
	{
		UpdateTickEnabled();
		return;
	}
	// A jump on a running clock heads for where the clock is now, not where it was when the jump started.
	if (ClockMode != EGolmokClockMode::Fixed && bBaseFromClock)
	{
		To = ComposeTarget();
	}
	const float Alpha = GetTransitionAlpha();
	const bool bDone = Alpha >= 1.f;
	if (bDone)
	{
		ApplyState(To, /*bFinal*/ true);
		bTransitioning = false;
		if (ClockMode != EGolmokClockMode::Fixed)
		{
			ApplyClockState(To);
		}
		UpdateTickEnabled();
		return;
	}
	ApplyState(Lerp(From, To, Alpha), /*bFinal*/ false);
}

void AGolmokTimeOfDay::ApplyState(const FGolmokLightingState& S, bool bFinal)
{
	if (AActor* Actor = SunActor.Get())
	{
		Actor->SetActorRotation(S.SunRotation);
	}
	if (UDirectionalLightComponent* Component = Sun.Get())
	{
		Component->SetIntensity(static_cast<float>(S.Lux));
		// Level lighting that never used a colour temperature gets it back untouched (bUseTemperature false).
		Component->SetUseTemperature(S.bUseTemperature);
		if (S.bUseTemperature)
		{
			Component->SetTemperature(static_cast<float>(S.Kelvin));
		}
		if (bFinal)
		{
			Component->SetVisibility(S.Lux > 0.0);
		}
	}
	if (USkyLightComponent* Component = Sky.Get())
	{
		Component->SetIntensity(static_cast<float>(S.Sky));
		if (bFinal && !Component->bRealTimeCapture)
		{
			Component->RecaptureSky();
		}
	}
	if (UExponentialHeightFogComponent* Component = Fog.Get())
	{
		Component->SetFogDensity(static_cast<float>(S.Fog));
		Component->SetFogHeightFalloff(static_cast<float>(S.FogHeightFalloff));
		if (bFinal)
		{
			Component->SetVolumetricFog(S.bVolumetric);
		}
	}
	if (APostProcessVolume* Volume = PostProcess.Get())
	{
		// Only write the bias while it is overridden; back at the level's lighting the override is switched off
		// again so the engine default applies exactly as before the first preset / interior overlay.
		Volume->Settings.bOverride_AutoExposureBias = S.bExposureOverridden;
		if (S.bExposureOverridden)
		{
			Volume->Settings.AutoExposureBias = static_cast<float>(S.ExposureBias);
		}
	}
	Applied = S;
}

FString AGolmokTimeOfDay::Describe() const
{
	if (!bPresetsLoaded)
	{
		return TEXT("(no presets)");
	}
	FString Text;
	if (bTransitioning)
	{
		const int32 Percent = FMath::RoundToInt(GetTransitionAlpha() * 100.f);
		const FString FromName = FromPreset.IsNone() ? FString(TEXT("(level)")) : FromPreset.ToString();
		const FString ToName = TargetPreset.IsNone() ? FString(TEXT("(level)")) : TargetPreset.ToString();
		Text = FromName == ToName ? FString::Printf(TEXT("%s %d%%"), *ToName, Percent) : FString::Printf(TEXT("%s -> %s %d%%"), *FromName, *ToName, Percent);
	}
	else
	{
		Text = BaseName();
	}
	if (IsInterior())
	{
		FString Sources;
		for (const FName& Source : InteriorSources)
		{
			if (!Sources.IsEmpty())
			{
				Sources += TEXT(", ");
			}
			Sources += Source.ToString();
		}
		Text += FString::Printf(TEXT(" [interior: %s]"), *Sources);
	}
	return Text;
}

// ---- WP-14a clock -----------------------------------------------------------------------------------------------

// Named namespace (unity build: see GolmokLightingJson above).
namespace GolmokTimeOfDayClock
{
	GolmokClockMath::LightKey ToKey(const FGolmokLightingPreset& P)
	{
		GolmokClockMath::LightKey K;
		K.Pitch = P.PitchDeg;
		K.Yaw = P.YawDeg;
		K.Lux = P.Lux;
		K.Kelvin = P.Kelvin;
		K.Sky = P.Sky;
		K.Fog = P.Fog;
		K.FogHeightFalloff = P.FogHeightFalloff;
		K.ExposureBias = P.ExposureBias;
		K.bVolumetric = P.bVolumetric;
		return K;
	}

	/** Wrapped minutes as the float property (a double just under 1440 must not round up to 1440.f). */
	float ToStoredMinutes(double Minutes)
	{
		const float Stored = static_cast<float>(GolmokClockMath::WrapMinutes(Minutes));
		return Stored >= 1440.f ? 0.f : Stored;
	}
} // namespace GolmokTimeOfDayClock

const TCHAR* AGolmokTimeOfDay::ClockModeName(EGolmokClockMode Mode)
{
	switch (Mode)
	{
	case EGolmokClockMode::Clock:
		return TEXT("clock");
	case EGolmokClockMode::Realtime:
		return TEXT("realtime");
	default:
		return TEXT("fixed");
	}
}

bool AGolmokTimeOfDay::ParseClockMode(const FString& Text, EGolmokClockMode& Out)
{
	const EGolmokClockMode Modes[] = {EGolmokClockMode::Fixed, EGolmokClockMode::Clock, EGolmokClockMode::Realtime};
	for (const EGolmokClockMode Candidate : Modes)
	{
		if (Text.Equals(ClockModeName(Candidate), ESearchCase::IgnoreCase))
		{
			Out = Candidate;
			return true;
		}
	}
	return false;
}

bool AGolmokTimeOfDay::EvaluateClock(double Minutes, FGolmokLightingState& Out) const
{
	if (CycleTimes.Num() == 0 || CycleTimes.Num() != Cycle.Num())
	{
		return false;
	}
	const GolmokClockMath::KeyframeSpan Span = GolmokClockMath::FindKeyframes(Minutes, CycleTimes.GetData(), CycleTimes.Num());
	if (!Span.IsValid())
	{
		return false;
	}
	const FGolmokLightingPreset* A = GolmokLightingJson::FindByName(Presets, Cycle[Span.Prev]);
	const FGolmokLightingPreset* B = GolmokLightingJson::FindByName(Presets, Cycle[Span.Next]);
	if (!A || !B)
	{
		return false;
	}
	const GolmokClockMath::LightKey K = GolmokClockMath::Interpolate(GolmokTimeOfDayClock::ToKey(*A), GolmokTimeOfDayClock::ToKey(*B), Span.Alpha);
	// Same fields and flags as StateFromPreset() of a complete preset: at a keyframe time (alpha 0) the values are the preset's.
	Out = Initial;
	Out.SunRotation = FRotator(K.Pitch, K.Yaw, 0.0);
	Out.Lux = K.Lux;
	Out.bUseTemperature = true;
	Out.Kelvin = K.Kelvin;
	Out.Sky = K.Sky;
	Out.Fog = K.Fog;
	Out.FogHeightFalloff = K.FogHeightFalloff;
	Out.bVolumetric = K.bVolumetric;
	Out.bExposureOverridden = true;
	Out.ExposureBias = K.ExposureBias;
	return true;
}

FName AGolmokTimeOfDay::NearestKeyframe(double Minutes) const
{
	if (CycleTimes.Num() == 0 || CycleTimes.Num() != Cycle.Num())
	{
		return CurrentPreset;
	}
	const GolmokClockMath::KeyframeSpan Span = GolmokClockMath::FindKeyframes(Minutes, CycleTimes.GetData(), CycleTimes.Num());
	return Span.IsValid() ? Cycle[Span.Nearest()] : CurrentPreset;
}

double AGolmokTimeOfDay::RealtimeTargetMinutes() const
{
	// PC local time, no time-zone conversion (design section 4: the owner's PC is on KST).
	const FDateTime Now = FDateTime::Now();
	const double Minutes = Now.GetHour() * 60.0 + Now.GetMinute() + Now.GetSecond() / 60.0 + Now.GetMillisecond() / 60000.0;
	return GolmokClockMath::WrapMinutes(Minutes + static_cast<double>(RealtimeOffsetMinutes));
}

bool AGolmokTimeOfDay::SetTimeOfDay(float Minutes, bool bInstant)
{
	if (!EnsurePresets())
	{
		return false;
	}
	if (CycleTimes.Num() == 0 || !FMath::IsFinite(Minutes))
	{
		LastError = CycleTimes.Num() == 0 ? FString(TEXT("no keyframes")) : FString(TEXT("time is not a number"));
		return false;
	}
	TimeOfDayMinutes = GolmokTimeOfDayClock::ToStoredMinutes(static_cast<double>(Minutes));
	bBaseFromClock = true;
	const FName Nearest = NearestKeyframe(TimeOfDayMinutes);
	const bool bPresetChanged = Nearest != CurrentPreset;
	FromPreset = CurrentPreset;
	CurrentPreset = Nearest;
	TargetPreset = Nearest;
	StartTransition(ComposeTarget(), bInstant);
	if (bPresetChanged)
	{
		// Same (name, bInstant) meaning as ApplyPreset(): WP-13 maps the nearest keyframe name to day / night.
		OnPresetChanged.Broadcast(Nearest, bInstant);
	}
	RefreshNight(/*bBroadcast*/ true);
	return true;
}

bool AGolmokTimeOfDay::SetClockMode(EGolmokClockMode Mode)
{
	if (Mode != EGolmokClockMode::Fixed && (!EnsurePresets() || CycleTimes.Num() == 0))
	{
		LastError = TEXT("no keyframes (presets not loaded)");
		return false;
	}
	ClockMode = Mode;
	bRealtimeHeld = false;
	if (Mode == EGolmokClockMode::Realtime)
	{
		SetTimeOfDay(static_cast<float>(RealtimeTargetMinutes()), /*bInstant*/ false);
	}
	else if (Mode == EGolmokClockMode::Clock && !bBaseFromClock)
	{
		// From a preset (or the level's lighting) onto the clock at the current time.
		SetTimeOfDay(TimeOfDayMinutes, /*bInstant*/ false);
	}
	// Fixed: the clock stops where it is and the lighting stays what it is.
	UpdateTickEnabled();
	return true;
}

void AGolmokTimeOfDay::AdvanceClock(double DeltaSeconds)
{
	if (ClockMode == EGolmokClockMode::Fixed || !bPresetsLoaded || CycleTimes.Num() == 0)
	{
		return;
	}
	double Target = TimeOfDayMinutes;
	if (ClockMode == EGolmokClockMode::Clock)
	{
		// World delta: a paused world does not tick, photo mode's time dilation leaves it near 0.
		Target = GolmokClockMath::Advance(TimeOfDayMinutes, static_cast<double>(ClockMinutesPerRealSecond), DeltaSeconds);
	}
	else
	{
		if (IsPhotoModeActive())
		{
			// Photo mode keeps the entry time; the first tick after it re-syncs with a transition (design section 4).
			bRealtimeHeld = true;
			return;
		}
		Target = RealtimeTargetMinutes();
		if (bRealtimeHeld || GolmokClockMath::CircularDistance(TimeOfDayMinutes, Target) > GolmokClockMath::ResyncMinutes)
		{
			bRealtimeHeld = false;
			SetTimeOfDay(static_cast<float>(Target), /*bInstant*/ false);
			return;
		}
	}
	if (!bBaseFromClock)
	{
		SetTimeOfDay(static_cast<float>(Target), /*bInstant*/ false);
		return;
	}
	TimeOfDayMinutes = GolmokTimeOfDayClock::ToStoredMinutes(Target);
	const FName Nearest = NearestKeyframe(TimeOfDayMinutes);
	if (Nearest != CurrentPreset)
	{
		// The clock passed the midpoint between two keyframes: one notification per crossing (design section 5).
		CurrentPreset = Nearest;
		TargetPreset = Nearest;
		bRecapturePending = true;
		OnPresetChanged.Broadcast(Nearest, /*bInstant*/ false);
	}
	if (!bTransitioning)
	{
		ApplyClockState(ComposeTarget());
	}
	RefreshNight(/*bBroadcast*/ true);
}

void AGolmokTimeOfDay::ApplyClockState(const FGolmokLightingState& S)
{
	ApplyState(S, /*bFinal*/ false);
	// Per tick, not only at a transition end: the sun follows lux > 0.01 and volumetric fog the alpha 0.5 rule,
	// each switched only when it changes (both invalidate caches).
	if (UDirectionalLightComponent* Component = Sun.Get())
	{
		const bool bVisible = GolmokClockMath::IsSunVisible(S.Lux);
		if (Component->GetVisibleFlag() != bVisible)
		{
			Component->SetVisibility(bVisible);
		}
	}
	if (UExponentialHeightFogComponent* Component = Fog.Get())
	{
		if ((Component->bEnableVolumetricFog != 0) != S.bVolumetric)
		{
			Component->SetVolumetricFog(S.bVolumetric);
		}
	}
	if (bRecapturePending)
	{
		bRecapturePending = false;
		USkyLightComponent* Component = Sky.Get();
		if (Component && !Component->bRealTimeCapture)
		{
			Component->RecaptureSky();
		}
	}
}

void AGolmokTimeOfDay::RefreshNight(bool bBroadcast)
{
	const bool bNow = GolmokClockMath::IsNight(ComposeBase().Lux, static_cast<double>(NightLuxThreshold));
	if (bNow == bNight)
	{
		return;
	}
	bNight = bNow;
	if (bBroadcast)
	{
		OnNightChanged.Broadcast(bNight);
	}
}

void AGolmokTimeOfDay::UpdateTickEnabled()
{
	// Fixed: exactly the WP-05 rule (tick only while a transition runs).
	SetActorTickEnabled(bTransitioning || ClockMode != EGolmokClockMode::Fixed);
}

bool AGolmokTimeOfDay::IsPhotoModeActive() const
{
	return UGolmokPhotoModeSubsystem::IsActiveIn(GetWorld());
}

FString AGolmokTimeOfDay::DescribeClock() const
{
	if (!bPresetsLoaded)
	{
		return FString();
	}
	TCHAR Hhmm[6];
	GolmokClockMath::FormatHHMM(static_cast<double>(TimeOfDayMinutes), Hhmm);
	// The level's own lighting has no time of day.
	const FString TimeText = (CurrentPreset.IsNone() && !bBaseFromClock) ? FString(TEXT("--:--")) : FString(Hhmm);
	if (ClockMode == EGolmokClockMode::Clock)
	{
		return FString::Printf(TEXT(" %s clock x%g"), *TimeText, static_cast<double>(ClockMinutesPerRealSecond));
	}
	return FString::Printf(TEXT(" %s %s"), *TimeText, ClockModeName(ClockMode));
}

// ---- console --------------------------------------------------------------------------------------------------

// WP-14a subcommands; a named namespace so a unity build never merges them with another file's helpers.
namespace GolmokTimeOfDayConsole
{
	FString Hhmm(double Minutes)
	{
		TCHAR Text[6];
		GolmokClockMath::FormatHHMM(Minutes, Text);
		return FString(Text);
	}

	/** "status 12:30 fixed rate 0.5 min/s | prev clear_noon 12:30 next golden_evening 18:00 alpha 0.00 | current clear_noon | night no | interior off". */
	FString DescribeStatus(const AGolmokTimeOfDay& TimeOfDay)
	{
		const double Minutes = static_cast<double>(TimeOfDay.GetTimeOfDayMinutes());
		FString Line = FString::Printf(TEXT("status %s %s rate %g min/s"), *Hhmm(Minutes), AGolmokTimeOfDay::ClockModeName(TimeOfDay.GetClockMode()),
			static_cast<double>(TimeOfDay.ClockMinutesPerRealSecond));
		const TArray<FName>& Cycle = TimeOfDay.GetCycle();
		const TArray<double>& Times = TimeOfDay.GetCycleTimes();
		const GolmokClockMath::KeyframeSpan Span = GolmokClockMath::FindKeyframes(Minutes, Times.GetData(), Times.Num());
		if (Span.IsValid() && Times.Num() == Cycle.Num())
		{
			Line += FString::Printf(TEXT(" | prev %s %s next %s %s alpha %.2f"), *Cycle[Span.Prev].ToString(), *Hhmm(Times[Span.Prev]),
				*Cycle[Span.Next].ToString(), *Hhmm(Times[Span.Next]), Span.Alpha);
		}
		const FString Current = TimeOfDay.CurrentPreset.IsNone() ? FString(TEXT("(level)")) : TimeOfDay.CurrentPreset.ToString();
		Line += FString::Printf(TEXT(" | current %s | night %s | interior %s"), *Current, TimeOfDay.IsNight() ? TEXT("yes") : TEXT("no"),
			TimeOfDay.IsInterior() ? TEXT("on") : TEXT("off"));
		return Line;
	}

	void CmdTime(AGolmokTimeOfDay& TimeOfDay, const TArray<FString>& Args)
	{
		int Minutes = 0;
		if (Args.Num() < 2 || !GolmokClockMath::ParseHHMM(*Args[1], Minutes))
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.tod: ERROR time must be HH:MM (00:00-23:59), got '%s'"), Args.Num() < 2 ? TEXT("") : *Args[1]);
			return;
		}
		const FString Before = Hhmm(static_cast<double>(TimeOfDay.GetTimeOfDayMinutes()));
		if (!TimeOfDay.SetTimeOfDay(static_cast<float>(Minutes), /*bInstant*/ false))
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.tod: ERROR %s"), *TimeOfDay.LastError);
			return;
		}
		UE_LOG(LogGolmok, Log, TEXT("golmok.tod: time %s -> %s (%s) over %.1f s"), *Before, *Hhmm(static_cast<double>(Minutes)),
			*TimeOfDay.CurrentPreset.ToString(), TimeOfDay.TransitionSeconds);
	}

	void CmdMode(AGolmokTimeOfDay& TimeOfDay, const TArray<FString>& Args)
	{
		EGolmokClockMode Mode = EGolmokClockMode::Fixed;
		if (Args.Num() < 2 || !AGolmokTimeOfDay::ParseClockMode(Args[1], Mode))
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.tod: ERROR mode must be fixed|clock|realtime, got '%s'"), Args.Num() < 2 ? TEXT("") : *Args[1]);
			return;
		}
		const TCHAR* Before = AGolmokTimeOfDay::ClockModeName(TimeOfDay.GetClockMode());
		if (!TimeOfDay.SetClockMode(Mode))
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.tod: ERROR %s"), *TimeOfDay.LastError);
			return;
		}
		UE_LOG(LogGolmok, Log, TEXT("golmok.tod: mode %s -> %s at %s"), Before, AGolmokTimeOfDay::ClockModeName(Mode),
			*Hhmm(static_cast<double>(TimeOfDay.GetTimeOfDayMinutes())));
	}

	void CmdRate(AGolmokTimeOfDay& TimeOfDay, const TArray<FString>& Args)
	{
		const double Rate = Args.Num() < 2 || !Args[1].IsNumeric() ? -1.0 : FCString::Atod(*Args[1]);
		if (!GolmokClockMath::IsValidRate(Rate))
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.tod: ERROR rate must be a number in (0, 1440] min/s, got '%s'"), Args.Num() < 2 ? TEXT("") : *Args[1]);
			return;
		}
		const double Before = static_cast<double>(TimeOfDay.ClockMinutesPerRealSecond);
		TimeOfDay.ClockMinutesPerRealSecond = static_cast<float>(Rate);
		UE_LOG(LogGolmok, Log, TEXT("golmok.tod: rate %g -> %g min/s (mode %s)"), Before, Rate, AGolmokTimeOfDay::ClockModeName(TimeOfDay.GetClockMode()));
	}
} // namespace GolmokTimeOfDayConsole

namespace
{
	AGolmokTimeOfDay* TimeOfDayFor(UWorld* World)
	{
		AGolmokTimeOfDay* TimeOfDay = AGolmokTimeOfDay::FindOrSpawn(World);
		if (!TimeOfDay)
		{
			UE_LOG(LogGolmok, Warning, TEXT("golmok.tod: no AGolmokTimeOfDay in this world (spawned automatically in game / PIE only)."));
		}
		return TimeOfDay;
	}

	FString DescribeList(const AGolmokTimeOfDay& TimeOfDay)
	{
		FString Line = TEXT("presets:");
		for (const FName& Name : TimeOfDay.GetCycle())
		{
			Line += FString::Printf(TEXT(" %s%s"), *Name.ToString(), Name == TimeOfDay.CurrentPreset ? TEXT("*") : TEXT(""));
		}
		FString Overlays;
		for (const FName& Name : TimeOfDay.GetPresetNames())
		{
			if (TimeOfDay.GetCycle().Contains(Name))
			{
				continue;
			}
			if (!Overlays.IsEmpty())
			{
				Overlays += TEXT(" ");
			}
			Overlays += Name.ToString();
		}
		if (!Overlays.IsEmpty())
		{
			Line += FString::Printf(TEXT(" (overlay: %s)"), *Overlays);
		}
		FString Sources;
		for (const FName& Source : TimeOfDay.InteriorSources)
		{
			if (!Sources.IsEmpty())
			{
				Sources += TEXT(", ");
			}
			Sources += Source.ToString();
		}
		const FString Current = TimeOfDay.CurrentPreset.IsNone() ? FString(TEXT("(level)")) : TimeOfDay.CurrentPreset.ToString();
		const FString InteriorText = TimeOfDay.IsInterior() ? FString::Printf(TEXT("on (%s)"), *Sources) : FString(TEXT("off"));
		Line += FString::Printf(TEXT(" - current %s, interior %s"), *Current, *InteriorText);
		return Line;
	}

	void CmdTod(const TArray<FString>& Args, UWorld* World)
	{
		AGolmokTimeOfDay* TimeOfDay = TimeOfDayFor(World);
		if (!TimeOfDay)
		{
			return;
		}
		if (Args.Num() < 1)
		{
			UE_LOG(LogGolmok, Warning, TEXT("usage: golmok.tod <preset>|next|list|status|time HH:MM|mode fixed|clock|realtime|rate <min/s>"));
			return;
		}
		if (!TimeOfDay->EnsurePresets())
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.tod: ERROR %s"), *TimeOfDay->LastError);
			return;
		}
		const FString& Arg = Args[0];
		if (Arg == TEXT("list"))
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.tod: %s"), *DescribeList(*TimeOfDay));
			return;
		}
		// WP-14a clock subcommands (checked before preset names, like next / list).
		if (Arg == TEXT("status"))
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.tod: %s"), *GolmokTimeOfDayConsole::DescribeStatus(*TimeOfDay));
			return;
		}
		if (Arg == TEXT("time"))
		{
			GolmokTimeOfDayConsole::CmdTime(*TimeOfDay, Args);
			return;
		}
		if (Arg == TEXT("mode"))
		{
			GolmokTimeOfDayConsole::CmdMode(*TimeOfDay, Args);
			return;
		}
		if (Arg == TEXT("rate"))
		{
			GolmokTimeOfDayConsole::CmdRate(*TimeOfDay, Args);
			return;
		}
		const FString Before = TimeOfDay->CurrentPreset.IsNone() ? FString(TEXT("(level)")) : TimeOfDay->CurrentPreset.ToString();
		const bool bOk = Arg == TEXT("next") ? TimeOfDay->NextPreset() : TimeOfDay->ApplyPreset(FName(*Arg));
		if (!bOk)
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.tod: ERROR unknown preset '%s'"), *Arg);
			return;
		}
		UE_LOG(LogGolmok, Log, TEXT("golmok.tod: %s -> %s over %.1f s"), *Before, *TimeOfDay->CurrentPreset.ToString(), TimeOfDay->TransitionSeconds);
	}

	FAutoConsoleCommandWithWorldAndArgs GCmdTod(TEXT("golmok.tod"),
		TEXT("golmok.tod <preset>|next|list|status|time HH:MM|mode fixed|clock|realtime|rate <min/s>: change the lighting preset (transition over TransitionSeconds), list presets, or drive the clock (WP-14a)."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdTod));
} // namespace
