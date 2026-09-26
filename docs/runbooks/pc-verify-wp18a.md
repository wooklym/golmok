# V-11 — WP-18a 캐릭터 로스터 PC 검증

2026-09-27 갱신 · 작성/헤드리스 실행 ChatGPT Astra · GUI 후속 Fable PC. 이번 #22/#23은 사용자 지시로 Astra 자체 리뷰·병합.
**코드·UE 헤드리스 통과, GUI·WP-12 통합/룩 검증 대기.** D-018 ①은 승인됐으며 설계 PR → 구현 PR 병합 뒤 아래 남은 항목을 진행한다. V-12 채점과 대조군/야간 실패의 판정은 [WP-18](../plan/WP-18-characters.md)의 최신 절차를 따른다.
계약과 D-018은 [WP-18](../plan/WP-18-characters.md), 아트 판단은 [컨셉](../design/character-concept.md), 예산은 [제작 사양](../research/11-character-pipeline.md).

병합 후 최신 진행: [WP-18 후속 기록](../plan/WP-18-followup.md). 실제 경로 재생/복귀 자동화는 실행 통과했고, WP-12 실통합은 상대 코드의 UE5.8 컴파일 오류를 재현했다. 아래 초기 결과표보다 후속 기록을 우선한다.

## 1. 안전한 별도 PC 작업 폴더

- 실행 기록 폴더: `C:\Users\user\golmok-astra\wp-18a-roster`. Claude의 `C:\Users\user\golmok`/`.claude\worktrees`는 수정하지 않는다.
- UE: `C:\Program Files\Epic Games\UE_5.8`, 실제 버전5.8.3. PC의 VS2026/MSVC14.51 toolchain 사용.
- GUI/PIE 전 `C:\Users\user\AppData\Local\Temp\claude\gui-foreground.lock`을 읽는다. 20분 이내 다른 세션 기록이면 기다린다. 쓰는 동안 `<세션> <목적> <ISO 시각>`으로 갱신하고 종료 때 자기 잠금만 지운다. 헤드리스는 잠금 불필요.
- fps/VRAM 비교는 다른 UnrealEditor 또는 `-game` 프로세스가 없는 때만 한다. 아래 nullrhi 수치를 GPU 성능 측정으로 쓰지 않는다.
- 생성된 L_Dev/L_ZoneTest·마네킹·합성 Zone은 git에서 제외한다. 테스트 스크립트는 해당 worktree의 `Saved/Automation/Report`를 지우므로 이전 결과가 필요하면 먼저 보관한다.

## 2. 빌드·자동화 명령

PowerShell5.1에서는 각 명령 종료 코드를 확인한 뒤 다음 명령을 실행한다. 다른 작업 폴더로 옮겨 실행하면 경로도 바꾼다.

```powershell
Set-Location C:\Users\user\golmok-astra\wp-18a-roster
$env:PYTHONUTF8 = '1'
.\tools\ue\add-mannequin.ps1
.\tools\ue\build.ps1
$wp18Root = (Get-Location).Path
$wp18Report = [IO.Path]::GetFullPath((Join-Path $wp18Root 'unreal/Golmok/Saved/Automation/Report'))
if (-not $wp18Report.StartsWith($wp18Root + [IO.Path]::DirectorySeparatorChar)) { throw 'Report path outside worktree' }
.\tools\ue\test.ps1 -SetupDevLevel -Filter Golmok.Character
.\tools\ue\test.ps1 -SetupDevLevel
$wp18Result = Get-Content unreal/Golmok/Saved/Automation/Report/index.json -Raw | ConvertFrom-Json
$wp18Result | Select-Object succeeded,succeededWithWarnings,failed,notRun,totalDuration
$wp18Result.tests | Select-Object fullTestPath,state
```

필터 테스트에도 `-SetupDevLevel`이 필요하다. 새 worktree의 전체 포털/Zone 검사를 위해 기존 `Content/Python/golmok/synthetic_zone.py`의 `run(interior=True)`로 합성 실외/실내를 먼저 준비한다. 이는 기존 생성기이며 변경하지 않는다. 생성 완료 뒤 에디터를 닫는다. dirty package 때문에 `QUIT_EDITOR`가 종료를 기다리면 완료 로그/프로세스 CommandLine을 확인하고 **자기 worktree의 생성 프로세스만** 종료한다. 자산이 없으면 일부 기존 테스트가 skip/warning으로 끝나므로 성공 수만 읽어 통합 통과로 판단하지 않는다.

