#include "Audio/GolmokFootstepComponent.h"

#include "Audio/GolmokAmbienceSubsystem.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Photo/GolmokPhotoModeSubsystem.h"
#include "PhysicsEngine/PhysicsSettings.h"
#include "Player/GolmokCharacter.h"

UGolmokFootstepComponent::UGolmokFootstepComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

void UGolmokFootstepComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	AGolmokCharacter* Character = Cast<AGolmokCharacter>(GetOwner());
	UGolmokAmbienceSubsystem* Audio = GetWorld() ? GetWorld()->GetSubsystem<UGolmokAmbienceSubsystem>() : nullptr;
	APlayerController* PC = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
	if (!Character || !Audio || !PC || PC->GetPawn() != Character || UGolmokPhotoModeSubsystem::IsActiveIn(GetWorld()))
	{ Stepper.Reset(); bHasPrevious = false; return; }
	const FVector Position = Character->GetActorLocation();
	const double Distance = bHasPrevious ? FVector::Dist2D(Position, Previous) : 0.0;
	Previous = Position; bHasPrevious = true;
	const FGolmokAudioConfig& Config = Audio->GetConfig();
	const double Stride = Character->GetVelocity().Size2D() >= Config.RunThreshold ? Config.RunStride : Config.WalkStride;
	const auto Result = Stepper.Advance(Distance, Character->GetCharacterMovement()->IsMovingOnGround(), true, Stride, Config.TeleportLimit);
	if (Result.Landed) TriggerFootstep(true);
	// Avoid an audible burst after a slow frame; residual distance is still consumed by the stepper.
	if (Result.Steps > 0) TriggerFootstep(false);
}

void UGolmokFootstepComponent::TriggerFootstep(bool bLanding)
{
	AGolmokCharacter* Character = Cast<AGolmokCharacter>(GetOwner());
	UGolmokAmbienceSubsystem* Audio = GetWorld() ? GetWorld()->GetSubsystem<UGolmokAmbienceSubsystem>() : nullptr;
	if (!Character || !Audio) return;
	FHitResult Hit;
	const FVector Start = Character->GetActorLocation();
	const FVector End = Start - FVector(0, 0, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 30.f);
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GolmokAudioFloor), true, Character);
	Params.bReturnPhysicalMaterial = true;
	FString Set = TEXT("default");
	FVector Point = End;
	if (GetWorld()->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params))
	{
		Point = Hit.ImpactPoint;
		Set = ResolveSurfaceSet(Audio->GetConfig(), static_cast<int32>(UGameplayStatics::GetSurfaceType(Hit)),
			Hit.GetActor() && Hit.GetActor()->ActorHasTag(TEXT("Course/Stairs")));
	}
	Audio->PlayFootstep(Set, bLanding, Point);
}

FString UGolmokFootstepComponent::ResolveSurfaceSet(const FGolmokAudioConfig& Config, int32 Surface, bool bStairs)
{
	// SurfaceType numbers alone do not define an authored physical surface in this project.
	const bool bNamed = Surface == 0 || GetDefault<UPhysicsSettings>()->PhysicalSurfaces.ContainsByPredicate(
		[Surface](const FPhysicalSurfaceName& Entry) { return static_cast<int32>(Entry.Type) == Surface && !Entry.Name.IsNone(); });
	const FString* Mapped = bNamed ? Config.Surfaces.Find(Surface) : nullptr;
	const auto Choice = GolmokAudioMath::ChooseSurface(Mapped != nullptr, bStairs);
	if (Choice == GolmokAudioMath::SurfaceChoice::StairsTag) return TEXT("stairs");
	return Choice == GolmokAudioMath::SurfaceChoice::PhysicalMaterial ? *Mapped : FString(TEXT("default"));
}
