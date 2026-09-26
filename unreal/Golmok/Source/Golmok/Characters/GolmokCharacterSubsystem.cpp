#include "Characters/GolmokCharacterSubsystem.h"

#include "Golmok.h"
#include "Animation/AnimBlueprintGeneratedClass.h"
#include "Animation/AnimInstance.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "HAL/IConsoleManager.h"
#include "Internationalization/Regex.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Player/GolmokCharacter.h"
#include "Engine/ScopedMovementUpdate.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/SoftObjectPath.h"
#include <initializer_list>

namespace GolmokCharacters
{
	using FObject = TSharedPtr<FJsonObject>;
	using FValue = TSharedPtr<FJsonValue>;

	bool Matches(const FString& Text, const TCHAR* Pattern)
	{
		FRegexMatcher Matcher(FRegexPattern(Pattern), Text);
		return Matcher.FindNext() && Matcher.GetMatchBeginning() == 0 && Matcher.GetMatchEnding() == Text.Len();
	}

	bool ValidId(const FString& Text)
	{
		return Text != TEXT("list") && Matches(Text, TEXT("[a-z][a-z0-9_]{0,47}"));
	}

	FValue Field(const FObject& Object, const TCHAR* Name)
	{
		return Object.IsValid() ? Object->TryGetField(FString(Name)) : nullptr;
	}

	FObject ObjectField(const FObject& Object, const TCHAR* Name)
	{
		const FValue Value = Field(Object, Name);
		return Value.IsValid() && Value->Type == EJson::Object ? Value->AsObject() : nullptr;
	}

	bool Keys(const FObject& Object, std::initializer_list<const TCHAR*> Names)
	{
		if (!Object.IsValid() || Object->Values.Num() != static_cast<int32>(Names.size()))
		{
			return false;
		}
		for (const TCHAR* Name : Names)
		{
			if (!Field(Object, Name).IsValid())
			{
				return false;
			}
		}
		return true;
	}

	bool String(const FObject& Object, const TCHAR* Name, FString& Out, int32 Limit = 256)
	{
		const FValue Value = Field(Object, Name);
		if (!Value.IsValid() || Value->Type != EJson::String)
		{
			return false;
		}
		Out = Value->AsString();
		return !Out.TrimStartAndEnd().IsEmpty() && Out.Len() <= Limit && !Out.Contains(TEXT("\n"))
			&& !Out.Contains(TEXT("\r"));
	}

	bool Number(const FObject& Object, const TCHAR* Name, double& Out)
	{
		const FValue Value = Field(Object, Name);
		if (!Value.IsValid() || Value->Type != EJson::Number)
		{
			return false;
		}
		Out = Value->AsNumber();
		return FMath::IsFinite(Out);
	}

	bool Vector(const FObject& Object, const TCHAR* Name, std::array<double, 3>& Out)
	{
		const FValue Value = Field(Object, Name);
		if (!Value.IsValid() || Value->Type != EJson::Array || Value->AsArray().Num() != 3)
		{
			return false;
		}
		for (int32 Axis = 0; Axis < 3; ++Axis)
		{
			const FValue& Item = Value->AsArray()[Axis];
			if (!Item.IsValid() || Item->Type != EJson::Number || !FMath::IsFinite(Item->AsNumber()))
			{
				return false;
			}
			Out[Axis] = Item->AsNumber();
		}
		return true;
	}

