#include "Photo/GolmokPhotoCameraPawn.h"

#include "Golmok.h"

#include "Camera/CameraComponent.h"
#include "Components/SphereComponent.h"
#include "Engine/EngineTypes.h"
#include "Engine/Scene.h"
#include "Misc/App.h"
#include "Photo/GolmokPhotoMath.h"
#include "Photo/GolmokPhotoModeSubsystem.h"

namespace
{
	// Design section 5-2 (the subsystem keeps the same numbers as private constants; the pawn cannot read those).
	constexpr float PhotoMouseLookDegPerUnit = 0.5f;
	constexpr float PhotoPadLookDegPerSec = 120.f;
	constexpr float PhotoFastMultiplier = 3.f;
	constexpr float PhotoPitchLimitDeg = 89.f;
	/** Upper bound of the per-tick dt: FApp::GetDeltaTime() spikes after a hitch (design section 10 #2). */
	constexpr float PhotoMaxTickDt = 0.1f;
	/** Retreat toward the anchor when a sweep starts penetrating (design section 6-3). */
	constexpr float PhotoPenetrationRetreatCm = 10.f;
} // namespace

AGolmokPhotoCameraPawn::AGolmokPhotoCameraPawn()
{
	// Ticks while the game is paused: photo mode pauses the world and this pawn is the only thing that moves.
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = true;
	PrimaryActorTick.bTickEvenWhenPaused = true;

	// Never possessed (design section 0 #1): no input, no auto possession, no AI controller.
	AutoPossessPlayer = EAutoReceiveInput::Disabled;
	AutoPossessAI = EAutoPossessAI::Disabled;
	AIControllerClass = nullptr;
	bUseControllerRotationPitch = false;
	bUseControllerRotationYaw = false;
	bUseControllerRotationRoll = false;

	// Sweep sphere (design section 6-3): blocks against level geometry (zone collision meshes and blockers are
	// BlockAll), ignores pawns, camera probes and visibility traces, raises no overlap events. Radius set in Init.
	Sphere = CreateDefaultSubobject<USphereComponent>(TEXT("PhotoSphere"));
	SetRootComponent(Sphere);
	Sphere->SetMobility(EComponentMobility::Movable);
	Sphere->SetSphereRadius(RadiusCm);
	Sphere->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Sphere->SetCollisionObjectType(ECC_WorldDynamic);
	Sphere->SetCollisionResponseToAllChannels(ECR_Ignore);
	Sphere->SetCollisionResponseToChannel(ECC_WorldStatic, ECR_Block);
	Sphere->SetCollisionResponseToChannel(ECC_WorldDynamic, ECR_Block);
	Sphere->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
	Sphere->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
	Sphere->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
	Sphere->SetGenerateOverlapEvents(false);
	Sphere->SetHiddenInGame(true);
	Sphere->SetCanEverAffectNavigation(false);

	// View target without possession: APawn::CalcCamera finds this component (bFindCameraComponentWhenViewTarget
	// stays at its default true, design section 10 #17). All optics overrides live here (PostProcessBlendWeight 1).
	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("PhotoCamera"));
	Camera->SetupAttachment(Sphere);
	Camera->bUsePawnControlRotation = false;
	Camera->PostProcessBlendWeight = 1.f;
}

void AGolmokPhotoCameraPawn::Init(UGolmokPhotoModeSubsystem* InOwner, const FVector& InLocation, const FRotator& InLookRotation, float InFov, float InRadiusCm)
{
	Owner = InOwner;
	RadiusCm = FMath::Max(InRadiusCm, 1.f);
	if (Sphere)
	{
		Sphere->SetSphereRadius(RadiusCm);
	}

	MoveInput = FVector2D::ZeroVector;
	UpDownInput = 0.f;
	MouseDelta = FVector2D::ZeroVector;
	PadStick = FVector2D::ZeroVector;
	bFast = false;
	RollDeg = 0.f;
	TickCount = 0;

	SetActorLocation(InLocation, /*bSweep*/ false, /*OutSweepHitResult*/ nullptr, ETeleportType::TeleportPhysics);
	// Roll starts at 0 (design section 4-2 step 3); ApplyLook clamps the pitch and writes the actor rotation.
	ApplyLook(FRotator(InLookRotation.Pitch, InLookRotation.Yaw, 0.f));
	if (Camera)
	{
		Camera->SetFieldOfView(InFov);
	}
}

