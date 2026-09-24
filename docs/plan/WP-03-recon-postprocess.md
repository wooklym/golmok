# WP-03 — 재구성 후처리 도구 `golmok-mesh` / `golmok-splat`

상태: 🟢 완료 · 담당: 클라우드 Claude 세션 · 의존: WP-02 · 검증: G1, 이후 G3(RealityScan/Postshot 실출력)

## 목표
RealityScan(메시)과 Postshot(splat) 출력을 **UE와 스파이크가 바로 쓰는 형태**로 바꾼다. 청크 분할, 충돌 메시, blocker, splat 정리, 그리고 스파이크 (b)에 필요한 **로컬 PLY→3D Tiles 변환기**(D-007: 외부 업로드 없이).

## 배경
- `docs/research/02` §3(이중 표현, 충돌 메시 생성 단계), `research/07` §3(RealityScan 내보내기: 10~20m 청크, 5~15M tri, 8K UDIM, VT), §5(Cesium splat 3D Tiles)
- D-002 라이선스: **trimesh(MIT), open3d(MIT), numpy** 사용 가능. **OpenMVS·Ultralytics·OpenSplat(AGPL) 금지.** `fast-simplification`(MIT) 가능. pymeshlab은 GPL이므로 **사용하지 않는다**.
- WP-02 스펙(`docs/spec/zone-manifest.md`)의 chunk/collision/blockers 필드.

## 산출물
### A. `tools/golmok_tools/mesh/` → CLI `golmok-mesh`
1. `chunk`: 입력 OBJ/GLB(RealityScan 내보내기, zone-local 좌표 가정) → `--size 15`(m) 격자 또는 `--along path.geojson`(골목 중심선 기준 구간)으로 분할. **UV·머티리얼·UDIM 타일 할당을 보존**한다(면 단위 분할, 정점 복제). 출력 `chunks/<chunk_id>.obj`(+.mtl) 또는 `.glb`(텍스처 미포함) 중 UE 임포트에 안전한 쪽을 택하고 이유를 문서에 적는다. `chunk_manifest.json`: 청크별 bbox_enu, tri 수, 사용 UDIM 타일, 원본 텍스처 파일 목록. manifest.json의 `layers.visual.chunks`도 갱신(`--manifest`).
2. `collision`: 전체 또는 청크 메시 → 충돌 메시. 단계: 작은 연결요소 제거(`--min-component-m2`) → (선택) hole fill → **바닥 RANSAC 평면 스냅**(`--snap-ground`, open3d `segment_plane`; 평면에서 ±`--snap-tol` 안 정점을 평면으로 투영) → 쿼드릭 데시메이션(목표 `--target-tris 30000` 또는 `--ratio`) → `collision.glb`. 옵션 `--per-chunk`. 결과 통계(면 수, 바운드, 노멀 위쪽 비율) 출력.
3. `blockers`: `blockers.json`(WP-02 스펙 평면 목록) → 얇은 박스 메시 `blockers.glb`(두께 2cm). `blockers add --center x,y,z --normal nx,ny,nz --size w,h --kind glass`로 항목 추가.
4. `inspect`: 메시 통계(면·정점·바운드·머티리얼·UDIM 타일·비매니폴드 여부).

### B. `tools/golmok_tools/splat/` → CLI `golmok-splat`
1. `ply.py`: 3DGS PLY 읽기·쓰기(속성 `x y z nx ny nz f_dc_0..2 f_rest_0..44 opacity scale_0..2 rot_0..3`; SH 차수 0~3 자동 감지; binary little endian). numpy 구조화 배열.
2. `inspect`: 개수, 바운드, opacity/scale 분포, SH 차수.
3. `crop`: bbox_enu 또는 zone footprint(manifest, `--margin-m`)로 자르기.
4. `clean`: 플로터 제거(kNN 평균거리 `--knn 16 --std 2.0`), `--min-opacity`, `--max-scale-m`. 제거 수 리포트.
5. `transform`: 4×4 적용(좌표계 맞추기; RealityScan 정렬 좌표를 쓰면 보통 항등).
6. `tiles`: **PLY → 3D Tiles 1.1(glTF `KHR_gaussian_splatting`)**. 옥트리(또는 그리드) 분할, 리프 타일당 `--max-splats 500000`, 부모 타일은 서브샘플(랜덤 또는 opacity 가중)로 LOD, `geometricError` 계산, `tileset.json`+`tiles/*.glb`. **확장 스펙은 Khronos README(`research/02` 출처 URL)에서 속성 이름·인코딩을 확인하고 문서에 인용**한다. 압축(SPZ 확장)은 이번에 하지 않는다. `npx 3d-tiles-validator`가 있으면 검증 테스트 추가(없으면 skip).

