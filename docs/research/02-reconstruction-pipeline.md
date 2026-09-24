# 02. 사진·영상 기반 3D 재구성 파이프라인

조사일: 2026-09-24
표기: **[검증]** 1차 출처(LICENSE 원문, 공식 문서, 가격 페이지)에서 직접 확인 / **[2차]** 기사·리뷰로만 확인 / **[미검증]** 확인 못 했거나 추정

> **핵심 결론**
> 1. **Inria 원본 3DGS 코드와 그 파생 연구 코드 대부분은 비상업 라이선스라 쓸 수 없다.** 해당: 2DGS, SuGaR, GOF, MILo, Mip-Splatting, Octree-GS, Hierarchical-3DGS, CityGaussian, PGSR.
> 2. 상용으로 안전한 스택은 다음과 같다.
>    - SfM: **COLMAP 4.x**(BSD, GLOMAP 통합) + **ALIKED/DISK + LightGlue**
>    - 학습: **gsplat**(Apache 2.0)
>    - 포맷: **SPZ / SOG**(MIT)
>    - 충돌 메시: **Open3D TSDF**(MIT) + **CoACD / V-HACD** + **Recast**(zlib)
> 3. feed-forward 모델(MASt3R/DUSt3R, Pi3, Depth-Anything-V2 Base 이상, SuperPoint/SuperGlue)은 **가중치가 비상업**이다. 예외는 `VGGT-1B-Commercial`(신청 필요)과 `map-anything-apache`뿐이다.

---

## 1. SfM / 카메라 포즈

| 도구 | 라이선스 | 상용 | 비고 |
|---|---|---|---|
| **COLMAP 4.x** | BSD [검증] | **Y** | 4.0.0(2026-03)에서 GLOMAP을 `global_mapper`로 통합했다. 4.2.0(2026-08)에서 multi-component global mapping이 추가됐다. ALIKED와 LightGlue(ONNX)를 내장한다. |
| GLOMAP(독립 repo) | BSD | Y | deprecated 상태로, 이후 유지보수는 COLMAP에서 한다 [검증]. |
| hloc | Apache 2.0 | 조건부 | **SuperPoint/SuperGlue 가중치는 비상업**이다 [검증]. DISK 또는 ALIKED + LightGlue 조합만 쓴다. |
| OpenMVG | MPL-2.0 | Y | 파일 단위 copyleft. |
| OpenMVS | **AGPL-3.0** | 조건부 | 서버 서비스로 쓰면 소스 공개 의무 리스크가 있다. |
| Meshroom/AliceVision | MPL-2.0 | Y | |
| RealityScan 2.x (Epic) | 독점 EULA | Y | 연매출 100만 USD 미만은 무료, 초과 시 $1,250/seat/년 [2차]. **서버 자동처리가 허용되는지는 [미검증]**이다. |
| Metashape | 독점 | Y | Pro $3,499. **서비스로 통합하려면 Service Provider License**가 별도로 필요하다(연 $6,736/대 또는 종량제) [검증]. |
| VGGT | VGGT License | Commercial 체크포인트만 Y | [검증] |
| MASt3R/DUSt3R | CC BY-NC-SA | **N** | [검증] |
| MapAnything | 코드 Apache | `-apache` 가중치만 Y | [검증] |
| Pi3 | 가중치 CC BY-NC | **N** | [검증] |

**선택**: 서버 SfM은 **COLMAP 4.2**로 한다. 적용 방식은 다음과 같다.
- 영상: `sequential_matcher` + loop detection
- 다중 세션: vocab tree
- 대규모 재구성: `global_mapper`
- 자체 앱이 기록한 ARKit/ARCore 포즈와 GPS는 `pose_prior_mapper`의 prior로 넣는다.

## 2. Gaussian Splatting 학습기

| 도구 | 라이선스 | 상용 | 비고 |
|---|---|---|---|
| Inria 3DGS 원본 | 비상업 [검증] | **N** | 원문: "CANNOT USE, EXPLOIT OR DISTRIBUTE THE SOFTWARE FOR COMMERCIAL PURPOSES" |
| **gsplat** | **Apache 2.0** [검증] | **Y** | MCMC, antialiased, 2DGS 래스터라이저, 3DGUT(롤링셔터 대응), multi-GPU를 지원한다. ⚠️ `*_inria_wrapper` 함수는 Inria 코드이므로 **사용 금지**. |
| nerfstudio splatfacto | Apache 2.0 | Y | gsplat 기반. |
| Brush | Apache 2.0 | Y | Rust/WebGPU 기반. 클라이언트 미리보기 용도로 유망하다. |
| NVIDIA 3DGRUT | Apache 2.0 | Y | |
| OpenSplat | AGPL-3.0 | 조건부 | |
| LichtFeld Studio | GPL-3.0 | 조건부 | 내부 도구로만 쓰면 무방하다. |
| Postshot | 상용 구독 | Y(Indie 이상) | CLI는 Studio 등급 이상 [2차]. |
| CityGaussian | CC BY-NC-SA | **N** | |
| Octree-GS / Hierarchical-3DGS / Mip-Splatting | Inria 라이선스 | **N** | 아이디어만 참고한다(공간 분할, LOD). |
| SpotLessSplats | Apache 2.0 | Y | transient(움직이는 물체) 제거 |
| WildGaussians | MIT | Y | 조명 변화·transient 대응 |

