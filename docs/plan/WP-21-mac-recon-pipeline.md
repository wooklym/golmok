# WP-21 — Mac 재구성 파이프라인 대체 (D-023)

상태: 🔵 진행 중(2026-11-27) · 담당: 로컬 Mac 오케스트레이터 세션 765a7a7d · 서브에이전트 Opus 5.5 ultracode(sfm-splat·objcap·splat-render·문서) · 의존: D-022 ④, D-023 · 검증: V-05(Mac판 재구성 절차 [`runbooks/mac-recon.md`](../runbooks/mac-recon.md))

## 목표
D-022로 이 Mac(Apple M5 Max·128 GB·macOS 27.2.1·arm64)이 유일한 개발 머신이 됐다. D-005/D-006의 재구성 도구(RealityScan·Postshot·XGRIDS LCC4Unreal)는 macOS를 지원하지 않는다. 소유자 지시(2026-11-27, 원문 "대체할 수 있는 것들은 대체해.")에 따라 **무료이고 라이선스를 확인할 수 있고 되돌릴 수 있는** Mac 대체 도구를 설치하고, 공개 데이터로 끝까지 돌려 보고, 기록한다. 돈이 드는 것(Metashape·클라우드 GPU), 소유자의 계정·약관 동의가 필요한 것(EgoBlur 모델·Fab), 확인할 수 없는 것은 소유자 항목으로 남긴다.

이 WP는 **파이프라인이 돈다는 것**만 보인다. RealityScan·Postshot과 품질이 같다는 주장은 하지 않는다. 품질 판정은 실촬영(C-02) 뒤 V-05와 D-010(예약 유지)이 한다.

## 배경
- D-022 ④가 선택지 (a) AWS g6e (b) Mac 네이티브 (c) Metashape (d) NVIDIA 머신 (e) 보류를 소유자 항목으로 남겼다. 소유자 지시로 (b) 중 무료로 되는 것을 지금 들인다(D-023).
- 조사: r5(파이프라인, URL 포함)·r4 §8(UE 플러그인 Mac 지원)·r1. 요지는 [mac-setup.md](../runbooks/mac-setup.md) §7에 있다.
- Windows 절차는 [pc-spike.md](../runbooks/pc-spike.md)·[recon-postprocess.md](../runbooks/recon-postprocess.md)다. 이 WP는 그 문서를 고치지 않고 Mac판 [mac-recon.md](../runbooks/mac-recon.md)를 더한다.
- 저장소 후처리 도구(`golmok-mesh`·`golmok-splat`·`golmok-align`·`golmok-zone`)는 순수 Python이라 Mac에서 그대로 돈다(WP-20 CI 통과).

## 설계 (확정, 2026-11-27, Opus)

### 1. 단계별 대체
| 단계 | Windows(D-005) | Mac 대체(D-023 후보) | 비고 |
|---|---|---|---|
| 블러 | `golmok-blur` CUDA | 같은 도구, CPU | 모델은 소유자 동의 뒤. MPS는 수동 지정만(`--device mps`, 결과 미검증) |
| SfM·포즈 | RealityScan 정렬 | COLMAP 4.2.1 conda-forge `cpu_lgpl` (CPU) | 증분 `mapper`, 비교용 `global_mapper`(GLOMAP) |
| 메시 | RealityScan(CUDA) | `golmok-objcap`(Apple Object Capture) | 후보. 약관 사실 확인 2건이 소유자 항목 |
| splat 학습 | Postshot Studio | Brush v0.3.0 (Metal) | COLMAP 모델 입력, 왜곡 없는 PINHOLE 필요 |
| splat 렌더(UE) | XGRIDS LCC4Unreal / Cesium | Cesium for Unreal 2.31.0 (Metal) | (c) LCC는 Mac 해당 없음 |
| 보조 | ffmpeg·exiftool(winget) | conda-forge ffmpeg 9.1 `lgpl`, exiftool 13.64 | Homebrew·sudo 불필요 |

### 2. 설치 원칙
- 저장소 밖 사용자 공간(`~/golmok-tools`)에만 설치한다. sudo·Homebrew·계정·약관 동의 없음. 공식 출처(GitHub 릴리스, conda-forge)에서 버전과 sha256을 고정한다.
- 스크립트 `tools/mac/install-recon-tools.sh`는 다시 돌려도 같은 결과를 내고, 매번 sha256을 다시 확인한다. env 안에 GPL 전용 conda 패키지가 있으면 실패한다(이중 라이선스는 허용, exiftool은 도구 자체라 예외).
- quarantine 제거·Gatekeeper 설정 변경은 하지 않는다.
- 데이터·PLY·모델·바이너리는 저장소에 넣지 않는다. 스모크 데이터와 결과는 `~/golmok_data/recon-smoke/<키>/`에 둔다.

