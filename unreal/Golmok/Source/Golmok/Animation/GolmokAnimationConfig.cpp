#include "Animation/GolmokAnimationConfig.h"

#include "Golmok.h"
#include "Animation/GolmokAnimationSubsystem.h"
#include "Animation/GolmokGaspCharacter.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Internationalization/Regex.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/Interface.h"
#include "UObject/SoftObjectPath.h"
#include <initializer_list>

namespace GolmokAnimation
{
	using FJsonObjectPtr = TSharedPtr<FJsonObject>;
	using FJsonValuePtr = TSharedPtr<FJsonValue>;

	// Asset path grammar (ASCII, like the roster): content_root relative "Folder/Name.Name" or "Folder/Name.Name_C".
	const TCHAR* RelativeObjectPattern = TEXT("([A-Za-z0-9_]+/)*[A-Za-z0-9_]+\\.[A-Za-z0-9_]+");
	const TCHAR* RelativeClassPattern = TEXT("([A-Za-z0-9_]+/)*[A-Za-z0-9_]+\\.[A-Za-z0-9_]+_C");
	const TCHAR* AbsoluteObjectPattern = TEXT("/Game/([A-Za-z0-9_]+/)+[A-Za-z0-9_]+\\.[A-Za-z0-9_]+");
	const TCHAR* AbsoluteClassPattern = TEXT("/Game/([A-Za-z0-9_]+/)+[A-Za-z0-9_]+\\.[A-Za-z0-9_]+_C");
	const TCHAR* ScriptClassPattern = TEXT("/Script/Golmok\\.[A-Za-z0-9_]+");
	const TCHAR* ProfileIdPattern = TEXT("[a-z][a-z0-9_]{0,15}");
	const TCHAR* CVarNamePattern = TEXT("[A-Za-z][A-Za-z0-9_.]{0,127}");
	constexpr int32 MaxProfiles = 8;
	constexpr int32 MaxDDCvars = 256;

	bool FullMatch(const FString& Text, const TCHAR* Pattern)
	{
		FRegexMatcher Matcher(FRegexPattern(Pattern), Text);
		return Matcher.FindNext() && Matcher.GetMatchBeginning() == 0 && Matcher.GetMatchEnding() == Text.Len();
	}

	FJsonValuePtr JsonField(const FJsonObjectPtr& Object, const TCHAR* Name)
	{
		return Object.IsValid() ? Object->TryGetField(FString(Name)) : nullptr;
	}

	FJsonObjectPtr JsonObjectField(const FJsonObjectPtr& Object, const TCHAR* Name)
	{
		const FJsonValuePtr Value = JsonField(Object, Name);
		return Value.IsValid() && Value->Type == EJson::Object ? Value->AsObject() : nullptr;
	}

	bool ExactKeys(const FJsonObjectPtr& Object, std::initializer_list<const TCHAR*> Names)
	{
		if (!Object.IsValid() || Object->Values.Num() != static_cast<int32>(Names.size()))
		{
			return false;
		}
		for (const TCHAR* Name : Names)
		{
			if (!JsonField(Object, Name).IsValid())
			{
				return false;
			}
		}
		return true;
	}

	bool JsonString(const FJsonObjectPtr& Object, const TCHAR* Name, FString& Out)
	{
		const FJsonValuePtr Value = JsonField(Object, Name);
		if (!Value.IsValid() || Value->Type != EJson::String)
		{
			return false;
		}
		Out = Value->AsString();
		return true;
	}

	bool JsonNumber(const FJsonObjectPtr& Object, const TCHAR* Name, double& Out)
	{
		const FJsonValuePtr Value = JsonField(Object, Name);
		if (!Value.IsValid() || Value->Type != EJson::Number)
		{
			return false;
		}
		Out = Value->AsNumber();
		return FMath::IsFinite(Out);
	}

	bool JsonBool(const FJsonObjectPtr& Object, const TCHAR* Name, bool& Out)
	{
		const FJsonValuePtr Value = JsonField(Object, Name);
		if (!Value.IsValid() || Value->Type != EJson::Boolean)
		{
			return false;
		}
		Out = Value->AsBool();
		return true;
	}

