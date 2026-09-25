# PC 검증 런북 — WP-04 UE C++ 런타임 1: Geo·Zone (V-03 일부)

대상: PC Claude 세션(또는 사용자). 전제: `runbooks/pc-setup.md` §0~4 완료(UE 5.8.3, 프로젝트 빌드 가능, `L_Dev` 있음).
소요: 빌드 10~20분 + 검증 20분. 결과는 이 문서 하단 "결과 기록"과 `docs/plan/STATUS.md`(V-03 행, WP-04 행 🟢)에 적는다.

클라우드 세션은 UE를 컴파일할 수 없었다. **컴파일 에러가 나면 §6의 표를 보고 고친 뒤 커밋**한다(`WP-04: PC fix …`). 설계 의도를 바꾸는 수정이면 `docs/plan/WP-04-ue-geo-zone.md` "결과"에 한 줄 적는다.

## 0. 대상 파일
| 파일 | 내용 |
|---|---|
| `Source/Golmok/Geo/GolmokGeoMath.h` | 순수 수학(UE 비의존, 클라우드 CI가 g++로 검증함) |
| `Source/Golmok/Geo/GolmokGeo.{h,cpp}` | FMatrix/FTransform 래퍼, `golmok.geo.selftest` |
| `Source/Golmok/Geo/GolmokGeoOrigin.{h,cpp}` | 레벨 원점 액터 `AGolmokGeoOrigin` |
| `Source/Golmok/Geo/GolmokGeoSubsystem.{h,cpp}` | `UGolmokGeoSubsystem`(zone-local → 레벨 UE) |
| `Source/Golmok/Zones/GolmokZoneManifest.{h,cpp}` | manifest·blockers JSON 파서 |
| `Source/Golmok/Zones/GolmokZone.{h,cpp}` | `AGolmokZone` 액터 |
| `Source/Golmok/Zones/GolmokZoneSubsystem.{h,cpp}` | 거리 로드/언로드, 우선순위, 베이스맵 숨김, 콘솔 |
| `Content/Python/golmok/synthetic_zone.py` | 합성 Zone 에셋·액터 생성 |
| `Content/Golmok/Zones/z_synthetic_001/v1/{manifest,blockers}.json` | 픽스처 |
| `Config/DefaultGame.ini` | `[/Script/Golmok.GolmokZoneSubsystem]`, UFS 스테이징 |

## 1. 빌드
```powershell
git pull
.\tools\ue\build.ps1          # Development Editor
```
- [ ] 컴파일 성공(경고는 기록). 실패 시 §6.
- [ ] 에디터 실행 `.\tools\ue\open-editor.ps1`, Output Log에 `LogGolmok` 카테고리가 보임.

