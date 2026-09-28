# V-10 — WP-13 환경음 검증

상태: 🟡 13b 코드 완료·PC V-10 패키징/청취 대기. 런타임·임포트 및 헤드리스 Audio 자동화 검증 완료. 최신 실행 결과는 WP-13 문서의 런타임 절을 우선한다.

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
| 배포 크레딧·SoundWave cook | Audio cook 등록 및 WP-05 목록 계약을 01:27Z 허용 범위로 반영. 크레딧 원본 메타데이터는 기존 UFS의 audio.json에 포함되며 `golmok.audio credits`가 읽어 출력한다. 독립 txt는 배포 문서용 생성물이고 별도 UFS에 넣지 않음. 패키징/게임 내 노출 미검증 |


## 5. 크로스페이드와 품질 확인

A/B 볼륨은 현재 값에서 선형 보간한다. 제3의 상태가 빠르게 들어오면 두 슬롯만으로 세 파일을 유지할 수 없으므로 더 조용한 슬롯을 최대50ms 동안0으로 낮춘 뒤 교체하고 JSON의 목적 상태별 전환을 시작한다(기본2초). 요청 상태 변경은 이벤트와 같은 프레임이고 새 파일 시작은 이 경우 최대50ms 뒤다. 이 정책은 Fable 설계 가설 승인을 받았고 합격은 V-10 청취로 결정한다. 포털을 1초 안에 실내↔실외 왕복3회 통과하며 클릭/끊김이 없는지 확인한다. Photo 유지 정책은 UI sound로 월드 pause와 분리하고, mute는 컴포넌트 볼륨을0으로 만든다. 헤드리스 자동화는 청취 증거가 아니며 출력 장치·음색·최종 밸런스를 판정하지 않는다.


`crossfade_seconds_by_state`는 진입할 상태별 초 단위 전환 시간이다. 누락한 상태는 `crossfade_seconds`를 사용하며 모두 0~30초다. 현재 세 상태 모두 2초를 유지한다. V-10에서 interior=1초, outdoor_day/outdoor_night=2초 가설을 JSON만 바꿔 비교하고 PIE를 재시작한다. 보폭에 메시 Z 스케일을 곱하는 `stride_scale_by_mesh` 제안은 이번 구현에 포함하지 않으며 로스터별 청취 뒤 후속으로 판단한다.

패키징 확인(미실행): 임포트 후 `.\tools\ue\package.ps1` 실행 → `build/Windows`의 패키징 로그/컨테이너 목록에서 Audio의 SoundWave 7개와 `Config/Golmok/audio.json`을 확인 → 패키지 실행에서 세 상태 전환과 `golmok.audio credits` 출처 출력 확인. pak은 엔진 `UnrealPak.exe <pak 경로> -List`로 조사한다. IoStore를 사용한 출력이면 해당 컨테이너 목록과 cook/stage manifest도 함께 확인한다. 파일 존재와 실제 재생/크레딧 출력을 각각 기록하고 미실행을 성공으로 표시하지 않는다.


### 런타임 불확실 API

컴파일/헤드리스 성공과 출력 장치·패키지 검증을 구분한다.

| 번호 | API | 위험 | 대안 | 확인 단계 | 결과 |
|---|---|---|---|---|---|
| A1 | USoundAttenuation(반경100cm·falloff600cm) | 실제 거리 감쇠 불일치 | 청취 뒤 설정 튜닝 | 근거리/600cm 비교 | 미확인 |
| A2 | USoundConcurrency(8, StopOldest) | 원샷 중첩/잘림 | voice·정책 조정 | 연속 이동/착지 | 미확인 |
| A3 | SpawnSound2D + bIsUISound | GamePause maintain 중 재생 중단 | pause 대응 검토 | Photo 양 모드 | 미확인 |
| A4 | SpawnSoundAtLocation | 무음/null/공간화 불일치 | 출력·에셋·감쇠 점검 | 실제 발소리 | 미확인 |
| A5 | LineTraceSingleByChannel(ECC_Visibility), bReturnPhysicalMaterial, GetSurfaceType | 재구성 메시·Zone 충돌/재질 누락 | default, Zone 재질/충돌 보완 | 각 재질/재구성 바닥 | 미확인 |
| A6 | LoadObject<USoundWave> 소프트 경로 | 패키지 cook 누락 | cook 등록·임포트 확인 | Development 패키지 | 미확인 |
| A7 | OnPossessedPawnChanged.AddDynamic | 교체 뒤 컴포넌트 누락/중복 | 바인딩 수명 점검 | 로스터·경로·Photo 복귀 | 헤드리스 부착 확인; GUI 미확인 |
| A8 | IsTickableWhenPaused | pause 중 정책/페이드 정지 | 시간 처리 검토 | mute/maintain | 미확인 |
| A9 | HasCalledBeginPlay | 초기/재시작 Tick 순서 | 월드 시작 후 초기화 | PIE 재시작3회 | 헤드리스 통과; GUI 미확인 |

