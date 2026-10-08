# V-17 — 2026-10-04 후속 묶음 PC 카드 (P14-2 · T23 · Full Precision UV · Yeonnam 성능 · 패키지 재실행 · TraceLog)

상태: ⚪ **카드 발행(2026-10-04, 오케스트레이터 Opus) — PC 대기.** 2026-10-04 클라우드 병합분(#106·#107·#108)과 V-11·V-13 리뷰 후속을 PC에서 한 번에 확인한다. 항목마다 기존 런북 절을 가리키며, 이 카드는 순서·조건·기록 위치만 정한다.

- **브랜치** `pc/v17-followup-bundle`(origin/main에서, 기준 SHA를 §7에 적는다). PR → main. 오케스트레이터가 `claude/v17-merge`로 반입한다.
- **작업 폴더**(AGENTS.md §5): 이 세션의 Claude Desktop 워크트리에서만 일한다. 다른 워크트리·`C:\Users\user\golmok`은 읽기·복사만 한다.
- **GUI 잠금**: GUI 에디터·PIE·녹화·패키지 실행 전에 `C:\Users\user\AppData\Local\Temp\claude\gui-foreground.lock`을 확인한다(V-08b 카드와 같은 규칙: 20분 안 기록이 있으면 기다리고, 쓰는 동안 20분마다 갱신, 끝나면 삭제). V-08b·V-16 카드와 GUI 시간을 나눠 쓴다.
- **소요**: 약 3~4 h(§5 패키지는 소유자 조치 뒤). 순서: §0 → §3(헤드리스 먼저) → §1·§2(L_ZoneTest·L_Dev GUI 묶음) → §4(Yeonnam) → §6(소스 조사, 언제든) → §5(패키지, 마지막).
- **저장소에 넣는 것**: 이 문서 결과 칸, 각 런북 결과 칸, STATUS 자기 행·세션 로그, jpg(긴 변 ≤ 1600 px, 각 ≤ 300 KB, LFS). 녹화 원본·CSV 원자료는 PC 로컬에 둔다.
- **PC fix**: 결함이 나오면 해당 WP 접두어로 `WP-NN: PC fix …` 커밋(제품 코드 최소 수정, Astra 레인 파일은 고치지 않고 PR에 적는다).
- 돈이 드는 일, 라이선스 동의, 외부 발송은 하지 않는다.

## 소유자 사전 조치 (§5 전에 필요)
- [ ] PC 화면의 "Windows 보안" 창(앱 Golmok, 게시자 Epic Games)에서 **취소**. 다시 뜨면 세션은 누르지 않고 소유자에게 넘긴다([pc-setup.md §2a](pc-setup.md)).
- [ ] 한 번만: `setx GOLMOK_PKG_DIR C:\Users\user\golmok-pkg\Windows` 뒤 새 셸([pc-setup.md §2a](pc-setup.md), #106). 이후 모든 워크트리가 같은 exe 경로를 써서 방화벽 창이 경로당 한 번만 뜬다.

## 0. 준비
- [ ] STATUS V-17 행을 🔵로 바꾸고 세션 로그 줄을 단다.
- [ ] `git fetch origin` 뒤 열린 `pc/*`·`astra/*`·`claude/*`(특히 `claude/wp16a-weather`)와 겹침 확인: `git diff --stat origin/main...origin/<브랜치>`.
- [ ] `git switch -c pc/v17-followup-bundle origin/main` → SHA 기록 → `git lfs pull`. tools venv 기준선 `pytest -q`.
- [ ] `.\tools\ue\add-mannequin.ps1`, `L_ZoneTest`·합성 Zone(`z_synthetic_001/002`)·`L_Basemap_Yeonnam`은 이전 카드 워크트리(V-14 `goofy-maxwell-3aee56`, V-13 `sharp-leakey-9296c7` 등)에서 복사한다.
- [ ] `.\tools\ue\build.ps1` → `.\tools\ue\test.ps1 -SetupDevLevel -Filter Golmok.` → **36 Success**(`Golmok.Travel.Teleport`의 새 단언 `camera snapped at arrival: …` 포함).

## 1. P14-2 도착 카메라 스냅 (#107) — [`pc-verify-wp15a.md` §11](pc-verify-wp15a.md)
- [ ] §11 체크리스트 전부(60 fps 녹화 `golmok.travel z_synthetic_002` ↔ `001`, 도착 뒤 걷기 랙, zone 없는 `golmok.save`/`golmok.load` 페이드 인과 스냅). §11 표를 채운다.
- 실패(스윕 남음·크래시·`check`)면 §9 #15 대안 → `WP-15a: PC fix …`.

## 2. T23 카메라 구도 실제 키 입력 재검수 (#108, R108-4) — [`pc-verify-wp18a.md` §14·§15](pc-verify-wp18a.md)
V-11 §14와 같은 방법(SendInput 지속 입력 + ffmpeg 1920×1080 60 fps)으로 4종(manny·quinn·proxy135·proxy110)을 녹화한다. 기본 피치(−15°, 마우스 무입력)와 아래 상황을 포함한다.
- [ ] (a) **카메라 쪽 계단 하강 전체 클립**(L_Dev 17 cm×10, 위에서 카메라 쪽으로 걸어 내려오기): 프레임별 최저 발 위치(화면 아래에서 %)를 잰다. 식으로는 proxy 1.9~2.0 %·성인 5.1 %다.
- [ ] (b) **착지**: 점프 2회, 피치 −15°와 0°(마우스로 수평)에서 각각.
- [ ] (c) **올려다보기**: 마우스로 피치를 +10°·+20°까지 올려 붐이 바닥에 닿아 줄어드는 모습(식: +14.5/+12.7/+10.8°부터)과 어색함 여부.
- [ ] (d) **도착 첫 화면**: `golmok.travel z_synthetic_002` 도착 직후 피치 0°(카메라 94/71/56 cm, 허리 높이) 첫 화면을 캡처한다.
- [ ] 통과 기준(D-018 진행 기록 2026-10-04): **걷기 중 발이 화면 밖으로 나가는 프레임 0, 머리 잘림 0.** (a)에서 발이 나가면 횟수·캐릭터·프레임을 적는다(다음 수단은 R108-10: 프록시 붐/FOV 또는 피치별 소켓 곡선 — 클라우드가 결정).
- [ ] 4×3 대표 프레임 시트(캐릭터당 1장, ≤ 300 KB)와 측정 표를 `pc-verify-wp18a.md` §15 끝 "V-17 결과"에 적는다(PC 결과 절, §7.6 예외).

## 3. Full Precision UV API 확인 (#107, P04c-2) — [`pc-verify-wp06.md` §2·§4·§12 #41](pc-verify-wp06.md)
- [ ] 합성 zone 임포트(§2, 헤드리스 `-nullrhi` 1회 + GUI 1회): 로그에 `zone_import: full precision UVs (LOD0) on 2/2 chunks (2 set, 0 already on)`가 나오고 `done … 8 assets`의 warnings 수가 늘지 않는다. 재실행 시 `(0 set, 2 already on)`이 아니라 새 메시라 다시 `2 set`이어도 정상(§12 #41).
- [ ] GUI에서 `SM_c_e000_n000` → LOD0 Build Settings › **Use Full Precision UVs ✔**.
- [ ] API가 없으면 WARNING 1줄(`StaticMeshEditorSubsystem.get_lod_build_settings/set_lod_build_settings unavailable…`)이 나오고 임포트는 끝난다 — 그 경우 §12 #41 대안(에디터 수동 체크)을 적고 `pc-spike.md` S7에 남긴다.
- [ ] 청크당 임포트 시간(이전 V-04c 로그 대비)을 적는다(R107-5: 빌드 3회 비용 판단 자료).

## 4. `L_Basemap_Yeonnam` 성능 재측정 (V-13 판단 #19 트리거) — [`pc-verify-wp14a.md` §3](pc-verify-wp14a.md)
- [ ] `L_Basemap_Yeonnam`(Nanite 건물)을 PIE(새 창, 1920×1080)로 열고 **골목 높이**와 **높은 시점** 2곳에서 각각: `golmok.tod mode fixed` → `golmok.tod time 15:00` → 5 s 뒤 `stat unit`·`stat gpu`(Frame·Game·Draw·GPU·Shadow Depths·Lumen)와 `r.Shadow.Virtual.Stats 1` 값을 적는다. 이어서 `golmok.tod mode clock`·`rate 0.5`로 같은 값을 적는다.
- [ ] 판정(WP-14 판단 #19 V-13 결정): clock x0.5 − fixed의 GPU 또는 ShadowDepths가 **≥ 1.0 ms**이거나 clock 모드에서 품질 목표 fps를 깨면 "재검토 필요"로 적는다(재검토 순서는 WP-14 문서 #19: ① `r.Shadow.Virtual.ResolutionLodBiasDirectionalMoving` → ② `ForceInvalidateDirectional` → ③ 캐스터 정리 → ④ 고도 연동 양자화 — 클라우드가 결정). 그 미만이면 "매 틱 갱신 유지 확인".
- [ ] 결과를 `pc-verify-wp14a.md` §11 표에 "V-17 Yeonnam" 행으로 추가한다.

## 5. 패키지 재실행 묶음 (V-10b·V-11 잔여, P11-2) — [`pc-verify-wp18a.md` §14-6](pc-verify-wp18a.md)·[`pc-verify-wp13.md` §8-1](pc-verify-wp13.md)
소유자 사전 조치 뒤에만 한다. `.\tools\ue\package.ps1`(출력 `Package output: C:\Users\user\golmok-pkg\Windows` 확인).
- [ ] ① 패키지에서 W 걷기 발소리 1회(소리·로그).
- [ ] ② 첫 화면이 대체 캡슐이 아니라 Manny, 로그에 `Character mesh '…' not found` 없음.
- [ ] ③ 콘솔 `golmok.character list|proxy135|quinn|manny` 전환.
- ②·③이 실패하면(P11-2 쿡 누락 [추정]) 코드를 고치지 말고 로그를 적는다. 클라우드가 `DefaultGame.ini` `[WP-18 hook]` `+DirectoriesToAlwaysCook=(Path="/Game/Characters/Mannequins")`를 넣는다.
- [ ] 방화벽 창이 다시 뜨면(같은 경로인데도) 세션은 누르지 않고 소유자에게 넘기며 §6 결과와 함께 적는다.

## 6. TraceLog 제어 소켓 인자 확인 (C-07, P11-3 [미확인]) — [`pc-setup.md` §2a](pc-setup.md)
- [ ] 엔진 소스(`C:\Program Files\Epic Games\UE_5.8\Engine\Source\Runtime\TraceLog\…`, `…\Core\Private\ProfilingDebugging\TraceAuxiliary.cpp`)에서 `Writer_ControlListen`(또는 제어 포트 1985를 여는 함수) 호출 조건과 `FParse` 인자(`-trace=`, `-notrace`, `-tracehost` 등)를 찾는다. Launcher 빌드에 소스가 없으면 "소스 없음"으로 적는다.
- [ ] 리스너를 끄는 인자가 있으면 그 인자로 `Golmok.exe`를 실행해 `netstat -ano | findstr 1985`가 비는지 확인한다. 결과를 `pc-setup.md` §2a에 한 줄로 적는다(보조안 — 고정 경로가 주 대책).

## 7. 결과
| 항목 | 기대 | 결과/근거 |
|---|---|---|
| 세션/head | 날짜·워크트리·기준 SHA | (대기) |
| §0 빌드·자동화 | 36 Success | (대기) |
| §1 P14-2 | 스윕 없음·랙 정상·zone 없는 페이드 인 | (대기) |
| §2 T23 (a)~(d) | 발 화면 밖 0·머리 잘림 0 | (대기) |
| §3 Full Precision UV | 로그 줄·LOD0 체크·임포트 시간 | (대기) |
| §4 Yeonnam 성능 | clock − fixed < 1.0 ms(또는 재검토 필요) | (대기) |
| §5 패키지 | 발소리·Manny·전환 | **선행 실행(V-11 세션, 2026-10-09, main `3cfeec5`, `GOLMOK_PKG_DIR` 미설정 → V-11 워크트리의 같은 exe 경로, 방화벽 창 없음)**: ① ✅ W 발소리(루프백 34 시작점, 0.37 s 간격) ② ✅ 첫 프레임 마네킹·`Character mesh … not found` 없음 ③ ⚠️ `list`·`proxy135`·`manny` ✅, **`quinn` 거절**(`SKM_Quinn_Simple` 미쿡) → `[WP-18 hook]` `+DirectoriesToAlwaysCook=(Path="/Game/Characters/Mannequins")` 로컬 시험(미커밋)으로 해결 확인. 남은 것: 클라우드 훅 반영 뒤 이 카드에서 `GOLMOK_PKG_DIR` 경로로 ③만 재확인. 세부 [wp18a §14-6](pc-verify-wp18a.md) |
| §6 TraceLog | 인자 유무·1985 | **확인(V-11 세션, 2026-10-09)**: 리스너를 끄는 런타임 인자 없음(소스: `Writer_InternalInitializeImpl` → `Writer_InitializeControl`, `-notrace` 파싱 없음), 실행마다 `netstat`에 `TCP 0.0.0.0:1985 LISTENING`. [pc-setup §2a](pc-setup.md)에 기록. 이 카드에서 다시 할 필요 없음 |

STATUS 반영(PC 세션이 자기 행만): V-17 행 결과, 세션 로그. 다른 행(WP-15a·V-14·WP-18·V-11·WP-06·V-05·WP-14a·V-13·C-07·V-10)은 클라우드 병합 커밋이 옮긴다 — PR 본문에 "병합 시 반영" 문안을 적는다.
