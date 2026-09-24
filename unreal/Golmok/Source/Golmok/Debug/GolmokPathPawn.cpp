#include "Debug/GolmokPathPawn.h"

#include "Golmok.h"

#include "Camera/CameraComponent.h"
#include "Components/SphereComponent.h"
#include "Debug/GolmokDebugSubsystem.h"
#include "Engine/EngineTypes.h"
#include "GameFramework/PlayerController.h"

AGolmokPathPawn::AGolmokPathPawn()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = true;

	// Nothing may take this pawn over: no input, no auto possession, no AI controller.
	AutoPossessPlayer = EAutoReceiveInput::Disabled;
	AutoPossessAI = EAutoPossessAI::Disabled;
	AIControllerClass = nullptr;
	bUseControllerRotationPitch = false;
	bUseControllerRotationYaw = false;
	bUseControllerRotationRoll = false;

	// Pawn-typed overlap sphere: portal triggers (OverlapOnlyPawn, object type WorldDynamic) see it, nothing blocks it.
	Sphere = CreateDefaultSubobject<USphereComponent>(TEXT("PathSphere"));
	SetRootComponent(Sphere);
	Sphere->SetMobility(EComponentMobility::Movable);
	Sphere->SetSphereRadius(30.f);
	Sphere->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Sphere->SetCollisionObjectType(ECC_Pawn);
	Sphere->SetCollisionResponseToAllChannels(ECR_Ignore);
	Sphere->SetCollisionResponseToChannel(ECC_WorldDynamic, ECR_Overlap);
	Sphere->SetGenerateOverlapEvents(true);
	Sphere->SetHiddenInGame(true);
	Sphere->SetCanEverAffectNavigation(false);

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("PathCamera"));
	Camera->SetupAttachment(Sphere);
	Camera->bUsePawnControlRotation = false;
}

void AGolmokPathPawn::Init(UGolmokDebugSubsystem* InOwner, GolmokStatsMath::CameraPath InPath, float Fov)
{
	OwnerSubsystem = InOwner;
	Path = MoveTemp(InPath);
	Elapsed = 0.0;
	Cursor = 0;
	bFirstTick = true;
	bFinished = false;
	if (Camera)
	{
		Camera->SetFieldOfView(Fov);
	}
	if (!Path.Samples.empty())
	{
		ApplyPose(Path.Samples.front(), Path.Samples.front(), 0.0);
	}
}

void AGolmokPathPawn::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	if (bFirstTick)
	{
		// The camera is in place now: a --csv capture starts here, not in StartPlayback.
		bFirstTick = false;
		if (OwnerSubsystem.IsValid())
		{
			OwnerSubsystem->BeginCsv();
		}
	}
	if (bFinished)
	{
		return;
	}

	const std::vector<GolmokStatsMath::PoseSample>& Samples = Path.Samples;
	if (Samples.empty())
	{
		bFinished = true;
		if (OwnerSubsystem.IsValid())
		{
			OwnerSubsystem->OnPlaybackFinished(this);
		}
		return;
	}

	Elapsed += static_cast<double>(DeltaSeconds);
	const double Duration = Path.Duration();
	if (Elapsed >= Duration)
	{
		Elapsed = Duration;
		ApplyPose(Samples.back(), Samples.back(), 0.0);
		bFinished = true;
		if (OwnerSubsystem.IsValid())
		{
			OwnerSubsystem->OnPlaybackFinished(this);
		}
		return;
	}

	// Advance the segment cursor monotonically: Samples[Cursor].T <= Elapsed < Samples[Cursor + 1].T (t is monotonic).
	while (Cursor + 1 < Samples.size() && Samples[Cursor + 1].T <= Elapsed)
	{
		++Cursor;
	}
	const GolmokStatsMath::PoseSample& A = Samples[Cursor];
	if (Cursor + 1 >= Samples.size())
	{
		ApplyPose(A, A, 0.0);
		return;
	}
	const GolmokStatsMath::PoseSample& B = Samples[Cursor + 1];
	const double Span = B.T - A.T;
	// Before the first sample (A.T > Elapsed) U clamps to 0: the pawn waits at the first pose.
	const double U = Span > 0.0 ? FMath::Clamp((Elapsed - A.T) / Span, 0.0, 1.0) : 1.0;
	ApplyPose(A, B, U);
}

void AGolmokPathPawn::ApplyPose(const GolmokStatsMath::PoseSample& A, const GolmokStatsMath::PoseSample& B, double U)
{
	const FVector LocationA(A.P[0], A.P[1], A.P[2]);
	const FVector LocationB(B.P[0], B.P[1], B.P[2]);
	const FQuat RotationA = FRotator(A.R[0], A.R[1], A.R[2]).Quaternion();
	const FQuat RotationB = FRotator(B.R[0], B.R[1], B.R[2]).Quaternion();
	const FVector Location = FMath::Lerp(LocationA, LocationB, U);
	const FRotator Rotation = FQuat::Slerp(RotationA, RotationB, U).Rotator();

	SetActorLocationAndRotation(Location, Rotation, /*bSweep*/ false, /*OutSweepHitResult*/ nullptr, ETeleportType::TeleportPhysics);
	if (APlayerController* PC = Cast<APlayerController>(GetController()))
	{
		PC->SetControlRotation(Rotation);
	}
}
