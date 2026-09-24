#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GolmokCharacter.generated.h"

class UCameraComponent;
class UInputAction;
class UInputMappingContext;
class USpringArmComponent;
struct FInputActionValue;

/**
 * Third-person character: walk (default), run (hold Shift / left stick click), jump, orbit camera.
 *
 * Input actions and the mapping context are created in C++ at runtime so the project needs no
 * binary input assets. Mesh and animation come from soft paths in DefaultGame.ini; when they are
 * missing the character still works and shows its collision capsule.
 */
UCLASS(Config = Game)
class GOLMOK_API AGolmokCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	AGolmokCharacter();

	virtual void PostInitializeComponents() override;
	virtual void NotifyControllerChanged() override;

	USpringArmComponent* GetCameraBoom() const { return CameraBoom; }
	UCameraComponent* GetFollowCamera() const { return FollowCamera; }
	float GetWalkSpeed() const { return WalkSpeed; }
	float GetRunSpeed() const { return RunSpeed; }

protected:
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

private:
	void EnsureInputAssets();
	void AddMappingContext() const;
	void ApplyCharacterVisuals();

	void Move(const FInputActionValue& Value);
	void Look(const FInputActionValue& Value);
	void StartRun();
	void StopRun();

	UPROPERTY(VisibleAnywhere, Category = "Camera")
	TObjectPtr<USpringArmComponent> CameraBoom;

	UPROPERTY(VisibleAnywhere, Category = "Camera")
	TObjectPtr<UCameraComponent> FollowCamera;

	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> DefaultMappingContext;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> MoveAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> LookAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> JumpAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> RunAction;

	/** Walking speed in cm/s (about 6.5 km/h). */
	UPROPERTY(Config, EditAnywhere, Category = "Movement")
	float WalkSpeed = 180.f;

	/** Running speed in cm/s (about 18 km/h). */
	UPROPERTY(Config, EditAnywhere, Category = "Movement")
	float RunSpeed = 500.f;

	UPROPERTY(Config, EditAnywhere, Category = "Camera")
	bool bInvertLookY = false;

	UPROPERTY(Config, EditAnywhere, Category = "Visuals")
	FSoftObjectPath CharacterMeshPath;

	UPROPERTY(Config, EditAnywhere, Category = "Visuals")
	FSoftClassPath AnimClassPath;
};
