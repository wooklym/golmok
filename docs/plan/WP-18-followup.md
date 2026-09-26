# WP-18 후속 — 실제 경로·포토 통합·렌더 증거

2026-09-27 · ChatGPT Astra · 기준 main `3c8f1b0` · 브랜치 `astra/wp-18-followup`

사용자의 후속 작업 지시에 따라 [V-11 런북](../runbooks/pc-verify-wp18a.md)의 미검증 항목을 진행한다. 이번 변경은 캐릭터 레인의 검증 코드와 문서다. 게임 런타임·공유 설정·최종 룩·발주② 결정은 바꾸지 않는다.

## 검증 설계와 결과

| 항목 | 검증 방법 | 결과 |
|---|---|---|
| 실제 경로 재생과 선택 유지 | `Golmok.Character.PathRoundTrip`: proxy135 선택 → 실제 `StartPlayback` → 경로 폰 빙의 중 교체 거절 → 2초 경로의 자연 종료 → 같은 원래 폰·선택·메시/캡슐·FOV·속도 복원 → Quinn 교체 | **실행 통과**. 임시 경로는 GUID 이름으로 Saved 아래 만들고 정리한다. 보행·영상 검수와는 구별 |
| 실제 WP-12와 로스터 | `Golmok.Character.PhotoIntegration`: proxy135/proxy110/Quinn × GamePause/TimeDilation, 총6조합. 카메라 갱신 후 FOV/캡슐 앵커 상속, 실제 여러 틱에 걸친 교체 거절·숨김/위치/메시/시간 배율 보존, 종료 복원과 교체 재개 | **테스트 구현·통합 브랜치에서 해당 파일 컴파일 완료, 실행 차단**. WP-12 자체의 UE5.8 접근 오류는 아래 기록. main에는 Photo가 없어 `NOT EXECUTED` 경고 |
| 렌더 증거 | `Golmok.Character.RenderEvidence`: 명시적 실행 옵션으로만 두 프록시 × 조명4종, Quinn/Manny 정오 대조, 프록시 붐1.5배 진단 구도. 기존 템플릿 PBR·L_Dev·정면·원래 조명값. 게임 뷰포트만 저장 | **D3D12 실제 렌더12장 저장·디코딩 확인**, 대표 구도 육안 검토. 야간 미가시성 재현. 본 V-12의 실 배경·재질3안·얼굴/DOF·소유자 채점과 구별 |
| GUI 조작 | `computer-use`로 L_Dev standalone 게임에서 콘솔·Space·F1 입력 | 사용자 보안 창 처리 후 **4종 교체·점프/착지·잘못된 ID 거절 확인**. 기본 카메라 구도와 HUD 좌표를 관찰하고 엔진 캡처4장 저장. 지속 보행·달리기·계단·포털 영상은 미완 |

`__has_include("Photo/GolmokPhotoModeSubsystem.h")`는 테스트의 컴파일 경계다. Photo가 없는 빌드에서 가짜 서브시스템으로 대체하지 않는다. WP-12가 들어오면 동일 테스트가 실제 Photo API를 컴파일·실행한다. 기본 헤드리스에서 렌더 증거도 `NOT EXECUTED`로 남는다. 두 경고를 테스트 통과 개수에 섞어 연동/화질 성공으로 읽지 않는다.

## WP-12 실행 차단 재현

