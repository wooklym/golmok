// GPU frame time source for the HUD (WP-05 design section 4-2). 1 = RHIGetGPUFrameCycles() (module "RHI" in
// Golmok.Build.cs). If that symbol is gone in a future engine, set this to 0: the GPU column then reads "n/a" and
// "RHI" can be dropped from Build.cs.
#define GOLMOK_GPU_TIME_SOURCE 1

#include "Debug/GolmokDebugSubsystem.h"

#include "Golmok.h"

#include "Camera/PlayerCameraManager.h"
#include "CoreGlobals.h"
#include "Debug/GolmokPathPawn.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Geo/GolmokGeo.h"
#include "Geo/GolmokGeoSubsystem.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformTime.h"
#include "Kismet/GameplayStatics.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Materials/Material.h"
#include "Materials/MaterialInterface.h"
#include "Misc/App.h"
#include "Misc/CoreDelegates.h"
#include "Misc/DateTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Portals/GolmokPortal.h"
#include "ShowFlags.h"
#include "TimerManager.h"
#include "Zones/GolmokZone.h"
#include "Zones/GolmokZoneSubsystem.h"

#if GOLMOK_GPU_TIME_SOURCE
#include "RHI.h"
#endif

namespace
{
	std::string ToUtf8(const FString& S)
	{
		// TCHAR_TO_UTF8 yields const ANSICHAR* (UTF8CHAR is char8_t under C++20, so the macro's cast is needed).
		return std::string(TCHAR_TO_UTF8(*S));
	}

	FString FromUtf8(const std::string& S)
	{
		return FString(UTF8_TO_TCHAR(S.c_str()));
	}

	/** HUD zone block: at most this many DescribeZones() rows after the header line. */
	constexpr int32 MaxHudZoneRows = 4;
} // namespace

// ---- lifecycle ------------------------------------------------------------------------------------------------

bool UGolmokDebugSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	// Runtime debug tools only (same reason as UGolmokZoneSubsystem).
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UGolmokDebugSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	RecordHz = FMath::Max(1, RecordHz);
	StatsWindowSeconds = FMath::Max(0.5f, StatsWindowSeconds);
	StatsCapacity = FMath::Max(64, StatsCapacity);
	ScreenshotMultiplier = FMath::Clamp(ScreenshotMultiplier, 1, 8);
	CollisionRefreshSeconds = FMath::Max(0.2f, CollisionRefreshSeconds);
	HudTextRefreshSeconds = FMath::Max(0.05f, HudTextRefreshSeconds);
	PlaybackFov = FMath::Clamp(PlaybackFov, 20.f, 150.f);
	Ring = GolmokStatsMath::RingBuffer(static_cast<std::size_t>(StatsCapacity));
	SampledSeconds = 0.0;
}

void UGolmokDebugSubsystem::Deinitialize()
{
	UWorld* World = GetWorld();
	if (bRecording)
	{
		UE_LOG(LogGolmok, Warning, TEXT("GolmokDebugSubsystem: world ending while recording path '%s' (%d samples) - discarded."), *RecordName,
			static_cast<int32>(RecordPath.Samples.size()));
		if (World)
		{
			World->GetTimerManager().ClearTimer(RecordTimer);
		}
		bRecording = false;
		RecordPath = GolmokStatsMath::CameraPath();
	}
	if (bPlaying)
	{
		StopPlayback(TEXT("world ending"));
	}
	if (World)
	{
		World->GetTimerManager().ClearTimer(CsvLookupTimer);
		World->GetTimerManager().ClearTimer(CollisionTimer);
	}
	if (bCollisionVisible)
	{
		// Restore the collision visuals / show flag only while the actors and viewport are still alive.
		bCollisionVisible = false;
		if (World && !World->bIsTearingDown)
		{
			RefreshCollisionVisuals();
			if (bCollisionShowFlag)
			{
				ApplyCollisionShowFlag(false);
			}
		}
	}
	// Last: StopPlayback() re-evaluates the sampler binding, so the unbind has to come after it.
	BindSampler(false);
	Super::Deinitialize();
}

void UGolmokDebugSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	if (bSampleWhenHudHidden)
	{
		BindSampler(true);
	}
	if (bHudOnAtStart)
	{
		SetHudVisible(true);
	}
	UE_LOG(LogGolmok, Log, TEXT("GolmokDebugSubsystem: ready (stats window %.1f s, %d frames; sampler %s; record %d Hz)"), StatsWindowSeconds,
		StatsCapacity, IsSamplerBound() ? TEXT("on") : TEXT("off until HUD / playback"), RecordHz);
}

// ---- statistics -----------------------------------------------------------------------------------------------

void UGolmokDebugSubsystem::BindSampler(bool bOn)
{
	if (bOn && !EndFrameHandle.IsValid())
	{
		EndFrameHandle = FCoreDelegates::OnEndFrame.AddUObject(this, &UGolmokDebugSubsystem::OnEndFrame);
	}
	else if (!bOn && EndFrameHandle.IsValid())
	{
		FCoreDelegates::OnEndFrame.Remove(EndFrameHandle);
		EndFrameHandle.Reset();
	}
}

