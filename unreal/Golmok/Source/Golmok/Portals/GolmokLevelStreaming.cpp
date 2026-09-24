#include "Portals/GolmokLevelStreaming.h"

#include "Golmok.h"

#include "Engine/LevelStreaming.h"
#include "Engine/LevelStreamingDynamic.h"
#include "Engine/World.h"
#include "Misc/PackageName.h"

namespace GolmokLevelStreaming
{
	ULevelStreaming* Find(UWorld* World, const FString& PackagePath)
	{
		if (!World || PackagePath.IsEmpty())
		{
			return nullptr;
		}
		for (ULevelStreaming* Level : World->GetStreamingLevels())
		{
			if (!IsValid(Level))
			{
				continue;
			}
			// A dynamic instance carries the original package in PackageNameToLoad (its world asset is the unique
			// instance name); a registered entry has it in the world asset, PIE-prefixed while playing in editor.
			if (!Level->PackageNameToLoad.IsNone() && Level->PackageNameToLoad.ToString() == PackagePath)
			{
				return Level;
			}
			if (UWorld::RemovePIEPrefix(Level->GetWorldAssetPackageName()) == PackagePath)
			{
				return Level;
			}
		}
		return nullptr;
	}

	bool StreamIn(UWorld* World, const FString& PackagePath, EGolmokInteriorStreamingMode Mode, FString& OutMessage)
	{
		if (!World)
		{
			OutMessage = TEXT("no world");
			return false;
		}
		if (PackagePath.IsEmpty())
		{
			OutMessage = TEXT("empty sublevel package path");
			return false;
		}
		if (World->IsPartitionedWorld())
		{
			UE_LOG(LogGolmok, Warning, TEXT("LevelStreaming: %s is a World Partition map; portal sublevel streaming was designed for non-partitioned levels."),
				*World->GetMapName());
		}

		if (ULevelStreaming* Existing = Find(World, PackagePath))
		{
			// Reuse (two doors into one interior, or a stream-out still pending): one instance only.
			Existing->SetShouldBeLoaded(true);
			Existing->SetShouldBeVisible(true);
			if (ULevelStreamingDynamic* Dynamic = Cast<ULevelStreamingDynamic>(Existing))
			{
				Dynamic->SetIsRequestingUnloadAndRemoval(false);
			}
			OutMessage = FString::Printf(TEXT("stream in (%s, reused) %s"),
				Mode == EGolmokInteriorStreamingMode::LevelInstance ? TEXT("LevelInstance") : TEXT("NamedStreamingLevel"), *PackagePath);
			return true;
		}

		if (Mode == EGolmokInteriorStreamingMode::NamedStreamingLevel)
		{
			OutMessage = FString::Printf(
				TEXT("sublevel %s is not registered in the persistent level (Window > Levels); use InteriorStreamingMode=LevelInstance"), *PackagePath);
			UE_LOG(LogGolmok, Error, TEXT("LevelStreaming: %s"), *OutMessage);
			return false;
		}

		if (!FPackageName::DoesPackageExist(PackagePath))
		{
			OutMessage = FString::Printf(TEXT("sublevel package missing: %s"), *PackagePath);
			UE_LOG(LogGolmok, Warning, TEXT("LevelStreaming: %s"), *OutMessage);
			return false;
		}
		bool bOk = false;
		const FString InstanceName = FPackageName::GetShortName(PackagePath) + TEXT("_inst");
		// Identity transform: interior sublevels are authored in level coordinates (design section 3-2).
		ULevelStreamingDynamic* Instance =
			ULevelStreamingDynamic::LoadLevelInstance(World, PackagePath, FVector::ZeroVector, FRotator::ZeroRotator, bOk, InstanceName);
		if (!bOk || !Instance)
		{
			OutMessage = FString::Printf(TEXT("LoadLevelInstance failed for %s"), *PackagePath);
			UE_LOG(LogGolmok, Error, TEXT("LevelStreaming: %s"), *OutMessage);
			return false;
		}
		OutMessage = FString::Printf(TEXT("stream in (LevelInstance) %s"), *PackagePath);
		return true;
	}

	bool StreamOut(UWorld* World, const FString& PackagePath, FString& OutMessage)
	{
		ULevelStreaming* Level = Find(World, PackagePath);
		if (!Level)
		{
			OutMessage = FString::Printf(TEXT("sublevel %s was not streamed"), *PackagePath);
			return false;
		}
		Level->SetShouldBeVisible(false);
		Level->SetShouldBeLoaded(false);
		// Only an instance StreamIn() created with LoadLevelInstance leaves the streaming level list once unloaded
		// (design section 11 #3): its world asset is the unique L_<id>_inst name while PackageNameToLoad holds the
		// source package. A registered entry (NamedStreamingLevel; also a ULevelStreamingDynamic when added by
		// synthetic_zone.register_interior_sublevel()) has world asset == PackagePath and must stay registered, or the
		// next StreamIn() in that mode fails with "not registered".
		ULevelStreamingDynamic* Dynamic = Cast<ULevelStreamingDynamic>(Level);
		const bool bInstance = Dynamic && !Dynamic->PackageNameToLoad.IsNone()
			&& UWorld::RemovePIEPrefix(Dynamic->GetWorldAssetPackageName()) != PackagePath;
		if (bInstance)
		{
			Dynamic->SetIsRequestingUnloadAndRemoval(true);
		}
		OutMessage = TEXT("sublevel out");
		return true;
	}

	bool IsLoaded(UWorld* World, const FString& PackagePath)
	{
		const ULevelStreaming* Level = Find(World, PackagePath);
		return Level && Level->IsLevelLoaded();
	}

	bool IsVisible(UWorld* World, const FString& PackagePath)
	{
		const ULevelStreaming* Level = Find(World, PackagePath);
		return Level && Level->IsLevelVisible();
	}

	FString Describe(UWorld* World, const FString& PackagePath)
	{
		const ULevelStreaming* Level = Find(World, PackagePath);
		if (!Level)
		{
			return TEXT("none");
		}
		if (Level->IsLevelVisible())
		{
			return TEXT("visible");
		}
		if (Level->IsLevelLoaded())
		{
			return TEXT("loaded");
		}
		// Registered but not requested counts as nothing streamed.
		return Level->ShouldBeLoaded() ? TEXT("loading") : TEXT("none");
	}
} // namespace GolmokLevelStreaming