Python 게이트(이 worktree의 새 venv):

```powershell
Set-Location tools
.venv\Scripts\ruff check .
.venv\Scripts\ruff format --check .
.venv\Scripts\pytest -q
.venv\Scripts\python scripts\check_repo.py
```

`Golmok.Character.Config`는 실제 JSON과 오류 원자성을, `.Runtime`은 자동 default·Quinn·프록시·기본 복귀·실패 시 보존을 검사한다. Runtime의 Manny 검증은 현재 값을 서로 비교하는 방식 대신 경로와 수치를 리터럴로 단언한다. 캡슐42/92, 메시Z−92/Yaw−90/scale1, 붐320/소켓(0,45,55)/FOV80, 속도180/500을 검사한다.

`.PortalRoundTrip`은 `L_ZoneTest`와 합성 실내 서브레벨을 사용한다. 누락된 환경에서는 `NOT EXECUTED` 경고를 내므로 완료 수만 보고 통합 통과로 기록하지 않는다. 새 C++ 파일을 추가했는데 빌드가 `Target is up to date`로 끝나면 UBT 소스 목록 캐시가 이전 상태일 수 있다. 프로젝트 파일을 다시 생성하거나 `Build.bat GolmokEditor Win64 Development -Project=<이 worktree의 Golmok.uproject> -WaitMutex -NoHotReloadFromIDE -gather`로 재수집하고 새 파일의 컴파일 로그를 확인한다. 이 실행에서는 실제 `GolmokCharacterRosterPortalTest.cpp` 컴파일을 확인했다.

## 3. GUI PIE 교체

L_Dev를 열고 PIE 시작 후 콘솔에서 다음을 차례로 실행한다. `list`는 Output Log에서 확인한다.

```text
golmok.character list
golmok.character quinn
golmok.character proxy135
golmok.character proxy110
golmok.character manny
golmok.character missing_id
```

1. 목록4종과 한/영 이름, default/current를 확인한다. Quinn의 ABP_Unarmed가 실제 재생되고 T-pose·팔/발 뒤틀림이 없어야 한다.
2. 평지에서 캐릭터 교체 시 발바닥 높이·XY·회전 유지, 카메라/높이 변경, 걷기/달리기 전환을 확인한다. 첫 동기 로드 소요 ms와 반복 교체 ms를 구분한다.
3. proxy135로 낮은 천장 아래 들어간 뒤 Manny로 바꾼다. 큰 캡슐이 겹치면 거절하고 기존 메시/캡슐/속도/카메라/id가 전부 유지되어야 한다. 여유가 있는 곳에서는 성공해야 한다.
4. 달리는 중 proxy110 선택 후 달리기310, Shift 해제 후 걷기120이 되어야 한다. Manny 복귀 뒤180/500 확인. 미지 id/추가 인자는 상태 변화 없이 거절한다.
5. 25cm 턱·80cm 통로·붐 충돌·좁은 계단을 영상으로 기록한다. 프록시는 전체 스케일이므로 4.5등신 팔다리/머리 리타깃 합격으로 보지 않는다.
6. PIE 종료/재시작 시 default Manny로 시작한다. 세이브·UI·키 바인딩 추가가 없음을 확인한다.

## 4. 포털·실내·경로

합성 실외/실내가 있는 L_ZoneTest에서 진행한다. Output Log의 portal active/inside와 Zone pin/unload 기록을 영상과 함께 남긴다.

