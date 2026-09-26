#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "GolmokPlayerController.generated.h"

class AGolmokTimeOfDay;
class UGolmokDebugSubsystem;
class UGolmokPhotoModeSubsystem;
class UInputAction;
class UInputMappingContext;

/**
 * Player controller with the WP-05 debug / lighting keys (design section 5).
 *
 * The input actions and the mapping context are created in C++ at runtime, the same way AGolmokCharacter builds
 * its movement bindings, so the project needs no binary input assets. The context is added at
 * DebugMappingPriority (above the character's 0; the keys do not overlap) unless bDebugKeysEnabled is false.
 *
 *   F1 HUD on/off        F2 collision view on/off      1..4 lighting preset cycle[0..3]      F5 next preset
 *   F9 record toggle (QuickPathName)                   F10 playback toggle (last played / QuickPathName, no csv)
 *   P photo mode on/off (WP-12; also Gamepad_Special_Left) - a player feature: IMC_GolmokPhotoToggle is always added
 *   at PhotoTogglePriority, whatever bDebugKeysEnabled says. The photo actions themselves belong to
 *   UGolmokPhotoModeSubsystem; SetupInputComponent only hands it the input component (BindInput).
 *
 * While photo mode is on it suspends the debug keys (SetDebugKeysSuspended: IMC_GolmokDebug removed, re-added when
 * bDebugKeysEnabled). BeginPlay also guarantees one AGolmokTimeOfDay in the level (AGolmokTimeOfDay::FindOrSpawn).
 * Config: [/Script/Golmok.GolmokPlayerController] in DefaultGame.ini.
 */
UCLASS(Config = Game)
class GOLMOK_API AGolmokPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	/** False: the debug mapping context is never added (packaged builds). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	bool bDebugKeysEnabled = true;

	/** Mapping context priority; above the character's context (0). The keys do not overlap, so this is formal. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	int32 DebugMappingPriority = 1;

	/** Cached AGolmokTimeOfDay of the level, spawned (transient) when the level has none. Null outside game worlds. */
	AGolmokTimeOfDay* GetTimeOfDay();

	/** true: IMC_GolmokDebug removed (photo mode); false: re-added when bDebugKeysEnabled. AddMappingContext() early-returns while suspended. */
	void SetDebugKeysSuspended(bool bSuspended);
	bool IsDebugKeysSuspended() const { return bDebugKeysSuspended; }

	/** Priority of IMC_GolmokPhotoToggle: above IMC_GolmokDebug (1), below the subsystem's IMC_GolmokPhoto (3). */
	static constexpr int32 PhotoTogglePriority = 2;

protected:
	virtual void BeginPlay() override;
	virtual void SetupInputComponent() override;
	virtual void OnPossess(APawn* InPawn) override;

private:
	void EnsureInputAssets();
	void AddMappingContext();

	void OnToggleHud();
	void OnToggleCollision();
	void OnPreset1();
	void OnPreset2();
	void OnPreset3();
	void OnPreset4();
	void OnNextPreset();
	void OnToggleRecord();
	void OnTogglePlay();

	/** P / Gamepad_Special_Left: UGolmokPhotoModeSubsystem::Toggle; logs "P: <message>". */
	void OnTogglePhoto();

	/** ApplyPreset(GetCycle()[Index]); warns when Index is outside the cycle (e.g. presets file missing). */
	void ApplyPresetIndex(int32 Index);

	UGolmokDebugSubsystem* GetDebugSubsystem() const;

	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> DebugMappingContext;

	/** F1 */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> HudAction;

	/** F2 */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> CollisionAction;

	/** One */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> Preset1Action;

	/** Two */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> Preset2Action;

	/** Three */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> Preset3Action;

	/** Four */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> Preset4Action;

	/** F5 */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> NextPresetAction;

	/** F9 */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> RecordAction;

	/** F10 */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> PlayAction;

	/** IMC_GolmokPhotoToggle: P, Gamepad_Special_Left; always added (bDebugKeysEnabled-independent). */
	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> PhotoToggleContext;

	/** P / Gamepad_Special_Left (bTriggerWhenPaused = true): IA_GolmokPhotoToggle */
	UPROPERTY(Transient)
	TObjectPtr<UInputAction> PhotoToggleAction;

	bool bDebugKeysSuspended = false;

	TWeakObjectPtr<AGolmokTimeOfDay> TimeOfDay;
};
