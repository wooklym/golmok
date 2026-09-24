#include "Zones/GolmokZone.h"

#include "Golmok.h"

#include "Components/BoxComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Geo/GolmokGeo.h"
#include "Geo/GolmokGeoMath.h"
#include "Geo/GolmokGeoSubsystem.h"
#include "Misc/Paths.h"
#include "UObject/UObjectGlobals.h"
#include "Zones/GolmokZoneSubsystem.h"

namespace
{
	constexpr double UnknownDistanceM = 1.0e9;

	FName MakeComponentName(const TCHAR* Prefix, const FString& Id)
	{
		return FName(*FString::Printf(TEXT("%s_%s"), Prefix, *Id));
	}
} // namespace

AGolmokZone::AGolmokZone()
{
	PrimaryActorTick.bCanEverTick = false;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("ZoneRoot"));
	SetRootComponent(Root);
	// Movable: the root is re-positioned from the manifest after BeginPlay (a Static root cannot move in a game
	// world). Children are Stationary so shadow / Lumen caches treat them as non-moving (Static children may not
	// attach to a non-Static parent).
	Root->SetMobility(EComponentMobility::Movable);
}

// ---- lifecycle ------------------------------------------------------------------------------------------------

void AGolmokZone::BeginPlay()
{
	Super::BeginPlay();
	if (UGolmokZoneSubsystem* Subsystem = GetZoneSubsystem())
	{
		Subsystem->RegisterZone(this);
	}
}

void AGolmokZone::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (UGolmokZoneSubsystem* Subsystem = GetZoneSubsystem())
	{
		Subsystem->UnregisterZone(this);
	}
	Unload();
	Super::EndPlay(EndPlayReason);
}

#if WITH_EDITOR
void AGolmokZone::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
	Super::PostEditChangeProperty(PropertyChangedEvent);
	const FName Name = PropertyChangedEvent.GetPropertyName();
	if (Name == GET_MEMBER_NAME_CHECKED(AGolmokZone, ZoneId) || Name == GET_MEMBER_NAME_CHECKED(AGolmokZone, Version))
	{
		bManifestLoaded = false;
		FootprintOriginRevision = INDEX_NONE;
	}
}
#endif

UGolmokZoneSubsystem* AGolmokZone::GetZoneSubsystem() const
{
	UWorld* World = GetWorld();
	return World ? World->GetSubsystem<UGolmokZoneSubsystem>() : nullptr;
}

FString AGolmokZone::GetManifestFilePath() const
{
	return GolmokZoneManifest::ManifestFilePath(ZoneId, Version);
}

// ---- manifest + placement -------------------------------------------------------------------------------------

bool AGolmokZone::EnsureManifest(bool bForceReload)
{
	if (bManifestLoaded && !bForceReload)
	{
		return true;
	}
	bManifestLoaded = false;
	FootprintOriginRevision = INDEX_NONE;
	LastError.Reset();

	if (ZoneId.IsEmpty() || Version < 1)
	{
		LastError = TEXT("ZoneId is empty or Version < 1");
		UE_LOG(LogGolmok, Error, TEXT("Zone '%s': %s"), *GetName(), *LastError);
		return false;
	}

	const FString Path = GetManifestFilePath();
	if (!GolmokZoneManifest::LoadManifest(Path, Manifest, LastError))
	{
		UE_LOG(LogGolmok, Error, TEXT("Zone %s v%d: manifest error: %s"), *ZoneId, Version, *LastError);
		return false;
	}
	if (Manifest.ZoneId != ZoneId || Manifest.Version != Version)
	{
		UE_LOG(LogGolmok, Warning, TEXT("Zone %s v%d: manifest says zone_id=%s version=%d (folder and file disagree)."), *ZoneId,
			Version, *Manifest.ZoneId, Manifest.Version);
	}
	if (Manifest.Layers.VisualFormat != TEXT("nanite_mesh"))
	{
		UE_LOG(LogGolmok, Warning, TEXT("Zone %s: visual format '%s' is not implemented yet (nanite_mesh only); chunks are placed as meshes."),
			*ZoneId, *Manifest.Layers.VisualFormat);
	}

	Blockers = FGolmokBlockers();
	if (!Manifest.Layers.BlockersUri.IsEmpty())
	{
		const FString BlockersPath = FPaths::Combine(FPaths::GetPath(Path), Manifest.Layers.BlockersUri);
		FString BlockersError;
		if (!GolmokZoneManifest::LoadBlockers(BlockersPath, Blockers, BlockersError))
		{
			UE_LOG(LogGolmok, Warning, TEXT("Zone %s: blockers skipped: %s"), *ZoneId, *BlockersError);
			Blockers = FGolmokBlockers();
		}
	}

	bManifestLoaded = true;
	ApplyRootTransform();
	BuildFootprintCache();
	return true;
}

bool AGolmokZone::ApplyRootTransform()
{
	UWorld* World = GetWorld();
	UGolmokGeoSubsystem* Geo = World ? World->GetSubsystem<UGolmokGeoSubsystem>() : nullptr;
	if (!Geo)
	{
		UE_LOG(LogGolmok, Warning, TEXT("Zone %s: no UGolmokGeoSubsystem (no world?); keeping the actor's current transform."), *ZoneId);
		return false;
	}
	const FTransform T = Geo->ZoneLocalToWorld(Manifest.Transform);
	SetActorTransform(T, false, nullptr, ETeleportType::TeleportPhysics);

	// Runbook item 6: compare with docs/spec/zone-manifest.md §4 table C.
	const FVector P0 = T.TransformPosition(FVector::ZeroVector);
	const FVector P10 = T.TransformPosition(GolmokGeo::EnuToUE(FVector(10.0, 0.0, 0.0)));
	UE_LOG(LogGolmok, Log, TEXT("Zone %s v%d root: zone-local (0,0,0) -> UE (%.2f, %.2f, %.2f) cm; (10,0,0) m -> (%.2f, %.2f, %.2f) cm; yaw %.4f deg"),
		*ZoneId, Version, P0.X, P0.Y, P0.Z, P10.X, P10.Y, P10.Z, T.Rotator().Yaw);
	return true;
}

bool AGolmokZone::BuildFootprintCache()
{
	FootprintUE.Reset();
	FootprintXs.Reset();
	FootprintYs.Reset();
	FootprintBoundsUE = FBox2D(ForceInit);
	if (!bManifestLoaded)
	{
		return false;
	}
	UWorld* World = GetWorld();
	UGolmokGeoSubsystem* Geo = World ? World->GetSubsystem<UGolmokGeoSubsystem>() : nullptr;
	if (!Geo)
	{
		return false;
	}
	// Without an origin actor the zone's own origin acts as area origin (same fallback ApplyRootTransform used).
	const GolmokGeoMath::Mat4 EcefToArea =
		Geo->EcefToAreaMatrix(Manifest.OriginLat, Manifest.OriginLon, Manifest.OriginHeightEllipsoidal);
	FootprintUE.Reserve(Manifest.FootprintLonLat.Num());
	for (const FVector2D& LonLat : Manifest.FootprintLonLat)
	{
		const FVector P = UGolmokGeoSubsystem::LonLatToLevelUE(EcefToArea, LonLat.X, LonLat.Y, Manifest.OriginHeightEllipsoidal);
		FootprintUE.Add(FVector2D(P.X, P.Y));
		FootprintXs.Add(P.X);
		FootprintYs.Add(P.Y);
		FootprintBoundsUE += FVector2D(P.X, P.Y);
	}
	FootprintOriginRevision = Geo->GetOriginRevision();
	return FootprintUE.Num() >= 3;
}

const TArray<FVector2D>& AGolmokZone::GetFootprintUE()
{
	if (bManifestLoaded)
	{
		UWorld* World = GetWorld();
		UGolmokGeoSubsystem* Geo = World ? World->GetSubsystem<UGolmokGeoSubsystem>() : nullptr;
		if (Geo && Geo->GetOriginRevision() != FootprintOriginRevision)
		{
			ApplyRootTransform();
			BuildFootprintCache();
		}
	}
	return FootprintUE;
}

const FBox2D& AGolmokZone::GetFootprintBoundsUE()
{
	GetFootprintUE();
	return FootprintBoundsUE;
}

double AGolmokZone::DistanceToFootprintM(const FVector2D& LevelUEPointCm)
{
	const TArray<FVector2D>& Poly = GetFootprintUE();
	if (Poly.Num() < 3)
	{
		return UnknownDistanceM;
	}
	// A handful of vertices per zone: the exact edge distance is cheap enough (0 inside).
	return GolmokGeoMath::DistanceToPolygon(FootprintXs.GetData(), FootprintYs.GetData(), static_cast<std::size_t>(FootprintXs.Num()),
			   LevelUEPointCm.X, LevelUEPointCm.Y)
		   / 100.0;
}

