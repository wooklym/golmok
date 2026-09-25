#include "Photo/GolmokPhotoModeSubsystem.h"

#include "Golmok.h"

#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "CollisionQueryParams.h"
#include "CollisionShape.h"
#include "Debug/GolmokDebugSubsystem.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/Pawn.h"
#include "Geo/GolmokGeoSubsystem.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformTime.h"
#include "InputAction.h"
#include "InputActionValue.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "Kismet/GameplayStatics.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Misc/CoreDelegates.h"
#include "Misc/DateTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Photo/GolmokPhotoCameraPawn.h"
#include "Player/GolmokPlayerController.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Zones/GolmokZone.h"
#include "Zones/GolmokZoneSubsystem.h"

// ---- photo.json ---------------------------------------------------------------------------------------------

// Named (not anonymous) so a unity build never sees two bodies for the same helper (GolmokLightingJson precedent).
// Keys are passed as FString objects: UE 5.8 keys FJsonObject::Values by UE::FSharedString, so lookups go through
// TryGetField(FStringView) and key enumeration through FString(*Pair.Key).
namespace GolmokPhotoJson
{
	using FJsonObjectPtr = TSharedPtr<FJsonObject>;
	using FJsonArray = TArray<TSharedPtr<FJsonValue>>;

	constexpr int32 SchemaVersion = 1;
	constexpr int32 ParamCount = 5;
	constexpr int32 MaxHintLines = 4;
	constexpr int32 MaxHintChars = 72;

	/** photo.json "params" keys in EGolmokPhotoParam order (the file order must match; also the overlay order). */
	const TCHAR* const ParamKeys[ParamCount] = {TEXT("fov"), TEXT("ev"), TEXT("focus"), TEXT("fstop"), TEXT("roll")};

	bool PhotoFail(FString& OutError, const FString& InWhere, const FString& InWhy)
	{
		OutError = FString::Printf(TEXT("photo.json: %s: %s"), *InWhere, *InWhy);
		return false;
	}