	bool IsJsonNull(const FJsonObjectPtr& Object, const TCHAR* Name)
	{
		const FJsonValuePtr Value = JsonField(Object, Name);
		return Value.IsValid() && Value->Type == EJson::Null;
	}

	/** Parser failure: "animation.json: <What>" (OutConfig untouched). */
	bool ConfigFail(FString& OutError, const FString& What)
	{
		OutError = FString::Printf(TEXT("animation.json: %s"), *What);
		return false;
	}

	/** Null or a string of the given pattern (visual override paths may also be absolute /Game/ paths). */
	bool OptionalPath(const FJsonObjectPtr& Object, const TCHAR* Name, const TCHAR* RelativePattern,
		const TCHAR* AbsolutePattern, FString& Out)
	{
		if (IsJsonNull(Object, Name))
		{
			Out.Reset();
			return true;
		}
		return JsonString(Object, Name, Out) && (FullMatch(Out, RelativePattern) || FullMatch(Out, AbsolutePattern));
	}

	bool ParseProfile(const FJsonObjectPtr& Object, FMovementProfile& Out)
	{
		return ExactKeys(Object, {TEXT("max_acceleration"), TEXT("braking_deceleration_walking"), TEXT("ground_friction"),
				TEXT("braking_friction_factor"), TEXT("use_separate_braking_friction"), TEXT("braking_friction")})
			&& JsonNumber(Object, TEXT("max_acceleration"), Out.MaxAcceleration)
			&& JsonNumber(Object, TEXT("braking_deceleration_walking"), Out.BrakingDecelerationWalking)
			&& JsonNumber(Object, TEXT("ground_friction"), Out.GroundFriction)
			&& JsonNumber(Object, TEXT("braking_friction_factor"), Out.BrakingFrictionFactor)
			&& JsonBool(Object, TEXT("use_separate_braking_friction"), Out.bUseSeparateBrakingFriction)
			&& JsonNumber(Object, TEXT("braking_friction"), Out.BrakingFriction)
			&& GolmokLocomotionMath::ValidateProfile(Out);
	}

	// ---- process-wide state (game thread) ----------------------------------------------------------------------

	struct FConfigOverrideState
	{
		bool bActive = false;
		FString Text;
		bool bIsolate = false;
	};

	FConfigOverrideState& ConfigOverrideState()
	{
		static FConfigOverrideState State;
		return State;
	}

	TOptional<EMode>& ConsoleModeStorage()
	{
		static TOptional<EMode> Mode;
		return Mode;
	}
}

const GolmokAnimation::FMovementProfile* GolmokAnimation::FConfig::FindProfile(const FString& Id) const
{
	const FNamedProfile* Found = Profiles.FindByPredicate([&Id](const FNamedProfile& Profile) { return Profile.Id == Id; });
	return Found && Found->bDefined ? &Found->Values : nullptr;
}

FString GolmokAnimation::FConfig::AssetPath(const FString& Relative) const
{
	if (Relative.IsEmpty() || Relative.StartsWith(TEXT("/")))
	{
		return Relative;
	}
	return ContentRoot + TEXT("/") + Relative;
}

const TCHAR* GolmokAnimation::ModeName(EMode Mode)
{
	return Mode == EMode::Gasp ? TEXT("gasp") : TEXT("abp");
}

bool GolmokAnimation::ParseModeName(const FString& Text, EMode& OutMode)
{
	if (Text == TEXT("abp"))
	{
		OutMode = EMode::Abp;
		return true;
	}
	if (Text == TEXT("gasp"))
	{
		OutMode = EMode::Gasp;
		return true;
	}
	return false;
}

