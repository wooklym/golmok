# WP-12 — 포토 모드 최소판 (D-013)

상태: 🔴 PC 검증 완료(V-09, 2026-09-28)·§7 footprint 후속 수정 대기 — 이전: 🟡 코드 완료·PC 검증 대기 (등록 2026-09-25, 시작 2026-09-25, 코드 완료 2026-09-27, session_01R7589q1vh4DRPq4NeCsZ4Q) · 담당: 클라우드 Claude 세션(**Fable 5.1 ultracode**, 검증 Opus 5.5 — 모델 정책 DEVELOPMENT-PLAN §7.4) · 의존: WP-05(디버그 스크린샷·HUD·시간대 프리셋), WP-04(Geo·Zone), WP-09(zone 발견) · 검증: G2(`runbooks/pc-verify-wp12.md`, V-09, PC 세션)

## 목표
플레이어가 키 하나로 **포토 모드**에 들어가 게임을 멈추고, 캐릭터 주변에서 자유 카메라로 구도를 잡아 고해상도 사진을 찍는다(D-013 최소판, 사용자 승인 2026-09-25). 실사 재구성 골목을 "내가 찍은 사진"으로 남기는 공유 동력이자, 스파이크·회귀 비교 캡처 도구와 겹친다. 범위·근거: [`design/game-features-proposal.md`](../design/game-features-proposal.md) D-013.

## 배경(코드에서 확인할 것)
- 촬영 경로는 WP-05 `UGolmokDebugSubsystem`의 `golmok.screenshot <tag> [name]`(`HighResShot N filename=…`, `Saved/Screenshots/Golmok/<tag>/<preset>/`, 다음 프레임에 기록)을 **재사용**한다. V-03 발견: 이 스크린샷에는 HUD가 포함된다 → 포토 모드는 촬영 직전 HUD와 자기 오버레이를 끄고 찍는다.
- 입력은 C++ Enhanced Input(`Player/GolmokCharacter.cpp` `IMC_Default`, `Player/GolmokPlayerController.cpp` F1~F10·1~4 디버그 키). 포토 모드 키는 기존 키와 겹치지 않게(권장 `P`, 게임패드 `Gamepad_Special_Left`/`Back`), 포토 모드 안에서는 별도 매핑 컨텍스트(`IMC_Photo`)를 더 높은 우선순위로 추가하고 나갈 때 제거.
- 시간대 프리셋 이름은 `AGolmokTimeOfDay`(WP-05), 플레이어 경위도는 `UGolmokGeoSubsystem::LevelUEToLonLat`(WP-04, 원점 없으면 실패 → 메타에 `null`), 현재 zone은 `UGolmokZoneSubsystem`(플레이어 위치가 footprint 안인 로드된 zone, 없으면 `null`).
- 디버그 카메라 폰 `Debug/GolmokPathPawn`(경로 재생용)이 있으나 포토 모드는 플레이어 입력으로 움직이는 **별도 폰**이 낫다(설계 패널이 재사용 여부 판단).
- 일시정지 중 입력·틱: `UInputAction::bTriggerWhenPaused`, `AActor::SetTickableWhenPaused`, `APlayerController::SetPause`의 5.8 동작은 **엔진 헤더에서 확인**하고 불확실하면 런북 "불확실 API" 표에 적는다(추측 금지).

## 산출물 (`unreal/Golmok/Source/Golmok/Photo/`, `Config/`, `docs/`)
1. **`UGolmokPhotoModeSubsystem`**(World 서브시스템) + **`AGolmokPhotoCameraPawn`**: 진입 시 게임 일시정지(캐릭터·시간대 전환·포털 타이머 정지, 오디오는 WP-13 뒤 연동), 현재 카메라 위치·회전에서 자유 카메라 시작, 나가면 원래 폰·HUD·PostProcess·일시정지 상태 복원(진입 전에 이미 일시정지였으면 유지). 콘솔 `golmok.photo [0|1]`, `golmok.photo.shoot`, `golmok.photo.reset`.
2. **자유 카메라 제약**: 캐릭터 반경 `MaxDistanceM`(Config, 기본 3.0 m) 구 안, 벽·바닥 충돌(구 컴포넌트 스윕, 재구성 메시 뒷면·구멍으로 새지 않게 반경 15 cm), 로드된 zone이 있으면 그 footprint(ENU 다각형, WP-04 파서) 안으로 클램프. 클램프·다각형 포함 판정은 **순수 헤더 `GolmokPhotoMath.h`**(UE 타입 없음)로 두고 pytest에서 g++ 교차검증(WP-04 `GolmokGeoMath.h`·`test_ue_geo_math.py` 방식).
3. **조절 항목**(키·게임패드, 화면 왼쪽 아래 작은 텍스트 오버레이 — HUD 클래스 재사용, 촬영 시 숨김): FOV(20~110°), 노출 보정(EV ±3), 피사계 심도(초점 거리 0.3~50 m, 조리개 f/1.4~f/16; `FPostProcessSettings` 오버라이드를 폰 카메라 컴포넌트에), 카메라 롤(±15°), 캐릭터 숨김 토글, 오버레이 숨김 토글, 리셋. 값은 `Config/Golmok/photo.json`(단일 소스: 기본값·범위·키 힌트 문자열)로 두고 WP-05 `lighting_presets.json`처럼 pytest 스키마 검사 + UFS 스테이징.
4. **촬영**: `UGolmokDebugSubsystem`의 스크린샷 함수를 public API로 분리해 호출(`HighResShot` 배율 `ScreenshotMultiplier` 기본 2, 상한 `MaxMultiplier` 기본 3 — RTX 5060 8 GB VRAM 고려, 런북에서 실측해 조정). 파일 `Saved/Screenshots/Golmok/photo/<yyyymmdd_hhmmss>.png` + 같은 이름 `.json`(스키마: `version`, `time_utc`, `preset`, `zone_id`/`zone_version` 또는 null, `lon`/`lat`/`height_m` 또는 null, `ue_location`·`rotation`, `fov`, `exposure_ev`, `dof:{focal_m, fstop}`, `multiplier`, `character_hidden`). 촬영 중 오버레이·HUD·캐릭터(숨김 켰으면) 상태를 보장하고, 기록이 끝나면 오버레이 복원.
5. **법·정책 문구**: `docs/research/05-legal-policy.md`의 공개 전 자문 항목에 "사용자 촬영 스크린샷 외부 공유(간판·상호·블러 누락 얼굴)" 추가(문서만; 판단은 D-009 자문).
6. **테스트**: UE 자동화 `Golmok.Photo.EnterExit`(일시정지·복원, `-nullrhi`), `Golmok.Photo.Clamp`(반경·다각형), `Golmok.Photo.MetaJson`(필드·null 규칙); pytest `test_ue_photo_math.py`(g++ 교차검증), `test_ue_config_photo.py`(JSON 스키마); 기존 WP-04/05/09 테스트 전부 통과.
7. **런북** `docs/runbooks/pc-verify-wp12.md`(V-09): 빌드 → `test.ps1 -Filter Golmok.Photo` → PIE에서 진입/조절/촬영/복원 → 배율 2·3에서 VRAM·소요 시간 → 벽 관통·zone 밖 이탈 시도 → 실내(포털) 안에서 촬영 → 스크린샷 4장(JPG 축소)을 런북에 첨부 → 불확실 API 표.

## 완료 기준
클라우드: 설계 패널 기록(`docs/plan/WP-12-photo-mode.md` "설계" 절), 코드·테스트·런북 작성, pytest·ruff·check_repo 통과, CI 초록, STATUS `🟡 코드 완료·PC 검증 대기`. PC: V-09 통과 → `🟢`.

## 주의
- D-003: 로직은 C++, 위젯 에셋은 만들지 않는다(텍스트 오버레이는 HUD `Canvas` 그리기). 새 플러그인·에셋·의존성 없음.
- WP-05 규약 유지: 일시정지 중 `AGolmokTimeOfDay` 전환·포털 타이머가 어긋나지 않게(진입 전 상태 저장·복원), `Load()` 스택에서 RegisterZone/RequestLoad 금지.
- 5.8 주의(V-03·WP-09): `FJsonObject::Values`는 `UE::FSharedString`, MSVC C4458 섀도잉은 오류, `GRenderThreadTime`은 `RenderTimer.h`. Windows CI: 경로 `pathlib`, 서브프로세스 `encoding="utf-8"`, 테스트 픽스처 `newline="\n"`, 부동소수 비교 `pytest.approx`.
- 세션 운영: 적대적 검증 최대 1라운드, Workflow 2시간 상한, 1.5시간마다 커밋·push. 비용 보고는 STATUS 세션 로그에.

## 설계 (확정, 2026-09-25)

근거: 이 문서 산출물 1~7, D-013(`design/game-features-proposal.md`), WP-05 "설계 (확정)" §11·§13 + "결과"(V-03: `TakeHighResScreenShot`은 다음 프레임에 기록되고 **HUD를 포함**, 에디터 창이 뒤에 있으면 뷰포트를 그리지 않음, `FJsonObject::Values`는 `UE::FSharedString` 키, MSVC C4458은 오류, `GRenderThreadTime`은 `RenderTimer.h`), WP-09 §0~§3·§10 형식, `runbooks/pc-verify-wp09.md` §11, 현재 코드(`Debug/GolmokDebugSubsystem`·`GolmokHUD`·`GolmokPathPawn`, `Player/*`, `Lighting/GolmokTimeOfDay`, `Portals/GolmokPortal`, `Zones/*`, `Geo/*`, `Tests/GolmokDebugTest.cpp`, `Golmok.Build.cs`, `Config/*`), Python 테스트 패턴(`test_ue_geo_math.py`·`test_ue_stats_math.py`의 stdin 드라이버, `test_lighting_presets.py`, `test_ue_wp05_fixture.py`·`test_ue_wp09_fixture.py`). 세 후보 설계(① UE API 현실성 / ② 플레이어 경험·품질 / ③ 데이터·테스트)를 심판 2명(엔진 사실 / 제품·검증)이 채점(27·27·27 / 27·27·29)했고, 어느 안도 그대로 채택하지 않았다: **골격은 ③(데이터·테스트·Windows CI 규약), 복원·시간대·촬영 전 대기는 ②(빙의 없음·`ShiftTransitionStart`·진입 FOV 연속성·DOF 기본 off), API 인용·캡처 종료 조건·틱 카운터 단언은 ①**에서 가져오고 심판 지적(§12 표 40건)을 전부 닫았다. 선택지는 남기지 않았다. 이 절은 코드를 쓰지 않는다 — 구현 세션은 시그니처·ini 키·JSON·테스트·런북을 그대로 옮기고, 엔진 API가 확실하지 않은 곳은 §10 표 번호로 런북에 넘긴다.

표기: [확인] = 이 세션에서 저장소 코드를 읽었거나 공식 문서 URL을 실제로 열어 본문을 확인 / [2차] = 엔진 소스 기억·간접 근거(헤더 없음) / [미확인] = 추정 → §10 표. 이 세션에서 실제로 열린 공식 문서(본문 있음): `FViewport::TakeHighResScreenShot`("Returns true if the screenshot can be taken, and false if it can't. The screenshot can fail if the requested multiplier makes the screen too big for the GPU to cope with", 반환 `bool`) https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Engine/FViewport/TakeHighResScreenShot · `UInputAction::bTriggerWhenPaused`("Should this action be able to trigger whilst the game is paused - Replaces bExecuteWhenPaused")·`bConsumeInput`("Should this action swallow any inputs bound to it or allow them to pass through to affect lower priority bound actions?") https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Plugins/EnhancedInput/UInputAction · `EKeys`(`Gamepad_Special_Left/Right`, `LeftBracket/RightBracket`, `Hyphen/Equals/Comma/Period`, `P H O R Z C N M E Q Enter`, `Gamepad_DPad_*`, `Gamepad_LeftShoulder`, `Gamepad_RightTrigger`, `Gamepad_FaceButton_*`, `Gamepad_RightThumbstick`, `MouseWheelAxis` 전부 존재) https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/InputCore/EKeys · BP `Set Game Paused`("Sets the game's paused state", 반환 "Whether the game was successfully paused/unpaused") https://dev.epicgames.com/documentation/en-us/unreal-engine/BlueprintAPI/Game/SetGamePaused · 액터 틱 가이드의 `PrimaryActorTick.bTickEvenWhenPaused = true;` 예시 https://dev.epicgames.com/documentation/en-us/unreal-engine/actor-ticking-in-unreal-engine · `FTimerManager` `PauseTimer/UnPauseTimer`(게임 일시정지와 타이머의 관계는 **언급 없음**) https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Engine/FTimerManager. **목차만 내려온 것(본문 없음 → [미확인])**: `APlayerController::bShouldPerformFullTickWhenPaused`, `UGameplayStatics::SetGamePaused`(C++), `AActor::SetTickableWhenPaused`, `UGameViewportClient::SetSuppressTransitionMessage`. 엔진 소스는 이 컨테이너에 없다.

