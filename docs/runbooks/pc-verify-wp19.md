# WP-19 — GASP 모션 매칭 로코모션 통합 PC 런북 (A절 19b 바인딩 · B절 V-15 통합 검증)

상태: 🟡 19a 코드 완료·PC 미검증(클라우드는 UE를 빌드할 수 없다). 스펙·결과: [`plan/WP-19-gasp-locomotion.md`](../plan/WP-19-gasp-locomotion.md), 결정: [D-021](../DECISIONS.md). A절(19b)은 **D-021 발효(소유자 라이선스 원문 재확인)와 V-08b 뒤**, B절(V-15)은 19a·19b·19c 병합 뒤다. A절 전이라도 §A1(① 회귀·새 자동화 4개)은 19a 병합 직후 아무 PC 카드에서 돌릴 수 있다.

**절대 규칙**
- **`git add -A` 금지.** GASP 원본·수정본, `Content/GASP/`·`Content/GolmokLocal/`의 `.uasset`, `Config/Golmok/local/`(매니페스트·DDCvar), `Config/Tags/GASP*.ini`, `Config/DefaultGameplayTags.ini`는 커밋하지 않는다(Fab EULA §5(a), 소유자 사실 확인 R21-11 전 기본값 "로컬 전용"). 커밋할 파일은 이름으로 하나씩 `git add <path>` 한다. `.gitignore` `[WP-19 hook]`이 막고, `python tools/scripts/check_repo.py`의 `gasp` 가드가 추적 중·추가 가능한 경로를 실패로 보고한다.
- GASP 에셋은 **고치지 않는다**(무수정 원칙). GASP 원본 프로젝트(`C:\UE\GASP_58`)도 열어서 저장하지 않는다(`add-gasp`는 읽기만 한다).
- 라이선스 판단을 새로 하지 않는다. 확인이 필요하면 STATUS "결정 필요"의 소유자 항목으로 올린다.
- 이동 의미(걷기 180·달리기 500·로스터 145/380·돌아서기 540°/s·점프 90 cm·CMC)는 바꾸지 않는다. 바꿀 수 있는 것은 `animation.json` 가감속 프로파일뿐이다(D-021).

## 0. 19a가 바꾼 파일