	bool ParseEntry(const FObject& Object, FGolmokCharacterEntry& Out)
	{
		if (!Keys(Object, {TEXT("id"), TEXT("display_name"), TEXT("mesh"), TEXT("anim_class"), TEXT("height_cm"),
			TEXT("capsule"), TEXT("mesh_offset_cm"), TEXT("mesh_scale"), TEXT("mesh_yaw_deg"), TEXT("camera"),
			TEXT("movement"), TEXT("footstep_set")}))
		{
			return false;
		}
		const FObject Names = ObjectField(Object, TEXT("display_name"));
		const FObject Capsule = ObjectField(Object, TEXT("capsule"));
		const FObject Camera = ObjectField(Object, TEXT("camera"));
		const FObject Movement = ObjectField(Object, TEXT("movement"));
		if (!Keys(Names, {TEXT("ko"), TEXT("en")}) || !Keys(Capsule, {TEXT("radius_cm"), TEXT("half_height_cm")})
			|| !Keys(Camera, {TEXT("boom_cm"), TEXT("socket_cm"), TEXT("fov_deg")})
			|| !Keys(Movement, {TEXT("walk_cm_s"), TEXT("run_cm_s")}))
		{
			return false;
		}
		GolmokCharacterMath::Dimensions& D = Out.Values;
		if (!String(Object, TEXT("id"), Out.Id, 48) || !ValidId(Out.Id)
			|| !String(Names, TEXT("ko"), Out.NameKo, 80) || !String(Names, TEXT("en"), Out.NameEn, 80)
			|| !String(Object, TEXT("mesh"), Out.MeshPath) || !String(Object, TEXT("anim_class"), Out.AnimPath)
			|| !Matches(Out.MeshPath, TEXT("/Game/([A-Za-z0-9_]+/)+[A-Za-z0-9_]+\\.[A-Za-z0-9_]+"))
			|| !Matches(Out.AnimPath, TEXT("/Game/([A-Za-z0-9_]+/)+[A-Za-z0-9_]+\\.[A-Za-z0-9_]+_C"))
			|| !Number(Object, TEXT("height_cm"), D.Height) || !Number(Capsule, TEXT("radius_cm"), D.Radius)
			|| !Number(Capsule, TEXT("half_height_cm"), D.HalfHeight)
			|| !Vector(Object, TEXT("mesh_offset_cm"), D.MeshOffset) || !Vector(Object, TEXT("mesh_scale"), D.MeshScale)
			|| !Number(Object, TEXT("mesh_yaw_deg"), D.MeshYaw) || !Number(Camera, TEXT("boom_cm"), D.Boom)
			|| !Vector(Camera, TEXT("socket_cm"), D.Socket) || !Number(Camera, TEXT("fov_deg"), D.Fov)
			|| !Number(Movement, TEXT("walk_cm_s"), D.Walk) || !Number(Movement, TEXT("run_cm_s"), D.Run)
			|| !GolmokCharacterMath::Validate(D))
		{
			return false;
		}
		const FValue Footstep = Field(Object, TEXT("footstep_set"));
		if (Footstep->Type != EJson::Null && (!String(Object, TEXT("footstep_set"), Out.FootstepSet, 48)
			|| !ValidId(Out.FootstepSet)))
		{
			return false;
		}
		return true;
	}

	bool ParseRoster(const FString& Text, FGolmokCharacterRoster& OutRoster, FString& OutError)
	{
		OutError = TEXT("characters.json: invalid root/schema_version/default/characters");
		FObject Root;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
		double Version = 0.0;
		FGolmokCharacterRoster Candidate;
		if (!FJsonSerializer::Deserialize(Reader, Root) || !Keys(Root, {TEXT("schema_version"), TEXT("default"), TEXT("characters")})
			|| !Number(Root, TEXT("schema_version"), Version) || Version != 1.0
			|| !String(Root, TEXT("default"), Candidate.DefaultId, 48) || !ValidId(Candidate.DefaultId))
		{
			return false;
		}
		const FValue Entries = Field(Root, TEXT("characters"));
		if (Entries->Type != EJson::Array || Entries->AsArray().Num() < 2 || Entries->AsArray().Num() > 32)
		{
			return false;
		}
		for (const FValue& Value : Entries->AsArray())
		{
			FGolmokCharacterEntry Entry;
			if (!Value.IsValid() || Value->Type != EJson::Object || !ParseEntry(Value->AsObject(), Entry)
				|| Candidate.Find(Entry.Id))
			{
				OutError = FString::Printf(TEXT("characters.json: invalid or duplicate entry at index %d (%s)"),
					Candidate.Entries.Num(), *Entry.Id);
				return false;
			}
			Candidate.Entries.Add(MoveTemp(Entry));
		}
		if (!Candidate.Find(Candidate.DefaultId))
		{
			OutError = TEXT("characters.json: default id is absent");
			return false;
		}
		OutRoster = MoveTemp(Candidate);
		OutError.Reset();
		return true;
	}

	bool LoadRoster(FGolmokCharacterRoster& OutRoster, FString& OutError)
	{
		FString Text;
		const FString Path = FPaths::Combine(FPaths::ProjectConfigDir(), TEXT("Golmok/characters.json"));
		if (!FFileHelper::LoadFileToString(Text, *Path))
		{
			OutError = TEXT("characters.json: cannot read Config/Golmok/characters.json; keeping ini character");
			return false;
		}
		return ParseRoster(Text, OutRoster, OutError);
	}

	FVector ToVector(const std::array<double, 3>& Value)
	{
		return FVector(Value[0], Value[1], Value[2]);
	}

