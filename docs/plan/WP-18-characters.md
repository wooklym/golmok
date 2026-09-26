# WP-18 — 플레이어 캐릭터

상태: **설계 가설·리뷰 준비, D-018 ① 승인 대기** · 담당: **ChatGPT Astra**, 리뷰 **Fable ultracode**.
의존: WP-01 캐릭터, WP-04/05/09 포털·Zone·디버그, WP-12 포토 모드(통합 검증), WP-13 오디오 키 계약(18b), V-08(최종 애니메이션).
검증: Python/CI, V-11(18a PC), V-12(룩 가설, Fable 실행·소유자 채점). 2026-09-26.

## 목표

“귀엽고 개성 있는 캐릭터를 골라 서울의 예쁜 공간들을 돌아다닌다.” 설계 PR은 아트·제작 경로·D-018을 제안하고, 스택 구현 PR은 템플릿 기반 **4종의 콘솔 교체**만 제공한다. 실제 에셋·리타깃·이모트·커스터마이즈는 18b다. 작성은 승인 대기 중 진행하며 병합·구매는 하지 않는다.

## 배경 (코드 확인)

[확인: origin/main 5c6f225] `Player/GolmokCharacter`는 캡슐 42/92, 메시 (0,0,−92)/Yaw−90, 붐320·소켓(0,45,55)·FOV80, 걷기180/달리기500이다. MaxStepHeight25, JumpZVelocity420, 붐 ProbeSize14는 그대로 둔다. `PostInitializeComponents()`가 ini 값을 적용하고 `ApplyCharacterVisuals()`에서 Manny/ABP_Unarmed를 로드한다. 속도 멤버는 private, public setter 없음. 달리기 상태는 `MaxWalkSpeed`로만 구분한다.

[확인: 병행 브랜치] `claude/hopeful-allen-f0a0jb` WP-12 확정 설계는 **빙의하지 않고 ViewTarget만 전환**, 캡슐 중심 반경3m, 진입 당시 FOV 상속, `SetActorHiddenInGame` 숨김이다. 초기 main WP-12 문서의 ‘별도 폰 빙의’ 제안은 확정안으로 읽지 않는다. WP-13은 거리 기반 보폭/재질을 audio.json에 둔다. `pc/v08-animation`과 이번 수정 파일은 겹치지 않는다.

## 산출물

- 설계: [A 컨셉](../design/character-concept.md), [B 제작 경로](../research/11-character-pipeline.md), 이 문서 C/D, 컨셉 JPG 7장(첫 세트1×2 + 나머지5×1), `docs/outreach/character-commission-draft.md`.
- 18a: `Characters/GolmokCharacterSubsystem.{h,cpp}`, 순수 `GolmokCharacterMath.h`, `Config/Golmok/characters.json`, `docs/spec/characters.schema.json`.
- 테스트: `Tests/GolmokCharacterRosterTest.cpp`의 `Golmok.Character.*`, `test_ue_character_roster_math.py`+stdin C++ driver, `test_ue_config_characters.py`.
- 런북: `docs/runbooks/pc-verify-wp18a.md`(V-11, V-12 절차).

## 설계 — WP-18a

### 데이터 계약

`Config/Golmok/characters.json`을 한 번 로드한다. 루트는 `schema_version:1`, `default:<id>`, `characters:[...]`이다. UTF-8, 추가 키 불가. id는 소문자 ASCII 영문으로 시작하는 `[a-z][a-z0-9_]{0,47}`, 중복 불가, 예약어 `list` 불가. `default`는 존재하는 id. 목록은 2~32개(납품 기본4개). 완전한 JSON·필드·관계 검증 후에만 목록을 교체한다. 한 항목이 깨져도 부분 목록을 활성화하지 않는다. 파일 오류 시 기존 ini 캐릭터 유지, 캐릭터 명령은 오류 설명. 외부 URL/파일 경로 로딩 없음.

