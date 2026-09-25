#include "Zones/GolmokZoneIndex.h"

#include "Golmok.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	// All helpers carry the IndexJson prefix: a unity build puts every unnamed namespace of the module into one scope
	// and GolmokZoneManifest.cpp already defines Fail / GetObject / GetArray / ... there. JSON keys are passed as
	// FString objects (never TCHAR literals) so the FJsonObject::TryGet*Field overloads of UE 5.8 (const FString& and
	// FStringView, V-03) never become ambiguous; FJsonObject::Values is never iterated (its key type is not FString).

	bool IndexJsonFail(FString& OutError, const FString& InMessage)
	{
		OutError = InMessage;
		return false;
	}

	bool IndexJsonParseObject(const FString& InJsonText, TSharedPtr<FJsonObject>& OutRoot, FString& OutError)
	{
		OutRoot.Reset();
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(InJsonText);
		if (!FJsonSerializer::Deserialize(Reader, OutRoot) || !OutRoot.IsValid())
		{
			return IndexJsonFail(OutError, FString::Printf(TEXT("not a JSON object (%s)"), *Reader->GetErrorMessage()));
		}
		return true;
	}

	bool IndexJsonNumber(const TSharedPtr<FJsonObject>& InObj, const FString& InKey, double& OutValue, FString& OutError)
	{
		if (InObj.IsValid() && InObj->TryGetNumberField(InKey, OutValue))
		{
			return true;
		}
		OutValue = 0.0;
		return IndexJsonFail(OutError, FString::Printf(TEXT("missing number '%s'"), *InKey));
	}

	bool IndexJsonString(const TSharedPtr<FJsonObject>& InObj, const FString& InKey, FString& OutValue, FString& OutError)
	{
		if (InObj.IsValid() && InObj->TryGetStringField(InKey, OutValue))
		{
			return true;
		}
		OutValue.Reset();
		return IndexJsonFail(OutError, FString::Printf(TEXT("missing string '%s'"), *InKey));
	}

	bool IndexJsonArray(const TSharedPtr<FJsonObject>& InObj, const FString& InKey, const TArray<TSharedPtr<FJsonValue>>*& OutArray, FString& OutError)
	{
		OutArray = nullptr;
		if (InObj.IsValid() && InObj->TryGetArrayField(InKey, OutArray) && OutArray)
		{
			return true;
		}
		return IndexJsonFail(OutError, FString::Printf(TEXT("missing array '%s'"), *InKey));
	}

	/** Array element -> object (false when the element is not an object). */
	bool IndexJsonObjectOf(const TSharedPtr<FJsonValue>& InValue, TSharedPtr<FJsonObject>& OutObj)
	{
		const TSharedPtr<FJsonObject>* ObjPtr = nullptr;
		if (!InValue.IsValid() || !InValue->TryGetObject(ObjPtr) || !ObjPtr || !ObjPtr->IsValid())
		{
			OutObj.Reset();
			return false;
		}
		OutObj = *ObjPtr;
		return true;
	}

	/** "exterior" / "interior" -> kind. */
	bool IndexJsonKind(const FString& InText, EGolmokZoneKind& OutKind)
	{
		if (InText == TEXT("exterior"))
		{
			OutKind = EGolmokZoneKind::Exterior;
			return true;
		}
		if (InText == TEXT("interior"))
		{
			OutKind = EGolmokZoneKind::Interior;
			return true;
		}
		return false;
	}

	/** Default FReadFile: a missing file is a plain false (no engine warning), anything else goes through FFileHelper. */
	bool IndexJsonReadFile(const FString& InFilePath, FString& OutText)
	{
		OutText.Reset();
		if (!IFileManager::Get().FileExists(*InFilePath))
		{
			return false;
		}
		return FFileHelper::LoadFileToString(OutText, *InFilePath, FFileHelper::EHashOptions::None, FILEREAD_Silent);
	}

	/** Web Mercator tile range at CellZoom: 0 .. 2^16 - 1. */
	constexpr int32 IndexJsonMaxCellCoord = (1 << FGolmokZoneIndex::CellZoom) - 1;
} // namespace