| 상황 | 동작 | 통과 조건 |
|---|---|---|
| 진입 전 | 문 앞 proxy135 → 실내 진입 → Quinn | 폰/Controller 유지, 문 평면 이동 없는데 잘못 출입 판정하지 않음 |
| 왕복 중 | 문 양쪽에서 프록시/Manny 교대로3회 왕복 | 실내 pin 유지/3초 해제 정상, 비어 있는 실내·추락 없음 |
| 실내 | proxy110으로 낮은 곳에서 Manny 요청 | 겹침이면 원자적으로 거절. 여유 있는 바닥은 발 위치 유지하고 성공 |
| 경로 재생 | 기존 경로 기록/재생 시작 → 로스터 명령 → 재생 종료 | 경로 폰에는 적용하지 않음. 원래 캐릭터 복귀 시 이전 선택이 재적용됨 |

2026-09-27 `Golmok.Character.PortalRoundTrip`에서 실제 플레이어 캡슐을 문 앞/뒤로 옮겨 overlap·문 평면 검사·비동기 실내 로드/해제를 **3회 왕복**했다. 문 앞 proxy135→Manny, 진입 뒤 proxy110, 실내 Quinn 교체에서 폰/Controller·XY/발 위치·출입 상태를 검사했다. 합성 실내의 공중 표식 아래에서는 확대를 거절하고 옆에서는 성공해야 한다. 실내에서 unload delay(3초)보다 오래 기다려도 실내가 유지되고, 실외로 나가면 지연 후 서브레벨/Zone이 해제됨을 확인했다. `EnterInterior/LeaveInterior` 강제 호출 없이 실제 overlap/틱으로 출입했다.

이 검사는 이동 컴포넌트를 멈추고 위치를 지정하므로 걷기·계단·시각 애니메이션 판정을 대신하지 않는다. **위 GUI 조합/영상과 실제 경로 재생은 여전히 미실행**이다. 비캐릭터 임시 Pawn 복귀와 기존 `Golmok.Portal.PawnSwap`/`RoundTrip`은 별도 자동화에서도 통과했다.

## 5. WP-12 병합 뒤 사진·V-12

WP-12는 ViewTarget 전환·캐릭터 중심3m 앵커·진입 FOV 상속 방식이다. `golmok.character proxy135` → 포토 진입 → FOV75 출발/앵커·숨김·종료 복원 확인. 포토 중 `golmok.character manny`는 거절하며 사진 카메라/캐릭터 hidden/포즈·시간 배율은 변하지 않아야 한다. 일시정지 설정과 TimeDilation 설정 둘 다 시험한다. 종료 후 교체 성공 확인.

V-12는 실제 Zone, 없으면 L_Basemap_Yeonnam에서 **프록시2종 × PBR/5.8 Toon BSDF/장난감 재질 × 조명4프리셋**을 비교한다. Toon 실험은 별도 로컬 프로젝트에서 하고 공유 렌더 설정은 바꾸지 않는다. 기본 거리와 얼굴0.5m, f/2.8·f/8, Manual 노출값/Physical Camera Exposure 여부를 기록한다. 조명은 `Config/Golmok/lighting_presets.json`의 `overcast_morning`, `clear_noon`, `golden_evening`, `night`를 사용한다.

사진 파일명은 `v12_<proxy>_<material>_<light>_<view>.jpg`를 제안한다. 실제 간판/사람 없는 구도를 고르고 공개본은 긴 변1600px/LFS. PC 원본 고해상도 사진은 로컬에 보관한다. splat 수신체·발 그림자·벽 그림자·헤어 DOF 경계를 확인하고 소유자가 WP-18 채점표를 작성한다. fps 측정은 UE 단독 실행에서, 동기 로드 hitch·GPU ms·VRAM peak를 별도로 남긴다.

## 6. 엔진 API·미확인 조합

