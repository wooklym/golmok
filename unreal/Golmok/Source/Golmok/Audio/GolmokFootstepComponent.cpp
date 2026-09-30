#include "Audio/GolmokFootstepComponent.h"

#include "Audio/GolmokAmbienceSubsystem.h"
#include "Animation/GolmokGaspCharacter.h"
#include "Animation/GolmokAnimationConfig.h"
#include "Animation/GolmokLocomotionStateComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Characters/GolmokCharacterSubsystem.h"
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

void UGolmokFootstepComponent::OnRegister()
{
	Super::OnRegister();
	bAnimClassCached = false; CachedAnimClass.Reset();
	RefreshFootEventBinding();
}

void UGolmokFootstepComponent::OnUnregister()
{
	if (auto* Provider = FootEvents.Get()) Provider->OnFootEvent.Remove(FootEventHandle);
	FootEvents.Reset(); FootEventHandle.Reset();
	Stepper.Reset(); bHasPrevious = false;
	Super::OnUnregister();
}

void UGolmokFootstepComponent::RefreshFootEventBinding()
{
	auto* Provider = GetOwner() ? GetOwner()->FindComponentByClass<UGolmokLocomotionStateComponent>() : nullptr;
	if (Provider == FootEvents.Get()) return;
	if (auto* Old = FootEvents.Get()) Old->OnFootEvent.Remove(FootEventHandle);
	FootEvents = Provider; FootEventHandle.Reset();
	if (Provider) FootEventHandle = Provider->OnFootEvent.AddUObject(this, &UGolmokFootstepComponent::OnFootEvent);
	Stepper.Reset(); bHasPrevious = false;
}

bool UGolmokFootstepComponent::UsesNotifyDriver() const
{
	const auto* Audio = GetWorld() ? GetWorld()->GetSubsystem<UGolmokAmbienceSubsystem>() : nullptr;
	if (!Audio) return false;
	const FString& Driver = Audio->GetConfig().FootstepDriver;
	if (Driver == TEXT("notify")) return true;
	const auto* Pawn = Cast<AGolmokGaspCharacter>(GetOwner());
	if (Driver != TEXT("auto") || !Pawn) return false;
	const UClass* AnimClass = Pawn->GetMesh() ? Pawn->GetMesh()->GetAnimClass() : nullptr;
	if (!AnimClass)
	{
		CachedAnimClass.Reset(); bAnimClassCached = true; bCachedRequiresGasp = false;
		return false;
	}
	const uint32 Generation = GolmokAnimation::GetModeSourceGeneration();
	if (!bAnimClassCached || CachedAnimClass.Get() != AnimClass || CachedModeGeneration != Generation)
	{
		CachedAnimClass = AnimClass;
		CachedModeGeneration = Generation;
#if WITH_DEV_AUTOMATION_TESTS
		++AnimContractEvaluations;
#endif
		bCachedRequiresGasp = AnimClass && GolmokAnimation::RequiresGaspPawn(AnimClass);
		bAnimClassCached = true;
	}
	return bCachedRequiresGasp;
}

bool UGolmokFootstepComponent::IsActivePlayer() const
{
	const auto* PC = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
	return PC && PC->GetPawn() == GetOwner() && !UGameplayStatics::IsGamePaused(GetWorld())
		&& !UGolmokPhotoModeSubsystem::IsActiveIn(GetWorld());
}

void UGolmokFootstepComponent::OnFootEvent(EGolmokFootEvent Kind, bool bLeft)
{
	if (!ensure(IsInGameThread())) return;
	if (Kind != EGolmokFootEvent::Step && Kind != EGolmokFootEvent::Land) return;
	++FootEventCount;
	if (!UsesNotifyDriver() || !IsActivePlayer()) return;
	Stepper.Reset(); bHasPrevious = false;
	TriggerFootstep(Kind == EGolmokFootEvent::Land);
}

void UGolmokFootstepComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	AGolmokCharacter* Character = Cast<AGolmokCharacter>(GetOwner());
	UGolmokAmbienceSubsystem* Audio = GetWorld() ? GetWorld()->GetSubsystem<UGolmokAmbienceSubsystem>() : nullptr;
	RefreshFootEventBinding();
	if (!Character || !Audio || !IsActivePlayer() || UsesNotifyDriver())
	{ Stepper.Reset(); bHasPrevious = false; return; }
	const FVector Position = Character->GetActorLocation();
	double Distance = bHasPrevious ? FVector::Dist2D(Position, Previous) : 0.0;
	Previous = Position; bHasPrevious = true;
	const FGolmokAudioConfig& Config = Audio->GetConfig();
	const auto* Roster = GetWorld()->GetSubsystem<UGolmokCharacterSubsystem>();
	const FString Id = Roster ? Roster->GetCurrentId() : FString();
	if (Id != LastRosterId) { Stepper.Reset(); Distance = 0; LastRosterId = Id; }
	const double Stride = Config.StrideFor(Id, Character->GetVelocity().Size2D() >= Config.RunThreshold);
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
	const FGolmokAudioConfig& Config = Audio->GetConfig();
	FHitResult Hit;
	const FVector Start = Character->GetActorLocation();
	const FVector End = Start - FVector(0, 0, Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 30.f);
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GolmokAudioFloor), true, Character);
	Params.bReturnPhysicalMaterial = true;
	FString Set = TEXT("default");
	Audio->SetSurfaceDiagnostic(0, FString());
	if (GetWorld()->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params))
	{
		const int32 Surface = static_cast<int32>(UGameplayStatics::GetSurfaceType(Hit));
		const FString Diagnostic = SurfaceDiagnostic(Config, Surface);
		Audio->SetSurfaceDiagnostic(Surface, Diagnostic);
		Set = ResolveSurfaceSet(Config, Surface,
			Hit.GetActor() && Hit.GetActor()->ActorHasTag(TEXT("Course/Stairs")), &Diagnostic);
	}
	Audio->PlayFootstep(Set, bLanding);
}

FString UGolmokFootstepComponent::ResolveSurfaceSet(const FGolmokAudioConfig& Config, int32 Surface, bool bStairs, const FString* Diagnostic)
{
	// SurfaceType numbers alone do not define an authored physical surface in this project.
	const FString Error = Diagnostic ? *Diagnostic : SurfaceDiagnostic(Config, Surface);
	const FString* Mapped = Error.IsEmpty() ? Config.Surfaces.Find(Surface) : nullptr;
	const auto Choice = GolmokAudioMath::ChooseSurface(Mapped != nullptr, bStairs);
	if (Choice == GolmokAudioMath::SurfaceChoice::StairsTag) return TEXT("stairs");
	return Choice == GolmokAudioMath::SurfaceChoice::PhysicalMaterial ? *Mapped : FString(TEXT("default"));
}

FString UGolmokFootstepComponent::SurfaceDiagnostic(const FGolmokAudioConfig& Config, int32 Surface)
{
	const FString* Expected = Config.Surfaces.Find(Surface);
	if (Surface == 0 || !Expected) return FString();
	const auto* Named = GetDefault<UPhysicsSettings>()->PhysicalSurfaces.FindByPredicate(
		[Surface](const FPhysicalSurfaceName& Entry) { return static_cast<int32>(Entry.Type) == Surface; });
	if (Named && Named->Name.ToString().Equals(*Expected, ESearchCase::IgnoreCase)) return FString();
	return FString::Printf(TEXT("surface %d needs Physics name '%s' (actual '%s'); physical mapping ignored"),
		Surface, **Expected, Named ? *Named->Name.ToString() : TEXT("undefined"));
}
