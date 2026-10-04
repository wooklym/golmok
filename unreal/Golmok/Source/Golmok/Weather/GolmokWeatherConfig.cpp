#include "Weather/GolmokWeatherConfig.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Lighting/GolmokClockMath.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include <initializer_list>

// Strict weather.json parser (design section 6). golmok/weather_pure.py parse_config is the mirror: same check
// order, byte-identical messages "weather.json: <where>: <reason>" (<where> = "root", dotted keys, [index]).
// FJsonObject's map compares keys case-insensitively, so every key lookup here goes through FindExact.

namespace GolmokWeather
{
	namespace ConfigJson
	{
		using FJsonObjectPtr = TSharedPtr<FJsonObject>;
		using FJsonValuePtr = TSharedPtr<FJsonValue>;

		constexpr double SchemaVersion = 1.0;
		constexpr double MaxSpawnRate = 20000.0;
		constexpr double MinBoxHalfExtent = 100.0;
		constexpr double MaxBoxHalfExtent = 5000.0;
		constexpr double MinHeightOffset = -1000.0;
		constexpr double MaxHeightOffset = 3000.0;
		const TCHAR* GamePrefix = TEXT("/Game/");

		/** Error = "weather.json: <Where>: <Reason>"; returns false so callers can `return Fail(...)`. */
		bool Fail(FString& Error, const FString& Where, const FString& Reason)
		{
			Error = FString::Printf(TEXT("weather.json: %s: %s"), *Where, *Reason);
			return false;
		}

		/** "[0.05, 1]" / "(0, 2]" / "[0, 1)" with printf %g (Python f"{v:g}"). */
		FString RangeText(double Lo, double Hi, bool bLoExclusive = false, bool bHiExclusive = false)
		{
			return FString::Printf(TEXT("%s%g, %g%s"), bLoExclusive ? TEXT("(") : TEXT("["), Lo, Hi, bHiExclusive ? TEXT(")") : TEXT("]"));
		}

		FJsonValuePtr FindExact(const FJsonObjectPtr& Object, const TCHAR* Name)
		{
			if (!Object.IsValid())
			{
				return nullptr;
			}
			// UE 5.8 keys Values by UE::FSharedString (repo precedent: GolmokPhotoModeSubsystem.cpp, GolmokTimeOfDay.cpp).
			for (const auto& Pair : Object->Values)
			{
				const FString Key(*Pair.Key);
				if (Key.Equals(Name, ESearchCase::CaseSensitive))
				{
					return Pair.Value;
				}
			}
			return nullptr;
		}

		bool Has(const FJsonObjectPtr& Object, const TCHAR* Name)
		{
			return FindExact(Object, Name).IsValid();
		}

		bool IsListed(std::initializer_list<const TCHAR*> Names, const FString& Key)
		{
			for (const TCHAR* Name : Names)
			{
				if (Key.Equals(Name, ESearchCase::CaseSensitive))
				{
					return true;
				}
			}
			return false;
		}

		/** First missing required key (schema order), then the first unknown key (code-point order). */
		bool CheckKeys(const FJsonObjectPtr& Object, const FString& Where, std::initializer_list<const TCHAR*> Required,
			std::initializer_list<const TCHAR*> Optional, FString& Error)
		{
			for (const TCHAR* Name : Required)
			{
				if (!Has(Object, Name))
				{
					return Fail(Error, Where, FString::Printf(TEXT("missing key \"%s\""), Name));
				}
			}
			TArray<FString> Unknown;
			for (const auto& Pair : Object->Values)
			{
				const FString Key(*Pair.Key);
				if (!IsListed(Required, Key) && !IsListed(Optional, Key))
				{
					Unknown.Add(Key);
				}
			}
			if (Unknown.Num() > 0)
			{
				Unknown.Sort([](const FString& A, const FString& B) { return A.Compare(B, ESearchCase::CaseSensitive) < 0; });
				return Fail(Error, Where, FString::Printf(TEXT("unknown key \"%s\""), *Unknown[0]));
			}
			return true;
		}

		bool GetObject(const FJsonValuePtr& Value, const FString& Where, FJsonObjectPtr& Out, FString& Error)
		{
			if (!Value.IsValid() || Value->Type != EJson::Object || !Value->AsObject().IsValid())
			{
				return Fail(Error, Where, TEXT("must be an object"));
			}
			Out = Value->AsObject();
			return true;
		}

		bool IsFiniteNumber(const FJsonValuePtr& Value)
		{
			return Value.IsValid() && Value->Type == EJson::Number && FMath::IsFinite(Value->AsNumber());
		}

		bool GetNumber(const FJsonValuePtr& Value, const FString& Where, double Lo, double Hi, bool bLoExclusive, bool bHiExclusive,
			double& Out, FString& Error)
		{
			bool bOk = IsFiniteNumber(Value);
			if (bOk)
			{
				const double V = Value->AsNumber();
				bOk = (bLoExclusive ? V > Lo : V >= Lo) && (bHiExclusive ? V < Hi : V <= Hi);
			}
			if (!bOk)
			{
				return Fail(Error, Where, TEXT("must be a number in ") + RangeText(Lo, Hi, bLoExclusive, bHiExclusive));
			}
			Out = Value->AsNumber();
			return true;
		}

		bool GetNumber(const FJsonValuePtr& Value, const FString& Where, double Lo, double Hi, double& Out, FString& Error)
		{
			return GetNumber(Value, Where, Lo, Hi, false, false, Out, Error);
		}

		/** A JSON string without an embedded NUL ("rain\u0000x" must not parse as "rain" through the C string; Python rejects it too). */
		bool IsPlainString(const FJsonValuePtr& Value)
		{
			return Value->Type == EJson::String && FCString::Strlen(*Value->AsString()) == Value->AsString().Len();
		}

		/** "state" (and "intensity" for rain only) of initial / a schedule slot; the key set is already checked. */
		bool GetStateAndIntensity(const FJsonObjectPtr& Object, const FString& Where, GolmokWeatherMath::State& OutState,
			double& OutIntensity, FString& Error)
		{
			const FJsonValuePtr StateValue = FindExact(Object, TEXT("state"));
			if (!IsPlainString(StateValue) || !GolmokWeatherMath::ParseState(*StateValue->AsString(), OutState))
			{
				return Fail(Error, Where + TEXT(".state"), TEXT("must be clear, overcast or rain"));
			}
			const FJsonValuePtr Intensity = FindExact(Object, TEXT("intensity"));
			if (OutState == GolmokWeatherMath::State::Rain)
			{
				if (!Intensity.IsValid())
				{
					return Fail(Error, Where + TEXT(".intensity"), TEXT("required for rain"));
				}
				return GetNumber(Intensity, Where + TEXT(".intensity"), GolmokWeatherMath::MinRainIntensity,
					GolmokWeatherMath::MaxRainIntensity, OutIntensity, Error);
			}
			if (Intensity.IsValid())
			{
				return Fail(Error, Where + TEXT(".intensity"), TEXT("only allowed for rain"));
			}
			OutIntensity = 0.0;
			return true;
		}

		/** "/Game/<...>/Package.Object": a /Game/ path whose last segment names an object. */
		bool GetObjectPath(const FJsonValuePtr& Value, const FString& Where, FString& Out, FString& Error)
		{
			bool bOk = Value.IsValid() && Value->Type == EJson::String;
			if (bOk)
			{
				const FString Text = Value->AsString();
				int32 Slash = INDEX_NONE;
				Text.FindLastChar(TEXT('/'), Slash);
				bOk = Text.StartsWith(GamePrefix, ESearchCase::CaseSensitive) && Text.Mid(Slash + 1).Contains(TEXT("."));
				Out = Text;
			}
			return bOk ? true : Fail(Error, Where, TEXT("must be an object path /Game/.../Package.Object"));
		}

