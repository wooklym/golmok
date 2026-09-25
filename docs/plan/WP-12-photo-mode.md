# WP-12 — 포토 모드 최소판 (D-013)

상태: 🔵 진행 중 (등록 2026-09-25, 시작 2026-09-25, session_01R7589q1vh4DRPq4NeCsZ4Q) · 담당: 클라우드 Claude 세션(**Fable 5.1 ultracode**, 검증 Opus 5.5 — 모델 정책 DEVELOPMENT-PLAN §7.4) · 의존: WP-05(디버그 스크린샷·HUD·시간대 프리셋), WP-04(Geo·Zone), WP-09(zone 발견) · 검증: G2(`runbooks/pc-verify-wp12.md`, V-09, PC 세션)

## 목표
플레이어가 키 하나로 **포토 모드**에 들어가 게임을 멈추고, 캐릭터 주변에서 자유 카메라로 구도를 잡아 고해상도 사진을 찍는다(D-013 최소판, 사용자 승인 2026-09-25). 실사 재구성 골목을 "내가 찍은 사진"으로 남기는 공유 동력이자, 스파이크·회귀 비교 캡처 도구와 겹친다. 범위·근거: [`design/game-features-proposal.md`](../design/game-features-proposal.md) D-013.

## 배경(코드에서 확인할 것)
- 촬영 경로는 WP-05 `UGolmokDebugSubsystem`의 `golmok.screenshot <tag> [name]`(`HighResShot N filename=…`, `Saved/Screenshots/Golmok/<tag>/<preset>/`, 다음 프레임에 기록)을 **재사용**한다. V-03 발견: 이 스크린샷에는 HUD가 포함된다 → 포토 모드는 촬영 직전 HUD와 자기 오버레이를 끄고 찍는다.
- 입력은 C++ Enhanced Input(`Player/GolmokCharacter.cpp` `IMC_Default`, `Player/GolmokPlayerController.cpp` F1~F10·1~4 디버그 키). 포토 모드 키는 기존 키와 겹치지 않게(권장 `P`, 게임패드 `Gamepad_Special_Left`/`Back`), 포토 모드 안에서는 별도 매핑 컨텍스트(`IMC_Photo`)를 더 높은 우선순위로 추가하고 나갈 때 제거.
- 시간대 프리셋 이름은 `AGolmokTimeOfDay`(WP-05), 플레이어 경위도는 `UGolmokGeoSubsystem::LevelUEToLonLat`(WP-04, 원점 없으면 실패 → 메타에 `null`), 현재 zone은 `UGolmokZoneSubsystem`(플레이어 위치가 footprint 안인 로드된 zone, 없으면 `null`).
- 디버그 카메라 폰 `Debug/GolmokPathPawn`(경로 재생용)이 있으나 포토 모드는 플레이어 입력으로 움직이는 **별도 폰**이 낫다(설계 패널이 재사용 여부 판단).
- 일시정지 중 입력·틱: `UInputAction::bTriggerWhenPaused`, `AActor::SetTickableWhenPaused`, `APlayerController::SetPause`의 5.8 동작은 **엔진 헤더에서 확인**하고 불확실하면 런북 "불확실 API" 표에 적는다(추측 금지).