void UGolmokDebugSubsystem::OnEndFrame()
{
	const double DtSec = FApp::GetDeltaTime();
	const double SecondsPerCycle = FPlatformTime::GetSecondsPerCycle();
	const double GameMs = GolmokStatsMath::CyclesToMs(static_cast<std::uint64_t>(GGameThreadTime), SecondsPerCycle);
	const double RenderMs = GolmokStatsMath::CyclesToMs(static_cast<std::uint64_t>(GRenderThreadTime), SecondsPerCycle);
#if GOLMOK_GPU_TIME_SOURCE
	const double GpuMs = GolmokStatsMath::CyclesToMs(static_cast<std::uint64_t>(RHIGetGPUFrameCycles()), SecondsPerCycle);
#else
	const double GpuMs = 0.0;
#endif
	PushFrameSample(DtSec, GameMs, RenderMs, GpuMs);
}

void UGolmokDebugSubsystem::PushFrameSample(double DtSec, double GameMs, double RenderMs, double GpuMs)
{
	GolmokStatsMath::FrameSample S;
	S.DtSec = DtSec;
	S.GameMs = GameMs;
	S.RenderMs = RenderMs;
	S.GpuMs = GpuMs;
	Ring.Push(S);
	if (DtSec > 0.0)
	{
		SampledSeconds += DtSec;
	}
}

bool UGolmokDebugSubsystem::GetStats(GolmokStatsMath::Stats& Out) const
{
	Out = GolmokStatsMath::Compute(Ring, static_cast<double>(StatsWindowSeconds));
	return Out.Frames > 0;
}

FString UGolmokDebugSubsystem::FormatStatsLine() const
{
	GolmokStatsMath::Stats S;
	if (!GetStats(S))
	{
		return TEXT("no samples yet");
	}
	const FString Gpu = S.HasGpu ? FString::Printf(TEXT("%.2f ms"), S.AvgGpuMs) : FString(TEXT("n/a"));
	return FString::Printf(TEXT("fps %.1f  1%% low %.1f  game %.2f ms  render %.2f ms  gpu %s  (%.1f s, %d fr)"), S.AvgFps, S.OnePercentLowFps,
		S.AvgGameMs, S.AvgRenderMs, *Gpu, S.WindowSec, static_cast<int32>(S.Frames));
}

// ---- HUD ------------------------------------------------------------------------------------------------------

void UGolmokDebugSubsystem::SetHudVisible(bool bVisible)
{
	bHudVisible = bVisible;
	HudLinesTime = -1.0;
	BindSampler(bSampleWhenHudHidden || bHudVisible || bPlaying);
}

const TArray<FString>& UGolmokDebugSubsystem::GetHudLines()
{
	GolmokStatsMath::Stats S;
	const bool bHasStats = GetStats(S);
	LastStats = S;

	FString FpsLine;
	FString MsLine;
	if (!bHasStats || SampledSeconds < static_cast<double>(StatsWindowSeconds))
	{
		FpsLine = FString::Printf(TEXT("Golmok  fps warming %.1f/%.1f s"), SampledSeconds, StatsWindowSeconds);
	}
	else
	{
		FpsLine = FString::Printf(TEXT("Golmok  fps %.1f  1%% low %.1f  (%.1f s, %d fr)"), S.AvgFps, S.OnePercentLowFps, S.WindowSec,
			static_cast<int32>(S.Frames));
	}
	if (bHasStats)
	{
		const FString Gpu = S.HasGpu ? FString::Printf(TEXT("%.2f ms"), S.AvgGpuMs) : FString(TEXT("n/a"));
		MsLine = FString::Printf(TEXT("game %.2f ms  render %.2f ms  gpu %s"), S.AvgGameMs, S.AvgRenderMs, *Gpu);
	}
	else
	{
		MsLine = TEXT("game -  render -  gpu -");
	}

	const double Now = FPlatformTime::Seconds();
	if (HudLinesTime < 0.0 || Now - HudLinesTime >= static_cast<double>(HudTextRefreshSeconds))
	{
		HudLinesCache.Reset();
		GetTimeOfDay(); // refresh the cache (BuildLightingLine is const)
		HudLinesCache.Add(BuildLightingLine());
		HudLinesCache.Add(BuildPlayerLine());
		TArray<FString> ZoneLines;
		BuildZoneLines().ParseIntoArrayLines(ZoneLines, /*bCullEmpty*/ true);
		HudLinesCache.Append(ZoneLines);
		HudLinesCache.Add(BuildPortalLine());
		HudLinesCache.Add(BuildPathLine());
		HudLinesCache.Add(FString::Printf(TEXT("collision: %s   keys: F1 hud  F2 col  1-4 tod  F5 next  F9 rec  F10 play"),
			bCollisionVisible ? TEXT("on") : TEXT("off")));
		HudLinesTime = Now;
	}

	HudLines.Reset();
	HudLines.Add(FpsLine);
	HudLines.Add(MsLine);
	HudLines.Append(HudLinesCache);
	return HudLines;
}

AGolmokTimeOfDay* UGolmokDebugSubsystem::GetTimeOfDay()
{
	if (!CachedTimeOfDay.IsValid())
	{
		CachedTimeOfDay = AGolmokTimeOfDay::Find(GetWorld());
	}
	return CachedTimeOfDay.Get();
}

FString UGolmokDebugSubsystem::BuildLightingLine() const
{
	const AGolmokTimeOfDay* Tod = CachedTimeOfDay.IsValid() ? CachedTimeOfDay.Get() : AGolmokTimeOfDay::Find(GetWorld());
	if (!Tod)
	{
		return TEXT("tod: -");
	}
	return FString::Printf(TEXT("tod: %s"), *Tod->Describe());
}

