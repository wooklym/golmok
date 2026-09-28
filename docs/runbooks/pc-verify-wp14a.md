# V-13 — WP-14a 시간대 폴리시(연속 시각·시계 모드) PC 검증

상태: 🟡 코드 완료·PC 미검증(클라우드는 UE를 빌드할 수 없다). 스펙·결과: [`plan/WP-14-time-of-day-policy.md`](../plan/WP-14-time-of-day-policy.md). 이 런북을 통과하면 WP-14a 🟢.

전제: V-03(WP-05 조명)·V-09(포토 모드)가 끝난 PC, L_Dev(`golmok.setup_dev_level`). §8 오디오 확인은 V-10(WP-13 임포트) 뒤에만 한다.

**14b 전 정상인 것**: night 프리셋은 WP-05 값 그대로(태양 lux 0) — night 근처 시각의 화면이 매우 어둡거나 검정인 것은 결함이 아니다(V-03 메모, 14b look-dev 항목). 이 런북은 **시각·보간·모드·이벤트가 맞는지**만 본다.

**설계 보완 §2a(2026-09-28)**: night 키프레임은 `"hold_minutes": 480` — 21:30부터 **05:30까지 night 그대로 유지**되고 05:30 → 07:30 두 시간 램프로 overcast_morning이 된다. 가장 가까운 키프레임 이름 night는 19:45~**06:30**(램프 중점).

## 0. 바뀐 파일

