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
	bool bHasVisual = false;
	FString VisualMeshPath;
	FString VisualAnimPath;
	std::array<double, 3> VisualScale = {1.0, 1.0, 1.0};
	FString FootstepSet; // Empty means audio.json default; reserved, not consumed by WP-18a.
	GolmokCharacterMath::Dimensions Values;
};

struct FGolmokCharacterRoster
{
	FString DefaultId;
	TMap<FString, FString> DefaultByAnimMode;
	const FString& DefaultForMode(const FString& Mode) const;
	TArray<FGolmokCharacterEntry> Entries;
	const FGolmokCharacterEntry* Find(const FString& InId) const;
};

namespace GolmokCharacters
{
	// All-or-nothing parsing: OutRoster is unchanged on failure.
	GOLMOK_API bool ParseRoster(const FString& Text, FGolmokCharacterRoster& OutRoster, FString& OutError);
	GOLMOK_API bool LoadRoster(FGolmokCharacterRoster& OutRoster, FString& OutError);
}

/** World-local console roster; Save/ reads IsExplicitSelection() to persist explicit choices only.
 * No input mapping or pawn replacement here. */
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
	/** True while CurrentId came from SelectCharacter. Automatic reapplication of that id keeps it;
	 * a successful automatic default/fallback clears it, and a fully failed automatic pass leaves it unchanged. */
	bool IsExplicitSelection() const { return bExplicitSelection; }
	const FString& GetLoadError() const { return LoadError; }

#if WITH_DEV_AUTOMATION_TESTS
	uint32 GetAssetLoadAttemptsForTest() const { return AssetLoadAttempts; }
	TFunction<void(AGolmokCharacter*)> BeforeVisualApplyForTest;
	FGolmokCharacterRoster& MutableRosterForTest() { return Roster; }
	void ApplyDefaultForTest(APawn* Pawn) { CurrentId.Reset(); bExplicitSelection = false; OnPlayerPawnChanged(nullptr, Pawn); }
#endif

private:
	void RefreshController();
	UFUNCTION()
	void OnPlayerPawnChanged(APawn* OldPawn, APawn* NewPawn);
	bool ApplyEntry(AGolmokCharacter* InCharacter, const FGolmokCharacterEntry& InEntry, FString& OutMessage);

	FGolmokCharacterRoster Roster;
	FString CurrentId;
	FString LoadError;
	FString LastAutomaticFailure;
	bool bWarnedGaspDefault = false;
	TWeakObjectPtr<APlayerController> BoundController;
	FTimerHandle BindingTimer;
	bool bApplying = false;
	bool bExplicitSelection = false;
#if WITH_DEV_AUTOMATION_TESTS
	uint32 AssetLoadAttempts = 0;
#endif
};
