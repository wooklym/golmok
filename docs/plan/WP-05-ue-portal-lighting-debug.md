# WP-05 — UE C++ 런타임 2: 포털·조명·디버그

상태: 🟡 코드 완료·PC 검증 대기 (2026-09-25, session_01W4S1qYJPhQaziYbJMvAXMo) · 담당: 클라우드 Claude 세션(**Fable 5.1 ultracode**, 모델 정책 DEVELOPMENT-PLAN §7.4) · 의존: WP-04 · 검증: **G2(`runbooks/pc-verify-wp05.md`)**

## 목표
(1) 실외↔실내 전환(포털·레벨 스트리밍·노출 전환), (2) 시간대 조명 런타임 전환, (3) 스파이크·회귀 측정용 디버그 도구(충돌 와이어프레임, 성능 HUD, 카메라 경로 녹화·재생)를 C++로 만든다. ROADMAP 1.3 "조명 프리셋·디버그", 1.5 "문 포털·전환".

## 배경
- WP-04의 `UGolmokZoneSubsystem`, `AGolmokZone`, manifest `portals[]`
- `Content/Python/golmok/lighting.py`의 프리셋 값(현재 Python에만 있음)
- `research/08` 측정 절차(고정 시점, 60초 경로, `CsvProfile Start/Stop`, `golmok-perf`)
- `GolmokCharacter.cpp`의 Enhanced Input 런타임 생성 방식(같은 방식으로 디버그 키 매핑)

