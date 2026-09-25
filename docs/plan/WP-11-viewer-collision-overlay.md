# WP-11 — 웹 검수 뷰어 2차: 충돌·blocker 메시 오버레이

상태: 🟢 완료(2026-09-25) · 담당: 클라우드 Claude 세션(**Opus**, UE 코드 변경 없음) · 의존: WP-03, WP-08 · 검증: G1(브라우저, Playwright 스모크)

## 목표
`golmok-viewer`(CesiumJS, `tools/viewer`)에서 zone의 **충돌 메시(`layers.collision.uri`, GLB)와 blockers.glb**를 와이어프레임/반투명으로 베이스맵 위에 겹쳐 보고 토글한다. WP-08 STATUS 인계 항목("충돌 메시 표시는 WP-03 산출물 나오면 추가")의 후속이다.

## 배경
- WP-08 `tools/viewer/app.js`: Zone manifest 오버레이(footprint·원점·청크 bbox·포털·blockers 평면 JSON)를 `?zone=…/manifest.json`으로 그린다. `window.golmok`(viewer, layers, zones, ready, errors, stats())로 스모크 테스트가 검사.
- WP-03 산출물: 청크 = `visual/<id>.obj`+MTL(Z-up), 충돌·blocker GLB = **glTF Y-up**. 스펙 §1 축 규약(zone-local Z-up ENU → UE `diag(100,−100,100)`). 뷰어는 zone-local → ECEF 모델 매트릭스가 이미 있다(footprint용).
- 서버 `tools/golmok_tools/viewer/`가 베이스맵 폴더를 같은 오리진으로 서빙(D-007: 로컬 파일만).

## 산출물
1. `tools/viewer/app.js`: manifest `layers.collision.uri`·`layers.blockers.uri`(GLB일 때)를 `Cesium.Model.fromGltfAsync`로 로드 — glTF Y-up → zone-local Z-up → ECEF 모델 매트릭스(스펙 §1과 `golmok-mesh` 출력 규약 그대로, 축 변환은 한 함수로 모아 단위테스트 가능하게), 색·투명도·와이어프레임 토글(UI 체크박스: footprint / chunks bbox / collision / blockers / portals), 원점·축 확인용 삼축 표시. OBJ 청크는 서버가 glTF로 변환하지 않으므로 **표시하지 않고 bbox 유지**(README에 이유 기록). 오류는 `golmok.errors`에 누적.
2. `golmok-viewer` 서버: zone 폴더(manifest가 있는 폴더)의 GLB를 같은 오리진으로 서빙, **경로 탈출 금지**(`..`, 절대경로, 심볼릭 링크) pytest.
3. Playwright 스모크 확장(`tools/viewer/test/smoke.mjs`): 합성 zone(`tools/tests/fixtures/zones/z_synthetic_001/v1` + WP-06 `tools/scripts/make_synthetic_zone.py` 산출 GLB를 테스트 중 생성)으로 collision·blockers 모델 생성·`errors` 0·토글 동작 확인. CI `npm test` 그대로(헤드리스 Chromium, `PLAYWRIGHT_BROWSERS_PATH`).
4. `docs/plan/WP-08-web-viewer.md` 결과 절에 2차 기록, `tools/viewer/README.md` 사용법 갱신, STATUS·ROADMAP 1.6 행 갱신.

## 완료 기준
`npm test` 통과, pytest(서버 경로 테스트·축 변환) 통과, CI 초록, STATUS `🟢`.

## 주의
- 라이선스 D-002: CesiumJS(Apache-2.0) 외 새 의존성 금지. 
- glTF 축 변환은 스펙 §1과 `golmok-mesh`의 출력 규약(collision/blockers GLB = glTF Y-up)을 그대로 따른다. 규약이 모호하면 추측하지 말고 `docs/plan/WP-03-*.md` 결과·`golmok_tools/mesh`의 export 코드를 읽어 확인한 뒤 문서에 인용한다.
- Windows CI: 경로는 `pathlib`, 서브프로세스 `encoding="utf-8"`.

## 결과
세션 session_01CSQya6KM72tpKC8L7aowSx (Opus 5.5 단일 세션, 읽기 전용 리뷰어 1명), 브랜치 `claude/hopeful-allen-f0a0jb`, PR #16.

