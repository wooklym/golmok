# 진행 상태 보드 (plan/STATUS)

갱신 규칙: 각 세션이 시작·종료 시 자기 행을 고친다. 상태 기호:
⚪ 대기 · 🔵 진행 중 · 🟡 코드 완료·PC 검증 대기 · 🟢 완료 · 🔴 막힘 · ⏸ 보류

마지막 갱신: 2026-09-27 (WP-18 설계 병합 기록·D-018 ① 승인, #23 구현 병합과 V-11 GUI/V-12는 별도)

## 마일스톤

| M | 상태 | 근거 |
|---|---|---|
| M1 클라우드 코드 완료 (WP-01~08) | 🟢 2026-09-25 | 전부 main에 병합(PR #2~#13), CI 초록, pytest 494 passed. WP-04/05는 PC 검증까지 🟢, WP-06은 🟡(V-04 대기) |
| M2 PC 빌드·PIE 검증 | 🔵 진행 중 | V-01 §0~2 🟢, V-02 🟢, V-03 🟢(WP-04/05), V-07 🟢(WP-09), V-04 ⚪ |
| M3 배경 베이스맵 | 🟡 파일럿 기준 달성 | V-02: 연남동 반경 1 km 실데이터 임포트·보행(ROADMAP 1.2 🟢). 홈 Zone 확정(D-008) 뒤 해당 지역으로 재확인 |
| M4 D-010 확정 | ⚪ | 스파이크 1.1(V-05) — C-01/C-02 촬영 대기 |

후속 클라우드 WP: ~~WP-09 → WP-11 → WP-10~~(2026-09-25 전부 병합) → **게임 기능(D-013~D-017 승인 2026-09-25)**: **WP-12** 포토 모드(Fable ultracode) → **WP-13** 환경음 기본(Fable ultracode) → WP-14 시간대 폴리시(D-010 뒤) → WP-15 지도·세이브(Phase 2 초반) → WP-16 날씨 → WP-17 현장 녹음(문서). 순서·조건은 DEVELOPMENT-PLAN §5.1.

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

| WP-09 | UE C++ 3: Zone Index 발견·비동기 로드 + V-03 디버그 표시 정리 | 🟢 완료(PC 검증 통과, V-07) | session_016UiCeoD2Sytfh4nSweonbs (Fable 5.1 ultracode, 심판·검증·수정 Opus 5.5) | `Zones/GolmokZoneIndex`(순수 파서·셀 캐시·3×3) · `UGolmokZoneSubsystem::OnEvaluateTimer = DiscoverZones → Evaluate`(Transient 스폰·파괴·retire, 배치 우선, `bPortalManaged`, 재진입 카운터) · `AGolmokZone::LoadAsync`(FStreamableManager, `Loading`, 완료 항상 다음 틱, 세대 취소, `bAsyncLoad=True`) · 포털 선로드 + `Loading`이면 Pending 유지 · `GOLMOK_RENDER_TIME_SOURCE`+`HoldLastPositive` · 콘솔 `golmok.zone.index` · Python `zone_index.sync`/`zone_import(with_index=)` · 픽스처 `z_synthetic_002`+`index/`(생성기 `make_index_fixture.py --check`) · pytest +70(전체 569 passed) · UE 자동화 5개(전체 16) · 런북 `runbooks/pc-verify-wp09.md`(불확실 API §11 34행+). PR #15. 적대적 검증 1라운드 13→확정 13(실질 8, major 2) 전부 수정·반박 0·미검증 0. **PC(V-07)**: 런북 §1~§10 순서; §7에서 render 소스 매크로 기본값 확정, §6 히치 표. WP-04 "남은 것"(Index 발견·bAsyncLoad) 해소 **병합 전 Opus 보완 리뷰**: 블로킹 없음, 비블로킹 3건 반영(GeoOrigin 없는 레벨 경고 억제, `ResolveObject` 우선, index 동일 파일 복사 건너뜀), V-07 메모 6건(WP-09 문서 "결과") **PC(V-07, 2026-09-26)**: 빌드 무수정 통과, 자동화 16/16, 런북 §1~§8·§10 전부 ✅, §9 미실행, `GOLMOK_RENDER_TIME_SOURCE` 1 유지(HUD render = stat unit Draw; 0.00은 엔진 값), 히치 async ≥ sync. 런북 §4 맵 사본 코드 교체(#35) |
| WP-10 | 애니메이션 평가·게임 기능 제안(문서) | 🟢 완료(문서; 제안 승인·PC 평가는 별도) | session_011Jdzkehx5EZRAV1kX7PnGD (Opus 5.5) | `research/09-animation-ue58.md`(현행 `ABP_Unarmed` / GASP 로코모션 이식(**권장 시험**) / Motion Matching 최소 구성 3안, 5.8 릴리스 노트·Motion Matching·GASP·Chooser 공식 문서 인용; Mover는 5.8에서도 Experimental이라 제외) · `runbooks/pc-verify-animation.md`(V-08: §0 라이선스 확인 → GASP 둘러보기 → ① 기준선 → ② 이식(시험 폴더 `Golmok_AnimEval`, 커밋 금지) → ③ 필요 시, 채점표·실패 대안) · `design/game-features-proposal.md` + DECISIONS **D-013~D-017 제안**(포토 모드·Zone 지도·시간대/날씨·환경음·세이브) · `design/lighting-night-lookdev.md`(night 검정 원인 = 태양 숨김 × 대기 0 × real-time SkyLight 0, 후보 A 달빛+B 노출 상한 → E 가로등). **확인 못 함(403)**: Fab EULA, UE EULA, Epic Content License, GASP Fab 리스팅·5.8 블로그, 통신비밀보호법 원문 → 사용자 확인 항목. UE 코드·JSON 변경 없음. 병합 전 Opus 보완 리뷰: Chooser 플러그인 5.8 Experimental(② 리스크에 추가), UAF 노트 인용 정정, 런북 보강(충돌 해결·저장 위치·CSV 위치·성능 조건·정리). PR #17 |
| WP-11 | 웹 검수 뷰어 2차(충돌·blocker 메시 오버레이) | 🟢 완료 | session_01CSQya6KM72tpKC8L7aowSx (Opus 5.5) | `tools/viewer/zonemath.js`(glTF Y-up → zone-local → ECEF 한 곳, Cesium 기본 축 보정 끔 — 기본값이면 90° 돌아감) · `app.js` collision/blockers GLB `Cesium.Model`·오버레이 체크박스 6개·원점 E·N·U 축 · `golmok-viewer --zone`(`/zones/<zone_id>/v<n>/`, 확장자 화이트리스트, 경로 탈출 거절) · pytest +49(전체 618 passed) · `npm test` 단위 5 + 스모크(zone 2·모델 4·배치 오차 < 5 cm·토글). OBJ 청크는 bbox만. CI에는 `npm test` 잡 없음(로컬 게이트). 병합 전 Opus 보완 리뷰 5건(스모크가 사용자 `GOLMOK_DATA` 폴더에 쓰지 않음, CORS 헤더 제거, Windows 예약 이름 거절, zone_id fullmatch·64자, transform 16개 검사) 반영. PR #16
| WP-12 | 포토 모드 최소판(D-013) | ⚪ 대기 | — | 스펙 `plan/WP-12-photo-mode.md`. 일시정지·자유 카메라(반경·footprint 클램프)·FOV/노출/DOF·캐릭터 숨김·고해상도 PNG + 메타 JSON, `Config/Golmok/photo.json`, 순수 헤더 g++ 교차검증, 런북 V-09 |
| WP-13 | 환경음 기본(D-016 (a)) | ⚪ 대기 | — | 스펙 `plan/WP-13-ambience-audio.md`. `research/10` 사운드 출처(라이선스 원문), `Audio/` 앰비언스 크로스페이드·발소리(거리 기반, 재질)·실내/시간대 전환, `audio.json`, `audio_import.py`, WAV(LFS ≤ 40 MB) 또는 플레이스홀더, 런북 V-10 |

## 병행 트랙 — ChatGPT Astra (DEVELOPMENT-PLAN §7.6)

Astra는 이 표를 고치지 않는다. 병합하는 Fable 세션이 Astra WP 문서의 "병합 시 반영" 문안으로 고친다. 예약 번호: WP-18(18a·18b), V-11, V-12, D-018, research/11.

이번 #22/#23은 2026-09-27 사용자가 Astra 자체 리뷰·병합을 직접 지시해 Astra가 병합 기록까지 반영한다. 상시 규칙의 변경은 아니다(D-018).

| 항목 | 내용 | 상태 | 담당 | 메모 |
|---|---|---|---|---|
| WP-18 | 플레이어 캐릭터 | 🔵 설계 완료·18a 스택 PR 검증 완료 | **ChatGPT Astra**, 이번 자체 리뷰·병합 사용자 승인 | [설계 #22](https://github.com/wooklym/golmok/pull/22): A~D/이미지7장/의뢰서 초안/자체 리뷰 완료, D-018 ① 승인. [구현 #23](https://github.com/wooklym/golmok/pull/23)에서 로스터4종·같은 폰 교체·훅2건·UE19 Success 기록. 18b는V-08/V-12/② 이후 |
| V-11 | WP-18a 캐릭터 목록·교체 검증 | 🟡 헤드리스 통과·GUI 대기 | Astra 헤드리스 / Fable PC 후속 | #23에서 빌드·Character3/전체UE19 Success, 실제 포털3회 왕복+실내 교체/확대 거절 통과. GUI 보행·계단·실제 경로 재생·WP-12 포토·hitch/VRAM은 미실행. 런북은 #23의 `runbooks/pc-verify-wp18a.md` |
| V-12 | 캐릭터 룩 검증(프록시) | ⚪ 대기 | Fable 실행·소유자 채점 | [WP-18](WP-18-characters.md) 절차: 프록시2×재질3×조명4 예비 비교, 채택 구성의 배경4곳 재검증. Toon 사본의 PBR 대조군, 야간 환경 실패의 부분 완료 구분. 실제4.5등신 V-08 시험과 최종 에셋 검수 별도 |

## 트랙 1B — PC 검증 (PC Claude 세션)

| V | 내용 | 상태 | 메모 |
|---|---|---|---|
| V-01 | PC 셋업·L_Dev·리허설 점검 (`runbooks/pc-setup.md` §0~4) | 🔵 진행 중 | §0~2 🟢(2026-09-24): UE 5.8.3·VS 2026 빌드 무수정 통과, L_Dev·마네킹 PIE, 자동 테스트 `Golmok.Player.Movement`(`tools/ue/test.ps1`) 통과, pytest·CUDA OK. 결과 ROADMAP 1.0a~1.0d. §3 리허설은 C-01 사진과 EgoBlur 모델(사용자 라이선스 동의) 대기. **push는 이 PC의 GitHub 로그인 필요**(사용자). 클라우드 인계(WP-06 필독): ① `viewpoints.capture`가 스크린샷을 빠뜨리거나 **다른 시점 이름으로 저장**하던 버그 수정(파일 기록 대기, missing 보고, 게임 뷰). 단 **에디터 창이 백그라운드에 오래 있으면 뷰포트를 그리지 않아 스크린샷이 안 나온다**("백그라운드 CPU 절약" 꺼도 같음) → `spike_runner`의 무인 캡처는 PIE/`-game`의 `HighResShot`으로 설계할 것. ② `golmok-perf`가 실제 5.8 CSV에서 죽던 문제(긴 필드)와 맵 로딩 프레임이 평균에 섞이던 문제 수정, `-game` CSV 위치는 `%LOCALAPPDATA%\UnrealEngine\5.8\Saved\Profiling\CSV`. 기준선(빈 L_Dev 1080p 158 fps / 1440p 128 fps)은 `research/08`. ③ `golmok.lighting` 4개 프리셋 에디터 검증 ✅. ④ `check_repo.py`에 병합 충돌 표시 검사 추가 |
| V-02 | 베이스맵 실데이터 (`pc-setup.md` §5) | 🟢 완료 | 연남동 반경 1 km: 건물 9,447동, 64타일, **5 m DEM**(수치지형도 등고선·표고점, `contour-dem`). UE `L_Basemap_Yeonnam`: fit error ≈0, 북쪽 −Y, 파사드 패턴, PIE 보행 OK, 1080p 169 fps(1% low 141), 충돌 추적 169/169(지형 Nanite 끔). 신규 `golmok-basemap georef-ortho`(좌표 없는 NGII 정사영상), `M_BasemapTerrain`. 결과·근거: ROADMAP 1.2, D-012 |
| V-03 | WP-04/05 빌드·PIE 검증 | 🟢 완료 | 2026-09-25 PC 세션(Fable 5.1), 브랜치 `pc/v03-verify-wp04-05`(PR → main). 빌드 통과(수정 `e446504`), 자동화 테스트 **11/11 Success**(실내 있을 때 Portal.* 3개 실제 실행), WP-04 런북 §2~§4 전부 ✅, WP-05 런북 §1~§8·§10 ✅(§9 패키징은 선택이라 미실행). 결과 표·스크린샷은 두 런북 맨 아래. **PC 수정 5건**(다음 클라우드 세션 WP-09/WP-06 필독): ① C++ `e446504` — 5.8 `FJsonObject::Values`가 `UE::FSharedString` 키(`TryGetField`/`FString(*Pair.Key)`), `GGameThreadTime`/`GRenderThreadTime`은 RenderCore(`RenderTimer.h`, Build.cs `RenderCore`), `REN_ForceNoResetLoaders` 제거. ② Python `12e6bad` — 5.8 Interchange가 glTF 메시를 `<폴더>/<소스>/StaticMeshes/<이름>`에 두므로 `_import`로 임포트 후 `rename_asset`로 규약 경로로 이동(**WP-06 `zone_import.py`도 같은 처리 필요**). ③ Python `dd2c538` — 빈 `L_ZoneTest`(첫 실행 실패 잔재)를 열면 조명 재생성. ④ Python `84f33c5` — `register_interior_sublevel()`이 서브레벨만 저장하던 버그(`add_level_to_world`가 current level을 바꿈) → `save_map`으로 영속 맵 저장 + `unregister_interior_sublevel()`. ⑤ 설계와 다른 동작(코드 미수정, 런북 §12 표): `golmok.screenshot`에 HUD 포함(깨끗한 캡처는 `golmok.hud 0` 뒤에 — spike_runner), HUD `render` ms가 자주 0.00(`GRenderThreadTime` 읽는 시점), night 프리셋은 태양 off + real-time SkyLight라 화면 검정(달빛/최소 lux 필요 — D-010 look-dev), 포털 언로드 뒤 실내 zone이 `blocked` 표시. 무인 검증 도구(에디터 Python PIE 드라이버, SendInput 키)는 이 세션 스크래치에만 있음 — 재현하려면 런북 절차를 사람이 수행 |
| V-04 | WP-06 에디터 Python 검증 | ⚪ 대기 | 런북 `runbooks/pc-verify-wp06.md`(V-03 뒤; `L_ZoneTest` 전제): `python tools\scripts\make_synthetic_zone.py --out D:\golmok_synth --interior` → `zi.run` → PIE 걷기 → `it.run` → 포털 왕복 → 재실행 → `spike_runner` 리허설 → `-game` 성능. 실패는 §12 표 번호로 수정·`WP-06: PC fix` 커밋. 이어서 V-05는 `runbooks/pc-spike.md` |
| V-05 | 재구성·후처리·스파이크 1.1 | ⚪ 대기 | C-02 필요 |
| V-06 | Zone 통합·튜닝·패키징 | ⚪ 대기 | D-010 이후 |
| V-07 | WP-09 Zone Index·비동기 로드 검증 | 🟢 완료 | 2026-09-26 PC 세션(Claude Desktop 워크트리 `cool-sinoussi-82af80`, Fable 5.1), 브랜치 `pc/v07-verify-wp09`(PR → main). V-04를 건너뛰고 V-03 산출물(`L_ZoneTest`·합성 실내, 다른 워크트리에서 복사)로 실행. 빌드 통과(C++ 무수정), 자동화 **16/16 Success**, 런북 §1~§8·§10 ✅(§9 선택 미실행), 결과 표·스크린샷은 런북 §12·`docs/images/pc-verify-wp09-*.jpg`. **PC 발견**: ① 런북 §4 맵 사본(`duplicate_asset`→`load_level`)이 헤드리스에서 GC Fatal → Save-As 코드로 교체(§11 #35). ② HUD `render` 0.00 = 엔진 `GRenderThreadTime` 자체가 0(`stat unit` Draw·CSV `RenderThreadTime` 열도 같은 세션에서 0; 세션에 따라 0 또는 4.7 ms) → 소스 0/1/2 동일, 기본 1 유지. ③ §6 히치: 같은 경로 재생 async/sync 표(런북 §12), async가 나쁘지 않음. ④ pytest는 `PYTHONUTF8=1`로(CI 동일). 무인 드라이버는 V-03 스크래치 것을 재사용(세션 스크래치에만) |
| V-08 | 애니메이션 3안 PC 평가 | ⚪ 대기 | 런북 `runbooks/pc-verify-animation.md`(V-01 뒤, 독립): **§0 사용자가 GASP 라이선스 원문 확인**(Fab 리스팅·Fab EULA·UE EULA) → §1 GASP Create Project(저장소 밖)·플러그인·스켈레톤 기록 → §2 ① 기준선 녹화 S1~S8 + `csvprofile` → §3 ② GASP 로코모션 Migrate(`Content/Golmok_AnimEval/`, 브랜치 `pc/v08-animation`, 에셋 커밋 금지) → §4 ③(막힐 때만) → §5 사용자 채점 → §8 결과 |
| V-09 | WP-12 포토 모드 검증 | ⚪ 대기 | 런북 `runbooks/pc-verify-wp12.md`(WP-12 뒤): 진입/조절/촬영/복원, 배율별 VRAM, 벽·zone 밖 이탈 시도, 실내 촬영 |
| V-10 | WP-13 환경음 검증 | ⚪ 대기 | 런북 `runbooks/pc-verify-wp13.md`(WP-13 뒤): `audio_import` → 낮/밤·실내 크로스페이드·발소리 재질·착지, 볼륨 밸런스, 플레이스홀더면 실제 파일 교체 |

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
- **D-018 ②**: ① 제작 가설·18a는 승인. V-08/V-12 뒤 최종 룩·이름·외주 예산/계약·비공개 에셋 보관·필요 라이선스/출시 표시를 결정한다. [D-018](../DECISIONS.md), [WP-18](WP-18-characters.md). 모든 지출은② 이후.
- ~~D-013~D-017 게임 기능 제안~~ → 2026-09-25 **전부 승인, 권장 우선순위대로**(WP-12 → 17). 남은 결정: **사운드 라이브러리 유료 구매 여부**(WP-13이 후보·가격 정리 뒤), 유료 모션 팩(V-08 뒤)
- **애니메이션 에셋 라이선스**: GASP Fab 리스팅·Fab EULA·UE EULA 원문 확인(클라우드 403) → V-08 §0, D-002 기록
- night 프리셋 look-dev 조합(D-010 뒤, `design/lighting-night-lookdev.md` §4)
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
| 2026-09-25 | session_011Jdzkehx5EZRAV1kX7PnGD | Opus 5.5 | WP-10 | 🟢 research/09·V-08 런북·게임 기능 제안(D-013~D-017 제안)·night look-dev 메모, Epic 공식 문서 12건 원문 확인·열리지 않은 6건 [확인 필요]. 문서 전용, pytest 626 passed. PR #17 |
| 2026-09-25 | session_01NM6uvZaVMgq5SUSaduHD1Z | Fable 5.1 | 오케스트레이션 | WP-09/11/10 병합(PR #15/#16/#17), 병합 전 Opus 보완 리뷰 반영(WP-11 5건, WP-10 Chooser Experimental·UAF 정정), PC 카드 V-04/V-07/V-08. 사용자 승인 D-013~D-017 기록, WP-12·13 스펙, WP-14~17 등록 |
| 2026-09-26 | PC 세션(Claude Desktop 워크트리 cool-sinoussi-82af80) | Fable 5.1 | V-07 WP-09 PC 검증 | 🟢 빌드 무수정 통과, 자동화 16/16, 런북 §1~§8·§10 ✅(§9 미실행), render 소스 1 확정, 히치 표, 런북 §4 코드 수정 1건(#35). 다른 PC 세션(V-08)과 포그라운드 잠금으로 순서 조정. PR `pc/v07-verify-wp09` → main |
