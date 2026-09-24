#include "Player/GolmokPlayerController.h"

#include "Golmok.h"

#include "Debug/GolmokDebugSubsystem.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "Lighting/GolmokTimeOfDay.h"

AGolmokTimeOfDay* AGolmokPlayerController::GetTimeOfDay()
{
	if (TimeOfDay.IsValid())
	{
		return TimeOfDay.Get();
	}
	UWorld* World = GetWorld();
	if (!World)
	{
		return nullptr;
	}
	// FindOrSpawn only spawns in game / PIE worlds; elsewhere it returns the existing actor or null.
	TimeOfDay = AGolmokTimeOfDay::FindOrSpawn(World);
	return TimeOfDay.Get();
}

void AGolmokPlayerController::BeginPlay()
{
	Super::BeginPlay();
	// Guarantee one lighting actor per level so the preset keys and portals have a target.
	GetTimeOfDay();
	AddMappingContext();
}

void AGolmokPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	EnsureInputAssets();

	UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(InputComponent);
	if (!Input)
	{
		UE_LOG(LogGolmok, Error, TEXT("Enhanced Input component missing; check Config/DefaultInput.ini."));
		return;
	}

	// Four preset handlers instead of one handler with a payload: keeps the BindAction overload unambiguous.
	Input->BindAction(HudAction, ETriggerEvent::Started, this, &AGolmokPlayerController::OnToggleHud);
	Input->BindAction(CollisionAction, ETriggerEvent::Started, this, &AGolmokPlayerController::OnToggleCollision);
	Input->BindAction(Preset1Action, ETriggerEvent::Started, this, &AGolmokPlayerController::OnPreset1);
	Input->BindAction(Preset2Action, ETriggerEvent::Started, this, &AGolmokPlayerController::OnPreset2);
	Input->BindAction(Preset3Action, ETriggerEvent::Started, this, &AGolmokPlayerController::OnPreset3);
	Input->BindAction(Preset4Action, ETriggerEvent::Started, this, &AGolmokPlayerController::OnPreset4);
	Input->BindAction(NextPresetAction, ETriggerEvent::Started, this, &AGolmokPlayerController::OnNextPreset);
	Input->BindAction(RecordAction, ETriggerEvent::Started, this, &AGolmokPlayerController::OnToggleRecord);
	Input->BindAction(PlayAction, ETriggerEvent::Started, this, &AGolmokPlayerController::OnTogglePlay);
}

void AGolmokPlayerController::OnPossess(APawn* InPawn)
{
	Super::OnPossess(InPawn);
	// Re-possession (path playback pawn <-> character): AddMappingContext is idempotent.
	AddMappingContext();
}

void AGolmokPlayerController::EnsureInputAssets()
{
	if (DebugMappingContext)
	{
		return;
	}

	auto MakeBoolAction = [this](const TCHAR* Name) -> UInputAction*
	{
		UInputAction* Action = NewObject<UInputAction>(this, Name);
		Action->ValueType = EInputActionValueType::Boolean;
		return Action;
	};

	HudAction = MakeBoolAction(TEXT("IA_GolmokHud"));
	CollisionAction = MakeBoolAction(TEXT("IA_GolmokCollision"));
	Preset1Action = MakeBoolAction(TEXT("IA_GolmokPreset1"));
	Preset2Action = MakeBoolAction(TEXT("IA_GolmokPreset2"));
	Preset3Action = MakeBoolAction(TEXT("IA_GolmokPreset3"));
	Preset4Action = MakeBoolAction(TEXT("IA_GolmokPreset4"));
	NextPresetAction = MakeBoolAction(TEXT("IA_GolmokNextPreset"));
	RecordAction = MakeBoolAction(TEXT("IA_GolmokRecord"));
	PlayAction = MakeBoolAction(TEXT("IA_GolmokPlay"));

	DebugMappingContext = NewObject<UInputMappingContext>(this, TEXT("IMC_GolmokDebug"));
	UInputMappingContext* Context = DebugMappingContext;

	Context->MapKey(HudAction, EKeys::F1);
	Context->MapKey(CollisionAction, EKeys::F2);
	Context->MapKey(Preset1Action, EKeys::One);
	Context->MapKey(Preset2Action, EKeys::Two);
	Context->MapKey(Preset3Action, EKeys::Three);
	Context->MapKey(Preset4Action, EKeys::Four);
	Context->MapKey(NextPresetAction, EKeys::F5);
	Context->MapKey(RecordAction, EKeys::F9);
	Context->MapKey(PlayAction, EKeys::F10);
}

