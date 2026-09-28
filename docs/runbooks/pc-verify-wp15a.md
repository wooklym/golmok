# PC 검증 런북 — WP-15a Zone 이동·세이브·manifest v2 (V-14)

대상: PC Claude 세션(또는 사용자). 전제: V-07(`runbooks/pc-verify-wp09.md`) 통과 상태 — `L_Dev`·`L_ZoneTest`가 있고, `synthetic_zone.run(interior=True)`이 한 번 돌아 `z_synthetic_001`·`z_synthetic_001_interior` 에셋·서브레벨이 있으며, `Content/Golmok/Zones/index`가 커밋본과 같다. `cd tools && PYTHONUTF8=1 python -m pytest -q` 초록.
소요: 빌드 10~20분 + 헤드리스 10분 + 검증 60분. 결과는 이 문서 §10과 `docs/plan/STATUS.md`(V-14 행, WP-15a 행)에 적는다.

클라우드 세션은 UE를 컴파일할 수 없었다. **컴파일 에러가 나면 §9 표를 보고 고친 뒤 커밋**한다(`WP-15a: PC fix …`). 설계 의도를 바꾸는 수정이면 `docs/plan/WP-15-zone-travel-save.md` "결과"에 한 줄 적는다.

규칙:
- 기대 로그는 코드(`Map/GolmokTravelSubsystem.cpp`, `Save/GolmokSaveSubsystem.cpp`, `Zones/GolmokZone.cpp`)의 `UE_LOG`/`Printf` 형식에 픽스처 값을 넣은 것이다. `x.xx`·`…`는 PC에서만 정해지는 값.
- 세이브 파일: `<Project>\Saved\SaveGames\golmok_auto.sav`(`<Project>` = `unreal\Golmok`). 자동화는 `golmok_test_wp15a` 슬롯만 쓰고 끝에 지운다. **개발자 슬롯은 자동화가 절대 건드리지 않는다**(`GIsAutomationTesting` 동안 자동 저장·복원 꺼짐).
- **PIE에서는 시작 시 자동 복원을 하지 않는다**(`bRestoreInPIE=False` 기본 — 기존 PIE 런북 V-03/V-07/V-09/V-10이 항상 PlayerStart에서 시작하도록). PIE의 복원은 `golmok.load`로, 시작 시 자동 복원은 §6의 standalone `-game` 실행으로 확인한다.
- 픽스처 스폰(manifest v2, pytest가 값 고정): `z_synthetic_001` `spawn {position_enu [5, 4, 0], yaw_deg 90}`("합성 골목 1", 문 door_1 남쪽 5.5 m에서 북쪽=문을 봄), `z_synthetic_001_interior` `[0, -1.5, 0]` yaw 90(직접 이동 대상 아님 → 부모 스폰), `z_synthetic_002` `[-8, 3, -0.16]` yaw 90("합성 골목 2", 파사드 B 유리창 남쪽 2 m). 002는 001 동쪽 200 m → 스폰은 001 원점 동쪽 **192 m**로 `L_ZoneTest`의 `Zone_Ground`(001 중심 ±200 m) 안에 떨어진다 — 002는 충돌 에셋이 없으므로 이 평면이 캐릭터를 받친다. 폴백(스폰 없음): zone-local (0,0,0) 위 3 m에서 아래로 라인 트레이스, 맞으면 그 지면, 아니면 원점; 방향 yaw_deg 0(zone +x). 도착 위치 = 발 + 캡슐 반높이 + 2 cm, UE Yaw = 루트 yaw − yaw_deg(루트 yaw는 로그 `Zone z_synthetic_001 v1 root: … yaw x.xxxx deg`에서 읽는다).

