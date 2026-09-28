#include "Audio/GolmokAudioConfig.h"

#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace GolmokAudio
{
	using FObject = TSharedPtr<FJsonObject>;
	FObject Object(const FObject& Parent, const TCHAR* Key)
	{
		const FObject* Value = nullptr;
		return Parent.IsValid() && Parent->TryGetObjectField(Key, Value) ? *Value : nullptr;
	}
	bool Number(const FObject& Parent, const TCHAR* Key, double& Out, double Low, double High)
	{
		return Parent.IsValid() && Parent->TryGetNumberField(Key, Out) && FMath::IsFinite(Out) && Out >= Low && Out <= High;
	}
	bool String(const FObject& Parent, const TCHAR* Key, FString& Out)
	{
		return Parent.IsValid() && Parent->TryGetStringField(Key, Out) && !Out.IsEmpty() && !Out.Contains(TEXT("\n"));
	}
	bool Range(const FObject& Parent, const TCHAR* Key, double& Low, double& High, double Min, double Max)
	{
		const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
		return Parent.IsValid() && Parent->TryGetArrayField(Key, Values) && Values->Num() == 2
			&& (*Values)[0]->TryGetNumber(Low) && (*Values)[1]->TryGetNumber(High)
			&& FMath::IsFinite(Low) && FMath::IsFinite(High) && Low >= Min && High >= Low && High <= Max;
	}
	bool ParseConfig(const FString& Json, FGolmokAudioConfig& Out, FString& Error)
	{
		Error = TEXT("invalid audio.json schema, values or references");
		FObject Root;
		if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root.IsValid()) return false;
		FGolmokAudioConfig Next;
		double Version = 0;
		FString Pause;
		if (!Number(Root, TEXT("schema_version"), Version, 1, 1)
			|| !Number(Root, TEXT("master_volume"), Next.MasterVolume, 0, 1)
			|| !Number(Root, TEXT("crossfade_seconds"), Next.CrossfadeSeconds, 0, 30)
			|| !String(Root, TEXT("pause_policy"), Pause) || (Pause != TEXT("mute") && Pause != TEXT("maintain"))) return false;
		Next.bMuteInPhoto = Pause == TEXT("mute");
		if (Root->HasField(TEXT("crossfade_seconds_by_state")))
		{
			const FObject Durations = Object(Root, TEXT("crossfade_seconds_by_state"));
			if (!Durations.IsValid()) return false;
			for (const auto& Pair : Durations->Values)
			{
				const FString Key(*Pair.Key);
				double Seconds = 0;
				if ((Key != TEXT("outdoor_day") && Key != TEXT("outdoor_night") && Key != TEXT("interior"))
					|| !Number(Durations, *Key, Seconds, 0, 30)) return false;
				Next.StateCrossfadeSeconds.Add(Key, Seconds);
			}
		}
		const FObject Assets = Object(Root, TEXT("assets"));
		if (!Assets.IsValid() || Assets->Values.IsEmpty()) return false;
		TSet<FString> Paths;
		for (const auto& Pair : Assets->Values)
		{
			if (Pair.Value->Type != EJson::Object) return false;
			const FObject Item = Pair.Value->AsObject();
			FGolmokAudioAsset Asset;
			FString Title, Author, Source, License, LicenseUrl, Changes;
			double Gain = 0;
			if (!String(Item, TEXT("asset"), Asset.Path) || !Asset.Path.StartsWith(TEXT("/Game/Golmok/Audio/"))
				|| Asset.Path.Contains(TEXT("..")) || !Item->TryGetBoolField(TEXT("loop"), Asset.bLoop)
				|| !Number(Item, TEXT("gain"), Gain, 0, 1) || !String(Item, TEXT("title"), Title)
				|| !String(Item, TEXT("author"), Author) || !String(Item, TEXT("source_url"), Source)
				|| !String(Item, TEXT("license"), License) || !String(Item, TEXT("changes"), Changes)
				|| !Item->TryGetStringField(TEXT("license_url"), LicenseUrl) || Paths.Contains(Asset.Path.ToLower())) return false;
			if (License != TEXT("project-generated") && License != TEXT("CC0-1.0") && License != TEXT("CC-BY-4.0")) return false;
			bool bPlaceholder = false;
			if (!Item->TryGetBoolField(TEXT("placeholder"), bPlaceholder) || !Source.StartsWith(TEXT("https://"))) return false;
			if (License == TEXT("project-generated") && (!bPlaceholder || !LicenseUrl.IsEmpty())) return false;
			if (License == TEXT("CC0-1.0") && LicenseUrl != TEXT("https://creativecommons.org/publicdomain/zero/1.0/")) return false;
			if (License == TEXT("CC-BY-4.0") && LicenseUrl != TEXT("https://creativecommons.org/licenses/by/4.0/")) return false;
			Paths.Add(Asset.Path.ToLower());
			Next.Assets.Add(FString(*Pair.Key), Asset);
			Next.Credits += FString::Printf(TEXT("%s — %s\n%s\n%s %s\n%s\n\n"), *Title, *Author, *Source, *License, *LicenseUrl, *Changes);
		}
		const FObject Ambience = Object(Root, TEXT("ambience")), Presets = Object(Root, TEXT("preset_states")), Steps = Object(Root, TEXT("footsteps"));
		if (!Ambience.IsValid() || Ambience->Values.Num() != 3 || !Presets.IsValid() || !Steps.IsValid()) return false;
		for (const TCHAR* Name : {TEXT("outdoor_day"), TEXT("outdoor_night"), TEXT("interior")})
		{
			FString Key;
			if (!String(Ambience, Name, Key) || !Next.Assets.Contains(Key) || !Next.Assets[Key].bLoop) return false;
			Next.Ambience.Add(Name, Key);
		}
		for (const auto& Pair : Presets->Values)
		{
			FString State;
			if (!Pair.Value->TryGetString(State) || (State != TEXT("outdoor_day") && State != TEXT("outdoor_night"))) return false;
			Next.Presets.Add(FString(*Pair.Key), State);
		}
		if (!Number(Steps, TEXT("walk_stride_cm"), Next.WalkStride, 1, 10000)
			|| !Number(Steps, TEXT("run_stride_cm"), Next.RunStride, 1, 10000)
			|| !Number(Steps, TEXT("run_threshold_cm_s"), Next.RunThreshold, 1, 10000)
			|| !Number(Steps, TEXT("teleport_threshold_cm"), Next.TeleportLimit, 1, 10000)
			|| !Range(Steps, TEXT("pitch_range"), Next.PitchMin, Next.PitchMax, .5, 2)
			|| !Range(Steps, TEXT("volume_range"), Next.VolumeMin, Next.VolumeMax, 0, 1)
			|| !String(Steps, TEXT("landing"), Next.Landing)) return false;
		const FObject Sets = Object(Steps, TEXT("sets")), Surfaces = Object(Steps, TEXT("surface_sets"));
		if (!Sets.IsValid() || !Surfaces.IsValid() || !Next.Assets.Contains(Next.Landing) || Next.Assets[Next.Landing].bLoop) return false;
		for (const auto& Pair : Sets->Values)
		{
			if (Pair.Value->Type != EJson::Array || Pair.Value->AsArray().IsEmpty()) return false;
			TArray<FString> List;
			for (const auto& Value : Pair.Value->AsArray())
			{
				FString Key;
				if (!Value->TryGetString(Key) || !Next.Assets.Contains(Key) || Next.Assets[Key].bLoop) return false;
				List.Add(Key);
			}
			Next.Sets.Add(FString(*Pair.Key), List);
		}
		for (const TCHAR* Name : {TEXT("default"), TEXT("asphalt"), TEXT("tile"), TEXT("stairs")}) if (!Next.Sets.Contains(Name)) return false;
		for (const auto& Pair : Surfaces->Values)
		{
			FString Set;
			const FString SurfaceKey(*Pair.Key);
			if (SurfaceKey.IsEmpty()) return false;
			for (const TCHAR Character : SurfaceKey) if (!FChar::IsDigit(Character)) return false;
			if (!Pair.Value->TryGetString(Set) || !Next.Sets.Contains(Set)) return false;
			const int32 Surface = FCString::Atoi(*Pair.Key);
			if (Surface < 0 || Surface > 62) return false;
			Next.Surfaces.Add(Surface, Set);
		}
		Out = MoveTemp(Next); Error.Empty(); return true;
	}
	bool LoadConfig(FGolmokAudioConfig& Out, FString& Error)
	{
		FString Text;
		if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectConfigDir() / TEXT("Golmok/audio.json"))))
		{ Error = TEXT("audio.json not found"); return false; }
		return ParseConfig(Text, Out, Error);
	}
}
