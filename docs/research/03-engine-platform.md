# 03. 게임 엔진 / 클라이언트 플랫폼

조사일: 2026-09-24

> **결정 갱신(2026-09-24, D-003)**: 퀄리티 최우선 원칙에 따라 **Unreal Engine 5 + Cesium for Unreal(고사양 PC)**로 결정했다. 이 문서의 웹 추천안은 대체됐고, 웹 스택은 내부 검수 뷰어 용도로만 남긴다. UE 세부 검증은 `07-ue5-toolchain.md`를 본다.
표기: **[V]** URL로 직접 확인 / **[U]** 미확인 또는 2차 출처·일반 지식

## 0. 전제

1. **서울에는 Google Photorealistic 3D Tiles 커버리지가 없다.** Cesium 커뮤니티에 한국 지역이 로드되지 않는다는 보고가 있다 [V]. 따라서 베이스맵은 국내·오픈 데이터를 **직접 3D Tiles로 변환해 호스팅**해야 하고, 엔진 선택도 이 전제를 따라야 한다(01-basemap-data.md 참고).
2. **KHR_gaussian_splatting**(glTF)은 Khronos repo README에 "Complete, Ratified"로 표기돼 있다 [V]. 2026-02에 RC가 나왔고 Q2 비준을 목표로 했다. 정확한 비준일은 [U].
3. **iOS 26 / Safari 26부터 WebGPU가 기본 활성화**다 [V]. Chrome Android는 121부터 지원한다. 앱 래핑(WKWebView)에서도 WebGPU가 되는지는 [U].

## 1. Cesium의 splat 지원 경과 (3D Tiles)

| 버전 | 시기 | 내용 |
|---|---|---|
| CesiumJS 1.130.1 | 2025-06 | SPZ splat 실험 지원 |
| CesiumJS 1.135 | 2025-11 | `KHR_gaussian_splatting` + `spz_2` 실험 지원 |
| CesiumJS 1.139 | 2026-03 | 첫 shipping 구현 |
| CesiumJS/Unreal | 2026-04-27 | **Hierarchical LOD splat 3D Tiles** 발표 |
| Cesium for Unreal | v2.23+ | KHR splat 지원. **Niagara 기반 렌더링**이라 그림자·post-process와 통합되지 않는다 [V]. |
| Cesium for Unity | 1.25 (2026-08) | **splat 미지원**("계획"만 있음) [V] |

## 2. 후보별 요약

### Unity 6 + Cesium for Unity
- 3D Tiles 스트리밍: ◎ (origin shifting 지원, 모바일·Web 빌드 가능) [V]
- Splat:
  - Cesium 경로는 미지원이다.
  - 대표 플러그인 aras-p/UnityGaussianSplatting(MIT)은 **추가 개발 계획이 없고, 모바일·WebGPU에서 실패**한다 [V].
  - gsplat-unity(MIT)는 Android에서 테스트됐지만 Web은 미지원이다 [V].
- 물리/캐릭터: ◎
- AI 코딩: ○. C#과 YAML 씬은 괜찮지만 에디터 의존도가 높다. 공식 MCP는 Pro 구독 필요 [V].
- 비용: Personal은 20만 달러 미만 무료, Pro는 좌석당 연 약 2,310달러 [V].

### Unreal Engine 5.6~5.8 + Cesium for Unreal
- 3D Tiles 스트리밍: ◎ (LWC double precision)
- Splat: **네이티브 엔진 중 유일하게 공식 3D Tiles splat LOD를 지원**한다 [V]. 단 Niagara 기반이다. Epic 1st-party splat은 없다 [U].
- 물리/캐릭터: ◎ (3인칭 템플릿 기본 제공)
- 모바일: △. Cesium과 Niagara splat을 함께 모바일에서 돌린 사례는 없다 [U].
- AI 코딩: △. `.uasset`/`.umap`이 바이너리이고, Blueprint는 diff가 불가하며, C++ 빌드가 무겁다. MCP는 5.8에서 experimental [U].
- 비용: 누적 매출 100만 달러 초과분에 5% 로열티 [V].

### Godot 4.x
- 3D Tiles: "3D Tiles for Godot" 플러그인(Cesium 그랜트) [V]
- Splat: GDGS(MIT) 커뮤니티 플러그인. LOD는 [U].
- AI 코딩: ◎ (텍스트 씬, headless CLI)
- 리스크: 3D Tiles와 splat이 모두 소규모 플러그인이다.

### CesiumJS (Web)
- 3D Tiles와 splat LOD는 최고 수준이다 [V].
- **게임 기능이 거의 없다.** 물리·캐릭터·navmesh를 직접 붙여야 한다. 뷰어나 검수 도구로 적합하다.

