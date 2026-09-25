# WP-09 — UE C++ 런타임 3: Zone Index 발견·비동기 로드

상태: ⚪ 대기 · 담당: 클라우드 Claude 세션(**Fable 5.1 ultracode**, 검증 Opus, 모델 정책 DEVELOPMENT-PLAN §7.4) · 의존: WP-04, WP-05, WP-06 · 검증: G2(`runbooks/pc-verify-wp09.md`, V-03 뒤 PC 세션)

## 목표
레벨에 액터를 미리 놓지 않아도 게임이 **Zone Index**(`docs/spec/zone-manifest.md` §6)를 읽어 플레이어 주변 zone을 발견·스폰·관리하게 한다(D-008 "가는 곳마다 누적" 방식의 런타임 절반, ARCHITECTURE §4-1). 대용량 청크 로드를 **비동기**(`FStreamableManager`)로 바꿔 히치를 없앤다. V-03에서 발견된 디버그 표시 문제 2건을 함께 정리한다.

## 배경
- WP-04 결과 "남은 것": Index(`index/cells`)에서 zone을 발견해 스폰하는 경로 미구현(레벨 배치 `AGolmokZone`만 `RegisterZone`). `bAsyncLoad`는 플래그 + 설계 §4-4 TODO 본문(코드 주석)만 있고 동기 로드. WP-05 결과도 같은 항목을 미구현으로 명시.
- `UGolmokZoneSubsystem::Evaluate()`는 `Zones` 배열 원소 포인터를 `Load()` 사이에 유지 → **`Load()` 스택에서 `RegisterZone`/`RequestLoad` 금지** 규약(WP-05가 테스트로 강제). 발견·스폰·파괴는 반드시 이 루프 밖에서 한다.
- Index 파일(WP-02, `golmok-zone index build --zones-root zones --out index`): `index/zones.json`(zone당 최신 유효 version, `bbox_wgs84`, manifest 상대경로), `index/cells/16_<x>_<y>.json`(footprint가 실제로 겹치는 z16 웹 메르카토르 타일, `zones`는 이기는 순서). 셀 공식: `x = floor((lon+180)/360·2^z)`, `y = floor((1 − asinh(tan φ)/π)/2·2^z)`.
- WP-06 `zone_import.py`가 manifest·에셋을 `Content/Golmok/Zones/<id>/v<ver>/`로 넣는다. Index는 아직 게임 콘텐츠에 없다.
- **V-03 발견(WP-05 런북 §12, 코드 미수정)**: (a) HUD `render` ms가 `0.00`으로 읽히는 일이 잦다(같은 순간 `stat unit` Draw는 5 ms대) — `GRenderThreadTime`(5.8: RenderCore `RenderTimer.h`)을 `OnEndFrame`에서 읽는 시점 문제로 추정. (b) 포털 언로드 뒤 실내 zone이 HUD/`golmok.zone.list`에 `unloaded … blocked`로 표시 — WP-04 `RequestUnload` 규약(반경 밖으로 나가야 자동 로드 재개)인데 실내는 거리 관리 대상이 아니라 표시만의 문제.
- 5.8 주의(V-03): `FJsonObject::Values`는 `TMap<UE::FSharedString, …>` → `TryGetField(FStringView)`/`FString(*Pair.Key)`; `FJsonSerializer`는 Build.cs `Json`에 이미 있음.

## 산출물 (`unreal/Golmok/Source/Golmok/Zones/`, `Content/Python/golmok/`, `tools/`)
1. **Index 게임 내 규약**: `Content/Golmok/Zones/index/zones.json` + `index/cells/`(원본 파일 그대로; 쿠킹 시 UFS 스테이징 — WP-05 `lighting_presets.json`과 같은 `DefaultGame.ini` `+DirectoriesToAlwaysStageAsUFS`). `zone_import.py`에 `--with-index`(또는 `zone_index.sync(zones_root)`) 추가: `golmok-zone index build` 결과를 복사·검증(순수 함수는 `_pure.py`, 테스트는 가짜 unreal). `docs/spec/zone-manifest.md` §6에 "게임 내 위치" 항목 추가.
2. **`FGolmokZoneIndex`**(`GolmokZoneIndex.h/.cpp`, 순수 파서): `zones.json`·셀 JSON 파싱, 셀 좌표 `LonLatToCell(lon, lat, z=16)`(스펙 공식; 순수 헤더 `GolmokGeoMath.h`에 추가해 **g++ 교차검증**), 플레이어 위치(`UGolmokGeoSubsystem::LevelUEToLonLat`) 주변 **3×3 셀** 조회, 셀당 1회 파싱 캐시(파일 없음 = 빈 셀, 경고 1회).
3. **`UGolmokZoneSubsystem` 확장**: `bDiscoverFromIndex`(Config, 기본 true; index 폴더 없으면 조용히 비활성), `DiscoveryIntervalSeconds`(기본 2 s), `DespawnDistanceM`(기본 UnloadRadius×2). 같은 타이머 발화 안에서 `Evaluate()` **앞**(`Load()` 스택 밖)에 `DiscoverZones()`: 주변 셀의 zone 중 미등록 id → `SpawnActorDeferred<AGolmokZone>`(ZoneId/Version 설정, `bSpawnedFromIndex=true`, Transient, 폴더 `Golmok/Zones/Discovered`) → `FinishSpawning`(BeginPlay가 `RegisterZone`). 레벨 배치 액터와 같은 id면 스폰하지 않음(배치 우선). 발견 zone이 3×3 셀 밖·Unloaded·`DespawnDistanceM` 밖이면 `Destroy()`(EndPlay가 `UnregisterZone`). 에디터 월드에서는 발견하지 않음.
4. **비동기 로드**(설계 §4-4 그대로): `FStreamableManager`는 서브시스템 소유, `AGolmokZone::LoadAsync()`, `EGolmokZoneState::Loading` 추가, `TSharedPtr<FStreamableHandle> LoadHandle`, `Unload()`가 취소, `OnAssetsLoaded`는 `IsValid && State==Loading`일 때만 컴포넌트 생성. `bAsyncLoad` 기본 **true**(ini로 끔, 동기 경로 유지). `RequestAsyncLoad` 오버로드 모호(5.4+) → 델리게이트 변수 선행. 포털 `RequestLoad(pin)`도 async를 타되 `AGolmokPortal`은 `Loading`을 `Pending` 유지로 처리(WP-05 상태기계 재검토; `Load()` 스택에서 RegisterZone/RequestLoad 금지 규약 유지).
5. **디버그 정리(V-03)**: (a) HUD/`golmok.stats`의 `render` ms — 프레임 끝이 아니라 렌더 스레드 시간이 확정된 시점(예: `FCoreDelegates::OnBeginFrame`에서 직전 프레임 값 읽기, 또는 `GRenderThreadTime` 대신 `FThreadIdleStats`/`GRenderThreadTimeCriticalPath` 등 5.8 제공 값)으로 옮기고, 0이면 `n/a`가 아니라 직전 유효값 유지 규칙을 순수 헤더 `GolmokStatsMath.h`에 넣어 g++ 검증. (b) 실내(포털 관리) zone은 `RequestUnload` 뒤 `blocked` 대신 `portal`(또는 `idle`)로 표시 — `UGolmokZoneSubsystem`에 "거리 관리 제외" 플래그(포털이 `RequestLoad/RequestUnload`한 zone) 추가, `golmok.zone.list`/HUD 형식은 열 추가만(기존 테스트 유지).
6. **콘솔·HUD**: `golmok.zone.index`(현재 셀 좌표, 주변 3×3 셀의 zone 목록, 발견/배치 구분, 캐시 상태), `golmok.zone.list`에 `[index]`/`[placed]` 표시, HUD `zones:` 줄에 발견 수·로딩 중 수.
7. **테스트**: 픽스처 `tools/tests/fixtures/zones/index/`(합성 zone 2개 — `z_synthetic_001`과 약 200 m 떨어진 `z_synthetic_002`를 WP-06 `tools/scripts/make_synthetic_zone.py`로 생성 → `golmok-zone index build`; pytest가 재현·바이트 비교), C++ 순수 셀 공식 g++ 교차검증(`test_ue_geo_math.py` 확장, 스펙 §6 예제값), UE 자동화 `Golmok.Zone.IndexParse / IndexDiscover / AsyncLoad / AsyncCancel / InteriorNotBlocked`(`-nullrhi`, `L_ZoneTest` 없으면 skip), Python `test_ue_zone_index_sync.py`(가짜 unreal, WP-06 `tools/tests/fake_unreal.py` 재사용), WP-04·05 기존 테스트 전부 통과(Evaluate 규약 테스트는 `Discover` 경로가 `Load()` 스택 밖임을 증명하는 형태로 확장).
8. **런북** `docs/runbooks/pc-verify-wp09.md`: index 동기화 → 빌드 → `test.ps1`(UE 자동화) → PIE에서 배치 액터 없이 발견·로드 확인 → 걸어 나가서 파괴 확인 → `bAsyncLoad` 켜고/끄고 히치(HUD 1% low, `golmok.path play --csv` → `golmok-perf`) 비교 → HUD `render` ms·실내 표시 재확인 → 불확실 API 표(WP-04 §6 형식). 무인 검증은 V-03 방식(에디터 Python PIE 드라이버, `unreal.SystemLibrary.quit_editor()`, HUD 끄고 캡처).

## 완료 기준
- `python -m pytest` 통과, CI 초록(ubuntu·windows), 런북 완비, STATUS `🟡`.
- WP-04·05 테스트가 그대로 통과. 발견·파괴·비동기 완료 콜백이 `Evaluate()`/`Load()` 스택 밖에서만 일어남을 테스트로 증명.

## 주의
- D-010 전이므로 시각 레이어 포맷은 건드리지 않는다(메시 경로 그대로).
- 발견 zone은 Transient(저장 안 함). 레벨 배치 액터가 있으면 항상 배치가 이긴다.
- 콘솔 명령 12개·Enhanced Input 키 이름을 바꾸지 않는다(WP-05 규약). `!DebugExecBindings=ClearArray` 유지.
- Windows CI: 서브프로세스 `encoding="utf-8"`, 큰 입력은 stdin, 경로 비교는 `os.path.normpath`, `rglob`/`iterdir` 결과는 정렬 후 비교(WP-06 교훈).

## 설계 (확정, 2026-09-25)

근거: 이 문서 산출물 1~8, WP-04 §4-4(`bAsyncLoad` TODO)·§5(`Evaluate` 규칙)·"통합 리뷰"(레코드 포인터), WP-05 "결과" §3-1 `Evaluate()` 포인터 안정성 문단, `runbooks/pc-verify-wp05.md` §11·§12(V-03 확정 사실), 스펙 §6·`zone-index.schema.json`·`tools/golmok_tools/zone/index.py`, 현재 코드(`Zones/*`, `Portals/GolmokPortal.*`, `Debug/GolmokDebugSubsystem.cpp`, `Geo/GolmokGeoMath.h`, `Debug/GolmokStatsMath.h`). 세 후보 설계(API 현실성·데이터/검증·상태기계/재진입)를 심판 2명이 심사해 **API 현실성안을 기준으로 나머지 둘의 장점을 이식**하고(§12 표) 지적된 결함을 전부 닫은 최종안이다. 선택지는 남기지 않았다. 이 절은 코드를 쓰지 않는다 — 구현 세션은 시그니처·ini 키·파일·테스트·런북을 그대로 옮기고, 엔진 API가 확실하지 않은 곳은 §10 표 번호로 런북에 넘긴다.

### 0. 확정 결정 요약
| 주제 | 결정 |
|---|---|
| Index 위치 | `Content/Golmok/Zones/index/zones.json` + `index/cells/16_<x>_<y>.json`, `golmok-zone index build` 출력 **바이트 그대로**. 스테이징 줄 추가 없음(`Golmok/Zones` UFS 항목이 덮음). `golmok_tools.zone.index.scan_zones`가 `index` 폴더를 건너뛰도록 고쳐 `--strict`와 스펙 레이아웃(zones 루트 안의 `index/`)의 모순을 해소 |
| 셀 공식 | `GolmokGeoMath::LonLatToCell/CellBounds`를 순수 헤더에 **추가만**(int, Zoom 0..30). Python `lonlat_to_tile`와 연산 순서까지 동일, g++ 드라이버 stdin 배치로 정수 완전 일치 검증 |
| 파서 | `FGolmokZoneIndex`: 리플렉션 없는 일반 클래스, **파일 리더 주입(`TFunction`)** + `NumFileReads()`로 "셀당 1회 파싱·없는 파일 = 빈 셀"을 메모리에서 증명. 정적 함수 인자는 전부 `In*`(C4458) |
| 발견 | 타이머 콜백 `OnEvaluateTimer()` = `DiscoverZones()`(주기 도달 시) → `Evaluate()`. `Evaluate()` 본문에는 스폰·파괴·등록·요청 호출이 **없다**(정적 pytest + 동적 `PointerHoldDepth` 위반 카운터). 스폰은 WP-05 포털과 같은 `FActorSpawnParameters{bDeferConstruction, RF_Transient}` + `FinishSpawning`, 파괴는 후보 수집 뒤 스냅샷 실행 |
| 파괴 | `bSpawnedFromIndex && Unloaded && !bPinned && 3×3 밖 && 거리 > DespawnDistanceM(0 = 2×UnloadRadiusM, 사용 시점 계산) && !(실내 && 부모 Loaded/Loading)`가 **`DespawnGraceSeconds`(10 s) 연속** 성립할 때만. 배치 쌍둥이가 생긴 발견 zone은 `Unloaded && !bPinned`일 때만 retire(Loaded/pinned면 `bRetirePending`으로 표시하고 다음 패스) |
| 비동기 | `FStreamableManager`는 서브시스템 **값 멤버**(`UAssetManager` 패턴; TUniquePtr/불완전형 함정 없음). `RequestAsyncLoad`는 `FPackageName::DoesPackageExist`를 통과한 경로만, **0개면 부르지 않고 동기 경로**(와이어 박스). 완료는 **항상 다음 틱**(`OnStreamableComplete` → `bFinishPending` + `AsyncFinishTimer = SetTimerForNextTick(FinishAsyncLoad)`), `AsyncSerial` 세대 검사로 취소·재요청·지연 발화 전부 폐기. 완료가 `Load()`/`Evaluate()` 스택 위에서 컴포넌트를 만드는 경로는 구조적으로 없다 |
| 취소 | `Unload()` 첫 줄 `CancelAsyncLoad()`: 타이머 해제 → `++AsyncSerial` → `CancelHandle()`+`Reset()` → `Loading`이면 `Unloaded`(로그 "async load cancelled", `NotifyZoneUnloaded` 없음) |
| 포털 | 상태 enum 불변. `Idle→Pending` 다음 틱에 실내 **선로드**(`RequestLoad(pin, Portal)`), 디바운스 끝에 실내가 `Loading`이면 **`Pending` 유지** 0.05 s 폴링(최대 10 s .cpp 상수) → `Loaded`/없음/실패/타임아웃일 때 `StreamIn`+`Active`. `bInteriorRequested` + `IsHoldingInterior()`(Active·Leaving·Pending+요청)가 `EndPlay`/`LeaveInterior`/`IsInteriorZoneInUse`를 넓혀 요청한 pin을 항상 반납. 반납은 언제나 타이머 뒤(`StartLeaving` → 3 s → `RequestUnload`) |
| 실내 표시 | `RequestLoad/RequestUnload(…, EGolmokZoneRequestSource)` 기본 `Console`. `Portal` 언로드는 `bBlocked` 대신 `bPortalManaged`(거리 관리 제외, `Evaluate`의 `bManaged`에서 제외) → 목록/HUD ` portal` 열 |
| render ms | `GOLMOK_RENDER_TIME_SOURCE` 0/1/2(기본 1 = `OnBeginFrame`에서 직전 프레임 `GRenderThreadTime` 캐시, `OnEndFrame`이 샘플에 넣음). 0이면 직전 유효값 유지 `GolmokStatsMath::HoldLastPositive`(g++ 검증). `OnEndFrame` 바인딩·`FormatStatsLine` 형식 불변, 진단은 `golmok.stats` 두 번째 로그 줄 |
| ini | `UGolmokZoneSubsystem` 4키(`bDiscoverFromIndex, DiscoveryIntervalSeconds, DespawnDistanceM, DespawnGraceSeconds`) + `bAsyncLoad=True`. 포털·디버그 키 집합 불변(WP-05 `EXPECTED_KEYS`). 스폰/파괴 예산은 `static constexpr` |
| 픽스처 | `z_synthetic_002` = 001 원점에서 **동쪽 200 m**(`make_synthetic_zone.py --offset-m 200,0`, manifest+blockers만 복사, 에셋 없음) → 다른 x 셀(55874). index는 `tools/tests/fixtures/zones/index/`(스펙 경로) + Content 사본, `make_index_fixture.py --check`로 바이트 재현 |
| WP-05 테스트 | `Golmok.Portal.SpawnFromManifest`는 `Zone->bAsyncLoad = false;` 1줄 추가(동기 경로 회귀 테스트로 유지; 비동기는 `Golmok.Zone.AsyncLoad`가 검증), L_ZoneTest 포털 테스트 3개의 `StreamInTimeoutSeconds` 2.0 → 5.0(상한만) |
| 헤더 형식 | `DescribeZones()` 헤더 줄은 기존 접두 뒤에 `, %d discovered, %d loading`만 덧붙임. 행은 ` portal`·` (loading %.1f s)`·` [index]`/` [placed]` 토큰 추가만 |

