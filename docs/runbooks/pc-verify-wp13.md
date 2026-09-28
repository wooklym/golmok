# V-10 — WP-13 환경음 검증

상태: 🟢 **V-10 PC 검증 통과(2026-09-29, §6·§7)**. 녹음 파형 분석 근거로 결함 0. 남은 소유자 항목(비차단): 볼륨 청취·최종 gain(후보 §6), 패키지 발소리 1회(§7-4). 이전: 🟡 13b 코드 완료·PC V-10 패키징/청취 대기. 런타임·임포트 및 헤드리스 Audio 자동화 검증 완료.

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

콘솔: `golmok.audio` 상태·슬롯·볼륨, `golmok.audio credits` JSON 출처/저자/라이선스/수정 내역, `golmok.audio.mute 1` / `0`, `golmok.audio.state outdoor_night` / `interior` / `outdoor_day` / `auto`. `auto`로 돌아와야 실제 Lighting 이벤트를 다시 따른다. HUD의 `audio:`는 Debug 공급자를 통해 갱신된다.

`golmok.tod night`와 `clear_noon`, 포털 진입/퇴장으로 이벤트 연동을 검증한다. 실내 소스가 여러 개면 마지막 소스가 빠질 때까지 interior다. PhysicalMaterial surface0=default, 1=asphalt, 2=tile, 3=stairs 매핑은 audio.json에 있다. L_Dev의 Course/Stairs는 **에디터 폴더이며 런타임 태그가 아니다**. 기본 L_Dev 계단은 지정 재질이 없으면 default 소리가 맞다. 재질 비교 시 별도 테스트 복사 맵에서 해당 물리 재질 또는 명시적 actor tag `Course/Stairs`를 설정한다. 원본 setup_dev_level.py는 수정하지 않는다.

보폭은 걷기70/달리기110cm, 속도 기준250cm/s다. 실제 소리 재생은 한 프레임 최대1발이며 긴 프레임의 나머지 거리는 소비한다. 공중은 무음, 공중→지면 전환은 착지1회, 폰 변경/경로/포토 진입 뒤에는 누적거리를 초기화한다. pause_policy의 `mute`/`maintain`은 JSON을 바꾸고 PIE를 재시작해 각각 확인한다. 사용자 mute는 두 정책보다 우선한다. Photo 유지/뮤트 양쪽, 빠른 낮→밤→실내 재전환, 복수 포털 소스, 폰 교체/경로 재생, 걷기/달리기/공중/착지/텔레포트, 미지정 물리 재질 fallback을 확인한다.

V-10 GUI는 다른 UE 세션 종료와 GUI 잠금 확인 뒤 수행한다. 낮/밤·실내 전환 각3회, 재질별 걷기/달리기 각각10보, 점프/착지5회를 청취하고 clipping·루프 이음·발소리 중복·pause 뒤 복귀를 기록한다. 실제 청취와 자동화 로직 성공은 구분한다. 최종 야외 음원은 WP-17 현장 녹음 교체 대상이다.

로스터별 확인: `golmok.character proxy135`, `golmok.character proxy110`, `golmok.character quinn`으로 각각 교체한 뒤 걷기/달리기10보씩 청취한다. 보폭 체감과 `stride_scale_by_mesh` 필요 여부를 기록한다. 현재 고정 보폭은 승인된 가설이며 옵션 도입 여부는 이 비교 뒤 판단한다.

소유자 청취: 재생 장치(헤드폰/스피커 모델·OS 출력 볼륨)를 적고 `master_volume`, 상태별 asset gain, 발소리 asset gain의 최종 값을 audio.json에 기록한다. 플레이스홀더의 비교는 잠정이며 실제 소스 교체 뒤 다시 듣는다. mute 플래그만 헤드리스 자동화로 확인하며 채널 볼륨0·재생 중 발소리 정지는 청취 항목이다.

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

A/B 볼륨은 현재 값에서 선형 보간한다. 제3의 상태가 빠르게 들어오면 두 슬롯만으로 세 파일을 유지할 수 없으므로 더 조용한 슬롯을 최대50ms 동안0으로 낮춘 뒤 교체하고 JSON의 목적 상태별 전환을 시작한다(기본2초). 요청 상태 변경은 이벤트와 같은 프레임이고 새 파일 시작은 이 경우 최대50ms 뒤다. 이 정책은 Fable 설계 가설 승인을 받았고 합격은 V-10 청취로 결정한다. 포털을 1초 안에 실내↔실외 왕복3회 통과하며 클릭/끊김이 없는지 확인한다. Photo 유지 정책은 UI sound로 월드 pause와 분리하고, mute는 컴포넌트 볼륨을0으로 만든다. 헤드리스 자동화는 청취 증거가 아니며 출력 장치·음색·최종 밸런스를 판정하지 않는다.


