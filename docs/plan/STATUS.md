# 진행 상태 보드 (plan/STATUS)

갱신 규칙: 각 세션이 시작·종료 시 자기 행을 고친다. 상태 기호:
⚪ 대기 · 🔵 진행 중 · 🟡 코드 완료·PC 검증 대기 · 🟢 완료 · 🔴 막힘 · ⏸ 보류

마지막 갱신: 2026-09-24 (WP-06 세션 시작 🔵)

## 트랙 1A — 클라우드 코드 (순차)

| WP | 이름 | 상태 | 세션 | 인계 메모 |
|---|---|---|---|---|
| WP-01 | 저장소 기반·CI | 🟢 완료 | session_01QwUxcoWCFmtiJhq3ZWByEJ (Opus) | CI 초록(ubuntu 3.11/3.12, windows 3.12, repo-check, tiles-validate). 커밋 전 `cd tools && ruff check . && ruff format --check . && pytest -q && python scripts/check_repo.py` |
| WP-02 | Zone 데이터 모델·CLI `golmok-zone` | 🟢 완료 | session_014zvy99LzAuVhnHYFtUYfVz (Opus) | 스펙 `docs/spec/zone-manifest.md`(필드·좌표·UE 매핑·수치 예제 표). transform은 **row-major**, UE Yaw = −yaw_deg, ENU→UE `diag(100,−100,100)`. 픽스처 `tools/tests/fixtures/zones/z_synthetic_001/v1/`(WP-04가 복사). 베이스맵 origin 높이는 `--geoid-offset` 없으면 정표고(WP-07 주의) |
| WP-03 | 재구성 후처리 `golmok-mesh` / `golmok-splat` | 🟢 완료 | session_014zvy99LzAuVhnHYFtUYfVz (Opus) | 청크 = `visual/<id>.obj`+MTL(Z-up, UDIM 유지), 충돌·blocker GLB = glTF Y-up. open3d 제외(D-002). splat 3D Tiles = `KHR_gaussian_splatting`(검증기 0.6.1은 확장 속성 이름만 오류). PC 절차 `runbooks/recon-postprocess.md` — [미확인] 항목은 V-05에서 확인 **병합 전 적대적 리뷰(Fable 리뷰 6관점 → Opus 검증 → Opus 수정) 반영: 확정 결함 17건 수정, 테스트 180 passed. 청크 id 규약이 zone 원점 기준 절대 셀 `c_e000_n000`로 바뀜(WP-04·06 주의)** |
| WP-04 | UE C++ 1: Geo·Zone | 🟡 코드 완료·PC 검증 대기 | session_01GGmw3pPHLp4Wk5Us9243AL (Fable 5.1 ultracode, 검증 Opus) | `Geo/`(순수 수학 헤더 + g++ 교차검증, 원점 액터, GeoSubsystem) · `Zones/`(manifest 파서, `AGolmokZone`, `UGolmokZoneSubsystem`) · `synthetic_zone.py` · 런북 `runbooks/pc-verify-wp04.md`(불확실 API 표 §6). PR #7. **PC(V-03)**: 빌드 → `z.run()` → PIE 체크 (1)~(6). WP-05 훅 `SpawnPortals/GetPortalWorldTransform/RequestLoad`, WP-06은 `synthetic_zone.find_or_spawn_*` 재사용. Zone Index 기반 발견은 미구현(레벨 배치 액터만) |
| WP-05 | UE C++ 2: 포털·조명·디버그 | 🟡 코드 완료·PC 검증 대기 | session_01W4S1qYJPhQaziYbJMvAXMo (Fable 5.1 ultracode, 검증 Opus) | `Lighting/`(프리셋 JSON 단일 소스·`AGolmokTimeOfDay`) · `Portals/`(`AGolmokPortal`, 스트리밍 2경로 ini 선택) · `Debug/`(HUD·통계·경로 녹화/재생·CSV·스크린샷, 순수 헤더 g++ 교차검증) · `Player/GolmokPlayerController` · 합성 실내 `z_synthetic_001_interior` + `synthetic_zone.run(interior=True)` · 런북 `runbooks/pc-verify-wp05.md`(§11 불확실 API 64행). PR #10. **PC(V-03)**: WP-04 런북 뒤에 실행, `test.ps1`로 UE 테스트 10개 먼저. WP-06: 서브레벨은 레벨 좌표·`L_<zone_id>` 규약, 포털은 C++가 스폰(Python 배치 금지), 조명 액터 태그 `GolmokLighting` |
| WP-06 | UE Python 에디터 자동화 2차 | 🔵 진행 중 | session_011qpTa7U7onDnW7L9jNSgwA (Fable 5.1 ultracode, 검증 Opus 5.5) | 시작 2026-09-24. 설계 패널 → `_pure.py`/`zone_import.py`/`interior_setup.py`/`spike_runner.py`/`make_synthetic_zone.py` → 적대적 검증 → 런북 2개 |
| WP-07 | 정합·검수 `golmok-align` | 🟢 완료(합성 검증) | session_01Cgm7f6oD6xSMpZ5jszj8Xi (Fable 5.1) | `golmok-align run/compare/check-blur`. GPS prior(level Umeyama+RANSAC) → 벽 ICP(dof 4/6) → 지면 ICP(수직만) → manifest transform/origin/quality 갱신 + align_report.md. open3d 대신 numpy/scipy(리눅스 CI에 libEGL 없음). 합성: 2°·1.4 m 교란을 3 cm 이내 복원. **실 Zone 검증은 V-05.** collision.glb 축 규약은 `--mesh-axes`로 맞춘다(WP-03 결정 대기) |
| WP-08 | (선택) 웹 검수 뷰어 | 🟢 완료 | session_01Cgm7f6oD6xSMpZ5jszj8Xi (Fable 5.1) | `golmok-viewer`(CesiumJS 1.145, ion 없음) + `tools/viewer` + Playwright 스모크(`npm test`, 합성 베이스맵 18타일). Zone manifest 오버레이(footprint·청크 bbox·포털·blockers, `?zone=…/manifest.json`) 포함. 충돌 메시 표시는 WP-03 산출물 나오면 추가 |

