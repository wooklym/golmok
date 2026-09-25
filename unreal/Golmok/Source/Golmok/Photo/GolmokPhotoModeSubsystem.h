#pragma once

#include "CoreMinimal.h"
#include "Engine/EngineTypes.h"
#include "Photo/GolmokPhotoMath.h"
#include "Subsystems/WorldSubsystem.h"
#include "GolmokPhotoModeSubsystem.generated.h"

class AGolmokPhotoCameraPawn;
class AGolmokPlayerController;
class AGolmokTimeOfDay;
class AActor;
class APawn;
class UEnhancedInputComponent;
class UGolmokDebugSubsystem;
class UInputAction;
class UInputMappingContext;
struct FInputActionValue;

/** GamePause: UGameplayStatics::SetGamePaused. TimeDilation: SetGlobalTimeDilation(0.0001) + character CustomTimeDilation 0 (PC fallback). */
UENUM()
enum class EGolmokPhotoPauseMode : uint8
{
	GamePause,
	TimeDilation
};

/** Not reflected. Exiting is the transient state of Exit() itself (re-entrancy guard for the pawn's EndPlay). */
enum class EGolmokPhotoState : uint8
{
	Inactive,
	Active,
	Shooting,
	Captured,
	Exiting
};

enum class EGolmokPhotoParam : uint8
{
	Fov,
	Ev,
	Focus,
	Fstop,
	Roll
};

/** One entry of photo.json "params" (linear / geometric / table). */
struct FGolmokPhotoParamSpec
{
	FString Label;
	FString Unit;
	double Default = 0.0;
	double Min = 0.0;
	double Max = 0.0;
	double Step = 0.0;
	double StepRatio = 0.0;
	/** Non-empty = table parameter. */
	TArray<double> Values;
	bool IsTable() const { return Values.Num() > 0; }
	bool IsGeometric() const { return StepRatio > 0.0; }
};

/** Config/Golmok/photo.json (design section 2-1). Plain struct, no reflection, no built-in defaults: a failed load refuses Enter(). */
struct FGolmokPhotoConfig
{
	/** EGolmokPhotoParam order (file order is validated to match). */
	FGolmokPhotoParamSpec Params[5];
	bool bDofDefault = false;
	bool bCharacterHiddenDefault = false;
	bool bOverlayHiddenDefault = false;
	TArray<FString> HintsKeyboard;
	TArray<FString> HintsGamepad;
	const FGolmokPhotoParamSpec& Spec(EGolmokPhotoParam P) const { return Params[static_cast<int32>(P)]; }
};

/** Parser helpers live in a NAMED namespace (unity build: GolmokLightingJson precedent). Static args are In* / Out* (C4458). */
namespace GolmokPhotoJson
{
	/** Parse + validate (section 2-1 rules). Error: "photo.json: <where>: <why>". TryGetField(FStringView); key enumeration via FString(*Pair.Key). */
	bool ParseConfigText(const FString& InJson, FGolmokPhotoConfig& Out, FString& OutError);
	/** FFileHelper::LoadFileToString, then ParseConfigText. */
	bool LoadConfigFile(const FString& InFilePath, FGolmokPhotoConfig& Out, FString& OutError);
} // namespace GolmokPhotoJson

/**
 * Photo mode (WP-12, D-013): a free camera around the player character with the game paused, camera-style
 * parameters (FOV, EV, focus, f-stop, roll, DOF), and a high-resolution screenshot plus a <stamp>.json sidecar
 * (design section 2-2) under Saved/<PhotoFolder>/.
 *
 * The photo pawn is the view target only (never possessed: portals and the zone subsystem keep seeing the
 * character). The world is paused with UGameplayStatics::SetGamePaused (ini PauseMode=TimeDilation is the PC
 * fallback); the pawn ticks while paused and the photo input actions carry bTriggerWhenPaused. Entering saves the
 * view target, control rotation, pause state, HUD visibility and debug-key state and Exit() restores them in reverse
 * (section 4-3); a transition of AGolmokTimeOfDay is shifted by the paused world time so it resumes where it was.
 *
 * Values / ranges / key hints come from Config/Golmok/photo.json (single source; a broken file refuses Enter()).
 * Console: golmok.photo [0|1] | golmok.photo.shoot | golmok.photo.reset | golmok.photo.set <name> <value>
 * Config: [/Script/Golmok.GolmokPhotoModeSubsystem] in DefaultGame.ini (section 7).
 */
