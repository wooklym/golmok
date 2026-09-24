# 07. UE5 툴체인 검증 (D-003 변경 후속)

조사일: 2026-09-24
표기: **[확인]** 1차 출처(공식 문서, 소스코드, 가격 페이지) / **[2차]** 기사·커뮤니티 / **[미확인]** 확인 불가 또는 추정. "권장"은 엔지니어링 판단.

## 요약

1. **엔진 고정: UE 5.8.3 (Launcher 바이너리) + Cesium for Unreal 2.29.x**
   - UE 5.8은 UE5의 마지막 예정 메이저다 [2차]. Cesium 2.29는 UE 5.6~5.8을 지원한다 [확인]. XGRIDS LCC도 5.1~5.8을 지원한다 [확인].
2. **Cesium for Unreal의 splat은 조명을 받지 않는다.**
   - 소스에서 `M_CesiumSplatMaterial = MSM_Unlit + BLEND_Translucent`를 직접 확인했다 [확인].
   - 따라서 동적 조명, 캐릭터 그림자 수신, 그림자 드리우기, depth 쓰기가 모두 없다.
   - → 스파이크 (b)는 **근경에서는 불리할 것으로 예상**한다. 원경이나 지오 컨텍스트 용도로는 여전히 유효하다.
3. **Postshot의 UE 플러그인은 게임 배포에 쓸 수 없다.**
   - 공식 문서: "패키징된 UE 프로젝트 사용 시 Postshot 앱 설치 필요" [확인].
   - → Postshot은 **학습과 .ply/.spz 내보내기 전용**으로 쓴다. UE 렌더링은 다른 플러그인이 맡는다.
4. **splat에 캐릭터 그림자를 받는 가장 성숙한 경로는 XGRIDS LCC4Unreal의 LCC2 파이프라인 + Lit + ProxyMesh**다 [확인: 공식 docs v3.3.1].
   - ProxyMesh가 GBuffer에 depth, 노멀, 머티리얼을 쓰므로 엔진 조명, VSM 그림자, 반사를 그대로 받는다.
   - **일반 .ply(Postshot/gsplat)를 입력으로 받는다.** XGRIDS 스캐너 데이터가 아니어도 된다.
   - Pro는 현재 "한시적 무료"다. 게임 배포 라이선스 조건은 [미확인]이므로 XGRIDS에 문의해야 한다.
5. **Postshot은 Windows + NVIDIA 전용이다** [확인]. **RunPod은 Linux 컨테이너만 제공한다** [2차]. → **RunPod에서는 Postshot을 돌릴 수 없다.** 대안은 D-006을 참고한다.
6. **UE로 출시된 splat 기반 상용 게임은 찾지 못했다** [미확인]. 사실적인 스캔 기반 게임(Unrecord, Bodycam)은 **포토그래메트리 메시 + UE5** 조합이다. → 스파이크 (a) 메시 경로가 **검증된 기준선**이다.

## 1. 엔진·버전

| 항목 | 내용 | 표기 |
|---|---|---|
| UE 최신 | 5.8 (2026-06 출시), 핫픽스 5.8.3 (2026-09-22) | [확인] https://forums.unrealengine.com/t/5-8-3-hotfix-released/2833315 |
| UE 5.8 주요 기능 | MegaLights 정식, Lumen Lite, Nanite 개선. **네이티브 splat은 없음** | [2차] |
| Cesium for Unreal | v2.29.1 (2026-09-01), UE 5.6 이상 필수, UE 5.8은 v2.28부터 지원 | [확인] https://cesium.com/learn/cesium-unreal/ref-doc/changes.html |
| XGRIDS LCC | 바이너리 플러그인이라 **Epic 배포 엔진에서만 동작**한다. 소스 빌드 엔진을 쓰면 별도 빌드가 필요 | [확인] |

→ **Launcher 버전 UE 5.8.3**을 쓴다. 엔진 소스는 수정하지 않는다. 게임 로직은 프로젝트 C++ 모듈로 만든다.

## 2. 개발용 로컬 PC 사양

근거:
- Epic 공식 요구사항 [확인]: Windows 11, RAM 32GB, Nanite/Lumen에는 RTX 2000 이상, **Visual Studio 2026**. https://dev.epicgames.com/documentation/en-us/unreal-engine/hardware-and-software-specifications-for-unreal-engine
- Puget Systems [2차]:
  - C++ 컴파일은 코어 수에 비례한다.
  - RealityScan RAM은 이미지 2천 장에 16GB, 4천 장에 32GB, 8천 장에 64GB가 필요하다.
- Postshot은 NVIDIA CC 7.5 이상이 필수다 [확인].