	/** Present-and-typed number lookup (EJson::Number only: a JSON bool / string is not a number, like Python). */
	bool PhotoReadNumber(const FJsonObjectPtr& InObj, const FString& InKey, bool& bOutPresent, double& OutValue)
	{
		OutValue = 0.0;
		const TSharedPtr<FJsonValue> Found = InObj->TryGetField(InKey);
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

	bool PhotoReadString(const FJsonObjectPtr& InObj, const FString& InKey, bool& bOutPresent, FString& OutValue)
	{
		OutValue.Reset();
		const TSharedPtr<FJsonValue> Found = InObj->TryGetField(InKey);
		bOutPresent = Found.IsValid();
		if (!bOutPresent)
		{
			return true;
		}
		if (Found->Type != EJson::String)
		{
			return false;
		}
		OutValue = Found->AsString();
		return true;
	}

	bool PhotoReadBool(const FJsonObjectPtr& InObj, const FString& InKey, bool& bOutPresent, bool& bOutValue)
	{
		bOutValue = false;
		const TSharedPtr<FJsonValue> Found = InObj->TryGetField(InKey);
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

	/** Object field; null pointer when missing or not an object. */
	FJsonObjectPtr PhotoObjectOf(const FJsonObjectPtr& InObj, const FString& InKey)
	{
		const TSharedPtr<FJsonValue> Found = InObj->TryGetField(InKey);
		const FJsonObjectPtr* Ptr = nullptr;
		if (Found.IsValid() && Found->TryGetObject(Ptr) && Ptr && Ptr->IsValid())
		{
			return *Ptr;
		}
		return FJsonObjectPtr();
	}

	/** Every key of InObj must be one of InAllowed. */
	bool PhotoCheckKeys(const FJsonObjectPtr& InObj, const TArray<FString>& InAllowed, const FString& InWhere, FString& OutError)
	{
		for (const auto& Pair : InObj->Values)
		{
			const FString Key(*Pair.Key); // UE::FSharedString key -> FString
			if (!InAllowed.Contains(Key))
			{
				return PhotoFail(OutError, InWhere, FString::Printf(TEXT("unknown key '%s'"), *Key));
			}
		}
		return true;
	}

	bool PhotoParseParam(const FJsonObjectPtr& InObj, const FString& InWhere, FGolmokPhotoParamSpec& Out, FString& OutError)
	{
		if (!InObj.IsValid())
		{
			return PhotoFail(OutError, InWhere, TEXT("must be an object"));
		}
		const FString KeyLabel(TEXT("label"));
		const FString KeyUnit(TEXT("unit"));
		const FString KeyDefault(TEXT("default"));
		const FString KeyMin(TEXT("min"));
		const FString KeyMax(TEXT("max"));
		const FString KeyStep(TEXT("step"));
		const FString KeyStepRatio(TEXT("step_ratio"));
		const FString KeyValues(TEXT("values"));
		if (!PhotoCheckKeys(InObj, {KeyLabel, KeyUnit, KeyDefault, KeyMin, KeyMax, KeyStep, KeyStepRatio, KeyValues}, InWhere, OutError))
		{
			return false;
		}

		Out = FGolmokPhotoParamSpec();
		bool bPresent = false;
		if (!PhotoReadString(InObj, KeyLabel, bPresent, Out.Label) || !bPresent)
		{
			return PhotoFail(OutError, InWhere + TEXT(".label"), TEXT("must be a string"));
		}
		if (!PhotoReadString(InObj, KeyUnit, bPresent, Out.Unit) || !bPresent)
		{
			return PhotoFail(OutError, InWhere + TEXT(".unit"), TEXT("must be a string (empty allowed)"));
		}
		if (!PhotoReadNumber(InObj, KeyDefault, bPresent, Out.Default) || !bPresent)
		{
			return PhotoFail(OutError, InWhere + TEXT(".default"), TEXT("must be a number"));
		}

		bool bHasMin = false;
		bool bHasMax = false;
		bool bHasStep = false;
		bool bHasRatio = false;
		if (!PhotoReadNumber(InObj, KeyMin, bHasMin, Out.Min))
		{
			return PhotoFail(OutError, InWhere + TEXT(".min"), TEXT("must be a number"));
		}
		if (!PhotoReadNumber(InObj, KeyMax, bHasMax, Out.Max))
		{
			return PhotoFail(OutError, InWhere + TEXT(".max"), TEXT("must be a number"));
		}
		if (!PhotoReadNumber(InObj, KeyStep, bHasStep, Out.Step))
		{
			return PhotoFail(OutError, InWhere + TEXT(".step"), TEXT("must be a number"));
		}
		if (!PhotoReadNumber(InObj, KeyStepRatio, bHasRatio, Out.StepRatio))
		{
			return PhotoFail(OutError, InWhere + TEXT(".step_ratio"), TEXT("must be a number"));
		}
		const TSharedPtr<FJsonValue> ValuesField = InObj->TryGetField(KeyValues);
		const bool bHasValues = ValuesField.IsValid();

		if (bHasValues)
		{
			// Table parameter: {values} only.
			if (bHasMin || bHasMax || bHasStep || bHasRatio)
			{
				return PhotoFail(OutError, InWhere, TEXT("values excludes min / max / step / step_ratio"));
			}
			const FJsonArray* Arr = nullptr;
			if (ValuesField->Type != EJson::Array || !ValuesField->TryGetArray(Arr) || !Arr)
			{
				return PhotoFail(OutError, InWhere + TEXT(".values"), TEXT("must be an array of numbers"));
			}
			for (const TSharedPtr<FJsonValue>& V : *Arr)
			{
				if (!V.IsValid() || V->Type != EJson::Number)
				{
					return PhotoFail(OutError, InWhere + TEXT(".values"), TEXT("entries must be numbers"));
				}
				const double Number = V->AsNumber();
				if (!(Number > 0.0))
				{
					return PhotoFail(OutError, InWhere + TEXT(".values"), TEXT("entries must be positive"));
				}
				if (Out.Values.Num() > 0 && !(Number > Out.Values.Last()))
				{
					return PhotoFail(OutError, InWhere + TEXT(".values"), TEXT("must be strictly ascending"));
				}
				Out.Values.Add(Number);
			}
			if (Out.Values.Num() < 2)
			{
				return PhotoFail(OutError, InWhere + TEXT(".values"), TEXT("needs at least 2 entries"));
			}
			if (!Out.Values.Contains(Out.Default))
			{
				return PhotoFail(OutError, InWhere + TEXT(".default"), TEXT("must be one of values"));
			}
			// Table parameters have no range; Min / Max mirror the ends for callers that clamp.
			Out.Min = Out.Values[0];
			Out.Max = Out.Values.Last();
			return true;
		}

		// Range parameter: {min, max} + exactly one of step / step_ratio.
		if (!bHasMin || !bHasMax)
		{
			return PhotoFail(OutError, InWhere, TEXT("needs min and max (or values)"));
		}
		if (bHasStep == bHasRatio)
		{
			return PhotoFail(OutError, InWhere, TEXT("needs exactly one of step / step_ratio"));
		}
		if (!(Out.Min < Out.Max))
		{
			return PhotoFail(OutError, InWhere, TEXT("min must be < max"));
		}
		if (Out.Default < Out.Min || Out.Default > Out.Max)
		{
			return PhotoFail(OutError, InWhere + TEXT(".default"), TEXT("must be within [min, max]"));
		}
		if (bHasStep && !(Out.Step > 0.0))
		{
			return PhotoFail(OutError, InWhere + TEXT(".step"), TEXT("must be > 0"));
		}
		if (bHasRatio)
		{
			if (!(Out.StepRatio > 1.0))
			{
				return PhotoFail(OutError, InWhere + TEXT(".step_ratio"), TEXT("must be > 1"));
			}
			if (!(Out.Min > 0.0))
			{
				return PhotoFail(OutError, InWhere + TEXT(".min"), TEXT("must be > 0 for a geometric parameter"));
			}
		}
		return true;
	}

	bool PhotoParseHints(const FJsonObjectPtr& InHints, const FString& InKey, TArray<FString>& Out, FString& OutError)
	{
		const FString Where = FString::Printf(TEXT("hints.%s"), *InKey);
		Out.Reset();
		const TSharedPtr<FJsonValue> Field = InHints->TryGetField(InKey);
		const FJsonArray* Arr = nullptr;
		if (!Field.IsValid() || Field->Type != EJson::Array || !Field->TryGetArray(Arr) || !Arr)
		{
			return PhotoFail(OutError, Where, TEXT("must be an array of strings"));
		}
		if (Arr->Num() < 1 || Arr->Num() > MaxHintLines)
		{
			return PhotoFail(OutError, Where, FString::Printf(TEXT("needs 1..%d lines (got %d)"), MaxHintLines, Arr->Num()));
		}
		for (const TSharedPtr<FJsonValue>& V : *Arr)
		{
			if (!V.IsValid() || V->Type != EJson::String)
			{
				return PhotoFail(OutError, Where, TEXT("lines must be strings"));
			}
			const FString Line = V->AsString();
			if (Line.Len() > MaxHintChars)
			{
				return PhotoFail(OutError, Where, FString::Printf(TEXT("line longer than %d characters"), MaxHintChars));
			}
			Out.Add(Line);
		}
		return true;
	}

	bool ParseConfigText(const FString& InJson, FGolmokPhotoConfig& Out, FString& OutError)
	{
		Out = FGolmokPhotoConfig();
		OutError.Reset();

		FJsonObjectPtr Root;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(InJson);
		if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
		{
			return PhotoFail(OutError, TEXT("root"), FString::Printf(TEXT("invalid JSON: %s"), *Reader->GetErrorMessage()));
		}

		const FString KeySchemaVersion(TEXT("schema_version"));
		const FString KeyParams(TEXT("params"));
		const FString KeyToggles(TEXT("toggles"));
		const FString KeyHints(TEXT("hints"));
		const FString WhereRoot(TEXT("root"));
		if (!PhotoCheckKeys(Root, {KeySchemaVersion, KeyParams, KeyToggles, KeyHints}, WhereRoot, OutError))
		{
			return false;
		}

		double Version = 0.0;
		bool bHasVersion = false;
		if (!PhotoReadNumber(Root, KeySchemaVersion, bHasVersion, Version) || !bHasVersion || Version != static_cast<double>(SchemaVersion))
		{
			return PhotoFail(OutError, KeySchemaVersion, FString::Printf(TEXT("must be %d (got %g)"), SchemaVersion, Version));
		}

		// params: exactly fov ev focus fstop roll, in that order (TMap keeps insertion order without removals).
		const FJsonObjectPtr Params = PhotoObjectOf(Root, KeyParams);
		if (!Params.IsValid())
		{
			return PhotoFail(OutError, KeyParams, TEXT("must be an object"));
		}
		if (Params->Values.Num() != ParamCount)
		{
			return PhotoFail(OutError, KeyParams, FString::Printf(TEXT("needs exactly %d entries fov ev focus fstop roll (got %d)"), ParamCount, Params->Values.Num()));
		}
		int32 Index = 0;
		for (const auto& Pair : Params->Values)
		{
			const FString Key(*Pair.Key); // UE::FSharedString key -> FString
			if (Key != ParamKeys[Index])
			{
				return PhotoFail(OutError, KeyParams, FString::Printf(TEXT("expected '%s' at position %d (got '%s')"), ParamKeys[Index], Index, *Key));
			}
			const FJsonObjectPtr* EntryPtr = nullptr;
			FJsonObjectPtr Entry;
			if (Pair.Value.IsValid() && Pair.Value->TryGetObject(EntryPtr) && EntryPtr)
			{
				Entry = *EntryPtr;
			}
			if (!PhotoParseParam(Entry, FString::Printf(TEXT("params.%s"), ParamKeys[Index]), Out.Params[Index], OutError))
			{
				return false;
			}
			++Index;
		}

		// toggles: exactly three booleans.
		const FJsonObjectPtr Toggles = PhotoObjectOf(Root, KeyToggles);
		if (!Toggles.IsValid())
		{
			return PhotoFail(OutError, KeyToggles, TEXT("must be an object"));
		}
		const FString KeyDof(TEXT("dof"));
		const FString KeyCharacterHidden(TEXT("character_hidden"));
		const FString KeyOverlayHidden(TEXT("overlay_hidden"));
		if (!PhotoCheckKeys(Toggles, {KeyDof, KeyCharacterHidden, KeyOverlayHidden}, KeyToggles, OutError))
		{
			return false;
		}
		bool bPresent = false;
		if (!PhotoReadBool(Toggles, KeyDof, bPresent, Out.bDofDefault) || !bPresent)
		{
			return PhotoFail(OutError, TEXT("toggles.dof"), TEXT("must be a boolean"));
		}
		if (!PhotoReadBool(Toggles, KeyCharacterHidden, bPresent, Out.bCharacterHiddenDefault) || !bPresent)
		{
			return PhotoFail(OutError, TEXT("toggles.character_hidden"), TEXT("must be a boolean"));
		}
		if (!PhotoReadBool(Toggles, KeyOverlayHidden, bPresent, Out.bOverlayHiddenDefault) || !bPresent)
		{
			return PhotoFail(OutError, TEXT("toggles.overlay_hidden"), TEXT("must be a boolean"));
		}

		// hints: keyboard / gamepad, 1..4 lines of at most 72 characters.
		const FJsonObjectPtr Hints = PhotoObjectOf(Root, KeyHints);
		if (!Hints.IsValid())
		{
			return PhotoFail(OutError, KeyHints, TEXT("must be an object"));
		}
		const FString KeyKeyboard(TEXT("keyboard"));
		const FString KeyGamepad(TEXT("gamepad"));
		if (!PhotoCheckKeys(Hints, {KeyKeyboard, KeyGamepad}, KeyHints, OutError))
		{
			return false;
		}
		if (!PhotoParseHints(Hints, KeyKeyboard, Out.HintsKeyboard, OutError) || !PhotoParseHints(Hints, KeyGamepad, Out.HintsGamepad, OutError))
		{
			return false;
		}
		return true;
	}

	bool LoadConfigFile(const FString& InFilePath, FGolmokPhotoConfig& Out, FString& OutError)
	{
		FString Text;
		if (!FFileHelper::LoadFileToString(Text, *InFilePath))
		{
			Out = FGolmokPhotoConfig();
			return PhotoFail(OutError, TEXT("file"), FString::Printf(TEXT("cannot read %s"), *InFilePath));
		}
		return ParseConfigText(Text, Out, OutError);
	}
} // namespace GolmokPhotoJson

// ---- file-local helpers ------------------------------------------------------------------------------------

namespace
{
	/** Index of each action in UGolmokPhotoModeSubsystem::Actions (creation order of EnsureInputAssets). */
	enum class EPhotoActionSlot : int32
	{
		Shoot,
		Reset,
		Dof,
		HideCharacter,
		HideOverlay,
		FovUp,
		FovDown,
		FovWheel,
		EvUp,
		EvDown,
		FocusUp,
		FocusDown,
		FstopUp,
		FstopDown,
		RollUp,
		RollDown,
		Move,
		UpDown,
		Look,
		LookPad,
		Fast,
		Count
	};

	/** The "saved <stem>.png (2x)" overlay line stays this long after the capture window closes. */
	constexpr double PhotoSavedMessageSeconds = 2.5;
	/** Overlay lines are rebuilt at most this often (real time; the world clock is paused). */
	constexpr double PhotoOverlayRefreshSeconds = 0.25;
	/** Entry overlap check: retreat toward the anchor by this much, at most PhotoEntryRetreatSteps times. */
	constexpr float PhotoEntryRetreatCm = 30.f;
	constexpr int32 PhotoEntryRetreatSteps = 10;
	/** TimeDilation pause mode: the world runs at this speed (AWorldSettings::MinGlobalTimeDilation default). */
	constexpr float PhotoDilationNearZero = 0.0001f;

	std::string PhotoToUtf8(const FString& S)
	{
		// TCHAR_TO_UTF8 yields const ANSICHAR* (UTF8CHAR is char8_t under C++20, so the macro's cast is needed).
		return std::string(TCHAR_TO_UTF8(*S));
	}

	FString PhotoFromUtf8(const std::string& S)
	{
		return FString(UTF8_TO_TCHAR(S.c_str()));
	}

	std::vector<double> PhotoToStdVector(const TArray<double>& In)
	{
		std::vector<double> Out;
		Out.reserve(static_cast<std::size_t>(In.Num()));
		for (const double V : In)
		{
			Out.push_back(V);
		}
		return Out;
	}

	/** Display form of one parameter value (overlay, Describe, console): fov 65.0 | ev +0.33 | focus 3.000 | f/2.80 | roll +0.0. */
	FString PhotoFormatValue(EGolmokPhotoParam P, double V)
	{
		switch (P)
		{
		case EGolmokPhotoParam::Fov:
			return FString::Printf(TEXT("%.1f"), V);
		case EGolmokPhotoParam::Ev:
			return FString::Printf(TEXT("%+.2f"), V);
		case EGolmokPhotoParam::Focus:
			return FString::Printf(TEXT("%.3f"), V);
		case EGolmokPhotoParam::Fstop:
			return FString::Printf(TEXT("%.2f"), V);
		case EGolmokPhotoParam::Roll:
		default:
			return FString::Printf(TEXT("%+.1f"), V);
		}
	}
} // namespace

// ---- lifecycle ----------------------------------------------------------------------------------------------

bool UGolmokPhotoModeSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	// Runtime feature only (same reason as UGolmokDebugSubsystem).
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UGolmokPhotoModeSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	// Section 7 ranges (the ClampMin / ClampMax meta only guards the editor). No range literal of photo.json here.
	constexpr int32 MaxMultiplierBound = 8;
	constexpr int32 MaxCollisionRadiusCm = 50;
	ScreenshotMultiplier = FMath::Clamp(ScreenshotMultiplier, 1, MaxMultiplierBound);
	MaxMultiplier = FMath::Clamp(MaxMultiplier, 1, MaxMultiplierBound);
	MaxDistanceM = FMath::Clamp(MaxDistanceM, 0.5f, 20.f);
	CollisionRadiusCm = FMath::Clamp(CollisionRadiusCm, 5.f, static_cast<float>(MaxCollisionRadiusCm));
	FootprintMarginM = FMath::Max(0.f, FootprintMarginM);
	MoveSpeedMps = FMath::Max(0.1f, MoveSpeedMps);
	PreCaptureFrames = FMath::Clamp(PreCaptureFrames, 0, 60);
	PostCaptureFrames = FMath::Clamp(PostCaptureFrames, 1, 10);
}

void UGolmokPhotoModeSubsystem::Deinitialize()
{
	// The world is going away: no PC / pause / view target calls, only our own references (section 4-3).
	if (State != EGolmokPhotoState::Inactive)
	{
		TeardownForDeadWorld();
	}
	if (EndFrameHandle.IsValid())
	{
		FCoreDelegates::OnEndFrame.Remove(EndFrameHandle);
		EndFrameHandle.Reset();
	}
	Super::Deinitialize();
}

UGolmokPhotoModeSubsystem* UGolmokPhotoModeSubsystem::Get(UWorld* World)
{
	return World ? World->GetSubsystem<UGolmokPhotoModeSubsystem>() : nullptr;
}

bool UGolmokPhotoModeSubsystem::IsActiveIn(UWorld* World)
{
	const UGolmokPhotoModeSubsystem* Photo = Get(World);
	return Photo && Photo->IsActive();
}

UGolmokDebugSubsystem* UGolmokPhotoModeSubsystem::GetDebug() const
{
	UWorld* World = GetWorld();
	return World ? World->GetSubsystem<UGolmokDebugSubsystem>() : nullptr;
}

AGolmokTimeOfDay* UGolmokPhotoModeSubsystem::GetTimeOfDay() const
{
	return AGolmokTimeOfDay::Find(GetWorld());
}

AGolmokPlayerController* UGolmokPhotoModeSubsystem::GetPC() const
{
	UWorld* World = GetWorld();
	if (!World || World->bIsTearingDown)
	{
		return nullptr;
	}
	return Cast<AGolmokPlayerController>(UGameplayStatics::GetPlayerController(World, 0));
}

AGolmokPhotoCameraPawn* UGolmokPhotoModeSubsystem::GetPhotoPawn() const
{
	return PhotoPawn.Get();
}

int32 UGolmokPhotoModeSubsystem::GetPawnTickCount() const
{
	return PhotoPawn.IsValid() ? PhotoPawn->GetTickCount() : 0;
}

// ---- config ---------------------------------------------------------------------------------------------------

FString UGolmokPhotoModeSubsystem::ResolveConfigPath() const
{
	if (FPaths::IsRelative(ConfigFile))
	{
		return FPaths::Combine(FPaths::ProjectConfigDir(), ConfigFile);
	}
	return ConfigFile;
}

bool UGolmokPhotoModeSubsystem::EnsureConfig()
{
	if (bConfigLoaded)
	{
		return true;
	}
	if (bConfigFailed)
	{
		return false;
	}
	const FString Path = ResolveConfigPath();
	FString Error;
	if (!GolmokPhotoJson::LoadConfigFile(Path, Config, Error))
	{
		bConfigFailed = true;
		LastError = Error;
		UE_LOG(LogGolmok, Error, TEXT("photo: config not loaded from %s: %s"), *Path, *Error);
		return false;
	}
	bConfigLoaded = true;
	// First successful load: the session values start at the file's defaults (section 4-2 step 1).
	for (int32 i = 0; i < 5; ++i)
	{
		Values[i] = Config.Params[i].Default;
	}
	bDof = Config.bDofDefault;
	bCharacterHidden = Config.bCharacterHiddenDefault;
	bOverlayHidden = Config.bOverlayHiddenDefault;
	UE_LOG(LogGolmok, Log, TEXT("photo: config loaded (5 params) from %s"), *Path);
	return true;
}

// ---- parameters -----------------------------------------------------------------------------------------------

const TCHAR* UGolmokPhotoModeSubsystem::ParamName(EGolmokPhotoParam P)
{
	switch (P)
	{
	case EGolmokPhotoParam::Fov:
		return TEXT("fov");
	case EGolmokPhotoParam::Ev:
		return TEXT("ev");
	case EGolmokPhotoParam::Focus:
		return TEXT("focus");
	case EGolmokPhotoParam::Fstop:
		return TEXT("fstop");
	case EGolmokPhotoParam::Roll:
	default:
		return TEXT("roll");
	}
}

bool UGolmokPhotoModeSubsystem::ParseParamName(const FString& InName, EGolmokPhotoParam& Out)
{
	const FString Lower = InName.ToLower();
	const EGolmokPhotoParam All[5] = {EGolmokPhotoParam::Fov, EGolmokPhotoParam::Ev, EGolmokPhotoParam::Focus, EGolmokPhotoParam::Fstop, EGolmokPhotoParam::Roll};
	for (const EGolmokPhotoParam P : All)
	{
		if (Lower == ParamName(P))
		{
			Out = P;
			return true;
		}
	}
	return false;
}

double UGolmokPhotoModeSubsystem::GetParam(EGolmokPhotoParam P) const
{
	return Values[static_cast<int32>(P)];
}

void UGolmokPhotoModeSubsystem::StepParam(EGolmokPhotoParam P, int32 Dir)
{
	// Keys are silent during the capture window and outside photo mode (section 4-1).
	if (State != EGolmokPhotoState::Active || !bConfigLoaded)
	{
		return;
	}
	const FGolmokPhotoParamSpec& Spec = Config.Spec(P);
	const int32 Index = static_cast<int32>(P);
	const double Current = Values[Index];
	double Next = Current;
	if (Spec.IsTable())
	{
		Next = GolmokPhotoMath::StepTable(PhotoToStdVector(Spec.Values), Current, Dir);
	}
	else if (Spec.IsGeometric())
	{
		Next = GolmokPhotoMath::StepGeometric(Current, Spec.Min, Spec.Max, Spec.StepRatio, Dir);
	}
	else
	{
		Next = GolmokPhotoMath::StepLinear(Current, Spec.Min, Spec.Max, Spec.Step, Dir);
	}
	Values[Index] = Next;
	ApplyToPawn();
}

bool UGolmokPhotoModeSubsystem::SetParam(EGolmokPhotoParam P, double Value, FString& OutMessage)
{
	if (State == EGolmokPhotoState::Inactive)
	{
		OutMessage = TEXT("not active");
		return false;
	}
	if (IsCapturing())
	{
		OutMessage = TEXT("capture in progress");
		return false;
	}
	if (!bConfigLoaded)
	{
		OutMessage = TEXT("photo.json not loaded");
		return false;
	}
	const FGolmokPhotoParamSpec& Spec = Config.Spec(P);
	const int32 Index = static_cast<int32>(P);
	double Next = Value;
	if (Spec.IsTable())
	{
		const std::vector<double> Table = PhotoToStdVector(Spec.Values);
		Next = Table[GolmokPhotoMath::NearestIndex(Table, Value)];
	}
	else if (Spec.IsGeometric())
	{
		// Dir 0: clamp + 3-decimal rounding only.
		Next = GolmokPhotoMath::StepGeometric(Value, Spec.Min, Spec.Max, Spec.StepRatio, 0);
	}
	else
	{
		Next = GolmokPhotoMath::Quantize(Value, Spec.Min, Spec.Max, Spec.Step);
	}
	Values[Index] = Next;
	ApplyToPawn();
	OutMessage = FString::Printf(TEXT("%s %s"), ParamName(P), *PhotoFormatValue(P, Next));
	return true;
}

void UGolmokPhotoModeSubsystem::SetDofEnabled(bool bOn)
{
	bDof = bOn;
	ApplyToPawn();
}

void UGolmokPhotoModeSubsystem::SetCharacterHidden(bool bHidden)
{
	bCharacterHidden = bHidden;
	ApplyToPawn();
}

void UGolmokPhotoModeSubsystem::SetOverlayHidden(bool bHidden)
{
	bOverlayHidden = bHidden;
	bOverlayDirty = true;
}

bool UGolmokPhotoModeSubsystem::SetMultiplier(int32 InMultiplier, FString& OutMessage)
{
	if (InMultiplier < 1 || InMultiplier > MaxMultiplier)
	{
		OutMessage = FString::Printf(TEXT("multiplier must be 1..%d (MaxMultiplier)"), MaxMultiplier);
		return false;
	}
	SessionMultiplier = InMultiplier;
	bOverlayDirty = true;
	OutMessage = FString::Printf(TEXT("mult %d"), InMultiplier);
	return true;
}

void UGolmokPhotoModeSubsystem::ApplyToPawn()
{
	if (PhotoPawn.IsValid())
	{
		PhotoPawn->ApplyOptics(static_cast<float>(Values[static_cast<int32>(EGolmokPhotoParam::Fov)]),
			BaseExposureBias() + Values[static_cast<int32>(EGolmokPhotoParam::Ev)], bDof, Values[static_cast<int32>(EGolmokPhotoParam::Focus)],
			Values[static_cast<int32>(EGolmokPhotoParam::Fstop)]);
		PhotoPawn->SetRoll(static_cast<float>(Values[static_cast<int32>(EGolmokPhotoParam::Roll)]));
	}
	if (SavedPawn.IsValid())
	{
		// Collision stays (SetActorHiddenInGame only); a pawn hidden before Enter stays hidden.
		SavedPawn->SetActorHiddenInGame(bSavedPawnHidden || bCharacterHidden);
	}
	bOverlayDirty = true;
}

double UGolmokPhotoModeSubsystem::BaseExposureBias() const
{
	// The camera override REPLACES the volume's bias (section 10 #9): add the preset's base back.
	const AGolmokTimeOfDay* Tod = GetTimeOfDay();
	FGolmokLightingState Current;
	if (Tod && Tod->CaptureState(Current))
	{
		return Current.ExposureBias;
	}
	return AGolmokTimeOfDay::DefaultAutoExposureBias();
}

// ---- footprint / anchor -----------------------------------------------------------------------------------------

FVector UGolmokPhotoModeSubsystem::GetAnchor() const
{
	if (SavedPawn.IsValid())
	{
		return SavedPawn->GetActorLocation();
	}
	return EnterLocation;
}

void UGolmokPhotoModeSubsystem::CacheFootprint()
{
	FootprintXs.Reset();
	FootprintYs.Reset();
	FootprintZoneId.Reset();
	FootprintZoneVersion = 0;
	UWorld* World = GetWorld();
	UGolmokZoneSubsystem* Zones = World ? World->GetSubsystem<UGolmokZoneSubsystem>() : nullptr;
	if (!Zones)
	{
		return;
	}
	const FVector Anchor = GetAnchor();
	AGolmokZone* Zone = Zones->FindLoadedZoneAt(FVector2D(Anchor.X, Anchor.Y));
	if (!IsValid(Zone))
	{
		return;
	}
	FootprintZoneId = Zone->ZoneId;
	FootprintZoneVersion = Zone->Version;
	const TArray<FVector2D>& Ring = Zone->GetFootprintUE();
	if (Ring.Num() < 3)
	{
		return;
	}
	FootprintXs.Reserve(Ring.Num());
	FootprintYs.Reserve(Ring.Num());
	for (const FVector2D& P : Ring)
	{
		FootprintXs.Add(P.X);
		FootprintYs.Add(P.Y);
	}
	bOverlayDirty = true;
}

void UGolmokPhotoModeSubsystem::SetFootprintForTest(const TArray<FVector2D>& LevelUEPolygonCm)
{
	FootprintXs.Reset();
	FootprintYs.Reset();
	for (const FVector2D& P : LevelUEPolygonCm)
	{
		FootprintXs.Add(P.X);
		FootprintYs.Add(P.Y);
	}
	bOverlayDirty = true;
}

// ---- state machine: enter -----------------------------------------------------------------------------------------

bool UGolmokPhotoModeSubsystem::Enter(FString& OutMessage)
{
	UWorld* World = GetWorld();
	if (!World || World->bIsTearingDown || !(World->WorldType == EWorldType::Game || World->WorldType == EWorldType::PIE))
	{
		OutMessage = TEXT("cannot enter: not in a game world");
		return false;
	}
	if (State != EGolmokPhotoState::Inactive)
	{
		OutMessage = TEXT("cannot enter: already active");
		return false;
	}
	UGolmokDebugSubsystem* Debug = GetDebug();
	if (Debug && Debug->IsPlaying())
	{
		OutMessage = TEXT("cannot enter while a path is playing (golmok.path stopplay first)");
		return false;
	}
	if (Debug && Debug->IsRecording())
	{
		// "rec <name> 12.3 s 123 samples": the record name has no getter of its own.
		TArray<FString> Parts;
		Debug->DescribePathState().ParseIntoArrayWS(Parts);
		const FString RecordName = Parts.Num() > 1 ? Parts[1] : FString(TEXT("?"));
		OutMessage = FString::Printf(TEXT("cannot enter while recording '%s'"), *RecordName);
		return false;
	}
	if (!EnsureConfig())
	{
		OutMessage = FString::Printf(TEXT("cannot enter: %s"), *LastError);
		return false;
	}
	AGolmokPlayerController* PC = GetPC();
	APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	APlayerCameraManager* Cam = nullptr;
	if (PC)
	{
		Cam = PC->PlayerCameraManager;
	}
	if (!PC || !Pawn || !Cam)
	{
		OutMessage = TEXT("cannot enter: no player controller / pawn");
		return false;
	}

	// 2. save what Exit restores.
	SavedPawn = Pawn;
	SavedViewTarget = PC->GetViewTarget();
	SavedControlRotation = PC->GetControlRotation();
	bWasPausedBefore = UGameplayStatics::IsGamePaused(World);
	SavedTimeDilation = UGameplayStatics::GetGlobalTimeDilation(World);
	SavedPawnTimeDilation = Pawn->CustomTimeDilation;
	// A copy, never a reference: the flag may be a bitfield (section 10 #3).
	const bool bSavedFullTick = PC->bShouldPerformFullTickWhenPaused;
	bSavedFullTickWhenPaused = bSavedFullTick;
	bSavedHudVisible = Debug ? Debug->IsHudVisible() : false;
	bSavedPawnHidden = Pawn->IsHidden();
	bDebugKeysWereActive = !PC->IsDebugKeysSuspended();
	WorldTimeAtEnter = World->GetTimeSeconds();
	UGameViewportClient* Viewport = World->GetGameViewport();
	// Section 10 #12: the member read is the uncertain part; SetSuppressTransitionMessage(bool) is the setter.
	bSavedSuppressTransition = Viewport ? Viewport->bSuppressTransitionMessage : false;

	// 3. camera pose: the photo camera starts exactly where the player camera is (FOV continuity, section 0 #12).
	EnterLocation = Cam->GetCameraLocation();
	EnterRotation = Cam->GetCameraRotation();
	EnterRotation.Roll = 0.f;
	// Section 10 #18: GetFOVAngle(); the fallback is Cam->GetCameraCacheView().FOV, then 80.
	EnterFov = Cam->GetFOVAngle();
	if (!(EnterFov > 0.f))
	{
		EnterFov = 80.f;
	}

	// 4. spawn the pawn (transient, never possessed) and back it out of any geometry it starts in.
	FActorSpawnParameters SpawnParams;
	SpawnParams.ObjectFlags = EObjectFlags(SpawnParams.ObjectFlags | RF_Transient);
	SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	AGolmokPhotoCameraPawn* NewPawn = World->SpawnActor<AGolmokPhotoCameraPawn>(AGolmokPhotoCameraPawn::StaticClass(), EnterLocation, EnterRotation, SpawnParams);
	if (!NewPawn)
	{
		SavedPawn.Reset();
		SavedViewTarget.Reset();
		OutMessage = TEXT("cannot enter: could not spawn the photo pawn");
		return false;
	}
	{
		// Section 10 #16: OverlapBlockingTestByChannel; the fallback is a zero-length sweep.
		FCollisionQueryParams QueryParams(FName(TEXT("GolmokPhotoEnter")), /*bInTraceComplex*/ false);
		QueryParams.AddIgnoredActor(NewPawn);
		QueryParams.AddIgnoredActor(Pawn);
		const FCollisionShape Shape = FCollisionShape::MakeSphere(CollisionRadiusCm);
		const FVector Anchor = Pawn->GetActorLocation();
		FVector Start = EnterLocation;
		for (int32 i = 0; i < PhotoEntryRetreatSteps; ++i)
		{
			if (!World->OverlapBlockingTestByChannel(Start, FQuat::Identity, ECC_WorldDynamic, Shape, QueryParams))
			{
				break;
			}
			Start += (Anchor - Start).GetSafeNormal() * PhotoEntryRetreatCm;
		}
		EnterLocation = Start;
	}
	NewPawn->Init(this, EnterLocation, EnterRotation, EnterFov, CollisionRadiusCm);
	PhotoPawn = NewPawn;

	// 5. view target only - no possession (section 0 #1).
	PC->SetViewTargetWithBlend(NewPawn, 0.f);

	// 6. paused-tick path for the controller (camera manager update while paused, section 10 #3) + the pause itself.
	PC->bShouldPerformFullTickWhenPaused = true;
	ApplyPause(true);
	if (PauseMode == EGolmokPhotoPauseMode::GamePause && !bWasPausedBefore && !UGameplayStatics::IsGamePaused(World))
	{
		// The game mode refused (section 10 #1): undo what was done so far.
		PC->bShouldPerformFullTickWhenPaused = bSavedFullTickWhenPaused;
		AActor* Back = SavedViewTarget.IsValid() ? SavedViewTarget.Get() : static_cast<AActor*>(Pawn);
		PC->SetViewTargetWithBlend(Back, 0.f);
		PhotoPawn.Reset();
		NewPawn->Destroy();
		SavedPawn.Reset();
		SavedViewTarget.Reset();
		OutMessage = TEXT("cannot enter: pause refused");
		return false;
	}

	// 7. no "PAUSED" transition message on screen or in the shot (section 10 #12).
	if (Viewport)
	{
		Viewport->SetSuppressTransitionMessage(true);
	}

	// 8. debug HUD off (golmok.hud 1 can bring it back), debug keys suspended.
	if (Debug)
	{
		Debug->SetHudVisible(false);
	}
	PC->SetDebugKeysSuspended(true);

	// 9. footprint of the zone the character stands in, entry FOV, optics / character visibility.
	CacheFootprint();
	Values[static_cast<int32>(EGolmokPhotoParam::Fov)] = GolmokPhotoMath::ClampParam(static_cast<double>(EnterFov),
		Config.Spec(EGolmokPhotoParam::Fov).Min, Config.Spec(EGolmokPhotoParam::Fov).Max);
	ApplyToPawn();

	// 10. photo input context, state, log.
	bExitPending = false;
	SavedMessageUntilRealSeconds = 0.0;
	AddPhotoContext(true);
	State = EGolmokPhotoState::Active;
	bOverlayDirty = true;
	const FString ZoneText = FootprintZoneId.IsEmpty() ? FString(TEXT("no zone")) : FString::Printf(TEXT("zone %s v%d"), *FootprintZoneId, FootprintZoneVersion);
	OutMessage = FString::Printf(TEXT("photo mode on (fov %.1f, %s, %s)"), Values[static_cast<int32>(EGolmokPhotoParam::Fov)], *ZoneText,
		bWasPausedBefore ? TEXT("already paused") : TEXT("paused"));
	UE_LOG(LogGolmok, Log, TEXT("photo: %s"), *OutMessage);
	return true;
}

void UGolmokPhotoModeSubsystem::ApplyPause(bool bOn)
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	if (PauseMode == EGolmokPhotoPauseMode::TimeDilation)
	{
		// PC fallback (section 0 #2): the world crawls at 0.0001x, the character does not move at all.
		if (bOn)
		{
			UGameplayStatics::SetGlobalTimeDilation(World, PhotoDilationNearZero);
			if (SavedPawn.IsValid())
			{
				SavedPawn->CustomTimeDilation = 0.f;
			}
		}
		else
		{
			UGameplayStatics::SetGlobalTimeDilation(World, SavedTimeDilation);
			if (SavedPawn.IsValid())
			{
				SavedPawn->CustomTimeDilation = SavedPawnTimeDilation;
			}
		}
		return;
	}
	// GamePause: only when the game was not paused before Enter; a pause that pre-dates photo mode is kept.
	if (bWasPausedBefore)
	{
		return;
	}
	// Section 10 #1: UGameplayStatics::SetGamePaused (bool result; the fallback is PC->SetPause / World->IsPaused).
	UGameplayStatics::SetGamePaused(World, bOn);
}