UCLASS(Config = Game)
class GOLMOK_API UGolmokPhotoModeSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	/** Game / PIE (WP-05 pattern, V-03 ok). */
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	/** Clamps the ini values (section 7); photo.json is loaded lazily. */
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	/** Active: TeardownForDeadWorld() (no PC / pause / view target calls). */
	virtual void Deinitialize() override;

	// ---- Config (1:1 with [/Script/Golmok.GolmokPhotoModeSubsystem]; two-line declarations) ----------------------

	/** Relative to <Project>/Config unless absolute (same rule as AGolmokTimeOfDay::PresetsFile). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo")
	FString ConfigFile = TEXT("Golmok/photo.json");

	/** Under <Project>/Saved/: <stamp>.png + <stamp>.json. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo")
	FString PhotoFolder = TEXT("Screenshots/Golmok/photo");

	/** HighResShot multiplier of a photo (capped by MaxMultiplier). Distinct from GolmokDebugSubsystem.ScreenshotMultiplier. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo", meta = (ClampMin = "1", ClampMax = "8"))
	int32 ScreenshotMultiplier = 2;

	/** Upper bound of the photo multiplier (VRAM; runbook section 6 measures 2 and 3 on the RTX 5060 8 GB). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo", meta = (ClampMin = "1", ClampMax = "8"))
	int32 MaxMultiplier = 3;

	/** Free-camera sphere radius around the character's capsule center (m). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo", meta = (ClampMin = "0.5", ClampMax = "20.0"))
	float MaxDistanceM = 3.f;

	/** Sweep sphere radius of the camera pawn (cm): never closer than this to geometry; holes narrower than 2x are impassable. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo", meta = (ClampMin = "5.0", ClampMax = "50.0"))
	float CollisionRadiusCm = 15.f;

	/** Clamped this far inside the loaded zone footprint the character stands in (m). 0 = boundary. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo", meta = (ClampMin = "0.0"))
	float FootprintMarginM = 0.2f;

	/** Camera move speed (m/s); Shift / L3 triples it. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo", meta = (ClampMin = "0.1"))
	float MoveSpeedMps = 1.5f;

	/** Frames with overlay / HUD hidden and input frozen before the request (0 = request in the Shoot() tick). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo", meta = (ClampMin = "0", ClampMax = "60"))
	int32 PreCaptureFrames = 2;

	/** Frames the hide is kept after the request at least (the file renders on the next Draw; the png poll / 3 s timeout ends it). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo", meta = (ClampMin = "1", ClampMax = "10"))
	int32 PostCaptureFrames = 2;

	/** GamePause (default) or TimeDilation (PC fallback when input / camera do not update while paused). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo")
	EGolmokPhotoPauseMode PauseMode = EGolmokPhotoPauseMode::GamePause;

	// ---- state machine (section 4) ---------------------------------------------------------------------------

	/** Inactive -> Active; false + message when refused. */
	bool Enter(FString& OutMessage);
	/** Active -> Inactive; Shooting / Captured -> bExitPending; Inactive -> false. */
	bool Exit(const TCHAR* Reason);
	bool Toggle(FString& OutMessage);
	/** Active -> Shooting. */
	bool Shoot(FString& OutMessage);
	/** Section 0 #12: JSON defaults, DOF off, character / overlay shown, pose back to the entry point. */
	void Reset();
	bool IsActive() const { return State != EGolmokPhotoState::Inactive; }
	bool IsCapturing() const { return State == EGolmokPhotoState::Shooting || State == EGolmokPhotoState::Captured; }
	EGolmokPhotoState GetState() const { return State; }
	/** Null outside game worlds. */
	static UGolmokPhotoModeSubsystem* Get(UWorld* World);
	/** UGolmokDebugSubsystem::StartPlayback / StartRecording refuse when true. */
	static bool IsActiveIn(UWorld* World);

	// ---- parameters (input handlers, console golmok.photo.set and tests share these) ----------------------------

	/** One key press -> GolmokPhotoMath::Step*(...) -> ApplyToPawn(). Ignored unless Active. */
	void StepParam(EGolmokPhotoParam P, int32 Dir);
	/** Quantized / nearest / clamped. */
	bool SetParam(EGolmokPhotoParam P, double Value, FString& OutMessage);
	double GetParam(EGolmokPhotoParam P) const;
	void SetDofEnabled(bool bOn);
	bool IsDofEnabled() const { return bDof; }
	void SetCharacterHidden(bool bHidden);
	bool IsCharacterHidden() const { return bCharacterHidden; }
	void SetOverlayHidden(bool bHidden);
	bool IsOverlayHidden() const { return bOverlayHidden; }
	/** golmok.photo.set mult: 1..MaxMultiplier (session override). */
	bool SetMultiplier(int32 InMultiplier, FString& OutMessage);
	/** fov|ev|focus|fstop|roll */
	static bool ParseParamName(const FString& InName, EGolmokPhotoParam& Out);
	static const TCHAR* ParamName(EGolmokPhotoParam P);

	// ---- config ---------------------------------------------------------------------------------------------

	/** Loads once; false + LastError (Error log once) - Enter() refuses. */
	bool EnsureConfig();
	const FGolmokPhotoConfig* GetConfig() const { return bConfigLoaded ? &Config : nullptr; }
	/** FPaths::ProjectConfigDir() / ConfigFile */
	FString ResolveConfigPath() const;
	const FString& GetLastError() const { return LastError; }

	// ---- HUD hooks (AGolmokHUD) -----------------------------------------------------------------------------

	/** True while nothing at all may draw (Shooting / Captured). */
	bool IsHudSuppressed() const { return IsCapturing(); }
	/** Bottom-left lines (section 5-3); empty when inactive, capturing or the overlay is hidden. Cached 0.25 s like the debug HUD. */
	const TArray<FString>& GetOverlayLines();
	/** "inactive" | "active fov 65.0 ev +0.33 focus 3.000 m f/2.80 dof off roll +0.0 (zone z_x v1)" | "shooting" | "captured" */
	FString Describe() const;

	// ---- input (called by AGolmokPlayerController::SetupInputComponent) ---------------------------------------

	/** Creates the photo actions + IMC_GolmokPhoto once (owned here, Transient) and binds the handlers on this object. */
	void BindInput(UEnhancedInputComponent* Input);

	// ---- constraint inputs / meta (public for the tests) --------------------------------------------------------

	/** Character capsule center (SavedPawn actor location); entry camera location without a pawn. */
	FVector GetAnchor() const;
	const TArray<double>& GetFootprintXs() const { return FootprintXs; }
	const TArray<double>& GetFootprintYs() const { return FootprintYs; }
	/** Overrides the cached polygon while Active. */
	void SetFootprintForTest(const TArray<FVector2D>& LevelUEPolygonCm);
	/** Section 2-2 null rules from the current pose. */
	GolmokPhotoMath::PhotoMeta BuildMeta(int32 InMultiplier) const;
	AGolmokPhotoCameraPawn* GetPhotoPawn() const;
	const FString& GetLastShotPathNoExt() const { return LastShotPathNoExt; }
	/** Pawn tick counter (EnterExit: ticks while paused). */
	int32 GetPawnTickCount() const;

	/** Called by AGolmokPhotoCameraPawn::EndPlay (section 4-3 exit paths). */
	void OnPhotoPawnEndPlay(AGolmokPhotoCameraPawn* Pawn, EEndPlayReason::Type Reason);