### 포맷·스트리밍

| 포맷 | 상태 | 비고 |
|---|---|---|
| .ply | 사실상 표준 | 비압축이라 매우 크다. 원본 보관용. |
| **.spz** (Niantic) | MIT [검증] | PLY 대비 약 1/10 크기. |
| **SOG** (PlayCanvas) | MIT [검증] | PLY 대비 약 1/15~1/20. Streamed SOG는 LOD 청크를 스트리밍한다. |
| **.RAD** (Spark 2) | MIT [검증] | LoD splat tree, HTTP Range 스트리밍. |
| **KHR_gaussian_splatting** (glTF) | "Complete, Ratified" [검증: Khronos repo README] | 정확한 비준일은 [미검증]. SPZ 압축 확장의 비준 여부도 [미검증]. |
| 3D Tiles + splat | CesiumJS 1.139+, Cesium for Unreal [검증] | Hierarchical LOD. Unity는 미지원. |

## 3. 시각용 표현과 충돌용 지오메트리의 분리·결합 설계

걷고 뛰려면 splat만으로는 부족하다. splat에는 "표면"이 없기 때문이다. 그래서 **이중 표현(dual representation)**을 원칙으로 한다.

```
            ┌────────── 같은 로컬 좌표계(ENU, 타일 원점 기준) ──────────┐
 Visual  :  Gaussian Splat (SOG/SPZ/RAD, LOD 스트리밍)      ← 렌더링 전용
 Physics :  저폴리 collision mesh (.glb, 수천~수만 tri)      ← 렌더링 안 함
 Nav     :  navmesh (Recast, 타일 단위)                      ← AI/경로탐색
 Meta    :  portal/door, 유리면 blocker, 스폰포인트, 구역 경계 (JSON)
```

### 3.1 충돌 메시 생성 (상용 가능한 도구만 사용)

1. **깊이 확보**: gsplat에서 학습 카메라별 median depth를 렌더링한다. 2DGS 모드나 depth/normal 정규화를 쓰면 표면이 더 날카로워진다. 대안으로 COLMAP PatchMatch depth map을 쓴다.
2. **TSDF fusion**: Open3D(MIT)로 한다. 보행 충돌용 voxel은 3~5cm면 충분하다 [미검증, 경험치].
3. **정리**:
   - 작은 연결요소를 제거한다.
   - hole fill을 한다.
   - **바닥·벽을 RANSAC 평면 스냅**해 울퉁불퉁한 바닥 때문에 캐릭터가 떨리는 것을 막는다.
4. **Decimation**: quadric error 기반으로 줄인다(meshoptimizer, MIT). 목표는 블록당 1만~5만 tri.
5. **소품 분리**: 동적이거나 복잡한 소품은 **CoACD(MIT)** 또는 **V-HACD(BSD-3)**로 convex decomposition한다. 정적 지형은 trimesh collider로 둔다.
6. **Navmesh**: Recast(zlib)로 만든다. 계단 높이·경사 한계는 캐릭터 파라미터와 맞춘다.
7. **대안 경로**: PlayCanvas `splat-transform`의 voxel 기반 `.collision.glb` 생성 기능을 먼저 시험해 본다. 엔진에 종속되지 않는 CLI인지는 [미검증].

### 3.2 결합 규칙
- splat과 collision mesh는 **같은 변환 행렬(타일 로컬 → ECEF)**을 공유한다. 정합 단계에서 한 번 산출하고 둘 다에 적용한다.
- **베이스맵**(LOD1/LOD2 건물 메시)은 시각용이자 충돌용이다. 고품질 구역이 로드되면 그 **구역 경계(polygon) 안의 베이스맵 건물은 숨기고 충돌도 끈다**. 대신 구역의 collision mesh를 켠다(→ ARCHITECTURE.md의 "구역 교체" 참고).
- **유리·거울**: 3DGS는 유리 너머를 "공간"으로 재구성하거나 depth에 구멍을 남긴다. 그래서 충돌 메시에는 창·쇼윈도 위치에 **평면 blocker를 반자동으로 삽입**한다(세그멘테이션: SAM2, Apache 2.0).
- **실내↔실외 연결**: 문 위치에 `portal` 메타데이터를 둔다. 실내 splat은 portal 근처에 가거나 portal이 시야에 들어올 때만 로드한다.
- **디버그 뷰**: collision mesh를 와이어프레임으로 겹쳐 보는 토글을 클라이언트에 기본으로 넣는다(검수에 필수).

