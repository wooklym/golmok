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

## 결과
(세션이 작성)
