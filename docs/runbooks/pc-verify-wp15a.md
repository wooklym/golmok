# PC 검증 런북 — WP-15a Zone 이동·세이브·manifest v2 (V-14)

대상: PC Claude 세션(또는 사용자). 전제: V-07(`runbooks/pc-verify-wp09.md`) 통과 상태 — `L_Dev`·`L_ZoneTest`가 있고, `synthetic_zone.run(interior=True)`이 한 번 돌아 `z_synthetic_001`·`z_synthetic_001_interior` 에셋·서브레벨이 있으며, `Content/Golmok/Zones/index`가 커밋본과 같다. `cd tools && PYTHONUTF8=1 python -m pytest -q` 초록.
소요: 빌드 10~20분 + 헤드리스 10분 + 검증 60분. 결과는 이 문서 §10과 `docs/plan/STATUS.md`(V-14 행, WP-15a 행)에 적는다.

클라우드 세션은 UE를 컴파일할 수 없었다. **컴파일 에러가 나면 §9 표를 보고 고친 뒤 커밋**한다(`WP-15a: PC fix …`). 설계 의도를 바꾸는 수정이면 `docs/plan/WP-15-zone-travel-save.md` "결과"에 한 줄 적는다.

규칙:
- 기대 로그는 코드(`Map/GolmokTravelSubsystem.cpp`, `Save/GolmokSaveSubsystem.cpp`, `Zones/GolmokZone.cpp`)의 `UE_LOG`/`Printf` 형식에 픽스처 값을 넣은 것이다. `x.xx`·`…`는 PC에서만 정해지는 값.
- 세이브 파일: `<Project>\Saved\SaveGames\golmok_auto.sav`(`<Project>` = `unreal\Golmok`). 자동화는 `golmok_test_wp15a` 슬롯만 쓰고 끝에 지운다. **개발자 슬롯은 자동화가 절대 건드리지 않는다**(`GIsAutomationTesting` 동안 자동 저장·복원 꺼짐).
- **PIE에서는 시작 시 자동 복원을 하지 않는다**(`bRestoreInPIE=False` 기본 — 기존 PIE 런북 V-03/V-07/V-09/V-10이 항상 PlayerStart에서 시작하도록). PIE의 복원은 `golmok.load`로, 시작 시 자동 복원은 §6의 standalone `-game` 실행으로 확인한다.
- 시간대 복원 규칙(스펙 §3 "시간대 저장·복원", WP-14a 연결): 세이브의 `{Minutes, Mode}`를 **즉시** 적용 — Fixed는 그 시각에 멈춤, Clock은 그 시각부터 설정 속도로 계속, Realtime은 모드만(PC 현지 시각; 저장한 분은 무시). `Minutes`가 없는(−1) 세이브(WP-14a 이전 세이브, 레벨 조명, `interior` 같은 시각 없는 프리셋 기저)는 종전처럼 `ApplyPreset(프리셋, 즉시)`. 로그 표기 `tod HH:MM <fixed|clock|realtime> (<가장 가까운 키프레임>)`.
- 픽스처 스폰(manifest v2, pytest가 값 고정): `z_synthetic_001` `spawn {position_enu [5, 4, 0], yaw_deg 90}`("합성 골목 1", 문 door_1 남쪽 5.5 m에서 북쪽=문을 봄), `z_synthetic_001_interior` `[0, -1.5, 0]` yaw 90(직접 이동 대상 아님 → 부모 스폰), `z_synthetic_002` `[-8, 3, -0.16]` yaw 90("합성 골목 2", 파사드 B 유리창 남쪽 2 m). 002는 001 동쪽 200 m → 스폰은 001 원점 동쪽 **192 m**로 `L_ZoneTest`의 `Zone_Ground`(001 중심 ±200 m) 안에 떨어진다 — 002는 충돌 에셋이 없으므로 이 평면이 캐릭터를 받친다. 폴백(스폰 없음): zone-local (0,0,0) 위 3 m에서 아래로 라인 트레이스, 맞으면 그 지면, 아니면 원점; 방향 yaw_deg 0(zone +x). 도착 위치 = 발 + 캡슐 반높이 + 2 cm, UE Yaw = 루트 yaw − yaw_deg(루트 yaw는 로그 `Zone z_synthetic_001 v1 root: … yaw x.xxxx deg`에서 읽는다).

## 0. 대상 파일
| 파일 (`unreal/Golmok/` 기준, 그 외 저장소 기준) | 내용 |
|---|---|
| `Source/Golmok/Zones/GolmokZoneManifest.{h,cpp}` | schema_version 1·2, v2 `spawn`/`display_name`(`bHasSpawn`, `SpawnPositionEnu`, `SpawnYawDeg`, `DisplayName`, `GetDisplayName()`); v1에 v2 키는 경고 후 무시 |
| `Source/Golmok/Zones/GolmokZone.{h,cpp}` | `GetSpawnUE(FVector&, float&, bool*)` — 스폰 또는 §1 폴백 |
| `Source/Golmok/Zones/GolmokZoneSubsystem.{h,cpp}` | `EGolmokZoneRequestSource::Travel`(액터가 없으면 인덱스에서 스폰), `ReleasePin`, `IsZonePinned` |
| `Source/Golmok/Map/GolmokTravelSubsystem.{h,cpp}` | 이동(거부 → 선로드 → 페이드 → 폴링 → 텔레포트 → 다음 틱 pin 해제·페이드 인·`OnTraveled`), 콘솔 `golmok.travel` |
| `Source/Golmok/Map/GolmokTravelMath.h`, `GolmokMapMath.h` | 순수 헤더(g++ 교차검증 `tools/tests/test_ue_travel_math.py`) |
| `Source/Golmok/Save/GolmokSaveGame.{h,cpp}`, `GolmokSaveSubsystem.{h,cpp}` | 세이브(SaveSchemaVersion 1)·자동 저장·복원 규칙 ①②③, 콘솔 `golmok.save`·`golmok.load`. 시간대 `TimeOfDay{PresetName, Minutes, Mode}`(WP-14a 연결: `Minutes` −1 = 없음 → 프리셋 이름으로 복원, `Mode` = `EGolmokClockMode` uint8) — Lighting/ 코드는 무수정, 공개 API만 호출. 캐릭터는 명시 선택만 `CharacterId`에 저장하고 `CharacterIdRule`(0 레거시·1 명시만)을 쓴다(R91-1 후속, Astra T20 `IsExplicitSelection()` 필요) |
| `Source/Golmok/Photo/GolmokPhotoModeSubsystem.{h,cpp}` | `[WP-15 hook]` 블록만: `OnPhotoSaved(RelativePath)` |
| `Source/Golmok/Debug/GolmokDebugSubsystem.cpp` | `[WP-15 hook]` 블록만: HUD `travel:` 줄 |
| `Source/Golmok/Tests/GolmokZoneManifestV2Test.cpp`, `GolmokTravelSaveTest.cpp` | 자동화 `Golmok.Zone.ManifestV2`·`Golmok.Travel.Teleport`·`Golmok.Save.RoundTrip` |
| `Content/Golmok/Zones/*/v1/manifest.json` | 픽스처 3개 schema 2 + spawn + display_name(Zone Index 파일은 불변) |

`Build.cs`·`Config/Default*.ini`·GameMode·PlayerController·Character는 **바뀌지 않았다**(새 Config 키는 코드 기본값만; ini 추가 불필요).