### 산출물
| # | 파일 | 내용 |
|---|---|---|
| 1 | `tools/viewer/zonemath.js` (신규) | Cesium 없는 순수 함수: `GLTF_TO_ZONE`·`gltfModelMatrix(transform)`(축 변환 **한 곳**), `blockerAxes/blockerCorners`(스펙 §3.1), `resolveZoneUri`(스펙 §2 uri 규칙), `blockersGlbUri`, `unionBoxes`. 브라우저 전역 `GolmokZoneMath` + Node `require` |
| 1 | `tools/viewer/app.js`·`index.html`·`style.css` | `layers.collision.uri`(GLB) → `Cesium.Model.fromGltfAsync`(반투명 주황), `layers.blockers.uri`가 `blockers.json`이면 평면 + 옆 파생 `blockers.glb`(반투명 보라), `.glb`면 GLB만. 모델 매트릭스 = `transform × GLTF_TO_ZONE`, Cesium 기본 축 보정 끔(`upAxis: Z, forwardAxis: X`). "Zone 오버레이" 체크박스 footprint / 원점·축 / 청크 bbox / 충돌 메시 / blockers / 포털(모든 zone), zone 행 체크박스는 zone 전체(메시 포함). 원점 E(빨강)·N(초록)·U(파랑) 5 m 화살표. 와이어프레임 체크박스가 zone 메시에도 적용. OBJ 청크는 bbox만. `golmok.errors`(collision 없음·fetch 실패·잘못된 uri·모델 오류), `golmok.warnings`(파생 blockers.glb 없음). `zoneStats()`·`setOverlay()`. `ready`는 zone 모델 `ready`까지 기다림. zone만 열 때 `loadManifest` 예외(기존 버그) 수정, ENU 읽기는 첫 zone 원점 기준 |
| 2 | `tools/golmok_tools/viewer_server.py` | `--zone <버전 폴더 또는 manifest.json>`(반복) → `/zones/<zone_id>/v<n>/`(manifest의 `zone_id` 정규식·`version` 검사, 중복 거절), `data_dir` 생략 가능. `/zones/`는 `.json .glb .gltf .bin .png .jpg .jpeg .ktx2`만. 모든 루트 공통: `..` 세그먼트·선행 `/`·백슬래시·`:`(드라이브·ADS)·NUL을 파일 시스템 접근 전에 거절, `resolve()`(심볼릭 링크 따라감) 뒤 루트 포함 검사 |
| 3 | `tools/viewer/test/smoke.mjs`·`test/unit.mjs`·`package.json` | `npm test` = 단위(node:test) → 스모크. 스모크: 합성 베이스맵 + WP-02 픽스처 zone(`/data/zones/…`; collision.glb는 생성기 것, blockers.glb는 `golmok-mesh blockers build`로 픽스처 blockers.json에서) + WP-06 생성기 zone(`make_synthetic_zone.py`, `--zone` 마운트). 검사: 모델 4개 `ready`·`bytes>0`, **배치**(모델 월드 bounding sphere 중심 vs manifest `collision.chunks` bbox 합집합 중심 / blockers.json 사각형 bbox 중심, < 5 cm) 그리고 Cesium 기본 보정이었다면 > 1 m 어긋남, 체크박스 6개·zone 행·와이어프레임 토글, `errors`·`warnings`·콘솔 오류 0. 생성물은 `test/out/`(git 무시) |
| 4 | `tools/viewer/README.md` (신규) | 실행·화면·축 변환 근거·OBJ 미표시 이유·자동화 API·테스트 |

### 테스트
- pytest **618 passed, 3 skipped**(이전 569 → +49: `test_viewer_server.py` 2 → 36, `test_viewer_zonemath.py` 14 신규). 심볼릭 링크 테스트는 권한 없는 Windows에서 skip, zonemath 교차검증은 `node`가 PATH에 없으면 skip(GitHub 러너에는 있음).
- `npm test`: 단위 5 pass, 스모크 OK — 18 타일, zone 2개·모델 4개, 배치 오차 collision 6e-9 m·blockers 0 m(Cesium 기본 보정이면 10.6 m), 토글 9항목 통과.
- ruff check/format, `check_repo.py` OK.