### Three.js + 3DTilesRendererJS + Spark 2 + Rapier
- 3D Tiles: NASA-AMMOS 3DTilesRendererJS. CesiumJS 다음으로 성숙했고, Babylon 9도 내부에서 이것을 쓴다 [V].
- Splat: **Spark 2.x**(World Labs, MIT, 2026-04) [V]
  - `.RAD` 포맷의 연속 LoD 스트리밍과 GPU 가상메모리(LRU 페이징)
  - three.js 메시와 fuse, 다중 splat global sort
  - WebGL2 기반, 모바일·Quest 대상
  - mkkellogg/GaussianSplats3D는 개발이 중단됐고 작성자가 Spark를 권장한다 [V].
- 3D Tiles 안의 splat: 3rd-party 플러그인(Apache-2.0, `KHR_gaussian_splatting` + `spz_2`, ECEF 대좌표)이 있다. 규모가 작은 프로젝트다 [V].
- 물리/캐릭터: Rapier(WASM) KinematicCharacterController, recast-navigation-js. 조립형이다.
- AI 코딩: ◎ (전부 TS 텍스트, Vite, Playwright headless 테스트)
- 비용: MIT/Apache

### Babylon.js 9.x
- 3D Tiles: 9.0(2026-03)에서 3DTilesRendererJS 경유 지원이 추가됐다. **Large World Rendering(floating origin)이 Havok 물리와 통합**돼 있고 Geospatial Camera도 있다 [V].
- Splat: ply/splat/spz/sog, **splat 그림자**, global sort를 지원한다. **LoD 스트리밍은 2026-06 기준 experimental** [V].
- 물리: Havok 내장. 웹 엔진 중 가장 "엔진답다".
- AI 코딩: ◎. 비용: Apache-2.0.

### PlayCanvas (engine-only + splat-transform)
- Splat: **현재 웹 최고 성능**이다 [V].
  - WebGPU compute 렌더러: M4 Max에서 3,500만 splat 75.8fps(WebGL2는 13.3fps). iPhone 13 Pro Max에서 WebGL2 대비 약 2.1배.
  - Streamed SOG LOD.
- **splat 씬을 걸어다니는 게임 실증**(2026-04) [V]:
  - voxel `.collision.glb`, 조명 probe grid, recast navmesh, NPC를 갖췄다.
  - 모바일 fps 수치는 비공개.
- 3D Tiles: `earthatile`(신생, 성숙도 [U])
- 물리: ammo.js(구형)

## 3. 비교표

◎ 우수, ○ 양호, △ 제한, × 미지원

| 기준 | Unity | UE5 | Godot | CesiumJS | **Three.js 스택** | Babylon 9 | PlayCanvas |
|---|---|---|---|---|---|---|---|
| 3D Tiles 스트리밍·정밀도 | ◎ | ◎ | ○ | ◎ | ◎ | ○ | △ |
| 3D Tiles 안 splat(KHR) | × | ◎ | × | ◎ | ○ (3rd-party) | × [U] | × [U] |
| 독립 splat 품질·LOD 스트리밍 | △ | ○ | △ | ○ | ◎ | ○ (exp.) | ◎ |
| 물리·3인칭·navmesh | ◎ | ◎ | ○ | × | ○ | ◎ | ○ |
| 모바일 | ○ (splat 취약) | △ | ○ | ○ | ○ | ○ | ◎ |
| AI 코딩·git·CLI | ○ | △ | ◎ | ◎ | ◎ | ◎ | ○~◎ |
| 비용 | Pro 유료 | 5% 로열티 | 무료 | 무료(ion 유료) | 무료 | 무료 | 무료 |

## 4. 추천

### 1순위: 웹 — **TypeScript + Three.js + 3DTilesRendererJS + Spark 2 + Rapier**
- 이유:
  - 베이스맵은 3D Tiles(ECEF)로, 고품질 구역은 Spark `.RAD` LoD로 따로 스트리밍한다. 이 두 요구를 가장 넓게 충족한다.
  - 전부 텍스트 코드라서 **너(개발자)와 AI가 함께 개발하기 가장 쉽다**. CLI 빌드, headless 테스트, git diff가 모두 된다.
  - 비용은 0이다. iOS 26 이후 모바일 웹 환경도 좋아졌다.
  - 앱스토어가 필요해지면 Capacitor 등으로 래핑하거나 그때 재평가한다.
- 좌표 처리: 지구 규모 좌표는 ECEF로 두고, **플레이 구역마다 ENU 로컬 프레임(floating origin)**을 잡는다. 물리(Rapier)는 로컬 좌표에서만 돌린다.

