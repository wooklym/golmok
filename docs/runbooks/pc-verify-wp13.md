# V-10 — WP-13 환경음 검증

상태: 🟢 **V-10 PC 검증 통과(2026-09-29, §6·§7)**. 녹음 파형 분석·루프백 근거(사람 귀 청취 없음)로 WP-13 코드 결함 0(도구·런북 결함 2건은 PC fix). `5f6c810` Audio 코드(T6 #50 이전) 기준 — #50 런타임 변경은 헤드리스만, 다음 PC 카드에서 스모크. 남은 소유자 항목(비차단): 볼륨 청취·최종 gain(후보 §6), 패키지 발소리 1회(§7-4). 이전: 🟡 13b 코드 완료·PC V-10 패키징/청취 대기. 런타임·임포트 및 헤드리스 Audio 자동화 검증 완료.

## 1. 데이터와 임포트

먼저 `.\tools\ue\build.ps1` → `.\tools\ue\open-editor.ps1` 순서로 실행한다. GUI 잠금 규칙을 확인한다. **PIE/자동화 전에 음원7개를 임포트**해야 LoadObject 누락 경고를 피할 수 있다.


`Config/Golmok/audio.json`이 소스·에셋 경로·출처·루프·gain의 단일 소스다. 현재 7개 WAV는 결정적 합성 플레이스홀더이고 서울 녹음이나 채택 후보 원본이 아니다. 기본값과 소리의 적절성은 품질 가설이며 Fable/V-10 검토 대상이다.

```powershell
$env:PYTHONUTF8 = '1'
.\tools\.venv\Scripts\python tools/scripts/make_placeholder_audio.py
```

생성기는 `placeholder=true`이면서 `license=project-generated`인 항목만 만든다. 채택 원본에는 이 값을 쓰지 않는다. 48kHz PCM16 mono, 앰비언스 4초/원샷 약 0.33초, 피크 약 −14dBFS. 짧은 루프는 재생·교체 검사용이며 음질 합격 기준이 아니다. 실행할 때마다 표기 파일과 배포 크레딧도 JSON에서 갱신한다.

에디터 Python:

```python
import golmok.audio_import as audio
audio.run()
```

모든 소스의 경로·WAV 헤더/본문·개별 5MB/합계 40MB 예산을 먼저 확인한다. 임포트 실패·잘못된 타입·저장 실패는 예외로 남는다. 일부 에셋 저장 뒤 실패하면 이미 저장한 에셋은 남을 수 있으며, 문제를 고쳐 재실행한다. 모든 임포트 성공 후 `Content/Golmok/Audio/ATTRIBUTION.md`와 `Credits/audio-credits.txt`를 갱신한다. 크레딧의 `project-generated`는 외부 라이선스나 CC0 권리 포기 선언이 아니다.

헤드리스 임포트 재현: 다음 Python을 `unreal/Golmok/Saved/wp13-import-check.py`에 저장한다(미커밋). 실제 검증에 사용한 `-run=pythonscript` 방식이다. 같은 worktree의 에디터 GUI는 먼저 닫는다.

```python
import unreal
from golmok import audio_import, audio_pure
first = audio_import.run()
second = audio_import.run()
assert first == second and len(first) == 7
for item in audio_pure.load_config()["assets"].values():
    sound = unreal.load_asset(item["asset"])
    assert sound.get_editor_property("looping") == item["loop"]
    assert abs(sound.get_editor_property("volume") - item["gain"]) < 1e-6
unreal.log("WP13_IMPORT_VERIFIED_7_REIMPORT_7")
```

저장소 루트 PowerShell:

```powershell
$projectFile = (Resolve-Path .\unreal\Golmok\Golmok.uproject).Path
$importFile = (Resolve-Path .\unreal\Golmok\Saved\wp13-import-check.py).Path
& 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' $projectFile -run=pythonscript "-script=$importFile" -unattended -nullrhi -nosound
```

## 2. 실제 소스로 교체

1. 출처 조사 문서의 라이선스 원문과 실제 파일을 대조한다. Freesound 원본은 로그인 요구를 확인했으며 계정 생성/약정은 수행하지 않았다. 미리듣기 손실 파일을 원본처럼 반입하지 않는다.
2. 허용된 파일을 PCM16/48kHz로 준비해 Audio/src 아래 둔다. 앰비언스 stereo, 발소리 mono를 우선 검토하며 각 5MB/총 40MB 이하로 유지한다.
3. JSON의 해당 asset 항목에서 `source`, `asset`, `title`, `author`, `license`, `license_url`, `verified`(YYYY-MM-DD 확인일; 합성은 생성일), `source_url`, `changes`, `placeholder=false`, `loop`, `gain`을 갱신한다. 상태/세트는 asset ID를 참조하므로 C++ 수정 없이 데이터로 교체한다. `seed`는 실제 파일에 사용하지 않는다.
   허용 값: `CC0-1.0` → `https://creativecommons.org/publicdomain/zero/1.0/`, `CC-BY-4.0` → `https://creativecommons.org/licenses/by/4.0/`. `project-generated`는 합성 전용이고 license_url은 빈 문자열이다. 실제 원본의 확인일을 생성일로 대신하지 않는다.
4. 임포터 재실행 후 에셋과 크레딧의 저자·URL·라이선스·수정 내역을 확인한다. CC0에도 프로젝트 출처 추적 기록을 남긴다. CC-BY 표기는 같은 파이프라인에서 생성한다.
5. gain은 SoundWave 볼륨 배율이며 원본 파형 정규화가 아니다. 이미 피크 조정한 파일에 gain을 적용한 후 청취로 밸런스를 정한다. 같은 gain을 런타임에서 중복 곱하지 않는다.

## 3. 남은 런타임·청취 항목

`UGolmokAmbienceSubsystem`과 `UGolmokFootstepComponent` 구현 뒤 `Golmok.Audio.StateMachine`·`Golmok.Audio.Footstep` 헤드리스 검사를 추가했다. 아래 명령은 사전 임포트 및 L_Dev/합성 zone 준비 후 수행한다.

```powershell
.\tools\ue\build.ps1
.\tools\ue\test.ps1 -SetupDevLevel -Filter Golmok.Audio
.\tools\ue\test.ps1 -SetupDevLevel
```

콘솔: `golmok.audio` 상태·슬롯·볼륨·선택 발소리 세트(`steps=default/asphalt/tile/stairs`)·Photo 배율(`photo_gain`), `golmok.audio credits` JSON 출처/저자/라이선스/수정 내역, `golmok.audio.mute 1` / `0`, `golmok.audio.state outdoor_night` / `interior` / `outdoor_day` / `auto`. `auto`로 돌아와야 실제 Lighting 이벤트를 다시 따른다. HUD의 `audio:`는 Debug 공급자를 통해 갱신된다.

`golmok.tod night`와 `clear_noon`, 포털 진입/퇴장으로 이벤트 연동을 검증한다. 실내 소스가 여러 개면 마지막 소스가 빠질 때까지 interior다. PhysicalMaterial surface0=default, 1=asphalt, 2=tile, 3=stairs 매핑은 audio.json에 있다. L_Dev의 Course/Stairs는 **에디터 폴더이며 런타임 태그가 아니다**. 기본 L_Dev 계단은 지정 재질이 없으면 default 소리가 맞다. 재질 비교 전 Project Settings → Physics → Physical Surfaces에 **1=asphalt, 2=tile, 3=stairs** 이름을 지정한다(세트 id와 대소문자 무관 일치). 이름이 없거나 다르면 HUD/`golmok.audio`의 `error: surface ...` 진단과 default fallback을 확인한다. 별도 테스트 복사 맵에서 해당 물리 재질 또는 명시적 actor tag `Course/Stairs`를 설정한다. 시험용 `DefaultEngine.ini` 이름 변경은 커밋하지 않고 시험 전 내용을 보관했다가 복구한다. 다른 세션의 기존 변경을 되돌리지 않는다. 원본 setup_dev_level.py는 수정하지 않는다.

보폭은 `footsteps.stride_cm_by_character`의 로스터 id별 cm 값이다: manny/quinn 걷기67·달리기146, proxy135 54/142, proxy110 45/115. 누락 id는 기본70/110cm, 달리기 속도 기준250cm/s다. 같은 폰의 로스터 id가 바뀌어도 누적거리를 초기화한다. V-08 애니메이션 채택 뒤 노티파이 방식으로 재검토한다. 실제 소리 재생은 한 프레임 최대1발이며 긴 프레임의 나머지 거리는 소비한다. 공중은 무음, 공중→지면 전환은 착지1회, 폰 변경/경로/포토 진입 뒤에는 누적거리를 초기화한다. pause_policy의 `mute`/`maintain`은 JSON을 바꾸고 PIE를 재시작해 각각 확인한다. 사용자 mute는 두 정책보다 우선한다. Photo 유지/뮤트 양쪽, 빠른 낮→밤→실내 재전환, 복수 포털 소스, 폰 교체/경로 재생, 걷기/달리기/공중/착지/텔레포트, 미지정 물리 재질 fallback을 확인한다.

V-10 GUI는 다른 UE 세션 종료와 GUI 잠금 확인 뒤 수행한다. 낮/밤·실내 전환 각3회, 재질별 걷기/달리기 각각10보, 점프/착지5회를 청취하고 clipping·루프 이음·발소리 중복·pause 뒤 복귀를 기록한다. 실제 청취와 자동화 로직 성공은 구분한다. 최종 야외 음원은 WP-17 현장 녹음 교체 대상이다.

로스터별 확인: `golmok.character proxy135`, `golmok.character proxy110`, `golmok.character quinn`으로 각각 교체한 뒤 걷기/달리기10보씩 청취한다. 새 보폭과 발 딛기 횟수를 비교해 기록한다. 메시 Z 스케일 곱(`stride_scale_by_mesh`)은 V-10 뒤 기각됐고 파서가 거부한다. 자체 발소리·착지는 2D로 재생하므로 붐 길이에 따른 거리 감쇠가 없어야 한다. 기존 attenuation 설정은 다른 소스용으로 유지한다.

소유자 청취: 재생 장치(헤드폰/스피커 모델·OS 출력 볼륨)를 적고 `master_volume`, 상태별 asset gain, 발소리 asset gain의 최종 값을 audio.json에 기록한다. 플레이스홀더의 비교는 잠정이며 실제 소스 교체 뒤 다시 듣는다. 헤드리스 자동화는 mute 플래그와 GamePause 중 Photo 배율의 0 도달·복귀를 타임아웃 안에서 폴링한다. 중간 곡선은 순수 수학 회귀로 확인한다. 실제 출력 파형·재생 중 원샷 FadeOut·청취 밸런스는 PC 항목이다.

## 4. API·패키징 확인

| 항목 | 상태 |
|---|---|
| AssetImportTask / imported_object_paths | fake unreal 계약 및 UE5.8.3 실제7개 임포트·재임포트 확인 |
| SoundWave looping·volume / save_loaded_asset | 실제7개 값 검증, 볼륨은 파형 정규화가 아님 |
| Lighting 프리셋/실내 변경 이벤트 | 00:13Z Fable 승인 최소 훅 구현, 실제 이벤트→상태 자동화 통과 |
| HUD audio: 줄 | 승인된 ExtraHudLineProviders 훅 구현; 바인딩/해제는 Audio 소유. FDelegateHandle 등록/해제로 다른 공급자 제거·중복 해제에도 등록이 유지됨(13c 헤드리스 회귀) |
| audio.json UFS | 기존 DefaultGame.ini의 ../Config/Golmok 스테이징 사용 |
| 배포 크레딧·SoundWave cook | Audio cook 등록 및 WP-05 목록 계약을 01:27Z 허용 범위로 반영. 크레딧 원본 메타데이터는 기존 UFS의 audio.json에 포함되며 `golmok.audio credits`가 읽어 출력한다. 독립 txt는 배포 문서용 생성물이고 별도 UFS에 넣지 않음. **V-10(2026-09-29)**: `Golmok-Windows.utoc`에 SW 7개(.uasset+.ubulk), `Golmok-Windows.pak`에 `Config/Golmok/audio.json`. 패키지 실행에서 `golmok.audio credits` 7항목 출력(§7) |


## 5. 크로스페이드와 품질 확인

T8은 슬롯 진폭 g를 전력 영역에서 보간한다: `u = (1 - cos(pi * alpha)) / 2`, `g = sqrt(F² + (T² - F²) * u)`. 시작/목표가 상보적인 두 슬롯의 합산 전력은 일정하고, 전환 중 재타깃도 현재 진폭에서 연속으로 이어진다. 서로 다른 소스의 RMS·상관관계까지 일정한 청감을 보장하지 않으므로 청취로 확인한다. 제3의 상태가 빠르게 들어오면 두 슬롯만으로 세 파일을 유지할 수 없어 조용한 슬롯을 최대50ms 동안0으로 낮춘 뒤 교체한다. 이 교체 구간과 초기 무음에서의 시작은 일정 전력 주장 대상이 아니다. 요청 상태는 즉시 바뀌고 새 파일은 슬롯 감쇠 뒤 시작한다.

포털 기준은 **0.5 s 간격 3왕복·클릭 없음**이다(`MinCrossingIntervalSeconds=0.25 s`). `crossfade_seconds_by_state`는 목적 상태별 0~30초이고 누락 시 전역 `crossfade_seconds`를 사용한다. T8 기본은 실내1.0초·실외2.0초다. Photo `pause_policy=mute` 진입/해제는 별도 `photo_mute_fade_seconds`(0~5초, 생략 .25초, 0이면 즉시) 진폭 raised-cosine S-curve로 앰비언스를 감쇠/복귀한다. 재생 중 원샷은 `FadeOut(..., SCurve)`로 종료하고 새 원샷은 Photo 중 억제한다. `maintain`은 UI sound로 월드 pause와 분리하며 사용자 mute가 우선한다.

T8 품질 정책은 [Fable 배정](https://github.com/wooklym/golmok/issues/30#issuecomment-5879528015)에 따른다. 아래 §6·§7은 **5f6c810의 V-10 실행 이력**이며 새 equal-power·Photo 페이드·2D 발소리·볼륨·보폭의 PC 합격 결과로 재사용하지 않는다. 새 정책의 청취·패키지 발소리는 C-07 해소 뒤 PC, 최종 밸런스는 소유자 C-08이다.

패키징 확인(V-10 실행, §6·§7): 임포트 후 `.\tools\ue\package.ps1` 실행 → `build/Windows`의 패키징 로그/컨테이너 목록에서 Audio의 SoundWave 7개와 `Config/Golmok/audio.json`을 확인 → 패키지 실행에서 세 상태 전환과 `golmok.audio credits` 출처 출력 확인. pak은 엔진 `UnrealPak.exe <pak 경로> -List`로 조사한다. IoStore를 사용한 출력이면 해당 컨테이너 목록과 cook/stage manifest도 함께 확인한다. 패키지 HUD/`golmok.audio` 출력에 **`error: missing SoundWave`가 없음**도 확인한다. 파일 존재와 실제 재생/크레딧 출력을 각각 기록하고 미실행을 성공으로 표시하지 않는다.


### 런타임 불확실 API

아래 결과는 T8 이전 V-10 이력이다. T8은 A1의 자체 발소리 감쇠를 제거하고 A4를 SpawnSound2D로 바꿨으며 A3·A8의 mute에 0.25초 페이드를 추가했다. 해당 변경의 실제 출력은 재검증 대상이다. 컴파일/헤드리스 성공과 출력 장치·패키지 검증을 구분한다.

| 번호 | API | 위험 | 대안 | 확인 단계 | 결과 |
|---|---|---|---|---|---|
| A1 | USoundAttenuation(반경100cm·falloff600cm) | 실제 거리 감쇠 불일치 | 청취 뒤 설정 튜닝 | 근거리/600cm 비교 | **부분 확인**(V-10): 감쇠 작동. 리스너가 카메라라 붐이 짧을수록 발소리 피크가 큼 — Manny(붐 320 cm) −35.8, proxy135(260) −34.5, proxy110(227) −34.2 dBFS. 600 cm 경계 비교는 미실행 |
| A2 | USoundConcurrency(8, StopOldest) | 원샷 중첩/잘림 | voice·정책 조정 | 연속 이동/착지 | **확인**(V-10): 걷기·달리기·착지에서 동시 발소리 보이스 최대 2(ListWaves 0.1 s 샘플). 보폭 1회당 1인스턴스, 누락·중복 없음. 8 한도에 닿지 않아 StopOldest 동작 자체는 미관찰 |
| A3 | SpawnSound2D + bIsUISound | GamePause maintain 중 재생 중단 | pause 대응 검토 | Photo 양 모드 | **확인**(V-10): maintain이면 Photo(GamePause) 동안 앰비언스 레벨 불변(−50.3 dBFS). mute면 20~40 ms 램프로 무음·클릭 없음, 해제 즉시 복귀. 엔진 `CreateSound2D`가 Play 전에 `bIsUISound=true`를 설정(GameplayStatics.cpp 1682) |
| A4 | SpawnSoundAtLocation | 무음/null/공간화 불일치 | 출력·에셋·감쇠 점검 | 실제 발소리 | **확인**(V-10): submix 녹음에 발소리 온셋, ListWaves에서 실제 소스(`Yes`) 재생. 발밑 위치라 L/R 동일(중앙) |
| A5 | LineTraceSingleByChannel(ECC_Visibility), bReturnPhysicalMaterial, GetSurfaceType | 재구성 메시·Zone 충돌/재질 누락 | default, Zone 재질/충돌 보완 | 각 재질/재구성 바닥 | **확인**(V-10): PIE에서만 Floor에 PhysicalMaterial override → complex·simple 트레이스 모두 그 재질 반환. SurfaceType1/2/3 → asphalt/tile/stairs 세트, 미지정 → default, 합성 Zone 충돌 메시 → default. Python은 이름 없는 SurfaceType을 못 다룸(Hidden enum) — §7-5 |
| A6 | LoadObject<USoundWave> 소프트 경로 | 패키지 cook 누락 | cook 등록·임포트 확인 | Development 패키지 | **확인**(V-10): 패키지에서 `golmok.audio` 슬롯 재생. 루프백으로 낮/밤/실내 −60.5/−64.2/−65.6 dBFS(OS 볼륨 포함), missing 경고 없음. 패키지 발소리는 미확인(§7-4) |
| A7 | OnPossessedPawnChanged.AddDynamic | 교체 뒤 컴포넌트 누락/중복 | 바인딩 수명 점검 | 로스터·경로·Photo 복귀 | 헤드리스 부착 확인. **V-10 GUI**: `golmok.character`는 같은 폰(`GolmokCharacter_0`)을 제자리에서 바꿔 발소리 계속 동작. Photo는 빙의하지 않음. 경로 재생 빙의 교체는 GUI 미확인 |
| A8 | IsTickableWhenPaused | pause 중 정책/페이드 정지 | 시간 처리 검토 | mute/maintain | **확인**(V-10): GamePause(Photo) 중에도 Tick이 돌아 mute 정책 적용·해제가 즉시 반영됨 |
| A9 | HasCalledBeginPlay | 초기/재시작 Tick 순서 | 월드 시작 후 초기화 | PIE 재시작3회 | 헤드리스 통과. **V-10 GUI**: 한 에디터 세션에서 PIE 재시작 3회 모두 시작 2 s 뒤 `outdoor_day`, `SW_outdoor_day` 보이스 재생(0.17), 경고 없음 |
| A10 | UAudioComponent::FadeOut(D, 0, SCurve), UI sound/GamePause | 실제 원샷 종료 곡선/정지 타이밍 | submix 녹음·보이스 로그 비교 | C-07 뒤 Photo 진입 중 원샷 | T8 리뷰 보완: 컴파일·헤드리스 envelope만 확인, 실제 출력 미검증 |

패키징 후 cook 파일 수 확인(7개 기대). UE 5.8.3은 Zen 스토어(`Saved/Cooked/Windows/ue.projectstore`)로 cook하므로 `Saved\Cooked\Windows\Golmok\Content\...`에 낱개 `.uasset`이 **없다**(V-10). stage manifest와 컨테이너 목록으로 확인한다:

```powershell
.\tools\ue\package.ps1
Select-String .\build\Windows\Manifest_UFSFiles_Win64.txt -Pattern 'Golmok/Content/Golmok/Audio/.*SW_.*\.uasset|Config/Golmok/audio.json'
$pak = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealPak.exe'
& $pak "-ListContainer=$((Resolve-Path .\build\Windows\Golmok\Content\Paks\Golmok-Windows.utoc).Path)" "-csv=$env:TEMP\utoc.csv"
Select-String "$env:TEMP\utoc.csv" -Pattern 'Golmok/Audio/.*SW_'
& $pak (Resolve-Path .\build\Windows\Golmok\Content\Paks\Golmok-Windows.pak).Path -List | Select-String 'audio.json'
```

`package.ps1`은 V-10부터 `-ubtargs=-NoHotReloadFromIDE`를 넘긴다. 같은 엔진 설치의 다른 에디터나 `-game`이 Live Coding을 켜 둔 상태이면, 이 인자가 없을 때 BuildCookRun이 "Unable to build while Live Coding is active"로 멈춘다(`build.ps1`과 같은 처리). 이 인자는 Live Coding 검사만 피한다. 같은 워크트리의 에디터가 `UnrealEditor-Golmok.dll`을 잡고 있고 코드가 바뀌었으면 에디터 타깃 링크는 여전히 실패하므로, 같은 워크트리의 에디터는 닫는다(GUI 잠금 규칙).

cook 파일만으로 합격시키지 않는다. 컨테이너/stage manifest의 SoundWave7개·audio.json과 패키지 실행의 재생·크레딧도 확인한다. 에디터 Packaging 저장은 중복 ini 섹션을 재작성할 수 있으므로 Audio cook 훅 보존을 diff로 확인한다. PhysicalSurfaces1/2/3 이름은 Zone 에셋 단계에서 정의한다. T8은 audio.json 번호에 대응하는 Physics 표면 이름이 세트 id와 대소문자 무관하게 같아야 매핑하며, 아니면 default + HUD error + 월드별 표면 번호당 1회 Warning을 남긴다(명시 Course/Stairs 태그 우선). CC-BY 원본 채택 시 Shipping에서 도달 가능한 크레딧 UI/배포 표기를 확인한다(현 콘솔 노출은 Development 검사용).

## 6. 결과 기록

판정 근거는 **master submix 녹음 파형 분석**(에디터 `AudioMixerLibrary.StartRecordingOutput`, 48 kHz 스테레오)과 WASAPI 루프백(패키지)이다. 세션이 사람 귀로 들은 것은 아니다. 음색·최종 밸런스는 소유자 청취 항목으로 남는다. 방법과 수치는 §7에 있다.

| 항목 | 실행·기대 기준 | 결과/근거 |
|---|---|---|
| 세션/head | 날짜·담당·커밋·장치 | 2026-09-29 04:37~06:20 KST, PC 검증 세션(Claude Fable 5.1), 워크트리 `stoic-kare-964e86`, 브랜치 `pc/v10-verify-wp13` ← origin/main `5f6c810`(PR #34·#37~#45 포함). Windows 11, UE 5.8.3 Launcher. 출력 장치 **DELL U2724D(NVIDIA High Definition Audio)**, OS 마스터 **52 %(−9.9 dB)**, 음소거 아님. 모니터 스피커·헤드폰 연결 여부는 세션이 확인할 수 없음 |
| build | UE5.8.3 성공 | ✅ `build.ps1` Succeeded(C++ 무수정, 엔진 헤더 C4996 경고만) |
| audio_import | 7개+재임포트7개·loop/gain | ✅ 헤드리스 `-run=pythonscript`: `WP13_IMPORT_VERIFIED_7_REIMPORT_7`, 0 errors/0 warnings. ATTRIBUTION·크레딧 재생성 diff 없음 |
| Audio 필터 | Golmok.Audio 2/2 | ✅ `test.ps1 -Filter Golmok.Audio` 2 Success(Footstep·StateMachine) |
| 전체 자동화 | 28 Success, RenderEvidence 미실행 별도 | ✅ 28 Success(21 + 경고 7), failed 0/notRun 0, 167.5 s. `RenderEvidence`는 설계대로 NOT EXECUTED |
| 콘솔/HUD | 상태·mute·auto·출처/확인일 | ✅ `golmok.audio` → `audio: outdoor_day [outdoor_day / ] vol 0.70`. `.mute 1`이면 ` muted`·무음, `.mute 0`이면 복귀. `.state outdoor_night/interior/outdoor_day/auto` 동작, 잘못된 값은 usage. `credits`는 7항목(제목—저자·URL·라이선스·`Verified: 2026-09-28`·수정 내역). HUD `audio:` 줄 표시(`pc-verify-wp13-hud.jpg`) |
| 낮/밤·실내 | 각3회·실내 우선·복수 소스 | ✅ 키 1·4·2·4·3·F5·F5로 낮↔밤 3회씩: −50.3 ↔ −53.9 dBFS, 1 dB 안착 1.66~1.93 s(2 s 페이드, 12회 중 1회는 잡음으로 3.0 s), 중간 dip 1.6~2.1 dB. 포털을 걸어서 실내 3회 진입·복귀: −55.6 dBFS ↔ 낮. 제3상태(밤 전환 0.4 s 뒤 실내): 끊김 없이 이어짐(최저 −58, 실내 대비 −2.5 dB). 복수 포털 소스 GUI는 미실행(헤드리스가 검사) |
| 포털 | 1초 안 왕복3회·클릭 없음 (T8 정정: 0.5 s 간격 3왕복) | ✅ 클릭 없음. 문 평면 순간이동으로 0.33 s 간격 6회 통과(3왕복 1.64 s)와 0.5 s 간격 3왕복(왕복당 1 s). `MinCrossingIntervalSeconds=0.25` 때문에 3왕복을 1.25 s 안에는 할 수 없음. 발소리를 끈 구간의 클릭 z 최댓값 4.2(판정 8, 자체 시험의 하드컷은 z 160). 레벨이 −50 → −53.7로 부드럽게 출렁였다가 복귀 |
| 크로스페이드 | 기본2초 vs 실내1초/실외2초 | ✅ 측정: 2.0 s면 → 실내 안착 1.83 s, 1.0 s면 0.94 s(0.66 s에 dip 2.5 dB). → 실외 2.0 s는 1.84 s로 양쪽 같음. 1.0 s는 빠른 왕복에서 더 깊게 출렁임(−56.5). 차트 `pc-verify-wp13-crossfade.jpg`. **체감 판정은 소유자 청취**. Fable 설계 의견은 §7-3 |
| 재질별 발소리 | default/asphalt/tile/stairs 걷기·달리기10보 | ✅ L_Dev Floor PIE 한정 override(§7-5): SurfaceType2 → `SW_tile`, 3 → `SW_stairs` 확인; 미지정·SurfaceType1은 둘 다 `SW_asphalt`(`audio.json`의 `sets.default`와 `sets.asphalt`가 같아 현 설정에서는 구분할 수 없음). 각각 걷기 11보(71.7 cm/보)·달리기 12보(109 cm/보). `Course/Stairs` 태그 계단 → `SW_stairs`(걷기 8보 중 계단 위 7보, 달리기 5+5보). 합성 Zone 충돌 바닥 → default `SW_asphalt` 10보 |
| 로스터별 발소리 | proxy135/proxy110/Quinn 각10보·스케일 필요성 | ✅ 실행: 각 걷기 10~11보, 달리기 11~12보, 소리 보폭은 고정(걷기 72~77, 달리기 109~112 cm). 애니메이션 발 딛기와의 비율(소리 ÷ 애니)은 걷기 Manny/Quinn 0.92·proxy135 0.70·proxy110 0.59, 달리기(애니 보폭 ÷ 소리 보폭 109~112 cm) Manny/Quinn 1.30~1.34·proxy135 1.27~1.30·proxy110 1.03~1.06(비율 = 발소리 횟수 ÷ 애니 발 딛기 횟수 = 애니 보폭 ÷ 소리 보폭; 세션 기록의 1.27·1.22는 소리 보폭 115~116 cm 기준 값이었음). **`stride_scale_by_mesh`(Z 스케일 곱)는 권장하지 않음**: proxy 걷기는 1.03~1.05로 맞지만 달리기가 1.7배로 나빠짐. 대안은 §7-3 |
| 착지 | 점프5회·공중 무음·착지1회 | ✅ 제자리 점프 5회 → `SW_landing` 5회, 발소리 0. 달리며 점프 2회 → 착지 2회, 공중 구간 발소리 없음 |
| Photo mute/maintain | 양 모드·원샷 정지/억제·채널0 | ✅ mute: 진입 시 앰비언스와 재생 중 원샷이 20~40 ms 램프로 무음(클릭 없음), 종료 즉시 복귀, describe ` muted`. maintain(JSON 수정·재시작): Photo 중 레벨 불변(이 구간에는 캐릭터가 움직이지 않아 발소리 없음). 사용자 `.mute 1`은 maintain 설정에서도 무음. Photo 안에서 두 가지를 겹친 경우는 미실행 |
| 발소리 중복·루프 이음·clipping | (§3 청취 항목) | ✅ 동시 발소리 보이스 최대 2, 보폭 1회당 1인스턴스. 4 s 루프 이음이 약 9회 지나는 구간에서 클릭 없음(z 최댓값 4.5). clipping 0 샘플, 전체 피크 −32.1 dBFS |
| 소유자 밸런스 | 장치·OS 볼륨·master/상태/발소리 gain JSON 값 | ⏳ **C-08 소유자 청취·최종값 대기**. T8([PR #55](https://github.com/wooklym/golmok/pull/55), 2026-09-29) 임시 적용: master 1.0 / 낮 0.5·밤 0.36·실내 0.30 / 발소리·착지 1.0, 자체 발소리·착지 거리 감쇠 제거(2D). V-10의 이전 측정(master 0.7, 상태 0.25/0.18/0.15, 발소리 0.5·착지 0.6)은 낮 RMS −50.3·밤 −53.9·실내 −55.6, 발소리 피크 −35.8·착지 −34.7 dBFS, OS 52 % 루프백 낮 −60.5 dBFS였다. gain 변경만 계산하면 앰비언스·발소리 약 +9.1 dB(master +3.1, gain ×2 +6.0), 착지 +7.5 dB(×1.67), 착지/발소리 상대 −1.6 dB. 자체 발소리의 감쇠 제거 영향은 별도(붐 간 실측 차 1.6 dB; 선형 falloff 추정 +2.5~4.8 dB, Manny 피크 ≈ −22 dBFS 예상)이므로 새 출력 레벨·clipping 없음은 측정 전 단정하지 않는다. C-07 뒤 같은 장치·OS 볼륨으로 재녹음(§7-1a 도구)·청취한다 |
| 패키징 | SW7개·audio.json 포함·재생/크레딧 | ✅(발소리 제외) BuildCookRun 성공. 첫 실행은 "Live Coding active"로 실패 → `package.ps1` PC fix 뒤 통과. stage manifest와 `.utoc`에 SW 7개(.uasset+.ubulk), `.pak`에 `Config/Golmok/audio.json`. 패키지 실행: `golmok.audio`·`credits` 출력, `-ExecCmds`로 night·interior 전환, 루프백 낮/밤/실내 −60.5/−64.2/−65.6 dBFS. **패키지 발소리 청취는 미확인**: 05:46부터 떠 있는 Windows 보안 시스템 대화상자가 포커스를 막아 키 입력 불가(§7-4). **V-10b 재시도(2026-10-04, §8-1)**: 새 패키지에서 `golmok.audio`·크레딧·`missing SoundWave` 없음·루프백 재생은 확인, W 발소리 1회는 새 exe 경로의 방화벽 알림 창이 다시 떠 미실행 |
| 고친 API | 위 번호·변경/재검증 근거 | A1~A9 코드 수정 없음. PC fix는 `tools/ue/package.ps1` 1건(`-ubtargs=-NoHotReloadFromIDE`, Astra 레인 아님)과 이 런북의 cook 확인 명령 정정. Astra 레인 코드·설정·에셋(`Source/Golmok/Audio/`·`audio.json`·`Content/Golmok/Audio/`)은 수정하지 않음. 레인 문서인 이 런북은 PC 세션이 결과 칸(§4·§6)·cook 확인 명령(§5)·§7을 수정(D-019 규칙 2026-09-28: PC 검증 세션은 레인 런북의 결과·확인 절을 고칠 수 있고, 병합 때 양쪽을 살린다) |
| STATUS 판정 | 통과/부분/차단·남은 항목 | **WP-13 🟢**, V-10 🟢. WP-13 코드 결함 0(도구·런북 결함 2건은 PC fix)이고 기능·전환·클릭·재질·착지·Photo·패키징(앰비언스·크레딧)이 통과. 비차단으로 남은 항목: ① 소유자 볼륨 청취·최종 gain(후보 위), ② 패키지 발소리 1회 청취(보안 대화상자를 소유자가 처리한 뒤), ③ 크로스페이드 1.0/2.0 체감, ④ 실제 음원 교체(결정 필요 ③) 뒤 재청취, ⑤ 미실행(비차단): A1 600 cm 경계·A7 경로 재생 빙의 교체·복수 포털 소스 GUI·Photo 안 사용자 mute+maintain 겹침·StopOldest 실동작(보이스가 8 한도에 닿지 않음), ⑥ T6 #50 런타임 변경(HUD 핸들·ToD 초기화·DoesPackageExist·이름 없는 표면 default)은 헤드리스만 — 다음 PC 카드에서 스모크 |

### T6(13c) 후속 확인 범위

ToD가 파괴되면 다음 재탐색(최대 0.25 s)에 프리셋·실내 상태를 초기화해 auto는 outdoor_day로 돌아간다. 새 ToD에 다시 바인딩하며 명시적인 강제 상태는 유지한다. 0.25 s 폴링은 Controller와 ToD의 수명·재탐색만 담당하고, 기존 ToD의 프리셋/실내 변경은 이벤트로 즉시 반영한다.

실내 broadcast는 기존대로 EnsurePresets 성공 조건 안에 있다. 프리셋 로드 실패 시 오디오 이벤트도 발행하지 않는다(B-7, 코드 변경 없음). SoundWave는 패키지 존재를 먼저 검사하므로 임포트 전 파일 누락은 HUD의 missing SoundWave 진단으로 남는다. 실제 임포트 후 PIE를 다시 시작하고 패키징/청취는 별도로 확인한다.

C-10: Packaging 설정을 에디터에서 저장한 뒤 DefaultGame.ini의 중복 ProjectPackagingSettings 섹션과 Audio cook 항목을 git diff로 확인한다. 훅 표지 유실이나 항목 제거를 그대로 커밋하지 않는다. C-2 Shipping 크레딧 UI는 이번 T6 배정에서 제외, 실제 음원 확정 뒤 별도 배정이다. D7은 당시 Fable이 V-10 뒤 재검토를 조건부 허용한 가설이었다. V-10 측정 뒤 T8에서 메시 스케일 곱을 기각하고 캐릭터별 보폭 데이터로 대체했다.

## 7. V-10 실행 기록 (2026-09-29, PC)

### 7-1. 방법

- 드라이버: V-09b `pie_driver.py`에 오디오 단계를 더한 것(세션 scratchpad `v10/`, 미커밋 — 후속(다음 PC 카드): WAV 분석(100 ms RMS 안착·클릭 z)을 순수 Python/numpy 스크립트로 테스트와 함께 `tools/` 아래에 커밋해 T6 스모크·실제 음원 재청취 때 같은 판정을 재현할 수 있게 한다 → §7-1a). 에디터 GUI를 `-ini:Engine:[Audio]:UnfocusedVolumeMultiplier=1.0`으로 띄우고(포커스 영향 제거), 새 창 PIE(Alt+P)와 SendInput 키(1~4·F5·W·Shift)를 쓴다.
- 녹음: PIE 월드에서 `unreal.AudioMixerLibrary.start_recording_output(world, s)` → `stop_recording_output(world, AudioRecordingExportType.WAV_FILE, name, dir)`(Python 이름은 `AudioMixerLibrary`, `ScriptName` 메타데이터). master submix 출력이라 OS 볼륨 전 신호다.
- 분석: 100 ms RMS 포락선(안착 = 최종 레벨 ±1 dB 진입 시각), 클릭 = 1차 차분을 국소 강건 σ(MAD, ±100 ms)로 나눈 z(발소리 원샷 구간 제외, 판정 z ≥ 8). 합성 베드가 32탭 이동평균 노이즈라 차분이 백색에 가깝다. 자체 시험에서 의도적 하드컷은 z 160, 2 s/1 s 선형 페이드는 안착 2.09/0.85 s로 검출됐다.
- 발소리 식별: `ListWaves`(0.1 s 샘플, 재생 위치 되감김 = 새 인스턴스)로 웨이브 이름·동시 보이스 수를 센다. 애니메이션 cadence는 foot_l/foot_r 소켓의 진행 방향 간격을 자기상관해 구한다(주기 = 2보).
- 패키지: `build\Windows\Golmok.exe`(부트스트랩이 실제 `Golmok\Binaries\Win64\Golmok.exe`를 띄움)를 `-forcelogflush -ExecCmds=…`로 실행하고, 기본 출력 장치의 WASAPI 루프백을 PowerShell+C# interop로 캡처했다(설치 없음, 읽기 전용).

![HUD audio 줄(L_ZoneTest 실내, 실행 A)](pc-verify-wp13-hud.jpg)

![녹음 포락선: A(전 상태 2.0 s) vs A2(interior 1.0 s)](pc-verify-wp13-crossfade.jpg)

### 7-1a. 저장소 분석 도구(R53-5)

- 위 WAV 분석은 `tools/golmok_tools/audio_analysis.py`로 다시 돌린다(tools venv, numpy만 필요): `cd tools; python -m golmok_tools.audio_analysis <녹음.wav> --event <키 입력 s> … --fade 2 --exclude <발소리 t0:t1> … [--json] [--trace] [--check]`. PCM 8/16/24/32·float 32/64 WAV(EXTENSIBLE 포함)를 읽는다. 헤더의 data 크기가 0이거나 파일보다 큰 미종결 녹음은 파일 끝까지 읽고, 오디오 프레임이 하나도 없으면 오류(종료 코드 2)다. 레벨·안착·dip은 채널 평균(모노 믹스)으로 재고, 클릭 z와 급정지는 믹스와 채널마다 따로 잰다. 한 채널에만 있는 결함이 믹스에서 묽어지지 않게 하려는 것이다(서로 무관한 두 베드의 왼쪽에만 넣은 0.3 스파이크: 믹스 z 15.5, 채널 22.2. 한 채널만의 하드컷은 믹스에서 3~6 dB만 떨어져 채널에서만 급정지로 잡힌다).
- 출력: 피크 dBFS·clipping 샘플 수·전체 RMS·클릭 z 최댓값과 시각·채널(판정 z ≥ 8, 스테레오는 믹스·채널별 값도 한 줄)·급정지(abrupt stop) 수와 처음 5개(시각·하강 dB·등가 램프 ms, 스테레오는 채널마다 한 줄 더), 이벤트마다 직전/최종 레벨·1 dB 안착·중간 dip. 안착은 이벤트 뒤 `--span`(기본: `--fade`가 있으면 페이드 + 1 s, 없으면 3 s; 다음 이벤트 전까지) 안에서 잰다. 100 ms 창 하나가 ±0.4 dB 흔들려 구간이 길면 늦은 이탈 한 번에 안착이 구간 끝으로 밀린다. `--trace`는 이벤트마다 0.3 s 앞부터 구간 끝까지의 100 ms 포락선(JSON `events[i].trace`의 `t`·`db`, 텍스트는 10개씩 한 줄)과 300 ms 에너지 평균 포락선으로 잰 안착(`settle_s_smoothed`)을 더한다. 늦은 이탈 한 번이 안착을 끌어갔는지 이것으로 본다. JSON에는 NaN/Infinity를 쓰지 않고 null로 바꾼다.
- 판정·종료 코드: `--check` 없이 종료 코드 0은 "분석이 끝났다"는 뜻이지 **통과가 아니다**. `--check`를 주면 클릭(z ≥ 8)·급정지(믹스나 어느 채널이든)·clipping·NaN/Inf 표본 가운데 하나라도 있으면 1, 없으면 0이고 마지막 줄에 `check` 결과를 쓴다(JSON은 `check.failed`). 읽을 수 없는 파일은 언제나 2다.
- 클릭 z 계산: 모든 표본을 자기 ±창으로 재지는 않는다(표본마다 중앙값 계산). 창/4 격자에서 MAD를 구한 뒤 두 단계로 후보를 다시 잰다. 1단계 격자 휴리스틱은 보통 소재에서 전수 계산과 같지만 무음 경계·게이트 소재·몇 LSB 크기의 16-bit 베드에서는 최댓값을 놓칠 수 있다(합성 게이트 소재 67.6 대 전수 99.1). 2단계는 두 격자점 사이 σ의 증명된 하한으로 후보를 고르므로 판정(z ≥ 8 여부)은 전수 계산과 항상 같고, 후보가 1000개 이하이면 최댓값도 전수와 같다. 플레이스홀더 베드처럼 최댓값 근처 표본이 많은 소재에서는 값이 1단계 값이다. 3분 48 kHz 스테레오(믹스와 두 채널)는 약 20 s, 표본 외 메모리 약 0.37 GB다.
- 무음 처리: |x| < 1e-4(약 −80 dBFS, `--silence-floor`로 바꿈, 0이면 모든 표본을 넣는 V-10 방식)를 무음으로 보고, 클릭 σ(MAD)는 ±100 ms 창 안의 비무음 차분만으로 계산한다. 창의 25 % 미만이 비무음인 샘플은 채점하지 않는다. 그래서 무음으로 가는 페이드와 무음 하드컷이 더 이상 z를 부풀리지 않는다. 플레이스홀더 베드에서 20 ms·250 ms 선형 페이드는 z ≈ 2.5·2.9다(이전 12~16·7~11). 하드컷은 컷 지점의 계단을 베드 자신의 σ로 채점해 z ≈ 3.7 × |컷 직전 표본| / 베드 RMS, 곧 2.4~6.5다(이전 수천, PC 자체 시험 160). 큰 표본에서 끊기면(무작위 컷의 약 3 %) 8을 넘을 수 있는데 이는 실제 계단이다. 소리 구간 안의 클릭(0.3 스파이크 z ≈ 22)은 무음 바로 옆에서도 그대로 잡힌다. −80 dBFS보다 조용한 소재는 무음으로 취급되고, 그에 가까운 베드는 영점 부근 표본도 빠진다(베드 −65 dBFS RMS: 표본 14 %, z 6~8 % 상승).
- 급정지(`abrupt_stop`, 기본 20 dB·10 ms·5 ms 창): 5 ms RMS 레벨이 기준보다 20 dB 이상 떨어지는 하강 중 10 ms 안에 끝난 것을 목록에 올린다. 하드컷, 무음이나 훨씬 조용한 베드로의 컷, 약 5 ms 이상의 끊김이 해당한다. '10 ms 안'은 등가 선형 램프로 판정한다. 무음 시작 직전 10 ms가 기준 전력(그 앞 100 ms 에너지 평균)의 1/3 이상을 유지하면 급정지다. 1/3은 정확히 10 ms인 선형 램프가 남기는 값이다. 보고하는 ms는 같은 전력비를 남기는 선형 램프 길이다(하드컷 ≈ 0). 플레이스홀더 베드 경계(시드 300개): 하드컷 300/300(0~9.4 ms), 5 ms 램프 95 %, 10 ms 43 %, 12 ms 13 %, 15 ms 1 %, 20·40·250 ms 0 %. 하강 dB는 5 ms 창 하나로 읽어 ±2 dB 흔들린다. 떨어지는 쪽만 찾고 무음에서의 급시작은 찾지 않는다. V-10의 Photo mute 진입(20~40 ms 램프)은 선형 램프라면 목록에 오르지 않는다. T8의 0.25 s 페이드 뒤에는 급정지 0이 기대값이다.
- 녹음·키 입력·`ListWaves`·WASAPI 루프백을 하는 PC 드라이버(V-09b `pie_driver.py` 오디오 단계)는 여전히 세션 scratchpad에만 있고 저장소에 없다.

### 7-2. 실행 목록

| 실행 | 맵·설정 | 내용 |
|---|---|---|
| A | L_ZoneTest, audio.json 기본(2 s·mute) | 녹음 183 s: 시간대 키 7회, 포털 걷기 3회, 빠른 포털 0.33/0.5 s, Zone 바닥 걷기, 제3상태, Photo, mute·state 콘솔 |
| A2 | 같은 시나리오, `crossfade_seconds_by_state.interior=1.0`, `pause_policy=maintain`(실행 뒤 `git checkout`) | 녹음 183 s, A와 비교 |
| B | L_Dev | 점프 5+2회, 로스터 proxy135/proxy110/quinn/manny 걷기·달리기, 발 소켓 궤적, PIE 재시작 3회 |
| bm | L_Dev, PhysicalSurfaces 이름 3개를 `DefaultEngine.ini`에 임시로 넣음(실행 뒤 `git checkout`) | 재질 4종 걷기·달리기, `Course/Stairs` 태그 계단 |
| pkg | 패키지 L_Dev | 크레딧·상태 출력, 낮/밤/실내 루프백 |

### 7-3. Fable 설계 의견(청취 전 가설, 결정은 오케스트레이터·소유자)

1. **실내 1.0 s / 실외 2.0 s는 채택 후보**: 문 통과는 공간 이벤트라 시간대 전환(2 s)보다 빨리 바뀌는 편이 자연스럽다. 측정상 1.0 s도 클릭·끊김이 없다. 다만 빠른 왕복에서 출렁임이 커지니 소유자 청취로 확정한다.
2. **동일 전력(equal-power) 크로스페이드**: 현재 선형 진폭 보간은 서로 무관한 두 베드를 섞을 때 중간에 1.6~2.8 dB 꺼진다. sin/cos 곡선이면 일정하게 유지된다. `GolmokAudioMath::Envelope` 곡선만 바꾸는 폴리시 후보(Astra 레인)다.
3. **발소리 보폭**: ABP_Unarmed의 걷기 cadence는 속도와 상관없이 2.68 보/s로 고정이다. 고정 보폭(70/110 cm)은 Manny 걷기(애니 67 cm)에는 맞지만, 달리기(애니 146 cm)에서는 발소리가 약 30~34 % 많다(소리 보폭 109~112 cm 기준). proxy 걷기(애니 54·45 cm)에서는 0.70·0.59배로 적다. `stride_scale_by_mesh`는 달리기를 1.7배로 망치므로 **권장하지 않는다**. 대안은 캐릭터별 (걷기, 달리기) 보폭 데이터다. 측정값은 Manny/Quinn 67/146, proxy135 54/142, proxy110 45/115 cm(각 캐릭터 걷기·달리기 속도 기준). 또는 V-08 애니메이션 채택 뒤 노티파이 구동으로 바꾼다(WP-13 원래 계획).
4. **Photo mute 진입**은 20~40 ms 안에 뚝 끊긴다(클릭은 없음). 0.2~0.3 s 짧은 페이드는 폴리시 후보다.
5. 합성 플레이스홀더 7개는 같은 공식(필터 노이즈 ± 95 Hz)이라 **세 앰비언스와 네 발소리 세트가 음색으로는 거의 구분되지 않는다**(gain 차이만 있음). 품질 판정은 실제 음원 교체(결정 필요 ③)나 WP-17 녹음 뒤에 한다.

### 7-4. 막힌 것·환경

- **Windows 보안 대화상자**: 05:46쯤부터 `PickerHost.exe`의 `Shell_SystemDialog`(제목 "Windows 보안")와 전체 화면 `Shell_SystemDim` 오버레이(최상위)가 떠 있다. 이 때문에 다른 창을 포그라운드로 만들 수 없고 SendInput 키가 게임에 들어가지 않는다. 패키지 `Golmok.exe`를 처음 실행할 때 뜬 방화벽 허용 프롬프트로 보인다. 보안 설정이라 세션은 누르지 않았다. 소유자가 처리한 뒤 패키지에서 W 걷기 발소리를 1회 확인한다(수동: `build\Windows\Golmok.exe` 실행 → L_Dev에서 W로 걷기 → 발소리 확인. 세션 드라이버는 저장소에 없다).
- `-log`로 패키지를 띄우면 로그 콘솔 창이 포그라운드를 가져간다. `-forcelogflush`만 쓴다. 부트스트랩 `Golmok.exe`를 종료해도 실제 게임 프로세스는 남는다.

### 7-5. 재현 메모

- T8 새 계약: Physics 표면 이름은 audio.json 세트 id와 대소문자 무관하게 일치해야 한다(1=asphalt, 2=tile, 3=stairs). 불일치/미정의는 default·HUD 오류 및 월드별 번호당 1회 Warning이다. 아래는 이전 V-10 시험 이력이다.
- PhysicalSurfaces 이름이 프로젝트에 없어서 Python에는 `unreal.PhysicalSurface.SURFACE_TYPE_DEFAULT`만 노출된다. 이 상태에서는 `set_editor_property("surface_type", …)`로 SurfaceType1~를 줄 수 없다. PIE 콘솔 `set <obj> SurfaceType SurfaceType2`도 GUI 에디터에서는 `ProcessUserConsoleInput`이 가로채 적용되지 않는다(헤드리스 commandlet에서만 적용됨). 재질 시험은 `DefaultEngine.ini`에 `[/Script/Engine.PhysicsSettings] +PhysicalSurfaces=(Type=SurfaceType1,Name="V10Asphalt")` 등 3줄을 **임시로** 넣고 한 뒤 `git checkout`한다. Zone 에셋 단계에서 이름을 정식으로 정의하면(B 항목 C-11) 이 문제는 없어진다.
- 임포트로 생긴 `Content/Golmok/Audio/{ambience,footsteps}/SW_*.uasset`은 gitignore 대상이 아니라 untracked로 보인다. 커밋할 때 제외해야 한다(후속: ignore 규칙 검토).


## 8. T8 재검증 범위 (13d, 2026-09-29)

- 헤드리스: 전력 보간·재전환·50ms 교체, 설정 타입/범위와 선택 보폭, `audio:` 공급자 실제 줄·상대 개수, 표면 이름/세트 id 대조, GamePause 중 Photo envelope의 목표 도달을 검사한다. mute가 아니거나 fade=0이면 이 시나리오는 NOT EXECUTED로 안내한다. 결과는 [WP-13 T8 결과](../plan/WP-13-ambience-audio.md)에 기록한다.
- PC: T6 수명/HUD/누락에셋 스모크와 T8 보폭·2D 자체 발소리·Photo 원샷 FadeOut·빠른 포털·새 gain을 재녹음/청취한다. `steps=`로 default/asphalt를 구별하고 `error: missing SoundWave`가 없는지 확인한다. C-07 해소·GUI 잠금 확인 뒤 실행한다.
- §7-5의 `V10Asphalt` 등은 이전 시험에서만 사용한 이름이다. T8 시험에는 §3의 정확한 세트 이름을 쓴다. 생성 `Audio/*/SW_*.uasset`은 PR #54부터 ignore되며 소스/JSON/임포터로 재생성한다.
- R50-3: T6 전체 자동화의 경고 테스트 수 7→8은 `Audio.StateMachine`이 ToD 파괴/재생성을 검사할 때 기록된 `No AGolmokGeoOrigin in L_Dev: zones are placed with their own origin at the level origin (dev level mode). Place one AGolmokGeoOrigin at (0,0,0) with the basemap area origin for geo-referenced placement.`다. L_Dev 배치 경고이며 오디오 누락 경고가 아니다. ExpectedMessage로 감추지 않고 보고서에 남긴다.

### 8-1. V-10b PC 스모크 결과 (V-11 카드, 2026-10-04)

PC 세션(Opus 5.5, 워크트리 `sharp-wright-5b1e4a`, 브랜치 `pc/v11-verify-wp18` ← main `8e7cfc5`, Audio 코드 = T8~T19 반영본). 판정 근거는 §7-1과 같은 master submix 녹음(`AudioMixerLibrary`, 48 kHz 스테레오, OS 볼륨 전)과 `ListWaves` 0.1 s 샘플이며 **사람 귀 청취가 아니다**. 수치 분석은 저장소 도구 `python -m golmok_tools.audio_analysis`(§7-1a)로 했다. 출력 장치는 V-10과 같은 기본 장치다. 녹음 WAV·보고서는 PC 로컬 `C:\Users\user\golmok-pc-recordings\v11-2026-10-04\wav\`에 있다(커밋 안 함). 임포트는 헤드리스 `WP13_IMPORT_VERIFIED_7_REIMPORT_7`(크레딧 diff 없음).

![HUD audio 줄: L_ZoneTest 실내(위), L_Dev 미정의 SurfaceType1 바닥(아래)](pc-verify-wp13-v10b-hud.jpg)

| 항목 | 기대 | 결과 |
|---|---|---|
| T6 HUD `audio:` 줄(핸들 API) | HUD에 줄 표시 | ✅ `audio: interior [outdoor_day / interior] vol 1.00 steps=default drv=distance(auto) ev=0 photo_gain=1.00`(위 그림). 낮·밤·실내 HUD 스크린샷 3장 로컬 |
| T6/T8 `golmok.audio` | `steps=`·`photo_gain=` | ✅ 모든 출력에 `steps=<세트> drv=distance(auto) ev=0 photo_gain=<값>`. Photo 중 `photo_gain=0.00 muted`. `golmok.audio credits` 7항목 |
| 낮/밤 전환(키 4·2 각 3회, L_ZoneTest 정지 상태) | 2.0 s 크로스페이드·끊김 없음 | ✅ 낮 −41.0 ↔ 밤 −44.7 dBFS. 키 입력부터 안착(300 ms 평균) 1.24~1.61 s(조명 전환 중점에서 상태 이벤트가 나므로 키 기준). 중간 dip 0.3~1.2 dB(V-10 선형 보간 1.6~2.1 dB). 급정지 0 |
| T8 실내 진입 ≈ 1 s(발소리 끈 run v11f, 포털 3왕복) | 실내 1.0 s·실외 2.0 s | ✅ 실내 진입 안착 0.82~0.92 s(dip 0.3 dB), 실외 복귀 1.22~1.54 s(dip 0.6~1.4 dB). 실외 −41.1 / 실내 −46.3 dBFS. 문 평면 통과 시각 기준 |
| T8 Photo 진입/해제 0.25 s 페이드(무클릭) | mute 0.25 s S-curve | ✅ 정지 상태 2회: P 뒤 0.28~0.37 s에 무음(−120 dB), 해제 뒤 0.28~0.34 s 안착, 급정지 0·클릭 없음(클릭 z ≥ 8은 전부 발소리 원샷 시작점). 걷기 직후 P 3회(v11f): 재생 중이던 발소리 원샷이 `ListWaves` 볼륨 0.99 → 0.93 → 0.34 → 소멸(≈ 0.3 s)로 FadeOut, 앰비언스는 0.26~0.29 s에 무음 |
| 이름 없는 SurfaceType → default(T6 C-11) | default + HUD error + 표면 번호당 Warning 1회 | ✅ L_Dev Floor에 PIE 한정 PhysicalMaterial(SurfaceType1)을 두고 런타임에 `PhysicsSettings` CDO 배열에서 SurfaceType1 항목을 뺐다 → `steps=default` + `error: surface 1 needs Physics name 'asphalt' (actual 'undefined'); physical mapping ignored`, Warning 1회. 이름이 다른 경우(SurfaceType2 = `V11Mismatch`) → `steps=default` + `actual 'V11Mismatch'` Warning 1회. 원래 이름으로 되돌리면 `steps=tile`. 이름이 맞는 0/1/2/3 → `default`(SW_asphalt)/`asphalt`(SW_asphalt)/`tile`(SW_tile)/`stairs`(SW_stairs). 시험용 `DefaultEngine.ini` `PhysicalSurfaces` 3줄(1=asphalt, 2=tile, 3=stairs)은 run 뒤 `git checkout`(diff 없음) |
| T8 캐릭터별 보폭(L_Dev 평지, 걷기 6 s·달리기 4 s) | proxy110 걷기 간격 < manny(45 vs 67 cm) | ✅ 발소리당 이동 거리 — manny 67.1/149.4, quinn 67.1/149.4, proxy135 54.1/135.1, **proxy110 47.8/110.8 cm**(걷기/달리기; 짧은 구간이라 개수 내림 오차 포함, 설정 67/146·54/142·45/115). 걷기 발소리 시간 간격은 4종 모두 ≈ 0.37 s(보폭 ÷ 속도가 같음). 동시 발소리 보이스 최대 2 |
| T8 2D 자체 발소리(붐 길이 무관) | 캐릭터 간 피크 차 없음 | ✅ 발소리 피크 중앙값 manny −22.4, quinn −22.5, proxy135 −22.7, proxy110 −22.6 dBFS(붐 320/320/260/227 cm; 범위 −24.4~−20.2, 볼륨 0.9~1.0 무작위 폭 안). V-10의 3D 감쇠·이전 gain에서는 −35.8/−34.5/−34.2였다. 착지 3회 −22.0~−23.6 dBFS, 공중 발소리 0 |
| clipping·`error: missing SoundWave` | 없음 | ✅ clipping 0, 최고 피크 −20.2 dBFS. PIE 6회 로그에 `missing SoundWave`·`error:` 없음(표면 시험의 의도된 `error: surface` 제외) |
| 패키지 W 걷기 발소리 1회·`error: missing SoundWave` 없음(T6 R50-6) | 패키지 실행 | 부분 ✅ / 발소리 ⛔ 미실행. 패키지 빌드 성공(BuildCookRun 287 s, stage manifest에 SW 7개·`Config/Golmok/audio.json`). 다른 PC 세션 GUI 단계가 모두 끝난 뒤 `build\Windows\Golmok.exe -windowed -forcelogflush -ExecCmds=golmok.audio,golmok.audio credits`(L_Dev) 실행: `audio: outdoor_day [outdoor_day / ] vol 1.00 steps=none drv=distance(auto) ev=0 photo_gain=1.00`, 크레딧 7항목, 로그에 `missing SoundWave`·`error:` 없음. 같은 장치(DELL U2724D, OS 52 %) WASAPI 루프백 42 s: 낮 앰비언스 RMS −51.0 dBFS(V-10 −60.5 → +9.5 dB, T8 gain 변경 계산 +9.1 dB), clipping 0. **W 걷기 발소리 1회는 미실행**: 실행 6 s 뒤 Windows 방화벽 알림 창이 떠서(아래) 드라이버가 키 입력 전에 멈췄다 |

**막힌 것(2026-10-04 20:05:43 KST)**: 패키지 첫 실행과 같은 시각에 `C:\Windows\System32\PickerHost.exe FirewallNotificationDialogServer -Embedding`이 "Windows 보안" 창(클래스 `Shell_SystemDialogProxy`)을 띄웠다. 내용: "공용 및 프라이빗 네트워크에서 이 앱에 액세스하도록 허용하시겠습니까?", 앱 Golmok, 게시자 Epic Games, Inc., 버튼 허용/취소. 대상은 이 워크트리의 새 경로 `C:\Users\user\golmok\.claude\worktrees\sharp-wright-5b1e4a\build\Windows\Golmok\Binaries\Win64\Golmok.exe`다(이전 두 경로 `upbeat-rosalind-95c87c`·`stoic-kare-964e86`에는 소유자가 만든 인바운드 허용 규칙이 있다). 세션은 누르지 않았고 게임만 종료했다. 원인: 같은 시각 패키지 로그 `LogTrace: Display: Control listening on port 1985` — 엔진 TraceLog 제어 소켓이 Development 빌드에서 TCP 1985를 모든 인터페이스(`INADDR_ANY`)에 바인딩한다(`Engine/Source/Runtime/TraceLog/Private/Trace/Control.cpp` `Writer_ControlListen`, `Detail/Windows/WindowsTrace.cpp` 185행). UDP 메시징은 패키지 게임에서 `-messaging` 없이는 켜지지 않는다(`UdpMessagingModule.cpp` `IsSupportEnabled`). 따라서 패키지 exe 경로가 바뀔 때마다 같은 창이 뜬다. 후속 후보(오케스트레이터 판단): PC 패키지 스모크용 고정 출력 경로(`package.ps1 -OutDir`)를 정해 소유자가 한 번만 허용하게 하기.

관찰(판정 아님):
- 드라이버가 포털 앞으로 300 cm보다 짧게 순간이동하면 발소리 1회가 났다(`teleport_threshold_cm` 300 설계대로 이동 거리로 셈).
- Photo 3회차 mute 동안 출력에 ±2 LSB(−97 dBFS RMS) 잔여 신호가 있었다(1·2회차는 디지털 무음). 들리지 않는 크기지만 `audio_analysis`가 이 잔여와 0 사이 깜박임을 급정지 17건으로 셌다: 급정지 판정이 하강 전 5 ms 레벨을 무음 기준(−80 dBFS)과 비교하지 않기 때문이다(도구 후속 후보). 이 구간을 빼면 급정지는 0이다.
- 볼륨 밸런스 최종값은 C-08 소유자 항목이다. 위 레벨은 T8 후보 gain(master 1.0·낮 0.5·밤 0.36·실내 0.30·발소리/착지 1.0)의 측정치다.


## T13 — WP-19c 노티파이 발소리 계약 (2026-09-30)

`audio.json`의 선택 키 `footsteps.driver`는 대소문자를 구분하는 `distance`·`notify`·`auto`만 받는다(`Notify`는 오류). 생략/현재 기본값은 `auto`: native `AGolmokGaspCharacter` 계열이고 실제 소스 `GetMesh()->GetAnimClass()`가 `RequiresGaspPawn` 계약에 해당할 때만 notify다. 일반 폰, GASP 폰의 비GASP ABP 로스터·폴백은 distance다. T15에서 T13의 폰 클래스 단독 판정을 대체했다. 애니메이션 클래스 약한 참조 키와 판정 bool을 캐시하므로 매 틱 설정 파일을 읽지 않는다. 실제 클래스·모드 소스 세대 변경/컴포넌트 재등록 때 갱신한다(T17). 디스크 파일을 감시하는 캐시는 아니므로 설정 파일을 직접 편집했다면 재시작한다.

notify 모드는 첫 이벤트 전부터 거리 스테퍼를 멈춘다. 이벤트가 없다고 거리 방식으로 자동 전환하지 않는다(늦게 온 노티파이와 중복 방지). `UGolmokLocomotionStateComponent::NotifyFootEvent(Step/Land, bLeft)` → `OnFootEvent` → 기존 표면 세트/착지 재생 경로에 1회 전달한다. 좌우 발 구분은 현재 샘플 선택에 사용하지 않는다. distance는 이벤트를 무시하고 종전 거리·보폭·공중·착지·텔레포트 규칙을 쓴다. pause/photo 또는 현재 플레이어가 아닌 폰의 이벤트는 무시한다. OnUnregister에서 구독을 해제하며 재등록은 1회만 연결한다.

재현은 build 후 `tools/ue/test.ps1 -Filter Golmok.Audio`. 기존 등록 2개 안에서 Footstep의 합성 PIE 이벤트 시험을 실행한다. native GASP 폰만 생성하며 GASP 원본·BPI·ABP는 필요 없다. PlayFootstep 진입점의 테스트 전용 계수로 Step 1 → 발소리 요청 1, Land 1 → 착지 요청 1, 거리 이동 중복 0, pause·이전 폰·구독 해제 시 요청 0, 재등록 시 중복 구독 0을 확인한다. **-nosound/nullrhi이므로 실제 소리 출력·샘플 청취 성공은 아니다.**

### 19b/V-15 인계 — 원본 GASP 폴리 차단은 아직 미구현

`UGolmokFootstepComponent::UsesNotifyDriver()`는 **진단용 조회이며 원본 폴리 억제 조건으로 쓰지 않는다**. D-021/R79-2 결정에 따라 19b BP는 `footsteps.driver`나 이 조회 결과와 무관하게 원본 GASP 발 폴리를 항상 끄고 Step/Land만 Golmok `NotifyFootEvent`에 한 번 전달한다. 다른 폴리는 V-08b §5 분류 전까지 사용하지 않는다. 이 규칙이 T13의 조건부 억제 가설을 대체한다. 실제 원본 억제는 아직 19b 작업이며 이 C++ 수정만으로 완료되지 않는다.

19b에서는 발소리와 Land 이벤트가 각각 한 번 오는지, 원본 GASP 오디오가 남아 이중 재생하지 않는지, 실제 착지와 노티파이 시점/좌우 발·표면 샘플이 맞는지 확인한다. notify를 켜고 이벤트가 누락되면 무음이므로 이벤트 연결부터 확인한다. 원본 폴리가 음소거된 것을 확인하기 전에는 distance 진단에서도 소리 중복 여부를 별도로 검사한다. 이 작업은 19b/V-15 및 청취 검증 담당에게 넘긴다.


## T15 — auto 판정·HUD 재검증 (2026-09-30)

- `golmok.audio`/HUD의 `drv=notify(auto)`·`drv=distance(auto)`는 실제 선택(설정값)이다. 플레이어 발소리 컴포넌트가 없으면 `drv=none(...)`이다. `ev=N`은 현재 컴포넌트가 게임 스레드에서 받은 유효 Step/Land 누적 수이며 driver/pause/photo/possess 필터로 재생하지 않은 이벤트도 포함한다. 재등록으로 초기화하지 않으며 재생 성공/샘플 출력 수가 아니다.
- 헤드리스 Audio.Footstep은 L_Dev 기본 폰 대신 일반 폰을 직접 생성해 100cm 거리 스텝을 검사한다. GASP native+비GASP ABP의 auto distance, 설치된 테스트 ABP를 scoped animation 계약에 넣은 auto notify 양성·클래스 교체 캐시 갱신·재등록 뒤 재평가 1회·HUD를 검사한다. 테스트 ABP가 없으면 양성만 Info NOT EXECUTED다. 이는 실제 GASP ABP/노티파이 검증이 아니다. 기존 합성 Step/Land는 명시 notify를 사용하며 TimeDilation Photo에서 GamePause 없이도 요청이 억제됨을 검사한다.
- 텔레포트·애니메이션 재초기화 직후 원본이 가짜 Step/Land를 보내면 아직 정상 이벤트와 구별하지 못한다. 게임 스레드 가드는 추가했지만 이 시점 필터는 19b 실제 경로 확인 뒤 판단한다. OnUnregister 거리 스테퍼 초기화(R79-8)는 이번 변경 범위가 아니다.
- 실제 원본 폴리 차단·발 접지 시점·청취·패키지 출력은 NOT EXECUTED, 19b/V-15 대기다. 전체 UE 게이트 결과는 WP-13 T15 결과 및 PR 코멘트에 기록한다.


## T17 — 캐시·키 대소문자 회귀 (2026-09-30)

- 테스트 전용 RequiresGaspPawn 평가 계수로 같은 클래스/설정 세대에서 반복 조회·이벤트·Tick·HUD 후 평가가 1회인지 확인한다. 비어 있지 않은 UAnimInstance 클래스와 테스트 ABP 간 교체도 판정이 갱신돼야 한다. scoped 설정의 진입·복귀는 재등록 없이 세대 변경으로 반영된다.
- 일반 폰에 같은 GASP 계약 애님을 넣어도 auto는 distance다. pause에서 버려진 Step도 ev는 증가하지만 재생 요청은 증가하지 않는다. 양성 ABP 시험을 건너뛰면 해당 cache/class/generation/HUD Info는 NOT EXECUTED다.
- C++는 루트·에셋 메타데이터·고정 ambience 상태·footsteps·개별 보폭 객체의 알려진 필드 이름을 읽기 전에 대소문자를 검사한다. 예: MASTER_VOLUME, gain의 GAIN, walk의 WALK는 필드 경로 오류다. 알려지지 않은 확장 키를 새로 금지하지 않으며 동적 에셋 id/세트 id/프리셋 이름을 소문자로 강제하지 않는다. 이 보완이 C++/Python의 모든 검증을 같게 만들었다는 뜻은 아니다.
- 실제 GASP 원본 발 폴리 차단·발 접지·청취/패키지 출력은 계속 19b/V-15 검증이다.
