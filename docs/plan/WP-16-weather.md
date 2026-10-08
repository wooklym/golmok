# WP-16 — 날씨(비) (D-015 (b)): 16a 상태·조명 수정자·빗줄기·계약(클라우드) / 16b 젖은 표면·look-dev(PC, D-010 뒤)

상태: **16a 설계 확정 2026-10-04 (Opus, D-019)** — 구현 🟡 코드 완료·PC 검증 대기(V-16 카드 발행 2026-10-04 — PC 대기; [#112](https://github.com/wooklym/golmok/pull/112) 병합 2026-10-04, R112 (C) 후속 [#113](https://github.com/wooklym/golmok/pull/113) 병합, 아래 "결과") · 16b ⚪ D-010 뒤 · 담당: 16a **Opus 5.5 ultracode**(Claude 레인), 빗소리 소비는 **ChatGPT Astra** 오디오 레인(T24 [#114](https://github.com/wooklym/golmok/pull/114) 병합, 후속 T25~T29; PC 확인 V-18), 16b PC 세션 + 소유자 채점 · PC 검증 **V-16**(런북 `runbooks/pc-verify-wp16a.md`; 메모의 V-15는 WP-19가 썼다). 설계 확정은 오케스트레이터 결정(D-019)이고 소유자가 뒤집을 수 있다(뒤집으면 16a 병합을 되돌린다).

## 목표
"같은 골목이 아침·밤·**비**에 다르게 보인다"(DEVELOPMENT-PLAN §1.2 경험 3, D-015 (b)). 16a는 환경 표현 방식(D-010)과 무관한 날씨의 뼈대 — 상태 머신, 시간대 위의 조명 수정자, 빗줄기 파티클, 16b·오디오가 붙을 계약(MPC·이벤트), 세이브, 콘솔·HUD — 를 만든다. **기본 날씨는 clear(수정자 항등)라 기존 화면·자동화·런북은 바이트 단위로 그대로다.** 젖은 표면·웅덩이·반사·빗줄기 룩과 수정자 값 확정은 16b(D-010 뒤 PC look-dev)다.

> 아래 §1~§4는 2026-09-29 분할 검토 메모 원문(이력)이다. 메모 당시 상태: "⚪ 검토 메모(착수 아님). D-015 (b)는 'Phase 2 중반, D-010 뒤'로 승인됐다. 이 메모는 WP-14/WP-15와 같은 방식으로 D-010(환경 표현 방식)과 무관한 부분을 16a로 떼어 낼 수 있는지를 검토하고, 떼어 낼 때의 설계 골격과 착수 조건을 적는다. 실제 '설계 (확정)'은 착수 세션 전에 Fable이 별도로 확정한다." 착수 조건(V-13·V-14 🟢, 2026-10-04)이 충족돼 §2 골격은 아래 **"16a 설계 (확정)"**이 대체한다(D-020에 따라 확정은 Opus). 바뀐 점은 확정 절 §0-2 표.

## 1. 결론(오케스트레이터 검토, D-019 — 소유자가 뒤집을 수 있음)
- **분할 가능.** 비의 구성 요소 중 *표면 젖음*(러프니스·웅덩이·반사)만 D-010에 묶여 있고, 나머지(날씨 상태·조명 수정자·빗줄기·소리·저장·콘솔/HUD)는 메시든 splat이든 같다.
- **16a(표현 무관, 클라우드 Opus ultracode 가능)**: 날씨 상태 머신 + JSON 날씨 프리셋(조명 수정자) + 빗줄기 파티클 + 젖음 파라미터 **계약**(값만 공급) + 오디오 이벤트 훅 + 세이브 필드 + 콘솔/HUD + 자동화.
- **16b(D-010 뒤, PC look-dev)**: 젖은 표면 머티리얼 레이어(메시일 때)·웅덩이·반사 튜닝·빗줄기 룩·성능 예산 확정. splat이면 젖음 표현은 파티클·조명·소리로 제한된다는 것을 스크린샷으로 확인해 D-015 (b) 범위를 다시 정한다.
- **착수 시점**: 16a는 V-13(WP-14a)·V-14(WP-15a) PC 검증이 끝나 시간대·세이브 계약이 안정된 뒤, 클라우드 여유가 있을 때. 지금은 착수하지 않는다(Phase 1 품질 게이트 D-010·V-08·V-12가 소유자·PC에 걸려 있고, 그 사이 클라우드 후보로 남겨 둔다).

## 2. 16a 설계 골격(초안 — 확정 아님)
1. **상태**: `EGolmokWeather { Clear, Overcast, Rain }` + `RainIntensity 0..1`. 모드는 WP-14a와 같은 형식으로 `fixed`(콘솔/ini 고정)·`scripted`(JSON 시퀀스 재생, 시연용)만 두고, 무작위/실시간 기상 연동은 하지 않는다.
2. **JSON 단일 소스** `Config/Golmok/weather_presets.json`(schema 1): 날씨별 *조명 수정자* — `lighting_presets.json`의 키(`lux`·`sky`·`fog`·`fog_height_falloff`·`kelvin`·`exposure_bias`·`volumetric`)에 곱셈/가산 계수를 적용한다. 시간대 프리셋 값은 바꾸지 않는다(WP-05 규칙 유지). 수정자는 `GolmokTimeOfDay`의 평가 결과 뒤에 한 단계로 끼운다(`ApplyState` 직전, 보간·hold와 독립). Python `lighting_presets.py`와 같은 파서 규칙(schema·타입·범위·미지 키 오류).
3. **빗줄기**: Niagara 시스템 1개(카메라 추종 박스 이미터, 강도 = `RainIntensity`). 프로젝트에 Niagara 플러그인이 아직 없다(uproject `Plugins`: EnhancedInput·PythonScriptPlugin·EditorScriptingUtilities·AndroidFileServer) — 플러그인 활성화는 `Golmok.uproject`·`Build.cs` 변경이라 착수 세션이 별도 커밋으로 하고, 에셋은 에디터 Python으로 생성 가능한 최소 구성(스프라이트·중력·수명)만 둔다. 카메라 근처 빗방울 화면 효과는 16b.
4. **젖음 계약**: `UMaterialParameterCollection` `MPC_GolmokWeather`에 `Wetness`·`RainIntensity`(0..1)·`PuddleLevel`. 16a는 값만 쓴다. 16b가 메시 머티리얼(`M_ZoneScan*`)에 바인딩한다. splat 표현이면 바인딩 대상이 없고 값은 무시된다 — 계약은 그대로 둔다.
5. **이벤트 계약(WP-13 오디오 레인용)**: `AGolmokTimeOfDay`와 같은 방식의 네이티브 멀티캐스트 `OnWeatherChanged(EGolmokWeather, float Intensity)`를 `Weather/GolmokWeatherSubsystem`(월드 서브시스템)에 둔다. Audio 레인은 `outdoor_rain` 상태(빗소리 베드, 실내 우선 규칙 그대로)와 발소리 세트 `wet`(선택)을 이벤트로 붙인다 — Audio 코드는 Astra 레인이므로 계약만 정하고 구현은 Astra 과제로 배정한다.
6. **세이브**: WP-15a `FGolmokSaveTimeOfDay`와 나란히 `FGolmokSaveWeather { uint8 State; float Intensity; }`를 추가(`SaveSchemaVersion` 유지, 필드 추가만; 구 세이브는 Clear).
7. **콘솔·HUD**: `golmok.weather clear|overcast|rain [intensity]|status`, HUD `weather:` 줄(Debug 훅 블록). 포토 모드 중 상태 변경은 허용하되 파티클은 정지 시간 규칙을 따른다(WP-12 GamePause).
8. **테스트**: 순수 헤더 `Weather/GolmokWeatherMath.h`(수정자 적용·강도 램프) g++ 교차검증, UE 자동화 `Golmok.Weather.Modifiers`(시간대 4종 × 날씨 3종 값 검사)·`Golmok.Weather.Events`(이벤트 1회·세이브 왕복) → 총수 +2.
9. **하지 않는 것(16a)**: 젖은 표면·웅덩이·반사, 눈, 실시간 기상 API, 바람/천둥, 날씨 전환 연출(페이드는 조명 수정자 보간 2 s로 갈음).

## 3. 의존·리스크(메모)
- **D-010**: 16b 전체. 16a는 무관.
- **R5(흐린 날 촬영 텍스처)**: Rain·Overcast는 흐린 촬영 텍스처와 잘 맞고, Clear 강한 태양이 오히려 부자연스럽다는 것이 D-015 리스크였다. 16a의 조명 수정자는 이 방향(흐림/비가 기본, 맑음은 약하게)으로 잡는다.
- **성능**: 볼류메트릭 안개 + 빗줄기 + (16b) 반사가 RTX 5060 1080p 30 fps 하한에 부담 — 16a 런북에 `stat gpu` fixed vs rain 비교 단계를 넣고, 16b에서 Lumen Lite(5.8 Beta) 채택 여부를 별도 결정.
- **레인**: `Weather/`는 새 Claude 레인, Audio 훅 구현은 Astra 레인(과제 배정), `Lighting/` 수정은 수정자 삽입 지점 한 곳(훅 블록 아님, Claude 레인).

## 4. 다음 단계
- 16a 착수 결정 시: 이 메모 §2를 "설계 (확정)"으로 승격(Fable), DEVELOPMENT-PLAN §5.1 행·STATUS 행 추가, Opus ultracode 세션 카드, 런북 V-15.
- 그 전에 필요한 것: V-13·V-14 통과(시간대·세이브 계약 안정), Astra 오디오 레인의 `outdoor_rain` 상태 수용 여부 확인(이슈 #30).

## 16a 설계 (확정) — 2026-10-04 (Opus)

오케스트레이터 결정(D-019, 소유자가 뒤집을 수 있음). 기준 코드는 main `9cd46fc`(WP-14a·WP-15a 🟢, 자동화 등록 36)다. 착수 조건(V-13·V-14 🟢)이 충족됐다.

### 0. 범위

#### 0-1. 16a / 16b
| | 16a (이 WP — 클라우드 + V-16) | 16b (D-010 뒤 PC look-dev) |
|---|---|---|
| 상태·전환 | clear/overcast/rain + 비 강도, fixed/schedule, 전환·강수 지연, 젖음·웅덩이 값 | — |
| 조명 | 수정자 7필드·합성 단계·가설값 | 값 확정, 태양 source angle(흐림의 부드러운 그림자), PPV 색보정 수정자(채도·대비 — splat이면 핵심), 기본 날씨(흐림 기본 여부, R5) |
| 빗줄기 | Niagara 컴포넌트·카메라 추종·활성 규칙·User 파라미터 계약·자리표시 에셋(레시피)·예산 | 빗줄기 머티리얼·크기·밀도·바람 기울기, 카메라 빗방울 화면 효과, 지붕·차양 차폐, 실내에서 창밖 비 |
| 표면 | MPC 값 공급만 | `M_ZoneScan*` 젖음 레이어(러프니스·알베도·웅덩이 마스크·잔물결), 반사(Lumen/SSR, Lumen Lite 결정), splat이면 젖음 범위 재정의(D-015 (b) 범위 재결정) |
| 소리 | C++ 계약(이벤트·조회) | — (Astra 과제는 16a 병합 뒤, 16b와 무관) |
| 성능 | 예산·측정(V-16) | 반사 포함 최종 예산 |

#### 0-2. 메모 골격(§2) 대비 바뀐 것
| # | 메모 | 확정 | 이유 |
|---|---|---|---|
| 1 | 모드 fixed·scripted(JSON 시퀀스) | fixed·**schedule**(시간대 시계의 분에 묶인 결정적 일정) | 시간대 3모드와 한 규칙으로 맞물리고 재현된다(사진·런북·자동화) |
| 2 | `weather_presets.json` | `weather.json` 한 파일(수정자·일정·표면·fx·mpc) | 단일 소스 |
| 3 | 수정자 = `ApplyState` 직전 | `ComposeTarget` 안, 실내 오버레이 **앞** | 실내 안개·노출은 실내 값이 이겨야 한다. `Applied`·전환 보간과 같은 공간 |
| 4 | lighting 키 전부에 곱/가산 | 7필드(scale 4·kelvin 2·exposure 1). 태양 각도·volumetric 불변 | 방향광 회전은 VSM 전 페이지 무효화(V-13), volumetric 토글은 캐시 무효화 |
| 5 | 페이드 = 수정자 보간 2 s | 월드 초 20 s smoothstep + 강수 지연 | 하늘이 먼저 어두워지고 비가 뒤에 온다 |
| 6 | 포토 모드 중 변경 허용 | **정지 + 변경 명령 거절** | 멈춘 빗줄기·젖음과 조명이 어긋난 사진을 막는다. Phase 2 포토 확장이 다시 본다 |
| 7 | `PuddleLevel` | `PuddleAmount` | 높이가 아니라 0~1 양 |
| 8 | 세이브 `{uint8 State; float Intensity}` | `FGolmokSaveWeather{Rule, State(문자열), Intensity, Mode, Wetness, Puddle}` | `CharacterIdRule` 선례(구 세이브 구별), 젖은 길 복원 |
| 9 | 오디오 `outdoor_rain` 상태 | 강도 **레이어** 제안(상태 방식도 수용) | 연속 강도·실내 감쇠. 결정은 Astra와 이슈 #30 |
| 10 | HUD = Debug 훅 블록 | `AddExtraHudLineProvider`(Debug/ 무수정) | `Golmok.Audio.StateMachine`이 상대 개수로 바뀌었다(WP-19 선례) |
| 11 | 자동화 +2 | +3, 세이브는 기존 `Golmok.Save.RoundTrip` 단계 | |
| 12 | 런북 V-15 | V-16 | V-15는 WP-19가 썼다 |

### 1. 파일·클래스 (새 폴더 `Source/Golmok/Weather/`, Claude 레인)
| 파일 | 내용 |
|---|---|
| `GolmokWeatherMath.h` | 순수 헤더(엔진 헤더 없음, `<cmath>`·`<cstdint>`와 순수 `Lighting/GolmokClockMath.h`만). §2~§5·§8 규칙: 상태 이름, 수정자 보간·적용, smoothstep·강수 지연, 표면 적분, 일정 조회, 계약 상수(MPC 파라미터·User 파라미터 이름) |
| `GolmokWeatherConfig.{h,cpp}` | namespace `GolmokWeather`: `weather.json` 파서(전부 아니면 아무것도)와 `FGolmokWeatherConfig` |
| `GolmokWeatherSubsystem.{h,cpp}` | `UGolmokWeatherSubsystem : UTickableWorldSubsystem`(Game·PIE만). `UENUM EGolmokWeather {Clear, Overcast, Rain}`·`EGolmokWeatherMode {Fixed, Schedule}`, 상태 머신·일정·표면·MPC 쓰기·ToD 수정자 전달·델리게이트·콘솔 `golmok.weather`·HUD 공급자 |
| `GolmokWeatherRainFx.{h,cpp}` | namespace `GolmokWeatherRainFx` 자유 함수(생성·갱신·리셋·설명). **Niagara 헤더를 include하는 유일한 파일**이고 헤더에는 Niagara 타입이 없다. 서브시스템은 `UPROPERTY(Transient) TObjectPtr<AActor>`(컴포넌트를 소유한 액터)만 쥔다 |
| `Tests/GolmokWeatherTest.cpp` | 자동화 3개(§14) |
- 유니티 빌드: 파일 범위 도우미는 `GolmokWeather`(RainFx 파일은 `GolmokWeatherRainFx`), 순수 규칙은 `GolmokWeatherMath` namespace, 콘솔 객체 `GCmdWeather`, 로그 `LogGolmok`. 익명 namespace·파일 범위 `static`은 쓰지 않는다.
- `UENUM` 값 순서는 순수 헤더의 `GolmokWeatherMath::State`와 같다(`static_assert`).

### 2. 상태 모델
- **목표** `{EGolmokWeather State, float Intensity}`. Intensity는 Rain에서만 뜻이 있다: [0.05, 1]. clear·overcast는 0이다.
- **약·중·강은 상태가 아니라 값이다**: `weather.json` `rain_levels` light 0.3 · moderate 0.6 · heavy 1.0. 근거: 빗줄기 생성률·소리·MPC·조명이 모두 연속값을 받으므로 상태를 늘리면 전환 표만 늘어난다. 이름은 콘솔 별칭으로 충분하다.
- **현재 값**(틱마다): 수정자 `M_now`, 강수 `RainNow`(0~1, 지금 보이고 들리는 비), `Wetness`, `PuddleAmount`.
- 비는 늘 흐린 하늘 아래다: Rain(I)의 조명 수정자는 `Lerp(M_overcast, M_rain, I)`(§5). I가 0에 가까우면 흐림과 같다.
- 눈·바람·천둥·안개 단독 상태는 없다(§18).

### 3. 전환 — 시간 기준은 월드 초
- 목표가 바뀌면(명령·일정·복원) 전환을 시작한다: `M_start = M_now`, `R_start = RainNow`. α = **누적 월드 델타** / `transition_seconds`(기본 20 s). 시작 시각 차가 아니라 누적이라 일시정지 뒤 보정이 필요 없다(WP-12 `ShiftTransitionStart` 같은 처리 없음).
- 조명: `M_now = Lerp(M_start, M_target, smoothstep(α))`.
- **강수 지연**: 비가 늘 때(R_target > R_start) `p = smoothstep(clamp(2α − 1, 0, 1))` — 하늘이 반쯤 어두워진 뒤 비가 온다. 줄 때 `p = smoothstep(clamp(2α, 0, 1))` — 비가 먼저 그치고 하늘이 갠다. `RainNow = R_start + (R_target − R_start)·p`.
- 진행 중 재목표: 그 순간의 `M_now`·`RainNow`에서 새로 시작한다(튐 없음).
- 즉시(`instant`, 세이브 복원, BeginPlay 초기값, `transition_seconds` 0): `M_now = M_target`, `RainNow = R_target`. 젖음·웅덩이는 즉시 바뀌지 않는다(복원만 세이브 값으로, 룩 확인은 `golmok.weather surface`).
- 시간대 전환(2 s)과 독립이다. ToD가 전환 중이면 날씨는 ToD의 목표 `To`만 갱신한다(§5-4).
- 이벤트 `OnWeatherChanged`는 목표가 바뀔 때 1회다(§9).

### 4. 모드 — 시간대 시계에 묶인 결정적 일정
- `EGolmokWeatherMode`: **Fixed**(기본)는 명령·세이브·초기값으로만 바뀐다. **Schedule**은 `weather.json` `schedule`의 칸을 시간대 시계의 분(`AGolmokTimeOfDay::GetTimeOfDayMinutes()`)으로 고른다. 그 분 이하의 마지막 칸이고, 첫 칸 전이면 마지막 칸이다(자정 넘김). 틱마다 고른 칸이 현재 목표와 다르면 §3 전환을 시작한다.
- 시간대 모드와의 관계(날씨는 시계를 읽기만 하고, 시계는 날씨를 모른다):

| 시간대 | 날씨 Fixed | 날씨 Schedule |
|---|---|---|
| Fixed | 그대로 | 고정 시각의 칸. 키 1–4·F5·`golmok.tod time` 점프 = 재평가(전환) |
| Clock | 그대로 | 시계가 칸 경계를 지날 때 전환 |
| Realtime | 그대로 | PC 현지 시각의 칸(실제 날씨 아님) |
| 레벨 조명(`HasTimeOfDay()` false)·ToD 없음 | 그대로 | 평가하지 않고 현재 유지, status `schedule: no clock` |

- 일정의 "언제"만 시계를 따르고, 전환 속도는 시계 배율과 무관한 월드 초다(시계 x10에서도 20 s).
- Schedule 중 명시 명령(`golmok.weather rain …`)은 Fixed로 바꾼다(로그 `weather: rain in schedule mode -> fixed`). WP-14a 판단 #3(Realtime + `ApplyPreset` → Fixed)과 같은 규칙이다.
- **무작위 없음**: 같은 시각이면 같은 날씨라 사진·런북·자동화가 재현된다. 하루마다 다른 일정(시드)은 시계에 날짜가 없어(1440분 순환) 하지 않는다. 필요하면 Phase 2에서 날짜 카운터와 함께 한다. 실제 기상 API 연동도 하지 않는다(외부 데이터 소스·약관은 소유자 항목).
- 기본 데이터: `initial` = clear·fixed(종전 동일). `schedule`에는 시연용 하루(§6)를 두고 `golmok.weather mode schedule`로 켠다. 흐림을 기본으로 할지(R5)는 16b look-dev가 데이터 한 줄로 정한다.

### 5. 조명 수정자와 합성 순서

#### 5-1. 필드(`GolmokWeatherMath::Modifier`)
| 필드 | 적용 | 항등 | 범위(파서) |
|---|---|---|---|
| `lux_scale` | 태양 lux × | 1 | (0, 2] |
| `sky_scale` | SkyLight 세기 × | 1 | (0, 2] |
| `fog_scale` | 안개 밀도 × | 1 | (0, 5] |
| `fog_height_falloff_scale` | 안개 높이 감쇠 × | 1 | (0, 2] |
| `kelvin_target`, `kelvin_weight` | K' = K + (target − K)·weight(`bUseTemperature`일 때만) | 6500, 0 | [2000, 12000], [0, 1] |
| `exposure_offset` | 노출 bias +(EV) | 0 | [−2, 2] |
- 태양 회전(pitch·yaw)·`volumetric`은 바꾸지 않는다. 방향광 회전은 VSM 전 페이지를 무효화하고(V-13), volumetric 토글은 캐시를 무효화한다. 흐림의 부드러운 그림자(태양 source angle)는 16b 후보다.
- `exposure_offset`이 0이 아니면 `bExposureOverridden = true`로 두고 유효 bias(상태의 `ExposureBias` — 볼륨 값 또는 엔진 기본값)에 더한다. 0이면 플래그를 건드리지 않는다.
- **항등이면 입력을 그대로 돌려준다**(비트 동일). 그래서 clear에서 기존 `Golmok.Lighting.*`·V-03/V-09/V-13 기대값이 바뀌지 않는다.
- 보간 `Lerp(A, B, t)`: scale 4개는 log2 공간(지각상 균등 — 14b의 EV 공간 보간 방향과 같다. 그래서 scale > 0), 나머지는 선형. Rain(I) = `Lerp(M_overcast, M_rain, I)`, clear = 항등.

#### 5-2. 기본값(가설 — 값 확정은 16b)
R5(흐린 날 촬영 텍스처) 방향으로 잡는다. 흐림·비는 직사광을 크게 줄이고 안개를 올리며 색온도를 중성 쪽으로 옮기고, 노출은 조금 어둡게 둔다(비 오는 날의 체감). 자동 노출이 이를 얼마나 되돌리는지는 V-16에서 잰다.

| | lux | sky | fog | falloff | kelvin(target, weight) | exposure |
|---|---|---|---|---|---|---|
| overcast | 0.3 | 1.0 | 1.4 | 0.8 | 6800, 0.5 | −0.2 |
| rain(I=1) | 0.12 | 0.8 | 2.0 | 0.6 | 7200, 0.7 | −0.4 |

#### 5-3. 합성 순서(한 곳, `AGolmokTimeOfDay::ComposeTarget`)
1. **기저** = `ComposeBase()`: 시계 위면 키프레임 보간(유지 구간 포함, `EvaluateClock`), 아니면 프리셋 값(Fixed `ApplyPreset`) 또는 레벨 조명(`Initial`).
2. **날씨** = `GolmokWeatherMath::Apply(기저, M_now)`.
3. **실내 오버레이**(WP-05 `interior` 프리셋): 안개·노출·volumetric을 실내 값으로 덮는다. 실내에서는 날씨 안개·노출 변화가 보이지 않고, 창으로 드는 태양·하늘빛은 날씨만큼 준다.
4. **시간대 전환 보간** `Lerp(From, To, α)`(2 s) → `ApplyState`. `From = Applied`도 1~3을 거친 값이라 같은 공간이다.
- `IsNight`/`OnNightChanged`/`OnPresetChanged`/`CurrentPreset`은 1(기저)만 본다. 날씨는 밤 판정과 WP-13 낮/밤 소리를 바꾸지 않는다.
- 포토 모드 EV 기준(`UGolmokPhotoModeSubsystem::BaseExposureBias` = `CaptureState`)은 4의 결과라 날씨 bias를 포함한다. 포토 모드 중에는 날씨가 멈춰 있으므로(§10) 일정하다.
- **14b 호환**: 14b가 넣을 노출 범위 키(Min/Max EV100, V-13 입력 1·2)는 1(기저 프리셋)에 속하고 날씨가 **바꾸지 않는다**. 그래서 범위가 마지막 안전장치(유효 노출 [−8, 12] 안, 여유 ≥ 1 EV)로 남고, night 유지 구간의 Min = Max 고정도 그대로다(bias만 움직인다). 14b 런북 수용 기준(엔진 노출 경고 0회)에 overcast·rain heavy를 더한다. 16a는 V-16 §5에서 경고가 난 시각을 기록해 14b에 넘긴다. 범위 자체를 옮겨야 한다고 14b가 판단하면 그때 `exposure_range_offset`을 schema 2로 더한다(16a는 이름만 예약).

#### 5-4. `Lighting/` 변경(Claude 레인, 훅 표지 없음, WP-13 훅 블록 무수정)
- `GolmokTimeOfDay.h`: `#include "Weather/GolmokWeatherMath.h"`(순수 헤더), 공개 `void SetWeatherModifier(const GolmokWeatherMath::Modifier& M, bool bSettled)`·`const GolmokWeatherMath::Modifier& GetWeatherModifier() const`, private `GolmokWeatherMath::Modifier WeatherModifier`(항등 초기값).
- `ComposeTarget()`: `ComposeBase()` 다음, 실내 오버레이 앞에 한 줄(private 도우미가 `FGolmokLightingState` ↔ 순수 값을 변환).
- `SetWeatherModifier`: 저장한다. BeginPlay 전이면 여기서 끝난다(BeginPlay가 `Initial`을 잡은 뒤 적용). 전환 중이면 `To = ComposeTarget()`(남은 전환이 새 목표로 간다). 시계가 진행 중(Clock/Realtime, 틱 켜짐)이면 저장만 하고 다음 시계 틱의 `ApplyClockState(ComposeTarget())`가 반영한다(`bSettled`면 `bRecapturePending = true`). 그 밖(Fixed 정지)이면 `ApplyState(ComposeTarget(), /*bFinal*/ bSettled)`.
- `bSettled`: 날씨 전환 중에는 false(조명 값만 쓰고 가시성·volumetric·정적 SkyLight 재캡처는 하지 않음), 전환 끝·즉시 변경에서 정확히 1회 true.
- `BeginPlay` 끝: 수정자가 항등이 아니면 `ApplyState(ComposeTarget(), true)`를 1회(레벨 조명 기저도 날씨를 받는다).
- 다른 동작(프리셋·시계·실내·이벤트·콘솔·`lighting_presets.json`)은 그대로다. 에디터 Python `lighting.py`도 바꾸지 않는다(에디터 레벨 look-dev는 PIE에서).

### 6. `Config/Golmok/weather.json` (schema 1, 단일 소스)
```json
{
  "schema_version": 1,
  "initial": {"state": "clear", "mode": "fixed"},
  "transition_seconds": 20.0,
  "rain_levels": {"light": 0.3, "moderate": 0.6, "heavy": 1.0},
  "modifiers": {
    "overcast": {"lux_scale": 0.3, "sky_scale": 1.0, "fog_scale": 1.4, "fog_height_falloff_scale": 0.8,
                 "kelvin_target": 6800.0, "kelvin_weight": 0.5, "exposure_offset": -0.2},
    "rain":     {"lux_scale": 0.12, "sky_scale": 0.8, "fog_scale": 2.0, "fog_height_falloff_scale": 0.6,
                 "kelvin_target": 7200.0, "kelvin_weight": 0.7, "exposure_offset": -0.4}
  },
  "surface": {"wet_seconds": 60.0, "dry_seconds": 600.0, "puddle_min_intensity": 0.4,
              "puddle_fill_seconds": 240.0, "puddle_dry_seconds": 1200.0},
  "schedule": [
    {"time": "00:00", "state": "rain", "intensity": 0.3},
    {"time": "03:00", "state": "overcast"},
    {"time": "08:30", "state": "clear"},
    {"time": "13:00", "state": "overcast"},
    {"time": "15:00", "state": "rain", "intensity": 0.6},
    {"time": "16:30", "state": "rain", "intensity": 1.0},
    {"time": "17:00", "state": "rain", "intensity": 0.3},
    {"time": "17:45", "state": "overcast"},
    {"time": "19:30", "state": "clear"},
    {"time": "22:30", "state": "overcast"}
  ],
  "rain_fx": {"system": "/Game/Golmok/Weather/NS_GolmokRain.NS_GolmokRain", "enabled": true,
              "max_spawn_rate": 12000, "box_half_extent_cm": [1000, 1000, 500], "height_offset_cm": 300},
  "mpc": "/Game/Golmok/Weather/MPC_GolmokWeather.MPC_GolmokWeather"
}
```
- 최상위 키는 정확히 위 9개이고 미지 키는 오류다. 상태 이름은 `clear|overcast|rain`. `modifiers`는 정확히 `overcast`·`rain` 두 개이고 각 7키다(clear는 항등 고정 — 키가 있으면 오류). `rain_levels`는 3키, (0, 1], 엄격 증가. 강도: rain은 [0.05, 1] 필수, clear·overcast는 키 금지(`initial`·`schedule` 모두). `initial.mode`는 `fixed|schedule`.
- `schedule`은 1칸 이상, `time`은 "HH:MM"(`GolmokClockMath::ParseHHMM`, Python `lighting_presets.parse_hhmm`), 엄격 증가. `surface` 5키는 > 0(`puddle_min_intensity`만 [0, 1)). `transition_seconds`는 [0, 600].
- `rain_fx.system`·`mpc`는 `/Game/`로 시작하는 오브젝트 경로. `max_spawn_rate` (0, 20000], `box_half_extent_cm` 3원소 각 [100, 5000], `height_offset_cm` [−1000, 3000], `enabled` bool.
- C++(`GolmokWeather::ParseConfigText`)와 Python(`Content/Python/golmok/weather_pure.py` `parse_config`)은 같은 규칙·같은 오류 문구(`weather.json: <위치>: <이유>`)를 쓴다. 파싱이 실패하면 날씨가 꺼진다: clear 항등을 유지하고, 명령은 오류 메시지를 내며, Error 로그는 1회다.
- 패키지: 기존 `+DirectoriesToAlwaysStageAsUFS=(Path="../Config/Golmok")`가 스테이징한다(ini 변경 없음).

### 7. 빗줄기 파티클 — Niagara

#### 7-1. Niagara 채택(결정)
- **채택한다.** Niagara는 엔진에 동봉된 Epic 1st-party FX 시스템(`Engine/Plugins/FX/Niagara`)이고 UE5의 표준 파티클이다(Cascade는 신규 제작용이 아니다[2차]). Experimental이 아니고 새 라이선스도 없다. EnhancedInput·PythonScriptPlugin과 같은 취급이라 D-002에 새 항목이 필요 없다.
- **되돌리기 비용이 작다.** 의존 코드는 `Weather/GolmokWeatherRainFx.cpp` 한 파일, 설정은 `.uproject` 플러그인 항목과 `Golmok.Build.cs` 훅 한 줄, 에셋은 `NS_GolmokRain` 하나다. 되돌리면 그 파일을 빈 구현으로 바꾸고 세 곳을 지운다. 빗줄기만 사라지고 나머지 계약은 그대로다. 그래서 "되돌리기 비용이 큰 스택 변경"(D-019 ⑤)이 아니고, 오케스트레이터가 정한다.
- 기각한 대안: (a) 컴파일 의존 없이 `UFXSystemComponent`(Engine)와 클래스 이름으로 Niagara 컴포넌트를 만들고 리플렉션으로 에셋을 꽂는 편법 — 깨지기 쉽다(WP-19 §13 (d)와 같은 이유). (b) 카메라에 붙인 원통 카드 + 패닝 머티리얼 — Engine만으로 되지만 시차·밀도 표현이 약하다(품질 최우선). (b)는 Niagara를 되돌릴 때의 스택 폴백으로만 남긴다(§7-6).
- **켜는 법**(별도 커밋 `WP-16: plugins (Golmok.uproject)`): `Plugins` 배열의 마지막 원소(`AndroidFileServer`) **앞**에 `{"Name": "Niagara", "Enabled": true},` 원소를 새 줄로 넣는다(JSON이라 훅 표지는 못 쓰고, 기존 줄은 고치지 않는다). 엔진 기본 활성(`EnabledByDefault`)이어도 명시한다. 프로젝트 모듈이 목록에 없는 플러그인 모듈에 의존하면 UBT가 경고하고[미확인 §17 #1], 누가 플러그인을 끄면 빌드가 조용히 깨지기 때문이다. `Modules[].AdditionalDependencies`는 그대로 둔다(`test_ue_wp19_fixture.py`가 고정). D-021 허용 목록 테스트의 `ALLOWED_PLUGINS`에 훅 줄로 `Niagara`를 더한다(§15).
- **`Golmok.Build.cs`**(핫스팟): `PrivateDependencyModuleNames.AddRange` 블록 바로 뒤, 편집기 테스트 주석·`Target.bBuildEditor` 앞에 `// [WP-16 hook] …` ~ `// [/WP-16 hook]` 블록으로 `PrivateDependencyModuleNames.Add("Niagara");` 한 줄과 이유 주석 한 줄. Private인 이유: 우리 헤더는 Niagara 타입을 노출하지 않는다.

#### 7-2. 컴포넌트 계약
- 월드마다 transient 액터 1개(`GolmokWeatherFx`, 저장·복제 없음)에 `UNiagaraComponent` 1개를 둔다.
- 위치: 날씨 틱마다 `PlayerCameraManager->GetCameraLocation() + (0, 0, height_offset_cm)`, 회전 없음(월드 축 정렬 박스). 1프레임 늦어도 무해하다(입자는 월드 공간).
- **월드 공간 시뮬레이션**(카메라가 움직여도 이미 떨어지는 빗줄기는 제자리 — 시차가 맞다), GPU 시뮬레이션, 고정 경계(박스 + 여유).
- **User 파라미터 계약**(이름은 `GolmokWeatherMath` 상수 = Python 상수, pytest가 대조):
  - `User.RainIntensity`(float 0~1) = `RainNow`. 16b가 굵기·불투명도에 쓴다.
  - `User.SpawnRate`(float) = `RainNow × max_spawn_rate`. 예산 손잡이가 JSON에 남는다.
  - `User.BoxHalfExtent`(vector, cm) = `box_half_extent_cm`.
  - 값은 0.001 넘게 바뀔 때만 쓴다.

#### 7-3. 활성 규칙
| 조건 | 동작 |
|---|---|
| `rain_fx.enabled` false, 에셋 없음·로드 실패, `golmok.weather fx off` | 컴포넌트 없음 또는 비활성, HUD `fx disabled` / `fx missing` / `fx off` |
| `RainNow` ≤ 0.001 | `Deactivate()`(새 생성 없음, 남은 입자는 수명 1 s 안에 사라짐), HUD `fx idle` |
| 실내(`AGolmokTimeOfDay::IsInterior()`, `OnInteriorChanged` 구독) | `Deactivate()` + 추종 정지(§11), HUD `fx interior` |
| 실내에서 나옴·비 시작 | `Activate(true)` — 에셋 `WarmupTime` 1 s로 곧바로 내리는 비 |
| `UGolmokTravelSubsystem::OnTraveled`·세이브 위치 복원 | `ResetSystem()`(텔레포트 줄무늬 방지) |
| 포토 모드 | 호출 없음. 월드가 멈춰 빗줄기가 멈춘 채 찍힌다(§10) |

#### 7-4. 자리표시 에셋 `/Game/Golmok/Weather/NS_GolmokRain`(PC가 레시피로 1회 저작, 룩은 16b)
Niagara 모듈 스택을 엔진 Python으로 만들 수 있는지 확인되지 않았다[미확인 §17 #8]. 그래서 클라우드에서 검증할 수 없는 생성기는 만들지 않는다. V-16 런북 §2에 레시피를 두고, PC 세션이 Niagara 에디터로 한 번 만들어 커밋한다(`.uasset` LFS·잠금. 이 에셋은 PC 세션만 고친다).
- 시스템: 빈 이미터 1개, GPU Compute Sim, Local Space 끔, Fixed Bounds = ±(BoxHalfExtent + 500 cm), Warmup 1.0 s, User 파라미터 3개(§7-2, 기본값 0 · 0 · (1000, 1000, 500)).
- Emitter Update: Spawn Rate = `User.SpawnRate`. Particle Spawn: Shape Location Box(크기 = 2 × `User.BoxHalfExtent`), Lifetime 1.0 s, Add Velocity (0, 0, −1000 cm/s ±10 %), 스프라이트 크기 (1, 60) cm. Particle Update: Solve Forces and Velocity. Renderer: Sprite, 속도 정렬, 엔진 기본 스프라이트 머티리얼(자리표시).
- 16b가 바꿀 것: 머티리얼·크기·밀도·바람·차폐(지붕·차양 아래 비 제거).

#### 7-5. 성능 예산(RTX 5060 8 GB, 1080p — V-16 §10)
- 빗줄기 GPU ≤ **0.5 ms**(rain heavy). 날씨 전체(같은 fixed 시각의 rain heavy − clear) ≤ **+1.0 ms** GPU. 게임 스레드 +0.05 ms 이하(틱당 할당 없음). 살아 있는 입자 ≤ 20,000(`max_spawn_rate` ≤ 20,000 × 수명 1 s).
- 넘으면 코드가 아니라 데이터로 낮춘다: `max_spawn_rate` 12,000 → 8,000 → 5,000. 그래도 넘으면 V-16 결과에 적고 16b가 머티리얼·크기로 푼다. volumetric 안개는 날씨가 켜지 않으므로 그 비용은 변하지 않는다. 정적 SkyLight 레벨에서는 전환 끝 재캡처 1회의 히치를 기록한다.

#### 7-6. 폴백
- **런타임**: 에셋이 없거나(V-16 전의 클론·CI) 로드에 실패하거나 `enabled` false·`fx off`면 빗줄기만 없다. 상태·조명·MPC·이벤트·세이브는 그대로 동작하고 경고는 1회다(`weather: rain fx missing (/Game/Golmok/Weather/NS_GolmokRain) - rain is lighting/MPC/audio only`). `-nullrhi` 자동화는 컴포넌트·파라미터 계약만 본다(GPU 시뮬레이션 없음).
- **스택**: Niagara를 되돌리면 §7-1 (b)(카메라 부착 카드)를 16b 룩 작업으로 만든다. 계약(`RainNow`, User 파라미터의 뜻)은 같다.

### 8. 젖음 계약 — MPC `MPC_GolmokWeather`(16b가 소비)
- 에셋 `/Game/Golmok/Weather/MPC_GolmokWeather`(경로는 `weather.json` `mpc`). 스칼라 3개, 이름·순서 고정, 기본값 0(날씨 없는 머티리얼은 마른 모습):

| 파라미터 | 뜻(0~1) | 16b 사용 예 |
|---|---|---|
| `RainIntensity` | 지금 내리는 비 = `RainNow`(하늘보다 늦게 오르고 먼저 내린다) | 잔물결·물방울 노멀, 빗물 흐름 |
| `Wetness` | 표면 젖음 | 러프니스 낮춤·알베도 어둡게·스페큘러 |
| `PuddleAmount` | 웅덩이 채움(항상 ≤ `Wetness`) | 높이·AO 마스크 임계 |

- **표면 적분**(월드 초 dt, 포토 모드 중 정지, `GolmokWeatherMath::StepSurface`): `RainNow > 0.01`이면 `Wetness += dt · RainNow / wet_seconds`, 아니면 `Wetness −= dt / dry_seconds`. `RainNow > puddle_min_intensity`이면 `PuddleAmount += dt · (RainNow − min) / (1 − min) / puddle_fill_seconds`, 아니면 `PuddleAmount −= dt / puddle_dry_seconds`. 둘 다 [0, 1]로 자르고 마지막에 `PuddleAmount = min(PuddleAmount, Wetness)`. 기본값이면 강한 비에 60 s면 흠뻑 젖고, 그친 뒤 10분에 마른다. 웅덩이는 강한 비 4분에 차고 20분에 빠진다(가설, 16b 확정).
- **쓰기**: 날씨 서브시스템만 쓴다. `UWorld::GetParameterCollectionInstance(MPC)->SetScalarParameterValue`로, 값이 0.001 넘게 바뀔 때만. MPC가 없으면 값은 서브시스템에만 있고(`GetWetness()` 등) 경고는 1회다.
- 실내: MPC 값은 전역(바깥 날씨)이다. 실내 Zone(`kind: interior`) 머티리얼은 16b에서 바인딩하지 않는다.
- splat 표현(D-010)이면 바인딩 대상이 없어 값은 무시된다. 계약은 그대로 둔다.
- **16a는 룩을 만들지 않는다**: MPC를 참조하는 머티리얼·머티리얼 함수를 만들지 않고 `M_ZoneScan*`을 고치지 않는다. MPC 파라미터를 나중에 더하면 참조하는 머티리얼이 전부 재컴파일되므로 이 세 개를 지금 고정한다(16b가 더 필요하면 추가만, 이름 변경 금지).
- **생성**: 에디터 Python `golmok.weather_setup.run()` — 없으면 `MaterialParameterCollectionFactoryNew`로 만들어 스칼라 3개를 넣고 저장한다. 있으면 이름·기본값만 검사하고 고치지 않는다(불일치는 Error 로그). Python으로 `scalar_parameters`를 쓰지 못하면[미확인 §17 #9] 런북 §2a의 수동 절차(3개, 기본 0)를 쓴다. 결과 `.uasset`은 커밋한다. 16b 머티리얼이 참조하는 안정 에셋이라 WP-13 `SW_*`처럼 ignore·재생성으로 두지 않는다.

### 9. 오디오 훅 — Claude 쪽 계약, 소비는 Astra 오디오 레인
```cpp
// Weather/GolmokWeatherSubsystem.h (Claude 레인; Audio/는 include만 한다)
DECLARE_MULTICAST_DELEGATE_ThreeParams(FGolmokOnWeatherChanged, EGolmokWeather /*Target*/, float /*TargetIntensity*/, bool /*bInstant*/);

class GOLMOK_API UGolmokWeatherSubsystem : public UTickableWorldSubsystem
{
public:
	static UGolmokWeatherSubsystem* Get(const UWorld* World); // Game·PIE 월드, 없으면 nullptr
	EGolmokWeather GetTargetWeather() const;
	float GetTargetIntensity() const;
	float GetRainIntensity() const;  // RainNow: 지금 보이고 들리는 비 0~1(강수 지연 포함), clear·overcast로 가라앉으면 0
	float GetWetness() const;
	float GetPuddleAmount() const;
	bool IsTransitioning() const;
	bool IsFrozen() const;           // 포토 모드
	static const TCHAR* WeatherName(EGolmokWeather Weather); // "clear" | "overcast" | "rain"
	FGolmokOnWeatherChanged OnWeatherChanged;
};
```
- `OnWeatherChanged`: 목표가 바뀌는 순간 1회 발화한다(명령·일정 경계·복원 — 복원은 `bInstant` true). BeginPlay 초기값은 구독 전이라 발화하지 않는다. 강도 램프 중에는 발화하지 않는다. 콜백 안에서 `GetTarget*`는 새 값이고 `GetRainIntensity()`는 아직 램프 전 값이다(R51-5와 같은 "목표 먼저" 계약).
- 연속값은 **조회**한다. 오디오 서브시스템이 이미 매 프레임 도는 자기 틱에서 `GetRainIntensity()`를 읽는다. 매 프레임 델리게이트 방송은 하지 않는다.
- 의존 방향: Audio → Weather 헤더(읽기만). Weather는 Audio를 모른다. 날씨 서브시스템이 없거나(구 빌드·에디터 월드) 꺼져 있으면 `Get()`이 nullptr이거나 값이 0이라 오디오는 종전과 같다.
- **제안**(결정은 Astra — 질문은 이슈 #30): **빗소리 레이어**. 낮/밤/실내 베드 위의 세 번째 채널이고 gain은 `audio.json`의 강도 곡선(예: 0 → 0, 0.3 → 0.35, 1 → 0.8)을 따른다. 실내에서는 감쇠한다(예: ×0.35, 선택으로 저역 통과 — 지붕·창의 빗소리). Photo mute 정책은 같고, HUD `audio:` 줄에 `rain 0.60`을 붙인다. 대안으로 `outdoor_rain` 상태(실외에서 `RainNow` ≥ 임계면 낮/밤 베드 대신)도 받는다. 선택: `GetWetness()` ≥ 0.5면 발소리 `wet` 세트. 소스는 WP-13 규칙(플레이스홀더 합성 또는 원문을 확인한 CC0, D-002 기록)을 따른다.
- 시점: 계약 합의는 16a 구현 전(이슈 #30), Astra 구현은 16a 병합 뒤 main에서 한다. 16a는 `Audio/`·`audio.json`을 고치지 않는다. V-16에서 빗소리가 없는 것은 Astra 과제 전이라 정상이다.

### 10. 포토 모드(WP-12)
- 포토 모드 중(`UGolmokPhotoModeSubsystem::IsActiveIn`, GamePause든 TimeDilation이든) 날씨는 **정지**한다. 전환 α·강수·젖음·웅덩이·일정 평가가 멈춘다. 기본 GamePause에서는 월드가 멈춰 빗줄기도 멈춘 채 찍힌다(사진에서 멈춘 빗줄기는 장점이다). 종료하면 누적 델타 방식이라 이어서 진행된다.
- `golmok.weather`의 변경 명령은 거절한다(`weather: photo mode is active - change the weather before entering photo mode`). `status`·`list`는 된다. 근거: 조명은 즉시 바뀌는데 멈춘 빗줄기·젖음은 바뀌지 않아 어긋난 사진이 된다. Phase 2 포토 확장(시간대 슬라이더·날씨 선택)이 프리웜과 함께 다시 정한다.
- 사진 메타 JSON에 `"weather": {"state": "rain", "intensity": 0.6}`(날씨 서브시스템이 없거나 꺼져 있으면 `null`)를 `preset` 다음 키로 더한다. `GolmokPhotoMath` 메타 형식·`test_ue_photo_math.py` `META_KEYS`·g++ 드라이버를 함께 고치고, 메타 `version`은 1을 유지한다(필드 추가).

### 11. 실내(WP-05/06 포털)
- 실내 판정은 `AGolmokTimeOfDay::IsInterior()`/`OnInteriorChanged(bool)`(WP-13 훅 블록의 공개 구독 API)을 그대로 쓴다. 날씨가 따로 판정하지 않는다.
- 조명: §5-3 합성 순서대로다(안개·노출은 실내 값, 태양·하늘은 날씨만큼 감소).
- 빗줄기: 실내 동안 비활성·추종 정지(§7-3). 문간에서 남은 입자가 1 s 안쪽으로 보일 수 있다 — 수용하고 V-16 §7에서 관찰한다. 실내에서 창밖으로 보이는 비와 지붕·차양 아래 비 제거는 차폐가 필요해 16b다.
- MPC는 전역 유지(§8), 오디오는 Astra 규칙(§9).
- 날씨 상태·일정·젖음은 실내에서도 계속 흐른다(밖에는 계속 비가 온다).

### 12. 세이브(WP-15a, `Save/` Claude 레인)
- `Save/GolmokSaveGame.h`에 USTRUCT `FGolmokSaveWeather`(모두 `UPROPERTY(SaveGame)`): `int32 Rule = 0`, `FString State`, `float Intensity = 0`, `uint8 Mode = 0`, `float Wetness = 0`, `float Puddle = 0`. `UGolmokSaveGame`에 필드 `FGolmokSaveWeather Weather`와 상수 `WeatherRuleNone = 0`·`WeatherRuleV1 = 1`을 둔다(`CharacterIdRule` 선례).
  - Rule 0 = 날씨 필드가 없던 세이브(태그 직렬화로 0) → **날씨를 복원하지 않는다**. 현재 날씨(= `initial`)를 유지하고 메시지는 `, weather - (not in save)`. Rule ≥ 1이면 아래 필드로 복원한다.
  - `State`는 문자열(`clear|overcast|rain`)이다. enum 순서와 세이브 형식을 떼어 놓기 위해서다(ToD `Mode`는 uint8 선례지만 날씨 상태는 늘 수 있다). 모르는 문자열은 clear + 메시지 `(unknown weather '<s>')`. `Mode`는 0 Fixed·1 Schedule이고 그 밖은 Fixed.
  - `SaveSchemaVersion`은 1 그대로다(필드 추가·기본값. `Restore`가 1만 받으므로 올리면 옛 세이브가 거절된다).
- **저장**: 스냅샷(`FSnapshot`)에 다섯 값 + Rule 1. `HoldSlotPosition`은 시간대처럼 슬롯 값을 그대로 넘긴다(Rule 포함 — 레거시를 1로 올리지 않는다). 저장 트리거는 늘리지 않되 `OnWeatherChanged` → `MarkDirty()`로 주기 저장이 날씨 변경을 싣게 한다. 젖음 값만 바뀐 것은 dirty가 아니다(다른 저장에 함께 실린다).
- **복원 순서**: 위치 → **시간대** → **날씨** → 캐릭터. 날씨가 시간대 뒤인 이유는 일정 모드가 복원된 시각을 읽기 때문이다. 절차: `SetMode(Fixed)` → `SetWeather(State, Intensity, instant)` → `SetSurface(Wetness, Puddle)` → 저장 모드가 Schedule이면 `SetMode(Schedule)`. 다음 틱에 일정 칸이 다르면 저장 상태에서 §3 전환이 시작된다("자리를 비운 사이 날씨가 바뀌었다" — Realtime 시계에서 자연스럽다). 빗줄기는 `ResetSystem`.
- `golmok.save status`의 `slot:` 줄에 `weather rain 0.60 wet 0.42 puddle 0.10 fixed` 또는 `weather - (not in save)`를 쓰고, `golmok.load` 메시지에 `, weather …`를 붙인다.
- 테스트는 기존 `Golmok.Save.RoundTrip`에 단계를 더한다(등록 수 불변, §14).

### 13. 콘솔·HUD
- 명령은 `golmok.weather` 하나다(등록부 +1):
  - `golmok.weather [status]` — 목표·현재·α, 수정자 7값, RainNow·젖음·웅덩이, 모드와 일정의 현재·다음 칸, MPC `ok|missing`, fx 상태, 정지 여부.
  - `golmok.weather clear|overcast [instant]`, `golmok.weather rain [light|moderate|heavy|<0.05~1>] [instant]`(기본 moderate). 범위 밖·모르는 단어는 오류 문구.
  - `golmok.weather mode fixed|schedule`, `golmok.weather list`(일정 칸, 현재 칸 표시).
  - `golmok.weather surface <wetness> [puddle]` — 16b look-dev용 즉시 설정(그 뒤 적분은 계속). `golmok.weather fx on|off` — 성능 A/B(저장 안 함).
  - 포토 모드 중 변경 명령은 거절(§10). 에디터 월드에서는 `no game world`.
- HUD: `UGolmokDebugSubsystem::AddExtraHudLineProvider`(WP-13 훅 API, WP-19 선례)로 한 줄을 넣는다. `Debug/`는 고치지 않는다. 형식 `weather: rain 0.60 (from clear 35%) | now 0.12 wet 0.05 puddle 0.00 | fixed | fx on`. 일정 모드면 ` | schedule next 15:00 rain 0.60`, 정지 중이면 끝에 ` | frozen`.

### 14. 테스트
- **UE 자동화**(`Tests/GolmokWeatherTest.cpp`, `-nullrhi`, 등록 36 → **39**. 착수 시 main의 실제 수 + 3):
  - `Golmok.Weather.Config`(PIE 없음): 저장소 `weather.json` 파싱·값, 오류 표(Python과 같은 문구, 12종 이상: 버전·미지 키·clear 수정자·범위·강도 규칙·일정 순서/형식·경로), 순수 규칙의 엔진 빌드 컴파일 확인(항등 비트 동일, Rain(0.05) ≈ overcast, 강수 지연 경계, 웅덩이 ≤ 젖음, 자정 넘김 일정).
  - `Golmok.Weather.Lighting`(L_Dev PIE): 프리셋 4 × {clear, overcast, rain 0.6} 즉시 → `CaptureState` == `Apply(프리셋 상태)`. clear는 `PresetApply` 기대값과 비트 동일. 실내 진입 시 안개 0·bias = interior 값, lux·sky는 수정값. ToD 2 s 전환 중 날씨 변경 → 전환 끝 = 새 합성. 날씨 전환 α 0.5 값 = 공식(서브시스템 틱 수동 구동). 날씨를 바꿔도 `IsNight`·`OnPresetChanged` 발화 0. Clock(rate 60) + Schedule → 칸 경계에서 `OnWeatherChanged` 정확히 1회·인자. 레벨 조명 기저에서 rain → clear 복귀 시 `bExposureOverridden` 원래 값.
  - `Golmok.Weather.Runtime`(L_Dev PIE): 콘솔 파싱(`rain heavy`·`rain 0.42`·범위 밖·`instant`·Schedule 중 명시 → Fixed), 이벤트 횟수와 콜백 안 조회 값, 강수 지연(오름: α < 0.5에서 0, 내림: α 0.5에서 0), 표면 적분 표, 포토 모드(GamePause) 진입 → 진행 0·변경 거절·종료 뒤 α 연속, 실내 → fx 비활성, `OnTraveled` → fx 리셋, HUD 줄 형식. MPC가 있으면 인스턴스 값 == 조회 값(±1e-3), 없으면 Info `MPC_GolmokWeather missing - skipped`. NS가 있으면 컴포넌트·User 파라미터 3개 존재·활성 규칙, 없으면 Info skip(GaspSmoke 선례).
  - `Golmok.Save.RoundTrip`에 날씨 단계(등록 불변): Rule 1 왕복(다섯 값), Rule 0 슬롯 → 날씨 유지·메시지, Schedule 모드는 시간대 뒤 복원, 모르는 상태 문자열, status 줄.
  - `pc-verify-wp12.md` "두 번째 명령" 줄의 총수·목록을 고친다(`test_ue_wp12_fixture.py`가 강제).
- **pytest**:
  - `test_ue_weather_math.py` + `fixtures/ue/weathermath_driver.cpp`: `GolmokWeatherMath.h` g++ 교차검증(`-Wall -Wextra -Wshadow -Werror -pedantic`). 표 + `weather_pure.py` 참조 구현과 무작위 600건(Apply·log Lerp·PrecipAlpha·StepSurface·ScheduleIndexAt).
  - `test_ue_config_weather.py`: 저장소 `weather.json` 유효, 오류 사례(C++ 자동화와 같은 표), 계약 상수 대조(MPC 이름 3·User 파라미터 3이 C++ 헤더 = Python), 기본 `initial`이 clear·fixed(종전 동일 보장).
  - `test_ue_python_weather_setup.py`: `fake_unreal`에 MPC 팩토리·`CollectionScalarParameter` 기록을 더해 생성·멱등·불일치 Error·NS 없음 로그를 본다.
  - `test_ue_wp16_fixture.py`: `Weather/` 파일 목록·규약(이름 있는 namespace, 파일 범위 static 금지), Niagara include는 `GolmokWeatherRainFx.cpp`에만, 훅 블록의 정확한 내용(Build.cs·DefaultGame.ini), `.uproject` Niagara 항목 Enabled, `ComposeTarget`에서 날씨 줄이 실내 오버레이 앞, 자동화 3개 선언, HUD는 공급자 등록(`Debug/`에 WP-16 문자열 없음), 사진 메타 `weather` 키.
  - 기존 등록부 테스트는 훅 줄로 고친다(§15).

### 15. 레인·핫스팟
- **새 파일**(Claude 레인): `Source/Golmok/Weather/*`, `Tests/GolmokWeatherTest.cpp`, `Config/Golmok/weather.json`, `Content/Python/golmok/weather_pure.py`·`weather_setup.py`, pytest 4개 + 드라이버, `docs/runbooks/pc-verify-wp16a.md`. PC가 만드는 `Content/Golmok/Weather/MPC_GolmokWeather.uasset`·`NS_GolmokRain.uasset`.
- **고치는 Claude 레인 파일**(핫스팟 아님, 훅 표지 없음): `Lighting/GolmokTimeOfDay.{h,cpp}`(§5-4, WP-13 훅 블록 무수정), `Save/GolmokSaveGame.h`·`GolmokSaveSubsystem.{h,cpp}`·`Tests/GolmokTravelSaveTest.cpp`(§12), `Photo/GolmokPhotoMath.h`·`GolmokPhotoModeSubsystem.cpp`·`tools/tests/test_ue_photo_math.py`와 드라이버(§10), `tools/tests/fake_unreal.py`, `docs/runbooks/pc-verify-wp12.md`(총수 줄).
- **핫스팟**(별도 커밋 `WP-16: hook <파일>`, 기존 줄 무수정):

| 파일 | 내용 |
|---|---|
| `Golmok.uproject` | 별도 커밋 `WP-16: plugins (Golmok.uproject)`. `AndroidFileServer` 원소 앞에 `{"Name": "Niagara", "Enabled": true},` 새 줄(§7-1) |
| `Golmok.Build.cs` | 비공개 의존 블록 뒤: `// [WP-16 hook] Niagara: rain particles (Weather/GolmokWeatherRainFx.cpp only)` / `PrivateDependencyModuleNames.Add("Niagara");` / `// [/WP-16 hook]` |
| `Config/DefaultGame.ini` | 파일 끝: `; [WP-16 hook] weather MPC / Niagara system are referenced only from weather.json` + `[/Script/UnrealEd.ProjectPackagingSettings]` + `+DirectoriesToAlwaysCook=(Path="/Game/Golmok/Weather")` |
| `test_ue_wp09_fixture.py` | `CONSOLE_COMMANDS` 끝 `"golmok.weather",  # [WP-16 hook]`, `BUILD_CS_PRIVATE` 정의 다음 줄 `BUILD_CS_PRIVATE \|= {"Niagara"}  # [WP-16 hook] rain particles` |
| `test_ue_zone_fixture.py` | `CONVENTION_FOLDERS += ("Weather",)  # [WP-16 hook]` |
| `test_ue_wp05_fixture.py` | `+DirectoriesToAlwaysCook=` 개수 4 → 5(줄 끝 주석에 `[WP-16 hook] Weather`, WP-19 선례) + 경로 단언 한 줄 |
| `test_ue_wp19_fixture.py`(Claude 레인, D-021 허용 목록) | `ALLOWED_PLUGINS` 정의 다음 줄 `ALLOWED_PLUGINS \|= {"Niagara"}  # [WP-16 hook] engine FX plugin, not Experimental` |
- **고치지 않음**: `Player/*`, `GolmokGameMode`, `DefaultEngine.ini`, `DefaultInput.ini`, `pyproject.toml`, CI, `check_repo.py`, `.gitignore`·`.gitattributes`(`Content/Golmok/`는 이미 추적·LFS), `Debug/`, Astra 레인(`Audio/`, `audio.json`, `Characters/`, `characters.json`과 그 테스트), `lighting_presets.json`·`lighting.py`.

### 16. PC 런북 `docs/runbooks/pc-verify-wp16a.md`(V-16) 개요 — 16a 세션이 쓴다
0. 전제: 16a가 병합된 main, `.uproject`에 Niagara.
1. 빌드: 무수정 통과, 우리 소스 경고 0. Niagara 관련 UBT 경고는 기록(§17 #1).
2. 에셋: (a) `import golmok.weather_setup as w; w.run()` → MPC 생성 로그(실패하면 수동 3개). (b) `NS_GolmokRain` 레시피(§7-4) 단계 표와 스크린샷 1장. (c) 둘 다 커밋(LFS·잠금, `git add -A` 금지).
3. 자동화: `test.ps1` → 39 Success, Weather 3개의 MPC·NS 단계 EXECUTED(Info skip 없음).
4. 상태 머신·전환: `rain heavy` 20 s(하늘이 먼저, 비는 10 s 뒤), `clear`(비가 먼저 그침), `instant`, 단계별 HUD 기대 줄.
5. 조명 룩 매트릭스(판정은 깨짐만, 값은 16b·14b 입력): fixed 06:00·07:30·12:30·18:00·21:30 × clear/overcast/rain 0.3/rain 1.0 스크린샷 20장 + 06:00 rain `ShowFlag.VisualizeHDR`. 깨짐 = 검정·백색 클리핑, 불투명 안개, 태양 깜박임. 엔진 노출 경고는 시각과 함께 기록(→ 14b).
6. 일정: `golmok.tod mode clock`·`rate 10` + `golmok.weather mode schedule`로 한 바퀴, 칸마다 `OnWeatherChanged` 로그 1회.
7. 실내: 포털 진입 → 빗줄기 정지(문간 잔상 관찰), 안개·노출 = 실내 값, 나오면 곧바로 비(warmup).
8. 포토: rain heavy 중 P → 멈춘 빗줄기 촬영, 날씨 변경 거절, 종료 뒤 전환 이어짐, 사진 메타 `weather`.
9. 이동·세이브: `golmok.travel` 뒤 줄무늬 없음. standalone 종료·재시작 복원(상태·강도·젖음·모드), 구 세이브(Rule 0), `golmok.save status`.
10. 성능(§7-5): L_Dev(있으면 `L_Basemap_Yeonnam`도) fixed 12:30 clear vs rain heavy, `stat unit`/`stat gpu`/`stat niagara`. 정적 SkyLight 레벨이면 전환 끝 히치. 예산을 넘으면 `max_spawn_rate` 단계와 값을 기록.
11. 패키지: `package.ps1` → 패키지에서 `golmok.weather rain heavy` → 빗줄기·MPC 로그·`weather.json` 로드.
12. 불확실 API 표(§17)와 결과·실행 기록. 빗소리가 없는 것은 Astra 과제 전이라 정상.

### 17. 위험·[미확인] UE 5.8 API(런북 §12 표로 옮긴다)
| # | 항목 | 확인·대안 |
|---|---|---|
| 1 | `Niagara.uplugin`의 `EnabledByDefault`와, 목록에 없을 때 UBT 경고 문구 | PC: uplugin 파일·빌드 로그. 명시 항목은 어느 쪽이든 무해 |
| 2 | Build.cs 모듈 `Niagara`만으로 `UNiagaraComponent`·`UNiagaraSystem`이 링크되는지(NiagaraCore 공개 전이) | 링크 오류면 같은 훅 블록에 `NiagaraCore` 추가 |
| 3 | 컴포넌트 생성: `NewObject<UNiagaraComponent>` + `SetAsset` + `RegisterComponent`, 또는 `UNiagaraFunctionLibrary::SpawnSystemAttached`(5.8 서명, `ENCPoolMethod`) | 컴파일되는 쪽 |
| 4 | `SetVariableFloat`/`SetVariableVec3` 이름에 `User.` 접두가 필요한지 | 자동화가 override 파라미터 존재를 확인. 안 되면 접두 없는 이름 |
| 5 | `-nullrhi`에서 GPU 이미터 컴포넌트 생성·활성 상태 조회 | 계약만 단언, 시뮬레이션 결과는 PIE GUI |
| 6 | `SetGamePaused`·TimeDilation 포토에서 Niagara가 멈추는지 | 런북 §8. 안 멈추면 포토 진입·종료에 `SetPaused` |
| 7 | GPU 고정 경계 + 월드 공간 + 매 프레임 이동하는 컴포넌트의 컬링 | 경계 여유 500 cm, 사라지면 늘림 |
| 8 | Niagara 모듈 스택을 Python으로 만들 수 있는지 | 16a는 레시피(§7-4). 가능하면 16b에서 생성기 |
| 9 | MPC `scalar_parameters`·`CollectionScalarParameter`를 Python으로 쓰기 | 수동 절차(런북 §2a) |
| 10 | `UWorld::GetParameterCollectionInstance`·`SetScalarParameterValue`(5.8), `-nullrhi`에서 값 읽기 | `UKismetMaterialLibrary::SetScalarParameterValue` |
| 11 | `UTickableWorldSubsystem`의 `IsTickableWhenPaused` false + PIE 틱 | 포토 판정은 `IsActiveIn`으로 겹쳐 둔다 |
| 12 | Niagara `WarmupTime`이 재활성(`Activate(true)`)에도 적용되는지 | 아니면 `AdvanceSimulation` 1회 |
| 13 | soft 경로로만 쓰는 `/Game/Golmok/Weather` 에셋이 `DirectoriesToAlwaysCook`로 패키지에 드는지 | 런북 §11 |
| 14 | 비 + 새벽·저녁 램프에서 엔진 노출 경고(V-13 06:00 −8.8)가 심해지는지 | 기록만 → 14b 노출 범위 키 |
- **품질 위험**: (a) splat(D-010)이면 환경이 Unlit이라 조명 수정자가 캐릭터·베이스맵·안개에만 보인다. 비 표현이 안개·빗줄기·소리에 기대므로 16b에서 PPV 색보정 수정자(채도·대비)를 먼저 검토한다. (b) 차폐가 없어 지붕·차양 아래로 비가 내린다 — 골목에 차양이 많아 눈에 띈다(16b 차폐). (c) 프리셋 `overcast_morning` 위의 날씨 overcast는 이중 흐림(lux 2.5 × 0.3)이다 — 16b에서 프리셋 값·이름을 정리한다(이름은 WP-13 오디오 매핑·세이브 `PresetName`에 걸려 있어 신중히). (d) 같은 일정이 날마다 반복된다(§4). (e) 문간 잔상(§11).
- **운영 위험**: 이진 에셋 2개(PC만 수정), 자동화 총수·등록부 충돌(착수·PR 전 열린 브랜치 확인), 빗소리는 Astra 일정에 달려 있다(V-16은 빗소리 없이).

### 18. 하지 않는 것(16a)
젖은 표면 머티리얼·웅덩이·반사·빗줄기 룩(16b), 차폐(지붕·차양·창밖), 카메라 렌즈 빗방울, 눈·바람·천둥·번개·안개 단독 상태, 무작위·날짜별 일정·실제 기상 API, 포토 모드 날씨 선택 UI(Phase 2), 오디오 구현(Astra), 프리셋 값·이름 변경(14b·16b), 흐림 기본값(16b), `lighting.py`의 에디터 날씨 적용.

### 19. 수용 기준
- **16a 🟡 코드 완료·PC 대기(클라우드)**:
  - §1·§5-4·§6~§15 산출물이 전부 있다(에셋 2개는 PC 몫).
  - **기본(clear·fixed)에서 종전과 같다**: 기존 자동화(`Golmok.Lighting.*`·`Photo.*`·`Audio.*`·`Save.RoundTrip` 등)와 V-03·V-09·V-10·V-13·V-14 런북이 무수정으로 통과한다(clear 항등 비트 동일).
  - MPC·NS가 없는 환경에서 새 자동화 3개가 Success(Info skip)다.
  - pytest·ruff·`check_repo`·`git diff --check`·CI가 초록이고, 적대 검증 1라운드를 반영했다.
  - 런북 V-16, 이 문서 "결과"와 "병합 시 반영" 문안이 있다.
- **16a 🟢(PC V-16)**:
  - 빌드 무수정(우리 소스 경고 0), MPC·NS 저작·커밋.
  - 자동화 39/39(MPC·NS 단계 EXECUTED), 런북 §4~§9 기대 동작, §5 깨짐 0(노출 경고는 기록만).
  - 성능 예산(§7-5) 충족, 또는 데이터로 낮춘 값 기록. 패키지에서 동작.
- 16b는 D-010 뒤 별도(PC look-dev + 소유자 채점), 범위는 §0-1.

## 세션 카드 — 16a 구현(Opus 5.5 ultracode)
오케스트레이터가 이 카드로 세션을 만든다(브랜치 `claude/wp16a-weather`). 이슈 #30의 빗소리 계약 질문을 먼저 올린다.

```
당신은 Golmok WP-16a(날씨 비 16a) 구현 세션이다. Claude Opus 5.5, ultracode(구현 → 적대적 검증 1라운드), D-020.
읽기: CLAUDE.md → docs/DEVELOPMENT-PLAN.md §7(§7.5 코드 규칙, §7.6 레인·핫스팟·훅) → docs/plan/STATUS.md →
docs/plan/WP-16-weather.md "16a 설계 (확정)" 전부 → WP-14 §5와 결과(판단 #3·#18·#19, R51-5) →
WP-15 §3과 "R91-1 후속"(CharacterIdRule 선례).
코드: Lighting/GolmokTimeOfDay.*, Save/*, Photo/GolmokPhotoMath.h·GolmokPhotoModeSubsystem.cpp,
Audio/GolmokAmbienceSubsystem.h(읽기만), Animation/GolmokAnimationSubsystem.cpp(HUD 공급자 선례),
Tests/GolmokTravelSaveTest.cpp, tools/tests의 등록부 테스트(wp09·wp05·wp19·zone fixture, wp12 총수).
브랜치: origin/main에서 claude/wp16a-weather를 만든다. PR은 draft, 병합은 오케스트레이터.
main·astra/*·pc/*에는 push하지 않는다.
착수 전: git fetch origin 뒤 열린 claude/*·astra/*·pc/* 브랜치와 겹침 확인(git diff --stat origin/main...origin/<b>;
특히 Lighting/, Save/, Photo/, 등록부 테스트, DefaultGame.ini, Golmok.uproject, pc-verify-wp12.md).
자동화 총수는 착수 시 main의 실제 수 + 3이다.
STATUS는 자기 WP-16 행만 시작(🔵)·끝(🟡)에 고친다(§7.2). ROADMAP·DECISIONS·DEVELOPMENT-PLAN 문안은
"결과" 끝 "병합 시 반영"에 둔다(오케스트레이터가 옮긴다).
구현: 설계 §1~§15 그대로. 빈틈은 "기본(clear·fixed)에서 종전 동일, Astra 레인 무수정, 핫스팟 최소" 쪽으로
최소 판단하고 "결과"에 번호를 붙여 적는다. 설계를 바꿔야 하면 멈추지 말고 판단으로 기록한 뒤 PR 설명 맨 위에 올린다.
커밋 순서: ① 자기 레인(Weather/·Lighting/·Save/·Photo/·테스트·weather.json·Python)
② 훅(파일마다 `WP-16: hook <파일>`, `WP-16: plugins (Golmok.uproject)`)
③ 런북 docs/runbooks/pc-verify-wp16a.md(V-16)와 이 문서 "결과". 커밋 접두어 `WP-16:`.
하지 않는다: Audio/·audio.json·Characters/·characters.json 수정, Debug/ 수정, 머티리얼 작성,
Niagara·MPC 에셋 생성(PC 몫).
적대 검증(별도 에이전트 2개, 파일 수정 없음):
(1) UE 5.8 컴파일·API·유니티 빌드·UHT·Niagara 링크·훅 정확성
(2) 설계 대조·clear 비트 동일·이벤트 계약·세이브 Rule 0/1·포토 정지·실내·일정 경계·순수 헤더와 Python 일치.
확정·유력 결함은 반영하고 표로 남긴다.
게이트: cd tools && ruff check . && ruff format --check . &&
PYTHONUTF8=1 PYTHONPATH=$PWD python -m pytest -q -p no:cacheprovider && python scripts/check_repo.py,
그리고 git diff --check origin/main...HEAD. UE 빌드·자동화는 PC(V-16)라 상태는 🟡.
이슈 #30의 Astra 답을 확인한다. "상태 방식"이어도 Claude 쪽 API(설계 §9)는 그대로다.
마지막 커밋 메시지에 "다음 세션 인계" 3줄(한 것, 남은 것, 주의).
```

## 결과
### 16a 구현 — 2026-10-04 (Opus 5.5 ultracode, 세션 session_01LBnDxTJqaPHaHe4915uZzk, 브랜치 `claude/wp16a-weather`)
상태: **🟡 코드 완료·PC 검증 대기(V-16)**. UE 빌드·자동화는 클라우드에서 못 돌린다.

**진행**: 오케스트레이터가 공유 계약(`GolmokWeatherMath.h`·`GolmokWeatherConfig.h`·`GolmokWeatherSubsystem.h`·`weather.json`)을 먼저 쓰고, 멀티 에이전트 워크플로로 구현했다(D-020): 구현 4(순수·설정 / 서브시스템·빗줄기 / Lighting / 세이브·포토) → 통합 2(자동화·훅·Python / 런북) → 적대 검증 2(UE 5.8 컴파일·API / 설계 대조, 파일 무수정) → 반영.

**산출물**(설계 §1·§5-4·§6~§15 전부, 에셋 2개는 PC 몫)
- `Source/Golmok/Weather/`: `GolmokWeatherMath.h`(순수), `GolmokWeatherConfig.{h,cpp}`(엄격 파서), `GolmokWeatherSubsystem.{h,cpp}`(상태 머신·일정·표면·MPC·ToD 수정자·콘솔 `golmok.weather`·HUD 공급자), `GolmokWeatherRainFx.{h,cpp}`(Niagara include 유일 파일).
- `Lighting/GolmokTimeOfDay.{h,cpp}`: `SetWeatherModifier`/`GetWeatherModifier`, `ComposeTarget` = 기저 → 날씨(`ApplyWeather`, 항등이면 입력 그대로) → 실내, BeginPlay 끝 비항등 1회 적용. WP-13 훅 블록 무수정.
- `Save/`: `FGolmokSaveWeather{Rule, State, Intensity, Mode, Wetness, Puddle}`, `WeatherRuleNone/V1`, 복원 위치 → 시간대 → 날씨 → 캐릭터, status·load 문구. `Photo/`: 메타 `weather`(preset 다음, 없으면 `null`, version 1 유지).
- 테스트: `Tests/GolmokWeatherTest.cpp`(`Golmok.Weather.Config`·`.Lighting`·`.Runtime`, 등록 36 → **39**), `Golmok.Save.RoundTrip` 날씨 단계, `Golmok.Photo.MetaJson` 16키 갱신. pytest `test_ue_weather_math.py`(g++ 교차 + 무작위 600)·`test_ue_config_weather.py`(공유 오류 표 36 + Python 전용 21, C++ 표와 일치 강제)·`test_ue_python_weather_setup.py`·`test_ue_wp16_fixture.py`, `test_ue_photo_math.py`·드라이버.
- Python: `golmok/weather_pure.py`(순수 규칙·파서 미러), `golmok/weather_setup.py`(MPC 생성·검사, NS 유무 로그).
- 훅(파일별 커밋): `Golmok.Build.cs`(Niagara), `DefaultGame.ini`(쿡 `/Game/Golmok/Weather`), `test_ue_wp09`·`zone`·`wp05`·`wp19` 등록부, `Golmok.uproject` Niagara 항목(`WP-16: plugins`).
- 런북 `docs/runbooks/pc-verify-wp16a.md`(V-16, §0~§13).

**게이트**: `ruff check`·`ruff format --check` 통과, pytest **1702 passed / 3 skipped**, `check_repo.py` OK, `git diff --check` 깨끗.

**구현 판단**(설계 빈틈, "기본 clear·fixed 종전 동일·Astra 레인 무수정·핫스팟 최소" 쪽으로; 설계 변경은 ★ — PR 설명 맨 위)
1. ★ `rain_levels` 범위를 (0, 1]이 아니라 **[0.05, 1]**로 검사한다. (0, 1]이면 `light: 0.01`이 파서를 통과해도 `rain light`가 강도 규칙(§2 [0.05, 1])에 막힌다.
2. 오류 문구 형식 `weather.json: <where>: <reason>`, `<where>`는 `root`·점 경로·`[i]`(예 `schedule[3].time`). 키 집합 오류는 빠진 키(스키마 순서) → 미지 키(코드 포인트 순서)라 파일 키 순서와 무관하다. `schema_version`을 키 집합보다 먼저, `modifiers.clear`를 modifiers 키 집합보다 먼저 본다.
3. C++ 파서는 키를 대소문자 구분으로 찾는다(`FJsonObject` 맵은 대소문자 무시). 한 객체 안에서 대소문자만 다른 키(`mode`/`Mode`)는 엔진이 합쳐 C++·Python 문구가 다를 수 있다 — 공유 표 밖, 수용. 문자열 안 NUL(`"rain\u0000x"`)은 C++도 거절한다(검증 반영).
4. 오브젝트 경로는 `/Game/`로 시작하고 마지막 세그먼트에 `.`(Package.Object)가 있어야 한다.
5. 초기 일정 모드: BeginPlay 때는 시계가 아직 없을 수 있어, 시계를 처음 찾은 스텝이 그 칸으로 **즉시·이벤트 없이** 간다.
6. 같은 목표 재요청은 no-op(이벤트 없음). 전환 중 같은 목표 + `instant`는 전환을 즉시 끝낸다(이벤트 없음). 강도 차 1e-5 이하는 같은 목표(콘솔 float vs 일정 double).
7. 이벤트 `bInstant`는 `instant`일 때와 `transition_seconds` 0일 때 true. 이벤트마다 `weather: OnWeatherChanged <목표> (transition|instant)` 로그 1줄(런북 §6 칸마다 1회 확인용).
8. `SetWeatherModifier`는 ToD의 현재 수정자와 같으면 부르지 않는다(불필요한 하늘 재캡처 방지). `bSettled` true는 착지마다 1회.
9. MPC·Niagara 값은 0.001 넘게 바뀌거나 정확히 0·1에 닿을 때 쓴다(가라앉은 clear가 정확히 0). Niagara User 파라미터는 비활성 중에도 `RainNow`를 따른다.
10. ToD 탐색은 캐시가 없을 때 0.5 s 간격(명령·BeginPlay는 즉시). **R112-U9 후속(#113)**: 강제 탐색이 빗나가면 쿨다운이 0으로 남아 다음 틱에 한 번 더 찾고, 그 실패부터 0.5 s 간격이다. 정상 상태 틱 할당 없음.
11. `ResetRainFx`: 활성이면 카메라로 옮겨 `ResetSystem()`, 아니면 `DeactivateImmediate()`.
12. HUD: clear·overcast는 강도 숫자 없음(`weather: clear | now 0.00 wet … | fixed | fx idle`), 전환 중 `(from <이전 목표> NN%)`, 일정 모드는 모드 칸 `schedule` + ` | schedule next HH:MM …` 또는 ` | schedule no clock`, 날씨 꺼짐은 `weather: off - <오류>`.
13. `surface <w>`만 주면 웅덩이는 현재 값을 새 젖음 이하로 자른다. [0, 1] 밖은 오류.
14. ★ `golmok.weather fx on|off`도 포토 모드 중 **거절**한다(설계 §10은 "변경 명령"만 명시; 멈춘 빗줄기를 지우거나 리셋하면 §7-3 "포토 중 호출 없음"과 어긋남 — 검증 반영).
15. ★ 에셋 없음 경고 2줄(MPC·NS)은 **프로세스당 1회**, 자동화 중에는 `Display`. V-16 전에는 PIE 월드마다 Warning 2개가 기존 자동화·런북 Warning 수를 바꾸기 때문(§19 "종전 동일")이다.
16. Lighting "시계 진행 중" 판정 = `ClockMode != Fixed && bBaseFromClock && IsActorTickEnabled()`. 하나라도 거짓이면 곧바로 `ApplyState`(조용히 버려지지 않음). 직접 쓰기 앞에 `ResolveTargets()`.
17. 세이브: 날씨가 꺼진 실행은 이전 스냅숏의 날씨(보유 중이면 슬롯 값, 아니면 Rule 0)를 유지한다(weather.json 없는 실행이 저장된 비를 지우지 않게). 복원 대기 중에도 슬롯 날씨 유지(캐릭터 선례).
18. 세이브 dirty: 복원 자신의 변경은 dirty 아님(`bRestoringWeather`). 목표 변경 없는 **모드만 변경**도 dirty(스냅숏 비교 — 검증 반영). 젖음만 바뀐 것은 dirty 아님.
19. 손상 세이브 값: rain 강도 [0.05, 1] 밖은 클램프 + 메시지 `(saved intensity X -> Y)`, 비유한 강도는 moderate, 비유한 젖음·웅덩이는 0. 모르는 상태는 clear지만 저장된 표면·모드는 적용.
20. 사진 메타 강도는 소수 2자리(`0.60`, clear·overcast `0.00`) — 기존 고정 소수 관례·HUD와 같다(설계 예 `0.6`과 같은 값).
21. 세이브 서브시스템 헤더에 UENUM 전방 선언을 두지 않고 `AddWeakLambda`로 구독(UHT 위험 회피 — 검증 반영).
22. `weather_setup`: 앞 세 개가 계약 이름·순서·기본 0이면 통과하고 뒤에 더 있는 파라미터는 16b 추가로 로그만. NS 없음은 Warning. Python이 `scalar_parameters`를 못 쓰면 빈 MPC를 저장하고 Error로 §2a 수동 절차를 안내.
23. `test_ue_wp19_fixture.py`의 "WP-19 블록이 DefaultGame.ini 끝" 단언에 새 훅 줄 1개(`tail = tail.split("; [WP-16 hook]")[0]…`)를 더했다(기존 줄 무수정). `test_ue_wp05_fixture.py` 쿡 개수 줄은 WP-19 선례대로 제자리 수정(4 → 5, 줄 끝 `[WP-16 hook]`).
24. 자동화의 알파 민감 구간은 한 latent `Update()` 안에서 `StepWeather`로 손으로 구동한다. `OnTraveled`는 L_Dev에 이동 존이 없어 직접 Broadcast. **R112-U7 후속(#113)**: 이제 Broadcast하지 않는다(세이브 서브시스템의 방문 기록·저장까지 돌았기 때문). 바인딩(`IsBoundToObject`)과 `ResetRainFx()` 횟수를 따로 단언하고, `Traveled` → `ResetRainFx` 연결과 바인딩 대상은 픽스처가 정적으로 본다. 포토 진입은 알파 0.6(비가 이미 내림)에서.
25. 자동화의 NS 단계는 컴포넌트 override 저장소(`ReadUserParameters`, 값 비교)와 **에셋 노출 파라미터**(`HasUserParameters`)를 따로 본다 — `SetVariable*`가 override에 없는 항목을 만들어 버리므로(검증 반영).
26. 런북: 룩 매트릭스 20장은 로컬에 두고 5×4 접촉 시트 1장 + HDR 1장만 커밋. `max_spawn_rate`를 낮추면 그 값을 고정한 테스트 2곳도 같이 고친다. 패키지 경로는 `$pkg`(`GOLMOK_PKG_DIR`) 규칙.
27. V-14 런북(`pc-verify-wp15a.md`)의 복원·저장 로그 예시는 날씨가 켜지면 `tod …` 뒤에 `, weather …`가 붙는다. 그 런북은 열린 PR #107도 고치므로 여기서 수정하지 않고 V-16 §9와 아래 "병합 시 반영"에 둔다. `pc-verify-wp19.md`·`pc-verify-wp15a.md`의 "36개" 총수 줄도 실행 당시 기록이라 두고, 강제되는 `pc-verify-wp12.md`만 39로 고쳤다.

**적대 검증 1라운드**(에이전트 2, 파일 무수정)
| # | 렌즈 | 등급 | 내용 | 조치 |
|---|---|---|---|---|
| R1 | 설계 | 확정 | `Golmok.Photo.MetaJson`이 새 `weather` 키를 모름(예시·15키) | `GolmokPhotoTest.cpp` 예시에 `"weather": null`, 키 16(`MetaKeyCount`), rain 객체 단언 추가 |
| R2 | 설계 | 유력 | 파서가 `FJsonObject::Values`를 `TPair<FString,…>`로 순회 — 5.8은 `FSharedString` 키 | 저장소 선례대로 `const auto&` + `FString Key(*Pair.Key)` |
| R3 | 설계 | 유력 | 포토 중 `fx on|off` 허용 | 거절(판단 14) + 자동화 단언 |
| R4 | 설계 | 가능 | C++/Python 차이: 문자열 NUL, 대소문자 충돌 키, 비BMP 정렬 | NUL은 C++도 거절; 대소문자 충돌·비BMP는 수용·기록(판단 3) |
| R5 | 설계 | 가능 | 모드만 바꾸면 세이브 dirty 아님 | 스냅숏 모드 비교로 dirty(판단 18) |
| R6 | 설계 | 가능 | 에셋 없음 Warning 2개가 PIE 월드마다 → 기존 Warning 수 변화 | 프로세스당 1회·자동화 중 Display(판단 15) |
| R7 | 설계 | 가능 | V-14 런북 로그 예시와 `, weather …` 접미 불일치 | 판단 27, 병합 시 반영 |
| R8 | UE | 가능 | User 파라미터 읽기가 에셋 노출을 증명 못 함 | `HasUserParameters`(에셋 노출 저장소) 추가(판단 25) |
| R9 | UE | 가능 | UCLASS 헤더의 UENUM 전방 선언(UHT) | 제거, `AddWeakLambda`(판단 21) |
| — | UE | — | 확정 컴파일·링크 결함 0(UHT·틱 오버라이드·콘솔·MPC·Niagara API·유니티 이름·축소 변환·섀도잉·포맷 지정자·훅) | — |
| R10 | 런북 | — | 런북이 기대하는 `OnWeatherChanged` 로그가 코드에 없음(통합 에이전트 지적) | 로그 추가(판단 7) |

**[미확인] UE 5.8 API**(런북 §12에 결과 칸): §17 #1~#14 + `DeactivateImmediate`·`ResetSystem`·`FActorSpawnParameters::NameMode`, `UNiagaraSystem::GetExposedParameters`·`FindParameterOffset`, `IsTickable` 오버라이드.

**Astra(빗소리)**: 착수 시점에는 답이 없었고, 이후 이슈 #30 [코멘트 5980334591](https://github.com/wooklym/golmok/issues/30#issuecomment-5980334591)로 답했다(오케스트레이터 확인 [5980906355](https://github.com/wooklym/golmok/issues/30#issuecomment-5980906355)). **레이어 방식**(낮/밤/실내 베드·두 슬롯 유지 + 별도 빗소리 채널, gain 곡선·실내 감쇠는 `audio.json` 데이터, 값은 청취 전 가설), **추가 Weather API 없음**(오디오 틱에서 `GetRainIntensity()`를 읽고 실내는 기존 `OnInteriorChanged`; 서브시스템 없음·꺼짐 → 0, 1프레임 지연 수용), 포토는 `IsFrozen()`으로 오디오를 멈추지 않고 기존 `PhotoGain`·mute 정책, `bInstant`는 §9가 정본. 이 구현의 API가 그대로 맞는다(리뷰 R112-D6). 과제는 Astra T24(병합 뒤 배정).

**겹치는 브랜치**: PR #107(`claude/ue-followups-p14-p04c`)이 `Save/GolmokSaveSubsystem.h`(주석)·`Tests/GolmokTravelSaveTest.cpp`·`tools/tests/fake_unreal.py`를 고친다 — 이쪽 변경은 새 블록·끝 추가라 기계적으로 풀린다. PR #108(Astra, Characters/)과는 겹침 없음.

### 병합 시 반영(오케스트레이터가 공유 문서에 옮긴다)
- **STATUS 트랙 1A WP-16 행**: 이 브랜치가 이미 `🟡 16a 코드 완료·PC 검증 대기(V-16)`로 고쳤다. 병합 뒤 "갱신 이력"에 한 줄: `2026-10-04 WP-16a 구현 병합(#PR) — Weather/ 서브시스템·Niagara 빗줄기·MPC 계약·세이브 Rule 0/1·포토 메타 weather, 자동화 39, pytest 1702; V-16 대기`.
- **STATUS V-16 행**: `⚪ 대기(16a 병합 뒤)` → `⚪ PC 대기 — 런북 runbooks/pc-verify-wp16a.md`. PC 카드 문안: "V-16(WP-16a 날씨): 런북 `pc-verify-wp16a.md` §0~§13, 브랜치 `pc/v16-verify-wp16a`, 에셋 2개(MPC·NS) 저작·커밋(LFS·잠금), 자동화 39."
- **ROADMAP**: WP-16 행 `16a 🟡 코드 완료·PC 검증 대기(V-16)`.
- **DECISIONS**: D-015 진행 기록에 "2026-10-04 WP-16a 구현(오케스트레이터 결정 D-019, 되돌릴 수 있음): 설계 대비 변경 3 — rain_levels [0.05, 1], 포토 중 `fx on|off` 거절, 에셋 없음 경고 프로세스당 1회·자동화 중 Display(WP-16 결과 판단 1·14·15)". D-002: 새 의존 없음(Niagara는 엔진 동봉 1st-party, 설계 §7-1).
- **DEVELOPMENT-PLAN §5.1 WP-16a 행**: 상태 `🟡 코드 완료(2026-10-04)·V-16 대기`.
- **pc-verify-wp15a.md(V-14)** §2·68행 부근: "WP-16a부터 `tod …` 뒤에 `, weather <목표> wet x puddle y <모드>`(또는 `, weather - (not in save)`)가 붙는다" 한 줄(PR #107 병합 뒤 그 브랜치 기준으로).
- **WP-12 문서 §2-2 메타 예시**: `"weather": {"state": "rain", "intensity": 0.60}` 줄(preset 다음).
- **이슈 #30**: 16a 병합 알림 + Astra 빗소리 과제 배정(계약 §9, 답이 오면 그 방식).

### R112 (C) 후속 병합 — [#113](https://github.com/wooklym/golmok/pull/113) (2026-10-04, 오케스트레이터 세션)

**내용**: R112 (C) U6·U7·U8·U9·U11(Claude 레인, 세션 session_015hb8GYCeFDJ7UA37GwNkdR, 브랜치 `claude/wp16a-followups`).
- U6: wp16 픽스처를 견고하게 했다(ini 훅은 WP-19 뒤 연속 블록, `.uproject`는 JSON 파싱, `Debug/` 금지어 `GolmokWeather`·`WP-16`).
- U7: 날씨 Runtime 테스트의 `OnTraveled` 브로드캐스트를 없앴다.
- U8: `Restore`가 위치·시간대·날씨 단계 뒤에 날씨 규칙과 무관하게 빗줄기를 1회 리셋한다(존 이동은 도착 `OnTraveled`, 포토 모드 제외).
- U9: 강제 시간대 탐색이 비면 다음 틱에 다시 찾는다.
- U11: `NightUnaffected` 시각을 프리셋에서 찾는다(기본 05:35).
- 등록 39 불변. U4·U5는 V-16 결과 뒤.

**병합 전 리뷰(Opus 5.5 적대 리뷰, [R113](https://github.com/wooklym/golmok/pull/113#issuecomment-5982025179))**: (A) 0 · (B) 2 · (C) 5. U6 픽스처 변이 약 30개를 돌려 의도한 완화만 통과했다. 생존한 바인딩·`Restore` 리셋 제거는 R113-5 needle로 막았다. 반영 커밋 `608234a`의 내용은 다음과 같다.
- R113-1: 런북 §3 U7 줄은 `GolmokSave: first visit weather_test`가 없는지로 판정한다. `weather_test`는 실내 단계 로그에 정상으로 나온다.
- R113-2: `NightUnaffected at …` Info 줄과 기대값 `05:35 (base lux 0.104167)`.
- R113-3: §9 U8·§12 #20에 "1 s쯤 성기게 시작" 증상.
- R113-5: 정적 needle 2개.
- R113-7: 주석.
- R113-4: 위 결과 #10·#24를 이 커밋에서 갱신했다.
- R113-6(건너뛸 때 이벤트 0 단언도 빠짐)은 선택으로 이월했다.

게이트(리눅스, Astra T24 #114 병합 뒤 main과 합친 트리): ruff, format, pytest 1752 passed / 3 skipped, check_repo, `diff --check`, 등록 39.

**병합**: 오케스트레이터 결정(D-019). 최신 main을 합친 뒤 이 커밋으로 반영했다. PC 확인은 V-16 `pc-verify-wp16a.md` §3·§4·§9·§12 #17~#20이다.
