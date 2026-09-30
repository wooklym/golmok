# WP-19 — GASP 모션 매칭 로코모션 통합 (D-021): 19a 클라우드 기반 / 19b PC GUI 바인딩 / 19c Astra 로스터·발소리

상태: 🟡 19a 코드 완료·PC 검증 대기(2026-09-30) · 설계 확정(2026-09-30, Opus) · 담당: 19a **Opus 5.5 ultracode**(Claude 레인), 19b PC 세션(Opus 5.5), 19c **ChatGPT Astra**(캐릭터·오디오 레인, 과제 번호 T12·T13은 병합 때 `astra-tasks.md`에 예약) · 선행 PC 실험 **V-08b** · PC 검증 **V-15**(`runbooks/pc-verify-wp19.md`).

## 목표
[D-021](../DECISIONS.md)의 ② GASP 모션 매칭 로코모션(`SandboxCharacter_CMC_ABP`, 무수정, 저장소 밖)을 **우리 C++ 캐릭터**(`AGolmokCharacter` 계열, CMC)로 구동한다. 이동 의미는 그대로 둔다. 걷기 180·달리기 500 cm/s와 로스터별 속도(WP-18 `SetMovementSpeeds`), 돌아서기(orient-to-movement, 540°/s), 점프 90 cm(JumpZ 420), CMC(Mover 이동 시스템 불채택)다. 바꿀 수 있는 것은 가감속뿐이고 값은 V-08b에서 정한다. ①(Manny + `ABP_Unarmed`)은 설정으로 고르는 상시 폴백이다. GASP가 없는 클론·CI·패키지에서도 빌드와 테스트가 통과해야 한다. 공개 저장소에는 GASP 콘텐츠를 넣지 않는다(Fab EULA §5(a)). 기본값을 ②로 바꾸는 것은 V-15 사전 등록 기준을 통과한 뒤다.

## 분할 근거 (오케스트레이터 결정, D-019, 2026-09-30)
- **19a 클라우드**: GASP 없이 만들고 시험할 수 있는 것 전부다. 상태 계산(순수 헤더), 상태 공급 컴포넌트와 C++ 폰, 모드 설정과 ① 폴백, 셋업 스크립트, 저장소 가드가 여기에 든다. D-021의 "발효 전에는 GASP 콘텐츠 없이 우리 코드·도구만"에 맞으므로 소유자 라이선스 재확인 전에 시작한다.
- **19b PC GUI**: C++는 BP 에셋으로 정의된 인터페이스(`BPI_SandboxCharacter_Pawn`)를 구현하지 못한다[추정, §13]. 그래서 얇은 BP 서브클래스가 필요하고, V-08 기록상 인터페이스 함수 그래프는 파이썬으로 만들 수 없다. D-021 발효와 V-08b 결과 뒤에 한다.
- **19c Astra**: 로스터(`Characters/`, `characters.json`)와 발소리(`Audio/`, `audio.json`)는 Astra 레인이다. 19a는 두 레인을 고치지 않고 §5·§14의 C++ 계약만 만든다. 19c는 19a 병합 뒤 main에서 시작한다.
- 순서: V-08b ∥ 19a → (D-021 발효) 19b ∥ 19c → V-15.

## 배경(코드에서 확인할 것)
- `Player/GolmokCharacter`(핫스팟): 생성자 값은 RotationRate 540, `MaxWalkSpeed = WalkSpeed`, `MinAnalogWalkSpeed` 20, `BrakingDecelerationWalking` 2000, `JumpZVelocity` 420, `AirControl` 0.3, `MaxStepHeight` 25다. `MaxAcceleration`·`GroundFriction`·`BrakingFrictionFactor`는 엔진 기본값이다. 달리기는 `StartRun/StopRun`이 `MaxWalkSpeed`를 바꾸는 방식이다. 공개 게터 `GetWalkSpeed/GetRunSpeed`와 WP-18 훅 `SetMovementSpeeds`(달리기 상태 보존)가 있다. 액터 틱은 꺼져 있다. 메시·ABP는 `PostInitializeComponents`에서 private `ApplyCharacterVisuals`가 ini 경로로 넣는다.
- `GolmokGameMode`(핫스팟): 생성자에서 `DefaultPawnClass = AGolmokCharacter`를 넣는다. `DefaultEngine.ini`의 `GlobalDefaultGameMode`가 이 C++ 클래스다(BP 게임 모드 없음).
- `Characters/GolmokCharacterSubsystem`(Astra): `OnPossessedPawnChanged`마다 현재 항목(없으면 `default`)을 `Cast<AGolmokCharacter>` 폰에 적용한다. `GetMesh()` 메시·`SetAnimInstanceClass`·상대 변환·붐·FOV·`SetMovementSpeeds`를 바꾸고, 캡슐 크기가 바뀌면 `TeleportPhysics`로 옮긴다. ABP `TargetSkeleton`이 메시 스켈레톤과 다르면 거절한다(18a "같은 스켈레톤만"). 항목 키는 정확히 12개여야 한다(`Keys()`가 개수까지 비교). 필드를 더하려면 파서를 고쳐야 한다.
- `Audio/GolmokFootstepComponent`(Astra): `UGolmokAmbienceSubsystem::PawnChanged`가 모든 `AGolmokCharacter`에 붙인다. 거리 기반(`stride_cm_by_character`)이고 트리거 `TriggerFootstep(bool bLanding)`은 노티파이 구동용으로 분리돼 있다.
- 핫스팟을 피한 선례: 발소리 컴포넌트(위), HUD 줄 `UGolmokDebugSubsystem::AddExtraHudLineProvider`(WP-13 훅). 등록부는 `CONSOLE_COMMANDS`·`BUILD_CS_*`(`test_ue_wp09_fixture.py`)와 `CONVENTION_FOLDERS`(`test_ue_zone_fixture.py`)다. 자동화 총수 32는 `pc-verify-wp12.md` "두 번째 명령" 줄과 `test_ue_wp12_fixture.py`가 대조한다. `test_ue_wp05_fixture.py`는 `+DirectoriesToAlwaysCook=` 개수(2)를 단언한다.
- V-08 사실([런북 §8](../runbooks/pc-verify-animation.md)): ②a(우리 폰 + GASP ABP 설정만)는 인터페이스가 없어 다리가 캡슐을 못 따라갔다(디딘 발 81~100 cm/m). ABP 폐포는 1,187 패키지·1,079 MB(폴리 오디오 278 포함)이고 폰까지 합치면 2,861이다. Migrate는 DDCvar 27개(`[/Script/Engine.DataDrivenConsoleVariableSettings] +CVarsArray`, 이름에 `DDCvar.`/`DDCVar.` 혼용)와 게임플레이 태그 39개(`+GameplayTagList`)를 옮기지 않는다. 또 GASP 경로 그대로 Content 루트에 떨어진다(`rename_assets` 실패). 스켈레톤은 UEFN이라 우리 `SK_Mannequin`과 다르다. 매니 메시는 GASP 런타임 리타깃(`BP_Manny` + `ABP_GenericRetarget` + IK Retargeter)으로 돌린다. ABP가 참조하는 모듈은 AnimationWarping·BlendStack·Chooser·CurveExpression·DrawDebugLibrary·Mover·MovieSceneAnimMixer·PoseSearch(+ MotionWarping·AnimationLocomotionLibrary)다. 같은 에디터 세션에서 GASP BP를 컴파일한 뒤 PIE를 띄우면 BP 게임 모드의 기본 폰이 C++ 기본값으로 스폰된다. `.gitignore` `[WP-19 hook]`(V-08 병합)은 `Content/`에서 `Golmok/`·`Python/`만 추적되게 한다.

## 설계 (확정, 2026-09-30, Opus)

### 1. 파일·클래스 (새 폴더 `Source/Golmok/Animation/`, Claude 레인)
| 파일 | 내용 |
|---|---|
| `GolmokLocomotionMath.h` | 순수 헤더(엔진 헤더 없음, `<cmath>`·`<array>`만), §2 규칙 |
| `GolmokLocomotionStateComponent.{h,cpp}` | `UGolmokLocomotionStateComponent`: 상태 계산·캐시, BlueprintPure 게터, 발 이벤트 델리게이트(§3) |
| `GolmokGaspCharacter.{h,cpp}` | `AGolmokGaspCharacter : AGolmokCharacter`: 19b BP의 C++ 부모. 컴포넌트(기본 서브오브젝트), 시각 메시 슬롯(§5), 프로파일 적용(§6) |
| `GolmokAnimationConfig.{h,cpp}` | namespace `GolmokAnimation`: `animation.json` 파싱(전부 아니면 아무것도), 유효 모드, 폰 클래스 해결과 폴백 사유, DDCvar 등록(§8), 로스터용 질의(§5) |
| `GolmokAnimationSubsystem.{h,cpp}` | `UGolmokAnimationSubsystem : UWorldSubsystem`(Game·PIE): DDCvar 등록 호출, 콘솔 `golmok.anim`, HUD 줄, 폰 클래스 미리 로드, 미리보기 |
- 유니티 빌드 규칙을 따른다. 파일 범위 도우미는 `GolmokAnimation` namespace에 두고 콘솔 객체는 `GCmdAnim`, 로그는 `LogGolmok`이다. `Golmok.Build.cs`는 바꾸지 않는다(D-021 조건 1: PoseSearch·Chooser·Mover 모듈 의존 금지, GASP는 에셋 참조로만).
- `GolmokCharacter.{h,cpp}`와 `GolmokPlayerController`는 **고치지 않는다**. 필요한 값은 모두 공개 API로 읽는다. `GetWalkSpeed/GetRunSpeed`, CMC `MaxWalkSpeed`·`GetCurrentAcceleration`·`GetMaxAcceleration`·`MovementMode`·`Velocity`, `ACharacter::LandedDelegate`·`MovementModeChangedDelegate`다.

