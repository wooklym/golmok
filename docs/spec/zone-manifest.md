# Zone manifest·Zone Index 스펙 (v1)

작성: 2026-09-24 (WP-02) · 상태: **확정(schema_version 1)** · 근거: [ARCHITECTURE.md](../ARCHITECTURE.md) §2~§4, [DECISIONS.md](../DECISIONS.md) D-010·D-012

이 문서는 Zone 데이터의 **계약**이다. `golmok-zone`(Python, WP-02), UE 로더(C++, WP-04), 에디터 임포트(Python, WP-06), 후처리(WP-03), 정합(WP-07)이 모두 이 문서를 따른다. 바꾸려면 `schema_version`을 올리고 이 문서·스키마·테스트를 같이 고친다.

| 파일 | 내용 |
|---|---|
| [zone-manifest.schema.json](zone-manifest.schema.json) | manifest JSON Schema (draft 2020-12) |
| [zone-blockers.schema.json](zone-blockers.schema.json) | `layers.blockers.uri`가 가리키는 평면 목록 |
| [zone-index.schema.json](zone-index.schema.json) | `index/zones.json`, `index/cells/<z>_<x>_<y>.json` |
| [../../tools/tests/fixtures/zones/z_synthetic_001/v1/manifest.json](../../tools/tests/fixtures/zones/z_synthetic_001/v1/manifest.json) | 합성 예제(청크 3·충돌 1·blocker 1·포털 1). WP-04 UE 픽스처와 같은 내용 |

스키마 원본은 `docs/spec/`이고, `tools/golmok_tools/zone/schemas/`는 패키지 데이터용 사본이다(테스트가 두 사본이 같은지 검사한다).

---

## 1. 좌표 규약 (가장 중요)

| 이름 | 원점 | 축 | 단위 | 손 |
|---|---|---|---|---|
| **zone-local** | `origin` (zone마다) | x=동(east), y=북(north), z=위(up) — `yaw_deg`만큼 돌 수 있음 | **m** | 오른손 |
| **ECEF** | 지구 중심 (EPSG:4978) | WGS84 | m | 오른손 |
| **area ENU** | 베이스맵 area 원점(`golmok-basemap` 출력 manifest.json의 `origin`) = 레벨의 CesiumGeoreference 원점 | x=동, y=북, z=위 | m | 오른손 |
| **UE** | 레벨 원점(= area 원점) 또는 zone actor 원점 | **X=동, Y=남, Z=위** | **cm** | 왼손 |

- 높이는 **타원체고**(WGS84 ellipsoidal)다. 해발(정표고)이 아니다. 해발과 타원체고는 지오이드고만큼(서울은 +20 m대로 알려져 있다 [미확인]) 차이가 나므로, 정확한 값은 KNGeoid 또는 정합(WP-07)으로 정한다. 예제의 h=50은 임의값이다.
- **주의**: `golmok-basemap build`의 `origin.height_ellipsoidal`은 `DEM 정표고 + --geoid-offset`이다. `--geoid-offset`을 주지 않으면(기본 0) 그 값은 사실상 정표고라서, 타원체고로 만든 zone과 지오이드고만큼 위아래로 어긋난다. zone을 레벨에 놓기 전에 베이스맵을 올바른 `--geoid-offset`으로 만들거나, 정합(WP-07)에서 그 차이를 흡수한다.
- **ENU → UE**: `(x, y, z)_m → (100x, −100y, 100z)_cm`. 행렬 `S = diag(100, −100, 100)`. `unreal/Golmok/Content/Python/golmok/basemap_import.py`의 `TARGET`과 같다(Cesium for Unreal 규약).
- **yaw**: `yaw_deg`는 위에서 내려다볼 때 +x(동)에서 **반시계**(동→북) 각도다. UE는 Y가 남쪽이라 **UE Yaw = −yaw_deg**.
- zone-local은 zone 원점의 접평면 ENU라서 area ENU와 **완전히 평행하지 않다**(지구 곡률). 원점이 200 m 떨어지면 약 0.002° 기운다. 그래서 변환은 항상 4×4 전체를 쓴다(§4 예제 C).