		bool GetModifier(const FJsonValuePtr& Value, const FString& Where, GolmokWeatherMath::Modifier& Out, FString& Error)
		{
			FJsonObjectPtr Object;
			if (!GetObject(Value, Where, Object, Error)
				|| !CheckKeys(Object, Where,
					{TEXT("lux_scale"), TEXT("sky_scale"), TEXT("fog_scale"), TEXT("fog_height_falloff_scale"), TEXT("kelvin_target"),
						TEXT("kelvin_weight"), TEXT("exposure_offset")},
					{}, Error))
			{
				return false;
			}
			for (int32 Index = 0; Index < GolmokWeatherMath::ModifierFieldCount; ++Index)
			{
				const GolmokWeatherMath::FieldRange& Range = GolmokWeatherMath::ModifierField(Index);
				const FString Key(UTF8_TO_TCHAR(Range.Key));
				double V = 0.0;
				if (!GetNumber(FindExact(Object, *Key), Where + TEXT(".") + Key, Range.Min, Range.Max, Range.bMinExclusive, false, V, Error))
				{
					return false;
				}
				GolmokWeatherMath::SetField(Out, Index, V);
			}
			return true;
		}
	} // namespace ConfigJson
} // namespace GolmokWeather

bool GolmokWeather::ParseConfigText(const FString& Json, FConfig& Out, FString& Error)
{
	using namespace GolmokWeather::ConfigJson;

	FJsonObjectPtr Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Json);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		return Fail(Error, TEXT("root"), TEXT("not a JSON object"));
	}

	const FJsonValuePtr Version = FindExact(Root, TEXT("schema_version"));
	if (!IsFiniteNumber(Version) || Version->AsNumber() != SchemaVersion)
	{
		return Fail(Error, TEXT("schema_version"), TEXT("must be 1"));
	}
	if (!CheckKeys(Root, TEXT("root"),
			{TEXT("schema_version"), TEXT("initial"), TEXT("transition_seconds"), TEXT("rain_levels"), TEXT("modifiers"), TEXT("surface"),
				TEXT("schedule"), TEXT("rain_fx"), TEXT("mpc")},
			{}, Error))
	{
		return false;
	}

	FConfig C;
	C.SchemaVersion = 1;

	// initial
	FJsonObjectPtr Initial;
	if (!GetObject(FindExact(Root, TEXT("initial")), TEXT("initial"), Initial, Error)
		|| !CheckKeys(Initial, TEXT("initial"), {TEXT("state"), TEXT("mode")}, {TEXT("intensity")}, Error)
		|| !GetStateAndIntensity(Initial, TEXT("initial"), C.InitialState, C.InitialIntensity, Error))
	{
		return false;
	}
	const FJsonValuePtr Mode = FindExact(Initial, TEXT("mode"));
	const FString ModeText = Mode->Type == EJson::String ? Mode->AsString() : FString();
	if (Mode->Type != EJson::String
		|| !(ModeText.Equals(TEXT("fixed"), ESearchCase::CaseSensitive) || ModeText.Equals(TEXT("schedule"), ESearchCase::CaseSensitive)))
	{
		return Fail(Error, TEXT("initial.mode"), TEXT("must be fixed or schedule"));
	}
	C.bInitialSchedule = ModeText.Equals(TEXT("schedule"), ESearchCase::CaseSensitive);

	if (!GetNumber(FindExact(Root, TEXT("transition_seconds")), TEXT("transition_seconds"), 0.0, GolmokWeatherMath::MaxTransitionSeconds,
			C.TransitionSeconds, Error))
	{
		return false;
	}

	// rain_levels
	FJsonObjectPtr Levels;
	if (!GetObject(FindExact(Root, TEXT("rain_levels")), TEXT("rain_levels"), Levels, Error)
		|| !CheckKeys(Levels, TEXT("rain_levels"), {TEXT("light"), TEXT("moderate"), TEXT("heavy")}, {}, Error)
		|| !GetNumber(FindExact(Levels, TEXT("light")), TEXT("rain_levels.light"), GolmokWeatherMath::MinRainIntensity,
			GolmokWeatherMath::MaxRainIntensity, C.RainLight, Error)
		|| !GetNumber(FindExact(Levels, TEXT("moderate")), TEXT("rain_levels.moderate"), GolmokWeatherMath::MinRainIntensity,
			GolmokWeatherMath::MaxRainIntensity, C.RainModerate, Error)
		|| !GetNumber(FindExact(Levels, TEXT("heavy")), TEXT("rain_levels.heavy"), GolmokWeatherMath::MinRainIntensity,
			GolmokWeatherMath::MaxRainIntensity, C.RainHeavy, Error))
	{
		return false;
	}
	if (!(C.RainLight < C.RainModerate && C.RainModerate < C.RainHeavy))
	{
		return Fail(Error, TEXT("rain_levels"), TEXT("must increase strictly (light < moderate < heavy)"));
	}

	// modifiers (clear is the identity, never listed)
	FJsonObjectPtr Modifiers;
	if (!GetObject(FindExact(Root, TEXT("modifiers")), TEXT("modifiers"), Modifiers, Error))
	{
		return false;
	}
	if (Has(Modifiers, TEXT("clear")))
	{
		return Fail(Error, TEXT("modifiers.clear"), TEXT("clear is the identity and must not be listed"));
	}
	if (!CheckKeys(Modifiers, TEXT("modifiers"), {TEXT("overcast"), TEXT("rain")}, {}, Error)
		|| !GetModifier(FindExact(Modifiers, TEXT("overcast")), TEXT("modifiers.overcast"), C.Overcast, Error)
		|| !GetModifier(FindExact(Modifiers, TEXT("rain")), TEXT("modifiers.rain"), C.Rain, Error))
	{
		return false;
	}

	// surface
	FJsonObjectPtr Surface;
	if (!GetObject(FindExact(Root, TEXT("surface")), TEXT("surface"), Surface, Error)
		|| !CheckKeys(Surface, TEXT("surface"),
			{TEXT("wet_seconds"), TEXT("dry_seconds"), TEXT("puddle_min_intensity"), TEXT("puddle_fill_seconds"), TEXT("puddle_dry_seconds")},
			{}, Error))
	{
		return false;
	}
	struct FSurfaceField
	{
		const TCHAR* Key;
		double* Value;
	};
	const FSurfaceField SurfaceFields[] = {
		{TEXT("wet_seconds"), &C.Surface.WetSeconds},
		{TEXT("dry_seconds"), &C.Surface.DrySeconds},
		{TEXT("puddle_min_intensity"), &C.Surface.PuddleMinIntensity},
		{TEXT("puddle_fill_seconds"), &C.Surface.PuddleFillSeconds},
		{TEXT("puddle_dry_seconds"), &C.Surface.PuddleDrySeconds},
	};
	for (const FSurfaceField& Field : SurfaceFields)
	{
		const FString Where = FString(TEXT("surface.")) + Field.Key;
		const FJsonValuePtr Value = FindExact(Surface, Field.Key);
		if (FCString::Strcmp(Field.Key, TEXT("puddle_min_intensity")) == 0)
		{
			if (!GetNumber(Value, Where, 0.0, 1.0, false, true, *Field.Value, Error))
			{
				return false;
			}
		}
		else if (!IsFiniteNumber(Value) || !(Value->AsNumber() > 0.0))
		{
			return Fail(Error, Where, TEXT("must be a positive number"));
		}
		else
		{
			*Field.Value = Value->AsNumber();
		}
	}

	// schedule
	const FJsonValuePtr ScheduleValue = FindExact(Root, TEXT("schedule"));
	if (ScheduleValue->Type != EJson::Array || ScheduleValue->AsArray().Num() == 0)
	{
		return Fail(Error, TEXT("schedule"), TEXT("must be a non-empty array"));
	}
	const TArray<FJsonValuePtr>& Items = ScheduleValue->AsArray();
	for (int32 Index = 0; Index < Items.Num(); ++Index)
	{
		const FString Where = FString::Printf(TEXT("schedule[%d]"), Index);
		FJsonObjectPtr Item;
		if (!GetObject(Items[Index], Where, Item, Error) || !CheckKeys(Item, Where, {TEXT("time"), TEXT("state")}, {TEXT("intensity")}, Error))
		{
			return false;
		}
		const FJsonValuePtr Time = FindExact(Item, TEXT("time"));
		int32 Minutes = 0;
		if (!IsPlainString(Time) || !GolmokClockMath::ParseHHMM(*Time->AsString(), Minutes))
		{
			return Fail(Error, Where + TEXT(".time"), TEXT("must be HH:MM (00:00-23:59)"));
		}
		FScheduleSlot Slot;
		Slot.Minutes = static_cast<double>(Minutes);
		if (C.Schedule.Num() > 0 && Slot.Minutes <= C.Schedule.Last().Minutes)
		{
			return Fail(Error, Where + TEXT(".time"), FString::Printf(TEXT("must be later than schedule[%d].time"), Index - 1));
		}
		if (!GetStateAndIntensity(Item, Where, Slot.State, Slot.Intensity, Error))
		{
			return false;
		}
		C.Schedule.Add(Slot);
		C.ScheduleTimes.Add(Slot.Minutes);
	}

	// rain_fx
	FJsonObjectPtr Fx;
	if (!GetObject(FindExact(Root, TEXT("rain_fx")), TEXT("rain_fx"), Fx, Error)
		|| !CheckKeys(Fx, TEXT("rain_fx"),
			{TEXT("system"), TEXT("enabled"), TEXT("max_spawn_rate"), TEXT("box_half_extent_cm"), TEXT("height_offset_cm")}, {}, Error)
		|| !GetObjectPath(FindExact(Fx, TEXT("system")), TEXT("rain_fx.system"), C.RainFxSystem, Error))
	{
		return false;
	}
	const FJsonValuePtr Enabled = FindExact(Fx, TEXT("enabled"));
	if (Enabled->Type != EJson::Boolean)
	{
		return Fail(Error, TEXT("rain_fx.enabled"), TEXT("must be true or false"));
	}
	C.bRainFxEnabled = Enabled->AsBool();
	if (!GetNumber(FindExact(Fx, TEXT("max_spawn_rate")), TEXT("rain_fx.max_spawn_rate"), 0.0, MaxSpawnRate, true, false, C.MaxSpawnRate,
			Error))
	{
		return false;
	}
	const FJsonValuePtr Box = FindExact(Fx, TEXT("box_half_extent_cm"));
	if (Box->Type != EJson::Array || Box->AsArray().Num() != 3)
	{
		return Fail(Error, TEXT("rain_fx.box_half_extent_cm"), TEXT("must be an array of 3 numbers"));
	}
	double Extent[3] = {0.0, 0.0, 0.0};
	for (int32 Axis = 0; Axis < 3; ++Axis)
	{
		if (!GetNumber(Box->AsArray()[Axis], FString::Printf(TEXT("rain_fx.box_half_extent_cm[%d]"), Axis), MinBoxHalfExtent,
				MaxBoxHalfExtent, Extent[Axis], Error))
		{
			return false;
		}
	}
	C.BoxHalfExtentCm = FVector(Extent[0], Extent[1], Extent[2]);
	if (!GetNumber(FindExact(Fx, TEXT("height_offset_cm")), TEXT("rain_fx.height_offset_cm"), MinHeightOffset, MaxHeightOffset,
			C.HeightOffsetCm, Error))
	{
		return false;
	}

	if (!GetObjectPath(FindExact(Root, TEXT("mpc")), TEXT("mpc"), C.Mpc, Error))
	{
		return false;
	}

	Out = MoveTemp(C);
	return true;
}

bool GolmokWeather::LoadConfigFile(const FString& FilePath, FConfig& Out, FString& Error)
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *FilePath))
	{
		Error = FString::Printf(TEXT("weather.json: %s: cannot read file"), *FilePath);
		return false;
	}
	return ParseConfigText(Text, Out, Error);
}

FString GolmokWeather::DefaultConfigPath()
{
	return FPaths::Combine(FPaths::ProjectConfigDir(), TEXT("Golmok/weather.json"));
}

bool GolmokWeather::ResolveRainLevel(const FConfig& Config, const FString& Word, double& OutIntensity)
{
	if (Word.Equals(TEXT("light"), ESearchCase::CaseSensitive))
	{
		OutIntensity = Config.RainLight;
		return true;
	}
	if (Word.Equals(TEXT("moderate"), ESearchCase::CaseSensitive))
	{
		OutIntensity = Config.RainModerate;
		return true;
	}
	if (Word.Equals(TEXT("heavy"), ESearchCase::CaseSensitive))
	{
		OutIntensity = Config.RainHeavy;
		return true;
	}
	return false;
}
