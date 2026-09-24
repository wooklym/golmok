#include "Zones/GolmokZoneManifest.h"

#include "Golmok.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Geo/GolmokGeoMath.h"
#include "Internationalization/Regex.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

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

	bool GetStringArray(const FJsonObjectPtr& Obj, const FString& Key, TArray<FString>& Out, FString& Error, bool bRequired = true)
	{
		Out.Reset();
		const FJsonArray* Arr = nullptr;
		if (!GetArray(Obj, Key, Arr, Error, bRequired))
		{
			return false;
		}
		if (Arr)
		{
			for (const TSharedPtr<FJsonValue>& V : *Arr)
			{
				FString S;
				if (!V.IsValid() || !V->TryGetString(S))
				{
					return Fail(Error, FString::Printf(TEXT("'%s' contains a non-string"), *Key));
				}
				Out.Add(S);
			}
		}
		return true;
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

	bool ObjectOf(const TSharedPtr<FJsonValue>& Value, FJsonObjectPtr& Out, const FString& What, FString& Error)
	{
		const FJsonObjectPtr* ObjPtr = nullptr;
		if (!Value.IsValid() || !Value->TryGetObject(ObjPtr) || !ObjPtr || !ObjPtr->IsValid())
		{
			return Fail(Error, FString::Printf(TEXT("%s is not an object"), *What));
		}
		Out = *ObjPtr;
		return true;
	}

	bool CheckUri(const FString& Uri, const FString& What, FString& Error)
	{
		if (!GolmokZoneManifest::IsSafeRelativeUri(Uri))
		{
			return Fail(Error, FString::Printf(TEXT("%s uri '%s' is not a safe relative path (spec §2)"), *What, *Uri));
		}
		return true;
	}

	bool ParseChunk(const TSharedPtr<FJsonValue>& Value, bool bVisual, FGolmokZoneChunk& Out, FString& Error)
	{
		FJsonObjectPtr Obj;
		if (!ObjectOf(Value, Obj, TEXT("chunk"), Error))
		{
			return false;
		}
		if (!GetString(Obj, TEXT("id"), Out.Id, Error) || !GetString(Obj, TEXT("uri"), Out.Uri, Error))
		{
			return false;
		}
		if (!CheckUri(Out.Uri, FString::Printf(TEXT("chunk '%s'"), *Out.Id), Error))
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
		else if (bVisual)
		{
			UE_LOG(LogGolmok, Warning, TEXT("Zone manifest: visual chunk '%s' has no bbox_enu (run golmok-mesh chunk --manifest)."), *Out.Id);
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

	bool ParseTransform(const FJsonObjectPtr& Root, FGolmokZoneManifest& Out, FString& Error)
	{
		const FJsonArray* TransformArr = nullptr;
		if (!GetArray(Root, TEXT("transform"), TransformArr, Error) || !NumberArray(TransformArr, 16, Out.Transform, TEXT("transform"), Error))
		{
			return false;
		}
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
			return Fail(Error, FString::Printf(TEXT("transform is not rigid (|R^T R - I| = %.2e, det = %.6f, last row ok = %d)"), OrthoErr,
				Det, bLastRowOk ? 1 : 0));
		}
		const FVector T(M[3], M[7], M[11]);
		if (!T.Equals(Out.OriginEcef, 0.001))
		{
			UE_LOG(LogGolmok, Warning, TEXT("Zone manifest %s: origin_ecef differs from the transform translation by %.4f m (> 1 mm)."), *Out.ZoneId,
				FVector::Dist(T, Out.OriginEcef));
		}
		// origin (geodetic) must be the same point as the translation, within 1 mm.
		const GolmokGeoMath::Vec3 OriginEcef = GolmokGeoMath::GeodeticToEcef(Out.OriginLat, Out.OriginLon, Out.OriginHeightEllipsoidal);
		const FVector OriginFromGeodetic(OriginEcef[0], OriginEcef[1], OriginEcef[2]);
		if (!T.Equals(OriginFromGeodetic, 0.001))
		{
			UE_LOG(LogGolmok, Warning, TEXT("Zone manifest %s: origin (lat/lon/h) differs from the transform translation by %.4f m (> 1 mm)."),
				*Out.ZoneId, FVector::Dist(T, OriginFromGeodetic));
		}
		return true;
	}

	bool ParseFootprint(const FJsonObjectPtr& Root, FGolmokZoneManifest& Out, FString& Error)
	{
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
		if (Rings->Num() > 1)
		{
			UE_LOG(LogGolmok, Warning, TEXT("Zone manifest %s: footprint has %d holes; holes are ignored at runtime."), *Out.ZoneId, Rings->Num() - 1);
		}
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
			if (!(*Point)[0].IsValid() || !(*Point)[0]->TryGetNumber(Lon) || !(*Point)[1].IsValid() || !(*Point)[1]->TryGetNumber(Lat))
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
		return true;
	}

	bool ParseLayers(const FJsonObjectPtr& Root, FGolmokZoneManifest& Out, FString& Error)
	{
		FJsonObjectPtr Layers, Visual, Collision, Blockers, Navmesh;
		const FJsonArray* Chunks = nullptr;
		if (!GetObject(Root, TEXT("layers"), Layers, Error) || !GetObject(Layers, TEXT("visual"), Visual, Error)
			|| !GetString(Visual, TEXT("format"), Out.Layers.Visual.FormatString, Error) || !GetArray(Visual, TEXT("chunks"), Chunks, Error))
		{
			return false;
		}
		Out.Layers.Visual.Format = GolmokZoneManifest::ParseVisualFormat(Out.Layers.Visual.FormatString);
		if (Out.Layers.Visual.Format == EGolmokVisualFormat::Unknown)
		{
			UE_LOG(LogGolmok, Warning, TEXT("Zone manifest %s: unknown layers.visual.format '%s'."), *Out.ZoneId, *Out.Layers.Visual.FormatString);
		}
		for (const TSharedPtr<FJsonValue>& V : *Chunks)
		{
			FGolmokZoneChunk Chunk;
			if (!ParseChunk(V, /*bVisual*/ true, Chunk, Error))
			{
				return false;
			}
			Out.Layers.Visual.Chunks.Add(MoveTemp(Chunk));
		}
		const FJsonArray* Textures = nullptr;
		if (GetArray(Visual, TEXT("textures"), Textures, Error, false) && Textures)
		{
			for (const TSharedPtr<FJsonValue>& V : *Textures)
			{
				FJsonObjectPtr TexObj;
				FGolmokZoneTexture Tex;
				if (!ObjectOf(V, TexObj, TEXT("texture"), Error) || !GetString(TexObj, TEXT("uri"), Tex.Uri, Error)
					|| !CheckUri(Tex.Uri, TEXT("texture"), Error))
				{
					return false;
				}
				GetString(TexObj, TEXT("chunk_id"), Tex.ChunkId, Error, false);
				GetString(TexObj, TEXT("role"), Tex.Role, Error, false);
				Out.Layers.Visual.Textures.Add(MoveTemp(Tex));
			}
		}

		if (!GetObject(Layers, TEXT("collision"), Collision, Error) || !GetString(Collision, TEXT("format"), Out.Layers.Collision.Format, Error)
			|| !GetString(Collision, TEXT("uri"), Out.Layers.Collision.Uri, Error) || !CheckUri(Out.Layers.Collision.Uri, TEXT("collision"), Error))
		{
			return false;
		}
		if (Out.Layers.Collision.Format != TEXT("glb"))
		{
			return Fail(Error, FString::Printf(TEXT("layers.collision.format '%s' must be glb"), *Out.Layers.Collision.Format));
		}
		const FJsonArray* CollisionChunks = nullptr;
		if (GetArray(Collision, TEXT("chunks"), CollisionChunks, Error, false) && CollisionChunks)
		{
			for (const TSharedPtr<FJsonValue>& V : *CollisionChunks)
			{
				FGolmokZoneChunk Chunk;
				if (!ParseChunk(V, /*bVisual*/ false, Chunk, Error))
				{
					return false;
				}
				Out.Layers.Collision.Chunks.Add(MoveTemp(Chunk));
			}
		}
		if (GetObject(Layers, TEXT("blockers"), Blockers, Error, false) && Blockers.IsValid())
		{
			if (!GetString(Blockers, TEXT("uri"), Out.Layers.Blockers.Uri, Error) || !CheckUri(Out.Layers.Blockers.Uri, TEXT("blockers"), Error))
			{
				return false;
			}
			Out.Layers.Blockers.bPresent = true;
		}
		if (GetObject(Layers, TEXT("navmesh"), Navmesh, Error, false) && Navmesh.IsValid())
		{
			if (!GetString(Navmesh, TEXT("uri"), Out.Layers.Navmesh.Uri, Error) || !CheckUri(Out.Layers.Navmesh.Uri, TEXT("navmesh"), Error))
			{
				return false;
			}
			GetString(Navmesh, TEXT("format"), Out.Layers.Navmesh.Format, Error, false);
			Out.Layers.Navmesh.bPresent = true;
		}
		return true;
	}

	bool ParsePortals(const FJsonObjectPtr& Root, FGolmokZoneManifest& Out, FString& Error)
	{
		const FJsonArray* Portals = nullptr;
		if (!GetArray(Root, TEXT("portals"), Portals, Error))
		{
			return false;
		}
		for (const TSharedPtr<FJsonValue>& V : *Portals)
		{
			FJsonObjectPtr PortalObj, Pose;
			FGolmokZonePortal Portal;
			if (!ObjectOf(V, PortalObj, TEXT("portal"), Error) || !GetString(PortalObj, TEXT("id"), Portal.Id, Error)
				|| !GetString(PortalObj, TEXT("to_zone"), Portal.ToZone, Error) || !GetObject(PortalObj, TEXT("pose_enu"), Pose, Error)
				|| !GetVec3(Pose, TEXT("position"), Portal.PositionEnu, Error) || !GetNumber(Pose, TEXT("yaw_deg"), Portal.YawDeg, Error)
				|| !GetNumber(PortalObj, TEXT("radius_m"), Portal.RadiusM, Error) || !GetString(PortalObj, TEXT("kind"), Portal.Kind, Error))
			{
				return false;
			}
			if (Portal.ToZone == Out.ZoneId)
			{
				return Fail(Error, FString::Printf(TEXT("portal '%s' points at its own zone"), *Portal.Id));
			}
			Out.Portals.Add(MoveTemp(Portal));
		}
		return true;
	}

	bool ParseQuality(const FJsonObjectPtr& Root, FGolmokZoneManifest& Out, FString& Error)
	{
		FJsonObjectPtr Quality;
		if (!GetObject(Root, TEXT("quality"), Quality, Error))
		{
			return false;
		}
		// TryGetNumberField is false for null, so bHas* mirrors "present and not null".
		const FString KeyIcp(TEXT("icp_rmse_m"));
		const FString KeyIou(TEXT("footprint_iou"));
		Out.Quality.bHasIcpRmseM = Quality->TryGetNumberField(KeyIcp, Out.Quality.IcpRmseM);
		Out.Quality.bHasFootprintIou = Quality->TryGetNumberField(KeyIou, Out.Quality.FootprintIou);
		GetString(Quality, TEXT("reviewed_by"), Out.Quality.ReviewedBy, Error, false);
		GetString(Quality, TEXT("reviewed_at"), Out.Quality.ReviewedAt, Error, false);
		// Extra keys (spec allows them only here): keep as JSON text.
		TSharedPtr<FJsonObject> Extra = MakeShared<FJsonObject>();
		static const TCHAR* Known[] = {TEXT("icp_rmse_m"), TEXT("footprint_iou"), TEXT("reviewed_by"), TEXT("reviewed_at")};
		for (const auto& Pair : Quality->Values)
		{
			bool bKnown = false;
			for (const TCHAR* K : Known)
			{
				bKnown = bKnown || Pair.Key == K;
			}
			if (!bKnown)
			{
				Extra->SetField(Pair.Key, Pair.Value);
			}
		}
		if (Extra->Values.Num() > 0)
		{
			const TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
				TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Out.Quality.ExtraJson);
			FJsonSerializer::Serialize(Extra.ToSharedRef(), Writer);
		}
		return true;
	}
} // namespace