void UGolmokPhotoModeSubsystem::AddPhotoContext(bool bOn)
{
	if (!PhotoContext)
	{
		return;
	}
	AGolmokPlayerController* PC = GetPC();
	if (!PC)
	{
		return;
	}
	UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer());
	if (!Subsystem)
	{
		return;
	}
	if (bOn)
	{
		Subsystem->AddMappingContext(PhotoContext, PhotoMappingPriority);
	}
	else
	{
		// Section 10 #6: RemoveMappingContext(const UInputMappingContext*); the fallback passes FModifyContextOptions().
		Subsystem->RemoveMappingContext(PhotoContext);
	}
}

// ---- state machine: exit ---------------------------------------------------------------------------------------

bool UGolmokPhotoModeSubsystem::Exit(const TCHAR* Reason)
{
	if (State == EGolmokPhotoState::Inactive || State == EGolmokPhotoState::Exiting)
	{
		return false;
	}
	if (IsCapturing())
	{
		bExitPending = true;
		UE_LOG(LogGolmok, Log, TEXT("photo: exit deferred until the capture window closes (%s)"), Reason ? Reason : TEXT(""));
		return true;
	}
	State = EGolmokPhotoState::Exiting;
	UE_LOG(LogGolmok, Verbose, TEXT("photo: exit (%s)"), Reason ? Reason : TEXT(""));
	RestoreAll();
	State = EGolmokPhotoState::Inactive;
	return true;
}