### C. 공통
- `pyproject.toml` extras: `mesh = ["trimesh", "open3d", "fast-simplification"]`, `splat = ["numpy", "scipy"]`(scipy는 kNN용, BSD). LICENSE 원문 확인 → `DECISIONS.md` D-002 표에 행 추가.
- 테스트: 합성 데이터(코드에서 생성)—UV 있는 박스 여러 개를 합친 메시로 chunk·collision·blockers, 랜덤 가우시안 PLY로 inspect·crop·clean·tiles. 왕복(write→read) 일치, tiles 출력 JSON 구조 검사.
- 문서: `tools/README.md` 절 추가, `docs/runbooks/recon-postprocess.md`(RealityScan 내보내기 설정 → golmok-mesh → golmok-splat → 결과 폴더 구조. PC 세션이 그대로 따라 하게).

## 완료 기준
- `pytest` 통과, CI 초록, 새 의존성 라이선스 기록.
- 합성 메시 → chunk → collision → manifest 갱신 → `golmok-zone validate --check-files` 통과(통합 테스트 1개).
- 합성 PLY → tiles → tileset.json 구조 검증.

## 주의
- open3d 휠은 크다(설치 시간). CI `python` 잡의 캐시를 쓰고, 테스트에서 `pytest.importorskip("open3d")`.
- 메모리: 실데이터는 수천만 tri일 수 있다. numpy 벡터화, 청크 단위 처리, 스트리밍 OBJ 파서(trimesh `process=False`)를 고려하고, 메모리 한계는 문서에 적는다.

## 결과
세션: session_014zvy99LzAuVhnHYFtUYfVz (Opus) · 2026-09-24 · 상태 🟢 완료(클라우드 합성 데이터로 완전 검증. 실데이터는 G3/V-05에서)

**한 것**
- `tools/golmok_tools/mesh/` → `golmok-mesh inspect|reproject|chunk|collision|blockers add|build`
  - `objio`: OBJ 읽기/쓰기(v/vt/vn 인덱스 분리, 머티리얼, 음수 인덱스·다각형, 삼각형 전용 벡터화 경로: 40만 tri 읽기 1.5초), GLB 읽기(Y-up → ENU), UDIM 타일 계산, 통계(비매니폴드·경계 에지, 위를 향한 면 비율).
  - `chunk`: 15 m 격자(`c_<열>_<행>`) 또는 경위도 중심선 구간(`s_<n>`), 면 단위 분할·정점 복제로 UV·머티리얼·UDIM 보존. **OBJ+MTL 출력**(glTF는 UDIM이 없고 텍스처 복사 필요 → OBJ가 원본 8K UDIM 경로를 그대로 가리킴), MTL 텍스처 경로 재작성, `chunk_manifest.json`, `--manifest`로 `layers.visual.chunks` 갱신.
  - `collision`: 용접 → 작은 연결요소 제거(scipy csgraph) → (선택) 구멍 채움(trimesh) → **셀별 RANSAC 바닥 평면 스냅**(경사 골목 대응, 선형 배치 inlier 거부) → 쿼드릭 데시메이션(fast-simplification) → GLB. `--per-chunk`는 완성된 충돌 메시를 청크 영역으로 나눔(먼저 청크로 자르면 잘린 조각이 제거돼 구멍이 나는 문제를 합성 테스트에서 발견해 이렇게 바꿈).
  - `blockers`: 스펙 §3.1 축 규약대로 2 cm 박스 GLB(노드 = plane id, extras.kind), `add`.
  - `reproject`(스펙 추가): RealityScan을 EPSG:5186 등 투영 좌표로 내보낸 OBJ → zone-local(UV 보존, 노멀 회전). RealityScan 로컬 원점 설정을 가정하지 않아도 됨.
