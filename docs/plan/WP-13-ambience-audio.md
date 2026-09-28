# WP-13 — 환경음 기본: 앰비언스·발소리·실내 전환 (D-016 (a))

상태: 🔵 **진행 중 — 13a 병합·13b 데이터/임포트 기반 구현, 런타임 연동 대기** (2026-09-28; 등록 2026-09-25) · 담당: **ChatGPT Astra**(2026-09-27 오디오 레인 배정, `plan/astra-tasks.md` T3; 코드 리뷰 Opus ultracode, 설계·최종 품질 Fable, 병합 오케스트레이터, DEVELOPMENT-PLAN §7.6) · 의존: WP-05(포털·시간대), WP-04(Zone), V-08 결과는 **불필요**(발소리는 이동 거리 기반으로 시작, 애니메이션 노티파이 연동은 채택안 뒤) · 검증: G2(`runbooks/pc-verify-wp13.md`, V-10)

## 목표
소리 없는 골목을 "장소"로 만든다(D-016 (a), 사용자 승인 2026-09-25): 전역 앰비언스(도시 원경, 낮/밤), 발소리(바닥 재질 2~3종), 실내 진입 시 앰비언스 전환, 시간대별 전환. 현재 코드에는 오디오가 전혀 없다. 근거: [`design/game-features-proposal.md`](../design/game-features-proposal.md) D-016.

## 배경(코드에서 확인할 것)
- 실내/실외 상태는 WP-05 `Portals/GolmokPortal`·`GolmokLevelStreaming`(실내 오버레이·노출 전환)에 있다. 시간대 프리셋 전환은 `Lighting/GolmokTimeOfDay`(프리셋 JSON 단일 소스, 이름으로 낮/밤 구분 — 프리셋 JSON에 `ambience` 키를 **추가하지 않고** 오디오 JSON 쪽에서 프리셋 이름 → 상태를 매핑).
- 캐릭터는 `Player/GolmokCharacter`(CMC, 걷기 180·달리기 500 cm/s). 발소리는 첫 구현에서 **이동 거리 기반**(걷기 보폭·달리기 보폭, 공중이면 없음, 착지 소리)으로 하고, V-08 채택안이 정해지면 애니메이션 노티파이로 옮길 수 있게 트리거 함수를 분리한다. 바닥 재질은 발밑 트레이스의 `UPhysicalMaterial`(`SurfaceType`) → 재질 세트 매핑; 재구성 메시·베이스맵 타일에 물리 머티리얼이 없으면 기본(아스팔트), 계단은 `Course/Stairs`(L_Dev)와 zone 충돌 메시의 경사·단차로 구분(설계 패널이 결정, 없으면 기본).
- 클라우드에서는 **에디터 에셋(MetaSound, SoundCue)을 만들 수 없다.** 첫 구현은 C++ + `USoundWave`(+ `USoundAttenuation`/`USoundConcurrency`를 C++에서 생성)로 하고, 크로스페이드·랜덤 피치/볼륨은 C++로 한다. MetaSounds 전환은 PC 작업 후보로 런북에 적는다(D-003 에셋 최소).
- 사운드 파일은 `.wav`(LFS, `.gitattributes`에 이미 있음). 원본 녹음·대용량 라이브러리는 저장소에 넣지 않는다.

## 산출물 (`unreal/Golmok/Source/Golmok/Audio/`, `Content/Golmok/Audio/`, `Content/Python/golmok/`, `tools/`, `docs/`)
1. **사운드 출처 조사(먼저, 문서)**: 무료 라이브러리 후보를 **라이선스 원문을 열어** 인용(CC0 우선, CC-BY는 표기 파일 필수, NC·ND·SA·"UE 결합 금지"(엔진 독립 CC0는 해당 없음) 등 조건은 제외 — D-002). 컨테이너에서 열리지 않으면 [확인 필요]. 후보별: 항목 URL, 라이선스, 길이, 용도(도시 원경 낮/밤, 실내 룸톤, 발소리 아스팔트/타일/계단, 착지). 유료(예: 상용 SFX 팩)는 **제안만**(가격·라이선스 요약) — 구매는 사용자 승인. 결과는 `docs/research/10-ambience-sources.md`.
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

## 13a 결과 (2026-09-28, Astra)

- **출처 조사 완료·채택 전**: [10-ambience-sources.md](../research/10-ambience-sources.md). CC0 7개로 도시 낮/밤·실내·아스팔트/타일/계단·착지 후보를 정리했다. 개별 URL·저자·길이·포맷·표시 용량·현재 라이선스와 CC0/CC-BY 법문을 직접 확인했다. Kenney CC0 대체 출처, InspectorJ CC-BY 4.0 예비 항목, BOOM Urban Europe 가격·오디오 EULA도 비교했다.
- **권장 가설**: CC0 7개를 첫 청취 후보로 삼고 품질 검수 후 채택한다. 다운로드가 불가능하면 13b 결정적 플레이스홀더로 로직 검증을 진행한다. 최종 게임 소리 품질 합격과 구분한다. 유료 구매는 보류 권장이다.
- **실행하지 않은 것**: 음원 청취·다운로드·반입·구매·가입·약관 동의, 13b 코드/에셋/런북, UE 빌드·V-10. 산출물 1만 완료이고 WP-13 전체는 진행 중이다. 라이선스 표기 확인을 원본 권리 관계의 독립 검증으로 표현하지 않았다.
- **규칙 적용**: 최신 과제의 “UE 결합 금지”를 필터로 쓴다. 위 초기 산출물의 “UE 전용 아님”이라는 문구가 엔진 독립 CC0를 배제하는 뜻은 아니다. `audio_pure.py`를 독립 파일로 만들고 공유 `_pure.py`는 수정하지 않는다. 13b 등록 훅은 `CONVENTION_FOLDERS += ("Audio",)  # [WP-13 hook]` 새 줄과 `CONSOLE_COMMANDS` 원소별 `# [WP-13 hook]`을 별도 커밋으로 추가한다.
- **레인·겹침**: 이 PR은 research/10 새 문서와 이 WP 문서만 바꾼다. 훅·공유 문서 수정 없음. 착수 시 열린 PR #21(V-08), #27(V-09) 및 `claude/hopeful-allen-f0a0jb`와 수정 파일 겹침 없음. 닫힌 `astra/wp-18-followup`에는 push하지 않는다.

### 13a 게이트

별도 worktree `C:/Users/user/golmok-astra/wp-13a-sources`, main `045cbe3`, 새 `tools/.venv`, `PYTHONUTF8=1`로 실행했다(2026-09-28).

| 명령 (`tools/` 기준) | 결과 |
|---|---|
| `.venv/Scripts/ruff check .` | 통과 |
| `.venv/Scripts/ruff format --check .` | 98 files already formatted |
| `.venv/Scripts/pytest -q` | **689 passed, 58 skipped**, 208 warnings, 44.84 s. g++ 없는 PC의 교차검증 등 skip은 통과로 세지 않음. 경고는 rasterio/affine 행렬 연산과 합성 래스터 지리참조 관련 |
| `.venv/Scripts/python scripts/check_repo.py` | OK (uproject, ini, json, links, gitattributes, conflicts) |
| `git diff --check` | 통과 |
| GitHub Actions | PR push 뒤 확인, 결과는 PR checks가 정본 |
| UE 빌드·테스트 / V-10 | 미실행(13a 문서만 변경) |

### 리뷰

PR #28 [리뷰](https://github.com/wooklym/golmok/pull/28#issuecomment-5859108624): Opus 5.5 ultracode 문서/라이선스 검토와 Fable 출처/품질 가설 검토 완료(오케스트레이터 보고). (A)-1 상태 🔵, (A)-2 CC0 표기 의무 없음, (A)-3 BOOM 실시간 사용 금지 인용·구매 전 적용 확인을 반영했다. 비블로킹의 용량 포맷·가격 재현성·칸별 STATUS 문안도 보완했다. C01~C03 임시 품질, 최종 야외 현장 녹음 교체, 13b 소스 독립 데이터 설정·표기/크레딧 파이프라인 요구를 인계한다. 자체 문서 점검을 이 리뷰의 대체로 기록하지 않는다. 소유자 승인 뒤 push를 멈추며 병합은 오케스트레이터가 한다.

