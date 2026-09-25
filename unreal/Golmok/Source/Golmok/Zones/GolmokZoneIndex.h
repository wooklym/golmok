#pragma once

#include "CoreMinimal.h"
#include "Templates/Function.h"
#include "Zones/GolmokZoneManifest.h"

/**
 * Runtime view of the Zone Index (docs/spec/zone-manifest.md §6, WP-09 design §3-2): index/zones.json (every zone,
 * latest valid version) and index/cells/16_<x>_<y>.json (zones per Web Mercator z16 tile, winning order). The files
 * are the byte-exact output of `golmok-zone index build`, read as plain text through an injectable reader so the
 * automation test feeds JSON from memory and the game reads UFS-staged files inside a .pak.
 *
 * Plain class: no UCLASS / USTRUCT / .generated.h. Owned by value by UGolmokZoneSubsystem.
 */

/** One row of index/zones.json (spec §6): the latest valid version of a zone. */
struct GOLMOK_API FGolmokZoneIndexEntry
{
	FString Id;
	int32 Version = 0;
	EGolmokZoneKind Kind = EGolmokZoneKind::Exterior;
	int32 Priority = 0;
	double West = 0.0;   // bbox_wgs84[0]
	double South = 0.0;  // [1]
	double East = 0.0;   // [2]
	double North = 0.0;  // [3]
	FString ManifestRel; // "<id>/v<n>/manifest.json" relative to Content/Golmok/Zones
};

struct GOLMOK_API FGolmokZoneIndexCellRef
{
	FString Id;
	int32 Version = 0;
};

/** One index/cells/16_<x>_<y>.json. Zones are in winning order (priority desc, version desc, id). */
struct GOLMOK_API FGolmokZoneIndexCell
{
	int32 Zoom = 16;
	int32 X = 0;
	int32 Y = 0;
	bool bFromFile = false;  // false = no file (empty cell) or parse error (Error set, treated as empty)
	FString Error;
	TArray<FGolmokZoneIndexCellRef> Zones;
};

/**
 * Runtime view of the Zone Index: zones.json parsed once, cell files parsed once each on first use and cached (a
 * missing file is an empty cell, warned once). File access goes through an injectable reader so Golmok.Zone.IndexParse
 * feeds JSON from memory. Owned by value by UGolmokZoneSubsystem. Static helpers take In* parameters (MSVC C4458).
 */
class GOLMOK_API FGolmokZoneIndex
{
public:
	/** (InFilePath, OutText) -> bool. Default: FFileHelper::LoadFileToString (UFS-staged files in a .pak included). */
	using FReadFile = TFunction<bool(const FString& InFilePath, FString& OutText)>;
	static constexpr int32 CellZoom = 16;

	static FString DefaultIndexDir();                                        // <ProjectContentDir>/Golmok/Zones/index
	static FString ZonesFilePath(const FString& InIndexDir);                 // <dir>/zones.json
	static FString CellFileName(int32 InX, int32 InY);                       // "16_<x>_<y>.json" (index.cell_name)
	static FString CellFilePath(const FString& InIndexDir, int32 InX, int32 InY);   // <dir>/cells/<CellFileName>
	static FString CellKey(int32 InX, int32 InY);                            // "16_<x>_<y>"
	/** zones.json text -> entries. false + OutError on: schema_version != 1, cell_zoom != 16, missing "zones", bad id
	 *  (GolmokZoneManifest::IsValidZoneId), version < 1, unknown kind, bbox not 4 numbers or west > east / south > north,
	 *  duplicate id. manifest != "<id>/v<version>/manifest.json" -> Warning, entry kept. Unknown keys ignored. */
	static bool ParseZonesText(const FString& InJsonText, TArray<FGolmokZoneIndexEntry>& OutEntries, FString& OutError);
	/** cell text -> OutCell (bFromFile = true). false + OutError on: schema_version != 1, z != 16, x / y missing or
	 *  negative, entry without id / version, duplicate id. */
	static bool ParseCellText(const FString& InJsonText, FGolmokZoneIndexCell& OutCell, FString& OutError);

	explicit FGolmokZoneIndex(FReadFile InReader = FReadFile());

	/** Reader(ZonesFilePath(InIndexDir)) + ParseZonesText; clears the cell cache. Missing file -> false with OutError
	 *  EMPTY (silently off); parse error -> false with OutError set. */
	bool Load(const FString& InIndexDir, FString& OutError);
	/** Tests: parse InZonesJson as zones.json and use InIndexDir (e.g. "mem:/index") for cell paths. */
	bool LoadFromText(const FString& InIndexDir, const FString& InZonesJson, FString& OutError);

	bool IsAvailable() const { return bLoaded; }
	const FString& GetIndexDir() const { return IndexDir; }
	int32 NumZones() const { return Entries.Num(); }
	const TArray<FGolmokZoneIndexEntry>& GetEntries() const { return Entries; }
	const FGolmokZoneIndexEntry* FindZone(const FString& InZoneId) const;   // TMap lookup

	/** Cached cell (parsed on first call, one Reader call per key ever). Never fails: no / bad file -> empty cell.
	 *  The reference stays valid until the next GetCell / TrimCache / Reset / Load (TMap growth may rehash). */
	const FGolmokZoneIndexCell& GetCell(int32 InX, int32 InY);

	/**
	 * Zones of the (2R+1)² cells around the center (0..2^16−1 clamped, no wrap; cell order y then x ascending), each
	 * cell in winning order, deduplicated by id keeping the first occurrence. A cell row whose id is unknown to
	 * zones.json or whose version differs is skipped and reported once per id in OutWarnings (nullptr = don't collect).
	 */
	void CollectAround(int32 InCenterX, int32 InCenterY, int32 InRadius, TArray<FGolmokZoneIndexCellRef>& OutRefs,
		TArray<FString>* OutWarnings = nullptr);

	/** Drop cached cells outside the 3x3 around (InKeepX, InKeepY) when more than InMaxCells are cached (long walks). */
	void TrimCache(int32 InKeepX, int32 InKeepY, int32 InMaxCells);

	int32 NumCachedCells() const { return Cells.Num(); }
	int32 NumMissingCells() const;                 // cached cells with bFromFile == false
	int32 NumFileReads() const { return FileReads; }   // test hook: GetCell twice == one read (Load's zones.json counts too)
	/** golmok.zone.index cell block for the 3x3 around the center (§6). */
	FString Describe(int32 InCenterX, int32 InCenterY, int32 InRadius);
	void Reset();

private:
	FReadFile Reader;
	FString IndexDir;
	TArray<FGolmokZoneIndexEntry> Entries;
	TMap<FString, int32> ById;
	TMap<FString, FGolmokZoneIndexCell> Cells;     // key = CellKey
	TSet<FString> WarnedCells;                     // missing / broken cell files warned once (key)
	TSet<FString> WarnedIds;                       // unknown / mismatched cell rows warned once
	int32 FileReads = 0;
	bool bLoaded = false;
};