### 축 변환 근거 (추측 없이 코드에서 확인)
1. 쓰기: `tools/golmok_tools/basemap/gltf.py` — "Input positions are in the ENU frame (x=east, y=north, z=up, meters). glTF is Y-up, so vertices are written as (east, up, -north)", `enu_to_gltf(v) = [v0, v2, −v1]`. `mesh/collision.py`의 `write_collision_glb`와 `mesh/blockers.py`의 `write_blockers_glb`가 이 `write_glb`를 쓴다(노드 변환 없음).
2. 읽기(정본 역변환): `tools/golmok_tools/mesh/objio.py` — "GLB is glTF Y-up and is converted back: (x, y, z)_gltf -> (x, -z, y)_enu", `gltf_to_enu`.
3. WP-03 결과: "충돌 `collision.glb`/`collision/<id>.glb`와 `blockers.glb`는 glTF Y-up(동, 위, −북)".
4. 스펙 §1: zone-local x=동·y=북·z=위(m, 오른손), §3: `transform`은 zone-local → ECEF 4×4 **row-major**.
5. 따라서 `GLTF_TO_ZONE` = row-major `[1,0,0,0, 0,0,−1,0, 0,1,0,0, 0,0,0,1]`(x축 +90°, det +1). Cesium `Axis.Y_UP_TO_Z_UP`(`@cesium/engine/Source/Scene/Axis.js`, column-major `[1,0,0, 0,0,1, 0,−1,0]`)과 같은 값. Cesium `ModelUtility.getAxisCorrectionMatrix`는 glTF 기본값(upAxis Y, forwardAxis Z)에서 `Z_UP_TO_X_UP`까지 곱해 zone을 90° 돌리므로(동 → 북) 끄고 우리 행렬만 쓴다.
6. 검증: `tests/test_viewer_zonemath.py`가 zonemath.js를 Node로 실행해 `enu_to_gltf`/`gltf_to_enu`, `zone.transform.zone_transform`(yaw 0/30/−135°)·`enu_to_ecef`, `blockers.plane_axes`/`plane_box`(법선 7종), **실제 `blockers.glb`의 raw POSITION**과 비교. 브라우저에서는 스모크의 배치 검사.
- "확인 필요" 항목 없음. 단 실측 zone(RealityScan 내보내기)은 `golmok-mesh collision --up`으로 입력 축을 맞춘 뒤 GLB가 위 규약으로 나오므로, V-05에서 실제 zone을 뷰어로 열어 원점 축과 메시가 맞는지 한 번 볼 것.

### 리뷰
읽기 전용 리뷰어 1명(34f6160): 블로킹 없음. 축 변환·Cesium 옵션(`upAxis Z/forwardAxis X` → 보정 항등, `gltf: Uint8Array`+`basePath` 유효, `show:false`여도 `ready`)과 Windows 경로(드라이브·UNC·ADS·예약 이름·8.3·끝 점/공백) 탈출 없음을 확인. minor 4건 반영: ① `resolve()`의 `is_dir()`가 긴 이름(ENAMETOOLONG)에서 예외 → 연결 끊김 대신 404(테스트 추가, 기존 `/data`·뷰어 경로도 해당) ② manifest JSON·필수 필드 오류를 `golmok.errors`에 기록 ③ GLB 로딩 중 zone 행 제거 시 모델 고아 방지(`zone.removed`) ④ `errorEvent`가 난 모델은 `ready` 대기에서 제외(60 초 대기 방지). 지적된 약점: 스모크 배치 검사는 중심만 비교 — 점 단위 대응은 `test_viewer_zonemath.py`가 맡는다.

### 남은 것
- CI에는 `npm test` 잡이 없다(WP-08부터 로컬 게이트). 축 변환은 CI python 잡의 `test_viewer_zonemath.py`(Node)로 검사된다. 필요하면 별도 WP로 Playwright CI 잡(브라우저 다운로드 포함) 추가.
- `layers.collision.chunks[]`(청크별 충돌 GLB)는 전체 `collision.glb`와 같은 메시를 나눈 것이라 그리지 않는다. 청크 경계 검수가 필요해지면 추가.
- splat 3D Tiles(`golmok-splat tiles`)는 기존 타일셋 추가 경로(`?tileset=`)로 열린다. `KHR_gaussian_splatting` 렌더 확인은 D-010 스파이크(V-05) 뒤.
