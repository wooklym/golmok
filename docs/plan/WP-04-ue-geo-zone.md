# WP-04 — UE C++ 런타임 1: Geo·Zone

상태: 🟡 코드 완료·PC 검증 대기 (2026-09-24, session_01GGmw3pPHLp4Wk5Us9243AL) · 담당: 클라우드 Claude 세션(**Fable 5.1 ultracode**, 모델 정책 DEVELOPMENT-PLAN §7.4) · 의존: WP-02 · 검증: **G2(PC 빌드·PIE, [runbooks/pc-verify-wp04.md](../runbooks/pc-verify-wp04.md))**

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

## 설계 (확정, 2026-09-24)

근거: `docs/spec/zone-manifest.md` §1/§3/§3.1/§4/§5, 이 문서 산출물 1~11, ARCHITECTURE §2/§4/§7, D-003(플러그인 컴파일 의존 금지), D-012(베이스맵 정적 Nanite, 런타임 숨김은 보조). 세 후보 설계(스펙 충실도·성능·안정성)를 심사해 **스펙 충실도안을 기준으로 나머지 둘의 장점을 이식**하고 지적된 결함을 모두 닫은 최종안이다. 커밋 `90a0d69`~`10208b6`에 이미 올라간 코드가 있으므로 식별자는 그 코드를 따르고, 코드가 이 설계와 다른 곳은 §12 "커밋 대비 변경 목록"에 적어 구현 세션이 그대로 반영한다. 선택지는 남기지 않았다.

### 0. 확정 결정 요약
| 주제 | 결정 |
|---|---|
| 순수 수학 | `Geo/GolmokGeoMath.h`(커밋됨, API 변경 금지: `test_ue_geo_math.py`·`geomath_driver.cpp`가 고정). `Mat4 = std::array<double,16>` row-major·열벡터 |
| 평가 방식 | `FTimerManager` 0.5 s 루프(틱 서브시스템 아님). 매 프레임 작업 0 |
| 거리 지표 | footprint 폴리곤(레벨 UE XY) 거리. **`FBox2D` 사전검사** 후 링 구간에서만 폴리곤 거리 계산 |
| 히스테리시스 | `LoadRadiusM=150` 안이면 로드, `UnloadRadiusM=250` 밖이면 언로드. 발화당 `MaxLoadsPerUpdate=1`·`MaxUnloadsPerUpdate=2` |
| 겹침 패자 | `SetVisualVisible(false)`**만**(스펙 문구 그대로). 충돌까지 끄는 것은 `bSuppressLoserCollision=False` 옵트인 |
| 콘솔 언로드 | `bBlocked`: `golmok.zone.unload`한 zone은 플레이어가 `UnloadRadiusM` 밖으로 나갈 때까지 거리 자동 로드 금지 |
| 로드 실패 | `bLoadFailed`: 재시도·로그 반복 금지. `golmok.zone.load`·`golmok.zone.refresh`·`RebuildInEditor`가 해제 |
| 베이스맵 숨김 | 태그 `GolmokBasemap` 액터 캐시(`TWeakObjectPtr` 키, 인덱스 금지). `GolmokBasemapTerrain` 태그 액터는 `replaces.terrain_clip=false`인 zone이 숨기지 않음 |
| 캐시 갱신 | `OnWorldBeginPlay`, `FWorldDelegates::LevelAddedToWorld/LevelRemovedFromWorld`, `golmok.zone.refresh`. 주기 재스캔 `BasemapRescanSeconds=0`(끔) |
| blocker 두께 | `AGolmokZone::BlockerThicknessCm`(`UCLASS(Config=Game)`, 기본 10). 서브시스템이 아니라 액터에 둔다(에디터 월드에도 존재) |
| 에디터 자동 리빌드 | **없음**. `RebuildInEditor()`를 WP-06 Python·디테일 버튼이 명시 호출. `PostEditChangeProperty(ZoneId/Version)`은 `Unload()`+manifest 무효화만 |
| GeoOrigin 기본값 | 스펙 area 원점 (37.5600, 126.9230, 40). `synthetic_zone.run()` 기본 `geo_origin="area"` |
| manifest 구조체 | 스펙 §3과 1:1(`Layers.Visual/Collision/Blockers/Navmesh` 중첩, `Quality/Consent/Attribution/Sources` 포함), enum `EGolmokZoneKind/EGolmokVisualFormat/EGolmokBlockerKind` |
| 비동기 로드 | `bAsyncLoad=False` 플래그 + `FStreamableManager` TODO 본문(§4-4)만. WP-04는 동기 |
| 큐브 픽스처 | **채택 안 함**: `synthetic_zone.py`가 실제 형상(GLB, 프로브로 임포터 매핑 측정 후 미리 변환)을 만들어 배치를 검증하므로 `bDevFitChunkToBBox`/큐브 복제 경로는 넣지 않았다. 에셋이 없으면 와이어 박스만 |

### 1. 파일 목록 (`unreal/Golmok/` 기준)
| 경로 | 상태 | 내용 |
|---|---|---|
| `Source/Golmok/Geo/GolmokGeoMath.h` | 있음·**변경 금지** | 순수 수학(`<array> <cmath> <cstddef>`만). §8 |
| `Source/Golmok/Geo/GolmokGeo.h/.cpp` | 있음 | `namespace GolmokGeo` UE 타입 래퍼 + `RunSpecSelfTest` |
| `Source/Golmok/Geo/GolmokGeoOrigin.h/.cpp` | 있음 | `AGolmokGeoOrigin` |
| `Source/Golmok/Geo/GolmokGeoSubsystem.h/.cpp` | 있음 | `UGolmokGeoSubsystem` + 콘솔 `golmok.geo.selftest` |
| `Source/Golmok/Zones/GolmokZoneManifest.h/.cpp` | 있음 → **구조체 확장** | USTRUCT/UENUM + `GolmokZoneManifest::ParseManifestText/LoadManifest/ParseBlockersText/LoadBlockers` + 경로 함수 |
| `Source/Golmok/Zones/GolmokZone.h/.cpp` | 있음 → 소폭 변경 | `AGolmokZone` |
| `Source/Golmok/Zones/GolmokZoneSubsystem.h/.cpp` | 있음 → 소폭 변경 | `UGolmokZoneSubsystem` + 콘솔 5개 |
| `Source/Golmok/Golmok.Build.cs` | 있음 | `"Json", "JsonUtilities"`(이미 있음. `JsonUtilities`는 산출물 7 그대로 유지, `DeveloperSettings` 불필요) |
| `Config/DefaultGame.ini` | 있음 → 키 추가 | §7 |
| `Content/Golmok/Zones/z_synthetic_001/v1/{manifest,blockers}.json` | 있음 | WP-02 픽스처와 바이트 동일(테스트가 강제) |
| `Content/Python/golmok/synthetic_zone.py` | 있음 | GLB 2-pass 임포트(프로브로 임포터 축·스케일 측정 후 미리 변환), FindOrSpawn, 더미 베이스맵 큐브 |
| `tools/tests/test_ue_geo_math.py`, `fixtures/ue/geomath_driver.cpp` | 있음 | g++ 교차검증(§8) |
| `tools/tests/test_ue_zone_fixture.py`, `test_ue_python_synthetic_zone.py` | 있음 → ini 키 검사 추가 | §9 |
| `docs/runbooks/pc-verify-wp04.md` | 있음 → §10 반영 | PC 검증 |