### 2. 상태 계산 (`GolmokLocomotionMath.h`, g++ 교차검증)
단위는 cm·s·도다. GASP 열거형을 흉내 내지 않고 우리 열거형을 둔다. GASP 쪽 매핑은 19b BP가 한다.
- `ClassifyGait(MaxWalkSpeed, Walk, Run)`: |MaxWalkSpeed − Run| ≤ 0.5면 Run, 아니면 Walk다. WP-18 훅의 달리기 판정과 같아서 로스터 145/380·120/310에서도 성립한다. Sprint와 Crouch는 없다(Stance는 늘 Stand).
- `MapMovementMode(int)`: Walking(1)·NavWalking(2)는 OnGround, Falling(3)은 InAir, 나머지는 OnGround(방어 코드, 게임에 없음).
- `Intent(A, MaxAccel, Deadzone)`: 수평 가속도 ÷ 최대 가속도, 길이 ≤ 1, 0.05 미만이면 0. 게임패드 아날로그 크기를 보존한다.
- `UpdateMoving(Prev, Speed2D, IntentLen)`: 10 cm/s 이상이거나 의도가 있으면 Moving, 3 cm/s 미만이고 의도가 0이면 Idle(히스테리시스).
- `LandingWindow`: `OnLanded(Vz, Now)` 뒤 `just_landed_seconds`(기본 0.3 [추정, 19b에서 GASP 폰 값 확인]) 동안 `JustLanded`, `LandVelocity`를 보관한다.
- `IsTeleportJump(Prev, Cur, Speed, Dt, Slack)`: 수평 이동이 Speed·Dt + Slack(`teleport_jump_cm` 100)을 넘으면 참이다(포털·`golmok.travel`·로스터 캡슐 보정).
- `PlantedSlip`: V-08 표 A 정의를 그대로 쓴다(뼈 높이 ≤ 평지 최저 + 2.5 cm이고 캡슐이 땅 위일 때 디딘 발 수평 이동 ÷ 캡슐 이동 m). GaspSmoke 자동화와 V-15가 같은 식을 쓴다.
- `ValidateProfile`(§6 범위).
- 교차검증은 `tools/tests/fixtures/ue/locomotionmath_driver.cpp` + `test_ue_locomotion_math.py`다(`-Wall -Wextra -Wshadow -Werror -pedantic`, 표와 Python 참조 구현 무작위 대조, `test_ue_clock_math.py` 방식).

### 3. 상태 공급 컴포넌트
- 게임 스레드 틱(`TG_PrePhysics`, CMC 틱을 선행 조건으로, `GetMesh()` 틱이 이 컴포넌트를 선행 조건으로)에서 `FGolmokLocomotionState`(USTRUCT BlueprintType)를 계산해 캐시한다. 필드는 `MovementMode`, `Gait`, `Stance`, `RotationMode`, `MovingState`, `InputIntent`, `Acceleration`, `Velocity`, `Speed2D`, `bJustLanded`, `LandVelocity`, `bTeleportedThisFrame`이다. `RotationMode`는 늘 OrientToMovement이고 설정으로 바꿀 수 없다(D-021).
- 게터는 캐시를 복사만 한다. ABP의 스레드 안전 갱신에서 불려도 계산하지 않는다. `GetLocomotionState()`와 필드별 BlueprintPure 게터를 둔다.
- 델리게이트는 `OnRegister`에서 묶고 `OnUnregister`에서 푼다.
- 텔레포트를 감지하면 `gasp.state.reinit_anim_on_teleport`(기본 true)일 때 다음 틱에 `GetMesh()->InitAnim(true)`를 부른다. Offset Root Bone이 옛 위치에 남는 것을 막기 위한 것이다[추정, 19b·V-15에서 효과와 히치 기록].
- 발 이벤트: `NotifyFootEvent(EGolmokFootEvent Kind, bool bLeft)`(BlueprintCallable; 19b BP가 GASP 폴리 노티파이 경로에서 부름)와 네이티브 델리게이트 `OnFootEvent`를 둔다. 구독자가 없으면 동작이 바뀌지 않는다(19c T13이 구독).

### 4. 모드·폰 선택·① 폴백
- 유효 모드 우선순위: 명령줄 `-GolmokAnim=abp|gasp` > 콘솔 `golmok.anim mode`(에디터 프로세스 동안 유지, PIE를 다시 시작하면 적용) > `animation.json` `mode`. 커밋 기본은 `"abp"`다(D-021: V-15 전 main은 ①).
- `GolmokGameMode` 훅이 `GetDefaultPawnClassForController_Implementation`에서 `GolmokAnimation::ResolvePlayerPawnClass`를 부른다. 규칙은 순서대로다. 실패하면 사유 한 줄을 월드당 1회 Warning으로 남기고 Super 결과(`AGolmokCharacter`)를 쓴다.
  1. 모드가 abp이거나 플레이어 컨트롤러가 아니면 Super.
  2. 설정 파싱 실패면 ①(사유 = 파서 오류).
  3. `gasp.pawn_class`(soft class) 로드 실패면 ①("GASP pawn class missing — add-gasp / 19b").
  4. `AGolmokGaspCharacter` 파생이 아니면 ①.
  5. `gasp.pawn_interface`(BPI 클래스)가 로드되지 않거나 폰이 구현하지 않으면 ①. ②a 실패 모드를 막는 규칙이다.
  6. 통과하면 그 BP 클래스.
- BP 게임 모드를 쓰지 않고 스폰 때마다 soft path로 해결한다. 그래서 V-08의 "BP 컴파일 뒤 기본 폰 복귀" 함정을 피한다[추정, V-15 §5에서 확인]. 월드 서브시스템이 `Initialize`에서 폰 클래스를 비동기로 미리 로드한다.
- 폴백은 폰 단위다. ①은 GASP 에셋·플러그인·DDCvar가 전혀 없어도 지금과 같은 코드 경로(`AGolmokCharacter`)다.

### 5. 로스터(WP-18)와의 계약 — 19a는 `Characters/`를 고치지 않는다
- 로스터는 계속 `GetMesh()`를 "ABP가 도는 메시"로 다룬다. GASP 항목에서 `GetMesh()`는 **소스**(UEFN 메시 + `SandboxCharacter_CMC_ABP`)다. 이 조합은 18a 스켈레톤 검사를 그대로 통과한다(V-08 ②a 로컬 항목과 같음).
- 매니로 보이게 하는 리타깃은 `AGolmokGaspCharacter::VisualMesh`가 맡는다. `GetMesh()`의 자식 USkeletalMeshComponent이고 기본은 비어 있다.
  - `bool SetVisualOverride(USkeletalMesh*, TSubclassOf<UAnimInstance>, FString& OutError)`: 시각 메시와 리타깃 ABP를 넣는다. `GetMesh()`는 렌더만 숨기고(`SetHiddenInGame`, 자식에 전파 안 함) `AlwaysTickPoseAndRefreshBones`로 포즈를 계속 만든다. 그림자는 시각 메시가 낸다.
  - `void ClearVisualOverride()`: 원상 복구.
  - [추정] `ABP_GenericRetarget`는 "Use Attached Parent"로 소스를 찾는다고 보고 자식으로 붙인다. 아니면 19b가 실제 방식(컴포넌트 태그 등)으로 PC fix한다. 타깃 스켈레톤이 GASP의 `UE5_Mannequins` 사본이면 시각 메시도 그 사본을 쓴다(같은 매니 아트).
- 로스터가 쓸 질의(T12): `GolmokAnimation::RequiresGaspPawn(const UClass* AnimClass)`(설정 `gasp.anim_class`와 같거나 파생)와 `GolmokAnimation::PawnSupportsGasp(const APawn*)`(§4 규칙 4·5).
- 19c 전의 동작: GASP 폰에도 로스터가 `default`(`manny`, `ABP_Unarmed`)를 적용하므로 ①처럼 보인다. 고장은 아니다. 19b 확인용으로 `golmok.anim preview`가 `gasp.preview`(소스 메시 + GASP ABP, 선택적 시각 메시)를 현재 GASP 폰에 직접 적용한다. 다음 로스터 적용(빙의 변경·`golmok.character`)이 이를 덮어쓴다(디버그 전용, 저장 안 함).

### 6. 가감속 프로파일
- `animation.json` `movement_profiles`에 `p0`(현행)·`p1`(중간)·`p2`(GASP)를 둔다. 필드와 허용 범위: `max_acceleration`(100~10000 cm/s²), `braking_deceleration_walking`(0~10000), `ground_friction`(0~20), `braking_friction_factor`(0~10), `use_separate_braking_friction`(bool), `braking_friction`(0~20).
- `p0` = 2048·2000·8·2·false·0(현 생성자 값 + 엔진 기본값[추정, StateProvider 자동화가 `AGolmokCharacter` CDO와 같은지 단언]). `p1`·`p2`는 `null`로 커밋하고 V-08b A/B 뒤 19b가 채운다. `null` 프로파일을 고르면 파싱 오류이고 결과는 ①이다.
- 적용: `AGolmokGaspCharacter::PostInitializeComponents`(Super 뒤)가 `gasp.movement_profile`을 CMC에 쓴다. ① 폰에는 적용하지 않는다(P0 그대로). 로스터는 속도만 바꾸므로 충돌하지 않는다. `golmok.anim profile <id>`는 현재 GASP 폰에 즉시 적용한다(A/B용, 저장 안 함).
- 최고 속도·회전 속도·점프·회전 모드는 프로파일 대상이 아니다. 바꾸려면 D-021을 개정해야 한다.