## 2. 폴더 레이아웃

```
zones/<zone_id>/v<version>/          ← 불변. 고치려면 golmok-zone bump로 새 version
  manifest.json
  visual/<chunk_id>.glb …            ← layers.visual.chunks[].uri (manifest 폴더 기준 상대경로)
  collision.glb
  blockers.json
index/zones.json                     ← golmok-zone index build
index/cells/16_<x>_<y>.json
```

- `zone_id`: `^z_[a-z0-9]+(_[a-z0-9]+)*$`, 64자 이하. 예 `z_yeonnam_alley_001`, 실내 `z_yeonnam_alley_001_cafe`.
- `uri`는 manifest 폴더 기준 **상대경로**, `/` 구분, `..`·절대경로·스킴 금지.
- 청크·포털·blocker `id`: `^[A-Za-z0-9][A-Za-z0-9_]*$`(UE 에셋 이름에 그대로 들어간다).

## 3. manifest 필드

| 필드 | 형식 | 필수 | 설명 |
|---|---|---|---|
| `schema_version` | `1` | ✔ | 이 문서 버전 |
| `zone_id` | string | ✔ | §2 형식. 폴더 이름과 같아야 한다 |
| `version` | int ≥ 1 | ✔ | 폴더 `v<version>`과 같아야 한다 |
| `kind` | `exterior` \| `interior` | ✔ | |
| `parent_zone` | zone_id \| null | ✔ | interior면 붙어 있는 exterior zone(필수), exterior면 `null` |
| `origin` | `{lat, lon, height_ellipsoidal}` double | ✔ | zone-local (0,0,0)의 측지 좌표. transform에서 **파생**되며 1 mm 안에서 일치해야 한다 |
| `origin_ecef` | `[x, y, z]` m | ✔ | = transform의 이동 성분(파생값, 1 mm 안에서 일치) |
| `transform` | 16 double | ✔ | zone-local ENU(Z-up, m) → ECEF 4×4, **row-major** `[r00,r01,r02,tx, r10,r11,r12,ty, r20,r21,r22,tz, 0,0,0,1]`. 회전은 직교·det=+1(rigid, 스케일 없음). 정합(WP-07)이 이 값을 고친다 |
| `footprint_wgs84` | GeoJSON Polygon `[lon, lat]` | ✔ | 이 zone이 권위를 갖는 영역. 감는 방향 무관, 링은 닫혀 있어야 함(RFC 7946). origin은 footprint 안이거나 50 m 이내 |
| `replaces.building_ids` | string[] | ✔ | 숨길 베이스맵 건물(GIS건물통합정보 키). MVP에서는 기록만 하고 실제 제거는 `exclude`(D-012) |
| `replaces.terrain_clip` | bool | ✔ | footprint 안 베이스맵 지면 숨김 |
| `layers.visual.format` | `nanite_mesh` \| `splat_ply` \| `splat_3dtiles` \| `splat_lcc` | ✔ | D-010 전이라 enum만 열어 둔다. **로더는 `nanite_mesh`부터** 구현 |
| `layers.visual.chunks[]` | `{id, uri, bbox_enu:[[min],[max]], tris?}` | ✔(빈 배열 허용) | bbox는 zone-local m. init 직후엔 비어 있고(경고) 후처리(WP-03)가 채운다 |
| `layers.visual.textures[]` | `{uri, chunk_id?, role?}` | | GLB에 텍스처를 넣지 않을 때만 |
| `layers.collision` | `{format:"glb", uri, chunks?}` | ✔ | 단순화된 충돌 메시(zone-local m) |
| `layers.blockers` | `{uri}` | | 유리면·접근 금지 평면 파일(§3.1) |
| `layers.navmesh` | `{format:"recast", uri}` | | 선택. UE가 collision으로 직접 만든다 |
| `portals[]` | `{id, to_zone, pose_enu:{position:[x,y,z], yaw_deg}, radius_m, kind:"door"}` | ✔(빈 배열 허용) | position은 zone-local m, yaw는 **들어가는 방향**. `to_zone`은 zone_id(버전은 Index에서 최신으로 해석), 자기 자신 금지 |
| `priority` | int | ✔ | 겹치면 큰 쪽이 이긴다. 같으면 최신 version |
| `quality` | `{icp_rmse_m, footprint_iou, reviewed_by, reviewed_at, …}` | ✔ | 값은 null 가능, 추가 키 허용. `bump`는 reviewed_*를 비운다 |
| `consent` | `{type: public_street \| owner_consent, record_id}` | ✔ | owner_consent인데 record_id가 없으면 경고(게시 전 필수) |
| `attribution` | string[] | ✔ | 크레딧 표기 |
| `sources[]` | `{capture_id, note?}` | ✔ | [captures/INDEX.md](../captures/INDEX.md)의 촬영 ID |

알 수 없는 최상위 키는 **스키마 오류**다(`quality`만 추가 키 허용).

### 3.1 blockers 파일

```json
{ "planes": [ { "id": "glass_1", "center_enu": [-12, 10, 1.5], "normal_enu": [0, -1, 0],
                "size_m": [3.0, 2.5], "kind": "glass" } ] }
```
- 사각형 평면. `center_enu`·`normal_enu`는 zone-local. `size_m = [폭, 높이]`.
- **높이 축** = zone +z를 평면에 투영한 방향(수직 벽이면 위쪽). 평면이 수평(normal ∥ z)이면 높이 축은 +y(북). 폭 축 = 높이 축 × normal.
- `kind`: `glass`(보이지만 못 지나감), `no_entry`(보이지 않는 벽).

### 3.2 의미 검사 (`golmok-zone validate`)

스키마로 표현 못 하는 것:
- transform이 rigid인가(|RᵀR−I| ≤ 1e−9, det = +1 ± 1e−9, 마지막 행 [0,0,0,1]).
- `origin`·`origin_ecef`·transform 이동 성분이 1 mm 안에서 일치하는가.
- zone +z가 연직에서 0.5° 넘게 기울면 **경고**(정합 결과인지 확인).
- footprint: 유효(자기교차 없음), 링 닫힘, 면적 ≥ 1 m², origin과의 거리 ≤ 50 m(밖이면 경고).
- 청크·포털 id 중복, bbox min ≤ max, 포털 `to_zone` ≠ 자기 자신.
- 경로: `<zone_id>/v<version>/manifest.json`과 폴더 이름이 맞는가.
- `--check-files`: 참조 파일이 있는가, blockers 파일이 스키마를 통과하는가, normal 길이 > 0.

## 4. 좌표 변환 수치 예제 (WP-04 C++ 단위테스트 기준값)

`tools/tests/test_zone_transform.py`가 아래 표를 이 문서에서 직접 읽어 Python 구현·pyproj와 비교한다. **표를 고치면 테스트가 깨진다**(의도).

WGS84: a = 6378137 m, f = 1/298.257223563, e² = f(2−f).
`N = a / sqrt(1 − e² sin²φ)`, `X = (N+h) cosφ cosλ`, `Y = (N+h) cosφ sinλ`, `Z = (N(1−e²)+h) sinφ`.

### A. 측지 → ECEF (m)

<!-- table:ecef -->
| lat | lon | h | X | Y | Z |
|---|---|---|---|---|---|
| 37.5620 | 126.9250 | 50.0 | -3041244.8025 | 4046878.9767 | 3867051.5610 |
| 37.5620 | 126.9250 | 0.0 | -3041220.9912 | 4046847.2918 | 3867021.0800 |
| 37.5600 | 126.9230 | 40.0 | -3041180.0675 | 4047086.9764 | 3866869.5020 |
| 0.0000 | 0.0000 | 0.0 | 6378137.0000 | 0.0000 | 0.0000 |
| 90.0000 | 0.0000 | 0.0 | 0.0000 | 0.0000 | 6356752.3142 |
<!-- /table -->

### B. zone-local → ECEF, 원점 (37.5620, 126.9250, h=50)

