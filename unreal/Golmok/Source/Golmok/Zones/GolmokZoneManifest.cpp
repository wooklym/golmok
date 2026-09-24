#include "Zones/GolmokZoneManifest.h"

#include "Golmok.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Geo/GolmokGeoMath.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	// Keys are passed as FString objects (never TCHAR literals) so the FJsonObject::TryGet*Field overloads that
	// exist in 5.x (const FString& and, since 5.4, FStringView) never become ambiguous.
	using FJsonObjectPtr = TSharedPtr<FJsonObject>;
	using FJsonArray = TArray<TSharedPtr<FJsonValue>>;

	bool Fail(FString& Error, const FString& Message)
	{
		Error = Message;
		return false;
	}

	bool GetObject(const FJsonObjectPtr& Obj, const FString& Key, FJsonObjectPtr& Out, FString& Error, bool bRequired = true)
	{
		const FJsonObjectPtr* Found = nullptr;
		if (Obj.IsValid() && Obj->TryGetObjectField(Key, Found) && Found && Found->IsValid())
		{
			Out = *Found;
			return true;
		}
		Out.Reset();
		return bRequired ? Fail(Error, FString::Printf(TEXT("missing object '%s'"), *Key)) : true;
	}

	bool GetArray(const FJsonObjectPtr& Obj, const FString& Key, const FJsonArray*& Out, FString& Error, bool bRequired = true)
	{
		Out = nullptr;
		if (Obj.IsValid() && Obj->TryGetArrayField(Key, Out) && Out)
		{
			return true;
		}
		return bRequired ? Fail(Error, FString::Printf(TEXT("missing array '%s'"), *Key)) : true;
	}

	bool GetString(const FJsonObjectPtr& Obj, const FString& Key, FString& Out, FString& Error, bool bRequired = true)
	{
		if (Obj.IsValid() && Obj->TryGetStringField(Key, Out))
		{
			return true;
		}
		Out.Reset();
		return bRequired ? Fail(Error, FString::Printf(TEXT("missing string '%s'"), *Key)) : true;
	}

	bool GetNumber(const FJsonObjectPtr& Obj, const FString& Key, double& Out, FString& Error, bool bRequired = true)
	{
		if (Obj.IsValid() && Obj->TryGetNumberField(Key, Out))
		{
			return true;
		}
		Out = 0.0;
		return bRequired ? Fail(Error, FString::Printf(TEXT("missing number '%s'"), *Key)) : true;
	}

	bool GetBool(const FJsonObjectPtr& Obj, const FString& Key, bool& Out, FString& Error, bool bRequired = true)
	{
		if (Obj.IsValid() && Obj->TryGetBoolField(Key, Out))
		{
			return true;
		}
		Out = false;
		return bRequired ? Fail(Error, FString::Printf(TEXT("missing bool '%s'"), *Key)) : true;
	}

	/** JSON number array of exactly N values -> doubles. */
	bool NumberArray(const FJsonArray* Arr, int32 N, TArray<double>& Out, const FString& What, FString& Error)
	{
		Out.Reset();
		if (!Arr || Arr->Num() != N)
		{
			return Fail(Error, FString::Printf(TEXT("'%s' needs %d numbers, got %d"), *What, N, Arr ? Arr->Num() : 0));
		}
		Out.Reserve(N);
		for (const TSharedPtr<FJsonValue>& V : *Arr)
		{
			double D = 0.0;
			if (!V.IsValid() || !V->TryGetNumber(D))
			{
				return Fail(Error, FString::Printf(TEXT("'%s' contains a non-number"), *What));
			}
			Out.Add(D);
		}
		return true;
	}

	bool GetVec3(const FJsonObjectPtr& Obj, const FString& Key, FVector& Out, FString& Error)
	{
		const FJsonArray* Arr = nullptr;
		TArray<double> V;
		if (!GetArray(Obj, Key, Arr, Error) || !NumberArray(Arr, 3, V, Key, Error))
		{
			return false;
		}
		Out = FVector(V[0], V[1], V[2]);
		return true;
	}

	bool ParseChunk(const TSharedPtr<FJsonValue>& Value, bool bRequireBbox, FGolmokZoneChunk& Out, FString& Error)
	{
		const FJsonObjectPtr* ObjPtr = nullptr;
		if (!Value.IsValid() || !Value->TryGetObject(ObjPtr) || !ObjPtr || !ObjPtr->IsValid())
		{
			return Fail(Error, TEXT("chunk is not an object"));
		}
		const FJsonObjectPtr Obj = *ObjPtr;
		if (!GetString(Obj, TEXT("id"), Out.Id, Error) || !GetString(Obj, TEXT("uri"), Out.Uri, Error))
		{
			return false;
		}
		double Tris = 0.0;
		GetNumber(Obj, TEXT("tris"), Tris, Error, false);
		Out.Tris = static_cast<int32>(Tris);
		const FJsonArray* Bbox = nullptr;
		if (GetArray(Obj, TEXT("bbox_enu"), Bbox, Error, false) && Bbox)
		{
			if (Bbox->Num() != 2)
			{
				return Fail(Error, FString::Printf(TEXT("chunk '%s' bbox_enu needs [min, max]"), *Out.Id));
			}
			TArray<double> Lo, Hi;
			const FJsonArray* LoArr = nullptr;
			const FJsonArray* HiArr = nullptr;
			if (!(*Bbox)[0].IsValid() || !(*Bbox)[0]->TryGetArray(LoArr) || !(*Bbox)[1].IsValid() || !(*Bbox)[1]->TryGetArray(HiArr)
				|| !NumberArray(LoArr, 3, Lo, TEXT("bbox_enu[0]"), Error) || !NumberArray(HiArr, 3, Hi, TEXT("bbox_enu[1]"), Error))
			{
				return false;
			}
			Out.BboxMinEnu = FVector(Lo[0], Lo[1], Lo[2]);
			Out.BboxMaxEnu = FVector(Hi[0], Hi[1], Hi[2]);
			Out.bHasBbox = true;
			for (int32 i = 0; i < 3; ++i)
			{
				if (Lo[i] > Hi[i])
				{
					return Fail(Error, FString::Printf(TEXT("chunk '%s' bbox_enu min > max"), *Out.Id));
				}
			}
		}
		else if (bRequireBbox)
		{
			return Fail(Error, FString::Printf(TEXT("chunk '%s' has no bbox_enu"), *Out.Id));
		}
		return true;
	}

	bool ParseJsonObject(const FString& JsonText, FJsonObjectPtr& Root, FString& Error)
	{
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonText);
		if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
		{
			return Fail(Error, FString::Printf(TEXT("invalid JSON: %s"), *Reader->GetErrorMessage()));
		}
		return true;
	}
} // namespace

