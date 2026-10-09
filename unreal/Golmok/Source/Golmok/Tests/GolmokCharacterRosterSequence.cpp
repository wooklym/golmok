// Opt-in InputKey/RHI capture aid; never a real-keyboard/video or animation-quality verdict.
#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"
#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
#include "Camera/CameraComponent.h"
#include "Characters/GolmokCharacterSubsystem.h"
#include "Components/CapsuleComponent.h"
#include "Debug/GolmokDebugSubsystem.h"
#include "Editor.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "HAL/FileManager.h"
#include "InputCoreTypes.h"
#include "InputKeyEventArgs.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Misc/App.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/PackageName.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "DynamicRHI.h"
#include "Player/GolmokCharacter.h"
#include "Portals/GolmokPortal.h"
#include "Tests/AutomationEditorCommon.h"
#include "UnrealClient.h"
#include "Zones/GolmokZoneSubsystem.h"
namespace GolmokCharacterRosterSequence
{
class FSequence : public IAutomationLatentCommand
{
public:
 FSequence(FAutomationTestBase* InTest, FString InId, int32 InCourse)
 : Test(InTest), Id(MoveTemp(InId)), Course(InCourse) {}
 ~FSequence() override { Release(); if (bClockChanged) { FApp::SetFixedDeltaTime(OldDelta); FApp::SetUseFixedTimeStep(bOldFixed); } }
 bool Update() override
 {
  if (!bStarted) { WallStart=FPlatformTime::Seconds(); bStarted=true; }
  const double WallElapsed=FPlatformTime::Seconds()-WallStart;
  if (WallElapsed > 300) return Fail(*FString::Printf(TEXT("sequence timeout after %.2fs (course limit 300s)"),WallElapsed));
  UWorld* World=GEditor?GEditor->PlayWorld.Get():nullptr;
  PC=World?World->GetFirstPlayerController():nullptr;
  Character=PC.IsValid()?Cast<AGolmokCharacter>(PC->GetPawn()):nullptr;
  if (!Character.IsValid() || World->GetTimeSeconds()<.6) return false;
  Now=World->GetTimeSeconds();
  auto* Roster=World->GetSubsystem<UGolmokCharacterSubsystem>();
  auto* Zones=World->GetSubsystem<UGolmokZoneSubsystem>();
  auto* Portal=Course==2?AGolmokPortal::FindPortal(World,TEXT("door_1")):nullptr;
  if (Phase==0)
  {
   OldDelta=FApp::GetFixedDeltaTime(); bOldFixed=FApp::UseFixedTimeStep(); bClockChanged=true;
   FApp::SetFixedDeltaTime(1.0/60.0); FApp::SetUseFixedTimeStep(true);
   Folder=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Automation/WP18T2Sequence")/(Id+FString::Printf(TEXT("_course%d_"),Course)+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
   IFileManager::Get().MakeDirectory(*Folder,true);
   Manifest=TEXT("ENGINE INPUT DRIVER RENDER EVIDENCE; not real keyboard/video; no hitch/fps verdict\nfixed simulation dt=1/60; screenshot requests at 0.1s sim intervals; image resolved on render frame\n");
   bFraming=FParse::Param(FCommandLine::Get(),TEXT("GolmokCharacterFraming"));
   Manifest+=FString::Printf(TEXT("id=%s course=%d (0=walk3s/run3s,1=L_Dev stairs,2=portal roundtrip) camera=%s\n"),*Id,Course,bFraming?TEXT("roster boom pitch-15"):TEXT("diagnostic boom1.5 pitch-10"));
   if(bFraming) Manifest+=TEXT("T23: course0 overrides legacy description: S walking toward camera for 6s, no run; roster boom, pitch -15.\n");
   Release(); FString Message;
   if (!Roster || !Roster->SelectCharacter(Id,Message)) return Fail(*Message);
   if(!bFraming) Character->GetCameraBoom()->TargetArmLength*=1.5;
   if(auto* Debug=World->GetSubsystem<UGolmokDebugSubsystem>()) Debug->SetHudVisible(false);
   auto* Light=AGolmokTimeOfDay::Find(World);
   const bool bLightApplied=Light && Light->ApplyPreset(TEXT("clear_noon"),true);
   Manifest+=FString::Printf(TEXT("environment rhi=%s preset=clear_noon applied=%s arm_length=%.3f command_line=%s\n"),GDynamicRHI?GDynamicRHI->GetName():TEXT("none"),bLightApplied?TEXT("true"):TEXT("false"),Character->GetCameraBoom()->TargetArmLength,FCommandLine::Get());
   if(!bLightApplied) return Fail(TEXT("clear_noon lighting preset not applied"));
   if(Course==2 && (!Zones || !Zones->RequestLoad(TEXT("z_synthetic_001"),true,Message))) return Fail(*Message);
   Phase=1; PhaseAt=Now; return false;
  }
  if(Phase==1)
  {
   if(Course==2 && !Portal) return false;
   FVector Position=Course==0?FVector(-6500,-3000,0):FVector(400,-1500,0);
   FRotator Rotation(0,0,0);
   if(Course==2){ Position=Portal->GetActorLocation()-Portal->GetActorForwardVector()*140; Rotation=Portal->GetActorRotation(); }
   Position.Z+=Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+3;
   Character->GetCharacterMovement()->StopMovementImmediately();
   Character->SetActorLocation(Position,false,nullptr,ETeleportType::TeleportPhysics);
   Character->SetActorRotation(Rotation); Rotation.Pitch=bFraming?-15:-10; PC->SetControlRotation(Rotation);
   Manifest+=FString::Printf(TEXT("setup teleport sim=%.4f position=%s; no teleports during traversal\n"),Now,*Position.ToString());
   Phase=2; PhaseAt=Now; return false;
  }
  if(Phase==2)
  {
   if(Now-PhaseAt<3 || Character->GetCharacterMovement()->IsFalling()) return false;
   if(Course==2 && (!Portal || !Portal->IsSublevelVisible())) return false;
   Start=Now; NextCapture=.1; Key(bFraming && Course==0?EKeys::S:EKeys::W,true); Phase=3; return false;
  }
  if(Phase==4)
  {
   for(const FString& File:Files) if(IFileManager::Get().FileSize(*File)<=0) return false;
   const FString AssertionStatus=AssertionCount==0?FString(TEXT("none")):FString::Printf(TEXT("%s(%d/%d)"),bAssertionsPassed?TEXT("PASS"):TEXT("FAIL"),PassedCount,AssertionCount);
   Manifest+=FString::Printf(TEXT("COMPLETE frames=%d duration=%.4f assertions=%s\n"),Files.Num(),End-Start,*AssertionStatus);
   Save(); Test->AddInfo(TEXT("SEQUENCE ")+Folder); return true;
  }
  const double Elapsed=Now-Start;
  if(Course==0 && !bFraming && !bShift && Elapsed>=3){Key(EKeys::LeftShift,true); bShift=true;}
  if(Course==1 && !bReturn && Character->GetActorLocation().X>=900)
  {
   Check(TEXT("stairs reached landing"),FMath::Abs(Feet()-170)<4,Feet());
   Key(EKeys::W,false); Key(EKeys::S,true); bReturn=true;
  }
  if(Course==1 && bReturn && !bStopped && Character->GetActorLocation().X<=380 && !Character->GetCharacterMovement()->IsFalling())
  {Key(EKeys::S,false); bStopped=true; Check(TEXT("stairs returned to ground"),FMath::Abs(Feet())<4,Feet());}
  if(Course==2)
  {
   if(!Portal) return Fail(TEXT("portal disappeared"));
   if(Portal->bPlayerInside) bEntered=true;
   if(!bReturn && Elapsed>=1.6){Key(EKeys::W,false); Key(EKeys::S,true); bReturn=true;}
   if(bEntered && bReturn && !Portal->bPlayerInside) bExited=true;
   if(!bStopped && Elapsed>=4.8){Key(EKeys::S,false); bStopped=true;}
  }
  if(Elapsed+0.001>=NextCapture)
  {
   if(Elapsed-NextCapture>.04) return Fail(TEXT("simulation missed 0.1s capture cadence"));
   FString File=Folder/FString::Printf(TEXT("%s_course%d_sim%08.3f.png"),*Id,Course,Elapsed);
   FScreenshotRequest::RequestScreenshot(File,false,false,false,FIntRect(),true);
   Files.Add(File);
   Manifest+=FString::Printf(TEXT("frame sim=%.4f elapsed=%.4f id=%s course=%d position=%s velocity=%s file=%s\n"),Now,Elapsed,*Id,Course,*Character->GetActorLocation().ToString(),*Character->GetVelocity().ToString(),*FPaths::GetCleanFilename(File));
   Manifest+=FString::Printf(TEXT("state sim=%.4f feet=%.3f portal_present=%d inside=%d entered=%d exited=%d\n"),Now,Feet(),Portal?1:0,Portal && Portal->bPlayerInside?1:0,bEntered?1:0,bExited?1:0);
   NextCapture+=.1; Save();
  }
  if((Course==0 && Elapsed>=6) || (Course==1 && bStopped && Elapsed>=6) || (Course==2 && Elapsed>=6))
  {
   if(Course==2){Check(TEXT("portal inward on foot"),bEntered,bEntered?1.0:0.0);Check(TEXT("portal outward on foot"),bExited,bExited?1.0:0.0);}
   Release(); End=Now; Phase=4; return false;
  }
  return false;
 }
private:
 void Check(const TCHAR* Label,bool Passed,double Value){++AssertionCount;if(Passed) ++PassedCount;Test->TestTrue(Label,Passed);bAssertionsPassed &= Passed;Manifest+=FString::Printf(TEXT("assert sim=%.4f result=%s label=%s value=%.3f\n"),Now,Passed?TEXT("PASS"):TEXT("FAIL"),Label,Value);}
 void Save(){if(Folder.IsEmpty()) return; FFileHelper::SaveStringToFile(Manifest,*(Folder/TEXT("capture.txt")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);}
 double Feet()const{return Character->GetActorLocation().Z-Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();}
 void Key(const FKey& K,bool Down){if(PC.IsValid()) PC->InputKey(FInputKeyEventArgs::CreateSimulated(K,Down?IE_Pressed:IE_Released,Down?1.f:0.f));Manifest+=FString::Printf(TEXT("input sim=%.4f key=%s %s\n"),Now,*K.ToString(),Down?TEXT("down"):TEXT("up"));}
 void Release(){Key(EKeys::W,false);Key(EKeys::S,false);Key(EKeys::LeftShift,false);}
 bool Fail(const TCHAR* Message){Test->AddError(FString::Printf(TEXT("%s course%d phase%d: %s"),*Id,Course,Phase,Message));Release();Save();return true;}
 FAutomationTestBase* Test; FString Id,Folder,Manifest; int32 Course,Phase=0,AssertionCount=0,PassedCount=0; double WallStart=0,Now=0,Start=0,End=0,PhaseAt=0,NextCapture=0,OldDelta=0;
 bool bFraming=false;
 bool bStarted=false,bAssertionsPassed=true,bOldFixed=false,bClockChanged=false,bShift=false,bReturn=false,bStopped=false,bEntered=false,bExited=false;
 TWeakObjectPtr<APlayerController> PC; TWeakObjectPtr<AGolmokCharacter> Character; TArray<FString> Files;
};
void Enqueue(FAutomationTestBase* Test)
{
 // Check all fixtures before queuing any PIE or map loads.
 bool bMissingFixture=false;
 for(const TCHAR* Map : {TEXT("/Game/Golmok/Maps/L_Dev"), TEXT("/Game/Golmok/Maps/L_ZoneTest"), TEXT("/Game/Golmok/Zones/z_synthetic_001_interior/v1/L_z_synthetic_001_interior")})
 {
  if(!FPackageName::DoesPackageExist(Map))
  {
   Test->AddError(FString::Printf(TEXT("Sequence fixture missing: %s; prepare L_Dev and synthetic_zone first."),Map));
   bMissingFixture=true;
  }
 }
 if(bMissingFixture) return;
 for(const TCHAR* Id:{TEXT("manny"),TEXT("proxy135"),TEXT("proxy110"),TEXT("quinn")}) for(int32 Course=0;Course<3;++Course)
 {
  if(FString(Id)==TEXT("manny") && !FParse::Param(FCommandLine::Get(),TEXT("GolmokCharacterFraming"))) continue;
  ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(Course==2?TEXT("/Game/Golmok/Maps/L_ZoneTest"):TEXT("/Game/Golmok/Maps/L_Dev")));
  ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
  ADD_LATENT_AUTOMATION_COMMAND(FSequence(Test,Id,Course));
  ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
 }
}
}
#endif