bool UGolmokPhotoModeSubsystem::Toggle(FString& OutMessage)
{
	if (!IsActive())
	{
		return Enter(OutMessage);
	}
	if (IsCapturing())
	{
		Exit(TEXT("toggle"));
		OutMessage = TEXT("exit deferred until the capture window closes");
		return true;
	}
	if (!Exit(TEXT("toggle")))
	{
		OutMessage = TEXT("not active");
		return false;
	}
	OutMessage = TEXT("photo mode off");
	return true;
}

void UGolmokPhotoModeSubsystem::RestoreAll()
{
	// Reverse of Enter (section 4-3); every step is null-safe and independent of the others.
	UWorld* World = GetWorld();
	AddPhotoContext(false);
	if (PhotoPawn.IsValid())
	{
		PhotoPawn->SetMoveInput(FVector2D::ZeroVector);
		PhotoPawn->SetUpDownInput(0.f);
		PhotoPawn->SetLookPad(FVector2D::ZeroVector);
		PhotoPawn->SetFast(false);
	}
	AGolmokPlayerController* PC = GetPC();
	if (PC)
	{
		AActor* Target = SavedViewTarget.IsValid() ? SavedViewTarget.Get() : static_cast<AActor*>(PC->GetPawn());
		if (Target)
		{
			PC->SetViewTargetWithBlend(Target, 0.f);
		}
		PC->SetControlRotation(SavedControlRotation);
	}
	if (SavedPawn.IsValid())
	{
		SavedPawn->SetActorHiddenInGame(bSavedPawnHidden);
	}
	if (UGolmokDebugSubsystem* Debug = GetDebug())
	{
		Debug->SetHudVisible(bSavedHudVisible);
	}
	if (PC)
	{
		if (bDebugKeysWereActive)
		{
			// Re-added only when bDebugKeysEnabled (the controller checks).
			PC->SetDebugKeysSuspended(false);
		}
		PC->bShouldPerformFullTickWhenPaused = bSavedFullTickWhenPaused;
	}
	if (UGameViewportClient* Viewport = World ? World->GetGameViewport() : nullptr)
	{
		Viewport->SetSuppressTransitionMessage(bSavedSuppressTransition);
	}
	ApplyPause(false);
	const bool bUnpaused = PauseMode == EGolmokPhotoPauseMode::TimeDilation || !bWasPausedBefore;

	// Time of day: a running transition resumes where it was, whether the world clock stood still or not.
	double TodShift = 0.0;
	if (World)
	{
		const double Delta = World->GetTimeSeconds() - WorldTimeAtEnter;
		AGolmokTimeOfDay* Tod = GetTimeOfDay();
		if (Tod && Tod->IsTransitioning() && Delta > 0.0)
		{
			Tod->ShiftTransitionStart(Delta);
			TodShift = Delta;
		}
	}

	// The pawn's EndPlay calls back into OnPhotoPawnEndPlay, which ignores it while State == Exiting.
	if (PhotoPawn.IsValid())
	{
		PhotoPawn->Destroy();
	}
	PhotoPawn.Reset();
	SavedPawn.Reset();
	SavedViewTarget.Reset();

	if (EndFrameHandle.IsValid())
	{
		FCoreDelegates::OnEndFrame.Remove(EndFrameHandle);
		EndFrameHandle.Reset();
	}
	FootprintXs.Reset();
	FootprintYs.Reset();
	FootprintZoneId.Reset();
	FootprintZoneVersion = 0;
	bExitPending = false;
	CaptureFrameCounter = 0;
	OverlayLines.Reset();
	bOverlayDirty = true;
	UE_LOG(LogGolmok, Log, TEXT("photo: photo mode off (restored, %s, tod shift %.3f s)"), bUnpaused ? TEXT("unpaused") : TEXT("left paused"), TodShift);
}

