# WP-11 — 웹 검수 뷰어 2차: 충돌·blocker 메시 오버레이

상태: ⚪ 대기 · 담당: 클라우드 Claude 세션(**Opus**, UE 코드 변경 없음) · 의존: WP-03, WP-08 · 검증: G1(브라우저, Playwright 스모크)

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
(세션이 작성)
