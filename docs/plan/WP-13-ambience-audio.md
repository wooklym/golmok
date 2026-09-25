# WP-13 — 환경음 기본: 앰비언스·발소리·실내 전환 (D-016 (a))

상태: ⚪ 대기 (등록 2026-09-25, WP-12 뒤) · 담당: 클라우드 Claude 세션(**Fable 5.1 ultracode**, 검증 Opus 5.5 — 모델 정책 §7.4; 사운드 출처 조사는 같은 세션의 리서치 에이전트 또는 선행 Opus 에이전트) · 의존: WP-05(포털·시간대), WP-04(Zone), V-08 결과는 **불필요**(발소리는 이동 거리 기반으로 시작, 애니메이션 노티파이 연동은 채택안 뒤) · 검증: G2(`runbooks/pc-verify-wp13.md`, V-10)

## 목표
소리 없는 골목을 "장소"로 만든다(D-016 (a), 사용자 승인 2026-09-25): 전역 앰비언스(도시 원경, 낮/밤), 발소리(바닥 재질 2~3종), 실내 진입 시 앰비언스 전환, 시간대별 전환. 현재 코드에는 오디오가 전혀 없다. 근거: [`design/game-features-proposal.md`](../design/game-features-proposal.md) D-016.

## 배경(코드에서 확인할 것)
- 실내/실외 상태는 WP-05 `Portals/GolmokPortal`·`GolmokLevelStreaming`(실내 오버레이·노출 전환)에 있다. 시간대 프리셋 전환은 `Lighting/GolmokTimeOfDay`(프리셋 JSON 단일 소스, 이름으로 낮/밤 구분 — 프리셋 JSON에 `ambience` 키를 **추가하지 않고** 오디오 JSON 쪽에서 프리셋 이름 → 상태를 매핑).
- 캐릭터는 `Player/GolmokCharacter`(CMC, 걷기 180·달리기 500 cm/s). 발소리는 첫 구현에서 **이동 거리 기반**(걷기 보폭·달리기 보폭, 공중이면 없음, 착지 소리)으로 하고, V-08 채택안이 정해지면 애니메이션 노티파이로 옮길 수 있게 트리거 함수를 분리한다. 바닥 재질은 발밑 트레이스의 `UPhysicalMaterial`(`SurfaceType`) → 재질 세트 매핑; 재구성 메시·베이스맵 타일에 물리 머티리얼이 없으면 기본(아스팔트), 계단은 `Course/Stairs`(L_Dev)와 zone 충돌 메시의 경사·단차로 구분(설계 패널이 결정, 없으면 기본).
- 클라우드에서는 **에디터 에셋(MetaSound, SoundCue)을 만들 수 없다.** 첫 구현은 C++ + `USoundWave`(+ `USoundAttenuation`/`USoundConcurrency`를 C++에서 생성)로 하고, 크로스페이드·랜덤 피치/볼륨은 C++로 한다. MetaSounds 전환은 PC 작업 후보로 런북에 적는다(D-003 에셋 최소).
- 사운드 파일은 `.wav`(LFS, `.gitattributes`에 이미 있음). 원본 녹음·대용량 라이브러리는 저장소에 넣지 않는다.

