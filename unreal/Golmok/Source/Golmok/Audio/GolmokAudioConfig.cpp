#include "Audio/GolmokAudioConfig.h"

#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace GolmokAudio
{
	using FObject = TSharedPtr<FJsonObject>;
	// A reader owns no data and reports the first failed field at its full JSON path.
	struct FConfigReader
	{
		FObject Data; FString Path; FString& Error;
		FString Field(const FString& Key) const { return Path.IsEmpty() ? Key : (Key.IsEmpty() ? Path : Path + TEXT(".") + Key); }
		bool Check(bool bValid, const FString& Key, const TCHAR* Expected) const
		{
			if (!bValid) Error = FString::Printf(TEXT("audio.json %s: expected %s"), *Field(Key), Expected);
			return bValid;
		}
		bool Valid() const { return Check(Data.IsValid(), TEXT(""), TEXT("object")); }
		FConfigReader Child(const TCHAR* Key) const
		{
			const FObject* Value = nullptr;
			const bool bFound = Data.IsValid() && Data->TryGetObjectField(Key, Value);
			return {bFound ? *Value : nullptr, Field(Key), Error};
		}
		bool Number(const TCHAR* Key, double& Out, double Low, double High) const
		{
			const FString Expected = FString::Printf(TEXT("finite number in [%g, %g]"), Low, High);
			return Check(Data.IsValid() && Data->HasTypedField<EJson::Number>(Key)
				&& Data->TryGetNumberField(Key, Out) && FMath::IsFinite(Out) && Out >= Low && Out <= High, Key, *Expected);
		}
		bool String(const TCHAR* Key, FString& Out, bool bAllowEmpty = false) const
		{
			return Check(Data.IsValid() && Data->HasTypedField<EJson::String>(Key) && Data->TryGetStringField(Key, Out)
				&& (bAllowEmpty || !Out.IsEmpty()) && !Out.Contains(TEXT("\n")), Key, TEXT("single-line string"));
		}
		bool Boolean(const TCHAR* Key, bool& Out) const
		{
			return Check(Data.IsValid() && Data->HasTypedField<EJson::Boolean>(Key) && Data->TryGetBoolField(Key, Out), Key, TEXT("boolean"));
		}
		bool Range(const TCHAR* Key, double& Low, double& High, double Min, double Max) const
		{
			const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
			if (!Check(Data.IsValid() && Data->TryGetArrayField(Key, Values) && Values->Num() == 2, Key, TEXT("array of two numbers"))) return false;
			double* Outputs[] = {&Low, &High};
			for (int32 Index = 0; Index < 2; ++Index)
			{
				const auto& Value = (*Values)[Index];
				const FString Expected = FString::Printf(TEXT("finite number in [%g, %g]"), Min, Max);
				if (!Check(Value->Type == EJson::Number && Value->TryGetNumber(*Outputs[Index]) && FMath::IsFinite(*Outputs[Index])
					&& *Outputs[Index] >= Min && *Outputs[Index] <= Max, FString::Printf(TEXT("%s[%d]"), Key, Index), *Expected)) return false;
			}
			return Check(High >= Low, Key, TEXT("ascending number pair"));
		}
	};
	bool VerifiedDate(const FString& Value)
	{
		if (Value.Len() != 10 || Value[4] != '-' || Value[7] != '-') return false;
		for (int32 Index = 0; Index < 10; ++Index)
			if (Index != 4 && Index != 7 && (Value[Index] < '0' || Value[Index] > '9')) return false;
		return FDateTime::Validate(FCString::Atoi(*Value.Left(4)), FCString::Atoi(*Value.Mid(5, 2)), FCString::Atoi(*Value.Right(2)), 0, 0, 0, 0);
	}
	bool ParseConfig(const FString& Json, FGolmokAudioConfig& Out, FString& Error)
	{
		Error.Empty();
		FObject RootObject;
		if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), RootObject) || !RootObject.IsValid())
		{ Error = TEXT("audio.json $: expected valid JSON object"); return false; }
		const FConfigReader Root{RootObject, TEXT(""), Error};
		FGolmokAudioConfig Next;
		double Version = 0; FString Pause;
		if (!Root.Number(TEXT("schema_version"), Version, 1, 1)
			|| !Root.Number(TEXT("master_volume"), Next.MasterVolume, 0, 1)
			|| !Root.Number(TEXT("crossfade_seconds"), Next.CrossfadeSeconds, 0, 30)
			|| !Root.String(TEXT("pause_policy"), Pause)
			|| !Root.Check(Pause == TEXT("mute") || Pause == TEXT("maintain"), TEXT("pause_policy"), TEXT("mute or maintain"))) return false;
		Next.bMuteInPhoto = Pause == TEXT("mute");
		if (Root.Data->HasField(TEXT("photo_mute_fade_seconds")) && !Root.Number(TEXT("photo_mute_fade_seconds"), Next.PhotoMuteFadeSeconds, 0, 5)) return false;
		if (Root.Data->HasField(TEXT("crossfade_seconds_by_state")))
		{
			const auto Durations = Root.Child(TEXT("crossfade_seconds_by_state"));
			if (!Durations.Valid()) return false;
			for (const auto& Pair : Durations.Data->Values)
			{
				const FString Key(*Pair.Key); double Seconds = 0;
				if (!Durations.Check(Key == TEXT("outdoor_day") || Key == TEXT("outdoor_night") || Key == TEXT("interior"), Key, TEXT("known ambience state"))
					|| !Durations.Number(*Key, Seconds, 0, 30)) return false;
				Next.StateCrossfadeSeconds.Add(Key, Seconds);
			}
		}
		const auto Assets = Root.Child(TEXT("assets"));
		if (!Assets.Valid() || !Assets.Check(!Assets.Data->Values.IsEmpty(), TEXT(""), TEXT("nonempty object"))) return false;
		TSet<FString> Paths;
		for (const auto& Pair : Assets.Data->Values)
		{
			const auto Item = Assets.Child(*Pair.Key);
			if (!Item.Valid()) return false;
			FGolmokAudioAsset Asset;
			FString Title, Author, Source, License, LicenseUrl, Changes, Verified; double Gain = 0; bool bPlaceholder = false;
			if (!Item.String(TEXT("asset"), Asset.Path)
				|| !Item.Check(Asset.Path.StartsWith(TEXT("/Game/Golmok/Audio/")) && !Asset.Path.Contains(TEXT("..")), TEXT("asset"), TEXT("path under /Game/Golmok/Audio/"))
				|| !Item.Boolean(TEXT("loop"), Asset.bLoop) || !Item.Number(TEXT("gain"), Gain, 0, 1)
				|| !Item.String(TEXT("title"), Title) || !Item.String(TEXT("author"), Author) || !Item.String(TEXT("source_url"), Source)
				|| !Item.String(TEXT("verified"), Verified) || !Item.Check(VerifiedDate(Verified), TEXT("verified"), TEXT("valid YYYY-MM-DD date"))
				|| !Item.String(TEXT("license"), License) || !Item.String(TEXT("changes"), Changes) || !Item.String(TEXT("license_url"), LicenseUrl, true)
				|| !Item.Check(!Paths.Contains(Asset.Path.ToLower()), TEXT("asset"), TEXT("unique asset path"))
				|| !Item.Check(License == TEXT("project-generated") || License == TEXT("CC0-1.0") || License == TEXT("CC-BY-4.0"), TEXT("license"), TEXT("approved license"))
				|| !Item.Boolean(TEXT("placeholder"), bPlaceholder) || !Item.Check(Source.StartsWith(TEXT("https://")), TEXT("source_url"), TEXT("HTTPS URL"))) return false;
			if (License == TEXT("project-generated"))
			{
				if (!Item.Check(bPlaceholder, TEXT("placeholder"), TEXT("true for project-generated audio"))
					|| !Item.Check(LicenseUrl.IsEmpty(), TEXT("license_url"), TEXT("empty string for project-generated audio"))) return false;
			}
			if (License == TEXT("CC0-1.0") && !Item.Check(LicenseUrl == TEXT("https://creativecommons.org/publicdomain/zero/1.0/"), TEXT("license_url"), TEXT("CC0-1.0 license URL"))) return false;
			if (License == TEXT("CC-BY-4.0") && !Item.Check(LicenseUrl == TEXT("https://creativecommons.org/licenses/by/4.0/"), TEXT("license_url"), TEXT("CC-BY-4.0 license URL"))) return false;
			Paths.Add(Asset.Path.ToLower()); Next.Assets.Add(FString(*Pair.Key), Asset);
			Next.Credits += FString::Printf(TEXT("%s — %s\n%s\n%s %s\nVerified: %s\n%s\n\n"), *Title, *Author, *Source, *License, *LicenseUrl, *Verified, *Changes);
		}
		const auto Ambience = Root.Child(TEXT("ambience"));
		const auto Presets = Root.Child(TEXT("preset_states"));
		const auto Steps = Root.Child(TEXT("footsteps"));
		if (!Ambience.Valid() || !Ambience.Check(Ambience.Data->Values.Num() == 3, TEXT(""), TEXT("three ambience states")) || !Presets.Valid() || !Steps.Valid()) return false;
		for (const TCHAR* Name : {TEXT("outdoor_day"), TEXT("outdoor_night"), TEXT("interior")})
		{
			FString Key;
			if (!Ambience.String(Name, Key) || !Ambience.Check(Next.Assets.Contains(Key) && Next.Assets[Key].bLoop, Name, TEXT("looping asset id"))) return false;
			Next.Ambience.Add(Name, Key);
		}
		for (const auto& Pair : Presets.Data->Values)
		{
			FString State;
			if (!Presets.Check(Pair.Value->Type == EJson::String && Pair.Value->TryGetString(State), FString(*Pair.Key), TEXT("string"))
				|| !Presets.Check(State == TEXT("outdoor_day") || State == TEXT("outdoor_night"), FString(*Pair.Key), TEXT("outdoor state id"))) return false;
			Next.Presets.Add(FString(*Pair.Key), State);
		}
		if (!Steps.Number(TEXT("walk_stride_cm"), Next.WalkStride, 1, 10000) || !Steps.Number(TEXT("run_stride_cm"), Next.RunStride, 1, 10000)
			|| !Steps.Number(TEXT("run_threshold_cm_s"), Next.RunThreshold, 1, 10000) || !Steps.Number(TEXT("teleport_threshold_cm"), Next.TeleportLimit, 1, 10000)
			|| !Steps.Range(TEXT("pitch_range"), Next.PitchMin, Next.PitchMax, .5, 2) || !Steps.Range(TEXT("volume_range"), Next.VolumeMin, Next.VolumeMax, 0, 1)
			|| !Steps.String(TEXT("landing"), Next.Landing)) return false;
		if (!Steps.Check(!Steps.Data->HasField(TEXT("stride_scale_by_mesh")), TEXT("stride_scale_by_mesh"), TEXT("field absent; use stride_cm_by_character"))) return false;
		if (Steps.Data->HasField(TEXT("stride_cm_by_character")))
		{
			const auto Strides = Steps.Child(TEXT("stride_cm_by_character"));
			if (!Strides.Valid()) return false;
			for (const auto& Pair : Strides.Data->Values)
			{
				const FString Id(*Pair.Key);
				bool bValidId = !Id.IsEmpty() && Id.Len() <= 48 && Id[0] >= 'a' && Id[0] <= 'z';
				for (const TCHAR C : Id) if (!(C >= 'a' && C <= 'z') && !(C >= '0' && C <= '9') && C != '_') bValidId = false;
				if (!Strides.Check(bValidId, Id, TEXT("character id [a-z][a-z0-9_]{0,47}"))) return false;
				const auto Entry = Strides.Child(*Id); double Walk = 0, Run = 0;
				if (!Entry.Valid() || !Entry.Check(Entry.Data->Values.Num() == 2, TEXT(""), TEXT("object with walk and run"))
					|| !Entry.Number(TEXT("walk"), Walk, 1, 10000) || !Entry.Number(TEXT("run"), Run, 1, 10000)) return false;
				Next.StrideByCharacter.Add(Id, FVector2D(Walk, Run));
			}
		}
		const auto Sets = Steps.Child(TEXT("sets")); const auto Surfaces = Steps.Child(TEXT("surface_sets"));
		if (!Sets.Valid() || !Surfaces.Valid() || !Steps.Check(Next.Assets.Contains(Next.Landing) && !Next.Assets[Next.Landing].bLoop, TEXT("landing"), TEXT("one-shot asset id"))) return false;
		for (const auto& Pair : Sets.Data->Values)
		{
			if (!Sets.Check(Pair.Value->Type == EJson::Array && !Pair.Value->AsArray().IsEmpty(), FString(*Pair.Key), TEXT("nonempty array"))) return false;
			TArray<FString> List; int32 Index = 0;
			for (const auto& Value : Pair.Value->AsArray())
			{
				FString Key; const FString Field = FString::Printf(TEXT("%s[%d]"), *Pair.Key, Index++);
				if (!Sets.Check(Value->Type == EJson::String && Value->TryGetString(Key), Field, TEXT("string"))
					|| !Sets.Check(Next.Assets.Contains(Key) && !Next.Assets[Key].bLoop, Field, TEXT("one-shot asset id"))) return false;
				List.Add(Key);
			}
			Next.Sets.Add(FString(*Pair.Key), List);
		}
		for (const TCHAR* Name : {TEXT("default"), TEXT("asphalt"), TEXT("tile"), TEXT("stairs")}) if (!Sets.Check(Next.Sets.Contains(Name), Name, TEXT("required footstep set"))) return false;
		for (const auto& Pair : Surfaces.Data->Values)
		{
			FString Set; const FString Key(*Pair.Key);
			bool bDigits = !Key.IsEmpty(); for (const TCHAR C : Key) if (!FChar::IsDigit(C)) bDigits = false;
			if (!Surfaces.Check(bDigits, Key, TEXT("surface number 0..62"))) return false;
			if (!Surfaces.Check(Pair.Value->Type == EJson::String && Pair.Value->TryGetString(Set), Key, TEXT("string"))
				|| !Surfaces.Check(Next.Sets.Contains(Set), Key, TEXT("footstep set id"))) return false;
			const int32 Surface = FCString::Atoi(*Pair.Key);
			if (!Surfaces.Check(Surface >= 0 && Surface <= 62, Key, TEXT("surface number 0..62"))) return false;
			Next.Surfaces.Add(Surface, Set);
		}
		Out = MoveTemp(Next); Error.Empty(); return true;
	}
	bool LoadConfig(FGolmokAudioConfig& Out, FString& Error)
	{
		FString Text;
		if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectConfigDir() / TEXT("Golmok/audio.json"))))
		{ Error = TEXT("audio.json $: expected readable Config/Golmok/audio.json"); return false; }
		return ParseConfig(Text, Out, Error);
	}
}