| 항목 | 2026-09-26 상태 | 근거/후속 |
|---|---|---|
| `OnPossessedPawnChanged.AddDynamic/RemoveDynamic`, UFUNCTION | 확인 | 5.8.3 빌드·Runtime 자동 기본/임시 Pawn 복귀 성공 |
| `FJsonObject::Values`/`TryGetField(FString)` | 확인 | Values는 개수만 읽고 TryGetField로 필수 키를 확인해 FSharedString 변환을 피함. 실제 JSON/잘못된 키 Config 테스트 성공 |
| `UAnimBlueprintGeneratedClass::TargetSkeleton` 및 Quinn 같은 ABP | 확인(로드·설정) | Runtime 실제 Quinn mesh/ABP 경로 성공. 시각 애니메이션 품질은 GUI 대기 |
| `FScopedMovementUpdate`, `CacheInitialMeshOffset` | 확인 | include는 `Engine/ScopedMovementUpdate.h`. 메시를 부모 캡슐 이동 전에 갱신한 뒤 proxy offsetZ−69와 고정 발밑 단언 성공 |
| `OverlapBlockingTestByChannel`+capsule response | 확인(자동화) | 인공 천장과 합성 실내 표식 아래 확대 거절, 여유 지점 성공. 실제 포털과 교체3회 왕복 통과. GUI는 §4 대기 |
| WP-12 실제 포토 actor/time dilation·앵커 | 미확인 통합 | Runtime의 별도 ViewTarget/paused 거절은 성공. WP-12 병합 뒤 §5 |
| 첫 soft load hitch·교체 peak VRAM·패키지 cook | 미확인 | nullrhi는 GPU 성능 근거 아님. JSON soft path만으로 cook 보장 안 됨. 18b 패키징 검증 별도 |
| 4.5등신 GASP, Toon/Mutable, Nanite+모프/cloth, groom | 미확인 실작품 조합 | 문서 기능 존재와 별개. V-08/V-12/18b에서 실제 에셋으로 측정 |

## 7. 실행 결과