## 산출물 (`unreal/Golmok/Source/Golmok/Audio/`, `Content/Golmok/Audio/`, `Content/Python/golmok/`, `tools/`, `docs/`)
1. **사운드 출처 조사(먼저, 문서)**: 무료 라이브러리 후보를 **라이선스 원문을 열어** 인용(CC0 우선, CC-BY는 표기 파일 필수, NC·ND·"UE 전용 아님" 등 조건은 제외 — D-002). 컨테이너에서 열리지 않으면 [확인 필요]. 후보별: 항목 URL, 라이선스, 길이, 용도(도시 원경 낮/밤, 실내 룸톤, 발소리 아스팔트/타일/계단, 착지). 유료(예: 상용 SFX 팩)는 **제안만**(가격·라이선스 요약) — 구매는 사용자 승인. 결과는 `docs/research/10-ambience-sources.md`.
2. **에셋 반입**: 다운로드가 컨테이너에서 가능하고 라이선스가 확인된 항목만 `unreal/Golmok/Content/Golmok/Audio/src/<category>/<name>.wav`(LFS, 항목당 ≤ 5 MB, 총 ≤ 40 MB)와 `ATTRIBUTION.md`(항목·저자·URL·라이선스 원문 링크)로 넣고 DECISIONS D-002에 기록. 불가능하면 **플레이스홀더 WAV**를 `tools/scripts/make_placeholder_audio.py`(numpy: 필터 노이즈·톤, 결정적 시드)로 생성해 같은 경로에 두고 런북에서 PC 세션·사용자가 실제 파일로 교체(파일 이름 규약 유지).
3. **에디터 반입 스크립트** `golmok/audio_import.py`: `Audio/src/*.wav` → `/Game/Golmok/Audio/<category>/SW_<name>`(`unreal.AssetImportTask`, 루프 플래그·볼륨 정규화 옵션), 순수 계획 함수는 `_pure.py`에 두고 가짜 unreal로 pytest(WP-06 방식).
4. **`Config/Golmok/audio.json`**(단일 소스, pytest 스키마 검사, UFS 스테이징): 상태별 앰비언스(`outdoor_day`, `outdoor_night`, `interior`) → 에셋 경로·볼륨·루프, 프리셋 이름 → 낮/밤 매핑, 크로스페이드 시간(기본 2 s), 발소리 재질 세트(`asphalt`, `tile`, `stairs`, `default`)·보폭(걷기 70 cm / 달리기 110 cm, 런북에서 조정)·피치/볼륨 랜덤 폭, 착지 소리, 마스터 볼륨.
5. **`UGolmokAmbienceSubsystem`**(World): 오디오 컴포넌트 2개(A/B)로 상태 전환 시 크로스페이드, 실내/실외는 포털 상태(WP-05 API 또는 델리게이트 추가) + 시간대 프리셋 변경 델리게이트 구독, 일시정지(WP-12 포토 모드) 시 유지/뮤트 옵션. **`UGolmokFootstepComponent`**(캐릭터에 C++로 부착): 거리 누적·재질 트레이스·재생, 착지. 콘솔 `golmok.audio`(상태·볼륨·재생 중 에셋), `golmok.audio.mute [0|1]`, `golmok.audio.state <name>`(강제 전환, 디버그). HUD `audio:` 줄(WP-05 HUD).
6. **테스트**: 순수 헤더 `GolmokAudioMath.h`(보폭 누적·크로스페이드 커브·재질 매핑 결정) g++ 교차검증 pytest; UE 자동화 `Golmok.Audio.StateMachine`(포털·프리셋 이벤트 → 상태, `-nullrhi`, 실제 재생 없이), `Golmok.Audio.Footstep`(거리·공중·착지); `test_ue_config_audio.py`, `test_ue_python_audio_import.py`, `test_make_placeholder_audio.py`(결정적 출력·헤더 검사).
7. **문서**: `docs/research/05-legal-policy.md` 공개 전 자문 항목에 "현장 녹음에 타인 대화 포함(통신비밀보호법·개인정보)" 추가(문서만). `docs/capture/01-alley-capture-guide.md`에는 손대지 않는다(현장 녹음 절차는 D-016 (b), WP-17).
8. **런북** `docs/runbooks/pc-verify-wp13.md`(V-10): `audio_import` 실행 → 빌드 → `test.ps1 -Filter Golmok.Audio` → PIE에서 낮/밤 전환·실내 진입 크로스페이드·발소리 재질(아스팔트·타일·계단)·착지 → 볼륨 밸런스 기록 → 플레이스홀더면 실제 파일 교체 절차 → 불확실 API 표.

## 완료 기준
클라우드: `research/10` 출처 표(라이선스 인용), 코드·JSON·스크립트·테스트·런북, pytest·ruff·check_repo·CI 통과, STATUS `🟡`. PC: V-10 통과 → `🟢`. 유료 라이브러리 구매·현장 녹음은 이 WP 밖(사용자 결정·WP-17).

## 주의
- D-002: 라이선스 원문 없이 파일을 넣지 않는다. 다운로드 URL·라이선스·저자를 `ATTRIBUTION.md`와 D-002에 남긴다. 저장소 총 오디오 용량 40 MB 이하.
- 품질 우선이지만 클라우드는 들을 수 없다 — 볼륨·밸런스는 런북의 PC 세션 항목. 첫 구현의 목표는 **파이프라인과 전환 로직이 맞는 것**.
- WP-05·09 규약(`Load()` 스택 규칙, 프리셋 JSON 단일 소스), 5.8 주의(WP-12 참조), Windows CI 주의 동일. 세션 운영: 적대적 검증 최대 1라운드, Workflow 2시간 상한.