| 파일 | 내용 |
|---|---|
| `Source/Golmok/Animation/GolmokLocomotionMath.h` (새) | 순수 규칙(`<cmath>`·`<array>`만): `ClassifyGait`(|MaxWalkSpeed − Run| ≤ 0.5 → Run), `MapMovementMode`(Falling만 InAir), `Intent`(수평 가속도 ÷ 최대 가속도, 길이 ≤ 1, 0.05 미만 0), `UpdateMoving`(10 cm/s 이상 또는 의도 → Moving, 3 cm/s 미만·의도 0 → Idle), `LandingWindow`, `IsTeleportJump`, `ValidateProfile`·`ValidateStateSettings`, `PlantedTravelCm`·`PlantedSlipCmPerM`(V-08 표 A). g++ 교차검증 `tools/tests/test_ue_locomotion_math.py` |
| `Source/Golmok/Animation/GolmokLocomotionStateComponent.{h,cpp}` (새) | `UGolmokLocomotionStateComponent`: `TG_PrePhysics`(CMC 뒤, `GetMesh()` 앞) 틱에서 `FGolmokLocomotionState` 계산·캐시, `BlueprintPure`·`BlueprintThreadSafe` 게터(복사만), `LandedDelegate`·`MovementModeChangedDelegate`(`OnRegister`/`OnUnregister`), 텔레포트 감지 → 다음 틱 `GetMesh()->InitAnim(true)`, `NotifyFootEvent`(BlueprintCallable) → 네이티브 `OnFootEvent` |
| `Source/Golmok/Animation/GolmokGaspCharacter.{h,cpp}` (새) | `AGolmokGaspCharacter : AGolmokCharacter`(19b BP의 C++ 부모): 컴포넌트, 시각 메시 슬롯 `VisualMesh`(`GetMesh()`의 자식, 기본 비어 있음), `SetVisualOverride`/`ClearVisualOverride`, `PostInitializeComponents`에서 `gasp.movement_profile` 적용 |
| `Source/Golmok/Animation/GolmokAnimationConfig.{h,cpp}` (새) | namespace `GolmokAnimation`: `animation.json` 엄격 파서, 유효 모드(명령줄 > 콘솔 > 파일), 폰 해결 규칙 1~6과 폴백 사유, 로스터 질의 `RequiresGaspPawn`/`PawnSupportsGasp`, DDCvar 파서·등록, 테스트용 `FScopedConfigOverride` |
| `Source/Golmok/Animation/GolmokAnimationSubsystem.{h,cpp}` (새) | `UGolmokAnimationSubsystem`(Game·PIE): DDCvar 등록, 폴백 Warning 월드당 1회, `anim:` HUD 줄, GASP 폰 클래스 비동기 미리 로드, 콘솔 `golmok.anim status | mode <abp|gasp|config> | profile <id> | preview [off]` |
| `Source/Golmok/Tests/GolmokAnimationTest.cpp` (새) | `Golmok.Animation.Config`·`.StateProvider`·`.Fallback`·`.GaspSmoke`(자동화 총수 32 → 36) |
| `Source/Golmok/GolmokGameMode.{h,cpp}` (훅) | `GetDefaultPawnClassForController_Implementation` → `GolmokAnimation::ResolvePlayerPawnClass(…, Super 결과)` |
| `Config/Golmok/animation.json` (새) | mode `abp`, `p0` = 현행 값, `p1`·`p2` = `null`, GASP 경로(일부 [추정] — §A7에서 확정) |
| `Config/DefaultGame.ini` (훅) | 끝 `; [WP-19 hook]` 섹션 `+DirectoriesToAlwaysCook` `/Game/GASP`·`/Game/GolmokLocal` |
| `.gitignore` (훅) | `Config/Golmok/local/`, `Config/Tags/GASP*.ini` |
| `tools/ue/add-gasp.ps1`, `tools/ue/gasp/closure.json`·`expected.json` (새) | 셋업 스크립트, 폐포 루트(원래 GASP 경로), 기대 digest(`null` — §A7에서 채움) |
| `Content/Python/golmok/gasp_import.py`·`gasp_pure.py` (새) | `unreal` 어댑터(migrate/relocate/verify)와 순수 계산 |
| `tools/scripts/check_repo.py` (훅) | `check_gasp_guard`, `GASP_INI_COMMIT_ALLOWED = False` |

고치지 않은 파일: `Player/GolmokCharacter.{h,cpp}`, `Player/GolmokPlayerController.{h,cpp}`, `Golmok.Build.cs`, `DefaultEngine.ini`, `DefaultInput.ini`, `Golmok.uproject`, `Characters/`·`Audio/`(Astra 레인).

폴백 사유 문구(로그 `LogGolmok: Warning: anim: falling back to ABP pawn (<사유>)`, 월드당 1회, HUD `anim: abp (fallback: <사유>)`):

| 규칙 | 사유 |
|---|---|
| 2 설정 파싱 실패 | `animation.json: <파서 오류>` |
| 3 `gasp.pawn_class` 로드 실패 | `GASP pawn class missing — add-gasp / 19b (<pawn_class>)` |
| 4 `AGolmokGaspCharacter` 파생 아님 | `pawn class <class> is not an AGolmokGaspCharacter` |
| 5 BPI 로드 실패 | `GASP pawn interface missing (<content_root>/<pawn_interface>)` |
| 5 BPI 미구현 | `pawn class <class> does not implement <interface> (19b)` |

## A. 19b — PC GUI 바인딩 (브랜치 `pc/wp19b-gasp-binding`)

### A1. 빌드와 ① 회귀 (GASP 없이도, 19a 병합 직후 가능)

