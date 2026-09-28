# V-10 — WP-13 환경음 검증

상태: 🔵 13b 데이터/임포트 기반 구현 중. 런타임 전환·발소리·청취 검증은 아직 완료하지 않았다.

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

`Golmok.Audio.StateMachine`·`Golmok.Audio.Footstep` 및 콘솔/서브시스템은 후속 구현 대상이다. 구현 뒤 빌드와 전체 회귀, Audio 필터를 실행한다. Photo 유지/뮤트 양쪽, 빠른 낮→밤→실내 재전환, 복수 포털 소스, 폰 교체/경로 재생, 걷기/달리기/공중/착지/텔레포트, 미지정 물리 재질 fallback을 확인한다.

V-10 GUI는 다른 UE 세션 종료와 GUI 잠금 확인 뒤 수행한다. 낮/밤·실내 전환 각3회, 재질별 걷기/달리기 각각10보, 점프/착지5회를 청취하고 clipping·루프 이음·발소리 중복·pause 뒤 복귀를 기록한다. 실제 청취와 자동화 로직 성공은 구분한다. 최종 야외 음원은 WP-17 현장 녹음 교체 대상이다.

## 4. API·패키징 확인

| 항목 | 상태 |
|---|---|
| AssetImportTask / imported_object_paths | fake unreal 계약 테스트; 실제 에디터 검증 결과는 WP-13 결과 절 |
| SoundWave looping·volume / save_loaded_asset | 동일, 볼륨은 파형 정규화가 아님 |
| Lighting 프리셋/실내 변경 이벤트 | 현행 공개 상태는 있으나 델리게이트 없음. 이슈 #30에 타 레인 API 요청 |
| HUD audio: 줄 | Debug 레인 연동 권한/훅 요청, 미구현 |
| audio.json UFS | 기존 DefaultGame.ini의 ../Config/Golmok 스테이징 사용 |
| 배포 크레딧·SoundWave cook | Audio cook 등록은 WP-05 고정 목록 테스트의 타 레인 계약 확장 후 추가. 크레딧 원본 메타데이터는 기존 UFS의 audio.json에 포함되며 게임 내 표시가 이를 읽도록 후속 구현. 독립 txt는 배포 문서용 생성물이고 별도 UFS에 넣지 않음. 패키징/게임 내 노출 미검증 |
