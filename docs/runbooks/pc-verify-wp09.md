# PC 검증 런북 — WP-09 UE C++ 런타임 3: Zone Index 발견·비동기 로드 (V-07)

대상: PC Claude 세션(또는 사용자). 전제: `runbooks/pc-verify-wp05.md` 통과(V-03: 빌드 OK, `L_Dev`·`L_ZoneTest` 존재, `synthetic_zone.run(interior=True)`이 한 번 돌아 `z_synthetic_001`·`z_synthetic_001_interior` 에셋·액터·서브레벨이 있음), `cd tools && python -m pytest -q` 초록.
소요: 빌드 10~20분 + 헤드리스 테스트 10분 + 검증 60분. 결과는 이 문서 하단 §12와 `docs/plan/STATUS.md`(V-07 행, WP-09 행)에 적는다.

클라우드 세션은 UE를 컴파일할 수 없었다. **컴파일 에러가 나면 §11의 표를 보고 고친 뒤 커밋**한다(`WP-09: PC fix …`). 설계 의도를 바꾸는 수정이면 `docs/plan/WP-09-ue-zone-index-async.md` "결과"에 한 줄 적는다(DEVELOPMENT-PLAN §4 핸드오프 규칙: 검증 결과는 이 파일 하단, API 수정·설계 변경은 커밋 메시지와 STATUS에).

