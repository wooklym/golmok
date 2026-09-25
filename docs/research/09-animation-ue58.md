# 09. UE 5.8 캐릭터 애니메이션 평가 (ROADMAP 1.3 애니메이션 행)

조사일: 2026-09-25 · 작성: WP-10(클라우드, 문서 전용 — UE 코드·설정·에셋 변경 없음)
표기: **[확인]** 1차 출처(공식 문서·릴리스 노트, 이 세션에서 직접 열어 문장 확인) / **[2차]** 검색 결과 요약·기사·커뮤니티 / **[확인 필요]** 컨테이너에서 원문이 열리지 않음(HTTP 403) — PC 세션 또는 사용자가 브라우저로 확인 / **[미확인]** 추정. "권장"은 엔지니어링 판단.
PC 평가 절차: [`runbooks/pc-verify-animation.md`](../runbooks/pc-verify-animation.md)(V-08).

## 요약

1. **현재 캐릭터**는 Third Person 템플릿의 마네킹(`SKM_Manny_Simple`)과 `ABP_Unarmed`(블렌드스페이스·상태 머신 방식)를 쓴다. V-01에서 걷기 180 cm/s·달리기 500 cm/s·점프가 PIE와 자동 테스트로 확인됐다(ROADMAP 1.0b). "이동이 자연스럽다"는 아직 사람이 채점하지 않았다.
2. **UE 5.8에서 품질을 한 단계 올리는 공식 경로는 Motion Matching**(Pose Search 플러그인)이고, Epic의 **Game Animation Sample Project(GASP)**가 그 완성 예제다. GASP는 모션 캡처 애니메이션 세트 + Motion Matching + Chooser + Orientation Warping + Leg IK를 한 캐릭터에 묶어 제공하고, 에셋을 **Migrate**해 다른 프로젝트에서 쓰는 절차를 공식 문서가 안내한다 [확인].
3. **5.8 변경점**: Pose Search에 다중 캐릭터 검색(`MotionMatchMulti`, Experimental)·Chooser 연동 수정이 들어갔고, Mover/ChaosMover는 motion matching용 궤적 예측을 얻었지만 Mover는 **아직 Experimental**이다 [확인: 5.8 릴리스 노트]. 우리 캐릭터는 `CharacterMovementComponent`를 쓰므로 Mover는 대상이 아니다.
4. **라이선스**: Fab 라이선스 종류(CC-BY / Standard)와 Personal·Professional 가격 구간은 공식 문서로 확인했다 [확인]. 그러나 **Fab EULA 원문·Unreal Engine EULA(엔진 동봉 콘텐츠 조항)·GASP Fab 리스팅은 컨테이너에서 403**이라 조항을 인용하지 못했다 → **[확인 필요]**, V-08 §0에서 사용자가 확인한다. GASP는 Epic이 만든 샘플이지만(가격·무료 여부도 리스팅에서 확인), 조건을 확인하기 전에는 "상용 게임 배포 가능"이라고 쓰지 않는다(CLAUDE.md 규칙).
5. **권장: ② GASP 에셋 이식(Motion Matching 로코모션만)**을 PC에서 먼저 시험하고(V-08), 실패하거나 비용이 크면 ③ 최소 구성, 그래도 안 되면 ① 현행 유지. 이유는 퀄리티 최우선(D-003·최우선 원칙)과 "Epic이 유지보수하는 5.8 대응 에셋"이라 직접 만드는 것보다 리스크가 작기 때문이다. 채택은 **라이선스 확인 + V-08 채점** 뒤 사용자 결정이다(ROADMAP 1.3 행의 구현 선택. 에셋 라이선스는 D-002 표에 기록).

## 1. 현재 프로젝트 상태 (코드에서 확인)

