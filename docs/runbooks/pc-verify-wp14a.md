# V-13 — WP-14a 시간대 폴리시(연속 시각·시계 모드) PC 검증

상태: 🟡 코드 완료·PC 미검증(클라우드는 UE를 빌드할 수 없다). 스펙·결과: [`plan/WP-14-time-of-day-policy.md`](../plan/WP-14-time-of-day-policy.md). 이 런북을 통과하면 WP-14a 🟢.

전제: V-03(WP-05 조명)·V-09(포토 모드)가 끝난 PC, L_Dev(`golmok.setup_dev_level`). §8 오디오 확인은 V-10(WP-13 임포트) 뒤에만 한다.

**14b 전 정상인 것**: night 프리셋은 WP-05 값 그대로(태양 lux 0) — night 근처 시각의 화면이 매우 어둡거나 검정인 것은 결함이 아니다(V-03 메모, 14b look-dev 항목). 이 런북은 **시각·보간·모드·이벤트가 맞는지**만 본다.

## 0. 바뀐 파일

| 파일 | 내용 |
|---|---|
| `Source/Golmok/Lighting/GolmokClockMath.h` (새) | 엔진 헤더 없는 순수 규칙: `WrapMinutes`, `ParseHHMM`/`FormatHHMM`, `FindKeyframes`(자정 넘김), `LerpYawShortest`, `Interpolate`(yaw 최단 호·나머지 선형·volumetric alpha<0.5면 prev), `IsSunVisible`(lux > 0.01), `IsNight`, `CheckKeyframeOrder`. g++ 교차검증 `tools/tests/test_ue_clock_math.py` |
| `Source/Golmok/Lighting/GolmokTimeOfDay.{h,cpp}` | `EGolmokClockMode { Fixed, Clock, Realtime }`, Config `TimeOfDayMinutes`(450)·`ClockMode`(Fixed)·`ClockMinutesPerRealSecond`(0.5)·`RealtimeOffsetMinutes`(0)·`NightLuxThreshold`(0.1) — **ini 변경 없음**. `SetTimeOfDay/GetTimeOfDayMinutes/SetClockMode/GetClockMode/IsNight/AdvanceClock/EvaluateClock/DescribeClock`, 델리게이트 `OnNightChanged(bool)`. 파서 schema 2(`time`). 콘솔 `golmok.tod time/mode/rate/status`. `Photo/GolmokPhotoModeSubsystem.h` include(Realtime이 `IsActiveIn`으로 포토 모드를 본다 — Photo 코드 수정 없음) |
| `Source/Golmok/Debug/GolmokDebugSubsystem.cpp` | HUD `tod:` 줄 끝에 `DescribeClock()`(한 줄) |
| `Source/Golmok/Tests/GolmokLightingTest.cpp` | `Golmok.Lighting.PresetsFile` schema 2 반영, 새 `Golmok.Lighting.Clock` |
| `Config/Golmok/lighting_presets.json` | `schema_version` 2, cycle 4개에 `time` 07:30 / 12:30 / 18:00 / 21:30. **조명 값은 한 글자도 안 바뀜** |
| `Content/Python/golmok/lighting{,_presets}.py` | 파서 schema 2·`parse_hhmm`/`format_hhmm`/`keyframes`, `set_time`/`mode`/`status` |

## 1. 빌드

```powershell
git pull
.\tools\ue\build.ps1
```
- [ ] 컴파일 성공(경고는 기록). 실패하면 §10 표의 번호로 고치고 `WP-14a: PC fix …` 커밋.
- [ ] `.\tools\ue\open-editor.ps1` → 에러 없이 열림. Output Log에 `TimeOfDay: presets not loaded` Error가 **없다**(PIE 시작 때 `LogGolmok: TimeOfDay: presets loaded (5) from …` — WP-05와 같은 줄).

## 2. 헤드리스 자동화 29

