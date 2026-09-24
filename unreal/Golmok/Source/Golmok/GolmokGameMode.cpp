#include "GolmokGameMode.h"

#include "Player/GolmokCharacter.h"

AGolmokGameMode::AGolmokGameMode()
{
	DefaultPawnClass = AGolmokCharacter::StaticClass();
}