| 검사 | 실행 결과 |
|---|---|
| Python3.12.10 / ruff check·format / check_repo | 통과, format95개 파일 |
| pytest 전체 | 608 passed, 42 skipped, 208 warnings (수정 뒤 재실행34.50s). 로컬 g++ 없음으로 교차검증 skip 포함. 기존 의존성 deprecation 경고 |
| g++ 교차검증 CI | 코드 수정 커밋 b8105f2의 [Actions](https://github.com/wooklym/golmok/actions/runs/36248981836): Linux3.11/3.12 및 Windows3.12+MinGW 각각 **647 passed, 3 skipped**, 전체5 jobs success. 최신 문서/병합 커밋 결과는 구현 PR checks 참조. 로컬 skip을 통과로 바꾸지 않음 |
| add-mannequin / UE5.8.3 빌드 | 실행·성공. 새 MSVC 버전 안내/C4996 기존 경고 있음. 초기 include 오류 수정 후 성공 |
| Character 필터 | Config/Runtime 2 Success, 실패0. 초기 proxy offset−92 회귀를 수정한 뒤−69 단언 통과 |
| 전체 UE (합성 실내 fixture 준비 후) | **18 Success = succeeded13 + succeededWithWarnings5, failed0, notRun0**, 39.11s. Character2·기존Movement·Portal4·Zone5 등 전부 실행 |
| 전체 UE 경고 | L_Dev GeoOrigin 부재 안내, 의도된 누락 Zone chunk/collision과 version mismatch fixture 경고. 개별 state는 전부 Success. missing asset 경고를 실자산 품질 합격으로 읽지 않음 |
| 기본 이동 실측 | 걷기/좌우/후진180cm/s, 달리기500cm/s, 점프 정점90cm. 기존 테스트 수정 없음 |
| GUI/실제 포털과 교체/포토 통합/성능/V-12 | **미실행**, Fable PC 후속. 최종 4.5등신 캐릭터 제작/리타깃은18b |

2026-09-27 포털 통합 자동화 추가 후 최신 결과: **UE 전체19 Success(14+경고5), failed0/notRun0, 63.79s**. Character 필터는3 Success이며, 새 `PortalRoundTrip`24.08s에서3회 왕복 완료 로그를 확인했다. Python/ruff/check_repo 성공(608 passed/42 skipped/208 warnings, 32.85s). 위 초기 표의 포털+교체 미실행은 이제 **GUI 조합만** 해당한다. 화면/실제 보행·실제 경로 재생·포토·성능/V-12는 계속 대기다.

2026-09-27 [Claude 리뷰 지적](https://github.com/wooklym/golmok/pull/23#discussion_r4111832801) 수정 후 재실행: UE 빌드 성공, Character2 Success, 전체18 Success(13+경고5)/실패0/미실행0, 39.87s. Python 게이트도 통과(608 passed/42 skipped/208 warnings, 40.12s). Runtime은 ini 메시 실패와 같은 `mesh=null`/대체 캡슐 표시 상태에서 잘못된 선택은 표시를 유지하고, 정상 로스터 메시 적용은 캡슐만 숨기며 메시와 Actor는 표시하는 회귀를 추가했다. GUI 검증에는 이 초기 실패 → 정상 선택 복구도 포함한다. 향후 crouch 지원 시 uncrouch의 CDO 크기/offset 복원은 별도 검증한다.

헤드리스 보고서: `unreal/Golmok/Saved/Automation/Report/index.json`, 로그는 같은 worktree의 `Saved/Logs`에 있다(ignored). 재실행하면 보고서가 대체된다. V-11 전체 완료는 위 GUI 미검증 항목까지 채운 뒤 기록한다.

2026-09-27 자체 리뷰/설계 동기화 뒤 병합 전 재검증: UE 빌드 성공, 전체 **19 Success(14+경고5)/실패0/미실행0, 63.89s**, 실제 포털3회 왕복 완료. Python608 passed/42 skipped/208 warnings(33.27s), ruff/format95개/check_repo 성공. 이후 main497566f 동기화는 이미 받은 설계와 동일해 구현 코드 변화가 없었다.

## 8. 후속 자동화와 화면 없는 렌더 증거

- `Golmok.Character.PathRoundTrip`: 실제 Debug 경로를 2초 재생하고 자연 종료를 기다린다. 수동 Pawn 교체 모사와 달리 `StartPlayback`·`StopPlayback` 수명을 통과한다.
- `Golmok.Character.PhotoIntegration`: WP-12가 함께 빌드될 때만 실제 Photo 서브시스템을 검사한다. main만 빌드하면 `NOT EXECUTED` 경고다. 이 상태를 사진 모드 통과로 보고하지 않는다. WP-12 `0806da8`의 컴파일 실패 위치는 [후속 기록](../plan/WP-18-followup.md)에 있다.
- `Golmok.Character.RenderEvidence`: 아래 명시적 옵션과 GPU RHI가 필요하다. 일반 헤드리스 실행의 `NOT EXECUTED`는 정상이며 렌더 성공이 아니다. 옵션을 주고 `-nullrhi`를 같이 주면 명확한 오류로 실패한다.

```powershell
# 기존 빌드/L_Dev/마네킹 준비 뒤, 다른 검사와 같은 프로젝트를 동시에 실행하지 않는다.
& 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' `
  'C:\Users\user\golmok-astra\wp-18a-roster\unreal\Golmok\Golmok.uproject' `
  '-ExecCmds=Automation RunTests Golmok.Character.RenderEvidence;Quit' `
  '-ReportExportPath=C:\Users\user\golmok-astra\wp-18a-roster\unreal\Golmok\Saved\Automation\WP18Followup\render-report' `
  -GolmokCharacterRenderEvidence -RenderOffscreen -unattended -nosplash -nopause -nosound -ResX=1280 -ResY=720
```

결과는 `Saved/Automation/WP18Render/<UTC시각-GUID>/`의 PNG와 `capture.txt`다. 게임 뷰포트만 요청하며 데스크톱·다른 앱을 촬영하지 않는다. **실제 PNG 크기를 확인**한다. PIE 뷰포트 크기는 `ResX/ResY`와 다를 수 있다. 프록시2×조명4 + Quinn/Manny 정오 대조 + 발 전체를 보는 프록시2개의 붐1.5배 진단 구도, 총12장이다. 진단 구도는 기본 카메라 설정 변경이 아니다.

`selection_cpu_ms`는 해당 세션에서 `SelectCharacter` API가 동기로 걸린 시간이다. 처음 요청된 메시/재사용 메시 여부와 OS/DDC 캐시 상태가 다르므로 cold-load hitch·GPU ms·프레임 끊김·VRAM 수치로 바꾸어 보고하지 않는다. 렌더 이미지는 템플릿 PBR·L_Dev에서 관찰한 증거이며 V-12의 실 배경·Toon·장난감·얼굴/DOF·최종4.5등신·소유자 채점은 계속 별도다.
