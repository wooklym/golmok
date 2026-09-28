#pragma once
#include "CoreMinimal.h"

struct FGolmokAudioAsset
{
	FString Path;
	bool bLoop = false;
};

struct FGolmokAudioConfig
{
	double MasterVolume = 0.7, CrossfadeSeconds = 2.0;
	double WalkStride = 70.0, RunStride = 110.0, RunThreshold = 250.0, TeleportLimit = 300.0;
	double PitchMin = 0.95, PitchMax = 1.05, VolumeMin = 0.9, VolumeMax = 1.0;
	bool bMuteInPhoto = true;
	TMap<FString, FGolmokAudioAsset> Assets;
	TMap<FString, FString> Ambience, Presets;
	TMap<FString, TArray<FString>> Sets;
	TMap<int32, FString> Surfaces;
	FString Landing, Credits;
};

namespace GolmokAudio
{
	GOLMOK_API bool ParseConfig(const FString& Json, FGolmokAudioConfig& Out, FString& Error);
	GOLMOK_API bool LoadConfig(FGolmokAudioConfig& Out, FString& Error);
}