FString UGolmokDebugSubsystem::BuildPlayerLine() const
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return TEXT("pos -");
	}
	FVector Location = FVector::ZeroVector;
	bool bHaveLocation = false;
	if (const APawn* Pawn = UGameplayStatics::GetPlayerPawn(World, 0))
	{
		Location = Pawn->GetActorLocation();
		bHaveLocation = true;
	}
	else if (const APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(World, 0))
	{
		Location = Camera->GetCameraLocation();
		bHaveLocation = true;
	}
	if (!bHaveLocation)
	{
		return TEXT("pos -");
	}
	const FVector Enu = GolmokGeo::UEToEnu(Location);
	double Lat = 0.0;
	double Lon = 0.0;
	double Height = 0.0;
	UGolmokGeoSubsystem* Geo = World->GetSubsystem<UGolmokGeoSubsystem>();
	if (Geo && Geo->LevelUEToLonLat(Location, Lat, Lon, Height))
	{
		return FString::Printf(TEXT("pos ENU E %.2f N %.2f U %.2f  lat %.6f lon %.6f"), Enu.X, Enu.Y, Enu.Z, Lat, Lon);
	}
	return FString::Printf(TEXT("pos UE (%.0f, %.0f, %.0f) cm (no GeoOrigin)"), Location.X, Location.Y, Location.Z);
}

FString UGolmokDebugSubsystem::BuildZoneLines() const
{
	UWorld* World = GetWorld();
	UGolmokZoneSubsystem* Zones = World ? World->GetSubsystem<UGolmokZoneSubsystem>() : nullptr;
	if (!Zones)
	{
		return TEXT("zones: -");
	}
	TArray<FString> Lines;
	Zones->DescribeZones().ParseIntoArrayLines(Lines, /*bCullEmpty*/ true);
	if (Lines.Num() == 0)
	{
		return TEXT("zones: -");
	}
	FString Out = FString::Printf(TEXT("zones: %s"), *Lines[0]);
	const int32 Rows = FMath::Min(Lines.Num() - 1, MaxHudZoneRows);
	for (int32 i = 1; i <= Rows; ++i)
	{
		Out += TEXT("\n");
		Out += Lines[i];
	}
	if (Lines.Num() - 1 > MaxHudZoneRows)
	{
		Out += FString::Printf(TEXT("\n  ... %d more"), Lines.Num() - 1 - MaxHudZoneRows);
	}
	return Out;
}

FString UGolmokDebugSubsystem::BuildPortalLine() const
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return TEXT("portals: -");
	}
	TArray<FString> Parts;
	for (TActorIterator<AGolmokPortal> It(World); It; ++It)
	{
		const AGolmokPortal* Portal = *It;
		if (IsValid(Portal) && !Portal->IsActorBeingDestroyed())
		{
			Parts.Add(Portal->Describe());
		}
	}
	if (Parts.Num() == 0)
	{
		return TEXT("portals: -");
	}
	return FString::Printf(TEXT("portals: %s"), *FString::Join(Parts, TEXT(" | ")));
}

FString UGolmokDebugSubsystem::BuildPathLine() const
{
	return FString::Printf(TEXT("path: %s"), *DescribePathState());
}

FString UGolmokDebugSubsystem::DescribePathState() const
{
	if (bRecording)
	{
		const UWorld* World = GetWorld();
		const double T = World ? World->GetTimeSeconds() - RecordStartSeconds : 0.0;
		return FString::Printf(TEXT("rec %s %.1f s %d samples"), *RecordName, T, static_cast<int32>(RecordPath.Samples.size()));
	}
	if (bPlaying)
	{
		double T = 0.0;
		double Duration = 0.0;
		GetPlaybackProgress(T, Duration);
		const int32 Percent = Duration > 0.0 ? FMath::RoundToInt(static_cast<float>(FMath::Clamp(T / Duration, 0.0, 1.0) * 100.0)) : 100;
		return FString::Printf(TEXT("play %s %.1f/%.1f s %d%%%s"), *PlayName, T, Duration, Percent, bPlayCsv ? TEXT(" [csv]") : TEXT(""));
	}
	return TEXT("idle");
}

// ---- collision view -------------------------------------------------------------------------------------------

UMaterialInterface* UGolmokDebugSubsystem::GetWireMaterial()
{
	if (WireMaterial)
	{
		return WireMaterial;
	}
	if (GEngine && GEngine->WireframeMaterial)
	{
		WireMaterial = GEngine->WireframeMaterial.Get();
		return WireMaterial;
	}
	if (CollisionDebugMaterialPath.IsValid())
	{
		WireMaterial = Cast<UMaterialInterface>(CollisionDebugMaterialPath.TryLoad());
	}
	if (!WireMaterial && !bWarnedNoWireMaterial)
	{
		bWarnedNoWireMaterial = true;
		UE_LOG(LogGolmok, Warning, TEXT("GolmokDebugSubsystem: no wire material (GEngine->WireframeMaterial null, CollisionDebugMaterialPath '%s'); collision meshes keep their own materials."),
			*CollisionDebugMaterialPath.ToString());
	}
	return WireMaterial;
}

void UGolmokDebugSubsystem::ApplyCollisionShowFlag(bool bOn)
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	UGameViewportClient* Viewport = World->GetGameViewport();
	if (Viewport)
	{
		Viewport->EngineShowFlags.SetCollision(bOn);
	}
	else if (GEngine)
	{
		// No game viewport (e.g. -nullrhi automation): the console toggle is the fallback (design section 11 #31).
		GEngine->Exec(World, TEXT("show collision"));
	}
}