| 파일 | 내용 |
|---|---|
| `Source/Golmok/Lighting/GolmokClockMath.h` (새) | 엔진 헤더 없는 순수 규칙: `WrapMinutes`, `ParseHHMM`/`FormatHHMM`, `FindKeyframes`(자정 넘김·유지 구간 `bHeld`), `LerpYawShortest`, `Interpolate`(yaw 최단 호·나머지 선형·volumetric alpha<0.5면 prev), `IsSunVisible`(lux > 0.01), `IsNight`, `CheckKeyframeOrder`, `IsValidHold`·`HoldEnd`·`CheckKeyframeHolds`(§2a). g++ 교차검증 `tools/tests/test_ue_clock_math.py` |
| `Source/Golmok/Lighting/GolmokTimeOfDay.{h,cpp}` | `EGolmokClockMode { Fixed, Clock, Realtime }`, Config `TimeOfDayMinutes`(450)·`ClockMode`(Fixed)·`ClockMinutesPerRealSecond`(0.5)·`RealtimeOffsetMinutes`(0)·`NightLuxThreshold`(0.1) — **ini 변경 없음**. `SetTimeOfDay/GetTimeOfDayMinutes/SetClockMode/GetClockMode/IsNight/AdvanceClock/EvaluateClock/DescribeClock`, 델리게이트 `OnNightChanged(bool)`. 파서 schema 2(`time`, 선택 `hold_minutes`). 콘솔 `golmok.tod time/mode/rate/status`(유지 중이면 `status`에 `… hold until HH:MM`). `Photo/GolmokPhotoModeSubsystem.h` include(Realtime이 `IsActiveIn`으로 포토 모드를 본다 — Photo 코드 수정 없음). 리뷰 반영(PR #51): 시계 기준 `NextPreset`(시간상 다음 키프레임), 이벤트 순서(`IsNight` 먼저 → `OnPresetChanged` → `OnNightChanged`), Realtime 실시간 공백 재동기, 레벨 조명 `status --:--`, BeginPlay 로그 |
| `Source/Golmok/Debug/GolmokDebugSubsystem.cpp` | HUD `tod:` 줄 끝에 `DescribeClock()`(한 줄) |
| `Source/Golmok/Tests/GolmokLightingTest.cpp` | `Golmok.Lighting.PresetsFile` schema 2 반영, 새 `Golmok.Lighting.Clock` |
| `Config/Golmok/lighting_presets.json` | `schema_version` 2, cycle 4개에 `time` 07:30 / 12:30 / 18:00 / 21:30, night에 `hold_minutes` 480(§2a). **조명 값은 한 글자도 안 바뀜** |
| `Content/Python/golmok/lighting{,_presets}.py` | 파서 schema 2·`hold_minutes`·`parse_hhmm`/`format_hhmm`/`keyframes`/`holds`/`find_keyframes`/`describe_hold`, `set_time`/`mode`/`status`(`status()`에 `"hold"`) |

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
- [ ] 시작 HUD: `tod: (level) --:-- fixed`(레벨 조명 — 시각 없음). 이때 `golmok.tod status` →
  ```
  LogGolmok: golmok.tod: status --:-- fixed rate 0.5 min/s | current (level) | night no | interior off
  ```
  (HUD와 같은 규칙 — 시각·prev/next 없음, 리뷰 R51-7). 키 **2** → 2 s 뒤 `tod: clear_noon 12:30 fixed`.
- [ ] 콘솔 `golmok.tod status` →
  ```
  LogGolmok: golmok.tod: status 12:30 fixed rate 0.5 min/s | prev clear_noon 12:30 next golden_evening 18:00 alpha 0.00 | current clear_noon | night no | interior off
  ```
- [ ] `golmok.tod rate 10` → `LogGolmok: golmok.tod: rate 0.5 -> 10 min/s (mode fixed)`. `golmok.tod mode clock` → `LogGolmok: golmok.tod: mode fixed -> clock at 12:30`.
- [ ] HUD가 `tod: clear_noon 12:30 clock x10`에서 1초에 10분씩 간다(하루 = 144 s). 약 2분 반 동안 지켜본다:
  - 태양이 **끊김 없이** 돌고 밝기·색이 이어진다(프리셋 사이 계단 없음). 18:00 근처 볼류메트릭 안개가 켜지는 순간(15:15, 12:30–18:00 중점)은 한 번 바뀌는 것이 정상.
  - HUD 이름이 **중점에서** 바뀐다: 15:15 → `golden_evening`, 19:45 → `night`, **06:30**(night 유지 뒤 램프 05:30 → 07:30의 중점) → `overcast_morning`, 10:00 → `clear_noon`. 02:30에는 바뀌지 않는다.
  - 21:25 무렵부터 어둡거나 검정(14b 전 정상). 태양은 lux ≤ 0.01인 21:29 무렵부터 05:30 무렵까지 꺼져 있고(night 유지 구간 전체) 그 밖에서 **깜빡이지 않는다**(가시성은 매 틱 lux > 0.01 한 규칙).
  - **night 유지(§2a)**: 21:30 → 05:30(rate 10이면 48 s) 동안 조명이 **night 프리셋 그대로 멈춰 있다**(어둡거나 검정, 태양 방향·안개·노출 변화 없음). 05:30부터 2시간(12 s) 램프로 밝아지고 07:30에 overcast_morning. 유지 중 `golmok.tod status` → `… | night HH:MM hold until 05:30 | current night | night yes | …`.
  - 태양 yaw의 0°/360° 통과는 golden_evening(265°) → night(0°) 구간(19:45에 312.5°, 21:30에 0°)에서 최단 호로 튐 없이. 자정(23:59 → 00:00)은 night 유지 안이라 yaw 0° 그대로, 05:30 뒤 램프에서 0° → 110°(06:30에 55°). 볼류메트릭 안개는 15:15에 켜지고 06:30(램프 중점)에 꺼진다.
  - **설계상 알려진 모습(결함 아님, 14b 항목)**: `IsNight`(lux < 0.1)는 21:24:45~05:34:48. 램프 05:30~06:06은 태양 pitch가 아직 0° 위(지평선 아래에서 비추는 빛, lux ≤ 0.75)이고, 저녁 쪽도 19:13 무렵 pitch 0°에서 lux 약 2.6(지평선 아래에서 비추는 빛). 램프 완화(smoothstep/EV 공간 보간)·night look은 14b look-dev 결정(WP 문서 결과 #15·#18).
- [ ] **night 유지 확인(§2a)**: `golmok.tod rate 10`·`mode clock` 상태에서 `golmok.tod time 21:30` → 2 s 전환 뒤 05:30까지(약 48 s) 화면이 night 그대로 어둡다(점점 밝아지지 않는다). 05:30을 지나면 12 s에 걸쳐 서서히 밝아진다(07:30 overcast_morning). 유지 중 `golmok.tod status`는 그 순간 시각으로 `… alpha 0.00 | night HH:MM hold until 05:30 | current night | night yes | …`.
  - 정확한 줄: `golmok.tod mode fixed` → `golmok.tod time 23:10` → 2 s 뒤 `golmok.tod status` →
    ```
    LogGolmok: golmok.tod: status 23:10 fixed rate 10 min/s | prev night 21:30 next overcast_morning 07:30 alpha 0.00 | night 23:10 hold until 05:30 | current night | night yes | interior off
    ```
    `golmok.tod time 06:00` 뒤 `status`는 `… alpha 0.25 | current night | night no | …`(유지 밖이라 `hold until` 없음, 램프 30/120).
  - 에디터 Python(PIE 중) `import golmok.lighting as l; l.set_time("23:10")` 2 s 뒤 `l.status()` → `{'time': '23:10', 'mode': 'fixed', 'rate': 10.0, 'hold': 'night 23:10 hold until 05:30'}`, Output Log `golmok.lighting: status 23:10 fixed | night 23:10 hold until 05:30`(유지 밖이면 `'hold': None`, 로그 끝 ` | …` 없음).
- [ ] **성능(리뷰 R51-3)**: Clock/Realtime은 매 틱 태양 회전·세기·색온도, SkyLight 세기, 안개, PPV 노출을 다시 쓴다. 움직이는 태양이 매 프레임 돌면 VSM(가상 섀도 맵) 캐시가 매 프레임 무효화되고 Lumen 갱신 비용이 붙으며, 정적 SkyLight는 중점마다 `RecaptureSky()`로 히치가 날 수 있다. 같은 자리·같은 카메라(캐릭터를 세워 두고)에서:
  1. `golmok.tod mode fixed` → `golmok.tod time 15:00` → 5 s 뒤 `stat unit`·`stat gpu`의 Frame·Game·Draw·GPU ms와 `stat gpu`의 Shadow Depths·Lumen 항목을 적는다. `r.Shadow.Virtual.ShowStats 1`이 먹으면 VSM 무효화 페이지 수도 적는다(명령이 없으면 생략하고 메모).
  2. `golmok.tod rate 0.5` → `golmok.tod mode clock`(15:00부터 x0.5) → 10 s 뒤 같은 값을 적는다.
  3. `golmok.tod rate 10`으로 중점(15:15·19:45·06:30·10:00)을 지나는 프레임에 히치(`stat unit` Frame 스파이크; 정적 SkyLight면 `RecaptureSky`)가 있는지 본다. `stat unitgraph`를 켜 두면 스파이크가 보인다.
  - 기록(§11): fixed vs clock x0.5 차이(ms)·VSM 무효화 수·중점 히치 유무. **비용이 크면**(예: GPU +1 ms 이상, VSM 페이지가 매 프레임 대량 무효화, 중점마다 눈에 띄는 히치) 후속은 태양 회전 갱신 **양자화**(회전 변화가 약 0.02°를 넘을 때만 또는 N Hz로 갱신) — 결정은 이 수치 뒤(WP 문서 결과 판단 #19). 지금은 결함이 아니다.
- [ ] 스크린샷(선택): 11:00·16:00·20:30 세 장 `pc-verify-wp14a-clock-*.jpg`.

## 4. 시각 점프 전환

- [ ] `golmok.tod time 18:00` → `LogGolmok: golmok.tod: time HH:MM -> 18:00 (golden_evening) over 2.0 s`, 2 s 보간(clock 모드면 전환 중에도 시계가 계속 가서 전환 끝이 18:00보다 조금 뒤 — 정상).
- [ ] `golmok.tod mode fixed` → `LogGolmok: golmok.tod: mode clock -> fixed at HH:MM`, HUD 시각이 멈춘다. `golmok.tod time 09:00` → 07:30과 12:30의 중간 조명(흐린 아침과 한낮 사이), HUD `tod: overcast_morning 09:00 fixed`.
- [ ] 오류 줄: `golmok.tod time 25:00` → `golmok.tod: ERROR time must be HH:MM (00:00-23:59), got '25:00'`; `golmok.tod mode dusk` → `golmok.tod: ERROR mode must be fixed|clock|realtime, got 'dusk'`; `golmok.tod rate abc` → `golmok.tod: ERROR rate must be a number in (0, 1440] min/s, got 'abc'`; `golmok.tod` → `usage: golmok.tod <preset>|next|list|status|time HH:MM|mode fixed|clock|realtime|rate <min/s>`(Warning).

## 5. Realtime·포토 모드 재동기

- [ ] `golmok.tod mode realtime` → `golmok.tod: mode fixed -> realtime at HH:MM`(PC 시계와 같은 시각), 2 s 전환. HUD `tod: <가장 가까운 키프레임> HH:MM realtime`이 1분마다 1분씩 간다.
- [ ] **P**(포토 모드)로 들어가 1분 넘게 머문다 → 조명·시각이 진입 시각에 머문다(HUD는 포토 오버레이라 `golmok.tod status`로 확인해도 된다). P로 나오면 2 s 전환으로 현재 PC 시각에 맞춰진다.
- [ ] **재동기 규칙(리뷰 R51-6)**: 기본 `PauseMode=GamePause`에서는 포토 모드 동안 게임이 일시정지돼 이 액터가 틱하지 않으므로 포토 모드를 직접 볼 수 없다. 대신 Realtime 틱 사이 **실시간 공백(`UWorld::GetRealTimeSeconds`)이 max(`TransitionSeconds`, 2 s)를 넘으면** 첫 틱에 전환으로 재동기한다(시계와 PC 시각 차가 1분 넘을 때와 같은 전환). 그래서 1분보다 짧게 머물러도 스냅이 아니다: P로 들어가 **약 10 s**만 머물다 나오면 HUD `tod:` 줄이 2 s 동안 `<키프레임> NN%`(전환 중)로 보였다가 PC 시각으로 돌아온다(시각 차가 10 s라 조명 변화는 눈에 거의 안 보인다 — 튀지 않고 전환 표시가 나오는지만 본다). 일시정지·2 s 넘는 히치도 같은 규칙.
- [ ] 포토 모드 `PauseMode=TimeDilation`(ini 선택 키, 커밋하지 않음)으로 한 번 더: 같은 결과.
- [ ] realtime에서 키 **3** → `LogGolmok: TimeOfDay: preset golden_evening in realtime mode -> fixed`, 18:00에 멈춘다(설계상 판단 — WP 문서 결과 #3). 다시 `golmok.tod mode realtime` 뒤 `golmok.tod time 09:00` → `LogGolmok: TimeOfDay: time set in realtime mode -> fixed`, 09:00에 멈춘다.

## 6. F5·키 4개 호환(Fixed 기본)

- [ ] 새 PIE(Fixed 기본). 키 1/2/3/4·F5·`golmok.tod <preset>|next|list`가 V-03(`pc-verify-wp05.md` §3)과 **같은 동작·같은 로그**. 차이는 HUD `tod:` 줄 끝의 ` HH:MM fixed`뿐(예: `tod: night 21:30 fixed`, 전환 중 `tod: clear_noon -> night 45% 21:30 fixed`).
- [ ] **시계 기준 F5(리뷰 R51-4)**: `golmok.tod time 10:01` → HUD `tod: clear_noon 10:01 fixed`(가장 가까운 키프레임 — 10:00 중점을 지남). **F5** → 2 s 뒤 `tod: clear_noon 12:30 fixed`(시간상 다음 키프레임; golden_evening으로 건너뛰지 않는다). `golmok.tod time 23:10` 뒤 F5 → `overcast_morning 07:30`. 키 1~4로 프리셋을 건 뒤의 F5는 종전 그대로(cycle 순서).
- [ ] 실내 왕복(V-03 §5): 실내 진입 → 안개 0·노출 +1, 이탈 → 진입 전 조명으로 복귀. 추가로 `golmok.tod time 09:00` 뒤 왕복 → 이탈하면 09:00 보간 조명으로 돌아온다(overcast_morning으로 튀지 않음).
- [ ] V-09 포토 모드 §4(진입·종료 밝기)가 그대로.

## 7. HUD 줄

- [ ] `tod:` 줄은 노란색 그대로(접두 불변), 형식 `tod: <WP-05 Describe()> HH:MM <fixed|clock xR|realtime>`. 레벨 조명은 `--:--`.

## 8. 오디오 낮/밤(V-10 뒤)

- [ ] WP-13 임포트가 끝난 빌드에서 `golmok.tod mode clock`·`rate 10`: HUD 오디오 줄의 상태가 19:45(night 중점)에 `outdoor_night`, 06:30(night 유지 뒤 램프 중점, §2a)에 `outdoor_day`로 바뀐다(`OnPresetChanged`가 중점에서 1회, Audio 코드 수정 없음). 포토·실내 규칙은 V-10 그대로.

## 9. 선택 ini 키(커밋하지 않음)

`Config/DefaultGame.ini`는 hot-spot이고 `test_ue_wp05_fixture.py`가 `[/Script/Golmok.GolmokTimeOfDay]` 키 집합을 고정한다. 시험할 때만 로컬에서 섹션에 더한다:
```ini
; ClockMode: Fixed | Clock | Realtime. TimeOfDayMinutes = Clock start time (an InitialPreset keyframe wins).
ClockMode=Clock
ClockMinutesPerRealSecond=0.5
RealtimeOffsetMinutes=0
NightLuxThreshold=0.1
TimeOfDayMinutes=450
```
(UE ini에는 줄 끝 주석이 없다 — 주석은 `;`로 시작하는 자기 줄에만.) ini를 바꾼 뒤에는 **에디터를 다시 연다**(클래스 기본 객체가 Config를 시작 때 읽는다).
- [ ] `ClockMode=Clock`으로 PIE → 시작부터 07:30 보간 상태에서 시계가 간다(HUD `clock x0.5`). `ClockMode=Realtime` + `InitialPreset=clear_noon`이어도 Realtime으로 시작한다(설정 모드 우선). 이때 Output Log에 `TimeOfDay: preset clear_noon in realtime mode -> fixed`가 **찍히지 않는다**(InitialPreset은 Fixed로 적용한 뒤 설정 모드 복원, 리뷰 R51-8). 시험 뒤 되돌린다.

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
| 13 | `TimeOfDayMinutes`(float) + 내부 double | 시계는 `PreciseMinutes`(double)로 진행하고 float 프로퍼티에 복사; 밖에서 float을 바꾸면 그 값으로 다시 맞춘다 | — |
| 10 | 정적 SkyLight 재캡처 | Clock/Realtime에서는 키프레임 이름이 바뀔 때(중점)만 `RecaptureSky()`(매 틱 아님). L_Dev가 real-time capture면 해당 없음 | 하늘 앰비언트가 늦게 따라오면 기록(14b 항목) |
| 12 | 에디터 월드의 `golmok.tod` | 에디터 월드(PIE 없음)에서 `time/mode/rate`는 배치된 `AGolmokTimeOfDay`의 Config 프로퍼티를 바꾸고 레벨 저장 시 함께 저장될 수 있다(L_Dev에는 배치 액터가 없어 해당 없음) | 배치 레벨에서는 PIE에서만 쓴다 |
| 11 | 전환 중 시계 진행 | clock 모드의 점프 전환은 매 틱 목표를 현재 시계로 다시 잡는다(`To = ComposeTarget()`) | 전환 끝 튐이 보이면 기록 |
| 14 | `UWorld::GetRealTimeSeconds()`(R51-6) | 5.8에서 `double`, 게임 일시정지 중에도 흐르고 시간 팽창을 받지 않는다 | `FPlatformTime::Seconds()` |

## 11. 결과 기록

| 항목 | 결과 | 메모 |
|---|---|---|
| §1 빌드 | | |
| §2 자동화 3 / 29 | | |
| §3 하루 순환·night 유지(§2a) | | |
| §3 성능 fixed vs clock x0.5·중점 히치(R51-3) | | Frame/GPU ms, VSM 무효화 |
| §4 점프·오류 줄 | | |
| §5 realtime·포토 | | |
| §6 Fixed 호환 | | |
| §7 HUD | | |
| §8 오디오(V-10 뒤) | | |
| §9 ini 선택 | | |