병합 기록(2026-09-27, 오케스트레이터 세션 Fable, §7.6 4단계): e684e1d에서 (A)-1~3 반영을 확인했고 소유자가 Claude 세션에서 병합을 승인했다. `WP-13: 병합 시 반영 (Fable)` 커밋으로 아래 문안을 STATUS 트랙 1A·병행 트랙 WP-13 행과 결정 필요 줄, DECISIONS D-002, research/05 자문 항목 8번, ROADMAP 1.6, 이 문서 산출물 1("UE 결합 금지" 문구)에 옮겼다.

### 리뷰 수정 검증 (2026-09-28)

main `d37720e`를 충돌 없이 병합한 뒤 ruff check·format(98파일), pytest **694 passed, 63 skipped**(44.99s), check_repo, diff --check 통과. g++ 미설치 항목은 로컬 skip이며 CI로 확인한다. 문서 수정으로 UE·청취는 실행하지 않았다. 수정 push 뒤 push 정지하고 T1을 별도 브랜치에서 진행한다.

## 병합 시 반영 (13a, 완성 문안)

### STATUS — WP-13 및 Astra 병행 트랙

> WP-13: 🔵 **진행 중 — 13a 출처 조사 완료·소스 채택/13b 구현 대기**(2026-09-28, Astra). `research/10-ambience-sources.md`: CC0 7개로 도시 원경 낮/밤·실내 룸톤·발소리 3재질·착지 후보, 개별 항목/CC0/CC-BY 원문 확인, 유료 BOOM 가격·배포 조건, 표기/바이트 예산 인계안. 미청취·미반입이며 최종 음질은 미검증. 13b C++/JSON/임포터/WAV·V-10은 미실행. 다음 순서는 T1 → T2(V-09 세션 종료·GUI 잠금 확인 후) → T5 → T4, 13b는 별도 스택 브랜치.

### DECISIONS D-002 — 조사 상태와 반입 조건

> WP-13 사운드 출처 조사(2026-09-28): Freesound CC0 1.0 7항목과 CC-BY 4.0 예비 항목의 개별 페이지 및 라이선스 법문을 확인했다(`research/10-ambience-sources.md`). **아직 소스 채택·파일 반입 없음**, 새 런타임/도구 의존성도 없음. 채택 후 실제 파일별 저자·URL·라이선스/버전·확인일·수정 내역을 `Content/Golmok/Audio/ATTRIBUTION.md`와 배포 크레딧에 남긴다. CC0는 제3자 권리 확인을 대체하지 않는다. 유료 BOOM 음원은 완성 게임 사용권과 원본/가공 파일 공유 금지가 구분되므로 공개 저장소에 넣지 않는다. 구매·계정·약관 동의는 실행하지 않았다.

### research/05 — 변호사 자문 필요 항목 8번 추가 요청 (타 레인, 직접 수정 안 함)

> 현장 녹음: 타인의 대화·방송·음악이 포함된 구간의 이용과 공개 배포(통신비밀보호법·개인정보·저작권). 운영안은 해당 구간을 사용하지 않는 것이다. 법령 원문과 개별 녹음의 권리 관계는 [확인 필요]. CC0/CC-BY 표시는 이 검토를 대신하지 않는다.

### STATUS 칸별 적용·결정 필요 (위 인용문과 함께 반영)

- 트랙 1A WP-13 행 상태: `🔵 진행 중 — 13a 출처 조사 완료·소스 채택/13b 구현 대기`.
- Astra 병행 트랙 WP-13 행 상태: `🔵 진행 중 — 13a 출처 조사 완료·소스 채택/13b 구현 대기`.
- Astra 병행 트랙 WP-13 행 담당: `**ChatGPT Astra**(T3), 코드 리뷰 Opus ultracode·설계/품질 Fable·병합 오케스트레이터`.
- 메모: 위 STATUS 인용문의 산출물·미실행 범위 문장.
- 결정 필요 줄: `WP-13 사운드: ① CC0 7개(research/10 §3) 청취 후보 채택 여부 ② 유료 BOOM Urban Europe(From $139.00) 구매는 보류 권장 — 소유자 결정`.

### ROADMAP

> WP-13 🔵 진행 중 — 13a 출처 조사 완료(`research/10-ambience-sources.md`), 소스 채택·13b 구현·V-10 청취 대기.


## 13b 진행 — 데이터/임포트 기반 (2026-09-28)

main `c7fa296`에서 `astra/wp-13b-audio`를 시작했다. 13a PR #28이 병합돼 스택이 아니며, 기존 13a worktree를 재사용한다. 이슈 #30의 CC0 7개 청취 후보 채택 결정을 확인했다. Freesound C01 원본 다운로드 요청은 200 HTML 로그인 페이지로 리다이렉트됐고 WAV를 받지 못했다. 가입·약정이나 미리듣기 대체 없이 허용된 합성 플레이스홀더 경로를 구현했다. 다른 6개의 다운로드 가능 여부를 성공/실패로 단정하지 않는다.

### 이번 산출물

- `Config/Golmok/audio.json`: 상태/프리셋/재질 세트가 asset ID를 참조하고, 각 asset에 소스·대상 경로·루프·gain·출처·저자·라이선스·수정 내역이 있다. 기본값은 품질 가설이다. 기존 lighting_presets.json의 4개 cycle 이름과 대조한다.
- `audio_pure.py`: Unreal 없는 검증·임포트 계획·표기 생성. 경로 이탈/중복·부정확한 CC 라이선스 URL·비유한 수치·누락 참조·WAV 포맷/본문·용량을 검증한다.
- `make_placeholder_audio.py`: numpy 기존 의존성으로 PCM16/48kHz mono 7개 생성. 채택된 실제 음원은 덮어쓰지 않는다. 앰비언스4초/원샷0.33초, deterministic seed, 피크 약−14dBFS. 실제 환경음 품질/루프 길이를 대체하지 않는다.
- `audio_import.py`: JSON만으로 임포트 경로·루프·볼륨을 바꾸고 재실행한다. 임포트/저장 실패를 숨기지 않는다. 원본 파형 정규화는 하지 않는다.
- `ATTRIBUTION.md` + `Credits/audio-credits.txt`: 같은 JSON에서 생성한다. CC-BY도 저자·원문 링크·수정 내역을 보존하는 테스트 포함. 현재 project-generated는 프로젝트 합성 테스트 음원이라는 출처 표시이며 새 라이선스 약정/CC0 선언이 아니다.
- 패키징: 기존 Config/Golmok UFS가 audio.json과 전체 크레딧 메타데이터를 포함한다. 별도 cook/UFS 훅3701fb4는 기존 고정 목록 테스트와 충돌해 철회했다. 최종 diff에서 DefaultGame.ini 변경 없음. Audio cook은 WP-05 테스트 계약 확장을 소유 레인에 요청한 뒤 추가한다. 독립 크레딧 txt는 배포 문서 생성물이다.
- [V-10 런북](../runbooks/pc-verify-wp13.md): 소스 교체·재임포트·남은 런타임/청취 검증·API 표.

### 검증

패키징 훅 추가 전 ruff check/format102, pytest **716 passed / 64 skipped / 208 warnings**(43.46s), check_repo 통과. 첫 CI에서는 추가 UFS 경로가 기존 고정 개수 테스트4개와 충돌했다. 추가 cook 경로도 WP-05 고정 개수 테스트에 걸려 최종적으로 이번 훅을 철회했다. 타 레인 테스트를 임의 완화하지 않고 계약 확장을 요청한다. 크레딧 데이터는 기존 audio.json UFS를 사용한다. 생성 표기의 줄 끝 공백도 제거했다. 최종 결과는 아래에 기록한다. 새 테스트는 경로/라이선스/재생 참조 오류, seed/PCM 결정성, 채택 파일 보존, 가짜 Unreal 임포트/실패·출처 교체를 검증한다. 로컬 symlink 권한 없음1건과 기존 g++ 등63건은 skip이며 CI에서 확인한다.

UE5.8.3 에디터 빌드 **성공(116.60s)**. Python commandlet(nullrhi·nosound)에서 **7개 임포트 + 같은7개 재임포트**, SoundWave 타입·looping·volume 확인 성공, **0 errors / 0 warnings**. `Saved/Automation/WP13/import-result.json`과 로컬 `tools/.venv/audio-import-log.txt`에 근거를 보관한다. 생성된 `.uasset`은 커밋하지 않으며 WAV/JSON/스크립트로 재생성한다. **청취·패키징·런타임 오디오 테스트 결과가 아니다.**

### 런타임 연동 설계 요청·남은 구현

[이슈 #30 요청](https://github.com/wooklym/golmok/issues/30#issuecomment-5861053935): 현행 AGolmokTimeOfDay는 CurrentPreset/InteriorSources 공개 상태만 있고 변경 델리게이트가 없다. 스펙의 이벤트 구독을 충족하려면 Lighting 소유자가 성공한 ApplyPreset 및 InteriorSources 변경 알림을 제공하거나 해당 파일 최소 훅을 허용해야 한다. Debug/GolmokHUD의 audio: 행도 타 레인 연동이다. 이 파일들을 임의 수정하지 않았다.

Fable 검토용 구체안: Audio WorldSubsystem이 초기 TimeOfDay 상태를 읽고 변경 이벤트를 구독한다. 실내 소스가 하나 이상이면 interior를 우선하고, 마지막 실내 소스가 빠지면 현재 프리셋의 outdoor 상태로 돌아간다. A/B 두 컴포넌트로 2초 페이드하며 빠른 재전환 때 현재 gain에서 다음 목표로 이동한다. Controller 교체 탐색과 PawnChanged 델리게이트로 Character에 거리 기반 FootstepComponent를 붙이고, 공중·경로/포토 폰에는 발소리를 내지 않는다. 표면 미지정은 default, 근거 없는 계단 경사 추정은 하지 않고 L_Dev Course/Stairs 태그 및 PhysicalMaterial만 사용한다. pause mute 기본/maintain 옵션은 Photo API로 상태를 읽어 적용한다. 이벤트 제공 전의 대안인 상태 폴링은 스펙과 다르므로 오케스트레이터에 선택을 요청했다.

아직 **미구현**: Audio C++/순수 수학 교차검증/UE StateMachine·Footstep/콘솔/실시간 전환·착지·HUD·게임 내 크레딧 노출. **미검증**: 패키징에 실제 사운드·크레딧 포함, 재생/청취/최종 음질. 이번 초안은 WP-13 완료·🟡로 표시하거나 최종 병합하지 않는다. 레인 간 설계 응답을 받아 같은 브랜치에서 이어간다.

### 병합 시 반영 (13b 진행, 아직 최종 병합 대상 아님)

> WP-13 🔵: 13a 병합, 13b JSON/결정적 플레이스홀더/임포트/출처·크레딧 기반 구현 및 UE 7개 임포트·재임포트 확인. 런타임 이벤트/HUD 연동 설계 요청 중, C++/Audio 자동화·V-10 청취·패키징 대기. 새 외부 음원 반입·라이선스 약정 없음.

패키징 추가 요청: `tools/tests/test_ue_wp05_fixture.py::test_default_game_ini_packaging_lines`가 cook 등록을 정확히1개로 고정한다. Audio 폴더 추가를 허용하는 타 레인 계약 갱신/훅 권한을 이슈 #30에서 요청한다. 계약 반영 전에는 패키징을 완료 표시하지 않는다.

훅 철회·표기 공백 수정 뒤 최종 로컬 게이트: **716 passed/64 skipped/208 warnings,37.13s**, ruff check/format102·check_repo·main 대비 diff --check 통과. Audio WAV7개 합계1,280,308바이트.