## 트랙 1B — PC 검증 (PC Claude 세션)

| V | 내용 | 상태 | 메모 |
|---|---|---|---|
| V-01 | PC 셋업·L_Dev·리허설 점검 (`runbooks/pc-setup.md` §0~4) | 🔵 진행 중 | §0~2 🟢(2026-09-24): UE 5.8.3·VS 2026 빌드 무수정 통과, L_Dev·마네킹 PIE, 자동 테스트 `Golmok.Player.Movement`(`tools/ue/test.ps1`) 통과, pytest·CUDA OK. 결과 ROADMAP 1.0a~1.0d. §3 리허설은 C-01 사진과 EgoBlur 모델(사용자 라이선스 동의) 대기. **push는 이 PC의 GitHub 로그인 필요**(사용자). 클라우드 인계(WP-06 필독): ① `viewpoints.capture`가 스크린샷을 빠뜨리거나 **다른 시점 이름으로 저장**하던 버그 수정(파일 기록 대기, missing 보고, 게임 뷰). 단 **에디터 창이 백그라운드에 오래 있으면 뷰포트를 그리지 않아 스크린샷이 안 나온다**("백그라운드 CPU 절약" 꺼도 같음) → `spike_runner`의 무인 캡처는 PIE/`-game`의 `HighResShot`으로 설계할 것. ② `golmok-perf`가 실제 5.8 CSV에서 죽던 문제(긴 필드)와 맵 로딩 프레임이 평균에 섞이던 문제 수정, `-game` CSV 위치는 `%LOCALAPPDATA%\UnrealEngine\5.8\Saved\Profiling\CSV`. 기준선(빈 L_Dev 1080p 158 fps / 1440p 128 fps)은 `research/08`. ③ `golmok.lighting` 4개 프리셋 에디터 검증 ✅. ④ `check_repo.py`에 병합 충돌 표시 검사 추가 |
| V-02 | 베이스맵 실데이터 (`pc-setup.md` §5) | 🟢 완료 | 연남동 반경 1 km: 건물 9,447동, 64타일, **5 m DEM**(수치지형도 등고선·표고점, `contour-dem`). UE `L_Basemap_Yeonnam`: fit error ≈0, 북쪽 −Y, 파사드 패턴, PIE 보행 OK, 1080p 169 fps(1% low 141), 충돌 추적 169/169(지형 Nanite 끔). 신규 `golmok-basemap georef-ortho`(좌표 없는 NGII 정사영상), `M_BasemapTerrain`. 결과·근거: ROADMAP 1.2, D-012 |
| V-03 | WP-04/05 빌드·PIE 검증 | ⚪ 대기 | 런북 2개 준비됨: `runbooks/pc-verify-wp04.md` → `runbooks/pc-verify-wp05.md`(순서대로; WP-05 런북 §2는 WP-04 §2의 `z.run()` 결과를 전제). 헤드리스 `test.ps1 -Filter Golmok. -SetupDevLevel`로 자동화 테스트 11개(WP-01 1 + WP-05 10) 먼저 |
| V-04 | WP-06 에디터 Python 검증 | ⚪ 대기 | |
| V-05 | 재구성·후처리·스파이크 1.1 | ⚪ 대기 | C-02 필요 |
| V-06 | Zone 통합·튜닝·패키징 | ⚪ 대기 | D-010 이후 |

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
| 2026-09-25 | session_01W4S1qYJPhQaziYbJMvAXMo | Fable 5.1 ultracode (검증 Opus) | WP-05 | 🟡 설계 패널 3안→심판 2→종합, Lighting·Portals·Debug·Player C++ + 합성 실내, 적대적 리뷰 3라운드(원시 25→11→1, 확정 33·반박 4, 전부 반영), 테스트 +95(전체 323 passed, 3 skipped), UE 자동화 10개, 런북. PR #10 |