에디터를 닫고:
```powershell
.\tools\ue\test.ps1 -Filter Golmok.Lighting
.\tools\ue\test.ps1 -Filter Golmok. -SetupDevLevel
```
- [ ] 첫 명령: 3개(`PresetsFile`·`PresetApply`·`Clock`) 전부 `Success`(`-nullrhi`). `PresetApply`는 WP-05 코드 그대로다(Fixed 모드 동일성).
- [ ] `Golmok.Lighting.Clock`의 기대 `[Info]` 줄(테스트 코드 `AddInfo`):
  ```
  Golmok.Lighting.Clock   [Info] realtime: HH:MM realtime                         (그 순간 PC 로컬 시각)
                          [Info] clock moved M min in S s (rate 60)               (M ≈ S × 60; 단언 0.5×~1.5× + 2)
                          [Info] end: overcast_morning 09:00 fixed                (실내 이탈 뒤 09:00 보간 상태 — overcast_morning 값이 아님)
  ```
  로그에는 `TimeOfDay: interior overlay on (source t, base overcast_morning)`·`interior overlay off -> overcast_morning`이 한 번씩 찍힌다.
- [ ] 두 번째 명령: **29개** 전부 `Success`(WP-12 런북 §1의 28개 + `Lighting.Clock`).

## 3. PIE — 시계 모드로 하루 순환

L_Dev PIE, F1로 HUD를 켠다.
- [ ] 시작 HUD: `tod: (level) --:-- fixed`(레벨 조명 — 시각 없음). 키 **2** → 2 s 뒤 `tod: clear_noon 12:30 fixed`.
- [ ] 콘솔 `golmok.tod status` →
  ```
  LogGolmok: golmok.tod: status 12:30 fixed rate 0.5 min/s | prev clear_noon 12:30 next golden_evening 18:00 alpha 0.00 | current clear_noon | night no | interior off
  ```
- [ ] `golmok.tod rate 10` → `LogGolmok: golmok.tod: rate 0.5 -> 10 min/s (mode fixed)`. `golmok.tod mode clock` → `LogGolmok: golmok.tod: mode fixed -> clock at 12:30`.
- [ ] HUD가 `tod: clear_noon 12:30 clock x10`에서 1초에 10분씩 간다(하루 = 144 s). 약 2분 반 동안 지켜본다:
  - 태양이 **끊김 없이** 돌고 밝기·색이 이어진다(프리셋 사이 계단 없음). 18:00 근처 볼류메트릭 안개가 켜지는 순간(15:15, 12:30–18:00 중점)은 한 번 바뀌는 것이 정상.
  - HUD 이름이 **중점에서** 바뀐다: 15:15 → `golden_evening`, 19:45 → `night`, 02:30 → `overcast_morning`, 10:00 → `clear_noon`.
  - 21:25 무렵부터 night 구간은 어둡거나 검정(14b 전 정상). 태양은 lux ≤ 0.01인 21:29~21:32 사이에만 꺼지고(night 키프레임 lux 0 양옆) 그 밖에서 **깜빡이지 않는다**(가시성은 매 틱 lux > 0.01 한 규칙).
  - 자정(23:59 → 00:00)에서 튐 없이 이어지고 태양 yaw가 0° 쪽 최단 호로 돈다.
- [ ] 스크린샷(선택): 11:00·16:00·20:30 세 장 `pc-verify-wp14a-clock-*.jpg`.

## 4. 시각 점프 전환

