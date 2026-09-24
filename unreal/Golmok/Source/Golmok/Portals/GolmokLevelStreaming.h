#pragma once

#include "CoreMinimal.h"
#include "Portals/GolmokPortal.h"

class ULevelStreaming;
class UWorld;

/**
 * Interior sublevel streaming for AGolmokPortal (WP-05 design section 3-2). Plain functions, no UObject.
 *
 * Two paths, chosen by EGolmokInteriorStreamingMode:
 *  - LevelInstance (default): ULevelStreamingDynamic::LoadLevelInstance by package path with the identity transform
 *    (sublevels are authored in level coordinates), instance name L_<id>_inst. An existing streaming level for the
 *    same package is reused, so two doors into one interior share one instance.
 *  - NamedStreamingLevel: the ULevelStreaming registered in the persistent level (Window > Levels) is switched on and
 *    off; nothing is created (no UGameplayStatics::LoadStreamLevel fallback).
 * Find() looks the level up by package name each time, so no state object is kept.
 */
namespace GolmokLevelStreaming
{
	/** Streaming level whose package (PackageNameToLoad / world asset, PIE prefix removed) is PackagePath; registered entries and dynamic instances alike. */
	GOLMOK_API ULevelStreaming* Find(UWorld* World, const FString& PackagePath);

	GOLMOK_API bool StreamIn(UWorld* World, const FString& PackagePath, EGolmokInteriorStreamingMode Mode, FString& OutMessage);
	GOLMOK_API bool StreamOut(UWorld* World, const FString& PackagePath, FString& OutMessage);

	GOLMOK_API bool IsLoaded(UWorld* World, const FString& PackagePath);
	GOLMOK_API bool IsVisible(UWorld* World, const FString& PackagePath);

	/** "none" | "loading" | "loaded" | "visible" */
	GOLMOK_API FString Describe(UWorld* World, const FString& PackagePath);
} // namespace GolmokLevelStreaming