| 항목 | 값 | 출처 |
|---|---|---|
| 캐릭터 클래스 | `AGolmokCharacter`(C++), `CharacterMovementComponent`, 캡슐 42×92 cm, `bOrientRotationToMovement`, 회전 540°/s | `unreal/Golmok/Source/Golmok/Player/GolmokCharacter.cpp` |
| 속도 | 걷기 `WalkSpeed` 180 cm/s, 달리기 `RunSpeed` 500 cm/s(V-01 실측 일치), 점프 Z 420 cm/s, 공중 제어 0.3, 턱 25 cm, 경사 45° | `GolmokCharacter.h` 72·76행, `Config/DefaultGame.ini` 10~11행, `.cpp`, ROADMAP 1.0b |
| 입력 | Enhanced Input을 C++에서 생성(`IA_Move/Look/Jump/Run`, `IMC_Default`): WASD·마우스, 게임패드 `Gamepad_Left2D`(이동) `Gamepad_Right2D`(시점) `Gamepad_FaceButton_Bottom`(점프) `Gamepad_LeftThumbstick`(달리기), Shift 달리기 | 같은 파일 145~167행 |
| 메시·ABP | `/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple`, `/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed` — ini 경로로 로드 | `Config/DefaultGame.ini` 6~9행 |
| 에셋 공급 | `tools/ue/add-mannequin.ps1`: 엔진 설치 폴더 `Templates/TemplateResources/High/Characters/Content`를 `Content/Characters`로 복사(git에 넣지 않음) | 스크립트 |
| 검증 | V-01: `Golmok.Player.Movement` 자동 테스트 통과, PIE 스크린샷 | `runbooks/pc-setup.md`, ROADMAP 1.0b |

특징: 애니메이션은 **속도·공중 여부만 보고** 블렌드스페이스로 섞는다. 이런 구성은 방향 전환·정지·출발에서 발 미끄러짐과 "미끄러지는 정지"가 보이기 쉽다 [미확인 — V-08 ①에서 기준선으로 채점].

## 2. UE 5.8이 제공하는 것

