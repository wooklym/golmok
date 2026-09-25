# Golmok 검수 뷰어 (`golmok-viewer`, CesiumJS)

베이스맵 3D Tiles와 Zone manifest 오버레이(footprint·원점 축·청크 bbox·포털·blockers)와 **충돌·blocker 메시(GLB)**를 한 화면에서 보는 내부 검수 도구다. 로컬 파일만 읽는다(D-007, Cesium ion 토큰 없음). WP-08(1차), WP-11(2차: 메시 오버레이).

## 실행

```powershell
cd tools; pip install -e ".[dev]"
cd viewer; npm install          # Cesium 1.145를 node_modules에 받아 오프라인으로 쓴다(없으면 CDN)

# 베이스맵만
golmok-viewer D:\golmok_basemap\yeonnam
# 베이스맵 + zone (manifest.json 이 있는 zone 버전 폴더 또는 그 manifest.json, 반복 가능)
golmok-viewer D:\golmok_basemap\yeonnam --zone D:\golmok\zones\z_yeonnam_alley_001\v1
# zone만
golmok-viewer --zone D:\golmok_synth\zones\z_synthetic_scan_001\v1
```

- `--zone`은 폴더를 `/zones/<zone_id>/v<version>/`로 서빙하고 URL에 `&zone=/zones/<zone_id>/v<version>/manifest.json`을 붙인다. zone이 베이스맵 폴더 안에 있으면 `?zone=/data/<상대경로>/manifest.json`으로도 열 수 있다.
- 패널 입력칸에 `…/tileset.json` 또는 `…/manifest.json` URL을 넣어 나중에 추가할 수도 있다.
- 서버는 각 루트(`/data/`, `/zones/…/`, `/cesium/`, 뷰어) 밖으로 나가는 경로(`..`, 절대·드라이브 경로, 백슬래시, NUL, 루트 밖을 가리키는 심볼릭 링크)를 404로 거절한다. `/zones/`는 `.json .glb .gltf .bin .png .jpg .jpeg .ktx2`만 준다(OBJ 청크는 주지 않는다).

## 화면

| 체크박스 | 내용 | 출처 |
|---|---|---|
| footprint | `footprint_wgs84` 링(노랑, origin 높이) | manifest |
| 원점·축 | zone 원점 점·라벨, zone-local **E(빨강)·N(초록)·U(파랑)** 5 m 화살표 | `transform` |
| 청크 bbox | `layers.visual.chunks[].bbox_enu` 상자(하늘색) | manifest |
| 충돌 메시 | `layers.collision.uri` GLB, 반투명 주황 | golmok-mesh collision |
| blockers | `blockers.json` 평면(유리 청록·접근 금지 빨강) + 파생 `blockers.glb`(반투명 보라, 2 cm 박스) | golmok-mesh blockers |
| 포털 | 위치 점·`id → to_zone` 라벨·들어가는 방향 선(분홍) | manifest `portals` |

- 체크박스는 모든 zone에 함께 적용되고, 레이어 목록의 zone 행 체크박스는 그 zone 전체(메시 포함)를 켜고 끈다. zone 이름을 누르면 그 zone으로 날아간다.
- "와이어프레임"은 타일셋과 zone 메시에 같이 적용된다.
- `layers.blockers.uri`가 `blockers.json`(정본, 스펙 §3.1)이면 평면을 그리고 같은 이름의 `blockers.glb`를 함께 찾는다. GLB가 없으면 경고(`golmok.warnings`)만 남긴다(파생물이라). uri가 GLB면 GLB만 그리고, 없으면 오류다. collision GLB가 없으면 오류(`golmok.errors`)다.

### 축 변환 (glTF Y-up → zone-local Z-up → ECEF)

`golmok-mesh`가 쓰는 collision/blockers GLB는 glTF Y-up이다: `golmok_tools/basemap/gltf.py`의 `enu_to_gltf`가 zone-local `(동, 북, 위)`를 **`(동, 위, −북)`**으로 쓰고, `golmok_tools/mesh/objio.py`의 `gltf_to_enu`가 `(x, y, z)_gltf → (x, −z, y)_enu`로 되읽는다(WP-03 결과 "충돌 `collision.glb`/`collision/<id>.glb`와 `blockers.glb`는 glTF Y-up(동, 위, −북)"). 뷰어는 이 역변환을 `zonemath.js`의 `GLTF_TO_ZONE`(x축 +90° 회전, Cesium `Axis.Y_UP_TO_Z_UP`과 같은 값) 하나로 두고, 모델 매트릭스 = `manifest.transform`(row-major, zone-local → ECEF, 스펙 §1·§3) × `GLTF_TO_ZONE`이다.

