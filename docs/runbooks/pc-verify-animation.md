# PC 평가 런북 — 캐릭터 애니메이션 3안 비교 (V-08, WP-10)

대상: PC Claude 세션 + 사용자(§0 라이선스 확인과 §5 채점은 **사용자**). 전제: V-01 통과(`L_Dev`, 마네킹 `add-mannequin.ps1`, `tools\ue\test.ps1`의 `Golmok.Player.Movement` 통과).
소요: 라이선스 확인 15분 + 다운로드·Create Project 30~60분 + 시험 2~3시간. 근거·3안 설명: [`research/09-animation-ue58.md`](../research/09-animation-ue58.md).
결과는 이 문서 하단 §8, `docs/plan/STATUS.md` V-08 행, ROADMAP 1.3 애니메이션 행에 적는다.

규칙:
- **main 작업 트리의 `unreal/Golmok`을 바로 고치지 않는다.** 시험은 새 브랜치 `pc/v08-animation`에서. GASP 에셋은 Migrate 뒤 `Content/Golmok_AnimEval/`(시험 전용 폴더)로 모아 두고 그 밖의 기존 `Content` 폴더는 건드리지 않는다(Migrate 자체는 `Content` 루트를 대상으로 하며 GASP의 폴더 경로를 그대로 만든다 — §3-1). 채택 전에는 에셋을 **커밋하지 않는다**(`.gitignore`에 없으면 `git status`에서 추적하지 않은 채로 둔다). **`git add -A`/`git add .` 금지** — 커밋할 경로(런북·스크린샷·ini)만 이름으로 지정한다(수 GB 에셋이 LFS로 딸려 들어가는 것을 막음).
- 라이선스(§0)가 확인되기 전에는 GASP 에셋을 Golmok 프로젝트로 옮기지 않는다(GASP 프로젝트 안에서 보는 것은 괜찮다).
- 코드 변경이 필요하면(ini 경로, Trajectory 컴포넌트) 커밋 메시지 접두어 `V-08:`로 같은 브랜치에 두고 PR 본문에 "시험용"이라고 적는다. 채택 결정 전 main 병합 금지.
- 돈이 드는 것(유료 모션 팩 등)은 사지 않는다.

