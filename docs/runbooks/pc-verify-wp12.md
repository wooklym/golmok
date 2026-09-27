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
| `Source/Golmok/Photo/GolmokPhotoMath.h` | 순수 헤더(따옴표 include는 `Geo/GolmokGeoMath.h`·`Debug/GolmokStatsMath.h` 2개): `ClampParam/Quantize/StepLinear/StepGeometric/StepTable/NearestIndex/WrapDeg180/FovToFocalMm`, `ClampToSphere/ClampToPolygonXY/Constrain`, `PhotoMeta`+`FormatPhotoMetaJson`(g++ 교차검증 `tools/tests/fixtures/ue/photomath_driver.cpp`) |
| `Source/Golmok/Photo/GolmokPhotoModeSubsystem.{h,cpp}` | `UGolmokPhotoModeSubsystem`(월드 서브시스템, Game/PIE): `GolmokPhotoJson` 파서, 상태기계 `Inactive/Active/Shooting/Captured/Exiting`, `Enter/Exit/Toggle/Reset/Shoot`, `StepParam/SetParam/SetMultiplier`, `OnEndFrame` 캡처 창, `BuildMeta/WriteMeta`, 오버레이 줄, 입력 자산 `IA_GolmokPhoto*` 21개 + `IMC_GolmokPhoto`(우선순위 3), 콘솔 `golmok.photo`·`golmok.photo.shoot`·`golmok.photo.reset`·`golmok.photo.set`; 복원 스냅샷 공개 계약 `FGolmokPhotoRestoreState` + `GetRestoreState() const`(f5c8861, WP-18 로스터×포토 테스트용) |
| `Source/Golmok/Photo/GolmokPhotoCameraPawn.{h,cpp}` | `AGolmokPhotoCameraPawn`: 구(`PhotoSphere`, QueryOnly, WorldDynamic)·카메라(`PhotoCamera`), `bTickEvenWhenPaused`, `MoveConstrained`(구 → 다각형 → 스윕, `bStartPenetrating`이면 앵커 쪽 10 cm 후퇴), `ApplyOptics`(PP 오버라이드), `EndPlay → Owner->OnPhotoPawnEndPlay` |
| `Source/Golmok/Debug/GolmokDebugSubsystem.{h,cpp}` | `RequestHighResScreenshot(AbsolutePathNoExt, Multiplier, OutMessage, OutEffectiveMultiplier)` public 분리(`TakeHighResScreenShot()` false면 1x 재시도), `TakeScreenshot`은 래퍼; `StartRecording/StartPlayback` 첫 검사 `photo mode is on (golmok.photo 0 first)` |
| `Source/Golmok/Debug/GolmokHUD.{h,cpp}` | `DrawHUD` 첫머리 `IsHudSuppressed()`(= 캡처 창) 가드 + 왼쪽 아래 포토 오버레이(흰/노랑·시안·회색·초록), 클래스 주석 정정 |
| `Source/Golmok/Player/GolmokPlayerController.{h,cpp}` | `IA_GolmokPhotoToggle`(P, `Gamepad_Special_Left`, `bTriggerWhenPaused`)·`IMC_GolmokPhotoToggle`(우선순위 2, 항상), `OnTogglePhoto`(로그 `P: …`), `SetDebugKeysSuspended/IsDebugKeysSuspended`, `SetupInputComponent`가 `Photo->BindInput(Input)` 위임; `GetFullTickWhenPausedFlag/SetFullTickWhenPausedFlag`(f5c8861 — `APlayerController::bShouldPerformFullTickWhenPaused`가 5.8.3에서 protected라 원시 비트 스냅샷·복원, §12 #3) |
| `Source/Golmok/Player/GolmokGameViewportClient.{h,cpp}` | 신규(f5c8861): `UGolmokGameViewportClient`(`UGameViewportClient` 파생) — `IsTransitionMessageSuppressed() const`로 protected `bSuppressTransitionMessage`를 읽음(엔진은 setter만 있음, §12 #12) |
| `Config/DefaultEngine.ini` | 파일 끝 `[/Script/Engine.Engine]` 절(`[WP-12 hook]`) `GameViewportClientClassName=/Script/Golmok.GolmokGameViewportClient`(f5c8861; 병합 전 리뷰로 파일 끝으로 이동). 이 줄이 없으면 서브시스템이 엔진 기본값(false)으로 복원하고 §2의 Warning을 1회 찍는다 |
| `Source/Golmok/Zones/GolmokZoneSubsystem.{h,cpp}` | 추가만: `AGolmokZone* FindLoadedZoneAt(const FVector2D& LevelUEPointCm) const`(Loaded + footprint 포함 + `ZoneWins`) |
| `Source/Golmok/Lighting/GolmokTimeOfDay.{h,cpp}` | 추가만: `void ShiftTransitionStart(double DeltaSeconds)`(전환 중 아니면 no-op) |
| `Source/Golmok/Tests/GolmokPhotoTest.cpp` | 자동화 3개 `Golmok.Photo.EnterExit / Clamp / MetaJson`(`EditorContext \| ProductFilter`, `L_Dev`, 대기는 전부 `FPlatformTime`) |
| `Config/DefaultGame.ini` | `[/Script/Golmok.GolmokPhotoModeSubsystem]` 11키(§4·§5·§6·§7 참조): `ConfigFile=Golmok/photo.json`, `PhotoFolder=Screenshots/Golmok/photo`, `ScreenshotMultiplier=2`, `MaxMultiplier=3`, `MaxDistanceM=3.0`, `CollisionRadiusCm=15`, `FootprintMarginM=0.2`, `MoveSpeedMps=1.5`, `PreCaptureFrames=2`, `PostCaptureFrames=2`, `PauseMode=GamePause`. 다른 섹션·`DefaultInput.ini`(`!DebugExecBindings=ClearArray`) 무변경 |
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
                           [Info] ApplyPreset(clear_noon) started no transition; drift assertion skipped   (나오면 안 됨 — §12 #50; "lighting presets file missing; drift block skipped"도 마찬가지)
                           [Info] SetGamePaused(true) refused; pre-existing pause block skipped           (나오면 안 됨 — §12 #1)
  Golmok.Photo.Clamp       [Info] after +1000 x: X=… Y=… Z=… (anchor X=… Y=… Z=…)     (구 300 cm 안·정사각형 ±200 cm 안)
                           [Info] after -500 z: X=… Y=… Z=… (floor z …)                (바닥 스윕 — §12 #49)
                           [Info] box at X=… Y=… Z=…: pawn X=…, face distance …, along …   (face distance ≥ 15 − 1, along < 100 — §12 #47)
                           [Info] box destroyed: pawn X=…, along …                    (along > 100)
  Golmok.Photo.MetaJson    [Info] Describe(): active fov 80.0 ev +0.00 focus 3.000 m f/2.80 dof off roll +0.0 (no zone)
                           [Info] shooting -> <Saved>/Screenshots/Golmok/photo/<stamp>.png (2x, meta <stamp>.json)
                           [Info] capture window closed after 3.xx s                  (-nullrhi는 PNG를 쓰지 않으므로 3 s 타임아웃 경로)
                           [Info] the clock rolled over between the marker and the second shot; _2 suffix not asserted   (초 경계에 걸리면 1회 — 무해)
  ```
  MetaJson의 로그에는 `photo: screenshot requested via HighResShot -> <Saved>/Screenshots/Golmok/photo/<stamp>00000.png (no viewport size; written on the next frame)`와 `photo: capture window closed (<stamp>.png timeout 3.0 s, png absent)`가 찍힌다(nullrhi 폴백 — 정상). 테스트가 만든 `<stamp>.json`·`_2.json`은 소멸자가 지운다(남아 있으면 §13에).
- [ ] 두 번째 명령: **22개** 전부 `Success` = WP-09까지 16개(`Golmok.Player.Movement`, `Lighting.PresetsFile/PresetApply`, `Debug.StatsMath/PathFormat/PathRoundTrip/HudStats`, `Portal.SpawnFromManifest/RoundTrip/PawnSwap/SharedInterior`, `Zone.IndexParse/IndexDiscover/AsyncLoad/AsyncCancel/InteriorNotBlocked`) + WP-18 병합분 3개(`Golmok.Character.Config/Runtime/PortalRoundTrip` — `Tests/GolmokCharacterRosterTest.cpp`·`GolmokCharacterRosterPortalTest.cpp`) + 위 3개. `test.ps1` 요약 줄 `Succeeded:`는 Warning이 있는 테스트를 따로 세므로(V-03) 상태 열이 전부 `Success`인지로 본다.
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
  LogGolmok: photo: photo mode off (restored, left paused, tod shift 0.000 s)
  LogGolmok: P: photo mode off
  ```
  P가 안 먹으면(정지 상태에서 풀틱이 아직 꺼져 있어 입력이 안 옴) `golmok.photo 1`로 진입해 나머지를 진행하고 §12 #4에 "사전 정지 P 불가"로 기록.
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
golmok.photo.set mult 3      → golmok.photo.set: mult 3      (`3x`)
golmok.photo.set mult 4      → golmok.photo.set: ERROR multiplier must be 1..3 (MaxMultiplier)
golmok.photo.set mult 0      → golmok.photo.set: ERROR multiplier must be 1..3 (MaxMultiplier)
```
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
- [ ] **벽**: 파사드·blocker(`glass_1`) 앞으로 밀기 → 표면에서 `CollisionRadiusCm`(15 cm) 앞에 정지, 관통 0(§12 #16). 밀착 상태에서 다른 방향으로 이동이 계속 된다(`bStartPenetrating` 후퇴가 매 틱 반복되면 §12 #40). 스크린샷 ③.
- [ ] **구**: 캐릭터에서 3 m 밖으로 밀기 → 구 표면에서 정지, 오버레이 1행 거리 = 분모(`3.0 / 3.0 m`, 진입 카메라가 3 m 밖이었으면 그 거리로 넓어진 유효 반경, 예 `3.3 / 3.3 m` — `GetEffectiveRadiusCm()`). 첫 이동에서 카메라가 앵커 쪽으로 튀지 않는다. 위로도 같다(높이 상한 없음, 구만).
- [ ] **바닥**: 아래로(Q) → 바닥 15 cm 위에서 정지(로우 앵글 허용; 뚫고 내려가면 §12 #49).
- [ ] **footprint**: 캐릭터를 001 footprint 경계 1 m 안에 세우고(`golmok.collision 1`로 충돌 메시·blocker·트리거를 보며 경계 확인 → `golmok.collision: …`) P → 카메라를 바깥으로 → 경계 `FootprintMarginM`(0.2 m) 안쪽에서 정지(다각형 클램프; 구 밖으로 밀리면 이동 취소 = 그 자리 유지). 오목 코너 근처에서 "걸리는" 느낌은 설계 §11-7의 알려진 한계 — 있었는지만 §13에.
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
| 1 | `UGameplayStatics::SetGamePaused(const UObject*, bool)` → bool / `IsGamePaused` (`Kismet/GameplayStatics.h`) — BP 문서로 존재·bool 반환 [확인] | C++ 시그니처 [2차]; 내부 `APlayerController::SetPause` → `AGameModeBase::SetPause`(`AllowPausing` 기본 true [2차]) | `PC->SetPause(true)` / `World->IsPaused()`; 게임모드가 거부하면 `AGolmokGameMode::AllowPausing` override true | §2 캐릭터 애니 정지·로그 `paused` | |
| 2 | 폰 생성자 `PrimaryActorTick.bTickEvenWhenPaused = true` → 정지 중 `Tick` 호출 [확인 가이드 예시]; `DeltaSeconds` 값(0인지 실시간인지) [미확인] | 정지 틱의 dt 의미. 설계는 `FApp::GetDeltaTime()`(0.1 s 상한)을 쓰므로 무의존. `AActor::SetTickableWhenPaused`는 쓰지 않음(페이지 본문 없음) | 틱이 안 오면 ini `PauseMode=TimeDilation` | 자동화 EnterExit 틱 카운터 > 0 + §3 이동 부드러움 | |
| 3 | `APlayerController::bShouldPerformFullTickWhenPaused`(public? 비트필드?) = true로 정지 중 `UpdateCameraManager`(뷰 타깃 폰의 카메라 반영) [2차 M1] — 페이지 본문 없음 [미확인] | 접근성·동작. 값은 `const bool bSaved = PC->…`로 복사(참조·포인터 금지) | 멤버가 private면 `AGolmokPlayerController::ShouldPerformFullTickWhenPaused() const` virtual override(`bPhotoFullTick` 플래그 반환) [2차]; 그래도 얼면 폰 Tick 끝에 `PC->PlayerCameraManager->UpdateCamera(dt)` [미확인]; 최후 `PauseMode=TimeDilation` | §3 이동 시 화면이 따라옴 | 수정(f5c8861): V-09 1차 빌드에서 C2248(protected) 확인 → `AGolmokPlayerController::GetFullTickWhenPausedFlag/SetFullTickWhenPausedFlag`로 원시 비트 스냅샷·복원. 동작(§3)은 미확인 |
| 4 | 정지 중 Enhanced Input: `UInputAction::bTriggerWhenPaused = true` [확인 필드] + PC 틱(풀틱 또는 약식)이 `TickPlayerInput(…, bGamePaused = true)` 수행 [2차 M2] | 발화 여부; 사전 정지(풀틱 아직 꺼진 상태)에서 P가 먹는지 | `PauseMode=TimeDilation` | §2 사전 정지 + P; §3 정지 중 WASD | |
| 5 | 풀틱 정지에서 캐릭터 `IMC_Default` 액션(`bTriggerWhenPaused = false`)이 발화하지 않음 + 포토 IMC(우선순위 3)의 `bConsumeInput` [확인 필드]이 같은 키를 하위로 넘기지 않음 [2차] | 소비·정지 게이트 규칙 | 캐릭터가 튀면 `AGolmokCharacter`에 `RemoveMappingContextForPhoto()` public 추가(PC fix 허용 범위) | §3 포토 중 WASD·마우스·Space → 나간 뒤 캐릭터 위치·회전 불변 | |
| 6 | `UEnhancedInputLocalPlayerSubsystem::RemoveMappingContext(const UInputMappingContext*)`(디버그 컨텍스트 제거·포토 컨텍스트 제거; `AddMappingContext`는 V-03 확인) | 오버로드(`FModifyContextOptions` 기본 인자) [2차] | `RemoveMappingContext(Ctx, FModifyContextOptions())`; 없으면 `ClearAllMappings()` 뒤 필요한 것 재추가(캐릭터 IMC 포함) | §3 F키 무반응, 이탈 후 복귀 | |
| 7 | `UEnhancedInputComponent::BindAction(Action, ETriggerEvent, UObject*, MemberFn)`에 `UWorldSubsystem` 메서드 바인딩(UFUNCTION 불필요) — WP-05가 PC 메서드로 확인 [확인]; 서브시스템도 `UObject` [2차] | 템플릿 제약 | 핸들러 21개를 `AGolmokPlayerController`에 두고 서브시스템으로 위임(①안) | 빌드 | |
| 8 | 정지 중 뷰 이력 읽기 전용(`bWorldIsPaused` → `bStatePrevViewInfoIsReadOnly`) [2차 M4] → 이동 중 TSR 고스팅·Lumen 노이즈 고정·눈 적응 정지; 고해상도 프레임은 히스토리 없이 그려짐; `r.HighResScreenshotDelay` cvar 존재 [미확인] | 화질 | `PauseMode=TimeDilation`; `PreCaptureFrames`↑; cvar 있으면 값 ↑ 실험 | §4 이동 중·정지 후 화면, §6 1x/2x 크롭 비교 | |
| 9 | 카메라 컴포넌트 `PostProcessSettings` 오버라이드: `bOverride_AutoExposureBias/AutoExposureBias` [확인 V-03 볼륨 동일 필드], `bOverride_DepthOfFieldFocalDistance/DepthOfFieldFocalDistance(cm)`, `bOverride_DepthOfFieldFstop/DepthOfFieldFstop`, `bOverride_MotionBlurAmount/MotionBlurAmount` [2차 이름], `PostProcessBlendWeight`; `FocalDistance = 0` = DOF 끔 [2차]; 카메라 오버라이드가 PPV 값을 **대체**(가산 아님) [2차]; 정지 중 뷰에 적용 [2차] | 필드명·off 규약·대체 규칙 | 이름은 오류 메시지대로(`Scene.h` grep); DOF off가 안 되면 `Fstop = 16`·`FocalDistance = 5000 cm`로 근사; EV 0 밝기가 다르면 base 재가산 제거 | §4 DOF on/off·EV ±3·EV 0 밝기 동일, §5 번짐 없음 | |
| 10 | 정지 중 노출 바이어스 변경이 **즉시** 화면에 반영(눈 적응 히스토리가 멈춰도 bias는 곱셈) [2차] | 눈 적응 정지로 EV 변화가 안 보일 가능성 | `bOverride_AutoExposureSpeedUp/Down = true, 값 20`(포토 동안만) → 그래도면 `bOverride_AutoExposureMethod = true, AEM_Manual`(런북에 화면 차이 기록) | §4 EV | |
| 11 | 월드 `FTimerManager`(포털 Debounce/Unload/Preload, zone Evaluate)가 게임 정지에 멈추는지 — 문서 언급 없음 [확인: 없음] → [미확인] | 엔진 동작 | 설계 무의존(빙의 안 함 + 캐릭터 정지 → 오버랩 변화 없음); 관찰만 | §7 30 s 대기·10 s 대기 | |
| 12 | `UGameViewportClient::SetSuppressTransitionMessage(bool)` / `bSuppressTransitionMessage` 멤버로 정지 "PAUSED" 전환 메시지 억제(`DrawTransition`) [2차 M5] — 페이지 본문 없음 [미확인]; 고해상도 재렌더에 그 메시지·`stat`·온스크린 메시지가 포함되는지 [미확인] | 존재·시그니처·포함 여부 | 줄 삭제 후 관찰; 메시지가 사진에 남으면 `PauseMode=TimeDilation` | §2 정지 화면, §5 PNG 중앙 | 수정(f5c8861): `bSuppressTransitionMessage` protected·getter 없음(C2248) → `UGolmokGameViewportClient::IsTransitionMessageSuppressed()` + `DefaultEngine.ini` `GameViewportClientClassName`; 쓰기는 `SetSuppressTransitionMessage`. 사진 포함 여부(§5)는 미확인 |
| 13 | `FViewport::TakeHighResScreenShot()`(`bool` [확인 문서])이 정지 중에도 다음 `Draw`에서 처리·파일 기록 [2차; V-03은 비정지]; 3x에서 false 반환 가능("too big for the GPU") [확인 문구]; `AGolmokHUD::DrawHUD`가 재렌더 프레임에도 호출됨 [확인 V-03 HUD 포함]; `Shoot()`의 상태 변경이 같은 프레임 `Draw` 전 [2차] | 정지 중 동작·순서 | 안 찍히면 요청 틱만 1프레임 언포즈(`SetGamePaused(false)` → 요청 → 다음 틱 `true`); false면 1x 재시도·메타 실효값(설계); 순서가 틀리면 `PreCaptureFrames ≥ 1`이 흡수 | §5 파일 생성·HUD 없음, §6 3x | |
| 14 | 고해상도 PNG 쓰기가 비동기(`FImageWriteQueue`) → 수백 ms 뒤 등장 [2차]; PNG 존재 폴링(`IFileManager::FileExists`)으로 숨김 해제 | 시점 | 실시간 3 s 타임아웃이 최종 방어(설계); `-nullrhi`는 타임아웃 경로 | 자동화 MetaJson·§5 로그 대기 시간 | |
| 15 | `FCoreDelegates::OnEndFrame`가 정지 중에도 발화 [2차; `-nullrhi` 발화는 V-03 확인] | — | 실시간 타임아웃 + 폰 틱 카운터(정지 틱)로 이중화 | 자동화 MetaJson | |
| 16 | `AActor::SetActorLocation(P, /*bSweep*/ true, &Hit)`가 `USphereComponent` 루트(QueryOnly, WorldDynamic)로 벽에서 멈춤; `FHitResult::bStartPenetrating`; `UWorld::OverlapBlockingTestByChannel(Pos, Quat, ECC_WorldDynamic, FCollisionShape::MakeSphere(r), Params)`; Chaos 삼각형 메시 뒷면 스윕 [미확인] | 스윕 적용·뒷면 | `World->SweepSingleByChannel(Hit, From, To, FQuat::Identity, ECC_WorldDynamic, MakeSphere(r), Params)` 후 `SetActorLocation(Hit.Location, false)`; 뒷면은 설계 무의존 | 자동화 Clamp (c) + §7 벽 | |
| 17 | 빙의 안 한 `APawn`을 `SetViewTargetWithBlend(Pawn, 0)` → `APawn::CalcCamera`가 카메라 컴포넌트 사용(`bFindCameraComponentWhenViewTarget` 기본 true) [2차]; `GetViewTarget/SetControlRotation/GetControlRotation` [확인 V-03] | 비빙의 뷰 타깃의 카메라 컴포넌트 사용 | `AActor::CalcCamera` override로 카메라 컴포넌트 값 직접 반환 | EnterExit `GetViewTarget()` + §2 화면 | |
| 18 | `APlayerCameraManager::GetCameraLocation/GetCameraRotation` [확인 코드 사용 중] · `GetFOVAngle()` [2차] | FOV getter 이름 | `PC->GetPlayerViewPoint(Loc, Rot)` + `Cam->GetCameraCacheView().FOV`; 실패 시 80 | EnterExit FOV 단언 | |
| 19 | `EKeys::` 이름: `P H O R Z C N M E Q Enter LeftBracket RightBracket Hyphen Equals Comma Period MouseWheelAxis Gamepad_Special_Left/Right Gamepad_DPad_* Gamepad_LeftShoulder/RightShoulder Gamepad_FaceButton_* Gamepad_RightThumbstick` [확인 EKeys 페이지]; `Gamepad_LeftTriggerAxis` [확인 J-product F7]·`Gamepad_RightTriggerAxis` [2차]; 휠 Axis1D 값이 노치당 ±1·`Triggered` 1프레임 [2차]; 트리거 축 0..1 + `UInputModifierNegate` [2차] | 축 이름·값 의미 | 오류난 이름만 `InputCoreTypes.h` grep; 휠은 부호만 사용(설계); 트리거는 `Gamepad_LeftTrigger/RightTrigger`(버튼) Bool 두 액션으로 | 빌드 + §3 휠 1노치 = 5°·LT/RT | |
| 20 | `Gamepad_Special_Left`·P가 PIE에서 에디터에 가로채이지 않음; Esc = PIE 종료 | [2차] | 게임패드 토글을 `Gamepad_Special_Right`로 교체(코드 상수) | §2 | |
| 21 | 캐릭터 `SetActorHiddenInGame(true)`가 그림자까지 제거 | [2차] | 메시 `SetCastShadow(false)` 병행·복원 | §4 H 후 그림자 | |
| 22 | `UPROPERTY(Transient) TArray<TObjectPtr<UInputAction>>`(GC 보관) | 리플렉션 가능 [2차] | 액션별 멤버 21개(한 줄에 하나 — UHT는 콤마 다중 선언 거부) | UHT/빌드 | |
| 23 | `UGameplayStatics::SetGlobalTimeDilation/GetGlobalTimeDilation`, `AWorldSettings::MinGlobalTimeDilation`(0.0001), `AActor::CustomTimeDilation`(폴백 경로만) | [2차] | `World->GetWorldSettings()->SetTimeDilation`; 하한 위반이면 `MinGlobalTimeDilation` 값으로 | `PauseMode=TimeDilation`일 때만 | |
| 24 | `FDateTime::UtcNow().ToString(TEXT("%Y-%m-%dT%H:%M:%SZ"))`·`Now().ToString(TEXT("%Y%m%d_%H%M%S"))` [확인 V-03 경로 JSON·스크린샷] | — | — | 메타 `time_utc` | |
| 25 | `UWorld::bIsTearingDown`·`DoesSupportWorldType` [확인 V-03]; `EEndPlayReason::Destroyed/EndPlayInEditor/Quit/LevelTransition/RemovedFromWorld` [2차 이름] | enum 값 이름 | 오류 메시지대로 | 빌드 + §11 PIE 종료 | |
| 26 | 자동화 latent 명령이 PIE 정지 중에도 매 엔진 프레임 `Update()` | [2차] | 테스트 타이밍 전부 `FPlatformTime`(설계) | 자동화 EnterExit | |
| 27 | `TActorIterator`는 쓰지 않음; `UGolmokZoneSubsystem::FindLoadedZoneAt` 안에서 `TWeakObjectPtr<AGolmokZone>::Get()`(non-const)로 `FootprintContains`(non-const) 호출 [확인 자체 코드] | const 메서드 안 호출 규칙 | 레코드 순회를 non-const 헬퍼로 | 빌드 | |
| 28 | `UGolmokGeoSubsystem::LevelUEToLonLat(const FVector&, double& Lat, double& Lon, double& H)`·`HasOrigin()` [확인 자체 코드, 인자 순서 Lat·Lon] | — | — | 메타 lon/lat 대조 | |
| 29 | `AGolmokTimeOfDay::CaptureState(FGolmokLightingState&)`·`DefaultAutoExposureBias()`·`IsTransitioning()`·`GetTransitionAlpha()` [확인 자체 코드]; 새 `ShiftTransitionStart`는 `TransitionStart`(private double)만 옮김 | — | — | EnterExit 드리프트 단언 | |
| 30 | MSVC C4458: 서브시스템 멤버 `Values/Config/State`·폰 `Look/RollDeg` vs 인자·**로컬 변수**; 멤버 함수 `StepParam`과 `GolmokPhotoMath::` 자유 함수 이름 충돌 | pytest 정적 검사(인자 `In*`/`Out*`, 로컬 `New*`/`Local*`, 한정 호출) | 이름 변경 | 빌드 | |
| 31 | `UCanvas::SizeX/SizeY`로 왼쪽 아래 배치(`DrawHUD`에서 `Canvas` 유효 [확인 V-03]) | [2차] | `Canvas->ClipX/ClipY` | §2 오버레이 위치 | |
| 32 | 유니티 빌드: `Photo/*.cpp` 익명 namespace(`PhotoSubsystemFor`, `PhotoParseToggle`, `CmdPhoto*`)·명명 `GolmokPhotoJson` | Debug의 `ParseToggle`·`DebugSubsystemFor`, Lighting의 `GolmokLightingJson`과 충돌 금지 | 접두 유지(pytest) | 빌드 | |
| 33 | photo.json 파싱 `TryGetField(FStringView)`·`AsNumber/AsString/AsArray/AsObject/AsBool`, 키 열거 `FString(*Pair.Key)` [확인 V-03] | — | — | MetaJson 파서 케이스 | |
| 34 | `FActorSpawnParameters{ObjectFlags \| RF_Transient, SpawnCollisionHandlingOverride = AlwaysSpawn}` [확인 V-03 포털·재생 폰] | — | — | — | |
| 35+ | (PC 세션 추가) | | | | |
| 36 | `Debug/GolmokDebugSubsystem.cpp:1077-1085` — `View->TakeHighResScreenShot()`가 false를 반환한 뒤 **같은 프레임**에 `FHighResScreenshotConfig::SetResolution(…, 1.f)` + `SetFilename` 재설정 후 `TakeHighResScreenShot()` 재호출 | false 반환 뒤 config 내부 상태(더티 플래그·요청 큐)가 남아 두 번째 호출이 받아들여지는지, 또는 첫 요청이 부분적으로 등록돼 다음 Draw에 3x가 시도되는지 [미확인] | 재시도를 다음 틱(`OnEndFrame`)으로 미루거나, false면 그 샷을 거부하고 메타에 `multiplier: 실효값`만 기록 | 런북 §6 3x → false 로그와 1x PNG 실제 생성 여부 | |
| 37 | `Photo/GolmokPhotoCameraPawn.cpp` `ApplyLook` — `SetActorRotation(Look, ETeleportType::TeleportPhysics)` 2-인자 오버로드 | 기존 모듈은 `SetActorRotation(FRotator)`·`SetActorLocationAndRotation(…, ETeleportType)`만 사용. `AActor::SetActorRotation(FRotator, ETeleportType = None)` 존재는 가설 | `SetActorRotation(Look)`(폰은 물리 없음) 또는 `SetActorLocationAndRotation(GetActorLocation(), Look, false, nullptr, TeleportPhysics)`[기존 코드 확인] | 빌드 | |
| 38 | `Photo/GolmokPhotoCameraPawn.h` 멤버 선언부 — 폰 멤버 `TWeakObjectPtr<UGolmokPhotoModeSubsystem> Owner`(UPROPERTY 아님)가 `AActor::Owner`(private UPROPERTY)를 가림 | UHT는 UPROPERTY가 아니므로 통과할 가능성이 크지만, `GetOwner()`와 의미 충돌·MSVC 경고(C4458은 로컬/인자 전용이라 해당 없음; 멤버 은닉 경고 없음)는 [미확인] | `PhotoOwner`로 개명(코드 4곳 + 주석) | 빌드 | |
| 39 | `Photo/GolmokPhotoCameraPawn.cpp` `Tick`(`Look.Vector()`), `Tests/GolmokPhotoTest.cpp:578` — `FRotator::Vector()` | 모듈 최초 사용(`NormalizeAxis`·`RotateVector`는 `GolmokCharacterTest.cpp`에 기존). 존재·정규화 방향 벡터 반환은 [2차] | `FRotationMatrix(Look).GetUnitAxis(EAxis::X)` | 빌드 + Clamp 테스트 (d) 방향 | |
| 40 | `Photo/GolmokPhotoCameraPawn.cpp` `MoveConstrained` — `Hit.bStartPenetrating`이면 `SetActorLocation(Location + Retreat, /*bSweep*/ true)`로 10 cm 후퇴 | 관통 시작 상태에서의 스윕 이동은 엔진이 0-거리 블로킹으로 **이동을 거부**할 수 있음(캐릭터 무브먼트만 관통 해소를 함) → 후퇴가 실행되지 않고 매 틱 반복 [미확인]. §10 #16은 `bStartPenetrating` 존재만 다룸 | 후퇴는 `bSweep=false` 텔레포트로(앵커 쪽은 자유 공간이라 안전), 또는 `Hit.PenetrationDepth * Hit.Normal`로 밀어내기 | 런북 §7 벽 밀착 후 이동 가능 여부; 자동화 Clamp (c) | |
| 41 | `Photo/GolmokPhotoModeSubsystem.cpp` 파일 머리 include·`Enter()`(`FCollisionQueryParams QueryParams(FName(TEXT("GolmokPhotoEnter")), …)`) — `#include "CollisionQueryParams.h"`·`"CollisionShape.h"` + `FCollisionQueryParams(FName, bool bTraceComplex)` 생성자 | 두 헤더 경로(`Engine/Public/` 직하)와 생성자 인자 순서는 [2차]; 모듈 최초 사용 | `Engine/World.h`가 이미 끌어오므로 두 include 삭제; 생성자는 `FCollisionQueryParams Params; Params.TraceTag = …` | 빌드 | |
| 42 | `Photo/GolmokPhotoModeSubsystem.cpp` `CmdPhotoSet`(익명 namespace) — `FString::IsNumeric()`, `FCString::Atod`, `FCString::Atoi` | 모듈은 `FCString::Atof`만 사용해 왔음. `Atod`(double) 존재·`IsNumeric`이 `-1.5` 같은 부호·소수를 true로 보는지 [2차] | `FCString::Atof` + `static_cast<double>`; 검증은 `LexTryParseString<double>` | 빌드 + `golmok.photo.set ev abc` 거부 메시지 | |
| 43 | `Photo/GolmokPhotoModeSubsystem.cpp` `Enter()`(`DescribePathState().ParseIntoArrayWS(Parts)`) — `FString::ParseIntoArrayWS(TArray<FString>&)` 기본 인자 | 모듈은 `ParseIntoArray`·`ParseIntoArrayLines`만 사용. `ParseIntoArrayWS`의 기본 `pchExtraDelim=nullptr, InCullEmpty=true` [2차]; `DescribePathState()` 문자열 형식 의존 | `ParseIntoArray(Parts, TEXT(" "), /*bCullEmpty*/ true)` | 빌드 + EnterExit "path plays → Enter 거부" 단언 | |
| 44 | `Photo/GolmokPhotoModeSubsystem.cpp` `BuildMeta` — 메타 회전에 `Camera->GetComponentRotation()`(카메라 컴포넌트 월드 회전) | 모듈 최초 사용. `bUsePawnControlRotation=false`·상대 회전 0이므로 폰 회전과 같아야 하나, 롤 적용 후 컴포넌트 월드 회전이 `Look`과 동일한지(짐벌·정규화 차이) [2차] | `PhotoPawn->GetActorRotation()`으로 통일(이미 폴백) | 자동화 MetaJson 회전 값 vs 로그; 런북 §5 메타 yaw/pitch/roll | |
| 45 | `Photo/GolmokPhotoModeSubsystem.cpp` `Enter()` 첫 검사 — `World->WorldType == EWorldType::Game \|\| … PIE` 멤버 직접 읽기 | 기존 모듈은 `DoesSupportWorldType(EWorldType::Type)` 인자만 비교. `UWorld::WorldType`이 public `TEnumAsByte<EWorldType::Type>`인지 [2차] | `World->IsGameWorld()` | 빌드 | |
| 46 | `Tests/GolmokPhotoTest.cpp:1082-1106` — `FJsonObject::SetNumberField/SetStringField/SetBoolField/SetArrayField/GetObjectField(TEXT("…"))`에 TCHAR 리터럴 | V-03에서 확인된 것은 `TryGetField(FStringView)`·`FString(*Pair.Key)`뿐. 5.8 `UE::FSharedString` 키에서 Set*/GetObjectField의 인자형(`FStringView`? `const FString&`?)과 TCHAR* 암시 변환·모호성 [미확인] | 오류 시 `FString(TEXT(…))` 또는 `FStringView(TEXT(…))`로 감싸기; 실패한 오버로드만 오류 메시지대로 | 빌드 (MetaJson/ParseConfig 테스트) | |
| 47 | `Tests/GolmokPhotoTest.cpp:584-593` — 맨 `AActor` 스폰 → `NewObject<UBoxComponent>` → `SetMobility/SetBoxExtent/SetCollisionProfileName(BlockAll)` → `SetRootComponent` → `RegisterComponent` → `SetActorLocationAndRotation` | 기존 `GolmokZone.cpp`는 자기 액터 안에서 컴포넌트를 만듦; 루트 없는 `AActor` 스폰의 위치가 유지되는지, `RegisterComponent` 전 프로파일 설정이 물리 상태에 반영되는지, `WorldDynamic` 구 스윕이 이 박스를 Block 하는지 [2차] | 스폰 시 `AStaticMeshActor` 대신 프로파일을 `RegisterComponent` 뒤 `SetCollisionProfileName` 재호출·`UpdateBounds`; 최후 (d) 단언을 `AddInfo`로 강등 금지 → 스폰 지점을 폰 앞 50 cm로 좁힘 | 자동화 Clamp (d) | |
| 48 | `Tests/GolmokPhotoTest.cpp:538,586` — `if (Test->TestNotNull(…))` bool 반환 사용; `TestEqual(*FString::Printf(…), Keys[i], FString(…))`(`const TCHAR*` 설명 + `FString,FString`), `TestEqual(TEXT(…), Num(), 4)`(int32,int32) | 기존 모듈은 `TestNotNull`을 표현식으로 쓰지 않음; `FAutomationTestBase::TestNotNull`이 bool을 반환하는지, `TestEqual(const TCHAR*, const FString&, const FString&)`·`(const TCHAR*, int32, int32)` 오버로드 해석(`Num()`은 int32, 리터럴 int) [2차] | `TestNotNull` 뒤 별도 `if (!Pawn) return;`; 모호하면 `static_cast<int32>` | 빌드 | |
| 49 | `Tests/GolmokPhotoTest.cpp:562-568` — L_Dev 바닥 가정: `-500 z` 이동 시 구 스윕이 바닥(캐릭터 발 = 캡슐 반높이 아래)에서 멈춰 `Z >= FloorZ - R - 20` | L_Dev 바닥 액터의 충돌(WorldStatic Block)·위치가 캐릭터 발과 일치한다는 가정 [미확인]; 구 제약(반경) 또는 footprint가 먼저 걸리면 바닥과 무관하게 통과할 수 있음 | 바닥 판정을 `Debug` 로그 + 완화 단언(구 내부)으로 이원화; 런북에서 시각 확인 | 자동화 Clamp (b) + 런북 §7 바닥 | |
| 50 | `Tests/GolmokPhotoTest.cpp:329-339` — `Tod->TransitionSeconds = 0.5f; Tod->ApplyPreset(TEXT("clear_noon"))`이 `IsTransitioning()` true로 시작한다는 가정(드리프트 단언 선행 조건) | 현재 프리셋이 이미 `clear_noon`이거나 `ApplyPreset`이 즉시 스냅(전환 0)하면 skip 경로(AddInfo)로 빠져 `ShiftTransitionStart` 단언이 실행되지 않음 [확인 자체 코드: skip 처리됨]; `TransitionSeconds`가 public UPROPERTY로 쓰기 가능한지 [2차] | 다른 프리셋(`overcast_morning`)으로 먼저 옮긴 뒤 `clear_noon`; 멤버가 private면 `SetTransitionSeconds` 추가 | 자동화 EnterExit 로그에 "drift assertion skipped"가 없어야 함 | |
| 51 | `Tests/GolmokPhotoTest.cpp:1050` — `GetDefault<UGolmokPhotoModeSubsystem>()->ResolveConfigPath()`(월드 서브시스템 CDO의 const 메서드 호출) | `UWorldSubsystem` CDO에 월드 없이 접근·`ResolveConfigPath() const`가 멤버 상태에 의존하지 않는지 [확인 자체 코드: const]; CDO 생성 여부는 [2차] | `static FString ResolveConfigPathStatic()` 또는 `UGolmokPhotoModeSubsystem::Get(World)->ResolveConfigPath()` | 빌드 + ParseConfig 테스트 | |
| 52 | `Photo/GolmokPhotoModeSubsystem.cpp` `OnFovWheel`·`OnUpDown` — `FInputActionValue::Get<float>()`(Axis1D: 휠·상하) | 모듈은 `Get<FVector2D>()`만 사용. Axis1D 액션에 `Get<float>()` 템플릿 특수화가 있는지, Bool 액션에서 호출하면 체크 실패인지 [2차] | `Value.GetMagnitude()` | 빌드 + 런북 §3 휠·E/Q | |
| 53 | `Photo/GolmokPhotoCameraPawn.cpp` 파일 머리 include·`ApplyOptics` — `#include "Engine/Scene.h"` + `UCameraComponent::PostProcessSettings`(public `FPostProcessSettings`) 직접 쓰기 | 필드명은 §10 #9; 멤버가 public이며 `CameraComponent.h`만으로 완전한 타입이 되는지, `Engine/Scene.h` 경로 [2차] | `Camera->PostProcessSettings`가 안 되면 `Camera->PostProcessBlendWeight`+`FPostProcessSettings` 로컬 후 대입; include는 `CameraComponent.h`가 끌어오면 삭제 | 빌드 | |
| 54 | `Tests/GolmokPhotoTest.cpp:563` — `UCapsuleComponent::GetScaledCapsuleHalfHeight()`(`Components/CapsuleComponent.h`) | 모듈 최초 사용; 이름·스케일 포함 의미 [2차] | `GetUnscaledCapsuleHalfHeight()` 또는 상수 92 | 빌드 | |
| 55 | `Photo/GolmokPhotoModeSubsystem.cpp` `AddPhotoContext(bool)` — 서브시스템이 `AddMappingContext(PhotoContext, 3)`/`RemoveMappingContext(PhotoContext)`를 **PC 소유 `AGolmokPlayerController::AddMappingContext()`와 별개로** 호출하고, PC는 `SetDebugKeysSuspended`로 디버그 컨텍스트만 제거·복귀 | 두 소유자가 같은 `UEnhancedInputLocalPlayerSubsystem`의 컨텍스트 스택을 번갈아 바꿀 때 재빙의(`OnPossess` → `AddMappingContext()` 재호출)가 포토 컨텍스트를 덮거나 우선순위를 재정렬하지 않는지 [2차]; §10 #6은 오버로드만 다룸 | 재빙의는 포토 중 거부(이미 `StartPlayback` 거부); 그래도 흔들리면 PC의 `AddMappingContext()`가 `Photo->IsActive()`일 때 포토 컨텍스트를 재추가 | 런북 §3 정지 중 F키 무반응·P 종료 후 F1 복귀 | |
| 56 | (적대 검증 STATE-2, 확인 불가) 정지 중 `APlayerController::PlayerTick` → `TickPlayerInput(dt, dt == 0)` 경로 — 엔진 소스를 기억으로 옮긴 것이고 출처 없음 [미확인 가설] | 이 경로가 사실이라도 캐릭터 `IMC_Default` 액션이 정지 중 발화할 수 있는지는 #5와 같은 문제. 포토 IMC(우선순위 3, 모든 액션 `bConsumeInput = true`)가 같은 키를 덮으므로 코드 변경 없음 | #5 대안: `AGolmokCharacter`에 `RemoveMappingContextForPhoto()` public 추가 | §3 포토 중 WASD·마우스·Space·Shift → P로 나간 뒤 캐릭터 위치·회전 불변(#5와 같은 확인) | |
| 57+ | (PC 세션 추가 — 예: `FHighResScreenshotConfig::SetResolution/SetFilename` 시그니처, `UInputModifierNegate::bX/bY/bZ`, `FEnhancedActionKeyMapping::Modifiers`, `IConsoleManager::ProcessUserConsoleInput(…, *GLog, World)`, `FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM`) | | | | |

## 13. 결과 기록
V-09 PC 세션(… , 사용자 PC, 모델 …), 날짜 …. UE 5.8.3, VS …, GPU …(VRAM … GB), 뷰포트 해상도 …, 브랜치 `pc/v09-verify-wp12`.
**검증 방식**: (에디터 Python PIE 드라이버 여부, 키 입력 방식 — 사람 손 / Win32 `SendInput`, 게임패드 유무, 헤드리스 명령을 적는다.)

| 항목 | 결과 | 메모·실측 |
|---|---|---|
| 빌드 | | 컴파일 오류·링크 오류 건수, §12 번호, 커밋 |
| 헤드리스 자동화 22개(Photo 3 + 기존 19) | | `[Info]` 실측(EnterExit fov·틱 수, Clamp 좌표, MetaJson `capture window closed after`), skip Info 유무 |
| §2 진입/복원(로그 두 줄·오버레이·PAUSED 없음·사전 정지·전환 드리프트) | | `tod shift` 값(월드 시계 정지 여부), 사전 정지에서 P 동작 |
| §3 정지 중 입력·틱·카메라(부드러움·휠·캐릭터 불변·F키 무반응·복귀) | | `PauseMode` 최종값(`GamePause`여야 함), 게임패드 표 |
| §4 조절·화질(EV 즉시 반영·EV 0 밝기·DOF off·그림자·콘솔 set) | | TSR/Lumen 관찰, `IsNumeric` 부호·소수 |
| §5 촬영(3줄 로그·PNG에 HUD/오버레이/PAUSED 없음·메타 15키·`_2`·deferred exit) | | `present after` s, `PreCaptureFrames=0` 결과 |
| §6 배율 표 | | 표 3행, 3x 판정, `MaxMultiplier` 커밋 여부 |
| §7 제약(벽·구·바닥·footprint·no zone·포털 타이머) | | 밀착 후 이동 가능 여부(#40), 타이머 정지 여부(#11) |
| §8 실내 | | 메타 `zone_id`, 벽 밖 노출 여부 |
| §9 경로 재생 배제 | | |
| §10 패키징(선택) | | pak 목록, `config loaded` 경로 |
| §11 PIE 종료 | | `teardown` 1회, 잔류 액터·dirty 없음, 고아 JSON |
| 고친 API 번호(§12)·커밋 | | |
| 설계와 다른 동작 발견 | | 이 문서에 없는 추가분 |
| STATUS | `🟡 → 🟢` | |

스크린샷 4장(JPG 축소, `docs/runbooks/` 옆; PNG 원본·JSON은 커밋하지 않는다):
- ① 포토 모드 화면(오버레이 5줄 보임, `L_ZoneTest` 001 안): `docs/runbooks/pc-verify-wp12-photo.jpg` — (자리)
- ② 찍힌 2x PNG 축소본(오버레이·HUD 없음): `docs/runbooks/pc-verify-wp12-png.jpg` — (자리)
- ③ 벽 15 cm 앞 또는 구 표면(`3.3 / 3.3 m` — 유효 반경, §7)에서 멈춘 장면: `docs/runbooks/pc-verify-wp12-clamp.jpg` — (자리)
- ④ 실내 촬영(오버레이 `z_synthetic_001_interior v1`): `docs/runbooks/pc-verify-wp12-interior.jpg` — (자리)

무인 검증: 에디터 Python PIE 드라이버 + `unreal.SystemLibrary.quit_editor()`; 값·배율·촬영은 `golmok.photo.set`·`golmok.photo.shoot` 콘솔로, 키 발화(P·WASD·휠·패드)만 사람이. 백그라운드 에디터 창은 뷰포트를 렌더하지 않는다(V-03) — 촬영 항목은 창을 전면에 둔 상태에서만.

기록 뒤:
1. 이 표를 채우고 커밋(`WP-12: PC 검증 결과`). §3·§5·§6에서 바꾼 `PauseMode`·`PreCaptureFrames`·`MaxMultiplier`는 확정값만 남기고(`git diff unreal/Golmok/Config/DefaultGame.ini`가 의도한 줄만), 바꾼 이유를 §13 표에 적는다.
2. `docs/plan/STATUS.md`: WP-12 행을 🟡 → 🟢(또는 🔴 + 막힌 항목), V-09 행 갱신, 세션 로그 표에 한 줄(날짜·PC 세션·모델·"V-09 WP-12 검증"·결과). 고친 API·설계 변경은 인계 메모에 번호(§12)와 커밋 해시로.
3. `docs/plan/WP-12-photo-mode.md` "결과"에 PC 검증 한 줄(통과/수정 건수, 확정한 `PauseMode`·`MaxMultiplier`·`PreCaptureFrames`), `docs/ROADMAP.md` 게임 기능(D-013) 진행 표시.