void UGolmokDebugSubsystem::RefreshCollisionVisuals()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	UMaterialInterface* Wire = bCollisionVisible ? GetWireMaterial() : nullptr;
	for (TActorIterator<AGolmokZone> It(World); It; ++It)
	{
		AGolmokZone* Zone = *It;
		if (IsValid(Zone) && !Zone->IsActorBeingDestroyed())
		{
			Zone->SetCollisionDebugVisible(bCollisionVisible, Wire);
		}
	}
	for (TActorIterator<AGolmokPortal> It(World); It; ++It)
	{
		AGolmokPortal* Portal = *It;
		if (IsValid(Portal) && !Portal->IsActorBeingDestroyed())
		{
			Portal->SetDebugVisible(bCollisionVisible);
		}
	}
}

void UGolmokDebugSubsystem::SetCollisionVisible(bool bVisible)
{
	bCollisionVisible = bVisible;
	RefreshCollisionVisuals();
	if (bCollisionShowFlag)
	{
		ApplyCollisionShowFlag(bVisible);
	}
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	if (bVisible)
	{
		// Newly loaded zones / portals are caught by the timer (no hook in AGolmokZone::Load()).
		World->GetTimerManager().SetTimer(CollisionTimer, this, &UGolmokDebugSubsystem::RefreshCollisionVisuals, CollisionRefreshSeconds, /*bLoop*/ true);
	}
	else
	{
		World->GetTimerManager().ClearTimer(CollisionTimer);
	}
	HudLinesTime = -1.0;
}

FString UGolmokDebugSubsystem::DescribeCollision() const
{
	int32 NumZones = 0;
	int32 NumPortals = 0;
	if (UWorld* World = GetWorld())
	{
		for (TActorIterator<AGolmokZone> It(World); It; ++It)
		{
			if (IsValid(*It))
			{
				++NumZones;
			}
		}
		for (TActorIterator<AGolmokPortal> It(World); It; ++It)
		{
			if (IsValid(*It))
			{
				++NumPortals;
			}
		}
	}
	return FString::Printf(TEXT("%s (show flag %d, %d zones, %d portals)"), bCollisionVisible ? TEXT("on") : TEXT("off"), bCollisionShowFlag ? 1 : 0,
		NumZones, NumPortals);
}

// ---- camera paths: files --------------------------------------------------------------------------------------

bool UGolmokDebugSubsystem::IsValidPathName(const FString& Name)
{
	if (Name.Len() < 1 || Name.Len() > 64)
	{
		return false;
	}
	for (int32 i = 0; i < Name.Len(); ++i)
	{
		const TCHAR C = Name[i];
		const bool bOk = (C >= TEXT('A') && C <= TEXT('Z')) || (C >= TEXT('a') && C <= TEXT('z')) || (C >= TEXT('0') && C <= TEXT('9')) ||
						 C == TEXT('_') || C == TEXT('-');
		if (!bOk)
		{
			return false;
		}
	}
	return true;
}

FString UGolmokDebugSubsystem::PathFilePath(const FString& Name) const
{
	return FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectSavedDir(), PathFolder, Name + TEXT(".json")));
}

bool UGolmokDebugSubsystem::SavePathFile(const FString& FilePath, const GolmokStatsMath::CameraPath& Path, FString& Error)
{
	const std::string Text = GolmokStatsMath::FormatPathJson(Path);
	const FString Content = FromUtf8(Text);
	if (!FFileHelper::SaveStringToFile(Content, *FilePath, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
	{
		Error = FString::Printf(TEXT("cannot write %s"), *FilePath);
		return false;
	}
	Error.Reset();
	return true;
}

bool UGolmokDebugSubsystem::LoadPathFile(const FString& FilePath, GolmokStatsMath::CameraPath& Out, FString& Error)
{
	FString Content;
	if (!FFileHelper::LoadFileToString(Content, *FilePath))
	{
		Error = FString::Printf(TEXT("cannot read %s"), *FilePath);
		return false;
	}
	const std::string Text = ToUtf8(Content);
	std::string ParseError;
	if (!GolmokStatsMath::ParsePathJson(Text, Out, ParseError))
	{
		Error = FString::Printf(TEXT("%s: %s"), *FilePath, *FromUtf8(ParseError));
		return false;
	}
	Error.Reset();
	return true;
}

TArray<FString> UGolmokDebugSubsystem::ListPathNames() const
{
	const FString Dir = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectSavedDir(), PathFolder));
	TArray<FString> Files;
	IFileManager::Get().FindFiles(Files, *Dir, TEXT("json"));
	TArray<FString> Names;
	for (const FString& File : Files)
	{
		Names.Add(FPaths::GetBaseFilename(File));
	}
	Names.Sort();
	return Names;
}

FString UGolmokDebugSubsystem::DescribePaths() const
{
	const FString Dir = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectSavedDir(), PathFolder));
	const TArray<FString> Names = ListPathNames();
	FString Out = FString::Printf(TEXT("%d paths in %s"), Names.Num(), *Dir);
	for (const FString& Name : Names)
	{
		GolmokStatsMath::CameraPath Path;
		FString Error;
		if (LoadPathFile(PathFilePath(Name), Path, Error))
		{
			Out += FString::Printf(TEXT("\n  %-24s %6d samples %8.1f s  (%s, %d Hz)"), *Name, static_cast<int32>(Path.Samples.size()), Path.Duration(),
				*FromUtf8(Path.Level), Path.Hz);
		}
		else
		{
			Out += FString::Printf(TEXT("\n  %-24s ERROR %s"), *Name, *Error);
		}
	}
	return Out;
}