## 산출물
1. **조명 프리셋 단일 소스**: `unreal/Golmok/Config/Golmok/lighting_presets.json`(현재 `lighting.py`의 4개 프리셋 + `interior` 프리셋: 노출 바이어스, 안개 0). `lighting.py`는 이 JSON을 읽도록 수정(값 중복 제거). 
2. `Lighting/GolmokTimeOfDay.h/.cpp` — `AGolmokTimeOfDay` 액터(레벨당 1개): `DirectionalLight/SkyLight/ExponentialHeightFog/PostProcessVolume`을 찾고(태그 또는 첫 번째), `ApplyPreset(FName)`을 `TransitionSeconds`(Config, 기본 2초) 동안 보간. 콘솔 `golmok.tod <preset>|next`. 키: 숫자 1~4 프리셋, F5 순환(플레이어 컨트롤러에서 매핑).
3. `Portals/GolmokPortal.h/.cpp` — `AGolmokPortal`: 박스 트리거, `TargetZoneId`, `PortalId`, `bIsEntry`. 오버랩 시 `UGolmokZoneSubsystem`에 대상 Zone 로드 요청 + 실내 서브레벨 스트리밍(`ULevelStreamingDynamic::LoadLevelInstance` 또는 레벨에 등록된 `ULevelStreaming`을 이름으로 찾아 `SetShouldBeLoaded/Visible`; 두 방식 중 하나를 고르고 이유를 적는다) + 노출·안개 전환(`ApplyPreset("interior")` / 이전 프리셋 복귀). 문 애니메이션은 없음(문은 열린 상태로 촬영, 가이드 #2). 반경 안에서만 실내 로드(ARCHITECTURE §4-5). WP-04 Zone 로더가 `portals[]`를 읽어 포털 액터를 자동 스폰하는 함수 `AGolmokZone::SpawnPortals()` 추가.
4. `Debug/GolmokDebugSubsystem.h/.cpp` — `UGolmokDebugSubsystem : UWorldSubsystem` + 콘솔 명령:
   - `golmok.hud 0|1`: 화면 좌상단에 fps 평균·1% low(최근 2초 링버퍼), Game/Render/GPU ms(`FApp::GetDeltaTime`, `GGameThreadTime`, `GRenderThreadTime`, `RHIGetGPUFrameCycles` 등 5.x에서 접근 가능한 것), 현재 Zone 목록·로드 상태, 현재 조명 프리셋, 플레이어 ENU 좌표(GeoSubsystem). `AHUD` 서브클래스 `AGolmokHUD`에 그리기(`DrawText`), 게임모드 `HUDClass` 설정.
   - `golmok.collision 0|1`: 충돌 표시(`GetWorld()->Exec(World, TEXT("show collision"))`가 PIE에서 동작하는지 불확실하므로, 대안으로 Zone 충돌 컴포넌트의 `SetHiddenInGame(false)`+와이어프레임 머티리얼 토글을 기본 구현).
   - `golmok.path record <name>` / `stop` / `play <name> [--csv]`: 플레이어 카메라 위치·회전을 10Hz로 `Saved/Golmok/Paths/<name>.json`에 기록, 재생 시 스펙테이터 폰(또는 카메라 액터)을 보간 이동. `--csv`면 재생 시작·끝에 `CsvProfile Start`/`Stop` 실행(Exec)하여 `golmok-perf` 입력 생성. 재생 중 HUD에 진행률.
   - `golmok.screenshot <tag>`: `HighResShot 2` + 파일명 태그(viewpoints.py와 같은 폴더 규약 `Saved/Screenshots/Golmok/<tag>/`).
5. `Player/GolmokPlayerController.h/.cpp` — `AGolmokPlayerController`: 디버그·조명 키를 Enhanced Input으로 런타임 생성(F1 HUD, F2 충돌, 1~4/F5 조명, F9 녹화 토글, F10 재생). `GolmokGameMode`에 `PlayerControllerClass`, `HUDClass` 설정.
6. 런북 `docs/runbooks/pc-verify-wp05.md`: 빌드 → PIE → 각 키·콘솔 명령 확인 체크리스트, 합성 실내 서브레벨(간단히 `synthetic_zone.py`에 `interior=True` 옵션 추가해 큐브 방 하나와 포털 생성) → 포털 왕복 시 노출 전환 확인, path 녹화·재생·CSV → `golmok-perf` 요약 출력.

## 완료 기준
- 파일 완비, WP-04와 같은 코드 리뷰 체크리스트 수행·기록.
- `lighting.py`가 JSON을 읽고, `tools/tests/test_lighting_presets.py`가 JSON 스키마(필수 키·범위)를 검사.
- CI 초록, STATUS `🟡`.

## 주의
- 레벨 스트리밍 API는 버전별 차이가 있다. 두 경로를 모두 코드에 두고 Config 플래그로 고르게 하면 PC 검증에서 빨리 우회할 수 있다.
- HUD 통계 접근 API가 불확실하면 `GAverageFPS`/`GAverageMS`(전역, 오래됨)와 `FPlatformTime::Seconds()` 기반 자체 계측으로 시작한다.

## 설계 (확정, 2026-09-25)

근거: 이 문서 산출물 1~6·주의, DEVELOPMENT-PLAN §7.5, WP-04 "설계(확정)" §0~§6·"결과"(WP-05에 알릴 것, `Evaluate()` 포인터 주의), `docs/spec/zone-manifest.md` §5(실내 서브레벨 경로), ARCHITECTURE §4-5(반경 안에서만 실내 로드), `runbooks/pc-verify-wp04.md` §6(불확실 API 표 형식), 기존 코드(`GolmokCharacter`, `GolmokZone`, `GolmokZoneSubsystem`, `GolmokGeoSubsystem`, `lighting.py`, `viewpoints.py`, `synthetic_zone.py`, `perf_report.py`, `test_ue_*`), `research/08`. 세 후보 설계(스펙 충실·안정성·성능)를 두 심판이 채점해(스펙안 33/32, 안정안 32/33, 성능안 31/31) **스펙 충실안을 기준으로 안정안의 API 최소화·성능안의 재생 폰·오버레이 집합을 이식**하고, 두 심판이 지적한 결함 33건을 전부 닫았다. 선택지는 남기지 않았다(레벨 스트리밍은 기본 경로를 골랐고 다른 경로는 Config 값으로만 남는다).

### 0. 확정 결정 요약
| 주제 | 결정 |
|---|---|
| 프리셋 단일 소스 | `Config/Golmok/lighting_presets.json`(`schema_version` 1, `cycle` 4개, `presets` 5개). 키 이름은 현재 `lighting.py`와 **동일**(`pitch yaw lux kelvin sky fog fog_height_falloff volumetric exposure_bias`). C++·Python 모두 이 파일만 읽고 값 하드코딩 없음 |
| `interior` 프리셋 | **부분 프리셋** 4키(`fog=0`, `fog_height_falloff=0.2`, `volumetric=false`, `exposure_bias=1.0`), `cycle`에 없음. 런타임은 현재 base 프리셋 위에 **오버레이**(태양·하늘 유지). 에디터 `lighting.apply("interior")`도 있는 키만 적용 |
| `lighting.py` | 순수 파서 모듈 `golmok/lighting_presets.py`(`import unreal` 없음, 경로는 `__file__` 상대) + `lighting.py`는 re-export·`apply()`만. `PRESETS` dict 삭제 |
| `AGolmokTimeOfDay` | 레벨당 1개. 없으면 `AGolmokPlayerController::BeginPlay`가 `FindOrSpawn`(Transient). 대상은 태그 `GolmokLighting` 우선 → 클래스별 첫 액터(PPV는 unbound). 기본은 **레벨 조명 존중**(`InitialPreset=` 비움) |
| 보간 | **Tick, 전환 중에만 켬**(`bStartWithTickEnabled=false`, `SetActorTickEnabled`). 선형 α, 태양 회전 `FQuat::Slerp`, bool은 α≥0.5. 캐시를 흔드는 호출(`SetVisibility`, `SetVolumetricFog`, `RecaptureSky`)은 전환 시작/끝 1회 |
| 실내 오버라이드 | `EnterInterior(FName Source)`/`ExitInterior(FName Source)` **소스 집합**(Source = `PortalId`). 0→1이면 오버레이 전환, 1→0이면 base 복귀. 실내에서 `ApplyPreset(x)`는 base만 바꾸고 오버레이 유지. 포털 `EndPlay`가 자기 Source를 반드시 제거 → 고아 오버라이드 없음. `ApplyPreset/NextPreset/EnterInterior/ExitInterior`는 `UFUNCTION(BlueprintCallable)`(WP-06 Python) |
| 포털 클래스 | `AGolmokPortal : AActor`(**AGolmokZone 아님**, `RegisterZone` 호출 없음). 루트 `UBoxComponent`(반경×반경×`TriggerHeightCm/2`, `OverlapOnlyPawn`, QueryOnly). 문마다 **능동 트리거 1개**: `bIsEntry=true`(exterior가 스폰). interior manifest의 되돌아가는 포털(`bIsEntry=false`)은 **수동 마커**(오버랩 이벤트 없음, HUD·`golmok.collision`에만 표시) |
| 포털 반응 | 오버랩 핸들러는 즉시 아무것도 하지 않고 `DebounceSeconds=0.25` 타이머로 미룬다(Load 스택 재진입 차단 + 캡슐 떨림 디바운스). `BeginPlay` 직후 `Trigger->IsOverlappingActor(Pawn)` 검사로 스폰 시 이미 안에 있는 폰도 처리 |
| 문 통과 판정 | 오버랩 중에만 Tick: 포털 전방(`UE Yaw = -yaw_deg`의 +X) 내적 부호 + `CrossingHysteresisCm=10` + `MinCrossingIntervalSeconds=0.25`로 **문 평면 통과**를 판정해 조명 오버레이 on/off. 박스 이탈이 바깥쪽이면 `UnloadDelaySeconds=3` 뒤 언로드 |
| 레벨 스트리밍 | 둘 다 구현, `[/Script/Golmok.GolmokPortal] InteriorStreamingMode=LevelInstance\|NamedStreamingLevel`. **기본 `LevelInstance`**(`ULevelStreamingDynamic::LoadLevelInstance`, 항등 트랜스폼, 이름 오버라이드 `L_<id>_inst`). 같은 패키지의 기존 `ULevelStreaming`이 있으면 재사용(중복 인스턴스 0), 스트림 아웃은 같은 실내를 쓰는 다른 포털이 `Active/Leaving`이 아닐 때만. `NamedStreamingLevel`은 퍼시스턴트 레벨 Levels에 등록된 항목만 켜고 끈다(`LoadStreamLevel` 폴백 없음, 미등록이면 Error 메시지) |
| 서브레벨 경로·좌표 | 스펙 §5 `/Game/Golmok/Zones/<zone_id>/v<version>/L_<zone_id>`(version = `FindZone(to_zone)->Version`, 없으면 1). 서브레벨은 **레벨 좌표로 저작**(두 경로 모두 항등 트랜스폼). 쿠킹: `+DirectoriesToAlwaysCook=(Path="/Game/Golmok/Zones")` |
| `SpawnPortals()` | `bDeferConstruction` → `Configure()` → `FinishSpawning`. `Params.Name` 없음(라벨만 `#if WITH_EDITOR`). WP-04 `Evaluate()`·`RegisterZone`·로그 문자열 무변경 |
| 통계 샘플링 | `FCoreDelegates::OnEndFrame`(`OnWorldBeginPlay`에서 바인드, `Deinitialize`에서 해제). HUD가 꺼져 있어도 샘플은 쌓인다(`bSampleWhenHudHidden=True`; 프레임당 double 4개 push) → `golmok.stats`·`--csv` 재생·`-nullrhi` 자동화가 HUD 없이 값을 읽는다. 문자열 생성은 HUD 켜짐·0.25 s 간격만 |
| 통계 원천 | dt = `FApp::GetDeltaTime()`; Game/Render = `GGameThreadTime/GRenderThreadTime`(uint32 cycles); GPU = `RHIGetGPUFrameCycles()`(uint64) — 셋 다 순수 헤더 `CyclesToMs(uint64, FPlatformTime::GetSecondsPerCycle())`로 ms(uint32→uint64 암시 승격, 축소 없음). `#define GOLMOK_GPU_TIME_SOURCE 1` 스위치(0이면 GPU `n/a`) |
| 1% low 정의 | 창(`StatsWindowSeconds=2`) 안 프레임별 `fps_i = 1/dt_i`를 오름차순 정렬 → **numpy `linear` 1번째 백분위수**(`h=(N−1)·0.01`, `x[⌊h⌋]+(h−⌊h⌋)(x[⌈h⌉]−x[⌊h⌋])`). `golmok-perf`의 `np.percentile(fps, 1)`과 식이 같다. 평균 fps = `N/Σdt`(`perf_report.fps_avg`와 동일). 창 = 최신부터 누적 dt ≤ 창(첫 샘플 항상 포함) |
| 순수 헤더 | `Debug/GolmokStatsMath.h` 하나(`namespace GolmokStatsMath`): 링버퍼·통계·백분위수·`CyclesToMs`·고정소수 포매터/리더·경로 JSON 쓰기/읽기·보간. include는 `<cmath> <array> <cstddef> <vector> <cstdint> <algorithm> <string>`만, `<cstdio>`·`std::min/max`·`printf` 금지. g++ `-std=c++17 -Wall -Wextra -Werror -pedantic` 교차검증 |
| 경로 JSON | `{"version":1,"name","level","hz","created","samples":[{"t","p":[x,y,z],"r":[pitch,yaw,roll]}]}` cm·deg, 고정소수 `t` 3자리·`p` 2자리·`r` 3자리, 한 샘플 한 줄. Python 왕복 계약은 **`json.loads` 후 값 동일(1e-6)**(바이트 동일 아님) |
| 재생 | 전용 `AGolmokPathPawn : APawn`(루트 `USphereComponent` ObjectType Pawn·QueryOnly·WorldDynamic Overlap, `UCameraComponent`)을 스폰해 **빙의** + `SetViewTargetWithBlend(PathPawn, 0)` 명시 호출. 원 캐릭터는 제자리·숨김(충돌 유지). 끝나면 `Possess(SavedPawn)`·숨김 복원·폰 파괴. 포털 트리거가 재생 폰을 보므로 `--csv` 재생이 실내 로드·노출 전환까지 재현 |
| `--csv` | 재생 첫 틱 `GEngine->Exec(World, TEXT("CsvProfile Start"))`, 끝 `"CsvProfile Stop"` → `FPaths::ProfilingDir()/CSV`에서 최신 `Profile(*).csv`를 찾아 **`golmok-perf "<csv>" --label <name> --markdown` 명령을 로그** |
| 충돌 표시 | 셋 다: ① zone 충돌 메시 `SetHiddenInGame(false)` + `GEngine->WireframeMaterial`(1순위, 없으면 `CollisionDebugMaterialPath` 소프트 로드, 그것도 없으면 nullptr) + blocker·플레이스홀더 박스 unhide ② 포털 박스 unhide ③ `UGameViewportClient::EngineShowFlags.SetCollision(b)`(실패 시 `show collision` Exec). 새로 로드되는 zone은 `CollisionRefreshSeconds=1` 타이머가 재적용(WP-04 `Load()` 무변경) |
| 스크린샷 | `HighResShot <ScreenshotMultiplier> filename="<FPaths::ProjectSavedDir()/Screenshots/Golmok/<tag>/<preset>/<name>>"` — `viewpoints.py`와 **정확히 같은 트리**(`FPaths::ScreenShotDir()`는 플랫폼 폴더가 끼므로 쓰지 않음) |
| HUD | `AGolmokHUD : AHUD`, `DrawHUD`에서 `DrawRect`+`DrawText`(SmallFont). fps 두 줄은 매 프레임, 나머지는 `HudTextRefreshSeconds=0.25` 캐시. zone 줄은 WP-04 `DescribeZones()` 재사용(새 API 없음) |
| 키 | `AGolmokPlayerController::SetupInputComponent`에서 IA/IMC 런타임 생성(`GolmokCharacter`와 같은 방식), IMC 우선순위 1. F1 HUD, F2 충돌, 1~4 = `cycle[0..3]`, F5 next, F9 녹화 토글(`quick`), F10 재생 토글(`quick`, csv 없음). 프리셋 4키는 **핸들러 4개**(가변 페이로드 `BindAction` 회피) |
| Build.cs | `PrivateDependencyModuleNames`에 `"RHI"` 1개(`RHIGetGPUFrameCycles`). 그 외 없음 |
| ini 규약 | 모든 새 키는 `UPROPERTY(Config)` **두 줄 선언**(`test_ini_keys_match_config_uproperties` 정규식이 요구). `+DirectoriesToAlwaysStageAsUFS` 두 번째 줄(`../Config/Golmok`) 추가에 맞춰 WP-04 스테이징 단언을 raw-text `in` 검사로 변경 |
| 합성 실내 | 실내 manifest 픽스처 `z_synthetic_001_interior/v1`(**자기 원점** = 실외 zone-local (5, 13, 0) m, 방 8×6×3 m, 포털 `door_out`)를 `tools/scripts/make_interior_fixture.py`가 생성(테스트가 재생성해 비교). `synthetic_zone.run(interior=True)`: chunk_01·충돌에 door_1 문 구멍, `SM_room`·실내 충돌 임포트, 실내 zone 액터, 서브레벨(레벨 좌표, PointLight+마커). Levels 등록은 별도 `register_interior_sublevel()`(NamedStreamingLevel 검증용) |
| UE 자동화 테스트 | `Golmok.Lighting.PresetsFile`, `Golmok.Lighting.PresetApply`, `Golmok.Debug.StatsMath`, `Golmok.Debug.PathFormat`, `Golmok.Debug.PathRoundTrip`, `Golmok.Debug.HudStats`, `Golmok.Portal.SpawnFromManifest`, `Golmok.Portal.RoundTrip`(L_ZoneTest 있을 때만, 없으면 `AddInfo("skipped")`). 전부 `-nullrhi` 통과 조건(GPU ms 0 허용, `HudStats`는 `Frames>=10` **필수**) |
| WP-04 변경 | `AGolmokZone::SpawnPortals()` 본문, `SetCollisionDebugVisible(bool, UMaterialInterface*)`, `GetPortalActors()` 접근자, `GolmokZoneManifest::SublevelPackagePath()` 경로 함수 **추가만**. `Evaluate()`·`RegisterZone`·로그 문자열·manifest 구조체 무변경 |

### 1. 파일 목록 (`unreal/Golmok/` 기준, 그 외는 저장소 기준)
| 경로 | 상태 | 내용 |
|---|---|---|
| `Config/Golmok/lighting_presets.json` | 신규 | 프리셋 단일 소스(§2-1) |
| `Config/DefaultGame.ini` | 변경 | 패키징 2줄(UFS 스테이징·쿠킹) + `[/Script/Golmok.GolmokTimeOfDay]`, `[…GolmokPortal]`, `[…GolmokDebugSubsystem]`, `[…GolmokHUD]`, `[…GolmokPlayerController]`(§6) |
| `Source/Golmok/Golmok.Build.cs` | 변경 | `"RHI"`(§7) |
| `Source/Golmok/GolmokGameMode.h/.cpp` | 변경 | `PlayerControllerClass`, `HUDClass` |
| `Source/Golmok/Lighting/GolmokTimeOfDay.h/.cpp` | 신규 | `FGolmokLightingPreset`, `FGolmokLightingState`, `AGolmokTimeOfDay`, JSON 로더, 콘솔 `golmok.tod` |
| `Source/Golmok/Portals/GolmokPortal.h/.cpp` | 신규 | `EGolmokInteriorStreamingMode`, `EGolmokPortalState`, `AGolmokPortal`, 콘솔 `golmok.portal` |
| `Source/Golmok/Portals/GolmokLevelStreaming.h/.cpp` | 신규 | `namespace GolmokLevelStreaming`(UObject 아님): 두 스트리밍 경로·재탐색·상태 문자열 |
| `Source/Golmok/Zones/GolmokZone.h/.cpp` | 변경(추가만) | `SpawnPortals()` 구현, `SetCollisionDebugVisible`, `GetPortalActors()` |
| `Source/Golmok/Zones/GolmokZoneManifest.h/.cpp` | 변경(추가만) | `GolmokZoneManifest::SublevelPackagePath(ZoneId, Version)` |
| `Source/Golmok/Debug/GolmokStatsMath.h` | 신규 | 순수 헤더(§4-3, §4-4) |
| `Source/Golmok/Debug/GolmokDebugSubsystem.h/.cpp` | 신규 | `UGolmokDebugSubsystem` + 콘솔 `golmok.hud/collision/path/screenshot/stats` |
| `Source/Golmok/Debug/GolmokHUD.h/.cpp` | 신규 | `AGolmokHUD::DrawHUD` |
| `Source/Golmok/Debug/GolmokPathPawn.h/.cpp` | 신규 | `AGolmokPathPawn`(재생 카메라 폰, 보간) |
| `Source/Golmok/Player/GolmokPlayerController.h/.cpp` | 신규 | `AGolmokPlayerController`(디버그·조명 키) |
| `Source/Golmok/Tests/GolmokLightingTest.cpp` | 신규 | `Golmok.Lighting.PresetsFile`, `Golmok.Lighting.PresetApply` |
| `Source/Golmok/Tests/GolmokDebugTest.cpp` | 신규 | `Golmok.Debug.StatsMath`, `Golmok.Debug.PathFormat`, `Golmok.Debug.PathRoundTrip`, `Golmok.Debug.HudStats` |
| `Source/Golmok/Tests/GolmokPortalTest.cpp` | 신규 | `Golmok.Portal.SpawnFromManifest`, `Golmok.Portal.RoundTrip` |
| `Content/Python/golmok/lighting_presets.py` | 신규 | 순수 파서·검증(`unreal` 미의존) |
| `Content/Python/golmok/lighting.py` | 변경 | re-export + `apply()`(부분 프리셋 처리), `PRESETS` 삭제 |
| `Content/Python/golmok/setup_dev_level.py` | 변경 | 조명 액터 4개에 태그 `GolmokLighting` 한 줄씩 |
| `Content/Python/golmok/synthetic_zone.py` | 변경 | `run(..., interior=False)`, `door_openings`, `interior_geometry`, 서브레벨 생성, `register_interior_sublevel()`(§9) |
| `Content/Golmok/Zones/z_synthetic_001_interior/v1/manifest.json` | 신규 | 실내 픽스처(§9-1, 생성기 출력) |
| `tools/tests/fixtures/zones/z_synthetic_001_interior/v1/manifest.json` | 신규 | 위와 바이트 동일(WP-04 규약, 테스트가 강제) |
| `tools/scripts/make_interior_fixture.py` | 신규 | 실내 manifest 생성기(`golmok_tools.zone.transform`) |
| `tools/tests/test_lighting_presets.py` | 신규 | JSON 스키마·범위·cycle·값 회귀·C++ 키 문자열 대조(§8-1) |
| `tools/tests/test_ue_python_lighting.py` | 신규 | 가짜 `unreal`로 `golmok.lighting` import·`apply` 부분 프리셋 분기(§8-4) |
| `tools/tests/test_ue_stats_math.py`, `tools/tests/fixtures/ue/statsmath_driver.cpp` | 신규 | g++ 교차검증(§8-2) |
| `tools/tests/test_ue_interior_fixture.py` | 신규 | 생성기 재생성 동일·스키마·포털 왕복 좌표(§8-5) |
| `tools/tests/test_ue_wp05_fixture.py` | 신규 | Build.cs `RHI`, ini 섹션·키, GameMode 클래스, 테스트 이름, 순수 헤더 화이트리스트, 플러그인 문자열 금지(§8-3) |
| `tools/tests/test_ue_zone_fixture.py` | 변경(2곳) | 헤더/소스 규약 폴더 `Geo Zones Lighting Portals Debug Player`; 스테이징 단언 raw-text |
| `tools/tests/test_ue_python_synthetic_zone.py` | 변경 | 문 구멍·실내 방 형상·서브레벨 액터 좌표(§8-4) |
| `docs/runbooks/pc-verify-wp05.md` | 신규 | §10 |
| `docs/runbooks/pc-verify-wp04.md` | 변경(1줄) | §3 (3) "다른 x에서는 막힘" → "`interior=True` 이후에는 x=+5 문(door_1) 제외" |
| `docs/plan/WP-05-ue-portal-lighting-debug.md`, `docs/plan/STATUS.md`, `docs/ROADMAP.md` | 변경 | 결과·상태·1.3/1.5 |

### 2. 조명

#### 2-1 `lighting_presets.json` (정확한 내용)
```json
{
  "schema_version": 1,
  "cycle": ["overcast_morning", "clear_noon", "golden_evening", "night"],
  "presets": {
    "overcast_morning": {"pitch": -35.0, "yaw": 110.0, "lux": 2.5, "kelvin": 6500.0, "sky": 1.4,
                         "fog": 0.035, "fog_height_falloff": 0.15, "volumetric": false, "exposure_bias": 0.3},
    "clear_noon":       {"pitch": -62.0, "yaw": 180.0, "lux": 10.0, "kelvin": 5600.0, "sky": 1.0,
                         "fog": 0.015, "fog_height_falloff": 0.2, "volumetric": false, "exposure_bias": 0.0},
    "golden_evening":   {"pitch": -8.0, "yaw": 265.0, "lux": 4.0, "kelvin": 3600.0, "sky": 0.8,
                         "fog": 0.05, "fog_height_falloff": 0.12, "volumetric": true, "exposure_bias": 0.5},
    "night":            {"pitch": 15.0, "yaw": 0.0, "lux": 0.0, "kelvin": 4000.0, "sky": 0.15,
                         "fog": 0.03, "fog_height_falloff": 0.2, "volumetric": true, "exposure_bias": 1.5},
    "interior":         {"fog": 0.0, "fog_height_falloff": 0.2, "volumetric": false, "exposure_bias": 1.0}
  }
}
```
| 키 | 단위 | 범위(테스트·Python·C++ 공통) | UE 대상 |
|---|---|---|---|
| `pitch` | deg(음수 = 지평선 위; UE Rotator Pitch) | [−90, 90] | DirectionalLight 액터 회전 |
| `yaw` | deg | [0, 360) (반개구간) | 위와 같음 |
| `lux` | DirectionalLight Intensity | [0, 150000] | `SetIntensity`; 0이면 전환 끝에 `SetVisibility(false)` |
| `kelvin` | K | [1700, 12000] | `SetUseTemperature(true)`+`SetTemperature` |
| `sky` | SkyLight Intensity 배율 | [0, 10] | `SetIntensity` |
| `fog` | ExponentialHeightFog FogDensity | [0, 1] | `SetFogDensity` |
| `fog_height_falloff` | FogHeightFalloff | [0.001, 2] | `SetFogHeightFalloff` |
| `volumetric` | bool | — | `SetVolumetricFog`(전환 시작/끝 1회) |
| `exposure_bias` | EV | [−5, 5] | unbound `APostProcessVolume::Settings.AutoExposureBias`(+`bOverride_AutoExposureBias=true`) |

규칙(`test_lighting_presets.py`·`lighting_presets.parse_presets`·C++ 파서가 같은 규칙): `schema_version==1`; 최상위 키는 `{schema_version, cycle, presets}`뿐; 이름 `^[a-z][a-z0-9_]*$`; `cycle`은 정확히 4개·중복 없음·전부 `presets`에 있고 **9키 전부** 필수; 그 외 프리셋은 부분 허용(없는 키 = 현재 값 유지)·미지 키 금지; `interior`는 존재 필수·`cycle`에 없음·`fog == 0`·`exposure_bias > 0`; 네 cycle 프리셋 값은 WP-04 시점 `lighting.py`와 동일(테스트가 상수 표로 고정). 오버레이 키 4개 = `interior`에 있는 키(C++ `FGolmokLightingPreset::bHas*`가 그대로 표현하므로 별도 상수 없음).

#### 2-2 Python: `lighting_presets.py`(순수) + `lighting.py`
```python
# golmok/lighting_presets.py  — no `import unreal` anywhere in this module
import json, os, re
REQUIRED_KEYS = ("pitch", "yaw", "lux", "kelvin", "sky", "fog", "fog_height_falloff", "volumetric", "exposure_bias")
RANGES = {"pitch": (-90.0, 90.0), "yaw": (0.0, 360.0), "lux": (0.0, 150000.0), "kelvin": (1700.0, 12000.0),
          "sky": (0.0, 10.0), "fog": (0.0, 1.0), "fog_height_falloff": (0.001, 2.0), "exposure_bias": (-5.0, 5.0)}
HALF_OPEN = ("yaw",)                      # lo <= v < hi; others lo <= v <= hi
NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
PRESETS_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Config", "Golmok",
                                             "lighting_presets.json"))   # unreal/Golmok/Config/Golmok/…
def parse_presets(text: str) -> tuple[list[str], dict[str, dict]]: ...   # (cycle, presets); ValueError("lighting_presets.json: <preset>: <reason>")
def load_presets(path: str = PRESETS_FILE) -> tuple[list[str], dict[str, dict]]: ...
def is_partial(preset: dict) -> bool: ...                                  # set(preset) < set(REQUIRED_KEYS)
```
`lighting.py`: `import unreal`는 모듈 상단 그대로(가짜 모듈로 stub 가능); `from .lighting_presets import REQUIRED_KEYS, RANGES, PRESETS_FILE, parse_presets, load_presets` re-export; `_cache`; `presets()`(캐시, `reload()`가 비움), `cycle()`, `list_presets()`(출력 형식 유지), `apply(name)`: 본문은 기존과 같되 **있는 키만** 적용(`if "lux" in p:` 등 그룹별: sun 5키·sky·fog 2키·volumetric·exposure). `viewpoints.py`·`setup_dev_level.py`의 호출부는 무변경. `check_repo.py`는 이미 `Config/Golmok/**/*.json` 파싱을 검사한다.

#### 2-3 `Lighting/GolmokTimeOfDay.h`
```cpp
struct FGolmokLightingPreset {          // plain struct. bHas* == false 그룹은 현재 값 유지(부분 프리셋)
	FName Name;
	bool bHasSun = false;  double PitchDeg = 0.0, YawDeg = 0.0, Lux = 0.0, Kelvin = 6500.0;
	bool bHasSky = false;  double Sky = 1.0;
	bool bHasFog = false;  double Fog = 0.0, FogHeightFalloff = 0.2;
	bool bHasVolumetric = false;  bool bVolumetric = false;
	bool bHasExposure = false;  double ExposureBias = 0.0;
	bool IsComplete() const { return bHasSun && bHasSky && bHasFog && bHasVolumetric && bHasExposure; }
};
struct FGolmokLightingState {           // 액터에서 읽은/적용할 실제 값(보간 끝점)
	FRotator SunRotation = FRotator::ZeroRotator;  double Lux = 0.0, Kelvin = 6500.0, Sky = 1.0;
	double Fog = 0.0, FogHeightFalloff = 0.2, ExposureBias = 0.0;  bool bVolumetric = false;
};

UCLASS(Config = Game, HideCategories = (Rendering, Replication, Collision, Input, LOD, Cooking, Physics, Networking))
class GOLMOK_API AGolmokTimeOfDay : public AActor
{
	GENERATED_BODY()
public:
	AGolmokTimeOfDay();   // Root USceneComponent; PrimaryActorTick.bCanEverTick = true; bStartWithTickEnabled = false

	/** Seconds for preset / interior-overlay transitions (0 = instant). Tick runs only while transitioning. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Lighting", meta = (ClampMin = "0.0"))
	float TransitionSeconds = 2.f;
	/** Relative to <Project>/Config unless absolute. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Lighting")
	FString PresetsFile = TEXT("Golmok/lighting_presets.json");
	/** Applied instantly at BeginPlay; empty = keep the level's authored lighting. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Lighting")
	FName InitialPreset;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Lighting")
	FName InteriorPreset = TEXT("interior");
	/** Actor tag that pins which DirectionalLight / SkyLight / ExponentialHeightFog / PostProcessVolume the presets drive. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Lighting")
	FName LightingActorTag = TEXT("GolmokLighting");

	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Lighting|State")
	FName CurrentPreset;                       // base preset (NAME_None = 레벨 조명 그대로)
	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Lighting|State")
	FName TargetPreset;                        // 전환 중 목표 base
	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Lighting|State")
	TArray<FName> InteriorSources;             // 비어 있지 않으면 오버레이 on
	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Lighting|State")
	FString LastError;

	static AGolmokTimeOfDay* Find(UWorld* World);            // TActorIterator 첫 액터(2개 이상 → Warning 1회)
	static AGolmokTimeOfDay* FindOrSpawn(UWorld* World);     // Game/PIE 월드에서만 스폰(RF_Transient), 로그 1줄
	static bool ParsePresetsText(const FString& Json, TArray<FGolmokLightingPreset>& Out, TArray<FName>& OutCycle, FString& Error);
	static bool LoadPresetsFile(const FString& FilePath, TArray<FGolmokLightingPreset>& Out, TArray<FName>& OutCycle, FString& Error);
	FString ResolvePresetsPath() const;                      // FPaths::ProjectConfigDir() / PresetsFile
	bool EnsurePresets();                                    // 1회 로드, 실패 시 Error 로그 1회 + LastError
	UFUNCTION(BlueprintCallable, Category = "Golmok|Lighting") bool ApplyPreset(FName Name, bool bInstant = false);   // base 변경. 미지 이름 → false
	UFUNCTION(BlueprintCallable, Category = "Golmok|Lighting") bool NextPreset();      // Cycle에서 CurrentPreset 다음(없거나 마지막이면 [0])
	UFUNCTION(BlueprintCallable, Category = "Golmok|Lighting") void EnterInterior(FName Source);   // AddUnique; 0→1이면 오버레이 전환
	UFUNCTION(BlueprintCallable, Category = "Golmok|Lighting") void ExitInterior(FName Source);    // Remove; 1→0이면 base 복귀
	UFUNCTION(BlueprintCallable, Category = "Golmok|Lighting") bool IsInterior() const { return InteriorSources.Num() > 0; }
	UFUNCTION(BlueprintCallable, Category = "Golmok|Lighting") TArray<FName> GetPresetNames() const;   // 5개
	const TArray<FName>& GetCycle() const { return Cycle; }
	bool FindPreset(FName Name, FGolmokLightingPreset& Out) const;
	bool IsTransitioning() const { return bTransitioning; }
	float GetTransitionAlpha() const;                        // 0..1 (전환 없으면 1)
	bool CaptureState(FGolmokLightingState& Out) const;      // 액터 현재 값 읽기(테스트 검증용)
	FString Describe() const;                                // "overcast_morning" | "overcast_morning -> night 45%" | + " [interior: door_1]" | "(no presets)"
	virtual void Tick(float DeltaSeconds) override;          // 전환 중에만 실행됨
protected:
	virtual void BeginPlay() override;    // EnsurePresets(); ResolveTargets(); InitialPreset != None → ApplyPreset(InitialPreset, true)
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;   // InteriorSources.Empty()
	virtual void ApplyState(const FGolmokLightingState& S, bool bFinal);   // 확장점(D-010: 서브클래스가 덮어씀)
private:
	bool ResolveTargets(bool bForce = false);
	FGolmokLightingState ComposeTarget() const;              // base(CurrentPreset 또는 Initial) 위에 IsInterior()면 InteriorPreset 부분 덮기
	FGolmokLightingState StateFromPreset(const FGolmokLightingPreset& P, const FGolmokLightingState& Current) const;
	void StartTransition(const FGolmokLightingState& To, bool bInstant);
	static FGolmokLightingState Lerp(const FGolmokLightingState& A, const FGolmokLightingState& B, float Alpha);
	TArray<FGolmokLightingPreset> Presets;  TArray<FName> Cycle;
	bool bPresetsLoaded = false, bPresetsFailed = false, bTransitioning = false, bWarnedTargets = false;
	FGolmokLightingState Initial, Applied, From, To;  double TransitionStart = 0.0;
	TWeakObjectPtr<UDirectionalLightComponent> Sun;  TWeakObjectPtr<AActor> SunActor;
	TWeakObjectPtr<USkyLightComponent> Sky;  TWeakObjectPtr<UExponentialHeightFogComponent> Fog;
	TWeakObjectPtr<APostProcessVolume> PostProcess;
};
```
- **대상 찾기(`ResolveTargets`)**: `TActorIterator<AActor>` 1회 순회 — `ActorHasTag(LightingActorTag)`인 `ADirectionalLight/ASkyLight/AExponentialHeightFog/APostProcessVolume`을 우선, 남은 슬롯은 클래스별 첫 액터(PPV는 `bUnbound`). 컴포넌트는 `Actor->FindComponentByClass<UDirectionalLightComponent>()` 등(액터별 접근자 이름 차이 회피). `TWeakObjectPtr` 캐시, 무효일 때만 재탐색. 없는 대상은 건너뛰고 Warning 1회. `BeginPlay`에서 `CaptureState(Initial)`(레벨 저작값 = base가 None일 때의 복귀점).
- **JSON 파서**: `FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root)`; WP-04 규칙대로 키는 `const FString` 객체로 `TryGetObjectField/TryGetNumberField/TryGetBoolField/TryGetArrayField`. §2-1 규칙 그대로 검사(`cycle` 프리셋은 `IsComplete()` 필수, 범위, `interior` 조건). 실패 시 `Error = "lighting_presets.json: preset <n>: <key> …"`.
- **보간**: `ApplyPreset(Name)` → `EnsurePresets` → `FindPreset` → `CurrentPreset = Name` → `StartTransition(ComposeTarget(), bInstant)`. `StartTransition`: `bInstant || TransitionSeconds <= 0 || 에디터 월드` → `ApplyState(To, true)` 즉시; 아니면 `From = Applied`(현재 보간값 — 전환 중 새 요청도 끊김 없음), `TransitionStart = World->GetTimeSeconds()`, `SetActorTickEnabled(true)`. `Tick`: `α = clamp((Now − Start)/TransitionSeconds)`(선형; smoothstep은 한 줄 교체 가능, 테스트가 중간값을 단언하지 않으므로 무관), `Applied = Lerp(From, To, α)`, `ApplyState(Applied, α >= 1)`; 끝나면 `SetActorTickEnabled(false)`, `bTransitioning=false`. `Lerp`: 태양 회전 `FQuat::Slerp(A.Quaternion(), B.Quaternion(), α).Rotator()`, 스칼라 `FMath::Lerp`, `bVolumetric = α >= 0.5 ? B : A`.
- **`ApplyState`**: `SunActor->SetActorRotation(S.SunRotation)`(C++ `FRotator(Pitch, Yaw, Roll)` — Python `unreal.Rotator(roll, pitch, yaw)`와 순서가 다름을 주석), `Sun->SetIntensity((float)Lux)`, `SetUseTemperature(true)`, `SetTemperature((float)Kelvin)`; `Sky->SetIntensity`; `Fog->SetFogDensity/SetFogHeightFalloff`; `PostProcess->Settings.bOverride_AutoExposureBias = true; Settings.AutoExposureBias = (float)ExposureBias`. **캐시를 흔드는 호출은 1회**: `Sun->SetVisibility(Lux > 0)`는 켤 때 전환 시작·끌 때 끝, `Fog->SetVolumetricFog`는 켤 때 시작·끌 때 끝, `Sky->RecaptureSky()`는 `!Sky->bRealTimeCapture`일 때 끝에만. 마지막에 `Applied = S`.
- **실내 오버레이**: `ComposeTarget()` = base 상태(`CurrentPreset`이 None이면 `Initial`) 위에 `IsInterior()`면 `InteriorPreset`의 `bHas*` 그룹만 덮기. `EnterInterior(Source)`: `AddUnique`, 0→1이면 `StartTransition(ComposeTarget(), false)` + 로그 `TimeOfDay: interior overlay on (source door_1, base overcast_morning)`. `ExitInterior(Source)`: `Remove`, 1→0이면 base로 전환 + 로그 `TimeOfDay: interior overlay off -> overcast_morning`. 실내에서 `ApplyPreset(x)`는 base만 바꾸고 오버레이 유지(문 밖 풍경이 바뀜). `EndPlay`는 집합을 비운다.
- **콘솔**(`.cpp` 익명 namespace, `FAutoConsoleCommandWithWorldAndArgs`, `FindOrSpawn(World)` 후): `golmok.tod <preset>` → `golmok.tod: overcast_morning -> night over 2.0 s` / `ERROR unknown preset 'x'`; `golmok.tod next`; `golmok.tod list` → `presets: overcast_morning* clear_noon golden_evening night (overlay: interior) — current overcast_morning, interior off`(현재에 `*`).
- **PlayerController**: 키 1~4 → `Tod->ApplyPreset(Tod->GetCycle()[i])`, F5 → `NextPreset()`. `AGolmokPlayerController::BeginPlay`가 `FindOrSpawn`을 한 번 호출해 `TWeakObjectPtr` 캐시. 에디터 Python `lighting.apply(x)`와 C++는 같은 JSON·같은 속성을 만지므로 화면이 같다(런북 §3이 대조).

### 3. 포털

#### 3-1 `Portals/GolmokPortal.h`
```cpp
UENUM() enum class EGolmokInteriorStreamingMode : uint8 { LevelInstance, NamedStreamingLevel };
UENUM(BlueprintType) enum class EGolmokPortalState : uint8 { Idle, Pending, Active, Leaving };   // Pending=디바운스 대기, Active=실내 로드 요청됨, Leaving=언로드 지연 중

UCLASS(Config = Game, HideCategories = (Rendering, Replication, Input, LOD, Cooking, Physics, Networking))
class GOLMOK_API AGolmokPortal : public AActor
{
	GENERATED_BODY()
public:
	AGolmokPortal();   // Trigger = CreateDefaultSubobject<UBoxComponent>("Trigger"), SetRootComponent; OverlapOnlyPawn, QueryOnly, GenerateOverlapEvents, HiddenInGame, ShapeColor Green, bDrawOnlyIfSelected=false, Mobility Movable; PrimaryActorTick.bCanEverTick=true, bStartWithTickEnabled=false
	// manifest 값 (SpawnPortals가 FinishSpawning 전에 채움)
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Portal") FString PortalId;          // "door_1"
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Portal") FString OwnerZoneId;       // 스폰한 zone
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Portal") FString TargetZoneId;      // to_zone
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Portal") bool bIsEntry = true;      // true: exterior→interior 능동 트리거. false: interior가 스폰한 되돌아가는 수동 마커
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Portal") FString SublevelPackagePath;   // /Game/Golmok/Zones/<interior>/v<n>/L_<interior> (bIsEntry일 때만)
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Portal") double RadiusCm = 150.0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Golmok|Portal") FString Kind;              // "door"
	// Config (ini 키와 1:1, 두 줄 선언)
	/** LevelInstance: ULevelStreamingDynamic::LoadLevelInstance by package path (default). NamedStreamingLevel: ULevelStreaming registered in the persistent level. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Portal")
	EGolmokInteriorStreamingMode InteriorStreamingMode = EGolmokInteriorStreamingMode::LevelInstance;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Portal", meta = (ClampMin = "0.0"))
	float DebounceSeconds = 0.25f;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Portal", meta = (ClampMin = "0.0"))
	float UnloadDelaySeconds = 3.f;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Portal", meta = (ClampMin = "50.0"))
	float TriggerHeightCm = 250.f;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Portal", meta = (ClampMin = "0.0"))
	float CrossingHysteresisCm = 10.f;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Portal", meta = (ClampMin = "0.0"))
	float MinCrossingIntervalSeconds = 0.25f;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Portal")
	bool bStreamSublevel = true;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Portal")
	bool bSwitchLighting = true;
	// 상태
	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Portal|State") EGolmokPortalState State = EGolmokPortalState::Idle;
	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Portal|State") bool bPlayerOverlapping = false;
	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Portal|State") bool bPlayerInside = false;   // 문 평면 안쪽
	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Portal|State") FString LastEvent;

	void Configure(const AGolmokZone& Owner, const FGolmokZonePortal& P);   // FinishSpawning 전: 필드 + Trigger extent (R, R, H/2), 상대 Z = H/2
	double SignedDistanceAlongForward(const FVector& WorldPos) const;        // dot(WorldPos - Loc, GetActorForwardVector()) cm, + = 안쪽
	bool EnterInterior(FString& OutMessage);    // 콘솔·테스트 진입점: Active 강제(RequestLoad + StreamIn) + SetInside(true). 멱등
	bool LeaveInterior(FString& OutMessage);    // SetInside(false) + Leaving(UnloadDelaySeconds). 멱등
	bool IsSublevelLoaded() const;  bool IsSublevelVisible() const;
	void SetDebugVisible(bool bVisible);        // Trigger->SetHiddenInGame(!bVisible)
	FString Describe() const;                   // "door_1 (z_synthetic_001 -> z_synthetic_001_interior) active inside; sublevel visible (LevelInstance)"
	static AGolmokPortal* FindPortal(UWorld* World, const FString& PortalId);   // TActorIterator, bIsEntry 우선
	static FString DescribeAll(UWorld* World);  // golmok.portal list
	virtual void OnInteriorEntered();  virtual void OnInteriorExited();   // 확장점(문 애니메이션 등), 기본 로그
protected:
	virtual void BeginPlay() override;    // 약참조 캐시; bIsEntry면 AddDynamic ×2 + IsOverlappingActor(Pawn)면 OnTriggerBeginOverlap 경로 수동 진입; 마커면 SetGenerateOverlapEvents(false)
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;   // 타이머 해제; Active/Leaving이면 StreamOut + ExitInterior(PortalId)
	virtual void Tick(float DeltaSeconds) override;   // 오버랩 중에만: 평면 통과 판정
	UFUNCTION() void OnTriggerBeginOverlap(UPrimitiveComponent* OverlappedComp, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);
	UFUNCTION() void OnTriggerEndOverlap(UPrimitiveComponent* OverlappedComp, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex);
private:
	bool IsPlayerPawn(const AActor* Other) const;   // UGameplayStatics::GetPlayerPawn(World, 0) == Other (재생 폰도 통과)
	void OnDebounceElapsed();       // Pending→Active: RequestLoad + StreamIn
	void OnUnloadDelayElapsed();    // Leaving→Idle: StreamOut + RequestUnload
	bool StreamIn(FString& Msg);  bool StreamOut(FString& Msg);   // GolmokLevelStreaming 경유; StreamOut은 다른 Active/Leaving 포털이 같은 실내를 쓰면 생략
	void SetInside(bool bInside);   // bSwitchLighting → TimeOfDay->EnterInterior/ExitInterior(FName(PortalId)) + OnInterior* 훅 + 로그
	UGolmokZoneSubsystem* GetZoneSubsystem() const;  AGolmokTimeOfDay* GetTimeOfDay();
	UPROPERTY(VisibleAnywhere, Category = "Golmok|Portal") TObjectPtr<UBoxComponent> Trigger;
	TWeakObjectPtr<AGolmokTimeOfDay> TimeOfDay;
	FTimerHandle DebounceTimer, UnloadTimer;  double LastCrossingSeconds = -1.0e9;  bool bWarnedNoTargetZone = false;
};
```
동작(entry 포털):
1. **BeginOverlap(플레이어 폰)**: `bPlayerOverlapping = true`, `SetActorTickEnabled(true)`, `UnloadTimer` 해제(재진입이면 `State = Active` 유지 → 스래싱 없음), `State == Idle`이면 `State = Pending` + `SetTimer(DebounceTimer, this, &AGolmokPortal::OnDebounceElapsed, DebounceSeconds, false)`. **핸들러는 여기서 끝**(로드·스트리밍·조명 호출 없음 → `Load()` 스택 재진입 없음).
2. **OnDebounceElapsed**(`Pending`이고 아직 overlapping이면): `Subsystem->RequestLoad(TargetZoneId, /*bPin*/true, Msg)` — 실내 zone 액터가 레벨에 없으면 Warning 1회 `Portal door_1: no AGolmokZone 'z_synthetic_001_interior' in this level; sublevel only`; `bStreamSublevel && !SublevelPackagePath.IsEmpty()`면 `StreamIn(Msg)`; `State = Active`. 로그 `Portal door_1 (z_synthetic_001 -> z_synthetic_001_interior): player within 150 cm -> load [zone z_synthetic_001_interior loaded (pinned)]; sublevel /Game/Golmok/Zones/z_synthetic_001_interior/v1/L_z_synthetic_001_interior (LevelInstance)`.
3. **Tick(오버랩 중)**: `d = SignedDistanceAlongForward(Pawn->GetActorLocation())`; `Now − LastCrossingSeconds < MinCrossingIntervalSeconds`면 건너뜀; `!bPlayerInside && d > +CrossingHysteresisCm` → `SetInside(true)`; `bPlayerInside && d < −CrossingHysteresisCm` → `SetInside(false)`. `SetInside`: `bPlayerInside` 갱신, `LastCrossingSeconds = Now`, `bSwitchLighting`이면 `TimeOfDay->EnterInterior(FName(*PortalId))`/`ExitInterior`, 로그 `Portal door_1: crossed inward|outward`. 비용: 오버랩 중에만 내적 1개/프레임.
4. **EndOverlap**: `bPlayerOverlapping = false`, `SetActorTickEnabled(false)`. `Pending`이면 디바운스 취소·`Idle`. `bPlayerInside`(안쪽으로 나감)면 아무것도 안 함(실내 유지). 바깥쪽이면 `State = Leaving` + `SetTimer(UnloadTimer, this, &AGolmokPortal::OnUnloadDelayElapsed, UnloadDelaySeconds, false)`.
5. **OnUnloadDelayElapsed**: `StreamOut(Msg)` + `Subsystem->RequestUnload(TargetZoneId, Msg)`(interior는 거리 관리 대상이 아니라 `bBlocked`는 무해) + `State = Idle`. 로그 `Portal door_1: player left -> unload z_synthetic_001_interior; sublevel out`.
6. **EndPlay**(exterior `Unload()`→`DestroyPortals()`, PIE 종료, 레벨 언로드): 타이머 해제; `Active/Leaving`이면 `StreamOut` + `TimeOfDay->ExitInterior(PortalId)`(오버라이드 고아 방지). `RequestUnload`는 호출하지 않는다(실내 zone 액터는 WP-04 `Evaluate()`의 "부모 언로드 → 고아 interior 언로드" 규칙이 정리).
7. **`bIsEntry=false`(마커)**: `BeginPlay`에서 `Trigger->SetGenerateOverlapEvents(false)`, 델리게이트 미바인드, `State = Idle` 고정, `Describe()`에 `(marker)`. 왕복(밖→안→밖)은 entry 포털 하나의 평면 통과 판정으로 완결된다(같은 문에 두 트리거가 겹쳐 조명이 두 번 토글되거나 exit 포털이 자기 zone을 언로드해 자신을 파괴하는 경로가 없다).
8. **콘솔 `golmok.portal enter <id>`** = `EnterInterior`: `UnloadTimer` 해제 → `State != Active`면 2단계 실행 → `SetInside(true)`. `leave <id>` = `LeaveInterior`: `SetInside(false)` → `State == Active`면 `Leaving` + 언로드 타이머. 런북·`Golmok.Portal.RoundTrip`이 걷지 않고 스트리밍 경로를 검증한다.

**`Evaluate()` 포인터 안정성**(WP-04 인계 사항): `UGolmokZoneSubsystem::Evaluate()`는 `TArray<FGolmokZoneRecord*> ToLoad/ToUnload`에 `Zones` 원소 주소를 들고 `Zone->Load()`를 호출하며, `Load()` 끝의 `SpawnPortals()` → `SpawnActor` → `AGolmokPortal::BeginPlay`가 그 스택 안에서 실행된다. 보장: (a) `AGolmokPortal`은 `AActor` 파생이고 `AGolmokZone`이 아니며 `AGolmokZone`을 스폰하지 않는다 → `RegisterZone/UnregisterZone`(배열 재할당) 호출 경로 없음. (b) 스폰 시 플레이어가 이미 트리거 안이어서 `BeginOverlap`(또는 `IsOverlappingActor` 수동 진입)이 `BeginPlay`에서 즉시 오더라도 액션은 **타이머로 미뤄지므로** `RequestLoad`(→ 실내 `Load()` → `NotifyZoneLoaded` → `ResolveOverlaps`)가 exterior `Load()` 안에서 재진입하지 않는다. (c) `DestroyPortals()` → `EndPlay`는 스트리밍·조명만 만지고 서브시스템 배열에 손대지 않는다. (d) 서브레벨 안에 `AGolmokZone`을 두지 않는다(§9 규약). `Evaluate()` 자체는 **바꾸지 않는다**(WP-04 동작 유지·표면 최소화; 인덱스/약참조 하드닝은 §12에 선택 과제로 기록).

#### 3-2 두 스트리밍 경로 — `Portals/GolmokLevelStreaming.h`
```cpp
namespace GolmokLevelStreaming
{
	GOLMOK_API ULevelStreaming* Find(UWorld* World, const FString& PackagePath);   // World->GetStreamingLevels() 중 GetWorldAssetPackageName() == PackagePath (등록 항목·동적 인스턴스 모두)
	GOLMOK_API bool StreamIn(UWorld* World, const FString& PackagePath, EGolmokInteriorStreamingMode Mode, FString& OutMessage);
	GOLMOK_API bool StreamOut(UWorld* World, const FString& PackagePath, FString& OutMessage);
	GOLMOK_API bool IsLoaded(UWorld* World, const FString& PackagePath);  GOLMOK_API bool IsVisible(UWorld* World, const FString& PackagePath);
	GOLMOK_API FString Describe(UWorld* World, const FString& PackagePath);   // "none | loading | loaded | visible"
}
```
- **`LevelInstance`(기본)**: `Find()`에 있으면 `SetShouldBeLoaded(true); SetShouldBeVisible(true)`(재사용 — 두 문이 한 실내로 통해도 인스턴스 1개). 없으면 `FPackageName::DoesPackageExist(PackagePath)` 검사(없으면 Warning `sublevel package missing: %s` + false, 실패 아님) → `bool bOk = false; ULevelStreamingDynamic* L = ULevelStreamingDynamic::LoadLevelInstance(World, PackagePath, FVector::ZeroVector, FRotator::ZeroRotator, bOk, FPackageName::GetShortName(PackagePath) + TEXT("_inst"));` → 메시지 `stream in (LevelInstance) %s`. **트랜스폼은 항등**(서브레벨은 레벨 좌표로 저작).
- **`NamedStreamingLevel`**: `Find()`에 있어야 한다(퍼시스턴트 레벨 Levels 창에 등록된 `ULevelStreaming`; `synthetic_zone.register_interior_sublevel()`이 등록). 있으면 `SetShouldBeLoaded/SetShouldBeVisible(true)`, 없으면 Error 메시지 `sublevel %s is not registered in the persistent level (Window > Levels); use InteriorStreamingMode=LevelInstance` + false. `UGameplayStatics::LoadStreamLevel` 폴백은 **두지 않는다**(기본 `FLatentActionInfo`로는 잠재 액션이 처리되지 않아 죽은 코드).
- **`StreamOut`**: `Find()` → `SetShouldBeVisible(false); SetShouldBeLoaded(false);` 동적 인스턴스(`Cast<ULevelStreamingDynamic>`)면 `SetIsRequestingUnloadAndRemoval(true)`(§11 #3, 실패 시 줄 삭제). 호출자(포털)는 `TActorIterator<AGolmokPortal>`로 같은 `SublevelPackagePath`를 가진 다른 포털이 `Active/Leaving`이면 호출을 생략한다(언로드 시점 1회 순회).
- **왜 `LevelInstance`가 기본인가**: ① 서브레벨 경로가 manifest에서 결정되므로(스펙 §5) 퍼시스턴트 맵을 손대지 않고 어떤 실내든 스트리밍한다 — WP-06 임포트 자동화가 서브레벨만 만들면 끝나고, 실내 N개에 Levels 편집·`.umap` LFS 잠금이 늘지 않는다(ARCHITECTURE §4-6 불변 버전 게시와 정합). ② 재탐색이 패키지 이름으로 가능해 상태 객체가 필요 없고 두 포털이 한 실내를 공유해도 인스턴스가 하나다. ③ `NamedStreamingLevel`은 `LoadLevelInstance` 시그니처가 5.8에서 어긋났을 때(§11 #1) ini 한 줄로 우회하는 용도이며, 그 등록에 필요한 Python `add_level_to_world`(§11 #30)는 기본 경로에 필요 없다. ④ 쿠킹은 `+DirectoriesToAlwaysCook=(Path="/Game/Golmok/Zones")`(§6)로 보장(명명 경로는 맵 등록으로 자동 포함되지만 기본 경로는 이 줄이 필요).

#### 3-3 `AGolmokZone::SpawnPortals()` 구현
```cpp
void AGolmokZone::SpawnPortals()
{
	UWorld* World = GetWorld();
	if (!World) { return; }
	DestroyPortals();   // 재진입 안전
	for (const FGolmokZonePortal& P : Manifest.Portals)
	{
		const FTransform T = GetPortalWorldTransform(P);
		FActorSpawnParameters Params;
		Params.Owner = this;
		Params.ObjectFlags |= RF_Transient;                     // 에디터 월드(RebuildInEditor)에서도 저장 안 됨
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		Params.bDeferConstruction = true;                        // BeginPlay 전에 필드를 채운다. Params.Name은 지정하지 않는다(재로드 시 이름 충돌)
		AGolmokPortal* Portal = World->SpawnActor<AGolmokPortal>(AGolmokPortal::StaticClass(), T, Params);
		if (!Portal) { UE_LOG(LogGolmok, Warning, TEXT("Zone %s: portal %s could not be spawned"), *ZoneId, *P.Id); continue; }
		Portal->Configure(*this, P);
#if WITH_EDITOR
		Portal->SetActorLabel(FString::Printf(TEXT("Portal_%s_%s"), *ZoneId, *P.Id));
#endif
		Portal->FinishSpawning(T);
		PortalActors.Add(Portal);
		const FVector Rel = GolmokGeo::EnuToUE(P.PositionEnu);
		const FVector Loc = T.GetLocation();
		UE_LOG(LogGolmok, Log, TEXT("Zone %s: portal %s -> %s rel (%.0f, %.0f, %.0f) cm yaw %.1f radius %.0f cm -> level (%.2f, %.2f, %.2f) [%s]"),
			*ZoneId, *P.Id, *P.ToZone, Rel.X, Rel.Y, Rel.Z, -P.YawDeg, PortalRadiusCm(P), Loc.X, Loc.Y, Loc.Z,
			IsInterior() ? TEXT("marker") : TEXT("entry"));
	}
}
```
`Configure`: `PortalId=P.Id; OwnerZoneId=Owner.ZoneId; TargetZoneId=P.ToZone; Kind=P.Kind; RadiusCm=PortalRadiusCm(P); bIsEntry=!Owner.IsInterior();` `bIsEntry`면 `Ver = Subsystem && Subsystem->FindZone(P.ToZone) ? FindZone(P.ToZone)->Version : 1`(에디터 월드에는 서브시스템이 없으므로 1), `SublevelPackagePath = GolmokZoneManifest::SublevelPackagePath(P.ToZone, Ver)`(새 함수 = `AssetFolder(ZoneId, Version) + "/L_" + ZoneId`); 마커면 빈 문자열. `Trigger->SetBoxExtent(FVector(R, R, TriggerHeightCm/2))`, `Trigger->SetRelativeLocation(FVector(0, 0, TriggerHeightCm/2))`. 에디터 월드(`RebuildInEditor`)에서도 스폰되어 위치를 눈으로 확인할 수 있다(BeginPlay 없음 = 바인딩 없음; Transient, `DestroyPortals()`가 정리). `DestroyPortals()`·`Load()`의 로그 문자열(`portals %d (WP-05)`)은 WP-04 그대로. 추가 API: `void SetCollisionDebugVisible(bool bVisible, UMaterialInterface* WireMaterial)`(충돌 SM 컴포넌트 `SetHiddenInGame(!bVisible)` + 모든 슬롯 `SetMaterial(i, bVisible ? WireMaterial : nullptr)`; `BlockerComponents`·`PlaceholderBoxes` `SetHiddenInGame(!bVisible)`), `const TArray<TObjectPtr<AActor>>& GetPortalActors() const`.
런북 기대 로그: `Zone z_synthetic_001: portal door_1 -> z_synthetic_001_interior rel (500, -950, 0) cm yaw -90.0 radius 150 cm -> level (18170.57, -23148.01, 999.32) [entry]` / `Zone z_synthetic_001_interior: portal door_out -> z_synthetic_001 rel (0, 350, 0) cm yaw 90.0 radius 150 cm -> level (18170.57, -23148.01, 999.32) [marker]`(같은 점, 소수 둘째 자리까지 일치).

### 4. 디버그

#### 4-1 `Debug/GolmokDebugSubsystem.h`
```cpp
UCLASS(Config = Game)
class GOLMOK_API UGolmokDebugSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()
public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;   // Game, PIE (WP-04 §11 #2와 같은 대안)
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;              // 값 보정(RecordHz>=1, Window>=0.5, Capacity>=64)
	virtual void Deinitialize() override;   // OnEndFrame 해제; 녹화 중이면 버림(Warning); 재생 중이면 StopPlayback("world ending"); CSV 중이면 Stop; 충돌 표시 복원
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;   // bSampleWhenHudHidden이면 OnEndFrame 바인드; bHudOnAtStart → SetHudVisible(true)

	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "0.5"))
	float StatsWindowSeconds = 2.f;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "64"))
	int32 StatsCapacity = 2048;               // 2 s × 1000 fps 상한
	/** False: frames are sampled only while the HUD is visible or a path is playing (saves 4 doubles per frame). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	bool bSampleWhenHudHidden = true;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "1"))
	int32 RecordHz = 10;
	/** Under <Project>/Saved/ */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	FString PathFolder = TEXT("Golmok/Paths");
	/** Under <Project>/Saved/ (same tree as viewpoints.py: Screenshots/Golmok/<tag>/<preset>/<name>.png) */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	FString ScreenshotFolder = TEXT("Screenshots/Golmok");
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "1", ClampMax = "8"))
	int32 ScreenshotMultiplier = 2;
	/** Fallback wire material when GEngine->WireframeMaterial is null. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	FSoftObjectPath CollisionDebugMaterialPath;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	bool bCollisionShowFlag = true;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "0.2"))
	float CollisionRefreshSeconds = 1.f;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "0.05"))
	float HudTextRefreshSeconds = 0.25f;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	bool bHudOnAtStart = false;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	bool bHidePlayerDuringPlayback = true;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	FString QuickPathName = TEXT("quick");    // F9/F10
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "20.0", ClampMax = "150.0"))
	float PlaybackFov = 80.f;

	// HUD / 통계
	void SetHudVisible(bool bVisible);  bool IsHudVisible() const { return bHudVisible; }
	bool GetStats(GolmokStatsMath::Stats& Out) const;     // Compute(Ring, StatsWindowSeconds); 샘플 0이면 false
	FString FormatStatsLine() const;                      // "fps 158.3  1% low 121.0  game 1.75 ms  render 6.98 ms  gpu 5.99 ms  (2.0 s, 316 fr)" — golmok.stats·HudStats 테스트
	void PushFrameSample(double DtSec, double GameMs, double RenderMs, double GpuMs);   // OnEndFrame 내부 + 테스트 훅
	const TArray<FString>& GetHudLines();                 // 캐시(HudTextRefreshSeconds), fps 두 줄은 매 호출 재생성
	// 충돌
	void SetCollisionVisible(bool bVisible);  bool IsCollisionVisible() const { return bCollisionVisible; }
	// 경로
	bool StartRecording(const FString& Name, FString& OutMessage);
	bool StopRecording(FString& OutMessage);                 // 파일 저장
	bool StartPlayback(const FString& Name, bool bCsv, FString& OutMessage);
	void StopPlayback(const TCHAR* Reason);                  // 복원 + CsvProfile Stop + 최신 CSV 로그
	void OnPlaybackFinished(AGolmokPathPawn* Pawn);          // 폰이 끝에서 호출
	bool IsRecording() const { return bRecording; }  bool IsPlaying() const { return bPlaying; }
	bool GetPlaybackProgress(double& OutT, double& OutDuration) const;
	FString PathFilePath(const FString& Name) const;         // <Saved>/<PathFolder>/<Name>.json
	static bool IsValidPathName(const FString& Name);        // ^[A-Za-z0-9_-]{1,64}$
	static bool SavePathFile(const FString& FilePath, const GolmokStatsMath::CameraPath& Path, FString& Error);   // FFileHelper::SaveStringToFile(UTF8_TO_TCHAR)
	static bool LoadPathFile(const FString& FilePath, GolmokStatsMath::CameraPath& Out, FString& Error);         // FFileHelper::LoadFileToString → TCHAR_TO_UTF8 → ParsePathJson
	TArray<FString> ListPathNames() const;                   // IFileManager::Get().FindFiles(Out, *Dir, TEXT("json"))
	const FString& GetLastPathName() const { return LastPathName; }
	// 스크린샷
	bool TakeScreenshot(const FString& Tag, const FString& NameOrEmpty, FString& OutMessage);
private:
	void OnEndFrame();  void BindSampler(bool bOn);  void RecordSample();  void RefreshCollisionVisuals();
	UMaterialInterface* GetWireMaterial();                   // GEngine->WireframeMaterial → CollisionDebugMaterialPath.TryLoad() → nullptr(Warning 1회)
	void ApplyCollisionShowFlag(bool bOn);
	FString BuildZoneLines() const;  FString BuildPortalLine() const;  FString BuildLightingLine() const;  FString BuildPlayerLine() const;  FString BuildPathLine() const;
	AGolmokTimeOfDay* GetTimeOfDay();
	GolmokStatsMath::RingBuffer Ring{2048};                  // 순수 C++(UPROPERTY 아님)
	FDelegateHandle EndFrameHandle;
	bool bHudVisible = false, bCollisionVisible = false, bRecording = false, bPlaying = false, bPlayCsv = false, bCsvStarted = false;
	TArray<FString> HudLinesCache;  double HudLinesTime = -1.0;
	FString RecordName;  GolmokStatsMath::CameraPath RecordPath;  double RecordStartSeconds = 0.0;  FTimerHandle RecordTimer;
	FString PlayName, LastPathName;
	TWeakObjectPtr<AGolmokPathPawn> PathPawn;  TWeakObjectPtr<APawn> SavedPawn;  bool bSavedPawnHidden = false;
	TWeakObjectPtr<AGolmokTimeOfDay> CachedTimeOfDay;
	UPROPERTY(Transient) TObjectPtr<UMaterialInterface> WireMaterial;
	FTimerHandle CollisionTimer;
};
```
월드 타입: Game·PIE만(`GolmokZoneSubsystem`과 같은 이유). 서브시스템은 틱하지 않는다(`UWorldSubsystem`; 매 프레임 일은 `OnEndFrame` 델리게이트 하나).

#### 4-2 통계 샘플링 위치와 전역
- **어디서**: `FCoreDelegates::OnEndFrame`(Core, `FSimpleMulticastDelegate`; `AddUObject(this, &UGolmokDebugSubsystem::OnEndFrame)`, `Remove(EndFrameHandle)`). `FEngineLoop::Tick` 끝에서 PIE·`-game`·`-nullrhi` 모두 무조건 한 번 불린다. `AHUD::DrawHUD`에서 재지 않는 이유: HUD가 꺼지면 샘플이 끊겨 `golmok.stats`·`--csv` 재생·자동화가 값을 못 읽고, `-nullrhi`에서 DrawHUD 호출을 보장할 수 없다. `UTickableWorldSubsystem`을 쓰지 않는 이유: `GetStatId`·`Super::Tick` 등 5.x 변동 표면이 더 넓다. `bSampleWhenHudHidden=True`(기본)면 `OnWorldBeginPlay`에서 바인드; False면 HUD 켜짐/재생 중에만 바인드(그때는 `golmok.stats`가 "sampler off" 메시지).
- **값**: `DtSec = FApp::GetDeltaTime()`(엔진 `stat fps`와 같은 프레임 델타, 시간 배율 무관); Game/Render = `GGameThreadTime`, `GRenderThreadTime`(`CoreGlobals.h`, uint32 cycles); GPU = `RHIGetGPUFrameCycles()`(`RHI.h`, uint64). 셋 다 `GolmokStatsMath::CyclesToMs(static_cast<std::uint64_t>(cycles), FPlatformTime::GetSecondsPerCycle())`(엔진 `ToMilliseconds`와 같은 식; uint32는 uint64로 승격, 축소 변환 없음). `.cpp` 상단 `#define GOLMOK_GPU_TIME_SOURCE 1` — 컴파일 실패 시 0으로 바꾸면 GPU는 항상 0(HUD `gpu n/a`). `GAverageFPS`는 쓰지 않는다.
- **창**: 링 용량 `StatsCapacity`(2048). `Compute`는 최신부터 누적 dt가 `StatsWindowSeconds`를 넘기 전까지 사용(60 fps·2 s = 120개). 켠 직후 누적 dt < 창이면 HUD에 `warming 0.8/2.0 s`.

#### 4-3 순수 헤더 `Debug/GolmokStatsMath.h` (namespace `GolmokStatsMath`, 전부 `inline`, double)
```cpp
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>
namespace GolmokStatsMath {
struct FrameSample { double DtSec = 0.0; double GameMs = 0.0; double RenderMs = 0.0; double GpuMs = 0.0; };
class RingBuffer {                       // 고정 용량 원형 버퍼(가득 차면 가장 오래된 것 덮음)
public:
	explicit RingBuffer(std::size_t Capacity = 2048);
	void Push(const FrameSample& S);  void Clear();
	std::size_t Size() const;  std::size_t Capacity() const;
	const FrameSample& FromNewest(std::size_t i) const;   // i = 0 최신
private: std::vector<FrameSample> Buf; std::size_t Head = 0, Count = 0; };
struct Stats { std::size_t Frames = 0; double WindowSec = 0.0; double AvgFps = 0.0; double OnePercentLowFps = 0.0;
               double AvgFrameMs = 0.0; double P99FrameMs = 0.0; double AvgGameMs = 0.0; double AvgRenderMs = 0.0; double AvgGpuMs = 0.0; bool HasGpu = false; };
inline double CyclesToMs(std::uint64_t Cycles, double SecondsPerCycle) { return static_cast<double>(Cycles) * SecondsPerCycle * 1000.0; }
double Percentile(std::vector<double> Values, double P);   // numpy 'linear': 정렬 후 h=(N-1)·P/100, lo=floor(h): x[lo]+(h-lo)·(x[lo+1]-x[lo]); N==0 → 0
Stats Compute(const RingBuffer& Ring, double WindowSec);
//  창 = 최신부터 누적 DtSec <= WindowSec(첫 샘플 항상 포함); DtSec <= 0 샘플 제외
//  AvgFps = Frames / ΣDt   (perf_report.fps_avg와 동일)
//  OnePercentLowFps = Percentile({1/Dt_i}, 1)   (perf_report: np.percentile(fps, 1))
//  P99FrameMs = Percentile({1000·Dt_i}, 99); Avg*Ms = 산술 평균; HasGpu = any(GpuMs > 0)
// ---- 숫자 포매팅(<cstdio> 없음, 로케일 무관) ----
std::string FormatFixed(double Value, int Decimals);        // 부호, 정수부, 소수부 Decimals자리 고정. 반올림 = std::llround(|v|·10^d) (half away from zero). NaN/Inf → "0"
bool ParseNumber(const std::string& Text, std::size_t& Pos, double& Out);   // JSON number 문법(부호, 정수, 소수, 지수) → std::stod
// ---- 경로 JSON ----
struct PoseSample { double T = 0.0; std::array<double, 3> P{}; std::array<double, 3> R{}; };   // t 초, p 레벨 UE cm (x,y,z), r 도 (pitch,yaw,roll)
struct CameraPath { int Version = 1; std::string Name, Level, Created; int Hz = 10; std::vector<PoseSample> Samples;
                    double Duration() const; /* 마지막 t, 없으면 0 */ };
std::string FormatPathJson(const CameraPath& Path);                             // §4-4 형식 그대로
bool ParsePathJson(const std::string& Text, CameraPath& Out, std::string& Error);   // 전용 소형 JSON 리더(객체·배열·문자열·수·true/false/null·공백), 키 순서 무관, 미지 키 무시
double LerpAngleDeg(double A, double B, double Alpha);                          // delta를 (-180, 180]로 정규화(최단호)
bool PoseAt(const CameraPath& Path, double T, PoseSample& Out);                 // 구간 선형(위치 Lerp, 각도 LerpAngleDeg); T<첫→첫, T>끝→끝; 비면 false
}
```
`std::min/max`(Windows 매크로)·`PI`·`check` 이름·`printf`·`<cstdio>`를 쓰지 않는다(MSVC·g++ `-pedantic -Werror` 둘 다 통과). UE 쪽 회전 보간은 `AGolmokPathPawn`이 `FQuat::Slerp`를 쓰고, 헤더의 `LerpAngleDeg/PoseAt`는 Python 교차검증과 `PathRoundTrip` 테스트의 참조 구현이다(둘의 차이는 yaw만 도는 경로에서 0).

#### 4-4 경로 JSON 형식(정확)
```json
{"version": 1, "name": "walk_01", "level": "L_ZoneTest", "hz": 10, "created": "2026-09-25T10:11:12Z", "samples": [
{"t": 0.000, "p": [17670.59, -22698.00, 1190.00], "r": [-5.000, 90.000, 0.000]},
{"t": 0.100, "p": [17670.59, -22690.12, 1190.00], "r": [-5.000, 90.000, 0.000]}
]}
```
- 키 순서 고정(위), 한 샘플 한 줄, 마지막 샘플 뒤 쉼표 없음, 파일 끝 개행 1개. 수치는 `FormatFixed`: `t` 3자리, `p` 2자리(cm, 0.1 mm 이하 손실), `r` 3자리. 문자열은 `" \ \n \t`와 제어문자(`\u00XX`)만 이스케이프(이름은 `IsValidPathName`으로 ASCII 제한). `version != 1`, `samples` 없음, `t` 비단조 → Error `"path json: <위치> <이유>"`.
- **왕복 계약**: Python `json.loads(C++ 출력)` 후 **값 동일(1e-6)**·키 순서·`version/name/level/hz/created` 보존. 바이트 동일은 요구하지 않는다(printf 반올림 재현 부담 없음; 테스트 입력값은 출력 자릿수 격자 위에서 생성해 tie를 만들지 않는다).
- 순수 C++ 선택 이유: 형식이 작고, `FJsonSerializer`를 쓰면 CI에서 재현할 수 없어 교차검증이 불가하다.

#### 4-5 녹화·재생
- **record** `StartRecording(Name)`: `IsValidPathName` 검사, 재생 중이면 거절. `RecordPath = {Name, Level = World->GetMapName()에서 `World->StreamingLevelsPrefix` 제거, Hz = RecordHz, Created = FDateTime::UtcNow().ToIso8601()}`, `RecordStartSeconds = World->GetTimeSeconds()`, `SetTimer(RecordTimer, this, &UGolmokDebugSubsystem::RecordSample, 1.f/RecordHz, true)` + 즉시 1회. `RecordSample`: `APlayerCameraManager* Cam = UGameplayStatics::GetPlayerCameraManager(World, 0)` → `GetCameraLocation()/GetCameraRotation()`(Pitch, Yaw, Roll), `t = Now − Start`. `StopRecording`: 타이머 해제, `IFileManager::Get().MakeDirectory(*Dir, true)`, `SavePathFile`, `LastPathName = Name`, 메시지 `path 'walk_01' saved: 612 samples, 61.2 s -> <abs path>`.
- **play** `StartPlayback(Name, bCsv)`: 녹화 중이면 거절; `LoadPathFile` 실패·샘플 0이면 메시지. `SavedPawn = PC->GetPawn()`; `bHidePlayerDuringPlayback`면 `SavedPawn->SetActorHiddenInGame(true)`(원값 저장; **충돌은 끄지 않는다**). `PathPawn = SpawnActor<AGolmokPathPawn>(첫 샘플 위치·회전, RF_Transient)` → `PathPawn->Init(this, MoveTemp(Path), PlaybackFov)` → `PC->Possess(PathPawn)` → **`PC->SetViewTargetWithBlend(PathPawn, 0.f)` 명시 호출**(§11 #22). `bPlaying = true; bPlayCsv = bCsv; bCsvStarted = false`. 로그 `path play 'walk_01' (61.2 s, 612 samples)%s`(" + CsvProfile").
- **`AGolmokPathPawn : APawn`**: 루트 `USphereComponent`(반경 30 cm, `SetCollisionEnabled(QueryOnly)`, `SetCollisionObjectType(ECC_Pawn)`, `SetCollisionResponseToAllChannels(ECR_Ignore)`, `SetCollisionResponseToChannel(ECC_WorldDynamic, ECR_Overlap)`, `SetGenerateOverlapEvents(true)` → 포털 트리거(`OverlapOnlyPawn`, ObjectType WorldDynamic)가 이 폰을 본다) + `UCameraComponent`(FOV = `PlaybackFov`). 입력 없음, `AutoPossessPlayer` 없음. `Tick(Dt)`: 첫 틱에 `bPlayCsv && !bCsvStarted`면 `Owner->BeginCsv()`(`GEngine->Exec(World, TEXT("CsvProfile Start"))`; 카메라가 자리 잡은 뒤 시작); `Elapsed += Dt`; 세그먼트 커서 단조 증가로 A/B 샘플 찾기, 위치 `FMath::Lerp`, 회전 `FQuat::Slerp(A.Quaternion(), B.Quaternion(), u)` → `SetActorLocationAndRotation`(TeleportPhysics) + `PC->SetControlRotation(Rot)`; `Elapsed >= Duration` → 마지막 샘플 고정 후 `Owner->OnPlaybackFinished(this)`. **왜 빙의 폰인가**: `UGolmokZoneSubsystem::GetPlayerLocation`·`AGolmokPortal::IsPlayerPawn`이 `GetPlayerPawn(0)`을 보므로 재생 폰이 플레이어여야 zone 거리 로드·포털 반응이 경로를 따라온다(카메라 액터 + 충돌 끈 유령 폰은 `UpdateOverlaps`가 오버랩을 만들지 않아 문 전환 스파이크가 CSV에서 빠진다). 캐릭터 자체를 옮기면 캡슐 충돌·붐 카메라 때문에 기록 포즈를 재현하지 못한다.
- **종료** `OnPlaybackFinished`/`StopPlayback(Reason)`: `bCsvStarted`면 `GEngine->Exec(World, TEXT("CsvProfile Stop"))` → `FPaths::ProfilingDir()/TEXT("CSV")`에서 `Profile*.csv`를 `IFileManager::GetTimeStamp` 최신순으로 골라 로그 `csv: <abs path>  ->  golmok-perf "<abs path>" --label walk_01 --markdown`(못 찾으면 폴더만 로그; `-game` 런처 엔진은 `%LOCALAPPDATA%\UnrealEngine\5.8\Saved\Profiling\CSV\`임을 런북에 명시); `PC->Possess(SavedPawn)`(무효면 `RestartPlayer`) + `SetViewTargetWithBlend(SavedPawn, 0)`; 숨김 복원; `PathPawn->Destroy()`; `bPlaying = false`; 로그 `path play 'walk_01' finished|stopped (<reason>) after 61.2 s`. `Deinitialize`(PIE 종료)도 같은 정리.
- **HUD 진행률**: `path: play walk_01 27.6/61.2 s 45% [csv]` / `rec walk_01 12.3 s 123 samples` / `idle`.
- **CSV·`golmok-perf`**: 엔진 `FCsvProfiler`가 `Exec`로 시작/정지되므로 열 이름(`FrameTime, GameThreadTime, RenderThreadTime, GPUTime`, `EVENTS`, 끝 헤더행)은 `perf_report.read_csv`가 이미 처리하는 5.8 형식 그대로. `golmok-perf` 기본 워밍업 2 s(`--skip-seconds`)가 정지 프레임에 떨어지도록 **녹화 시작 후 3 s는 제자리에 서 있으라**고 런북에 적는다.

#### 4-6 `golmok.collision`
`SetCollisionVisible(b)`: ① `TActorIterator<AGolmokZone>`마다 `Zone->SetCollisionDebugVisible(b, GetWireMaterial())`(충돌 SM 와이어, blocker·플레이스홀더 박스 unhide — WP-04 색 유리 청록/no_entry 빨강) ② `TActorIterator<AGolmokPortal>`마다 `SetDebugVisible(b)`(초록 박스) ③ `bCollisionShowFlag`면 `UGameViewportClient* VC = World->GetGameViewport(); VC->EngineShowFlags.SetCollision(b)`(실패 시 `GEngine->Exec(World, TEXT("show collision"))` 토글, §11 #20). b면 `CollisionRefreshSeconds` 타이머로 ①②를 재적용(새로 로드된 zone·포털을 잡는다; WP-04 `Load()`에 훅을 넣지 않는다), false면 타이머 해제. `GetWireMaterial()`: `GEngine->WireframeMaterial`(이미 로드된 `UEngine` 프로퍼티) → 없으면 `CollisionDebugMaterialPath.TryLoad()` → 그것도 없으면 nullptr(Warning 1회, 충돌 메시는 기본 머티리얼로 보임).

#### 4-7 `golmok.screenshot <tag> [name]`
`Preset = TimeOfDay ? TimeOfDay->CurrentPreset(None이면 "current")`; `Dir = FPaths::ProjectSavedDir() / ScreenshotFolder / <tag> / <preset>`; `File = <name>`(생략 시 `FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S"))`); `MakeDirectory(Dir, true)`; `GEngine->Exec(World, *FString::Printf(TEXT("HighResShot %d filename=\"%s\""), ScreenshotMultiplier, *(Dir / File)))`. 메시지 `screenshot requested -> <Dir/File>.png (written on the next frame)`. `viewpoints.py`의 `Saved/Screenshots/Golmok/<tag>/<preset>/<name>.png`와 같은 트리(`FPaths::ScreenShotDir()`는 `Saved/Screenshots/WindowsEditor/`를 끼워 넣으므로 쓰지 않는다). 고해상도 캡처라 HUD는 찍히지 않는다.

#### 4-8 `AGolmokHUD::DrawHUD`
```cpp
UCLASS(Config = Game)
class GOLMOK_API AGolmokHUD : public AHUD
{
	GENERATED_BODY()
public:
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "0.5", ClampMax = "3.0"))
	float HudScale = 1.f;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug", meta = (ClampMin = "0.0"))
	float MarginPx = 16.f;
	virtual void DrawHUD() override;
};
```
`DrawHUD()`: `Super::DrawHUD()`; 서브시스템 없거나 `!IsHudVisible()`면 return(재생 중이면 `path:` 줄만 그린다); `Lines = Subsystem->GetHudLines()`; `UFont* Font = GEngine->GetSmallFont()`; `LineH = 16 * HudScale`; 배경 `DrawRect(FLinearColor(0,0,0,0.55f), MarginPx-6, MarginPx-4, 640*HudScale, Lines.Num()*LineH+8)`; 각 줄 `DrawText(Line, Color, MarginPx, MarginPx + i*LineH, Font, HudScale)`. 줄(값은 예; zone 줄은 `DescribeZones()`의 줄을 그대로 최대 4줄):
```
Golmok  fps 158.3  1% low 121.0  (2.0 s, 316 fr)                    흰색; 워밍업이면 "fps warming 0.8/2.0 s"; 1% low < avg·0.5면 노랑
game 1.75 ms  render 6.98 ms  gpu 5.99 ms                          흰색; GPU 샘플 최대 0이면 "gpu n/a"
tod: overcast_morning (-> clear_noon 45%) [interior: door_1]        노랑; 전환 없으면 괄호 생략, 오버레이 없으면 대괄호 생략, 프리셋 없으면 "tod: -"
pos ENU E 176.71 N 221.98 U 9.99  lat 37.562000 lon 126.925000     청록; 원점 없으면 "pos UE (x, y, z) cm (no GeoOrigin)"
zones: 2 zones (load < 150 m, unload > 250 m)                      초록; 이어서 DescribeZones() 줄 최대 4개
  z_synthetic_001              v1   prio 10   loaded    dist 0.0 m