bool AGolmokZone::FootprintContains(const FVector2D& LevelUEPointCm)
{
	const TArray<FVector2D>& Poly = GetFootprintUE();
	if (Poly.Num() < 3 || !FootprintBoundsUE.IsInside(LevelUEPointCm))
	{
		return false;
	}
	return GolmokGeoMath::PointInPolygon(FootprintXs.GetData(), FootprintYs.GetData(), static_cast<std::size_t>(FootprintXs.Num()),
		LevelUEPointCm.X, LevelUEPointCm.Y);
}

bool AGolmokZone::FootprintOverlaps(AGolmokZone& Other)
{
	const TArray<FVector2D>& A = GetFootprintUE();
	const TArray<FVector2D>& B = Other.GetFootprintUE();
	if (A.Num() < 3 || B.Num() < 3 || !FootprintBoundsUE.Intersect(Other.FootprintBoundsUE))
	{
		return false;
	}
	return GolmokGeoMath::PolygonsOverlap(FootprintXs.GetData(), FootprintYs.GetData(), static_cast<std::size_t>(FootprintXs.Num()),
		Other.FootprintXs.GetData(), Other.FootprintYs.GetData(), static_cast<std::size_t>(Other.FootprintXs.Num()));
}

// ---- load / unload --------------------------------------------------------------------------------------------

UStaticMesh* AGolmokZone::LoadMeshAsset(const FString& ObjectPath)
{
	// Synchronous. LOAD_NoWarn | LOAD_Quiet keeps a missing fixture asset from spamming the log (we warn ourselves).
	return Cast<UStaticMesh>(StaticLoadObject(UStaticMesh::StaticClass(), nullptr, *ObjectPath, nullptr, LOAD_NoWarn | LOAD_Quiet));
}

