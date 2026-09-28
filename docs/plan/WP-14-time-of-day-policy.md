# WP-14 — 시간대 폴리시 (D-015 (a)): 14a 연속 시각·시계 모드(클라우드) / 14b 밤 look-dev(PC, D-010 뒤)

상태: 🔵 **14a 진행 중**(2026-09-28 설계 확정, 오케스트레이터 결정 D-019) · 담당: 14a **Opus 5.5 ultracode**(설계 Fable 5.1, 검증 Opus), 14b PC 세션 + 소유자 채점 · PC 검증 번호 **V-13**(14a).

## 목표
"같은 골목이 다르게 보인다"(DEVELOPMENT-PLAN §1.2 경험 3)의 시간대 부분. 지금은 프리셋 4개를 키 4개·F5로만 바꾼다(WP-05). 14a는 프리셋 사이를 잇는 **연속 시각(하루 1440분)**과 **시계 모드(fixed/clock/realtime)**를 넣어 어느 시각에서든 조명이 이웃 프리셋 둘의 보간으로 정해지게 하고, 포토 모드 시간대 슬라이더(Phase 2, D-013 확장)·세이브(WP-15, D-017)·환경음 낮/밤(WP-13)·가로등 발광(Zone 에셋)이 **같은 시계**를 쓰게 한다. 14b는 night 프리셋 값(look-dev, [`design/lighting-night-lookdev.md`](../design/lighting-night-lookdev.md))과 발광 에셋 연동 — D-010 뒤 PC.

## 분할 근거 (오케스트레이터 결정, D-019, 2026-09-28)
D-015가 WP-14를 D-010 뒤로 미룬 이유는 밤 look-dev가 환경 표현 방식(메시/splat)에 좌우되기 때문이다. 시계·보간·모드·저장 표현은 표현 방식과 무관하고 프리셋 값을 바꾸지 않으므로 지금 할 수 있다. 소유자가 뒤집으면 14a 브랜치를 닫는다(되돌릴 수 있음).

## 배경(코드에서 확인할 것)
- `Lighting/GolmokTimeOfDay`: 프리셋 JSON(`Config/Golmok/lighting_presets.json`, `schema_version` 1, `cycle` 정확히 4개, cycle 프리셋은 9키 완비) 단일 소스. API `ApplyPreset(Name, bInstant)`·`NextPreset()`·`EnterInterior/ExitInterior(Source)`·`IsInterior()`·`FindPreset`·`CaptureState`·`IsTransitioning`·`GetTransitionAlpha`·`ShiftTransitionStart`·정적 `Lerp(A, B, Alpha)`·`TransitionSeconds`(Config). 델리게이트 `OnPresetChanged(FName, bool)`·`OnInteriorChanged(bool)`(D-019 결정, WP-13이 구독). 콘솔 `golmok.tod <preset>|next|list`는 같은 파일. 에디터 Python `golmok/lighting.py`(`presets/cycle/reload/list_presets/apply`), pytest `tools/tests/test_lighting_presets.py`·`test_ue_python_lighting.py`, UE 자동화 `Golmok.Lighting.PresetsFile`·`Golmok.Lighting.PresetApply`(`Tests/GolmokLightingTest.cpp`).
- 소비자: WP-12 포토 모드(`GetTimeOfDay()`로 노출 바이어스·HUD), WP-13 오디오(`OnPresetChanged` 프리셋 이름 → 낮/밤), HUD `tod:` 줄(`Debug/GolmokHUD.cpp`; Astra 오디오 훅 블록이 같은 파일에 있을 수 있다 — 훅 블록은 건드리지 않는다).
- night 프리셋은 현재 빛 0(태양 pitch +15·lux 0·sky 0.15 → 화면 검정, V-03). **14a는 프리셋 값을 바꾸지 않는다.**

## 설계 (확정, 2026-09-28, Fable)

### 1. 시각 표현
- `float TimeOfDayMinutes` ∈ [0, 1440). 콘솔·HUD·저장은 `HH:MM`. 순수 헤더 `Lighting/GolmokClockMath.h`(엔진 헤더 없이 컴파일): `WrapMinutes`, `ParseHHMM`/`FormatHHMM`, `FindKeyframes(t, times[])` → 이전/다음 키프레임 인덱스와 alpha(자정 넘김: 마지막→첫째 구간, 시간 폭 = 1440 − last + first), `LerpYawShortest(a, b, alpha)`, 선형 `Lerp`. WP-13 `GolmokAudioMath.h`처럼 g++ 교차검증 pytest 표를 둔다.