### 2. 좌표·경로 규약 (스펙 §1·§5 그대로)
- zone-local ENU(m) → ECEF: manifest `transform`(16, row-major, 열벡터). area ENU = `AGolmokGeoOrigin`(lat/lon/h)의 ENU. `M = inv(T_area)·T_zone` **4×4 전체**.
- ENU→UE `S = diag(100,-100,100)`; 루트 액터 = `S·M·S⁻¹`(회전 `D R D`, det +1, 위치 `S·t`). 청크 정점은 이미 UE cm이므로 청크 컴포넌트는 **항등 상대 트랜스폼**. `UE Yaw = -yaw_deg`.
- bbox: `S` 적용 후 성분별 min/max 재정렬(`GolmokGeo::EnuBoxToUE`). 포털: 위치 `S·position`, Yaw `-yaw_deg`, 반경 `100·radius_m`. blocker: 중심 `S·center`, 법선 `D·normal`, 높이축 = zone +z의 평면 투영(수평이면 +y), 폭축 = 높이축 × 법선(`GolmokGeoMath::BlockerAxes(n, &w, &h)`; 수평 법선 (0,0,1) → h=(0,1,0), **w=(+1,0,0)**).
- manifest 파일: `<ProjectContentDir>/Golmok/Zones/<zone_id>/v<version>/manifest.json`(non-asset, `+DirectoriesToAlwaysStageAsUFS=(Path="Golmok/Zones")`로 pak에 UFS 스테이징, `FFileHelper`로 읽음). `blockers.json`은 manifest 폴더 기준 `layers.blockers.uri`.
- 에셋: 패키지 `/Game/Golmok/Zones/<zone_id>/v<version>`, 청크 `SM_<chunk_id>`, 충돌 `SM_<zone_id>_collision`(`collision.chunks`가 있으면 `SM_<zone_id>_collision_<chunk_id>`). 오브젝트 경로는 `<pkg>/SM_x.SM_x`. 함수: `GolmokZoneManifest::ManifestFilePath/AssetFolder/ChunkAssetPath/CollisionAssetPath`.
- uri 안전(스펙 §2): 비어있지 않음, `/` 구분, `..`·`\`·절대경로·`scheme:` 금지 → `IsSafeRelativeUri`. 실패는 Error.

### 3. 클래스·함수 시그니처

#### 3-1 `Geo/GolmokGeo.h` (커밋됨, `namespace GolmokGeo`, 전부 `GOLMOK_API`, double)
```cpp
bool ToMat4(const TArray<double>& RowMajor16, GolmokGeoMath::Mat4& Out);   // Num()!=16 → false, Identity
FVector ToFVector(const GolmokGeoMath::Vec3&);  GolmokGeoMath::Vec3 ToVec3(const FVector&);
FMatrix ToFMatrix(const GolmokGeoMath::Mat4& A);       // F.M[i][j] = At(A, j, i), 이동 = F.M[3][0..2] (UE 행벡터)
FTransform ToFTransform(const GolmokGeoMath::Mat4& UEMatrix); // 3x3 → FQuat(정규화), 스케일 1 강제
FVector EnuToUE(const FVector& EnuM);  FVector UEToEnu(const FVector& UECm);  FVector EnuDirToUE(const FVector& Dir);
FBox EnuBoxToUE(const FVector& MinEnu, const FVector& MaxEnu);                 // S 후 min/max 재정렬
double UEYawDeg(const GolmokGeoMath::Mat4& ZoneToArea);                        // -yaw_deg
bool RunSpecSelfTest(FString& OutReport);   // 스펙 §4 표 B·C 5행 + Yaw −30 (1e-4 m / 0.01 cm / 1e-6)
```

#### 3-2 `Geo/GolmokGeoOrigin.h` (커밋됨)
```cpp
UCLASS(HideCategories = (Rendering, Replication, Collision, Input, LOD, Cooking, Physics, Networking))
class GOLMOK_API AGolmokGeoOrigin : public AActor {
  GENERATED_BODY()
public:
  AGolmokGeoOrigin();                                   // Root USceneComponent(Static), Tick off
  UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Golmok|Geo") double Latitude = 37.5600;
  UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Golmok|Geo") double Longitude = 126.9230;
  UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Golmok|Geo") double HeightEllipsoidal = 40.0;  // 타원체고
  static AGolmokGeoOrigin* Find(UWorld* World);         // TActorIterator 첫 번째. 2개 이상·(0,0,0) 아님 → Warning
  int32 GetRevision() const;                            // PostEditChangeProperty마다 ++
#if WITH_EDITOR
  virtual void PostEditChangeProperty(FPropertyChangedEvent&) override;
#endif
};
```
규약: 레벨 원점(0,0,0) = area 원점, 액터 위치는 무시. WP-06 `FindOrSpawn`: `get_all_level_actors()`의 첫 `unreal.GolmokGeoOrigin`, 없으면 (0,0,0) 스폰, 라벨 `GeoOrigin`, 폴더 `Golmok`, `latitude/longitude/height_ellipsoidal` ← basemap manifest `origin`.

#### 3-3 `Geo/GolmokGeoSubsystem.h` (커밋됨) — 모든 월드 타입(Editor 포함)에 생성
```cpp
UCLASS() class GOLMOK_API UGolmokGeoSubsystem : public UWorldSubsystem {
  GENERATED_BODY()
public:
  virtual void Deinitialize() override;
  bool HasOrigin();  bool GetOrigin(double& Lat, double& Lon, double& H);
  int32 GetOriginRevision();                            // PresenceRevision*100000 + Origin->GetRevision()
  bool ZoneToAreaMatrix(const TArray<double>& ZoneToEcefRowMajor, GolmokGeoMath::Mat4& Out); // 16개 아니면 false
  FTransform ZoneLocalToWorld(const TArray<double>& ZoneToEcefRowMajor);   // ToFTransform(UEActorMatrix(M))
  FTransform ZoneLocalToWorld(const GolmokGeoMath::Mat4& ZoneToEcef);
  bool LonLatToLevelUE(double LonDeg, double LatDeg, double H, FVector& OutLevelUE);   // 원점 없으면 false(임의 점에는 폴백 없음)
  static FVector LonLatToLevelUE(const GolmokGeoMath::Mat4& EcefToArea, double LonDeg, double LatDeg, double H);
  bool LevelUEToLonLat(const FVector& LevelUE, double& Lat, double& Lon, double& H);
  GolmokGeoMath::Mat4 EcefToAreaMatrix(double FallbackLat, double FallbackLon, double FallbackH);
private:
  AGolmokGeoOrigin* FindOrigin();  void WarnNoOriginOnce();   // 원점 없을 때 재탐색은 2 s에 1회
  TWeakObjectPtr<AGolmokGeoOrigin> CachedOrigin; double LastMissSeconds; bool bWarnedNoOrigin; int32 PresenceRevision; bool bLastHadOrigin;
};
```
원점 없음 = **zone 자신의 원점을 area 원점으로**(zone이 레벨 원점에 yaw만 적용되어 놓임) + 월드당 Warning 1회. 콘솔 `golmok.geo.selftest`(`.cpp` 파일 범위 `static FAutoConsoleCommandWithWorldAndArgs`)는 `RunSpecSelfTest` 결과 PASS/FAIL과 현재 레벨 원점을 출력 — 런북 항목 (6)은 이 명령 하나다.

#### 3-4 `Zones/GolmokZoneManifest.h` — 스펙 §3과 1:1 (JSON 키 → PascalCase 멤버)
```cpp
UENUM(BlueprintType) enum class EGolmokZoneKind : uint8 { Exterior, Interior };
UENUM(BlueprintType) enum class EGolmokVisualFormat : uint8 { NaniteMesh, SplatPly, Splat3DTiles, SplatLcc, Unknown }; // D-010 전: 로더는 NaniteMesh만
UENUM(BlueprintType) enum class EGolmokBlockerKind : uint8 { Glass, NoEntry };
USTRUCT(BlueprintType) struct GOLMOK_API FGolmokZoneChunk { GENERATED_BODY()          // visual.chunks[] / collision.chunks[] 공용
  UPROPERTY(...) FString Id;  UPROPERTY(...) FString Uri;
  UPROPERTY(...) FVector BboxMinEnu = FVector::ZeroVector;  UPROPERTY(...) FVector BboxMaxEnu = FVector::ZeroVector; // zone-local m (FVector = FVector3d)
  UPROPERTY(...) bool bHasBbox = false;  UPROPERTY(...) int32 Tris = 0; };
USTRUCT(BlueprintType) struct GOLMOK_API FGolmokZoneTexture { GENERATED_BODY() UPROPERTY(...) FString Uri; UPROPERTY(...) FString ChunkId; UPROPERTY(...) FString Role; };
USTRUCT(BlueprintType) struct GOLMOK_API FGolmokZoneVisualLayer { GENERATED_BODY()
  UPROPERTY(...) EGolmokVisualFormat Format = EGolmokVisualFormat::NaniteMesh;  UPROPERTY(...) FString FormatString;   // 원문(로그용)
  UPROPERTY(...) TArray<FGolmokZoneChunk> Chunks;  UPROPERTY(...) TArray<FGolmokZoneTexture> Textures; };
USTRUCT(BlueprintType) struct GOLMOK_API FGolmokZoneCollisionLayer { GENERATED_BODY()
  UPROPERTY(...) FString Format;  UPROPERTY(...) FString Uri;  UPROPERTY(...) TArray<FGolmokZoneChunk> Chunks; };
USTRUCT(BlueprintType) struct GOLMOK_API FGolmokZoneBlockersLayer { GENERATED_BODY() UPROPERTY(...) bool bPresent = false; UPROPERTY(...) FString Uri; };
USTRUCT(BlueprintType) struct GOLMOK_API FGolmokZoneNavmeshLayer  { GENERATED_BODY() UPROPERTY(...) bool bPresent = false; UPROPERTY(...) FString Format; UPROPERTY(...) FString Uri; };
USTRUCT(BlueprintType) struct GOLMOK_API FGolmokZoneLayers { GENERATED_BODY()
  UPROPERTY(...) FGolmokZoneVisualLayer Visual;  UPROPERTY(...) FGolmokZoneCollisionLayer Collision;
  UPROPERTY(...) FGolmokZoneBlockersLayer Blockers;  UPROPERTY(...) FGolmokZoneNavmeshLayer Navmesh; };
USTRUCT(BlueprintType) struct GOLMOK_API FGolmokZonePortal { GENERATED_BODY()          // WP-05가 그대로 사용
  UPROPERTY(...) FString Id;  UPROPERTY(...) FString ToZone;  UPROPERTY(...) FVector PositionEnu = FVector::ZeroVector;
  UPROPERTY(...) double YawDeg = 0.0;  UPROPERTY(...) double RadiusM = 1.0;  UPROPERTY(...) FString Kind; };
USTRUCT(BlueprintType) struct GOLMOK_API FGolmokZoneReplaces { GENERATED_BODY() UPROPERTY(...) TArray<FString> BuildingIds; UPROPERTY(...) bool bTerrainClip = false; };
USTRUCT(BlueprintType) struct GOLMOK_API FGolmokZoneQuality { GENERATED_BODY()          // 값 null 가능 → bHas*; 추가 키는 ExtraJson 문자열 보존
  UPROPERTY(...) bool bHasIcpRmseM = false;  UPROPERTY(...) double IcpRmseM = 0.0;  UPROPERTY(...) bool bHasFootprintIou = false;  UPROPERTY(...) double FootprintIou = 0.0;
  UPROPERTY(...) FString ReviewedBy;  UPROPERTY(...) FString ReviewedAt;  UPROPERTY(...) FString ExtraJson; };
USTRUCT(BlueprintType) struct GOLMOK_API FGolmokZoneConsent { GENERATED_BODY() UPROPERTY(...) FString Type; UPROPERTY(...) FString RecordId; }; // null → ""
USTRUCT(BlueprintType) struct GOLMOK_API FGolmokZoneSource  { GENERATED_BODY() UPROPERTY(...) FString CaptureId; UPROPERTY(...) FString Note; };
USTRUCT(BlueprintType) struct GOLMOK_API FGolmokZoneManifest { GENERATED_BODY()
  UPROPERTY(...) int32 SchemaVersion = 0;  UPROPERTY(...) FString ZoneId;  UPROPERTY(...) int32 Version = 0;
  UPROPERTY(...) EGolmokZoneKind Kind = EGolmokZoneKind::Exterior;  UPROPERTY(...) FString ParentZone;   // null → ""
  UPROPERTY(...) double OriginLat = 0.0;  UPROPERTY(...) double OriginLon = 0.0;  UPROPERTY(...) double OriginHeightEllipsoidal = 0.0;
  UPROPERTY(...) FVector OriginEcef = FVector::ZeroVector;  UPROPERTY(...) TArray<double> Transform;   // 16 row-major
  UPROPERTY(...) TArray<FVector2D> FootprintLonLat;        // 외곽 링, 닫힘 중복점 제거, X=lon Y=lat. 구멍 링은 Warning 후 무시
  UPROPERTY(...) FGolmokZoneReplaces Replaces;  UPROPERTY(...) FGolmokZoneLayers Layers;  UPROPERTY(...) TArray<FGolmokZonePortal> Portals;
  UPROPERTY(...) int32 Priority = 0;  UPROPERTY(...) FGolmokZoneQuality Quality;  UPROPERTY(...) FGolmokZoneConsent Consent;
  UPROPERTY(...) TArray<FString> Attribution;  UPROPERTY(...) TArray<FGolmokZoneSource> Sources;
  bool IsInterior() const { return Kind == EGolmokZoneKind::Interior; }  FString Key() const; /* "<zone_id>@v<version>" */ };