## 1. 빌드
```powershell
.\tools\ue\build.ps1
```
- [ ] 컴파일·링크 오류 0, 프로젝트 소스 경고 0. 오류가 나면 §9.

## 2. 헤드리스 자동화
에디터를 닫고:
```powershell
.\tools\ue\test.ps1 -Filter Golmok.Zone.ManifestV2
.\tools\ue\test.ps1 -Filter Golmok.Travel
.\tools\ue\test.ps1 -Filter Golmok.Save
.\tools\ue\test.ps1 -Filter Golmok.
```
- [ ] `Golmok.Zone.ManifestV2` `Success`. 의도된 Warning 1줄: `Zone manifest z_synthetic_001: unknown top-level key 'spawn' (schema error for golmok-zone validate).`(v1 + spawn 케이스). 픽스처가 없으면 `[Info] skipped: fixture manifest … missing`(전제 위반).
- [ ] `Golmok.Travel.Teleport` `Success`. 기대 `[Info]`: `traveling to z_synthetic_001 (zone z_synthetic_001 loaded (pinned)); z_synthetic_001_interior is an interior: going to its parent z_synthetic_001's spawn`, `golmok.travel status: idle; arrivals 1, last z_synthetic_001; …`, `golmok.travel list: 3 index zones` 블록, `traveling to z_synthetic_002 (…)`. 포토 모드 `Enter()`가 거부되면 `[Info] photo refusal not checked: …`(통과는 하지만 §10에 기록). 002는 에셋이 없어 `Zone z_synthetic_002 v1 loaded in x ms: chunks 0/2 (2 wire boxes)…` Warning이 나올 수 있다(V-07과 동일). 타임아웃 케이스의 Warning `GolmokTravel: travel to z_synthetic_001 failed: timeout: z_synthetic_001 not loaded after 0.3 s (state loaded)` 1줄은 의도된 것.
- [ ] `Golmok.Save.RoundTrip` `Success`. 기대 `[Info]`: `golmok.save: slot golmok_test_wp15a (exists), automatic off, …` 블록(`slot:` 줄에 `tod 13:07 clock (<키프레임>)`), `restore saved position from slot golmok_test_wp15a (…): …, tod 13:07 clock; …`, `restore saved zone spawn (version changed) …, tod HH:MM realtime (local time); …`(HH:MM = PC 시각), `restore home zone spawn …, tod <프리셋>; …`(구 세이브 폴백), 그리고 리셋 단계(R49-1) `slot golmok_test_wp15a deleted; visit / photo index cleared; no first visit for z_synthetic_002 until you leave`(이 단계만 자동 저장을 켜고, 리셋 뒤 방문 폴링이 슬롯을 되살리지 않는지·zone을 나갔다 들어오면 다시 첫 방문·저장되는지 단언). `L_ZoneTest`에 GeoOrigin이 없으면 `[Info] skipped: …`(전제 위반). `[Info] reset / visit poll step skipped: …`가 나오면 002 스폰이 로드된 zone 밖이라는 뜻이므로 §10에 기록. 시간대 단계(WP-14a 연결)가 단언하는 것: Clock 13:07 저장 → `TimeOfDay.Minutes` 787(±0.01)·`Mode` Clock·`PresetName` = 가장 가까운 키프레임 → Fixed 05:00으로 바꾼 뒤 복원 → 분 787(±0.01)·모드 Clock·전환 없음(즉시); 세이브를 Realtime·01:40으로 고쳐 복원 → 모드 Realtime·시각은 PC 현지 시각(1분 안, 01:40 아님); Fixed 16:40 → 분 1000(±0.01)·모드 Fixed(위치 복원이 없는 규칙 ③에서도 적용); `TimeOfDay` 기본값(−1·0) + 프리셋 이름(구 세이브) → 그 프리셋이 이름으로 적용·모드 Fixed. `[Info] time-of-day steps skipped: no AGolmokTimeOfDay with keyframes in the PIE world`가 나오면 시간대 단계는 건너뛴 것이므로 §10에 기록(`lighting_presets.json` schema 2 로드 실패 — V-13 전제). 캐릭터 단계(R91-1 후속)의 기대 `[Info]`: `restore none from slot golmok_test_wp15a (…): no usable position / zone (PlayerStart kept), character manny (legacy default, not pinned); …`, `…, character quinn; …`. 단언하는 것: 자동 선택은 빈 id·`CharacterIdRule` 1로 저장, `quinn`을 고르면 `quinn`·규칙 1, 레거시(규칙 0) 기본 id는 `SelectCharacter`를 부르지 않음(자동 선택·자동 플래그 유지), 레거시 비기본 `quinn`은 명시로 복원. 거절된 명시 복원(적대적 검증 V1)의 기대 `[Info]`: `…, character wp15a_unloadable (not applied, kept for the next save); …`, `…, character wp15a_not_in_roster (not applied, not in the roster); …`. 단언하는 것: 테스트 전용 항목 `wp15a_unloadable`(`quinn` 사본, 없는 메시)의 규칙 1 복원은 거절되고 다음 세이브가 `id 'wp15a_unloadable' rule 1`을 남긴다, 로스터에 없는 id는 버린다, 그 뒤 레거시 기본 복원·`golmok.save reset`·`SelectCharacter(quinn)`(뒤이어 자동으로 돌아가도)는 그 id를 남기지 않는다. `[Info] character steps skipped: …`가 나오면 매니킨이 없는 것이므로(`add-mannequin.ps1`) §10에 기록.
- [ ] 네 번째 명령: **36개**(WP-15a 병합 때 32 = 기존 29(WP-14a `Golmok.Lighting.Clock` 포함) + 위 3, 그 뒤 WP-19a `Golmok.Animation.Config`·`Fallback`·`GaspSmoke`·`StateProvider` 4) 전부 `Success`. `test.ps1`의 `Succeeded:`는 Warning 있는 테스트를 따로 세므로 상태 열로 판정(V-03).
- [ ] 끝난 뒤 `<Project>\Saved\SaveGames\`에 `golmok_test_wp15a.sav`가 **없고**, 원래 있던 `golmok_auto.sav`의 수정 시각이 바뀌지 않았다.

## 3. PIE — 목록·이동
에디터에서 `L_ZoneTest`를 열고 PIE. `F1`로 HUD를 켠다.
- [ ] 시작 로그: `GolmokSave: restore skipped (PIE, bRestoreInPIE=False; golmok.load restores)`. 플레이어는 PlayerStart(001 슬래브, 원점 남쪽 5 m)에 있다(**기존 런북 동작 그대로**).
- [ ] HUD에 `travel: idle` 줄.
- [ ] `golmok.travel list`:
  ```
  golmok.travel list: 3 index zones
    z_synthetic_001              v1   exterior new/visited   x m  "합성 골목 1"
    z_synthetic_001_interior     v1   interior new        x m  "합성 골목 1 실내"  [-> parent spawn]
    z_synthetic_002              v1   exterior new        ~x m  "합성 골목 2"
  ```
  (001은 PIE 시작 1초 안에 `visited` — 첫 방문 기록 `GolmokSave: first visit z_synthetic_001 v1 (entered)`. 한글 표시 이름이 깨지면 §10에 기록.)
- [ ] `golmok.travel z_synthetic_002` → 로그
  ```
  GolmokTravel: traveling to z_synthetic_002 (zone z_synthetic_002 loaded (pinned))
  GolmokTravel: arrived at z_synthetic_002 (manifest spawn) UE (x, x, x) yaw x.xx after x.xx s
  GolmokSave: first visit z_synthetic_002 v1 (travel)
  GolmokSave: saving golmok_auto (async, travel): zone z_synthetic_002, visited 2, photos N, position yes, tod HH:MM fixed (<키프레임>)
  ```
  (저장 로그 끝의 `tod …`는 WP-14a 연결 뒤 추가된 부분: 레벨 조명 그대로면 `tod -`, 시각 없는 프리셋 기저면 프리셋 이름만.)
  화면이 약 0.35 s 검게 페이드 아웃 → 파사드 B 유리창을 마주 보고(북쪽) 서 있음 → 페이드 인. 캐릭터가 떨어지지 않는다(`Zone_Ground`). 로딩 중 WASD가 먹지 않는다(이동 입력 차단).
- [ ] **히치 기록**: `golmok.stats` 또는 `stat unit`으로 이동 순간 최대 프레임(ms)을 적고 `pc-verify-wp09.md` §6 표(비동기 로드 히치)와 비교. 001(에셋 있음, 비동기)로 돌아갈 때(`golmok.travel z_synthetic_001`)의 `arrived … after x.xx s`도 적는다.
- [ ] `golmok.zone.list`: 도착한 zone 행에 ` pinned`가 **없다**(다음 틱 해제). 002 행 `loaded … [index]`.
- [ ] `golmok.travel z_synthetic_001_interior` → `traveling to z_synthetic_001 (…); z_synthetic_001_interior is an interior: going to its parent z_synthetic_001's spawn` → 001 스폰(문 남쪽 5.5 m, 문을 봄).
- [ ] 거부: 존재하지 않는 id `golmok.travel z_nope` → `golmok.travel: ERROR travel to z_nope refused: zone is not in the index or the level`. 포토 모드(P) 중 콘솔 → `… refused: photo mode is active`. 문 안(실내 활성, 포털 active) → `… refused: a portal transition / interior is active`. 이동 중 두 번째 명령 → `… refused: already traveling`. HUD `travel:` 줄에 거부 사유가 10초간 보인다.
- [ ] `golmok.travel status`가 상태·마지막 도착·설정값(`timeout 20.0 s, fade 0.35 s, poll 0.05 s, region 30 km`)을 찍는다.