// ---- static helpers ---------------------------------------------------------------------------------------------

FString FGolmokZoneIndex::DefaultIndexDir()
{
	return FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Golmok"), TEXT("Zones"), TEXT("index"));
}

FString FGolmokZoneIndex::ZonesFilePath(const FString& InIndexDir)
{
	return FPaths::Combine(InIndexDir, TEXT("zones.json"));
}

FString FGolmokZoneIndex::CellFileName(int32 InX, int32 InY)
{
	return FString::Printf(TEXT("%d_%d_%d.json"), CellZoom, InX, InY);
}

FString FGolmokZoneIndex::CellFilePath(const FString& InIndexDir, int32 InX, int32 InY)
{
	return FPaths::Combine(InIndexDir, TEXT("cells"), CellFileName(InX, InY));
}

FString FGolmokZoneIndex::CellKey(int32 InX, int32 InY)
{
	return FString::Printf(TEXT("%d_%d_%d"), CellZoom, InX, InY);
}

bool FGolmokZoneIndex::ParseZonesText(const FString& InJsonText, TArray<FGolmokZoneIndexEntry>& OutEntries, FString& OutError)
{
	OutEntries.Reset();
	OutError.Reset();
	TSharedPtr<FJsonObject> Root;
	if (!IndexJsonParseObject(InJsonText, Root, OutError))
	{
		return false;
	}
	double Number = 0.0;
	if (!IndexJsonNumber(Root, TEXT("schema_version"), Number, OutError))
	{
		return false;
	}
	if (static_cast<int32>(Number) != 1)
	{
		return IndexJsonFail(OutError, FString::Printf(TEXT("unsupported schema_version %d (expected 1)"), static_cast<int32>(Number)));
	}
	if (!IndexJsonNumber(Root, TEXT("cell_zoom"), Number, OutError))
	{
		return false;
	}
	if (static_cast<int32>(Number) != CellZoom)
	{
		return IndexJsonFail(OutError, FString::Printf(TEXT("cell_zoom %d != %d"), static_cast<int32>(Number), CellZoom));
	}
	const TArray<TSharedPtr<FJsonValue>>* ZonesArr = nullptr;
	if (!IndexJsonArray(Root, TEXT("zones"), ZonesArr, OutError))
	{
		return false;
	}

	const FString KeyId(TEXT("id"));
	const FString KeyVersion(TEXT("version"));
	const FString KeyKind(TEXT("kind"));
	const FString KeyPriority(TEXT("priority"));
	const FString KeyBbox(TEXT("bbox_wgs84"));
	const FString KeyManifest(TEXT("manifest"));
	TSet<FString> SeenIds;
	OutEntries.Reserve(ZonesArr->Num());
	for (int32 Index = 0; Index < ZonesArr->Num(); ++Index)
	{
		TSharedPtr<FJsonObject> Obj;
		if (!IndexJsonObjectOf((*ZonesArr)[Index], Obj))
		{
			return IndexJsonFail(OutError, FString::Printf(TEXT("zones[%d] is not an object"), Index));
		}
		FGolmokZoneIndexEntry Entry;
		if (!IndexJsonString(Obj, KeyId, Entry.Id, OutError))
		{
			return IndexJsonFail(OutError, FString::Printf(TEXT("zones[%d]: %s"), Index, *OutError));
		}
		if (!GolmokZoneManifest::IsValidZoneId(Entry.Id))
		{
			return IndexJsonFail(OutError, FString::Printf(TEXT("zones[%d]: bad id '%s'"), Index, *Entry.Id));
		}
		if (SeenIds.Contains(Entry.Id))
		{
			return IndexJsonFail(OutError, FString::Printf(TEXT("zones[%d]: duplicate id '%s'"), Index, *Entry.Id));
		}
		if (!IndexJsonNumber(Obj, KeyVersion, Number, OutError))
		{
			return IndexJsonFail(OutError, FString::Printf(TEXT("zone '%s': %s"), *Entry.Id, *OutError));
		}
		Entry.Version = static_cast<int32>(Number);
		if (Entry.Version < 1)
		{
			return IndexJsonFail(OutError, FString::Printf(TEXT("zone '%s': version %d < 1"), *Entry.Id, Entry.Version));
		}
		FString KindText;
		if (!IndexJsonString(Obj, KeyKind, KindText, OutError))
		{
			return IndexJsonFail(OutError, FString::Printf(TEXT("zone '%s': %s"), *Entry.Id, *OutError));
		}
		if (!IndexJsonKind(KindText, Entry.Kind))
		{
			return IndexJsonFail(OutError, FString::Printf(TEXT("zone '%s': unknown kind '%s'"), *Entry.Id, *KindText));
		}
		// priority is optional here (the CLI always writes it); a missing value ranks lowest.
		Entry.Priority = Obj->TryGetNumberField(KeyPriority, Number) ? static_cast<int32>(Number) : 0;
		const TArray<TSharedPtr<FJsonValue>>* Bbox = nullptr;
		if (!IndexJsonArray(Obj, KeyBbox, Bbox, OutError) || Bbox->Num() != 4)
		{
			return IndexJsonFail(OutError, FString::Printf(TEXT("zone '%s': bbox_wgs84 needs 4 numbers"), *Entry.Id));
		}
		double Values[4] = {0.0, 0.0, 0.0, 0.0};
		for (int32 K = 0; K < 4; ++K)
		{
			if (!(*Bbox)[K].IsValid() || !(*Bbox)[K]->TryGetNumber(Values[K]))
			{
				return IndexJsonFail(OutError, FString::Printf(TEXT("zone '%s': bbox_wgs84[%d] is not a number"), *Entry.Id, K));
			}
		}
		Entry.West = Values[0];
		Entry.South = Values[1];
		Entry.East = Values[2];
		Entry.North = Values[3];
		if (Entry.West > Entry.East || Entry.South > Entry.North)
		{
			return IndexJsonFail(OutError, FString::Printf(TEXT("zone '%s': bbox_wgs84 west > east or south > north"), *Entry.Id));
		}
		const FString ExpectedManifest = FString::Printf(TEXT("%s/v%d/manifest.json"), *Entry.Id, Entry.Version);
		if (!Obj->TryGetStringField(KeyManifest, Entry.ManifestRel))
		{
			Entry.ManifestRel.Reset();
		}
		if (Entry.ManifestRel != ExpectedManifest)
		{
			UE_LOG(LogGolmok, Warning, TEXT("GolmokZoneIndex: zone '%s' manifest '%s' != '%s' (entry kept; the manifest path helper wins)"),
				*Entry.Id, *Entry.ManifestRel, *ExpectedManifest);
		}
		SeenIds.Add(Entry.Id);
		OutEntries.Add(MoveTemp(Entry));
	}
	return true;
}