| 구분 | 최소 | **권장** | 이상적 |
|---|---|---|---|
| CPU | Ryzen 7 9700X (8C) | **Ryzen 9 9950X (16C)** | Threadripper 9970X (32C) |
| RAM | 64GB DDR5 | **128GB DDR5** | 256GB |
| GPU | RTX 5070 Ti / 4070 Ti Super 16GB | **RTX 5090 32GB** | RTX PRO 6000 Blackwell 96GB |
| 저장장치 | NVMe 2TB | **NVMe 3개 구성**: OS·엔진 2TB / 프로젝트 4TB / DDC·RealityScan 캐시 2TB (Gen4 이상) | 권장 구성 + 원본 보관용 NAS(10GbE) |
| 백업 | 외장 HDD 2개 | 외장 2개 + 클라우드 비공개 버킷 | NAS + 클라우드 |
| OS·도구 | Windows 11, VS 2026, Git + Git LFS | 좌동 | 좌동 |
| 모니터 | – | 27" 1440p 이상, sRGB 보정 | 4K + 보정 장비 |

- GPU는 **NVIDIA를 쓴다**. Postshot, 대부분의 splat 플러그인, DLSS가 NVIDIA 기준이다.
- **권장 사양이면 RealityScan과 Postshot을 로컬에서 최고 설정으로 돌릴 수 있다**(VRAM 32GB). 이 경우 클라우드는 보조가 된다(D-006 참고).

## 3. RealityScan 2.x

| 항목 | 내용 | 표기 |
|---|---|---|
| 최신 | 2.2 (2026-06). AMD GPU 지원(Windows) | [확인] https://dev.epicgames.com/documentation/realityscan/release-notes |
| GPU | 메시·텍스처 생성에 CUDA 필요(CC 3.5 이상, 권장 6.1 이상) | [확인] |
| 라이선스 | 연매출 $1M 미만 무료, 초과 시 $1,250/석·년 | [2차] 공식 페이지는 로그인 필요 |
| Linux | 2.1 이상, **CLI 전용, Wine 기반 "experimental"**, NVIDIA 8GB 이상 | [확인] https://dev.epicgames.com/documentation/realityscan/realityscan-for-linux |
| 내보내기 | OBJ/FBX/GLB/USD 등. 텍스처는 단일 또는 **UDIM 타일**, 최대 65536 | [확인] |
| 지오레퍼런싱 | GCP, 컨트롤 포인트, GPS prior | [확인] |
| 영상 입력 | 키프레임 추출(기본 1초당 1프레임) | [확인] |
| 마스크 | 2.0부터 AI 마스킹 | [확인] |
| splat 연계 | COLMAP/XMP 포즈 내보내기 → Postshot 입력 | [확인] |

**UE/Nanite용 권장 내보내기** (판단)
- 골목을 **10~20m 청크**로 나눈다. 청크당 5~15M 삼각형으로 Simplify한다.
  - 청크로 나누는 이유: LFS 2GB 제한, 스트리밍, 편집 편의.
