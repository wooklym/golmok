#pragma once

#include "CoreMinimal.h"
#include "Animation/GolmokAnimationConfig.h"
#include "Engine/StreamableManager.h"
#include "Subsystems/WorldSubsystem.h"
#include "GolmokAnimationSubsystem.generated.h"

class AGolmokGaspCharacter;
class UGolmokDebugSubsystem;

/**
 * WP-19 design sections 4, 8, 10 (Game and PIE worlds): registers the local GASP DDCvars
 * (Config/Golmok/local/gasp_ddcvars.json, when present), preloads the GASP pawn class asynchronously when the
 * effective mode is gasp, writes the pawn fallback Warning once per world, adds the "anim:" HUD line through
 * UGolmokDebugSubsystem::AddExtraHudLineProvider, and serves the console:
 *
 *   golmok.anim status | mode <abp|gasp|config> | profile <id> | preview [off]
 *
 * mode is process-wide (a new PIE picks it up); profile / preview act on the current GASP pawn only (active
 * character view, not paused, not in photo mode), are not saved, and the next roster apply replaces the preview.
 */
UCLASS()
class GOLMOK_API UGolmokAnimationSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	/** From GolmokAnimation::ResolvePlayerPawnClass: keeps the result and logs a fallback Warning once per world. */
	void RecordResolution(const GolmokAnimation::FPawnResolution& Resolution);

	/** "" until a player pawn resolution fell back in this world. */
	const FString& GetLastFallbackReason() const { return LastFallbackReason; }
	int32 GetFallbackWarningCount() const { return FallbackWarnings; }
	int32 GetResolutionCount() const { return Resolutions; }

	/** golmok.anim status text (several lines). */
	FString DescribeStatus() const;

	/** "anim: abp" | "anim: abp (fallback: <reason>)" | "anim: gasp p0 | ground run moving | intent 0.82 | land 0.12s -512". */
	FString BuildHudLine() const;

	bool SetMode(const FString& Argument, FString& OutMessage);
	bool ApplyProfile(const FString& Id, FString& OutMessage);
	bool ApplyPreview(bool bOn, FString& OutMessage);

	int32 GetDDCvarCount() const { return DDCvarCount; }
	int32 GetDDCvarPresent() const { return DDCvarPresent; }

private:
	/** The possessed AGolmokGaspCharacter in an active character view (not paused, not in photo mode), else null. */
	AGolmokGaspCharacter* GetActiveGaspCharacter(FString& OutMessage) const;
	void RegisterLocalDDCvars();
	void StartPreload();

	FStreamableManager Streamable;
	TSharedPtr<FStreamableHandle> PreloadHandle;
	TWeakObjectPtr<UGolmokDebugSubsystem> Debug;
	FDelegateHandle HudHandle;

	FString LastFallbackReason;
	FString LastResolvedClass;
	bool bFallbackWarned = false;
	int32 FallbackWarnings = 0;
	int32 Resolutions = 0;

	int32 DDCvarCount = 0;
	int32 DDCvarPresent = 0;
	int32 DDCvarAdded = 0;
	FString DDCvarError;
};
