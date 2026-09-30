#include "Animation/GolmokAnimationSubsystem.h"

#include "Golmok.h"
#include "Animation/AnimInstance.h"
#include "Animation/GolmokGaspCharacter.h"
#include "Animation/GolmokLocomotionStateComponent.h"
#include "Characters/GolmokCharacterSubsystem.h"
#include "Components/SkeletalMeshComponent.h"
#include "Debug/GolmokDebugSubsystem.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Photo/GolmokPhotoModeSubsystem.h"
#include "Player/GolmokCharacter.h"
#include "UObject/Interface.h"

namespace GolmokAnimation
{
	const TCHAR* MovementModeLabel(EGolmokMovementMode Mode)
	{
		return Mode == EGolmokMovementMode::InAir ? TEXT("air") : TEXT("ground");
	}

	FString DescribeState(const UGolmokLocomotionStateComponent& Component)
	{
		const FGolmokLocomotionState& S = Component.GetLocomotionState();
		const double Since = Component.GetSecondsSinceLanding();
		const FString Land = Since >= 0.0 ? FString::Printf(TEXT("land %.2fs %.0f"), Since, S.LandVelocity.Z) : FString(TEXT("land -"));
		return FString::Printf(TEXT("%s %s %s | intent %.2f | %s"), MovementModeLabel(S.MovementMode),
			S.Gait == EGolmokGait::Run ? TEXT("run") : TEXT("walk"), S.MovingState == EGolmokMovingState::Moving ? TEXT("moving") : TEXT("idle"),
			S.InputIntent.Size2D(), *Land);
	}

	FString DescribeMovement(const UCharacterMovementComponent& Movement)
	{
		return FString::Printf(TEXT("max_acceleration %.0f braking_deceleration_walking %.0f ground_friction %.2f braking_friction_factor %.2f use_separate_braking_friction %s braking_friction %.2f"),
			Movement.MaxAcceleration, Movement.BrakingDecelerationWalking, Movement.GroundFriction, Movement.BrakingFrictionFactor,
			Movement.bUseSeparateBrakingFriction ? TEXT("true") : TEXT("false"), Movement.BrakingFriction);
	}

	const TCHAR* YesNo(bool bValue)
	{
		return bValue ? TEXT("yes") : TEXT("no");
	}

	void CmdAnim(const TArray<FString>& Args, UWorld* World)
	{
		UGolmokAnimationSubsystem* Subsystem = World ? World->GetSubsystem<UGolmokAnimationSubsystem>() : nullptr;
		FString Message = TEXT("usage: golmok.anim status | mode <abp|gasp|config> | profile <id> | preview [off]");
		if (Args.Num() == 2 && Args[0] == TEXT("mode"))
		{
			// Process-wide; works without a game world too (the next PIE uses it).
			if (Subsystem)
			{
				Subsystem->SetMode(Args[1], Message);
			}
			else
			{
				EMode Mode = EMode::Abp;
				if (Args[1] == TEXT("config"))
				{
					SetConsoleModeOverride(TOptional<EMode>());
					Message = TEXT("mode follows animation.json (applies to the next PIE / pawn spawn)");
				}
				else if (ParseModeName(Args[1], Mode))
				{
					SetConsoleModeOverride(Mode);
					Message = FString::Printf(TEXT("mode %s (applies to the next PIE / pawn spawn)"), ModeName(Mode));
				}
			}
		}
		else if (!Subsystem)
		{
			Message = TEXT("no supported game world");
		}
		else if (Args.Num() == 0 || (Args.Num() == 1 && Args[0] == TEXT("status")))
		{
			Message = Subsystem->DescribeStatus();
		}
		else if (Args.Num() == 2 && Args[0] == TEXT("profile"))
		{
			Subsystem->ApplyProfile(Args[1], Message);
		}
		else if (Args.Num() >= 1 && Args.Num() <= 2 && Args[0] == TEXT("preview") && (Args.Num() == 1 || Args[1] == TEXT("off")))
		{
			Subsystem->ApplyPreview(Args.Num() == 1, Message);
		}
		UE_LOG(LogGolmok, Log, TEXT("golmok.anim: %s"), *Message);
	}

	FAutoConsoleCommandWithWorldAndArgs GCmdAnim(TEXT("golmok.anim"),
		TEXT("golmok.anim status | mode <abp|gasp|config> | profile <id> | preview [off]: animation mode (WP-19, D-021)."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdAnim));
}

bool UGolmokAnimationSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UGolmokAnimationSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Collection.InitializeDependency<UGolmokDebugSubsystem>();
	Super::Initialize(Collection);
	RegisterLocalDDCvars();
	Debug = GetWorld()->GetSubsystem<UGolmokDebugSubsystem>();
	if (Debug.IsValid())
	{
		const TWeakObjectPtr<UGolmokAnimationSubsystem> WeakThis(this);
		HudHandle = Debug->AddExtraHudLineProvider([WeakThis]() { return WeakThis.IsValid() ? WeakThis->BuildHudLine() : FString(); });
	}
	StartPreload();
}

