# WP-18 — 플레이어 캐릭터

상태: **🟡 설계 자체 리뷰·18a 코드/헤드리스 완료·D-018 ① 승인, PC GUI 검증 대기** · 담당/이번 리뷰·병합: **ChatGPT Astra(2026-09-27 사용자 지시)**. 최종 엔진 품질 검증은 Fable PC 후속.
의존: WP-01 캐릭터, WP-04/05/09 포털·Zone·디버그, WP-12 포토 모드(통합 검증), WP-13 오디오 키 계약(18b), V-08(최종 애니메이션).
검증: Python/CI, V-11(18a PC), V-12(룩 가설, Fable 실행·소유자 채점). 2026-09-26.

병합 후 후속(2026-09-27): [경로 복귀·WP-12 통합·렌더 증거 기록](WP-18-followup.md). 실제 경로 자동화 통과와 WP-12 UE 컴파일 차단을 확인했으며 GUI/최종 품질의 완료 범위는 해당 기록을 따른다.

## 목표

“귀엽고 개성 있는 캐릭터를 골라 서울의 예쁜 공간들을 돌아다닌다.” 설계 PR은 아트·제작 경로·D-018을 제안하고, 스택 구현 PR은 템플릿 기반 **4종의 콘솔 교체**만 제공한다. 실제 에셋·리타깃·이모트·커스터마이즈는 18b다. 2026-09-27 사용자 지시로 자체 리뷰 후 설계→구현 순서로 병합한다. 구매·발주②는 별도다.

## 배경 (코드 확인)

[확인: origin/main 5c6f225] `Player/GolmokCharacter`는 캡슐 42/92, 메시 (0,0,−92)/Yaw−90, 붐320·소켓(0,45,55)·FOV80, 걷기180/달리기500이다. MaxStepHeight25, JumpZVelocity420, 붐 ProbeSize14는 그대로 둔다. `PostInitializeComponents()`가 ini 값을 적용하고 `ApplyCharacterVisuals()`에서 Manny/ABP_Unarmed를 로드한다. 속도 멤버는 private, public setter 없음. 달리기 상태는 `MaxWalkSpeed`로만 구분한다.

[확인: 병행 브랜치] `claude/hopeful-allen-f0a0jb` WP-12 확정 설계는 **빙의하지 않고 ViewTarget만 전환**, 캡슐 중심 반경3m, 진입 당시 FOV 상속, `SetActorHiddenInGame` 숨김이다. 초기 main WP-12 문서의 ‘별도 폰 빙의’ 제안은 확정안으로 읽지 않는다. WP-13은 거리 기반 보폭/재질을 audio.json에 둔다. `pc/v08-animation`과 이번 수정 파일은 겹치지 않는다.

## 산출물

- 설계: [A 컨셉](../design/character-concept.md), [B 제작 경로](../research/11-character-pipeline.md), 이 문서 C/D, 컨셉 JPG 7장(첫 세트1×2 + 나머지5×1), `docs/outreach/character-commission-draft.md`.
- 18a: `Characters/GolmokCharacterSubsystem.{h,cpp}`, 순수 `GolmokCharacterMath.h`, `Config/Golmok/characters.json`, `docs/spec/characters.schema.json`.
- 테스트: `Tests/GolmokCharacterRosterTest.cpp`, `Tests/GolmokCharacterRosterPortalTest.cpp`의 `Golmok.Character.*`, `test_ue_character_roster_math.py`+stdin C++ driver, `test_ue_config_characters.py`.
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
5. 검증 뒤 scoped movement update 안에서 메시·오프셋·스케일·ABP·initial offset cache·카메라·속도·현재 id를 갱신한 다음 캡슐 크기/중심을 바꾼다. 지연된 부모 이동보다 자식 메시 상대변환을 먼저 설정해야 실제 Z offset이 유지된다. scope 종료 때 overlap을 알리므로 관찰자는 완성된 교체 상태를 본다. 유효한 로스터 메시 적용에 성공하면 ini 메시 실패 시 보였던 대체 캡슐만 숨긴다(자식 전파 없음). actor hidden/collision flags·ViewTarget·time dilation은 건드리지 않는다. 로드가 동기식이므로 첫 교체 히치는 V-11에 측정 항목으로 남긴다.

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
- UE `Golmok.Character.PortalRoundTrip`: L_ZoneTest/합성 실내에서 실제 overlap·문 평면 판정으로3회 왕복. 문 앞 확대/진입 뒤 축소/실내 교체·표식 아래 확대 거절, 동일 폰/발 위치/실내 유지·해제를 검사. 이동을 멈추고 캡슐 위치를 지정하므로 실제 보행·시각 품질 검증과 구별한다.
- 실제 GUI 포털 왕복·실내 교체·Quinn 스켈레톤·사진/그림자 품질은 V-11/V-12 기록. Python 성공을 UE 성공으로 대체하지 않는다.