### 3. 좌표
- splat과 메시가 같은 좌표계를 쓰려면 둘 다 **하나의 COLMAP 희소 모델**(`sparse/0` 또는 그 undistorted 사본)에서 나와야 한다. Brush는 COLMAP world 좌표를 그대로 쓴다(재중심·재스케일 없음, 측정 확인).
- COLMAP 좌표의 스케일·방향은 임의다. 미터·ENU 정합(`colmap model_aligner` 또는 `golmok-align`)은 희소 모델에서 **한 번**, 메시와 splat보다 먼저 한다 [미확인, 끝까지 해 보지 않음].
- Object Capture는 자기 좌표계를 따로 만든다. 같은 실행의 메시·포즈·점군끼리만 같은 좌표계다. COLMAP 모델과 맞추는 경로는 `golmok-objcap colmap`(실험) 하나뿐이고 끝까지 확인하지 않았다.

### 4. 하지 않는 것
- D-005/D-006 본문 수정, Windows 런북 수정·삭제.
- 지출(Metashape, 클라우드 GPU), 계정·약관 동의(EgoBlur 모델, Fab), 업로드(D-007).
- 품질 판정, D-010 결정.
- `.uproject`에 Cesium 활성화(핫스팟, 아래 "남은 작업"의 `[WP-21 hook]` 별도 커밋).
- D-002 금지 도구: Inria 3DGS, MASt3R/DUSt3R, OpenMVS, OpenSplat, gsplat-mps, Ultralytics.

## 산출물
- `tools/mac/install-recon-tools.sh`, `tools/mac/recon-smoke.sh`(bash 3.2), `tools/tests/test_mac_recon_scripts.py`(10개)
- `tools/mac/objcap/`(Swift 패키지 `golmok-objcap`, README), `tools/tests/test_mac_objcap.py`(10개)
- 런북 [`runbooks/mac-recon.md`](../runbooks/mac-recon.md)
- [DECISIONS](../DECISIONS.md) D-023, 공유 문서 갱신(STATUS·DEVELOPMENT-PLAN·ROADMAP·mac-setup §7·tools/README·docs/README)
- 이 문서

## 완료 기준
- 공개 데이터로 COLMAP → undistort → Brush → PLY → `golmok-splat inspect/clean/tiles`가 오류 없이 끝난다. **충족(2026-11-27)**
- `golmok-objcap run`이 공개 데이터로 메시·포즈·점군을 낸다. **충족**
- Brush PLY → `golmok-splat tiles` → Cesium for Unreal이 Metal에서 화면에 그린다. **충족(저장소 밖 프로젝트 사본)**
- 각 도구의 라이선스를 LICENSE 원문으로 확인하고 출처 URL을 D-023에 적는다. **충족(일부 의존성 [미확인] 표시)**
- 품질 동등성은 이 WP의 완료 기준이 아니다(V-05).

## 주의
- 스모크 데이터는 물체(탁자 위 불상, 드론으로 둘러싼 교회)다. 골목 안에서 바깥을 보는 촬영이 아니다.
- 측정 중 UE 패키징 작업이 함께 돌았다(load average 24–55). 시간은 상한 쪽으로 읽는다.
- Brush는 현재 폴더에 `./target/autotune`을 쓴다. 저장소 루트에서 돌리면 저장소에 파일이 생긴다(실제로 한 번 생겨서 지웠다). `recon-smoke.sh`는 작업 폴더로 이동해서 돌린다.
- Brush v0.3.0은 공증되지 않았다(ad-hoc 서명). curl로 받으면 quarantine이 붙지 않아 터미널에서 돈다. 브라우저로 받으면 Gatekeeper 창이 뜬다.

## 결과

### 21a (2026-11-27, 로컬 Mac 오케스트레이터 세션 765a7a7d · 서브에이전트 Opus 5.5, 브랜치 `claude/wp20-mac-dev-env`) — 🔵 진행 중
- 커밋은 오케스트레이터가 한다. 서브에이전트는 커밋·푸시·브랜치 전환을 하지 않았다.

**설치(`~/golmok-tools`, 새 접두 경로 재설치 58 s, 같은 패키지 집합)**

| 도구 | 버전·빌드 | 출처·sha256 | 라이선스 |
|---|---|---|---|
| micromamba | 2.10.0-0 | GitHub `mamba-org/micromamba-releases`, sha256 `c547639f…0c4c01`(공개 .sha256과 일치) | BSD-3-Clause |
| COLMAP | 4.2.1, conda-forge `cpu_lgpl_he9ae76f_9` ("without GPU support") | conda-forge | new BSD. lgpl 변형은 CGAL 끔·CHOLMOD 제거(Eigen simplicial) |
| ffmpeg | 9.1, conda-forge `lgpl_ha3d7a35_0` | conda-forge(`ffmpeg=9.1.0=lgpl*` 고정 — 기본 해석은 gpl 빌드를 골랐다) | `ffmpeg -L`: LGPL v3 이상 |
| exiftool | 13.64 | conda-forge | "same terms as Perl itself". env의 perl이 필요해서 env bin이 PATH 맨 앞이어야 한다(`env.sh`) |
| Brush | v0.3.0 `brush-app-aarch64-apple-darwin.tar.xz`(2025-09-14, 아직 최신) | GitHub 릴리스, sha256 `65b26313…a1048c`(공개 .sha256과 일치) | Apache-2.0(타르볼 LICENSE) |
| golmok-objcap | 저장소 Swift 패키지, Xcode 27.2, 패키지 의존성 없음 | `swift build -c release --scratch-path ~/golmok-tools/objcap/build` | Apple 프레임워크만 |
| Cesium for Unreal | 2.31.0 `CesiumForUnreal-58-v2.31.0.zip`(Mac universal dylib) | GitHub 릴리스, sha256 `6bab4f6e…cfe91` → `~/golmok-tools/ue-plugins/cesium-2.31.0/` | Apache-2.0(배포본 LICENSE) |

- 디스크: env 약 1.3 GB, 패키지 캐시 574 MB, Brush 144 MB, 다운로드 109 MB.

**스모크: COLMAP → Brush → golmok-splat**(AliceVision Buddha 67장 PNG 2736×1540, CC-BY-4.0; run2, `~/golmok_data/recon-smoke/sfm-splat/run2/summary.txt`)

| 단계 | 시간 | 메모리·결과 |
|---|---|---|
| `feature_extractor`(SIFT, CPU 18스레드) | 17 s(run1 부하 중 44 s) | 피크 21.4 GB, 장당 키포인트 평균 8,767(최대 16,396) |
| `exhaustive_matcher`(CPU) | 22 s | 2,211쌍(약 100쌍/s), 매칭 1,735, 검증 824 |
| `mapper`(증분) | 23 s | 67/67 등록, 모델 1, 점 35,901, 평균 트랙 4.70, 재투영 0.320 px |
| `global_mapper`(GLOMAP, `gp_use_gpu 0`) | 14 s | 67/67, 점 35,763, 0.321 px |
| `image_undistorter` | 6 s | PINHOLE 2731×1534, f 1855.75 |
| Brush 3,000스텝, max-res 1600, 8장마다 평가 | 69 s | footprint 2.9 GB, RSS 1.55 GB, 어댑터 "Apple M5 Max … backend: Metal", GPU 사용률 유휴 12 % → 최대 100 %, 학습 58·평가 9, PSNR 19.74, SSIM 0.867, PLY 11 MB, 49,214 splat, SH3 |
| Brush 30,000스텝(기본값, max-res 1920) | 926 s | footprint 3.5 GB, PSNR 21.25 / 21.16 / 20.77(10k/20k/30k), SSIM 0.894, 128,783 splat, PLY 30 MB |
| `golmok-splat inspect --json` / `clean --min-opacity 0.02` / `tiles` | 1 s 이하 | 개수·범위·불투명도·스케일 백분위·SH 3차, 타일 1개(`tileset.json` + `r.glb` 12 MB) |

- 돌리지 않은 것: `crop`(bbox나 zone manifest 필요), `transform`(행렬 필요). 저장소에 SPZ 경로는 없다.
- 좌표: splat 중앙값 (1.161, 0.246, 0.638), SfM 중앙값 (1.176, 0.214, 0.534). splat → 최근접 SfM 점 거리 중앙값 0.0049 단위(p90 0.035). PLY는 COLMAP world 좌표다.
- Brush PLY 헤더 "Vertical axis: y", `f_rest_*`를 이름의 사전순(f_rest_0, f_rest_1, f_rest_10, …)으로 쓴다. `golmok-splat`은 이름으로 읽으므로 문제없다. 열 순서로 읽는 리더는 SH를 틀리게 읽는다 [미확인: Cesium·다른 UE 임포터].
- COLMAP이 이 Mac에서 못 하는 것(설치 바이너리로 확인): `patch_match_stereo`("Dense stereo reconstruction requires CUDA"), `delaunay_mesher`("requires CGAL", lgpl 빌드). 조밀 MVS·Delaunay 메시가 없고, `poisson_mesher`는 조밀 점군이 없어 못 쓴다.

