#pragma once

#include "CoreMinimal.h"
#include "Animation/GolmokLocomotionMath.h"

class AController;
class APawn;
class UClass;
class UWorld;

/**
 * WP-19 (D-021) animation mode configuration: Config/Golmok/animation.json (design sections 4, 5, 7, 8).
 *
 * Mode "abp" (committed default) spawns AGolmokCharacter exactly as before; mode "gasp" asks for the local GASP
 * pawn Blueprint (gasp.pawn_class, a child of AGolmokGaspCharacter implementing the GASP pawn interface) and falls
 * back to the ABP pawn with a one-line reason when anything is missing. Parsing is all-or-nothing and strict (exact
 * key sets, like the roster); tools/tests/test_ue_config_animation.py applies the same rules to the committed file.
 * Effective mode priority: command line -GolmokAnim=abp|gasp > console golmok.anim mode > animation.json mode.
 */
namespace GolmokAnimation
{
	enum class EMode : uint8
	{
		Abp,
		Gasp,
	};

	using FMovementProfile = GolmokLocomotionMath::MovementProfile;

	struct FNamedProfile
	{
		FString Id;
		bool bDefined = false; // false: committed as null (filled by 19b after V-08b)
		FMovementProfile Values;
	};

	struct GOLMOK_API FConfig
	{
		EMode Mode = EMode::Abp;
		FString ContentRoot = TEXT("/Game/GASP");
		FString PawnClass;             // absolute (our local Blueprint), or /Script/Golmok.<Class> in tests
		FString PawnInterface;         // content_root relative
		FString AnimClass;             // content_root relative
		FString PreviewSourceMesh;     // content_root relative
		FString PreviewVisualMesh;     // empty = null; /Game/... absolute or content_root relative
		FString PreviewVisualAnimClass;
		FString MovementProfileId = TEXT("p0");
		double JustLandedSeconds = GolmokLocomotionMath::DefaultJustLandedSeconds;
		double TeleportJumpCm = GolmokLocomotionMath::DefaultTeleportSlackCm;
		bool bReinitAnimOnTeleport = true;
		TArray<FNamedProfile> Profiles;

		/** The profile with this id when it is defined (not null), else nullptr. */
		const FMovementProfile* FindProfile(const FString& Id) const;
		/** content_root + "/" + Relative; an absolute /Game/ or /Script/ path is returned unchanged. */
		FString AssetPath(const FString& Relative) const;
	};

	GOLMOK_API const TCHAR* ModeName(EMode Mode);
	GOLMOK_API bool ParseModeName(const FString& Text, EMode& OutMode);

	/** All-or-nothing: OutConfig is unchanged on failure and OutError names the first rule that failed. */
	GOLMOK_API bool ParseConfig(const FString& Text, FConfig& OutConfig, FString& OutError);
	/** <ProjectConfigDir>/Golmok/animation.json */
	GOLMOK_API FString ConfigFilePath();
	/** <ProjectConfigDir>/Golmok/local (git-ignored; written by tools/ue/add-gasp.ps1). */
	GOLMOK_API FString LocalDir();
	/** Reads the file (or the active FScopedConfigOverride text) and parses it. */
	GOLMOK_API bool LoadConfig(FConfig& OutConfig, FString& OutError);

	/**
	 * Test-only: while alive, LoadConfig parses Text instead of the file. With bIsolateModeSources (default) the
	 * effective mode ignores the command line and the console override, so a PC started with -GolmokAnim=abp still
	 * runs the gasp fallback cases. Nests (restores the previous override on destruction); game thread only.
	 */
	class GOLMOK_API FScopedConfigOverride
	{
	public:
		explicit FScopedConfigOverride(const FString& Text, bool bIsolateModeSources = true);
		~FScopedConfigOverride();
		FScopedConfigOverride(const FScopedConfigOverride&) = delete;
		FScopedConfigOverride& operator=(const FScopedConfigOverride&) = delete;

	private:
		bool bHadPrevious = false;
		FString PreviousText;
		bool bPreviousIsolate = false;
	};

	struct FModeResolution
	{
		EMode Mode = EMode::Abp;
		FString Source;       // "command line" | "console" | "animation.json" | "animation.json invalid"
		bool bConfigValid = false;
		FString ConfigError;  // parser error when !bConfigValid
	};