bool GolmokAnimation::ParseConfig(const FString& Text, FConfig& OutConfig, FString& OutError)
{
	FJsonObjectPtr Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		return ConfigFail(OutError, TEXT("not a JSON object"));
	}
	if (!ExactKeys(Root, {TEXT("schema_version"), TEXT("mode"), TEXT("gasp"), TEXT("movement_profiles")}))
	{
		return ConfigFail(OutError, TEXT("root keys must be exactly schema_version, mode, gasp, movement_profiles"));
	}
	FConfig Candidate;
	double Version = 0.0;
	if (!JsonNumber(Root, TEXT("schema_version"), Version) || Version != 1.0)
	{
		return ConfigFail(OutError, TEXT("schema_version must be 1"));
	}
	FString ModeText;
	if (!JsonString(Root, TEXT("mode"), ModeText) || !ParseModeName(ModeText, Candidate.Mode))
	{
		return ConfigFail(OutError, TEXT("mode must be \"abp\" or \"gasp\""));
	}

	const FJsonObjectPtr Gasp = JsonObjectField(Root, TEXT("gasp"));
	if (!ExactKeys(Gasp, {TEXT("content_root"), TEXT("pawn_class"), TEXT("pawn_interface"), TEXT("anim_class"),
			TEXT("preview"), TEXT("movement_profile"), TEXT("state")}))
	{
		return ConfigFail(OutError, TEXT("gasp keys must be exactly content_root, pawn_class, pawn_interface, anim_class, preview, movement_profile, state"));
	}
	if (!JsonString(Gasp, TEXT("content_root"), Candidate.ContentRoot)
		|| (Candidate.ContentRoot != TEXT("/Game/GASP") && Candidate.ContentRoot != TEXT("/Game")))
	{
		return ConfigFail(OutError, TEXT("gasp.content_root must be \"/Game/GASP\" or \"/Game\""));
	}
	if (!JsonString(Gasp, TEXT("pawn_class"), Candidate.PawnClass)
		|| !(FullMatch(Candidate.PawnClass, AbsoluteClassPattern) || FullMatch(Candidate.PawnClass, ScriptClassPattern)))
	{
		return ConfigFail(OutError, TEXT("gasp.pawn_class must be /Game/<Folder>/<Name>.<Name>_C or /Script/Golmok.<Class>"));
	}
	if (!JsonString(Gasp, TEXT("pawn_interface"), Candidate.PawnInterface) || !FullMatch(Candidate.PawnInterface, RelativeClassPattern))
	{
		return ConfigFail(OutError, TEXT("gasp.pawn_interface must be a content_root relative <Folder>/<Name>.<Name>_C"));
	}
	if (!JsonString(Gasp, TEXT("anim_class"), Candidate.AnimClass) || !FullMatch(Candidate.AnimClass, RelativeClassPattern))
	{
		return ConfigFail(OutError, TEXT("gasp.anim_class must be a content_root relative <Folder>/<Name>.<Name>_C"));
	}

	const FJsonObjectPtr Preview = JsonObjectField(Gasp, TEXT("preview"));
	if (!ExactKeys(Preview, {TEXT("source_mesh"), TEXT("visual_mesh"), TEXT("visual_anim_class")})
		|| !JsonString(Preview, TEXT("source_mesh"), Candidate.PreviewSourceMesh)
		|| !FullMatch(Candidate.PreviewSourceMesh, RelativeObjectPattern)
		|| !OptionalPath(Preview, TEXT("visual_mesh"), RelativeObjectPattern, AbsoluteObjectPattern, Candidate.PreviewVisualMesh)
		|| !OptionalPath(Preview, TEXT("visual_anim_class"), RelativeClassPattern, AbsoluteClassPattern, Candidate.PreviewVisualAnimClass)
		|| Candidate.PreviewVisualMesh.IsEmpty() != Candidate.PreviewVisualAnimClass.IsEmpty())
	{
		return ConfigFail(OutError, TEXT("gasp.preview must be {source_mesh, visual_mesh, visual_anim_class} with both visual fields null or both paths"));
	}

	const FJsonObjectPtr StateObject = JsonObjectField(Gasp, TEXT("state"));
	if (!ExactKeys(StateObject, {TEXT("just_landed_seconds"), TEXT("teleport_jump_cm"), TEXT("reinit_anim_on_teleport")})
		|| !JsonNumber(StateObject, TEXT("just_landed_seconds"), Candidate.JustLandedSeconds)
		|| !JsonNumber(StateObject, TEXT("teleport_jump_cm"), Candidate.TeleportJumpCm)
		|| !JsonBool(StateObject, TEXT("reinit_anim_on_teleport"), Candidate.bReinitAnimOnTeleport)
		|| !GolmokLocomotionMath::ValidateStateSettings(Candidate.JustLandedSeconds, Candidate.TeleportJumpCm))
	{
		return ConfigFail(OutError, TEXT("gasp.state must be {just_landed_seconds 0.05-2, teleport_jump_cm 20-1000, reinit_anim_on_teleport bool}"));
	}

	const FJsonObjectPtr Profiles = JsonObjectField(Root, TEXT("movement_profiles"));
	if (!Profiles.IsValid() || Profiles->Values.Num() < 1 || Profiles->Values.Num() > MaxProfiles)
	{
		return ConfigFail(OutError, FString::Printf(TEXT("movement_profiles must be an object with 1-%d entries"), MaxProfiles));
	}
	for (const TPair<FString, FJsonValuePtr>& Pair : Profiles->Values)
	{
		FNamedProfile Named;
		Named.Id = Pair.Key;
		if (!FullMatch(Named.Id, ProfileIdPattern) || !Pair.Value.IsValid())
		{
			return ConfigFail(OutError, FString::Printf(TEXT("movement_profiles: invalid id '%s'"), *Named.Id));
		}
		if (Pair.Value->Type != EJson::Null)
		{
			if (Pair.Value->Type != EJson::Object || !ParseProfile(Pair.Value->AsObject(), Named.Values))
			{
				return ConfigFail(OutError, FString::Printf(TEXT("movement_profiles.%s: expected null or the six fields in range"), *Named.Id));
			}
			Named.bDefined = true;
		}
		Candidate.Profiles.Add(MoveTemp(Named));
	}
	if (!JsonString(Gasp, TEXT("movement_profile"), Candidate.MovementProfileId) || !Candidate.FindProfile(Candidate.MovementProfileId))
	{
		return ConfigFail(OutError, FString::Printf(TEXT("gasp.movement_profile '%s' is missing or null"), *Candidate.MovementProfileId));
	}

	OutConfig = MoveTemp(Candidate);
	OutError.Reset();
	return true;
}