### 3.3 움직이는 객체·개인정보
- 사람·차량 마스크를 만든다(SAM2 등, Apache). 이 마스크를 (a) COLMAP 특징점 추출에서 제외(`mask_path`, [검증])하는 데 쓰고, (b) 학습 loss에서도 제외한다. (c) 필요하면 SpotLessSplats도 함께 쓴다.
- ⚠️ **Ultralytics YOLO는 AGPL**이다 [검증]. 서버 파이프라인에서는 피한다.
- 얼굴·번호판 블러는 **재구성 전 원본 이미지 단계**에서 한다. splat의 색은 학습 이미지에서 오기 때문이다. 자세한 내용은 05-legal-policy.md 참고.

## 4. 정합(Georeferencing)

- **1차 정합**: EXIF/앱 GPS를 COLMAP `pose_prior_mapper` / `model_aligner`에 넣어 **스케일·대략적 위치**를 잡는다 [검증: COLMAP FAQ]. 도심 GPS 오차는 수~수십 m이다 [미검증, 일반 지식].
- **2차 정합**: ICP(Open3D, point-to-plane)로 맞춘다. 대상은 **베이스맵 건물 외곽 메시**, 또는 건물 footprint와 높이를 extrude한 메시다.
  - 기준 데이터의 라이선스가 정합 참조 용도를 허용하는지는 01-basemap-data.md를 따른다.
- **정밀 앵커(선택)**: 교차로·랜드마크에 GCP를 두거나 RTK를 쓴다. 실내는 GPS가 없으므로 **출입구에서 외부 모델과 공통 특징으로 연결**하고, AprilTag나 실측 거리로 스케일을 확인한다.
- **정합 품질 지표**(검수 자동화용): ICP RMSE, 베이스맵 footprint와의 IoU, 수직축 기울기(°). 임계값을 넘으면 사람이 검수한다.

## 5. 촬영 앱

| 앱 | 상용 사용 | 문제점 |
|---|---|---|
| Polycam | 결과물 상용화 가능 [검증: ToS 5.2] | **ToS 5.4.7: 경쟁 서비스 구축이나 AI 학습 목적 사용 금지.** 우리 파이프라인 입력으로 쓰면 저촉될 소지가 있다. |
| Scaniverse | Pro($50/월) 이상만 상용 [검증] | Niantic에 광범위한 라이선스를 부여해야 한다. |
| Luma | 유료 구독 중 생성분만 [검증] | |
| KIRI | [미검증] | |

→ **MVP(나 혼자 촬영)**: 폰 기본 카메라나 미러리스로 찍은 **원본 사진·영상**을 바로 쓴다. 제3자 앱 ToS에 의존하지 않는다.
→ **크라우드소싱 단계**: **자체 캡처 앱**(ARKit/ARCore 포즈, GPS, 노출 고정, 촬영 가이드 UI)과 **자체 UGC 약관**을 만든다.

## 6. 연산 비용

- gsplat 공식 벤치마크(Mip-NeRF 360, 30k step) [검증]:
  - A100: 19.4분, 5.6GB
  - MCMC 1M: 15.4분, 2.0GB
- Hierarchical-3DGS 예제(1,500장): A6000으로 전 과정 약 5.2시간 [검증]. 참고용이며, 코드는 비상업.
- 클라우드 GPU 시간당(2026-09 조회) [검증]:
  - RunPod: RTX 4090 $0.34~0.74, L40S $0.79~1.09, A100 80GB $1.19~1.59
  - Lambda: A6000 $1.09, H100 $3.99~
- **블록(골목 1곳) 처리 추정** [미검증 추정]:
  - 500장: GPU 2~3시간, **$1~5**
  - 2,000장: 4~8시간, **$5~20**
  - → MVP 단계에서 비용은 무시할 수 있는 수준이다. 로컬 GPU가 있으면 로컬에서 돌려도 된다.

## 7. 촬영 모범 사례 요약 (Phase 1 촬영 가이드의 근거)