// ---- camera paths: recording ----------------------------------------------------------------------------------

bool UGolmokDebugSubsystem::StartRecording(const FString& Name, FString& OutMessage)
{
	if (!IsValidPathName(Name))
	{
		OutMessage = FString::Printf(TEXT("invalid path name '%s' (use [A-Za-z0-9_-], 1-64 chars)"), *Name);
		return false;
	}
	if (bPlaying)
	{
		OutMessage = FString::Printf(TEXT("cannot record while playing '%s' (golmok.path stopplay first)"), *PlayName);
		return false;
	}
	if (bRecording)
	{
		OutMessage = FString::Printf(TEXT("already recording '%s' (golmok.path stop first)"), *RecordName);
		return false;
	}
	UWorld* World = GetWorld();
	if (!World)
	{
		OutMessage = TEXT("no world");
		return false;
	}
	FString Level = World->GetMapName();
	Level.RemoveFromStart(World->StreamingLevelsPrefix);

	RecordPath = GolmokStatsMath::CameraPath();
	RecordPath.Version = 1;
	RecordPath.Name = ToUtf8(Name);
	RecordPath.Level = ToUtf8(Level);
	RecordPath.Hz = RecordHz;
	RecordPath.Created = ToUtf8(FDateTime::UtcNow().ToIso8601());
	RecordName = Name;
	RecordStartSeconds = World->GetTimeSeconds();
	bRecording = true;
	World->GetTimerManager().SetTimer(RecordTimer, this, &UGolmokDebugSubsystem::RecordSample, 1.f / static_cast<float>(RecordHz), /*bLoop*/ true);
	RecordSample();
	HudLinesTime = -1.0;
	OutMessage = FString::Printf(TEXT("recording '%s' at %d Hz (level %s)"), *Name, RecordHz, *Level);
	return true;
}

void UGolmokDebugSubsystem::RecordSample()
{
	if (!bRecording)
	{
		return;
	}
	UWorld* World = GetWorld();
	APlayerCameraManager* Camera = World ? UGameplayStatics::GetPlayerCameraManager(World, 0) : nullptr;
	if (!Camera)
	{
		return;
	}
	const FVector Location = Camera->GetCameraLocation();
	const FRotator Rotation = Camera->GetCameraRotation();
	GolmokStatsMath::PoseSample S;
	S.T = World->GetTimeSeconds() - RecordStartSeconds;
	S.P[0] = Location.X;
	S.P[1] = Location.Y;
	S.P[2] = Location.Z;
	S.R[0] = Rotation.Pitch;
	S.R[1] = Rotation.Yaw;
	S.R[2] = Rotation.Roll;
	RecordPath.Samples.push_back(S);
}

bool UGolmokDebugSubsystem::StopRecording(FString& OutMessage)
{
	if (!bRecording)
	{
		OutMessage = TEXT("not recording");
		return false;
	}
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(RecordTimer);
	}
	bRecording = false;
	HudLinesTime = -1.0;

	const FString Dir = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectSavedDir(), PathFolder));
	IFileManager::Get().MakeDirectory(*Dir, /*Tree*/ true);
	const FString FilePath = PathFilePath(RecordName);
	FString Error;
	if (!SavePathFile(FilePath, RecordPath, Error))
	{
		OutMessage = Error;
		return false;
	}
	LastPathName = RecordName;
	OutMessage = FString::Printf(TEXT("path '%s' saved: %d samples, %.1f s -> %s"), *RecordName, static_cast<int32>(RecordPath.Samples.size()),
		RecordPath.Duration(), *FilePath);
	return true;
}

// ---- camera paths: playback -----------------------------------------------------------------------------------