	void CmdCharacter(const TArray<FString>& Args, UWorld* World)
	{
		UGolmokCharacterSubsystem* Subsystem = World ? World->GetSubsystem<UGolmokCharacterSubsystem>() : nullptr;
		FString Message = TEXT("no supported game world");
		if (Subsystem)
		{
			if (Args.Num() == 1 && Args[0] == TEXT("list"))
			{
				Message = Subsystem->DescribeRoster();
			}
			else if (Args.Num() == 1)
			{
				Subsystem->SelectCharacter(Args[0], Message);
			}
			else
			{
				Message = TEXT("usage: golmok.character list | <id>");
			}
		}
		UE_LOG(LogGolmok, Log, TEXT("golmok.character: %s"), *Message);
	}

	FAutoConsoleCommandWithWorldAndArgs GCmdCharacter(TEXT("golmok.character"),
		TEXT("golmok.character list | <id>: list or switch the current player character (no save)."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdCharacter));
}

const FGolmokCharacterEntry* FGolmokCharacterRoster::Find(const FString& InId) const
{
	return Entries.FindByPredicate([&InId](const FGolmokCharacterEntry& Entry) { return Entry.Id == InId; });
}

bool UGolmokCharacterSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UGolmokCharacterSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	if (!GolmokCharacters::LoadRoster(Roster, LoadError))
	{
		UE_LOG(LogGolmok, Log, TEXT("golmok.character: %s"), *LoadError);
	}
}

void UGolmokCharacterSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	RefreshController();
	InWorld.GetTimerManager().SetTimer(BindingTimer, this, &UGolmokCharacterSubsystem::RefreshController, 0.25f, true);
}

void UGolmokCharacterSubsystem::RefreshController()
{
	UWorld* World = GetWorld();
	if (!World || World->bIsTearingDown)
	{
		return;
	}
	APlayerController* NewController = World->GetFirstPlayerController();
	if (NewController == BoundController.Get())
	{
		return;
	}
	if (APlayerController* Previous = BoundController.Get())
	{
		Previous->OnPossessedPawnChanged.RemoveDynamic(this, &UGolmokCharacterSubsystem::OnPlayerPawnChanged);
	}
	BoundController = NewController;
	if (NewController)
	{
		NewController->OnPossessedPawnChanged.AddDynamic(this, &UGolmokCharacterSubsystem::OnPlayerPawnChanged);
		OnPlayerPawnChanged(nullptr, NewController->GetPawn());
	}
}

void UGolmokCharacterSubsystem::Deinitialize()
{
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(BindingTimer);
	}
	if (APlayerController* Previous = BoundController.Get())
	{
		Previous->OnPossessedPawnChanged.RemoveDynamic(this, &UGolmokCharacterSubsystem::OnPlayerPawnChanged);
	}
	BoundController.Reset();
	Super::Deinitialize();
}

void UGolmokCharacterSubsystem::OnPlayerPawnChanged(APawn* OldPawn, APawn* NewPawn)
{
	AGolmokCharacter* Character = Cast<AGolmokCharacter>(NewPawn);
	const FGolmokCharacterEntry* Entry = Roster.Find(CurrentId.IsEmpty() ? Roster.DefaultId : CurrentId);
	if (Character && Entry)
	{
		FString Message;
		if (!ApplyEntry(Character, *Entry, Message))
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.character: %s"), *Message);
		}
	}
}

bool UGolmokCharacterSubsystem::SelectCharacter(const FString& InId, FString& OutMessage)
{
	if (!LoadError.IsEmpty())
	{
		OutMessage = LoadError;
		return false;
	}
	const FGolmokCharacterEntry* Entry = Roster.Find(InId);
	if (!Entry)
	{
		OutMessage = FString::Printf(TEXT("unknown id '%s'; use golmok.character list"), *InId);
		return false;
	}
	APlayerController* PC = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
	AGolmokCharacter* Character = PC ? Cast<AGolmokCharacter>(PC->GetPawn()) : nullptr;
	if (!Character || UGameplayStatics::IsGamePaused(GetWorld()) || PC->GetViewTarget() != Character)
	{
		OutMessage = TEXT("switch requires an active character view; exit photo/path/pause first");
		return false;
	}
	return ApplyEntry(Character, *Entry, OutMessage);
}