## 산출물 (`unreal/Golmok/Source/Golmok/Photo/`, `Config/`, `docs/`)
1. **`UGolmokPhotoModeSubsystem`**(World 서브시스템) + **`AGolmokPhotoCameraPawn`**: 진입 시 게임 일시정지(캐릭터·시간대 전환·포털 타이머 정지, 오디오는 WP-13 뒤 연동), 현재 카메라 위치·회전에서 자유 카메라 시작, 나가면 원래 폰·HUD·PostProcess·일시정지 상태 복원(진입 전에 이미 일시정지였으면 유지). 콘솔 `golmok.photo [0|1]`, `golmok.photo.shoot`, `golmok.photo.reset`.
2. **자유 카메라 제약**: 캐릭터 반경 `MaxDistanceM`(Config, 기본 3.0 m) 구 안, 벽·바닥 충돌(구 컴포넌트 스윕, 재구성 메시 뒷면·구멍으로 새지 않게 반경 15 cm), 로드된 zone이 있으면 그 footprint(ENU 다각형, WP-04 파서) 안으로 클램프. 클램프·다각형 포함 판정은 **순수 헤더 `GolmokPhotoMath.h`**(UE 타입 없음)로 두고 pytest에서 g++ 교차검증(WP-04 `GolmokGeoMath.h`·`test_ue_geo_math.py` 방식).
3. **조절 항목**(키·게임패드, 화면 왼쪽 아래 작은 텍스트 오버레이 — HUD 클래스 재사용, 촬영 시 숨김): FOV(20~110°), 노출 보정(EV ±3), 피사계 심도(초점 거리 0.3~50 m, 조리개 f/1.4~f/16; `FPostProcessSettings` 오버라이드를 폰 카메라 컴포넌트에), 카메라 롤(±15°), 캐릭터 숨김 토글, 오버레이 숨김 토글, 리셋. 값은 `Config/Golmok/photo.json`(단일 소스: 기본값·범위·키 힌트 문자열)로 두고 WP-05 `lighting_presets.json`처럼 pytest 스키마 검사 + UFS 스테이징.
4. **촬영**: `UGolmokDebugSubsystem`의 스크린샷 함수를 public API로 분리해 호출(`HighResShot` 배율 `ScreenshotMultiplier` 기본 2, 상한 `MaxMultiplier` 기본 3 — RTX 5060 8 GB VRAM 고려, 런북에서 실측해 조정). 파일 `Saved/Screenshots/Golmok/photo/<yyyymmdd_hhmmss>.png` + 같은 이름 `.json`(스키마: `version`, `time_utc`, `preset`, `zone_id`/`zone_version` 또는 null, `lon`/`lat`/`height_m` 또는 null, `ue_location`·`rotation`, `fov`, `exposure_ev`, `dof:{focal_m, fstop}`, `multiplier`, `character_hidden`). 촬영 중 오버레이·HUD·캐릭터(숨김 켰으면) 상태를 보장하고, 기록이 끝나면 오버레이 복원.
5. **법·정책 문구**: `docs/research/05-legal-policy.md`의 공개 전 자문 항목에 "사용자 촬영 스크린샷 외부 공유(간판·상호·블러 누락 얼굴)" 추가(문서만; 판단은 D-009 자문).
6. **테스트**: UE 자동화 `Golmok.Photo.EnterExit`(일시정지·복원, `-nullrhi`), `Golmok.Photo.Clamp`(반경·다각형), `Golmok.Photo.MetaJson`(필드·null 규칙); pytest `test_ue_photo_math.py`(g++ 교차검증), `test_ue_config_photo.py`(JSON 스키마); 기존 WP-04/05/09 테스트 전부 통과.
7. **런북** `docs/runbooks/pc-verify-wp12.md`(V-09): 빌드 → `test.ps1 -Filter Golmok.Photo` → PIE에서 진입/조절/촬영/복원 → 배율 2·3에서 VRAM·소요 시간 → 벽 관통·zone 밖 이탈 시도 → 실내(포털) 안에서 촬영 → 스크린샷 4장(JPG 축소)을 런북에 첨부 → 불확실 API 표.

## 완료 기준
클라우드: 설계 패널 기록(`docs/plan/WP-12-photo-mode.md` "설계" 절), 코드·테스트·런북 작성, pytest·ruff·check_repo 통과, CI 초록, STATUS `🟡 코드 완료·PC 검증 대기`. PC: V-09 통과 → `🟢`.

## 주의
- D-003: 로직은 C++, 위젯 에셋은 만들지 않는다(텍스트 오버레이는 HUD `Canvas` 그리기). 새 플러그인·에셋·의존성 없음.
- WP-05 규약 유지: 일시정지 중 `AGolmokTimeOfDay` 전환·포털 타이머가 어긋나지 않게(진입 전 상태 저장·복원), `Load()` 스택에서 RegisterZone/RequestLoad 금지.
- 5.8 주의(V-03·WP-09): `FJsonObject::Values`는 `UE::FSharedString`, MSVC C4458 섀도잉은 오류, `GRenderThreadTime`은 `RenderTimer.h`. Windows CI: 경로 `pathlib`, 서브프로세스 `encoding="utf-8"`, 테스트 픽스처 `newline="\n"`, 부동소수 비교 `pytest.approx`.
- 세션 운영: 적대적 검증 최대 1라운드, Workflow 2시간 상한, 1.5시간마다 커밋·push. 비용 보고는 STATUS 세션 로그에.