bool UGolmokDebugSubsystem::StartPlayback(const FString& Name, bool bCsv, FString& OutMessage)
{
	if (bRecording)
	{
		OutMessage = FString::Printf(TEXT("cannot play while recording '%s' (golmok.path stop first)"), *RecordName);
		return false;
	}
	if (bPlaying)
	{
		OutMessage = FString::Printf(TEXT("already playing '%s' (golmok.path stopplay first)"), *PlayName);
		return false;
	}
	if (!IsValidPathName(Name))
	{
		OutMessage = FString::Printf(TEXT("invalid path name '%s' (use [A-Za-z0-9_-], 1-64 chars)"), *Name);
		return false;
	}
	UWorld* World = GetWorld();
	if (!World)
	{
		OutMessage = TEXT("no world");
		return false;
	}
	GolmokStatsMath::CameraPath Path;
	FString Error;
	if (!LoadPathFile(PathFilePath(Name), Path, Error))
	{
		OutMessage = Error;
		return false;
	}
	if (Path.Samples.empty())
	{
		OutMessage = FString::Printf(TEXT("path '%s' has no samples"), *Name);
		return false;
	}
	APlayerController* PC = UGameplayStatics::GetPlayerController(World, 0);
	if (!PC)
	{
		OutMessage = TEXT("no player controller");
		return false;
	}
	const double Duration = Path.Duration();
	const int32 NumSamples = static_cast<int32>(Path.Samples.size());
	const GolmokStatsMath::PoseSample& First = Path.Samples.front();
	const FVector StartLocation(First.P[0], First.P[1], First.P[2]);
	const FRotator StartRotation(First.R[0], First.R[1], First.R[2]);

	FActorSpawnParameters Params;
	Params.ObjectFlags = EObjectFlags(Params.ObjectFlags | RF_Transient);
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	AGolmokPathPawn* Pawn = World->SpawnActor<AGolmokPathPawn>(AGolmokPathPawn::StaticClass(), StartLocation, StartRotation, Params);
	if (!Pawn)
	{
		OutMessage = TEXT("could not spawn the playback pawn");
		return false;
	}

	SavedPawn = PC->GetPawn();
	bSavedPawnHidden = SavedPawn.IsValid() ? SavedPawn->IsHidden() : false;
	if (bHidePlayerDuringPlayback && SavedPawn.IsValid())
	{
		SavedPawn->SetActorHiddenInGame(true);
	}

	Pawn->Init(this, MoveTemp(Path), PlaybackFov);
	PC->Possess(Pawn);
	// Possess() normally switches the view target too; the explicit call makes the camera hand-over deterministic.
	PC->SetViewTargetWithBlend(Pawn, 0.f);

	PathPawn = Pawn;
	PlayName = Name;
	LastPathName = Name;
	bPlaying = true;
	bPlayCsv = bCsv;
	bCsvStarted = false;
	CsvLabel = Name;
	HudLinesTime = -1.0;
	BindSampler(bSampleWhenHudHidden || bHudVisible || bPlaying);

	OutMessage = FString::Printf(TEXT("path play '%s' (%.1f s, %d samples)%s"), *Name, Duration, NumSamples, bCsv ? TEXT(" + CsvProfile") : TEXT(""));
	UE_LOG(LogGolmok, Log, TEXT("GolmokDebugSubsystem: %s"), *OutMessage);
	return true;
}

void UGolmokDebugSubsystem::BeginCsv()
{
	if (!bPlaying || !bPlayCsv || bCsvStarted)
	{
		return;
	}
	UWorld* World = GetWorld();
	if (!World || !GEngine)
	{
		return;
	}
	CsvStartUtc = FDateTime::UtcNow();
	GEngine->Exec(World, TEXT("CsvProfile Start"));
	bCsvStarted = true;
	UE_LOG(LogGolmok, Log, TEXT("GolmokDebugSubsystem: CsvProfile Start (path '%s')"), *PlayName);
}

void UGolmokDebugSubsystem::LogLatestCsv()
{
	const FString Dir = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProfilingDir(), TEXT("CSV")));
	TArray<FString> Files;
	IFileManager::Get().FindFiles(Files, *FPaths::Combine(Dir, TEXT("Profile*.csv")), /*Files*/ true, /*Directories*/ false);
	FString Newest;
	FDateTime NewestStamp = FDateTime::MinValue();
	for (const FString& File : Files)
	{
		const FString Full = FPaths::Combine(Dir, File);
		const FDateTime Stamp = IFileManager::Get().GetTimeStamp(*Full);
		if (Newest.IsEmpty() || Stamp > NewestStamp)
		{
			Newest = Full;
			NewestStamp = Stamp;
		}
	}
	const bool bStale = Newest.IsEmpty() || NewestStamp + FTimespan::FromSeconds(5.0) < CsvStartUtc;
	if (Newest.IsEmpty())
	{
		UE_LOG(LogGolmok, Log, TEXT("GolmokDebugSubsystem: csv: no Profile*.csv yet in %s (the -game launcher engine writes to %%LOCALAPPDATA%%\\UnrealEngine\\5.8\\Saved\\Profiling\\CSV)"),
			*Dir);
	}
	else
	{
		UE_LOG(LogGolmok, Log, TEXT("GolmokDebugSubsystem: csv: %s  ->  golmok-perf \"%s\" --label %s --markdown%s"), *Newest, *Newest, *CsvLabel,
			bStale ? TEXT("  (older than this capture: the file may still be written; check the folder)") : TEXT(""));
	}
	UWorld* World = GetWorld();
	if (bStale && CsvLookupRetries > 0 && World && !World->bIsTearingDown)
	{
		--CsvLookupRetries;
		World->GetTimerManager().SetTimer(CsvLookupTimer, this, &UGolmokDebugSubsystem::LogLatestCsv, 2.f, /*bLoop*/ false);
	}
}

void UGolmokDebugSubsystem::EndPlayback(bool bFinished, const TCHAR* Reason)
{
	if (!bPlaying)
	{
		return;
	}
	bPlaying = false;
	UWorld* World = GetWorld();
	const bool bWorldAlive = World && !World->bIsTearingDown;

	double Elapsed = 0.0;
	if (PathPawn.IsValid())
	{
		Elapsed = PathPawn->GetElapsed();
	}

	if (bCsvStarted)
	{
		bCsvStarted = false;
		if (GEngine && World)
		{
			GEngine->Exec(World, TEXT("CsvProfile Stop"));
		}
		CsvLookupRetries = 1;
		LogLatestCsv();
	}

	APlayerController* PC = bWorldAlive ? UGameplayStatics::GetPlayerController(World, 0) : nullptr;
	if (PC)
	{
		if (SavedPawn.IsValid())
		{
			PC->Possess(SavedPawn.Get());
			PC->SetViewTargetWithBlend(SavedPawn.Get(), 0.f);
		}
		else if (AGameModeBase* GameMode = World->GetAuthGameMode())
		{
			GameMode->RestartPlayer(PC);
		}
	}
	if (SavedPawn.IsValid() && bHidePlayerDuringPlayback)
	{
		SavedPawn->SetActorHiddenInGame(bSavedPawnHidden);
	}
	SavedPawn.Reset();

	if (PathPawn.IsValid())
	{
		PathPawn->Destroy();
	}
	PathPawn.Reset();

	UE_LOG(LogGolmok, Log, TEXT("GolmokDebugSubsystem: path play '%s' %s (%s) after %.1f s"), *PlayName, bFinished ? TEXT("finished") : TEXT("stopped"),
		Reason ? Reason : TEXT(""), Elapsed);
	bPlayCsv = false;
	HudLinesTime = -1.0;
	BindSampler(bSampleWhenHudHidden || bHudVisible || bPlaying);
}

