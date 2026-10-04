# PC 검증 런북 — WP-16a 날씨(비): 상태·조명 수정자·빗줄기·계약 (V-16)

상태: ⚪ **PC 미검증**(WP-16a 🟡 코드 완료·PC 검증 대기). 스펙·결과: [`plan/WP-16-weather.md`](../plan/WP-16-weather.md) "16a 설계 (확정)"(이하 "설계 §n").

대상: PC Claude 세션(또는 사용자). 브랜치 `pc/v16-verify-wp16a` ← 16a가 병합된 origin/main.
전제: V-03(WP-05 조명)·V-09(포토)·V-13(WP-14a 시간대)·V-14(WP-15a 이동·세이브) 🟢인 PC. `L_Dev`(`golmok.setup_dev_level`)와 `L_ZoneTest`(+ `synthetic_zone.run(interior=True)`의 실내 서브레벨)가 있다. `cd tools && PYTHONUTF8=1 python -m pytest -q` 초록. `Golmok.uproject` `Plugins`에 `{"Name": "Niagara", "Enabled": true}`가 있다(16a 커밋 `WP-16: plugins (Golmok.uproject)`).
소요: 빌드 10~20분 + 에셋 저작 30분 + 헤드리스 15분 + PIE 검증 90분 + 성능 20분 + 패키지 30분. 결과는 이 문서 §13과 `docs/plan/STATUS.md`(V-16 행, WP-16 행)에 적는다.

클라우드 세션은 UE를 컴파일할 수 없었다. **컴파일·링크 에러가 나면 §12 표를 보고 고친 뒤 커밋**한다(`WP-16a: PC fix …`). 설계 의도를 바꾸는 수정이면 `docs/plan/WP-16-weather.md` "결과"에 한 줄 적는다.