USTRUCT(BlueprintType) struct GOLMOK_API FGolmokBlockerPlane { GENERATED_BODY() UPROPERTY(...) FString Id;
  UPROPERTY(...) FVector CenterEnu = FVector::ZeroVector;  UPROPERTY(...) FVector NormalEnu = FVector(0,-1,0);
  UPROPERTY(...) FVector2D SizeM = FVector2D(1,1); /* [폭, 높이] */  UPROPERTY(...) EGolmokBlockerKind Kind = EGolmokBlockerKind::NoEntry; };
USTRUCT(BlueprintType) struct GOLMOK_API FGolmokBlockers { GENERATED_BODY() UPROPERTY(...) TArray<FGolmokBlockerPlane> Planes; };
namespace GolmokZoneManifest {
  GOLMOK_API bool ParseManifestText(const FString& Json, FGolmokZoneManifest& Out, FString& Error);
  GOLMOK_API bool LoadManifest(const FString& FilePath, FGolmokZoneManifest& Out, FString& Error);   // FFileHelper::LoadFileToString + Parse, Error 앞에 경로
  GOLMOK_API bool ParseBlockersText(const FString& Json, FGolmokBlockers& Out, FString& Error);
  GOLMOK_API bool LoadBlockers(const FString& FilePath, FGolmokBlockers& Out, FString& Error);
  GOLMOK_API bool IsSafeRelativeUri(const FString& Uri);
  GOLMOK_API EGolmokVisualFormat ParseVisualFormat(const FString& S);   // 미지 문자열 → Unknown
  GOLMOK_API FString ManifestFilePath(const FString& ZoneId, int32 Version);  GOLMOK_API FString AssetFolder(const FString& ZoneId, int32 Version);
  GOLMOK_API FString ChunkAssetPath(const FString& ZoneId, int32 Version, const FString& ChunkId);
  GOLMOK_API FString CollisionAssetPath(const FString& ZoneId, int32 Version, const FString& ChunkId /* "" = 단일 */);
}
```
(`UPROPERTY(...)` = `UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Golmok|Zone")`. **UPROPERTY 한 줄에 선언자 하나**: UHT는 `double A, B;`를 거부한다.)
파서: `FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root)` 수동 파싱(`FJsonObjectConverter`는 snake_case·null·enum 문자열 때문에 안 씀). **JSON 접근 규칙**: 키는 항상 `const FString` 객체로 `TryGet*Field`/`HasTypedField<EJson::Null>`에 넘긴다(TCHAR 리터럴 금지 — 5.4+ `FStringView` 오버로드 모호성 회피). 커밋된 `GetObject/GetArray/GetString/GetNumber/GetBool/NumberArray/GetVec3` 헬퍼가 이 규칙이다.
**Error(로드 중단)**: `schema_version==1`; `zone_id` `^z_[a-z0-9]+(_[a-z0-9]+)*$` 64자 이하; `version>=1`; `kind`∈{exterior,interior}; `parent_zone` 키 존재(interior면 non-null); `origin` 3 double; `origin_ecef` 3; `transform` 16 + `RigidityError<=1e-6`·`det=1±1e-6`·마지막 행 [0,0,0,1]; `footprint_wgs84.type=="Polygon"` 링 ≥3점; `replaces`; `layers.visual.format`+`chunks[]`(각 `id`,`uri`, `bbox_enu` 있으면 2×3·min≤max); `layers.collision.format=="glb"`+`uri`; `portals[]`(`id`,`to_zone`≠zone_id,`pose_enu.position`,`yaw_deg`,`radius_m`,`kind`); `priority`; `quality` 객체; `consent.type`∈{public_street,owner_consent}; `attribution`; `sources[]`; 모든 uri `IsSafeRelativeUri`. **Warning(계속)**: `origin`과 `transform` 이동 성분 불일치 >1 mm, 알 수 없는 최상위 키, `Format==Unknown`, `bbox_enu` 없음, `owner_consent`인데 `record_id` 없음. 정본 검증은 `golmok-zone validate`(런타임은 관대).

#### 3-5 `Zones/GolmokZone.h`
```cpp
UENUM(BlueprintType) enum class EGolmokZoneState : uint8 { Unloaded, Loaded, Failed };
UCLASS(Config = Game, HideCategories = (Rendering, Replication, Input, LOD, Cooking, Physics, Networking))
class GOLMOK_API AGolmokZone : public AActor {
  GENERATED_BODY()
public:
  AGolmokZone();   // Root USceneComponent "ZoneRoot", Mobility Movable(BeginPlay 후 이동), 자식은 Stationary, Tick off
  UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Golmok|Zone") FString ZoneId;
  UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Golmok|Zone", meta=(ClampMin="1")) int32 Version = 1;
  UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Golmok|Zone") bool bAutoManaged = true;      // 거리 규칙 대상
  UPROPERTY(Config, EditAnywhere, Category="Golmok|Zone|Streaming") bool bAsyncLoad = false;         // TODO §4-4
  UPROPERTY(Config, EditAnywhere, Category="Golmok|Zone|Debug") bool bDrawMissingAssetBoxes = true;
  UPROPERTY(Config, EditAnywhere, Category="Golmok|Zone|Collision", meta=(ClampMin="1.0")) double BlockerThicknessCm = 10.0;
  UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="Golmok|Zone|State") EGolmokZoneState State = EGolmokZoneState::Unloaded;
  UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="Golmok|Zone|State") FString LastError;
  UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="Golmok|Zone|State") FGolmokZoneManifest Manifest;
  UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="Golmok|Zone|State") FGolmokBlockers Blockers;
  UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="Golmok|Zone|State") int32 MissingAssetCount = 0;

  UFUNCTION(BlueprintCallable, Category="Golmok|Zone") bool Load();      // §4-1. 이미 Loaded면 true
  UFUNCTION(BlueprintCallable, Category="Golmok|Zone") void Unload();    // §4-2
  UFUNCTION(BlueprintCallable, Category="Golmok|Zone") bool IsLoaded() const;
  UFUNCTION(BlueprintCallable, Category="Golmok|Zone") void SetVisualVisible(bool bVisible);     // 청크 + 플레이스홀더 박스
  UFUNCTION(BlueprintCallable, Category="Golmok|Zone") void SetCollisionEnabled(bool bEnabled);  // 충돌 메시 + blocker
  UFUNCTION(CallInEditor, BlueprintCallable, Category="Golmok|Zone") void RebuildInEditor();     // Unload → manifest 강제 재파싱 → Load
  UFUNCTION(CallInEditor, BlueprintCallable, Category="Golmok|Zone") void UnloadInEditor();
  bool EnsureManifest(bool bForceReload = false);   // manifest·blockers 파싱 + 루트 배치 + footprint 캐시 (1단계)
  bool HasManifest() const;  bool IsVisualVisible() const;
  const TArray<FVector2D>& GetFootprintUE();  const FBox2D& GetFootprintBoundsUE();   // 원점 리비전 바뀌면 재계산
  double DistanceToBoundsM(const FVector2D& LevelXYcm);     // FBox2D 거리(안이면 0) — 사전검사용, 폴리곤 거리의 하한
  double DistanceToFootprintM(const FVector2D& LevelXYcm);  // DistanceToPolygon/100, 안이면 0, 미지면 1e9
  bool FootprintContains(const FVector2D& LevelXYcm);       // bounds 사전검사 → PointInPolygon
  bool FootprintOverlaps(AGolmokZone& Other);                // bounds Intersect → PolygonsOverlap
  int32 GetPriority() const;  bool IsInterior() const;  FString GetManifestFilePath() const;
  FTransform GetPortalWorldTransform(const FGolmokZonePortal& P) const;          // (S·position, Yaw=-yaw_deg) × 루트 — WP-05
  static double PortalRadiusCm(const FGolmokZonePortal& P) { return 100.0 * P.RadiusM; }
  virtual void SpawnPortals();  virtual void DestroyPortals();   // WP-05 훅(기본: 개수 Verbose 로그 / PortalActors Destroy)
  UPROPERTY(Transient) TArray<TObjectPtr<AActor>> PortalActors;
protected:
  virtual void BeginPlay() override;      // ZoneSubsystem->RegisterZone(this)
  virtual void EndPlay(const EEndPlayReason::Type) override;   // Unregister → Unload()
#if WITH_EDITOR
  virtual void PostEditChangeProperty(FPropertyChangedEvent&) override;  // ZoneId/Version → Unload(); bManifestLoaded=false
#endif
  virtual int32 BuildVisualLayer();                     // 확장점(D-010 splat 서브클래스가 덮어씀; 플러그인 헤더는 여기 금지). 만든 컴포넌트 수 반환
  virtual int32 BuildCollisionLayer();
  virtual int32 BuildBlockers();
private:
  bool ApplyRootTransform();  bool BuildFootprintCache();  UGolmokZoneSubsystem* GetZoneSubsystem() const;
  UStaticMeshComponent* MakeMeshComponent(const FName& Name, UStaticMesh* Mesh, bool bVisual);
  UBoxComponent* MakeBoxComponent(const FName& Name, const FVector& RelLoc, const FRotator& RelRot, const FVector& Extent, bool bCollide, const FColor& Color);
  void DestroyOwnedComponents();  static UStaticMesh* LoadMeshAsset(const FString& ObjectPath);
  UPROPERTY(VisibleAnywhere, Category="Golmok|Zone") TObjectPtr<USceneComponent> Root;
  UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> ChunkComponents;
  UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> CollisionComponents;
  UPROPERTY(Transient) TArray<TObjectPtr<UBoxComponent>> PlaceholderBoxes;
  UPROPERTY(Transient) TArray<TObjectPtr<UBoxComponent>> BlockerComponents;
  TArray<FVector2D> FootprintUE;  TArray<double> FootprintXs, FootprintYs;  FBox2D FootprintBoundsUE;  int32 FootprintOriginRevision = INDEX_NONE;
  bool bManifestLoaded = false;  bool bVisualVisible = true;  bool bCollisionOn = true;  bool bWarnedAsync = false;
};
```
런타임 컴포넌트: `NewObject<>(this, UniqueComponentName(Name), RF_Transient)`(정확한 이름 `Chunk_<id>`·`Blocker_<id>`; 언로드 시 죽은 컴포넌트는 `TRASH_Golmok_*`로 개명해 이름을 비운다 — `AActor::DestroyConstructedComponents`와 같은 방식. 컴포넌트 태그 = manifest id) → `SetMobility(Stationary)` → `SetupAttachment(Root)` → 설정 → `RegisterComponent()`. 에디터에서도 `AddInstanceComponent` 안 함(레벨에 저장하지 않고 항상 manifest에서 재생성). 이름 `Chunk_<id>`, `Collision`/`Collision_<id>`, `Blocker_<id>`, `Missing_<id>`.

