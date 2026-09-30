#pragma once

#include "CoreMinimal.h"
#include "Characters/GolmokCharacterMath.h"
#include "Subsystems/WorldSubsystem.h"
#include "TimerManager.h"
#include "GolmokCharacterSubsystem.generated.h"

class AGolmokCharacter;
class APlayerController;
class APawn;

struct FGolmokCharacterEntry
{
	FString Id;
	FString NameKo;
	FString NameEn;
	FString MeshPath;
	FString AnimPath;
	FString FootstepSet; // Empty means audio.json default; reserved, not consumed by WP-18a.
	GolmokCharacterMath::Dimensions Values;
};

struct FGolmokCharacterRoster
{
	FString DefaultId;
	TArray<FGolmokCharacterEntry> Entries;
	const FGolmokCharacterEntry* Find(const FString& InId) const;
};

namespace GolmokCharacters
{
	// All-or-nothing parsing: OutRoster is unchanged on failure.
	GOLMOK_API bool ParseRoster(const FString& Text, FGolmokCharacterRoster& OutRoster, FString& OutError);
	GOLMOK_API bool LoadRoster(FGolmokCharacterRoster& OutRoster, FString& OutError);
}

/** World-local console roster; no saved selection, input mapping, or pawn replacement. */
UCLASS()
class GOLMOK_API UGolmokCharacterSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;

	bool SelectCharacter(const FString& InId, FString& OutMessage);
	FString DescribeRoster() const;
	const FGolmokCharacterRoster& GetRoster() const { return Roster; }
	const FString& GetCurrentId() const { return CurrentId; }
	const FString& GetLoadError() const { return LoadError; }

private:
	void RefreshController();
	UFUNCTION()
	void OnPlayerPawnChanged(APawn* OldPawn, APawn* NewPawn);
	bool ApplyEntry(AGolmokCharacter* InCharacter, const FGolmokCharacterEntry& InEntry, FString& OutMessage);

	FGolmokCharacterRoster Roster;
	FString CurrentId;
	FString LoadError;
	TWeakObjectPtr<APlayerController> BoundController;
	FTimerHandle BindingTimer;
	bool bApplying = false;
};
