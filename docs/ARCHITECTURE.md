# Golmok 전체 아키텍처 (Phase 0 설계안)

작성일: 2026-09-24 · 상태: **승인된 결정(D-003~D-007) 반영, 1차 개정**
근거 문서: `research/01~07`, `DECISIONS.md`

> **개정 요약 (2026-09-24)**
> - 클라이언트가 웹에서 **Unreal Engine 5.8 + Cesium for Unreal(고사양 PC)**로 바뀌었다(D-003).
> - Zone의 시각 레이어 포맷은 스파이크 1.1의 결과(D-010)로 확정한다. 후보는 Nanite 메시, splat, 하이브리드다.
> - MVP 재구성은 RealityScan + Postshot을 **수동**으로 쓴다(D-005). 아래 §5의 자동 파이프라인(COLMAP + gsplat)은 **Phase 2** 설계다.
> - 좌표계, Zone 모델, 교체 규칙(§2~§4)은 엔진과 무관하므로 유지한다.

---

## 1. 한눈에 보기

```
 ┌─────────────┐   ┌──────────────────────── 처리 파이프라인 (서버/GPU) ─────────────────────────┐
 │ 촬영·업로드 │   │                                                                          │
 │ (폰/카메라, │──▶│ ① Ingest ─▶ ② 개인정보 ─▶ ③ 보안구역 ─▶ ④ SfM ─▶ ⑤ Splat 학습 ─▶ ⑥ 충돌메시 │
 │  자체 앱)   │   │   검증        블러/마스크    지오펜스      COLMAP     gsplat          TSDF/Recast │
 └─────────────┘   │                                                        │                 │
                   │                         ⑦ 정합(GPS prior → ICP to basemap) ◀┘                │
                   │                                   │                                      │
                   │                         ⑧ 검수(자동 지표 + 사람 검수 뷰어)                   │
                   │                                   │                                      │
                   │                         ⑨ 게시(Zone 버전 생성, CDN 업로드)                   │
                   └───────────────────────────────────┼──────────────────────────────────────┘
                                                       ▼
 ┌─────────────────────── 저장 (지리좌표 기반) ────────────────────────┐
 │  Basemap 3D Tiles (지형 + LOD1 건물, 건물ID 메타데이터)                  │
 │  Zone Index (공간 인덱스: 어떤 셀에 어떤 Zone이 있나)                    │
 │  Zones/<zone_id>/<version>/ { manifest.json, visual(D-010), collision, navmesh } │
 └───────────────────────────────────────┬───────────────────────────┘
                                         ▼  HTTP(S) / CDN, Range 요청
 ┌──────────────── 게임 클라이언트 (Unreal Engine 5.8, C++, 고사양 PC) ────────────────┐
 │  Cesium3DTileset(배경 LOD1)  +  Zone(Nanite 메시 / splat 플러그인)  +  Chaos 물리 + 캐릭터 │
 │  Floating origin(ENU) · Zone 교체 로직(베이스맵 건물 숨김 + 충돌 스왑)              │
 └────────────────────────────────────────────────────────────────────────────┘
```

## 2. 좌표계

| 용도 | 좌표계 | 이유 |
|---|---|---|
| 저장·교환(전역) | **WGS84 / ECEF (EPSG:4978)** | 3D Tiles 표준이고 전 세계로 확장할 수 있다. |
| 국내 원천 데이터 | EPSG:5186 / 5179 등 → 변환 | GIS건물통합정보와 NGII 데이터는 TM 좌표로 제공된다. |
| Zone 내부 | **Zone 로컬 ENU** (원점 = zone.origin, 단위 m, Y-up 또는 Z-up 하나로 고정) | splat·collision·navmesh가 float32 정밀도로 표현된다. |
| 클라이언트 런타임 | **Floating origin ENU** | 플레이어 근처를 원점으로 둔다. 물리는 이 로컬 좌표에서만 돈다. |

- 변환 체인: `zone-local ENU → (zone.transform: 4x4, double) → ECEF`. 이 변환은 정합(⑦)에서 한 번 산출하고, 해당 Zone의 모든 레이어가 **공유**한다.
- 높이 기준: 타원체고(ECEF)로 저장한다. DEM의 정표고(해발)와 맞추기 위한 지오이드 보정(KNGeoid)은 베이스맵 빌드 단계에서 처리한다.

## 3. 데이터 모델

### 3.1 Basemap (전역, 저해상도, 항상 존재)
- **지형**: NGII DEM → 지형 타일, 정사영상 드레이프.
- **건물**: GIS건물통합정보 폴리곤 × 높이 → LOD1 압출(+ 절차적 파사드 텍스처) → glTF → **3D Tiles 1.1**.
  - 각 건물 feature에 **`building_id`**(건물통합정보 고유키)를 `EXT_mesh_features`/`EXT_structural_metadata`로 넣는다.
  - 이 ID가 Zone 교체 때 "어떤 건물을 숨길지"의 키가 된다.