- 텍스처는 청크당 **8K UDIM 여러 장**으로 내보내고, UE에서 **Virtual Texture**로 임포트한다.
- 좌표: RealityScan에서 GPS/GCP로 좌표를 잡는다. 로컬 원점 기준으로 내보낸 뒤 `CesiumGeoreference`와 `CesiumGlobeAnchor`로 배치한다.
- **Delighting**(텍스처에 구워진 조명 제거)은 Lumen 동적 조명 품질의 핵심이다. 흐린 날 촬영(가이드 #1 §2)이 1차 대책이고, 스파이크에서 delight 도구를 평가한다.

## 4. Postshot

| 항목 | 내용 | 표기 |
|---|---|---|
| 플랫폼 | **Windows 10 이상 + NVIDIA CC 7.5 이상 전용**, macOS·Linux 없음 | [확인] https://www.jawset.com/ |
| 요금 | Indie €17/월(상업 사용, PLY/SPZ 내보내기), **Studio €39/월(CLI, 4K 초과 이미지, AprilTag)** | [2차] 공식 가격 페이지 404 |
| CLI | `postshot-cli.exe`: `-s`(스텝), `--max-image-size 0`(축소 없음). **compute-only 데이터센터 GPU에서도 학습 가능** | [확인] https://www.jawset.com/docs/d/Postshot+User+Guide/Command-line+Interface |
| 학습 설정 | 프로파일 Splat3(권장)/MCMC. Max Splat Count, Limit Image Size, SH Degree 0~3, Anti-Aliasing, Sky Model, Photometric Compensation | [확인] |
| 입력 | JPG/PNG/TIF/EXR/**DNG/RAW**, MOV/MP4 영상, 마스크, COLMAP/RealityScan 임포트 | [확인] |
| 내보내기 | PLY, SPZ | [2차] |
| UE 플러그인 | **배포 불가**(최종 사용자 PC에 Postshot이 설치돼 있어야 함) | [확인] https://www.jawset.com/docs/d/Postshot+User+Guide/Unreal+Engine+Integration |

**"학습 해상도·반복 수를 줄이지 않는다" 설정**
- `--max-image-size 0`(원본 해상도). 4K를 넘는 이미지는 **Studio** 요금제가 필요하다.
- SH Degree 3, Anti-Aliasing 켬.
- 스텝은 자동 추정값 이상으로 두고, 품질이 수렴할 때까지 늘린다.
- Max Splat Count는 VRAM이 허용하는 최대값으로 둔다.

## 5. Cesium for Unreal splat (스파이크 (b))

| 항목 | 내용 | 표기 |
|---|---|---|
| 렌더링 | Niagara 스프라이트, ViewDepth 정렬, compute 셰이더 | [확인] 소스 |
| 머티리얼 | **Unlit + Translucent** → 조명과 그림자 없음, depth 안 씀 | [확인] 소스 |
| 공식 안내 | "색은 데이터셋의 뷰 의존 색이며, 조명 변화에 메시처럼 반응하지 않음", 모션블러·AO·DOF 끄기 권장 | [확인] https://cesium.com/learn/unreal/3d-gaussian-splat-tilesets-lods/ |
| 3D Tiles 만들기 | (1) Cesium ion에 PLY 업로드(`gaussianSplats: true`) [2차] (2) 오픈소스 3DGS-PLY-3DTiles-Converter [2차] | |

- ⚠️ 방법 (1)은 Cesium ion 서버에 데이터를 올리는 것이다. MVP는 비공개 원칙(D-007)이고 원본에 얼굴·번호판이 있다. 그래서 **블러 처리한 결과만 올리거나, 로컬 변환기를 우선**한다.
- ⚠️ Cesium ion Community 요금제는 비상업이다(01 문서). 스파이크 평가 용도로만 쓴다.

## 6. 서드파티 UE splat 플러그인 (스파이크 (c))

| 플러그인 | 입력 | 조명·그림자 | 가격 | 판단 |
|---|---|---|---|---|
| **XGRIDS LCC4Unreal v3.3.1** | LCC/LCC2, **일반 PLY**, SOG, SPZ | **Lit(deferred) + ProxyMesh로 GBuffer 기록 → 엔진 그림자·반사**. depth 출력, 전역 정렬, 충돌·NavMesh, Cesium 연동 | Free + Pro(한시적 무료) | **1순위** [확인] https://github.com/xgrids/LCC-3DGS-Unreal-Plugin |
| Volinga Plugin Pro | PLY/SPZ/SOG | 기본판은 그림자 수신만. Pro는 프록시 기반 재조명과 그림자 드리우기 | 약 €120~400+/년 | 2순위 [2차] |
| 3D Gaussians Plugin (Akiya) | PLY | Masked Lit 그림자 수신(experimental) | 1회 구매 | 참고 |
| NanoGS | PLY | 조명 관련 언급 없음, Nanite식 LOD | 무료 | 성능 참고 |
| Postshot 플러그인 | .psht | – | – | **배포 불가** |
| Luma | – | – | – | **지원 종료** |

## 7. 하이브리드 구조 (스파이크 결과 전 가설)

1. **RealityScan Nanite 메시(청크)가 기본 레이어**다. 충돌, 그림자, Lumen 표면, NavMesh, 정합 기준을 맡는다.
2. **splat은 메시가 약한 부분에만 겹친다**: 전선, 철망, 식생, 간판 가장자리, 유리. XGRIDS 클리핑 볼륨으로 겹치는 영역을 잘라낸다. **같은 메시를 ProxyMesh로 재사용**해 splat도 그림자를 받게 한다.
3. **숨김 그림자 프록시**(Epic 공식 기법): `bCastHiddenShadow`, Render in Main Pass 끄기 [확인] https://dev.epicgames.com/documentation/en-us/unreal-engine/proxy-geometry-shadows-in-unreal-engine
4. 원경은 LOD1 배경 + 원경 안개 + 조명으로 처리한다(D-004). Cesium splat은 원경 후보로 평가만 한다.

## 8. 버전 관리 (Git LFS)

- GitHub LFS 무료 할당량은 저장 10GiB, 대역폭 10GiB다(Free/Pro). 초과하면 저장 $0.07/GiB·월, 다운로드 $0.0875/GiB다. **파일당 최대 크기는 Free/Pro 2GB** [확인] https://docs.github.com/en/billing/concepts/product-billing/git-lfs
- `.gitattributes`에서 `*.uasset`, `*.umap`을 `lockable`로 지정한다. UE 에디터에서는 ProjectBorealis UEGitPlugin(Git LFS 2)을 쓴다 [확인] https://github.com/ProjectBorealis/UEGitPlugin
- **원본 사진·영상, RealityScan 프로젝트, .ply 원본은 git에 넣지 않는다.** 이것들은 외장 디스크와 비공개 버킷에 둔다(D-005 보관 원칙). git에는 UE 에셋과 게임용 파생물만 둔다.
- 대안: Diversion(무료 5명, 100GB, UE 공식 플러그인), Perforce(무료 5명). 인원이 늘면 재검토한다.

## 9. GPU 클라우드 (2026-09 조회)

| 제공사 | 사양 | 가격/h | Windows | 용도 |
|---|---|---|---|---|
| RunPod [확인] | L40S | $0.79~1.09 | **불가** | Phase 2 gsplat, 변환 작업 |
| RunPod | RTX PRO 6000 | $1.69~2.09 | 불가 | 좌동 |
| RunPod | H100 SXM | $2.69~3.49 | 불가 | 좌동 |
| **AWS g6e.xlarge (서울)** [확인] | L40S 48GB, 4vCPU/32GB | $2.288 + Windows 라이선스 | **가능** | Postshot CLI(Studio) |
| **AWS g6e.4xlarge (서울)** [확인] | L40S, 16vCPU/128GB | $3.69 + Windows 라이선스 | **가능** | RealityScan + Postshot |

## 출처
- UE: https://dev.epicgames.com/documentation/en-us/unreal-engine/hardware-and-software-specifications-for-unreal-engine , https://forums.unrealengine.com/t/5-8-3-hotfix-released/2833315 , https://dev.epicgames.com/documentation/en-us/unreal-engine/proxy-geometry-shadows-in-unreal-engine
- Cesium: https://cesium.com/learn/cesium-unreal/ref-doc/changes.html , https://github.com/CesiumGS/cesium-unreal , https://cesium.com/learn/unreal/3d-gaussian-splat-tilesets-lods/ , https://cesium.com/blog/2026/04/27/3d-gaussian-splats-lod/ , https://community.cesium.com/t/converting-3dgs-ply-to-3d-tiles-via-cesium-ion-rest-api/42003/7 , https://github.com/WilliamLiu-1997/3DGS-PLY-3DTiles-Converter
- RealityScan: https://dev.epicgames.com/documentation/realityscan/release-notes , https://dev.epicgames.com/documentation/realityscan/hardware-and-software-requirements?lang=en-US , https://dev.epicgames.com/documentation/realityscan/realityscan-for-linux , https://rshelp.capturingreality.com/en-US/tools/export.htm , https://rshelp.capturingreality.com/en-US/tutorials/georeferencing.htm , https://www.cgchannel.com/2025/11/epic-games-releases-realityscan-2-1/
- Postshot: https://www.jawset.com/ , https://www.jawset.com/docs/d/Postshot+User+Guide/Command-line+Interface , https://www.jawset.com/docs/d/Postshot+User+Guide/Interface/Training+Configuration , https://www.jawset.com/docs/d/Postshot+User+Guide/Unreal+Engine+Integration , https://radiancefields.com/platforms/postshot
- 플러그인: https://github.com/xgrids/LCC-3DGS-Unreal-Plugin , https://web.volinga.ai/volinga-plugin-pro/ , https://www.cgchannel.com/2026/08/volinga-plugin-pro-lets-you-relight-4dgs-data-inside-unreal-engine/ , https://akiya-research-institute.github.io/3dGaussiansPlugin-Manual/en/ , https://www.cgchannel.com/2026/03/free-plugin-nanogs-puts-nanite-style-gaussian-splatting-in-unreal-engine/
- 사례: https://gdcvault.com/play/1035516/Gaussian-Splatting-with-Unreal , https://www.pcgamer.com/hardware/this-photorealistic-fps-runs-in-browser-thanks-to-gaussian-splatting-which-is-now-my-new-favorite-thing/
- Git LFS: https://docs.github.com/en/billing/concepts/product-billing/git-lfs , https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage , https://github.com/ProjectBorealis/UEGitPlugin , https://www.diversion.dev/pricing
- 하드웨어: https://www.pugetsystems.com/solutions/game-dev-workstations/unreal-engine/hardware-recommendations/ , https://www.pugetsystems.com/solutions/photogrammetry-workstations/realityscan/hardware-recommendations/
- 클라우드: https://www.runpod.io/pricing , https://lambda.ai/pricing , https://instances.vantage.sh/aws/ec2/g6e.xlarge , https://medium.com/@airrender/windows-on-runpod-what-we-tried-why-it-fails-bb1d045b03d4
