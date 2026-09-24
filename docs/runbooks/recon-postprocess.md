# 런북: 재구성 결과 후처리 (RealityScan · Postshot → Zone 폴더)

작성: 2026-09-24 (WP-03) · 대상: PC Claude 세션 / 사용자 · 도구: `golmok-zone`, `golmok-mesh`, `golmok-splat`
관련: [spec/zone-manifest.md](../spec/zone-manifest.md) (Zone 계약), [research/07](../research/07-ue5-toolchain.md) §3~§5, [pc-setup.md](pc-setup.md)

이 런북은 **블러 처리된 사진**(`golmok-blur`, D-007)으로 RealityScan·Postshot 재구성을 끝낸 뒤부터 시작한다. 결과물은 `zones/<zone_id>/v<N>/` 폴더 하나이며, `golmok-zone validate --check-files`가 통과해야 끝이다.

## 0. 준비 (한 번)

```powershell
cd golmok\tools
.\.venv\Scripts\Activate.ps1
pip install -e ".[basemap,zone,mesh,splat,dev]"
golmok-mesh --help; golmok-splat --help
```

- 작업 폴더 예: `D:\golmok_zones\` (git 밖). 원본 사진·RealityScan 프로젝트·`.ply`는 **git에 넣지 않는다**.
- 메모리·시간(2026-09-24 클라우드 측정, v/vt/vn가 있는 OBJ 400만 tri, 최대 RSS): 읽기 **0.8 GB·21초**, `chunk` **1.0 GB·58초**, `collision` **1.9 GB·99초**. 삼각형 1개당 읽기 약 0.2 KB, `chunk` 약 0.25 KB, `collision` 약 0.5 KB(+0.3 GB 안팎). 그래서 32GB PC에서 **내보내기 한 조각은 2천만 tri 이하**(충돌 단계 약 10 GB 추정)로 하고, 더 크면 RealityScan에서 구역을 나눠 내보낸다. PC 속도는 다르므로 첫 실데이터에서 다시 재서 아래 결과에 적는다.
  - `chunk`는 조각을 하나씩 읽어 같은 폴더에 합치므로 조각 수에 상관없이 한 조각 크기만큼만 쓴다.
  - `collision`은 조각들을 **합쳐서** 한 번에 처리하므로 전체 tri 수만큼 쓴다(1억 tri ≈ 50 GB). 충돌 메시는 3만 tri면 되므로 전체가 2천만 tri를 넘으면 RealityScan에서 **충돌용으로 단순화한 메시**(예: 500만 tri 이하)를 따로 내보내 `collision`에 넣는다.

## 1. Zone 만들기 (없으면)

```powershell
golmok-zone init --id z_yeonnam_alley_001 --kind exterior --origin 37.5620,126.9250,<타원체고> `
  --footprint D:\golmok_zones\fp_alley_001.geojson --capture alley01 --out D:\golmok_zones\zones\z_yeonnam_alley_001\v1
$Z = "D:\golmok_zones\zones\z_yeonnam_alley_001\v1"
```
원점은 골목 가운데쯤, footprint는 QGIS 등으로 그린 경위도 Polygon이다(스펙 §3).

## 2. RealityScan 내보내기 (메시)

좌표를 **zone-local(동·북·위, m)**로 가져오는 방법은 둘 중 하나다.