## 0. 라이선스 확인 (사용자, 필수)
클라우드 세션은 아래 페이지를 열지 못했다(403). 브라우저로 열어 **해당 문단을 그대로 복사**해 §8 표와 `docs/DECISIONS.md` D-002에 붙인다.
1. Fab의 "Game Animation Sample Project" 리스팅(GASP 공식 문서가 링크: https://www.fab.com/listings/880e319a-a59e-4ed2-b268-b32dac7fa016) → 오른쪽 **Details**의 라이선스 표기(Standard / CC-BY / legacy UE Marketplace License / 기타).
2. https://www.fab.com/eula — Standard License의 허용(상용 프로젝트 배포, 수정)·금지(원본 재배포, 생성형 AI 학습 등) 조항, **Epic이 만든 콘텐츠나 "Unreal Engine 전용" 콘텐츠에 붙는 추가 조건**.
3. https://www.unrealengine.com/eula/unreal — 엔진 동봉 콘텐츠(Third Person 템플릿 마네킹) 조항(①·③안에 해당).
4. 판정: 상용 게임에 넣어 배포 가능 + 비상업 조건 없음 → 진행. 그 외(비상업, 조건 불명확) → ②를 중단하고 ①/③만 평가, STATUS에 "결정 필요"로 적는다.

## 1. GASP 받기와 둘러보기 (GASP 프로젝트 안에서)
1. Epic 런처 → Fab에서 GASP를 라이브러리에 추가(가격을 확인하고 **결제가 필요하면 멈추고 사용자에게 묻는다**) → Library의 Vault → **Create Project**(엔진 5.8, 위치 `D:\UE\GASP_58` 등 저장소 밖).
2. 열어서 PIE. 기본 레벨에서 걷기·뛰기·정지·급회전·계단·경사를 1분 체험. 게임패드도 연결해 본다.
3. 기록(§8 표 1):
   - 프로젝트 `Content` 폴더 용량, `Animations` 하위 시퀀스 개수(콘텐츠 브라우저 필터 Animation Sequence).
   - `.uproject`의 `Plugins` 목록(파일을 텍스트로 열어 복사) → Golmok `.uproject`와 차이.
   - Edit → Plugins에서 **Pose Search / Chooser / Motion Warping / Animation Warping**의 Beta·Experimental 표시.
   - 캐릭터 스켈레톤 이름(`SK_UEFN_Mannequin` 등)과 Golmok의 `SKM_Manny_Simple` 스켈레톤이 같은지(메시 에디터 → Skeleton 항목).
   - 1080p PIE `stat unit`의 Game/Draw/GPU ms(참고용).

## 2. ① 기준선 촬영 (Golmok, 현행)
1. `git switch -c pc/v08-animation`(WP-10 병합 후 main 최신에서). `.\tools\ue\build.ps1` → `.\tools\ue\open-editor.ps1`.
2. `L_Dev` PIE. 아래 **관찰 시나리오**를 그대로 수행하며 화면 녹화(Windows Game Bar `Win+Alt+R`, 각 20~40초):
   - S1 걷기 출발·정지(W 짧게 3회), S2 달리기 출발·정지(Shift+W), S3 180° 급회전(W↔S), S4 원 그리기(W+마우스), S5 계단 10단 오르내리기(`Course/Stairs`), S6 12° 경사, S7 60 cm 벽 점프·착지, S8 게임패드: 스틱 살짝(걷기 느린 속도 `MinAnalogWalkSpeed`) → 끝까지 → 왼스틱 누름(달리기) → A(점프).
3. 스크린샷: `golmok.hud 0` 뒤 `golmok.screenshot v08_1 <장면>`(`<tag>` 인자 필수 — 없으면 usage 경고만 남김; PNG는 `Saved/Screenshots/Golmok/<tag>/<preset>/`에 생김). 장면: 계단 중간(발과 디딤판), 정지 직후, 경사 위 서 있기. JPG로 변환·축소(각 300 KB 이하)해 `docs/runbooks/pc-verify-animation-1-<장면>.jpg`로 복사한다.
4. 성능 기준선: §3-6과 같은 절차(`csvprofile start` → S4 30초 → `csvprofile stop` → `golmok-perf`).
5. `.\tools\ue\test.ps1 -Filter Golmok.Player.Movement` 통과 확인(기준값).

## 3. ② GASP 이식 시험
1. **GASP 프로젝트에서** 로코모션에 필요한 것만 고른다: `ABP_SandboxCharacter`(또는 문서의 Retarget용 `ABP_GenericRetarget`), 그것이 참조하는 Pose Search Schema/Database, Chooser 테이블, 애니메이션 시퀀스, 캐릭터 메시·스켈레톤. 우클릭 → **Asset Actions → Migrate** → 대상 `…\golmok\unreal\Golmok\Content`(Migrate가 GASP의 원래 폴더 경로를 그대로 만든다). **덮어쓰기를 묻는 창이 뜨면 거절한다** — GASP가 `/Game/Characters/Mannequins/…`처럼 `add-mannequin.ps1` 에셋과 같은 경로를 쓰면 현행 캐릭터(①)가 바뀐다(해당 여부 [미확인]). 충돌이 있으면 빈 임시 UE 프로젝트로 먼저 Migrate해 폴더 목록을 확인하고, 겹치는 폴더는 **GASP 프로젝트 안에서 먼저 이름을 바꾼 뒤**(예: `Characters` → `GASP_Characters`, 리디렉터 Fix Up) 다시 Migrate한다. 생긴 폴더 목록을 §8 표 2에 적고(주의: `Content/Characters/`는 `.gitignore`라 `git status`에 안 보인다), 마이그레이션 뒤 Golmok에서 `Content/Golmok_AnimEval/`로 모아 옮긴다(Fix Up Redirectors).
   - Traversal(ledge·vault)·Smart Object·MetaHuman 폴더는 제외 가능하면 제외. 참조 때문에 딸려 오면 그대로 두고 기록.
2. §1에서 적은 플러그인 중 Golmok에 없는 것을 Edit → Plugins에서 켠다 → 에디터 재시작 → `.uproject` 차이를 기록(커밋은 시험 브랜치에만).
3. **바인딩**(두 방법 중 하나, 쉬운 것부터):
   - (a) ini만: `Config/DefaultGame.ini`의 `CharacterMeshPath`·`AnimClassPath`를 이식한 메시·ABP로 바꾼다. ABP가 `CBP_SandboxCharacter`로 캐스트하는 곳이 있으면 컴파일 경고/런타임 None이 나온다 → 그 노드를 `Character`/`CharacterMovementComponent` 기반으로 바꾼다(ABP 안, 최소 수정). 궤적이 필요하면 캐릭터에 **Character Trajectory** 컴포넌트를 붙여야 한다 → (b).
   - (b) 시험용 BP 서브클래스: `AGolmokCharacter`를 부모로 BP `BP_GolmokCharacter_AnimEval`을 만들고(저장 위치 `Content/Golmok_AnimEval/`) Character Trajectory 컴포넌트 추가, 메시·ABP 지정, 게임모드 오버라이드는 `L_Dev` 사본(`L_Dev_AnimEval`, 같은 폴더에 저장)의 World Settings에서만. (채택되면 C++로 옮기는 것은 후속 WP.)
   - 스켈레톤이 다르면(§1 기록) GASP 문서 "Importing Your Own Character" 절차(IK Rig → IK Retargeter, 소스 UEFN_Mannequin)를 따르거나, 가장 쉬운 길로 **GASP의 캐릭터 메시를 그대로** 쓴다(시험 목적).
4. C++ 이동 값은 바꾸지 않는다(걷기 180·달리기 500 cm/s). GASP ABP가 다른 속도를 기대해 발이 미끄러지면 그 사실을 기록한다(§8 표 2 "속도 불일치").
5. §2의 S1~S8 녹화·스크린샷을 같은 방법으로(`golmok.screenshot v08_2 <장면>` → `pc-verify-animation-2-<장면>.jpg`).
6. 성능: `golmok.path play`는 캐릭터가 아닌 재생 폰으로 카메라만 움직이므로 애니메이션 비용을 재지 못한다. 대신 1080p PIE(Editor Preferences → Play → New Editor Window 크기 1920×1080, "Play in New Editor Window")나 `-game`에서 콘솔 `csvprofile start` → **S4 원 그리기 달리기를 30초** → `csvprofile stop` → `golmok-perf <csv>`로 평균·1% low를 ①과 같은 방법으로 잰다(①도 같은 절차로 한 번). CSV 위치: PIE는 `unreal/Golmok/Saved/Profiling/CSV/`, `-game`(런처 엔진)은 `%LOCALAPPDATA%\UnrealEngine\5.8\Saved\Profiling\CSV\`(V-01 기록). `stat anim`의 Pose Search 관련 줄 ms도 적는다.
7. `test.ps1 -Filter Golmok.Player.Movement`를 다시 돌린다(애니메이션 교체가 이동 수치를 바꾸지 않아야 함; 루트 모션을 켜지 않았는지 확인).

## 4. ③ 최소 구성 (②가 라이선스·용량·성능·스켈레톤 중 하나로 막혔을 때만)
1. Pose Search 플러그인만 켠다. 템플릿 마네킹 애니메이션(`Content/Characters/Mannequins/Anims/Unarmed/`의 Idle·Walk·Jog 계열)으로 Pose Search Schema 1개(Trajectory·Pose 채널 기본값) + Database 1개.
2. `ABP_Unarmed` 복제본(`ABP_Unarmed_MM`, `Content/Golmok_AnimEval/`)의 로코모션 상태를 Motion Matching 노드 하나로 교체. Character Trajectory 컴포넌트는 §3-3(b)와 같은 BP 서브클래스로.
3. S1~S8 녹화·스크린샷(`golmok.screenshot v08_3 <장면>` → `pc-verify-animation-3-<장면>.jpg`), 성능 측정은 §3-6과 같다.

## 5. 채점표 (사용자가 녹화를 보고 채점)
각 항목 1~5점(5 = 실제 사람처럼 자연스럽다, 3 = 눈에 띄지만 거슬리지 않음, 1 = 몰입을 깸). 같은 녹화를 나란히 놓고 본다.

| # | 항목 | 보는 장면 | ① | ② | ③ |
|---|---|---|---|---|---|
| 1 | 자연스러움(전체 인상) | S1~S4 | | | |
| 2 | 발 미끄러짐(정지·출발·회전 중 발이 바닥에서 미끄러지나) | S1 S2 S3 | | | |
| 3 | 전환(걷기↔달리기↔정지↔점프 사이 튐·끊김) | S2 S7 | | | |
| 4 | 계단·경사(발이 디딤판에 붙나, 무릎 굽힘) | S5 S6 | | | |
| 5 | 조작감(입력 반응 지연, 게임패드 아날로그 속도 표현) | S8 | | | |
| 6 | 비용: 1080p 평균 fps / 1% low (수치) | §3-6(①은 §2에서 같은 절차) | | | |
| 7 | 비용: 에셋 용량(MB), 켠 플러그인 수, 작업 시간(h) | §1·§3 | | | |

판정 기준(권장): ②가 1~5 합계에서 ①보다 **4점 이상** 높고, 성능 조건 둘 중 하나를 만족하고(평균 fps 하락 **5% 이하**, 또는 하락이 5%를 넘어도 1080p 평균 **60 fps 이상** 유지 — 예: 158 → 140 fps는 통과; 1% low는 기록해 두고 판정 때 참고), 용량이 LFS 여유 안이면 ② 채택 제안. 차이가 작으면 ①(단순함 우선), ②가 막히면 ③ 결과로 같은 판정.

## 6. 실패 시 대안
| 증상 | 대안 |
|---|---|
| 라이선스가 비상업·불명확 | ② 중단, ①/③만. STATUS "결정 필요"에 원문 인용 |
| Migrate 뒤 ABP 컴파일 에러(캐스트·누락 변수) | 에러 노드만 `Character`/CMC 기반으로 교체. 10개 넘으면 GASP 프로젝트 안에서 `CBP_SandboxCharacter`의 부모를 `GolmokCharacter`와 같은 설정으로 흉내 내는 대신, ③으로 |
| 스켈레톤 불일치로 리타깃이 어긋남 | GASP 메시를 그대로 쓴 시험으로 품질만 먼저 판단 → 채택 시 리타깃은 후속 작업 |
| 발 미끄러짐이 ①보다 나쁨(속도 불일치) | GASP 기대 속도를 기록만 하고 C++ 값은 그대로. 채택 결정 때 속도 조정 여부를 함께 결정 |
| fps 하락 > 5% | Motion Matching Database LOD(GASP 위젯) 낮춰 재측정, Leg IK 끄고 재측정 → 원인 분리 |
| 빌드·에디터 크래시 | 로그 `Saved/Logs/Golmok.log` 마지막 50줄을 §8에 붙이고 ① 유지 |

## 7. 정리
- 시험 뒤 `Content/Golmok_AnimEval/`·`L_Dev_AnimEval`·켠 플러그인은 **채택 전까지 커밋하지 않는다**. 브랜치에는 이 런북 §8 결과·스크린샷(작게)·(있다면) ini/`.uproject` 시험 변경만 커밋.
- main으로 돌아가기 전 정리: 채택되지 않았으면 `Content/Golmok_AnimEval/`과 Migrate가 만든 GASP 폴더를 저장소 밖(예: `D:\UE\golmok_animeval_backup\`)으로 옮기고, `.uproject`·ini의 시험 변경을 되돌린다(`git checkout -- unreal/Golmok/Golmok.uproject unreal/Golmok/Config/`). 플러그인이 꺼진 상태에서 GASP 에셋이 남아 있으면 에디터가 로드 경고를 낸다. 채택 대기면 브랜치에 그대로 두고 `.gitignore`에 `Content/Golmok_AnimEval/`를 넣어 `git status`가 깨끗한지 확인.
- 채택되면 후속 작업(WP 또는 PC 작업 카드): 캐릭터 C++에 Trajectory 컴포넌트, ini 경로, 에셋 LFS 커밋, D-002 표 기록.

## 8. 결과 (PC 세션·사용자가 작성)

표 1 — 라이선스·GASP 정보

§0 확인 경위: 2026-09-26 PC 세션(Fable 5.1)이 Claude 내장 브라우저로 세 페이지를 열어 국문 표시와 영문 원문(`?lang=en-US`; 두 계약 모두 "지배 언어는 영어")을 그대로 복사했다. 런북 §0은 **사용자 확인**을 요구하므로 아래 인용은 사용자가 같은 URL에서 재확인한 뒤 확정한다.

| 항목 | 값 |
|---|---|
| GASP 리스팅 라이선스(원문) | https://www.fab.com/listings/880e319a-a59e-4ed2-b268-b32dac7fa016 — 판매자 **Epic Games**, 가격 **무료**("Free"), 상세 정보 "**라이선스 조건: 스탠다드 라이선스**"("License terms: Standard License"), "AI 사용 허용: 아니요"("Allows usage with AI: No"), "AI로 생성됨: 아니요", 설명 끝 "**언리얼 엔진 전용 콘텐츠 - 언리얼 엔진 기반 제품에서만 사용할 수 있습니다.**", 호환 엔진 5.4–5.8, 배포 방식 "Complete project", 마지막 업데이트 2026년 8월 18일, 퍼블리싱 2024년 6월 11일. 설명: "500+ of game-ready animations compatible with the UE5 Mannequin Skeleton through runtime retargeting." |
| Fab EULA 관련 조항(원문) | https://www.fab.com/eula (Last updated: October 1st, 2024; §16(i) "the controlling language for this Agreement is English"). 요약(비구속, 페이지 상단): "You may: Use the assets commercially or privately / Modify and adjust the assets in order to incorporate them into your Projects / Commercially distribute your Projects with the Fab assets incorporated into it / Use the assets with any compatible tools (usage is not limited to Unreal Engine) / Share the asset (directly, via a private repository or in the Project) with your collaborators that are working on the Project with you. You may not: Resell or redistribute the asset for free on a standalone basis or allow others to do the same." (국문: "허용 사항: 에셋을 상업적으로나 사적으로 사용 … Fab 에셋이 통합된 프로젝트를 상업적으로 배포 … 금지 사항: 에셋을 무료로 독자적으로 재판매 또는 재배포하거나 타인이 그렇게 하도록 허용"). 구속 조항: **§3(a)** "A 'Standard License' grants you a non-exclusive and non-transferable license to privately use, reproduce, display, perform, and modify the Content in accordance with the terms of this Agreement." **§4(c)** "you may Distribute a Project that incorporates Content as an included dependency to end users. When you make such a Distribution, you may, however, only authorize end users to make use of Content solely as incorporated in the Project in object code and you must restrict end users from extracting or otherwise using Content outside of the Project. … you may Distribute software applications (such as video games) that include Content to the general public". **§5(a)** "you may not Distribute Content on a standalone basis to third parties except to your collaborators (either directly or through a third-party repository) … you may share Content with your employees, affiliates, and contractors in a private online repository while you work on a Project together." **§6(a)** "you may not combine Content under a Standard License with code or content that is licensed under any of the following licenses: GNU General Public License (GPL), Lesser GPL (LGPL) (unless you are merely dynamically linking a shared library), or Creative Commons Attribution-ShareAlike License." **§6(b)(vii)·§16(l)** NoAI: "Content that is tagged with 'NoAI' … you may not use NoAI Content (a) in datasets utilized by Generative AI Programs, (b) in the development of Generative AI Programs, or (c) as training inputs to Generative AI Programs." **§7(a)** "Any Content you acquired (whether free or paid) prior to the modified terms will remain governed by the license terms applicable at the time when you acquired the Content." Epic 제작 콘텐츠에 붙는 별도 조건은 EULA 본문에 없고, 리스팅의 "언리얼 엔진 전용 콘텐츠" 표기가 그 조건이다(UE EULA §4(a)(i) "certain assets that we make available under separate agreements are available for use only with Unreal Engine"). |
| UE EULA 엔진 콘텐츠 조항(원문) | https://www.unrealengine.com/eula/unreal (§18(e) 지배 언어 영어). **§1** "The Licensed Technology licensed to you under this Agreement includes all Unreal Engine code and related Epic-provided content that you access when you download, use, or install Unreal Engine. This includes Engine Code, Examples, and Starter Content." / "'Examples' means the code, artwork, or other content made available by us in the Samples and Templates folders in the install directory." (국문 "'예시(Examples)'란 설치 디렉터리의 샘플 및 템플릿 폴더에서 사용할 수 있도록 당사가 만든 코드, 아트워크 또는 기타 콘텐츠를 의미합니다.") / "Licensed Technology does not include any items, assets, content, or other materials that we may make available to you in other ways … For example, assets you may download from an Epic-operated online marketplace (including, but not limited to, Fab) are not Licensed Technology and are not licensed to you under the terms of this Agreement." **§4** "Any Product that you Distribute that incorporates Licensed Technology must incorporate the Licensed Technology only in object code and only as an inseparable part of the Product." **§4(a)(i)** "Please note that certain assets that we make available under separate agreements are available for use only with Unreal Engine." **§5(b)** "You may Distribute Examples (including as modified by you) in Source Code or object code to any third party." **§6(c)** 비호환 라이선스(GPL, LGPL(동적 링크 제외), CC-BY-SA)와 결합 금지. → 템플릿 마네킹(`Templates/TemplateResources/…`, ①·③)은 **Examples**로 UE EULA(로열티 조건은 제품 전체와 동일)의 적용을 받고, GASP(Fab)는 UE EULA가 아니라 **Fab EULA**의 적용을 받는다. |
| **§0 판정(PC 세션; 사용자 재확인 필요)** | **상용 게임 배포 가능 + 비상업 조건 없음 → ② 진행.** 부대 조건: (1) 언리얼 엔진 전용(우리는 UE 제품이라 충족), (2) NoAI — GASP 에셋을 생성형 AI 학습·개발에 쓰지 않음, (3) **독자 재배포 금지(§5(a))** — 원본 에셋은 협업자·비공개 저장소로만 공유 가능한데 `github.com/wooklym/golmok`은 **공개 저장소**(API 응답 200, 2026-09-26)라 **채택해도 GASP 에셋을 이 저장소에 커밋할 수 없다**(마네킹처럼 로컬 Vault에서 스크립트로 복사하거나 비공개 LFS 저장소가 필요 — 사용자 결정), (4) GPL/LGPL(정적)/CC-BY-SA 콘텐츠와 결합 금지 → D-002에 추가. |
| GASP Content 용량 / 시퀀스 수 | |
| GASP 플러그인 목록(Golmok에 없는 것) | |
| 플러그인 성숙도 표시(Pose Search 등) | 엔진 5.8.3 설치본의 `.uplugin` 플래그(에디터 Plugins 창의 Beta/Experimental 배지가 읽는 값) [확인: `Engine/Plugins/…/*.uplugin`, 2026-09-26]: **Pose Search** — `Animation/PoseSearch`, 플래그 없음(정식) · **Chooser** — `Engine/Plugins/Chooser`, 플래그 없음(정식; 5.8 문서 배너는 Experimental → research/09 §2.3, 문서와 플러그인 표기가 다름) · **Motion Warping** — `IsBetaVersion: true` · **Animation Warping** — 플래그 없음 · **Motion Trajectory**(Character Trajectory 컴포넌트가 든 플러그인) — `Experimental/Animation/MotionTrajectory`, **`IsExperimentalVersion: true`** · **Animation Locomotion Library** — `IsBetaVersion: true`. |
| 스켈레톤 동일 여부 | |

표 2 — 시험 기록

| 안 | 바인딩 방법 | 문제·수정 | 1080p 평균 / 1% low | 스크린샷 |
|---|---|---|---|---|
| ① | 현행 | | | |
| ② | | | | |
| ③ | | | | |

채점(§5 표 복사) · 결론(채택 제안 안과 이유) · 사용자 결정:
