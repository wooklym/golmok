#pragma once

#include "CoreMinimal.h"
#include "Debug/GolmokStatsMath.h"
#include "GameFramework/Pawn.h"
#include "GolmokPathPawn.generated.h"

class UCameraComponent;
class UGolmokDebugSubsystem;
class USphereComponent;

/**
 * Camera pawn that replays a recorded camera path (WP-05 design section 4-5). UGolmokDebugSubsystem::StartPlayback
 * spawns one at the first sample, possesses it with the player controller and makes it the view target; the
 * original character stays where it is (hidden, collision kept).
 *
 * The root is a small pawn-typed overlap sphere, so portal triggers (OverlapOnlyPawn) and the zone subsystem's
 * player distance follow the path exactly as they would follow the player: a --csv playback reproduces the interior
 * load and lighting spikes. Tick interpolates between samples (position lerp, rotation FQuat::Slerp) and calls
 * BeginCsv() on its first tick and OnPlaybackFinished() at the last sample.
 */
UCLASS(NotPlaceable, NotBlueprintable)
class GOLMOK_API AGolmokPathPawn : public APawn
{
	GENERATED_BODY()

public:
	AGolmokPathPawn();

	/** Takes the path (moved in), sets the camera FOV and rewinds to t = 0. */
	void Init(UGolmokDebugSubsystem* InOwner, GolmokStatsMath::CameraPath InPath, float Fov);

	/** Playback time in seconds since Init (clamped to the duration once finished). */
	double GetElapsed() const { return Elapsed; }

	/** t of the last sample (0 for an empty path). */
	double GetDuration() const { return Path.Duration(); }

	const GolmokStatsMath::CameraPath& GetPath() const { return Path; }
	bool IsFinished() const { return bFinished; }

	virtual void Tick(float DeltaSeconds) override;

private:
	/** Position lerp + FQuat::Slerp between A and B at U in [0, 1], then SetActorLocationAndRotation + control rotation. */
	void ApplyPose(const GolmokStatsMath::PoseSample& A, const GolmokStatsMath::PoseSample& B, double U);

	UPROPERTY(VisibleAnywhere, Category = "Golmok|Debug")
	TObjectPtr<USphereComponent> Sphere;

	UPROPERTY(VisibleAnywhere, Category = "Golmok|Debug")
	TObjectPtr<UCameraComponent> Camera;

	TWeakObjectPtr<UGolmokDebugSubsystem> OwnerSubsystem;
	GolmokStatsMath::CameraPath Path;
	double Elapsed = 0.0;
	/** Index of the segment start sample; only moves forward. */
	std::size_t Cursor = 0;
	bool bFirstTick = true;
	bool bFinished = false;
};