### 2.1 Third Person 템플릿 마네킹 (현행)
- 공식 문서: "The Third Person template in Unreal Engine 5 contains … A playable third-person character that can move and jump. Additional meshes for the character. … The template also comes with redesigned mannequins." 템플릿에는 Combat·Platforming·Side Scroller **Variants**가 있다 [확인: https://dev.epicgames.com/documentation/en-us/unreal-engine/third-person-template-in-unreal-engine].
- 라이선스: 엔진 설치물(`Templates/`)에 들어 있는 Epic 콘텐츠라 **Unreal Engine EULA**의 적용을 받는다고 알려져 있으나, EULA 원문(https://www.unrealengine.com/eula/unreal)이 컨테이너에서 403 → **[확인 필요]**.

### 2.2 Motion Matching (Pose Search 플러그인)
- 정의: "Motion Matching in Unreal Engine is a query-based animation pose selection system. Contained within the Pose Search plugin, you can use the Motion Matching Animation Blueprint node as a dynamic alternative to State Machines, or Blendspaces." [확인: https://dev.epicgames.com/documentation/unreal-engine/motion-matching-in-unreal-engine?lang=en-US]
- 구성 요소(같은 문서): Pose Search **Schema**(무엇을 비교할지: 채널), **Database**(후보 애니메이션), ABP의 **Motion Matching 노드**. 궤적 채널은 "designed to be used in conjunction with the Character Trajectory blueprint component"다.
- 비용 주의(같은 문서): "the more channels and samples within the channels you have, the more performance it will take to run", "It is recommended to use as few channels as necessary". 일부 채널은 "experimental, and their functionality should not be relied upon in production"(Crashing Legs 등).
- 플러그인 성숙도(Beta/Experimental 여부)는 문서에서 찾지 못했다 → **[확인 필요]**: V-08 §1에서 에디터 Plugins 창의 표시를 기록한다.

### 2.3 Chooser
- "you can use Chooser Tables to dynamically select individual animation assets … the system itself is generic and can be used to select any type of Asset, Object, or Class." 전제: "Enable the Chooser plugin." [확인: https://dev.epicgames.com/documentation/en-us/unreal-engine/dynamic-asset-selection-in-unreal-engine]
- Motion Matching과는 `PoseSearchColumn`으로 연결된다(아래 5.8 변경점).

### 2.4 Game Animation Sample Project (GASP)
출처: https://dev.epicgames.com/documentation/en-us/unreal-engine/game-animation-sample-project-in-unreal-engine (문서 버전 표기 5.8) [확인]
- 내용: "The system uses a suite of motion captured animations driven by animation features such as Motion Matching … for a human character's traversal system. The system features coverage for common animation needs such as locomotion, scaling ledges, and vaulting."
- 기능 토글(문서의 Game Animation Widget): Orientation Warping, **Leg IK**("creates more natural poses where the character is standing on uneven surfaces"), Offset Root Bone(**experimental** 노드, 캡슐과 메시 어긋남 보정), Motion Matching Database LOD.
- 캐릭터: 기본 스켈레톤은 **UEFN_Mannequin**, MetaHuman 바디 교체 예제(`CPB_Sandbox_MetaHuman_Bodies`) 포함. 자기 캐릭터를 쓰려면 IK Rig → IK Retargeter(소스 UEFN_Mannequin) → `ABP_GenericRetarget` 절차를 문서가 안내한다.
- 이식: "you can … even migrate the animation assets and systems into your own project", 방법은 콘텐츠 브라우저 우클릭 **Migrate**. "The Game Animation Sample Project is designed to be built upon as Engine and feature development continues, so it is recommended that you continue to follow updates with upcoming releases."
- 얻는 곳: "download the Game Animation Sample Project from Fab", 런처 Library의 Vault에서 **Create Project**.
- 구현 형태: 캐릭터 `CBP_SandboxCharacter`와 `ABP_SandboxCharacter`가 **Blueprint**이고, ABP는 `CharacterMovementComponent`를 참조한다(문서의 함수 설명: "references to the CBP_SandboxCharacter blueprint and the Character Movement component"). → 우리 규칙(로직 C++, BP 최소, D-003)과 맞추려면 **ABP만 가져오고 캐릭터 BP는 쓰지 않는다**(ABP는 D-003이 허용하는 "불가피한 곳").
- 5.8 업데이트 내용: Epic 기술 블로그 "Download the latest Game Animation Sample Project—now updated for UE 5.8"(https://www.unrealengine.com/tech-blog/download-the-latest-game-animation-sample-project-now-updated-for-ue-5-8)는 컨테이너에서 403 → **[확인 필요]**. 검색 요약으로는 Smart Object 레벨의 벤치 상호작용(State Tree)·Pose Search Interaction 에셋이 추가됐다 [2차].
- 애니메이션 개수·용량: 문서에 숫자 없음 → **[미확인]**, V-08 §1에서 실측(폴더 용량·시퀀스 수).

### 2.5 5.8 릴리스 노트의 관련 변경 (원문 인용)
출처: https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes?lang=en-US [확인]

| 영역 | 원문 | 우리에게 의미 |
|---|---|---|
| Pose Search | "Pose Search databases created for Chooser Columns now default to BruteForce, since KD Tree usually fails with external filtering." / "PoseSearchColumn (motion matching integration with choosers) bug fixes." | GASP식 Chooser+MM 구성이 5.8에서 손봐짐 |
| Pose Search | "Added Experimental BlueprintCallable UPoseSearchInteractionLibrary::MotionMatchMulti, new API to perform multi character motion matching searches without any frame delay." | 다중 캐릭터(NPC 상호작용)용. MVP 밖 |
| Pose Search | "Strip out disabled PoseSearchDatabase animations during cook." | 패키지 크기에 유리 |
| Motion Warping | "Account for mesh scale when calculating Motion Warping warp points. Enable with a.MotionWarping.UseMeshScale." | 참고 |
| Mover | "Mover receives a broad update across core movement, networking, animation, and ChaosMover." / "ChaosMover adds trajectory prediction for motion-matching workflows …" / "Together, these changes continue the architectural work toward moving Mover out of Experimental status" | **Mover는 여전히 Experimental** → 채택하지 않음(우리는 CMC) |
| 캐릭터 이동 | "Converted Characters, Character Movement and dependent functionality to use a UObject representation of Movement Bases instead of UPrimitiveComponents." | C++ `GetMovementBase()` 류 사용 시 주의. 현재 코드는 쓰지 않음 |
| UAF | "The Animation Mixer also supports workflows for the new Unreal Animation Framework." | 차세대 애니메이션 프레임워크(UAF)는 5.8에서 시퀀서·크라우드 쪽 언급뿐. 게임 로코모션 전환은 시기상조 [미확인] |

## 3. 적용 경로 3안

| | ① 현행 유지(+ 다듬기) | ② GASP 에셋 이식 (권장 시험 대상) | ③ Motion Matching 최소 구성 |
|---|---|---|---|
| 내용 | `ABP_Unarmed` 그대로. 필요하면 C++ 이동 값(가감속·회전율)과 ABP 블렌드 시간만 조정 | GASP에서 로코모션 관련만 Migrate(애니메이션·Pose Search Schema/Database·Chooser 테이블·`ABP_SandboxCharacter` 또는 축소판). 우리 C++ 캐릭터에 ABP 바인딩(ini `AnimClassPath`) + Character Trajectory 컴포넌트 | 템플릿 마네킹 애니메이션(+ 필요 시 GASP 애니 일부)으로 Schema 1개·Database 1개·ABP에 Motion Matching 노드 하나. Chooser·traversal 없음 |
| 플러그인 | 없음 | Pose Search, Chooser, Motion Warping, Animation Warping 등 GASP가 켜는 것(V-08 §1에서 `.uproject` 차이로 확정) | Pose Search(+ Trajectory 컴포넌트가 속한 플러그인) |
| C++ 변경 | 없음 | 소: ini 경로 교체, Trajectory 컴포넌트 추가(C++ 또는 BP 서브클래스), ABP가 읽는 변수(가속·스트레이프 여부 등) 노출 | 소: 같음 |
| 에셋 용량 | 현행 | 클 것으로 예상 [미확인 — V-08 §1에서 폴더 용량 실측] — LFS 대상(R7: LFS 10 GiB) | 작음 |
| 기대 품질 | 기준선 | 높음: 출발·정지·급회전·경사(Leg IK)가 "AAA 데모" 수준 | 중: 데이터가 적으면 MM이 튀거나 같은 포즈 반복 |
| 작업량 | 0.5일 | 1~3일(PC, 에디터 작업 중심) | 2~4일(Schema 튜닝 반복) |
| 리스크 | 품질 상한 낮음 | 라이선스 [확인 필요], 스켈레톤 차이(UEFN_Mannequin ↔ `SKM_Manny_Simple`의 SK_Mannequin → 리타깃 필요 여부 [미확인]), ABP가 BP 캐릭터를 캐스트하는 곳 수정, 성능(Pose Search 비용), LFS 용량 | 튜닝 노하우 필요, 결과가 ①보다 나쁠 수 있음 |
| 비용(돈) | 0 | 0 예상(가격 표기는 공식 문서에 없음 [확인 필요 — V-08 §1-1]) | 0 |

**권장 순서**: V-08에서 ①을 기준선으로 먼저 찍고(10분) → ②를 **별도 폴더·별도 레벨 사본**에서 시험 → 채점표(런북 §5)로 비교. ③은 ②가 라이선스·용량·성능 중 하나로 막힐 때만.

**권장 이유**
- 퀄리티 최우선: 실촬영 골목(근경 0.5 m)에서는 캐릭터 발이 계단·턱에 붙어 있는지가 몰입을 크게 좌우한다. GASP의 Leg IK·Motion Matching은 이 문제를 직접 다룬다 [확인: GASP 문서 Leg IK 설명].
- Epic이 5.8에 맞춰 유지보수하는 에셋이라, 우리가 MM 데이터를 직접 만드는 ③보다 결과가 안정적이다.
- 우리 코드는 CMC 기반이고 GASP ABP도 CMC를 참조하므로 이동 컴포넌트를 바꿀 필요가 없다 [확인: GASP 문서].

**채택 전 조건(게이트)**
1. Fab EULA / GASP 리스팅 라이선스 원문을 사용자가 확인하고 DECISIONS D-002 표에 기록(비상업·"UE 전용" 등 조건을 그대로 인용).
2. V-08 채점 ②가 ①보다 좋고, 1080p RTX 5060에서 fps 하락이 작다(런북 §5 기준).
3. LFS 용량 추정이 R7 한도 안.

## 4. 라이선스 확인 결과

| 대상 | 확인한 것 | 상태 |
|---|---|---|
| Fab 라이선스 종류 | "Fab offers the following license types: Creative Commons Attribution (CC-BY) (Free) / Standard (Free or For Sale)" | [확인] https://dev.epicgames.com/documentation/en-us/fab/licenses-and-pricing-in-fab |
| Standard 가격 구간 | "Personal: For buyers who have not generated more than $100,000 USD in gross revenue from commercial activity in the last 12 months." / "Professional: For buyers who have generated more than $100,000 USD …" / "For more information on how the Personal and Professional tier thresholds are calculated, see the Fab End User License Agreement." | [확인] 같은 문서 |
| 구 Marketplace 라이선스 | "Epic Games is phasing out the UE Marketplace License." 리스팅의 Details에 표시된다 | [확인] 같은 문서 |
| **Fab EULA 원문**(Standard License 허용·금지 조항, Epic 제작 콘텐츠·"UE 전용" 조건) | https://www.fab.com/eula — 403 | **[확인 필요]** (검색 요약에는 "commercially distribute your Projects with the Fab assets incorporated" 류 문구가 있으나 [2차]라 근거로 쓰지 않음) |
| **Unreal Engine EULA**(템플릿 마네킹 등 엔진 동봉 콘텐츠) | https://www.unrealengine.com/eula/unreal — 403 | **[확인 필요]** |
| Epic Content License Agreement | https://www.unrealengine.com/eula/content — 403 | **[확인 필요]**(GASP에 이 라이선스가 적용되는지도 리스팅에서 확인) |
| **GASP Fab 리스팅**(어느 라이선스로 배포되는지) | https://www.fab.com/listings/880e319a-a59e-4ed2-b268-b32dac7fa016(GASP 공식 문서가 링크) — 403 | **[확인 필요]** |

→ 비상업 조건이 있으면 D-002에 따라 제외한다. 유료 에셋(Fab의 다른 모션 팩 등)은 **제안만** 하고 사지 않는다(§5).

## 5. 참고: 쓰지 않거나 나중에 볼 것
- **Mover / ChaosMover**: 5.8에서도 Experimental [확인]. MVP에 들이지 않는다.
- **UAF(Unreal Animation Framework)**: 5.8 노트에 시퀀서 믹서·MetaHuman Crowd 문맥으로만 등장 [확인]. Phase 2 이후 재평가.
- **MetaHuman 플레이어 캐릭터**: GASP가 예제를 준다 [확인]. 캐릭터 커스터마이즈(DEVELOPMENT-PLAN §1.3 결정 대기)와 함께 Phase 2 이후.
- **유료 모션 팩(Fab)**: ②가 부족할 때만 후보. 구매는 사용자 승인 사항(CLAUDE.md).
- **NPC 보행자**: 5.8 `MotionMatchMulti`(Experimental)·MetaHuman Crowd(Experimental) — MVP 밖.

## 6. 출처 목록
1. UE 5.8 릴리스 노트 — https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes?lang=en-US [확인]
2. Motion Matching in Unreal Engine — https://dev.epicgames.com/documentation/unreal-engine/motion-matching-in-unreal-engine?lang=en-US [확인]
3. Game Animation Sample Project — https://dev.epicgames.com/documentation/en-us/unreal-engine/game-animation-sample-project-in-unreal-engine [확인]
4. Dynamic Asset Selection(Chooser) — https://dev.epicgames.com/documentation/en-us/unreal-engine/dynamic-asset-selection-in-unreal-engine [확인]
5. Third Person Template — https://dev.epicgames.com/documentation/en-us/unreal-engine/third-person-template-in-unreal-engine [확인]
6. Licenses and Pricing in Fab — https://dev.epicgames.com/documentation/en-us/fab/licenses-and-pricing-in-fab [확인]
7. GASP 5.8 업데이트 블로그 — https://www.unrealengine.com/tech-blog/download-the-latest-game-animation-sample-project-now-updated-for-ue-5-8 [확인 필요, 403]
8. Fab EULA — https://www.fab.com/eula [확인 필요, 403]
9. Unreal Engine EULA — https://www.unrealengine.com/eula/unreal [확인 필요, 403]
10. Epic Content License Agreement — https://www.unrealengine.com/eula/content [확인 필요, 403]
