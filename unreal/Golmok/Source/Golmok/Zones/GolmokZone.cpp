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
#include "Materials/MaterialInterface.h"
#include "Misc/Paths.h"
#include "Portals/GolmokPortal.h"
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
		Unload();
		State = EGolmokZoneState::Unloaded;
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
		// Spec §2/§3.2: folder name and manifest must agree; a copy into the wrong folder is a setup error.
		LastError = FString::Printf(TEXT("manifest says zone_id=%s version=%d but the actor/folder is %s v%d"), *Manifest.ZoneId,
			Manifest.Version, *ZoneId, Version);
		UE_LOG(LogGolmok, Error, TEXT("Zone %s v%d: %s"), *ZoneId, Version, *LastError);
		return false;
	}
	if (Manifest.Layers.Visual.Format != EGolmokVisualFormat::NaniteMesh)
	{
		UE_LOG(LogGolmok, Warning, TEXT("Zone %s: visual format '%s' is not implemented yet (nanite_mesh only, D-010); chunks get wire boxes."),
			*ZoneId, *Manifest.Layers.Visual.FormatString);
	}

	Blockers = FGolmokBlockers();
	if (Manifest.Layers.Blockers.bPresent)
	{
		const FString BlockersPath = FPaths::Combine(FPaths::GetPath(Path), Manifest.Layers.Blockers.Uri);
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

double AGolmokZone::DistanceToBoundsM(const FVector2D& LevelUEPointCm)
{
	const TArray<FVector2D>& Poly = GetFootprintUE();
	if (Poly.Num() < 3)
	{
		return UnknownDistanceM;
	}
	const FVector2D Clamped(FMath::Clamp(LevelUEPointCm.X, FootprintBoundsUE.Min.X, FootprintBoundsUE.Max.X),
		FMath::Clamp(LevelUEPointCm.Y, FootprintBoundsUE.Min.Y, FootprintBoundsUE.Max.Y));
	return FVector2D::Distance(Clamped, LevelUEPointCm) / 100.0;
}

FTransform AGolmokZone::GetPortalWorldTransform(const FGolmokZonePortal& Portal) const
{
	const FTransform Relative(FRotator(0.0, -Portal.YawDeg, 0.0), GolmokGeo::EnuToUE(Portal.PositionEnu), FVector::OneVector);
	return Relative * GetActorTransform();
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
	MissingAssetCount = 0;
	const double StartSeconds = FPlatformTime::Seconds();

	const int32 NumChunks = BuildVisualLayer();
	const int32 NumCollision = BuildCollisionLayer();
	const int32 NumBlockers = BuildBlockers();

	State = EGolmokZoneState::Loaded;
	LastError.Reset();
	SetVisualVisible(bVisualVisible);
	SetCollisionEnabled(bCollisionOn);
	SpawnPortals();

	const int32 NumCollisionWanted = FMath::Max(1, Manifest.Layers.Collision.Chunks.Num());
	UE_LOG(LogGolmok, Log, TEXT("Zone %s v%d loaded in %.1f ms: chunks %d/%d (%d wire boxes), collision %d/%d, blockers %d/%d, portals %d (WP-05)"),
		*ZoneId, Version, (FPlatformTime::Seconds() - StartSeconds) * 1000.0, NumChunks, Manifest.Layers.Visual.Chunks.Num(),
		PlaceholderBoxes.Num(), NumCollision, NumCollisionWanted, NumBlockers, Blockers.Planes.Num(), Manifest.Portals.Num());

	if (UGolmokZoneSubsystem* Subsystem = GetZoneSubsystem())
	{
		Subsystem->NotifyZoneLoaded(this);
	}
	return true;
}

int32 AGolmokZone::BuildVisualLayer()
{
	// Vertices are already zone-local UE cm (spec §5), so every chunk component sits at the root with identity.
	int32 Loaded = 0;
	const bool bMeshFormat = Manifest.Layers.Visual.Format == EGolmokVisualFormat::NaniteMesh;
	for (const FGolmokZoneChunk& Chunk : Manifest.Layers.Visual.Chunks)
	{
		const FString AssetPath = GolmokZoneManifest::ChunkAssetPath(ZoneId, Version, Chunk.Id);
		UStaticMesh* Mesh = bMeshFormat ? LoadMeshAsset(AssetPath) : nullptr;
		if (Mesh)
		{
			if (UStaticMeshComponent* Component = MakeMeshComponent(MakeComponentName(TEXT("Chunk"), Chunk.Id), Mesh, /*bVisual*/ true, Chunk.Id))
			{
				ChunkComponents.Add(Component);
				++Loaded;
				if (Chunk.bHasBbox)
				{
					// Runbook check: bbox center in level coordinates (few chunks -> Log, many -> Verbose).
					const FVector Center = GetActorTransform().TransformPosition(GolmokGeo::EnuBoxToUE(Chunk.BboxMinEnu, Chunk.BboxMaxEnu).GetCenter());
					if (Manifest.Layers.Visual.Chunks.Num() <= 16)
					{
						UE_LOG(LogGolmok, Log, TEXT("Zone %s: chunk %s bbox center -> level (%.2f, %.2f, %.2f) cm"), *ZoneId, *Chunk.Id, Center.X,
							Center.Y, Center.Z);
					}
					else
					{
						UE_LOG(LogGolmok, Verbose, TEXT("Zone %s: chunk %s bbox center -> level (%.2f, %.2f, %.2f) cm"), *ZoneId, *Chunk.Id, Center.X,
							Center.Y, Center.Z);
					}
				}
			}
			continue;
		}
		++MissingAssetCount;
		if (bMeshFormat)
		{
			UE_LOG(LogGolmok, Warning, TEXT("Zone %s: chunk asset %s missing%s"), *ZoneId, *AssetPath,
				(bDrawMissingAssetBoxes && Chunk.bHasBbox) ? TEXT("; drawing its bbox as a wire box") : TEXT(""));
		}
		if (bDrawMissingAssetBoxes && Chunk.bHasBbox)
		{
			const FBox Box = GolmokGeo::EnuBoxToUE(Chunk.BboxMinEnu, Chunk.BboxMaxEnu);
			if (UBoxComponent* Proxy = MakeBoxComponent(MakeComponentName(TEXT("Missing"), Chunk.Id), Box.GetCenter(), FRotator::ZeroRotator,
					Box.GetExtent(), /*bCollide*/ false, FColor::Orange, Chunk.Id))
			{
				PlaceholderBoxes.Add(Proxy);
			}
		}
	}
	return Loaded;
}

int32 AGolmokZone::BuildCollisionLayer()
{
	// Hidden, blocks everything, no shadows. One asset per collision chunk when the manifest lists chunks.
	int32 Loaded = 0;
	TArray<FString> CollisionIds;
	for (const FGolmokZoneChunk& Chunk : Manifest.Layers.Collision.Chunks)
	{
		CollisionIds.Add(Chunk.Id);
	}
	if (CollisionIds.Num() == 0)
	{
		CollisionIds.Add(FString());
	}
	for (const FString& Id : CollisionIds)
	{
		const FString AssetPath = GolmokZoneManifest::CollisionAssetPath(ZoneId, Version, Id);
		if (UStaticMesh* Mesh = LoadMeshAsset(AssetPath))
		{
			const FName Name = Id.IsEmpty() ? FName(TEXT("Collision")) : MakeComponentName(TEXT("Collision"), Id);
			if (UStaticMeshComponent* Component = MakeMeshComponent(Name, Mesh, /*bVisual*/ false, Id.IsEmpty() ? TEXT("collision") : Id))
			{
				CollisionComponents.Add(Component);
				++Loaded;
			}
		}
		else
		{
			++MissingAssetCount;
			UE_LOG(LogGolmok, Warning, TEXT("Zone %s: collision asset %s missing; the player will fall through this zone."), *ZoneId, *AssetPath);
		}
	}
	return Loaded;
}

int32 AGolmokZone::BuildBlockers()
{
	// Spec §3.1: thin boxes; local X = plane normal, Z = height axis (zone +z projected onto the plane, +north when
	// horizontal), Y = width axis. Both kinds are physical walls; glass is visible in the scan mesh itself.
	int32 Built = 0;
	for (const FGolmokBlockerPlane& Plane : Blockers.Planes)
	{
		GolmokGeoMath::Vec3 WidthEnu, HeightEnu;
		GolmokGeoMath::BlockerAxes(GolmokGeo::ToVec3(Plane.NormalEnu), WidthEnu, HeightEnu);
		const FVector NormalUE = GolmokGeo::EnuDirToUE(Plane.NormalEnu.GetSafeNormal());
		const FVector HeightUE = GolmokGeo::EnuDirToUE(GolmokGeo::ToFVector(HeightEnu));
		// MakeFromXZ builds a proper (det +1) UE frame; FMatrix(Dn, Dw, Dh) would be improper because D flips handedness.
		const FRotator Rotation = FRotationMatrix::MakeFromXZ(NormalUE, HeightUE).Rotator();
		const FVector Extent(BlockerThicknessCm * 0.5, Plane.SizeM.X * 50.0, Plane.SizeM.Y * 50.0);
		const FColor Color = (Plane.Kind == EGolmokBlockerKind::Glass) ? FColor::Cyan : FColor::Red;
		const FVector RelCenter = GolmokGeo::EnuToUE(Plane.CenterEnu);
		if (UBoxComponent* Blocker = MakeBoxComponent(MakeComponentName(TEXT("Blocker"), Plane.Id), RelCenter, Rotation, Extent, /*bCollide*/ true, Color, Plane.Id))
		{
			BlockerComponents.Add(Blocker);
			++Built;
			const FVector LevelCenter = GetActorTransform().TransformPosition(RelCenter);
			UE_LOG(LogGolmok, Log, TEXT("Zone %s: blocker %s (%s) rel (%.0f, %.0f, %.0f) cm yaw %.1f extent (%.0f, %.0f, %.0f) -> level (%.2f, %.2f, %.2f)"),
				*ZoneId, *Plane.Id, Plane.Kind == EGolmokBlockerKind::Glass ? TEXT("glass") : TEXT("no_entry"), RelCenter.X, RelCenter.Y, RelCenter.Z,
				Rotation.Yaw, Extent.X, Extent.Y, Extent.Z, LevelCenter.X, LevelCenter.Y, LevelCenter.Z);
		}
	}
	return Built;
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
	// One transient AGolmokPortal per manifest portal (WP-05 design section 3-3). Deferred construction so the
	// manifest fields are set before BeginPlay; no Params.Name (a reload would collide with the dying actor's name).
	// Also runs in editor worlds (RebuildInEditor) so the placement can be checked; there BeginPlay never runs.
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	DestroyPortals(); // re-entrancy safe
	for (const FGolmokZonePortal& P : Manifest.Portals)
	{
		const FTransform T = GetPortalWorldTransform(P);
		FActorSpawnParameters Params;
		Params.Owner = this;
		Params.ObjectFlags = EObjectFlags(Params.ObjectFlags | RF_Transient); // never saved, even from the editor world
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		Params.bDeferConstruction = true;
		AGolmokPortal* Portal = World->SpawnActor<AGolmokPortal>(AGolmokPortal::StaticClass(), T, Params);
		if (!Portal)
		{
			UE_LOG(LogGolmok, Warning, TEXT("Zone %s: portal %s could not be spawned"), *ZoneId, *P.Id);
			continue;
		}
		Portal->Configure(*this, P);
#if WITH_EDITOR
		Portal->SetActorLabel(FString::Printf(TEXT("Portal_%s_%s"), *ZoneId, *P.Id));
#endif
		Portal->FinishSpawning(T);
		PortalActors.Add(Portal);
		const FVector Rel = GolmokGeo::EnuToUE(P.PositionEnu);
		const FVector Loc = T.GetLocation();
		UE_LOG(LogGolmok, Log, TEXT("Zone %s: portal %s -> %s rel (%.0f, %.0f, %.0f) cm yaw %.1f radius %.0f cm -> level (%.2f, %.2f, %.2f) [%s]"),
			*ZoneId, *P.Id, *P.ToZone, Rel.X, Rel.Y, Rel.Z, -P.YawDeg, PortalRadiusCm(P), Loc.X, Loc.Y, Loc.Z,
			IsInterior() ? TEXT("marker") : TEXT("entry"));
	}
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

void AGolmokZone::SetCollisionDebugVisible(bool bVisible, UMaterialInterface* WireMaterial)
{
	for (const TObjectPtr<UStaticMeshComponent>& Component : CollisionComponents)
	{
		if (!IsValid(Component))
		{
			continue;
		}
		Component->SetHiddenInGame(!bVisible);
		const int32 NumMaterials = Component->GetNumMaterials();
		for (int32 i = 0; i < NumMaterials; ++i)
		{
			Component->SetMaterial(i, bVisible ? WireMaterial : nullptr);
		}
	}
	for (const TObjectPtr<UBoxComponent>& Box : BlockerComponents)
	{
		if (IsValid(Box))
		{
			Box->SetHiddenInGame(!bVisible);
		}
	}
	for (const TObjectPtr<UBoxComponent>& Box : PlaceholderBoxes)
	{
		if (IsValid(Box))
		{
			// Placeholder wire boxes are drawn in game by default (MakeBoxComponent); never hide them here.
			Box->SetHiddenInGame(false);
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

FName AGolmokZone::UniqueComponentName(const FName& Base) const
{
	// Destroyed components are renamed to TRASH_* (see DestroyOwnedComponents), so the exact name is normally free.
	// MakeUniqueObjectName would rewrite ids that end in _<digits> (glass_1 -> glass_2), so add our own suffix instead.
	UObject* Outer = const_cast<AGolmokZone*>(this);
	if (!StaticFindObjectFast(nullptr, Outer, Base))
	{
		return Base;
	}
	for (int32 i = 1; i < 1000; ++i)
	{
		const FName Candidate(*FString::Printf(TEXT("%s__%d"), *Base.ToString(), i));
		if (!StaticFindObjectFast(nullptr, Outer, Candidate))
		{
			return Candidate;
		}
	}
	return NAME_None; // NewObject picks a name
}

UStaticMeshComponent* AGolmokZone::MakeMeshComponent(const FName& Name, UStaticMesh* Mesh, bool bVisual, const FString& Tag)
{
	if (!Mesh || !Root)
	{
		return nullptr;
	}
	UStaticMeshComponent* Component = NewObject<UStaticMeshComponent>(this, UniqueComponentName(Name), RF_Transient);
	if (!Component)
	{
		return nullptr;
	}
	Component->ComponentTags.Add(FName(*Tag));
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
	const FVector& Extent, bool bCollide, const FColor& Color, const FString& Tag)
{
	if (!Root)
	{
		return nullptr;
	}
	UBoxComponent* Box = NewObject<UBoxComponent>(this, UniqueComponentName(Name), RF_Transient);
	if (!Box)
	{
		return nullptr;
	}
	Box->ComponentTags.Add(FName(*Tag));
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
	// Same pattern as AActor::DestroyConstructedComponents: rename the dead component out of the way so the next
	// Load() can reuse the exact name (Chunk_<id>, Blocker_<id>) before the garbage collector runs.
	auto DestroyAll = [this](auto& Components) {
		for (auto& Component : Components)
		{
			if (IsValid(Component))
			{
				Component->DestroyComponent();
				const FName Trash = MakeUniqueObjectName(this, Component->GetClass(), TEXT("TRASH_Golmok"));
				Component->Rename(*Trash.ToString(), this, REN_DontCreateRedirectors | REN_DoNotDirty | REN_NonTransactional);
			}
		}
		Components.Empty();
	};
	DestroyAll(ChunkComponents);
	DestroyAll(CollisionComponents);
	DestroyAll(PlaceholderBoxes);
	DestroyAll(BlockerComponents);
}
