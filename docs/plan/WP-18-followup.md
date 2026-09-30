# WP-18 후속 — 이동·실제 경로·포토 통합·렌더 증거

2026-09-27 · ChatGPT Astra · 최초 기준 main `3c8f1b0` · 최초 브랜치 `astra/wp-18-followup`(PR #24 병합·닫힘)

**2026-09-28 T1 현재 상태**: main `045cbe3`에서 시작해 `d37720e`를 병합한 새 `astra/wp-18-review-fixes`. WP-12는 main `939207e`에 병합됐고 당시 컴파일 차단은 해소됐다. 아래 2026-09-27 실행 기록은 그때의 결과로 보존한다. `PauseMode`는 `Enter()`에서 래치되며 `GetRestoreState().PauseMode`로 확인 가능하다. 현재 V-09 런북 자동화 총계는 26개다. [PR #27](https://github.com/wooklym/golmok/pull/27)은 26/26과 PhotoIntegration 6조합 실행을 보고한다 [2차: PC 세션 보고, Astra T2 직접 실행 결과 아님]. T1 처리·게이트는 문서 끝에 기록한다.

사용자의 후속 작업 지시에 따라 [V-11 런북](../runbooks/pc-verify-wp18a.md)의 미검증 항목을 진행한다. 이번 변경은 캐릭터 레인의 검증 코드와 문서다. 게임 런타임·공유 설정·최종 룩·발주② 결정은 바꾸지 않는다.

## 검증 설계와 결과

| 항목 | 검증 방법 | 결과 |
|---|---|---|
| 실제 경로 재생과 선택 유지 | `Golmok.Character.PathRoundTrip`: proxy135 선택 → 실제 `StartPlayback` → 경로 폰 빙의 중 교체 거절 → 2초 경로의 자연 종료 → 같은 원래 폰·선택·메시/캡슐·FOV·속도 복원 → Quinn 교체 | **실행 통과**. 임시 경로는 GUID 이름으로 Saved 아래 만들고 정리한다. 보행·영상 검수와는 구별 |
| 실제 WP-12와 로스터 | `Golmok.Character.PhotoIntegration`: proxy135/proxy110/Quinn × GamePause/TimeDilation, 총6조합. 카메라 갱신 후 FOV/캡슐 앵커 상속, 실제 여러 틱에 걸친 교체 거절·숨김/위치/메시/시간 배율 보존, 종료 복원과 교체 재개 | **당시 해당 파일 오류 없음, 실행 전**. 전체 빌드는 WP-12 자체의 UE5.8 접근 오류로 실패(아래 기록). 당시 main에는 Photo가 없어 `NOT EXECUTED` 경고 |
| 렌더 증거 | `Golmok.Character.RenderEvidence`: 명시적 실행 옵션으로만 두 프록시 × 조명4종, Quinn/Manny 정오 대조, 프록시 붐1.5배 진단 구도. 기존 템플릿 PBR·L_Dev·정면·원래 조명값. 게임 뷰포트만 저장 | **D3D12 실제 렌더12장 저장·디코딩 확인**, 대표 구도 육안 검토. 야간 미가시성 재현. 본 V-12의 실 배경·재질3안·얼굴/DOF·소유자 채점과 구별 |
| GUI 조작 | `computer-use`로 L_Dev standalone 게임에서 콘솔·Space·F1 입력 | 사용자 보안 창 처리 후 **4종 교체·점프/착지·잘못된 ID 거절 확인**. 기본 카메라 구도와 HUD 좌표를 관찰하고 엔진 캡처4장 저장. 지속 보행·달리기·계단·포털 영상은 미완 |
| 지속 입력·지형 통과 | `Golmok.Character.Locomotion`: 실제 InputKey/Enhanced Input으로4종의 달리기 중 교체·걷기 복귀, 점프,25cm 턱/40cm 장애물,80cm 통로, 계단 왕복, 카메라 충돌 | **실행 통과**, 필터1 Success/경고0/실패0,83.82s. 위치 배치는 코스 출발점에만 사용. nullrhi 물리 검사이며 GUI 보행 영상/애니메이션 품질 판정은 별도 |

`__has_include("Photo/GolmokPhotoModeSubsystem.h")`는 테스트의 컴파일 경계다. Photo가 없는 빌드에서 가짜 서브시스템으로 대체하지 않는다. WP-12가 들어오면 동일 테스트가 실제 Photo API를 컴파일·실행한다. 기본 헤드리스에서 렌더 증거도 `NOT EXECUTED`로 남는다. 두 경고를 테스트 통과 개수에 섞어 연동/화질 성공으로 읽지 않는다.

## WP-12 실행 차단 재현

- 읽은 원격 [초안 PR #19](https://github.com/wooklym/golmok/pull/19): `0806da880d2fc7855b3ca6fd52be6a7143900411`, open/draft, 미병합.
- 로컬 `astra/wp-18-photo-integration`의 `1d321fb`는 캐릭터 테스트 `ad57159`와 WP-12를 결합한 **검증용 병합**이다. 공개 main/상대 브랜치를 변경하지 않았다.
- 충돌은 `docs/plan/STATUS.md` 한 곳이며 main 문안을 유지했다. 콘솔 목록의 photo·character 등록은 모두 보존했다.
- UE5.8.3 `Build.bat ... -gather`: 새 `GolmokCharacterRosterPhotoTest.cpp`는 해당 파일 오류 없음, 실행 전. WP-12 아래 7곳의 C2248 때문에 전체 빌드 실패. 런타임 검사는 시작하지 않았다.

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

## 지속 보행·달리기·지형 기능 검증

2026-09-27 후속으로 `Tests/GolmokCharacterRosterMovementTest.cpp`를 추가했다. 기존 `Golmok.Player.Movement`의 실제 `APlayerController::InputKey` 패턴을 사용하며 게임 런타임·기존 이동 테스트·공유 설정을 바꾸지 않는다. 각 코스 시작점만 배치하고, **측정 구간은 키를 누른 상태로 유지한 채 여러 게임 틱 동안 실제 이동·충돌**로 통과한다. Shift+W를 해제하지 않고 다른 로스터를 적용한 뒤 속도와 전진 거리, 폰/XY/캡슐 바닥 보존을 확인한다.

| 캐릭터 | 교체 뒤 달리기 실측 | Shift 해제 뒤 걷기 실측 | 점프 정점 | 80cm 통로 |
|---|---|---|---|---|
| Manny | 500cm/s | 180cm/s | 89.99cm | 폭84cm 캡슐이 입구에서 차단 |
| Quinn | 500cm/s | 180cm/s | 89.99cm | 폭84cm 캡슐이 입구에서 차단 |
| proxy135 | 380cm/s | 145cm/s | 89.99cm | 폭67.2cm 캡슐 통과, 내부에서 Manny 확대 거절 후145cm/s 유지 |
| proxy110 | 310cm/s | 120cm/s | 89.99cm | 폭67.2cm 캡슐 통과, 내부에서 Manny 확대 거절 후120cm/s 유지 |

4종 모두 키 해제 뒤 정지,25cm 턱 통과,40cm 장애물 앞 차단, L_Dev의17cm×10계단을 걸어 올라170cm 랜딩 도달 후 하강, 벽면에서 붐 수축/열린 방향 복귀를 통과했다. 계단 랜딩의 캡슐 바닥은171.91–172.07cm, 내려온 바닥은2.15–2.37cm였다. 이는 CharacterMovement의 바닥 간격을 포함하며 메시 발본 위치/발 미끄러짐 측정은 아니다. 속도는 독립 계약 리터럴의 ±10%, 바닥 높이는 ±3cm로 검사한다. 차단 검사는 장애물까지 실제 접근한 위치와 정지 속도를 함께 요구한다.

최초 테스트 실행에서는 초기화의 키 해제와 누르기를 같은 프레임에 보내 첫 이동 구간이0cm/s로 실패했다. 해제 이벤트가 처리된 뒤 별도 준비 단계에서 누르도록 테스트를 수정하자 기존 게임 코드 변경 없이4종 전 구간이 통과했다. 초기 실패 보고서도 `Saved/Automation/WP18Followup/locomotion-initial-report.json`에 보관했다. 실패를 성공으로 바꾸려고 속도 단언이나 장애물 조건을 완화하지 않았다.

최종 필터 결과: **1 Success, 경고0/실패0/미실행0,83.82s**. UE5.8.3 빌드 성공. 결과 `Saved/Automation/WP18Followup/locomotion-report.json`, 로그 `Saved/Logs/WP18-Locomotion.log`.

전체 UE 회귀: **23 Success(16+경고7), failed0/notRun0,149.37s**. 이 중 PhotoIntegration/RenderEvidence의 명시적 NOT EXECUTED2개를 빼면 **실제 실행 성공21개**다. 새 Locomotion은 전체 실행에서도83.85s로 통과했고, 기존 Movement·캐릭터 포털3회 왕복·실제 경로·Zone 검사도 통과했다. 보고서 `Saved/Automation/WP18Followup/locomotion-full-report.json`, 출력 `locomotion-full-tests.txt`, 로그 `Saved/Logs/WP18-LocomotionFull.log`. Python 최종 게이트: **608 passed / 42 skipped / 208 warnings,33.57s**, ruff check/format95/check_repo 성공.

V-11의 지속 이동·지형 항목은 이제 **물리/입력 자동화 확인, GUI 영상·애니메이션 품질 대기**로 구분한다. 단발 GUI 입력의 제약은 남아 있으며, 위 테스트를 실제 키보드 플레이 영상이나 최종 리타깃 품질 합격으로 표기하지 않는다. WP-12 원격 head는 여전히 `0806da8`이며 포토 컴파일 차단 상태가 바뀌지 않았다.

## 병합 시 반영

- V-11: 실제 경로 폰 왕복·선택 복원,4종 지속 입력/달리기 중 교체/지형 통과 자동화와 standalone GUI4종 교체·점프·착지·잘못된 ID 거절 확인을 추가한다. GUI 보행·계단·포털 영상과 사진 통합은 아직 완료 표시하지 않는다.
- WP-12/V-09: 위 `0806da8`의 UE5.8.3 컴파일 차단 두 종류를 소유 PC 세션에서 해결하고, Character.PhotoIntegration과 기존 Photo 검사를 같이 실행한다.
- V-12: 템플릿 렌더 증거는 환경/캡처 준비 검증이다. 실 배경4곳·PBR/Toon/장난감 비교·얼굴0.5m/f2.8/f8·GPU/VRAM·소유자 채점과 실제4.5등신 리타깃은 별도다.
- 이번 변경의 최종 리뷰·병합 기록과 CI는 후속 PR에 남긴다. #22/#23에 한정한 자체 리뷰 예외를 독립 Fable 검토로 확대해 표기하지 않는다.

반영 기록(2026-09-27, 병합 세션 Fable, §7.6 4단계): 위 문안은 `WP-18: 병합 시 반영 (Fable)` 커밋으로 STATUS 병행 트랙 WP-18·V-11·V-12·V-09 행, ROADMAP 1.3 캐릭터 행, `WP-18-characters.md` "리뷰" 절에 옮겼다. WP-12(#19)는 이보다 먼저 main 939207e에 병합됐으므로 `PhotoIntegration` 6조합은 V-09 PC 검증의 전체 실행에서 돈다. 마지막 항목(후속 PR에 남긴다)은 §7.6과 어긋나 적용하지 않았다(리뷰 B3).


## T1 — PR #24 리뷰 후속 (2026-09-28)

| 항목 | 조치 |
|---|---|
| B1 | PathRoundTrip의 z=1000 시작 폰은 재빙의 뒤 중력이 작용하므로 복귀 위치는 XY만 0.01cm 이내 단언. 메시·캡슐·선택·FOV·속도 복원 단언 유지 |
| B2 | 이전 부분 컴파일 기록을 “해당 파일 오류 없음, 실행 전”으로 교정 |
| B4 | RenderEvidence/PhotoIntegration 단독 필터의 succeededWithWarnings 및 Succeeded: 0 예외, NOT EXECUTED 구분과 JSON 진단을 런북 §8에 명시 |
| B5 | Movement의 L_Dev 지형/좌표가 setup_dev_level.py에 의존함을 코드와 런북에 기록 |
| B6 | 런북 §8 제목과 §6 엔진 API/래치 상태 표 갱신 |
| B7 | 자동 재적용 실패의 CurrentId 잔류·실제 폰 확인 절차, 0.25s Controller 탐색과 Pawn 델리게이트 역할/한계를 §10에 보고. 런타임 변경 없음 |

B3·B8은 PR #24 병합 세션 처리 범위다. 이번 PR은 테스트 2파일과 캐릭터 문서 2파일만 변경한다. main `d37720e` 병합 충돌 없음. 공유 등록부 훅·설정 변경 없음.

### 직접 실행 근거

- UE5.8.3: add-mannequin 뒤 최초 전체 빌드 성공(156.41s), 최신 main 병합 뒤 증분 빌드 성공(19.57s).
- PathRoundTrip 단독: **1 Success, 경고0/실패0/미실행0**, 2.79s.
- RenderEvidence 단독, 렌더 opt-in 없음: **Succeeded: 0 / succeededWithWarnings: 1 / failed: 0 / notRun: 0**, test.ps1 예외 재현. 개별 state는 Success지만 NOT EXECUTED이므로 렌더 검증 통과로 세지 않는다.
- 최신 main 전체: **26 Success(19+경고7), failed0/notRun0**, 164.87s. RenderEvidence의 NOT EXECUTED 1개를 제외한 **실제 실행 성공 25개**. 나머지 경고는 Photo.MetaJson 및 synthetic Zone/Portal fixture 자산 관련이다.
- PhotoIntegration: proxy135/proxy110/quinn × GamePause/TimeDilation **6조합 모두 EXECUTED**, 경고0. Locomotion 4종, PathRoundTrip, PortalRoundTrip 3회도 실제 실행 통과. 이는 T1 회귀 결과이며 T2 GUI·시각 품질 완료로 확장하지 않는다.
- 로컬 증거(ignored): `Saved/Automation/T1/path-report.json`, `render-skip-report.json`, `full-report.json`, `build-main-log.txt`. 생성 L_Dev/Zone 테스트 맵과 로그는 커밋하지 않는다.

Python 게이트: ruff check·format(98파일), pytest **694 passed / 63 skipped / 208 warnings, 43.20s**, check_repo 통과. g++ 미설치 검사는 CI에서 확인한다. 코드 리뷰 Opus ultracode 대기, 설계/품질 가설 변경 없음. push 후 정지하고 비동기 리뷰를 받는다.

### 병합 시 반영 (T1, 완성 문안)

> WP-18 T1: PR #24 리뷰 B1·B2·B4·B5·B6·B7 보완. PathRoundTrip XY 복귀 단언과 fixture 의존성, 필터 경고 판정·엔진 API·CurrentId 잔류/Controller 폴링 한계를 기록했다. main d37720e 기준 UE5.8.3 빌드 및 전체 26 Success(경고7, failed0/notRun0); RenderEvidence NOT EXECUTED 1개를 제외한 실제 실행25개. Character.PhotoIntegration 6조합 직접 실행 성공. V-11 GUI 잔여·시각 품질과 V-12는 대기. T2 GUI는 V-09 §7 세션 종료·PC 가용성·GUI 잠금 확인 후 진행한다.


### PR #32 리뷰 수정 — STATUS 칸별 완성 문안

대상은 main `c7fa296`의 `docs/plan/STATUS.md` 병행 트랙 WP-18·V-11 행이다. 공유 파일은 직접 수정하지 않는다.

1. **WP-18 / 인계 메모**, 아래 문장을 교체한다.
   - 원문: 전체 UE 실행 23(실행 21 Success + 설계상 NOT EXECUTED 2: `PhotoIntegration`·`RenderEvidence`).
   - 대체: 전체 UE 26(실행 25 Success + NOT EXECUTED 1: `RenderEvidence`, main d37720e 기준 T1 [#32](https://github.com/wooklym/golmok/pull/32)).
2. **WP-18 / 인계 메모**, 아래 문구를 교체한다.
   - 원문: 비블로킹 B1~B8은 Astra T1(`astra-tasks.md`).
   - 대체: B1·B2·B4~B7은 T1 [#32](https://github.com/wooklym/golmok/pull/32) 반영, B3·B8은 #24 병합 세션 처리.
3. **V-11 / 인계 메모**, 대기 문장을 교체하고 통과 목록 끝에 한 문장을 추가한다.
   - 원문: 대기: GUI 보행·계단·포털 영상, PIE 재시작, 포토 통합(`PhotoIntegration` 6조합 — WP-12 병합됐으므로 V-09 전체 실행에서 함께), hitch/VRAM.
   - 대체: 대기: GUI 보행·계단·포털 영상, PIE 재시작, hitch/VRAM.
   - 통과 목록 추가: `PhotoIntegration` 6조합(proxy135/proxy110/quinn × GamePause/TimeDilation) T1 직접 실행 EXECUTED·경고 0([#32](https://github.com/wooklym/golmok/pull/32)).
4. **상태 칸 유지**: WP-18 `🟡 설계·코드·후속 자동화 완료·PC GUI 영상 대기`, V-11 `🟡 헤드리스·물리/입력 자동화 통과·GUI 영상 대기`. GUI·시각 품질이 남아 있으므로 🟢로 바꾸지 않는다.

리뷰 A1은 합성 경로 Y를 300cm로 옮겨 원래 폰의 Y=0과 전 구간 분리했다. 따라서 경로 마지막 위치에 폰을 방치하는 회귀가 XY 복원 단언에 걸린다. B-D2의 런북 네 곳은 T1 EXECUTED 6/6·경고0, T2 GUI·시각 대기로 통일했고, B-D4는 entries 배열의 메시지를 펼쳐 EXECUTED/NOT EXECUTED를 출력한다. 비블로킹 A2 자연 종료/Restart 주석, A3 `_build_course()` 위치도 반영했다.

수정 뒤 검증(main c7fa296): ruff check/format98·pytest **694 passed/63 skipped**(42.21s)·check_repo·diff --check 통과. UE5.8.3 빌드 성공(20.82s), 전체 **26 Success(19+경고7), failed0/notRun0**, 165.38s. 경로 XY 분리 후 PathRoundTrip 통과, PhotoIntegration EXECUTED6/6 유지, RenderEvidence NOT EXECUTED1은 실제 실행 수에서 제외. 증거 `Saved/Automation/T1/review-report.json`, `review-build.txt`(ignored).

반영 기록(2026-09-28, 병합 세션 Fable, §7.6 4단계): 위 칸별 문안 1~4는 `WP-18: 병합 시 반영 (Fable)` 커밋으로 STATUS 병행 트랙 WP-18·V-11 행, ROADMAP 1.3 캐릭터 행, `astra-tasks.md` T1, `WP-18-characters.md` 리뷰 절에 옮겼다. D-019(2026-09-27)에 따라 소유자 승인 없이 병합했다.


## T2 V-11 착수 기록 (2026-09-28 05시 UTC)

브랜치 astra/wp-18-v11-gui, main c16b5a7 기준. 이슈 #30의 V-09 §7 종료 통보 뒤 GUI 잠금·다른 UE 프로세스 없음 확인, 전용 worktree에서 실행했다.

| 항목 | 실제 실행 결과 |
|---|---|
| 빌드 | UE5.8.3 성공1.15s |
| PhotoIntegration | 1 Success, 경고/실패/notRun0, 5.38s. proxy135/proxy110/Quinn × GamePause/TimeDilation EXECUTED6줄 확인 |
| PIE 재시작 | L_Dev 에디터 GUI에서 Alt+P → 기본 캐릭터 화면 → 게임 콘솔 proxy135 교체 → Escape 종료 → Alt+P 재시작 → 캐릭터 화면 확인 → Escape 종료. 크래시 없음. 선택 유지/품질 채점은 별도 단언하지 않음 |
| 지속 보행/계단/포털 영상 | 미실행. 현 computer-use sky API는 press_key 탭만 제공하고 key-down/up·hold duration·영상 녹화 API가 없음. 단발 키를 지속 키 검증으로 대체하지 않음 |
| 초기 메시 실패→GUI 복구 | 미실행 |

증거는 로컬 Saved/Automation/WP18T2/photo-report.json 및 gui-session.log, GUI 스냅샷은 이 세션 도구 결과에 있다. 완성 영상/스크린샷 산출물 없음. **T2 부분 진행**, V-11 전체 완료/애니메이션 품질 합격 아님. native 입력 지속/녹화 대신 UE 드라이버로 렌더된 실행을 기록해도 되는지 또는 PC 세션에 영상 항목을 인계할지 오케스트레이터에 요청한다. GUI 종료 후 잠금을 해제하며 다른 세션은 건드리지 않는다.


## T2 엔진 입력 드라이버 렌더 근거 (2026-09-28 06시 UTC)

이슈 #30 코멘트 5863958089의 대체 증거 조건에 따라 main b0f583d에서 실행했다. **엔진 입력 드라이버 렌더 근거(실제 키보드 지속 입력·영상 아님)**다. WP-18/V-11은 🟡 유지하며, 보행 주기·관절·발 미끄러짐은 Fable 시각 리뷰 대기다. hitch/프레임 시간·VRAM 판정은 하지 않았다.

| 검증 | 결과와 한계 |
|---|---|
| D3D12 렌더 실행 | RenderEvidence opt-in에 `-GolmokCharacterSequence` 추가. D3D12_SM6, RTX5060, fixed sim dt=1/60, 1 Success·경고/실패/notRun0, 71.51s. nullrhi 사용 안 함 |
| 캡처 | 3종×3코스, PNG 총577장 디코딩 성공. 실제1014×550(요청960×540와 다름), 인접 sim 간격0.1s±0.002 확인. 코스당6초 이상 |
| 걷기→달리기 | W down부터3초 뒤 Shift down, 총6초. 시작 배치 뒤 실제 CharacterMovement로 이동 |
| 계단·포털 | L_Dev 계단 상승/하강 도착 및 캡슐 바닥 높이 단언 통과, L_ZoneTest 포털 안/밖 상태 왕복 단언 통과. 이동 중 순간이동 없음 |
| 초기 메시 실패 GUI | DefaultGame.ini 메시 경로를 임시 `/Game/Missing/T2Missing.T2Missing`로 바꾸고 L_Dev PIE 실행. `not found; showing capsule` 로그 재현. 로스터 기본 Manny가 BeginPlay(첫 프레임 전)에서 대체 캡슐을 덮고 숨기므로 ini만 바꾸는 절차로는 캡슐 화면이 재현되지 않는다. 콘솔 `golmok.character quinn` 입력·실행 뒤 Quinn 표시 확인. 오케스트레이터 D-019 결정(2026-09-28 #39 리뷰): 헤드리스 `Golmok.Character.Runtime` ApplyEntry 복구 검사와 T2 ini 실패 로그로 **대체·종결**, PC 카드로 넘기지 않음 |
| 정리 | PIE·검증 에디터 정상 종료, ini를 바이트 백업으로 복원(diff 없음), Astra GUI 잠금 해제. 타 세션 변경 없음 |

카메라는 진단용 붐1.5배·pitch−10, HUD off·clear_noon이다. 파일명의 sim은 코스 시작 기준 elapsed sim time이며 manifest에는 월드 sim과 elapsed를 함께 적었다. 첫 시도의 첫 구간0.0833초를 후처리 검사에서 발견해 첫 요청을0.1초로 고친 뒤 **전9코스를 재실행**했다. 아래는 재실행 결과만이다. 원본 PNG와 자동화 보고서는 로컬 `Saved/Automation/WP18T2Sequence/` 및 `WP18T2SequenceReport2/index.json`에 보관한다. GUI 로그는 `Saved/Automation/WP18T2/initial-mesh-gui.log`다.

콘택트 시트는 코스별 4×3 프레임 2장(전체 구간 균등 샘플 / 연속 = elapsed 1.1~2.2s 12프레임(걷기 코스는 걷기 구간만; 전체 달리기·계단 하강 연속 프레임은 로컬 PNG)), 긴 변1600px·각300KB 이하 JPG다. 선택된 샘플이므로 전체 움직임의 연속 영상으로 읽지 않는다. `capture.txt`의 해상도와 디코딩/간격 확인 줄은 실제 PNG를 읽은 후처리 결과다.

| 캐릭터·코스 | 길이/프레임 | 콘택트 시트 | 입력·프레임 기록 |
|---|---|---|---|
| proxy135 걷기/달리기 | 6.0000s / 60 | [전체](../images/characters/v11-sequence/proxy135_course0_1.jpg) · [연속](../images/characters/v11-sequence/proxy135_course0_2.jpg) | [capture.txt](../images/characters/v11-sequence/proxy135_course0-capture.txt) |
| proxy135 계단 왕복 | 7.1667s / 71 | [전체](../images/characters/v11-sequence/proxy135_course1_1.jpg) · [연속](../images/characters/v11-sequence/proxy135_course1_2.jpg) · [하강4.1~5.2s](../images/characters/v11-sequence/proxy135_course1_3.jpg) | [capture.txt](../images/characters/v11-sequence/proxy135_course1-capture.txt) |
| proxy135 포털 왕복 | 6.0000s / 60 | [전체](../images/characters/v11-sequence/proxy135_course2_1.jpg) · [연속](../images/characters/v11-sequence/proxy135_course2_2.jpg) | [capture.txt](../images/characters/v11-sequence/proxy135_course2-capture.txt) |
| proxy110 걷기/달리기 | 6.0000s / 60 | [전체](../images/characters/v11-sequence/proxy110_course0_1.jpg) · [연속](../images/characters/v11-sequence/proxy110_course0_2.jpg) | [capture.txt](../images/characters/v11-sequence/proxy110_course0-capture.txt) |
| proxy110 계단 왕복 | 8.6167s / 86 | [전체](../images/characters/v11-sequence/proxy110_course1_1.jpg) · [연속](../images/characters/v11-sequence/proxy110_course1_2.jpg) | [capture.txt](../images/characters/v11-sequence/proxy110_course1-capture.txt) |
| proxy110 포털 왕복 | 6.0000s / 60 | [전체](../images/characters/v11-sequence/proxy110_course2_1.jpg) · [연속](../images/characters/v11-sequence/proxy110_course2_2.jpg) | [capture.txt](../images/characters/v11-sequence/proxy110_course2-capture.txt) |
| quinn 걷기/달리기 | 6.0000s / 60 | [전체](../images/characters/v11-sequence/quinn_course0_1.jpg) · [연속](../images/characters/v11-sequence/quinn_course0_2.jpg) · [달리기3.1~4.2s](../images/characters/v11-sequence/quinn_course0_3.jpg) | [capture.txt](../images/characters/v11-sequence/quinn_course0-capture.txt) |
| quinn 계단 왕복 | 6.0000s / 60 | [전체](../images/characters/v11-sequence/quinn_course1_1.jpg) · [연속](../images/characters/v11-sequence/quinn_course1_2.jpg) | [capture.txt](../images/characters/v11-sequence/quinn_course1-capture.txt) |
| quinn 포털 왕복 | 6.0000s / 60 | [전체](../images/characters/v11-sequence/quinn_course2_1.jpg) · [연속](../images/characters/v11-sequence/quinn_course2_2.jpg) | [capture.txt](../images/characters/v11-sequence/quinn_course2-capture.txt) |

### 병합 시 반영 (T2, STATUS 칸별 완성 문안)

- **WP-18 / 상태**: 🟡 설계·코드·후속 자동화 완료·엔진 렌더 근거 확보·PC 영상/시각 판정 대기
- **WP-18 / 인계 메모 추가**: T2에서 proxy135/proxy110/quinn의 걷기3초→달리기3초·계단 왕복·포털 왕복 D3D12 InputKey 렌더 시퀀스9코스(577프레임)를 확보했다. 실제 키보드 지속 입력·영상 아님. 코스별 시트와 입력 타임라인은 WP-18-followup T2 절. 최종 시각 판정은 Fable 대기.
- **V-11 / 상태**: 🟡 헤드리스·물리/입력 자동화·엔진 렌더 근거 확인·PC 영상/시각 판정 대기
- **V-11 / 인계 메모 추가**: T2 PhotoIntegration 6조합 EXECUTED·경고0, GUI PIE 재시작·Quinn 콘솔 선택 확인. 로스터 기본이 BeginPlay에서 캡슐을 덮으므로 ini만으로 GUI 캡슐 복구를 재현할 수 없다. D-019 결정으로 Runtime 헤드리스 복구 검사와 T2 ini 실패 로그로 대체·종결했다. 실제 키보드 지속 입력·영상·사람 눈 검수는 PC 카드로 인계하며 hitch/VRAM은 미판정.

검증 게이트(T2 최종): UE5.8.3 증분 빌드 성공5.17s. `test.ps1 -SetupDevLevel` 전체 **28 Success(21+경고7), failed0/notRun0,166.99s**; opt-in 없는 RenderEvidence NOT EXECUTED1을 제외한 실제 실행27개. 별도 D3D12 시퀀스는 위와 같이 실제 실행 성공. PhotoIntegration은 전체에서도6조합 EXECUTED·경고0. Python ruff check/format103·pytest **736 passed/68 skipped/208 warnings,51.63s**·check_repo·diff --check 통과. 로컬 `Saved/Automation/WP18T2/full-report.json`에 보고서를 보관했다. 열린 pc/v08-animation #21과 변경 파일 겹침 없음, 신규 공유 훅 없음. PR CI와 Opus 코드/Fable 시각 리뷰는 별도다.


PR #39 (A) 수정: D1 GUI 캡슐 복구를 Runtime+ini 실패 로그로 대체·종결, D5 상태·§9 표기 갱신, D3/C6 실제 명령·후처리 접두와 규칙 기록, D4/C7 연속 구간 명시, C2 Sequence 단독/nullrhi 오류 처리, Fable 요청 달리기·하강 연속 시트2장 추가. Fable은 기존18장을 🟡 근거로 채택했으며 타일당60~80px 한계로 발 접지·관절·발 미끄러짐은 사람 눈 검수 대기다. 비블로킹 C1/C3/C4/C5는 별도 후속으로 남긴다.

수정 후 게이트: UE build 성공7.02s, Sequence 단독+nullrhi 및 두 플래그+nullrhi는 각각 failed1로 명시적 오류 확인. 전체28 Success(21+경고7), failed0/notRun0, 167.06s; RenderEvidence NOT EXECUTED1 제외실제27, Runtime 복구 검사 통과. pytest736 passed/68 skipped(45.03s), ruff check/format103·check_repo·diff check 통과. 추가 JPG2장195866/201429bytes, post-processed 접두9개 확인.

## 병합 기록 — T2 PR #39 (2026-09-28, 오케스트레이터 세션)

대상: [PR #39](https://github.com/wooklym/golmok/pull/39) `astra/wp-18-v11-gui` 4b34ca1(리뷰) → f9819c7(수정; 병합 세션이 diff로 (A) 6건 반영 확인). 절차: DEVELOPMENT-PLAN §7.6 — Opus 5.5 ultracode 코드/증거 리뷰 + 문서/기록 리뷰(major 지적 회의론자 검증) + Fable 시각 판정 → PR 코멘트(2026-09-28 06:53Z) → Astra 수정 → D-019에 따라 소유자 승인 없이 이 커밋(`WP-18: 병합 시 반영 (Fable)`) → merge commit. 전문은 PR #39 코멘트.

- **BLOCKING 없음.** 레인 준수(Tests/GolmokCharacter*·WP-18 문서·런북·images만, 런타임/공유 문서/훅 무변경), 등록 테스트 28 = 28(RenderEvidence opt-in 분기만), nullrhi 게이팅(두 플래그 + nullrhi → 오류), InputKey 유지/해제·fixed dt 1/60 설정·복원, 0.1 s sim 요청 간격(577 프레임 줄 전부 정확), 파일명·teleport 1회·계단 좌표(런북 §8)·속도 계약(quinn 180/500, proxy135 145/380, proxy110 120/310)·포털 평면 통과·JPG 18장 1600×750 ≤ 229,038 B(LFS oid 일치)·capture.txt 9개·'엔진 입력 드라이버 렌더 근거(실제 키보드 지속 입력·영상 아님)' 표기·🟡 유지·hitch/fps 무판정을 코드와 산출물로 확인.
- **(A) 6건 → 수정 반영**: D1 초기 메시 실패→GUI 복구 원인 정정(로스터 기본 manny가 BeginPlay에서 ini 대체 캡슐을 덮어 GUI로는 재현되지 않음, `GolmokCharacterSubsystem.cpp` :286/:307/:384) + **오케스트레이터 결정(D-019): 이 GUI 항목은 헤드리스 `Golmok.Character.Runtime`(ApplyEntry 복구 검사)과 T2의 ini 실패 로그 재현으로 대체·종결, PC 카드로 넘기지 않음**(회의론자: 인과 확인, minor); D5 런북 4·7·104·174행 잔존 문구·§9 표기; D3/C6 §11 실제 명령줄(960×540·보고서 경로)·후처리 규칙·capture.txt `post-processed:` 접두; D4/C7 '연속 12프레임 = elapsed 1.1~2.2 s' 정정; C2 `-GolmokCharacterSequence` 단독 사용 시 오류 처리; Fable 판정 보강 시트 2장(달리기 3.1~4.2 s·계단 하강 연속).
- **(B) 후속 가능**: C1 300 s timeout 누적(코스별로), C3 맵 존재 사전 검사, C4 capture.txt에 포털 `bPlayerInside`·단언 결과·`Feet()`, C5 manifest에 RHI·프리셋 결과·TargetArmLength·명령줄. D2(병합 시 반영 칸별 문안)는 이 커밋에서 병합 세션이 조립.
- **Fable 시각 판정(시트)**: 걷기→달리기 전환에서 보폭·팔 스윙이 깨끗하게 바뀌고 0.1 s 연속 구간의 다리 교대가 끊김 없음; 계단 상승·랜딩·회전·하강이 단차를 따라 연속, 부유·침하 없음; 포털 진입·회전·복귀 연속. 보강 시트(quinn 달리기 3.1~4.2 s·proxy135 계단 하강 4.1~5.2 s 연속 12프레임): 달리기 주기의 공중 위상·팔 스윙과 하강의 단차 추종이 끊김 없이 이어짐. T-pose·팝 없음, 3종 동일 품질. 한계: 타일당 캐릭터 60~80 px라 발 접지·관절·미끄러짐은 판정 불가 → **사람 눈 검수는 PC 카드 유지**. 참고: L_Dev 실내 상자 과노출(눈 적응 스윙)은 WP-14 조명 look-dev 메모. **판정: 🟡 근거로 채택, WP-18/V-11 🟡 유지.**
- **(C) 옮긴 것**: STATUS 병행 트랙 WP-18·V-11 행(상태 칸·메모: T2 근거·PC 카드 인계·D1 종결)·마지막 갱신, ROADMAP 1.3, astra-tasks T2 완료·우선순위, 이 절.
- 판정: **병합**. 실제 키보드 지속 입력·영상·사람 눈 검수(보행 주기·관절·발 미끄러짐)는 다음 PC 카드(V-09c와 합침)에서.


## #39 비블로킹 후속 C1/C3/C4/C5 (2026-09-28)

main4826929 기준 별도 astra/wp-18-sequence-diagnostics. T5는 #41 맵 복제/로드 오류 검토를 기다리며, 독립 후속 큐를 진행했다. 런타임/공유 훅/테스트 등록 수 변경 없음.

- C1: 코스 생성 시각이 아닌 첫 Update에서 300초 제한 시작, timeout 오류에 경과시간 기록.
- C3: 큐 추가 전에 L_Dev/L_ZoneTest/합성 실내 패키지 존재를 모두 확인해 누락 경로 즉시 보고.
- C4: 프레임별 Feet/포털 상태와 계단·포털 단언 PASS/FAIL·값, COMPLETE 단언 집계 기록.
- C5: RHI·명령줄·프리셋 적용 결과·진단 붐 길이를 manifest에 기록, clear_noon 적용 실패는 명시적 오류.

### 병합 시 반영 — 후속

> WP-18 인계 메모 추가: #39 비블로킹 C1/C3/C4/C5 후속으로 렌더 시퀀스 코스별 타임아웃·fixture 사전 검사·환경/단언 진단을 보완했다. 기존 시각 판정 범위와 WP-18/V-11 🟡 상태는 유지한다. T5 #41 차단은 별도다.

검증(2026-09-28): UE5.8.3 빌드5.38s 성공. 자체 worktree의 생성 실내 .umap을 잠시 별도 이름으로 옮겨 missing fixture 오류를 재현(0.07s, failed1, PIE 큐 시작 전), finally에서 원래 경로로 복원했다. D3D12 정상9코스 **1 Success·경고/실패/notRun0,77.54s**, PNG577장1014×550 디코딩·0.1s 간격·프레임별 state577줄·PASS 단언12개·포털 inside1→복귀0 기록 확인. 각 manifest에 D3D12/preset applied=true/붐 길이/실제 명령줄 존재. 타임아웃300초 자체의 만료를 기다리는 실험은 하지 않았으며 첫 Update 초기화와 코스별 인스턴스로 범위를 확인했다.

Python ruff check/format103·pytest740 passed/77 skipped(33.05s)·check_repo·diff check 통과. 바로 앞 main4826929 전체 UE 기준선은28 Success(21+경고7), 실패0/notRun0,167.53s(RenderEvidence NOT EXECUTED1 제외실제27); 후속 변경 검증은 위 실제 RHI opt-in 실행이며 전체 회귀를 재실행한 것으로 중복 집계하지 않는다. 증거는 로컬 Saved/Automation/SequenceDiagnostics/index.json·SequenceMissingFixture/index.json·WP18T2Sequence의 최신9개 폴더에 보관. 기존 PR39 시트·manifest는 변경하지 않음. GUI 잠금 해제·생성 에셋 복원 완료.

## 병합 기록 — PR #42 (2026-09-28, 오케스트레이터 세션)

대상: [PR #42](https://github.com/wooklym/golmok/pull/42) `astra/wp-18-sequence-diagnostics` 459fe03 — PR #39 리뷰 (B) C1/C3/C4/C5 후속. 절차: DEVELOPMENT-PLAN §7.6 — Opus 5.5 코드 리뷰(단일 관점, 지적 6건 중 major 없음) → PR 코멘트(2026-09-28 08:52Z) → D-019에 따라 (A) 없이 이 커밋(`WP-18: 병합 시 반영 (Fable)`) → merge commit.

- **BLOCKING/major 없음.** 변경 3파일 모두 Astra 레인(Tests/GolmokCharacterRosterSequence.cpp +39/−10, WP-18-followup, 런북 wp18a), 핫스팟·공유 문서 무변경, 등록 테스트 28 = 28. include 해석(RHI는 Build.cs 기존 private 의존성, PackageName.h/CommandLine.h는 Core/CoreUObject), `GDynamicRHI` null 가드·`GetName()` const TCHAR*, `ApplyPreset` bool 반환·PIE에서 TimeOfDay는 FindOrSpawn으로 존재, `GetCameraBoom()` 존재·Phase 0에서 non-null, 멤버 초기화 순서·섀도잉 없음. C1 코스별 첫 Update 기준 300 s·경과 시간 메시지(FSequence는 코스마다 새로 생성), C3 fixture 검사가 첫 latent command보다 앞·AddError로 실패 확정(Astra 재현 failed 1·0.07 s), C4 `Check()` 실패 표시·집계·assert 줄, state 줄의 null Portal 안전(course 0/1), 단언 12개 = 3×(2+2), C5 environment 줄이 프리셋 적용 뒤·첫 캡처 전, 실패 시 applied=false manifest 저장 뒤 Fail, `Save()` 빈 Folder 가드(예전엔 CWD에 capture.txt가 생길 수 있었음). 문서와 코드 일치, 과장 없음(🟡 유지, 300 s 만료 실험 미실행 명시), 수치 일관(577 = T2 프레임 합).
- **(A) 없음.** minor S1(병합 시 반영 문안이 세 문장·T5 문장 포함·대상 칸 미지정)은 이 커밋에서 병합 세션이 한 문장 WP-18 메모로 조립.
- **(B) 후속(다음 Astra push에 실으면 됨)**: S2 런북 "매 프레임" → "캡처 프레임마다(0.1 s sim)"; S3 300 s에 PIE 기동·정착 대기가 포함됨을 반 문장; S4 fixture 루프는 첫 누락만 보고(모아서 보고하거나 문서 정정); S5 course 0은 단언 없음 → `assertions=none` 또는 개수 표기; S6 capture.txt의 command_line에 절대 경로가 들어가니 저장소에 넣을 때도 확인/마스킹 문구.
- **(C) 옮긴 것**: STATUS 마지막 갱신·WP-18 행 메모 한 문장, 이 절. ROADMAP/astra-tasks/DECISIONS 무변경(상태 변화 없음).
- 판정: **병합**. WP-18·V-11 🟡 유지, 시각 판정 범위 변경 없음.

## 병합 기록 — T7 PR #52 (2026-09-28, 오케스트레이터 세션)

**내용**: PR #41 리뷰 T4/T6/T7 반영, `Tests/GolmokCharacterRosterZoneWalk.cpp`·`RenderTest.cpp`만(등록 28 유지). (T4) 코스 0·1의 1 s 압박 측정을 "접촉면 5 cm 이내 **그리고** 수평 속도 < 1 cm/s"에서 시작(과제 문구는 OR였으나 AND가 더 안전 — 리뷰 판단), 20 s 안에 정착하지 않으면 Fail. (T6) 녹화 중 Fail은 `golmok.path stop`을 생략하고 경고만 남겨 월드 서브시스템 `Deinitialize`가 녹화를 폐기(과제의 "다른 이름 저장" 대신 폐기 — walk.txt에 위치 샘플이 남고 잘린 경로는 아무도 쓰지 않으므로 허용). (T7) `-GolmokZoneWalk`와 RenderEvidence/Sequence 플래그 동시 지정 시 AddWarning. Astra 보고: PC 빌드·헤드리스 28 Success, RHI 실행은 PC 카드 3장(V-09c→V-10→V-04b) 뒤로 보류.

**병합 전 리뷰(Opus 읽기 전용)**: BLOCKING·major 없음. 확인: 레인·hot-spot 준수, IMPLEMENT 28=28, 네임스페이스·unity·컴파일 위험 없음, T4 접촉면 수치(유리 남면 495 = 500 − BlockerThicknessCm/2, 벽 500, 캡슐 반지름 42 → FaceY 453/458)가 PR #41 실측과 일치, 교착 경로 없음, 1 s 변위 <5 cm·접촉면 ±30 cm 단언 의미 불변, T6 파일 보존 경로(StopRecording만 파일을 씀) 확인, T7 경고가 결과를 바꾸지 않음. (B) 3건은 RHI 실행 push에 반영: R52-1 경고 문구에 `walk_01` 경로 명시·주석 "EndPlay"→"Deinitialize", R52-2 유리 면을 `Zone->BlockerThicknessCm`에서 계산, R52-3 타임아웃 메시지에 y·면·속도 수치. 참고: 코스 4 성공 경로가 단언 전에 저장하는 기존 순서(R52-6), 세 수정은 아직 실행된 적 없음(R52-7 — RHI 실행에서 코스 0·1, 플래그 조합, 코스 4 강제 실패로 확인).

**병합**: 오케스트레이터 결정(D-019), 헤드리스·CI 초록 기준. WP-18·V-11 상태 변동 없음(🟡 유지).


## T7 RHI 실행·R52 보완·F4 (2026-09-30)

이슈 #30 코멘트 5903520898(C-07 해소·T7 배정), main `99142bf` 기준 `astra/wp-18-zonewalk-rhi`. 코드 변경은 `Tests/GolmokCharacterRosterZoneWalk.cpp`만이며 RenderTest의 기존 조합 경고를 실제 실행으로 확인했다. 새 등록·런타임·공유 훅·에셋 변경 없음. 현재 main의 등록 수는 **32개**(과제의 28은 이전 시점 수치)이며 이 작업은 그대로 유지한다.

- R52-1: 실패 경고에 `walk_01` 실제 경로 및 기존 파일 유무를 표시한다. 주석도 world-subsystem `Deinitialize`의 폐기로 바로잡았다. 실패 시 저장 명령을 보내지 않는다.
- R52-2: 유리 접촉면을 `Zone->BlockerThicknessCm`의 절반으로 계산한다. 코스 0·1은 접촉면 ±5 cm **그리고** 속도 <1 cm/s에서만 1초 압박을 시작한다(PR #52 T4 조건 유지).
- R52-3: 접촉 20 s 타임아웃 메시지에 y·face·수평 속도(cm/s)를 포함한다.
- F4: W를 누른 이동 구간에서 다음 틱부터 `IsInputKeyDown`을 확인하고 소실이면 `input flushed (viewport focus lost)`로 즉시 실패한다. 입력 발행 프레임은 PlayerInput 처리 전이라 제외한다. 첫 RHI 시행에서 같은 프레임 검사 오탐을 발견했고 이 수정 후 코스 0·1이 통과했다.
- 재현용 opt-in `-GolmokZoneWalkForceInputFlush`: 코스 4의 두 번째 waypoint에서 W 입력 후 0.25 s에 직접 `FlushPressedKeys()`를 호출한다. 평상시 및 다른 코스에는 영향이 없다. 실제 포커스 변경 대신 엔진 입력 flush 이후의 분기만 시험한다. 런북 §12에 백그라운드/포커스 ini 우회와 실패 판정 방법을 남겼다.

### 실제 RHI 결과

자체 worktree·UE5.8.3·D3D12 offscreen·실시간 PIE·합성 `L_ZoneTest06`, 실행 UTC 04:38~04:39. GUI 잠금이 없고 다른 UE 프로세스가 없음을 확인한 뒤 독점 생성한 잠금을 유지했고 완료 후 해제했다. 새 보안 창을 조작하지 않았다. 화면 품질/fps 판정은 하지 않았다.

| 실행 | 결과 | 근거 |
|---|---|---|
| 코스 0 + RenderEvidence 플래그 | Success, 경고 1, 테스트 14.95 s | 우선순위 경고 1회; 압박 1초 변위 0 cm, 접촉 Y=452.89884 cm |
| 코스 1 | Success, 경고 0, 테스트 16.26 s | 압박 1초 변위 0.00069 cm, 접촉 Y=457.89893 cm |
| 코스 4 + 강제 flush | 의도된 Fail 1, 경고 2, 테스트 6.78 s | step1 입력 소실 오류; walk_01 경로 경고; Deinitialize에서 35샘플 discarded |

정상 코스 PNG 3장씩 **6장**, 1014×550 디코딩 확인. 로컬 근거는 `Saved/Automation/T7RHI-course0-combo`, `T7RHI-course1`, `T7RHI-course4-flush`의 index.json 및 `Saved/Automation/WP06ZoneWalk/course0_7487648A4B9AA0B6E32BD0833735D2C8`, `course1_5C712A544E40CAA7C4EE5F976583DB0D`의 walk.txt·PNG다. 생성물은 커밋하지 않았다.

기존 `Saved/Golmok/Paths/walk_01.json`은 전후 **61069 bytes**, SHA-256 `fea743b0ef4f9398528396de78fe9fc99e43b8f410628294c95119ed85f5362c`, mtime_ns `1790587719792403000`으로 모두 동일했다. 폐기 로그와 파일 보존을 확인했으며 잘린 녹화 파일은 만들지 않았다. 파일 미존재 경고 분기·20초 접촉 타임아웃·실제 창 포커스 전환·Sequence 플래그 조합은 별도 실행하지 않았다. 기존 코스 4 정상 저장 순서(R52-6)는 이번 범위 밖이다.

검증 게이트: 최종 UE5.8.3 빌드 5.74 s 성공(엔진 Character.h의 기존 deprecated 경고). `test.ps1 -SetupDevLevel` 전체 32 Success(21 + 경고11), 실패0/notRun0, 178.34 s. 기본 RenderEvidence NOT EXECUTED 1건을 제외한 실제 실행은31개이며, opt-in RHI 근거는 위 별도 실행이다. pytest1029 passed/203 skipped/208 warnings(42.01 s), ruff check·format108·check_repo·diff check 통과. 로컬 g++ 없음. CI g++는 순수 수학 헤더만 교차검증하며 이 UE .cpp의 컴파일 근거는 로컬 UE5.8.3 빌드다. 열린 #21 pc/v08-animation과 변경 파일 겹침 없음. 소유자 결정 필요 없음; Opus ultracode 코드 리뷰 요청.

### 병합 시 반영 — T7 RHI

> STATUS Astra T7 메모: T7 RHI 완료. R52-1/2/3 경고·접촉면·타임아웃 진단 보완, F4 W 입력 소실 즉시 실패(입력 발행 다음 틱부터). D3D12 코스 0·1 성공, opt-in 조합 경고 확인, 코스 4 강제 flush 실패·35샘플 폐기·기존 walk_01 해시/mtime 보존 확인. WP-18/V-11 품질 판정 상태는 별도 PC 카드에 따른다.

> astra-tasks T7 결과: RHI 보류 해소. 위 실행 완료, Opus ultracode 리뷰 후 병합. 코스 4 강제 실패는 의도된 음성 시험이며 정상 테스트 실패로 집계하지 않는다. 실제 포커스 전환과 20 s 타임아웃의 실험은 미실행.

## 병합 기록 — T7 RHI PR [#72](https://github.com/wooklym/golmok/pull/72) (2026-09-30, 오케스트레이터 세션)

**내용**: 위 "T7 RHI 실행·R52 보완·F4" 절 그대로다. 코드는 `Tests/GolmokCharacterRosterZoneWalk.cpp`만 바뀌었고 등록 수는 32로 같다. R52-1/2/3과 F4(이동 중 W 입력 소실 → 다음 틱부터 `input flushed (viewport focus lost)`로 즉시 실패)를 반영했다. 재현용 opt-in `-GolmokZoneWalkForceInputFlush`를 추가했다. D3D12 RHI 결과: 코스 0(+RenderEvidence 조합 경고 1회)과 코스 1이 성공했고, 1 s 압박 변위는 0 / 0.00069 cm였다. 코스 4 강제 flush는 의도된 음성 시험으로 step1에서 즉시 실패했고, 녹화 35샘플은 폐기됐으며 기존 `walk_01.json`의 크기·SHA-256·mtime은 그대로였다. Astra 보고: UE 5.8.3 빌드, 전체 32 Success, pytest·ruff·check_repo 통과.

**병합 전 리뷰(Opus 5.5 읽기 전용, R72)**: (A) 0 · (B) 1 · (C) 5. 레인·핫스팟·공유 문서·등록 수·unity 빌드 위생 모두 문제없다. 입력 발행 프레임 오탐은 없다(검사는 `Now>StepAt`에서만). W를 의도적으로 떼는 경로는 모두 `Key(false)`로 `bKeyExpected`를 끈다. T6 보존 경로와 R52-2/3 수치(접촉 y 453/458 ↔ 실측 452.899/457.899)도 확인했다.
- (B) **R72-1** 런북 §12 명령 블록에 코스별 필수 플래그(코스 0 `-GolmokCharacterRenderEvidence`, 코스 4 `-GolmokZoneWalkForceInputFlush`)가 없다. 블록을 복사해 `$course = 4`만 바꾸면 정상 코스 4가 `walk_01.json`을 덮어쓴다(R52-6 순서) → **T11**.
- (C) R72-2 실패 문구가 원인을 포커스 상실로 단정한다(`W seen down since press`·경과 시간 추가 권장). R72-3 새 검사의 실행 근거는 코스 0·1과 코스 4 step1뿐이다 — **코스 2·3·5와 정상 코스 4는 새 검사로 아직 실행하지 않았다**(다음 RHI 실행에서 6코스 1회). R72-4 강제 flush 플래그를 코스 4 외 코스와 함께 주면 표시 없이 무시된다. R72-5 §12의 Astra 작업 트리 고정 경로, 유리면 식은 캡슐 중심 y, 에디터 PIE에서 ResX/ResY 미적용. R72-6 "기존 T7 조건"은 PR #52 리뷰 T4 조건이고, CI g++는 이 `.cpp`를 컴파일하지 않는다(컴파일 근거는 로컬 UE 빌드) → T11(선택).

**병합**: 오케스트레이터 결정(D-019)으로, CI 10/10 초록과 (A) 없음을 기준으로 병합했다. WP-18·V-11 상태는 바뀌지 않는다(🟡 유지; 품질 판정은 V-11 PC 카드).


## T11 R72 후속 결과 (2026-09-30)

배정: 이슈 #30 코멘트 5904874219, PR #72 R72 리뷰. main `48ba577`에서 새 `astra/wp-18-zonewalk-r72`로 시작했다. 배정 3파일만 수정, 등록32 유지. GASP 통합(WP-19)·품질 가설·런타임·공유 훅 변경 없음.

- R72-1: 런북 §12 코드 블록이 코스 0 조합 플래그와 코스 4 강제 flush를 직접 붙인다. 코스 4를 포함하면 `.pre-t7` 백업·SHA-256·mtime 기록, finally 복원·해시/mtime 확인을 수행한다. 기존 백업은 덮어쓰지 않는다. `$course=-1`은 강제 flush 없는 정상 6코스이며 이때도 기준 녹화를 복원한다.
- R72-2: 지정 입력 소실 문자열 뒤에 `W seen down since press`와 `Now-StepAt`를 붙였다. 각 press에서 이력을 초기화하고 다음 틱부터 실제 W 상태를 누적한다. 진단은 입력을 한 번이라도 인식했는지 구별하며 포커스 상실의 직접 관찰을 뜻하지 않는다.
- R72-4: 코스 4를 제외한 단일 코스에 강제 flush 플래그를 주면 무시 경고. 전체 코스 선택에는 4가 포함되므로 이 경고가 없다.
- R72-5/6: worktree 루트 상대 경로, 접촉 시 캡슐 중심 y와 유리 면 구분, PIE 해상도 실제값 안내, PR #52 T4 조건 표기 및 CI g++/로컬 UE 컴파일 범위를 정정했다.

### R72-3 실제 정상 6코스 RHI

UE5.8.3·D3D12 offscreen·실시간 PIE·`L_ZoneTest06`, UTC 06:37~06:41. 다른 UE 프로세스·GUI 잠금 없음 확인 뒤 자체 잠금을 생성·유지·해제했다. 기존 `walk_01.json`을 `.pre-t7`로 백업했고 아래 모든 실행 뒤 복원했다. 새 보안 창을 조작하지 않았다.

정상 6코스를 **한 프로세스에서 한 번** 실행: `Golmok.Character.RenderEvidence` 1 Success, 경고0/실패0, 테스트200.83 s(프로세스233.86 s). 입력 소실 오탐 없음. 6개의 COMPLETE, 단언25개 PASS, PNG37장 전부1014×550 디코딩 확인. 코스 4 정상 녹화73.05068 s, 포털 진입·복귀·언로드·녹화 종료 통과. 코스 5 실내 3면·천장·조명 overlay 단언도 통과. 이는 엔진 입력 회귀 근거이며 키보드 지속 입력·영상·최종 품질/fps 판정이 아니다.

| 코스 | PNG | PASS 단언 | 로컬 Saved/Automation/WP06ZoneWalk 하위 폴더 |
|---|---:|---:|---|
| 0 | 3 | 2 | `course0_C5536BEB463417434C0F8F9C7DAC7357` |
| 1 | 3 | 2 | `course1_588CA3514C2ECBE0E97ABCAC799E1BAB` |
| 2 | 3 | 2 | `course2_4C0FB6444EFFC89789E069A6CECD66A2` |
| 3 | 3 | 1 | `course3_EEAC39E04383A12BB281C593BAF11C68` |
| 4 | 12 | 6 | `course4_7752B8F9453055AEA3EB2E816D950202` |
| 5 | 13 | 12 | `course5_E94B0B714A2B2382D87F0AA0708B51C1` |

보고서는 `Saved/Automation/T11-normal-six/index.json`. 정상 녹화 직후 파일은60912 bytes·SHA-256 `c6befa2e6a23084d51a5480d3f25af4eb200ddb612d0ff3acc773ae62f09a972`였으며, 실행 뒤 기준 파일 **61069 bytes·SHA-256 `fea743b0ef4f9398528396de78fe9fc99e43b8f410628294c95119ed85f5362c`·mtime_ns `1790587719792403000`**으로 복원됐다. 백업은 로컬에 보존했고 생성 에셋·녹화·PNG는 커밋하지 않았다.

추가 RHI 확인:
- `T11-flush4`: 의도된 Fail1·경고2,6.90 s. `input flushed (viewport focus lost); W seen down since press=true; Now-StepAt=0.400 s`, Deinitialize 36샘플 discarded. 복원 전에도 기준 파일 해시/mtime/크기가 동일했다.
- `T11-wrong-flag0`: Success·경고1,14.98 s. `GolmokZoneWalkForceInputFlush applies only to course 4; ignored for the selected course.` 확인. 기준 파일 불변.

런북 PowerShell 블록은 Parser 검사와 임시 파일/엔진 stub로 코스0·4·-1 인자 전달, 정상 녹화 덮어쓰기 뒤 finally 복원, 기존 백업 거부(IOException)를 확인했다. 이 stub 결과를 UE 실행으로 세지 않는다. 실제 RHI는 동일 인자의 Python 실행기로 위 별도 결과를 얻었다.

미실행: W가 처음부터 등록되지 않는 경우(`seen=false`)의 주입 시험, 실제 창 포커스 전환, 접촉20초 타임아웃·파일 미존재 경고. 정상 코스4의 기존 저장 순서(R52-6)는 변경하지 않았다. 기준 녹화는 런북 백업/복원으로 보호한다.

검증 게이트: UE5.8.3 빌드7.90 s 성공, `test.ps1 -SetupDevLevel` 전체32 Success(21+경고11), failed0/notRun0, 178.39 s. 기본 RenderEvidence NOT EXECUTED1을 제외한 실제31개, RHI는 위 별도 실행이다. Python1029 passed/203 skipped/208 warnings(43.09 s), ruff check·format108·check_repo·diff check 통과. 소유자 결정 필요 없음; Opus ultracode 리뷰 요청. CI는 PR에서 확인한다.

### 병합 시 반영 — T11

> STATUS WP-18/T11 메모: R72-1 런북 코스별 플래그·walk_01 백업/복원, R72-2 입력 인식 이력, R72-4 잘못 지정한 강제 flush 경고, R72-5/6 표기 정정. 정상 D3D12 6코스1회 경고0/실패0·단언25 PASS·PNG37장, 기준 경로 복원 확인. 엔진 입력 회귀 근거이며 WP-18/V-11 품질 판정은 별도 PC 카드에 따른다.

> astra-tasks T11 결과: R72 후속 완료. 정상 코스4 포함 6코스 통과, 강제 flush 진단·잘못 지정한 플래그 경고 확인, 백업 파일 보존·원본 해시/mtime 복원. Opus ultracode 리뷰 후 병합. WP-19 3단계는 별도 배정 뒤 시작.

## 병합 기록 — T11 PR [#75](https://github.com/wooklym/golmok/pull/75) (2026-09-30, 오케스트레이터 세션)

**내용**: 위 "T11" 절과 같다. 반영한 것은 다음과 같다.
- R72-1(B): 런북 §12 블록 안에 코스별 인자(`$extra`)를 넣고, `walk_01.json`을 `.pre-t7`로 백업한 뒤 SHA-256·mtime을 기록하고 `finally`에서 복원·검증한다.
- R72-2: 실패 문구 뒤에 `W seen down since press`와 `Now-StepAt`를 붙였다.
- R72-4: 코스 4가 아닌 코스에 강제 flush 플래그를 주면 경고를 낸다.
- R72-5/6: 표기를 정정했다.

D3D12 정상 6코스를 한 프로세스에서 한 번 돌렸다(단언 25 PASS, PNG 37장, 입력 소실 오탐 없음). 강제 flush 음성 시험과 잘못 지정한 플래그 경고도 확인했고, 끝난 뒤 기준 `walk_01.json`을 복원했다. 코드는 `ZoneWalk.cpp`만 바꿨고 등록 수는 32로 같다.

**병합 전 리뷰(Opus 5.5 읽기 전용, R75)**: (A) 0 · (B) 0 · (C) 4. C++ 정상 동작은 그대로다(조건은 같고 메시지만 늘었다). seen 플래그 수명, Enqueue 경고, PowerShell 스플래팅·`finally` 복원 경로, 증거 수치(단언 25 = 2+2+2+1+6+12, PNG 37)를 확인했다.

(C)는 다음과 같다. 다음 Astra push에서 선택적으로 반영한다.
- R75-1: 복원 뒤에도 `.pre-t7`이 남아, 다음 보호 실행이 IOException으로 시작 전에 멈춘다(해시가 같으면 재사용하도록 제안).
- R75-2: `walk_01.json`·`$project`가 없는 worktree에서 바로 중단된다(`Test-Path`로 분기하도록 제안).
- R75-3: 정상 코스 4가 새 녹화를 실제로 썼는지 블록이 확인하지 않는다.
- R75-4: 세 실행의 순서·시각 기록이 없고, "0.25 s 이후 첫 틱" 표현을 고쳐야 한다.

**병합**: 오케스트레이터 결정(D-019). CI 10/10 초록이고 (A)가 없어 병합했다. WP-18·V-11 상태는 바뀌지 않는다(🟡 유지).


## T12 — WP-19c GASP 로스터 결과 (2026-09-30)

배정: 이슈 #30의 5907278376, main `4acf20d`의 19a 계약. `astra/wp-19c-roster-gasp`에서 캐릭터 레인·스키마·설정·기존 자동화만 변경했다. 오디오에는 신규 두 id의 보폭 67/146 cm만 함께 추가해 R63-3 계약을 맞췄다. 19a 공개 API 세 이름은 그대로다. 핫스팟·공유 문서·GASP 원본/ini/바이너리는 수정하지 않았다.

- optional visual과 모드별 기본값을 C++/JSON Schema에 추가. 필드 생략은 이전 동작, 잘못된 키·타입·scale·기본 id 참조는 전체 로스터 교체 전에 거절한다.
- GASP 필요 애니는 `RequiresGaspPawn`/`PawnSupportsGasp` 계약을 검사한다. source/visual 에셋·스켈레톤·캡슐 확장 검사를 모두 마친 뒤 적용하며 실패하면 기존 항목을 유지한다. ABP 또는 direct source 선택은 `ClearVisualOverride`, retarget 선택은 `SetVisualOverride` + visual scale이다.
- 두 GASP 준비 항목·gasp 기본값을 추가했다. 마지막 성공 선택 우선, 실제 GASP 폰이 아닌 폴백에서는 abp 기본값을 쓴다. 상세 조건·실검증 인계는 런북 §13.
- 등록은 기존 36개 유지. GASP 원본 없는 Runtime에서 메모리 계약 대역으로 source/visual 적용·거절·복귀를 검사했다. 실제 GASP 시각 통합은 Info skip이며 19b/V-15 대기다. R75-1~4 선택 문서 개선은 이번 필수 계약 변경과 별도로 남긴다.

최종 게이트: UE 5.8.3 빌드 성공, 전체 자동화 36 state=Success(`succeeded=24`, `succeededWithWarnings=12`, failed/notRun=0), Config/Runtime·PhotoIntegration 6조합 실행. RenderEvidence는 기존 NOT EXECUTED, GaspSmoke·GASP 실제 로스터 시각 통합은 Info skip. Python ruff check/format 113, pytest 1093 passed / 215 skipped / 208 warnings, check_repo·diff --check 통과. Windows에서 건너뛴 g++ 교차검증은 CI에 맡긴다.

재현성 주의: 최초 전체 `-SetupDevLevel` 실행에서 기존 Locomotion의 Quinn 40cm 장애물 두 단언이 실패했다(새 Config/Runtime 성공). 직전 캐릭터 단독 실행과 코드 변경 없는 전체 재실행에서는 통과했다. 최초 실패 보고서를 보존했으며 원인을 확정하거나 해결했다고 주장하지 않는다. 품질/물리 비결정성 후속 검토 대상으로 리뷰에 알린다.

### 병합 시 반영 — T12

STATUS 병행 트랙 문안: `T12(WP-19c 캐릭터) 코드·헤드리스 계약 검증 완료: optional visual/모드별 기본값, manny_gasp·uefn_gasp 준비 항목, GASP 폰 호환성 거절·ABP visual 해제. 실제 GASP 경로·GenericRetarget·품질은 19b/V-15 대기. 등록 36 유지. T13 노티파이 발소리는 별도 PR.`

WP-19 결과 절 22번 갱신 문안(Claude 소유 문서): `19c T12에서 로스터 적용이 visual override를 제거/교체하도록 연결했다. golmok.anim preview off도 기존 SelectCharacter API를 통해 복원한다. GASP 실제 리타깃 경로·Attached Parent는 19b 검증 대기.`