**스모크: golmok-objcap**(같은 Buddha, Tyrol 교회 드론 76장 JPEG 5472×3648 CC BY 4.0)

| 데이터 | detail | 시간 | 피크 메모리 | 정점 / 삼각형 | 텍스처 | 출력 |
|---|---|---|---|---|---|---|
| Buddha 67 × 4.2 MP | medium | 103 s | 4.9 GB | 25,003 / 50,000 | 3 × 4096² | OBJ 41.5 MB, USDZ 32.4 MB, 희소 점 18,105 |
| Tyrol 76 × 20 MP | medium | 671 s | 32.9 GB | 50,673 / 100,000 | 3 × 4096² | OBJ 68.5 MB, 희소 점 35,934 |
| Tyrol 76 × 20 MP | full | 645 s | 33.0 GB | 125,678 / 250,000 | 5 × 8192²(roughness PNG·displacement EXR 추가) | 421.7 MB |

- `limits`: `isSupported` true, `maximumNumberOfInputImages` 2000, `maximumInputImageDimension` 16384. macOS 26 intrinsics·왜곡 API 있음.
- 세 실행 모두 invalid·skipped 샘플, 자동 다운샘플, 이음 미완료 0. full이 medium보다 빨랐던 이유는 배경 부하 차이로 보인다 [미확인].
- Tyrol medium 메시 정점 중 교회 반경 25 m 안은 8 %다. detail별 삼각형 예산이 장면 전체에 퍼진다.
- 좌표(Buddha만 측정): transform은 camera→world, 카메라는 −Z를 보고 +Y가 위. 회전 오차 평균 0.05°, 중심 오차 0.11 %. K는 원본 픽셀 단위(초점 Buddha −0.4 %, Tyrol EXIF 대비 +0.8 %). GPS가 있는 Tyrol은 +Y 위·약 미터, EXIF 없는 Buddha는 미터가 아님. 같은 76장의 카메라가 medium↔full 실행 사이에 중앙값 0.116 단위(분산 폭의 약 0.1 %) 움직였다 — 메시와 포즈는 같은 실행에서 받는다.
- `golmok-objcap colmap`: PINHOLE·world→camera로 내보내고, Buddha에서 기준 포즈와 일치, 희소 점 96.9 %가 이미지 안에 투영. 렌즈 왜곡은 적용하지 않는다.
- 시각 품질은 보지 않았다.

**스모크: Cesium for Unreal on Metal**(저장소 밖 프로젝트 사본 `~/golmok_data/recon-smoke/splat-render/Golmok/`)
- 프로젝트 `Plugins/`에 넣으면 UBT가 소스에서 다시 빌드하고, Xcode 27 clang 21에서 `CesiumEditor/Private/IonQuickAddPanel.cpp:194` `-Werror,-Wuninitialized`로 멈춘다. 사본에 `#pragma clang diagnostic ignored "-Wuninitialized"` 한 줄을 넣자 `Build.sh`가 성공했다. CesiumRuntime은 수정 없이 컴파일됐다.
- 에디터 로드: 플러그인 마운트, 두 dylib 로드, `Cesium3DTileset`·`CesiumGeoreference`·`/CesiumForUnreal/GaussianSplatting/GaussianSplatSystem`, 셰이더 METAL_SM6/SM5.
- `-game -RenderOffscreen`: Niagara `GaussianSplatSystem` 컴파일, `CesiumGltfGaussianSplatComponent` 생성. 합성 splat 5만 개(20×10×5 m)가 조명 큐브와 함께 렌더되고 위치가 zone 매니페스트 `root.transform` → ECEF(37.562, 126.9272636, 50 m)와 일치했다.
- 전체 체인: Brush 30k PLY → `golmok-splat tiles --manifest tests/fixtures/zones/z_synthetic_002/v1/manifest.json` → `r.glb` 32 MB → Cesium on Metal. 불상 머리·받침판·ArUco 마커가 알아볼 수 있게 보이고 색이 정상이다. 정리·정렬을 안 해서 COLMAP 좌표 그대로 기울어져 있고 floater가 보인다(예상된 현상).
- 첫 스크린샷이 검었던 원인은 카메라 피치 −90°였다. 고정 `CameraActor`로 해결.
- Cesium 로드 때마다 `LogClass: Error: EnumProperty FCesiumMetadataPropertyStatisticValue::Semantic is not initialized properly`가 찍힌다.

