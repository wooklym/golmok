#include "Player/GolmokCharacter.h"

#include "Golmok.h"

#include "Animation/AnimInstance.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/LocalPlayer.h"
#include "Engine/SkeletalMesh.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputAction.h"
#include "InputActionValue.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"

AGolmokCharacter::AGolmokCharacter()
{
	PrimaryActorTick.bCanEverTick = false;

	// Roughly a 180 cm adult.
	GetCapsuleComponent()->InitCapsuleSize(42.f, 92.f);

	// Character turns toward movement; camera orbits independently.
	bUseControllerRotationPitch = false;
	bUseControllerRotationYaw = false;
	bUseControllerRotationRoll = false;

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->bOrientRotationToMovement = true;
	Movement->RotationRate = FRotator(0.f, 540.f, 0.f);
	Movement->MaxWalkSpeed = WalkSpeed;
	Movement->MinAnalogWalkSpeed = 20.f;
	Movement->BrakingDecelerationWalking = 2000.f;
	Movement->JumpZVelocity = 420.f;
	Movement->AirControl = 0.3f;
	// Alleys have curbs and single steps: allow up to ~25 cm, walkable slopes up to 45 degrees.
	Movement->MaxStepHeight = 25.f;
	Movement->SetWalkableFloorAngle(45.f);

	CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
	CameraBoom->SetupAttachment(RootComponent);
	CameraBoom->TargetArmLength = 320.f;
	CameraBoom->SocketOffset = FVector(0.f, 45.f, 55.f);
	CameraBoom->bUsePawnControlRotation = true;
	// Narrow alleys: keep the boom collision test on so the camera never clips into walls.
	CameraBoom->bDoCollisionTest = true;
	CameraBoom->ProbeSize = 14.f;
	CameraBoom->bEnableCameraLag = true;
	CameraBoom->CameraLagSpeed = 12.f;

	FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
	FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
	FollowCamera->bUsePawnControlRotation = false;
	FollowCamera->SetFieldOfView(80.f);

	GetMesh()->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -92.f), FRotator(0.f, -90.f, 0.f));
}

void AGolmokCharacter::PostInitializeComponents()
{
	Super::PostInitializeComponents();

	// Config values are loaded after the constructor ran on the CDO; re-apply the speed.
	GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
	ApplyCharacterVisuals();
}

void AGolmokCharacter::ApplyCharacterVisuals()
{
	USkeletalMesh* SkeletalMesh = nullptr;
	if (CharacterMeshPath.IsValid())
	{
		SkeletalMesh = Cast<USkeletalMesh>(CharacterMeshPath.TryLoad());
	}

	if (!SkeletalMesh)
	{
		UE_LOG(LogGolmok, Warning,
			TEXT("Character mesh '%s' not found; showing capsule. Add the Third Person content pack or set CharacterMeshPath."),
			*CharacterMeshPath.ToString());
		GetCapsuleComponent()->SetHiddenInGame(false);
		return;
	}

	GetMesh()->SetSkeletalMesh(SkeletalMesh);

	if (AnimClassPath.IsValid())
	{
		if (UClass* AnimClass = AnimClassPath.TryLoadClass<UAnimInstance>())
		{
			GetMesh()->SetAnimInstanceClass(AnimClass);
		}
		else
		{
			UE_LOG(LogGolmok, Warning, TEXT("Anim class '%s' not found; mesh will stay in reference pose."),
				*AnimClassPath.ToString());
		}
	}
}