	/** Pure precedence rule (Golmok.Animation.Config): command line > console override > file mode. */
	GOLMOK_API FModeResolution ComputeEffectiveMode(const TCHAR* CommandLine, const TOptional<EMode>& ConsoleOverride,
		bool bConfigValid, EMode FileMode);
	/** ComputeEffectiveMode(FCommandLine::Get(), console override, LoadConfig()) (isolated under an override). */
	GOLMOK_API FModeResolution GetEffectiveMode();

	/** golmok.anim mode: process-wide (kept for the editor session; a new PIE picks it up). Unset = animation.json. */
	GOLMOK_API void SetConsoleModeOverride(const TOptional<EMode>& Mode);
	GOLMOK_API TOptional<EMode> GetConsoleModeOverride();

	struct FPawnResolution
	{
		UClass* PawnClass = nullptr; // the class to spawn (SuperClass on rule 1 and on every fallback)
		bool bFallback = false;      // true = mode wanted gasp (or the config is broken) and rules 2-5 refused
		FString Reason;              // fallback reason (the Warning text after "anim: falling back to ABP pawn (")
		FModeResolution Mode;
	};

	/**
	 * Design section 4 rules, in order: 1 mode abp or not a player -> SuperClass; 2 config parse failure -> fallback
	 * (parser error); 3 gasp.pawn_class does not load -> fallback; 4 not an AGolmokGaspCharacter -> fallback;
	 * 5 gasp.pawn_interface does not load or the pawn does not implement it -> fallback; 6 the Blueprint class.
	 * Missing packages are checked before loading, so a fallback logs nothing but its own Warning.
	 */
	GOLMOK_API FPawnResolution ResolvePawn(bool bIsPlayer, UClass* SuperClass);

	/** AGolmokGameMode hook: ResolvePawn + the fallback Warning once per world (UGolmokAnimationSubsystem). */
	GOLMOK_API UClass* ResolvePlayerPawnClass(AController* InController, UClass* SuperClass);

	/** Rules 4-5 for a class: empty OutReason when PawnClass can drive the GASP ABP. */
	GOLMOK_API bool PawnClassSupportsGasp(const FConfig& Config, const UClass* PawnClass, FString& OutReason);

	/** Roster query (T12): AnimClass is gasp.anim_class or a child of it (path compare, no loading). */
	GOLMOK_API bool RequiresGaspPawn(const UClass* AnimClass);
	/** Roster query (T12): design section 4 rules 4-5 hold for this pawn. */
	GOLMOK_API bool PawnSupportsGasp(const APawn* Pawn);

	/**
	 * Loads a class / object only when it is already in memory or its package exists on disk (no "failed to find"
	 * warnings for absent GASP content); /Script paths are only looked up. nullptr when absent or of another type.
	 */
	GOLMOK_API UClass* LoadClassIfPresent(const FString& Path, const UClass* BaseClass);
	GOLMOK_API UObject* LoadObjectIfPresent(const FString& Path, const UClass* ObjectClass);

	// ---- DDCvars (design section 8; local file only, never committed) ------------------------------------------

	enum class EDDCvarType : uint8
	{
		Int,
		Float,
		Bool,
	};

	struct FDDCvar
	{
		FString Name;
		EDDCvarType Type = EDDCvarType::Int;
		double Default = 0.0; // Int / Bool (0 or 1) are stored here too
		FString Help;
	};

	/** Config/Golmok/local/gasp_ddcvars.json (tools/ue/add-gasp.ps1). All-or-nothing. */
	GOLMOK_API bool ParseDDCvars(const FString& Text, TArray<FDDCvar>& OutVars, FString& OutError);
	GOLMOK_API FString DDCvarFilePath();
	GOLMOK_API FString ManifestFilePath();
	GOLMOK_API FString TagFilePath();

	/**
	 * Registers the variables the console manager does not know yet (process lifetime, never unregistered: the
	 * engine's own DataDrivenConsoleVariableSettings entries behave the same). Returns how many it added;
	 * OutPresent = how many of Vars exist afterwards.
	 */
	GOLMOK_API int32 RegisterDDCvars(const TArray<FDDCvar>& Vars, int32& OutPresent);
}