FString GolmokAnimation::ConfigFilePath()
{
	return FPaths::Combine(FPaths::ProjectConfigDir(), TEXT("Golmok/animation.json"));
}

FString GolmokAnimation::LocalDir()
{
	return FPaths::Combine(FPaths::ProjectConfigDir(), TEXT("Golmok/local"));
}

FString GolmokAnimation::DDCvarFilePath()
{
	return FPaths::Combine(LocalDir(), TEXT("gasp_ddcvars.json"));
}

FString GolmokAnimation::ManifestFilePath()
{
	return FPaths::Combine(LocalDir(), TEXT("gasp_manifest.json"));
}

FString GolmokAnimation::TagFilePath()
{
	return FPaths::Combine(FPaths::ProjectConfigDir(), TEXT("Tags/GASP.ini"));
}

bool GolmokAnimation::LoadConfig(FConfig& OutConfig, FString& OutError)
{
	const FConfigOverrideState& Override = ConfigOverrideState();
	if (Override.bActive)
	{
		return ParseConfig(Override.Text, OutConfig, OutError);
	}
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *ConfigFilePath()))
	{
		OutError = TEXT("animation.json: cannot read Config/Golmok/animation.json");
		return false;
	}
	return ParseConfig(Text, OutConfig, OutError);
}

GolmokAnimation::FScopedConfigOverride::FScopedConfigOverride(const FString& Text, bool bIsolateModeSources)
{
	FConfigOverrideState& State = ConfigOverrideState();
	bHadPrevious = State.bActive;
	PreviousText = State.Text;
	bPreviousIsolate = State.bIsolate;
	State.bActive = true;
	State.Text = Text;
	State.bIsolate = bIsolateModeSources;
}

