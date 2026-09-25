# WP-08 — (선택) 웹 내부 검수 뷰어 `tools/viewer`

상태: 🟢 완료(1차 2026-09-24 WP-08, 2차 2026-09-25 WP-11) · 담당: 클라우드 Claude 세션 · 의존: WP-02 · 검증: G1(Playwright 스모크)

ROADMAP 1.6의 "(웹, 선택)" 항목이다. WP-05의 UE 디버그 도구가 검수 역할을 먼저 맡으므로 **기본 실행에서 제외**한다. 사용자가 켜면 아래 범위로 진행한다.

## 범위(요약)
- Three.js + 3DTilesRendererJS(MIT)로 `golmok-basemap`의 `tileset.json` 로드, Zone manifest footprint·portals·chunk bbox 오버레이, `collision.glb` 와이어프레임, (가능하면) splat 3D Tiles(WP-03 `golmok-splat tiles`) 로드.
- 정적 사이트(Vite), `npm test`로 Playwright 스모크(페이지 로드, 타일셋 로드 이벤트).
- D-007: 로컬 파일만 읽는다. 외부 업로드 없음.

## 결과
- **1차(WP-08, session_01Cgm7f6oD6xSMpZ5jszj8Xi, 2026-09-24)**: 범위의 Three.js 대신 **CesiumJS 1.145**(Apache-2.0, ion 토큰 없음)로 구현 — 3D Tiles·지구 좌표를 그대로 다룬다. `golmok-viewer` 서버(`/data/`, `/cesium/` 오프라인) + `tools/viewer`(레이어 토글·와이어프레임·타일 경계·ENU 좌표 읽기·통계) + Zone manifest 오버레이(footprint·원점·청크 bbox·포털·blockers 평면, `?zone=…/manifest.json`) + Playwright 스모크(`npm test`, 합성 베이스맵 18타일). 충돌 메시는 WP-03 산출물 뒤로 넘김.
- **2차(WP-11, session_01CSQya6KM72tpKC8L7aowSx, 2026-09-25)**: collision/blockers **GLB 메시** 오버레이(`Cesium.Model`, glTF Y-up → zone-local → ECEF, Cesium 기본 축 보정 끔), 오버레이 체크박스(footprint/원점·축/청크 bbox/충돌/blockers/포털), 원점 E·N·U 삼축, `golmok-viewer --zone`(`/zones/<zone_id>/v<n>/`, 경로 탈출 거절), `zonemath.js` 단위·교차검증, 스모크 확장(zone 2개·모델 4개·배치·토글). OBJ 청크는 bbox만(README). 상세 [`WP-11-viewer-collision-overlay.md`](WP-11-viewer-collision-overlay.md) "결과", 사용법 [`tools/viewer/README.md`](../../tools/viewer/README.md).