- `tools/golmok_tools/splat/` → `golmok-splat inspect|crop|clean|transform|tiles`
  - `ply`: 3DGS PLY(SH 0~3 자동, channel-major f_rest, 기타 속성 보존).
  - `ops`: bbox/footprint(+margin) 자르기, kNN 플로터·opacity·크기 필터, 4×4(회전×균일 스케일+이동) 변환 — 위치·쿼터니언·scale·**SH 계수 회전**(밴드별 최소제곱, 오차 1e−9).
  - `tiles`: 옥트리 LOD(부모 = opacity×면적 가중 서브샘플, 확대 보정 지수 0.5·최대 3배, 튜닝용), 3D Tiles 1.1 + glTF `KHR_gaussian_splatting`(Khronos README 원문: 속성 이름, opacity=sigmoid, scale=exp, 쿼터니언 xyzw, POINTS, ellipse, `srgb_rec709_display`, COLOR_0 선형 폴백). glTF Y-up 변환(위치·회전·SH 모두), `--manifest`면 root.transform = zone→ECEF.
- extras `mesh`, `splat`, 스크립트 2개. CI는 extras 설치, tiles-validate 잡에 splat 타일셋 검증 단계 추가.
- 문서: [runbooks/recon-postprocess.md](../runbooks/recon-postprocess.md)(PC 세션용 절차), `tools/README.md` 6) 절, 스펙 §5에 파일 형식 행, D-002(라이선스·open3d 제외), ROADMAP 1.4, docs/README.

**테스트**: `test_mesh.py`(13), `test_mesh_zone_integration.py`(2), `test_splat.py`(14 + 검증기 1) 추가. 전체 `144 passed, 2 skipped`(로컬 3.11). 완료 기준 확인:
- 합성 메시 → chunk → collision(--per-chunk) → blockers → manifest → `golmok-zone validate --check-files` 통과(`test_mesh_pipeline_produces_a_valid_zone`).
- 합성 PLY → tiles → tileset.json 구조·값 검사(부모/자식 geometricError 단조, 리프 합 = 입력 수, bbox가 Y-up 내용 포함, 속성 값이 확장 정의와 일치).
- `3d-tiles-validator@0.6.1`: 타일셋 구조 오류 0. glTF 쪽은 검증기가 확장을 몰라(“not supported” INFO) **확장 속성 이름 오류만** 나오며 테스트는 그것만 허용한다(`GOLMOK_TILES_VALIDATOR=1`).

**판단한 것(사용자 확인 불필요, 되돌리기 쉬움)**
- open3d 제외(위 D-002). 청크 형식 OBJ. `reproject` 추가. 부모 타일 확대 보정 휴리스틱(끄려면 `--lod-scale-exp 0`).

**남은 것**
- 실데이터 검증(V-05): RealityScan 출력 좌표계 메뉴 이름, GPS 고도 기준(해발/타원체), Postshot splat 좌표계, 1천만 tri 이상 처리 시간·메모리 — 런북 [미확인] 항목. 결과는 런북 하단에 적는다.
- SPZ 압축 확장은 범위 밖(WP 스펙대로).

**다음 WP에 알릴 것**
- WP-04/06: 청크는 `visual/<id>.obj`(Z-up, zone-local m) + MTL(원본 UDIM 텍스처 상대경로). UE 임포트 축 변환은 bbox로 측정(basemap_import 방식). 충돌 `collision.glb`/`collision/<id>.glb`와 `blockers.glb`는 glTF Y-up(동, 위, −북). blocker GLB 노드 이름 = plane id, `extras.kind` = glass|no_entry.
- WP-07: `golmok-mesh reproject`가 투영 좌표 → zone-local을 이미 한다. 정합은 그 결과(또는 청크)에 ICP를 걸고 `transform`만 고친다.

