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
- 재구성 후처리 `golmok-mesh`/`golmok-splat`(WP-03, `mesh`·`splat` extra, 로컬 도구): **trimesh** 4.x — MIT, **fast-simplification** 0.2 — MIT(PyVista; 내장 Fast-Quadric-Mesh-Simplification도 MIT), **scipy** 1.x — BSD-3-Clause [확인: 각 wheel `*.dist-info` 라이선스 원문, 2026-09-24]. **open3d(MIT)는 쓰지 않기로 판단**: Linux 휠이 시스템 libEGL을 요구해 CI·헤드리스에서 import가 실패했고 dash/flask 등 웹 스택을 끌고 온다. 필요한 기능(바닥 평면 RANSAC)은 numpy로 구현. pymeshlab(GPL)은 WP 스펙대로 제외. 3D Tiles 출력의 splat 인코딩은 Khronos `KHR_gaussian_splatting` README(Ratified) 원문을 따른다.
- 로컬 정합 도구 `golmok-align`(WP-07, `align` extra — 게임 패키지에는 들어가지 않음): **trimesh** 5.1 — MIT [확인: wheel 동봉 LICENSE.md 원문, https://github.com/mikedh/trimesh/blob/main/LICENSE.md], **scipy** 1.17 — BSD-3-Clause [확인: wheel 동봉 LICENSE.txt, https://github.com/scipy/scipy/blob/main/LICENSE.txt]. **open3d(MIT)는 쓰지 않는다**: 리눅스 CI 러너에 libEGL이 없어 import가 실패하므로 ICP를 numpy/scipy로 직접 구현했다. 2026-09-24 확인.
- WP-13 사운드 출처 조사(2026-09-27, Astra [#28](https://github.com/wooklym/golmok/pull/28)): Freesound CC0 1.0 7항목과 CC-BY 4.0 예비 항목의 개별 페이지 및 라이선스 법문을 확인했다(`research/10-ambience-sources.md`). **아직 소스 채택·파일 반입 없음**, 새 런타임/도구 의존성도 없음. 채택 후 실제 파일별 저자·URL·라이선스/버전·확인일·수정 내역을 `Content/Golmok/Audio/ATTRIBUTION.md`와 배포 크레딧에 남긴다. CC0는 법문상 표기 의무가 없지만 제3자 권리 확인을 대체하지 않는다. 유료 BOOM 음원은 완성 게임 사용권과 원본/가공 파일 공유 금지가 구분되고 EULA §3 'Real-time Exploitation' 조항이 있어 공개 저장소에 넣지 않으며 구매 전 적용 범위를 확인한다. 구매·계정·약관 동의는 실행하지 않았다.
- WP-13 13b(2026-09-28, Astra [#34](https://github.com/wooklym/golmok/pull/34)): 현재 `Content/Golmok/Audio/src/` WAV 7개는 프로젝트의 **결정적 합성 플레이스홀더**(`tools/scripts/make_placeholder_audio.py`, 기존 numpy 의존성, 48 kHz PCM16 mono, 합계 1,280,308바이트, LFS). 출처 표기 `project-generated`는 외부 라이선스 채택이나 CC0 권리 포기 선언이 아니다. Freesound CC0 청취 후보 7개의 조사·채택 기록은 13a 그대로이고 원본 다운로드·계정 약정은 하지 않았다(소유자 결정 대기). 출처·저자·라이선스 URL·수정 내역은 `Config/Golmok/audio.json` → `ATTRIBUTION.md`/`Credits/audio-credits.txt` 파이프라인으로 보존한다. 새 런타임/도구 의존성 없음. 패키징은 `DefaultGame.ini` `+DirectoriesToAlwaysCook=(Path="/Game/Golmok/Audio")` 훅(`[WP-13 hook]`).
- 베이스맵 `golmok-basemap contour-dem`(2026-09-25, `basemap` extra)도 위의 **scipy**(BSD-3-Clause)를 쓴다(TIN 보간·가우시안 필터). 게임 패키지에는 들어가지 않는다.
- 캐릭터 애니메이션 에셋(V-08, 2026-09-26 PC 세션이 브라우저로 원문 확인 — **사용자 재확인 필요**, 인용 전문은 `runbooks/pc-verify-animation.md` §8 표 1): **Game Animation Sample(GASP, Epic Games)** — Fab **Standard License**, 무료 [확인: Fab 리스팅 https://www.fab.com/listings/880e319a-a59e-4ed2-b268-b32dac7fa016 "License terms: Standard License", Fab EULA https://www.fab.com/eula (영문 지배)]. 허용: 사용·복제·수정(§3(a) "privately use, reproduce, display, perform, and modify"), 프로젝트에 통합한 배포 — 비디오 게임 등 일반 공개 배포 포함(§4(c)). 조건·금지: **독자 재배포 금지**(§5(a) — 협업자·비공개 저장소만; 이 저장소는 공개라 **원본 에셋을 커밋하지 않는다**), GPL/LGPL(동적 링크 제외)/CC-BY-SA 콘텐츠와 결합 금지(§6(a)), 리스팅 표기 "언리얼 엔진 전용 콘텐츠", "AI 사용 허용: 아니요"(NoAI, §6(b)(vii)). **템플릿 마네킹**(`SKM_Manny_Simple`·`ABP_Unarmed`, 엔진 `Templates/` 동봉) — UE EULA의 **Examples**(§1)로 §5(b) "You may Distribute Examples (including as modified by you) in Source Code or object code to any third party." [확인: https://www.unrealengine.com/eula/unreal]. Fab 에셋은 UE EULA 대상이 아님(§1). 어느 안을 채택하든 GPL/CC-BY-SA 콘텐츠·코드와의 결합 금지는 두 EULA 공통(§6).
- 개발·CI 전용 도구(제품에 포함되지 않음, WP-01): **ruff** — MIT [확인: https://github.com/astral-sh/ruff/blob/main/LICENSE], **3d-tiles-validator**(CesiumGS, `npx`로 CI에서만 실행) — Apache-2.0 [확인: https://github.com/CesiumGS/3d-tiles-validator/blob/main/LICENSE.md]. 2026-09-24 원문 확인.

- WP-18 컨셉 자료(2026-09-27 병합 기록): **OpenAI 내장 image_gen** 출력은 공개 컨셉 JPG7장에만 사용한다. [약관·저작물성·표시 확인과 한계](design/character-concept.md#a5-권리-점검)를 따르며 최종 에셋/비침해 보증으로 취급하지 않는다. UE 템플릿 Manny/Quinn은 기존 설치에서 로컬 복사하고 원본을 커밋하지 않는다. Meshy/VRoid/VRM4U/MetaHuman/Fab 구매·신규 라이선스 의존성은 채택하지 않았다. 외주 계약과 비공개 에셋 보관은 D-018 ② 이후 항목별로 기록한다.

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
- **사진**: 기본 카메라 앱, **메인 1x(24mm), 48MP ProRAW Max, ProRAW 형식 JPEG 무손실**, AE/AF 잠금, 매크로 자동 전환 끔. 수동 셔터 앱은 RAW 해상도가 12MP로 제한되는 경우가 있어 해상도를 우선했다 [2차].
- **영상**: Blackmagic Camera 앱, 4K60, 셔터 1/250~1/500, ISO·WB·초점 고정, HEVC 10-bit.
- 초광각과 망원은 쓰지 않는다.
- **첫 촬영 전 리허설**(가이드 §4-C)로 셔터 속도를 확인한다. 흐린 아침에 셔터가 느리게 잡히면 설정을 다시 정한다.
- PC 전송 시 "원본 유지" 설정을 확인한다.
- **추가(승인, 2026-09-24)**: ProRAW 형식(설정 > 카메라 > 포맷 > ProRAW 형식)을 **JPEG 무손실**로 고정한다. 가이드 #1 v3에 반영.
  - 이유: iPhone 16 Pro/17 Pro의 JPEG-XL ProRAW(무손실·손실)는 DNG 1.7이다. LibRaw 0.22는 이것을 **Adobe DNG SDK와 함께 빌드했을 때만** 현상한다([LibRaw 0.22 릴리스 노트](https://www.libraw.org/news/libraw-0-22-0-release)). 우리 `golmok-blur`가 쓰는 rawpy 0.27.1 휠은 SDK 없이 빌드됐다(PC에서 `rawpy.flags` 확인). JPEG 무손실은 기존 ProRAW 형식이라 현상된다.
  - 대가: 48MP 장당 약 75MB(JPEG-XL 무손실은 약 46MB, 손실은 약 20MB) [2차]. 1,300장이면 약 100GB로, 저장공간 계획(D-006)과 맞는다. 화질은 JPEG 무손실과 JPEG-XL 무손실이 같다(둘 다 무손실).
  - 채택하지 않은 대안: JPEG-XL 무손실로 찍고 현상 경로를 추가한다(예: tifffile + imagecodecs로 JPEG-XL 타일 디코드 후 선형 DNG 현상, 또는 Adobe DNG Converter로 DNG 1.4 변환 — 약관 동의 필요). 저장공간이 병목이 되면 다시 검토한다.

### D-012 | 승인(기술 결정, 원칙 적용) | 2026-09-24 — 배경 베이스맵을 **UE 정적 메시(Nanite)로 임포트**한다
- **내용**: `golmok-basemap`이 만든 GLB 타일을 UE 정적 메시로 임포트한다. 건물은 Nanite + 절차적 파사드 머티리얼, 지형은 정사영상 텍스처를 쓴다. Cesium3DTileset 런타임 스트리밍은 쓰지 않는다. 같은 출력에 `tileset.json`(3D Tiles 1.1)도 함께 만들어 두어, 웹 검수 뷰어와 Cesium에서도 쓸 수 있게 한다.
- **이유(퀄리티 우선)**:
  - 런타임에 생성되는 타일셋 메시에는 Nanite와 메시 디스턴스 필드가 없어 Lumen 소프트웨어 GI 품질이 떨어진다[추정, UE 일반 동작].
  - 커스텀 머티리얼을 붙이려면 Cesium 머티리얼 레이어 구조를 따라야 한다.
  - 파일럿 반경 1~2km 정도의 한정된 배경은 정적 임포트가 품질과 제어 면에서 낫다.
- **ARCHITECTURE 반영**: §4의 "베이스맵 건물 숨김"은 빌드 단계의 `--exclude`(플레이 구역 GeoJSON)로 처리한다.
- **지형 타일은 Nanite를 끈다**(2026-09-25): Nanite 메시의 복합 충돌은 단순화된 fallback 메시로 만들어진다. 5 m DEM으로 지형에 기복이 생기자 타일 경계에 충돌 틈이 생겼다(13×13 격자 추적 169점 중 19점이 통과, 모두 경계선 위). 지형 타일(250 m, 5 m 격자)은 작아서 Nanite 이득이 없으므로 일반 정적 메시로 두고(169/169, 경계 3 cm 옆 597/597 명중), 건물은 Nanite를 유지하되 fallback을 단순화하지 않는다(`fallback_relative_error` 0) — 충돌이 보이는 형상과 같다.
- **남은 확인** (2026-09-24 PC 세션에서 실데이터로 확인한 것 포함):
  - ✅ **실제 SHP 컬럼 매핑** — 서울 `AL_D010_11_20260909.shp`(V-World, 기준일 2026-09-09, 695,754건, 필드 29개 A0~A28, `.prj` = EPSG:5186):

    | 용도 | 컬럼 | 컬럼정의서 항목명 | 연남동 2×2 km 표본(9,393동) |
    |---|---|---|---|
    | 높이(m) `--height-field` | **A16** | 높이(m) | 값 있음 54.7%, 중앙 12.2 m, 5~95% 6.7~23.7 m, 최대 87.7 m. 0 = 결측 |
    | 지상층수 `--floors-field` | **A26** | 지상층_수 | 값 있음 90.7%, 중앙 3층, 최대 25층. A16/A26 중앙 **3.23 m/층**(10~90% 2.74~3.99) |
    | 용도명 `--usage-field` | **A9** | 건축물용도명 | 단독주택 3,908, 제2종근린생활시설 1,954, 공동주택 1,319, 제1종근린생활시설 914, 빈 값 872 … |
    | 건물 ID `--id-field` | **A1** | GIS건물통합식별번호(28자) | 9,387개 고유(중복 폴리곤 6개), 빈 값 0 |

    근거: V-World 「국가중점데이터_컬럼정의서(26.08.19)_배포용.xlsx」(데이터셋 페이지의 "컬럼 정의서 다운로드", 테이블정의서(전체) `AL_D010` 행)와 `inspect` 표본값·위 통계가 서로 맞는다. 높이가 0이거나 없으면 층수×3.2 m로 추정한다(`DEFAULT_FLOOR_HEIGHT`, 실측 중앙값 3.23 m/층과 일치). 연남동 반경 1 km 빌드에서 9,447동 중 4,258동(45%)이 추정 높이.
  - ✅ **DEM 5 m** — 2026-09-25 사용자 결정: ② 수치지형도로 만든다. 국토정보플랫폼 "공개DEM"은 **90 m 격자**뿐이고(`37608.img`, 253×316, EPSG:5179; 국토지리정보원 안내도 공개 DEM은 90 m, 도시지역 1 m는 LiDAR로 별도 구축 [https://www.ngii.go.kr/kor/content.do?sq=204]), 5 m는 다운로드 목록에 없다. 그래서 1:5,000 **수치지형도 Ver2.0**(SHP, 2025년 제작, 도엽 37608067·068·077·078·087·088, 도엽당 2~5 MB, 같은 신청서)의 등고선 `N3L_F0010000`(`등고수치`, 주곡선 5 m·계곡선 25 m)과 표고점 `N3P_F0020000`(`수치`)으로 5 m DEM을 만든다(`golmok-basemap contour-dem`: 등고선을 5 m마다 재표본 + 표고점 → Delaunay TIN 선형 보간 → 가우시안 σ 1칸). 연남동 ±1.3 km: 등고선 점 95,550 + 표고점 999, TIN이 전 영역을 덮음, 높이 5.0~101.3 m. 표고점 10%(99점)를 빼고 만든 뒤 그 점에서 잰 오차: 중앙 0.63 m, RMSE 2.09 m, 95% 3.2 m, 최대 14.5 m(가장 큰 오차는 등고선 사이 작은 봉우리·정상. 최종 DEM에는 모든 표고점이 들어가 정상이 깎이지 않는다). 90 m 공개DEM과의 차이: 평균 −0.13 m, 표준편차 4.9 m. 옹벽 `N3L_F0040000`의 `높이`는 벽 높이라 쓰지 않는다. 90 m 공개DEM은 가장자리 채움(`--fill-dem`)으로만 남긴다.
  - ✅ **정사영상 좌표**: 2025 정사영상(25 cm, `(B060)정사영상_2025_<도엽>.tif`)은 GeoTIFF 태그·월드파일이 **없다**. 메타데이터 XML은 좌표계(중부원점 GRS80 TM = EPSG:5186)와 도엽번호만 준다. `golmok-basemap georef-ortho`가 도엽번호로 위치를 잡고(이미지 = 도엽 경계상자 + 약 50 m 여유, 중심 정렬), 건물 윤곽선과 영상 경계를 맞춰 보정하고(37608077: peak 0.256 / 차순위 0.138, 보정 (−1, −1) m; 37608078: 0.287 / 0.170, 보정 0), 인접 도엽의 겹침(약 100 m)을 픽셀 단위로 맞춘다(상관 1.000). 절대 위치 약 1 m, 도엽 간 이음새 없음. 빌드된 지형 텍스처에 건물 지붕 윤곽을 겹쳐 맞는 것을 눈으로 확인했다.
  - ✅ **국외 반출** — 2026-09-25 사용자가 법률 자문을 받았고, NGII 파생물(지형 텍스처·스크린샷 등)을 저장소에 올려도 된다고 확인했다(자문 세부 내용은 이 문서에 없음, D-009). 배경: NGII 다운로드 신청서의 "사용자 준수사항"에 동의해야 받을 수 있고, 거기에 「공간정보관리법 제16조 및 제21조에 따라 국토교통부 장관의 허가 없이 측량성과를 국외 반출 시 2년 이하의 징역 또는 2천만원 이하의 벌금」이 적혀 있다. 법 제16조①: "누구든지 국토교통부장관의 허가 없이 기본측량성과 중 지도등 또는 측량용 사진을 국외로 반출하여서는 아니 된다. 다만, … 대통령령으로 정하는 경우에는 그러하지 아니하다." [국가법령정보센터, https://www.law.go.kr/법령/공간정보의구축및관리등에관한법률/제16조]. 생성된 UE 에셋은 법률 때문이 아니라 스크립트로 다시 만들 수 있어서 커밋하지 않는다(`.gitignore`).
  - 지오이드 보정값(Cesium 정렬 시). 아직 필요 없음(정적 임포트).

---

> **D-013~D-017은 WP-10(2026-09-25)이 등록한 제안이다.** 상세(플레이어 가치·마일스톤·구현 규모·의존·리스크)는 [`design/game-features-proposal.md`](design/game-features-proposal.md). 사용자가 승인·수정·보류·폐기를 정한다. MVP 범위(DEVELOPMENT-PLAN §1.3)는 바꾸지 않는다.

### D-013 | 승인 | 2026-09-25 — 포토 모드
- 제안: Phase 1 M7(1.6 폴리시)에 **선택 항목으로 최소판**(일시정지·자유 카메라·DOF·노출·HUD/캐릭터 숨김·고해상도 촬영 + 메타 JSON), Phase 2에 확장(시간대 슬라이더·LUT·사진첩).
- 규모: C++ 1 WP(Fable ultracode, 게임 비주얼 직접 영향) + PC 검증. 의존: WP-05 `golmok.screenshot`, D-010.
- 리스크: 공유 사진에 실제 간판·블러 누락 얼굴 → 공개 전 자문(D-009) 항목에 "사용자 스크린샷 공유" 추가 필요.
- **결정(2026-09-25, 사용자)**: D-013~D-017 전부 승인, 권장 우선순위대로 진행. 최소판은 **WP-12**(`plan/WP-12-photo-mode.md`, Fable ultracode)로 즉시 착수. 확장(시간대 슬라이더·LUT·사진첩)은 Phase 2.
- **결정 2(2026-09-27, 사용자, V-09 PC 검증 뒤 — PR #27·#29)**: ① `MaxMultiplier` 2 유지(3x 복귀는 #59 비동기 저장·진행 표시 뒤) ② 2x 촬영 시 1.2 s 정지 허용(폴리시 단계에서 비동기 저장 검토) ③ `PauseMode` 기본값 `GamePause` 유지 ④ 마우스 시선 속도(1000 px = 35°) 현행 유지, 사용자 체감 후 재검토 ⑤ PC fix c026815(정지 잔상·EV 속도) 채택(Opus 적대 검증 통과, PR #27). 코드 변경 없음(값은 이미 main).
- **결정 3(2026-09-28, 오케스트레이터 D-019 — Fable 설계 결정, V-09b 관찰 뒤)**: **수평 입력만 있을 때 카메라 높이(Z)는 바뀌지 않는다.** 구·footprint 경계·벽에 막힌 이동은 수평면 안에서만 미끄러지고(수평면에 투영한 방향), 수평면 안에서 더 갈 수 없으면 정지한다. 수직 입력(Q/E)이 있을 때만 제약이 Z를 바꿀 수 있다(구면을 따라 미끄러져도 된다). 근거: 포토 모드에서 WASD는 수평 이동이라는 사용자 기대(V-09b: 구∩경계 접합에서 수평으로 밀면 최근접점 투영 때문에 구면을 따라 앵커 높이 쪽으로 내려감, Shift 1.6 s에 −44 cm). 구현(WP-12 후속 수정 2): `GolmokPhotoMath::Constraint::bKeepHeight`(구 클램프를 원하는 높이의 수평 단면 원판 최근접점으로; 그 높이가 구의 높이 범위 밖이면 현재 높이 평면), `AGolmokPhotoCameraPawn::MoveConstrained(…, bKeepHeight)`(벽 슬라이드 Z 성분 0), `Tick`은 Q/E 축이 데드존(|축| ≤ 0.1 — 패드 트리거에 손가락만 얹은 경우 포함) 안일 때 켠다. **확정판(2026-09-28, PR #40 리뷰 M1/M2 뒤 — Fable 설계 결정, 오케스트레이터 D-019; 이전 해석 "설계 §5-2 '전방(피치 포함)'은 그대로 — 피치를 준 W는 시선 방향대로 Z가 변하고 제약·슬라이드만 Z를 더하지 않는다"는 폐기)**: **포토 카메라의 W/S/A/D는 항상 yaw 기준 수평면 이동이다(피치 무시). 높이(Z)는 Q/E(UpDown)만 바꾼다.** WP-12 설계 §3-3(원래 '§5-2'로 잘못 인용)의 "전방(피치 포함)"을 "전방(yaw만)"으로 바꾼다(§5-2 스텝·속도 표는 그대로). 근거: ① 포토 모드에서 WASD는 수평 이동이라는 사용자 기대(대부분의 AAA 포토 모드: 스틱 = 수평면, 트리거/버튼 = 상하)와 결정 3의 근거를 일치시킨다. ② 피치 W/S + 높이 유지 클램프 조합이 구 경계에서 극까지 타고 오르며 틱당 최대 11배 튀는 결함(리뷰 M1)을 별도 가드 없이 없앤다. ③ 런북 §7의 "z 변동 0" 기대가 피치와 무관하게 정확히 성립한다(M2). ④ 벽(슬라이드 평탄화)과 구의 처리가 대칭이 된다(N1). ⑤ Q/E와 3 m 구 반경이 있으므로 시선 방향 돌리(dolly)를 잃는 손실은 작다. 유지: 수직 입력(Q/E, 데드존 0.1)이 있으면 3D 구 클램프 경로(구면을 따라 미끄러져도 됨). 구·경계·벽에 막힌 수평 이동은 수평면에서만 미끄러지고 더 못 가면 정지(`bKeepHeight`·`ClampToSphereXY`·슬라이드 Z 평탄화는 그대로 — 이제 Desired.z == Current.z이므로 방어 수단으로 남는다). 결과: 피치를 숙이고 W를 밀어도 z 변동 0(런북 §7 ⑤), 경사로를 수평으로 밀면 정지(E로 올림, ⑦), 파사드에 피치 W → 정지. 구현: `AGolmokPhotoCameraPawn::Tick`의 전방 `FRotator(0.f, Look.Yaw, 0.f).Vector()`. 겹침에서 벗어나는 후퇴(`bStartPenetrating`, 앵커 쪽 10 cm)는 복구 동작이라 3D 그대로. PC 재검증: 런북 §7 "접합 수평 입력 시 높이 불변".
- **진행(2026-09-29, 오케스트레이터 D-019 — V-09c PC fix #68, [PR #56](https://github.com/wooklym/golmok/pull/56)→[PR #58](https://github.com/wooklym/golmok/pull/58))**: **WP-12 🟢·V-09 🟢**(§4 종료 밝기 1~4·§7 높이 불변 통과). 결정 3 구현 보완: 경사면·계단 모서리에 막히면 슬라이드는 충돌면의 **수평 단면 방향**(수평면에 평탄화한 뒤 충돌면 수평 법선의 안쪽 성분만 제거; 수평 법선 길이 ≤ 0.02(≈1.15°)는 평탄화만). 의도(수평만, 못 가면 정지, 오르지 않음)는 그대로이고 수직 벽 결과는 동일, 3D(Q/E) 경로 불변. 리뷰 R56(Opus 읽기 전용) A 없음; 0.02 임계값은 스캔 바닥 저고도 이동을 PC에서 본 뒤 유지 또는 sin 5°(0.087)로 재판단(R56-1, V-11 카드). 후속(Claude 레인): 슬라이드 방향을 `GolmokPhotoMath.h` 순수 함수로 분리해 numpy 교차검증(R56-2), fixture 단언·(c3) 변형·주석(R56-5/6/7). 절차 기록: 이 PC fix는 Fable PC 세션이 작성했고(2026-09-27 정책상 코딩은 Opus) Opus 서브 리뷰·적대 리뷰로 보완했다 — 이후 PC 카드는 "PC fix 코드는 Opus 서브에이전트, Fable은 판정만"을 명시한다(V-11 카드부터). ⑥ 게임패드는 소유자 항목 C-09.

### D-014 | 승인 | 2026-09-25 — Zone 지도·이동
- 제안: **Phase 2 초반**(Zone 2곳 이상일 때). 정사영상 기반 2D 지도 + Zone footprint·방문 여부 + 선택 이동(선로드 후 텔레포트). 미니맵은 기본 끔.
- 규모: C++ 1~2 WP + 지도 텍스처 도구 + manifest `spawn` 필드(스키마 변경). 의존: WP-09(V-07), D-008, D-012.
- 리스크: 정사영상 파생물의 공개 배포 조건, 위치기반서비스 해당 여부 → 공개 전 자문 [확인 필요].
- **결정(2026-09-25, 사용자)**: 승인. 시점은 제안대로 Phase 2 초반(Zone 2곳 이상·V-07 통과 뒤), D-017과 묶어 **WP-15**로 등록(착수 조건 충족 시 스펙 작성).
- **오케스트레이터 결정(D-019, 2026-09-28)**: WP-15를 **15a**(manifest schema 2 `spawn`/`display_name`, `Map/GolmokTravelSubsystem` 이동, `Save/` 자동 세이브·복원 — 표현 방식·실제 zone 수와 무관, 합성 zone 2곳으로 테스트, 클라우드 Opus ultracode, PC 검증 V-14)와 **15b**(정사영상 지도 텍스처·Slate 지도 UI·미니맵 — D-009 정사영상 파생물 배포 조건 자문·실제 zone 뒤 PC)로 나누어 15a를 WP-14a와 병렬로 시작한다. 근거: V-07 통과, 클라우드 유휴 방지(소유자 지적 2026-09-28), 15a는 브랜치로 되돌릴 수 있음. 스펙 [`plan/WP-15-zone-travel-save.md`](plan/WP-15-zone-travel-save.md). WP-17 `sounds[]`는 v2에 넣지 않는다(V-10·첫 현장 녹음 뒤 결정).
- **진행(2026-09-28, 오케스트레이터 D-019)**: **WP-15a 🟡 코드 완료·PC V-14 대기**([PR #49](https://github.com/wooklym/golmok/pull/49) 병합, session_018Tn23KryyZ9XmYXMAa91Mb). 리뷰 R49(Opus 읽기 전용): (A) 1건(`golmok.save reset` 뒤 1 s 방문 폴링이 현재 zone을 첫 방문으로 재기록 → 리셋 시점의 zone 집합은 떠나기 전까지 억제)·(B) 4건(종료 스냅샷 `OnWorldBeginTearDown` 강제 갱신, 보류 중 수동 저장은 현재 위치, 스펙 002 스폰 값, 런북 로그 줄) 반영. **Fable 판단**: R49-6 `bRestoreInPIE=False` 채택 — 기존 PIE 런북(V-03/07/09/10)의 PlayerStart 결정성을 지키고 제품 복원은 standalone/패키지에서 V-14 §6이 확인 · R49-8 GeoOrigin 없는 레벨(L_Dev)에서는 index zone travel을 거절하고 '다른 지역'은 레벨 원점 30 km 휴리스틱으로 둔다(판단 18) · **WP-14a 연결**: 세이브에 시간대 {분, 모드}를 저장하고 복원은 모드별 즉시(Fixed/Clock: 저장 시각 복원, Realtime: 모드만·로컬 시각), 구 세이브(분 -1)는 프리셋 이름 폴백, 복원 순서는 Fixed로 멈춘 뒤 즉시 점프·모드 설정(2 s 전환·중복 `OnPresetChanged` 없음). `SaveSchemaVersion` 1 유지(필드 추가만). 15b(지도 텍스처·UI)는 D-009 자문·실제 zone 2곳 뒤.

### D-015 | 승인 | 2026-09-25 — 시간대 폴리시·날씨
- 제안: 시간대 폴리시(night look-dev, [`design/lighting-night-lookdev.md`](design/lighting-night-lookdev.md))는 **Phase 1 M7**, 날씨(비)는 **Phase 2 중반, D-010 결과를 본 뒤**. 눈은 제외.
- 규모: 시간대 소(프리셋 값·필요 시 노출 키 추가), 날씨 대(2~3 WP: 상태·젖음 머티리얼·Niagara·소리). 의존: D-010(splat이면 젖음 표현 제한), R5.
- **결정(2026-09-25, 사용자)**: 승인. 시간대 폴리시는 **WP-14**(D-010 확정 뒤, night look-dev는 PC), 날씨(비)는 **WP-16**(Phase 2 중반, D-010 뒤). 눈 제외 유지. 조합 선택(night A+B 등)은 look-dev 결과를 보고 별도 결정.
- **오케스트레이터 결정(D-019, 2026-09-28)**: WP-14를 **14a**(연속 시각 1440분·시계 모드 fixed/clock/realtime·키프레임 `time`·보간·이벤트 계약·콘솔/HUD — 환경 표현 방식과 무관, 프리셋 값 불변, 클라우드 Opus ultracode, PC 검증 V-13)와 **14b**(night look-dev·발광 에셋 — D-010 뒤 PC)로 나누어 14a를 먼저 한다. 근거: D-010 의존은 밤 look-dev뿐이고 PC·C-02 대기로 클라우드가 비어 있음. 스펙 [`plan/WP-14-time-of-day-policy.md`](plan/WP-14-time-of-day-policy.md). 소유자가 뒤집으면 14a 브랜치를 닫는다(되돌릴 수 있음).
- **진행(2026-09-28, 오케스트레이터 D-019)**: **WP-14a 🟡 코드 완료·PC V-13 대기**([PR #51](https://github.com/wooklym/golmok/pull/51) 병합, session_01S3bDop479NqGLXdV66Ky1L). **§2a `hold_minutes` 결정(Fable 게임 감각)**: 4키프레임 선형 보간만으로는 lux < 0.1 구간이 약 29분뿐이라 '밤'이 사실상 없다 → 키프레임별 `hold_minutes`(cycle 프리셋만, time+hold < 다음 키프레임)를 두고 night를 480분(21:30→05:30) 유지한 뒤 2 h 램프. 유지 중 alpha 0·CurrentPreset = night·IsNight true. 그래서 `OnPresetChanged` 중점이 02:30 → 06:30으로 옮겨지고 WP-13 오디오는 무수정으로 19:45/06:30에 전환하며, 14b 가로등이 `IsNight`/`OnNightChanged`를 밤 신호로 쓸 수 있다. **리뷰 R51 계약**: `IsNight`/`CurrentPreset`은 점프 시작 시점의 목표 상태이고 `OnPresetChanged` 콜백 안에서 이미 새 값(R51-5); F5(`NextPreset`)는 시계 기준이면 시간상 다음 키프레임(R51-4); Realtime은 틱 간 실시간 공백이 max(전환 시간, 2 s)를 넘으면 전환으로 재동기(R51-6). 태양 회전 갱신 양자화(VSM/Lumen 비용)는 V-13 성능 수치 뒤 판단(R51-3). 되돌리기: JSON `hold_minutes` 제거·코드 계약 한 줄.
- **검토(2026-09-29, 오케스트레이터 D-019 — 착수 아님)**: (b) 날씨 WP-16의 **16a/16b 분할 검토 메모** [`plan/WP-16-weather.md`](plan/WP-16-weather.md) — 표면 젖음(러프니스·웅덩이·반사)만 D-010에 묶이고 날씨 상태·JSON 조명 수정자·빗줄기 파티클·젖음 파라미터 계약(MPC)·오디오 이벤트 훅·세이브 필드·콘솔/HUD는 표현 방식과 무관하므로 16a(클라우드 Opus ultracode 가능)로 분리 가능. 착수는 V-13·V-14 통과 뒤 클라우드 여유 시(Phase 1 품질 게이트 D-010·V-08·V-12가 소유자·PC에 걸린 동안의 클라우드 후보); 설계 확정은 착수 전 Fable. Niagara 플러그인 활성화(uproject·Build.cs)는 착수 세션의 별도 커밋. 소유자가 뒤집을 수 있음.

### D-016 | 승인 | 2026-09-25 — 환경음
- 제안: **기본 앰비언스·발소리·실내 전환은 Phase 1 M5~M7**, Zone별 현장 녹음은 Phase 2(촬영 가이드에 녹음 절차 추가).
- 규모: C++ 1 WP(MetaSounds) + 사운드 에셋(라이선스 원문 D-002 기록, 유료면 사용자 승인). 의존: 애니메이션 채택안(V-08, 발소리 노티파이).
- 리스크: 녹음에 타인의 대화가 담기는 문제(통신비밀보호법·개인정보) — 법령 원문 미확인 [확인 필요], 대화 구간은 쓰지 않는 운영 제안.
- **결정(2026-09-25, 사용자)**: 승인. 기본 앰비언스·발소리·실내 전환은 **WP-13**(`plan/WP-13-ambience-audio.md`, WP-12 다음, Fable ultracode). 사운드는 라이선스 원문이 확인된 무료(CC0 우선) 항목으로 시작하고 **유료 라이브러리 구매는 별도 승인**(미결). 현장 녹음 절차·Zone별 소리는 **WP-17**(Phase 2, 문서·촬영 가이드).
- **진행(2026-09-28, 오케스트레이터 D-019)**: (b) 현장 녹음 절차 문서 완료(Astra T4, [#37](https://github.com/wooklym/golmok/pull/37)): `capture/03-field-recording.md`·`plan/WP-17-field-recording.md`. Zone manifest `sounds[]`는 새 schema_version·로더·검증기·스펙 동시 변경 **제안 단계**(채택은 Zone 2곳·V-10·Fable 청취 뒤, bump는 Claude 레인). 현행 `audio.json` 계약(license 3종·https `source_url`)으로 자체 녹음은 반입 불가 → license 값·내부 기록 ID 계약 확장이 반입 전제이고, 자체 녹음에 CC0 등 공개 라이선스를 붙이는 것은 소유자 항목(라이선스 약정). 운영 규칙: 녹음 기기 음성 메모 iCloud 동기화 끄기. 외장 마이크·바람막이 구매는 소유자 항목(내장 마이크 30 s 시험 실패 시에만 후보 제시). 루프 길이 가설: 도시 원경 스테레오 20~26 s, 룸톤 mono 30~40 s(V-10 청취로 확정).
- **진행(2026-09-28, 오케스트레이터 D-019)**: (a) **WP-13 🟢** — V-10 PC 검증 통과([#53](https://github.com/wooklym/golmok/pull/53) → 클라우드 병합 [PR #54](https://github.com/wooklym/golmok/pull/54)): 판정 근거는 master submix 녹음 파형 분석과 패키지 루프백이며 음색·최종 밸런스 청취는 소유자 항목(STATUS C-08). **Fable 설계 판단(런북 `pc-verify-wp13.md` §7-3 의견)**: ① 실내 크로스페이드 1.0 s 채택(문 통과는 공간 이벤트라 시간대 전환 2 s보다 빨라야 자연스럽고, 측정상 클릭·끊김 0) ② equal-power(sin/cos) 크로스페이드 채택(선형 진폭 보간은 무관한 두 베드 사이에서 중간 1.6~2.8 dB가 꺼짐) ③ Photo mute 진입/해제 0.25 s 페이드 채택(20~40 ms 컷은 클릭은 없지만 거칠다) ④ `stride_scale_by_mesh` 기각(proxy 걷기는 맞지만 달리기가 1.7배) → 캐릭터별 걷기/달리기 보폭 데이터(애니 실측 manny·quinn 67/146, proxy135 54/142, proxy110 45/115 cm)를 임시 채택, V-08 애니 채택 뒤 노티파이 구동으로 교체 ⑤ 볼륨 후보(master 1.0·낮 0.5·밤 0.36·실내 0.30·발소리/착지 1.0, 비율 유지 +9 dB) 임시 적용 — 장치에서 −60 dBFS는 실용상 들리지 않으며 합성 소스 상한 안에서 최대, 최종값은 소유자 청취 ⑥ 임포트가 만드는 `Content/Golmok/Audio/*/SW_*.uasset`은 ignore(단일 소스는 `audio.json`+WAV, `golmok.audio_import`로 재생성). ①~⑤는 Astra **T8**(오디오 레인, `astra-tasks.md`), ⑥은 병합 커밋의 `.gitignore`(핫스팟 훅 블록). 전부 되돌릴 수 있음(JSON 값·곡선·ignore 한 줄). 리뷰(R53-1~11, Opus 읽기 전용) 반영: V-10 범위는 `5f6c810` Audio 코드(T6 #50 이전)·녹음 파형 분석 기준으로 한정하고 #50 런타임 변경은 다음 PC 카드에서 스모크. **레인 규칙 보완(D-019)**: PC 검증 세션은 Astra 레인 런북의 결과 칸·확인 명령·실행 기록 절을 고칠 수 있고, 병합 때 양쪽을 살린다(DEVELOPMENT-PLAN §7.6). **Fable 판단 추가**: ⑦ 리스너가 카메라라 붐 길이에 따라 플레이어 발소리 레벨이 달라짐(Manny −35.8 ~ proxy110 −34.2 dBFS) → 플레이어 자신의 발소리·착지는 거리 감쇠 없이 재생(2D 또는 감쇠 해제; 감쇠는 다른 소스용으로 유지) → T8 ⑦. PC 환경 항목: Windows 보안 대화상자가 GUI 검증 키 입력을 막고 있음(STATUS C-07, 소유자 처리). **T8 병합(2026-09-29, [PR #55](https://github.com/wooklym/golmok/pull/55))**: ①~⑤·⑦ 구현·헤드리스·UE 빌드 검증(Astra). 곡선 결정(리뷰 R55-1, Fable): 전력 보간의 진행값을 sin²(πα/2)(raised cosine)로 성형 — 0↔1은 정확한 sin/cos 법칙, 끝점 급변(첫 틱 −18 dB 점프) 제거, 상보 전력·재타깃 연속성 유지; Photo mute는 단일 소스라 진폭 S-curve, 원샷은 `FadeOut(…, EAudioFaderCurve::SCurve)`. 새 계약: Physics 표면 이름이 세트 id(asphalt/tile/stairs)와 대소문자 무관하게 같아야 매핑되고, 아니면 default + HUD error + 번호당 1회 Warning(C-11 Zone 에셋 단계에서 이름 정식 정의). 최종 음질·밸런스 합격은 포함하지 않음 — C-07 뒤 V-11 카드에서 T6/T8 스모크·재녹음, C-08 청취.

### D-017 | 승인 | 2026-09-25 — 세이브
- 제안: **Phase 2 초반, D-014와 함께**. 자동 저장 슬롯 1개, 위치는 경위도·높이 + zone_id·버전으로 저장(UE 좌표 아님), 시간대·방문 zone·사진 목록.
- 규모: C++ 1 WP(`USaveGame` + `AsyncSaveGameToSlot`), Opus 가능. 의존: D-014, WP-04 Geo, zone 버전 규약.
- **결정(2026-09-25, 사용자)**: 승인. D-014와 함께 **WP-15**(Phase 2 초반).
- **진행(2026-09-28, 오케스트레이터 D-019)**: 15a 세이브 구현 병합([PR #49](https://github.com/wooklym/golmok/pull/49)) — 슬롯 `golmok_auto` 1개, 경위도·타원체고·ENU yaw·zone id/버전·방문·사진 상대 경로(`Saved/` 기준, 절대/`..` 거절)·시간대 {분, 모드}, UE 좌표·개인정보 없음. 자동 저장 트리거: 이동 도착·첫 방문·사진·60 s·종료 동기(강제 스냅샷); 복원 규칙 ①②③·`-GolmokNoRestore`·레벨 불일치 시 위치 복원 안 함·PIE 자동 복원 끔. 상세는 D-014 진행 항목.

### D-018 | ① 승인·② 대기 | 2026-09-27 — 캐릭터 선택·교체와 고유 캐릭터 제작

- **① 승인 범위**: 스타일라이즈드 PBR, 135cm/4.5등신, GASP+스타일 보정은 제작/시험 가설이다. 첫 세트 c01 한 종(모루빛/Morubit은 가칭), 같은 폰의 JSON 로스터·콘솔 교체(18a), V-11/V-12 절차를 진행한다. Phase1 M7 품질 검증 기반이며 메뉴·세이브를 MVP에 넣지 않는다.
- **18b 시점**: V-08·V-12와② 이후 실제 에셋/리타깃/이모트를 추진한다. 선택 UI·선택 저장·커스터마이즈는 Phase2 초반 WP-15와 함께 검토한다. 비율 변경이 가능한 전체 스케일 프록시를 실제4.5등신 리타깃 결과로 취급하지 않는다.
- **② 별도 승인 필요**: 최종 룩·비율/얼굴, 상표 최종 명칭과 미확인 권리 조건, 외주 예산·업체·계약/권리 양도·수정 범위, 비공개 에셋 저장소/협업자 범위, 필요 라이선스·출시 AI 표시 검토. 모든 지출·발주·구매는② 이후다. 인간 아티스트 외주가 권장 경로이며160~280h/4~7주는 견적이 아닌 계획 가설이다.
- **의존·리스크**: V-08 소스 스켈레톤/애니메이션·라이선스, WP-12 사진, D-010 그림자 수신체, WP-13 발소리 세트키, WP-15 저장. 작은 비율의 성인 모캡/관통, 동기 로드 히치/피크VRAM, AI 컨셉의 정합과 권리 한계를 검증한다.
- **이번 병합의 사용자 예외**: “너가 알아서 머지하고 다음 작업 이어가” 및 “설계 부분 문제없는지 자체 리뷰하고 머지해” 지시로 #22/#23에 한해 Astra 자체 리뷰·병합을 승인했다. Fable 리뷰를 완료했다고 기록하지 않는다. 상시 역할 규칙과 최종 엔진 품질 판정·② 승인 절차는 그대로다.
- 근거: [WP-18 설계·리뷰](plan/WP-18-characters.md), [컨셉](design/character-concept.md), [제작 사양/비용·권리](research/11-character-pipeline.md). V-08 추가 시험은 WP-18 마지막 문안의 실제 머리/팔다리 프록시·145/380cm/s·턴/25cm계단·발 미끄러짐/관통·자연스러움/귀여움 채점을 따른다.

### D-019 | 승인 | 2026-09-27 — 자율 진행 규칙: 되돌릴 수 없는 일에만 소유자 승인을 묻는다

- **소유자 지시 원문**: "되돌릴 수 없는 작업이 아니면 소유자 승인 여부 묻지 말고 끝까지 진행하도록 하고, 이를 규칙으로 명시해둬." (PR #28 병합 승인과 함께, Claude 오케스트레이터 세션.)
- **승인이 필요한 것(되돌릴 수 없는 일)**: ① 지출·구매·구독·계약·발주(사운드 라이브러리, 모션 팩, 외주, PC 업그레이드, D-018 ②의 예산·계약 포함) ② 라이선스·법적 약정(약관 동의, 계정 가입, 권리 양도, 출시 표시) ③ 외부 공개·발송(저장소 공개 범위·라이선스 변경, 릴리스·배포, 외부 업체 문의 발송, 블러 전 데이터·개인정보의 외부 업로드 — D-007) ④ 공유 브랜치의 이력 재작성·삭제(force-push, rebase, 브랜치·태그 삭제, `pc/*`·`astra/*` 리셋)와 LFS 에셋·원본 촬영물·데이터 삭제 ⑤ 되돌리기 비용이 큰 스택·데이터 소스 변경(엔진 버전, 재구성 파이프라인 교체, 유료 API) ⑥ 실제 사람에 관한 일(초상·동의·의뢰서 발송).
- **묻지 않고 끝까지 진행하는 것**: PR 병합(Claude WP·Astra PR 모두 — 리뷰 (A) 해소·CI 초록·충돌 없음이면 바로), 설계 결정(D-0xx 제안의 채택 여부는 오케스트레이터가 근거와 함께 정한다 — 게임 설계 판단은 Fable, 코드는 Opus ultracode), 무료·되돌릴 수 있는 에셋 채택(CC0 사운드, 프록시, 플레이스홀더), PC 세션 카드 발행, Astra 과제 배정·큐 변경, 문서·코드·CI 변경, 세션 생성. 라이선스 원문을 확인할 수 없는 에셋(클라우드 403)은 채택하지 않고 소유자에게 **원문 확인**을 요청한다(승인이 아니라 사실 확인).
- **기록·번복**: 오케스트레이터 결정은 이 문서에 "오케스트레이터 결정(D-019)"으로 날짜·근거와 함께 적고, STATUS "결정 필요"에는 되돌릴 수 없는 항목만 남긴다. 소유자는 언제든 뒤집을 수 있고, 뒤집으면 되돌리는 작업을 최우선으로 한다. 승인 표식 `[소유자 승인]`(AGENTS.md §10)은 되돌릴 수 없는 일이 얽힌 PR에만 쓴다.
- **기존 대기 항목 재분류(2026-09-27)**: PR #28·#32 병합 승인 → 불필요(#28은 승인과 함께 병합, #32는 (A) 수정 확인 뒤 바로 병합) · WP-13 CC0 7개 청취 후보 → **오케스트레이터 결정: 채택**(무료·되돌릴 수 있음; 13b에서 반입해 V-10 청취, 소유자가 청취 뒤 교체 가능), BOOM 등 유료 구매 → 소유자(보류) · D-010 환경 표현 방식 → 스파이크 결과로 오케스트레이터(Fable)가 결정·기록, 유료 도구·데이터 구매가 얽힌 부분만 소유자 · night look-dev 조합(D-010 뒤) → 오케스트레이터 · V-08 §5 채점 → Fable이 PC 결과로 채점·기록하되 소유자 채점이 있으면 그것이 우선; GASP·Fab EULA·UE EULA 원문 확인은 소유자 사실 확인 항목 유지 · D-018 ②(예산·계약·권리·출시 표시)·사운드 라이브러리·모션 팩 구매·저장소 공개 범위·라이선스 → 소유자 유지.
- **오케스트레이터 결정(D-019, 2026-09-28)**: WP-13 Audio↔Lighting/Debug 레인 간 연결은 **이벤트 방식**(Tick 관측 아님) — `AGolmokTimeOfDay`에 네이티브 멀티캐스트 델리게이트 `OnPresetChanged(FName, bool)`·`OnInteriorChanged(bool)`, `UGolmokDebugSubsystem`에 HUD 줄 공급자 `ExtraHudLineProviders`를 Astra가 `[WP-13 hook]` 블록으로 추가하도록 허용(Lighting/·Debug/ 4파일 한정, 별도 커밋, 추가만). 근거: 크로스페이드가 프리셋 전환과 같은 프레임에 시작해야 하고 WP-13 스펙 5번이 델리게이트 구독을 요구하며, Debug/가 Audio/를 include하지 않게 하려면 등록 방식이 맞다. Freesound 계정 가입은 약관 동의라 소유자 항목으로 남기고 13b는 플레이스홀더로 진행(이슈 #30 2026-09-28 00:13Z). **보완(2026-09-28, T6 PR #50)**: HUD 줄 공급자는 배열 필드가 아니라 핸들 API `AddExtraHudLineProvider/RemoveExtraHudLineProvider/NumExtraHudLineProviders`(`FDelegateHandle` 키, 멱등 제거)로 바뀌었다 — 같은 `[WP-13 hook]` 블록 안, 다른 레인은 이 API로 등록한다.
- **오케스트레이터 결정(D-019, 2026-09-28)**: WP-14 분할(14a 먼저, 14b는 D-010 뒤) — D-015 항목 참조.
- **오케스트레이터 결정(D-019, 2026-09-28)**: WP-15 분할(15a 이동·세이브·스키마 먼저, 15b 지도 UI는 D-009 자문·실제 zone 뒤) — D-014 항목 참조.
- 반영: CLAUDE.md 소유자 규칙, DEVELOPMENT-PLAN §2·§7.6, AGENTS.md 소유자 원칙·§10, STATUS 결정 필요, astra-tasks.md.

### D-020 | 승인 | 2026-09-29 — 모델 정책: 모든 작업을 Opus로

- **소유자 지시 원문**: "지금부터 모든 작업 OPUS 로 해" (2026-09-29, 오케스트레이터 세션에서 `/model claude-opus-5-5` 전환과 함께).
- **내용**: 코딩·리뷰·검증뿐 아니라 게임 설계(설계 패널·"설계 (확정)" 절), 게임성·비주얼 품질 판단(룩 검증·스파이크 판정·폴리시 결정·D-0xx 제안), Astra PR의 설계 리뷰, 조사·문서·단순 도구, 오케스트레이션·병합까지 모두 Claude Opus 5.5로 한다. 코딩은 계속 ultracode(구현 → 적대적 검증). 다른 모델로 세션·서브에이전트를 만들지 않는다. 2026-09-27 모델 정책(코딩 Opus / 설계 Fable)과 D-019 본문의 "게임 설계 판단은 Fable" 문구를 대체한다.
- **관례**: 병합 시 반영 커밋 제목은 앞으로 `WP-NN: 병합 시 반영 (Opus)`, PC 결과의 클라우드 병합 브랜치는 `V-xx: 병합 시 반영 (Opus)`로 한다. 이전 커밋의 `(Fable)`은 그대로 둔다.
- **이력**: 세션 로그·병합 기록에 적힌 "Fable 5.1" 판단(WP-13 T8 오디오 폴리시, WP-14a §2a, WP-15a, WP-12 keep-height 슬라이드, V-12 채점표 등)은 기록대로 두고, 다시 판단할 일이 생기면 Opus가 한다.
- 반영: CLAUDE.md 모델 정책·Astra 절, DEVELOPMENT-PLAN §7.4·§7.6(표·리뷰 절차·리뷰 세션 템플릿), AGENTS.md(품질 판단·리뷰·병합 커밋), astra-tasks.md, STATUS 마지막 갱신, 이슈 #30 알림.

### D-021 | 승인(오케스트레이터 결정, D-019) | 2026-09-30 — 캐릭터 로코모션: GASP Motion Matching 방향 채택
- **근거**: V-08(PC, [PR #21](https://github.com/wooklym/golmok/pull/21), [런북 §8](runbooks/pc-verify-animation.md)). GASP 자체 CMC 폰 ②b는 ① 현행(매니+`ABP_Unarmed`)보다 디딘 발 미끄러짐이 S1·S2에서 약 1/4, S4에서 −16 %였다. 1080p 성능 차이는 없었다(181.0 → 183.1 fps, 게임 스레드 +0.84 ms). 채점은 ① 16 / ②b 21(PC 세션 Opus, 소유자 채점 우선). 단 ②b는 런북 §3-4 조건 밖(GASP 폰·카메라·이동 값)의 **품질 상한**이다. 우리 C++ 폰에 설정만 붙인 ②a는 폰 인터페이스(`BPI_SandboxCharacter_Pawn`)가 없어 작동하지 않았다. 병합 리뷰 R21(Opus)은 방향 채택 근거로는 충분하지만 채택 판정은 통합본으로 다시 해야 한다고 봤다.
- **결정**: ② GASP Motion Matching 로코모션을 **방향으로 채택**한다. 퀄리티 최우선 원칙에 맞고 되돌릴 수 있다. 발효는 소유자의 라이선스 원문 재확인 뒤다(CLAUDE.md: 클라우드에서 원문을 확인할 수 없는 에셋은 소유자 사실 확인 전 채택하지 않는다). 그 전의 통합 작업은 GASP 콘텐츠 없이 우리 코드·도구만 다룬다. 최종 기본값 전환(`manny` 기본 ① → ②)은 WP-19 통합본이 V-15 사전 등록 기준을 통과한 뒤에 한다.
  - V-15 기준: 같은 메시·같은 카메라·블라인드 채점. 합계 ≥ ① + 4, ≥ ②b − 2. S1·S2 미끄러짐 ≤ ①의 1/2. S3은 돌아서기로 측정. 평균 fps 하락 5 % 이하 또는 60 fps 이상.
  - 미통과 시: ① 기본을 유지한다. ②는 설정 옵션으로 남기고 B안(GASP 데이터 + 우리 ABP)을 검토한다.
- **되돌릴 수 있게**: GASP 원본은 **수정하지 않고 저장소 밖**에 둔다. 공개 저장소 커밋 금지(Fab EULA §5(a)). 기본안은 각 PC가 Fab에서 받아 스크립트로 복사하는 방식이다(`add-mannequin.ps1` 패턴). ① 경로는 상시 폴백으로 유지하고, ①↔②는 설정으로 전환한다. GASP가 없는 클론·CI에서도 빌드·테스트가 통과해야 한다.
- **이동 감각**: 최고 속도(걷기 180·달리기 500, 로스터별 145/380 등), 돌아서기(orient-to-movement), 점프 90 cm는 **유지**한다. GASP의 걷기 200·뒷걸음·넘기(traversal)는 채택하지 않는다. **가감속만** V-08b A/B로 정한다. 후보는 P0 현행·P1 중간·P2 GASP이고, 규칙은 미리 정한다. S1·S2 미끄러짐이 ①의 1/2 이하이고 1~5 합이 가장 높은 프로파일을 고른다. 동점이면 빠른 쪽을 고르고, 조작감 2 이하는 탈락이다.
- **Experimental 허용 범위**: 무수정 GASP 로코모션 에셋이 참조해서 켜야 하는 플러그인과 그 의존 플러그인만 허용한다. 기록상 PoseSearch·Chooser·AnimationWarping·MotionWarping(Beta)·AnimationLocomotionLibrary(Beta)·BlendStack·CurveExpression·DrawDebugLibrary·MovieSceneAnimMixer·Mover이고, Offset Root Bone 노드도 포함한다. 조건은 다섯 가지다.
  1. 우리 C++ 모듈은 이들에 의존을 추가하지 않는다(에셋 참조만).
  2. 이동은 CMC 그대로 둔다(Mover 이동 시스템 불채택).
  3. Development·Shipping 패키지 스모크를 통과한다.
  4. `.uplugin` 플래그 표를 기록한다(V-08b).
  5. 엔진 버전을 바꿀 때 재검증한다.
  - 불허: GameplayCameras, Mover 폰·ChaosMover, 넘기·SmartObjects·GameplayInteractions·Locomotor, MetaHuman·LiveLink·RigLogic·HairStrands, `MotionMatchMulti`·UAF. research/09 §5의 Mover 문장은 이 범위로 바꿨다.
- **후속**:
  - **V-08b**(PC 실험, 코드 변경 없음, GASP 폰 그대로): 이동 값 A/B, 돌아서기 모드, Manny·4.5등신 리타깃(D-018 V-08 추가 시험), Offset Root Bone 거리·80 cm 통로·포토 구도·포털, `.uplugin` 플래그 표, 폴리 노티파이, 패키지 스모크, 드라이버·지표 스크립트 `tools/` 커밋, 블라인드 채점.
  - **WP-19**(통합): 1단계 클라우드(Claude 레인)는 상태 공급 컴포넌트·폴백·셋업 스크립트·경로 가드, 2단계 PC GUI는 인터페이스 구현 BP, 3단계 Astra는 로스터 GASP 항목·노티파이 구동 발소리와 GASP 폴리 비활성이다.
  - **V-15**: 통합 검증.
  - 병합 리뷰 R21 (B) 7~12는 V-08b·WP-19에 넣는다.
- **진행 기록**:
  - 2026-09-30: WP-19a [#76](https://github.com/wooklym/golmok/pull/76)·19c T12 [#77](https://github.com/wooklym/golmok/pull/77)·19a-2 [#78](https://github.com/wooklym/golmok/pull/78) 병합. 기본은 여전히 ①(`animation.json` mode abp)이다.
  - 2026-09-30 오케스트레이터 결정(D-019, 되돌릴 수 있음; 리뷰 R77·R78·R79): (1) 원본 GASP 발 폴리는 19b BP가 `footsteps.driver`와 **무관하게** 끄고 Step·Land만 `NotifyFootEvent`로 보낸다. Golmok 폰의 발소리 소스는 `audio.json` 하나로 둔다(D-016/D-002 크레딧 파이프라인과 일관, distance 진단에서도 이중 재생 없음; R79-2). 점프 발성·옷 스침 같은 발 이외 폴리는 V-08b §5 기록 뒤 따로 판단하며 그 전에는 쓰지 않는다. (2) 발소리 auto 판정은 GASP 폰 클래스가 아니라 `GetMesh()` 애님 클래스가 GASP ABP인지로 한다(R79-1, Astra T15; N초 무이벤트 폴백은 19b 연결 누락을 가려 기각). (3) 19b가 확정한 GASP 경로의 `characters.json` 반영은 Astra 후속 과제로 배정하고 19b PC 세션은 이 파일을 고치지 않는다(R77-1). (4) preview와 로스터의 시각 메시 ABP 규칙은 `TargetSkeleton`이 없는 템플릿도 받는 것으로 통일하고, 19b에서 `ABP_GenericRetarget` 값을 확인한 뒤 다시 판단한다(R78-2·R77-13).
- **소유자 항목**(STATUS 결정 필요):
  - 라이선스 원문 재확인(사실 확인). Fab EULA NoAI 정의와 AI 에이전트 작업 흐름의 관계, Personal/Professional 티어, GASP 설정 파일(ini)이 Content에 드는지, GASP를 참조만 하는 우리 에셋을 공개 저장소에 커밋해도 되는지를 함께 본다.
  - 비공개 에셋 저장소 여부(D-018 ②와 같은 결정).
  - (선택) 녹화 재채점.
- 이 결정은 소유자가 언제든 뒤집을 수 있다.
