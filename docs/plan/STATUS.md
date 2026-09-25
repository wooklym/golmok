# 진행 상태 보드 (plan/STATUS)

갱신 규칙: 각 세션이 시작·종료 시 자기 행을 고친다. 상태 기호:
⚪ 대기 · 🔵 진행 중 · 🟡 코드 완료·PC 검증 대기 · 🟢 완료 · 🔴 막힘 · ⏸ 보류

마지막 갱신: 2026-09-25 (WP-11 🟢 완료 → PR #16 draft)

## 마일스톤

| M | 상태 | 근거 |
|---|---|---|
| M1 클라우드 코드 완료 (WP-01~08) | 🟢 2026-09-25 | 전부 main에 병합(PR #2~#13), CI 초록, pytest 494 passed. WP-04/05는 PC 검증까지 🟢, WP-06은 🟡(V-04 대기) |
| M2 PC 빌드·PIE 검증 | 🔵 진행 중 | V-01 §0~2 🟢, V-02 🟢, V-03 🟢(WP-04/05), V-04 ⚪ |
| M3 배경 베이스맵 | 🟡 파일럿 기준 달성 | V-02: 연남동 반경 1 km 실데이터 임포트·보행(ROADMAP 1.2 🟢). 홈 Zone 확정(D-008) 뒤 해당 지역으로 재확인 |
| M4 D-010 확정 | ⚪ | 스파이크 1.1(V-05) — C-01/C-02 촬영 대기 |

후속 클라우드 WP(계획서 잔여 항목, M1 이후): **WP-09**(Fable ultracode) → **WP-11**(Opus) → **WP-10**(Opus). 순서·범위는 DEVELOPMENT-PLAN §5.1.

## 트랙 1A — 클라우드 코드 (순차)

| WP | 이름 | 상태 | 세션 | 인계 메모 |
|---|---|---|---|---|
| WP-01 | 저장소 기반·CI | 🟢 완료 | session_01QwUxcoWCFmtiJhq3ZWByEJ (Opus) | CI 초록(ubuntu 3.11/3.12, windows 3.12, repo-check, tiles-validate). 커밋 전 `cd tools && ruff check . && ruff format --check . && pytest -q && python scripts/check_repo.py` |
| WP-02 | Zone 데이터 모델·CLI `golmok-zone` | 🟢 완료 | session_014zvy99LzAuVhnHYFtUYfVz (Opus) | 스펙 `docs/spec/zone-manifest.md`(필드·좌표·UE 매핑·수치 예제 표). transform은 **row-major**, UE Yaw = −yaw_deg, ENU→UE `diag(100,−100,100)`. 픽스처 `tools/tests/fixtures/zones/z_synthetic_001/v1/`(WP-04가 복사). 베이스맵 origin 높이는 `--geoid-offset` 없으면 정표고(WP-07 주의) |
| WP-03 | 재구성 후처리 `golmok-mesh` / `golmok-splat` | 🟢 완료 | session_014zvy99LzAuVhnHYFtUYfVz (Opus) | 청크 = `visual/<id>.obj`+MTL(Z-up, UDIM 유지), 충돌·blocker GLB = glTF Y-up. open3d 제외(D-002). splat 3D Tiles = `KHR_gaussian_splatting`(검증기 0.6.1은 확장 속성 이름만 오류). PC 절차 `runbooks/recon-postprocess.md` — [미확인] 항목은 V-05에서 확인 **병합 전 적대적 리뷰(Fable 리뷰 6관점 → Opus 검증 → Opus 수정) 반영: 확정 결함 17건 수정, 테스트 180 passed. 청크 id 규약이 zone 원점 기준 절대 셀 `c_e000_n000`로 바뀜(WP-04·06 주의)** |
| WP-04 | UE C++ 1: Geo·Zone | 🟢 완료(PC 검증 통과) | session_01GGmw3pPHLp4Wk5Us9243AL (Fable 5.1 ultracode, 검증 Opus) | `Geo/`(순수 수학 헤더 + g++ 교차검증, 원점 액터, GeoSubsystem) · `Zones/`(manifest 파서, `AGolmokZone`, `UGolmokZoneSubsystem`) · `synthetic_zone.py` · 런북 `runbooks/pc-verify-wp04.md`(불확실 API 표 §6). PR #7. **PC(V-03)**: 빌드 → `z.run()` → PIE 체크 (1)~(6). WP-05 훅 `SpawnPortals/GetPortalWorldTransform/RequestLoad`, WP-06은 `synthetic_zone.find_or_spawn_*` 재사용. Zone Index 기반 발견은 미구현(레벨 배치 액터만) |
| WP-05 | UE C++ 2: 포털·조명·디버그 | 🟢 완료(PC 검증 통과) | session_01W4S1qYJPhQaziYbJMvAXMo (Fable 5.1 ultracode, 검증 Opus) | `Lighting/`(프리셋 JSON 단일 소스·`AGolmokTimeOfDay`) · `Portals/`(`AGolmokPortal`, 스트리밍 2경로 ini 선택) · `Debug/`(HUD·통계·경로 녹화/재생·CSV·스크린샷, 순수 헤더 g++ 교차검증) · `Player/GolmokPlayerController` · 합성 실내 `z_synthetic_001_interior` + `synthetic_zone.run(interior=True)` · 런북 `runbooks/pc-verify-wp05.md`(§11 불확실 API 64행). PR #10. **PC(V-03)**: WP-04 런북 뒤에 실행, `test.ps1`로 UE 테스트 10개 먼저. WP-06: 서브레벨은 레벨 좌표·`L_<zone_id>` 규약, 포털은 C++가 스폰(Python 배치 금지), 조명 액터 태그 `GolmokLighting` |
| WP-06 | UE Python 에디터 자동화 2차 | 🟡 코드 완료·PC 검증 대기 | session_011qpTa7U7onDnW7L9jNSgwA (Fable 5.1 ultracode, 검증 Opus 5.5) | `_pure.py`(순수 함수·임포트 계획·LOG) · `zone_import.py`(OBJ 청크+UDIM VT+충돌 임포트, Interchange `_import` 스크래치→규약 경로 이동, GeoOrigin/Zone 리빌드) · `interior_setup.py`(포털 왕복 검사→에셋→서브레벨 PointLight→부모 리빌드) · `spike_runner.py`(PIE 무인 캡처 `capture_all`, `-game` 성능 `.ps1`, 컨택트 시트, research/08 템플릿) · `tools/scripts/make_synthetic_zone.py`(합성 zone 생성기, 클라우드 검증) · 가짜 `unreal`(`tests/fake_unreal.py`) 테스트 +171(전체 494 passed) · 런북 `runbooks/pc-verify-wp06.md`(불확실 API 표 §12 38행)·`runbooks/pc-spike.md`. PR #12. 적대적 검증 1라운드 33→확정 28 수정·반박 5; 2라운드 소견 6건은 **미검증**(WP-06 문서 결과 표). **PC(V-04)**: 런북 §1~§8 순서, 실측(route·매핑·UDIM 표기)을 §11 표에 **병합 전 Opus 보완 리뷰**: 블로킹 2건 수정(런북 §0 `L_ZoneTest06` 사본으로 픽스처 겹침 회피, `legacy_flag` 캐시 적중 재전송) + 2라운드 6건 판정(WP-06 문서 "결과" 표; ② Full Precision UV는 V-05 전 반영) |
| WP-07 | 정합·검수 `golmok-align` | 🟢 완료(합성 검증) | session_01Cgm7f6oD6xSMpZ5jszj8Xi (Fable 5.1) | `golmok-align run/compare/check-blur`. GPS prior(level Umeyama+RANSAC) → 벽 ICP(dof 4/6) → 지면 ICP(수직만) → manifest transform/origin/quality 갱신 + align_report.md. open3d 대신 numpy/scipy(리눅스 CI에 libEGL 없음). 합성: 2°·1.4 m 교란을 3 cm 이내 복원. **실 Zone 검증은 V-05.** collision.glb 축 규약은 `--mesh-axes`로 맞춘다(WP-03 결정 대기) |
| WP-08 | (선택) 웹 검수 뷰어 | 🟢 완료 | session_01Cgm7f6oD6xSMpZ5jszj8Xi (Fable 5.1) | `golmok-viewer`(CesiumJS 1.145, ion 없음) + `tools/viewer` + Playwright 스모크(`npm test`, 합성 베이스맵 18타일). Zone manifest 오버레이(footprint·청크 bbox·포털·blockers, `?zone=…/manifest.json`) 포함. 충돌 메시 표시는 WP-03 산출물 나오면 추가 |

| WP-09 | UE C++ 3: Zone Index 발견·비동기 로드 + V-03 디버그 표시 정리 | 🟡 코드 완료·PC 검증 대기 | session_016UiCeoD2Sytfh4nSweonbs (Fable 5.1 ultracode, 심판·검증·수정 Opus 5.5) | `Zones/GolmokZoneIndex`(순수 파서·셀 캐시·3×3) · `UGolmokZoneSubsystem::OnEvaluateTimer = DiscoverZones → Evaluate`(Transient 스폰·파괴·retire, 배치 우선, `bPortalManaged`, 재진입 카운터) · `AGolmokZone::LoadAsync`(FStreamableManager, `Loading`, 완료 항상 다음 틱, 세대 취소, `bAsyncLoad=True`) · 포털 선로드 + `Loading`이면 Pending 유지 · `GOLMOK_RENDER_TIME_SOURCE`+`HoldLastPositive` · 콘솔 `golmok.zone.index` · Python `zone_index.sync`/`zone_import(with_index=)` · 픽스처 `z_synthetic_002`+`index/`(생성기 `make_index_fixture.py --check`) · pytest +70(전체 569 passed) · UE 자동화 5개(전체 16) · 런북 `runbooks/pc-verify-wp09.md`(불확실 API §11 34행+). PR #15. 적대적 검증 1라운드 13→확정 13(실질 8, major 2) 전부 수정·반박 0·미검증 0. **PC(V-07)**: 런북 §1~§10 순서; §7에서 render 소스 매크로 기본값 확정, §6 히치 표. WP-04 "남은 것"(Index 발견·bAsyncLoad) 해소 **병합 전 Opus 보완 리뷰**: 블로킹 없음, 비블로킹 3건 반영(GeoOrigin 없는 레벨 경고 억제, `ResolveObject` 우선, index 동일 파일 복사 건너뜀), V-07 메모 6건(WP-09 문서 "결과") |
| WP-10 | 애니메이션 평가·게임 기능 제안(문서) | ⚪ 대기 | (Opus) | 스펙 `plan/WP-10-animation-features-proposal.md`. ROADMAP 1.3 애니메이션 행, DEVELOPMENT-PLAN §11 #6(D-013~ 제안), night 프리셋 look-dev 메모. UE 코드 변경 없음, 제안 승인은 사용자 |
| WP-11 | 웹 검수 뷰어 2차(충돌·blocker 메시 오버레이) | 🟢 완료 | session_01CSQya6KM72tpKC8L7aowSx (Opus 5.5) | `tools/viewer/zonemath.js`(glTF Y-up → zone-local → ECEF 한 곳, Cesium 기본 축 보정 끔 — 기본값이면 90° 돌아감) · `app.js` collision/blockers GLB `Cesium.Model`·오버레이 체크박스 6개·원점 E·N·U 축 · `golmok-viewer --zone`(`/zones/<zone_id>/v<n>/`, 확장자 화이트리스트, 경로 탈출 거절) · pytest +49(전체 618 passed) · `npm test` 단위 5 + 스모크(zone 2·모델 4·배치 오차 < 5 cm·토글). OBJ 청크는 bbox만. CI에는 `npm test` 잡 없음(로컬 게이트). PR #16

## 트랙 1B — PC 검증 (PC Claude 세션)

| V | 내용 | 상태 | 메모 |
|---|---|---|---|
| V-01 | PC 셋업·L_Dev·리허설 점검 (`runbooks/pc-setup.md` §0~4) | 🔵 진행 중 | §0~2 🟢(2026-09-24): UE 5.8.3·VS 2026 빌드 무수정 통과, L_Dev·마네킹 PIE, 자동 테스트 `Golmok.Player.Movement`(`tools/ue/test.ps1`) 통과, pytest·CUDA OK. 결과 ROADMAP 1.0a~1.0d. §3 리허설은 C-01 사진과 EgoBlur 모델(사용자 라이선스 동의) 대기. **push는 이 PC의 GitHub 로그인 필요**(사용자). 클라우드 인계(WP-06 필독): ① `viewpoints.capture`가 스크린샷을 빠뜨리거나 **다른 시점 이름으로 저장**하던 버그 수정(파일 기록 대기, missing 보고, 게임 뷰). 단 **에디터 창이 백그라운드에 오래 있으면 뷰포트를 그리지 않아 스크린샷이 안 나온다**("백그라운드 CPU 절약" 꺼도 같음) → `spike_runner`의 무인 캡처는 PIE/`-game`의 `HighResShot`으로 설계할 것. ② `golmok-perf`가 실제 5.8 CSV에서 죽던 문제(긴 필드)와 맵 로딩 프레임이 평균에 섞이던 문제 수정, `-game` CSV 위치는 `%LOCALAPPDATA%\UnrealEngine\5.8\Saved\Profiling\CSV`. 기준선(빈 L_Dev 1080p 158 fps / 1440p 128 fps)은 `research/08`. ③ `golmok.lighting` 4개 프리셋 에디터 검증 ✅. ④ `check_repo.py`에 병합 충돌 표시 검사 추가 |
| V-02 | 베이스맵 실데이터 (`pc-setup.md` §5) | 🟢 완료 | 연남동 반경 1 km: 건물 9,447동, 64타일, **5 m DEM**(수치지형도 등고선·표고점, `contour-dem`). UE `L_Basemap_Yeonnam`: fit error ≈0, 북쪽 −Y, 파사드 패턴, PIE 보행 OK, 1080p 169 fps(1% low 141), 충돌 추적 169/169(지형 Nanite 끔). 신규 `golmok-basemap georef-ortho`(좌표 없는 NGII 정사영상), `M_BasemapTerrain`. 결과·근거: ROADMAP 1.2, D-012 |
| V-03 | WP-04/05 빌드·PIE 검증 | 🟢 완료 | 2026-09-25 PC 세션(Fable 5.1), 브랜치 `pc/v03-verify-wp04-05`(PR → main). 빌드 통과(수정 `e446504`), 자동화 테스트 **11/11 Success**(실내 있을 때 Portal.* 3개 실제 실행), WP-04 런북 §2~§4 전부 ✅, WP-05 런북 §1~§8·§10 ✅(§9 패키징은 선택이라 미실행). 결과 표·스크린샷은 두 런북 맨 아래. **PC 수정 5건**(다음 클라우드 세션 WP-09/WP-06 필독): ① C++ `e446504` — 5.8 `FJsonObject::Values`가 `UE::FSharedString` 키(`TryGetField`/`FString(*Pair.Key)`), `GGameThreadTime`/`GRenderThreadTime`은 RenderCore(`RenderTimer.h`, Build.cs `RenderCore`), `REN_ForceNoResetLoaders` 제거. ② Python `12e6bad` — 5.8 Interchange가 glTF 메시를 `<폴더>/<소스>/StaticMeshes/<이름>`에 두므로 `_import`로 임포트 후 `rename_asset`로 규약 경로로 이동(**WP-06 `zone_import.py`도 같은 처리 필요**). ③ Python `dd2c538` — 빈 `L_ZoneTest`(첫 실행 실패 잔재)를 열면 조명 재생성. ④ Python `84f33c5` — `register_interior_sublevel()`이 서브레벨만 저장하던 버그(`add_level_to_world`가 current level을 바꿈) → `save_map`으로 영속 맵 저장 + `unregister_interior_sublevel()`. ⑤ 설계와 다른 동작(코드 미수정, 런북 §12 표): `golmok.screenshot`에 HUD 포함(깨끗한 캡처는 `golmok.hud 0` 뒤에 — spike_runner), HUD `render` ms가 자주 0.00(`GRenderThreadTime` 읽는 시점), night 프리셋은 태양 off + real-time SkyLight라 화면 검정(달빛/최소 lux 필요 — D-010 look-dev), 포털 언로드 뒤 실내 zone이 `blocked` 표시. 무인 검증 도구(에디터 Python PIE 드라이버, SendInput 키)는 이 세션 스크래치에만 있음 — 재현하려면 런북 절차를 사람이 수행 |
| V-04 | WP-06 에디터 Python 검증 | ⚪ 대기 | 런북 `runbooks/pc-verify-wp06.md`(V-03 뒤; `L_ZoneTest` 전제): `python tools\scripts\make_synthetic_zone.py --out D:\golmok_synth --interior` → `zi.run` → PIE 걷기 → `it.run` → 포털 왕복 → 재실행 → `spike_runner` 리허설 → `-game` 성능. 실패는 §12 표 번호로 수정·`WP-06: PC fix` 커밋. 이어서 V-05는 `runbooks/pc-spike.md` |
| V-05 | 재구성·후처리·스파이크 1.1 | ⚪ 대기 | C-02 필요 |
| V-06 | Zone 통합·튜닝·패키징 | ⚪ 대기 | D-010 이후 |
| V-07 | WP-09 Zone Index·비동기 로드 검증 | ⚪ 대기 | 런북 `runbooks/pc-verify-wp09.md`(V-04 뒤; `L_ZoneTest`+합성 실내 전제): §1 index 동기화(`git status` 깨끗) → §2 빌드 → §3 `test.ps1 -Filter Golmok.Zone` 5개 → 전체 16 → §4 `L_ZoneTest09`(배치 액터 없이 발견·로드) → §5 동쪽 1.5 km 파괴 → §6 `bAsyncLoad` True/False 히치 표 → §7 render ms 소스 1/2/0 대조(매크로 기본값 커밋) → §8 실내 `portal` 표시·포털 대기·재진입 → §10 PIE 종료. 실패는 §11 표 번호로 수정·`WP-09: PC fix` 커밋 |
| V-08 | 애니메이션 3안 PC 평가 | ⚪ 대기 | `runbooks/pc-verify-animation.md`(WP-10이 작성; L_Dev, 채점표) |

## 트랙 1C — 사용자

| C | 내용 | 상태 |
|---|---|---|
| C-01 | 아이폰 리허설 — ProRAW 형식 **JPEG 무손실**로 찍는다(D-011, 가이드 #1 v3 §4-A) | ⚪ |
| C-02 | 골목 촬영(홈 Zone 후보 포함) | ⚪ |
| C-03 | 베이스맵 데이터 다운로드 | 🟢 (수치지형도 6도엽 추가 2026-09-25) |
| C-04 | PC 업그레이드 결정, Postshot Studio, XGRIDS 문의 | ⚪ |
| C-05 | 실내 동의·촬영 | ⚪ |
| C-06 | S-Map 문의 발송 | ⚪ |

## 결정 필요 (세션이 발견한 것)
- ~~DEM 5 m 출처~~ → 2026-09-25 ② 수치지형도 등고선·표고점으로 생성(`golmok-basemap contour-dem`, D-012)
- ~~NGII 데이터 국외 반출~~ → 2026-09-25 사용자 법률 자문 완료, 업로드 허용(D-012)

## 세션 로그
| 날짜 | 세션 | 모델 | 대상 | 결과 |
|---|---|---|---|---|
| 2026-09-24 | session_01NM6uvZaVMgq5SUSaduHD1Z | Fable 5.1 | 개발 전체 과정 설계, WP 문서, 오케스트레이션 | PR #2 |
| 2026-09-24 | session_01QwUxcoWCFmtiJhq3ZWByEJ | Opus | WP-01 | 🟢 CI·check_repo·ruff. Actions 실행 36007213938/36007216880 success |
| 2026-09-24 | session_014zvy99LzAuVhnHYFtUYfVz | Opus | WP-02 | 🟢 zone 스펙·스키마·`golmok-zone`·테스트 80개(전체 116 passed) |
| 2026-09-24 | session_01Cgm7f6oD6xSMpZ5jszj8Xi | Fable 5.1 | PR #1·#2 병합(main), WP-08 검수 뷰어, PC 작업 카드 2건 | PR #3 (`claude/golmok-phase-0-research-4kloq6`). 전체 119 passed |
| 2026-09-24 | session_014zvy99LzAuVhnHYFtUYfVz | Opus | WP-03 | 🟢 golmok-mesh·golmok-splat·런북, 테스트 30개(전체 144 passed) |
| 2026-09-24 | PC 로컬 세션 (trusting-varahamihira) | Opus 5.5 | V-02 베이스맵 실데이터 | 🟢 SHP 컬럼 매핑·연남동 빌드·UE 임포트·보행·fps. georef-ortho, M_BasemapTerrain, UE 5.8 CustomInput 수정. 전체 123 passed |
| 2026-09-24 | session_01GGmw3pPHLp4Wk5Us9243AL | Fable 5.1 ultracode (검증 Opus) | WP-04 | 🟡 설계 패널 3안→심판→종합, Geo·Zones C++, 적대적 리뷰 20건(확정 6 수정·반박 14), 테스트 38개 추가(전체 218 passed, 2 skipped, 189 warnings in 12.06s). PR #7 |
| 2026-09-24 | PC 세션(Claude Desktop, 사용자 PC) | Opus 5.5 | V-01 PC 셋업·UE 검증, JPEG-XL ProRAW 발견 → D-011 JPEG 무손실, 스파이크 도구 에디터 검증 | 🔵 `claude/golmok-phase-0-research-4kloq6`에 커밋(사용자 push 대기). 전체 125 passed, check_repo OK |
| 2026-09-25 | PC 로컬 세션 (trusting-varahamihira) | Opus 5.5 | V-02 후속: 5 m DEM | 🟢 수치지형도 6도엽 → `contour-dem`(RMSE 2.1 m), 재빌드·UE 재임포트, 지형 Nanite 끔(충돌 틈 수정), 1080p 169/141 fps. 전체 142 passed |
| 2026-09-25 | PC 로컬 세션 (relaxed-swartz, Claude Desktop) | Fable 5.1 | V-03 WP-04/05 PC 검증 | 🟢 빌드 수정 3건(C++ 1·Python 3 커밋), 자동화 11/11, WP-04 런북 전부 통과, WP-05 런북 §1~§8·§10 통과(경로 B: ✅ (Python 수정 1건 뒤)), 설계와 다른 동작 4건 기록. PR `pc/v03-verify-wp04-05` → main |
| 2026-09-25 | session_011qpTa7U7onDnW7L9jNSgwA | Fable 5.1 ultracode (심판·검증·수정 Opus 5.5) | WP-06 | 🟡 설계 패널 3안→심판 2→종합, `_pure`/`zone_import`/`interior_setup`/`spike_runner`/합성 zone 생성기, 가짜 unreal 테스트 +171(전체 494 passed, 3 skipped), 적대적 검증 1라운드(33→확정 28·반박 5, 2라운드 중단·6건 미검증), 런북 2개. main V-03 병합·PC 발견 6건 반영. PR #12 |
| 2026-09-25 | session_01W4S1qYJPhQaziYbJMvAXMo | Fable 5.1 ultracode (검증 Opus) | WP-05 | 🟡 설계 패널 3안→심판 2→종합, Lighting·Portals·Debug·Player C++ + 합성 실내, 적대적 리뷰 3라운드(원시 25→11→1, 확정 33·반박 4, 전부 반영), 테스트 +95(전체 323 passed, 3 skipped), UE 자동화 10개, 런북. PR #10 |
| 2026-09-25 | session_01NM6uvZaVMgq5SUSaduHD1Z | Fable 5.1 (오케스트레이터) | PR #12 병합, M1 기록, WP-09/10/11 스펙 | 🟢 WP-06 병합 전 로컬 게이트(494 passed)·Opus 보완 리뷰, V-04 카드, M1 달성 기록, 후속 WP 스펙 3개·STATUS/DEVELOPMENT-PLAN 행 |
| 2026-09-25 | session_016UiCeoD2Sytfh4nSweonbs | Fable 5.1 ultracode (심판·회의론자·수정 Opus 5.5) | WP-09 | 🟡 설계 패널 3안→심판 2→종합, C++(GeoMath 셀·ZoneIndex·발견/파괴·비동기 로드·포털 대기·디버그 정리)·Python zone_index·픽스처 002+index·UE 자동화 5개·런북, 적대적 검증 1라운드(13→확정 13 전부 수정, 반박 0), pytest +70(전체 569 passed, 3 skipped), Windows CI 수정 2건. PR #15 |
| 2026-09-25 | session_01CSQya6KM72tpKC8L7aowSx | Opus 5.5 | WP-11 | 🟢 뷰어 충돌·blocker GLB 오버레이·토글·원점 축, `--zone` 마운트·경로 탈출 거절, zonemath 단위·Python 교차검증, 스모크 확장. pytest 618 passed(+49), npm test OK. PR #16 |