void UGolmokDebugSubsystem::StopPlayback(const TCHAR* Reason)
{
	EndPlayback(/*bFinished*/ false, Reason);
}

void UGolmokDebugSubsystem::OnPlaybackFinished(AGolmokPathPawn* Pawn)
{
	if (!bPlaying || Pawn != PathPawn.Get())
	{
		return;
	}
	EndPlayback(/*bFinished*/ true, TEXT("end of path"));
}

bool UGolmokDebugSubsystem::GetPlaybackProgress(double& OutT, double& OutDuration) const
{
	OutT = 0.0;
	OutDuration = 0.0;
	if (!bPlaying || !PathPawn.IsValid())
	{
		return false;
	}
	OutDuration = PathPawn->GetDuration();
	OutT = FMath::Clamp(PathPawn->GetElapsed(), 0.0, OutDuration);
	return true;
}

// ---- screenshots ----------------------------------------------------------------------------------------------

bool UGolmokDebugSubsystem::TakeScreenshot(const FString& Tag, const FString& NameOrEmpty, FString& OutMessage)
{
	if (!IsValidPathName(Tag))
	{
		OutMessage = FString::Printf(TEXT("invalid tag '%s' (use [A-Za-z0-9_-], 1-64 chars)"), *Tag);
		return false;
	}
	if (!NameOrEmpty.IsEmpty() && !IsValidPathName(NameOrEmpty))
	{
		OutMessage = FString::Printf(TEXT("invalid name '%s' (use [A-Za-z0-9_-], 1-64 chars)"), *NameOrEmpty);
		return false;
	}
	UWorld* World = GetWorld();
	if (!World || !GEngine)
	{
		OutMessage = TEXT("no world / engine");
		return false;
	}
	const AGolmokTimeOfDay* Tod = GetTimeOfDay();
	const FString Preset = (Tod && !Tod->CurrentPreset.IsNone()) ? Tod->CurrentPreset.ToString() : FString(TEXT("current"));
	const FString Dir = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectSavedDir(), ScreenshotFolder, Tag, Preset));
	const FString File = NameOrEmpty.IsEmpty() ? FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S")) : NameOrEmpty;
	IFileManager::Get().MakeDirectory(*Dir, /*Tree*/ true);
	const FString FullPath = FPaths::Combine(Dir, File);
	GEngine->Exec(World, *FString::Printf(TEXT("HighResShot %d filename=\"%s\""), ScreenshotMultiplier, *FullPath));
	OutMessage = FString::Printf(TEXT("screenshot requested -> %s.png (written on the next frame)"), *FullPath);
	return true;
}

// ---- console: golmok.hud | golmok.collision | golmok.path | golmok.screenshot | golmok.stats ---------------------

namespace
{
	UGolmokDebugSubsystem* DebugSubsystemFor(UWorld* World)
	{
		UGolmokDebugSubsystem* Subsystem = World ? World->GetSubsystem<UGolmokDebugSubsystem>() : nullptr;
		if (!Subsystem)
		{
			UE_LOG(LogGolmok, Warning, TEXT("golmok.*: no debug subsystem in this world (game / PIE only)."));
		}
		return Subsystem;
	}

	/** "0" / "1" (also off/on, false/true); anything else -> !Current. */
	bool ParseToggle(const TArray<FString>& Args, bool bCurrent)
	{
		if (Args.Num() < 1)
		{
			return !bCurrent;
		}
		const FString Arg = Args[0].ToLower();
		if (Arg == TEXT("0") || Arg == TEXT("off") || Arg == TEXT("false"))
		{
			return false;
		}
		if (Arg == TEXT("1") || Arg == TEXT("on") || Arg == TEXT("true"))
		{
			return true;
		}
		return !bCurrent;
	}

	void CmdHud(const TArray<FString>& Args, UWorld* World)
	{
		UGolmokDebugSubsystem* Subsystem = DebugSubsystemFor(World);
		if (!Subsystem)
		{
			return;
		}
		Subsystem->SetHudVisible(ParseToggle(Args, Subsystem->IsHudVisible()));
		UE_LOG(LogGolmok, Log, TEXT("golmok.hud: %s"), Subsystem->IsHudVisible() ? TEXT("on") : TEXT("off"));
	}

	void CmdCollision(const TArray<FString>& Args, UWorld* World)
	{
		UGolmokDebugSubsystem* Subsystem = DebugSubsystemFor(World);
		if (!Subsystem)
		{
			return;
		}
		Subsystem->SetCollisionVisible(ParseToggle(Args, Subsystem->IsCollisionVisible()));
		UE_LOG(LogGolmok, Log, TEXT("golmok.collision: %s"), *Subsystem->DescribeCollision());
	}