### 7. `Config/Golmok/animation.json` 스키마 (Claude 레인, 기존 `../Config/Golmok` UFS 스테이징)
```json
{
  "schema_version": 1,
  "mode": "abp",
  "gasp": {
    "content_root": "/Game/GASP",
    "pawn_class": "/Game/GolmokLocal/GASP/BP_GolmokCharacter_GASP.BP_GolmokCharacter_GASP_C",
    "pawn_interface": "Blueprints/Interfaces/BPI_SandboxCharacter_Pawn.BPI_SandboxCharacter_Pawn_C",
    "anim_class": "Blueprints/SandboxCharacter_CMC_ABP.SandboxCharacter_CMC_ABP_C",
    "preview": {"source_mesh": "Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin.SKM_UEFN_Mannequin",
                "visual_mesh": null, "visual_anim_class": null},
    "movement_profile": "p0",
    "state": {"just_landed_seconds": 0.3, "teleport_jump_cm": 100, "reinit_anim_on_teleport": true}
  },
  "movement_profiles": {"p0": {"max_acceleration": 2048, "braking_deceleration_walking": 2000, "ground_friction": 8,
                               "braking_friction_factor": 2, "use_separate_braking_friction": false, "braking_friction": 0},
                        "p1": null, "p2": null}
}
```
- GASP 에셋 경로는 `content_root` 기준 상대 경로(앞 `/` 없음)다. `pawn_class`는 우리 로컬 BP라 절대 경로다. `anim_class` 폴더는 V-08에서 확인됐다. BPI·UEFN 메시 폴더는 기록이 없어 [추정] 값이고 19b가 실제 경로로 고친다(mode abp라 그 전에도 무해).
- 검증 규칙은 C++ 파서와 pytest가 같다. 키 집합이 정확히 일치해야 하고 `mode` ∈ {abp, gasp}, `content_root` ∈ {`/Game/GASP`, `/Game`}(§8 대안)이다. 경로는 로스터와 같은 ASCII 형식이다. 프로파일은 범위 안이어야 하고 고른 프로파일은 null이 아니어야 한다. `state` 값은 범위 안(0.05~2 s, 20~1000 cm)이어야 한다.

### 8. 셋업 스크립트 `add-gasp`, 매니페스트, DDCvar·태그 (로컬 전용)
- `tools/ue/add-gasp.ps1 [-GaspProject C:\UE\GASP_58] [-Verify] [-Force]`(`add-mannequin.ps1` 패턴, `common.ps1`)를 둔다. 에디터 Python `Content/Python/golmok/gasp_import.py`는 얇은 `unreal` 어댑터이고 계산은 `gasp_pure.py`(클라우드 pytest)에 둔다. 폐포 루트는 `tools/ue/gasp/closure.json`에 원래 GASP 경로로 적는다. `/Game/Blueprints/SandboxCharacter_CMC_ABP`는 V-08에서 확인됐고, `ABP_GenericRetarget`·IK Retargeter·UEFN 메시는 [추정] 경로라 19b가 확정한다. GASP 폰 `SandboxCharacter_CMC`·레벨·MetaHuman은 루트가 아니다.
- 단계:
  1. GASP 프로젝트를 헤드리스로 열어(V-08 방식) 루트의 의존 폐포를 에셋 레지스트리로 구하고 `AssetTools.migrate_packages`(충돌 Skip)로 Golmok `Content`에 옮긴다. GASP 원본 프로젝트는 고치지 않는다.
  2. 새 Golmok 헤드리스 세션에서 옮겨 온 최상위 폴더마다 `EditorAssetLibrary.rename_directory`로 `/Game/GASP/<폴더>`로 옮기고 리디렉터를 정리한 뒤 옛 경로 참조 0을 확인한다. V-08 `rename_assets` 실패 원인은 모른다[추정]. 실패하면 원래 경로에 두고 매니페스트 `content_root: "/Game"`, 종료 코드 2와 "animation.json content_root를 /Game으로" 안내를 낸다. 두 경우 모두 `.gitignore` 훅이 막는다.
  3. 로컬 파일을 만든다(모두 git 무시). `Config/Golmok/local/gasp_manifest.json`에는 GASP 프로젝트 경로, 엔진 버전, `content_root`, 패키지별 경로·크기·sha256, 집계 digest, 생성 시각을 적는다. `Config/Golmok/local/gasp_ddcvars.json`에는 GASP `DefaultEngine.ini`의 `+CVarsArray` 27개(이름·형식·기본값·설명)를 옮긴다. `Config/Tags/GASP.ini`에는 GASP `DefaultGameplayTags.ini`의 `+GameplayTagList` 39개를 UE 추가 태그 ini 형식(`[/Script/GameplayTags.GameplayTagsList]`)으로 쓴다.
  4. 검증(`-Verify` 단독 포함): 매니페스트의 패키지가 전부 있고 크기·해시가 같은지, ABP·BPI 클래스가 로드되는지, DDCvar 27·태그 39인지 본다. 커밋된 `tools/ue/gasp/expected.json`(집계 digest·패키지 수; 19b가 첫 검증 값으로 채우고 그 전에는 `null`)과 다르면 경고한다("GASP 갱신 — V-08b/V-15 재확인"; Fab §7(a) 취득 시점 조건 고정 대비). 마지막으로 `git status --porcelain --untracked-files=all unreal/Golmok`에 추가 가능한 GASP 경로가 있으면 실패한다.
- DDCvar 등록: `UGolmokAnimationSubsystem::Initialize`가 `gasp_ddcvars.json`이 있으면 아직 없는 이름만 `IConsoleManager::RegisterConsoleVariable`로 등록한다. 엔진 DDCvar 설정이 이미 만든 것은 건너뛴다. 파일이 없으면 아무것도 하지 않는다. [추정] GASP ABP는 DDCvar를 일반 콘솔 변수로 읽는다. 19b에서 `DDCvar.FootPlacementMode` 값이 보이는지 확인한다. `DDCvar.PawnClass`·`VisualOverride`·`LocomotionSetupCMC`는 GASP 폰·레벨용이라 우리 폰에서는 쓰이지 않는다(등록은 무해).
- 커밋 기본값: DDCvar·태그 **텍스트는 커밋하지 않는다**. GASP 설정 파일이 Fab "Content"인지는 소유자 사실 확인(R21-11-3) 대상이기 때문이다. "커밋 가능"으로 확인되면 `Default*.ini` 훅 섹션으로 옮기고 §9 가드 상수를 바꾸는 소형 후속으로 처리한다.

### 9. 저장소 가드·쿡
- `.gitignore` 기존 `[WP-19 hook]` 블록에 두 줄을 더한다: `unreal/Golmok/Config/Golmok/local/`, `unreal/Golmok/Config/Tags/GASP*.ini`. `Content/GASP/`·`Content/GolmokLocal/`은 이미 `Content/*` 규칙으로 무시된다.
- `check_repo.py` 훅 `check_gasp_guard`(표준 라이브러리, `git ls-files` 서브프로세스). 루트가 git 작업 트리 최상위가 아니면 건너뛴다(기존 `test_clean_repo_passes` 유지).
  - 추적 중(`ls-files`)이거나 추가 가능한(`ls-files --others --exclude-standard`) 파일이 `unreal/Golmok/Content/` 아래인데 `Golmok/`·`Python/` 밖이면 실패.
  - `Config/Golmok/local/`, `Config/Tags/GASP*.ini`, `Config/DefaultGameplayTags.ini`가 추적 중이거나 추가 가능하면 실패.
  - `Config/Default*.ini`에 `DDCvar.`(대소문자 무시)가 있으면 실패. 상수 `GASP_INI_COMMIT_ALLOWED = False`(소유자 확인 뒤 바꿈).
- 쿡: soft path로만 쓰이는 GASP 에셋과 로컬 BP가 패키지에 들어가도록 `DefaultGame.ini` 끝 훅 섹션에 `+DirectoriesToAlwaysCook=(Path="/Game/GASP")`, `(Path="/Game/GolmokLocal")`를 둔다. 폴더가 없는 클론에서는 무해하다고 본다[추정, V-15 ① 패키지로 확인]. `test_ue_wp05_fixture.py`의 개수 단언은 2 → 4(`# [WP-19 hook]` 주석)로 바꾼다.

### 10. 콘솔·HUD
- `golmok.anim status | mode <abp|gasp|config> | profile <id> | preview [off]`(명령 1개). `status`는 유효 모드와 출처, 설정 오류, 해결된 폰 클래스와 폴백 사유, GASP 설치 상태(매니페스트·ABP·BPI 로드), DDCvar n/27과 태그 파일, 현재 폰 클래스, 상태 스냅샷, 프로파일과 CMC 값을 찍는다. `preview`·`profile`은 로스터와 같은 조건(활성 캐릭터 시점, 일시정지·포토 모드 아님)에서만 된다.
- HUD 한 줄은 `AddExtraHudLineProvider`로 넣는다. 예: `anim: gasp p1 | ground run moving | intent 0.82 | land 0.12s -512`, `anim: abp`, `anim: abp (fallback: <사유>)`. `Debug/`는 고치지 않는다.

### 11. 핫스팟 훅 (별도 커밋 `WP-19: hook <파일>`, 기존 줄 무수정)
| 파일 | 내용 |
|---|---|
| `GolmokGameMode.h` | `};` 앞 `// [WP-19 hook] …` ~ `// [/WP-19 hook]` 안에 `virtual UClass* GetDefaultPawnClassForController_Implementation(AController* InController) override;` 한 줄 |
| `GolmokGameMode.cpp` | include 블록 끝 `#include "Animation/GolmokAnimationConfig.h" // [WP-19 hook]`. 파일 끝 훅 블록에 정의 1개, 본문은 `return GolmokAnimation::ResolvePlayerPawnClass(InController, Super::GetDefaultPawnClassForController_Implementation(InController));` 한 줄 |
| `.gitignore` | 기존 WP-19 블록에 두 줄(§9) |
| `tools/scripts/check_repo.py` | `CHECKS` 바로 앞 훅 블록(가드 함수·상수), `CHECKS` 끝 `"gasp": check_gasp_guard,  # [WP-19 hook]` |
| `Config/DefaultGame.ini` | 파일 끝 `; [WP-19 hook]` 섹션(쿡 두 줄) |
| `test_ue_wp09_fixture.py` | `CONSOLE_COMMANDS` 끝 `"golmok.anim",  # [WP-19 hook]` |
| `test_ue_zone_fixture.py` | `CONVENTION_FOLDERS += ("Animation",)  # [WP-19 hook]` |
- 고치지 않는 핫스팟: `GolmokCharacter.{h,cpp}`, `GolmokPlayerController.{h,cpp}`, `Golmok.Build.cs`(`BUILD_CS_*` 그대로), `DefaultEngine.ini`, `DefaultInput.ini`, `pyproject.toml`, CI.
- `Golmok.uproject` 플러그인은 19a에서 켜지 않는다. D-021 발효 전에 모든 빌드에 Experimental 플러그인(Mover 등)을 싣지 않기 위해서다(19b §13-1).