namespace GolmokZoneManifest
{
	bool ParseManifestText(const FString& JsonText, FGolmokZoneManifest& Out, FString& Error)
	{
		Out = FGolmokZoneManifest();
		FJsonObjectPtr Root;
		if (!ParseJsonObject(JsonText, Root, Error))
		{
			return false;
		}

		double Number = 0.0;
		if (!GetNumber(Root, TEXT("schema_version"), Number, Error))
		{
			return false;
		}
		Out.SchemaVersion = static_cast<int32>(Number);
		if (Out.SchemaVersion != 1)
		{
			return Fail(Error, FString::Printf(TEXT("unsupported schema_version %d (expected 1)"), Out.SchemaVersion));
		}
		if (!GetString(Root, TEXT("zone_id"), Out.ZoneId, Error) || Out.ZoneId.IsEmpty())
		{
			return Fail(Error, TEXT("zone_id missing or empty"));
		}
		if (!GetNumber(Root, TEXT("version"), Number, Error))
		{
			return false;
		}
		Out.Version = static_cast<int32>(Number);
		if (Out.Version < 1)
		{
			return Fail(Error, TEXT("version must be >= 1"));
		}
		if (!GetString(Root, TEXT("kind"), Out.Kind, Error))
		{
			return false;
		}
		if (Out.Kind != TEXT("exterior") && Out.Kind != TEXT("interior"))
		{
			return Fail(Error, FString::Printf(TEXT("kind '%s' must be exterior|interior"), *Out.Kind));
		}
		GetString(Root, TEXT("parent_zone"), Out.ParentZone, Error, false); // null -> empty

		FJsonObjectPtr Origin;
		if (!GetObject(Root, TEXT("origin"), Origin, Error) || !GetNumber(Origin, TEXT("lat"), Out.OriginLat, Error)
			|| !GetNumber(Origin, TEXT("lon"), Out.OriginLon, Error)
			|| !GetNumber(Origin, TEXT("height_ellipsoidal"), Out.OriginHeightEllipsoidal, Error))
		{
			return false;
		}
		if (!GetVec3(Root, TEXT("origin_ecef"), Out.OriginEcef, Error))
		{
			return false;
		}

		const FJsonArray* TransformArr = nullptr;
		if (!GetArray(Root, TEXT("transform"), TransformArr, Error) || !NumberArray(TransformArr, 16, Out.Transform, TEXT("transform"), Error))
		{
			return false;
		}
		{
			GolmokGeoMath::Mat4 M;
			for (int32 i = 0; i < 16; ++i)
			{
				M[static_cast<std::size_t>(i)] = Out.Transform[i];
			}
			double Det = 0.0;
			const double OrthoErr = GolmokGeoMath::RigidityError(M, Det);
			const bool bLastRowOk = FMath::IsNearlyZero(M[12], 1e-9) && FMath::IsNearlyZero(M[13], 1e-9) && FMath::IsNearlyZero(M[14], 1e-9)
									&& FMath::IsNearlyEqual(M[15], 1.0, 1e-9);
			if (OrthoErr > 1e-6 || FMath::Abs(Det - 1.0) > 1e-6 || !bLastRowOk)
			{
				return Fail(Error, FString::Printf(TEXT("transform is not rigid (|R^T R - I| = %.2e, det = %.6f, last row ok = %d)"),
					OrthoErr, Det, bLastRowOk ? 1 : 0));
			}
			const FVector T(M[3], M[7], M[11]);
			if (!T.Equals(Out.OriginEcef, 0.01))
			{
				return Fail(Error, TEXT("origin_ecef differs from the transform translation by more than 1 cm"));
			}
		}

		FJsonObjectPtr Footprint;
		FString FootprintType;
		const FJsonArray* Rings = nullptr;
		if (!GetObject(Root, TEXT("footprint_wgs84"), Footprint, Error) || !GetString(Footprint, TEXT("type"), FootprintType, Error)
			|| !GetArray(Footprint, TEXT("coordinates"), Rings, Error))
		{
			return false;
		}
		if (FootprintType != TEXT("Polygon") || Rings->Num() < 1)
		{
			return Fail(Error, TEXT("footprint_wgs84 must be a GeoJSON Polygon with an outer ring"));
		}
		{
			const FJsonArray* Ring = nullptr;
			if (!(*Rings)[0].IsValid() || !(*Rings)[0]->TryGetArray(Ring) || !Ring)
			{
				return Fail(Error, TEXT("footprint_wgs84.coordinates[0] is not an array"));
			}
			for (const TSharedPtr<FJsonValue>& PointValue : *Ring)
			{
				const FJsonArray* Point = nullptr;
				if (!PointValue.IsValid() || !PointValue->TryGetArray(Point) || !Point || Point->Num() < 2)
				{
					return Fail(Error, TEXT("footprint_wgs84 vertex is not [lon, lat]"));
				}
				double Lon = 0.0, Lat = 0.0;
				if (!(*Point)[0]->TryGetNumber(Lon) || !(*Point)[1]->TryGetNumber(Lat))
				{
					return Fail(Error, TEXT("footprint_wgs84 vertex is not numeric"));
				}
				Out.FootprintLonLat.Add(FVector2D(Lon, Lat));
			}
			if (Out.FootprintLonLat.Num() >= 2 && Out.FootprintLonLat[0].Equals(Out.FootprintLonLat.Last(), 1e-12))
			{
				Out.FootprintLonLat.Pop();
			}
			if (Out.FootprintLonLat.Num() < 3)
			{
				return Fail(Error, TEXT("footprint_wgs84 needs at least 3 distinct vertices"));
			}
		}

		FJsonObjectPtr Replaces;
		const FJsonArray* BuildingIds = nullptr;
		if (!GetObject(Root, TEXT("replaces"), Replaces, Error) || !GetArray(Replaces, TEXT("building_ids"), BuildingIds, Error)
			|| !GetBool(Replaces, TEXT("terrain_clip"), Out.bTerrainClip, Error))
		{
			return false;
		}
		for (const TSharedPtr<FJsonValue>& V : *BuildingIds)
		{
			FString Id;
			if (V.IsValid() && V->TryGetString(Id))
			{
				Out.ReplacesBuildingIds.Add(Id);
			}
		}

		FJsonObjectPtr Layers, Visual, Collision, Blockers, Navmesh;
		const FJsonArray* Chunks = nullptr;
		if (!GetObject(Root, TEXT("layers"), Layers, Error) || !GetObject(Layers, TEXT("visual"), Visual, Error)
			|| !GetString(Visual, TEXT("format"), Out.Layers.VisualFormat, Error) || !GetArray(Visual, TEXT("chunks"), Chunks, Error))
		{
			return false;
		}
		for (const TSharedPtr<FJsonValue>& V : *Chunks)
		{
			FGolmokZoneChunk Chunk;
			if (!ParseChunk(V, /*bRequireBbox*/ true, Chunk, Error))
			{
				return false;
			}
			Out.Layers.VisualChunks.Add(MoveTemp(Chunk));
		}
		if (!GetObject(Layers, TEXT("collision"), Collision, Error) || !GetString(Collision, TEXT("uri"), Out.Layers.CollisionUri, Error))
		{
			return false;
		}
		GetString(Collision, TEXT("format"), Out.Layers.CollisionFormat, Error, false);
		const FJsonArray* CollisionChunks = nullptr;
		if (GetArray(Collision, TEXT("chunks"), CollisionChunks, Error, false) && CollisionChunks)
		{
			for (const TSharedPtr<FJsonValue>& V : *CollisionChunks)
			{
				FGolmokZoneChunk Chunk;
				if (!ParseChunk(V, /*bRequireBbox*/ false, Chunk, Error))
				{
					return false;
				}
				Out.Layers.CollisionChunks.Add(MoveTemp(Chunk));
			}
		}
		if (GetObject(Layers, TEXT("blockers"), Blockers, Error, false) && Blockers.IsValid())
		{
			GetString(Blockers, TEXT("uri"), Out.Layers.BlockersUri, Error, false);
		}
		if (GetObject(Layers, TEXT("navmesh"), Navmesh, Error, false) && Navmesh.IsValid())
		{
			GetString(Navmesh, TEXT("uri"), Out.Layers.NavmeshUri, Error, false);
		}

		const FJsonArray* Portals = nullptr;
		if (!GetArray(Root, TEXT("portals"), Portals, Error))
		{
			return false;
		}
		for (const TSharedPtr<FJsonValue>& V : *Portals)
		{
			const FJsonObjectPtr* PortalObjPtr = nullptr;
			if (!V.IsValid() || !V->TryGetObject(PortalObjPtr) || !PortalObjPtr || !PortalObjPtr->IsValid())
			{
				return Fail(Error, TEXT("portal is not an object"));
			}
			const FJsonObjectPtr PortalObj = *PortalObjPtr;
			FGolmokZonePortal Portal;
			FJsonObjectPtr Pose;
			if (!GetString(PortalObj, TEXT("id"), Portal.Id, Error) || !GetString(PortalObj, TEXT("to_zone"), Portal.ToZone, Error)
				|| !GetObject(PortalObj, TEXT("pose_enu"), Pose, Error) || !GetVec3(Pose, TEXT("position"), Portal.PositionEnu, Error)
				|| !GetNumber(Pose, TEXT("yaw_deg"), Portal.YawDeg, Error) || !GetNumber(PortalObj, TEXT("radius_m"), Portal.RadiusM, Error)
				|| !GetString(PortalObj, TEXT("kind"), Portal.Kind, Error))
			{
				return false;
			}
			if (Portal.ToZone == Out.ZoneId)
			{
				return Fail(Error, FString::Printf(TEXT("portal '%s' points at its own zone"), *Portal.Id));
			}
			Out.Portals.Add(MoveTemp(Portal));
		}

		if (!GetNumber(Root, TEXT("priority"), Number, Error))
		{
			return false;
		}
		Out.Priority = static_cast<int32>(Number);
		return true;
	}