private:
	// input handlers (one per action; Started unless noted)
	void OnShoot();
	void OnReset();
	void OnDof();
	void OnHideCharacter();
	void OnHideOverlay();
	void OnFovUp();
	void OnFovDown();
	/** Triggered: sign -> +-1 step (wheel up = narrower). */
	void OnFovWheel(const FInputActionValue& Value);
	void OnEvUp();
	void OnEvDown();
	void OnFocusUp();
	void OnFocusDown();
	void OnFstopUp();
	void OnFstopDown();
	void OnRollUp();
	void OnRollDown();
	/** Triggered / Completed */
	void OnMove(const FInputActionValue& Value);
	void OnMoveEnd(const FInputActionValue& Value);
	void OnUpDown(const FInputActionValue& Value);
	void OnUpDownEnd(const FInputActionValue& Value);
	/** Mouse2D (Triggered): per-frame delta -> pawn AddLookMouse. */
	void OnLook(const FInputActionValue& Value);
	/** Gamepad_Right2D (Triggered / Completed): stick value -> pawn SetLookPad (its own action: one handler cannot tell the devices apart). */
	void OnLookPad(const FInputActionValue& Value);
	void OnFastStart();
	void OnFastEnd();

	void EnsureInputAssets(UObject* Outer);
	/** IMC_GolmokPhoto at PhotoMappingPriority (3), Active only. */
	void AddPhotoContext(bool bOn);
	/** PauseMode branch; honours bWasPausedBefore. */
	void ApplyPause(bool bOn);
	/** Values -> pawn (FOV, roll, PP overrides), character hidden. */
	void ApplyToPawn();
	/** Section 6-2 */
	void CacheFootprint();
	/** Capture counter: Shooting -> request -> Captured -> restore. */
	void OnEndFrame();
	/** Stem, meta, RequestHighResScreenshot, effective multiplier. */
	void RequestShot();
	bool WriteMeta(const FString& InJsonPath, const GolmokPhotoMath::PhotoMeta& M, FString& OutError);
	/** <Saved>/<PhotoFolder>/<stamp>[_n] (no extension). */
	FString NextStemPath() const;
	/** Section 4-3 (live world). */
	void RestoreAll();
	/** Section 4-3 (EndPlayInEditor / Quit / bIsTearingDown). */
	void TeardownForDeadWorld();
	/** AGolmokTimeOfDay::CaptureState().ExposureBias or DefaultAutoExposureBias(). */
	double BaseExposureBias() const;
	UGolmokDebugSubsystem* GetDebug() const;
	AGolmokTimeOfDay* GetTimeOfDay() const;
	AGolmokPlayerController* GetPC() const;

	/** Above IMC_GolmokPhotoToggle (2) and IMC_GolmokDebug (1). */
	static constexpr int32 PhotoMappingPriority = 3;
	static constexpr double CaptureTimeoutSeconds = 3.0;
	static constexpr float FastMultiplier = 3.f;
	static constexpr float MouseLookDegPerUnit = 0.5f;
	static constexpr float PadLookDegPerSec = 120.f;

	/** IMC_GolmokPhoto */
	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> PhotoContext;

	/** Keeps the actions alive; indexed by the EPhotoActionSlot order of the .cpp (names: IA_GolmokPhotoShoot Reset Dof HideCharacter HideOverlay FovUp FovDown FovWheel EvUp EvDown FocusUp FocusDown FstopUp FstopDown RollUp RollDown Move UpDown Look LookPad Fast). */
	UPROPERTY(Transient)
	TArray<TObjectPtr<UInputAction>> Actions;

	EGolmokPhotoState State = EGolmokPhotoState::Inactive;
	FGolmokPhotoConfig Config;
	bool bConfigLoaded = false;
	bool bConfigFailed = false;
	FString LastError;
	/** Overwritten from photo.json at the first Enter (never used before). */
	double Values[5] = {65.0, 0.0, 3.0, 2.8, 0.0};
	bool bDof = false;
	bool bCharacterHidden = false;
	bool bOverlayHidden = false;
	/** 0 = ini ScreenshotMultiplier */
	int32 SessionMultiplier = 0;
	bool bExitPending = false;
	// saved at Enter, restored at Exit
	TWeakObjectPtr<AGolmokPhotoCameraPawn> PhotoPawn;
	TWeakObjectPtr<APawn> SavedPawn;
	TWeakObjectPtr<AActor> SavedViewTarget;
	FRotator SavedControlRotation = FRotator::ZeroRotator;
	bool bWasPausedBefore = false;
	bool bSavedFullTickWhenPaused = false;
	bool bSavedHudVisible = false;
	bool bSavedPawnHidden = false;
	bool bSavedSuppressTransition = false;
	bool bDebugKeysWereActive = false;
	float SavedTimeDilation = 1.f;
	float SavedPawnTimeDilation = 1.f;
	double WorldTimeAtEnter = 0.0;
	FVector EnterLocation = FVector::ZeroVector;
	FRotator EnterRotation = FRotator::ZeroRotator;
	float EnterFov = 80.f;
	TArray<double> FootprintXs;
	TArray<double> FootprintYs;
	FString FootprintZoneId;
	int32 FootprintZoneVersion = 0;
	// capture
	FDelegateHandle EndFrameHandle;
	int32 CaptureFrameCounter = 0;
	double CaptureRequestRealSeconds = 0.0;
	FString LastShotPathNoExt;
	int32 LastEffectiveMultiplier = 0;
	double SavedMessageUntilRealSeconds = 0.0;
	TArray<FString> OverlayLines;
	double OverlayLinesRealSeconds = -1.0;
	bool bOverlayDirty = true;
};