```powershell
git pull
.\tools\ue\build.ps1
.\tools\ue\test.ps1 -Filter Golmok.Animation -SetupDevLevel
.\tools\ue\test.ps1 -Filter Golmok.
```
- [ ] 컴파일 성공(경고는 기록). 실패하면 §C 표의 번호로 고치고 `WP-19: PC fix …` 커밋(핫스팟은 훅 줄만).
- [ ] 첫 명령: 4개 전부 `Success`. `Golmok.Animation.GaspSmoke`는 GASP가 없으면 `[Info] GASP not installed — skipped (…)`. `Golmok.Animation.Fallback`은 기대 Warning 1개(`anim: falling back to ABP pawn (GASP pawn class missing — add-gasp / 19b (/Game/GolmokLocal/GASP/BP_Missing.BP_Missing_C))`)를 소비한다.
- [ ] 두 번째 명령: **36개** 전부 `Success`(`pc-verify-wp12.md` §2와 같은 목록 + `Animation` 4개). `Golmok.Player.Movement`·`Golmok.Character.*`·`Golmok.Photo.*`·`Golmok.Audio.*`는 코드 변경 없이 종전과 같아야 한다(① 불변).
- [ ] `StateProvider` 로그에 `[Error]`가 없고, `Info` 줄 `GASP pawn after p0: accel 2048/2048 braking 2000/2000 friction 8.00/8.00 factor 2.00/2.00 separate 0/0 braking friction 0.00/0.00 (pawn/CDO)`가 있다(§D #6 p0 = 엔진 기본값 확인). `W intent (…) length 1.000` 근처, 점프 apex 약 90 cm, `land velocity z` < −300.
- [ ] `Saved/Logs/Golmok.log`에서 `StateProvider` 구간에 `Character mesh '' not found`가 **없다**(§C #14: 파생 C++ 폰이 `[/Script/Golmok.GolmokCharacter]` ini 값을 물려받는지). 있으면 §C #14 대안.
- [ ] 에디터 PIE(L_Dev) 콘솔 `golmok.anim status` → 첫 줄 `mode abp (animation.json) | animation.json ok`, `pawn: /Script/Golmok.GolmokCharacter | last spawn: /Script/Golmok.GolmokCharacter`. HUD(F1)에 `anim: abp` 한 줄.

### A2. 플러그인 (V-08b `.uplugin` 표의 최소 집합, 별도 커밋)
- [ ] V-08b가 기록한 표대로 `Golmok.uproject` `Plugins`에 GASP 로코모션 플러그인만 켠다(D-021 허용: PoseSearch·Chooser·AnimationWarping·MotionWarping·AnimationLocomotionLibrary·BlendStack·CurveExpression·DrawDebugLibrary·MovieSceneAnimMixer·Mover). 의존 플러그인이 더 필요하면 목록을 기록하고 `tools/tests/test_ue_wp19_fixture.py` `ALLOWED_PLUGINS`에 근거와 함께 더한다. 불허(GameplayCameras·ChaosMover·MoverExamples·Locomotor·SmartObjects·GameplayInteractions·MetaHuman·LiveLink·RigLogic·HairStrands)는 켜지 않는다.
- [ ] 커밋 `WP-19: plugins (Golmok.uproject)`(이 파일만). 빌드 → §A1 두 번째 명령 36개 다시 `Success`(플러그인을 켠 ①).

### A3. `add-gasp` (GASP 복사, 로컬 전용)

```powershell
.\tools\ue\add-gasp.ps1 -GaspProject C:\UE\GASP_58
.\tools\ue\add-gasp.ps1 -Verify
git status --porcelain --untracked-files=all
python tools\scripts\check_repo.py
```
- [ ] 세 헤드리스 세션(migrate → relocate → verify)이 끝나고 `add-gasp verify: <n> packages, digest <sha256>`가 찍힌다. `Saved/Golmok/add-gasp/*.json`에 단계별 결과가 있다.
- [ ] migrate 메시지 `closure root not in the GASP project (19b fixes the path): …`가 있으면 그 루트([추정] 경로)의 실제 경로를 GASP 콘텐츠 브라우저에서 찾아 `tools/ue/gasp/closure.json`을 고치고 다시 돌린다(`-Force`).
- [ ] 종료 코드 2(`GASP stays at the Migrate paths`)면 헤드리스 `rename_directory`가 실패한 것이다(§D #4). `animation.json` `gasp.content_root`를 `/Game`으로 바꾸고 `-Verify`를 다시 돈다(스크립트는 이때 검증 전에 멈춘다). 이 경우 `DefaultGame.ini`의 `/Game/GASP` 쿡 줄이 GASP를 덮지 못하므로 패키지(§B7) 전에 PC fix로 쿡 경로를 정한다. `-Force` 재실행은 `Content/GASP`가 있으면 relocate가 "delete Content/GASP before add-gasp -Force"로 멈춘다 — 로컬 `Content/GASP`를 지우고 다시 돈다. 원인(로그의 `rename_directory` 실패 줄)을 §A9에 기록한다.
- [ ] 검증: 패키지 전부 크기·해시 일치, ABP·BPI 클래스 로드, DDCvar **27**, 태그 **39**, `expected.json`은 첫 설치라 `expected.json not filled yet` 경고.
- [ ] `git status`에 GASP·로컬 경로가 **하나도 없다**(무시됨). `check_repo.py` → `OK (…, gasp)`.
- [ ] 에디터를 열고 PIE 전에 Output Log `anim: DDCvars 27/27 present (… registered now)`(§D #5). `Config/Tags/GASP.ini` 태그가 Project Settings > GameplayTags에 보이는지(§D #5).

### A4. BP 바인딩 `BP_GolmokCharacter_GASP` (함수 목록 먼저 기록)
1. 콘텐츠 브라우저 `/Game/GolmokLocal/GASP/`에 Blueprint Class 생성, 부모 `GolmokGaspCharacter`(C++). 이름 `BP_GolmokCharacter_GASP`(= `animation.json` `gasp.pawn_class`). `.gitignore`로 로컬 전용.
2. Class Settings > Implemented Interfaces에 `BPI_SandboxCharacter_Pawn` 추가. **먼저** 인터페이스 함수 목록과 시그니처(반환 구조체·열거형 이름과 멤버)를 아래 표로 기록한다.

   | # | 함수 | 입력 | 반환(구조체/열거형 멤버) | 우리 값 | 비고 |
   |---|---|---|---|---|---|
   | 1 | | | | | |

3. 각 함수: `GetLocomotionStateComponent` → `GetLocomotionState`(또는 필드 게터) → GASP 구조체·열거형으로 변환해 반환. 열거형은 `Select`/`Switch on Enum`으로 **이름으로** 대응시키고 순서(바이트 값)에 기대지 않는다: `EGolmokMovementMode::OnGround/InAir`, `EGolmokGait::Walk/Run`, `EGolmokStance::Stand`, `EGolmokRotationMode::OrientToMovement`, `EGolmokMovingState::Idle/Moving`, 의도 `InputIntent`(Z = 0), 착지 `bJustLanded`·`LandVelocity`. GASP에만 있는 값(Sprint, Crouch, Strafe, 넘기 등)은 기본값을 돌려준다.
4. §13 대안: (a) BPI가 GASP 전용 구조체를 요구하면 BP Make 노드로 만든다. (b) ABP가 BPI 밖에서 GASP 폰 클래스로 캐스트해 필수 값을 읽으면 무수정 원칙으로는 풀 수 없다 → 중단하고 오케스트레이터에 보고(B안·D-021 개정 검토). (d) C++ 네이티브 함수 이름을 BPI에 맞춰 흉내 내는 편법은 쓰지 않는다.
5. 컴파일·저장(로컬). `golmok.anim mode gasp` 뒤 PIE를 다시 시작 → `golmok.anim status` `pawn: /Game/GolmokLocal/GASP/BP_GolmokCharacter_GASP.BP_GolmokCharacter_GASP_C`, HUD `anim: gasp p0 | ground walk idle | intent 0.00 | land …`(스폰 낙하 착지 뒤 초·속도).

### A5. 발 이벤트
- [ ] GASP 폴리 노티파이가 폰 쪽 인터페이스 함수를 부르면 그 구현에서 `GetLocomotionStateComponent → NotifyFootEvent(Kind, bLeft)`(`Step`/`Land`)를 부른다. 경로와 함수 이름을 §A9에 기록한다(T13이 이 경로로 발소리를 구동한다. 이중 재생 차단은 T13).

### A6. T3D 텍스트 (커밋 가능한 재현 수단)
- [ ] 각 인터페이스 함수 그래프를 전부 선택 → Ctrl+C → `tools/ue/gasp/BP_GolmokCharacter_GASP.t3d.txt`에 함수별 절(`# <함수 이름>`)로 붙여 넣어 커밋한다(우리 그래프, GASP 이름만 포함). `.uasset`은 R21-11-4 확인 전 커밋하지 않는다. 다른 PC는 같은 부모·인터페이스로 BP를 만들고 붙여 넣어 재현한다.

### A7. `animation.json`·`expected.json` 확정 (별도 커밋)
- [ ] `gasp.pawn_interface`·`gasp.preview.source_mesh` 등 [추정] 경로를 실제 경로로 고친다(`content_root` 기준 상대 경로).
- [ ] `gasp.preview.visual_mesh`·`visual_anim_class`: 매니 리타깃(V-08 `BP_Manny` + `ABP_GenericRetarget` + IK Retargeter). 타깃 스켈레톤이 GASP의 `UE5_Mannequins` 사본이면 시각 메시도 그 사본을 쓴다. `/Game/…` 절대 경로(우리 매니)나 `content_root` 상대 경로 둘 다 받는다.
- [ ] `movement_profiles.p1`·`p2`에 V-08b 값을 넣고, V-08b 사전 등록 규칙이 고른 프로파일을 `gasp.movement_profile`에 넣는다. **`mode`는 `abp`로 둔다**(기본 전환은 §B8).
- [ ] `tools/ue/gasp/expected.json`에 §A3 verify의 `engine_version`·`package_count`·`digest`를 적는다.
- [ ] pytest(`test_ue_config_animation.py`)·`check_repo.py` 통과 뒤 커밋 `WP-19: 19b 확정 값`.

### A8. 확인
- [ ] `-GolmokAnim=gasp`(또는 `golmok.anim mode gasp`)로 PIE → `golmok.anim preview` → `preview on: … (debug only; the next roster apply replaces it)`. 매니(시각 메시)가 캡슐을 따라 걷고 달린다. `golmok.anim profile p1`·`p2`로 즉시 바뀐다(`profile p1: max_acceleration …`).
- [ ] 텔레포트: `golmok.travel`(또는 포털) 직후 메시가 캡슐 위치에 다시 붙는다. `golmok.anim status`의 `teleports n reinit n`이 오른다. 히치(ms)를 기록한다(§D #7).
- [ ] 헤드리스 `.\tools\ue\test.ps1 -Filter Golmok.Animation` → `GaspSmoke` `[Info] GASP installed: EXECUTED`, `walk 3 s: PlantedSlip ≤ 30 cm/m`, `run 3 s: PlantedSlip ≤ 30 cm/m`, 발 뼈 4개가 움직임, 상태가 Walk/Run을 보고. 값과 발 뼈별 planted travel을 §A9에 적는다.
- [ ] `golmok.anim preview off` → 로스터가 현재 항목을 다시 적용(`preview off; roster: selected manny …`).

### A9. 결과 (19b PC 세션이 작성)
(비어 있음)

## B. V-15 — 통합 검증 (19a·19b·19c 병합·D-021 발효 뒤, 사전 등록 기준)

판정 기준은 [D-021](../DECISIONS.md) 원문 그대로이고 **사후에 바꾸지 않는다**:

> V-15 기준: 같은 메시·같은 카메라·블라인드 채점. 합계 ≥ ① + 4, ≥ ②b − 2. S1·S2 미끄러짐 ≤ ①의 1/2. S3은 돌아서기로 측정. 평균 fps 하락 5 % 이하 또는 60 fps 이상.

### B0. 전제
- [ ] 19a·19b·19c 병합, D-021 발효, V-08b 드라이버·지표 스크립트가 `tools/`에 커밋됨, `add-gasp.ps1 -Verify` 통과.

### B1. 빌드와 자동화
- [ ] 빌드, `test.ps1 -Filter Golmok. -SetupDevLevel` 전부 `Success`, `GaspSmoke` EXECUTED.

### B2. 측정 (같은 드라이버)
- [ ] S1~S7(패드가 있으면 S8)을 ①(매니 + `ABP_Unarmed`), ②c(통합본: 리타깃 매니·우리 카메라·선택 프로파일), ②b(참고: GASP 폰 — 메시·카메라가 다름을 표기)로 잰다. 표 A(디딘 발: 뼈 높이 ≤ 평지 최저 + 2.5 cm이고 캡슐이 땅 위일 때의 수평 이동 ÷ 캡슐 이동 m — `GolmokLocomotionMath::PlantedSlipCmPerM`과 같은 식)·표 B(성능)·표 C(채점)와 녹화를 남긴다.

### B3. 판정
- [ ] ②c 합계 ≥ ① + 4 · ②c ≥ ②b − 2 · S1·S2 디딘 발 미끄러짐 ≤ ①의 1/2 · S3은 돌아서기로 측정 · 평균 fps 하락 ≤ 5 % 또는 ≥ 60 fps(1% low 기록).
- [ ] 채점은 시험 세션과 다른 Opus 세션이 순서를 섞은 녹화로 블라인드로 한다. 소유자 채점이 있으면 우선한다.
- [ ] 이동 의미 불변(180/500/90 cm, 로스터 145/380)은 자동으로 확인한다(`Golmok.Player.Movement`, `Golmok.Character.Locomotion`, `Golmok.Animation.StateProvider`).

### B4. 통합 확인 (점수 밖, 실패하면 기본 전환 차단)
- [ ] 로스터 교체(abp ↔ gasp 항목), 포털 왕복, `golmok.travel` 뒤 메시–캡슐 어긋남(텔레포트 재초기화), 포토 모드 구도·keep-height, 80 cm 통로 관통 0, 발소리 동기·이중 재생 없음, 세이브 복원.
- [ ] Offset Root Bone 메시–캡슐 최대 거리를 기록한다.

### B5. BP 컴파일 직후 PIE (V-08 함정)
- [ ] 에디터를 다시 열지 않고 `BP_GolmokCharacter_GASP`를 컴파일한 직후 PIE → `golmok.anim status` `last spawn`이 BP 클래스다(C++ 게임 모드 훅이 스폰마다 soft path로 해결 — §D 추정 확인).

### B6. 폴백
- [ ] `-GolmokAnim=abp`로 한 번, `Content/GASP`·`Content/GolmokLocal`을 저장소 밖으로 옮긴 상태에서 `mode gasp`로 한 번 띄운다. 둘 다 ①(`AGolmokCharacter`), Warning 1(두 번째만; 첫 번째는 명시적 abp라 Warning 없음), `Golmok.Player.Movement` 통과.

### B7. 패키지
- [ ] Development·Shipping cook·실행(gasp/abp 각각), 크기 증가 기록, 태그·DDCvar 경고 0(`Config/Tags/GASP.ini`·`Config/Golmok/local/` 스테이징 — §D #5), S4 성능, 플러그인을 켠 ① 패키지 정상, `/Game/GASP`·`/Game/GolmokLocal`이 없는 클론의 ① 패키지 정상(§D #9).
- [ ] 기존 `+DirectoriesToAlwaysStageAsUFS=(Path="../Config/Golmok")`가 `Config/Golmok/local/`(매니페스트의 GASP 프로젝트 절대 경로·해시, DDCvar JSON)도 패키지에 넣는다. DDCvar 등록에 필요하므로 의도된 동작이다. 다만 add-gasp를 돌린 PC의 패키지는 외부로 배포하지 않는다(GASP 콘텐츠 포함 — D-021 소유자 항목).

### B8. 결정 게이트
- [ ] 통과: `animation.json` `mode: gasp`와 로스터 모드별 기본(T12)을 별도 커밋으로 바꾼다(D-021 진행 기록). 같은 커밋에서 `Golmok.Animation.Config`의 "committed mode is abp"와 `test_ue_config_animation.py`의 mode 단언을 gasp로 바꾼다.
- [ ] 미통과: ① 기본 유지, ②는 옵션으로 두고 B안(GASP 데이터 + 우리 ABP)을 검토한다.

### B9. 결과 (V-15 PC 세션이 작성)
(비어 있음)

## C. 불확실 API 표 (UE 5.8.3 Launcher, 클라우드에서 빌드 못 함)

| # | 위치 | 가정 | 틀렸을 때 대안 | 확인 | 결과 |
|---|---|---|---|---|---|
| 1 | `GolmokGameMode.h` 훅 | `AGameModeBase::GetDefaultPawnClassForController_Implementation(AController*)`가 public virtual(`BlueprintNativeEvent`의 `_Implementation`) | 이름이 바뀌었으면 5.8 `GameModeBase.h`의 같은 역할 함수로 훅 한 줄만 바꾼다 | 빌드·§A1 Fallback | |
| 2 | `GolmokLocomotionStateComponent` | `ACharacter::LandedDelegate`(`FLandedSignature`, `const FHitResult&`)·`MovementModeChangedDelegate`(`ACharacter*`, `EMovementMode`, `uint8`)가 public dynamic multicast, `AddUniqueDynamic`/`RemoveDynamic` | 시그니처가 다르면 핸들러 매개변수만 맞춘다 | 빌드·StateProvider 착지 | |
| 3 | 같은 파일 | UFUNCTION 매개변수에 원시 `EMovementMode`(엔진 델리게이트 선언과 같음)를 UHT가 받는다 | `TEnumAsByte<EMovementMode>`로 | UHT | |
| 4 | 컴포넌트 게터 | 멤버 UFUNCTION의 `meta = (BlueprintThreadSafe)`를 UHT가 받는다 | meta 제거(게터는 캐시 복사만이라 동작은 같음) — 19b에서 스레드 안전 갱신에서 부를 수 없으면 BP에서 게임 스레드 경로로 | UHT·19b | |
| 5 | 틱 | `UActorComponent::AddTickPrerequisiteComponent`/`RemoveTickPrerequisiteComponent`, `USkeletalMeshComponent::InitAnim(bool)` public | `PrimaryComponentTick.AddPrerequisite(Component, Component->PrimaryComponentTick)` | 빌드 | |
| 6 | `GolmokGaspCharacter.cpp` | CMC `MaxAcceleration`·`BrakingDecelerationWalking`·`GroundFriction`·`BrakingFrictionFactor`·`bUseSeparateBrakingFriction`·`BrakingFriction`이 public 멤버(float/비트필드) | setter가 있으면 setter로 | 빌드·StateProvider p0 | |
| 7 | 같은 파일 | `USkinnedMeshComponent::VisibilityBasedAnimTickOption` public 멤버, `EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones` | `SetVisibilityBasedAnimTickOption()` | 빌드 | |
| 8 | 같은 파일·서브시스템 | `USkeletalMeshComponent::SetSkeletalMesh(USkeletalMesh*)`(로스터 선례와 같음) | `SetSkinnedAssetAndUpdate` | 빌드 | |
| 9 | `GolmokAnimationConfig.cpp` | `FSoftClassPath::ResolveClass`·`TryLoadClass<T>`, `FSoftObjectPath::ResolveObject`·`GetLongPackageName()`(FString), `FPackageName::DoesPackageExist(const FString&)` | `GetLongPackageFName().ToString()`, `FPackageName::DoesPackageExist(FPackagePath)` | 빌드 | |
| 10 | 같은 파일 | BP 인터페이스 생성 클래스를 `TryLoadClass<UObject>` 뒤 `IsChildOf(UInterface)`로 받고 `UClass::ImplementsInterface`로 구현 여부를 본다 | BPI 생성 클래스가 `UInterface` 자식이 아니면 `HasAnyClassFlags(CLASS_Interface)`로 판정 | 19b `status`의 `bpi yes` | |
| 11 | 같은 파일 | `IConsoleManager::RegisterConsoleVariable`의 `bool`/`int32`/`float` 오버로드, `FindConsoleObject`, 테스트의 `UnregisterConsoleObject(Object, false)` | `TAutoConsoleVariable`은 이름이 런타임 값이라 못 씀 — 오버로드 이름만 맞춘다 | Config 자동화 | |
| 12 | 서브시스템 | `FStreamableManager::RequestAsyncLoad(FSoftObjectPath, FStreamableDelegate, Priority, bool, bool, FString)`(Zones 선례와 같은 방식의 이름 있는 델리게이트) | `TArray<FSoftObjectPath>` 오버로드 | 빌드 | |
| 13 | 테스트 | `TEXT(R"JSON(…)JSON")` 원시 문자열, `AddExpectedMessagePlain`, `FInputKeyEventArgs::CreateSimulated`, `TestNull`/`TestNotNull` bool 반환 | 원시 문자열이 매크로에서 안 되면 일반 문자열 이어 붙이기 | 빌드 | |
| 14 | `AGolmokGaspCharacter` ini | 파생 C++ 클래스 CDO가 `[/Script/Golmok.GolmokCharacter]` 값(메시·ABP 경로·속도)을 물려받는다(CDO `LoadConfig`가 부모 섹션을 읽음) | 로그에 `Character mesh '' not found`가 보이면 `DefaultGame.ini` `; [WP-19 hook]` 섹션에 `[/Script/Golmok.GolmokGaspCharacter]`로 같은 네 키를 추가(핫스팟 훅) | §A1 로그 | |
| 15 | `gasp_import.py` migrate | `unreal.AssetRegistryDependencyOptions` 필드 5개, `AssetRegistry.get_dependencies(Name, options)`, `unreal.MigrationOptions`(`prompt`·`ignore_dependencies`·`asset_conflict`·`orphan_folder`), `unreal.AssetMigrationConflict.SKIP`, `AssetTools.migrate_packages(names, dest_dir, options)` | 이름이 다르면 `dir(unreal.MigrationOptions)`로 확인해 고친다. 없으면 V-08 방식(GUI Migrate) 뒤 relocate부터 | §A3 | |
| 16 | `gasp_import.py` relocate/verify | `EditorAssetLibrary.rename_directory`/`rename_asset`, `AssetTools.fixup_referencers(redirectors)`, `unreal.load_class(None, path)` | `fixup_referencers`가 없으면 콘텐츠 브라우저 "Fix Up Redirectors" 뒤 `-Verify` | §A3 | |
| 17 | `add-gasp.ps1` | `UnrealEditor-Cmd <uproject> -ExecutePythonScript=<file>`가 파일을 스크립트로 실행하고 `quit_editor()`로 끝난다(환경 변수 `GOLMOK_GASP_JOB`은 자식 프로세스에 전달) | `-run=pythonscript -script=<file>` | §A3 | |

## D. [추정] 목록과 해소

| # | 내용 | 해소 |
|---|---|---|
| 1 | C++는 BP 인터페이스를 구현할 수 없다 | §A4 BP, 스펙 §13 대안 |
| 2 | BPI 함수·구조체 목록, ABP가 BPI·CMC 밖에서 폰을 읽지 않음 | §A4-2 표 |
| 3 | 리타깃 ABP가 부모 부착("Use Attached Parent")으로 소스를 찾고 타깃은 GASP 매니 사본 | V-08b §3, §A7 — 아니면 `AGolmokGaspCharacter` PC fix(컴포넌트 태그 등) |
| 4 | 헤드리스 `rename_directory`가 된다 | §A3, 실패 시 `content_root: /Game`(종료 코드 2) |
| 5 | `Config/Tags/*.ini`가 로드·스테이징되고, JSON으로 등록한 DDCvar가 설정 DDCvar와 같게 동작(`DDCvar.FootPlacementMode` 값이 ABP에 보임) | §A3 로그, §B7 패키지 로그 |
| 6 | p0 = 엔진 기본값(2048·8·2·false·0) | §A1 StateProvider Info |
| 7 | 착지 창 0.3 s(GASP 폰 값 확인), 텔레포트 재초기화가 Offset Root Bone을 정리 | §A8, §B4 |
| 8 | 폴리 노티파이 경로와 끄는 방법 | V-08b §5 → §A5 → T13 |
| 9 | 켠 플러그인과 없는 쿡 폴더(`/Game/GASP`·`/Game/GolmokLocal`)가 ①에 무해 | §A2, §B7 |
| 10 | 우리 속도(180, 로스터 145/380)에서 스트라이드 워핑 품질 | V-08b P0 측정, §B2 |
| 11 | `closure.json`의 estimated 루트 4개 경로(BPI·UEFN 메시·`ABP_GenericRetarget`·GASP 매니 사본), `animation.json`의 BPI·UEFN 메시 경로 | §A3 migrate 메시지, §A7 |
| 12 | `-nullrhi`에서 `AlwaysTickPoseAndRefreshBones`로 뼈가 갱신된다(GaspSmoke) | §A8 헤드리스 GaspSmoke |
| 13 | 텔레포트 판정은 수평 이동만 본다(스펙 §2) — 로스터 캡슐 보정(수직 몇 cm)은 재초기화하지 않는다 | §A8 |
