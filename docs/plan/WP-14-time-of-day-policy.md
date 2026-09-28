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
(세션이 채운다.)