### 1. 파일 목록
| 경로 (`unreal/Golmok/` 기준, 그 외 저장소 기준) | 상태 | 내용 |
|---|---|---|
| `Source/Golmok/Zones/GolmokZoneIndex.h` / `.cpp` | 신규 | `FGolmokZoneIndex`(§3-2): 파서·셀 캐시·3×3 조회·Describe. `.generated.h` 없음 |
| `Source/Golmok/Zones/GolmokZone.h` / `.cpp` | 변경 | `Loading` 상태, `LoadAsync/OnStreamableComplete/FinishAsyncLoad/CancelAsyncLoad/CollectAssetPaths/AcquireMeshAsset`, `bSpawnedFromIndex`, `AsyncLoadCount`(§3-4) |
| `Source/Golmok/Zones/GolmokZoneSubsystem.h` / `.cpp` | 변경 | `FStreamableManager Streamable`, `FGolmokZoneIndex Index`, `OnEvaluateTimer/DiscoverZones/SpawnDiscoveredZone`, Config 4키, `EGolmokZoneRequestSource`, 레코드 플래그, `PointerHoldDepth`, `golmok.zone.index`, 목록 열(§3-3) |
| `Source/Golmok/Geo/GolmokGeoMath.h` | 변경(추가만) | `MaxMercatorLatDeg`, `LonLatToCell`, `CellBounds`(§3-1) |
| `Source/Golmok/Portals/GolmokPortal.h` / `.cpp` | 변경 | 선로드·Pending 대기·`bInteriorRequested`·`IsHoldingInterior`·`Source=Portal`·`ResolveZoneVersion`(§3-5) |
| `Source/Golmok/Debug/GolmokStatsMath.h` | 변경(추가만) | `HeldValue`, `HoldLastPositive`(§3-6) |
| `Source/Golmok/Debug/GolmokDebugSubsystem.h` / `.cpp` | 변경 | `OnBeginFrame` 바인딩, `GOLMOK_RENDER_TIME_SOURCE`, `DescribeRenderSource`(§3-6) |
| `Source/Golmok/Tests/GolmokZoneTest.cpp` | 신규 | `Golmok.Zone.IndexParse / IndexDiscover / AsyncLoad / AsyncCancel / InteriorNotBlocked`(§8-2) |
| `Source/Golmok/Tests/GolmokPortalTest.cpp` | 변경(4줄) | SpawnFromManifest `Zone->bAsyncLoad = false;`, `StreamInTimeoutSeconds` 3곳 2.0 → 5.0 |
| `Config/DefaultGame.ini` | 변경 | `[/Script/Golmok.GolmokZoneSubsystem]` 4키, `[/Script/Golmok.GolmokZone] bAsyncLoad=True` + 주석(§7) |
| `Content/Golmok/Zones/index/zones.json`, `index/cells/16_*.json` | 신규 | Content zone 3개(001·001_interior·002)로 만든 index(픽스처와 바이트 동일) |
| `Content/Golmok/Zones/z_synthetic_002/v1/manifest.json`, `blockers.json` | 신규 | 001 동쪽 200 m, 에셋 없음(와이어 박스), 포털 없음 |
| `Content/Python/golmok/zone_index.py` | 신규 | `plan/sync/describe`, `ZoneIndexError`(§3-7) |
| `Content/Python/golmok/zone_import.py` | 변경 | `run(..., with_index=False)` |
| `Content/Python/golmok/_pure.py` | 변경 | index 순수 함수 6개, `LOG` `zx.*` 7키 |
| `tools/golmok_tools/zone/index.py` | 변경 | `scan_zones`가 `INDEX_DIR_NAME`("index") 폴더를 건너뜀 |
| `tools/scripts/make_synthetic_zone.py` | 변경 | `--offset-m E,N`(원점만 이동, 기본 `0,0` → 기존 출력 불변) |
| `tools/scripts/make_index_fixture.py` | 신규 | 002 생성(manifest·blockers만) → `build_index/write_index` → 픽스처·Content 두 사본, `--check` |
| `tools/tests/fixtures/zones/z_synthetic_002/v1/manifest.json`, `blockers.json` | 신규 | Content 사본과 바이트 동일 |
| `tools/tests/fixtures/zones/index/zones.json`, `cells/*.json` | 신규 | 스펙 경로(zones 루트 안) |
| `tools/tests/fixtures/ue/geomath_driver.cpp` | 변경 | `cell`, `cells`(stdin 배치), `cellbounds` 명령 |
| `tools/tests/fixtures/ue/statsmath_driver.cpp` | 변경 | `hold`(stdin 배치) 명령 |
| `tools/tests/test_ue_geo_math.py` | 변경 | +2(§8-1) |
| `tools/tests/test_ue_stats_math.py` | 변경 | +2 |
| `tools/tests/test_zone_index.py` | 변경 | +1(`index` 폴더 skip·`--strict` 회귀) |
| `tools/tests/test_ue_zone_index_fixture.py` | 신규 | 생성기 재현·바이트 비교·셀 표·거리 |
| `tools/tests/test_ue_python_zone_index_sync.py` | 신규 | 가짜 unreal로 `sync()`·`run(with_index=)` |
| `tools/tests/test_ue_wp09_fixture.py` | 신규 | ini·자동화 이름·**스택 규약 정적 증명**·C4458·익명 namespace·렌더 매크로·Build.cs·스테이징 줄 |
| `tools/tests/test_ue_zone_fixture.py` | 변경(1줄) | `actor["bAsyncLoad"] == "True"` |
| `tools/tests/test_ue_python_pure.py` | 변경 | `RUNBOOKS += pc-verify-wp09.md`, 모듈·touchpoint 목록에 `zone_index` |
| `tools/tests/test_make_synthetic_zone.py` | 변경 | `--offset-m` 1개 |
| `docs/spec/zone-manifest.md` §6 | 변경 | "게임 내 위치" 항목(§2 문안) |
| `docs/runbooks/pc-verify-wp09.md` | 신규 | §9 골자 |
| `docs/plan/WP-09-…md` 결과, `docs/plan/STATUS.md`, `docs/ROADMAP.md` | 변경 | 세션 규약 |

새 모듈 의존 없음(`Engine/StreamableManager.h`는 Engine, `Misc/PackageName.h`·`UObject/SoftObjectPath.h`는 Core/CoreUObject). `Golmok.Build.cs` 무변경을 pytest가 강제.

### 2. 데이터·경로 규약
- **Index 위치**: `<ProjectContentDir>/Golmok/Zones/index/zones.json`, `…/index/cells/16_<x>_<y>.json`. zones 루트 = `Content/Golmok/Zones`이므로 `zones.json`의 `manifest`(`<id>/v<n>/manifest.json`)가 그대로 `GolmokZoneManifest::ManifestFilePath`와 같은 파일을 가리킨다. C++는 재직렬화하지 않고 `FFileHelper::LoadFileToString`으로 읽는다(WP-04 manifest와 같은 경로, UFS pak 안에서도 동작). "index 없음" 판정은 디렉터리가 아니라 **`zones.json` 파일 존재**로 한다(pak 안 디렉터리 검사는 신뢰 불가).
- 스테이징: 기존 `+DirectoriesToAlwaysStageAsUFS=(Path="Golmok/Zones")`가 하위 폴더를 포함 → 줄 추가 없음(`test_default_game_ini_packaging_lines`의 2줄 유지).
- Content 트리에서 `index/`는 zone 폴더가 아니다. `test_every_content_zone_folder_matches_manifest_id_and_version`는 `*/v*/manifest.json` glob이라 영향 없음(변경 없음). CLI 쪽은 `scan_zones`가 `index`를 건너뛴다(§3-7).
- 스펙 §6 추가 문안: "**게임 내 위치**(WP-09): 게임은 `Content/Golmok/Zones/index/zones.json`과 `index/cells/16_<x>_<y>.json`을 원본 그대로 읽는다(비에셋 파일, `+DirectoriesToAlwaysStageAsUFS=(Path="Golmok/Zones")`가 덮음). 동기화는 `golmok-zone index build --zones-root <zones> --out <zones>/index` 뒤 에디터 Python `import golmok.zone_index as zx; zx.sync(r"<zones>")`(또는 `zone_import.run(..., with_index=True)`). 런타임은 플레이어 위치의 셀과 3×3 이웃만 읽고 셀당 1회 파싱해 캐시한다(없는 파일 = 빈 셀). zones 루트 안의 `index/` 폴더는 zone이 아니다(`scan_zones`가 건너뜀)."
- **셀 공식**(스펙 §6): `n = 2^z`, `φ = clamp(lat, ±85.0511287798066)`, `x = floor((lon+180)/360·n)`, `y = floor((1 − asinh(tan φ)/π)/2·n)`, x·y를 `[0, n−1]`로 클램프(랩 없음). Python과 동일 상수·연산 순서(`math.radians(lat) == lat·(π/180) == DegToRad`).
- **예제값**(이 세션에서 `index.lonlat_to_tile`·`tiles_for_polygon`으로 계산, pytest가 재계산해 단언):

| 입력 (lon, lat) | z | 셀 (x, y) | 비고 |
|---|---|---|---|
| (126.9250, 37.5620) | 16 | (55873, 25379) | 스펙 §6 예제 = `z_synthetic_001` 원점(동쪽 경계에서 4.3 m, 남쪽 경계에서 0.3 m) |
| (126.9230, 37.5600) | 16 | (55873, 25380) | area 원점 = 레벨 원점 = PIE 시작 위치 |
| (126.9272665, 37.5620) | 16 | (55874, 25379) | `z_synthetic_002` 원점(001 동쪽 200 m) |
| (0, 0) | 16 | (32768, 32768) | |
| (−180, 85.06) | 16 | (0, 0) | 위도 클램프 |
| (180, −85.1) | 16 | (65535, 65535) | x·y 클램프 |
| (126.9250, 37.5620) | 0 | (0, 0) | |
| (126.9250, 37.5620) | 20 | (893983, 406079) | |
| 셀 (55873, 25379) 경계 | 16 | W 126.9195556640625 S 37.56199695314352 E 126.925048828125 N 37.566351224992246 | `tile_bounds` |

- **픽스처 셀 표**(footprint 실제 겹침): 001 → {55873/25379, 55873/25380, 55874/25379, 55874/25380}(4셀), 001_interior → {55873/25379, 55874/25379}, 002 → {55874/25379, 55874/25380}. 셀 파일 4개: `16_55873_25379` = [001_interior, 001], `16_55873_25380` = [001], `16_55874_25379` = [001_interior, 001, 002], `16_55874_25380` = [001, 002](priority↓ → version↓ → id). 레벨 원점(55873/25380)의 3×3(x 55872..55874, y 25379..25381)이 4셀을 모두 덮으므로 PIE 시작 직후 세 zone이 전부 "near"다.
- 에셋: `GolmokZoneManifest::ChunkAssetPath/CollisionAssetPath`(WP-04 규약) → `FSoftObjectPath`. 패키지 이름은 `FPackageName::ObjectPathToPackageName`.

### 3. 클래스·함수 시그니처

#### 3-1 `Geo/GolmokGeoMath.h` 추가 (순수, `<array> <cmath> <cstddef>`만, 기존 함수 불변)
```cpp
	/** Web Mercator latitude limit (deg). Same literal as golmok_tools.zone.index.MAX_LAT. */
	constexpr double MaxMercatorLatDeg = 85.0511287798066;

	/**
	 * XYZ tile of (lon, lat) at Zoom (spec §6): x = floor((lon+180)/360·2^z), y = floor((1 − asinh(tan φ)/π)/2·2^z).
	 * Same expression order as index.lonlat_to_tile (g++ cross-check). Lat clamped to ±MaxMercatorLatDeg, x/y clamped
	 * to [0, 2^Zoom − 1] (no wrap), Zoom clamped to 0..30 (fits int).
	 */
	inline void LonLatToCell(double LonDeg, double LatDeg, int Zoom, int& OutX, int& OutY)
	{
		const int Z = (Zoom < 0) ? 0 : ((Zoom > 30) ? 30 : Zoom);
		const double N = std::ldexp(1.0, Z);                                   // 2^z exactly
		const double Lat = (LatDeg < -MaxMercatorLatDeg) ? -MaxMercatorLatDeg : ((LatDeg > MaxMercatorLatDeg) ? MaxMercatorLatDeg : LatDeg);
		const double X = std::floor((LonDeg + 180.0) / 360.0 * N);
		const double Y = std::floor((1.0 - std::asinh(std::tan(DegToRad(Lat))) / Pi) / 2.0 * N);
		const double Max = N - 1.0;
		OutX = static_cast<int>((X < 0.0) ? 0.0 : ((X > Max) ? Max : X));
		OutY = static_cast<int>((Y < 0.0) ? 0.0 : ((Y > Max) ? Max : Y));
	}

	/** (west, south, east, north) degrees of tile (X, Y) at Zoom — index.tile_bounds. */
	inline void CellBounds(int X, int Y, int Zoom, double& OutWest, double& OutSouth, double& OutEast, double& OutNorth)
	{
		const int Z = (Zoom < 0) ? 0 : ((Zoom > 30) ? 30 : Zoom);
		const double N = std::ldexp(1.0, Z);
		auto LatOf = [N](double Row) { return RadToDeg(std::atan(std::sinh(Pi * (1.0 - 2.0 * Row / N)))); };
		OutWest = static_cast<double>(X) / N * 360.0 - 180.0;
		OutEast = static_cast<double>(X + 1) / N * 360.0 - 180.0;
		OutSouth = LatOf(static_cast<double>(Y + 1));
		OutNorth = LatOf(static_cast<double>(Y));
	}
```
드라이버 명령: `cell <lon> <lat> <z>` → `x y`; `cells` → stdin 한 줄에 `lon lat z`씩(배치, Windows CI 규칙) → 한 줄에 `x y`씩; `cellbounds <x> <y> <z>` → 4 double(`%.17g`). MSVC `tan/asinh`의 마지막 ulp 차이는 `floor` 뒤 정수라 셀 경계 위 점(측정 불가 확률)에서만 드러난다 → 테스트는 경계 ±1e-9°·±1e-6°는 넣되 **정확히 경계인 점은 넣지 않는다**(문서화).