## 0. 대상 파일
| 파일 (`unreal/Golmok/` 기준, 그 외 저장소 기준) | 내용 |
|---|---|
| `Source/Golmok/Zones/GolmokZoneManifest.{h,cpp}` | schema_version 1·2, v2 `spawn`/`display_name`(`bHasSpawn`, `SpawnPositionEnu`, `SpawnYawDeg`, `DisplayName`, `GetDisplayName()`); v1에 v2 키는 경고 후 무시 |
| `Source/Golmok/Zones/GolmokZone.{h,cpp}` | `GetSpawnUE(FVector&, float&, bool*)` — 스폰 또는 §1 폴백 |
| `Source/Golmok/Zones/GolmokZoneSubsystem.{h,cpp}` | `EGolmokZoneRequestSource::Travel`(액터가 없으면 인덱스에서 스폰), `ReleasePin`, `IsZonePinned` |
| `Source/Golmok/Map/GolmokTravelSubsystem.{h,cpp}` | 이동(거부 → 선로드 → 페이드 → 폴링 → 텔레포트 → 다음 틱 pin 해제·페이드 인·`OnTraveled`), 콘솔 `golmok.travel` |
| `Source/Golmok/Map/GolmokTravelMath.h`, `GolmokMapMath.h` | 순수 헤더(g++ 교차검증 `tools/tests/test_ue_travel_math.py`) |
| `Source/Golmok/Save/GolmokSaveGame.{h,cpp}`, `GolmokSaveSubsystem.{h,cpp}` | 세이브(SaveSchemaVersion 1)·자동 저장·복원 규칙 ①②③, 콘솔 `golmok.save`·`golmok.load` |
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
- [ ] `Golmok.Save.RoundTrip` `Success`. 기대 `[Info]`: `golmok.save: slot golmok_test_wp15a (exists), automatic off, …` 블록, `restore saved position from slot golmok_test_wp15a (…)`, `restore saved zone spawn (version changed) …`, `restore home zone spawn …`. `L_ZoneTest`에 GeoOrigin이 없으면 `[Info] skipped: …`(전제 위반).
- [ ] 네 번째 명령: **31개**(기존 28 + 위 3) 전부 `Success`. `test.ps1`의 `Succeeded:`는 Warning 있는 테스트를 따로 세므로 상태 열로 판정(V-03).
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
  GolmokSave: saving golmok_auto (async, travel): zone z_synthetic_002, visited 2, photos N, position yes
  ```
  화면이 약 0.35 s 검게 페이드 아웃 → 파사드 B 유리창을 마주 보고(북쪽) 서 있음 → 페이드 인. 캐릭터가 떨어지지 않는다(`Zone_Ground`). 로딩 중 WASD가 먹지 않는다(이동 입력 차단).
- [ ] **히치 기록**: `golmok.stats` 또는 `stat unit`으로 이동 순간 최대 프레임(ms)을 적고 `pc-verify-wp09.md` §6 표(비동기 로드 히치)와 비교. 001(에셋 있음, 비동기)로 돌아갈 때(`golmok.travel z_synthetic_001`)의 `arrived … after x.xx s`도 적는다.
- [ ] `golmok.zone.list`: 도착한 zone 행에 ` pinned`가 **없다**(다음 틱 해제). 002 행 `loaded … [index]`.
- [ ] `golmok.travel z_synthetic_001_interior` → `traveling to z_synthetic_001 (…); z_synthetic_001_interior is an interior: going to its parent z_synthetic_001's spawn` → 001 스폰(문 남쪽 5.5 m, 문을 봄).
- [ ] 거부: 존재하지 않는 id `golmok.travel z_nope` → `golmok.travel: ERROR travel to z_nope refused: zone is not in the index or the level`. 포토 모드(P) 중 콘솔 → `… refused: photo mode is active`. 문 안(실내 활성, 포털 active) → `… refused: a portal transition / interior is active`. 이동 중 두 번째 명령 → `… refused: already traveling`. HUD `travel:` 줄에 거부 사유가 10초간 보인다.
- [ ] `golmok.travel status`가 상태·마지막 도착·설정값(`timeout 20.0 s, fade 0.35 s, poll 0.05 s, region 30 km`)을 찍는다.