- 읽은 원격 [초안 PR #19](https://github.com/wooklym/golmok/pull/19): `0806da880d2fc7855b3ca6fd52be6a7143900411`, open/draft, 미병합.
- 로컬 `astra/wp-18-photo-integration`의 `1d321fb`는 캐릭터 테스트 `ad57159`와 WP-12를 결합한 **검증용 병합**이다. 공개 main/상대 브랜치를 변경하지 않았다.
- 충돌은 `docs/plan/STATUS.md` 한 곳이며 main 문안을 유지했다. 콘솔 목록의 photo·character 등록은 모두 보존했다.
- UE5.8.3 `Build.bat ... -gather`: 새 `GolmokCharacterRosterPhotoTest.cpp` 컴파일 성공. WP-12 아래 7곳의 C2248 때문에 전체 빌드 실패. 런타임 검사는 시작하지 않았다.

| 원격 WP-12 소스 위치 | 원인 | 소유 레인 수정 시 필요한 조건 |
|---|---|---|
| `Photo/GolmokPhotoModeSubsystem.cpp`: 912, 970, 975, 1161 / `Tests/GolmokPhotoTest.cpp`: 276, 367 | `APlayerController::bShouldPerformFullTickWhenPaused`가 UE5.8.3에서 protected | 프로젝트 PlayerController에 원래 값 보존이 가능한 좁은 접근자/설정자를 두고 Photo와 테스트가 사용해야 한다. 엔진 소스나 접근제어 매크로를 바꾸지 않는다 |
| `Photo/GolmokPhotoModeSubsystem.cpp`: 920 | `UGameViewportClient::bSuppressTransitionMessage`가 protected | 원래 suppression 상태의 정확한 저장·복원이 가능한 프로젝트 측 계약이 필요. 무조건 false로 복원하면 다른 상태를 잃는다 |

설치 엔진 원문 확인: `PlayerController.h:1730`, `GameViewportClient.h:118`. `ShouldPerformFullTickWhenPaused()`는 공개지만 `PlayerController.cpp:6599`에서 raw bit 외 XR 조건도 OR하므로 원래 bit의 정확한 스냅샷과 동일하지 않다. `SetSuppressTransitionMessage(bool)`는 공개 setter이나 대응하는 raw getter는 해당 헤더에 없다. 따라서 컴파일만 통과시키려고 상태 보존을 삭제하지 않았다.

위 파일들은 [AGENTS §4](../../AGENTS.md)의 Photo/기존 테스트 레인이다. 이번에는 소유 코드 수정 없이 실패를 재현하고, 재검증용 캐릭터 테스트를 준비했다. 전체 로그는 로컬 `unreal/Golmok/Saved/Automation/WP18Followup/wp12-build-failure.txt`에 보관했다.

## 게이트

| 실행 대상 | 결과 |
|---|---|
| main 기반 Python | ruff check·format95·check_repo 통과, **608 passed / 42 skipped / 208 warnings, 33.00s** |
| main 기반 UE5.8.3 | 빌드 성공. 전체 보고서 **22 Success = 15 + 경고7**, failed0/notRun0, 66.59s. 이 중 PhotoIntegration·RenderEvidence 2개는 명시적 **NOT EXECUTED**이므로 실제 실행 성공은 기존19+새 경로1=**20개** |
| 로컬 WP-12 통합 Python | ruff check·format98·check_repo 통과, **671 passed / 59 skipped / 208 warnings, 35.30s**. Python 통과가 UE 컴파일 오류를 검출하지 못했음 |
| 로컬 WP-12 통합 UE | 위 protected 접근 오류로 빌드 실패. 사진 조합6개·사진 저장·DOF 미실행 |

기존 UE 경고5는 이전 WP-18 기록과 같다. 새 헤드리스 보고서 `Saved/Automation/WP18Followup/main-report.json`, 실행 로그 `main-tests.txt`는 로컬 보관이며 원본 에셋/GUI 화면을 공개 저장소에 추가하지 않았다. g++ 교차검사는 CI에서 확인한다.

## GPU 렌더 관찰

최종 렌더 실행: 코드 `8bbf7ae`, UE5.8.3 / **D3D12** / 기존 Lumen·VSM·TSR 설정, `-RenderOffscreen`의 게임 뷰포트. RenderEvidence **1 Success, 경고0/실패0/미실행0, 74.18s**. 명령은1280×720을 요청했지만 실제 PIE 캡처는 **1014×550**이므로 후자를 결과 해상도로 기록한다. 이미지의 디코딩·크기12건과 SHA256을 로컬 `evidence.json`에 저장했다.

저장 위치(이 worktree 아래): `unreal/Golmok/Saved/Automation/WP18Render/20260926-181308-D7BC08DD464E1EB65DB6ADBFE805C5B9/`. 보고서 `Saved/Automation/WP18Followup/render-wide-report/index.json`, 모아보기 `render-review.md`, 로그 `Saved/Logs/WP18-RenderWide.log`. 생성물은 ignored이며 정식 원화/납품 에셋이 아니다.

| 관찰 | 의미·후속 |
|---|---|
| 주간 Quinn/Manny·두 프록시가 실제 메시/재질·정지 포즈로 보임 | 로드 성공의 화면 근거. 실제 걷기·달리기 애니메이션/리타깃 판정을 대신하지 않음 |
| `night`에서 발광 가슴 표식 외 캐릭터·배경이 거의 검음 | **야간 판정 불가 재현**. 밝은 프리셋 평균에 숨기지 않음. 조명 레인의 야간 보정 실험이 필요 |
| 기본 피치0·기본 붐에서 프록시 발끝이 화면 하단에 잘림 | 그 구도로 접지를 채점하지 않음. 기본 샷을 보존하고 테스트 안에서만 붐1.5배(135:390cm, 110:340cm) 진단 샷을 추가. 해당 두 샷에서 발 전체와 바닥 그림자가 보임 |
| 첫 Quinn 선택의 동기 CPU 작업88.584ms(앞선 별도 실행103.812ms) | 첫 메시 로드 지연을 후속 측정해야 할 근거. 두 프록시는 이미 로드된 Manny를 공유한다. 측정은 `SelectCharacter` API 전체 시간이며 GPU 프레임/VRAM/cold-cache 벤치마크가 아님 |

자체 검토: 테스트만으로 게임 코드를 바꾸지 않으며, 캡처 옵션/실행 여부와 결과 경계를 분리했다. 야간 문제·카메라 구도·로드 지연을 임의 합격으로 처리하지 않았다. V-12 최종 룩·비율과 D-018② 판단은 여전히 미실행/미승인이다.

## 보안 창 처리 뒤 GUI 검증

2026-09-27 03:48–03:57 KST, 코드 `26c27af`. 사용자가 보안 창을 허용한 뒤 별도 worktree의 L_Dev를 `UnrealEditor.exe <project> /Game/Golmok/Maps/L_Dev -game -windowed -ResX=1280 -ResY=720 -NoSound`로 실행했다. **에디터 PIE가 아닌 standalone 게임 창**, UE5.8.3 D3D12 SM6이며 레벨 기본 조명을 사용했다. F1 HUD의 `tod: (level)`을 특정 조명 프리셋으로 표기하지 않는다.

| 확인한 동작 | 화면·로그 근거 |
|---|---|
| `golmok.character list` | Manny/Quinn/proxy135/proxy110의 한·영 이름4종, default/current=manny 로그 |
| Manny → Quinn → proxy135 → proxy110 → Manny | 각 `selected` 로그, 메시·체형·카메라 구도 변경. HUD의 XY는−500/0 유지, 착지 후 중심Z는94/71/58/94cm(정수 표시). 캡슐 반높이 변경과 일치하며 정확한 발 위치 단언은 기존 Runtime 자동화가 담당 |
| 각4종에서 Space 점프 → 착지 | 공중 점프 포즈와 바닥 그림자 분리, 다음 관찰에서 정지 포즈/착지 높이 복귀. 관찰한 정지·점프 프레임에는 T-pose가 없음. 연속 영상·보행 주기·리타깃 품질 판정은 하지 않음 |
| proxy110에서 `missing_id` | `unknown id 'missing_id'` 로그 뒤 프록시와 XY/Z·카메라 구도 유지. 이후 Manny 복귀 성공 |
| 기본 카메라 접지 구도 | 두 프록시 발끝이 하단에 잘리는 현상 재현. 기본 카메라를 수정하지 않았으며, 전신 접지 비교는 위 붐1.5배 진단 샷을 별도로 사용 |

기존 `golmok.screenshot` 명령으로 `Saved/Screenshots/Golmok/wp18-gui-resume/current/`에 `quinn_idle.png`, `proxy135_idle.png`, `proxy110_idle.png`, `manny_restored.png`를 저장했다. 창 렌더는1280×720, 엔진 HighResShot2배의 **실제 PNG4장은2560×1440**다. 모두 디코딩·크기·SHA256을 확인했다. 메타데이터와 모아보기는 `Saved/Automation/WP18Followup/gui-evidence.json`, `gui-review.md`, 실행 로그는 `Saved/Logs/WP18-GUI-Resume.log`에 있다. 점프의 일시적 화면 관찰은 이 정지 PNG4장과 구별한다. 파일은 ignored이며 공개 저장소에 올리지 않는다.

입력 도구는 키를 길게 누르는 기능을 제공하지 않는다. W 단발 입력에서 지속 이동을 입증하지 못했으므로 **보행/달리기 전환, 25cm 턱·80cm 통로·계단·붐 충돌, 포털 왕복 영상, PIE 재시작은 미완**이다. 화면 HUD의 fps는 이동·해상도·워밍업 조건을 통제한 벤치마크가 아니므로 성능 합격 근거로 쓰지 않는다. 검증 뒤 게임을 정상 종료하고 이 세션의 GUI 잠금을 해제했다. WP-12 컴파일 차단과 V-12 룩 검증의 남은 범위는 그대로다.

GUI 기록 반영 후 Python 게이트 재실행: ruff check·format95·check_repo 통과, **608 passed / 42 skipped / 208 warnings, 33.09s**. 이번 추가 변경은 문서2개뿐이므로 UE 빌드/전체 자동화는 위 코드 검증 결과를 유지한다.

## 병합 시 반영

- V-11: 실제 경로 폰 왕복·선택 복원 자동화와 standalone GUI4종 교체·점프·착지·잘못된 ID 거절 확인을 추가한다. GUI 보행·계단·포털 영상과 사진 통합은 아직 완료 표시하지 않는다.
- WP-12/V-09: 위 `0806da8`의 UE5.8.3 컴파일 차단 두 종류를 소유 PC 세션에서 해결하고, Character.PhotoIntegration과 기존 Photo 검사를 같이 실행한다.
- V-12: 템플릿 렌더 증거는 환경/캡처 준비 검증이다. 실 배경4곳·PBR/Toon/장난감 비교·얼굴0.5m/f2.8/f8·GPU/VRAM·소유자 채점과 실제4.5등신 리타깃은 별도다.
- 이번 변경의 최종 리뷰·병합 기록과 CI는 후속 PR에 남긴다. #22/#23에 한정한 자체 리뷰 예외를 독립 Fable 검토로 확대해 표기하지 않는다.