namespace GolmokZoneManifest
{
	bool IsSafeRelativeUri(const FString& Uri)
	{
		if (Uri.IsEmpty() || Uri.StartsWith(TEXT("/")) || Uri.Contains(TEXT("\\")) || Uri.Contains(TEXT("://")))
		{
			return false;
		}
		if (Uri.Len() >= 2 && FChar::IsAlpha(Uri[0]) && Uri[1] == TEXT(':'))
		{
			return false; // Windows drive
		}
		TArray<FString> Parts;
		Uri.ParseIntoArray(Parts, TEXT("/"), /*InCullEmpty*/ false);
		for (const FString& Part : Parts)
		{
			if (Part.IsEmpty() || Part == TEXT(".."))
			{
				return false;
			}
		}
		return true;
	}

	bool IsValidZoneId(const FString& ZoneId)
	{
		if (ZoneId.Len() > 64)
		{
			return false;
		}
		const FRegexPattern Pattern(TEXT("^z_[a-z0-9]+(_[a-z0-9]+)*$"));
		FRegexMatcher Matcher(Pattern, ZoneId);
		return Matcher.FindNext();
	}

	EGolmokVisualFormat ParseVisualFormat(const FString& Text)
	{
		if (Text == TEXT("nanite_mesh"))
		{
			return EGolmokVisualFormat::NaniteMesh;
		}
		if (Text == TEXT("splat_ply"))
		{
			return EGolmokVisualFormat::SplatPly;
		}
		if (Text == TEXT("splat_3dtiles"))
		{
			return EGolmokVisualFormat::Splat3DTiles;
		}
		if (Text == TEXT("splat_lcc"))
		{
			return EGolmokVisualFormat::SplatLcc;
		}
		return EGolmokVisualFormat::Unknown;
	}

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
		if (!GetString(Root, TEXT("zone_id"), Out.ZoneId, Error))
		{
			return false;
		}
		if (!IsValidZoneId(Out.ZoneId))
		{
			return Fail(Error, FString::Printf(TEXT("zone_id '%s' does not match ^z_[a-z0-9]+(_[a-z0-9]+)*$ (max 64)"), *Out.ZoneId));
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
		FString KindText;
		if (!GetString(Root, TEXT("kind"), KindText, Error))
		{
			return false;
		}
		if (KindText == TEXT("exterior"))
		{
			Out.Kind = EGolmokZoneKind::Exterior;
		}
		else if (KindText == TEXT("interior"))
		{
			Out.Kind = EGolmokZoneKind::Interior;
		}
		else
		{
			return Fail(Error, FString::Printf(TEXT("kind '%s' must be exterior|interior"), *KindText));
		}
		if (!Root->HasField(FString(TEXT("parent_zone"))))
		{
			return Fail(Error, TEXT("missing 'parent_zone' (null for exterior zones)"));
		}
		GetString(Root, TEXT("parent_zone"), Out.ParentZone, Error, false); // null -> empty
		if (Out.IsInterior() && Out.ParentZone.IsEmpty())
		{
			return Fail(Error, TEXT("interior zone needs a parent_zone"));
		}

		FJsonObjectPtr Origin;
		if (!GetObject(Root, TEXT("origin"), Origin, Error) || !GetNumber(Origin, TEXT("lat"), Out.OriginLat, Error)
			|| !GetNumber(Origin, TEXT("lon"), Out.OriginLon, Error) || !GetNumber(Origin, TEXT("height_ellipsoidal"), Out.OriginHeightEllipsoidal, Error))
		{
			return false;
		}
		if (!GetVec3(Root, TEXT("origin_ecef"), Out.OriginEcef, Error))
		{
			return false;
		}
		if (!ParseTransform(Root, Out, Error) || !ParseFootprint(Root, Out, Error))
		{
			return false;
		}

		FJsonObjectPtr Replaces;
		if (!GetObject(Root, TEXT("replaces"), Replaces, Error) || !GetStringArray(Replaces, TEXT("building_ids"), Out.Replaces.BuildingIds, Error)
			|| !GetBool(Replaces, TEXT("terrain_clip"), Out.Replaces.bTerrainClip, Error))
		{
			return false;
		}

		if (!ParseLayers(Root, Out, Error) || !ParsePortals(Root, Out, Error))
		{
			return false;
		}

		if (!GetNumber(Root, TEXT("priority"), Number, Error))
		{
			return false;
		}
		Out.Priority = static_cast<int32>(Number);

		if (!ParseQuality(Root, Out, Error))
		{
			return false;
		}

		FJsonObjectPtr Consent;
		if (!GetObject(Root, TEXT("consent"), Consent, Error) || !GetString(Consent, TEXT("type"), Out.Consent.Type, Error))
		{
			return false;
		}
		if (Out.Consent.Type != TEXT("public_street") && Out.Consent.Type != TEXT("owner_consent"))
		{
			return Fail(Error, FString::Printf(TEXT("consent.type '%s' must be public_street|owner_consent"), *Out.Consent.Type));
		}
		GetString(Consent, TEXT("record_id"), Out.Consent.RecordId, Error, false);
		if (Out.Consent.Type == TEXT("owner_consent") && Out.Consent.RecordId.IsEmpty())
		{
			UE_LOG(LogGolmok, Warning, TEXT("Zone manifest %s: owner_consent without record_id (required before publishing)."), *Out.ZoneId);
		}

		if (!GetStringArray(Root, TEXT("attribution"), Out.Attribution, Error))
		{
			return false;
		}
		const FJsonArray* Sources = nullptr;
		if (!GetArray(Root, TEXT("sources"), Sources, Error))
		{
			return false;
		}
		for (const TSharedPtr<FJsonValue>& V : *Sources)
		{
			FJsonObjectPtr SourceObj;
			FGolmokZoneSource Source;
			if (!ObjectOf(V, SourceObj, TEXT("source"), Error) || !GetString(SourceObj, TEXT("capture_id"), Source.CaptureId, Error))
			{
				return false;
			}
			GetString(SourceObj, TEXT("note"), Source.Note, Error, false);
			Out.Sources.Add(MoveTemp(Source));
		}

		static const TCHAR* KnownTopLevel[] = {TEXT("schema_version"), TEXT("zone_id"), TEXT("version"), TEXT("kind"), TEXT("parent_zone"),
			TEXT("origin"), TEXT("origin_ecef"), TEXT("transform"), TEXT("footprint_wgs84"), TEXT("replaces"), TEXT("layers"), TEXT("portals"),
			TEXT("priority"), TEXT("quality"), TEXT("consent"), TEXT("attribution"), TEXT("sources")};
		for (const auto& Pair : Root->Values)
		{
			bool bKnown = false;
			for (const TCHAR* K : KnownTopLevel)
			{
				bKnown = bKnown || Pair.Key == K;
			}
			if (!bKnown)
			{
				UE_LOG(LogGolmok, Warning, TEXT("Zone manifest %s: unknown top-level key '%s' (schema error for golmok-zone validate)."), *Out.ZoneId,
					*Pair.Key);
			}
		}
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
			FJsonObjectPtr PlaneObj;
			FGolmokBlockerPlane Plane;
			const FJsonArray* SizeArr = nullptr;
			TArray<double> Size;
			FString KindText;
			if (!ObjectOf(V, PlaneObj, TEXT("plane"), Error) || !GetString(PlaneObj, TEXT("id"), Plane.Id, Error)
				|| !GetVec3(PlaneObj, TEXT("center_enu"), Plane.CenterEnu, Error) || !GetVec3(PlaneObj, TEXT("normal_enu"), Plane.NormalEnu, Error)
				|| !GetArray(PlaneObj, TEXT("size_m"), SizeArr, Error) || !NumberArray(SizeArr, 2, Size, TEXT("size_m"), Error)
				|| !GetString(PlaneObj, TEXT("kind"), KindText, Error))
			{
				return false;
			}
			Plane.SizeM = FVector2D(Size[0], Size[1]);
			if (KindText == TEXT("glass"))
			{
				Plane.Kind = EGolmokBlockerKind::Glass;
			}
			else if (KindText == TEXT("no_entry"))
			{
				Plane.Kind = EGolmokBlockerKind::NoEntry;
			}
			else
			{
				return Fail(Error, FString::Printf(TEXT("plane '%s' kind '%s' must be glass|no_entry"), *Plane.Id, *KindText));
			}
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
		return FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Golmok"), TEXT("Zones"), ZoneId, FString::Printf(TEXT("v%d"), Version),
			TEXT("manifest.json"));
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

	FString SublevelPackagePath(const FString& ZoneId, int32 Version)
	{
		return FString::Printf(TEXT("%s/L_%s"), *AssetFolder(ZoneId, Version), *ZoneId);
	}
} // namespace GolmokZoneManifest
