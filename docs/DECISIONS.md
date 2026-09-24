# 결정 기록 (Decision Log)

형식: `D-번호 | 상태 | 날짜`. 상태는 **승인**, **제안**(승인 대기), **확인 요청**, **보류**, **폐기** 중 하나다.
근거는 `docs/research/`와 `docs/ARCHITECTURE.md`에 있다.

## 최우선 원칙 (2026-09-24 승인)

> **게임 퀄리티가 최우선이다.** 개발 난이도와 비용보다 퀄리티를 우선한다.
> 선택지가 갈리면 "최종 화면 품질이 더 높은 쪽"을 기본값으로 삼는다.

---

### D-001 | 승인 | 2026-09-24 — Google Photorealistic 3D Tiles를 쓰지 않는다
- 서울에는 3D 메시가 없다. 약관상 캐싱, 추출, 파생, 오프라인 사용, Google 외 지도와의 혼용이 모두 금지된다(01 문서).

### D-002 | 승인 | 2026-09-24 — 비상업 라이선스 코드와 가중치는 제품 파이프라인에 넣지 않는다
- 제외 대상: Inria 3DGS 계열, CityGaussian, PGSR, MASt3R/DUSt3R, Pi3, SuperPoint/SuperGlue, InsightFace 가중치.
- AGPL 도구(Ultralytics, OpenMVS, OpenSplat)는 서버 파이프라인에서 쓰지 않는다.
- 새 의존성을 추가할 때는 LICENSE 원문을 확인하고 이 문서에 기록한다.
- 상용 툴(RealityScan, Postshot, 서드파티 UE 플러그인)은 **EULA와 배포 조건**을 확인하고 기록한다.
- 촬영·베이스맵 도구 공통 의존성(`tools/pyproject.toml` 기본·`basemap` extra, 게임 패키지에는 들어가지 않음): **opencv-python** 5.0 — 래퍼 MIT + OpenCV 바이너리 Apache-2.0(동봉 서드파티 중 LGPL 항목은 macOS 휠의 libgnutls 등에만 해당; Windows/Linux 휠은 libvpx·libpng·zlib 등 BSD/zlib 계열) [확인: wheel 동봉 LICENSE.txt·LICENSE-3RD-PARTY.txt 원문, https://github.com/opencv/opencv/blob/4.x/LICENSE], **numpy** 2.4 — BSD-3-Clause(+0BSD/MIT/Zlib/CC0 부속) [확인: wheel `License-Expression`, https://github.com/numpy/numpy/blob/main/LICENSE.txt], **Pillow** 12 — MIT-CMU(HPND) [확인: wheel `License-Expression`, https://github.com/python-pillow/Pillow/blob/main/LICENSE], **exifread** 3.5 — BSD-3-Clause, **rasterio** 1.4 — BSD-3-Clause, **pyshp** 3.1 — MIT, **mapbox-earcut** 2.1 — ISC, **piexif** 1.1 — MIT, **pygltflib** 1.16 — MIT(개발 전용) [확인: 각 wheel `*.dist-info/licenses/` 원문]. 2026-09-25 확인(V-02에서 `basemap/ngii.py`가 OpenCV 템플릿 매칭을 새로 쓰면서 기록).
- 로컬 데이터 도구 `golmok-zone`(WP-02, `zone` extra — 게임 패키지에는 들어가지 않음): **jsonschema** 4.26 — MIT, 의존 **referencing**·**jsonschema-specifications**·**rpds-py** — MIT(모두 Julian Berman), **attrs** — MIT [확인: 각 wheel의 `*.dist-info/licenses/` 원문, https://github.com/python-jsonschema/jsonschema/blob/main/COPYING]. `basemap`과 같이 쓰는 **pyproj** 3.7 — MIT(동봉 PROJ — MIT/X 계열), **shapely** 2.1 — BSD-3-Clause(동봉 GEOS — **LGPL-2.1**, 동적 라이브러리로 링크돼 도구로 쓰는 데 제약 없음. 게임에 동봉하지 않는다) [확인: wheel 동봉 LICENSE·LICENSE_proj·LICENSE_GEOS 원문]. 2026-09-24 확인.
- 로컬 정합 도구 `golmok-align`(WP-07, `align` extra — 게임 패키지에는 들어가지 않음): **trimesh** 5.1 — MIT [확인: wheel 동봉 LICENSE.md 원문, https://github.com/mikedh/trimesh/blob/main/LICENSE.md], **scipy** 1.17 — BSD-3-Clause [확인: wheel 동봉 LICENSE.txt, https://github.com/scipy/scipy/blob/main/LICENSE.txt]. **open3d(MIT)는 쓰지 않는다**: 리눅스 CI 러너에 libEGL이 없어 import가 실패하므로 ICP를 numpy/scipy로 직접 구현했다. 2026-09-24 확인.
- 개발·CI 전용 도구(제품에 포함되지 않음, WP-01): **ruff** — MIT [확인: https://github.com/astral-sh/ruff/blob/main/LICENSE], **3d-tiles-validator**(CesiumGS, `npx`로 CI에서만 실행) — Apache-2.0 [확인: https://github.com/CesiumGS/3d-tiles-validator/blob/main/LICENSE.md]. 2026-09-24 원문 확인.

### D-003 | 승인 | 2026-09-24 — 엔진: **Unreal Engine 5 + Cesium for Unreal**
- **이유**: Lumen, Nanite, 캐릭터 애니메이션, 포스트프로세스 덕분에 비주얼 상한이 웹 스택보다 압도적이다(퀄리티 최우선 원칙).
- **타깃 플랫폼**: 1차는 **고사양 PC(Windows)**다. 모바일은 Phase 2 이후에 재평가한다.
- **버전 고정**: **UE 5.8.3(Launcher 바이너리) + Cesium for Unreal 2.29.x**(07 문서).
  - 5.8은 UE5의 마지막 예정 메이저다.
  - XGRIDS 플러그인이 바이너리라서 엔진 소스는 수정하지 않는다.
  - 버전 업그레이드는 별도 결정으로 다룬다.
- **개발 방식**
  - 게임 로직은 **C++**(프로젝트 모듈)로 쓴다.
  - 에디터 자동화(임포트, 배치, 머티리얼 설정, 빌드)는 **Unreal Python**으로 쓴다.
  - **Blueprint는 최소화**한다. 애니메이션 BP나 UI 바인딩처럼 불가피한 곳에만 쓰고, 로직은 C++로 올린다.
  - 바이너리 에셋은 **Git LFS**로 관리한다. `.uasset`과 `.umap`은 lockable로 지정하고, UEGitPlugin을 쓴다.
  - 원본 사진·영상, RealityScan 프로젝트, .ply 원본은 git에 넣지 않는다.
- **스파이크 1.0(환경 표현 방식 확정)**: 같은 골목 데이터로 아래 세 방식을 비교한다.
  - (a) RealityScan 메시 → Nanite + Lumen
  - (b) Gaussian splat → Cesium for Unreal splat LOD
  - (c) splat → 서드파티 UE 플러그인(1순위 XGRIDS LCC4Unreal, 2순위 Volinga)
  - 평가 기준: 시각 품질, 캐릭터 그림자·조명 통합, 이음새, fps. 상세 기준은 ROADMAP 1.0.
  - 사전 조사로 예상되는 결과(07 문서):
    - (b)는 Cesium splat 머티리얼이 **Unlit/Translucent**라서 캐릭터 그림자를 받지 못한다. 근경에는 불리할 것이다.
    - (c)의 XGRIDS는 **Lit + ProxyMesh**로 그림자를 받는다.
    - (a)는 출시된 스캔 기반 게임들이 쓰는 검증된 기준선이다.
    - 따라서 **"(a) 메시 기본 + (c) splat 부분 보강" 하이브리드**가 유력하다. 최종 판단은 측정 후에 한다.
- **웹 스택(Three.js/CesiumJS)은 내부 검수 뷰어 용도로만 쓴다.**
- 03 문서의 웹 추천안은 이 결정으로 대체됐다.

### D-004 | 승인 | 2026-09-24 — 베이스맵: GIS건물통합정보 LOD1 + NGII DEM·정사영상, S-Map 병행
- **역할 한정**: LOD1 박스는 **파일럿 지역 "바깥 배경"으로만** 쓴다. **플레이 구역은 전부 실촬영으로 채운다.**
- **박스 느낌 숨기기**
  - 층수와 용도에 따른 **절차적 파사드**(창, 층 띠, 1층 상가 패턴)를 Unreal 머티리얼로 만든다. World-aligned이고 층고를 기준으로 한다.
  - 원경 안개(Exponential Height Fog), 대기 산란, 조명(역광·실루엣 위주 구도)을 쓴다.
  - 플레이 구역 경계에서 시선 방향으로 보이는 배경 블록은 우선순위를 높여 디테일을 올린다.
- **B안(S-Map)**: 병행한다. 문의 초안은 `docs/outreach/smap-inquiry-draft.md`에 있고 **사용자가 직접 발송**한다. 협의가 진행되면 계약 검토는 D-009에 따라 그 시점에 자문한다.
- 출처 표시(공공누리 1유형)는 크레딧에 넣는다.

### D-005 | 승인(수정) | 2026-09-24 — 재구성 파이프라인
- **MVP(Phase 1, 사용자가 직접 처리)**
  - 메시: **RealityScan 2.x**. 연매출 $1M 미만 무료이며, 약관 원문은 설치 시 확인한다.
  - splat 학습: **Postshot**. 상업 사용과 PLY 내보내기에는 Indie 이상, 4K 초과 이미지와 CLI에는 **Studio**가 필요하다. **최고 품질 설정을 위해 Studio**로 한다.
  - Postshot UE 플러그인은 게임 배포가 불가하므로 **쓰지 않는다.** Postshot은 학습과 내보내기 전용이다.
  - 카메라 포즈는 RealityScan 정렬 결과를 COLMAP/XMP로 내보내 Postshot에 넣는다. 이렇게 하면 **메시와 splat이 같은 좌표계**를 공유한다.
- **Phase 2**: 서버 자동화 파이프라인(COLMAP + gsplat, D-002 기준 준수)을 구축한다.
- **보관**: 원본 사진(RAW + JPG), 원본 영상, RealityScan 프로젝트, **학습 결과 .ply 원본**을 모두 보관한다. 외장 디스크 2곳과 비공개 버킷에 두고, git에는 넣지 않는다.
- **개인정보 처리**: RealityScan/Postshot에 넣기 전에 얼굴·번호판 블러를 적용한다(05 문서). MVP에서는 로컬 스크립트로 처리한다(EgoBlur, Apache 2.0).

### D-006 | 승인(수정 2) | 2026-09-24 — 연산 환경: **사용자의 Windows PC를 주 처리 머신으로 쓴다**
- **원칙**: 학습 해상도와 반복 수를 줄이지 않는다.
  - Postshot: `max-image-size 0`(원본), SH 3, AA 켬, 수렴할 때까지 스텝을 늘린다.
  - RealityScan: High detail, 원본 해상도.
- **결정(2026-09-24)**: RealityScan, Postshot, UE 개발을 **사용자의 Windows PC**에서 돌린다.
  - Postshot은 Windows + NVIDIA 전용이다. 로컬 GUI 실시간 프리뷰가 품질 조정에 가장 유리하다.
  - **사양 확인 대기**: CPU, RAM, GPU(모델·VRAM), 저장공간. 권장 사양은 07 문서 §2이며, Ryzen 9 9950X / 128GB / RTX 5090 32GB다.
    - Postshot은 **NVIDIA RTX 2060 이상**(CC 7.5)이 필수다.
    - 사양이 권장보다 낮으면 병목에 따라 결정한다. 부품 업그레이드(GPU나 RAM)와 클라우드 보조 중에서 고른다.
- **사용자 PC 현재 사양(2026-09-24 확인)**
  - CPU: Ryzen 5 7500F(6코어)
  - RAM: 32GB DDR5-5200
  - GPU: **RTX 5060 8GB**
  - 저장공간: SSD 1TB(약 740GB 여유)
  - OS: Windows 11 Home
  - 메인보드: A620 계열로 보임(사진에서 잘림, 확인 필요)

  | 작업 | 현재 사양으로 | 판단 |
  |---|---|---|
  | UE 5.8 개발(C++, 에디터) | Epic 최소 요구(32GB, DX12, RTX)를 충족한다. 셰이더·C++ 컴파일은 6코어라 느리다 | **가능** |
  | UE 고품질 골목(Nanite + Lumen + 8K VT) | VRAM 8GB가 병목이다. 편집과 1080p~1440p 확인은 가능하지만, 4K Lumen 품질 검증은 어렵다 | **제한적** |
  | RealityScan(사진 약 1,300장) | CUDA 사용 가능. RAM 32GB는 약 4,000장까지 권장 범위다[2차]. CPU 6코어라 느리다 | **가능(느림)** |
  | **Postshot 최고 품질**(원본 해상도, 큰 splat 예산) | 8GB VRAM으로는 이미지 크기나 splat 수를 줄여야 한다 → **품질 원칙과 충돌** | **부족** |
  | 원본 보관 | 촬영 1회에 100~150GB, RealityScan 캐시와 UE DDC까지 더하면 1TB로는 몇 번 못 버틴다 | **부족** |

  - **업그레이드 우선순위**(퀄리티 기준):
    1. **GPU**: RTX 5090 32GB. 차선은 16GB급(5080/5070 Ti). 5090은 대용량 파워와 케이스 공간이 필요하므로 **파워 용량과 케이스 길이를 먼저 확인**한다.
    2. **저장장치**: NVMe 2TB 이상 추가 + 백업용 외장 디스크.
    3. **RAM**: 64GB 이상. A620 보드는 슬롯이 2개인 경우가 많아 **2×32GB 이상 키트로 교체**하게 된다.
    4. CPU: 가장 후순위다. AM5라서 소켓은 같지만 A620 보드의 전원부 한계 때문에 고성능 CPU는 보드 확인이 먼저다.
  - **업그레이드 전 운영안**:
    - RealityScan, UE 개발, Postshot 미리보기는 **로컬**에서 한다.
    - **Postshot 최종 학습(원본 해상도)은 AWS g6e Windows(L40S 48GB, 서울)**에서 한다.
    - RTX 5060 PC는 **저사양 기준 측정기**로 활용한다(스파이크 fps 측정에서 하한선 역할).
- **클라우드는 보조**로 쓴다(대량·병렬 처리, 또는 로컬 VRAM 부족 시).
  - Windows가 필요한 작업(Postshot, RealityScan): **AWS g6e Windows, 서울 리전**
  - Linux 작업(Phase 2 gsplat, 변환): **RunPod**. RunPod은 Linux 컨테이너만 제공하므로 Postshot은 돌릴 수 없다.
- **작업 방식**: 이 클라우드 세션은 사용자 PC에 접근할 수 없다. UE 빌드, RealityScan/Postshot 실행, 로컬 스크립트 작업은 **사용자 PC에서 도는 Claude Code 세션**(Claude Desktop 앱, 또는 프로젝트 폴더에서 `claude remote-control`)으로 진행한다. 문서와 설계 작업은 어느 세션에서 해도 된다.

### D-007 | 승인 | 2026-09-24 — 호스팅
- MVP는 비공개로 운영하고, 공개할 때는 국내 리전을 쓴다.
- 비공개 원칙에 따라, 원본(얼굴·번호판 포함)이나 블러 처리 전 데이터를 **외부 서비스(Cesium ion 등)에 올리지 않는다.** 스파이크 (b)는 블러 처리한 결과 또는 로컬 변환기로만 진행한다.

### D-008 | 승인(수정) | 2026-09-24 — 지역: **"가는 곳마다 찍어 올리는" Zone 누적 방식 + MVP 홈 Zone 1곳**
- **사용자 방침**: 한 동네로 고정하지 않고 **사용자가 가는 곳마다 골목을 찍어 올린다.** 후보는 연남동, 한남동, 신사동 등이다.
- **설계상 문제 없음**: ARCHITECTURE의 Zone 모델은 원래 Zone을 서로 독립된 단위(각자 좌표와 매니페스트를 가짐)로 설계했다. 흩어진 골목들이 서울 지도 위에 하나씩 쌓이는 구조가 곧 최종 비전(크라우드소싱)의 축소판이다.
- **MVP 목표를 위해 "홈 Zone" 1곳은 정한다.** 조건은 다음과 같다.
  - 골목 + **실내 동의 가능한 가게** + 주변 배경(LOD1)이 한곳에 모여 있어야 한다.
  - 스파이크(1.1)와 MVP 완성도 작업은 홈 Zone에 집중한다.
  - 다른 곳에서 찍은 골목은 **Zone 백로그**로 쌓는다. 원본을 보관하고 처리 대기열에 넣었다가, 파이프라인이 안정되면 차례로 처리한다.
- **홈 Zone 후보 평가**(06 문서 §추가 후보):
  - **연남동**: 추천 유지.
  - **신사동**: 가로수길 본선은 성수와 같은 브랜드·변화 리스크가 있다. 이면(세로수길 등)은 가능하다.
  - **한남동**: 대통령 관저(2026-09 현재 임시 사용 중 [2차]), 공관촌, 대사관이 밀집해 있다. → **홈 Zone으로는 비추천.** 관저·공관 일대를 벗어난 골목은 촬영 전 체크(가이드 §0)를 거쳐 백로그로 넣는 것은 가능하다.
- **모든 촬영**은 가이드 #1 §0의 "촬영 전 30초 체크"를 거친다.
- 홈 Zone은 첫 촬영물 중에서 사용자와 함께 고른다.

### D-009 | 승인 | 2026-09-24 — 법률 자문
- 비공개 MVP까지는 자문 없이 진행한다. 외부 공개 전에 05 문서의 자문 항목 6개를 일괄로 자문받는다.
- **S-Map 협의가 진행되면 계약 검토는 그 시점에 자문받는다.**
- 추가 항목: **XGRIDS LCC 플러그인 등 서드파티 런타임 플러그인의 게임 배포 라이선스**를 확인한다(스파이크 채택 후).

### D-010 | 예약 | — 환경 표현 방식 (스파이크 1.1 결과로 결정)

### D-011 | 승인 | 2026-09-24 — 촬영 장비: **iPhone 17 Pro**
- **사진**: 기본 카메라 앱, **메인 1x(24mm), 48MP ProRAW Max**, AE/AF 잠금, 매크로 자동 전환 끔. 수동 셔터 앱은 RAW 해상도가 12MP로 제한되는 경우가 있어 해상도를 우선했다 [2차].
- **영상**: Blackmagic Camera 앱, 4K60, 셔터 1/250~1/500, ISO·WB·초점 고정, HEVC 10-bit.
- 초광각과 망원은 쓰지 않는다.
- **첫 촬영 전 리허설**(가이드 §4-C)로 셔터 속도를 확인한다. 흐린 아침에 셔터가 느리게 잡히면 설정을 다시 정한다.
- PC 전송 시 "원본 유지" 설정을 확인한다.

### D-012 | 승인(기술 결정, 원칙 적용) | 2026-09-24 — 배경 베이스맵을 **UE 정적 메시(Nanite)로 임포트**한다
- **내용**: `golmok-basemap`이 만든 GLB 타일을 UE 정적 메시로 임포트한다. 건물은 Nanite + 절차적 파사드 머티리얼, 지형은 정사영상 텍스처를 쓴다. Cesium3DTileset 런타임 스트리밍은 쓰지 않는다. 같은 출력에 `tileset.json`(3D Tiles 1.1)도 함께 만들어 두어, 웹 검수 뷰어와 Cesium에서도 쓸 수 있게 한다.
- **이유(퀄리티 우선)**:
  - 런타임에 생성되는 타일셋 메시에는 Nanite와 메시 디스턴스 필드가 없어 Lumen 소프트웨어 GI 품질이 떨어진다[추정, UE 일반 동작].
  - 커스텀 머티리얼을 붙이려면 Cesium 머티리얼 레이어 구조를 따라야 한다.
  - 파일럿 반경 1~2km 정도의 한정된 배경은 정적 임포트가 품질과 제어 면에서 낫다.
- **ARCHITECTURE 반영**: §4의 "베이스맵 건물 숨김"은 빌드 단계의 `--exclude`(플레이 구역 GeoJSON)로 처리한다.
- **남은 확인** (2026-09-24 PC 세션에서 실데이터로 확인한 것 포함):
  - ✅ **실제 SHP 컬럼 매핑** — 서울 `AL_D010_11_20260909.shp`(V-World, 기준일 2026-09-09, 695,754건, 필드 29개 A0~A28, `.prj` = EPSG:5186):

    | 용도 | 컬럼 | 컬럼정의서 항목명 | 연남동 2×2 km 표본(9,393동) |
    |---|---|---|---|
    | 높이(m) `--height-field` | **A16** | 높이(m) | 값 있음 54.7%, 중앙 12.2 m, 5~95% 6.7~23.7 m, 최대 87.7 m. 0 = 결측 |
    | 지상층수 `--floors-field` | **A26** | 지상층_수 | 값 있음 90.7%, 중앙 3층, 최대 25층. A16/A26 중앙 **3.23 m/층**(10~90% 2.74~3.99) |
    | 용도명 `--usage-field` | **A9** | 건축물용도명 | 단독주택 3,908, 제2종근린생활시설 1,954, 공동주택 1,319, 제1종근린생활시설 914, 빈 값 872 … |
    | 건물 ID `--id-field` | **A1** | GIS건물통합식별번호(28자) | 9,387개 고유(중복 폴리곤 6개), 빈 값 0 |

    근거: V-World 「국가중점데이터_컬럼정의서(26.08.19)_배포용.xlsx」(데이터셋 페이지의 "컬럼 정의서 다운로드", 테이블정의서(전체) `AL_D010` 행)와 `inspect` 표본값·위 통계가 서로 맞는다. 높이가 0이거나 없으면 층수×3.2 m로 추정한다(`DEFAULT_FLOOR_HEIGHT`, 실측 중앙값 3.23 m/층과 일치). 연남동 반경 1 km 빌드에서 9,447동 중 4,258동(45%)이 추정 높이.
  - 🔴 **DEM 5 m 출처(결정 필요)**: 국토정보플랫폼 "공개DEM"은 **90 m 격자**만 있다(`37608.img`, 253×316, EPSG:5179; 국토지리정보원 안내도 공개 DEM은 90 m, 도시지역 1 m는 LiDAR로 별도 구축 [https://www.ngii.go.kr/kor/content.do?sq=204]). 5 m DEM은 다운로드 목록에 없고 받으려면 별도 신청이 필요해 보인다(절차 미확인). 지금 빌드는 **90 m로 임시** 진행했다(도로 경사·언덕 형태가 뭉개짐). 대안: ① NGII에 5 m/1 m DEM 제공 신청(사용자), ② 공개 1:5,000 수치지형도의 등고선·표고점으로 DEM 생성(코드 추가, 같은 신청서로 다운로드), ③ 90 m 유지(배경 전용이라 허용).
  - ✅ **정사영상 좌표**: 2025 정사영상(25 cm, `(B060)정사영상_2025_<도엽>.tif`)은 GeoTIFF 태그·월드파일이 **없다**. 메타데이터 XML은 좌표계(중부원점 GRS80 TM = EPSG:5186)와 도엽번호만 준다. `golmok-basemap georef-ortho`가 도엽번호로 위치를 잡고(이미지 = 도엽 경계상자 + 약 50 m 여유, 중심 정렬), 건물 윤곽선과 영상 경계를 맞춰 보정하고(37608077: peak 0.256 / 차순위 0.138, 보정 (−1, −1) m; 37608078: 0.287 / 0.170, 보정 0), 인접 도엽의 겹침(약 100 m)을 픽셀 단위로 맞춘다(상관 1.000). 절대 위치 약 1 m, 도엽 간 이음새 없음. 빌드된 지형 텍스처에 건물 지붕 윤곽을 겹쳐 맞는 것을 눈으로 확인했다.
  - ✅ **국외 반출** — 2026-09-25 사용자가 법률 자문을 받았고, NGII 파생물(지형 텍스처·스크린샷 등)을 저장소에 올려도 된다고 확인했다(자문 세부 내용은 이 문서에 없음, D-009). 배경: NGII 다운로드 신청서의 "사용자 준수사항"에 동의해야 받을 수 있고, 거기에 「공간정보관리법 제16조 및 제21조에 따라 국토교통부 장관의 허가 없이 측량성과를 국외 반출 시 2년 이하의 징역 또는 2천만원 이하의 벌금」이 적혀 있다. 법 제16조①: "누구든지 국토교통부장관의 허가 없이 기본측량성과 중 지도등 또는 측량용 사진을 국외로 반출하여서는 아니 된다. 다만, … 대통령령으로 정하는 경우에는 그러하지 아니하다." [국가법령정보센터, https://www.law.go.kr/법령/공간정보의구축및관리등에관한법률/제16조]. 생성된 UE 에셋은 법률 때문이 아니라 스크립트로 다시 만들 수 있어서 커밋하지 않는다(`.gitignore`).
  - 지오이드 보정값(Cesium 정렬 시). 아직 필요 없음(정적 임포트).
