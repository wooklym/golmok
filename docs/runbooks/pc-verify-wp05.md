# PC 검증 런북 — WP-05 UE C++ 런타임 2: 포털·조명·디버그 (V-03 나머지)

대상: PC Claude 세션(또는 사용자). 전제: `runbooks/pc-verify-wp04.md` §1~§2 통과(빌드 OK, `L_Dev`·`L_ZoneTest` 존재, `z.run()`이 한 번 돌아 `z_synthetic_001` 에셋·액터가 있음).
소요: 빌드 10~20분 + 헤드리스 테스트 10분 + 검증 40분. 결과는 이 문서 하단 "결과 기록"과 `docs/plan/STATUS.md`(V-03 행, WP-05 행)에 적는다.

클라우드 세션은 UE를 컴파일할 수 없었다. **컴파일 에러가 나면 §11의 표를 보고 고친 뒤 커밋**한다(`WP-05: PC fix …`). 설계 의도를 바꾸는 수정이면 `docs/plan/WP-05-ue-portal-lighting-debug.md` "결과"에 한 줄 적는다(DEVELOPMENT-PLAN §4 핸드오프 규칙: 검증 결과는 이 파일 하단, API 수정·설계 변경은 커밋 메시지와 STATUS에).

이 문서의 기대 로그·메시지·파일명은 **설계 문서가 아니라 코드**(`5f0db44` + 리뷰 2차 수정본; 설계 §13 표가 목록)에서 옮겨 적었다. 설계(§3-3, §4-8, §4-9 등)와 다른 곳은 그 자리에 "설계와 다름:" 한 줄로 표시했다.

## 0. 대상 파일
| 파일 | 내용 |
|---|---|
| `Config/Golmok/lighting_presets.json` | 조명 프리셋 단일 소스(cycle 4 + `interior` 부분 프리셋). C++·Python이 같은 파일을 읽음 |
| `Config/DefaultGame.ini` | `[/Script/Golmok.GolmokTimeOfDay]`, `[…GolmokPortal]`, `[…GolmokDebugSubsystem]`, `[…GolmokHUD]`, `[…GolmokPlayerController]`, UFS 스테이징 2줄 + `+DirectoriesToAlwaysCook` |
| `Source/Golmok/Golmok.Build.cs` | `PrivateDependencyModuleNames` += `"RHI"`(`RHIGetGPUFrameCycles`) |
| `Source/Golmok/GolmokGameMode.{h,cpp}` | `PlayerControllerClass = AGolmokPlayerController`, `HUDClass = AGolmokHUD` |
| `Source/Golmok/Lighting/GolmokTimeOfDay.{h,cpp}` | `AGolmokTimeOfDay`(프리셋 JSON 파서, 2 s 보간, 실내 오버레이), 콘솔 `golmok.tod` |
| `Source/Golmok/Portals/GolmokPortal.{h,cpp}` | `AGolmokPortal`(오버랩 트리거, 디바운스·언로드 지연, 문 평면 통과 판정), 콘솔 `golmok.portal` |
| `Source/Golmok/Portals/GolmokLevelStreaming.{h,cpp}` | `namespace GolmokLevelStreaming`: `LevelInstance`(기본)·`NamedStreamingLevel` 두 경로 |
| `Source/Golmok/Zones/GolmokZone.{h,cpp}` | 추가만: `SpawnPortals()` 본문, `SetCollisionDebugVisible`, `GetPortalActors()` |
| `Source/Golmok/Zones/GolmokZoneManifest.{h,cpp}` | 추가만: `GolmokZoneManifest::SublevelPackagePath(ZoneId, Version)` |
| `Source/Golmok/Debug/GolmokStatsMath.h` | 순수 헤더(링버퍼·1% low·경로 JSON; 클라우드 CI가 g++로 검증함) |
| `Source/Golmok/Debug/GolmokDebugSubsystem.{h,cpp}` | `UGolmokDebugSubsystem`: 통계(`OnEndFrame`), 충돌 표시, 경로 녹화/재생(+CSV), 스크린샷; 콘솔 `golmok.hud/collision/path/screenshot/stats` |
| `Source/Golmok/Debug/GolmokHUD.{h,cpp}` | `AGolmokHUD::DrawHUD` |
| `Source/Golmok/Debug/GolmokPathPawn.{h,cpp}` | `AGolmokPathPawn`(재생 카메라 폰, 빙의) |
| `Source/Golmok/Player/GolmokPlayerController.{h,cpp}` | `AGolmokPlayerController`: F1/F2/1~4/F5/F9/F10 (Enhanced Input 런타임 생성) |
| `Source/Golmok/Tests/Golmok{Lighting,Portal,Debug}Test.cpp` | 자동화 테스트 10개(§1) |
| `Content/Python/golmok/lighting_presets.py`, `lighting.py`, `setup_dev_level.py` | 순수 파서 / `apply()`가 JSON을 읽음 / 조명 액터 4개에 태그 `GolmokLighting` |
| `Content/Python/golmok/synthetic_zone.py` | `run(interior=True)`, `register_interior_sublevel()` |
| `Content/Golmok/Zones/z_synthetic_001_interior/v1/manifest.json` | 실내 픽스처(`tools/scripts/make_interior_fixture.py` 출력) |

## 1. 빌드·헤드리스 테스트
```powershell
git pull
.\tools\ue\build.ps1          # Development Editor
```
- [ ] 컴파일 성공(경고는 기록). 실패 시 §11.
- [ ] 에디터 실행 `.\tools\ue\open-editor.ps1` → 아무 에러 없이 열림(Output Log에 `LogGolmok`).

헤드리스 자동화(에디터를 닫고):
```powershell
.\tools\ue\test.ps1 -Filter Golmok. -SetupDevLevel
```
- [ ] 아래 11개가 전부 `Success` (`-nullrhi`이므로 GPU ms는 0이어도 정상):
  ```
  Golmok.Player.Movement          (WP-01, 회귀)
  Golmok.Lighting.PresetsFile
  Golmok.Lighting.PresetApply     (L_Dev PIE)
  Golmok.Debug.StatsMath
  Golmok.Debug.PathFormat
  Golmok.Debug.PathRoundTrip      (L_Dev PIE, Saved/Golmok/Paths/_automation_rec.json 생성 후 삭제 — 실패로 끝나도 삭제)
  Golmok.Debug.HudStats           (L_Dev PIE, Frames>=10 필수; 1% low는 > 0만 단언)
  Golmok.Portal.SpawnFromManifest (L_Dev PIE)
  Golmok.Portal.RoundTrip         (L_ZoneTest PIE — §2 전에는 [Info] "skipped: run synthetic_zone.run(interior=True)"로 Success)
  Golmok.Portal.PawnSwap          (L_ZoneTest PIE — 같은 skip 조건; 빙의 교체 후 실외 판정)
  Golmok.Portal.SharedInterior    (L_ZoneTest PIE — 같은 skip 조건; 두 문·한 실내)
  ```
  `Golmok.Portal.RoundTrip`·`PawnSwap`·`SharedInterior`의 skip 조건은 코드상 `L_ZoneTest` **및** 실내 서브레벨 패키지 `/Game/Golmok/Zones/z_synthetic_001_interior/v1/L_z_synthetic_001_interior` 존재 여부다(L_ZoneTest만 있어도 skip). 설계와 다름: 설계 §8-6은 "L_ZoneTest 있을 때만"이라 적었으나 코드는 서브레벨 패키지까지 요구한다(§13).
- [ ] 실패한 테스트는 `unreal\Golmok\Saved\Logs\Golmok.log`에서 `[Error]` 줄을 §12에 옮겨 적는다.