portals: door_1 -> z_synthetic_001_interior active inside, sublevel visible | door_out (marker)   초록; 없으면 "portals: -"
path: idle | rec walk_01 12.3 s 123 samples | play walk_01 27.6/61.2 s 45% [csv]   주황
collision: off   keys: F1 hud  F2 col  1-4 tod  F5 next  F9 rec  F10 play   회색
```
`pos` 줄: 폰 → 없으면 카메라 위치; ENU = `GolmokGeo::UEToEnu(LevelUE)`(m), lat/lon = `UGolmokGeoSubsystem::LevelUEToLonLat`. fps 두 줄은 매 프레임 `FormatStatsLine` 계열로 재생성, 나머지는 `HudTextRefreshSeconds`마다 캐시.

#### 4-9 콘솔 명령(정확한 구문, 전부 `FAutoConsoleCommandWithWorldAndArgs`, `.cpp` 익명 namespace, 출력 `UE_LOG(LogGolmok, Log, "golmok.<cmd>: %s")`, 오류는 `ERROR ` 접두 — WP-04 규약)
| 명령 | 동작 |
|---|---|
| `golmok.tod <preset>` / `next` / `list` | §2-3 |
| `golmok.hud [0\|1]` | 인자 없으면 토글 |
| `golmok.collision [0\|1]` | 인자 없으면 토글. 메시지 `on (show flag 1, 2 zones, 2 portals)` |
| `golmok.path record <name>` | 녹화 시작 |
| `golmok.path stop` | 녹화 종료·저장(재생 중이면 재생 중단) |
| `golmok.path play <name> [--csv]` | 재생(+CsvProfile). `--csv`는 어느 위치든 |
| `golmok.path stopplay` | 재생 중단(복원) |
| `golmok.path list` | `Saved/Golmok/Paths/*.json` 이름·샘플 수·길이 |
| `golmok.screenshot <tag> [name]` | §4-7 |
| `golmok.stats` | `FormatStatsLine()` 한 줄을 로그(HUD 없이, `-nullrhi` 자동화·스크립트용). 샘플 0이면 `stats: no samples yet` |
| `golmok.portal list` / `enter <portal_id>` / `leave <portal_id>` | `DescribeAll` / `EnterInterior` / `LeaveInterior`(§3-1 8) |

### 5. 플레이어

```cpp
UCLASS(Config = Game)
class GOLMOK_API AGolmokPlayerController : public APlayerController
{
	GENERATED_BODY()
public:
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	bool bDebugKeysEnabled = true;
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Debug")
	int32 DebugMappingPriority = 1;   // 캐릭터 IMC(0) 위; 키가 겹치지 않으므로 형식적
	AGolmokTimeOfDay* GetTimeOfDay();  // TWeakObjectPtr 캐시 → AGolmokTimeOfDay::FindOrSpawn(GetWorld())
protected:
	virtual void BeginPlay() override;              // Super; GetTimeOfDay()(스폰 보장); AddMappingContext()
	virtual void SetupInputComponent() override;    // Super; EnsureInputAssets(); BindAction ×9
	virtual void OnPossess(APawn* InPawn) override; // Super; AddMappingContext()(재빙의 대비, AddMappingContext는 멱등)
private:
	void EnsureInputAssets();  void AddMappingContext();
	void OnToggleHud();  void OnToggleCollision();  void OnPreset1();  void OnPreset2();  void OnPreset3();  void OnPreset4();
	void OnNextPreset();  void OnToggleRecord();  void OnTogglePlay();
	void ApplyPresetIndex(int32 Index);            // GetTimeOfDay()->ApplyPreset(GetCycle()[Index]); 범위 밖이면 Warning
	UGolmokDebugSubsystem* GetDebugSubsystem() const;
	UPROPERTY(Transient) TObjectPtr<UInputMappingContext> DebugMappingContext;
	UPROPERTY(Transient) TObjectPtr<UInputAction> HudAction;         // F1
	UPROPERTY(Transient) TObjectPtr<UInputAction> CollisionAction;   // F2
	UPROPERTY(Transient) TObjectPtr<UInputAction> Preset1Action;     // One
	UPROPERTY(Transient) TObjectPtr<UInputAction> Preset2Action;     // Two
	UPROPERTY(Transient) TObjectPtr<UInputAction> Preset3Action;     // Three
	UPROPERTY(Transient) TObjectPtr<UInputAction> Preset4Action;     // Four
	UPROPERTY(Transient) TObjectPtr<UInputAction> NextPresetAction;  // F5
	UPROPERTY(Transient) TObjectPtr<UInputAction> RecordAction;      // F9
	UPROPERTY(Transient) TObjectPtr<UInputAction> PlayAction;        // F10
	TWeakObjectPtr<AGolmokTimeOfDay> TimeOfDay;
};
```
| 키 | 액션(Boolean, `ETriggerEvent::Started`) | 동작 |
|---|---|---|
| F1 | `IA_GolmokHud` | `Debug->SetHudVisible(!IsHudVisible())` |
| F2 | `IA_GolmokCollision` | `Debug->SetCollisionVisible(!IsCollisionVisible())` |
| 1 / 2 / 3 / 4 (`EKeys::One..Four`) | `IA_GolmokPreset1..4` | `ApplyPresetIndex(0..3)` = `cycle[i]` |
| F5 | `IA_GolmokNextPreset` | `NextPreset()` |
| F9 | `IA_GolmokRecord` | 녹화 중이면 `StopRecording`, 아니면 `StartRecording(QuickPathName)` |
| F10 | `IA_GolmokPlay` | 재생 중이면 `StopPlayback("F10")`, 아니면 `StartPlayback(LastPathName.IsEmpty() ? QuickPathName : LastPathName, false)` |
생성 방식은 `GolmokCharacter::EnsureInputAssets`와 동일(`NewObject<UInputAction>(this, TEXT("IA_GolmokHud"))`, `ValueType = Boolean`, `DebugMappingContext = NewObject<UInputMappingContext>(this, TEXT("IMC_GolmokDebug"))`, `Context->MapKey(HudAction, EKeys::F1)`). `SetupInputComponent`: `Cast<UEnhancedInputComponent>(InputComponent)`(null이면 Error, 캐릭터와 같은 메시지) → `BindAction(HudAction, ETriggerEvent::Started, this, &AGolmokPlayerController::OnToggleHud)` ×9 — **프리셋 4개는 핸들러 4개**(가변 페이로드 오버로드의 템플릿 추론 위험 회피). `AddMappingContext`: `ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer())->AddMappingContext(DebugMappingContext, DebugMappingPriority)`; `bDebugKeysEnabled=false`면 추가하지 않는다(패키지 배포 시 ini로 끔). 재생 중 `AGolmokPathPawn`에 빙의해도 컨트롤러 바인딩·로컬 플레이어 컨텍스트는 유지되므로 F10으로 중단 가능.
`AGolmokGameMode::AGolmokGameMode()`: `DefaultPawnClass = AGolmokCharacter::StaticClass(); PlayerControllerClass = AGolmokPlayerController::StaticClass(); HUDClass = AGolmokHUD::StaticClass();`. `Golmok.Player.Movement` 테스트는 `InputKey`로 WASD만 보내므로 영향 없음.

### 6. `Config/DefaultGame.ini` 추가분
```ini
[/Script/UnrealEd.ProjectPackagingSettings]
+DirectoriesToAlwaysStageAsUFS=(Path="Golmok/Zones")
; WP-05: lighting_presets.json lives under Config/Golmok (Python and C++ read the same file); see runbook §9 if it is missing in a package.
+DirectoriesToAlwaysStageAsUFS=(Path="../Config/Golmok")
; WP-05: interior sublevels are streamed by package path (LoadLevelInstance), so no map references them; cook the whole zone tree.
+DirectoriesToAlwaysCook=(Path="/Game/Golmok/Zones")

[/Script/Golmok.GolmokTimeOfDay]
; Seconds for preset / interior-overlay transitions (0 = instant). Tick runs only while transitioning.
TransitionSeconds=2.0
; Relative to <Project>/Config unless absolute.
PresetsFile=Golmok/lighting_presets.json
; Applied instantly at BeginPlay; empty = keep the level's authored lighting until a key / golmok.tod is used.
InitialPreset=
InteriorPreset=interior
; Actor tag that pins which DirectionalLight / SkyLight / ExponentialHeightFog / PostProcessVolume the presets drive.
LightingActorTag=GolmokLighting

[/Script/Golmok.GolmokPortal]
; LevelInstance: ULevelStreamingDynamic::LoadLevelInstance by package path (default). NamedStreamingLevel: ULevelStreaming registered in the persistent level.
InteriorStreamingMode=LevelInstance
DebounceSeconds=0.25
UnloadDelaySeconds=3.0
TriggerHeightCm=250
CrossingHysteresisCm=10
MinCrossingIntervalSeconds=0.25
bStreamSublevel=True
bSwitchLighting=True

[/Script/Golmok.GolmokDebugSubsystem]
StatsWindowSeconds=2.0
StatsCapacity=2048
bSampleWhenHudHidden=True
RecordHz=10
PathFolder=Golmok/Paths
ScreenshotFolder=Screenshots/Golmok
ScreenshotMultiplier=2
CollisionDebugMaterialPath=/Engine/EngineDebugMaterials/WireframeMaterial.WireframeMaterial
bCollisionShowFlag=True
CollisionRefreshSeconds=1.0
HudTextRefreshSeconds=0.25
bHudOnAtStart=False
bHidePlayerDuringPlayback=True
QuickPathName=quick
PlaybackFov=80

[/Script/Golmok.GolmokHUD]
HudScale=1.0
MarginPx=16

[/Script/Golmok.GolmokPlayerController]
bDebugKeysEnabled=True
DebugMappingPriority=1
```
`test_ini_keys_match_config_uproperties`가 모든 `/Script/Golmok.*` 키 = `UPROPERTY(Config)`(**두 줄 선언**)를 강제한다. 스테이징 두 번째 줄 때문에 `test_default_game_ini_stages_zone_manifests…`의 `packaging.get("+DirectoriesToAlwaysStageAsUFS") == '(Path="Golmok/Zones")'`(RawConfigParser는 중복 키의 마지막 값만 보관)를 raw 텍스트 `'+DirectoriesToAlwaysStageAsUFS=(Path="Golmok/Zones")' in text` 검사로 바꾼다.

### 7. `Golmok.Build.cs`
```csharp
PrivateDependencyModuleNames.AddRange(new string[]
{
	// WP-05: RHIGetGPUFrameCycles() for the debug HUD's GPU ms (Debug/GolmokDebugSubsystem.cpp).
	// Remove together with GOLMOK_GPU_TIME_SOURCE if the symbol moved.
	"RHI"
});
```
그 외 없음: Enhanced Input·Json은 이미 있고, `AHUD::DrawText`/`UCanvas`·`ULevelStreaming(Dynamic)`·라이트/안개 컴포넌트·`APostProcessVolume`은 Engine, `GGameThreadTime/GRenderThreadTime`은 Core(`CoreGlobals.h`), `FCsvProfiler`는 `Exec` 문자열 경유라 헤더 불필요. `UnrealEd`(에디터 빌드 테스트) 유지.

### 8. 테스트

#### 8-1 `tools/tests/test_lighting_presets.py`(순수, `lighting_presets` 직접 import)
파일 존재·JSON 파싱(utf-8)·`schema_version == 1`·최상위 키 = `{schema_version, cycle, presets}`; `cycle == ["overcast_morning","clear_noon","golden_evening","night"]`, 각각 9키 전부·타입(`volumetric` bool, 나머지 number)·`RANGES`(yaw 반개구간); `set(presets) == {4개 + interior}`, 이름 정규식, 미지 키 없음; `interior`는 부분·`fog == 0.0`·`exposure_bias > 0`·cycle 밖; **값 회귀**: 4개 cycle 프리셋이 WP-04 시점 `lighting.py` 값과 동일(테스트 안 상수 dict); `parse_presets` 오류 케이스(키 누락, 범위 밖 `kelvin=100`, `schema_version=2`, cycle에 미지 이름, `interior.fog=0.1`, 미지 키) → `ValueError`에 프리셋명·키; C++ 대조: `Lighting/GolmokTimeOfDay.cpp`에 `TEXT("<key>")` 9키 + `TEXT("cycle")`·`TEXT("presets")`·`TEXT("schema_version")`; Python 대조: `lighting.py`에 `PRESETS = {`·`pitch=` 리터럴 없음, `lighting_presets` import 있음; ini `[/Script/Golmok.GolmokTimeOfDay] PresetsFile == Golmok/lighting_presets.json`, `InteriorPreset`이 JSON에 존재.

#### 8-2 `tools/tests/test_ue_stats_math.py` + `fixtures/ue/statsmath_driver.cpp`
`test_ue_geo_math.py` 골격 그대로(`_compiler()`, `-std=c++17 -Wall -Wextra -Werror -pedantic -I Source/Golmok/Debug`, 컴파일러 없으면 skip). 드라이버 명령:
| 명령 | 입력 | 출력 |
|---|---|---|
| `pct <p> <n> v×n` | 정렬 안 된 값 | `Percentile` |
| `stats <window> <n> dt game render gpu ×n` | 오래된 것부터 Push | `Frames AvgFps OnePct AvgFrameMs P99 AvgGame AvgRender AvgGpu HasGpu` |
| `ring <cap> <n> v×n` | | 용량 초과 후 `Size`와 최신 3개(덮어쓰기 검증) |
| `cycles <cycles> <spc>` | | ms |
| `fmt <value> <decimals>` | | `FormatFixed` |
| `pathfmt <name> <hz> <level> <created> <n> t x y z pitch yaw roll ×n` | | JSON 텍스트 |
| `pathparse` | stdin JSON | `version hz n` + 샘플 줄(`%.17g` 상당) 또는 `ERROR <msg>`(exit 3) |
| `pose <t>` | stdin JSON | `px py pz pitch yaw roll` |
| `angle <a> <b> <alpha>` | | `LerpAngleDeg` |
Python 검증: (a) 헤더 순수성(`#include "` 없음, `<>` ⊆ 허용 7개, `CoreMinimal/UCLASS/UE_LOG/std::min/std::max/printf/cstdio` 문자열 없음); (b) `pct` == `np.percentile(v, p)` 무작위 50벌 + n=1,2·중복; (c) `stats`: 무작위 dt(6~40 ms, 히치 200 ms 몇 개, 시드 고정) 30세트 × 창 0.5/2/10 s → 파이썬이 같은 창 규칙으로 자른 뒤 `len/sum`, `np.percentile(1/dt, 1)`, `np.percentile(1000·dt, 99)`, 평균, `HasGpu` 1e-9 이내; `test_perf_report.py`의 히치 배열(1% low ≈ 30)도 재사용; (d) `fmt`: 격자값·음수·0·큰 값이 `f"{v:.{d}f}"`와 동일(tie 없는 입력), `-0.00` 대신 `0.00`; (e) `pathfmt` → `json.loads` 성공·키 순서·값 1e-6·`hz` 정수; (f) `pathparse`: `json.dumps(indent=2)`·키 순서 섞기·미지 키 `"note"`·`hz: 10.0` 표기 입력 → 같은 샘플; `version: 2`·비단조 `t`·잘린 텍스트 → exit 3 + `ERROR`; (g) 왕복 `pathparse(pathfmt(x)) == x`(격자 입력, 정확히 동일); (h) `pose` vs `np.interp` + 각도 unwrap 무작위 200건, 경계(t<첫, t>끝, 단일 샘플), yaw 170→−170이 −180을 지나 20° 회전; (i) `angle`.

#### 8-3 `test_ue_zone_fixture.py`(변경 2곳) + `test_ue_wp05_fixture.py`(신규)
- `test_ue_zone_fixture.py`: `_headers("Geo", "Zones")` → `_headers("Geo", "Zones", "Lighting", "Portals", "Debug", "Player")`, 소스 규약 parametrize도 같은 폴더(루트 `GolmokGameMode.cpp`·`Tests/`는 기존대로 제외); 스테이징 단언 raw-text.
- `test_ue_wp05_fixture.py`: Build.cs `"RHI"`; ini 5개 새 섹션 존재 + §6 키 집합 정확히 일치, `InteriorStreamingMode ∈ {LevelInstance, NamedStreamingLevel}`, `UnloadDelaySeconds > DebounceSeconds > 0`, `RecordHz >= 1`, `StatsWindowSeconds > 0`, `TransitionSeconds >= 0`, `ScreenshotFolder == Screenshots/Golmok`, `+DirectoriesToAlwaysStageAsUFS` 두 줄·`+DirectoriesToAlwaysCook` 한 줄 raw-text; `GolmokGameMode.cpp`에 `PlayerControllerClass = AGolmokPlayerController::StaticClass()`·`HUDClass = AGolmokHUD::StaticClass()`; `Tests/*.cpp`에 8개 테스트 이름 문자열 + `WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR` 가드; 전 소스에 `Cesium`·`XGRIDS` 문자열 없음(플러그인 컴파일 의존 금지); `Debug/GolmokStatsMath.h` 순수성(8-2와 함수 공유); `GolmokDebugSubsystem.cpp`에 `GOLMOK_GPU_TIME_SOURCE`·`OnEndFrame` 문자열; `GolmokZoneSubsystem.cpp`가 WP-04 커밋과 동일(diff 0 — `git`이 아니라 파일 해시를 상수로; 의도적 변경 시 함께 갱신); `GolmokPortal.h`에 `AGolmokZone`을 상속하지 않음(`class GOLMOK_API AGolmokPortal : public AActor`).

#### 8-4 가짜 `unreal` 테스트
- `test_ue_python_lighting.py`: `sys.modules["unreal"] = types.ModuleType("unreal")`(기존 fixture 재사용)로 `golmok.lighting` import 성공; `lighting.presets()`가 `lighting_presets.load_presets()`와 동일; `lighting.cycle()`; `apply()`의 부분 프리셋 분기는 `_first`·`get_all_level_actors`를 스텁해 `interior`가 sun/sky 세터를 호출하지 않고 fog/ppv만 호출함을 기록으로 확인.
- `test_ue_python_synthetic_zone.py` 확장: `synthetic_geometry(manifest)` 기본 결과 불변; `synthetic_geometry(manifest, openings=door_openings(manifest))`: chunk_01·충돌 박스에 x 3.5~6.5·z 0~2.2 문 구멍(프로브 (5, 9.9, 1.0)에 solid 없음), x=0 벽은 있음, 기존 glass 구멍 유지; `interior_geometry(int_manifest)` → `SM_room`(바닥 `(-4,-3,-0.2)-(4,3,0)`, 서벽 `(-4,-3,0)-(-3.8,3,3)`, 동벽 `(3.8,-3,0)-(4,3,3)`, 북벽 `(-4,2.8,0)-(4,3,3)`, 천장 `(-4,-3,3)-(4,3,3.2)`; **남쪽은 파사드 chunk_01이 벽**) + 같은 박스의 충돌; 모든 박스가 `room` bbox 안(천장·바닥 두께 허용); `sublevel_actor_specs(int_manifest)`(PointLight 실내-local UE (0, 0, 250) cm 3000 cd 3000 K, 마커 큐브 (0, 0, 150) 50 cm) 방 안.

#### 8-5 `test_ue_interior_fixture.py`
`tools/scripts/make_interior_fixture.py`의 `build()`를 import해 재생성한 dict가 커밋된 JSON(Content·tests/fixtures 둘 다)과 동일; `schema.validate == []`, `zm.check` 오류·경고 0; `kind == "interior"`, `parent_zone == "z_synthetic_001"`, `portals[0].id == "door_out"`, `to_zone == "z_synthetic_001"`; **포털 왕복 좌표**: 실외 `door_1` position (5, 9.5, 0)을 실외 `transform`으로 ECEF → 실내 `transform` 역행렬로 실내-local → `door_out` position (0, −3.5, 0)과 1e-6 m 이내, yaw 90 vs −90(반대 방향); 실내 origin이 실외 zone-local (5, 13, 0)(1e-6 m); 실내 footprint(8×6 m)가 실외 y 10~16에 붙어 있음; 실외 door_1이 chunk_01 bbox(x −7~7) 안(문 구멍이 chunk_01에 나야 하는 근거 고정).

#### 8-6 UE 자동화 테스트(`Source/Golmok/Tests/`, `WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR`, `EditorContext | ProductFilter`; PIE 테스트는 `FEditorLoadMap(L_Dev) → FStartPIECommand(false) → 시나리오 latent → FEndPlayMapCommand`; `.\tools\ue\test.ps1 -Filter Golmok. -SetupDevLevel`이 `-nullrhi`로 실행)
| 이름 | PIE | 단계·단언 |
|---|---|---|
| `Golmok.Lighting.PresetsFile` | 아니오 | `AGolmokTimeOfDay::LoadPresetsFile(FPaths::ProjectConfigDir()/Golmok/lighting_presets.json)` 성공, 5개, cycle 4개, `overcast_morning.Lux==2.5`·`IsComplete()`, `interior.bHasSun==false`·`Fog==0`; 깨진 텍스트·`schema_version 2`·`interior.fog 0.1`은 false + Error 비어있지 않음 |
| `Golmok.Lighting.PresetApply` | L_Dev | `FindOrSpawn` 존재; `ApplyPreset("clear_noon", true)` → `CaptureState`: `Lux≈10`, `Kelvin≈5600`, `Fog≈0.015`, `ExposureBias≈0`, `SunRotation.Pitch≈−62`; `TransitionSeconds=0.2`로 `ApplyPreset("night")` → **0.6 s 뒤 끝값만** 단언(`Lux==0`, `Sun visible false`, `bVolumetric true`, `!IsTransitioning()`, `IsActorTickEnabled()==false`); `EnterInterior("t")` → 0.6 s 뒤 `Fog==0`·`ExposureBias==1.0`·태양 회전은 night 그대로·`IsInterior()`; 실내에서 `ApplyPreset("clear_noon")` → 0.6 s 뒤 `Lux≈10`·`Fog==0`(오버레이 유지); `ExitInterior("t")` → 0.6 s 뒤 `Fog≈0.015`; `NextPreset()` → `golden_evening`. L_Dev 조명은 `setup_dev_level`이 만듦(태그 있음). nullrhi 무관(컴포넌트 값만 검사) |
| `Golmok.Debug.StatsMath` | 아니오 | dt 배열(590×1/60, 10×1/30)로 `AvgFps≈59.0`, `OnePercentLowFps==30.0`(numpy와 같은 손계산 상수), `Percentile` n=1·2, 창 절단, `CyclesToMs(1000, 1e-6)==1.0`, `FormatFixed(-0.004, 2)=="0.00"`·`FormatFixed(1234.5678, 2)=="1234.57"` |
| `Golmok.Debug.PathFormat` | 아니오 | 3샘플 `CameraPath` → `FormatPathJson`이 고정 리터럴(§4-4 예시와 같은 샘플)과 동일 → `ParsePathJson` 왕복 동일; `SavePathFile/LoadPathFile`(`<Saved>/Golmok/Paths/_automation_fmt.json`) 왕복; 끝에 파일 삭제 |
| `Golmok.Debug.PathRoundTrip` | L_Dev | `StartRecording("_automation_rec")` → 1.2 s → `StopRecording` → 파일 존재·`Samples.Num()>=10`·`Duration()>=1.0`; `StartPlayback("_automation_rec", false)` → `IsPlaying()`, `PC->GetPawn()`이 `AGolmokPathPawn`, `PC->GetViewTarget()==PathPawn`, 캐릭터 `IsHidden()`; `Duration+0.5` s 뒤 `!IsPlaying()`, `PC->GetPawn()`이 `AGolmokCharacter`, 숨김 복원, 재생 폰 `IsPendingKillPending`; 파일 삭제. `--csv`는 켜지 않는다 |
| `Golmok.Debug.HudStats` | L_Dev | `PC->GetHUD()->IsA<AGolmokHUD>()`; `SetHudVisible(true)` → 1.0 s → `GetStats`: **`Frames>=10` 필수**(OnEndFrame은 nullrhi에서도 발화), `AvgFps>0`, `0<OnePercentLowFps<=AvgFps*1.001`, `AvgGameMs>=0`, `AvgRenderMs>=0`, `AvgGpuMs>=0`(`HasGpu`는 검사하지 않고 로그만), 값 유한; `PushFrameSample` 20회(1/60 ×19 + 0.1)로 `FormatStatsLine()`에 `1% low` 예상값 문자열; `IConsoleManager::Get().ProcessUserConsoleInput(TEXT("golmok.hud 0"), *GLog, World)` 후 `IsHudVisible()==false`; `golmok.stats` 실행이 로그에 `stats: fps` 출력(로그 캡처 대신 `FormatStatsLine()` 비어있지 않음) |
| `Golmok.Portal.SpawnFromManifest` | L_Dev | `SpawnActor<AGolmokZone>` `ZoneId=z_synthetic_001, Version=1` → `Load()`(에셋 없음: 와이어 박스만, 성공) → `GetPortalActors().Num()==1`, `Cast<AGolmokPortal>`, `PortalId=="door_1"`, `TargetZoneId=="z_synthetic_001_interior"`, `RadiusCm==150`, `bIsEntry`, zone 기준 상대 위치 (500, −950, 0)·yaw −90 (1e-3), `Trigger` extent (150, 150, 125), `SublevelPackagePath=="/Game/Golmok/Zones/z_synthetic_001_interior/v1/L_z_synthetic_001_interior"`; `Unload()` → `GetPortalActors()` 비고 액터 `IsPendingKillPending`. 원점 없음 Warning 무시 |
| `Golmok.Portal.RoundTrip` | L_ZoneTest(있을 때만; 없으면 `AddInfo("skipped: run synthetic_zone.run(interior=True)")` 후 성공) | `FindPortal("door_1")`; `EnterInterior` → 2 s 안에 `IsSublevelVisible()`, `FindZone("z_synthetic_001_interior")->IsLoaded()`, `TimeOfDay->IsInterior()`; `LeaveInterior` → `!IsInterior()`; `UnloadDelaySeconds+1` s 뒤 sublevel unloaded·zone unloaded·`State==Idle` |

### 9. `synthetic_zone.py interior=True`

#### 9-1 실내 픽스처(커밋, `tools/scripts/make_interior_fixture.py build()`)
- `zone_id=z_synthetic_001_interior`, `version=1`, `kind=interior`, `parent_zone=z_synthetic_001`, `priority=20`.
- origin = 실외 zone-local (5, 13, 0) m → `transform.enu_to_lonlat`로 lat/lon, 높이 50(실외와 같음), yaw 0 → `zone_transform(lat, lon, 50, 0)`; `origin_ecef`는 transform 이동 성분. footprint = origin 중심 8×6 m 직사각형(`zone_util.rect_footprint` 방식) → 실외 y 10~16.
- `layers.visual = {format: nanite_mesh, chunks: [{id: "room", uri: "visual/room.glb", bbox_enu: [[-4,-3,0],[4,3,3.2]], tris: 60}]}`, `collision = {format: glb, uri: "collision.glb"}`, blockers·navmesh 없음.
- `portals = [{id: "door_out", to_zone: "z_synthetic_001", pose_enu: {position: [0, -3.5, 0], yaw_deg: -90}, radius_m: 1.5, kind: "door"}]` — 실외 `door_1`(5, 9.5, 0; yaw 90)과 같은 점, 반대 방향.
- `replaces {building_ids: [], terrain_clip: false}`, `quality` null 4개, `consent {type: owner_consent, record_id: "synthetic-consent-001"}`, `attribution ["합성 테스트 데이터 (WP-05)"]`, `sources [{capture_id: "synthetic", note: "실내 테스트 픽스처, 실촬영 아님"}]`.
- 이유: 실내를 **자기 원점을 가진 진짜 zone**으로 두면 `RequestLoad/RequestUnload`, `SpawnPortals`(마커), 부모-자식 정리, `golmok.zone.list`, 그리고 실 파이프라인과 같은 "다른 원점" 코드 경로가 전부 검증된다. 서브레벨은 manifest 밖의 것(조명·소품)을 담는 자리.

#### 9-2 `run(geo_origin="area", move_player_start=True, import_assets=True, level=ZONE_TEST_MAP, interior=False)`
`interior=True`일 때 기존 단계 뒤에:
1. `_import_assets(manifest, work_dir, openings=door_openings(manifest))`: `DOOR_HEIGHT_M = 2.2`, kind `door` 포털마다 `x ∈ [px−r, px+r]`(door_1: 3.5~6.5)·`z ∈ [0, 2.2]` 구멍을 파사드 chunk_01(y 9.8~10.0)과 충돌 메시에 뚫어 재임포트(`chunk_boxes(..., openings)` 일반화; 기존 glass 구멍 상수는 그대로). `interior=False`면 형상 불변(WP-04 런북 수치 유지).
2. 실내 manifest 로드 → `_import_interior_assets`: `interior_geometry` 박스를 같은 2-pass(pretransform·complex collision·Nanite 끔) 파이프라인으로 `/Game/Golmok/Zones/z_synthetic_001_interior/v1/SM_room`, `SM_z_synthetic_001_interior_collision`.
3. `find_or_spawn_zone("z_synthetic_001_interior", 1)` → `rebuild_in_editor()`(에디터에서 방·마커 포털 확인) → `unload_in_editor()`(PIE는 포털이 로드). 기대 로그 `Zone z_synthetic_001_interior: portal door_out -> z_synthetic_001 rel (0, 350, 0) cm yaw 90.0 radius 150 cm -> level (18170.57, -23148.01, 999.32) [marker]`.
4. 서브레벨: `save_current_level()` → `LevelEditorSubsystem.new_level("/Game/Golmok/Zones/z_synthetic_001_interior/v1/L_z_synthetic_001_interior")` → 실내 zone 액터 트랜스폼 `t`로 `t.transform_location(...)`한 **레벨 좌표**에 PointLight(`Interior_Light`, 방 중심 z 250 cm, 3000 cd, 3000 K)와 큐브 `Interior_Marker`(50 cm, 방 중심 z 150 cm, `WorldGridMaterial`, 충돌 없음) 스폰 → `save_current_level()` → `load_level(ZONE_TEST_MAP)`. 서브레벨에는 `AGolmokZone`·PostProcessVolume·DirectionalLight를 넣지 않는다.
5. PlayerStart 그대로(슬래브 위, 문에서 남서쪽 약 10 m, 트리거 밖).
6. 로그 `synthetic_zone: interior ready — sublevel <path> (level coordinates), zone actor Zone_z_synthetic_001_interior (unloaded until door_1)`.
- **`register_interior_sublevel()`**(별도 함수, `NamedStreamingLevel` 검증용): `unreal.EditorLevelUtils.add_level_to_world(world, path, unreal.LevelStreamingDynamic)` → `set_editor_property("initially_loaded", False)`·`("initially_visible", False)` → 저장. 예외면 `log_warning("could not register the sublevel; add it in Window > Levels, or keep InteriorStreamingMode=LevelInstance")`. 기본 `run()`은 등록하지 않는다 → 기본 경로가 실제로 `LoadLevelInstance`를 탄다.

#### 9-3 런북이 보는 것
문(x=+5 m, 슬래브 북쪽 끝)을 향해 북진 → 1.5 m 안에서 HUD `zones` 줄에 실내 zone `loaded pinned`, `portals` 줄 `active`, 어두운 방 안에 마커 큐브·PointLight(서브레벨 스트림 인) → 문 평면 통과 → `crossed inward`, 2 s 동안 안개 0·노출 +1 EV(HUD `tod: … [interior: door_1]`) → 방 안 보행(벽 충돌) → 되돌아 나오면 `crossed outward`·오버레이 off → 박스 이탈 3 s 뒤 언로드·서브레벨 사라짐. 3 s 안에 재진입하면 언로드 로그 없음.

### 10. 런북 `docs/runbooks/pc-verify-wp05.md` 골자
0. 대상 파일 표(§1) · 전제: WP-04 런북 §1~§2 통과, `L_Dev`·`L_ZoneTest` 존재.
1. **빌드**: `git pull`, `.\tools\ue\build.ps1` — [ ] 컴파일 성공(실패 시 §11 표 번호로 고치고 `WP-05: PC fix` 커밋); [ ] `.\tools\ue\test.ps1 -Filter Golmok. -SetupDevLevel` → `Golmok.Player.Movement` + 8개 전부 `Success`(`Portal.RoundTrip`는 2 전에는 `skipped`).
2. **합성 실내 생성**: `import golmok.synthetic_zone as z; z.run(interior=True)` — 기대 로그: `SM_chunk_01 … bounds ok`(문 구멍 재임포트), `…/z_synthetic_001_interior/v1/SM_room … bounds ok`, `Zone z_synthetic_001: portal door_1 … [entry]`, `Zone z_synthetic_001_interior: portal door_out … [marker]`, `interior ready`. 체크: 아웃라이너 `Portal_z_synthetic_001_door_1`·`Zone_z_synthetic_001_interior`, 콘텐츠 브라우저 `L_z_synthetic_001_interior`. 그 뒤 `test.ps1`을 다시 돌려 `Golmok.Portal.RoundTrip` `Success`.
3. **PIE 조명**: [ ] 시작 로그 `TimeOfDay: presets loaded (5) from …`(레벨 조명 그대로); [ ] 1/2/3/4 키마다 2 s 전환·HUD `tod:` 진행률, 4(night)에서 태양 꺼짐·볼류메트릭; [ ] 전환 중 다른 키 → 튐 없이 재출발; [ ] F5 순환; [ ] `golmok.tod list` 5개; [ ] `golmok.tod bogus` → `ERROR unknown preset`; [ ] 에디터 `import golmok.lighting as l; l.apply("golden_evening")`와 PIE `golmok.tod golden_evening` 화면 대조(같은 값).
4. **PIE HUD·좌표**: F1 → 줄(§4-8); [ ] fps·1% low가 `stat fps`와 ±5%; [ ] game/render/gpu ms가 `stat unit`과 ±0.5 ms(gpu 0 아님); [ ] `pos` 줄 lat/lon ≈ 37.56196/126.92500(PlayerStart), ENU ≈ (176.7, 217.0, 11.2); [ ] `zones` 줄 = `golmok.zone.list`; [ ] `golmok.stats` 로그가 HUD 값과 같음; [ ] `golmok.hud 0`.
5. **PIE 포털 왕복**(§9-3): 기대 로그 순서 `Portal door_1 (…): player within 150 cm -> load [zone z_synthetic_001_interior loaded (pinned)]; sublevel … (LevelInstance)` → `Zone z_synthetic_001_interior v1 loaded …, portals 1 (WP-05)` → `Portal door_1: crossed inward` → `TimeOfDay: interior overlay on (source door_1, base …)` → (나감) `crossed outward` → `interior overlay off -> …` → 3 s 뒤 `Portal door_1: player left -> unload z_synthetic_001_interior; sublevel out` → `Zone … unloaded`. [ ] 문 앞에서 멈췄다가 물러나면 로드→3 s 뒤 언로드만(노출 변화 없음). [ ] 3 s 안 재진입 시 언로드 없음. [ ] `golmok.portal list`; `golmok.portal enter door_1`/`leave door_1`로 같은 로그. [ ] **음성 테스트**: 아웃라이너에서 `Zone_z_synthetic_001_interior` 삭제 후 왕복 → `Warning … no AGolmokZone … sublevel only` 1회, 서브레벨·노출 전환은 계속 동작. [ ] **경로 B**: `z.register_interior_sublevel()` + `DefaultGame.ini` `InteriorStreamingMode=NamedStreamingLevel` → PIE 재시작 → 같은 결과, 로그 `(NamedStreamingLevel)`; 되돌림.
6. **PIE 충돌 표시**: F2 → 충돌 슬래브·파사드 충돌 메시 와이어(또는 회색), blocker 청록 박스, 포털 초록 박스, 베이스맵 큐브 충돌(show flag); 실내 진입 후 1 s 안에 실내 충돌도 와이어; F2 → 원복. `golmok.collision 1` 동일.
7. **PIE 경로·CSV**: `golmok.path record walk_01` → **3 s 제자리** → 문 왕복 포함 ≈60 s 보행 → `golmok.path stop` → 로그 `path 'walk_01' saved: ~600 samples`, `Saved\Golmok\Paths\walk_01.json`(`"version": 1`); `golmok.path play walk_01 --csv` → HUD `path: play … [csv]`, 캐릭터 숨김, 카메라가 경로를 따라감, **[ ] 포털이 재생 중에도 반응**(실내 로드·`crossed inward` 로그·노출 전환), 끝나면 캐릭터 복귀·로그 `csv: <path> -> golmok-perf "<path>" --label walk_01 --markdown`; PowerShell에서 그 명령 실행 → 표 출력(프레임 ≈ 60 s × fps). [ ] F9/F10 `quick` 경로. 참고: 재생 중 캐릭터 애니메이션이 빠져 Game ms가 실제보다 약간 낮다.
8. **스크린샷**: `golmok.screenshot wp05 door` → `Saved\Screenshots\Golmok\wp05\<preset>\door.png` 2배 해상도(HUD 없음).
9. **패키징(선택)**: `package.ps1` → `open L_ZoneTest` → `golmok.tod list` 5개(JSON 스테이징 확인; 없으면 §11 #29 대안) + 포털 왕복(서브레벨 쿠킹 확인).
10. **PIE 종료**: 에러·ensure 없음, 오버레이 잔류 없음.
11. **컴파일 에러가 나면** — §11 표 그대로(번호 유지).
12. **결과 기록** 표(빌드·테스트 8·§2~§10 각 행·고친 API 번호·커밋 해시), STATUS `🟡` 갱신 지시.

### 11. 불확실한 UE 5.8 API와 대안 (런북 §11 표 그대로)
| # | 파일 | API | 불확실한 점 | 대안 |
|---|---|---|---|---|
| 1 | GolmokLevelStreaming | `ULevelStreamingDynamic::LoadLevelInstance(UObject* WorldContext, const FString& LevelName, const FVector&, const FRotator&, bool& bOutSuccess, const FString& OptionalLevelNameOverride)` | 5.4+ `FLoadLevelInstanceParams` 오버로드 추가·구 시그니처 deprecated 가능 | ① `ULevelStreamingDynamic::FLoadLevelInstanceParams Params(World, PackagePath, FTransform::Identity); Params.OptionalLevelNameOverride = …; LoadLevelInstance(Params, bOk)` ② `LoadLevelInstanceBySoftObjectPtr(World, TSoftObjectPtr<UWorld>(FSoftObjectPath(PackagePath + TEXT(".") + ShortName)), FVector::ZeroVector, FRotator::ZeroRotator, bOk)` ③ ini `InteriorStreamingMode=NamedStreamingLevel` |
| 2 | GolmokLevelStreaming | `UWorld::GetStreamingLevels()`, `ULevelStreaming::GetWorldAssetPackageName()`, `SetShouldBeLoaded/SetShouldBeVisible`, `IsLevelLoaded/IsLevelVisible` | 이름 유지 여부(4.x부터 안정) | `GetWorldAssetPackageFName().ToString()`, `GetLoadedLevel() != nullptr`, `GetLevelStreamingState() == ELevelStreamingState::LoadedVisible` |
| 3 | GolmokLevelStreaming | `ULevelStreaming::SetIsRequestingUnloadAndRemoval(true)` | 존재 여부 | 줄 삭제(언로드만, 목록에 남음) |
| 4 | GolmokLevelStreaming | `FPackageName::DoesPackageExist(const FString&)` | 오버로드 기본 인자 | `DoesPackageExist(Path, nullptr)`; 쿠킹 빌드에서 의심되면 검사 생략 |
| 5 | GolmokPortal | `UBoxComponent::OnComponentBeginOverlap.AddDynamic`(6인자) / `OnComponentEndOverlap`(4인자) | 안정 | 오류 메시지의 `FComponentBeginOverlapSignature` 형에 맞춤; 초기 오버랩 누락이 보이면 바인딩을 생성자로 이동 |
| 6 | GolmokPortal | `UPrimitiveComponent::IsOverlappingActor(const AActor*)` | 안정 | `GetOverlappingActors(Out, APawn::StaticClass())` 후 검색 |
| 7 | GolmokPortal | `SetCollisionProfileName(TEXT("OverlapOnlyPawn"))` | 엔진 기본 프로필 존재 | `SetCollisionResponseToAllChannels(ECR_Ignore); SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap)` |
| 8 | GolmokPortal | `GetActorForwardVector()`가 `UE Yaw = -yaw_deg` 기준 "들어가는 방향"인지 | 규약(스펙 §5)·부호 | 런북 5에서 `crossed inward`가 반대로 찍히면 `SignedDistanceAlongForward` 부호 반전 |
| 9 | GolmokPortal | `UPROPERTY(Config) EGolmokInteriorStreamingMode`(enum class) ini 텍스트 파싱 | 안정(이름으로 직렬화) | `FString InteriorStreamingModeName` + 파싱 |
| 10 | GolmokPortal | `FTimerManager::SetTimer(Handle, this, &Class::Method, float, bool)`, `ClearTimer` | 안정 | `FTimerDelegate::CreateUObject` |
| 11 | GolmokPortal | 컴포넌트 파괴 시 `OnComponentEndOverlap` 발화 여부 | 엔진 동작 | 핸들러 첫 줄 `if (!IsValid(this) \|\| IsActorBeingDestroyed()) return;`(이미 있음) |
| 12 | GolmokZone | `FActorSpawnParameters::bDeferConstruction`, `ObjectFlags`, `SpawnCollisionHandlingOverride` + `FinishSpawning(T)` | 안정(4.x) | `SpawnActor` 후 `Configure()`·`Trigger->UpdateOverlaps()`, `bIsEntry`를 `BeginPlay`에서 재해석 |
| 13 | GolmokZone/Portal | `AActor::SetActorLabel`(`#if WITH_EDITOR`) | 안정 | 줄 삭제 |
| 14 | GolmokTimeOfDay | `FJsonObject::TryGet{Object,Number,Bool,Array}Field(const FString&, …)` | WP-04 #0과 동일(리터럴 모호) | 키를 `const FString` 객체로(설계 그대로); `GetField<EJson::…>` |
| 15 | GolmokTimeOfDay | `ULightComponent::SetIntensity`, `SetUseTemperature(bool)`, `SetTemperature(float)` | 세터 존재(4.x~) | `Comp->bUseTemperature = true; Comp->Temperature = K; Comp->MarkRenderStateDirty()` |
| 16 | GolmokTimeOfDay | `UExponentialHeightFogComponent::SetFogDensity/SetFogHeightFalloff/SetVolumetricFog` | 안정 | 멤버 대입 + `MarkRenderStateDirty()` |
| 17 | GolmokTimeOfDay | `USkyLightComponent::SetIntensity`, `RecaptureSky()`, `bRealTimeCapture` | 접근 권한 | `RecaptureSky` 줄 삭제(L_Dev는 real-time capture) |
| 18 | GolmokTimeOfDay | `APostProcessVolume::Settings.bOverride_AutoExposureBias / AutoExposureBias`, `bUnbound` | public 멤버(안정) | 컴파일 오류면 이름 확인 |
| 19 | GolmokTimeOfDay | `AActor::FindComponentByClass<UDirectionalLightComponent>()` | 안정 | `ADirectionalLight::GetComponent()` |
| 20 | GolmokTimeOfDay | `SetActorTickEnabled(bool)`, `PrimaryActorTick.bStartWithTickEnabled` | 안정 | 30 Hz 타이머(`SetTimer(…, 1.f/30, true)`)로 전환 |
| 21 | GolmokTimeOfDay | `FQuat::Slerp(A, B, Alpha)` | 안정 | `FMath::Lerp`로 각도 개별 보간 |
| 22 | GolmokDebugSubsystem | `FCoreDelegates::OnEndFrame.AddUObject` / `.Remove(Handle)` | 안정(Core) | `UTickableWorldSubsystem`(`Tick`, `GetStatId` `RETURN_QUICK_DECLARE_CYCLE_STAT`, `Super::Tick`) |
| 23 | GolmokDebugSubsystem | `FApp::GetDeltaTime()`(`Misc/App.h`) | 안정 | `FPlatformTime::Seconds()` 차이(첫 샘플 버림) |
| 24 | GolmokDebugSubsystem | `GGameThreadTime`, `GRenderThreadTime`(`CoreGlobals.h`, `CORE_API uint32`) | 선언 헤더 | `#include "Stats/Stats.h"`; 링크 오류면 `extern CORE_API uint32 GGameThreadTime;` 직접 선언; 최후 0 표시 |
| 25 | GolmokDebugSubsystem | `RHIGetGPUFrameCycles()`(`RHI.h`, uint64; `uint32 GPUIndex = 0` 인자 가능) | 5.8 유지 여부·모듈 `RHI` | `GGPUFrameTime`(RHI 전역 uint32); 최후 `#define GOLMOK_GPU_TIME_SOURCE 0` + Build.cs `"RHI"` 제거(GPU n/a) |
| 26 | GolmokDebugSubsystem | `FPlatformTime::GetSecondsPerCycle()` | 안정 | `FPlatformTime::ToMilliseconds64(uint64)` / `ToMilliseconds(uint32)` |
| 27 | GolmokDebugSubsystem | `GEngine->Exec(World, TEXT("CsvProfile Start"))`가 PIE에서 CSV 프로파일러에 닿는지 | Exec 라우팅 | `#include "ProfilingDebugging/CsvProfiler.h"` → `FCsvProfiler::Get()->BeginCapture(-1, FPaths::ProfilingDir() / TEXT("CSV")); EndCapture();`(`#if CSV_PROFILER`) |
| 28 | GolmokDebugSubsystem | `HighResShot 2 filename="<path>"` 파일명 옵션 | `filename=` 파싱·확장자·경로 처리 | `GetHighResScreenshotConfig().SetResolution(w, h, 2.f)` + `FScreenshotRequest::RequestScreenshot(Path + TEXT(".png"), false, false)`(`UnrealClient.h`) |
| 29 | DefaultGame.ini | `+DirectoriesToAlwaysStageAsUFS=(Path="../Config/Golmok")` | Content 밖 상대경로 허용 여부 | JSON을 `Content/Golmok/Lighting/`로 복사 + `+DirectoriesToAlwaysStageAsUFS=(Path="Golmok/Lighting")` + `PresetsFile`을 `Content/` 기준 경로로(코드는 `Config/`·`Content/` 접두를 인식해 `FPaths::ProjectDir()`와 결합); 테스트 함께 수정 |
| 30 | DefaultGame.ini | `+DirectoriesToAlwaysCook=(Path="/Game/Golmok/Zones")` 형식 | `Path` 값 형식(`/Game/…` vs 상대) | `+MapsToCook=(FilePath="/Game/Golmok/Zones/z_synthetic_001_interior/v1/L_z_synthetic_001_interior")` |
| 31 | GolmokDebugSubsystem | `UGameViewportClient::EngineShowFlags.SetCollision(bool)`, `World->GetGameViewport()` | 접근 권한·setter 이름 | `GEngine->Exec(World, TEXT("show collision"))`(토글, 자체 bool로 동기) 또는 `bCollisionShowFlag=False` |
| 32 | GolmokDebugSubsystem/GolmokZone | `GEngine->WireframeMaterial`(`UMaterial*`, public UPROPERTY) | public 여부 | `CollisionDebugMaterialPath.TryLoad()`만(이미 2순위); 그것도 없으면 머티리얼 교체 생략 |
| 33 | GolmokDebugSubsystem | `APlayerController::Possess/UnPossess`, `SetViewTargetWithBlend(AActor*, float)`, `GetViewTarget()`, `RestartPlayer` | `Possess`가 뷰타깃을 자동 전환하는지 | `SetViewTargetWithBlend` 명시 호출(이미 설계); 실패 시 `SetViewTarget` |
| 34 | GolmokPathPawn | `USphereComponent::SetCollisionObjectType(ECC_Pawn)`, `SetCollisionResponseToChannel(ECC_WorldDynamic, ECR_Overlap)`, `SetGenerateOverlapEvents` | 안정 | `SetCollisionProfileName(TEXT("Pawn"))` 후 `SetCollisionEnabled(QueryOnly)` |
| 35 | GolmokDebugSubsystem | `IFileManager::Get().FindFiles(Out, *Dir, TEXT("json"))`·`GetTimeStamp` | 오버로드·반환 순서 | `FindFilesRecursive`; 타임스탬프 비교로 최신 선택(이미 설계) |
| 36 | GolmokDebugSubsystem | `UWorld::GetMapName()` + `StreamingLevelsPrefix` 제거 | PIE 접두 처리 | `FPackageName::GetShortName(World->GetOutermost()->GetName())` |
| 37 | GolmokDebugSubsystem | `FDateTime::UtcNow().ToIso8601()`, `Now().ToString(TEXT("%Y%m%d_%H%M%S"))` | 안정 | `ToString()` 기본 |
| 38 | GolmokHUD | `AHUD::DrawText(const FString&, FLinearColor, float, float, UFont*, float Scale, bool)`, `DrawRect`, `GEngine->GetSmallFont()` | 안정 | `Canvas->DrawText(Font, Text, X, Y)`; `Canvas->TextSize` |
| 39 | GolmokPlayerController | `SetupInputComponent()`에서 `InputComponent`가 `UEnhancedInputComponent`(DefaultInput.ini) | 컨트롤러 생성 순서 | `BeginPlay`에서 재바인드 |
| 40 | GolmokPlayerController | `ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer())`가 `BeginPlay`에 유효한지 | 로컬 플레이어 순서 | `ReceivedPlayer()` 오버라이드에서 추가 |
| 41 | GolmokPlayerController | `EKeys::One..Four`, `EKeys::F1/F2/F5/F9/F10` | 이름 | `FKey(TEXT("One"))` |
| 42 | GolmokDebugSubsystem/GolmokZoneSubsystem | `UWorldSubsystem::DoesSupportWorldType` | WP-04 #1과 동일 | 오버라이드 삭제 + `ShouldCreateSubsystem`에서 `WorldType` 검사 |
| 43 | Tests | `IConsoleManager::Get().ProcessUserConsoleInput(Cmd, *GLog, World)` | 인자형 | `GEngine->Exec(World, Cmd)` |
| 44 | Tests | `FWaitLatentCommand(float)`(`Misc/AutomationTest.h`), `FEditorLoadMap/FStartPIECommand/FEndPlayMapCommand` | 안정(Character 테스트에서 사용) | `FDelayedFunctionLatentCommand` |
| 45 | synthetic_zone.py | `unreal.EditorLevelUtils.add_level_to_world(world, path, unreal.LevelStreamingDynamic)`, 반환 객체의 `initially_loaded/initially_visible` | Python 노출 이름 | `dir(level)`로 확인; 실패 시 Levels 창 수동 등록(런북 안내); 기본 경로(`LevelInstance`)는 무영향 |
| 46 | synthetic_zone.py | `LevelEditorSubsystem.new_level()`가 현재 레벨을 닫음 → 저장·재오픈 순서 | 동작 | `save_current_level()` 먼저(설계 그대로); 실패 시 `load_level` 재시도 |
| 47 | synthetic_zone.py | `unreal.CollisionEnabled.NO_COLLISION`, `StaticMeshComponent.set_collision_enabled` | enum 이름 | `set_editor_property("collision_enabled", …)`; 실패 시 충돌 그대로(중복 충돌 무해) |
| 48 | 전체 | World Partition 맵에서 `GetStreamingLevels()`·`LoadLevelInstance` 동작 | L_ZoneTest/L_Dev는 비-WP | `World->IsPartitionedWorld()`면 Warning 로그 |
| 49 | GolmokStatsMath.h | MSVC에서 `std::string`·`std::vector`·`std::llround`·`std::stod` 조합(UE 코드) | 안정 | `std::llround` → `std::floor(x + 0.5)` |

### 12. 위험·트레이드오프
1. **`LoadLevelInstance` 시그니처 불일치** — 가장 가능성 큰 컴파일 오류. 대안 3단(§11 #1)과 ini 우회(`NamedStreamingLevel`)가 준비됨. 명명 경로는 서브레벨 등록이 필요해 실내 N개면 퍼시스턴트 레벨 편집·LFS 잠금이 늘어나므로 우회 전용.
2. **부분 프리셋(interior)**: 스키마가 조금 복잡하지만 실내에서 태양 값을 "모르는" 문제를 정직하게 풀고 값 중복이 없다. 오버레이 기반이라 실내가 태양 그림자에 노출된 채 안개만 0이 되며, 실내의 진짜 어둡기는 서브레벨 조명 + 자동 노출에 맡긴다(품질 우선). 필요하면 `interior`에 키를 추가하는 것만으로 오버레이 범위가 넓어진다.
3. **Tick 기반 보간**: 전환 2 s 동안만 틱, 유휴 비용 0. 태양이 움직이는 동안 VSM/Lumen 캐시가 프레임마다 무효화되므로 스파이크 측정은 전환 구간을 피하거나 CSV 워밍업으로 제외한다(런북 §7·research/08에 명시).
4. **문 평면 판정의 부호**: `yaw_deg`가 "들어가는 방향"이라는 스펙 규약을 따르므로 실 데이터가 반대로 저작되면 오버레이가 뒤집힌다. 런북 §5가 즉시 드러내고 수정은 부호 하나. 장기적으로 `golmok-zone validate`가 포털 방향과 실내 footprint를 대조(WP-06/07 메모).
5. **선로드 반경 = 트리거 반경(1.5 m)**: 큰 실내는 로드 히치가 문 앞에서 보인다. `radius_m`를 키우면 문 평면 판정은 그대로(평면 기준)라 부작용이 없지만 스펙 값이 우선. 필요 시 `PreloadRadiusScale` 한 키로 확장 가능.
6. **언로드 지연 3 s + 디바운스 0.25 s**: 문 앞에서 서성여도 로드/언로드 스래싱이 없다. 실 Zone에서는 ini 튜닝.
7. **재생 폰 빙의**: 캐릭터가 컨트롤러 없이 남아 숨겨진다. 캐릭터 애니메이션이 프레임 비용에서 빠져 Game ms가 실제보다 약간 낮다(런북 명시). 재생 중 PIE 종료는 `Deinitialize`가 복원한다. 재생 종료 시 캐릭터가 서 있던 zone이 이미 언로드됐을 수 있다(잠깐 낙하 → `Zone_Ground`).
8. **HUD 1% low 창 2 s**: 샘플 수가 적어(120~600) 최저 1~6 프레임에 좌우되어 `golmok-perf`(60 s, 워밍업 제외)와 절대값이 다를 수 있다. 정의는 동일하며 HUD는 현장 눈금, CSV가 회귀 정본.
9. **CSV 파일 위치를 엔진에 맡김**: 파일명을 지정하지 않으므로 최신 파일을 고른다(로그에 명령까지 출력). `FCsvProfiler::BeginCapture(폴더, 파일명)`은 시그니처가 버전마다 달라 회피.
10. **순수 JSON 리더·포매터 자작**: 이 스키마 전용 ~200줄, g++·Python 교차검증으로 고정. 일반 JSON 재사용은 목표가 아니다.
11. **프리셋 파일이 Config 아래**: 에디터·PIE는 항상 읽지만 패키지 빌드는 스테이징 줄(§11 #29)에 의존. 실패해도 게임은 돌아가고 조명만 레벨 값 유지(Error 1회).
12. **실내 픽스처의 자기 원점**: 실 파이프라인과 같은 코드 경로를 검증하지만 픽스처 생성기(`make_interior_fixture.py`)와 좌표 왕복 테스트가 필요했다. 문 구멍 재임포트는 `interior=True`일 때만이라 WP-04 런북 수치는 그대로(단, 같은 맵에서 다시 실행하면 chunk_01에 문 구멍이 남는다 — WP-04 런북 §3 (3) 한 줄 수정).
13. **`Evaluate()` 포인터 안정성은 규약으로 보장**: 코드 방어(인덱스/약참조)는 넣지 않았다(WP-04 동작·테스트 무변경 우선). 리뷰 체크리스트에 "`Load()` 스택에서 `RegisterZone`을 부르는 경로 없음"을 항목으로 넣고, 서브레벨에 `AGolmokZone`을 넣지 않는 규약을 WP-06 인계에 적는다. 하드닝은 Zone Index 발견 경로(ARCHITECTURE §4-1)를 구현할 때 함께.
14. **`bSampleWhenHudHidden=True`**: 프레임당 double 4개 push(수십 ns)가 항상 든다. 측정 정확도·자동화 편의가 우선이고 ini로 끌 수 있다.
15. **에디터에서 포털 스폰(Transient)**: `RebuildInEditor` 때 아웃라이너에 나타나고 저장은 안 된다(WP-04 "빈 zone" 동작과 일치).

### 13. 구현·리뷰 중 확정 변경 (설계 대비)
적대적 리뷰 1차(`5f0db44`)와 2차(작업 트리, 같은 브랜치에 커밋)에서 코드가 §0~§12와 달라진 곳. §0~§12 본문은 원안 그대로 두었고, 아래 표가 우선한다(런북 `pc-verify-wp05.md`의 "설계와 다름:" 표시와 같은 내용). 전체 diff: `git diff 1f17fc4..HEAD` + 작업 트리.

| 항목 | 설계 | 구현(확정) | 이유 |
|---|---|---|---|
| 포털 루트 컴포넌트(§3-1 생성자) | 루트 = `UBoxComponent Trigger` | 루트 `USceneComponent`(`PortalRoot`) + 자식 `Trigger`(상대 Z = `TriggerHeightCm/2`); `GetTrigger()` 접근자 | 액터 위치가 문 바닥점(manifest 점)과 같아야 `SignedDistanceAlongForward`·로그 `level (…)`가 마커와 일치. 박스 오프셋을 루트에서 분리 |
| 플레이어 폰 판정(§3-1 `IsPlayerPawn`, 6단계) | 이벤트마다 `GetPlayerPawn(0) == Other` | BeginOverlap만 `IsPlayerPawn`; 이후는 `OverlappingPawn` 약참조로 추적(EndOverlap은 그 폰과 대조). `BeginPlay`에서 `APlayerController::OnPossessedPawnChanged.AddDynamic(OnPlayerPawnChanged)`(`BoundController`, EndPlay에서 해제) → `RefreshOverlap(NewPawn)`; `NewPawn == nullptr` 브로드캐스트(`Possess` 안의 `UnPossess`)는 무시. `Tick`도 추적 폰 ≠ 플레이어 폰이거나 오버랩이 사라졌으면 `RefreshOverlap` | 경로 재생 시작·종료가 트리거 이벤트 없이 플레이어 폰을 바꾼다(캐릭터↔`AGolmokPathPawn`); 옛 폰의 EndOverlap이 유실되면 오버랩이 영원히 남음 |
| 빙의 교체 후 실외 판정(신규) | 없음 | `RefreshOverlap`: 새 폰이 박스 밖·문 평면 바깥(d < 0)이고 `bPlayerInside`면 `SetInside(false)`; 추적 오버랩이 없고 Active면 `StartLeaving("player pawn outside after possession change")`, 추적 중이면 `EndPlayerOverlap()`의 바깥 이탈 경로 | 재생 폰이 방 안에서 끝나고 캐릭터(밖)로 복귀하면 오버레이·Active가 남는다(R2-runtime-01) |
| `EndPlay`(§3-1 6) | Active/Leaving일 때만 `StreamOut` + `ExitInterior`; `RequestUnload` 호출 안 함 | **항상** `ExitInterior(PortalId)`(소스 없으면 no-op). Active/Leaving이면 `StreamOut` + 월드가 살아 있으면(`!World->bIsTearingDown`, `EndPlayInEditor`/`Quit` 아님) `SetTimerForNextTick`으로 `RequestUnload(TargetZoneId)` 예약(`static UnloadInteriorAfterEndPlay()`) — 다른 entry 포털이 같은 실내에 Active/Leaving이면 건너뜀(`Portal door_1: gone; <zone> kept (another portal is active)`), Pending이면 `DebounceSeconds + 0.05` s 뒤 재판정(`Portal door_1: gone; unload of <zone> postponed 0.30 s (another portal is pending)`; R3-state-01). 로그 `Portal door_1: end play while active -> sublevel out; zone unload scheduled` → 다음 틱 `Portal door_1: gone -> zone <zone> unloaded (…)` | 핀된 실내는 WP-04 `Evaluate()`의 고아 규칙이 건너뛰므로 실외 언로드 뒤 실내가 누수. `Pending` 중에도 평면 통과로 소스가 생길 수 있다. 다음 틱으로 미루는 이유는 `DestroyPortals()`가 `Evaluate()` 스택 안일 수 있기 때문 |
| 디바운스 중 안쪽 이탈(§3-1 4) | `Pending`이면 디바운스 취소·`Idle` | `Pending`이라도 `bPlayerInside`면 타이머 유지(`LastEvent = left trigger inward before debounce`); `OnDebounceElapsed`는 `!bPlayerOverlapping && !bPlayerInside`일 때만 `Idle`, 아니면 `Activate()` | 0.25 s 안에 평면을 넘고 박스를 빠져나가면 오버레이만 켜지고 실내가 안 실린다 |
| 트리거 안에서 `LeaveInterior`(§3-1 8) | `SetInside(false)` → `Leaving` → 3 s 뒤 `Idle` | `OnUnloadDelayElapsed` 끝에 `bPlayerOverlapping`이면 `State = Pending` + 디바운스 재장전(로그 `Portal door_1: player still in the trigger -> reload in 0.25 s`, `LastEvent = unloaded; player still in trigger -> debounce re-armed`). `LeaveInterior` 메시지에 ` (player still in the trigger: reloads after the debounce)` 접미사(오버랩 중일 때만). `Tick`은 `Idle`/`Leaving`이면 평면 판정을 하지 않는다 | 추적 오버랩이 있는 `Idle`은 BeginOverlap이 다시 오지 않아 되돌아갈 길이 없다(R2-runtime-05) |
| `StartLeaving(const TCHAR* Event)`(신규 private) | 각 호출부가 `Leaving` + 타이머 직접 | Active→Leaving + `UnloadTimer` 공용 헬퍼(EndPlayerOverlap 바깥 이탈·LeaveInterior·RefreshOverlap·ReleaseSiblings) | 네 경로가 같아야 한다 |
| 두 문·한 실내(§3-2 StreamOut) | `StreamOut`만 다른 Active/Leaving 포털이 있으면 생략 | `OnUnloadDelayElapsed`: `IsInteriorZoneInUse(World, TargetZoneId, this)`면 `RequestUnload`도 생략(`Portal door_1: player left -> <zone> kept (another portal is active); sublevel kept (portal door_2 is leaving)`, `LastEvent = released; interior kept by another portal`); 다른 entry 포털이 `Pending`이면 `StreamOut`·`RequestUnload` 모두 미루고 `Leaving`인 채 `UnloadTimer`를 `DebounceSeconds + 0.05` s로 재장전(`Portal door_1: unload of <zone> postponed 0.30 s (another portal is pending)`, `LastEvent = unload postponed; another portal is pending`; 그 포털이 Active가 되면 kept, Idle이면 언로드 — Pending을 "사용 중"으로 세지 않는 이유는 디바운스 전에 떠난 Pending 포털은 언로드 없이 Idle이 돼 실내가 영구 핀되기 때문; R3-state-01). `SetInside(false)`마다 `ReleaseSiblings()`: 같은 `TargetZoneId`의 entry 포털 중 `bPlayerInside && !bPlayerOverlapping`인 것을 `SetInside(false)` + `StartLeaving("released: player left through another door")`(로그 `Portal door_1: released by portal door_2 (player left <zone> through another door)` → `Portal door_1: crossed outward`). 마지막으로 Leaving을 끝내는 포털 하나가 언로드 | A로 들어가 B로 나가면 A의 소스·Active가 영구 잔류(R2-runtime-02) |
| 스트림 아웃 제거 범위(§3-2 `StreamOut`) | `Cast<ULevelStreamingDynamic>`이면 `SetIsRequestingUnloadAndRemoval(true)` | `LoadLevelInstance`가 만든 인스턴스만(`PackageNameToLoad`가 있고 `UWorld::RemovePIEPrefix(GetWorldAssetPackageName()) != PackagePath`). `register_interior_sublevel()`이 등록한 `ULevelStreamingDynamic`은 목록에 남긴다 | 등록 항목이 목록에서 빠지면 `NamedStreamingLevel` 재진입이 `not registered` Error |
| 조명 상태·레벨 값 복원(§2-3 `FGolmokLightingState`, `ApplyState`) | 7필드; `SetUseTemperature(true)`·`bOverride_AutoExposureBias = true` 고정 | `bUseTemperature`·`bExposureOverridden` 필드 추가. `CaptureState`가 레벨 값을 그대로 읽고(오버라이드 없으면 노출은 `r.DefaultFeature.AutoExposure.Bias` cvar, `DefaultAutoExposureBias()`), `InitialPreset` 비움·base None 복귀 시 `SetUseTemperature(false)`·오버라이드 해제로 **저작값 복원**. 프리셋 적용은 둘 다 true. `Lerp`는 OR | 기본이 "레벨 조명 존중"인데 한 번 프리셋을 쓰면 색온도·노출 오버라이드가 레벨 값 위에 남았다 |
| 프리셋 로드 로그(§2-3) | 없음(§10-3 런북 기대만) | `TimeOfDay: presets loaded (5) from <path>` Log 1회, 실패 `TimeOfDay: presets not loaded from <path>: <error>` Error 1회 | 런북 §3 첫 체크 |
| JSON 파서 헬퍼 위치(§2-3 "익명 namespace") | 파서·콘솔 모두 `.cpp` 익명 namespace | 파서 헬퍼(`Fail`, `FailPreset`, 키 표, `FirstMissingKey` …)는 **`namespace GolmokLightingJson`**; 콘솔 명령만 익명. `test_lighting_presets.py`의 `_unity_scope_definitions()`가 모듈 전체 익명/파일 스코프 정의의 중복 0을 강제(`test_unity_scope_scanner_catches_the_known_shapes`) | 유니티 빌드는 모듈 .cpp를 이어 붙여 익명 namespace가 하나가 되므로 다른 파일의 같은 이름(`Fail` 등)과 중복 심볼 |
| 부분 프리셋 키 그룹(§2-1 규칙) | 없는 키 = 현재 값 유지(어느 키든) | 태양 4키(`pitch yaw lux kelvin`)·안개 2키(`fog fog_height_falloff`)는 **전부 있거나 전부 없어야** 한다(C++ `missing key 'x' (pitch, yaw, lux, kelvin are set together)`, Python `KEY_GROUPS` 동일 메시지) | 반쪽 태양 프리셋은 회전·강도가 어긋나고 `bHasSun/bHasFog`가 그룹 단위라 표현할 수 없다 |
| 스크린샷(§4-7, §11 #28) | `HighResShot <N> filename="…"` Exec, 메시지 `(written on the next frame)` | 1순위 `GetHighResScreenshotConfig().SetResolution(w, h, N)`(false면 1x 재시도) + `SetFilename(<path>.png)` + `UGameViewportClient::Viewport->TakeHighResScreenShot()` → **정확히 `<name>.png`**. 메시지 `screenshot requested -> <path>.png (2x, written on the next frame)`, 배율이 줄면 ` [multiplier reduced: the requested size exceeds the max texture size]` 추가. 뷰포트 크기를 못 얻으면(`-nullrhi`) 콘솔 `HighResShot` 폴백 → `<name>00000.png`(`screenshot requested via HighResShot -> …00000.png (no viewport size; …)`) | `HighResShot filename=`은 5자리 카운터를 붙인다. 이 시퀀스는 `viewpoints.py`가 부르는 `AutomationLibrary.take_high_res_screenshot`과 같고 V-01에서 `<name>.png`로 PC 검증됨 |
| 콘솔 명령 라우팅(§4-2 `--csv`, §4-5, §4-6 ③, §4-7) | `GEngine->Exec(World, …)` | `ExecConsole()`: `APlayerController::ConsoleCommand` → 없으면 `UGameViewportClient::Exec` → 월드 종료 중이면 `GEngine->Exec`. `CsvProfile Start/Stop`·`HighResShot`·`show collision` 전부 이 경로 | PIE의 `GEngine`은 에디터 엔진이라 `UEngine::Exec`가 뷰포트 명령(`show`, `HighResShot`)을 파싱하지 않는다 |
| 충돌 show flag 폴백(§4-6 ③) | `SetCollision(b)` 실패 시 Exec | 게임 뷰포트가 없을 때만(`-nullrhi`) `show collision` 폴백; 뷰포트가 있으면 `EngineShowFlags.SetCollision(b)`만 | 둘 다 부르면 토글이 두 번 |
| `Golmok.Debug.HudStats`(§8-6) | `0 < OnePercentLowFps <= AvgFps·1.001` | `OnePercentLowFps > 0`만 단언(하한), 비율은 `AddInfo`. 결정적 `PushFrameSample` 패턴 블록이 백분위수 식을 검증 | numpy `linear` 1% 백분위수는 조화평균(`N/Σdt`)에 묶이지 않는다 — 시작 히치 1개면 1% low > avg가 정상 |
| `Golmok.Portal.RoundTrip`(§8-6) | L_ZoneTest 있을 때만; Enter → Leave 1회 | skip 조건 = `L_ZoneTest` **및** 실내 서브레벨 패키지(`/Game/Golmok/Zones/z_synthetic_001_interior/v1/L_z_synthetic_001_interior`) 존재; Enter/Leave **2회** 반복; 1회차 Active 중 `RequestUnload(z_synthetic_001)`로 포털 파괴 → 핀 실내 언로드·서브레벨 out·오버레이 off 확인(`[Info] exterior unload released the interior after x.xx s`) | 재진입·EndPlay 언핀 경로를 함께 검증 |
| UE 테스트 수(§0 표, §1 표, §8-6) | 8개 | **10개**: `Golmok.Portal.PawnSwap`(캐릭터를 문 밖 6 m에 두고 `EnterInterior` → 방 안 5 m에 `ADefaultPawn` 스폰·`PC->Possess(inside)`(변화 없음) → `PC->Possess(character)` → `!bPlayerInside`·`!IsInterior()`·Leaving → 지연 뒤 언로드·Idle), `Golmok.Portal.SharedInterior`(door_1 옆 10 m에 `door_2` entry 포털을 RF_Transient로 스폰, door_1 Enter → door_2 Enter+Leave → 즉시 오버레이 off·door_1 `!bPlayerInside`·둘 다 Leaving → 지연 뒤 둘 다 Idle·서브레벨·zone 언로드). 둘 다 L_ZoneTest PIE, RoundTrip과 같은 skip. `test_ue_wp05_fixture.AUTOMATION_TESTS`가 10개를 요구 | R2-runtime-01/02의 회귀 고정 |
| `Golmok.Debug.PathRoundTrip` 정리(§8-6) | 끝에 파일 삭제 | `FPathRoundTripScenario::DeleteRecordedFile()`(삭제 + `FilePath.Reset()`)을 Playing 단계와 가상 소멸자에서 호출 → 실패 종료에도 `_automation_rec.json` 삭제 | 실패 뒤 다음 실행이 옛 파일을 재생하지 않게 |
| `test_ue_wp05_fixture.py`(§8-3) | `GolmokZoneSubsystem.cpp` 파일 해시 상수로 diff 0 강제 | 해시 검사 없음. 대신 `Portals Lighting Debug Player` 폴더에 `RegisterZone(` 호출이 없음을 스캔(`test_wp05_folders_never_call_register_zone`) + `AGolmokPortal : public AActor` 검사. `GolmokZoneSubsystem.cpp`는 실제로 무변경(`git diff 1f17fc4..HEAD` 0줄) | 해시는 무관한 포맷 변경에도 깨지고, 계약의 실체는 "`Load()` 스택에서 `RegisterZone` 없음" |
| 로그 순서(§10-5) | `Portal … -> load […]` → `Zone … loaded`; `crossed inward` → `interior overlay on` | 실내 `Zone … loaded` 줄들이 **먼저**, 그 뒤 `Portal door_1 (…): player within 150 cm -> load […]; sublevel …`; `TimeOfDay: interior overlay on/off`가 **먼저**, 그 뒤 `Portal door_1: crossed inward/outward`; `Zone … unloaded`가 `Portal door_1: player left -> unload …`보다 먼저 | `RequestLoad`·`EnterInterior`가 로그 줄보다 앞서 실행된다(런북 §5가 코드 순서를 적음) |
| HUD·콘솔 문자열(§2-3, §4-8) | `tod: overcast_morning (-> clear_noon 45%)`; `golmok.tod list … (overlay: interior) — current …`; `zones: 2 zones (load < 150 m, unload > 250 m)`; `door_out (marker)` | `tod: overcast_morning -> clear_noon 45%`(괄호 없음, base None은 `(level)`, from == to면 `night 45%`); ` - current …`(하이픈); zones 헤더 끝 `, N basemap actors tagged`(WP-04 `DescribeZones()` 그대로); `door_out (z_synthetic_001_interior -> z_synthetic_001) (marker)` | 런북이 코드 문자열을 기준으로 함 |
| `LastEvent` 값(§3-1 상태) | 열거 없음 | `entered trigger`, `re-entered trigger; unload cancelled`, `left trigger before debounce`, `left trigger inward before debounce`, `left trigger inward`, `left trigger outward`, `interior loaded`, `crossed inward`/`outward`, `leave requested`, `unloaded`, `unloaded; player still in trigger -> debounce re-armed`, `unload postponed; another portal is pending`, `released; interior kept by another portal`, `released: player left through another door`, `player pawn outside after possession change` | 디테일 패널에서 경로를 읽기 위해 |
| `AGolmokPortal` 비공개 API(§3-1 헤더) | `OnDebounceElapsed/OnUnloadDelayElapsed/StreamIn/StreamOut/SetInside` | + `Activate()`(OnDebounceElapsed·EnterInterior 공용 로드 단계), `BeginPlayerOverlap/EndPlayerOverlap/RefreshOverlap/StartLeaving/ReleaseSiblings`, `static AnyEntryPortal()/IsInteriorZoneInUse()/HasPendingSibling()/UnloadInteriorAfterEndPlay()`, `OnPlayerPawnChanged`(UFUNCTION), 멤버 `Root/OverlappingPawn/BoundController`. `EnterInterior`는 `DebounceTimer`도 해제 | 위 행들의 구현 |

## 결과
세션: session_01W4S1qYJPhQaziYbJMvAXMo (Fable 5.1 ultracode; 적대적 검증 회의론자는 모델 정책대로 Opus) · 2026-09-25 · 상태 **🟡 코드 완료·PC 검증 대기** (G2 `runbooks/pc-verify-wp05.md`, V-03). PR #10.

**진행 방식(ultracode)** — ① 설계 패널: 안정성·성능·스펙 충실 3안(Fable) → 심판 2명(엔진 사실 / 제품·검증 관점) 채점(스펙안 33/32, 안정안 32/33, 성능안 31/31) → 종합해 위 "설계 (확정)" §0~§12(심판 지적 결함 33건 반영). ② 구현: Lighting·StatsMath·Portals·합성 실내 4모듈 병렬 → Debug(다른 모듈의 실제 헤더를 읽고) → 통합(PlayerController·GameMode·ini·Build.cs·규약 테스트, 전체 게이트). ③ 적대적 검증 3라운드: 리뷰어 4관점(UE 5.8 API / 리플렉션·빌드 / 스트리밍·입력·HUD 런타임 / 스펙·테스트) → 소견마다 Opus 회의론자 2명(엔진 사실·코드 맥락)이 반박 → 둘 다 반박한 것만 기각 → 모듈별 수정 → 바뀐 영역만 다시 리뷰. 원시 소견 **25 → 11 → 1**(수렴), 확정 24·8·1(1차 24건은 관점이 겹쳐 실질 12건), 반박 1·3·0. 확정은 전부 반영했고 설계 대비 변경은 §13 표(25행)에, 반박 근거는 세션 로그(워크플로 결과)에 있다.
- 1차 확정(실질): 명명 스트리밍 경로에서 첫 stream-out이 등록 항목까지 제거(재진입 불가) / 포털 `EndPlay`가 pin된 실내를 영영 못 풀음 + 오버레이 고아 / 재생 폰 교체 시 오버랩 추적 유실 / MSVC C4458 섀도잉 2건(컴파일 차단) / 유니티 빌드 익명 namespace `Fail` 중복 / `HighResShot`이 `UEngine::Exec`에 안 닿음·파일명 `00000` 접미 / `InitialPreset` 비움일 때 실내 왕복이 레벨 노출 오버라이드를 영구 변경 / `HudStats`의 수학적으로 보장 안 되는 단언 / `RoundTrip` skip 조건 / 디바운스 중 안쪽 이탈이 실내를 안 올림 / 프리셋 로드 로그 부재.
- 2차 확정: `SetResolution`+`RequestScreenshot`만으로는 고해상도 렌더가 안 됨(`TakeHighResScreenShot()` 필요) / `OnPossessedPawnChanged`가 `(Old, nullptr)`를 먼저 방송해 실외 판정 분기 도달 불가 / 두 문·한 실내에서 B로 나가면 A 소스 잔류 / 트리거 안에서 `leave` 시 Idle-오버랩 상태 / 익명 namespace 스캐너 누락 형태 / 실패 시 녹화 파일 잔류.
- 3차 확정: Pending 형제 포털이 있을 때 실내 언로드→재로드 스래싱(언로드 연기로 해결).
- 반박(기각) 4건: 런북 미작성(당시 시점 정상) / 유니티 빌드 `using namespace` 모호성(현재 파일 순서·정의 위치상 불가) / 컨트롤러 생성 전 포털 스폰(포털은 `Load()`에서만 스폰되어 순서상 불가) / `ExecConsole` 폴백 도달 불가(로컬 플레이어 있으면 뷰포트도 있음).

**한 것** (`unreal/Golmok/` 기준; 파일 목록은 설계 §1, 설계 대비 변경은 §13)
- 조명: `Config/Golmok/lighting_presets.json`(단일 소스: cycle 4 + `interior` 부분 프리셋 4키) · `Content/Python/golmok/lighting_presets.py`(순수 파서·범위·키 그룹) · `lighting.py`(JSON 로드, 있는 키만 적용, `PRESETS` 삭제) · `setup_dev_level.py` 조명 액터 태그 `GolmokLighting` · `Lighting/GolmokTimeOfDay`(태그 우선 대상 탐색, 2 s 보간은 전환 중에만 Tick, 실내 오버레이 소스 집합, 레벨 값 복원, 콘솔 `golmok.tod <preset>|next|list`).
- 포털: `Portals/GolmokPortal`(박스 트리거 1개/문, 디바운스 0.25 s → `RequestLoad(pin)` + 서브레벨 stream-in, 문 평면 통과로 `EnterInterior/ExitInterior`, 바깥 이탈 3 s 뒤 언로드, 빙의 교체 추적, 두 문·한 실내 규칙, 콘솔 `golmok.portal list|enter|leave`) · `Portals/GolmokLevelStreaming`(`LevelInstance` 기본 / `NamedStreamingLevel`, ini `InteriorStreamingMode`) · `AGolmokZone::SpawnPortals()`(지연 생성 → `Configure` → `FinishSpawning`, 런북용 로그) + `SetCollisionDebugVisible`·`GetPortalActors` · `GolmokZoneManifest::SublevelPackagePath`. WP-04 `Evaluate()`·`RegisterZone`·`GolmokZoneSubsystem.cpp`는 무변경(테스트가 WP-05 폴더의 `RegisterZone(` 호출 부재를 강제).
- 디버그: `Debug/GolmokStatsMath.h`(순수 헤더: 링버퍼, 평균 fps `N/Σdt`, 1% low = numpy `linear` 1번째 백분위수, `CyclesToMs`, 고정소수 포매터, 경로 JSON 쓰기/읽기, 보간) · `Debug/GolmokDebugSubsystem`(`FCoreDelegates::OnEndFrame` 샘플링, HUD 줄 캐시, 충돌 표시 3중, 경로 녹화 10 Hz/재생 빙의 폰/`--csv`는 `CsvProfile Start/Stop`을 플레이어 콘솔 경로로, 스크린샷 `TakeHighResScreenShot`으로 정확히 `<tag>/<preset>/<name>.png`, 콘솔 `golmok.hud/collision/path/screenshot/stats`) · `Debug/GolmokHUD`(`DrawHUD` 8줄) · `Debug/GolmokPathPawn`.
- 플레이어: `Player/GolmokPlayerController`(Enhanced Input 런타임 생성, F1 HUD·F2 충돌·1~4 프리셋·F5 순환·F9 녹화·F10 재생, IMC 우선순위 1) · `GolmokGameMode`(컨트롤러·HUD 클래스) · `Golmok.Build.cs` `"RHI"` · `DefaultGame.ini` 5섹션 + 스테이징·쿠킹 2줄.
- 합성 실내: `tools/scripts/make_interior_fixture.py` → `z_synthetic_001_interior/v1/manifest.json`(Content·tests/fixtures 동일; 자기 원점 = 실외 zone-local (5, 13, 0) m, 8×6 m 방, 포털 `door_out`) · `synthetic_zone.run(interior=True)`(chunk_01·충돌에 문 구멍, `SM_room`·충돌 임포트, 실내 zone 액터, 서브레벨 `L_z_synthetic_001_interior`) · `register_interior_sublevel()`(명명 경로 검증용).
- 테스트: Python **+95개**(전체 323 passed, 3 skipped): `test_lighting_presets.py`(스키마·범위·값 회귀·C++ 키 대조·유니티 스코프 중복 스캔), `test_ue_python_lighting.py`(가짜 unreal), `test_ue_stats_math.py`(g++ 드라이버 vs numpy/json 교차검증 18개), `test_ue_interior_fixture.py`(생성기 재현·포털 왕복 좌표), `test_ue_wp05_fixture.py`(Build.cs·ini 키=UPROPERTY(Config)·GameMode·테스트 이름·플러그인 문자열 금지·순수 헤더), `test_ue_zone_fixture.py`(규약 폴더 6개), `test_ue_python_synthetic_zone.py`(문 구멍·방·서브레벨 액터). UE 자동화 **10개**(`Golmok.Lighting.PresetsFile/PresetApply`, `Golmok.Debug.StatsMath/PathFormat/PathRoundTrip/HudStats`, `Golmok.Portal.SpawnFromManifest/RoundTrip/PawnSwap/SharedInterior`; 전부 `-nullrhi` 통과 조건, `Portal.*` 3개는 합성 실내 없으면 skip).
- 문서: 런북 `docs/runbooks/pc-verify-wp05.md`(체크 54개, 불확실 API 표 64행), 설계 §13, ROADMAP 1.3·1.5, STATUS.

**코드 리뷰 체크리스트**
- (a) UPROPERTY 타입: `float/int32/bool/double/FString/FName/FSoftObjectPath/TArray<FName>/TObjectPtr<컴포넌트·UInputAction·UInputMappingContext·UMaterialInterface>`, `UENUM(enum class : uint8)` 2종(`EGolmokInteriorStreamingMode`·`EGolmokPortalState`) — 모두 리플렉션 가능. Config 키는 두 줄 선언(테스트가 ini 키와 1:1 대조). 순수 헤더 구조체(`GolmokStatsMath::*`)는 UPROPERTY 아님(`RingBuffer`는 서브시스템 비반영 멤버).
- (b) double↔float: 프리셋·상태는 double, 엔진 세터에 `static_cast<float>`; Config 시간·거리는 float; 엔진 cycles(uint32/uint64)는 `CyclesToMs(uint64, double)`로 승격만; 경로 JSON은 double 고정소수(cm 2자리·deg 3자리); 보간 α는 float.
- (c) `#if WITH_EDITOR`: `AGolmokZone::SpawnPortals`의 `SetActorLabel`만. 테스트 3파일은 `WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR`. 에디터 월드에서는 `AGolmokTimeOfDay::FindOrSpawn`이 스폰하지 않고, 포털은 스폰되지만 `BeginPlay`가 없어 바인딩 없음.
- (d) 로그: 전부 `LogGolmok`(테스트가 `LogTemp` 금지). 런북이 대조하는 문자열은 코드에서 옮겨 적음.
- (e) nullptr/IsValid: `GetWorld()`·서브시스템·`SpawnActor` 결과·`TWeakObjectPtr::Get()`·컴포넌트 `IsValid`·`GEngine`·뷰포트·플레이어 컨트롤러·JSON 포인터 검사; 타이머 람다는 `CreateWeakLambda(Subsystem)`; `EndPlay`/`Deinitialize`는 `bIsTearingDown` 검사.
- (f) Tick 비용: 유휴 시 프레임당 일 = `OnEndFrame`의 double 4개 push뿐(`bSampleWhenHudHidden=False`면 0). `AGolmokTimeOfDay` Tick은 전환 2 s 동안만, `AGolmokPortal` Tick은 플레이어가 트리거 안에 있을 때만(내적 1개), `AGolmokPathPawn`은 재생 중만. HUD 문자열은 0.25 s 캐시(fps 2줄만 매 프레임). 서브시스템 자체는 틱하지 않는다.

**테스트 로그(클라우드)**: `ruff check .` All checks passed · `ruff format --check .` 78 files already formatted · `python3 -m pytest -q` **323 passed, 3 skipped, 208 warnings in 14.59s** · `check_repo.py` OK. CI(`ci.yml`): 구현 커밋 `b0dd40d`는 Windows 잡만 실패(argv 32 KiB 한도·cp1252 argv 변환 → `bf4cf9a`·`359fda0`으로 드라이버 입력을 stdin으로 옮겨 해결, `359fda0` success). 최종 커밋 결과는 PR #10 체크 참조.

**불확실 API**: 공식 문서 사이트는 이 컨테이너에서 열리지 않았다. 확신 없는 호출은 런북 §11 표 64행(설계 §11의 49행 + 코드에서 추가된 15행: `OnPossessedPawnChanged`, `SetTimerForNextTick`/`CreateWeakLambda`, `PackageNameToLoad`/`RemovePIEPrefix`, `TakeHighResScreenShot`/`SetFilename`, `ConsoleCommand`/`UGameViewportClient::Exec`, `FindConsoleVariable` 등)에 대안과 함께 있다. 가장 가능성 큰 컴파일 오류는 `ULevelStreamingDynamic::LoadLevelInstance` 시그니처(§11 #1, ini `InteriorStreamingMode=NamedStreamingLevel`로 우회 가능)와 `RHIGetGPUFrameCycles`(#25, `GOLMOK_GPU_TIME_SOURCE 0`).

**판단한 것(스펙과 다른 점)**
- `interior`는 완전 프리셋이 아니라 **부분 프리셋(오버레이)**: 실내에서 태양·하늘 값을 "모른다"는 문제를 정직하게 풀고 값 중복이 없다(스펙 "노출 바이어스, 안개 0" 그대로 + `fog_height_falloff`·`volumetric`).
- 문마다 능동 트리거는 exterior가 스폰한 1개(`bIsEntry`); interior manifest의 되돌아가는 포털은 수동 마커. 왕복은 문 평면 통과 판정 하나로 완결된다.
- 재생은 스펙테이터가 아니라 **빙의 폰**(`AGolmokPathPawn`): zone 거리 로드·포털이 재생 카메라를 따라와 `--csv` 측정에 실내 전환 스파이크가 포함된다.
- `Evaluate()` 포인터 안정성은 코드 방어 대신 규약(포털은 `AActor`, `Load()` 스택에서 `RequestLoad/Unload`는 항상 타이머 뒤)으로 보장하고 테스트가 `RegisterZone(` 부재를 강제. 하드닝은 Zone Index 발견 경로 구현 때.
- `test_ue_wp05_fixture.py`에 `GolmokZoneSubsystem.cpp` 파일 해시 검사는 넣지 않았다(PC 세션의 정당한 API 수정을 막는다).

**남은 것**
- PC 검증 V-03(런북 §1~§12). 컴파일 에러는 §11 표로 고치고 `WP-05: PC fix` 커밋. 특히 `LoadLevelInstance` 시그니처·`RHIGetGPUFrameCycles`·`OnPossessedPawnChanged` 바인딩·`TakeHighResScreenShot` 파일명을 먼저 본다.
- `Golmok.Portal.SharedInterior`는 Pending 형제 연기 분기를 자동으로 검증하지 않는다(런북 §5 수동).
- `bAsyncLoad`(WP-04 TODO), Zone Index 발견 경로, splat 시각 형식(D-010)은 그대로 미구현.

**WP-06에 알릴 것**
- 실내 서브레벨 규약: 패키지 `/Game/Golmok/Zones/<zone_id>/v<version>/L_<zone_id>`(`GolmokZoneManifest::SublevelPackagePath`), **레벨 좌표로 저작**(두 스트리밍 경로 모두 항등 트랜스폼), 서브레벨 안에 `AGolmokZone`·PostProcessVolume·DirectionalLight를 두지 않는다. `interior_setup.py`는 `synthetic_zone._spawn_interior_sublevel`/`sublevel_path`/`register_interior_sublevel` 패턴을 재사용하면 된다(기본 경로 `LevelInstance`는 등록 불필요).
- 포털은 manifest `portals[]`에서 C++가 스폰하므로 Python은 포털을 배치하지 않는다. 실내 manifest의 되돌아가는 포털(`door_out`)은 같은 점·반대 yaw여야 한다(`test_ue_interior_fixture.py`의 왕복 검사 방식).
- 조명 액터에 태그 `GolmokLighting`을 달면 프리셋 대상이 고정된다(`setup_dev_level._build_lighting` 참고). `lighting.apply()`·C++ `ApplyPreset`은 같은 JSON을 읽는다; 새 프리셋은 JSON에만 추가(cycle 4개는 9키 전부, 그 외는 부분 허용·키 그룹 규칙).
- `spike_runner.py`: 무인 캡처는 PIE/`-game`에서 `golmok.path play <name> --csv` + `golmok.screenshot <tag> <name>`(HUD 없이 정확한 파일명)로 설계하면 된다. `-game` CSV는 `%LOCALAPPDATA%\UnrealEngine\5.8\Saved\Profiling\CSV`, 워밍업 2 s 규칙(녹화 시작 후 3 s 정지).
- `AGolmokTimeOfDay::ApplyPreset/NextPreset/EnterInterior/ExitInterior`는 `BlueprintCallable`(Python `call_method`)이다.