### 2. 키프레임 = cycle 프리셋 + `time`
- JSON `schema_version` **2**: cycle에 든 프리셋마다 `"time": "HH:MM"` 필수, cycle 순서 = 시각 증가 순(파서가 중복·역순·형식 오류를 `Error`로). interior 프리셋엔 `time` 없음(있으면 오류). 기본값: `overcast_morning` 07:30, `clear_noon` 12:30, `golden_evening` 18:00, `night` 21:30. schema 1 파일은 오류(단일 소스 규칙: 파일·파서·`lighting.py`·pytest 스키마·런북 기대 로그를 한 PR에서 함께 올린다).

### 3. 보간
- 시각 t의 목표 상태 = `Lerp(prev, next, alpha)`(기존 정적 함수 재사용). 단 sun yaw는 최단 호, pitch·lux·kelvin·sky·fog·fog_height_falloff·exposure_bias는 선형, `volumetric`은 alpha < 0.5면 prev 아니면 next. 태양 가시성은 전환 끝에서만이 아니라 **매 틱** `lux > 0.01`로 정한다(night 구간에서 태양이 켜졌다 꺼졌다 하지 않게). 이 규칙은 `GolmokClockMath.h`에 두고 pytest 표로 고정한다.
- 명시적 점프(`SetTimeOfDay`, `ApplyPreset`, 모드 전환, 포토 모드 종료 재동기)는 기존 `TransitionSeconds` 전환을 쓴다. 시계 진행(Clock/Realtime)은 매 틱 목표 상태를 바로 적용한다(전환 없음, `bTransitioning` false).
- 실내 오버레이(WP-05)는 그대로 위에 덮는다. `ExitInterior`는 "이전 프리셋 이름"이 아니라 **현재 시각의 보간 상태**로 복귀한다(Fixed 모드에서는 결과가 종전과 같다).

### 4. 시계 모드
- `enum class EGolmokClockMode : uint8 { Fixed, Clock, Realtime }`. 기본 **Fixed** = 종전 동작과 바이트 동일: 시계는 멈춰 있고 `ApplyPreset(Name)`은 시각을 그 키프레임의 `time`으로 맞춘 뒤 종전처럼 전환한다(`NextPreset`도 같다). 기존 런북(V-03·V-09·V-10)이 그대로 성립해야 한다.
- **Clock**: `ClockMinutesPerRealSecond`(Config, 기본 0.5 → 하루 48분) × 월드 델타(`DeltaSeconds`, 일시정지·포토 모드 정지면 자연히 멈춤)만큼 진행, 1440에서 wrap.
- **Realtime**: `FDateTime::Now()`(PC 로컬 시각, 시간대 변환 없음 — 소유자 PC = KST) + `RealtimeOffsetMinutes`(Config, 기본 0)을 매 틱 목표 시각으로. 포토 모드 진입 중에는 진입 시각을 유지하고, 종료·모드 전환 시 `TransitionSeconds` 전환으로 재동기.
- 모드·배율·오프셋·night 임계는 `UPROPERTY(Config)` **코드 기본값**으로만 둔다(`Config/Default*.ini`는 hot-spot: 변경하지 않고, 런북에 선택 키만 적는다).

### 5. 이벤트 계약(소비자 호환)
- `CurrentPreset`은 항상 **가장 가까운 키프레임 이름**(자정 넘김 포함). `OnPresetChanged(FName, bool)`은 Clock/Realtime에서 t가 두 키프레임의 **중점**을 지날 때 새 이름으로 1회 발화(bool은 종전 의미 유지). 이로써 WP-13 오디오의 이름→낮/밤 매핑은 수정 없이 동작한다. Fixed 모드의 발화 시점은 종전과 같다.
- 새 `OnNightChanged(bool)`와 `IsNight()`: 보간 상태 `lux < NightLuxThreshold`(Config, 기본 0.1). 14b 발광 에셋과 오디오가 선택적으로 쓴다. 지금 소비자는 없어도 된다.
- 포토 모드(WP-12): UI 없음. `GetTimeOfDayMinutes()`/`SetTimeOfDay(Minutes, bInstant)`/`GetClockMode()`만 노출(Phase 2 슬라이더·WP-15 저장용). 포토 모드 코드는 고치지 않는다(필요하면 훅 블록).

