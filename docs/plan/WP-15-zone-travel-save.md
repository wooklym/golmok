# WP-15 — Zone 지도·이동 + 세이브 (D-014·D-017): 15a 이동·세이브·스키마(클라우드) / 15b 지도 UI·지도 텍스처(PC·자문 뒤)

상태: 🟢 **15a PC V-14 통과**(2026-10-04, [#98](https://github.com/wooklym/golmok/pull/98) 클라우드 병합, PC fix R49-2 `d2eb06f`; 아래 "PC 검증 V-14") · 후속 P14-2 도착 카메라 스냅([#107](https://github.com/wooklym/golmok/pull/107)) PC 확인 대기(V-17 §1) · 15b ⚪ D-009 자문·실제 zone 뒤 — 이전: 🟡 15a 코드 완료·PC V-14 대기(2026-09-28, PR #49; WP-14a 시간대 `{분, 모드}` 연결·자동화 총 32 — 결과 "병합 준비"; 착수 2026-09-28, 세션 https://claude.ai/code/session_018Tn23KryyZ9XmYXMAa91Mb; 브랜치 `claude/wp15a-travel-save`, WP-14a와 병렬) · 담당: 15a **Opus 5.5 ultracode**(설계 Fable 5.1, 검증 Opus), 15b PC 세션 + 소유자 · PC 검증 번호 **V-14**(15a).

## 목표
"가는 곳마다 찍어 올리는" Zone 누적(D-008)이 게임 안에서 보이고(지도), 골라서 갈 수 있고(이동), 다시 켰을 때 이어진다(세이브). D-014·D-017은 "Phase 2 초반, Zone 2곳 이상·V-07 통과 뒤"로 승인됐다. V-07은 통과했고, 개발·테스트에는 합성 zone 2곳(`z_synthetic_001`, `z_synthetic_scan_001`+실내)이 있으므로 **표현 방식·실제 zone 수와 무관한 15a**(스키마 v2, 이동 로직, 세이브)를 지금 클라우드에서 만들고, **15b**(정사영상 지도 텍스처·지도 UI·미니맵)는 실제 zone과 D-009 자문(정사영상 파생물 배포 조건) 뒤 PC에서 한다.

## 분할 근거 (오케스트레이터 결정, D-019, 2026-09-28)
- 15a는 코드·스키마·테스트만이고 되돌릴 수 있다(브랜치). 15b는 NGII 정사영상 파생물의 **공개 배포 조건**(D-009, [확인 필요])과 실제 zone이 있어야 가치가 있다.
- WP-14a와 파일 겹침이 없다(Lighting/ ↔ Zones/·Map/·Save/·tools). 세이브가 시간대를 저장하려면 WP-14a의 `GetTimeOfDayMinutes/GetClockMode`가 필요하므로 15a는 **WP-14a 병합 뒤 그 API를 쓰고**, 그 전에는 프리셋 이름만 저장한다(스펙 §4).

## 배경(코드에서 확인할 것)
- Zone: `Zones/GolmokZoneSubsystem`(`RequestLoad(ZoneId, bPin, OutMessage, Source)`·`RequestUnload`·`ResolveZoneVersion`·`IsZoneInIndex`·`GetIndex`·`NotifyZoneLoaded`·겹침 해소·베이스맵 숨김), `AGolmokZone`(`Load/IsLoaded/IsLoading`, `EnsureManifest`, `GetFootprintUE/Bounds`, `FootprintContains`, `GetPriority`), `GolmokZoneManifest`(파서, schema_version 1), `GolmokZoneIndex`(`zones.json`·셀). 포털 선로드 패턴은 `Portals/GolmokPortal`(RequestLoad → 폴링 → 활성화).
- Geo: `Geo/GolmokGeoSubsystem`(`LonLatToLevelUE`, `LevelUEToLonLat`, `ZoneToAreaMatrix`), 순수 `GolmokGeoMath.h`.
- 플레이어: `Player/GolmokCharacter`·`GolmokPlayerController`(hot-spot — 훅만). 포토 모드(`Photo/GolmokPhotoModeSubsystem`, 사진 `Saved/Screenshots/Golmok/photo/<stamp>.png+.json`), 시간대(`Lighting/GolmokTimeOfDay`), 캐릭터 로스터(WP-18, Astra 레인 — 읽기만).
- 스펙: `docs/spec/zone-manifest.md`(schema_version 1, 알 수 없는 최상위 키는 오류), `zone-manifest.schema.json`, `tools/golmok_tools`의 `golmok-zone` CLI·validator·`init/bump`, Zone Index schema 1. `Golmok.Build.cs`(hot-spot)에 UMG/Slate 없음.

## 설계 (확정, 2026-09-28, Fable)

### 1. manifest schema_version 2 (15a)
- 추가 필드(둘 다 **선택**): `spawn: {position_enu:[x,y,z], yaw_deg}`(zone-local m, Z-up; 플레이어가 서는 곳과 바라보는 방향, 포털 `pose_enu`와 같은 규약) · `display_name: string`(지도·HUD 표시 이름, 없으면 `zone_id`). 그 밖의 알 수 없는 키는 여전히 오류.
- 파서(UE·Python)는 **v1과 v2를 모두** 읽는다. v1 또는 `spawn` 없음 → 스폰 폴백 = zone-local `(0,0,0)`을 UE로 옮긴 뒤 위 3 m에서 아래로 라인 트레이스한 지면 + 캡슐 반높이, yaw 0. `golmok-zone init`은 v2로 쓰고, `bump`는 기존 버전을 유지한다(전 zone 일괄 bump 금지). 합성 zone 생성기(`make_synthetic_zone.py`)와 `synthetic_zone.py` 픽스처는 v2 + `spawn`을 쓴다(픽스처 재생성, `CONVENTION_FOLDERS`류 등록부는 훅 줄).
- Zone Index(schema 1)는 바꾸지 않는다. 지도·이동은 index의 `id/bbox_wgs84/version`으로 목록을 만들고, `display_name`·`spawn`은 그 zone의 manifest를 읽어 얻는다(작은 JSON, `AGolmokZone::EnsureManifest` 재사용).
- WP-17 `sounds[]` 제안은 이 v2에 **넣지 않는다**(V-10·첫 현장 녹음 뒤 채택 결정; 채택되면 v3). 스펙 문서에 "v2 예약 없음"을 명시.

### 2. 이동 (15a) — `Map/GolmokTravelSubsystem`(World 서브시스템)
- `TravelToZone(ZoneId, OutMessage)`: ① 포토 모드 중·포털 전환 중·이미 이동 중이면 거부 ② `ResolveZoneVersion`으로 index에서 찾고(없으면 오류) `RequestLoad(ZoneId, bPin=true, Source=Travel)` — `EGolmokZoneRequestSource`에 `Travel` 추가(열거형은 Zones/ 안, Claude 레인) ③ 카메라 페이드 아웃(`APlayerCameraManager::StartCameraFade`, 에셋 없음) ④ `IsLoaded()`까지 폴링(`TravelTimeoutSeconds` 기본 20 s, 실패면 페이드 인·오류) ⑤ 스폰 UE 좌표 = manifest `spawn`(zone-local → ECEF → area ENU → UE, 기존 Zone 변환 재사용; `AGolmokZone::GetSpawnUE(FVector&, float& YawUE)` 추가) 또는 §1 폴백 ⑥ 캐릭터 `SetActorLocation`(sweep 없음) + 컨트롤러 yaw(UE yaw = −yaw_deg 규약) ⑦ 한 틱 뒤 pin 해제(`RequestUnload`가 아니라 pin만 풀어 거리 규칙에 맡김) ⑧ 페이드 인, 델리게이트 `OnTraveled(FString ZoneId)` 발화, 방문 기록(§4).
- 콘솔 `golmok.travel <zone_id>`·`golmok.travel list`(index의 zone id·표시 이름·방문 여부·거리 m)·`golmok.travel status`. HUD `travel:` 줄(이동 중/실패 사유). 등록부 `CONSOLE_COMMANDS`는 `# [WP-15 hook]` 줄.
- 실내 zone(`kind: interior`)으로는 직접 이동하지 않는다(부모 exterior의 스폰으로 보냄, 메시지). 베이스맵 범위 밖 zone("다른 지역")은 15a 범위 밖: index에 있으면 목록에 표시하되 이동은 "지원 안 함" 메시지.

### 3. 세이브 (15a) — `Save/GolmokSaveGame` + `Save/GolmokSaveSubsystem`(GameInstance 서브시스템)
- `UGolmokSaveGame : USaveGame` 필드: `SaveSchemaVersion`(1), `Lat/Lon/HeightEllipsoidal`(double), `YawDeg`(ENU 기준, UE yaw 아님), `ZoneId`·`ZoneVersion`(현재 안에 있는 권위 zone, 없으면 빈 문자열), `TimeOfDay`(§4: `{PresetName, Minutes, Mode}` — WP-14a 연결 2026-09-28, 아래 "시간대 저장·복원"), `Visited[]`(`{ZoneId, Version, FirstVisitUtc}`), `Photos[]`(`Saved/` 기준 상대 경로 문자열만), `CharacterId`(WP-18 로스터 현재 id, 문자열; 없으면 빈 값 — R91-1 후속(2026-10-04)부터 명시 선택 id만 + `CharacterIdRule`, 아래 "R91-1 후속"), `SavedAtUtc`. UE 좌표는 저장하지 않는다.
- 자동 저장 슬롯 1개 `golmok_auto`(사용자 인덱스 0), `AsyncSaveGameToSlot`만 사용. 트리거: 이동 완료, 첫 방문(zone 진입 = `NotifyZoneLoaded` 뒤 `FootprintContains(플레이어)`가 처음 참일 때), 포토 촬영 완료(WP-12에 델리게이트가 없으면 `// [WP-15 hook]` 블록으로 `OnPhotoSaved(FString RelativePath)` 추가), 주기 `AutosaveIntervalSeconds`(기본 60, 변경이 있을 때만), 월드 종료(`EndPlay`·`FCoreDelegates::OnPreExit`)는 **동기** `SaveGameToSlot`(종료 중 비동기는 유실).
- **시간대 저장·복원**(WP-14a 연결, 2026-09-28, R49-7/R51-2 오케스트레이터 결정): `FGolmokSaveTimeOfDay{PresetName(FString), Minutes(float, 기본 −1 = 없음), Mode(uint8 = EGolmokClockMode를 static_cast, 0 Fixed·1 Clock·2 Realtime, 기본 0)}`. 필드 추가만이라 `SaveSchemaVersion` 1 유지(태그 직렬화 — 옛 세이브는 −1·0으로 읽힌다; 버전 검사가 1만 받으므로 올리면 옛 세이브가 거절된다). 저장: `GetTimeOfDayMinutes()`·`GetClockMode()`·`CurrentPreset`(시계 위에서는 가장 가까운 키프레임). 단 시각이 없는 상태는 `Minutes −1`: 레벨 조명(`HasTimeOfDay()` false), Fixed에서 키프레임 시각이 없는 프리셋을 기저로 건 경우(예: `interior`) — 이름으로 복원. 복원(모드별, 모두 즉시): 먼저 `SetClockMode(Fixed)`로 시계를 세운 뒤 **Fixed** → `SetTimeOfDay(Minutes, true)`; **Clock** → `SetTimeOfDay(Minutes, true)` 후 `SetClockMode(Clock)`(저장한 분부터 설정 속도로 계속; 이미 시계 기저라 두 번째 점프 없음); **Realtime** → `SetTimeOfDay(RealtimeTargetMinutes(), true)` 후 `SetClockMode(Realtime)`(PC 현지 시각이 정본 — 저장한 분은 무시). `SetClockMode(Clock)`을 먼저 부르면 프리셋 기저에서 전환(2 s) 점프와 `OnPresetChanged(…, false)`가 한 번 더 나가고, Realtime에서 `SetTimeOfDay`는 Fixed로 떨어지므로 이 순서로 한다. **`Minutes < 0`(WP-14a 이전 세이브 등)** 또는 키프레임 없음 → 종전 `ApplyPreset(PresetName, true)`(현재 모드 규칙 그대로: Realtime이면 Fixed로). 알 수 없는 `Mode` 값은 Fixed. 로그·`golmok.save status`·`golmok.load` 메시지에 `tod HH:MM <mode>`(`GolmokClockMath::FormatHHMM`).
- 복원(`RestoreOnBeginPlay`, 기본 true; `-GolmokNoRestore` 명령줄로 끔 — 런북·자동화용): 월드 BeginPlay 뒤 GeoOrigin이 준비되면 ① 세이브의 `ZoneId`가 index에 있고 version 같음 → 저장 위치로 ② version 다름·zone 없음 → 그 zone(있으면) 또는 `HomeZoneId`(Config, 기본 빈 값 = 현재 PlayerStart 유지)의 스폰으로 `TravelToZone` ③ 어느 것도 없으면 복원 안 함(로그). 복원 뒤 시간대(§4)·캐릭터(§4) 적용. 위치 복원은 캐릭터가 이미 스폰된 뒤 `SetActorLocation`(GameMode·PlayerController는 hot-spot: 손대지 않고 서브시스템 `OnWorldBeginPlay`에서 한 틱 뒤 처리).
- 콘솔 `golmok.save`(즉시 동기 저장)·`golmok.save status`·`golmok.save reset`(슬롯 삭제)·`golmok.load`(즉시 복원). HUD `save:` 줄은 두지 않는다(로그만).

### 4. 다른 WP와의 계약
- **시간대**: WP-14a 병합 전에는 `TimeOfDay = {PresetName}`만 저장·복원(`ApplyPreset(Name, true)`); 병합 뒤 `{Minutes, Mode}`를 추가하고 우선 적용(WP-14a API `GetTimeOfDayMinutes/GetClockMode/SetTimeOfDay/SetClockMode`). 세이브 스키마는 1 그대로(필드 추가는 기본값으로 호환). **반영 완료(2026-09-28, WP-14a PR #51 병합 뒤)**: §3 "시간대 저장·복원" — Lighting/ 코드는 수정하지 않고 공개 API(`GetTimeOfDayMinutes`·`GetClockMode`·`SetTimeOfDay`·`SetClockMode`·`HasTimeOfDay`·`FindPreset`·`RealtimeTargetMinutes`·`ApplyPreset`)만 쓴다.
- **캐릭터(WP-18, Astra 레인)**: 로스터 현재 id를 읽는 공개 API가 있으면 저장·복원에 쓰고, 없으면 `CharacterId`를 비워 두고 WP 문서에 "Astra 후속: `UGolmokCharacterRoster::GetCurrentId/Select` 노출"을 적는다. Astra 파일은 고치지 않는다.
- **포토(WP-12)**: 사진 목록은 파일 시스템이 정본이고 세이브는 색인일 뿐 — 복원 시 없는 파일은 목록에서 제거.
- **Zone 겹침·pin**: 이동의 pin은 도착 뒤 해제, `bAutoManageInterior`·거리 규칙은 그대로. 이동 중 포털 오버랩은 무시(포털 상태 Idle 확인).

### 5. 15b (PC·자문 뒤) — 지도 UI
- 지도 텍스처: `golmok-basemap map-texture`(정사영상 축소 PNG + 도로 레이어 옵션) → `Content/Golmok/Map/<area>.png`(UFS 스테이징, 런타임 `IImageWrapper` 로드, `.uasset` 없음). 공개 배포 조건은 D-009 자문 결과에 따른다(게임 내부 사용은 D-012로 허용).
- UI: Slate `SGolmokMapWidget`(C++만, 위젯 BP 없음): 정사영상 위 Zone footprint/점·표시 이름·촬영일·방문 여부·현재 위치, 클릭/확인 → `TravelToZone`. 입력 액션 `IA_Map`(M)은 C++로 생성(규약). 미니맵은 기본 끔(옵션만). `Golmok.Build.cs`에 `Slate`·`SlateCore` 추가는 hot-spot 훅 블록(15b에서).
- 순수 수학(`GolmokMapMath.h`: WGS84 bbox ↔ 텍스처 픽셀, 웹 메르카토르 z16 셀 ↔ 픽셀)은 15a에서 미리 만들고 g++ 교차검증한다(15b가 그대로 쓴다).

### 6. 테스트·문서 (15a)
- pytest: 스키마 v2(`spawn`·`display_name` 형식·범위·v1 호환·알 수 없는 키 오류), `golmok-zone validate/init/bump` v2, 합성 zone 생성기 v2, Zone Index 불변 확인, `GolmokMapMath.h`·`GolmokTravelMath.h`(스폰 변환·폴백·yaw 부호) g++ 교차검증 표.
- UE 자동화(`-nullrhi`): `Golmok.Zone.ManifestV2`(v1/v2 파싱·폴백), `Golmok.Travel.Teleport`(합성 zone 2곳 사이 이동: 선로드→스폰 좌표·yaw→pin 해제→`OnTraveled`, 실내 거부, 포토 모드 중 거부, 타임아웃), `Golmok.Save.RoundTrip`(저장→로드 경위도 1 mm·yaw·방문·사진 색인, version 불일치 폴백, 슬롯 없음; WP-14a 연결 뒤 시간대 {분, 모드} 왕복·Realtime 모드만·구 세이브 프리셋 폴백). 등록 +3.
- 런북 `docs/runbooks/pc-verify-wp15a.md`(**V-14**): 빌드·자동화 → PIE `golmok.travel list`·이동(페이드·히치 시간 기록, WP-09 §6 표와 비교) → 종료·재시작 복원(위치·시간대·방문) → `golmok.save reset` → 사진 촬영 뒤 색인. 불확실 API 표(`StartCameraFade`, `AsyncSaveGameToSlot` 콜백 스레드, `OnPreExit` 시점).

### 7. 하지 않는 것
지도 UI·텍스처·미니맵(15b), 다른 지역(베이스맵) 간 레벨 전환, 수동 슬롯·클라우드 세이브, 설정 저장(설정 UI 뒤), `sounds[]`(WP-17 채택 뒤), 위치기반서비스 관련 실제 위치 수집(하지 않음 — 세이브는 게임 안 좌표만).

## 산출물 (`docs/spec/zone-manifest.md`·`zone-manifest.schema.json`, `tools/golmok_tools/`, `unreal/Golmok/Source/Golmok/Zones/`·`Map/`·`Save/`, `Content/Python/golmok/synthetic_zone.py`, `tools/scripts/make_synthetic_zone.py`, `docs/`)
1. 스키마 v2(문서·JSON 스키마·validator·CLI·생성기·픽스처). 2. `AGolmokZone::GetSpawnUE`·manifest v2 파서. 3. `Map/GolmokTravelSubsystem` + 콘솔·HUD. 4. `Save/GolmokSaveGame`·`GolmokSaveSubsystem` + 콘솔. 5. 순수 헤더 `GolmokTravelMath.h`·`GolmokMapMath.h` + g++ 교차검증. 6. UE 자동화 3개. 7. 런북 V-14. 8. 이 문서 "결과" + STATUS/ROADMAP 문안.

## 완료 기준
클라우드: 위 산출물, 기존 자동화·V-03/V-07 런북 동작 불변(v1 manifest 그대로 읽힘), pytest·ruff·check_repo·CI 초록, 적대적 검증 1라운드 → 🟡 코드 완료·PC V-14 대기. PC: V-14 통과 → 15a 🟢. 15b는 D-009 자문·실제 zone 뒤.

## 주의
- hot-spot(§7.6): `GolmokCharacter`·`PlayerController`·`GameMode`·`Build.cs`·`Default*.ini`·등록부 테스트는 훅만. Astra 레인(`Characters/`·`Audio/`) 수정 금지. 포토 모드 델리게이트는 훅 블록.
- 세이브에 UE 좌표·실제 위치·개인정보를 넣지 않는다. 세이브 스키마 버전 필드 필수.
- 세션 운영: Opus ultracode(구현 → 적대적 검증 1라운드), Workflow 2시간 상한, 브랜치 `claude/wp15a-travel-save`(WP-14a와 병렬), PR draft, 병합은 오케스트레이터(WP-14a 병합 뒤 §4 시간대 API 연결 커밋 추가).

## 결과
**15a 🟡 코드 완료·PC V-14 대기**(2026-09-28, 세션 https://claude.ai/code/session_018Tn23KryyZ9XmYXMAa91Mb, 브랜치 `claude/wp15a-travel-save`, PR [#49](https://github.com/wooklym/golmok/pull/49); Opus ultracode — 구현 → 적대적 검증 1라운드(검토 2: 컴파일/API, 스펙/로직) → 확정·유력 결함 반영) → **🟢 V-14 통과**(2026-10-04, 아래 "PC 검증 V-14"). 클라우드 게이트: ruff·format OK, pytest **950 passed / 3 skipped**(기준 864 → +86: `test_zone_manifest_v2.py` 63, `test_ue_travel_math.py` 15, 기타), `check_repo.py` OK, `git diff --check` OK. **리뷰 반영 뒤**(아래 "리뷰 반영", main 4f91133 병합 상태): ruff·format OK, pytest **978 passed / 3 skipped**(main 병합분 +28, 반영 자체는 pytest 추가 없음 — 교차검증할 순수 로직이 없는 UE 수명주기 수정), `check_repo.py` OK, `git diff --check` OK. **병합 준비 뒤**(아래 "병합 준비", main 2e6b642 = WP-14a #51·#54 병합 상태): ruff·format OK, pytest **1132 passed / 3 skipped**(main 병합분; 시간대 연결 자체는 pytest 추가 없음 — UE 수명주기·세이브 직렬화라 g++ 교차검증 대상 아님, UE 자동화 `Golmok.Save.RoundTrip` 단계로 검증), `check_repo.py` OK, `git diff --check`(작업 트리·`origin/main...HEAD`) OK. UE 빌드·자동화는 PC(V-14, `runbooks/pc-verify-wp15a.md`).

### 구현 요약(스펙 산출물 1~8)
| # | 산출물 | 구현 |
|---|---|---|
| 1 | 스키마 v2 | `docs/spec/zone-manifest.md` §3.3·스키마 JSON 2벌(동일): `schema_version` 1\|2, v2 전용 선택 키 `spawn{position_enu,yaw_deg}`·`display_name`(1~64자, 공백만 금지), v1에 v2 키는 오류, 그 밖의 알 수 없는 키 오류 유지, "v2 예약 없음(`sounds[]`는 v3)". validator: spawn footprint 밖 경고(`--strict` 실패). `golmok-zone init` → v2(`--display-name`, `--spawn X,Y,Z,YAW`), `bump` 버전 유지. 픽스처 3개 v2 + spawn + display_name(생성기 재실행; Zone Index 파일 불변, schema 1) |
| 2 | UE 파서·스폰 | `GolmokZoneManifest` v1/v2(`bHasSpawn`, `SpawnPositionEnu`, `SpawnYawDeg`, `DisplayName`, `GetDisplayName()`), v1 파일은 종전과 바이트 단위로 같은 결과. `AGolmokZone::GetSpawnUE(FVector&, float&, bool*)`: 루트 × (100x, −100y, 100z), UE Yaw = 루트 yaw − yaw_deg; 폴백 = zone-local (0,0,0) +3 m에서 `ECC_WorldStatic` 하향 트레이스(없으면 원점), yaw_deg 0 |
| 3 | 이동 | `Map/GolmokTravelSubsystem`(World): 스펙 §2 ①~⑧ 순서, `EGolmokZoneRequestSource::Travel`(액터가 없으면 인덱스에서 스폰), `ReleasePin`/`IsZonePinned`, `StartCameraFade`, 폴링 0.05 s·타임아웃 20 s, 실내 → 부모 스폰, 다른 지역(인덱스 bbox 중심이 레벨 원점에서 `MaxRegionDistanceKm` 30 km 밖) "지원 안 함", 콘솔 `golmok.travel <id>\|list\|status`, HUD `travel:` 줄(Debug 훅) |
| 4 | 세이브 | `Save/GolmokSaveGame`(SaveSchemaVersion 1: `bHasPosition`, Lat/Lon/HeightEllipsoidal, ENU `YawDeg`, ZoneId/Version, `TimeOfDay{PresetName}` → 병합 준비에서 `{PresetName, Minutes, Mode}`, `Visited[]`, `Photos[]`(Saved/ 상대), `CharacterId`, `LevelName`, `SavedAtUtc`) · `Save/GolmokSaveSubsystem`(GameInstance, `golmok_auto`, Async 저장, 트리거 이동·첫 방문·사진(`OnPhotoSaved` 훅)·주기 60 s(변경 시)·월드 종료/`OnPreExit` 동기, 복원 ①②③·`-GolmokNoRestore`·`HomeZoneId`, 콘솔 `golmok.save [status\|reset]`·`golmok.load`) |
| 5 | 순수 헤더 | `Map/GolmokTravelMath.h`(스폰·폴백·yaw 부호·거부 순서·폴링·복원 규칙·주기 저장), `Map/GolmokMapMath.h`(bbox↔픽셀 선형/웹 메르카토르, z16 셀↔픽셀, 월드 픽셀) + `tools/tests/test_ue_travel_math.py`(g++ 교차검증: transform.py·index.py·numpy) |
| 6 | UE 자동화 +3(28 → 31) | `Golmok.Zone.ManifestV2`(PIE 없음), `Golmok.Travel.Teleport`·`Golmok.Save.RoundTrip`(L_ZoneTest PIE, `-nullrhi`) |
| 7 | 런북 | `docs/runbooks/pc-verify-wp15a.md`(V-14, 불확실 API 표 10행) |
| 8 | 이 절 | 아래 판단·검증·병합 시 반영 |

hot-spot·레인: `Build.cs`·`Default*.ini`·GameMode·PlayerController·Character·pyproject·CI·check_repo **미변경**. 훅은 별도 커밋(`[WP-15 hook]` 블록: Photo `OnPhotoSaved`, Debug HUD 줄; 등록부 `CONSOLE_COMMANDS` 3줄·`CONVENTION_FOLDERS += ("Map", "Save")`). Audio/·Characters/·Lighting/ 수정 없음(Characters·Lighting은 공개 API 읽기만). Slate/UMG 없음. `pc-verify-wp12.md` 자동화 총수 28 → 31(등록부 테스트가 요구).

### 판단(스펙 빈틈, 원칙: v1 호환·기존 자동화/런북 불변·UE 좌표 저장 금지·hot-spot 훅만)
1. **PIE 자동 복원 끔**(`bRestoreInPIE=False`, Config): 켜 두면 한 번 플레이한 뒤 모든 PIE가 PlayerStart가 아닌 곳에서 시작해 V-03/V-07/V-09/V-10 런북 동작이 바뀐다. 게임(`-game`·패키지)은 스펙대로 복원, PIE는 `golmok.load`. 저장은 PIE에서도 한다. **Fable 설계 리뷰(R49-6)가 채택**: 기존 PIE 런북의 PlayerStart 결정성 유지, 제품 복원은 standalone/패키지에서 V-14가 확인.
2. **자동화 중 자동 저장·복원 끔**(`GIsAutomationTesting`): 테스트가 개발자 슬롯을 덮지도, 개발자 슬롯이 테스트를 바꾸지도 않는다. 테스트는 `golmok_test_wp15a` 슬롯.
3. **세이브에 `LevelName`**(맵 패키지, 좌표 아님) 추가: 슬롯이 하나라 다른 레벨(L_Dev·스파이크 맵)에 위치를 적용하지 않기 위해. 스키마 1 유지(필드 추가·기본값).
4. **보류(hold)**: 복원 대기·거부·타임아웃 동안 스냅샷의 위치/zone은 슬롯 값을 유지(이동 도착 또는 2 m 넘게 걸으면 해제) — 실패한 복원 뒤 종료 저장이 PlayerStart로 세이브를 덮지 않는다.
5. **리셋 억제**: `golmok.save reset` 뒤 새 방문·사진·이동·`golmok.save` 전까지 자동 쓰기(종료·pre-exit·비행 중 async 포함) 안 함. 리셋 때 플레이어가 서 있던 zone(footprint 포함, 로드 여부 무관)은 **나갔다가 다시 들어올 때까지**(또는 다른 쓰기로 억제가 풀릴 때까지) 첫 방문이 아니다 — 그러지 않으면 다음 1 s 폴링이 그 zone을 첫 방문으로 기록하며 억제를 풀고 슬롯을 되살린다(R49-1).
6. **저장 위치 = 캡슐 중심**, yaw = 영역 ENU 기준(−UE Yaw). 복원은 `TravelToLocation`(같은 선로드·페이드; zone이 비었으면(베이스맵) 즉시 배치).
7. **실내 저장 위치는 부모 스폰으로**: 실내는 포털이 서브레벨·조명 오버레이를 소유하므로 위치 복원 대상이 아니다(이동과 같은 규칙).
8. **폴백 yaw 0 = zone-local yaw_deg 0**(zone +x 방향, UE Yaw = 루트 yaw). 스폰 위치 = 발, 도착 = 발 + 캡슐 반높이 + 2 cm(sweep 없음).
9. **로딩 중 이동 입력 차단**(`SetIgnoreMoveInput`, 짝 관리) + 폴링 중 포토 모드·포털 전환이 시작되면 실패 처리(①을 다시 확인).
10. **pin**: 이동 전에 이미 pin(콘솔/포털)이었던 zone은 도착 뒤에도 pin을 풀지 않는다.
11. **첫 방문** = 로드된 모든 zone 중 footprint가 플레이어를 포함하는 것(겹친 낮은 우선순위 zone 포함), 1 s 폴링(매 프레임 아님).
12. **HUD 줄은 Debug 훅으로 직접**: `ExtraHudLineProviders`에 넣으면 `Golmok.Audio.StateMachine`이 개수(1)를 단언해 깨진다.
13. **OnPhotoSaved는 png가 있을 때만** 발화(`-nullrhi`는 png를 쓰지 않음) — 자동화는 `NotePhoto`로 색인을 검증.
14. **캐릭터**: WP-18 `UGolmokCharacterSubsystem::GetCurrentId/SelectCharacter`가 이미 공개라 저장·복원에 사용(Astra 후속 불필요, Astra 파일 무수정). → 자동 선택까지 저장해 다음 실행에 명시로 고정하던 문제(R91-1)는 아래 "R91-1 후속"(명시 선택만 저장, T20 `IsExplicitSelection()`).
15. **시간대**: WP-14a 전이라 `PresetName`만(`ApplyPreset(Name, true)`). ~~WP-14a 병합 뒤 `{Minutes, Mode}` 연결 커밋 필요~~ → **반영(2026-09-28, 아래 "병합 준비")**: `{PresetName, Minutes, Mode}` 저장, 모드별 즉시 복원, `Minutes < 0`(구 세이브)은 프리셋 폴백, 스키마 1 유지.
16. **z_synthetic_002 스폰을 파사드 B 창 앞(x −8)** 으로: 002는 충돌 에셋이 없어 L_ZoneTest `Zone_Ground`(001 중심 ±200 m)가 받쳐야 하는데 문 앞(x +5)은 205 m로 평면 밖.
17. z_synthetic_001 매니페스트는 생성기가 없는 WP-02 픽스처라 `zm.load → zm.save`로 v2 키를 넣었다(원본 바이트 왕복 확인).
18. **GeoOrigin 없는 레벨에서 Zone Index zone 이동 거절**(R49-8): '다른 지역' 규칙은 **레벨 원점 기준 반경 `MaxRegionDistanceKm` 30 km의 휴리스틱**(index bbox 중심까지의 수평 거리)이지 실제 지역 경계가 아니다. `AGolmokGeoOrigin`이 없는 레벨(`L_Dev`)에서는 그 거리도 잴 수 없고, index zone을 스폰하면 geo 폴백이 zone을 레벨 원점에 세워 엉뚱한 곳으로 이동하므로, 레벨에 배치되지 않은(index에서만 아는) zone은 `travel to <id> refused: this level has no geo origin (AGolmokGeoOrigin), …`로 거절한다(`LastError`·HUD·콘솔). 레벨에 배치된 zone은 원점 없이도 이동 가능(종전 동작). `golmok.travel list`는 그 행에 `[no geo origin: not supported]`. 순수 헤더 `CheckTravel`은 바꾸지 않고 서브시스템에서 거절(g++ 교차검증 대상 불변).

### 적대적 검증(1라운드, 검토 에이전트 2)
| # | 지적 | 판정 | 조치 |
|---|---|---|---|
| A1 | PIE 매 시작 복원·레벨 무관 적용 → 기존 PIE 런북 동작 변경 | 유력 | 판단 1·3(`bRestoreInPIE=False`, `LevelName` 일치 시만) |
| A2 | 복원 실패 뒤 종료 저장이 PlayerStart로 세이브를 덮음 | 유력 | 판단 4(hold) |
| A3 | 로딩(검은 화면, 최대 20 s) 중 이동 입력으로 포털 진입·포토 모드 | 유력 | 판단 9 |
| A4 | `golmok.save reset` 뒤 종료/비행 중 async가 슬롯을 되살림 | 유력 | 판단 5 |
| A5 | async 비행 중 sync 쓰기 순서 역전 | 유력 | sync 뒤 async 완료 시 최신 스냅샷으로 재기록(`bSyncAfterAsync`), 월드 종료 뒤 큐 재발행 안 함 |
| A6 | 복원 전 첫 방문 저장 경쟁 | 유력 | `bRestorePending` 동안 방문 저장·주기 저장 안 함 + hold |
| A7 | 도착 단언이 `GetSpawnUE`와 순환, 합성 루트가 거의 무회전이라 전치 오류를 못 잡음 | 확정(테스트 공백) | 독립 경로(루트 `FTransform` × `EnuToUE`, 루트 yaw − yaw_deg) 단언 + 루트 30° 회전 케이스 추가 |
| A8 | 도착 시 기존 콘솔 pin까지 해제 / 첫 방문이 승자 zone만 | 유력(낮음) | 판단 10·11 |
| A9 | 헤더의 `FTimerHandle`이 PCH에만 기대 | 유력(빌드) | 두 헤더에 `TimerManager.h` |
| A10 | `UEToEnu(const Vec3& UE)`가 전역 네임스페이스 `UE`를 가림 | 유력(낮음) | 인자 이름 `PointUE` |
| — | API 시그니처(카메라 페이드·Async 저장·타이머·JSON·Printf 형식), UHT, C4458, unity 이름, 전치·부호·경위도 인자 순서, v1 호환, hot-spot/레인, 개인정보 | 확인(문제 없음) | — |

### 리뷰 반영 (PR #49 R49-1~9, 2026-09-28)
오케스트레이터가 브랜치를 인수해 클라우드 Opus 5.5 세션(https://claude.ai/code/session_01NM6uvZaVMgq5SUSaduHD1Z)에서 반영. UE 컴파일은 PC(V-14).
- **R49-1 (A)** `Save/GolmokSaveSubsystem.cpp` `ResetSlot`·`OnVisitPoll`: 리셋 때 플레이어를 포함하는 zone id를 `ResetPresentZoneIds`(transient)에 기록하고, 억제 중에는 그 zone을 첫 방문으로 기록하지 않으며(억제 해제·저장 없음) 플레이어가 footprint를 벗어나면 집합에서 뺀다(다른 쓰기로 억제가 풀리면 비움) → 판단 5. `golmok.save reset`·`status` 메시지에 `no first visit for <zone> until you leave`. 자동화 `Golmok.Save.RoundTrip`에 단계 추가(자동 저장 켠 리셋 → 직접·타이머 폴링 → `HasSave()` false, 나갔다 들어오면 첫 방문·재저장; 테스트 훅 `PollVisitsNow()`·`GetResetPresentZoneIds()`), 런북 §2·§7. 곁들여 `OnAsyncSaved`가 리셋 뒤 비행 중이던 쓰기를 `SlotName`이 아니라 그 쓰기의 `InSlotName`으로 지운다(테스트 정리가 슬롯 이름을 되돌린 뒤에도 개발자 슬롯을 지우지 않게).
- **R49-2 (B)** `OnWorldBeginTearDown`·`TakeSnapshot(bForce)`: `FWorldDelegates::OnWorldBeginTearDown`(EndPlay 전, 액터 유효)에서 `bIsTearingDown` 게이트를 우회해 스냅샷을 갱신 → 월드 종료·pre-exit 동기 저장이 최대 1 s 묵은 폴링 스냅샷이 아니라 종료 순간 위치를 쓴다. 런북 §4 확인 줄, §9 #11(API 불확실·대안).
- **R49-3 (B)** `GolmokSaveConsole::CmdSave`: `SaveNow` 전에 `ReleaseHold("console save")`(명시 저장은 "여기"). `ReleaseHold`를 public으로. 런북 §4.
- **R49-4 (B)** `docs/spec/zone-manifest.md` §3.3: `z_synthetic_002` 스폰을 픽스처·생성기·런북과 같은 `[−8, 3, −0.16]` yaw 90(파사드 B 유리창 앞)으로 정정.
- **R49-5 (B)** 런북 §4: `golmok.save` 기대 로그를 두 줄(`GolmokSave: saved … : zone …`, `golmok.save: saved golmok_auto (sync, console)`)로.
- **R49-6 (설계)** 판단 1 `bRestoreInPIE=False` — Fable 설계 리뷰 채택(판단 1에 기록; DECISIONS 기록은 병합 때 오케스트레이터).
- **R49-7 (병합)** WP-14a(#51) 병합 뒤 main 병합·자동화 수 32·시간대 `{Minutes, Mode}` 연결 커밋 — 이 반영 범위 밖(오케스트레이터).
- **R49-8 (note)** `Map/GolmokTravelSubsystem.cpp` `StartTravel`·`DescribeList`: GeoOrigin 없는 레벨에서 index zone 이동 거절 → 판단 18, 런북 §8.
- **R49-9 (note)** 런북 §9 #2: PIE GameInstance 해제 뒤 끝나는 async 쓰기는 완료 델리게이트가 약한 바인딩이라 재기록되지 않아, 종료 동기 저장보다 약 1 s 이내 오래된 데이터가 남을 수 있음(알려진 한계).
- R49-10 (note, 디스크 v1 경로는 `ManifestV2` 텍스트 변형으로만 커버): 허용, 조치 없음.

### 병합 준비 (2026-09-28): WP-14a 시간대 연결 · 자동화 32
WP-14a(PR #51)가 main에 들어온 뒤 오케스트레이터 결정(R49-7 / R51-2)으로 클라우드 Opus 5.5 세션(https://claude.ai/code/session_01NM6uvZaVMgq5SUSaduHD1Z)이 반영. UE 컴파일은 PC(V-14).
- **main 병합**(origin/main 2e6b642 = WP-14a #51·V-10 #54): 충돌 2곳 — `docs/plan/STATUS.md`(main의 WP-13·WP-14a 행을 따르고 이 브랜치의 WP-15a 행만 유지), `docs/runbooks/pc-verify-wp12.md` 자동화 총수(main 29·이 브랜치 31 → **32** = Photo 3 + 기존 29: WP-09까지 16·WP-18 7·WP-13 2·WP-14a `Lighting.Clock` 1·WP-15a 3; `tools/tests/test_ue_wp12_fixture.py`가 코드에서 세어 단언 — 테스트 수정 없음). `Debug/GolmokDebugSubsystem.cpp`는 자동 병합(main의 `tod:` 줄 `DescribeClock()` + `[WP-15 hook]` travel 줄).
- **세이브 필드**(`Save/GolmokSaveGame.h`): `FGolmokSaveTimeOfDay`에 `float Minutes = -1.f`(−1 = 없음)·`uint8 Mode = 0`(`EGolmokClockMode`를 `static_cast`; Lighting 헤더에 세이브 형식이 묶이지 않게) 추가, `PresetName` 유지. `SaveSchemaVersion` 1 그대로(`Restore`가 1만 받으므로 올리면 옛 세이브가 거절됨; 태그 직렬화라 옛 세이브는 −1·0).
- **저장**(`TakeSnapshot`·`HoldSlotPosition`·`BuildSaveObject`): `GetTimeOfDayMinutes()`·`GetClockMode()`·`CurrentPreset`. 레벨 조명(`HasTimeOfDay()` false)이나 Fixed에서 키프레임 시각 없는 프리셋 기저(`interior` 등, `FindPreset`의 `bHasTime` false)는 `Minutes −1`(이름으로 복원).
- **복원**(`GolmokSavePrivate::RestoreTimeOfDay`, 모두 즉시): `SetClockMode(Fixed)` → Fixed `SetTimeOfDay(분, true)` / Clock `SetTimeOfDay(분, true)` + `SetClockMode(Clock)`(저장한 분부터 계속) / Realtime `SetTimeOfDay(RealtimeTargetMinutes(), true)` + `SetClockMode(Realtime)`(모드만 — 현지 시각). 오케스트레이터 지시는 "Clock → `SetClockMode(Clock)` 뒤 `SetTimeOfDay`", "Realtime → `SetClockMode(Realtime)`만"이었으나, WP-14a 코드상 `SetClockMode(Clock)`은 프리셋 기저에서 `JumpTo(…, bInstant=false)`(2 s 전환 + `OnPresetChanged(…, false)` 한 번 더)를, `SetClockMode(Realtime)`은 항상 2 s 전환 점프를 하므로 시계를 먼저 세우고 즉시 점프 뒤 모드를 거는 순서로 바꿨다(결과 상태는 같고 전환·중복 이벤트 없음). `Minutes < 0`(구 세이브) 또는 키프레임 없음 → 종전 `ApplyPreset(PresetName, true)`. 알 수 없는 `Mode` 값은 Fixed. Lighting/ 코드 무수정(공개 API만).
- **로그·콘솔**: 저장 로그 끝 `, tod HH:MM <mode> (<키프레임>)`(없으면 `tod <프리셋>`/`tod -`), `golmok.save status` `slot:` 줄 같은 표기, `golmok.load`·시작 복원 메시지 `, tod HH:MM <mode>`(Realtime은 ` (local time)`), `GolmokClockMath::FormatHHMM`. (`golmok.status` 콘솔은 없어 `golmok.save status`에 넣음.)
- **자동화**(`Golmok.Save.RoundTrip`, 이름 추가 없음 — 총 32): 단계 0 Clock 13:07 저장 → 슬롯 `Minutes` 787(±0.01)·`Mode` Clock·`PresetName` = 가장 가까운 키프레임 → Fixed 05:00으로 바꾼 뒤 규칙 ① 복원 → 분 787(±0.01)·Clock·`IsTransitioning()` false; 단계 1 슬롯 Realtime·01:40 → 모드 Realtime·시각 = `RealtimeTargetMinutes()`(1분 안); 단계 2 Fixed 16:40 → 분 1000(±0.01)·Fixed(규칙 ③, 위치 복원 없음에도 적용), 이어 기본값 `FGolmokSaveTimeOfDay()` + 다른 cycle 프리셋 이름(구 세이브) → 그 프리셋이 `CurrentPreset`·Fixed. `AGolmokTimeOfDay`나 키프레임이 없으면 `[Info] time-of-day steps skipped: …`.
- **문서**: 스펙 §3 "시간대 저장·복원"·§4 반영 완료, 런북 §0·§2(기대 Info·단언 목록·총 32)·§3/§4 저장 로그 `tod`·§4 Clock 모드 분 복원/Realtime 확인·§6 재시작 시간대(clock 18:MM)·§9 #12·§10.

### 병합 시 반영(오케스트레이터)
- STATUS WP-15a 행: `🟡 코드 완료·PC V-14 대기(2026-09-28, PR #49): manifest schema 2(spawn·display_name, v1 호환)·GolmokTravelSubsystem(golmok.travel)·GolmokSaveSubsystem(golmok_auto, 복원 ①②③, PIE 자동 복원 끔, 시간대 {분, 모드} 저장/복원 — 모드별 즉시·구 세이브는 프리셋 폴백)·순수 헤더 2(g++)·자동화 +3(총 32) · 런북 runbooks/pc-verify-wp15a.md` + V-14 행(대기).
- ROADMAP 게임 기능 줄에 한 줄: `지도·세이브 **WP-15** — 15a 🟡 코드 완료·PC V-14 대기(2026-09-28 PR #49: Zone 이동(선로드·페이드·스폰)·자동 세이브(경위도·방문·사진 색인·시간대 {분, 모드})·manifest v2), 15b 지도 UI·정사영상 텍스처는 D-009 자문·실제 zone 뒤`.

## 병합 기록 — [PR #49](https://github.com/wooklym/golmok/pull/49) (2026-09-28)

대상: `claude/wp15a-travel-save` 58b038d(세션 session_018Tn23KryyZ9XmYXMAa91Mb Opus 5.5 ultracode 구현 → Opus 읽기 전용 리뷰 R49-1~10 → Opus 수정 R49-1(A)·2/3/4/5/8/9 → WP-14a 병합 뒤 Opus 병합 준비: main 2e6b642 병합·자동화 32·시간대 {분, 모드} 연결). 병합: 오케스트레이터 결정(D-019).

- **판정: 🟡 코드 완료·PC V-14 대기.** 게이트(병합 트리): ruff·format 통과, pytest 1132 passed/3 skipped, check_repo OK, `git diff --check origin/main...HEAD` 깨끗. C++·UE 자동화(32)는 미컴파일 — 런북 `pc-verify-wp15a.md`(§9 불확실 API #1~#12, §6 standalone 복원).
- **리뷰 요약(R49)**: 레인·핫스팟 무변경, 훅은 별도 커밋 표식 블록, WP-13 훅 보존, v1 manifest 6개 validator·UE 파서 통과, 좌표 변환·세이브 내용(경위도 double·ENU yaw) 교차검증. (A) R49-1 reset 재방문 억제, (B) R49-2~5, note R49-8/9 반영; R49-6 `bRestoreInPIE=False` Fable 채택; R49-7은 병합 준비 커밋(자동화 32·시간대 연결); R49-10 허용.
- **Fable 결정 기록**: DECISIONS D-014·D-017 진행(bRestoreInPIE, GeoOrigin 없는 travel 거절, 시간대 연결·복원 순서).
- **(C) 옮긴 것**: STATUS 마지막 갱신·WP-15a 행·트랙 1B V-13/V-14 행·세션 로그, ROADMAP 게임 기능 줄, DECISIONS D-014/D-017, 이 절. 다음: V-14 PC 카드, 15b는 D-009 자문 뒤.

## R91-1 후속 — 명시 캐릭터 선택만 저장 (2026-10-04)

클라우드 Opus 5.5 세션(https://claude.ai/code/session_01NM6uvZaVMgq5SUSaduHD1Z), 브랜치 `claude/save-explicit-character`(main 8e7cfc5 기준). Claude 레인 파일만 고쳤다(`Save/`, `Tests/GolmokTravelSaveTest.cpp`, 이 문서, 런북 2개). UE 컴파일·자동화는 PC. **Astra T20의 `IsExplicitSelection()`을 쓰므로 T20 병합 전에는 컴파일되지 않는다 — T20 뒤에 병합한다.**

- **문제**(리뷰 [R91](https://github.com/wooklym/golmok/pull/91#issuecomment-5977339808) (B) R91-1, 기존 동작이며 T18 원인 아님): `TakeSnapshot`이 명시 여부와 무관하게 `GetCurrentId()`를 저장하고, `Restore`는 현재 id와 다르면 `SelectCharacter`로 다시 적용했다. `SelectCharacter`는 선택을 명시로 표시한다(T18 `bExplicitSelection`). 그래서 abp 세션의 **자동** `manny`가 다음 `-GolmokAnim=gasp` 실행에서 GASP 폰에 명시로 고정되고(standalone·패키지는 BeginPlay 다음 틱에 자동 복원, PIE는 `bRestoreInPIE=False`라 제외), 다음 세이브가 다시 `manny`를 쓴다. V-15 §B8로 `mode: gasp`가 기본이 되면, 옛 세이브가 있는 모든 실행이 HUD `anim: gasp`인 채 ①로 돈다.
- **규칙**: `UGolmokSaveGame::CharacterIdRule`(`int32`, `UPROPERTY(SaveGame)`, 상수 `CharacterIdRuleLegacy` 0·`CharacterIdRuleExplicit` 1)을 더했다.
  - 0은 규칙 이전 세이브다(자동 선택을 포함한 아무 현재 id). 필드가 없는 옛 `.sav`는 태그 직렬화로 0으로 읽힌다.
  - 1은 명시 선택만 담는다.
  - `SaveSchemaVersion`은 1 그대로다(필드 추가·기본값. `Restore`가 1만 받으므로 올리면 옛 세이브가 거절된다).
  - 스냅숏은 `IsExplicitSelection()`일 때만 `GetCurrentId()`를 저장하고, 자동이면 빈 id를 저장한다(이 월드에서 복원이 거절된 명시 id가 있으면 그 id — 판단 2). 규칙은 1이다(`FSnapshot::CharacterIdRule` 기본 1 → `BuildSaveObject`).
  - 예외는 하나다. 폰 스냅숏이 아직 없을 때 슬롯 값을 보류하는 경로(`HoldSlotPosition`)는 슬롯의 id와 규칙을 그대로 넘긴다. 레거시 자동 id가 규칙 1로 바뀌어 명시로 승격되면 안 되기 때문이다. 첫 폰 스냅숏이 둘 다 현재 값으로 바꾼다.
- **복원**:
  - 빈 id(규칙 1 = 저장 때 자동 선택)는 아무것도 하지 않는다.
  - **레거시 가드**: 규칙 0이고 id가 로스터 기본값(`default` 또는 `default_by_anim_mode`의 값, 지금은 `manny`·`manny_gasp`)이면 `SelectCharacter`를 부르지 않는다. 자동·모드 기본 선택이 그대로 남고, 메시지에 `, character manny (legacy default, not pinned)`가 붙는다. 판정은 순수 함수 `GolmokSaveCharacter::IsLegacyDefault(Rule, SavedId, Roster)`(헤더 선언)가 한다.
  - 그 밖의 id(규칙 1, 또는 레거시 비기본 `quinn` 등 — 사용자가 고른 것이므로 명시로 본다)는 종전처럼 `SelectCharacter`로 복원한다. 현재 id가 같아도 자동 적용일 뿐이면(`!IsExplicitSelection()`) 다시 불러 명시로 만든다. 그러지 않으면 다음 세이브가 그 명시 선택을 빈 id로 잃는다.
  - `SelectCharacter`가 거절하면(abp 폰의 GASP 항목, 캐릭터 뷰가 아직 없음, 캡슐이 막힘 등) 그 id는 다음 세이브에 남는다(판단 2). 메시지는 `, character <id> (not applied, kept for the next save)`, 로스터에 없는 id는 `(not applied, not in the roster)`이고 버린다.
- **판단**:
  1. 레거시 가드의 "로스터 기본 id"를 `default_by_anim_mode` 값까지 넓혔다. gasp 세션의 레거시 자동 `manny_gasp`도 같은 부류다. 옛 빌드에서 사용자가 일부러 기본 id를 골랐다면 그 선택을 한 번 잃는다(구별할 수 없다. 다시 고르면 규칙 1로 저장된다).
     - **가드는 복원 시점의 로스터로 판정한다**(적대적 검증 V3로 정정). 그래서 19b가 gasp 기본값을 바꾸는 것까지 막아 주지는 않는다. 규칙 0 세이브는 모두 세이브에 `CharacterId`가 생긴 WP-15a(2026-09-28)부터 이 변경 전까지의 빌드가 썼다. 그 빌드들의 로스터 기본값은 `default` `manny`(WP-18 `c9194d5`부터)와 `default_by_anim_mode` abp `manny`·gasp `manny_gasp`(WP-19 `3da6712`, 2026-09-30부터)뿐이다(`characters.json` 이력). V-15 §B8은 gasp 기본값 `manny_gasp`를 유지하므로 지금 로스터로 둘 다 걸러진다.
     - 19b가 gasp 기본값을 바꾸면 옛 자동 `manny_gasp`는 더는 기본값이 아니므로 명시로 복원·고정된다. 받아들인다: GASP 폰에서는 세이브 때와 같은 모습이고, abp 폰에서는 적용이 거절되어 자동 선택이 남는다(그 id는 판단 2로 세이브에 남는다). 옛 기본 id를 C++에 하드코딩하지 않는다. 바꾸게 되면 그 커밋이 이 판단을 다시 본다.
  2. **거절된 명시 복원은 세이브에 남는다**(적대적 검증 V1). 첫 초안은 명시 id 복원이 거절된 세션(예: 명시 GASP id를 abp 폰에 복원 → 로드 전 거절)의 다음 세이브가 빈 id를 써서, 이 서브시스템의 계약 "실패·보류된 복원은 세이브를 잃지 않는다"(`HoldSlotPosition`)를 어겼다. 이제 private `FString UnappliedCharacterId`(UPROPERTY 아님)가 그 id를 이 월드에서 새 명시 선택이 있을 때까지 들고 있다.
     - `Restore`: 캐릭터 단계 시작에서 비우고, `SelectCharacter` 뒤 `UnappliedCharacterId = (bSelected || !GetRoster().Find(id)) ? 빈 값 : id`다. 로스터에 없는 id(지워진 항목)는 버린다. 로스터 로드가 실패했으면(`GetLoadError()`) 규칙 1 id는 이미 명시 선택이므로 남기고, 규칙 0 id는 레거시 기본 id를 가릴 수 없으므로 버린다(규칙 1로 승격하지 않는다 — 검증 W2).
     - 빈 id·레거시 기본·이미 명시로 적용된 같은 id 갈래는 아무것도 남기지 않는다. 그래서 앞선 거절이 "자동"이라고 말하는 다음 복원 뒤의 세이브로 새지 않는다. 복원이 아무것도 하지 않고 일찍 끝나는 경우(슬롯 없음·스키마·다른 레벨)는 값을 그대로 둔다.
     - `TakeSnapshot`: `IsExplicitSelection()`이면 현재 id를 쓰고 `UnappliedCharacterId`를 비운다. 자동이면 `UnappliedCharacterId`(대개 빈 값)를 쓴다. 규칙은 1이다(적용되지 않은 명시 id도 명시 의도다).
     - 월드별 상태와 함께 `HandleWorldBeginPlay`에서 비운다(맵 이동은 종료 동기 저장이 그 id를 쓰고, 새 월드의 복원이 다시 판정한다). `golmok.save reset`(`ResetSlot`)에서도 비운다(지운 슬롯에서 온 값이라 다음 쓰기가 되살리면 안 된다 — 검증 지시 밖의 추가).
     - 시작 복원이 아직 판정하지 않은 동안(`bRestorePending`) 폰 스냅숏이 생겨도 슬롯의 id·규칙(`HoldSlotPosition` 통과)을 그대로 쓴다. 그 사이의 쓰기(월드 종료·이동 도착·`golmok.save`)가 슬롯의 캐릭터를 지우지 않게 한다(검증 W1, 길어야 한 프레임 창).
     - 남는 것: 이 월드에서 복원 전에 이미 한 명시 선택(예: `golmok.character quinn` 뒤 `golmok.load`)은 보이는 선택이므로 거절된 id보다 앞선다. `-GolmokNoRestore` 실행은 복원을 시도하지 않으므로 다음 세이브가 슬롯의 id를 덮는다(위치와 같은 종전 동작).
  3. `golmok.save status`의 `slot:` 줄은 `character quinn`(명시)·`character - (automatic)`(규칙 1 빈 id)·`character manny (legacy)`(규칙 0)로 쓴다. 저장 로그 형식은 바꾸지 않았다.
  4. `golmok.anim preview off`(Claude 레인 `Animation/GolmokAnimationSubsystem.cpp`)는 `SelectCharacter(현재 id)`를 불러 현재 항목을 **명시 선택**으로 만든다. 그래서 자동 `manny_gasp`도 preview off 뒤에는 규칙 1로 저장되고 다음 실행에 고정된다(적대적 검증 V4). 코드는 바꾸지 않았다 — 19b가 정한다. `runbooks/pc-verify-wp19.md` §A8에 힌트 한 줄.
- **의존**: Astra T20의 `bool UGolmokCharacterSubsystem::IsExplicitSelection() const`(`bExplicitSelection` 반환). 이 브랜치는 그 서명으로 썼고 캐릭터 레인 파일은 고치지 않았다. 그 밖에 쓰는 공개 API는 `GetRoster()`(`DefaultId`·`DefaultByAnimMode`)·`GetCurrentId`·`SelectCharacter`, 테스트 훅 `MutableRosterForTest`·`ApplyDefaultForTest`(`WITH_DEV_AUTOMATION_TESTS`)다.
- **테스트**(`Golmok.Save.RoundTrip` 안, 새 등록 없음 — 36 유지):
  - 지도 검사 전 순수 단언(리터럴 로스터 `manny`·abp `manny`·gasp `manny_gasp`): 규칙 0의 `manny`·`manny_gasp`는 레거시 기본이고, 규칙 0 `quinn`·규칙 1 `manny`·빈 id는 아니다. abp 값을 `quinn`으로 바꾸면 `default`에만 있는 `manny`도 레거시 기본이다(V2a).
  - 단계 0: 슬롯 `CharacterIdRule` 1. 자동 선택(전제: 명시 아님)은 `CharacterId` 빈 값, `golmok.save status`에 `character - (automatic)`.
  - 단계 3(동기): 위치·zone·`HomeZoneId`가 없는 슬롯을 써서 규칙 ③(이동 없음)으로 캐릭터 단계만 돌린다.
    - `SelectCharacter(quinn)` → 슬롯 `quinn`·규칙 1.
    - 모드 기본값을 모두 `quinn`으로 바꾼 로스터(GASP 폰의 `manny_gasp`와 같은 상황)에서 자동 `quinn` + 레거시 `manny` → 현재 id `quinn`, 자동 유지, 메시지 `(legacy default, not pinned)`, status `character manny (legacy)`. 같은 슬롯을 규칙 1로 → `manny` 명시.
    - 실제 로스터로 자동 `manny` + 레거시 `quinn` → `quinn` 명시.
    - 규칙 1 `manny`(자동과 같은 id) → 명시로 바뀐다.
    - 규칙 1 빈 id → 변화 없음, 메시지에 캐릭터 단계 없음.
    - 거절된 명시 복원(V1): 테스트 전용 항목 `wp15a_unloadable`을 넣는다. `quinn` 사본이고 메시가 `/Game/GolmokTests/Absent.Absent`(없는 에셋)라 `ApplyEntry`가 폰을 건드리기 전에 거절한다(`mesh/animation missing …`). `TGuardValue`가 `Entries`를 되돌린다. 슬롯 상태는 `SlotCharacter` 문자열(`id '…' rule N`) 하나로 비교하고, `SaveNow`가 실패하면 `save failed: …`라 단언이 헛통과하지 않는다.
      - 규칙 1 `wp15a_unloadable` 복원 → 전제(현재 id·자동 불변), 메시지 `(not applied, kept for the next save)`, 다음 세이브 `id 'wp15a_unloadable' rule 1`.
      - 로스터에 없는 `wp15a_not_in_roster` → 다음 세이브 `id '' rule 1`.
      - 거절 뒤 레거시 기본 복원(전제 `not pinned`) → `id '' rule 1`. 거절 뒤 `golmok.save reset` → `id '' rule 1`.
      - 거절 뒤 `SelectCharacter(quinn)` → `id 'quinn' rule 1`. 이어서 자동으로 돌아가도(`ApplyDefaultForTest`) `id '' rule 1`(거절된 id가 돌아오지 않는다).
  - 변이별로 실패하는 단언:
    - 스냅숏 게이트를 되돌리면 단계 0의 빈 id 단언.
    - 규칙 쓰기를 빼면 규칙 1 단언 2곳.
    - 레거시 가드를 빼면 자동 `quinn` 유지·자동 유지·메시지 단언.
    - 가드가 규칙을 보지 않으면 규칙 1 `manny` 단언.
    - 레거시 id를 모두 건너뛰면 레거시 `quinn` 단언.
    - 같은 id 재적용 조건을 빼면 "now explicit" 단언.
    - status 표기를 되돌리면 status 단언 2곳.
    - 모드 기본값 비교를 빼면 순수 `manny_gasp` 단언. `DefaultId` 비교를 빼면 순수 "DefaultId alone" 단언(V2a).
    - (V1) 스냅숏의 자동 갈래를 빈 값으로 되돌리거나 `Restore`의 `UnappliedCharacterId` 대입을 빼면 `id 'wp15a_unloadable' rule 1` 단언(대입을 빼면 메시지 단언도).
    - (V1) 대입의 `!Find` 항을 빼면 로스터 밖 id 단언. 캐릭터 단계 시작의 `Reset()`을 빼면 레거시 기본 뒤 단언. `ResetSlot`의 `Reset()`을 빼면 reset 뒤 단언.
    - (V1) 스냅숏 명시 갈래의 `Reset()`을 빼면 "does not come back" 단언. 명시 선택보다 보류 id를 앞세우면 `quinn` 단언.
    - 단언 없음: 대입의 `bSelected ||` 항(빼도 성공한 복원 뒤 다음 스냅숏의 명시 갈래가 지운다 — 사실상 관찰 불가), `HandleWorldBeginPlay`의 `Reset()`(테스트는 한 월드), 복원 보류 중 스냅숏의 슬롯 id·규칙 유지(W1)와 로스터 로드 실패 때 규칙 1 id 유지(W2)(둘 다 훅이 필요해 미검증), 폰 스냅숏 전 `HoldSlotPosition`의 id·규칙 통과(`HoldSlotPosition`은 private이고 자동화 중에는 시작 복원이 꺼져 있으며, 테스트의 `Restore`는 스냅숏이 이미 있어 그 경로를 타지 않는다 — **훅이 필요해 미검증**, V2b).
  - 매니킨이 없으면 PIE 캐릭터 단계는 `[Info] character steps skipped: …`로 건너뛴다(순수 단언은 돈다).
  - 세이브 필드를 미러링하는 Python 테스트·픽스처는 없다(`tools/`에서 `CharacterId` grep 0건). pytest는 바꾸지 않았다.
- **PC 확인**:
  - `runbooks/pc-verify-wp15a.md` §2(기대 Info, 자동화 36개), §6(선택 0회차: 옛 세이브의 레거시 기본 / 재시작: 명시 `quinn` 복원, 자동 선택은 `character - (automatic)`), §9 #13.
  - `runbooks/pc-verify-wp19.md` §A8(preview off는 명시 선택), §B7(GASP 설치 PC: 옛 abp 세이브 `manny` + `-GolmokAnim=gasp` → `manny_gasp` 유지, 명시 `quinn` → `quinn`, 명시 `manny_gasp`를 abp로 → 거절되어도 세이브에 남음; 옛 세이브 만드는 법).
- **적대적 검증 반영**(2026-10-04, (A) 0 · (B) 0 · (C) 6): V1 판단 2·복원·테스트, V2 테스트(a 순수 단언 추가, b `HoldSlotPosition` 통과는 미검증으로 표기), V3 판단 1 정정, V4 판단 4·`pc-verify-wp19.md` §A8, V5 `pc-verify-wp15a.md` 자동화 수 32 → 36(§2·§10), V6 `pc-verify-wp15a.md` §6 레거시 확인을 1회차 앞 선택 단계로·`pc-verify-wp19.md` §B7 옛 세이브 만드는 법(선택).
- **적대적 검증 2라운드**(2026-10-04, V1~V6 델타·T20 병합 트리, (A) 0 · (B) 0 · (C) 3, 모두 반영): W1 복원 보류 중 폰 스냅숏이 슬롯의 캐릭터를 지우던 한 프레임 창 → 슬롯 id·규칙 유지, W2 로스터 로드 실패 때 규칙 1 id도 버리던 것 → 규칙 1은 남김(판단 2 문장 정정), W3 `pc-verify-wp15a.md` §6 단서에 0회차 비기본 id 경우 추가. 컴파일(병합 트리 식별자·const·유니티 빌드)·변이 대응표·거절 경로(로그 없이 거절)·레인을 다시 확인했다.
- **게이트**(리눅스): ruff 통과, format 112, pytest 1501 passed / 3 skipped(기준과 같음), check_repo OK, `git diff --check` 통과, 자동화 등록 36.

## PC 검증 V-14 (2026-10-04)

PC 세션(Claude Opus 5.5, 워크트리 `goofy-maxwell-3aee56`, 브랜치 `pc/v14-verify-wp15a`, main `f1535ac` 병합 포함). 결과 표는 `runbooks/pc-verify-wp15a.md` §10, API별 결과는 §9.
- **판정 🟢**: 빌드 무수정, 자동화 36/36, §3~§8 통과(R49-1·R49-8·시간대 {분, 모드}·R91-1 명시 캐릭터 포함).
- **PC fix 1건(설계 의도 그대로, 메커니즘만 바뀜)**: R49-2 "종료 순간 위치"가 PIE 종료·`-game` 창 닫기에서 실패했다(마지막 1 s 폴링 위치 저장). UE 5.8은 이 두 경로에서 `BeginTearingDown` 전에 로컬 플레이어를 지워(`EndPlayMap`: `CloseRequested` → `CleanupGameViewport` → `RemoveLocalPlayer`) `OnWorldBeginTearDown` 안에서 폰이 없다. 종료 스냅샷을 `UGameViewportClient::OnCloseRequested`에서도 갱신하도록 고쳤다(복원 보류 중·첫 스냅샷 전 제외; teardown 핸들러는 `-game` quit·맵 전환용으로 유지). 위 "리뷰 반영" R49-2의 "`OnWorldBeginTearDown`(EndPlay 전, 액터 유효)" 기록은 이력으로 둔다.
- **관찰(룩, 후속 제안)**: 도착 페이드 인 동안 카메라가 스프링암 랙(`CameraLagSpeed 12`)으로 192 m를 날아와 캐릭터가 +0.33 s에 블러와 함께 들어온다. 도착 틱의 랙 1틱 해제 + 카메라 컷을 제안한다.

## 병합 기록 — V-14 PC 결과 [#98](https://github.com/wooklym/golmok/pull/98) (2026-10-04, 오케스트레이터 세션)

**판정**: WP-15a 🟢 · V-14 🟢. Opus 읽기 전용 리뷰 [P14](https://github.com/wooklym/golmok/pull/98#issuecomment-5979513801) 결과는 (A) 0 · (B) 3 · (C) 4다. PC 브랜치는 그대로 두고 클라우드 병합 브랜치 `claude/v14-merge`(PC head `3230eef` + main 병합 + `V-14: 병합 시 반영 (Opus)`)로 병합했다.

- **PC fix `d2eb06f`(R49-2) 적대 리뷰 — 차단 0**
  - 바인딩·해제: `HandleWorldBeginPlay`에서 바인딩하고, `HandleWorldEnd`·`Deinitialize`·재바인딩 전에 해제한다. `AddUObject`, `TWeakObjectPtr` 뷰포트.
  - 뷰포트가 없는 실행(서버·커맨드릿·자동화)은 종전 teardown 경로를 탄다.
  - #93(R91-1)과 맞는다: 복원 보류 중이거나 첫 스냅샷 전이면 건너뛰고, 그 뒤에는 `OnVisitPoll`과 같은 규칙이다.
  - 개발자 슬롯 쓰기 조건은 바뀌지 않았다.
- **(B) P14-1**: 런북 §9 #1~#13의 `||`(6열 표에 7셀) → 이 커밋에서 고쳤다.
- **(B) P14-3**: STATUS M2·WP-15a·V-14 행과 ROADMAP 15a를 갱신했고, 이 절을 추가했다.
- **(B) P14-2 도착 카메라 스윕 → Claude 레인 후속.** 스프링암은 텔레포트 뒤에도 랙 기준점을 유지하고, 카메라 컷도 없다. zone 없는 저장 위치 복원에는 페이드도 없다.
  - 수정: `Map/GolmokTravelSubsystem.cpp`에 `GolmokTravelPrivate::SnapCameraAfterTeleport(Pawn, PC)`를 두고 `Arrive`와 zone 없는 배치에서 부른다.
  - 동작: 폰의 모든 `USpringArmComponent`에서 랙을 잠깐 끄고 `TickComponent(0)`을 부른 뒤 랙을 복원한다. 이어서 `SetGameCameraCutThisFrame()`을 부른다.
  - hot-spot·훅·등록 수(36)는 바꾸지 않는다.
  - 테스트: `Golmok.Travel.Teleport` case 2에서 도착 시점 암 소켓–폰 거리가 암 길이 + |SocketOffset| + 50 cm 이하인지 단언한다.
  - PC 확인: 다음 L_ZoneTest 카드에서 60 fps로 다시 녹화한다.
  - → [#107](https://github.com/wooklym/golmok/pull/107) 반영(2026-10-04, 리뷰 R107 (A) 0): 단언은 충돌 전 암 끝과 소켓 둘 다(상한 = 암 길이 + |SocketOffset| + |TargetOffset| + 부착 오프셋 + 50 cm), zone 없는 저장 위치 배치에 페이드 인 추가. PC 확인은 `pc-verify-wp15a.md` §11.
- **(C)**
  - P14-4: STATUS 마지막 갱신 충돌은 §7.6대로 풀었다.
  - P14-5: `(sync, pre-exit)`는 V-14에서 나오지 않았다. 런북 §6·§9 #3 문구를 이 커밋에서 고쳤고, Save 헤더 주석은 P14-2 PR에서 고친다. 핸들러는 무해한 대비책으로 남긴다.
  - P14-6: close 경로 자동 회귀(선택: RoundTrip 종단 단계, 등록 36 유지).
  - P14-7: 수치 표기 차이로, 조치하지 않는다.
