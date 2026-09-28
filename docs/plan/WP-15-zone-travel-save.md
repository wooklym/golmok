# WP-15 — Zone 지도·이동 + 세이브 (D-014·D-017): 15a 이동·세이브·스키마(클라우드) / 15b 지도 UI·지도 텍스처(PC·자문 뒤)

상태: 🔵 **15a 진행 중**(2026-09-28 착수, 세션 https://claude.ai/code/session_018Tn23KryyZ9XmYXMAa91Mb; 브랜치 `claude/wp15a-travel-save`, WP-14a와 병렬) · 담당: 15a **Opus 5.5 ultracode**(설계 Fable 5.1, 검증 Opus), 15b PC 세션 + 소유자 · PC 검증 번호 **V-14**(15a).

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
- `UGolmokSaveGame : USaveGame` 필드: `SaveSchemaVersion`(1), `Lat/Lon/HeightEllipsoidal`(double), `YawDeg`(ENU 기준, UE yaw 아님), `ZoneId`·`ZoneVersion`(현재 안에 있는 권위 zone, 없으면 빈 문자열), `TimeOfDay`(§4), `Visited[]`(`{ZoneId, Version, FirstVisitUtc}`), `Photos[]`(`Saved/` 기준 상대 경로 문자열만), `CharacterId`(WP-18 로스터 현재 id, 문자열; 없으면 빈 값), `SavedAtUtc`. UE 좌표는 저장하지 않는다.
- 자동 저장 슬롯 1개 `golmok_auto`(사용자 인덱스 0), `AsyncSaveGameToSlot`만 사용. 트리거: 이동 완료, 첫 방문(zone 진입 = `NotifyZoneLoaded` 뒤 `FootprintContains(플레이어)`가 처음 참일 때), 포토 촬영 완료(WP-12에 델리게이트가 없으면 `// [WP-15 hook]` 블록으로 `OnPhotoSaved(FString RelativePath)` 추가), 주기 `AutosaveIntervalSeconds`(기본 60, 변경이 있을 때만), 월드 종료(`EndPlay`·`FCoreDelegates::OnPreExit`)는 **동기** `SaveGameToSlot`(종료 중 비동기는 유실).
- 복원(`RestoreOnBeginPlay`, 기본 true; `-GolmokNoRestore` 명령줄로 끔 — 런북·자동화용): 월드 BeginPlay 뒤 GeoOrigin이 준비되면 ① 세이브의 `ZoneId`가 index에 있고 version 같음 → 저장 위치로 ② version 다름·zone 없음 → 그 zone(있으면) 또는 `HomeZoneId`(Config, 기본 빈 값 = 현재 PlayerStart 유지)의 스폰으로 `TravelToZone` ③ 어느 것도 없으면 복원 안 함(로그). 복원 뒤 시간대(§4)·캐릭터(§4) 적용. 위치 복원은 캐릭터가 이미 스폰된 뒤 `SetActorLocation`(GameMode·PlayerController는 hot-spot: 손대지 않고 서브시스템 `OnWorldBeginPlay`에서 한 틱 뒤 처리).
- 콘솔 `golmok.save`(즉시 동기 저장)·`golmok.save status`·`golmok.save reset`(슬롯 삭제)·`golmok.load`(즉시 복원). HUD `save:` 줄은 두지 않는다(로그만).

### 4. 다른 WP와의 계약
- **시간대**: WP-14a 병합 전에는 `TimeOfDay = {PresetName}`만 저장·복원(`ApplyPreset(Name, true)`); 병합 뒤 `{Minutes, Mode}`를 추가하고 우선 적용(WP-14a API `GetTimeOfDayMinutes/GetClockMode/SetTimeOfDay/SetClockMode`). 세이브 스키마는 1 그대로(필드 추가는 기본값으로 호환).
- **캐릭터(WP-18, Astra 레인)**: 로스터 현재 id를 읽는 공개 API가 있으면 저장·복원에 쓰고, 없으면 `CharacterId`를 비워 두고 WP 문서에 "Astra 후속: `UGolmokCharacterRoster::GetCurrentId/Select` 노출"을 적는다. Astra 파일은 고치지 않는다.
- **포토(WP-12)**: 사진 목록은 파일 시스템이 정본이고 세이브는 색인일 뿐 — 복원 시 없는 파일은 목록에서 제거.
- **Zone 겹침·pin**: 이동의 pin은 도착 뒤 해제, `bAutoManageInterior`·거리 규칙은 그대로. 이동 중 포털 오버랩은 무시(포털 상태 Idle 확인).

### 5. 15b (PC·자문 뒤) — 지도 UI
- 지도 텍스처: `golmok-basemap map-texture`(정사영상 축소 PNG + 도로 레이어 옵션) → `Content/Golmok/Map/<area>.png`(UFS 스테이징, 런타임 `IImageWrapper` 로드, `.uasset` 없음). 공개 배포 조건은 D-009 자문 결과에 따른다(게임 내부 사용은 D-012로 허용).
- UI: Slate `SGolmokMapWidget`(C++만, 위젯 BP 없음): 정사영상 위 Zone footprint/점·표시 이름·촬영일·방문 여부·현재 위치, 클릭/확인 → `TravelToZone`. 입력 액션 `IA_Map`(M)은 C++로 생성(규약). 미니맵은 기본 끔(옵션만). `Golmok.Build.cs`에 `Slate`·`SlateCore` 추가는 hot-spot 훅 블록(15b에서).
- 순수 수학(`GolmokMapMath.h`: WGS84 bbox ↔ 텍스처 픽셀, 웹 메르카토르 z16 셀 ↔ 픽셀)은 15a에서 미리 만들고 g++ 교차검증한다(15b가 그대로 쓴다).

### 6. 테스트·문서 (15a)
- pytest: 스키마 v2(`spawn`·`display_name` 형식·범위·v1 호환·알 수 없는 키 오류), `golmok-zone validate/init/bump` v2, 합성 zone 생성기 v2, Zone Index 불변 확인, `GolmokMapMath.h`·`GolmokTravelMath.h`(스폰 변환·폴백·yaw 부호) g++ 교차검증 표.
- UE 자동화(`-nullrhi`): `Golmok.Zone.ManifestV2`(v1/v2 파싱·폴백), `Golmok.Travel.Teleport`(합성 zone 2곳 사이 이동: 선로드→스폰 좌표·yaw→pin 해제→`OnTraveled`, 실내 거부, 포토 모드 중 거부, 타임아웃), `Golmok.Save.RoundTrip`(저장→로드 경위도 1 mm·yaw·방문·사진 색인, version 불일치 폴백, 슬롯 없음). 등록 +3.
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
(세션이 채운다.)