bool FGolmokZoneIndex::ParseCellText(const FString& InJsonText, FGolmokZoneIndexCell& OutCell, FString& OutError)
{
	OutCell = FGolmokZoneIndexCell();
	OutError.Reset();
	TSharedPtr<FJsonObject> Root;
	if (!IndexJsonParseObject(InJsonText, Root, OutError))
	{
		return false;
	}
	double Number = 0.0;
	if (!IndexJsonNumber(Root, TEXT("schema_version"), Number, OutError))
	{
		return false;
	}
	if (static_cast<int32>(Number) != 1)
	{
		return IndexJsonFail(OutError, FString::Printf(TEXT("unsupported schema_version %d (expected 1)"), static_cast<int32>(Number)));
	}
	if (!IndexJsonNumber(Root, TEXT("z"), Number, OutError))
	{
		return false;
	}
	if (static_cast<int32>(Number) != CellZoom)
	{
		return IndexJsonFail(OutError, FString::Printf(TEXT("z %d != %d"), static_cast<int32>(Number), CellZoom));
	}
	OutCell.Zoom = CellZoom;
	if (!IndexJsonNumber(Root, TEXT("x"), Number, OutError))
	{
		return false;
	}
	OutCell.X = static_cast<int32>(Number);
	if (!IndexJsonNumber(Root, TEXT("y"), Number, OutError))
	{
		return false;
	}
	OutCell.Y = static_cast<int32>(Number);
	if (OutCell.X < 0 || OutCell.Y < 0)
	{
		return IndexJsonFail(OutError, FString::Printf(TEXT("x / y negative (%d, %d)"), OutCell.X, OutCell.Y));
	}
	const TArray<TSharedPtr<FJsonValue>>* ZonesArr = nullptr;
	if (!IndexJsonArray(Root, TEXT("zones"), ZonesArr, OutError))
	{
		return false;
	}
	const FString KeyId(TEXT("id"));
	const FString KeyVersion(TEXT("version"));
	TSet<FString> SeenIds;
	OutCell.Zones.Reserve(ZonesArr->Num());
	for (int32 Index = 0; Index < ZonesArr->Num(); ++Index)
	{
		TSharedPtr<FJsonObject> Obj;
		if (!IndexJsonObjectOf((*ZonesArr)[Index], Obj))
		{
			return IndexJsonFail(OutError, FString::Printf(TEXT("zones[%d] is not an object"), Index));
		}
		FGolmokZoneIndexCellRef Ref;
		if (!Obj->TryGetStringField(KeyId, Ref.Id) || !Obj->TryGetNumberField(KeyVersion, Number))
		{
			return IndexJsonFail(OutError, FString::Printf(TEXT("zones[%d] needs id and version"), Index));
		}
		Ref.Version = static_cast<int32>(Number);
		if (SeenIds.Contains(Ref.Id))
		{
			return IndexJsonFail(OutError, FString::Printf(TEXT("zones[%d]: duplicate id '%s'"), Index, *Ref.Id));
		}
		SeenIds.Add(Ref.Id);
		OutCell.Zones.Add(MoveTemp(Ref));
	}
	OutCell.bFromFile = true;
	return true;
}