### 0. 확정 결정 요약
| # | 주제 | 결정 | 근거·바꾼 지적 |
|---|---|---|---|
| 1 | 빙의 | **포토 폰을 빙의하지 않는다.** `PC->GetPawn()`은 캐릭터 그대로, `SetViewTargetWithBlend(PhotoPawn, 0)`만. 진입 시 `SavedViewTarget`·`SavedControlRotation` 저장, 종료 시 역순 복원. pytest가 `Photo/`에 `->Possess(` 부재를 강제 | `AGolmokPortal::OnPlayerPawnChanged → RefreshOverlap(NewPawn)`이 문 트리거 상태·실내 오버레이를 끝낸다 [확인 `GolmokPortal.cpp` 141·276~289·379~413]; `GetPlayerLocation`·`IsPlayerPawn`도 빙의 폰 기준 [확인]. ①③의 결함(J-engine-1, J-product-1) → ② 채택 |
| 2 | 정지 | `UGameplayStatics::SetGamePaused(World, true)`(BP 문서로 존재·bool 반환 [확인]; C++ 시그니처 [2차] §10 #1). 진입 전 `IsGamePaused()`를 `bWasPausedBefore`에 저장, 나갈 때 **false였을 때만** 해제. `PauseMode` ini enum `GamePause`(기본)/`TimeDilation`(PC 폴백: `SetGlobalTimeDilation(0.0001)` + 캐릭터 `CustomTimeDilation = 0`, 저장·복원) — 재빌드 없이 전환 | J-engine-5·X10: 정지 중 렌더 시간 누적·입력이 5.8에서 어긋날 때의 한 스위치 |
| 3 | 정지 중 살아 있는 것 | 폰 `PrimaryActorTick.bTickEvenWhenPaused = true`(생성자 [확인 가이드 예시]); 모든 포토 액션 `bTriggerWhenPaused = true`·`bConsumeInput = true` [확인 필드]; 진입 시 `PC->bShouldPerformFullTickWhenPaused = true`(**기본 경로**, `const bool bSaved = PC->…`로 값 복사 후 복원; 비트필드일 수 있어 참조·포인터 금지) | J-engine-3·J-product-2: 정지 중 `UpdateCameraManager`는 풀틱 PC에만 [2차 M1] → 폴백이 아니라 기본 |
| 4 | 시간대 | `AGolmokTimeOfDay::ShiftTransitionStart(double DeltaSeconds)` public 추가(전환 중 아니면 no-op, `TransitionStart += Delta`). 진입 시 `WorldTimeAtEnter = World->GetTimeSeconds()`, 종료 시 `Δ > 0 && IsTransitioning()`이면 시프트. 월드 시계가 멈추든(Δ = 0) 안 멈추든 결과가 같다 | J-engine-2: ①의 "즉시 완료"는 스펙("어긋나지 않게 저장·복원") 위반이고 `TargetPreset == None`(실내 오버레이 전환)에서 `ApplyPreset`이 실패 [확인 `GolmokTimeOfDay.cpp` 857~890] |
| 5 | 입력 위치 | 토글 액션·`IMC_GolmokPhotoToggle`은 **PC 소유**(우선순위 2, `bDebugKeysEnabled`와 무관하게 항상). 포토 액션 21개(시선은 마우스 `Look`·패드 `LookPad` 둘 — 결과 참고)·`IMC_GolmokPhoto`(우선순위 3)는 **서브시스템 소유**(Transient); 바인딩은 `AGolmokPlayerController::SetupInputComponent`가 `Photo->BindInput(Input)` 한 줄로 위임(PC 입력 컴포넌트는 빙의와 무관하게 스택에 있음). 컨텍스트 추가/제거는 서브시스템 `Enter/Exit`가 직접 | 빙의 없음(#1)의 귀결. 서브시스템 메서드 `BindAction`은 [2차] → §10 #7(실패 시 핸들러를 PC로) |
| 6 | 조절 모델 | **한 조절 한 액션 쌍, `Started`만**(반복·가속·스무딩·선택 모델·장치별 힌트 전환 없음 — Phase 2). 예외: FOV는 마우스 휠(`MouseWheelAxis`)로도 조절. 스텝: FOV 5°, EV 1/3(정수 스텝 양자화 `Quantize`), focus ×1.25, f-stop 1스톱 표 `1.4 2 2.8 4 5.6 8 11 16`, roll 1° | J-engine-11·J-product-8(②의 과설계 제거), X8(스텝은 반복 없이 20회 이내로 범위를 돎) |
| 7 | 키 | P / `Gamepad_Special_Left` 토글; Space·Enter / A 촬영; WASD·EQ / 왼스틱·LT/RT 이동; Mouse2D / 오른스틱 시선; `[ ]`·휠 / D-pad ←→ FOV; `- =` / D-pad ↓↑ EV; `, .` / LB RB focus; N M / X Y f-stop; Z C / (없음) roll; F / R3 DOF; H / B 캐릭터 숨김; O / (없음) 오버레이; R / `Gamepad_Special_Right` 리셋; LeftShift / L3 빠르게(§5) | ③의 대칭 배정 + J-product-15(f-stop X/Y·숨김 B·리셋 Menu·DOF R3·오버레이 패드 없음·패드 롤 없음). LMB 제외(X9: 시선 조작 중 오촬영) |
| 8 | 디버그 키·HUD | 진입 시 `IMC_GolmokDebug` 제거(`AGolmokPlayerController::SetDebugKeysSuspended(true)`), 종료 시 `bDebugKeysEnabled`일 때만 재추가; `AddMappingContext()`는 suspended 동안 early-return(재빙의는 없지만 방어). 디버그 HUD는 진입 시 `SetHudVisible(false)` 저장·복원(개발자는 `golmok.hud 1`로 켤 수 있음; 캡처 프레임은 별도 플래그로 숨김) | X5·X6, F12(`OnPossess` 재추가 가드) |
| 9 | photo.json 실패 | **진입 거부**(`golmok.photo` 메시지 `photo.json: <error>` + Error 로그 1회, `LastError`). C++에 기본값 사본 없음(pytest가 `Photo/*.cpp`에 범위 리터럴 `20/110/1.4/16/0.3/50/15` 부재를 느슨히 검사) | X4·J-engine-15·J-product-7: "단일 소스" |
| 10 | 순수 헤더 include | `Photo/GolmokPhotoMath.h`는 따옴표 include **정확히 2개** `"Geo/GolmokGeoMath.h"`(PointInPolygon·DistanceToSegment)·`"Debug/GolmokStatsMath.h"`(FormatFixed·JsonQuote). 복제 0. 공용 `assert_pure_header`는 손대지 않고 `test_ue_photo_math.py`에 PhotoMath 전용 검사(따옴표 == 그 2개, 꺾쇠 ⊆ StatsMath 허용 7개, 금지어) | X5(제품)·J-engine-9·J-product-9/10. 엔진 심판의 "GeoMath만 + FormatFixed 자체 구현"은 복제를 남기므로 채택하지 않음; 두 헤더 모두 순수·g++ 검증됨 |
| 11 | DOF | 기본 **off**(F / R3 토글, 켜면 JSON 기본 3.0 m·f/2.8). off = `bOverride_DepthOfFieldFocalDistance = true, DepthOfFieldFocalDistance = 0` [2차 → §10 #9]. 메타 `"dof": {"enabled": …, "focal_m": …, "fstop": …}`(스펙 키 유지 + `enabled` 1키) | X6·J-product-6(진입 즉시 원경 흐림은 "찍힌 그대로" 기대와 재구성 품질 판정 캡처에 해로움). J-engine-18의 `dof: null` 대안은 스펙 객체 형을 깨므로 키 추가로 |
| 12 | 진입 FOV·값 지속 | 진입 시 FOV = **현재 카메라 FOV**(`PlayerCameraManager->GetFOVAngle()` [2차], 캐릭터 80), 나머지 값은 월드 안에서 유지(서브시스템 멤버). 리셋 = JSON `default` 5개 + DOF off + 캐릭터 표시 + 오버레이 표시 + 위치/회전을 진입 시점으로 | X7·J-product-14 |
| 13 | 촬영 순서 | `Shoot()`: 같은 게임 틱에 `State = Shooting`(HUD·오버레이 숨김, 이동·시선 입력 동결) → `OnEndFrame` 바인딩 → `PreCaptureFrames`(ini, 기본 2) 뒤 stem 결정 → **메타 JSON 동기 기록(실패면 요청하지 않음)** → `Debug->RequestHighResScreenshot(...)`(실효 배율이 다르면 메타 재기록) → `Captured` → **PNG 존재 또는 실시간 3 s 타임아웃** 중 먼저, 단 최소 `PostCaptureFrames`(기본 2) → 복원. 카운터는 `FCoreDelegates::OnEndFrame`(`-nullrhi` 발화 V-03 확인), 폰 틱에 의존하지 않음 | X10·J-engine-4·J-product-4, X13(메타 먼저) |
| 14 | 스크린샷 API | `UGolmokDebugSubsystem::RequestHighResScreenshot(const FString& AbsolutePathNoExt, int32 Multiplier, FString& OutMessage, int32& OutEffectiveMultiplier)` public 분리; `TakeScreenshot`은 경로 조립 + 이 함수 호출(메시지 3종 불변). `TakeHighResScreenShot()`의 bool 반환을 검사해 false면 1x 재시도(현재 코드는 무시 — F5, 분리 시 함께 고침) | J-product-4·F6 |
| 15 | 메타 | 스펙 필드 + `dof.enabled`만. `preset`은 `CurrentPreset == None`이면 `null`(`"current"`는 폴더 규약일 뿐), zone·geo는 그룹 단위 null, `file`·`resolution`·`+interior` 없음. lon/lat 7자리·height 3·ue_location 2·rotation 3·fov 1·ev 2·focal 3·fstop 2 | X11·X12·J-product-12/13 |
| 16 | footprint zone 선택 | `UGolmokZoneSubsystem::FindLoadedZoneAt(const FVector2D& LevelUEPointCm) const` public 추가(읽기 전용, `Zones` 순회 + `ZoneWins`: priority↓ → version↓ → id; `RegisterZone/RequestLoad` 호출 없음). 진입 시 1회 + `Shoot` 시 재조회해 footprint 복사 | J-engine-8: 규칙이 셋이면 메타 `zone_id`와 HUD/스트리밍이 다른 zone을 가리킴. ③의 TActorIterator 규칙(실내→priority→id)은 `ZoneWins`(private)와 불일치라 채택하지 않음 |
| 17 | 구·다각형 충돌 | 순서 구 → 다각형(**V-09 후속** a6c48a3 → e03753e → 7f66810: inset 20 cm만큼 줄인 침식 영역 S의 정확한 최근접점 — §6-2) → 스윕. 다각형 클램프 결과가 구 밖이면 최대 16라운드 교대, 재검사 실패면 **이동 취소**(직전 위치가 있으면 Current→P 이분 탐색 폴백; 앵커는 둘 다의 안, 직전 위치도 둘 다 만족하므로 항상 안전). 스윕이 막히면 남은 이동을 충돌면에 투영해 한 번 더 스윕(**V-09 후속**, 최대 2회 — §6-3), `bStartPenetrating`이면 앵커 쪽 10 cm 후퇴 | X14(③) |
| 18 | 콘솔 | `golmok.photo [0\|1]`(인자 없음 = **토글**, `golmok.hud` 규약), `golmok.photo.shoot`, `golmok.photo.reset`, + `golmok.photo.set <fov\|ev\|focus\|fstop\|roll\|dof\|char\|overlay\|mult> <value>`(헤드리스 드라이버가 키 없이 값·배율 검증). 매 전이 때 상태 한 줄 로그 | X15 |
| 19 | ini | `[/Script/Golmok.GolmokPhotoModeSubsystem]` 11키(§7): `ConfigFile PhotoFolder ScreenshotMultiplier MaxMultiplier MaxDistanceM CollisionRadiusCm FootprintMarginM MoveSpeedMps PreCaptureFrames PostCaptureFrames PauseMode`. 우선순위는 코드 상수, `bPhotoKeyEnabled` 없음. JSON = params·toggles 기본·hints만(`camera`·`keys` 블록 없음) | X16·J-product-11 |
| 20 | 폰 EndPlay·월드 해체 | 폰 `EndPlay(Reason)`은 항상 `Owner->OnPhotoPawnEndPlay(this, Reason)`. 서브시스템: `State == Exiting`(자기 Destroy)이면 무시; `Reason == Destroyed && !World->bIsTearingDown`이면 정상 `Exit("pawn destroyed")`; 그 밖(`EndPlayInEditor`/`Quit`/`LevelTransition`/해체 중)이면 PC·정지·뷰 타깃을 건드리지 않고 내부 상태·`OnEndFrame`·IMC 참조만 정리. `Deinitialize`도 같은 "월드 죽음" 경로. **유일한 예외**(수정 STATE-4, 2026-09-27): 게임 뷰포트 클라이언트는 월드가 아니라 GameInstance/WorldContext 소유라 -game `open`/`RestartLevel` 뒤에도 살아남으므로 `TeardownForDeadWorld`도 `SetSuppressTransitionMessage(bSavedSuppressTransition)`을 복원한다 | J-engine-10 |
| 21 | 화면 텍스트 | 진입 시 `GameViewport->SetSuppressTransitionMessage(true)`(원값은 `bSuppressTransitionMessage` 멤버 읽기 [미확인 §10 #12]), 종료 시 복원; 런북이 정지 화면·PNG 중앙 "PAUSED" 없음을 확인. 카메라 PP에 `bOverride_MotionBlurAmount = true, MotionBlurAmount = 0` [2차 §10 #9] | J-engine-6·J-product-3/5 |
| 22 | 테스트 | UE 3개 이름 그대로(`Golmok.Photo.EnterExit / Clamp / MetaJson`, `-nullrhi`); 파서 실패 케이스는 `MetaJson`의 순수 부분에 합침. Geo 단언은 `Geo->HasOrigin()`으로 분기(L_Dev에 GeoOrigin 없음 [확인 F13]). pytest 3파일 + 기존 상수 확장(`CONVENTION_FOLDERS += "Photo"`, `RUNBOOKS`) | J-engine-7·J-product-22 |
| 23 | enum | `PauseMode`만 `UENUM`(Config용); `EGolmokPhotoState`는 일반 `enum class`(리플렉션 불필요, `Count` 없음). 멤버 함수는 `GolmokPhotoMath::` 한정 호출(이름 충돌 회피), 로컬 변수는 `New*`/`Local*`(C4458은 로컬도 해당), 익명 namespace는 `Photo*` 접두 | J-engine-13/14 |
| 24 | 문서 정정 | `GolmokHUD.h` 주석 "never include it" → "hidden by photo mode while capturing; golmok.screenshot includes it (V-03)" | J-product-20 |

### 1. 파일 목록
| 경로 (`unreal/Golmok/` 기준, 그 외 저장소 기준) | 상태 | 내용 |
|---|---|---|
| `Source/Golmok/Photo/GolmokPhotoMath.h` | 신규 | 순수 헤더(§3-1): 파라미터 스텝·양자화·f-stop 표, 구·다각형 클램프, `Constrain`, 메타 JSON 포매터. include는 표준 + `Geo/GolmokGeoMath.h` + `Debug/GolmokStatsMath.h` |
| `Source/Golmok/Photo/GolmokPhotoModeSubsystem.h` / `.cpp` | 신규 | `FGolmokPhotoConfig` + 파서(`namespace GolmokPhotoJson`, 명명), `UGolmokPhotoModeSubsystem`(§3-2): 상태기계, 입력 자산·`BindInput`, 촬영·메타, 오버레이 줄, 콘솔 4개 |
| `Source/Golmok/Photo/GolmokPhotoCameraPawn.h` / `.cpp` | 신규 | `AGolmokPhotoCameraPawn`(§3-3): 구·카메라 컴포넌트, 정지 중 Tick, 제약·스윕, `ApplyOptics` |
| `Source/Golmok/Debug/GolmokDebugSubsystem.h` / `.cpp` | 변경 | `RequestHighResScreenshot` public 분리(§3-4), `TakeScreenshot`은 래퍼, `TakeHighResScreenShot()` 반환값 검사; `StartPlayback/StartRecording` 첫 검사에 포토 활성 거부 1 if |
| `Source/Golmok/Debug/GolmokHUD.h` / `.cpp` | 변경 | `DrawHUD` 첫머리 캡처 가드 + 왼쪽 아래 포토 오버레이(§3-5); 클래스 주석 정정 |
| `Source/Golmok/Player/GolmokPlayerController.h` / `.cpp` | 변경 | `IA_GolmokPhotoToggle`·`IMC_GolmokPhotoToggle`(P, `Gamepad_Special_Left`, `bTriggerWhenPaused`), `OnTogglePhoto`, `SetDebugKeysSuspended/IsDebugKeysSuspended`, `SetupInputComponent`에서 `Photo->BindInput(Input)`(§3-6) |
| `Source/Golmok/Zones/GolmokZoneSubsystem.h` / `.cpp` | 변경(추가만) | `AGolmokZone* FindLoadedZoneAt(const FVector2D& LevelUEPointCm) const`(§3-7) |
| `Source/Golmok/Lighting/GolmokTimeOfDay.h` / `.cpp` | 변경(추가만) | `void ShiftTransitionStart(double DeltaSeconds)`(§3-7) |
| `Source/Golmok/Tests/GolmokPhotoTest.cpp` | 신규 | `Golmok.Photo.EnterExit / Clamp / MetaJson`(§8-1) |
| `Source/Golmok/Golmok.Build.cs` | **불변** | `Camera/CameraComponent.h`·`Components/SphereComponent.h`·`Kismet/GameplayStatics.h`·`EngineUtils.h`·`EnhancedInput*`·`Json`은 이미 의존. pytest가 무변경 강제 |
| `Config/Golmok/photo.json` | 신규 | §2-1(단일 소스) |
| `Config/DefaultGame.ini` | 변경 | `[/Script/Golmok.GolmokPhotoModeSubsystem]` 11키(§7). 스테이징 줄 추가 없음(`../Config/Golmok` UFS 항목이 덮음) |
| `Config/DefaultInput.ini` | 무변경 | `!DebugExecBindings=ClearArray` 유지 |
| `tools/tests/fixtures/ue/photomath_driver.cpp` | 신규 | g++ 드라이버(입력은 stdin) |
| `tools/tests/test_ue_photo_math.py` | 신규 | §8-2 |
| `tools/tests/test_ue_config_photo.py` | 신규 | §8-3 |
| `tools/tests/test_ue_wp12_fixture.py` | 신규 | §8-4 |
| `tools/tests/test_ue_zone_fixture.py` | 변경(1줄) | `CONVENTION_FOLDERS += "Photo"` |
| `tools/tests/test_ue_python_pure.py` | 변경(1줄) | `RUNBOOKS += pc-verify-wp12.md` |
| `docs/research/05-legal-policy.md` | 변경 | "변호사 자문 필요 항목" 7(§2-4) |
| `docs/runbooks/pc-verify-wp12.md` | 신규 | §9 골자 + §10 표 |
| `docs/plan/WP-12-photo-mode.md` 결과, `docs/plan/STATUS.md`, `docs/ROADMAP.md` | 변경 | 세션 규약 |

`Content/Python/golmok/photo_config.py`는 만들지 않는다(에디터 Python이 읽을 곳이 없음, J-product-23). 새 모듈·플러그인·에셋 없음.

### 2. 데이터·경로 규약
#### 2-1 `Config/Golmok/photo.json`(정확한 내용 = 기본값)
```json
{
  "schema_version": 1,
  "params": {
    "fov":   {"label": "fov",   "unit": "deg", "default": 65.0, "min": 20.0,  "max": 110.0, "step": 5.0},
    "ev":    {"label": "ev",    "unit": "EV",  "default": 0.0,  "min": -3.0,  "max": 3.0,   "step": 0.3333333333},
    "focus": {"label": "focus", "unit": "m",   "default": 3.0,  "min": 0.3,   "max": 50.0,  "step_ratio": 1.25},
    "fstop": {"label": "f/",    "unit": "",    "default": 2.8,  "values": [1.4, 2.0, 2.8, 4.0, 5.6, 8.0, 11.0, 16.0]},
    "roll":  {"label": "roll",  "unit": "deg", "default": 0.0,  "min": -15.0, "max": 15.0,  "step": 1.0}
  },
  "toggles": {"dof": false, "character_hidden": false, "overlay_hidden": false},
  "hints": {
    "keyboard": ["P exit  Space shoot  R reset  F dof  H char  O overlay",
                 "WASD/EQ move  Shift fast  mouse look  Z/C roll  wheel fov",
                 "[ ] fov   - = ev   , . focus   N M f-stop"],
    "gamepad":  ["View exit  A shoot  Menu reset  R3 dof  B char",
                 "LS move  LT/RT down/up  RS look  L3 fast",
                 "DPad L/R fov  DPad D/U ev  LB/RB focus  X/Y f-stop"]
  }
}
```
규칙(pytest·C++ 파서 공통, 위반 = 진입 거부): 최상위 키 정확히 `{schema_version, params, toggles, hints}`, `schema_version == 1`; `params` 키 정확히 `fov ev focus fstop roll`(순서 고정 = 오버레이 순서); 각 항목은 `label`(문자열)·`unit`(문자열, 빈 문자열 허용)·`default`(숫자) + 꼴 셋 중 하나 — `{min, max, step}`(선형, `step > 0`), `{min, max, step_ratio}`(기하, `step_ratio > 1`, `min > 0`), `{values}`(이산, 오름차순·양수·2개 이상); `min < max`, `min ≤ default ≤ max` 또는 `default ∈ values`; 숫자는 `EJson::Number`만(bool 거부); `toggles` 3키 bool; `hints.keyboard/gamepad`는 문자열 배열 1~4줄·각 ≤ 72자. 스펙 수치(20~110°, ±3 EV, 0.3~50 m, f/1.4~16, ±15°)는 JSON과 pytest 회귀 상수에만 있고 C++에는 없다. EV는 `Quantize`(k = round((v − min)/step), v = min + k·step)로 정수 스텝 위에만 놓여 누적 드리프트가 없다(값 표시 2자리: `+0.33`).

#### 2-2 스크린샷·메타 경로
- 디렉터리 `FPaths::ProjectSavedDir()/<PhotoFolder>` = `Saved/Screenshots/Golmok/photo/`(ini `PhotoFolder=Screenshots/Golmok/photo`; `viewpoints.py`·`golmok.screenshot`과 같은 트리, 프리셋 하위 폴더 없음 — 사진첩(D-017)이 폴더 하나를 훑도록).
- 파일 스템 `FDateTime::Now().ToString(TEXT("%Y%m%d_%H%M%S"))`(로컬 시각, WP-05와 동일 [확인 V-03]); 같은 초에 두 번이면 `<stem>_2`, `_3`(`.json` 존재 검사 — JSON이 점유 표식, PNG는 다음 프레임에 생김).
- PNG `<stem>.png`(뷰포트 있음) / `<stem>00000.png`(`-nullrhi` 등 뷰포트 크기 0 → `HighResShot` 폴백, WP-05 규약; 실제로는 nullrhi에서 파일이 생기지 않음). 메타는 두 경우 모두 `<stem>.json`, **요청 직전에 동기 기록**(`FFileHelper::SaveStringToFile`, UTF-8, 개행 `\n`); 실패면 스크린샷을 요청하지 않는다(`ERROR cannot write meta <path>`). 실효 배율이 요청과 다르면(1x 강등) 같은 파일을 다시 쓴다.
- 메타 스키마(`version` 1) — WP 문서 §2와 런북 §5에 같은 표:

| 필드 | 형 | 규칙 |
|---|---|---|
| `version` | int | 1 |
| `time_utc` | string | `FDateTime::UtcNow().ToString(TEXT("%Y-%m-%dT%H:%M:%SZ"))`(경로 JSON `created`와 같은 방식; 밀리초 없음) |
| `preset` | string 또는 null | `AGolmokTimeOfDay::CurrentPreset`; 액터 없음/`None`이면 `null`. 실내 오버레이는 별도 표기 없음 |
| `zone_id` / `zone_version` | string / int **또는 둘 다 null** | §6-2의 zone(`FindLoadedZoneAt(캐릭터 XY)`); 없으면 둘 다 `null`(한쪽만 null 금지 — 구조체가 bool 하나로 묶음) |
| `lon` / `lat` / `height_m` | number×3 **또는 셋 다 null** | **카메라(폰) 위치**의 `UGolmokGeoSubsystem::LevelUEToLonLat`(인자 순서 Lat, Lon [확인 `GolmokGeoSubsystem.h:55`]); 원점 없음(false) → 셋 다 `null`. 7·7·3자리(≈1 cm) |
| `ue_location` | [x, y, z] cm | 카메라(폰) 액터 위치, 2자리 |
| `rotation` | [pitch, yaw, roll] deg | 카메라 회전(roll 포함), 3자리 |
| `fov` | number | 1자리 |
| `exposure_ev` | number | 상대 EV(프리셋 bias 위에 더한 값), 2자리 |
| `dof` | `{"enabled": bool, "focal_m": n, "fstop": n}` | 3·2자리; off여도 값은 기록(켜면 쓸 값) |
| `multiplier` | int | **실효 배율**(`MaxMultiplier` 상한·`SetResolution`/`TakeHighResScreenShot` 강등 반영; 폴백 경로는 요청 배율) |
| `character_hidden` | bool | 촬영 시 캐릭터 숨김 여부 |

바이트 규약(`GolmokPhotoMath::FormatPhotoMetaJson`, `GolmokStatsMath::FormatFixed`·`JsonQuote` 사용): 키 순서 위 표 그대로, **한 필드 한 줄**, 2칸 들여쓰기, 배열·`dof`는 한 줄, 파일 끝 `\n`. 예(zone·geo 있음):
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
null 예: `"preset": null,` · `"zone_id": null,\n  "zone_version": null,` · `"lon": null,\n  "lat": null,\n  "height_m": null,`. Python 왕복 계약은 WP-05 경로 JSON과 같이 두 단계: 이 예제는 **바이트 동일**, 임의 입력은 `json.loads` 뒤 값 동일(1e-6)·키 순서 동일(`list(d)`).

#### 2-3 상태 문자열
`golmok.photo`(전이 때마다·인자 없이 토글) 로그 `golmok.photo: <메시지>`, 오류는 `ERROR ` 접두(Debug 규약). 메시지(런북이 대조): `photo mode on (fov 80.0, zone z_synthetic_001 v1, paused)` / `photo mode on (fov 80.0, no zone, already paused)` / `photo mode off (restored, unpaused, tod shift 0.000 s)` / `ERROR cannot enter: not in a game world` · `already active` · `cannot enter while a path is playing (golmok.path stopplay first)` · `cannot enter while recording '<name>'` · `photo.json: <error>` · `no player controller / pawn` · `pause refused` / `ERROR not active` / `ERROR capture in progress` / `ERROR cannot write meta <path>`. `golmok.photo.shoot` 성공: `shooting -> <dir>/<stem>.png (2x, meta <stem>.json)`; 캡처 종료 로그 `photo: capture window closed (<stem>.png present after 0.31 s)` / `(… timeout 3.0 s, png absent)`. `Describe()`가 오버레이 1~2줄과 같은 문자열을 만든다.

#### 2-4 법·정책 문구(`docs/research/05-legal-policy.md` "변호사 자문 필요 항목")
7. **사용자 촬영 스크린샷의 외부 공유**(D-013 포토 모드): 재구성 골목에 남은 간판·상호·블러가 누락된 얼굴이 사용자의 사진으로 SNS 등에 재배포될 때의 책임 범위(이미 인용된 개인정보 보호법 제25조의2의 목적 외 이용, 저작권법 제35조 제2항; 상표·초상은 자문 대상), 게임 내 워터마크·메타데이터 제거·공유 약관으로 줄일 수 있는지. 판단은 D-009 자문. (새 법 조문은 추측하지 않는다 — F13.)

### 3. 클래스·함수 시그니처

#### 3-1 `Photo/GolmokPhotoMath.h`(순수; include는 `<algorithm> <array> <cmath> <cstddef> <cstdint> <string> <vector>` ⊆ StatsMath 허용 집합 + 따옴표 **정확히** `"Geo/GolmokGeoMath.h"`·`"Debug/GolmokStatsMath.h"`; `std::min/max`·`printf`·`<cstdio>`·`PI`·`TEXT(`·`FVector`·`UE_LOG` 금지; 전부 `inline`, double)
```cpp
#pragma once
// Pure header (no Unreal types): tools/tests/test_ue_photo_math.py compiles it with g++ (fixtures/ue/photomath_driver.cpp)
// and cross-checks it against numpy / shapely. The only quoted includes are the two other pure headers of the module:
// Geo/GolmokGeoMath.h (PointInPolygon, DistanceToSegment) and Debug/GolmokStatsMath.h (FormatFixed, JsonQuote). Same
// rules as those headers (own min/max, no C stdio, C++17, -Wall -Wextra -Werror -pedantic). Units: cm for level UE
// positions, m for the JSON-facing values, degrees for angles.
#include "Debug/GolmokStatsMath.h"
#include "Geo/GolmokGeoMath.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace GolmokPhotoMath
{
	using Vec3 = std::array<double, 3>;

	// ---- parameters ------------------------------------------------------------------------------------------
	/** Lo <= Hi assumed (swapped when not); NaN -> Lo. */
	inline double ClampParam(double V, double Lo, double Hi);
	/** k = round((V - Min) / Step) clamped to [0, floor((Max - Min) / Step + 1e-9)]; returns Min + k * Step. */
	inline double Quantize(double V, double Min, double Max, double Step);
	/** Quantize(V + Dir * Step): Dir in {-1, 0, +1} (any |Dir| >= 1 counts as one step). */
	inline double StepLinear(double V, double Min, double Max, double Step, int Dir);
	/** V * Ratio^Dir clamped to [Min, Max], rounded to 3 decimals (focus distance). Dir 0 -> clamped V. */
	inline double StepGeometric(double V, double Min, double Max, double Ratio, int Dir);
	/** Index of the nearest table value (ties: lower index); StepTable moves that index by Dir (clamped). Empty table -> V. */
	inline std::size_t NearestIndex(const std::vector<double>& Table, double V);
	inline double StepTable(const std::vector<double>& Table, double V, int Dir);
	/** Wrap degrees into (-180, 180]. */
	inline double WrapDeg180(double Deg);
	/** 35 mm-equivalent focal length for a horizontal FOV: SensorWidthMm / (2 tan(fov / 2)); fov clamped to [1, 179]. Overlay only. */
	inline double FovToFocalMm(double FovDeg, double SensorWidthMm = 36.0);

	// ---- constraints (level UE cm) ---------------------------------------------------------------------------
	/** P clamped into the closed ball (Center, RadiusCm). Returns true when it moved. RadiusCm <= 0 -> Center. */
	inline bool ClampToSphere(const Vec3& Center, double RadiusCm, Vec3& P);
	/** Nearest point of the ring boundary (parallel arrays, N >= 3) to (X, Y); returns its distance, OutEdge = segment j (j -> j+1), ties: lowest j. */
	inline double NearestBoundaryPoint(const double* Xs, const double* Ys, std::size_t N, double X, double Y, double& OutX, double& OutY, std::size_t& OutEdge);
	// (V-09 후속 2026-09-27: 아래 함수들 + MeetsConstraint + Constraint 두 필드 추가, ClampToPolygonXY·Constrain 의미 변경 — §6-2)
	inline double RingArea2(const double* Xs, const double* Ys, std::size_t N);   // 부호 면적 x2 (> 0 반시계)
	inline bool InErodedRing(const double* Xs, const double* Ys, std::size_t N, double Inset, double X, double Y); // 안 ∧ 경계 거리 >= Inset - 1e-6
	inline double SignedBoundaryDistance(const double* Xs, const double* Ys, std::size_t N, double X, double Y); // 안 +, 밖 -
	inline double EffectiveInsetCm(const double* Xs, const double* Ys, std::size_t N, double AnchorX, double AnchorY, double InsetCm);
	/**
	 * XY clamp into the eroded ring S = {inside and boundary distance >= EffectiveInsetCm}: in S -> 0, unchanged; else
	 * the exact nearest point of S (candidates: projections onto the inset-shifted edges and the vertex arcs, their
	 * pairwise intersections, the anchor) -> 1; no candidate in S (degenerate ring) -> 2, X/Y unchanged. N < 3 -> 0.
	 */
	inline int ClampToPolygonXY(const double* Xs, const double* Ys, std::size_t N, double AnchorX, double AnchorY, double InsetCm, double& X, double& Y);
	struct Constraint
	{
		Vec3 Anchor{};                     // character capsule center
		double RadiusCm = 300.0;           // MaxDistanceM * 100
		double InsetCm = 20.0;             // FootprintMarginM * 100
		const double* Xs = nullptr;        // footprint ring (level UE cm), N = 0 -> no polygon
		const double* Ys = nullptr;
		std::size_t N = 0;
		bool bHasCurrent = false;          // Current = the pawn's position before this move
		Vec3 Current{};
	};
	inline double MoveInsetCm(const Constraint& C); // InsetCm, lowered to Current's boundary distance when Current is inside the band
	/**
	 * Sphere -> polygon (up to ConstrainMaxRounds = 16 rounds), then re-checked: inside the sphere AND (N == 0 or ClampToPolygonXY == 0 with
	 * MoveInsetCm); not converged -> farthest valid point of Current -> last point (bisection). Returns 0 / 1 (sphere) / 2 (polygon) / 3 (both) / -1 = rejected (Out untouched). The pawn calls it
	 * before each of its (at most 2) sweeps.
	 */
	inline int Constrain(const Constraint& C, const Vec3& Desired, Vec3& Out);

	// ---- meta json -------------------------------------------------------------------------------------------
	struct PhotoMeta
	{
		int Version = 1;
		std::string TimeUtc;                       // "YYYY-MM-DDThh:mm:ssZ"
		bool bHasPreset = false;  std::string Preset;
		bool bHasZone = false;    std::string ZoneId;  int ZoneVersion = 0;
		bool bHasGeo = false;     double Lon = 0.0, Lat = 0.0, HeightM = 0.0;
		Vec3 UeLocation{};  Vec3 Rotation{};       // cm; pitch yaw roll deg
		double Fov = 65.0;  double ExposureEv = 0.0;
		bool bDofEnabled = false;  double FocalM = 3.0;  double Fstop = 2.8;
		int Multiplier = 2;  bool bCharacterHidden = false;
	};
	/** Exact section 2-2 layout (fixed key order, one key per line, 2-space indent, trailing "\n"). Never fails. */
	inline std::string FormatPhotoMetaJson(const PhotoMeta& M);
} // namespace GolmokPhotoMath
```
드라이버·pytest는 `-I Source/Golmok`으로 컴파일한다(두 헤더 모두 그 아래). 함수 인자 이름은 멤버와 겹칠 일이 없는 자유 함수지만 서브시스템·폰의 멤버 함수 `StepParam` 등에서 부를 때는 항상 `GolmokPhotoMath::` 한정(J-engine-14).

#### 3-2 `Photo/GolmokPhotoModeSubsystem.h`
```cpp
/** GamePause: UGameplayStatics::SetGamePaused. TimeDilation: SetGlobalTimeDilation(0.0001) + character CustomTimeDilation 0 (PC fallback). */
UENUM()
enum class EGolmokPhotoPauseMode : uint8 { GamePause, TimeDilation };

/** Not reflected. Exiting is the transient state of Exit() itself (re-entrancy guard for the pawn's EndPlay). */
enum class EGolmokPhotoState : uint8 { Inactive, Active, Shooting, Captured, Exiting };
enum class EGolmokPhotoParam : uint8 { Fov, Ev, Focus, Fstop, Roll };

/** One entry of photo.json "params" (linear / geometric / table). */
struct FGolmokPhotoParamSpec
{
	FString Label, Unit;
	double Default = 0.0, Min = 0.0, Max = 0.0, Step = 0.0, StepRatio = 0.0;
	TArray<double> Values;                                    // non-empty = table parameter
	bool IsTable() const { return Values.Num() > 0; }
	bool IsGeometric() const { return StepRatio > 0.0; }
};

/** Config/Golmok/photo.json (§2-1). Plain struct, no reflection, no built-in defaults: a failed load refuses Enter(). */
struct FGolmokPhotoConfig
{
	FGolmokPhotoParamSpec Params[5];                          // EGolmokPhotoParam order (file order is validated to match)
	bool bDofDefault = false, bCharacterHiddenDefault = false, bOverlayHiddenDefault = false;
	TArray<FString> HintsKeyboard, HintsGamepad;
	const FGolmokPhotoParamSpec& Spec(EGolmokPhotoParam P) const { return Params[static_cast<int32>(P)]; }
};

/** Parser helpers live in a NAMED namespace (unity build: GolmokLightingJson precedent). Static args are In*/Out* (C4458). */
namespace GolmokPhotoJson
{
	/** Parse + validate (§2-1 rules). Error: "photo.json: <where>: <why>". TryGetField(FStringView); key enumeration via FString(*Pair.Key). */
	bool ParseConfigText(const FString& InJson, FGolmokPhotoConfig& Out, FString& OutError);
	bool LoadConfigFile(const FString& InFilePath, FGolmokPhotoConfig& Out, FString& OutError);   // FFileHelper::LoadFileToString
}

UCLASS(Config = Game)
class GOLMOK_API UGolmokPhotoModeSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()
public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;   // Game / PIE (WP-05 pattern, V-03 ok)
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;                // clamps ini values (§7); photo.json is loaded lazily
	virtual void Deinitialize() override;                                                  // Active: TeardownForDeadWorld() (no PC / pause / view target calls)

	// ---- Config (1:1 with [/Script/Golmok.GolmokPhotoModeSubsystem]; two-line declarations) ----
	/** Relative to <Project>/Config unless absolute (same rule as AGolmokTimeOfDay::PresetsFile). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo")
	FString ConfigFile = TEXT("Golmok/photo.json");
	/** Under <Project>/Saved/: <stamp>.png + <stamp>.json. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo")
	FString PhotoFolder = TEXT("Screenshots/Golmok/photo");
	/** HighResShot multiplier of a photo (capped by MaxMultiplier). Distinct from GolmokDebugSubsystem.ScreenshotMultiplier. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo", meta = (ClampMin = "1", ClampMax = "8"))
	int32 ScreenshotMultiplier = 2;
	/** Upper bound of the photo multiplier (VRAM; runbook section 6 measures 2 and 3 on the RTX 5060 8 GB). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo", meta = (ClampMin = "1", ClampMax = "8"))
	int32 MaxMultiplier = 3;
	/** Free-camera sphere radius around the character's capsule center (m). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo", meta = (ClampMin = "0.5", ClampMax = "20.0"))
	float MaxDistanceM = 3.f;
	/** Sweep sphere radius of the camera pawn (cm): never closer than this to geometry; holes narrower than 2x are impassable. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo", meta = (ClampMin = "5.0", ClampMax = "50.0"))
	float CollisionRadiusCm = 15.f;
	/** Clamped this far inside the loaded zone footprint the character stands in (m). 0 = boundary. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo", meta = (ClampMin = "0.0"))
	float FootprintMarginM = 0.2f;
	/** Camera move speed (m/s); Shift / L3 triples it. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo", meta = (ClampMin = "0.1"))
	float MoveSpeedMps = 1.5f;
	/** Frames with overlay / HUD hidden and input frozen before the request (0 = request in the Shoot() tick). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo", meta = (ClampMin = "0", ClampMax = "60"))
	int32 PreCaptureFrames = 2;
	/** Frames the hide is kept after the request at least (the file renders on the next Draw; the png poll / 3 s timeout ends it). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo", meta = (ClampMin = "1", ClampMax = "10"))
	int32 PostCaptureFrames = 2;
	/** GamePause (default) or TimeDilation (PC fallback when input / camera do not update while paused). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Photo")
	EGolmokPhotoPauseMode PauseMode = EGolmokPhotoPauseMode::GamePause;

	// ---- state machine (§4) ----
	bool Enter(FString& OutMessage);             // Inactive -> Active; false + message when refused
	bool Exit(const TCHAR* Reason);              // Active -> Inactive; Shooting / Captured -> bExitPending; Inactive -> false
	bool Toggle(FString& OutMessage);
	bool Shoot(FString& OutMessage);             // Active -> Shooting
	void Reset();                                // §0 #12
	bool IsActive() const { return State != EGolmokPhotoState::Inactive; }
	bool IsCapturing() const { return State == EGolmokPhotoState::Shooting || State == EGolmokPhotoState::Captured; }
	EGolmokPhotoState GetState() const { return State; }
	static UGolmokPhotoModeSubsystem* Get(UWorld* World);       // null outside game worlds
	static bool IsActiveIn(UWorld* World);                       // UGolmokDebugSubsystem::StartPlayback / StartRecording refuse when true

	// ---- parameters (input handlers, console golmok.photo.set and tests share these) ----
	void StepParam(EGolmokPhotoParam P, int32 Dir);              // one key press -> GolmokPhotoMath::Step*(...) -> ApplyToPawn()
	bool SetParam(EGolmokPhotoParam P, double Value, FString& OutMessage);   // quantized / nearest / clamped
	double GetParam(EGolmokPhotoParam P) const;
	void SetDofEnabled(bool bOn);  bool IsDofEnabled() const { return bDof; }
	void SetCharacterHidden(bool bHidden);  bool IsCharacterHidden() const { return bCharacterHidden; }
	void SetOverlayHidden(bool bHidden);    bool IsOverlayHidden() const { return bOverlayHidden; }
	bool SetMultiplier(int32 InMultiplier, FString& OutMessage);   // golmok.photo.set mult: 1..MaxMultiplier (session override)
	static bool ParseParamName(const FString& InName, EGolmokPhotoParam& Out);   // fov|ev|focus|fstop|roll
	static const TCHAR* ParamName(EGolmokPhotoParam P);

	// ---- config ----
	bool EnsureConfig();                                         // loads once; false + LastError (Error log once) — Enter() refuses
	const FGolmokPhotoConfig* GetConfig() const { return bConfigLoaded ? &Config : nullptr; }
	FString ResolveConfigPath() const;                           // FPaths::ProjectConfigDir() / ConfigFile
	const FString& GetLastError() const { return LastError; }

	// ---- HUD hooks (AGolmokHUD) ----
	/** True while nothing at all may draw (Shooting / Captured). */
	bool IsHudSuppressed() const { return IsCapturing(); }
	/** Bottom-left lines (§5-3); empty when inactive, capturing or the overlay is hidden. Cached 0.25 s like the debug HUD. */
	const TArray<FString>& GetOverlayLines();
	FString Describe() const;                                    // "inactive" | "active fov 65.0 ev +0.33 focus 3.000 m f/2.80 dof off roll +0.0 (zone z_x v1)" | "shooting" | "captured"

	// ---- input (called by AGolmokPlayerController::SetupInputComponent) ----
	/** Creates the 21 actions + IMC_GolmokPhoto once (owned here, Transient) and binds the handlers on this object. */
	void BindInput(UEnhancedInputComponent* Input);

	// ---- constraint inputs / meta (public for the tests) ----
	FVector GetAnchor() const;                                   // character capsule center (SavedPawn actor location); entry camera location without a pawn
	const TArray<double>& GetFootprintXs() const { return FootprintXs; }
	const TArray<double>& GetFootprintYs() const { return FootprintYs; }
	void SetFootprintForTest(const TArray<FVector2D>& LevelUEPolygonCm);   // overrides the cached polygon while Active
	GolmokPhotoMath::PhotoMeta BuildMeta(int32 InMultiplier) const;         // §2-2 null rules from the current pose
	AGolmokPhotoCameraPawn* GetPhotoPawn() const { return PhotoPawn.Get(); }
	const FString& GetLastShotPathNoExt() const { return LastShotPathNoExt; }
	int32 GetPawnTickCount() const;                              // pawn tick counter (EnterExit: ticks while paused)

	/** Called by AGolmokPhotoCameraPawn::EndPlay (§4-3 exit paths). */
	void OnPhotoPawnEndPlay(AGolmokPhotoCameraPawn* Pawn, EEndPlayReason::Type Reason);

private:
	// input handlers (one per action; Started unless noted)
	void OnShoot();  void OnReset();  void OnDof();  void OnHideCharacter();  void OnHideOverlay();
	void OnFovUp();  void OnFovDown();  void OnFovWheel(const FInputActionValue& Value);   // Triggered: sign -> +-1 step
	void OnEvUp();  void OnEvDown();  void OnFocusUp();  void OnFocusDown();  void OnFstopUp();  void OnFstopDown();
	void OnRollUp();  void OnRollDown();
	void OnMove(const FInputActionValue& Value);  void OnMoveEnd(const FInputActionValue& Value);      // Triggered / Completed
	void OnUpDown(const FInputActionValue& Value);  void OnUpDownEnd(const FInputActionValue& Value);
	void OnLook(const FInputActionValue& Value);     // Mouse2D, Triggered: delta -> AddLookMouse
	void OnLookPad(const FInputActionValue& Value);  // Gamepad_Right2D, Triggered/Completed: value -> SetLookPad
	void OnFastStart();  void OnFastEnd();

	void EnsureInputAssets(UObject* Outer);
	void AddPhotoContext(bool bOn);                              // IMC_GolmokPhoto at PhotoMappingPriority (3), Active only
	void ApplyPause(bool bOn);                                   // PauseMode branch; honours bWasPausedBefore
	void ApplyToPawn();                                          // values -> pawn (FOV, roll, PP overrides), character hidden
	void CacheFootprint();                                       // §6-2
	void OnEndFrame();                                           // capture counter: Shooting -> request -> Captured -> restore
	void RequestShot();                                          // stem, meta, RequestHighResScreenshot, effective multiplier
	bool WriteMeta(const FString& InJsonPath, const GolmokPhotoMath::PhotoMeta& M, FString& OutError);
	FString NextStemPath() const;                                // <Saved>/<PhotoFolder>/<stamp>[_n]
	void RestoreAll();                                           // §4-3 (live world)
	void TeardownForDeadWorld();                                 // §4-3 (EndPlayInEditor / Quit / bIsTearingDown)
	double BaseExposureBias() const;                             // AGolmokTimeOfDay::CaptureState().ExposureBias or DefaultAutoExposureBias()
	UGolmokDebugSubsystem* GetDebug() const;  AGolmokTimeOfDay* GetTimeOfDay() const;  AGolmokPlayerController* GetPC() const;

	static constexpr int32 PhotoMappingPriority = 3;             // above IMC_GolmokPhotoToggle (2) and IMC_GolmokDebug (1)
	static constexpr double CaptureTimeoutSeconds = 3.0;
	static constexpr float FastMultiplier = 3.f;
	static constexpr float MouseLookDegPerUnit = 0.5f;
	static constexpr float PadLookDegPerSec = 120.f;

	UPROPERTY(Transient) TObjectPtr<UInputMappingContext> PhotoContext;   // IMC_GolmokPhoto
	UPROPERTY(Transient) TArray<TObjectPtr<UInputAction>> Actions;        // keeps the 21 actions alive (named raw pointers below index it)
	// (names: IA_GolmokPhotoShoot Reset Dof HideCharacter HideOverlay FovUp FovDown FovWheel EvUp EvDown FocusUp FocusDown FstopUp FstopDown RollUp RollDown Move UpDown Look LookPad Fast)

	EGolmokPhotoState State = EGolmokPhotoState::Inactive;
	FGolmokPhotoConfig Config;  bool bConfigLoaded = false, bConfigFailed = false;  FString LastError;
	double Values[5] = {65.0, 0.0, 3.0, 2.8, 0.0};               // overwritten from photo.json at the first Enter (never used before)
	bool bDof = false, bCharacterHidden = false, bOverlayHidden = false;
	int32 SessionMultiplier = 0;                                 // 0 = ini ScreenshotMultiplier
	bool bExitPending = false;
	// saved at Enter, restored at Exit
	TWeakObjectPtr<AGolmokPhotoCameraPawn> PhotoPawn;  TWeakObjectPtr<APawn> SavedPawn;  TWeakObjectPtr<AActor> SavedViewTarget;
	FRotator SavedControlRotation = FRotator::ZeroRotator;
	bool bWasPausedBefore = false, bSavedFullTickWhenPaused = false, bSavedHudVisible = false, bSavedPawnHidden = false;
	bool bSavedSuppressTransition = false, bDebugKeysWereActive = false;
	float SavedTimeDilation = 1.f, SavedPawnTimeDilation = 1.f;
	double WorldTimeAtEnter = 0.0;  FVector EnterLocation = FVector::ZeroVector;  FRotator EnterRotation = FRotator::ZeroRotator;  float EnterFov = 80.f;
	TArray<double> FootprintXs, FootprintYs;  FString FootprintZoneId;  int32 FootprintZoneVersion = 0;
	// capture
	FDelegateHandle EndFrameHandle;  int32 CaptureFrameCounter = 0;  double CaptureRequestRealSeconds = 0.0;
	FString LastShotPathNoExt;  int32 LastEffectiveMultiplier = 0;  double SavedMessageUntilRealSeconds = 0.0;
	TArray<FString> OverlayLines;  double OverlayLinesRealSeconds = -1.0;  bool bOverlayDirty = true;
};
```
콘솔(`.cpp` 익명 namespace, 이름은 `Photo*` 접두: `PhotoSubsystemFor`, `PhotoParseToggle`, `CmdPhoto`, `CmdPhotoShoot`, `CmdPhotoReset`, `CmdPhotoSet`; 전부 `FAutoConsoleCommandWithWorldAndArgs` [확인 V-03]):
| 명령 | 동작 |
|---|---|
| `golmok.photo [0\|1]` | 인자 없으면 `Toggle`, `1`/`0`이면 `Enter`/`Exit`. 메시지 §2-3 |
| `golmok.photo.shoot` | `Shoot` |
| `golmok.photo.reset` | `Reset` → `reset (fov 65.0 ev +0.00 focus 3.000 f/2.80 dof off roll +0.0, character shown, overlay shown, pose restored)` |
| `golmok.photo.set <name> <value>` | `fov\|ev\|focus\|fstop\|roll <number>`(양자화·클램프), `dof\|char\|overlay 0\|1`, `mult <n>`(1..`MaxMultiplier`). 런북·자동화용 |

#### 3-3 `Photo/GolmokPhotoCameraPawn.h`
```cpp
UCLASS(NotPlaceable, NotBlueprintable)
class GOLMOK_API AGolmokPhotoCameraPawn : public APawn
{
	GENERATED_BODY()
public:
	AGolmokPhotoCameraPawn();
	// PrimaryActorTick.bCanEverTick = bStartWithTickEnabled = bTickEvenWhenPaused = true; AutoPossessPlayer = Disabled.
	// Sphere (root): radius set in Init, QueryOnly, ObjectType ECC_WorldDynamic, all channels Ignore then WorldStatic / WorldDynamic Block
	//   (Pawn / Camera / Visibility Ignore), bGenerateOverlapEvents = false, hidden. Camera: attached to Sphere, bUsePawnControlRotation = false,
	//   PostProcessBlendWeight = 1. bFindCameraComponentWhenViewTarget stays true (view target without possession, §10 #17).
	void Init(UGolmokPhotoModeSubsystem* InOwner, const FVector& InLocation, const FRotator& InLookRotation, float InFov, float InRadiusCm);
	UCameraComponent* GetCamera() const { return Camera; }

	// raw input written by the subsystem's handlers; Tick consumes it. Ignored while Owner->IsCapturing().
	void SetMoveInput(const FVector2D& InLocal);  void SetUpDownInput(float InAxis);
	void AddLookMouse(const FVector2D& InDelta);  void SetLookPad(const FVector2D& InStick);
	void SetFast(bool bInFast);

	/** Pitch / yaw actor rotation (pitch clamped +-89), roll on the camera component only. */
	void ApplyLook(const FRotator& InLook);
	/** SetFieldOfView + PostProcessSettings overrides (§6-4): exposure bias, DOF (focal 0 when off), motion blur 0. */
	void ApplyOptics(float InFov, double InExposureBias, bool bInDof, double InFocusM, double InFstop);
	FRotator GetLook() const { return Look; }
	void SetRoll(float InRollDeg);

	/** One constraint + sweep step toward InDesired (public test hook; Tick calls it with Location + Velocity * dt). */
	void MoveConstrained(const FVector& InDesired);
	int32 GetTickCount() const { return TickCount; }
	virtual void Tick(float DeltaSeconds) override;              // dt = clamp(FApp::GetDeltaTime(), 0, 0.1) (§10 #2)
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;   // Owner->OnPhotoPawnEndPlay(this, Reason)
private:
	UPROPERTY(VisibleAnywhere, Category = "Golmok|Photo") TObjectPtr<USphereComponent> Sphere;
	UPROPERTY(VisibleAnywhere, Category = "Golmok|Photo") TObjectPtr<UCameraComponent> Camera;
	TWeakObjectPtr<UGolmokPhotoModeSubsystem> Owner;
	FRotator Look = FRotator::ZeroRotator;  float RollDeg = 0.f;
	FVector2D MoveInput = FVector2D::ZeroVector;  float UpDownInput = 0.f;
	FVector2D MouseDelta = FVector2D::ZeroVector;  FVector2D PadStick = FVector2D::ZeroVector;
	bool bFast = false;  float RadiusCm = 15.f;  int32 TickCount = 0;
};
```
Tick(정지 중에도 실행, 입력 동결 중이면 카운터만 증가): `LocalDt = clamp(FApp::GetDeltaTime(), 0, 0.1)` → `Look.Yaw += MouseDelta.X * MouseLookDegPerUnit + PadStick.X * PadLookDegPerSec * LocalDt`, `Look.Pitch = clamp(Look.Pitch − MouseDelta.Y * … − PadStick.Y * …, −89, 89)`, `MouseDelta = 0` → `ApplyLook` → 목표 = 위치 + (전방(yaw만 — D-013 결정 3 확정판, PR #40 리뷰 뒤; 처음 설계는 '피치 포함')·MoveInput.Y + 우측(yaw만)·MoveInput.X + 월드 상·UpDownInput).GetClampedToMaxSize(1) × `MoveSpeedMps·100·(bFast ? 3 : 1)` × LocalDt → `MoveConstrained(목표)`. `MoveConstrained`: `Constrain(C, Desired, Out)` < 0이면 return(취소) → `SetActorLocation(Out, /*bSweep*/ true, &Hit)` → `Hit.bStartPenetrating`이면 `SetActorLocation(Location + (Anchor − Location).GetSafeNormal() * 10, true)`(후퇴). ~~슬라이드 없음.~~ (V-09 후속) 막히면 `Slide = VectorPlaneProject((Target − Start) * (1 − Hit.Time), Hit.Normal)`, 0.01 cm 이상이면 `Current = 현재 위치`로 `Constrain` → 두 번째 스윕(최대 2회).

#### 3-4 `Debug/GolmokDebugSubsystem.h` 추가·변경
```cpp
	/**
	 * Public part of TakeScreenshot for callers that own the path: requests <AbsolutePathNoExt>.png at InMultiplier x the game
	 * viewport. OutEffectiveMultiplier = what was applied: drops to 1 when SetResolution() refuses or TakeHighResScreenShot()
	 * returns false at the requested size (retried once at 1x); the requested value on the HighResShot console fallback
	 * (no sized viewport, file <name>00000.png). Messages are the three golmok.screenshot strings (unchanged).
	 */
	bool RequestHighResScreenshot(const FString& InAbsolutePathNoExt, int32 InMultiplier, FString& OutMessage, int32& OutEffectiveMultiplier);
```
`TakeScreenshot`은 태그·이름 검증, 디렉터리 조립·`MakeDirectory` 뒤 `RequestHighResScreenshot(FullPath, ScreenshotMultiplier, OutMessage, Effective)`를 부른다. `StartPlayback`·`StartRecording` 첫 검사: `if (UGolmokPhotoModeSubsystem::IsActiveIn(GetWorld())) { OutMessage = TEXT("photo mode is on (golmok.photo 0 first)"); return false; }`.

#### 3-5 `Debug/GolmokHUD.cpp` 변경(`DrawHUD` 첫머리; 헤더는 주석 정정만)
```cpp
	UGolmokPhotoModeSubsystem* Photo = World ? World->GetSubsystem<UGolmokPhotoModeSubsystem>() : nullptr;
	if (Photo && Photo->IsHudSuppressed()) { return; }                       // capture frames: nothing at all (debug HUD included)
	... 기존 디버그 HUD(변경 없음) ...
	if (Photo && Photo->IsActive() && !Photo->IsOverlayHidden())              // bottom-left box: Canvas->SizeY - MarginPx - Lines * LineH
	{
		const TArray<FString>& PhotoLines = Photo->GetOverlayLines();          // §5-3: 1 status line, 1 values line, 1..4 hint lines, 1 "saved" line (2.5 s)
		DrawRect(..., MarginPx - 6.f, Y - 4.f, 640.f * HudScale, PhotoLines.Num() * LineH + 8.f);
		for (...) DrawText(PhotoLines[i], i == 0 ? HudWhite : (i == 1 ? HudCyan : HudGray), MarginPx, Y + i * LineH, Font, HudScale);
	}
```
`AGolmokHUD` ini 키 추가 없음(`MarginPx`·`HudScale` 재사용). `UCanvas::SizeY`는 [2차] → §10 #31(`ClipY`).

#### 3-6 `Player/GolmokPlayerController` 추가
```cpp
public:
	/** true: IMC_GolmokDebug removed (photo mode); false: re-added when bDebugKeysEnabled. AddMappingContext() early-returns while suspended. */
	void SetDebugKeysSuspended(bool bSuspended);
	bool IsDebugKeysSuspended() const { return bDebugKeysSuspended; }
	static constexpr int32 PhotoTogglePriority = 2;
private:
	void OnTogglePhoto();                                        // Photo->Toggle(Msg); logs "P: <msg>"
	UPROPERTY(Transient) TObjectPtr<UInputMappingContext> PhotoToggleContext;   // IMC_GolmokPhotoToggle: P, Gamepad_Special_Left; always added (bDebugKeysEnabled-independent)
	/** P / Gamepad_Special_Left (bTriggerWhenPaused = true) */
	UPROPERTY(Transient) TObjectPtr<UInputAction> PhotoToggleAction;              // IA_GolmokPhotoToggle
	bool bDebugKeysSuspended = false;
```
`EnsureInputAssets`: `PhotoToggleAction = MakeBoolAction(TEXT("IA_GolmokPhotoToggle")); PhotoToggleAction->bTriggerWhenPaused = true; PhotoToggleAction->bConsumeInput = true;` + `PhotoToggleContext = NewObject<UInputMappingContext>(this, TEXT("IMC_GolmokPhotoToggle"))`, `MapKey(P)`, `MapKey(Gamepad_Special_Left)`. `AddMappingContext()`: 토글 컨텍스트는 `bDebugKeysEnabled`와 무관하게 `PhotoTogglePriority`로 항상; 디버그 컨텍스트는 `bDebugKeysEnabled && !bDebugKeysSuspended`일 때만. `SetupInputComponent`: 기존 9개 바인딩 뒤 `Input->BindAction(PhotoToggleAction, ETriggerEvent::Started, this, &AGolmokPlayerController::OnTogglePhoto);` + `if (UGolmokPhotoModeSubsystem* Photo = UGolmokPhotoModeSubsystem::Get(GetWorld())) { Photo->BindInput(Input); }`. 기존 9개 액션·키·이름·`IMC_GolmokDebug` 불변.

#### 3-7 Zones·Lighting 추가(각 1 함수, 그 외 무변경)
```cpp
// Zones/GolmokZoneSubsystem.h (public)
	/** Loaded zone whose footprint contains the level XY point; several -> ZoneWins order (interior 20 before its parent 10). Null when none. Read-only. */
	AGolmokZone* FindLoadedZoneAt(const FVector2D& LevelUEPointCm) const;
// Lighting/GolmokTimeOfDay.h (public)
	/** Moves a running transition's start forward by DeltaSeconds (photo mode: world time that passed while paused). No-op when not transitioning. */
	void ShiftTransitionStart(double DeltaSeconds);
```
`FindLoadedZoneAt`는 `Zones` 레코드를 읽기만 한다(`FootprintContains`가 non-const라 `TWeakObjectPtr::Get()`의 non-const 포인터로 호출 [확인 `GolmokZone.h:165~182`]). `RegisterZone/RequestLoad/RequestUnload` 호출 없음 → `Load()`/`Evaluate()` 스택 규약 무관(pytest가 `Photo/`에 그 문자열 부재를 강제).

### 4. 상태기계·전이표
상태: `Inactive → (Entering) → Active → Shooting → Captured → Active → (Exiting) → Inactive`. `Entering`/`Exiting`은 `Enter()`/`Exit()` 본문 안의 순간 상태(재진입·폰 `EndPlay` 가드).

#### 4-1 전이표
| 현재 | 사건 | 가드 | 동작(순서) | 다음 |
|---|---|---|---|---|
| Inactive | `Enter`(P / `golmok.photo 1`) | 게임/PIE 월드·`!bIsTearingDown`, PC0 있음, `!Debug->IsPlaying() && !IsRecording()`, `EnsureConfig()` | §4-2 진입 시퀀스 | Active |
| Inactive | `Enter` | 가드 실패 | `ERROR cannot enter: <reason>`(§2-3), 상태·엔진 무변경(정지 요청 거부 시 `pause refused`, 이미 만든 폰은 파괴) | Inactive |
| Active | 조절 키·`golmok.photo.set` | — | `StepParam/SetParam` → `ApplyToPawn()`; 캐릭터 숨김은 `SavedPawn->SetActorHiddenInGame`(충돌 유지); `bOverlayDirty` | Active |
| Active | 이동·시선 | — | 폰 입력 버퍼 → 다음 폰 Tick에서 `MoveConstrained`(§6) | Active |
| Active | `Reset` | — | 값 5개 = JSON default, DOF off, 캐릭터 표시, 오버레이 표시, 폰 위치/회전 = `EnterLocation/EnterRotation`(FOV는 default 65, 진입 FOV 아님) | Active |
| Active | `Shoot`(Space·Enter / A / `golmok.photo.shoot`) | 폰 유효 | `State = Shooting`(같은 틱: `IsHudSuppressed()` true → 다음 `DrawHUD`부터 아무것도 안 그림), 폰 입력 동결·`MoveInput = 0`, `CaptureFrameCounter = 0`, `OnEndFrame` 바인딩, 로그 `shooting -> …` | Shooting |
| Shooting | `OnEndFrame` | `++Counter >= PreCaptureFrames` | `RequestShot()`: stem → `BuildMeta(Mult)` → `WriteMeta`(실패: 로그 `ERROR cannot write meta`, `OnEndFrame` 해제, 복원 → Active) → `Debug->RequestHighResScreenshot(Stem, Mult, Msg, Effective)`(false: 메타 삭제, 복원 → Active) → `Effective != Mult`면 메타 재기록 → `CaptureRequestRealSeconds = FPlatformTime::Seconds()`, `Counter = 0` | Captured |
| Captured | `OnEndFrame` | `Counter >= PostCaptureFrames && (PNG 존재 \|\| 실시간 ≥ 3 s)` | `OnEndFrame` 해제 → 로그 `capture window closed (…)` → `SavedMessageUntil` → 입력 동결 해제 → `State = Active` → `bExitPending`이면 `Exit("deferred")` | Active / Inactive |
| Shooting / Captured | `Exit` | — | `bExitPending = true`, `true` 반환(로그 `exit deferred until the capture window closes`) | 동일 |
| Shooting / Captured | `Shoot`·`Reset`·조절·이동 | — | 무시(`ERROR capture in progress` — 콘솔만; 키는 조용히) | 동일 |
| Active | `Exit`(P / `golmok.photo 0`) | — | `State = Exiting` → §4-3 `RestoreAll()` → `State = Inactive` → 로그 `photo mode off (…)` | Inactive |
| Active / Shooting / Captured | 폰 `EndPlay(Destroyed)`·월드 살아 있음 | `State != Exiting` | `Exit("pawn destroyed")`(폰 파괴 단계는 건너뜀) | Inactive |
| 어느 상태 | 폰 `EndPlay(EndPlayInEditor/Quit/LevelTransition/RemovedFromWorld)` 또는 `Deinitialize` 또는 `bIsTearingDown` | — | `TeardownForDeadWorld()`: `OnEndFrame` 해제, IMC·폰 참조 정리, `State = Inactive`, 로그 `photo: teardown (world ending)`. PC·정지·뷰 타깃·시간대는 건드리지 않음 | Inactive |
| Inactive | `Exit`·`Shoot`·`Reset`·`set` | — | `ERROR not active` | Inactive |

#### 4-2 진입 시퀀스(`Enter`)
1. 가드(위). `EnsureConfig()` 실패면 `photo.json: <error>`로 거부(첫 실패에 Error 로그 1회). 첫 성공 로드 때 `Values[] = default`, 토글 = JSON `toggles`.
2. 저장: `SavedPawn = PC->GetPawn()`, `SavedViewTarget = PC->GetViewTarget()`, `SavedControlRotation = PC->GetControlRotation()`, `bWasPausedBefore = UGameplayStatics::IsGamePaused(World)`, `SavedTimeDilation = GetGlobalTimeDilation`(TimeDilation 모드), `bSavedFullTickWhenPaused = PC->bShouldPerformFullTickWhenPaused`(bool 복사), `bSavedHudVisible = Debug->IsHudVisible()`, `bSavedPawnHidden = SavedPawn->IsHidden()`, `bDebugKeysWereActive = !PC->IsDebugKeysSuspended()`, `WorldTimeAtEnter = World->GetTimeSeconds()`, `bSavedSuppressTransition = GameViewport->bSuppressTransitionMessage`(§10 #12), `bSavedCameraMoveableWhenPaused = World->bIsCameraMoveableWhenPaused`(V-09 #57, c026815).
3. 카메라 자세: `Cam = PC->PlayerCameraManager`; `EnterLocation = Cam->GetCameraLocation()`, `EnterRotation = Cam->GetCameraRotation()`(roll 0으로 시작), `EnterFov = Cam->GetFOVAngle()`(§10 #18; 실패 시 80).
4. 폰 스폰(`FActorSpawnParameters{ObjectFlags |= RF_Transient, SpawnCollisionHandlingOverride = AlwaysSpawn}`) at `EnterLocation/EnterRotation` → `Init(this, …, EnterFov, CollisionRadiusCm)` → 시작점 겹침 검사 `World->OverlapBlockingTestByChannel(…, ECC_WorldDynamic, MakeSphere(R))`(§10 #16): 겹치면 앵커 쪽으로 30 cm씩 최대 10회 후퇴.
5. **빙의 없음.** `PC->SetViewTargetWithBlend(PhotoPawn, 0.f)`.
6. `PC->bShouldPerformFullTickWhenPaused = true`; `ApplyPause(true)`: `GamePause`면 `!bWasPausedBefore`일 때 `SetGamePaused(World, true)`(false 반환 → 폰 파괴·뷰 타깃 복원·거부 `pause refused`); `TimeDilation`면 `SetGlobalTimeDilation(World, 0.0001f)` + `SavedPawn->CustomTimeDilation = 0`. 정지 거부 롤백을 지난 뒤 `World->bIsCameraMoveableWhenPaused = true`(V-09 #57: 정지 월드도 뷰 이력 갱신 → 잔상 제거; 롤백 경로에서는 아직 건드리지 않았으므로 복원 불필요).
7. `GameViewport->SetSuppressTransitionMessage(true)`(§10 #12).
8. `Debug->SetHudVisible(false)`; `PC->SetDebugKeysSuspended(true)`.
9. `CacheFootprint()`(§6-2); `Values[Fov] = EnterFov`(나머지는 세션 값 유지); `ApplyToPawn()`(캐릭터 숨김 토글이 켜져 있었으면 즉시 숨김).
10. `AddPhotoContext(true)`; `State = Active`; 로그 `photo mode on (fov 80.0, zone z_synthetic_001 v1, paused)`.

#### 4-3 복원 시퀀스(`Exit` → `RestoreAll`, 살아 있는 월드; 각 단계 널 안전·독립)
`AddPhotoContext(false)` → 폰 입력 0 → `PC->SetViewTargetWithBlend(SavedViewTarget ?: PC->GetPawn(), 0.f)` → `PC->SetControlRotation(SavedControlRotation)` → `PC->PlayerCameraManager->UpdateCamera(0.f)`(V-09b #64: 정지로 시작한 종료 틱은 카메라 매니저 갱신을 건너뛰므로 여기서 캐시를 플레이어 POV·PP로) → `PC->PlayerCameraManager->SetGameCameraCutThisFrame()`(PR #27 리뷰 A2: 포토 카메라의 눈 적응·TSR 이력이 플레이어 뷰로 이어지지 않게; 진입은 같은 POV라 불필요) → `SavedPawn->SetActorHiddenInGame(bSavedPawnHidden)` → `Debug->SetHudVisible(bSavedHudVisible)` → `PC->SetDebugKeysSuspended(false)`(재추가는 `bDebugKeysEnabled && bDebugKeysWereActive`일 때만) → `PC->bShouldPerformFullTickWhenPaused = bSavedFullTickWhenPaused` → `GameViewport->SetSuppressTransitionMessage(bSavedSuppressTransition)` → `ApplyPause(false)`: `GamePause`면 `!bWasPausedBefore`일 때만 `SetGamePaused(World, false)`(**진입 전 정지였으면 유지**); `TimeDilation`면 `SetGlobalTimeDilation(SavedTimeDilation)`·`CustomTimeDilation` 복원 → `World->bIsCameraMoveableWhenPaused = bSavedCameraMoveableWhenPaused`(V-09 #57) — 단 `ApplyPause(false)` 뒤에도 월드가 정지로 남으면(사전 정지 (b)) true로 두고 정지 해제를 본 첫 `OnEndFrame`에 복원(PR #40 리뷰 R1, 런북 §12 #67) → 시간대: `Δ = World->GetTimeSeconds() − WorldTimeAtEnter; if (Tod && Tod->IsTransitioning() && Δ > 0) Tod->ShiftTransitionStart(Δ)` → `PhotoPawn->Destroy()`(EndPlay 재진입은 `State == Exiting`으로 무시) → `OnEndFrame` 해제, footprint 비움 → `State = Inactive` → 로그 `photo mode off (restored, unpaused, tod shift 0.000 s)`.
PostProcess 오버라이드는 폰 카메라 컴포넌트에만 있으므로 폰 파괴 = 복원(PPV·캐릭터 `FollowCamera` 무변경). 포털·zone 타이머는 건드리지 않는다: 빙의를 바꾸지 않고 캐릭터가 제자리이므로 오버랩 변화 자체가 없다(정지 중 타이머 진행 여부 §10 #11은 관찰 항목).

#### 4-4 촬영 프레임의 가시성 보장
| 단계 | 디버그 HUD | 포토 오버레이 | 캐릭터 | 입력 |
|---|---|---|---|---|
| Active | 숨김(진입 시; `golmok.hud 1`로 켤 수 있음) | 표시(O로 숨김) | 토글대로 | 자유 |
| Shooting(`PreCaptureFrames`) | **숨김**(`IsHudSuppressed`) | **숨김** | 토글대로(H 켰으면 숨김 유지) | 동결 |
| 요청 프레임 → Captured | 숨김 | 숨김 | 동일 | 동결 |
| Active 복귀 | 이전 상태 복원 | 복원 + "saved …" 2.5 s | 동일 | 자유 |

`Shoot()`은 입력 콜백(Tick 단계)에서 `State`를 바꾸므로 같은 프레임의 `DrawHUD`가 이미 아무것도 그리지 않는다[2차, §10 #13]; `PreCaptureFrames ≥ 1`이면 요청 전에 최소 한 `Draw`가 숨김 상태로 지나가 순서 가정에 의존하지 않는다(기본 2).

### 5. 입력
#### 5-1 키 표(모든 포토 액션 `bTriggerWhenPaused = true`·`bConsumeInput = true` [확인 필드]; 이름 `IA_GolmokPhoto*`, 컨텍스트 `IMC_GolmokPhotoToggle`(PC, 우선순위 2, 항상)·`IMC_GolmokPhoto`(서브시스템, 우선순위 3, Active만))
| 기능 | 키보드/마우스 | 게임패드 | 액션·타입·이벤트 | 핸들러 |
|---|---|---|---|---|
| 진입/종료 | **P** | **View/Back**(`Gamepad_Special_Left`) | `IA_GolmokPhotoToggle` Bool, Started(토글 IMC) | `AGolmokPlayerController::OnTogglePhoto` → `Toggle()` |
| 촬영 | SpaceBar, Enter | A(`Gamepad_FaceButton_Bottom`) | `Shoot` Bool, Started | `OnShoot` → `Shoot()` |
| 이동 | W S A D(캐릭터와 같은 Swizzle/Negate) | `Gamepad_Left2D` | `Move` Axis2D, Triggered/Completed | `OnMove/OnMoveEnd` → 폰 `SetMoveInput` |
| 상승/하강 | E / Q(Negate) | `Gamepad_RightTriggerAxis` / `Gamepad_LeftTriggerAxis`(Negate) | `UpDown` Axis1D, Triggered/Completed | `OnUpDown/OnUpDownEnd` |
| 시선(마우스) | `Mouse2D`(Y Negate, `bInvertLookY` 규약 그대로) | — | `Look` Axis2D, Triggered | `OnLook` → 폰 `AddLookMouse`(델타) |
| 시선(패드) | — | `Gamepad_Right2D`(Y Negate 같은 규약) | `LookPad` Axis2D, Triggered/Completed | `OnLookPad` → 폰 `SetLookPad`(값; Completed에서 0) |
| 빠르게(×3) | LeftShift | L3(`Gamepad_LeftThumbstick`) | `Fast` Bool, Started/Completed | `OnFastStart/End` |
| FOV −/+ | `[` / `]`(`LeftBracket/RightBracket`), 휠(`MouseWheelAxis`, 위 = 좁게) | D-pad ← / → | `FovDown/FovUp` Bool Started; `FovWheel` Axis1D Triggered | `StepParam(Fov, ∓1)`; 휠은 부호만 |
| EV −/+ | `-` / `=`(`Hyphen/Equals`) | D-pad ↓ / ↑ | `EvDown/EvUp` | `StepParam(Ev, ±1)` |
| focus −/+ | `,` / `.`(`Comma/Period`) | LB / RB(`Gamepad_LeftShoulder/RightShoulder`) | `FocusDown/FocusUp` | `StepParam(Focus, ±1)` |
| f-stop −/+ | N / M | X / Y(`Gamepad_FaceButton_Left/Top`) | `FstopDown/FstopUp` | `StepParam(Fstop, ±1)` |
| roll −/+ | Z / C | (없음 — 힌트에 명시) | `RollDown/RollUp` | `StepParam(Roll, ±1)` |
| DOF on/off | F | R3(`Gamepad_RightThumbstick`) | `Dof` Bool, Started | `SetDofEnabled(!bDof)` |
| 캐릭터 숨김 | H | B(`Gamepad_FaceButton_Right`) | `HideCharacter` | 토글 |
| 오버레이 숨김 | O | (없음 — 촬영 때 자동 숨김이라 필요성 낮음) | `HideOverlay` | 토글 |
| 리셋 | R | Menu(`Gamepad_Special_Right`) | `Reset` | `Reset()` |

충돌 검토: 캐릭터 `IMC_Default`(0)의 W/A/S/D·Mouse2D·Space·LeftShift·L3·A, 디버그 `IMC_GolmokDebug`(1)의 F1~F10·1~4, 엔진 `DebugExecBindings`(ClearArray, F3/F4만)와 새 키 P·`[ ]`·`- =`·`, .`·N M·Z C·F·H·O·R·E·Q·Enter·휠·`Gamepad_Special_*`는 겹치지 않는다. 겹치는 키(WASD·마우스·Space·Shift·L3·A)는 정지 중 캐릭터 액션이 `bTriggerWhenPaused = false`라 발화하지 않고(1차 방어), 포토 IMC가 우선순위 3·`bConsumeInput`으로 소비한다(2차 방어; `TimeDilation` 폴백에서는 이것만 방어 → §10 #5). Esc는 PIE 종료 키라 매핑하지 않는다. 반복 입력(길게 누름)은 없다 — Phase 2 `UInputTriggerPulse`.

#### 5-2 스텝·속도
| 항목 | 값 | 범위를 도는 횟수 | 이유 |
|---|---|---|---|
| FOV | 5°(휠 노치도 5°) | 18 | 20~110 |
| EV | 1/3 EV(정수 스텝, 표시 2자리) | 18 | 카메라 관례 |
| focus | ×1.25, 3자리 반올림 | 23 | 근거리 촘촘 |
| f-stop | 1스톱 표 8개 | 7 | 카메라 눈금 |
| roll | 1° | 30 | 수평 보정 |
| 이동 | 1.5 m/s(Shift/L3 ×3), 스무딩 없음 | — | 반경 3 m 구를 2 s에 가로지름 |
| 시선 | 마우스 0.5°/unit, 패드 120°/s(데드존 모디파이어 없음 — 스틱 데드존은 캐릭터와 같은 기본) | — | 정밀 프레이밍 |
| 피치 | ±89° | — | 짐벌 회피 |

#### 5-3 오버레이(왼쪽 아래, `GEngine->GetSmallFont()`, `HudScale`, 줄 높이 16·`HudScale`, 반투명 검정 박스; 디버그 HUD는 왼쪽 위라 겹치지 않음)
```
PHOTO  z_synthetic_001 v1  overcast_morning  2.4 / 3.0 m  2x        (흰색; zone 없으면 "no zone" 노랑, preset 없으면 "-")
fov 65 (28 mm)  ev +0.33  focus 3.000 m  f/2.80  dof off  roll +0.0  [char hidden]   (시안)
P exit  Space shoot  R reset  F dof  H char  O overlay                 (회색; hints.keyboard 줄들, 패키지에서도 JSON 값)
WASD/EQ move  Shift fast  mouse look  Z/C roll  wheel fov
[ ] fov   - = ev   , . focus   N M f-stop
saved 20260925_101112.png (2x)                                        (초록, 2.5 s; 그 외에는 줄 없음)
```
힌트는 키보드 줄만 그린다(장치 감지 없음, 최소판); 게임패드 힌트는 JSON에 두고 런북·문서가 참조한다. 값 줄은 `Describe()`와 같은 포매터. 줄은 값이 바뀌거나 0.25 s마다 재생성(거리 표시), 시계는 `FPlatformTime`(월드 시계는 정지).

### 6. 카메라 제약
#### 6-1 구(반경 `MaxDistanceM` 3 m, 앵커 = 캐릭터 캡슐 중심 = `SavedPawn->GetActorLocation()`)
(수정 STATE-1, 2026-09-27) 스프링암 카메라는 캡슐 중심에서 ≈ 328 cm(암 320 + `SocketOffset(0,45,55)`)라 3 m 구 밖에서 시작한다. §4-2 3항 "카메라 자세 그대로 시작"을 지키려고 진입 시 세션 유효 반경 `EffectiveRadiusCm = max(MaxDistanceM·100, Dist(EnterLocation, 앵커) + 1)`을 저장하고, 폰 `MoveConstrained`와 오버레이 거리 분모는 `GetEffectiveRadiusCm()`을 쓴다(첫 이동·R에서 튐 없음).

재구성 품질은 촬영 경로(보행자 시선) 근처에서 가장 좋고 멀어질수록 무너진다. 3 m는 골목 폭 2~4 m에서 벽 앞까지 닿고, 28 mm 환산(65°)에서 전신 인물 + 여유가 나오며, "다른 골목"까지는 못 가는 반경. 하한은 바닥 충돌(15 cm 구)이 정한다(로우 앵글 허용). 높이 상한은 두지 않는다(스펙 밖; ②의 `MaxHeightAboveAnchorM` 제거).
#### 6-2 footprint 다각형
- 대상 = `Zones->FindLoadedZoneAt(앵커 XY)`: 앵커를 **포함**하는 **Loaded** zone 중 `ZoneWins` 첫 번째 → 실내(priority 20) > 실외(10)이므로 방 안에서는 방 footprint(합성 실내 8×6 m)로 클램프되어 카메라가 벽 너머(충돌 메시 없는 뒷면)로 못 나간다. 문턱(둘 다 포함)도 실내 우선.
- `Zone->GetFootprintUE()`(level UE cm, `TArray<FVector2D>` [확인 `GolmokZone.h:165`])를 **진입 시 1회** `FootprintXs/Ys`로 복사(캐릭터가 정지 중 움직이지 않음), `Shoot` 시 재조회해 메타 `zone_id`를 정확히. `N < 3`이면 클램프 없음. Loading/Unloaded zone은 대상이 아니다.
- 알고리즘(`GolmokPhotoMath::Constrain`, 폰 스윕마다 1회): ① `ClampToSphere` ② `ClampToPolygonXY` — **(V-09 후속 2026-09-27, #58)** 원래 규칙("안이면 통과, 밖이면 Q에서 앵커 방향으로 inset")은 경계로 밀 때 0~20 cm 띠 안에서 톱니 왕복했고(안쪽 점이 통과 → 밖으로 나가면 20 cm 뒤로), 앵커가 법선 위에 없으면 튈 때마다 옆으로 끌렸다. 지금은 침식 영역 S = {다각형 안 ∧ 경계 거리 ≥ inset}으로의 투영: S 안이면 그대로(0), 아니면 S의 **정확한 최근접점**: S의 경계는 각 변을 내향 법선(링 부호 면적으로 방향 결정)으로 inset만큼 옮긴 선분과 꼭짓점 둘레 반경 inset의 호로 이루어지므로, 각 조각으로의 투영·조각 쌍의 교점(볼록 모서리 = 두 offset 선 교점, 반사 꼭짓점 = 호)·앵커를 후보로 두고 S 안인 것 중 가장 가까운 것(가장 가까운 경계 변 주변 조각 11개를 쌍 교점까지 먼저 시도해 상한을 좁히고, 나머지 조각은 그 거리 안의 것만 — 200각형에서 틱당 약 0.1 ms(클라우드 g++ -O1 드라이버 walk 실측 ≈0.07 ms, 전 2.6 ms; pytest 상한 2000틱 1.5 s; PC/MSVC 실측은 미확인); 2차 검증에서 전 조각 쌍 방식이 틱당 3 ms였음). 적대 검증에서 처음 구현(교대 투영, 인접 변만 교점)이 짧은 변·중복/공선 꼭짓점 모서리에서 주기 5~8 진동·수렴 실패를 보여 이것으로 바꿨다. 후보가 없으면(퇴화 링) 2(이동 취소). 그래서 밀면 정확히 20 cm 안쪽에서 멈추고 접선 성분은 남아 경계를 따라 미끄러진다. inset = `FootprintMarginM`(0.2 m)을 앵커의 경계 거리로 상한(좁은 다각형에서도 앵커는 S 안), 폰의 **현재 위치**가 이미 띠 안이면(스프링암 시작점) 그 거리로 낮춤(진입 직후 튐 없음, 안쪽으로 가면 20 cm로 복귀; 현재 위치가 밖이면 첫 이동에서 S로 들어감 — 전과 같음). 구·다각형은 최대 16라운드 교대(2차 검증: 4라운드는 구가 반사 꼭짓점 호와 만나는 곳에서 수렴하지 못해 매 틱 −1로 얼었음), 그래도 수렴하지 않으면 현재 위치 → 마지막 점 선분의 가장 먼 유효점(이분 20회; 접합 앞(걷기 1.25~2.5 cm/틱이면 약 0.5~1.5 cm, Shift·낮은 FPS에서는 스텝에 비례해 수 cm~10 cm — PR #29 리뷰 A2)에서 멈출 수 있음) ③ 결과가 구 안이고 다각형 안(또는 N = 0)이면 채택, 아니면 **이동 취소**(직전 위치 유지 — 앵커가 둘 다의 안이고 직전 위치도 둘 다를 만족하므로 항상 안전; 작은 zone에서 구가 footprint 밖으로 삐져나오는 경우 다각형이 이김).
- 앵커가 어느 로드된 zone에도 없으면(zone 사이 도로) 다각형 없음, 구·충돌만; 오버레이 1줄 `no zone`(노랑)으로 "재구성 밖일 수 있음"을 알린다.
#### 6-3 충돌 스윕(15 cm)
`SetActorLocation(P, /*bSweep*/ true, &Hit)` — 루트 `USphereComponent` 반경 `CollisionRadiusCm`, QueryOnly, ObjectType `ECC_WorldDynamic`, WorldStatic·WorldDynamic Block, Pawn·Camera·Visibility Ignore, 오버랩 이벤트 off. zone 충돌 메시·blocker 박스는 BlockAll [확인 `GolmokZone.cpp`], 포털 트리거는 `OverlapOnlyPawn`(Pawn만 Overlap) [확인] → 트리거·캐릭터 캡슐·재생 폰과 상호작용 0. 첫 블로킹 히트에서 정지 — **(V-09 후속, #60)** 대각선으로 밀면 벽에 붙던 것을 고쳐, 막히면 남은 이동 `(Target − Start)·(1 − Hit.Time)`을 `Hit.Normal` 평면에 투영(`FVector::VectorPlaneProject`, `UMovementComponent::SlideAlongSurface`와 같은 식)해 현재 위치에서 다시 `Constrain` → 한 번 더 스윕(최대 2회, 0.01 cm 미만 슬라이드는 버림). 결과는 구·다각형 안. 지름 30 cm 미만의 구멍(메시 이음새)은 통과 불가; 큰 구멍(미촬영 벽)은 충돌이 없으므로 footprint·반경이 막는다. 뒷면 스윕 여부(§10 #16)에 의존하지 않는다: 시작점(스프링암 카메라, `ProbeSize 14` ECC_Camera 검사 통과 [확인 코드])에서 이전 위치→목표 스윕만 하고, `bStartPenetrating`이면 앵커 쪽 10 cm 후퇴, 진입 시 겹침 검사(§4-2 4)로 벽 안 시작을 배제. 이동 스윕 최대 2회(+관통 시 후퇴 스윕 1회)(V-09 후속).
#### 6-4 광학 매핑(`ApplyOptics`; PostProcess 오버라이드는 폰 카메라 컴포넌트에만, `PostProcessBlendWeight = 1`)
- FOV: `Camera->SetFieldOfView(Fov)` [확인 V-03 PathPawn].
- 노출: `bOverride_AutoExposureBias = true; AutoExposureBias = float(Base + Ev)`(Base = `Tod->CaptureState(S)` 성공 시 `S.ExposureBias`, 아니면 `AGolmokTimeOfDay::DefaultAutoExposureBias()`) — 카메라 오버라이드는 볼륨 값을 **대체**하므로 base를 다시 더한다 [2차 §10 #9]. 메타에는 상대 EV만.
- DOF: `bOverride_DepthOfFieldFocalDistance = true; DepthOfFieldFocalDistance = bDof ? FocusM * 100 : 0`(0 = DOF 끔 [2차 §10 #9]); `bOverride_DepthOfFieldFstop = true; DepthOfFieldFstop = Fstop`.
- 모션 블러: `bOverride_MotionBlurAmount = true; MotionBlurAmount = 0`(이동 직후 촬영의 번짐 방지 [2차 §10 #9]).
- 롤: `Camera->SetRelativeRotation(FRotator(0, 0, RollDeg))`, 액터 회전은 pitch/yaw만.
#### 6-5 실내
포털이 `RequestLoad(pin)`한 실내 zone은 `Loaded` → §6-2 규칙(방 footprint). 서브레벨 메시 `SM_room`은 BlockAll → 벽 충돌. 조명 오버레이(`EnterInterior`)는 정지 중 그대로(전환 Tick 정지·`ShiftTransitionStart`). 빙의를 바꾸지 않으므로 `RefreshOverlap` 경로가 발생하지 않는다(WP-05 §13 "빙의 교체 후 실외 판정"의 정반대 위험 제거).
#### 6-6 배율과 VRAM(RTX 5060 8 GB, 1440p 기준 — 전부 [미확인] 추정, 런북 §6 실측)
| 배율 | 해상도 | 픽셀 | 추정 추가 VRAM | 판정 |
|---|---|---|---|---|
| 2 | 5120×2880 | 14.7 MP | +1.2~1.8 GB | **기본** |
| 3 | 7680×4320 | 33.2 MP | +2.7~4 GB | **상한** `MaxMultiplier=3`; 실패·스톨이면 2로 커밋 — V-09 결과로 2(4834941, 3x 촬영마다 3~6 s 정지) |
`SetResolution`은 최대 텍스처 크기만 검사하고 VRAM은 검사하지 않는다(V-03 코드) → 상한은 ini가, 실패는 `TakeHighResScreenShot()` false 반환([확인 문서]) → 1x 재시도·메타 실효값이 담당.

### 7. ini (`Config/DefaultGame.ini` 추가분; 다른 섹션 무변경 — WP-05 `EXPECTED_KEYS`·WP-09 `test_ini_keys_and_values` 그대로)
```ini
[/Script/Golmok.GolmokPhotoModeSubsystem]
; WP-12 photo mode (D-013). Player-facing values / ranges / key hints live in Config/Golmok/photo.json (single source; staged by the ../Config/Golmok UFS line above).
ConfigFile=Golmok/photo.json
; Under <Project>/Saved/: <stamp>.png + <stamp>.json (same tree as golmok.screenshot, no preset subfolder).
PhotoFolder=Screenshots/Golmok/photo
; HighResShot multiplier of a photo and its upper bound (RTX 5060 8 GB: runbook section 6 measures 2 and 3). Independent of GolmokDebugSubsystem.ScreenshotMultiplier.
ScreenshotMultiplier=2
; V-09(4834941): 3x shoots but stalls the game 3-6 s per shot -> 2 (owner decision 2026-09-27, D-013 결정 2)
MaxMultiplier=2
; Free camera stays inside this sphere around the character's capsule center (m).
MaxDistanceM=3.0
; Sweep sphere radius (cm): never closer than this to geometry; holes narrower than 2x are impassable.
CollisionRadiusCm=15
; Clamped this far inside the loaded zone footprint the character stands in (m).
FootprintMarginM=0.2
; Camera move speed (m/s); Shift / L3 triples it.
MoveSpeedMps=1.5
; Frames with overlay / HUD hidden and input frozen before the request, and kept after it at least (the file renders on the next Draw; a png poll / 3 s timeout ends the window).
PreCaptureFrames=2
PostCaptureFrames=2
; GamePause (default) or TimeDilation (PC fallback: input / camera not updating while paused; runbook section 3).
PauseMode=GamePause
```
`test_ini_keys_match_config_uproperties`(기존, `CONVENTION_FOLDERS`에 `Photo` 추가)가 두 줄 선언과 1:1 대조하고 `test_ue_wp12_fixture.py`가 키 집합 11개를 고정한다. `+DirectoriesToAlwaysStageAsUFS=(Path="../Config/Golmok")`가 `photo.json`을 덮는다 [확인 ini] → 스테이징 줄 추가 없음(`test_default_game_ini_packaging_lines` 불변).

### 8. 테스트
#### 8-1 UE 자동화(`Tests/GolmokPhotoTest.cpp`, `#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR`, `EditorContext | ProductFilter`, `-nullrhi` 통과 조건)
공통: `FEditorLoadMap(L_Dev)` → `FStartPIECommand(false)` → 시나리오(`IAutomationLatentCommand`, `GEditor->PlayWorld`) → `FEndPlayMapCommand()`; L_Dev 없으면 `AddError`(WP-05 방식). **대기는 전부 `FPlatformTime::Seconds()`**(월드 시계는 정지할 수 있음). 생성 파일은 소멸자에서도 삭제. 헤드리스에서 단언 못 하는 것(실제 화면 정지·키 입력·렌더 화질)은 런북.

| 이름 | 단계 · 단언 |
|---|---|
| `Golmok.Photo.EnterExit` | ① 폰 대기 0.5 s → `AGolmokCharacter` 빙의 확인, `Debug->SetHudVisible(true)`, `Cam` 위치 기록 ② `Enter` true → `IsActive`·`State == Active`·`IsGamePaused(World) == true`·`PC->GetViewTarget()`이 `AGolmokPhotoCameraPawn`·**`PC->GetPawn()`은 여전히 `AGolmokCharacter`**·폰 위치 == 기록한 카메라 위치(1 cm)·`GetParam(Fov) == 진입 FOV(80)`·`Debug->IsHudVisible() == false`·`PC->IsDebugKeysSuspended()`·`Enter` 재호출 false(`already active`) ③ 실시간 0.5 s 뒤 캐릭터 위치 == ①(정지), `GetPawnTickCount() > 0`(정지 중 틱 증명) ④ `SetCharacterHidden(true)` → 캐릭터 `IsHidden()`; `Debug->StartPlayback(...)` false + 메시지 `photo mode is on` ⑤ **드리프트**: `Tod->TransitionSeconds = 0.5; Tod->ApplyPreset("clear_noon")`(프리셋 파일 없으면 이 블록 skip Info) → 실시간 1.0 s 대기 → `Exit("test")` → `Tod->IsTransitioning() == true && GetTransitionAlpha() < 0.3`(월드 시계 동작과 무관) ⑥ 종료 단언: `!IsGamePaused`·뷰 타깃 == 캐릭터·`GetControlRotation` == 진입 전·캐릭터 visible·HUD true 복원·`!PC->IsDebugKeysSuspended()`·`PC->bShouldPerformFullTickWhenPaused == false`·폰 `IsValid` false·`State == Inactive` ⑦ **사전 정지**: `SetGamePaused(true)` → `Enter` → `Exit` → `IsGamePaused() == true` → `SetGamePaused(false)` ⑧ **거부**: `StartRecording("_automation_photo")` → `Enter` false(`while recording`) → `StopRecording` → 파일 삭제; 2샘플 경로를 `SavePathFile`로 만들고 `StartPlayback` → `Enter` false(`path is playing`) → `StopPlayback` ⑨ 콘솔 왕복 `ProcessUserConsoleInput("golmok.photo 1")`·`("golmok.photo 0")` |
| `Golmok.Photo.Clamp` | (a) 순수(월드 불필요): `ClampToSphere` 안/밖/경계/중심 일치/r = 0; `ClampToPolygonXY` 사각형 밖→안(inset 20 cm)·띠 안 점 → inset 선·볼록 모서리 → inset 꼭짓점·오목 L자 홈 → 변 법선(V-09 후속, 전에는 2)·경계 위 점; `Constrain` 현재 위치가 띠 안이면 바깥 이동 거리 유지·안쪽 이동 통과; `Constrain` 구·다각형 동시 위반 → −1(취소), 다각형 우선 케이스 값; `Quantize` 1/3 EV 18스텝 왕복 == 0.0; `StepGeometric` 0.3→50 왕복 3자리; `StepTable` f/2.8 → 4 → … → 16 상한 불변, 1.4 하한 불변; `WrapDeg180`; `FovToFocalMm(65) ≈ 28.2` (b) PIE: `Enter` → `SetFootprintForTest`(앵커 중심 4×4 m 사각형) → `Pawn->MoveConstrained(Anchor + (1000, 0, 0))` → 거리 ≤ `MaxDistanceM·100 + 1` **그리고** 사각형 안(마진 20 cm 이내) → `MoveConstrained(Anchor + (0, 0, −500))` → 바닥 스윕에 막혀 Z ≥ 바닥 − 반경 − 20 cm(바닥은 캐릭터 발 위치로 추정) (c) 스윕: 앵커 앞 1.0 m에 `UBoxComponent`(BlockAll, 50 cm) Transient 액터 스폰 → `MoveConstrained(앵커 + 전방 2 m)` → 카메라–박스 면 거리 ≥ `CollisionRadiusCm − 1`·박스를 넘지 않음; 박스 파괴 → 같은 이동이 통과 (d) `SetParam(Fov, 200)` → 110, `SetParam(Ev, 0.4)` → 0.3333, `SetParam(Fstop, 3.0)` → 2.8(최근접), `Reset` → default·`GetParam(Fov) == 65` → `Exit` |
| `Golmok.Photo.MetaJson` | (a) 순수: `FormatPhotoMetaJson`이 §2-2 예제와 **바이트 동일** + null 3조합(preset/zone/geo) + 문자열 이스케이프(`"`·`\`·한글 zone_id) → `FJsonSerializer::Deserialize`로 재파싱(`TryGetField`, 5.8 규칙) 값·형 확인; **파서 실패 케이스**(`GolmokPhotoJson::ParseConfigText`): `schema_version 2`, `params.fov` 누락, `default > max`, `step`과 `step_ratio` 동시, `values` 내림차순, 미지 최상위 키, `hints.keyboard` 5줄, 숫자 자리 bool → 각각 false + Error에 위치 이름; 정상 파일(`ResolveConfigPath()`) 성공 + 스펙 범위 상수 5개 (b) PIE: `Enter` → `BuildMeta(2)`: `bHasGeo == Geo->HasOrigin()`(원점 있으면 lat ≈ 37.56·lon ≈ 126.92, 없으면 셋 null — **L_Dev는 GeoOrigin이 없을 수 있음**), zone 없음 → `bHasZone == false`, `bHasPreset == !Tod->CurrentPreset.IsNone()`, `UeLocation` == 폰 위치, `bDofEnabled == false` → `Shoot()` → `State == Shooting` → 실시간 대기(최대 5 s, `OnEndFrame`은 nullrhi에서도 발화 V-03) → `State == Active`(nullrhi: PNG 없음 → 3 s 타임아웃 경로) → `GetLastShotPathNoExt() + ".json"` 존재 → 파싱: 키 15개·순서·`version == 1`·`multiplier == min(ScreenshotMultiplier, MaxMultiplier)`(폴백 경로 요청값)·null 규칙 → 같은 초 두 번째 `Shoot` → `_2` 접미 → 파일 삭제; `Shooting` 중 `Exit` → `bExitPending` → 완료 뒤 `Inactive`; `golmok.photo.set fov 40` → `GetParam(Fov) == 40` |

`test_ue_wp12_fixture.py`가 세 이름 + 가드를 요구한다(WP-05 `AUTOMATION_TESTS`는 불변, 별도 상수).

#### 8-2 `tools/tests/test_ue_photo_math.py` + `fixtures/ue/photomath_driver.cpp`
컴파일: `test_ue_stats_math._compiler()`와 같은 플래그(`-std=c++17 -O1 -Wall -Wextra -Werror -pedantic`) + `-I<Source/Golmok>`(두 순수 헤더 모두 그 아래), 컴파일러 없으면 skip. 드라이버 명령(숫자·문자열 배치는 **stdin**, Windows argv 32 KiB·cp1252 대비; `subprocess.run(..., text=True, encoding="utf-8")`; 출력 `%.17g`; 파싱 실패 `ERROR` exit 3):
| 명령 | stdin | 출력 |
|---|---|---|
| `clamp` | `v lo hi` | 값 |
| `quant` / `steplin` | `v min max step [dir]` | 값 |
| `stepgeo` | `v min max ratio dir` | 값 |
| `table` | `dir v n t1..tn` | 값 인덱스 |
| `wrap` / `fov2mm` | `deg` / `fov [w]` | 값 |
| `sphere` | `cx cy cz r x y z` | `moved x y z` |
| `poly` | `ax ay inset n x1 y1 … xn yn m px py …` | 줄마다 `code x y` |
| `constrain` | `ax ay az r inset n xs ys m px py pz …` | 줄마다 `code x y z` |
| `meta` | `key=value` 줄(`preset=-`, `zone=-`, `geo=-`로 null) | JSON 텍스트 그대로 |

케이스: (a) **순수성**(PhotoMath 전용): `#pragma once`, 따옴표 include == `["Debug/GolmokStatsMath.h", "Geo/GolmokGeoMath.h"]`(정렬 후 비교), 꺾쇠 ⊆ `test_ue_stats_math.ALLOWED_INCLUDES`, 금지어(`CoreMinimal UCLASS UE_LOG std::min std::max printf cstdio TEXT( FVector FString`), `namespace GolmokPhotoMath`; 기존 `assert_pure_header`·`test_pure_geo_math_header_has_no_unreal_includes`는 무변경 (b) `clamp`: 안·양끝·NaN → lo·lo > hi 교환 (c) `quant/steplin`: 1/3 EV 18스텝 왕복 뒤 정확히 0.0(`== 0.0`), 0.1 스텝 30번 누적이 그리드값(`pytest.approx`), 경계 클램프, `dir = 0` (d) `stepgeo`: 0.3→50 m 스텝 수 == `ceil(ln(50/0.3)/ln(1.25))`, 왕복 3자리 (e) `table`: photo.json의 `fstop.values`로 중간값 최근접·양 끝·동률(낮은 인덱스) (f) `wrap`: 180→180, 181→−179, −180→180, 720→0 (g) `fov2mm`: 65° → 28.2(±0.1), 39.6° → 50, 20° → 102.07, 110° → 12.60 (h) `sphere` vs numpy: 안(unchanged, moved 0), 밖(거리 == r, 1e-9), 경계, p == center, r = 0, 난수 200개(seed 고정) (i) `poly` vs **shapely**(`pytest.importorskip("shapely")` — `zone` extra, CI는 `[dev,zone]` 설치) — **V-09 후속 2026-09-27로 교체**: 볼록 사각형·오목 L자·별·fixture footprint·예각 쐐기·inset의 두 배보다 좁은 직사각형, 난수 500점: 침식 영역 S(= 안 ∧ `exterior.distance ≥ eff_inset − 1e-6`, eff_inset = inset을 0.001 cm로 하한·앵커 경계 거리로 상한) 안의 점 → `0`·unchanged; 그 밖 → code 1이면 결과가 S 안이고 S까지 40 cm 이내인 점은 `Polygon.buffer(-eff)`의 최근접점과 거리 0.05 cm 이내(호 다각형화 오차), code 2는 unchanged(퇴화 링에서만 허용); 변 밖·띠 안 → 변 법선으로 inset 선(앵커가 법선 위에 없어도), 볼록 모서리 → inset 꼭짓점, 반사 꼭짓점 → 반경 inset 호, 시계 방향 링 동일, inset ≤ 0·NaN → 0.001 cm; `polyq` 최근접점·동률 가장 낮은 변 인덱스; n < 3 → 0. `walk`(Current = 직전 위치를 되먹이는 틱 루프): 경계로 60틱+ 밀면 단조 수렴·진동 폭 0, 대각선 → 접선 미끄러짐, 띠 안 시작 → 튐 없음(바깥 이동 유지·안쪽 이동 래칫), 경계 위 시작 → 첫 틱에 inset 안, 예각·짧은 변(6.2 cm)·중복/공선 꼭짓점 모서리 → 고정점(적대 검증 회귀), 구와 반사 변의 접합으로 미끄러짐, 구·다각형 동시 (j) `constrain`: 결과가 구 안 AND S 안이거나 `−1`; 코드 비트 1 ⇔ 구 밖 입력; 둘 다 만족하는 입력은 unchanged; 두 번째 라운드가 필요한 입력(L자·NOTCHED) 정확값; 200각형 walk 비용 상한; 오목 홈 쪽이 구 밖이면 `−1`; 라운드가 수렴하지 않는 접합에서는 현재 위치 → 마지막 점 선분 이분 탐색 (k) `meta`: §2-2 예제 **바이트 동일**(`res.stdout.replace("\r\n", "\n")`), null 3조합, 이스케이프(`"`·`\`·한글 → StatsMath `JsonQuote` 규칙, statsmath 드라이버 `pathfmt`와 같은 출력), `json.loads` 왕복 값 1e-6, 키 순서 == 스키마 표(`list(d)`), `-0.00` 없음, `fov`가 `65.0`(1자리)·`fstop` 2자리.

#### 8-3 `tools/tests/test_ue_config_photo.py`(순수, 컴파일러 불필요)
`raw = json.loads(photo.json, encoding utf-8)`: (1) 최상위 키 == `{schema_version, params, toggles, hints}`, `schema_version == 1` (2) `params` 키 순서 == `["fov", "ev", "focus", "fstop", "roll"]`, 각 항목 `label`·`unit`·`default` + 꼴 3종 중 정확히 하나(`{min,max,step}` / `{min,max,step_ratio}` / `{values}`), `min < max`, `min ≤ default ≤ max` 또는 `default ∈ values`, `step > 0`, `step_ratio > 1 and min > 0`, `values` 오름차순·양수·≥ 2, 숫자는 `bool` 아님 (3) **스펙 회귀 상수**: `fov (20, 110)`, `ev (−3, 3)`, `focus (0.3, 50)`, `fstop values[0] == 1.4, values[-1] == 16`, `roll (−15, 15)`, `ev.step ≈ 1/3`, `fov.default == 65`, `fstop.default == 2.8` (4) `toggles` 3키 bool, `dof == False`(기본 off) (5) `hints.keyboard/gamepad` 1~4줄·≤ 72자; 키보드 힌트 토큰 집합에 `P Space R F H O WASD Shift Z/C [ ] - = , . N M` 포함, 게임패드 힌트에 `View A Menu R3 B LS LT/RT RS L3 DPad LB/RB X/Y` 포함(작은 표시명 표를 테스트가 가짐) (6) **힌트 ↔ `EKeys::`**: 힌트 표시명 → `EKeys` 이름 표(`[`→`LeftBracket`, `View`→`Gamepad_Special_Left` …)로 변환한 이름이 `GolmokPhotoModeSubsystem.cpp`(포토 액션) 또는 `GolmokPlayerController.cpp`(토글)에 `EKeys::<Name>`으로 존재; 토글 키는 컨트롤러 파일에만 (7) C++ 대조: `GolmokPhotoModeSubsystem.cpp`에 `TEXT("schema_version") TEXT("params") TEXT("toggles") TEXT("hints") TEXT("keyboard") TEXT("gamepad") TEXT("label") TEXT("unit") TEXT("default") TEXT("min") TEXT("max") TEXT("step") TEXT("step_ratio") TEXT("values") TEXT("dof") TEXT("character_hidden") TEXT("overlay_hidden")` + 파라미터 이름 5개; `FJsonSerializer::Deserialize`·`TryGetField` 존재, `Values.Find(` 부재(5.8) (8) **범위 리터럴 부재**: `Photo/*.cpp`에서 문자열·주석을 벗긴 뒤 숫자 토큰 `110`, `1.4`, `16.0`, `0.3`, `50.0`, `15.0`이 없음(단일 소스; `20`·`3.0`은 흔해 제외) (9) ini: `ConfigFile == Golmok/photo.json`이 이 파일을 가리킴, `1 ≤ ScreenshotMultiplier ≤ MaxMultiplier ≤ 8`, `MaxDistanceM ≥ 0.5`, `PhotoFolder`가 `Screenshots/Golmok/`로 시작, `PauseMode ∈ {GamePause, TimeDilation}`, `PreCaptureFrames ≥ 0`, `PostCaptureFrames ≥ 1` (10) 스테이징: `../Config/Golmok` UFS 줄이 있고 `photo.json`이 그 폴더 안(줄 추가 없음) (11) `docs/research/05-legal-policy.md`에 "사용자 촬영 스크린샷" 항목 7 존재. Windows CI: `pathlib`·`REPO` 기준, `encoding="utf-8"`(ini는 `utf-8-sig`), `sorted(rglob)`, `pytest.approx`, 임시 파일은 `tmp_path`.

#### 8-4 `tools/tests/test_ue_wp12_fixture.py`
(1) `[/Script/Golmok.GolmokPhotoModeSubsystem]` 키 == §7 11개 정확히; 다른 섹션 키 집합은 `test_ue_wp05_fixture.EXPECTED_KEYS`·WP-09 4키와 동일(import해 재단언) (2) `Golmok.Build.cs` 텍스트가 WP-09 fixture의 기준과 동일(모듈 추가 없음, `test_build_cs_and_staging_unchanged` 확장) (3) `Photo/*.h/.cpp`·변경된 Debug/Player/Zones/Lighting 파일에 `UE_LOG(LogTemp` 없음, `LogGolmok`만 (4) `Tests/GolmokPhotoTest.cpp`에 3개 이름 + `#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR`, `IMPLEMENT_SIMPLE_AUTOMATION_TEST(` 3회 (5) 플러그인 문자열(`Cesium`, `XGRIDS`) 없음; 위젯 금지(D-003): `UUserWidget`·`CreateWidget`·`WBP_`·`.uasset` 문자열 없음; `Blueprintable` 없음(폰·서브시스템 `NotBlueprintable`) (6) 콘솔 이름 `golmok.photo`, `golmok.photo.shoot`, `golmok.photo.reset`, `golmok.photo.set`이 `FAutoConsoleCommandWithWorldAndArgs`로 등록, 기존 명령 이름 전부 그대로(WP-09 fixture 목록) (7) 익명 namespace 정의 이름 유일(`test_lighting_presets._unity_scope_definitions` 재사용, `Photo` 폴더 포함) + `Photo*` 접두 (8) C4458: WP-09 `_shadow_clashes` 재사용 — `Photo/*.h` 멤버 vs 함수 인자(`In*`/`Out*`), 추가로 `.cpp` 본문의 로컬 선언 `\b(Fov|Ev|Focus|Fstop|Roll|Look|State|Config)\s*=`가 멤버 이름과 같지 않음(느슨한 정규식) (9) 입력 이름: `IA_GolmokPhoto*`·`IMC_GolmokPhoto`·`IMC_GolmokPhotoToggle` 존재, 기존 `IA_Golmok*`/`IMC_GolmokDebug`/`IMC_Default`·`IA_Move/IA_Look/IA_Jump/IA_Run` 그대로, 기존 `MapKey(` 줄 9개 불변 (10) `bTriggerWhenPaused = true`·`bConsumeInput = true`가 서브시스템·컨트롤러 파일에 있음 (11) **빙의 금지**: `Photo/`에 `->Possess(`·`RestartPlayer(` 없음; `SetViewTargetWithBlend(` 있음 (12) `RegisterZone(`/`RequestLoad(`/`RequestUnload(`가 `Photo/`에 없음; `GolmokZoneSubsystem.cpp` 변경이 `FindLoadedZoneAt` 정의 추가뿐(함수 본문에 `RegisterZone`·`RequestLoad`·`SpawnDiscoveredZone` 없음, `_function_body` 재사용) (13) `DefaultInput.ini`의 `!DebugExecBindings=ClearArray` 유지 (14) `GolmokDebugSubsystem.h`에 `RequestHighResScreenshot` 선언, `TakeScreenshot` 메시지 3종 문자열 유지, `.cpp`에 `TakeHighResScreenShot()` 반환값 검사(`if (!View->TakeHighResScreenShot())` 패턴) (15) `GolmokHUD.h` 주석에 "never include it" 없음 (16) `GolmokTimeOfDay.h`에 `ShiftTransitionStart` 선언 (17) 런북 `pc-verify-wp12.md`가 4개 콘솔 명령·`photo.json`·`Screenshots/Golmok/photo`·3개 테스트 이름·`test.ps1 -Filter Golmok.Photo`·ini 11키·"에디터 창을 전면"·§11 표 헤더 문자열을 전부 언급 (18) `test_ue_zone_fixture.CONVENTION_FOLDERS`에 `Photo` 포함(헤더 규약·own-header-first·`.generated.h` 마지막 검사가 자동 적용).

기존 WP-04/05/09/11 테스트 전부 통과가 조건(변경은 `CONVENTION_FOLDERS`·`RUNBOOKS` 1줄씩).

### 9. 런북 `docs/runbooks/pc-verify-wp12.md` 골자 (V-09)
0. 대상 파일 표(§1) · 전제: V-03·V-07 통과, `L_Dev`·`L_ZoneTest`(z_synthetic_001 + 합성 실내) 존재, `cd tools && python -m pytest -q` 초록. 검증 방식은 V-03과 같은 에디터 Python PIE 드라이버 + `unreal.SystemLibrary.quit_editor()`(헤드리스 `UnrealEditor-Cmd -unattended -nullrhi`); 키 입력은 사람이(정지 중 Enhanced Input은 드라이버가 흉내 못 냄 — `golmok.photo.*` 콘솔이 대체). **에디터 창을 전면에**(뒤에 있으면 뷰포트를 그리지 않아 사진이 안 생김 — V-03). 촬영 중 `stat` 명령 끄기.
1. **빌드** `.\tools\ue\build.ps1` → 컴파일 오류는 §11 표 번호로 고치고 `WP-12: PC fix` 커밋. 헤드리스 `test.ps1 -Filter Golmok.Photo`(3) → `-Filter Golmok.`(전체, 기존 + 3) 전부 `Success`.
2. **진입/복원(L_ZoneTest, zone 안)**: F1 HUD 켠 채 P → 로그 `photo mode on (fov 80.0, zone z_synthetic_001 v1, paused)`, 화면 정지(캐릭터 애니 멈춤), HUD 사라짐, 왼쪽 아래 오버레이(값 줄 + 힌트 3줄), **정지 화면에 "PAUSED" 글자 없음**(§11 #12); P → 원래 3인칭 시점·컨트롤 회전·HUD 복귀·캐릭터 즉시 이동 가능; `golmok.photo 1/0`·인자 없는 토글 동일; **사전 정지**: `pause` 콘솔 → **P 키** → 이동 → P → 여전히 정지 → `pause`(§11 #4); `1` 키 직후 P(전환 중 진입) → 10 s → P → 전환이 이어서 끝남(HUD `tod:` 진행률이 진입 전 값에서 계속, 로그 `tod shift`).
3. **정지 중 입력·틱·카메라**(§11 #2·#3·#4·#7): WASD/QE/마우스로 카메라가 **부드럽게** 움직이고 화면이 따라옴(안 움직이면 #3 대안, 최후 ini `PauseMode=TimeDilation` 후 재실행); 포토 중 WASD·마우스·Space → 나간 뒤 캐릭터 위치·회전 불변(#5); 1~4·F5·F9·F10이 포토 안에서 **안 먹음**(디버그 컨텍스트 제거), F1도 안 먹음(의도), `golmok.hud 1`은 먹음; 엔진 DebugExecBindings 충돌 없음; 게임패드 있으면 §5-1 전 항목 체크(없으면 "미실행").
4. **조절·화질**: `[`/`]`·휠 FOV 20↔110(오버레이 값·화면), `-`/`=` EV(±3에서 멈춤; **정지 중 즉시 밝기 변화 — 안 변하면 #10**, EV 0 밝기 == 진입 전 #9), F DOF on → `,`/`.` 초점 0.3↔50 m, N/M f/1.4↔f/16(가까운 물체 초점 시 배경 흐림; off에서 전체 선명), Z/C 롤 ±15, H 캐릭터·그림자 사라짐(#21), O 오버레이, R 리셋(값·구도·FOV 65), `golmok.photo.set fov 35` 콘솔 경로; 정지 상태에서 카메라 이동 중·정지 후 TSR 고스팅·Lumen 노이즈 관찰(#8).
5. **촬영**: Space → 로그 `shooting -> …png (2x, meta …json)` → `capture window closed (… present after x.xx s)`; `Saved/Screenshots/Golmok/photo/<stamp>.png` + `.json`; PNG에 **HUD·오버레이·"PAUSED"·(H 켰으면) 캐릭터 없음**, 이동 직후 촬영에 번짐 없음(#9 모션 블러); 촬영 뒤 오버레이·"saved" 줄 복귀; JSON 필드 15개 §2-2 표 대조(`preset`, `zone_id`, lon/lat ≈ HUD `pos`, `multiplier`, `dof.enabled`); 같은 초 두 번 → `_2`; `PreCaptureFrames=0`으로도 PNG에 HUD 없음(#13, 아니면 기본 2 유지 기록).
6. **배율 VRAM 표**: `golmok.photo.set mult 2` / `3`으로 각 3장, `stat RHI`(render target memory)·작업 관리자 전용 GPU 메모리 피크·촬영 소요(입력→파일)·PNG 크기: `배율 | 해상도 | VRAM 피크 GB | 소요 s | PNG MB | 결과`; 3에서 스톨/실패(`TakeHighResScreenShot` false → 로그 `[multiplier reduced …]`·메타 1)면 `MaxMultiplier=2` 커밋(#14). 1x·2x 크롭(같은 간판) 비교 → 계단·노이즈면 `PreCaptureFrames`↑ 기록(#8).
7. **제약(L_ZoneTest)**: 벽으로 밀기(파사드·blocker 앞) → 15 cm 앞 정지, 관통 0(#16); 캐릭터에서 3 m 밖 → 구 표면 정지(오버레이 거리 `3.0 / 3.0 m`); footprint 경계 밖(캐릭터를 경계 1 m 안에 세우고 카메라를 바깥으로) → 경계 0.2 m 안쪽 정지(`golmok.collision 1`로 경계 확인); zone 밖 도로에서 진입 → `no zone` 노랑·구만; **포털 타이머 관찰**: 문 트리거 안에서 P → 30 s → P → `golmok.portal list` 상태 불변·언로드 로그 없음; 트리거에서 나와 1 s 안에 P → 10 s → P → 언로드가 즉시(타이머 안 멈춤) 또는 2 s 뒤(멈춤)인지 기록(둘 다 허용, #11).
8. **실내**: 문으로 들어가 방 안에서 P → 오버레이 `z_synthetic_001_interior v1`, 실내 조명 오버레이 유지, 촬영 → 메타 `zone_id` 실내·`preset` base 이름, 벽·천장 밖으로 못 나감, 나간 뒤 `golmok.portal list` 불변·실내 로드 유지.
9. **경로 재생 배제**: `golmok.path play quick` 중 P → 거부 로그; 포토 중 `golmok.path play quick` / F9 → `photo mode is on`.
10. (선택) **패키징**: `package.ps1` → `-game`에서 `golmok.photo 1` → 오버레이 힌트가 JSON 값(UFS 스테이징), 로그 `photo: config loaded (5 params) from …`.
11. **PIE 종료**: 포토 모드 켠 채(그리고 Shooting 중) Stop → Error/ensure 0, 로그 `photo: teardown (world ending)`, 에디터 잔류 액터·dirty 없음, 다음 PIE 정상.
12. **불확실 API 표**(§10 그대로, 번호 유지, `PC 결과` 열 ✅/수정/미확인 + 35번 이후 PC 추가 행).
13. **결과 기록** 표(빌드·자동화·§2~§11 각 행·고친 API 번호·커밋) + 스크린샷 4장(JPG 축소, `docs/runbooks/pc-verify-wp12-*.jpg`: ① 포토 모드 화면(오버레이) ② 찍힌 PNG 축소본(오버레이 없음) ③ 벽/구 경계에서 멈춘 장면 ④ 실내 촬영; PNG 원본·JSON은 커밋하지 않음) → STATUS `🟡→🟢`.

### 10. 불확실한 UE 5.8 API와 대안 (런북 §11 표 그대로; 세 안 + 심판 추가 행을 합쳐 중복 제거)
| 번호 | 호출/가정 | 불확실한 점 | 대안 | PC 검증 |
|---|---|---|---|---|
| 1 | `UGameplayStatics::SetGamePaused(const UObject*, bool)` → bool / `IsGamePaused` (`Kismet/GameplayStatics.h`) — BP 문서로 존재·bool 반환 [확인] | C++ 시그니처 [2차]; 내부 `APlayerController::SetPause` → `AGameModeBase::SetPause`(`AllowPausing` 기본 true [2차]) | `PC->SetPause(true)` / `World->IsPaused()`; 게임모드가 거부하면 `AGolmokGameMode::AllowPausing` override true | §2 캐릭터 애니 정지·로그 `paused` |
| 2 | 폰 생성자 `PrimaryActorTick.bTickEvenWhenPaused = true` → 정지 중 `Tick` 호출 [확인 가이드 예시]; `DeltaSeconds` 값(0인지 실시간인지) [미확인] | 정지 틱의 dt 의미. 설계는 `FApp::GetDeltaTime()`(0.1 s 상한)을 쓰므로 무의존. `AActor::SetTickableWhenPaused`는 쓰지 않음(페이지 본문 없음) | 틱이 안 오면 ini `PauseMode=TimeDilation` | 자동화 EnterExit 틱 카운터 > 0 + §3 이동 부드러움 |
| 3 | `APlayerController::bShouldPerformFullTickWhenPaused`(public? 비트필드?) = true로 정지 중 `UpdateCameraManager`(뷰 타깃 폰의 카메라 반영) [2차 M1] — 페이지 본문 없음 [미확인] | 접근성·동작. 값은 `const bool bSaved = PC->…`로 복사(참조·포인터 금지) | 멤버가 private면 `AGolmokPlayerController::ShouldPerformFullTickWhenPaused() const` virtual override(`bPhotoFullTick` 플래그 반환) [2차]; 그래도 얼면 폰 Tick 끝에 `PC->PlayerCameraManager->UpdateCamera(dt)` [미확인]; 최후 `PauseMode=TimeDilation` | §3 이동 시 화면이 따라옴 |
| 4 | 정지 중 Enhanced Input: `UInputAction::bTriggerWhenPaused = true` [확인 필드] + PC 틱(풀틱 또는 약식)이 `TickPlayerInput(…, bGamePaused = true)` 수행 [2차 M2] | 발화 여부; 사전 정지(풀틱 아직 꺼진 상태)에서 P가 먹는지 | `PauseMode=TimeDilation` | §2 사전 정지 + P; §3 정지 중 WASD |
| 5 | 풀틱 정지에서 캐릭터 `IMC_Default` 액션(`bTriggerWhenPaused = false`)이 발화하지 않음 + 포토 IMC(우선순위 3)의 `bConsumeInput` [확인 필드]이 같은 키를 하위로 넘기지 않음 [2차] | 소비·정지 게이트 규칙 | 캐릭터가 튀면 `AGolmokCharacter`에 `RemoveMappingContextForPhoto()` public 추가(PC fix 허용 범위) | §3 포토 중 WASD·마우스·Space → 나간 뒤 캐릭터 위치·회전 불변 |
| 6 | `UEnhancedInputLocalPlayerSubsystem::RemoveMappingContext(const UInputMappingContext*)`(디버그 컨텍스트 제거·포토 컨텍스트 제거; `AddMappingContext`는 V-03 확인) | 오버로드(`FModifyContextOptions` 기본 인자) [2차] | `RemoveMappingContext(Ctx, FModifyContextOptions())`; 없으면 `ClearAllMappings()` 뒤 필요한 것 재추가(캐릭터 IMC 포함) | §3 F키 무반응, 이탈 후 복귀 |
| 7 | `UEnhancedInputComponent::BindAction(Action, ETriggerEvent, UObject*, MemberFn)`에 `UWorldSubsystem` 메서드 바인딩(UFUNCTION 불필요) — WP-05가 PC 메서드로 확인 [확인]; 서브시스템도 `UObject` [2차] | 템플릿 제약 | 핸들러 21개를 `AGolmokPlayerController`에 두고 서브시스템으로 위임(①안) | 빌드 |
| 8 | 정지 중 뷰 이력 읽기 전용(`bWorldIsPaused` → `bStatePrevViewInfoIsReadOnly`) [2차 M4] → 이동 중 TSR 고스팅·Lumen 노이즈 고정·눈 적응 정지; 고해상도 프레임은 히스토리 없이 그려짐; `r.HighResScreenshotDelay` cvar 존재 [미확인] | 화질 | `PauseMode=TimeDilation`; `PreCaptureFrames`↑; cvar 있으면 값 ↑ 실험 | §4 이동 중·정지 후 화면, §6 1x/2x 크롭 비교 |
| 9 | 카메라 컴포넌트 `PostProcessSettings` 오버라이드: `bOverride_AutoExposureBias/AutoExposureBias` [확인 V-03 볼륨 동일 필드], `bOverride_DepthOfFieldFocalDistance/DepthOfFieldFocalDistance(cm)`, `bOverride_DepthOfFieldFstop/DepthOfFieldFstop`, `bOverride_MotionBlurAmount/MotionBlurAmount` [2차 이름], `PostProcessBlendWeight`; `FocalDistance = 0` = DOF 끔 [2차]; 카메라 오버라이드가 PPV 값을 **대체**(가산 아님) [2차]; 정지 중 뷰에 적용 [2차] | 필드명·off 규약·대체 규칙 | 이름은 오류 메시지대로(`Scene.h` grep); DOF off가 안 되면 `Fstop = 16`·`FocalDistance = 5000 cm`로 근사; EV 0 밝기가 다르면 base 재가산 제거 | §4 DOF on/off·EV ±3·EV 0 밝기 동일, §5 번짐 없음 |
| 10 | 정지 중 노출 바이어스 변경이 **즉시** 화면에 반영(눈 적응 히스토리가 멈춰도 bias는 곱셈) [2차] | 눈 적응 정지로 EV 변화가 안 보일 가능성 | `bOverride_AutoExposureSpeedUp/Down = true, 값 20`(포토 동안만) → 그래도면 `bOverride_AutoExposureMethod = true, AEM_Manual`(런북에 화면 차이 기록) | §4 EV |
| 11 | 월드 `FTimerManager`(포털 Debounce/Unload/Preload, zone Evaluate)가 게임 정지에 멈추는지 — 문서 언급 없음 [확인: 없음] → [미확인] | 엔진 동작 | 설계 무의존(빙의 안 함 + 캐릭터 정지 → 오버랩 변화 없음); 관찰만 | §7 30 s 대기·10 s 대기 |
| 12 | `UGameViewportClient::SetSuppressTransitionMessage(bool)` / `bSuppressTransitionMessage` 멤버로 정지 "PAUSED" 전환 메시지 억제(`DrawTransition`) [2차 M5] — 페이지 본문 없음 [미확인]; 고해상도 재렌더에 그 메시지·`stat`·온스크린 메시지가 포함되는지 [미확인] | 존재·시그니처·포함 여부 | 줄 삭제 후 관찰; 메시지가 사진에 남으면 `PauseMode=TimeDilation` | §2 정지 화면, §5 PNG 중앙 |
| 13 | `FViewport::TakeHighResScreenShot()`(`bool` [확인 문서])이 정지 중에도 다음 `Draw`에서 처리·파일 기록 [2차; V-03은 비정지]; 3x에서 false 반환 가능("too big for the GPU") [확인 문구]; `AGolmokHUD::DrawHUD`가 재렌더 프레임에도 호출됨 [확인 V-03 HUD 포함]; `Shoot()`의 상태 변경이 같은 프레임 `Draw` 전 [2차] | 정지 중 동작·순서 | 안 찍히면 요청 틱만 1프레임 언포즈(`SetGamePaused(false)` → 요청 → 다음 틱 `true`); false면 1x 재시도·메타 실효값(설계); 순서가 틀리면 `PreCaptureFrames ≥ 1`이 흡수 | §5 파일 생성·HUD 없음, §6 3x |
| 14 | 고해상도 PNG 쓰기가 비동기(`FImageWriteQueue`) → 수백 ms 뒤 등장 [2차]; PNG 존재 폴링(`IFileManager::FileExists`)으로 숨김 해제 | 시점 | 실시간 3 s 타임아웃이 최종 방어(설계); `-nullrhi`는 타임아웃 경로 | 자동화 MetaJson·§5 로그 대기 시간 |
| 15 | `FCoreDelegates::OnEndFrame`가 정지 중에도 발화 [2차; `-nullrhi` 발화는 V-03 확인] | — | 실시간 타임아웃 + 폰 틱 카운터(정지 틱)로 이중화 | 자동화 MetaJson |
| 16 | `AActor::SetActorLocation(P, /*bSweep*/ true, &Hit)`가 `USphereComponent` 루트(QueryOnly, WorldDynamic)로 벽에서 멈춤; `FHitResult::bStartPenetrating`; `UWorld::OverlapBlockingTestByChannel(Pos, Quat, ECC_WorldDynamic, FCollisionShape::MakeSphere(r), Params)`; Chaos 삼각형 메시 뒷면 스윕 [미확인] | 스윕 적용·뒷면 | `World->SweepSingleByChannel(Hit, From, To, FQuat::Identity, ECC_WorldDynamic, MakeSphere(r), Params)` 후 `SetActorLocation(Hit.Location, false)`; 뒷면은 설계 무의존 | 자동화 Clamp (c) + §7 벽 |
| 17 | 빙의 안 한 `APawn`을 `SetViewTargetWithBlend(Pawn, 0)` → `APawn::CalcCamera`가 카메라 컴포넌트 사용(`bFindCameraComponentWhenViewTarget` 기본 true) [2차]; `GetViewTarget/SetControlRotation/GetControlRotation` [확인 V-03] | 비빙의 뷰 타깃의 카메라 컴포넌트 사용 | `AActor::CalcCamera` override로 카메라 컴포넌트 값 직접 반환 | EnterExit `GetViewTarget()` + §2 화면 |
| 18 | `APlayerCameraManager::GetCameraLocation/GetCameraRotation` [확인 코드 사용 중] · `GetFOVAngle()` [2차] | FOV getter 이름 | `PC->GetPlayerViewPoint(Loc, Rot)` + `Cam->GetCameraCacheView().FOV`; 실패 시 80 | EnterExit FOV 단언 |
| 19 | `EKeys::` 이름: `P H O R Z C N M E Q Enter LeftBracket RightBracket Hyphen Equals Comma Period MouseWheelAxis Gamepad_Special_Left/Right Gamepad_DPad_* Gamepad_LeftShoulder/RightShoulder Gamepad_FaceButton_* Gamepad_RightThumbstick` [확인 EKeys 페이지]; `Gamepad_LeftTriggerAxis` [확인 J-product F7]·`Gamepad_RightTriggerAxis` [2차]; 휠 Axis1D 값이 노치당 ±1·`Triggered` 1프레임 [2차]; 트리거 축 0..1 + `UInputModifierNegate` [2차] | 축 이름·값 의미 | 오류난 이름만 `InputCoreTypes.h` grep; 휠은 부호만 사용(설계); 트리거는 `Gamepad_LeftTrigger/RightTrigger`(버튼) Bool 두 액션으로 | 빌드 + §3 휠 1노치 = 5°·LT/RT |
| 20 | `Gamepad_Special_Left`·P가 PIE에서 에디터에 가로채이지 않음; Esc = PIE 종료 | [2차] | 게임패드 토글을 `Gamepad_Special_Right`로 교체(코드 상수) | §2 |
| 21 | 캐릭터 `SetActorHiddenInGame(true)`가 그림자까지 제거 | [2차] | 메시 `SetCastShadow(false)` 병행·복원 | §4 H 후 그림자 |
| 22 | `UPROPERTY(Transient) TArray<TObjectPtr<UInputAction>>`(GC 보관) | 리플렉션 가능 [2차] | 액션별 멤버 21개(한 줄에 하나 — UHT는 콤마 다중 선언 거부) | UHT/빌드 |
| 23 | `UGameplayStatics::SetGlobalTimeDilation/GetGlobalTimeDilation`, `AWorldSettings::MinGlobalTimeDilation`(0.0001), `AActor::CustomTimeDilation`(폴백 경로만) | [2차] | `World->GetWorldSettings()->SetTimeDilation`; 하한 위반이면 `MinGlobalTimeDilation` 값으로 | `PauseMode=TimeDilation`일 때만 |
| 24 | `FDateTime::UtcNow().ToString(TEXT("%Y-%m-%dT%H:%M:%SZ"))`·`Now().ToString(TEXT("%Y%m%d_%H%M%S"))` [확인 V-03 경로 JSON·스크린샷] | — | — | 메타 `time_utc` |
| 25 | `UWorld::bIsTearingDown`·`DoesSupportWorldType` [확인 V-03]; `EEndPlayReason::Destroyed/EndPlayInEditor/Quit/LevelTransition/RemovedFromWorld` [2차 이름] | enum 값 이름 | 오류 메시지대로 | 빌드 + §11 PIE 종료 |
| 26 | 자동화 latent 명령이 PIE 정지 중에도 매 엔진 프레임 `Update()` | [2차] | 테스트 타이밍 전부 `FPlatformTime`(설계) | 자동화 EnterExit |
| 27 | `TActorIterator`는 쓰지 않음; `UGolmokZoneSubsystem::FindLoadedZoneAt` 안에서 `TWeakObjectPtr<AGolmokZone>::Get()`(non-const)로 `FootprintContains`(non-const) 호출 [확인 자체 코드] | const 메서드 안 호출 규칙 | 레코드 순회를 non-const 헬퍼로 | 빌드 |
| 28 | `UGolmokGeoSubsystem::LevelUEToLonLat(const FVector&, double& Lat, double& Lon, double& H)`·`HasOrigin()` [확인 자체 코드, 인자 순서 Lat·Lon] | — | — | 메타 lon/lat 대조 |
| 29 | `AGolmokTimeOfDay::CaptureState(FGolmokLightingState&)`·`DefaultAutoExposureBias()`·`IsTransitioning()`·`GetTransitionAlpha()` [확인 자체 코드]; 새 `ShiftTransitionStart`는 `TransitionStart`(private double)만 옮김 | — | — | EnterExit 드리프트 단언 |
| 30 | MSVC C4458: 서브시스템 멤버 `Values/Config/State`·폰 `Look/RollDeg` vs 인자·**로컬 변수**; 멤버 함수 `StepParam`과 `GolmokPhotoMath::` 자유 함수 이름 충돌 | pytest 정적 검사(인자 `In*`/`Out*`, 로컬 `New*`/`Local*`, 한정 호출) | 이름 변경 | 빌드 |
| 31 | `UCanvas::SizeX/SizeY`로 왼쪽 아래 배치(`DrawHUD`에서 `Canvas` 유효 [확인 V-03]) | [2차] | `Canvas->ClipX/ClipY` | §2 오버레이 위치 |
| 32 | 유니티 빌드: `Photo/*.cpp` 익명 namespace(`PhotoSubsystemFor`, `PhotoParseToggle`, `CmdPhoto*`)·명명 `GolmokPhotoJson` | Debug의 `ParseToggle`·`DebugSubsystemFor`, Lighting의 `GolmokLightingJson`과 충돌 금지 | 접두 유지(pytest) | 빌드 |
| 33 | photo.json 파싱 `TryGetField(FStringView)`·`AsNumber/AsString/AsArray/AsObject/AsBool`, 키 열거 `FString(*Pair.Key)` [확인 V-03] | — | — | MetaJson 파서 케이스 |
| 34 | `FActorSpawnParameters{ObjectFlags \| RF_Transient, SpawnCollisionHandlingOverride = AlwaysSpawn}` [확인 V-03 포털·재생 폰] | — | — | — |
| 35+ | (PC 세션 추가) | | | |

메모(PR #27 리뷰 A7, 2026-09-27): 지금은 동적 해상도를 쓰지 않는다. 켤 때는 포토 모드 진입·종료를 `GEngine->PauseDynamicResolution()` / `ResumeDynamicResolution()`으로 감싼다(정지 중 해상도 배율이 흔들리면 사진·HighResShot 품질이 틱마다 달라짐).

### 11. 위험·트레이드오프
1. **정지 스택이 [미확인]**(#2·#3·#4·#13): 가장 가능성 큰 PC 수정. 설계는 ini `PauseMode=TimeDilation` 한 스위치로 코드 손질 없이 우회한다(0.0001배속: 캐릭터가 1프레임당 0.0001 s만 움직여 실질 정지, 시간대 드리프트는 `ShiftTransitionStart`가 상쇄, 포털은 빙의 없음이 보호). 자동화는 `IsGamePaused`·뷰 타깃·틱 카운터만 단언하므로 렌더 동작은 런북 §3~§6만이 증거.
2. **정지 중 화질**(#8·#10): TSR·Lumen·눈 적응이 멈추면 이동 중 고스팅·EV 미반영. 품질 우선 원칙상 런북 필수 판정 항목; 폴백 순서(적응 속도↑ → Manual → TimeDilation)를 런북이 결정하고 화면을 첨부.
3. **빙의 안 함의 부작용**: 캐릭터 `IMC_Default`가 살아 있어 `TimeDilation` 폴백에서는 `bConsumeInput`만이 방어(#5). 정지 모드에서는 `bTriggerWhenPaused = false`가 1차 방어.
4. **HUD 포함 사진의 잔여 위험**(#13): `Shoot()` 플래그가 같은 프레임 `Draw` 전에 서는 것에 의존하지 않도록 `PreCaptureFrames` 기본 2. 자동화(nullrhi)로는 못 잡고 런북 §5만이 확인.
5. **배율 3 VRAM**: 추정치. OOM이면 엔진이 크래시할 수도 있다(런북 경고 후 실행). 기본 2는 여유가 크다. `TakeHighResScreenShot` false는 1x로 떨어져 메타가 실제값을 갖는다.
6. **뒷면·구멍**: 충돌 메시가 없는 큰 구멍은 footprint·반경만 막고, zone 밖 도로에서는 아무것도 막지 않는다 → 오버레이 `no zone`으로 정직하게 알린다(클램프 규칙 추가보다 "재구성 안에서 찍게 유도"가 우선).
7. **오목 footprint**: ~~inset 점이 밖이면 이동 취소(2)라 오목 코너 근처에서 카메라가 "걸리는" 느낌 가능. 다각형 오프셋(침식)은 Phase 2.~~ V-09 후속(2026-09-27)에서 침식 영역 투영으로 바꿔 오목 코너는 반경 inset의 호를 따라 미끄러진다. 남은 한계: 구–다각형 접합에서는 정확한 교점보다 걷기 약 0.5~1.5 cm, Shift·저 FPS는 스텝에 비례해 수 cm~10 cm 앞에서 멈출 수 있음(진동 없음); 반사 꼭짓점을 돌아 밀면 최근접점이 호 건너편이라 한 틱 이동이 입력 스텝의 최대 2배(퍼즈 최대 1.7배, 걷기 1.25 cm → 약 2 cm)가 될 수 있음(끝점은 S 안, 이동 경로는 링 안의 여백 띠); 스윕 경로 자체는 다각형을 검사하지 않아 오목 코너를 한 틱(≤ 45 cm)에 가로지를 수 있음(끝점만 S 안).
8. **JSON 실패 = 기능 거부**: 플레이어에게는 "P가 안 눌림"으로 보임 → `golmok.photo` 메시지·Error 1회. 패키징에서 `../Config/Golmok` UFS 스테이징이 빠지면 같은 증상(런북 §10).
9. **메타 먼저, PNG는 다음 프레임**: PNG가 끝내 안 써지면 고아 JSON(nullrhi에서는 의도). 사진첩(D-017)은 PNG 존재로 필터.
10. **세션 값 지속**: "저번에 EV +2로 찍었더니 지금 화면이 밝다" 혼란 → 오버레이 값 줄 상시 표시 + R 리셋. 월드 간 저장은 Phase 2(D-017).
11. **Zones·Lighting 각 1 함수 추가**: 읽기 전용·전환 시작 시프트뿐이지만 WP-05/09 모듈을 건드린다. pytest가 `FindLoadedZoneAt` 본문에 로드·스폰 호출이 없음을 고정.
12. **디버그 키 차단·F1 무반응**은 의도(사진에 HUD 금지); `golmok.hud 1`이 개발용 우회. 포토 중 1~4 프리셋 전환 불가도 의도(전환 Tick 정지) — Phase 2 D-015 슬라이더.
13. **테스트 공백**: 게임패드·마우스 감도·TSR 화질·"PAUSED" 텍스트는 자동화가 못 잡는다 → 런북 체크박스로만.

### 12. 심판 지적 반영표 (defect → 조치)
| # | 심판 | 대상 | 지적 | 최종안 조치 |
|---|---|---|---|---|
| 1 | engine-1·product-1 | api·data | 포토 폰 빙의 → `OnPossessedPawnChanged → RefreshOverlap`이 문 트리거·실내 오버레이를 끝냄(blocking) | §0 #1: 빙의 없음, 뷰 타깃만; pytest `->Possess(` 부재; EnterExit가 `GetPawn()` 불변 단언 |
| 2 | engine-2 | api | 시간대 "즉시 완료"는 스펙 위반·`TargetPreset == None`에서 실패 | §0 #4: `ShiftTransitionStart(Δ)`; EnterExit `alpha < 0.3` 단언 |
| 3 | engine-3·product-2 | api | `bShouldPerformFullTickWhenPaused`를 폴백으로만 | §0 #3: 기본 경로(bool 복사·복원), §10 #3 대안 사슬 |
| 4 | engine-4·product-4 | data·ux | 캡처 창 종료가 폰 틱 의존/고정 프레임/타임아웃 없음 | §0 #13: `OnEndFrame` 카운터 + PNG 존재 폴링 + 실시간 3 s 타임아웃, 최소 `PostCaptureFrames`; `TakeHighResScreenShot` 반환값 검사 |
| 5 | engine-5·product-5 | 전부 | 정지 중 렌더 시간 누적·모션 블러 무대책 | §0 #2 `PauseMode` ini 스위치, §6-4 `MotionBlurAmount = 0`, §10 #8·#9·#10, 런북 §4·§6 필수 판정 |
| 6 | engine-6·product-3 | 전부 | "PAUSED" 전환 메시지·`stat`·온스크린 텍스트 | §0 #21 `SetSuppressTransitionMessage` 저장·복원, §10 #12, 런북 §2·§5 |
| 7 | engine-7 | api·ux | 자동화가 L_Dev GeoOrigin 존재를 단언 | §8-1 MetaJson: `Geo->HasOrigin()` 분기; 고정 좌표는 순수 포매터 바이트 테스트만 |
| 8 | engine-8 | api | footprint zone 선택 규칙이 `ZoneWins`와 다름 | §0 #16 `FindLoadedZoneAt`(ZoneWins) 채택; ③의 실내→priority→id 규칙 기각 |
| 9 | engine-9·product-9/10 | data·api·ux | 순수 헤더 include 규칙 불일치·PointInPolygon/FormatFixed 복제 | §0 #10: GeoMath + StatsMath 둘 다 include(복제 0), PhotoMath 전용 순수성 검사, 공용 검사 불변 |
| 10 | engine-10 | 전부 | 폰 `EndPlay`·월드 해체 중 복원 호출 / ②는 EndPlay 훅 없음 | §0 #20·§4-1: 사유별 `OnPhotoPawnEndPlay`, `TeardownForDeadWorld` |
| 11 | engine-11·product-8 | ux | 최소판 대비 과설계(선택 모델·홀드 반복·스무딩·룩커브·장치 힌트·높이 상한·ini 20키·콘솔 5) | §0 #6·#19: 직접 키·`Started`만, ini 11키, 콘솔 3 + set; 유지한 ②의 것은 빙의 없음·시프트·진입 FOV·DOF off·휠 FOV·pre/post 프레임 |
| 12 | engine-12 | api | 힌트 문자열과 키 표 불일치 | §2-1 힌트는 §5-1 표에서 생성; §8-3 (6) 힌트 토큰 ↔ `EKeys::` 대조 |
| 13 | engine-13 | ux | `UENUM`·`Count` 노출 | §0 #23: `PauseMode`만 UENUM, 나머지 일반 enum |
| 14 | engine-14 | 전부 | C4458 로컬 변수·`StepParam` 이름 충돌·익명 namespace 이름 미정 | §0 #23, §8-4 (7)(8), §10 #30·#32 |
| 15 | engine-15·product-7 | api·ux | photo.json 실패 시 내장 기본값(단일 소스 위반) | §0 #9 진입 거부; §8-3 (8) 범위 리터럴 부재 검사 |
| 16 | engine-16 | 전부 | 사전 정지 상태에서 P 진입 미검증 | 런북 §2 "`pause` → P 키 → 이동 → P → 여전히 정지", §10 #4 |
| 17 | engine-17·product-16/17 | api·data | [확인] 태그 근거(TakeHighResScreenShot 문서 모순·EKeys URL 없음) | 이 세션에서 두 페이지를 직접 열어 [확인]으로 확정(서두에 URL·인용 문구); 목차만 온 페이지는 [미확인] |
| 18 | engine-18·product-11/12/13 | ux·data | 메타 스펙 외 필드(`resolution`·`file`·`+interior`·lon 9자리)·JSON `keys` 거울·별도 Config 클래스·`camera` 블록 | §0 #15·#19: `dof.enabled`만 추가, lon/lat 7자리; JSON은 params·toggles·hints만; 파서는 서브시스템 `.cpp`의 `GolmokPhotoJson` |
| 19 | product-6 | api·data | DOF 항상 켜짐이 기본 | §0 #11 off 기본 + F/R3 토글 |
| 20 | product-14 | api | 진입 시 FOV 점프·매 진입 초기화 | §0 #12 진입 FOV 연속, 세션 값 유지 |
| 21 | product-15 | api | 게임패드 f-stop 없음·롤 한쪽·버튼 충돌 | §5-1: f-stop X/Y, 숨김 B, 리셋 Menu, DOF R3, 오버레이 패드 없음, 패드 롤 없음(힌트 명시) |
| 22 | product-18 | api | 런북에 "에디터 창 전면" 누락 | §9-0 |
| 23 | product-19 | 전부 | Debug 섹션에 같은 이름 `ScreenshotMultiplier`가 이미 있음 | §7 주석 "Independent of GolmokDebugSubsystem.ScreenshotMultiplier"; Debug 섹션 키 집합 불변 |
| 24 | product-20 | 전부 | `GolmokHUD.h` 주석이 V-03과 모순 | §0 #24, §8-4 (15) |
| 25 | product-21 | 전부 | 풀틱 정지에서 캐릭터 액션 발화 가능성 | 포토 IMC가 겹치는 키 전부 매핑 + `bConsumeInput`, `SavedControlRotation` 복원, §10 #5, 런북 §3 |
| 26 | product-22 | data | 4번째 자동화 `ConfigFile` | 파서 실패 케이스를 `MetaJson` 순수 부분에 합쳐 스펙 이름 3개 유지 |
| 27 | product-23 | api | `photo_config.py` 불필요 | 제외(§1) |
| 28 | product-24 | 전부 | 디버그 키 처리 방식 셋 | IMC 제거 + `AddMappingContext()` 가드, 복원은 `bDebugKeysEnabled && bDebugKeysWereActive`일 때만 |
| 29 | product-25 | 전부 | 헤드리스 단언 합본(틱 카운터·드리프트·`GetPawn()` 불변·사전 정지·재생 거부·스윕 박스) | §8-1 전부 채택, 대기는 `FPlatformTime` |
| 30 | product X4/X9/X12/X14/X15/X16 | 교차 | JSON 실패 거부 / 촬영 키 Space+A(LMB 제외) / `preset` null / 둘 다 만족 못 하면 취소 / 콘솔 3 + set·인자 없음 = 토글 / ini 분담 | §0 #9·#7·#15·#17·#18·#19 |
| 31 | engine X12 | 교차 | 폰 dt 의미 | `FApp::GetDeltaTime()` 0.1 s 상한(③) |
| 32 | engine X6 | 교차 | 디버그 HUD 진입 시 숨김 vs 유지 | 진입 시 숨김(스펙 "나가면 HUD 복원"), `golmok.hud 1`로 켤 수 있음 |
| 33 | product X10 | 교차 | PreCaptureFrames 8 vs 0 | 기본 2(요청 전 최소 한 Draw가 숨김 상태; TSR 누적 효과는 [2차]라 런북이 조정) |
| 34 | engine·product 공통 | 교차 | 파서 위치(별도 클래스 vs 서브시스템 .cpp) | 서브시스템 `.cpp`의 명명 namespace `GolmokPhotoJson`(조명 `GolmokLightingJson` 거울) |
| 35 | product-J-product-3 대안 | 교차 | 정지 메시지 억제 실패 시 | `PauseMode=TimeDilation` 경로로 통일(별도 `#define` 없음) |
| 36 | engine E-표 / product A~E | 불확실 표 | 세 안 + 심판 추가 행(A~E, E1~E20) | §10에 34행으로 병합·중복 제거(번호 재부여) |
| 37 | product F11 | 전부 | WP-05 `EXPECTED_KEYS` 불변 | §7·§8-4 (1): 새 섹션은 별도 상수, 기존 섹션 재단언 |
| 38 | engine F13 / product F13 | 문서 | 법 조문 추측 금지 | §2-4: 이미 인용된 조문만, 판단은 D-009 |
| 39 | product X11 `file` 필드 | data | nullrhi 폴백 이름과 어긋남 | 제외 |
| 40 | engine·product "best ideas" | 채택 | `ShiftTransitionStart`·`FindLoadedZoneAt`·진입 FOV·DOF off·pre/post 프레임·PNG 폴링·메타 먼저·Windows CI 함정 목록·거부 경로 테스트·VRAM 표·JPG 4장 | 전부 채택(§0·§8·§9) |

## 결과

### 설계 대비 변경
- **포토 액션 17 → 21개(`IA_GolmokPhotoLookPad` 추가)**: 설계 §5는 시선을 `Look` 한 액션(Axis2D)에 `Mouse2D`와 `Gamepad_Right2D`를 함께 매핑하고 핸들러에서 "마우스면 델타, 패드면 값"으로 나누도록 적었으나, 한 Axis2D 액션의 `FInputActionValue`에는 어느 장치에서 왔는지가 없어 핸들러가 둘을 구분할 수 없다(마우스 델타는 프레임마다 누적, 스틱 값은 유지·Completed에서 0이어야 함). 그래서 `Look`(Mouse2D, Triggered → `AddLookMouse`)과 `LookPad`(Gamepad_Right2D, Triggered/Completed → `SetLookPad`)로 나눴다. §0 #5·§3-2·§5·§10 #7/#22의 개수를 21로 고쳤고, `tools/tests/test_ue_wp12_fixture.py`의 `PHOTO_ACTIONS`(21개)가 코드의 `IA_GolmokPhoto*` 집합과 **같음(==)**을 고정한다(이전 `>=`는 액션 추가를 잡지 못했다).
- **포토 카메라 전방 yaw만(D-013 결정 3 확정판, 2026-09-28, PR #40 리뷰 M1/M2 뒤)**: §3-3 "전방(피치 포함)" → "전방(yaw만)". W/S/A/D는 항상 수평면 이동이고 높이(Z)는 Q/E만 바꾼다(`DECISIONS.md` D-013 결정 3, 근거 5개). §5-2 스텝·속도 표는 그대로.

**병합 전 보완 리뷰(Opus 5.5 읽기 전용, 2026-09-27, 오케스트레이터 반영)** — BLOCKING 0·major 1·minor 3·note 5, 판정 "merge as-is". 병합 커밋 전에 반영한 것: ① 핫스팟 등록 줄을 `[WP-12 hook]` 표식으로 정리(`test_ue_zone_fixture.py` `CONVENTION_FOLDERS`는 원래 한 줄 복원 + `+= ("Photo",)` 훅 줄, `test_ue_wp09_fixture.py` `CONSOLE_COMMANDS` 4줄 표식, `DefaultEngine.ini` `[/Script/Engine.Engine]` 절을 파일 끝으로 이동 — Astra 오디오 레인이 같은 등록부를 늘리므로 충돌 예방); ② `Quantize`가 0 격자점을 `+0.0`으로 스냅(`photo.json` 스텝 `0.3333333333`으로 9번 올리고 9번 내리면 `-3e-10` → 오버레이 `ev -0.00`이던 것; pytest에 정확히 `+0.0` 단언 추가); ③ `PauseMode`를 `Enter()`에서 `ActivePauseMode`로 래치해 `Exit()`가 같은 분기를 복원(활성 중 프로퍼티가 바뀌면 정지 상태·시간 배율이 남던 경로; `FGolmokPhotoRestoreState::PauseMode` 공개); ④ 이 절의 `## 결과` 중복 제목 정리. 남긴 note: 포토 시선이 `bInvertLookY`를 무시(ini 기본 False라 현재 차이 없음), 패드 스틱 데드존 없음(런북 §3에서 스틱 놓고 10 s 드리프트 확인 권장), `PhotoFolder` ini 값 런타임 검증 없음(pytest만), `Player/GolmokGameViewportClient`가 프로젝트 전체 뷰포트 클래스가 됨(향후 플러그인 뷰포트 클래스는 이를 상속). `Player/GolmokPlayerController.cpp` `AddMappingContext()`의 기존 줄 변경(디버그 키 꺼짐 상태에서도 포토 토글 컨텍스트를 넣기 위한 early-out 제거)은 9ec35ee(2026-09-25, §7.6 규칙 이전)이며 사유를 PR #19 본문에 적었다.

### 세션 기록
세션: session_01R7589q1vh4DRPq4NeCsZ4Q (Fable 5.1 ultracode; 심판·회의론자·수정 에이전트는 모델 정책대로 Opus 5.5) · 2026-09-25 → 2026-09-27 · 상태 **🟡 코드 완료·PC 검증 대기** (G2 `runbooks/pc-verify-wp12.md`, V-09). PR #19(draft, 병합은 오케스트레이터).

**진행 방식(ultracode, Workflow 3회, 동시성 2)** — ① 설계 패널: ① UE 5.8 API 현실성 / ② 플레이어 경험·품질 / ③ 데이터·테스트 3안(Fable) → Opus 심판 2명(엔진 사실 27·27·27 / 제품·검증 27·27·29) → 종합 "설계 (확정)" §0~§12(심판 지적 40건 반영, 어느 안도 그대로 채택하지 않음). ② 구현: A(순수 헤더+g++ 교차검증 ∥ 기존 코드 추가분·photo.json·법 문서) → B(서브시스템 ∥ 폰·HUD·컨트롤러) → C(정적 통합 검토·UE 자동화 3개·픽스처 pytest·전체 게이트). ③ 적대적 검증 **1라운드**(상한): 런북 작성 ∥ 리뷰어 4관점(① API·컴파일 3 / ② 리플렉션·Config·빌드 7 / ③ 상태 복원·상호작용 9 / ④ 스펙·테스트·런북 5 = 24건) → Opus 회의론자 4명 재현·반박 → **확정 9**(major 3: 진입 포즈가 3 m 구 밖(스프링암 320 cm+오프셋) / 런북 자동화 개수 / 런북에 C2248 수정분 누락; minor 6: 상수 이중 정의, 액션 수 21 vs 주석 20·픽스처 `>=`, f 접미 리터럴 검사 누락, Reset이 배율 초기화, 해체 시 전환 메시지 억제 잔류, 런북 줄 번호) · **반박 14** · **미검증 1**(정지 중 `TickPlayerInput` 경로 → 런북 #56) → Opus 수정 3그룹(각 결함에 pytest 회귀 검사 먼저 추가) → 게이트. 원시 소견 24 → 확정 9는 전부 반영했다.

**PC 빌드 보고 반영(V-09 선행, 2026-09-27)** — ChatGPT Astra가 소유자 PC에서 이 브랜치(0806da8)를 main과 합쳐 빌드하니 **C2248 7곳**(`Photo/GolmokPhotoModeSubsystem.cpp` 912·920·970·975·1161, `Tests/GolmokPhotoTest.cpp` 276·367): `APlayerController::bShouldPerformFullTickWhenPaused`(`PlayerController.h:1730`)와 `UGameViewportClient::bSuppressTransitionMessage`(`GameViewportClient.h:118`)가 5.8.3에서 **protected**(설계 §10 #3·#12의 [2차] 가정이 틀림). 수정(`f5c8861`·`915692f`): (a) `Player/GolmokPlayerController`에 `[WP-12 hook]` 블록으로 `GetFullTickWhenPausedFlag()/SetFullTickWhenPausedFlag(bool)`(파생 클래스는 protected 접근 가능; 엔진 공개 `ShouldPerformFullTickWhenPaused()`는 XR 조건을 OR해 raw bit 스냅샷이 아님) — 서브시스템·테스트는 이 접근자만 사용, `GetPC()`의 캐스트 실패는 진입 거부. (b) 뷰포트 플래그는 raw getter가 없어 **`Player/GolmokGameViewportClient`(신규, `IsTransitionMessageSuppressed()`)** + `DefaultEngine.ini` `[/Script/Engine.Engine] GameViewportClientClassName=/Script/Golmok.GolmokGameViewportClient`로 정확히 저장·복원한다. **한계**: 그 ini 줄이 없으면(또는 다른 뷰포트 클래스면) 원값을 읽지 못해 종료 시 `false`(엔진 기본)로 복원하고 Warning 1회 — 다른 시스템이 켜 둔 억제 상태를 잃을 수 있다(런북 §12 #12 행에 명시). 오케스트레이터가 핫스팟 ini 변경을 원치 않으면 그 줄만 빼도 코드는 컴파일·동작한다(폴백 경로). (c) `UGolmokPhotoModeSubsystem::GetRestoreState()`(`FGolmokPhotoRestoreState`: 정지·풀틱·HUD·폰 숨김·전환 메시지·디버그 키·시간 배율·뷰 타깃·컨트롤 회전) 공개 조회 계약 — `Exit()`가 복원. (d) `test_ue_wp12_fixture.py`에 두 엔진 protected 멤버 이름을 서브클래스 파일 밖에서 쓰지 않는다는 검사 + ini·계약 검사 3개.

**한 것** (`unreal/Golmok/` 기준; 파일 목록은 설계 §1)
- `Photo/GolmokPhotoMath.h`(순수 헤더: 스텝·양자화·f-stop 표·구/다각형 클램프·`Constrain`·메타 JSON 포매터, include는 `Geo/GolmokGeoMath.h`·`Debug/GolmokStatsMath.h`뿐) · `Photo/GolmokPhotoModeSubsystem`(photo.json 파서 `GolmokPhotoJson`, 상태기계 Inactive→Active→Shooting→Captured, 진입/복원 시퀀스, 빙의 없음·뷰 타깃만, `SetGamePaused`/`TimeDilation` 폴백, 포토 액션 21개·`IMC_GolmokPhoto` 우선순위 3, `OnEndFrame` 캡처 창(메타 먼저·PNG 폴링·3 s 타임아웃), 오버레이 줄, 콘솔 `golmok.photo [0|1]`·`.shoot`·`.reset`·`.set`) · `Photo/GolmokPhotoCameraPawn`(15 cm 구·카메라, 정지 중 Tick, 구→다각형→스윕, `ApplyOptics` PP 오버라이드) · `Debug/GolmokDebugSubsystem::RequestHighResScreenshot` public 분리(`TakeHighResScreenShot()` false면 1x 재시도)·경로 재생/녹화의 포토 거부 · `Debug/GolmokHUD` 캡처 가드 + 왼쪽 아래 오버레이 · `Player/GolmokPlayerController` P/`Gamepad_Special_Left` 토글(`IMC_GolmokPhotoToggle` 2)·`SetDebugKeysSuspended`·풀틱 접근자 · `Player/GolmokGameViewportClient`(신규) · `Zones/GolmokZoneSubsystem::FindLoadedZoneAt` · `Lighting/GolmokTimeOfDay::ShiftTransitionStart` · `Config/Golmok/photo.json`(단일 소스) · `DefaultGame.ini` `[/Script/Golmok.GolmokPhotoModeSubsystem]` 11키 · `DefaultEngine.ini` 뷰포트 클래스 1줄.
- 테스트: UE 자동화 **3개** `Golmok.Photo.EnterExit / Clamp / MetaJson`(`-nullrhi`; 전체 22개) · pytest 포토 3파일 **90개**(`test_ue_photo_math.py` g++ 드라이버 vs numpy·shapely, `test_ue_config_photo.py` 스키마·힌트↔`EKeys` 대조, `test_ue_wp12_fixture.py` ini·Build.cs·로그·콘솔·입력 이름·빙의/RegisterZone 부재·유니티 이름·C4458·protected 멤버·런북 대조) + 기존 파일 추가(`CONVENTION_FOLDERS` Photo, `RUNBOOKS`, `CONSOLE_COMMANDS`). 문서: 런북(419줄, 체크 67, 불확실 API 56행 + PC 행), `research/05` 자문 항목 7, 설계 §6-1 유효 반경 메모.

**테스트 로그(클라우드)**: `ruff check .` All checks passed · `ruff format --check .` 96 files already formatted · `python -m pytest -q` **744 passed, 3 skipped, 208 warnings in 36.62s**(main 병합 뒤; WP-12 이전 기준 626) · `check_repo.py` OK. CI는 PR #19 체크 참조.

**불확실 API**: 런북 §12 표 **56행**(설계 §10 #1~#34 + 구현 #36~#55 + 회의론자 #56; `35+`·`57+`는 PC 추가 행). PC에서 먼저 볼 것: 정지 중 Enhanced Input·카메라 매니저 갱신(#2~#5, 안 되면 ini `PauseMode=TimeDilation`), 정지 중 `TakeHighResScreenShot` 기록(#13·#14), PP 오버라이드 멤버 이름(#9), `GameViewportClientClassName` 적용 여부(#12), 진입 시 `OverlapBlockingTestByChannel`(#16). 공식 문서로 확인된 것: `bTriggerWhenPaused`·`bConsumeInput`·컨텍스트 우선순위·`bTickEvenWhenPaused` 예시·`HighResShot` 문법·Cinematic DOF 단위·`TakeHighResScreenShot` bool 반환.

**판단한 것(설계·스펙과 다른 점, 코드 기준)**
- 진입 카메라가 캐릭터 스프링암(320 cm+오프셋)보다 멀어 3 m 구 밖 → **유효 반경** `GetEffectiveRadiusCm() = max(MaxDistanceM·100, 진입 거리+1)`(오버레이 `3.3 / 3.3 m`). `Reset()`은 세션 배율을 지우지 않음. 포토 액션은 21개(`IA_GolmokPhotoLookPad` 분리: 마우스 델타와 스틱 값은 한 핸들러로 구분 불가). 진입/종료 로그는 `photo: …` + 호출자(`P:`/`golmok.photo:`) 2줄, 종료 호출자 메시지는 `photo mode off`. photo.json 실패 메시지는 `cannot enter: photo.json: <where>: <why>`. 포토 중 F9/F10은 컨텍스트가 제거돼 눌리지 않음(거부 문구는 콘솔 `golmok.path`가 담당). DOF 기본 off(§0 #11), `dof.enabled` 키 추가.

**Astra(WP-18) 통합 요청 사항** — PR #24 `Tests/GolmokCharacterRosterPhotoTest.cpp`(`Golmok.Character.PhotoIntegration`, proxy135/proxy110/Quinn × GamePause/TimeDilation 6조합)가 쓰는 공개 API(`Enter/Exit/PauseMode/GetParam/GetAnchor/GetPhotoPawn/GetPawnTickCount/SetCharacterHidden/IsCharacterHidden/IsActive`)는 이 브랜치에 전부 있고 시그니처가 같다; `GetRestoreState()`는 추가 계약. 6조합 재실행과 캐릭터 교체 뒤 앵커 검증은 **PR #24 쪽**(V-09 §1 뒤 `test.ps1 -Filter Golmok.`). 캐릭터 폰이 교체돼도 포토 앵커는 `SavedPawn`(진입 시 빙의 폰)이라 포토 중 교체는 지원하지 않는다(진입 거부·`Exit` 뒤 교체).

**남은 것**
- PC 검증 V-09(런북 §1~§13). 컴파일 에러는 §12 표로 고치고 `WP-12: PC fix` 커밋; 배율 3의 VRAM 실측으로 `MaxMultiplier` 확정.
- 반복 입력(길게 누름)·장치별 힌트·사진첩·시간대 슬라이더는 Phase 2(D-013 확장).
- 세션 비용: 오케스트레이터 집계 2026-09-27 08:50Z 기준 $124 + 검증·마무리분(STATUS 세션 로그).

**PC 검증 V-09 (2026-09-28, 런북 §13)** — 빌드 무수정, 자동화 26/26(PhotoIntegration 6조합 포함), §2~§6·§8·§9·§11 통과, §10은 L_Dev로 통과, **§7 footprint 실패**. 설계 변경 2건(c026815): ① GamePause에서도 `UWorld::bIsCameraMoveableWhenPaused`를 켜 뷰 이력을 갱신(정지 월드의 TSR/Lumen 이력 고정 → 카메라 이동 뒤 캐릭터 잔상이 화면·PNG에 남던 것 제거, 런북 §12 #57). ② 포토 카메라 눈 적응 속도 20 EV/s(EV가 2~4 s에 걸쳐 수렴하던 것 → 0.3 s, #10). 확정값: `PauseMode=GamePause`, `MaxMultiplier=2`(4834941, 3x는 촬영마다 3~6 s 정지), `PreCaptureFrames=2`(0에서도 HUD 없음). 후속(클라우드): #58 `ClampToPolygonXY`가 경계 20 cm 띠 안의 점을 받아 경계로 밀면 0~20 cm 톱니, #60 벽에 대각선으로 밀면 붙음(면 따라 미끄러짐 없음). 관찰: 촬영 저장이 게임 스레드를 멈춤(2x 1.2 s, #59), 사전 정지 종료 뒤 화면이 정지 해제까지 옛 구도, TimeDilation은 EV 무반응(#61). c026815는 Unreal 코드라 병합 전 Opus 5.5 ultracode 적대 검증 필요(모델 정책 2026-09-27), 결정 항목의 화질 판단은 Fable.

**V-09 후속 수정 (2026-09-27, session_01HUggmuMt3WjKXq8PsHv99j, Opus 5.5 ultracode)** — 상태 🔴 → **🟡 §7 재검증 대기**. 설계 변경이 아니라 §6-2·§6-3이 약속한 동작의 구현이다.
- **#58 footprint 톱니** — 원인: `ClampToPolygonXY`가 다각형 **안**의 점을 그대로 통과시키고 밖으로 나간 점만 경계 + 20 cm로 되돌려, 경계로 밀면 0~20 cm 띠 안을 앞뒤로 오갔다(V-09 남쪽 y 980.0 ↔ 999.8). 되돌리는 방향이 앵커 쪽이라 앵커가 법선 위에 없으면 튈 때마다 옆으로 끌렸다. 수정(a6c48a3 → e03753e → 7f66810): 침식 영역 S = {안 ∧ 경계 거리 ≥ inset}의 **정확한 최근접점**(inset만큼 옮긴 변·꼭짓점 둘레 반경 inset의 호·그 쌍 교점·앵커 후보, 가장 가까운 변 주변 11조각을 먼저 시도). inset은 앵커의 경계 거리로 상한, 폰의 현재 위치가 이미 띠 안이면 그 거리 유지(진입 직후 튐 없음, `Constraint::Current`·`MoveInsetCm`). 구·다각형은 최대 16라운드 교대 + 수렴하지 않으면 현재 위치 → 마지막 점 이분 탐색.
- **#60 벽 밀착** — 원인: `MoveConstrained`가 스윕 1회, 첫 충돌에서 이동 전체(접선 성분 포함)를 버림. 수정(6c36fd3): 막히면 남은 이동 `(Target − Start)·(1 − Hit.Time)`을 `FVector::VectorPlaneProject(…, Hit.Normal)`로 투영, 멈춘 위치에서 다시 `Constrain` 후 두 번째 스윕(최대 2회), `bStartPenetrating` 후퇴 유지.
- **PR #27 병합 전 리뷰(비블로킹) 반영**: A2 `RestoreAll`에서 뷰 타깃 복원 직후 `SetGameCameraCutThisFrame()`(런북 §4 종료 밝기 항목) · A3 §4-2 2·6단계와 §4-3에 `bIsCameraMoveableWhenPaused` 저장·설정·복원, `FGolmokPhotoRestoreState::bCameraMoveableWhenPaused`, fixture 순서 검사 · A1 `bWorldIsPaused`가 엔진 WITH_EDITOR 분기에만 있다는 범위(주석·런북 §12 #57·§10 패키지 잔상 항목) · B1·B2 런북 §6 기대 출력 `1..2`·§0 `MaxMultiplier=2` · B3 헤더 기본값 2·ini 주석 한 줄 · B5 STATUS · A7 §10 동적 해상도 메모 · #61 원인(눈 적응이 팽창된 DeltaWorldTime으로 적분)만 런북에.
- **적대 검증 2라운드**(Workflow 2회: 1차 관점 3 → 반박 13, 2차 관점 2 → 반박 5): 1차 확정 9·반박 4 — 교대 투영이 짧은(6.2 cm)·중복·공선 변 모서리에서 주기 5~8 진동(1~5.7 cm)·수렴 실패, 구–반사 변 접합 정지, 호–변 첨점 포기, 두 번째 라운드·구·다각형 동시 walk·#60 행동 테스트 공백, §8-2 문구 → 정확한 최근접점·이분 탐색·pytest 회귀·UE `Golmok.Photo.Clamp` (c2) 비스듬한 밀기 슬라이드 테스트로 수정. 2차 확정 5·반박 0 — 구가 반사 호와 만나는 곳의 영구 정지(→ 16라운드), 200각형 틱당 3 ms(→ 국소 후보 우선, 0.1 ms), 반사 꼭짓점을 돌 때 한 틱 이동이 스텝의 최대 2배(끝점 S 안·진동 없음 → §11-7 한계로 기록, 코드 유지). 1차 반박 4(PIE 사각형 마진 검사 느슨함, #60 행동 테스트 중복 지적, 비스듬한 walk 단언, Arm 주석)는 결함 아님.
- **테스트**: pytest `test_ue_photo_math.py` 17 → 21(`test_ue_photo_math.py` 테스트 함수 수; 침식 영역 소속·shapely 최근접, 띠·모서리·호·좁은 링·시계 방향, 드라이버 `walk`로 60틱+ 단조 수렴·진동 폭 0·접선 미끄러짐·띠 시작·예각·짧은/중복/공선 변·구–변/구–호 접합, 200각형 비용), `test_ue_wp12_fixture.py` +4(카메라 컷 순서, `bCameraMoveableWhenPaused` 저장 < 정지 < 거부 롤백 < true·복원, 슬라이드 2회·각 구간 Constrain, 클램프 구조). 로컬 게이트: `ruff check` 통과 · `ruff format --check` 96 files · `pytest -q` **752 passed, 3 skipped** · `check_repo.py` OK. UE는 빌드 못 함 → 런북 §7 재검증 절차(틱 샘플 기대값: 980.0에서 단조 정지·변동 0, 대각선 미끄러짐, 벽 W+D 45°에서 1 s ≈ 1.06 m) + §12 #62(`VectorPlaneProject`·`Hit.Time`)·#63(`SetGameCameraCutThisFrame`) 행.
- **바꾸지 않은 것 → 사용자 결정(2026-09-27, D-013 결정 2)**: ① `MaxMultiplier` 2 유지(3x 복귀는 #59 비동기 저장·진행 표시 뒤) ② 2x 촬영 시 1.2 s 정지 허용(폴리시 단계에서 비동기 저장 검토) ③ `PauseMode` 기본값 `GamePause` 유지 ④ 마우스 시선 속도(1000 px = 35°) 현행 유지, 사용자 체감 후 재검토 ⑤ PC fix c026815(정지 잔상·EV 속도) 채택(Opus 적대 검증 통과, PR #27). 코드 변경 없음.

**PR #29 병합 전 보완 리뷰(Opus 5.5 ultracode 워크플로: 수학·폰/서브시스템·문서 3관점 → 지적마다 회의론자 2, 2026-09-27)** — BLOCKING/major 없음. 반영(오케스트레이터): A1 `MoveInsetCm`이 앵커 상한 전의 `C.InsetCm`과 비교해 앵커가 경계에서 inset 이내일 때 구 접합에서 1e-6 cm 허용치로 여백이 매 틱 깎이던 래칫 → `EffectiveInsetCm`으로 먼저 상한(회귀 테스트 `test_walk_anchor_inside_the_inset_band_at_a_sphere_junction_settles`: 수정 전 실패·수정 후 통과 확인) · A5 `ClampToPolygonXY` 비유한 입력 → 2 반환(테스트 추가) · A3/C1 §3-1 라운드 수 16·이분 탐색 문구 · A2 '접합 약 1 cm' → 스텝 비례 표현(런북 §7·§6-2·§11-7) · C2 §0 17행·런북 §0 옛 '내향 법선' 설명 교체 · C3 런북 §7 머리글(수정분·§4·§10·(c2) `slide:` Info 줄) · C4 '1.25 cm' 판정을 dt 기준으로 · C5 §7 ini 블록 `MaxMultiplier=2` · C6/B-4 fixture(런북 `1..N`↔ini↔헤더 기본값, §12 #62/#63, `slide: from`) · B-1 둔각 꺾임 관찰 항목 · B-2 §12 #63 지연 종료·사전 정지 확인 · B-3 스윕 횟수 문구 · C7 0.1 ms 측정 조건 · C10 STATUS 문장. 미반영(기록): A4 좁은 홈 건너편 한 틱 도약(홈 폭 < 2·스텝 − 2·inset), A7 `MeetsConstraint`의 전체 투영 비용(폴백 틱 한정, `InErodedRing`로 대체 가능), A8 오목 접합 1 mm대 후퇴·느린 수렴, B-5 익명 namespace 상수(충돌 없음) — §11-7 한계로 둔다.

**PC 재검증 V-09b (2026-09-28, 런북 §13 'V-09b 재검증')** — 상태 🟡 → **🔴**. PR #29 수정분: §7 ①~⑤ 통과 — footprint는 경계 20 cm 안쪽에서 단조로 멈추고 변동 0(톱니 없음), 대각선은 경계를 따라 106 cm/s·옆 끌림 0, 띠 안 진입 튐 0, 벽 W+D 1 s = 106.07 cm·135° 안쪽 꺾임에서 두 번째 벽을 따라감, 반사 꼭짓점(임시 오목 홈)에서 호를 따라 돌며 120 fps 한 틱 ≤ 1.004배 — §11-7의 한계는 10 fps+Shift(스텝 45 cm)에서 한 틱 69 cm = 1.54배로 실제로 나타남, 앵커가 경계 20 cm 안이면 그 거리로 여백을 낮추고 래칫 없음(PR #29 A1 확인), dt 0.1 s 클램프 작동. 설계와 다른 관찰 1: 구∩경계 접합으로 밀면 멈추지 않고 구면∩경계 원을 따라 카메라가 앵커 높이 쪽으로 내려간다(Shift 1.6 s에 −44 cm; 가장 가까운 점 투영의 설계 동작 — 폴리시 후보, 사용자 결정). **실패 1: §4 종료 밝기** — P로 나가면 눈 적응이 포토 노출에서 이어져 1~4 s 페이드(런북 §12 #64): 종료 틱은 정지로 시작해 카메라 매니저 갱신이 건너뛰어지고 그 옛 포토 POV·PP 프레임이 `RestoreAll`의 컷을 소비한다. 촬영 중 P(지연 종료)는 정상. 후속(클라우드, Opus 5.5): `RestoreAll`에서 카메라 매니저를 같은 틱에 갱신(1순위) 또는 다음 프레임 컷. PC fix 0건.

**V-09b 후속 수정 (2026-09-28, session_01WbUh9LRpBze3YmrZV19iim, Opus 5.5 ultracode)** — 상태 🔴 → **🟡 PC §4 종료 밝기·§7 접합 재검증 대기**.
- **#64 P 종료 시 눈 적응 이력** — 원인(PC V-09b 틱 추적·엔진 소스): P는 정지로 시작한 월드 틱의 PC 틱에서 처리된다. `UWorld::Tick`은 정지 틱이면 풀틱 PC만 `UpdateCameraManager`를 하는데 `RestoreAll`이 풀틱 플래그를 되돌리므로, 그 틱은 카메라 캐시가 옛 포토 POV·PP로 남은 채 그려지며 `RestoreAll`의 컷을 소비한다(컷은 `GameViewportClient` 그리기 뒤 지워짐). 다음 프레임(플레이어 POV)엔 컷이 없어 포토 EV(20 EV/s 눈 적응)에서 1~4 s 페이드. 수정(PC 제안 ①): `RestoreAll`에서 `SetViewTargetWithBlend` → `SetControlRotation` → `PlayerCameraManager->UpdateCamera(0.f)` → `SetGameCameraCutThisFrame()`. 종료 프레임부터 플레이어 POV + 컷. 부작용 검토: 정지 없이 시작한 틱(TimeDilation, 지연 종료 `OnEndFrame` 복원 뒤 다음 틱)은 월드 틱이 같은 틱에 한 번 더 갱신 — 뷰 타깃이 이미 캐릭터라 같은 결과, dt 0 갱신은 셰이크·모디파이어를 진행시키지 않음; 사전 정지 종료 (#63 (b)·§12 #3)는 정지가 유지돼도 캐시가 바로 플레이어 POV라 옛 구도 고정이 풀린다(PC 확인 대상). 대안 ②(다음 프레임 컷)는 런북 §12 #65의 폴백.
- **D-013 결정 3 수평 입력 시 높이 불변**(Fable 설계 결정, `DECISIONS.md`) — `GolmokPhotoMath::Constraint::bKeepHeight`: 구 클램프를 원하는 높이의 수평 단면 원판 최근접점(`ClampToSphereXY`)으로, 그 높이가 구의 높이 범위 밖이면 현재 높이 평면에서; 다각형 클램프는 원래 XY만. `bKeepHeight = false`면 이전과 같은 코드 경로. `MoveConstrained(…, bKeepHeight)`는 벽 슬라이드의 Z 성분을 0으로. `Tick`은 Q/E 축이 데드존(0.1, `PhotoUpDownDeadZone`) 안이면 수직 성분을 버리고 `bKeepHeight`를 켠다. 설계 §3-3(처음엔 '§5-2'로 잘못 인용) "전방(피치 포함)"은 유지 — 피치를 준 W의 Z 변화는 입력이 명령한 것이고 제약은 Z를 더하지 않는다(수평 시선이면 Z 완전 불변). → PR #40 리뷰 뒤 결정 3 확정판으로 대체(아래: W/S도 yaw만). 겹침 후퇴(`bStartPenetrating`)는 복구 동작이라 3D 그대로. 접합에서는 틱마다의 클램프 고정점(정확한 교점에서 한 스텝 이내, 예 1.6 cm 안쪽)에서 멈추고 변동 0.
- **테스트**: pytest `test_ue_photo_math.py` +4(`walkh`/`constrainh` 드라이버 명령: 접합에서 400틱 z 불변·단조·정지, 순수 구 밀기, 피치 이동·높이 범위 밖, 무작위 점 z 보존·두 제약 만족; 옛 `walk`는 같은 입력에서 z가 10 cm 넘게 내려감을 단언해 판별력 확인), `test_ue_wp12_fixture.py` 카메라 컷 순서 검사 갱신(뷰 타깃 < 제어 회전 < `UpdateCamera(0.f)` < 컷 < `ApplyPause(false)`) + 높이 불변 정적 검사 1. UE 자동화(이름 추가 없음, 총 28 유지): `EnterExit` — Exit 직전 카메라 매니저가 포토 카메라 자리(> 20 cm, 전제)·직후 플레이어 카메라(2 cm)·컷, 새 단계 `PrePausedExit`로 사전 정지 종료도 같은 검사(정지 유지 확인 포함); `Clamp` (b2) — 유효 반경 R 기준 0.5 R 높이·반변 0.85 R 정사각형으로 구와 경계가 **둘 다** 걸리는 접합에서 60회 수평 밀기 → |dz| ≤ 0.01·단면 원·여백 선 도달. 전체 `pytest -q` 806 passed·3 skipped, `ruff`·`check_repo.py` 통과.
- **적대 검증**(Workflow 1회: 엔진·수학·폰·테스트 4관점 → 지적마다 회의론자 1, 8에이전트): 확정 3 전부 수정 — ① `Clamp` (b2) 첫 판이 구에 닿지 않아(반경 300 대비 모서리 261 cm) 옛 코드로도 통과 → 접합 기하로 재작성·구 도달 단언(major), ② 패드 트리거 축에 데드존이 없어 손가락만 얹어도 `UpDownInput ≠ 0` → 3D 클램프 복귀 → 데드존 0.1(minor), ③ 사전 정지 종료의 카메라 위치가 미검사(Enter·Exit가 같은 업데이트) → `PrePausedExit` 단계(minor). 반박 1(주 종료 경로 단언이 무의미하다는 지적 — L_Dev 기하에서 ≈74 cm 이동이라 판별력 있음; 전제 단언은 보강으로 추가). 수학 관점 지적 0(퍼즈 포함).
- **남은 것**: PC V-09c — 런북 §4 "종료 밝기" 1~4(EV ±3, GamePause 즉시·지연, TimeDilation, 사전 정지 (b))·§7 "접합 수평 입력 시 높이 불변" ①~⑥(→ 아래 "PR #40 리뷰 반영"에서 ①~⑦·§12 #67로 갱신)·빌드(§12 #65 `UpdateCamera` 접근성, #66 `bGameCameraCutThisFrame` 공개 여부).

**PR #40 리뷰 반영 (2026-09-28, Opus 5.5 ultracode; 설계 결정은 Fable)** — 상태 🟡 유지(PC V-09c 대기). 리뷰(수학·런타임·테스트/문서 3관점)의 (A)/(B) 전부 반영. **D-013 결정 3 확정판**(M1/M2/N1/N2, `DECISIONS.md`): W/S/A/D는 항상 yaw 기준 수평면 이동, 높이는 Q/E만 — `AGolmokPhotoCameraPawn::Tick`의 전방을 `FRotator(0.f, Look.Yaw, 0.f).Vector()`로(§3-3 "전방(yaw만)"). 피치 W/S가 높이 유지 클램프와 만나 구 경계에서 극까지 타고 오르며 틱당 최대 11배 튀던 결함(M1)과 런북 §7 '피치 0°±2°에서 z ±0.01 cm' 판정 모순(M2/T1)이 함께 사라지고, `bKeepHeight`·`ClampToSphereXY`·슬라이드 평탄화는 방어 수단으로 남는다. **R1 사전 정지 종료 플래그 지연 복원**(런북 §12 #67): `RestoreAll`이 `ApplyPause(false)` 뒤에도 월드가 정지면(`IsGamePaused`, 저장값 false) `bIsCameraMoveableWhenPaused`를 true로 두고 `FCoreDelegates::OnEndFrame`에 `OnEndFrameCameraMoveableRestore`를 걸어 정지 해제를 본 첫 프레임에 복원(정지 유지 중 뷰 이력이 읽기 전용이 되어 포토 마지막 프레임의 TSR·Lumen 이력이 컷 뒤 재투영되는 것을 피함 — 추론, PC 미확인); `Deinitialize`·`TeardownForDeadWorld`·재진입 `Enter`는 대기 중 복원을 버리고(`CancelCameraMoveableRestore`) `Enter`는 앞 세션의 저장값을 유지한다. §4-3 복원 순서를 코드 순서로 고침(R2). **테스트**(자동화 이름 추가 없음, 총 28 유지): `EnterExit` — 두 종료에 Info `exit camera: before …, after …, cut …`(T3), 사전 정지 종료 뒤 플래그 true 유지·정지 해제 한 프레임 뒤 저장값(false) 복원 단언(새 단계 `PrePausedRestore`); `Clamp` — (c2) 벽 대각 슬라이드를 `bKeepHeight`로 한 번 더(측면 > 20 cm·|dz| ≤ 0.01·면 거리 ≥ 반경 − 1, Info `keep height wall slide: …`, M3); pytest — PR #29 walk 회귀 5개를 `walk`/`walkh`로 parametrize(+5, `walkh`에서 수평 스텝이면 z 불변 단언, M3), fixture +3(지연 복원 구조·Info 줄/런북 인용·런북 §7 피치 전제 없음)·기존 3개 갱신(yaw 전방, Enter 저장값 유지, 복원 순서 view < control < refresh < cut < unpause < 정지 분기). **런북**: §1 Info 목록(`exit camera:`·`keep height:`·`keep height wall slide:`), §4-4 정지 유지 중 둘째~10번째 프레임 잔상 판정·✗ 때 조치(T5), §7 ①~⑦ 재작성(피치 전제 삭제, ⑤ 피치 −30° W → z 변동 0, ⑥ `showdebug enhancedinput`으로 `IA_GolmokPhotoUpDown` 축 확인(T6), ⑦ 낮은 카메라로 경사로 수평 밀기 → 정지), §12 #67, §13 V-09c ①~⑦·Info 문구(T2/N2). 남은 것: PC V-09c — 런북 §4 "종료 밝기" 1~4(4는 잔상 판정 포함)·§7 ①~⑦·빌드(§12 #65·#66·#67).

**다음 세션 인계** — 한 것: 포토 모드 최소판 코드·테스트·런북, C2248 7곳 수정, main(WP-18) 병합. 남은 것: V-09 PC 검증, PR #24와 함께 `Golmok.` 전체 자동화. 주의: `GameViewportClientClassName`(DefaultEngine.ini 핫스팟)은 뷰포트 억제 플래그 복원용 — 빼면 false 복원 폴백; 정지 중 입력이 안 먹으면 `PauseMode=TimeDilation`.

