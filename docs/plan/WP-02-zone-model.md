# WP-02 — Zone 데이터 모델·CLI `golmok-zone`

상태: 🔵 진행 중 · 담당: 클라우드 Claude 세션 · 의존: WP-01 · 검증: G1, 이후 G3(실 Zone)

## 목표
ARCHITECTURE §2~§4의 Zone 모델을 **실행 가능한 스펙**으로 만든다. manifest 스키마, 좌표 변환, Zone Index, 베이스맵 제외 폴리곤 생성까지. 이후 WP-03(후처리), WP-04(UE 로더), WP-06(임포트), WP-07(정합)이 모두 이 스펙을 읽는다.

## 배경 (읽을 것)
- `docs/ARCHITECTURE.md` §2 좌표계, §3.2 manifest, §3.3 Zone Index, §4 교체 규칙
- `tools/golmok_tools/basemap/geo.py`의 `EnuFrame`, `Projector` (재사용)
- `unreal/Golmok/Content/Python/golmok/basemap_import.py` 상단 주석: UE 축 규약 **X=east, Y=south, Z=up, cm**
- D-012: 베이스맵은 정적 임포트, 플레이 구역은 빌드 단계 `--exclude`

## 산출물
1. **스펙 문서** `docs/spec/zone-manifest.md` + JSON Schema `docs/spec/zone-manifest.schema.json` (draft 2020-12)
   - ARCHITECTURE §3.2의 필드를 유지하고 다음을 **확정**한다.
     - `schema_version: 1`
     - `origin`: `{lat, lon, height_ellipsoidal}` (double). `origin_ecef`는 파생값으로 함께 기록.
     - `transform`: zone-local ENU(**Z-up, m**) → ECEF 4×4, **row-major 16개 double**.
     - `layers.visual`: `{format: "nanite_mesh" | "splat_ply" | "splat_3dtiles" | "splat_lcc", chunks: [{id, uri, bbox_enu:[[x,y,z],[x,y,z]], tris?}], textures?: [...]}` — D-010 전이므로 format enum만 열어 두고 로더는 `nanite_mesh` 우선.
     - `layers.collision`: `{format:"glb", uri, chunks?}`; `layers.blockers`: `{uri}`(평면 목록 JSON: `{planes:[{id, center_enu, normal_enu, size_m:[w,h], kind:"glass"|"no_entry"}]}`); `layers.navmesh`는 UE가 만들므로 **선택**.
     - `footprint_wgs84` GeoJSON Polygon, `replaces.building_ids[]`, `replaces.terrain_clip`, `portals[]`(`{id, to_zone, pose_enu:{position:[x,y,z], yaw_deg}, radius_m, kind:"door"}`), `priority`, `quality`, `consent`, `attribution`, `sources`(촬영 ID = `captures/INDEX.md`의 ID).
   - **UE 매핑 규약**: manifest 파일 위치 `Content/Golmok/Zones/<zone_id>/v<version>/manifest.json`; 청크 에셋 `/Game/Golmok/Zones/<zone_id>/v<version>/SM_<chunk_id>`; 충돌 `SM_<zone_id>_collision`; 실내 서브레벨 `/Game/Golmok/Zones/<zone_id>/v<version>/L_<zone_id>`. ENU→UE: `(x, y, z)_m → (100x, −100y, 100z)_cm`. 이 규약은 WP-04·06이 그대로 구현한다.
   - Zone Index 스펙: `index/zones.json`(전체 목록: id, 최신 version, kind, priority, bbox_wgs84), `index/cells/<z>_<x>_<y>.json`(웹 메르카토르 z16 타일별 겹치는 zone id·version). 
2. **패키지** `tools/golmok_tools/zone/`
   - `schema.py`: 스키마 로드(`docs/spec/zone-manifest.schema.json`을 패키지 데이터로 복사하거나 상대경로 참조—패키지 설치 시 깨지지 않게 `importlib.resources` 사용) + `validate(manifest) -> list[str]`(jsonschema 의존 추가 가능: MIT).
   - `manifest.py`: dataclass 모델, `load/save`, 기본값, semantic 검사(transform이 rigid(회전 직교, det=+1)인지, footprint 유효·시계 방향 무관, origin이 footprint 안 또는 근처인지, 포털 to_zone 형식).
   - `transform.py`: `zone_transform(lat, lon, h, yaw_deg=0) -> 4x4`(ENU 프레임의 ECEF 변환, `EnuFrame` 재사용), `enu_to_ecef/ecef_to_enu`, `zone_local_to_area_enu(zone_T, area_origin) -> 4x4`(WP-04가 C++로 같은 계산을 하므로 **수치 예제를 스펙 문서에 표로** 남긴다: 원점 37.5620,126.9250,h=50 기준 등).
   - `index.py`: `build_index(zones_root) -> (zones.json, cells)`; z16 타일 계산; 같은 zone 여러 version 중 최신만.
   - `exclude.py`: exterior zone footprint들을 합쳐 GeoJSON FeatureCollection으로(`golmok-basemap --exclude` 입력). 0.5~1m 오버랩 규칙(ARCHITECTURE §4-4)은 여기서 `--buffer-m` 옵션으로.
   - `cli.py` → `golmok-zone`:
     - `init --id z_yeonnam_alley_001 --kind exterior --origin 37.5620,126.9250[,h] --footprint fp.geojson [--yaw 0] --out zones/z_.../v1/` → manifest.json 생성
     - `validate <manifest.json> [--check-files]`
     - `index build --zones-root zones/ --out index/`
     - `exclude --zones-root zones/ --out exclude.geojson [--buffer-m 0.75]`
     - `transform <manifest.json> --enu x,y,z` → ECEF, lat/lon, UE cm 출력
     - `bump <manifest.json>` → 새 version 디렉터리 복사(불변 버전 규칙)
   - `pyproject.toml`에 스크립트·extra(`zone = ["jsonschema", "pyproj", "shapely"]`) 추가.
3. **테스트** `tools/tests/test_zone_*.py`: 스키마 통과/실패 케이스, transform 왕복 오차 < 1e-6 m, 알려진 좌표의 ECEF 값(문서 표와 일치), index 셀 계산, exclude 병합, CLI(`subprocess` 또는 `main([...])`) 스모크.
4. **픽스처** `tools/tests/fixtures/zones/z_synthetic_001/v1/manifest.json` (WP-04의 UE 픽스처와 동일 내용. WP-04가 이 파일을 `unreal/Golmok/Content/Golmok/Zones/`로 복사한다.)
5. 문서: `tools/README.md`에 `golmok-zone` 절, `docs/README.md`에 spec 링크, `docs/ARCHITECTURE.md` §3.2에 "확정 스펙은 spec/zone-manifest.md" 한 줄.

## 완료 기준
- `pytest` 통과, CI 초록.
- `golmok-zone init` → `validate` → `index build` → `exclude`가 임시 디렉터리에서 연속 실행된다(테스트로 보장).
- 스펙 문서에 UE 규약과 수치 예제가 있다.

## 주의
- WGS84 타원체 상수는 `pyproj` 변환과 교차 검증한다(`Transformer.from_crs("EPSG:4979","EPSG:4978")`).
- 좌표 단위·축 규약을 문서·코드·테스트에서 한 번씩 확인한다(가장 흔한 사고).

## 결과
(세션이 작성)