`crossfade_seconds_by_state`는 진입할 상태별 초 단위 전환 시간이다. 누락한 상태는 `crossfade_seconds`를 사용하며 모두 0~30초다. 현재 세 상태 모두 2초를 유지한다. V-10에서 interior=1초, outdoor_day/outdoor_night=2초 가설을 JSON만 바꿔 비교하고 PIE를 재시작한다. 보폭에 메시 Z 스케일을 곱하는 `stride_scale_by_mesh` 제안은 이번 구현에 포함하지 않으며 로스터별 청취 뒤 후속으로 판단한다.

패키징 확인(미실행): 임포트 후 `.\tools\ue\package.ps1` 실행 → `build/Windows`의 패키징 로그/컨테이너 목록에서 Audio의 SoundWave 7개와 `Config/Golmok/audio.json`을 확인 → 패키지 실행에서 세 상태 전환과 `golmok.audio credits` 출처 출력 확인. pak은 엔진 `UnrealPak.exe <pak 경로> -List`로 조사한다. IoStore를 사용한 출력이면 해당 컨테이너 목록과 cook/stage manifest도 함께 확인한다. 파일 존재와 실제 재생/크레딧 출력을 각각 기록하고 미실행을 성공으로 표시하지 않는다.


### 런타임 불확실 API

컴파일/헤드리스 성공과 출력 장치·패키지 검증을 구분한다.

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

패키징 후 cook 파일 수 확인(7개 기대). UE 5.8.3은 Zen 스토어(`Saved/Cooked/Windows/ue.projectstore`)로 cook하므로 `Saved\Cooked\Windows\Golmok\Content\...`에 낱개 `.uasset`이 **없다**(V-10). stage manifest와 컨테이너 목록으로 확인한다:

```powershell
.\tools\ue\package.ps1
Select-String .\build\Windows\Manifest_UFSFiles_Win64.txt -Pattern 'Golmok/Content/Golmok/Audio/.*SW_.*\.uasset|Config/Golmok/audio.json'
$pak = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealPak.exe'
& $pak "-ListContainer=$((Resolve-Path .\build\Windows\Golmok\Content\Paks\Golmok-Windows.utoc).Path)" "-csv=$env:TEMP\utoc.csv"
Select-String "$env:TEMP\utoc.csv" -Pattern 'Golmok/Audio/.*SW_'
& $pak (Resolve-Path .\build\Windows\Golmok\Content\Paks\Golmok-Windows.pak).Path -List | Select-String 'audio.json'
```

`package.ps1`은 V-10부터 `-ubtargs=-NoHotReloadFromIDE`를 넘긴다. 같은 엔진 설치의 다른 에디터나 `-game`이 Live Coding을 켜 둔 상태이면, 이 인자가 없을 때 BuildCookRun이 "Unable to build while Live Coding is active"로 멈춘다(`build.ps1`과 같은 처리).

