# WP-04 — UE C++ 런타임 1: Geo·Zone

상태: ⚪ 대기 · 담당: 클라우드 Claude 세션 · 의존: WP-02 · 검증: **G2(PC 빌드·PIE, `runbooks/pc-verify-wp04.md`)**

## 목표
Zone manifest를 읽어 청크 메시·충돌·blocker를 올바른 위치에 배치하고, 거리·우선순위 규칙으로 로드/언로드하며, 겹치는 배경 베이스맵을 숨기는 **런타임 핵심**을 C++로 만든다. 이 세션은 UE를 빌드할 수 없으므로 **보수적인 API + 상세한 PC 검증 런북**이 완료 조건이다.

## 배경
- `docs/ARCHITECTURE.md` §2(좌표), §4(교체 규칙), §7(클라이언트 구조)
- `docs/spec/zone-manifest.md`(WP-02) — UE 매핑 규약과 ENU→UE 변환. 수치 예제로 C++ 변환을 검증한다.
- 기존 코드 스타일: `Source/Golmok/Player/GolmokCharacter.*`(Config UPROPERTY, 런타임 생성, LogGolmok), `Golmok.Build.cs`
- D-003: 로직 C++, 플러그인(Cesium/XGRIDS)에 **컴파일 의존 금지**. Cesium 연동은 Python(`basemap_import._set_georeference`)이 맡는다.
- D-012: 배경 제외는 빌드 단계가 기본. 런타임 숨김은 **보조**(태그 기반).

## 산출물 (`unreal/Golmok/Source/Golmok/`)
1. `Geo/GolmokGeo.h/.cpp` — 순수 수학(UObject 아님): WGS84 상수, `LatLonHToEcef`, `EcefToLatLonH`, `EnuFrameAt(lat,lon,h) -> FMatrix(double)`, `EnuToUE(FVector3d m) -> FVector(cm, X=east, Y=south, Z=up)`, `UEToEnu`. 모두 double(`FVector3d`, `FMatrix44d`).
2. `Geo/GolmokGeoOrigin.h/.cpp` — `AGolmokGeoOrigin` 액터(레벨에 1개, `UPROPERTY(EditAnywhere) double Latitude, Longitude, HeightEllipsoidal`). `basemap_import.py`가 이 액터를 만들거나 갱신하도록 Python 한 줄 추가(WP-06에서 확정, 여기서는 `FindOrSpawn` 규약만 문서화).
3. `Geo/GolmokGeoSubsystem.h/.cpp` — `UGolmokGeoSubsystem : UWorldSubsystem`: 원점 액터를 찾고, `ZoneLocalToWorld(const FMatrix44d& ZoneToEcef) -> FTransform`(zone-local ENU m → area ENU → UE cm)를 제공. 원점이 없으면 경고 후 항등(개발 레벨용).
4. `Zones/GolmokZoneManifest.h/.cpp` — USTRUCT들(`FGolmokZoneChunk`, `FGolmokZoneLayers`, `FGolmokZonePortal`, `FGolmokZoneManifest`)과 `LoadManifest(const FString& Path, FGolmokZoneManifest& Out, FString& Error)`(`FJsonSerializer`, 필수 필드 검사, transform 16개). 스펙의 필드명과 **정확히** 일치.
5. `Zones/GolmokZone.h/.cpp` — `AGolmokZone`:
   - `UPROPERTY(EditAnywhere) FString ZoneId; int32 Version;` 경로 규약으로 manifest·에셋 위치 계산(스펙 §UE 매핑).
   - `Load()`: manifest 읽기 → 루트 트랜스폼 설정(GeoSubsystem) → 청크마다 `UStaticMeshComponent` 생성, `StaticLoadObject`/`FSoftObjectPath`로 `SM_<chunk_id>` 로드(동기 로드로 시작, `FStreamableManager` 비동기 로드는 옵션 플래그) → 충돌 메시 컴포넌트(hidden in game, 충돌만) → blocker 컴포넌트(hidden, 충돌만, `blockers.json` 파싱) → `bLoaded=true`. 에셋이 없으면 청크 bbox 크기의 **와이어 박스**를 대신 그려(DrawDebugBox 또는 간단한 프록시) 위치 검증이 가능하게.
   - `Unload()`, `UFUNCTION(CallInEditor) void RebuildInEditor()`.
   - 청크별 `SetVisibility`로 스파이크용 레이어 토글 함수(`SetVisualVisible(bool)`, `SetCollisionEnabled(bool)`).