| 필드(전부 필수) | 형·범위·단위 | 의미 |
|---|---|---|
| `id`, `display_name:{ko,en}` | 위 id, 비어 있지 않은 문자열 각80자 이하 | 로그 목록/후속 UI용 |
| `mesh`, `anim_class` | `/Game/.../Name.Name`, ABP는 `.Name_C`, ASCII 경로 | soft path. 실제 자산 존재/스켈레톤은 적용 전 로드로 검증 |
| `height_cm` | 80~220 | 시각 디자인 목표, 캡슐 전체높이와 구별 |
| `capsule:{radius_cm,half_height_cm}` | radius15~60, half40~120, half≥radius | 액터는 unit scale, Z-up 직립 상태만 지원 |
| `mesh_offset_cm`, `mesh_scale` | 숫자3개, offset 각±250, scale 각0.25~2 | scale은 메시 로컬 축. 액터/캡슐을 스케일하지 않음 |
| `mesh_yaw_deg` | −180~180 | pitch/roll은0, Manny−90 |
| `camera:{boom_cm,socket_cm,fov_deg}` | boom100~500, socket 각±150, FOV40~110 | 다른 붐 충돌·lag 설정 불변 |
| `movement:{walk_cm_s,run_cm_s}` | walk50~300, run100~800, run>walk | setter로 현재 걷기/달리기 모드 유지 |
| `footstep_set` | null 또는 id 형식 키 | **참조만**, 18a에서는 값 조회/재생 안 함 |

발소리 우선순위(18b 연결 제안): 유효한 캐릭터 `footstep_set` → audio.json의 `default` 세트. 각 세트 안에서 실제 바닥 SurfaceType의 샘플 → 해당 세트 default 샘플. 없는 참조는 로그1회+오디오 기본 세트로 되돌린다. 보폭/음량/재질 샘플 값은 audio.json이 유일한 소스다. 아직 WP-13 확정 스키마가 아니므로 18a 기본4개는 전부 `null`이다.

### 순수 계산과 플레이스홀더

`GolmokCharacterMath::Calculate(height,width_ratio)`는 UE 타입 없이 설계 출발값을 만든다. `s=height/180`, `scale=(s×width_ratio,s×width_ratio,s)`, `radius=42×s×width_ratio`, `half=92×s`, `offsetZ=−half`, `boom=80+240×s`, `socket=(0,5+40×s,15+40×s)`, `FOV=60+20×s`. 유효 height80~220/width0.75~1.35만 허용하고 결과 검증도 통과해야 한다. 런타임은 JSON의 명시적 아트 조정값을 사용한다. Calculate가 schema의 필수 필드를 대신하지 않는다. 공통 `Validate`로 유한수·범위·반높이/반지름·속도 관계를 검증한다.

| id | 메시/ABP | 키·메시 스케일 | 캡슐 | 붐/소켓/FOV | 걷기/달리기 |
|---|---|---|---|---|---|
| `manny` (default) | SKM_Manny_Simple / ABP_Unarmed | 180 / (1,1,1) | 42/92 | 320/(0,45,55)/80 | 180/500 |
| `quinn` | SKM_Quinn_Simple / 같은 ABP | 180 / (1,1,1) | 42/92 | 같음 | 180/500 |
| `proxy135` | Manny / 같은 ABP | 135 / (0.8,0.8,0.75) | 33.6/69 | 260/(0,35,45)/75 | 145/380 |
| `proxy110` | Manny / 같은 ABP | 110 / (0.8,0.8,0.6111111) | 33.6/56.2222222 | 226.6666667/(0,29.4444444,39.4444444)/72.2222222 | 120/310 |

메시 경로는 `/Game/Characters/Mannequins/Meshes/<name>.<name>`, ABP는 `/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed.ABP_Unarmed_C`. 각 메시 offsetZ는 −half, yaw−90. 프록시는 **키/가로폭 변형**이며 4.5등신 머리/팔다리 리타깃 결과가 아니다.

### 같은 폰 교체·수명

**UWorldSubsystem 1개**를 선택한다. 월드별 목록·선택 상태가 PIE/맵 전환에서 분리되고 GameMode/Controller 생성자 훅이 필요 없다. GameInstance 방식은 맵이 바뀌어도 선택이 남아 18a의 비저장 범위와 수명 정리가 복잡하다. LocalPlayer 방식은 로컬 플레이어 없는 자동화 월드와 콘솔 World 연계가 불편하다.

OnWorldBeginPlay에서 첫 PC에 AddDynamic. 즉시 이미 빙의된 폰을 처리한다. PC가 늦게 나타나거나 교체될 때를 위해 0.25초 바인딩 감시 타이머를 둔다(프레임 틱 아님, 동일 PC는 no-op). 이전 PC는 RemoveDynamic, 새 PC의 현재 폰에 즉시 재적용. Deinitialize에서 타이머/델리게이트 해제. handler는 UFUNCTION, 새 폰이 AGolmokCharacter가 아니면 무시. PostInitializeComponents 이후에만 적용한다.