cook 파일만으로 합격시키지 않는다. 컨테이너/stage manifest의 SoundWave7개·audio.json과 패키지 실행의 재생·크레딧도 확인한다. 에디터 Packaging 저장은 중복 ini 섹션을 재작성할 수 있으므로 Audio cook 훅 보존을 diff로 확인한다. PhysicalSurfaces1/2/3 이름은 Zone 에셋 단계에서 정의한다. 13c는 audio.json에 번호 매핑이 있어도 프로젝트 PhysicalSurfaces에 이름이 없으면 default로 처리한다(명시 Course/Stairs 태그는 우선). CC-BY 원본 채택 시 Shipping에서 도달 가능한 크레딧 UI/배포 표기를 확인한다(현 콘솔 노출은 Development 검사용).

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
| 포털 | 1초 안 왕복3회·클릭 없음 | ✅ 클릭 없음. 문 평면 순간이동으로 0.33 s 간격 6회 통과(3왕복 1.64 s)와 0.5 s 간격 3왕복(왕복당 1 s). `MinCrossingIntervalSeconds=0.25` 때문에 3왕복을 1.25 s 안에는 할 수 없음. 발소리를 끈 구간의 클릭 z 최댓값 4.2(판정 8, 자체 시험의 하드컷은 z 160). 레벨이 −50 → −53.7로 부드럽게 출렁였다가 복귀 |
| 크로스페이드 | 기본2초 vs 실내1초/실외2초 | ✅ 측정: 2.0 s면 → 실내 안착 1.83 s, 1.0 s면 0.94 s(0.66 s에 dip 2.5 dB). → 실외 2.0 s는 1.84 s로 양쪽 같음. 1.0 s는 빠른 왕복에서 더 깊게 출렁임(−56.5). 차트 `pc-verify-wp13-crossfade.jpg`. **체감 판정은 소유자 청취**. Fable 설계 의견은 §7-3 |
| 재질별 발소리 | default/asphalt/tile/stairs 걷기·달리기10보 | ✅ L_Dev Floor PIE 한정 override(§7-5): 미지정·SurfaceType1 → `SW_asphalt`, 2 → `SW_tile`, 3 → `SW_stairs`. 각각 걷기 11보(71.7 cm/보)·달리기 12보(109 cm/보). `Course/Stairs` 태그 계단 → `SW_stairs`(걷기 8보 중 계단 위 7보, 달리기 5+5보). 합성 Zone 충돌 바닥 → default `SW_asphalt` 10보 |
| 로스터별 발소리 | proxy135/proxy110/Quinn 각10보·스케일 필요성 | ✅ 실행: 각 걷기 10~11보, 달리기 11~12보, 소리 보폭은 고정(걷기 72~77, 달리기 109~112 cm). 애니메이션 발 딛기와의 비율(소리 ÷ 애니)은 걷기 Manny/Quinn 0.92·proxy135 0.70·proxy110 0.59, 달리기 1.27·1.22·1.03. **`stride_scale_by_mesh`(Z 스케일 곱)는 권장하지 않음**: proxy 걷기는 1.03~1.05로 맞지만 달리기가 1.7배로 나빠짐. 대안은 §7-3 |
| 착지 | 점프5회·공중 무음·착지1회 | ✅ 제자리 점프 5회 → `SW_landing` 5회, 발소리 0. 달리며 점프 2회 → 착지 2회, 공중 구간 발소리 없음 |
| Photo mute/maintain | 양 모드·원샷 정지/억제·채널0 | ✅ mute: 진입 시 앰비언스와 재생 중 원샷이 20~40 ms 램프로 무음(클릭 없음), 종료 즉시 복귀, describe ` muted`. maintain(JSON 수정·재시작): Photo 중 레벨 불변(이 구간에는 캐릭터가 움직이지 않아 발소리 없음). 사용자 `.mute 1`은 maintain 설정에서도 무음. Photo 안에서 두 가지를 겹친 경우는 미실행 |
| 발소리 중복·루프 이음·clipping | (§3 청취 항목) | ✅ 동시 발소리 보이스 최대 2, 보폭 1회당 1인스턴스. 4 s 루프 이음이 약 9회 지나는 구간에서 클릭 없음(z 최댓값 4.5). clipping 0 샘플, 전체 피크 −32.1 dBFS |
| 소유자 밸런스 | 장치·OS 볼륨·master/상태/발소리 gain JSON 값 | ⏳ **소유자 결정 대기**(세션은 후보만 제시). 현재 값: master 0.7 / 낮 0.25·밤 0.18·실내 0.15 / 발소리 0.5·착지 0.6. 측정(엔진 출력): 낮 베드 RMS −50.3, 밤 −53.9, 실내 −55.6 dBFS, 발소리 피크 약 −35.8, 착지 −34.7 dBFS. 장치 루프백(OS 52 %)은 낮 −60.5 dBFS로 **매우 작음**. 후보: master 1.0, 낮 0.5·밤 0.36·실내 0.30, 발소리 1.0, 착지 1.0 — 상대 비율을 유지한 채 약 +9 dB(낮 ≈ −41 dBFS RMS, 발소리 피크 ≈ −27 dBFS, clipping 없음 예상). 합성 소스 자체가 −26 dBFS RMS라 JSON 상한(1.0) 안에서는 이 정도가 최대 |
| 패키징 | SW7개·audio.json 포함·재생/크레딧 | ✅(발소리 제외) BuildCookRun 성공. 첫 실행은 "Live Coding active"로 실패 → `package.ps1` PC fix 뒤 통과. stage manifest와 `.utoc`에 SW 7개(.uasset+.ubulk), `.pak`에 `Config/Golmok/audio.json`. 패키지 실행: `golmok.audio`·`credits` 출력, `-ExecCmds`로 night·interior 전환, 루프백 낮/밤/실내 −60.5/−64.2/−65.6 dBFS. **패키지 발소리 청취는 미확인**: 05:46부터 떠 있는 Windows 보안 시스템 대화상자가 포커스를 막아 키 입력 불가(§7-4) |
| 고친 API | 위 번호·변경/재검증 근거 | A1~A9 코드 수정 없음. PC fix는 `tools/ue/package.ps1` 1건(`-ubtargs=-NoHotReloadFromIDE`, Astra 레인 아님)과 이 런북의 cook 확인 명령 정정. Astra 레인 파일(`Source/Golmok/Audio/`·`audio.json`·`Content/Golmok/Audio/`)은 수정하지 않음 |
| STATUS 판정 | 통과/부분/차단·남은 항목 | **WP-13 🟢**, V-10 🟢. 결함 0이고 기능·전환·클릭·재질·착지·Photo·패키징(앰비언스·크레딧)이 통과. 비차단으로 남은 항목: ① 소유자 볼륨 청취·최종 gain(후보 위), ② 패키지 발소리 1회 청취(보안 대화상자를 소유자가 처리한 뒤), ③ 크로스페이드 1.0/2.0 체감, ④ 실제 음원 교체(결정 필요 ③) 뒤 재청취 |