패키징 후 cook 파일 수 확인(7개 기대):

```powershell
.\tools\ue\package.ps1
$audioCookFiles = Get-ChildItem .\unreal\Golmok\Saved\Cooked\Windows\Golmok\Content\Golmok\Audio -Recurse -Filter SW_*.uasset
$audioCookFiles | Select-Object FullName
$audioCookFiles.Count
Get-ChildItem .\build\Windows -Recurse -Include *.pak,*.utoc
```

cook 파일만으로 합격시키지 않는다. 컨테이너/stage manifest의 SoundWave7개·audio.json과 패키지 실행의 재생·크레딧도 확인한다. 에디터 Packaging 저장은 중복 ini 섹션을 재작성할 수 있으므로 Audio cook 훅 보존을 diff로 확인한다. PhysicalSurfaces1/2/3 이름은 Zone 에셋 단계에서 정의한다. 13c는 audio.json에 번호 매핑이 있어도 프로젝트 PhysicalSurfaces에 이름이 없으면 default로 처리한다(명시 Course/Stairs 태그는 우선). CC-BY 원본 채택 시 Shipping에서 도달 가능한 크레딧 UI/배포 표기를 확인한다(현 콘솔 노출은 Development 검사용).

## 6. 결과 기록

| 항목 | 실행·기대 기준 | 결과/근거 |
|---|---|---|
| 세션/head | 날짜·담당·커밋·장치 | 미기록 |
| build | UE5.8.3 성공 | 미기록 |
| audio_import | 7개+재임포트7개·loop/gain | 미기록 |
| Audio 필터 | Golmok.Audio 2/2 | 미기록 |
| 전체 자동화 | 28 Success, RenderEvidence 미실행 별도 | 미기록 |
| 콘솔/HUD | 상태·mute·auto·출처/확인일 | 미기록 |
| 낮/밤·실내 | 각3회·실내 우선·복수 소스 | 미기록 |
| 포털 | 1초 안 왕복3회·클릭 없음 | 미기록 |
| 크로스페이드 | 기본2초 vs 실내1초/실외2초 | 미기록 |
| 재질별 발소리 | default/asphalt/tile/stairs 걷기·달리기10보 | 미기록 |
| 로스터별 발소리 | proxy135/proxy110/Quinn 각10보·스케일 필요성 | 미기록 |
| 착지 | 점프5회·공중 무음·착지1회 | 미기록 |
| Photo mute/maintain | 양 모드·원샷 정지/억제·채널0 | 미기록 |
| 소유자 밸런스 | 장치·OS 볼륨·master/상태/발소리 gain JSON 값 | 미기록 |
| 패키징 | SW7개·audio.json 포함·재생/크레딧 | 미기록 |
| 고친 API | 위 번호·변경/재검증 근거 | 미기록 |
| STATUS 판정 | 통과/부분/차단·남은 항목 | 미기록 |


### T6(13c) 후속 확인 범위

ToD가 파괴되면 다음 재탐색(최대 0.25 s)에 프리셋·실내 상태를 초기화해 auto는 outdoor_day로 돌아간다. 새 ToD에 다시 바인딩하며 명시적인 강제 상태는 유지한다. 0.25 s 폴링은 Controller와 ToD의 수명·재탐색만 담당하고, 기존 ToD의 프리셋/실내 변경은 이벤트로 즉시 반영한다.

실내 broadcast는 기존대로 EnsurePresets 성공 조건 안에 있다. 프리셋 로드 실패 시 오디오 이벤트도 발행하지 않는다(B-7, 코드 변경 없음). SoundWave는 패키지 존재를 먼저 검사하므로 임포트 전 파일 누락은 HUD의 missing SoundWave 진단으로 남는다. 실제 임포트 후 PIE를 다시 시작하고 패키징/청취는 별도로 확인한다.

C-10: Packaging 설정을 에디터에서 저장한 뒤 DefaultGame.ini의 중복 ProjectPackagingSettings 섹션과 Audio cook 항목을 git diff로 확인한다. 훅 표지 유실이나 항목 제거를 그대로 커밋하지 않는다. C-2 Shipping 크레딧 UI는 이번 T6 배정에서 제외, 실제 음원 확정 뒤 별도 배정이다. D7 stride_scale_by_mesh도 로스터별 V-10 청취 뒤 결정하며 현재 고정 보폭을 유지한다.
