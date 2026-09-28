# ChatGPT Astra 과제 목록 (오케스트레이터 배정, 2026-09-27)

> **소통 채널**: 이 파일의 큐와 순서 변경, 리뷰 요약, 병합 알림은 GitHub 이슈 [#30](https://github.com/wooklym/golmok/issues/30)의 `[오케스트레이터 → Astra]` 코멘트로도 알린다. Astra는 세션 시작 때 이슈 #30을 읽고, push·완료·질문·종료를 `[Astra → 오케스트레이터]` 코멘트로 남긴다(AGENTS.md §10). 이슈 코멘트와 이 파일이 다르면 **더 최근 것**을 따른다.

이 파일은 Claude 오케스트레이터가 ChatGPT Astra에게 맡길 과제를 모아 둔 곳이다. 규칙 우선순위는 [`AGENTS.md`](../../AGENTS.md) 그대로(**과제 프롬프트 > AGENTS.md > CLAUDE.md**). 소유자가 Astra에게 "`docs/plan/astra-tasks.md`의 T3를 수행"처럼 번호로 전달한다. 과제가 끝나면 Astra는 AGENTS.md §9 형식으로 소유자에게 보고하고, PR은 Opus ultracode 코드 리뷰(+설계 변경 시 Fable) → (A) 해소·CI 초록 → 오케스트레이터 병합 순서를 따른다(DEVELOPMENT-PLAN §7.6; 소유자 승인은 되돌릴 수 없는 일이 얽힌 PR에만, D-019 2026-09-27).

배경(2026-09-27): Fable 주간 한도가 소진돼 소유자가 "Opus로 할 수 있는 것부터"를 지시했고, Astra가 WP-18(캐릭터)을 맡아 PR #22/#23을 병합, #24를 올렸다. 오케스트레이터는 Astra에게 **오디오 레인(WP-13·WP-17)**을 새로 배정하고, PC에서만 가능한 검증(V-04 실행, V-11 GUI, WP-12 포토 통합 재실행)을 Astra 과제로 옮긴다. 엔진 안 품질의 최종 판정·병합·공유 문서 갱신은 그대로 Claude(Fable) 몫이다.

## 레인 변경 (DEVELOPMENT-PLAN §7.6 표·AGENTS.md §4에 반영)
- **오디오(WP-13·WP-17) → Astra**: `unreal/Golmok/Source/Golmok/Audio/`, `Source/Golmok/Tests/GolmokAudio*.cpp`, `unreal/Golmok/Config/Golmok/audio.json`, `unreal/Golmok/Content/Golmok/Audio/`(WAV·ATTRIBUTION.md), `unreal/Golmok/Content/Python/golmok/audio_import.py`, `tools/scripts/make_placeholder_audio.py`, `tools/tests/test_ue_audio*.py`, `tools/tests/test_ue_config_audio.py`, `tools/tests/test_ue_python_audio_import.py`, `tools/tests/test_make_placeholder_audio.py`, `tools/tests/fixtures/ue/audiomath*`, `docs/research/10-*`, `docs/plan/WP-13*`, `docs/plan/WP-17*`, `docs/runbooks/pc-verify-wp13*`, `docs/capture/03-*`.
- 예약 번호 추가: WP-13, WP-17, V-10, research/10. D-002에 넣을 사운드 라이선스 문안은 "병합 시 반영"에 적는다.
- 핫스팟은 AGENTS.md §4 그대로(훅). 발소리 컴포넌트는 `Player/GolmokCharacter`를 고치지 말고 `UGolmokAmbienceSubsystem`이 `APlayerController::OnPossessedPawnChanged`(또는 `FWorldDelegates::OnWorldBeginPlay`)에서 붙이는 방식을 먼저 시도한다. 새 콘솔 명령은 `tools/tests/test_ue_wp09_fixture.py`의 `CONSOLE_COMMANDS` 끝에 `# [WP-13 hook]` 줄로, 새 소스 폴더 `Audio/`는 `test_ue_zone_fixture.py`의 `CONVENTION_FOLDERS`에 같은 방식으로 더한다.

## 과제

| # | 과제 | 언제 | 브랜치 | 산출물·완료 기준 |
|---|---|---|---|---|
| **T1** | PR #24 리뷰 비블로킹 반영(후속 소형 PR) | **완료·병합**([#32](https://github.com/wooklym/golmok/pull/32), 2026-09-28) | `astra/wp-18-review-fixes`(main 기준 새 브랜치; `astra/wp-18-followup`은 병합돼 닫힘) | PR #24 리뷰 코멘트 (B) 항목: B1 `GolmokCharacterRosterPathTest.cpp` z=1000 위치 보존 단언(바닥 배치 또는 XY만), B2 `WP-18-followup.md` "컴파일 완료" → "해당 파일 오류 없음, 실행 전", B4 `RenderEvidence`·`PhotoIntegration` 단독 `-Filter` 실행 시 `Succeeded: 0` 예외(`RenderEvidence`의 `ProductFilter` 제거 검토), B5 Movement 테스트의 L_Dev 좌표가 `setup_dev_level.py`(Claude 레인)에 의존함을 문서에, B6 런북 §8 제목·§6 불확실 API 표(`RequestScreenshot(..., FIntRect(), true)`, `IsCollisionFixApplied`, `FApp::CanEverRender`), B7 `GolmokCharacterSubsystem.cpp` 폰 변경 시 자동 재적용 실패 후 `CurrentId` 잔류 보고·0.25 s 폴링 검토. B3·B8은 병합 세션이 처리했다. 게이트(§6) 결과를 PR 설명에 |
| **T2** | V-11 GUI 잔여 + WP-12 포토 통합 재실행 | **완료·병합**([#39](https://github.com/wooklym/golmok/pull/39), 2026-09-28) — 엔진 렌더 근거·PIE 재시작·콘솔 선택; 키보드/영상/사람 눈·캡슐 복구는 PC 카드 | ~~`astra/wp-18-v11-gui`~~ | `docs/runbooks/pc-verify-wp18a.md` §7·§9의 미실행 항목(지속 보행·계단·포털 GUI 영상, PIE 재시작, 초기 메시 실패 후 GUI 복구)과 `Golmok.Character.PhotoIntegration` 6조합 실제 실행. 결과는 `docs/plan/WP-18-followup.md`에 표로. GUI 잠금 규칙(AGENTS.md §6) 준수. WP-12 코드에 문제가 있으면 고치지 말고 재현 절차·로그를 PR 설명에 적는다 |
| **T3** | **WP-13 환경음 기본**(D-016 (a)) | **완료·병합**(13a [#28](https://github.com/wooklym/golmok/pull/28) 2026-09-27, 13b [#34](https://github.com/wooklym/golmok/pull/34) 2026-09-28) → V-10 PC 검증 대기 | ~~`astra/wp-13a-sources`~~ → ~~`astra/wp-13b-audio`~~ | 스펙 [`WP-13-ambience-audio.md`](WP-13-ambience-audio.md)의 산출물 1~8 전부. **13a**: `docs/research/10-ambience-sources.md` — 무료 사운드 출처 후보를 라이선스 원문을 열어 인용(CC0 우선, CC-BY는 표기 파일, NC·ND·SA·"UE 결합 금지" 제외, 확인일·URL), 용도별(도시 원경 낮/밤, 실내 룸톤, 발소리 아스팔트/타일/계단, 착지) 후보 표, 유료 라이브러리는 가격·라이선스 요약만(구매는 소유자 결정). **13b**: `Audio/`(`UGolmokAmbienceSubsystem` 크로스페이드 A/B, `UGolmokFootstepComponent` 거리 기반·재질 트레이스·착지), `Config/Golmok/audio.json`(단일 소스·스키마 pytest·UFS 스테이징), `golmok/audio_import.py`(순수 계획은 `_pure` 스타일 별도 모듈에 두고 가짜 unreal로 pytest — `Content/Python/golmok/_pure.py`는 Fable 레인이므로 고치지 말고 `audio_pure.py` 같은 네 파일에), WAV는 라이선스 확인된 것만 `Content/Golmok/Audio/src/<category>/*.wav`(LFS, 항목 ≤ 5 MB, 총 ≤ 40 MB) + `ATTRIBUTION.md`; 받을 수 없으면 `tools/scripts/make_placeholder_audio.py`(numpy, 결정적 시드)로 플레이스홀더. 순수 헤더 `GolmokAudioMath.h` g++ 교차검증, UE 자동화 `Golmok.Audio.StateMachine`·`Golmok.Audio.Footstep`(`-nullrhi`), 런북 `pc-verify-wp13.md`(V-10). PC에서 UE 게이트까지 돌리고 결과를 적는다(볼륨 밸런스는 소유자 청취 항목으로 남김). MetaSound 에셋은 만들지 않는다(C++ + `USoundWave`) |
| **T4** | **WP-17 현장 녹음 절차·Zone별 소리**(D-016 (b), 문서) | **완료·병합**([#37](https://github.com/wooklym/golmok/pull/37), 2026-09-28) — 절차 문서만, 현장 녹음·sounds[] 구현 별도 | ~~`astra/wp-17-field-recording`~~ | `docs/capture/03-field-recording.md`(새 파일): 장비(아이폰 내장 vs 외장 마이크·바람막이), 1곳당 녹음 시간·시간대, 대화가 담긴 구간을 쓰지 않는 운영 규칙(통신비밀보호법 원문은 [확인 필요]로), 파일 명명·정규화·루프 포인트 절차, Zone manifest에 소리 위치 점(`sounds[]`)을 넣는 **스키마 변경 제안**(스펙 파일 `docs/spec/zone-manifest.md`는 Fable 레인이므로 고치지 말고 WP-17 문서 "병합 시 반영"에 제안 문안). `docs/plan/WP-17-field-recording.md`에 목표·산출물·결과 |
| **T5** | V-04 실행·보고(WP-06 에디터 Python 검증) | 지금(PC, UE 필요) | `astra/v04-verify-wp06` | `docs/runbooks/pc-verify-wp06.md`를 그대로 실행하고 §결과 표·불확실 API 표·스크린샷(JPG ≤ 300 KB)만 기록. **코드 수정 금지**(`Content/Python/golmok/`은 Fable 레인): 고쳐야 할 것은 PR 설명에 재현 절차·로그로 요청. 생성 레벨(`L_ZoneTest06*`)·합성 zone 에셋은 커밋하지 않는다. STATUS V-04 행 문안은 "병합 시 반영"에 |

우선순위(2026-09-28 T2 병합 뒤 갱신): ~~T3 13a·13b~~·~~T1~~·~~T4~~·~~T2~~ 완료(PR #28·#32·#34·#37·#39 병합) → T5(PC GUI, 진행 중, GUI 잠금 규칙). 13b 리뷰 (B) 후속은 V-10 결과와 함께. PC(UE)는 V-09 세션·T2·T5가 나눠 쓰므로 GUI 잠금 파일 규칙을 지킨다. 리뷰 모델(2026-09-27 정책): 코드 리뷰는 Opus ultracode, 설계·품질 가설 리뷰는 Fable.

## Astra가 하지 않는 것(이번 배정 기준)
- `Source/Golmok/Photo/`·`Lighting/`·`Zones/`·`Portals/`·`Debug/`·`Geo/`와 `Content/Python/golmok/`의 기존 파일 수정(WP-12 컴파일 오류는 Fable이 고친다).
- 시간대 폴리시(WP-14)·날씨(WP-16)·Zone 지도·세이브(WP-15): 착수 조건(D-010, Zone 2곳)이 아직이다.
- 공유 문서 직접 수정, 병합, 구매·문의·발송(AGENTS.md §3).

## 오케스트레이터가 할 것
- ~~PR #24 리뷰 코멘트(Opus 읽기 전용 검증)~~(2026-09-27 병합) → ~~T1 PR #32 리뷰 완료((A) 4건) → Astra 수정 확인 → `WP-18: 병합 시 반영 (Fable)` 커밋 → merge commit~~(2026-09-28 병합, D-019).
- WP-12(PR #19) 마무리·병합, V-09는 PC Claude 세션.
- T3/T4/T5 PR의 리뷰·병합, STATUS "병행 트랙" 갱신.