#### 3-6 `Zones/GolmokZoneSubsystem.h`
```cpp
USTRUCT() struct FGolmokZoneRecord { GENERATED_BODY()
  UPROPERTY() TWeakObjectPtr<AGolmokZone> Zone;
  bool bPinned = false;      // golmok.zone.load / 포털: 거리로 언로드 안 함
  bool bBlocked = false;     // golmok.zone.unload: UnloadRadiusM 밖으로 나갈 때까지 거리 자동 로드 금지
  bool bSuppressed = false;  // 겹침 패자
  bool bLoadFailed = false;  // 실패 후 재시도 금지(로그 1회)
  double LastDistanceM = 1.0e9;  bool bDistanceIsLowerBound = false; };   // 사전검사만 했으면 bounds 거리(하한)
USTRUCT() struct FGolmokBasemapEntry { GENERATED_BODY()
  UPROPERTY() TWeakObjectPtr<AActor> Actor;   // 안정 키. 배열 인덱스로 참조 금지
  FVector2D CenterUE = FVector2D::ZeroVector; // 바운드 중심 XY, 캐시 시 1회 계산
  bool bIsTerrain = false;  bool bOriginalHidden = false;  bool bOriginalCollision = true;
  TArray<FName> HiddenBy; };                  // 덮고 있는 zone id 집합. 비면 복원
UCLASS(Config = Game)
class GOLMOK_API UGolmokZoneSubsystem : public UWorldSubsystem {   // ini [/Script/Golmok.GolmokZoneSubsystem]
  GENERATED_BODY()
public:
  virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;   // Game, PIE 만
  virtual void Initialize(FSubsystemCollectionBase&) override;   // 값 검증(Unload>Load, 간격≥0.1), 레벨 델리게이트 바인드
  virtual void Deinitialize() override;                          // 타이머 해제, 델리게이트 해제, RestoreAllBasemap()
  virtual void OnWorldBeginPlay(UWorld& InWorld) override;       // 배치 zone 스윕 등록, 베이스맵 캐시 dirty, 타이머 시작
  UPROPERTY(Config, EditAnywhere, Category="Golmok|Zone") float LoadRadiusM = 150.f;
  UPROPERTY(Config, EditAnywhere, Category="Golmok|Zone") float UnloadRadiusM = 250.f;
  UPROPERTY(Config, EditAnywhere, Category="Golmok|Zone") float UpdateIntervalSeconds = 0.5f;
  UPROPERTY(Config, EditAnywhere, Category="Golmok|Zone") int32 MaxLoadsPerUpdate = 1;
  UPROPERTY(Config, EditAnywhere, Category="Golmok|Zone") int32 MaxUnloadsPerUpdate = 2;
  UPROPERTY(Config, EditAnywhere, Category="Golmok|Zone") bool bAutoManageInterior = false;
  UPROPERTY(Config, EditAnywhere, Category="Golmok|Zone") bool bSuppressLoserCollision = false;   // 옵트인: 패자 충돌도 끔
  UPROPERTY(Config, EditAnywhere, Category="Golmok|Basemap") bool bHideBasemap = true;
  UPROPERTY(Config, EditAnywhere, Category="Golmok|Basemap") FName BasemapTag = TEXT("GolmokBasemap");
  UPROPERTY(Config, EditAnywhere, Category="Golmok|Basemap") FName BasemapTerrainTag = TEXT("GolmokBasemapTerrain");
  UPROPERTY(Config, EditAnywhere, Category="Golmok|Basemap") float BasemapRescanSeconds = 0.f;   // 0 = 이벤트·refresh 때만
  void RegisterZone(AGolmokZone*);  void UnregisterZone(AGolmokZone*);
  bool RequestLoad(const FString& ZoneId, bool bPin, FString& OutMessage);   // WP-05 포털도 호출(bPin=true)
  bool RequestUnload(const FString& ZoneId, FString& OutMessage);            // bPinned=false, bBlocked=true, Unload
  void NotifyZoneLoaded(AGolmokZone*);  void NotifyZoneUnloaded(AGolmokZone*);   // AGolmokZone이 호출 → ResolveOverlaps + UpdateBasemapHiding
  void RefreshBasemap();  void SetRadii(float LoadM, float UnloadM);  void Evaluate();   // 타이머 콜백(§5)
  FString DescribeZones();  AGolmokZone* FindZone(const FString& ZoneId) const;  // 같은 id 여러 버전 → 최고 Version
  int32 NumZones() const;
private:
  bool GetPlayerLocation(FVector& Out) const;   // GetPlayerPawn(World,0) → PlayerCameraManager → false(평가 건너뜀, Warning 1회)
  void PruneInvalid();  FGolmokZoneRecord* FindRecord(const AGolmokZone*);
  void ResolveOverlaps();  void UpdateBasemapHiding();  void RestoreAllBasemap();  void ApplyBasemapEntryState(FGolmokBasemapEntry&, bool bHidden);
  void OnLevelAddedOrRemoved(ULevel*, UWorld*);   // 이 월드면 bBasemapDirty=true
  UPROPERTY(Transient) TArray<FGolmokZoneRecord> Zones;  UPROPERTY(Transient) TArray<FGolmokBasemapEntry> Basemap;
  FTimerHandle EvaluateTimer;  FDelegateHandle LevelAddedHandle, LevelRemovedHandle;
  double LastBasemapScanSeconds = -1.0;  bool bBasemapDirty = true;  bool bWarnedNoPlayer = false;
};
```
콘솔(`.cpp` 익명 namespace의 `FAutoConsoleCommandWithWorldAndArgs` 5개, 출력 `UE_LOG(LogGolmok, Log)`): `golmok.zone.list`(id, version, prio, state, dist m — 하한이면 `>=` 접두, pinned/blocked/visual-off/manual/error), `golmok.zone.load <id>`(pin, bBlocked·bLoadFailed 해제), `golmok.zone.unload <id>`, `golmok.zone.refresh`(베이스맵 재스캔 + 모든 bLoadFailed 해제 + Evaluate), `golmok.zone.radius <load_m> <unload_m>`(SetRadii + Evaluate).

### 4. `AGolmokZone` 로드 흐름
#### 4-1 `Load()`
1. `State==Loaded` → true. `EnsureManifest()` 실패 → `State=Failed`, false.
   - `EnsureManifest`: `ZoneId` 비었거나 `Version<1` → Error. `LoadManifest(ManifestFilePath(ZoneId, Version))`. **`Manifest.ZoneId != ZoneId || Manifest.Version != Version` → Error**(폴더·파일 불일치, 스펙 §3.2; `LastError` 설정). `Layers.Blockers.bPresent`면 `LoadBlockers(FPaths::Combine(FPaths::GetPath(Path), Uri))` — 실패는 Warning + blocker 없이 계속. `Format != NaniteMesh` → Warning "not implemented (D-010)". 그 뒤 `ApplyRootTransform()`·`BuildFootprintCache()`, `bManifestLoaded=true`.
   - `ApplyRootTransform`: `Geo->ZoneLocalToWorld(Manifest.Transform)` → `SetActorTransform(T, false, nullptr, TeleportPhysics)`. Display 로그: zone-local (0,0,0)·(10,0,0) m의 레벨 위치와 Yaw(런북 표 C 대조). 픽스처 기대: root (17670.594, −22197.999, 999.368) cm, Yaw −0.0012°.
