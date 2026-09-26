#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "GolmokHUD.generated.h"

/**
 * Debug overlay (WP-05 design section 4-8): draws the lines of UGolmokDebugSubsystem::GetHudLines() with the engine
 * small font over a translucent box while the HUD is visible (golmok.hud / F1). While a path plays with the HUD
 * hidden only the "path:" progress line is drawn. It is hidden by photo mode while capturing (WP-12); golmok.screenshot
 * includes it (V-03).
 * Set as HUDClass by AGolmokGameMode. Config: [/Script/Golmok.GolmokHUD] in DefaultGame.ini.
 */
UCLASS(Config = Game)
class GOLMOK_API AGolmokHUD : public AHUD
{
	GENERATED_BODY()

public:
	/** Text and box scale. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "0.5", ClampMax = "3.0"))
	float HudScale = 1.f;

	/** Distance from the top-left corner of the viewport (px). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "0.0"))
	float MarginPx = 16.f;

	virtual void DrawHUD() override;
};