	bool LoadManifest(const FString& FilePath, FGolmokZoneManifest& Out, FString& Error)
	{
		FString Text;
		if (!FFileHelper::LoadFileToString(Text, *FilePath))
		{
			return Fail(Error, FString::Printf(TEXT("cannot read %s"), *FilePath));
		}
		if (!ParseManifestText(Text, Out, Error))
		{
			Error = FString::Printf(TEXT("%s: %s"), *FilePath, *Error);
			return false;
		}
		return true;
	}

	bool ParseBlockersText(const FString& JsonText, FGolmokBlockers& Out, FString& Error)
	{
		Out = FGolmokBlockers();
		FJsonObjectPtr Root;
		if (!ParseJsonObject(JsonText, Root, Error))
		{
			return false;
		}
		const FJsonArray* Planes = nullptr;
		if (!GetArray(Root, TEXT("planes"), Planes, Error))
		{
			return false;
		}
		for (const TSharedPtr<FJsonValue>& V : *Planes)
		{
			const FJsonObjectPtr* PlaneObjPtr = nullptr;
			if (!V.IsValid() || !V->TryGetObject(PlaneObjPtr) || !PlaneObjPtr || !PlaneObjPtr->IsValid())
			{
				return Fail(Error, TEXT("plane is not an object"));
			}
			const FJsonObjectPtr PlaneObj = *PlaneObjPtr;
			FGolmokBlockerPlane Plane;
			const FJsonArray* SizeArr = nullptr;
			TArray<double> Size;
			if (!GetString(PlaneObj, TEXT("id"), Plane.Id, Error) || !GetVec3(PlaneObj, TEXT("center_enu"), Plane.CenterEnu, Error)
				|| !GetVec3(PlaneObj, TEXT("normal_enu"), Plane.NormalEnu, Error) || !GetArray(PlaneObj, TEXT("size_m"), SizeArr, Error)
				|| !NumberArray(SizeArr, 2, Size, TEXT("size_m"), Error) || !GetString(PlaneObj, TEXT("kind"), Plane.Kind, Error))
			{
				return false;
			}
			Plane.SizeM = FVector2D(Size[0], Size[1]);
			if (Plane.NormalEnu.IsNearlyZero())
			{
				return Fail(Error, FString::Printf(TEXT("plane '%s' has a zero normal"), *Plane.Id));
			}
			if (Plane.SizeM.X <= 0.0 || Plane.SizeM.Y <= 0.0)
			{
				return Fail(Error, FString::Printf(TEXT("plane '%s' size_m must be positive"), *Plane.Id));
			}
			Out.Planes.Add(MoveTemp(Plane));
		}
		return true;
	}