void UGolmokPhotoModeSubsystem::TeardownForDeadWorld()
{
	// EndPlayInEditor / Quit / LevelTransition / bIsTearingDown: the PC, the pause state, the view target and the
	// time of day belong to a world that is ending; only our own references and the frame delegate are cleaned.
	if (EndFrameHandle.IsValid())
	{
		FCoreDelegates::OnEndFrame.Remove(EndFrameHandle);
		EndFrameHandle.Reset();
	}
	PhotoPawn.Reset();
	SavedPawn.Reset();
	SavedViewTarget.Reset();
	FootprintXs.Reset();
	FootprintYs.Reset();
	FootprintZoneId.Reset();
	FootprintZoneVersion = 0;
	bExitPending = false;
	CaptureFrameCounter = 0;
	OverlayLines.Reset();
	bOverlayDirty = true;
	State = EGolmokPhotoState::Inactive;
	UE_LOG(LogGolmok, Log, TEXT("photo: teardown (world ending)"));
}

void UGolmokPhotoModeSubsystem::OnPhotoPawnEndPlay(AGolmokPhotoCameraPawn* Pawn, EEndPlayReason::Type Reason)
{
	if (State == EGolmokPhotoState::Inactive || State == EGolmokPhotoState::Exiting)
	{
		// Exit() is destroying it itself, or a stale pawn: nothing to do.
		return;
	}
	if (PhotoPawn.IsValid() && PhotoPawn.Get() != Pawn)
	{
		return;
	}
	UWorld* World = GetWorld();
	if (Reason == EEndPlayReason::Destroyed && World && !World->bIsTearingDown)
	{
		// Someone destroyed the pawn under us in a living world: a normal exit minus the destroy step.
		PhotoPawn.Reset();
		if (IsCapturing())
		{
			// The capture window cannot finish without the camera: close it here, then restore.
			if (EndFrameHandle.IsValid())
			{
				FCoreDelegates::OnEndFrame.Remove(EndFrameHandle);
				EndFrameHandle.Reset();
			}
			State = EGolmokPhotoState::Active;
		}
		Exit(TEXT("pawn destroyed"));
		return;
	}
	TeardownForDeadWorld();
}

// ---- reset / shoot ---------------------------------------------------------------------------------------------

void UGolmokPhotoModeSubsystem::Reset()
{
	if (State != EGolmokPhotoState::Active || !bConfigLoaded)
	{
		return;
	}
	for (int32 i = 0; i < 5; ++i)
	{
		Values[i] = Config.Params[i].Default;
	}
	bDof = false;
	bCharacterHidden = false;
	bOverlayHidden = false;
	SessionMultiplier = 0;
	if (PhotoPawn.IsValid())
	{
		// Back to the entry pose (the entry point was overlap-checked, so no sweep is needed).
		PhotoPawn->SetActorLocation(EnterLocation, /*bSweep*/ false, /*OutSweepHitResult*/ nullptr, ETeleportType::TeleportPhysics);
		PhotoPawn->ApplyLook(FRotator(EnterRotation.Pitch, EnterRotation.Yaw, 0.f));
	}
	ApplyToPawn();
}

FString UGolmokPhotoModeSubsystem::NextStemPath() const
{
	const FString Dir = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectSavedDir(), PhotoFolder));
	const FString Stamp = FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S"));
	const FString Base = FPaths::Combine(Dir, Stamp);
	// The .json is the occupancy marker (the png appears a frame later): <stem>, <stem>_2, <stem>_3, ...
	FString Candidate = Base;
	int32 Suffix = 2;
	while (IFileManager::Get().FileExists(*(Candidate + TEXT(".json"))) || IFileManager::Get().FileExists(*(Candidate + TEXT(".png"))))
	{
		Candidate = FString::Printf(TEXT("%s_%d"), *Base, Suffix);
		++Suffix;
	}
	return Candidate;
}

bool UGolmokPhotoModeSubsystem::Shoot(FString& OutMessage)
{
	if (State == EGolmokPhotoState::Inactive)
	{
		OutMessage = TEXT("not active");
		return false;
	}
	if (IsCapturing())
	{
		OutMessage = TEXT("capture in progress");
		return false;
	}
	if (State != EGolmokPhotoState::Active || !PhotoPawn.IsValid())
	{
		OutMessage = TEXT("no photo pawn");
		return false;
	}
	if (!GetDebug())
	{
		OutMessage = TEXT("no debug subsystem (screenshots go through it)");
		return false;
	}
	const FString Dir = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectSavedDir(), PhotoFolder));
	IFileManager::Get().MakeDirectory(*Dir, /*Tree*/ true);

	// Same tick: HUD / overlay suppressed from the next Draw on, pawn input frozen (the pawn reads IsCapturing()).
	State = EGolmokPhotoState::Shooting;
	PhotoPawn->SetMoveInput(FVector2D::ZeroVector);
	PhotoPawn->SetUpDownInput(0.f);
	PhotoPawn->SetLookPad(FVector2D::ZeroVector);
	CaptureFrameCounter = 0;
	LastShotPathNoExt = NextStemPath();
	const int32 Multiplier = FMath::Clamp(SessionMultiplier > 0 ? SessionMultiplier : ScreenshotMultiplier, 1, MaxMultiplier);
	if (!EndFrameHandle.IsValid())
	{
		EndFrameHandle = FCoreDelegates::OnEndFrame.AddUObject(this, &UGolmokPhotoModeSubsystem::OnEndFrame);
	}
	OutMessage = FString::Printf(TEXT("shooting -> %s.png (%dx, meta %s.json)"), *LastShotPathNoExt, Multiplier, *FPaths::GetBaseFilename(LastShotPathNoExt));
	UE_LOG(LogGolmok, Log, TEXT("photo: %s"), *OutMessage);
	bOverlayDirty = true;
	if (PreCaptureFrames == 0)
	{
		RequestShot();
	}
	return true;
}

void UGolmokPhotoModeSubsystem::OnEndFrame()
{
	if (State == EGolmokPhotoState::Shooting)
	{
		if (++CaptureFrameCounter >= PreCaptureFrames)
		{
			RequestShot();
		}
		return;
	}
	if (State != EGolmokPhotoState::Captured)
	{
		return;
	}
	++CaptureFrameCounter;
	const double Elapsed = FPlatformTime::Seconds() - CaptureRequestRealSeconds;
	const FString PngPath = LastShotPathNoExt + TEXT(".png");
	const bool bPngPresent = IFileManager::Get().FileExists(*PngPath);
	if (CaptureFrameCounter < PostCaptureFrames || !(bPngPresent || Elapsed >= CaptureTimeoutSeconds))
	{
		return;
	}
	// Window closed: the file is there (or 3 s of real time passed - -nullrhi never writes one).
	FCoreDelegates::OnEndFrame.Remove(EndFrameHandle);
	EndFrameHandle.Reset();
	const FString Base = FPaths::GetBaseFilename(LastShotPathNoExt);
	if (bPngPresent)
	{
		UE_LOG(LogGolmok, Log, TEXT("photo: capture window closed (%s.png present after %.2f s)"), *Base, Elapsed);
	}
	else
	{
		UE_LOG(LogGolmok, Log, TEXT("photo: capture window closed (%s.png timeout %.1f s, png absent)"), *Base, CaptureTimeoutSeconds);
	}
	SavedMessageUntilRealSeconds = FPlatformTime::Seconds() + PhotoSavedMessageSeconds;
	State = EGolmokPhotoState::Active;
	bOverlayDirty = true;
	if (bExitPending)
	{
		bExitPending = false;
		Exit(TEXT("deferred"));
	}
}

void UGolmokPhotoModeSubsystem::RequestShot()
{
	// Runs in the Shooting state, PreCaptureFrames frames after Shoot() (or inside it when that is 0).
	auto AbortCapture = [this]()
	{
		if (EndFrameHandle.IsValid())
		{
			FCoreDelegates::OnEndFrame.Remove(EndFrameHandle);
			EndFrameHandle.Reset();
		}
		State = EGolmokPhotoState::Active;
		bOverlayDirty = true;
		if (bExitPending)
		{
			bExitPending = false;
			Exit(TEXT("deferred"));
		}
	};

	UGolmokDebugSubsystem* Debug = GetDebug();
	if (!Debug || !PhotoPawn.IsValid())
	{
		UE_LOG(LogGolmok, Warning, TEXT("photo: ERROR capture aborted (no debug subsystem / photo pawn)"));
		AbortCapture();
		return;
	}
	const int32 Multiplier = FMath::Clamp(SessionMultiplier > 0 ? SessionMultiplier : ScreenshotMultiplier, 1, MaxMultiplier);
	// The zone can only have changed through streaming, but the meta's zone_id must be exact.
	CacheFootprint();
	GolmokPhotoMath::PhotoMeta Meta = BuildMeta(Multiplier);
	const FString JsonPath = LastShotPathNoExt + TEXT(".json");
	FString Error;
	// Meta first, synchronously; no screenshot when it cannot be written (section 0 #13).
	if (!WriteMeta(JsonPath, Meta, Error))
	{
		UE_LOG(LogGolmok, Error, TEXT("photo: ERROR %s"), *Error);
		AbortCapture();
		return;
	}
	FString Message;
	int32 Effective = Multiplier;
	if (!Debug->RequestHighResScreenshot(LastShotPathNoExt, Multiplier, Message, Effective))
	{
		IFileManager::Get().Delete(*JsonPath, /*RequireExists*/ false, /*EvenReadOnly*/ true, /*Quiet*/ true);
		UE_LOG(LogGolmok, Error, TEXT("photo: ERROR screenshot request failed: %s"), *Message);
		AbortCapture();
		return;
	}
	if (Effective != Multiplier)
	{
		// 1x fallback: the meta carries what will really be rendered.
		Meta.Multiplier = Effective;
		if (!WriteMeta(JsonPath, Meta, Error))
		{
			UE_LOG(LogGolmok, Warning, TEXT("photo: ERROR %s (multiplier %d recorded instead of %d)"), *Error, Multiplier, Effective);
		}
	}
	LastEffectiveMultiplier = Effective;
	CaptureRequestRealSeconds = FPlatformTime::Seconds();
	CaptureFrameCounter = 0;
	State = EGolmokPhotoState::Captured;
	UE_LOG(LogGolmok, Log, TEXT("photo: %s"), *Message);
}

