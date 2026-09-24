#include "Geo/GolmokGeoOrigin.h"

#include "Golmok.h"

#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"

AGolmokGeoOrigin::AGolmokGeoOrigin()
{
	PrimaryActorTick.bCanEverTick = false;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);
	Root->SetMobility(EComponentMobility::Static);
}

AGolmokGeoOrigin* AGolmokGeoOrigin::Find(UWorld* World)
{
	if (!World)
	{
		return nullptr;
	}
	AGolmokGeoOrigin* First = nullptr;
	int32 Count = 0;
	for (TActorIterator<AGolmokGeoOrigin> It(World); It; ++It)
	{
		if (!IsValid(*It))
		{
			continue;
		}
		++Count;
		if (!First)
		{
			First = *It;
		}
	}
	if (Count > 1)
	{
		UE_LOG(LogGolmok, Warning, TEXT("%d AGolmokGeoOrigin actors in %s; using '%s'. Keep exactly one per level."),
			Count, *World->GetName(), *First->GetName());
	}
	if (First && !First->GetActorLocation().IsNearlyZero(1.0))
	{
		UE_LOG(LogGolmok, Warning, TEXT("AGolmokGeoOrigin '%s' is at %s; it should sit at the level origin (0,0,0)."),
			*First->GetName(), *First->GetActorLocation().ToString());
	}
	return First;
}

#if WITH_EDITOR
void AGolmokGeoOrigin::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
	Super::PostEditChangeProperty(PropertyChangedEvent);
	++Revision;
}
#endif
