# WP-07 — 정합·검수 도구 `golmok-align`

상태: 🟢 완료(합성 검증, 실 Zone은 V-05) · 세션: session_01Cgm7f6oD6xSMpZ5jszj8Xi · 담당: 클라우드 Claude 세션 · 의존: WP-02, WP-03 · 검증: G1, 이후 G3(실 Zone)

## 목표
Zone을 베이스맵 위 올바른 위치·스케일·방향에 놓고(ARCHITECTURE §5 ⑦), 품질 지표를 manifest에 기록하며(⑧ 자동 지표), 렌더 결과의 블러 누락을 재검사한다(05 문서, ROADMAP 1.6).

## 배경
- `research/02` §4 정합(GPS prior → similarity → ICP, 지표: ICP RMSE·footprint IoU·수직 기울기)
- `golmok-basemap` 출력(`manifest.json`, `tiles/b_*.glb` 건물, `tiles/t_*.glb` 지형), `basemap/geo.py`
- `golmok-blur`의 `gps_priors.csv`(사진별 GPS), RealityScan 카메라 포즈 내보내기 형식(CSV/XMP — 세션이 공식 문서로 형식 확인·인용)
- WP-02 `transform`, WP-03 `collision.glb`, `golmok-splat`

## 산출물 (`tools/golmok_tools/align/` → CLI `golmok-align`)
1. `poses.py`: RealityScan 카메라 포즈 파일(CSV 우선, XMP 보조) 파서 → 이름, 위치(zone-local), 회전. `gps_priors.csv`와 사진 이름으로 조인.
2. `prior.py`: 카메라 zone-local 위치 ↔ GPS(ENU 변환, area origin 기준)로 **Umeyama 유사변환**(scale·R·t) 추정, RANSAC로 GPS 이상치 제거. RealityScan이 이미 지오레퍼런싱했으면(`--already-georeferenced`) 스케일 1 고정.
3. `icp.py`: Zone 충돌 메시(또는 splat 포인트)에서 샘플링 → 베이스맵 건물 GLB(LOD1 벽면)와 open3d point-to-plane ICP. 지면 포인트는 DEM 지형 타일과 별도 ICP(`--ground`). 초기값은 prior. 수렴 조건·최대 보정 한계(`--max-shift-m 5 --max-yaw-deg 5`) 넘으면 실패로 보고.
4. `metrics.py`: ICP RMSE(m), inlier 비율, footprint IoU(manifest footprint vs 정합 후 Zone bbox/컨벡스헐), 수직 기울기(지면 법선 vs Z, deg), 스케일 오차(실측 거리 `--scale-check a,b,meters`: notes.md의 줄자 측정 3곳).
5. `cli.py`:
   - `golmok-align run --zone zones/z_.../v1 --basemap D:\golmok_basemap\yeonnam [--poses cameras.csv --gps gps_priors.csv] [--already-georeferenced] --write` → manifest `transform`·`origin` 갱신, `quality` 기록, `align_report.md`(수치·전후 비교 요약).
   - `golmok-align check-blur <screenshots_dir> --face-model ... --lp-model ...` → 렌더 스크린샷에 EgoBlur 검출을 다시 돌려 검출 수 리포트(`privacy/detector.py` 재사용; 모델 없으면 명확한 안내).
   - `golmok-align compare --before manifest_a --after manifest_b` → 변환 차이(이동 m, 회전 deg, 스케일).
6. 테스트: 합성 — 박스 건물 몇 개로 베이스맵 GLB 생성(`basemap/gltf.py` 재사용) → 알려진 변환으로 흔든 포인트 → ICP가 오차 < 5cm·0.2° 로 복원; Umeyama 왕복; 지표 계산; CLI 스모크.
7. 문서: `tools/README.md` 절, `docs/runbooks/align.md`(PC 세션용: 언제 어떤 순서로 돌리고 임계값을 넘으면 무엇을 하는지).

## 완료 기준
- `pytest` 통과, CI 초록, 새 의존성 라이선스 기록(open3d는 WP-03에서 기록됨).
- STATUS `🟢`(클라우드에서 합성 검증 완료) + "실 Zone 검증은 V-05".

## 주의
- LOD1 건물은 실제 벽면과 수십 cm~1m 차이가 난다(높이 추정, footprint 단순화). ICP는 **대략 정합**용이며 최종은 육안 검증(ARCHITECTURE ⑧). 지표 임계값 제안(RMSE < 0.5m, 기울기 < 1°)을 문서에 적되 "조정 예정"으로 표기.
- 성능: 포인트 수를 `--max-points 200000`으로 제한.

## 결과
- 구현: `tools/golmok_tools/align/` — `meshio.py`(GLB/OBJ → ENU 표면 샘플+법선, 축 규약 gltf-yup/enu/ue), `poses.py`(RealityScan CSV `#name,x,y,alt,…` + `gps_priors.csv` 조인), `prior.py`(Umeyama 3D·**level(yaw+scale+이동)** + RANSAC), `icp.py`(point-to-plane ICP, dof 1/4/6, rcond 정규화), `metrics.py`(RMSE·inlier·footprint IoU·기울기·point-to-plane 거리·스케일 확인·임계값 경고), `cli.py`(`run`/`compare`/`check-blur`, manifest 갱신, `align_report.md`).
- 스펙과 다른 점: **open3d를 쓰지 않는다**(리눅스 CI에 libEGL 없음 → import 실패). ICP를 numpy/scipy로 직접 구현. GPS prior는 기본 **level**(3D 자유회전은 평면적인 카메라 궤적에서 GPS 노이즈로 기울어짐 — 합성 테스트에서 7° 기울기 발생, level로 해결). 지면 ICP는 **수직 이동만**(평면 하나에 대한 yaw·xy는 관측 불가 → 발산).
- 테스트 9개(`tests/test_align.py`): ICP 강체 복원(1.5°, 0.8/0.5/0.3 m → 5 cm 이내), Umeyama 왕복+RANSAC 이상치 제거, RealityScan CSV·GPS 조인, 지표, **합성 베이스맵 위 교란 Zone 정합**(yaw 2°, 이동 1.2/−0.8/0.4 m → yaw 오차 0.05°, 이동 오차 < 2 cm, RMSE 3 cm, manifest `validate --check-files` 통과), 보정 한계 초과 시 거부, **GPS prior 경로**(30/−20 m 오프셋 → prior + ICP로 복원), compare, check-blur 모델 부재 안내. 전체 128 passed.
- 남은 것(V-05): 실 collision.glb 축 규약 확인(`--mesh-axes`), 실 RealityScan CSV 첫 줄 확인, 임계값 조정, LOD1 대비 실제 벽 오차 관찰.
