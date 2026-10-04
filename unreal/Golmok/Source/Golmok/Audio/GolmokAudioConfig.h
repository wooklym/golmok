#pragma once
#include "CoreMinimal.h"
#include "Audio/GolmokAudioMath.h"

struct FGolmokAudioAsset
{
	FString Path;
	bool bLoop = false;
};

struct FGolmokAudioConfig
{
	double MasterVolume = 0.7, CrossfadeSeconds = 2.0, PhotoMuteFadeSeconds = 0.25;
	double WalkStride = 70.0, RunStride = 110.0, RunThreshold = 250.0, TeleportLimit = 300.0;
	double PitchMin = 0.95, PitchMax = 1.05, VolumeMin = 0.9, VolumeMax = 1.0;
	bool bMuteInPhoto = true;
	// Optional rain layer: absent in legacy manifests, independent of the two bed slots.
	FString RainAsset;
	double RainInteriorGain = .35;
	TArray<FVector2D> RainGainCurve;
	double RainGain(double Intensity) const
	{
		return GolmokAudioMath::RainGain(RainGainCurve.GetData(), RainGainCurve.Num(), Intensity);
	}
	FString FootstepDriver = TEXT("auto");
	TMap<FString, FVector2D> StrideByCharacter;
	double StrideFor(const FString& Id, bool bRunning) const
	{
		const FVector2D* Pair = StrideByCharacter.Find(Id);
		return Pair ? (bRunning ? Pair->Y : Pair->X) : (bRunning ? RunStride : WalkStride);
	}
	TMap<FString, double> StateCrossfadeSeconds;
	double FadeSeconds(const FString& Destination) const
	{
		const double* Override = StateCrossfadeSeconds.Find(Destination);
		return Override ? *Override : CrossfadeSeconds;
	}
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