같은 폰은 Actor/Controller/입력·컴포넌트·포털 참조·Zone 위치를 유지한다. 새 폰 spawn+possess 방식은 포털의 PawnSwap 재판정, 입력/오디오 컴포넌트 재생성, 사진 앵커·경로 재생의 원래 폰 포인터 복원이 추가되어 제외한다.

선택은 그 월드의 세션 상태로만 유지한다. 일시적인 경로 폰 빙의를 무시하고 원래/새 AGolmokCharacter로 돌아오면 현재 id를 적용한다. 다음 게임/맵에서는 JSON default로 시작한다. 파일·세이브·ini에 마지막 선택을 쓰지 않는다.

### 적용 트랜잭션

1. `golmok.character list`는 로그에 id/한·영 이름/기본 id/현재 id를 표시한다. `golmok.character <id>`만 교체. 추가 인자·잘못된 id는 거절하며 현재 id와 모든 컴포넌트는 유지한다.
2. 대상은 첫 PC의 AGolmokCharacter. 정지 중 또는 ViewTarget이 캐릭터가 아니면 수동 교체를 거절한다(WP-12 촬영/TimeDilation 모드도 ViewTarget으로 감지). 경로 폰, crouch, 물리 시뮬레이션·비단위 액터 스케일/기울어진 캡슐은 범위 밖으로 거절한다. 콘솔에서 이유를 알린다.
3. 새 메시·ABP를 모두 로드하고 애니메이션 클래스의 TargetSkeleton과 메시 Skeleton이 같은지 검사한다. **18a는 같은 스켈레톤만 허용**. GASP/다른 리그의 허용은 18b retarget ABP가 완료된 뒤 설계를 확장한다. 실패하면 기존 메시·수치·id 유지.
4. 기존 발밑 = 캡슐 중심 Z−기존 half. 새 중심 = 발밑+새 half. XY/회전/속도는 보존. 새 캡슐 위치/크기의 blocking overlap을 기존 collision response로 검사해 천장·벽에 겹치면 거절. 크기/위치 동일한 기본 재적용은 이동/overlap 검사 생략.
5. 검증 뒤 scoped movement update 안에서 메시·오프셋·스케일·ABP·initial offset cache·카메라·속도·현재 id를 갱신한 다음 캡슐 크기/중심을 바꾼다. 지연된 부모 이동보다 자식 메시 상대변환을 먼저 설정해야 실제 Z offset이 유지된다. scope 종료 때 overlap을 알리므로 관찰자는 완성된 교체 상태를 본다. actor hidden/collision flags·ViewTarget·time dilation은 건드리지 않는다. 로드가 동기식이므로 첫 교체 히치는 V-11에 측정 항목으로 남긴다.

포털: 반지름/높이가 달라지면 실제 overlap은 재평가되지만 평면을 넘는 XY 이동은 발생하지 않는다. 실내 상태·Zone pin을 인위적으로 바꾸지 않는다. Zone loader: XY 위치가 같아 거리 기준 유지. 포토: 진입 전에 바꾸고 새 FOV를 상속받도록 한다. 포토 중엔 교체 거절. 경로: 경로 폰을 무시하고 복귀 시 같은 선택 복원.

### 핫스팟 훅 (각 별도 커밋)

1. `WP-18: hook GolmokCharacter` — h 클래스 끝 `FSoftClassPath AnimClassPath;` 다음에 public `SetMovementSpeeds(float InWalkSpeed,float InRunSpeed)`. cpp 끝에 정의. `[WP-18 hook]`/`[/WP-18 hook]` 표지. 기존 StartRun/StopRun 불변. 이전 MaxWalkSpeed≈이전 RunSpeed인지 저장한 뒤 새 속도·MaxWalkSpeed 적용.
2. `WP-18: hook test_ue_wp09_fixture.py` — `CONSOLE_COMMANDS` 끝에 `"golmok.character",  # [WP-18 hook] 캐릭터 콘솔`. WP-12와 겹치면 photo 줄 먼저, character 줄 뒤로 둘 다 보존.

그 외 PlayerController/DefaultGame.ini/Build.cs/GameMode/공유 문서 수정 없음. Json/JsonUtilities·UFS 설정은 이미 있다. 도우미 namespace는 `GolmokCharacters`, 콘솔 객체는 `FAutoConsoleCommandWithWorldAndArgs GCmdCharacter` 하나다.

### 테스트 계획