### 6. 콘솔·HUD·에디터
- `golmok.tod <preset>|next|list`(유지) + `golmok.tod time HH:MM` + `golmok.tod mode fixed|clock|realtime` + `golmok.tod rate <min/s>` + `golmok.tod status`(시각·모드·배율·현재/다음 키프레임·alpha·night). 등록부(`CONSOLE_COMMANDS`)는 한 명령이라 변경 없음; 사용법 문자열만 갱신.
- HUD `tod:` 줄: 기존 내용 뒤에 ` HH:MM mode[×rate]`를 덧붙인다(기존 파서·테스트가 `tod:` 접두를 보므로 접두는 그대로).
- `lighting.py`: `set_time("HH:MM")`, `mode(name=None)`(조회/설정), `status()`; `apply` 유지. 가짜 unreal(`tests/fake_unreal.py`)에 콘솔 호출 기록만 추가.

### 7. 테스트·문서
- pytest: `test_lighting_presets.py`(schema 2, `time` 형식·단조 증가·interior 금지, 기본 4개 값), `GolmokClockMath.h` g++ 교차검증 표(자정 넘김·최단 호(350°→10°)·alpha 경계 0/1·HH:MM 파싱 실패), `test_ue_python_lighting.py`(새 함수).
- UE 자동화(`-nullrhi`) **`Golmok.Lighting.Clock`** 1개 추가(등록 28 → 29; `tools/tests/test_ue_wp09_fixture.py`의 등록부 갱신은 hot-spot 규칙대로 `# [WP-14 hook]` 줄): 키프레임 시각에서 상태 == 프리셋, 중간 시각 보간값(계산식 대조), 자정 넘김, 모드 전환·`rate`, 중점 통과 시 `OnPresetChanged` 정확히 1회·`OnNightChanged`, `ApplyPreset`이 시각을 키프레임으로, Fixed 모드에서 기존 `PresetApply` 시나리오 결과 동일, 실내 진입/이탈 뒤 시각 상태 복귀.
- 런북 `docs/runbooks/pc-verify-wp14a.md`(**V-13**): 빌드 → 자동화 29 → PIE `golmok.tod mode clock`·`rate 10`으로 하루 순환 관찰(night 구간이 어둡거나 검정인 것은 14b 전 정상), `time` 점프 전환, `realtime`·포토 모드 진입/종료 재동기, F5·키 4개 호환, HUD 줄, 오디오 낮/밤 전환 유지(V-10 뒤). 불확실 API 표.

### 8. 하지 않는 것
night 프리셋 값·look-dev(14b), 가로등·간판 발광 에셋(14b, Zone 제작), 날씨(WP-16), 포토 슬라이더 UI(Phase 2), 저장 파일(WP-15 — 14a는 조회/설정 API만), 시간대(TZ) 변환, 프리셋 개수 변경(cycle 4 고정 유지).

## 산출물 (`unreal/Golmok/Source/Golmok/Lighting/`, `Config/Golmok/lighting_presets.json`, `Content/Python/golmok/lighting.py`, `tools/tests/`, `docs/`)
1. `GolmokClockMath.h` + g++ 교차검증 pytest. 2. `GolmokTimeOfDay` 확장(시각·모드·보간 틱·이벤트·콘솔·HUD 줄). 3. `lighting_presets.json` schema 2(`time` 4개). 4. `lighting.py`·pytest. 5. UE 자동화 `Golmok.Lighting.Clock`. 6. 런북 `pc-verify-wp14a.md`(V-13). 7. 이 문서 "결과" 절 + STATUS/ROADMAP "병합 시 반영" 문안.