void AGolmokPhotoCameraPawn::SetMoveInput(const FVector2D& InLocal)
{
	MoveInput = InLocal;
}

void AGolmokPhotoCameraPawn::SetUpDownInput(float InAxis)
{
	UpDownInput = InAxis;
}

void AGolmokPhotoCameraPawn::AddLookMouse(const FVector2D& InDelta)
{
	MouseDelta += InDelta;
}

void AGolmokPhotoCameraPawn::SetLookPad(const FVector2D& InStick)
{
	PadStick = InStick;
}

void AGolmokPhotoCameraPawn::SetFast(bool bInFast)
{
	bFast = bInFast;
}

void AGolmokPhotoCameraPawn::ApplyLook(const FRotator& InLook)
{
	Look.Pitch = FMath::Clamp(InLook.Pitch, -PhotoPitchLimitDeg, PhotoPitchLimitDeg);
	Look.Yaw = FRotator::NormalizeAxis(InLook.Yaw);
	Look.Roll = 0.f;
	// Pitch / yaw on the actor, roll on the camera component only (design section 6-4).
	SetActorRotation(Look, ETeleportType::TeleportPhysics);
	if (Camera)
	{
		Camera->SetRelativeRotation(FRotator(0.f, 0.f, RollDeg));
	}
}

void AGolmokPhotoCameraPawn::ApplyOptics(float InFov, double InExposureBias, bool bInDof, double InFocusM, double InFstop)
{
	if (!Camera)
	{
		return;
	}
	Camera->SetFieldOfView(InFov);
	// Camera overrides REPLACE the post-process volume values (design section 10 #9): the subsystem passes the
	// preset's base bias plus the relative EV. Focal distance 0 = DOF off; motion blur 0 for shots right after a move.
	FPostProcessSettings& Settings = Camera->PostProcessSettings;
	Settings.bOverride_AutoExposureBias = true;
	Settings.AutoExposureBias = static_cast<float>(InExposureBias);
	Settings.bOverride_DepthOfFieldFocalDistance = true;
	Settings.DepthOfFieldFocalDistance = bInDof ? static_cast<float>(InFocusM * 100.0) : 0.f;
	Settings.bOverride_DepthOfFieldFstop = true;
	Settings.DepthOfFieldFstop = static_cast<float>(InFstop);
	Settings.bOverride_MotionBlurAmount = true;
	Settings.MotionBlurAmount = 0.f;
	Camera->PostProcessBlendWeight = 1.f;
}

void AGolmokPhotoCameraPawn::SetRoll(float InRollDeg)
{
	RollDeg = InRollDeg;
	if (Camera)
	{
		Camera->SetRelativeRotation(FRotator(0.f, 0.f, RollDeg));
	}
}