void UGolmokAnimationSubsystem::Deinitialize()
{
	if (Debug.IsValid())
	{
		Debug->RemoveExtraHudLineProvider(HudHandle);
	}
	HudHandle.Reset();
	Debug.Reset();
	if (PreloadHandle.IsValid())
	{
		PreloadHandle->CancelHandle();
		PreloadHandle.Reset();
	}
	Super::Deinitialize();
}

void UGolmokAnimationSubsystem::RegisterLocalDDCvars()
{
	const FString Path = GolmokAnimation::DDCvarFilePath();
	if (!FPaths::FileExists(Path))
	{
		return; // no add-gasp on this checkout: nothing to register
	}
	FString Text;
	TArray<GolmokAnimation::FDDCvar> Vars;
	if (!FFileHelper::LoadFileToString(Text, *Path) || !GolmokAnimation::ParseDDCvars(Text, Vars, DDCvarError))
	{
		if (DDCvarError.IsEmpty())
		{
			DDCvarError = TEXT("gasp_ddcvars.json: unreadable");
		}
		UE_LOG(LogGolmok, Warning, TEXT("anim: %s (re-run tools/ue/add-gasp.ps1)"), *DDCvarError);
		return;
	}
	DDCvarCount = Vars.Num();
	DDCvarAdded = GolmokAnimation::RegisterDDCvars(Vars, DDCvarPresent);
	UE_LOG(LogGolmok, Log, TEXT("anim: DDCvars %d/%d present (%d registered now)"), DDCvarPresent, DDCvarCount, DDCvarAdded);
}

void UGolmokAnimationSubsystem::StartPreload()
{
	const GolmokAnimation::FModeResolution Mode = GolmokAnimation::GetEffectiveMode();
	GolmokAnimation::FConfig Config;
	FString Error;
	if (Mode.Mode != GolmokAnimation::EMode::Gasp || !GolmokAnimation::LoadConfig(Config, Error))
	{
		return;
	}
	const FSoftObjectPath PawnPath(Config.PawnClass);
	const FString Package = PawnPath.GetLongPackageName();
	if (!PawnPath.IsValid() || PawnPath.ResolveObject() || Package.StartsWith(TEXT("/Script/")) || !FPackageName::DoesPackageExist(Package))
	{
		return; // loaded already, native, or absent (the spawn falls back and says why)
	}
	FStreamableDelegate Done;
	PreloadHandle = Streamable.RequestAsyncLoad(PawnPath, Done, FStreamableManager::DefaultAsyncLoadPriority,
		/*bManageActiveHandle*/ false, /*bStartStalled*/ false, TEXT("GolmokAnimation pawn preload"));
}

void UGolmokAnimationSubsystem::RecordResolution(const GolmokAnimation::FPawnResolution& Resolution)
{
	++Resolutions;
	LastResolvedClass = Resolution.PawnClass ? Resolution.PawnClass->GetPathName() : FString(TEXT("(none)"));
	if (!Resolution.bFallback)
	{
		return;
	}
	LastFallbackReason = Resolution.Reason;
	if (!bFallbackWarned)
	{
		bFallbackWarned = true;
		++FallbackWarnings;
		UE_LOG(LogGolmok, Warning, TEXT("anim: falling back to ABP pawn (%s)"), *Resolution.Reason);
	}
}

AGolmokGaspCharacter* UGolmokAnimationSubsystem::GetActiveGaspCharacter(FString& OutMessage) const
{
	UWorld* World = GetWorld();
	APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	AGolmokGaspCharacter* Character = PC ? Cast<AGolmokGaspCharacter>(PC->GetPawn()) : nullptr;
	if (!Character)
	{
		OutMessage = TEXT("the player pawn is not a GASP pawn (mode abp or fallback; see golmok.anim status)");
		return nullptr;
	}
	if (UGameplayStatics::IsGamePaused(World) || PC->GetViewTarget() != Character || UGolmokPhotoModeSubsystem::IsActiveIn(World))
	{
		OutMessage = TEXT("requires an active character view; exit photo/path/pause first");
		return nullptr;
	}
	return Character;
}