## 완료 기준
클라우드: 위 산출물 전부, **Fixed 모드가 종전과 동일**(기존 자동화·런북 무수정 통과), pytest·ruff·check_repo·CI 초록, 적대적 검증 1라운드 반영 → 🟡 코드 완료·PC V-13 대기. PC: V-13 통과 → 14a 🟢. 14b는 D-010 뒤 별도 세션(PC look-dev + 소유자 채점).

## 주의
- hot-spot(DEVELOPMENT-PLAN §7.6) 훅 규칙: `Default*.ini`·등록부 테스트는 훅 줄만, `GolmokHUD.cpp`의 Astra 오디오 훅 블록 보존. Astra 레인(`Audio/`, `Characters/`)은 고치지 않는다(오디오 호환은 §5 계약으로).
- 프리셋 JSON 단일 소스(WP-05 규칙): 파일·파서·Python·테스트·런북 기대 로그를 한 PR에서. 5.8 주의(WP-12 참조), Windows CI 주의 동일.
- 세션 운영: Opus ultracode(구현 → 적대적 검증 최대 1라운드), Workflow 2시간 상한, 브랜치 `claude/hopeful-allen-f0a0jb`, PR은 draft, 병합은 오케스트레이터.

## 결과

### 14a (2026-09-28, 세션 session_01S3bDop479NqGLXdV66Ky1L, Opus ultracode) — 🟡 코드 완료·PC V-13 대기

**구현 요약**(스펙 §1~§8 대응)

| 스펙 | 구현 |
|---|---|
| §1 시각 표현 | `Lighting/GolmokClockMath.h`(엔진 헤더 없음, `<cmath>`만): `WrapMinutes`·`CircularDistance`·`ParseHHMM<CharT>`/`FormatHHMM<CharT>`(char·wchar_t·TCHAR)·`Advance`·`IsValidRate`·`FindKeyframes`(자정 넘김 폭 = 1440 − last + first, 키프레임 시각에서 alpha 0)·`LerpYawShortest`·`Interpolate`·`IsSunVisible`·`IsNight`·`CheckKeyframeOrder`. g++ 교차검증 `tools/tests/test_ue_clock_math.py`(+ `fixtures/ue/clockmath_driver.cpp`, `-Wall -Wextra -Wshadow -Werror -pedantic`): 표(자정 넘김·350°→10°·alpha 0/0.5/1·HH:MM 실패 10종) + Python 참조 구현 대조 무작위 900건 |
| §2 키프레임 | `lighting_presets.json` schema 2, `time` 07:30/12:30/18:00/21:30(조명 값 불변 — pytest가 WP-04 값과 대조). C++ `ParsePresetsText`·Python `parse_presets` 같은 규칙: cycle `time` 필수·형식·중복·역순·cycle 밖 `time` 금지·schema 1 오류 |
| §3 보간 | `AGolmokTimeOfDay::EvaluateClock` = `GolmokClockMath::Interpolate`(yaw 최단 호, 나머지 선형, volumetric alpha<0.5 → prev). 시계 틱은 `ApplyClockState`(전환 없이 즉시, 태양 가시성 매 틱 lux > 0.01, volumetric 바뀔 때만 토글). 명시적 점프(`SetTimeOfDay`·`ApplyPreset`·모드 전환·Realtime 재동기)는 `TransitionSeconds` 전환. 실내 오버레이는 그 위에(`ComposeTarget` = `ComposeBase` + overlay), `ExitInterior`는 현재 시각의 보간 상태로 |
| §4 시계 모드 | `EGolmokClockMode { Fixed, Clock, Realtime }`(UENUM), Config 코드 기본값 `ClockMode` Fixed·`ClockMinutesPerRealSecond` 0.5·`RealtimeOffsetMinutes` 0·`NightLuxThreshold` 0.1·`TimeOfDayMinutes` 450 — ini 변경 없음. Clock = rate × 월드 `DeltaSeconds`(일시정지면 틱 없음, 포토 TimeDilation이면 ≈0). Realtime = `FDateTime::Now()` + offset, 포토 모드 중 유지(`UGolmokPhotoModeSubsystem::IsActiveIn`), 종료 뒤 첫 틱에 전환으로 재동기 |
| §5 이벤트 | `CurrentPreset` = 가장 가까운 키프레임. `OnPresetChanged`: Clock/Realtime 틱에서 중점 통과 시 1회(`bInstant` false), `SetTimeOfDay`는 이름이 바뀔 때만(인자 `bInstant`), `ApplyPreset`은 WP-05 그대로 무조건. 새 `OnNightChanged(bool)`·`IsNight()`(기본 상태 lux < 임계). `GetTimeOfDayMinutes/SetTimeOfDay/GetClockMode/SetClockMode` 공개(BlueprintCallable) |
| §6 콘솔·HUD·에디터 | `golmok.tod time HH:MM | mode fixed|clock|realtime | rate <min/s> | status`(기존 `<preset>|next|list` 유지, 명령 등록 1개 그대로). HUD `tod:` 뒤 `DescribeClock()` = ` HH:MM fixed` / ` HH:MM clock x10` / ` HH:MM realtime`(레벨 조명 `--:--`). `lighting.py` `set_time`·`mode(name=None)`·`status()`, `fake_unreal`에 `tod_commands` 기록 |
| §7 테스트·문서 | UE 자동화 `Golmok.Lighting.Clock`(28 → 29): 키프레임 = 프리셋 4개, 09:00 보간(식 대조), 00:30·23:00 자정 넘김, 19:45 최단 호·volumetric, `ApplyPreset`/`NextPreset` 시각, Clock 중점 통과 `OnPresetChanged` 정확히 1회·`bInstant` false, `OnNightChanged` true/false, 태양 lux 0.0019 숨김, rate 10 자정 wrap, Realtime 전환, 실제 틱 rate 60 진행, Fixed 정지·틱 off, Fixed `PresetApply` 시퀀스 값, 09:00 실내 진입/이탈 복귀. `Golmok.Lighting.PresetsFile` schema 2 반영(time 오류 5종). 런북 [`runbooks/pc-verify-wp14a.md`](../runbooks/pc-verify-wp14a.md)(V-13) |
| §8 하지 않는 것 | 프리셋 값·night look-dev·발광·날씨·포토 슬라이더·저장·TZ 변환·cycle 개수 — 손대지 않음. Audio/·Characters/·Photo/ 수정 없음 |