2. `bAsyncLoad`면 Warning 1회("not implemented, loading synchronously"). `DestroyOwnedComponents()`(재진입 안전).
3. **`BuildVisualLayer`**(Format==NaniteMesh; 그 외 형식은 플레이스홀더 박스만): 청크마다 `LoadMeshAsset(ChunkAssetPath)`(`StaticLoadObject(UStaticMesh, nullptr, *Path, nullptr, LOAD_NoWarn|LOAD_Quiet)`). 있으면 `MakeMeshComponent("Chunk_<id>", Mesh, true)`: 항등 상대 트랜스폼, `NoCollision`, 오버랩 이벤트 끔, 그림자 켬. 없으면 `MissingAssetCount++`, `bDrawMissingAssetBoxes && bHasBbox`면 `MakeBoxComponent("Missing_<id>", Box.GetCenter(), Zero, Box.GetExtent(), false, Orange)`(`SetHiddenInGame(false)`, `bDrawOnlyIfSelected=false`, NoCollision — 매 프레임 DrawDebugBox 없이 컴포넌트 와이어프레임).
4. **`BuildCollisionLayer`**: `Layers.Collision.Chunks.Num()>0`이면 청크별 `CollisionAssetPath(id, ver, chunk)`, 아니면 단일. `MakeMeshComponent(name, Mesh, false)`: `BlockAll`, `QueryAndPhysics`, `SetHiddenInGame(true)`, `CastShadow=false`, `bAffectDistanceFieldLighting=false`, 내비게이션 영향 켬. 없으면 Warning "player will fall through" + `MissingAssetCount++`.
5. **`BuildBlockers`**: plane마다 `BlockerAxes(n → w,h)`; `N_ue = EnuDirToUE(n̂)`, `H_ue = EnuDirToUE(h)`; 회전 = **`FRotationMatrix::MakeFromXZ(N_ue, H_ue).Rotator()`**(X=법선, Z=높이축. `FMatrix(X=Dn, Y=Dw, Z=Dh)`는 D가 외적 손방향을 뒤집어 det −1이 되므로 쓰지 않는다); 상대 위치 `EnuToUE(center)`; extent `(BlockerThicknessCm/2, 50·size_m[0], 50·size_m[1])`; `BlockAll`+`QueryAndPhysics`, `SetHiddenInGame(true)`, 색 glass=Cyan/no_entry=Red(`show collision`용). 두 kind 모두 물리 벽(glass의 "보임"은 청크 메시 몫). 픽스처 glass_1: 상대 중심 (−1200, −1000, 150), 법선 UE (0,1,0), Yaw 90, extent (5, 150, 125), 레벨 (16470.58, −23197.98, 1149.37).
6. `State=Loaded`, `LastError` 비움, `SetVisualVisible(bVisualVisible)`·`SetCollisionEnabled(bCollisionOn)` 재적용, `SpawnPortals()`(WP-05; 기본 Verbose 로그. 포털 door_1 기대: 상대 (500, −950, 0), Yaw −90, 반경 150 cm, 레벨 (18170.57, −23148.01, 999.32)). Display 로그 "zone <id> v<n> loaded in <ms>: chunks a/b (<k> wire boxes), collision c/d, blockers e, portals f". `Subsystem->NotifyZoneLoaded(this)`.
#### 4-2 `Unload()` / `RebuildInEditor()` / 토글
- `Unload()`: `DestroyPortals()` → 모든 런타임 컴포넌트 `DestroyComponent()`·배열 비움 → `State`가 Failed가 아니면 Unloaded → 로드 상태였으면 로그 + `NotifyZoneUnloaded`. manifest·footprint 캐시는 유지(재로드 시 파일 재파싱 없음).
- `RebuildInEditor()`: `Unload(); State=Unloaded; EnsureManifest(true)` 실패면 Failed, 아니면 `Load()`. `MarkPackageDirty` 안 함(전부 Transient). WP-06 `zone_import.py`: `set_editor_property("zone_id"/"version")` → `zone.rebuild_in_editor()`(BlueprintCallable → Python 노출; 안 되면 `call_method("RebuildInEditor")`).
- `PostEditChangeProperty`: `ZoneId`/`Version` 변경 → `Unload()`, `bManifestLoaded=false`, `FootprintOriginRevision=INDEX_NONE`(다음 Rebuild가 재파싱).
- `SetVisualVisible(b)`: `ChunkComponents`·`PlaceholderBoxes`에 `SetVisibility(b, true)`. `SetCollisionEnabled(b)`: `CollisionComponents`·`BlockerComponents`에 `QueryAndPhysics/NoCollision`. 언로드 상태에서는 플래그만 저장.
#### 4-3 footprint 캐시
`BuildFootprintCache()`: `EcefToArea = Geo->EcefToAreaMatrix(OriginLat, OriginLon, OriginH)`(원점 없으면 zone 원점 폴백 — 루트 폴백과 정합), 링 점마다 `LonLatToLevelUE(EcefToArea, lon, lat, OriginH)` → `FootprintUE/Xs/Ys`, `FootprintBoundsUE`. `FootprintOriginRevision = Geo->GetOriginRevision()`; `GetFootprintUE()`가 리비전 불일치를 보면 루트·캐시 재계산. 픽스처(area 원점 37.5600/126.9230/40) 모서리 UE XY cm: (15670.62, −21197.96) (19670.61, −21198.04) (19670.57, −23198.05) (15670.57, −23197.96); 레벨 원점에서 footprint까지 **263.61 m**(≈264 m) → 기본 반경으로는 자동 로드되지 않는다(런북은 `golmok.zone.radius`로 확인).
#### 4-4 `bAsyncLoad` TODO 본문(주석으로 코드에 남긴다, WP-04 미구현)
`UGolmokZoneSubsystem`이 `FStreamableManager Streamable` 1개를 소유. `AGolmokZone::LoadAsync()`: `EnsureManifest` → 청크·충돌 `FSoftObjectPath` 목록 → `State=Loading`(enum 값 추가) → **`FStreamableDelegate Done = FStreamableDelegate::CreateUObject(this, &AGolmokZone::OnAssetsLoaded);`를 변수로 먼저 만들고** `LoadHandle = Streamable.RequestAsyncLoad(Paths, Done)`(임시 델리게이트를 인자에 직접 쓰면 5.4+ `FStreamableDelegateWithHandle`/업데이트 델리게이트 오버로드와 모호). `TSharedPtr<FStreamableHandle> LoadHandle` 보관; `Unload()`가 `LoadHandle->CancelHandle()` 후 리셋; `OnAssetsLoaded`는 `IsValid(this) && State==Loading`일 때만 §4-1 3~6단계 실행(에셋은 이미 메모리에 있어 `StaticLoadObject`가 즉시 반환).

### 5. `UGolmokZoneSubsystem` 규칙
#### 5-1 등록
`AGolmokZone::BeginPlay → RegisterZone`, `EndPlay → UnregisterZone`. `OnWorldBeginPlay`가 `TActorIterator<AGolmokZone>`로 한 번 스윕(순서 무관). 같은 `ZoneId+Version` 두 액터 → Warning(둘 다 등록, 겹침 규칙은 같은 id를 무조건 겹침으로 본다). Editor 월드에는 서브시스템이 없으므로 액터는 등록을 건너뛴다.
#### 5-2 타이머
`OnWorldBeginPlay`: `InWorld.GetTimerManager().SetTimer(EvaluateTimer, this, &ThisClass::Evaluate, FMath::Max(0.1f, UpdateIntervalSeconds), true)`. 발화 사이 비용 0, 일시정지에 동조. 틱 서브시스템 아님.
#### 5-3 `Evaluate()` — 거리·히스테리시스
1. `PruneInvalid()`; `GetPlayerLocation` 실패 → Warning 1회, return. `P = (X, Y)`.
2. 각 Record(manifest 없으면 `EnsureManifest`, 실패 시 `bLoadFailed=true` 후 건너뜀):
   - `dBox = Zone->DistanceToBoundsM(P)`(`FBox2D` 거리, 안이면 0). dBox ≤ dPoly가 항상 성립.
   - **Loaded**: `dBox >= UnloadRadiusM` → 폴리곤 계산 없이 언로드 후보(`Last=dBox`, 하한 아님·이미 충분). 아니면 `dPoly = DistanceToFootprintM(P)`; `dPoly >= UnloadRadiusM`이면 언로드 후보. `Last=dPoly`.
   - **Unloaded**: `dBox > LoadRadiusM` → 건너뜀(`Last=dBox`, `bDistanceIsLowerBound=true`). 아니면 `dPoly` 계산; `dPoly <= LoadRadiusM`이면 로드 후보. `Last=dPoly`.
   - 거리 규칙 제외: `!bAutoManaged`, interior(`bAutoManageInterior=false`일 때), `bLoadFailed`. `bBlocked`는 `Last >= UnloadRadiusM`이 되는 순간 해제되고, 해제 전에는 로드 후보가 되지 않는다. `bPinned`는 언로드 후보가 되지 않는다.
   - interior가 로드돼 있고 `ParentZone`이 등록된 exterior인데 그 부모가 Unloaded면 → 언로드 후보(포털 없이 부모만 떠난 경우 정리).
3. 로드 후보는 `Last` 오름차순으로 최대 `MaxLoadsPerUpdate`개 `Load()`(실패 → `bLoadFailed=true`, Error 로그 1회); 언로드 후보는 `Last` 내림차순으로 최대 `MaxUnloadsPerUpdate`개 `Unload()`. 나머지는 다음 발화.
4. 상태가 바뀌었거나 `bBasemapDirty`면 `ResolveOverlaps()` + `UpdateBasemapHiding()`(Notify*가 이미 호출했으면 중복 무해). 폴리곤 겹침·point-in-polygon은 **이벤트 때만**; 타이머 경로의 폴리곤 비용은 링 구간(LoadRadius<d<UnloadRadius 부근) zone에만 발생한다.
#### 5-4 겹침·우선순위
로드된 exterior zone 쌍(i<j): 같은 `ZoneId`면 무조건 겹침, 아니면 `FootprintOverlaps`(bounds → `PolygonsOverlap`). 한쪽이 다른 쪽 `ParentZone`이면 건너뜀. 승자: `Priority` 큼 → manifest `Version` 큼 → `ZoneId` 사전순 작음(결정적). 패자 `bSuppressed=true` → `SetVisualVisible(false)`; `bSuppressLoserCollision`이면 `SetCollisionEnabled(false)`도. 승자·비겹침 zone은 `SetVisualVisible(true)`(+충돌 복원). **패자는 베이스맵을 숨기지 않는다**(승자만). 로그는 상태가 바뀐 zone만.
#### 5-5 베이스맵 숨김(D-012 보조)
- 캐시: `bBasemapDirty`일 때만 `TActorIterator<AActor>`로 `ActorHasTag(BasemapTag)` 액터를 훑어 `FGolmokBasemapEntry`(`Actor`, `CenterUE = GetActorBounds(false, O, E)`의 (O.X, O.Y), `bIsTerrain = ActorHasTag(BasemapTerrainTag)`, 원래 hidden/collision) 추가·무효 항목 제거. dirty 트리거: `OnWorldBeginPlay`, `FWorldDelegates::LevelAddedToWorld/LevelRemovedFromWorld`(이 월드일 때), `RegisterZone/UnregisterZone`, `golmok.zone.refresh`, `BasemapRescanSeconds>0`이면 주기.
- 판정: 로드된 **승자** zone마다 `Entry.bIsTerrain && !Zone->Manifest.Replaces.bTerrainClip`이면 건너뛰고, `FootprintContains(CenterUE)`(bounds → `PointInPolygon`)면 `HiddenBy.AddUnique(zone id)`. 집합이 비어 있다가 차면 `SetActorHiddenInGame(true)`+`SetActorEnableCollision(false)`, 차 있다가 비면 원래 값 복원. 두 zone이 같은 액터를 덮어도 언로드 순서와 무관. `Deinitialize`에서 `RestoreAllBasemap()`(PIE 종료 시 에디터 액터 오염 방지). `bHideBasemap=false`면 전부 복원 후 아무것도 안 함.
- 한계: 기준이 바운드 중심 하나라 footprint에 걸친 큰 타일은 남는다. 정본 제거는 빌드 단계 `golmok-zone exclude`(D-012). `replaces.building_ids`는 파싱·보관만.

### 6. 플레이어 위치·기타 규칙
- `GetPlayerLocation`: `UGameplayStatics::GetPlayerPawn(World, 0)` → 없으면 `GetPlayerCameraManager(World,0)->GetCameraLocation()` → 없으면 false.
- 루트 Mobility: Movable(게임 월드에서 BeginPlay 후 `SetActorTransform`을 허용), 자식 Stationary(그림자·Lumen 캐시). Static 자식은 비Static 부모에 붙일 수 없다.
- 로그 카테고리 `LogGolmok`만. 에디터 전용 코드는 `#if WITH_EDITOR`. 모든 외부 포인터 nullptr/IsValid 검사. double↔float 변환은 `static_cast`.

