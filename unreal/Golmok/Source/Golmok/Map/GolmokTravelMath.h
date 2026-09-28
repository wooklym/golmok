#pragma once

// Pure, header-only math and decisions for WP-15a zone travel and saves. No Unreal headers on purpose:
// tools/tests/test_ue_travel_math.py compiles this file with g++ and cross-checks it against numpy /
// golmok_tools.zone.transform, so the spawn conversion, the yaw sign and the restore rules are verified in cloud CI
// without an engine. Map/GolmokTravelSubsystem, Save/GolmokSaveSubsystem and AGolmokZone::GetSpawnUE call it.
//
// Conventions (docs/spec/zone-manifest.md §1, §5; same as Geo/GolmokGeoMath.h):
//   ENU      x=east, y=north, z=up, meters. zone-local = ENU at the zone origin.
//   UE       X=east, Y=south, Z=up, centimeters: UE = (100 x, -100 y, 100 z).
//   Mat4     4x4 row-major M[r*4+c], points are columns (p' = M p). ActorUE = the zone root actor transform in UE
//            cm (S * M * S^-1 of the zone-local -> area ENU matrix), the same matrix GolmokGeoMath::UEActorMatrix returns.
//   yaw_deg  counter-clockwise from +x (east) seen from above. UE Yaw = -yaw_deg.
// All values are double.

#include <array>
#include <cmath>
#include <cstddef>

namespace GolmokTravelMath
{
	using Vec3 = std::array<double, 3>;
	using Mat4 = std::array<double, 16>;

	// Named Pi, not the upper-case spelling: Unreal defines that as a preprocessor macro.
	constexpr double Pi = 3.14159265358979323846;
	constexpr double EnuToUEScale = 100.0; // m -> cm

	/** Spec §1 fallback: the ground probe starts this far above zone-local (0,0,0) ... */
	constexpr double FallbackTraceUpCm = 300.0;
	/** ... and ends this far below it (a zone floor is never that deep under its origin). */
	constexpr double FallbackTraceDownCm = 5000.0;
	/** Gap between the capsule bottom and the ground at arrival (no sweep: never start inside the floor). */
	constexpr double ArrivalClearanceCm = 2.0;

	inline double DegToRad(double Deg) { return Deg * (Pi / 180.0); }
	inline double RadToDeg(double Rad) { return Rad * (180.0 / Pi); }

	/** Degrees -> (-180, 180]. */
	inline double NormalizeYawDeg(double Deg)
	{
		double D = std::fmod(Deg, 360.0);
		if (D <= -180.0)
		{
			D += 360.0;
		}
		else if (D > 180.0)
		{
			D -= 360.0;
		}
		return D;
	}

	inline Vec3 EnuToUE(const Vec3& Enu) { return Vec3{Enu[0] * EnuToUEScale, -Enu[1] * EnuToUEScale, Enu[2] * EnuToUEScale}; }
	inline Vec3 UEToEnu(const Vec3& UE) { return Vec3{UE[0] / EnuToUEScale, -UE[1] / EnuToUEScale, UE[2] / EnuToUEScale}; }

	inline Vec3 ApplyPoint(const Mat4& M, const Vec3& P)
	{
		return Vec3{M[0] * P[0] + M[1] * P[1] + M[2] * P[2] + M[3], M[4] * P[0] + M[5] * P[1] + M[6] * P[2] + M[7],
			M[8] * P[0] + M[9] * P[1] + M[10] * P[2] + M[11]};
	}

	inline Vec3 ApplyVector(const Mat4& M, const Vec3& V)
	{
		return Vec3{M[0] * V[0] + M[1] * V[1] + M[2] * V[2], M[4] * V[0] + M[5] * V[1] + M[6] * V[2], M[8] * V[0] + M[9] * V[1] + M[10] * V[2]};
	}

	/** manifest spawn.position_enu (zone-local m) -> level UE (cm): ActorUE * (100x, -100y, 100z). The feet point. */
	inline Vec3 SpawnFeetUE(const Mat4& ActorUE, const Vec3& SpawnEnu) { return ApplyPoint(ActorUE, EnuToUE(SpawnEnu)); }

