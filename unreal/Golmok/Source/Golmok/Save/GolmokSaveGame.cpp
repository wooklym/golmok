#include "Save/GolmokSaveGame.h"

const FGolmokSaveVisit* UGolmokSaveGame::FindVisit(const FString& InZoneId) const
{
	return Visited.FindByPredicate([&InZoneId](const FGolmokSaveVisit& V) { return V.ZoneId == InZoneId; });
}