GolmokAnimation::FScopedConfigOverride::~FScopedConfigOverride()
{
	FConfigOverrideState& State = ConfigOverrideState();
	State.bActive = bHadPrevious;
	State.Text = PreviousText;
	State.bIsolate = bPreviousIsolate;
}

GolmokAnimation::FModeResolution GolmokAnimation::ComputeEffectiveMode(const TCHAR* CommandLine,
	const TOptional<EMode>& ConsoleOverride, bool bConfigValid, EMode FileMode)
{
	FModeResolution Result;
	Result.bConfigValid = bConfigValid;
	FString Value;
	EMode Parsed = EMode::Abp;
	if (CommandLine && FParse::Value(CommandLine, TEXT("GolmokAnim="), Value) && ParseModeName(Value, Parsed))
	{
		Result.Mode = Parsed;
		Result.Source = TEXT("command line");
	}
	else if (ConsoleOverride.IsSet())
	{
		Result.Mode = ConsoleOverride.GetValue();
		Result.Source = TEXT("console");
	}
	else if (bConfigValid)
	{
		Result.Mode = FileMode;
		Result.Source = TEXT("animation.json");
	}
	else
	{
		Result.Mode = EMode::Abp;
		Result.Source = TEXT("animation.json invalid");
	}
	return Result;
}

GolmokAnimation::FModeResolution GolmokAnimation::GetEffectiveMode()
{
	FConfig Config;
	FString Error;
	const bool bValid = LoadConfig(Config, Error);
	const bool bIsolate = ConfigOverrideState().bActive && ConfigOverrideState().bIsolate;
	FModeResolution Result = ComputeEffectiveMode(bIsolate ? nullptr : FCommandLine::Get(),
		bIsolate ? TOptional<EMode>() : ConsoleModeStorage(), bValid, Config.Mode);
	Result.ConfigError = Error;
	return Result;
}

void GolmokAnimation::SetConsoleModeOverride(const TOptional<EMode>& Mode)
{
	ConsoleModeStorage() = Mode;
}

TOptional<GolmokAnimation::EMode> GolmokAnimation::GetConsoleModeOverride()
{
	return ConsoleModeStorage();
}

UClass* GolmokAnimation::LoadClassIfPresent(const FString& Path, const UClass* BaseClass)
{
	if (Path.IsEmpty())
	{
		return nullptr;
	}
	const FSoftClassPath SoftPath(Path);
	if (!SoftPath.IsValid())
	{
		return nullptr;
	}
	UClass* Class = SoftPath.ResolveClass();
	if (!Class)
	{
		const FString Package = SoftPath.GetLongPackageName();
		if (Package.IsEmpty() || Package.StartsWith(TEXT("/Script/")) || !FPackageName::DoesPackageExist(Package))
		{
			return nullptr;
		}
		Class = SoftPath.TryLoadClass<UObject>();
	}
	return Class && (!BaseClass || Class->IsChildOf(BaseClass)) ? Class : nullptr;
}

UObject* GolmokAnimation::LoadObjectIfPresent(const FString& Path, const UClass* ObjectClass)
{
	if (Path.IsEmpty())
	{
		return nullptr;
	}
	const FSoftObjectPath SoftPath(Path);
	if (!SoftPath.IsValid())
	{
		return nullptr;
	}
	UObject* Object = SoftPath.ResolveObject();
	if (!Object)
	{
		const FString Package = SoftPath.GetLongPackageName();
		if (Package.IsEmpty() || Package.StartsWith(TEXT("/Script/")) || !FPackageName::DoesPackageExist(Package))
		{
			return nullptr;
		}
		Object = SoftPath.TryLoad();
	}
	return Object && (!ObjectClass || Object->IsA(ObjectClass)) ? Object : nullptr;
}