#### 3-2 `Zones/GolmokZoneIndex.h` (리플렉션 없음: UCLASS/USTRUCT/`.generated.h` 없음; include `CoreMinimal.h`, `Templates/Function.h`, `Zones/GolmokZoneManifest.h`)
```cpp
/** One row of index/zones.json (spec §6): the latest valid version of a zone. */
struct GOLMOK_API FGolmokZoneIndexEntry
{
	FString Id;
	int32 Version = 0;
	EGolmokZoneKind Kind = EGolmokZoneKind::Exterior;
	int32 Priority = 0;
	double West = 0.0;   // bbox_wgs84[0]
	double South = 0.0;  // [1]
	double East = 0.0;   // [2]
	double North = 0.0;  // [3]
	FString ManifestRel; // "<id>/v<n>/manifest.json" relative to Content/Golmok/Zones
};

struct GOLMOK_API FGolmokZoneIndexCellRef
{
	FString Id;
	int32 Version = 0;
};

/** One index/cells/16_<x>_<y>.json. Zones are in winning order (priority desc, version desc, id). */
struct GOLMOK_API FGolmokZoneIndexCell
{
	int32 Zoom = 16;
	int32 X = 0;
	int32 Y = 0;
	bool bFromFile = false;  // false = no file (empty cell) or parse error (Error set, treated as empty)
	FString Error;
	TArray<FGolmokZoneIndexCellRef> Zones;
};

/**
 * Runtime view of the Zone Index: zones.json parsed once, cell files parsed once each on first use and cached (a
 * missing file is an empty cell, warned once). File access goes through an injectable reader so Golmok.Zone.IndexParse
 * feeds JSON from memory. Owned by value by UGolmokZoneSubsystem. Static helpers take In* parameters (MSVC C4458).
 */
class GOLMOK_API FGolmokZoneIndex
{
public:
	/** (InFilePath, OutText) -> bool. Default: FFileHelper::LoadFileToString (UFS-staged files in a .pak included). */
	using FReadFile = TFunction<bool(const FString& InFilePath, FString& OutText)>;
	static constexpr int32 CellZoom = 16;

	static FString DefaultIndexDir();                                        // <ProjectContentDir>/Golmok/Zones/index
	static FString ZonesFilePath(const FString& InIndexDir);                 // <dir>/zones.json
	static FString CellFileName(int32 InX, int32 InY);                       // "16_<x>_<y>.json" (index.cell_name)
	static FString CellFilePath(const FString& InIndexDir, int32 InX, int32 InY);   // <dir>/cells/<CellFileName>
	static FString CellKey(int32 InX, int32 InY);                            // "16_<x>_<y>"
	/** zones.json text -> entries. false + OutError on: schema_version != 1, cell_zoom != 16, missing "zones", bad id
	 *  (GolmokZoneManifest::IsValidZoneId), version < 1, unknown kind, bbox not 4 numbers or west > east / south > north,
	 *  duplicate id. manifest != "<id>/v<version>/manifest.json" -> Warning, entry kept. Unknown keys ignored. */
	static bool ParseZonesText(const FString& InJsonText, TArray<FGolmokZoneIndexEntry>& OutEntries, FString& OutError);
	/** cell text -> OutCell (bFromFile = true). false + OutError on: schema_version != 1, z != 16, x / y missing or
	 *  negative, entry without id / version, duplicate id. */
	static bool ParseCellText(const FString& InJsonText, FGolmokZoneIndexCell& OutCell, FString& OutError);

	explicit FGolmokZoneIndex(FReadFile InReader = FReadFile());

	/** Reader(ZonesFilePath(InIndexDir)) + ParseZonesText; clears the cell cache. Missing file -> false with OutError
	 *  EMPTY (silently off); parse error -> false with OutError set. */
	bool Load(const FString& InIndexDir, FString& OutError);
	/** Tests: parse InZonesJson as zones.json and use InIndexDir (e.g. "mem:/index") for cell paths. */
	bool LoadFromText(const FString& InIndexDir, const FString& InZonesJson, FString& OutError);

	bool IsAvailable() const { return bLoaded; }
	const FString& GetIndexDir() const { return IndexDir; }
	int32 NumZones() const { return Entries.Num(); }
	const TArray<FGolmokZoneIndexEntry>& GetEntries() const { return Entries; }
	const FGolmokZoneIndexEntry* FindZone(const FString& InZoneId) const;   // TMap lookup

	/** Cached cell (parsed on first call, one Reader call per key ever). Never fails: no / bad file -> empty cell. */
	const FGolmokZoneIndexCell& GetCell(int32 InX, int32 InY);

	/**
	 * Zones of the (2R+1)² cells around the center (0..2^16−1 clamped, no wrap; cell order y then x ascending), each
	 * cell in winning order, deduplicated by id keeping the first occurrence. A cell row whose id is unknown to
	 * zones.json or whose version differs is skipped and reported once per id in OutWarnings (nullptr = don't collect).
	 */
	void CollectAround(int32 InCenterX, int32 InCenterY, int32 InRadius, TArray<FGolmokZoneIndexCellRef>& OutRefs,
		TArray<FString>* OutWarnings = nullptr);

	/** Drop cached cells outside the 3x3 around (InKeepX, InKeepY) when more than InMaxCells are cached (long walks). */
	void TrimCache(int32 InKeepX, int32 InKeepY, int32 InMaxCells);

	int32 NumCachedCells() const { return Cells.Num(); }
	int32 NumMissingCells() const;                 // cached cells with bFromFile == false
	int32 NumFileReads() const { return FileReads; }   // test hook: GetCell twice == one read
	/** golmok.zone.index cell block for the 3x3 around the center (§6). */
	FString Describe(int32 InCenterX, int32 InCenterY, int32 InRadius);
	void Reset();

private:
	FReadFile Reader;
	FString IndexDir;
	TArray<FGolmokZoneIndexEntry> Entries;
	TMap<FString, int32> ById;
	TMap<FString, FGolmokZoneIndexCell> Cells;     // key = CellKey
	TSet<FString> WarnedCells;                     // missing / broken cell files warned once (key)
	TSet<FString> WarnedIds;                       // unknown / mismatched cell rows warned once
	int32 FileReads = 0;
	bool bLoaded = false;
};
```
JSON 접근은 V-03 확정대로 `FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root)` + `const FString` 키 객체로 `TryGetArrayField/TryGetNumberField/TryGetStringField/TryGetObjectField`. `Values` 순회는 하지 않는다. `.cpp` 익명 namespace 헬퍼는 `IndexJson*` 접두(유니티 빌드 충돌 방지). 없는 파일: `bFromFile=false`, 빈 목록, **Log 1회**(셀 키 기준; `write_index`는 zone이 있는 셀만 쓰므로 "없음"이 정상). 파싱 실패: `Error` 보관 + **Warning 1회**.