**Cesium 기본 축 보정은 끈다**(`Model.fromGltfAsync({upAxis: Axis.Z, forwardAxis: Axis.X})`). Cesium은 glTF에 기본으로 `Y_UP_TO_Z_UP`뿐 아니라 `Z_UP_TO_X_UP`(glTF +Z 전방 → +X)까지 곱하는데(`@cesium/engine/Source/Scene/Model/ModelUtility.js` `getAxisCorrectionMatrix`), 그러면 zone이 90° 돌아간다(동 → 북). 스모크 테스트가 그 차이(합성 zone에서 10.6 m)와 올바른 배치(오차 < 5 cm)를 둘 다 확인한다.

### OBJ 청크를 그리지 않는 이유

시각 청크는 `visual/<id>.obj` + MTL(Z-up, 원본 UDIM 텍스처 경로, WP-03)이다. 브라우저가 직접 그리려면 서버가 OBJ → glTF 변환과 UDIM 타일 텍스처 처리를 해야 하는데(glTF에는 UDIM이 없다), 이 뷰어의 목적(배치·충돌·blocker 검수)에는 필요 없고 8K UDIM을 브라우저에 올리는 비용이 크다. 그래서 청크는 **bbox만** 그린다. 시각 품질 검수는 UE(PIE, WP-05 디버그 도구)에서 한다. `/zones/`는 OBJ를 서빙하지도 않는다.

## 자동화 (`window.golmok`)

`{ viewer, layers, zones, overlay, ready, errors, warnings, stats(), zoneStats(), setOverlay(kind, on) }`. `ready`는 모든 타일셋 `tilesLoaded`와 zone 모델 `ready`(또는 60 초) 뒤 true. `zoneStats()`는 zone별 엔티티 수·그룹 표시 상태·모델(`url`, `bytes`, `ready`, `show`, 월드 bounding sphere)을 준다.

## 테스트

```bash
cd tools/viewer && npm install && npm test   # = node test/unit.mjs && node test/smoke.mjs
cd tools && python -m pytest -q tests/test_viewer_server.py tests/test_viewer_zonemath.py
```

- `test/unit.mjs`(node:test, 의존성 없음): `zonemath.js` 축 변환·blocker 축·uri 규칙.
- `tests/test_viewer_zonemath.py`: 같은 함수를 Node로 돌려 Python 정본(`enu_to_gltf`/`gltf_to_enu`, `blockers.plane_axes`/`plane_box`, `zone.transform`, 실제 `blockers.glb` 정점)과 비교(`node`가 없으면 skip).
- `tests/test_viewer_server.py`: 라우팅, `--zone` 마운트, 경로 탈출(`..`·절대·드라이브·백슬래시·NUL·Windows 예약 장치 이름·심볼릭 링크) 거절, zone_id 64자 제한, CORS 헤더 없음.
- `test/smoke.mjs`(헤드리스 Chromium, `PLAYWRIGHT_BROWSERS_PATH`; `playwright install`은 하지 않는다): 합성 베이스맵(18타일) + WP-02 픽스처 zone(`/data/zones/…`, 생성기 collision.glb와 `golmok-mesh blockers build`로 만든 blockers.glb; `GOLMOK_DATA`로 실제 베이스맵을 주면 픽스처는 `test/out/`에 복사해 `--zone`으로 마운트하므로 그 폴더에는 쓰지 않는다) + WP-06 생성기 zone(`make_synthetic_zone.py`, `--zone` 마운트). collision·blockers 모델 4개 생성, 배치(bounding sphere 중심 vs manifest bbox·blockers.json), 체크박스 토글·zone 행 토글·와이어프레임, `errors`·`warnings`·콘솔 오류 0. 생성물은 `test/out/`(git 무시). 환경변수 `GOLMOK_DATA`(베이스맵 폴더), `GOLMOK_PORT`, `GOLMOK_SHOT`, `PLAYWRIGHT_PROXY`, `PLAYWRIGHT_CHROMIUM`.

## 라이선스

CesiumJS 1.145(Apache-2.0)와 테스트용 Playwright(Apache-2.0)만 쓴다(D-002). 다른 npm 의존성은 없다.