## 4. PIE — 세이브·복원(`golmok.load`)
- [ ] `golmok.save status` → `golmok.save: slot golmok_auto (exists), automatic on, restore on, home '', autosave 60 s, …` + `slot:` 줄(zone·lat/lon·tod·character·visited·photos).
- [ ] 시간대 `2`(다른 프리셋)로 바꾸고 조금 걸은 뒤 `golmok.save` → `golmok.save: saved golmok_auto (sync, console): zone …, visited …, photos …, position yes`. 위치·방향을 기억(HUD `pos` 줄).
- [ ] 50 m쯤 걸어가 방향을 돌리고 시간대 `1`로 바꾼 뒤 `golmok.load` → `golmok.load: restore saved position from slot golmok_auto (…): traveling to … [또는 placed at the saved position (no zone) …], tod <프리셋>…` → 저장한 자리·방향(±1 cm·±0.1°)으로 돌아오고 시간대가 저장 때 프리셋으로 즉시 바뀐다.
- [ ] 캐릭터: `golmok.character <다른 id>` → `golmok.save` → 원래 id로 바꾸고 `golmok.load` → 저장 때 캐릭터로 바뀐다(WP-18 공개 API `SelectCharacter`).
- [ ] 주기 저장: 가만히 60 s 이상 → 저장 로그 없음. 1 m 넘게 걷고 60 s가 지나면 `saving golmok_auto (async, periodic)` 1회.
- [ ] PIE 종료 → `GolmokSave: saved golmok_auto (sync, world end): …` 1줄(동기).

## 5. PIE — 사진 색인
- [ ] P → 촬영(`golmok.photo.shoot`) → 창이 닫히면 `GolmokSave: saving golmok_auto (async, photo): … photos N+1 …`. `golmok.save status`의 `slot:` 줄 photos가 1 늘었다.
- [ ] 탐색기에서 방금 png를 지우고 `golmok.load` → 메시지 끝 `photos N (1 missing dropped)`.

## 6. 재시작 복원(standalone `-game`)
에디터를 닫고:
```powershell
& "<UE>\Engine\Binaries\Win64\UnrealEditor.exe" "<repo>\unreal\Golmok\Golmok.uproject" /Game/Golmok/Maps/L_ZoneTest -game -windowed -ResX=1280 -ResY=720 -log
```
- [ ] 1회차: 002로 이동(`~` 콘솔 `golmok.travel z_synthetic_002`), 몇 걸음, 시간대 변경, 창 닫기(종료 동기 저장 `(sync, world end)` 또는 `(sync, pre-exit)`).
- [ ] 2회차: 같은 명령 → 시작 로그 `GolmokSave: restore on begin play: restore saved position from slot golmok_auto (saved …, zone z_synthetic_002 v1, index v1): traveling to z_synthetic_002 …` → 페이드 뒤 저장한 자리·방향, 시간대 복원, `golmok.travel list`에 001·002 `visited`.
- [ ] 3회차: `-GolmokNoRestore`를 붙여 실행 → `GolmokSave: restore skipped (-GolmokNoRestore)`, PlayerStart에서 시작. `golmok.travel list`의 visited는 **유지**(색인은 계속 이어짐).
- [ ] 폴백 ②: `golmok.save status`로 zone을 확인하고, 텍스트 편집 대신 콘솔로 확인하기 어려우면 생략 가능(자동화 `Save.RoundTrip`이 version 99·zone 없음·HomeZoneId를 이미 검증). (선택) `Config/DefaultGame.ini`를 **커밋하지 않는 로컬 수정**으로 `[/Script/Golmok.GolmokSaveSubsystem] HomeZoneId=z_synthetic_001` 넣고, 저장을 `L_Dev`에서 만든 뒤 `L_ZoneTest`로 실행 → `slot golmok_auto was saved in /Game/Golmok/Maps/L_Dev, this level is /Game/Golmok/Maps/L_ZoneTest: position not restored`.

## 7. 리셋
- [ ] `golmok.save reset` → `golmok.save reset: slot golmok_auto deleted; visit / photo index cleared`. 곧바로 창을 닫아도 `.sav`가 **다시 생기지 않는다**(리셋 뒤 새 방문·사진·이동·`golmok.save` 전까지 자동 쓰기 억제). 다음 실행 → `restore on begin play: no save in slot golmok_auto: nothing restored (PlayerStart kept)`.

## 8. 기존 런북 불변 확인(샘플)
- [ ] `L_Dev` PIE: 시작 위치 PlayerStart, `Golmok.Player.Movement` 등 기존 자동화 통과(§2). V-07 §4(발견 로그)·V-03 포털 왕복을 한 번 따라 해 로그가 같다(추가 줄은 `GolmokSave: first visit …`·`saving golmok_auto (async, …)`뿐).