bool UGolmokPhotoModeSubsystem::WriteMeta(const FString& InJsonPath, const GolmokPhotoMath::PhotoMeta& M, FString& OutError)
{
	const std::string Text = GolmokPhotoMath::FormatPhotoMetaJson(M);
	const FString Content = PhotoFromUtf8(Text);
	if (!FFileHelper::SaveStringToFile(Content, *InJsonPath, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
	{
		OutError = FString::Printf(TEXT("cannot write meta %s"), *InJsonPath);
		return false;
	}
	OutError.Reset();
	return true;
}

GolmokPhotoMath::PhotoMeta UGolmokPhotoModeSubsystem::BuildMeta(int32 InMultiplier) const
{
	GolmokPhotoMath::PhotoMeta M;
	M.Version = 1;
	M.TimeUtc = PhotoToUtf8(FDateTime::UtcNow().ToString(TEXT("%Y-%m-%dT%H:%M:%SZ")));

	const AGolmokTimeOfDay* Tod = GetTimeOfDay();
	M.bHasPreset = Tod && !Tod->CurrentPreset.IsNone();
	if (M.bHasPreset)
	{
		M.Preset = PhotoToUtf8(Tod->CurrentPreset.ToString());
	}

	M.bHasZone = !FootprintZoneId.IsEmpty();
	if (M.bHasZone)
	{
		M.ZoneId = PhotoToUtf8(FootprintZoneId);
		M.ZoneVersion = FootprintZoneVersion;
	}

	// Camera (pawn) pose; the entry pose stands in when the pawn is gone.
	FVector Location = EnterLocation;
	FRotator Rotation = EnterRotation;
	if (PhotoPawn.IsValid())
	{
		Location = PhotoPawn->GetActorLocation();
		const UCameraComponent* Camera = PhotoPawn->GetCamera();
		Rotation = Camera ? Camera->GetComponentRotation() : PhotoPawn->GetActorRotation();
	}
	M.UeLocation = {Location.X, Location.Y, Location.Z};
	M.Rotation = {Rotation.Pitch, Rotation.Yaw, Rotation.Roll};

	UWorld* World = GetWorld();
	UGolmokGeoSubsystem* Geo = World ? World->GetSubsystem<UGolmokGeoSubsystem>() : nullptr;
	double Lat = 0.0;
	double Lon = 0.0;
	double Height = 0.0;
	if (Geo && Geo->LevelUEToLonLat(Location, Lat, Lon, Height))
	{
		M.bHasGeo = true;
		M.Lon = Lon;
		M.Lat = Lat;
		M.HeightM = Height;
	}

	M.Fov = Values[static_cast<int32>(EGolmokPhotoParam::Fov)];
	M.ExposureEv = Values[static_cast<int32>(EGolmokPhotoParam::Ev)];
	M.bDofEnabled = bDof;
	M.FocalM = Values[static_cast<int32>(EGolmokPhotoParam::Focus)];
	M.Fstop = Values[static_cast<int32>(EGolmokPhotoParam::Fstop)];
	M.Multiplier = InMultiplier;
	M.bCharacterHidden = bCharacterHidden;
	return M;
}

// ---- overlay / describe ------------------------------------------------------------------------------------------

FString UGolmokPhotoModeSubsystem::Describe() const
{
	switch (State)
	{
	case EGolmokPhotoState::Inactive:
		return TEXT("inactive");
	case EGolmokPhotoState::Shooting:
		return TEXT("shooting");
	case EGolmokPhotoState::Captured:
		return TEXT("captured");
	case EGolmokPhotoState::Exiting:
		return TEXT("exiting");
	case EGolmokPhotoState::Active:
	default:
		break;
	}
	const FString ZoneText = FootprintZoneId.IsEmpty() ? FString(TEXT("no zone")) : FString::Printf(TEXT("zone %s v%d"), *FootprintZoneId, FootprintZoneVersion);
	return FString::Printf(TEXT("active fov %s ev %s focus %s m f/%s dof %s roll %s (%s)"), *PhotoFormatValue(EGolmokPhotoParam::Fov, GetParam(EGolmokPhotoParam::Fov)),
		*PhotoFormatValue(EGolmokPhotoParam::Ev, GetParam(EGolmokPhotoParam::Ev)), *PhotoFormatValue(EGolmokPhotoParam::Focus, GetParam(EGolmokPhotoParam::Focus)),
		*PhotoFormatValue(EGolmokPhotoParam::Fstop, GetParam(EGolmokPhotoParam::Fstop)), bDof ? TEXT("on") : TEXT("off"),
		*PhotoFormatValue(EGolmokPhotoParam::Roll, GetParam(EGolmokPhotoParam::Roll)), *ZoneText);
}

const TArray<FString>& UGolmokPhotoModeSubsystem::GetOverlayLines()
{
	if (State != EGolmokPhotoState::Active || bOverlayHidden)
	{
		OverlayLines.Reset();
		OverlayLinesRealSeconds = -1.0;
		return OverlayLines;
	}
	const double Now = FPlatformTime::Seconds();
	const bool bSavedLineVisible = Now < SavedMessageUntilRealSeconds;
	const bool bSavedLineShown = OverlayLines.Num() > 0 && OverlayLines.Last().StartsWith(TEXT("saved "));
	if (!bOverlayDirty && OverlayLinesRealSeconds >= 0.0 && Now - OverlayLinesRealSeconds < PhotoOverlayRefreshSeconds && bSavedLineVisible == bSavedLineShown)
	{
		return OverlayLines;
	}
	OverlayLines.Reset();

	// Status line (white; "no zone" turns it yellow in the HUD).
	const FString ZoneText = FootprintZoneId.IsEmpty() ? FString(TEXT("no zone")) : FString::Printf(TEXT("%s v%d"), *FootprintZoneId, FootprintZoneVersion);
	const AGolmokTimeOfDay* Tod = GetTimeOfDay();
	const FString PresetText = (Tod && !Tod->CurrentPreset.IsNone()) ? Tod->CurrentPreset.ToString() : FString(TEXT("-"));
	const FVector CameraLocation = PhotoPawn.IsValid() ? PhotoPawn->GetActorLocation() : EnterLocation;
	const double DistanceM = FVector::Dist(CameraLocation, GetAnchor()) / 100.0;
	const int32 Multiplier = FMath::Clamp(SessionMultiplier > 0 ? SessionMultiplier : ScreenshotMultiplier, 1, MaxMultiplier);
	OverlayLines.Add(FString::Printf(TEXT("PHOTO  %s  %s  %.1f / %.1f m  %dx"), *ZoneText, *PresetText, DistanceM, MaxDistanceM, Multiplier));

	// Values line (cyan): the Describe() formatter plus the 35 mm equivalent of the FOV.
	const double FovDeg = GetParam(EGolmokPhotoParam::Fov);
	FString ValuesLine = FString::Printf(TEXT("fov %.0f (%.0f mm)  ev %s  focus %s m  f/%s  dof %s  roll %s"), FovDeg, GolmokPhotoMath::FovToFocalMm(FovDeg),
		*PhotoFormatValue(EGolmokPhotoParam::Ev, GetParam(EGolmokPhotoParam::Ev)), *PhotoFormatValue(EGolmokPhotoParam::Focus, GetParam(EGolmokPhotoParam::Focus)),
		*PhotoFormatValue(EGolmokPhotoParam::Fstop, GetParam(EGolmokPhotoParam::Fstop)), bDof ? TEXT("on") : TEXT("off"),
		*PhotoFormatValue(EGolmokPhotoParam::Roll, GetParam(EGolmokPhotoParam::Roll)));
	if (bCharacterHidden)
	{
		ValuesLine += TEXT("  [char hidden]");
	}
	OverlayLines.Add(ValuesLine);

	// Hints (gray): keyboard lines only (no device detection in this version; the gamepad lines stay in the JSON).
	if (bConfigLoaded)
	{
		OverlayLines.Append(Config.HintsKeyboard);
	}

	// "saved ..." (green) for a short while after a capture.
	if (bSavedLineVisible && !LastShotPathNoExt.IsEmpty())
	{
		OverlayLines.Add(FString::Printf(TEXT("saved %s.png (%dx)"), *FPaths::GetBaseFilename(LastShotPathNoExt), LastEffectiveMultiplier));
	}
	OverlayLinesRealSeconds = Now;
	bOverlayDirty = false;
	return OverlayLines;
}

// ---- input ------------------------------------------------------------------------------------------------------

void UGolmokPhotoModeSubsystem::EnsureInputAssets(UObject* Outer)
{
	if (PhotoContext || !Outer)
	{
		return;
	}
	Actions.Reset();
	Actions.SetNum(static_cast<int32>(EPhotoActionSlot::Count));

	// Every photo action fires while the game is paused and swallows its keys (design section 5-1 / 0 #3).
	auto MakeAction = [this, Outer](EPhotoActionSlot Slot, const TCHAR* Name, EInputActionValueType Type) -> UInputAction*
	{
		UInputAction* Action = NewObject<UInputAction>(Outer, Name);
		Action->ValueType = Type;
		Action->bTriggerWhenPaused = true;
		Action->bConsumeInput = true;
		Actions[static_cast<int32>(Slot)] = Action;
		return Action;
	};

	UInputAction* ShootAction = MakeAction(EPhotoActionSlot::Shoot, TEXT("IA_GolmokPhotoShoot"), EInputActionValueType::Boolean);
	UInputAction* ResetAction = MakeAction(EPhotoActionSlot::Reset, TEXT("IA_GolmokPhotoReset"), EInputActionValueType::Boolean);
	UInputAction* Dof = MakeAction(EPhotoActionSlot::Dof, TEXT("IA_GolmokPhotoDof"), EInputActionValueType::Boolean);
	UInputAction* HideCharacter = MakeAction(EPhotoActionSlot::HideCharacter, TEXT("IA_GolmokPhotoHideCharacter"), EInputActionValueType::Boolean);
	UInputAction* HideOverlay = MakeAction(EPhotoActionSlot::HideOverlay, TEXT("IA_GolmokPhotoHideOverlay"), EInputActionValueType::Boolean);
	UInputAction* FovUp = MakeAction(EPhotoActionSlot::FovUp, TEXT("IA_GolmokPhotoFovUp"), EInputActionValueType::Boolean);
	UInputAction* FovDown = MakeAction(EPhotoActionSlot::FovDown, TEXT("IA_GolmokPhotoFovDown"), EInputActionValueType::Boolean);
	UInputAction* FovWheel = MakeAction(EPhotoActionSlot::FovWheel, TEXT("IA_GolmokPhotoFovWheel"), EInputActionValueType::Axis1D);
	UInputAction* EvUp = MakeAction(EPhotoActionSlot::EvUp, TEXT("IA_GolmokPhotoEvUp"), EInputActionValueType::Boolean);
	UInputAction* EvDown = MakeAction(EPhotoActionSlot::EvDown, TEXT("IA_GolmokPhotoEvDown"), EInputActionValueType::Boolean);
	UInputAction* FocusUp = MakeAction(EPhotoActionSlot::FocusUp, TEXT("IA_GolmokPhotoFocusUp"), EInputActionValueType::Boolean);
	UInputAction* FocusDown = MakeAction(EPhotoActionSlot::FocusDown, TEXT("IA_GolmokPhotoFocusDown"), EInputActionValueType::Boolean);
	UInputAction* FstopUp = MakeAction(EPhotoActionSlot::FstopUp, TEXT("IA_GolmokPhotoFstopUp"), EInputActionValueType::Boolean);
	UInputAction* FstopDown = MakeAction(EPhotoActionSlot::FstopDown, TEXT("IA_GolmokPhotoFstopDown"), EInputActionValueType::Boolean);
	UInputAction* RollUp = MakeAction(EPhotoActionSlot::RollUp, TEXT("IA_GolmokPhotoRollUp"), EInputActionValueType::Boolean);
	UInputAction* RollDown = MakeAction(EPhotoActionSlot::RollDown, TEXT("IA_GolmokPhotoRollDown"), EInputActionValueType::Boolean);
	UInputAction* Move = MakeAction(EPhotoActionSlot::Move, TEXT("IA_GolmokPhotoMove"), EInputActionValueType::Axis2D);
	UInputAction* UpDown = MakeAction(EPhotoActionSlot::UpDown, TEXT("IA_GolmokPhotoUpDown"), EInputActionValueType::Axis1D);
	UInputAction* LookAction = MakeAction(EPhotoActionSlot::Look, TEXT("IA_GolmokPhotoLook"), EInputActionValueType::Axis2D);
	UInputAction* LookPad = MakeAction(EPhotoActionSlot::LookPad, TEXT("IA_GolmokPhotoLookPad"), EInputActionValueType::Axis2D);
	UInputAction* Fast = MakeAction(EPhotoActionSlot::Fast, TEXT("IA_GolmokPhotoFast"), EInputActionValueType::Boolean);

	PhotoContext = NewObject<UInputMappingContext>(Outer, TEXT("IMC_GolmokPhoto"));
	UInputMappingContext* Context = PhotoContext;

	// Section 5-1 key table. Section 10 #19: every EKeys name below is on the EKeys page except the trigger axes
	// (Gamepad_LeftTriggerAxis confirmed, Gamepad_RightTriggerAxis second-hand); the fallback is the two trigger
	// buttons (Gamepad_LeftTrigger / Gamepad_RightTrigger) as Bool actions.
	Context->MapKey(ShootAction, EKeys::SpaceBar);
	Context->MapKey(ShootAction, EKeys::Enter);
	Context->MapKey(ShootAction, EKeys::Gamepad_FaceButton_Bottom);
	Context->MapKey(ResetAction, EKeys::R);
	Context->MapKey(ResetAction, EKeys::Gamepad_Special_Right);
	Context->MapKey(Dof, EKeys::F);
	Context->MapKey(Dof, EKeys::Gamepad_RightThumbstick);
	Context->MapKey(HideCharacter, EKeys::H);
	Context->MapKey(HideCharacter, EKeys::Gamepad_FaceButton_Right);
	Context->MapKey(HideOverlay, EKeys::O);
	Context->MapKey(FovUp, EKeys::RightBracket);
	Context->MapKey(FovUp, EKeys::Gamepad_DPad_Right);
	Context->MapKey(FovDown, EKeys::LeftBracket);
	Context->MapKey(FovDown, EKeys::Gamepad_DPad_Left);
	Context->MapKey(FovWheel, EKeys::MouseWheelAxis);
	Context->MapKey(EvUp, EKeys::Equals);
	Context->MapKey(EvUp, EKeys::Gamepad_DPad_Up);
	Context->MapKey(EvDown, EKeys::Hyphen);
	Context->MapKey(EvDown, EKeys::Gamepad_DPad_Down);
	Context->MapKey(FocusUp, EKeys::Period);
	Context->MapKey(FocusUp, EKeys::Gamepad_RightShoulder);
	Context->MapKey(FocusDown, EKeys::Comma);
	Context->MapKey(FocusDown, EKeys::Gamepad_LeftShoulder);
	Context->MapKey(FstopUp, EKeys::M);
	Context->MapKey(FstopUp, EKeys::Gamepad_FaceButton_Top);
	Context->MapKey(FstopDown, EKeys::N);
	Context->MapKey(FstopDown, EKeys::Gamepad_FaceButton_Left);
	Context->MapKey(RollUp, EKeys::C);
	Context->MapKey(RollDown, EKeys::Z);

	// Keyboard keys produce a 1D value on X. Swizzle moves it to Y (forward / back); Negate flips it (AGolmokCharacter).
	auto MapMoveKey = [Context, Move](const FKey& Key, bool bToY, bool bNegate)
	{
		FEnhancedActionKeyMapping& Mapping = Context->MapKey(Move, Key);
		if (bToY)
		{
			Mapping.Modifiers.Add(NewObject<UInputModifierSwizzleAxis>(Context));
		}
		if (bNegate)
		{
			Mapping.Modifiers.Add(NewObject<UInputModifierNegate>(Context));
		}
	};
	MapMoveKey(EKeys::W, true, false);
	MapMoveKey(EKeys::S, true, true);
	MapMoveKey(EKeys::D, false, false);
	MapMoveKey(EKeys::A, false, true);
	Context->MapKey(Move, EKeys::Gamepad_Left2D);

	// Up / down: E and the right trigger up, Q and the left trigger down (Negate).
	auto MapUpDownKey = [Context, UpDown](const FKey& Key, bool bNegate)
	{
		FEnhancedActionKeyMapping& Mapping = Context->MapKey(UpDown, Key);
		if (bNegate)
		{
			Mapping.Modifiers.Add(NewObject<UInputModifierNegate>(Context));
		}
	};
	MapUpDownKey(EKeys::E, false);
	MapUpDownKey(EKeys::Q, true);
	MapUpDownKey(EKeys::Gamepad_RightTriggerAxis, false);
	MapUpDownKey(EKeys::Gamepad_LeftTriggerAxis, true);

	// Mouse / right stick Y is positive when pushed up; pitch input is positive when looking down (character convention).
	auto MapLookKey = [Context](UInputAction* Action, const FKey& Key)
	{
		FEnhancedActionKeyMapping& Mapping = Context->MapKey(Action, Key);
		UInputModifierNegate* Negate = NewObject<UInputModifierNegate>(Context);
		Negate->bX = false;
		Negate->bY = true;
		Negate->bZ = false;
		Mapping.Modifiers.Add(Negate);
	};
	MapLookKey(LookAction, EKeys::Mouse2D);
	MapLookKey(LookPad, EKeys::Gamepad_Right2D);

	Context->MapKey(Fast, EKeys::LeftShift);
	Context->MapKey(Fast, EKeys::Gamepad_LeftThumbstick);
}

void UGolmokPhotoModeSubsystem::BindInput(UEnhancedInputComponent* Input)
{
	if (!Input)
	{
		return;
	}
	EnsureInputAssets(this);
	if (!PhotoContext)
	{
		return;
	}
	auto ActionAt = [this](EPhotoActionSlot Slot) -> UInputAction*
	{
		return Actions[static_cast<int32>(Slot)];
	};
	// Section 10 #7: BindAction with a UWorldSubsystem (UObject) handler; the fallback moves the handlers to the PC.
	Input->BindAction(ActionAt(EPhotoActionSlot::Shoot), ETriggerEvent::Started, this, &UGolmokPhotoModeSubsystem::OnShoot);
	Input->BindAction(ActionAt(EPhotoActionSlot::Reset), ETriggerEvent::Started, this, &UGolmokPhotoModeSubsystem::OnReset);
	Input->BindAction(ActionAt(EPhotoActionSlot::Dof), ETriggerEvent::Started, this, &UGolmokPhotoModeSubsystem::OnDof);
	Input->BindAction(ActionAt(EPhotoActionSlot::HideCharacter), ETriggerEvent::Started, this, &UGolmokPhotoModeSubsystem::OnHideCharacter);
	Input->BindAction(ActionAt(EPhotoActionSlot::HideOverlay), ETriggerEvent::Started, this, &UGolmokPhotoModeSubsystem::OnHideOverlay);
	Input->BindAction(ActionAt(EPhotoActionSlot::FovUp), ETriggerEvent::Started, this, &UGolmokPhotoModeSubsystem::OnFovUp);
	Input->BindAction(ActionAt(EPhotoActionSlot::FovDown), ETriggerEvent::Started, this, &UGolmokPhotoModeSubsystem::OnFovDown);
	Input->BindAction(ActionAt(EPhotoActionSlot::FovWheel), ETriggerEvent::Triggered, this, &UGolmokPhotoModeSubsystem::OnFovWheel);
	Input->BindAction(ActionAt(EPhotoActionSlot::EvUp), ETriggerEvent::Started, this, &UGolmokPhotoModeSubsystem::OnEvUp);
	Input->BindAction(ActionAt(EPhotoActionSlot::EvDown), ETriggerEvent::Started, this, &UGolmokPhotoModeSubsystem::OnEvDown);
	Input->BindAction(ActionAt(EPhotoActionSlot::FocusUp), ETriggerEvent::Started, this, &UGolmokPhotoModeSubsystem::OnFocusUp);
	Input->BindAction(ActionAt(EPhotoActionSlot::FocusDown), ETriggerEvent::Started, this, &UGolmokPhotoModeSubsystem::OnFocusDown);
	Input->BindAction(ActionAt(EPhotoActionSlot::FstopUp), ETriggerEvent::Started, this, &UGolmokPhotoModeSubsystem::OnFstopUp);
	Input->BindAction(ActionAt(EPhotoActionSlot::FstopDown), ETriggerEvent::Started, this, &UGolmokPhotoModeSubsystem::OnFstopDown);
	Input->BindAction(ActionAt(EPhotoActionSlot::RollUp), ETriggerEvent::Started, this, &UGolmokPhotoModeSubsystem::OnRollUp);
	Input->BindAction(ActionAt(EPhotoActionSlot::RollDown), ETriggerEvent::Started, this, &UGolmokPhotoModeSubsystem::OnRollDown);
	Input->BindAction(ActionAt(EPhotoActionSlot::Move), ETriggerEvent::Triggered, this, &UGolmokPhotoModeSubsystem::OnMove);
	Input->BindAction(ActionAt(EPhotoActionSlot::Move), ETriggerEvent::Completed, this, &UGolmokPhotoModeSubsystem::OnMoveEnd);
	Input->BindAction(ActionAt(EPhotoActionSlot::UpDown), ETriggerEvent::Triggered, this, &UGolmokPhotoModeSubsystem::OnUpDown);
	Input->BindAction(ActionAt(EPhotoActionSlot::UpDown), ETriggerEvent::Completed, this, &UGolmokPhotoModeSubsystem::OnUpDownEnd);
	Input->BindAction(ActionAt(EPhotoActionSlot::Look), ETriggerEvent::Triggered, this, &UGolmokPhotoModeSubsystem::OnLook);
	Input->BindAction(ActionAt(EPhotoActionSlot::LookPad), ETriggerEvent::Triggered, this, &UGolmokPhotoModeSubsystem::OnLookPad);
	Input->BindAction(ActionAt(EPhotoActionSlot::LookPad), ETriggerEvent::Completed, this, &UGolmokPhotoModeSubsystem::OnLookPad);
	Input->BindAction(ActionAt(EPhotoActionSlot::Fast), ETriggerEvent::Started, this, &UGolmokPhotoModeSubsystem::OnFastStart);
	Input->BindAction(ActionAt(EPhotoActionSlot::Fast), ETriggerEvent::Completed, this, &UGolmokPhotoModeSubsystem::OnFastEnd);
}

void UGolmokPhotoModeSubsystem::OnShoot()
{
	FString Message;
	if (!Shoot(Message))
	{
		// Keys are silent about "capture in progress"; other refusals are worth a line.
		if (!IsCapturing())
		{
			UE_LOG(LogGolmok, Warning, TEXT("photo: shoot refused: %s"), *Message);
		}
	}
}

void UGolmokPhotoModeSubsystem::OnReset()
{
	Reset();
}

void UGolmokPhotoModeSubsystem::OnDof()
{
	if (State == EGolmokPhotoState::Active)
	{
		SetDofEnabled(!bDof);
	}
}

void UGolmokPhotoModeSubsystem::OnHideCharacter()
{
	if (State == EGolmokPhotoState::Active)
	{
		SetCharacterHidden(!bCharacterHidden);
	}
}

void UGolmokPhotoModeSubsystem::OnHideOverlay()
{
	if (State == EGolmokPhotoState::Active)
	{
		SetOverlayHidden(!bOverlayHidden);
	}
}

void UGolmokPhotoModeSubsystem::OnFovUp()
{
	StepParam(EGolmokPhotoParam::Fov, +1);
}

void UGolmokPhotoModeSubsystem::OnFovDown()
{
	StepParam(EGolmokPhotoParam::Fov, -1);
}

void UGolmokPhotoModeSubsystem::OnFovWheel(const FInputActionValue& Value)
{
	// Wheel up (positive) = narrower; only the sign counts (section 10 #19).
	const float Axis = Value.Get<float>();
	if (Axis > 0.f)
	{
		StepParam(EGolmokPhotoParam::Fov, -1);
	}
	else if (Axis < 0.f)
	{
		StepParam(EGolmokPhotoParam::Fov, +1);
	}
}

void UGolmokPhotoModeSubsystem::OnEvUp()
{
	StepParam(EGolmokPhotoParam::Ev, +1);
}

void UGolmokPhotoModeSubsystem::OnEvDown()
{
	StepParam(EGolmokPhotoParam::Ev, -1);
}

void UGolmokPhotoModeSubsystem::OnFocusUp()
{
	StepParam(EGolmokPhotoParam::Focus, +1);
}

void UGolmokPhotoModeSubsystem::OnFocusDown()
{
	StepParam(EGolmokPhotoParam::Focus, -1);
}

void UGolmokPhotoModeSubsystem::OnFstopUp()
{
	StepParam(EGolmokPhotoParam::Fstop, +1);
}

void UGolmokPhotoModeSubsystem::OnFstopDown()
{
	StepParam(EGolmokPhotoParam::Fstop, -1);
}

void UGolmokPhotoModeSubsystem::OnRollUp()
{
	StepParam(EGolmokPhotoParam::Roll, +1);
}

void UGolmokPhotoModeSubsystem::OnRollDown()
{
	StepParam(EGolmokPhotoParam::Roll, -1);
}

void UGolmokPhotoModeSubsystem::OnMove(const FInputActionValue& Value)
{
	if (State == EGolmokPhotoState::Active && PhotoPawn.IsValid())
	{
		PhotoPawn->SetMoveInput(Value.Get<FVector2D>());
	}
}

void UGolmokPhotoModeSubsystem::OnMoveEnd(const FInputActionValue& Value)
{
	(void)Value;
	if (PhotoPawn.IsValid())
	{
		PhotoPawn->SetMoveInput(FVector2D::ZeroVector);
	}
}

void UGolmokPhotoModeSubsystem::OnUpDown(const FInputActionValue& Value)
{
	if (State == EGolmokPhotoState::Active && PhotoPawn.IsValid())
	{
		PhotoPawn->SetUpDownInput(Value.Get<float>());
	}
}

void UGolmokPhotoModeSubsystem::OnUpDownEnd(const FInputActionValue& Value)
{
	(void)Value;
	if (PhotoPawn.IsValid())
	{
		PhotoPawn->SetUpDownInput(0.f);
	}
}

void UGolmokPhotoModeSubsystem::OnLook(const FInputActionValue& Value)
{
	if (State == EGolmokPhotoState::Active && PhotoPawn.IsValid())
	{
		PhotoPawn->AddLookMouse(Value.Get<FVector2D>());
	}
}

void UGolmokPhotoModeSubsystem::OnLookPad(const FInputActionValue& Value)
{
	if (!PhotoPawn.IsValid())
	{
		return;
	}
	// Completed delivers a zero value, which releases the stick.
	PhotoPawn->SetLookPad(State == EGolmokPhotoState::Active ? Value.Get<FVector2D>() : FVector2D::ZeroVector);
}

void UGolmokPhotoModeSubsystem::OnFastStart()
{
	if (PhotoPawn.IsValid())
	{
		PhotoPawn->SetFast(true);
	}
}

void UGolmokPhotoModeSubsystem::OnFastEnd()
{
	if (PhotoPawn.IsValid())
	{
		PhotoPawn->SetFast(false);
	}
}

// ---- console: golmok.photo | golmok.photo.shoot | golmok.photo.reset | golmok.photo.set --------------------------

namespace
{
	UGolmokPhotoModeSubsystem* PhotoSubsystemFor(UWorld* World)
	{
		UGolmokPhotoModeSubsystem* Subsystem = UGolmokPhotoModeSubsystem::Get(World);
		if (!Subsystem)
		{
			UE_LOG(LogGolmok, Warning, TEXT("golmok.photo*: no photo mode subsystem in this world (game / PIE only)."));
		}
		return Subsystem;
	}

	/** "0" / "1" (also off/on, false/true); anything else -> !Current. */
	bool PhotoParseToggle(const FString& Arg, bool bCurrent)
	{
		const FString Lower = Arg.ToLower();
		if (Lower == TEXT("0") || Lower == TEXT("off") || Lower == TEXT("false"))
		{
			return false;
		}
		if (Lower == TEXT("1") || Lower == TEXT("on") || Lower == TEXT("true"))
		{
			return true;
		}
		return !bCurrent;
	}

	void CmdPhoto(const TArray<FString>& Args, UWorld* World)
	{
		UGolmokPhotoModeSubsystem* Subsystem = PhotoSubsystemFor(World);
		if (!Subsystem)
		{
			return;
		}
		FString Message;
		bool bOk = false;
		if (Args.Num() < 1)
		{
			bOk = Subsystem->Toggle(Message);
		}
		else if (PhotoParseToggle(Args[0], Subsystem->IsActive()))
		{
			// Enter() writes the section 2-3 refusal messages itself ("cannot enter: already active", ...).
			bOk = Subsystem->Enter(Message);
		}
		else
		{
			const bool bWasCapturing = Subsystem->IsCapturing();
			bOk = Subsystem->Exit(TEXT("golmok.photo 0"));
			Message = bOk ? (bWasCapturing ? TEXT("exit deferred until the capture window closes") : TEXT("photo mode off")) : TEXT("not active");
		}
		UE_LOG(LogGolmok, Log, TEXT("golmok.photo: %s%s"), bOk ? TEXT("") : TEXT("ERROR "), *Message);
	}

	void CmdPhotoShoot(const TArray<FString>& Args, UWorld* World)
	{
		(void)Args;
		UGolmokPhotoModeSubsystem* Subsystem = PhotoSubsystemFor(World);
		if (!Subsystem)
		{
			return;
		}
		FString Message;
		const bool bOk = Subsystem->Shoot(Message);
		UE_LOG(LogGolmok, Log, TEXT("golmok.photo.shoot: %s%s"), bOk ? TEXT("") : TEXT("ERROR "), *Message);
	}

	void CmdPhotoReset(const TArray<FString>& Args, UWorld* World)
	{
		(void)Args;
		UGolmokPhotoModeSubsystem* Subsystem = PhotoSubsystemFor(World);
		if (!Subsystem)
		{
			return;
		}
		if (!Subsystem->IsActive())
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.photo.reset: ERROR not active"));
			return;
		}
		if (Subsystem->IsCapturing())
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.photo.reset: ERROR capture in progress"));
			return;
		}
		Subsystem->Reset();
		UE_LOG(LogGolmok, Log, TEXT("golmok.photo.reset: reset (fov %s ev %s focus %s f/%s dof %s roll %s, character shown, overlay shown, pose restored)"),
			*PhotoFormatValue(EGolmokPhotoParam::Fov, Subsystem->GetParam(EGolmokPhotoParam::Fov)),
			*PhotoFormatValue(EGolmokPhotoParam::Ev, Subsystem->GetParam(EGolmokPhotoParam::Ev)),
			*PhotoFormatValue(EGolmokPhotoParam::Focus, Subsystem->GetParam(EGolmokPhotoParam::Focus)),
			*PhotoFormatValue(EGolmokPhotoParam::Fstop, Subsystem->GetParam(EGolmokPhotoParam::Fstop)), Subsystem->IsDofEnabled() ? TEXT("on") : TEXT("off"),
			*PhotoFormatValue(EGolmokPhotoParam::Roll, Subsystem->GetParam(EGolmokPhotoParam::Roll)));
	}

	void CmdPhotoSet(const TArray<FString>& Args, UWorld* World)
	{
		UGolmokPhotoModeSubsystem* Subsystem = PhotoSubsystemFor(World);
		if (!Subsystem)
		{
			return;
		}
		if (Args.Num() < 2)
		{
			UE_LOG(LogGolmok, Warning, TEXT("usage: golmok.photo.set <fov|ev|focus|fstop|roll|dof|char|overlay|mult> <value>"));
			return;
		}
		if (!Subsystem->IsActive())
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.photo.set: ERROR not active"));
			return;
		}
		if (Subsystem->IsCapturing())
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.photo.set: ERROR capture in progress"));
			return;
		}
		const FString Name = Args[0].ToLower();
		FString Message;
		bool bOk = false;
		EGolmokPhotoParam Param = EGolmokPhotoParam::Fov;
		if (Name == TEXT("dof"))
		{
			Subsystem->SetDofEnabled(PhotoParseToggle(Args[1], Subsystem->IsDofEnabled()));
			bOk = true;
			Message = FString::Printf(TEXT("dof %s"), Subsystem->IsDofEnabled() ? TEXT("on") : TEXT("off"));
		}
		else if (Name == TEXT("char"))
		{
			Subsystem->SetCharacterHidden(PhotoParseToggle(Args[1], Subsystem->IsCharacterHidden()));
			bOk = true;
			Message = FString::Printf(TEXT("character %s"), Subsystem->IsCharacterHidden() ? TEXT("hidden") : TEXT("shown"));
		}
		else if (Name == TEXT("overlay"))
		{
			Subsystem->SetOverlayHidden(PhotoParseToggle(Args[1], Subsystem->IsOverlayHidden()));
			bOk = true;
			Message = FString::Printf(TEXT("overlay %s"), Subsystem->IsOverlayHidden() ? TEXT("hidden") : TEXT("shown"));
		}
		else if (Name == TEXT("mult"))
		{
			bOk = Subsystem->SetMultiplier(FCString::Atoi(*Args[1]), Message);
		}
		else if (UGolmokPhotoModeSubsystem::ParseParamName(Name, Param))
		{
			if (!Args[1].IsNumeric())
			{
				Message = FString::Printf(TEXT("'%s' is not a number"), *Args[1]);
			}
			else
			{
				bOk = Subsystem->SetParam(Param, FCString::Atod(*Args[1]), Message);
			}
		}
		else
		{
			Message = FString::Printf(TEXT("unknown name '%s' (fov|ev|focus|fstop|roll|dof|char|overlay|mult)"), *Args[0]);
		}
		UE_LOG(LogGolmok, Log, TEXT("golmok.photo.set: %s%s"), bOk ? TEXT("") : TEXT("ERROR "), *Message);
	}

	FAutoConsoleCommandWithWorldAndArgs GCmdPhoto(TEXT("golmok.photo"), TEXT("golmok.photo [0|1]: enter / leave photo mode (toggle without argument)."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdPhoto));
	FAutoConsoleCommandWithWorldAndArgs GCmdPhotoShoot(TEXT("golmok.photo.shoot"), TEXT("golmok.photo.shoot: take the photo (Saved/Screenshots/Golmok/photo/<stamp>.png + .json)."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdPhotoShoot));
	FAutoConsoleCommandWithWorldAndArgs GCmdPhotoReset(TEXT("golmok.photo.reset"), TEXT("golmok.photo.reset: photo.json defaults, DOF off, character / overlay shown, entry pose."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdPhotoReset));
	FAutoConsoleCommandWithWorldAndArgs GCmdPhotoSet(TEXT("golmok.photo.set"),
		TEXT("golmok.photo.set <fov|ev|focus|fstop|roll|dof|char|overlay|mult> <value>: set one photo parameter (quantized / clamped)."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdPhotoSet));
} // namespace