bool UGolmokAnimationSubsystem::SetMode(const FString& Argument, FString& OutMessage)
{
	GolmokAnimation::EMode Mode = GolmokAnimation::EMode::Abp;
	if (Argument == TEXT("config"))
	{
		GolmokAnimation::SetConsoleModeOverride(TOptional<GolmokAnimation::EMode>());
	}
	else if (GolmokAnimation::ParseModeName(Argument, Mode))
	{
		GolmokAnimation::SetConsoleModeOverride(Mode);
	}
	else
	{
		OutMessage = TEXT("usage: golmok.anim mode <abp|gasp|config>");
		return false;
	}
	const GolmokAnimation::FModeResolution Effective = GolmokAnimation::GetEffectiveMode();
	OutMessage = FString::Printf(TEXT("mode %s (%s); restart PIE to respawn the pawn"), GolmokAnimation::ModeName(Effective.Mode), *Effective.Source);
	return true;
}

bool UGolmokAnimationSubsystem::ApplyProfile(const FString& Id, FString& OutMessage)
{
	AGolmokGaspCharacter* Character = GetActiveGaspCharacter(OutMessage);
	GolmokAnimation::FConfig Config;
	FString Error;
	if (!Character)
	{
		return false;
	}
	if (!GolmokAnimation::LoadConfig(Config, Error))
	{
		OutMessage = Error;
		return false;
	}
	const GolmokAnimation::FMovementProfile* Profile = Config.FindProfile(Id);
	if (!Profile || !Character->ApplyMovementProfile(Id, *Profile))
	{
		OutMessage = FString::Printf(TEXT("profile '%s' is unknown or null in animation.json"), *Id);
		return false;
	}
	OutMessage = FString::Printf(TEXT("profile %s: %s (not saved)"), *Id, *GolmokAnimation::DescribeMovement(*Character->GetCharacterMovement()));
	return true;
}

bool UGolmokAnimationSubsystem::ApplyPreview(bool bOn, FString& OutMessage)
{
	AGolmokGaspCharacter* Character = GetActiveGaspCharacter(OutMessage);
	if (!Character)
	{
		return false;
	}
	if (!bOn)
	{
		Character->ClearVisualOverride();
		FString RosterMessage = TEXT("no roster");
		if (UGolmokCharacterSubsystem* Roster = GetWorld()->GetSubsystem<UGolmokCharacterSubsystem>())
		{
			const FString Id = Roster->GetCurrentId().IsEmpty() ? Roster->GetRoster().DefaultId : Roster->GetCurrentId();
			Roster->SelectCharacter(Id, RosterMessage);
		}
		OutMessage = FString::Printf(TEXT("preview off; roster: %s"), *RosterMessage);
		return true;
	}
	GolmokAnimation::FConfig Config;
	FString Error;
	if (!GolmokAnimation::LoadConfig(Config, Error))
	{
		OutMessage = Error;
		return false;
	}
	const FString SourcePath = Config.AssetPath(Config.PreviewSourceMesh);
	const FString AnimPath = Config.AssetPath(Config.AnimClass);
	USkeletalMesh* Source = Cast<USkeletalMesh>(GolmokAnimation::LoadObjectIfPresent(SourcePath, USkeletalMesh::StaticClass()));
	UClass* AnimClass = GolmokAnimation::LoadClassIfPresent(AnimPath, UAnimInstance::StaticClass());
	if (!Source || !AnimClass)
	{
		OutMessage = FString::Printf(TEXT("preview assets missing (source %s: %s, anim %s: %s) - add-gasp / 19b"),
			*SourcePath, GolmokAnimation::YesNo(Source != nullptr), *AnimPath, GolmokAnimation::YesNo(AnimClass != nullptr));
		return false;
	}
	Character->GetMesh()->SetSkeletalMesh(Source);
	Character->GetMesh()->SetAnimInstanceClass(AnimClass);
	FString Visual = TEXT("no visual mesh");
	if (!Config.PreviewVisualMesh.IsEmpty())
	{
		const FString VisualMeshPath = Config.AssetPath(Config.PreviewVisualMesh);
		const FString VisualAnimPath = Config.AssetPath(Config.PreviewVisualAnimClass);
		USkeletalMesh* VisualMesh = Cast<USkeletalMesh>(GolmokAnimation::LoadObjectIfPresent(VisualMeshPath, USkeletalMesh::StaticClass()));
		UClass* VisualAnim = GolmokAnimation::LoadClassIfPresent(VisualAnimPath, UAnimInstance::StaticClass());
		FString VisualError;
		if (Character->SetVisualOverride(VisualMesh, VisualAnim, VisualError))
		{
			Visual = FString::Printf(TEXT("visual %s + %s"), *VisualMeshPath, *VisualAnimPath);
		}
		else
		{
			Visual = FString::Printf(TEXT("visual mesh not applied (%s: %s)"), *VisualMeshPath, *VisualError);
		}
	}
	else
	{
		Character->ClearVisualOverride();
	}
	OutMessage = FString::Printf(TEXT("preview on: %s + %s, %s (debug only; the next roster apply replaces it)"), *SourcePath, *AnimPath, *Visual);
	return true;
}