### 대안 A: Babylon.js 9 — 엔진 일체형 웹
- Havok, floating origin, 3D Tiles, splat 그림자가 한 엔진에 있다.
- splat LoD가 experimental이라 2순위로 둔다. 1순위 스파이크 결과가 나쁘면 즉시 전환할 후보다. 두 엔진 모두 3DTilesRendererJS를 쓰므로 전환 비용이 비교적 작다.

### 대안 B: PlayCanvas engine-only — splat 성능 최우선
- 모바일 splat 성능이 병목이면 선택한다. 대신 3D Tiles 쪽을 직접 보강해야 한다.

### 네이티브가 필수라면: Unreal + Cesium for Unreal
- 공식 splat 3D Tiles LOD가 있는 유일한 네이티브 조합이다.
- AI 코딩 효율이 낮고, 모바일은 미검증이며, 5% 로열티가 있다.

### 비추천
- **Unity**: Cesium splat이 없고, 주요 splat 플러그인이 유지보수 중단 상태이며 모바일·Web에서 실패한다.
- **CesiumJS 단독**: 게임 기능이 없다. 다만 **내부 검수 뷰어로는 채택을 권장**한다.
- **Godot**: 핵심 기능이 모두 소규모 플러그인이다.

### 검증 계획 (Phase 1 첫 2주 스파이크)
- 같은 테스트 splat(공개 샘플 또는 내가 찍은 소규모 장면)을 **Spark 2**와 **PlayCanvas Streamed SOG**로 각각 띄운다.
- Rapier 캐릭터를 걷게 하고, **iPhone(13 이상)과 갤럭시 중급기**에서 fps, 메모리, 로딩 시간을 측정한다.
- 목표 기준(제안): 모바일 30fps 이상, 초기 로딩 10초 이하, 탭 메모리 1.5GB 이하.

## 5. 확인하지 못한 항목 [U]
- 앱 래핑(WKWebView)에서 WebGPU가 되는지
- Spark의 WebGPURenderer 지원
- Babylon·PlayCanvas의 3D Tiles 내 KHR splat 지원
- Unity 모바일 splat fps
- PlayCanvas 보행 데모의 모바일 fps
- `splat-transform`의 엔진 비종속 사용 가능성

## 출처
- https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_gaussian_splatting/README.md
- https://www.khronos.org/news/press/gltf-gaussian-splatting-press-release
- https://cesium.com/blog/2026/04/27/3d-gaussian-splats-lod/
- https://raw.githubusercontent.com/CesiumGS/cesium/main/CHANGES.md
- https://cesium.com/learn/unreal/3d-gaussian-splat-tilesets-lods/
- https://cesium.com/blog/2026/08/04/cesium-releases-in-august-2026/
- https://cesium.com/learn/cesium-unity/ref-doc/supported-platforms.html
- https://community.cesium.com/t/google-3d-tiles-unity-south-korea-not-working/35783
- https://github.com/aras-p/UnityGaussianSplatting
- https://github.com/wuyize25/gsplat-unity
- https://unity.com/blog/unity-is-canceling-the-runtime-fee
- https://docs.unity3d.com/Packages/com.unity.ai.assistant@2.7/manual/integration/unity-mcp-get-started.html
- https://www.unrealengine.com/license
- https://github.com/xgrids/LCC-3DGS-Unreal-Plugin
- https://cesium.com/blog/2025/05/01/introducing-3d-tiles-for-godot-by-battle-road/
- https://github.com/ReconWorldLab/godot-gaussian-splatting
- https://www.worldlabs.ai/blog/spark-2.0 , https://sparkjs.dev/docs/new-features-2.0/ , https://github.com/sparkjsdev/spark
- https://github.com/mkkellogg/GaussianSplats3D
- https://github.com/NASA-AMMOS/3DTilesRendererJS
- https://github.com/WilliamLiu-1997/3D-Tiles-RendererJS-3DGS-Plugin
- https://blogs.windows.com/windowsdeveloper/2026/03/30/part-2-babylon-js-9-0-tooling-updates-and-new-geospatial-features/
- https://forum.babylonjs.com/t/gaussian-splatting-streaming-and-lod/63728
- https://blog.playcanvas.com/new-in-supersplat-webgpu-and-streaming-bring-huge-performance-wins/
- https://blog.playcanvas.com/turning-a-gaussian-splat-into-a-videogame/
- https://github.com/playcanvas/earthatile
- https://github.com/gpuweb/gpuweb/wiki/Implementation-Status