- [ ] `golmok.tod time 18:00` → `LogGolmok: golmok.tod: time HH:MM -> 18:00 (golden_evening) over 2.0 s`, 2 s 보간(clock 모드면 전환 중에도 시계가 계속 가서 전환 끝이 18:00보다 조금 뒤 — 정상).
- [ ] `golmok.tod mode fixed` → `LogGolmok: golmok.tod: mode clock -> fixed at HH:MM`, HUD 시각이 멈춘다. `golmok.tod time 09:00` → 07:30과 12:30의 중간 조명(흐린 아침과 한낮 사이), HUD `tod: overcast_morning 09:00 fixed`.
- [ ] 오류 줄: `golmok.tod time 25:00` → `golmok.tod: ERROR time must be HH:MM (00:00-23:59), got '25:00'`; `golmok.tod mode dusk` → `golmok.tod: ERROR mode must be fixed|clock|realtime, got 'dusk'`; `golmok.tod rate abc` → `golmok.tod: ERROR rate must be a number in (0, 1440] min/s, got 'abc'`; `golmok.tod` → `usage: golmok.tod <preset>|next|list|status|time HH:MM|mode fixed|clock|realtime|rate <min/s>`(Warning).

## 5. Realtime·포토 모드 재동기

- [ ] `golmok.tod mode realtime` → `golmok.tod: mode fixed -> realtime at HH:MM`(PC 시계와 같은 시각), 2 s 전환. HUD `tod: <가장 가까운 키프레임> HH:MM realtime`이 1분마다 1분씩 간다.
- [ ] **P**(포토 모드)로 들어가 1분 넘게 머문다 → 조명·시각이 진입 시각에 머문다(HUD는 포토 오버레이라 `golmok.tod status`로 확인해도 된다). P로 나오면 2 s 전환으로 현재 PC 시각에 맞춰진다.
- [ ] 포토 모드 `PauseMode=TimeDilation`(ini 선택 키, 커밋하지 않음)으로 한 번 더: 같은 결과.
- [ ] realtime에서 키 **3** → `LogGolmok: TimeOfDay: preset golden_evening in realtime mode -> fixed`, 18:00에 멈춘다(설계상 판단 — WP 문서 결과 #3).

## 6. F5·키 4개 호환(Fixed 기본)

- [ ] 새 PIE(Fixed 기본). 키 1/2/3/4·F5·`golmok.tod <preset>|next|list`가 V-03(`pc-verify-wp05.md` §3)과 **같은 동작·같은 로그**. 차이는 HUD `tod:` 줄 끝의 ` HH:MM fixed`뿐(예: `tod: night 21:30 fixed`, 전환 중 `tod: clear_noon -> night 45% 21:30 fixed`).
- [ ] 실내 왕복(V-03 §5): 실내 진입 → 안개 0·노출 +1, 이탈 → 진입 전 조명으로 복귀. 추가로 `golmok.tod time 09:00` 뒤 왕복 → 이탈하면 09:00 보간 조명으로 돌아온다(overcast_morning으로 튀지 않음).
- [ ] V-09 포토 모드 §4(진입·종료 밝기)가 그대로.

## 7. HUD 줄

- [ ] `tod:` 줄은 노란색 그대로(접두 불변), 형식 `tod: <WP-05 Describe()> HH:MM <fixed|clock xR|realtime>`. 레벨 조명은 `--:--`.

## 8. 오디오 낮/밤(V-10 뒤)

- [ ] WP-13 임포트가 끝난 빌드에서 `golmok.tod mode clock`·`rate 10`: HUD 오디오 줄의 상태가 19:45(night 중점)에 `outdoor_night`, 02:30(overcast_morning 중점)에 `outdoor_day`로 바뀐다(`OnPresetChanged`가 중점에서 1회, Audio 코드 수정 없음). 포토·실내 규칙은 V-10 그대로.

## 9. 선택 ini 키(커밋하지 않음)

`Config/DefaultGame.ini`는 hot-spot이고 `test_ue_wp05_fixture.py`가 `[/Script/Golmok.GolmokTimeOfDay]` 키 집합을 고정한다. 시험할 때만 로컬에서 섹션에 더한다:
```ini
ClockMode=Clock            ; Fixed | Clock | Realtime
ClockMinutesPerRealSecond=0.5
RealtimeOffsetMinutes=0
NightLuxThreshold=0.1
TimeOfDayMinutes=450       ; Clock 시작 시각(InitialPreset이 있으면 그 키프레임)
```
- [ ] `ClockMode=Clock`으로 PIE → 시작부터 07:30 보간 상태에서 시계가 간다(HUD `clock x0.5`). 시험 뒤 되돌린다.

## 10. 불확실 API·가정

| # | 곳 | 가정 | 실패 시 |
|---|---|---|---|
| 1 | `GolmokClockMath.h` `ParseHHMM<TCHAR>`/`FormatHHMM<TCHAR>` | 템플릿이 `TCHAR`(Windows `wchar_t`)로 인스턴스화되고 `CharT('0')` 비교가 MSVC 경고 없이 컴파일(g++는 `char`·`wchar_t`·`char16_t` `-Wconversion -Wshadow -Werror` 통과) | `static_cast<int>` 추가 |
| 2 | `UENUM(BlueprintType) enum class EGolmokClockMode : uint8` + `UPROPERTY(Config)` | UHT가 같은 헤더의 enum Config 프로퍼티를 받아들이고 ini 값 `Clock`을 읽는다 | 열거 대신 `FString`/`uint8` Config + 변환 |
| 3 | `FDateTime::Now().GetMillisecond()` | 5.8에 있음(`Misc/DateTime.h`) | 밀리초 항 제거 |
| 4 | `FMath::IsFinite(float)` | 5.8에 있음 | `std::isfinite` |
| 5 | `UGolmokPhotoModeSubsystem::IsActiveIn(UWorld*)` from `AGolmokTimeOfDay` (const 메서드의 `GetWorld()`) | Lighting이 Photo 헤더를 include해도 순환 없음 | `GetWorld()->GetSubsystem<UGolmokPhotoModeSubsystem>()` |
| 6 | `USceneComponent::GetVisibleFlag()`, `UExponentialHeightFogComponent::bEnableVolumetricFog` 읽기 | 공개(기존 코드·테스트가 이미 씀) | — |
| 7 | 테스트 `TMap<FName, FGolmokLightingPreset>::Add(Key)` 참조 반환·`TestEqual(float, float)`·`AddLambda` 캡처 `this` | 5.8 그대로 | `Emplace`/`TestTrue(IsNearlyEqual)` |
| 8 | `FString::Printf(TEXT("%s"), TCHAR[6])` 배열 인자 | 5.8 형식 검사가 배열→포인터 변환을 받아들임 | `FString(Buffer)` 후 `*` |
| 9 | Python `unreal.GolmokTimeOfDay`·프로퍼티 `clock_mode`/`time_of_day_minutes`/`clock_minutes_per_real_second`·enum 값의 `.name`(`CLOCK`) | UE Python 이름 규칙 | `l.mode()`/`l.status()`가 `None` → `get_editor_property` 이름을 로그로 확인해 고침 |
| 10 | 정적 SkyLight 재캡처 | Clock/Realtime에서는 키프레임 이름이 바뀔 때(중점)만 `RecaptureSky()`(매 틱 아님). L_Dev가 real-time capture면 해당 없음 | 하늘 앰비언트가 늦게 따라오면 기록(14b 항목) |
| 11 | 전환 중 시계 진행 | clock 모드의 점프 전환은 매 틱 목표를 현재 시계로 다시 잡는다(`To = ComposeTarget()`) | 전환 끝 튐이 보이면 기록 |

## 11. 결과 기록

| 항목 | 결과 | 메모 |
|---|---|---|
| §1 빌드 | | |
| §2 자동화 3 / 29 | | |
| §3 하루 순환 | | |
| §4 점프·오류 줄 | | |
| §5 realtime·포토 | | |
| §6 Fixed 호환 | | |
| §7 HUD | | |
| §8 오디오(V-10 뒤) | | |
| §9 ini 선택 | | |
