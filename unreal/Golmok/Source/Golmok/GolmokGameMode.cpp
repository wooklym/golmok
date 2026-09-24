#include "GolmokGameMode.h"

#include "Debug/GolmokHUD.h"
#include "Player/GolmokCharacter.h"
#include "Player/GolmokPlayerController.h"

AGolmokGameMode::AGolmokGameMode()
{
	DefaultPawnClass = AGolmokCharacter::StaticClass();
	// WP-05: debug / lighting keys and the debug HUD (design section 5).
	PlayerControllerClass = AGolmokPlayerController::StaticClass();
	HUDClass = AGolmokHUD::StaticClass();
}