void AGolmokPlayerController::AddMappingContext()
{
	if (!bDebugKeysEnabled)
	{
		return;
	}
	EnsureInputAssets();
	if (!DebugMappingContext)
	{
		return;
	}
	if (UEnhancedInputLocalPlayerSubsystem* Subsystem =
			ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer()))
	{
		Subsystem->AddMappingContext(DebugMappingContext, DebugMappingPriority);
	}
}

UGolmokDebugSubsystem* AGolmokPlayerController::GetDebugSubsystem() const
{
	UWorld* World = GetWorld();
	return World ? World->GetSubsystem<UGolmokDebugSubsystem>() : nullptr;
}

void AGolmokPlayerController::OnToggleHud()
{
	if (UGolmokDebugSubsystem* Debug = GetDebugSubsystem())
	{
		Debug->SetHudVisible(!Debug->IsHudVisible());
	}
}

void AGolmokPlayerController::OnToggleCollision()
{
	if (UGolmokDebugSubsystem* Debug = GetDebugSubsystem())
	{
		Debug->SetCollisionVisible(!Debug->IsCollisionVisible());
	}
}

void AGolmokPlayerController::OnPreset1()
{
	ApplyPresetIndex(0);
}

void AGolmokPlayerController::OnPreset2()
{
	ApplyPresetIndex(1);
}

void AGolmokPlayerController::OnPreset3()
{
	ApplyPresetIndex(2);
}

void AGolmokPlayerController::OnPreset4()
{
	ApplyPresetIndex(3);
}

void AGolmokPlayerController::ApplyPresetIndex(int32 Index)
{
	AGolmokTimeOfDay* Tod = GetTimeOfDay();
	if (!IsValid(Tod))
	{
		UE_LOG(LogGolmok, Warning, TEXT("Preset key %d: no AGolmokTimeOfDay in this world."), Index + 1);
		return;
	}
	// EnsurePresets may have failed (missing / broken presets file): the cycle is then empty.
	Tod->EnsurePresets();
	const TArray<FName>& Cycle = Tod->GetCycle();
	if (!Cycle.IsValidIndex(Index))
	{
		UE_LOG(LogGolmok, Warning, TEXT("Preset key %d: cycle has %d presets (%s)."), Index + 1, Cycle.Num(),
			Tod->LastError.IsEmpty() ? TEXT("no preset at that index") : *Tod->LastError);
		return;
	}
	Tod->ApplyPreset(Cycle[Index]);
}

void AGolmokPlayerController::OnNextPreset()
{
	AGolmokTimeOfDay* Tod = GetTimeOfDay();
	if (!IsValid(Tod))
	{
		UE_LOG(LogGolmok, Warning, TEXT("F5: no AGolmokTimeOfDay in this world."));
		return;
	}
	Tod->NextPreset();
}

void AGolmokPlayerController::OnToggleRecord()
{
	UGolmokDebugSubsystem* Debug = GetDebugSubsystem();
	if (!Debug)
	{
		return;
	}
	FString Message;
	bool bOk = false;
	if (Debug->IsRecording())
	{
		bOk = Debug->StopRecording(Message);
	}
	else
	{
		bOk = Debug->StartRecording(Debug->QuickPathName, Message);
	}
	if (bOk)
	{
		UE_LOG(LogGolmok, Log, TEXT("F9: %s"), *Message);
	}
	else
	{
		UE_LOG(LogGolmok, Warning, TEXT("F9: %s"), *Message);
	}
}

void AGolmokPlayerController::OnTogglePlay()
{
	UGolmokDebugSubsystem* Debug = GetDebugSubsystem();
	if (!Debug)
	{
		return;
	}
	if (Debug->IsPlaying())
	{
		Debug->StopPlayback(TEXT("F10"));
		return;
	}
	const FString& LastPathName = Debug->GetLastPathName();
	const FString Name = LastPathName.IsEmpty() ? Debug->QuickPathName : LastPathName;
	FString Message;
	if (Debug->StartPlayback(Name, false, Message))
	{
		UE_LOG(LogGolmok, Log, TEXT("F10: %s"), *Message);
	}
	else
	{
		UE_LOG(LogGolmok, Warning, TEXT("F10: %s"), *Message);
	}
}
