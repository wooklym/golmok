# V-12 — 캐릭터 룩 검증(프록시) 실행 런북·채점표

상태: ⚪ 대기(2026-09-29 작성, Fable). 절차·기준의 원문은 [WP-18 설계 "V-12 절차·채점"](../plan/WP-18-characters.md)이며 이 문서는 그것을 **실행 순서·촬영 매트릭스·소유자 채점표**로 풀어 쓴 것이다. 기준을 바꾸지 않는다. 전제: V-11(사람 눈 검수) 뒤, C-07 해소 뒤, D-010 경로(메시/splat)가 무엇이든 실 Zone이 없으면 `L_Basemap_Yeonnam`에서 한다.

## 카드 발행(2026-10-09, 오케스트레이터 Opus)
이 런북을 PC 카드로 낸다. 2026-09-29 작성 뒤 바뀐 사실은 §0~§5에 반영했다. 기준(§2·§3)은 바꾸지 않았다.
- **선행**: V-11 🟢(2026-10-04, [#100](https://github.com/wooklym/golmok/pull/100)). 이 카드에는 패키지 단계가 없어 C-07(방화벽)이 막지 않는다 — 위 "C-07 해소 뒤" 전제는 더 이상 조건이 아니다.
- **카메라 구도**: T23([#108](https://github.com/wooklym/golmok/pull/108), 2026-10-04 병합)으로 로스터 카메라 소켓 Z가 성인·proxy135 2 cm, proxy110 0 cm로 바뀌었고, 구도 기준은 제어 피치 −15°다(DECISIONS D-018 진행 기록 2026-10-04 (2)와 T23 결정). 실제 키 입력 재검수는 V-17 §2에서 아직이다. 그 결과로 프록시 붐·FOV가 바뀌면(R108-10) `base*` 샷은 다시 찍는다.
- **야간**: night는 D-010·14b(밤 look-dev) 전이라 어둡게 나올 수 있다. §0의 부분 완료 규칙대로 한다.
- **애니메이션**: GASP 로코모션(WP-19)은 아직 통합 전이다(19b 대기, `Config/Golmok/animation.json` mode `abp`). V-12는 지금의 ABP(`ABP_Unarmed`)와 로스터 그대로 찍는다. 로스터의 `manny_gasp`·`uefn_gasp`는 쓰지 않는다.
- **브랜치** `pc/v12-character-look`(origin/main에서, 기준 SHA를 §5에 적는다). PR → main. 오케스트레이터가 `claude/v12-merge`로 반입한다.
- **작업 폴더**(AGENTS.md §5): 이 세션의 Claude Desktop 워크트리에서만 일한다. 다른 워크트리·`C:\Users\user\golmok`은 읽기·복사만 한다.
- **GUI 잠금**: GUI 에디터·PIE 실행 전에 `C:\Users\user\AppData\Local\Temp\claude\gui-foreground.lock`을 확인한다(한 줄 `<세션> <목적> <ISO 시각>`). 20분이 안 된 기록이 있으면 기다린다. 쓰는 동안 20분 안에 갱신하고 끝나면 지운다. 성능 측정(§4) 중에는 다른 UnrealEditor·`-game` 프로세스가 없어야 한다. 헤드리스 빌드·테스트는 잠금 없이 해도 된다. V-08b·V-16·V-17·V-18 카드와 GUI 시간을 나눠 쓴다.
- **소요(추정)**: 1차 세션 약 6~8 h — 준비·빌드·자동화 1 h, 재질 3안 준비 1.5~2.5 h(Toon 로컬 사본 포함), 1차 96장 촬영 2~3 h, 측정 0.5 h, 축소·표 1 h. 소유자 채점은 따로 하고, 2차(후보 구성 × 배경 4곳)는 채점 뒤 다른 세션에서 약 2 h(후보 수에 비례).
- **저장소에 넣는 것**: 이 문서 결과 칸, STATUS V-12 자기 행·세션 로그, jpg(§1 규칙). PNG 원본·재질 에셋·Toon 사본은 넣지 않는다.
- **제품 코드 무수정**: Astra 레인(`Characters/`·`characters.json`)과 핫스팟 파일은 고치지 않는다. 결함이 보이면 PR 본문에 적는다.
- 돈이 드는 일, 라이선스 동의, 외부 발송은 하지 않는다.

**준비(§1 전)**
- [ ] STATUS V-12 행을 🔵로 바꾸고 세션 로그 줄을 단다.
- [ ] `git fetch origin` 뒤 열린 `pc/*`·`astra/*`와 겹침 확인(`git diff --stat origin/main...origin/<브랜치>`).
- [ ] `git switch -c pc/v12-character-look origin/main` → SHA 기록 → `git lfs pull`. `.\tools\ue\add-mannequin.ps1`. `L_Basemap_Yeonnam`은 이전 카드 워크트리(V-13 `sharp-leakey-9296c7` 등)에서 복사한다(읽기·복사만).
- [ ] `.\tools\ue\build.ps1` → `.\tools\ue\test.ps1 -SetupDevLevel -Filter Golmok.` → **39 Success**(`Golmok.Character.*` 7·`Golmok.Photo.*` 3 포함. `Golmok.Character.RenderEvidence`는 설계상 `NOT EXECUTED` Warning, `Golmok.Weather.Runtime`은 MPC·NS 에셋이 없으면 skip Info — 둘 다 상태 열은 `Success`).
- [ ] PIE(`L_Basemap_Yeonnam`)에서 `golmok.anim status` 첫 줄이 `mode abp (animation.json) …`, `golmok.weather status`가 clear·fixed(`weather.json` 시작값)인지 본다. 날씨는 끝까지 clear로 둔다.

## 0. 전제·역할
- 세션(Opus 5.5): 촬영·파일 정리·측정. **판정하지 않는다.** 룩 판단은 소유자 채점 + Opus 검토.
- 프록시 2종: `proxy135`·`proxy110`(WP-18a 로스터, 전체 스케일 프록시 — 4.5등신 리타깃 결과가 아님). 재질 3안: **PBR**(기준)·**장난감**(기존 설정 후처리, 같은 프로젝트)·**Toon**(5.8 Substrate 실험 — 별도 로컬 사본, 같은 PBR 대조군을 그 사본에도 둔다). 프록시 전환은 `golmok.character proxy135`·`golmok.character proxy110`. 로스터 카메라(`Config/Golmok/characters.json`, T23 뒤): proxy135 붐 260 cm·소켓 (0, 35, 2)·FOV 75°, proxy110 붐 226.7 cm·소켓 (0, 29.4, 0)·FOV 72.2°. 재질 3안을 프록시에 입히는 방법과 에셋 위치는 저장소에 정해진 도구가 없다 [PC 확인] — 세션이 정해 §5에 적는다. `Content/Characters/Mannequins` 원본 머티리얼은 고치지 않고, 사본은 `Content/Golmok/` 밖(예: `Content/V12Local/`)에 둔다(`Content/` 아래 `Golmok/`·`Python/` 밖은 git 무시, `.gitignore`). 조명 4 프리셋: `overcast_morning`·`clear_noon`·`golden_evening`·`night`(`Config/Golmok/lighting_presets.json` `cycle`). `golmok.tod mode fixed` 뒤 `golmok.tod <preset>`, 2 s 전환이 끝난 뒤 찍는다.
- night는 D-010/14b 전이라 화면이 검게 나올 수 있다(`design/lighting-night-lookdev.md`). 원래 프리셋 샷을 남기고, 광원/노출을 바꾼 보정 샷은 별도 표시한다. 야간 판정이 불가능하면 그 구성은 **부분 완료**로 적고 평균에서 뺀다.
- 배경 4곳(실명 간판·사람이 없는 구도만): ① 회색 콘크리트 ② 붉은 벽돌 ③ 초록 대문 ④ 간판 색면. 없는 배경은 무지 색판으로 대체하고 그렇게 적는다.
- 카메라: 기본 거리와 얼굴 0.5 m, 각각 f/2.8·f/8.
  - **기본 거리**: 프록시의 게임 카메라 그대로(위 로스터 값)에서 제어 피치를 −15°로 맞춘 뒤 포토 모드에 들어간 자리(포토 앵커 3 m 구). 2026-09-29 작성 때의 "피치 0"은 쓰지 않는다 — T23 뒤 피치 0은 카메라가 허리 높이(proxy 71/56 cm, V-17 §2(d))이고, 피치 0 구도의 발끝 잘림이 V-12 준비 검증(`RenderEvidence`)에서 지적됐다. 코드에 기본 피치 −15°는 없다(스폰은 PlayerStart 방향, 이동 도착은 피치 0°). −15°는 V-11 §14-2처럼 드라이버로 맞춘다(방법 [PC 확인]).
  - **얼굴 0.5 m**: 포토 카메라를 얼굴 앞 0.5 m로 옮긴 자리.
  - **f값**: 포토 모드는 DOF가 꺼져 있으면 f값이 화면에 영향이 없다(`GolmokPhotoCameraPawn.cpp` `ApplyOptics`: DOF off면 초점 거리 0). `golmok.photo.set dof 1`, `golmok.photo.set focus <캐릭터까지 m>`(얼굴은 0.5), `golmok.photo.set fstop 2.8`/`8`로 맞춘다(`photo.json` f값 목록에 2.8·8.0 있음).
  - **FOV**: 진입 때 로스터 FOV를 그대로 쓰고 오버레이 `fov` 값을 적는다. R(reset)은 FOV를 `photo.json` 기본 65°로 바꾸므로 쓰지 않는다(쓰면 다시 맞춘다).
  - Manual 노출값·Physical Camera Exposure 여부를 기록한다(포토 모드는 프리셋 노출 보정 + EV를 `AutoExposureBias`로만 넣는다. 레벨의 노출 방식은 [PC 확인]). 해상도·DLSS·그림자 설정은 전 구성 동일(§1 표 머리에 한 번 적음).

## 1. 촬영 매트릭스
**1차(대표 배경 1곳, ① 회색 콘크리트)**: 프록시 2 × 재질 3 × 조명 4 × 시점 4(기본 f/2.8·f/8, 얼굴 f/2.8·f/8) = 96장(Toon 미지원이면 64장 + 미실행 기록).
**2차(채택 후보 구성만, 배경 4곳)**: 후보 구성 n × 배경 4 × 시점 4.

파일명 `v12_<proxy>_<material>_<light>_<view>.jpg`(view = `base28`·`base8`·`face28`·`face8`; 2차는 `_bg2`~`_bg4` 접미), 공개본 jpg는 긴 변 ≤ 1600 px·각 ≤ 300 KB·LFS(`.gitattributes`의 `*.jpg`)로 `docs/runbooks/v12/`에 두고, PC 원본 고해상도는 로컬 보관. 촬영은 포토 모드: `golmok.photo 1` → 값 설정 → `golmok.photo.shoot`(`Saved/Screenshots/Golmok/photo/<stamp>.png` + `.json`, 배율 `ScreenshotMultiplier` 2) → 축소. 메타 `.json`의 `preset`·`dof`(`enabled`·`focal_m`·`fstop`)로 설정이 맞는지 확인한다.

| # | proxy | material | light | view | 파일 | 노출(Manual/PCE) | 비고(보정 샷·미실행 사유) |
|---|---|---|---|---|---|---|---|
| 1 | proxy135 | pbr | overcast_morning | base28 | v12_proxy135_pbr_overcast_morning_base28.jpg | | |
| … | | | | | | | |

(세션이 96행을 생성해 채운다. 순서: proxy → material → light → view.)

## 2. 소유자 채점표(구성 = proxy × material)
각 항목 1~5. **필수 셀**: 배경 ①의 조명 4 × 시점 `base28`·`face28`(8셀) — 이것이 구성 평균의 모집단이다. 나머지 시점(f/8)과 2차 배경 ②~④는 참고·재검증용으로 같은 표에 적되 평균에 넣지 않는다.

| 구성 | 배경 | 조명 | 시점 | 배경 조화 | 실루엣 | 사진 매력 | 발밑/벽 그림자 | 비율 감각 | 평균 | blocker(관통·그림자 수신 실패 등) | 메모 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| proxy135 × pbr | ① | overcast_morning | base28 | | | | | | | | |
| proxy135 × pbr | ① | overcast_morning | face28 | | | | | | | | |
| … | | | | | | | | | | | |

구성 요약(세션이 계산, 소유자 확인):

| 구성 | 필수 셀 수(실행/8) | 평균 | 최저 항목(점수·셀) | 부분 완료 사유(야간 등) | blocker | GPU ms/캐릭터(1080p, UE 단독) | VRAM peak | D-010 경로 | 판정(소유자·Opus) |
|---|---|---|---|---|---|---|---|---|---|
| proxy135 × pbr | | | | | | | | | |
| proxy135 × toy | | | | | | | | | |
| proxy135 × toon | | | | | | | | | |
| proxy110 × pbr | | | | | | | | | |
| proxy110 × toy | | | | | | | | | |
| proxy110 × toon | | | | | | | | | |

## 3. 통과 가설(WP-18 원문 그대로)
- 구성 평균 **4 이상**이고 개별 항목 **3 미만 없음**이면 채택 후보. 여러 재질·밝은 프리셋의 평균으로 실패한 구성을 덮지 않는다.
- 천장/계단 관통·그림자 수신 실패는 점수와 **별도 blocker**(하나라도 있으면 채택 보류, 원인은 D-010/에셋 쪽으로 기록).
- Toon 실패는 PBR 채택의 필수 조건이 아니다(미지원/미실행으로 남김). Toon 성공도 PBR 채택을 대신하지 않는다.
- 프록시 통과는 룩/카메라 가설을 좁히는 결과다. 최종 얼굴·연령감·4.5등신 승인은 원화·V-08 동작 영상·최종 에셋 검수가 있어야 한다(D-018 ②).

## 4. 측정(세션)
- fps/GPU ms: UE 단독 실행(다른 에디터·`-game` 없음), `stat gpu`·`stat unit` 3초 평균, 캐릭터 없음/있음 차이.
- VRAM peak: 첫 교체·촬영 포함(`stat memory` 또는 GPU-Z 로그), 동기 로드 hitch ms.
- 발 그림자·벽 그림자·splat 수신체(D-010이 splat이면)·헤어 DOF 경계는 §1 파일에 표시(빨간 원 표기 사본은 `_mark` 접미).

## 5. 결과 기록
| 항목 | 결과/근거 |
|---|---|
| 세션/head·장치·D-010 경로 | |
| 준비: 빌드·자동화(39 Success)·`anim`/`weather` 상태 | |
| 재질 3안 적용 방법·에셋 위치(로컬), 기본 거리 피치 −15° 맞춘 방법 | |
| 배경 4곳 실제 위치(Zone id·좌표) 또는 색판 대체 | |
| 1차 촬영 수(실행/96), Toon 실행 여부 | |
| 2차 후보 구성·배경 4곳 재검증 수 | |
| 부분 완료(야간) 구성 | |
| blocker 목록 | |
| 성능(§4) | |
| 소유자 채점 완료일·Opus 검토 | |
| STATUS 판정(V-12 🟢/부분/🔴, WP-18b 착수 조건 충족 여부) | |