#### 3-3 `Zones/GolmokZoneSubsystem.h` 확장 (include 추가: `Engine/StreamableManager.h`, `Zones/GolmokZoneIndex.h`)
```cpp
/** Who asked for RequestLoad / RequestUnload: portals own their interior zones (never distance-managed, never "blocked"). */
UENUM()
enum class EGolmokZoneRequestSource : uint8 { Console, Portal, Discovery };   // Discovery reserved (logs only)

USTRUCT()
struct FGolmokZoneRecord
{
	… (기존 필드 그대로) …
	/** A portal loaded / unloaded this zone: excluded from the distance rules and shown as "portal" instead of "blocked". */
	bool bPortalManaged = false;
	/** Discovered zone with a level-placed twin (same id): destroyed by the next DiscoverZones() once Unloaded and not pinned. */
	bool bRetirePending = false;
	/** World time when this discovered zone first met every despawn condition; < 0 while it does not. */
	double DespawnEligibleSince = -1.0;
};

// UGolmokZoneSubsystem — Config (두 줄 선언, ini 키와 1:1)
	/** Discover zones from Content/Golmok/Zones/index around the player (WP-09). Silently off when zones.json is missing or the level has no AGolmokGeoOrigin. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone|Index")
	bool bDiscoverFromIndex = true;

	/** Seconds between index lookups (inside the Evaluate timer, before Evaluate; never per frame). Minimum UpdateIntervalSeconds. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone|Index")
	float DiscoveryIntervalSeconds = 2.f;

	/** A discovered, unloaded zone outside the 3x3 cells and farther than this (m) is destroyed. 0 = 2 x UnloadRadiusM (computed when used). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone|Index")
	float DespawnDistanceM = 0.f;

	/** The despawn conditions must hold this long (s) before a discovered zone is destroyed (no spawn / destroy thrash at cell borders). */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone|Index")
	float DespawnGraceSeconds = 10.f;

// public API (기존 호출자는 기본 인자로 그대로 컴파일)
	bool RequestLoad(const FString& ZoneId, bool bPin, FString& OutMessage, EGolmokZoneRequestSource Source = EGolmokZoneRequestSource::Console);
	bool RequestUnload(const FString& ZoneId, FString& OutMessage, EGolmokZoneRequestSource Source = EGolmokZoneRequestSource::Console);
	/** One discovery step (spawn / despawn / retire from the index). Public for golmok.zone.index and tests; never called from Evaluate(). */
	void DiscoverZones();
	/** Re-read zones.json, drop the cell cache, discover now (golmok.zone.index reload). */
	void ReloadIndex();
	/** bDiscoverFromIndex && zones.json parsed && the world is a game world. */
	bool IsDiscoveryActive() const;
	/** Version for ZoneId: a registered actor's Version (placed first), else the index entry's, else 0 (AGolmokPortal::Configure). */
	int32 ResolveZoneVersion(const FString& ZoneId) const;
	bool IsZoneInIndex(const FString& ZoneId) const { return Index.FindZone(ZoneId) != nullptr; }
	float GetDespawnDistanceM() const { return DespawnDistanceM > 0.f ? DespawnDistanceM : 2.f * UnloadRadiusM; }
	FStreamableManager& GetStreamable() { return Streamable; }
	const FGolmokZoneIndex& GetIndex() const { return Index; }
	int32 NumDiscovered() const;   // records whose zone has bSpawnedFromIndex
	int32 NumLoading() const;      // records whose zone IsLoading()
	/** True while Evaluate() / RequestLoad() / RequestUnload() hold FGolmokZoneRecord pointers across Load() / Unload(). */
	bool IsHoldingRecordPointers() const { return PointerHoldDepth > 0; }
	/** Forbidden entries (RegisterZone / UnregisterZone / RequestLoad / RequestUnload / DiscoverZones / async finish) seen while holding pointers. Tests assert 0. */
	int32 GetReentrancyViolations() const { return ReentrancyViolations; }
	/** AGolmokZone::FinishAsyncLoad() calls this first: counts a violation (Error log) when pointers are held. */
	void NoteAsyncFinish(const AGolmokZone* Zone);
	/** golmok.zone.index body (§6). */
	FString DescribeIndex();
	/** First placed actor with this id, else the first discovered one (placed wins). */
	AGolmokZone* FindZone(const FString& ZoneId) const;

private:
	/** Timer callback: DiscoverZones() when due, then Evaluate(). The only place both run in one stack, discovery first. */
	void OnEvaluateTimer();
	AGolmokZone* SpawnDiscoveredZone(const FString& InZoneId, int32 InVersion);
	bool GetPlayerCell(int32& OutX, int32& OutY, double& OutLon, double& OutLat) const;   // GetPlayerLocation + Geo->LevelUEToLonLat + LonLatToCell
	/** ++ReentrancyViolations + UE_LOG Error "<Op> called while zone record pointers are held" when PointerHoldDepth > 0. */
	void CheckNotHoldingPointers(const TCHAR* Op);

	FStreamableManager Streamable;      // value member (UAssetManager pattern); handles cancelled in Deinitialize before it dies
	FGolmokZoneIndex Index;
	double NextDiscoverySeconds = 0.0;
	int32 LastCellX = -1;
	int32 LastCellY = -1;
	int32 PointerHoldDepth = 0;
	int32 ReentrancyViolations = 0;
	bool bWarnedNoGeoOrigin = false;
	TSet<FString> WarnedShadowedIds;    // "placed v1 shadows index v2" once per id
	static constexpr int32 MaxSpawnsPerDiscovery = 8;
	static constexpr int32 MaxDestroysPerDiscovery = 4;
	static constexpr int32 MaxCachedCells = 64;
```
- `Initialize()`: 기존 + `DiscoveryIntervalSeconds = FMath::Max(DiscoveryIntervalSeconds, UpdateIntervalSeconds)`; `if (DespawnDistanceM > 0.f && DespawnDistanceM < UnloadRadiusM) { Warning; DespawnDistanceM = UnloadRadiusM; }`; `DespawnGraceSeconds = FMath::Max(0.f, DespawnGraceSeconds)`; `Streamable.SetManagerName(FString::Printf(TEXT("GolmokZones:%s"), *GetWorld()->GetName()))`(§10 #14).
- `OnWorldBeginPlay()`: 기존 스윕 뒤 `if (bDiscoverFromIndex) { FString Err; if (!Index.Load(FGolmokZoneIndex::DefaultIndexDir(), Err)) Log(Err.IsEmpty() ? "no zone index at <path>; discovery off" : Warning Err); }`, `NextDiscoverySeconds = 0`, 타이머 대상 **`&UGolmokZoneSubsystem::OnEvaluateTimer`**(주기 `UpdateIntervalSeconds` 그대로).
- `OnEvaluateTimer()` 본문은 정확히: `const double Now = GetWorld()->GetTimeSeconds(); if (IsDiscoveryActive() && Now >= NextDiscoverySeconds) { NextDiscoverySeconds = Now + DiscoveryIntervalSeconds; DiscoverZones(); } Evaluate();` `CmdZoneRefresh`도 `RefreshBasemap(); DiscoverZones(); Evaluate();`.
- `Deinitialize()`: **먼저** `for (R : Zones) if (AGolmokZone* Z = R.Zone.Get()) Z->CancelAsyncLoad();` → 델리게이트 해제 → 타이머 해제 → `RestoreAllBasemap()` → 배열 비움 → `Index.Reset()` → `Super`. 발견 액터는 파괴하지 않는다(월드가 지운다).
- `RegisterZone`: `CheckNotHoldingPointers(TEXT("RegisterZone"))`; "placed twice" Warning은 **같은 `bSpawnedFromIndex` 값끼리만**; 새 액터가 배치이고 같은 id의 발견 레코드가 있으면 그 레코드에 `bRetirePending = true`(배열 변경·Destroy 금지 — BeginPlay 스택). `Record.bPortalManaged=false; DespawnEligibleSince=-1`.
- `UnregisterZone`: `CheckNotHoldingPointers(TEXT("UnregisterZone"))` 뒤 기존.
- `RequestLoad(Id, bPin, Msg, Source)`: `CheckNotHoldingPointers(TEXT("RequestLoad"))`; 기존 검색; `R->bBlocked=false; R->bLoadFailed=false; R->bPinned=bPin; R->bPortalManaged = (Source == Portal);` `Zone->SetAsyncLoadPriority(bPin ? FStreamableManager::AsyncLoadHighPriority : FStreamableManager::DefaultAsyncLoadPriority)`; `++PointerHoldDepth; const bool bOk = Zone->Load(); --PointerHoldDepth;` 실패면 기존; 성공 `Msg = "zone %s loading%s" | "zone %s loaded%s"`(`%s` = ` (pinned)`).
- `RequestUnload(Id, Msg, Source)`: `CheckNotHoldingPointers(TEXT("RequestUnload"))`; `R->bPinned=false; if (Source == Portal) R->bPortalManaged = true; else { R->bBlocked = true; R->bPortalManaged = false; }` `const bool bWasLoading = Zone->IsLoading(); ++PointerHoldDepth; Zone->Unload(); --PointerHoldDepth;` `Msg = bWasLoading ? "zone %s load cancelled" : (Portal ? "zone %s unloaded (portal)" : 기존 문구)`.
- `Evaluate()`: 본문 첫 줄 `++PointerHoldDepth`, 모든 return 경로에서 `--PointerHoldDepth`(구조체 `FPointerHoldScope { int32& D; … }` RAII, 참조 멤버·`TOptional` 없이 함수 첫 줄에 스코프 객체 1개). 변경 diff는 §4-5.
- `DescribeZones()`: 헤더 `"%d zones (load < %.0f m, unload > %.0f m), %d basemap actors tagged, %d discovered, %d loading\n"`(기존 접두 바이트 동일). 행: 상태 열에 `loading`, 기존 접미 뒤에 ` portal`(`bPortalManaged`), ` (loading %.1f s)`(`IsLoading()`), 마지막 ` [index]`/` [placed]`. ` blocked`는 `bBlocked`일 때만.
- 콘솔 `golmok.zone.index [reload]`: 익명 namespace `CmdZoneIndex` + `FAutoConsoleCommandWithWorldAndArgs GCmdZoneIndex(TEXT("golmok.zone.index"), …)`(13번째; 기존 12개 이름 불변). 출력 §6.

#### 3-4 `Zones/GolmokZone.h` 확장 (include 추가: `Engine/StreamableManager.h`, `UObject/SoftObjectPath.h`)
```cpp
UENUM(BlueprintType)
enum class EGolmokZoneState : uint8 { Unloaded, Loaded, Failed, Loading };   // Loading appended (existing values unchanged)

// public
	/** Stream chunk / collision assets through UGolmokZoneSubsystem's FStreamableManager (state Loading; components built next tick after completion). False = WP-04 synchronous StaticLoadObject path. Editor worlds are always synchronous. */
	UPROPERTY(Config, EditAnywhere, Category = "Golmok|Zone|Streaming")
	bool bAsyncLoad = true;

	/** Spawned by UGolmokZoneSubsystem::DiscoverZones from the Zone Index (transient; a level-placed actor with the same id wins). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category = "Golmok|Zone|State")
	bool bSpawnedFromIndex = false;

	/** Asynchronous loads completed since BeginPlay (test hook). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category = "Golmok|Zone|State")
	int32 AsyncLoadCount = 0;

	UFUNCTION(BlueprintCallable, Category = "Golmok|Zone")
	bool IsLoading() const { return State == EGolmokZoneState::Loading; }
	bool IsLoadedOrLoading() const { return State == EGolmokZoneState::Loaded || State == EGolmokZoneState::Loading; }
	/** Seconds since LoadAsync() issued the request; 0 when not loading. */
	double GetLoadingSeconds() const;
	/** Priority for the next LoadAsync(): FStreamableManager::AsyncLoadHighPriority for pinned (portal / console) loads. */
	void SetAsyncLoadPriority(int32 InPriority) { AsyncPriority = InPriority; }
	/** Cancel an in-flight async load (no-op otherwise): timer cleared, serial bumped, handle cancelled, Loading -> Unloaded. */
	void CancelAsyncLoad();
	/** Chunk (nanite_mesh) / collision object paths whose package exists (FPackageName::DoesPackageExist); OutMissing counts the rest. */
	TArray<FSoftObjectPath> CollectAssetPaths(int32& OutMissing) const;
	bool IsFinishPending() const { return bFinishPending; }

// protected
	/** Mesh for a manifest object path. Inside FinishAsyncLoad (bAssetsPreloaded) FSoftObjectPath::ResolveObject() first; otherwise
	 *  nullptr when the package does not exist (no StaticLoadObject probe, no flush), else LoadMeshAsset(). Virtual for D-010 formats. */
	virtual UStaticMesh* AcquireMeshAsset(const FString& ObjectPath);
	/** Issue the streamable request. False when nothing can be requested (no existing package / no handle): Load() continues synchronously. */
	bool LoadAsync();
	/** Streamable completion (weak lambda target). Only records bFinishPending and schedules FinishAsyncLoad for the next tick. */
	void OnStreamableComplete(uint32 InSerial);
	/** Next-tick timer target, the ONLY Loading -> Loaded path: build the layers from resident assets, SpawnPortals, NotifyZoneLoaded. */
	void FinishAsyncLoad();

// private
	TSharedPtr<FStreamableHandle> LoadHandle;
	FTimerHandle AsyncFinishTimer;
	uint32 AsyncSerial = 0;            // bumped by every request and every cancel
	uint32 PendingFinishSerial = 0;    // serial the pending FinishAsyncLoad belongs to
	int32 AsyncPriority = 0;           // FStreamableManager::DefaultAsyncLoadPriority
	double AsyncStartSeconds = 0.0;
	bool bFinishPending = false;       // OnStreamableComplete ran, FinishAsyncLoad not yet
	bool bAssetsPreloaded = false;     // true only during FinishAsyncLoad's Build* calls
	bool bWarnedHandleIncomplete = false;
```
`bWarnedAsync` 멤버와 `Load()` 위 TODO 주석은 삭제. `LoadMeshAsset`(정적)은 유지하고 `BuildVisualLayer/BuildCollisionLayer`의 호출을 `AcquireMeshAsset(...)`로 바꾼다. `DescribeZones` 상태 텍스트: `loaded / loading / FAILED / unloaded`.

#### 3-5 `Portals/GolmokPortal.h` 변경
```cpp
// public
	/** RequestLoad(TargetZoneId, pinned, Portal) was issued for the current Pending / Active cycle (this portal owes the interior an unload). */
	UPROPERTY(VisibleAnywhere, Transient, Category = "Golmok|Portal|State")
	bool bInteriorRequested = false;
	/** Active / Leaving, or Pending after the interior was requested. Widens EndPlay, LeaveInterior and IsInteriorZoneInUse. */
	bool IsHoldingInterior() const { return State == EGolmokPortalState::Active || State == EGolmokPortalState::Leaving || (State == EGolmokPortalState::Pending && bInteriorRequested); }

// private
	/** Next tick after Idle -> Pending (PreloadTimer): RequestInterior() while still Pending, so the async load starts before the debounce ends. Never on the overlap-callback stack. */
	void PreloadInterior();
	/** RequestLoad(TargetZoneId, true, Msg, Portal) once per cycle; sets bInteriorRequested / InteriorRequestSeconds. False when there is no zone subsystem. */
	bool RequestInterior(FString& OutZoneMsg);
	/** Interior zone Loaded, or absent / Failed / timed out (InteriorLoadTimeoutSeconds) -> ready to StreamIn. Loading -> false ("interior loading"). */
	bool IsInteriorReady(FString& OutWhy) const;
	/** StreamIn + State = Active + log: the second half of the old Activate(). */
	void CompleteActivation(const FString& ZoneMsg);
	FTimerHandle PreloadTimer;
	double InteriorRequestSeconds = 0.0;
```
`.cpp` 익명 namespace 상수: `constexpr float InteriorLoadPollSeconds = 0.05f; constexpr float InteriorLoadTimeoutSeconds = 10.f;`(Config 키 아님 — WP-05 `EXPECTED_KEYS` 유지). `EndPlay`는 `DebounceTimer`·`UnloadTimer`에 더해 `PreloadTimer`도 해제한다. `IsInteriorZoneInUse` 술어: `Other.IsHoldingInterior()`. `HasPendingSibling` 술어: `Other.State == Pending && !Other.bInteriorRequested`(요청한 Pending은 이미 "in use"). 모든 `RequestLoad/RequestUnload` 호출(`UnloadInteriorAfterEndPlay`·`OnUnloadDelayElapsed` 포함)에 `EGolmokZoneRequestSource::Portal`. `Configure()`: `TargetVersion = Subsystem ? FMath::Max(1, Subsystem->ResolveZoneVersion(P.ToZone)) : 1`. `Describe()`: Pending && bInteriorRequested → `"pending(loading %.1f s)"`. 전이는 §4-2.

#### 3-6 Debug
`Debug/GolmokStatsMath.h` 추가(허용 7헤더 안, g++ 검증):
```cpp
	/** V-03: a 0 (or negative / NaN) render-thread reading means "not sampled yet", not "free": keep the last positive value. */
	struct HeldValue
	{
		double Value = 0.0;           // 0 until the first positive sample
		bool bHeldLast = false;       // the last Feed kept the previous value
		std::size_t HeldCount = 0;    // samples that were held
		std::size_t Total = 0;        // samples fed
		void Reset() { Value = 0.0; bHeldLast = false; HeldCount = 0; Total = 0; }
	};
	inline double HoldLastPositive(HeldValue& State, double Sample)
	{
		++State.Total;
		if (Sample > 0.0) { State.Value = Sample; State.bHeldLast = false; }   // NaN fails the comparison -> held
		else { State.bHeldLast = true; ++State.HeldCount; }
		return State.Value;
	}
```
`Debug/GolmokDebugSubsystem.h/.cpp`:
```cpp
// .cpp 상단 (GOLMOK_GPU_TIME_SOURCE 옆)
// Render-thread time source for the HUD (WP-09 design §6-1).
//   0 = GRenderThreadTime read in OnEndFrame (WP-05 behaviour; V-03 saw 0.00 often)
//   1 = GRenderThreadTime read in OnBeginFrame (the previous frame's settled value), applied in OnEndFrame  [default]
//   2 = GRenderThreadTimeCriticalPath read in OnBeginFrame (RenderTimer.h; set 1 if the symbol is missing)
// Whatever the source, a 0 sample keeps the last positive value (GolmokStatsMath::HoldLastPositive).
#define GOLMOK_RENDER_TIME_SOURCE 1
// .h
	void OnBeginFrame();                                   // caches RenderCyclesAtBeginFrame (source 1 / 2)
	/** "render source 1: begin 12345 cycles, end 0 cycles, held 3/120 frames (window)" — golmok.stats second line, runbook §7. */
	FString DescribeRenderSource() const;
	FDelegateHandle BeginFrameHandle;
	GolmokStatsMath::HeldValue RenderHold;
	uint32 RenderCyclesAtBeginFrame = 0;
```
`BindSampler(bOn)`: `OnEndFrame` 바인딩 그대로 + `BeginFrameHandle = FCoreDelegates::OnBeginFrame.AddUObject(this, &UGolmokDebugSubsystem::OnBeginFrame)`(해제 쌍). `OnEndFrame()`: `raw = (SOURCE == 0) ? GRenderThreadTime : RenderCyclesAtBeginFrame`; `RenderMs = HoldLastPositive(RenderHold, CyclesToMs(raw))`; 나머지 동일 → `PushFrameSample`. `FormatStatsLine()`·HUD 줄·`PushFrameSample` 무변경(`Golmok.Debug.HudStats` 유지). `CmdStats`가 `FormatStatsLine()` 뒤 `DescribeRenderSource()`를 두 번째 Log 줄로 찍는다.

#### 3-7 Python
`Content/Python/golmok/zone_index.py`(에디터 API 사용은 `unreal.Paths.project_content_dir()`, `unreal.log/log_warning`뿐):
```python
"""Copy a Zone Index (golmok-zone index build) into Content/Golmok/Zones/index (spec §6 "게임 내 위치")."""
INDEX_REL = "Golmok/Zones/index"
class ZoneIndexError(zone_import.ZoneImportError):   # str() = "zone_index: ERROR <step>: <message>"
    log_key = "zx.error"
def plan(zones_root, index_dir=None) -> dict:
    """index_dir default <zones_root>/index. Read zones.json + cells/*.json (sorted), _pure.check_index -> problems ->
    ZoneIndexError('plan', 'zones.json not found …') | ZoneIndexError('check', '; '.join(problems)). Nothing written.
    Returns {'index_dir', 'zones': doc, 'cells': {name: doc}}."""
def sync(zones_root, index_dir=None, content_dir=None) -> dict:
    """plan() -> _pure.index_sync_plan -> byte copy (shutil.copyfile) zones.json + cells -> remove stale dest cells ->
    _pure.index_missing_manifests warning. content_dir default unreal.Paths.project_content_dir().
    Logs zx.plan, zx.copied, zx.removed (n > 0 only), zx.missing (n > 0 only), zx.done.
    Returns {'dest', 'zones': n, 'cells': k, 'removed': [...], 'missing': [...]}."""
def describe(content_dir=None) -> str:   # "index: 3 zones, 4 cells at <dest>" | "index: none at <dest>"
```
`_pure.py` 추가(순수, `unreal`·numpy 미사용):
```python
INDEX_DIR_NAME = "index"; INDEX_ZONES_NAME = "zones.json"; INDEX_CELLS_DIR = "cells"; INDEX_CELL_ZOOM = 16
CELL_NAME_RE = re.compile(r"^(?P<z>\d+)_(?P<x>\d+)_(?P<y>\d+)\.json$")
def zones_root_of(zone_dir: str) -> str                      # '.../zones/<id>[/v<n>]' -> '.../zones' (os.path.normpath)
def parse_cell_name(name: str) -> tuple[int, int, int] | None   # '16_55873_25379.json' -> (16, 55873, 25379); '16_-1_2.json' -> None
def cell_name(z: int, x: int, y: int) -> str                 # == golmok_tools.zone.index.cell_name
def check_index(zones_doc: dict, cells: dict[str, dict]) -> list[str]
    # zones.json: schema_version == 1, cell_zoom == 16, zones list; id ZONE_ID_RE, version >= 1, kind in {exterior, interior},
    # priority int, bbox 4 numbers w <= e / s <= n, manifest == f"{id}/v{version}/manifest.json", unique ids, id-sorted.
    # cells: name parses and == (z, x, y) inside, z == 16, every (id, version) in zones.json with the same version, unique ids.
def index_sync_plan(index_dir: str, content_dir: str, source_cells: list[str], dest_cells: list[str]) -> dict
    # {'dest': <content>/Golmok/Zones/index, 'copy': [(src, dst), ...] (zones.json first, then sorted cells), 'remove': [dst, ...]}
def index_missing_manifests(zones_doc: dict, exists) -> list[str]   # ids whose <root>/<id>/v<n>/manifest.json exists(...) is False
LOG += {
    "zx.plan": "zone_index: plan {zones} zones, {cells} cells from {index_dir}",
    "zx.copied": "zone_index: copied zones.json + {cells} cells -> {dest}",
    "zx.removed": "zone_index: removed {n} stale cell files ({names})",
    "zx.missing": "zone_index: WARNING {n} indexed zones have no manifest under Content yet ({ids})",
    "zx.warn": "zone_index: WARNING {message}",
    "zx.error": "zone_index: ERROR {step}: {message}",
    "zx.done": "zone_index: done {zones} zones, {cells} cells -> {dest}",
}
```
`zone_import.run(zone_dir, version=None, level=None, geo_origin=None, save=True, remeasure=False, reimport_textures=True, with_index=False)`: `True`면 zone 리빌드 **뒤**·저장 **앞**에 `_step("index")` 안에서 `zone_index.sync(_pure.zones_root_of(plan["zone_dir"]))`, 결과 `result["index"]`(없으면 `None`); index 폴더가 없으면 `zx.warn` 1회(실패 아님). `_pure.result_json`에 `index` 키.
`tools/golmok_tools/zone/index.py`: `INDEX_DIR_NAME = "index"`; `scan_zones` 루프 첫 줄 `if zdir.name == INDEX_DIR_NAME: continue`(경고 없음).
`tools/scripts/make_synthetic_zone.py --offset-m E,N`: `ZONE_ORIGIN`을 `transform.enu_to_lonlat([[E, N, 0]], ZONE_ORIGIN)`로 옮긴 뒤(높이 유지, 소수 7자리 반올림) 기존 흐름; 기본 `0,0`은 출력 불변(`test_deterministic_and_check_mode`).
`tools/scripts/make_index_fixture.py`: `msz.main(["--out", tmp, "--zone-id", "z_synthetic_002", "--offset-m", "200,0", "--quiet"])` → `zones/z_synthetic_002/v1/{manifest.json, blockers.json}`만 두 사본으로 복사(에셋·recon 제외) → 임시 zones 루트(픽스처 001·001_interior·002)에 `index.build_index` → `write_index`를 `fixtures/zones/index/`와 `Content/Golmok/Zones/index/`에 → `--check`는 임시 재생성 후 정렬 `rglob` 바이트 비교(exit 1 on diff).

### 4. 상태기계·전이표

#### 4-1 `EGolmokZoneState` 전이 (`Loading` 추가; 그 외 WP-04 그대로)
| 현재 | 이벤트 | 조건 | 다음 | 부수효과 |
|---|---|---|---|---|
| Unloaded/Failed | `Load()` | `EnsureManifest` 실패 | Failed | `LastError` |
| Unloaded/Failed | `Load()` | `bAsyncLoad && 서브시스템 && IsGameWorld && !bIsTearingDown && LoadAsync()==true` | **Loading** | `++AsyncSerial`, `LoadHandle`, `AsyncStartSeconds`, 로그 "async load requested (N assets, M missing, priority P)" |
| Unloaded/Failed | `Load()` | 그 외(동기: 플래그 off, 에디터, 존재 패키지 0개, 핸들 null) | Loaded | WP-04 §4-1 3~6단계 그대로(`AcquireMeshAsset`이 없는 패키지는 `StaticLoadObject` 없이 null) |
| Loading | `Load()` | – | Loading | no-op, `true`(중복 요청 없음) |
| Loading | `OnStreamableComplete(S)` | `S == AsyncSerial && !bFinishPending` | Loading | `bFinishPending=true; PendingFinishSerial=S; AsyncFinishTimer = SetTimerForNextTick(FinishAsyncLoad)` — **항상 미룸** |
| Loading | `OnStreamableComplete(S)` | 세대 불일치 / 이미 pending / State≠Loading | (불변) | 무시(취소·재요청·지연 발화) |
| Loading | `FinishAsyncLoad()` | `bFinishPending && PendingFinishSerial == AsyncSerial && !bIsTearingDown` | **Loaded** | `NoteAsyncFinish`, Build*(ResolveObject), `LoadHandle.Reset()`, `SpawnPortals`, `++AsyncLoadCount`, 로그 "loaded (async %.1f ms wait + %.1f ms build)", `NotifyZoneLoaded` |
| Loading | `FinishAsyncLoad()` | 그 외 | (불변 / 티어다운이면 `CancelAsyncLoad`) | 무시 |
| Loading | `Unload()`·`CancelAsyncLoad()`(Evaluate 반경 밖·고아·RequestUnload·EndPlay·retire·Deinitialize) | – | Unloaded | `ClearTimer(AsyncFinishTimer)`, `++AsyncSerial`, `bFinishPending=false`, `CancelHandle()`+`Reset()`, 로그 "async load cancelled after %.1f ms"; **`NotifyZoneUnloaded` 없음** |
| Loaded | `Unload()` | – | Unloaded | WP-04 그대로(`CancelAsyncLoad`는 no-op) |
| any | `EndPlay` | – | Unloaded | 기존 순서 `UnregisterZone` → `Unload()`(취소 포함) |

`Load()` 반환값: `true` = Loaded **또는 Loading 시작**, `false` = Failed. 호출자: `Evaluate`(bChanged), `RequestLoad`("loading"/"loaded"), `RebuildInEditor`(에디터 → 항상 동기). zone 쪽 Loading 타임아웃은 두지 않는다(멈춘 요청은 `golmok.zone.unload`가 취소하고 목록의 ` (loading %.1f s)`가 드러낸다; 포털 쪽은 10 s 상수).

#### 4-2 포털 상호작용 (WP-05 enum `Idle/Pending/Active/Leaving` 불변; Loading 관련 행만)
| 포털 상태 | 이벤트 | 실내 zone | 결과 |
|---|---|---|---|
| Idle | `BeginPlayerOverlap` | – | Pending, `bInteriorRequested=false`, `DebounceTimer`, **`PreloadTimer = SetTimerForNextTick(PreloadInterior)`** |
| Pending | `PreloadInterior`(다음 틱) | 등록됨 | `RequestInterior` → `RequestLoad(pin, Portal)` → zone Loading(또는 즉시 Loaded), `bInteriorRequested=true`, `LastEvent="interior preload requested"` |
| Pending | `PreloadInterior` | 미등록(index에 있고 아직 스폰 전 / 없음) | 요청 안 함(`bInteriorRequested` 유지 false); 디바운스 때 다시 시도 |
| Pending | `OnDebounceElapsed` | 밖·안 아님, 요청 전 | Idle(기존) |
| Pending | `OnDebounceElapsed` | 밖·안 아님, **요청 후** | `State=Active; StartLeaving("left before interior loaded")` → Leaving → 3 s → `RequestUnload(Portal)`(Loading이면 취소) |
| Pending | `OnDebounceElapsed` | `!bInteriorRequested` | `RequestInterior` 먼저 |
| Pending | `OnDebounceElapsed` | `IsInteriorReady`: Loaded / 없음(index에도 없거나 타임아웃) / Failed / 타임아웃(Warning "interior still loading after %.1f s; activating anyway") | `CompleteActivation` → StreamIn + **Active** |
| Pending | `OnDebounceElapsed` | **Loading**(또는 index에 있는데 스폰 대기, 경과 < 10 s) | **Pending 유지**, `LastEvent="interior loading"`, `DebounceTimer` 재무장 `TimerRate(0.05)` |
| Pending | `EndPlayerOverlap` 바깥, `!bPlayerInside` | 요청 후 | `State=Active; StartLeaving("left trigger outward while interior loading")`(요청 전은 기존 Idle) |
| Pending(요청 후) | `LeaveInterior` | – | 폴링 타이머 해제 → `State=Active; StartLeaving` |
| Pending(요청 후) | `EndPlay` | – | `IsHoldingInterior()` → `StreamOut`(no-op) + 다음 틱 `UnloadInteriorAfterEndPlay`(pin 반납) |
| Active/Leaving | 기존 전이 | Loading | WP-05 그대로; `OnUnloadDelayElapsed`의 `RequestUnload(Portal)`가 Loading이면 취소 |
| Leaving/EndPlay | `IsInteriorZoneInUse` | – | 다른 포털이 `IsHoldingInterior()`면 소유권 이전(기존 규칙 확장) |
| Idle→Pending / Leaving→Idle(`OnUnloadDelayElapsed`) | – | – | `bInteriorRequested=false` |
| Idle | `golmok.portal enter`(`EnterInterior`→`Activate`) | Loading | `RequestInterior` + `IsInteriorReady ? CompleteActivation : (Pending 유지 + 폴링)`; 메시지에 "loading; activates when ready" |

`bAsyncLoad=False`면 `RequestLoad` 직후 `IsLoaded()`라 디바운스 끝에 즉시 `CompleteActivation` → WP-05와 같은 타이밍. 포털 폴더는 여전히 `RegisterZone(`·`->Load(`·`->Unload(`를 직접 부르지 않는다.

#### 4-3 발견·파괴·retire 규칙 (`DiscoverZones()`, 후보 수집 → 실행)
```
if (!IsDiscoveryActive() || !World || World->bIsTearingDown || !World->HasBegunPlay()) return;
CheckNotHoldingPointers(TEXT("DiscoverZones"));
int32 CX, CY; double Lon, Lat; if (!GetPlayerCell(CX, CY, Lon, Lat)) { GeoOrigin 없음 → Warning 1회; return; }
LastCellX = CX; LastCellY = CY; Index.TrimCache(CX, CY, MaxCachedCells);
TArray<FGolmokZoneIndexCellRef> Near; TArray<FString> Warnings; Index.CollectAround(CX, CY, 1, Near, &Warnings);  // Warnings: Log 1회씩
PruneInvalid();
// 1) 후보 수집 (Zones를 읽기만; 포인터 보유 없음)
TSet<FString> NearIds; for (Ref : Near) NearIds.Add(Ref.Id);
TArray<TWeakObjectPtr<AGolmokZone>> ToRetire, ToDespawn; TArray<FGolmokZoneIndexCellRef> ToSpawn;
const double Now = World->GetTimeSeconds(); FVector P; GetPlayerLocation(P); const FVector2D PXY(P.X, P.Y);
for (FGolmokZoneRecord& R : Zones) {
    AGolmokZone* Z = R.Zone.Get(); if (!Z || !Z->bSpawnedFromIndex) continue;
    const bool bTwin = R.bRetirePending || (같은 id의 !bSpawnedFromIndex 레코드 존재);
    const bool bIdle = Z->State == EGolmokZoneState::Unloaded && !R.bPinned;
    if (bTwin) { R.bRetirePending = true; if (bIdle) ToRetire.Add(Z); continue; }          // Loaded/Loading/pinned 쌍둥이는 다음 패스
    bool bParentBusy = false;
    if (Z->IsInterior() && !Z->GetParentZoneId().IsEmpty()) if (const AGolmokZone* Parent = FindZone(Z->GetParentZoneId())) bParentBusy = Parent->IsLoadedOrLoading();
    const double D = Z->HasManifest() ? Z->DistanceToFootprintM(PXY) : 1.0e9;
    const bool bEligible = bIdle && !NearIds.Contains(Z->ZoneId) && D > GetDespawnDistanceM() && !bParentBusy;
    if (!bEligible) { R.DespawnEligibleSince = -1.0; continue; }
    if (R.DespawnEligibleSince < 0.0) { R.DespawnEligibleSince = Now; continue; }
    if (Now - R.DespawnEligibleSince >= DespawnGraceSeconds) ToDespawn.Add(Z);
}
for (Ref : Near) if (!FindZone(Ref.Id)) ToSpawn.Add(Ref);        // 배치든 발견이든 등록된 id는 스킵 (배치 v≠index v: WarnedShadowedIds Log 1회)
// 2) 실행 (Zones 순회 없음; 각 호출이 배열을 바꿔도 잡아둔 포인터가 없다)
for (W : ToRetire) if (AGolmokZone* Z = W.Get()) { Log "zone %s: placed actor wins; discovered actor destroyed"; Z->Destroy(); }
int32 Destroyed = 0; for (W : ToDespawn) if (Destroyed < MaxDestroysPerDiscovery) if (AGolmokZone* Z = W.Get()) { Log "zone %s despawned (index; %.0f m, cells far)"; Z->Destroy(); ++Destroyed; }
int32 Spawned = 0; for (Ref : ToSpawn) if (Spawned < MaxSpawnsPerDiscovery && SpawnDiscoveredZone(Ref.Id, Ref.Version)) ++Spawned;
if (Spawned || Destroyed || ToRetire.Num()) Log "discovery: cell 16/%d/%d, 3x3 zones %d, spawned %d, destroyed %d, retired %d, actors %d";
```
`SpawnDiscoveredZone(InZoneId, InVersion)`: `FActorSpawnParameters Params; Params.ObjectFlags = EObjectFlags(Params.ObjectFlags | RF_Transient); Params.SpawnCollisionHandlingOverride = AlwaysSpawn; Params.bDeferConstruction = true;`(`Params.Name` 없음) → `World->SpawnActor<AGolmokZone>(AGolmokZone::StaticClass(), FTransform::Identity, Params)` → `ZoneId = InZoneId; Version = FMath::Max(1, InVersion); bSpawnedFromIndex = true;` → `#if WITH_EDITOR SetActorLabel("Zone_<id> (index)"); SetFolderPath(TEXT("Golmok/Zones/Discovered")); #endif` → `FinishSpawning(FTransform::Identity)`(BeginPlay → `RegisterZone`, Evaluate 밖) → Log "zone %s v%d discovered from index (cell 16/%d/%d)". manifest는 다음 `Evaluate()`의 기존 `EnsureManifest` 경로가 읽는다(배치 zone과 동일; 실패 → `bLoadFailed` + Error 1회 = Content에 manifest가 없는 index 항목이 드러나는 자리, `zx.missing`이 미리 경고). 실내도 발견한다(footprint가 실외 안이라 같은 셀; `bAutoManageInterior=False`면 거리 관리 대상이 아니고 포털이 `ResolveZoneVersion`·`RequestLoad`로 쓴다). `Destroy()` → `EndPlay` → `UnregisterZone` + `Unload()`(→ `CancelAsyncLoad`).

#### 4-4 `Evaluate()` 스택 규약 — 증명
규약(WP-04/05): `Evaluate()`는 `TArray<FGolmokZoneRecord*> ToLoad/ToUnload`로 `Zones` 원소 주소를 들고 `Load()/Unload()`를 부른다. 그 스택 위에서 `Zones`를 바꾸는 `RegisterZone/UnregisterZone`, 그리고 레코드 포인터를 다시 잡는 `RequestLoad/RequestUnload`, 액터를 만들거나 없애는 `DiscoverZones`가 실행되면 안 된다. 비동기 완료도 같은 스택에서 컴포넌트를 만들지 않아야 한다(스펙 완료 기준).

| 경로 | 왜 스택 밖인가 | 증명 수단 |
|---|---|---|
| 발견 스폰 `FinishSpawning → BeginPlay → RegisterZone` | `DiscoverZones()`에서만 호출되고, `OnEvaluateTimer()`가 `DiscoverZones()`를 **끝낸 뒤** `Evaluate()`가 포인터를 잡는다. 두 함수는 서로를 부르지 않는다 | 정적: `Evaluate()` 본문에 `SpawnActor/FinishSpawning/DiscoverZones(/RegisterZone(` 없음, `OnEvaluateTimer` 본문에서 `DiscoverZones(` < `Evaluate(`; 동적: `CheckNotHoldingPointers("RegisterZone")` |
| 파괴 `Destroy → EndPlay → UnregisterZone` | `DiscoverZones()` 실행 단계에서만(스냅샷 실행, `Zones` 순회 없음). `Evaluate()`는 `Unload()`만 부르고 `Destroy()`는 안 부른다 | 정적: `Evaluate()` 본문에 `Destroy(` 없음, `DiscoverZones()` 본문의 `for (… : Zones)` 안에 `Destroy(`·`SpawnActor` 없음; 동적: `CheckNotHoldingPointers("UnregisterZone")` |
| 비동기 완료 `FinishAsyncLoad` | 유일한 호출자가 `AsyncFinishTimer`(`SetTimerForNextTick`) 콜백. `OnStreamableComplete`는 플래그+타이머만. 엔진이 델리게이트를 `RequestAsyncLoad` 안(=`Load()` 스택)에서 동기로 부르든 지연 헬퍼로 부르든 컴포넌트는 다음 틱 타이머에서만 생긴다. `FTimerManager::Tick`은 콜백을 순차 실행하고 `Evaluate()`는 아무것도 펌프하지 않으므로 타이머 콜백이 `Evaluate()` 안에 중첩될 수 없다 | 정적: `LoadAsync`·`OnStreamableComplete` 본문에 `FinishAsyncLoad(` 없음(타이머 바인딩 `&AGolmokZone::FinishAsyncLoad`만), `FinishAsyncLoad` 본문에 `RegisterZone(/RequestLoad(/SpawnActor<AGolmokZone` 없음; 동적: `NoteAsyncFinish`가 `PointerHoldDepth > 0`이면 위반 |
| 동기 폴백(존재 패키지 0개) | `AcquireMeshAsset`이 없는 패키지에 `StaticLoadObject`를 부르지 않으므로 `FlushAsyncLoading` 유발 지점이 없다. 있어도 완료는 타이머로 미뤄진다 | 정적: `AcquireMeshAsset` 본문에 `DoesPackageExist(` 존재 |
| 포털 반응 | WP-05 그대로 타이머 뒤(디바운스·선로드 next tick·언로드 지연·EndPlay next tick). `BeginPlayerOverlap`이 실외 `Load()` 안(포털 BeginPlay의 수동 진입)에서 불려도 `PreloadInterior`는 다음 틱 | `test_wp05_folders_never_call_register_zone` 유지 + Portals에 `->Load(`·`->Unload(` 없음; 동적: `CheckNotHoldingPointers("RequestLoad")` |
| `NotifyZoneLoaded/Unloaded → ResolveOverlaps/UpdateBasemapHiding` | `Zones`를 읽고 플래그만 바꾼다(WP-04) — 스택 안에서 허용 | 변경 없음 |
| 콘솔 `golmok.zone.refresh/index` | 콘솔 명령 스택(타이머·Evaluate 밖) | – |

동적 카운터의 비용은 정수 비교뿐. 위반 시 `UE_LOG Error`가 자동화 테스트를 실패시키고, 5개 자동화 테스트가 끝에 `GetReentrancyViolations() == 0`을 단언한다.

#### 4-5 `Evaluate()` 변경 diff(의사코드; 포인터 사용 방식 그대로)
```
FPointerHoldScope Hold(PointerHoldDepth);                      // 첫 줄
…기존 PruneInvalid·플레이어…
for R in Zones:
  …기존 manifest 확보…
  bManaged = Zone->bAutoManaged && (!Zone->IsInterior() || bAutoManageInterior) && !R.bLoadFailed && !R.bPortalManaged && !R.bRetirePending
  if Loaded:  기존 그대로 (고아 판정만 Parent->IsLoadedOrLoading() 로 완화)
  else if Loading:                                             // 새 분기: 거리 부기 + 취소 후보만
      bFar = BoundsM >= UnloadRadiusM; if !bFar { LastDistanceM = 폴리곤; bFar = … >= UnloadRadiusM }
      if R.bBlocked && bFar: R.bBlocked = false
      orphan = 실내 && 부모 등록 && !Parent->IsLoadedOrLoading()
      if !R.bPinned && ((bManaged && bFar) || orphan): ToUnload.Add(&R)      // Unload() = 취소
  else: 기존 그대로
ToUnload/ToLoad 실행 기존 그대로 (Load()가 true를 돌려주면 bChanged=true; Loading 시작도 포함 — ResolveOverlaps는 IsLoaded()만 본다)
```
`Load()` 직전 `Zone->SetAsyncLoadPriority(FStreamableManager::DefaultAsyncLoadPriority)`(Evaluate 경로는 기본 우선순위).

### 5. 비동기 로드 흐름
```
Evaluate()/RequestLoad()  ── Zone->Load()
   EnsureManifest → DestroyOwnedComponents → MissingAssetCount=0
   bAsyncLoad && Sub && World->IsGameWorld() && !bIsTearingDown ? LoadAsync() : 동기
LoadAsync():
   Paths = CollectAssetPaths(Missing)                       // ChunkAssetPath(nanite_mesh만)·CollisionAssetPath(단일/청크별) 중 DoesPackageExist 통과, AddUnique
   if Paths.Num()==0 → return false                         // 동기 경로: 와이어 박스만, StaticLoadObject 없음
   State=Loading; AsyncStartSeconds=now; bFinishPending=false; Serial=++AsyncSerial
   FStreamableDelegate Done = FStreamableDelegate::CreateWeakLambda(this, [this, Serial]() { OnStreamableComplete(Serial); });   // 변수 선행
   LoadHandle = Sub->GetStreamable().RequestAsyncLoad(MoveTemp(Paths), Done, AsyncPriority, /*bManageActiveHandle*/ false, /*bStartStalled*/ false, FString::Printf(TEXT("GolmokZone %s v%d"), *ZoneId, Version));
   if !LoadHandle → State=Unloaded; ++AsyncSerial; Warning "RequestAsyncLoad refused; loading synchronously"; return false
   Log "Zone %s v%d: async load requested (%d assets, %d missing, priority %d)"; return true
[엔진] 완료 → OnStreamableComplete(Serial)                  // RequestAsyncLoad 안에서 동기로 오든, 지연 헬퍼 틱에서 오든
   Serial==AsyncSerial && State==Loading && !bFinishPending ? { bFinishPending=true; PendingFinishSerial=Serial; AsyncFinishTimer = TM.SetTimerForNextTick(this, &FinishAsyncLoad) } : 무시
[다음 틱] FinishAsyncLoad()
   !bFinishPending || State!=Loading || PendingFinishSerial!=AsyncSerial → return
   bFinishPending=false; World->bIsTearingDown → CancelAsyncLoad(); return
   LoadHandle && !HasLoadCompleted() → Warning 1회(bWarnedHandleIncomplete) 후 진행
   Sub->NoteAsyncFinish(this)
   bAssetsPreloaded=true; BuildVisualLayer/BuildCollisionLayer/BuildBlockers (AcquireMeshAsset → ResolveObject; 없으면 LoadMeshAsset = 상주라 즉시); bAssetsPreloaded=false
   LoadHandle.Reset()                                        // 컴포넌트가 메시를 붙잡는다
   State=Loaded; LastError.Reset(); SetVisualVisible; SetCollisionEnabled; SpawnPortals(); ++AsyncLoadCount
   Log "Zone %s v%d loaded (async %.1f ms wait + %.1f ms build): chunks a/b (k wire boxes), collision c/d, blockers e/f, portals g (WP-05)"
   Sub->NotifyZoneLoaded(this)
Unload()/CancelAsyncLoad()/EndPlay/Deinitialize → §4-1 취소 행
```
- 취소 뒤 지연 헬퍼가 그래도 델리게이트를 부르면 세대 불일치로 무시; 취소 → 재로드 → 옛 완료 순으로 와도 세대가 다르다; 취소 뒤 남은 next-tick 타이머는 `ClearTimer(AsyncFinishTimer)`로 지우고, 지워지지 않아도 `PendingFinishSerial != AsyncSerial`로 무시된다(이중 방어).
- 우선순위: 포털·콘솔 pin은 `AsyncLoadHighPriority`, 거리 로드는 기본.
- 월드 해체: 액터 `EndPlay`(타이머 해제·취소·등록 해제) → 서브시스템 `Deinitialize`(남은 핸들 전부 취소) → GC 때 `~FStreamableManager`(활성 핸들 0). 델리게이트는 약참조라 죽은 액터에는 오지 않는다.
- `RebuildInEditor`/`zone_import.py`: 서브시스템 없음 → 동기(무변경).

### 6. 디버그 정리 2건
- **6-1 render ms(5a)**: 사실 — `GRenderThreadTime`은 렌더 스레드가 자기 프레임 끝에 쓰고 `stat unit`은 0.9/0.1 EMA로 평활한다; 우리는 2 s 창 산술 평균이라 0이 잦으면 평균이 0.00으로 무너진다(V-03). `OnEndFrame` 시점에 그 프레임 값이 아직 쓰이지 않았거나 리셋된 뒤일 수 있다(5.8 순서 미확인, §10 #17). 설계는 **읽는 시점을 `OnBeginFrame`(직전 프레임 확정값)으로 옮기고**(기본 소스 1), 소스 2(`GRenderThreadTimeCriticalPath`)·0(구동작)을 매크로로 남기며, 어느 소스든 0 샘플은 `HoldLastPositive`로 직전 유효값을 유지한다. `OnEndFrame` 바인딩·`GOLMOK_GPU_TIME_SOURCE`·`FormatStatsLine`·`PushFrameSample`은 그대로(WP-05 테스트 계약). 런북 §7이 `stat unit` Draw와 대조해 소스를 확정하고 매크로 기본값을 커밋한다.
- **6-2 실내 표시(5b)**: `OnUnloadDelayElapsed`/`UnloadInteriorAfterEndPlay` → `RequestUnload(…, Portal)` → `bBlocked` 안 세움 + `bPortalManaged=true` → `golmok.zone.list`/HUD 행 `z_synthetic_001_interior … unloaded … portal [placed]`. `blocked` 규칙(반경 밖으로 나가야 해제)은 콘솔 언로드에만 남는다. `bPortalManaged`는 `Evaluate`의 `bManaged`에서 제외되므로 `bAutoManageInterior=True`여도 포털이 놓은 실내를 거리 규칙이 다시 만지지 않는다(기본값 False라 기본 동작은 무변화; 런북에 명시). 해제: 콘솔 출처 `RequestLoad/RequestUnload`, `UnregisterZone`.
- 콘솔 `golmok.zone.index [reload]` 출력(`DescribeIndex()`):
```
golmok.zone.index
index: <Content>/Golmok/Zones/index (3 zones, 4 cells cached, 5 missing cell files) | index: not found (<path>) - discovery off | index: disabled (bDiscoverFromIndex=False) | index: error <parse error>
discovery: on every 2.0 s, despawn > 500 m after 10 s, 3 discovered actors, 0 loading | discovery: off (no AGolmokGeoOrigin | no player)
player: lon 126.923000 lat 37.560000 -> cell 16/55873/25380 (W 126.9196 E 126.9250 S 37.5576 N 37.5620)
cells 3x3 (winning order per cell, * = center, - = no file):
  16/55872/25379 -   16/55873/25379 z_synthetic_001_interior@v1 z_synthetic_001@v1   16/55874/25379 z_synthetic_001_interior@v1 z_synthetic_001@v1 z_synthetic_002@v1
  16/55872/25380 -   16/55873/25380 * z_synthetic_001@v1                             16/55874/25380 z_synthetic_001@v1 z_synthetic_002@v1
  16/55872/25381 -   16/55873/25381 -                                                16/55874/25381 -
near: z_synthetic_001@v1 [placed, loaded]  z_synthetic_001_interior@v1 [placed, unloaded portal]  z_synthetic_002@v1 [index, unloaded]
```
`reload` → `ReloadIndex()`(캐시 비움·재파싱·즉시 `DiscoverZones()`) → Log "index reloaded: N zones". HUD `zones:` 첫 줄은 `DescribeZones()` 헤더라 발견 수·로딩 수가 자동으로 실린다(`BuildZoneLines` 무변경).

### 7. ini (`Config/DefaultGame.ini`)
```ini
[/Script/Golmok.GolmokZoneSubsystem]
; … 기존 11키 그대로 …
; WP-09: discover zones around the player from Content/Golmok/Zones/index (golmok-zone index build output synced by zone_index.sync). Silently off without zones.json.
bDiscoverFromIndex=True
; Seconds between index lookups (inside the Evaluate timer, before Evaluate; never per frame).
DiscoveryIntervalSeconds=2.0
; Discovered, unloaded zones outside the 3x3 cells and farther than this (m) are destroyed; 0 = 2 x UnloadRadiusM.
DespawnDistanceM=0
; Those conditions must hold this long (s) first (no spawn / destroy thrash at cell borders).
DespawnGraceSeconds=10

[/Script/Golmok.GolmokZone]
; WP-09: chunk / collision assets stream through FStreamableManager (state Loading, built next tick); False keeps the WP-04 synchronous path.
bAsyncLoad=True
bDrawMissingAssetBoxes=True
BlockerThicknessCm=10
```
`MaxLoadsPerUpdate` 주석을 "loads (requests) per evaluation"으로 갱신(키 이름 불변). `[GolmokPortal]`·`[GolmokDebugSubsystem]` 키 집합 불변. 스테이징 줄 불변. `test_ue_zone_fixture.py`의 `bAsyncLoad == "False"` 단언은 `"True"`로(스펙 기본값 변경; WP-04 §9 문구도 한 줄 갱신).

### 8. 테스트

#### 8-1 pytest
| 파일 | 테스트 | 내용 |
|---|---|---|
| `test_ue_geo_math.py` | `test_lonlat_to_cell_matches_python_exactly` | `cell` 단건: §2 표 9행; `cells` stdin 배치(`subprocess.run(..., input=text, encoding="utf-8")`): z ∈ {0, 5, 16, 20, 30}, 난수 3000점(lon −180..180, lat −90..90 → 클램프 포함) + 픽스처 셀 4개 경계 ±1e-9°·±1e-6° 점(정확한 경계 제외, 주석) → `(x, y) == zi.lonlat_to_tile(lon, lat, z)` 정수 일치 |
| | `test_cell_bounds_match_python` | `cellbounds` ↔ `zi.tile_bounds` 1e-12 (셀 4개 + 난수 50개) |
| | `test_header_is_pure` | 기존(include 집합 불변) |
| `test_ue_stats_math.py` | `test_hold_last_positive_sequence` | `hold` stdin `0 5 0 0 6 nan -1 7` → `0 5 5 5 6 6 6 7`, HeldCount 5, Total 8 |
| | `test_hold_state_resets` | Reset 뒤 Value 0·카운터 0 |
| `test_zone_index.py` | `test_scan_zones_skips_index_folder` | `make_zone` 1개 + `(tmp/"index"/"cells").mkdir(parents=True)` → `scan_zones` problems == []; `zone_main(["index","build","--zones-root",tmp,"--out",tmp/"index","--strict"]) == 0` |
| `test_ue_zone_index_fixture.py` | `test_generator_reproduces_committed_index_and_zone_002` | `make_index_fixture.write_all(tmp)` ↔ `fixtures/zones/{z_synthetic_002,index}/**`·`Content/Golmok/Zones/{z_synthetic_002,index}/**` 바이트 동일(정렬 `rglob`, `normpath`), `--check` exit 0 |
| | `test_index_validates_and_cells_expected` | `schema.validate_index` 전부 `[]`; ids == [001, 001_interior, 002]; 셀 파일 4개 == §2 표(이름·내용·순서); 각 셀 (id, version) ⊆ zones.json |
| | `test_zone_002_is_200_m_east_in_next_cell` | `transform.lonlat_to_enu`로 001→002 원점 ENU = (200 ± 0.5, 0 ± 0.5) m; `lonlat_to_tile(002 origin)[0] == 55874 != 55873`; footprint 겹침 없음; 002 manifest `zm.check` errors == [], 포털 0개 |
| | `test_cli_index_build_strict_from_fixture_root` | `zone_main(["index","build","--zones-root",FIXTURE_ZONES,"--out",tmp,"--strict"]) == 0`, 출력 == 픽스처 index(§3-7 skip 증명) |
| `test_ue_python_zone_index_sync.py`(가짜 unreal) | `test_sync_copies_fixture_index_bytes` | `zx.sync(FIXTURE_ZONES)` → `<tmp Content>/Golmok/Zones/index/**` == 픽스처; 로그 `zx.plan/zx.copied/zx.missing/zx.done` |
| | `test_sync_removes_stale_cells_and_is_idempotent` | dest에 `16_1_1.json` 미리 생성 → 제거 + `zx.removed`; 2회차에 `zx.removed` 없음 |
| | `test_sync_rejects_broken_index_before_writing` | 셀 JSON 깨짐 / 버전 불일치 / `manifest` 경로 불일치 / 파일명≠내용 → `ZoneIndexError('check', …)`, dest 파일 0개 |
| | `test_sync_missing_index_dir` | `ZoneIndexError('plan', …zones.json…)` |
| | `test_run_with_index_true_uses_zones_root` | `zi.run(zone_dir, with_index=True)` → `result["index"]["cells"] == 4`, 호출 순서 zone → index → save |
| | `test_run_with_index_missing_folder_warns_not_fails` | `zx.warn` 1회, `result["index"] is None` |
| `test_ue_python_pure.py` | 기존 확장 | `zone_index` 모듈 import·touchpoint·LOG 인용(`RUNBOOKS += pc-verify-wp09.md`); 순수 함수 6개 단위 테스트(`parse_cell_name` 거부 `16_-1_2.json`·`x16_1_2.json`, `check_index` 오류 케이스 8개 각 1건, `index_sync_plan` 정렬·stale) |
| `test_ue_wp09_fixture.py` | `test_ini_keys_and_values` | 4키 존재·범위(`DiscoveryIntervalSeconds >= UpdateIntervalSeconds`, `DespawnDistanceM == 0 or >= UnloadRadiusM`, grace ≥ 0), `bAsyncLoad == "True"`; 키=UPROPERTY는 기존 `test_ini_keys_match_config_uproperties`가 자동 대조 |
| | `test_automation_tests_declared` | 5개 이름 + `#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR` |
| | `test_evaluate_body_never_spawns_registers_or_destroys` | `void UGolmokZoneSubsystem::Evaluate()` 본문(중괄호 매칭) 안에 `SpawnActor`, `FinishSpawning(`, `DiscoverZones(`, `Destroy(`, `RegisterZone(`, `UnregisterZone(`, `RequestLoad(`, `RequestUnload(` 없음 |
| | `test_timer_runs_discovery_before_evaluate` | `OnEvaluateTimer()`·`CmdZoneRefresh` 본문에 `DiscoverZones(` 인덱스 < `Evaluate(`; `SetTimer(EvaluateTimer, this, &UGolmokZoneSubsystem::OnEvaluateTimer` 존재, `&UGolmokZoneSubsystem::Evaluate,` 바인딩 없음 |
| | `test_discover_never_loads_and_destroys_outside_zones_loop` | `DiscoverZones()` 본문에 `->Load(`·`->Unload(`·`RequestLoad(`·`RequestUnload(`·`Evaluate(` 없음; `for (` … `: Zones)` 블록 안에 `Destroy(`·`SpawnActor` 없음 |
| | `test_async_completion_is_always_deferred` | `GolmokZone.cpp`: `FStreamableDelegate\s+\w+\s*=\s*FStreamableDelegate::CreateWeakLambda` 위치 < `RequestAsyncLoad(`; `RequestAsyncLoad(` 인자에 `CreateWeakLambda`/`CreateUObject` 직접 사용 없음; `LoadAsync`·`OnStreamableComplete` 본문에 `FinishAsyncLoad(` 호출 없음(`&AGolmokZone::FinishAsyncLoad` 바인딩만), `OnStreamableComplete` 본문에 `AsyncSerial`·`SetTimerForNextTick`·`AsyncFinishTimer =`; `FinishAsyncLoad` 본문에 `PendingFinishSerial`·`NoteAsyncFinish(`, `RegisterZone(/RequestLoad(/SpawnActor<AGolmokZone` 없음; `CancelAsyncLoad` 본문에 `ClearTimer(AsyncFinishTimer)`·`CancelHandle()`; `AcquireMeshAsset` 본문에 `DoesPackageExist(`; enum에서 `Loading`이 `Failed` 뒤 |
| | `test_portals_never_load_zones_directly` | Portals/*.cpp에 `->Load(`·`->Unload(`·`RegisterZone(` 없음; `PreloadInterior` 바인딩이 `SetTimerForNextTick` |
| | `test_static_member_params_do_not_shadow_members` | Zones/Portals/Debug 헤더: 클래스별 멤버 이름 집합 vs `static … Name(...)` 인자 이름 — 교집합 없음(C4458) |
| | `test_anonymous_namespace_names_unique_across_zones_portals_debug` | `test_lighting_presets.py`의 스캐너 재사용: 익명 namespace 최상위 이름 중복 없음(유니티 빌드) |
| | `test_debug_render_source_macro_and_hold_rule` | `.cpp`에 `GOLMOK_RENDER_TIME_SOURCE`, `OnBeginFrame`, `OnEndFrame`, `HoldLastPositive`, `DescribeRenderSource`; `assert_pure_header(GolmokStatsMath.h)` |
| | `test_zone_index_header_is_plain` | `GolmokZoneIndex.h`에 UCLASS/USTRUCT/`.generated.h` 없음, `TFunction` 리더 존재 |
| | `test_build_cs_and_staging_unchanged` | Build.cs 모듈 집합 WP-05와 동일; `+DirectoriesToAlwaysStageAsUFS=` 2줄 그대로 |
| | `test_describe_zones_header_prefix_kept` | `"%d zones (load < %.0f m, unload > %.0f m), %d basemap actors tagged"` 문자열 존재; `golmok.zone.index` 문자열 + `FAutoConsoleCommandWithWorldAndArgs` 13개 |
| | `test_spec_has_in_game_location` | `zone-manifest.md`에 `게임 내 위치`·`Content/Golmok/Zones/index/zones.json` |
| | `test_wp05_portal_test_edit_is_the_documented_one` | `GolmokPortalTest.cpp`에 `Zone->bAsyncLoad = false;` 1회, `StreamInTimeoutSeconds = 5.0` 3회 |
| `test_ue_zone_fixture.py` | 변경(1줄) | `actor["bAsyncLoad"] == "True"` |
| `test_make_synthetic_zone.py` | `test_offset_moves_origin_only` | `--offset-m 200,0` → origin lon 증가·lat 동일(1e-7), 나머지 파일 동일, 기본값 출력 불변 |

Windows CI 규칙: 모든 `subprocess.run`에 `encoding="utf-8"`, 배치 입력은 stdin, 경로 비교는 `os.path.normpath`, `rglob/iterdir`는 `sorted`.

#### 8-2 UE 자동화 (`Tests/GolmokZoneTest.cpp`, `#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR`, `EditorContext | ProductFilter`, 전부 `-nullrhi`, WP-05 테스트의 `FStartPIECommand`/latent 패턴)
| 이름 | 맵 | skip | 단언 |
|---|---|---|---|
| `Golmok.Zone.IndexParse` | 없음(PIE 아님) | 없음 | 스펙 §6 예제 문자열 `ParseZonesText/ParseCellText` → 필드 전부; 오류 8케이스(`schema_version 2`, `cell_zoom 15`, bad id, bbox 3개, west>east, manifest 불일치, 중복 id, 셀 z≠16) 각 false + Error 비어있지 않음; `CellFileName(55873, 25379) == "16_55873_25379.json"`; `GolmokGeoMath::LonLatToCell(126.9250, 37.5620, 16) == (55873, 25379)`, `(126.9272665, 37.5620) → (55874, 25379)`; **메모리 리더**(`TMap<FString, FString>` + 읽기 카운터, `LoadFromText("mem:/index", …)`): `GetCell(55873, 25379)` 2회 → `NumFileReads()==1`; 없는 셀 → `bFromFile==false`·0 zones·읽기 1회 뒤 캐시(`NumMissingCells()==1`); `CollectAround(55873, 25380, 1)` == [001_interior, 001, 002] 중복 없음; 셀의 버전 불일치 행 → 경고 1건·항목 제외; Content index가 있으면 `Load(DefaultIndexDir())` → 3 zones(없으면 AddInfo) |
| `Golmok.Zone.IndexDiscover` | `L_ZoneTest` | 맵 없음 → `AddInfo("skipped: run synthetic_zone.run()")` | PIE 시작(폰 = 레벨 원점) → `IsDiscoveryActive()`; ≤ `DiscoveryIntervalSeconds`+1 s: `FindZone("z_synthetic_002")` 유효·`bSpawnedFromIndex`·`HasAnyFlags(RF_Transient)`, `z_synthetic_001` 레코드 1개뿐(`!bSpawnedFromIndex`, 배치 우선), `NumDiscovered() >= 1`, `DescribeZones()`에 `[index]`·`[placed]`·`discovered`; `GEngine->Exec(World, TEXT("golmok.zone.index"))` 오류 없음; 서브시스템 `DespawnGraceSeconds = 0`(DespawnDistanceM 0 → 500 m), 폰을 동쪽 3 km(`SetActorLocation(+300000 cm X)`) → `Evaluate()` → `DiscoverZones()` 2회(연속 틱) → `FindZone("z_synthetic_002") == nullptr`, 001 유지; `GetReentrancyViolations()==0` |
| `Golmok.Zone.AsyncLoad` | `L_Dev` | 맵 없음 → skip(WP-05와 동일) | 지연 스폰 001(`bAutoManaged=false`, `bAsyncLoad=true`) → `int32 Missing; const int32 N = Zone->CollectAssetPaths(Missing).Num()` → **N > 0**(PC: 001 에셋이 프로젝트에 있음): `Load()==true` 직후 `IsLoading()`·`GetPortalActors().Num()==0`·`RequestLoad` 메시지 `loading`; ≤ 5 s `IsLoaded()`, `AsyncLoadCount==1`, 포털 1개, `GetLoadingSeconds()==0`, `DescribeZones`에 `loaded`; **N == 0**(에셋 없음): `Load()` 직후 `IsLoaded()`·`MissingAssetCount == 청크+충돌 수`·`AsyncLoadCount==0`, AddInfo "no assets: synchronous fallback exercised"; 두 경우 모두 `Unload()` → Unloaded·포털 0·`GetReentrancyViolations()==0` |
| `Golmok.Zone.AsyncCancel` | `L_Dev` | 동일 | N > 0: `Load()` → `IsLoading()` → 같은 틱 `Unload()` → `Unloaded`·`IsFinishPending()==false`; 1 s 뒤에도 Unloaded·컴포넌트 0·`AsyncLoadCount==0`; 다시 `Load()` → ≤ 5 s `Loaded`·`AsyncLoadCount==1`(세대 갱신); Loading 중 `Destroy()` → 1 s 뒤 Error 없음. N == 0: 동기 폴백이라 취소 경로 없음 → AddInfo 후 통과. 끝에 `GetReentrancyViolations()==0` |
| `Golmok.Zone.InteriorNotBlocked` | `L_ZoneTest`(실내 zone은 배치 또는 index 발견) | 맵 없음 → skip | `DiscoverZones()`; `RequestLoad(interior, true, Msg, Portal)` → ≤ 5 s Loaded; `RequestUnload(interior, Msg, Portal)` → 행에 `" portal"` 있고 `" blocked"` 없음·`!R.bBlocked`; `Evaluate()` 3회 뒤에도 실내 자동 재로드 없음(`bPortalManaged`); `RequestUnload(interior, Msg, Console)` → `" blocked"` 있음(회귀); `RequestLoad(interior, false, Msg, Console)` 뒤 ` portal` 사라짐; `GetReentrancyViolations()==0` |

기존 `Golmok.Portal.*` 4개(§0의 4줄 수정 뒤)·`Golmok.Debug.HudStats`·`Golmok.Lighting.*`·`Golmok.Player.Movement` 통과가 완료 기준. `LogStreaming` 오류는 사전 검사로 발생하지 않는다(`AddExpectedError` 미사용).

### 9. 런북 `docs/runbooks/pc-verify-wp09.md` 골자 (V-07)
0. 대상 파일 표(§1), 전제: V-03 통과, `L_ZoneTest`(+ 합성 실내) 존재, `cd tools && python -m pytest -q` 초록. 기대 로그는 `_pure.LOG` 인용(``` 블록, 드리프트 테스트 대상).
1. **Index 동기화(오염 없음)**: `golmok-zone index build --zones-root unreal\Golmok\Content\Golmok\Zones --out D:\golmok_index --strict`(index 폴더는 조용히 건너뜀, 경고 0) → 에디터 Python `import golmok.zone_index as zx; zx.sync(r"unreal\Golmok\Content\Golmok\Zones", index_dir=r"D:\golmok_index"); zx.describe()` → 기대 로그 `zone_index: plan 3 zones, 4 cells from D:\golmok_index` … `zone_index: done 3 zones, 4 cells -> <Project>\Content\Golmok\Zones\index` → `git status` 깨끗함(커밋본과 바이트 동일 = 자기 검증). [ ] 필요하면 `zi.run(..., with_index=True)` 경로도 합성 zone 1개로 확인(그 결과는 `git checkout`으로 되돌림, §4 전에).
2. **빌드** `.\tools\ue\build.ps1` — 컴파일 오류는 §10 표 번호로 고치고 `WP-09: PC fix` 커밋.
3. **헤드리스** `.\tools\ue\test.ps1 -Filter Golmok.Zone`(5) → `-Filter Golmok.`(전체 16) 전부 Success(실내 없으면 Portal.* 3개 skip Info).
4. **PIE 발견(배치 액터 없이)**: `L_ZoneTest`를 `L_ZoneTest09`로 복제, `Zone_*` 액터 삭제(GeoOrigin·바닥·PlayerStart 유지). PIE → 2 s 안 로그 `discovery: cell 16/55873/25380, 3x3 zones 3, spawned 3 …` → `golmok.zone.index` 기대 출력(§6 블록: 플레이어 셀 `16/55873/25380`, near 3개 `[index]`) → `golmok.zone.list` 헤더 `3 zones (load < 150 m, unload > 250 m), N basemap actors tagged, 3 discovered, 0 loading` → HUD `zones:` 첫 줄 동일 → 아웃라이너 `Golmok/Zones/Discovered`에 Transient 액터 3개 → `golmok.zone.radius 300 400` → 001 로그 `async load requested (… assets …)` → 다음 틱 `loaded (async … ms wait + … ms build)`; 002는 `loaded` + 주황 와이어 박스(에셋 경고 없음).
5. **걸어 나가서 파괴**: 에디터 Python PIE 드라이버로 폰을 001 동쪽 **1.5 km**(셀 55877; 3×3 = 55876..55878, 거리 > 500 m) → `Zone … unloaded`(반경) → 10 s 뒤 `zone z_synthetic_00x despawned (index; … m, cells far)` 3건, 목록 `0 discovered`; 되돌아오면 2 s 안 재발견.
6. **히치 비교**: `golmok.path record hitch`(원점 → 001 → 002 왕복 60 s) → `golmok.path play hitch --csv` ×2(ini `bAsyncLoad=True`/`False`, 에디터 재시작) → `golmok-perf … --label async|sync` 표(1% low·p99·최대 프레임 ms) + 로그 `loaded in X ms` vs `loaded (async X ms wait + Y ms build)`. 기대: sync에 로드 스파이크, async에서 감소(합성 zone은 작아 차이가 작을 수 있음 — 수치 기록). 스크린샷은 `golmok.hud 0` 뒤.
7. **render ms**: HUD `render` vs `stat unit` Draw를 2 s 창 5회 대조(소스 1) + `golmok.stats` 두 번째 줄 `held a/b`. 0.00이 남으면 소스 2, 그래도면 0으로 재빌드해 같은 표. held 비율이 가장 낮은 소스를 매크로 기본값으로 커밋.
8. **실내 표시·포털 대기**: 문 왕복(V-03 §5) → 3 s 뒤 `golmok.zone.list` 실내 행 `unloaded … portal [placed]`(blocked 없음), HUD 동일; `golmok.zone.unload z_synthetic_001_interior` → `blocked`; 로그 순서 `Portal door_1: interior preload requested` → `… interior loading` → `… -> load [zone … loading (pinned)] …` → Active; 문을 지나도 바닥이 있다(방 안 낙하 없음); 3 s 안에 되돌아 나오면 `zone … load cancelled`.
9. (선택) 패키징: `UnrealPak -List`에 `Golmok/Zones/index/zones.json`·`cells/*.json`; `-game`에서 `golmok.zone.index` → `index: …(3 zones …)`.
10. PIE 종료(방 안·Loading 중에도): Error/ensure 0, `async load cancelled` 외 경고 없음, 에디터 월드에 Discovered 액터 없음, dirty 맵 없음.
11. **불확실 API 표** = §10(번호 유지) + PC 세션 추가 행.
12. 결과 표(빌드·테스트 16·§4~§10 각 행·고친 API 번호·커밋), STATUS `🟡→🟢`. 무인 검증: 에디터 Python PIE 드라이버 + `unreal.SystemLibrary.quit_editor()`.

### 10. 불확실한 UE 5.8 API와 대안 (런북 §11 형식)
| # | 파일 | API | 불확실한 점 | 대안 |
|---|---|---|---|---|
| 1 | GolmokZoneSubsystem | `FStreamableManager Streamable;`를 `UWorldSubsystem` 값 멤버로(`FGCObject` 파생, 비복사) | `UAssetManager`가 같은 패턴. CDO에도 인스턴스 1개(무해) | `UAssetManager::IsInitialized() ? &UAssetManager::Get().GetStreamableManager() : nullptr`(`Engine/AssetManager.h`, 새 모듈 없음); null이면 동기 폴백 |
| 2 | GolmokZone | `RequestAsyncLoad(TArray<FSoftObjectPath>, FStreamableDelegate, TAsyncLoadPriority, bool, bool, FString)` — 5.4+ `FStreamableAsyncLoadParams&&`·`TFunction` 오버로드 | 델리게이트를 이름 있는 변수로 넘기면 정확 일치 | ① `RequestAsyncLoad(MoveTemp(Paths), Done)` ② `FStreamableAsyncLoadParams P; P.TargetsToStream = MoveTemp(Paths); P.OnComplete = FStreamableDelegateWithHandle::CreateWeakLambda(this, [this, Serial](TSharedPtr<FStreamableHandle>){ OnStreamableComplete(Serial); }); P.Priority = …; P.DebugName = …; RequestAsyncLoad(MoveTemp(P))` |
| 3 | GolmokZone | 완료 델리게이트 발화 시점(`FStreamableDelegateDelayHelper`가 항상 다음 틱인지) | 불확실 — 설계가 의존하지 않음(항상 미룸 + 세대) | 런북 §4 로그로 관찰만 |
| 4 | GolmokZone | `FStreamableHandle::CancelHandle()` 뒤 큐에 든 완료 델리게이트가 불리는지 | 불확실 | 세대 불일치로 무시. `ReleaseHandle()`은 쓰지 않는다(로드 계속·델리게이트 발화) |
| 5 | GolmokZone | `FStreamableDelegate::CreateWeakLambda(UObject*, Lambda)` | `TDelegate::CreateWeakLambda` 4.2x+ | `CreateUObject(this, &AGolmokZone::OnStreamableComplete, Serial)`(payload) |
| 6 | GolmokZone | `FSoftObjectPath(const FString&)`로 `/Game/…/SM_x.SM_x` 파싱 | 안정; `IsNull()`로 실패 검사 | `FSoftObjectPath P; P.SetPath(FStringView(Path));` |
| 7 | GolmokZone | `FSoftObjectPath::ResolveObject()` | 안정(찾기만) | `StaticFindObject(UStaticMesh::StaticClass(), nullptr, *Path)`; 최후 `StaticLoadObject`(상주라 즉시) |
| 8 | GolmokZone | `FPackageName::DoesPackageExist(const FString&)`, `FPackageName::ObjectPathToPackageName` | 전자는 V-03에서 컴파일 확인. 쿠킹(IoStore)에서 pak을 보는지 | 후자: `Path.Left(Path.Find(TEXT(".")))`. 전자가 쿠킹에서 false면(런북 §9) `#if WITH_EDITOR`에서만 검사하고 패키지 빌드는 `LogStreaming` 오류 허용 |
| 9 | GolmokZoneSubsystem | `AActor::SetFolderPath(FName)`(`#if WITH_EDITOR`) | 에디터 전용 | 줄 삭제(라벨만) |
| 10 | GolmokZoneSubsystem | `FActorSpawnParameters{bDeferConstruction, ObjectFlags\|RF_Transient, SpawnCollisionHandlingOverride}` + `FinishSpawning` | V-03에서 포털로 확인. `SpawnActorDeferred<T>`는 `ObjectFlags`를 못 받아 쓰지 않음 | `SpawnActorDeferred<AGolmokZone>(…)` 뒤 `Zone->SetFlags(RF_Transient)` |
| 11 | GolmokZone / Portal | `FTimerManager::SetTimerForNextTick(UserClass*, MethodPtr)`가 **`FTimerHandle`을 반환** | 반환형 확인(4.2x+에서 반환); 저장해 `ClearTimer` | `FTimerHandle H = SetTimerForNextTick(FTimerDelegate::CreateUObject(this, &AGolmokZone::FinishAsyncLoad))`; 핸들이 없으면 `SetTimer(H, …, 0.001f, false)`; 어차피 세대 검사가 최종 방어 |
| 12 | GolmokZone/Subsystem | `FStreamableManager::AsyncLoadHighPriority`(100)/`DefaultAsyncLoadPriority`(0), `TAsyncLoadPriority` | 정적 상수 이름 | 리터럴 `100`/`0` |
| 13 | GolmokZone | `FStreamableHandle::HasLoadCompleted()/WasCanceled()` | 4.17+ 안정 | 상태 검사만 `State`로 |
| 14 | GolmokZoneSubsystem | `FStreamableManager::SetManagerName(FString)` | 존재(4.2x+) | 줄 삭제 |
| 15 | GolmokDebugSubsystem | `GRenderThreadTimeCriticalPath`(`RenderTimer.h`) | `GRenderThreadTime`과 같은 헤더라 봄 | 링크 오류면 소스 1(`#if == 2` 블록만 컴파일) |
| 16 | GolmokDebugSubsystem | `FCoreDelegates::OnBeginFrame.AddUObject/Remove` | `OnEndFrame`과 쌍(V-03 확인) | `FWorldDelegates::OnWorldPreActorTick` |
| 17 | GolmokDebugSubsystem | `GRenderThreadTime`이 `OnBeginFrame` 시점에 직전 프레임 최종값인지(0.00 원인) | 엔진 순서 미확인 | 매크로 0/1/2 + hold 규칙; 런북 §7이 확정 |
| 18 | GolmokZoneTest | 자동화가 `LogStreamableManager`/`LogStreaming` Warning·Error에 반응 | 없는 패키지는 요청하지 않음 | 뜻밖의 경고면 `AddExpectedError(TEXT("Couldn't find file for package"), EAutomationExpectedErrorFlags::Contains, 0)` |
| 19 | GolmokZoneSubsystem | `UWorld::HasBegunPlay()`, `UWorld::IsGameWorld()`, `UWorld::bIsTearingDown` | 후자는 WP-05에서 컴파일 확인 | `GetBegunPlay()`; `WorldType == Game/PIE` 직접 비교 |
| 20 | GolmokGeoMath | `std::ldexp/asinh/sinh/atan`(`<cmath>`) MSVC | 안정. `tan/asinh` 마지막 ulp | 결과 차이는 셀 경계 위 점만; 런북 §3에 기록 |
| 21 | GolmokZoneIndex | `TryGetArrayField/TryGetNumberField/TryGetStringField/TryGetObjectField(const FString&, …)` | V-03 확정: `FString` 키 객체 | `TryGetField(FStringView)` + `AsArray()/AsNumber()/AsString()` |
| 22 | GolmokZoneIndex | `TFunction<bool(const FString&, FString&)>` 기본 생성·`operator bool` | `TFunction`에 `bool` 변환 있음 | 함수 포인터 + 컨텍스트 |
| 23 | GolmokZoneIndex | `FFileHelper::LoadFileToString` + `IFileManager::Get().FileExists`가 UFS pak 안에서 동작 | WP-04 manifest로 확인 | 존재 검사 없이 `LoadFileToString` 실패를 "없음"으로 |
| 24 | GolmokZone | `EGolmokZoneState`에 `Loading` 추가(끝) | BlueprintType enum 값 추가 안전; `State`는 Transient | — |
| 25 | GolmokZoneSubsystem | `FStreamableManager` 소멸(GC) 시 살아있는 핸들 | `Deinitialize`에서 전 zone `CancelAsyncLoad()` | 문제면 `TUniquePtr<FStreamableManager>` + **사용자 선언 소멸자를 .cpp에 정의**(불완전형 함정 회피) 후 `Deinitialize`에서 명시 파괴 |
| 26 | GolmokPortal | `SetTimerForNextTick(this, &AGolmokPortal::PreloadInterior)` UObject 메서드 오버로드 | #11과 동일 | `FTimerDelegate::CreateUObject` |
| 27 | GolmokZoneTest | `GEngine->Exec(World, TEXT("golmok.zone.index"))` | 콘솔 실행 경로 | `UKismetSystemLibrary::ExecuteConsoleCommand` |
| 28 | GolmokZoneTest | `IMPLEMENT_SIMPLE_AUTOMATION_TEST(…, EditorContext \| ProductFilter)`, `FStartPIECommand`, `GEditor->PlayWorld` | WP-05 4파일과 동일 패턴(V-03 통과) | — |
| 29 | GolmokZoneSubsystem | `UGolmokGeoSubsystem::LevelUEToLonLat(const FVector&, double& Lat, double& Lon, double& H)` | 자체 코드(WP-04) | — |
| 30 | 정적 검사 | MSVC C4458: `FGolmokZoneIndexCell` 멤버 `X/Y/Zoom`·`FGolmokZoneIndex` 멤버 `IndexDir` vs 정적 함수 인자 | `In*` 규칙 + pytest | 컴파일 오류 시 인자 이름만 변경 |
| 31 | 유니티 빌드 | Zones/*.cpp 익명 namespace 이름(`MakeComponentName`, `ZoneSubsystemFor`, 새 `IndexJson*`, `CmdZoneIndex`) | 파일 접두 + pytest | 충돌 시 이름 변경 |
| 32 | GolmokPortalTest | `StreamInTimeoutSeconds` 5.0이 비동기 실내 + 서브레벨 스트리밍에 충분한지 | 합성 실내는 에셋 수 개 | 부족하면 10.0(상한만; 결과에 기록) |
| 33 | Python | `unreal.Paths.project_content_dir()` | WP-06 사용 | — |
| 34 | 런북 | 콘솔 `teleport` 부재 → 에디터 Python 드라이버로 폰 이동 | V-03 방식 | `golmok.path play`로 원거리 경로 재생 |

### 11. 위험·트레이드오프
1. **엔진 완료 델리게이트 타이밍·취소 의미론**(§10 #3·#4): 항상-지연 + 세대로 양쪽을 흡수하지만 PC 전에는 미검증. 지연 헬퍼가 없어 동기 발화가 기본이면 완료가 항상 1틱 늦다(체감 없음). 오버로드 모호로 컴파일이 막히면 #2 대안이 첫 손질.
2. **"바닥 없는 방" 창**: 선로드(트리거 진입 다음 틱)로 요청을 앞당기고 포털이 `Loaded`까지 `Pending`을 유지하므로 방에 들어갔을 때 바닥이 없는 상태는 없다. 대신 실내 로드가 느리면 문 앞에서 최대 10 s 대기 후 "activating anyway" 경고. `bAsyncLoad=False`가 즉시 우회.
3. **`DoesPackageExist` 비용**: 로드마다 청크 수만큼 존재 검사(IoStore 해시 조회, 에디터 stat) — 수십 청크에도 ms 미만. 로그 오염 방지 이득이 크다. 쿠킹에서 거짓 음성이면 와이어 박스로 드러난다(런북 §9).
4. **발견 zone의 manifest 파싱은 `Evaluate`에서**(zone당 JSON 1회, 배치 zone과 동일). 3×3에 zone 수십 개면 첫 발화에 몰림 → `MaxSpawnsPerDiscovery=8`. 후속 WP에서 manifest도 비동기화.
5. **셀 경계 왕복**: "3×3 밖" 조건에는 히스테리시스가 없고 거리(500 m vs 150 m)와 `DespawnGraceSeconds`(10 s)가 대신한다. 부족하면 ini로 grace를 늘린다.
6. **render ms 원인 미확정**: hold 규칙은 표시를 고치지만 `GRenderThreadTime`이 아예 안 써지는 구성이면 오래된 값을 보여 준다 → `golmok.stats` 두 번째 줄의 held 비율을 런북에 기록.
7. **WP-05 테스트 수정 4줄**: 의도적·문서화된 변경(SpawnFromManifest는 동기 경로 회귀, 타임아웃은 상한). `bPortalManaged`로 `bAutoManageInterior=True` 사용자는 동작 변화를 본다(기본값 False).
8. 정적 "스택 밖" 증명은 텍스트 기반(중괄호 매칭). 함수를 쪼개면 테스트도 따라가야 한다.

### 12. 심판 지적 반영표 (defect → 조치)
| # | 심판 | 대상 | 지적 | 최종안 조치 |
|---|---|---|---|---|
| 1 | 1 | state | 포털이 실내 Loading 중 Active(스펙 4 위반) | 채택 안 함. §4-2: `Loaded`까지 `Pending` 유지(0.05 s 폴링, 10 s 상한) |
| 2 | 1·2 | state | 빈 목록으로 `RequestAsyncLoad` 호출 | 채택 안 함. §5: 경로 0개면 호출하지 않고 동기 경로 |
| 3 | 1 | state | `SetTimerForNextTick`이 핸들을 안 준다는 잘못된 근거 | §3-4·§10 #11: 반환 핸들을 `AsyncFinishTimer`에 저장해 `ClearTimer`; 세대 검사는 이중 방어 |
| 4 | 1 | state | `IndexDir()` 멤버 vs `IndexDir` 인자(C4458) | §3-2: 정적 함수 인자 전부 `In*`(`InIndexDir`), pytest `test_static_member_params_do_not_shadow_members` |
| 5 | 1 | state | `TUniquePtr<FGolmokZoneIndex>` 불완전형 | §3-3: `FGolmokZoneIndex Index` 값 멤버 + 헤더 include |
| 6 | 1 | state | pull-in 실내가 3×3 밖이면 스폰/파괴 반복 | pull-in 채택 안 함(실내는 같은 셀에 있어 자연 발견) + `DespawnGraceSeconds` + "부모 Loaded/Loading이면 미파괴" |
| 7 | 1 | state | `IsValid(this)` 무의미·위반 카운터 이름 오류 | 카운터 구조체 채택 안 함; `PointerHoldDepth`+`ReentrancyViolations` 하나, `IsValid(this)` 검사 없음 |
| 8 | 1·2 | data | `TUniquePtr<FStreamableManager>` 전방 선언 + UHT 소멸자 | 값 멤버(§0); #25 대안도 사용자 선언 소멸자 명시 |
| 9 | 1·2 | data | 완료 경로에 세대 가드 없음·타이머 미해제 | `AsyncSerial`/`PendingFinishSerial` + `ClearTimer(AsyncFinishTimer)`(§5) |
| 10 | 1·2 | data | Pending 선로드 pin이 EndPlay에서 안 돌아옴 | `IsHoldingInterior()`가 EndPlay·LeaveInterior·IsInteriorZoneInUse를 넓힘(§3-5, §4-2) |
| 11 | 1 | data | `EndPlayerOverlap`에서 `RequestUnload` 동기 호출 | 반납은 항상 `StartLeaving` → 3 s 타이머 → `RequestUnload`(§4-2); 오버랩 콜백에서 서브시스템 호출 없음 |
| 12 | 1·2 | data | AsyncLoad/AsyncCancel이 L_Dev(에셋 없음)에서 스트리머를 안 탐 / PC에선 `MissingAssetCount==4` 실패 | §8-2: `CollectAssetPaths().Num()`으로 분기해 두 경우 모두 정확한 단언; PC(에셋 있음)에서는 스트리머·취소 경로 실행 |
| 13 | 1·2 | data | 포털 대기 상한 없음 | `InteriorLoadTimeoutSeconds = 10 s`(.cpp 상수) 뒤 "activating anyway" |
| 14 | 1 | api | `SetTimerForNextTick` 핸들 버림 → 취소 뒤 옛 타이머가 새 요청을 완료 | #3과 동일 + `PendingFinishSerial` |
| 15 | 1 | api | 동기 폴백의 `StaticLoadObject`가 Evaluate 스택에서 플러시를 유발할 수 있어 "스택 밖" 증명 과장 | 항상-지연(§5) + `AcquireMeshAsset`이 없는 패키지에 `StaticLoadObject`를 부르지 않음(§4-4 표) |
| 16 | 1 | api | `FinishAsyncLoad` 재시도 폴링 무한 | 폴링 제거: 타이머는 완료 델리게이트 뒤에만 잡히고, `!HasLoadCompleted()`면 경고 1회 후 진행(§5) |
| 17 | 1 | api | `bSuperseded`가 Loaded·pinned 발견 zone도 파괴 | `Unloaded && !bPinned`일 때만 retire, 아니면 `bRetirePending`(§4-3); `FindZone`은 배치 우선 |
| 18 | 1·2 | api | 픽스처를 `fixtures/zone_index/`로 옮김(스펙 경로 위반) | 스펙 경로 `fixtures/zones/index/` + `scan_zones` skip + `--strict` 회귀 테스트(§3-7, §8-1) |
| 19 | 2 | 전부 | `bAsyncLoad=True`가 `Golmok.Portal.SpawnFromManifest`를 깨뜨림 | `Zone->bAsyncLoad = false;` 1줄(문서화된 WP-05 테스트 수정) + `StreamInTimeoutSeconds` 5.0; pytest가 그 수정만 있음을 고정 |
| 20 | 2 | api | 런북 §1이 `make_synthetic_zone --interior`로 index를 만들어 커밋본을 덮고 §3·§4와 모순 | §9-1: Content zones 루트에서 빌드 → `D:\golmok_index` → sync → `git status` 깨끗(자기 검증, 오염 없음) |
| 21 | 2 | api | `test_ue_zone_fixture.py` 1줄 변경 불필요 | 삭제(glob이 `index/`를 못 만남). 남은 변경은 `bAsyncLoad == "True"` 뿐 |
| 22 | 2 | api | 샘플 출력의 셀 번호 추측(002는 55874) | §2 예제값·픽스처 셀 표를 계산해 기재, pytest가 재계산·단언, 런북 기대문은 그 값 |
| 23 | 2 | api | `DespawnDistanceM` 규칙 불일치(주석 0=2× vs 코드 500) | ini 기본 `0` = `2 × UnloadRadiusM`, `GetDespawnDistanceM()`이 사용 시점에 계산(radius 변경 추종); Initialize는 0 < 값 < UnloadRadiusM만 보정 |
| 24 | 2 | api | `bPortalManaged`가 `bManaged`에 반영 안 됨 | §4-5: `bManaged`에 `!R.bPortalManaged`(+`!R.bRetirePending`) |
| 25 | 2 | state | 스펙 4 거부 | #1과 동일 |
| 26 | 2 | state | 스펙 5(a) 미이행(`OnEndFrame` 유지) | §6-1: 기본 소스 1 = `OnBeginFrame` 읽기 |
| 27 | 2 | state | 빈 `RequestAsyncLoad` | #2와 동일 |
| 28 | 2 | state | `LastDiscoverFrame == LastEvaluateFrame` 단언 flaky | 채택 안 함. 순서 증명은 정적(본문 순서) + 동적(`ReentrancyViolations==0`) |
| 29 | 2 | state | 과설계(25 카운터·ini 3키 추가·타임아웃 sticky Failed) | 카운터 2개, ini 4키(스펙 3 + grace), zone 타임아웃 없음(§4-1) |
| 30 | 2 | data | 런북 §5 "600 m 북쪽(셀 25378)"이 3×3 안 | §9-5: 동쪽 1.5 km(셀 55877; 3×3 완전히 밖) |
| 31 | 2 | data | 런북 §1이 커밋본을 덮고 복원 시점이 모호 | #20과 동일(오염 없음) |
| 32 | 2 | data | 세대 가드 없음 | #9와 동일 |
| 33 | 2 | data | `TUniquePtr<FStreamableManager>` | #8과 동일 |
| 34 | 2 | data | 포털 대기 상한 없음·EndPlay 조건 미확장 | #13·#10과 동일 |
| 35 | 1 | api(설계 평가) | "지연 발화는 즉시 FinishAsyncLoad" 경로가 스택에 의존 | 즉시 경로 삭제: 완료는 예외 없이 다음 틱(§5) |
| 36 | 1·2 | best ideas | 값 멤버·DoesPackageExist·Pending 유지·선로드·주입 리더·scan_zones 수정·OnBeginFrame 캐시·C4458/익명 namespace 스캔·위반 카운터(축소)·002 동쪽 200 m·런북 자기 검증 | 전부 채택(§0) |

## 결과
(세션이 작성)