	void CmdPath(const TArray<FString>& Args, UWorld* World)
	{
		UGolmokDebugSubsystem* Subsystem = DebugSubsystemFor(World);
		if (!Subsystem)
		{
			return;
		}
		const FString Sub = Args.Num() > 0 ? Args[0].ToLower() : FString();
		FString Message;
		if (Sub == TEXT("record"))
		{
			if (Args.Num() < 2)
			{
				UE_LOG(LogGolmok, Warning, TEXT("usage: golmok.path record <name>"));
				return;
			}
			const bool bOk = Subsystem->StartRecording(Args[1], Message);
			UE_LOG(LogGolmok, Log, TEXT("golmok.path record: %s%s"), bOk ? TEXT("") : TEXT("ERROR "), *Message);
			return;
		}
		if (Sub == TEXT("stop"))
		{
			if (Subsystem->IsPlaying())
			{
				Subsystem->StopPlayback(TEXT("golmok.path stop"));
				UE_LOG(LogGolmok, Log, TEXT("golmok.path stop: playback stopped"));
				return;
			}
			const bool bOk = Subsystem->StopRecording(Message);
			UE_LOG(LogGolmok, Log, TEXT("golmok.path stop: %s%s"), bOk ? TEXT("") : TEXT("ERROR "), *Message);
			return;
		}
		if (Sub == TEXT("play"))
		{
			FString Name;
			bool bCsv = false;
			for (int32 i = 1; i < Args.Num(); ++i)
			{
				if (Args[i].ToLower() == TEXT("--csv"))
				{
					bCsv = true;
				}
				else if (Name.IsEmpty())
				{
					Name = Args[i];
				}
			}
			if (Name.IsEmpty())
			{
				UE_LOG(LogGolmok, Warning, TEXT("usage: golmok.path play <name> [--csv]"));
				return;
			}
			const bool bOk = Subsystem->StartPlayback(Name, bCsv, Message);
			UE_LOG(LogGolmok, Log, TEXT("golmok.path play: %s%s"), bOk ? TEXT("") : TEXT("ERROR "), *Message);
			return;
		}
		if (Sub == TEXT("stopplay"))
		{
			if (!Subsystem->IsPlaying())
			{
				UE_LOG(LogGolmok, Log, TEXT("golmok.path stopplay: ERROR not playing"));
				return;
			}
			Subsystem->StopPlayback(TEXT("golmok.path stopplay"));
			UE_LOG(LogGolmok, Log, TEXT("golmok.path stopplay: playback stopped"));
			return;
		}
		if (Sub == TEXT("list"))
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.path list: %s"), *Subsystem->DescribePaths());
			return;
		}
		UE_LOG(LogGolmok, Warning, TEXT("usage: golmok.path record <name> | stop | play <name> [--csv] | stopplay | list"));
	}

	void CmdScreenshot(const TArray<FString>& Args, UWorld* World)
	{
		UGolmokDebugSubsystem* Subsystem = DebugSubsystemFor(World);
		if (!Subsystem)
		{
			return;
		}
		if (Args.Num() < 1)
		{
			UE_LOG(LogGolmok, Warning, TEXT("usage: golmok.screenshot <tag> [name]"));
			return;
		}
		FString Message;
		const bool bOk = Subsystem->TakeScreenshot(Args[0], Args.Num() > 1 ? Args[1] : FString(), Message);
		UE_LOG(LogGolmok, Log, TEXT("golmok.screenshot: %s%s"), bOk ? TEXT("") : TEXT("ERROR "), *Message);
	}

	void CmdStats(const TArray<FString>& Args, UWorld* World)
	{
		UGolmokDebugSubsystem* Subsystem = DebugSubsystemFor(World);
		if (!Subsystem)
		{
			return;
		}
		GolmokStatsMath::Stats S;
		if (!Subsystem->GetStats(S))
		{
			UE_LOG(LogGolmok, Log, TEXT("golmok.stats: no samples yet%s"),
				Subsystem->IsSamplerBound() ? TEXT("") : TEXT(" (sampler off: bSampleWhenHudHidden=False; turn on the HUD or play a path)"));
			return;
		}
		UE_LOG(LogGolmok, Log, TEXT("golmok.stats: %s"), *Subsystem->FormatStatsLine());
	}

	FAutoConsoleCommandWithWorldAndArgs GCmdHud(TEXT("golmok.hud"), TEXT("golmok.hud [0|1]: show / hide the Golmok debug HUD (toggle without argument)."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdHud));
	FAutoConsoleCommandWithWorldAndArgs GCmdCollision(TEXT("golmok.collision"),
		TEXT("golmok.collision [0|1]: show / hide zone collision meshes, blockers and portal triggers (toggle without argument)."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdCollision));
	FAutoConsoleCommandWithWorldAndArgs GCmdPath(TEXT("golmok.path"),
		TEXT("golmok.path record <name> | stop | play <name> [--csv] | stopplay | list: record / play camera paths (Saved/Golmok/Paths)."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdPath));
	FAutoConsoleCommandWithWorldAndArgs GCmdScreenshot(TEXT("golmok.screenshot"),
		TEXT("golmok.screenshot <tag> [name]: HighResShot into Saved/Screenshots/Golmok/<tag>/<preset>/<name>.png."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdScreenshot));
	FAutoConsoleCommandWithWorldAndArgs GCmdStats(TEXT("golmok.stats"), TEXT("golmok.stats: log the HUD frame statistics line (works without the HUD)."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&CmdStats));
} // namespace