### 12. 자동화·pytest (GASP 없는 CI·PC에서 통과)
- `Tests/GolmokAnimationTest.cpp`(`#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR`, 총 32 → 36, `pc-verify-wp12.md` 두 번째 명령 줄 갱신):
  - `Golmok.Animation.Config`(PIE 없음): 저장소 `animation.json` 파싱 성공·mode abp·p0 값을 본다. 오류 사례(버전, 키 누락/추가, mode, 경로 형식, content_root, 범위, null 프로파일 선택)마다 결과가 바뀌지 않는지 본다. 해결 규칙 1~6을 본다: 없는 경로(규칙 3), `/Script/Golmok.GolmokCharacter`(규칙 4), `/Script/Golmok.GolmokGaspCharacter` + 없는 BPI(규칙 5)가 모두 ①과 정해진 사유 문구를 낸다. 명령줄·콘솔·설정 우선순위도 본다. 테스트 전용 `GolmokAnimation::FScopedConfigOverride`로 파일과 무관하게 돌린다.
  - `Golmok.Animation.StateProvider`(L_Dev PIE, `Golmok.Player.Movement`처럼 `InputKey`): 네이티브 `AGolmokGaspCharacter`를 스폰·빙의한다(GASP 불필요). 정지는 Idle·OnGround, W는 Walk·Moving·의도 ≈ 전방 단위, Shift는 Run, `SetMovementSpeeds(145, 380)` 중에도 Run 유지, 놓으면 Idle(히스테리시스), Space는 InAir, 착지 때 `bJustLanded`와 `LandVelocity.Z` < −300, 0.3 s 뒤 거짓. p0 적용 뒤 CMC 값이 `AGolmokCharacter` CDO와 같다. `NotifyFootEvent` 1회에 `OnFootEvent` 1회. 이 폰에서도 걷기 180·달리기 500·점프 90 cm가 같다. 마네킹이 있으면 `SetVisualOverride(Manny, ABP_Unarmed)` 뒤 `GetMesh()` 숨김·시각 메시 보임, `Clear` 뒤 복구(없으면 Info).
  - `Golmok.Animation.Fallback`(L_Dev PIE): 모드 gasp + 없는 `pawn_class`로 덮어쓰면 스폰 폰이 정확히 `AGolmokCharacter`이고, 기대 Warning 1개, 로스터 `manny` 적용, 이동 값 불변이다. 덮어쓰기라 GASP가 설치된 PC에서도 같다.
  - `Golmok.Animation.GaspSmoke`: GASP가 없으면(매니페스트 없음 또는 폰 클래스 로드 실패) Info "GASP not installed — skipped"로 Success다. 설치된 PC에서는 해결된 BP 폰을 스폰하고 `preview`를 적용한 뒤 걷기 3 s·달리기 3 s를 돌린다. 애님 클래스가 `gasp.anim_class`, 발 뼈(`foot_l/r`, `ball_l/r`)가 움직임, `PlantedSlip` ≤ 30 cm/m(②a 81~100, ① 8~21 — 인터페이스 연결 회귀 방지), 상태 게터가 Walk/Run을 보고하는지 본다. 메시는 `AlwaysTickPoseAndRefreshBones`(-nullrhi 뼈 갱신 [추정]).
- pytest:
  - `test_ue_locomotion_math.py`(+ 드라이버).
  - `test_ue_config_animation.py`: 스키마, mode abp, p0 == `GolmokCharacter.cpp` 생성자 값, p1/p2 null 허용.
  - `test_ue_python_gasp_import.py`: `gasp_pure`의 폐포 필터, `/Game/X` → `/Game/GASP/X` 매핑, 매니페스트 digest 안정성·불일치 감지, `+CVarsArray` 파싱(3형식·`DDCVar` 대소문자), 태그 ini 변환. `fake_unreal`에 migrate/rename 기록을 더한다.
  - `test_check_repo_gasp.py`: 임시 git 저장소로 가드 규칙 각각, 비 git 폴더는 건너뜀.
  - `test_ue_wp19_fixture.py`: Animation 헤더 규약, GameMode 훅 블록의 정확한 내용, `Source/`에 PoseSearch·Chooser·Mover·GameplayCameras include와 Build.cs 의존이 없음, `.uproject` 플러그인 ⊆ D-021 허용 목록(GameplayCameras·ChaosMover·MoverExamples·Locomotor·SmartObjects·GameplayInteractions·MetaHuman·LiveLink·RigLogic·HairStrands 금지), `.gitignore` 줄, `add-gasp.ps1`가 `gasp_import`를 부름, 콘솔 등록, 자동화 4개 선언.

### 13. 19b PC GUI 바인딩 (D-021 발효·V-08b 뒤, PC 세션, 브랜치 `pc/wp19b-gasp-binding`)
1. `.uproject`에 V-08b `.uplugin` 표의 최소 플러그인을 켠다. 별도 커밋 `WP-19: plugins (Golmok.uproject)`이고 D-021 허용 목록 안이어야 한다(pytest가 막는다). 빌드 → `add-gasp.ps1` → `-Verify`.
2. `/Game/GolmokLocal/GASP/BP_GolmokCharacter_GASP`(부모 `AGolmokGaspCharacter`, `.gitignore`로 로컬 전용)를 만든다. Class Settings에 `BPI_SandboxCharacter_Pawn`을 더하고, 각 함수가 `GetLocomotionState()` 값을 GASP 구조체·열거형으로 바꿔 돌려주게 한다. 열거형은 `Select`/`Switch`로 이름 대응시키고 순서에 기대지 않는다. 범위 밖 함수(넘기 등)는 기본값을 돌려준다. 먼저 BPI 함수 목록과 시그니처를 런북에 기록한다.
3. GASP 폴리 노티파이가 폰 쪽 인터페이스를 부르면 그 함수에서 `NotifyFootEvent`를 부른다(이중 재생 차단은 T13).
4. 함수 그래프를 Ctrl+C한 T3D 텍스트를 `tools/ue/gasp/BP_GolmokCharacter_GASP.t3d.txt`로 커밋한다. 우리가 만든 그래프이고 GASP 이름만 들어 있다. 다른 PC는 붙여넣기로 재현한다. `.uasset`은 R21-11-4(참조 에셋 커밋 가능 여부) 확인 전 커밋하지 않는다.
5. `animation.json`에 GASP 경로를 확정하고, `preview` 시각 메시(리타깃), p1/p2(V-08b 값), V-08b 사전 등록 규칙이 고른 `movement_profile`을 넣는다. `expected.json` digest도 채운다. `status`, `preview`, GaspSmoke EXECUTED로 확인한다.
- [추정] 대안: (a) BPI가 GASP 전용 구조체를 돌려줘야 하면 BP Make 노드로 만든다. (b) ABP가 BPI 밖에서 GASP 폰 클래스로 캐스트해 필수 값을 읽으면 무수정 원칙으로는 못 푼다. 그때는 오케스트레이터에 보고하고 B안(GASP 데이터 + 우리 ABP)이나 D-021 개정을 검토한다. (c) 리타깃이 부모 부착 방식이 아니면 §5 PC fix. (d) C++ 네이티브 함수 이름을 BPI에 맞춰 ProcessEvent로 흉내 내는 편법은 쓰지 않는다.

### 14. 19c Astra 과제 (이슈 #30, 19a 병합 뒤 main에서; Opus 적대 코드 리뷰 + 설계 리뷰)
- **T12 캐릭터 레인**:
  - 항목에 선택 필드 `visual`(`mesh`·`anim_class`·`mesh_scale`)을 더한다. 엄격 키 파서, `docs/spec/characters.schema.json`, `test_ue_config_characters.py`를 함께 고친다.
  - GASP 항목(예: `manny_gasp` 리타깃 매니, `uefn_gasp` 직접)은 `RequiresGaspPawn`이면 `PawnSupportsGasp` 폰에만 적용한다. 아니면 거절하고 기존 항목을 유지한다. 에셋이 없으면 로드 실패로 기존을 유지한다(18a 원칙). ABP 항목을 GASP 폰에 적용할 때는 `ClearVisualOverride`를 부른다.
  - 모드별 기본 항목(예: 루트 `default_by_anim_mode`)을 둔다.
  - 새 id의 `stride_cm_by_character`는 R63-3 계약대로 T13과 같은 PR에 넣거나 순서를 맞춘다.
  - 기존 `Golmok.Character.*`는 GASP 없이 통과해야 한다(GASP 항목은 Info로 건너뜀). 4.5등신 리타깃(D-018)은 V-08b/c 결과를 따른다.
- **T13 오디오 레인**: `footsteps.driver: distance|notify|auto`를 둔다. GASP 폰의 `OnFootEvent`를 구독해 노티파이 구동으로 바꾸고, 이벤트가 오면 거리 스테퍼를 멈추며, 착지는 `Land` 이벤트로 낸다. GASP 폴리를 끈다(방법은 V-08b §5 결과 [추정]). `Golmok.Audio.Footstep`은 GASP 없이 종전과 같아야 하고, 합성 이벤트 1개가 발소리 1개를 내며 거리 발소리와 겹치지 않아야 한다.