### T6(13c) 후속 확인 범위

ToD가 파괴되면 다음 재탐색(최대 0.25 s)에 프리셋·실내 상태를 초기화해 auto는 outdoor_day로 돌아간다. 새 ToD에 다시 바인딩하며 명시적인 강제 상태는 유지한다. 0.25 s 폴링은 Controller와 ToD의 수명·재탐색만 담당하고, 기존 ToD의 프리셋/실내 변경은 이벤트로 즉시 반영한다.

실내 broadcast는 기존대로 EnsurePresets 성공 조건 안에 있다. 프리셋 로드 실패 시 오디오 이벤트도 발행하지 않는다(B-7, 코드 변경 없음). SoundWave는 패키지 존재를 먼저 검사하므로 임포트 전 파일 누락은 HUD의 missing SoundWave 진단으로 남는다. 실제 임포트 후 PIE를 다시 시작하고 패키징/청취는 별도로 확인한다.

C-10: Packaging 설정을 에디터에서 저장한 뒤 DefaultGame.ini의 중복 ProjectPackagingSettings 섹션과 Audio cook 항목을 git diff로 확인한다. 훅 표지 유실이나 항목 제거를 그대로 커밋하지 않는다. C-2 Shipping 크레딧 UI는 이번 T6 배정에서 제외, 실제 음원 확정 뒤 별도 배정이다. D7 stride_scale_by_mesh도 로스터별 V-10 청취 뒤 결정하며 현재 고정 보폭을 유지한다.

## 7. V-10 실행 기록 (2026-09-29, PC)

### 7-1. 방법

- 드라이버: V-09b `pie_driver.py`에 오디오 단계를 더한 것(세션 scratchpad `v10/`, 미커밋). 에디터 GUI를 `-ini:Engine:[Audio]:UnfocusedVolumeMultiplier=1.0`으로 띄우고(포커스 영향 제거), 새 창 PIE(Alt+P)와 SendInput 키(1~4·F5·W·Shift)를 쓴다.
- 녹음: PIE 월드에서 `unreal.AudioMixerLibrary.start_recording_output(world, s)` → `stop_recording_output(world, AudioRecordingExportType.WAV_FILE, name, dir)`(Python 이름은 `AudioMixerLibrary`, `ScriptName` 메타데이터). master submix 출력이라 OS 볼륨 전 신호다.
- 분석: 100 ms RMS 포락선(안착 = 최종 레벨 ±1 dB 진입 시각), 클릭 = 1차 차분을 국소 강건 σ(MAD, ±100 ms)로 나눈 z(발소리 원샷 구간 제외, 판정 z ≥ 8). 합성 베드가 32탭 이동평균 노이즈라 차분이 백색에 가깝다. 자체 시험에서 의도적 하드컷은 z 160, 2 s/1 s 선형 페이드는 안착 2.09/0.85 s로 검출됐다.
- 발소리 식별: `ListWaves`(0.1 s 샘플, 재생 위치 되감김 = 새 인스턴스)로 웨이브 이름·동시 보이스 수를 센다. 애니메이션 cadence는 foot_l/foot_r 소켓의 진행 방향 간격을 자기상관해 구한다(주기 = 2보).
- 패키지: `build\Windows\Golmok.exe`(부트스트랩이 실제 `Golmok\Binaries\Win64\Golmok.exe`를 띄움)를 `-forcelogflush -ExecCmds=…`로 실행하고, 기본 출력 장치의 WASAPI 루프백을 PowerShell+C# interop로 캡처했다(설치 없음, 읽기 전용).