규칙:
- 이 문서의 기대 로그·메시지는 **설계 문서가 아니라 코드**에서 옮겨 적었다. Python 줄(`zone_index: …`)은 `unreal/Golmok/Content/Python/golmok/_pure.py`의 `LOG`(`zx.*`)에서 옮긴 것이고 `tools/tests/test_ue_python_pure.py::test_log_formats_are_quoted_in_runbook`가 드리프트를 잡는다(로그 문자열을 바꾸면 `_pure.LOG`와 이 문서를 **함께** 고친다; 기대 로그는 항상 ```` ``` ```` 블록 안에). C++ 줄(`LogGolmok: …`)은 `Zones/GolmokZone.cpp`·`GolmokZoneSubsystem.cpp`·`GolmokZoneIndex.cpp`·`Portals/GolmokPortal.cpp`·`Debug/GolmokDebugSubsystem.cpp`의 `UE_LOG`/`Printf` 형식에 픽스처 값을 넣은 것이다. 설계(§6 등)와 다른 곳은 그 자리에 "설계와 다름:"으로 표시했다.
- 값 표기: `x.x ms`·`…`는 PC에서만 정해지는 실측값. `<Project>` = `unreal\Golmok`, `<Content>` = `<Project>\Content`(엔진이 `../../../…` 상대 경로로 찍을 수 있음), `<Saved>` = `<Project>\Saved`. 에디터 Python은 Output Log 창의 Python 입력줄(또는 `py` 콘솔 명령)로 실행한다.
- 픽스처 좌표(설계 §2, pytest가 재계산·단언): `z_synthetic_001` 원점 (126.9250, 37.5620) → 셀 `16/55873/25379`(남쪽 경계에서 0.3 m); `L_ZoneTest`의 PlayerStart = 001 zone-local (0, −5, 0) m ≈ lat 37.561955 lon 126.925000 → 셀 **`16/55873/25380`**(셀 북쪽 경계 4.6 m 남쪽; 북으로 5 m만 걸어도 25379로 바뀌지만 3×3은 여전히 셀 파일 4개를 전부 덮는다); `z_synthetic_002` 원점 (126.9272636, 37.5620) = 001 동쪽 200 m → 셀 `16/55874/25379`, footprint 서쪽 끝이 001 원점 동쪽 184 m. 셀 파일 4개: `16_55873_25379` = [001_interior, 001], `16_55873_25380` = [001], `16_55874_25379` = [001_interior, 001, 002], `16_55874_25380` = [001, 002]. 001 = 청크 3 + 충돌 1 = 에셋 4개(PC에 있음), 001_interior = 청크 1 + 충돌 1 = 2개, 002 = 청크 2 + 충돌 2 = 4개(**에셋 없음** → 동기 폴백·와이어 박스), 002 blockers 1, 포털 0.

## 0. 대상 파일
| 파일 (`unreal/Golmok/` 기준, 그 외 저장소 기준) | 내용 |
|---|---|
| `Source/Golmok/Zones/GolmokZoneIndex.{h,cpp}` | `FGolmokZoneIndex`: `zones.json`·셀 파서, 셀당 1회 캐시, 3×3 조회, 주입 리더(설계 §3-2) |
| `Source/Golmok/Zones/GolmokZone.{h,cpp}` | `Loading` 상태, `LoadAsync/OnStreamableComplete/FinishAsyncLoad/CancelAsyncLoad`, `CollectAssetPaths`(`DoesPackageExist` 사전 검사), `bSpawnedFromIndex`, `AsyncLoadCount`(§3-4) |
| `Source/Golmok/Zones/GolmokZoneSubsystem.{h,cpp}` | `FStreamableManager`, `FGolmokZoneIndex Index`, `OnEvaluateTimer/DiscoverZones/SpawnDiscoveredZone`, Config 4키, `EGolmokZoneRequestSource`, `PointerHoldDepth` 위반 카운터, 콘솔 `golmok.zone.index`(§3-3) |
| `Source/Golmok/Geo/GolmokGeoMath.h` | 추가만: `MaxMercatorLatDeg`, `LonLatToCell`, `CellBounds`(§3-1, g++ 교차검증) |
| `Source/Golmok/Portals/GolmokPortal.{h,cpp}` | 실내 선로드(`PreloadInterior`), `Loading`이면 `Pending` 유지(0.05 s 폴링, 10 s 상한), `bInteriorRequested`, `IsHoldingInterior`, `Source=Portal`(§3-5) |
| `Source/Golmok/Debug/GolmokStatsMath.h` | 추가만: `HeldValue`, `HoldLastPositive`(§3-6) |
| `Source/Golmok/Debug/GolmokDebugSubsystem.{h,cpp}` | `OnBeginFrame` 바인딩, `GOLMOK_RENDER_TIME_SOURCE`(기본 1), `DescribeRenderSource`(§3-6) |
| `Source/Golmok/Tests/GolmokZoneTest.cpp` | 자동화 5개 `Golmok.Zone.IndexParse / IndexDiscover / AsyncLoad / AsyncCancel / InteriorNotBlocked`(§8-2) |
| `Source/Golmok/Tests/GolmokPortalTest.cpp` | 4줄: `Zone->bAsyncLoad = false;`, `StreamInTimeoutSeconds` 2.0 → 5.0 ×3 |
| `Config/DefaultGame.ini` | `[/Script/Golmok.GolmokZoneSubsystem]` `bDiscoverFromIndex=True, DiscoveryIntervalSeconds=2.0, DespawnDistanceM=0, DespawnGraceSeconds=10`, `[/Script/Golmok.GolmokZone] bAsyncLoad=True`(§7) |
| `Content/Golmok/Zones/index/zones.json`, `index/cells/16_*.json` | Content zone 3개(001·001_interior·002)의 index — `tools/scripts/make_index_fixture.py` 출력(픽스처와 바이트 동일) |
| `Content/Golmok/Zones/z_synthetic_002/v1/{manifest.json, blockers.json}` | 001 동쪽 200 m(셀 x 55874), 에셋 없음(와이어 박스), 포털 없음 |
| `Content/Python/golmok/zone_index.py` | `plan/sync/describe`, `ZoneIndexError`(§3-7) |
| `Content/Python/golmok/zone_import.py` | `run(..., with_index=False)`: zone 리빌드 뒤·저장 앞에 `zone_index.sync` |
| `Content/Python/golmok/_pure.py` | index 순수 함수 6개, `LOG` `zx.*` 7키 |
| `tools/golmok_tools/zone/index.py` | `scan_zones`가 zones 루트 안의 `index/`를 조용히 건너뜀 |
| `tools/scripts/make_synthetic_zone.py` | `--offset-m E,N` |
| `tools/scripts/make_index_fixture.py` | 002 + index 픽스처 생성, `--check` |
| `docs/spec/zone-manifest.md` §6 | "게임 내 위치" 항목 |

전제 확인:
- [ ] `git pull` 후 `cd tools; .\.venv\Scripts\Activate.ps1; pip install -e ".[zone,mesh,dev]"; pytest -q` 초록(`test_ue_zone_index_fixture.py`·`test_ue_python_zone_index_sync.py`·`test_ue_geo_math.py`·`test_ue_stats_math.py` 포함). 여기서 빨간 것은 PC 문제가 아니라 코드 문제 — 클라우드 세션에 돌려보낸다.
- [ ] `python tools\scripts\make_index_fixture.py --check` → `check: OK`(커밋된 픽스처·Content index가 생성기와 바이트 동일).
- [ ] `L_ZoneTest`에 `Zone_z_synthetic_001`(Loaded)·`Zone_z_synthetic_001_interior`(Unloaded)·`Portal_z_synthetic_001_door_1`·서브레벨 `L_z_synthetic_001_interior`가 있다(V-03 §2). 없으면 `import golmok.synthetic_zone as z; z.run(interior=True)`.

## 1. Index 동기화(오염 없음)
Content zones 루트에서 index를 **저장소 밖**에 만들고 sync한다. 커밋본과 바이트가 같아야 하므로 `git status`가 깨끗하면 자기 검증이 된 것이다.
```powershell
cd <repo>
golmok-zone index build --zones-root unreal\Golmok\Content\Golmok\Zones --out D:\golmok_index --strict
```
- [ ] 출력 `zone 3개, 셀 4개 → D:\golmok_index (5 파일)`, `WARN` 줄 0개(`index/` 폴더는 조용히 건너뜀), 종료 코드 0.
- [ ] `D:\golmok_index\cells\`에 `16_55873_25379.json 16_55873_25380.json 16_55874_25379.json 16_55874_25380.json` 4개.

에디터 Python(Output Log):
```python
import golmok.zone_index as zx
zx.sync(r"<repo>\unreal\Golmok\Content\Golmok\Zones", index_dir=r"D:\golmok_index")
zx.describe()
```
- [ ] 기대 로그(순서대로; `<Project>` = `unreal\Golmok`):
  ```
  zone_index: plan 3 zones, 4 cells from D:\golmok_index
  zone_index: copied zones.json + 4 cells -> <Project>\Content\Golmok\Zones\index
  zone_index: done 3 zones, 4 cells -> <Project>\Content\Golmok\Zones\index
  ```
  `zone_index: removed …`·`zone_index: WARNING …` 줄은 **없어야** 한다(세 zone의 manifest가 전부 Content에 있음).
- [ ] `zx.describe()` → `index: 3 zones, 4 cells at <Project>\Content\Golmok\Zones\index`.
- [ ] `git status` 깨끗함(커밋본과 바이트 동일). 다르면 `python tools\scripts\make_index_fixture.py --check`로 어느 쪽이 틀렸는지 확인하고 §12에 기록.

참고(다른 경로의 기대 문구 — 정상 흐름에서는 나오지 않음):
```
zone_index: removed 1 stale cell files (16_1_1.json)
zone_index: WARNING 1 indexed zones have no manifest under Content yet (z_synthetic_002)
zone_index: WARNING index not synced: zones.json not found in D:\golmok\zones\index (run golmok-zone index build --zones-root <zones> --out <zones>/index first)
zone_index: ERROR check: cells/16_55873_25379.json: 'z_synthetic_001' version 2 != zones.json version 1
zone_index: ERROR plan: zones.json not found in D:\nowhere\index (run golmok-zone index build --zones-root <zones> --out <zones>/index first)
```
- [ ] (선택) `zi.run(..., with_index=True)` 경로: 합성 zone 1개(`make_synthetic_zone.py --out D:\golmok_synth --interior`)를 `golmok-zone index build --zones-root D:\golmok_synth\zones --out D:\golmok_synth\zones\index`로 index한 뒤 `import golmok.zone_import as zi; zi.run(r"D:\golmok_synth\zones\z_synthetic_scan_001", level="/Game/Golmok/Maps/L_ZoneTest06", geo_origin="area", with_index=True)` → 로그 순서 `zone_import: zone Zone_z_synthetic_scan_001 rebuilt` → `zone_index: plan 2 zones, … cells from D:\golmok_synth\zones\index` → `zone_index: done …` → 레벨 저장 → `import_result.json`에 `"index": {...}`. **§4 전에** `git checkout -- unreal/Golmok/Content/Golmok/Zones`로 되돌린다(Content index가 합성 zone의 것으로 바뀌므로).

## 2. 빌드
```powershell
git pull
.\tools\ue\build.ps1          # Development Editor
```
- [ ] 컴파일 성공(경고는 기록). 실패 시 §11 표 번호로 고치고 `WP-09: PC fix …` 커밋. 먼저 볼 곳: #1(`FStreamableManager` 값 멤버), #2(`RequestAsyncLoad` 오버로드 — 이름 있는 `FStreamableDelegate Done` 변수), #5(`CreateWeakLambda`), #11/#26(`SetTimerForNextTick`의 `FTimerHandle` 반환), #12(`AsyncLoadHighPriority`), #15(`GRenderThreadTimeCriticalPath`는 매크로 2일 때만 컴파일), #22(`TFunction`의 `operator bool`), #23(`FFileHelper::LoadFileToString(..., EHashOptions::None, FILEREAD_Silent)` 인자 순서), MSVC C4458(§11 #30).
- [ ] `.\tools\ue\open-editor.ps1` → 에러 없이 열림. `L_ZoneTest`를 열어도 **에디터 월드에서는 발견하지 않는다**(`IsDiscoveryActive()`가 게임 월드만 true): 아웃라이너에 `Golmok/Zones/Discovered` 폴더 없음, Output Log에 `GolmokZoneSubsystem: zone index …` 줄 없음.

## 3. 헤드리스 자동화
에디터를 닫고:
```powershell
.\tools\ue\test.ps1 -Filter Golmok.Zone
.\tools\ue\test.ps1 -Filter Golmok. -SetupDevLevel
```
- [ ] 첫 명령: 5개 전부 `Success`(`-nullrhi`). 기대 `[Info]` 줄(테스트 코드 `AddInfo`):
  ```
  Golmok.Zone.IndexParse           [Info] content index <Content>/Golmok/Zones/index: 3 zones      (§1 전이면 "no content index at … (run zone_index.sync)")
                                   [Info] schema_version 2 -> unsupported schema_version 2 (expected 1)   (오류 8케이스 각 1줄; cell z 15 -> z 15 != 16)
                                   [Info] cells 3x3 (winning order per cell, * = center, - = no file): …   (메모리 리더의 Describe 블록)
  Golmok.Zone.IndexDiscover        [Info] z_synthetic_002 discovered after x.xx s      (≤ DiscoveryIntervalSeconds + 1 = 3 s)
                                   [Info] golmok.zone.index via GEngine->Exec: handled   ("not handled"여도 통과 — §11 #27; DescribeIndex()는 별도로 찍힘)
  Golmok.Zone.AsyncLoad            [Info] asset packages: 4 existing, 0 missing        (001 에셋이 프로젝트에 있으므로 비동기 분기)
                                   [Info] async load finished after x.xx s: missing 0, error ''
  Golmok.Zone.AsyncCancel          [Info] asset packages: 4 existing, 0 missing
                                   [Info] second request finished after x.xx s
  Golmok.Zone.InteriorNotBlocked   [Info]   z_synthetic_001_interior     v1   prio 20   unloaded  dist    >=  8.x m portal [placed]   (행 Info 3~4줄)
  ```
  `asset packages: 0 existing, 4 missing` + `no assets: synchronous fallback exercised`가 나오면 `L_Dev`에서 001 에셋을 못 찾은 것(`/Game/Golmok/Zones/z_synthetic_001/v1/SM_chunk_*`·`SM_z_synthetic_001_collision` 확인) — 통과는 하지만 비동기 경로를 검증하지 못했으므로 §12에 기록. `Golmok.Zone.IndexDiscover`/`InteriorNotBlocked`가 `[Info] skipped: run synthetic_zone.run()`이면 `L_ZoneTest`가 없는 것(전제 위반).
- [ ] 두 번째 명령: **16개** 전부 `Success` = WP-05까지 11개(`Golmok.Player.Movement`, `Lighting.PresetsFile/PresetApply`, `Debug.StatsMath/PathFormat/PathRoundTrip/HudStats`, `Portal.SpawnFromManifest/RoundTrip/PawnSwap/SharedInterior`) + 위 5개. 실내 서브레벨이 없으면 `Portal.RoundTrip/PawnSwap/SharedInterior` 3개는 skip Info(전제상 있어야 함). `test.ps1` 요약 줄 `Succeeded:`는 Warning이 있는 테스트를 따로 세므로(V-03) 상태 열이 전부 `Success`인지로 본다.
- [ ] `Golmok.Portal.SpawnFromManifest`가 동기 경로(`Zone->bAsyncLoad = false;` — 로그 `Zone z_synthetic_001 v1 loaded in x ms: …`)로, `Golmok.Zone.AsyncLoad`가 비동기 경로(`AsyncLoadCount==1` — 로그 `Zone z_synthetic_001 v1: async load requested (4 assets, 0 missing, priority 0)` → `Zone z_synthetic_001 v1 loaded (async x.x ms wait + y.y ms build): …`)로 통과. `Golmok.Portal.RoundTrip`은 이제 실내를 비동기로 로드하므로 `[Info] cycle 1: interior ready after x.xx s …`의 시간이 V-03(0.03 s)보다 길 수 있다(`StreamInTimeoutSeconds` 5.0 안이면 정상; 넘으면 §11 #32).
- [ ] `Golmok.log`에 `GolmokZoneSubsystem: … called while zone record pointers are held (depth …, violation …)`·`async finish of zone … called while zone record pointers are held …` **Error가 0건**(재진입 규약; 5개 테스트가 `GetReentrancyViolations()==0`을 단언).
- [ ] 셀 공식 g++ 교차검증(`tools/tests/test_ue_geo_math.py`)은 클라우드 CI에서 이미 초록; MSVC `tan/asinh` 마지막 ulp 차이는 셀 경계 위의 점에서만 드러나므로(§11 #20) `Golmok.Zone.IndexParse`의 `LonLatToCell(126.9250, 37.5620, 16) == (55873, 25379)`·`(126.9272665, 37.5620) → (55874, 25379)` 단언 통과만 확인하고 §12에 "경계 점 없음"으로 적는다.
- [ ] 실패한 테스트는 `unreal\Golmok\Saved\Logs\Golmok.log`의 `[Error]` 줄을 §12에 옮겨 적는다.

## 4. PIE 발견(배치 액터 없이)
검증용 맵 사본 `L_ZoneTest09`를 만들고 `Zone_*` 액터만 지운다(GeoOrigin·바닥·PlayerStart·조명·서브레벨 등록 유지). 원본 `L_ZoneTest`는 자동화 테스트가 계속 쓰므로 건드리지 않는다(`.gitignore`에 사본 포함). Output Log → Python:
```python
import unreal
unreal.EditorAssetLibrary.duplicate_asset("/Game/Golmok/Maps/L_ZoneTest", "/Game/Golmok/Maps/L_ZoneTest09")
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); les.load_level("/Game/Golmok/Maps/L_ZoneTest09")
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if a.get_actor_label() in ("Zone_z_synthetic_001", "Zone_z_synthetic_001_interior"):
        eas.destroy_actor(a)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.EditorLoadingAndSavingUtils.save_map(world, "/Game/Golmok/Maps/L_ZoneTest09")
```
- [ ] `L_ZoneTest09`에 `AGolmokZone` 0개(`Portal_…`은 Transient라 원래 저장되지 않음). PIE 시작 = PlayerStart(001 zone-local (0, −5, 0) m) = 셀 `16/55873/25380`.

PIE 시작(HUD F1). 시작 로그(WP-05 §3의 `GolmokDebugSubsystem: ready …`·`TimeOfDay: …` 줄 사이):
```
LogGolmok: GolmokZoneSubsystem: zone index <Content>/Golmok/Zones/index: 3 zones; discovery every 2.0 s
LogGolmok: GolmokZoneSubsystem: 0 zones registered; load < 150 m, unload > 250 m, every 0.50 s
```
- [ ] 위 두 줄(zone 0개 등록 — 배치 액터가 없으므로). `GolmokZoneSubsystem: no zone index at …; discovery off`면 §1이 안 된 것, `zone index …: <오류>; discovery off`(Warning)면 `zones.json` 파싱 실패 → §12.
- [ ] **첫 Evaluate 타이머(0.5 s) 안** 발견 로그(순서: 없는 셀 파일 Log 5개 → 스폰 3개 → 요약):
  ```
  LogGolmok: GolmokZoneIndex: no cell file <Content>/Golmok/Zones/index/cells/16_55872_25379.json (empty cell)     (16_55872_25380, 16_55872_25381, 16_55873_25381, 16_55874_25381도 — 셀당 1회, 다시 안 나옴)
  LogGolmok: GolmokZoneSubsystem: zone z_synthetic_001_interior v1 discovered from index (cell 16/55873/25380)
  LogGolmok: GolmokZoneSubsystem: zone z_synthetic_001 v1 discovered from index (cell 16/55873/25380)
  LogGolmok: GolmokZoneSubsystem: zone z_synthetic_002 v1 discovered from index (cell 16/55873/25380)
  LogGolmok: GolmokZoneSubsystem: discovery: cell 16/55873/25380, 3x3 zones 3, spawned 3, destroyed 0, retired 0, actors 3
  ```
  스폰 순서는 `CollectAround`의 셀 순서(y 오름차순 → x 오름차순, 셀 안은 이기는 순서, id 중복 제거)라 **001_interior → 001 → 002**다(설계 §6 예시는 001을 먼저 적었으나 코드 순서가 정본). 셀 `16/55873/25380`이 아니라 `…/25379`로 찍히면 폰이 북쪽 경계(4.6 m)를 넘은 것 — 무해(3×3이 같은 4셀을 덮는다).
- [ ] 같은 틱의 `Evaluate()`가 발견 zone의 manifest를 읽고(각 zone `Zone <id> v1 root: zone-local (0,0,0) -> UE (…) cm; …` 줄 — 001은 (17670.59, -22198.00, 999.37), 001_interior는 (18170.6x, -23498.0x, 999.3x)), 001(dist 0 m < 150 m)만 로드를 시작한다(`MaxLoadsPerUpdate=1`; 002는 184 m라 아직 아님, 실내는 `bAutoManageInterior=False`라 거리 관리 밖):
  ```
  LogGolmok: Zone z_synthetic_001 v1: async load requested (4 assets, 0 missing, priority 0)
  (다음 틱)
  LogGolmok: Zone z_synthetic_001: chunk chunk_00 bbox center -> level (…) cm          (chunk_01, chunk_02도)
  LogGolmok: Zone z_synthetic_001: blocker glass_1 (glass) rel (…) cm yaw … extent (…) -> level (…)
  LogGolmok: Zone z_synthetic_001: portal door_1 -> z_synthetic_001_interior rel (500, -950, 0) cm yaw -90.0 radius 150 cm -> level (18170.57, -23148.01, 999.32) [entry]
  LogGolmok: Zone z_synthetic_001 v1 loaded (async x.x ms wait + y.y ms build): chunks 3/3 (0 wire boxes), collision 1/1, blockers 1/1, portals 1 (WP-05)
  ```
  `priority 0` = `DefaultAsyncLoadPriority`(거리 로드). `Zone z_synthetic_001 v1: RequestAsyncLoad refused; loading synchronously`(Warning) 뒤 `loaded in x ms`가 나오면 스트리머가 핸들을 안 준 것 → §11 #1·#2. `x.x ms wait`는 엔진 완료 델리게이트가 `RequestAsyncLoad` 안에서 동기로 오는지(= 다음 틱 1회 대기만) 지연 헬퍼로 오는지에 따라 다르다 — §12에 값 기록(§11 #3).
- [ ] `golmok.zone.index` → (열 정렬 공백은 로그 폰트에 따라 달라 보일 수 있음; 001이 로드된 뒤의 값)
  ```
  golmok.zone.index
  index: <Content>/Golmok/Zones/index (3 zones, 9 cells cached, 5 missing cell files)
  discovery: on every 2.0 s, despawn > 500 m after 10 s, 3 discovered actors, 0 loading
  player: lon 126.9250xx lat 37.5619xx -> cell 16/55873/25380 (W 126.9196 E 126.9250 S 37.5576 N 37.5620)
  cells 3x3 (winning order per cell, * = center, - = no file):
    16/55872/25379 -                                                                   16/55873/25379 z_synthetic_001_interior@v1 z_synthetic_001@v1                      16/55874/25379 z_synthetic_001_interior@v1 z_synthetic_001@v1 z_synthetic_002@v1
    16/55872/25380 -                                                                   16/55873/25380 * z_synthetic_001@v1                                                16/55874/25380 z_synthetic_001@v1 z_synthetic_002@v1
    16/55872/25381 -                                                                   16/55873/25381 -                                                                   16/55874/25381 -
  near:  z_synthetic_001_interior@v1 [index, unloaded]  z_synthetic_001@v1 [index, loaded]  z_synthetic_002@v1 [index, unloaded]
  ```
  설계와 다름: 설계 §6 예시의 `4 cells cached`는 파일이 있는 셀만 센 것이고 코드 `NumCachedCells()`는 3×3 전부(파일 4 + 없음 5 = **9**)를 캐시로 센다; `near:` 순서는 위와 같이 001_interior가 먼저. `despawn > 500 m` = `DespawnDistanceM=0` → `2 × UnloadRadiusM`. `player:` 줄의 lat/lon은 HUD `pos` 줄과 같은 값(V-03: lat 37.561955 lon 126.925000). 셀 경계(`W … N …`)는 `GolmokGeoMath::CellBounds` = Python `tile_bounds`. `golmok.zone.index reload` → `LogGolmok: GolmokZoneSubsystem: index reloaded: 3 zones` 뒤 같은 블록(캐시 비움·재파싱·즉시 발견; 이미 등록된 id는 다시 스폰하지 않는다).
- [ ] `golmok.zone.list` →
  ```
  golmok.zone.list
  3 zones (load < 150 m, unload > 250 m), N basemap actors tagged, 3 discovered, 0 loading
    z_synthetic_001_interior     v1   prio 20   unloaded  dist    >=  8.x m [index]
    z_synthetic_001              v1   prio 10   loaded    dist      0.0 m [index]
    z_synthetic_002              v1   prio 10   unloaded  dist    184.x m [index]
  ```
  헤더는 WP-04 접두(`N zones (load < … m, unload > … m), K basemap actors tagged`) 뒤에 `, 3 discovered, 0 loading`만 붙는다. 로드 중인 순간에는 상태 열 `loading` + 행 끝 ` (loading 0.x s) [index]`, 헤더 `1 loading`.
- [ ] HUD `zones:` 첫 줄 = 같은 헤더(`zones: 3 zones (load < 150 m, unload > 250 m), N basemap actors tagged, 3 discovered, 0 loading`) + 위 3행(최대 4행).
- [ ] 아웃라이너(PIE 월드) `Golmok/Zones/Discovered`에 라벨 `Zone_z_synthetic_001_interior (index)`·`Zone_z_synthetic_001 (index)`·`Zone_z_synthetic_002 (index)` 3개(Transient; 디테일 `SpawnedFromIndex` ✔). PIE 종료 뒤 에디터 월드에 남지 않고 `L_ZoneTest09`가 dirty가 아니다(`SetActorLabel(..., bMarkDirty=false)`).
- [ ] `golmok.zone.radius 300 400` → `LogGolmok: GolmokZoneSubsystem: radii now load < 300 m, unload > 400 m` → 즉시 `Evaluate()` → 002(184 m) 로드. 002는 에셋 패키지가 없어 `CollectAssetPaths()`가 0개 → **`async load requested` 없이 동기 경로**:
  ```
  LogGolmok: Zone z_synthetic_002: chunk asset /Game/Golmok/Zones/z_synthetic_002/v1/SM_c_e000_n000.SM_c_e000_n000 missing; drawing its bbox as a wire box      (Warning; c_w001_n000도)
  LogGolmok: Zone z_synthetic_002: collision asset /Game/Golmok/Zones/z_synthetic_002/v1/SM_z_synthetic_002_collision_c_e000_n000.SM_z_synthetic_002_collision_c_e000_n000 missing; the player will fall through this zone.      (Warning; c_w001_n000도)
  LogGolmok: Zone z_synthetic_002: blocker glass_1 (glass) rel (…) cm yaw … extent (…) -> level (…)
  LogGolmok: Zone z_synthetic_002 v1 loaded in x.x ms: chunks 0/2 (2 wire boxes), collision 0/2, blockers 1/1, portals 0 (WP-05)
  ```
  001 동쪽 200 m에 **주황 와이어 박스 2개**(청크 bbox). 위 4개 Warning은 우리 로그(`bDrawMissingAssetBoxes=True`)이고 정상; **엔진 `LogStreaming`/`LogStreamableManager`의 `Couldn't find file for package …` 경고는 없어야** 한다(`DoesPackageExist` 사전 검사로 없는 패키지는 요청하지 않음 — 나오면 §11 #8·#18). `golmok.zone.list` 002 행 `loaded    dist    184.x m [index]`.
- [ ] `golmok.zone.refresh` → `golmok.zone.refresh: basemap rescanned, index discovery run and zones re-evaluated`(발견 → 평가 순서; 새 스폰 없음이면 `discovery:` 요약 줄은 안 찍힌다 — 스폰·파괴·retire가 0이면 침묵).

## 5. 걸어 나가서 파괴
에디터 Python PIE 드라이버(V-03 방식: `set_actor_location` 텔레포트)로 폰을 001 동쪽 **1.5 km**로 옮긴다. 셀은 `16/55877/25380`(lon ≈ 126.942; 3×3 = x 55876..55878, y 25379..25381 — 셀 파일 4개와 겹치지 않음), 001 footprint까지 ≈ 1,500 m·002까지 ≈ 1,300 m > `DespawnDistanceM`(500 m). PIE 중 Output Log → Python:
```python
import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
pawn.set_actor_location(pawn.get_actor_location() + unreal.Vector(150000.0, 0.0, 0.0), False, True)   # +1.5 km east (UE X), teleport
```
(`L_ZoneTest09`의 `Zone_Ground` 400 m 지면 밖이라 폰이 떨어진다 — 낙하해도 XY는 유지되므로 판정에 무관. 걷기로 하려면 `golmok.path play`로 원거리 경로 재생, §11 #34.)
- [ ] 다음 Evaluate(≤ 0.5 s): 반경 밖 → 001·002 언로드:
  ```
  LogGolmok: Zone z_synthetic_001 v1 unloaded
  LogGolmok: Zone z_synthetic_002 v1 unloaded
  ```
  (`golmok.zone.radius 300 400`을 되돌리지 않았어도 400 m < 1.3 km라 같다.) 001이 아직 `Loading`이었다면 대신 `Zone z_synthetic_001 v1: async load cancelled after x.x ms`(`Zone … unloaded` 줄 없음 — 만든 게 없으므로).
- [ ] 다음 발견(≤ 2 s): 새 3×3에 셀 파일이 없어 `GolmokZoneIndex: no cell file …/16_55876_25379.json (empty cell)` 등 Log 9줄(1회씩), 스폰 0 → `discovery:` 요약 없음. `golmok.zone.index` → `player: … -> cell 16/55877/25380 …`, `cells 3x3` 전부 `-`, `near: (none)`, `index: … (3 zones, 18 cells cached, 14 missing cell files)`(캐시는 `MaxCachedCells=64`까지 유지; 넘으면 `GolmokZoneIndex: cell cache trimmed by N (kept M around 16_…)`).
- [ ] 첫 발견 패스가 `DespawnEligibleSince`를 찍고 **10 s(`DespawnGraceSeconds`) 이상 지난 다음 패스**(도착 후 10~12 s)에 3건이 한 번에 파괴된다(`MaxDestroysPerDiscovery=4`):
  ```
  LogGolmok: GolmokZoneSubsystem: zone z_synthetic_001_interior despawned (index; 15xx m, cells far)
  LogGolmok: GolmokZoneSubsystem: zone z_synthetic_001 despawned (index; 15xx m, cells far)
  LogGolmok: GolmokZoneSubsystem: zone z_synthetic_002 despawned (index; 13xx m, cells far)
  LogGolmok: GolmokZoneSubsystem: discovery: cell 16/55877/25380, 3x3 zones 0, spawned 0, destroyed 3, retired 0, actors 0
  ```
  (실내는 부모 001이 Unloaded라 함께 파괴된다 — 부모가 Loaded/Loading이면 남는다.) `golmok.zone.list` → `0 zones (load < … m, unload > … m), N basemap actors tagged, 0 discovered, 0 loading`; 아웃라이너 `Discovered` 폴더 비어 있음.
- [ ] 되돌아오기(`unreal.Vector(-150000.0, 0.0, 0.0)`): ≤ 2 s 안에 §4의 발견 로그 3줄 + `discovery: cell 16/55873/25380, 3x3 zones 3, spawned 3, destroyed 0, retired 0, actors 3`, 001 재로드(`async load requested` → `loaded (async …)`), 목록 `3 discovered`. 파괴 없이 셀 경계만 오가면(예: 북으로 5 m) 파괴·재스폰이 **일어나지 않는다**(3×3이 겹치고 거리 < 500 m).

## 6. 히치 비교(bAsyncLoad True/False)
비동기 로드의 유일한 실전 사례는 **에셋이 있는 001의 언로드 → 재로드**다(002는 에셋이 없어 항상 동기 폴백, 실내는 포털이 관리). 60 s 경로 안에 그 사이클을 넣기 위해 반경을 줄인다(설계와 다름: 설계 §9-6의 "원점 → 001 → 002 왕복"은 001을 반경 밖으로 내보내지 못하고 160 s가 걸려 아래로 바꿈). `L_ZoneTest09`(발견 zone) 또는 `L_ZoneTest`(배치 zone) 어느 쪽이든 같다.
```
golmok.zone.radius 60 100         → GolmokZoneSubsystem: radii now load < 60 m, unload > 100 m
golmok.path record hitch          → golmok.path record: recording 'hitch' at 10 Hz (level L_ZoneTest09)
   3 s 제자리 → 남쪽 ~120 m(001 언로드, dist > 100) → PlayerStart로 복귀(001 재로드, dist < 60) → 동쪽 ~130 m(002 로드, 60 m 전 = x ≈ 125 m) → 복귀   ≈ 60 s
golmok.path stop                  → golmok.path stop: path 'hitch' saved: ~600 samples, 60.x s -> <Saved>\Golmok\Paths\hitch.json
golmok.zone.radius 60 100         (재생 전마다; 반경은 ini에 저장되지 않는다)
golmok.path play hitch --csv      → golmok.path play: path play 'hitch' (60.x s, 60x samples) + CsvProfile
                                    GolmokDebugSubsystem: CsvProfile Start (path 'hitch')
                                    … GolmokDebugSubsystem: csv: <Saved>\Profiling\CSV\Profile(…).csv  ->  golmok-perf "<abs>\Profile(…).csv" --label hitch --markdown
                                    GolmokDebugSubsystem: path play 'hitch' finished (end of path) after 60.x s
```
1. **async**(ini 기본 `bAsyncLoad=True`): 재생 1회 → CSV를 `hitch_async.csv`로 복사. 재생 중 로그:
   ```
   LogGolmok: Zone z_synthetic_001 v1 unloaded
   LogGolmok: Zone z_synthetic_001 v1: async load requested (4 assets, 0 missing, priority 0)
   LogGolmok: Zone z_synthetic_001 v1 loaded (async x.x ms wait + y.y ms build): chunks 3/3 (0 wire boxes), collision 1/1, blockers 1/1, portals 1 (WP-05)
   LogGolmok: Zone z_synthetic_002 v1 loaded in x.x ms: chunks 0/2 (2 wire boxes), collision 0/2, blockers 1/1, portals 0 (WP-05)
   ```
2. **sync**: `Config\DefaultGame.ini` `[/Script/Golmok.GolmokZone]` `bAsyncLoad=False`로 바꾸고 **에디터 재시작**(Config 프로퍼티는 CDO 로드 때 읽힌다) → 같은 맵 PIE → `golmok.zone.radius 60 100` → 재생 → CSV를 `hitch_sync.csv`로. 로그는 `Zone z_synthetic_001 v1 loaded in x.x ms: chunks 3/3 …`(`async` 문구 없음; 이 `x.x ms`가 `StaticLoadObject` 4개를 포함한 스파이크). 끝나면 ini를 `True`로 **되돌리고** 재시작(`git diff`에 남기지 않는다).
3. 표:
   ```powershell
   cd tools; golmok-perf "<abs>\hitch_async.csv" "<abs>\hitch_sync.csv" --label async --label sync --markdown
   ```
- [ ] `golmok-perf` 표 2행(`| 구성 | 프레임 | 평균 fps | 1% low fps | 프레임 p50 ms | p99 ms | Game ms | Render ms | GPU ms |`)을 §12에 붙인다. 설계와 다름: `golmok-perf`에는 "최대 프레임 ms" 열이 없다 — 최대값은 CSV `FrameTime` 열의 max를 따로 읽어(예: `python -c "import csv,sys; …"`) 표 옆에 적거나 생략하고 p99로 갈음(§12에 어느 쪽인지 명시).
- [ ] 기대: sync 쪽 p99·최대 프레임에 001 재로드 시점의 스파이크, async 쪽에서 감소하고 대신 `loaded (async x.x ms wait …)`의 wait가 수십~수백 ms. 합성 zone은 메시가 작아 차이가 수 ms 이하일 수 있다 — 수치만 정직하게 기록(판정 기준은 "async가 sync보다 나쁘지 않다").
- [ ] 로그 `loaded in X ms`(sync) vs `loaded (async X ms wait + Y ms build)`(async)의 X·Y를 §12에.
- [ ] 스크린샷은 `golmok.hud 0` 뒤 `golmok.screenshot wp09 hitch`(HUD가 켜져 있으면 캡처에 포함된다 — V-03).

## 7. render ms
HUD(F1) `game … ms  render … ms  gpu … ms` 줄과 `stat unit`의 `Draw`를 같은 순간에 5회 읽는다(2 s 창마다 1회, 걷는 중·정지 중 섞어서). 소스 1(`OnBeginFrame`에서 직전 프레임 `GRenderThreadTime` 캐시) + 0 샘플은 직전 유효값 유지(`HoldLastPositive`).
- [ ] `golmok.stats` → 두 줄:
  ```
  golmok.stats: fps 158.3  1% low 121.0  game 1.75 ms  render 6.98 ms  gpu 5.99 ms  (2.0 s, 316 fr)
  golmok.stats: render source 1: begin 123456 cycles, end 0 cycles, held 3/1200 frames (since bind)
  ```
  둘째 줄 = `DescribeRenderSource()`: `begin` = 이번 프레임 `OnBeginFrame`에서 읽은 `GRenderThreadTime`(cycles), `end` = 같은 프레임 `OnEndFrame`에서 읽은 값(소스 0이 쓰던 값; V-03에서 0이 잦았던 그것), `held a/b` = 샘플러가 바인드된 뒤(PIE 시작·HUD 켠 뒤) 유지된 샘플 수 / 전체 샘플 수, 마지막 샘플이 유지였으면 ` (since bind, last held)`. 설계와 다름: 설계 §3-6의 `(window)`(2 s 창)가 아니라 **바인드 이후 누적**이다 — 비율 `a/b`로 비교한다.
- [ ] 표(§12): 5회 × (HUD render, `stat unit` Draw, `held a/b`). 기대: HUD render ≈ Draw ±0.5 ms, `0.00`이 **한 번도 없음**, held 비율 낮음(수 % 이하; 소스 1에서 `end 0 cycles`가 잦아도 `begin`이 0이 아니면 정상 — 그게 V-03의 원인 확인이다).
- [ ] `0.00`이 남거나 held 비율이 높으면 `Debug/GolmokDebugSubsystem.cpp` 상단 `#define GOLMOK_RENDER_TIME_SOURCE 2`(`GRenderThreadTimeCriticalPath`; 링크 오류면 §11 #15)로 재빌드해 같은 표, 그래도면 `0`(구동작 + hold). **held 비율이 가장 낮은 소스를 매크로 기본값으로 커밋**(`WP-09: PC fix render source N`)하고 §12에 세 소스의 표를 남긴다. 어느 소스든 `FormatStatsLine()` 형식·HUD 줄·`Golmok.Debug.HudStats`는 그대로다.

## 8. 실내 표시·포털 대기
`L_ZoneTest`(배치 실내; §4 사본에서는 실내가 `[index]`로 발견되고 나머지는 같다)에서 문 왕복(V-03 §5: 문 x = +5 m, 트리거 반경 1.5 m, 북쪽이 실내). PIE를 시작하면 002도 index에서 발견돼 `golmok.zone.list`가 3행(`z_synthetic_002 … [index]`)이 된다 — 정상.
- [ ] 기대 로그 **순서**(비동기, `bAsyncLoad=True`):
  ```
  ① 트리거 진입 다음 틱(선로드; RequestLoad가 먼저 실행되므로 Zone 줄이 Portal 줄보다 앞)
     LogGolmok: Zone z_synthetic_001_interior v1: async load requested (2 assets, 0 missing, priority 100)
     LogGolmok: Portal door_1: interior preload requested -> zone z_synthetic_001_interior loading (pinned)
  ② 그다음 틱(완료는 항상 다음 틱)
     LogGolmok: Zone z_synthetic_001_interior: chunk room bbox center -> level (18170.6x, -23498.0x, 1159.3x) cm
     LogGolmok: Zone z_synthetic_001_interior: portal door_out -> z_synthetic_001 rel (0, 350, 0) cm yaw 90.0 radius 150 cm -> level (18170.57, -23148.01, 999.32) [marker]
     LogGolmok: Zone z_synthetic_001_interior v1 loaded (async x.x ms wait + y.y ms build): chunks 1/1 (0 wire boxes), collision 1/1, blockers 0/0, portals 1 (WP-05)
  ③ 디바운스 끝(진입 0.25 s 뒤) — 실내가 아직 Loading이면 먼저 이 줄(1회)과 0.05 s 폴링:
     LogGolmok: Portal door_1: interior loading; waiting (poll 0.05 s, at most 10 s)
     그리고 Loaded가 된 다음 폴링에서:
     LogGolmok: Portal door_1 (z_synthetic_001 -> z_synthetic_001_interior): player within 150 cm -> load [zone z_synthetic_001_interior loaded (pinned)]; sublevel /Game/Golmok/Zones/z_synthetic_001_interior/v1/L_z_synthetic_001_interior (LevelInstance)
  ④ 문 평면 통과·복귀는 V-03 그대로: TimeOfDay: interior overlay on (source door_1, base …) → Portal door_1: crossed inward → … overlay off → crossed outward
  ⑤ 박스를 남쪽으로 벗어난 뒤 3 s
     LogGolmok: Zone z_synthetic_001_interior v1 unloaded
     LogGolmok: Portal door_1: player left -> unload z_synthetic_001_interior (zone z_synthetic_001_interior unloaded (portal)); sublevel out
  ```
  `priority 100` = `AsyncLoadHighPriority`(pin). ③의 `waiting` 줄은 실내가 0.25 s 안에 로드되면 나오지 않는다(합성 실내는 보통 그렇다 — 나왔는지 여부와 `pending(loading x.x s)`가 보였는지 §12에). 설계와 다름: ⑤의 Portal 줄은 WP-05의 `player left -> unload z_synthetic_001_interior; sublevel out`이 아니라 괄호 안에 `RequestUnload` 메시지(`zone … unloaded (portal)`)가 들어간다.
- [ ] **문을 지나도 바닥이 있다**(방 안 낙하 없음): 포털은 실내가 `Loaded`가 될 때까지 `Active`가 되지 않으므로(Pending 유지) 방에 들어섰을 때 충돌 메시가 이미 있다. `golmok.portal list`가 대기 중이면 `door_1 (z_synthetic_001 -> z_synthetic_001_interior) pending(loading 0.3 s) outside; sublevel none (LevelInstance)`.
- [ ] ⑤ 뒤 `golmok.zone.list` 실내 행:
  ```
    z_synthetic_001_interior     v1   prio 20   unloaded  dist    >=  8.x m portal [placed]
  ```
  ` blocked` 없음, HUD `zones:` 블록도 동일. 이후 `Evaluate()`가 실내를 다시 로드하지 않는다(`bPortalManaged`는 거리 관리 제외; `bAutoManageInterior=True`로 바꿔도 마찬가지 — 기본값 False라 기본 동작은 WP-04와 같다). 다시 문에 가면 ①부터 반복되고 ` portal`이 유지된다.
- [ ] `golmok.zone.unload z_synthetic_001_interior` → `golmok.zone.unload: zone z_synthetic_001_interior unloaded (auto-load resumes after leaving the unload radius)` → 행 `unloaded … blocked [placed]`(콘솔 출처 회귀; ` portal` 사라짐). `golmok.zone.load z_synthetic_001_interior` → `golmok.zone.load: zone z_synthetic_001_interior loading (pinned)`(동기면 `loaded (pinned)`) → 행 `loading … pinned (loading 0.x s) [placed]` → 다음 틱 `loaded … pinned [placed]`. `golmok.zone.unload`로 정리.
- [ ] **3 s 안에 되돌아 나오기**(트리거 진입 → 바로 후퇴): 로그 순서 `interior preload requested` → 디바운스 전에 나갔으면 `Portal door_1` 상태가 `Active`를 거쳐 Leaving(디테일 `LastEvent = left trigger outward while interior loading` 또는 `left before interior loaded`) → 3 s 뒤 실내가 아직 `Loading`이면:
  ```
  LogGolmok: Zone z_synthetic_001_interior v1: async load cancelled after x.x ms
  LogGolmok: Portal door_1: player left -> unload z_synthetic_001_interior (zone z_synthetic_001_interior load cancelled); sublevel out
  ```
  (합성 실내는 3 s 안에 로드되므로 대개 ⑤의 `unloaded` 줄이 나온다 — 취소 줄을 보려면 §10의 "Loading 중 PIE 종료"로 확인.) 3 s 안 재진입은 V-03과 같이 ⑤가 찍히지 않는다(`re-entered trigger; unload cancelled`).
- [ ] `golmok.portal enter door_1`(걷지 않고): 실내가 `Loading`이면 `golmok.portal enter: Portal door_1 (z_synthetic_001 -> z_synthetic_001_interior): interior loading; activates when ready [zone z_synthetic_001_interior loading (pinned)]` → 폴링 → ③의 Portal 줄로 Active; 이미 Loaded면 `golmok.portal enter: Portal door_1 (…): active [zone z_synthetic_001_interior loaded (pinned)]; sublevel …`. 대기 중 `golmok.portal leave door_1` → `golmok.portal leave: portal door_1 leaving (interior was still loading); z_synthetic_001_interior unloads in 3.0 s`.
- [ ] 10 s 상한(`InteriorLoadTimeoutSeconds`, .cpp 상수): 실내 로드가 10 s를 넘기면 Warning `Portal door_1: interior still loading after 10.0 s; activating anyway` 뒤 ③의 Portal 줄이 `-> load [zone z_synthetic_001_interior loading (pinned)]`로 찍힌다 — 합성 실내에서는 나오면 안 된다(나오면 §12에 원인).
- [ ] `bAsyncLoad=False`(§6-2 상태)에서 같은 왕복: ①이 `Zone … loaded in x ms` + `interior preload requested -> zone z_synthetic_001_interior loaded (pinned)`, ③의 `waiting` 줄 없음, 나머지 동일(WP-05 타이밍).

## 9. (선택) 패키징
- [ ] `.\tools\ue\package.ps1` → `UnrealPak <pak> -List | findstr /i "Golmok/Zones/index"` → `Golmok/Zones/index/zones.json`·`Golmok/Zones/index/cells/16_55873_25379.json` 등 5개(기존 `+DirectoriesToAlwaysStageAsUFS=(Path="Golmok/Zones")` 줄이 덮음; `z_synthetic_002/v1/manifest.json`·`blockers.json`도).
- [ ] 실행 파일에서 `open L_ZoneTest09`(사본이 쿠킹 목록에 없으면 `L_ZoneTest`) → `golmok.zone.index` → `index: ../../../Golmok/Content/Golmok/Zones/index (3 zones, …)`, `discovery: on …`, `near:` 3개. `index: not found (…) - discovery off`면 UFS 스테이징 문제 → §12.
- [ ] 001 로드 로그가 `async load requested (4 assets, 0 missing, …)`인지: `(0 assets, 4 missing …)`은 아예 안 찍히고 대신 `loaded in x ms: chunks 0/3 (3 wire boxes), collision 0/1 …` + 와이어 박스만 보이면 `FPackageName::DoesPackageExist`가 쿠킹(IoStore)에서 false를 준 것 → §11 #8 대안(`#if WITH_EDITOR`에서만 검사)으로 고치고 §12에 기록.

## 10. PIE 종료 검사
- [ ] **`Loading` 중 종료**: `golmok.zone.unload z_synthetic_001` → `golmok.zone.load z_synthetic_001` 직후(같은 초 안에) PIE 종료 →
  ```
  LogGolmok: Zone z_synthetic_001 v1: async load cancelled after x.x ms
  ```
  (`EndPlay` → `Unload()` → `CancelAsyncLoad()`; `Deinitialize`가 남은 핸들을 전부 취소) 외에 Warning·Error·ensure 없음. `Zone … v1 loaded (async …)`가 종료 뒤에 찍히면 취소가 안 된 것(§11 #3·#4).
- [ ] **방 안(오버레이 on)에서 종료**: V-03 §10과 같이 `Portal door_1: end play while active -> sublevel out; zone unload scheduled`, `TimeOfDay: interior overlay off -> …`, zone `unloaded`, Error·ensure 없음. Pending(선로드 요청 후, `pending(loading …)`) 상태에서 종료해도 같다(`IsHoldingInterior()` → 다음 틱 `Portal door_1: gone -> zone z_synthetic_001_interior unloaded (portal)` 또는 `… load cancelled`).
- [ ] 종료 뒤 에디터 월드: 아웃라이너에 `Golmok/Zones/Discovered` 폴더·`Zone_* (index)` 액터 없음, Transient 포털·재생 폰 없음, `L_ZoneTest09`·`L_ZoneTest` dirty 아님(저장 프롬프트 없음).
- [ ] 다시 PIE → 발견·로드가 처음처럼 반복된다(`AsyncLoadCount`는 BeginPlay마다 0부터).

## 11. 컴파일 에러가 나면 — 불확실한 UE 5.8 API와 대안 (설계 §10, 번호 유지) + PC 세션 추가 행
클라우드 세션이 엔진 헤더로 직접 확인하지 못한 호출 목록(설계 §10 그대로, 번호 유지). 오류 메시지에 아래 이름이 보이면 대안으로 바꾼다. **35번 이후**는 PC 세션이 코드를 다시 읽어 표에 없던 호출을 보탠 것. `PC 결과` 열에 ✅(그대로 컴파일·동작) / 수정(대안 번호·커밋) / 미확인을 적는다.

| # | 파일 | API | 불확실한 점 | 대안 | PC 결과 |
|---|---|---|---|---|---|
| 1 | GolmokZoneSubsystem | `FStreamableManager Streamable;`를 `UWorldSubsystem` 값 멤버로(`FGCObject` 파생, 비복사) | `UAssetManager`가 같은 패턴. CDO에도 인스턴스 1개(무해) | `UAssetManager::IsInitialized() ? &UAssetManager::Get().GetStreamableManager() : nullptr`(`Engine/AssetManager.h`, 새 모듈 없음); null이면 동기 폴백 | |
| 2 | GolmokZone | `RequestAsyncLoad(TArray<FSoftObjectPath>, FStreamableDelegate, TAsyncLoadPriority, bool, bool, FString)` — 5.4+ `FStreamableAsyncLoadParams&&`·`TFunction` 오버로드 | 델리게이트를 이름 있는 변수로 넘기면 정확 일치 | ① `RequestAsyncLoad(MoveTemp(Paths), Done)` ② `FStreamableAsyncLoadParams P; P.TargetsToStream = MoveTemp(Paths); P.OnComplete = FStreamableDelegateWithHandle::CreateWeakLambda(this, [this, Serial](TSharedPtr<FStreamableHandle>){ OnStreamableComplete(Serial); }); P.Priority = …; P.DebugName = …; RequestAsyncLoad(MoveTemp(P))` | |
| 3 | GolmokZone | 완료 델리게이트 발화 시점(`FStreamableDelegateDelayHelper`가 항상 다음 틱인지) | 불확실 — 설계가 의존하지 않음(항상 미룸 + 세대) | 런북 §4 로그로 관찰만 | |
| 4 | GolmokZone | `FStreamableHandle::CancelHandle()` 뒤 큐에 든 완료 델리게이트가 불리는지 | 불확실 | 세대 불일치로 무시. `ReleaseHandle()`은 쓰지 않는다(로드 계속·델리게이트 발화) | |
| 5 | GolmokZone | `FStreamableDelegate::CreateWeakLambda(UObject*, Lambda)` | `TDelegate::CreateWeakLambda` 4.2x+ | `CreateUObject(this, &AGolmokZone::OnStreamableComplete, Serial)`(payload) | |
| 6 | GolmokZone | `FSoftObjectPath(const FString&)`로 `/Game/…/SM_x.SM_x` 파싱 | 안정; `IsNull()`로 실패 검사 | `FSoftObjectPath P; P.SetPath(FStringView(Path));` | |
| 7 | GolmokZone | `FSoftObjectPath::ResolveObject()` | 안정(찾기만) | `StaticFindObject(UStaticMesh::StaticClass(), nullptr, *Path)`; 최후 `StaticLoadObject`(상주라 즉시) | |
| 8 | GolmokZone | `FPackageName::DoesPackageExist(const FString&)`, `FPackageName::ObjectPathToPackageName` | 전자는 V-03에서 컴파일 확인. 쿠킹(IoStore)에서 pak을 보는지 | 후자: `Path.Left(Path.Find(TEXT(".")))`. 전자가 쿠킹에서 false면(런북 §9) `#if WITH_EDITOR`에서만 검사하고 패키지 빌드는 `LogStreaming` 오류 허용 | |
| 9 | GolmokZoneSubsystem | `AActor::SetFolderPath(FName)`(`#if WITH_EDITOR`) | 에디터 전용 | 줄 삭제(라벨만) | |
| 10 | GolmokZoneSubsystem | `FActorSpawnParameters{bDeferConstruction, ObjectFlags\|RF_Transient, SpawnCollisionHandlingOverride}` + `FinishSpawning` | V-03에서 포털로 확인. `SpawnActorDeferred<T>`는 `ObjectFlags`를 못 받아 쓰지 않음 | `SpawnActorDeferred<AGolmokZone>(…)` 뒤 `Zone->SetFlags(RF_Transient)` | |
| 11 | GolmokZone / Portal | `FTimerManager::SetTimerForNextTick(UserClass*, MethodPtr)`가 **`FTimerHandle`을 반환** | 반환형 확인(4.2x+에서 반환); 저장해 `ClearTimer` | `FTimerHandle H = SetTimerForNextTick(FTimerDelegate::CreateUObject(this, &AGolmokZone::FinishAsyncLoad))`; 핸들이 없으면 `SetTimer(H, …, 0.001f, false)`; 어차피 세대 검사가 최종 방어 | |
| 12 | GolmokZone/Subsystem | `FStreamableManager::AsyncLoadHighPriority`(100)/`DefaultAsyncLoadPriority`(0), `TAsyncLoadPriority` | 정적 상수 이름 | 리터럴 `100`/`0` | |
| 13 | GolmokZone | `FStreamableHandle::HasLoadCompleted()/WasCanceled()` | 4.17+ 안정 | 상태 검사만 `State`로 | |
| 14 | GolmokZoneSubsystem | `FStreamableManager::SetManagerName(FString)` | 존재(4.2x+) | 줄 삭제 | |
| 15 | GolmokDebugSubsystem | `GRenderThreadTimeCriticalPath`(`RenderTimer.h`) | `GRenderThreadTime`과 같은 헤더라 봄 | 링크 오류면 소스 1(`#if == 2` 블록만 컴파일) | |
| 16 | GolmokDebugSubsystem | `FCoreDelegates::OnBeginFrame.AddUObject/Remove` | `OnEndFrame`과 쌍(V-03 확인) | `FWorldDelegates::OnWorldPreActorTick` | |
| 17 | GolmokDebugSubsystem | `GRenderThreadTime`이 `OnBeginFrame` 시점에 직전 프레임 최종값인지(0.00 원인) | 엔진 순서 미확인 | 매크로 0/1/2 + hold 규칙; 런북 §7이 확정 | |
| 18 | GolmokZoneTest | 자동화가 `LogStreamableManager`/`LogStreaming` Warning·Error에 반응 | 없는 패키지는 요청하지 않음 | 뜻밖의 경고면 `AddExpectedError(TEXT("Couldn't find file for package"), EAutomationExpectedErrorFlags::Contains, 0)` | |
| 19 | GolmokZoneSubsystem | `UWorld::HasBegunPlay()`, `UWorld::IsGameWorld()`, `UWorld::bIsTearingDown` | 후자는 WP-05에서 컴파일 확인 | `GetBegunPlay()`; `WorldType == Game/PIE` 직접 비교 | |
| 20 | GolmokGeoMath | `std::ldexp/asinh/sinh/atan`(`<cmath>`) MSVC | 안정. `tan/asinh` 마지막 ulp | 결과 차이는 셀 경계 위 점만; 런북 §3에 기록 | |
| 21 | GolmokZoneIndex | `TryGetArrayField/TryGetNumberField/TryGetStringField/TryGetObjectField(const FString&, …)` | V-03 확정: `FString` 키 객체 | `TryGetField(FStringView)` + `AsArray()/AsNumber()/AsString()` | |
| 22 | GolmokZoneIndex | `TFunction<bool(const FString&, FString&)>` 기본 생성·`operator bool` | `TFunction`에 `bool` 변환 있음 | 함수 포인터 + 컨텍스트 | |
| 23 | GolmokZoneIndex | `FFileHelper::LoadFileToString` + `IFileManager::Get().FileExists`가 UFS pak 안에서 동작 | WP-04 manifest로 확인 | 존재 검사 없이 `LoadFileToString` 실패를 "없음"으로 | |
| 24 | GolmokZone | `EGolmokZoneState`에 `Loading` 추가(끝) | BlueprintType enum 값 추가 안전; `State`는 Transient | — | |
| 25 | GolmokZoneSubsystem | `FStreamableManager` 소멸(GC) 시 살아있는 핸들 | `Deinitialize`에서 전 zone `CancelAsyncLoad()` | 문제면 `TUniquePtr<FStreamableManager>` + **사용자 선언 소멸자를 .cpp에 정의**(불완전형 함정 회피) 후 `Deinitialize`에서 명시 파괴 | |
| 26 | GolmokPortal | `SetTimerForNextTick(this, &AGolmokPortal::PreloadInterior)` UObject 메서드 오버로드 | #11과 동일 | `FTimerDelegate::CreateUObject` | |
| 27 | GolmokZoneTest | `GEngine->Exec(World, TEXT("golmok.zone.index"))` | 콘솔 실행 경로 | `UKismetSystemLibrary::ExecuteConsoleCommand` | |
| 28 | GolmokZoneTest | `IMPLEMENT_SIMPLE_AUTOMATION_TEST(…, EditorContext \| ProductFilter)`, `FStartPIECommand`, `GEditor->PlayWorld` | WP-05 4파일과 동일 패턴(V-03 통과) | — | |
| 29 | GolmokZoneSubsystem | `UGolmokGeoSubsystem::LevelUEToLonLat(const FVector&, double& Lat, double& Lon, double& H)` | 자체 코드(WP-04) | — | |
| 30 | 정적 검사 | MSVC C4458: `FGolmokZoneIndexCell` 멤버 `X/Y/Zoom`·`FGolmokZoneIndex` 멤버 `IndexDir` vs 정적 함수 인자 | `In*` 규칙 + pytest | 컴파일 오류 시 인자 이름만 변경 | |
| 31 | 유니티 빌드 | Zones/*.cpp 익명 namespace 이름(`MakeComponentName`, `ZoneSubsystemFor`, 새 `IndexJson*`, `CmdZoneIndex`) | 파일 접두 + pytest | 충돌 시 이름 변경 | |
| 32 | GolmokPortalTest | `StreamInTimeoutSeconds` 5.0이 비동기 실내 + 서브레벨 스트리밍에 충분한지 | 합성 실내는 에셋 수 개 | 부족하면 10.0(상한만; 결과에 기록) | |
| 33 | Python | `unreal.Paths.project_content_dir()` | WP-06 사용 | — | |
| 34 | 런북 | 콘솔 `teleport` 부재 → 에디터 Python 드라이버로 폰 이동 | V-03 방식 | `golmok.path play`로 원거리 경로 재생 | |
| 35+ | (PC 세션 추가 — 예: `FFileHelper::LoadFileToString(…, FFileHelper::EHashOptions::None, FILEREAD_Silent)` 인자 순서, `AActor::SetActorLabel(FString, bool bMarkDirty)`, `FString::Printf`의 `%llu`/`%u`, `TFunction` 명시적 `operator bool`) | | | | |

## 12. 결과 기록
V-07 PC 세션(… , 사용자 PC, 모델 …), 날짜 …. UE 5.8.3, VS …, 브랜치 `pc/v07-verify-wp09`.
**검증 방식**: (V-03과 같은 에디터 Python PIE 드라이버 여부, 키 입력 방식, 헤드리스 명령을 적는다.)

| 항목 | 결과 | 메모·실측 |
|---|---|---|
| 빌드 | | 컴파일 오류·링크 오류 건수, §11 번호, 커밋 |
| 헤드리스 자동화 16개(Zone 5 + 기존 11) | | `[Info]` 실측(discovered after, asset packages, finished after), 재진입 Error 0 |
| §1 index 동기화(`git status` 깨끗) | | |
| §4 발견(로그·`golmok.zone.index`·목록·HUD·아웃라이너) | | 발견까지 걸린 시간, `async … wait` ms |
| §4 002 동기 폴백(와이어 박스·엔진 LogStreaming 경고 0) | | |
| §5 파괴·재발견 | | 파괴까지 걸린 시간(10~12 s), `despawned … m` 값 |
| §6 히치 표(async / sync) | | `golmok-perf` 표 2행 + 최대 프레임 ms 출처, `loaded in X ms` vs `async X wait + Y build` |
| §7 render ms 소스·held 비율 | | 5회 표(소스 1; 필요 시 2·0), 커밋한 매크로 기본값 |
| §8 실내 표시·포털 대기 | | 로그 순서, `waiting` 줄 유무, `pending(loading …)`, `portal` 행, 콘솔 회귀, `load cancelled` |
| §9 패키징(선택) | | pak 목록, `-game` `golmok.zone.index`, `DoesPackageExist` 쿠킹 결과 |
| §10 PIE 종료 | | `async load cancelled`, Discovered 잔류 없음, dirty 없음 |
| 고친 API 번호(§11)·커밋 | | |
| 설계와 다른 동작 발견 | | 이 문서에 없는 추가분 |
| STATUS | `🟡 → 🟢` | |

무인 검증: 에디터 Python PIE 드라이버 + `unreal.SystemLibrary.quit_editor()`; `golmok.screenshot`은 HUD를 포함하므로 캡처 전에 `golmok.hud 0`. 백그라운드 에디터 창은 뷰포트를 렌더하지 않는다(V-03).

기록 뒤:
1. 이 표를 채우고 커밋(`WP-09: PC 검증 결과`). 스크린샷은 `docs/runbooks/` 옆에 `pc-verify-wp09-*.jpg`(작게). §6-2에서 바꾼 `bAsyncLoad`는 `True`로 되돌아가 있어야 한다(`git diff unreal/Golmok/Config/DefaultGame.ini` 비어 있음).
2. `docs/plan/STATUS.md`: WP-09 행을 🟡 → 🟢(또는 🔴 + 막힌 항목), V-07 행 갱신, 세션 로그 표에 한 줄(날짜·PC 세션·모델·"V-07 WP-09 검증"·결과). 고친 API·설계 변경은 인계 메모에 번호(§11)와 커밋 해시로.
3. `docs/plan/WP-09-ue-zone-index-async.md` "결과"에 PC 검증 한 줄(통과/수정 건수, 채택한 `GOLMOK_RENDER_TIME_SOURCE`), `docs/ROADMAP.md` 1.3·1.5 진행 표시.