## 2. 합성 실내 생성 (에디터 Python)
어느 레벨이 열려 있든 상관없다(`L_ZoneTest`를 열거나 만든다). Output Log → Python:
```python
import golmok.synthetic_zone as z; z.run(interior=True)
```
기대 로그(WP-04 런북 §2의 줄들이 먼저 나오고 — `SM_chunk_01`·충돌 메시는 **문 구멍이 뚫린 채 재임포트** — 그 뒤에 아래가 추가된다. 값은 소수 둘째 자리까지):
```
synthetic_zone: /Game/Golmok/Zones/z_synthetic_001/v1/SM_chunk_01.SM_chunk_01 bounds ok (error 0.xx cm)      (chunk_00/02, collision도)
LogGolmok: Zone z_synthetic_001: portal door_1 -> z_synthetic_001_interior rel (500, -950, 0) cm yaw -90.0 radius 150 cm -> level (18170.57, -23148.01, 999.32) [entry]
LogGolmok: Zone z_synthetic_001 v1 loaded in x ms: chunks 3/3 (0 wire boxes), collision 1/1, blockers 1/1, portals 1 (WP-05)
synthetic_zone: zone root at ... yaw -0.0012
synthetic_zone: PlayerStart moved to ...
synthetic_zone: /Game/Golmok/Zones/z_synthetic_001_interior/v1/SM_room.SM_room bounds ok (error 0.xx cm)
synthetic_zone: /Game/Golmok/Zones/z_synthetic_001_interior/v1/SM_z_synthetic_001_interior_collision.SM_z_synthetic_001_interior_collision bounds ok (...)
LogGolmok: Zone z_synthetic_001_interior v1 root: zone-local (0,0,0) -> UE (18170.6x, -23498.0x, 999.3x) cm; ...   (실외 zone-local (5, 13, 0) m 지점)
LogGolmok: Zone z_synthetic_001_interior: chunk room bbox center -> level (18170.6x, -23498.0x, 1159.3x) cm
LogGolmok: Zone z_synthetic_001_interior: portal door_out -> z_synthetic_001 rel (0, 350, 0) cm yaw 90.0 radius 150 cm -> level (18170.57, -23148.01, 999.32) [marker]
LogGolmok: Zone z_synthetic_001_interior v1 loaded in x ms: chunks 1/1 (0 wire boxes), collision 1/1, blockers 0/0, portals 1 (WP-05)
LogGolmok: Zone z_synthetic_001_interior v1 unloaded
synthetic_zone: sublevel actor Interior_Light at ... (level coordinates)
synthetic_zone: sublevel actor Interior_Marker at ... (level coordinates)
synthetic_zone: interior ready — sublevel /Game/Golmok/Zones/z_synthetic_001_interior/v1/L_z_synthetic_001_interior (level coordinates), zone actor Zone_z_synthetic_001_interior (unloaded until door_1)
LogGolmok: Zone z_synthetic_001: portal door_1 -> z_synthetic_001_interior rel (500, -950, 0) cm yaw -90.0 radius 150 cm -> level (18170.57, -23148.01, 999.32) [entry]      (서브레벨 저장 뒤 L_ZoneTest를 디스크에서 다시 열었으므로 실외 zone을 다시 빌드 — 트랜지언트 컴포넌트·door_1 포털 복원)
LogGolmok: Zone z_synthetic_001 v1 loaded in x ms: chunks 3/3 (0 wire boxes), collision 1/1, blockers 1/1, portals 1 (WP-05)
synthetic_zone: done. PIE checklist: docs/runbooks/pc-verify-wp04.md (...) and docs/runbooks/pc-verify-wp05.md (walk north through the door at x=+5 m)
```
- [ ] `door_1`(entry)과 `door_out`(marker)의 `level (…)`이 **같은 점** (18170.57, −23148.01, 999.32)이고 yaw는 −90.0 / 90.0(반대 방향).
- [ ] 콘텐츠 브라우저 `/Game/Golmok/Zones/z_synthetic_001_interior/v1/`에 `SM_room`, `SM_z_synthetic_001_interior_collision`, `L_z_synthetic_001_interior` 3개.
- [ ] 아웃라이너 `Golmok/Zones/Zone_z_synthetic_001_interior`(State = Unloaded), `Portal_z_synthetic_001_door_1`(Transient, 저장 안 됨). 실내 zone은 `unload_in_editor()`로 내려가므로 `Portal_z_synthetic_001_interior_door_out`은 이 시점에 **없다**(PIE에서 문을 지나면 생김).
- [ ] 뷰포트: chunk_01(가운데 조각)에 x = +3.5~6.5 m, z = 0~2.2 m 문 구멍. WP-04의 x = −12 m 유리 구멍은 그대로. 실내 방(8×6×3 m)은 언로드 상태라 안 보인다(`Zone_z_synthetic_001_interior` 디테일 → Rebuild In Editor로 잠깐 확인 가능, 확인 후 Unload In Editor).
- [ ] **Levels 창(Window › Levels)에 서브레벨이 등록되어 있지 않다** — 기본 경로 `LevelInstance`가 실제로 `LoadLevelInstance`를 타야 하기 때문. 등록은 §5 경로 B에서만.
- [ ] 다시 `.\tools\ue\test.ps1 -Filter Golmok.Portal` → `Golmok.Portal.RoundTrip` **Success**(skip 아님; `[Info] cycle 1: interior ready after x.xx s: door_1 (z_synthetic_001 -> z_synthetic_001_interior) active inside; sublevel visible (LevelInstance)`, `cycle 2 …`, `exterior unload released the interior after x.xx s`), `Golmok.Portal.PawnSwap` **Success**(`[Info] interior released after x.xx s: door_1 (…) idle outside; sublevel none (LevelInstance)`), `Golmok.Portal.SharedInterior` **Success**(`[Info] interior released after x.xx s: door_1 (…) idle outside; … | door_2 (…) idle outside; …`; 테스트가 만든 `door_2`는 끝에 파괴됨).