	/**
	 * manifest spawn.yaw_deg (zone-local, CCW from east) -> UE Yaw (deg) in the level: the zone-local facing direction
	 * (cos, sin, 0) in UE is (cos, -sin, 0) (relative UE Yaw = -yaw_deg), turned by the root actor; the yaw is the
	 * heading of that vector (a tilted root only changes its length in XY).
	 */
	inline double SpawnYawUE(const Mat4& ActorUE, double YawDegEnu)
	{
		const double R = DegToRad(YawDegEnu);
		const Vec3 F = ApplyVector(ActorUE, Vec3{std::cos(R), -std::sin(R), 0.0});
		return NormalizeYawDeg(RadToDeg(std::atan2(F[1], F[0])));
	}

	/** Spec §1 fallback probe: from zone-local (0, 0, +3 m) straight down (level -Z) FallbackTraceUpCm + FallbackTraceDownCm. */
	inline void FallbackTrace(const Mat4& ActorUE, Vec3& OutStart, Vec3& OutEnd)
	{
		const Vec3 Origin = ApplyPoint(ActorUE, Vec3{0.0, 0.0, 0.0});
		OutStart = Vec3{Origin[0], Origin[1], Origin[2] + FallbackTraceUpCm};
		OutEnd = Vec3{Origin[0], Origin[1], Origin[2] - FallbackTraceDownCm};
	}

	/** Fallback feet point: the probe's hit, else zone-local (0,0,0) itself (no collision loaded yet). */
	inline Vec3 FallbackFeetUE(const Mat4& ActorUE, bool bHit, const Vec3& HitUE)
	{
		return bHit ? HitUE : ApplyPoint(ActorUE, Vec3{0.0, 0.0, 0.0});
	}

	/** Actor (capsule center) location for a feet point: + half height + ArrivalClearanceCm. */
	inline Vec3 StandingLocationUE(const Vec3& FeetUE, double CapsuleHalfHeightCm)
	{
		return Vec3{FeetUE[0], FeetUE[1], FeetUE[2] + CapsuleHalfHeightCm + ArrivalClearanceCm};
	}

	/** Saves keep the ENU heading (area frame), never a UE yaw: EnuYaw = -UEYaw, both normalized. */
	inline double UEYawToEnuYaw(double UEYawDeg) { return NormalizeYawDeg(-UEYawDeg); }
	inline double EnuYawToUEYaw(double EnuYawDeg) { return NormalizeYawDeg(-EnuYawDeg); }

	/** Horizontal distance (m) between two level UE points (cm). */
	inline double HorizontalDistanceM(const Vec3& A, const Vec3& B)
	{
		const double Dx = A[0] - B[0];
		const double Dy = A[1] - B[1];
		return std::sqrt(Dx * Dx + Dy * Dy) / EnuToUEScale;
	}

	// ---- travel request gate (spec §2 ①) ---------------------------------------------------------------------------

	enum class ERefusal : int
	{
		None = 0,
		AlreadyTraveling = 1,
		PhotoMode = 2,
		PortalBusy = 3,
		UnknownZone = 4,
		OtherRegion = 5,
		NoPlayer = 6
	};

	/** First reason a travel request is refused, in the order the subsystem checks them. */
	inline ERefusal CheckTravel(bool bTraveling, bool bPhotoActive, bool bPortalBusy, bool bZoneKnown, bool bHasPlayer, double RegionDistanceKm,
		double MaxRegionDistanceKm)
	{
		if (bTraveling)
		{
			return ERefusal::AlreadyTraveling;
		}
		if (bPhotoActive)
		{
			return ERefusal::PhotoMode;
		}
		if (bPortalBusy)
		{
			return ERefusal::PortalBusy;
		}
		if (!bZoneKnown)
		{
			return ERefusal::UnknownZone;
		}
		if (MaxRegionDistanceKm > 0.0 && RegionDistanceKm > MaxRegionDistanceKm)
		{
			return ERefusal::OtherRegion;
		}
		if (!bHasPlayer)
		{
			return ERefusal::NoPlayer;
		}
		return ERefusal::None;
	}