	bool LoadBlockers(const FString& FilePath, FGolmokBlockers& Out, FString& Error)
	{
		FString Text;
		if (!FFileHelper::LoadFileToString(Text, *FilePath))
		{
			return Fail(Error, FString::Printf(TEXT("cannot read %s"), *FilePath));
		}
		if (!ParseBlockersText(Text, Out, Error))
		{
			Error = FString::Printf(TEXT("%s: %s"), *FilePath, *Error);
			return false;
		}
		return true;
	}

	FString ManifestFilePath(const FString& ZoneId, int32 Version)
	{
		return FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Golmok"), TEXT("Zones"), ZoneId,
			FString::Printf(TEXT("v%d"), Version), TEXT("manifest.json"));
	}

	FString AssetFolder(const FString& ZoneId, int32 Version)
	{
		return FString::Printf(TEXT("/Game/Golmok/Zones/%s/v%d"), *ZoneId, Version);
	}

	FString ChunkAssetPath(const FString& ZoneId, int32 Version, const FString& ChunkId)
	{
		const FString Name = FString::Printf(TEXT("SM_%s"), *ChunkId);
		return FString::Printf(TEXT("%s/%s.%s"), *AssetFolder(ZoneId, Version), *Name, *Name);
	}

	FString CollisionAssetPath(const FString& ZoneId, int32 Version, const FString& ChunkId)
	{
		const FString Name = ChunkId.IsEmpty() ? FString::Printf(TEXT("SM_%s_collision"), *ZoneId)
											   : FString::Printf(TEXT("SM_%s_collision_%s"), *ZoneId, *ChunkId);
		return FString::Printf(TEXT("%s/%s.%s"), *AssetFolder(ZoneId, Version), *Name, *Name);
	}
} // namespace GolmokZoneManifest