## 3. PIE 조명
`L_ZoneTest`에서 PIE 시작(PlayerStart = 슬래브 위, zone 원점 남쪽 5 m). 시작 로그:
```
LogGolmok: GolmokDebugSubsystem: ready (stats window 2.0 s, 2048 frames; sampler on; record 10 Hz)
LogGolmok: TimeOfDay: spawned a transient AGolmokTimeOfDay in UEDPIE_0_L_ZoneTest (none placed in the level).
LogGolmok: TimeOfDay: presets loaded (5) from <Project>/Config/Golmok/lighting_presets.json      (상대 경로로 찍힐 수 있음)
```
- [ ] 위 3줄이 있고, `TimeOfDay: lighting targets missing …` **경고가 없다**(L_ZoneTest의 태양·하늘·안개·PPV가 잡혔다는 뜻. 경고가 나면 L_ZoneTest가 WP-05 이전에 만들어져 태그가 없는 것 — 클래스별 첫 액터로 폴백하므로 4개 모두 있으면 경고 없이 동작해야 한다).
- [ ] 시작 화면은 **레벨 저작 조명 그대로**(`InitialPreset=` 비움). HUD(F1)의 `tod:` 줄이 `tod: (level)`.
- [ ] 엔진 기본 디버그 키(`BaseInput.ini` `DebugExecBindings`: F1 wireframe, F2 unlit, F5 shader complexity, F9 `shot showui`)는 `Config/DefaultInput.ini`의 `!DebugExecBindings=ClearArray`로 제거했다(F3 lit·F4 detail lighting만 다시 추가). PIE에서 F1/F2/F5/F9를 눌렀을 때 **뷰모드가 바뀌거나 스크린샷이 찍히면** ini가 적용되지 않은 것 — F3으로 lit 복귀 후 §11 #65.
- [ ] 키 **1/2/3/4** = `overcast_morning / clear_noon / golden_evening / night`. 키마다 약 2 s 동안 태양이 회전·밝기가 보간되고 HUD `tod:` 줄이 `tod: (level) -> overcast_morning 45%`처럼 진행률을 보인다(설계와 다름: 설계 §4-8의 `(-> clear_noon 45%)` 괄호 표기가 아니라 `from -> to NN%`). 끝나면 `tod: overcast_morning`.
- [ ] **4(night)**: 전환 끝에 태양 꺼짐(`lux 0` → `SetVisibility(false)`), 볼류메트릭 안개 켜짐, 노출 +1.5 EV로 밝아짐.
- [ ] 전환 중 다른 키 → 현재 보간값에서 다시 출발(튐 없음). HUD가 `night -> clear_noon 30%`로 바뀐다.
- [ ] **F5** 순환: `overcast_morning → clear_noon → golden_evening → night → overcast_morning`.
- [ ] 콘솔(`) `golmok.tod list` →
  ```
  golmok.tod: presets: overcast_morning* clear_noon golden_evening night (overlay: interior) - current overcast_morning, interior off
  ```
  (현재 프리셋에 `*`; 아직 아무 키도 안 눌렀으면 `*` 없이 `current (level)`. 설계와 다름: 구분자는 ` - `(하이픈), 설계의 ` — `가 아님.)
- [ ] `golmok.tod bogus` → `golmok.tod: ERROR unknown preset 'bogus'`. `golmok.tod night` → `golmok.tod: overcast_morning -> night over 2.0 s`. `golmok.tod next`도 동작.
- [ ] **에디터 Python 대조**: PIE를 끝내고 `import golmok.lighting as l; l.apply("golden_evening")`(에디터 뷰포트) vs PIE에서 `golmok.tod golden_evening`(전환 끝) — 태양 방향·색·안개가 같아 보인다(같은 JSON, 같은 속성). `l.list_presets()`가 5개(4 cycle + `interior`)를 나열한다. 되돌리려면 `l.apply("overcast_morning")` 또는 에디터에서 저장하지 않고 닫기.

## 4. PIE HUD·좌표
PIE에서 **F1**(또는 `golmok.hud 1`, 로그 `golmok.hud: on`). 좌상단 반투명 박스에 줄(값은 예):
```
Golmok  fps 158.3  1% low 121.0  (2.0 s, 316 fr)           켠 직후 2 s는 "Golmok  fps warming 0.8/2.0 s"; 1% low < avg/2면 노랑
game 1.75 ms  render 6.98 ms  gpu 5.99 ms                  GPU 샘플이 전부 0이면 "gpu n/a"
tod: overcast_morning                                      전환 중 "(level) -> night 45%", 실내면 " [interior: door_1]" 붙음; TimeOfDay 없으면 "tod: -"
pos ENU E 176.71 N 216.98 U 10.9x  lat 37.5619xx lon 126.9250xx    원점 없으면 "pos UE (x, y, z) cm (no GeoOrigin)"
zones: 2 zones (load < 150 m, unload > 250 m), 2 basemap actors tagged
  z_synthetic_001              v1   prio 10   loaded    dist      0.0 m
  z_synthetic_001_interior     v1   prio 20   unloaded  dist    >=  8.x m
portals: door_1 (z_synthetic_001 -> z_synthetic_001_interior) idle outside; sublevel none (LevelInstance)
path: idle
collision: off   keys: F1 hud  F2 col  1-4 tod  F5 next  F9 rec  F10 play
```
- [ ] fps·1% low가 `stat fps`와 ±5 %, game/render/gpu ms가 `stat unit`과 ±0.5 ms(**gpu가 0/n/a가 아님** — 0이면 §11 #25).
- [ ] `pos` 줄: PlayerStart(zone-local (0, −5, 0) m)에서 **ENU ≈ (176.7, 217.0, 10.9~11.2)**, **lat ≈ 37.56196, lon ≈ 126.92500**(원점 37.5600/126.9230). U는 캡슐 중심 높이라 슬래브 위 ~0.92 m(PlayerStart 자체는 1.2 m).
- [ ] `zones:` 블록 = `golmok.zone.list` 출력과 동일(헤더 + 최대 4행; 설계와 다름: 헤더 끝에 `, N basemap actors tagged`가 붙는다). `portals:` 줄의 `door_out … (marker)`는 실내가 로드된 뒤에만 나타난다.
- [ ] `golmok.stats` → `golmok.stats: fps 158.3  1% low 121.0  game 1.75 ms  render 6.98 ms  gpu 5.99 ms  (2.0 s, 316 fr)` — HUD의 두 줄과 같은 값(HUD를 꺼도 찍힌다: `bSampleWhenHudHidden=True`).
- [ ] `golmok.hud 0` → `golmok.hud: off`, 박스 사라짐. F1로 다시 켬.

## 5. PIE 포털 왕복 (설계 §9-3)
HUD를 켠 채 슬래브 위에서 **문(x = +5 m, 파사드 북쪽 끝; PlayerStart에서 동쪽 5 m·북쪽 14.5 m)**을 향해 걷는다. 트리거는 문 중심 반경 1.5 m·높이 2.5 m 박스, 문 평면의 북쪽(+forward)이 실내.

기대 로그 **순서**(코드 기준 — 설계 §10-5와 다른 두 곳을 표시):
```
① (트리거 진입 0.25 s 뒤)  실내 zone 로드 로그가 먼저:
   LogGolmok: Zone z_synthetic_001_interior v1 root: ...      (이 줄은 PIE 시작 시 첫 Evaluate()의 EnsureManifest()에서 이미 찍혀 있고 트리거 뒤에는 다시 나오지 않을 수 있다)
   LogGolmok: Zone z_synthetic_001_interior: chunk room bbox center -> level (...)
   LogGolmok: Zone z_synthetic_001_interior: portal door_out -> z_synthetic_001 rel (0, 350, 0) cm yaw 90.0 radius 150 cm -> level (18170.57, -23148.01, 999.32) [marker]
   LogGolmok: Zone z_synthetic_001_interior v1 loaded in x ms: chunks 1/1 (0 wire boxes), collision 1/1, blockers 0/0, portals 1 (WP-05)
   LogGolmok: Portal door_1 (z_synthetic_001 -> z_synthetic_001_interior): player within 150 cm -> load [zone z_synthetic_001_interior loaded (pinned)]; sublevel /Game/Golmok/Zones/z_synthetic_001_interior/v1/L_z_synthetic_001_interior (LevelInstance)
   (설계와 다름: 설계는 Portal 줄 → Zone loaded 순서로 적었으나 RequestLoad가 Portal 줄보다 먼저 실행되므로 Zone 로그가 앞선다)
② (문 평면을 북으로 10 cm 넘김)
   LogGolmok: TimeOfDay: interior overlay on (source door_1, base overcast_morning)      (아무 프리셋도 안 눌렀으면 base (level))
   LogGolmok: Portal door_1: crossed inward
   (설계와 다름: overlay on이 crossed inward보다 먼저 찍힌다 — SetInside가 EnterInterior를 부른 뒤 로그)
③ (되돌아 남으로 넘김)
   LogGolmok: TimeOfDay: interior overlay off -> overcast_morning
   LogGolmok: Portal door_1: crossed outward
④ (박스를 남쪽으로 벗어난 뒤 3 s)
   LogGolmok: Zone z_synthetic_001_interior v1 unloaded
   LogGolmok: Portal door_1: player left -> unload z_synthetic_001_interior; sublevel out
```
- [ ] ① 직후 HUD `zones` 줄에 `z_synthetic_001_interior … loaded … pinned`, `portals` 줄이 `door_1 (…) active outside; sublevel visible (LevelInstance) | door_out (z_synthetic_001_interior -> z_synthetic_001) (marker)`(`loading`이 1~2프레임 보일 수 있음). 문 너머로 어두운 방 안에 **마커 큐브(그리드 재질 50 cm)와 따뜻한 PointLight**가 보인다(서브레벨 스트림 인).
- [ ] ② 직후 2 s 동안 안개가 0으로, 노출 +1 EV로 바뀐다. HUD `tod: overcast_morning [interior: door_1]`(전환 중엔 `overcast_morning 45% [interior: door_1]`). 실내에서 키 2 → 문 밖 풍경만 바뀌고 안개 0·노출 +1은 유지(`clear_noon [interior: door_1]`).
- [ ] 방 안 보행: 벽(서·동·북)·천장에 막히고 바닥(방 z 0 = 슬래브 높이)을 걷는다. 남쪽은 파사드(문 구멍만 통과).
- [ ] ③ 직후 안개·노출 복귀, HUD에서 `[interior: …]` 사라짐. ④에서 벽 너머 방·큐브·빛이 사라지고 `portals` 줄이 `idle outside; sublevel none`.
- [ ] **문 앞에서 멈췄다가 물러나기**(평면을 넘지 않음): ① 로드 → 3 s 뒤 ④ 언로드만. `crossed`·`overlay` 로그 없음, 노출 변화 없음.
- [ ] **3 s 안 재진입**: ④가 찍히지 않는다(디테일 `LastEvent = re-entered trigger; unload cancelled`).
- [ ] `golmok.portal list` →
  ```
  golmok.portal list
  door_1 (z_synthetic_001 -> z_synthetic_001_interior) idle outside; sublevel none (LevelInstance)
  ```
  (실내 로드 중이면 `door_out (z_synthetic_001_interior -> z_synthetic_001) (marker)` 줄 추가.)
- [ ] 걷지 않고: `golmok.portal enter door_1` → ①과 같은 Zone·Portal 로그 + `TimeOfDay: interior overlay on …`·`Portal door_1: crossed inward` + `golmok.portal enter: Portal door_1 (…): player within 150 cm -> load […]; sublevel … (LevelInstance)`(이미 active면 `golmok.portal enter: portal door_1 is already active`). `golmok.portal leave door_1` → ③ 로그 + `golmok.portal leave: portal door_1 leaving; z_synthetic_001_interior unloads in 3.0 s` → 3 s 뒤 ④. `golmok.portal enter door_out` → `golmok.portal enter: ERROR portal door_out is a marker (bIsEntry=false); use the entry portal of zone z_synthetic_001`.
- [ ] **트리거 안에 선 채로 `golmok.portal leave door_1`**(문 박스 안, 어느 쪽이든): 메시지 끝에 ` (player still in the trigger: reloads after the debounce)`가 붙고, ④ 뒤에 `Portal door_1: player still in the trigger -> reload in 0.25 s`(디테일 `LastEvent = unloaded; player still in trigger -> debounce re-armed`) → 0.25 s 뒤 ① 로드 로그가 다시 찍힌다(포털은 `Idle`이 아니라 `Pending`을 거쳐 `Active`로 돌아온다). 박스 밖에서 내린 `leave`는 위 줄 그대로.
- [ ] 두 문·한 실내(entry 포털 A로 들어가 B로 나감)는 픽스처에 문이 하나라 PIE로 재현하지 않는다 — `Golmok.Portal.SharedInterior`가 검증한다. 로그 형식만 적어 둔다: B에서 나갈 때 `Portal door_1: released by portal door_2 (player left z_synthetic_001_interior through another door)` → `Portal door_1: crossed outward`; 언로드 지연이 먼저 끝난 쪽은 `Portal door_2: player left -> z_synthetic_001_interior kept (another portal is active); sublevel kept (portal door_1 is leaving)`(`LastEvent = released; interior kept by another portal`), 마지막 쪽이 ④. 지연이 끝나는 순간 다른 문이 `Pending`(플레이어가 그 박스 안, 디바운스 진행 중)이면 언로드하지 않고 `Portal door_2: unload of z_synthetic_001_interior postponed 0.30 s (another portal is pending)`(`LastEvent = unload postponed; another portal is pending`, 상태는 `Leaving` 유지) → 0.30 s(`DebounceSeconds + 0.05`) 뒤 재판정: 그 문이 `Active`가 됐으면 위 kept 줄, `Idle`로 돌아갔으면 ④(리뷰 3차 R3-state-01: 언로드 직후 재로드되는 스래싱 방지).
- 디테일 패널 `LastEvent`로 경로를 읽을 수 있다: `entered trigger`, `re-entered trigger; unload cancelled`, `left trigger before debounce`, `left trigger inward before debounce`, `left trigger inward`, `left trigger outward`, `interior loaded`, `crossed inward`/`crossed outward`, `leave requested`, `unloaded`, `unloaded; player still in trigger -> debounce re-armed`, `unload postponed; another portal is pending`, `released; interior kept by another portal`, `released: player left through another door`, `player pawn outside after possession change`.
- [ ] **부호 확인**(§11 #8): 북으로 넘길 때 `crossed inward`가 찍혀야 한다. 반대로 찍히면 `AGolmokPortal::SignedDistanceAlongForward` 부호 반전 후 커밋.
- [ ] **PIE 도중 실외 zone 언로드**(선택): 방 안에서 `golmok.zone.unload z_synthetic_001` → 포털이 파괴되며 `Portal door_1: end play while active -> sublevel out; zone unload scheduled` → 다음 틱 `Portal door_1: gone -> zone z_synthetic_001_interior unloaded (auto-load resumes after leaving the unload radius)`, 오버레이 off(`TimeOfDay: interior overlay off -> …`). 그 틱에 같은 실내로 가는 다른 entry 포털이 `Pending`이면(예: 실외가 바로 재로드돼 새 `door_1`이 박스 안 플레이어를 보고 디바운스 중) `Portal door_1: gone; unload of z_synthetic_001_interior postponed 0.30 s (another portal is pending)` 뒤 0.30 s마다 재판정(Active면 `gone; … kept (another portal is active)`, Idle이면 `gone -> …`). 설계와 다름: 설계 §3-1 6은 "EndPlay는 RequestUnload를 호출하지 않는다"였으나 핀된 실내는 고아 규칙이 건너뛰므로 코드가 다음 틱에 RequestUnload를 예약한다(리뷰 1차 반영). `golmok.zone.load z_synthetic_001`로 복구.
- [ ] **음성 테스트**: PIE 종료 → 아웃라이너에서 `Zone_z_synthetic_001_interior` 삭제 → PIE → 문 왕복. Warning 1회 `Portal door_1: no AGolmokZone 'z_synthetic_001_interior' in this level; sublevel only`, Portal 줄이 `-> load [no AGolmokZone 'z_synthetic_001_interior' in this level; sublevel only]; sublevel … (LevelInstance)`. 서브레벨(큐브·빛)과 노출 전환은 **계속 동작**, ④는 `player left -> unload z_synthetic_001_interior; sublevel out`(Zone unloaded 줄 없음). 끝나면 Ctrl+Z 또는 `z.run(interior=True, import_assets=False)`로 액터 복구.
- [ ] **경로 B(`NamedStreamingLevel`)**: 에디터 Python `z.register_interior_sublevel()` → 로그 `synthetic_zone: sublevel /Game/Golmok/Zones/z_synthetic_001_interior/v1/L_z_synthetic_001_interior registered in Levels (initially unloaded, hidden)`(실패 시 Warning `could not register the sublevel; add it in Window > Levels, or keep InteriorStreamingMode=LevelInstance (…)` → Levels 창에서 수동 등록, §11 #45). `Config/DefaultGame.ini` `InteriorStreamingMode=NamedStreamingLevel`로 바꾸고 에디터 재시작 → PIE → 같은 왕복. Portal 줄 끝이 `(NamedStreamingLevel)`, `golmok.portal list`에 `sublevel visible (NamedStreamingLevel)`. 등록 없이 이 모드를 켜면 Error `LevelStreaming: sublevel … is not registered in the persistent level (Window > Levels); use InteriorStreamingMode=LevelInstance`. **되돌림**: ini를 `LevelInstance`로, Levels 창에서 서브레벨 항목 제거 후 저장(남겨두면 기본 경로가 `stream in (LevelInstance, reused)`로 등록 항목을 재사용해 `LoadLevelInstance`를 타지 않는다). `test.ps1 -Filter Golmok.Portal`이 두 모드 모두 Success.

## 6. PIE 충돌 표시
- [ ] **F2**(또는 `golmok.collision 1` → `golmok.collision: on (show flag 1, 2 zones, 1 portals)`; 실내 로드 중이면 `2 portals`): 충돌 슬래브·파사드 충돌 메시가 와이어프레임(`GEngine->WireframeMaterial`; 없으면 ini `CollisionDebugMaterialPath`, 그것도 없으면 Warning `GolmokDebugSubsystem: no wire material …` 1회 + 회색 메시), blocker `glass_1` 청록 박스, 포털 `door_1` **초록 박스**(3×3×2.5 m), 베이스맵 큐브·캐릭터 캡슐 충돌(뷰포트 show flag). HUD `collision: on`.
- [ ] 켠 채로 문을 지나 실내 로드 → **1 s 안에** 실내 충돌 메시(방)도 와이어·`door_out` 초록 박스(`CollisionRefreshSeconds=1` 타이머).
- [ ] F2 → 전부 원복(`golmok.collision: off (…)`). PIE 종료 시에도 원복(에디터 뷰포트에 와이어 잔류 없음).

## 7. PIE 경로 녹화·재생·CSV → golmok-perf
```
golmok.path record walk_01      → golmok.path record: recording 'walk_01' at 10 Hz (level L_ZoneTest)
```
- [ ] **녹화 시작 후 3 s는 제자리에 서 있는다**(`golmok-perf`의 기본 워밍업 `--skip-seconds 2`가 정지 프레임에 떨어지도록). 그 뒤 문 왕복(실내 진입·퇴장)을 포함해 **약 60 s** 걷는다. HUD `path: rec walk_01 12.3 s 123 samples`.
- [ ] `golmok.path stop` → `golmok.path stop: path 'walk_01' saved: ~600 samples, 60.x s -> <Project>\Saved\Golmok\Paths\walk_01.json`. 파일 첫 줄 `{"version": 1, "name": "walk_01", "level": "L_ZoneTest", "hz": 10, "created": "…Z", "samples": [`, 한 샘플 한 줄. `golmok.path list` → `golmok.path list: 1 paths in <dir>` + `walk_01  … samples  … s  (L_ZoneTest, 10 Hz)`.
- [ ] 시작 위치로 돌아가 `golmok.path play walk_01 --csv` →
  ```
  golmok.path play: path play 'walk_01' (60.x s, 60x samples) + CsvProfile
  GolmokDebugSubsystem: path play 'walk_01' (60.x s, 60x samples) + CsvProfile
  GolmokDebugSubsystem: CsvProfile Start (path 'walk_01')          (재생 폰 첫 틱)
  ```
  캐릭터가 숨고(충돌은 유지) 카메라가 기록 경로를 따라간다. HUD `path: play walk_01 27.6/60.x s 45% [csv]`(HUD를 꺼도 이 줄만 그려진다).
- [ ] **재생 중에도 포털이 반응**: §5 ①~④ 로그가 그대로 찍히고 노출 전환이 보인다(재생 폰이 Pawn 타입 구체라 트리거가 본다).
- [ ] **재생이 방 안에서 끝나는 경우**(경로를 방 안에서 `golmok.path stop`으로 끝냈거나, 재생 중 `golmok.path stopplay`/F10을 방 안에서): 재생 폰이 방 안에 있고 캐릭터는 밖(숨김 위치)이므로 `PC->Possess(캐릭터)` 직후 `TimeOfDay: interior overlay off -> …` → `Portal door_1: crossed outward`(디테일 `LastEvent = player pawn outside after possession change`), 오버레이 즉시 off, 3 s 뒤 ④ 언로드. `OnPossessedPawnChanged`의 nullptr 브로드캐스트(`Possess` 안의 `UnPossess`)는 포털 로그를 남기지 않는다. 반대로 캐릭터가 문 박스 안에 서 있는 채 재생을 시작하면 새 폰으로 추적만 바뀌고(로그 없음) 상태가 유지된다.
- [ ] 끝나면(또는 `golmok.path stopplay`/F10):
  ```
  GolmokDebugSubsystem: csv: <abs>\Profile(…).csv  ->  golmok-perf "<abs>\Profile(…).csv" --label walk_01 --markdown
  GolmokDebugSubsystem: path play 'walk_01' finished (end of path) after 60.x s
  ```
  캐릭터 복귀·숨김 해제. CSV가 아직 안 써졌으면 `csv: no Profile*.csv yet in <dir> (…)` 또는 `(older than this capture: …)` 뒤 **2 s 뒤 1회 재조회** 로그. PIE(에디터)의 CSV 폴더는 `<Project>\Saved\Profiling\CSV\`; **`-game`으로 실행한 런처 엔진은 `%LOCALAPPDATA%\UnrealEngine\5.8\Saved\Profiling\CSV\`**에 쓴다(V-01 발견) — 로그의 경로가 아니라 그 폴더의 최신 파일을 쓴다.
- [ ] PowerShell에서 로그의 명령을 그대로 실행:
  ```powershell
  cd tools; golmok-perf "<abs>\Profile(...).csv" --label walk_01 --markdown
  ```
  표 1행(`walk_01`, 프레임 수 ≈ (60 − 2) s × fps, avg fps, 1% low, game/render/gpu ms). HUD 1% low(2 s 창)와 절대값은 다를 수 있으나 정의는 같다.
- [ ] **F9/F10**: F9 → `F9: recording 'quick' at 10 Hz (level L_ZoneTest)`, 다시 F9 → `F9: path 'quick' saved: …`; F10 → `F10: path play 'quick' (…)`(csv 없음), 재생 중 F10 → `GolmokDebugSubsystem: path play 'quick' stopped (F10) after x.x s`.
- [ ] 참고: 재생 중 캐릭터 애니메이션이 빠져 Game ms가 실제보다 약간 낮다. 조명 전환 2 s 구간은 VSM/Lumen 캐시 무효화 스파이크가 정상(research/08).

## 8. 스크린샷
```
golmok.screenshot wp05 door     → golmok.screenshot: screenshot requested -> <Project>\Saved\Screenshots\Golmok\wp05\<preset>\door.png (2x, written on the next frame)
```
- [ ] 파일이 **정확히 `door.png`**(뷰포트 2배 해상도, HUD 없음)로 생긴다. `<preset>`은 현재 base 프리셋 이름, 아무 프리셋도 안 눌렀으면 `current`. `viewpoints.py`와 같은 트리. 설계와 다름: 설계 §4-7의 `HighResShot filename=`이 아니라 코드는 `GetHighResScreenshotConfig().SetResolution(w, h, 2.f)` + `SetFilename(<path>.png)` + `UGameViewportClient::Viewport->TakeHighResScreenShot()`를 1순위로 쓴다(`viewpoints.py`가 부르는 `unreal.AutomationLibrary.take_high_res_screenshot`과 같은 시퀀스로 V-01에서 `<name>.png`가 확인됨; HighResShot 콘솔 명령은 `<name>00000.png`으로 접미사를 붙이기 때문).
- [ ] 메시지가 `(1x, written on the next frame) [multiplier reduced: the requested size exceeds the max texture size]`이면 `SetResolution`이 2배를 거부한 것(뷰포트 × 2가 최대 텍스처 크기 초과) — 파일은 1배로 생긴다. 뷰포트를 줄이거나 ini `ScreenshotMultiplier=1`. §12에 기록.
- [ ] `<name>00000.png`이 생겼다면 게임 뷰포트 크기를 못 얻어 HighResShot 폴백을 탄 것(메시지 `screenshot requested via HighResShot -> …00000.png (no viewport size; written on the next frame)`) — `-nullrhi`가 아닌 PIE에서는 나오면 안 된다. §12에 기록.
- [ ] 이름 생략 `golmok.screenshot wp05` → `<YYYYMMDD_HHMMSS>.png`.

## 9. 패키징 (선택, 30분)
- [ ] `.\tools\ue\package.ps1` → 실행 파일에서 콘솔 `open L_ZoneTest` → `golmok.tod list`에 5개(JSON이 `../Config/Golmok` UFS 스테이징으로 pak에 들어감; `golmok.tod: ERROR lighting_presets.json: cannot read …`면 §11 #29 대안) → 문 왕복(서브레벨이 `+DirectoriesToAlwaysCook=(Path="/Game/Golmok/Zones")`로 쿠킹됨; `LevelStreaming: sublevel package missing: …`이면 §11 #30).

## 10. PIE 종료
- [ ] 방 안(오버레이 on)·재생 중·녹화 중 각각의 상태에서 PIE를 끝내도 에러·ensure 없음. 녹화 중 종료는 Warning `GolmokDebugSubsystem: world ending while recording path '…' (… samples) - discarded.`만.
- [ ] 다시 PIE → HUD `tod:`에 `[interior: …]` 잔류 없음(포털 EndPlay + TimeOfDay EndPlay가 소스 집합을 비움), 캐릭터 보임, 충돌 표시 off.
- [ ] 에디터 뷰포트에 Transient 포털·재생 폰·TimeOfDay가 남아 있지 않다(저장 시 dirty 없음).

## 11. 컴파일 에러가 나면 — 불확실한 UE 5.8 API와 대안
클라우드 세션이 엔진 헤더로 직접 확인하지 못한 호출 목록(설계 §11 그대로, 번호 유지). 오류 메시지에 아래 이름이 보이면 대안으로 바꾼다. 50번 이후는 코드를 다시 읽어 표에 없던 호출을 보탠 것.

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
| 50 | GolmokPortal | `APlayerController::OnPossessedPawnChanged.AddDynamic/RemoveDynamic(this, &AGolmokPortal::OnPlayerPawnChanged)`(`FPawnChangedSignature(APawn* Old, APawn* New)`, 5.0+) | 델리게이트 이름·시그니처 | 바인드/해제 두 줄 + `BoundController` 삭제 — `Tick`의 `RefreshOverlap(Player)`가 폰 교체를 다음 틱에 잡는다(재생 시작 직후 1프레임 지연만; 실외 판정 규칙(§7 "재생이 방 안에서 끝나는 경우")도 같은 함수라 유지됨). 단 `Golmok.Portal.PawnSwap`은 `Possess` 직후를 단언하므로 그 단언을 `FWaitLatentCommand(0.1)` 뒤로 옮긴다 |
| 51 | GolmokPortal | `FTimerManager::SetTimerForNextTick(FTimerDelegate::CreateWeakLambda(Subsystem, Lambda))` | 오버로드·`CreateWeakLambda` 존재 | `SetTimer(Handle, FTimerDelegate::CreateWeakLambda(…), 0.001f, false)`; `CreateWeakLambda`가 없으면 `CreateLambda` + 람다 안 `IsValid(Subsystem)` 검사 |
| 52 | GolmokLevelStreaming | `ULevelStreaming::PackageNameToLoad`(public `FName` UPROPERTY), `UWorld::RemovePIEPrefix(const FString&)`(static) | 접근 권한·정적 함수 존재 | `PackageNameToLoad` 비교 삭제(`GetWorldAssetPackageName()`만 비교; `_inst` 인스턴스는 `FPackageName::GetShortName`이 `L_<id>_inst`로 시작하는지로 판별); `RemovePIEPrefix` → `UWorld::StripPIEPrefixFromPackageName(Name, World->StreamingLevelsPrefix)` |
| 53 | GolmokLevelStreaming | `UWorld::IsPartitionedWorld()` | 이름 | `World->GetWorldPartition() != nullptr` 또는 검사 삭제(#48) |
| 54 | GolmokLevelStreaming | `ULevelStreaming::ShouldBeLoaded()` 게터(`Describe`의 `loading` 판정) | 이름(`GetShouldBeLoadedFlag` 등) | `Describe`에서 `loading` 분기 삭제 → `none` |
| 55 | GolmokDebugSubsystem | `APlayerController::ConsoleCommand(const FString&)`, `UGameViewportClient::Exec(UWorld*, const TCHAR*, FOutputDevice&)`(`ExecConsole` 헬퍼: `show collision`·`HighResShot`·`CsvProfile`이 PIE 뷰포트에 닿게) | 시그니처 | `GEngine->Exec(World, *Cmd)`만 남김(그러면 PIE에서 `show collision`이 안 먹을 수 있음 → `bCollisionShowFlag=False`, HighResShot 폴백은 §8 `00000` 접미사) |
| 56 | GolmokDebugSubsystem | `FHighResScreenshotConfig& GetHighResScreenshotConfig()`, `FHighResScreenshotConfig::SetResolution(int32, int32, float)`(bool 반환), `FHighResScreenshotConfig::SetFilename(FString)`(`HighResScreenshot.h`), `FViewport::TakeHighResScreenShot()`, `FViewport::GetSizeXY()`(`UnrealClient.h`), `UGameViewportClient::Viewport`(public `FViewport*`) | 인자·반환형·헤더·멤버 접근 | `SetResolution`이 void면 반환 검사 삭제(항상 2배 시도); `SetFilename`/`TakeHighResScreenShot`가 없으면 `FScreenshotRequest::RequestScreenshot(FullPath + TEXT(".png"), false, false)`(`UnrealClient.h`; 뷰포트 해상도 1배)로 대체; 그것도 안 되면 뷰포트 크기 분기 삭제 → HighResShot 폴백만(파일 `<name>00000.png`; §8·`viewpoints.py` 규약 불일치를 §12에 기록) |
| 57 | GolmokDebugSubsystem | `IFileManager::FindFiles(TArray<FString>&, const TCHAR* Wildcard, bool Files, bool Directories)` 4인자(`Profile*.csv`) | 오버로드 | #35의 3인자 `FindFiles(Out, *Dir, TEXT("csv"))` 후 이름이 `Profile`로 시작하는 것만 |
| 58 | GolmokTimeOfDay | `IConsoleManager::Get().FindConsoleVariable(TEXT("r.DefaultFeature.AutoExposure.Bias"))->GetFloat()`(`DefaultAutoExposureBias`) | cvar 이름·`GetFloat` | 상수 `1.0` 반환 |
| 59 | GolmokTimeOfDay | `CaptureState`의 public 멤버 읽기: `UDirectionalLightComponent::Intensity/bUseTemperature/Temperature`, `UExponentialHeightFogComponent::FogDensity/FogHeightFalloff/bEnableVolumetricFog`, `USkyLightComponent::Intensity` | 접근 권한(UPROPERTY public) | 해당 필드 읽기 삭제(`Initial`은 기본값; base None 복귀가 레벨 저작값 대신 기본값이 됨 — §12에 기록) |
| 60 | GolmokPathPawn | `AutoPossessAI = EAutoPossessAI::Disabled`, `AIControllerClass = nullptr`, `SetActorLocationAndRotation(Loc, Rot, false, nullptr, ETeleportType::TeleportPhysics)` 5인자 | enum·오버로드 | 두 줄 삭제 / 3인자 `SetActorLocationAndRotation(Loc, Rot)` |
| 61 | GolmokPortal/PathPawn | `UPrimitiveComponent::SetCanEverAffectNavigation(false)`, `UBoxComponent::InitBoxExtent`, `UShapeComponent::SetLineThickness` | 안정 | 줄 삭제 |
| 62 | GolmokPortal/DebugSubsystem | `UWorld::bIsTearingDown`(public), `AActor::IsActorBeingDestroyed()` | 접근 권한 | `World->IsPendingKillPending()` / `!IsValid(this)`만 |
| 63 | Tests | `UWorld::SpawnActorDeferred<AGolmokZone>(Class, FTransform)` + `FinishSpawning`, `TWeakObjectPtr::Get(bool bEvenIfPendingKill)`, `AActor::IsPendingKillPending()` | 템플릿 오버로드·인자 | `SpawnActor` + `FActorSpawnParameters::bDeferConstruction`; `Get()` + `IsValid()` 검사 |
| 64 | Tests(PawnSwap·SharedInterior) | `AController::Possess(APawn*)`를 테스트에서 직접 호출, `ADefaultPawn` 스폰(`GameFramework/DefaultPawn.h`), `AActor::SetActorLocation(Loc, false, nullptr, ETeleportType::TeleportPhysics)` 4인자, `SpawnActor<AGolmokPortal>` + `bDeferConstruction` + public 필드 복사 후 `FinishSpawning` | 헤더·오버로드·`Possess`가 `OnPossessedPawnChanged`를 즉시 브로드캐스트하는지 | `SetActorLocation(Loc)` 1인자; `ADefaultPawn` → `APawn` 파생 임의 폰(`ASpectatorPawn`); 브로드캐스트가 지연되면 단언을 `FWaitLatentCommand(0.1)` 뒤로 |
| 65 | Config/DefaultInput.ini | `[/Script/Engine.PlayerInput]` `!DebugExecBindings=ClearArray` + `+DebugExecBindings=(Key=F3,Command="viewmode lit")` | `!`(배열 비움)이 `BaseInput.ini` 항목에 적용되는지, `FKeyBind` 직렬화 형식 | `!` 대신 PC의 `Engine/Config/BaseInput.ini`에서 F1/F2/F5/F9 줄을 **그대로 복사**해 `-DebugExecBindings=(…)`로 제거; 그것도 안 되면 `GolmokPlayerController.cpp`의 `MapKey`를 F6/F7/F8/F11로 옮기고 런북·HUD `keys:` 줄 갱신 |
| 66 | GolmokLevelStreaming | `LoadLevelInstance(…, OptionalLevelNameOverride = "L_<id>_inst")` 고정 인스턴스 이름 재사용 | `Golmok.Portal.RoundTrip` cycle 2에서 `LoadLevelInstance failed`(이전 인스턴스 패키지가 아직 GC되지 않음) | 이름 오버라이드를 빈 문자열로(엔진이 고유 이름 생성; `Find()`는 `PackageNameToLoad`로 대조하므로 그대로 동작) |

## 12. 결과 기록
V-03 PC 세션(Claude Desktop, 사용자 PC, Fable 5.1), 2026-09-25. UE 5.8.3, VS 2026(MSVC 14.51), 브랜치 `pc/v03-verify-wp04-05`.
**검증 방식**: WP-04 런북 §7과 같은 에디터 Python 드라이버(PIE 시작 → 콘솔 명령·텔레포트·`add_movement_input` 보행·상태 프로브·`golmok.screenshot`/`shot showui` 스크린샷). 키 입력(F1/F2/1~4/F5/F9/F10)은 에디터 창을 전면으로 올리고 PIE 뷰포트를 클릭한 뒤 Win32 `SendInput`으로 **실제 키 이벤트**를 보냈다(Enhanced Input 매핑까지 검증). 헤드리스 `z.run(interior=True)`·자동화 테스트는 `UnrealEditor-Cmd -unattended -nullrhi`.

| 항목 | 결과 | 메모 |
|---|---|---|
| 빌드 | ✅ 수정 후 통과 | 컴파일 오류 5건(전부 `GolmokTimeOfDay.cpp`): 5.8의 `FJsonObject::Values`는 `TMap<UE::FSharedString, …>`라 `Values.Find(FString)`·`Pair.Key` 비교/`FString` 변환이 안 됨 → `TryGetField(FStringView)`·`FString(*Pair.Key)`. 링크 오류 2건: `GGameThreadTime`/`GRenderThreadTime`이 5.8에서는 `RENDERCORE_API`(`RenderCore/Public/RenderTimer.h`) → Build.cs `"RenderCore"` + `#include "RenderTimer.h"`(§11 #24의 대안과 다름). 커밋 `e446504`. 그 외 §11 표의 호출은 전부 그대로 컴파일·동작: #1 구 `LoadLevelInstance` 오버로드 존재, #25 `RHIGetGPUFrameCycles`(uint32, `DynamicRHI.h`←`RHI.h`), #50 `FOnPossessedPawnChanged(Old, New)`, #56 `TakeHighResScreenShot`/`SetFilename`, #65 `!DebugExecBindings=ClearArray` 적용됨, #66 고정 인스턴스 이름 재사용 문제 없음(RoundTrip cycle 3회). 프로젝트 경고 0(엔진 헤더 C4996만) |
| §1 테스트 10개 + Movement | ✅ 11/11 Success | 실내 전: `Portal.RoundTrip/PawnSwap/SharedInterior` 3개 `[Info] skipped: run synthetic_zone.run(interior=True)`로 Success. 실내 후: RoundTrip `cycle 1/2: interior ready after 0.03 s … released after 3.00 s`, `cycle 3 … exterior unload released the interior after 0.01 s`; PawnSwap `interior released after 3.00 s`; SharedInterior `door_1 … idle outside … | door_2 … idle outside`. `test.ps1` 요약 줄의 `Succeeded: 10`은 Warning이 있는 `SpawnFromManifest`(L_Dev에 GeoOrigin 없음)를 따로 세는 UE 리포트 방식 — 11개 모두 `Success` 상태 |
| §2 실내 생성 | ✅ | `door_1 … rel (500, -950, 0) cm yaw -90.0 … -> level (18170.57, -23148.01, 999.32) [entry]`와 `door_out … rel (0, 350, 0) cm yaw 90.0 … -> level (18170.57, -23148.01, 999.32) [marker]` **같은 점, 반대 yaw**. 실내 root (18170.57, −23498.01, 999.31), `chunk room bbox center -> (18170.57, -23498.02, 1159.31)`, `loaded … chunks 1/1, collision 1/1, blockers 0/0, portals 1` → `unloaded`, `sublevel actor Interior_Light … z 1249.31`, `Interior_Marker … 1149.31`, `interior ready — sublevel …`, 실외 zone 재빌드(door_1 복원). 에셋 3개(`SM_room`, `SM_z_synthetic_001_interior_collision`, `L_z_synthetic_001_interior`), Levels 등록 없음(`GameplayStatics.get_streaming_level` → None). SM_chunk_01·충돌 메시가 문 구멍 포함으로 재임포트(`bounds ok`). WP-04의 Interchange 경로 수정(`12e6bad`)이 그대로 필요했음 |
| §3 조명(키·F5·`golmok.tod`·에디터 대조) | ✅ (night 화면은 검정 — 아래 메모) | 시작 로그 3줄 ✓, `lighting targets missing` 경고 없음, 시작 HUD `tod: (level)`. 키 1/2/3/4 → `overcast_morning/clear_noon/golden_evening/night`(각 2 s 보간, HUD `tod: overcast_morning 44%` 진행률 — from==to 표기), 전환 중 다른 키 → 현재값에서 재출발(`night -> clear_noon` 30 % 스크린샷 뒤 4로 복귀), F5 순환 night→overcast_morning→clear_noon→golden_evening→night. `golmok.tod list` → `presets: overcast_morning clear_noon golden_evening night (overlay: interior) - current (level), interior off`(뒤에는 `clear_noon*`), `bogus` → `ERROR unknown preset 'bogus'`, `overcast_morning` → `(level) -> overcast_morning over 2.0 s`, `next` → `clear_noon`. 에디터 `l.apply("golden_evening")`(같은 카메라) vs PIE 키 3: 태양 위치·색·안개 동일(`pc-verify-wp05-editor-vs-pie.jpg`), `l.list_presets()` 5개. 4 프리셋 화면 `pc-verify-wp05-presets.jpg`. **메모(night)**: 태양 `lux 0`→`SetVisibility(false)`인데 `L_ZoneTest`의 SkyLight가 real-time capture라 태양 없는 SkyAtmosphere를 캡처 → 하늘·지면 **완전 검정**(노출 +1.5 EV로도 0). 코드 결함이 아니라 프리셋/조명 설계(달빛 DirectionalLight 또는 최소 lux 필요) → D-010 look-dev 항목 |
| 엔진 디버그 키(§11 #65) | ✅ | PIE에서 F1/F2/F5/F9 → 뷰모드 변화 없음(lit 유지), 엔진 `Saved/Screenshots/WindowsEditor/ScreenShot*.png` 생성 없음. Golmok 동작만: F1 HUD 토글, F2 충돌 토글, F5 프리셋, F9 `recording 'quick' at 10 Hz` → `path 'quick' saved: 37 samples, 3.6 s`, F10 `path play 'quick' (3.6 s, 37 samples)` → `stopped (F10) after 2.5 s` |
| §4 HUD·좌표(`stat fps/unit` 대조, ENU/lat/lon) | ✅ | HUD 8줄 형식 그대로(`pc-verify-wp05-hud-stat.jpg`). HUD vs `stat fps/unit`: fps 117.4 vs 118.8(1.2 %), game 7.02 vs 7.00 ms, render 5.25 vs Draw 5.62, **gpu 4.81 vs GPU 4.47**(±0.4 ms, `RHIGetGPUFrameCycles` 정상). `pos ENU E 176.71 N 216.98 U 10.94 lat 37.561955 lon 126.925000`. `zones:` 블록 = `golmok.zone.list`(헤더 끝 `2 basemap actors tagged`), `portals:` 줄, `golmok.stats: fps 114.8  1% low 98.9  game 7.13 ms  render 5.17 ms  gpu 4.98 ms  (2.0 s, 229 fr)`, `golmok.hud 0` → `off` 박스 사라짐. **관찰**: 다른 2 s 창에서는 HUD `render`가 `0.00 ms`로 읽히는 일이 잦다(같은 순간 `stat unit` Draw는 5 ms대) — `GRenderThreadTime`을 `OnEndFrame`에서 읽는 시점 문제로 보임, 표시만 문제 → WP-09 확인 |
| §5 포털 왕복(로그 순서·부호·재진입) | ✅ | 로그 순서 코드 기준 그대로: ① `Zone z_synthetic_001_interior v1 loaded …` → `Portal door_1 (…): player within 150 cm -> load [zone z_synthetic_001_interior loaded (pinned)]; sublevel … (LevelInstance)` ② `TimeOfDay: interior overlay on (source door_1, base overcast_morning)` → `Portal door_1: crossed inward` ③ `interior overlay off -> overcast_morning` → `crossed outward` ④ 3 s 뒤 `Zone … unloaded` → `Portal door_1: player left -> unload z_synthetic_001_interior; sublevel out`. 부호 정상(북으로 넘길 때 inward). 방 안: 마커 큐브·따뜻한 PointLight, HUD `tod: overcast_morning [interior: door_1]`·`z_synthetic_001_interior … loaded … pinned`·`portals: door_1 (…) active inside; sublevel visible (LevelInstance) | door_out (…) (marker)`(`pc-verify-wp05-interior-hud.jpg`); 벽 동 x=837.9 / 서 162.1 / 북 y=−1537.9 cm에서 정지(벽면+캡슐 42); 실내에서 키 2 → `clear_noon [interior: door_1]`, 안개 0·노출 +1 유지. 문 앞 멈춤·후퇴: ① → 3 s 뒤 ④만(crossed·overlay 없음). 3 s 안 재진입: ④ 없음(`LastEvent = re-entered trigger; unload cancelled`). `golmok.portal list/enter/leave` 메시지 전부 런북과 일치, `enter door_1` 두 번째 → `portal door_1 is already active`, `enter door_out` → 실내 로드 중 `ERROR portal door_out is a marker (bIsEntry=false); use the entry portal of zone z_synthetic_001`(언로드 상태면 `ERROR no portal 'door_out' (is its zone loaded? …)`). 트리거 안 `leave` → `… unloads in 3.0 s (player still in the trigger: reloads after the debounce)` → ④ → `player still in the trigger -> reload in 0.25 s` → Active 복귀. 실외 언로드(방 안에서 `golmok.zone.unload z_synthetic_001`) → `end play while active -> sublevel out; zone unload scheduled` → `gone -> zone z_synthetic_001_interior unloaded (auto-load resumes …)`, overlay off, `golmok.zone.load`로 복구 |
| §5 음성 테스트(zone 삭제) | ✅ | 에디터에서 `Zone_z_synthetic_001_interior` 삭제(저장 안 함) → PIE 문 왕복: Warning 1회 `Portal door_1: no AGolmokZone 'z_synthetic_001_interior' in this level; sublevel only`, Portal 줄 `-> load [no AGolmokZone … sublevel only]; sublevel … (LevelInstance)`, 서브레벨(큐브·빛) 스트림 인·노출 전환 동작, ④ `player left -> unload z_synthetic_001_interior; sublevel out`(Zone 줄 없음). 디스크의 umap 무변경 확인 |
| §5 경로 B(NamedStreamingLevel) | ✅ (Python 수정 1건 뒤) | 첫 시도: `z.register_interior_sublevel()`이 `registered in Levels` 로그를 남기고도 **영속 맵을 저장하지 않았다**(`add_level_to_world`가 새 서브레벨을 current level로 만들어 `save_current_level()`이 서브레벨만 저장) → ini를 `NamedStreamingLevel`로 켠 PIE·테스트가 Error `LevelStreaming: sublevel … is not registered in the persistent level (Window > Levels); use InteriorStreamingMode=LevelInstance`(zone 로드·오버레이는 `sublevel none`으로 계속 동작 — 미등록 경로의 기대 동작 확인). `save_map`으로 수정(`84f33c5`) 뒤: `Saving map L_ZoneTest`, 맵에 서브레벨 참조 저장, PIE 왕복 2회 `active inside; sublevel visible (NamedStreamingLevel)`(등록 항목이 loaded/visible True → 퇴장 후 False로 목록 유지, 두 번째 진입도 재사용), `test.ps1 -Filter Golmok.Portal` **4/4 Success**(RoundTrip 3 cycle, `(NamedStreamingLevel)`). 되돌림: ini `LevelInstance` + 신규 `z.unregister_interior_sublevel()`(`remove_level_from_world` + `save_map`, 맵 참조 0) → Portal 테스트 4/4(`LevelInstance`) |
| §6 충돌 표시 | ✅ | `golmok.collision 1` → `on (show flag 1, 2 zones, 1 portals)`, 실내 로드 중 `off (show flag 1, 2 zones, 2 portals)`. 슬래브·파사드 충돌 메시 흰 와이어(`GEngine->WireframeMaterial`, `no wire material` 경고 없음), blocker 박스, door_1 초록 박스, 캡슐(뷰포트 show flag). 실내 진입 1 s 안에 방 충돌 와이어 + door_out 초록 박스(`pc-verify-wp05-collision-interior.jpg`). F2 키 토글 ✓. off → 원복, PIE 종료 후 에디터 뷰포트 잔류 없음 |
| §7 경로·CSV·golmok-perf 표 | ✅ | `golmok.path record walk_01` → `recording 'walk_01' at 10 Hz (level L_ZoneTest)`, 3 s 정지 후 문 왕복 포함 보행 → `stop` → `path 'walk_01' saved: 342 samples, 34.1 s -> …\Saved\Golmok\Paths\walk_01.json`(첫 줄 `{"version": 1, "name": "walk_01", "level": "L_ZoneTest", "hz": 10, "created": "2026-09-25T00:07:56.648Z", "samples": [`, 샘플 1줄씩), `list` → `2 paths in …`. `play walk_01 --csv` → `path play 'walk_01' (34.1 s, 342 samples) + CsvProfile` → `CsvProfile Start (path 'walk_01')`, 캐릭터 숨김·카메라 추종, HUD `path: play walk_01 8.1/34.1 s 24% [csv]`, 화면에 `CsvProfiler 프레임` 카운터. 재생 중 포털 반응: 트리거 진입으로 ①(로드)·Leaving·④는 찍히나 이 녹화의 **카메라 경로가 문 평면 41 cm 남쪽까지만** 가서(캐릭터가 방 안 1.2 m, 카메라는 3.2 m 뒤) crossed는 없음 — 깊은 경로는 아래 행. 끝: `csv: <Saved>/Profiling/CSV/Profile(20260925_090832).csv  ->  golmok-perf "…" --label walk_01 --markdown`, `path play 'walk_01' finished (end of path) after 34.1 s`, 캐릭터 복귀. **golmok-perf**(`--skip-seconds 2`): 프레임 3820 · 평균 119.0 fps · 1% low 103.9 · p50 8.33 ms · p99 9.63 ms · Game 6.27 · Render 5.39 · GPU 5.00 ms(프레임 수 ≈ (34.1−2) s × 119 ✓). F9/F10 ✓(위 행) |
| §7 재생이 방 안에서 끝나는 경우 | ✅ | 경로 `deep2`(x=4.2 m — 실내 마커 큐브(x=5 m, 높이 1.5 m, 50 cm)가 캡슐 가슴 높이를 막아 x=5 m 직진은 y=−12.3 m에서 멈춘다; 첫 시도의 `inroom` 경로가 문 평면 41 cm 남쪽에서 끝난 이유)로 방 안 y=−14.9 m까지 녹화(104 samples, 10.3 s). 재생: 재생 폰이 문 평면을 넘어 ① 로드 → `interior overlay on` → `crossed inward`(`inside=True`), 방 안에서 끝나 캐릭터(밖, 문 남쪽 5 m)로 복귀 → 즉시 `interior overlay off -> (level)` → `Portal door_1: crossed outward`(`LastEvent = player pawn outside after possession change`) → Leaving → 3 s 뒤 ④. 캐릭터가 트리거 안(Active)일 때 밖에서 시작하는 경로를 재생하면 새 폰이 박스 밖이라 `left trigger outward`로 Leaving, `stopplay`로 캐릭터 복귀 → `re-entered trigger; unload cancelled`(런북의 "추적만 바뀜"은 새 폰도 박스 안일 때) |
| §8 스크린샷(`door.png` 이름) | ✅ (HUD 포함 — 메모) | `golmok.screenshot wp05 door` → `screenshot requested -> …/Saved/Screenshots/Golmok/wp05/overcast_morning/door.png (2x, written on the next frame)` → **정확히 `door.png`**(2028×1100, 뷰포트 2배, `00000` 접미 없음, multiplier reduced 없음). 이름 생략 → `20260925_085054.png`. **메모**: HUD가 켜져 있으면 AHUD 오버레이가 스크린샷에 **포함**된다(`TakeHighResScreenShot`이 캔버스 HUD까지 그림; 런북의 "HUD 없음"과 다름) → 깨끗한 캡처는 `golmok.hud 0` 뒤에(WP-06 `spike_runner` 메모) |
| §9 패키징 | ⏭ 미실행 | 선택 항목, V-06에서 |
| §10 PIE 종료 | ✅ | 방 안(오버레이 on) 종료: `Portal door_1: end play while active -> sublevel out`, `interior overlay off -> overcast_morning`, zone 둘 `unloaded`, Error·ensure 없음. 재생 중 종료: `path play 'walk_01' stopped (world ending) after 5.1 s`. 녹화 중 종료: Warning `GolmokDebugSubsystem: world ending while recording path 'tmp' (22 samples) - discarded.`만. 다음 PIE: HUD `tod: (level)`(`[interior]` 잔류 없음), 캐릭터 보임, `collision: off`. 에디터 월드에 Transient 포털·재생 폰·TimeOfDay 없음, dirty 맵 없음 |
| 고친 API(§11 번호) | 2건(`e446504`) | ① `FJsonObject::Values`의 키 형(§11에 없던 항목, WP-04 #0·§11 #14와 같은 뿌리 — 5.8 `UE::FSharedString`) ② #24 `GGameThreadTime`/`GRenderThreadTime` → RenderCore 모듈(표의 대안 대신 정식 헤더). Python: `12e6bad` Interchange 폴더 배치, `dd2c538` 빈 맵 조명 |
| 설계와 다른 동작 발견 | 4건(코드 수정 없음) | (1) `golmok.screenshot`에 HUD 포함(§8) (2) HUD `render` ms `0.00` 빈발(§4) (3) night 프리셋 화면 검정(§3) (4) 포털 언로드 뒤 실내 zone이 HUD/`golmok.zone.list`에 `unloaded … blocked`로 표시 — WP-04 `RequestUnload` 규약(반경 밖으로 나가야 자동 로드 재개)인데 실내는 거리 관리 대상이 아니라 표시만의 문제 |

기록 뒤:
1. 이 표를 채우고 커밋(`WP-05: PC 검증 결과`). 스크린샷은 `docs/runbooks/` 옆에 `pc-verify-wp05-*.jpg`(작게).
2. `docs/plan/STATUS.md`: WP-05 행을 🟡 → 🟢(또는 🔴 + 막힌 항목), V-03 행을 WP-04·WP-05 결과로 갱신, 세션 로그 표에 한 줄(날짜·PC 세션·모델·"V-03 WP-05 검증"·결과). 고친 API·설계 변경은 인계 메모에 번호(§11)와 커밋 해시로.
3. `docs/plan/WP-05-ue-portal-lighting-debug.md` "결과"에 PC 검증 한 줄(통과/수정 건수), `docs/ROADMAP.md` 1.3·1.5 진행 표시.