bool GolmokAnimation::PawnClassSupportsGasp(const FConfig& Config, const UClass* PawnClass, FString& OutReason)
{
	if (!PawnClass || !PawnClass->IsChildOf(AGolmokGaspCharacter::StaticClass()))
	{
		OutReason = FString::Printf(TEXT("pawn class %s is not an AGolmokGaspCharacter"),
			PawnClass ? *PawnClass->GetPathName() : TEXT("(none)"));
		return false;
	}
	const FString InterfacePath = Config.AssetPath(Config.PawnInterface);
	UClass* Interface = LoadClassIfPresent(InterfacePath, UInterface::StaticClass());
	if (!Interface)
	{
		OutReason = FString::Printf(TEXT("GASP pawn interface missing (%s)"), *InterfacePath);
		return false;
	}
	if (!PawnClass->ImplementsInterface(Interface))
	{
		OutReason = FString::Printf(TEXT("pawn class %s does not implement %s (19b)"), *PawnClass->GetPathName(), *InterfacePath);
		return false;
	}
	OutReason.Reset();
	return true;
}

GolmokAnimation::FPawnResolution GolmokAnimation::ResolvePawn(bool bIsPlayer, UClass* SuperClass)
{
	FPawnResolution Result;
	Result.PawnClass = SuperClass;
	FConfig Config;
	FString Error;
	const bool bValid = LoadConfig(Config, Error);
	const bool bIsolate = ConfigOverrideState().bActive && ConfigOverrideState().bIsolate;
	Result.Mode = ComputeEffectiveMode(bIsolate ? nullptr : FCommandLine::Get(),
		bIsolate ? TOptional<EMode>() : ConsoleModeStorage(), bValid, Config.Mode);
	Result.Mode.ConfigError = Error;

	// Rule 1. An explicit abp (command line / console / valid file) never reads further.
	if (!bIsPlayer || (Result.Mode.Mode == EMode::Abp && (bValid || Result.Mode.Source != TEXT("animation.json invalid"))))
	{
		return Result;
	}
	Result.bFallback = true;
	// Rule 2.
	if (!bValid)
	{
		Result.Reason = Error;
		return Result;
	}
	// Rule 3.
	UClass* Pawn = LoadClassIfPresent(Config.PawnClass, APawn::StaticClass());
	if (!Pawn)
	{
		Result.Reason = FString::Printf(TEXT("GASP pawn class missing — add-gasp / 19b (%s)"), *Config.PawnClass);
		return Result;
	}
	// Rules 4-5.
	if (!PawnClassSupportsGasp(Config, Pawn, Result.Reason))
	{
		return Result;
	}
	// Rule 6.
	Result.bFallback = false;
	Result.PawnClass = Pawn;
	return Result;
}

UClass* GolmokAnimation::ResolvePlayerPawnClass(AController* InController, UClass* SuperClass)
{
	const FPawnResolution Resolution = ResolvePawn(Cast<APlayerController>(InController) != nullptr, SuperClass);
	UWorld* World = InController ? InController->GetWorld() : nullptr;
	if (UGolmokAnimationSubsystem* Subsystem = World ? World->GetSubsystem<UGolmokAnimationSubsystem>() : nullptr)
	{
		Subsystem->RecordResolution(Resolution);
	}
	else if (Resolution.bFallback)
	{
		UE_LOG(LogGolmok, Warning, TEXT("anim: falling back to ABP pawn (%s)"), *Resolution.Reason);
	}
	return Resolution.PawnClass;
}

bool GolmokAnimation::RequiresGaspPawn(const UClass* AnimClass)
{
	FConfig Config;
	FString Error;
	if (!AnimClass || !LoadConfig(Config, Error))
	{
		return false;
	}
	const FString GaspAnimPath = Config.AssetPath(Config.AnimClass);
	for (const UClass* Class = AnimClass; Class; Class = Class->GetSuperClass())
	{
		if (Class->GetPathName() == GaspAnimPath)
		{
			return true;
		}
	}
	return false;
}

bool GolmokAnimation::PawnSupportsGasp(const APawn* Pawn)
{
	FConfig Config;
	FString Error;
	FString Reason;
	return Pawn && LoadConfig(Config, Error) && PawnClassSupportsGasp(Config, Pawn->GetClass(), Reason);
}

