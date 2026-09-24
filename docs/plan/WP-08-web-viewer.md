# WP-08 — (선택) 웹 내부 검수 뷰어 `tools/viewer`

상태: ⏸ 보류 · 담당: 클라우드 Claude 세션 · 의존: WP-02 · 검증: G1(Playwright 스모크)

ROADMAP 1.6의 "(웹, 선택)" 항목이다. WP-05의 UE 디버그 도구가 검수 역할을 먼저 맡으므로 **기본 실행에서 제외**한다. 사용자가 켜면 아래 범위로 진행한다.

## 범위(요약)
- Three.js + 3DTilesRendererJS(MIT)로 `golmok-basemap`의 `tileset.json` 로드, Zone manifest footprint·portals·chunk bbox 오버레이, `collision.glb` 와이어프레임, (가능하면) splat 3D Tiles(WP-03 `golmok-splat tiles`) 로드.
- 정적 사이트(Vite), `npm test`로 Playwright 스모크(페이지 로드, 타일셋 로드 이벤트).
- D-007: 로컬 파일만 읽는다. 외부 업로드 없음.

## 결과
(미시작)