| 방법 | RealityScan 설정 | 후처리 |
|---|---|---|
| **A. 투영 좌표로 내보내기 (권장)** | 지오레퍼런싱(GPS/GCP) 후, 출력 좌표계를 **EPSG:5186**(Korea 2000 / Central Belt 2010)로 두고 OBJ 내보내기 [미확인: 메뉴 이름은 2.x 버전마다 다름. 도움말 https://rshelp.capturingreality.com/en-US/tools/export.htm] | `golmok-mesh reproject` (아래) |
| B. 로컬 좌표 그대로 | 원점을 zone 원점에, 축을 동·북·위로 맞춘 로컬 좌표계로 내보내기 | 없음(바로 chunk) |

A가 안전하다. RealityScan이 로컬 원점을 어떻게 잡는지 확인하지 않아도 되고, 변환 결과를 `reproject`가 범위로 보여 준다.

**내보내기 설정** (research/07 §3 판단 그대로)
- 형식 **OBJ** + MTL. 텍스처 **8K UDIM**(파일 이름 `<이름>.1001.png` …), PNG 또는 TIF.
- 메시: Simplify로 **청크당 5~15M tri**가 되게(골목 100m를 15m 청크로 나누면 전체 40~100M tri). 너무 크면 구역을 나눠 여러 번 내보낸다(한 조각 2천만 tri 이하, §0). 조각은 `chunk`/`collision`에 한꺼번에 넘긴다(§3·§4).
- 파일 이름: 조각마다 OBJ·MTL 이름을 다르게 둔다(예: `alley01_a.obj`+`alley01_a.mtl`). 같은 MTL 이름에 내용이 다르면 `chunk`가 거부한다.
- 높이: GPS 고도가 **해발인지 타원체고인지** 확인한다 [미확인: 촬영 기기·설정마다 다름]. 해발이면 `--height-offset <지오이드고>`(서울 +20 m대, [미확인] 정확한 값은 KNGeoid). 오차는 WP-07 정합(ICP)에서 잡는다.

```powershell
# A 방법이면: EPSG:5186 → zone-local (UV·머티리얼 보존, 텍스처 경로 다시 씀)
golmok-mesh reproject D:\recon\alley01\alley01.obj --src-crs EPSG:5186 --manifest $Z\manifest.json `
  --height-offset 0 --out D:\recon\alley01\local\alley01.obj
golmok-mesh inspect D:\recon\alley01\local\alley01.obj
```
`inspect`에서 확인할 것: 범위가 zone 원점 주변 수십~수백 m인지, 바닥 높이 z가 0 근처인지(원점 높이 기준), **위를 향한 면**이 20~50%인지, UDIM 타일 목록이 내보낸 텍스처와 맞는지, 비매니폴드 에지가 많지 않은지.

## 3. 청크 (시각 레이어)

```powershell
# 격자 15 m (기본). 나눠 내보낸 조각은 한꺼번에 넘긴다 → 같은 폴더·같은 manifest로 합쳐진다
golmok-mesh chunk D:\recon\alley01\local\alley01_a.obj D:\recon\alley01\local\alley01_b.obj --size 15 `
  --out $Z\visual --manifest $Z\manifest.json
# 또는 골목 중심선을 따라 15 m 구간 (경위도 LineString GeoJSON)
golmok-mesh chunk D:\recon\alley01\local\alley01_a.obj --along D:\golmok_zones\centerline_alley_001.geojson --size 15 `
  --out $Z\visual --manifest $Z\manifest.json
# 조각을 나중에 더할 때 / 폴더를 처음부터 다시 만들 때
golmok-mesh chunk D:\recon\alley01\local\alley01_c.obj --size 15 --out $Z\visual --manifest $Z\manifest.json --append
golmok-mesh chunk ...같은 입력... --out $Z\visual --manifest $Z\manifest.json --overwrite
```
- 결과: `$Z\visual\c_e000_n000.obj …`(또는 `s_000.obj …`), `alley01_a.mtl`(텍스처 경로를 청크 폴더 기준 상대경로로 다시 씀, 이름의 공백은 `_`), `chunk_manifest.json`(청크별 bbox·tri·UDIM 타일·머티리얼·원본 조각, 원본 텍스처 목록, 없는 MTL·텍스처 `missing`).
- 청크 id는 **zone 원점 기준 절대 셀**이다: `c_e000_n000` = 동 0~15 m·북 0~15 m, `c_w001_s002` = 서쪽 첫 칸·남쪽 셋째 칸. 어느 조각에서 왔든 같은 셀은 같은 id이고, 두 조각이 한 셀에 걸치면 둘째는 `c_…_2`가 된다(겹치지 않고 따로 청크). 중심선 구간은 시작점 앞이 `s_m001`, 끝을 넘어가면 `s_<n>`이 계속 이어진다(끝 청크에 몰리지 않음).
- 청크가 이미 있는 폴더에 `--append`나 `--overwrite` 없이 쓰면 **거부한다**(예전에는 조각 두 번째가 첫 번째를 덮어썼다).
- manifest의 `layers.visual.chunks`가 자동으로 채워진다(`format: nanite_mesh`, uri `visual/<id>.obj`, 폴더 전체 청크).
- `WARN  MTL 없음` / `WARN  텍스처 없음`이 나오면 멈추고 고친다. 그대로 두면 청크가 머티리얼 없이 UE에 들어간다. OBJ·MTL·텍스처 이름에 공백이 있어도 되지만 없는 편이 안전하다.
- 텍스처가 zone 폴더와 **다른 드라이브**(예: `E:\recon`, `D:\golmok_zones`)에 있으면 MTL에 상대경로를 만들 수 없어 **절대경로**(`E:/recon/…`)를 적는다. 그 zone 폴더는 다른 PC로 옮기면 텍스처를 못 찾으므로 같은 드라이브에 두는 편이 낫다.
- **OBJ를 쓰는 이유**: glTF에는 UDIM 개념이 없고(UV가 이미지마다 0~1), 텍스처를 복사·내장해야 한다. OBJ는 RealityScan의 UV·머티리얼을 그대로 두고 MTL이 원본 8K UDIM 텍스처를 가리키므로, UE가 UDIM 가상 텍스처로 가져올 수 있다.
- 텍스처는 복사하지 않는다. UE 임포트(WP-06) 때 MTL이 가리키는 원본을 읽으므로 **원본 텍스처 폴더를 옮기지 않는다.** zone 폴더를 다른 PC로 옮길 땐 텍스처도 같이 옮기고 chunk를 다시 돌린다.
- 청크 하나가 1,500만 tri를 넘으면 경고가 나온다 → `--size`를 줄인다.

## 4. 충돌 메시

```powershell
# 조각이 여럿이면 모두 넘긴다(합쳐서 충돌 메시 하나). 전체가 2천만 tri를 넘으면 충돌용 단순화 메시를 쓴다(§0)
golmok-mesh collision D:\recon\alley01\local\alley01_a.obj D:\recon\alley01\local\alley01_b.obj --out $Z\collision.glb `
  --target-tris 30000 --per-chunk $Z\visual --manifest $Z\manifest.json --report $Z\..\collision_report.json
```
단계: 작은 조각 제거(`--min-component-m2 1`) → (선택) `--fill-holes`(둘레 `--max-hole-m 20` m 이하인 구멍을 가운데 점 부채꼴로 메움. 메시 바깥 테두리는 더 길어서 그대로 둔다) → **바닥 스냅**(10 m 셀마다 위를 향한 평면을 RANSAC으로 찾아 ±5 cm 안의 정점을 평면에 붙임, `--snap-cell/--snap-tol`) → 쿼드릭 데시메이션(`--target-tris` 또는 `--ratio`) → `collision.glb`. `--per-chunk`는 완성된 충돌 메시를 청크 영역별 `collision\<id>.glb`로도 나눈다(청크 이음새가 정확히 맞음).

- 바닥 후보는 0.5 m 기둥마다 가장 낮은 점 근처(벽이 높고 좁은 골목에서도 바닥을 찾음)이고, 셀 안 바닥이 폭 약 0.7 m(표준편차 0.2 m)보다 좁으면 그 셀은 건너뛴다. 2~4 m 골목은 기본 `--snap-cell 10`으로 스냅된다(합성 테스트). `--report`의 `ground_planes`에 셀이 빠져 있으면 그 셀은 스냅되지 않은 것이다.

출력 통계에서 볼 것: 제거된 조각 수(수백 개 이상이면 `--min-component-m2`를 낮춰 계단·난간이 사라지지 않았는지 확인), 셀마다 찾은 경사(`slope_deg`, 골목 경사와 비슷해야 함), 위를 향한 면 비율.

- 골목 계단·턱이 뭉개지면 `--snap-tol 0.02`로 줄이거나 `--no-snap-ground`.
- 3만 tri는 시작값이다. PIE에서 끼임·떨림이 있으면 늘린다(ROADMAP 1.4 완료 기준).

## 5. Blocker (유리·접근 금지)

좌표는 zone-local m다. UE에서 위치를 읽거나 `golmok-zone transform`으로 확인한다.
```powershell
golmok-mesh blockers add $Z\blockers.json --center 12.0,4.8,1.4 --normal 0,-1,0 --size 3.0,2.4 --kind glass
golmok-mesh blockers add $Z\blockers.json --center -3,2,1 --normal 1,0,0 --size 2,2 --kind no_entry
golmok-mesh blockers build $Z\blockers.json --manifest $Z\manifest.json   # → blockers.glb (두께 2 cm)
```
`normal`은 **플레이어가 있는 쪽**(골목 쪽)을 향하게 한다. 높이 축은 위쪽, 폭 축 = 높이 × 법선(스펙 §3.1).

## 6. Splat (Postshot)

Postshot은 RealityScan에서 내보낸 포즈(COLMAP/XMP)로 학습한다(research/07 §3 [확인]). 그래서 splat 좌표는 **RealityScan 포즈 내보내기 좌표계를 따를 가능성이 높다** [미확인]. `inspect`의 범위를 메시와 비교하고, 다르면 `transform --matrix`로 맞춘다(스파이크에서 한 번 확인해 이 런북에 적는다).

```powershell
golmok-splat inspect D:\recon\alley01\postshot\alley01.ply
golmok-splat crop D:\recon\alley01\postshot\alley01.ply --manifest $Z\manifest.json --margin-m 2 --out D:\recon\alley01\splat_crop.ply
golmok-splat clean D:\recon\alley01\splat_crop.ply --knn 16 --std 2.0 --min-opacity 0.02 --max-scale-m 1.0 --out $Z\splat.ply
# 스파이크 (b): 3D Tiles (glTF KHR_gaussian_splatting). --manifest면 root.transform = zone → ECEF
golmok-splat tiles $Z\splat.ply --out $Z\splat_tiles --manifest $Z\manifest.json --max-splats 500000
```
- `transform --matrix`는 **row-major 16개**(zone manifest와 같음). 회전·균일 스케일·이동만(SH 계수까지 회전한다).
- `clean` 결과 JSON에서 floaters 비율이 5%를 넘으면 `--std`를 올려 본다(골목 끝 먼 배경이 잘려 나갈 수 있음).
- 3D Tiles는 로컬에서 만든다. **외부(Cesium ion 등)에 업로드하지 않는다**(D-007).
- 색: `COLOR_0`는 기본 `--color0 display` = `0.5 + C0·f_dc`(디코드 안 함). Cesium for Unreal은 `SH_DEGREE_0_COEF_0`를 읽지 않고 `COLOR_0`를 0차 색으로 쓰며 1~3차 SH를 같은 공간에서 더한다(cesium-unreal `CesiumGaussianSplatCompute.usf`의 `OutColor = InColor + float4(SHColor, 0.0)`, cesium-native `decodeSpz.cpp`도 `0.5 + color * SH_C0`를 그대로 넣음). `--color0 linear`는 Khronos README 폴백 문구대로 sRGB→선형 디코드한 값이라 Cesium에서 **어둡게**(회색 0.5 → 0.214) 보인다. 스파이크에서 색이 어두우면 PLY나 촬영보다 이 옵션을 먼저 확인한다.
- 부모(LOD) 타일의 splat은 크기를 최대 3배 키워 넣고, 타일 bounding box는 그 확대된 3σ 범위와 자식 박스를 모두 감싼다(가장자리 컬링 방지).
- `.ply`는 git에 넣지 않는다. 스파이크 결과가 D-010을 정하면 manifest `layers.visual.format`을 그때 바꾼다.

## 7. 확인과 결과 폴더

```powershell
golmok-zone validate $Z\manifest.json --check-files
golmok-zone index build --zones-root D:\golmok_zones\zones --out D:\golmok_zones\index
golmok-zone exclude --zones-root D:\golmok_zones\zones --out D:\golmok_zones\exclude.geojson
```

```
zones/z_yeonnam_alley_001/v1/
  manifest.json            ← layers.visual.chunks / collision / blockers 채워짐
  visual/c_e000_n000.obj … ← 청크 (OBJ, zone-local m, Z-up, id = zone 원점 기준 절대 셀)
  visual/alley01_a.mtl     ← 원본 UDIM 텍스처를 가리킴(조각마다 하나)
  visual/chunk_manifest.json
  collision.glb            ← glTF(Y-up: 동, 위, −북), golmok-basemap과 같은 규약
  collision/c_e000_n000.glb …
  blockers.json, blockers.glb
  splat.ply, splat_tiles/  ← 스파이크용 (D-010 전)
```
이 폴더를 UE로 가져오는 것은 WP-06(에디터 Python)이 맡는다. 게시된 버전은 고치지 않는다 — 다시 만들 땐 `golmok-zone bump`.

## 결과 (PC 세션이 작성)
- 날짜 / 촬영 ID / 입력 tri 수 / 청크 수 / 충돌 tri / 문제:
