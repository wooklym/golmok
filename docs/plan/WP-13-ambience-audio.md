# WP-13 — 환경음 기본: 앰비언스·발소리·실내 전환 (D-016 (a))

상태: 🟡 **코드 완료·PC V-10 대기** (2026-09-28; 등록 2026-09-25) · 담당: **ChatGPT Astra**(2026-09-27 오디오 레인 배정, `plan/astra-tasks.md` T3; 코드 리뷰 Opus ultracode, 설계·최종 품질 Fable, 병합 오케스트레이터, DEVELOPMENT-PLAN §7.6) · 의존: WP-05(포털·시간대), WP-04(Zone), V-08 결과는 **불필요**(발소리는 이동 거리 기반으로 시작, 애니메이션 노티파이 연동은 채택안 뒤) · 검증: G2(`runbooks/pc-verify-wp13.md`, V-10)

## 목표
소리 없는 골목을 "장소"로 만든다(D-016 (a), 사용자 승인 2026-09-25): 전역 앰비언스(도시 원경, 낮/밤), 발소리(바닥 재질 2~3종), 실내 진입 시 앰비언스 전환, 시간대별 전환. WP 착수 당시 코드에는 오디오가 없었다. 근거: [`design/game-features-proposal.md`](../design/game-features-proposal.md) D-016.

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
- 패키징: 기존 Config/Golmok UFS가 audio.json과 전체 크레딧 메타데이터를 포함한다. 별도 cook/UFS 훅3701fb4는 기존 고정 목록 테스트와 충돌해 철회했다. 당시 diff에서는 DefaultGame.ini 변경을 철회했다. 이후 허용 응답을 받아 7be448d로 Audio cook 훅을 반영했다(아래 최종 계약 반영 절). 독립 크레딧 txt는 배포 문서 생성물이다.
- [V-10 런북](../runbooks/pc-verify-wp13.md): 소스 교체·재임포트·남은 런타임/청취 검증·API 표.

### 검증

패키징 훅 추가 전 ruff check/format102, pytest **716 passed / 64 skipped / 208 warnings**(43.46s), check_repo 통과. 첫 CI에서는 추가 UFS 경로가 기존 고정 개수 테스트4개와 충돌했다. 추가 cook 경로도 WP-05 고정 개수 테스트에 걸려 최종적으로 이번 훅을 철회했다. 타 레인 테스트를 임의 완화하지 않고 계약 확장을 요청한다. 크레딧 데이터는 기존 audio.json UFS를 사용한다. 생성 표기의 줄 끝 공백도 제거했다. 최종 결과는 아래에 기록한다. 새 테스트는 경로/라이선스/재생 참조 오류, seed/PCM 결정성, 채택 파일 보존, 가짜 Unreal 임포트/실패·출처 교체를 검증한다. 로컬 symlink 권한 없음1건과 기존 g++ 등63건은 skip이며 CI에서 확인한다.

UE5.8.3 에디터 빌드 **성공(116.60s)**. Python commandlet(nullrhi·nosound)에서 **7개 임포트 + 같은7개 재임포트**, SoundWave 타입·looping·volume 확인 성공, **0 errors / 0 warnings**. `Saved/Automation/WP13/import-result.json`과 로컬 `tools/.venv/audio-import-log.txt`에 근거를 보관한다. 생성된 `.uasset`은 커밋하지 않으며 WAV/JSON/스크립트로 재생성한다. **청취·패키징·런타임 오디오 테스트 결과가 아니다.**

### 런타임 연동 설계 요청·남은 구현

[이슈 #30 요청](https://github.com/wooklym/golmok/issues/30#issuecomment-5861053935): 현행 AGolmokTimeOfDay는 CurrentPreset/InteriorSources 공개 상태만 있고 변경 델리게이트가 없다. 스펙의 이벤트 구독을 충족하려면 Lighting 소유자가 성공한 ApplyPreset 및 InteriorSources 변경 알림을 제공하거나 해당 파일 최소 훅을 허용해야 한다. Debug/GolmokHUD의 audio: 행도 타 레인 연동이다. 이 파일들을 임의 수정하지 않았다.

Fable 검토용 구체안: Audio WorldSubsystem이 초기 TimeOfDay 상태를 읽고 변경 이벤트를 구독한다. 실내 소스가 하나 이상이면 interior를 우선하고, 마지막 실내 소스가 빠지면 현재 프리셋의 outdoor 상태로 돌아간다. A/B 두 컴포넌트로 2초 페이드하며 빠른 재전환 때 현재 gain에서 다음 목표로 이동한다. Controller 교체 탐색과 PawnChanged 델리게이트로 Character에 거리 기반 FootstepComponent를 붙이고, 공중·경로/포토 폰에는 발소리를 내지 않는다. 표면 미지정은 default, 근거 없는 계단 경사 추정은 하지 않고 L_Dev Course/Stairs 태그 및 PhysicalMaterial만 사용한다. pause mute 기본/maintain 옵션은 Photo API로 상태를 읽어 적용한다. 이벤트 제공 전의 대안인 상태 폴링은 스펙과 다르므로 오케스트레이터에 선택을 요청했다.

데이터 기반 단계 당시 **미구현**: Audio C++/순수 수학 교차검증/UE StateMachine·Footstep/콘솔/실시간 전환·착지·HUD·게임 내 크레딧 노출. **미검증**: 패키징에 실제 사운드·크레딧 포함, 재생/청취/최종 음질. 이번 초안은 WP-13 완료·🟡로 표시하거나 최종 병합하지 않는다. 레인 간 설계 응답을 받아 같은 브랜치에서 이어간다.

### 병합 시 반영 (13b 진행, 아직 최종 병합 대상 아님)

> WP-13 🔵: 13a 병합, 13b JSON/결정적 플레이스홀더/임포트/출처·크레딧 기반 구현 및 UE 7개 임포트·재임포트 확인. 런타임 이벤트/HUD 연동 설계 요청 중, C++/Audio 자동화·V-10 청취·패키징 대기. 새 외부 음원 반입·라이선스 약정 없음.

패키징 추가 요청: `tools/tests/test_ue_wp05_fixture.py::test_default_game_ini_packaging_lines`가 cook 등록을 정확히1개로 고정한다. Audio 폴더 추가를 허용하는 타 레인 계약 갱신/훅 권한을 이슈 #30에서 요청한다. 계약 반영 전에는 패키징을 완료 표시하지 않는다.

훅 철회·표기 공백 수정 뒤 최종 로컬 게이트: **716 passed/64 skipped/208 warnings,37.13s**, ruff check/format102·check_repo·main 대비 diff --check 통과. Audio WAV7개 합계1,280,308바이트.


## 13b 런타임 진행 (2026-09-28, 위 데이터 단계 이후)

오케스트레이터의 [00:13Z Fable 설계 결정·최소 훅 허용](https://github.com/wooklym/golmok/issues/30#issuecomment-5861126977)을 받아 이벤트 방식을 구현했다. main `4a31718`까지 충돌 없이 병합했고, 병합된 PR #32 브랜치에는 push하지 않는다.

- Audio WorldSubsystem: JSON 로딩, 월드별 A/B 컴포넌트, 실제 TimeOfDay 프리셋/실내 이벤트 구독, 초기 상태·지연 생성 바인딩, 강제/auto 상태, mute/maintain Photo 정책, 부드러운 볼륨 전환. 늦은 Controller/TimeOfDay 재탐색은0.25s 간격이고 상태 변경은 이벤트다. PawnChanged에서 기존 Player 파일 수정 없이 FootstepComponent를 붙인다.
- FootstepComponent: 수평 거리 누적·걷기/달리기 보폭, 공중 무음·착지1회, 텔레포트/폰 변경/포토/경로 누적 초기화, 재질 트레이스→JSON 세트·default, 명시적 계단 태그. L_Dev 폴더가 런타임 태그라는 가정은 하지 않는다.
- 재생: SoundWave·코드 생성 attenuation/concurrency(최대8 voice), 피치/볼륨 범위, import된 SoundWave gain×master×랜덤(원본 gain 중복 곱하지 않음). 소스 교체는 JSON+임포트만으로 한다.
- `golmok.audio` / `.mute` / `.state`, `golmok.audio credits`가 런타임 JSON의 전체 출처를 출력한다. HUD는 Debug 공급자 등록이며 Debug가 Audio를 include하지 않는다. 현재 확장 공급자는 Audio 하나다.
- 승인된 훅: Lighting/GolmokTimeOfDay.h/.cpp 네이티브 델리게이트2개·성공 경로 broadcast3곳, Debug/GolmokDebugSubsystem.h/.cpp 공급자 배열/캐시 출력. 기존 줄은 변경하지 않고 WP-13 블록으로 추가한다. Audio 폴더·콘솔3개 등록도 훅 줄로 추가한다.
- 순수 GolmokAudioMath.h: 보폭/착지·보간 재타깃·표면 우선순위. g++ 드라이버는 stdin으로1000프레임 거리 누적을 독립 기준과 비교하고 공중/착지/텔레포트/보간 연속성/표면 우선순위를 검사한다.

### 검증과 남은 계약

Audio 단독 자동화 **2 Success, 경고0/실패0/notRun0,0.76s**. StateMachine은 실제 TimeOfDay 이벤트·복수 실내 소스·force/auto·잘못된 상태 거절·mute 플래그·크레딧·컴포넌트 부착을 검사한다. 채널 볼륨0/재생 중 원샷 정지는 헤드리스가 검사하지 않으며 V-10 청취 항목이다. Footstep은 거리/공중/착지/텔레포트/재빙의·보간 계산을 검사한다. 실제 음색/청취를 테스트했다는 뜻은 아니다.

첫 전체 UE 회귀 **28 Success(21+경고7), failed0/notRun0,166.33s**. RenderEvidence NOT EXECUTED1 제외 실제 실행27개. PhotoIntegration6조합·Locomotion4종 등 기존 검사도 실행 성공. 이후 초기 BeginPlay 전 Tick 차단·표면 우선순위/메타데이터 검증 보완 후 최종 빌드/회귀를 다시 수행한다. 로그와 JSON은 Saved/Automation/WP13 및 tools/.venv 아래이며 생성 레벨/에셋/로그는 커밋하지 않는다.

Python에서 런타임 추가 뒤 **1 failed,722 passed,67 skipped**(37.34s)를 확인했다. 실패는 WP-12 런북 고정 총계26개가 코드28개와 다른 `test_runbook_automation_total_matches_the_code`다. [PR #34 요청](https://github.com/wooklym/golmok/pull/34#issuecomment-5861292679)으로 WP-12 런북의 현재 총계28·기존25 및 두 번째 명령 목록 Audio.StateMachine/Footstep 갱신 권한을 요청했다. 기존26개 PC 검증 이력은 보존한다. 앞의 WP-05 cook 고정 목록 계약 요청도 아직 대기다. 타 레인 파일을 임의 수정하거나 테스트를 숨겨 통과시키지 않는다.

### Fable 검토 항목

빠른 제3상태 요청은 조용한 슬롯을 최대50ms 감쇠한 뒤 교체한다(두 슬롯에서 세 소리를 동시에 유지할 수 없음). 이때 요청 상태는 같은 프레임에 바뀌고 새 파일 시작은 최대50ms 지연된다. 현재 값부터 페이드해 파형을 즉시 끊지 않는 방식이며 청취/설계 승인 전 품질 합격으로 기록하지 않는다. PhysicalMaterial 없는 실제 메시의 재질 구분은 default이고, 최종 바닥 세트는 명시적 재질 부여 후 V-10에서 확인한다.

최종 런타임 빌드 **성공10.82s**, 재생 중 발소리 정지 코드를 보완한 뒤 실행한 Audio 필터 **2 Success, 경고0/실패0/notRun0,0.92s**. 직전 전체 회귀 **28 Success(21+경고7),167.19s**, RenderEvidence 제외 실제27개. 최종 Python **1 failed/722 passed/68 skipped/208 warnings,38.15s**이며 실패는 위 WP-12 런북 총계 계약1개뿐이다. ruff check/format103·check_repo·diff --check 통과. CI를 초록 또는 WP-13 완료로 보고하지 않는다.

소유 레인에 제안하는 최소 반영 문안: WP-12 런북 §1 두 번째 명령의 현재 총계 `**26개**`를 `**28개**`로 갱신하고 열거 끝에 `+ WP-13 2개(`Audio.StateMachine/Footstep`)`를 추가한다. 같은 §1에 `현재 코드 기준 헤드리스 자동화 28개(Photo 3 + 기존 25). 아래 §13의26개는 당시 PC 실행 이력이다.`를 추가해 기존 결과표를 보존한다. WP-05 fixture의 cook 등록 검사는 기존 Zones와 새 Audio2개를 확인하도록 확장한다. 이 수정은 권한 응답 뒤만 반영한다.


## 13b 최종 계약 반영 (2026-09-28)

[오케스트레이터 01:27Z 응답](https://github.com/wooklym/golmok/pull/34#issuecomment-5861681375)으로 위 두 계약 대기를 해소했다. WP-12 런북 §1 현재 총계를 28개로 갱신했으며 §13의 26/26 실행 이력은 보존했다(`fd3a318`). DefaultGame.ini 끝 Audio cook 훅과 WP-05 fixture의 허용된 두 줄 예외를 별도 커밋으로 반영했다(`7be448d`). UFS 항목은 추가하지 않았다.

Fable은 빠른 제3상태 최대50ms 교체, 70/110cm 보폭, 재질 default, Photo mute/maintain의 설계 가설을 승인했다. 상태별 `crossfade_seconds_by_state` JSON 값을 추가해 목적 상태별 튜닝을 지원한다. 누락 상태는 전역 crossfade_seconds로 돌아가며 기본값은 모두2초다. 실내1초/실외2초 비교 및 1초 안에 포털 왕복3회 청취는 V-10 런북에 남긴다. 당시 Fable은 메시 Z 스케일 보폭 옵션을 V-10 로스터 비교 뒤 재검토하도록 조건부 허용했다. 이후 V-10 측정/T8에서 기각하고 캐릭터별 보폭으로 대체했다(아래 13d). 실제 소리 품질·패키징 합격을 뜻하지 않는다.

### 병합 시 반영 — 최종 문안 (앞의 중간 단계 문안 대체)

- STATUS의 WP-13 작업 행: **🟡 코드 완료·PC V-10 대기** — 13a 출처 조사·후보 채택, 13b JSON/합성 WAV/임포트·출처/크레딧, 이벤트 기반 환경음 A/B·발소리·HUD/콘솔·헤드리스 검증 완료. 패키징/청취는 V-10.
- STATUS의 Astra 병행 트랙 WP-13 행: **🟡 코드 완료·PC V-10 대기** — PR #34, 기본2초·상태별 JSON 튜닝, Audio cook 훅, 원본 Freesound 계정은 소유자 결정 대기. 리뷰·병합은 오케스트레이터.
- ROADMAP: WP-13 환경음/발소리 코드 완료, 소스 교체는 audio.json+재임포트. V-10에서 패키지 포함·상태 전환/포털·발소리·볼륨·포토 청취 검증 대기.
- D-002 출처 기록: WP-13 현재 WAV7개는 프로젝트의 결정적 합성 플레이스홀더(numpy 기존 의존성, 48kHz PCM16, 합계1,280,308바이트). `project-generated`는 출처 표기이며 외부 라이선스 채택/CC0 권리 포기 선언이 아니다. Freesound CC0 청취 후보7개 조사·채택은 13a 기록 유지, 실제 원본 다운로드/계정 약정은 하지 않음. 출처·저자·라이선스 URL·수정 내역은 audio.json→ATTRIBUTION.md/크레딧 파이프라인으로 보존.

최종 계약 반영 로컬 게이트: ruff check/format103, check_repo, diff --check 통과. pytest **730 passed/68 skipped/208 warnings,34.12s**. UE5.8.3 빌드 **성공12.51s**; 전체 자동화 **28 Success(21+경고7), failed0/notRun0**, 166.97073364257812s. RenderEvidence NOT EXECUTED1 제외 실제27개, Audio2개·PhotoIntegration6조합 실행 성공. 증거는 Saved/Automation/WP13/full-contract-report.json. 패키징/청취는 미실행이며 V-10으로 남긴다. CI 결과는 PR #34의 현재 head 검사 및 최종 코멘트에 기록한다.


## PR #34 리뷰 수정 (2026-09-28 03시 세션)

[02:50Z 리뷰](https://github.com/wooklym/golmok/pull/34#issuecomment-5862385823)의 (A)10건 반영: 모든 asset에 verified 확인일(합성은 생성일)을 필수로 검증·출력하고 표기 파일을 재생성했다. 잘못된 날짜 Python/C++ 검사와 생성 표기 드리프트 검사를 추가했다. 실패 프리셋 호출 전에 night로 상태를 바꾸어 상태 유지를 확인한다. StartSlot은 Stop 직전 볼륨0을 적용한다. mute 자동화는 플래그만 확인하며 채널/원샷 정지는 V-10에서 청취한다는 범위를 명시했다.

런북에 로스터별10보·소유자 gain/장치 기록, 런타임 API9개 위험/대안/단계/결과, 결과표, 빌드→에디터→임포트·헤드리스 재현, cook 목록 명령, 허용 라이선스/URL/확인일을 보완했다. cook 철회는 당시 이력으로 정정했다. (B) ToD도0.25초 재탐색, 임포트 선행·ini 재작성·PhysicalSurfaces·Shipping CC-BY 크레딧도 기록했다. 메시 스케일 보폭 옵션은 로스터 청취 근거를 얻은 뒤 판단한다.

수정 게이트: ruff check/format103·check_repo·diff --check 통과, pytest **736 passed/68 skipped/208 warnings,33.34s**. UE 빌드 **7.47s 성공**, 전체 **28 Success(21+경고7), failed0/notRun0,167.10s**. RenderEvidence NOT EXECUTED1 제외 실제27개. 확인일 오류 거부·night에서 실패 프리셋 상태 유지 검사 실행 성공. 증거 Saved/Automation/WP13/full-review-report.json; 실제 청취/패키징 미실행.

## 병합 기록 — 13b PR #34 (2026-09-28, 오케스트레이터 세션)

대상: [PR #34](https://github.com/wooklym/golmok/pull/34) `astra/wp-13b-audio` 4808c5b(리뷰) → 수정 head(병합 세션이 diff로 (A) 반영 확인). 절차: DEVELOPMENT-PLAN §7.6 — Opus 5.5 ultracode 적대적 리뷰(리뷰어 4관점: 런타임 C++ / 훅·테스트·계약 / 데이터·Python / 라이선스·문서 → 지적 38건마다 회의론자 2명, 80 에이전트) + Fable 설계·품질 검토 → PR 코멘트(2026-09-28 02:50Z) → Astra 수정 → D-019에 따라 소유자 승인 없이 이 커밋(`WP-13: 병합 시 반영 (Fable)`) → merge commit. 전문은 PR #34 코멘트.

- **BLOCKING 없음.** 훅 3커밋(527233c 델리게이트/HUD/등록부, 7be448d Audio cook, fd3a318 WP-12 런북 총계)은 허용 범위 안의 추가 전용. 수명·바인딩·크로스페이드 연속성·50 ms 교체·실내 우선·발소리 누적/재질/게인·Photo mute·콘솔/HUD·순수 헤더 코드상 정확. 라이선스·출처: WAV 7개를 재생성해 LFS 바이트 일치, ATTRIBUTION/크레딧이 JSON 재생성과 동일, CC URL 정확, research/10·공유 문서 무변경. tools pytest 795 passed, ruff·format·check_repo 통과, g++ 드라이버 -Werror -pedantic.
- **(A) 10건 → 수정 반영**: C-1 asset `verified` 확인일 필드(D-002 요구)·B-1 실패 경로 단언(outdoor_night 전제 또는 broadcast 횟수)·B-2 mute 검사 강화 또는 문서 정정·A-3 슬롯 교체 직전 볼륨 0 적용(클릭 방지)·B-4 문서 102행 시점 정정·D3 V-10 로스터별 보폭 체감·소유자 볼륨 밸런스 항목·D4 런타임 UE API 불확실 표(Attenuation/Concurrency, SpawnSound2D+bIsUISound, PhysicalMaterial 트레이스, LoadObject 소프트 경로, OnPossessedPawnChanged, IsTickableWhenPaused)·D5 결과 기록 표·D9 빌드→에디터 순서·헤드리스 임포트 명령·패키징 확인 명령·라이선스 값/URL·D10 표기 파일 드리프트 테스트.
- **(B) 비블로킹(V-10 뒤 후속 가능)**: A-4 ToD 파괴 시 상태 초기화, A-5/B-5 HUD 공급자 인덱스 제거(핸들 방식으로), A-6 0.25 s 폴링 범위 문구, A-7/B-8 임포트 전 PIE LoadObject 경고(DoesPackageExist 선확인), B-7 실내 broadcast가 EnsurePresets 조건 안, C-9 임포트 실패 테스트 2케이스, C-10 ini 중복 섹션 헤더 재작성 주의, C-11 `PhysicalSurfaces` 이름 미정의, C-2 Shipping 크레딧 노출(CC-BY 채택 시 게임 내 UI 필요), D7 보폭 옵션 문구. 반박: A-1, A-2, B-3, B-6, C-3~C-7, D2, D11.
- **Fable 설계·품질**: 승인 가설(상태별 크로스페이드 JSON, ≤50 ms 조용한 슬롯 교체, 실내 우선, 보폭 70/110·달리기 250 cm/s, 재질 default·계단 태그, Photo mute/maintain)이 코드·런북에 그대로 반영. 합격은 V-10 청취(포털 1 s 왕복 3회 클릭, 진입 1 s/복귀 2 s 비교, 로스터별 보폭, 소유자 밸런스). `stride_scale_by_mesh`는 V-10 뒤 후속.
- **(C) 옮긴 것**: STATUS 트랙 1A·병행 트랙 WP-13 행(🟡 코드 완료·PC V-10 대기), ROADMAP 1.6, DECISIONS D-002(합성 플레이스홀더 출처·cook 훅·의존성 없음), astra-tasks T3, 이 절. 병합 시 반영 문안의 칸별 분리(D1/D8)는 병합 세션이 처리.
- 판정: **병합**. 실제 음질·패키징·볼륨 밸런스 합격이 아니며 V-10(PC)에서 판정한다. 원본 음원은 Freesound 계정 소유자 결정(STATUS 결정 필요 ③) 뒤 JSON+재임포트로 교체.


## 13c 결과 — T6 리뷰 (B) 후속 (2026-09-29 KST)

| 항목 | 반영 |
|---|---|
| A-4 | ToD 약한 참조가 파괴되어 null이 된 경우도 이전 바인딩 핸들로 감지. 프리셋·실내 상태 초기화, auto outdoor_day 복귀·새 ToD 재바인딩. 강제 상태는 유지 |
| A-5/B-5 | Debug의 기존 WP-13 훅 안에서 공급자를 FDelegateHandle로 등록/제거. 순서가 바뀌거나 두 번 해제해도 다른 공급자를 지우지 않음. HUD 캐시 무효화 |
| A-7/B-8 | SoundWave LoadObject 전에 패키지 존재 확인, 미임포트는 HUD 진단으로 안내 |
| B-7 | Enter/ExitInterior broadcast가 이미 EnsurePresets 성공 조건 안임을 확인·문서화, Lighting 수정 없음 |
| C-9 | 빈 imported_object_paths·SoundWave 아닌 객체 실패 회귀. 실패 시 기존 크레딧/ATTRIBUTION 유지 |
| C-11 | 프로젝트에 이름이 정의되지 않은 PhysicalSurface 번호는 default. 명시 계단 태그 우선, 이름 있는 매핑만 적용 |
| A-6/C-10/D7 | Controller+ToD 0.25 s 재탐색 범위, Packaging ini 재작성 주의, 메시 스케일 보폭은 V-10 청취 후 결정임을 런북에 명시 |
| C-2 | Shipping 크레딧 UI 보류(이번 배정 제외, 실제 음원 확정 후) |

검증: ruff check·format103·pytest818 passed/77 skipped·check_repo·diff check 통과. UE 최종 빌드4.92s 성공(최초128.95s), -SetupDevLevel -Filter Golmok.Audio 2 Success(경고1)·실패0. 전체 -SetupDevLevel 28 Success(20+경고8)·실패0·미실행0; 기본 RenderEvidence의 NOT EXECUTED를 제외한 실제27개. 기존 Audio.StateMachine/Footstep에 수명·HUD 핸들·미정의 표면 회귀 추가, 새 등록 없음. 청취/패키징/GUI 미실행, CI는 PR checks가 정본.

## 병합 시 반영 — 13c T6

STATUS 트랙 1A WP-13 행의 상태는 **🟡 코드 완료·PC V-10 대기** 유지. 근거 칸에 추가할 한 문장: “13c T6 리뷰 (B) 후속: ToD 수명 초기화·HUD 핸들·미임포트 패키지 선확인·미정의 물리 표면 default·임포트 실패 회귀, 헤드리스 검증; 청취·패키징 및 Shipping 크레딧 UI는 별도.”

## 병합 기록 — 13c T6 PR #50 (2026-09-28, 오케스트레이터 세션)

**내용**: PR #34 리뷰 (B) 중 청취 결과와 무관한 항목 — A-4 ToD 파괴 시 상태 초기화·재바인딩, A-5/B-5 HUD 공급자 인덱스 → 핸들 API(Debug/ 기존 `[WP-13 hook]` 블록 내부, 별도 커밋), A-7/B-8 `DoesPackageExist` 선확인, B-7 조건 위치 확인, C-9 임포트 실패 테스트 2케이스, C-11 미정의 `PhysicalSurfaces` → `default`, A-6/C-10/D7 문구. C-2(Shipping 크레딧 UI)는 오케스트레이터 보류(음원 확정 뒤). Astra 보고: PC 빌드, `Golmok.Audio` 2 Success(경고 1), 전체 28 Success, CI 10/10.

**병합 전 리뷰(Opus 읽기 전용)**: BLOCKING·major 없음. 확인: 레인·hot-spot 준수(Debug/ 2파일은 훅 블록 내부, 재정렬 없음), 핸들 API 수명 안전(고유 ID·멱등 제거·HUD 캐시 무효화·Deinitialize 해제·weak 람다), 공급자 수 ==1 단언 유지, PR #49/#51/#52와 Debug 충돌 없음(merge-tree), A-4·A-7·B-7 동작, C-9 변이 3종 검증, 로컬 pytest 892. (B) 8건 → V-10 뒤 다음 Audio push: R50-1 미정의/미명명 표면 무진단 폴백(번호당 1회 경고 + 이름↔세트 id 대조 자동화 또는 이름 키잉), R50-2 런북 재질 비교 단계에 SurfaceType1~3 이름 지정 전제(`DefaultEngine.ini` 변경 커밋 금지), R50-3 헤드리스 경고 0→1(전체 21+7→20+8) 원인 기록, R50-4 훅 커밋 순서(중간 커밋 단독 빌드 불가), R50-5 B-5 잔여(`audio:` 줄 실제 단언·상대 개수), R50-6 패키지 실행에서 `error: missing SoundWave` 없음 확인, R50-7 D-019 훅 API 변경 기록(이번 병합 커밋에서 반영), R50-8 13b D7 문구.

**병합**: 오케스트레이터 결정(D-019). WP-13 🟡 코드 완료·PC V-10 대기 유지.

## 병합 기록 — V-10 PC 검증 [PR #53](https://github.com/wooklym/golmok/pull/53) → [PR #54](https://github.com/wooklym/golmok/pull/54) (2026-09-28)

대상: PC 세션(Claude Desktop 워크트리 `stoic-kare-964e86`, Fable 5.1) `pc/v10-verify-wp13` 6273f78 → 클라우드 병합 브랜치 `claude/v10-merge`(main 4f91133 병합, STATUS·런북 충돌 해결). 리뷰: Opus 5.5 읽기 전용(R53-x, #53 코멘트)·Fable 설계 판단(런북 §7-3). 병합: 오케스트레이터 결정(D-019).

- **판정: WP-13 🟢·V-10 🟢**(결함 0). 근거는 master submix 녹음 파형 분석(PIE)과 WASAPI 루프백(패키지)이며 사람 청취가 아니다. 빌드 무수정, 임포트 7+7, 자동화 Audio 2/2·전체 28, 낮/밤·실내 전환·포털 빠른 왕복 클릭 없음·재질 4종·태그 계단·착지·Photo mute/maintain·PIE 재시작 3회·clipping 0, 패키지에 SW 7개·audio.json·크레딧, 루프백 재생. A1~A9 결과 채움(코드 수정 없음). PC fix `tools/ue/package.ps1` `-ubtargs=-NoHotReloadFromIDE` 1건(Astra 레인 아님). 런북 §6·§7.
- **소유자 항목(비차단)**: C-07 Windows 보안 대화상자(패키지 발소리 청취·이후 PC GUI 카드 차단), C-08 볼륨·크로스페이드 청취·최종 gain.
- **Fable 설계 판단 → Astra T8**(`astra-tasks.md`, D-016 진행 2026-09-28): ① 실내 크로스페이드 1.0 s 채택 ② equal-power(sin/cos) 곡선 채택 ③ Photo mute 0.25 s 페이드 채택 ④ `stride_scale_by_mesh` 기각 → 캐릭터별 걷기/달리기 보폭 데이터(임시; V-08 뒤 노티파이) ⑤ 볼륨 후보(master 1.0·낮 0.5·밤 0.36·실내 0.30·발소리/착지 1.0) 임시 적용 ⑥ 생성 `Content/Golmok/Audio/*/SW_*.uasset` ignore(이 PR). T8에는 PR #50 리뷰 (B) R50-1~8도 포함.
- **(C) 옮긴 것**: STATUS 마지막 갱신·WP-13 행 2개·V-10 행(PC 세션 작성)·C-07·C-08, DECISIONS D-016 진행 (a), ROADMAP 1.x WP-13 🟢, astra-tasks T8·우선순위, `.gitignore`.
- 후속(R53-5, 2026-09-28): `tools/golmok_tools/audio_analysis.py`(RMS 안착·클릭 z·급정지(abrupt stop)·dip·clipping, `python -m golmok_tools.audio_analysis`) — [PR #57](https://github.com/wooklym/golmok/pull/57)


## 13d 결과 — T8 V-10 후속 (2026-09-29 KST)

배정: [이슈 #30 Fable T8](https://github.com/wooklym/golmok/issues/30#issuecomment-5879528015). main `f759bf8`에서 착수 후 WP-14a 병합 `2e6b642`를 충돌 없이 반영했다. WP-14a의 프리셋/실내 이벤트 계약은 그대로 사용하며 Lighting/Debug/Player·ini 변경과 새 훅은 없다.

| 항목 | 반영·판정 |
|---|---|
| 목적 상태 전환 | 실내1.0초·실외2.0초, 슬롯별 전력 보간 `sqrt(F² + (T²-F²)*alpha)`. 상보 슬롯 합산 전력·중간 재타깃·50ms 교체 수학 회귀. 제3슬롯 교체/초기 시작의 일정 전력이나 서로 다른 음원의 같은 청감을 주장하지 않음 |
| Photo | 별도 0.25초 envelope, JSON `photo_mute_fade_seconds`(0~5, 생략 .25, 0 즉시). GamePause에서 진입 중간값→0→종료 중간값→1 실제 헤드리스 검사. 원샷 FadeOut·새 원샷 억제. 출력 파형은 PC 미검증 |
| 로스터 보폭 | `footsteps.stride_cm_by_character`: manny/quinn 67/146, proxy135 54/142, proxy110 45/115cm, 없으면70/110. 같은 폰에서 id 변경 시 거리 리셋. `stride_scale_by_mesh` 기각·입력 거부. V-08 이후 노티파이 재검토 |
| 볼륨·발소리 | master1.0, 낮.5·밤.36·실내.30, 발소리/착지1.0. 자체 발소리/착지는 SpawnSound2D로 카메라 붐 감쇠 제거. 다른 소스용 attenuation 설정 유지. 최종 청취/밸런스는 C-08 |
| R50-1·2·5·6 | 표면 이름↔세트 id 대소문자 무관 대조, 누락/불일치 HUD 오류와 fallback. `steps=`로 default/asphalt 진단. HUD 실제 `audio:` 줄·Before+2→Before 공급자 수 검사. 런북에 임시 Physics 이름·복사 맵·ini 원상복구 및 패키지 `error: missing SoundWave` 부재 확인 |
| R50-3 | T6 추가 경고는 Audio.StateMachine의 ToD 파괴/재생성 중 L_Dev GeoOrigin 부재 안내(런북 §8에 전문). 누락 SoundWave 경고가 아니며 숨기지 않음 |
| R50-4·7·8 | 이번 훅 없음(향후 의존 훅 우선); D-019 기록은 오케스트레이터가 이미 반영. D7 당시 조건부 허용→V-10 뒤 기각 이력 정정 |
| 스키마/출처 | Python/C++ 새 필드 타입·범위·기본값 일치. UE의 bool/숫자 문자열 자동 변환을 발견해 Number/Range에서 숫자 타입 요구. 실패 파싱의 기존 설정 보존 검사. source/출처는 변경하지 않았으며 실제 임포트·재임포트7+7, gain/loop 확인·크레딧 동일 |
| 런북 | 포털 기준을 0.5 s 간격3왕복으로 정정. §6·§7의 V-10 원래 측정값·PC cook 명령·이력을 보존하고 T8 검증 범위를 별도 표기 |

검증: ruff check/format104·check_repo·diff --check 통과. pytest **881 passed/185 skipped/208 warnings,34.43s**(로컬 g++ 등 건너뜀; CI 교차검증 별도). UE5.8.3 빌드 **32.24s 성공**(엔진 C4996 경고), 실제 SoundWave **7개 임포트+재임포트7개**, loop/gain 일치·**0 errors/0 warnings**·ATTRIBUTION/크레딧 diff 없음. `test.ps1 -SetupDevLevel -Filter Golmok.Audio`: **2 Success(경고1), failed0/notRun0,1.88s**. 전체 `test.ps1 -SetupDevLevel`: **29 Success(21+경고8), failed0/notRun0,172.34s**; RenderEvidence NOT EXECUTED1 제외 실제28개. WP-14a Lighting.Clock·PhotoIntegration6조합 포함. 근거는 로컬 tools/.venv/t8-{import.log,audio-report.json,full-report.json,pytest.log}. CI 결과는 PR checks/이슈 보고가 정본.

제한: 기존 WP-13/V-10 🟢는 `5f6c810` 녹음 파형/루프백 근거다. 이번 T8과 T6의 런타임 PC 스모크·청취·패키지 발소리는 새 결과가 없으며 C-07 뒤 실행한다. C-08 최종 gain·크로스페이드 체감은 소유자 판단, C-2 Shipping 크레딧 UI는 실제 소스 확정 뒤 별도 배정이다. 새 음원 채택·구매·약정·외부 의존성 없음.

## 병합 시 반영 — 13d T8 (병합 커밋에서 적용, 2026-09-29)

- STATUS 트랙 1A WP-13 및 병행 트랙 WP-13 행: **🟢 V-10 PC 검증 통과(5f6c810 파형·루프백 근거)** 유지 + "13d T8 [PR #55](https://github.com/wooklym/golmok/pull/55): 실내 1.0/실외 2.0 s·전력 보간(sin² 성형)·Photo 0.25 s·로스터별 보폭·2D 자체 발소리·임시 gain·표면 이름=세트 id 계약·R50 후속 구현·헤드리스 검증. T6/T8 런타임 PC 스모크·새 설정 청취·패키지 발소리는 C-07 뒤 V-11 카드, 최종 밸런스 C-08 대기."
- STATUS C-08 행: T8 적용 완료, C-07 뒤 같은 장치·OS 볼륨으로 재녹음·청취(착지/발소리 −1.6 dB, 2D 추가 상승 추정 유의).
- astra-tasks T8 행: "병합(#55, 2026-09-29; 헤드리스·UE 빌드) — 런타임 출력·청취·패키지 발소리는 C-07 뒤 PC"; 우선순위 줄: ~~T8~~ → T7 RHI(C-07 뒤) + 다음 오디오 push(R55-5/7/9).
- 런북 §6 소유자 밸런스 행: PR 본문 문안으로 교체(V-10 측정값 보존, T8 임시 값, +9.1/+7.5 dB 산술, 2D 추정).
- D-016 진행: T8 병합, 곡선 결정(sin² 성형·Photo S-curve), 표면 이름=세트 id 계약, 최종 음질/밸런스 합격 미포함.
- 자동화 총수: main 병합 뒤 기대값 **32**(Audio 2 불변); PR의 29는 base 2e6b642 기준.

## PR #55 리뷰 보완 — R55 (2026-09-29 KST)

[리뷰](https://github.com/wooklym/golmok/pull/55#issuecomment-5880728596)·[배정](https://github.com/wooklym/golmok/issues/30#issuecomment-5880730532)에 따라 같은 브랜치에서 R55-1/2·권장 R55-4/6/8을 한 번의 push로 반영한다. 위 13d 초기 구현 설명 중 곡선/진단/Photo 테스트는 이 절로 갱신한다.

- **R55-1(Fable 결정)**: 전력 보간의 진행값을 `u = (1 - cos(pi * alpha)) / 2`로 성형한다. 0↔1은 sin/cos 법칙이며 상보 전력·재타깃 연속성·50ms 교체를 유지한다. Photo는 같은 진행값으로 **진폭**을 보간하고 원샷은 `FadeOut(D, 0, SCurve)`를 사용한다. g++ 드라이버에 Photo 모드와 60fps 첫 틱/끝점 검사를 추가하고 C++ 기대값도 갱신했다.
- **R55-2**: 서브시스템의 `WarnedSurfaces`로 월드별 표면 번호당 Warning 한 번을 남긴다. 발걸음 진단을 한 번 계산해 매핑과 HUD에 재사용한다. Physics 표면 이름은 세트 id와 대소문자 무관하게 같아야 매핑되며, 아니면 default + HUD error + 1회 로그(명시 계단 태그 우선). 자동화는 서로 다른 2번호 및 반복·HUD 초기화 후 재호출에 정확히 각1회 로그를 요구한다. 이 의도적 경고만 ExpectedMessage로 검증하고 L_Dev GeoOrigin 경고는 그대로 보고한다.
- **R55-4**: 미사용 Location/Point 전달 제거, attenuation은 비로컬 소스 예약 주석으로 목적 명시. SpawnSound2D가 Play 전에 UI sound를 설정하므로 사후 bIsUISound 대입 제거.
- **R55-6**: Photo 시나리오는 mute/양수 fade일 때만 실행하고 다른 설정은 NOT EXECUTED 안내. 목표0/1 도달을 폴링하며 각 단계10초 타임아웃으로 제한한다. 고정 시각 중간값은 순수 곡선 검사로 옮겼다. HUD audio 줄 정확히1개 단언, 테스트 라벨 수정.
- **R55-8**: 런북 C-11·§7-5의 이름/세트 계약, §6 포털 원문과 T8 정정 병기, 불확실 API A10(FadeOut/UI sound/GamePause 실제 출력 미검증)을 추가했다. 기존 PC 수치는 보존했다.

검증: ruff check/format104·check_repo·diff --check 통과, pytest **881 passed/187 skipped/208 warnings,34.77s**(로컬 g++ 없음, 새 순수 검사2개 포함 skip; CI 별도). UE5.8.3 최종 빌드 **4.94s 성공**, Audio **2 Success(경고1), failed0/notRun0,1.40s**. 전체 **29 Success(21+경고8), failed0/notRun0,171.73s**; 기본 RenderEvidence NOT EXECUTED1 제외 실제28개. GamePause fade 목표0/1 실제 도달 및 표면 로그 개수 회귀 통과. 근거는 로컬 tools/.venv/r55-*.log·*-report.json, CI는 PR 체크/보고 코멘트가 정본.

R55-3 공유 문안/큐·C-08·소유자 밸런스 행과 main 통합은 오케스트레이터 병합 커밋 담당(요청 순서). 따라서 이 수정의 전체 UE 실측은 기반 `2e6b642`의29개이며 현재 main 기대값32와 구분한다. R55-5/7/9는 배정대로 다음 오디오 push에 남긴다. C-07·C-08 및 실제 출력 청취 제한은 그대로다.

## 병합 기록 — 13d T8 [PR #55](https://github.com/wooklym/golmok/pull/55) (2026-09-29)

대상: `astra/wp-13d-v10-followups` ef3ace7(Astra push 정지) + 오케스트레이터 병합 커밋(main 6872583 병합·충돌 없음·위 병합 시 반영). 리뷰: Opus 5.5 읽기 전용 적대 검증 R55-1~9 + Fable 설계 검토(#55 코멘트). 병합: 오케스트레이터 결정(D-019).

- **판정: 병합(A 없음).** T8 ①~⑨ 전부 구현, R50-1/2/5/6 후속 포함. (B) R55-1(Fable 결정: 전력 보간 α=sin²(πα/2) 성형·Photo 진폭 S-curve·원샷 SCurve)·R55-2(표면 번호당 1회 Warning·진단 1회 계산) 및 (C) R55-4/6/8을 Astra가 한 번의 push(bf9522d·ef3ace7)로 반영; R55-3(공유 문안)은 이 병합 커밋; R55-5(bool/문자열 타입 엄격성)·R55-7(보폭 id 교차 검사)·R55-9(밸런스 추정 문안 — 런북 §6에 반영)는 다음 오디오 push.
- **Fable 설계 검토**: 전력 영역 보간·실내 1.0 s·Photo 0.25 s·캐릭터별 보폭·SpawnSound2D 자체 발소리·임시 gain은 T8 결정과 일치. 새 계약(표면 이름=세트 id)은 V-10 §7-5의 임시 이름(`V10Asphalt` 등)이 더 이상 매핑되지 않으므로 다음 PC 카드는 세트 id 이름을 쓴다.
- **검증 범위**: 헤드리스·UE 5.8.3 빌드·`Golmok.Audio` 2/2·전체 29(base 2e6b642; main은 32)·CI 10/10. 실제 파형·음색·밸런스·패키지 발소리는 미실행 — C-07 뒤 V-11 카드(T6/T8 스모크, §7-1a 도구 재녹음), C-08 소유자 청취.
- **(C) 옮긴 것**: STATUS 마지막 갱신·WP-13 행 2개·C-08, astra-tasks T8·우선순위, 런북 §6 소유자 밸런스 행, DECISIONS D-016 (a) 진행, 이 절.


## 13e 결과 — T9 R55 잔여 (2026-09-29 KST)

배정: [이슈 #30 T9](https://github.com/wooklym/golmok/issues/30#issuecomment-5881358195), 분석 도구 병합 반영 뒤 main `2b152ce`에서 새 브랜치 `astra/wp-13e-r55-followups`로 착수했다. 병합된 T8 브랜치에는 push하지 않는다.

- **R55-5**: C++ `loop`/`placeholder`는 JSON Boolean, 공통 `String()` 및 빈 값이 허용되는 `license_url`은 JSON String을 요구한다. 이 필드들에서 UE의 숫자/문자열 자동 변환을 허용하지 않으며 기존 정상 매니페스트는 그대로 읽는다. 참조 배열·매핑 값의 타입 검사는 13f에서 보완한다. C++의 bool 필드 숫자·문자열 변이와 author 숫자·bool 변이, 실패 뒤 기존 설정 보존을 검사했다. Python 쪽에도 대응하는 변이 6개를 추가했다.
- **R55-7**: 보폭 설정의 모든 키가 `characters.json` 로스터 id인지 검사하는 pytest를 추가했다. 알 수 없는 키는 실패, 보폭 항목이 없는 로스터 id는 전역 보폭 fallback을 사용한다는 UserWarning이며 실패로 처리하지 않는다. 로스터 파일은 읽기만 하며 수정하지 않았다.
- **런북 범위 점검**: §6 소유자 밸런스 행의 R55-9 추정값·미측정 표시, §7의 이전 V-10 실행 이력과 §7-1a 분석 도구, §8 T8 실제 출력 미검증 범위가 유지됨을 확인했다. 중복 수정은 하지 않았다. R55-9는 병합 세션 완료 사항으로 T9에서 제외한다.

검증: 로컬 ruff check/format·check_repo·diff --check 통과(추적 파일 기준 format 대상106). pytest **1000 passed/203 skipped/208 warnings,39.46s**(로컬 g++ 등 skip, CI 별도). UE5.8.3 빌드 **68.47s 성공**(엔진 C4996 경고). Audio **2 Success(경고1), failed0/notRun0,1.24s**. 전체 **32 Success(21+경고11), failed0/notRun0,178.56s**; RenderEvidence 기본 NOT EXECUTED1 제외 실제31개. 근거: 로컬 tools/.venv/t9-*.log·*-report.json. CI 결과는 PR 체크/보고 코멘트가 정본.

훅·공유 문서·설정 값·음원·출처·새 품질 정책 변경 없음. 이번 엄격성/테스트 보완은 헤드리스 결과이며 T6/T8의 실제 출력·청취·패키지 발소리를 대신하지 않는다. T7 RHI 및 C-07/C-08 대기는 그대로다.

### 병합 시 반영 — T9

astra-tasks T9 행/STATUS Astra 진행 기록 문안: “T9 13e: R55-5 C++ Boolean/String 타입 엄격성 및 변이 회귀, R55-7 보폭 키↔로스터 교차 검사(미등록 키 실패·보폭 누락 경고), 런북 범위 점검 완료. 헤드리스 검증; T6/T8 출력·청취는 C-07 뒤 PC, 다음 T7 RHI도 PC 조건 뒤.” 기존 WP-13/V-10 🟢 및 C-08 판정 범위는 유지한다.

## 병합 기록 — 13e T9 [PR #63](https://github.com/wooklym/golmok/pull/63) (2026-09-29)

대상: `astra/wp-13e-r55-followups` 25901ad(Astra push 정지) + 오케스트레이터 병합 커밋(main 3079dad 병합·충돌 없음·위 병합 시 반영). 리뷰: Opus 5.5 읽기 전용 적대 검증 R63-1~6(#63 코멘트). 병합: 오케스트레이터 결정(D-019). 설계 변경·새 품질 가설이 없어 Fable 설계 검토는 없다.

- **판정: 병합(A 없음).** R55-5·R55-7·런북 범위 점검 완료. 필드별 타입 일치표(#63 코멘트 §2): `loop`/`placeholder`·`String()` 필드·`license_url`은 C++와 Python이 같은 JSON 타입을 요구하고, Python이 받는 매니페스트를 C++가 거부하는 경우는 없다. 배포된 `audio.json`은 그대로 읽히고 실패 시 이전 설정이 유지된다.
- **(B) 다음 오디오 push**: R63-1 — `footsteps.sets` 원소·`surface_sets` 값·`preset_states`는 아직 `FJsonValue::TryGetString` 강제 변환이 남아 있다(Python이 거부하는 두 매니페스트를 C++가 수락; 커밋본은 CI의 Python 검사가 먼저 막으므로 PC 로컬 편집(C-08) 때만 영향). 따라서 위 13e 결과의 "UE의 숫자/문자열 자동 변환을 허용하지 않으며"는 `loop`/`placeholder`/`String()` 필드에 한한 말로 읽는다. 수정은 `EJson::String` 가드 3곳 + C++ 변이 1개. R63-2 — C++ 파서 실패 메시지가 항상 같은 문장이고 Python `text()`/`number()`도 필드 이름이 없다(이전부터의 문제). 실패 지점마다 필드·기대 타입을 넣는다.
- **(C)**: R63-3 경고 문구의 70/110 cm 하드코딩·오타 메시지 안내·레인 간 계약 문서화(astra-tasks T9 행에 적음: 로스터 id 변경·삭제는 같은 PR에서 `stride_cm_by_character` 갱신), R63-4 테스트 라벨·parametrize·보존 비교는 다음 오디오 push. R63-5: 위 검증 문단의 "ruff check/format108"은 로컬 파일이 섞인 수치이고 head 기준 `ruff format --check`는 106 files다(13f T10 #65에서 정정).
- **검증 범위**: 리뷰 세션 게이트(ruff·pytest 1200 passed/3 skipped, g++ audio math 8/8 실행·check_repo·diff --check)·main 3079dad 시험 병합 충돌 없음·CI 10/10. UE 빌드·`Golmok.Audio` 2/2·전체 32는 Astra 보고 수치. 실제 출력·청취·패키지 발소리는 미실행 — C-07 뒤 V-11 카드(T6/T8 스모크), C-08 소유자 청취.
- **(C) 옮긴 것**: STATUS 마지막 갱신·WP-13 행·세션 로그, astra-tasks T9 행 신설·T8 행·우선순위, 이 절.

## 13f 결과 — T10 R63 잔여 (2026-09-29 KST)

배정: [이슈 #30 T10](https://github.com/wooklym/golmok/issues/30#issuecomment-5882698771). T9 병합 뒤 main `5c4464e`에서 `astra/wp-13f-r63-followups`로 착수했다. 배정문의 Python 경로는 실제 파일 `unreal/Golmok/Content/Python/golmok/audio_pure.py`로 해석했다.

- **R63-1**: C++ `footsteps.sets` 배열 원소·`surface_sets` 값·`preset_states` 값에 JSON String 가드를 추가했다. 문자열 세트 `"1"`과 숫자 표면 값 `1`, 문자열 에셋 `"true"`와 bool 배열 원소, bool 프리셋 변이를 거부한다. 문자열 대조군은 수락하며 거부 뒤 Credits·Assets.Num을 그대로 보존한다. 13e 결과의 타입 엄격성 문구도 당시 적용 필드로 한정했다.
- **R63-2**: C++ 파서 reader가 전체 필드 경로와 기대 타입/범위/참조를 실패 위치에서 기록한다. 예: `audio.json footsteps.surface_sets.4: expected string`. 성공할 때만 새 설정을 반영한다. HUD의 기존 `LoadError`→`Describe()`→`error:` 전달은 그대로 사용하므로 AmbienceSubsystem 파일 변경은 불필요하다. Python `text`/`number`에 field 인수를 추가하고 객체·필수 값·날짜·배열 인덱스·참조 오류에도 경로를 붙였다. 기존의 Python 추가 제약(문자열 공백/탭/표 구분자, 스키마 정수 등)까지 C++와 완전히 같다고 주장하지 않는다.
- **R63-3**: 로스터 보폭 누락 경고는 실제 walk/run 전역값을 읽는다. 임시 81/123cm 및 누락 manny 변이로 경고를 검사했다. 미등록 id 실패에는 같은 PR에서 `footsteps.stride_cm_by_character`를 갱신하라는 안내를 넣고 회귀로 확인했다.
- **R63-4·5**: pytest의 bool/string 6조합을 명시하고 진단 문구를 단언했다. C++ 라벨에 Field/Value, 루프마다 Credits·Assets.Num 보존 비교를 추가했다. 13e의 format108은 로컬 표기와 추적 파일106으로 정정했다.

검증: 로컬 ruff check/format·check_repo·diff --check 통과(Python 파서는 tools/pyproject.toml 규칙으로 별도 검사). pytest **1011 passed/203 skipped/208 warnings,38.13s**(g++ 등 로컬 skip, CI 별도). UE5.8.3 최종 빌드 **5.54s 성공**, Audio **2 Success(경고1), failed0/notRun0,1.25s**. 전체 **32 Success(21+경고11), failed0/notRun0,178.38s**; RenderEvidence 기본 NOT EXECUTED1 제외 실제31개. 실제 SoundWave **7개 임포트+재임포트7개**, loop/gain 일치·크레딧 diff 없음. 근거: 로컬 tools/.venv/t10-{build.log,pytest.log,audio-report.json,full-report.json,import.log}. CI 결과는 PR checks/이슈 보고가 정본.

레인5파일만 변경했다. 훅·핫스팟·공유 문서·ini·audio.json·characters.json·음원·출처 변경 없음. 초기 추가 C++ 배열 변이 테스트의 공백 의존성을 발견해 JSON 직렬화한 입력으로 고친 뒤 재검증했다. 청취·실제 출력·패키지 발소리는 이번 헤드리스 결과에 포함하지 않는다. 기존 WP-13/V-10 🟢 판정 범위, T7 RHI의 C-07/PC 조건 및 C-08 소유자 청취는 유지한다.

### 병합 시 반영 — T10

- **astra-tasks T10 행**: “T10 13f — R63-1~5 완료: 참조 문자열 타입 가드·필드 경로 진단·설정값 보폭 경고·변이/보존 회귀·13e 문구 정정. `astra/wp-13f-r63-followups`, 헤드리스/UE 빌드 통과. 다음 T7 RHI는 C-07 해소·PC 카드 뒤.” PR 번호는 병합 대상 PR 링크를 붙인다.
- **STATUS Astra 진행 한 줄**: “T10 13f R63 잔여 구현·헤드리스 검증 완료(참조 타입·필드 진단·보폭 경고·회귀). WP-13/V-10 기존 🟢 범위 유지, T6/T8 실제 출력·청취·패키지 발소리는 C-07 뒤 V-11/C-08, T7 RHI도 PC 조건 뒤.”

## 병합 기록 — 13f T10 [PR #65](https://github.com/wooklym/golmok/pull/65) (2026-09-29)

대상: `astra/wp-13f-r63-followups` 117f820(Astra push 정지) + 오케스트레이터 병합 커밋(main 5c4464e 병합·변경 없음·위 병합 시 반영). 리뷰: Opus 5.5 읽기 전용 적대 검증 R65-1~8(#65 코멘트). 병합: 오케스트레이터 결정(D-019). 설계 변경·새 품질 가설이 없어 Fable 설계 검토는 없다.

- **판정: 병합(A·B 없음).** R63-1~5 전부 반영. 타입 일치표(#65 코멘트 §2): 위험 방향(Python 수락·C++ 거부) 없음, C++의 `TryGet*` 호출은 모두 타입 가드 뒤에만 있어 강제 변환 경로 0. 새 C++ 변이 3종(숫자 표면 매핑·bool 샘플·bool preset)은 거부와 정확한 메시지를 함께 단언하고 문자열 대조군 2종은 수락을 단언한다.
- **진단 형식**: C++ `audio.json <경로>: expected <기대>`(ASCII·한 줄), 실패 시 이전 설정 유지(`Out = MoveTemp(Next)`는 성공 뒤에만), HUD는 기존 `LoadError → Describe()` 경로 그대로(`GolmokAmbienceSubsystem.cpp` 무수정). Python `parse_config`의 모든 raise에 필드 경로. 파일 미발견 메시지는 상대 경로만.
- **Python 재작성 의미 동일**: 배포 `audio.json` 기준 값 교체·삭제·키 추가 퍼징 14,647건에서 PR 전/후 수락/거부 차이 0. 예외 타입만 ValueError로 통일(868건). 의도하지 않은 강화 1건(R65-1: `surface_sets` 값이 공백·제어 문자를 포함한 세트 id를 가리키면 거부 — 현재 세트 id에는 영향 없음, 안전 방향). 과제 밖 포맷 변경 포함(줄 길이 110, import 순서; 의미 동일). `attribution()` 출력은 커밋된 `ATTRIBUTION.md`·`Credits/audio-credits.txt`와 바이트 동일.
- **(C) 다음 오디오 push 선택**: R65-1 세트 id 정의 쪽에서 C++/Python 같은 정규식 검사, R65-2 JSON 구문 오류에 `Reader->GetErrorMessage()` 줄·열 + 로드 실패 `UE_LOG` 1회, R65-3 참조 실패 3종의 보존 검사에 `Sets`/`Assets`/`Presets` 항목 단언, R65-4 변이 생성을 텍스트 치환 대신 DOM 수정으로, R65-5 오류 경로의 제어 문자 치환, R65-7 기존 `raises(ValueError)` 40 케이스에 `match=`. R65-6(포맷)은 조치 없음. R65-8은 이 커밋(13e 병합 기록 "(원문 유지)" 정정·빈 줄).
- **검증 범위**: 리뷰 세션 게이트(ruff·format 106, pytest 1211 passed/3 skipped, g++ audio math 8/8 실행, `test_ue_config_audio` 64/64, check_repo·diff --check)·main 5c4464e 시험 병합 트리 동일·CI 10/10. UE 5.8.3 빌드·`Golmok.Audio` 2/2·전체 32·SoundWave 임포트 7+7은 Astra 보고 수치(Astra 정정, #65 코멘트: "최종 빌드 5.54 s"는 up-to-date 실행이 아니라 `GolmokAudioConfig.cpp`·`GolmokAudioTest.cpp` 실제 컴파일·lib/dll 링크·WriteMetadata 5 actions의 결과이며 문서 커밋 전 최종 C++ 검증, 근거 로컬 `tools/.venv/t10-build.log`). 실제 출력·청취·패키지 발소리는 미실행 — C-07 뒤 V-11 카드(선택 추가: gain을 `"0.5"`로 바꿔 HUD `error: audio.json assets.<id>.gain: expected finite number in [0, 1]` 확인 뒤 원복), C-08 소유자 청취.
- **(C) 옮긴 것**: STATUS 마지막 갱신·WP-13 행 2개·세션 로그, astra-tasks T10 행 병합 표기·T9 행·우선순위, 이 절.


## T13 — WP-19c 노티파이 발소리 결과 (2026-09-30)

이슈 #30의 5907278376 배정. T12 PR #77 위 별도 `astra/wp-19c-footstep-notify` 스택에서 오디오 레인만 변경했다. `footsteps.driver`는 선택 키이며 auto 기본값으로 이전 일반 폰의 distance 동작을 유지한다. C++/Python은 잘못된 문자열·타입을 같은 필드 경로로 거절한다. 데이터 외 음원/라이선스·보폭·볼륨 값은 바꾸지 않았고 크레딧 파이프라인도 같다.

- native GASP 계열 폰의 auto 및 명시 notify는 첫 이벤트 전부터 거리 스테퍼를 멈춘다. `OnFootEvent`를 구독해 Step/Land를 각각 발소리/착지 재생 경로로 전달하고, distance는 이벤트를 무시한다.
- pause/photo·현재 플레이어 아님을 검사한다. 컴포넌트 등록/해제에 맞춰 구독하고 바뀐 공급 컴포넌트는 tick에서 다시 연결한다. 두 드라이버가 동시 재생하지 않는다.
- BlueprintPure `UsesNotifyDriver()`는 19b가 읽을 수 있는 설정 훅이다. **GASP 원본 폴리 비활성화 자체는 미구현**이며 V-08b §5 결과 뒤 정확한 BP 경로에 연결한다. 임의 원본 함수/ini/에셋 변경은 없다. 실제 폴리 억제·발 시점·청취·패키지 출력은 19b/V-15 대기다.
- 기존 `Golmok.Audio.Footstep` 등록 안에 native 폰/합성 이벤트 PIE 검사를 추가했다. 실제 PlayFootstep 진입점 계수는 WITH_DEV_AUTOMATION_TESTS 한정이다. Step/Land 각각 1요청, 거리 중복 0, pause·빙의·구독 해제·재등록 검사를 실행했다. GASP 패키지 없이 도는 계약 검사이며 -nosound 재생 요청을 청취 성공으로 세지 않는다.

검증: UE 5.8.3 build 성공, 오디오 단독 2 state=Success(1 + warning1), Python ruff check/format 113·pytest 1104 passed / 215 skipped / 208 warnings·check_repo 통과. 전체 UE 36 state=Success(succeeded24 + warnings12, failed/notRun0), Locomotion 포함 통과. RenderEvidence는 NOT EXECUTED, GaspSmoke/실제 GASP 시각 통합은 Info skip. 등록 수 36 유지. 자세한 재현·인계는 pc-verify-wp13.md 끝 T13 절.

### 병합 시 반영 — T13

STATUS 병행 트랙 문안: `T13(WP-19c 오디오) 노티파이 발소리 코드·헤드리스 계약 검증 완료. footsteps.driver auto/distance/notify, Step/Land 단일 재생 요청·거리 중복 방지. 기존 일반 폰은 distance 유지, 등록 36. GASP 원본 폴리 비활성화는 설정 조회 훅만 제공; V-08b §5/19b 연결·V-15 청취 실검증 대기.`

WP-19 결과/19b 인계 문안: `T13은 UGolmokFootstepComponent::UsesNotifyDriver() BlueprintPure 조회 훅과 OnFootEvent 구독을 제공한다. 실제 GASP 폴리 경로를 확인한 뒤 원본 재생 차단 + NotifyFootEvent 단일 전달을 19b BP에서 연결해야 한다. auto는 native GASP 계열 폰 기준이며 이벤트가 없으면 거리로 폴백하지 않는다. ABP 로스터를 GASP 폰에서 진단할 때 distance를 명시한다.`

## 병합 기록 — T13 PR [#79](https://github.com/wooklym/golmok/pull/79) (2026-09-30, 오케스트레이터 세션)

**내용**: 위 "T13" 절과 같다. `footsteps.driver`(auto/distance/notify, 기본 auto) 엄격 파싱, `OnFootEvent` 구독(등록·해제·공급 컴포넌트 교체), Step/Land를 기존 표면·착지 재생 경로로 각각 한 번, 첫 이벤트 전부터 거리 스테퍼 정지, pause·photo·이전 폰 이벤트 무시, BlueprintPure `UsesNotifyDriver()`. 등록 수는 36으로 같다.

**병합 전 리뷰(Opus 5.5 ultracode 적대 검증 + 설계 리뷰, [R79](https://github.com/wooklym/golmok/pull/79#issuecomment-5908764323))**: (A) 0 · (B) 2 · (C) 6.
- 게이트(리눅스): ruff·format, pytest 1316 passed / 3 skipped(#77 위), check_repo, `diff --check` 통과, 등록 36. #78과 `merge-tree` 충돌 0(합친 트리 pytest 1353). UE 빌드·자동화 36 Success는 Astra 보고 수치다.
- 확인(결함 없음): ① 기본 폰 발소리 틱 경로가 main과 같다(공급 컴포넌트 없음 → 바인딩 즉시 반환, auto → distance). 틱과 이벤트가 같은 술어로 상호 배제되어 이중 재생 경로가 없다. `AddUObject` 약참조·`OnUnregister`/교체 시 해제로 댕글링 없음. #78 C8(착지 값은 틱에서만)과 충돌 없음(페이로드는 종류·좌우뿐). 새 단언이 각각 그럴듯한 결함을 잡는다. 레인·핫스팟 준수.
- (B) **R79-1 → Astra T15**(19b 착수 전): auto가 폰 클래스로 판정해 GASP 폰에 비GASP ABP가 돌면(모드 기본값 실패 폴백·`golmok.character manny`·19b 연결 전) 발소리가 영구히 무음이다. auto를 "GASP 폰 ∧ `GetMesh()` 애님 클래스가 GASP ABP(`RequiresGaspPawn`, 애님 클래스 키 캐시)"로 바꾼다. ① 영향 없음.
- (B) **R79-2**: 원본 GASP 발 폴리는 19b BP가 `footsteps.driver`와 무관하게 끈다(오케스트레이터 결정, D-019). (a) Claude 문서(WP-19 §13-3·§16·§17, 런북 §A5·§D)는 WP-19a-2 [#78](https://github.com/wooklym/golmok/pull/78)에서 고쳤다. (c) 헤더 주석·`pc-verify-wp13.md` 문안("진단용 조회, 억제 조건으로 쓰지 않는다")은 T15.
- (C): R79-3 C++ driver 파서 대소문자 구분(Python과 일치), R79-4 ① 경로 직접 단언·L_Dev 기본 폰 전제 제거, R79-5 HUD `drv=… ev=N`, R79-6 텔레포트 직후 가짜 노티파이·게임 스레드 가드, R79-7 헤더 전방 선언, R79-8 `OnUnregister` 스테퍼 리셋(기록만). R79-3·5는 T15 권장.
- 설계 리뷰: 이 PR은 채택, "첫 이벤트 전 거리 정지"도 채택. GASP 폰 + ABP 로스터의 무음은 수용하지 않고 애님 클래스 기준(R79-1)으로 바꾼다. N초 무이벤트 폴백은 19b 연결 누락을 가리고 늦은 노티파이와 겹칠 수 있어 기각. 품질 가설(노티파이가 발 접지와 더 잘 맞음)은 바뀌지 않고 V-15에서 검증한다. 새 D 번호 없음.

**병합**: 오케스트레이터 결정(D-019). #77 병합 뒤 base를 main으로 바꾸고, main(#77·#78 포함)을 이 브랜치에 병합한 뒤 이 커밋으로 반영했다. CI 초록이고 (A)가 없어 병합했다. 위 "병합 시 반영 — T13" 문안은 STATUS 병행 트랙 WP-13 행, WP-19 결과 23번, `astra-tasks.md` T13·T15에 옮겼다.


## T15 결과 — WP-19c auto 발소리 후속 (2026-09-30 KST)

배정: [이슈 #30 T15](https://github.com/wooklym/golmok/issues/30#issuecomment-5909415427). main `a92cad8` 기준 별도 `astra/wp-19c-footstep-followup`; T14와 독립이며 오디오 C++/시험/WP-13/런북만 변경했다.

- **R79-1**: auto는 native GASP 폰 AND 실제 소스 GetMesh 애님 클래스의 RequiresGaspPawn 계약이다. 약한 클래스 키/bool 캐시로 매 틱 파일 파싱을 피한다. 클래스 변경·재등록으로 갱신한다. GASP 폰+일반 ABP/폴백은 distance이며 시간 기반 무이벤트 폴백은 추가하지 않았다.
- **R79-2c**: 헤더/런북을 진단용 UsesNotifyDriver·19b 원본 발 폴리 무조건 억제 규칙으로 정정했다. 이 절이 위 T13 인계 문안의 폰 클래스 단독 auto 및 조건부 폴리 억제 가설을 대체한다. 실제 원본 억제는 아직 19b 미구현이다.
- **C3/4/5/6/7**: driver 대소문자 엄격 파싱/Notify 거절, 직접 생성 일반 폰의 100cm 거리 요청, 합성 이벤트의 명시 notify, auto 음성/테스트 ABP 계약 양성·캐시 갱신, drv/ev HUD, TimeDilation Photo 억제, 게임 스레드 가드 및 헤더 전방 선언. ev는 필터 전 유효 이벤트 수이며 재생 수가 아니다. C6 텔레포트/재초기화 가짜 이벤트 필터는 실제 경로 확인 뒤, C8 스테퍼 해제 리셋은 미변경이다.

검증: UE5.8.3 build 성공(7.83s, 엔진 C4996 경고), Audio 2 Success(경고1)/failed0/notRun0. 설치 테스트 ABP scoped 양성도 이번에 실행했다. pytest **1141 passed/217 skipped/208 warnings,50.79s**, ruff check/format114·check_repo 통과. T14의 교차 검사 8개는 별도 브랜치라 이 수치에 포함되지 않는다. 전체 UE는 **35 Success(23+경고12)/1 Fail/notRun0**: 기존 main #78 Animation.Config의 `Case.Text != FString(BaseConfig)`가 abp/ABP를 같다고 판단하는 변이 단언 실패다. Claude 레인으로 수정 요청했고 전체 게이트는 차단 상태다. 로컬 근거: tools/.venv/t15-{audio,full}-index.json 및 t15-build.txt/t15-pytest.txt. 등록 **36 유지**. 실제 GASP 에셋/원본 폴리/청취/GUI/패키지 출력은 NOT EXECUTED다.

### 병합 시 반영 — T15

- **astra-tasks T15/STATUS**: “T15 R79-1·2c 및 C3/4/5/6 일부/7 구현·Audio 헤드리스 검증 완료. auto는 native GASP AND 소스 애님 클래스 계약, 클래스 키 캐시. drv/ev 진단·엄격 driver 파싱. 등록36 유지, 실제 GASP 원본 폴리 억제·V-15 청취는 19b 대기.” 전체 UE 게이트 차단이 남으면 해소 전 완료 판정에 포함하지 않는다.
- **WP-19 19b 인계**: “UsesNotifyDriver는 진단 전용, 원본 GASP 발 폴리 억제 조건으로 사용하지 않는다. 19b는 driver와 무관하게 원본 발 폴리를 끄고 Step/Land만 NotifyFootEvent로 단일 전달한다. auto는 native GASP 폰과 실제 GetMesh 소스 애님 클래스 RequiresGaspPawn 둘 다 충족할 때 notify, 그 밖은 distance. 무이벤트 시간 폴백 없음.”

## 병합 기록 — T15 PR [#82](https://github.com/wooklym/golmok/pull/82) (2026-09-30, 오케스트레이터 세션)

**내용**: 위 "T15" 절과 같다. R79-1(auto = 네이티브 GASP 폰 ∧ `GetMesh()` 소스 애님이 `RequiresGaspPawn`, 애님 클래스 약참조 키 캐시·`OnRegister` 리셋, 시간 초과 폴백 없음), R79-2(c)(`UsesNotifyDriver()`는 진단용, 원본 폴리 억제 조건 아님), (C) R79-3 driver 대소문자 구분·R79-4 ① 동적 단언·R79-5 HUD `drv=<실효>(<설정>) ev=<수>`·R79-6 게임 스레드 가드·R79-7 전방 선언. 등록 수는 36으로 같다.

**병합 전 리뷰(Opus 5.5 ultracode 적대 검증 + 짧은 설계 리뷰, [R82](https://github.com/wooklym/golmok/pull/82#issuecomment-5910685446))**: (A) 0 · (B) 0 · (C) 6.
- 게이트(리눅스): ruff, format 112, pytest 1355 passed / 3 skipped, check_repo, `diff --check`, 등록 36, CI 10/10. main(#83)·#80·#81과 충돌 0, 넷을 합친 트리 pytest 1403. UE 빌드·Audio 2 Success는 Astra 보고이며, 전체 35/1의 원인이던 main `Animation.Config` 단언은 [#83](https://github.com/wooklym/golmok/pull/83)으로 해소됐다(PC 전체 36 재실행 대기).
- 확인(결함 없음): ① 기본 폰 발소리 경로가 main과 바이트 단위로 같음, 틱·이벤트가 같은 술어·캐시로 상호 배제(이중 재생 없음, GASP↔ABP 전환 때 중복 한 보 없음), 캐시가 로스터 교체·preview·`SetAnimInstanceClass`·BP 재컴파일·GC를 따라감, 디스크 읽기는 클래스가 바뀔 때 1회, 컴파일 위험 낮음, 레인 준수.
- (C → 선택 과제 T17): R82-1 캐시 테스트가 캐시 존재·non-null 교체 무효화를 증명하지 못함, R82-2 캐시 키에 설정 세대 없음(실사용 영향 없음), R82-3 양성 블록을 건너뛸 때 마지막 Info 과장, R82-4 폰 클래스 조건·`ev` 필터 포함 미단언, R82-6(기존) 오디오 JSON 키 대소문자 C++/Python 불일치. R82-5(문서)는 이 커밋에서 반영(D-021 진행 기록 (2) 문구, WP-19 결과 23번 완료형).
- 설계 리뷰: 품질 가설 변화 없음, 새 D 번호 없음. GASP 폰에 ABP 로스터를 적용하면 무음이 아니라 거리 발소리가 나서 R79의 품질 결함이 해소된다.

**병합**: 오케스트레이터 결정(D-019). main(#83·#80 포함)을 병합한 뒤 이 커밋으로 반영했다. 위 "병합 시 반영 — T15"의 "전체 UE 게이트 차단"은 #83으로 원인이 해소되어 PC 전체 36 재실행 대기로 옮겼다. STATUS 병행 트랙 WP-13 행, WP-19 결과 23번, `astra-tasks.md` T15·T17, DECISIONS D-021 진행 기록에 반영했다.


## T17 결과 — 오디오 캐시·키 검사 후속 (2026-09-30 KST)

배정: [현재 큐 T17](https://github.com/wooklym/golmok/issues/30#issuecomment-5911002600), 리뷰 [R82](https://github.com/wooklym/golmok/pull/82#issuecomment-5910685446). main `d414034`에서 독립 `astra/wp-19c-footstep-followup2`. T16 리뷰 (A)/(B) 0·병합 진행을 확인하고 해당 브랜치 push 정지를 유지했다.

- **R82-1·2**: 캐시 키에 GetModeSourceGeneration을 추가했다. 테스트 전용 평가 누적 계수로 반복 query/event/Tick/HUD에서 1회 평가를 확인하고, null이 아닌 UAnimInstance↔설치 ABP 교체를 검사한다. scoped 설정 진입·복귀에 Reregister 우회를 없앴다. 디스크 파일 감시나 시간 기반 무이벤트 폴백은 추가하지 않았다.
- **R82-3·4**: 양성 fixture 실행 여부를 Info에 구분한다. 일반 폰+GASP 계약 애님은 notify가 아니며, pause에 필터된 이벤트도 ev 증가·재생 요청 불변임을 단언한다.
- **R82-6**: UE JSON 조회 전에 객체별 알려진 필드의 case alias를 ToView().Equals로 거절한다. 루트/에셋/상태/발소리/개별 보폭 변이 8개와 실패 후 설정 보존을 검사했다. 무관한 확장 키의 기존 허용·동적 id는 유지한다. Python의 모든 키/참조/값 검증과 완전 일치를 주장하지 않는다. R82-5 문서는 이미 병합 세션이 처리했다.

검증: UE5.8.3 빌드 성공(20.85s), Audio2 Success(경고1)/failed0/notRun0, 양성 cache/class/generation/HUD fixture EXECUTED. 전체 UE **36 Success(24+경고12)/failed0/notRun0**, Python **1188 passed/218 skipped/208 warnings,72.18s**, ruff check/format114·check_repo·diff 통과. T16과 독립 main 기준이므로 T16 신규 검사3개는 이 수치에 포함하지 않는다. GaspSmoke 설치 미충족·RenderEvidence NOT EXECUTED를 실제 성공으로 세지 않는다. 로컬 근거: tools/.venv/t17-{audio,full}-index.json 및 t17-build.txt/t17-pytest.txt. 오디오 레인만 변경, 등록36 유지. 공유 문서·animation.json·characters.json·훅·핫스팟·음원·라이선스 변경 없음. 실제 GASP/GUI/청취는 NOT EXECUTED.

### 병합 시 반영 — T17

STATUS/astra-tasks 문안: “선택 T17 R82-1/2/3/4/6 완료: 클래스+설정 세대 캐시, 평가 계수·nonnull 교체·폰 조건·필터 이벤트 회귀, 조건부 NOT EXECUTED, 알려진 오디오 JSON 키 case alias 거부. 등록36 유지. 19b/V-15 실제 원본 폴리·청취 검증은 별도.”

## 병합 기록 — T17 PR [#85](https://github.com/wooklym/golmok/pull/85) (2026-09-30, 오케스트레이터 세션)

**내용**: 위 "T17" 절과 같다. 선택 과제 R82-1·2·3·4·6(클래스 + 설정 세대 캐시, 테스트 전용 평가 계수·non-null 클래스 교체·폰 조건·필터 이벤트 `ev` 회귀, 조건부 NOT EXECUTED, 알려진 오디오 JSON 키의 대소문자 변형 거부). 등록 수는 36으로 같고, Astra 전체 UE 36 Success(양성 fixture EXECUTED)다.

**병합 전 리뷰(Opus 5.5 ultracode 적대 검증, [R85](https://github.com/wooklym/golmok/pull/85#issuecomment-5913445157))**: (A) 0 · (B) 0 · (C) 4. 게이트(리눅스): ruff, format 112, pytest 1403 passed / 3 skipped, check_repo, `diff --check`, 등록 36, CI 10/10; main(#84)과 충돌 0, 합친 트리 pytest 1406. UE 빌드·전체 36 Success는 Astra 보고다. 확인(결함 없음): R82-1·2·3·4·6 모두 해결(평가 계수 정확히 +1, 클래스 ∧ 설정 세대 캐시 키, 변이 모델에서 캐시·키·세대·폰 조건·`ev` 순서 변이 모두 검출), ① 기본 폰 경로가 main과 같음, 캐시 무효화 누락 없음, 실제 `audio.json`·레거시 fixture 무영향, 레인 준수. (C → 선택): R85-1 KeyCase·캐시 리셋 개별 커버리지 공백 3(ambience 단독 변이, 대소문자 중복 키 고정, `OnRegister` 리셋), R85-2 `stride_scale_by_mesh` 오류 안내, R85-3 남은 C++/Python 비대칭 무해 기록. R85-4는 이 커밋에서 처리. 설계 리뷰 불필요(품질 가설·D-021 (2) 불변).

**병합**: 오케스트레이터 결정(D-019). main(#84 포함)을 병합한 뒤 이 커밋으로 반영했다. 위 "병합 시 반영 — T17" 문안은 STATUS 병행 트랙 WP-13 행과 `astra-tasks.md` T17에 옮겼다. 남은 (C) R85-1~3은 선택으로 이월해 다음 오디오 레인 push(19b 뒤 원본 폴리·청취 후속 등)에 함께 싣는다. 19b를 막지 않는다. PC는 main에서 UE 전체 36을 재실행할 때 Footstep 로그의 `EXECUTED auto positive cache/class/generation/HUD` Info를 확인한다(R85-4).


## T19 결과 — 키 검사별 회귀와 재등록 캐시 (2026-10-04 KST)

배정: [이슈 #30 T19](https://github.com/wooklym/golmok/issues/30#issuecomment-5913613213), R85 (C) 후속. main `c3f6541`에서 별도 `astra/wp-19c-footstep-followup3`; T18 PR과 독립이다.

- **R85-1a**: DOM에서 ambience 또는 crossfade_seconds_by_state 한 객체의 outdoor_day만 OUTDOOR_DAY로 바꾸고 실패와 정확한 객체 경로를 검사한다. 다른 객체의 키 오류가 해당 검사의 누락을 가리지 않는다.
- **R85-1b**: footsteps에 정확히 `"driver":"auto","Driver":"notify"`를 넣은 원문 JSON을 TestFalse로 고정했다. UE5.8.3 실제 실행에서 거절됐다. 이 결과는 해당 순서의 입력에 대한 것이며 모든 중복 키 조합을 보장하지 않는다.
- **R85-1c**: auto 양성에서 ReregisterComponent 후 조회가 참이고 RequiresGaspPawn 평가 계수가 정확히 +1 증가하는지 단언한다.
- **R85-2**: stride_scale_by_mesh는 KeyCase 목록에서 제외했다. Stride_Scale_By_Mesh도 기존 HasField 검사로 거절하고 `use stride_cm_by_character` 안내를 내는지 DOM 회귀로 확인한다.
- **R85-3**: Python 알려진 키 alias 검사는 선택 이월했다. 기존 C++/Python 비대칭과 동적 id/값의 대소문자 규칙은 이번 범위가 아니다.

UE build·Audio2 Success(경고1)/failed0/notRun0 통과. 최종 build6.80s 성공, 전체 **36 Success(24+경고12)/failed0/notRun0**, pytest **1286 passed/218 skipped/208 warnings,82.44s**, ruff check/format114·check_repo·diff 통과. GaspSmoke 설치 미충족·RenderEvidence NOT EXECUTED는 실제 검증 성공이 아니다. 근거: tools/.venv/t19-{audio,full}-index.json, t19-build.txt/t19-pytest.txt. 등록36 유지. 실제 GASP·GUI·원본 폴리·청취는 NOT EXECUTED. 오디오 레인만 변경하고 설정/훅/핫스팟/공유 문서/음원·라이선스는 변경하지 않았다.

### 병합 시 반영 — T19

STATUS/astra-tasks 문안: “선택 T19 R85-1a/b/c·2 완료: 객체별 DOM case 변이, driver/Driver 중복 거절 UE5.8.3 회귀, 재등록 평가 계수+1, 폐기된 stride_scale_by_mesh의 교체 안내 보존. 등록36, R85-3 Python alias 검사 선택 이월. 실제 GASP/청취는 19b/V-15 대기.”

## 병합 기록 — T19 PR [#92](https://github.com/wooklym/golmok/pull/92) (2026-10-04, 오케스트레이터 세션)

**내용**: 위 "T19" 절과 같다. 선택 과제 R85-1a/b/c·2(객체별 DOM 대소문자 변이로 `Ambience.KeyCase`·`Durations.KeyCase` 개별 검출, `"driver":"auto","Driver":"notify"` 중복 거절 고정, `ReregisterComponent` 뒤 평가 계수 +1, 폐기 키 `stride_scale_by_mesh` 철자 변형의 `use stride_cm_by_character` 안내 보존). 등록 수는 36으로 같고, Astra 전체 UE 36 Success다.

**병합 전 리뷰(Opus 5.5 ultracode 적대 검증, [R92](https://github.com/wooklym/golmok/pull/92#issuecomment-5977301171))**: (A) 0 · (B) 0 · (C) 3. 게이트(리눅스): ruff, format 112, pytest 1501 passed / 3 skipped, check_repo, `diff --check`, 등록 36, CI 10/10; base `c3f6541` = 당시 main(충돌 0). UE 빌드·전체 36 Success는 Astra 보고다. 확인(결함 없음): R85-1a/b/c·2 모두 해결 — 파서 KeyCase 구조 모델(CRLF 실제 `audio.json`)의 변이 6개(각 KeyCase 삭제, driver KeyCase 제외, FindOrAdd식 엔진, `OnRegister` 리셋 삭제, R85-2 되돌림)를 모두 검출, 상태·순서 독립, 레인 준수, 런북 `pc-verify-wp13.md` :234·:257 문구와 일치. (C → 선택): R92-1 R85-1c 양성 블록 실행 증거(EXECUTED Info에 `reregister`, 결과 절 한 줄, 런북 헤드리스 범위), R92-2 중복 driver 거절 경로를 정확한 오류 문구로 고정하고 메커니즘 기록, R92-3 반복 라벨에 객체 이름. 설계 리뷰 불필요(품질 가설·D-021 (2) 불변).

**병합**: 오케스트레이터 결정(D-019). 위 "병합 시 반영 — T19" 문안은 STATUS 병행 트랙 WP-13 행과 `astra-tasks.md` T19에 옮겼다. R85-3(Python alias 검사)과 R92-1~3은 선택으로 이월해 다음 오디오 레인 push(19b 뒤 원본 폴리·청취 후속 등)에 함께 싣는다. 19b를 막지 않는다. PC는 main에서 UE 전체 36을 재실행할 때 Footstep 로그의 양성 fixture `EXECUTED` Info를 확인한다(R85-4, R92-1).

## T22 — 오디오 키 별칭 검사·실행 증거 (2026-10-04 KST)

배정: [이슈 #30 T22](https://github.com/wooklym/golmok/issues/30#issuecomment-5978814306). main `f1535ac`(#95 큐 문서 포함)에서 새 `astra/wp-19c-footstep-followup4`로 진행했다.

- R85-3: `audio_pure.py`는 C++ KeyCase와 같은 알려진 키를 root/asset/ambience/crossfade durations/footsteps/캐릭터 보폭 쌍에서 검사한다. 오류는 실제 별칭 경로와 기대 철자를 가리킨다. 무관한 확장 키·동적 id 및 기존 검증 규칙은 유지한다. 필수/선택 키의 단독 별칭·정상 키와 공존한 별칭, 확장 키/동적 id 보존, 중복 driver 양쪽 순서를 pytest로 검사한다.
- R92-1: 양성 fixture Info에 `reregister`를 넣고 런북 헤드리스 범위에 재등록 뒤 재평가 1회를 명시했다. 최종 index의 실행 증거는 아래 기록한다.
- R92-2: `"driver":"auto","Driver":"notify"` 거절 사유를 `audio.json footsteps.Driver: expected driver`로 고정했다. 역순 `"Driver":"notify","driver":"auto"`는 성공하며 최종 driver=auto다. 로컬 UE5.8.3의 JsonObject.cpp SetField는 Values.Add를 사용하고, SharedString.h의 키 동등 비교는 IgnoreCase다. TMap에서 뒤 키/값이 앞 항목을 교체하여 DOM에는 뒤 철자가 남는다. Python json/dict는 두 철자를 모두 보존하므로 양쪽 순서 모두 별칭을 거절한다. UE의 파싱 전 중복 키 검출 기능을 추가한 것은 아니다.
- R92-3: 격리 변이의 경로 단언 라벨에 객체 이름을 추가했다.

검증: UE5.8.3 build54.85s 성공, 전체 **36 Success(24+경고12)/failed0/notRun0,192.94s**, Audio2 포함. Python **1307 passed/218 skipped/208 warnings,85.65s**(+21), ruff check/format114 및 audio_pure 개별 format/check·check_repo·diff 통과. index의 Footstep Info: `EXECUTED auto positive cache/class/generation/reregister/HUD and ordinary-pawn conjunction`. 실제 GASP 원본/청취·GUI·RenderEvidence는 NOT EXECUTED. 로컬 근거: tools/.venv/t22-build.txt, t22-pytest.txt, t22-full-index.json.

### 병합 시 반영 — T22

STATUS/astra-tasks 문안: “T22 R92-1~3·R85-3 완료: 재등록 양성 실행 증거·런북, 중복 driver 정확한 거절 사유와 UE 역순 auto 수락 회귀, 객체별 진단 라벨, Python 알려진 키 별칭 검사(확장/동적 키 기존 규칙 유지). 등록36 유지. 실제 GASP 원본 폴리·청취는 19b/V-15 대기.”

## 병합 기록 — T22 PR [#101](https://github.com/wooklym/golmok/pull/101) (2026-10-04, 오케스트레이터 세션)

**내용**: 위 "T22" 절과 같다. 선택 과제 R85-3(Python `audio_pure.py`의 알려진 키 별칭 검사 — C++ `KeyCase`와 같은 객체 6곳·이름 40개, 확장 키·동적 id 규칙 유지, pytest +21)과 R92-1~3(재등록 양성 실행 증거·런북 범위, 중복 driver 정확한 거절 문구와 UE 역순 auto 수락 회귀, 객체별 진단 라벨). 등록 수는 36으로 같고, Astra 전체 UE 36 Success(Audio 2 포함)다.

**병합 전 리뷰(Opus 5.5 ultracode 적대 검증, [R101](https://github.com/wooklym/golmok/pull/101#issuecomment-5979548775))**: (A) 0 · (B) 0 · (C) 3. 게이트(리눅스): ruff, format 112, pytest 1522 passed / 3 skipped(+21), check_repo, `diff --check`, 등록 36, CI 10/10; base `f1535ac`(main merge-tree 충돌 0). UE 빌드·전체 36 Success는 Astra 보고다. 확인(결함 없음): C++ `KeyCase` 목록과 Python 목록이 객체 6개·이름 40개·순서까지 같고 `stride_scale_by_mesh`는 빠짐(R85-2), `audio_pure.py` 변이 52개 중 호출 단위 변이는 모두 검출, Python 중복 키 처리가 UE보다 엄격(CI 통과 파일이 UE에서 다른 값으로 읽히지 않음), R92-1~3 해결, 레인 준수. (C → 선택): R101-1 역순 중복 driver pytest가 실제 역순을 만들지 못함(`del` 뒤 순서 단언), R101-2 이름 단위 C++ 대응 패리티 테스트(모듈 상수 + `GolmokAudioConfig.cpp` 6개 목록 대조, 선례 `test_ue_config_animation.py`·`test_ue_config_photo.py`), R101-3 폐기 키 검사의 대소문자 무시. 설계 리뷰 불필요(검증 엄격화·테스트·문서뿐).

**병합**: 오케스트레이터 결정(D-019). 최신 main을 합친 뒤 이 커밋으로 반영했다. 위 "병합 시 반영 — T22" 문안은 STATUS 병행 트랙 WP-13 행과 `astra-tasks.md` T22에 옮겼다. R101-1~3은 선택으로 이월해 다음 오디오 레인 push(19b 뒤 원본 폴리·청취 후속 등)에 함께 싣는다. 19b를 막지 않는다.


## T24 — WP-16a 빗소리 레이어 (2026-10-05 KST)

배정: [이슈 #30 T24](https://github.com/wooklym/golmok/issues/30#issuecomment-5981293651), 계약 확정 [5980906355](https://github.com/wooklym/golmok/issues/30#issuecomment-5980906355). main `cb221aa`에서 `astra/wp-13-rain-layer`로 시작했다. 기존 WP-13/V-10 🟢와 별개로 **T24 🟡 코드·헤드리스 검증, 빗소리 청취/패키지 대기**다.

- 기존 세 환경음 상태·두 크로스페이드 슬롯을 유지하고 독립 `RainChannel`을 추가했다. BeginPlay와 매 Audio 틱에서 Weather `Get`→`IsEnabled`→`GetRainIntensity`를 읽는다. null/disabled는 0이며 이벤트나 목표 강도로 대체하지 않는다. Weather 레인 수정·추가 API·틱 의존 순서 변경 없음(최대 1프레임 지연 수용). `fx off`는 날씨 자체를 끄는 API가 아니므로 소리는 유지한다.
- `audio.json` 선택 `rain` 절: 루프 자산 ID·2~32점 선형 gain 곡선·실내 감쇠. 처음 `[0,0]`, 마지막 강수량 1, 강수량 엄격 증가·유한 0~1·루프 참조를 C++/Python이 검사한다. 절이 없는 구 manifest는 빗소리 없이 동작한다. 강수 0/0.3/1에 gain 0/0.35/0.8, 실내 ×0.35는 승인된 **초기 청취 가설**이고 최종 품질 합격이 아니다.
- 문간에서 갑자기 볼륨이 떨어지지 않도록 실내 배율에 기존 목적 상태 fade 시간과 진폭 S-curve를 재사용한다(초기 바인딩은 현재 실내 상태를 즉시 반영, 이후 변화는 fade). 원본 SoundWave gain(0.5)은 임포트에서, 곡선 × 실내 × master × PhotoGain은 채널에서 각각 한 번 적용한다. 포토 정지 중에도 Audio의 실시간 envelope가 진행하며 `IsFrozen`으로 멈추지 않는다. HUD `rain`은 실제 강수량, `rain_gain`은 채널 배율이다.
- `make_placeholder_audio.py`를 그대로 사용해 seed 1307·4 s·mono PCM16/48 kHz 합성 루프 384,044 bytes를 생성했다. 자산/출처/크레딧은 기존 JSON 단일 소스와 `ATTRIBUTION.md`·txt·런타임 credits 경로를 그대로 쓴다. 새 외부 소스·라이선스·저역 통과·wet 발소리 없음. 생성 `.uasset`은 로컬 검증용, WAV만 LFS 추적한다.
- R101 선택 3건: driver 역순 검사 전에 기존 driver를 제거하고 실제 마지막 키 순서를 단언, Python AST `key_case` 목록과 C++ `KeyCase` 목록의 **이름 집합·중복 수** 대조(새 rain 포함 7개 목록), 폐기된 `stride_scale_by_mesh`의 철자 변형도 Python에서 거절한다.
- wp13 런북 §6과 현재 패키지 재현 명령을 `$pkg`/`GOLMOK_PKG_DIR`로 변경하고 명시 `-OutDir`/실제 `Package output` 대조를 적었다. 당시 경로·7개 쿡 증거는 역사적 실행 기록으로 보존한다. §7-1 급정지 문구에 −80 dBFS 기준 레벨 게이트·수 LSB 무음·`--silence-floor 0` 이전 방식, §9에 빗소리 PC 카드와 8개 임포트/쿡 기준을 추가했다.

### 검증 — T24

- Python 전체: **1483 passed / 272 skipped / 208 warnings**, 90.30 s(Windows g++ 교차검증 등 skip). 설정·생성기·임포터 표적 134 passed / 1 skipped. ruff check·format(119 files)·check_repo·diff check 통과.
- UE5.8.3 빌드: 첫 main 동기화 포함 168.25 s, 최종 증분 9.89 s 성공. 엔진 `Character.h`의 C4996만 관찰했고 프로젝트 컴파일 오류 없음.
- 실제 UE 헤드리스 WAV 임포트/재임포트 **8+8**, loop/volume 8개 단언, `T24_IMPORT_VERIFIED_8_REIMPORT_8`(로컬 `Saved/Logs/Golmok-backup-2026.10.04-15.20.59.log`), commandlet **0 errors / 0 warnings**.
- UE 전체 **39 Success (succeeded 26 + succeededWithWarnings 13), failed 0 / notRun 0, 195.57 s**. Audio 2개 모두 Success이며 새 rain·save·photo EXECUTED Info를 확인했다(로컬 `tools/.venv/t24-full-index.json`). 기존 Audio StateMachine에 null/disabled 경로·강수 상승/하강·clear·늦은 공급자/실내 바인딩·기존 베드 보존·실제 독립 GUID 세이브 슬롯 복원·master/mute·Photo maintain 두 pause 모드·GamePause mute 페이드 검사를 추가했다. 등록은 **39 유지**(WP-16a가 +3). 컴포넌트 논리 검증과 `-nosound` 결과를 청취로 기록하지 않는다.
- **미실행**: 실제 오디오 장치 루프백·주관적 밸런스·패키지 쿡/재생. V-16 이후 플레이스홀더 오디오 PC 카드([wp13 §9](../runbooks/pc-verify-wp13.md))는 레벨·타이밍·클릭·mute/Photo·복원만 기록하며 밸런스·마스킹은 판정하지 않는다. 곡선·실내 배율·발소리 headroom은 빗소리다운 소스(CC0 채택 또는 합성 변형) 뒤 C-08 청취에서 평가한다. 소유자 결정 필요 없음, Opus 코드/품질 가설 리뷰 요청.
- 겹침: 시작 시 열린 #113 `claude/wp16a-followups`는 Weather/Save 및 그 테스트·wp16 런북으로 직접 겹치는 수정 파일이 없다. 핫스팟/공유 문서/등록부 변경 없음.

### 병합 시 반영 — T24

STATUS/astra-tasks 문안: “T24 빗소리 레이어 완료: 낮/밤/실내 두 슬롯 유지 + 별도 rain 채널, 실제 강수 조회·실내 S-curve 감쇠·master/PhotoGain 공유, JSON 곡선/합성 루프·크레딧, null/disabled·세이브 복원·포토 회귀. 등록39 유지. R101 선택3건과 wp13 패키지 경로/무음 바닥 문구 포함. T24 🟡 청취·패키지 검증 대기(V-16 이후 오디오 카드), 기존 WP-13/V-10 🟢 유지.”

DECISIONS D-015 진행 문안: “T24 오디오가 WP-16a 실제 강수를 별도 레이어로 소비한다. gain 곡선 0→0 / 0.3→0.35 / 1→0.8와 실내 ×0.35는 초기 청취 가설이며 최종은 PC/Opus 검토. 실내 전환은 기존 목적 상태 fade 시간의 S-curve를 재사용한다. 새 음원 출처 채택 없음, 합성 플레이스홀더. 되돌리기: audio.json의 rain 절 제거(루프/크레딧까지 제거하려면 assets.rain·생성 파일도 함께 정리).”

## 병합 기록 — T24 PR [#114](https://github.com/wooklym/golmok/pull/114) (2026-10-04, 오케스트레이터 세션)

**내용**: 위 "T24" 절과 같다. 기존 낮/밤/실내 두 크로스페이드 슬롯 위에 독립 rain 채널을 더했다. Audio 틱이 실제 `GetRainIntensity()`(없음·꺼짐 0)를 읽고, `audio.json` `rain` 곡선 0→0 / 0.3→0.35 / 1→0.8과 실내 ×0.35(목적 상태 fade 1.0/2.0 s S-curve)를 적용하며, master·PhotoGain·mute는 베드와 공유한다. HUD에 `rain`·`rain_gain`, 합성 루프 `rain.wav`(seed 1307)·크레딧, null/disabled·세이브 즉시 복원·포토 회귀를 넣었다. R101 (C) 3건과 wp13 런북 `$pkg`·−80 dBFS 문구도 함께다. 등록 39 유지, Astra 전체 UE 39 Success(Audio 2 포함)·임포트 8+8.

**병합 전 리뷰(Opus 5.5 ultracode 적대 검증 + Opus 디자인 리뷰, [R114](https://github.com/wooklym/golmok/pull/114#issuecomment-5981980619))**: (A) 0 · (B) 1 · (C) 9. 게이트(리눅스): ruff, format 117, pytest 1752 passed / 3 skipped(+32), check_repo, `diff --check`, 등록 39, CI 10/10; base `cb221aa`(main merge-tree 충돌 0, #113과 공통 파일 없음). UE 빌드·전체 39 Success·임포트 8+8은 Astra 보고다. 확인(결함 없음): null/꺼짐 0·NaN clamp, 첫 바인딩 즉시·이후 목적 상태 fade, 베드와 같은 master/PhotoGain/mute 식, 볼륨 0 루프 + PlayWhenSilent(재시작 팝 없음)·Deinitialize 정리, 유니티 이름 공간, 원자적 파서와 C++/Python 규칙·KeyCase 7목록 44키 일치, `rain.wav` LFS·seed 1307 재생성 바이트 동일·크레딧 일치, R101-1~3·런북 `$pkg`/−80 dBFS. **디자인**: 곡선·실내 ×0.35·문간 1.0/2.0 s를 초기값으로 채택한다. 예측(V-10b master submix 기준)은 강한 비에서 낮 합 +2.1 dB·밤 +3.8 dB·실내 +1.0 dB, 발소리 피크 여유 18.5 → 16.4 dB다. (B) R114-1: 플레이스홀더가 베드와 같은 저역 노이즈라 밸런스·가림을 판정할 수 없다 → 런북 §9-3·T24 절 문구, 빗소리다운 소스 뒤 C-08. (C) R114-2~10: 검증 규칙 독립 사례(변이 생존 5), 곡선 평가 g++ 교차검증·gain 비감소 규칙, PIE 가설 수치 하드코딩, disabled 단언·null 가드, 매 틱 SetVolumeMultiplier, 런북 §5 참조·문장, 강제 상태 안내, 즉시 경로 평활, C-08 청취 가설.

**병합**: 오케스트레이터 결정(D-019). 이 커밋으로 반영했다(base가 main `cb221aa`라 합칠 것 없음). 위 "병합 시 반영 — T24" 문안은 STATUS 병행 트랙 WP-13 행, `astra-tasks.md` T24, DECISIONS D-015 진행에 옮겼다. V-16 카드(`pc-verify-wp16a.md`)의 "빗소리 없음 정상" 문구는 이 병합으로 맞지 않게 되어 같은 커밋에서 고쳤다. R114-1 (B)와 (C) R114-2~9는 Astra **T25**로 배정한다(R114-10은 C-08 청취 가설). PC 청취·패키지는 V-16 뒤 런북 §9 카드에서 한다.


## T25 — 빗소리 합성 변형·R114 후속 (2026-10-05 KST)

배정: [이슈 #30 T25](https://github.com/wooklym/golmok/issues/30#issuecomment-5982046162), [R114](https://github.com/wooklym/golmok/pull/114#issuecomment-5981980619). main `46d07cb`에서 `astra/wp-13-rain-followup`로 시작했다.

- 필수 R114-1: T24/런북 §9-3의 플레이스홀더 카드는 레벨·타이밍·클릭·mute/Photo·복원만 기록한다. 밸런스·마스킹 판정은 제외하고, 곡선·실내 배율·발소리 여유는 빗소리다운 소스 뒤 C-08 청취로 남겼다.
- 권장 합성 변형: Python 전용 자산 필드 `synthesis`(생략/`default`, `rain`)를 추가했다. `rain`은 자체 생성 루프에만 허용하며 채택 음원에서는 남아 있어도 무시한다. 런타임·등록부 변경 없음. 기존 7개 WAV 바이트 유지, rain만 seed 1307로 재생성(LFS), 크레딧 동기화. 주기적 FFT 1–8 kHz 노이즈에 4초당 12개의 15–40 ms Hann 과도음을 더한다. 재현 가능한 검사용 질감이며 현장 녹음·청취 합격이 아니다.
- 선택 R114-7/8/9: `$pkg` 정의 §5 참조·과거 실행 문장 정정, 실제 포털로 rain 실내 감쇠 확인(ForceState는 베드만), 세이브/instant/첫 바인딩의 즉시 gain 점프를 기대 동작으로 문서화했다. 선택 R114-2~6은 이번 범위에 포함하지 않았다.

### 검증 — T25

- `audio_analysis rain.wav --check`: 통과, peak −14.0 dBFS, RMS −25.5 dBFS, click z 4.0, clipping/급정지 0. 전력 가중 스펙트럼 중심 4,185.0 Hz(낮 베드 864.8 Hz), 1–8 kHz 전력 비율 >99.99%. 최종 WAV SHA-256 `02c8022adca514b56986bc03fd4f70d9582c0524460393b0953504db959cd9b7`.
- pytest에 seed 0/13/1307/uint32 최댓값의 결정성·대역 전력 >99%·중심 2.5–6 kHz 및 베드의 3배 초과·3회 반복 루프의 `--check`를 고정했다. 잘못된 합성 필드의 쓰기 전 거부, 채택 음원 보존, 실제 생성 경로의 rain 선택도 검사한다.
- 로컬 전체 Python **1494 passed / 272 skipped / 208 warnings**(81.66 s), ruff check/format, UE Python 명시 lint, check_repo, diff --check 통과. 플랫폼/의존성 skip은 실행 성공으로 세지 않았다.
- 실제 UE 헤드리스 임포트/재임포트 **8+8**, loop/volume 검증, `T25_IMPORT_VERIFIED_8_REIMPORT_8`, **0 errors / 0 warnings**. C++ 변경 없음으로 빌드·전체 UE 자동화는 이번에 재실행하지 않았다(등록39 유지). T24의 전체39 통과는 이전 결과다.
- 미실행: 실제 장치 출력·루프백·패키지 쿡/재생·주관적 빗소리/밸런스/마스킹. C-08 및 V-16 뒤 오디오 카드에서 확인한다. 새 출처 채택/소유자 결정 없음. Opus ultracode 코드 리뷰와 합성 질감/평가 범위의 Opus 품질 리뷰 요청.

### 병합 시 반영 — T25

STATUS/astra-tasks 문안: “T25 R114 후속 완료: 필수 플레이스홀더 검증 범위 정정, Python 전용 합성 선택·1–8 kHz rain 질감/크레딧, seed·대역·반복 루프 파형 회귀, 실제 UE 임포트 8+8(오류0). 기존 7 WAV·런타임·등록39 유지. R114-7/8/9 문서 반영, 선택2~6 미포함. C-08 청취·V-16 뒤 출력/패키지는 대기.”

DECISIONS D-015 진행 문안: “T25는 베드와 구별되는 합성 rain 질감을 검사용으로 추가했다. 스펙트럼/클릭 검사는 음질 합격이 아니며 곡선·실내 ×0.35·발소리 여유의 최종 판단은 C-08 청취다. 플레이스홀더 PC 카드는 레벨·타이밍·클릭·mute/Photo·복원만 기록한다. 새 라이선스/소스 채택 없음.”

## 병합 기록 — T25 PR [#115](https://github.com/wooklym/golmok/pull/115) (2026-10-04, 오케스트레이터 세션)

**병합 전 리뷰(Opus 5.5 ultracode 적대 검증 + Opus 디자인 리뷰, [R115](https://github.com/wooklym/golmok/pull/115#issuecomment-5982789631))**: (A) 0 · (B) 1 · (C) 4.
- 게이트(리눅스): ruff, format 117, pytest 1763 passed / 3 skipped(+11), check_repo, `diff --check`, 등록 39, CI 10/10; base `46d07cb`(= main, merge-tree 충돌 0).
- UE 임포트 8+8은 Astra 보고다. C++ 변경이 없어 빌드·자동화는 재실행하지 않았다.

확인(결함 없음):
- C++ 파서가 `synthesis`를 `seed`·`source`처럼 확장 키로 보존한다(KeyCase 자산 11개 이름과 대소문자 충돌 없음, 패리티 7목록 44키 불변).
- `changes`의 en dash는 UTF-8로 읽힌다(비 ASCII `characters.json` 선례).
- 검증기의 타입·값·루프 규칙과 채택 음원 비활성이 맞다.
- WAV 8개를 재생성한 sha256이 포인터 oid와 같다. 기존 7개는 불변이고, rain은 `02c8022a…` 384,044 bytes이며 LFS 서버 객체와 바이트가 같다.
- 크레딧이 생성기 출력과 같다.
- `--check` 통과: z 4.0, 이음매 계단 = 차분 중앙값의 0.11배, DC 0, 루프 안 주기성 없음.
- 문서 수치(중심 4185.0/864.8 Hz, 1–8 kHz 99.99998%)가 재현된다.
- R114-1/7/8/9가 반영됐다.

**디자인**: 합성 rain을 베드와 구별되는 층으로 채택한다. 약한 비가 낮 베드 대비 K-가중 −5.0 dB라 따로 들린다.
- 같은 RMS에서 K-가중 +3.5 dB·A-가중 +4.3 dB 크게 들린다.
- 그래서 V-10b 기준 강한 비는 RMS로 낮 베드 −1.4 dB지만 체감은 +2.2 dB, 밤은 +5.8 dB다. 실내 강한 비는 룸톤 −1.6 dB다(R114 RMS 예측 −2.1/−5.9).
- rain 자산 gain을 0.3으로 내리면 곡선·실내 배율을 그대로 둔 채 R114 관계가 돌아온다 → C-08 비교.
- 발소리 플레이스홀더 에너지의 83%가 rain 대역 밖이라 가림은 여전히 판정하지 않는다.

(B) R115-1: 빗방울 과도음 12개가 배경보다 12–15 dB 낮아 들리지 않는다(제거 변이 생존). 들리게 하거나(지수 포락선 진폭 ~2, `--check` 통과 범위) 문구를 정정한다.

(C) R115-2~5:
- R115-2: Python 전용 키 별칭(`Synthesis`가 조용히 기본 생성)
- R115-3: 생성 WAV를 LFS 포인터 oid에 고정(생존 변이 5)
- R115-4: 실제 빗소리의 클릭 판정 범위
- R115-5: C-08 청취 가설

R114-2~6은 선택 이월.

**병합**: 오케스트레이터 결정(D-019). 이 커밋으로 반영했다(base가 main `46d07cb`라 합칠 것 없음).
- 위 "병합 시 반영 — T25" 문안은 STATUS 병행 트랙 WP-13 행, `astra-tasks.md` T25, DECISIONS D-015 진행에 옮겼다.
- STATUS C-08의 빗소리 가설은 R115-5로 갱신했다.
- R115-1은 **들리는 과도음(a)**으로 정했다(퀄리티 우선). gain은 K-가중으로 맞춘다. 이것과 (C) R115-2~4, R114-2~6 이월은 Astra **T26**으로 배정한다.
- PC 청취·패키지는 V-16 뒤 런북 §9 카드에서 한다.


## T26 — 빗방울 과도음·K-가중 레벨 (2026-10-05 KST)

배정: [이슈 #30 T26](https://github.com/wooklym/golmok/issues/30#issuecomment-5982843766), [R115](https://github.com/wooklym/golmok/pull/115#issuecomment-5982789631). main `9a52431`에서 `astra/wp-13-rain-followup2`로 시작했다.

- R115-1 a안: 4초당 36개의 1 ms 상승·6 ms 지수 감쇠(48 ms 길이) 과도음을 진폭2.1로 추가한다. 원형 인덱스/FFT로 이음매를 래핑한다. seed1307의 5 ms 포락선 max/중앙값 대비는 5.368 dB, 과도음 없는 동일 대역 노이즈2.060 대비 **+3.308 dB**다. 제거 변이를 잡는 ≥3 dB 단언을 추가했다. 가청성을 위한 물리적 대비 증거이며 사람 청취 증거는 아니다. 4초 반복 인지 여부는 밤 강한 비5분 PC 청취에 남기고 인지되면 rain만16–30초로 확장한다.
- 자산 rain gain **0.6023**. `day_gain / max_rain_curve × 10^((day_K − 2 − rain_K)/20)`로 산출·소수4자리 반올림, 최고 강수에서 K 차이 −2.0006 dB(허용±0.02) 회귀. 원본 peak 정규화 후 RMS는 T25 −25.5 → T26 −31.23 dBFS로 낮아져 gain0.3 제안을 그대로 쓰지 않았다. 곡선·실내 ×0.35·런타임은 그대로다.
- K 계산은 오디오 테스트 헬퍼 `tools/tests/audio_weighting.py`에서 numpy로 48 kHz 두 biquad의 주기적 정상상태를 FFT 평가한다. 계수 출처: [ITU-R BS.1770-1 Annex 1 Tables 1/2](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-1-200709-S!!PDF-E.pdf). K 표는 mono −0.691 보정 포함, 시간 게이트/다채널 합산 없는 루프 비교값으로 통합 LUFS·SPL 측정이 아니다. A는 1 kHz 정규화 아날로그 A 곡선을 FFT 빈에서 평가한 참고치(디지털 bilinear 필터와 다름). `audio_analysis`는 수정하지 않았다.

| 소스/모델 | RMS dBFS | K (무게이트) | A 가중 dBFS |
|---|---:|---:|---:|
| rain 원본 | −31.23 | −28.17 | −30.52 |
| 낮 원본 | −26.02 | −26.49 | −29.66 |
| rain 강수1 모델 | −46.53 | −43.47 | −45.82 |
| 낮 베드 모델 | −41.00 | −41.47 | −44.64 |
| 밤 베드 모델 | −44.62 | −45.12 | −48.31 |
| 실내 베드 모델 | −46.34 | −46.82 | −49.98 |

모델은 V-10b 공통 출력 오프셋 −8.96 dB + 자산 gain, rain에는 곡선최댓값0.8을 포함한다. 실내 rain은 해당 rain 모델에서 ×0.35(−9.12 dB). 모두 계산 예측이며 새 master-submix 녹음이 아니다.

- 선택 R115-2/3/4: Python 전용 키 source/seed/synthesis의 대소문자 별칭을 거절(런타임 KeyCase 패리티 불변), 자체 생성 WAV8개의 재생성 SHA-256과 LFS 포인터/스머지 파일 일치 회귀, 런북에 전환 구간만 rain 클릭·급정지 판정 및 정상 구간은 원본z 비교를 추가했다. R114-2~6은 이월한다.

### 검증 — T26

- rain `audio_analysis --check` 통과: peak−14.0, RMS−31.2, click z6.5, 급정지/clipping0. 최종 WAV SHA-256 `1126d5cc2e074045d109f0a1adaf2fe74ea3aa2d625ce2b471e27f1d96a27c75`. 기존7 WAV 바이트 유지, rain LFS·크레딧만 재생성.
- 관련 pytest **154 passed / 1 skipped**: 4seed×3반복 루프, 스펙트럼, 과도음 대비, 생성물8개 해시, alias, K 목표와 기준 사인파 검사. 전체 **1503 passed / 272 skipped / 208 warnings**(86.49 s), ruff check/format·UE Python lint·check_repo·diff --check 통과.
- 실제 UE 임포트/재임포트8+8, loop/변경 gain 포함8개 검증, `T26_IMPORT_VERIFIED_8_REIMPORT_8`, commandlet 오류0/경고0. 빌드/전체 UE 자동화는 C++ 변경이 없어 재실행하지 않는다(등록39 유지).
- 실제 청취·출력 루프백·패키지 미실행. 최종 곡선/실내/마스킹은 채택 음원 C-08, 플레이스홀더 PC 카드는 레벨·타이밍·클릭·mute/Photo·복원만. 소스 채택/소유자 결정 없음. Opus ultracode 코드+Opus 소리 품질 리뷰 요청.

### 병합 시 반영 — T26

STATUS/astra-tasks 문안: “T26 R115 후속 완료: 지수 빗방울36개/4초·대비+3.31 dB, K-가중 기준 rain gain0.6023(강수1 대 낮−2.00 dB), 원본파형 check 통과·임포트8+8. Python 전용 alias·생성WAV/LFS 회귀·전환 구간 판정 안내. 런타임/등록39 유지. PC 청취/패키지·4초 반복인지·최종 C-08 대기, R114-2~6 이월.”

DECISIONS D-015/C-08 진행 문안: “T26 과도음을 강화해 원본 RMS가−31.23 dBFS로 바뀌었으므로 rain gain0.6023으로 K-가중 강수1 대 낮−2.00 dB를 맞췄다. T25의 gain0.5 대0.3 비교는 이전 파형 기준이다. 새 초기값 주변에서 층 분리/거칠음/문간을 청취하고, 밤 강한 비5분 반복인지 시 rain 루프16–30초 확장을 검토한다. 최종 곡선/실내 배율/가림은 채택 음원에서 판단한다.”

## 병합 기록 — T26 PR [#116](https://github.com/wooklym/golmok/pull/116) (2026-10-04, 오케스트레이터 세션)

**병합 전 리뷰(Opus 5.5 ultracode 적대 검증 + Opus 디자인 리뷰, [R116](https://github.com/wooklym/golmok/pull/116#issuecomment-5983689306))**: (A) 0 · (B) 0 · (C) 4.
- 게이트(리눅스): ruff, format 118, pytest 1772 passed / 3 skipped(+9), check_repo, `diff --check`, 등록 39, CI 10/10; base `9a52431`(= main, merge-tree 충돌 0).
- UE 임포트 8+8은 Astra 보고다. C++ 변경이 없어 빌드·자동화는 재실행하지 않았다.

확인(결함 없음):
- K-가중 헬퍼의 계수·−0.691이 BS.1770 48 kHz 표와 같다. FFT 정상상태가 scipy 시간영역 필터와 0.001 dB 안에서 같다(997 Hz 사인 −3.01 LKFS, 게이트 적용 차 ≤ 0.01 dB). A는 IEC 61672 대비 ≤ 0.003 dB다.
- 문서 수치가 재현된다: rain RMS −31.23·K −28.17·A −30.52, 모델 표 6줄, gain 0.60234 → 0.6023, 강수 1 차 −2.0006 dB. 목표는 낮 베드 단독이고, 공통 오프셋·master는 상쇄된다.
- 과도음: 36개, 포락선 대비 +3.31 dB, `--check` z 6.5·급정지/clipping 0, 이음매·DC·주기성 정상. 베드와 섞으면 z 3.4–5.6이다.
- 자산: WAV 8개를 재생성한 sha256이 포인터 oid와 같다(기존 7개 불변, rain `1126d5cc…`, LFS 서버 객체와 바이트 일치). 크레딧은 생성기 출력과 같다.
- R115-2/3/4가 반영됐다: 별칭 거절(패리티 7목록 44키 불변), 포인터·스머지 해시 테스트, 런북 전환 구간 판정.
- 변이 41개 중 37개를 검출했다. R115 생존 변이는 모두 검출됐고, 생존 4개 중 2개는 등가다.

**디자인**: 보수적 초기값으로 채택한다.
- V-10b 기준 강한 비는 낮 베드 −2.0 dB·밤 +1.6 dB·실내 룸톤 −5.8 dB(K)다.
- 약한 비는 낮 −9.2 dB지만 4–8 kHz 옥타브에서는 베드보다 +2.2 dB다.
- 발소리 피크 여유는 강한 비 낮 17.4 dB(0.63이면 13.4 dB)다.
- T25 대비 강한 비 체감이 4.2 dB 내려가, 밤 합 증가가 +6.8 → +3.9 dB다.
- 자산 gain 상한 1.0이면 강한 비는 낮 +2.4 dB까지다. T25 체감(+2.2)은 gain 0.977이다 → C-08 비교.

(C) R116-1~4:
- R116-1: 빗방울 크기·감쇠가 고르다(틱 위험) → 분포와 1–4 kHz 대역.
- R116-2: 4 s 루프 반복 → PC 청취 전 rain 16–30 s.
- R116-3: 가중 테스트 보강(A 10 kHz, 48 kHz 가드, 997 Hz 기준, 목표 실패 메시지).
- R116-4: 런북 §9-2 rain 예측 레벨.

**병합**: 오케스트레이터 결정(D-019). 이 커밋으로 반영했다(base가 main `9a52431`라 합칠 것 없음).
- 위 "병합 시 반영 — T26" 문안은 STATUS 병행 트랙 WP-13 행, `astra-tasks.md` T26, DECISIONS D-015 진행에 옮겼다.
- STATUS C-08의 빗소리 가설은 R116 수치로 갱신했다.
- `tools/tests/audio_weighting.py`를 오디오 레인 목록(AGENTS.md §4, DEVELOPMENT-PLAN §7.6, `astra-tasks.md` 레인 변경)에 더했다.
- 오케스트레이터 판단(퀄리티 우선): R116-1(빗방울 분포)과 R116-2(rain 16–30 s 루프)는 둘 다 파형을 바꾼다. 그래서 PC 청취 **전에** 한 번의 재생성·K 재보정으로 묶어 Astra **T27**에 배정한다(PC 청취 카드 1회 절약). R116-3·4와 R114-2~6은 같은 과제의 선택 항목이다.
- PC 청취·패키지는 V-16 뒤 런북 §9 카드에서 한다.


## T27 — PC 청취 전 rain 루프·방울 분포 (2026-10-05 KST)

배정: [이슈 #30 T27](https://github.com/wooklym/golmok/issues/30#issuecomment-5983746740), [R116](https://github.com/wooklym/golmok/pull/116#issuecomment-5983689306). main `12b334b`에서 `astra/wp-13-rain-followup3`로 시작했다.

- rain만 Python 전용 `seconds=24`(정수16–30, 생략 시 이전4초)로 연장했다. 다른7개는 바이트/길이 불변(베드3개4초, 발소리/착지 원샷4개는 기존1/3초). rain WAV2,304,044 bytes, 파일당5 MB 예산 안이다. 채택 음원에서는 합성 메타데이터가 남아도 생성하지 않는다.
- 24초에216방울(9/s). 진폭 log-uniform0.6–3.3(14.8 dB 범위), 감쇠3–15 ms·상승1 ms, 과도음 대역1–4 kHz. 순환 간격은 최소30 ms에 무작위 지수 잔여 간격을 더해 정규화한다. 이전1.05초의 짧은4방울 군집을 피하고 등간격 틱 격자는 쓰지 않는다. 방울 꼬리는 서로 겹칠 수 있다. 합산 burst를 한 번 FFT 필터링해 길어진 루프에서도 생성 비용을 제한한다. 모든 방울은 이음매에서 래핑한다.
- 5 ms 포락선 max/중앙값5.846 dB, 동일 대역 무과도음2.400 대비 **+3.446 dB**. 전력 중심4108.9 Hz, 4seed×3반복 `--check`/대역·대비 회귀 유지. 반복/틱의 주관적 부재는 미판정이며 PC5분 청취로 확인한다.
- K 목표 강수1 rain 대 낮−2 dB를 유지하도록 gain **0.5503**으로 재보정했다(반올림 뒤−2.0003 dB). T26과 같은 numpy 48 kHz 두 단계 정상상태·mono−0.691 보정, 무게이트 루프 비교다. 런타임·가중 헬퍼·등록39는 변경하지 않았다.

| 항목 | RMS dBFS | K 무게이트 | A 가중 dBFS |
|---|---:|---:|---:|
| rain 원본 | −30.43 | −27.39 | −29.70 |
| 낮 원본 | −26.02 | −26.49 | −29.66 |
| 강수0.3 rain 층 예측 | −53.70 | −50.65 | −52.97 |
| 강수0.6 rain 층 예측 | −49.89 | −46.84 | −49.16 |
| 강수1 rain 층 예측 | −46.52 | −43.47 | −45.79 |

예측은 자산gain×rain곡선에 V-10b 출력 오프셋−8.96 dB를 적용한다. 실내 rain은 여기에 ×0.35. R116-4 런북 §9-2에는 상관없는 전력합으로 강수1 낮−39.93(+1.08)/밤−42.45(+2.16), 강수0.3 낮−40.77(+0.23)/밤−44.11(+0.51) dBFS를 적었다. 안착 뒤 최소24초 평균, ±1 dB 안은 기록만 한다. 실제 출력 측정·밸런스 판정이 아니다.

- 선택 R116-3: A10 kHz−2.49 dB, 44.1 kHz 거절, 997 Hz0 dBFS 사인−3.01 LKFS 기준, K목표 변경 시 gain도 함께 고치라는 실패 메시지를 추가했다. seconds 필드/별칭·잘못된 타입/범위·비rain 지정 거부·실제 프레임 길이 회귀도 추가했다. R114-2~6은 이월한다.

### 검증 — T27

- rain 원본 `audio_analysis --check` 통과: peak−14.0, RMS−30.4, 클릭z5.1, 급정지/clipping0. SHA-256 `2bfe82deca9cbf1afe0c868a2071c066f23a78412d19c060dbe8fe5f127035c8`. LFS/크레딧 재생성, 기존7 WAV 불변.
- 관련 pytest165 passed/1 skipped. 전체 **1514 passed/272 skipped/208 warnings**(94.78 s), ruff check/format·UE Python lint·check_repo·diff --check 통과. 실제 UE 임포트/재임포트 **8+8**, loop/gain 검증, `T27_IMPORT_VERIFIED_8_REIMPORT_8`, 오류0/경고0.
- C++ 무변경이라 빌드/전체UE자동화 재실행 없음. 실제 장치출력·루프백·청취·패키지는 미실행, V-16 뒤 wp13 §9 및 C-08에 남긴다. 새 출처/라이선스·소유자 결정 없음. Opus ultracode 코드+Opus 소리 품질 리뷰 요청.

### 병합 시 반영 — T27

STATUS/astra-tasks 문안: “T27 R116 후속 완료: rain24초·216방울의 진폭/감쇠 분포와 최소30 ms 순환 간격, K목표−2 dB 재보정 gain0.5503, §9-2 master submix 합 RMS 예측/±1 dB 기록 기준. 가중 기준/seconds 회귀·WAV/LFS 유지. 기존7 WAV·런타임·등록39 불변. PC 출력/패키지·5분 반복인지 청취·최종C-08 대기, R114-2~6 이월.”

DECISIONS D-015/C-08 문안: “T27은 PC 카드 전에 rain24초와 방울 분포를 한 번에 반영하고 gain0.5503으로 강수1 대 낮−2.0 dB K를 유지했다. T26 gain0.6023/0.977 비교는 이전파형 기준이므로 새파형 비교는0.5503 대 약0.893(+4.2 dB)로 환산한다. 반복/틱·밤5분 거칠음·실내 저역통과 필요성은 청취하고, 최종 곡선/실내/가림은 채택음원에서 정한다.”

## 병합 기록 — T27 PR [#117](https://github.com/wooklym/golmok/pull/117) (2026-10-04, 오케스트레이터 세션)

**병합 전 리뷰(Opus 5.5 ultracode 적대 검증 + Opus 디자인 리뷰, [R117](https://github.com/wooklym/golmok/pull/117#issuecomment-5984680780))**: (A) 0 · (B) 0 · (C) 4.
- 게이트(리눅스): ruff, format 118, pytest 1783 passed / 3 skipped(+11), check_repo, `diff --check`, 등록 39, CI 10/10; base `12b334b`(= main, merge-tree 충돌 0).
- UE 임포트 8+8은 Astra 보고다. C++ 변경이 없어 빌드·자동화는 재실행하지 않았다.

확인(결함 없음):
- `seconds`: C++ KeyCase 목록과 대소문자 충돌이 없고 모르는 키로 무시된다. 패리티는 7목록·44키 그대로다. Python이 별칭·정수 [16, 30]·rain 루프 한정을 검사하고, 생략하면 4 s다.
- 자산: WAV 8개를 재생성한 sha256이 포인터 oid와 같다(기존 7개 불변). rain `2bfe82de…` 2,304,044 bytes는 LFS 서버 객체와 바이트가 같다. 크레딧은 생성기 출력과 같고, 임포터에는 길이에 따른 경로가 없다.
- 방울: 216개, 진폭 0.607–3.300(14.7 dB), 감쇠 3.0–14.9 ms, 1–4 kHz. 시작 간격은 최소 30.25 ms, CV 0.78이다.
- 클릭·이음매: `--check` z 5.1(seed 40개 4.35–5.88), 급정지/clipping 0, 대비 +3.446 dB. 이음매·DC는 정상이고, 4/8/12 s 숨은 반복은 없다.
- K: rain RMS −30.43·K −27.39·A −29.70, gain 0.550316 → 0.5503(−2.0003 dB). 모델 표와 §9-2 예측이 오프셋 반올림 안에서 재현된다.
- 회귀·변이: R116-3 회귀가 반영됐다. 변이 61개 중 56개를 검출했고, 생존 5개 중 3개는 등가다. R116의 'A f4 생존'은 분자 상수만 바꾼 등가 변이였다.

**디자인**: 채택한다.
- K 관계는 T26과 같다: 강한 비 낮 −2.0·밤 +1.6·실내 −5.8 dB, 발소리 여유 ≥ 13.4 dB.
- 강한 비의 큰 방울이 더 다양하다(+6 dB 넘는 방울 낮 0.4/s·밤 0.75/s, 들리는 크기 폭 p10–p90 2.6 → 5.5 dB). 4 s 반복 단서도 사라졌다.
- 약한 비는 방울이 거의 묻혀 4–8 kHz에 정상 히스만 남는다.

(C) R117-1~4:
- R117-1: §9-2 ±1 dB 판별은 강수 1 밤 행만 → 판정 행·측정 방법·차분 측정을 적는다.
- R117-2: 방울 일정 성질 테스트와 `samples()` 가드 직접 테스트.
- R117-3: 런북 §1 "앰비언스 4초" 정정, 24 s 이음매 녹음·패키지 확인.
- R117-4: 약한 비 방울(청취에서 확인될 때만).

**병합**: 오케스트레이터 결정(D-019). 이 커밋으로 반영했다(base가 main `12b334b`라 합칠 것 없음).
- 위 "병합 시 반영 — T27" 문안은 STATUS 병행 트랙 WP-13 행, `astra-tasks.md` T27, DECISIONS D-015 진행에 옮겼다. STATUS C-08의 빗소리 가설도 R117 수치로 갱신했다.
- **오케스트레이터 판단(퀄리티 우선): 플레이스홀더 합성 rain 반복은 여기서 멈춘다.** 남은 질문(틱 대 비, 24 s 반복, 약한 비 질감, 실내 필터)은 귀로만 답할 수 있다. 단일 루프는 강도별 밀도를 원리적으로 표현하지 못한다. 그래서 다음은 V-16 뒤 wp13 §9 PC 카드 → C-08 → 채택 음원이다.
- Astra **T28**은 파형을 바꾸지 않는 묶음이다: PC 카드 전에 고칠 런북 정확성(R117-1·3), 방울 일정 성질 테스트(R117-2), 이월된 런타임 코드 품질(R114-2~6). R117-4는 청취 결과를 기다린다.


## T28 — 파형 유지·검증/런타임 품질 (2026-10-05 KST)

배정: [이슈 #30 T28](https://github.com/wooklym/golmok/issues/30#issuecomment-5984754855), [R117](https://github.com/wooklym/golmok/pull/117#issuecomment-5984680780). main `75b8869`에서 `astra/wp-13-audio-quality`로 시작했다. 합성 반복 종료 결정에 따라 WAV8개·audio.json 값·크레딧은 바꾸지 않았다.

- 필수 R117-1/3: wp13 §1의 길이를 베드3개4초/rain24초로 정정, §9-1/3 정상 구간·패키지에서24초 이음매 최소1회 통과. §9-2 판정은 강수1·밤−42.45±1 dBFS 한 행, 나머지 참고. §7-1 master submix 녹음에서 안착 뒤48초를 자르는 PCM 예시와 `audio_analysis` whole-file RMS 측정, 선택 clear/rain 차분 추정식을 적었다. 실제 청취/측정 결과가 아니다.
- 권장 R117-2: `rain_schedule(seed,count,rate)`가 독립 RNG로 배경 draw부터 재현하고 방울별 noise까지 반환해 원래 호출 순서를 보존한다. 생성기는 일정 출력으로 합성한다. 중복 배경 RNG draw 비용은 생기지만 파형 재현성을 우선했다. 4seed의9/s·순환 최소간격≥1439표본·간격CV>.5·진폭폭≥10 dB·감쇠3–15 ms, 비rain seconds 거부와 기존8개 LFS 해시 회귀 통과.
- 권장 R114-3: `RainGain`을 UE 독립 `GolmokAudioMath.h`의 점 배열 템플릿 순수 함수로 옮겼다. 파서가 검증한 점 배열을 받는 계약이며 FGolmokAudioConfig는 위임한다. 40개 무작위 곡선·매듭·범위 밖·NaN/Inf·빈 배열의 Python 거울/g++ 드라이버 교차검증을 추가했다. gain 비감소 규칙을 C++/Python 양쪽에 넣고 감소만 어긴 사례의 정확한 진단·파서 원자성(UE)을 검사한다. 기존 설정은 유효하다.
- 권장 R114-6: rain/베드2채널은 현재 AudioComponent.VolumeMultiplier와 목표의 차가1e-4 미만이면 SetVolumeMultiplier를 생략한다. 별도 캐시 없이 마지막 적용값과 비교하므로 작은 변화가 누적되면 갱신되고 교체 컴포넌트도 자체 값을 기준으로 한다. 종료 시0·Stop·Destroy 경로는 유지했다. 오디오 스레드 명령량의 실제 계측은 하지 않았다.
- 선택 R114-5: 초기화 전 disabled 공급자의0 기본값만 확인하는 단언임을 라벨/보고에 명시하고 Photo weather 조회에 null 가드를 추가했다. R114-2의 모든 독립 사례·R114-4 기대값 설정 기반 전환은 이번 범위에 포함하지 않았다. R117-4 약한 비 질감은 C-08 뒤다.

### 검증 — T28

- 로컬 Python 전체 **1519 passed/273 skipped/208 warnings**(91.98 s). g++/clang++가 없어 순수 수학 드라이버9건은 로컬 skip이며 CI Linux에서 확인한다. 관련165 passed/10 skipped. WAV8개 재생성/LFS 일치·기존자산/설정 diff0.
- ruff check/format·UE Python lint·check_repo·diff --check 통과. UE5.8.3 빌드 최초29.89 s·최종 테스트 추가 뒤6.51 s 성공. 전체 UE **39 Success**(일반26+경고13), Failed0/NotRun0, Audio2 포함. 보고서 `t28-full-index.json`의39개 state로 확인했다. 기저 fixture의 MPC/Fx 부재와 실제GASP 미설치 경로는 기존 제한이며 실제 출력 증거가 아니다.
- 실제 출력·루프백·패키지·청취 미실행. V-16 뒤wp13 §9/C-08 유지, 등록39. 새출처/라이선스·소유자 결정 없음. Opus ultracode 코드 리뷰 요청.

### 병합 시 반영 — T28

STATUS/astra-tasks 문안: “T28 완료: 파형/설정값 유지, rain PC판정 밤1행·master submix 절단/RMS·이음매 명시, 방울 일정 성질/LFS 회귀, RainGain 순수함수와 g++거울·비감소 검증, rain/베드 볼륨 불변 갱신 생략, disabled 범위·Photo null 가드. 등록39 유지. R114-2 전체·4는 이월, 실제 청취/출력/패키지·R117-4는 PC카드/C-08 뒤.”

## 병합 기록 — T28 PR [#118](https://github.com/wooklym/golmok/pull/118) (2026-10-04, 오케스트레이터 세션)

**병합 전 리뷰(Opus 5.5 ultracode 적대 검증, [R118](https://github.com/wooklym/golmok/pull/118#issuecomment-5985411136))**: (A) 0 · (B) 0 · (C) 3. 파형·설정값·소리 가설이 바뀌지 않아 디자인 리뷰는 하지 않았다.
- 게이트(리눅스): ruff, format 118, pytest 1789 passed / 3 skipped(+6), check_repo, `diff --check`, 등록 39, CI 10/10; base `75b8869`(= main, merge-tree 충돌 0). g++ 드라이버 9건이 실제로 실행됐다.
- UE 빌드·전체 39 Success(경고 13)·Audio 2는 Astra 보고다.

확인(결함 없음):
- 볼륨 생략: 비교 대상이 컴포넌트의 `VolumeMultiplier`(마지막으로 보낸 값)다. 작은 변화가 쌓이면 보내므로 오차는 1e-4 미만이다. 채널은 0에서 시작하고, 슬롯 교체·Deinitialize·구 설정 경로는 그대로다.
- `RainGain`: UE 타입 없는 inline 템플릿이다. 옛 구현과 1,538,200건이 비트 단위로 같다.
- 비감소 규칙: C++ `>=`와 Python `<` 거절은 같은 규칙(같은 값 허용)이다. 검사 순서·문구가 맞고, 현재 곡선은 통과한다.
- 방울 일정: RNG 순서가 같아 WAV 8개 sha256이 포인터 oid와 같다(rain `2bfe82de…`). 성질 테스트 여유는 최소 간격 1443–1473 표본, CV 0.66–0.78이다.
- 런북: 판정 행 강수 1 밤 −42.45 dBFS(+2.16)와 Δ 진단 −46.52 dBFS가 R117 모델과 같다. 절단 예시와 `audio_analysis` 명령은 합성 WAV로 실행해 확인했다.
- 변이: 40개 중 29개를 검출했다. 생존 11개는 등가 4, 경계 2(R118-2), R114-2 이월 5다.

(C) R118-1~3:
- R118-1: 날씨 clear 뒤 rain 채널 끝값이 0이 아니라 ≤ 1e-4로 남는다(들리지 않지만 "mute·clear = 디지털 0"이 깨짐). → 끝값 0은 항상 보낸다. 판정식은 순수 함수로 둔다.
- R118-2: 규칙 경계 사례(평평한 구간 수락, 진단 순서, driver Count 1의 Y ≠ 0).
- R118-3: §9-2 측정 조건(정지·`golmok.tod night`·정수 `start_s`·녹음 경로).

**병합**: 오케스트레이터 결정(D-019). 이 커밋으로 반영했다(base가 main `75b8869`라 합칠 것 없음). 위 "병합 시 반영 — T28" 문안은 STATUS 병행 트랙 WP-13 행과 `astra-tasks.md` T28에 옮겼다. 새 결정이 없어 DECISIONS는 바꾸지 않았다.

오케스트레이터 판단(퀄리티 우선): R118-1(디지털 0 보장)과 R118-3(PC 카드 측정 조건)은 PC 청취 카드 **전에** 고친다. 그래서 R118-2, R114-2 전체, R114-4와 묶어 Astra **T29**로 바로 배정한다(파형 무변경). R117-4는 C-08 청취 뒤다. wp13 §9 오디오 PC 카드는 T29 병합 뒤 V-16과 함께 발행한다.