## 9. 컴파일 에러가 나면 — 불확실한 UE 5.8 API와 대안
| # | 파일 | API | 불확실한 점 | 대안 | PC 결과 |
|---|---|---|---|---|---|
| 1 | GolmokTravelSubsystem | `APlayerCameraManager::StartCameraFade(From, To, Duration, Color, bShouldFadeAudio, bHoldWhenFinished)`, `StopCameraFade()` | 인자 순서·`bHoldWhenFinished` 동작(페이드 아웃 뒤 검정 유지) | 페이드 없이 `FadeSeconds=0` 동작(텔레포트만) 또는 `SetManualCameraFade(1.f, FLinearColor::Black, false)` / `(0.f, …)` | |
| 2 | GolmokSaveSubsystem | `UGameplayStatics::AsyncSaveGameToSlot(USaveGame*, const FString&, int32, FAsyncSaveGameToSlotDelegate)` 콜백 스레드 | 콜백이 게임 스레드에서 오는지(엔진은 게임 스레드로 되돌림으로 알려짐) | 콜백에서 UObject 접근을 `AsyncTask(ENamedThreads::GameThread, …)`로 감싼다 | |
| 3 | GolmokSaveSubsystem | `FCoreDelegates::OnPreExit` 시점 | 월드·폰이 이미 없을 수 있음 → 스냅샷 캐시로 저장(월드 없음 가정) | 로그 `(sync, pre-exit)` 유무만 기록 | |
| 4 | GolmokSaveSubsystem | `GIsAutomationTesting`(`CoreGlobals.h`) | Launcher 빌드에서 에디터 자동화 중 true인지 | 거짓이면 기존 자동화가 개발자 슬롯을 복원·기록 → `test.ps1`에 `-GolmokNoRestore` 추가는 hot-spot 아님(`tools/ue`)이나 PIE 복원은 이미 꺼져 있어 영향은 저장뿐 | |
| 5 | GolmokSaveSubsystem | `UWorld::RemovePIEPrefix(const FString&)`, `UObject::GetPackage()` | 5.x 정적 함수·접근자 | `World->GetOutermost()->GetName()` + `FString::Replace(TEXT("UEDPIE_0_"), TEXT(""))` | |
| 6 | GolmokSaveGame | `UPROPERTY(SaveGame, …)`와 `static constexpr int32 CurrentSchemaVersion` in `UCLASS` | UHT 허용 여부 | `SaveGame` 지정자 삭제(필드는 그대로 직렬화), 상수는 `.cpp`의 `namespace` 상수로 | |
| 7 | GolmokZone | `FTransform::ToMatrixNoScale()` + `FMatrix::M[r][c]`(행벡터 규약) | 전치 방향 — `Golmok.Travel.Teleport`의 30° 회전 루트 단언이 검증 | 대안: `GetActorTransform().TransformPosition(GolmokGeo::EnuToUE(p))`, yaw = 루트 yaw − yaw_deg | |
| 8 | GolmokTravelSubsystem | `APlayerController::SetIgnoreMoveInput(bool)`(카운터) | 짝이 맞지 않으면 이동 불가로 남음 | 로딩 중 입력 차단 줄 2곳 삭제 | |
| 9 | GolmokPhotoModeSubsystem 훅 | `UCLASS` 끝의 `public:` 뒤 `FGolmokOnPhotoSaved OnPhotoSaved;`(비동적 멀티캐스트) | UHT가 UPROPERTY 없는 델리게이트 멤버를 허용(WP-13 훅과 같은 패턴) | 멤버를 `public` 구역 맨 앞으로 옮기는 것은 hot-spot 규칙상 훅 블록 안에서만 | |
| 10 | Tests | `FFileHelper::SaveArrayToFile(TArray<uint8>, …)`, `FRotator + FRotator`, `TestNotNull(const T*)` | 오버로드 | `SaveStringToFile(TEXT("png"), …)` | |

## 10. 결과 기록
(PC 세션이 채운다: 빌드·자동화 31개·§3~§8 체크, 히치 표, 고친 API 번호·커밋, 설계와 다른 동작.)