### 7. ini (`Config/DefaultGame.ini`)
```ini
[/Script/UnrealEd.ProjectPackagingSettings]
+DirectoriesToAlwaysStageAsUFS=(Path="Golmok/Zones")

[/Script/Golmok.GolmokZoneSubsystem]
LoadRadiusM=150
UnloadRadiusM=250
UpdateIntervalSeconds=0.5
MaxLoadsPerUpdate=1
MaxUnloadsPerUpdate=2
bAutoManageInterior=False
bSuppressLoserCollision=False
bHideBasemap=True
BasemapTag=GolmokBasemap
BasemapTerrainTag=GolmokBasemapTerrain
BasemapRescanSeconds=0

[/Script/Golmok.GolmokZone]
bAsyncLoad=False
bDrawMissingAssetBoxes=True
BlockerThicknessCm=10
```
`Initialize()`가 `UnloadRadiusM<=LoadRadiusM`이면 Warning 후 `LoadRadiusM+100`, 간격 최소 0.1, `MaxLoadsPerUpdate>=1`, `MaxUnloadsPerUpdate>=1`로 보정한다.

### 8. 순수 수학 헤더 API와 g++ 테스트
`Geo/GolmokGeoMath.h`(namespace `GolmokGeoMath`, include `<array> <cmath> <cstddef>`만, 전부 `inline`·double): `Vec3`, `Mat4`, `WGS84_A/F/E2/B`, `Pi`(UE 매크로 `PI`와 충돌하므로 이 철자), `ENU_TO_UE_SCALE`, `DegToRad/RadToDeg`, `Identity`, `At/Set`, `Multiply`, `ApplyPoint`, `ApplyVector`, `RigidInverse`, `Translation`, `GeodeticToEcef`, `EcefToGeodetic`, `EnuFrame`, `RotZ`, `ZoneTransform`, `ZoneLocalToAreaEnu`, `EnuToUE`, `UEToEnu`, `EnuDirToUE`, `UEActorMatrix`, `RigidityError(M, &det)`, `UEYawDegFromZoneToArea`, `PointInPolygon`, `DistanceToSegment`, `DistanceToPolygon`, `SegmentsIntersect`, `PolygonsOverlap`, `BlockerAxes(n, &w, &h)`. **시그니처·이름 변경 금지**(래핑 구조체나 이름 바꾸기는 커밋된 테스트·드라이버를 전부 깨뜨린다).
`tools/tests/test_ue_geo_math.py`: `shutil.which("g++"/"clang++"/"c++")` 없으면 `pytest.skip`(windows-latest CI). `fixtures/ue/geomath_driver.cpp`를 `-std=c++17 -Wall -Wextra -Werror -pedantic -I Source/Golmok/Geo`로 빌드해 명령(`ecef geodetic enuframe zone apply applyvec inverse toarea actor enu2ue ue2enu rigid yaw pip dist overlap blocker`)별 double 출력을 `golmok_tools.zone.transform`(pyproj 교차검증)·스펙 §4 표와 비교: 헤더 순수성, 표 A(1e-4 m·파이썬과 1e-9), 무작위 20점, ECEF↔측지 왕복(극 포함), ENU 프레임·zone transform(1e-9), 표 B, 표 C(레벨 0.01 cm, 액터 행렬 1e-7, 청크 정점 경유 1e-6), `D R D` det +1·Yaw −30°, 역행렬·강체성, point-in-polygon(열린/닫힌/오목), 폴리곤 거리(shapely 교차), 폴리곤 겹침(분리/포함/십자/접촉/동일), blocker 축(남향 유리 h=+z w=+x; 동향 w=+y; 수평 h=+y w=+x; 기울어진 법선 직교), 픽스처 transform이 origin 재현. 이 테스트가 이미 커밋돼 통과 중이므로 WP-04 C++는 헤더를 **읽기만** 한다.

### 9. Python 테스트·`synthetic_zone.py`
- `test_ue_zone_fixture.py`(확장): Content 픽스처 = WP-02 픽스처 바이트 동일, 스키마·의미 검사, 에셋 이름 규약, 폴더 = id/v<n>, ini — `+DirectoriesToAlwaysStageAsUFS`, `0<LoadRadiusM<UnloadRadiusM`, `UpdateIntervalSeconds>=0.1`, **추가**: `MaxLoadsPerUpdate>=1`, `MaxUnloadsPerUpdate>=1`, `bSuppressLoserCollision`·`bHideBasemap`·`BasemapTag`·`BasemapTerrainTag` 존재, `[/Script/Golmok.GolmokZone] BlockerThicknessCm>0`·`bAsyncLoad=False`(WP-09부터 `True`); Build.cs `Json`/`JsonUtilities`; Geo/Zones 헤더·소스 규약(`#pragma once`, 마지막 include `.generated.h`, `GOLMOK_API`, 모듈 루트 상대 include, `.cpp` 첫 include는 자기 헤더, `LogTemp` 금지); 순수 헤더 검사.
- `test_ue_python_synthetic_zone.py`(있음): 가짜 `unreal` 모듈로 `boxes_glb`(Y-up, CCW), `synthetic_geometry`(문 구멍 = glass_1 위치), `pretransform_box`(임포터 매핑 48종 상쇄), `expected_ue_bounds` = chunk_00 UE bbox (−2000,−1000,0)~(−700,1000,1200).
- `synthetic_zone.run(geo_origin="area", move_player_start=True, import_assets=True)`: 기본 경로 = 프로브 GLB로 임포터 축·스케일 측정(`basemap_import`와 같은 방식) → 미리 변환한 GLB 4개 임포트(파사드 벽 3청크 + 문 구멍, 충돌 슬래브+벽) → `AGolmokGeoOrigin` FindOrSpawn(37.5600, 126.9230, 40) → `AGolmokZone` FindOrSpawn(라벨 `Zone_z_synthetic_001`, 폴더 `Golmok/Zones`) → `rebuild_in_editor()` → 태그 `GolmokBasemap` 큐브 2개(`BM_dummy_inside` zone 위 5 m, `BM_dummy_outside` 동쪽 60 m) → PlayerStart를 슬래브 위(원점 남쪽 5 m)로. `geo_origin="zone"`은 zone을 레벨 원점에 놓는 개발 모드(런북 표 C 대조는 `"area"`에서만 성립).

### 10. 런북 `docs/runbooks/pc-verify-wp04.md` 골자
빌드 → `z.run()` → 에디터: 4 에셋, `GeoOrigin`(0,0,0 / 37.56 / 126.923 / 40), `Zone_z_synthetic_001` State=Loaded, 로그 root (17670.59, −22198.00, 999.37) / Yaw −0.0012, (10,0,0) m → (18670.59, −22198.02, 999.34), chunk_01 중심 (17670.61, −22198.02, 1599.37), `Blocker_glass_1` 상대 (−1200, −1000, 150) extent (5,150,125) → PIE: `golmok.geo.selftest` PASS(항목 6) → `golmok.zone.list` dist 0.0 loaded → (1) 벽 3조각 (2) 슬래브 보행 (3) x=−12 m 문 구멍에서 유리 blocker에 막힘 (5) `BM_dummy_inside`만 숨김(`hidden +1`) (4) `golmok.zone.radius 20 40` 후 남쪽 40 m → `unloaded`·`restored 1`, 복귀 → `loaded`; `golmok.zone.unload`(blocked, 안에 있어도 재로드 안 됨) → `golmok.zone.load`(pinned, 멀어져도 유지) → `golmok.zone.radius 150 250` 복구 → 시작 위치에서 dist ≈ 263.6 m 확인 → PIE 종료 시 큐브 복원 → §4 원점 없음(GeoOrigin 삭제 + Rebuild → 레벨 원점) → §5 패키징(`golmok.zone.list`에 loaded = UFS 스테이징 OK). 컴파일 에러 표는 §11.

### 11. 불확실한 UE 5.8 API와 대안 (런북 "컴파일 에러가 나면" 표 그대로)
| # | 파일 | API | 불확실한 점 | 대안 |
|---|---|---|---|---|
| 1 | GolmokZoneManifest | `FJsonObject::TryGet{Number,String,Array,Object,Bool}Field(key, …)`, `HasTypedField<EJson::Null>(key)` | 5.4+ `FStringView` 오버로드 → 리터럴 키 모호 | **키를 `const FString` 객체로 넘긴다**(이미 그렇게 함). 그래도 실패하면 `GetField<EJson::…>(FString)` |
| 2 | GolmokZoneSubsystem | `UWorldSubsystem::DoesSupportWorldType(const EWorldType::Type) const` | 시그니처 유지 여부 | 오버라이드 삭제, `ShouldCreateSubsystem(UObject* Outer)`에서 `Cast<UWorld>(Outer)->WorldType` 검사 |
| 3 | GolmokZoneSubsystem | `OnWorldBeginPlay(UWorld&)` | 액터 BeginPlay와의 순서 | 설계가 순서 무관(등록+스윕). 시그니처 오류면 첫 `RegisterZone`에서 타이머 시작 |
| 4 | GolmokZoneSubsystem | `FWorldDelegates::LevelAddedToWorld / LevelRemovedFromWorld` (`AddUObject`, `(ULevel*, UWorld*)`) | 시그니처·존재 | 바인드 삭제하고 `BasemapRescanSeconds=10`으로 주기 재스캔 |
| 5 | GolmokZoneSubsystem | `FTimerManager::SetTimer(Handle, this, &Class::Method, float, bool)` | 안정 | `FTimerDelegate::CreateUObject` 오버로드 |
| 6 | GolmokZoneSubsystem | `AActor::GetActorBounds(bool, FVector&, FVector&)` | 4번째 인자 기본값 | `GetComponentsBoundingBox(true).GetCenter()` |
| 7 | GolmokZoneSubsystem | `UGameplayStatics::GetPlayerPawn / GetPlayerCameraManager(World, 0)` | 안정 | `World->GetFirstPlayerController()->GetPawn()` (0.5 s에 1회) |
| 8 | GolmokZone | `FRotationMatrix::MakeFromXZ(X, Z)` | 안정 | `FMatrix(FPlane(X,0), FPlane(Z^X,0), FPlane(Z,0), FPlane(0,0,0,1)).Rotator()` (Y = Z×X를 UE 공간에서 계산) |
| 9 | GolmokZone | `StaticLoadObject(UStaticMesh::StaticClass(), nullptr, *Path, nullptr, LOAD_NoWarn\|LOAD_Quiet)` | 플래그 이름 | `LoadObject<UStaticMesh>(nullptr, *Path)` 또는 `FSoftObjectPath(*Path).TryLoad()` |
| 10 | GolmokZone | `UBoxComponent` 인게임 와이어: `SetHiddenInGame(false)`, `bDrawOnlyIfSelected=false`, `ShapeColor`, `SetLineThickness` | 멤버 접근·렌더 여부 | 컴파일 오류면 줄 삭제; 안 보이면 `#if !UE_BUILD_SHIPPING` `DrawDebugBox`(0.5 s 타이머, 수명 0.6 s) |
| 12 | GolmokZone | `UCollisionProfile::BlockAll_ProfileName / NoCollision_ProfileName` | 안정 | `SetCollisionProfileName(TEXT("BlockAll"))` |
| 13 | GolmokZone | `SetupAttachment(Root)` → `RegisterComponent()` (런타임 NewObject) | 경고 가능 | `RegisterComponent()` 후 `AttachToComponent(Root, KeepRelativeTransform)` |
| 14 | GolmokZone | 루트 Movable + 자식 Stationary | "Mobility … has to be Movable" 로그 | 자식도 Movable(VSM 캐시 비용↑) |
| 15 | GolmokZone | `StaticFindObjectFast(nullptr, this, Name)`, `UObject::Rename(*Name, this, REN_DontCreateRedirectors \| REN_DoNotDirty \| REN_NonTransactional \| REN_ForceNoResetLoaders)`(죽은 컴포넌트 TRASH 개명) | 플래그 이름 | Rename 줄 삭제(이름이 `__<n>` 접미사를 얻을 뿐 동작 동일) |
| 16 | GolmokZone | `UFUNCTION(CallInEditor, BlueprintCallable)` 조합 | 허용 | `BlueprintCallable` 제거, Python은 `call_method("RebuildInEditor")` |
| 17 | GolmokZone | `bAffectDistanceFieldLighting` 직접 대입 | public UPROPERTY | 줄 삭제 |
| 18 | GolmokGeo | `FMatrix::ToQuat()` | 안정 | `FQuat(Rot)` 또는 `Rot.Rotator().Quaternion()` |
| 19 | 전체 | `UPROPERTY` `double`, `TArray<double>`, `FVector2D`, enum class : uint8, `TWeakObjectPtr` in USTRUCT | UE5 리플렉션 가능 | 문제 시 `TArray<double>`→`FVector`×4+`FVector`; enum→`FString` |
| 20 | GolmokGeoOrigin | `UCLASS(HideCategories=(…))` 이름 | 없는 이름은 무시 | 목록 축소 |
| 21 | (TODO) | `FStreamableManager::RequestAsyncLoad(TArray<FSoftObjectPath>, FStreamableDelegate)` | 5.4+ 오버로드 모호 | 델리게이트를 변수로 먼저 만들어 넘김(§4-4). WP-04에서는 주석만 |
| 22 | synthetic_zone.py | `unreal.GolmokGeoOrigin/GolmokZone`, `set_editor_property("zone_id")`, `zone.rebuild_in_editor()` | Python 이름 노출 | `dir(zone)`으로 이름 확인, `call_method` |
| 23 | 패키징 | `FFileHelper::LoadFileToString`로 pak 안 UFS 파일 읽기 | 경로 유지 여부 | `+DirectoriesToAlwaysStageAsNonUFS`(느슨한 파일)로 전환 |

### 12. 커밋 `10208b6` 대비 변경 목록 (설계 확정 후 같은 세션이 반영함 — 적용 결과는 "결과" 절)
1. `GolmokZoneManifest.h/.cpp`: `FGolmokZoneLayers`를 §3-4처럼 중첩 구조(`Visual/Collision/Blockers/Navmesh`)로 바꾸고 `Replaces`, `Quality`, `Consent`, `Attribution`, `Sources`, `Textures` 파싱 추가; `Kind`/`Format`/blocker `Kind`를 enum으로(`FormatString` 원문 보존); `IsSafeRelativeUri`, zone_id 정규식, `parent_zone`·`consent.type` 검사, origin 1 mm Warning, 미지 최상위 키 Warning. 참조 갱신: `Layers.VisualChunks→Layers.Visual.Chunks`, `Layers.CollisionChunks→Layers.Collision.Chunks`, `Layers.BlockersUri→Layers.Blockers.Uri`, `bTerrainClip→Replaces.bTerrainClip`, `Plane.Kind==TEXT("glass")→EGolmokBlockerKind::Glass`.
2. `GolmokZone`: manifest `zone_id/version` 불일치를 Warning → **Error**; `MissingAssetCount`; `DistanceToBoundsM`; `GetPortalWorldTransform/PortalRadiusCm`; `PostEditChangeProperty`에 `Unload()` 추가; `BuildVisualLayer/BuildCollisionLayer/BuildBlockers` 가상 함수로 분리; §4-4 TODO 주석.
3. `GolmokZoneSubsystem`: `Evaluate`에 bbox 사전검사·`bDistanceIsLowerBound`·`MaxUnloadsPerUpdate`(내림차순)·interior 부모 언로드 정리; `bSuppressLoserCollision`; `FWorldDelegates::LevelAddedToWorld/LevelRemovedFromWorld` 바인드(Initialize)·해제(Deinitialize); `BasemapRescanSeconds` 기본 0; `golmok.zone.refresh`가 `bLoadFailed` 전부 해제; `list` 출력에 `>=` 하한 표시; `FindZone`은 같은 id 중 최고 Version.
4. `DefaultGame.ini`: §7 키 추가. `test_ue_zone_fixture.py`: §9 검사 추가.
5. 런북: §10 순서·수치(263.6 m)·§11 표(JSON 키 규칙을 맨 위로). (`synthetic_zone.py`의 큐브 경로는 채택하지 않음, §0 참조.)

### 13. 위험·트레이드오프
1. **동기 로드 히치**: 대형 Nanite 청크의 `StaticLoadObject`는 수십~수백 ms. 완화 `MaxLoadsPerUpdate=1`·거리 오름차순; 근본 해결은 `bAsyncLoad`(§4-4, WP-05+).
2. **바운드 중심 기준 숨김**: footprint 경계에 걸친 큰 지형·건물 타일은 남거나(중심 밖) 통째로 사라진다(중심 안). D-012대로 빌드 단계 `exclude`가 정본, 런타임은 보조.
3. **패자 시각만 끄기**: 겹치는 두 충돌 메시가 캐릭터를 튕길 수 있다. MVP 겹침은 0.5~1 m 띠뿐이고 승자 충돌이 덮는다고 가정; 문제가 보이면 `bSuppressLoserCollision=True`(비겹침 부분 바닥이 사라지는 반대 위험).
4. **원점 없음 폴백**: zone 자신의 원점을 area 원점으로 쓰므로 여러 zone이 모두 레벨 원점에 겹쳐 놓인다 — 개발 레벨 전용, Warning 1회.
5. **footprint 높이 근사**: 링 점 높이에 zone 원점 타원체고를 쓴다. XY 오차 <1 mm.
6. **루트 Movable**: 게임 월드에서 BeginPlay 후 이동을 허용하는 대가로 그림자 캐시가 Stationary 규칙을 따른다. 관측 비용이 크면 WP-06이 에디터에서 위치를 확정하고 루트를 Static으로 되돌린다(§11 #14).
7. **manifest 폴더·파일 불일치를 Error로**: 복사 실수를 즉시 드러내지만 스파이크에서 임의 경로를 쓸 수 없다. 개발 시에는 폴더 이름을 맞추는 것이 규약(스펙 §2)이므로 override 경로는 두지 않는다.
8. **레벨 델리게이트 의존**: 스트리밍 서브레벨의 베이스맵 액터 캐시는 `LevelAdded/Removed`에 의존한다. 컴파일·동작 문제면 `BasemapRescanSeconds=10`으로 대체(§11 #4).
9. **Transient 컴포넌트**: 레벨에는 `AGolmokZone` 액터만 저장되므로 에셋 없이도 레벨이 열리고 WP-06 재임포트가 액터를 다시 만들 필요가 없다. 대신 에디터에서 레벨을 열면 zone이 비어 있고 `RebuildInEditor`를 눌러야 보인다(자동 리빌드는 로드 순서 위험 때문에 제외).
10. **quality 추가 키**: 문자열(`ExtraJson`) 보존만, 구조화하지 않는다.

## 결과
세션: session_01GGmw3pPHLp4Wk5Us9243AL (Fable 5.1 ultracode; 검증 단계 회의론자는 사용자 지시로 Opus) · 2026-09-24 · 상태 **🟡 코드 완료·PC 검증 대기** (G2 `runbooks/pc-verify-wp04.md`, V-03)

**진행 방식(ultracode)** — ① 설계 패널: 안정성·성능·스펙 충실 3안(Fable) → 심판 채점(스펙안 34/40 승, 결함 목록) → 종합 → 위 "설계 (확정)" 절. ② 구현(Geo → Zones, 공용 헤더 `GolmokGeoMath.h` 먼저 확정·g++ 테스트로 고정). ③ 적대적 리뷰: UE 5.8 API / 리플렉션·빌드 / 수학·규약 / 스펙·런북 4관점(Fable) → 원시 소견 20건 → 소견마다 회의론자 2명(Opus, 엔진 사실 관점 + 코드 맥락 관점)이 반박 시도 → **확정 6·반박 14**(반박 14 중 12는 1차 수정 커밋 뒤 "이미 고쳐짐", 실질 반박은 A6·D5 2건). 확정 6건은 모두 반영: A1 컴포넌트 이름 훼손(`MakeUniqueObjectName`이 `glass_1`→`glass_2`; 정확한 이름 + 죽은 컴포넌트 TRASH 개명 + 컴포넌트 태그), A2 런타임 컴포넌트가 디테일 패널에 안 보임(배열 `VisibleAnywhere` + 배치 로그 추가), A3 런북 로그 문자열(`blockers 1/1`), A4 언로드 테스트 거리(원점 기준 −50 m), A5 설계 시그니처 불일치(설계 문구를 코드에 맞춤: `FTransform GetPortalWorldTransform(...) const`, `int32 Build*()`), D7 결과·STATUS(이 절). 세션 자체 점검으로 잡은 것: UE `PI` 매크로 충돌(`Pi`로 개명), Static 루트는 게임 월드에서 이동 불가(루트 Movable·자식 Stationary), `FTimerHandle` include, 원점 없는 레벨의 `LonLatToLevelUE` 폴백 오류(false 반환으로 변경), blocker 축 임계값을 Python 기준(`|h|<1e-6`)에 맞춤, exterior 쌍만 겹침 판정, L_Dev 바닥이 zone까지 안 닿음(`Zone_Ground` 평면).

**한 것** (`unreal/Golmok/`)
- `Source/Golmok/Geo/GolmokGeoMath.h` — 순수 double 수학(UE 비의존). `tools/tests/test_ue_geo_math.py`가 g++로 컴파일해 `golmok_tools.zone.transform`·스펙 §4 표 A/B/C·shapely와 교차검증(1e-6 m, 13 테스트).
- `Geo/GolmokGeo`(FMatrix/FTransform 래퍼, `RunSpecSelfTest`), `Geo/GolmokGeoOrigin`(기본값 = 스펙 area 원점), `Geo/GolmokGeoSubsystem`(`ZoneLocalToWorld` = S·M·S⁻¹, 원점 없으면 zone 원점 폴백 + 경고 1회, 콘솔 `golmok.geo.selftest`).
- `Zones/GolmokZoneManifest`(스펙 §3 1:1 USTRUCT·enum, `FJsonSerializer` 수동 파서: 필수 필드·rigid·uri·zone_id·consent 검사, 경로 함수), `Zones/GolmokZone`(Load/Unload, 청크·충돌·blocker 트랜지언트 컴포넌트, 에셋 없으면 와이어 박스, footprint 캐시, `RebuildInEditor`, WP-05 훅), `Zones/GolmokZoneSubsystem`(FTimerManager 0.5 s, bbox 사전검사 → footprint 거리 히스테리시스, priority→version 겹침, 태그 베이스맵 숨김·복원, 콘솔 `golmok.zone.list/load/unload/refresh/radius`).
- `Golmok.Build.cs`(Json, JsonUtilities), `Config/DefaultGame.ini`(UFS 스테이징, `[/Script/Golmok.GolmokZoneSubsystem]` 11키, `[/Script/Golmok.GolmokZone]` 3키), `Content/Golmok/Zones/z_synthetic_001/v1/`(WP-02 픽스처 사본), `Content/Python/golmok/synthetic_zone.py`(GLB 2-pass 임포트로 파사드 벽 3청크(문 구멍 = glass_1) + 충돌 슬래브, GeoOrigin/Zone FindOrSpawn, 더미 베이스맵 큐브 2개, 지면, PlayerStart 이동), `basemap_import.py`에 `GolmokBasemap`/`GolmokBasemapTerrain`/`tile:<id>` 태그 한 줄(WP-06 항목 5를 앞당김).
- 테스트: `test_ue_geo_math.py`(13), `test_ue_zone_fixture.py`(22: 픽스처 동일성·스키마·에셋 이름·ini 키 = UPROPERTY(Config)·Build.cs·헤더/소스 규약·순수 헤더), `test_ue_python_synthetic_zone.py`(3, 가짜 `unreal`). 런북 `docs/runbooks/pc-verify-wp04.md`.

**코드 리뷰 체크리스트**
- (a) UPROPERTY 타입: `double`, `TArray<double>`, `FVector`(=FVector3d), `FVector2D`, `FString`, `int32`, `bool`, `TArray<USTRUCT>`, `TObjectPtr`, `TWeakObjectPtr`(USTRUCT 안), `UENUM(enum class : uint8)` 3종 — 모두 리플렉션 가능. 한 UPROPERTY에 선언자 하나. 리뷰어(b)·회의론자 확인.
- (b) double↔float: 설정값 `LoadRadiusM` 등은 float(UPROPERTY Config), 비교는 double 거리와 암시 승격(float→double, 손실 없음). `BlockerThicknessCm`은 double. Mat4 ↔ FMatrix/FVector은 double 그대로(UE5 LWC). `int32` ← JSON double은 `static_cast<int32>`. Python 진입점(`FCString::Atof`)만 float.
- (c) `#if WITH_EDITOR`: `AGolmokGeoOrigin::PostEditChangeProperty`, `AGolmokZone::PostEditChangeProperty`. `RebuildInEditor`는 `CallInEditor` UFUNCTION이라 모든 빌드에 존재(본문은 런타임 코드만 사용).
- (d) 로그 카테고리: Geo/Zones 모두 `LogGolmok`(테스트가 `LogTemp` 금지 확인).
- (e) nullptr/IsValid: `GetWorld()`·서브시스템·`NewObject` 결과·`TWeakObjectPtr::Get()`·`IsValid(Component)`·JSON 포인터(`Found && Found->IsValid()`)·`TArray` 인덱스 접근 전 `Num()` 검사.
- (f) Tick 비용: Tick 없음. `FTimerManager` 0.5 s(`UpdateIntervalSeconds`, 최소 0.1). 폴리곤 거리는 bbox 사전검사를 통과한 zone만, point-in-polygon·폴리곤 겹침은 로드/언로드 이벤트 때만, 베이스맵 액터 스캔은 BeginPlay·서브레벨 변경·콘솔·(선택) 주기 때만.

**테스트 로그(클라우드)**: `ruff check .` All checks passed · `ruff format --check .` 68 files already formatted · `pytest -q` **218 passed, 2 skipped, 189 warnings in 12.06s** · `check_repo.py` OK. CI(GitHub Actions `ci.yml`): 첫 push(90a0d69) success(ubuntu 3.11/3.12, windows 3.12, repo-check, tiles-validate); 최종 커밋 결과는 PR #7 체크 참조.

**불확실 API**: 공식 문서 사이트는 이 컨테이너에서 열리지 않았다(API 페이지는 스크립트 렌더링으로 본문 없음, 레거시 미러 403). 확신 없는 호출 24건과 대안을 런북 §6 표(0~24)와 설계 §11에 적었다. 리뷰어(a)·(b)는 엔진 헤더 기억으로 시그니처를 확인했고 이의는 위 확정 목록뿐이었다.

**판단한 것(스펙과 다른 점, 되돌리기 쉬움)**
- `ZoneLocalToWorld`는 `FMatrix44d` 대신 manifest 그대로의 `TArray<double>`(row-major)과 `GolmokGeoMath::Mat4`를 받는다(UE FMatrix는 행벡터 규약이라 혼동 방지).
- 루트 Movable + 자식 Stationary(게임 월드에서 BeginPlay 후 이동 허용). 겹침 패자는 시각만 끔(옵션 `bSuppressLoserCollision`), 베이스맵은 승자만 숨김. 큐브 픽스처 경로(`bDevFitChunkToBBox`)는 넣지 않음. manifest 폴더/파일 불일치는 Error.
- `basemap_import.py` 태그 추가는 WP-06 범위였지만 한 줄이라 여기서 했다(PC에서 베이스맵을 다시 임포트하기 전까지 기존 레벨 액터에는 태그가 없음 — 런북 §3 (5)는 더미 큐브로 검증).

**통합 리뷰(오케스트레이터 세션, main 병합 후, Opus 읽기 전용) 2026-09-24** — 컴파일 차단 결함 없음(모듈 의존·로그 카테고리·헤더 규약·픽스처·ini 키·Python 구문·g++/clang 컴파일 확인). 반영: ① `synthetic_zone.run()`이 기본으로 전용 맵 `L_ZoneTest`를 만들어 쓴다(런북 §2가 L_Dev의 PlayerStart를 옮겨 main의 `Golmok.Player.Movement` 테스트를 깨뜨리던 문제; `level=None`이면 현재 레벨). ② 충돌 메시 임포트 후 Nanite 끔(`bm._set_nanite(mesh, False)`, 메인 PR #9의 발견: Nanite 메시의 복합 충돌은 단순화 폴백 메시라 틈이 생김). ③ 변수 `UE`→`UEPos`(엔진 `UE` 네임스페이스 가림 방지). 기록만: `Golmok.Build.cs`의 `JsonUtilities`는 현재 미사용(무해), `UGolmokZoneSubsystem::Evaluate()`가 `Zones` 배열 원소 포인터를 `Load()` 호출 사이에 유지함 — **WP-05 주의**: `Load()` 경로에서 `RegisterZone`(배열 재할당)이 일어나지 않게 하거나 인덱스/약참조로 바꿀 것.

**PC 검증(V-03, 2026-09-25, PC 세션 Fable 5.1)** — 🟢 통과. 빌드 무수정(경고 1건 `REN_ForceNoResetLoaders` 제거 `e446504`), `z.run()`은 Python 수정 2건 뒤 기대 로그 전부 일치(`12e6bad` UE 5.8 Interchange 폴더 배치 → 규약 경로로 이동, `dd2c538` 빈 맵 조명 재생성), PIE 체크 (1)~(6)·§4 전부 통과(런북 §7 표·스크린샷 4장). 무인 세션이라 에디터 Python PIE 드라이버로 실행. **WP-06 주의**: `zone_import.py`도 Interchange 결과를 `SM_<chunk>` 규약 경로로 옮겨야 한다(`synthetic_zone._move_asset` 재사용).

**남은 것**
- PC 검증 V-03(런북 §1~§5). 컴파일 에러는 런북 §6 표로 고치고 `WP-04: PC fix` 커밋.
- Zone Index(`index/cells`)에서 zone을 발견해 스폰하는 경로(ARCHITECTURE §4-1)는 미구현 — 현재는 레벨에 배치된 `AGolmokZone`만 관리. 실 Zone이 2개 이상 생기면(V-06) 추가.
- `bAsyncLoad`(FStreamableManager, 설계 §4-4 TODO), splat 시각 형식(D-010 뒤), `replaces.building_ids` 단위 숨김(태그 `tile:<id>`만 준비).

**WP-05·06에 알릴 것**
- WP-05: `AGolmokZone::SpawnPortals()/DestroyPortals()`(virtual, `PortalActors` 배열), `Manifest.Portals`, `GetPortalWorldTransform(portal)`(S·position, Yaw −yaw_deg, × 루트), `PortalRadiusCm`. 실내 zone 로드는 `UGolmokZoneSubsystem::RequestLoad(id, bPin)`/`RequestUnload`(interior는 거리 자동 관리 제외, 부모가 언로드되면 정리됨). HUD용 `UGolmokGeoSubsystem::LevelUEToLonLat`. `AGolmokZone::SetVisualVisible/SetCollisionEnabled`는 스파이크 레이어 토글.
- WP-06: `zone_import.py`는 `synthetic_zone.py`의 `find_or_spawn_geo_origin`·`find_or_spawn_zone`·`pretransform_box`(임포터 매핑 상쇄)를 재사용하면 된다. Python 이름: `zone_id`, `version`, `rebuild_in_editor()`, `load()`, `unload()`. 청크 정점은 임포트 후 UE cm(zone-local)이어야 하며 액터 변환은 C++가 manifest에서 계산한다(Python은 배치하지 않음). GeoOrigin 값은 베이스맵 manifest `origin`(타원체고 주의, 스펙 §1).