- 텍스처가 풍부해야 한다. 노출·화이트밸런스를 **고정**한다. 흐린 날이나 이른 아침이 좋다(그림자·인파가 적다) [COLMAP tutorial, Postshot guide 검증].
- **제자리 회전 금지**, 반드시 이동하며 촬영한다 [검증].
- 셔터 1/500s 이상. 노이즈가 블러보다 낫다(ISO 허용) [검증/2차].
- 광각 24mm 환산 전후 [검증].
- 인접 프레임 overlap 60~80% [2차].
- 영상은 1~3fps로 추출하고 샤프니스 필터를 적용한다 [미검증, 경험치]. nerfstudio 기본값은 영상당 300프레임이다 [검증].
- 높이·기울기를 바꾼 링을 2~5개 촬영한다 [검증: Postshot].
- 교차로에서 **루프를 닫아** 드리프트를 줄인다.
- 실내는 벽을 따라가는 궤적과 중앙을 바라보는 궤적을 섞는다. **문을 통과하는 연결 촬영이 필수**다.

## 출처

- COLMAP: https://github.com/colmap/colmap/blob/main/CHANGELOG.rst , https://github.com/colmap/colmap/blob/main/LICENSE , https://colmap.github.io/faq.html , https://colmap.github.io/tutorial.html
- GLOMAP: https://github.com/colmap/glomap
- hloc / LightGlue / SuperGlue: https://github.com/cvg/Hierarchical-Localization , https://github.com/cvg/LightGlue , https://github.com/magicleap/SuperGluePretrainedNetwork/blob/master/LICENSE
- OpenMVG / OpenMVS / AliceVision: https://github.com/openMVG/openMVG , https://github.com/cdcseacave/openMVS , https://github.com/alicevision/AliceVision
- RealityScan: https://www.cgchannel.com/2025/06/epic-games-releases-realityscan-2-0-and-realityscan-mobile-1-7/ , https://www.cgchannel.com/2025/11/epic-games-releases-realityscan-2-1/
- Metashape: https://www.agisoft.com/buy/online-store/ , https://www.agisoft.com/buy/saas/service-provider-license/
- VGGT / MASt3R / MapAnything / Pi3 / Depth-Anything-V2: https://github.com/facebookresearch/vggt , https://github.com/naver/mast3r , https://github.com/facebookresearch/map-anything , https://github.com/yyfz/Pi3 , https://github.com/DepthAnything/Depth-Anything-V2
- Inria 3DGS: https://github.com/graphdeco-inria/gaussian-splatting/blob/main/LICENSE.md
- gsplat: https://github.com/nerfstudio-project/gsplat , https://docs.gsplat.studio/main/tests/eval.html
- Brush / OpenSplat / LichtFeld / 3DGRUT: https://github.com/ArthurBrussee/brush , https://github.com/pierotofy/OpenSplat , https://github.com/MrNeRF/LichtFeld-Studio , https://github.com/nv-tlabs/3dgrut
- Postshot: https://www.jawset.com/docs/d/Postshot+User+Guide/Capturing+Guidelines , https://radiancefields.com/platforms/postshot
- CityGaussian / Octree-GS / H3DGS / Mip-Splatting: https://github.com/DekuLiuTesla/CityGaussian , https://github.com/city-super/Octree-GS , https://github.com/graphdeco-inria/hierarchical-3d-gaussians , https://github.com/autonomousvision/mip-splatting
- SpotLessSplats / WildGaussians: https://github.com/lilygoli/SpotLessSplats , https://github.com/jkulhanek/wild-gaussians
- 2DGS / SuGaR / PGSR / GOF / MILo: https://github.com/hbb1/2d-gaussian-splatting , https://github.com/Anttwo/SuGaR , https://github.com/zju3dv/PGSR , https://github.com/autonomousvision/gaussian-opacity-fields , https://github.com/Anttwo/MILo
- SPZ / SOG: https://github.com/nianticlabs/spz , https://github.com/playcanvas/splat-transform , https://developer.playcanvas.com/user-manual/gaussian-splatting/formats/sog/
- KHR_gaussian_splatting: https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_gaussian_splatting/README.md , https://www.khronos.org/news/press/gltf-gaussian-splatting-press-release
- Cesium splat LOD: https://cesium.com/blog/2026/04/27/3d-gaussian-splats-lod/
- Open3D / CoACD / V-HACD / Recast / SAM2 / Ultralytics: https://github.com/isl-org/Open3D , https://github.com/SarahWeiii/CoACD , https://github.com/kmammou/v-hacd , https://github.com/recastnavigation/recastnavigation , https://github.com/facebookresearch/sam2 , https://github.com/ultralytics/ultralytics
- 앱 약관: https://poly.cam/legal/terms-of-service , https://www.nianticspatial.com/en/terms , https://www.nianticspatial.com/pricing , https://lumalabs.ai/legal/tos , https://www.kiriengine.app/pricing
- GPU 가격: https://www.runpod.io/pricing , https://lambda.ai/pricing , https://instances.vantage.sh/aws/ec2/g6e.xlarge
- 캡처 가이드: https://radiancefields.com/how-to-capture-radiance-fields
