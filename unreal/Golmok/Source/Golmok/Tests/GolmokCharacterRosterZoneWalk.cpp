// Opt-in WP-06 functional evidence: real-time PIE, InputKey and CharacterMovement; no traversal teleports.
#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"
#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
#include "Components/CapsuleComponent.h"
#include "Debug/GolmokDebugSubsystem.h"
#include "Editor.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerStart.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "EngineUtils.h"
#include "HAL/FileManager.h"
#include "InputKeyEventArgs.h"
#include "Lighting/GolmokTimeOfDay.h"
#include "Misc/CommandLine.h"
#include "Misc/App.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Player/GolmokCharacter.h"
#include "Portals/GolmokPortal.h"
#include "Tests/AutomationEditorCommon.h"
#include "UnrealClient.h"
#include "Zones/GolmokZone.h"
#include "Zones/GolmokZoneSubsystem.h"

namespace GolmokCharacterRosterZoneWalk
{
struct FStep
{
 FName Name;
 FVector2D Target;
 double Wait;
 bool bPush;
};
class FWalk : public IAutomationLatentCommand
{
public:
 FWalk(FAutomationTestBase* InTest, int32 InCourse) : Test(InTest), Course(InCourse) {}
 ~FWalk() override { Release(); }
 bool Update() override
 {
  const double Wall=FPlatformTime::Seconds();
  if(!Started) { Started=Wall; }
  if(Wall-Started>240) return Fail(TEXT("240s wall timeout"));
  UWorld* World=GEditor?GEditor->PlayWorld.Get():nullptr;
  PC=World?World->GetFirstPlayerController():nullptr;
  Character=PC.IsValid()?Cast<AGolmokCharacter>(PC->GetPawn()):nullptr;
  if(!Character.IsValid() || World->GetTimeSeconds()<1) return false;
  auto* Zones=World->GetSubsystem<UGolmokZoneSubsystem>();
  auto* Zone=Zones?Zones->FindZone(TEXT("z_synthetic_scan_001")):nullptr;
  auto* Debug=World->GetSubsystem<UGolmokDebugSubsystem>();
  auto* Portal=AGolmokPortal::FindPortal(World,TEXT("door_1"));
  if(!Zone || !Debug || !Portal) return false;
  Now=World->GetTimeSeconds();
  if(!bPlaced)
  {
   if(Zones->NumDiscovered()!=0) return Fail(TEXT("Unrelated indexed zones contaminate fixture; launch with bDiscoverFromIndex=False INI override"));
   APlayerStart* Start=nullptr;
   for(TActorIterator<APlayerStart> It(World);It;++It){Start=*It;break;}
   if(!Start) return Fail(TEXT("PlayerStart missing"));
   const FVector Expected=Zone->GetActorTransform().TransformPosition(FVector(0,-200,150));
   if(FVector::Dist(Start->GetActorLocation(),Expected)>5) return Fail(TEXT("PlayerStart differs from WP-06 expected.json; follow runbook section3 before running"));
   if(FApp::UseFixedTimeStep()) return Fail(TEXT("ZoneWalk requires real-time PIE, not a fixed time step"));
   Character->GetCharacterMovement()->StopMovementImmediately();
   Character->SetActorLocation(Start->GetActorLocation(),false,nullptr,ETeleportType::TeleportPhysics);
   PC->SetControlRotation(Start->GetActorRotation());
   bPlaced=true; PlacedAt=Now;return false;
  }
  if(Now-PlacedAt<2) return false;
  const FVector Local=Zone->GetActorTransform().InverseTransformPosition(Character->GetActorLocation());
  Pos=FVector(Local.X,-Local.Y,Local.Z);
  if(!bReady)
  {
   Folder=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Automation/WP06ZoneWalk")/(FString::Printf(TEXT("course%d_"),Course)+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
   IFileManager::Get().MakeDirectory(*Folder,true);
   Log=TEXT("InputKey driver; real-time PIE; one initial teleport to PlayerStart; no traversal teleport; no fixed dt; units cm, local ENU\n");
   Log+=FString::Printf(TEXT("course=%d initial_world=%s local=%s\n"),Course,*Character->GetActorLocation().ToString(),*Pos.ToString());
   for(const auto& Line:Debug->GetHudLines()) Log+=TEXT("HUD ")+Line+TEXT("\n");
   Debug->SetHudVisible(true);
   auto* Light=AGolmokTimeOfDay::Find(World);
   if(!Light || !Light->ApplyPreset(TEXT("clear_noon"),true)) return Fail(TEXT("clear_noon unavailable"));
   if(Course<3)
   {
    const double X=Course==0?-800:Course==1?-1050:1150;
    Steps={{TEXT("south_lane"),{0,100},.3,false},{TEXT("align_obstacle"),{X,100},.3,false},
     {TEXT("push_obstacle"),{X,Course==2?600.:800.},3,true}};
   }
   else if(Course==3)
   {
    Steps={{TEXT("south_lane"),{0,75},.3,false},{TEXT("east_edge"),{1490,75},.3,false},
     {TEXT("slope_30m"),{-1490,75},.3,false}};
   }
   else if(Course==5)
   {
    Steps={{TEXT("align_door"),{500,200},.3,false},{TEXT("load_at_door"),{500,610},2,false},
     {TEXT("inside"),{500,900},3,false},{TEXT("west_approach"),{250,900},.3,false},
     {TEXT("west_wall"),{-200,900},1,true},{TEXT("center"),{500,900},.3,false},
     {TEXT("north_approach"),{500,1250},.3,false},{TEXT("north_wall"),{500,1550},1,true},
     {TEXT("back_center"),{500,1000},.3,false},{TEXT("east_approach"),{750,1000},.3,false},
     {TEXT("east_wall"),{1050,1000},1,true},{TEXT("door_align"),{500,1000},.3,false},
     {TEXT("outside"),{500,200},4,false}};
    FGolmokLightingState State;
    if(!Light->CaptureState(State)) return Fail(TEXT("initial lighting state unavailable"));
    BaseExposure=State.ExposureBias;
   }
   else
   {
    PC->ConsoleCommand(TEXT("golmok.path record walk_01"),true);
    if(!Debug->IsRecording()) return Fail(TEXT("walk_01 did not start recording"));
    RecordAt=Now;
    Steps={{TEXT("stationary3s"),{0,200},3,false},{TEXT("align_door"),{500,200},.3,false},
     {TEXT("load_at_door"),{500,610},2,false},{TEXT("inside"),{500,900},3,false},
     {TEXT("outside"),{500,200},4,false},{TEXT("south_lane"),{500,75},.3,false},
     {TEXT("west"),{-1400,75},.3,false},{TEXT("east"),{1400,75},.3,false},
     {TEXT("return_door"),{500,75},.3,false},{TEXT("load_again"),{500,610},2,false},
     {TEXT("inside_again"),{500,900},3,false},{TEXT("outside_again"),{500,200},4,false}};
   }
   bReady=true; StepAt=Now; SampleAt=Now; Save(); return false;
  }
  if(Now-SampleAt>=.25)
  {
   Log+=FString::Printf(TEXT("sample t=%.3f world=%s local=%s inside=%d overlap=%d visible=%d state=%d\n"),Now,*Character->GetActorLocation().ToString(),*Pos.ToString(),Portal->bPlayerInside,Portal->bPlayerOverlapping,Portal->IsSublevelVisible(),int32(Portal->State));
   SampleAt=Now; Save();
  }
  if(Course==5 && Portal->bPlayerInside && InsideAt==0) InsideAt=Now;
  if(Course==5 && InsideAt>0 && !bOverlayChecked && Now-InsideAt>=2.1)
  {
   auto* Light=AGolmokTimeOfDay::Find(World);FGolmokLightingState State;
   if(!Light || !Light->CaptureState(State)) return Fail(TEXT("interior lighting state unavailable"));
   Check(TEXT("overlay settled after2.1s"),!Light->IsTransitioning(),Now-InsideAt);
   Check(TEXT("interior fog zero"),FMath::Abs(State.Fog)<.00001,State.Fog);
   Check(TEXT("interior exposure base plus1EV"),FMath::Abs(State.ExposureBias-BaseExposure-1)<.01,State.ExposureBias-BaseExposure);
   bOverlayChecked=true;
  }
  if(Portal->bPlayerInside) bEntered=true;
  if(bEntered && !Portal->bPlayerInside) bExited=true;
  if(bExited && Portal->State==EGolmokPortalState::Idle && !Portal->IsSublevelVisible()) bUnloaded=true;
  if(Course==3 && Step==2)
  {
   const double Feet=Pos.Z-Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
   MinGroundClearance=FMath::Min(MinGroundClearance,Feet-.02*Pos.X);
  }
  if(bFinalized)
  {
   for(const FString& File:Files) if(IFileManager::Get().FileSize(*File)<=0)
   {
    if(Now-FinalizedAt>15) return Fail(TEXT("game viewport screenshot missing after15s"));
    return false;
   }
   Log+=TEXT("COMPLETE (see individual assertions)\n");Save();Test->AddInfo(TEXT("ZONE WALK ")+Folder);return true;
  }
  if(Step>=Steps.Num())
  {
   Release();
   if(Course==4)
   {
    // Continue a safe ground traversal until the recording includes at least 60s after the initial pause.
    if(Now-RecordAt<63)
    {
     Steps.Add({TEXT("extra_ground"),{bExtraWest?-1400.:1400.,75},.3,false});
     bExtraWest=!bExtraWest; StepAt=Now; return false;
    }
    PC->ConsoleCommand(TEXT("golmok.path stop"),true);
    Check(TEXT("real-time path >=63s"),Now-RecordAt>=63,Now-RecordAt);
    Check(TEXT("portal crossed inward"),bEntered,bEntered);
    Check(TEXT("portal crossed outward"),bExited,bExited);
    Check(TEXT("portal unloaded after return"),bUnloaded,bUnloaded);
    Check(TEXT("recording stopped"),!Debug->IsRecording(),Debug->IsRecording());
    PC->ConsoleCommand(TEXT("golmok.zone.list"),true);
   }
   if(Course==5) Check(TEXT("interior overlay measured"),bOverlayChecked,bOverlayChecked);
   if(Course==3) Check(TEXT("slope feet above ground minus5cm"),MinGroundClearance>=-5,MinGroundClearance);
   bFinalized=true;FinalizedAt=Now;Save();return false;
  }
  const FStep& S=Steps[Step];
  if(!bMoving && !bWaiting)
  {
   const FVector PushDirection=S.Name==TEXT("west_wall")?FVector(-1,0,0):S.Name==TEXT("east_wall")?FVector(1,0,0):FVector(0,-1,0);
   const FVector Delta=Zone->GetActorTransform().TransformVector(S.bPush?PushDirection:FVector(S.Target.X-Pos.X,-(S.Target.Y-Pos.Y),0));
   FRotator Rotation=Delta.Rotation();Rotation.Pitch=-10; PC->SetControlRotation(Rotation);
   MoveStart=Pos; Direction=(S.Target-FVector2D(Pos.X,Pos.Y)).GetSafeNormal();
   TargetDistance=FVector2D::Distance(S.Target,FVector2D(Pos.X,Pos.Y));
   StepAt=Now;bMoving=true;if(TargetDistance>12 || S.bPush)Key(true);
  }
  if(bMoving)
  {
   // InputKey is processed by PlayerInput on the next tick; do not inspect the press frame.
   if(bKeyExpected && Now>StepAt)
   {
    bKeySeenDownSincePress |= PC->IsInputKeyDown(EKeys::W);
    // Opt-in fault injection exercises the same failure path as a viewport focus-loss flush.
    if(Course==4 && Step==1 && Now-StepAt>=.25 &&
       FParse::Param(FCommandLine::Get(),TEXT("GolmokZoneWalkForceInputFlush")))
     PC->FlushPressedKeys();
    if(!PC->IsInputKeyDown(EKeys::W))
     return Fail(*FString::Printf(TEXT("input flushed (viewport focus lost); W seen down since press=%s; Now-StepAt=%.3f s"),
      bKeySeenDownSincePress?TEXT("true"):TEXT("false"),Now-StepAt));
   }
   if(S.bPush)
   {
    // The facade contact occurs around 2s; do not start measuring while still approaching it.
    const double FaceY=(500.-(Course==0?.5*Zone->BlockerThicknessCm:0.))-Character->GetCapsuleComponent()->GetScaledCapsuleRadius();
    const bool bFacadeSettled=FMath::Abs(Pos.Y-FaceY)<=5 && Character->GetVelocity().Size2D()<1;
    const bool bCanMeasure=(Course==0 || Course==1)?bFacadeSettled:Now-StepAt>=2;
    if(!bPushMeasured && Now-StepAt>20) return Fail(*FString::Printf(TEXT("obstacle contact did not settle within20s: y=%.3f face=%.3f speed=%.3f cm/s"),Pos.Y,FaceY,Character->GetVelocity().Size2D()));
    if(Now-StepAt>=.25 && bCanMeasure && !bPushMeasured){PushStart=Pos;PushAt=Now;bPushMeasured=true;}
    if(!bPushMeasured || Now-PushAt<1) return false;
    Check(TEXT("obstacle 1s push displacement <5cm"),FVector::Dist(Pos,PushStart)<5,FVector::Dist(Pos,PushStart));
    // Guard against vacuous stationary success (input failure or a wrong obstacle).
    const double Radius=Character->GetCapsuleComponent()->GetScaledCapsuleRadius();
    if(Course==5)
    {
     const double Actual=S.Name==TEXT("north_wall")?Pos.Y:Pos.X;
     const double Expected=S.Name==TEXT("west_wall")?120+Radius:S.Name==TEXT("east_wall")?880-Radius:1380-Radius;
     Check(TEXT("reached interior wall face"),FMath::Abs(Actual-Expected)<30,Actual);
    }
    else
    {
     const double ExpectedY=Course==2?200:500;
     Check(TEXT("reached obstacle south face"),FMath::Abs(Pos.Y-(ExpectedY-Radius))<30,Pos.Y);
    }
   }
   else
   {
    const double Progress=FVector2D::DotProduct(FVector2D(Pos.X-MoveStart.X,Pos.Y-MoveStart.Y),Direction);
    if(Progress<TargetDistance-12)
    {
     if(Now-StepAt>20) return Fail(TEXT("waypoint blocked or no input"));
     return false;
    }
   }
   Release();bMoving=false;bWaiting=true;WaitAt=Now;
   Log+=FString::Printf(TEXT("step=%s arrived t=%.3f local=%s\n"),*S.Name.ToString(),Now,*Pos.ToString());
   if(S.Name==TEXT("inside")) Check(TEXT("door traversed y>=720cm"),Pos.Y>=720,Pos.Y);
  }
  if(bWaiting && Now-WaitAt>=S.Wait)
  {
   if(Course==5 && S.Name==TEXT("inside"))
   {
    FHitResult Hit;FCollisionQueryParams Query;Query.AddIgnoredActor(Character.Get());
    const FVector Begin=Character->GetActorLocation();
    const bool bHit=World->LineTraceSingleByChannel(Hit,Begin,Begin+FVector(0,0,400),ECC_Visibility,Query);
    const double CeilingZ=bHit?Zone->GetActorTransform().InverseTransformPosition(Hit.ImpactPoint).Z:-1;
    Check(TEXT("ceiling collision trace at300cm (not jump)"),bHit && FMath::Abs(CeilingZ-300)<5 && Hit.ImpactNormal.Z<-.9,CeilingZ);
   }
   FString File=Folder/(S.Name.ToString()+FString::Printf(TEXT("_%02d.png"),Step));
   FScreenshotRequest::RequestScreenshot(File,false,false,false,FIntRect(),true);Files.Add(File);
   for(const auto& Line:Debug->GetHudLines()) Log+=TEXT("HUD ")+Line+TEXT("\n");
   ++Step;bWaiting=false;bPushMeasured=false;StepAt=Now;Save();
  }
  return false;
 }
private:
 void Key(bool Down){bKeyExpected=Down;if(Down)bKeySeenDownSincePress=false;if(PC.IsValid())PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::W,Down?IE_Pressed:IE_Released,Down?1.f:0.f));}
 void Release(){Key(false);}
 void Save(){if(!Folder.IsEmpty())FFileHelper::SaveStringToFile(Log,*(Folder/TEXT("walk.txt")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);}
 void Check(const TCHAR* Label,bool OK,double Value){Test->TestTrue(Label,OK);Log+=FString::Printf(TEXT("assert %s value=%.5f %s\n"),Label,Value,OK?TEXT("PASS"):TEXT("FAIL"));}
 bool Fail(const TCHAR* Why)
 {
  Release();
  if(PC.IsValid())
  {
   auto* Debug=PC->GetWorld()->GetSubsystem<UGolmokDebugSubsystem>();
   if(Debug && Debug->IsRecording())
   {
    // World-subsystem Deinitialize discards the active recording; StopRecording would save it.
    const FString Path=Debug->PathFilePath(TEXT("walk_01"));
    const FString Warning=FString::Printf(TEXT("ZoneWalk failure: active walk_01 recording left unsaved for world-subsystem Deinitialize; path=%s (%s)."),
     *Path,IFileManager::Get().FileExists(*Path)?TEXT("existing file left untouched"):TEXT("no existing file"));
    Test->AddWarning(Warning);Log+=Warning+TEXT("\n");
   }
   else PC->ConsoleCommand(TEXT("golmok.path stop"),true);
  }
  Test->AddError(FString::Printf(TEXT("ZoneWalk course%d step%d: %s"),Course,Step,Why));
  Log+=FString(TEXT("FAILED: "))+Why+TEXT("\n");Save();return true;
 }
 FAutomationTestBase* Test;int32 Course,Step=0;double InsideAt=0,BaseExposure=0,FinalizedAt=0,PlacedAt=0,Started=0,Now=0,StepAt=0,SampleAt=0,WaitAt=0,PushAt=0,RecordAt=0,TargetDistance=0,MinGroundClearance=1e9;
 bool bKeySeenDownSincePress=false,bKeyExpected=false,bOverlayChecked=false,bFinalized=false,bPlaced=false,bReady=false,bMoving=false,bWaiting=false,bPushMeasured=false,bEntered=false,bExited=false,bUnloaded=false,bExtraWest=true;
 TWeakObjectPtr<APlayerController> PC;TWeakObjectPtr<AGolmokCharacter> Character;
 FVector Pos,MoveStart,PushStart;FVector2D Direction;TArray<FStep> Steps;TArray<FString> Files;FString Folder,Log;
};
void Enqueue(FAutomationTestBase* Test)
{
 FString Map;
 if(!FParse::Value(FCommandLine::Get(),TEXT("GolmokZoneWalkMap="),Map) || !FPackageName::DoesPackageExist(Map))
 {Test->AddError(TEXT("ZoneWalk requires an existing -GolmokZoneWalkMap=/Game/... package"));return;}
 int32 Only=-1;FParse::Value(FCommandLine::Get(),TEXT("GolmokZoneWalkCourse="),Only);
 if(Only < -1 || Only > 5){Test->AddError(TEXT("ZoneWalkCourse must be 0..5 or omitted"));return;}
 if(Only>=0 && Only!=4 && FParse::Param(FCommandLine::Get(),TEXT("GolmokZoneWalkForceInputFlush")))
  Test->AddWarning(TEXT("GolmokZoneWalkForceInputFlush applies only to course 4; ignored for the selected course."));
 for(int32 Course=0;Course<6;++Course)
 {
  if(Only>=0 && Only!=Course)continue;
  ADD_LATENT_AUTOMATION_COMMAND(FEditorLoadMap(Map));
  ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
  ADD_LATENT_AUTOMATION_COMMAND(FWalk(Test,Course));
  ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
 }
}
}
#endif