**설계상 판단**(스펙 빈틈 — Fixed 종전 동일·프리셋 값 불변·JSON 단일 소스 쪽으로 최소 판단)
1. **Fixed의 기본 상태 두 갈래**: `ApplyPreset`/`NextPreset`(Fixed)는 종전처럼 프리셋 값 그대로(`bBaseFromClock` false — WP-05와 같은 코드 경로), `SetTimeOfDay`(Fixed)는 그 시각의 보간 상태를 보이고 시계는 멈춘 채. 키프레임 시각의 보간값은 프리셋 값과 비트 단위로 같다(alpha 0; pytest·자동화가 확인).
2. `TimeOfDayMinutes`도 `UPROPERTY(Config)`(지시 "전부 Config"): Clock 시작 시각(InitialPreset이 있으면 그 키프레임이 우선). 기본 450(07:30, 첫 키프레임).
3. **Realtime에서 `ApplyPreset`(키 1–4·F5·콘솔 프리셋) → Fixed로 전환**: 그대로 두면 다음 틱 재동기가 곧바로 현재 시각으로 되돌린다. Clock에서는 그 키프레임에서 계속 흐른다. `time` 없는 프리셋(`interior`를 기본으로 거는 콘솔 사용)도 Clock/Realtime이면 Fixed로. 로그 `TimeOfDay: preset <name> in <mode> mode -> fixed`.
4. **Realtime 재동기 규칙**: 포토 모드 중(`IsActiveIn`) 유지 → 끝나면 전환. `GamePause` 포토 모드는 액터 틱이 멈춰 감지되지 않으므로 "시계와 로컬 시각 차가 1분(`GolmokClockMath::ResyncMinutes`) 넘으면 전환으로 재동기"를 함께 둔다(일시정지·히치에도 같은 규칙).
5. Clock/Realtime에서 점프 전환 중에는 목표를 매 틱 현재 시계 상태로 다시 잡는다(전환 끝에 시계가 흐른 만큼 튀지 않게).
6. 정적 SkyLight 재캡처는 시계 틱마다가 아니라 가장 가까운 키프레임이 바뀔 때만(비용). L_Dev가 real-time capture면 해당 없음.
7. `IsNight`는 실내 오버레이를 뺀 기본 상태 lux로 판단(오버레이는 lux를 안 바꾼다). `OnNightChanged`는 명시적 점프·`ApplyPreset`에서도 바뀌면 발화한다. BeginPlay 끝의 판정은 발화하지 않는다(`InitialPreset` 적용은 `ApplyPreset` 경로라 바뀌면 발화하지만 구독자가 붙기 전이다).
8. HUD 배율 표기는 ASCII `x`(`×`는 `TEXT()` 소스 인코딩·HUD 폰트 위험). `rate` 범위 (0, 1440] min/s.
9. `time` 금지 범위를 interior뿐 아니라 cycle 밖 프리셋 전체로(현재는 interior 하나라 같은 결과).
10. Python `parse_presets`는 `time`을 프리셋 dict에 그대로 둔다(`apply()`는 무시, `is_partial`은 `time`을 빼고 판단). `keyframes(cycle, presets)` 추가.
11. 등록부(`test_ue_wp09_fixture.py` `CONSOLE_COMMANDS`)는 새 명령이 없어 **변경 없음**(`# [WP-14 hook]` 줄 불필요). 자동화 총수 고정 테스트(`test_ue_wp12_fixture.py`)가 `pc-verify-wp12.md` "두 번째 명령" 줄을 보므로 그 줄만 28 → 29로 고쳤다.
12. 포토 모드 감지를 위해 `GolmokTimeOfDay.cpp`가 `Photo/GolmokPhotoModeSubsystem.h`를 include(읽기만, Photo 코드 수정 없음). HUD 줄은 `Debug/GolmokDebugSubsystem.cpp` `BuildLightingLine` 한 줄(Fable 레인, hot-spot 아님; `GolmokHUD.cpp`·Astra 훅 블록은 그대로).
13. `lighting.py` `mode()`/`status()`의 조회는 월드의 `GolmokTimeOfDay` 액터 프로퍼티(`clock_mode` 등)를 읽고, 없으면 `None`(콘솔 `status` 줄은 항상 로그). 콘솔은 PIE 월드 우선, 없으면 에디터 월드.
14. 기존 V-03 런북의 HUD 기대 줄(`tod: overcast_morning` 등)은 스펙 §6대로 뒤에 ` HH:MM fixed`가 붙는다 — 접두·앞부분·로그는 그대로(런북 V-13 §6에 명시).
15. **night 구간이 짧다(설계 그대로, 14b 결정 항목)**: 키프레임 4개 선형 보간이라 night(21:30, lux 0) → overcast_morning(07:30) 600분 구간에서 lux가 곧바로 올라 `IsNight`(lux < 0.1)는 21:24:45~21:54만 참이고, 태양 pitch가 00:30에 0°를 지나 새벽에 약한 태양이 보인다. 스펙 §3(선형 보간)·§5(`IsNight` = lux < 임계)·프리셋 값 불변을 지키면 이렇게 되므로 14a에서는 바꾸지 않았다. 14b look-dev에서 정할 것: 밤 유지 키프레임(예: `night_late` 02:00) 추가 또는 cycle 4 고정 해제, 구간 완화(smoothstep·EV 공간 보간), `IsNight` 정의(가장 가까운 키프레임 = night 등). WP-13 오디오는 이름 매핑이라 19:45~02:30이 밤으로 영향 없음. 런북 V-13 §3에 "결함 아님"으로 명시.
16. Realtime에서 `SetTimeOfDay`(콘솔 `time` 포함)도 `ApplyPreset`처럼 Fixed로 전환(다음 틱 재동기가 되돌리고 `OnPresetChanged`가 두 번 나는 것을 막음; 로그 `TimeOfDay: time set in realtime mode -> fixed`). 시계 자신의 점프(모드 전환·재동기·BeginPlay)는 내부 `JumpTo`로 이 전환을 거치지 않는다.
17. 시계 정밀도: `TimeOfDayMinutes`(float, Config) 옆에 내부 `PreciseMinutes`(double)로 진행(느린 배율·높은 fps에서 float 스텝이 사라지거나 튀는 것 방지). 밖에서 float을 바꾸면 그 값으로 다시 맞춘다.