void AGolmokPhotoCameraPawn::MoveConstrained(const FVector& InDesired)
{
	UGolmokPhotoModeSubsystem* LocalOwner = Owner.Get();
	if (!LocalOwner)
	{
		return;
	}
	const FVector Anchor = LocalOwner->GetAnchor();
	const TArray<double>& Xs = LocalOwner->GetFootprintXs();
	const TArray<double>& Ys = LocalOwner->GetFootprintYs();

	GolmokPhotoMath::Constraint LocalConstraint;
	LocalConstraint.Anchor = {Anchor.X, Anchor.Y, Anchor.Z};
	LocalConstraint.RadiusCm = static_cast<double>(LocalOwner->MaxDistanceM) * 100.0;
	LocalConstraint.InsetCm = static_cast<double>(LocalOwner->FootprintMarginM) * 100.0;
	if (Xs.Num() >= 3 && Xs.Num() == Ys.Num())
	{
		LocalConstraint.Xs = Xs.GetData();
		LocalConstraint.Ys = Ys.GetData();
		LocalConstraint.N = static_cast<std::size_t>(Xs.Num());
	}

	// Sphere -> footprint polygon -> re-check; -1 cancels the move (the previous position satisfies both).
	const GolmokPhotoMath::Vec3 Desired = {InDesired.X, InDesired.Y, InDesired.Z};
	GolmokPhotoMath::Vec3 Accepted = {};
	if (GolmokPhotoMath::Constrain(LocalConstraint, Desired, Accepted) < 0)
	{
		return;
	}

	// One blocking sweep, stop at the first hit (no slide, design section 6-3 / section 10 #16).
	FHitResult Hit;
	SetActorLocation(FVector(Accepted[0], Accepted[1], Accepted[2]), /*bSweep*/ true, &Hit);
	if (Hit.bStartPenetrating)
	{
		// Already inside geometry (a mesh seam): back off toward the anchor, which is always in free space.
		const FVector Location = GetActorLocation();
		const FVector Retreat = (Anchor - Location).GetSafeNormal() * PhotoPenetrationRetreatCm;
		SetActorLocation(Location + Retreat, /*bSweep*/ true);
	}
}

void AGolmokPhotoCameraPawn::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	// Counts every tick, paused or not: Golmok.Photo.EnterExit proves the paused tick with it.
	++TickCount;

	UGolmokPhotoModeSubsystem* LocalOwner = Owner.Get();
	if (!LocalOwner || LocalOwner->IsCapturing())
	{
		// Input frozen during the capture window: drop the mouse delta so it does not jump afterwards.
		MouseDelta = FVector2D::ZeroVector;
		return;
	}

	// DeltaSeconds is 0 (or meaningless) while the game is paused; the application delta is real time.
	const float LocalDt = FMath::Clamp(static_cast<float>(FApp::GetDeltaTime()), 0.f, PhotoMaxTickDt);

	// Look: mouse per unit, pad per second.
	FRotator NewLook = Look;
	NewLook.Yaw += MouseDelta.X * PhotoMouseLookDegPerUnit + PadStick.X * PhotoPadLookDegPerSec * LocalDt;
	NewLook.Pitch = FMath::Clamp(
		NewLook.Pitch - MouseDelta.Y * PhotoMouseLookDegPerUnit - PadStick.Y * PhotoPadLookDegPerSec * LocalDt,
		-PhotoPitchLimitDeg, PhotoPitchLimitDeg);
	MouseDelta = FVector2D::ZeroVector;
	ApplyLook(NewLook);

	// Move: forward includes the pitch, right is yaw only, up is world up; unit direction times the owner's speed.
	const FVector Forward = Look.Vector();
	const FVector Right = FRotator(0.f, Look.Yaw, 0.f).RotateVector(FVector::RightVector);
	const FVector Direction =
		(Forward * MoveInput.Y + Right * MoveInput.X + FVector::UpVector * UpDownInput).GetClampedToMaxSize(1.0);
	if (Direction.IsNearlyZero())
	{
		// No input: nothing to constrain or sweep this tick.
		return;
	}
	const float SpeedCmPerSec = LocalOwner->MoveSpeedMps * 100.f * (bFast ? PhotoFastMultiplier : 1.f);
	MoveConstrained(GetActorLocation() + Direction * (SpeedCmPerSec * LocalDt));
}

void AGolmokPhotoCameraPawn::EndPlay(const EEndPlayReason::Type Reason)
{
	// Always: the subsystem tells a normal Exit (Destroyed, world alive) from a dead-world teardown apart, and ignores
	// the call while it is destroying us itself (State == Exiting).
	if (UGolmokPhotoModeSubsystem* LocalOwner = Owner.Get())
	{
		LocalOwner->OnPhotoPawnEndPlay(this, Reason);
	}
	Owner.Reset();
	Super::EndPlay(Reason);
}