// ---- instance ---------------------------------------------------------------------------------------------------

FGolmokZoneIndex::FGolmokZoneIndex(FReadFile InReader)
{
	if (InReader)
	{
		Reader = MoveTemp(InReader);
	}
	else
	{
		Reader = FReadFile(&IndexJsonReadFile);
	}
}

bool FGolmokZoneIndex::Load(const FString& InIndexDir, FString& OutError)
{
	Reset();
	OutError.Reset();
	IndexDir = InIndexDir;
	FString Text;
	++FileReads;
	if (!Reader(ZonesFilePath(IndexDir), Text))
	{
		return false; // no zones.json: index silently off (OutError stays empty)
	}
	if (!ParseZonesText(Text, Entries, OutError))
	{
		Entries.Reset();
		OutError = FString::Printf(TEXT("%s: %s"), *ZonesFilePath(IndexDir), *OutError);
		return false;
	}
	for (int32 Index = 0; Index < Entries.Num(); ++Index)
	{
		ById.Add(Entries[Index].Id, Index);
	}
	bLoaded = true;
	return true;
}

bool FGolmokZoneIndex::LoadFromText(const FString& InIndexDir, const FString& InZonesJson, FString& OutError)
{
	Reset();
	OutError.Reset();
	IndexDir = InIndexDir;
	if (!ParseZonesText(InZonesJson, Entries, OutError))
	{
		Entries.Reset();
		return false;
	}
	for (int32 Index = 0; Index < Entries.Num(); ++Index)
	{
		ById.Add(Entries[Index].Id, Index);
	}
	bLoaded = true;
	return true;
}

const FGolmokZoneIndexEntry* FGolmokZoneIndex::FindZone(const FString& InZoneId) const
{
	const int32* Index = ById.Find(InZoneId);
	return (Index && Entries.IsValidIndex(*Index)) ? &Entries[*Index] : nullptr;
}

