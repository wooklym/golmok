#pragma once

#include "CoreMinimal.h"
#include "Debug/GolmokStatsMath.h"
#include "Engine/EngineTypes.h"
#include "Subsystems/WorldSubsystem.h"
#include "UObject/SoftObjectPath.h"
#include "GolmokDebugSubsystem.generated.h"

class AGolmokPathPawn;
class AGolmokTimeOfDay;
class APawn;
class UMaterialInterface;

/**
 * Debug tools of WP-05 (design section 4): frame statistics (HUD lines, golmok.stats), the collision debug view,
 * camera path recording / playback (with an optional CsvProfile capture) and high resolution screenshots.
 *
 * Game and PIE worlds only. The subsystem never ticks: frame samples come from FCoreDelegates::OnEndFrame (bound in
 * OnWorldBeginPlay when bSampleWhenHudHidden, otherwise only while the HUD is visible or a path plays), so
 * golmok.stats, --csv playback and the -nullrhi automation read values without the HUD. HUD text is rebuilt every
 * HudTextRefreshSeconds; only the two fps lines are regenerated per call.
 *
 * Console: golmok.hud [0|1] | golmok.collision [0|1] | golmok.path record <name> | stop | play <name> [--csv] |
 *          stopplay | list | golmok.screenshot <tag> [name] | golmok.stats
 * Config: [/Script/Golmok.GolmokDebugSubsystem] in DefaultGame.ini.
 */
UCLASS(Config = Game)
class GOLMOK_API UGolmokDebugSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;

	// ---- Config (1:1 with the ini keys; keep the two-line declarations) ---------------------------------------------

	/** Seconds of frames the HUD statistics (avg fps, 1% low) cover. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "0.5"))
	float StatsWindowSeconds = 2.f;

	/** Ring buffer capacity in frames (2 s x 1000 fps upper bound). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "64"))
	int32 StatsCapacity = 2048;

	/** False: frames are sampled only while the HUD is visible or a path is playing (saves 4 doubles per frame). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	bool bSampleWhenHudHidden = true;

	/** Camera path recording rate. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "1"))
	int32 RecordHz = 10;

	/** Under <Project>/Saved/ */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	FString PathFolder = TEXT("Golmok/Paths");

	/** Under <Project>/Saved/ (same tree as viewpoints.py: Screenshots/Golmok/<tag>/<preset>/<name>.png) */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	FString ScreenshotFolder = TEXT("Screenshots/Golmok");

	/** HighResShot multiplier. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "1", ClampMax = "8"))
	int32 ScreenshotMultiplier = 2;

	/** Fallback wire material when GEngine->WireframeMaterial is null. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	FSoftObjectPath CollisionDebugMaterialPath;

	/** Also toggle the viewport's Collision show flag with golmok.collision. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	bool bCollisionShowFlag = true;

	/** While the collision view is on, re-apply it to newly loaded zones / portals this often (s). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "0.2"))
	float CollisionRefreshSeconds = 1.f;

	/** Seconds between rebuilds of the non-fps HUD lines. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "0.05"))
	float HudTextRefreshSeconds = 0.25f;

	/** Show the HUD as soon as the world begins play. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	bool bHudOnAtStart = false;

	/** Hide the player pawn while a path plays (its collision stays). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	bool bHidePlayerDuringPlayback = true;

	/** Path name used by the F9 / F10 keys. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	FString QuickPathName = TEXT("quick");

	/** Field of view of the playback camera (degrees). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "20.0", ClampMax = "150.0"))
	float PlaybackFov = 80.f;

	// ---- HUD / statistics -------------------------------------------------------------------------------------

	void SetHudVisible(bool bVisible);
	bool IsHudVisible() const { return bHudVisible; }

	/** Compute(Ring, StatsWindowSeconds). False when there is no sample yet. */
	bool GetStats(GolmokStatsMath::Stats& Out) const;

	/**
	 * "fps 158.3  1% low 121.0  game 1.75 ms  render 6.98 ms  gpu 5.99 ms  (2.0 s, 316 fr)" (gpu n/a without GPU
	 * samples); "no samples yet" before the first sample. Used by golmok.stats and the HudStats test.
	 */
	FString FormatStatsLine() const;

	/** One frame sample (OnEndFrame internally; public as a test hook). */
	void PushFrameSample(double DtSec, double GameMs, double RenderMs, double GpuMs);

	/** HUD lines: the two fps lines are regenerated on every call, the rest every HudTextRefreshSeconds. */
	const TArray<FString>& GetHudLines();

	/** Statistics computed by the last GetHudLines() call (the HUD colors the fps line with it). */
	const GolmokStatsMath::Stats& GetLastStats() const { return LastStats; }

	/** True while the OnEndFrame sampler is bound. */
	bool IsSamplerBound() const { return EndFrameHandle.IsValid(); }

	// ---- collision view ---------------------------------------------------------------------------------------

	void SetCollisionVisible(bool bVisible);
	bool IsCollisionVisible() const { return bCollisionVisible; }

	/** "on (show flag 1, 2 zones, 2 portals)" / "off (...)" for golmok.collision. */
	FString DescribeCollision() const;

	// ---- camera paths -----------------------------------------------------------------------------------------

	bool StartRecording(const FString& Name, FString& OutMessage);

	/** Stops the timer and writes <Saved>/<PathFolder>/<Name>.json. */
	bool StopRecording(FString& OutMessage);

	bool StartPlayback(const FString& Name, bool bCsv, FString& OutMessage);

	/** Restores the player pawn / view target, stops the CsvProfile capture and logs the csv path. */
	void StopPlayback(const TCHAR* Reason);

	/** Called by AGolmokPathPawn when its path reaches the last sample. */
	void OnPlaybackFinished(AGolmokPathPawn* Pawn);

	/** Called by AGolmokPathPawn on its first tick: "CsvProfile Start" when the playback was started with --csv. */
	void BeginCsv();

	bool IsRecording() const { return bRecording; }
	bool IsPlaying() const { return bPlaying; }
	bool GetPlaybackProgress(double& OutT, double& OutDuration) const;

	/** "idle" | "rec walk_01 12.3 s 123 samples" | "play walk_01 27.6/61.2 s 45% [csv]" (the HUD path line). */
	FString DescribePathState() const;

	/** <Saved>/<PathFolder>/<Name>.json (absolute). */
	FString PathFilePath(const FString& Name) const;

	/** ^[A-Za-z0-9_-]{1,64}$ */
	static bool IsValidPathName(const FString& Name);

	static bool SavePathFile(const FString& FilePath, const GolmokStatsMath::CameraPath& Path, FString& Error);
	static bool LoadPathFile(const FString& FilePath, GolmokStatsMath::CameraPath& Out, FString& Error);

	/** Names (without .json) of the files in <Saved>/<PathFolder>, sorted. */
	TArray<FString> ListPathNames() const;

	/** One line per path with its sample count and length (golmok.path list). */
	FString DescribePaths() const;

	const FString& GetLastPathName() const { return LastPathName; }

	// ---- screenshots ------------------------------------------------------------------------------------------

	/** HighResShot into <Saved>/<ScreenshotFolder>/<tag>/<preset>/<name>.png (name = timestamp when empty). */
	bool TakeScreenshot(const FString& Tag, const FString& NameOrEmpty, FString& OutMessage);