### 18b 개요

①/V-11 이후 V-12와 V-08을 거쳐 ② 승인 → 인간 최종 원화·에셋 1종 발주 → 스킨/IK Retargeter·가산 포즈 → 아이들/포토 포즈 → 의상/헤어 확장 순서. Mutable은 옷/체형 조합이 많아져 단순 모듈 조합보다 이득이 확인될 때만 도입한다.

선택 화면: Slate C++(바이너리 최소·D-003 일치)와 UMG 레이아웃+전부 C++ 로직(디자이너 검수 편의)을 비교해, Phase2 초반에는 **UMG 레이아웃·C++ 로직**을 권장한다. 18a에는 선택 화면 없음. WP-15 세이브에 character_id+스키마 버전, 없는 id는 default 복구를 추가한다. 입력 키는 현 F1~F10/1~4, WP-12 P·WASD/EQ·Space/Enter·괄호·쉼표·N/M·Z/C·F/H/O/R·Shift를 피하고 UI 액션으로 배치, 최종 키는 입력 충돌표 작성 후 승인. `Tab` 후보이나 예약하지 않는다. Photo 메타 JSON에 character_id를 추가할 때 Photo 소유자가 스키마/테스트를 함께 바꾼다.

### V-12 절차·채점

Fable PC 세션이 실 Zone(없으면 L_Basemap_Yeonnam)에서 회색 콘크리트·붉은 벽돌·초록 대문·간판 색면 배경 4곳을 선정한다. 실명 간판/인물이 없는 검수 가능 구도만 저장한다. 18a 키/폭 프록시 2개 × 재질3안(Toon은 5.8 Substrate 실험 기능, 기존 설정 후처리는 별도 대조군) × 조명4프리셋, 기본 거리와 얼굴0.5m/사진 f2.8·f8을 같은 위치에서 비교한다. 없는 배경은 무지 색판으로 대체했다고 기록한다.

소유자가 배경 조화·실루엣·사진 매력·발밑/벽 그림자·비율 감각을 각1~5로 채점한다. 먼저 대표 배경1곳에서 프록시2×재질3×조명4를 비교하고, 채택 후보 구성을 배경4곳에서 기본 거리/얼굴0.5m의 f2.8·f8로 재검증한다. **채택할 각 구성**의 필수 배경·조명·시점별 점수를 남기고, 그 구성 평균4 이상·개별 항목3 미만 없음이 권장 통과 가설이다. 여러 재질이나 밝은 프리셋의 평균으로 실패한 구성을 덮지 않는다. 천장/계단 관통·그림자 수신 실패는 점수와 별도 blocker다. 캐릭터당 프레임 GPU ms·VRAM peak와 D-010 경로를 같이 적는다.

비교의 통제 조건:

- PBR/장난감 기준은 같은 프로젝트·맵·프록시·카메라/노출·해상도·DLSS·그림자 설정에서 재질만 바꾼다. Toon용 별도 로컬 사본에도 **같은 PBR 대조군**을 두고 렌더 설정 차이와 대조군 차이를 함께 기록한다. 프로젝트 간 차이를 Toon 재질의 효과로 단정하지 않는다. Toon이 해당 엔진/렌더 경로에서 실패하면 미지원/미실행으로 남기고 PBR 검증을 계속한다. Toon 성공은 PBR 채택의 필수 조건이 아니다.
- 기존 night 프리셋은 화면이 검게 나오는 문제가 기록돼 있다(`design/lighting-night-lookdev.md`). 원래 프리셋 샷을 남기고 환경 조명 문제와 캐릭터 재질 결함을 구분한다. 임의 광원/노출 변경본은 별도 보정 실험으로 표시한다. 필수 야간 판정이 불가능하면 해당 구성의 V-12는 **부분 완료**이며 평균에서 빼고 합격으로 만들지 않는다.
- 프록시 검증 통과는 룩/카메라의 제작 가설을 좁히는 결과다. 최종 얼굴·성인 연령감·정확한4.5등신 승인은 정합된 인간 원화, 머리/팔다리를 수정한 별도 프록시의 V-08 동작 영상, 최종 납품 에셋 검수가 있어야 한다. 18a 전체 스케일 프록시와 AI 무드만으로 이 승인을 대신하지 않는다.

