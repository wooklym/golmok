# V-10 — WP-13 환경음 검증

상태: 🔵 13b 런타임·임포트 구현 및 헤드리스 Audio 자동화 통과. 공유 테스트/패키징 계약 갱신과 V-10 청취 대기. 최신 실행 결과는 WP-13 문서의 런타임 절을 우선한다.

## 1. 데이터와 임포트

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

## 2. 실제 소스로 교체

1. 출처 조사 문서의 라이선스 원문과 실제 파일을 대조한다. Freesound 원본은 로그인 요구를 확인했으며 계정 생성/약정은 수행하지 않았다. 미리듣기 손실 파일을 원본처럼 반입하지 않는다.
2. 허용된 파일을 PCM16/48kHz로 준비해 Audio/src 아래 둔다. 앰비언스 stereo, 발소리 mono를 우선 검토하며 각 5MB/총 40MB 이하로 유지한다.
3. JSON의 해당 asset 항목에서 `source`, `asset`, `title`, `author`, `license`, `license_url`, `source_url`, `changes`, `placeholder=false`, `loop`, `gain`을 갱신한다. 상태/세트는 asset ID를 참조하므로 C++ 수정 없이 데이터로 교체한다. `seed`는 실제 파일에 사용하지 않는다.
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

## 4. API·패키징 확인

| 항목 | 상태 |
|---|---|
| AssetImportTask / imported_object_paths | fake unreal 계약 및 UE5.8.3 실제7개 임포트·재임포트 확인 |
| SoundWave looping·volume / save_loaded_asset | 실제7개 값 검증, 볼륨은 파형 정규화가 아님 |
| Lighting 프리셋/실내 변경 이벤트 | 00:13Z Fable 승인 최소 훅 구현, 실제 이벤트→상태 자동화 통과 |
| HUD audio: 줄 | 승인된 ExtraHudLineProviders 훅 구현; 바인딩/해제는 Audio 소유. 현재 공급자1개이며 추후 공급자를 추가할 때 배열 수명 계약 재검토 |
| audio.json UFS | 기존 DefaultGame.ini의 ../Config/Golmok 스테이징 사용 |
| 배포 크레딧·SoundWave cook | Audio cook 등록은 WP-05 고정 목록 테스트의 타 레인 계약 확장 후 추가. 크레딧 원본 메타데이터는 기존 UFS의 audio.json에 포함되며 게임 내 표시가 이를 읽도록 후속 구현. 독립 txt는 배포 문서용 생성물이고 별도 UFS에 넣지 않음. 패키징/게임 내 노출 미검증 |


## 5. 크로스페이드와 품질 확인

A/B 볼륨은 현재 값에서 선형 보간한다. 제3의 상태가 빠르게 들어오면 두 슬롯만으로 세 파일을 유지할 수 없으므로 더 조용한 슬롯을 최대50ms 동안0으로 낮춘 뒤 교체하고 설정된2초 전환을 시작한다. 요청 상태 변경은 이벤트와 같은 프레임이고 새 파일 시작은 이 경우 최대50ms 뒤다. 이 짧은 지연·음량 변화는 Fable 설계/청취 검토 대상이다. Photo 유지 정책은 UI sound로 월드 pause와 분리하고, mute는 컴포넌트 볼륨을0으로 만든다. 헤드리스 자동화는 청취 증거가 아니며 출력 장치·음색·최종 밸런스를 판정하지 않는다.