### 15. PC 런북 `docs/runbooks/pc-verify-wp19.md`(A절 19b, B절 V-15) — 기준은 D-021 원문, 사후 변경 금지
0. 전제: 19a·19b·19c 병합, D-021 발효, V-08b 드라이버·지표 스크립트 `tools/` 커밋, `add-gasp -Verify` 통과.
1. 빌드와 자동화 전부 Success(GaspSmoke EXECUTED).
2. 같은 드라이버로 S1~S7(패드가 있으면 S8)을 잰다. 비교 대상은 ①(매니 + `ABP_Unarmed`), ②c(통합본: 리타깃 매니·우리 카메라·선택 프로파일), ②b(참고: GASP 폰, 메시·카메라가 다름을 표기)다. 표 A·B·C와 녹화를 남긴다.
3. 판정: ②c 합계 ≥ ① + 4 · ②c ≥ ②b − 2 · S1·S2 디딘 발 미끄러짐 ≤ ①의 1/2 · S3은 돌아서기로 측정 · 평균 fps 하락 ≤ 5 % 또는 ≥ 60 fps(1% low 기록). 채점은 시험 세션과 다른 Opus 세션이 순서를 섞은 녹화로 블라인드로 하고, 소유자 채점이 있으면 우선한다. 이동 의미 불변(180/500/90 cm, 로스터 145/380)은 자동으로 확인한다.
4. 통합 확인(점수 밖, 실패하면 기본 전환 차단): 로스터 교체(abp↔gasp 항목), 포털 왕복, `golmok.travel` 뒤 메시–캡슐 어긋남(텔레포트 재초기화), 포토 모드 구도·keep-height, 80 cm 통로 관통 0, 발소리 동기·이중 재생 없음, 세이브 복원. Offset Root Bone 메시–캡슐 최대 거리는 기록한다.
5. 에디터를 다시 열지 않고 BP 컴파일 직후 PIE를 띄워 폰 클래스가 BP인지 본다(V-08 함정).
6. 폴백: `-GolmokAnim=abp`로 한 번, `Content/GASP`·`GolmokLocal`을 저장소 밖으로 옮긴 상태에서 mode gasp로 한 번 띄운다. 둘 다 ①, Warning 1, Movement 통과여야 한다.
7. 패키지: Development·Shipping cook·실행(gasp/abp), 크기 증가, 태그·DDCvar 경고 0, S4 성능, 플러그인을 켠 ① 패키지 정상.
8. 결정 게이트: 통과면 `animation.json` `mode: gasp`와 로스터 모드별 기본을 별도 커밋으로 바꾼다(D-021 진행 기록). 미통과면 ① 기본을 유지하고 ②는 옵션으로 두며 B안을 검토한다.

### 16. 다른 WP 계약과의 충돌·위험
- WP-18: ① 로스터가 빙의마다 `GetMesh()`를 덮어써 19c 전에는 GASP 폰도 ①로 보인다(§5 preview로 우회). ② 18a "같은 스켈레톤만"은 소스 메시에는 그대로 성립하지만 시각 메시에는 T12 스키마 확장이 필요하다(엄격 키). ③ 로스터 `mesh_scale`은 소스에 걸리고 시각 메시가 물려받는다. 축소 프록시에서 GASP 발 IK·보폭이 달라질 수 있다[추정, D-018 V-08b/c]. ④ 캡슐 크기 변경 텔레포트는 §3 감지 대상이다. ⑤ 새 로스터 id와 `stride_cm_by_character`(R63-3).
- WP-12: 포토 모드는 캡슐 중심 3 m 구를 기준으로 하는데 Offset Root Bone은 메시를 캡슐에서 떼어 둔다(V-08 ②b 정지 뒤 발 98~175 cm). 구도 중심이 어긋날 수 있다[추정, V-15 §4]. 포토 폰 빙의 왕복은 로스터 재적용과 같은 경로라 T12 뒤 시각 메시도 복구돼야 한다.
- WP-13: T13 전에는 거리 발소리와 GASP 폴리가 겹칠 수 있다[추정]. 그래서 V-15는 T13 뒤다.
- WP-15: `golmok.travel`과 세이브 복원은 텔레포트다(§3). 모드는 설정이라 저장하지 않는다.
- WP-05·기존 자동화: 기본이 ①이라 `Golmok.Player.Movement`·`Golmok.Character.*`·`Golmok.Photo.*`는 그대로 통과해야 한다.
- D-003: 로직은 C++, BP는 인터페이스 구현 하나(불가피한 곳)다.

### 17. [추정] 목록과 해소
| # | 내용 | 해소 |
|---|---|---|
| 1 | C++는 BP 인터페이스를 구현할 수 없다 | 19b BP, §13 대안 |
| 2 | BPI 함수·구조체 목록, ABP가 BPI·CMC 밖에서 폰을 읽지 않음 | 19b 2단계 첫 기록 |
| 3 | 리타깃 ABP가 부모 부착으로 소스를 찾고 타깃은 GASP 매니 사본 | V-08b §3, 19b |
| 4 | 헤드리스 `rename_directory`가 된다 | 19b `add-gasp`; 실패 시 `content_root: /Game` |
| 5 | `Config/Tags/*.ini`가 로드·스테이징되고, JSON으로 등록한 DDCvar가 설정 DDCvar와 같게 동작 | 19b `status`, V-15 패키지 로그 |
| 6 | p0 = 엔진 기본값 | StateProvider 자동화 |
| 7 | 착지 창 0.3 s, 텔레포트 재초기화가 Offset Root Bone을 정리 | 19b, V-15 §4 |
| 8 | 폴리 경로와 끄는 방법 | V-08b §5 → T13 |
| 9 | 플러그인과 없는 쿡 폴더가 ①에 무해 | V-15 §7 |
| 10 | 우리 속도(180, 로스터 145/380)에서 스트라이드 워핑 품질 | V-08b P0 측정, V-15 |

### 18. 하지 않는 것
넘기(traversal), GameplayCameras, Mover 폰·ChaosMover, MetaHuman, UAF, `MotionMatchMulti`, NPC. 뒷걸음/스트레이프 회전 모드, 웅크리기, 전력 질주. GASP 걷기 200·점프 높이·회전 속도 도입. GASP 에셋 수정과 커밋. 18b 최종 캐릭터·리타깃 에셋 제작. B안(우리 ABP). 비공개 에셋 저장소(소유자 결정). ② 기본값 전환(V-15 뒤).

## 산출물
- 19a:
  1. `Source/Golmok/Animation/` 파일(§1)과 `Tests/GolmokAnimationTest.cpp`(자동화 4개).
  2. `Config/Golmok/animation.json`.
  3. `tools/ue/add-gasp.ps1`, `tools/ue/gasp/closure.json`·`expected.json`, `Content/Python/golmok/gasp_import.py`·`gasp_pure.py`.
  4. 훅 커밋(§11), pytest 5개와 `fake_unreal` 확장, `pc-verify-wp12.md` 총수 줄.
  5. `docs/runbooks/pc-verify-wp19.md`(A절 19b·B절 V-15), 이 문서 "결과", STATUS WP-19 행, ROADMAP 애니메이션 행, research/09 §7에서 이 문서 링크.
- 19b: `.uproject` 플러그인 커밋, `animation.json` 확정 값, `expected.json` digest, T3D 텍스트, 런북 A절 결과, PC fix.
- 19c: T12·T13 PR.

## 완료 기준
- 19a: 산출물이 전부 있고 ①이 종전과 같다(기존 자동화·런북 무수정 통과). GASP 없는 환경에서 새 자동화 4개가 Success다(GaspSmoke는 Info skip). pytest·ruff·check_repo·CI가 초록이고 적대 검증 1라운드를 반영한다. 상태는 🟡 코드 완료·PC 대기가 된다.
- 19b: 런북 A절 통과(BP 바인딩, preview에서 GaspSmoke EXECUTED·`PlantedSlip` ≤ 30 cm/m), 확정 값 커밋.
- WP-19 🟢: 19c 병합과 V-15 판정 기록. 통과든 미통과든 §15-8 결정 게이트대로 처리하면 완료다.

## 주의
- 핫스팟은 §11 훅만 별도 커밋으로 고친다. Astra 레인(`Characters/`, `Audio/`, `characters.json`, `audio.json`, 해당 테스트·스키마)은 고치지 않는다.
- GASP 원본·수정본, DDCvar/태그 텍스트, GASP를 참조하는 `.uasset`은 커밋하지 않는다. 런북에도 `git add -A` 금지를 적는다. GASP 에셋 이름·경로 문자열(JSON·T3D·문서)은 커밋해도 된다.
- 라이선스 판단을 새로 하지 않는다. 소유자 사실 확인(R21-11: NoAI 정의, 티어, ini 범위, 참조 에셋)이 오기 전 기본값은 "로컬 전용"이다.
- 엔진 5.8.3 공개 API만 쓴다. 이름이 바뀐 API는 런북 불확실 API 표에 대안과 함께 적는다.
- 세션 운영: Opus ultracode(구현 → 적대 검증 1라운드), 브랜치 규칙은 DEVELOPMENT-PLAN §7을 따른다. 착수 때와 PR 전에 `git diff --stat origin/main...origin/<branch>`로 `astra/*`·`pc/*`와 겹침을 확인한다(특히 `test_ue_wp09_fixture.py`, `.gitignore`, `DefaultGame.ini`, `pc-verify-wp12.md`).

## 결과