bool GolmokAnimation::ParseDDCvars(const FString& Text, TArray<FDDCvar>& OutVars, FString& OutError)
{
	FJsonObjectPtr Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	double Version = 0.0;
	FString Source;
	if (!FJsonSerializer::Deserialize(Reader, Root) || !ExactKeys(Root, {TEXT("schema_version"), TEXT("source"), TEXT("cvars")})
		|| !JsonNumber(Root, TEXT("schema_version"), Version) || Version != 1.0 || !JsonString(Root, TEXT("source"), Source))
	{
		OutError = TEXT("gasp_ddcvars.json: expected {schema_version 1, source, cvars}");
		return false;
	}
	const FJsonValuePtr List = JsonField(Root, TEXT("cvars"));
	if (!List.IsValid() || List->Type != EJson::Array || List->AsArray().Num() > MaxDDCvars)
	{
		OutError = FString::Printf(TEXT("gasp_ddcvars.json: cvars must be an array of at most %d"), MaxDDCvars);
		return false;
	}
	TArray<FDDCvar> Candidate;
	for (const FJsonValuePtr& Item : List->AsArray())
	{
		const FJsonObjectPtr Object = Item.IsValid() && Item->Type == EJson::Object ? Item->AsObject() : nullptr;
		FDDCvar Var;
		FString Type;
		const FJsonValuePtr Default = JsonField(Object, TEXT("default"));
		bool bOk = ExactKeys(Object, {TEXT("name"), TEXT("type"), TEXT("default"), TEXT("help")})
			&& JsonString(Object, TEXT("name"), Var.Name) && FullMatch(Var.Name, CVarNamePattern)
			&& JsonString(Object, TEXT("type"), Type) && JsonString(Object, TEXT("help"), Var.Help) && Default.IsValid();
		if (bOk && Type == TEXT("bool"))
		{
			Var.Type = EDDCvarType::Bool;
			bOk = Default->Type == EJson::Boolean;
			Var.Default = bOk && Default->AsBool() ? 1.0 : 0.0;
		}
		else if (bOk && (Type == TEXT("int") || Type == TEXT("float")))
		{
			Var.Type = Type == TEXT("int") ? EDDCvarType::Int : EDDCvarType::Float;
			bOk = Default->Type == EJson::Number && FMath::IsFinite(Default->AsNumber());
			Var.Default = bOk ? Default->AsNumber() : 0.0;
			bOk = bOk && (Var.Type == EDDCvarType::Float || FMath::Abs(Var.Default) <= static_cast<double>(MAX_int32));
		}
		else
		{
			bOk = false;
		}
		if (!bOk || Candidate.ContainsByPredicate([&Var](const FDDCvar& Other) { return Other.Name.Equals(Var.Name, ESearchCase::IgnoreCase); }))
		{
			OutError = FString::Printf(TEXT("gasp_ddcvars.json: invalid or duplicate entry at index %d (%s)"), Candidate.Num(), *Var.Name);
			return false;
		}
		Candidate.Add(MoveTemp(Var));
	}
	OutVars = MoveTemp(Candidate);
	OutError.Reset();
	return true;
}

int32 GolmokAnimation::RegisterDDCvars(const TArray<FDDCvar>& Vars, int32& OutPresent)
{
	IConsoleManager& Manager = IConsoleManager::Get();
	int32 Added = 0;
	OutPresent = 0;
	for (const FDDCvar& Var : Vars)
	{
		if (!Manager.FindConsoleObject(*Var.Name))
		{
			IConsoleVariable* Registered = nullptr;
			switch (Var.Type)
			{
			case EDDCvarType::Bool:
				Registered = Manager.RegisterConsoleVariable(*Var.Name, Var.Default != 0.0, *Var.Help, ECVF_Default);
				break;
			case EDDCvarType::Int:
				Registered = Manager.RegisterConsoleVariable(*Var.Name, static_cast<int32>(Var.Default), *Var.Help, ECVF_Default);
				break;
			case EDDCvarType::Float:
				Registered = Manager.RegisterConsoleVariable(*Var.Name, static_cast<float>(Var.Default), *Var.Help, ECVF_Default);
				break;
			}
			Added += Registered ? 1 : 0;
		}
		OutPresent += Manager.FindConsoleObject(*Var.Name) ? 1 : 0;
	}
	return Added;
}