## 2. 합성 Zone 생성 (에디터 Python)
어느 레벨이 열려 있든 상관없다. `z.run()`은 **전용 맵 `/Game/Golmok/Maps/L_ZoneTest`**를 만들거나(없으면 L_Dev와 같은 조명으로 생성) 열어 그 안에 구성하므로 `L_Dev`는 건드리지 않는다 — main의 자동 테스트 `Golmok.Player.Movement`(`tools/ue/test.ps1`)가 L_Dev의 PlayerStart 위치를 전제하기 때문이다(통합 리뷰 지적). 현재 레벨에 만들려면 `z.run(level=None)`. Output Log → Python:
```python
import golmok.synthetic_zone as z; z.run()
```
기대 로그(값은 소수 둘째 자리까지 일치해야 함):
```
synthetic_zone: importer mapping scale=... M=... (fit error 0.00)
synthetic_zone: /Game/Golmok/Zones/z_synthetic_001/v1/SM_chunk_00.SM_chunk_00 bounds ok (error 0.xx cm)   × 4 (chunk_00..02, collision)
LogGolmok: Zone z_synthetic_001 v1 root: zone-local (0,0,0) -> UE (17670.59, -22198.00, 999.37) cm; (10,0,0) m -> (18670.59, -22198.02, 999.34) cm; yaw -0.0012 deg
LogGolmok: Zone z_synthetic_001 v1: chunk chunk_01 bbox center -> level (17670.61, -22198.02, 1599.37) cm   (chunk_00/02도 한 줄씩)
LogGolmok: Zone z_synthetic_001: blocker glass_1 (glass) rel (-1200, -1000, 150) cm yaw 90.0 extent (5, 150, 125) -> level (16470.58, -23197.98, 1149.37)
LogGolmok: Zone z_synthetic_001 v1 loaded in x ms: chunks 3/3 (0 wire boxes), collision 1/1, blockers 1/1, portals 1 (WP-05)
synthetic_zone: zone root at ... yaw -0.0012
synthetic_zone: PlayerStart moved to ...
```
- [ ] 콘텐츠 브라우저 `/Game/Golmok/Zones/z_synthetic_001/v1/`에 `SM_chunk_00`, `SM_chunk_01`, `SM_chunk_02`, `SM_z_synthetic_001_collision` 4개.
- [ ] 아웃라이너 `Golmok/GeoOrigin`(위치 0,0,0, Latitude 37.56, Longitude 126.923, HeightEllipsoidal 40), `Golmok/Zones/Zone_z_synthetic_001`, `Golmok/Zone_Ground`(400 m 지면, 슬래브보다 20 cm 아래), `Golmok/BasemapDummy/BM_dummy_inside`·`BM_dummy_outside`.
- [ ] 뷰포트: 레벨 원점에서 동쪽 176.7 m·남쪽 222 m·위 10 m에 파사드 벽 3조각(각 13~14 m 폭, 12 m 높이, 두께 0.2 m)이 동서로 이어져 있고, 서쪽 조각(chunk_00)에 문 크기 구멍(폭 3 m, 높이 2.5 m)이 있다. 벽 남쪽에 44×24 m 충돌 슬래브(회색, 에디터에서는 보임).
- [ ] `Zone_z_synthetic_001` 디테일: State = Loaded, LastError 비어 있음, MissingAssetCount 0, Manifest.Priority 10, Manifest.Portals 1개(door_1), ChunkComponents 3(`Chunk_chunk_00..02`), CollisionComponents 1(`Collision`), BlockerComponents 1(`Blocker_glass_1`, 컴포넌트 태그 `glass_1`).

수치 대조(스펙 `docs/spec/zone-manifest.md` §4 표 C, 원점 37.5600/126.9230/40). 런타임 생성 컴포넌트는 디테일 패널에 나오지 않으므로 **위 로그 줄**과 비교한다:
| 항목 | 기대값(레벨 UE cm) | 어디서 |
|---|---|---|
| zone root 위치 / Yaw | (17670.59, −22198.00, 999.37) / −0.0012° | `root:` 로그, 액터 디테일 Transform |
| zone-local (10,0,0) m | (18670.59, −22198.02, 999.34) | `root:` 로그 |
| chunk_01 bbox 중심 | (17670.61, −22198.02, 1599.37) | `chunk chunk_01 bbox center` 로그 |
| blocker glass_1 | 상대 (−1200, −1000, 150), yaw 90, extent (5, 150, 125), 레벨 (16470.58, −23197.98, 1149.37) | `blocker glass_1` 로그 |
| 포털 door_1(WP-05) | 상대 (500, −950, 0), Yaw −90, 반경 150 cm | `AGolmokZone::GetPortalWorldTransform` (WP-05에서 로그) |