yaw 0일 때 transform(row-major, 소수 10자리):
```
-0.7994225996  0.3662405942 -0.4762261378  -3041244.8025000524
-0.6007690964 -0.4873436561  0.6336976042   4046878.9766597343
 0.0000000000  0.7926941327  0.6096195634   3867051.5610148320
 0             0             0              1
```
열 = 동·북·위 단위벡터(ECEF). 동 = (−sinλ, cosλ, 0), 북 = (−sinφ cosλ, −sinφ sinλ, cosφ), 위 = (cosφ cosλ, cosφ sinλ, sinφ). yaw ≠ 0이면 `R = R_enu · Rz(yaw)`.

<!-- table:zone -->
| yaw_deg | zone-local (m) | ECEF X | ECEF Y | ECEF Z | UE zone-local (cm) |
|---|---|---|---|---|---|
| 0 | 0, 0, 0 | -3041244.8025 | 4046878.9767 | 3867051.5610 | 0, 0, 0 |
| 0 | 10, 0, 0 | -3041252.7967 | 4046872.9690 | 3867051.5610 | 1000, 0, 0 |
| 0 | 0, 10, 0 | -3041241.1401 | 4046874.1032 | 3867059.4880 | 0, -1000, 0 |
| 0 | 0, 0, 10 | -3041249.5648 | 4046885.3136 | 3867057.6572 | 0, 0, 1000 |
| 30 | 10, 0, 0 | -3041249.8945 | 4046871.3371 | 3867055.5245 | 1000, 0, 0 |
| 30 | 0, 10, 0 | -3041237.6337 | 4046877.7600 | 3867058.4259 | 0, -1000, 0 |
<!-- /table -->

### C. zone-local → area ENU → UE 레벨 (cm)

area 원점(= CesiumGeoreference 원점) (37.5600, 126.9230, h=40). `M = inv(T_area) · T_zone`, UE 위치 = `S · (M · p)`.

<!-- table:area -->
| yaw_deg | zone-local (m) | area E | area N | area U | UE 레벨 (cm) |
|---|---|---|---|---|---|
| 0 | 0, 0, 0 | 176.7059 | 221.9800 | 9.9937 | 17670.59, -22198.00, 999.37 |
| 0 | 10, 0, 0 | 186.7059 | 221.9802 | 9.9934 | 18670.59, -22198.02, 999.34 |
| 0 | 0, 10, 0 | 176.7057 | 231.9800 | 9.9933 | 17670.57, -23198.00, 999.33 |
| 30 | 10, 0, 0 | 185.3661 | 226.9802 | 9.9933 | 18536.61, -22698.02, 999.33 |
| 30 | 0, 10, 0 | 171.7058 | 230.6401 | 9.9935 | 17170.58, -23064.01, 999.35 |
<!-- /table -->

- 두 원점이 약 290 m 떨어져 있어 회전 성분에 약 3e−5(≈0.002°)의 기울기가 생긴다. **순수 yaw로 근사하지 않는다.**
- yaw 30: area에서 zone +x = (0.866, 0.500, ·) → UE에서 (0.866, −0.500, ·) → UE Yaw ≈ **−30°**.
- 확인 명령: `golmok-zone transform <manifest> --enu 10,0,0 --area-origin 37.5600,126.9230,40`.

## 5. UE 매핑 규약 (WP-04·WP-06이 그대로 구현)

| 항목 | 규약 |
|---|---|
| manifest 위치(패키지) | `Content/Golmok/Zones/<zone_id>/v<version>/manifest.json` (non-asset 파일. 패키지에 넣는 방법(예: Packaging의 "Additional Non-Asset Directories to Package")은 WP-04가 확정) |
| 시각 청크 에셋 | `/Game/Golmok/Zones/<zone_id>/v<version>/SM_<chunk_id>` |
| 충돌 에셋 | `/Game/Golmok/Zones/<zone_id>/v<version>/SM_<zone_id>_collision` (collision.chunks가 있으면 `SM_<zone_id>_collision_<chunk_id>`) |
| 실내 서브레벨 | `/Game/Golmok/Zones/<zone_id>/v<version>/L_<zone_id>` |
| 메시 정점 | 임포트 후 zone-local을 `S = diag(100,−100,100)`로 바꾼 값(cm, X=동, Y=남, Z=위). 임포터의 축 변환은 가정하지 말고 bbox로 측정한다(`basemap_import.py`와 같은 방식) |
| zone 루트 actor 변환 | `S · M · S⁻¹` (M = zone-local → area ENU). 회전 = `D R D`(D = diag(1,−1,1), det +1), 위치 = `S t` cm. `golmok-zone transform --json`의 `ue_actor_matrix` |
| 포털 | 위치 `S · position`, UE Yaw = `−yaw_deg`, 반경 cm = `100 · radius_m` |
| blocker | 중심 `S · center`, 법선 `D · normal`, 크기 cm = `100 · size_m` |
| bbox | `S`로 바꾼 뒤 min/max를 다시 정렬한다(Y 부호가 뒤집힘) |