6. `Zones/GolmokZoneSubsystem.h/.cpp` — `UGolmokZoneSubsystem : UTickableWorldSubsystem`: 레벨의 `AGolmokZone`들을 등록, 플레이어 폰과 footprint(또는 bbox) 거리로 `LoadRadiusM/UnloadRadiusM`(Config) 히스테리시스 로드·언로드, `priority`→`version` 우선순위(겹침 시 낮은 쪽 `SetVisualVisible(false)`), **베이스맵 숨김**: 액터 태그 `GolmokBasemap`이 있고 바운드 중심이 footprint(ENU 폴리곤, point-in-polygon) 안이면 숨김+충돌 끔, 언로드 시 복원. 콘솔 명령 `golmok.zone.list/load/unload <id>`(`FAutoConsoleCommand`).
7. `Golmok.Build.cs`: `"Json", "JsonUtilities"` 추가(필요 시 `"DeveloperSettings"`). `GolmokGameMode`나 모듈 시작에서 아무것도 바꾸지 않아도 서브시스템은 자동 생성된다.
8. `Config/DefaultGame.ini`: 패키징에 manifest 포함 — `[/Script/UnrealEd.ProjectPackagingSettings] +DirectoriesToAlwaysStageAsUFS=(Path="Golmok/Zones")`. `[/Script/Golmok.GolmokZoneSubsystem] LoadRadiusM=150 UnloadRadiusM=250`.
9. **합성 픽스처**: `unreal/Golmok/Content/Golmok/Zones/z_synthetic_001/v1/manifest.json`(WP-02 픽스처 복사, 청크 3개·충돌 1개·blocker 1개·포털 1개, 원점은 L_Dev 원점 근처) + `unreal/Golmok/Content/Python/golmok/synthetic_zone.py`: 에디터 Python으로 `SM_c00..c02`(큐브 스케일)·`SM_z_synthetic_001_collision`을 `/Game/Golmok/Zones/z_synthetic_001/v1/`에 생성하고 `AGolmokGeoOrigin`·`AGolmokZone` 액터를 L_Dev에 배치. (에디터 검증용. 클라우드에서는 실행 불가.)
10. **런북** `docs/runbooks/pc-verify-wp04.md`: 빌드 → `synthetic_zone.run()` → PIE에서 (1) 청크가 manifest 위치에 보임 (2) 충돌 메시 위를 걸음 (3) blocker에 막힘 (4) 멀어지면 언로드·가까우면 로드(콘솔 `golmok.zone.list`) (5) 베이스맵 태그 액터 숨김 (6) 스펙 수치 예제와 `ZoneLocalToWorld` 결과 비교(로그 출력) — 각 항목 체크박스와 예상 로그. **컴파일 에러가 나면 고치고 커밋**하라는 지시와, 5.8에서 바뀌었을 가능성이 있는 API 목록(세션이 확신 없는 호출을 여기 적는다).
11. `tools/tests/test_ue_zone_fixture.py`: 픽스처 manifest가 WP-02 스키마를 통과하는지.

## 완료 기준
- 위 파일이 모두 있고, 헤더는 `#pragma once`, `GENERATED_BODY`, `GOLMOK_API` 규약 준수, include 경로는 모듈 루트 상대(`"Zones/GolmokZone.h"`).
- 세션이 **코드 리뷰 체크리스트**를 스스로 수행하고 WP 문서 "결과"에 기록: (a) 모든 UPROPERTY 타입이 리플렉션 가능 (b) double↔float 변환 명시 (c) 에디터 전용 코드는 `#if WITH_EDITOR` (d) 로그 카테고리 `LogGolmok` (e) nullptr 검사 (f) Tick 비용(매 프레임 폴리곤 검사 금지: 0.5초 간격 타이머).
- `pytest` 통과(픽스처 테스트), CI 초록, STATUS `🟡 코드 완료·PC 검증 대기`.

## 주의
- **UE 5.8 API를 확신할 수 없는 곳**은 가장 오래된 안정 API를 쓴다(`UWorldSubsystem`, `FJsonSerializer`, `UStaticMeshComponent::SetStaticMesh`, `FAutoConsoleCommandWithWorldAndArgs`). 5.x에서 deprecated된 것(`TAssetPtr`, `GetWorld()->GetFirstPlayerController()` 남용 등)은 피한다.
- 대용량 청크 동기 로드는 히치를 만든다. 우선 동기로 두되 `bAsyncLoad` 플래그와 TODO를 남긴다.

## 결과
(세션이 작성)
