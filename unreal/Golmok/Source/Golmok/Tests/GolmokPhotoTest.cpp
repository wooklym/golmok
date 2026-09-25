// Photo mode tests (WP-12 design section 8-1).
//
// Golmok.Photo.EnterExit: on L_Dev, Enter() pauses the game, makes the photo pawn the view target WITHOUT possessing
//                         it, hides the debug HUD and suspends the debug keys; the pawn ticks while paused; playback
//                         and recording refuse each other; a running lighting transition resumes where it was after
//                         Exit(); a pause that pre-dates photo mode is kept; golmok.photo 1 / 0 round-trip.
// Golmok.Photo.Clamp:     the pure constraint math (sphere / footprint polygon / Constrain / parameter steps), then
//                         on L_Dev the pawn stays inside the sphere and a test footprint, stops on the floor, stops
//                         at a transient blocking box and passes once the box is gone; SetParam / Reset.
// Golmok.Photo.MetaJson:  FormatPhotoMetaJson matches the design section 2-2 layout byte for byte (null groups, string
//                         escapes, FJsonSerializer round trip); GolmokPhotoJson::ParseConfigText rejects the design
//                         section 2-1 violations and accepts Config/Golmok/photo.json; on L_Dev BuildMeta / Shoot()
//                         write <stem>.json (15 keys in order), a second shot in the same second gets _2, Exit()
//                         during a capture is deferred, golmok.photo.set works.
//
// Every wait uses FPlatformTime::Seconds(): the world clock stands still while the game is paused. Files the tests
// create are deleted at the end and in the latent commands' destructors. Passes under -nullrhi (no png is written
// there: the capture window closes on the 3 s timeout).
//
// Headless: .\tools\ue\test.ps1 -Filter Golmok.Photo   (or in the editor console: Automation RunTests Golmok.Photo)

#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR

#include "Camera/PlayerCameraManager.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "CoreGlobals.h"
#include "Debug/GolmokDebugSubsystem.h"
#include "Debug/GolmokStatsMath.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Editor.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "GameFramework/PlayerController.h"
#include "Geo/GolmokGeoSubsystem.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformTime.h"
#include "Kismet/GameplayStatics.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Misc/DateTime.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Photo/GolmokPhotoCameraPawn.h"
#include "Photo/GolmokPhotoMath.h"
#include "Photo/GolmokPhotoModeSubsystem.h"
#include "Player/GolmokCharacter.h"
#include "Player/GolmokPlayerController.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Tests/AutomationEditorCommon.h"

namespace GolmokPhotoTest
{
	const TCHAR* DevMap = TEXT("/Game/Golmok/Maps/L_Dev");

	FString FromStd(const std::string& S)
	{
		return FString(UTF8_TO_TCHAR(S.c_str()));
	}

	std::string ToStd(const FString& S)
	{
		return std::string(TCHAR_TO_UTF8(*S));
	}

	/** Design section 2-2 example: every value sits on the output decimal grid. */
	GolmokPhotoMath::PhotoMeta ExampleMeta()
	{
		GolmokPhotoMath::PhotoMeta M;
		M.Version = 1;
		M.TimeUtc = "2026-09-25T10:11:12Z";
		M.bHasPreset = true;
		M.Preset = "overcast_morning";
		M.bHasZone = true;
		M.ZoneId = "z_synthetic_001";
		M.ZoneVersion = 1;
		M.bHasGeo = true;
		M.Lon = 126.9250123;
		M.Lat = 37.5620456;
		M.HeightM = 51.234;
		M.UeLocation = {17670.59, -22698.0, 1190.0};
		M.Rotation = {-5.0, 90.0, 0.0};
		M.Fov = 65.0;
		M.ExposureEv = 0.33;
		M.bDofEnabled = false;
		M.FocalM = 3.0;
		M.Fstop = 2.8;
		M.Multiplier = 2;
		M.bCharacterHidden = false;
		return M;
	}

	const TCHAR* ExampleJson = TEXT("{\n")
							   TEXT("  \"version\": 1,\n")
							   TEXT("  \"time_utc\": \"2026-09-25T10:11:12Z\",\n")
							   TEXT("  \"preset\": \"overcast_morning\",\n")
							   TEXT("  \"zone_id\": \"z_synthetic_001\",\n")
							   TEXT("  \"zone_version\": 1,\n")
							   TEXT("  \"lon\": 126.9250123,\n")
							   TEXT("  \"lat\": 37.5620456,\n")
							   TEXT("  \"height_m\": 51.234,\n")
							   TEXT("  \"ue_location\": [17670.59, -22698.00, 1190.00],\n")
							   TEXT("  \"rotation\": [-5.000, 90.000, 0.000],\n")
							   TEXT("  \"fov\": 65.0,\n")
							   TEXT("  \"exposure_ev\": 0.33,\n")
							   TEXT("  \"dof\": {\"enabled\": false, \"focal_m\": 3.000, \"fstop\": 2.80},\n")
							   TEXT("  \"multiplier\": 2,\n")
							   TEXT("  \"character_hidden\": false\n")
							   TEXT("}\n");

	/** Design section 2-2 key order (the meta file is written one key per line in this order). */
	const TCHAR* MetaKeys[15] = {TEXT("version"), TEXT("time_utc"), TEXT("preset"), TEXT("zone_id"), TEXT("zone_version"), TEXT("lon"), TEXT("lat"), TEXT("height_m"),
		TEXT("ue_location"), TEXT("rotation"), TEXT("fov"), TEXT("exposure_ev"), TEXT("dof"), TEXT("multiplier"), TEXT("character_hidden")};

	TSharedPtr<FJsonObject> ParseJson(const FString& Text)
	{
		TSharedPtr<FJsonObject> Root;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
		if (!FJsonSerializer::Deserialize(Reader, Root))
		{
			return nullptr;
		}
		return Root;
	}

	FString SerializeJson(const TSharedPtr<FJsonObject>& Root)
	{
		FString Text;
		const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Text);
		FJsonSerializer::Serialize(Root.ToSharedRef(), Writer);
		return Text;
	}

	/** Keys of a parsed object in file order (FJsonObject::Values keeps insertion order; keys are UE::FSharedString in 5.8). */
	TArray<FString> KeysInOrder(const TSharedPtr<FJsonObject>& Object)
	{
		TArray<FString> Keys;
		for (const auto& Pair : Object->Values)
		{
			Keys.Add(FString(*Pair.Key));
		}
		return Keys;
	}

	/** <stem>.json, <stem>.png and the HighResShot fallback name <stem>00000.png. */
	void DeleteShotFiles(const TArray<FString>& StemsNoExt)
	{
		for (const FString& Stem : StemsNoExt)
		{
			for (const TCHAR* Suffix : {TEXT(".json"), TEXT(".png"), TEXT("00000.png")})
			{
				IFileManager::Get().Delete(*(Stem + Suffix), /*RequireExists*/ false, /*EvenReadOnly*/ true, /*Quiet*/ true);
			}
		}
	}

	/** Shared latent-command skeleton: PIE world lookup, real-time phases, timeouts. */
	class FPhotoScenarioBase : public IAutomationLatentCommand
	{
	public:
		explicit FPhotoScenarioBase(FAutomationTestBase* InTest) : Test(InTest), CreatedAt(FPlatformTime::Seconds()) {}

	protected:
		/** Null (and a timeout error after 60 s) until the PIE world runs. */
		UWorld* PlayWorld()
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			if (World && PhaseStart < 0.0)
			{
				PhaseStart = FPlatformTime::Seconds();
			}
			return World;
		}

		double Elapsed() const
		{
			return FPlatformTime::Seconds() - PhaseStart;
		}

		bool Next(int32 NextPhase)
		{
			Phase = NextPhase;
			PhaseStart = FPlatformTime::Seconds();
			return false;
		}

		/** False (keep waiting) until Timeout seconds of real time passed in this phase, then an error and true. */
		bool Fail(const TCHAR* What, double Timeout)
		{
			if (Elapsed() < Timeout)
			{
				return false;
			}
			Test->AddError(FString::Printf(TEXT("%s (phase %d, %.1f s)"), What, Phase, Elapsed()));
			return true;
		}

		bool NoWorld()
		{
			if (FPlatformTime::Seconds() - CreatedAt < 60.0)
			{
				return false;
			}
			Test->AddError(TEXT("PIE world not running after 60 s"));
			return true;
		}

		FAutomationTestBase* Test;
		double CreatedAt;
		int32 Phase = 0;
		double PhaseStart = -1.0;
	};

	// ---- EnterExit scenario -----------------------------------------------------------------------------------

	const TCHAR* RecordName = TEXT("_automation_photo");
	const TCHAR* PlayName = TEXT("_automation_photo_play");

	enum class EEnterExitPhase : int32
	{
		WaitForPawn,
		Paused,
		Exited,
		Refusals,
		Console,
		Done,
	};

	class FEnterExitScenario : public FPhotoScenarioBase
	{
	public:
		explicit FEnterExitScenario(FAutomationTestBase* InTest) : FPhotoScenarioBase(InTest) {}

		virtual ~FEnterExitScenario() override
		{
			DeleteFiles();
		}

		virtual bool Update() override
		{
			UWorld* World = PlayWorld();
			if (!World)
			{
				return NoWorld();
			}
			UGolmokPhotoModeSubsystem* Photo = UGolmokPhotoModeSubsystem::Get(World);
			UGolmokDebugSubsystem* Debug = World->GetSubsystem<UGolmokDebugSubsystem>();
			AGolmokPlayerController* PC = Cast<AGolmokPlayerController>(World->GetFirstPlayerController());
			if (!Photo || !Debug || !PC)
			{
				return Fail(TEXT("no UGolmokPhotoModeSubsystem / UGolmokDebugSubsystem / AGolmokPlayerController in the PIE world"), 10.0);
			}

			switch (static_cast<EEnterExitPhase>(Phase))
			{
			case EEnterExitPhase::WaitForPawn:
			{
				AGolmokCharacter* Pawn = Cast<AGolmokCharacter>(PC->GetPawn());
				if (Elapsed() < 0.5 || !Pawn || !PC->PlayerCameraManager)
				{
					return Fail(TEXT("no AGolmokCharacter possessed by the first player controller"), 20.0);
				}
				Character = Pawn;
				Debug->SetHudVisible(true);
				CameraLocationBefore = PC->PlayerCameraManager->GetCameraLocation();
				FovBefore = PC->PlayerCameraManager->GetFOVAngle();
				CharacterLocationBefore = Pawn->GetActorLocation();
				ControlRotationBefore = PC->GetControlRotation();
				const bool bFullTick = PC->bShouldPerformFullTickWhenPaused;
				bFullTickBefore = bFullTick;

				FString Message;
				if (!Test->TestTrue(TEXT("Enter()"), Photo->Enter(Message)))
				{
					Test->AddError(Message);
					return true;
				}
				Test->AddInfo(Message);
				Test->TestTrue(TEXT("IsActive()"), Photo->IsActive());
				Test->TestTrue(TEXT("State == Active"), Photo->GetState() == EGolmokPhotoState::Active);
				Test->TestTrue(TEXT("IsGamePaused(World)"), UGameplayStatics::IsGamePaused(World));
				AGolmokPhotoCameraPawn* PhotoPawn = Cast<AGolmokPhotoCameraPawn>(PC->GetViewTarget());
				Test->TestNotNull(TEXT("view target is the AGolmokPhotoCameraPawn"), PhotoPawn);
				Test->TestTrue(TEXT("PC->GetPawn() is still the AGolmokCharacter (no possession)"), PC->GetPawn() == Pawn);
				PawnRef = Photo->GetPhotoPawn();
				if (PhotoPawn)
				{
					Test->TestTrue(TEXT("photo pawn starts at the player camera location (1 cm)"),
						FVector::Dist(PhotoPawn->GetActorLocation(), CameraLocationBefore) <= 1.0);
				}
				Test->TestTrue(FString::Printf(TEXT("GetParam(Fov) == entry FOV (%.1f)"), FovBefore), FMath::IsNearlyEqual(Photo->GetParam(EGolmokPhotoParam::Fov), static_cast<double>(FovBefore), 0.01));
				Test->TestFalse(TEXT("debug HUD hidden on Enter"), Debug->IsHudVisible());
				Test->TestTrue(TEXT("debug keys suspended on Enter"), PC->IsDebugKeysSuspended());
				FString Again;
				Test->TestFalse(TEXT("second Enter() refused"), Photo->Enter(Again));
				Test->TestTrue(TEXT("second Enter() says 'already active'"), Again.Contains(TEXT("already active")));
				return Next(static_cast<int32>(EEnterExitPhase::Paused));
			}

			case EEnterExitPhase::Paused:
			{
				if (Elapsed() < 0.5)
				{
					return false;
				}
				if (!Character.IsValid())
				{
					Test->AddError(TEXT("the character disappeared while paused"));
					return true;
				}
				Test->TestTrue(TEXT("character did not move while paused (1 cm)"), FVector::Dist(Character->GetActorLocation(), CharacterLocationBefore) <= 1.0);
				Test->TestTrue(FString::Printf(TEXT("photo pawn ticked while paused (%d ticks)"), Photo->GetPawnTickCount()), Photo->GetPawnTickCount() > 0);

				Photo->SetCharacterHidden(true);
				Test->TestTrue(TEXT("SetCharacterHidden(true) hides the character"), Character->IsHidden());
				FString Message;
				Test->TestFalse(TEXT("StartPlayback refused while photo mode is on"), Debug->StartPlayback(TEXT("quick"), /*bCsv*/ false, Message));
				Test->TestTrue(TEXT("StartPlayback refusal names photo mode"), Message.Contains(TEXT("photo mode is on")));

				// Drift: a transition started while paused resumes where it was after Exit (ShiftTransitionStart).
				AGolmokTimeOfDay* Tod = AGolmokTimeOfDay::Find(World);
				if (Tod && IFileManager::Get().FileExists(*Tod->ResolvePresetsPath()))
				{
					Tod->TransitionSeconds = 0.5f;
					if (Tod->ApplyPreset(TEXT("clear_noon")) && Tod->IsTransitioning())
					{
						bDriftStarted = true;
					}
					else
					{
						Test->AddInfo(TEXT("ApplyPreset(clear_noon) started no transition; drift assertion skipped"));
					}
				}
				else
				{
					Test->AddInfo(TEXT("lighting presets file missing; drift block skipped"));
				}
				return Next(static_cast<int32>(EEnterExitPhase::Exited));
			}

			case EEnterExitPhase::Exited:
			{
				if (Elapsed() < 1.0)
				{
					return false;
				}
				Test->TestTrue(TEXT("Exit(test)"), Photo->Exit(TEXT("test")));
				AGolmokTimeOfDay* Tod = AGolmokTimeOfDay::Find(World);
				if (bDriftStarted && Tod)
				{
					Test->TestTrue(TEXT("transition still running after Exit"), Tod->IsTransitioning());
					Test->TestTrue(FString::Printf(TEXT("transition alpha < 0.3 after 1 s paused (%.3f)"), Tod->GetTransitionAlpha()), Tod->GetTransitionAlpha() < 0.3f);
				}
				Test->TestFalse(TEXT("game unpaused after Exit"), UGameplayStatics::IsGamePaused(World));
				Test->TestTrue(TEXT("view target is the character again"), Character.IsValid() && PC->GetViewTarget() == Character.Get());
				Test->TestTrue(TEXT("control rotation restored"), PC->GetControlRotation().Equals(ControlRotationBefore, 0.01f));
				Test->TestTrue(TEXT("character visible again"), Character.IsValid() && !Character->IsHidden());
				Test->TestTrue(TEXT("debug HUD visibility restored (true)"), Debug->IsHudVisible());
				Test->TestFalse(TEXT("debug keys no longer suspended"), PC->IsDebugKeysSuspended());
				const bool bFullTickAfter = PC->bShouldPerformFullTickWhenPaused;
				Test->TestTrue(TEXT("bShouldPerformFullTickWhenPaused restored (false)"), bFullTickAfter == bFullTickBefore && !bFullTickAfter);
				Test->TestTrue(TEXT("photo pawn destroyed (or pending kill)"), !PawnRef.IsValid() || PawnRef->IsPendingKillPending());
				Test->TestTrue(TEXT("State == Inactive"), Photo->GetState() == EGolmokPhotoState::Inactive);

				// A pause that pre-dates photo mode is kept.
				if (UGameplayStatics::SetGamePaused(World, true))
				{
					FString Message;
					Test->TestTrue(TEXT("Enter() while already paused"), Photo->Enter(Message));
					Test->TestTrue(TEXT("Enter() message says 'already paused'"), Message.Contains(TEXT("already paused")));
					Test->TestTrue(TEXT("Exit() after a pre-existing pause"), Photo->Exit(TEXT("test")));
					Test->TestTrue(TEXT("pre-existing pause kept after Exit"), UGameplayStatics::IsGamePaused(World));
					UGameplayStatics::SetGamePaused(World, false);
				}
				else
				{
					Test->AddInfo(TEXT("SetGamePaused(true) refused; pre-existing pause block skipped"));
				}
				return Next(static_cast<int32>(EEnterExitPhase::Refusals));
			}

			case EEnterExitPhase::Refusals:
			{
				FString Message;
				if (Test->TestTrue(TEXT("StartRecording(_automation_photo)"), Debug->StartRecording(RecordName, Message)))
				{
					FString Refused;
					Test->TestFalse(TEXT("Enter() refused while recording"), Photo->Enter(Refused));
					Test->TestTrue(TEXT("refusal names the recording"), Refused.Contains(TEXT("while recording")) && Refused.Contains(RecordName));
					Debug->StopRecording(Message);
					RecordFile = Debug->PathFilePath(RecordName);
				}
				else
				{
					Test->AddError(Message);
				}

				// A two-sample path (3 s) played back through the debug subsystem.
				GolmokStatsMath::CameraPath Path;
				Path.Version = 1;
				Path.Name = ToStd(PlayName);
				Path.Level = "L_Dev";
				Path.Hz = 10;
				Path.Created = "2026-09-25T00:00:00Z";
				const FVector P = CharacterLocationBefore;
				for (int32 i = 0; i < 2; ++i)
				{
					GolmokStatsMath::PoseSample S;
					S.T = 3.0 * i;
					S.P[0] = P.X;
					S.P[1] = P.Y;
					S.P[2] = P.Z + 100.0;
					S.R[0] = 0.0;
					S.R[1] = 90.0 * i;
					S.R[2] = 0.0;
					Path.Samples.push_back(S);
				}
				PlayFile = Debug->PathFilePath(PlayName);
				FString Error;
				if (Test->TestTrue(TEXT("SavePathFile(_automation_photo_play)"), UGolmokDebugSubsystem::SavePathFile(PlayFile, Path, Error)))
				{
					if (Test->TestTrue(TEXT("StartPlayback(_automation_photo_play)"), Debug->StartPlayback(PlayName, /*bCsv*/ false, Message)))
					{
						FString Refused;
						Test->TestFalse(TEXT("Enter() refused while a path plays"), Photo->Enter(Refused));
						Test->TestTrue(TEXT("refusal names the playback"), Refused.Contains(TEXT("path is playing")));
						Debug->StopPlayback(TEXT("test"));
					}
					else
					{
						Test->AddError(Message);
					}
				}
				else
				{
					Test->AddError(Error);
				}
				DeleteFiles();
				return Next(static_cast<int32>(EEnterExitPhase::Console));
			}

			case EEnterExitPhase::Console:
			{
				// StopPlayback re-possesses the character; give it a moment before the console round trip.
				if (Elapsed() < 0.5 || !Cast<AGolmokCharacter>(PC->GetPawn()))
				{
					return Fail(TEXT("character not possessed again after StopPlayback"), 10.0);
				}
				IConsoleManager::Get().ProcessUserConsoleInput(TEXT("golmok.photo 1"), *GLog, World);
				Test->TestTrue(TEXT("golmok.photo 1 enters"), Photo->IsActive());
				IConsoleManager::Get().ProcessUserConsoleInput(TEXT("golmok.photo 0"), *GLog, World);
				Test->TestFalse(TEXT("golmok.photo 0 leaves"), Photo->IsActive());
				Test->TestFalse(TEXT("game unpaused after the console round trip"), UGameplayStatics::IsGamePaused(World));
				return Next(static_cast<int32>(EEnterExitPhase::Done));
			}

			case EEnterExitPhase::Done:
			default:
				return true;
			}
		}

	private:
		void DeleteFiles()
		{
			for (FString* File : {&RecordFile, &PlayFile})
			{
				if (!File->IsEmpty())
				{
					IFileManager::Get().Delete(**File, /*RequireExists*/ false, /*EvenReadOnly*/ true, /*Quiet*/ true);
					File->Reset();
				}
			}
		}

		TWeakObjectPtr<AGolmokCharacter> Character;
		TWeakObjectPtr<AGolmokPhotoCameraPawn> PawnRef;
		FVector CameraLocationBefore = FVector::ZeroVector;
		FVector CharacterLocationBefore = FVector::ZeroVector;
		FRotator ControlRotationBefore = FRotator::ZeroRotator;
		float FovBefore = 0.f;
		bool bFullTickBefore = false;
		bool bDriftStarted = false;
		FString RecordFile;
		FString PlayFile;
	};

	// ---- Clamp scenario ----------------------------------------------------------------------------------------

	enum class EClampPhase : int32
	{
		WaitForPawn,
		Done,
	};

	class FClampScenario : public FPhotoScenarioBase
	{
	public:
		explicit FClampScenario(FAutomationTestBase* InTest) : FPhotoScenarioBase(InTest) {}

		virtual bool Update() override
		{
			UWorld* World = PlayWorld();
			if (!World)
			{
				return NoWorld();
			}
			UGolmokPhotoModeSubsystem* Photo = UGolmokPhotoModeSubsystem::Get(World);
			APlayerController* PC = World->GetFirstPlayerController();
			if (!Photo || !PC)
			{
				return Fail(TEXT("no UGolmokPhotoModeSubsystem / player controller in the PIE world"), 10.0);
			}
			if (static_cast<EClampPhase>(Phase) == EClampPhase::Done)
			{
				return true;
			}
			AGolmokCharacter* Character = Cast<AGolmokCharacter>(PC->GetPawn());
			if (Elapsed() < 0.5 || !Character)
			{
				return Fail(TEXT("no AGolmokCharacter possessed by the first player controller"), 20.0);
			}

			FString Message;
			if (!Test->TestTrue(TEXT("Enter()"), Photo->Enter(Message)))
			{
				Test->AddError(Message);
				return true;
			}
			AGolmokPhotoCameraPawn* Pawn = Photo->GetPhotoPawn();
			if (!Test->TestNotNull(TEXT("photo pawn spawned"), Pawn))
			{
				Photo->Exit(TEXT("test"));
				return true;
			}
			const FVector Anchor = Photo->GetAnchor();
			const FVector EntryLocation = Pawn->GetActorLocation();
			const double RadiusCm = static_cast<double>(Photo->MaxDistanceM) * 100.0;
			const double Sweep = static_cast<double>(Photo->CollisionRadiusCm);

			// (b) sphere + test footprint (4 x 4 m square around the anchor)
			TArray<FVector2D> Square;
			Square.Add(FVector2D(Anchor.X - 200.0, Anchor.Y - 200.0));
			Square.Add(FVector2D(Anchor.X + 200.0, Anchor.Y - 200.0));
			Square.Add(FVector2D(Anchor.X + 200.0, Anchor.Y + 200.0));
			Square.Add(FVector2D(Anchor.X - 200.0, Anchor.Y + 200.0));
			Photo->SetFootprintForTest(Square);
			Test->TestEqual(TEXT("SetFootprintForTest copied 4 vertices"), Photo->GetFootprintXs().Num(), 4);
			Pawn->MoveConstrained(Anchor + FVector(1000.0, 0.0, 0.0));
			FVector Location = Pawn->GetActorLocation();
			Test->AddInfo(FString::Printf(TEXT("after +1000 x: %s (anchor %s)"), *Location.ToString(), *Anchor.ToString()));
			Test->TestTrue(TEXT("pawn inside the sphere after +1000 x"), FVector::Dist(Location, Anchor) <= RadiusCm + 1.0);
			Test->TestTrue(TEXT("pawn inside the square after +1000 x"), FMath::Abs(Location.X - Anchor.X) <= 200.0 + 0.01 && FMath::Abs(Location.Y - Anchor.Y) <= 200.0 + 0.01);

			// floor: the sweep sphere stops on it (floor = character feet)
			const double FloorZ = Anchor.Z - (Character->GetCapsuleComponent() ? Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() : 92.f);
			Pawn->MoveConstrained(Anchor + FVector(0.0, 0.0, -500.0));
			Location = Pawn->GetActorLocation();
			Test->AddInfo(FString::Printf(TEXT("after -500 z: %s (floor z %.1f)"), *Location.ToString(), FloorZ));
			Test->TestTrue(TEXT("pawn inside the sphere after -500 z"), FVector::Dist(Location, Anchor) <= RadiusCm + 1.0);
			Test->TestTrue(TEXT("floor sweep stops the pawn (z >= floor - radius - 20 cm)"), Location.Z >= FloorZ - Sweep - 20.0);

			// (c) a transient blocking box 1 m in front of the anchor; the move stops before it and passes once it is gone
			Photo->Reset();
			TArray<FVector2D> Wide;
			Wide.Add(FVector2D(Anchor.X - 400.0, Anchor.Y - 400.0));
			Wide.Add(FVector2D(Anchor.X + 400.0, Anchor.Y - 400.0));
			Wide.Add(FVector2D(Anchor.X + 400.0, Anchor.Y + 400.0));
			Wide.Add(FVector2D(Anchor.X - 400.0, Anchor.Y + 400.0));
			Photo->SetFootprintForTest(Wide);
			const FVector Forward = FRotator(0.f, Character->GetActorRotation().Yaw, 0.f).Vector();
			const FVector BoxCenter = Anchor + Forward * 100.0;
			const FRotator BoxRotation(0.f, Character->GetActorRotation().Yaw, 0.f);
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			Params.ObjectFlags = EObjectFlags(Params.ObjectFlags | RF_Transient);
			AActor* BoxActor = World->SpawnActor<AActor>(AActor::StaticClass(), BoxCenter, BoxRotation, Params);
			UBoxComponent* Box = BoxActor ? NewObject<UBoxComponent>(BoxActor, TEXT("PhotoTestBox")) : nullptr;
			if (Test->TestNotNull(TEXT("transient box actor spawned"), Box))
			{
				Box->SetMobility(EComponentMobility::Movable);
				Box->SetBoxExtent(FVector(50.f));
				Box->SetCollisionProfileName(TEXT("BlockAll"));
				BoxActor->SetRootComponent(Box);
				Box->RegisterComponent();
				BoxActor->SetActorLocationAndRotation(BoxCenter, BoxRotation);

				const FVector Target = Anchor + Forward * 200.0;
				Pawn->MoveConstrained(Target);
				Location = Pawn->GetActorLocation();
				const FVector Local = BoxRotation.UnrotateVector(Location - BoxCenter);
				const double FaceDistance = FMath::Max3(FMath::Abs(Local.X) - 50.0, FMath::Abs(Local.Y) - 50.0, FMath::Abs(Local.Z) - 50.0);
				const double Along = FVector::DotProduct(Location - Anchor, Forward);
				Test->AddInfo(FString::Printf(TEXT("box at %s: pawn %s, face distance %.1f, along %.1f"), *BoxCenter.ToString(), *Location.ToString(), FaceDistance, Along));
				Test->TestTrue(TEXT("pawn keeps the sweep radius from the box faces"), FaceDistance >= Sweep - 1.0);
				Test->TestTrue(TEXT("pawn did not pass the box"), Along < 100.0);

				BoxActor->Destroy();
				Pawn->MoveConstrained(Target);
				Location = Pawn->GetActorLocation();
				const double AlongAfter = FVector::DotProduct(Location - Anchor, Forward);
				Test->AddInfo(FString::Printf(TEXT("box destroyed: pawn %s, along %.1f"), *Location.ToString(), AlongAfter));
				Test->TestTrue(TEXT("the same move passes once the box is gone"), AlongAfter > 100.0);
			}

			// (d) SetParam / Reset
			Test->TestTrue(TEXT("SetParam(Fov, 200)"), Photo->SetParam(EGolmokPhotoParam::Fov, 200.0, Message));
			Test->TestTrue(TEXT("Fov clamped to 110"), FMath::IsNearlyEqual(Photo->GetParam(EGolmokPhotoParam::Fov), 110.0, 1e-9));
			Test->TestTrue(TEXT("SetParam(Ev, 0.4)"), Photo->SetParam(EGolmokPhotoParam::Ev, 0.4, Message));
			Test->TestTrue(TEXT("Ev quantized to 0.3333"), FMath::IsNearlyEqual(Photo->GetParam(EGolmokPhotoParam::Ev), 1.0 / 3.0, 1e-6));
			Test->TestTrue(TEXT("SetParam(Fstop, 3.0)"), Photo->SetParam(EGolmokPhotoParam::Fstop, 3.0, Message));
			Test->TestTrue(TEXT("Fstop snapped to 2.8"), FMath::IsNearlyEqual(Photo->GetParam(EGolmokPhotoParam::Fstop), 2.8, 1e-9));
			Photo->Reset();
			Test->TestTrue(TEXT("Reset: fov 65"), FMath::IsNearlyEqual(Photo->GetParam(EGolmokPhotoParam::Fov), 65.0, 1e-9));
			Test->TestTrue(TEXT("Reset: ev 0"), FMath::IsNearlyEqual(Photo->GetParam(EGolmokPhotoParam::Ev), 0.0, 1e-9));
			Test->TestTrue(TEXT("Reset: fstop 2.8"), FMath::IsNearlyEqual(Photo->GetParam(EGolmokPhotoParam::Fstop), 2.8, 1e-9));
			Test->TestTrue(TEXT("Reset: pawn back at the entry pose (1 cm)"), FVector::Dist(Pawn->GetActorLocation(), EntryLocation) <= 1.0);
			Test->TestTrue(TEXT("Exit(test)"), Photo->Exit(TEXT("test")));
			Test->TestFalse(TEXT("game unpaused"), UGameplayStatics::IsGamePaused(World));
			return Next(static_cast<int32>(EClampPhase::Done));
		}
	};

	// ---- MetaJson scenario -------------------------------------------------------------------------------------

	enum class EMetaPhase : int32
	{
		WaitForPawn,
		FirstCapture,
		SecondCapture,
		Done,
	};

	class FMetaJsonScenario : public FPhotoScenarioBase
	{
	public:
		explicit FMetaJsonScenario(FAutomationTestBase* InTest) : FPhotoScenarioBase(InTest) {}

		virtual ~FMetaJsonScenario() override
		{
			DeleteShotFiles(Stems);
		}

		virtual bool Update() override
		{
			UWorld* World = PlayWorld();
			if (!World)
			{
				return NoWorld();
			}
			UGolmokPhotoModeSubsystem* Photo = UGolmokPhotoModeSubsystem::Get(World);
			APlayerController* PC = World->GetFirstPlayerController();
			if (!Photo || !PC)
			{
				return Fail(TEXT("no UGolmokPhotoModeSubsystem / player controller in the PIE world"), 10.0);
			}

			switch (static_cast<EMetaPhase>(Phase))
			{
			case EMetaPhase::WaitForPawn:
			{
				if (Elapsed() < 0.5 || !Cast<AGolmokCharacter>(PC->GetPawn()))
				{
					return Fail(TEXT("no AGolmokCharacter possessed by the first player controller"), 20.0);
				}
				FString Message;
				if (!Test->TestTrue(TEXT("Enter()"), Photo->Enter(Message)))
				{
					Test->AddError(Message);
					return true;
				}
				const GolmokPhotoMath::PhotoMeta M = Photo->BuildMeta(2);
				UGolmokGeoSubsystem* Geo = World->GetSubsystem<UGolmokGeoSubsystem>();
				const bool bOrigin = Geo && Geo->HasOrigin();
				Test->TestTrue(FString::Printf(TEXT("bHasGeo == Geo->HasOrigin() (%s)"), bOrigin ? TEXT("origin") : TEXT("no origin")), M.bHasGeo == bOrigin);
				if (bOrigin)
				{
					Test->TestTrue(TEXT("lat ~ 37.56"), FMath::Abs(M.Lat - 37.56) < 0.05);
					Test->TestTrue(TEXT("lon ~ 126.92"), FMath::Abs(M.Lon - 126.92) < 0.05);
				}
				const bool bNoZone = Photo->Describe().Contains(TEXT("no zone"));
				Test->AddInfo(FString::Printf(TEXT("Describe(): %s"), *Photo->Describe()));
				Test->TestTrue(TEXT("bHasZone matches Describe() (L_Dev: no zone)"), M.bHasZone == !bNoZone);
				const AGolmokTimeOfDay* Tod = AGolmokTimeOfDay::Find(World);
				Test->TestTrue(TEXT("bHasPreset == (CurrentPreset != None)"), M.bHasPreset == (Tod && !Tod->CurrentPreset.IsNone()));
				const AGolmokPhotoCameraPawn* Pawn = Photo->GetPhotoPawn();
				if (Test->TestNotNull(TEXT("photo pawn"), Pawn))
				{
					const FVector L = Pawn->GetActorLocation();
					Test->TestTrue(TEXT("UeLocation == pawn location"), FMath::Abs(M.UeLocation[0] - L.X) < 1e-3 && FMath::Abs(M.UeLocation[1] - L.Y) < 1e-3 && FMath::Abs(M.UeLocation[2] - L.Z) < 1e-3);
				}
				Test->TestFalse(TEXT("bDofEnabled false by default"), M.bDofEnabled);
				Test->TestEqual(TEXT("BuildMeta(2).Multiplier"), M.Multiplier, 2);

				if (!Test->TestTrue(TEXT("Shoot()"), Photo->Shoot(Message)))
				{
					Test->AddError(Message);
					Photo->Exit(TEXT("test"));
					return true;
				}
				Test->AddInfo(Message);
				Test->TestTrue(TEXT("State == Shooting right after Shoot()"), Photo->GetState() == EGolmokPhotoState::Shooting);
				Stems.Add(Photo->GetLastShotPathNoExt());
				return Next(static_cast<int32>(EMetaPhase::FirstCapture));
			}

			case EMetaPhase::FirstCapture:
			{
				if (Photo->IsCapturing())
				{
					return Fail(TEXT("capture window did not close (png poll / 3 s timeout)"), 6.0);
				}
				Test->AddInfo(FString::Printf(TEXT("capture window closed after %.2f s"), Elapsed()));
				Test->TestTrue(TEXT("State == Active after the capture window"), Photo->GetState() == EGolmokPhotoState::Active);
				const FString JsonPath = Photo->GetLastShotPathNoExt() + TEXT(".json");
				if (!Test->TestTrue(TEXT("<stem>.json written"), IFileManager::Get().FileExists(*JsonPath)))
				{
					Photo->Exit(TEXT("test"));
					return true;
				}
				FString Text;
				FFileHelper::LoadFileToString(Text, *JsonPath);
				const TSharedPtr<FJsonObject> Root = ParseJson(Text);
				if (Test->TestTrue(TEXT("meta file parses"), Root.IsValid()))
				{
					const TArray<FString> Keys = KeysInOrder(Root);
					Test->TestEqual(TEXT("15 keys"), Keys.Num(), 15);
					for (int32 i = 0; i < Keys.Num() && i < 15; ++i)
					{
						Test->TestEqual(*FString::Printf(TEXT("key %d"), i), Keys[i], FString(MetaKeys[i]));
					}
					const TSharedPtr<FJsonValue> Version = Root->TryGetField(TEXT("version"));
					Test->TestTrue(TEXT("version == 1"), Version.IsValid() && Version->Type == EJson::Number && Version->AsNumber() == 1.0);
					const int32 Expected = FMath::Min(Photo->ScreenshotMultiplier, Photo->MaxMultiplier);
					const TSharedPtr<FJsonValue> Multiplier = Root->TryGetField(TEXT("multiplier"));
					Test->TestTrue(FString::Printf(TEXT("multiplier == min(ScreenshotMultiplier, MaxMultiplier) = %d"), Expected),
						Multiplier.IsValid() && Multiplier->Type == EJson::Number && static_cast<int32>(Multiplier->AsNumber()) == Expected);
					const TSharedPtr<FJsonValue> Preset = Root->TryGetField(TEXT("preset"));
					Test->TestTrue(TEXT("preset is a string or null"), Preset.IsValid() && (Preset->Type == EJson::String || Preset->Type == EJson::Null));
					const TSharedPtr<FJsonValue> ZoneId = Root->TryGetField(TEXT("zone_id"));
					const TSharedPtr<FJsonValue> ZoneVersion = Root->TryGetField(TEXT("zone_version"));
					Test->TestTrue(TEXT("zone_id / zone_version both null or both set"),
						ZoneId.IsValid() && ZoneVersion.IsValid() && ((ZoneId->Type == EJson::Null) == (ZoneVersion->Type == EJson::Null)));
					const TSharedPtr<FJsonValue> Lon = Root->TryGetField(TEXT("lon"));
					const TSharedPtr<FJsonValue> Lat = Root->TryGetField(TEXT("lat"));
					const TSharedPtr<FJsonValue> Height = Root->TryGetField(TEXT("height_m"));
					Test->TestTrue(TEXT("lon / lat / height_m all null or all numbers"),
						Lon.IsValid() && Lat.IsValid() && Height.IsValid() && (Lon->Type == EJson::Null) == (Lat->Type == EJson::Null) && (Lon->Type == EJson::Null) == (Height->Type == EJson::Null));
					const TSharedPtr<FJsonValue> Dof = Root->TryGetField(TEXT("dof"));
					const TSharedPtr<FJsonObject>* DofObject = nullptr;
					Test->TestTrue(TEXT("dof is an object with enabled / focal_m / fstop"),
						Dof.IsValid() && Dof->TryGetObject(DofObject) && DofObject && DofObject->IsValid() && KeysInOrder(*DofObject) == TArray<FString>({TEXT("enabled"), TEXT("focal_m"), TEXT("fstop")}));
				}

				IConsoleManager::Get().ProcessUserConsoleInput(TEXT("golmok.photo.set fov 40"), *GLog, World);
				Test->TestTrue(TEXT("golmok.photo.set fov 40"), FMath::IsNearlyEqual(Photo->GetParam(EGolmokPhotoParam::Fov), 40.0, 1e-9));

				// Second shot in the same second: a marker <stamp>.json forces the _2 suffix.
				const FString Dir = FPaths::GetPath(Photo->GetLastShotPathNoExt());
				const FString Stamp = FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S"));
				const FString Marker = FPaths::Combine(Dir, Stamp);
				Stems.Add(Marker);
				FFileHelper::SaveStringToFile(TEXT("{}\n"), *(Marker + TEXT(".json")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
				FString Message;
				if (!Test->TestTrue(TEXT("second Shoot()"), Photo->Shoot(Message)))
				{
					Test->AddError(Message);
					Photo->Exit(TEXT("test"));
					return true;
				}
				Stems.Add(Photo->GetLastShotPathNoExt());
				if (FPaths::GetBaseFilename(Photo->GetLastShotPathNoExt()).StartsWith(Stamp))
				{
					Test->TestEqual(TEXT("second shot in the same second gets _2"), Photo->GetLastShotPathNoExt(), Marker + TEXT("_2"));
				}
				else
				{
					Test->AddInfo(TEXT("the clock rolled over between the marker and the second shot; _2 suffix not asserted"));
				}
				// Exit during the capture window is deferred until it closes.
				Test->TestTrue(TEXT("Exit() during a capture returns true"), Photo->Exit(TEXT("test")));
				Test->TestTrue(TEXT("still capturing after the deferred Exit()"), Photo->IsCapturing() && Photo->IsActive());
				return Next(static_cast<int32>(EMetaPhase::SecondCapture));
			}

			case EMetaPhase::SecondCapture:
			{
				if (Photo->IsActive())
				{
					return Fail(TEXT("deferred Exit() did not complete after the capture window"), 6.0);
				}
				Test->TestTrue(TEXT("State == Inactive after the deferred Exit()"), Photo->GetState() == EGolmokPhotoState::Inactive);
				Test->TestFalse(TEXT("game unpaused"), UGameplayStatics::IsGamePaused(World));
				Test->TestTrue(TEXT("second <stem>.json written"), Stems.Num() >= 3 && IFileManager::Get().FileExists(*(Stems.Last() + TEXT(".json"))));
				DeleteShotFiles(Stems);
				return Next(static_cast<int32>(EMetaPhase::Done));
			}

			case EMetaPhase::Done:
			default:
				return true;
			}
		}

	private:
		TArray<FString> Stems;
	};
} // namespace GolmokPhotoTest

// ---- Golmok.Photo.EnterExit -------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokPhotoEnterExitTest, "Golmok.Photo.EnterExit", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokPhotoEnterExitTest::RunTest(const FString& Parameters)
{
	using namespace GolmokPhotoTest;

	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddError(FString::Printf(TEXT("%s is missing. Run golmok.setup_dev_level in the editor first."), DevMap));
		return false;
	}

	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FEnterExitScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

// ---- Golmok.Photo.Clamp -----------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokPhotoClampTest, "Golmok.Photo.Clamp", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokPhotoClampTest::RunTest(const FString& Parameters)
{
	using namespace GolmokPhotoTest;
	using GolmokPhotoMath::Vec3;

	// (a) pure: sphere
	const Vec3 Center = {100.0, 200.0, 300.0};
	Vec3 P = {150.0, 200.0, 300.0};
	TestFalse(TEXT("ClampToSphere: inside unchanged"), GolmokPhotoMath::ClampToSphere(Center, 300.0, P));
	TestTrue(TEXT("ClampToSphere: inside value kept"), P[0] == 150.0 && P[1] == 200.0 && P[2] == 300.0);
	P = {1100.0, 200.0, 300.0};
	TestTrue(TEXT("ClampToSphere: outside moved"), GolmokPhotoMath::ClampToSphere(Center, 300.0, P));
	TestTrue(TEXT("ClampToSphere: outside lands on the surface"), FMath::IsNearlyEqual(P[0], 400.0, 1e-9) && FMath::IsNearlyEqual(P[1], 200.0, 1e-9) && FMath::IsNearlyEqual(P[2], 300.0, 1e-9));
	P = {400.0, 200.0, 300.0};
	TestFalse(TEXT("ClampToSphere: boundary unchanged"), GolmokPhotoMath::ClampToSphere(Center, 300.0, P));
	P = Center;
	TestFalse(TEXT("ClampToSphere: center unchanged"), GolmokPhotoMath::ClampToSphere(Center, 300.0, P));
	P = {150.0, 200.0, 300.0};
	TestTrue(TEXT("ClampToSphere: r = 0 -> center"), GolmokPhotoMath::ClampToSphere(Center, 0.0, P) && P[0] == 100.0 && P[1] == 200.0 && P[2] == 300.0);

	// (a) pure: polygon (4 x 4 m square around the origin, inset 20 cm)
	const double SquareX[4] = {-200.0, 200.0, 200.0, -200.0};
	const double SquareY[4] = {-200.0, -200.0, 200.0, 200.0};
	double X = 300.0;
	double Y = 0.0;
	TestEqual(TEXT("ClampToPolygonXY: outside -> 1"), GolmokPhotoMath::ClampToPolygonXY(SquareX, SquareY, 4, 0.0, 0.0, 20.0, X, Y), 1);
	TestTrue(TEXT("ClampToPolygonXY: boundary point moved 20 cm inward"), FMath::IsNearlyEqual(X, 180.0, 1e-9) && FMath::IsNearlyEqual(Y, 0.0, 1e-9));
	X = 50.0;
	Y = -20.0;
	TestEqual(TEXT("ClampToPolygonXY: inside -> 0"), GolmokPhotoMath::ClampToPolygonXY(SquareX, SquareY, 4, 0.0, 0.0, 20.0, X, Y), 0);
	TestTrue(TEXT("ClampToPolygonXY: inside unchanged"), X == 50.0 && Y == -20.0);
	X = 200.0;
	Y = 0.0;
	const int32 EdgeCode = GolmokPhotoMath::ClampToPolygonXY(SquareX, SquareY, 4, 0.0, 0.0, 20.0, X, Y);
	TestTrue(TEXT("ClampToPolygonXY: point on the boundary -> inside (0 or 1)"), (EdgeCode == 0 || EdgeCode == 1) && X <= 200.0 + 1e-9 && FMath::IsNearlyEqual(Y, 0.0, 1e-9));
	// concave L: the nearest boundary point of (150, 150) is the horizontal edge y = 100 (tie with x = 100 -> lowest edge index);
	// nudged toward an anchor in the vertical arm it leaves the ring -> 2, Out = Q.
	const double LX[6] = {0.0, 400.0, 400.0, 100.0, 100.0, 0.0};
	const double LY[6] = {0.0, 0.0, 100.0, 100.0, 400.0, 400.0};
	X = 150.0;
	Y = 150.0;
	TestEqual(TEXT("ClampToPolygonXY: concave corner, inset point outside -> 2"), GolmokPhotoMath::ClampToPolygonXY(LX, LY, 6, 50.0, 350.0, 20.0, X, Y), 2);
	TestTrue(TEXT("ClampToPolygonXY: code 2 leaves Q on the boundary"), FMath::IsNearlyEqual(X, 150.0, 1e-9) && FMath::IsNearlyEqual(Y, 100.0, 1e-9));
	X = 300.0;
	Y = 0.0;
	TestEqual(TEXT("ClampToPolygonXY: N < 3 -> 0"), GolmokPhotoMath::ClampToPolygonXY(SquareX, SquareY, 2, 0.0, 0.0, 20.0, X, Y), 0);

	// (a) pure: Constrain (polygon wins over the sphere; both violated and not repairable -> -1)
	GolmokPhotoMath::Constraint C;
	C.Anchor = {0.0, 0.0, 0.0};
	C.RadiusCm = 300.0;
	C.InsetCm = 20.0;
	C.Xs = SquareX;
	C.Ys = SquareY;
	C.N = 4;
	Vec3 Out = {-1.0, -1.0, -1.0};
	TestEqual(TEXT("Constrain: sphere then polygon -> 3"), GolmokPhotoMath::Constrain(C, Vec3{1000.0, 0.0, 0.0}, Out), 3);
	TestTrue(TEXT("Constrain: polygon result (180, 0, 0)"), FMath::IsNearlyEqual(Out[0], 180.0, 1e-9) && FMath::IsNearlyEqual(Out[1], 0.0, 1e-9) && FMath::IsNearlyEqual(Out[2], 0.0, 1e-9));
	TestEqual(TEXT("Constrain: inside both -> 0"), GolmokPhotoMath::Constrain(C, Vec3{10.0, 20.0, 30.0}, Out), 0);
	TestEqual(TEXT("Constrain: sphere only -> 1"), GolmokPhotoMath::Constrain(C, Vec3{0.0, 0.0, 1000.0}, Out), 1);
	TestTrue(TEXT("Constrain: sphere result (0, 0, 300)"), FMath::IsNearlyEqual(Out[2], 300.0, 1e-9));
	// A ring whose boundary nearest to the clamped point is farther from the anchor than the radius: the nudged
	// point is outside the ring (and Q outside the sphere) -> rejected, Out untouched.
	const double ArmX[6] = {-1000.0, -1.0, -1.0, 1000.0, 1000.0, -1000.0};
	const double ArmY[6] = {-1000.0, -1000.0, 290.0, 290.0, 1000.0, 1000.0};
	GolmokPhotoMath::Constraint Arm;
	Arm.Anchor = {-5.0, 0.0, 0.0};
	Arm.RadiusCm = 300.0;
	Arm.InsetCm = 20.0;
	Arm.Xs = ArmX;
	Arm.Ys = ArmY;
	Arm.N = 6;
	Out = {-1.0, -1.0, -1.0};
	TestEqual(TEXT("Constrain: sphere and polygon both violated, no repair -> -1"), GolmokPhotoMath::Constrain(Arm, Vec3{2950.0, 0.0, 0.0}, Out), -1);
	TestTrue(TEXT("Constrain: rejected leaves Out untouched"), Out[0] == -1.0 && Out[1] == -1.0 && Out[2] == -1.0);
	C.N = 0;
	TestEqual(TEXT("Constrain: no polygon -> sphere only"), GolmokPhotoMath::Constrain(C, Vec3{1000.0, 0.0, 0.0}, Out), 1);

	// (a) pure: parameters
	const double Third = 1.0 / 3.0;
	double Ev = 0.0;
	for (int32 i = 0; i < 18; ++i)
	{
		Ev = GolmokPhotoMath::StepLinear(Ev, -3.0, 3.0, Third, +1);
	}
	TestTrue(TEXT("Quantize: 18 x +1/3 EV clamps at +3"), Ev == 3.0);
	for (int32 i = 0; i < 18; ++i)
	{
		Ev = GolmokPhotoMath::StepLinear(Ev, -3.0, 3.0, Third, -1);
	}
	TestTrue(TEXT("Quantize: 18 x -1/3 EV clamps at -3"), Ev == -3.0);
	Ev = 0.0;
	for (int32 i = 0; i < 9; ++i)
	{
		Ev = GolmokPhotoMath::StepLinear(Ev, -3.0, 3.0, Third, +1);
	}
	for (int32 i = 0; i < 9; ++i)
	{
		Ev = GolmokPhotoMath::StepLinear(Ev, -3.0, 3.0, Third, -1);
	}
	TestTrue(TEXT("Quantize: 9 up + 9 down is exactly 0.0"), Ev == 0.0);
	TestTrue(TEXT("Quantize(0.4) on the 1/3 grid"), FMath::IsNearlyEqual(GolmokPhotoMath::Quantize(0.4, -3.0, 3.0, Third), Third, 1e-12));

	double Focus = 0.3;
	int32 Steps = 0;
	while (Focus < 50.0 && Steps < 40)
	{
		Focus = GolmokPhotoMath::StepGeometric(Focus, 0.3, 50.0, 1.25, +1);
		TestTrue(TEXT("StepGeometric: 3 decimals"), FMath::IsNearlyEqual(Focus * 1000.0, FMath::RoundToDouble(Focus * 1000.0), 1e-6));
		++Steps;
	}
	TestEqual(TEXT("StepGeometric: 0.3 -> 50 in ceil(ln(50/0.3)/ln 1.25) = 23 steps"), Steps, 23);
	TestTrue(TEXT("StepGeometric: clamped at 50"), Focus == 50.0);
	for (int32 i = 0; i < 30; ++i)
	{
		Focus = GolmokPhotoMath::StepGeometric(Focus, 0.3, 50.0, 1.25, -1);
	}
	TestTrue(TEXT("StepGeometric: back at 0.3"), FMath::IsNearlyEqual(Focus, 0.3, 1e-9));
	TestTrue(TEXT("StepGeometric: dir 0 clamps and rounds"), FMath::IsNearlyEqual(GolmokPhotoMath::StepGeometric(0.12345, 0.3, 50.0, 1.25, 0), 0.3, 1e-9));

	const std::vector<double> Fstops = {1.4, 2.0, 2.8, 4.0, 5.6, 8.0, 11.0, 16.0};
	double Fstop = 2.8;
	const double UpSteps[6] = {4.0, 5.6, 8.0, 11.0, 16.0, 16.0};
	for (int32 i = 0; i < 6; ++i)
	{
		Fstop = GolmokPhotoMath::StepTable(Fstops, Fstop, +1);
		TestTrue(FString::Printf(TEXT("StepTable up %d -> %.1f"), i, UpSteps[i]), Fstop == UpSteps[i]);
	}
	TestTrue(TEXT("StepTable: 1.4 stays at the lower end"), GolmokPhotoMath::StepTable(Fstops, 1.4, -1) == 1.4);
	TestTrue(TEXT("StepTable: 3.0 -> nearest 2.8, up -> 4"), GolmokPhotoMath::StepTable(Fstops, 3.0, +1) == 4.0);
	TestEqual(TEXT("NearestIndex(3.0) == 2"), static_cast<int32>(GolmokPhotoMath::NearestIndex(Fstops, 3.0)), 2);
	TestEqual(TEXT("NearestIndex tie -> lower index"), static_cast<int32>(GolmokPhotoMath::NearestIndex(Fstops, 1.7)), 0);

	TestTrue(TEXT("WrapDeg180(180) == 180"), GolmokPhotoMath::WrapDeg180(180.0) == 180.0);
	TestTrue(TEXT("WrapDeg180(181) == -179"), FMath::IsNearlyEqual(GolmokPhotoMath::WrapDeg180(181.0), -179.0, 1e-9));
	TestTrue(TEXT("WrapDeg180(-180) == 180"), GolmokPhotoMath::WrapDeg180(-180.0) == 180.0);
	TestTrue(TEXT("WrapDeg180(720) == 0"), FMath::IsNearlyEqual(GolmokPhotoMath::WrapDeg180(720.0), 0.0, 1e-9));
	TestTrue(TEXT("FovToFocalMm(65) ~ 28.2"), FMath::Abs(GolmokPhotoMath::FovToFocalMm(65.0) - 28.2) < 0.1);
	TestTrue(TEXT("ClampParam(NaN) -> lo"), GolmokPhotoMath::ClampParam(std::nan(""), 20.0, 110.0) == 20.0);
	TestTrue(TEXT("ClampParam swaps lo > hi"), GolmokPhotoMath::ClampParam(200.0, 110.0, 20.0) == 110.0);

	// (b)-(d) PIE
	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddError(FString::Printf(TEXT("%s is missing. Run golmok.setup_dev_level in the editor first."), DevMap));
		return false;
	}
	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FClampScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

// ---- Golmok.Photo.MetaJson --------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGolmokPhotoMetaJsonTest, "Golmok.Photo.MetaJson", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FGolmokPhotoMetaJsonTest::RunTest(const FString& Parameters)
{
	using namespace GolmokPhotoTest;

	// (a) pure: the design section 2-2 example byte for byte
	const GolmokPhotoMath::PhotoMeta Example = ExampleMeta();
	TestEqual(TEXT("FormatPhotoMetaJson matches the design section 2-2 example"), FromStd(GolmokPhotoMath::FormatPhotoMetaJson(Example)), FString(ExampleJson));

	// null groups (preset / zone / geo) and string escapes, re-parsed with FJsonSerializer (TryGetField, UE 5.8 keys)
	GolmokPhotoMath::PhotoMeta Nulls = Example;
	Nulls.bHasPreset = false;
	Nulls.bHasZone = false;
	Nulls.bHasGeo = false;
	const FString NullText = FromStd(GolmokPhotoMath::FormatPhotoMetaJson(Nulls));
	TestTrue(TEXT("preset null"), NullText.Contains(TEXT("  \"preset\": null,\n")));
	TestTrue(TEXT("zone null pair"), NullText.Contains(TEXT("  \"zone_id\": null,\n  \"zone_version\": null,\n")));
	TestTrue(TEXT("geo null triple"), NullText.Contains(TEXT("  \"lon\": null,\n  \"lat\": null,\n  \"height_m\": null,\n")));
	const TSharedPtr<FJsonObject> NullRoot = ParseJson(NullText);
	if (TestTrue(TEXT("null variant parses"), NullRoot.IsValid()))
	{
		const TArray<FString> NullKeys = KeysInOrder(NullRoot);
		TestEqual(TEXT("null variant keeps 15 keys"), NullKeys.Num(), 15);
		for (int32 i = 0; i < NullKeys.Num() && i < 15; ++i)
		{
			TestEqual(*FString::Printf(TEXT("null variant key %d"), i), NullKeys[i], FString(MetaKeys[i]));
		}
		const TSharedPtr<FJsonValue> Preset = NullRoot->TryGetField(TEXT("preset"));
		TestTrue(TEXT("preset parses as null"), Preset.IsValid() && Preset->Type == EJson::Null);
		const TSharedPtr<FJsonValue> ZoneVersion = NullRoot->TryGetField(TEXT("zone_version"));
		TestTrue(TEXT("zone_version parses as null"), ZoneVersion.IsValid() && ZoneVersion->Type == EJson::Null);
		const TSharedPtr<FJsonValue> Fov = NullRoot->TryGetField(TEXT("fov"));
		TestTrue(TEXT("fov parses as 65"), Fov.IsValid() && Fov->Type == EJson::Number && Fov->AsNumber() == 65.0);
		const TSharedPtr<FJsonValue> Hidden = NullRoot->TryGetField(TEXT("character_hidden"));
		TestTrue(TEXT("character_hidden parses as false"), Hidden.IsValid() && Hidden->Type == EJson::Boolean && !Hidden->AsBool());
	}
	GolmokPhotoMath::PhotoMeta Escaped = Example;
	const FString OddZone = TEXT("z_\"quoted\"_\\back\\_골목");
	Escaped.ZoneId = ToStd(OddZone);
	Escaped.Preset = ToStd(TEXT("tab\there"));
	const FString EscapedText = FromStd(GolmokPhotoMath::FormatPhotoMetaJson(Escaped));
	const TSharedPtr<FJsonObject> EscapedRoot = ParseJson(EscapedText);
	if (TestTrue(TEXT("escaped variant parses"), EscapedRoot.IsValid()))
	{
		const TSharedPtr<FJsonValue> ZoneId = EscapedRoot->TryGetField(TEXT("zone_id"));
		TestTrue(TEXT("zone_id round-trips quotes, backslashes and Hangul"), ZoneId.IsValid() && ZoneId->Type == EJson::String && ZoneId->AsString() == OddZone);
		const TSharedPtr<FJsonValue> Preset = EscapedRoot->TryGetField(TEXT("preset"));
		TestTrue(TEXT("preset round-trips a tab"), Preset.IsValid() && Preset->AsString() == TEXT("tab\there"));
	}

	// (a) pure: photo.json parser (the real file loads; the section 2-1 violations name their location)
	const FString ConfigPath = GetDefault<UGolmokPhotoModeSubsystem>()->ResolveConfigPath();
	FGolmokPhotoConfig Loaded;
	FString Error;
	if (!TestTrue(TEXT("LoadConfigFile(photo.json)"), GolmokPhotoJson::LoadConfigFile(ConfigPath, Loaded, Error)))
	{
		AddError(FString::Printf(TEXT("%s: %s"), *ConfigPath, *Error));
		return false;
	}
	TestTrue(TEXT("fov 20..110"), Loaded.Spec(EGolmokPhotoParam::Fov).Min == 20.0 && Loaded.Spec(EGolmokPhotoParam::Fov).Max == 110.0);
	TestTrue(TEXT("ev -3..3"), Loaded.Spec(EGolmokPhotoParam::Ev).Min == -3.0 && Loaded.Spec(EGolmokPhotoParam::Ev).Max == 3.0);
	TestTrue(TEXT("focus 0.3..50 (geometric)"), Loaded.Spec(EGolmokPhotoParam::Focus).Min == 0.3 && Loaded.Spec(EGolmokPhotoParam::Focus).Max == 50.0 && Loaded.Spec(EGolmokPhotoParam::Focus).IsGeometric());
	TestTrue(TEXT("fstop 1.4..16 (table)"), Loaded.Spec(EGolmokPhotoParam::Fstop).IsTable() && Loaded.Spec(EGolmokPhotoParam::Fstop).Values[0] == 1.4 && Loaded.Spec(EGolmokPhotoParam::Fstop).Values.Last() == 16.0);
	TestTrue(TEXT("roll -15..15"), Loaded.Spec(EGolmokPhotoParam::Roll).Min == -15.0 && Loaded.Spec(EGolmokPhotoParam::Roll).Max == 15.0);
	TestTrue(TEXT("defaults fov 65 / fstop 2.8, dof off"), Loaded.Spec(EGolmokPhotoParam::Fov).Default == 65.0 && Loaded.Spec(EGolmokPhotoParam::Fstop).Default == 2.8 && !Loaded.bDofDefault);
	TestTrue(TEXT("hints 1..4 lines"), Loaded.HintsKeyboard.Num() >= 1 && Loaded.HintsKeyboard.Num() <= 4 && Loaded.HintsGamepad.Num() >= 1 && Loaded.HintsGamepad.Num() <= 4);

	FString ConfigText;
	FFileHelper::LoadFileToString(ConfigText, *ConfigPath);
	auto ExpectParseError = [this, &ConfigText](const TCHAR* Case, const TCHAR* Where, TFunctionRef<void(const TSharedPtr<FJsonObject>&)> Mutate)
	{
		const TSharedPtr<FJsonObject> Root = ParseJson(ConfigText);
		if (!TestTrue(FString::Printf(TEXT("%s: photo.json parses"), Case), Root.IsValid()))
		{
			return;
		}
		Mutate(Root);
		FGolmokPhotoConfig Parsed;
		FString ParseError;
		TestFalse(FString::Printf(TEXT("%s rejected"), Case), GolmokPhotoJson::ParseConfigText(SerializeJson(Root), Parsed, ParseError));
		TestTrue(FString::Printf(TEXT("%s error is prefixed 'photo.json:' (%s)"), Case, *ParseError), ParseError.StartsWith(TEXT("photo.json: ")));
		TestTrue(FString::Printf(TEXT("%s error names '%s' (%s)"), Case, Where, *ParseError), ParseError.Contains(Where));
	};
	ExpectParseError(TEXT("schema_version 2"), TEXT("schema_version"), [](const TSharedPtr<FJsonObject>& Root) { Root->SetNumberField(TEXT("schema_version"), 2.0); });
	ExpectParseError(TEXT("params.fov missing"), TEXT("params"), [](const TSharedPtr<FJsonObject>& Root) { Root->GetObjectField(TEXT("params"))->RemoveField(TEXT("fov")); });
	ExpectParseError(TEXT("default > max"), TEXT("params.fov"),
		[](const TSharedPtr<FJsonObject>& Root) { Root->GetObjectField(TEXT("params"))->GetObjectField(TEXT("fov"))->SetNumberField(TEXT("default"), 200.0); });
	ExpectParseError(TEXT("step and step_ratio together"), TEXT("params.fov"),
		[](const TSharedPtr<FJsonObject>& Root) { Root->GetObjectField(TEXT("params"))->GetObjectField(TEXT("fov"))->SetNumberField(TEXT("step_ratio"), 1.5); });
	ExpectParseError(TEXT("values descending"), TEXT("params.fstop"), [](const TSharedPtr<FJsonObject>& Root) {
		TArray<TSharedPtr<FJsonValue>> Descending;
		for (const double V : {16.0, 11.0, 8.0, 5.6, 4.0, 2.8, 2.0, 1.4})
		{
			Descending.Add(MakeShared<FJsonValueNumber>(V));
		}
		Root->GetObjectField(TEXT("params"))->GetObjectField(TEXT("fstop"))->SetArrayField(TEXT("values"), Descending);
	});
	ExpectParseError(TEXT("unknown top-level key"), TEXT("notes"), [](const TSharedPtr<FJsonObject>& Root) { Root->SetStringField(TEXT("notes"), TEXT("x")); });
	ExpectParseError(TEXT("hints.keyboard 5 lines"), TEXT("hints.keyboard"), [](const TSharedPtr<FJsonObject>& Root) {
		TArray<TSharedPtr<FJsonValue>> Lines;
		for (int32 i = 0; i < 5; ++i)
		{
			Lines.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("line %d"), i)));
		}
		Root->GetObjectField(TEXT("hints"))->SetArrayField(TEXT("keyboard"), Lines);
	});
	ExpectParseError(TEXT("bool where a number is required"), TEXT("params.fov.default"),
		[](const TSharedPtr<FJsonObject>& Root) { Root->GetObjectField(TEXT("params"))->GetObjectField(TEXT("fov"))->SetBoolField(TEXT("default"), true); });
	FGolmokPhotoConfig Bad;
	TestFalse(TEXT("truncated text rejected"), GolmokPhotoJson::ParseConfigText(TEXT("{\"schema_version\": 1, \"params\": {"), Bad, Error));
	TestTrue(TEXT("truncated text error names root"), Error.Contains(TEXT("root")));

	// (b) PIE
	if (!FPackageName::DoesPackageExist(DevMap))
	{
		AddError(FString::Printf(TEXT("%s is missing. Run golmok.setup_dev_level in the editor first."), DevMap));
		return false;
	}
	ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(DevMap));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FMetaJsonScenario(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

#endif