const FGolmokZoneIndexCell& FGolmokZoneIndex::GetCell(int32 InX, int32 InY)
{
	const FString Key = CellKey(InX, InY);
	if (const FGolmokZoneIndexCell* Cached = Cells.Find(Key))
	{
		return *Cached;
	}
	FGolmokZoneIndexCell Cell;
	Cell.Zoom = CellZoom;
	Cell.X = InX;
	Cell.Y = InY;
	if (bLoaded)
	{
		FString Text;
		++FileReads;
		const FString FilePath = CellFilePath(IndexDir, InX, InY);
		if (!Reader(FilePath, Text))
		{
			// write_index only writes cells that hold a zone, so a missing file is the normal empty cell.
			if (!WarnedCells.Contains(Key))
			{
				WarnedCells.Add(Key);
				UE_LOG(LogGolmok, Log, TEXT("GolmokZoneIndex: no cell file %s (empty cell)"), *FilePath);
			}
		}
		else
		{
			FString Error;
			if (!ParseCellText(Text, Cell, Error))
			{
				Cell = FGolmokZoneIndexCell();
				Cell.Zoom = CellZoom;
				Cell.X = InX;
				Cell.Y = InY;
				Cell.Error = Error;
			}
			else if (Cell.X != InX || Cell.Y != InY)
			{
				// File name and content disagree: treated like a broken file (the Python check rejects it as well).
				Cell.Error = FString::Printf(TEXT("file says cell %d/%d, expected %d/%d"), Cell.X, Cell.Y, InX, InY);
				Cell.X = InX;
				Cell.Y = InY;
				Cell.bFromFile = false;
				Cell.Zones.Reset();
			}
			if (!Cell.Error.IsEmpty() && !WarnedCells.Contains(Key))
			{
				WarnedCells.Add(Key);
				UE_LOG(LogGolmok, Warning, TEXT("GolmokZoneIndex: cell file %s ignored: %s"), *FilePath, *Cell.Error);
			}
		}
	}
	return Cells.Add(Key, MoveTemp(Cell));
}

void FGolmokZoneIndex::CollectAround(int32 InCenterX, int32 InCenterY, int32 InRadius, TArray<FGolmokZoneIndexCellRef>& OutRefs,
	TArray<FString>* OutWarnings)
{
	OutRefs.Reset();
	const int32 Radius = FMath::Max(0, InRadius);
	TSet<FString> Seen;
	for (int32 Y = InCenterY - Radius; Y <= InCenterY + Radius; ++Y)
	{
		if (Y < 0 || Y > IndexJsonMaxCellCoord)
		{
			continue; // clamped to the tile range: nothing beyond the edge, no wrap
		}
		for (int32 X = InCenterX - Radius; X <= InCenterX + Radius; ++X)
		{
			if (X < 0 || X > IndexJsonMaxCellCoord)
			{
				continue;
			}
			const FGolmokZoneIndexCell& Cell = GetCell(X, Y);
			for (const FGolmokZoneIndexCellRef& Ref : Cell.Zones)
			{
				if (Seen.Contains(Ref.Id))
				{
					continue;
				}
				const FGolmokZoneIndexEntry* Entry = FindZone(Ref.Id);
				if (!Entry || Entry->Version != Ref.Version)
				{
					if (!WarnedIds.Contains(Ref.Id))
					{
						WarnedIds.Add(Ref.Id);
						const FString Message = Entry
							? FString::Printf(TEXT("cell %s lists %s@v%d but zones.json has v%d (skipped)"), *CellKey(X, Y), *Ref.Id, Ref.Version, Entry->Version)
							: FString::Printf(TEXT("cell %s lists %s@v%d which is not in zones.json (skipped)"), *CellKey(X, Y), *Ref.Id, Ref.Version);
						UE_LOG(LogGolmok, Warning, TEXT("GolmokZoneIndex: %s"), *Message);
						if (OutWarnings)
						{
							OutWarnings->Add(Message);
						}
					}
					continue;
				}
				Seen.Add(Ref.Id);
				OutRefs.Add(Ref);
			}
		}
	}
}

