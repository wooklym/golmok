# WP-05 — UE C++ 런타임 2: 포털·조명·디버그

상태: ⚪ 대기 · 담당: 클라우드 Claude 세션(**Fable 5.1 ultracode**, 모델 정책 DEVELOPMENT-PLAN §7.4) · 의존: WP-04 · 검증: **G2(`runbooks/pc-verify-wp05.md`)**

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

## 결과
(세션이 작성)
