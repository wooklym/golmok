#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GolmokGameMode.generated.h"

UCLASS()
class GOLMOK_API AGolmokGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AGolmokGameMode();
	// [WP-19 hook] animation.json mode gasp picks the local GASP pawn Blueprint per spawn (① fallback, D-021).
	virtual UClass* GetDefaultPawnClassForController_Implementation(AController* InController) override;
	// [/WP-19 hook]
};