## 3. PIE 체크리스트
PIE 시작(PlayerStart가 슬래브 위, zone 원점에서 남쪽 5 m). 콘솔(`)에서:
```
golmok.geo.selftest
golmok.zone.list
```
- [ ] **(6) 수치 예제**: `golmok.geo.selftest … PASS`, 6줄 모두 `OK` (표 B·C, Yaw −30).
- [ ] `golmok.zone.list`: `z_synthetic_001  v1  prio 10  loaded  dist 0.0 m` (플레이어가 footprint 안). 참고: `L_ZoneTest`에는 PlayerStart가 slab 위에 생성된다. L_Dev 기본 PlayerStart(−5 m, 0) 자리에서라면 dist ≈ 266.6 m, 레벨 원점에서는 263.6 m라 기본 반경(150/250)으로는 자동 로드되지 않는다 — `synthetic_zone.run()`이 PlayerStart를 옮기는 이유.
- [ ] **(1) 청크 위치**: 북쪽에 파사드 벽 3조각이 보이고, 서쪽 조각에 문 구멍.
- [ ] **(2) 충돌 메시**: 슬래브 위를 걷고 뛴다. 슬래브 끝(남쪽 12 m, 동서 22 m)에서 20 cm 아래 지면(`Zone_Ground`)으로 내려가고 다시 올라올 수 있다.
- [ ] **(3) blocker**: x = −12 m 지점(원점에서 서쪽 12 m)의 문 구멍으로 북진 → 보이지 않는 벽(`Blocker_glass_1`, 유리)에 막힌다. 다른 x에서는 파사드 충돌벽에 막힌다(`z.run(interior=True)` 이후에는 x=+5 m 문(`door_1`) 제외 — WP-05). `interior=False` 상태에서도 manifest의 `door_1` 포털은 스폰되므로 x=+5 m 문 앞에 서면 Warning `Portal door_1: no AGolmokZone 'z_synthetic_001_interior' … sublevel only`·`LevelStreaming: sublevel package missing`이 찍힌다 — 무해(WP-05 런북 §2에서 실내를 만들면 사라진다). `show collision`으로 청록/빨강 박스 확인 가능.
- [ ] **(5) 베이스맵 숨김**: 시작 시 `BM_dummy_inside`(zone 위 5 m의 4 m 큐브)가 **보이지 않고**, `BM_dummy_outside`(동쪽 60 m)는 보인다. 로그 `GolmokZoneSubsystem: basemap actors hidden +1, restored 0 (tagged 2, zones loaded 1)`.
- [ ] **(4) 거리 로드/언로드**: 반경을 줄여 걷기 거리 안에서 확인한다.
  ```
  golmok.zone.radius 20 40
  ```
  남쪽으로 **50 m 이상** 뛰어간다(시작점이 원점 남쪽 5 m, footprint 남쪽 경계가 원점 남쪽 10 m이므로 경계에서 40 m를 넘기려면 원점 기준 y ≤ −50 m, 즉 시작점에서 45 m 이상. 지면 `Zone_Ground` 위). 0.5 s 안에 로그 `Zone z_synthetic_001 v1 unloaded`, 벽이 사라지고 `BM_dummy_inside`가 **다시 보인다**(`restored 1`). 돌아와 footprint 경계 20 m 안(원점 기준 y ≥ −30 m) → `loaded` 로그, 벽 복귀, 큐브 다시 숨김. `golmok.zone.list`의 dist가 움직임을 따라 바뀐다(`>=`가 붙은 값은 bbox 하한).
  `golmok.zone.radius 150 250`으로 복구.
- [ ] 콘솔 `golmok.zone.unload z_synthetic_001` → 언로드(blocked), `golmok.zone.load z_synthetic_001` → 로드(pinned, `list`에 `pinned`). 이후 멀리 가도 언로드되지 않는다.
- [ ] PIE 종료 시 에러·ensure 없음. 에디터로 돌아오면 큐브 2개 모두 보임(복원).
- [ ] (선택) 두 번째 zone 겹침: `Zone_z_synthetic_001`를 복제하고 ZoneId는 같게 두되 Version=1 그대로 → 로그 `zone … is placed twice` 경고만 확인(우선순위 규칙은 실 Zone 2개가 생기면 V-06에서).

## 4. 원점 없음(개발 레벨) 동작
- [ ] `GeoOrigin` 액터를 삭제하고 `Zone_z_synthetic_001` 디테일의 **Rebuild In Editor** → 경고 `No AGolmokGeoOrigin in …` 1회, zone이 레벨 원점(0,0,0)에 Yaw 0으로 놓인다. 되돌리려면 `z.run(import_assets=False)`.

## 5. 패키징(선택, 30분)
- [ ] `.\tools\ue\package.ps1` → 실행 파일에서 콘솔 `open L_ZoneTest`(기본 맵은 L_Dev) → `golmok.zone.list`에 zone이 있고 `loaded`. 실패하면 manifest가 pak에 안 들어간 것: `DefaultGame.ini`의 `+DirectoriesToAlwaysStageAsUFS=(Path="Golmok/Zones")`가 프로젝트 설정 Packaging › "Additional Non-Asset Directories to Package"에 보이는지 확인.

## 6. 컴파일 에러가 나면 — 불확실한 UE 5.8 API와 대안
클라우드 세션이 공식 문서를 열지 못해(사이트가 스크립트 렌더링·403) **엔진 헤더로 직접 확인하지 못한** 호출 목록. 오류 메시지에 아래 이름이 보이면 대안으로 바꾼다.

| # | 파일 | API | 불확실한 점 | 대안 |
|---|---|---|---|---|
| 0 | GolmokZoneManifest | `FJsonObject::TryGet{Number,String,Array,Object,Bool}Field(key, …)`, `HasField`, `TryGetField` | 5.4+ `FStringView` 오버로드 → TCHAR 리터럴 키가 모호 | **키를 `const FString` 객체로 넘긴다**(이미 그렇게 함). 그래도 실패하면 `GetField<EJson::…>(FString)` |
| 1 | GolmokZoneSubsystem | `UWorldSubsystem::DoesSupportWorldType(const EWorldType::Type) const` override | 5.8에서 시그니처 유지 여부 | 오버라이드 삭제 후 `ShouldCreateSubsystem(UObject* Outer)`에서 `Cast<UWorld>(Outer)->WorldType`이 Game/PIE인지 검사 |
| 2 | GolmokZoneSubsystem | `UWorldSubsystem::OnWorldBeginPlay(UWorld&)` | 존재는 확실, 액터 BeginPlay와의 순서 | 순서 무관하게 설계됨(액터 등록 + 스윕). 시그니처 오류면 `Initialize`에서 `FWorldDelegates::OnWorldBeginPlay`? 대신 첫 `RegisterZone`에서 타이머 시작 |
| 3 | GolmokZoneSubsystem | `FTimerManager::SetTimer(Handle, this, &Class::Method, float, bool)` | 안정 | `FTimerDelegate::CreateUObject(this, &UGolmokZoneSubsystem::Evaluate)` 오버로드 |
| 4 | GolmokZoneSubsystem | `AActor::GetActorBounds(bool, FVector&, FVector&)` | 4번째 인자 `bIncludeFromChildActors` 기본값 | 그대로 3인자 호출 가능해야 함; 안 되면 `GetComponentsBoundingBox(true).GetCenter()` |
| 5 | GolmokZone | `UBoxComponent` 인게임 와이어(`SetHiddenInGame(false)`, `bDrawOnlyIfSelected=false`, `ShapeColor`, `SetLineThickness`) | 멤버 접근 권한·렌더 여부 | 컴파일 오류면 해당 줄 삭제; 안 보이면 `Evaluate()`에서 `DrawDebugBox(World, …, 0.6f)`(0.5 s 타이머) |
| 6 | GolmokGeo | `FMatrix::ToQuat()` | 안정(UnrealMath) | `FQuat(Rot)` 생성자 또는 `Rot.Rotator().Quaternion()` |
| 7 | GolmokZone | `FRotationMatrix::MakeFromXZ(X, Z)` | 안정 | `FMatrix(FPlane(X,0), FPlane(Z^X,0), FPlane(Z,0), FPlane(0,0,0,1)).Rotator()` |
| 8 | GolmokZone | `StaticLoadObject(UStaticMesh::StaticClass(), nullptr, *Path, nullptr, LOAD_NoWarn \| LOAD_Quiet)` | 플래그 이름 | `LoadObject<UStaticMesh>(nullptr, *Path)` |
| 9 | GolmokZone | `UCollisionProfile::BlockAll_ProfileName`, `NoCollision_ProfileName` (`Engine/CollisionProfile.h`) | 안정 | `SetCollisionProfileName(TEXT("BlockAll"))` / `TEXT("NoCollision")` |
| 10 | GolmokZone | `USceneComponent::SetupAttachment` → `RegisterComponent()` 순서(런타임 NewObject) | 경고 가능 | `RegisterComponent()` 후 `AttachToComponent(Root, FAttachmentTransformRules::KeepRelativeTransform)` |
| 12 | 전체 | `UPROPERTY` `double`, `TArray<double>`, `FVector2D`(double), `TWeakObjectPtr` in USTRUCT | UE5에서 리플렉션 가능 | 문제 시 `TArray<double>` → `TArray<FVector>`4개로 분해 |
| 13 | GolmokZone | `UFUNCTION(CallInEditor, BlueprintCallable)` 조합 | 허용됨 | `BlueprintCallable` 제거(Python은 `call_method("RebuildInEditor")`) |
| 14 | GolmokGeoOrigin | `UCLASS(HideCategories=(…))` 목록의 카테고리 이름 | 없는 이름은 무시됨 | 목록 축소 |
| 15 | GolmokZoneSubsystem | `UGameplayStatics::GetPlayerPawn / GetPlayerCameraManager(World, 0)` | 안정 | `World->GetFirstPlayerController()->GetPawn()` |
| 16 | GolmokZone | `UStaticMeshComponent::bAffectDistanceFieldLighting` 직접 대입 | public UPROPERTY | 줄 삭제 |
| 17 | synthetic_zone.py | `unreal.GolmokGeoOrigin`, `unreal.GolmokZone`, `set_editor_property("zone_id")`, `zone.rebuild_in_editor()` | Python 이름 노출(BlueprintCallable) | `zone.call_method("RebuildInEditor")`; 속성 이름은 `dir(zone)`으로 확인 |
| 18 | synthetic_zone.py | `unreal.Paths.project_content_dir()/project_saved_dir()`, `EditorAssetLibrary.delete_directory` | 안정 | `unreal.SystemLibrary.get_project_content_directory()` |
| 19 | GolmokZone | 루트 Movable + 자식 Stationary 조합(런타임 `SetActorTransform` 허용, Static 자식은 비Static 부모에 붙일 수 없음) | 런타임 로그 "AttachTo … Aborting" 또는 "Mobility … has to be Movable" | 자식도 Movable로(VSM 캐시 비용 증가) 또는 원점 액터를 먼저 배치해 에디터에서 위치 확정 후 루트 Static |
| 20 | GolmokZone | `StaticFindObjectFast(nullptr, this, Name)`, `UObject::Rename(*Name, this, REN_DontCreateRedirectors \| REN_DoNotDirty \| REN_NonTransactional \| REN_ForceNoResetLoaders)`(언로드한 컴포넌트를 `TRASH_Golmok_*`로 개명) | 플래그 이름 | Rename 줄 삭제(이름이 `__<n>` 접미사를 얻을 뿐 동작 동일) |
| 21 | GolmokZoneSubsystem | `FWorldDelegates::LevelAddedToWorld / LevelRemovedFromWorld` (`AddUObject`, `(ULevel*, UWorld*)`) | 시그니처·존재 | 바인드 두 줄 삭제 후 `DefaultGame.ini`의 `BasemapRescanSeconds=10` |
| 22 | GolmokZoneManifest | `FRegexPattern`/`FRegexMatcher` (`Internationalization/Regex.h`, zone_id 검사) | 안정(Core) | 수동 문자 검사로 교체 |
| 23 | GolmokZoneManifest | `TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&String)` + `FJsonSerializer::Serialize(Obj, Writer)` (quality 추가 키 보존) | 안정 | `ExtraJson` 채우는 블록 삭제 |
| 24 | 패키징 | `FFileHelper::LoadFileToString`로 pak 안 UFS 스테이징 파일 읽기 | 경로 유지 여부 | `+DirectoriesToAlwaysStageAsNonUFS`(느슨한 파일)로 전환 |

## 7. 결과 기록
V-03 PC 세션(Claude Desktop, 사용자 PC, Fable 5.1), 2026-09-25. UE 5.8.3, VS 2026(MSVC 14.51), 브랜치 `pc/v03-verify-wp04-05`.
**검증 방식**: 사람이 없는 무인 세션이라 PIE 체크는 에디터 Python 드라이버(Slate 틱 콜백에서 `editor_request_begin_play` → 콘솔 명령·`set_actor_location` 텔레포트·`add_movement_input` 보행·`golmok.screenshot`/`shot showui` 스크린샷·액터 상태 프로브)로 돌리고, 로그·상태값·스크린샷으로 판정했다. 텔레포트는 오버랩 이벤트를 정상 발생시킨다(문 트리거·슬래브 낙하 확인). 헤드리스 `z.run()`은 `UnrealEditor-Cmd -unattended -nullrhi`로 실행(같은 로그).

| 항목 | 결과 | 메모 |
|---|---|---|
| 빌드 | ✅ 수정 후 통과 | WP-04 코드 자체는 컴파일 오류 없음. 프로젝트 경고 1건: `GolmokZone.cpp(705)` `REN_ForceNoResetLoaders` C4996(5.8에서 no-op, 제거 → `e446504`). 나머지 C4996 경고 34건은 엔진 헤더(`Class.h`, `SkeletalMesh.h`, `Character.h` 등) — 프로젝트 무관 |
| §2 생성 | ✅ 수정 2건 후 기대 로그 전부 일치 | ① UE 5.8 Interchange가 glTF 메시를 `<폴더>/<소스명>/StaticMeshes/<이름>`에 두어 `imported as …, but AGolmokZone loads …` 예외 → `_import`로 임포트 후 `rename_asset`로 규약 경로로 이동(`12e6bad`). ② 첫 실행이 ①에서 죽으면서 `new_level()`이 저장한 **빈** `L_ZoneTest`(조명 없음)가 남아 다음 실행이 그대로 열었다 → 조명 없는 맵을 열면 `_build_lighting()` 재실행(`dd2c538`). 로그: root (17670.59, −22198.00, 999.37) yaw −0.0012 · (10,0,0) m → (18670.59, −22198.02, 999.34) · chunk_01 (17670.61, −22198.02, 1599.37) · glass_1 → (16470.58, −23197.98, 1149.37) · door_1 → (18170.57, −23148.01, 999.32) yaw −90 · `loaded … chunks 3/3 (0 wire boxes), collision 1/1, blockers 1/1, portals 1`. 에셋 4개, 액터(GeoOrigin 0,0,0 / 37.56 / 126.923 / 40, Zone, Zone_Ground z 979.37, BM_dummy_inside/outside, 조명 5) 확인. 디테일: State LOADED, LastError 빈, Missing 0, Priority 10, Portals [door_1], Chunk 3(태그 chunk_00..02), Collision 1, Blocker_glass_1(태그 glass_1) |
| (1) 청크 위치 | ✅ | PlayerStart에서 북쪽에 파사드 3조각이 이음새 없이 이어지고 서쪽 조각에 문 구멍(`pc-verify-wp04-facade.jpg`, `pc-verify-wp04-glass-opening.jpg`) |
| (2) 충돌 | ✅ | 슬래브 위 캡슐 중심 z 94.2 cm → 남쪽 7 m 넘어 `Zone_Ground`로 내려가 74.1(−20 cm) → 북으로 걸어 다시 94.1. 달리기 500 cm/s(`vel=(500,0,0)`) |
| (3) blocker | ✅ | x=−12 m 문 구멍으로 북진 → y=−952.9 cm에서 정지(유리 남면 −995 + 캡슐 반경 42 = −953). x=−8 m → −937.9(파사드 남면 −980 + 42). `interior=False`에서 x=+5 m 문 트리거에 서면 Warning `Portal door_1: no AGolmokZone 'z_synthetic_001_interior' … sublevel only` + `LevelStreaming: sublevel package missing` 2줄 → 무해 확인, 트리거를 벗어나면 `player left -> unload … was not streamed`. `show collision`으로 캡슐·문 트리거 초록 박스 확인(`pc-verify-wp04-collision.jpg`) |
| (4) 거리 로드/언로드 | ✅ | `golmok.zone.radius 20 40` → 원점 남쪽 55 m(지면)로 이동 0.5 s 안에 `unloaded`, `list` `dist >= 45.0 m`, 벽 사라지고 `BM_dummy_inside` 다시 보임(`restored 1`, `pc-verify-wp04-unloaded.jpg`) → 25 m로 복귀 `loaded`, `dist 15.0 m`, 큐브 다시 숨김. `radius 150 250` 복구 |
| (5) 베이스맵 숨김 | ✅ | 시작 로그 `basemap actors hidden +1, restored 0 (tagged 2, zones loaded 1)`; PIE에서 `BM_dummy_inside` hidden=True, outside False; PIE 종료 시 `restored 1`, 에디터로 돌아오면 둘 다 보임(dirty 없음) |
| (6) selftest | ✅ | `golmok.geo.selftest (spec zone-manifest.md §4 B/C): PASS`, `Level origin: lat=37.5600000 lon=126.9230000 h=40.000` |
| `unload`/`load` 콘솔 | ✅ | `unload` → unloaded(큐브 복원) → `load` → `loaded (pinned)`, `list`에 `pinned`; 90 m 밖에서도 `loaded dist 80.0 m pinned` |
| §4 원점 없음 | ✅ | GeoOrigin 삭제 + Rebuild → Warning `No AGolmokGeoOrigin in L_ZoneTest …` 1회, zone (0,0,0) yaw 0, chunk_01 center (0,0,600). `z.run(import_assets=False)`로 복구(원점·zone·PlayerStart 원위치) |
| §5 패키징 | ⏭ 미실행 | 선택 항목. WP-05 §9와 함께 V-06에서 |
| (선택) 두 번째 zone 겹침 | ⏭ 미실행 | 실 Zone 2개가 생기면 V-06 |
| PIE 종료 | ✅ | Error·ensure 없음(LogHttp 종료 경고만), Transient 액터 잔류 없음 |
| 고친 API(§6 번호) | 표에 없던 3건 | `12e6bad` Interchange 폴더 배치(§6 #17·18 영역, Python) · `dd2c538` 빈 맵 조명 재생성(Python) · `e446504` #20 `REN_ForceNoResetLoaders` 제거(C++). §6 #0~#24의 C++ 호출은 전부 5.8에서 그대로 컴파일됨 |

발견 메모(다음 세션용): `UnrealEditor-Cmd -ExecCmds="py …,Quit"`의 별도 `Quit`는 에디터를 끝내지 않는다(프로세스가 남음) — 스크립트 끝에서 `unreal.SystemLibrary.quit_editor()`를 부를 것. `test.ps1`의 `Automation RunTests …;Quit`는 자동화 컨트롤러가 처리하므로 정상.