## 완료 기준

설계 A~D·원문 확인 수준·권장안·이미지 LFS·D-018 결정 묶음. 18a 기본 동작 유지·새/기존 테스트·Python/CI 초록·표지와 독립 훅 커밋·V-11 런북. UE 헤드리스는 이 PC UE5.8.3에서 실제 실행하고 GUI/최종 품질은 확인한 만큼만 표기한다.

## 주의

공개 저장소에 Fab·외주 원본 넣지 않음. default ini 불변. 처음 로드가 실패하면 기존 플레이가 가능해야 한다. 돈이 드는 일/외부 메시지 발송 없음. 에디터 GUI 실행 전 `gui-foreground.lock` 확인, fps 측정은 다른 UE 프로세스 없을 때만. 원문 확인 못한 항목은 사실로 확정하지 않는다.

## 결과

2026-09-26~27, 별도 worktree에서 실행했다. [설계 PR #22](https://github.com/wooklym/golmok/pull/22) → [구현 PR #23](https://github.com/wooklym/golmok/pull/23) 순서다. 아래 초기 실행 뒤 캡슐 복구 수정·포털 통합 자동화·자체 리뷰와 병합 문안 반영을 추가했다. 설계67ee125 동기화는 충돌 없이 완료했고, 자체 리뷰 반영442d52f 동기화에서는 이 문서 상태 머리말만 충돌해 승인/리뷰 기록과 구현 완료를 함께 보존했다.

| 산출물 | 상태·근거 |
|---|---|
| A~D / B6 | 완료. 아트3안·후보6종/N1·KIPRIS6건 검색식·제작6경로·UE5.8 원문·D-018·외주 의뢰서 초안. 조건 미확인은 각 표에 남김 |
| A4 이미지 | 최종7장1536×1024 JPG, 로컬 git LFS pointer7개·업로드 완료. 모든 그림에 컨셉 표시, 실제 입력 프롬프트 별도 문서. 모루빛 무드의 연령감/얼굴 일치·정확한 등신은 최종 인간 원화 검수 필요 |
| 로스터/스키마 | 완료. Manny/Quinn/proxy135/proxy110, default Manny. [스키마](../spec/characters.schema.json)와 실제 JSON·유한수/관계 검증, 오류 시 전체 거절 |
| 런타임/콘솔 | 완료. WorldSubsystem+빙의 델리게이트, 같은 폰 교체, `golmok.character list\|<id>`, 발밑/달리기 상태 보존·천장 겹침 거절. UI/저장/새 키/발소리 연결 없음 |
| 훅 | 5ecb47f `GolmokCharacter` public 속도 setter, d530c3d 콘솔 등록 목록. 두 독립 커밋·표지, 기존 줄 삭제0 |
| Python 게이트 | 설계: ruff/check_repo 성공, format93개, pytest590 passed/39 skipped. 구현: ruff/check_repo 성공, format95개, pytest608 passed/42 skipped. 양쪽208 warnings, 로컬 g++ skip 포함 |
| CI 코드 검증 | b8105f2의 [Actions](https://github.com/wooklym/golmok/actions/runs/36248981836) 전체5 jobs success. Linux3.11/3.12·Windows3.12+MinGW 각각647 passed/3 skipped. 최신 head checks도 PR에서 확인 |
| UE5.8.3 | add-mannequin·build 성공. Character 필터2 Success. 합성 실내 준비 후 전체 **18 Success(13+경고5), failed0/notRun0**, 39.11s. Movement180/500cm/s·점프90cm, 기존 테스트 수정 없음 |
| V-11/V-12 | [PC 런북](../runbooks/pc-verify-wp18a.md) 완료. **GUI 포털과 교체 조합·실내 교체·WP-12 실제 사진·최초 로드 hitch/VRAM·V-12 채점 미실행**. V-11 전체 완료로 표시하지 않음 |

UE 실행에서 `FScopedMovementUpdate` include 경로와 부모 캡슐의 지연 이동 후 메시 offset이−92로 남는 문제를 발견했다. 메시 상대변환을 먼저 적용하는 순서로 수정한 뒤−69/고정 발밑 단언과 전체 회귀 테스트가 통과했다. 전체 UE 경고5건은 L_Dev GeoOrigin/의도된 누락 Zone 자산·버전 fixture 경고이며 개별 state는 전부 Success다. nullrhi의 HUD fps는 성능 결과로 사용하지 않았다.

최종 동기화 때 main은5c6f225이며 WP-12(`claude/hopeful-allen-f0a0jb`)와 공통 파일은 `test_ue_wp09_fixture.py` 한 개다. WP-12가 먼저 병합되면 photo 줄 먼저/character 줄 뒤로 보존한다. `pc/v08-animation`과 파일 충돌은 없다. 구매·발주·외부 의뢰 발송·새 라이선스 의존성 설치는 하지 않았다. 다음 실행은 D-018 ①/Fable 리뷰 뒤 V-11 GUI, WP-12 통합, V-12 및 V-08의 실제4.5등신 프록시 시험이다.

### 2026-09-27 리뷰 지적 수정

[Claude 코드리뷰의 지적](https://github.com/wooklym/golmok/pull/23#discussion_r4111832801)을 반영했다. ini 메시 로드 실패로 대체 캡슐이 표시된 상태에서 로스터 메시를 정상 적용하면 캡슐만 숨긴다. 실패한 선택은 대체 표시를 유지한다. 회귀 검사는 메시가 없는 상태에서 잘못된 id 거절 → 정상 프록시 적용 → 캡슐 숨김 및 메시/Actor 표시 유지를 확인한다. 이 리뷰는 코드 읽기만 수행했다고 명시되어 있으며 Fable ultracode 리뷰 조건의 충족 근거로 간주하지 않는다.

수정 후 UE5.8.3 빌드 성공, Character 필터2 Success, 전체 **18 Success(13+경고5), failed0/notRun0, 39.87s**. Python ruff/check_repo 성공, format95개, pytest **608 passed/42 skipped/208 warnings, 40.12s**. 경고와 로컬 g++ skip은 위 결과와 같다. 리뷰의 향후 uncrouch 참고사항은 현재 crouch 미지원 범위에 해당하며, crouch를 도입할 때 CDO 캡슐/메시 오프셋 복원과 로스터 크기 유지의 통합 검사가 필요하다.

당시 소유자의 병합 실행 승인은 있었으나 별도의 Fable 사전 리뷰 조건을 확인 중이었다. 이후 소유자가 설계 자체 리뷰 후 머지를 지시해 이번 두 PR의 검토/병합 방식을 확정했다(아래 리뷰 절). V-11 GUI와 WP-12 실제 포토 통합은 계속 미실행 상태다.

### 2026-09-27 V-11 포털 통합 자동화 보강

`GolmokCharacterRosterPortalTest.cpp`를 레인 안에 추가했다. 문 앞 확대, 진입 후 축소, 실내 확대 거절/성공, 실내3초 이상 유지, 출구 통과 후3초 해제를 실제 포털 overlap과 틱으로 **3회 왕복**했다. 동일 폰/Controller·XY/발 위치·문 평면 거리·실내 조명·서브레벨/Zone 수명을 검사한다. 첫 실행의 실내 Quinn 실패는 공중 표식 큐브 아래 확대가 막힌 것이므로, 이를 거절 사례로 남기고 옆으로150cm 이동한 뒤 성공을 검사했다. 런타임 코드를 완화하지 않았다.

빌드 성공, Character **3 Success**, 전체 **19 Success(14+경고5), failed0/notRun0, 63.79s**. 새 통합 검사24.08s에 `cycle 1/3`, `2/3`, `3/3 complete`가 전부 기록됐다. Python/ruff/check_repo도 통과(608 passed/42 skipped/208 warnings, 32.85s). 합성 맵/실내가 없으면 `NOT EXECUTED` 경고를 내므로 실행 로그 없이 통합 통과로 기록하지 않는다. UBT가 새 C++를 발견하도록 `-gather`로 소스 목록을 갱신한 뒤 실제 컴파일을 확인했다.

자동화는 이동을 멈추고 캡슐 위치를 지정했다. GUI 보행·계단·Quinn 애니메이션/화면·실제 경로 재생·WP-12 포토·hitch/VRAM·V-12 채점은 여전히 후속 검증이다. 다른 레인/핫스팟 변경은 추가하지 않았다.

## 리뷰 — 2026-09-27 Astra 자체 검토

소유자의 “설계 부분 문제없는지 자체 리뷰하고 머지해” 지시로 이번 #22/#23의 Fable 사전 리뷰를 Astra 자체 리뷰로 대체하고 Astra가 병합한다. 이 예외는 이번 두 PR에 한정하며 상시 협업 규칙과 최종 엔진 품질 판정·② 지출 승인을 바꾸지 않는다. 승인 대상은 D-018 ①의 제작/시험 가설과 18a 범위다.

| 검토 | 판정·조치 |
|---|---|
| A~D 요구사항·MVP | 후보6종/첫세트1종·이미지7장·제작6경로·외주 초안·18a/18b 경계가 있다. UI/저장/새 키/최종 에셋은18a에 들어가지 않음 |
| 구현 계약 | 구현 PR의 JSON4종·스키마·수학 헤더·기본 리터럴·동일 폰/고정 발밑·실패 원자성·포털/포토/경로 경계를 대조. 설계의 기본 수치와 일치. 구현의 캡슐 복구 수정/실제 포털3회 왕복·전체UE19 Success는 #23에 기록 |
| V-12 비교의 공정성 | **보완**: 별도 Toon 프로젝트의 PBR 대조군과 설정 기록을 요구. 실험 기능 실패를 PBR 채택 차단으로 취급하지 않음 |
| V-12 합격 기준 | **보완**: 채택할 구성별·필수 조건별 점수, 야간 환경 실패의 부분 완료, 최종 원화/리타깃/납품 검수를 구분. 좋은 조건의 평균으로 실패나 미실행을 가리지 않음 |
| 이미지/리그 | 7장 원본 육안 검토, 컨셉 표시·가상 장소/무지 소품 확인. c01 무드의 어린 연령감·정/측/후 치수 정합과 c05 세 발의 모든 뷰 정합은 최종 원화 검수 항목. 휴머노이드와 세 발 비휴머노이드 구분 유지 |
| 예산·저장·권리 | VRAM 계산(BC7/BC5 각4K16MiB, mip 포함 텍스처160MiB)과 고/저사양 조건, 기존 ignore/UFS와 cook 미보장 확인. 가격·공수는 확인일/추정 표기이며 발주 승인이 아님. Fab 전체 계약·지역/학습 조건·상표 최종 검토는② 전에 해소 |
| 원문 재확인 | 2026-09-27 [OpenAI Content](https://openai.com/policies/row-terms-of-use/)의 출력 소유/비독점성과 [Steam 설문](https://partner.steamgames.com/doc/gettingstarted/contentsurvey?language=english)의 출하 콘텐츠 중심 범위를 다시 확인. Epic5.8 릴리스 노트 웹 재접근은 timeout; 기존 직접 열람 기록을 유지하고 로컬5.8.3의 `ToonProfile.h` 존재를 확인. 이를 엔진 룩 합격으로 쓰지 않음 |

판정: 위 문서 보완 후 **설계/18a 병합을 막을 확정 결함은 발견하지 못했다**. 이는 자체 검토이며 독립 Fable 적대적 리뷰 완료나 최종 아트/권리 비침해 보증을 뜻하지 않는다. V-11 GUI·WP-12 실통합·V-12·V-08 비율 리타깃과 D-018 ②는 계속 후속이다.

설계 수정/공유 문안 반영 뒤 로컬 게이트: ruff check·format93개·check_repo·diff check 성공, pytest **590 passed/39 skipped/208 warnings, 36.48s**. 최종 설계 head의 CI도 병합 전에 확인한다. 39 skip 중 로컬 g++ 부재를 CI 교차검증으로 보완한다.

## 병합 시 반영

최종 병합 준비 기록(2026-09-27): 설계 #22는 **497566f**로 main에 병합했다. #23 base를 main으로 바꾸고 `git merge origin/main`으로 동기화했다. 이미 받은 설계442d52f와 같아 추가 파일 충돌/코드 변경은 없었다. 앞선 설계 동기화의 유일한 충돌은 이 문서 상태 머리말이며 구현 결과와 새 승인/리뷰 기록을 모두 보존했다. 최종 로컬 재검증: UE 빌드 성공·**19 Success(14+경고5), failed0/notRun0, 63.89s**, Python **608 passed/42 skipped/208 warnings, 33.27s**, ruff/format95개/check_repo/diff check 통과. 구현 소스/테스트는 이 재검증 이후 불변이며 최종 head CI 확인 뒤 merge commit으로 병합한다.

2026-09-27: 사용자에게 위임받은 Astra가 STATUS·DECISIONS(D-002/D-018)·ROADMAP·DEVELOPMENT-PLAN·game-features-proposal에 아래 문안을 반영했다. #22는 설계/스택 상태를, #23은 설계·18a 코드 완료 및V-11 GUI·WP-12 포토·V-12 대기를 기록한다. 이 병합 기록은 실제 에셋 발주·최종 품질 승인이 아니다.

### D-018 | ① 승인·② 대기 | 2026-09-27 — 캐릭터 선택·교체와 고유 캐릭터 제작

- 권장 시점: **18a는 Phase1 M7 품질 검증 기반**, 콘솔·데이터만. 18b의 실제 캐릭터1종은 V-08/V-12/② 뒤 M7 여유 시, 선택 UI·저장·커스터마이즈는 **Phase2 초반 WP-15와 함께**. Phase1 MVP에 메뉴/세이브를 추가하지 않는다.
- 제안: 스타일라이즈드 PBR·135cm/4.5등신·GASP+스타일 보정 가설, 첫 세트 c01 1종, 인간 외주 최종 제작, 같은 폰에서 로스터 교체.
- 규모: 설계PR+18aPR, PC V-11/V-12, 18b 아트160~280h/4~7주 가설(견적 아님), 리타깃·UI/저장은 별도 산정.
- 의존: V-08 소스 스켈레톤·라이선스, WP-12, D-010 그림자 수신체, WP-13 세트키, WP-15.
- 리스크: 작은 비율의 성인 모캡/손 관통, 캡슐 변경·포털, splat 접지, AI 참고 이미지 권리/상표, 동기 로드 히치/VRAM, 비공개 에셋 재현성.
- **① 승인(2026-09-27)**: 룩/애니메이션 가설·비율 시험, 후보 c01 한 종(이름은 상표 확인 전 가칭), 18a 범위, V-11/V-12 채점·18b 시점. 이번 #22/#23은 사용자 지시로 Astra 자체 리뷰·병합한다.
- **소유자 결정 필요 ②**: V-12/V-08 뒤 최종 룩/비율, 상표 최종 명칭과 검토, 외주 예산·업체·권리양도 계약/수정 범위, 비공개 에셋 저장소·협업자 범위, 필요 도구/라이선스 확인, 출시 AI표시 자문. **모든 지출은 ② 이후**.

### 다른 문서에 반영한 문안 (최초 제안 보관)

- STATUS WP-18: “설계/18a 코드·검증 상태는 WP-18 결과 절 참조. D-018 ①·Fable 리뷰 대기. 18b는 V-08/V-12/② 뒤.” V-11: “pc-verify-wp18a의 헤드리스·GUI 미검증 항목 진행.” V-12: “Fable 실행/소유자 채점, 프록시2×재질3×조명4, 실제4.5등신 리타깃은 V-08 추가 시험.” 결정 필요에 D-018 ①/② 링크.
- DEVELOPMENT-PLAN §1.3: “캐릭터 선택·교체/커스터마이즈는 D-018 제안: Phase1 콘솔 검증, Phase2 UI·세이브. 수집 요소는 미등록.” §11: D-018 두 단계 결정을 별도 행으로 추가.
- ROADMAP 1.3 행: “캐릭터 선택·교체(WP-18): 18a 템플릿 로스터·콘솔·동일 폰, V-11; 18b 최종 에셋·리타깃은 V-12/② 뒤. 기본 조작 유지.”
- game-features-proposal의 캐릭터 줄: “D-018 제안 등록(WP-18): c01 우선1종·18a 기반, 커스터마이즈 UI/저장은 Phase2 WP-15와 함께.”
- D-002 후보 행: “WP-18 OpenAI 이미지: 공개 컨셉 참고자료만, A5 약관/저작물성 조건 참조. 템플릿 마네킹: 기존 UE 설치 Examples, 로컬 복사·커밋 없음. Meshy/VRoid/VRM4U/MetaHuman/Fab 구매·신규 의존성은 이번에 채택하지 않음. 외주 계약/에셋은 D-018 ② 후 항목별 기록.”
- **V-08 추가 시험 문안**: “135cm·4.5등신(머리30cm), 넓은 몸/짧은 다리의 임시 휴머노이드 프록시에 GASP를 IK Retargeter로 적용. 18a 전체 스케일 proxy135는 카메라/키 비교에만 사용하고 머리/팔다리 비율을 조정한 프록시를 별도로 준비한다. 리타깃만/팔·상체 가산 보정/키프레임 기준 영상 비교. 145/380cm/s, 정지→걷기→달리기→180도 턴→25cm 계단. 팔-머리/배 관통 횟수, 접지 발 미끄러짐(cm), 성인 보폭 느낌, 자연스러움과 귀여움을 각각 채점. 다른 리그를 호환 스켈레톤 지정만으로 실행하지 않는다.”