- JSON schema: 필수·추가 키·배열 길이·유효/잘못된 경로·범위, default 존재·중복id·속도/캡슐 관계는 semantic 검사로 보강.
- 순수 C++: 기준 리터럴, 두 프록시, 무작위 유효 입력 Python 교차계산, NaN/Inf/범위·관계 실패. stdin 입력/UTF-8, g++ `-Wall -Wextra -Werror -pedantic`.
- UE `Golmok.Character.Config`: 실제 JSON, malformed·duplicate·unknown default·타입/관계 실패, 파서 실패 원자성.
- UE `Golmok.Character.Runtime`: L_Dev PIE/nullrhi. 자동 default 적용을 리터럴로 검사(경로·캡슐·메시 offset/yaw/scale·카메라·속도), Quinn/프록시/Manny 왕복, 잘못된 id 보존, 달리기 상태 보존, 발밑 보존, 천장 겹침 거절, 비캐릭터 폰 무시/복귀, 정지/뷰타깃 교체 거절. 기존 `Golmok.Player.Movement` 수정 없이 전체 실행.
- 실제 GUI 포털 왕복·실내 교체·Quinn 스켈레톤·사진/그림자 품질은 V-11/V-12 기록. Python 성공을 UE 성공으로 대체하지 않는다.

### 18b 개요

①/V-11 이후 V-12와 V-08을 거쳐 ② 승인 → 인간 최종 원화·에셋 1종 발주 → 스킨/IK Retargeter·가산 포즈 → 아이들/포토 포즈 → 의상/헤어 확장 순서. Mutable은 옷/체형 조합이 많아져 단순 모듈 조합보다 이득이 확인될 때만 도입한다.

선택 화면: Slate C++(바이너리 최소·D-003 일치)와 UMG 레이아웃+전부 C++ 로직(디자이너 검수 편의)을 비교해, Phase2 초반에는 **UMG 레이아웃·C++ 로직**을 권장한다. 18a에는 선택 화면 없음. WP-15 세이브에 character_id+스키마 버전, 없는 id는 default 복구를 추가한다. 입력 키는 현 F1~F10/1~4, WP-12 P·WASD/EQ·Space/Enter·괄호·쉼표·N/M·Z/C·F/H/O/R·Shift를 피하고 UI 액션으로 배치, 최종 키는 입력 충돌표 작성 후 승인. `Tab` 후보이나 예약하지 않는다. Photo 메타 JSON에 character_id를 추가할 때 Photo 소유자가 스키마/테스트를 함께 바꾼다.

### V-12 절차·채점

Fable PC 세션이 실 Zone(없으면 L_Basemap_Yeonnam)에서 회색 콘크리트·붉은 벽돌·초록 대문·간판 색면 배경 4곳을 선정한다. 실명 간판/인물이 없는 검수 가능 구도만 저장한다. 18a 키/폭 프록시 2개 × 재질3안(Toon은 5.8 Substrate 실험 기능, 기존 설정 후처리는 별도 대조군) × 조명4프리셋, 기본 거리와 얼굴0.5m/사진 f2.8·f8을 같은 위치에서 비교한다. 없는 배경은 무지 색판으로 대체했다고 기록한다.

소유자가 배경 조화·실루엣·사진 매력·발밑/벽 그림자·비율 감각을 각1~5로 채점. 권장 통과 가설: 평균4 이상, 어느 항목도3 미만 없음, 천장/계단 관통·그림자 수신 실패는 별도 blocker. 캐릭터당 프레임 GPU ms·VRAM peak와 D-010 경로를 같이 적는다. 최종 캐릭터 승인에는 4.5등신 별도 프록시의 V-08 동작 영상도 필요하다.

## 완료 기준

설계 A~D·원문 확인 수준·권장안·이미지 LFS·D-018 결정 묶음. 18a 기본 동작 유지·새/기존 테스트·Python/CI 초록·표지와 독립 훅 커밋·V-11 런북. UE 헤드리스는 이 PC UE5.8.3에서 실제 실행하고 GUI/최종 품질은 확인한 만큼만 표기한다.

## 주의

공개 저장소에 Fab·외주 원본 넣지 않음. default ini 불변. 처음 로드가 실패하면 기존 플레이가 가능해야 한다. 돈이 드는 일/외부 메시지 발송 없음. 에디터 GUI 실행 전 `gui-foreground.lock` 확인, fps 측정은 다른 UE 프로세스 없을 때만. 원문 확인 못한 항목은 사실로 확정하지 않는다.

## 결과 (구현 PR에서 작성)