bool AGolmokZone::Load()
{
	if (State == EGolmokZoneState::Loaded)
	{
		return true;
	}
	if (!EnsureManifest())
	{
		State = EGolmokZoneState::Failed;
		return false;
	}
	if (bAsyncLoad && !bWarnedAsync)
	{
		bWarnedAsync = true;
		UE_LOG(LogGolmok, Warning, TEXT("Zone %s: bAsyncLoad is not implemented yet (TODO FStreamableManager); loading synchronously."), *ZoneId);
	}
	DestroyOwnedComponents();
	const double StartSeconds = FPlatformTime::Seconds();

	// 1) visual chunks — vertices are already zone-local UE cm, so every component sits at the root with identity.
	int32 LoadedChunks = 0;
	for (const FGolmokZoneChunk& Chunk : Manifest.Layers.VisualChunks)
	{
		const FString AssetPath = GolmokZoneManifest::ChunkAssetPath(ZoneId, Version, Chunk.Id);
		if (UStaticMesh* Mesh = LoadMeshAsset(AssetPath))
		{
			if (UStaticMeshComponent* Component = MakeMeshComponent(MakeComponentName(TEXT("Chunk"), Chunk.Id), Mesh, /*bVisual*/ true))
			{
				ChunkComponents.Add(Component);
				++LoadedChunks;
			}
			continue;
		}
		UE_LOG(LogGolmok, Warning, TEXT("Zone %s: chunk asset %s missing%s"), *ZoneId, *AssetPath,
			(bDrawMissingAssetBoxes && Chunk.bHasBbox) ? TEXT("; drawing its bbox as a wire box") : TEXT(""));
		if (bDrawMissingAssetBoxes && Chunk.bHasBbox)
		{
			const FBox Box = GolmokGeo::EnuBoxToUE(Chunk.BboxMinEnu, Chunk.BboxMaxEnu);
			if (UBoxComponent* Proxy = MakeBoxComponent(MakeComponentName(TEXT("Missing"), Chunk.Id), Box.GetCenter(), FRotator::ZeroRotator,
					Box.GetExtent(), /*bCollide*/ false, FColor::Orange))
			{
				PlaceholderBoxes.Add(Proxy);
			}
		}
	}

	// 2) collision mesh(es): hidden, block everything, no shadows.
	int32 LoadedCollision = 0;
	TArray<FString> CollisionIds;
	if (Manifest.Layers.CollisionChunks.Num() > 0)
	{
		for (const FGolmokZoneChunk& Chunk : Manifest.Layers.CollisionChunks)
		{
			CollisionIds.Add(Chunk.Id);
		}
	}
	else
	{
		CollisionIds.Add(FString());
	}
	for (const FString& Id : CollisionIds)
	{
		const FString AssetPath = GolmokZoneManifest::CollisionAssetPath(ZoneId, Version, Id);
		if (UStaticMesh* Mesh = LoadMeshAsset(AssetPath))
		{
			const FName Name = Id.IsEmpty() ? FName(TEXT("Collision")) : MakeComponentName(TEXT("Collision"), Id);
			if (UStaticMeshComponent* Component = MakeMeshComponent(Name, Mesh, /*bVisual*/ false))
			{
				CollisionComponents.Add(Component);
				++LoadedCollision;
			}
		}
		else
		{
			UE_LOG(LogGolmok, Warning, TEXT("Zone %s: collision asset %s missing; the player will fall through this zone."), *ZoneId, *AssetPath);
		}
	}

	// 3) blockers (spec §3.1): thin boxes, local X = normal, Z = height axis, Y = width axis.
	for (const FGolmokBlockerPlane& Plane : Blockers.Planes)
	{
		GolmokGeoMath::Vec3 WidthEnu, HeightEnu;
		GolmokGeoMath::BlockerAxes(GolmokGeo::ToVec3(Plane.NormalEnu), WidthEnu, HeightEnu);
		const FVector NormalUE = GolmokGeo::EnuDirToUE(Plane.NormalEnu.GetSafeNormal());
		const FVector HeightUE = GolmokGeo::EnuDirToUE(GolmokGeo::ToFVector(HeightEnu));
		const FRotator Rotation = FRotationMatrix::MakeFromXZ(NormalUE, HeightUE).Rotator();
		const FVector Extent(BlockerThicknessCm * 0.5, Plane.SizeM.X * 50.0, Plane.SizeM.Y * 50.0);
		const FColor Color = (Plane.Kind == TEXT("glass")) ? FColor::Cyan : FColor::Red;
		if (UBoxComponent* Blocker = MakeBoxComponent(MakeComponentName(TEXT("Blocker"), Plane.Id), GolmokGeo::EnuToUE(Plane.CenterEnu),
				Rotation, Extent, /*bCollide*/ true, Color))
		{
			BlockerComponents.Add(Blocker);
		}
	}

	State = EGolmokZoneState::Loaded;
	LastError.Reset();
	SetVisualVisible(bVisualVisible);
	SetCollisionEnabled(bCollisionOn);
	SpawnPortals();

	UE_LOG(LogGolmok, Log, TEXT("Zone %s v%d loaded in %.1f ms: chunks %d/%d (%d wire boxes), collision %d/%d, blockers %d, portals %d (WP-05)"),
		*ZoneId, Version, (FPlatformTime::Seconds() - StartSeconds) * 1000.0, LoadedChunks, Manifest.Layers.VisualChunks.Num(),
		PlaceholderBoxes.Num(), LoadedCollision, CollisionIds.Num(), BlockerComponents.Num(), Manifest.Portals.Num());

	if (UGolmokZoneSubsystem* Subsystem = GetZoneSubsystem())
	{
		Subsystem->NotifyZoneLoaded(this);
	}
	return true;
}

void AGolmokZone::Unload()
{
	const bool bWasLoaded = State == EGolmokZoneState::Loaded;
	DestroyPortals();
	DestroyOwnedComponents();
	if (State != EGolmokZoneState::Failed)
	{
		State = EGolmokZoneState::Unloaded;
	}
	if (bWasLoaded)
	{
		UE_LOG(LogGolmok, Log, TEXT("Zone %s v%d unloaded"), *ZoneId, Version);
		if (UGolmokZoneSubsystem* Subsystem = GetZoneSubsystem())
		{
			Subsystem->NotifyZoneUnloaded(this);
		}
	}
}

void AGolmokZone::RebuildInEditor()
{
	Unload();
	State = EGolmokZoneState::Unloaded;
	if (!EnsureManifest(/*bForceReload*/ true))
	{
		State = EGolmokZoneState::Failed;
		return;
	}
	Load();
}

void AGolmokZone::UnloadInEditor()
{
	Unload();
}

void AGolmokZone::SpawnPortals()
{
	// WP-05 replaces this with AGolmokPortal spawning; the manifest data is already parsed in Manifest.Portals.
	UE_LOG(LogGolmok, Verbose, TEXT("Zone %s: %d portals parsed (spawning arrives with WP-05)"), *ZoneId, Manifest.Portals.Num());
}