	inline const char* RefusalName(ERefusal R)
	{
		switch (R)
		{
		case ERefusal::AlreadyTraveling:
			return "already traveling";
		case ERefusal::PhotoMode:
			return "photo mode is active";
		case ERefusal::PortalBusy:
			return "a portal transition / interior is active";
		case ERefusal::UnknownZone:
			return "zone is not in the index or the level";
		case ERefusal::OtherRegion:
			return "zone is in another region (not supported in 15a)";
		case ERefusal::NoPlayer:
			return "no player pawn";
		case ERefusal::None:
		default:
			return "ok";
		}
	}

	/** Poll verdict while waiting for the target zone (spec §2 ④): keep waiting, arrive, or fail on timeout / load failure. */
	enum class EPoll : int
	{
		Wait = 0,
		Arrive = 1,
		TimedOut = 2,
		LoadFailed = 3
	};

	inline EPoll PollTravel(bool bZoneLoaded, bool bZoneFailed, double ElapsedSeconds, double FadeSeconds, double TimeoutSeconds)
	{
		if (bZoneFailed)
		{
			return EPoll::LoadFailed;
		}
		if (bZoneLoaded && ElapsedSeconds >= FadeSeconds)
		{
			return EPoll::Arrive;
		}
		if (ElapsedSeconds >= TimeoutSeconds)
		{
			return EPoll::TimedOut;
		}
		return EPoll::Wait;
	}

	// ---- save restore rules (spec §3 ①②③) -------------------------------------------------------------------------

	enum class ERestore : int
	{
		None = 0,             // ③ nothing usable (or no save): keep the PlayerStart
		SavedPosition = 1,    // ① same zone and version (or no zone: basemap position)
		SavedZoneSpawn = 2,   // ② the saved zone exists with another version: its spawn
		HomeZoneSpawn = 3     // ② the saved zone is gone: HomeZoneId's spawn
	};

	/**
	 * bHasSave: a readable slot. SavedZoneId empty = the player stood on the basemap (no zone): the position is restored
	 * when bHasPosition. IndexVersion = the version the level / index resolves for SavedZoneId now (0 = unknown).
	 * bHomeKnown = HomeZoneId is set and resolvable.
	 */
	inline ERestore DecideRestore(bool bHasSave, bool bHasPosition, bool bSavedZoneEmpty, int SavedVersion, int IndexVersion, bool bHomeKnown)
	{
		if (!bHasSave)
		{
			return ERestore::None;
		}
		if (bSavedZoneEmpty)
		{
			return bHasPosition ? ERestore::SavedPosition : (bHomeKnown ? ERestore::HomeZoneSpawn : ERestore::None);
		}
		if (IndexVersion > 0 && IndexVersion == SavedVersion && bHasPosition)
		{
			return ERestore::SavedPosition;
		}
		if (IndexVersion > 0)
		{
			return ERestore::SavedZoneSpawn;
		}
		return bHomeKnown ? ERestore::HomeZoneSpawn : ERestore::None;
	}

	inline const char* RestoreName(ERestore R)
	{
		switch (R)
		{
		case ERestore::SavedPosition:
			return "saved position";
		case ERestore::SavedZoneSpawn:
			return "saved zone spawn (version changed)";
		case ERestore::HomeZoneSpawn:
			return "home zone spawn";
		case ERestore::None:
		default:
			return "none";
		}
	}

	/**
	 * Periodic autosave (spec §3, every AutosaveIntervalSeconds, only when something changed): a pending event (visit /
	 * photo / travel), or the player moved more than MoveThresholdM / turned more than TurnThresholdDeg since the last save.
	 */
	inline bool ShouldAutosave(double NowSeconds, double LastSaveSeconds, double IntervalSeconds, bool bDirty, double MovedM, double TurnedDeg,
		double MoveThresholdM = 1.0, double TurnThresholdDeg = 10.0)
	{
		if (IntervalSeconds <= 0.0 || NowSeconds - LastSaveSeconds < IntervalSeconds)
		{
			return false;
		}
		return bDirty || MovedM > MoveThresholdM || std::fabs(NormalizeYawDeg(TurnedDeg)) > TurnThresholdDeg;
	}
} // namespace GolmokTravelMath
