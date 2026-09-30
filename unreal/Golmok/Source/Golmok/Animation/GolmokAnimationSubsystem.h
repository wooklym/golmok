#pragma once

#include "CoreMinimal.h"
#include "Animation/GolmokAnimationConfig.h"
#include "Engine/StreamableManager.h"
#include "Subsystems/WorldSubsystem.h"
#include "GolmokAnimationSubsystem.generated.h"

class AGolmokGaspCharacter;
class UClass;
class UGolmokDebugSubsystem;

/**
 * WP-19 design sections 4, 8, 10 (Game and PIE worlds): registers the local GASP DDCvars
 * (Config/Golmok/local/gasp_ddcvars.json, when present), preloads the GASP pawn class asynchronously when the
 * effective mode is gasp, writes the pawn fallback Warning once per world, adds the "anim:" HUD line through
 * UGolmokDebugSubsystem::AddExtraHudLineProvider, and serves the console:
 *
 *   golmok.anim status [load] | mode <abp|gasp|config> | profile <id> | preview [off]
 *
 * status only checks that the GASP assets exist (asset registry / package on disk; "status load" loads them).
 * mode is process-wide (a new PIE picks it up); profile / preview act on the current GASP pawn only (active
 * character view, not paused, not in photo mode) and are not saved. A roster apply replaces the preview (19c T12:
 * the source mesh, and the visual override is set or cleared); `golmok.anim preview off` restores the roster entry.
 */
UCLASS()
class GOLMOK_API UGolmokAnimationSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	/**
	 * From GolmokAnimation::ResolvePlayerPawnClass: keeps the result (reused for the same SuperClass within this
	 * frame while the mode sources are unchanged) and logs a fallback Warning once per world.
	 */
	void RecordResolution(const GolmokAnimation::FPawnResolution& Resolution, const UClass* SuperClass);
	/** The resolution recorded for SuperClass in this frame (same mode source generation), if any. */
	bool FindCachedResolution(const UClass* SuperClass, GolmokAnimation::FPawnResolution& OutResolution) const;

	/** "" until a player pawn resolution fell back in this world. */
	const FString& GetLastFallbackReason() const { return LastFallbackReason; }
	int32 GetFallbackWarningCount() const { return FallbackWarnings; }

	/** golmok.anim status text (several lines); bLoadAssets = "status load" (loads the GASP classes). */
	FString DescribeStatus(bool bLoadAssets = false) const;

	/**
	 * "anim: abp" | "anim: abp (fallback: <reason>)" | "anim: abp (possessed <class> is not the GASP pawn)" |
	 * "anim: gasp p0 | ground run moving | intent 0.82 | land 0.12s -512".
	 */
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
	bool bLastResolvedGasp = false; // the last player spawn got the GASP pawn (HUD reason when another pawn is possessed)
	bool bFallbackWarned = false;
	int32 FallbackWarnings = 0;

	// Same-frame resolution cache (never dereferenced after the frame; compared by address only).
	GolmokAnimation::FPawnResolution CachedResolution;
	const UClass* CachedSuperClass = nullptr;
	uint64 CachedFrame = MAX_uint64;
	uint32 CachedGeneration = 0;

	int32 DDCvarCount = 0;
	int32 DDCvarPresent = 0;
	int32 DDCvarAdded = 0;
	FString DDCvarError;
};