**검사(tools/.venv, 2026-11-27 서브에이전트 보고)**
- `bash -n` 두 스크립트 통과, 새 테스트 20개 통과, `check_repo.py` OK, `ruff format --check .` 통과.
- `ruff check .`: E501 2건 — `tools/tests/test_mac_objcap.py:3`(WP-21 새 파일), `tools/tests/test_ue_mac_scripts.py:352`(WP-20, HEAD 9f3b64d). 커밋 전에 고친다.
- `pytest -q`: 1921 통과·3 건너뜀·5 실패. 4건은 `test_ue_mac_scripts.py`의 add-gasp 테스트가 이 Mac에서 실행 중인 Unreal 편집기를 보고 "close the Unreal Editor first"로 멈춘 것(환경 의존, 테스트 가드 문제), 1건은 `test_mac_objcap.py::test_commands_and_options_in_usage_and_readme`(sfm-splat 보고 시점; objcap 보고에서는 통과).
- 문서 작성 뒤 재실행(2026-11-27, 같은 venv): `pytest -q` **1926 통과·3 건너뜀·실패 0**, `check_repo.py` OK, `ruff format --check .` 통과, `ruff check .`는 E501 1건(`tools/tests/test_ue_mac_scripts.py:352`, WP-20 파일)만 남았다. add-gasp 테스트 4건은 이번에는 통과했다(편집기 실행 여부에 따라 달라지는 환경 의존 — 가드 정리는 후속).
- 사고 1건(해결): 첫 스모크를 저장소 루트에서 돌려 Brush가 `target/`(autotune .json.log 5개)를 만들었다. 지웠고 스크립트가 작업 폴더로 이동하도록 고쳤다.

**부수 발견(D-007 관련, 후속)**
- UE CrashReportClient가 크래시 리포트를 Epic datarouter로 자동 업로드한다(`CrashReportClient.log`의 "All uploads done"). 로그·minidump에 로컬 경로가 들어간다. 촬영 이미지는 아니지만 프로젝트 설정에서 크래시 업로드를 끄는 것을 권한다(`Config/Default*.ini`는 핫스팟 — `[WP-21 hook]` 별도 커밋).
- 측정 시점에 CrashReportClient(pid 78718)가 저장소 프로젝트 Mac Cook 크래시(pid 65773, `ShaderCompilerEditor.cpp:606` Fatal) 뒤 55분 넘게 CPU 약 99 %로 멈춰 있었다. 백그라운드 패키징 세션이 확인한다.
- `-ExecutePythonScript`로 띄운 편집기가 종료 때 Slate/ICU 쪽 malloc abort로 크래시한다(결과 파일은 그 전에 써짐). 연습 레벨 `duplicate_asset` 복제본은 로드 때 GC Fatal이 나서 쓰지 않는다.

**남은 작업(WP-21 후속)**
1. `Golmok.uproject`에 CesiumForUnreal 활성화와 플러그인 배치 — `[WP-21 hook]` 별도 커밋. `IonQuickAddPanel.cpp` 처리 방식(플러그인 로컬 패치 / Engine `Plugins/Marketplace` 프리빌트 설치 / 업스트림 이슈)과 서드파티 소스를 저장소에 둘지 정한다.
2. **Mac 패키지(쿡) 빌드에서 Cesium splat이 보이는지** 확인(출시 가능성을 가르는 항목).
3. Cesium 로드 오류 줄이 `Golmok.*` 자동화(`test.sh`)를 실패로 만드는지 확인.
4. COLMAP 희소 모델 미터·ENU 정합 → 메시·splat 좌표 공유를 끝까지 해 본다.
5. 크래시 업로드 끄기(D-007).
6. E501(`test_ue_mac_scripts.py:352`)·~~add-gasp 테스트의 편집기 실행 가드(환경 의존) 정리~~(2026-11-28 J-06 [#143](https://github.com/wooklym/golmok/pull/143) `a37b4ef`로 닫음: `gasp_env`가 가짜 `ps` 스텁을 써서 떠 있는 편집기와 상관없이 통과 — 더미 편집기 프로세스로 6 failed 재현 → 수정 뒤 더미 유무 모두 8 passed). E501 절반은 J-07([jaehwan-tasks](jaehwan-tasks.md)) 확인 대기.
7. 실촬영(C-02) 뒤 V-05로 품질·fps 판정, D-010.