void FGolmokZoneIndex::TrimCache(int32 InKeepX, int32 InKeepY, int32 InMaxCells)
{
	if (Cells.Num() <= InMaxCells)
	{
		return;
	}
	TArray<FString> Drop;
	for (const TPair<FString, FGolmokZoneIndexCell>& Pair : Cells)
	{
		const FGolmokZoneIndexCell& Cell = Pair.Value;
		if (FMath::Abs(Cell.X - InKeepX) > 1 || FMath::Abs(Cell.Y - InKeepY) > 1)
		{
			Drop.Add(Pair.Key);
		}
	}
	for (const FString& Key : Drop)
	{
		Cells.Remove(Key);
	}
	if (Drop.Num() > 0)
	{
		UE_LOG(LogGolmok, Log, TEXT("GolmokZoneIndex: cell cache trimmed by %d (kept %d around %s)"), Drop.Num(), Cells.Num(),
			*CellKey(InKeepX, InKeepY));
	}
}

int32 FGolmokZoneIndex::NumMissingCells() const
{
	int32 Missing = 0;
	for (const TPair<FString, FGolmokZoneIndexCell>& Pair : Cells)
	{
		if (!Pair.Value.bFromFile)
		{
			++Missing;
		}
	}
	return Missing;
}

FString FGolmokZoneIndex::Describe(int32 InCenterX, int32 InCenterY, int32 InRadius)
{
	if (!bLoaded)
	{
		return TEXT("cells: index not loaded");
	}
	const int32 Radius = FMath::Max(0, InRadius);
	const int32 Side = 2 * Radius + 1;
	// Rows y ascending (north to south on the map), columns x ascending; one cell = "16/x/y[ *] zones..." and "-"
	// for a cell without a file, "!" for a broken one. Columns are padded so the rows line up in the log.
	TArray<TArray<FString>> Rows;
	int32 Width = 0;
	for (int32 Y = InCenterY - Radius; Y <= InCenterY + Radius; ++Y)
	{
		TArray<FString>& Row = Rows.AddDefaulted_GetRef();
		for (int32 X = InCenterX - Radius; X <= InCenterX + Radius; ++X)
		{
			FString Text = FString::Printf(TEXT("%d/%d/%d"), CellZoom, X, Y);
			if (X == InCenterX && Y == InCenterY)
			{
				Text += TEXT(" *");
			}
			if (X < 0 || X > IndexJsonMaxCellCoord || Y < 0 || Y > IndexJsonMaxCellCoord)
			{
				Text += TEXT(" (out of range)");
			}
			else
			{
				const FGolmokZoneIndexCell& Cell = GetCell(X, Y);
				if (!Cell.Error.IsEmpty())
				{
					Text += FString::Printf(TEXT(" ! %s"), *Cell.Error);
				}
				else if (Cell.Zones.Num() == 0)
				{
					Text += TEXT(" -");
				}
				for (const FGolmokZoneIndexCellRef& Ref : Cell.Zones)
				{
					Text += FString::Printf(TEXT(" %s@v%d"), *Ref.Id, Ref.Version);
				}
			}
			Width = FMath::Max(Width, Text.Len());
			Row.Add(MoveTemp(Text));
		}
	}
	FString Out = FString::Printf(TEXT("cells %dx%d (winning order per cell, * = center, - = no file):"), Side, Side);
	for (const TArray<FString>& Row : Rows)
	{
		Out += TEXT("\n ");
		for (int32 Column = 0; Column < Row.Num(); ++Column)
		{
			Out += TEXT(" ");
			Out += Row[Column];
			if (Column + 1 < Row.Num())
			{
				Out += FString::ChrN(Width - Row[Column].Len() + 2, TEXT(' '));
			}
		}
	}
	return Out;
}

void FGolmokZoneIndex::Reset()
{
	IndexDir.Reset();
	Entries.Reset();
	ById.Reset();
	Cells.Reset();
	WarnedCells.Reset();
	WarnedIds.Reset();
	FileReads = 0;
	bLoaded = false;
}
