#pragma once

#include "CoreMinimal.h"
#include "Engine/GameViewportClient.h"
#include "GolmokGameViewportClient.generated.h"

/**
 * Project game viewport client (WP-12). UGameViewportClient::bSuppressTransitionMessage is protected in UE 5.8.3 and the
 * engine offers SetSuppressTransitionMessage(bool) but no getter (V-09 build report, C2248), so photo mode could not
 * snapshot the flag it overrides while paused (the "PAUSED" transition text must stay out of the photo). This subclass
 * exposes the raw value; DefaultEngine.ini [/Script/Engine.Engine] GameViewportClientClassName selects it. Without that
 * line the photo subsystem falls back to the engine default (false) and warns once.
 */
UCLASS()
class GOLMOK_API UGolmokGameViewportClient : public UGameViewportClient
{
	GENERATED_BODY()

public:
	/** Raw bSuppressTransitionMessage (protected in the base class; readable here). */
	bool IsTransitionMessageSuppressed() const { return bSuppressTransitionMessage != 0; }
};
