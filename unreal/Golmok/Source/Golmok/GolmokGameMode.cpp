#include "GolmokGameMode.h"

#include "Debug/GolmokHUD.h"
#include "Player/GolmokCharacter.h"
#include "Player/GolmokPlayerController.h"
#include "Animation/GolmokAnimationConfig.h" // [WP-19 hook]

AGolmokGameMode::AGolmokGameMode()
{
	DefaultPawnClass = AGolmokCharacter::StaticClass();
	// WP-05: debug / lighting keys and the debug HUD (design section 5).
	PlayerControllerClass = AGolmokPlayerController::StaticClass();
	HUDClass = AGolmokHUD::StaticClass();
}

// [WP-19 hook] ① AGolmokCharacter unless animation.json / -GolmokAnim / golmok.anim ask for gasp and rules 2-5 pass.
UClass* AGolmokGameMode::GetDefaultPawnClassForController_Implementation(AController* InController)
{
	return GolmokAnimation::ResolvePlayerPawnClass(InController, Super::GetDefaultPawnClassForController_Implementation(InController));
}
// [/WP-19 hook]