void AGolmokCharacter::EnsureInputAssets()
{
	if (DefaultMappingContext)
	{
		return;
	}

	MoveAction = NewObject<UInputAction>(this, TEXT("IA_Move"));
	MoveAction->ValueType = EInputActionValueType::Axis2D;

	LookAction = NewObject<UInputAction>(this, TEXT("IA_Look"));
	LookAction->ValueType = EInputActionValueType::Axis2D;

	JumpAction = NewObject<UInputAction>(this, TEXT("IA_Jump"));
	JumpAction->ValueType = EInputActionValueType::Boolean;

	RunAction = NewObject<UInputAction>(this, TEXT("IA_Run"));
	RunAction->ValueType = EInputActionValueType::Boolean;

	DefaultMappingContext = NewObject<UInputMappingContext>(this, TEXT("IMC_Default"));
	UInputMappingContext* Context = DefaultMappingContext;

	// Keyboard keys produce a 1D value on X. Swizzle moves it to Y (forward/back); Negate flips it.
	auto MapMoveKey = [Context, this](const FKey& Key, bool bToY, bool bNegate)
	{
		FEnhancedActionKeyMapping& Mapping = Context->MapKey(MoveAction, Key);
		if (bToY)
		{
			Mapping.Modifiers.Add(NewObject<UInputModifierSwizzleAxis>(Context));
		}
		if (bNegate)
		{
			Mapping.Modifiers.Add(NewObject<UInputModifierNegate>(Context));
		}
	};
	MapMoveKey(EKeys::W, true, false);
	MapMoveKey(EKeys::S, true, true);
	MapMoveKey(EKeys::D, false, false);
	MapMoveKey(EKeys::A, false, true);
	Context->MapKey(MoveAction, EKeys::Gamepad_Left2D);

	// Mouse/right stick Y is positive when pushed up; pitch input is positive when looking down.
	auto MapLookKey = [Context, this](const FKey& Key)
	{
		FEnhancedActionKeyMapping& Mapping = Context->MapKey(LookAction, Key);
		if (!bInvertLookY)
		{
			UInputModifierNegate* Negate = NewObject<UInputModifierNegate>(Context);
			Negate->bX = false;
			Negate->bY = true;
			Negate->bZ = false;
			Mapping.Modifiers.Add(Negate);
		}
	};
	MapLookKey(EKeys::Mouse2D);
	MapLookKey(EKeys::Gamepad_Right2D);

	Context->MapKey(JumpAction, EKeys::SpaceBar);
	Context->MapKey(JumpAction, EKeys::Gamepad_FaceButton_Bottom);

	Context->MapKey(RunAction, EKeys::LeftShift);
	Context->MapKey(RunAction, EKeys::Gamepad_LeftThumbstick);
}

void AGolmokCharacter::AddMappingContext() const
{
	const APlayerController* PC = Cast<APlayerController>(Controller);
	if (!PC || !DefaultMappingContext)
	{
		return;
	}
	if (UEnhancedInputLocalPlayerSubsystem* Subsystem =
			ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
	{
		Subsystem->AddMappingContext(DefaultMappingContext, 0);
	}
}

void AGolmokCharacter::NotifyControllerChanged()
{
	Super::NotifyControllerChanged();
	EnsureInputAssets();
	AddMappingContext();
}

void AGolmokCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);
	EnsureInputAssets();

	UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(PlayerInputComponent);
	if (!Input)
	{
		UE_LOG(LogGolmok, Error, TEXT("Enhanced Input component missing; check Config/DefaultInput.ini."));
		return;
	}

	Input->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AGolmokCharacter::Move);
	Input->BindAction(LookAction, ETriggerEvent::Triggered, this, &AGolmokCharacter::Look);
	Input->BindAction(JumpAction, ETriggerEvent::Started, this, &ACharacter::Jump);
	Input->BindAction(JumpAction, ETriggerEvent::Completed, this, &ACharacter::StopJumping);
	Input->BindAction(RunAction, ETriggerEvent::Started, this, &AGolmokCharacter::StartRun);
	Input->BindAction(RunAction, ETriggerEvent::Completed, this, &AGolmokCharacter::StopRun);
}

void AGolmokCharacter::Move(const FInputActionValue& Value)
{
	if (!Controller)
	{
		return;
	}
	const FVector2D Axis = Value.Get<FVector2D>();
	const FRotator YawRotation(0.f, Controller->GetControlRotation().Yaw, 0.f);
	const FRotationMatrix YawMatrix(YawRotation);
	AddMovementInput(YawMatrix.GetUnitAxis(EAxis::X), Axis.Y);
	AddMovementInput(YawMatrix.GetUnitAxis(EAxis::Y), Axis.X);
}

void AGolmokCharacter::Look(const FInputActionValue& Value)
{
	const FVector2D Axis = Value.Get<FVector2D>();
	AddControllerYawInput(Axis.X);
	AddControllerPitchInput(Axis.Y);
}

void AGolmokCharacter::StartRun()
{
	GetCharacterMovement()->MaxWalkSpeed = RunSpeed;
}

void AGolmokCharacter::StopRun()
{
	GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
}

// [WP-18 hook] 로스터 교체 중 Shift 달리기 상태를 보존한다.
void AGolmokCharacter::SetMovementSpeeds(float InWalkSpeed, float InRunSpeed)
{
	const bool bWasRunning = FMath::IsNearlyEqual(GetCharacterMovement()->MaxWalkSpeed, RunSpeed);
	WalkSpeed = InWalkSpeed;
	RunSpeed = InRunSpeed;
	GetCharacterMovement()->MaxWalkSpeed = bWasRunning ? RunSpeed : WalkSpeed;
}
// [/WP-18 hook]