FString UGolmokAnimationSubsystem::BuildHudLine() const
{
	const UWorld* World = GetWorld();
	const APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	const AGolmokGaspCharacter* Character = PC ? Cast<AGolmokGaspCharacter>(PC->GetPawn()) : nullptr;
	if (Character && Character->GetLocomotionStateComponent())
	{
		const FString Profile = Character->GetAppliedProfileId().IsEmpty() ? FString(TEXT("-")) : Character->GetAppliedProfileId();
		return FString::Printf(TEXT("anim: gasp %s | %s"), *Profile, *GolmokAnimation::DescribeState(*Character->GetLocomotionStateComponent()));
	}
	return LastFallbackReason.IsEmpty() ? FString(TEXT("anim: abp")) : FString::Printf(TEXT("anim: abp (fallback: %s)"), *LastFallbackReason);
}

FString UGolmokAnimationSubsystem::DescribeStatus() const
{
	const GolmokAnimation::FModeResolution Mode = GolmokAnimation::GetEffectiveMode();
	GolmokAnimation::FConfig Config;
	FString Error;
	const bool bValid = GolmokAnimation::LoadConfig(Config, Error);
	FString Out = FString::Printf(TEXT("mode %s (%s) | animation.json %s"), GolmokAnimation::ModeName(Mode.Mode), *Mode.Source,
		bValid ? TEXT("ok") : *Error);

	const GolmokAnimation::FPawnResolution Resolution = GolmokAnimation::ResolvePawn(true, AGolmokCharacter::StaticClass());
	Out += FString::Printf(TEXT("\n  pawn: %s%s | last spawn: %s"),
		Resolution.PawnClass ? *Resolution.PawnClass->GetPathName() : TEXT("(none)"),
		Resolution.bFallback ? *FString::Printf(TEXT(" (fallback: %s)"), *Resolution.Reason) : TEXT(""),
		LastResolvedClass.IsEmpty() ? TEXT("-") : *LastResolvedClass);

	if (bValid)
	{
		const FString AnimPath = Config.AssetPath(Config.AnimClass);
		const FString InterfacePath = Config.AssetPath(Config.PawnInterface);
		Out += FString::Printf(TEXT("\n  gasp install: manifest %s | content_root %s | abp %s (%s) | bpi %s (%s) | pawn bp %s (%s)"),
			GolmokAnimation::YesNo(FPaths::FileExists(GolmokAnimation::ManifestFilePath())), *Config.ContentRoot,
			GolmokAnimation::YesNo(GolmokAnimation::LoadClassIfPresent(AnimPath, UAnimInstance::StaticClass()) != nullptr), *AnimPath,
			GolmokAnimation::YesNo(GolmokAnimation::LoadClassIfPresent(InterfacePath, UInterface::StaticClass()) != nullptr), *InterfacePath,
			GolmokAnimation::YesNo(GolmokAnimation::LoadClassIfPresent(Config.PawnClass, AGolmokGaspCharacter::StaticClass()) != nullptr), *Config.PawnClass);
	}
	Out += FString::Printf(TEXT("\n  ddcvars %d/%d present (expected 27; %d registered by Golmok)%s | tags file %s"), DDCvarPresent, DDCvarCount, DDCvarAdded,
		DDCvarError.IsEmpty() ? TEXT("") : *FString::Printf(TEXT(" error: %s"), *DDCvarError),
		GolmokAnimation::YesNo(FPaths::FileExists(GolmokAnimation::TagFilePath())));

	const UWorld* World = GetWorld();
	const APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	const APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	Out += FString::Printf(TEXT("\n  current pawn: %s"), Pawn ? *Pawn->GetClass()->GetPathName() : TEXT("(none)"));
	if (const AGolmokGaspCharacter* Character = Cast<AGolmokGaspCharacter>(Pawn))
	{
		if (const UGolmokLocomotionStateComponent* State = Character->GetLocomotionStateComponent())
		{
			Out += FString::Printf(TEXT("\n  state: %s | teleports %d reinit %d foot events %d | visual override %s"),
				*GolmokAnimation::DescribeState(*State), State->GetTeleportCount(), State->GetAnimReinitCount(), State->GetFootEventCount(),
				GolmokAnimation::YesNo(Character->HasVisualOverride()));
		}
		Out += FString::Printf(TEXT("\n  profile %s: %s"), Character->GetAppliedProfileId().IsEmpty() ? TEXT("-") : *Character->GetAppliedProfileId(),
			*GolmokAnimation::DescribeMovement(*Character->GetCharacterMovement()));
	}
	else if (const ACharacter* Other = Cast<ACharacter>(Pawn))
	{
		Out += FString::Printf(TEXT("\n  profile (not applied to ABP pawns): %s"), *GolmokAnimation::DescribeMovement(*Other->GetCharacterMovement()));
	}
	return Out;
}
