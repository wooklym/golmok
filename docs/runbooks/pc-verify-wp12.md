# PC 검증 런북 — WP-12 포토 모드 최소판 (V-09)

대상: PC Claude 세션(또는 사용자). 전제: `runbooks/pc-verify-wp05.md` 통과(V-03: 빌드 OK, `L_Dev`·`L_ZoneTest` 존재, `synthetic_zone.run(interior=True)`이 한 번 돌아 `z_synthetic_001`·`z_synthetic_001_interior` 에셋·액터·서브레벨·포털이 있음), `runbooks/pc-verify-wp09.md`(V-07)는 권장(미통과면 §7·§8은 배치 zone `L_ZoneTest`로 진행하고 §13에 적는다), `cd tools && python -m pytest -q` 초록(`test_ue_photo_math.py`·`test_ue_config_photo.py`·`test_ue_wp12_fixture.py` 포함 — 여기서 빨간 것은 PC 문제가 아니라 코드 문제이므로 클라우드 세션에 돌려보낸다).
소요: 빌드 10~20분 + 헤드리스 테스트 10분 + 검증 90분(배율 표·실내 포함). 결과는 이 문서 하단 §13과 `docs/plan/STATUS.md`(V-09 행, WP-12 행)에 적는다.

클라우드 세션은 UE를 컴파일할 수 없었다. **컴파일 에러가 나면 §12의 표를 보고 고친 뒤 커밋**한다(`WP-12: PC fix …`). 설계 의도를 바꾸는 수정이면 `docs/plan/WP-12-photo-mode.md` "결과"에 한 줄 적는다(DEVELOPMENT-PLAN §4 핸드오프 규칙: 검증 결과는 이 파일 하단, API 수정·설계 변경은 커밋 메시지와 STATUS에).

