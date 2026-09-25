#include "Debug/GolmokHUD.h"

#include "Golmok.h"

#include "Debug/GolmokDebugSubsystem.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Engine/World.h"
#include "Photo/GolmokPhotoModeSubsystem.h"

namespace
{
	const FLinearColor HudWhite(1.f, 1.f, 1.f, 1.f);
	const FLinearColor HudYellow(1.f, 0.9f, 0.2f, 1.f);
	const FLinearColor HudCyan(0.4f, 0.9f, 1.f, 1.f);
	const FLinearColor HudGreen(0.5f, 1.f, 0.5f, 1.f);
	const FLinearColor HudOrange(1.f, 0.6f, 0.2f, 1.f);
	const FLinearColor HudGray(0.7f, 0.7f, 0.7f, 1.f);

	/** Line color by prefix (design section 4-8); the fps line turns yellow when the 1% low is under half the average. */
	FLinearColor ColorForLine(const FString& Line, bool bLowFps)
	{
		if (Line.StartsWith(TEXT("Golmok")))
		{
			return bLowFps ? HudYellow : HudWhite;
		}
		if (Line.StartsWith(TEXT("game ")))
		{
			return HudWhite;
		}
		if (Line.StartsWith(TEXT("tod:")))
		{
			return HudYellow;
		}
		if (Line.StartsWith(TEXT("pos ")))
		{
			return HudCyan;
		}
		if (Line.StartsWith(TEXT("zones:")) || Line.StartsWith(TEXT("  ")) || Line.StartsWith(TEXT("portals:")))
		{
			return HudGreen;
		}
		if (Line.StartsWith(TEXT("path:")))
		{
			return HudOrange;
		}
		return HudGray;
	}

	/** Photo overlay (WP-12 design section 5-3): status line white (yellow when the character is in no loaded zone), values line cyan, hints gray, "saved ..." green. */
	FLinearColor PhotoColorForLine(const FString& Line, int32 Index)
	{
		if (Line.StartsWith(TEXT("saved ")))
		{
			return HudGreen;
		}
		if (Index == 0)
		{
			return Line.Contains(TEXT("no zone")) ? HudYellow : HudWhite;
		}
		return Index == 1 ? HudCyan : HudGray;
	}
} // namespace

void AGolmokHUD::DrawHUD()
{
	Super::DrawHUD();

	UWorld* World = GetWorld();
	UGolmokDebugSubsystem* Debug = World ? World->GetSubsystem<UGolmokDebugSubsystem>() : nullptr;
	UGolmokPhotoModeSubsystem* Photo = World ? World->GetSubsystem<UGolmokPhotoModeSubsystem>() : nullptr;
	if (Photo && Photo->IsHudSuppressed())
	{
		// WP-12 capture frames: nothing at all (debug HUD included) - the high-resolution shot includes the HUD (V-03).
		return;
	}
	if (!Debug || !Canvas)
	{
		return;
	}
	UFont* Font = GEngine ? GEngine->GetSmallFont() : nullptr;
	if (!Font)
	{
		return;
	}
	const float LineH = 16.f * HudScale;

	// WP-12 photo overlay (design section 3-5 / 5-3), bottom-left so it never meets the debug HUD at the top-left.
	// Drawn before the debug section because that section returns early while the debug HUD is hidden, which is the
	// normal state of photo mode (Enter hides it).
	if (Photo && Photo->IsActive() && !Photo->IsOverlayHidden())
	{
		const TArray<FString>& PhotoLines = Photo->GetOverlayLines();
		if (PhotoLines.Num() > 0)
		{
			// Canvas->SizeY is the viewport height in canvas units; Canvas->ClipY is the fallback named in design
			// section 10 #31 should SizeY not be the drawable height on the PC.
			const float PhotoY = static_cast<float>(Canvas->SizeY) - MarginPx - static_cast<float>(PhotoLines.Num()) * LineH;
			DrawRect(FLinearColor(0.f, 0.f, 0.f, 0.55f), MarginPx - 6.f, PhotoY - 4.f, 640.f * HudScale, static_cast<float>(PhotoLines.Num()) * LineH + 8.f);
			for (int32 i = 0; i < PhotoLines.Num(); ++i)
			{
				DrawText(PhotoLines[i], PhotoColorForLine(PhotoLines[i], i), MarginPx, PhotoY + static_cast<float>(i) * LineH, Font, HudScale);
			}
		}
	}

	if (!Debug->IsHudVisible())
	{
		if (Debug->IsPlaying())
		{
			const FString PathLine = FString::Printf(TEXT("path: %s"), *Debug->DescribePathState());
			DrawRect(FLinearColor(0.f, 0.f, 0.f, 0.55f), MarginPx - 6.f, MarginPx - 4.f, 640.f * HudScale, LineH + 8.f);
			DrawText(PathLine, HudOrange, MarginPx, MarginPx, Font, HudScale);
		}
		return;
	}

	const TArray<FString>& Lines = Debug->GetHudLines();
	const GolmokStatsMath::Stats& Stats = Debug->GetLastStats();
	const bool bLowFps = Stats.Frames > 0 && Stats.OnePercentLowFps < Stats.AvgFps * 0.5;

	DrawRect(FLinearColor(0.f, 0.f, 0.f, 0.55f), MarginPx - 6.f, MarginPx - 4.f, 640.f * HudScale, static_cast<float>(Lines.Num()) * LineH + 8.f);
	for (int32 i = 0; i < Lines.Num(); ++i)
	{
		DrawText(Lines[i], ColorForLine(Lines[i], bLowFps), MarginPx, MarginPx + static_cast<float>(i) * LineH, Font, HudScale);
	}
}