bool UGolmokCharacterSubsystem::ApplyEntry(AGolmokCharacter* InCharacter, const FGolmokCharacterEntry& InEntry, FString& OutMessage)
{
	OutMessage = TEXT("character not initialized, busy, crouched, simulated, scaled or tilted");
	if (!IsValid(InCharacter) || !InCharacter->IsActorInitialized() || bApplying || InCharacter->bIsCrouched
		|| !InCharacter->GetActorScale3D().Equals(FVector::OneVector)
		|| !InCharacter->GetActorUpVector().Equals(FVector::UpVector)
		|| InCharacter->GetCapsuleComponent()->IsSimulatingPhysics() || InCharacter->GetMesh()->IsSimulatingPhysics())
	{
		return false;
	}
	TGuardValue<bool> Guard(bApplying, true);
	USkeletalMesh* NewMesh = Cast<USkeletalMesh>(FSoftObjectPath(InEntry.MeshPath).TryLoad());
	UClass* NewAnimClass = FSoftClassPath(InEntry.AnimPath).TryLoadClass<UAnimInstance>();
	const UAnimBlueprintGeneratedClass* AnimBP = Cast<UAnimBlueprintGeneratedClass>(NewAnimClass);
	if (!NewMesh || !AnimBP || !NewMesh->GetSkeleton() || AnimBP->GetTargetSkeleton() != NewMesh->GetSkeleton())
	{
		OutMessage = TEXT("mesh/animation missing or skeleton mismatch; keeping current character");
		return false;
	}
	const GolmokCharacterMath::Dimensions& D = InEntry.Values;
	UCapsuleComponent* Capsule = InCharacter->GetCapsuleComponent();
	FVector Center = InCharacter->GetActorLocation();
	Center.Z = GolmokCharacterMath::CenterForFixedFeet(Center.Z, Capsule->GetUnscaledCapsuleHalfHeight(), D.HalfHeight);
	const bool bResize = !FMath::IsNearlyEqual(Capsule->GetUnscaledCapsuleRadius(), static_cast<float>(D.Radius))
		|| !FMath::IsNearlyEqual(Capsule->GetUnscaledCapsuleHalfHeight(), static_cast<float>(D.HalfHeight));
	if (bResize)
	{
		FCollisionQueryParams Query(SCENE_QUERY_STAT(GolmokCharacterResize), false, InCharacter);
		const FCollisionResponseParams Response(Capsule->GetCollisionResponseToChannels());
		if (GetWorld()->OverlapBlockingTestByChannel(Center, Capsule->GetComponentQuat(), Capsule->GetCollisionObjectType(),
			FCollisionShape::MakeCapsule(static_cast<float>(D.Radius), static_cast<float>(D.HalfHeight)), Query, Response))
		{
			OutMessage = TEXT("new capsule is blocked; move away from the wall/ceiling first");
			return false;
		}
	}
	{
		FScopedMovementUpdate Scoped(Capsule, EScopedUpdate::DeferredUpdates);
		USkeletalMeshComponent* Mesh = InCharacter->GetMesh();
		Mesh->SetSkeletalMesh(NewMesh);
		Mesh->SetAnimInstanceClass(NewAnimClass);
		// ApplyCharacterVisuals exposes the capsule when the ini mesh cannot load.
		// A valid roster mesh replaces that fallback; do not propagate to the mesh.
		Capsule->SetHiddenInGame(true);
		Mesh->SetRelativeScale3D(GolmokCharacters::ToVector(D.MeshScale));
		Mesh->SetRelativeLocationAndRotation(GolmokCharacters::ToVector(D.MeshOffset), FRotator(0.0, D.MeshYaw, 0.0));
		InCharacter->CacheInitialMeshOffset(Mesh->GetRelativeLocation(), Mesh->GetRelativeRotation());
		InCharacter->GetCameraBoom()->TargetArmLength = static_cast<float>(D.Boom);
		InCharacter->GetCameraBoom()->SocketOffset = GolmokCharacters::ToVector(D.Socket);
		InCharacter->GetFollowCamera()->SetFieldOfView(static_cast<float>(D.Fov));
		InCharacter->SetMovementSpeeds(static_cast<float>(D.Walk), static_cast<float>(D.Run));
		CurrentId = InEntry.Id;
		// Finish child transforms before moving their deferred parent. Otherwise a child
		// update can recompute its relative offset against a stale parent world transform.
		if (bResize)
		{
			Capsule->SetCapsuleSize(static_cast<float>(D.Radius), static_cast<float>(D.HalfHeight), false);
			InCharacter->SetActorLocation(Center, false, nullptr, ETeleportType::TeleportPhysics);
		}
	}
	OutMessage = FString::Printf(TEXT("selected %s (%s / %s)"), *InEntry.Id, *InEntry.NameKo, *InEntry.NameEn);
	return true;
}

FString UGolmokCharacterSubsystem::DescribeRoster() const
{
	if (!LoadError.IsEmpty())
	{
		return LoadError;
	}
	FString Result = FString::Printf(TEXT("default=%s current=%s"), *Roster.DefaultId, *CurrentId);
	for (const FGolmokCharacterEntry& Entry : Roster.Entries)
	{
		Result += FString::Printf(TEXT("\n  %s | %s | %s"), *Entry.Id, *Entry.NameKo, *Entry.NameEn);
	}
	return Result;
}