![HUD audio 줄(L_ZoneTest 실내, 실행 A)](pc-verify-wp13-hud.jpg)

![녹음 포락선: A(전 상태 2.0 s) vs A2(interior 1.0 s)](pc-verify-wp13-crossfade.jpg)

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
3. **발소리 보폭**: ABP_Unarmed의 걷기 cadence는 속도와 상관없이 2.68 보/s로 고정이다. 고정 보폭(70/110 cm)은 Manny 걷기(애니 67 cm)에는 맞지만, 달리기(애니 146 cm)에서는 발소리가 27 % 많다. proxy 걷기(애니 54·45 cm)에서는 0.70·0.59배로 적다. `stride_scale_by_mesh`는 달리기를 1.7배로 망치므로 **권장하지 않는다**. 대안은 캐릭터별 (걷기, 달리기) 보폭 데이터다. 측정값은 Manny/Quinn 67/146, proxy135 54/142, proxy110 45/115 cm(각 캐릭터 걷기·달리기 속도 기준). 또는 V-08 애니메이션 채택 뒤 노티파이 구동으로 바꾼다(WP-13 원래 계획).
4. **Photo mute 진입**은 20~40 ms 안에 뚝 끊긴다(클릭은 없음). 0.2~0.3 s 짧은 페이드는 폴리시 후보다.
5. 합성 플레이스홀더 7개는 같은 공식(필터 노이즈 ± 95 Hz)이라 **세 앰비언스와 네 발소리 세트가 음색으로는 거의 구분되지 않는다**(gain 차이만 있음). 품질 판정은 실제 음원 교체(결정 필요 ③)나 WP-17 녹음 뒤에 한다.

### 7-4. 막힌 것·환경

- **Windows 보안 대화상자**: 05:46쯤부터 `PickerHost.exe`의 `Shell_SystemDialog`(제목 "Windows 보안")와 전체 화면 `Shell_SystemDim` 오버레이(최상위)가 떠 있다. 이 때문에 다른 창을 포그라운드로 만들 수 없고 SendInput 키가 게임에 들어가지 않는다. 패키지 `Golmok.exe`를 처음 실행할 때 뜬 방화벽 허용 프롬프트로 보인다. 보안 설정이라 세션은 누르지 않았다. 소유자가 처리한 뒤 패키지에서 W 걷기 발소리를 1회 확인한다(`scratchpad v10/run_packaged.py` 방식, 또는 직접 실행해 걸어 보기).
- `-log`로 패키지를 띄우면 로그 콘솔 창이 포그라운드를 가져간다. `-forcelogflush`만 쓴다. 부트스트랩 `Golmok.exe`를 종료해도 실제 게임 프로세스는 남는다.

### 7-5. 재현 메모

- PhysicalSurfaces 이름이 프로젝트에 없어서 Python에는 `unreal.PhysicalSurface.SURFACE_TYPE_DEFAULT`만 노출된다. 이 상태에서는 `set_editor_property("surface_type", …)`로 SurfaceType1~를 줄 수 없다. PIE 콘솔 `set <obj> SurfaceType SurfaceType2`도 GUI 에디터에서는 `ProcessUserConsoleInput`이 가로채 적용되지 않는다(헤드리스 commandlet에서만 적용됨). 재질 시험은 `DefaultEngine.ini`에 `[/Script/Engine.PhysicsSettings] +PhysicalSurfaces=(Type=SurfaceType1,Name="V10Asphalt")` 등 3줄을 **임시로** 넣고 한 뒤 `git checkout`한다. Zone 에셋 단계에서 이름을 정식으로 정의하면(B 항목 C-11) 이 문제는 없어진다.
- 임포트로 생긴 `Content/Golmok/Audio/{ambience,footsteps}/SW_*.uasset`은 gitignore 대상이 아니라 untracked로 보인다. 커밋할 때 제외해야 한다(후속: ignore 규칙 검토).