### 19a (2026-09-30, Opus 5.5 ultracode, 세션 `session_01KrDgSpzFbAhrahXqUoHCC9`, 브랜치 `claude/wp19a-gasp-locomotion`) — 🟡 코드 완료·PC 검증 대기
**구현 요약**
- `Source/Golmok/Animation/`(새 폴더, Claude 레인, 유니티 도우미는 모두 namespace `GolmokAnimation`):
  - `GolmokLocomotionMath.h`: §2 규칙 전부와 `PlantedTravelCm`·`PlantedSlipCmPerM`.
  - `UGolmokLocomotionStateComponent`: §3. `TG_PrePhysics`에서 CMC → 컴포넌트 → `GetMesh()` 순서, 12필드 캐시, `BlueprintPure`·`BlueprintThreadSafe` 게터, 텔레포트 다음 틱 `InitAnim(true)`, `NotifyFootEvent`/`OnFootEvent`.
  - `AGolmokGaspCharacter`: §5·§6. `VisualMesh`, `SetVisualOverride`/`ClearVisualOverride`, `PostInitializeComponents`에서 프로파일 적용.
  - `GolmokAnimationConfig`: §4·§7·§8. 엄격 파서, 모드 우선순위, 규칙 1~6과 사유 문구, T12 질의, DDCvar, `FScopedConfigOverride`.
  - `UGolmokAnimationSubsystem`: §8·§10. DDCvar 등록, 폴백 Warning 월드당 1회, `anim:` HUD 줄, 비동기 미리 로드, 콘솔 `golmok.anim`.
- 자동화 4개 `Golmok.Animation.Config/StateProvider/Fallback/GaspSmoke`(`Tests/GolmokAnimationTest.cpp`): 총수 32 → 36. `pc-verify-wp12.md` 두 번째 명령 줄도 갱신했다.
- 설정·셋업:
  - `Config/Golmok/animation.json`: mode `abp`, p0 = 2048·2000·8·2·false·0, p1·p2 `null`.
  - `tools/ue/add-gasp.ps1`, `tools/ue/gasp/closure.json`·`expected.json`(null).
  - `Content/Python/golmok/gasp_import.py`·`gasp_pure.py`.
- 훅 커밋(§11, 파일마다 `WP-19: hook <파일>`): `GolmokGameMode.h`, `GolmokGameMode.cpp`, `.gitignore`, `check_repo.py`, `DefaultGame.ini`, `test_ue_wp09_fixture.py`(`golmok.anim`), `test_ue_zone_fixture.py`(`Animation`), `test_ue_wp05_fixture.py`(쿡 2 → 4).
- pytest 5개와 `fake_unreal` 확장: `test_ue_locomotion_math.py`(+ g++ 드라이버), `test_ue_config_animation.py`, `test_ue_python_gasp_import.py`, `test_check_repo_gasp.py`, `test_ue_wp19_fixture.py`. 새 파일의 테스트는 49개다.
- 게이트: ruff check·format 통과, **pytest 1287 passed / 3 skipped**(main 1229 + 58: 새 파일 49 + 기존 규약 테스트가 `Animation/` 9파일을 새로 검사), `check_repo.py` `OK (…, gasp)`, `git diff --check` 깨끗.
- 런북 [`runbooks/pc-verify-wp19.md`](../runbooks/pc-verify-wp19.md): A절 19b, B절 V-15(D-021 기준 원문), C절 불확실 API 17행, D절 [추정] 13행.
- 고치지 않은 파일: `GolmokCharacter.{h,cpp}`, `GolmokPlayerController`, `Golmok.Build.cs`, `DefaultEngine.ini`, `DefaultInput.ini`, `pyproject.toml`, CI, `Golmok.uproject`, Astra 레인.