- 베이스맵 건물은 **그대로 충돌체로도 쓴다**(박스형이므로 simplification이 필요 없다).

### 3.2 Zone (촬영으로 만든 고품질 구역)

```jsonc
// zones/<zone_id>/<version>/manifest.json
{
  "zone_id": "z_seongsu_alley_001",
  "version": 3,
  "kind": "exterior",              // exterior | interior
  "parent_zone": null,             // interior일 때 연결된 exterior zone
  "origin_ecef": [x, y, z],
  "transform": [/* 4x4 zone-local → ECEF, double */],
  "footprint_wgs84": { /* GeoJSON Polygon: 이 Zone이 권위를 갖는 영역 */ },
  "replaces": {
    "building_ids": ["11110-100xxxx", "..."],  // 숨길 베이스맵 건물
    "terrain_clip": true                       // footprint 안의 베이스맵 지면 숨김
  },
  "layers": {
    "visual":    { "format": "rad", "uri": "splat.rad", "lod": true },  // 또는 sog / spz
    "collision": { "format": "glb", "uri": "collision.glb" },
    "navmesh":   { "format": "recast", "uri": "navmesh.bin" },
    "blockers":  { "uri": "blockers.json" }    // 유리면·접근 금지 평면
  },
  "portals": [ { "id": "door_1", "to_zone": "z_..._interior", "pose": [...], "radius_m": 1.5 } ],
  "priority": 10,                  // 겹칠 때 높은 쪽이 이긴다
  "quality": { "icp_rmse_m": 0.18, "footprint_iou": 0.93, "reviewed_by": "...", "reviewed_at": "..." },
  "consent": { "type": "public_street" /* | owner_consent */, "record_id": "..." },
  "attribution": ["촬영: ..."]
}
```

### 3.3 Zone Index
- 공간 셀(예: 웹 메르카토르 z16 타일, 한 변 약 500m 이하)마다 겹치는 zone과 **현재 게시 버전**을 나열한 정적 JSON을 둔다.
- 규모가 커지면 PostGIS에서 생성하는 동적 API로 바꾸되, **클라이언트 계약(JSON 스키마)은 유지**한다.

## 4. "베이스맵 위 점진적 교체" 규칙

1. 클라이언트는 플레이어 주변 셀의 Zone Index를 받고, 가시 범위 안의 zone manifest를 로드한다.
2. Zone이 **로드 완료** 상태가 되면 다음을 한다.
   - `replaces.building_ids`에 있는 베이스맵 feature를 **숨긴다**(렌더 + 충돌 모두 끈다).
     - UE 구현: MVP에서는 Zone footprint로 `CesiumCartographicPolygon` 클리핑을 쓴다(타일셋 제외). building_id 단위로 숨기는 것은 필요해지면 metadata 기반으로 구현한다.
   - `terrain_clip`이면 footprint 안의 베이스맵 지면을 클리핑한다. 시각적으로는 splat이 지면을 덮고, 물리는 zone collision이 대신한다.
   - zone의 collision과 navmesh를 켠다.
3. 로드 전이나 원거리에서는 **베이스맵을 유지**한다. 이렇게 하면 구멍이 생기지 않는다(fallback-first).
4. 두 zone이 겹치면 `priority`, 그다음 최신 `version`이 이긴다. 경계에는 **0.5~1m 오버랩 + 시각 블렌드**를 둔다(splat opacity fade).
5. **Interior zone**은 portal 반경 안에 들어오거나 portal이 시야에 들어올 때만 로드한다. 실내 진입 시 외부 zone의 LOD를 낮춘다.
6. 게시는 **불변 버전**으로 한다(`/zones/<id>/<version>/`). Index만 바꿔서 롤백·AB 테스트를 할 수 있다.

## 5. 처리 파이프라인 상세