설계 A1~A5·B1~B6·C/D와 컨셉7장을 작성했다. 런타임 코드·실행 결과·V-11 런북은 [스택 구현 PR #23](https://github.com/wooklym/golmok/pull/23)의 이 절에서 기록한다. 설계 PR은 구현 결과를 이미 병합한 것으로 표시하지 않는다.

## 병합 시 반영

### D-018 | 제안 | 2026-09-26 — 캐릭터 선택·교체와 고유 캐릭터 제작

- 권장 시점: **18a는 Phase1 M7 품질 검증 기반**, 콘솔·데이터만. 18b의 실제 캐릭터1종은 V-08/V-12/② 뒤 M7 여유 시, 선택 UI·저장·커스터마이즈는 **Phase2 초반 WP-15와 함께**. Phase1 MVP에 메뉴/세이브를 추가하지 않는다.
- 제안: 스타일라이즈드 PBR·135cm/4.5등신·GASP+스타일 보정 가설, 첫 세트 c01 1종, 인간 외주 최종 제작, 같은 폰에서 로스터 교체.
- 규모: 설계PR+18aPR, PC V-11/V-12, 18b 아트160~280h/4~7주 가설(견적 아님), 리타깃·UI/저장은 별도 산정.
- 의존: V-08 소스 스켈레톤·라이선스, WP-12, D-010 그림자 수신체, WP-13 세트키, WP-15.
- 리스크: 작은 비율의 성인 모캡/손 관통, 캡슐 변경·포털, splat 접지, AI 참고 이미지 권리/상표, 동기 로드 히치/VRAM, 비공개 에셋 재현성.
- **소유자 결정 필요 ①**: 룩/애니메이션 가설·비율 시험, 후보 c01 한 종(이름은 상표 확인 전 가칭), 18a 범위, V-11/V-12 채점·18b 시점. 작성/검증은 승인 전 가능, 병합은 Fable 리뷰+승인 후.
- **소유자 결정 필요 ②**: V-12/V-08 뒤 최종 룩/비율, 상표 최종 명칭과 검토, 외주 예산·업체·권리양도 계약/수정 범위, 비공개 에셋 저장소·협업자 범위, 필요 도구/라이선스 확인, 출시 AI표시 자문. **모든 지출은 ② 이후**.

### 다른 문서로 옮길 문안

- STATUS WP-18: “설계/18a 코드·검증 상태는 WP-18 결과 절 참조. D-018 ①·Fable 리뷰 대기. 18b는 V-08/V-12/② 뒤.” V-11: “pc-verify-wp18a의 헤드리스·GUI 미검증 항목 진행.” V-12: “Fable 실행/소유자 채점, 프록시2×재질3×조명4, 실제4.5등신 리타깃은 V-08 추가 시험.” 결정 필요에 D-018 ①/② 링크.
- DEVELOPMENT-PLAN §1.3: “캐릭터 선택·교체/커스터마이즈는 D-018 제안: Phase1 콘솔 검증, Phase2 UI·세이브. 수집 요소는 미등록.” §11: D-018 두 단계 결정을 별도 행으로 추가.
- ROADMAP 1.3 행: “캐릭터 선택·교체(WP-18): 18a 템플릿 로스터·콘솔·동일 폰, V-11; 18b 최종 에셋·리타깃은 V-12/② 뒤. 기본 조작 유지.”
- game-features-proposal의 캐릭터 줄: “D-018 제안 등록(WP-18): c01 우선1종·18a 기반, 커스터마이즈 UI/저장은 Phase2 WP-15와 함께.”
- D-002 후보 행: “WP-18 OpenAI 이미지: 공개 컨셉 참고자료만, A5 약관/저작물성 조건 참조. 템플릿 마네킹: 기존 UE 설치 Examples, 로컬 복사·커밋 없음. Meshy/VRoid/VRM4U/MetaHuman/Fab 구매·신규 의존성은 이번에 채택하지 않음. 외주 계약/에셋은 D-018 ② 후 항목별 기록.”
- **V-08 추가 시험 문안**: “135cm·4.5등신(머리30cm), 넓은 몸/짧은 다리의 임시 휴머노이드 프록시에 GASP를 IK Retargeter로 적용. 18a 전체 스케일 proxy135는 카메라/키 비교에만 사용하고 머리/팔다리 비율을 조정한 프록시를 별도로 준비한다. 리타깃만/팔·상체 가산 보정/키프레임 기준 영상 비교. 145/380cm/s, 정지→걷기→달리기→180도 턴→25cm 계단. 팔-머리/배 관통 횟수, 접지 발 미끄러짐(cm), 성인 보폭 느낌, 자연스러움과 귀여움을 각각 채점. 다른 리그를 호환 스켈레톤 지정만으로 실행하지 않는다.”