private:
	void OnEndFrame();
	void BindSampler(bool bOn);
	void RecordSample();
	void RefreshCollisionVisuals();

	/** GEngine->WireframeMaterial, else CollisionDebugMaterialPath.TryLoad(), else nullptr (warns once). */
	UMaterialInterface* GetWireMaterial();
	void ApplyCollisionShowFlag(bool bOn);

	/** "finished" (end of path) or "stopped" (Reason): the shared teardown of StopPlayback / OnPlaybackFinished. */
	void EndPlayback(bool bFinished, const TCHAR* Reason);

	/** Newest Profile*.csv under <ProfilingDir>/CSV -> log with the golmok-perf command line. */
	void LogLatestCsv();

	FString BuildZoneLines() const;
	FString BuildPortalLine() const;
	FString BuildLightingLine() const;
	FString BuildPlayerLine() const;
	FString BuildPathLine() const;
	AGolmokTimeOfDay* GetTimeOfDay();

	GolmokStatsMath::RingBuffer Ring{2048};
	GolmokStatsMath::Stats LastStats;
	FDelegateHandle EndFrameHandle;

	/** Seconds sampled since the ring was created (HUD "warming" until it reaches StatsWindowSeconds). */
	double SampledSeconds = 0.0;

	bool bHudVisible = false;
	bool bCollisionVisible = false;
	bool bRecording = false;
	bool bPlaying = false;
	bool bPlayCsv = false;
	bool bCsvStarted = false;
	bool bWarnedNoWireMaterial = false;

	TArray<FString> HudLinesCache;
	TArray<FString> HudLines;
	double HudLinesTime = -1.0;

	FString RecordName;
	GolmokStatsMath::CameraPath RecordPath;
	double RecordStartSeconds = 0.0;
	FTimerHandle RecordTimer;

	FString PlayName;
	FString LastPathName;
	FString CsvLabel;
	FDateTime CsvStartUtc;
	FTimerHandle CsvLookupTimer;
	int32 CsvLookupRetries = 0;

	TWeakObjectPtr<AGolmokPathPawn> PathPawn;
	TWeakObjectPtr<APawn> SavedPawn;
	bool bSavedPawnHidden = false;

	TWeakObjectPtr<AGolmokTimeOfDay> CachedTimeOfDay;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> WireMaterial;

	FTimerHandle CollisionTimer;
};