**빗소리(2026-10-04 갱신)**: Astra T24 [#114](https://github.com/wooklym/golmok/pull/114)가 병합되어 main에는 빗소리 레이어가 있다(낮/밤/실내 베드 위 별도 rain 채널, 실제 `GetRainIntensity()`를 읽고 실내에서 ×0.35로 줄어든다). 16a 자체는 `Audio/`·`audio.json`을 고치지 않았다(설계 §9). V-16은 빗소리의 **밸런스·가림을 판정하지 않는다** — 플레이스홀더가 베드와 같은 저역 노이즈라 판정할 수 없다(R114-1). 비가 오고 그칠 때 클릭·급정지 같은 깨짐만 결과에 적는다. 청취·패키지 검증은 V-16 뒤 `pc-verify-wp13.md` §9 카드, 최종 밸런스는 C-08이다. HUD `audio:` 줄 끝에 `rain`(실제 강수)·`rain_gain`(채널 배율)이 붙는다.

**16b 전 정상인 것**: 빗줄기는 엔진 기본 스프라이트 머티리얼의 자리표시(흰 막대)이고, 지붕·차양 아래로도 내리며(차폐 없음), 바닥은 젖어 보이지 않는다(MPC 값만 공급하고 바인딩하는 머티리얼이 없다). 수정자 값(lux·안개·색온도·노출)은 가설값이다. 이 런북은 **상태·전환·계약·활성 규칙·깨짐·예산**만 보고, 룩 판정은 16b·14b의 입력으로 기록만 한다.

규칙:
- 기대 로그·HUD·메시지는 코드(`Weather/GolmokWeatherSubsystem.cpp`, `Weather/GolmokWeatherRainFx.cpp`, `Save/GolmokSaveSubsystem.cpp`, `Photo/GolmokPhotoMath.h`)의 `UE_LOG`/`Printf` 형식에 `Config/Golmok/weather.json` 값을 넣은 것이다. `x.xx`·`…`는 PC에서만 정해지는 값이다. 콘솔 결과는 전부 `LogGolmok: weather: …`로 찍히고, 오류는 `LogGolmok: Warning: weather: …`다.
- 시간 기준: 날씨 전환은 **월드 초 20 s**(`transition_seconds`) smoothstep이고 시간대 시계 배율과 무관하다. 비가 늘 때는 하늘이 먼저(α 0.5 = 10 s까지 `now 0.00`), 줄 때는 비가 먼저 그친다(α 0.5 = 10 s에 `now 0.00`). HUD 퍼센트 = 반올림(α × 100).
- 수정자 기대값(`golmok.weather status`의 `modifier` 줄, 설계 §5-2. Rain(I) = log2 공간 Lerp(overcast, rain, I)):

| 날씨 | `modifier` 줄 |
|---|---|
| clear(항등) | `lux 1.000 sky 1.000 fog 1.000 falloff 1.000 kelvin 6500 weight 0.00 exposure 0.00` |
| overcast | `lux 0.300 sky 1.000 fog 1.400 falloff 0.800 kelvin 6800 weight 0.50 exposure -0.20` |
| rain 0.30 (light) | `lux 0.228 sky 0.935 fog 1.558 falloff 0.734 kelvin 6920 weight 0.56 exposure -0.26` |
| rain 0.60 (moderate) | `lux 0.173 sky 0.875 fog 1.734 falloff 0.673 kelvin 7040 weight 0.62 exposure -0.32` |
| rain 1.00 (heavy) | `lux 0.120 sky 0.800 fog 2.000 falloff 0.600 kelvin 7200 weight 0.70 exposure -0.40` |

- **구 세이브 백업(§9 Rule 0용, 맨 먼저)**: 이 빌드로 PIE·`-game`을 한 번이라도 돌리면 `golmok_auto.sav`가 Rule 1로 다시 쓰인다. §1 전에 `<Project>\Saved\SaveGames\golmok_auto.sav`(`<Project>` = `unreal\Golmok`)가 있으면 `golmok_auto.pre-wp16a.sav`로 복사해 둔다(커밋하지 않음). 없으면 §9 Rule 0 단계는 자동화 근거만으로 적는다.

## 0. 바뀐 파일
| 파일 (`unreal/Golmok/` 기준, 그 외 저장소 기준) | 내용 |
|---|---|
| `Source/Golmok/Weather/GolmokWeatherMath.h` (새) | 순수 규칙: 상태 이름, 수정자 `Apply`·log2 `Lerp`·`ForState`, smoothstep·강수 지연 `PrecipAt`, 표면 적분 `StepSurface`, 일정 `ScheduleIndexAt`, 계약 상수(MPC 3·User 파라미터 3). g++ 교차검증 `tools/tests/test_ue_weather_math.py` |
| `Source/Golmok/Weather/GolmokWeatherConfig.{h,cpp}` (새) | `weather.json` 파서(전부 아니면 아무것도, Python `weather_pure.py`와 같은 오류 문구) |
| `Source/Golmok/Weather/GolmokWeatherSubsystem.{h,cpp}` (새) | `UGolmokWeatherSubsystem`(Game·PIE 월드): 상태 머신·일정·표면·MPC 쓰기·시간대 수정자 전달·`OnWeatherChanged`·콘솔 `golmok.weather`·HUD 공급자(`AddExtraHudLineProvider`, `Debug/` 무수정) |
| `Source/Golmok/Weather/GolmokWeatherRainFx.{h,cpp}` (새) | Niagara를 include하는 유일한 파일. transient 액터 `GolmokWeatherFx` + `UNiagaraComponent`, User 파라미터 쓰기·활성·리셋 |
| `Source/Golmok/Lighting/GolmokTimeOfDay.{h,cpp}` | `SetWeatherModifier`/`GetWeatherModifier`, `ComposeTarget`에서 기저 다음·실내 오버레이 앞에 날씨 한 단계(설계 §5-3·§5-4). WP-13 훅 블록 무수정 |
| `Source/Golmok/Save/GolmokSaveGame.h`, `GolmokSaveSubsystem.{h,cpp}` | `FGolmokSaveWeather{Rule, State, Intensity, Mode, Wetness, Puddle}`, 복원 순서 위치 → 시간대 → **날씨** → 캐릭터, `OnWeatherChanged` → dirty |
| `Source/Golmok/Photo/GolmokPhotoMath.h`, `GolmokPhotoModeSubsystem.cpp` | 사진 메타 `"weather"` 키(`preset` 다음, 메타 version 1 유지) |
| `Source/Golmok/Tests/GolmokWeatherTest.cpp` (새), `GolmokTravelSaveTest.cpp` | 자동화 `Golmok.Weather.Config`·`Lighting`·`Runtime`, `Golmok.Save.RoundTrip`에 날씨 단계(등록 수 불변) |
| `Config/Golmok/weather.json` (새) | 단일 소스(설계 §6). `initial` clear·fixed(종전 동일) |
| `Content/Python/golmok/weather_pure.py`·`weather_setup.py` (새) | 순수 Python 규칙·파서, 에디터 MPC 생성기 |
| 훅(별도 커밋) | `Golmok.uproject` Niagara, `Golmok.Build.cs` `[WP-16 hook]` `PrivateDependencyModuleNames.Add("Niagara");`, `Config/DefaultGame.ini` `[WP-16 hook]` `+DirectoriesToAlwaysCook=(Path="/Game/Golmok/Weather")`, 등록부 테스트 |

R112 후속(`claude/wp16a-followups`, 리뷰 R112 (C)): `GolmokWeatherSubsystem.{h,cpp}`(U9 첫 시간대 탐색, `GetRainFxResetCount`), `GolmokSaveSubsystem.cpp`(U8 복원 뒤 빗줄기 리셋 1회), `GolmokWeatherTest.cpp`(U7 `OnTraveled` 브로드캐스트 제거, U11 `NightUnaffected` 분을 프리셋에서 찾음), `GolmokTravelSaveTest.cpp`(U8 리셋 횟수 단언), `tools/tests/test_ue_wp16_fixture.py`(U6). 자동화 등록 수 39 불변. 확인 줄은 §3·§4·§9·§12 #17~#20.

PC가 만드는 것: `Content/Golmok/Weather/MPC_GolmokWeather.uasset`, `Content/Golmok/Weather/NS_GolmokRain.uasset`(§2). `DefaultEngine.ini`·`DefaultInput.ini`·Player·GameMode·`Debug/`·Astra 레인은 **바뀌지 않았다**.

## 1. 빌드
```powershell
git pull
.\tools\ue\build.ps1
```
- [ ] 컴파일·링크 오류 0, **프로젝트 소스 경고 0**(엔진 헤더 C4996은 종전처럼 무시). 오류가 나면 §12.
- [ ] Niagara 관련 UBT 경고 문구가 있으면 그대로 기록(§12 #1). `Niagara` 모듈 링크 오류(`UNiagaraComponent`·`FNiagaraVariable` 미해결 외부 기호)면 §12 #2: 같은 훅 블록에 `PrivateDependencyModuleNames.Add("NiagaraCore");`를 더한다(`test_ue_wp09_fixture.py`의 `BUILD_CS_PRIVATE` 훅 줄도 함께). 같은 `WP-16a: PC fix` 커밋에서 `tools/tests/test_ue_wp16_fixture.py`의 `BUILD_CS_HOOK`(정확한 3줄)과 `"NiagaraCore" not in` 단언도 함께 고친다(그대로 두면 CI가 빨개진다, 리뷰 R112-U2).
- [ ] `.\tools\ue\open-editor.ps1` → 에러 없이 열림(Niagara 플러그인 활성 대화상자 없음).

## 2. 에셋 저작(PC만 고치는 이진 에셋 2개)
에셋 폴더 `/Game/Golmok/Weather`(= `unreal/Golmok/Content/Golmok/Weather/`). 저작 전 에디터 Output Log에서 PIE를 한 번 돌리면 다음 Warning 2줄이 나온다(에셋 없음 폴백, 설계 §7-6 — 정상). 두 줄은 **프로세스당 1회**이고(두 번째 PIE부터는 없음), 자동화 실행 중(`GIsAutomationTesting`)에는 Warning이 아니라 `Display`로 찍혀 기존 테스트의 Warning 수를 바꾸지 않는다(구현 판단 #R6):
```
LogGolmok: Warning: weather: MPC missing (/Game/Golmok/Weather/MPC_GolmokWeather.MPC_GolmokWeather) - wetness / puddles stay in the subsystem only
LogGolmok: Warning: weather: rain fx missing (/Game/Golmok/Weather/NS_GolmokRain.NS_GolmokRain) - rain is lighting/MPC/audio only
LogGolmok: weather: clear fixed, transition 20.0 s, 10 schedule slots, mpc missing, fx missing
```

### 2a. MPC `MPC_GolmokWeather`
에디터 Output Log → Python:
```python
import golmok.weather_setup as w; w.run()
```
- [ ] 다음 2줄이 나온다(NS 경고는 §2b 전이라 정상). Error 없음.
  ```
  LogPython: weather_setup: /Game/Golmok/Weather/MPC_GolmokWeather created (RainIntensity, Wetness, PuddleAmount, default 0)
  LogPython: Warning: weather_setup: /Game/Golmok/Weather/NS_GolmokRain missing - author it with runbook pc-verify-wp16a §2b
  ```
  Python이 `scalar_parameters`를 못 쓰면 `LogPython: Error: weather_setup: /Game/Golmok/Weather/MPC_GolmokWeather created but … - add …`가 나온다 → 아래 수동 절차로 3개를 넣는다(§12 #9).
- [ ] 다시 `w.run()` → `weather_setup: /Game/Golmok/Weather/MPC_GolmokWeather ok (RainIntensity, Wetness, PuddleAmount, default 0)`(멱등, 고치지 않음). 에셋 수정 표시(*)가 생기지 않는다.
- [ ] 에셋을 열어 Scalar Parameters가 정확히 3개, 순서·이름·기본값이 `RainIntensity` 0 / `Wetness` 0 / `PuddleAmount` 0인지 본다(Vector Parameters 0개).
- **수동 절차(Python이 `scalar_parameters`를 못 쓸 때, §12 #9)**: 콘텐츠 브라우저 `/Game/Golmok/Weather` → 우클릭 → Materials → **Material Parameter Collection** → 이름 `MPC_GolmokWeather` → 열기 → Scalar Parameters `+` 3번 → 이름 `RainIntensity`·`Wetness`·`PuddleAmount`(이 순서, 대소문자 정확), Default Value 0 → 저장. 이후 `w.run()`이 불일치 Error 없이 "있음"으로 끝나야 한다. 어느 쪽을 썼는지 §13에 적는다.

### 2b. Niagara 시스템 `NS_GolmokRain`(자리표시, 룩은 16b)
Niagara 모듈 스택은 Python 생성이 확인되지 않아(§12 #8) Niagara 에디터로 한 번 만든다. 값은 설계 §7-4 그대로다.

| 단계 | 위치 | 설정 |
|---|---|---|
| 1 | 콘텐츠 브라우저 `/Game/Golmok/Weather` → 우클릭 → FX → **Niagara System** | "Create empty system"(또는 "New system from selected emitters" → **Empty** 이미터 템플릿 1개). 이름 `NS_GolmokRain`. 빈 시스템이면 `+ Emitter` → Empty 1개. 이미터는 **1개만** |
| 2 | System Properties | **Warmup Time 1.0** s(Warmup Tick Count는 자동). **Fixed Bounds** 켬: Min (−1500, −1500, −1000), Max (1500, 1500, 1000) cm(= ±(BoxHalfExtent (1000, 1000, 500) + 500)) |
| 3 | User Parameters(Parameters 패널 → User Exposed `+`) | `RainIntensity` **float** 기본 0, `SpawnRate` **float** 기본 0, `BoxHalfExtent` **Vector**(vec3) 기본 (1000, 1000, 500). 패널에는 `User.` 접두로 보인다. 이름 대소문자 정확(코드 상수 `User.RainIntensity`·`User.SpawnRate`·`User.BoxHalfExtent`) |
| 4 | Emitter Properties | **Sim Target = GPUCompute Sim**, **Local Space 끔**(월드 공간), Calculate Bounds Mode = **Fixed**, Fixed Bounds = 단계 2와 같은 값 |
| 5 | Emitter Update | **Spawn Rate** 모듈(없으면 추가) → SpawnRate 입력을 `User.SpawnRate`에 연결(링크 드롭다운 → User → SpawnRate). Emitter State는 기본(Loop Behavior Infinite) |
| 6 | Particle Spawn — Initialize Particle | Lifetime Mode Direct Set, **Lifetime 1.0** s. Sprite Size Mode **Non-Uniform**, Sprite Size **(1, 60)** cm |
| 7 | Particle Spawn — **Shape Location** | Shape Primitive **Box**, Box Size = **2 × `User.BoxHalfExtent`**(Box Size 입력 → 동적 입력 Multiply Vector By Float: Vector `User.BoxHalfExtent`, Float 2.0) |
| 8 | Particle Spawn — **Add Velocity** | Velocity Mode Linear, Velocity = 동적 입력 **Uniform Ranged Vector** Min (0, 0, −1100) Max (0, 0, −900) cm/s(−1000 ± 10 %) |
| 9 | Particle Update | **Solve Forces and Velocity** 있음(Empty 템플릿 기본). 중력·Drag 모듈은 넣지 않는다 |
| 10 | Render — **Sprite Renderer** | Alignment **Velocity Aligned**, Material = 엔진 기본 `DefaultSpriteMaterial`(자리표시) |
| 11 | 컴파일·저장 | 툴바 Compile → 경고·오류 0 → Save. 미리보기 뷰포트에서 `User.SpawnRate`를 임시로 12000으로 두면 박스 안에 흰 줄무늬가 아래로 떨어진다 — 확인 뒤 **기본값 0으로 되돌리고** 저장 |

- [ ] Niagara 에디터 스크린샷 1장(시스템 개요 + 이미터 스택이 보이게) → `docs/runbooks/pc-verify-wp16a-ns.jpg`.
- [ ] `w.run()` 한 번 더 → NS가 없다는 로그가 더는 나오지 않는다.
- [ ] PIE 한 번 → §2 첫머리의 Warning 2줄이 **없고** 시작 로그가
  ```
  LogGolmok: weather: clear fixed, transition 20.0 s, 10 schedule slots, mpc ok, fx idle
  ```

### 2c. 커밋(LFS·잠금)
```powershell
git check-attr filter lockable -- unreal/Golmok/Content/Golmok/Weather/MPC_GolmokWeather.uasset unreal/Golmok/Content/Golmok/Weather/NS_GolmokRain.uasset
git add unreal/Golmok/Content/Golmok/Weather/MPC_GolmokWeather.uasset unreal/Golmok/Content/Golmok/Weather/NS_GolmokRain.uasset
git status --short
git commit -m "WP-16a: PC assets MPC_GolmokWeather, NS_GolmokRain (V-16)"
git lfs ls-files | Select-String "Golmok/Weather"
git push -u origin pc/v16-verify-wp16a
git lfs lock unreal/Golmok/Content/Golmok/Weather/MPC_GolmokWeather.uasset
git lfs lock unreal/Golmok/Content/Golmok/Weather/NS_GolmokRain.uasset
```
- [ ] `check-attr`가 `filter: lfs`·`lockable: set`. `git status --short`에 위 두 파일 말고 스테이징된 것이 **없다**. **`git add -A`·`git add .` 금지**(엔진이 만든 `Saved/`·`Intermediate/`·다른 에셋 변경이 섞인다). `git lfs ls-files`에 두 파일.
- [ ] 잠금은 PC 세션 몫이다(이 두 에셋은 PC 세션만 고친다, 설계 §7-4·§8). 잠금이 거부되면(서버 미지원 등) 그 메시지를 §13에 적고 계속한다.

## 3. 헤드리스 자동화
에디터를 닫고:
```powershell
.\tools\ue\test.ps1 -Filter Golmok.Weather
.\tools\ue\test.ps1 -Filter Golmok.Save
.\tools\ue\test.ps1 -Filter Golmok. -SetupDevLevel
```
- [ ] 첫 명령: 3개(`Golmok.Weather.Config`·`Golmok.Weather.Lighting`·`Golmok.Weather.Runtime`) 전부 `Success`(`-nullrhi`).
- [ ] **MPC·NS 단계가 EXECUTED**: `Golmok.Weather.Runtime`의 `[Info]`에 `MPC_GolmokWeather missing - skipped`나 NS 없음 skip 줄이 **없다**(§2 전에는 그 Info로 Success — 설계 §19). MPC 인스턴스 값 == 조회 값(±1e-3), 컴포넌트·User 파라미터 3개 존재·활성 규칙 단언이 실제로 돈다. `-nullrhi`에서 GPU 이미터 활성 조회가 막혀 다른 Info·Warning이 나오면 그대로 §12 #5에 적는다.
- [ ] `Golmok.Save.RoundTrip` `Success`(날씨 단계 포함: Rule 1 왕복 다섯 값, Rule 0 슬롯 → 날씨 유지, 두 복원 모두 `rain fx reset once`(R112-U8), 모르는 상태 `snow` → clear, Schedule 모드는 시간대 뒤 복원). 날씨 단계가 Info로 건너뛰어졌으면(`weather` 서브시스템 없음·꺼짐) 실패로 본다.
- [ ] `Golmok.Weather.Lighting`의 `NightUnaffected` 단계(R112-U11)가 **건너뛰지 않았다**: `[Info]`에 `no minute with base lux in … - NightUnaffected skipped`가 없고 `NightUnaffected at hh:mm (base lux …)` 줄이 있다(통과한 단언의 문구는 보고서에 나오지 않으므로 이 Info 줄로 본다). 그 시각을 §13에 적는다(0~1439분 중 처음 맞는 분 — 오늘 프리셋이면 `05:35 (base lux 0.104167)`, night 유지가 끝난 05:30 뒤 새벽 램프 초입). 14b가 night lux를 바꾼 뒤에도 같은 확인.
- [ ] `Golmok.Weather.Runtime`의 이동 리셋 단계(R112-U7, NS 있을 때): `the weather subsystem is bound to OnTraveled`·`ResetRainFx counted once` 실패 줄이 없다. 실행 로그에 `GolmokSave: first visit weather_test`가 **없다**(브로드캐스트를 하지 않으므로 세이브 서브시스템의 방문 기록·저장이 돌지 않는다. `TimeOfDay: interior overlay on (source weather_test, …)`는 실내 단계의 정상 줄이다).
- [ ] 세 번째 명령: **39개** 전부 `Success`(WP-12 런북 `pc-verify-wp12.md` "두 번째 명령" 줄의 목록 = 기존 36 + `Weather.*` 3). `test.ps1`의 `Succeeded:`는 Warning 있는 테스트를 따로 세므로 상태 열로 판정(V-03). 기존 `Golmok.Lighting.*`·`Photo.*`·`Audio.*`·`Portal.*`가 무수정 통과하는 것이 "clear 항등 비트 동일"(설계 §5-1)의 근거다.

## 4. PIE — 상태 머신·전환(L_Dev)
`L_Dev` PIE, `F1`로 HUD.
- [ ] 시작 HUD에 날씨 줄 1개(`UGolmokDebugSubsystem::AddExtraHudLineProvider` 추가 줄 — 위치·색은 Debug 쪽 규칙 그대로, §13에 적는다):
  ```
  weather: clear | now 0.00 wet 0.00 puddle 0.00 | fixed | fx idle
  ```
  키 **2** → 2 s 뒤 `tod: clear_noon 12:30 fixed`. 날씨 줄은 그대로.
- [ ] **늦게 생기는 시간대의 첫 프레임(R112-U9)**: `Config/Golmok/weather.json` `initial`을 로컬에서만 `{"state": "rain", "intensity": 1.0, "mode": "fixed"}`로 바꾸고(커밋하지 않음) 레벨에 `AGolmokTimeOfDay`가 **배치되지 않은** 레벨(플레이어 컨트롤러가 `FindOrSpawn`으로 만드는 경우 — `L_ZoneTest`에 배치돼 있으면 World Outliner에서 지운 임시 사본 레벨)로 PIE 시작 → 시작 화면이 처음부터 비 조명이다(맑은 조명이 0.5 s 번쩍인 뒤 어두워지지 않음). 의심되면 `-game` + `stat unit`/화면 녹화로 첫 30프레임을 본다. 끝나면 `weather.json`을 되돌린다(`git checkout -- unreal/Golmok/Config/Golmok/weather.json`). [추정] `OnWorldBeginPlay`가 액터 BeginPlay 앞이고 첫 날씨 틱이 컨트롤러 BeginPlay 뒤라는 엔진 순서(§12 #19).
- [ ] `golmok.weather` (= `status`) →
  ```
  LogGolmok: weather: target clear | current settled
    modifier lux 1.000 sky 1.000 fog 1.000 falloff 1.000 kelvin 6500 weight 0.00 exposure 0.00
    rain now 0.000 | wet 0.000 | puddle 0.000
    mode fixed | schedule: now 08:30 clear, next 13:00 overcast
    mpc ok | fx idle | interior no | frozen no
  ```
  (Fixed 모드여도 시각이 있으면 일정 칸을 보여 준다. 키 2 전 레벨 조명이면 `mode fixed | schedule: no clock`.)
- [ ] **비 시작** `golmok.weather rain heavy` →
  ```
  LogGolmok: weather: rain 1.00 over 20.0 s
  LogGolmok: weather: OnWeatherChanged rain 1.00 (transition)
  ```
  스톱워치로 HUD를 본다(값은 60 fps 시뮬레이션 기준, ±1 프레임):

  | 경과 | HUD 기대 | 화면 |
  |---|---|---|
  | 5 s | `weather: rain 1.00 (from clear 25%) \| now 0.00 wet 0.00 puddle 0.00 \| fixed \| fx idle` | 하늘·태양이 어두워지기 시작, 빗줄기 없음 |
  | 10 s | `… (from clear 50%) \| now 0.00 … \| fx idle` | 반쯤 어두움, 아직 비 없음 |
  | 12 s | `… (from clear 60%) \| now 0.10 wet 0.00 … \| fx on` | 빗줄기 시작(성김) |
  | 15 s | `… (from clear 75%) \| now 0.50 wet 0.02 puddle 0.00 \| fixed \| fx on` | |
  | 20 s | `weather: rain 1.00 \| now 1.00 wet 0.08 puddle 0.01 \| fixed \| fx on`(puddle 0.01~0.02) | 전환 끝, 이후 젖음이 1분에 걸쳐 1로 |

  - [ ] 하늘이 **먼저** 어두워지고 비는 약 **10 s 뒤**에 온다(설계 §3 강수 지연). 조명 변화에 계단·깜박임이 없다. 태양 방향·그림자 방향은 바뀌지 않는다(수정자는 회전을 건드리지 않는다).
  - [ ] HUD `tod:` 줄은 `tod: clear_noon 12:30 fixed` 그대로(날씨는 프리셋 이름·밤 판정을 바꾸지 않는다).
  - [ ] 끝난 뒤 `status`의 `modifier` 줄 = 위 표 rain 1.00, `current settled`, `fx on`.
- [ ] **비 그침** (비 전환 끝나고 20 s쯤 뒤) `golmok.weather clear` → `weather: clear over 20.0 s` + `weather: OnWeatherChanged clear (transition)`. 5 s에 `weather: clear (from rain 1.00 25%) | now 0.50 …| fx on`, 10 s에 `now 0.00 … | fx idle`(비가 **먼저** 그침, 남은 줄무늬는 수명 1 s 안에 사라짐), 하늘은 20 s까지 계속 갠다. 젖음은 그 뒤 천천히(10분에 0) 준다 — HUD `wet`이 줄어든다.
- [ ] **즉시** `golmok.weather rain light instant` → `weather: rain 0.30 (instant)` + `weather: OnWeatherChanged rain 0.30 (instant)`. HUD가 곧바로 `weather: rain 0.30 | now 0.30 … | fixed | fx on`, 빗줄기가 곧바로 화면 위아래 전체에 있다(warmup, §12 #12).
- [ ] 같은 목표: `golmok.weather rain light` → `weather: already rain 0.30`(이벤트 줄 없음). `golmok.weather rain heavy` 직후(전환 중) `golmok.weather rain heavy instant` → `weather: rain 1.00 (transition finished now)`(이벤트 줄 없음, 곧바로 끝 값).
- [ ] **진행 중 재목표**: `golmok.weather clear instant` → `golmok.weather rain heavy` → 5 s 뒤 `golmok.weather overcast` → HUD `weather: overcast (from rain 1.00 0%)`부터 다시 20 s, 화면이 **튀지 않는다**(그 순간 값에서 출발).
- [ ] `golmok.weather rain 0.42` → `weather: rain 0.42 over 20.0 s`. `golmok.weather rain moderate`·`golmok.weather rain` → 둘 다 0.60.
- [ ] 표면: `golmok.weather surface 0.8 0.5` → `weather: surface wet 0.80 puddle 0.50`. `golmok.weather surface 0.3` → `weather: surface wet 0.30 puddle 0.30`(웅덩이는 젖음 이하로 잘림). fx: `golmok.weather fx off` → `weather: fx off`(빗줄기 사라짐, HUD `fx off`), `golmok.weather fx on` → 비가 오고 있으면 `weather: fx on`, 아니면 `weather: fx idle`.
- [ ] 오류(전부 Warning, 상태 불변):
  ```
  golmok.weather rain 0.01      -> weather: rain intensity must be light|moderate|heavy or a number in [0.05, 1], got '0.01'
  golmok.weather rain heavy now -> weather: unknown word 'now' (golmok.weather rain [light|moderate|heavy|<0.05~1>] [instant])
  golmok.weather clear now      -> weather: unknown word 'now' (golmok.weather clear [instant])
  golmok.weather mode dusk      -> weather: mode must be fixed|schedule, got 'dusk'
  golmok.weather surface 2      -> weather: surface takes <wetness> [puddle], numbers in [0, 1]
  golmok.weather fx             -> weather: fx must be on|off, got ''
  golmok.weather snow           -> weather: unknown command 'snow'
                                   weather: usage: golmok.weather [status] | clear|overcast [instant] | rain [light|moderate|heavy|<0.05~1>] [instant] | mode fixed|schedule | list | surface <wetness> [puddle] | fx on|off
  ```
- [ ] PIE를 끄고 에디터 콘솔에서 `golmok.weather` → `LogGolmok: Warning: golmok.weather: no game world`.

## 5. 조명 룩 매트릭스(판정은 깨짐만)
L_Dev PIE, 캐릭터를 한자리에 세우고 카메라를 고정(같은 구도). `golmok.tod mode fixed` 뒤 시각마다 `golmok.tod time HH:MM`(2 s 전환 끝까지 기다림) → 날씨 4종을 **instant**로 바꾸며 각 3 s 뒤(자동 노출 안정) 스크린샷.
```
golmok.tod mode fixed
golmok.tod time 06:00
golmok.weather clear instant      -> HighResShot 1920x1080
golmok.weather overcast instant   -> HighResShot 1920x1080
golmok.weather rain 0.3 instant   -> HighResShot 1920x1080
golmok.weather rain 1.0 instant   -> HighResShot 1920x1080
(07:30, 12:30, 18:00, 21:30 반복)
```
- [ ] 20장: 시각 06:00·07:30·12:30·18:00·21:30 × clear/overcast/rain 0.3/rain 1.0. 원본은 `<Project>\Saved\Screenshots\WindowsEditor\`에 두고(커밋하지 않음) 파일 이름을 `look-<HHMM>-<clear|overcast|rain03|rain10>.png`로 바꾼다. 5행(시각) × 4열(날씨) 한 장으로 줄여 `docs/runbooks/pc-verify-wp16a-look-matrix.jpg`로 커밋(긴 변 ≤ 2400 px).
- [ ] 06:00 rain 1.0에서 `ShowFlag.VisualizeHDR 1` 스크린샷 1장 → `docs/runbooks/pc-verify-wp16a-hdr-0600-rain.jpg`, 끝나면 `ShowFlag.VisualizeHDR 0`.
- [ ] **깨짐 판정**(이것만 차단): 화면 전체 검정 또는 백색 클리핑(21:30 night는 14b 전 원래 매우 어둡다 — clear와 비교해 **날씨 때문에** 새로 생긴 것만), 앞이 안 보이는 불투명 안개, 태양·그림자 깜박임, 날씨 변경 순간 노출 튐(즉시 변경은 한 번 바뀌는 것이 정상). 깨짐이 있으면 시각·날씨·스크린샷을 §13에.
- [ ] **엔진 노출 경고**(화면 붉은 글씨 `…lighting is going to be clipped. … Exposure: x.x. Safe exposure range: [-8.0, 12.0].`)는 판정에 넣지 않고 **시각·날씨·Exposure 값**을 §13 표에 기록한다(V-13 06:00 clear −8.8 기준, 설계 §5-3 → 14b 노출 범위 키 입력, §12 #14).
- [ ] 룩 메모(판정 아님, 16b 입력): overcast_morning(07:30) 위 overcast의 이중 흐림, rain에서 캐릭터·베이스맵만 어두워 보이는지, 자동 노출이 수정자를 얼마나 되돌리는지(clear ↔ rain 1.0 체감 밝기 차) 한두 줄.
- [ ] 끝나면 `golmok.weather clear instant`.

## 6. 일정(Schedule) 한 바퀴
L_Dev PIE(새로), 키 **2**(12:30 fixed).
- [ ] 키 2 **전**(레벨 조명): `golmok.weather mode schedule` → `weather: mode fixed -> schedule (no clock - clear kept until the time of day has one)`, HUD 끝 `| schedule | fx idle | schedule no clock`. 키 2 → HUD 끝이 `| schedule | fx idle | schedule next 13:00 overcast`(12:30은 08:30 clear 칸이라 변화·이벤트 없음).
- [ ] `golmok.weather list` →
  ```
  LogGolmok: weather: schedule (10 slots, mode schedule)
      00:00 rain 0.30
      03:00 overcast
    * 08:30 clear
      13:00 overcast
      15:00 rain 0.60
      16:30 rain 1.00
      17:00 rain 0.30
      17:45 overcast
      19:30 clear
      22:30 overcast
  ```
- [ ] `golmok.tod rate 10` → `golmok.tod mode clock`(하루 144 s). 한 바퀴(약 2분 반) 동안 Output Log에서 `weather: OnWeatherChanged` 줄을 센다: 칸 경계마다 **정확히 1회**, 순서 `overcast`(13:00) → `rain 0.60`(15:00) → `rain 1.00`(16:30) → `rain 0.30`(17:00) → `overcast`(17:45) → `clear`(19:30) → `overcast`(22:30) → `rain 0.30`(00:00) → `overcast`(03:00) → `clear`(08:30), 모두 `(transition)`. 10줄.
  - 전환은 월드 초 20 s라 x10에서는 칸(시계 분)이 전환보다 짧을 수 있다(16:30~17:00 = 3 s, 17:00~17:45 = 4.5 s). 이때 HUD `(from … 0%)`가 다시 시작하고 화면은 튀지 않는다 — 정상(설계 §3 재목표).
  - 경계 사이에 이벤트 줄이 반복되거나(같은 칸 재발화) 빠지면 실패.
- [ ] Fixed 시간대에서 점프: `golmok.tod mode fixed` → `golmok.tod time 15:30` → `weather: OnWeatherChanged rain 0.60 (transition)` 1줄, 키 **1**(07:30) → `overcast`(03:00 칸) 1줄.
- [ ] Schedule 중 명시 명령: `golmok.weather rain heavy` →
  ```
  LogGolmok: Display: weather: rain in schedule mode -> fixed
  LogGolmok: weather: rain 1.00 over 20.0 s
  ```
  HUD 모드 칸 `fixed`, `schedule next …` 꼬리 없음.
- [ ] (선택) `golmok.tod mode realtime` + `golmok.weather mode schedule` → 메시지의 `slot HH:MM …`이 PC 현지 시각의 칸.
- [ ] 다시 `golmok.weather mode fixed` → `weather: mode schedule -> fixed (<현재 목표> kept)`.

## 7. 실내(L_ZoneTest 포털)
`L_ZoneTest` PIE, HUD 켬. `golmok.weather rain heavy instant`.
- [ ] 문 `door_1`로 들어간다 → 로그 `TimeOfDay: interior overlay on (source …, base …)`, HUD 날씨 줄 `… | fixed | fx interior`. 새 빗줄기가 생기지 않는다. 문간에서 남은 줄무늬가 1 s 안쪽으로 보일 수 있다 — **관찰만**(설계 §11, §13에 보였는지·얼마나).
- [ ] 실내 조명: 안개 없음·노출은 실내 값(V-03 §5와 같은 밝기 — 실내에서 rain과 clear를 `instant`로 바꿔 비교하면 안개·노출 차이가 없고, 창으로 드는 태양·하늘빛만 약해진다).
- [ ] 실내에서도 날씨는 흐른다: `golmok.weather status`의 `wet`이 계속 오르고 `interior yes`, `fx interior`.
- [ ] 나온다 → `interior overlay off`, HUD `fx on`, 빗줄기가 **곧바로** 화면 위아래 전체에 있다(위에서부터 차오르지 않음 — warmup 1 s, §12 #12). 차오르면 §12 #12 대안.
- [ ] 실내에서 `golmok.weather clear` 뒤 나오면 `fx idle`(비 없음).

## 8. 포토 모드(정지)
L_Dev(또는 L_ZoneTest) PIE. `golmok.weather rain heavy instant`.
- [ ] **P** → 빗줄기가 **멈춘 채** 보인다(기본 `PauseMode=GamePause`, §12 #6). `golmok.weather status` → 끝 줄 `… | frozen yes`(HUD는 포토 오버레이라 콘솔로 본다).
- [ ] 포토 중 변경 거절: `golmok.weather clear` →
  ```
  LogGolmok: Warning: weather: photo mode is active - change the weather before entering photo mode
  ```
  `mode schedule`·`surface 0.5`·`fx off`도 같은 문구(멈춘 빗줄기를 지우지 않는다 — 적대 검증 반영). `golmok.weather list`·`status`는 된다.
- [ ] 촬영(`golmok.photo.shoot` 또는 촬영 키) → `<Saved>/Screenshots/Golmok/photo/<stamp>.json`에 `preset` 다음 줄
  ```
    "weather": {"state": "rain", "intensity": 1.00},
  ```
  png에 멈춘 빗줄기가 찍혔다. clear에서 찍으면 `"weather": {"state": "clear", "intensity": 0.00},`.
- [ ] **전환 이어짐**: P를 나와 `golmok.weather clear instant` → `golmok.weather rain heavy` → HUD `25%` 무렵 **P** → 10 s 머문 뒤 P 종료 → HUD가 `25%` 근처에서 이어 간다(앞으로 튀지 않음, 누적 델타). 젖음·웅덩이도 포토 동안 멈췄다(전후 `status` 비교).
- [ ] (선택) `PauseMode=TimeDilation`(로컬 ini, 커밋하지 않음)으로 한 번 더: 빗줄기가 멈추거나 거의 멈추는지, 날씨 α가 진행하지 않는지(§12 #6·#11).

## 9. 이동·세이브
`L_ZoneTest` PIE.
- [ ] **이동 리셋**: `golmok.weather rain heavy instant` → `golmok.travel z_synthetic_002` → 페이드 뒤 도착지에서 빗줄기가 곧바로 내리고, 192 m를 가로지르는 **줄무늬·늘어진 입자가 없다**(`OnTraveled` → `ResetSystem`, §12 #15). `golmok.travel z_synthetic_001`로 돌아와도 같다.
- [ ] **세이브 왕복(PIE)**: `golmok.weather overcast instant` → `golmok.weather surface 0.42 0.10` → `golmok.save` →
  ```
  LogGolmok: GolmokSave: saved golmok_auto (sync, console): zone …, visited …, photos …, position yes, tod …, weather overcast wet 0.42 puddle 0.10 fixed
  ```
  (흐림에서는 젖음이 초당 1/600씩 마르므로 `wet 0.41`일 수 있다.) `golmok.save status`의 `slot:` 줄 끝 `…, weather overcast wet 0.4x puddle 0.10 fixed`.
- [ ] `golmok.weather rain heavy instant` → `golmok.load` → 메시지 끝 `…, weather overcast wet 0.4x puddle 0.10 fixed` → HUD가 **전환 없이** 곧바로 `weather: overcast | now 0.00 wet 0.4x puddle 0.10 | fixed | fx idle`, 빗줄기 잔상 없음(`ResetRainFx`). 로그에 `weather: OnWeatherChanged overcast (instant)` 1줄.
- [ ] **basemap 위치 복원의 빗줄기 리셋(R112-U8)**: 존 밖 basemap 위치(존 발판 밖, `golmok.save status`의 `slot:` 줄 `zone -`)에서 `golmok.weather rain heavy instant` → `golmok.save` → 100 m 이상 걸어간 뒤 `golmok.load` → 메시지 `restore saved position …: placed at the saved position (no zone) …`이고 그 자리에서 빗줄기가 곧바로 내리며 **줄무늬·늘어진 입자가 없다**. 빗줄기가 1 s쯤 성기게 시작해 차오르는지도 본다(리셋 웜업이 옛 자리에서 돈 증상, R113-3 — 보이면 §12 #20). 이 리셋은 이제 날씨 규칙과 무관하게 `Restore`가 1회 한다(Rule 0 슬롯도 같은 줄이고 자동화 `weather rule 0: rain fx reset once`가 근거). 존 이동 복원은 도착 `OnTraveled`가 1회 리셋한다(앞 줄의 이동 리셋과 같다).
- [ ] **Schedule 복원**: `golmok.tod mode fixed` → `golmok.tod time 15:30` → `golmok.weather mode schedule` → 20 s 뒤 `golmok.save`(로그 끝 `weather rain 0.60 wet x.xx puddle x.xx schedule`) → `golmok.weather mode fixed` → `golmok.weather clear instant` → `golmok.load` → 메시지 `…, tod 15:30 fixed…, weather rain 0.60 wet x.xx puddle x.xx schedule`(시간대가 먼저 복원돼 같은 칸이라 `(transition)` 없음), HUD 모드 칸 `schedule`.
- [ ] **재시작 복원(standalone `-game`)**: 에디터를 닫고
  ```powershell
  & "<UE>\Engine\Binaries\Win64\UnrealEditor.exe" "<repo>\unreal\Golmok\Golmok.uproject" /Game/Golmok/Maps/L_ZoneTest -game -windowed -ResX=1280 -ResY=720 -log
  ```
  1회차: `~` → `golmok.weather rain heavy instant` → 30 s 기다림 → 창 닫기 → 종료 로그 `GolmokSave: saved golmok_auto (sync, world end): … weather rain 1.00 wet 0.xx puddle 0.xx fixed`의 wet·puddle을 적는다.
  2회차: 같은 명령 → 시작 로그 `GolmokSave: restore on begin play: … , weather rain 1.00 wet <적은 값> puddle <적은 값> fixed; …` → 시작하자마자 비(20 s 전환 없음), HUD `weather: rain 1.00 | now 1.00 wet …| fixed | fx on`. **시작 뒤 clear로 되돌아가면** 복원과 날씨 BeginPlay 순서 결함이다(§12 #16).
- [ ] **구 세이브(Rule 0)**: 머리말에서 백업한 `golmok_auto.pre-wp16a.sav`가 있으면 에디터·게임을 닫고 `golmok_auto.sav`를 백업본으로 바꾼 뒤(지금 슬롯은 `golmok_auto.v16.sav`로 따로 둠) `-game` 실행 → `golmok.save status`의 `slot:` 줄 끝 `weather - (not in save)`, 시작 복원 로그에 `, weather - (not in save)`, 날씨는 `initial`(HUD `weather: clear | …`)이다. `golmok.weather rain light instant` → `golmok.load` → 메시지 끝 `, weather - (not in save)`이고 비가 **그대로**(Rule 0은 현재 날씨 유지). 끝나면 슬롯 파일을 원래대로 돌린다. 백업이 없으면 "자동화 RoundTrip Rule 0 단계로 갈음"이라고 §13에 적는다.

## 10. 성능(설계 §7-5, RTX 5060 8 GB 1080p)
GUI PIE 새 창 1920×1080(또는 `-game -windowed -ResX=1920 -ResY=1080`), `L_Dev`(있으면 `L_Basemap_Yeonnam`도). 캐릭터·카메라 고정, `golmok.tod mode fixed` → `golmok.tod time 12:30`.
```
stat unit
stat gpu
stat niagara
```
1. `golmok.weather clear instant` → 10 s 뒤 Frame·Game·Draw·GPU(ms), `stat gpu` 합계, `stat niagara` 입자 수.
2. `golmok.weather rain heavy instant` → 10 s 뒤 같은 값. `stat gpu`의 Niagara(GPU 시뮬레이션·Translucency/스프라이트) 항목.
3. `golmok.weather fx off` → 10 s 뒤 같은 값 → `golmok.weather fx on`(빗줄기만의 비용 = 2 − 3).
4. `golmok.weather clear` → 전환 끝(20 s) 순간 `stat unit` Frame 스파이크 유무. 정적 SkyLight 레벨이면 전환 끝 재캡처 1회 히치(ms)를 기록.

| 예산(설계 §7-5) | 기준 |
|---|---|
| 빗줄기 GPU(2 − 3) | ≤ **0.5 ms** |
| 날씨 전체 GPU(2 − 1) | ≤ **+1.0 ms** |
| 게임 스레드(2 − 1) | ≤ **+0.05 ms**(틱당 할당 없음). `stat unit` Game 차이는 잡음보다 작으므로 `stat tickables`(서브시스템 `GetStatId` = `STATGROUP_Tickables`)의 날씨 틱 항목이나 Insights 캡처로 잰다(리뷰 R112-D8) |
| 살아 있는 입자 | ≤ **20,000**(`max_spawn_rate` × 수명 1 s ≈ 12,000 기대) |

- [ ] 예산을 넘으면 **코드가 아니라 데이터로** 낮춘다: `Config/Golmok/weather.json` `rain_fx.max_spawn_rate` 12000 → 8000 → 5000 순으로 바꾸고 PIE를 **새로 시작**(설정은 서브시스템 초기화 때 읽는다)해 2·3을 다시 잰다. 단계마다 값을 §13에 적는다. 채택하면 커밋 `WP-16a: PC fix max_spawn_rate <값>`에 `weather.json`과 함께 그 값을 고정한 테스트(`tools/tests/test_ue_config_weather.py`의 저장소 값, `Tests/GolmokWeatherTest.cpp` `Golmok.Weather.Config`의 값 단언)를 같이 고친다. 5000에서도 넘으면 V-16 결과에 적고 16b(머티리얼·크기)로 넘긴다.
- [ ] volumetric 안개는 날씨가 켜지 않는다(1과 2의 volumetric 상태가 같다).

## 11. 패키지
```powershell
.\tools\ue\package.ps1
$pkg = if (-not [string]::IsNullOrWhiteSpace($env:GOLMOK_PKG_DIR)) { $env:GOLMOK_PKG_DIR.Trim().TrimEnd('\') } else { ".\build\Windows" }
Select-String "$pkg\Manifest_UFSFiles_Win64.txt" -Pattern 'Config/Golmok/weather.json'
$pak = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealPak.exe'
& $pak "-ListContainer=$((Resolve-Path "$pkg\Golmok\Content\Paks\Golmok-Windows.utoc").Path)" "-csv=$env:TEMP\utoc.csv"
Select-String "$env:TEMP\utoc.csv" -Pattern 'Golmok/Weather/(MPC_GolmokWeather|NS_GolmokRain)'
```
- [ ] BuildCookRun 성공. `weather.json`이 스테이징됐고(기존 `../Config/Golmok` UFS 줄), 컨테이너에 `MPC_GolmokWeather`·`NS_GolmokRain`이 있다(soft 경로만 쓰는 에셋 — `DirectoriesToAlwaysCook` 훅, §12 #13). IoStore가 아니면 `.pak` `-List`로 같은 확인.
- [ ] 패키지 실행 명령: `& "$pkg\Golmok.exe" -windowed -forcelogflush`(`$pkg`는 `pc-setup.md` §2a; `-log` 창은 포커스를 뺏으므로 쓰지 않는다). Windows 방화벽 대화상자가 뜨면 세션은 누르지 않고 소유자가 **취소**한다(C-07, `pc-setup.md` §2a).
- [ ] 패키지 실행 → 로그(`$pkg\Golmok\Saved\Logs\Golmok.log` — `$pkg`는 `pc-setup.md` §2a의 `GOLMOK_PKG_DIR` 규칙)에 `weather: clear fixed, transition 20.0 s, 10 schedule slots, mpc ok, fx idle`, `MPC missing`·`rain fx missing`·`weather: off -` 줄 없음.
- [ ] `~` → `golmok.weather rain heavy` → 20 s 전환·빗줄기(HUD는 Development 빌드에서 F1), `golmok.weather status` 끝 줄 `mpc ok | fx on | interior no | frozen no`.

## 12. 불확실한 UE 5.8 API와 대안(설계 §17)
| # | 파일 | API·항목 | 불확실한 점 | 대안 | PC 결과 |
|---|---|---|---|---|---|
| 1 | `Golmok.uproject` | `Niagara.uplugin` `EnabledByDefault`, 목록에 없을 때 UBT 경고 | 경고 문구·기본 활성 여부 | 명시 항목은 어느 쪽이든 무해 — uplugin 값과 빌드 로그를 기록만 | |
| 2 | `Golmok.Build.cs` 훅 | `PrivateDependencyModuleNames.Add("Niagara")`만으로 `UNiagaraComponent`·`UNiagaraSystem`·`FNiagaraVariable`·`FNiagaraTypeDefinition` 링크 | NiagaraCore 공개 전이 여부 | 링크 오류면 같은 훅 블록에 `NiagaraCore` 추가(+ `BUILD_CS_PRIVATE` 훅 줄) | — 이때 `test_ue_wp16_fixture.py` `BUILD_CS_HOOK`·NiagaraCore 단언도 같은 커밋에서 갱신(R112-U2) |
| 3 | `GolmokWeatherRainFx.cpp` | `NewObject<UNiagaraComponent>` + `SetAsset` + `SetUsingAbsoluteRotation` + `SetRootComponent` + `AddInstanceComponent` + `RegisterComponent`(plain `AActor`) | 컴파일·등록·렌더 | `UNiagaraFunctionLibrary::SpawnSystemAttached`(5.8 서명, `ENCPoolMethod::None`)로 만들고 액터는 소유자로만 | |
| 4 | `GolmokWeatherRainFx.cpp` | `SetVariableFloat`/`SetVariableVec3`에 `User.` 접두 이름, 읽기 `GetOverrideParameters()`(const)·`FindParameterOffset`·`GetParameterValue<float/FVector3f>` | 접두 필요 여부, const 접근자·템플릿 존재 | `Golmok.Weather.Runtime`이 파라미터 존재를 단언. 실패하면 접두 없는 이름(`RainIntensity` 등)으로 쓰기, 읽기는 `GetOverrideParameters().GetParametersWithOffsets()` 순회 | |
| 5 | Tests | `-nullrhi`에서 GPU 이미터 컴포넌트 생성·`IsActive()` 조회 | 활성 상태가 RHI 없이 의미 있는지 | 계약(컴포넌트·파라미터·활성 요청)만 단언, 시뮬레이션은 §4·§7 PIE GUI | |
| 6 | 포토 | `SetGamePaused`·TimeDilation 포토에서 Niagara 정지 | GamePause에서 GPU 시뮬레이션이 멈추는지 | 안 멈추면 포토 진입·종료에 컴포넌트 `SetPaused(true/false)`(Weather/ 안, 포토 이벤트 구독) | |
| 7 | `GolmokWeatherRainFx.cpp`·NS | GPU 고정 경계 + 월드 공간 + 매 프레임 이동하는 컴포넌트의 컬링 | 카메라가 움직일 때 빗줄기가 사라지는지 | NS 경계 여유 500 cm → 늘림(에셋만) | |
| 8 | 에셋 | Niagara 모듈 스택 Python 생성 | 가능 여부 | 16a는 §2b 레시피. 가능하면 16b에서 생성기 | ➖ 16a는 레시피 |
| 9 | `weather_setup.py` | MPC `scalar_parameters`·`CollectionScalarParameter` Python 쓰기 | 속성 쓰기 허용 | §2a 수동 절차 | |
| 10 | `GolmokWeatherSubsystem.cpp` | `UWorld::GetParameterCollectionInstance`(월드 시작 뒤 로드한 MPC)·`SetScalarParameterValue`, `-nullrhi` 값 읽기 | 인스턴스가 있는지 | `UKismetMaterialLibrary::SetScalarParameterValue(World, Mpc, Name, Value)` | |
| 11 | `GolmokWeatherSubsystem` | `UTickableWorldSubsystem` + `IsTickable()` override, `IsTickableWhenPaused` false, PIE 틱 | 틱 여부·정지 중 틱 없음 | 포토 판정은 `IsActiveIn`으로 겹쳐 둠(이미 코드에 있음) | |
| 12 | `GolmokWeatherRainFx.cpp` | `Activate(true)` 재활성에 시스템 `WarmupTime` 적용 | §4 instant·§7 실내 퇴장에서 위에서부터 차오르는지 | 재활성 뒤 `AdvanceSimulation` 1회(경과 1 s) | |
| 13 | `DefaultGame.ini` 훅 | soft 경로만 쓰는 `/Game/Golmok/Weather` 에셋이 `DirectoriesToAlwaysCook`로 패키지에 드는지 | 쿡 포함 | §11 확인. 빠지면 Asset Manager Primary Asset 규칙(ini 훅) | |
| 14 | 룩 | 비 + 새벽·저녁 램프에서 엔진 노출 경고(V-13 06:00 −8.8)가 심해지는지 | 값 | 기록만 → 14b 노출 범위 키(§5) | |
| 15 | `GolmokWeatherRainFx.cpp` | `DeactivateImmediate()`·`ResetSystem()`·`FActorSpawnParameters::NameMode = Requested` + `RF_Transient` | 5.8 서명·텔레포트 뒤 줄무늬 제거 | `ResetSystem` 대신 `DeactivateImmediate` → `Activate(true)`. NameMode가 없으면 이름 지정 생략 | |
| 16 | Save·Weather 순서 | 시작 복원(다음 틱)이 날씨 `OnWorldBeginPlay`의 초기값 뒤에 오는지 | 재시작 복원이 clear로 덮이는지(§9) | 날씨 초기값을 복원 대기 중에는 건너뛰기(Save/·Weather/ PC fix) | |
| 17 | `GolmokWeatherTest.cpp` | `TMulticastDelegate::IsBoundToObject(const void*)`(R112-U7) | 5.8에서 공개 멤버인지 | 컴파일 오류면 `W->GetRainFxResetCount()` 단언만 두고 바인딩은 `UGolmokWeatherSubsystem`에 `bool IsTravelResetBound() const { return Travel.IsValid() && TraveledHandle.IsValid(); }`를 더해 단언 | |
| 18 | `GolmokSaveSubsystem.cpp` `Restore` | 존 이동이 진행 중이면(`IsTraveling()`) 리셋을 도착 `OnTraveled`에 맡김(R112-U8) | 이동이 실패하면 리셋이 없다(위치가 안 바뀌어 줄무늬 원인도 없다고 봄) | 실패 뒤 줄무늬가 보이면 `Fail` 경로에서도 리셋(Map/ 수정은 Claude 레인) | |
| 19 | `GolmokWeatherSubsystem.cpp` | `OnWorldBeginPlay` → 액터 BeginPlay(컨트롤러 `FindOrSpawn`) → 첫 서브시스템 틱 순서(R112-U9) | 첫 틱이 컨트롤러 BeginPlay 뒤인지 | §4 첫 프레임 줄이 실패하면 `OnWorldBeginPlay` 끝에서 `World->OnActorSpawned` 1회 구독으로 시간대 액터를 잡는다 | |
| 20 | `GolmokSaveSubsystem.cpp` `Restore` → `ResetRainFx` | basemap 위치 복원은 같은 호출 안에서 순간 이동한 뒤 곧바로 리셋한다. 이때 `APlayerCameraManager::GetCameraLocation()`이 아직 지난 프레임의 POV(옛 자리)일 수 있다[추정, 리뷰 후속 검증] | 빗줄기가 옛 자리에서 다시 시작해 다음 틱에 100 m 넘게 이동할 수 있다. 화면은 페이드 인 중이라 보이지 않을 가능성이 크다. R112 전 Rule 1 리셋도 같았다 | §9 basemap 줄에서 줄무늬나 성기게 시작하는 빗줄기(R113-3)가 보이면 `Restore`의 리셋을 `SetTimerForNextTick`으로 한 틱 미룬다(RoundTrip 횟수 단언도 한 틱 뒤로) | |

## 13. 결과 기록

| 항목 | 기대 | 결과/근거 |
|---|---|---|
| 세션/head | 날짜·담당·커밋·장치 | |
| 구 세이브 백업 | `golmok_auto.pre-wp16a.sav` 유무 | |
| §1 빌드 | 오류 0·프로젝트 경고 0, Niagara UBT 경고 문구 | |
| §2a MPC | 생성 로그(문구)·멱등·3 스칼라 0, Python/수동 | |
| §2b NS | 레시피 11단계·스크린샷 `pc-verify-wp16a-ns.jpg`·시작 로그 `mpc ok, fx idle` | |
| §2c 커밋 | 커밋 해시·LFS·잠금 결과 | |
| §3 자동화 | Weather 3 Success(MPC·NS 단계 EXECUTED)·RoundTrip·전체 39/39 | |
| §4 전환 | rain heavy 표 5행·clear·instant·already·재목표·오류 8줄·no game world | |
| §5 매트릭스 | 20장 + HDR, 깨짐 0, 노출 경고(시각·날씨·값) | |
| §6 일정 | no clock·list·이벤트 10줄 순서·점프·명시 → fixed | |
| §7 실내 | fx interior·문간 잔상·실내 조명·퇴장 즉시 비 | |
| §8 포토 | 멈춘 빗줄기·거절 문구·메타 `weather`·α 이어짐(TimeDilation 선택) | |
| §9 이동·세이브 | 줄무늬 없음·PIE 왕복·Schedule·`-game` 재시작·Rule 0 | |
| §10 성능 | 표 4값(clear·rain heavy·fx off)·전환 끝 히치·`max_spawn_rate` 단계 | |
| §11 패키지 | 스테이징·컨테이너·패키지 실행 로그·rain heavy | |
| §12 API | 번호별 결과·PC fix 커밋 | |
| 빗소리 | T24 레이어 있음 — 깨짐(클릭·급정지)만, 밸런스는 wp13 §9·C-08 | |
| STATUS 판정 | 통과/부분/차단·남은 항목 | |

성능 표(§10):

| 레벨 | 조건 | Frame | Game | Draw | GPU | Niagara GPU | 입자 수 |
|---|---|---|---|---|---|---|---|
| L_Dev | clear 12:30 | | | | | | |
| L_Dev | rain heavy | | | | | | |
| L_Dev | rain heavy, fx off | | | | | | |

노출 경고 표(§5, → 14b):

| 시각 | 날씨 | 경고 유무 | Exposure 값 |
|---|---|---|---|
| | | | |

### V-16 실행 기록
(PC 세션이 채운다: 드라이버·시나리오, GUI/헤드리스 구분, 스크린샷 목록 `pc-verify-wp16a-ns.jpg`·`pc-verify-wp16a-look-matrix.jpg`·`pc-verify-wp16a-hdr-0600-rain.jpg`, PC fix 원인.)