C++(WP-04)는 §4의 A·B·C 표 값을 단위테스트 기준으로 쓴다(허용 오차 1e−4 m).

## 6. Zone Index

게임은 플레이어 주변 셀 파일을 읽고, 셀에 있는 zone의 manifest를 로드한다(ARCHITECTURE §4-1).

- `index/zones.json`
  ```json
  { "schema_version": 1, "cell_zoom": 16,
    "zones": [ { "id": "z_synthetic_001", "version": 1, "kind": "exterior", "priority": 10,
                 "bbox_wgs84": [126.924773635, 37.561909901, 126.925226365, 37.562090099],
                 "manifest": "z_synthetic_001/v1/manifest.json" } ] }
  ```
  zone당 한 줄, **최신 유효 version만**. `bbox_wgs84 = [west, south, east, north]`. `manifest`는 zones 루트 기준. id 순 정렬.
- `index/cells/16_<x>_<y>.json` — 웹 메르카토르 XYZ 타일(z16, 서울에서 한 변 약 480 m). `x = floor((lon+180)/360 · 2^z)`, `y = floor((1 − asinh(tan φ)/π)/2 · 2^z)`(y는 남쪽으로 증가).
  ```json
  { "schema_version": 1, "z": 16, "x": 55873, "y": 25379,
    "zones": [ { "id": "z_synthetic_001", "version": 1 } ] }
  ```
  footprint 폴리곤과 **실제로 겹치는** 타일만(bbox가 아니라). `zones`는 이기는 순서: priority 내림차순 → version 내림차순 → id.
- 스키마 검사에 실패한 최신 버전은 건너뛰고 그 아래 유효한 버전을 쓴다(경고 출력, `--strict`면 실패).
- 게시·롤백은 index만 다시 만들어 바꾼다(버전 폴더는 불변, ARCHITECTURE §4-6).

## 7. 베이스맵 제외 (`golmok-zone exclude`)

- exterior zone의 최신 유효 version footprint를 `--buffer-m`(기본 0.75 m, ≥ 0)만큼 **바깥으로** 넓혀 합친 GeoJSON FeatureCollection을 만든다. 각 Feature의 `properties.zone_ids`에 기여한 zone이 있다.
- `golmok-basemap build --exclude exclude.geojson`은 이 폴리곤과 **겹치는 건물을 통째로** 뺀다(D-012). buffer는 ARCHITECTURE §4-4의 0.5~1 m 오버랩 띠다: 경계에 닿은 베이스맵 건물까지 빠지므로 **zone 메시가 footprint 바깥 buffer 폭까지 덮어야** 구멍이 없다.
- interior zone은 제외에 들어가지 않는다.

## 8. CLI 요약

```
golmok-zone init --id z_… --kind exterior|interior --origin lat,lon[,h] --footprint fp.geojson [--yaw 0] [--parent z_…] [--capture ID] --out zones/z_…/v1
golmok-zone validate <manifest.json>… [--check-files] [--strict]
golmok-zone index build --zones-root zones --out index [--strict]
golmok-zone exclude --zones-root zones --out exclude.geojson [--buffer-m 0.75]
golmok-zone transform <manifest.json> --enu x,y,z [--area-origin lat,lon,h] [--json]
golmok-zone bump <manifest.json>
```
종료 코드: 0 성공, 1 검사 실패, 2 입력 오류.