## 4. PIE — 세이브·복원(`golmok.load`)
- [ ] `golmok.save status` → `golmok.save: slot golmok_auto (exists), automatic on, restore on, home '', autosave 60 s, …` + `slot:` 줄(zone·lat/lon·`tod HH:MM <mode> (<키프레임>)`·character·visited·photos).
- [ ] 시간대 `2`(다른 프리셋)로 바꾸고 조금 걸은 뒤 `golmok.save` → 로그 두 줄(서브시스템 로그가 먼저, 콘솔 결과가 뒤):
  ```
  GolmokSave: saved golmok_auto (sync, console): zone …, visited …, photos …, position yes, tod HH:MM fixed (<프리셋>)
  golmok.save: saved golmok_auto (sync, console)
  ```
  위치·방향을 기억(HUD `pos` 줄). `golmok.save`는 복원 보류(hold)를 먼저 푼다 — 보류 중이었으면 그 앞에 `GolmokSave: saved position no longer held (console save)`가 나오고, 보류 위치가 아니라 **지금 선 자리**가 저장된다(R49-3).
- [ ] 50 m쯤 걸어가 방향을 돌리고 시간대 `1`로 바꾼 뒤 `golmok.load` → `golmok.load: restore saved position from slot golmok_auto (…): traveling to … [또는 placed at the saved position (no zone) …], tod HH:MM fixed…` → 저장한 자리·방향(±1 cm·±0.1°)으로 돌아오고 시간대가 저장 때 시각(= 그 프리셋의 키프레임 시각)으로 **전환 없이 즉시** 바뀐다. `golmok.tod status`의 시각·모드가 메시지의 `tod HH:MM fixed`와 같다.
- [ ] **Clock 모드 분 복원(WP-14a 연결)**: `golmok.tod mode fixed` → `golmok.tod time 13:07` → `golmok.tod mode clock`(속도는 기본 0.5 min/s) → 몇 초 뒤 `golmok.save` → 저장 로그 끝 `tod 13:MM clock (clear_noon)`의 HH:MM를 적는다. `golmok.tod mode fixed` → `golmok.tod time 21:00`(밤) → `golmok.load` → 메시지 `…, tod <적은 HH:MM> clock` · 화면이 **전환 없이** 저장 때 낮 조명으로 · `golmok.tod status` 첫머리 `status <적은 HH:MM 또는 1~2분 뒤> clock` · HUD `tod:` 줄 시각이 다시 흐른다(적은 시각부터, 07:30/21:30 키프레임으로 튀지 않음). 이어서 `golmok.tod mode realtime` → `golmok.save` → `golmok.tod mode fixed` → `golmok.tod time 03:00` → `golmok.load` → `tod <PC 시각> realtime (local time)`(저장한 분이 아니라 PC 시계). 틀리면 §9 #12.
- [ ] 캐릭터: `golmok.character <다른 id>` → `golmok.save` → 원래 id로 바꾸고 `golmok.load` → 저장 때 캐릭터로 바뀐다(WP-18 공개 API `SelectCharacter`). `golmok.save` 뒤 `golmok.save status`의 `slot:` 줄은 `character <다른 id>`다(명시 선택만 저장 — R91-1 후속).
- [ ] 주기 저장: 가만히 60 s 이상 → 저장 로그 없음. 1 m 넘게 걷고 60 s가 지나면 `saving golmok_auto (async, periodic)` 1회.
- [ ] PIE 종료 → `GolmokSave: saved golmok_auto (sync, world end): …` 1줄(동기).
- [ ] 종료 순간 위치(R49-2): 다시 PIE, 몇 m 걸은 뒤 **멈추자마자(1초 안에)** PIE 종료 → 다음 PIE에서 `golmok.load` → 멈춘 그 자리(±1 cm)로 돌아온다(1초 폴링 전 위치가 아님). 종료 저장은 게임 뷰포트 close 요청(`UGameViewportClient::OnCloseRequested` — PIE 종료·PIE `exit`·창 닫기, 엔진이 로컬 플레이어를 지우기 전)과 `FWorldDelegates::OnWorldBeginTearDown`(`-game` quit·맵 전환, 액터가 아직 유효)에서 갱신한 스냅샷을 쓴다(V-14 PC fix, §9 #11·#14). 틀리면 §9 #11·#14.

## 5. PIE — 사진 색인
- [ ] P → 촬영(`golmok.photo.shoot`) → 창이 닫히면 `GolmokSave: saving golmok_auto (async, photo): … photos N+1 …`. `golmok.save status`의 `slot:` 줄 photos가 1 늘었다.
- [ ] 탐색기에서 방금 png를 지우고 `golmok.load` → 메시지 끝 `photos N (1 missing dropped)`.

## 6. 재시작 복원(standalone `-game`)
에디터를 닫고:
```powershell
& "<UE>\Engine\Binaries\Win64\UnrealEditor.exe" "<repo>\unreal\Golmok\Golmok.uproject" /Game/Golmok/Maps/L_ZoneTest -game -windowed -ResX=1280 -ResY=720 -log
```
- [ ] (선택) 0회차 — 옛 세이브의 레거시 기본(R91-1 후속): 1회차 **전에**, `golmok_auto.sav`가 이 빌드보다 오래된 빌드가 쓴 것일 때만 한다(이 빌드로 PIE·`-game`을 한 번이라도 돌려 슬롯을 썼다면 이미 규칙 1이다. §3 전에 백업해 둔 옛 `.sav`를 되돌려 놓아도 된다). 같은 명령으로 실행 → 슬롯이 이 레벨에서 만든 것이면 시작 로그 `…, character manny (legacy default, not pinned); …`(gasp 세션의 세이브면 `manny_gasp`), `golmok.character list` 첫 줄 `current=manny`(자동 유지). 옛 세이브의 id가 비기본(`quinn` 등)이면 `…, character quinn; …`로 명시 복원된다. 다른 레벨의 세이브면 `position not restored`로 캐릭터 단계까지 건너뛴다. 옛 세이브가 없으면 건너뛴다 — 자동화 §2 캐릭터 단계가 레거시 규칙을 덮는다.
- [ ] 1회차: 002로 이동(`~` 콘솔 `golmok.travel z_synthetic_002`), 몇 걸음, 시간대를 `golmok.tod time 18:40` → `golmok.tod mode clock`으로(시계 모드), 창 닫기(종료 동기 저장 `(sync, world end)` 또는 `(sync, pre-exit)` — 로그 끝 `tod 18:MM clock (golden_evening)`의 HH:MM를 적는다).
- [ ] 2회차: 같은 명령 → 시작 로그 `GolmokSave: restore on begin play: restore saved position from slot golmok_auto (saved …, zone z_synthetic_002 v1, index v1): traveling to z_synthetic_002 …, tod <적은 HH:MM> clock; …` → 페이드 뒤 저장한 자리·방향, 시간대가 **적은 시각의 시계 모드로 즉시**(복원 순간 저녁 조명으로 바로 — 2 s 전환 없음) 이어서 흐른다(`golmok.tod status` `… clock`), `golmok.travel list`에 001·002 `visited`.
- [ ] 명시 캐릭터만 저장(R91-1 후속): 캐릭터를 고르지 않은 실행을 닫은 뒤 다음 실행의 `golmok.save status` `slot:` 줄은 `character - (automatic)`이고 시작 로그에 `character` 부분이 없다. 단 §4에서 `golmok.character <다른 id>`로 저장한 슬롯이 남아 있거나 0회차에서 비기본 id(`quinn` 등)가 복원되었으면 그 명시 id가 복원·저장되어 `character <다른 id>`로 보인다 — 그 경우 이 줄은 `golmok.save reset` 뒤 실행 두 번(닫고 다시)으로 확인한다. 이어서 `golmok.character quinn` → 창 닫기 → 다시 실행 → 시작 로그 `…, character quinn; …`, `golmok.character list` 첫 줄 `current=quinn`.
- [ ] 3회차: `-GolmokNoRestore`를 붙여 실행 → `GolmokSave: restore skipped (-GolmokNoRestore)`, PlayerStart에서 시작. `golmok.travel list`의 visited는 **유지**(색인은 계속 이어짐).
- [ ] 폴백 ②: `golmok.save status`로 zone을 확인하고, 텍스트 편집 대신 콘솔로 확인하기 어려우면 생략 가능(자동화 `Save.RoundTrip`이 version 99·zone 없음·HomeZoneId를 이미 검증). (선택) `Config/DefaultGame.ini`를 **커밋하지 않는 로컬 수정**으로 `[/Script/Golmok.GolmokSaveSubsystem] HomeZoneId=z_synthetic_001` 넣고, 저장을 `L_Dev`에서 만든 뒤 `L_ZoneTest`로 실행 → `slot golmok_auto was saved in /Game/Golmok/Maps/L_Dev, this level is /Game/Golmok/Maps/L_ZoneTest: position not restored`.

## 7. 리셋
- [ ] `golmok.save reset` → `golmok.save reset: slot golmok_auto deleted; visit / photo index cleared; no first visit for <지금 선 zone> until you leave`. 곧바로 창을 닫아도 `.sav`가 **다시 생기지 않는다**(리셋 뒤 새 방문·사진·이동·`golmok.save` 전까지 자동 쓰기 억제). 다음 실행 → `restore on begin play: no save in slot golmok_auto: nothing restored (PlayerStart kept)`.
- [ ] 리셋 뒤 zone 안에 머무르기(R49-1): 다시 실행해 zone 안에서 `golmok.save reset` → 5 s 이상 그 zone 안에서 걷고(`first visit`·`saving golmok_auto` 로그 **없음**, `golmok.save status`에 `reset: no automatic write until …; no first visit for <zone> until you leave` 줄, 탐색기에 `.sav` 없음) → 그 zone footprint 밖으로 나갔다가 다시 들어오면 `GolmokSave: first visit <zone> v1 (entered)` + `saving golmok_auto (async, first visit)`로 평소대로 돌아온다.

## 8. 기존 런북 불변 확인(샘플)
- [ ] `L_Dev` PIE: 시작 위치 PlayerStart, `Golmok.Player.Movement` 등 기존 자동화 통과(§2). V-07 §4(발견 로그)·V-03 포털 왕복을 한 번 따라 해 로그가 같다(추가 줄은 `GolmokSave: first visit …`·`saving golmok_auto (async, …)`뿐).
- [ ] GeoOrigin 없는 레벨(R49-8): `L_Dev` PIE에서 `golmok.travel list` → index zone 행 끝에 `[no geo origin: not supported]`(실내 행은 `[-> parent spawn]`). `golmok.travel z_synthetic_002` → `golmok.travel: ERROR travel to z_synthetic_002 refused: this level has no geo origin (AGolmokGeoOrigin), so a Zone Index zone cannot be placed; only zones placed in the level` — 레벨 원점에 zone이 생기거나 그리로 이동하지 **않는다**(`golmok.zone.list`에 002 `[index]` 행 없음).

## 9. 컴파일 에러가 나면 — 불확실한 UE 5.8 API와 대안
| # | 파일 | API | 불확실한 점 | 대안 | PC 결과 |
|---|---|---|---|---|---|
| 1 | GolmokTravelSubsystem | `APlayerCameraManager::StartCameraFade(From, To, Duration, Color, bShouldFadeAudio, bHoldWhenFinished)`, `StopCameraFade()` | 인자 순서·`bHoldWhenFinished` 동작(페이드 아웃 뒤 검정 유지) | 페이드 없이 `FadeSeconds=0` 동작(텔레포트만) 또는 `SetManualCameraFade(1.f, FLinearColor::Black, false)` / `(0.f, …)` || ✅ 무수정. 60 fps 녹화(§10 `travel-fade.jpg`): 페이드 아웃 ≈0.37 s → 도착까지 검정 유지(`bHoldWhenFinished`) → 페이드 인 0.35 s. 도착 카메라 랙 스윕은 별개(§10 관찰) |
| 2 | GolmokSaveSubsystem | `UGameplayStatics::AsyncSaveGameToSlot(USaveGame*, const FString&, int32, FAsyncSaveGameToSlotDelegate)` 콜백 스레드 | 콜백이 게임 스레드에서 오는지(엔진은 게임 스레드로 되돌림으로 알려짐). **알려진 한계(R49-9)**: 완료 델리게이트는 `CreateUObject`(약한 바인딩)라 PIE 종료로 GameInstance가 해제된 뒤 끝나는 async 쓰기는 `bSyncAfterAsync` 재기록을 못 해, 종료 동기 저장보다 **약 1 s 이내 오래된** async 데이터가 슬롯에 남을 수 있다(종료 직전 이동·방문·사진 저장이 비행 중일 때만) | 콜백에서 UObject 접근을 `AsyncTask(ENamedThreads::GameThread, …)`로 감싼다. 한계가 문제면 `HandleWorldEnd`에서 `PendingAsync > 0`일 때 짧게 대기하는 후속으로(15a 범위 밖) || ✅ 무수정. async 완료 콜백 정상(`pending async 0`, `saves` 증가), 리셋 중 비행 쓰기 삭제(status `(empty)`) 확인. R49-9 한계 상황은 재현하지 않음 |
| 3 | GolmokSaveSubsystem | `FCoreDelegates::OnPreExit` 시점 | 월드·폰이 이미 없을 수 있음 → 스냅샷 캐시로 저장(월드 없음 가정; 캐시는 월드 teardown 시작 때 갱신된 것, #11) | 로그 `(sync, pre-exit)` 유무만 기록 || ✅ 무수정. `(sync, pre-exit)` 줄은 어떤 종료에서도 나오지 않음 — `-game` 종료는 `UGameEngine::PreExit`가 월드 teardown·게임 인스턴스 종료(서브시스템 Deinitialize로 OnPreExit 핸들러 제거)를 먼저 해 `(sync, world end)`가 종료 저장을 맡는다 |
| 4 | GolmokSaveSubsystem | `GIsAutomationTesting`(`CoreGlobals.h`) | Launcher 빌드에서 에디터 자동화 중 true인지 | 거짓이면 기존 자동화가 개발자 슬롯을 복원·기록 → `test.ps1`에 `-GolmokNoRestore` 추가는 hot-spot 아님(`tools/ue`)이나 PIE 복원은 이미 꺼져 있어 영향은 저장뿐 || ✅ 에디터 자동화 중 true: 센티널 `golmok_auto.sav`(SHA-1·수정 시각) 4회 실행 내내 불변, RoundTrip status `automatic off` |
| 5 | GolmokSaveSubsystem | `UWorld::RemovePIEPrefix(const FString&)`, `UObject::GetPackage()` | 5.x 정적 함수·접근자 | `World->GetOutermost()->GetName()` + `FString::Replace(TEXT("UEDPIE_0_"), TEXT(""))` || ✅ 무수정. PIE 세이브 `LevelName` = `/Game/Golmok/Maps/L_ZoneTest`(UEDPIE 접두사 없음, `-game`이 그대로 복원), 레벨 불일치 문구 정확 |
| 6 | GolmokSaveGame | `UPROPERTY(SaveGame, …)`와 `static constexpr int32 CurrentSchemaVersion` in `UCLASS` | UHT 허용 여부 | `SaveGame` 지정자 삭제(필드는 그대로 직렬화), 상수는 `.cpp`의 `namespace` 상수로 || ✅ 무수정 컴파일 |
| 7 | GolmokZone | `FTransform::ToMatrixNoScale()` + `FMatrix::M[r][c]`(행벡터 규약) | 전치 방향 — `Golmok.Travel.Teleport`의 30° 회전 루트 단언이 검증 | 대안: `GetActorTransform().TransformPosition(GolmokGeo::EnuToUE(p))`, yaw = 루트 yaw − yaw_deg || ✅ 무수정. `Travel.Teleport` 30° 루트 단언 통과, 001·002 스폰 실측이 ENU 픽스처와 일치 |
| 8 | GolmokTravelSubsystem | `APlayerController::SetIgnoreMoveInput(bool)`(카운터) | 짝이 맞지 않으면 이동 불가로 남음 | 로딩 중 입력 차단 줄 2곳 삭제 || ✅ 무수정. 로딩 중 `IsMoveInputIgnored` 참(실제 W 키·`AddMovementInput` 모두 위치 불변), 도착 다음 틱 거짓 — 이동 불가로 남지 않음 |
| 9 | GolmokPhotoModeSubsystem 훅 | `UCLASS` 끝의 `public:` 뒤 `FGolmokOnPhotoSaved OnPhotoSaved;`(비동적 멀티캐스트) | UHT가 UPROPERTY 없는 델리게이트 멤버를 허용(WP-13 훅과 같은 패턴) | 멤버를 `public` 구역 맨 앞으로 옮기는 것은 hot-spot 규칙상 훅 블록 안에서만 || ✅ 무수정. `OnPhotoSaved` 방송 → `saving golmok_auto (async, photo)` |
| 10 | Tests | `FFileHelper::SaveArrayToFile(TArray<uint8>, …)`, `FRotator + FRotator`, `TestNotNull(const T*)` | 오버로드 | `SaveStringToFile(TEXT("png"), …)` || ✅ 무수정 컴파일 |
| 11 | GolmokSaveSubsystem | `FWorldDelegates::OnWorldBeginTearDown`(`FWorldEvent`, 인자 `UWorld*`; `UWorld::BeginTearingDown`이 `bIsTearingDown = true` 직후·EndPlay 전에 방송), `TSet::Intersect`·`TSet::Array` | 시그니처·방송 시점(PIE `TeardownPlaySession`·`LoadMap`·`UGameEngine::PreExit`) | 핸들러를 지우면 종료 저장이 마지막 폴링(≤ 1 s) 스냅샷을 쓴다 — 그 경우 §4의 R49-2 확인을 "≤ 1 s 오차"로 기록 || ⚠ 컴파일·방송은 정상. 그러나 PIE 종료·`-game` 창 닫기에서는 `BeginTearingDown` **전에** 엔진이 로컬 플레이어를 지운다(`UEditorEngine::EndPlayMap`: `GameViewport->CloseRequested` → `CleanupGameViewport` → `UGameInstance::RemoveLocalPlayer`(PlayerController Destroy) → `TeardownPlaySession` → `BeginTearingDown`; `-game`도 창 닫기 → 다음 Tick `CleanupGameViewport`) — 핸들러 안 `GetPlayerPawn`이 null이라 마지막 폴링 위치가 저장됐다(R49-2 실패: 24 cm·105 cm). `-game` quit·맵 전환은 이 시점에 폰이 유효(정확). PC fix → #14 |
| 12 | GolmokSaveGame / GolmokSaveSubsystem | `FGolmokSaveTimeOfDay`의 `UPROPERTY(SaveGame) float Minutes = -1.f`·`uint8 Mode`(태그 직렬화: 필드가 없는 옛 `.sav`는 기본값 −1·0), WP-14a 공개 API `SetClockMode`/`SetTimeOfDay(float, bool)`/`GetTimeOfDayMinutes`/`GetClockMode`/`HasTimeOfDay`/`FindPreset`/`RealtimeTargetMinutes`, `GolmokClockMath::FormatHHMM(double, TCHAR(&)[6])` | 옛 세이브에서 기본값이 들어오는지(UE 태그 직렬화), 복원 순서(`SetClockMode(Fixed)` → `SetTimeOfDay(분, 즉시)` → 모드)에서 추가 전환·`OnPresetChanged`가 없는지 | 이 PR 이전 브랜치로 만든 `golmok_auto.sav`가 있으면 `golmok.save status`의 `slot:` 줄이 `tod <프리셋>`(시각 없음)이어야 한다 — `tod 00:00 fixed`로 읽히면 기본값 폴백이 깨진 것: PC fix로 `SaveSchemaVersion`은 1 그대로 두고 복원을 `Minutes <= 0 && Mode == 0`이면 프리셋 폴백으로 바꾼다. `uint8` UPROPERTY가 거부되면 `int32 Mode`로 || ✅ 무수정. `{Minutes, Mode}` 저장·모드별 즉시 복원 실측(§10). 이 PR 이전 빌드의 세이브가 PC에 없어 옛 파일 폴백은 자동화로만 확인 |
| 13 | GolmokSaveSubsystem / Tests | `UGolmokCharacterSubsystem::IsExplicitSelection() const`(Astra T20), `TMap::FindKey`, `UPROPERTY(SaveGame) int32 CharacterIdRule = CharacterIdRuleLegacy`(옛 `.sav`는 0) | T20이 main에 없으면 `IsExplicitSelection` 미정의(이 후속은 T20 뒤 병합). 옛 세이브에서 기본값 0이 들어오는지 | T20 병합을 기다린다(캐릭터 레인 파일은 고치지 않는다). `FindKey`가 없으면 `DefaultByAnimMode` 값 루프. 테스트의 `TMap::operator[]`가 거부되면 `Add`(같은 키 덮어쓰기), `TGuardValue<TArray<FGolmokCharacterEntry>>`가 안 되면 `TGuardValue<FGolmokCharacterRoster>`(Astra 로스터 테스트와 같은 방식). 옛 세이브가 `character manny`(규칙 1)로 읽히면 기본값 폴백이 깨진 것 — §9 #12처럼 PC fix || ✅ main `f1535ac`(T20 포함) 병합 뒤 무수정 빌드·RoundTrip 캐릭터 단계 통과. 규칙 0 옛 슬롯(#93 이전 빌드가 쓴 것)이 status `character manny (legacy)`로 읽힘 |
| 14 | GolmokSaveSubsystem(V-14 PC fix) | `UWorld::GetGameViewport()`, `UGameViewportClient::OnCloseRequested()`(`FOnCloseRequested(FViewport*)`, `CloseRequested` 첫머리에 방송) — 활성 월드의 뷰포트에 바인딩(`HandleWorldBeginPlay`), 해제는 `HandleWorldEnd`·`Deinitialize`·재바인딩 전 | PIE 종료·창 닫기에서 로컬 플레이어 제거 전에 방송되는지, 뷰포트가 BeginPlay 때 있는지 | 바인딩이 없거나 실패하면 종료 저장이 마지막 폴링(≤ 1 s) 위치를 쓴다 — R49-2를 "≤ 1 s 오차"로 기록 | ✅ PC fix `d2eb06f`: 복원 보류 중·첫 스냅샷 전에는 갱신하지 않음. 헤드리스 PIE 종료(멈춘 뒤 0.0 cm, 걷는 중 다음 프레임 +1.6 cm)·GUI `-game` 창 닫기(닫은 자리 그대로) 확인, 적대 리뷰 4관점 차단 0 |

## 10. 결과 기록

판정 근거는 PC에서 돌린 에디터 Python 드라이버의 로그·프로브(헤드리스 `-nullrhi` PIE, 오프스크린 `-game`, GUI 새 창 PIE, GUI `-game`)와 스크린샷·60 fps 녹화다. 방법은 아래 "V-14 실행 기록". 룩(페이드·도착 연출)은 관찰로만 적는다.

| 항목 | 기대 | 결과/근거 |
|---|---|---|
| 세션/head | 날짜·담당·커밋·장치 | 2026-10-04 18:19~20:10 KST, PC 검증 세션(Claude Opus 5.5), 워크트리 `goofy-maxwell-3aee56`, 브랜치 `pc/v14-verify-wp15a` ← origin/main `8e7cfc5`. 도중에 main `f1535ac`(#93 R91-1 세이브 후속·#94 T20·#95) 병합 → §2 자동화·§3/§4/§7 헤드리스 PIE·§6/§7 `-game`·GUI를 병합 코드(+ PC fix)로 다시 돌렸다. Windows 11, UE 5.8.3 Launcher, GUI PIE 새 창 1920×1080(≈120 fps). 픽스처(L_Dev·L_ZoneTest·합성 zone·매니킨)는 V-10 워크트리에서 복사 |
| §1 빌드 | 오류 0·프로젝트 경고 0 | ✅ 첫 빌드 무수정 성공(엔진 헤더 C4996 54건만, 프로젝트 소스 경고 0). §9 대안은 하나도 쓰지 않았다. PC fix 뒤·main 병합 뒤 재빌드도 성공 |
| §2 자동화 | 3 필터 Success·전체 36 | ✅ ManifestV2 Success(의도된 `unknown top-level key 'spawn'` Warning 1줄). Travel.Teleport Success(기대 Info 전부, `photo refusal not checked` 없음, 의도된 timeout Warning 1줄 + 002 wire box·collision 누락 Warning 4줄). Save.RoundTrip Success(`tod 13:07 clock (clear_noon)`, realtime은 PC 시각 `18:37 realtime (local time)`, 구 세이브 `tod overcast_morning`, 리셋 R49-1 줄, `skipped` 없음). 전체 **36/36 Success**(24 + Warning 12; 32 + WP-19a `Animation.*` 4, `RenderEvidence`는 NOT EXECUTED Warning). 병합 뒤(+ PC fix): RoundTrip에 R91-1 캐릭터 줄(`legacy default, not pinned`·`character quinn`·`wp15a_unloadable (not applied, kept for the next save)`·`not in the roster`)까지 Success, 전체 36/36 Success. 개발자 슬롯: V-08 워크트리의 `golmok_auto.sav`를 센티널로 두고 4회 실행 → SHA-1·수정 시각 불변, `golmok_test_wp15a.sav` 남지 않음 |
| §3 시작·list | restore skipped(PIE), PlayerStart, 첫 방문, 3 zones | ✅ `restore skipped (PIE, bRestoreInPIE=False; golmok.load restores)`, PlayerStart(001 zone-local (0, 500)), 0.6 s 뒤 `first visit z_synthetic_001 v1 (entered)` + `saving … (async, first visit)`. list 3행·한글 이름 정상(`"합성 골목 1"`·`"합성 골목 1 실내"  [-> parent spawn]`·`"합성 골목 2"`), HUD `travel: idle`(`pc-verify-wp15a-hud.jpg`) |
| §3 002 이동 | 로그 4줄·스폰·입력 차단 | ✅ `traveling to z_synthetic_002 (zone z_synthetic_002 loaded (pinned))` → `arrived at z_synthetic_002 (manifest spawn) UE (36870.2, -22498.6, 1076.5) yaw -90.00 after 0.39~0.41 s`(001 원점 동쪽 192.0 m, zone-local (−800, −300) = ENU (−8, 3); 루트 yaw 0이라 UE −90 = 북쪽) → `first visit z_synthetic_002 v1 (travel)` → `saving golmok_auto (async, travel): …, tod -`(레벨 조명 그대로). `Zone_Ground`에 서 있음(2 s 뒤 z 1073.5 그대로). 로딩 중 실제 W 키(SendInput, GUI)·`AddMovementInput`(헤드리스) 모두 위치 불변·`IsMoveInputIgnored` 참. 이동 중 두 번째 명령 → `refused: already traveling`. `golmok.zone.list` 도착 zone에 `pinned` 없음, 002 `[index]` |
| §3 001·실내 id | 부모 스폰 | ✅ 001 `manifest spawn UE (18170.6, -22598.0, 1093.3) yaw -90.00`(zone-local (500, −400) = ENU (5, 4), 문을 봄). `golmok.travel z_synthetic_001_interior` → `…; z_synthetic_001_interior is an interior: going to its parent z_synthetic_001's spawn` → 같은 스폰 |
| §3 거부·status | 4 문구·HUD 10 s·설정값 | ✅ `zone is not in the index or the level`·`photo mode is active`·`a portal transition / interior is active`(문 안, 실내 활성)·`already traveling` 정확. HUD `travel: travel to z_nope refused: zone is not in the index or the level`(`pc-verify-wp15a-hud.jpg`). status `timeout 20.0 s, fade 0.35 s, poll 0.05 s, region 30 km`, `last error` 포함. 20 s 타임아웃은 자동화(시뮬레이션 0.3 s)로만 |
| §3 페이드·도착 연출 | 0.35 s 페이드 → 북쪽을 보고 서 있음 → 페이드 인 | ⚠ **관찰(룩)**. 페이드 아웃 ≈0.37 s·검정 2프레임은 설계대로다. 그러나 페이드 인 0.3 s 동안 캐릭터가 화면에 없고 빈 지면이 옆으로 흐르다가, 검정 뒤 +0.33 s에 오른쪽에서 모션 블러와 함께 들어와 +0.5 s에 멈춘다(60 fps 녹화 `pc-verify-wp15a-travel-fade.jpg`; 001 복귀도 같은 모양). 원인: `GolmokCharacter` 스프링암 `bEnableCameraLag`·`CameraLagSpeed 12`(hot-spot)인데 엔진 `USpringArmComponent`는 텔레포트에 랙을 리셋하지 않아 카메라가 192 m를 날아온다. 카메라 컷이 없어 TSR·모션 블러도 번진다. 후속 제안(15a 범위 밖·설계 판단): 도착 틱에 스프링암 랙을 1틱 끄고 `SetGameCameraCutThisFrame()`(Map/ 레인 안에서 가능) |
| §3 히치 | 이동 순간 최대 프레임 | ✅ `-forcelogflush` 없이 4회(002·001 각 2회): 프레임 중앙값 8.3 ms(120 fps), 이동 구간 최대 11.1~12.9 ms, `golmok.stats` 1% low 97~115 fps — V-07 `pc-verify-wp09.md` §6(비동기 로드에서 11 ms 초과 0개)과 같은 수준. `arrived … after` 001(에셋, 이미 로드·pin) 0.38~0.40 s, 002(에셋 없음) 0.39~0.41 s. 드라이버의 로그 대기용 `-forcelogflush`를 켠 실행에서는 시작·도착 프레임이 32~47 ms였다 — 동기 로그 쓰기 비용(아래 표) |
| §4 status·save | 블록·두 줄 순서 | ✅ status 블록(`automatic on, restore on, home '', autosave 60 s`·`slot:` 줄). `golmok.save` → `GolmokSave: saved golmok_auto (sync, console): … tod 12:30 fixed (clear_noon)` 다음에 `golmok.save: saved golmok_auto (sync, console)` |
| §4 load(프리셋) | ±1 cm·±0.1°·즉시 | ✅ 49 m 달리고 돌아서 `overcast_morning`으로 바꾼 뒤 load → `restore saved position …, tod 12:30 fixed` → UE (18170.6, −21816.0, 1093.5) yaw 30.00(저장과 0.0 cm·0.00°). `golmok.tod status` `12:30 fixed … current clear_noon` |
| §4 Clock·Realtime | 저장 분부터 즉시·계속 | ✅ 13:07 → clock → 5 s 뒤 저장 `tod 13:09 clock (clear_noon)`. fixed 21:00(night) 뒤 load → `tod 13:09 clock`, 0.08 s 뒤 프로브 `current=clear_noon target=clear_noon min=789.6 CLOCK`(전환 없음), status `13:09 clock`, 4 s 뒤 `13:11`(0.5 min/s). realtime 저장 → fixed 03:00 → load → `tod 18:54 realtime (local time)`(PC 시각) |
| §4 캐릭터 | 저장 때 캐릭터·slot 줄 | ✅ quinn 저장 → manny → load → `…, character quinn`. 병합 뒤 slot 줄 `character quinn` |
| §4 주기 | 정지 60 s 없음·걸으면 1회 | ✅ 정지 65 s 동안 없음. 깔끔한 확인: `golmok.save` → 2 m 걷고 정지 → 60.7 s 뒤 `saving golmok_auto (async, periodic)` 1회, 이후 72 s 없음(시나리오 A에서는 저장 66 s 뒤 걷기 시작해 걷는 중 1회 + 남은 걸음 1 m 넘어 60 s 뒤 1회 — 규칙대로) |
| §4 PIE 종료 | sync world end 1줄 | ✅ `saved golmok_auto (sync, world end): …` 1줄 |
| §4 R49-2 | 멈춘 자리 ±1 cm | ❌→✅ **PC fix**(아래). 처음: 멈추고 0.3 s 뒤 종료 → 24 cm 뒤, 걷는 중 종료 → 105 cm 뒤(마지막 1 s 폴링 위치). 수정 뒤(병합 코드): 멈춘 뒤 종료 → 같은 자리(0.0 cm), 걷는 중 종료 → 종료 프레임 위치(마지막 샘플 +1.6 cm = 다음 한 프레임 이동분). GUI `-game` 창 닫기(걷는 중) → 다음 실행이 닫은 자리 그대로 |
| §5 사진 | photos +1·missing dropped | ✅ GUI PIE: `photo: capture window closed (20261004_193842.png present after 1.21 s)` → `saving golmok_auto (async, photo): … photos 1`, status `photos 1`. png 삭제 → `golmok.load` → `photos 0 (1 missing dropped)`. 사진 저장의 위치·yaw는 캐릭터 것(포토 중에도 캐릭터를 possess) |
| §6 0회차(선택) | 레거시 기본 | ➖ 옛 세이브(V-08, 2026-09-30 빌드, `CharacterIdRule` 없음)가 다른 레벨(`/Game/Golmok_AnimEval/Maps/L_Dev_AnimEvalB`)에서 만든 것이라 `position not restored`로 캐릭터 단계까지 건너뜀(런북대로). 규칙 0 읽기는 #93 이전 빌드가 쓴 L_ZoneTest 슬롯이 GUI 실행 첫 status에서 `character manny (legacy)`로 확인, 레거시 복원 규칙은 §2 RoundTrip |
| §6 1·2회차 | 저장·즉시 복원 | ✅ 1회차(오프스크린 `quit`·GUI 창 닫기 각 1회): `saved golmok_auto (sync, world end): zone z_synthetic_002 … tod 18:41 clock (golden_evening)`(GUI 실행은 `18:42`). 2회차: `restore on begin play: restore saved position … (zone z_synthetic_002 v1, index v1): traveling to z_synthetic_002 …, tod 18:41 clock` → 닫은 자리·yaw 120 그대로, 복원 0.1 s 뒤 화면이 이미 저녁 조명(전환 없음, 밝기 변화는 시작 직후 자동 노출), status `18:42 → 18:44 clock`, list 001·002 `visited`(`pc-verify-wp15a-restart.jpg`). `(sync, pre-exit)`는 나오지 않음(§9 #3) |
| §6 명시 캐릭터 | automatic·quinn | ✅ 캐릭터를 고르지 않은 실행 뒤 slot `character - (automatic)`, 시작 로그에 character 없음 → `golmok.character quinn` → 닫기 → 다시 실행 `…, character quinn;`, `current=quinn`, slot `character quinn` |
| §6 3회차·폴백 ② | NoRestore·레벨 불일치 | ✅ `restore skipped (-GolmokNoRestore)`, PlayerStart, visited 2 유지. 폴백 ②는 `DefaultGame.ini` 대신 명령줄 `-ini:Game:[/Script/Golmok.GolmokSaveSubsystem]:HomeZoneId=z_synthetic_001`(파일 무수정): L_Dev 실행이 저장한 뒤 L_ZoneTest → `slot golmok_auto was saved in /Game/Golmok/Maps/L_Dev, this level is /Game/Golmok/Maps/L_ZoneTest: position not restored (visit / photo index kept)` |
| §7 리셋 | 다시 생기지 않음·no save | ✅ 리셋 문구 정확, 곧바로 종료(PIE·`-game`) → `.sav` 없음(0 s·2 s 뒤 확인), 다음 실행 `restore on begin play: no save in slot golmok_auto: nothing restored (PlayerStart kept)` |
| §7 R49-1 | 머무는 동안 쓰기 없음 | ✅ zone 안 리셋 → 6 s 걷기: `first visit`·`saving` 없음, status `reset: no automatic write until …; no first visit for z_synthetic_001 until you leave`, `.sav` 없음 → footprint 밖(25 m 남쪽)으로 나갔다 돌아오면 0.8 s 안에 `first visit z_synthetic_001 v1 (entered)` + `saving … (async, first visit)` |
| §8 불변 | PlayerStart·로그·no geo origin | ✅ L_Dev PIE PlayerStart (−500, 0), 기존 자동화 통과(§2). 포털 왕복 로그(`Portal door_1: … within 150 cm -> load`·`crossed inward/outward`·`player left -> unload`)가 V-10 L_ZoneTest 로그와 같은 형태(추가 줄은 `GolmokSave`·`GolmokTravel`·`golmok.load`뿐). L_Dev: list `[no geo origin: not supported]`(실내 `[-> parent spawn]`), 002 → 런북 문구 그대로 거절, 실내 id → 부모 001도 같은 거절, `golmok.zone.list` `0 zones`(index zone 생성 없음). V-07 §4 발견 로그(`L_ZoneTest09`)는 맵이 없어 미실행(자동화 `Zone.IndexDiscover` 통과) |
| 고친 API·PC fix | 번호·커밋 | §9 #1~#13 대안 적용 없음. **PC fix 1건** `d2eb06f`(`Save/`, Claude 레인): 종료 스냅샷을 `UGameViewportClient::OnCloseRequested`에서도 갱신(§9 #11·#14). 적대 리뷰 4관점(엔진 순서·수명·세이브 의미·테스트/문서) 차단 0, 반영 2(복원 보류 중·첫 스냅샷 전 생략) |
| STATUS 판정 | 통과/부분/차단 | **WP-15a 🟢**, V-14 🟢. 비차단으로 남은 것: ① 도착 카메라 랙 스윕(관찰·후속 제안), ② §6 0회차 같은 레벨 옛 세이브 미확인, ③ 20 s 실제 타임아웃·R49-9 async 한계는 자동화·설계 근거만 |

### V-14 실행 기록 (2026-10-04, PC)

- 드라이버: V-10 `pie_driver.py`를 넓힌 것(세션 scratchpad `v14/`, 미커밋). 더한 것: 엔진 로그 꼬리 대기(`until_log`), 이동 중 틱별 추적(틱·실시간·위치·control yaw·`IsMoveInputIgnored`), `-game` 모드(월드는 PlayerController로 찾고, 종료는 게임 창 `UnrealWindow`에 WM_CLOSE 또는 `quit`). 시나리오: A(L_ZoneTest 헤드리스 PIE 195단계: §3·§4·§7), b(L_Dev §8), p(주기 저장), r(R49-2 진단), g0~g6·gdev·gc1·gc2(오프스크린 `-game -nullrhi -RenderOffScreen`), gui(새 창 PIE: HUD·W 키·히치·사진), gui2(`-forcelogflush` 없이 히치 4회 + ddagrab 60 fps 녹화), gg1·gg2(GUI `-game`: 창 닫기·복원 스크린샷). GUI 단계는 V-11 → V-13 → V-14 잠금 순서로, 헤드리스는 숨긴 창으로 겹쳐 돌렸다(V-13 성능 run 동안 멈춤).
- **PC fix 원인**(R49-2): 임시 진단 로그로 PIE 종료 때 `OnWorldBeginTearDown` 안 `UGameplayStatics::GetPlayerPawn`이 null임을 확인했다. UE 5.8 `UEditorEngine::EndPlayMap`(PlayLevel.cpp)은 `OnPIEEnded` → `GameViewport->CloseRequested` → `CleanupGameViewport`(→ `UGameInstance::RemoveLocalPlayer`, PlayerController `Destroy`, 폰은 unpossess) → `TeardownPlaySession` → `BeginTearingDown` 순서다. `-game` 창 닫기(`UGameEngine::OnGameWindowClosed`)도 다음 Tick의 `CleanupGameViewport`가 먼저다. `-game`의 `quit`(`UGameEngine::HandleExitCommand` → `PreExit`)와 맵 전환은 teardown 때 폰이 유효했다(측정: 정확). 수정: 활성 월드의 `UGameViewportClient::OnCloseRequested`(close 요청 첫머리에 방송, 이때 폰 유효)에 바인딩해 `TakeSnapshot(bForce)`, 복원 보류 중·첫 스냅샷 전에는 하지 않는다. teardown 핸들러는 -game quit·맵 전환용으로 유지한다.
- 히치 표(L_ZoneTest, GUI 새 창 PIE 1920×1080, 드라이버 Slate post-tick 사이 실시간 간격; 이동 명령 전후 ≈1.7 s 구간):

| 이동 | 조건 | 프레임 중앙값 | 구간 최대 | `golmok.stats` 1% low(2 s) |
|---|---|---|---|---|
| 001 → 002 | 로그 플러시 없음 | 8.4 ms | 12.9 ms | 97.1 fps |
| 002 → 001 | 로그 플러시 없음 | 8.3 ms | 11.4 ms | 99.6 fps |
| 001 → 002 | 로그 플러시 없음 | 8.3 ms | 12.9 ms | 106.8 fps |
| 002 → 001 | 로그 플러시 없음 | 8.3 ms | 11.1 ms | 114.5 fps |
| 001 → 002 | `-forcelogflush` | 8.4 ms | 45 ms(시작)·47 ms(도착) | 92.5 fps |
| 002 → 001 | `-forcelogflush`, W 키 누름 | 8.3 ms | 32 ms(시작)·42 ms(도착 0.13 s 뒤) | — |

- 스크린샷: `pc-verify-wp15a-hud.jpg`(HUD `travel:` 줄 idle·거절), `pc-verify-wp15a-travel-fade.jpg`(60 fps 녹화, 33 ms 간격 27프레임: 페이드·카메라 랙 스윕), `pc-verify-wp15a-restart.jpg`(§6 1회차 닫기 직전·2회차 복원 0.1 s·2.5 s).