**판단(스펙 빈틈을 최소로 메운 것, 오케스트레이터가 뒤집을 수 있음)**
1. `gasp.pawn_class`는 `/Game/…_C` 외에 `/Script/Golmok.<Class>`도 받는다. 스펙 §12의 규칙 4·5 자동화 사례(네이티브 클래스 경로)를 설정 덮어쓰기로 돌리기 위해서다.
2. `preview.visual_mesh`·`visual_anim_class`는 `content_root` 상대 경로와 `/Game/…` 절대 경로를 모두 받는다. 시각 메시가 우리 매니일 수도, GASP 사본일 수도 있어서다(§5). 둘은 함께 null이거나 함께 값이어야 한다.
3. 설정 파일이 무효이고 명령줄·콘솔 지정이 없으면 모드를 알 수 없다. 이때 규칙 2로 보고 ①과 파서 오류 Warning을 낸다. 명시적 abp(명령줄·콘솔)는 규칙 1이라 Warning이 없다. 깨진 설정을 조용히 넘기지 않기 위한 판단이다(적대 검증 B로 지적됨, 유지).
4. 없는 패키지는 로드 전에 `DoesPackageExist`로 확인한다. `/Script`는 조회만 한다. 엔진의 "failed to find" Warning이 폴백 Warning 1개 단언을 깨지 않게 하기 위해서다. 규칙 3은 "로드 안 됨"만 보고, 폰이 아닌 클래스는 규칙 4 사유로 간다.
5. 폴백 Warning은 사유와 무관하게 월드당 1회다. 이후 사유는 HUD·`status`에만 갱신된다. 비플레이어 컨트롤러는 기록하지 않는다.
6. 텔레포트 판정 속도는 max(이전, 현재 수평 속도)이고 수평만 본다(스펙 §2). 로스터 캡슐 보정(수직 수 cm)은 재초기화하지 않는다([추정] D#13).
7. Falling으로 모드가 바뀌면 착지 창을 즉시 닫는다(새 점프에서 `bJustLanded`가 남지 않게).
8. `AGolmokCharacter`가 아닌 `ACharacter`는 Gait를 늘 Walk로 본다. `EGolmokFootEvent`는 `Step`·`Land` 두 값이다.
9. 프로파일 id는 `[a-z][a-z0-9_]{0,15}`이고 1~8개다.
10. `FScopedConfigOverride`는 기본으로 명령줄·콘솔 모드를 격리한다. `-GolmokAnim=`으로 띄운 PC에서도 Fallback·StateProvider가 결정적이다. StateProvider도 커밋된 파일로 격리해 돈다.
11. `golmok.anim mode`는 게임 월드가 없어도 된다(프로세스 전역). `preview off`는 로스터 공개 API `SelectCharacter(현재 id)`로 원상 복구한다(`Characters/` 무수정).
12. GaspSmoke의 `PlantedSlip`는 `foot_l`+`foot_r`의 디딘 이동 합 ÷ 캡슐 이동이다. 평지 최저는 구간 안 뼈별 최저값이다. `ball_l/r`은 "움직임" 확인에만 쓴다. 구간마다 캡슐 이동 ≥ 3 s × 속도 × 0.8도 확인한다.
13. `gasp_ddcvars.json` 형식은 `{schema_version 1, source, cvars[{name, type int|float|bool, default, help}]}`로 정했다. "3형식"은 `CVarInt`·`CVarFloat`·`CVarBool`로 해석했다(`+`/`.`/무접두 배열 줄도 받음). int 기본값은 정수여야 한다.
14. add-gasp relocate는 스펙의 "최상위 폴더마다 `rename_directory`"를 좁혔다. 옮겨 온 패키지만 있는 폴더만 통째로 옮기고, 기존 패키지가 섞인 폴더(예: 매니 팩이 있는 `/Game/Characters`)는 에셋 단위 `rename_asset`으로 옮긴다. 우리 마네킹 팩이 `/Game/GASP`로 딸려 가는 것을 막기 위해서다. 실패하면 되돌리고 `content_root /Game`, 종료 코드 2로 끝난다(검증 전에 멈춤). `-Force` 재실행은 `Content/GASP`가 있으면 멈춘다.
15. `add-gasp.ps1` ↔ Python은 작업 JSON(`GOLMOK_GASP_JOB` 환경 변수, BOM 없는 UTF-8)과 단계별 결과 JSON으로 주고받는다. `git status`는 ps1이 파일로 넘긴다. Python 쪽은 예외가 나도 `quit_editor()`로 편집기를 닫는다.
16. `closure.json` 루트는 5개다. confirmed는 ABP 1개이고, estimated 4개는 BPI·UEFN 메시·`ABP_GenericRetarget`·GASP 매니 사본이다. 없는 루트는 보고하고 건너뛴다.
17. `check_repo` 가드는 git 최상위가 아니면 DDCvar ini 검사까지 모두 건너뛴다(스펙 문구대로). `Config/DefaultGameplayTags.ini`는 스펙대로 추적·추가 가능하면 실패로 두고 `.gitignore`에는 넣지 않았다. 편집기 Project Settings에서 태그를 만지면 로컬 `check_repo`가 실패하는데, 그것이 의도다.
18. 런북 B6: `-GolmokAnim=abp` 실행은 규칙 1이라 Warning 0이다. Warning 1은 GASP를 치운 `mode gasp` 실행에만 해당한다고 명시했다(스펙 §15-6 "Warning 1"의 해석).
19. `test_ue_wp05_fixture.py` 개수 줄의 주석은 WP-13 표기를 남기고 WP-19 표기를 더했다.
20. 해결 규칙 6(BP 폰 채택)은 GASP·19b BP가 있어야 하므로 `Golmok.Animation.Config`가 아니라 `GaspSmoke`(설치된 PC에서 EXECUTED)가 확인한다.
21. 커밋 파일에 의존하는 단언은 19b 확정 값(p1/p2, 선택 프로파일, 경로, `expected.json`, 플러그인, T3D 텍스트)에도 유지되게 썼다(R76-D1·D2). StateProvider는 커밋 파일에 mode abp·p0를 강제해 돌린다. mode 전환(§B8)만 단언 수정이 필요하다.
22. 시각 메시 preview는 로스터 적용이 지우지 못한다(로스터는 `GetMesh()`만 바꿈). 19c T12가 `ClearVisualOverride`를 부르기 전까지는 `golmok.anim preview off`를 먼저 하라고 메시지·런북에 적었다(R76-C1, 스펙 §5 "다음 로스터 적용이 덮어쓴다"와 다름).

**T12 계약(19a가 쓰는 Astra API, 이름을 바꾸면 알려 달라)**: `UGolmokCharacterSubsystem::GetCurrentId()`, `GetRoster().DefaultId`, `SelectCharacter(const FString&, FString&)`(`golmok.anim preview off`의 원상 복구). 19a가 T12에 주는 API: `GolmokAnimation::RequiresGaspPawn(const UClass*)`, `PawnSupportsGasp(const APawn*)`, `AGolmokGaspCharacter::SetVisualOverride`/`ClearVisualOverride`/`HasVisualOverride`/`GetVisualMesh`, `UGolmokLocomotionStateComponent::OnFootEvent`(T13).

**적대 검증 1라운드(별도 에이전트 4개: 스펙·① 불변 / UE C++ 컴파일·API / 자동화 로직 / Python·가드) — 확정 결함 반영**

| # | 지적 | 등급 | 처리 |
|---|---|---|---|
| 1 | "결과"·STATUS·ROADMAP 미작성 | A | 이 절, STATUS 행. ROADMAP은 병합 시 반영 |
| 2 | 작업 JSON BOM(PS 5.1) → 파싱 실패로 헤드리스 편집기가 끝나지 않음 | A | BOM 없는 쓰기, `utf-8-sig` 읽기, `try/finally quit_editor`(de5ecf1 이후 363594b) |
| 3 | add-gasp를 돌린 PC에서 `test_ue_wp19_fixture`가 무시된 로컬 파일 때문에 실패 | A | 추적 파일(`git ls-files`)만 검사 |
| 4 | StateProvider 폰 교체 뒤 옛 폰의 `IMC_Default`가 같은 우선순위로 남아 입력을 가로챌 수 있음 | A(조건부) | 빙의 전 `ClearAllMappings`(새 폰이 자기 컨텍스트를 다시 넣음) |
| 5 | GASP 설치 PC에서 Config 규칙 5 사유가 "does not implement"로 바뀜 | A/B | 절대 없는 BPI 경로로 고정 |
| 6 | 커밋 파일 단언(p1/p2 null·경로)이 19b 확정 값과 충돌, pytest의 리터럴 동일성도 마찬가지 | A/B | 스키마 동일성으로 바꿈. 병합 전 리뷰 R76-D1·D2로 남은 의존(선택 프로파일·pytest null 사례·StateProvider·플러그인·T3D·expected·estimated)까지 제거. §B8 모드 전환 때만 단언을 함께 고친다 |
| 7 | GaspSmoke가 폰이 움직이지 않아도 통과 가능, 부모가 틀린 BP를 "not installed"로 건너뜀 | B | 이동 거리 단언, Walk/Run 비교를 `Expected`로, 컴포넌트 없음은 실패, 부모 불일치는 오류 |
| 8 | 히스테리시스 PIE 단언이 사실상 불가 | B | Config에 `UpdateMoving` 규칙 단언 추가(PIE는 Info) |
| 9 | 단일 에셋 이동의 리디렉터 미정리, 리디렉터 판정 방식, 레지스트리 스캔 미완료, `-Force` 재실행 실패, 종료 코드 2 도달 불가 | B/C | 전부 반영(363594b) |
| 10 | 규칙 3이 비폰 클래스를 "missing"으로 보고, AI 폰이 status를 덮어씀 | C | 반영 |
| 11 | JSON 순회 타입, int DDCvar 소수 기본값 | C | `const auto&`, 정수 검사 |
| 12 | 무효 설정에서 규칙 2 Warning(스펙 규칙 1 우선과 다름) | B | 판단 3으로 유지·기록 |
| 13 | `DefaultGameplayTags.ini`가 가드 대상이지만 무시되지 않음, 가드 대소문자·기타 ini | B/C | 판단 17로 유지·기록. 대소문자·`Config/Windows` 등은 후속 후보 |
| 14 | 패키지가 `Config/Golmok/local/`도 스테이징함 | C | 런북 §B7 주석 |

UE 컴파일·UHT 리뷰에서 A급 결함은 없었다. 순수 헤더는 g++(`-Wall -Wextra -Wshadow -Werror -pedantic`)과 clang++(`-Wshadow-all -Wconversion`) 모두로 컴파일된다. 남은 위험은 런북 §C 표(17행)에 대안과 함께 적었다.

**PC 19b에 넘길 [추정]**(런북 §C·§D)
- 파생 C++ 폰의 ini 상속(`Character mesh '' not found` 확인).
- BPI 경로·함수·구조체, ABP가 BPI·CMC 밖에서 폰을 읽는지.
- 리타깃 방식("Use Attached Parent")과 GASP 매니 사본.
- 헤드리스 `rename_directory`, `MigrationOptions` 필드 이름과 `fixup_referencers`, `-ExecutePythonScript` 동작.
- JSON으로 등록한 DDCvar·`Config/Tags/GASP.ini` 로드와 스테이징.
- p0 = 엔진 기본값, 착지 창 0.3 s, 텔레포트 재초기화 효과와 히치.
- `-nullrhi`에서 `AlwaysTickPoseAndRefreshBones`로 뼈가 갱신되는지.
- 켠 플러그인과 없는 쿡 폴더가 ①에 무해한지.
- estimated 폐포 루트 4개와 `animation.json` 경로, `expected.json` digest가 PC마다 안정적인지.

**병합 시 반영(문안)**
- STATUS WP-19 행: `🟡 19a 코드 완료·PC 대기(2026-09-30, PR #<번호> 병합; Opus ultracode, 적대 검증 4에이전트 반영) · 19b(D-021 발효·V-08b 뒤, 런북 pc-verify-wp19.md A절) ∥ 19c(Astra T12·T13) → V-15`. 비고: 자동화 32 → 36(GASP 없이 GaspSmoke Info skip), pytest +49, 훅 8, ① 불변(mode abp).
- ROADMAP 애니메이션 행 한 줄: `WP-19a(2026-09-30): GASP 통합 기반 — 상태 공급 컴포넌트·AGolmokGaspCharacter·animation.json(mode abp)·① 폴백·add-gasp·GASP 저장소 가드, PC 19b·V-15 대기`.

### 19a-2 (2026-09-30, Opus 5.5 ultracode, 세션 `session_01NrENvrfp5RFiuskBtvqkYR`, 브랜치 `claude/wp19a2-gasp-setup-guard`) — 🟡 코드 완료·PC 검증 대기
병합 리뷰 R76의 셋업·가드 (B) 4건(T1~T4)과 (C)를 처리했다. 설계(§1~§18, D-021)는 바꾸지 않았다. ① 동작(mode abp)은 그대로이고, GASP 없이 빌드·테스트가 통과한다.

**구현 요약**
- T1 재실행·`-Force` 복구(`add-gasp.ps1`, `gasp_import.py`, `gasp_pure.py`):
  - migrate가 **복사 전에** 전제 조건을 확인한다(`migrate_preconditions`). `/Game/GASP`에 패키지가 있으면 멈춘다. 폐포 패키지가 Migrate 경로에 앞 실행의 잔재로 남아 있어도 멈춘다. 잔재는 이 체크아웃의 누적 이력 `Saved/Golmok/add-gasp/migrated-history.json`에 있거나 GASP 원본과 바이트가 같은 패키지다. 이때 지울 폴더·파일 목록(`delete`)을 알린다. 목록은 `split_folders`로 만들고 마네킹 팩은 넣지 않는다.
  - relocate는 migrate 보고서가 ok가 아니거나 0 패키지이면 실패하고 기존 매니페스트를 지킨다. GASP ini(DDCvar·태그)는 **이동 전에** 파싱한다.
  - ps1: `-Force`는 `Content\GASP`가 있으면 migrate 전에 멈춘다. 매니페스트만 있어도(종료 코드 2 설치) 설치로 보고 검증만 한다. 새 단계 `-LocalFiles`(DDCvar·태그 파일만)와 `-Manifest`(GUI Move 뒤 매니페스트만)를 더했다.
- T2 원본 digest: migrate가 GASP 프로젝트의 폐포 원본 파일(원래 `/Game` 상대 경로·크기·sha256)로 `source_digest`를 만든다. 복사 뒤 다시 해시해 `source_unchanged`를 보고한다. 매니페스트는 `source_digest`·`source_package_count`를 싣고, 로컬 `digest`는 무결성용으로만 남는다. `expected.json`은 schema 2(`engine_version`·`package_count`·`source_digest`)이고, `compare_expected`는 이 세 값을 비교한다.
- T3 가드(`check_repo.py` `[WP-19 hook]` 안, `gasp_pure.is_local_only`):
  - 경로는 소문자로 비교한다. `.uasset`·`.umap`은 `Content/Golmok/` 밖이면 저장소 어디서든 실패한다. `Content` 아래 `GASP`·`GolmokLocal` 폴더도 실패한다.
  - 추적 중이거나 추가 가능한 `Config/**/*.ini` 전부에서 `DataDrivenConsoleVariableSettings|CVarsArray|ddcvar.|GameplayTagList`(대소문자 무시)를 찾는다. `Config/Tags/*.ini`는 허용 목록(빈 목록) 밖이면 실패한다.
  - 한 경로 표로 두 구현을 함께 시험한다.
- T4 이름 규칙: `PACKAGE_RE`를 UE `INVALID_LONGPACKAGE_CHARACTERS` 기준으로 넓혔다. `closure()`는 이름이 불가능한 `/Game` 의존을 `rejected`로 돌려주고, migrate는 복사 전에 실패한다. `relocation_plan`은 기존 패키지를 검증하지 않는다.
- (C):
  - T5: 리디렉터를 에셋 레지스트리(`get_assets(ARFilter)`, `is_redirector`)로 판정한다.
  - T6: `package.ps1` 경고와 런북 §B7.
  - T7: ps1이 경로 공백을 거부하고, 실행 중인 편집기와 마네킹 팩 누락을 검사한다. `$ExitCode`와 `is_ddcvar`를 지웠다.
  - T8: git 실패를 보고한다. `GASP_INI_COMMIT_ALLOWED`가 ini 규칙 전부를 제어한다.
  - C2: `golmok.anim status`는 로드하지 않는다(`status load`로 분리).
  - C3: 같은 프레임 폰 해결을 캐시한다. `GetResolutionCount`를 지웠다.
  - C4: 명령줄·콘솔 모드는 대소문자를 무시하고, 틀린 `-GolmokAnim`은 Warning을 1회 낸다.
  - C5: HUD 사유를 보인다.
  - C6: preview가 스켈레톤을 검사한다.
  - C8: 착지 값은 틱에서만 쓴다.
  - D8: include 파일 이름·`.uproject` `Modules`를 고정 검사한다.
  - D10: g++ 드라이버가 `nan`/`inf`를 읽는다.
- 테스트:
  - 새 파일 `tools/tests/test_ue_python_gasp_rerun.py`(T1·T2·T4·T5 재현 12개).
  - `test_check_repo_gasp.py`(경로 표·ini 텍스트 12조합·git 실패).
  - `test_ue_locomotion_math.py`(비유한값 2개).
  - `test_ue_wp19_fixture.py`(include 규칙).
  - `fake_unreal`: `ARFilter`·`get_assets`·`is_redirector`, 노브 `leave_redirectors`·`fixup_deletes_redirectors`.
  - `GolmokAnimationTest.cpp` Config: 모드 인자·무효 명령줄 값·파일 모드 대소문자.
- T1~T4 재현 테스트는 고치기 전에 먼저 써서 23개가 실패하는 것을 확인했다. 예: `-Force` 재실행이 두 번째 migrate 복사를 함, 빈 migrate에 relocate `ok True`, ini 파싱 전에 이동 2건, `closure()`가 `-` 이름을 뺌, 가드가 `Config/Tags/Locomotion.ini`·`content/…`·DDCvar 텍스트를 통과시킴, git 실패 무시. 고친 뒤에는 모두 통과한다.
- 훅 커밋: `WP-19: hook tools/scripts/check_repo.py`(블록 안만). `.gitignore`·`DefaultGame.ini`·등록부 테스트는 고치지 않았다.
- 고치지 않은 파일: `GolmokCharacter`, `GolmokPlayerController`, `Golmok.Build.cs`, `DefaultEngine.ini`, `DefaultInput.ini`, `pyproject.toml`, CI, `Golmok.uproject`, Astra 레인(`Characters/`·`Audio/`·`characters.json`·`audio.json`).

**판단(오케스트레이터가 뒤집을 수 있음)**
1. `-Force`는 설치를 덮거나 지우지 않는다. `Content\GASP`가 있으면 멈추고, 지우는 일은 사용자가 런북 §A3 "다시 설치"로 한다. `Content/Characters`에 마네킹 팩이 섞여 있어서, 스크립트가 지우는 것보다 목록을 알리는 편이 안전하다.
2. 잔재 판정은 두 가지를 합친다. 하나는 누적 이력이고, 다른 하나는 이력이 없을 때를 위한 원본과 바이트가 같은 사본이다. 직전 `migrate.json`은 ps1이 실행마다 지우고, 실패한 실행이 덮어써서 목록을 잃는다. 그래서 이력을 따로 둔다. 이력은 복사가 일부 실패해도 복사된 것을 남긴다. 바이트가 다르고 이력에도 없는 이름 충돌은 종전처럼 "기존 Golmok 패키지"로 건너뛴다.
3. `-Manifest` 단계를 더했다(R76 T5가 말한 "GUI Move + Fix Up 뒤 매니페스트 재생성"의 수단). 마지막 성공 migrate의 패키지가 모두 `/Game/GASP`에 있거나 모두 Migrate 경로에 있을 때만 쓴다.
4. `source_digest`는 폐포 **전체**(이름 충돌로 건너뛴 것 포함)의 원본 파일로 만든다. 그래서 로컬 상태, 종료 코드 0/2, PC와 무관하다. 복사 뒤 원본이 바뀌었으면(`source_unchanged false`) 실패가 아니라 경고로 둔다. 이미 복사가 끝났고, 실패로 멈추면 잔재 처리만 늘어난다.
5. `expected.json`은 schema 2로 올리고 `digest` 키를 `source_digest`로 바꿨다(값은 아직 null이라 잃는 것이 없음). `package_count`는 원본 폐포 수다(V-08 1,187과 대조, 런북 §A3).
6. 가드의 경로 규칙과 ini 내용 규칙을 나눴다. 경로 규칙은 `is_local_only`와 같고 한 표로 시험한다. 내용 규칙은 `check_repo`에만 있다(git status 문자열에는 내용이 없으므로). 무시된 로컬 ini(`Config/Tags/GASP.ini`)는 추적·추가 가능이 아니므로 내용 검사 대상이 아니다.
7. `GASP_INI_COMMIT_ALLOWED`는 GASP ini 규칙 전부(DDCvar·태그 텍스트, `Config/Tags` 허용 목록, `DefaultGameplayTags.ini`)를 제어한다. add-gasp 산출물(`Config/Golmok/local/`, `Config/Tags/GASP*.ini`)과 GASP 콘텐츠는 PC마다 만드는 로컬 파일이라 플래그와 무관하게 막는다.
8. `.git`이 있는데 git 호출이 실패하면 "skipped" 출력이 아니라 **실패**로 한다. CI·PC에서 가드가 조용히 꺼지는 경로를 없애기 위해서다. `.git`이 없는 합성 저장소(`test_check_repo.py`)는 종전처럼 건너뛴다.
9. R76 T6: `/Game/GASP` 상시 쿡(`DefaultGame.ini` 훅)은 그대로 둔다. `package.ps1` 경고와 런북 §B7로 알린다. "하드 참조 + `/Game/GolmokLocal`만 쿡"으로 바꿀지는 19b가 패키지 결과(§B7)를 보고 결정한다.
10. ps1 경로 공백은 거부한다. `-ExecCmds="py …"`도 따옴표 처리가 같은 문제를 가져서다. 편집기 검사는 CIM `CommandLine`의 `Golmok.uproject`·GASP 프로젝트 경로로 한다(권한 문제로 비면 통과, 런북 §C #20). `git status`는 저장소 전체를 넘긴다(`.uasset` 규칙이 `Content` 밖도 보므로).
11. C2: `status`는 로드된 클래스는 `yes`, 패키지만 있으면 `on disk`, 없으면 `no`로 보인다. `status load`가 19a 동작(동기 로드)이다. gasp 모드의 `pawn:` 줄은 규칙 3~5를 위해 여전히 폰 클래스를 로드한다(스폰과 같은 비용).
12. C3: 캐시 키는 `GFrameCounter`, `SuperClass`, 모드 원천 세대다. 세대는 콘솔 모드 변경과 `FScopedConfigOverride` 생성·소멸 때 오른다. 같은 프레임 안에서만 쓰고, 포인터는 비교만 한다. AI 컨트롤러는 설정을 읽지 않고 바로 `SuperClass`를 돌려준다(종전과 결과 같음).
13. C4: 파일의 `mode`는 대소문자를 구분하도록 바꿨다(`ParseModeName`). 19a의 `FString ==`는 대소문자를 무시해 pytest 스키마와 달랐다. 명령줄·콘솔은 `ParseModeArgument`(대소문자 무시·공백 제거)를 쓴다. 틀린 `-GolmokAnim` Warning은 순수 함수 `ComputeEffectiveMode`가 아니라 `GetEffectiveMode`·`ResolvePawn`에서 프로세스당 1회 낸다. 그래서 자동화의 bogus 사례가 Warning을 만들지 않는다.
14. C5: HUD는 마지막 스폰이 GASP 폰이었는데 다른 폰에 빙의했을 때만 `anim: abp (possessed <클래스> is not the GASP pawn)`를 보인다. 폴백 사유가 우선이다.
15. C6: preview는 로스터와 같은 엄격 규칙(`TargetSkeleton == 메시 스켈레톤`)을 소스 메시와 GASP ABP, 시각 메시와 리타깃 ABP 둘 다에 쓴다. GASP가 호환 스켈레톤만 쓰면 preview가 거부된다([추정] 런북 §D #17).
16. D8: 금지 헤더는 include의 파일 이름에 `PoseSearch|Chooser|Mover|GameplayCamera`가 들어가는지로 잡는다(`CharacterMoverComponent.h` 포함). `.uproject` `Modules`는 통째로 고정한다.
17. 적대 검증 결과는 아래 표에 적는다.

**적대 검증 1라운드(별도 에이전트 1개: T1 재실행·T2 digest·T3 우회·T4 이름·① 불변·C++ 컴파일)**

(검증 결과 반영 뒤 채움)

**PC 19b에 남는 [추정]**(런북 §C #16~#22, §D #14~#18)
- `ARFilter`·`get_assets`·`is_redirector`·`AssetData.get_asset` 이름, 그리고 rename·fixup 뒤 레지스트리 즉시 갱신.
- `migrate_packages`가 바이트 그대로 복사하는지.
- 헤드리스 세션이 GASP 원본을 바꾸지 않는지(`source_unchanged`).
- rename 뒤 로컬 digest가 실행마다 달라지는지(고정하지 않는 근거).
- GASP ABP `TargetSkeleton`과 UEFN 메시 스켈레톤이 같은 객체인지(preview 엄격 규칙).
- 상시 쿡이 플러그인 없는 PC에서 쿡 오류를 내는지.
- CIM `CommandLine` 권한.
- `GFrameCounter` 캐시와 `TrimStartAndEnd().ToLower()`·const 게터 컴파일.
- 19a의 [추정](위 19a 절)은 그대로 남는다.

**병합 시 반영(문안)**
- STATUS WP-19 행: 상태 칸 끝에 `· 19a-2 셋업·가드 보강 병합(PR #<번호>; R76 T1~T4·(C))`를 더한다. 비고 끝에 `19a-2: add-gasp 재실행 복구(복사 전 정지·잔재 목록·빈 migrate 거부·-LocalFiles/-Manifest), expected.json source_digest(schema 2), 가드 내용·대소문자·위치 규칙, golmok.anim status 무로드, pytest 1287 → <수>`를 더한다.
- ROADMAP 애니메이션 행: `WP-19a-2(2026-09-30): add-gasp 재실행·복구와 원본 digest, GASP 저장소 가드 보강(리뷰 R76 후속), PC 19b 대기`.