void AGolmokZone::DestroyPortals()
{
	for (TObjectPtr<AActor>& Portal : PortalActors)
	{
		if (IsValid(Portal))
		{
			Portal->Destroy();
		}
	}
	PortalActors.Empty();
}

void AGolmokZone::SetVisualVisible(bool bVisible)
{
	bVisualVisible = bVisible;
	for (const TObjectPtr<UStaticMeshComponent>& Component : ChunkComponents)
	{
		if (IsValid(Component))
		{
			Component->SetVisibility(bVisible, true);
		}
	}
	for (const TObjectPtr<UBoxComponent>& Box : PlaceholderBoxes)
	{
		if (IsValid(Box))
		{
			Box->SetVisibility(bVisible, true);
		}
	}
}

void AGolmokZone::SetCollisionEnabled(bool bEnabled)
{
	bCollisionOn = bEnabled;
	const ECollisionEnabled::Type Mode = bEnabled ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision;
	for (const TObjectPtr<UStaticMeshComponent>& Component : CollisionComponents)
	{
		if (IsValid(Component))
		{
			Component->SetCollisionEnabled(Mode);
		}
	}
	for (const TObjectPtr<UBoxComponent>& Box : BlockerComponents)
	{
		if (IsValid(Box))
		{
			Box->SetCollisionEnabled(Mode);
		}
	}
}

// ---- component factories --------------------------------------------------------------------------------------

UStaticMeshComponent* AGolmokZone::MakeMeshComponent(const FName& Name, UStaticMesh* Mesh, bool bVisual)
{
	if (!Mesh || !Root)
	{
		return nullptr;
	}
	// Unique names: a component destroyed by Unload() a moment ago may still exist until GC.
	UStaticMeshComponent* Component =
		NewObject<UStaticMeshComponent>(this, MakeUniqueObjectName(this, UStaticMeshComponent::StaticClass(), Name), RF_Transient);
	if (!Component)
	{
		return nullptr;
	}
	Component->SetMobility(EComponentMobility::Stationary);
	Component->SetupAttachment(Root);
	Component->SetRelativeTransform(FTransform::Identity);
	Component->SetStaticMesh(Mesh);
	if (bVisual)
	{
		// Visual chunks never collide: the simplified collision layer is authoritative (ARCHITECTURE §4).
		Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Component->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
		Component->SetGenerateOverlapEvents(false);
	}
	else
	{
		Component->SetHiddenInGame(true);
		Component->SetCastShadow(false);
		Component->bAffectDistanceFieldLighting = false;
		Component->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
		Component->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
		Component->SetCanEverAffectNavigation(true);
	}
	Component->RegisterComponent();
	return Component;
}

UBoxComponent* AGolmokZone::MakeBoxComponent(const FName& Name, const FVector& RelativeLocation, const FRotator& RelativeRotation,
	const FVector& Extent, bool bCollide, const FColor& Color)
{
	if (!Root)
	{
		return nullptr;
	}
	UBoxComponent* Box = NewObject<UBoxComponent>(this, MakeUniqueObjectName(this, UBoxComponent::StaticClass(), Name), RF_Transient);
	if (!Box)
	{
		return nullptr;
	}
	Box->SetMobility(EComponentMobility::Stationary);
	Box->SetupAttachment(Root);
	Box->SetRelativeLocationAndRotation(RelativeLocation, RelativeRotation);
	Box->InitBoxExtent(Extent);
	Box->ShapeColor = Color;
	Box->SetLineThickness(2.0f);
	if (bCollide)
	{
		// Blockers: invisible collision only (glass is visible in the scan mesh itself).
		Box->SetHiddenInGame(true);
		Box->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
		Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
		Box->SetCanEverAffectNavigation(true);
	}
	else
	{
		// Placeholder for a missing chunk asset: drawn in game (shape components render their wireframe when not hidden).
		Box->SetHiddenInGame(false);
		Box->bDrawOnlyIfSelected = false;
		Box->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
		Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Box->SetCanEverAffectNavigation(false);
	}
	Box->SetGenerateOverlapEvents(false);
	Box->RegisterComponent();
	return Box;
}

void AGolmokZone::DestroyOwnedComponents()
{
	auto DestroyAll = [](auto& Components) {
		for (auto& Component : Components)
		{
			if (IsValid(Component))
			{
				Component->DestroyComponent();
			}
		}
		Components.Empty();
	};
	DestroyAll(ChunkComponents);
	DestroyAll(CollisionComponents);
	DestroyAll(PlaceholderBoxes);
	DestroyAll(BlockerComponents);
}
