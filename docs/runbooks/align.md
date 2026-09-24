# 런북: Zone 정합 `golmok-align` (PC 세션용, WP-07)

언제: Zone의 `collision.glb`(WP-03 `golmok-mesh collision`)가 나온 뒤, UE에 배치하기 **전**. 정합은 Zone을 베이스맵의 올바른 위치·방향에 놓고, 그 결과를 manifest의 `transform`·`origin`·`quality`에 기록한다(ARCHITECTURE §5 ⑦⑧).

## 0. 준비물
| 항목 | 출처 |
|---|---|
| Zone 폴더 `zones/<id>/v<n>/` (manifest.json, collision.glb) | `golmok-zone init`, `golmok-mesh collision` |
| 베이스맵 폴더 (manifest.json, tiles/b_*.glb, tiles/t_*.glb) | `golmok-basemap build` (같은 area origin으로 만든 것) |
| (권장) 카메라 포즈 CSV | RealityScan: Alignment → Export → Registration → **Internal/External camera parameters**(CSV). 헤더 `#name,x,y,alt,yaw,pitch,roll,f,px,py,k1,k2,k3,k4,t1,t2` [2차: 커뮤니티 임포터 기준. 실제 파일 첫 줄을 확인] |
| (권장) 사진별 GPS `gps_priors.csv` | `golmok-blur` 출력 `_golmok/gps_priors.csv` |
| 실측 거리 3곳 | 촬영 `notes.md` (가이드 #1 §7) |

## 1. 순서
```powershell
cd tools; .\.venv\Scripts\Activate.ps1
# ① 먼저 --write 없이 돌려 리포트만 본다
golmok-align run --zone D:\golmok_zones\zones\z_yeonnam_alley_001\v1 --basemap D:\golmok_basemap\yeonnam `
  --poses D:\golmok_recon\alley01\cameras.csv --gps D:\golmok_capture\...\photos_blurred\_golmok\gps_priors.csv `
  --gps-alt-offset <지오이드고 m> --ground
# ② 리포트(align_report.md, 콘솔 JSON)를 읽고 경고가 없으면 --write로 manifest 갱신
golmok-align run ... --ground --write
# ③ 검사
golmok-zone validate D:\golmok_zones\zones\z_yeonnam_alley_001\v1\manifest.json --check-files
# ④ (선택) 실측 스케일 확인: 줄자로 잰 두 점의 zone-local 좌표(뷰어/UE에서 읽음)와 실측값
golmok-align run ... --scale-check 12.3,4.5,0.2 14.1,4.5,0.2 1.82
```
- 이미 RealityScan에서 GPS로 지오레퍼런싱했으면 `--already-georeferenced`(스케일 1 고정).
- `--mesh-axes`: collision.glb의 정점 축. 기본 `gltf-yup`(glTF Y-up, golmok-basemap과 같은 규약). WP-03이 다른 규약으로 쓰면 `enu` 또는 `ue`.
- `--dof 4`(기본): 벽면 ICP는 yaw + 이동만. 스캔의 위 방향을 믿을 때. 기울어져 보이면 `--dof 6`.
- `--ground`: 지면 포인트를 지형 타일과 맞춰 **높이만** 보정한다. 베이스맵 origin이 정표고(`--geoid-offset` 없이 만든 경우)면 Zone(타원체고)과 지오이드고만큼 차이가 나므로 이 옵션이 그 차이를 흡수한다.

## 2. 결과 읽기
- `gps_prior`: 사용된 카메라 수/전체, RMSE(폰 GPS는 3~10 m가 정상), scale(1에서 2% 넘게 벗어나면 RealityScan 스케일을 의심).
- `icp_walls`: RMSE(m)와 inlier 비율. LOD1 박스는 실제 벽과 수십 cm~1 m 차이가 나므로 **RMSE 0.3~0.5 m도 정상 범위**다. 벽이 거의 없는 골목(담장·식생)은 inlier가 낮다.
- `correction_area_enu`: 이번에 적용된 보정(이동 m, yaw°). `--max-shift-m 5 --max-yaw-deg 5`를 넘으면 **실패로 멈추고 manifest를 고치지 않는다.** GPS prior 없이 초기 추정이 많이 틀린 경우이므로 prior를 주거나 한계를 의식적으로 올린다.
- `quality`(manifest에 기록): `icp_rmse_m`, `icp_inlier_ratio`, `footprint_iou`, `tilt_deg`, `wall_distance_median_m`, `ground_distance_median_m`, `aligned_at`.
- 제안 임계값(**조정 예정**): RMSE < 0.5 m, 기울기 < 1°, footprint IoU > 0.5, inlier > 0.5. 넘으면 리포트에 경고가 붙는다 → UE에서 육안 확인(ARCHITECTURE ⑧). 최종 판단은 항상 눈으로 한다.

## 3. 실패·이상 시
| 증상 | 원인 후보 | 대응 |
|---|---|---|
| inlier 0, RMSE NaN | Zone이 베이스맵과 수십 m 이상 떨어짐 / 축 규약 다름 | `--poses --gps`로 prior 제공, `--mesh-axes` 확인, 뷰어(`golmok-viewer`)에서 Zone footprint 위치 확인 |
| yaw 보정이 5° 근처 | 초기 방향이 틀림 | prior 사용. 한계를 올리기 전에 뷰어에서 확인 |
| 지면 보정이 수십 m | 베이스맵 origin 높이 기준 불일치(정표고/타원체고) | 정상일 수 있음. `--gps-alt-offset`·`--geoid-offset` 값을 문서(D-012 남은 확인)에 기록 |
| footprint IoU 낮음 | footprint를 대충 그림 | QGIS에서 footprint 다시 그린 뒤 `golmok-zone bump` |

## 4. 블러 재검사 (ROADMAP 1.6)
UE에서 `golmok.viewpoints.capture(...)`로 찍은 스크린샷 폴더에 대해:
```powershell
golmok-align check-blur unreal\Golmok\Saved\Screenshots\Golmok\<tag> --face-model tools\models\ego_blur_face.jit --lp-model tools\models\ego_blur_lp.jit
```
검출이 1건이라도 있으면 해당 원본 사진을 찾아 `golmok-blur`를 다시 돌리고(누락 프레임), 재구성을 다시 한다. 종료 코드 1 = 검출 있음.