**적대 검증**(별도 에이전트 1라운드)

검증 대상 3943e4a(+ 런북). 에이전트는 파일을 고치지 않고 pytest 957 통과·g++ 드라이버·`Golmok.Lighting.Clock` 단언을 수치로 추적했다. **Fixed 모드 종전 동일 확인**(ApplyPreset/NextPreset/실내/전환/틱/가시성/Describe/콘솔 프리셋 경로·PresetApply 무수정 통과), blocker 없음. 반영 커밋: 이 절 다음 커밋.

| # | 심각도 | 지적 | 조치 |
|---|---|---|---|
| 1 | major(설계) | night 구간이 약 29분, 00:30 이후 지평선 위 약한 태양(4 키프레임 선형 보간의 결과) | 스펙 설계·프리셋 값 불변 그대로 — 판단 #15로 14b 결정 항목, 런북 §3에 "결함 아님" 명시 |
| 2 | minor | float 시계가 느린 배율·높은 fps에서 멈추거나 튐 | 수정: 내부 double `PreciseMinutes`(판단 #17), 자동화에 rate 1/60·240 fps 10 s 단언 추가 |
| 3 | minor | `ClockMode=Realtime` + `InitialPreset`이면 BeginPlay에서 Fixed로 끝남 | 수정: 설정 모드를 ApplyPreset 전에 저장해 우선 |
| 4 | minor | Realtime에서 `SetTimeOfDay`가 다음 틱에 되돌려지고 이벤트 2회 | 수정: Fixed로 전환(판단 #16), 내부 점프는 `JumpTo`; 자동화 단언 추가 |
| 5 | minor | Python `HH:MM` 정규식이 끝 개행 허용(C++와 불일치) | 수정: `fullmatch` + pytest(개행·공백 4종, JSON `12:30\n`) |
| 6 | minor | 시계 기본 상태의 전환 끝 가시성이 lux > 0(시계 규칙 0.01과 다름, 한 프레임 두 번 토글) | 수정: `bBaseFromClock`이면 `IsSunVisible`(전환 시작·끝 모두); 프리셋 기본은 WP-05 그대로 |
| 7 | nit | 런북 §3 자정 yaw 서술 오류·volumetric 꺼짐(02:30) 누락 | 수정 |
| 8 | nit | 런북 §9 ini 줄 끝 `;` 주석·에디터 재시작 누락 | 수정 |
| 9 | nit | 에디터 월드에서 `golmok.tod` 하위 명령이 배치 액터 Config 값을 바꿔 레벨에 저장될 수 있음 | 런북 §10 #12에 기록(L_Dev 해당 없음) |
| 10 | nit | 초대형 스텝(배율 1440·히치)에서 틱당 이벤트 최대 1회 | 최종 이름은 맞음 — 조치 없음 |
| 11 | nit | 포토 모드 중 `SetClockMode(Realtime)`은 즉시 점프 | 명시적 조작이라 그대로 |
| 12 | nit | HUD `x` 표기 | 판단 #8(의도) |

**게이트**: ruff check·format, pytest, check_repo, `git diff --check` — PR 본문에 수치.

**병합 시 반영**(오케스트레이터)
- STATUS WP-14a 행: `🟡 코드 완료·PC V-13 대기(PR #<번호>, 2026-09-28): GolmokClockMath·연속 시각·fixed/clock/realtime·schema 2 time·OnPresetChanged 중점 발화·OnNightChanged·golmok.tod time/mode/rate/status·HUD 시각·자동화 29(Golmok.Lighting.Clock), Fixed 종전 동일·프리셋 값 불변, 런북 pc-verify-wp14a.md`
- ROADMAP 1.3 조명 프리셋 행 끝: `WP-14a 연속 시각·시계 모드(fixed/clock/realtime, 키프레임 time 보간) 🟡 코드 완료·PC V-13 대기(2026-09-28) — night look-dev·발광은 14b(D-010 뒤)`
- ROADMAP 1.6: "시간대 폴리시(WP-14)는 D-010 뒤." → `시간대 폴리시 WP-14a(연속 시각·시계 모드) 🟡 PC V-13 대기, 14b(night look-dev·발광 에셋)는 D-010 뒤.`

