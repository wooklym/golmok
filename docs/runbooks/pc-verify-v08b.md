# V-08b — GASP 통합 전 PC 실험 카드 (D-021)

상태: ⚪ **카드 발행(2026-10-04, 오케스트레이터 Opus) — PC 대기.** 근거: [D-021](../DECISIONS.md) "후속 V-08b"·"이동 감각"·"Experimental 허용 범위"·진행 기록 (1)·(7)·(8), [D-018](../DECISIONS.md) "V-08 추가 시험"·진행 기록 2026-10-04 (3)·(4)(V-11 병합 [#105](https://github.com/wooklym/golmok/pull/105)), [WP-19](../plan/WP-19-gasp-locomotion.md) §6·§13·§15·§17, V-08 [런북 §8](pc-verify-animation.md), V-11 리뷰 [P11](https://github.com/wooklym/golmok/pull/100#issuecomment-5979649367) P11-5·P11-6·P11-10, V-08 병합 리뷰 R21 (B) 7·8·10. 결과는 각 절의 결과 표와 §13, STATUS V-08b 행에 적는다.

- **브랜치** `pc/v08b-gasp-experiment`(origin/main에서, 기준 SHA를 §13에 적는다). PR → main. 클라우드가 `claude/v08b-merge`로 문서·스크립트·jpg만 반입하고 `V-08b: tools` 커밋은 Opus 적대 코드 리뷰를 거친다.
- **작업 폴더**(AGENTS.md §5): 이 세션의 Claude Desktop 워크트리(`.claude\worktrees\<이름>`, 경로에 공백 없음)에서만 일한다. `C:\Users\user\golmok`, 다른 워크트리, `golmok-astra\*`는 읽기·복사만 한다.
- **소요**: 준비 1.5 h, 스크립트 2 h, §1·§2·§7 측정 3 h, §3 리타깃 3~4 h, §4·§5·§6 3 h, §8 패키지 1.5 h, §10 채점 1 h(다른 세션). 합계 약 15 h다. GUI 묶음 셋으로 나눈다: **G1** §1·§2·§7 → **G2** §3·§5·§6 → **G3** §4-3·§8. 묶음 사이에는 잠금을 풀어 다른 PC 카드가 GUI를 쓰게 한다.
- **실행 순서**: §0 → §9-1·§9-2(스크립트를 측정 전에 정리·대조) → §3-1·§4-1·§4-2(읽기 조사, 헤드리스 가능) → §1-1~§1-4(사전 등록 커밋 포함) → G1(§1-5·§2·§7) → §9-3 커밋(드라이버가 실제 실행으로 확인된 뒤, 이후 수정은 같은 접두어의 추가 커밋) → G2(§3-2·§3-3·§5·§6) → G3(§4-3·§8 — 패키지는 방화벽 창 때문에 마지막) → §10 → §11·§13.
- **GUI 잠금**: GUI 에디터·PIE·녹화·패키지 실행 전에 `C:\Users\user\AppData\Local\Temp\claude\gui-foreground.lock`을 확인한다(한 줄 `<세션> <목적> <ISO 시각>`). 20분이 안 된 기록이 있으면 기다린다. 쓰는 동안 20분 안에 갱신하고 끝나면 지운다. 녹화·틱 측정 중에는 다른 UnrealEditor·`-game` 프로세스가 없어야 한다(틱 간격이 흔들린다). 헤드리스 빌드·테스트·정적 조사는 잠금 없이 해도 된다.

**절대 규칙**
- **채택이 아니다.** 이미 받은 GASP(`C:\UE\GASP_58`, V-08 백업)로 하는 로컬 평가이고 V-08과 같은 범위다. 소유자 라이선스 원문 재확인 전에도 한다. 라이선스 판단을 새로 하지 않는다. 확인이 필요하면 STATUS "결정 필요"의 소유자 항목에 붙인다.
- **저장소에 넣는 것**: 이 문서, STATUS V-08b 행·세션 로그, §9 스크립트·테스트, jpg(`docs/runbooks/pc-verify-v08b-<항목>.jpg`, 긴 변 ≤ 1600 px, 각 ≤ 300 KB).
- **넣지 않는 것**: GASP 원본·사본·`.uasset`/`.umap`, GASP 설정 텍스트(DDCvar·태그 ini, 시험용 `.uproject` 플러그인 목록), 녹화·틱 원자료, 프록시 메시. V-08과 달리 **시험 설정 커밋도 만들지 않는다.** **`git add -A`/`git add .` 금지** — 파일 이름으로 하나씩 add한다.
- **제품 코드 무수정**: `Source/`, `Config/`(`animation.json` 포함), `Golmok.uproject`, Astra 레인(`Characters/`·`Audio/`·`characters.json`·`audio.json`)을 커밋하지 않는다. 시험 설정은 작업 트리에서만 쓰고 §13 정리에서 되돌린다. 고칠 일이 보이면 고치지 말고 기록해 19b·WP-19로 넘긴다.
- **GASP 무수정**: `C:\UE\GASP_58`은 열어도 저장하지 않고, 런처 업데이트도 하지 않는다. 바꿔야 할 것은 로컬 자식 BP(`Content/Golmok_AnimEval/V08b/`, Content 루트 규칙으로 git 무시)에만 둔다.
- 돈이 드는 일은 하지 않는다.

## 0. 준비
- [ ] STATUS V-08b 행을 🔵로 바꾸고 세션 로그 줄을 단다(§11-3 문안).
- [ ] 겹침 확인: `git fetch origin` 뒤 열린 `pc/*`·`astra/*`에 `git diff --stat origin/main...origin/<브랜치>`. #105(V-11 병합, D-018·D-021 진행 기록 2026-10-04)가 main에 있는지 본다. (T23 `astra/wp-18-camera-framing` [#108](https://github.com/wooklym/golmok/pull/108)과 `package.ps1` `GOLMOK_PKG_DIR` 도구 [#106](https://github.com/wooklym/golmok/pull/106)은 2026-10-04 main에 병합됐다.)
- [ ] 브랜치: `git switch -c pc/v08b-gasp-experiment origin/main` → SHA 기록 → `git lfs pull`. tools venv: `cd tools; py -3.12 -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -e ".[dev]"; $env:PYTHONUTF8=1; pytest -q`(기준선).
- [ ] UE 자료: `.\tools\ue\add-mannequin.ps1`. §6-4 포털용 `L_ZoneTest`와 합성 Zone은 이전 카드 워크트리(V-14 `goofy-maxwell-3aee56` 등)에서 복사한다(읽기·복사만, [`pc-verify-wp06.md`](pc-verify-wp06.md) §0~§4와 같은 자료).
- [ ] **패키지 출력 경로(§8용, C-07, PC 세션이 한 번)**: `[Environment]::GetEnvironmentVariable('GOLMOK_PKG_DIR','User')`가 비어 있으면 `setx GOLMOK_PKG_DIR C:\Users\user\golmok-pkg\Windows`를 실행하고 새 셸을 연다([pc-setup.md §2a](pc-setup.md), 소유자 작업 아님).
- [ ] 빌드·기준선(헤드리스): `.\tools\ue\build.ps1` → `.\tools\ue\test.ps1 -SetupDevLevel -Filter Golmok.` → **39 Success**(카드 발행 때 36, 그 뒤 WP-16a `Golmok.Weather.*` 3 — MPC·NS 에셋이 없으면 해당 단계 skip Info로 Success. `Golmok.Animation.GaspSmoke`는 `GASP not installed — skipped` Info).
- [ ] **GASP 식별**(V-08과 같은 판인지):
  - `C:\UE\GASP_58\*.uproject`의 `EngineAssociation`, `Content` 용량·파일 수(V-08: 5,582 MB)를 적는다.
  - `Get-FileHash`로 `Content\Blueprints\SandboxCharacter_CMC_ABP.uasset`·`SandboxCharacter_CMC.uasset`의 해시를 적는다.
  - 런처 Vault의 판 표기(V-08: 마지막 업데이트 2026-08-18)를 적는다.
  - 다르면 "GASP 갱신 — V-08 수치 대조 주의"(Fab EULA §7(a) 취득 시점 조건)로 적고 그대로 진행한다. 다시 받거나 업데이트하지 않는다.
- [ ] **GASP 사본**: `C:\UE\golmok_animeval_backup\Content\*`(V-08 Migrate 2,861 패키지 + `Golmok_AnimEval/`)를 이 워크트리 `unreal\Golmok\Content\`로 **복사**한다(백업은 그대로 둔다). 기존 `Characters\Mannequins`를 덮어쓰지 않았는지 확인하고, `git status --porcelain --untracked-files=all unreal/Golmok`에 GASP 경로가 0개인지 본다(`.gitignore` `[WP-19 hook]`).
- [ ] **시험 설정(작업 트리 전용, 커밋 금지)**:
  - 적용: `git fetch origin pc/v08-animation`, 그다음 `git show b61eea0 -- unreal/Golmok/Golmok.uproject unreal/Golmok/Config/DefaultEngine.ini unreal/Golmok/Config/DefaultGameplayTags.ini | git apply -3`(V-08 플러그인 21 + BlendStack, DDCvar 27, 태그 39). 충돌하면 같은 내용을 손으로 넣는다.
  - 적용 중에는 `check_repo.py`(gasp 가드: `Default*.ini`의 `DDCvar.`, `DefaultGameplayTags.ini`)와 `test_ue_wp19_fixture.py`(플러그인 허용 목록)가 **실패하는 것이 정상**이다.
  - 커밋할 때마다: `git stash push -u -- unreal/Golmok/Golmok.uproject unreal/Golmok/Config/DefaultEngine.ini unreal/Golmok/Config/DefaultGameplayTags.ini` → 게이트 → 이름으로 add·commit → `git stash pop`.
- [ ] 빌드(플러그인 켠 상태) → `Golmok.Player.Movement` 통과(V-08: 플러그인 켠 상태에서도 같은 값). GUI 에디터 인자는 V-11 §14-2와 같다(`bThrottleCPUWhenNotForeground=False`, `UnfocusedVolumeMultiplier=1.0`).
- [ ] `Golmok_AnimEval/Maps/L_Dev_AnimEvalB`(V-08 ②b 맵, 게임 모드 `BP_GolmokGameMode_AnimEvalB`)로 PIE를 띄운다. GASP 폰이 스폰되고 움직이는지 보고, 콘솔 `DDCvar.FootPlacementMode` 값이 1인지 본다. BP를 컴파일한 세션이면 PIE 전에 에디터를 다시 연다(V-08 함정).
- [ ] **녹화**:
  - 장비: ffmpeg `ddagrab` 60 fps `h264_nvenc -cq 21`(V-11 §14-2), PIE 새 창 1920×1080. Windows 집중 모드를 켠다(P11-7 알림 토스트).
  - 원자료(저장소 밖): `C:\UE\v08b_recordings\{rec,ticks,blind,key,pkg-logs}\`.
- [ ] **V-08 드라이버 찾기**:
  - V-08 스크래치(워크트리 `awesome-cohen-31f894`)와 `C:\UE\v08_recordings\scenes\`(드라이버 보고·틱 JSON).
  - V-11 `C:\Users\user\golmok-pc-recordings\v11-2026-10-04\`(보고서·스크립트)와 V-09c `pie_driver.py`(워크트리 `upbeat-mccarthy-343277`).
  - 찾은 경로를 §13에 적고 §9-1로 옮긴다. 못 찾으면 V-08 §8 "시험 방법·환경"과 V-11 §14-2 서술대로 다시 쓴다. 어느 쪽이든 ①·②b는 이 세션에서 다시 잰다(§1).
- [ ] 게임패드가 있으면 S8을 넣고, 없으면 "패드 없음"(C-09)으로 적는다.

장면(V-08 §2-2와 같음): S1 걷기 출발·정지(W 짧게 3회), S2 달리기 출발·정지(Shift+W), S3 180° 전환(W↔S), S4 원 그리며 달리기(W+마우스 60°/s), S5 계단 10단 오르내리기(`Course/Stairs`, 17 cm×10), S6 12° 경사, S7 60 cm 벽 점프·착지, S8 게임패드. 배치는 순간이동이다(S1~S4 골목 입구, S5 계단 앞, S6 경사 앞, S7 60 cm 벽 앞).

## 1. 이동 값 A/B — P0 현행 · P1 중간 · P2 GASP (R21-8)

**사전 등록 규칙(D-021 원문, 바꾸지 않는다)**
> 이동 감각: 최고 속도(걷기 180·달리기 500, 로스터별 145/380 등), 돌아서기(orient-to-movement), 점프 90 cm는 유지한다. GASP의 걷기 200·뒷걸음·넘기(traversal)는 채택하지 않는다. 가감속만 V-08b A/B로 정한다. 후보는 P0 현행·P1 중간·P2 GASP이고, 규칙은 미리 정한다. S1·S2 미끄러짐이 ①의 1/2 이하이고 1~5 합이 가장 높은 프로파일을 고른다. 동점이면 빠른 쪽을 고르고, 조작감 2 이하는 탈락이다.

| 라벨 | 폰 | 이동 값 | 용도 |
|---|---|---|---|
| `c1` ① | 우리 `AGolmokCharacter`(로스터 `manny`, `ABP_Unarmed`), `L_Dev` | 현행 | 미끄러짐 기준값(①) |
| `c2b` ②b | GASP `SandboxCharacter_CMC` 그대로, `L_Dev_AnimEvalB` | GASP 값(걷기 200, 뒷걸음) | 참고·채점 앵커(V-08 재측정) |
| `p0`·`p1`·`p2` ②b′ | 로컬 자식 BP `BP_V08b_P0/P1/P2`(부모 `SandboxCharacter_CMC`) | 우리 이동 의미 + 프로파일 | 선택 대상 |

우리 이동 의미(②b′ 공통):
- 걷기 180·달리기 500 cm/s. GASP에 방향별 속도 벡터가 있으면 세 성분을 같게 둔다.
- 돌아서기: orient-to-movement, 회전 속도 540°/s, 뒷걸음·스트레이프 없음.
- 점프: `JumpZVelocity` 420(정점 ≈ 90 cm), `AirControl` 0.3, `MaxStepHeight` 25.
- 넘기는 끈다(§12 #3). 전력 질주·웅크리기는 쓰지 않는다.

- [ ] **1-1 GASP 폰 값 조사**(측정 전, 읽기만, 저장 안 함). `SandboxCharacter_CMC`에서 Find in Blueprints로 아래 필드를 쓰는 곳을 찾고, `c2b` 틱 샘플(§9 `cmc` 필드)로 런타임 값을 확인한다. 회전 모드 변수, 방향별 속도 변수, 넘기 진입 함수 이름도 적는다.

  | CMC 필드 | CDO 기본값 | 런타임에 쓰는 곳(함수·이벤트·조건) | 걷기 정속 | 달리기 정속 | 정지 중 |
  |---|---|---|---|---|---|
  | MaxAcceleration | | | | | |
  | BrakingDecelerationWalking | | | | | |
  | GroundFriction | | | | | |
  | BrakingFrictionFactor | | | | | |
  | bUseSeparateBrakingFriction | | | | | |
  | BrakingFriction | | | | | |
  | MaxWalkSpeed · RotationRate · bOrientRotationToMovement · bUseControllerDesiredRotation · JumpZVelocity · AirControl · MaxStepHeight | | | | | |

- [ ] **1-2 P2 정의**: P2는 GASP 런타임 값이다.
  - 걷기·달리기 값이 같으면 그 값을 쓴다.
  - 게이트(gait)·속도에 따라 바뀌면 우리 스키마(단일 값, WP-19 §6)로 옮길 수 없다. 이때는 A/B를 "P2 = GASP 그대로(가변)"로 끝내고 게이트별 표를 §11로 넘긴다. 스키마 처리는 19b 전에 오케스트레이터가 정한다.
  - WP-19 §6 범위(`ValidateProfile`) 밖의 값이 나오면 적고 보고한다.
- [ ] **1-3 P1 정의(이 카드가 측정 전에 고정)**:
  - 숫자 필드는 (P0 + P2) / 2이고, cm/s² 필드는 정수로 반올림한다.
  - `use_separate_braking_friction`은 P2 값을 따른다. 그 값이 true면 `braking_friction` = (P0 실효값 8[별도 마찰을 끄면 엔진은 `GroundFriction`을 쓴다] + P2) / 2다.
  - P2가 가변이면 게이트마다 같은 식을 쓴다.
  - 표를 채우고 **측정 전에** 문서만 커밋한다: `V-08b: 사전 등록 값(P1·P2)`(설정 stash 뒤).

  | 필드 | P0(현행) | P2(GASP) | P1(중간) | 범위(WP-19 §6) |
  |---|---|---|---|---|
  | max_acceleration | 2048 | | | 100~10000 |
  | braking_deceleration_walking | 2000 | | | 0~10000 |
  | ground_friction | 8 | | | 0~20 |
  | braking_friction_factor | 2 | | | 0~10 |
  | use_separate_braking_friction | false | | | bool |
  | braking_friction | 0 | | | 0~20 |

- [ ] **1-4 자식 BP**: `Content/Golmok_AnimEval/V08b/BP_V08b_P0`·`_P1`·`_P2`(부모 `SandboxCharacter_CMC`)를 만든다.
  - 클래스 기본값에 우리 이동 의미와 프로파일을 넣는다.
  - GASP가 틱마다 값을 다시 쓰면 그 함수를 자식에서 오버라이드하거나(부모 그래프는 고치지 않는다), 자식 Event Tick에서 부모를 부른 뒤 다시 쓴다(§12 #1).
  - 컴파일 뒤 에디터를 **다시 연다**(V-08 함정).
  - 폰 교체는 PIE 중 Python 스폰·빙의로 하거나(§12 #13) 조건별 게임 모드 BP를 쓴다. PIE마다 폰 클래스를 로그 첫 줄에 남긴다.
- [ ] **적용 확인(측정 전 게이트)**. 하나라도 틀리면 측정하지 않고 원인부터 고친다.
  - (a) 모든 틱의 CMC 값이 프로파일 값과 같다.
  - (b) 최고 속도 180/500 ± 1 cm/s, S3에서 몸이 돈다(캡슐 yaw 180° 변화, 뒷걸음 아님), 점프 정점 90 ± 3 cm.
  - (c) `p0`의 표 B 값이 ①과 같은 크기다(V-08 표 B: 걷기 90 % 0.08~0.09 s, 달리기 0.23 s, 정지 2~3 / 14~15 cm). 크게 다르면 덮어쓰기가 안 된 것이다.
- [ ] **1-5 녹화·틱**(G1): 조건 5개 × S1~S7(패드 있으면 S8)을 §9 드라이버로 돌린다. S1·S2는 3회 반복하고 판정에는 중앙값을 쓴다. 나머지는 1회다.
  - 카메라는 각 폰의 기본이다(①은 로스터 카메라, 나머지는 GASP 카메라). 같은 카메라 조건은 V-15 몫이다. ①은 메시·카메라가 달라 블라인드가 완전하지 않다(V-08과 같음). 핵심은 P0/P1/P2 사이의 블라인드다.
  - S7에서 Space가 넘기를 띄우면(§12 #3) 평지 점프 S7′로 바꾸고 표에 표시한다.
- [ ] **1-6 지표**(§9 통일 정의). 결과 표:

  | 조건 | S1 slip cm/m(중앙값 [범위]) | S2 slip | S3 | S4 | 걷기 90 % s | 달리기 90 % s | 걷기 정지 s/cm | 달리기 정지 s/cm | 정지 뒤 발 이동 S1/S2 cm | 정속 보폭 걷기/달리기 cm |
  |---|---|---|---|---|---|---|---|---|---|---|
  | c1 ① | | | | | | | | | | |
  | c2b ②b | | | | | | | | | | |
  | p0 | | | | | | | | | | |
  | p1 | | | | | | | | | | |
  | p2 | | | | | | | | | | |

  V-08 표 A(① 16.4·12.6·20.8·8.2, ②b 4.4·3.3·6.3·6.9)를 옆에 참고로 적는다. 180 cm/s에서 스트라이드 워핑이 어떻게 보이는지(발이 끌리는지, 보폭이 줄어드는지)를 한 줄로 적는다(WP-19 §17 #10).
- [ ] **1-7 선택**(§10 채점 뒤, 기계적으로 적용):
  1. 자격: S1 ≤ ½ × `c1` S1 **그리고** S2 ≤ ½ × `c1` S2. 같은 세션·같은 정의의 중앙값으로 본다. V-08 표 A 값은 참고로만 쓴다.
  2. 조작감(채점 5번) ≤ 2면 탈락이다.
  3. 남은 것 가운데 1~5 합이 가장 높은 프로파일을 고른다. 동점이면 빠른 쪽(가감속이 큰 쪽: P0 > P1 > P2)을 고른다.
  4. 자격 있는 프로파일이 없으면 고르지 않는다. "해당 없음"과 수치를 적고 오케스트레이터 결정(D-019)으로 넘긴다. 그때까지 19b는 `movement_profile: p0`이다.

  | 프로파일 | S1 ≤ ½① | S2 ≤ ½① | 조작감(5번) | 1~5 합 | 결과 |
  |---|---|---|---|---|---|
  | p0 | | | | | |
  | p1 | | | | | |
  | p2 | | | | | |

## 2. 돌아서기 모드 — S3 · S5 · S6 (R21-3)
규칙: D-021이 돌아서기(orient-to-movement)를 고정했다. V-15 기준은 "S3은 돌아서기로 측정"이다. **고를 것이 없으므로 기록만 한다.** V-08 ②b의 S3·S5·S6 하행은 뒷걸음이라 참고치였다(V-08 §8 R21-3).
- [ ] §1 녹화를 그대로 쓴다(`c1`·`p0~p2`는 돌아서기, `c2b`는 GASP 기본 뒷걸음). 선택 사항으로 `c2b-o`(GASP 값 + 돌아서기만)를 한 번 더 찍으면 회전 모드 효과만 따로 볼 수 있다.
- [ ] 지표:
  - S3: S 입력부터 캡슐 yaw가 180° ± 5°에 드는 시간, 전환 창(입력 + 1.0 s) PlantedSlip, 메시 yaw 지연 최대(root 뼈 yaw − 캡슐 yaw, 메시 기본 yaw 보정).
  - 피벗 동작 유무: 발을 딛고 방향을 바꾸는지, 제자리에서 도는지(녹화로 판단).
  - S 입력 때 GASP 카메라가 크게 도는지.
  - S5·S6 하행: 정면으로 내려가는지, 그리고 §7 계단·경사 접지.

  | 조건 | S3 돌아서기 s | S3 전환 창 slip cm/m | 메시 yaw 지연 최대 ° | 피벗 동작 | 카메라 회전 | S5 하행 정면 | S6 하행 정면 | 메모 |
  |---|---|---|---|---|---|---|---|---|
  | c1 / c2b / p0 / p1 / p2 (/ c2b-o) | | | | | | | | |

## 3. Manny · 4.5등신 리타깃 (D-018 V-08 추가 시험, WP-19 §17 #3)

### 3-1 GASP 리타깃 경로 조사(읽기만)
- [ ] **경로 확인 표**(`tools/ue/gasp/closure.json`의 estimated 루트와 `animation.json` [추정] 경로 → 19b §A3·§A7).

  | 항목 | 19a 추정 경로(원래 GASP `/Game` 기준) | 실제 경로 | 패키지 존재 | 비고 |
  |---|---|---|---|---|
  | 폰 인터페이스 BPI | `/Game/Blueprints/Interfaces/BPI_SandboxCharacter_Pawn` | | | |
  | UEFN 소스 메시 | `/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin` | | | |
  | 리타깃 ABP | `/Game/Blueprints/RetargetedCharacters/ABP_GenericRetarget` | | | |
  | GASP 매니 사본 메시 | `/Game/Characters/UE5_Mannequins/Meshes/SKM_Manny_Simple` | | | |
  | IK Retargeter(UEFN→Manny), IK Rig 2개 | — | | | |

- [ ] `BP_Manny`(`Blueprints/RetargetedCharacters/`) 컴포넌트 계층을 적는다: 시각 메시가 소스 메시의 자식인지, 소스가 숨김인지, 틱 옵션. `ABP_GenericRetarget`의 `Retarget Pose From Mesh` 설정(Use Attached Parent·소스 컴포넌트 태그·IK Retargeter 지정 방식), `TargetSkeleton` 값(없음 또는 이름 — wp19 §D #19)도 적는다. GASP의 캐릭터 전환(`DDCvar.VisualOverride` 등) 값 대응은 §12 #5에 적는다.

### 3-2 Manny 시각 메시 (V-15 "같은 메시"의 사전 확인)
- [ ] 자식 BP `BP_V08b_Manny`(부모 `BP_V08b_P0`, §1 선택이 끝났으면 그 프로파일)를 만든다. 구성은 `AGolmokGaspCharacter::VisualMesh` 설계(WP-19 §5)를 흉내 낸다. 소스 메시의 자식으로 SkeletalMeshComponent를 하나 붙이고, 소스는 게임에서 숨기되 `AlwaysTickPoseAndRefreshBones`로 둔다. 그림자는 시각 메시가 낸다.
  - (a) GASP 매니 사본 + `ABP_GenericRetarget`
  - (b) 우리 `/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple` + 같은 ABP(§12 #6)
  - 되는 쪽을 적는다.
- [ ] S1~S5를 시각 메시 뼈와 소스 뼈로 **동시에** 샘플한다. 미끄러짐 차이, 팝, 관통, `stat anim` 차이(선택)를 적는다.

  | 변형 | 작동 | 부착 방식(부모 부착/태그/기타) | S1 / S2 / S4 slip(시각 · 소스) | S5 상승 p10 / 하강 p90(시각) | 문제 |
  |---|---|---|---|---|---|
  | (a) GASP 매니 사본 | | | | | |
  | (b) 우리 SKM_Manny_Simple | | | | | |

  판정: 없다(기록). 19b §A7 `preview.visual_mesh`·`visual_anim_class`와 wp19 §D #3·#19의 입력이다.

### 3-3 4.5등신 프록시 (D-018)
**시험 문안(WP-18 마지막 문안, 원문)**
> 135cm·4.5등신(머리30cm), 넓은 몸/짧은 다리의 임시 휴머노이드 프록시에 GASP를 IK Retargeter로 적용. 18a 전체 스케일 proxy135는 카메라/키 비교에만 사용하고 머리/팔다리 비율을 조정한 프록시를 별도로 준비한다. 리타깃만/팔·상체 가산 보정/키프레임 기준 영상 비교. 145/380cm/s, 정지→걷기→달리기→180도 턴→25cm 계단. 팔-머리/배 관통 횟수, 접지 발 미끄러짐(cm), 성인 보폭 느낌, 자연스러움과 귀여움을 각각 채점. 다른 리그를 호환 스켈레톤 지정만으로 실행하지 않는다.

**사전 등록 통과 조건(D-018 진행 기록 2026-10-04 (3), P11-6, 원문)**
> 18b 최종 캐릭터와 V-08b 4.5등신 시험은 정속 걷기 딛은 발 미끄러짐 ≤ 성인 ① 수준(V-11 정의, ≈ 8 cm/m)을 통과 조건으로 둔다.

- [ ] **프록시 요건**: 키 135 cm, 머리 30 cm, 넓은 몸·짧은 다리다. **별도 스켈레톤 자산과 IK Rig**를 둔다(뼈 이름은 UE5 마네킹과 같아도 된다). 메시는 로컬 전용이고 스크린샷만 커밋한다. D-018에 따라 전체 스케일 `proxy135`를 4.5등신 리타깃 결과로 취급하지 않는다.
- [ ] **만드는 법**(쉬운 것부터, §12 #7):
  - (a) UE 5.8 Skeletal Editor(스켈레톤 편집)로 `SKM_Manny_Simple` 로컬 사본의 기준 포즈 비율을 바꾼다(머리 약 ×1.6, 허벅지·종아리 짧게, 몸통 넓게).
  - (b) 우리 스크립트로 블록 휴머노이드 skinned glTF를 만들어 Interchange로 임포트한다. 스크립트를 커밋하려면 §9 tools 커밋에 넣고 pytest를 붙인다.
  - **2 h 안에 못 만들면** 멈추고 "미실행 — 사유"를 적는다. 그다음 V-08c(별도 카드)로 넘긴다.
- [ ] **리타깃**: 프록시 IK Rig를 자동 생성한 뒤 다리·팔·척추 체인을 확인한다. IK Retargeter `RTG_V08b_UEFN_to_H45`는 소스가 GASP UEFN IK Rig다. 5.8 Foot Definition·Retarget Override Sets([research/11](../research/11-character-pipeline.md) B4)를 써도 된다. 변형 세 개:
  - `h45_rt`: 리타깃만
  - `h45_add`: 팔·상체 가산 보정(체인 오프셋·Override Set으로 팔 벌림·상체 보정, 관통 줄이기)
  - `h45_key`: 키프레임 기준 — ① `ABP_Unarmed`(템플릿 키프레임 클립)를 같은 프록시에 리타깃한 비교 영상(카드의 해석)
- [ ] **폰**: `BP_V08b_H45`(부모 `BP_V08b_P0`; 정속 지표는 가감속과 무관). 캡슐 33.6/69(`proxy135`), 걷기 145·달리기 380, GASP 카메라(구도는 T23·V-12 몫).
- [ ] **시나리오**: 정지 → 걷기(정속 3 s 이상) → 달리기(정속 3 s 이상) → 180° 턴 → 25 cm 계단을 측면·후면 각 1회 녹화한다. 25 cm 계단은 V-11의 25 cm 턱이다(중심 (−4700, −4000), 600×400×25 cm, `Golmok.Character.Locomotion`과 같은 좌표). 비transient로 스폰하고 저장하지 않는다(V-11 v11a 함정). 17 cm×10 계단(§7)도 돈다. 판정 기준값을 위해 `c1`(Manny ①, 180/500)도 같은 시나리오로 한 번 찍는다.
- [ ] **지표**:
  - 정속 걷기·달리기 slip: 통일 정의와 `legacy_v11` 둘 다.
  - §7 계단 접지.
  - 관통: 자동은 손·아래팔 뼈 ↔ 머리 구·배 캡슐(프록시 실측 반지름) 안의 틱 수, 그리고 채점자가 눈으로 센 개수.
  - 정속 보폭 cm·걸음 주기 Hz, 팝(틱당 캡슐 대비 뼈 상대 이동 최대).
- [ ] **판정 운용**(사전 등록 문장 그대로, 운용만 정한다):
  - 기준값은 같은 세션·같은 정의의 `c1`(Manny ①) 정속 걷기 slip이다.
  - V-11 정의 값과 "≈ 8 cm/m"(V-11 Manny 6.9·7.9)도 나란히 적는다.
  - 두 정의가 다른 판정을 내면 둘 다 적고 오케스트레이터가 판단한다.
  - 자연스러움·귀여움·성인 보폭 느낌은 §10 채점 B다. 기준은 없고 D-018 ② 판단의 입력이다.

  | 변형 | 정속 걷기 slip 통일 (측면 · 후면) | V-11 정의 | 기준 c1 | ≤ 기준 | 달리기 slip | 계단 상승 p10 / 하강 p90 | 25 cm 턱 p10~p90 | 관통 틱(자동) | 보폭 cm · 주기 Hz | 팝 최대 cm |
  |---|---|---|---|---|---|---|---|---|---|---|
  | h45_rt | | | | | | | | | | |
  | h45_add | | | | | | | | | | |
  | h45_key | | | | | | | | | | |

## 4. `.uplugin` 플래그 표 (D-021 조건 4 → 19b §A2, R21-7)
**D-021 원문**
> 무수정 GASP 로코모션 에셋이 참조해서 켜야 하는 플러그인과 그 의존 플러그인만 허용한다. 기록상 PoseSearch·Chooser·AnimationWarping·MotionWarping(Beta)·AnimationLocomotionLibrary(Beta)·BlendStack·CurveExpression·DrawDebugLibrary·MovieSceneAnimMixer·Mover이고, Offset Root Bone 노드도 포함한다.

조건 1~5(모듈 의존 금지·CMC 유지·Development·Shipping 패키지 스모크·이 표·엔진 버전 변경 시 재검증)와 불허 목록(GameplayCameras, Mover 폰·ChaosMover, 넘기·SmartObjects·GameplayInteractions·Locomotor, MetaHuman·LiveLink·RigLogic·HairStrands, `MotionMatchMulti`·UAF)은 D-021 그대로다.

- [ ] **4-1 정적 조사**(헤드리스, 잠금 불필요). 대상은 ABP 폐포와 리타깃 루트(§3-1 실제 경로)다. GASP 프로젝트는 열어도 저장하지 않는다. 가능하면 이 워크트리의 사본으로 조사한다.
  - 대상 패키지의 의존에서 `/Script/<모듈>`을 모은다(§12 #16).
  - 엔진 `Engine\Plugins\**\*.uplugin`의 `Modules[].Name`으로 플러그인을 찾는다.
  - `Plugins[]` 의존을 재귀로 더한다.
  - V-08 기록상 ABP가 직접 참조하는 모듈: AnimationWarping·BlendStack·Chooser·CurveExpression·DrawDebugLibrary·Mover·MovieSceneAnimMixer·PoseSearch·PropertyAccessNode.
- [ ] **4-2 BPI·캐스트 조사**(19b §A4-2를 미리 채움, wp19 §D #2). `BPI_SandboxCharacter_Pawn` 함수와 시그니처(반환 구조체·열거형 멤버)를 적는다. ABP 그래프에서 폰 클래스 캐스트(`Cast To SandboxCharacter_CMC` 등)를 찾는다. **BPI 밖에서 폰을 읽는 노드가 있으면** WP-19 §13 대안 (b)(무수정으로 못 풂 → B안·D-021 개정 검토)의 조기 경보다. §13과 STATUS에 바로 적고 오케스트레이터(이슈 #30)에 보고한다.

  | # | 함수 | 입력 | 반환(구조체/열거형 멤버) | 비고 |
  |---|---|---|---|---|
  | 1 | | | | |

  | ABP 캐스트 노드 | 대상 클래스 | 읽는 값 | 대체 가능(BPI·CMC로) |
  |---|---|---|---|
  | (없으면 "없음") | | | |

- [ ] **4-3 최소 집합 확인**(G3, §8 전).
  1. 작업 트리 `.uproject` 플러그인을 main 목록 + 4-1 최소 집합으로만 바꾼다(시험 설정 대체, 커밋 금지).
  2. 빌드하고 에디터를 다시 연다.
  3. 확인: ABP·리타깃 ABP 컴파일 오류 0, 로그에 플러그인·모듈 누락 없음. ABP 폐포 밖 자산(GASP 폰·레벨·MetaHumans 등)이 내는 경고는 따로 센다. 판정은 ABP·리타깃 ABP·스모크 맵 경로에서 나온 오류로만 한다.
  4. 스모크 맵 `/Game/GolmokLocal/V08b/L_V08b_PluginSmoke`(L_Dev Save-As)를 만든다. 구성: UEFN 메시 + `SandboxCharacter_CMC_ABP`를 단 SkeletalMeshActor 하나와, 그 자식 Manny 시각 메시 + `ABP_GenericRetarget`.
  5. PIE에서 아이들 포즈가 나오고(인터페이스 기본값으로 서 있음) 오류가 없는지 본다.
  6. 빠져서 필요해진 플러그인은 더하고 이유를 적는다.
- [ ] **4-4 판정**: 최소 집합이 D-021 허용 목록 + 그 의존 안이면 통과다. 허용 밖(불허 목록 포함)이 필요하면 **멈추고 보고한다**. D-021 개정이 필요하고, 그때까지 19b는 진행할 수 없다.

**표(19b §A2가 그대로 읽는 형식)**

| 플러그인(`.uproject` Name) | `.uplugin` 경로(`Engine/Plugins/` 아래) | IsBetaVersion | IsExperimentalVersion | EnabledByDefault | 의존 플러그인(`Plugins`) | 필요 근거(참조 모듈 · 참조 패키지 수 / 의존 / 경고) | D-021 허용 | `.uproject`에 적음 | V-08 기록[2차] |
|---|---|---|---|---|---|---|---|---|---|
| PoseSearch | | | | | | | 예 | | 플래그 없음 |
| Chooser | | | | | | | 예 | | 플래그 없음(문서 배너는 Experimental) |
| AnimationWarping | | | | | | | 예 | | 플래그 없음 |
| MotionWarping | | | | | | | 예 | | Beta |
| AnimationLocomotionLibrary | | | | | | | 예 | | Beta |
| BlendStack | | | | | | | 예 | | — |
| CurveExpression | | | | | | | 예 | | Experimental 모듈 |
| DrawDebugLibrary | | | | | | | 예 | | Experimental 모듈 |
| MovieSceneAnimMixer | | | | | | | 예 | | Experimental 모듈 |
| Mover | | | | | | | 예 | | Experimental 모듈 |
| (의존으로 더 필요한 것, 예: NetworkPrediction) | | | | | | | 의존 | | |

함께 남길 것:
- 19b §A2가 붙여 넣을 `Golmok.uproject` `Plugins` 줄(이 순서): `{ "Name": "PoseSearch", "Enabled": true },` …
- `tools/tests/test_ue_wp19_fixture.py` `ALLOWED_PLUGINS` 추가 요청: `<이름> — <근거>`(의존 플러그인만, 없으면 "없음")
- `EnabledByDefault`라 적지 않아도 되는 것(PropertyAccessNode 등)

## 5. 폴리 노티파이 (19b §A5, WP-19 §17 #8)
**규칙(D-021 진행 기록 2026-09-30 (1), 원문)**
> 원본 GASP 발 폴리는 19b BP가 `footsteps.driver`와 무관하게 끄고 Step·Land만 `NotifyFootEvent`로 보낸다. Golmok 폰의 발소리 소스는 `audio.json` 하나로 둔다(…). 점프 발성·옷 스침 같은 발 이외 폴리는 V-08b §5 기록 뒤 따로 판단하며 그 전에는 쓰지 않는다.

이 절은 기록만 한다. 새 결정은 하지 않는다.
- [ ] **5-1 정적**: ABP 폐포 AnimSequence·Montage의 노티파이를 클래스·`Foley.Event.*` 태그별로 센다(§12 #9). 노티파이가 부르는 대상(폰 인터페이스 함수·시그니처, 또는 노티파이 안에서 직접 재생)과 재생 자산(MetaSound·데이터 자산 경로)을 적는다.
- [ ] **5-2 런타임**: `BP_V08b_P0`(또는 선택 프로파일)의 자식 BP에서 폴리 인터페이스 함수를 오버라이드한다. 로그만 남기고 부모는 부르지 않는다(끄는 방법 후보). S1·S2·S7 동안 다음을 적는다(§12 #4).
  - 이벤트(태그·좌우·시각)
  - 발 접지 시각(ball z 최저)과의 시차 중앙값(ms)
  - 걸음당 이벤트 수
  - 발 이외 폴리의 종류(점프 발성·옷 스침 등)
- [ ] **5-3 소리 확인**: 오버라이드 전후로 master submix를 녹음한다(V-10 방식, `unreal.AudioMixerLibrary.start_recording_output`/`stop_recording_output`). `cd tools; python -m golmok_tools.audio_analysis <wav> …`로 발소리 onset 수를 비교한다. 오버라이드 뒤 GASP 폴리가 0이면 그것이 끄는 방법이다. 노티파이가 폰을 거치지 않고 직접 재생하면 무수정으로 끌 수 있는지 적고 보고한다(19b §A5 위험).

| GASP 이벤트(노티파이 클래스 · 태그) | 부르는 함수(인터페이스 · 시그니처) | 좌/우 판정 | 대응(Step / Land / 무시) | 끄는 방법(확인 여부) | 발 접지와 시차 중앙값 ms | 걸음당 수 | 비고(발 이외 폴리 등) |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## 6. Offset Root Bone 거리 · 80 cm 통로 · 포토 구도 · 포털 · 텔레포트 (R21-7)
규칙: V-08b 판정은 없다(기록). V-15의 해당 항목은 wp19 §B4("통합 확인(점수 밖, 실패하면 기본 전환 차단)" — 로스터 교체, 포털 왕복, `golmok.travel` 뒤 메시–캡슐 어긋남, 포토 모드 구도·keep-height, 80 cm 통로 관통 0, 발소리 동기·이중 재생 없음, 세이브 복원; Offset Root Bone 메시–캡슐 최대 거리는 기록)이다. 여기서는 그 사전 자료를 만든다.
- [ ] **6-1 Offset Root Bone**(§1 틱 재사용): 장면별로 다음을 적는다.
  - |root 뼈 XY − 캡슐 XY| 최대·p95
  - yaw 차 최대
  - 정지 뒤 5 cm 안으로 돌아오는 시간
  - 대상: `c2b`, `p0~p2`, Manny 시각(§3-2)
- [ ] **6-2 80 cm 통로**:
  - 벽: V-11·Locomotion과 같은 큐브(벽 중심 (−4700, −5565)·(−4700, −5435), 600×50×250 cm). 비transient로 두고 저장하지 않는다.
  - GASP 폰 캡슐 반지름을 적는다.
  - 들어가면 걷기·달리기로 지나가며 손·팔·발 뼈 ↔ 벽면 최소 거리와 벽면을 넘은 틱 수를 적는다. `BP_V08b_H45`(캡슐 33.6)도 같은 방법으로 잰다.
  - 못 들어가면 그 사실을 적는다(성인 84 cm 캡슐 ①과 같다).
- [ ] **6-3 포토 구도**: S2 정지 직후(Offset 최대)와 아이들에서 `golmok.photo 1`을 켜고 `golmok.hud 0` 기본 구도로 찍는다. 포토 모드는 `AGolmokPlayerController`가 필요하고, `BP_GolmokGameMode_AnimEvalB`는 `AGolmokGameMode` 파생이다. 다음을 적는다.
  - 메시가 화면 안인지(머리·발 뼈 화면 투영, §12 #15)
  - 캡슐 앵커와 메시 중심의 차이
  - 참고: T23(로스터 카메라 소켓 Z, D-018 진행 기록 (2))은 우리 카메라 대상이라 GASP 카메라 시험에는 적용되지 않는다. 플레이 구도는 T23 뒤 V-15에서 보고, 여기서는 포토 앵커만 본다.
- [ ] **6-4 포털**: `L_ZoneTest` door_1 앞 140 cm에서 W 2.4 s로 들어가고 S 3.2 s로 돌아온다. 2회 왕복한다(V-11 C 코스, S는 돌아서기). 게임 모드는 World Settings 덮어쓰기로 바꾸고 저장하지 않는다(§12 #12). 틱당 캡슐 이동 최대, 뼈의 캡슐 대비 상대 이동 최대(팝), inside/interior 플래그를 적는다.
- [ ] **6-5 텔레포트**(wp19 §D #7 미리):
  - Python `set_actor_location(…, teleport=True)`로 5 m 옮긴다. `golmok.travel`이 GASP 폰에서 되면 그것도 한다.
  - 직후 메시–캡슐 거리, 0 근처로 돌아오는 시간, 메시가 미끄러져 오는지(녹화)를 적는다.
  - 가능하면 애님 재초기화(§12 #11) 뒤 같은 측정을 한다. `reinit_anim_on_teleport`의 근거가 된다.

| 항목 | 조건 | 값 | 관찰 |
|---|---|---|---|
| Offset 최대 / p95 / yaw / 복귀 s | c2b · p0 · p1 · p2 · Manny | | |
| 통로 (캡슐 반지름, 통과, 최소 거리, 넘은 틱) | GASP 폰 · H45 | | |
| 포토 (메시 화면 안, 앵커–메시 차) | 정지 직후 · 아이들 | | |
| 포털 (틱당 최대, 팝, 플래그) | | | |
| 텔레포트 (직후 거리, 복귀 s, 재초기화 효과) | | | |

## 7. 계단 접지 지표 (P11-5)
**규칙(D-021 진행 기록 2026-10-04 (7)·(8), 원문)**
> (7) V-15 기록 항목(채점 밖): S5 계단 접지를 V-11 정의(ball 소켓 − 디딤판, 상승 p10 / 하강 p90)로 기록하고, proxy135 정속 미끄러짐도 같은 지표로 기록한다. 지표 정의는 V-08b 드라이버·지표 `tools/` 커밋에서 WP-19 `PlantedSlip`과 하나로 맞춘다(P11-10). … (8) 발 IK 게이트(P11-5): ②c(WP-19 통합본)가 ① 대비 계단 접지를 개선하지 못하면 18b 전에 발 IK 후속(GASP FootPlacement 설정 또는 다리 IK)을 연다. V-15 통과 기준(합계·S1·S2 미끄러짐·fps)은 바꾸지 않는다.

V-08b 판정은 없다. 게이트 (8)의 사전 자료다.
- [ ] **정의**(§9 `stair_contact`):
  - d = ball 소켓 z − 그 XY의 디딤판 윗면 z
  - L_Dev 계단: x 500~800에서 17 × (⌊(x − 500) / 30⌋ + 1) cm, 랜딩 x 800~1100에서 170 cm, 폭 y −1600~−1400(`setup_dev_level._build_course`)
  - 25 cm 턱: 25 cm
  - 지지 발 판정은 V-11 스크립트 그대로 옮긴다. 스크립트가 없으면 "틱마다 두 ball 중 d가 작은 쪽"으로 정하고 그렇게 적는다.
  - 상승 p10, 하강 p90, 중앙값, |d| > 3 cm 틱 비율을 낸다.
- [ ] 대상: `c1`, `c2b`(하행 뒷걸음 — 참고), `p0~p2`, Manny 시각, `h45_*`. V-11 값(상승 p10 −7~−12, 하강 p90 +10~+13 cm)과 V-08 ②b S5 p10 −14.1 cm를 옆에 둔다.

| 조건 | 상승 p10 cm | 하강 p90 cm | 중앙값 | \|d\| > 3 cm % | 25 cm 턱 p10~p90 | 메모 |
|---|---|---|---|---|---|---|
| | | | | | | |

## 8. 패키지 스모크 (D-021 조건 3)
**규칙(D-021 Experimental 허용 조건 3, 원문)**
> Development·Shipping 패키지 스모크를 통과한다.

**규칙(D-018 진행 기록 2026-10-04 (4), 원문)**
> 패키지 실행 규칙(P11-3, C-07 재발): PC 패키지 스모크는 고정 출력 경로(Claude 레인 `package.ps1` `GOLMOK_PKG_DIR`)를 쓴다. 방화벽 창이 뜨면 소유자가 취소한다(게임은 인바운드가 필요 없다). `DefaultEngine.ini`(핫스팟)는 바꾸지 않는다.

- [ ] **출력 경로**: `$pkg = $env:GOLMOK_PKG_DIR`을 쓴다(§0에서 설정, [pc-setup.md §2a](pc-setup.md)). 비어 있으면 §0 단계를 먼저 한다. A·B는 구성별 하위 폴더를 `-OutDir`로 명시한다(아래 명령). 하위 폴더도 새 exe 경로라 Development 첫 실행에서 방화벽 창이 뜰 수 있다(Shipping은 TraceLog 리스너가 없다, pc-setup §2a).
- [ ] **A(필수, D-021 조건 3)**: §4-3 최소 집합 상태에서 Development와 Shipping 둘 다 만든다.
  - 명령: `.\tools\ue\package.ps1 -Config Development -OutDir $pkg\v08b-dev`, `.\tools\ue\package.ps1 -Config Shipping -OutDir $pkg\v08b-ship`. `/Game/GolmokLocal`은 상시 쿡이라 스모크 맵과 그 참조(ABP·UEFN·Manny·리타깃)가 들어간다.
  - 실행: `Golmok.exe /Game/GolmokLocal/V08b/L_V08b_PluginSmoke -windowed -ResX=1920 -ResY=1080 -forcelogflush`(`-log` 금지: 콘솔 창이 포그라운드를 가져간다).
  - 확인: 아이들 포즈 스크린샷, 30 s 실행 뒤 정상 종료. 패키지 로그에 플러그인·모듈 로드 실패, `Failed to load`, Ensure가 0이다.
  - Shipping에서 맵 인자가 먹지 않으면(§12 #14) L_Dev 시작·쿡 로그의 스모크 맵 포함·로그 오류 0만 본다.
  - 패키지 크기를 적는다.
- [ ] **B(참고, 선택)**: ②b′ 시험 설정(플러그인 21개)으로 Development 1회 만든다. `L_Dev_AnimEvalB` 사본을 `/Game/GolmokLocal/V08b/`에 두어 쿡하고, 실행해 W 5 s 걷기가 애니메이션되는지 본다. **불허 플러그인이 든 구성이라 D-021 조건 판정에 쓰지 않는다.**
- [ ] **C(선택)**: V-11 패키지 재실행 묶음(wp18a §14-6: W 걷기 발소리 1회, 첫 화면 Manny·`Character mesh … not found` 없음, `golmok.character list|proxy135|quinn|manny`)을 A의 Development 패키지(L_Dev 시작)로 해도 된다. "최소 플러그인 켬"을 함께 적는다. 플러그인 없는 main 기준으로는 ①·②가 2026-10-09 V-11 재실행에서 끝났고 ③ quinn은 V-17 §5 몫이다([#123](https://github.com/wooklym/golmok/pull/123) 쿡 훅). 결과는 §13에 적고 오케스트레이터가 옮긴다.
- [ ] **방화벽**: 새 exe 경로에서 Windows 방화벽 창이 뜨면 **누르지 않고** 소유자에게 넘긴다. 소유자는 **취소**를 누른다(또는 그 exe에 차단 규칙을 미리 만든다, pc-setup §2a). 창이 포그라운드를 막으면 SendInput 단계를 멈추고 기록한다. 이 절은 GUI 묶음의 마지막이다.
- 패키지 창의 콘솔(` 키)은 이 PC에서 SendInput으로 열리지 않았다(2026-10-09 V-11 재실행, [wp18a §14-6](pc-verify-wp18a.md)). C의 `golmok.character …`처럼 콘솔 명령이 필요하면 실행 인자 `-ExecCmds=…`로 준다.

| 구성 | 쿡 | 실행 | 로그 오류 | 크기 | 스크린샷 |
|---|---|---|---|---|---|
| A Development | | | | | |
| A Shipping | | | | | |
| B Development(참고) | | | | | |

## 9. 드라이버·지표 스크립트 `tools/` 커밋 (P11-10, R21-10, V-15 전제)
**규칙(D-021 진행 기록 2026-10-04 (7), 원문 일부)**
> 지표 정의는 V-08b 드라이버·지표 `tools/` 커밋에서 WP-19 `PlantedSlip`과 하나로 맞춘다(P11-10).

V-15 전제(wp19 §B0): "V-08b 드라이버·지표 스크립트가 `tools/`에 커밋됨".

### 9-1 파일
| 파일 | 내용 |
|---|---|
| `tools/golmok_tools/locomotion_metrics.py` | 순수 지표(표준 라이브러리 + numpy): `planted_travel_cm`·`planted_slip_cm_per_m`(헤더와 같음), `slip_frames`, `legacy_v11_slip`, `stair_contact`(L_Dev 계단·턱 높이 함수 포함), 표 B 반응, Offset Root Bone, 돌아서기 시간, 벽 최소 거리, 관통 근사. CLI `python -m golmok_tools.locomotion_metrics report <ticks.json>… [--markdown]`, `blind`, `unblind`(§10). 핫스팟 `pyproject.toml`은 고치지 않는다. console script 없이 `python -m`으로 쓴다(`audio_analysis` 선례) |
| `tools/tests/test_locomotion_metrics.py` | 합성 데이터: 디딘 발 0 cm/m, 일정 미끄러짐 n cm/m, 들린 발·공중 제외, 계단 높이 함수·p10/p90, 90 % 도달·정지 거리, 블라인드 키 왕복·장면별 다른 순열. `fixtures/ue/locomotionmath_driver.cpp`의 `planted` 명령과 무작위 대조(컴파일러가 없으면 skip — `test_ue_locomotion_math.py` 방식, 드라이버 파일은 고치지 않음) |
| `unreal/Golmok/Content/Python/golmok/locomotion_pure.py` | 순수: 장면 S1~S8 정의(시작 위치·방향·키 타임라인 — 찾은 V-08 드라이버 값), L_Dev 코스 상수, 틱 JSON 스키마·기록기 |
| `unreal/Golmok/Content/Python/golmok/locomotion_driver.py` | 얇은 `unreal` + ctypes 어댑터: Slate post-tick 단계 진행, PIE 시작, 순간이동 배치, Win32 SendInput 키·마우스, 틱마다 캡슐·CMC·뼈 샘플, ffmpeg 시작·종료 |
| `tools/tests/test_ue_python_locomotion_pure.py` | 장면 정의·스키마 단위 테스트 |

파일 이름은 바꿔도 된다. 다만 "순수 모듈 + 얇은 어댑터" 구성은 유지한다(`gasp_pure`/`gasp_import` 선례).

틱 JSON(`schema: golmok-locomotion-ticks/1`)의 최소 필드:
- 장면 수준: `scene`, `condition`, `pawn_class`, `profile`, `speeds`, `map`
- 틱마다 `ticks[]`: `t`·`dt`·`keys`·`capsule`(xyz)·`yaw`·`half_height`·`on_ground`·`vel`·`cmc`(§1-1 필드)·`bones`
- `bones`: `root`·`pelvis`·`head`·`foot_l/r`·`ball_l/r`·`hand_l/r`·`lowerarm_l/r` 월드 좌표, 시각 메시가 있으면 `visual_bones`

### 9-2 정의 통일
| 지표 | 통일 정의(이 커밋) | V-08 표 A | V-11 §14-5 | WP-19 헤더 |
|---|---|---|---|---|
| 디딘 발 미끄러짐 `planted_slip` | `foot_l`·`foot_r` 뼈마다 기준 = 장면 안 캡슐 접지 틱의 그 뼈 최저 z. 디딤 = z ≤ 기준 + 2.5 cm ∧ 캡슐 접지(연속 두 틱 모두). 디딤 연속 틱 사이 수평 이동을 합하고 두 발을 더해 캡슐 수평 이동(m)으로 나눈다. 평지 장면(S1~S4·정속 구간)만 쓴다 | "평지 최저값 + 2.5 cm"(뼈 명시 없음) | 기준 = 평지 프레임 p2, 틱마다 디딘 소켓(발목·앞꿈치) 최솟값 | `PlantedTravelCm`·`PlantedSlipCmPerM` = 통일 정의(GaspSmoke·V-15 §B2) |
| `slip_frames`(보조) | 디딘 발 수평 속도 > 15 cm/s 틱 수 | — | 같음 | — |
| `legacy_v11_slip`(보조) | V-11 정의 그대로(P11-6 연속성) | — | 원본 | — |
| 계단 접지 `stair_contact` | §7 | S5 앞꿈치 − 평지 | ball − 디딤판, 상승 p10 / 하강 p90 | — |
| 반응(표 B) | 키 입력부터 캡슐 수평 속도 ≥ 0.9 × 목표 속도까지 시간. 키를 뗀 뒤 < 1 cm/s까지 시간·거리 | 같은 뜻 | — | — |
| Offset Root Bone | root 뼈 XY ↔ 캡슐 XY 거리, yaw 차(메시 기본 yaw −90 보정) | — | — | — |

**수락(커밋 전)**:
- (a) 헤더와 무작위 대조가 1e-9 안에서 같다.
- (b) V-08 원자료(`C:\UE\v08_recordings\scenes\`)를 새 모듈로 다시 계산해 표 A가 ±0.1로 나온다. 안 나오면 두 값을 다 적고 차이 원인(뼈·기준)을 §13에 적는다. V-15의 ① 기준은 같은 세션 재측정이라 이 차이로 막히지 않는다.
- (c) V-11 원자료로 계산한 `legacy_v11_slip`·계단 값이 V-11 §14-5 표와 같다.
- 원자료를 못 찾은 항목은 "미대조"로 적는다.

### 9-3 커밋
- [ ] 별도 커밋 `V-08b: tools — 로코모션 드라이버·지표(P11-10)`에는 위 파일만 넣는다. 녹화·틱 원자료는 넣지 않는다. 작은 합성 fixture는 넣어도 된다. GASP 에셋 이름·경로 문자열은 커밋해도 된다(WP-19 "주의").
- [ ] 게이트(설정 stash 뒤): `cd tools; ruff check .; ruff format --check .; $env:PYTHONUTF8=1; pytest -q; python scripts/check_repo.py` → `git diff --check`.
- [ ] PR 본문에 "`V-08b: tools` 커밋은 클라우드 Opus 적대 코드 리뷰 대상(V-15 §B0 전제)"이라고 적는다.

## 10. 블라인드 채점 — 다른 Opus 세션
근거: V-15 기준 "같은 메시·같은 카메라·블라인드 채점", WP-19 §15-3 "채점은 시험 세션과 다른 Opus 세션이 순서를 섞은 녹화로 블라인드로 하고, 소유자 채점이 있으면 우선한다", D-021 후속 "다른 Opus 세션 블라인드 채점".
- [ ] **세트 A**(§1): `c1`·`c2b`·`p0`·`p1`·`p2` × S1~S7(S8). 항목은 V-08 §5의 1~5다: 1 자연스러움 S1~S4 · 2 발 미끄러짐 S1 S2 S3 · 3 전환 S2 S7 · 4 계단·경사 S5 S6 · 5 조작감(S8, 패드 없으면 키보드 S1~S3). 1~5점이다(5 = 실제 사람처럼 자연스럽다, 3 = 눈에 띄지만 거슬리지 않음, 1 = 몰입을 깸).
- [ ] **세트 B**(§3-3): `h45_rt`·`h45_add`·`h45_key`. 항목은 자연스러움·귀여움·성인 보폭 느낌(5 = 몸에 맞는 보폭, 1 = 성인 보폭이 그대로 보임)의 1~5점과 팔–머리/배 관통 횟수다.
- [ ] **1. 섞기**(PC 세션): `python -m golmok_tools.locomotion_metrics blind C:\UE\v08b_recordings\rec --out C:\UE\v08b_recordings\blind --key C:\UE\v08b_recordings\key\key.json --seed <임의>`. 결과물:
  - 장면마다 조건 순서를 다르게 섞은 `S1_A.mp4`…
  - 장면별 나란히 영상(섞은 순서)
  - 클립별 프레임 시트: 입력 시각 기준 8장, 캐릭터 중심 크롭
  - 같은 글자를 붙인 익명 지표 표

  `key.json`의 sha256을 §13에 적고, **채점 전에** `V-08b: 블라인드 키 해시`로 커밋한다.
- [ ] **2. 채점 세션**: 시험 세션과 다른 Opus 5.5 세션이 한다.
  - 기본: 이 PC의 새 Claude Desktop 세션(소유자나 오케스트레이터가 연다).
  - 열 수 없을 때: 이 세션이 Agent 도구로 새 서브에이전트(Opus 5.5)를 띄우고 아래 프롬프트만 준다. 조건 이름·수치·이 문서는 주지 않는다.
  - 어느 쪽이었는지 §13에 적는다.

```text
너는 Golmok 캐릭터 애니메이션 블라인드 채점자다. C:\UE\v08b_recordings\blind\ 만 읽는다.
key\ 폴더, 저장소(문서·git log·STATUS), 다른 녹화 폴더는 열지 않는다. 조건 이름을 추측해 적지 않는다.
장면(S1…)마다 클립 A·B·C…를 비교한다(ffmpeg로 프레임을 더 뽑아도 된다). 익명 지표 표는 참고만 한다.
세트 A: 항목 1 자연스러움(S1~S4), 2 발 미끄러짐(S1 S2 S3), 3 전환(S2 S7), 4 계단·경사(S5 S6),
5 조작감(S8, 없으면 키보드 S1~S3 입력 반응)을 1~5점(5 = 실제 사람처럼 자연스럽다, 3 = 눈에 띄지만
거슬리지 않음, 1 = 몰입을 깸)으로 매긴다.
세트 B: 자연스러움·귀여움·성인 보폭 느낌(5 = 몸에 맞는 보폭, 1 = 성인 보폭이 그대로 보임)을 1~5점으로,
팔–머리/배 관통을 횟수로 적는다.
점수마다 근거를 한 줄씩 단다. 결과를 blind\scores.json(글자 → 항목 → 점수·근거)과 blind\scores.md에 쓴다.
```

- [ ] **3. 해제**: 채점이 끝나면 PC 세션이 `unblind`로 점수를 조건에 붙이고 §1-7 규칙을 기계적으로 적용한다. 소유자 채점이 들어오면 그것이 우선한다. §13에는 둘 다 적는다.

| 조건 | 1 | 2 | 3 | 4 | 5 | 1~5 합 | 채점자 | 소유자(있으면) |
|---|---|---|---|---|---|---|---|---|
| c1 / c2b / p0 / p1 / p2 | | | | | | | | |

| 변형 | 자연스러움 | 귀여움 | 성인 보폭 느낌 | 관통 횟수 | 채점자 | 소유자(있으면) |
|---|---|---|---|---|---|---|
| h45_rt / h45_add / h45_key | | | | | | |

## 11. 인계

### 11-1 19b가 쓰는 것([`pc-verify-wp19.md`](pc-verify-wp19.md) A절)
| 19b | V-08b 출처 | 형식 |
|---|---|---|
| §A2 플러그인 | §4 표·`.uproject` 줄·`ALLOWED_PLUGINS` 추가 요청 | 표 + JSON 줄 |
| §A3 `add-gasp` | §3-1 경로 확인 표(`closure.json` estimated 루트의 실제 경로), §4-1 폐포 패키지 수 | 표 |
| §A4-2 BPI 함수 | §4-2 표(미리 채움), ABP 캐스트 유무 | 표 |
| §A5 발 이벤트 | §5 표(대응·끄는 방법·함수 이름) | 표 |
| §A7 `animation.json` | §1-3·§1-7 값과 선택, §3-2 시각 메시·애님 클래스·부착 방식·`TargetSkeleton`(wp19 §D #3·#19) | 아래 JSON |
| §A8 텔레포트 | §6-5 관찰(wp19 §D #7) | 표 |

```json
"movement_profiles": {
  "p1": {"max_acceleration": 0, "braking_deceleration_walking": 0, "ground_friction": 0,
         "braking_friction_factor": 0, "use_separate_braking_friction": false, "braking_friction": 0},
  "p2": {"max_acceleration": 0, "braking_deceleration_walking": 0, "ground_friction": 0,
         "braking_friction_factor": 0, "use_separate_braking_friction": false, "braking_friction": 0}
},
"gasp": {"movement_profile": "p0|p1|p2 (§1-7 결과, 해당 없음이면 p0)"}
```
(0·false는 자리표시다. §1-3 값으로 바꾼다. P2가 가변이면 이 형식 대신 게이트별 표를 넘긴다 — §1-2.)

### 11-2 V-15와 그 밖에서 쓰는 것
- wp19 §B0 전제: §9 `tools` 커밋(드라이버·통일 지표·블라인드 도구).
- §B2: 이번 `c1`·`c2b` 값과 측정 방식, §7 계단 기록(P11-5), §3-3 소형 캐릭터 slip 기록(P11-6, proxy135는 V-15에서 같은 지표로).
- §B3: §10 절차를 그대로 쓴다.
- §B4: §6 관찰(Offset 최대 거리·통로·포토·포털·텔레포트).
- §B7: §8 크기·로그 기준선.
- Astra T12·18b(오케스트레이터 경유): §3-2 Manny 시각 경로(`characters.json` 갱신은 Astra 레인 — PC는 고치지 않는다), §3-3 결과(D-018 ② 입력).
- 4.5등신이 미실행이면 V-08c 카드가 필요하다고 적는다.

### 11-3 STATUS 문안(PC 세션이 채운다)
- 시작: `| V-08b | GASP 통합 전 PC 실험(D-021) | 🔵 진행 중(<날짜>, 워크트리 <이름>, 브랜치 pc/v08b-gasp-experiment, main <SHA>) | <기존 메모 유지> |`
- 끝: `| V-08b | GASP 통합 전 PC 실험(D-021) | 🟢 완료(<날짜>) — 프로파일 <p0|p1|p2|해당 없음> · 4.5등신 <통과|미통과|미실행> · 플러그인 최소 집합 <n>개(D-021 허용 안 <예/아니오>) | <워크트리>, [PR #<번호>](…). §1 S1/S2 slip c1 <a>/<b> · 선택 <x>/<y> cm/m, 1~5 합 <…>(블라인드: <세션/서브에이전트>), §2 S3 돌아서기 <s>, §3 Manny 시각 <(a)/(b)>·H45 정속 걷기 <v> ≤ 기준 <c1>, §4 표, §5 끄는 방법 <…>, §6 Offset 최대 <cm>, §7 계단 p10/p90 <…>, §8 Dev·Shipping <✅/✗>, §9 tools 커밋 <SHA>. 인계: 19b §A2·§A3·§A4-2·§A5·§A7·§A8, V-15 §B0~§B7 |`
- 세션 로그: `| <날짜> | Claude Desktop 워크트리 <이름> (PC, 브랜치 pc/v08b-gasp-experiment) | Opus 5.5 | V-08b GASP 통합 전 실험 | <요약> |`

## 12. [미확인] UE API · GASP 판 항목
| # | 항목 | 가정 | 틀렸을 때 대안 | 확인 | 결과 |
|---|---|---|---|---|---|
| 1 | GASP 폰 가감속 설정 위치 | CDO 기본값 또는 자식에서 오버라이드할 수 있는 BP 함수에서 정한다 | 자식 Event Tick에서 부모 호출 뒤 다시 쓴다. 그래도 덮이면 폰 BP를 로컬 Save-As 사본(`Golmok_AnimEval/V08b/`)으로 만들어 사본만 고친다(원본 무수정). 어느 쪽인지 적는다 | §1-1·§1-4 게이트 | |
| 2 | 회전 모드 전환 | 폰 변수(스트레이프 여부 등) 하나로 돌아서기가 된다 | CMC `bOrientRotationToMovement`=true·`bUseControllerDesiredRotation`=false·RotationRate 540을 자식이 매 틱 쓴다 | §1-4 (b) | |
| 3 | 넘기 끄기 | 넘기 진입 함수를 자식에서 오버라이드해 false | 못 끄면 S7을 평지 점프 S7′로 바꾸고 표시 | §1-5 | |
| 4 | 폴리 인터페이스 오버라이드 | 노티파이가 폰 인터페이스 함수를 부르고 자식 BP가 그것을 오버라이드할 수 있다 | 5-1 정적 목록 + 5-3 녹음으로 시점·개수를 잰다. 직접 재생이면 보고 | §5 | |
| 5 | GASP 리타깃 구성 | `BP_Manny` 시각 메시는 소스의 자식이고 `Retarget Pose From Mesh`가 Use Attached Parent로 소스를 찾는다 | 컴포넌트 태그·명시 소스면 그 방식을 적는다(19b `AGolmokGaspCharacter` PC fix 근거). `DDCvar.VisualOverride` 값 대응도 적는다 | §3-1 | |
| 6 | 우리 `SKM_Manny_Simple` + GASP IK Retargeter | 같은 뼈 이름이면 GASP 사본 대신 써도 된다 | 안 되면 GASP 사본으로 하고 이유(스켈레톤 자산 불일치 등)를 적는다 | §3-2 | |
| 7 | 4.5등신 프록시 제작 | 5.8 Skeletal Editor로 기준 포즈 비율 편집·재바인딩이 된다(GUI) | 우리 스크립트 glTF 블록 휴머노이드 → Interchange skinned 임포트. 둘 다 2 h 안에 안 되면 V-08c | §3-3 | |
| 8 | IK Rig 자동 생성 | 에디터 "Auto Create Retarget Chains"(또는 Python `IKRigController`)가 마네킹 이름 체인을 만든다 | 체인을 손으로 만든다 | §3-3 | |
| 9 | 노티파이 조회 | `unreal.AnimationLibrary`로 시퀀스별 노티파이 이벤트·클래스를 읽는다 | 에셋 레지스트리 태그나 GUI 표본 조사(대표 시퀀스 10개) | §5-1 | |
| 10 | PIE 뼈 샘플 | `get_socket_location`·`get_bone_location`(월드)을 Slate post-tick에서 매 틱 읽는다(V-08·V-11 [2차]) | — | §0 | |
| 11 | 텔레포트 재초기화 | Python에서 애님 재초기화(`InitAnim`에 해당하는 노출 함수)를 부를 수 있다 | 같은 애님 클래스를 다시 지정하거나 생략하고 "미확인"으로 적는다 | §6-5 | |
| 12 | 저장 안 한 World Settings | PIE가 에디터 월드의 저장 안 한 게임 모드 덮어쓰기를 쓴다 | 맵을 로컬 Save-As(`Golmok_AnimEval/V08b/`)해서 쓴다 | §6-4 | |
| 13 | PIE 중 폰 교체 | Python 스폰 + `possess`로 GASP 폰 카메라·입력이 초기화된다 | 조건별 게임 모드 BP + 에디터 재시작 | §1-4 | |
| 14 | Shipping 맵 인자 | Shipping exe가 명령줄 맵 URL을 받는다 | 쿡 로그에 맵이 들어갔는지·L_Dev 시작·로그 오류 0만 본다 | §8 | |
| 15 | 화면 투영 | `GameplayStatics.project_world_to_screen`(또는 `PlayerController.project_world_location_to_screen`)이 Python에서 된다 | 스크린샷에서 눈으로 판정한다 | §6-3 | |
| 16 | `/Script` 의존 | 에셋 레지스트리 패키지 의존에 `/Script/<모듈>`이 나온다 | 최소 집합 후보로 켰다 껐다 하며 ABP 컴파일 로그의 누락 모듈을 본다(§4-3) | §4-1 | |
| 17 | GASP 판 | `C:\UE\GASP_58`이 V-08 때와 같다(Vault 2026-08-18 판) | 다르면 그대로 진행하고 "GASP 갱신"을 적는다. V-08 수치는 판이 다른 참고치가 된다. 19b `expected.json` source_digest와 대조 | §0 | |
| 18 | DDCvar 적용 | b61eea0의 `DefaultEngine.ini` DDCvar 27개가 GASP ABP에 보인다(`DDCvar.FootPlacementMode` = 1) | 콘솔로 값을 확인하고 다르면 측정 전에 고친다(§1 비교의 전제) | §0 | |

## 13. 결과 (PC 세션이 작성)
(비어 있음 — 실행 정보: 날짜·워크트리·기준 main SHA·GASP 식별(§0)·찾은 드라이버 경로; 사전 등록 값 커밋 SHA; 블라인드 키 sha256·채점 세션 종류; 각 절 결과 표; 막힌 것; 커밋 목록)

**정리 체크리스트**
- [ ] 시험 설정 되돌림: `git checkout -- unreal/Golmok/Golmok.uproject unreal/Golmok/Config/DefaultEngine.ini`, 그리고 `unreal/Golmok/Config/DefaultGameplayTags.ini` 제거(stash가 남았으면 `git stash drop`).
- [ ] 로컬 GASP 사본(Migrate 경로 폴더)과 `Content/Golmok_AnimEval/V08b/`·`Content/GolmokLocal/V08b/`를 `C:\UE\v08b_backup\Content\`로 **옮긴다**(삭제하지 않는다). 그래야 같은 워크트리에서 나중에 `add-gasp`가 잔재로 멈추지 않는다.
- [ ] `git status --porcelain --untracked-files=all`에 의도한 파일만 남았는지 보고, `python tools\scripts\check_repo.py` → `OK (…, gasp)`.
- [ ] STATUS V-08b 행(§11-3)과 세션 로그를 쓰고 PR을 연다(본문에 `tools` 커밋 리뷰 요청, "GASP 원본·설정 커밋 없음").