규칙:
- 이 문서의 기대 로그·메시지는 **설계 문서가 아니라 코드**에서 옮겨 적었다. C++ 줄(`LogGolmok: …`)은 `Photo/GolmokPhotoModeSubsystem.cpp`·`Photo/GolmokPhotoCameraPawn.cpp`·`Debug/GolmokDebugSubsystem.cpp`·`Debug/GolmokHUD.cpp`·`Player/GolmokPlayerController.cpp`의 `UE_LOG`/`Printf` 형식에 픽스처 값을 넣은 것이고, 콘솔 이름·ini 키·JSON 키·키 힌트는 각각 같은 파일·`Config/DefaultGame.ini`·`Config/Golmok/photo.json`에서 옮긴 것이다. `tools/tests/test_ue_wp12_fixture.py::test_runbook_mentions_commands_files_tests_and_keys`가 콘솔 4개·자동화 3개·ini 11키·`photo.json`·폴더명이 이 문서에 있는지 잡는다(이름을 바꾸면 코드와 이 문서를 **함께** 고친다; 기대 로그는 항상 ```` ``` ```` 블록 안에). 설계(`docs/plan/WP-12-photo-mode.md` §2-3·§4·§9 등)와 다른 곳은 그 자리에 "설계와 다름:"으로 표시했다.
- 값 표기: `x.xx s`·`…`는 PC에서만 정해지는 실측값. `<Project>` = `unreal\Golmok`, `<Saved>` = `<Project>\Saved`(코드는 `FPaths::ConvertRelativePathToFull`로 절대 경로를 `/` 구분자로 찍는다), `<stamp>` = `FDateTime::Now().ToString("%Y%m%d_%H%M%S")`(로컬 시각, 예 `20260927_101112`). 에디터 Python은 Output Log 창의 Python 입력줄(또는 `py` 콘솔 명령)로 실행한다.
- 검증 방식은 V-03과 같은 에디터 Python PIE 드라이버 + `unreal.SystemLibrary.quit_editor()`(헤드리스는 `UnrealEditor-Cmd -unattended -nullrhi`). **키 입력은 사람이 한다**: 정지 중 Enhanced Input은 드라이버가 흉내 내지 못하므로(V-03의 Win32 `SendInput`은 창이 전면일 때만) 값·배율·촬영은 콘솔 `golmok.photo`·`golmok.photo.shoot`·`golmok.photo.reset`·`golmok.photo.set`이 대체한다. **에디터 창을 전면에** 둔다(뒤에 있으면 뷰포트를 그리지 않아 사진이 생기지 않음 — V-03). 촬영 중 `stat` 명령은 끈다(`stat none`; 고해상도 샷에 온스크린 텍스트가 들어갈 수 있음, §12 #12).
- 포토 모드는 `IMC_GolmokDebug`를 제거하므로 F1~F10·1~4가 **안 먹는 것이 정상**이다. 디버그 HUD가 필요하면 `golmok.hud 1`.

## 0. 대상 파일
| 파일 (`unreal/Golmok/` 기준, 그 외 저장소 기준) | 내용 |
|---|---|
| `Source/Golmok/Photo/GolmokPhotoMath.h` | 순수 헤더(따옴표 include는 `Geo/GolmokGeoMath.h`·`Debug/GolmokStatsMath.h` 2개): `ClampParam/Quantize/StepLinear/StepGeometric/StepTable/NearestIndex/WrapDeg180/FovToFocalMm`, `ClampToSphere/ClampToPolygonXY/Constrain`·`KeepHeightSlide`(keep-height 슬라이드 방향, §12 #68)(V-09 후속 a6c48a3 → e03753e → 7f66810: `ClampToPolygonXY`는 경계 거리 ≥ inset인 침식 영역 S의 **정확한 최근접점**(inset만큼 옮긴 변·꼭짓점 호·쌍 교점·앵커 후보, 가까운 변 주변 11조각 먼저), `EffectiveInsetCm`·`MoveInsetCm`(앵커 상한, PR #29 리뷰 A1)·`Constraint::Current`, 재검사 실패면 Current→P 이분 탐색 폴백), `PhotoMeta`+`FormatPhotoMetaJson`(g++ 교차검증 `tools/tests/fixtures/ue/photomath_driver.cpp`) |
| `Source/Golmok/Photo/GolmokPhotoModeSubsystem.{h,cpp}` | `UGolmokPhotoModeSubsystem`(월드 서브시스템, Game/PIE): `GolmokPhotoJson` 파서, 상태기계 `Inactive/Active/Shooting/Captured/Exiting`, `Enter/Exit/Toggle/Reset/Shoot`, `StepParam/SetParam/SetMultiplier`, `OnEndFrame` 캡처 창, `BuildMeta/WriteMeta`, 오버레이 줄, 입력 자산 `IA_GolmokPhoto*` 21개 + `IMC_GolmokPhoto`(우선순위 3), 콘솔 `golmok.photo`·`golmok.photo.shoot`·`golmok.photo.reset`·`golmok.photo.set`; 복원 스냅샷 공개 계약 `FGolmokPhotoRestoreState` + `GetRestoreState() const`(f5c8861, WP-18 로스터×포토 테스트용) |
| `Source/Golmok/Photo/GolmokPhotoCameraPawn.{h,cpp}` | `AGolmokPhotoCameraPawn`: 구(`PhotoSphere`, QueryOnly, WorldDynamic)·카메라(`PhotoCamera`), `bTickEvenWhenPaused`, `MoveConstrained`(구 → 다각형 → 스윕, 막히면 남은 이동을 충돌면에 투영해 한 번 더 — V-09 후속 6c36fd3, `bStartPenetrating`이면 앵커 쪽 10 cm 후퇴), `ApplyOptics`(PP 오버라이드), `EndPlay → Owner->OnPhotoPawnEndPlay` |
| `Source/Golmok/Debug/GolmokDebugSubsystem.{h,cpp}` | `RequestHighResScreenshot(AbsolutePathNoExt, Multiplier, OutMessage, OutEffectiveMultiplier)` public 분리(`TakeHighResScreenShot()` false면 1x 재시도), `TakeScreenshot`은 래퍼; `StartRecording/StartPlayback` 첫 검사 `photo mode is on (golmok.photo 0 first)` |
| `Source/Golmok/Debug/GolmokHUD.{h,cpp}` | `DrawHUD` 첫머리 `IsHudSuppressed()`(= 캡처 창) 가드 + 왼쪽 아래 포토 오버레이(흰/노랑·시안·회색·초록), 클래스 주석 정정 |
| `Source/Golmok/Player/GolmokPlayerController.{h,cpp}` | `IA_GolmokPhotoToggle`(P, `Gamepad_Special_Left`, `bTriggerWhenPaused`)·`IMC_GolmokPhotoToggle`(우선순위 2, 항상), `OnTogglePhoto`(로그 `P: …`), `SetDebugKeysSuspended/IsDebugKeysSuspended`, `SetupInputComponent`가 `Photo->BindInput(Input)` 위임; `GetFullTickWhenPausedFlag/SetFullTickWhenPausedFlag`(f5c8861 — `APlayerController::bShouldPerformFullTickWhenPaused`가 5.8.3에서 protected라 원시 비트 스냅샷·복원, §12 #3) |
| `Source/Golmok/Player/GolmokGameViewportClient.{h,cpp}` | 신규(f5c8861): `UGolmokGameViewportClient`(`UGameViewportClient` 파생) — `IsTransitionMessageSuppressed() const`로 protected `bSuppressTransitionMessage`를 읽음(엔진은 setter만 있음, §12 #12) |
| `Config/DefaultEngine.ini` | 파일 끝 `[/Script/Engine.Engine]` 절(`[WP-12 hook]`) `GameViewportClientClassName=/Script/Golmok.GolmokGameViewportClient`(f5c8861; 병합 전 리뷰로 파일 끝으로 이동). 이 줄이 없으면 서브시스템이 엔진 기본값(false)으로 복원하고 §2의 Warning을 1회 찍는다 |
| `Source/Golmok/Zones/GolmokZoneSubsystem.{h,cpp}` | 추가만: `AGolmokZone* FindLoadedZoneAt(const FVector2D& LevelUEPointCm) const`(Loaded + footprint 포함 + `ZoneWins`) |
| `Source/Golmok/Lighting/GolmokTimeOfDay.{h,cpp}` | 추가만: `void ShiftTransitionStart(double DeltaSeconds)`(전환 중 아니면 no-op) |
| `Source/Golmok/Tests/GolmokPhotoTest.cpp` | 자동화 3개 `Golmok.Photo.EnterExit / Clamp / MetaJson`(`EditorContext \| ProductFilter`, `L_Dev`, 대기는 전부 `FPlatformTime`) |
| `Config/DefaultGame.ini` | `[/Script/Golmok.GolmokPhotoModeSubsystem]` 11키(§4·§5·§6·§7 참조): `ConfigFile=Golmok/photo.json`, `PhotoFolder=Screenshots/Golmok/photo`, `ScreenshotMultiplier=2`, `MaxMultiplier=2`(V-09 4834941, 원래 3), `MaxDistanceM=3.0`, `CollisionRadiusCm=15`, `FootprintMarginM=0.2`, `MoveSpeedMps=1.5`, `PreCaptureFrames=2`, `PostCaptureFrames=2`, `PauseMode=GamePause`. 다른 섹션·`DefaultInput.ini`(`!DebugExecBindings=ClearArray`) 무변경 |
| `Config/Golmok/photo.json` | 단일 소스: `schema_version 1`, `params` 5개(`fov ev focus fstop roll`), `toggles` 3개(`dof character_hidden overlay_hidden`), `hints.keyboard/gamepad` 3줄씩. `../Config/Golmok` UFS 스테이징 줄이 덮음 |
| `tools/tests/test_ue_photo_math.py`, `test_ue_config_photo.py`, `test_ue_wp12_fixture.py`, `fixtures/ue/photomath_driver.cpp` | 클라우드 CI(초록); PC에서는 `pytest -q`로만 재확인 |
| `docs/research/05-legal-policy.md` 항목 7 | 사용자 촬영 스크린샷 외부 공유(자문 대상, 판단 없음) |

전제 확인:
- [ ] `git pull` 후 `cd tools; .\.venv\Scripts\Activate.ps1; pip install -e ".[basemap,zone,mesh,splat,align,dev]"; pytest -q` 초록(`test_ue_photo_math.py`는 g++가 없으면 skip — 클라우드 CI에서 이미 통과, skip이면 §13에 "g++ 없음"으로).
- [ ] `L_ZoneTest`에 `Zone_z_synthetic_001`(Loaded)·`Zone_z_synthetic_001_interior`·`Portal_z_synthetic_001_door_1`·서브레벨 `L_z_synthetic_001_interior`가 있다(V-03 §2). 없으면 `import golmok.synthetic_zone as z; z.run(interior=True)`.
- [ ] 경로 `quick`이 있다(`golmok.path list`; §9에서 쓴다). 없으면 PIE에서 `golmok.path record quick` → 5 s 걷기 → `golmok.path stop`.
- [ ] 게임패드 유무를 §13에 적는다(없으면 §3의 패드 항목은 "미실행").

## 1. 빌드
```powershell
git pull
.\tools\ue\build.ps1          # Development Editor
```
- [ ] 컴파일 성공(경고는 기록). 실패 시 §12 표 번호로 고치고 `WP-12: PC fix …` 커밋. 먼저 볼 곳 — 설계 행: #7(`BindAction`에 `UWorldSubsystem` 메서드), #22(`TArray<TObjectPtr<UInputAction>>`), #25(`EEndPlayReason` 값 이름), #30(C4458), #32(유니티 빌드 익명 namespace); 구현 행: #37(`SetActorRotation(FRotator, ETeleportType)`), #38(폰 멤버 `Owner`가 `AActor::Owner`를 가림), #39(`FRotator::Vector()`), #41(`CollisionQueryParams.h`/`CollisionShape.h` include·`FCollisionQueryParams(FName, bool)`), #42(`FCString::Atod`·`IsNumeric`), #43(`ParseIntoArrayWS`), #45(`World->WorldType` 직접 비교), #46(`FJsonObject::Set*Field(TEXT(…))` TCHAR 리터럴), #48(`TestNotNull` bool 반환·`TestEqual` 오버로드), #51(`GetDefault<UGolmokPhotoModeSubsystem>()->ResolveConfigPath()`), #52(`FInputActionValue::Get<float>()`), #53(`Camera->PostProcessSettings` 직접 쓰기·`Engine/Scene.h`), #54(`GetScaledCapsuleHalfHeight`). #3(`bShouldPerformFullTickWhenPaused`)·#12(`bSuppressTransitionMessage`)는 V-09 1차 빌드의 C2248(protected)로 확인돼 **f5c8861에서 이미 고쳤다**(PC 접근자·`UGolmokGameViewportClient`) — 같은 이름으로 다시 오류가 나면 f5c8861이 pull 됐는지부터 본다.
- [ ] `.\tools\ue\open-editor.ps1` → 에러 없이 열림. 에디터 월드에서는 서브시스템이 없다(`DoesSupportWorldType`이 Game/PIE만): 에디터 콘솔 `golmok.photo` →
  ```
  LogGolmok: Warning: golmok.photo*: no photo mode subsystem in this world (game / PIE only).
  ```

헤드리스 자동화(에디터를 닫고):
```powershell
.\tools\ue\test.ps1 -Filter Golmok.Photo
.\tools\ue\test.ps1 -Filter Golmok. -SetupDevLevel
```
- [ ] 첫 명령: 3개 전부 `Success`(`-nullrhi`). 기대 `[Info]` 줄(테스트 코드 `AddInfo`; L_Dev에는 zone·GeoOrigin이 없다):
  ```
  Golmok.Photo.EnterExit   [Info] photo mode on (fov 80.0, no zone, paused)          (Enter() 메시지; fov는 캐릭터 FollowCamera FOV — 80이 아니면 그 값)
                           [Info] exit camera: before … cm, after … cm, cut 1          (일반 종료, §12 #64: before > 20 — 포토 카메라를 80 cm 올린 뒤, after ≤ 2, cut 1)
                           [Info] exit camera: before … cm, after … cm, cut 1          (사전 정지 종료 — 같은 기준. 이어서 #67 단언은 성공하면 줄이 없다)
                           [Info] ApplyPreset(clear_noon) started no transition; drift assertion skipped   (나오면 안 됨 — §12 #50; "lighting presets file missing; drift block skipped"도 마찬가지)
                           [Info] SetGamePaused(true) refused; pre-existing pause block skipped           (나오면 안 됨 — §12 #1)
  Golmok.Photo.Clamp       [Info] after +1000 x: X=… Y=… Z=… (anchor X=… Y=… Z=…)     (구 300 cm 안·정사각형 ±200 cm 안)
                           [Info] after -500 z: X=… Y=… Z=… (floor z …)                (바닥 스윕 — §12 #49)
                           [Info] keep height: from X=… Y=… Z=… to X=… Y=… Z=…, max |dz| 0.0000, horizontal … / slice … (R …)   ((b2) 구∩정사각형 접합 수평 밀기: max |dz| ≤ 0.01, horizontal = slice −3..+0.01 — D-013 결정 3)
                           [Info] box at X=… Y=… Z=…: pawn X=…, face distance …, along …   (face distance ≥ 15 − 1, along < 100 — §12 #47)
                           [Info] slide: from X=… to X=…, lateral …, face distance …, along …   ((c2) 비스듬한 밀기: lateral > 20, face distance ≥ 15 − 1, along < 50 — §12 #62)
                           [Info] keep height wall slide: from X=… to X=…, lateral …, |dz| 0.0000, face distance …   ((c2)를 bKeepHeight로 한 번 더, PR #40 리뷰 M3: lateral > 20, |dz| ≤ 0.01, face distance ≥ 15 − 1)
                           [Info] keep height slope slide: from X=… to X=…, lateral …, |dz| 0.0000, face distance …   ((c3) 같은 상자를 피치 30°로 기울여 한 번 더, V-09c §12 #68: lateral > 20, |dz| ≤ 0.01, face distance ≥ 15 − 1 — 수정 전 코드는 lateral 2.3)
                           [Info] keep height slope slide (pitch -30): from X=… to X=…, lateral …, |dz| 0.0000, face distance …   ((c3) 변형 R56-6: 면이 폰 반대쪽으로 기움(법선 Nz > 0 — 12° 경사로·계단 모서리 쪽). 기대 lateral 40.0·face distance 15.9((c3)과 같음), 판정 lateral > 20, |dz| ≤ 0.01, face distance ≥ 15 − 1)
                           [Info] keep height near-level slide (pitch 1): from X=… to X=…, lateral …, along …, |dz| 0.0000, face distance … (start …)   ((c3) 변형 R56-6: 1° 기운 윗면에 내려앉은 뒤 같은 밀기 — 수평 법선 0.0175 ≤ 0.02라 평탄화만. 기대 lateral 23.9·along 59.8(비 0.40 — 옆으로 꺾이지 않음)·face distance 15.0 (start 16.1), 판정 start 15 − 1..15 + 3, along < 95, |lateral − 0.4·along| ≤ 1, |dz| ≤ 0.01)
                           [Info] box destroyed: pawn X=…, along …                    (along > 100)
  Golmok.Photo.MetaJson    [Info] Describe(): active fov 80.0 ev +0.00 focus 3.000 m f/2.80 dof off roll +0.0 (no zone)
                           [Info] shooting -> <Saved>/Screenshots/Golmok/photo/<stamp>.png (2x, meta <stamp>.json)
                           [Info] capture window closed after 3.xx s                  (-nullrhi는 PNG를 쓰지 않으므로 3 s 타임아웃 경로)
                           [Info] the clock rolled over between the marker and the second shot; _2 suffix not asserted   (초 경계에 걸리면 1회 — 무해)
  ```
  EnterExit의 로그에는 사전 정지 종료 뒤 `photo: world still paused; camera-moveable-when-paused flag kept true until the unpause`와 정지 해제 뒤 `photo: camera-moveable-when-paused flag restored after the unpause (false)`가 한 번씩 찍힌다(§12 #67). MetaJson의 로그에는 `photo: screenshot requested via HighResShot -> <Saved>/Screenshots/Golmok/photo/<stamp>00000.png (no viewport size; written on the next frame)`와 `photo: capture window closed (<stamp>.png timeout 3.0 s, png absent)`가 찍힌다(nullrhi 폴백 — 정상). 테스트가 만든 `<stamp>.json`·`_2.json`은 소멸자가 지운다(남아 있으면 §13에).
- [ ] 두 번째 명령: **32개** 전부 `Success` = WP-09까지 16개(`Golmok.Player.Movement`, `Lighting.PresetsFile/PresetApply`, `Debug.StatsMath/PathFormat/PathRoundTrip/HudStats`, `Portal.SpawnFromManifest/RoundTrip/PawnSwap/SharedInterior`, `Zone.IndexParse/IndexDiscover/AsyncLoad/AsyncCancel/InteriorNotBlocked`) + WP-18 병합분 7개(`Golmok.Character.Config/Runtime/PortalRoundTrip` — `Tests/GolmokCharacterRosterTest.cpp`·`GolmokCharacterRosterPortalTest.cpp`; PR #24 `Character.PathRoundTrip/Locomotion/PhotoIntegration/RenderEvidence` — `GolmokCharacterRoster{Path,Movement,Photo,Render}Test.cpp`. `PhotoIntegration`은 Photo가 있는 이 빌드에서 실제 6조합(proxy135/proxy110/Quinn × GamePause/TimeDilation)을 돌리고, `RenderEvidence`는 명시적 실행 옵션 없이는 설계상 `NOT EXECUTED` Warning 1개로 끝난다 — 둘 다 상태 열은 `Success`) + WP-13 2개(`Audio.StateMachine/Footstep` — `Tests/GolmokAudioTest.cpp`) + WP-14a 1개(`Lighting.Clock` — `Tests/GolmokLightingTest.cpp`, 런북 `pc-verify-wp14a.md`) + WP-15a 3개(`Zone.ManifestV2` — `Tests/GolmokZoneManifestV2Test.cpp`; `Travel.Teleport`, `Save.RoundTrip` — `Tests/GolmokTravelSaveTest.cpp`, L_ZoneTest가 없으면 skip Info) + 위 3개. 현재 코드 기준 헤드리스 자동화 32개(Photo 3 + 기존 29); 아래 §13의 26개는 V-09 PC 실행 당시 이력이다. `test.ps1` 요약 줄 `Succeeded:`는 Warning이 있는 테스트를 따로 세므로(V-03) 상태 열이 전부 `Success`인지로 본다.
- [ ] `Golmok.log`에 `photo:` 접두 `[Error]` 0건(`photo: ERROR cannot write meta …`·`photo: ERROR screenshot request failed: …`·`photo: config not loaded from …`가 없어야 한다). 실패한 테스트는 `unreal\Golmok\Saved\Logs\Golmok.log`의 `[Error]` 줄을 §13에 옮겨 적는다.

## 2. 진입/복원(`L_ZoneTest`, zone 안)
PIE 시작(PlayerStart = 001 zone-local (0, −5, 0) m, `Zone_z_synthetic_001` Loaded), F1로 디버그 HUD 켠 채 **P**.
- [ ] 로그(첫 진입에만 `config loaded` 1회; `ResolveConfigPath()` = `FPaths::ProjectConfigDir()` + `Golmok/photo.json`이라 `../../../Golmok/Config/…` 상대 경로로 찍힐 수 있음):
  ```
  LogGolmok: photo: config loaded (5 params) from <Project>/Config/Golmok/photo.json
  LogGolmok: photo: photo mode on (fov 80.0, zone z_synthetic_001 v1, paused)
  LogGolmok: P: photo mode on (fov 80.0, zone z_synthetic_001 v1, paused)
  ```
  `no zone`이 찍히면 001이 아직 `Loading`이거나 캐릭터가 footprint 밖(`golmok.zone.list`로 `loaded` 확인). 설계와 다름: 설계 §2-3은 `golmok.photo: photo mode on …` 한 줄만 적었지만 코드는 서브시스템의 `photo: …` 줄 + 호출자(`P:` / `golmok.photo:`) 줄, 두 줄이다.
- [ ] 다음 Warning이 **없어야** 한다(f5c8861 이후 진입 시 뷰포트 클래스 검사, PIE 세션당 1회):
  ```
  LogGolmok: Warning: photo: game viewport is GameViewportClient, not UGolmokGameViewportClient (DefaultEngine.ini GameViewportClientClassName); the transition message flag is restored to false
  ```
  찍히면(`%s` 자리는 실제 뷰포트 클래스 이름) `Config/DefaultEngine.ini` **파일 끝** `[/Script/Engine.Engine]` 절에 `GameViewportClientClassName=/Script/Golmok.GolmokGameViewportClient`가 있는지 확인한다(§12 #12). 이 상태에서도 포토 모드는 동작하지만 종료 시 전환 메시지 억제 플래그를 원래 값 대신 false로 되돌린다 → §13.
- [ ] 화면: 정지(캐릭터 애니·바람 멈춤), 디버그 HUD 사라짐, **왼쪽 아래** 반투명 검정 박스에 5줄(`GolmokHUD.cpp` `PhotoColorForLine`: 1행 흰색, 2행 시안, 3~5행 회색):
  ```
  PHOTO  z_synthetic_001 v1  overcast_morning  3.3 / 3.3 m  2x
  fov 80 (21 mm)  ev +0.00  focus 3.000 m  f/2.80  dof off  roll +0.0
  P exit  Space shoot  R reset  F dof  H char  O overlay
  WASD/EQ move  Shift fast  mouse look  Z/C roll  wheel fov
  [ ] fov   - = ev   , . focus   N M f-stop
  ```
  프리셋 칸은 `AGolmokTimeOfDay::CurrentPreset`(없으면 `-`), 거리는 폰↔캐릭터 캡슐 중심 — 진입 직후는 스프링암 카메라 거리(`CameraBoom->TargetArmLength = 320` + `SocketOffset(0,45,55)` ≈ 3.28 m; 카메라 프로브가 당겼으면 더 짧음)다. 분모는 이번 세션의 유효 반경 `GetEffectiveRadiusCm()` = max(`MaxDistanceM` 3.0 m, 진입 거리 + 1 cm)라 진입 카메라가 3 m 밖이면 `3.3 / 3.3 m`처럼 넓어지고, 첫 이동·R에서 카메라가 튀지 않는다(튀면 §13에; 관찰한 분모 값도 §13에), 배율은 `ScreenshotMultiplier`(2). `(21 mm)`는 `FovToFocalMm(80)`(36 mm 환산; 65°면 `28 mm`). 힌트 3줄은 `photo.json` `hints.keyboard` 그대로(패키지에서도 JSON 값).
- [ ] **정지 화면 중앙에 "PAUSED" 글자 없음**(`SetSuppressTransitionMessage(true)`, §12 #12). 있으면 §12 #12 대안(`PauseMode=TimeDilation`)으로 재실행하고 §13에.
- [ ] P → 원래 3인칭 시점·컨트롤 회전·디버그 HUD(F1 상태) 복귀, 캐릭터 즉시 이동 가능:
  ```
  LogGolmok: photo: photo mode off (restored, unpaused, tod shift 0.000 s)
  LogGolmok: P: photo mode off
  ```
  (`photo: exit (toggle)`는 Verbose라 기본 로그에 없다.) 설계와 다름: 설계 §2-3의 `golmok.photo: photo mode off (restored, unpaused, tod shift 0.000 s)`는 코드에서 `photo:` 줄이고, 호출자 줄은 `photo mode off`만.
- [ ] 콘솔 왕복(같은 동작, 호출자 접두만 다름):
  ```
  golmok.photo 1
  LogGolmok: photo: photo mode on (fov 80.0, zone z_synthetic_001 v1, paused)
  LogGolmok: golmok.photo: photo mode on (fov 80.0, zone z_synthetic_001 v1, paused)
  golmok.photo 1
  LogGolmok: golmok.photo: ERROR cannot enter: already active
  golmok.photo 0
  LogGolmok: photo: photo mode off (restored, unpaused, tod shift 0.000 s)
  LogGolmok: golmok.photo: photo mode off
  golmok.photo 0
  LogGolmok: golmok.photo: ERROR not active
  golmok.photo          (인자 없음 = 토글; on/off/true/false도 받는다)
  ```
- [ ] **사전 정지**(§12 #4): 콘솔 `pause` → **P 키**(정지 중에도 `IA_GolmokPhotoToggle`이 발화해야 함) → WASD로 카메라 이동 → P → **여전히 정지** → `pause`로 해제:
  ```
  LogGolmok: photo: photo mode on (fov 80.0, zone z_synthetic_001 v1, already paused)
  LogGolmok: P: photo mode on (fov 80.0, zone z_synthetic_001 v1, already paused)
  LogGolmok: photo: world still paused; camera-moveable-when-paused flag kept true until the unpause
  LogGolmok: photo: photo mode off (restored, left paused, tod shift 0.000 s)
  LogGolmok: P: photo mode off
  pause
  LogGolmok: photo: camera-moveable-when-paused flag restored after the unpause (false)
  ```
  `camera-moveable` 두 줄은 PR #40 리뷰 R1(§12 #67): 정지가 유지되는 동안 플래그를 true로 두고 정지 해제 뒤 첫 프레임에 저장값으로 되돌린다(진입 전 값이 true였으면 두 줄 모두 없다). P가 안 먹으면(정지 상태에서 풀틱이 아직 꺼져 있어 입력이 안 옴) `golmok.photo 1`로 진입해 나머지를 진행하고 §12 #4에 "사전 정지 P 불가"로 기록.
- [ ] **전환 중 진입**(시간대 드리프트): `1` 키(또는 `golmok.tod clear_noon`; `TransitionSeconds` 기본값으로 전환 시작) 직후 P → 10 s 대기 → P → HUD `tod: <from> -> <to> NN%`의 진행률이 **진입 전 값에서 이어서** 끝난다(`ShiftTransitionStart`). 로그의 `tod shift x.xxx s`: 정지 중 월드 시계가 멈추면 `0.000`, 흐르면 ≈ 10 — 어느 쪽이든 정상이고 값을 §13에(§12 #11 관찰).

## 3. 정지 중 입력·틱·카메라
- [ ] **WASD / E Q / 마우스**로 카메라가 **부드럽게** 움직이고 화면이 따라온다(§12 #2·#3·#4). LeftShift로 ×3(`1.5 m/s` → `4.5 m/s`; 반경 3 m 구를 2 s 안에 가로지름). 마우스 0.5°/unit, 피치 ±89°에서 멈춤. 안 움직이거나 화면이 안 따라오면 §12 #3 대안 순서대로, 최후 `Config\DefaultGame.ini` `PauseMode=TimeDilation`으로 바꾸고 **에디터 재시작** 후 §2부터 재실행(어느 단계에서 됐는지 §13에; 끝나면 `GamePause`로 되돌려 `git diff` 비어 있게).
- [ ] 마우스 휠 1노치 = FOV 5°(위로 = 좁게, `OnFovWheel`은 부호만 봄) — §12 #19·#52.
- [ ] 포토 중 WASD·마우스·Space·Shift를 마음껏 누른 뒤 P → **캐릭터 위치·회전 불변**(`IMC_Default`는 `bTriggerWhenPaused = false` + 포토 IMC 우선순위 3 `bConsumeInput`; §12 #5). 캐릭터가 튀었으면 §12 #5 대안.
- [ ] 포토 중 **1~4·F5·F9·F10이 안 먹음**(디버그 컨텍스트 제거 — 로그에 `Preset key …`·`F9: …`·`F10: …` 줄 없음), **F1·F2도 안 먹음**(의도), `golmok.hud 1`은 먹음:
  ```
  golmok.hud 1
  LogGolmok: golmok.hud: on
  ```
  → 왼쪽 위 디버그 HUD가 포토 오버레이와 함께 보인다(겹치지 않음). `golmok.hud 0`으로 끄고 P → 나간 뒤 HUD는 **진입 전 상태**(`bSavedHudVisible`)로 돌아간다(§4-3).
- [ ] P로 나간 뒤 **F1·1~4가 다시 먹음**(`SetDebugKeysSuspended(false)` → `bDebugKeysEnabled`일 때 재추가; §12 #6·#55). 안 먹으면 §12 #55.
- [ ] 엔진 `DebugExecBindings` 충돌 없음(`!DebugExecBindings=ClearArray` 유지; P·`[ ]`·`- =`·`, .`·N M·Z C·F·H·O·R·E·Q·Enter·휠은 엔진 기본 바인딩과 겹치지 않는다). Esc는 PIE 종료(매핑 안 함).
- [ ] 게임패드(있으면; `IMC_GolmokPhoto` `MapKey` 목록, `photo.json` `hints.gamepad` 3줄 = `View exit  A shoot  Menu reset  R3 dof  B char` / `LS move  LT/RT down/up  RS look  L3 fast` / `DPad L/R fov  DPad D/U ev  LB/RB focus  X/Y f-stop`):

  | 기능 | 키 상수(`EKeys::`) | 확인 |
  |---|---|---|
  | 진입/종료 | `Gamepad_Special_Left`(View/Back) | [ ] (§12 #20: 에디터가 가로채면 대안) |
  | 촬영 | `Gamepad_FaceButton_Bottom`(A) | [ ] |
  | 이동 / 상승·하강 | `Gamepad_Left2D` / `Gamepad_RightTriggerAxis`(위)·`Gamepad_LeftTriggerAxis`(아래, Negate) | [ ] (§12 #19 트리거 축) |
  | 시선 | `Gamepad_Right2D`(Y Negate, 120°/s) | [ ] |
  | 빠르게 | `Gamepad_LeftThumbstick`(L3) | [ ] |
  | FOV −/+ | `Gamepad_DPad_Left` / `Gamepad_DPad_Right` | [ ] |
  | EV −/+ | `Gamepad_DPad_Down` / `Gamepad_DPad_Up` | [ ] |
  | focus −/+ | `Gamepad_LeftShoulder` / `Gamepad_RightShoulder` | [ ] |
  | f-stop −/+ | `Gamepad_FaceButton_Left`(X) / `Gamepad_FaceButton_Top`(Y) | [ ] |
  | DOF | `Gamepad_RightThumbstick`(R3) | [ ] |
  | 캐릭터 숨김 | `Gamepad_FaceButton_Right`(B) | [ ] |
  | 리셋 | `Gamepad_Special_Right`(Menu) | [ ] |
  | 롤·오버레이 | 패드 없음(힌트에 명시) | — |

## 4. 조절·화질
값 줄(오버레이 2행 = `PhotoFormatValue`: fov `%.1f`/오버레이는 `%.0f`, ev `%+.2f`, focus `%.3f`, f/ `%.2f`, roll `%+.1f`)과 화면을 함께 본다. 키는 `Started`만(길게 눌러도 반복 없음), 조절 때마다 `ApplyToPawn()`이 즉시 카메라 PP에 쓴다.
- [ ] `[` / `]` · 휠: FOV 5° 스텝, 20 ↔ 110에서 멈춤(`StepLinear`; 80 → `]` → `fov 85 (…)`). 화면 화각이 함께 바뀐다(`SetFieldOfView`).
- [ ] `-` / `=`: EV 1/3 스텝 `ev +0.33`·`+0.67`·`+1.00` … ±3.00에서 멈춤(`Quantize`, 9번 올리고 9번 내리면 정확히 `+0.00`). **정지 중에도 밝기가 즉시 바뀐다**(§12 #10; 안 바뀌면 #10 대안 순서대로 시도·§13에). EV `+0.00`의 밝기가 **진입 전과 같다**(카메라 오버라이드가 PPV 값을 대체하므로 `BaseExposureBias()`가 프리셋 bias를 다시 더한다 — §12 #9; 다르면 #9 대안).
- [ ] F → `dof on`; `,` / `.`: 초점 ×1.25 `focus 3.750 m`·`4.688 m` …, 0.300 ↔ 50.000에서 멈춤(`StepGeometric`, 3자리); N / M: `f/1.40 2.00 2.80 4.00 5.60 8.00 11.00 16.00` 표(`StepTable`). 가까운 물체에 초점을 두면 배경이 흐리고, F로 `dof off`면 전체가 선명(`DepthOfFieldFocalDistance = 0` — §12 #9 off 규약; 안 되면 #9 대안).
- [ ] Z / C: `roll -1.0` … ±15.0에서 멈춤, 수평선이 기운다(카메라 컴포넌트 상대 회전만; 액터는 pitch/yaw).
- [ ] H → 값 줄 끝에 `  [char hidden]`, 캐릭터 메시·**그림자**가 사라진다(`SetActorHiddenInGame`; 그림자가 남으면 §12 #21). 다시 H → 복귀. 충돌은 유지(구가 캐릭터 캡슐을 무시하므로 어차피 상호작용 없음).
- [ ] O → 오버레이 5줄 사라짐(`bOverlayHidden`), 다시 O → 복귀. 촬영에는 무관(촬영 프레임은 어차피 숨김).
- [ ] R → 값 5개 = JSON `default`(fov **65**, ev 0, focus 3, f/2.8, roll 0), DOF off, 캐릭터·오버레이 표시, 위치·회전 = 진입 시점, 오버레이 `fov 65 (28 mm)  ev +0.00  focus 3.000 m  f/2.80  dof off  roll +0.0`. `golmok.photo.set mult 3`으로 바꾼 세션 배율은 R 뒤에도 유지된다(오버레이 1행 끝 `3x`; §0 #12 — R이 지우는 목록에 배율은 없다).
- [ ] 콘솔 경로(키 없이 값 검증; `golmok.photo.set <fov|ev|focus|fstop|roll|dof|char|overlay|mult> <value>`):
  ```
  golmok.photo.set fov 35
  LogGolmok: golmok.photo.set: fov 35.0
  golmok.photo.set ev 0.4
  LogGolmok: golmok.photo.set: ev +0.33
  golmok.photo.set fstop 3
  LogGolmok: golmok.photo.set: fstop 2.80
  golmok.photo.set focus 0.1
  LogGolmok: golmok.photo.set: focus 0.300
  golmok.photo.set roll 40
  LogGolmok: golmok.photo.set: roll +15.0
  golmok.photo.set dof 1
  LogGolmok: golmok.photo.set: dof on
  golmok.photo.set char on
  LogGolmok: golmok.photo.set: character hidden
  golmok.photo.set overlay 1
  LogGolmok: golmok.photo.set: overlay hidden
  golmok.photo.set ev abc
  LogGolmok: golmok.photo.set: ERROR 'abc' is not a number
  golmok.photo.set xyz 1
  LogGolmok: golmok.photo.set: ERROR unknown name 'xyz' (fov|ev|focus|fstop|roll|dof|char|overlay|mult)
  golmok.photo.set fov
  LogGolmok: Warning: usage: golmok.photo.set <fov|ev|focus|fstop|roll|dof|char|overlay|mult> <value>
  golmok.photo.reset
  LogGolmok: golmok.photo.reset: reset (fov 65.0 ev +0.00 focus 3.000 f/2.80 dof off roll +0.0, character shown, overlay shown, pose restored)
  ```
  `ev -1.5`처럼 부호·소수가 `'…' is not a number`로 거부되면 §12 #42(`IsNumeric`)로 고친다. 포토 밖에서 `golmok.photo.set fov 35` → `golmok.photo.set: ERROR not active`, `golmok.photo.reset` → `golmok.photo.reset: ERROR not active`.
- [ ] **종료 밝기**(PR #27 리뷰 A2 67f9d8c `SetGameCameraCutThisFrame` → **V-09b 후속 수정 2(#64): `RestoreAll`이 뷰 타깃·제어 회전 복원 뒤 `PlayerCameraManager->UpdateCamera(0.f)`로 카메라 캐시를 플레이어 POV·PP로 갱신하고 그 다음 컷**): 기대값 — **종료 프레임(P를 처리한 틱이 그리는 프레임)부터** 플레이어 구도이고 밝기가 진입 전과 같다(V-09b: 종료 프레임 220.3 포토 화면 → 3.5 s 페이드 ✗). 기준 L = 진입 전 플레이어 화면(`shot showui` 가운데 60 % 휘도 평균, V-09b와 같은 방식). 판정: 종료 프레임·다음 프레임·0.25 s·1 s 모두 기준 ±5 이내, 종료 프레임이 포토 구도가 아니다. V-09b 드라이버의 틱 추적(post-tick 뷰 타깃·카메라 매니저 위치·`bGameCameraCutThisFrame`)을 같이 적는다 — 기대: P 종료 틱의 post-tick에서 **카메라 매니저 위치 = 플레이어 카메라**(V-09b는 포토 카메라 자리). 다음 조합을 EV `+3.00`과 `−3.00` 각각 한 번씩(각 조합 = 진입 → EV → 카메라를 1 m 이상 옮기기 → 촬영 → 창이 닫힌 뒤 P):
  1. **GamePause · 즉시 종료**(P) — V-09b 실패 경로. 가장 중요.
  2. **GamePause · 지연 종료**(Space 다음 틱에 P → `photo: exit deferred until the capture window closes (toggle)` → 창이 닫힌 뒤 `photo mode off (restored, unpaused, …)`) — V-09b ✅ 회귀 확인(종료 프레임부터 기준 ±5).
  3. **TimeDilation · 즉시 종료**: `Config\DefaultGame.ini` `PauseMode=TimeDilation` → **에디터 재시작** → 같은 절차(TimeDilation은 EV가 화면에 안 먹으므로(#61) 기준과 같으면 통과, 구도만 판정). 끝나면 `GamePause`로 되돌려 `git diff` 비어 있게.
  4. **사전 정지 (b)**(§12 #63 (b)): 콘솔 `pause` → P(`already paused`) → EV `+3`·카메라 이동 → P(`left paused`) → **정지가 유지된 채 종료 프레임부터 플레이어 구도·진입 전 밝기**(V-09b: `pause` 해제까지 포토 구도·221.7 고정 → 이번 수정의 기대는 즉시 플레이어 화면). 0.24 s 간격 10장에서 노이즈·깜빡임 없음, `pause` 해제 뒤에도 밝기 변화 없음. **정지가 유지되는 동안 둘째~10번째 프레임에 포토 구도 잔상·고스트 없음**(종료 프레임과 비교 — PR #40 리뷰 R1: 정지 중 `bIsCameraMoveableWhenPaused`가 false로 돌아가면 뷰 이력이 읽기 전용이라 포토 마지막 프레임의 TSR·Lumen 이력이 컷 1프레임 뒤 다시 보일 수 있어, 이제 정지가 풀릴 때까지 true로 둔다: P 뒤 로그 `photo: world still paused; camera-moveable-when-paused flag kept true until the unpause`, `pause` 해제 뒤 `photo: camera-moveable-when-paused flag restored after the unpause (false)` — §12 #67). 4가 ✗(잔상·고스트·깜빡임)면: §13에 관찰(프레임별 휘도·잔상 위치·로그 두 줄 유무)을 적고 §12 #67을 본 뒤 #64 대안 ②(다음 프레임 컷)를 검토한다.
  결과는 §13 "V-09c 재검증" 표에. 1이 여전히 ✗면 §12 #64 대안 ②(다음 프레임 컷)로.
- [ ] **화질 관찰**(§12 #8): 정지 상태에서 카메라를 움직이는 동안·멈춘 직후의 TSR 고스팅·Lumen 노이즈·눈 적응 정지 여부를 §13에 적고(스크린샷 ①에 담기게), 심하면 `PreCaptureFrames`를 올려 §5·§6에서 비교.

## 5. 촬영
Space(또는 Enter, 콘솔 `golmok.photo.shoot`). 순서: 같은 틱 `State = Shooting`(HUD·오버레이 숨김, 입력 동결) → `OnEndFrame` `PreCaptureFrames`(2) 뒤 메타 JSON 동기 기록 → `Debug->RequestHighResScreenshot` → `Captured` → PNG 존재 또는 실시간 3 s 중 먼저(최소 `PostCaptureFrames` 2) → `Active` + "saved" 줄 2.5 s.
- [ ] 로그(3줄; 콘솔이면 `golmok.photo.shoot: shooting -> …`가 하나 더):
  ```
  LogGolmok: photo: shooting -> <Saved>/Screenshots/Golmok/photo/<stamp>.png (2x, meta <stamp>.json)
  LogGolmok: photo: screenshot requested -> <Saved>/Screenshots/Golmok/photo/<stamp>.png (2x, written on the next frame)
  LogGolmok: photo: capture window closed (<stamp>.png present after 0.xx s)
  ```
  `present after` 값(수백 ms — §12 #14)을 §13에. `capture window closed (<stamp>.png timeout 3.0 s, png absent)`가 나오면 PNG가 3 s 안에 안 생긴 것(에디터 창이 뒤에 있는지 먼저 확인 — V-03; 그다음 §12 #13). `screenshot requested via HighResShot -> …00000.png (no viewport size; …)`는 뷰포트 크기를 못 얻은 것 — `-nullrhi`가 아닌 PIE에서는 나오면 안 된다.
- [ ] `<Project>\Saved\Screenshots\Golmok\photo\`에 `<stamp>.png` + `<stamp>.json`(프리셋 하위 폴더 없음; `golmok.screenshot`의 `Screenshots\Golmok\<tag>\<preset>\`과 다른 트리).
- [ ] PNG: 해상도 = 뷰포트 × 2, **디버그 HUD·포토 오버레이·"PAUSED" 없음**(`IsHudSuppressed()` → `DrawHUD` 즉시 반환; V-03에서 `golmok.screenshot`은 HUD를 포함했으므로 이것이 WP-12의 핵심 확인), H를 켰으면 **캐릭터 없음**, 이동 직후 촬영에 **번짐 없음**(`MotionBlurAmount = 0` — §12 #9). `stat` 텍스트가 들어갔으면 `stat none` 뒤 재촬영(§12 #12에 기록).
- [ ] 촬영 뒤 오버레이 복귀 + 초록 줄 2.5 s:
  ```
  saved <stamp>.png (2x)
  ```
- [ ] `<stamp>.json` — 키 15개, 순서·형식은 `FormatPhotoMetaJson`(한 필드 한 줄, 2칸 들여쓰기, 끝 `\n`; `Golmok.Photo.MetaJson`이 바이트 대조하는 예):
  ```
  {
    "version": 1,
    "time_utc": "2026-09-25T10:11:12Z",
    "preset": "overcast_morning",
    "zone_id": "z_synthetic_001",
    "zone_version": 1,
    "lon": 126.9250123,
    "lat": 37.5620456,
    "height_m": 51.234,
    "ue_location": [17670.59, -22698.00, 1190.00],
    "rotation": [-5.000, 90.000, 0.000],
    "fov": 65.0,
    "exposure_ev": 0.33,
    "dof": {"enabled": false, "focal_m": 3.000, "fstop": 2.80},
    "multiplier": 2,
    "character_hidden": false
  }
  ```
  대조: `time_utc` = 촬영 UTC(`FDateTime::UtcNow()`), `preset` = HUD `tod:`의 현재 프리셋(`None`이면 `null`), `zone_id`/`zone_version` = 오버레이 1행(없으면 둘 다 `null`), `lon`/`lat` ≈ HUD `pos … lat … lon …`(캐릭터가 아니라 **카메라 폰** 위치라 반경 3 m 안에서 다름; GeoOrigin 없으면 셋 다 `null`), `ue_location` = 폰 위치 2자리, `rotation` = 카메라 컴포넌트 월드 회전(`[pitch, yaw, roll]`, 롤을 줬으면 세 번째 값 — §12 #44), `fov` 1자리, `exposure_ev` 2자리(상대 EV), `dof.enabled` = F 상태, `multiplier` = **실효 배율**, `character_hidden` = H 상태.
- [ ] 같은 초에 두 번(Space 연타는 `capture in progress`로 막히므로 창이 닫히자마자 다시): 두 번째 스템 `<stamp>_2`(`.json`/`.png` 존재 검사).
- [ ] 캡처 창 중 거부(콘솔만 메시지, 키는 조용히):
  ```
  golmok.photo.shoot
  LogGolmok: golmok.photo.shoot: ERROR capture in progress
  golmok.photo.set fov 40
  LogGolmok: golmok.photo.set: ERROR capture in progress
  golmok.photo.reset
  LogGolmok: golmok.photo.reset: ERROR capture in progress
  ```
  캡처 창 중 P → `LogGolmok: photo: exit deferred until the capture window closes (toggle)` + `LogGolmok: P: exit deferred until the capture window closes` → 창이 닫힌 뒤 `photo: photo mode off (restored, unpaused, tod shift …)`(`P:` 줄은 다시 없음 — `Exit("deferred")`는 내부 호출). 콘솔 `golmok.photo 0`이면 `golmok.photo: exit deferred until the capture window closes`.
- [ ] `PreCaptureFrames=0`(ini, 에디터 재시작)으로도 PNG에 HUD·오버레이가 없는지(§12 #13: `Shoot()`의 상태 변경이 같은 프레임 `DrawHUD` 앞인지). 있으면 기본 2 유지로 §13에 기록. 끝나면 ini를 `2`로 되돌린다.
- [ ] (선택) 메타 실패 경로: `Saved\Screenshots\Golmok\photo\`를 읽기 전용으로 만들고 촬영 → `LogGolmok: Error: photo: ERROR cannot write meta <Saved>/Screenshots/Golmok/photo/<stamp>.json`, 스크린샷 요청 없음, 즉시 `Active` 복귀.

## 6. 배율 VRAM 표
RTX 5060 8 GB, 1440p 뷰포트 기준(설계 §6-6 추정치 검증). `stat RHI`(render target memory)는 촬영 **전에** 읽고 촬영 중에는 `stat none`; GPU 전용 메모리 피크는 작업 관리자. **3x는 OOM 크래시 가능성**이 있으니 다른 작업을 저장한 뒤 실행.
```
golmok.photo.set mult 2      → golmok.photo.set: mult 2      (오버레이 1행 끝 `2x`)
golmok.photo.set mult 3      → golmok.photo.set: ERROR multiplier must be 1..2 (MaxMultiplier)
golmok.photo.set mult 0      → golmok.photo.set: ERROR multiplier must be 1..2 (MaxMultiplier)
```
3x 측정은 `Config\DefaultGame.ini` `MaxMultiplier`를 **임시로 3**으로 바꿨을 때만 가능하다(그때 `mult 3` → `golmok.photo.set: mult 3`, `mult 4`·`mult 0` → `… 1..3 …`). 측정 뒤 2로 되돌리고 커밋하지 않는다(V-09 4834941 확정값 2, 3 복귀는 사용자 결정).
- [ ] 각 배율 3장(`golmok.photo.shoot`; 로그 `shooting -> … (3x, meta …)` → `screenshot requested -> ….png (3x, written on the next frame)` → `capture window closed (… present after x.xx s)`):

  | 배율 | 해상도(PNG 실측) | VRAM 피크 GB | 소요 s(`present after`) | PNG MB | 결과 |
  |---|---|---|---|---|---|
  | 1 | | | | | |
  | 2 (기본) | 5120×2880 기대 | | | | |
  | 3 (상한) | 7680×4320 기대 | | | | |

- [ ] 3x에서 강등이 일어나면 로그가 `(1x, written on the next frame) [multiplier reduced: the requested size exceeds the max texture size]`(`SetResolution` 거부 **또는** `TakeHighResScreenShot()` false → 1x 재시도; 괄호 문구는 두 경우 같다 — §12 #36), 메타 `"multiplier": 1`(재기록), 오버레이 `saved <stamp>.png (1x)`. 1x도 거부되면 `LogGolmok: Error: photo: ERROR screenshot request failed: screenshot refused by the viewport at 1x (too big for the GPU)` + JSON 삭제. 3x에서 스톨(수 초 멈춤)·강등·크래시면 `Config\DefaultGame.ini` `MaxMultiplier=2`로 커밋(`WP-12: PC fix MaxMultiplier 2`) — pytest `1 <= ScreenshotMultiplier <= MaxMultiplier <= 8` 안. 재기록이 실패하면 `photo: ERROR cannot write meta … (multiplier 3 recorded instead of 1)`(Warning; 앞 숫자가 **요청** 배율, 뒤가 실효 — 코드 순서 그대로).
- [ ] 1x·2x 크롭(같은 간판) 비교 → 계단·노이즈가 2x에서 심하면 `PreCaptureFrames`↑로 재촬영·비교하고 값과 판정을 §13에(§12 #8).
- [ ] 스크린샷 ② = 2x PNG 축소본(오버레이 없음).

## 7. 제약(`L_ZoneTest`)
**V-09 후속 재검증(2026-09-27 수정분 a6c48a3 → e03753e → 7f66810(footprint 침식 영역 최근접점)·6c36fd3(슬라이드)·67f9d8c(종료 카메라 컷)·PR #29 리뷰 A1(MoveInsetCm 앵커 상한))**: V-09에서 실패한 §7과 이번 수정이 더한 항목만 다시 한다 — §1 빌드·`test.ps1 -Filter Golmok.Photo` 3/3(새 (c2) `slide:` Info 줄 포함) → §7 → §4 "종료 밝기" → (가능하면) §10 패키지 잔상. 드라이버는 V-09와 같이 폰 위치를 **틱마다** 샘플(`GetActorLocation`, 틱 번호·y·경계 거리)해 §13에 표로 남긴다. 판정 기대값:
- footprint 남쪽 경계(V-09에서 y 980.0 ↔ 999.8 톱니): 경계 쪽으로 S(또는 해당 방향 키)를 누르고 있으면 샘플 y가 **단조 증가해 980.0(= 경계 − 20 cm)에서 멈추고 그 뒤 변동 0**(±0.01 cm 이내 — 틱 dt 반올림 외 없음). 999.x나 980 이하로 되돌아가는 샘플이 하나라도 있으면 ✗(§12 #58). 동쪽 경계도 같게.
- 같은 경계에서 대각선(경계 쪽 + 옆): 법선 좌표는 980.0 고정, 접선 좌표는 1.5 m/s × 접선 성분으로 계속 변한다(미끄러짐). 앵커(캐릭터)가 법선 위에 없어도 옆으로 끌리지 않는다(접선 입력 0이면 접선 좌표 불변).
- 볼록 모서리로 대각선: 두 경계 모두 20 cm 안쪽 꼭짓점에서 멈추고 변동 0. 오목 코너가 있으면 반경 20 cm 호를 따라 돈다(전의 "걸림" 없음). 구(3.3 m)와 경계가 만나는 곳으로 밀면 그 접합 앞 걷기 약 0.5~1.5 cm(Shift·저 FPS는 스텝에 비례해 수 cm~10 cm) 안에서 멈춘다(변동 0).
- 진입 시 카메라가 이미 경계 20 cm 안(띠 안)이면: 첫 이동에서 튀지 않고(샘플 간 이동 ≤ 150 cm/s × 그 틱 dt(Shift면 ×3; 드라이버가 틱마다 dt도 기록), 반사(오목) 꼭짓점을 도는 틱만 최대 2배 허용(설계 §11-7)), 바깥으로 밀면 그 자리 유지, 안쪽으로 움직이면 여유가 20 cm까지 다시 는다. 진입 카메라가 footprint 밖이면 첫 이동에서 안으로 들어간다(전과 같음, 튐 폭을 §13에).
- 벽(#60): 파사드에 대고 **W+D·W+A 대각선** → 표면 15 cm 앞 유지하며 벽을 따라 이동(V-09: 1 s 0.3 cm → 기대: 1 s에 1.5 m/s × sin(입사각)만큼, 45°면 ≈ 1.06 m). 모서리(두 벽)에서는 멈춤, 진동·관통 없음. 둔각(≈135°) 안쪽 꺾임에 W+D로 밀 때 두 번째 벽을 따라 이동하는지도 적는다(스윕 2회 제한이라 멈출 수 있음 — 멈추면 §13에 기록, 후속: 세 번째 스윕 또는 두 법선 각 < 90°면 재투영, PR #29 리뷰 B-1). 슬라이드가 footprint 경계에 닿으면 경계 20 cm 안쪽에서 멈춤(벽 → 다각형 재클램프).
- [ ] **벽**: 파사드·blocker(`glass_1`) 앞으로 밀기 → 표면에서 `CollisionRadiusCm`(15 cm) 앞에 정지, 관통 0(§12 #16). 밀착 상태에서 다른 방향으로 이동이 계속 된다(`bStartPenetrating` 후퇴가 매 틱 반복되면 §12 #40). **대각선으로 밀면 벽을 따라 미끄러진다**(위 기대값, §12 #60·#62). 스크린샷 ③.
- [ ] **구**: 캐릭터에서 3 m 밖으로 밀기 → 구 표면에서 정지, 오버레이 1행 거리 = 분모(`3.0 / 3.0 m`, 진입 카메라가 3 m 밖이었으면 그 거리로 넓어진 유효 반경, 예 `3.3 / 3.3 m` — `GetEffectiveRadiusCm()`). 첫 이동에서 카메라가 앵커 쪽으로 튀지 않는다. 위로도 같다(높이 상한 없음, 구만).
- [ ] **접합 수평 입력 시 높이 불변**(D-013 결정 3 확정판 — W/S/A/D는 항상 yaw 기준 수평면 이동, 높이(Z)는 Q/E만; V-09b 관찰 "구∩경계 접합에서 밀면 구면을 따라 내려감 −44 cm" 후속 수정 2 + PR #40 리뷰 M1/M2): 카메라를 앵커(캐릭터 중심)보다 **50 cm 이상 높이**(E) 둔다. 피치는 어떤 값이든 된다(전방이 yaw만이라 피치가 z에 들어가지 않는다). ① 구∩footprint 경계 접합으로 W+D(또는 해당 대각) Shift 2 s, ② 경계 없는 쪽에서 구 표면으로 W Shift 2 s, ③ 파사드 벽에 대각선 2 s. 기대(①~③): **틱 샘플 z 변동 0(±0.01 cm)**(V-09b ①은 1.6 s에 −44 cm), 수평면 안에서 미끄러지다 더 갈 수 없으면 정지(변동 0). ④ 같은 자리에서 **E 또는 Q를 같이 누르면** z가 변한다(구면을 따라 미끄러져도 됨). ⑤ 피치를 −30°로 숙이고 W만: **z 변동 0**(전방은 yaw만; 예전 설계 '피치 포함'은 결정 3 확정판으로 폐기) — 구·벽에 닿아도 같다. ⑥ (게임패드가 있으면) 트리거에 손가락을 살짝 얹은 채 스틱으로 ①을 반복 → z 변동 0. 콘솔 `showdebug enhancedinput`으로 `IA_GolmokPhotoUpDown` 값이 0 < |축| ≤ 0.1(데드존 `PhotoUpDownDeadZone`)인 구간이었는지 확인해 적는다(0이면 트리거에 닿지 않은 것 — 다시; 0.1을 넘으면 ④와 같은 3D 경로라 z가 변해도 정상; 표시가 안 나오면 §13에 '축 확인 불가'). ⑦ Q로 카메라를 낮게(바닥 근처) 두고 경사로(없으면 계단·기울어진 면, 그것도 없으면 벽)에 수평으로 정면으로 밀면 그 자리에서 정지하고 비스듬히 밀면 수평으로만 미끄러진다 — z 변동 0(경사를 타고 오르지 않는다, 올리려면 E). 예외: z가 바뀐 틱이 겹침 후퇴(`bStartPenetrating` → 앵커 쪽 10 cm, 3D)와 겹치면 §12의 후퇴 행으로 기록하고 결정 3 실패로 보지 않는다. 틱 샘플(틱·x·y·z·dt)을 §13에.
- [ ] **바닥**: 아래로(Q) → 바닥 15 cm 위에서 정지(로우 앵글 허용; 뚫고 내려가면 §12 #49).
- [ ] **footprint**: 캐릭터를 001 footprint 경계 1 m 안에 세우고(`golmok.collision 1`로 충돌 메시·blocker·트리거를 보며 경계 확인 → `golmok.collision: …`) P → 카메라를 바깥으로 → 경계 `FootprintMarginM`(0.2 m) 안쪽에서 **톱니 없이** 정지하고 대각선 입력이면 경계를 따라 미끄러진다(위 틱 샘플 기대값; 다각형 클램프, 구와 동시에 걸리면 둘 다 만족하는 점 또는 이동 취소 = 그 자리 유지). 예각 꼭짓점·20 cm의 두 배보다 좁은 목에서 멈추는 것은 설계 §11-7의 남은 한계 — 있었는지만 §13에.
- [ ] **zone 밖**: footprint 밖 도로(001 서쪽 등, `golmok.zone.list`의 어느 loaded zone에도 포함되지 않는 곳)에서 P →
  ```
  LogGolmok: photo: photo mode on (fov 80.0, no zone, paused)
  ```
  오버레이 1행 `PHOTO  no zone  overcast_morning  x.x / 3.3 m  2x`(분모 = `GetEffectiveRadiusCm()`: 진입 카메라가 3 m 밖이면 그 거리 + 1 cm, 아니면 `3.0`)가 **노랑**, 구·충돌만 작동, 메타 `zone_id`/`zone_version` 둘 다 `null`.
- [ ] **포털 타이머 관찰**(§12 #11, 둘 다 허용): ① 문 트리거 안(반경 1.5 m)에서 P → 30 s → P → `golmok.portal list` 상태 불변(`active` 그대로)·`Zone z_synthetic_001_interior v1 unloaded` 로그 없음(빙의를 바꾸지 않아 오버랩 변화가 없음). ② 트리거에서 나와 1 s 안에 P → 10 s → P → 실내 언로드(`Portal door_1: player left -> unload …`)가 **즉시**(정지 중 타이머가 흘렀음) 또는 **약 2 s 뒤**(타이머가 멈췄음)인지 §13에.

## 8. 실내
문으로 들어가(V-03 §5) 방 안에서 P.
- [ ] 로그 `photo: photo mode on (fov 80.0, zone z_synthetic_001_interior v1, paused)`(`FindLoadedZoneAt`: 실내 priority 20 > 실외 10, 문턱도 실내 우선), 오버레이 1행 `PHOTO  z_synthetic_001_interior v1  <preset>  … 2x`. 프리셋 칸·메타 `preset`은 `CurrentPreset`(base 프리셋 이름; 실내 오버레이 표기 없음).
- [ ] 실내 조명 오버레이(`TimeOfDay: interior overlay on …` 상태)가 정지 중 그대로 유지된다(전환 Tick 정지·`ShiftTransitionStart`).
- [ ] 카메라가 **벽·천장 밖으로 못 나간다**: 서브레벨 `SM_room` 충돌(BlockAll) + 방 footprint(8×6 m) 클램프. 방 밖(뒷면, 충돌 메시 없는 쪽)이 보이면 §13에.
- [ ] 촬영 → 메타 `"zone_id": "z_synthetic_001_interior"`, `"zone_version": 1`. 스크린샷 ④.
- [ ] P로 나간 뒤 `golmok.portal list` 불변(`active`), 실내 zone 로드 유지(`golmok.zone.list` 실내 행 `loaded … pinned`), 문으로 나가면 V-03 §5 그대로 오버레이 off·언로드.

## 9. 경로 재생 배제
- [ ] `golmok.path play quick` 중 **P** →
  ```
  LogGolmok: Warning: P: cannot enter while a path is playing (golmok.path stopplay first)
  ```
  콘솔 `golmok.photo 1` → `golmok.photo: ERROR cannot enter while a path is playing (golmok.path stopplay first)`. `golmok.path stopplay` 뒤 진입 가능.
- [ ] `golmok.path record tmp` 중 P → `P: cannot enter while recording 'tmp'`(이름은 `DescribePathState()`의 두 번째 토큰). `golmok.path stop` 뒤 `Saved\Golmok\Paths\tmp.json` 삭제.
- [ ] 포토 중:
  ```
  golmok.path play quick
  LogGolmok: golmok.path play: ERROR photo mode is on (golmok.photo 0 first)
  golmok.path record tmp
  LogGolmok: golmok.path record: ERROR photo mode is on (golmok.photo 0 first)
  ```
  설계와 다름: 설계 §9-9의 "F9 → `photo mode is on`"은 일어나지 않는다 — 포토 중에는 `IMC_GolmokDebug`가 제거돼 F9·F10이 아예 발화하지 않는다(`F9: …` 줄 없음). 콘솔 경로가 같은 검사를 지난다.

## 10. (선택) 패키징
- [ ] `.\tools\ue\package.ps1` → `UnrealPak <pak> -List | findstr /i "Config/Golmok"` → `Golmok/Config/Golmok/photo.json`(기존 `+DirectoriesToAlwaysStageAsUFS=(Path="../Config/Golmok")` 줄이 덮음; WP-05 `lighting_presets.json`과 같은 경로).
- [ ] 실행 파일에서 `open L_ZoneTest` → `golmok.photo 1` → `photo: config loaded (5 params) from ../../../Golmok/Config/Golmok/photo.json` → 오버레이 힌트 3줄이 JSON 값. 실패면:
  ```
  LogGolmok: Error: photo: config not loaded from ../../../Golmok/Config/Golmok/photo.json: photo.json: file: cannot read ../../../Golmok/Config/Golmok/photo.json
  LogGolmok: golmok.photo: ERROR cannot enter: photo.json: file: cannot read ../../../Golmok/Config/Golmok/photo.json
  ```
  → UFS 스테이징 문제(설계 §11-8) → §13. 두 번째 시도부터는 `bConfigFailed`가 남아 파일 접근 없이 같은 메시지(재시작해야 다시 읽음). 설계와 다름: 설계 §2-3은 `photo.json: <error>`만 적었으나 코드는 `cannot enter: ` 접두를 붙인다.
- [ ] 패키지에서 촬영 → `<GameDir>\Saved\Screenshots\Golmok\photo\<stamp>.png`+`.json` 생성.
- [ ] **잔상(§12 #57, PR #27 리뷰 A1)**: 패키지에서도 §4와 같은 장면(캐릭터가 화면에 있는 채 P → 카메라를 옆으로 옮기고 돌린 직후 촬영)에서 화면·PNG에 캐릭터 잔상이 없다. 엔진의 `bWorldIsPaused` 대입이 에디터 빌드 분기에만 있다면 패키지는 원래 잔상이 없고 c026815는 무해한 no-op — 결과(잔상 있음/없음)를 §13에.

## 11. PIE 종료
- [ ] **포토 모드 켠 채** Stop(Esc) →
  ```
  LogGolmok: photo: teardown (world ending)
  ```
  (`OnPhotoPawnEndPlay(EndPlayInEditor)` 또는 `Deinitialize` → `TeardownForDeadWorld()`; PC·정지·뷰 타깃·시간대는 건드리지 않음) 외에 Warning·Error·ensure 없음. `photo: photo mode off (restored, …)`가 종료 뒤에 찍히면 살아 있는 월드로 오판한 것(§12 #25) → §13.
- [ ] **캡처 창(Shooting/Captured) 중** Stop: `golmok.photo.shoot` 직후 Esc → 같은 `teardown` 한 줄, `capture window closed` 없음, `<stamp>.json`만 남고 PNG는 있을 수도 없을 수도(고아 JSON은 설계 §11-9의 허용 — 삭제하고 §13에).
- [ ] 종료 뒤 에디터 월드: 아웃라이너에 `GolmokPhotoCameraPawn`·Transient 액터 없음, `L_ZoneTest` dirty 아님(저장 프롬프트 없음), 에디터 뷰포트 정상.
- [ ] 다시 PIE → P가 처음처럼 동작(`config loaded` 1회 — 서브시스템은 월드마다 새로 만들어짐), 사전 정지 상태 남지 않음(`pause`가 필요 없음).
- [ ] (선택) 포토 중 `golmok.zone.unload z_synthetic_001`·`load`로 zone을 바꿔도 폰은 파괴되지 않는다(폰은 zone 소속이 아님). 폰을 강제로 지우면(`unreal`/디테일 Delete) `photo: exit (pawn destroyed)`(Verbose) 경로로 정상 복원 — `photo: photo mode off (restored, …)`.

## 12. 컴파일 에러가 나면 — 불확실한 UE 5.8 API와 대안 (설계 §10, 번호 유지) + 구현 세션 추가 행
클라우드 세션이 엔진 헤더로 직접 확인하지 못한 호출 목록. #1~#35는 설계 §10 그대로(번호 유지), **#36~#55는 구현 세션이 커밋 `9ec35ee`의 코드를 다시 읽어 표에 없던 호출을 보탠 것**, #56은 적대 검증에서 확인 불가로 남은 항목(엔진 소스·API 페이지 본문은 확인 불가 → 전부 가설), #57부터는 PC 세션이 보탠다. 오류 메시지에 아래 이름이 보이면 대안으로 바꾼다. `PC 결과` 열에 ✅(그대로 컴파일·동작) / 수정(대안·커밋) / 미확인을 적는다. 구현 행의 파일 경로는 `unreal/Golmok/Source/Golmok/` 기준. `Photo/` 소스는 수정마다 줄이 움직이므로 줄 번호 대신 함수·심벌 이름으로 인용한다(`test_ue_wp12_fixture.py::test_runbook_cites_photo_sources_by_symbol`).

| 번호 | 호출/가정 | 불확실한 점 | 대안 | PC 검증 | PC 결과 |
|---|---|---|---|---|---|
| 1 | `UGameplayStatics::SetGamePaused(const UObject*, bool)` → bool / `IsGamePaused` (`Kismet/GameplayStatics.h`) — BP 문서로 존재·bool 반환 [확인] | C++ 시그니처 [2차]; 내부 `APlayerController::SetPause` → `AGameModeBase::SetPause`(`AllowPausing` 기본 true [2차]) | `PC->SetPause(true)` / `World->IsPaused()`; 게임모드가 거부하면 `AGolmokGameMode::AllowPausing` override true | §2 캐릭터 애니 정지·로그 `paused` | ✅ 진입 시 `IsGamePaused` true(프로브), `already paused` 분기도 동작 |
| 2 | 폰 생성자 `PrimaryActorTick.bTickEvenWhenPaused = true` → 정지 중 `Tick` 호출 [확인 가이드 예시]; `DeltaSeconds` 값(0인지 실시간인지) [미확인] | 정지 틱의 dt 의미. 설계는 `FApp::GetDeltaTime()`(0.1 s 상한)을 쓰므로 무의존. `AActor::SetTickableWhenPaused`는 쓰지 않음(페이지 본문 없음) | 틱이 안 오면 ini `PauseMode=TimeDilation` | 자동화 EnterExit 틱 카운터 > 0 + §3 이동 부드러움 | ✅ 정지 중 폰 틱 정상: W 1 s = 1.46 m, Shift ×3 = 4.4 m/s(프로브) |
| 3 | `APlayerController::bShouldPerformFullTickWhenPaused`(public? 비트필드?) = true로 정지 중 `UpdateCameraManager`(뷰 타깃 폰의 카메라 반영) [2차 M1] — 페이지 본문 없음 [미확인] | 접근성·동작. 값은 `const bool bSaved = PC->…`로 복사(참조·포인터 금지) | 멤버가 private면 `AGolmokPlayerController::ShouldPerformFullTickWhenPaused() const` virtual override(`bPhotoFullTick` 플래그 반환) [2차]; 그래도 얼면 폰 Tick 끝에 `PC->PlayerCameraManager->UpdateCamera(dt)` [미확인]; 최후 `PauseMode=TimeDilation` | §3 이동 시 화면이 따라옴 | 수정(f5c8861): V-09 1차 빌드에서 C2248(protected) 확인 → `AGolmokPlayerController::GetFullTickWhenPausedFlag/SetFullTickWhenPausedFlag`로 원시 비트 스냅샷·복원. 동작(§3)은 미확인 / 동작 ✅: 정지 중 카메라 매니저가 폰을 따라감. 단 사전 정지 상태에서 나가면 정지가 풀릴 때까지 화면이 마지막 포토 카메라 구도에 머문다(뷰 타깃은 캐릭터로 복원됨, 풀틱 플래그 복원으로 카메라 매니저가 갱신 안 됨) — 관찰 |
| 4 | 정지 중 Enhanced Input: `UInputAction::bTriggerWhenPaused = true` [확인 필드] + PC 틱(풀틱 또는 약식)이 `TickPlayerInput(…, bGamePaused = true)` 수행 [2차 M2] | 발화 여부; 사전 정지(풀틱 아직 꺼진 상태)에서 P가 먹는지 | `PauseMode=TimeDilation` | §2 사전 정지 + P; §3 정지 중 WASD | ✅ 사전 정지(`pause`)에서 P 진입·WASD 이동·P 종료 모두 동작(`already paused` / `left paused`) |
| 5 | 풀틱 정지에서 캐릭터 `IMC_Default` 액션(`bTriggerWhenPaused = false`)이 발화하지 않음 + 포토 IMC(우선순위 3)의 `bConsumeInput` [확인 필드]이 같은 키를 하위로 넘기지 않음 [2차] | 소비·정지 게이트 규칙 | 캐릭터가 튀면 `AGolmokCharacter`에 `RemoveMappingContextForPhoto()` public 추가(PC fix 허용 범위) | §3 포토 중 WASD·마우스·Space → 나간 뒤 캐릭터 위치·회전 불변 | ✅ WASD·마우스·Space·Shift 난타 뒤 캐릭터 위치·회전 불변(0, 500, 94.2)/(0, 0, 0) |
| 6 | `UEnhancedInputLocalPlayerSubsystem::RemoveMappingContext(const UInputMappingContext*)`(디버그 컨텍스트 제거·포토 컨텍스트 제거; `AddMappingContext`는 V-03 확인) | 오버로드(`FModifyContextOptions` 기본 인자) [2차] | `RemoveMappingContext(Ctx, FModifyContextOptions())`; 없으면 `ClearAllMappings()` 뒤 필요한 것 재추가(캐릭터 IMC 포함) | §3 F키 무반응, 이탈 후 복귀 | ✅ 포토 중 1·F5·F9·F10·F1·F2 무반응(로그·프리셋 불변), 종료 뒤 F1·3 복귀 |
| 7 | `UEnhancedInputComponent::BindAction(Action, ETriggerEvent, UObject*, MemberFn)`에 `UWorldSubsystem` 메서드 바인딩(UFUNCTION 불필요) — WP-05가 PC 메서드로 확인 [확인]; 서브시스템도 `UObject` [2차] | 템플릿 제약 | 핸들러 21개를 `AGolmokPlayerController`에 두고 서브시스템으로 위임(①안) | 빌드 | ✅ 빌드(C++ 무수정) |
| 8 | 정지 중 뷰 이력 읽기 전용(`bWorldIsPaused` → `bStatePrevViewInfoIsReadOnly`) [2차 M4] → 이동 중 TSR 고스팅·Lumen 노이즈 고정·눈 적응 정지; 고해상도 프레임은 히스토리 없이 그려짐; `r.HighResScreenshotDelay` cvar 존재 [미확인] | 화질 | `PauseMode=TimeDilation`; `PreCaptureFrames`↑; cvar 있으면 값 ↑ 실험 | §4 이동 중·정지 후 화면, §6 1x/2x 크롭 비교 | 수정(c026815, #57): 이동 중·정지 1 s 뒤에도 캐릭터 잔상이 화면과 HighResShot PNG에 남음(H로 숨겨도) — 이력 읽기 전용이 원인. `PreCaptureFrames`↑로는 못 고침. `PauseMode=TimeDilation`은 잔상 없음(대신 #61). 눈 적응은 정지 중에도 실시간으로 돈다(#10). `r.HighResScreenshotDelay` 미시험 |
| 9 | 카메라 컴포넌트 `PostProcessSettings` 오버라이드: `bOverride_AutoExposureBias/AutoExposureBias` [확인 V-03 볼륨 동일 필드], `bOverride_DepthOfFieldFocalDistance/DepthOfFieldFocalDistance(cm)`, `bOverride_DepthOfFieldFstop/DepthOfFieldFstop`, `bOverride_MotionBlurAmount/MotionBlurAmount` [2차 이름], `PostProcessBlendWeight`; `FocalDistance = 0` = DOF 끔 [2차]; 카메라 오버라이드가 PPV 값을 **대체**(가산 아님) [2차]; 정지 중 뷰에 적용 [2차] | 필드명·off 규약·대체 규칙 | 이름은 오류 메시지대로(`Scene.h` grep); DOF off가 안 되면 `Fstop = 16`·`FocalDistance = 5000 cm`로 근사; EV 0 밝기가 다르면 base 재가산 제거 | §4 DOF on/off·EV ±3·EV 0 밝기 동일, §5 번짐 없음 | ✅ 필드명 컴파일, EV +0.00 밝기 = 진입 전(안정 장면 116.8 vs 116.9, 휘도 평균), DOF off = `FocalDistance 0`, `MotionBlurAmount 0`으로 이동 직후 촬영 번짐 없음 |
| 10 | 정지 중 노출 바이어스 변경이 **즉시** 화면에 반영(눈 적응 히스토리가 멈춰도 bias는 곱셈) [2차] | 눈 적응 정지로 EV 변화가 안 보일 가능성 | `bOverride_AutoExposureSpeedUp/Down = true, 값 20`(포토 동안만) → 그래도면 `bOverride_AutoExposureMethod = true, AEM_Manual`(런북에 화면 차이 기록) | §4 EV | 수정(c026815): EV가 즉시가 아니라 2~4 s에 걸쳐 수렴(기본 3/1 EV/s) → 촬영 직전 EV를 바꾸면 반쯤 적응된 노출이 찍힘. 대안 1(`AutoExposureSpeedUp/Down` 20)로 0.3 s 안 수렴(실측). 대안 2(수동 노출) 불필요 |
| 11 | 월드 `FTimerManager`(포털 Debounce/Unload/Preload, zone Evaluate)가 게임 정지에 멈추는지 — 문서 언급 없음 [확인: 없음] → [미확인] | 엔진 동작 | 설계 무의존(빙의 안 함 + 캐릭터 정지 → 오버랩 변화 없음); 관찰만 | §7 30 s 대기·10 s 대기 | 관찰: 정지 중 월드 타이머 멈춤 — 트리거 밖으로 나와 0.5 s 뒤 P, 10 s, P → 실내 언로드는 종료 2.44 s 뒤(타이머 정지). 트리거 안 30 s는 상태 불변(`active`) |
| 12 | `UGameViewportClient::SetSuppressTransitionMessage(bool)` / `bSuppressTransitionMessage` 멤버로 정지 "PAUSED" 전환 메시지 억제(`DrawTransition`) [2차 M5] — 페이지 본문 없음 [미확인]; 고해상도 재렌더에 그 메시지·`stat`·온스크린 메시지가 포함되는지 [미확인] | 존재·시그니처·포함 여부 | 줄 삭제 후 관찰; 메시지가 사진에 남으면 `PauseMode=TimeDilation` | §2 정지 화면, §5 PNG 중앙 | 수정(f5c8861): `bSuppressTransitionMessage` protected·getter 없음(C2248) → `UGolmokGameViewportClient::IsTransitionMessageSuppressed()` + `DefaultEngine.ini` `GameViewportClientClassName`; 쓰기는 `SetSuppressTransitionMessage`. 사진 포함 여부(§5)는 미확인 / 동작 ✅: Warning 없음, 포토 화면·PNG에 "PAUSED" 없음. 단 PIE에서는 엔진 `pause`만으로도 "PAUSED"가 보이지 않아 억제 효과 자체는 구별 불가 |
| 13 | `FViewport::TakeHighResScreenShot()`(`bool` [확인 문서])이 정지 중에도 다음 `Draw`에서 처리·파일 기록 [2차; V-03은 비정지]; 3x에서 false 반환 가능("too big for the GPU") [확인 문구]; `AGolmokHUD::DrawHUD`가 재렌더 프레임에도 호출됨 [확인 V-03 HUD 포함]; `Shoot()`의 상태 변경이 같은 프레임 `Draw` 전 [2차] | 정지 중 동작·순서 | 안 찍히면 요청 틱만 1프레임 언포즈(`SetGamePaused(false)` → 요청 → 다음 틱 `true`); false면 1x 재시도·메타 실효값(설계); 순서가 틀리면 `PreCaptureFrames ≥ 1`이 흡수 | §5 파일 생성·HUD 없음, §6 3x | ✅ 정지 중 HighResShot 생성, `PreCaptureFrames` 2·0 모두 PNG에 HUD·오버레이 없음, 3x도 거부 없음(`TakeHighResScreenShot` true) |
| 14 | 고해상도 PNG 쓰기가 비동기(`FImageWriteQueue`) → 수백 ms 뒤 등장 [2차]; PNG 존재 폴링(`IFileManager::FileExists`)으로 숨김 해제 | 시점 | 실시간 3 s 타임아웃이 최종 방어(설계); `-nullrhi`는 타임아웃 경로 | 자동화 MetaJson·§5 로그 대기 시간 | ✅(시간은 설계보다 김) `present after` 1x 0.49 s / 2x 1.43~2.16 s / 3x 2.97~6.29 s. 저장 프레임 하나가 게임 스레드를 멈춘다(1x 0.32 s, 2x 1.2 s, 3x 2.4 s + 렌더) — #59 |
| 15 | `FCoreDelegates::OnEndFrame`가 정지 중에도 발화 [2차; `-nullrhi` 발화는 V-03 확인] | — | 실시간 타임아웃 + 폰 틱 카운터(정지 틱)로 이중화 | 자동화 MetaJson | ✅ 정지 중 OnEndFrame 발화(캡처 창 정상 종료) |
| 16 | `AActor::SetActorLocation(P, /*bSweep*/ true, &Hit)`가 `USphereComponent` 루트(QueryOnly, WorldDynamic)로 벽에서 멈춤; `FHitResult::bStartPenetrating`; `UWorld::OverlapBlockingTestByChannel(Pos, Quat, ECC_WorldDynamic, FCollisionShape::MakeSphere(r), Params)`; Chaos 삼각형 메시 뒷면 스윕 [미확인] | 스윕 적용·뒷면 | `World->SweepSingleByChannel(Hit, From, To, FQuat::Identity, ECC_WorldDynamic, MakeSphere(r), Params)` 후 `SetActorLocation(Hit.Location, false)`; 뒷면은 설계 무의존 | 자동화 Clamp (c) + §7 벽 | ✅ 파사드 앞 y −964.6(면 −980, 15.4 cm), 실내 북벽 −1564.6·천장 284.9·서벽 135.4 cm(각 면에서 15 cm), 관통 0 |
| 17 | 빙의 안 한 `APawn`을 `SetViewTargetWithBlend(Pawn, 0)` → `APawn::CalcCamera`가 카메라 컴포넌트 사용(`bFindCameraComponentWhenViewTarget` 기본 true) [2차]; `GetViewTarget/SetControlRotation/GetControlRotation` [확인 V-03] | 비빙의 뷰 타깃의 카메라 컴포넌트 사용 | `AActor::CalcCamera` override로 카메라 컴포넌트 값 직접 반환 | EnterExit `GetViewTarget()` + §2 화면 | ✅ 뷰 타깃 = 포토 폰, 화면이 폰 카메라 |
| 18 | `APlayerCameraManager::GetCameraLocation/GetCameraRotation` [확인 코드 사용 중] · `GetFOVAngle()` [2차] | FOV getter 이름 | `PC->GetPlayerViewPoint(Loc, Rot)` + `Cam->GetCameraCacheView().FOV`; 실패 시 80 | EnterExit FOV 단언 | ✅ 진입 FOV 80(캐릭터 카메라) |
| 19 | `EKeys::` 이름: `P H O R Z C N M E Q Enter LeftBracket RightBracket Hyphen Equals Comma Period MouseWheelAxis Gamepad_Special_Left/Right Gamepad_DPad_* Gamepad_LeftShoulder/RightShoulder Gamepad_FaceButton_* Gamepad_RightThumbstick` [확인 EKeys 페이지]; `Gamepad_LeftTriggerAxis` [확인 J-product F7]·`Gamepad_RightTriggerAxis` [2차]; 휠 Axis1D 값이 노치당 ±1·`Triggered` 1프레임 [2차]; 트리거 축 0..1 + `UInputModifierNegate` [2차] | 축 이름·값 의미 | 오류난 이름만 `InputCoreTypes.h` grep; 휠은 부호만 사용(설계); 트리거는 `Gamepad_LeftTrigger/RightTrigger`(버튼) Bool 두 액션으로 | 빌드 + §3 휠 1노치 = 5°·LT/RT | ✅ 키 이름 컴파일, 휠 1노치 = 5°(위 = 좁게). 트리거 축은 패드 없음으로 미확인 |
| 20 | `Gamepad_Special_Left`·P가 PIE에서 에디터에 가로채이지 않음; Esc = PIE 종료 | [2차] | 게임패드 토글을 `Gamepad_Special_Right`로 교체(코드 상수) | §2 | ✅ P는 에디터가 가로채지 않음(PIE 새 창). 패드 토글 미실행(패드 없음) |
| 21 | 캐릭터 `SetActorHiddenInGame(true)`가 그림자까지 제거 | [2차] | 메시 `SetCastShadow(false)` 병행·복원 | §4 H 후 그림자 | ✅ H로 캐릭터와 그림자 함께 사라짐(clear_noon 발밑 그림자 비교) |
| 22 | `UPROPERTY(Transient) TArray<TObjectPtr<UInputAction>>`(GC 보관) | 리플렉션 가능 [2차] | 액션별 멤버 21개(한 줄에 하나 — UHT는 콤마 다중 선언 거부) | UHT/빌드 | ✅ UHT/빌드 |
| 23 | `UGameplayStatics::SetGlobalTimeDilation/GetGlobalTimeDilation`, `AWorldSettings::MinGlobalTimeDilation`(0.0001), `AActor::CustomTimeDilation`(폴백 경로만) | [2차] | `World->GetWorldSettings()->SetTimeDilation`; 하한 위반이면 `MinGlobalTimeDilation` 값으로 | `PauseMode=TimeDilation`일 때만 | ✅ `PauseMode=TimeDilation` 경로 동작(0.0001, 복원 1.0) — 단 #61 |
| 24 | `FDateTime::UtcNow().ToString(TEXT("%Y-%m-%dT%H:%M:%SZ"))`·`Now().ToString(TEXT("%Y%m%d_%H%M%S"))` [확인 V-03 경로 JSON·스크린샷] | — | — | 메타 `time_utc` | ✅ 메타 `time_utc` 형식 |
| 25 | `UWorld::bIsTearingDown`·`DoesSupportWorldType` [확인 V-03]; `EEndPlayReason::Destroyed/EndPlayInEditor/Quit/LevelTransition/RemovedFromWorld` [2차 이름] | enum 값 이름 | 오류 메시지대로 | 빌드 + §11 PIE 종료 | ✅ PIE 종료 시 `photo: teardown (world ending)` 1줄 |
| 26 | 자동화 latent 명령이 PIE 정지 중에도 매 엔진 프레임 `Update()` | [2차] | 테스트 타이밍 전부 `FPlatformTime`(설계) | 자동화 EnterExit | ✅ 헤드리스 26/26 |
| 27 | `TActorIterator`는 쓰지 않음; `UGolmokZoneSubsystem::FindLoadedZoneAt` 안에서 `TWeakObjectPtr<AGolmokZone>::Get()`(non-const)로 `FootprintContains`(non-const) 호출 [확인 자체 코드] | const 메서드 안 호출 규칙 | 레코드 순회를 non-const 헬퍼로 | 빌드 | ✅ 빌드 |
| 28 | `UGolmokGeoSubsystem::LevelUEToLonLat(const FVector&, double& Lat, double& Lon, double& H)`·`HasOrigin()` [확인 자체 코드, 인자 순서 Lat·Lon] | — | — | 메타 lon/lat 대조 | ✅ 메타 lon/lat 값 있음(L_ZoneTest GeoOrigin) |
| 29 | `AGolmokTimeOfDay::CaptureState(FGolmokLightingState&)`·`DefaultAutoExposureBias()`·`IsTransitioning()`·`GetTransitionAlpha()` [확인 자체 코드]; 새 `ShiftTransitionStart`는 `TransitionStart`(private double)만 옮김 | — | — | EnterExit 드리프트 단언 | ✅ 전환 드리프트 16% → 10 s 포토 → 25%(바깥 0.6 s분만 진행) |
| 30 | MSVC C4458: 서브시스템 멤버 `Values/Config/State`·폰 `Look/RollDeg` vs 인자·**로컬 변수**; 멤버 함수 `StepParam`과 `GolmokPhotoMath::` 자유 함수 이름 충돌 | pytest 정적 검사(인자 `In*`/`Out*`, 로컬 `New*`/`Local*`, 한정 호출) | 이름 변경 | 빌드 | ✅ 빌드(경고 0) |
| 31 | `UCanvas::SizeX/SizeY`로 왼쪽 아래 배치(`DrawHUD`에서 `Canvas` 유효 [확인 V-03]) | [2차] | `Canvas->ClipX/ClipY` | §2 오버레이 위치 | ✅ 오버레이 왼쪽 아래 |
| 32 | 유니티 빌드: `Photo/*.cpp` 익명 namespace(`PhotoSubsystemFor`, `PhotoParseToggle`, `CmdPhoto*`)·명명 `GolmokPhotoJson` | Debug의 `ParseToggle`·`DebugSubsystemFor`, Lighting의 `GolmokLightingJson`과 충돌 금지 | 접두 유지(pytest) | 빌드 | ✅ 빌드 |
| 33 | photo.json 파싱 `TryGetField(FStringView)`·`AsNumber/AsString/AsArray/AsObject/AsBool`, 키 열거 `FString(*Pair.Key)` [확인 V-03] | — | — | MetaJson 파서 케이스 | ✅ `config loaded (5 params)` |
| 34 | `FActorSpawnParameters{ObjectFlags \| RF_Transient, SpawnCollisionHandlingOverride = AlwaysSpawn}` [확인 V-03 포털·재생 폰] | — | — | — | ✅ |
| 35+ | (PC 세션 추가) | | | | |
| 36 | `Debug/GolmokDebugSubsystem.cpp:1077-1085` — `View->TakeHighResScreenShot()`가 false를 반환한 뒤 **같은 프레임**에 `FHighResScreenshotConfig::SetResolution(…, 1.f)` + `SetFilename` 재설정 후 `TakeHighResScreenShot()` 재호출 | false 반환 뒤 config 내부 상태(더티 플래그·요청 큐)가 남아 두 번째 호출이 받아들여지는지, 또는 첫 요청이 부분적으로 등록돼 다음 Draw에 3x가 시도되는지 [미확인] | 재시도를 다음 틱(`OnEndFrame`)으로 미루거나, false면 그 샷을 거부하고 메타에 `multiplier: 실효값`만 기록 | 런북 §6 3x → false 로그와 1x PNG 실제 생성 여부 | 미확인: 3x도 거부되지 않아 1x 재시도 경로는 발생하지 않음 |
| 37 | `Photo/GolmokPhotoCameraPawn.cpp` `ApplyLook` — `SetActorRotation(Look, ETeleportType::TeleportPhysics)` 2-인자 오버로드 | 기존 모듈은 `SetActorRotation(FRotator)`·`SetActorLocationAndRotation(…, ETeleportType)`만 사용. `AActor::SetActorRotation(FRotator, ETeleportType = None)` 존재는 가설 | `SetActorRotation(Look)`(폰은 물리 없음) 또는 `SetActorLocationAndRotation(GetActorLocation(), Look, false, nullptr, TeleportPhysics)`[기존 코드 확인] | 빌드 | ✅ 빌드 |
| 38 | `Photo/GolmokPhotoCameraPawn.h` 멤버 선언부 — 폰 멤버 `TWeakObjectPtr<UGolmokPhotoModeSubsystem> Owner`(UPROPERTY 아님)가 `AActor::Owner`(private UPROPERTY)를 가림 | UHT는 UPROPERTY가 아니므로 통과할 가능성이 크지만, `GetOwner()`와 의미 충돌·MSVC 경고(C4458은 로컬/인자 전용이라 해당 없음; 멤버 은닉 경고 없음)는 [미확인] | `PhotoOwner`로 개명(코드 4곳 + 주석) | 빌드 | ✅ 빌드 |
| 39 | `Photo/GolmokPhotoCameraPawn.cpp` `Tick`(`Look.Vector()`), `Tests/GolmokPhotoTest.cpp:578` — `FRotator::Vector()` | 모듈 최초 사용(`NormalizeAxis`·`RotateVector`는 `GolmokCharacterTest.cpp`에 기존). 존재·정규화 방향 벡터 반환은 [2차] | `FRotationMatrix(Look).GetUnitAxis(EAxis::X)` | 빌드 + Clamp 테스트 (d) 방향 | ✅ 빌드 + Clamp (d) |
| 40 | `Photo/GolmokPhotoCameraPawn.cpp` `MoveConstrained` — `Hit.bStartPenetrating`이면 `SetActorLocation(Location + Retreat, /*bSweep*/ true)`로 10 cm 후퇴 | 관통 시작 상태에서의 스윕 이동은 엔진이 0-거리 블로킹으로 **이동을 거부**할 수 있음(캐릭터 무브먼트만 관통 해소를 함) → 후퇴가 실행되지 않고 매 틱 반복 [미확인]. §10 #16은 `bStartPenetrating` 존재만 다룸 | 후퇴는 `bSweep=false` 텔레포트로(앵커 쪽은 자유 공간이라 안전), 또는 `Hit.PenetrationDepth * Hit.Normal`로 밀어내기 | 런북 §7 벽 밀착 후 이동 가능 여부; 자동화 Clamp (c) | ✅(부분) 벽에 밀착한 채 평행 이동은 계속됨(A/D 1 s ≈ 1.5 m). 단 벽 쪽 성분이 있는 대각 입력(W+D)은 1 s 동안 0.3 cm — 면을 따라 미끄러지지 않음(#60) |
| 41 | `Photo/GolmokPhotoModeSubsystem.cpp` 파일 머리 include·`Enter()`(`FCollisionQueryParams QueryParams(FName(TEXT("GolmokPhotoEnter")), …)`) — `#include "CollisionQueryParams.h"`·`"CollisionShape.h"` + `FCollisionQueryParams(FName, bool bTraceComplex)` 생성자 | 두 헤더 경로(`Engine/Public/` 직하)와 생성자 인자 순서는 [2차]; 모듈 최초 사용 | `Engine/World.h`가 이미 끌어오므로 두 include 삭제; 생성자는 `FCollisionQueryParams Params; Params.TraceTag = …` | 빌드 | ✅ 빌드 |
| 42 | `Photo/GolmokPhotoModeSubsystem.cpp` `CmdPhotoSet`(익명 namespace) — `FString::IsNumeric()`, `FCString::Atod`, `FCString::Atoi` | 모듈은 `FCString::Atof`만 사용해 왔음. `Atod`(double) 존재·`IsNumeric`이 `-1.5` 같은 부호·소수를 true로 보는지 [2차] | `FCString::Atof` + `static_cast<double>`; 검증은 `LexTryParseString<double>` | 빌드 + `golmok.photo.set ev abc` 거부 메시지 | ✅ `ev -1.5` → `ev -1.33`(부호·소수 수용), `ev abc` 거부 |
| 43 | `Photo/GolmokPhotoModeSubsystem.cpp` `Enter()`(`DescribePathState().ParseIntoArrayWS(Parts)`) — `FString::ParseIntoArrayWS(TArray<FString>&)` 기본 인자 | 모듈은 `ParseIntoArray`·`ParseIntoArrayLines`만 사용. `ParseIntoArrayWS`의 기본 `pchExtraDelim=nullptr, InCullEmpty=true` [2차]; `DescribePathState()` 문자열 형식 의존 | `ParseIntoArray(Parts, TEXT(" "), /*bCullEmpty*/ true)` | 빌드 + EnterExit "path plays → Enter 거부" 단언 | ✅ 경로 재생·녹화 중 진입 거부 문구 |
| 44 | `Photo/GolmokPhotoModeSubsystem.cpp` `BuildMeta` — 메타 회전에 `Camera->GetComponentRotation()`(카메라 컴포넌트 월드 회전) | 모듈 최초 사용. `bUsePawnControlRotation=false`·상대 회전 0이므로 폰 회전과 같아야 하나, 롤 적용 후 컴포넌트 월드 회전이 `Look`과 동일한지(짐벌·정규화 차이) [2차] | `PhotoPawn->GetActorRotation()`으로 통일(이미 폴백) | 자동화 MetaJson 회전 값 vs 로그; 런북 §5 메타 yaw/pitch/roll | ✅ 롤 5° 촬영 → 메타 `rotation` 세 번째 값 5.000 |
| 45 | `Photo/GolmokPhotoModeSubsystem.cpp` `Enter()` 첫 검사 — `World->WorldType == EWorldType::Game \|\| … PIE` 멤버 직접 읽기 | 기존 모듈은 `DoesSupportWorldType(EWorldType::Type)` 인자만 비교. `UWorld::WorldType`이 public `TEnumAsByte<EWorldType::Type>`인지 [2차] | `World->IsGameWorld()` | 빌드 | ✅ 빌드 |
| 46 | `Tests/GolmokPhotoTest.cpp:1082-1106` — `FJsonObject::SetNumberField/SetStringField/SetBoolField/SetArrayField/GetObjectField(TEXT("…"))`에 TCHAR 리터럴 | V-03에서 확인된 것은 `TryGetField(FStringView)`·`FString(*Pair.Key)`뿐. 5.8 `UE::FSharedString` 키에서 Set*/GetObjectField의 인자형(`FStringView`? `const FString&`?)과 TCHAR* 암시 변환·모호성 [미확인] | 오류 시 `FString(TEXT(…))` 또는 `FStringView(TEXT(…))`로 감싸기; 실패한 오버로드만 오류 메시지대로 | 빌드 (MetaJson/ParseConfig 테스트) | ✅ 빌드 |
| 47 | `Tests/GolmokPhotoTest.cpp:584-593` — 맨 `AActor` 스폰 → `NewObject<UBoxComponent>` → `SetMobility/SetBoxExtent/SetCollisionProfileName(BlockAll)` → `SetRootComponent` → `RegisterComponent` → `SetActorLocationAndRotation` | 기존 `GolmokZone.cpp`는 자기 액터 안에서 컴포넌트를 만듦; 루트 없는 `AActor` 스폰의 위치가 유지되는지, `RegisterComponent` 전 프로파일 설정이 물리 상태에 반영되는지, `WorldDynamic` 구 스윕이 이 박스를 Block 하는지 [2차] | 스폰 시 `AStaticMeshActor` 대신 프로파일을 `RegisterComponent` 뒤 `SetCollisionProfileName` 재호출·`UpdateBounds`; 최후 (d) 단언을 `AddInfo`로 강등 금지 → 스폰 지점을 폰 앞 50 cm로 좁힘 | 자동화 Clamp (d) | ✅ Clamp (d) face distance 16.5 |
| 48 | `Tests/GolmokPhotoTest.cpp:538,586` — `if (Test->TestNotNull(…))` bool 반환 사용; `TestEqual(*FString::Printf(…), Keys[i], FString(…))`(`const TCHAR*` 설명 + `FString,FString`), `TestEqual(TEXT(…), Num(), 4)`(int32,int32) | 기존 모듈은 `TestNotNull`을 표현식으로 쓰지 않음; `FAutomationTestBase::TestNotNull`이 bool을 반환하는지, `TestEqual(const TCHAR*, const FString&, const FString&)`·`(const TCHAR*, int32, int32)` 오버로드 해석(`Num()`은 int32, 리터럴 int) [2차] | `TestNotNull` 뒤 별도 `if (!Pawn) return;`; 모호하면 `static_cast<int32>` | 빌드 | ✅ 빌드 |
| 49 | `Tests/GolmokPhotoTest.cpp:562-568` — L_Dev 바닥 가정: `-500 z` 이동 시 구 스윕이 바닥(캐릭터 발 = 캡슐 반높이 아래)에서 멈춰 `Z >= FloorZ - R - 20` | L_Dev 바닥 액터의 충돌(WorldStatic Block)·위치가 캐릭터 발과 일치한다는 가정 [미확인]; 구 제약(반경) 또는 footprint가 먼저 걸리면 바닥과 무관하게 통과할 수 있음 | 바닥 판정을 `Debug` 로그 + 완화 단언(구 내부)으로 이원화; 런북에서 시각 확인 | 자동화 Clamp (b) + 런북 §7 바닥 | ✅ Clamp (b) + GUI 바닥 15.1 cm |
| 50 | `Tests/GolmokPhotoTest.cpp:329-339` — `Tod->TransitionSeconds = 0.5f; Tod->ApplyPreset(TEXT("clear_noon"))`이 `IsTransitioning()` true로 시작한다는 가정(드리프트 단언 선행 조건) | 현재 프리셋이 이미 `clear_noon`이거나 `ApplyPreset`이 즉시 스냅(전환 0)하면 skip 경로(AddInfo)로 빠져 `ShiftTransitionStart` 단언이 실행되지 않음 [확인 자체 코드: skip 처리됨]; `TransitionSeconds`가 public UPROPERTY로 쓰기 가능한지 [2차] | 다른 프리셋(`overcast_morning`)으로 먼저 옮긴 뒤 `clear_noon`; 멤버가 private면 `SetTransitionSeconds` 추가 | 자동화 EnterExit 로그에 "drift assertion skipped"가 없어야 함 | ✅ skip Info 없음 |
| 51 | `Tests/GolmokPhotoTest.cpp:1050` — `GetDefault<UGolmokPhotoModeSubsystem>()->ResolveConfigPath()`(월드 서브시스템 CDO의 const 메서드 호출) | `UWorldSubsystem` CDO에 월드 없이 접근·`ResolveConfigPath() const`가 멤버 상태에 의존하지 않는지 [확인 자체 코드: const]; CDO 생성 여부는 [2차] | `static FString ResolveConfigPathStatic()` 또는 `UGolmokPhotoModeSubsystem::Get(World)->ResolveConfigPath()` | 빌드 + ParseConfig 테스트 | ✅ |
| 52 | `Photo/GolmokPhotoModeSubsystem.cpp` `OnFovWheel`·`OnUpDown` — `FInputActionValue::Get<float>()`(Axis1D: 휠·상하) | 모듈은 `Get<FVector2D>()`만 사용. Axis1D 액션에 `Get<float>()` 템플릿 특수화가 있는지, Bool 액션에서 호출하면 체크 실패인지 [2차] | `Value.GetMagnitude()` | 빌드 + 런북 §3 휠·E/Q | ✅ 휠·E/Q |
| 53 | `Photo/GolmokPhotoCameraPawn.cpp` 파일 머리 include·`ApplyOptics` — `#include "Engine/Scene.h"` + `UCameraComponent::PostProcessSettings`(public `FPostProcessSettings`) 직접 쓰기 | 필드명은 §10 #9; 멤버가 public이며 `CameraComponent.h`만으로 완전한 타입이 되는지, `Engine/Scene.h` 경로 [2차] | `Camera->PostProcessSettings`가 안 되면 `Camera->PostProcessBlendWeight`+`FPostProcessSettings` 로컬 후 대입; include는 `CameraComponent.h`가 끌어오면 삭제 | 빌드 | ✅ 빌드 |
| 54 | `Tests/GolmokPhotoTest.cpp:563` — `UCapsuleComponent::GetScaledCapsuleHalfHeight()`(`Components/CapsuleComponent.h`) | 모듈 최초 사용; 이름·스케일 포함 의미 [2차] | `GetUnscaledCapsuleHalfHeight()` 또는 상수 92 | 빌드 | ✅ 빌드 |
| 55 | `Photo/GolmokPhotoModeSubsystem.cpp` `AddPhotoContext(bool)` — 서브시스템이 `AddMappingContext(PhotoContext, 3)`/`RemoveMappingContext(PhotoContext)`를 **PC 소유 `AGolmokPlayerController::AddMappingContext()`와 별개로** 호출하고, PC는 `SetDebugKeysSuspended`로 디버그 컨텍스트만 제거·복귀 | 두 소유자가 같은 `UEnhancedInputLocalPlayerSubsystem`의 컨텍스트 스택을 번갈아 바꿀 때 재빙의(`OnPossess` → `AddMappingContext()` 재호출)가 포토 컨텍스트를 덮거나 우선순위를 재정렬하지 않는지 [2차]; §10 #6은 오버로드만 다룸 | 재빙의는 포토 중 거부(이미 `StartPlayback` 거부); 그래도 흔들리면 PC의 `AddMappingContext()`가 `Photo->IsActive()`일 때 포토 컨텍스트를 재추가 | 런북 §3 정지 중 F키 무반응·P 종료 후 F1 복귀 | ✅ 종료 뒤 F1·프리셋 키 복귀 |
| 56 | (적대 검증 STATE-2, 확인 불가) 정지 중 `APlayerController::PlayerTick` → `TickPlayerInput(dt, dt == 0)` 경로 — 엔진 소스를 기억으로 옮긴 것이고 출처 없음 [미확인 가설] | 이 경로가 사실이라도 캐릭터 `IMC_Default` 액션이 정지 중 발화할 수 있는지는 #5와 같은 문제. 포토 IMC(우선순위 3, 모든 액션 `bConsumeInput = true`)가 같은 키를 덮으므로 코드 변경 없음 | #5 대안: `AGolmokCharacter`에 `RemoveMappingContextForPhoto()` public 추가 | §3 포토 중 WASD·마우스·Space·Shift → P로 나간 뒤 캐릭터 위치·회전 불변(#5와 같은 확인) | ✅ #5와 같은 확인 |
| 57 | (V-09 PC) 정지 월드 렌더: `FSceneViewFamily::bWorldIsPaused = !UWorld::IsCameraMoveable()` → `SceneVisibility.cpp`에서 `bStatePrevViewInfoIsReadOnly = true` → TSR·Lumen 이력 고정 | GamePause 포토에서 카메라를 움직이면 이전 프레임의 캐릭터 잔상이 화면·PNG에 남음(1 s 뒤에도) | `Enter()`에서 `UWorld::bIsCameraMoveableWhenPaused`(엔진 public 비트, `IsCameraMoveable()`이 읽음) 저장 후 true, `RestoreAll()`에서 복원. 게임은 정지 유지, 뷰 이력만 갱신 | §3·§5 이동·회전 직후 화면·PNG; §10 패키지 같은 장면 | 수정(c026815): GUI 재검증에서 잔상 0(이동 중·정지 직후·회전·H 숨김·2x PNG). **범위(PR #27 리뷰 A1)**: `bWorldIsPaused` 대입은 엔진 `SceneView.cpp`의 `#else`(WITH_EDITOR) 분기에만 있음(5.6·5.7 소스 미러 확인, 5.8.3 미확인) → PIE·`-game`(에디터 바이너리)에서는 잔상·수정 효과가 있고 패키지 빌드에서는 둘 다 없을 가능성이 높음(§10 확인). 67f9d8c: 복원 계약 `FGolmokPhotoRestoreState::bCameraMoveableWhenPaused` **V-09b(5.8.3 소스)**: 대입은 `SceneView.cpp` 3128 한 곳, `#if !WITH_EDITOR`(3110) … `#else`(3112) 뒤 에디터 분기에만 있고 이력 읽기 전용은 이 값에 달림(`SceneVisibility.cpp` 5210) → 패키지는 잔상·수정 효과 둘 다 없다고 예측(§10은 실행 안 함 — 관찰 아님) |
| 58 | (V-09 PC) `GolmokPhotoMath::ClampToPolygonXY` — 다각형 **안**의 점은 그대로 받고, 밖으로 나간 점만 경계 + `InsetCm` 안쪽으로 되돌림 | 경계로 밀면 0~20 cm 띠 안을 앞뒤로 오가는 톱니(1.5 m/s에서 약 16틱마다 20 cm 후퇴) — 20 cm 안쪽 정지가 아님 | 안쪽 점도 경계까지 거리 < `InsetCm`이고 이전 위치보다 가까워지면 거부(이전 위치 유지)하거나 inset 다각형으로 클램프. g++ 드라이버·pytest 기대값도 함께 | §7 footprint(틱 샘플) | V-09: 남쪽 경계 y 980.0 ↔ 999.8 반복, 동쪽도 같음. **수정(a6c48a3, 클라우드 — PC 재검증 대기)**: 침식 영역 {안 ∧ 경계 거리 ≥ inset}의 정확한 최근접점(offset 변·꼭짓점 호·그 교점 후보; 적대 검증 뒤 교대 투영에서 교체 — 짧은/중복 변 모서리 진동 제거), 구–변 접합은 16라운드 교대 + 이분 탐색 폴백(e03753e·7f66810); 현재 위치가 띠 안이면 그 거리 유지(튐 없음). pytest: 60틱+ 연속 이동 단조 수렴·진동 0·접선 미끄러짐·오목·좁은·예각 **V-09b ✅**: 남쪽 y 600 → 980.00 단조·뒤 352틱 변동 0, 동쪽 1979.99, 볼록 모서리 (1979.99, 980.00), 대각선 106 cm/s·옆 끌림 0, 띠 안 진입 튐 0·여유 20 cm 복귀, 임시 홈의 반사 꼭짓점 호 추종(120 fps 한 틱 ≤ 1.004배, 10 fps+Shift는 1.54배 — §11-7 한계 실측), 앵커가 띠 안이면 앵커 거리로 여백을 낮추고 래칫 없음. 구∩경계 접합은 멈추지 않고 구면을 따라 내려감(§13 V-09b — 설계대로, 폴리시 후보) |
| 59 | (V-09 PC) HighResShot 저장이 게임 스레드의 한 프레임 안에서 동기로 끝남 | 촬영마다 화면이 멈춤: 1x 0.32 s, 2x 1.2 s, 3x 3~6 s(첫 장 6.29 s). 3x GPU 전체 사용 피크 7.73/8.15 GB | 3x 상한 해제는 비동기 저장(`FImageWriteQueue`) 경로나 진행 표시가 있어야. 지금은 `MaxMultiplier=2` | §6 | 수정(4834941): `MaxMultiplier=2`(런북 §6 규칙). 2x 1.2 s 정지는 남음 — 사용자 판단 |
| 60 | (V-09 PC) `AGolmokPhotoCameraPawn::MoveConstrained` — 스윕이 막히면 그 틱 이동을 멈춤(면 따라 미끄러짐 없음) | 벽에 대고 대각선으로 밀면 카메라가 붙어 움직이지 않음(W+D 1 s = 0.3 cm); 평행 입력만 이동 | 막힌 이동을 충돌면에 투영해 나머지 성분으로 한 번 더 스윕(`SlideAlongSurface`식) | §7 벽 | V-09: W+D 1 s = 0.3 cm. **수정(6c36fd3, 클라우드 — PC 재검증 대기)**: `(Target − Start)·(1 − Hit.Time)`을 `FVector::VectorPlaneProject(…, Hit.Normal)`로 투영, 현재 위치에서 `Constrain` 재클램프 후 두 번째 스윕(최대 2회), `bStartPenetrating` 후퇴 유지(§12 #62) **V-09b ✅**: W+D 1 s = 106.07 cm, W+A 105.18 cm, 면 거리 15.04~15.38 cm, 135° 안쪽 꺾임에서 두 번째 벽을 따라 46 cm/s(전환 틱만 0.24 cm로 잘림) |
| 61 | (V-09 PC) `PauseMode=TimeDilation`(0.0001): 눈 적응이 팽창된 월드 시간으로 돈다 | TimeDilation에서는 잔상은 없지만 EV를 바꿔도 화면 밝기가 전혀 안 바뀜(+1·0 모두 153.2); 사전 정지 종료 로그가 `unpaused`(실제로는 정지 유지 — 코드상 TD면 항상 `unpaused`) | GamePause + #57이 기본. TimeDilation을 쓰려면 수동 노출 또는 폰 CustomTimeDilation 보정 필요 | §3 대안 경로 | 관찰(기본값 GamePause 유지). 원인: 눈 적응(`AutoExposureSpeedUp/Down`)이 팽창된 `DeltaWorldTime`(0.0001배)으로 적분돼 20 EV/s도 사실상 0 — 코드 변경 없음 |
| 62 | (V-09 후속, 클라우드 6c36fd3) `FVector::VectorPlaneProject(V, PlaneNormal)`(static) · `SetActorLocation(…, bSweep true, &Hit)`의 `FHitResult::Time`(Start→Target 중 이동한 비율, 0..1) · `Hit.Normal`(`FVector_NetQuantizeNormal` → `FVector`) | 이름·정적 여부; 스윕 이동의 `Time`이 풀백(`MIN_TICK_TIME`식 소량 후퇴) 전 값인지 — 슬라이드 길이가 약간 길거나 짧아도 두 번째 스윕·재클램프가 막으므로 동작은 안전 | 컴파일 오류면 `V - (V | N) * N`(= `V - FVector::DotProduct(V, N) * N`); 슬라이드가 벽을 파고들면(`bStartPenetrating` 반복) `Hit.ImpactNormal`로 | §7 벽 대각선(1 s 이동 거리) | ✅ V-09b: 빌드 통과. 벽 W+D 1 s = 106.07 cm, 슬라이드 중 면 거리 15.04~15.09 cm로 일정(파고듦·반복 후퇴 없음) |
| 63 | (PR #27 리뷰 A2, 67f9d8c) `APlayerCameraManager::SetGameCameraCutThisFrame()`(public) — 복원 프레임에 카메라 컷 → 눈 적응·TSR·모션 블러 이력 리셋 | 이름·접근성; 뷰 타깃 변경과 같은 프레임에서 효과 | 없으면 `PC->PlayerCameraManager->bGameCameraCutThisFrame = true`; 그래도 밝기가 이어지면 종료 프레임에 눈 적응 리셋 관찰만 기록 | §4 종료 밝기(EV ±3) | 미확인 추가 확인(PR #29 리뷰 B-2): (a) 촬영 중 P로 지연 종료했을 때 종료 밝기·첫 프레임 (b) 사전 정지 상태에서 들어갔다 나왔을 때 정지 유지 중 노이즈·깜빡임(매 프레임 컷 여부) **V-09b**: 컴파일·호출 OK. (a) 촬영 중 P(지연 종료) ✅ — 종료 뒤 둘째 프레임부터 진입 전 밝기(126.0 / 126.6). **P 종료 ✗** — 컷이 옛 포토 POV 프레임에서 소비돼 눈 적응이 1~4 s 이어짐 → #64. (b) 사전 정지: 노이즈·깜빡임 없음, 정지가 풀릴 때까지 포토 구도·노출 고정(#3) 뒤 같은 페이드 |
| 64 | (V-09b PC) `RestoreAll`의 `SetGameCameraCutThisFrame()`이 플레이어 뷰가 처음 그려지는 프레임에 닿지 않음(P 종료 경로) | P 입력은 정지로 시작한 월드 틱의 PC 틱에서 처리된다. `UWorld::Tick`은 `bIsPaused`를 틱 시작에 읽고(`LevelTick.cpp` 1565) 정지 중에는 풀틱 PC만 `UpdateCameraManager`(1845) — `RestoreAll`이 풀틱 플래그를 되돌리므로 그 틱은 카메라 갱신을 건너뛰고 옛 포토 POV·PP(EV 바이어스·20 EV/s)로 그려지며 컷을 소비한다(`GameViewportClient.cpp` 1922~1924에서 지움). 다음 프레임(플레이어 POV)엔 컷이 없어 눈 적응이 포토 노출에서 이어짐. 지연 종료(`OnEndFrame` 복원 → 다음 틱은 정지 없이 시작)는 정상. `UpdateCameraPhotographyOnly`(정지 틱의 else 분기, `PlayerCameraManager.cpp` 1015)는 컷을 `=`로 덮지만 포토그래피 제공자가 없어 여기선 비활성 | ① (1순위) `RestoreAll`에서 뷰 타깃 복원·풀틱 복원 뒤 `PC->PlayerCameraManager->UpdateCamera(0.f)`로 같은 틱에 카메라 캐시를 플레이어 POV·PP로 갱신 → 종료 프레임부터 플레이어 뷰 + 컷(사전 정지 종료의 옛 구도 고정 #3도 풀릴 수 있음 — 확인 필요). ② 컷을 다음 프레임에 한 번 더(종료 프레임 1장은 옛 포토 화면으로 남음). ③ P 종료도 `OnEndFrame`에서 복원(지연 종료와 같은 경로) | §4 종료 밝기 EV ±3(종료 프레임 포함), #63 (b); 틱 추적(뷰 타깃·카메라 매니저 위치·`bGameCameraCutThisFrame`) | V-09b: P 종료 틱 post-tick에서 뷰 타깃 = 캐릭터, 카메라 매니저 위치 = 포토 카메라 자리, 컷 이미 지워짐; 종료 프레임 220.3(포토 구도·노출) → 0.23 s 182.9 → 3.55 s 126.6(기준 126.6). `r.Test.CameraCut 1`이면 즉시 126.0, post-tick에서 컷을 한 번 더 걸면 첫 플레이어 프레임부터 126.0(②의 실측). 클라우드 후속 → **후속 수정 2(2026-09-28, 클라우드)**: ① 채택 — `RestoreAll`에서 `SetViewTargetWithBlend` → `SetControlRotation` → `PlayerCameraManager->UpdateCamera(0.f)` → `SetGameCameraCutThisFrame()` 순서(풀틱·정지 복원보다 앞; 정지 틱이든 아니든 캐시가 바로 플레이어 POV). 정지 없이 시작한 틱(TimeDilation, 지연 종료 뒤 다음 틱)은 월드 틱이 같은 틱에 dt로 한 번 더 갱신 — 뷰 타깃이 이미 캐릭터라 결과 같음. UE 자동화 `Golmok.Photo.EnterExit`가 GamePause 종료와 사전 정지 종료(새 단계 `PrePausedExit`: 정지 유지 중 0.5 s 포토 카메라 이동 뒤 Exit) 둘 다에서 `Exit()` 직후 카메라 매니저 위치 = 진입 전 플레이어 카메라(2 cm)·`bGameCameraCutThisFrame` 켜짐을 검사하고, 그 전제(Exit 직전 카메라 매니저가 포토 카메라 자리, > 20 cm)도 단언(테스트 이름 추가 없음). **재검증**: §4 "종료 밝기" 1~4(EV ±3), 틱 추적으로 종료 틱 post-tick 카메라 매니저 위치 = 플레이어 카메라 확인. 컴파일·동작 문제면 #65·#66. **V-09c(2026-09-29) 확인**: ① 채택분 그대로 통과 — P 종료 틱 post-tick에서 카메라 매니저 위치 = 플레이어 카메라 (45.0, 514.0, 176.7)(직전 틱 포토 카메라 (152.5, 479.3, 176.7)), 종료 프레임 125.97 / 126.39(EV +3 / −3, 기준 126.58), 지연 종료·TimeDilation·사전 정지 종료도 종료 프레임부터 기준 ±1 이내·플레이어 구도(§13 V-09c) |
| 65 | (V-09b 후속 수정 2, #64) `APlayerCameraManager::UpdateCamera(float DeltaTime)` — public virtual(`ENGINE_API`), 로컬 PC면 `DoUpdateCamera` → `FillCameraCache`(뷰 타깃 `CalcCamera` → 카메라 컴포넌트 POV·PP 블렌드) | 이름·접근성; 월드 틱 밖(`OnEndFrame` 지연 종료)·정지 틱 안에서 호출해도 안전한지; dt 0에서 카메라 셰이크·모디파이어가 한 번 더 도는 부작용 | 없거나 보호면 `PC->UpdateCameraManager(0.f)`(public virtual, 같은 동작); 둘 다 안 되면 #64 대안 ②(다음 프레임에 `SetGameCameraCutThisFrame()` 한 번 더 — `OnEndFrame` 한 번 등록) | §4 종료 밝기 1~4, `Golmok.Photo.EnterExit` "camera manager POV back at the player camera right after Exit" | 확인(V-09c): C++ 무수정 컴파일(public virtual). 정지로 시작한 P 종료 틱(GamePause·사전 정지)·`OnEndFrame`(지연 종료)·TimeDilation 모두 그 프레임부터 플레이어 POV·PP — `EnterExit` `exit camera: before 74.4 cm, after 0.00 cm, cut 1` 2회, GUI 종료 프레임 휘도 기준 ±0.7. dt 0 호출의 셰이크·모디파이어 부작용은 관찰되지 않음(이 장면에 카메라 셰이크 없음 — 셰이크가 있는 장면은 미확인) |
| 66 | (V-09b 후속 수정 2, 테스트) `APlayerCameraManager::bGameCameraCutThisFrame`(`uint32 : 1`, public UPROPERTY로 가정 — `LocalPlayer.cpp` `CalcSceneView`가 직접 읽음) — `GolmokPhotoTest.cpp`가 `Exit()` 직후 읽음 | 접근성(protected면 C2248) | 게터가 있으면 그것으로(`GetGameCameraCutThisFrame()` 등), 없으면 해당 네 곳(`TestTrue` 2줄과 `AddInfo` "exit camera" 2줄의 `cut` 인자 — AddInfo는 cut을 −1로)을 고치고 §4 틱 추적으로만 확인(§13에 기록) | 빌드, `Golmok.Photo.EnterExit` | 확인(V-09c): public 멤버 그대로 컴파일(대안 불필요), `EnterExit`의 `cut 1` 2회. 에디터 Python에서도 `game_camera_cut_this_frame`로 읽힘(post-tick에서는 그리기가 이미 소비해 false — V-09b와 같은 관찰 위치) |
| 67 | (PR #40 리뷰 R1) 사전 정지 종료 (b)(GamePause에서 `bWasPausedBefore`, 또는 진입 전부터 정지였던 TimeDilation): `RestoreAll`이 `ApplyPause(false)` 뒤에도 `UGameplayStatics::IsGamePaused(World)`면 `UWorld::bIsCameraMoveableWhenPaused`를 저장값(false)으로 바로 되돌리지 않고 true로 둔 채 `FCoreDelegates::OnEndFrame`(`OnEndFrameCameraMoveableRestore`)이 정지 해제를 본 첫 프레임에 복원(`CancelCameraMoveableRestore`로 해제; `Deinitialize`·`TeardownForDeadWorld`·재진입 `Enter`는 대기 중 복원을 버리고 `Enter`는 앞 세션의 저장값을 유지). 정지가 유지되지 않는 경로(즉시·지연 종료, 일반 TimeDilation)는 전처럼 즉시 복원 | 정지 유지 중 플래그를 false로 되돌리면 뷰 이력이 읽기 전용(`SceneVisibility` `bStatePrevViewInfoIsReadOnly = bWorldIsPaused`, #57 메커니즘)이라 포토 마지막 프레임의 TSR·Lumen 이력이 컷 1프레임 뒤 재투영될 수 있다 — **추론, PIE/-game에서 잔상 여부 미확인**(패키지 빌드는 #57처럼 해당 없음 예측). 정지 중 플래그가 true인 동안의 부작용(정지 월드가 비정지처럼 이력을 갱신 — 포토 중과 같은 상태)도 미확인. `OnEndFrame` 브로드캐스트 중 핸들 제거는 기존 캡처 창과 같은 패턴이고, 사전 정지 상태의 지연 종료에서는 브로드캐스트 중 바인딩 추가(다음 프레임부터 호출)라는 새 패턴 | 잔상은 없는데 부작용이 보이면 즉시 복원으로 되돌린다(`RestoreAll`의 분기 제거). 잔상이 여전하면 #64 대안 ②(다음 프레임 컷)·컷을 정지 해제까지 반복 검토 | §4 종료 밝기 4(사전 정지 (b), 둘째~10번째 프레임·로그 두 줄), `Golmok.Photo.EnterExit` `PrePausedExit`·`PrePausedRestore` | 확인(V-09c): 헤드리스 `EnterExit`와 GUI §4-4(EV ±3) 모두 로그 두 줄(`… kept true until the unpause` → `pause` 해제 첫 프레임 `… restored after the unpause (false)`). 정지 유지 중 둘째~10번째 프레임에 포토 구도 잔상·고스트 없음(종료 프레임과 평균 차 ≤ 1.74, 16×16 블록 최대 ≤ 11, 포토 화면과 ≥ 89.7), 0.24 s 간격 10장 차 0.30~0.36(노이즈·깜빡임 없음), 해제 뒤 밝기 변화 ≤ 0.05 — 플래그 true 유지 중 부작용 관찰 없음. 분기는 그대로 둔다 |
| 68 | (V-09c PC) `AGolmokPhotoCameraPawn::MoveConstrained` bKeepHeight 슬라이드 — 충돌면에 투영한 슬라이드의 Z만 0으로 만들던 것(`Slide.Z = 0.0`) | 수직 벽은 정확하지만, 법선에 수직 성분이 있는 충돌(12° 경사로 윗면 법선 ≈ (−0.21, 0, 0.98), 구가 계단 앞 모서리에 닿은 법선 ≈ (−0.59, 0, 0.81))에서는 평탄화한 슬라이드가 여전히 면 안쪽을 향해 두 번째 스윕이 곧바로 막힌다 → 대각선으로 밀어도 수평으로 미끄러지지 않고 정지(z는 불변). D-013 결정 3 "수평면 안에서 더 갈 수 없으면 정지"(여기선 수평면 안에서 면을 따라 갈 수 있다)와 §7 ⑦ "비스듬히 밀면 수평으로만 미끄러진다"에 어긋남 | **PC fix(V-09c)**: 평탄화한 슬라이드에서 충돌면의 수평 법선 쪽으로 들어가는 성분만 뺀다(한쪽 투영 — 면에서 멀어지는 성분은 그대로, Opus 적대 리뷰 제안). 수평 법선 길이 ≤ 0.02(`PhotoSlopeSlideMinHorizontal`, 경사 약 1.1° 이하 — 거친 바닥 스캔 메시)면 평탄화만(옆으로 새지 않게). 수직 벽은 결과 같음(수평 법선 = 법선이라 들어가는 성분이 이미 0). UE 자동화 `Golmok.Photo.Clamp`에 (c3) 추가(같은 상자를 피치 30°, 이름 추가 없음). 후속(R56-2/6, #<n>): 이 규칙은 이제 순수 함수 `GolmokPhotoMath::KeepHeightSlide`에 있고(폰은 `if (bKeepHeight)` 안에서 호출만, 동작 동일) pytest `test_ue_photo_math.py`가 g++·numpy로 교차검증하며, (c3)에 피치 −30°·1° 윗면 변형을 더했다 | §7 ⑦(L_Dev 12° 경사로·계단), `Golmok.Photo.Clamp` (c3) `keep height slope slide:` | 수정(V-09c): 수정 전 GUI — 경사로 W+D 2 s에 0.02 cm·W+A 0 cm, 계단 앞 모서리 W+D 2 s에 0.07 cm에서 정지(240틱, z 변동 0). 수정 뒤 (c3) lateral 40.0·|dz| 0.0000·face distance 15.9(수정을 끈 빌드로는 lateral 2.3 → 실패, 판별력 확인), `Golmok.` 28/28. GUI 재확인은 §13 V-09c |
| 69+ | (PC 세션 추가) | | | | |

## 13. 결과 기록
V-09 PC 세션(Claude Desktop 워크트리 `upbeat-rosalind-95c87c`, 사용자 PC, 모델 Claude Fable 5.1로 시작 — 세션 중 Opus 5.5로 바뀜, 커밋 서명 기준), 날짜 2026-09-28. UE 5.8.3, VS 18 Community(MSVC 14.51), GPU RTX 5060 8 GB(드라이버 617.14, 2560×1440 모니터), 뷰포트 **2554×1354**(PIE 새 창 2560×1392 — 작업 표시줄 때문에 1440 불가), 브랜치 `pc/v09-verify-wp12`(main a4764c8 = PR #24 병합 뒤).
**검증 방식**: 에디터 Python PIE 드라이버(V-07 드라이버 + 누르고 있기·마우스 이동·휠, Alt+P로 PIE 새 창 2560×1440 요청) + `TerminateProcess` 종료. **키·마우스·휠 입력은 전부 Win32 `SendInput`**(사람 손 없음, 창 전면·클릭 포커스), 값 확인은 폰·카메라·PP 프로브와 `shot showui` 화면, 밝기는 PIL 휘도 평균, 경계는 틱마다 위치 샘플. **게임패드 없음**(XInput 4슬롯 모두 미연결) → §3 패드 표 미실행. 헤드리스: `test.ps1 -Filter Golmok.Photo`, `test.ps1 -Filter Golmok. -SetupDevLevel`. VRAM은 `nvidia-smi` 50 ms 샘플(GPU 전체 사용량 — 에디터·데스크톱 포함). 드라이버·시나리오·원본 PNG는 세션 스크래치에만.

| 항목 | 결과 | 메모·실측 |
|---|---|---|
| 빌드 | ✅ | 1차 빌드 C++ 무수정 성공(프로젝트 경고 0, 엔진 헤더 C4996만). PR #24 pull 뒤 증분 빌드 성공. PC fix 뒤 재빌드 성공 |
| 헤드리스 자동화 26개(Photo 3 + 기존 23) | ✅ 26/26 `Success` | PC fix 전·후 두 번. EnterExit `photo mode on (fov 80.0, no zone, paused)`, Clamp `after +1000 x: X=-320.000`·`floor z 2.2`·`face distance 16.5, along 33.5`·`along 200.0`, MetaJson `capture window closed after 3.03 s`. PhotoIntegration 6조합 EXECUTED, RenderEvidence 설계상 NOT EXECUTED Warning. skip Info 없음, `photo:` `[Error]` 0, 남은 JSON 없음. 요약 줄 `Succeeded: 19`는 Warning 테스트를 따로 셈 |
| §2 진입/복원(로그 두 줄·오버레이·PAUSED 없음·사전 정지·전환 드리프트) | ✅ | 로그 두 줄·콘솔 왕복·`on/off/true/false` 문구가 런북과 글자 단위로 같음. 뷰포트 클래스 Warning 없음. 오버레이 5줄·색 정상, 분모 `3.3 / 3.3 m`(진입 거리 327.8 cm). 프리셋 칸은 PIE 시작 때 `-`(L_ZoneTest에 초기 프리셋 없음 → 시나리오가 `golmok.tod overcast_morning` 적용). "PAUSED" 없음(단 PIE에서는 엔진 `pause`만으로도 안 보임 — §12 #12). 사전 정지: P 진입 `already paused` → 이동 → P `left paused` → 여전히 정지. `tod shift 0.000 s`(월드 시계 정지). 전환 16% → 포토 10 s → 종료 직후 25%(포토 밖 0.6 s분만) → 2 s 뒤 68%. **관찰**: 사전 정지에서 나가면 정지가 풀릴 때까지 화면이 마지막 포토 구도에 머묾(§12 #3) |
| §3 정지 중 입력·틱·카메라(부드러움·휠·캐릭터 불변·F키 무반응·복귀) | ✅ | W 1 s = 1.46 m, Shift ×3 = 4.4 m/s, E/Q 1.5 m/s, 화면이 폰을 따라감. 마우스 1000 px = 35°(0.5°/unit × 엔진 Mouse 감도 0.07), 피치 ±89°에서 멈춤. 휠 1노치 = 5°(위 = 좁게). 난타(WASD·Space·Shift·마우스) 뒤 캐릭터 (0, 500, 94.2)·회전 0 불변. 포토 중 1·F5·F9·F10·F1·F2 무반응, `golmok.hud 1`로 HUD+오버레이 공존, 종료 뒤 HUD는 진입 전 상태, F1·3 복귀. `PauseMode` 최종 `GamePause`(비교용 TimeDilation 1회 — §12 #61). 패드 미실행(없음) |
| §4 조절·화질(EV 즉시 반영·EV 0 밝기·DOF off·그림자·콘솔 set) | ✅(수정 2건) | FOV 5° 20↔110, EV 1/3 ±3 → 9회 뒤 정확히 base 0.3, 초점 ×1.25 0.300↔50.000, f/1.4↔16, 롤 ±15(카메라만), H 캐릭터·그림자 제거, O, R(fov 65·자세 복원, 배율 3x 유지). 콘솔 set 13줄 글자 단위 일치, `ev -1.5` → `-1.33`. EV 0 밝기 = 진입 전(안정 장면 116.9/116.8). **수정**: ① EV가 2~4 s에 걸쳐 수렴 → 눈 적응 속도 20 EV/s로 0.3 s(§12 #10). ② 이동·회전 뒤 캐릭터 잔상이 화면·PNG에 고정 → `bIsCameraMoveableWhenPaused`로 제거(§12 #8·#57, 수정 뒤 이동 중·정지 직후·회전 모두 깨끗). DOF는 f/1.4에서 먼 문틀이 흐려짐(합성 장면이라 효과는 약하게 보임) |
| §5 촬영(3줄 로그·PNG에 HUD/오버레이/PAUSED 없음·메타 15키·`_2`·deferred exit) | ✅ | Space·Enter·콘솔 모두 3줄 로그. `present after` 2x 1.43~2.16 s(첫 장이 김), 1x 0.49 s — 수백 ms보다 김(§12 #14·#59). PNG 5108×2708, HUD·오버레이·PAUSED 없음, H 숨김 반영, 이동 직후 번짐·잔상 없음. 초록 `saved <stamp>.png (2x)`. 메타 15키·값 대조 일치(롤 5 → `rotation[2] 5.000`, `exposure_ev 0.33`, `dof.enabled true`). `_2`는 1x에서 4회 생성(2x는 한 장이 1.4 s 이상이라 같은 초 불가). 캡처 창 중 거부 3줄, 키 P·콘솔 deferred exit 문구와 창 종료 뒤 `photo mode off`. `PreCaptureFrames=0`에서도 PNG 4장 모두 HUD·오버레이 없음 → 기본 2 유지. 메타 실패 경로(폴더 대신 파일): `Error: photo: ERROR cannot write meta …`, 요청 없음, 즉시 Active |
| §6 배율 표 | ✅ → `MaxMultiplier=2` | 아래 표. 3x는 강등·크래시 없이 찍히지만 촬영마다 게임이 3~6 s 멈춤 → 런북 규칙대로 2로 커밋(4834941). 1x·2x 같은 곳 크롭: 합성 장면이 평면이라 계단·노이즈 차이 없음, `PreCaptureFrames` 유지 |
| §7 제약(벽·구·바닥·footprint·no zone·포털 타이머) | 🔴 footprint 실패 | 벽: 파사드 면 −980에서 y −964.6(15.4 cm) 정지, 관통 0, 평행 이동 계속(#40 반복 후퇴 없음). **대각선(W+D)으로 밀면 붙어서 안 움직임**(1 s 0.3 cm — §12 #60). glass_1 앞 −979.6(통과 없음; blocker·footprint 여백이 같은 자리). 구: 첫 이동 튐 없음(2.4 cm), 3.29 m 표면 유지, 위로도 동일. 바닥 15.1 cm. **footprint: 20 cm 안쪽 정지가 아니라 0~20 cm 띠 안에서 톱니 왕복**(남쪽 y 980.0 ↔ 999.8, 1.5 m/s에서 약 16틱마다 20 cm 후퇴, 동쪽도 같음 — §12 #58). no zone: `no zone` 노랑, 메타 `zone_id`·`zone_version` null, 구만 작동. 포털 ① 트리거 안 30 s → `active` 불변, 언로드 없음. ② 나와서 0.5 s 뒤 P, 10 s → 종료 2.44 s 뒤 언로드 = **타이머 정지**(§12 #11) |
| §8 실내 | ✅ | `photo mode on (fov 80.0, zone z_synthetic_001_interior v1, paused)`, 오버레이 1행 실내 zone, 실내 조명 유지(`interior=True`). 북벽 −1564.6·천장 284.9·서벽 135.4 cm(각 면 15 cm 앞), 방 밖 노출 없음(방 한가운데 마커 큐브에도 정상으로 막힘). 메타 `zone_id z_synthetic_001_interior`·`zone_version 1`. 종료 뒤 `door_1 active`·실내 loaded, 문으로 나가면 오버레이 off·언로드 |
| §9 경로 재생 배제 | ✅ | `P: cannot enter while a path is playing …`, `golmok.photo: ERROR cannot enter while a path is playing …`, `P: cannot enter while recording 'tmp'`, 포토 중 `golmok.path play/record: ERROR photo mode is on …` 모두 글자 단위 일치. `quick` 경로는 이 세션에서 녹화(5.0 s), `tmp.json` 삭제 |
| §10 패키징(선택) | ✅(L_Dev로) | `package.ps1` 성공. `UnrealPak -List`에 `Golmok/Config/Golmok/photo.json`(596 B) 포함. `L_ZoneTest`는 쿡 대상이 아니라(맵 목록 없음 → 기본 맵만) `Failed to load package` — 기본 맵 `L_Dev`에서 확인: P → `photo: config loaded (5 params) from ../../../Golmok/Config/Golmok/photo.json`, `no zone`, Space → `<GameDir>\Saved\Screenshots\Golmok\photo\<stamp>.png`(3840×2160 = 1920×1080 창 ×2) + `.json`(preset·zone·lon/lat null), `present after 0.98 s`. 오버레이 힌트 줄 화면 확인은 못 함(외부 SendInput 스크립트) |
| §11 PIE 종료 | ✅ | 포토 켠 채 종료 → `photo: teardown (world ending)` 1줄, 다른 경고·에러 없음. 캡처 창 중 종료(촬영과 같은 틱) → `teardown` 1줄, `capture window closed` 없음, JSON·PNG 모두 안 생김(메타 기록 전 — 고아 없음). 종료 뒤 에디터 월드에 포토 폰 없음, 더티 맵 없음. 재 PIE: `config loaded` 1회, 정지 잔재 없음. 포토 중 zone unload/load → 폰 유지, 폰 강제 삭제 → `photo mode off (restored, …)` |
| 고친 API 번호(§12)·커밋 | 3건 | c026815: #57(`UWorld::bIsCameraMoveableWhenPaused` 저장·설정·복원 — 잔상) + #10(눈 적응 속도 20 EV/s). 4834941: `MaxMultiplier=2`(#59, §6 규칙). 컴파일 오류 수정은 0건 |
| 설계와 다른 동작 발견 | 7건 | ① 정지 월드 이력 고정 잔상(#57, 수정). ② EV 눈 적응 완화(#10, 수정). ③ footprint 톱니(#58, 미수정·클라우드). ④ 벽 대각 밀착 정지(#60, 미수정). ⑤ 촬영이 게임 스레드를 멈춤 2x 1.2 s·3x 3~6 s(#59). ⑥ 사전 정지 종료 뒤 화면이 정지 해제까지 옛 구도(#3). ⑦ TimeDilation: 잔상은 없지만 EV 무반응·로그 `unpaused`(#61). 그 밖: 마우스 시선이 1000 px에 35°로 느림(조작감 판단), 뷰포트 2554×1354라 배율 해상도가 1440p 기대값보다 약간 작음 |
| STATUS | `🟡 → 🔴` | §7 footprint 경계 톱니(#58)가 "20 cm 안쪽 정지"를 못 지킴 + 벽 대각 밀착 정지(#60) → 클라우드 수정 뒤 §7만 재검증. PC fix c026815는 Unreal 코드라 병합 전 Opus 5.5 ultracode 적대 검증 필요(모델 정책 2026-09-27) |

§6 배율 VRAM 표(뷰포트 2554×1354, `nvidia-smi` GPU 전체 사용량; "증가"는 촬영 직전 1.5 s 최소값 대비 피크):

| 배율 | 해상도(PNG 실측) | VRAM 피크 GB(증가) | 소요 s(`present after`) | 게임 정지(저장 프레임) | PNG MB | 결과 |
|---|---|---|---|---|---|---|
| 1 | 2554×1354 | 6.36 (+0.01) | 0.48~0.51 | 0.32 s | 3.3~3.4 | ✅ |
| 2 (기본) | 5108×2708 | 7.56 (+1.21) | 1.43~2.16 | 1.2 s | 11.4~12.8 | ✅ |
| 3 (옛 상한) | 7662×4062 | 7.73 (+0.42~0.54, 2x 뒤 풀 7.19~7.27 위) | 6.29 / 2.97 / 3.07 | 렌더 3.8 s + 저장 2.4 s(첫 장) | 25.4 | ⚠ 강등·크래시 없음, 스톨 → `MaxMultiplier=2` |

`stat RHI` 화면 캡처는 세션 스크래치에 있다(수치는 nvidia-smi를 기준으로 삼았다). 3x는 8 GB 중 95%까지 차므로 패키지 게임(에디터 메모리 없음)에서는 여유가 더 있을 수 있다 — 3을 다시 열지는 사용자 결정.

스크린샷 4장(JPG 축소, `docs/runbooks/` 옆; PNG 원본·JSON은 커밋하지 않는다):
- ① 포토 모드 화면(오버레이 5줄 보임, `L_ZoneTest` 001 안): `docs/runbooks/pc-verify-wp12-photo.jpg` — 수정 빌드, `3.3 / 3.3 m  2x`
- ② 찍힌 2x PNG 축소본(오버레이·HUD 없음): `docs/runbooks/pc-verify-wp12-png.jpg` — 수정 빌드, 카메라를 옆으로 옮기고 돌린 직후 촬영(잔상 없음)
- ③ 벽 15 cm 앞 또는 구 표면(`3.3 / 3.3 m` — 유효 반경, §7)에서 멈춘 장면: `docs/runbooks/pc-verify-wp12-clamp.jpg` — 구 표면(3.29 m) → **V-09b에서 교체**: footprint 남동 볼록 모서리 정지(카메라 (1979.99, 980.00), 정지 뒤 캐릭터·파사드 쪽으로 돌아봄, 오버레이 `1.9 / 3.3 m`, 설명 줄 포함)
- ④ 실내 촬영(오버레이 `z_synthetic_001_interior v1`): `docs/runbooks/pc-verify-wp12-interior.jpg`

무인 검증: 에디터 Python PIE 드라이버 + `unreal.SystemLibrary.quit_editor()`; 값·배율·촬영은 `golmok.photo.set`·`golmok.photo.shoot` 콘솔로, 키 발화(P·WASD·휠·패드)만 사람이. 백그라운드 에디터 창은 뷰포트를 렌더하지 않는다(V-03) — 촬영 항목은 창을 전면에 둔 상태에서만.

기록 뒤:
1. 이 표를 채우고 커밋(`WP-12: PC 검증 결과`). §3·§5·§6에서 바꾼 `PauseMode`·`PreCaptureFrames`·`MaxMultiplier`는 확정값만 남기고(`git diff unreal/Golmok/Config/DefaultGame.ini`가 의도한 줄만), 바꾼 이유를 §13 표에 적는다.
2. `docs/plan/STATUS.md`: WP-12 행을 🟡 → 🟢(또는 🔴 + 막힌 항목), V-09 행 갱신, 세션 로그 표에 한 줄(날짜·PC 세션·모델·"V-09 WP-12 검증"·결과). 고친 API·설계 변경은 인계 메모에 번호(§12)와 커밋 해시로.
3. `docs/plan/WP-12-photo-mode.md` "결과"에 PC 검증 한 줄(통과/수정 건수, 확정한 `PauseMode`·`MaxMultiplier`·`PreCaptureFrames`), `docs/ROADMAP.md` 게임 기능(D-013) 진행 표시.

### V-09b 재검증 — WP-12 후속(PR #29) §7·§4 종료 밝기 (2026-09-28)
PC 세션(Claude Desktop 워크트리 `clever-goldstine-ec6dec`, 모델 Claude Fable 5.1), 브랜치 `pc/v09b-verify-wp12-s7`(main 4a31718 = PR #29 d37720e 뒤 #28·#33·#32·#35 병합분), 같은 PC(UE 5.8.3, RTX 5060 8 GB, PIE 새 창 2560×1392). V-09 워크트리의 `L_ZoneTest`·합성 zone·실내·마네킹을 복사해 썼다. ini는 main 그대로(V-09 결정 5건).
**방식**: V-09 드라이버에 틱 샘플을 더했다 — 키를 누르고 있는 동안 Slate post-tick마다 포토 폰 위치(zone 로컬 cm, 소수 3자리)·틱 번호·Slate dt를 기록(PIE ≈ 120 fps). 키·마우스는 전부 Win32 `SendInput`, 밝기는 `shot showui` PNG 가운데 60 %의 휘도 평균(PIL, Rec.709, 0~255), 종료 전후는 틱마다 뷰 타깃·카메라 매니저 위치·`bGameCameraCutThisFrame`을 추적했다. 135° 꺾임은 **PIE 사본에서만** `BM_dummy_outside` 큐브를 4 × 0.2 × 3 m 벽으로 옮겨 만들었다(에디터 월드·맵 무변경). 반사 꼭짓점은 `z_synthetic_001/v1/manifest.json` footprint에 **임시 홈**(x −600..−200, y 600..1000)을 넣어 실행한 뒤 `git checkout`으로 되돌렸다(커밋 없음). 드라이버·시나리오 12개(s7a~s7k)·원본 PNG·틱 JSON은 세션 스크래치에만 있다. 표의 수치는 적대 검증 워크플로(주장 7개마다 회의론자가 원시 JSON·엔진 소스로 다시 계산, 완전성 비평 1)를 거쳐 고친 값이고, 비평이 짚은 공백은 s7j·s7k로 더 쟀다(남은 것은 표 끝 '미측정·한계'). 밝기 표의 시각은 실시간이다 — 촬영(`shot`)이 프레임을 멈추므로 같은 시각의 프레임 수는 적다(예: 0.23 s = 14프레임).
**속도 판정**: 런북 기준을 틱마다 그대로 적용하면 자유 이동에서도 넘는다(최대 1.51배) — 측정 방식 때문이다. 엔진은 틱마다 150 cm/s × `FApp::GetDeltaTime()`만큼 움직이는데, 이 dt는 최대 틱 속도에서 8.333 ms가 하한이다(자유 이동 한 틱 = 1.250 cm, 긴 프레임은 그만큼 길다: 걷기 최대 2.02 cm). 드라이버가 받는 Slate dt는 프레임의 다른 지점에서 재고 한 프레임 늦다(`SlateApplication.cpp` 1640·1676·1827 — `TickTime()` 전 값을 post-tick에 넘김). 증거: 평행 이동의 모든 틱이 1.250~1.252 cm인데 Slate dt 비율은 0.92~1.10, Slate dt가 5.70 ms(엔진 하한보다 작음)인 틱도 있다. 그래서 판정은 창으로 했다: 밖 진입 첫 틱(아래)을 빼면 10틱 창 ≤ 1.031배, 이동 틱 평균 걷기 ≤ 150.4 cm/s(창 끝 위상 오차)·Shift ≤ 447.9/450. 큰 한 틱은 27.7 ms 프레임의 벽 슬라이드 2.641 cm(그 틱 dt로는 0.92배) 하나다. 드라이버가 엔진 dt를 기록하지 않으므로 틱 단위 판정은 이 창 판정으로 대신했다(대리 지표). 저 FPS(`t.MaxFPS 10`)에서는 Slate dt = 엔진 dt ≈ 100 ms라 틱 단위 비교가 그대로 된다(아래 저 FPS 행).

| 항목 | 결과 | 실측 |
|---|---|---|
| pytest | ✅ | `test_ue_photo_math.py`·`test_ue_wp12_fixture.py` 62 passed·21 skipped(g++ 없음) → g++ 호환 MSVC `cl` 심을 PATH 앞에 두면 83/83. 전체 `pytest -q` **751 passed, 6 skipped**(심 포함), `ruff check`·`ruff format --check`·`check_repo.py` 통과 |
| 빌드 | ✅ | C++ 무수정 성공(114 s, 프로젝트 경고 0 — 엔진 헤더 C4996만). §12 #62(`FVector::VectorPlaneProject`·`FHitResult::Time`)·#63(`SetGameCameraCutThisFrame`) 컴파일 문제 없음 → PC fix 0건 |
| `test.ps1 -Filter Golmok.Photo` | ✅ 3/3 | Clamp `slide: from X=-480.000 Y=0.000 Z=94.150 to X=-466.028 Y=40.000 Z=94.150, lateral 40.0, face distance 16.0, along 34.0`(lateral > 20·face ≥ 14·along < 50), EnterExit `photo mode on (fov 80.0, no zone, paused)`, MetaJson `capture window closed after 3.02 s`. `-Filter Golmok. -SetupDevLevel` **26/26 Success**(요약 줄 `Succeeded: 19`는 Warning 테스트 제외) |
| §7 ① 남쪽 경계 | ✅ | W 4 s: y 600.00 → **980.00**(원값 980.003) 단조(증가 300틱·감소 0), 뒤 174틱 + Shift+W 178틱 **변동 0**(기록 해상도 0.001 cm). V-09 톱니(980.0 ↔ 999.8) 없음. 동쪽: x 1600.00 → **1979.99**, 뒤 234틱 변동 0. 볼록 남동 모서리(W, 45°): 남쪽 경계를 따라 미끄러진 뒤 **(1979.99, 980.00)**, 281틱 변동 0(두 번 실행 같음) |
| 띠 안 진입 | ✅ | 카메라 y 990.01(경계 9.99 cm 안)로 진입 → S 1 s 바깥 밀기: y 990.006 유지(튐 0; 진입 거리가 구 반경과 같아 x·z는 구면을 따라 0.73·0.89 cm 미끄러짐) → W 0.5 s 안쪽 916.1 → 다시 S: **980.00**에서 정지, 126틱 변동 0(여유 20 cm로 복귀). 첫 시도(s7a D)는 띠 안에서 D(접선)를 먼저 눌러 구에 걸렸다(y 990 → 944.9로 구면을 따라 끌림, 다시 밀어도 975.7에서 구에 멈춤) — 구가 걸리지 않는 순서로 s7c에서 다시 쟀다 |
| 앵커가 띠 안(PR #29 A1) | ✅ | 캐릭터를 남쪽 경계 10 cm 안(y 990)에 세우고 진입 → W: 카메라가 y **990.00**(유효 여백 = 앵커의 경계 거리 10 cm)에서 정지, 104틱 변동 0. 이어서 Shift+W+D로 구 접합까지 밀고 W+D 1.5 s: y 990.00이 **420틱 동안 한 번도 안 깎임**(`MoveInsetCm` 래칫 없음; x·z는 구면 미끄러짐) |
| 밖 진입 | ✅(튐 90 cm) | 카메라 y 1070(70 cm 밖)으로 진입 → 첫 이동 틱에 y 980.00으로 **90.0 cm 한 번** 튐(설계대로), 뒤로 정상 |
| §7 ② 대각선 | ✅ | 남쪽 경계에서 W+D 1.5 s: y 980.00 고정, x −45.0 → −203.8(**106.0 cm/s** = 150·sin 45°, 179틱 전부 같은 방향). 이어서 W만 1 s: x −204.75 **불변**(앵커 x 0 쪽 끌림 0; 첫 샘플의 −0.99 cm는 D 키를 뗀 한 틱 지연). 볼록 모서리 실행도 y 980에 닿은 뒤 x 1917 → 1980을 0.88 cm/틱으로 경계를 따라 미끄러졌다. 동쪽 경계(s7j): W+D 1.5 s에 x 1979.99 고정·y +158.2(106 cm/s), 이어서 W만: y 불변 |
| 구∩경계 접합 | ⚠ 기대와 다름(설계대로) | Shift+W+D: y 980 고정, x −322.7에서 구 표면에 닿는다(앵커 거리 328.40 — 유효 반경 328.8보다 0.4 cm 안: 설계 §11-7 "접합 앞 수 mm~cm"). 그 뒤 **멈추지 않고 구면∩경계 원을 따라 미끄러진다**: 입력을 누르는 동안 z가 앵커 높이(94) 쪽으로 감쇠하며 내려감 — Shift 1.63 s에 148.6 → 105.1(**−43.5 cm**, 처음 약 53 cm/s), 걷기 1 s에 −3.1 cm. x 역행 약 0.04 cm 5회(무시 가능). 톱니·되튐은 없다. 런북 기대("접합 앞 0.5~1.5 cm에서 멈춤, 변동 0")는 입력에 원 방향 성분이 없을 때(z가 이미 앵커 높이)만 맞고, 카메라가 앵커보다 55 cm 높은 보통 진입에서는 가장 가까운 점 투영이 이렇게 움직인다(`Constrain` 주석 "keeps sliding into the junction instead of freezing"). 순수 구 밀기(④)에서도 같은 원리로 2 s에 31 cm 내려간다. 확인(s7j): 카메라를 Q로 앵커 높이(1.25 cm 아래)까지 내린 뒤 같은 접합으로 밀면 x −322.87·거리 328.7에서 사실상 정지(뒤 179틱 동안 0.16 cm, z가 앵커 높이로 수렴) — 런북 기대와 같다. **설계 판단(Fable)**: 수평 입력이 카메라 높이를 바꾸는 것은 촬영자가 의도하지 않은 움직임이라 눈에 띈다 — 막는 버그는 아니지만 폴리시 후보(구 대신 높이를 보존하는 수평 투영 등; 사용자 결정) |
| §7 ③ 벽 | ✅ | 파사드 정면 Shift+W → y −964.62(면에서 15.38 cm) → W 계속 −964.87(15.13 cm), 슬라이드 중 15.04~15.09 cm, 관통·반복 후퇴 0. **W+D 1 s = +106.07 cm**(기대 ≈ 1.06 m; V-09 0.3 cm), W+A 1 s = −105.18 cm(같은 106 cm/s, 창이 0.99 s로 짧음), 평행 D 150.0 cm/s, y 변화 0.04 cm 이내 |
| 135° 안쪽 꺾임 | ✅ 따라 감 | 임시 벽이 파사드와 (−200, −980)에서 135°(꺾임이 −x 쪽이라 런북의 W+D 대신 거울 대칭인 W+A). yaw −90 W+A(두 번째 벽 법선과 정반대): 벽 1을 106 cm/s로 따라가다 꺾임 x −193.78에서 정지(84틱 변동 0 — 물리적으로 맞다). 마우스 −514 px로 yaw −107.99 뒤 W+A: 벽 1을 1.11 cm/틱으로 가다 꺾임에서 **멈추지 않고** 두 번째 벽을 따라 0.386 cm/틱(**46 cm/s** = 150·0.309)으로 진행, 벽 2 면 거리 15.08 cm 일정. 전환 틱 하나만 스윕 2회 제한으로 0.24 cm에서 잘렸다(PR #29 리뷰 B-1; 다음 틱부터 정상) |
| 벽 → footprint·blocker·실내 모서리 | ✅ | 파사드에 붙어 W+D로 동쪽 끝까지: 벽을 따라 가다 footprint 동쪽 경계에서 x **1979.99**·y −964.91로 정지(270틱 변동 0 — 벽 → 다각형 재클램프). `glass_1` 정면 Shift+W → y −980.00(footprint 여백과 blocker 면 앞 15 cm가 같은 자리), W+D는 개구부 동쪽 옆벽에서 x −1065.1로 막힘(옆벽 −1050 − 15), W+A 105 cm/s. 실내(문으로 들어가): 북벽 −1564.62(15.38 cm), W+A로 서쪽 90° 모서리 **(135.10, −1564.91)**에서 정지, 184틱 변동 0·진동 없음 |
| §7 ④ 구 | ✅(표면 유지·미끄러짐) | 첫 이동 튐 없음(최대 1.04 cm/틱, 327.8 → 328.79), 표면 거리 **328.8 cm**(유효 반경 = 진입 327.8 + 1, 오버레이 흰 `3.3 / 3.3 m`) 유지, E 위로도 328.8에서 제한. 단 '표면에서 정지'가 아니라 밀기에 원 방향 성분이 있으면 표면을 따라 미끄러진다(카메라가 앵커보다 높아 S 2 s에 z 146.8 → 115.5, 위 접합 행과 같은 원리). 기본 반경(진입 < 3 m, 실내 267.8 cm): D로 밀면 **300.0 cm**에서 제한, 오버레이 `3.0 / 3.0 m`. 바닥 Q → z **15.12**(구면을 따라 y +4.2 cm 미끄러진 뒤 바닥에서 정지, 250틱 변동 0) |
| zone 밖 | ✅ | `photo: photo mode on (fov 80.0, no zone, paused)`, 오버레이 1행 노랑 `PHOTO  no zone  overcast_morning  3.3 / 3.3 m  2x`, 메타 `"zone_id": null`·`"zone_version": null`, 구만 작동(328.81 = 진입 327.81 + 1) |
| 포털 타이머 | ✅(둘 다 허용) | ① 문 트리거 안에서 P → 30 s → P: `door_1` ACTIVE 그대로, 언로드 없음. ② 트리거에서 나와 0.56 s 뒤 P → 10.1 s → P: 종료 **2.44 s 뒤** `Portal door_1: player left -> unload …`. 0.56 + 2.44 = 3.00 s = `UnloadDelaySeconds` → 정지 중 타이머가 완전히 멈췄다(V-09와 같음) |
| §7 ⑤ 반사 꼭짓점 | ✅ 120 fps 도약 없음 / ⚠ 10 fps+Shift 1.54배 | 반사 꼭짓점은 임시 홈으로 만들었다(`L_ZoneTest` footprint·실내는 볼록). 120 fps: 45° 입력(W+D·Shift는 (−600, 600), W+A는 (−200, 600))과 거의 정면 입력(15°·5°, 걷기·Shift) — y **580.00** 정지 → 반경 20 cm 호를 따라 돎(|p − V| = 20.000 ± 0.002, 원 맞춤 반경 19.999~20.002), 틱 이동은 sin(입사각)배(0.71·0.26·0.09)에서 1.00배로 매끄럽게 오르고 꼭짓점 근처 최대 **1.004배**(이 홈에서는 호 투영이 한 틱을 r·cos α / (r − s·sin α)로 묶어 걷기 1.002배·Shift 1.018배가 상한). **10 fps(`t.MaxFPS 10`, dt 0.1 s)**: Shift 45°에서 한 틱이 **69.15 cm = 자유 스텝 45 cm의 1.54배** — 홈 안쪽으로 떨어진 목표점의 최근접점이 x −620 선이라 꼭짓점을 한 번에 가로질렀다(설계 §11-7 한계 실측; 그 틱의 끝점은 S 안, 진동 없음). Shift 15°는 1.07배, 걷기 45°는 1.08배. 10 fps는 원래 45 cm씩 끊기는 화면이라 한 번의 69 cm가 두드러지지는 않는다. 구가 반사 호를 자르는 곳(앵커가 꼭짓점에서 320 cm, 걷기·Shift): 얼지 않고(2차 검증의 영구 정지 없음) 정지 틱 0·진동 없이 구면∩호를 따라 느리게 미끄러짐(0.07~0.12 cm/틱). 호를 벗어난 뒤의 감속은 구에 닿은 것(반사 꼭짓점과 무관) |
| 저 FPS·dt 클램프 | ✅ | `t.MaxFPS 10`: 남쪽 경계 W 스텝 15.000 cm로 980.00에서 정지(14틱 변동 0, 넘침·톱니 없음), Shift+W 유지 변동 0.009 cm, 접합 Shift+W+D 스텝 31.8 cm(= 45·sin 45°). `t.MaxFPS 5`(프레임 0.2 s): 한 틱 최대 14.0 cm ≤ 15 cm → `PhotoMaxTickDt` 0.1 s 클램프가 작동(클램프가 없으면 30 cm) |
| §4 종료 밝기(EV ±3) | ✗ #64 | 진입 전 기준 L 126.6. EV +3 → 촬영 → P: **종료 프레임 220.3**(포토 구도·포토 노출 그대로, 오버레이만 사라짐), 0.23 s 182.9, 0.57 s 140.7, 1.41 s 128.2, 3.55 s 126.6. EV −3: 종료 프레임 40.3, 0.24 s 50.3, 0.58 s 66.1, 1.42 s 96.3, 3.56 s 120.7(3.5 s 뒤에도 덜 참). EV −3 프레임별(s7j, 연속 촬영): 종료 프레임 41.3(포토 화면) → 다음 프레임부터 플레이어 구도 47.4 · 53.2 · 61.5 · 71.3 · 82.5(프레임마다 약 0.12 s) → 1.6 s 107.8 → 3.8 s 123.0(기준 126.1). 종료 직후부터 진입 전 밝기가 아니라 **눈 적응 이력이 이어져 1~4 s에 걸쳐 수렴** |
| #63 (a) 촬영 중 P(지연 종료) | ✅ | 주의: 처음 세 실행(s7b·s7d·s7f의 F2)은 P가 캡처 정지(1.2 s) 뒤 창이 닫힌 다음에 도착해 일반 P 종료였다(로그에 `exit deferred` 없음 — 드라이버는 캡처 프레임 동안 틱하지 않는다). Space 다음 틱에 P를 보내 다시 쟀다(s7g·s7h): `photo: exit deferred until the capture window closes (toggle)` + `P: exit deferred …` → 창이 닫힌 뒤 `photo mode off (restored, unpaused, …)`. 종료 뒤 **두 번째 프레임 126.0**(EV +3 두 번, 플레이어 구도 — 기준과 평균 차 2.3~2.8), 4프레임 뒤(촬영 정지로 약 0.4 s) 126.4, 약 3 s 126.6. EV −3(s7j): 두 번째 프레임 126.5(기준 126.1). 종료 프레임 자체의 화면은 잡지 못했다(PNG 감지가 종료 틱과 같은 틱) — '컷이 플레이어 뷰에 닿는다'는 판단은 틱 추적에 기댄다. 틱 추적: 종료 틱에 카메라 매니저가 이미 플레이어 카메라 위치이고 컷이 그 프레임 그리기에서 소비됨 → 컷이 플레이어 뷰에 닿는다 |
| #63 (b) 사전 정지 진입·종료 | ⚠ 관찰(V-09 ⑥ 재확인) | `pause` → P(`already paused`) → EV +3·이동 → P(`left paused`): 정지가 풀릴 때까지 화면이 **마지막 포토 구도·EV +3 밝기(221.7)로 고정**(뷰 타깃은 캐릭터인데 카메라 매니저 위치는 포토 폰 자리, §12 #3). 0.24 s 간격 10장의 프레임 차이 0.76 → 0.01 → 0.00: 노이즈·깜빡임 없음(컷은 코드상 종료 때 한 번). `pause` 해제 뒤 0.23 s 191.3 → 1.41 s 129.1 → 3.55 s 126.6으로 같은 페이드 |
| #64 원인(s7d·s7f 틱 추적) | — | P 종료 틱: post-tick에서 뷰 타깃 = 캐릭터, **카메라 매니저 위치 = 포토 카메라 자리**(128.7, 492.6, 171.0), 컷 플래그는 이미 지워짐 → 그 프레임은 옛 포토 POV·PP로 그려지며 컷을 소비했다. 다음 틱에야 플레이어 카메라(45, 514, 176.7)로 바뀌는데 컷이 없어 눈 적응이 포토 노출에서 이어진다. 엔진(5.8.3): `UWorld::Tick`이 `bIsPaused`를 틱 시작에 읽고(`LevelTick.cpp` 1565) 정지 중에는 풀틱 PC만 `UpdateCameraManager`(1845) — P 입력은 정지로 시작한 틱의 PC 틱에서 처리되고 `RestoreAll`이 풀틱 플래그를 되돌리므로 그 틱은 카메라 갱신을 건너뛴다. 컷은 `CalcSceneView`(`LocalPlayer.cpp` 828)까지 살아 있다가 그리기 뒤 지워지고(`GameViewportClient.cpp` 1922~1924), 렌더러는 컷이면 목표 노출로 바로 간다(`PostProcessEyeAdaptation.cpp` 723 `ForceTarget`). 지연 종료는 `OnEndFrame`에서 복원하고 다음 틱이 정지 없이 시작해 정상. 확인 실험: `r.Test.CameraCut 1`이면 즉시 126.0, 종료가 보인 틱의 post-tick에서 `SetGameCameraCutThisFrame()`을 한 번 더 부르면 첫 플레이어 프레임부터 126.0(기준 실행 219.9에서 페이드) |
| §10 패키지 잔상(선택) | 미실행 | 실행하지 않았다(선택 항목). 5.8.3 소스 판독: `SceneView.cpp` 3128 `bWorldIsPaused = !(World->IsCameraMoveable() || …)`는 `#if !WITH_EDITOR`(3110) … `#else`(3112) 뒤 **에디터 분기에만** 있고, 이력 읽기 전용은 이 값에 달려 있다(`SceneVisibility.cpp` 5210) → 패키지 빌드는 정지 월드 이력 고정·#57 잔상이 원래 없고 c026815는 그곳에서 효과 없음으로 **예측**(관찰 아님) |
| 컷 뒤 작은 되오름(관찰) | — | 컷이 플레이어 뷰에 닿은 모든 경우(`r.Test.CameraCut`, 늦은 컷, 지연 종료)에서 126.0 → 0.5~1.3 s에 127.2~128.4 → 126.6(약 +1.4 %). 컷이 Lumen·TSR 이력도 지워 다시 쌓이는 과정으로 추정. 눈으로는 거의 안 보인다 |
| 미측정·한계 | — | ① 예각 꼭짓점·inset 두 배보다 좁은 목: 해당 기하 없음(직사각형·4 m 홈). ② 띠 안에서 구가 걸리지 않는 접선 이동: 진입 카메라가 늘 구 표면(진입 거리 + 1 cm)이라 접선으로 움직이면 구가 먼저 걸린다. ③ 135° 꺾임은 한 각도(접선 성분 0.309)·걷기만. ④ zone 밖 충돌은 따로 안 봤다(구만 확인). ⑤ `glass_1` 앞 정지는 footprint 여백 선과 같은 자리라 blocker만의 효과로 떼어 보이지 못했다. ⑥ 포털 ②는 순간 이동으로 트리거를 나갔다(걸어 나가기 아님; 오버랩 끝 이벤트는 발생). ⑦ #64의 1순위 대안(`UpdateCamera(0)`)은 재지 못했고 ②(늦은 컷)만 실측. ⑧ §10 패키지: 잔상·종료 밝기 둘 다 미관찰 |
| 고친 API(§12)·커밋 | 0건 | 컴파일 오류 없음. #64는 동작 문제라 PC fix 대신 클라우드 후속(모델 정책: 코딩은 Opus 5.5) |
| STATUS | WP-12 `🟡 → 🔴` | §7 ①~⑤ 통과(footprint 톱니·벽 밀착 수정 확인; 구·구∩경계 접합에서 표면을 따라 내려가는 것은 설계대로·폴리시 후보; 반사 꼭짓점 2배 한계는 10 fps+Shift에서만 1.54배로 나타남). **§4 종료 밝기 실패(#64, P 종료 경로)** — 수정 뒤 §4 "종료 밝기"(EV ±3, 종료 프레임 포함)와 #63 (b)만 재검증 |

스크린샷: ③ `docs/runbooks/pc-verify-wp12-clamp.jpg`를 **V-09b 남동 모서리 정지 장면**(카메라 (1979.99, 980.00), 정지 뒤 캐릭터·파사드 쪽으로 돌아봄, 오버레이 `1.9 / 3.3 m`)으로 교체(1600×912, 105 KB, 아래 설명 줄 포함). ①②④는 V-09 그대로.

### V-09c 재검증 — WP-12 후속 수정 2(#64 종료 카메라·D-013 결정 3 높이 불변)·PR #40 리뷰 반영(결정 3 확정판·#67) (2026-09-29)
범위(이것만 한다): §1 빌드 → `test.ps1 -Filter Golmok.Photo` 3/3(`EnterExit`에 새 Info 줄 `exit camera: before x.x cm, after x.xx cm, cut 1` 2줄 — 일반 종료·사전 정지 종료, 각각 before > 20·after ≤ 2·cut 1(실패하면 같은 값이 TestTrue 메시지 "precondition: camera manager POV at the photo camera before Exit (x.x cm > 20)"·"camera manager POV back at the player camera right after Exit (x.xx cm <= 2)"·"camera cut set on the exit frame"과 사전 정지 쪽 "… (pre-existing pause, …)"·"camera manager POV back at the player camera while still paused (x.xx cm <= 2)"로 `[Error]`에 찍힌다), 사전 정지 쪽 #67 단언(성공 시 줄 없음; 로그 `photo: world still paused; camera-moveable-when-paused flag kept true until the unpause` → `photo: camera-moveable-when-paused flag restored after the unpause (false)`), `Clamp`에 새 Info 줄 `keep height: from … to …, max |dz| 0.0000, horizontal … / slice … (R …)` — 구 단면 원과 정사각형 여백 선이 만나는 접합(시작 높이 0.5 R) — 와 `keep height wall slide: from … to …, lateral …, |dz| 0.0000, face distance …` — (c2) 벽 대각 슬라이드를 bKeepHeight로) → `Golmok.` 전체 28/28 → §4 "종료 밝기" 1~4(EV ±3; 4는 정지 유지 중 둘째~10번째 프레임 잔상 판정 포함) → §7 "접합 수평 입력 시 높이 불변" ①~⑦(⑥은 게임패드가 있으면; 피치 전제 없음 — 결정 3 확정판). 드라이버는 V-09b 것(틱 샘플·종료 틱 추적)을 그대로 쓴다. 컴파일 오류는 §12 #65·#66·#67.

PC 세션(Claude Desktop 워크트리 `upbeat-mccarthy-343277`, 모델 Claude Fable 5.1; PC fix 적대 리뷰는 Opus 5.5 서브에이전트), 날짜 2026-09-29, 브랜치 `pc/v09c-verify-wp12`(main 5f6c810 = PR #40·#41·#43·#44·#45 병합 뒤). 같은 PC(UE 5.8.3, RTX 5060 8 GB, PIE 새 창 2560×1392, ≈ 120 fps). V-09b 워크트리의 `L_Dev`·`L_ZoneTest`·합성 zone·실내·마네킹을 복사했다. 게임패드 없음(XInput 4슬롯 모두 1167 = 미연결). 처음에 다른 세션의 `-game` 프로세스(`golmok-play`, GPU 95 %)가 떠 있어 그 세션에 요청해 정상 종료한 뒤 GUI를 돌렸다. GUI 잠금 파일에는 8시간 지난 `play-session run-latest` 한 줄만 있었다(stale, 그 세션이 지움). 이후 V-10 세션과 잠금을 번갈아 썼다.
**방식**: V-09b 드라이버를 그대로 쓰고 세 가지를 더했다. ① `stall_burst` — Space 다음 틱에 P를 보내고, HighResShot 정지 틱부터 매 틱 샷을 찍는다. 포토 폰이 살아 있던 마지막 틱의 샷이 지연 종료의 종료 프레임이다. ② 틱 샘플에 월드 좌표를 더했다(zone 좌표 z는 zone 액터의 ENU 기울기를 탄다). ③ 캐릭터 추적(V-11). 키·마우스 입력은 전부 Win32 `SendInput`이다. 밝기는 `shot showui` PNG 가운데 60 %의 휘도 평균(PIL, Rec.709)이다. 구도·잔상은 같은 영역의 평균 절대차와 16×16 블록 최대 차로 판정했다. **종료 프레임** = P를 보낸 post-tick에서 요청한 샷이다. 그 샷은 다음 프레임, 곧 P를 처리한 틱이 그린 프레임을 찍는다(틱 추적으로 확인: 그 post-tick까지 포토 폰이 살아 있고 다음 post-tick에 없다). 시나리오는 c4(GamePause 조합 1·2·4), c4t(TimeDilation), c2s(지연 종료의 종료 프레임), c7(§7 L_ZoneTest), c7d(§7 ⑦ L_Dev)이다. 드라이버·원본 PNG·틱 JSON은 세션 스크래치에만 있다.

| 항목 | 결과 | 실측 |
|---|---|---|
| 빌드·자동화 | ✅ | 1차 빌드 C++ 무수정 성공(317 s, 프로젝트 경고 0 — 엔진 헤더 C4996만). §12 #65 `UpdateCamera(0.f)`·#66 `bGameCameraCutThisFrame` 대안 불필요. `test.ps1 -Filter Golmok.Photo` **3/3**: EnterExit `exit camera: before 74.4 cm, after 0.00 cm, cut 1` **2회**(일반·사전 정지 — before > 20·after ≤ 2·cut 1), 로그 `photo: world still paused; camera-moveable-when-paused flag kept true until the unpause` → `photo: camera-moveable-when-paused flag restored after the unpause (false)`(#67 단언 성공), Clamp `keep height: from X=-500.000 Y=0.000 Z=258.548 to X=-240.524 Y=114.318 Z=258.548, max \|dz\| 0.0000, horizontal 283.54 / slice 284.75 (R 328.8)`(slice −1.21), `keep height wall slide: from X=-480.000 Y=0.000 Z=94.150 to X=-466.028 Y=40.000 Z=94.150, lateral 40.0, \|dz\| 0.0000, face distance 16.0`. 전체 `test.ps1` **28/28 Success**(20 + Warning 8, failed 0·notRun 0, `RenderEvidence` NOT EXECUTED 1 정상, PhotoIntegration 6조합 EXECUTED). Warning에 WP-13 SoundWave 미임포트 7줄(이 워크트리에서 `audio_import`를 돌리지 않음 — V-10 영역, 판정 무관). pytest(MSVC g++ 심) **860 passed, 7 skipped**, `ruff check`·`ruff format --check`·`check_repo.py` 통과. **PC fix(§12 #68) 뒤**: 증분 빌드 성공, `Golmok.Photo` 3/3에 (c3) `keep height slope slide: from X=-480.000 Y=0.000 Z=94.150 to X=-476.084 Y=40.000 Z=94.150, lateral 40.0, \|dz\| 0.0000, face distance 15.9`. 수정을 끈 빌드로 같은 테스트를 돌리면 lateral 2.3으로 실패한다(판별력 확인). 전체 28/28 Success(20 + 8), fixture pytest 65 passed. **main 8e6b311 병합 뒤**(WP-14a·WP-15a·V-10, Photo는 WP-15 훅 2곳뿐) 재빌드: `Golmok.Photo` 3/3(같은 Info 줄), 전체 **32/32 Success**(21 + 11), pytest 1128 passed·7 skipped(MSVC 심) |
| §4 종료 밝기 1 GamePause·즉시(EV +3 / −3) | ✅ | 기준 L(진입 직전 플레이어 화면) 126.58 / 126.59. 포토 화면 221.97(EV +3) / 41.23(EV −3). **종료 프레임**(P를 보낸 post-tick에 요청한 샷 = P를 처리한 틱이 그린 프레임) **125.97 / 126.39**, 다음 프레임 126.09 / 126.49, 0.14 s 126.46 / 126.88, 0.39 s 126.85 / 126.81, 1.27 s 127.20 / 126.76, 3.46 s 126.62 / 126.62 — 전부 기준 ±5(최대 차 0.62). 구도: 종료 프레임과 기준의 차(가운데 60 % 평균 절대차) 2.83 / 2.55, 포토 화면과는 95.84 / 89.70 → 플레이어 구도. 틱 추적: P를 처리한 틱의 post-tick에서 포토 폰 없음·뷰 타깃 `GolmokCharacter_0`·**카메라 매니저 위치 = 플레이어 카메라 (45.0, 514.0, 176.7)**(직전 틱은 포토 카메라 (152.5, 479.3, 176.7); V-09b는 이 틱에 포토 카메라 자리), 컷 플래그는 그리기에서 이미 소비(false, V-09b와 같은 관찰 위치), 정지 해제. V-09b ✗(종료 프레임 220.3 → 3.5 s 페이드) 해소 |
| §4 종료 밝기 2 GamePause·지연 | ✅ | Space 다음 틱에 P → `photo: exit deferred until the capture window closes (toggle)` + `P: exit deferred …` → `capture window closed (… present after 1.14~1.35 s)` → `photo mode off (restored, unpaused, tod shift 0.000 s)`. **종료 프레임**(HighResShot 정지 틱부터 매 틱 샷, 포토 폰이 살아 있던 마지막 틱의 샷 — c2s) **125.98 / 126.46**(기준 126.60 / 126.61), 다음 프레임 126.08 / 126.55, 종료 뒤 0.19 s 126.52 / 126.91, 0.69 s 128.04 / 127.08(작은 되오름 — V-09b 관찰과 같음), 1.58 s 126.98 / 126.71, 3.76 s 126.58 / 126.58 — 기준 ±5(최대 차 1.44). 구도 차: 기준과 2.75 / 2.66, 포토와 95.83 / 89.76. c4 실행(PNG 감지 틱 샷 = 종료 뒤 둘째 프레임)도 126.03 / 126.65 → 0.26 s 126.50 / 126.75 → 1.14 s 127.54 / 126.82. V-09b ✅ 회귀 없음(이번엔 종료 프레임 자체도 확인) |
| §4 종료 밝기 3 TimeDilation·즉시 | ✅ | `PauseMode=TimeDilation`(ini 임시 변경 → 에디터 재시작 → 실행 뒤 `git checkout`, `git diff` 비어 있음). 진입 시 프로브 `paused False`·`time_dilation 0.0001`. EV는 화면에 안 먹음(#61: 포토 화면 127.60 / 132.93) → 구도만 판정. 종료 프레임 126.33 / 126.16(기준 126.58 / 126.59), 다음 126.63 / 126.56, 0.38 s 126.72 / 126.63, 1.27 s 126.76 / 126.75. 구도 차: 기준과 2.40 / 2.57, 포토와 15.25 / 18.50(밝기가 같아 포토와의 차가 작다 — 그래도 기준 쪽이 6배 가깝다). 틱 추적: 종료 틱 post-tick 카메라 매니저 = 플레이어 카메라 |
| §4 종료 밝기 4 사전 정지 (b)(둘째~10번째 프레임 잔상·#67 로그 두 줄) | ✅ | `pause` → P(`already paused`) → EV ±3 → D 0.8 s(1.2 m) → 촬영 → P: `photo: world still paused; camera-moveable-when-paused flag kept true until the unpause` → `photo mode off (restored, left paused, tod shift 0.000 s)`, 이후 `pause` 해제 첫 프레임에 `photo: camera-moveable-when-paused flag restored after the unpause (false)`(두 EV 모두 두 줄). **정지 유지 중 종료 프레임부터 플레이어 구도**: 종료 프레임 125.93 / 126.33, 둘째~10번째 프레임 125.99~126.52 / 126.62~126.88(프레임마다), 0.24 s 간격 10장 126.58~126.76 / 126.58~126.62, 해제 뒤 126.57~126.62 / 126.58~126.61(기준 126.58 / 126.59). **잔상**: 둘째~10번째 프레임과 종료 프레임의 평균 차 0.45~1.65 / 0.57~1.74, 16×16 블록 최대 차 ≤ 11(차 이미지 ×8: 캐릭터 윤곽의 TSR 누적 선명화·밝은 상자 둘레 번짐만, 포토 위치의 캐릭터·배경 흔적 없음), 포토 화면과의 차 ≥ 95.3 / 89.7 유지. 10장 사이 프레임 차 0.30~0.36(노이즈·깜빡임 없음). 틱 추적: P 다음 post-tick에 카메라 매니저 = 플레이어 카메라, `paused True` 유지. V-09b ⚠(정지 해제까지 포토 구도 221.7 고정) 해소 → #63 (b) ✅ |
| §7 접합 수평 입력 높이 불변 ①~⑦ | ✅ ①~⑤, ⑦(PC fix #68 뒤) / ⑥ 미실행(게임패드 없음) | 카메라는 E 0.4 s로 앵커(캡슐 중심)보다 **약 111 cm 높이** 둔다(149.0 → 204.0; 키를 뗀 뒤 한 틱 +1.1). 이하 z는 틱 샘플의 zone 좌표 z다. zone 좌표 z는 수평 이동에 따라 기울기 x 2.775e-5·y −3.526e-5 /cm로 변한다. zone 루트 로그 `(10,0,0) m -> … 999.34 cm`(원점 999.37)와 같은 ENU 기울기이고, 한 평면으로 맞추면 수평 입력 2565틱 전체의 잔차가 **≤ 0.0006 cm**(기록 해상도 0.001)다. 즉 월드 z 변동 0이다. L_Dev(zone 없음, 월드 좌표)에서는 기울기 없이 변동이 **정확히 0.000**이다. ① **구∩남쪽 경계 접합**: W 3 s — y 613.58 → **980.005**(경계 − 20 cm, 틱 4088)에서 멈춘 뒤 66틱 변동 0. 이어 Shift+W+D 2 s — 경계를 따라 x −43.10 → **−303.155**(틱 4266)에서 구의 수평 단면 원(앵커 수평 거리 309.0, 3D 328.4 ≈ 유효 반경 328.8)에 닿아 **정지**(뒤 128틱 변동 0). W+D 1 s 더 밀어도 0.27 cm 뒤 정지. z 변동 0(zone z 205.140 → 205.120 = 기울기 성분). V-09b의 −44 cm 하강은 없다. ② **경계 없는 쪽 구 표면**: Shift+W 2 s — y 506.4 → −108.9(앵커 위를 지나 반대편 원, 수평 거리 309.4), 원을 따라 x 43.07 → 17.29로 수평으로만 미끄러짐. W 1 s 더 — 틱당 ≤ 0.07 cm로 극 쪽 수렴(수평). z 변동 0. ③ **파사드 벽 대각선**: Shift+W로 y −964.62(면에서 15.4 cm), W+D 2 s — 벽을 따라 x 43.04 → 254.39(**105.7 cm/s** = 150·sin 45°), W+A 2 s 되돌아옴. 면 거리 15.09 일정, z 변동 0. ④ **E/Q 동시**: 접합에서 W+D+E 1 s → z +39.4(구면을 따라 x −303.4 → −286.0), W+D+Q 1 s → z −101.8. 구에서 W+E +47.1, 벽에서 W+D+Q −85.9 — **z가 변한다**. ⑤ **피치 −30°**(마우스 857 px, 프로브 `p=-30.00`): 구 표면에서 W 1.5 s → z 205.336 그대로(수평으로 0.03 cm/틱 수렴). 열린 곳 W 1 s → y 520.0 → 370.1(150 cm/s), z 변동 0(기울기 성분 0.005). 이어 Shift+W 2.5 s로 구까지도 z 변동 0. 벽에 피치 −30° W 1 s → **정지**(120틱 이동 0, z 0). W+D는 벽을 따라 105 cm, z 0. L_Dev 경사로 위로 피치 −30° W 3 s → 449 cm 수평, z **149.000 고정**. ⑥ 게임패드 없음 → 미실행(`showdebug enhancedinput`은 키보드만으로 화면 확인 — 축 값 판독 불가). ⑦ **낮은 카메라**(Q 0.8 s → z 29.2, 바닥 위 약 14 cm 틈): 12° 경사로 정면 W 3 s → x **525.14**에서 경사면에 닿아 정지(면까지 15.04 cm). Shift+W 1 s 이동 0. 계단 정면 W 3 s → 첫 단 앞 모서리(x 500, 높이 17)에서 x **491.11** 정지. **오르지 않음, z 변동 0.000**(L_Dev 월드 좌표). E를 같이 누르면 경사를 타고 z +105.3. **그러나 비스듬히(W+D·W+A 2 s) 밀면 수평으로 미끄러지지 않고 멈췄다**: 경사로 0.02 cm·0 cm, 계단 모서리 0.07 cm(240틱). 원인은 §12 #68(슬라이드 평탄화가 경사면·모서리에서 면 안쪽을 향함) → PC fix, 헤드리스 (c3) 통과. **수정 뒤 재확인(c7i)**: 이때 방화벽 알림 창(아래 한계 ⑤)이 포그라운드를 잡고 있어 SendInput을 쓸 수 없었다. 그래서 헤드리스 에디터(`-nullrhi`) PIE에서 Enhanced Input 주입으로 같은 L_Dev 기하·같은 움직임을 다시 했다. `EnhancedInputLocalPlayerSubsystem.inject_input_vector_for_action`으로 `IA_GolmokPhotoMove`·`UpDown`·`Fast`에 W·W+D·Q·Shift와 같은 값을 매 틱 넣었다. 키 매핑만 우회하고 폰 `Tick` → `MoveConstrained` 경로는 같다. 결과: 경사로 정면 W → x 525.11에서 정지(Shift도 이동 0). **W+D 2 s → 경사면에 붙은 채 y로 0.88 cm/틱(≈ 106 cm/s = 150·sin 45°) 미끄러지고**, 경사로 옆을 지나면 대각선으로 진행. W+A → 경사로 옆면·구 한계에서 정지. 계단 앞 모서리 W+D → 모서리를 따라 y 0.88 cm/틱, 계단 옆을 지나 진행. 모두 **z 변동 0.000**(월드). 바닥까지 내린 카메라(z 15.119)로 W 2 s → y 44.406 불변(옆으로 새지 않음). 계단 정면의 첫 두 틱에 z −1.2가 있었는데, Q 주입을 끊은 뒤 한 틱 늦게 풀린 것이다(같은 틱에 x도 구 쪽으로 0.24 이동). 그 뒤 358틱은 변동 0이다. 겹침 후퇴(`bStartPenetrating`)와 겹친 z 변화는 없었다 |
| 틱 샘플(틱·x·y·z·dt, zone 좌표 cm·Slate dt ms) | — | ① W: 3795 (−43.091, 613.576, 205.140) 8.78 → 3796 (−43.091, 614.826, 205.140) 8.03 → 4087 (−43.099, 978.787, 205.127) 8.79 → **4088 (−43.099, 980.005, 205.127) 8.27** → 4154 (−43.099, 980.005, 205.127) 8.06. ① Shift+W+D: 4155 (−43.099, 980.005, 205.127) 8.81 → 4156 (−45.750, 980.005, 205.127) 9.03 → **4266 (−303.155, 980.005, 205.120) 9.51** → 4394 (−303.155, 980.005, 205.120) 8.43. ④ W+D+E: 4627 (−303.438, 980.005, 205.120) → 4687 (−294.541, 980.006, 226.996) → 4746 (−285.990, 980.007, 244.508). ② Shift+W: 5322 (43.070, 506.369, 205.316) 8.59 → 5441 (43.079, 54.458, 205.331) → 5560 (17.289, −108.885, 205.336) 8.31. ⑤ 피치 −30° W(구): 5778 (10.532, −109.189, 205.336) → 5958 (5.098, −109.326, 205.336). ③ W+D(벽): 7595 (43.043, −964.621, 206.051) 8.23 → 7715 (149.123, −964.911, 206.054) → 7834 (254.394, −964.911, 206.057) 8.31. ⑤ 피치 −30° W(벽): 8274~8393 (42.972, −964.911, 206.051) 이동 0. ⑦ L_Dev 월드 좌표: 경사로 W 1074 (80.802, −2155.113, 29.157) 8.53 → **1430 (525.141, −2155.113, 29.157)** → 1433 같음. 경사로 W+D 1660 (525.141, −2155.113, 29.157) → 1661 (525.158, −2155.096, 29.157) → 1899 같음(수정 전). 계단 W+D 3247 (491.111, −1455.113, 29.156) → 3248 (491.154, −1455.054, 29.156) → 3486 같음(수정 전). 피치 −30° W 3979 (80.000, −2155.000, 149.000) → 4338 (528.771, −2155.000, 149.000). **수정 뒤(c7i, L_Dev 월드)**: 경사로 W+D 1160 (525.110, −2155.113, 29.156) 8.53 → 1162 (525.147, −2154.229, 29.156) 8.05 → 1200 (525.147, −2120.641, 29.156) 8.23 → 1399 (637.654, −1982.233, 29.156) 8.39. 계단 W+D 2692 (489.628, −1455.147, 27.955) 8.36 → 2694 (489.665, −1454.263, 27.955) 8.12 → 2732 (489.665, −1420.673, 27.955) 8.60 → 2931 (621.046, −1265.728, 27.955) 8.43. 바닥 W 4002 (−815.776, 44.406, 15.119) 8.47 → 4241 (−518.268, 44.406, 15.119) 8.15. |
| 미측정·한계 | — | ① ⑥ 게임패드 없음 → 미실행(`IA_GolmokPhotoUpDown` 데드존 0 < \|축\| ≤ 0.1 구간은 pytest·코드로만). ② L_ZoneTest의 z 판정은 zone 좌표 샘플을 한 평면으로 맞춘 잔차(≤ 0.0006 cm)다. 월드 좌표 샘플은 L_Dev에서만 기록했다(드라이버에 뒤늦게 추가). ③ 수정 뒤 ⑦은 Enhanced Input 주입(헤드리스)이다. SendInput 키 경로는 수정 전 실행(c7d)에서만 확인했고, 수정은 키 경로를 건드리지 않는다. ④ 밝기 시각은 실시간이다. 매 틱 샷이 프레임을 멈추게 해서 '0.25 s'·'1 s' 샷이 0.13~0.39 s·1.13~1.72 s에 찍혔다(실측 시각을 그대로 적음). ⑤ 05:48부터 Windows 방화벽 알림 대화상자(`PickerHost.exe FirewallNotificationDialogServer`, V-10 세션의 패키지 `golmok.exe` 대상, 최상위)가 포그라운드를 잡았다. 그래서 수정 뒤 GUI SendInput 재실행과 V-11 녹화를 하지 못했다. 보안 설정이라 누르지 않고 소유자 조작을 기다린다. ⑥ §10 패키지 잔상·종료 밝기(선택)는 미실행 |
| 고친 파일(PC fix)·커밋 | 1건(§12 #68) | `Photo/GolmokPhotoCameraPawn.cpp`(`MoveConstrained` keep-height 슬라이드: 수평 법선 쪽 성분 제거·상수 `PhotoSlopeSlideMinHorizontal`), `.h`(주석), `Tests/GolmokPhotoTest.cpp`(Clamp (c3), 이름 추가 없음), `tools/tests/test_ue_wp12_fixture.py`(순서 단언 1곳). Opus 5.5 적대 리뷰: "sound" — 수학(Z 정확히 0, 길이 ≤ 남은 이동)·LWC 컴파일·3D 경로 무변경 확인. 제안 3건(한쪽 투영, 거의 수평인 법선 제외, 고정 테스트) 모두 반영. Astra 레인 파일은 건드리지 않았다 |
| STATUS | WP-12 `🟡 → 🟢`(PC fix #68 포함 — 병합 리뷰 대상), V-09 `🔴 → 🟢` | §4 "종료 밝기" 1~4(EV ±3)·#63 (b)·§7 "접합 수평 입력 시 높이 불변" ①~⑤·⑦ 통과(⑦은 PC fix 뒤 헤드리스 (c3)와 주입 재확인), ⑥은 게임패드가 없어 미실행. §12 #64~#67 "확인", #68 새 행(수정). 남은 것(비차단): 수정 뒤 ⑦의 SendInput GUI 재확인·§10 패키지(선택) |