| 단계 | 내용 | 도구(상용 가능) | 산출물 |
|---|---|---|---|
| ① Ingest | 업로드(재개 가능), EXIF·앱 메타(포즈·GPS·IMU) 추출, 품질 필터(블러·노출) | tus 프로토콜, ffmpeg(프레임 추출) | raw/, meta.json |
| ② 개인정보 | **얼굴·번호판 검출 → 블러**, 사람·차량 마스크 생성. **이후 단계는 블러된 이미지만** 쓴다. 원본은 암호화 보관 후 짧은 기간 내 삭제 | 검출 모델(라이선스 확인된 것만, 05 참고), SAM2 | images_blurred/, masks/ |
| ③ 보안구역 | 촬영 GPS와 **공개제한 구역 지오펜스**를 교차 검사. 걸리면 차단하거나 사람 검토로 보낸다 | PostGIS / shapely | pass / hold |
| ④ SfM | 포즈 추정. 앱 포즈·GPS를 prior로 사용 | COLMAP 4.2 (ALIKED+LightGlue, global/sequential) | sparse/ |
| ⑤ Splat | 학습(antialiased, MCMC, 마스크 loss, appearance embedding) | gsplat | splat.ply → rad/sog/spz |
| ⑥ Collision | depth 렌더 → TSDF → 평면 스냅 → decimate → CoACD → navmesh | Open3D, meshoptimizer, CoACD, Recast | collision.glb, navmesh.bin |
| ⑦ 정합 | GPS·앱 포즈로 similarity → **베이스맵 LOD1과 ICP** → transform 산출 | COLMAP model_aligner, Open3D ICP | transform, 품질 지표 |
| ⑧ 검수 | 자동 지표(ICP RMSE, footprint IoU, 수직 기울기, 블러 누락 재검사). **사람 검수**: 웹 뷰어에서 splat·collision 오버레이 확인 | 자체 검수 뷰어(클라이언트 재사용) | approve / reject |
| ⑨ 게시 | manifest 생성, CDN 업로드, Zone Index 갱신 | 스크립트 | zones/…/vN |

- **MVP**: ①~⑨를 **로컬 Python CLI**(`pipeline/`)로 수동 실행한다. 서버, 큐, 업로드 앱은 만들지 않는다.
- **확장기**: 각 단계를 작업 큐(예: 컨테이너 잡 + GPU 워커)로 옮긴다. 상태는 PostgreSQL/PostGIS에 둔다.

## 6. 저장·서빙

- **정적 파일 + CDN**이 기본이다. 3D Tiles와 Zone 레이어는 모두 정적 파일이다. MVP(PC 패키지 빌드)에서는 게임 설치 파일에 포함한다. 원격 스트리밍은 공개 서비스 단계에서 결정한다.
- 원천 이미지(블러 처리 전)는 **분리된 비공개 버킷에 두고, 암호화와 보존기간(예: 30일)**을 적용한다.
- **호스팅 리전**: 국내 리전을 기본으로 한다. 공간정보 국외반출 규정과 보안 검토 리스크를 줄이기 위해서다(05 참고). 최종 결정은 법률 검토 후 한다.

## 7. 클라이언트 구조 (Unreal Engine 5.8, C++)

```
unreal/Golmok/Source/Golmok/
  Geo/        CesiumGeoreference 원점 관리, Zone transform 적용(CesiumGlobeAnchor)
  Basemap/    배경 타일셋 설정, 플레이 구역 클리핑 폴리곤, 절차적 파사드 파라미터
  Zones/      Zone manifest 로더, 교체 규칙, 포털(실내 레벨 스트리밍)
  Player/     3인칭 캐릭터(걷기·뛰기·점프), 카메라 붐, Enhanced Input
  Lighting/   시간대 프리셋, 안개·대기, 실내외 노출 전환
  Debug/      충돌 와이어프레임, Zone 경계, 성능 HUD, 고정 카메라 경로 재생
unreal/Golmok/Content/Python/   에디터 자동화: 메시·텍스처 임포트, 청크 배치, 머티리얼 설정, 측정·스크린샷
```

- 로직은 C++로 쓰고 Blueprint는 최소화한다(D-003). 물리는 Chaos, 캐릭터는 CharacterMovementComponent, 내비게이션은 Recast 기반 NavMesh를 쓴다.
- 좌표: UE의 Large World Coordinates와 Cesium의 origin rebasing을 쓴다. 플레이 구역은 약 500m라서 정밀도 문제는 작다.

## 8. 저장소 구조 (제안)

```
golmok/
  docs/                 설계·결정·로드맵
  unreal/Golmok/        UE 5.8 게임 프로젝트 (C++ + Unreal Python, 에셋은 Git LFS)
  tools/privacy/        얼굴·번호판 블러 (MVP)
  tools/basemap/        베이스맵 빌더 (SHP/DEM → glTF → 3D Tiles)
  tools/viewer/         (선택) 웹 내부 검수 뷰어
  pipeline/             (Phase 2) 자동 재구성 파이프라인
  data/                 (git 제외) 로컬 원천·산출물
```

## 9. 이후 확장 포인트 (지금은 만들지 않음)
- 자체 촬영 앱(ARKit/ARCore 포즈 + 가이드 UI + 온디바이스 블러 미리보기)
- 크라우드 업로드 서버, 사용자·동의 관리, 신고·임시조치 처리
- 여러 촬영 세션의 병합, 시간대별 외관 차이 보정
- 모바일 재평가(Phase 2 이후)
