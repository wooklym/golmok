# Golmok Python 도구

| 명령 | 하는 일 |
|---|---|
| `golmok-exif <폴더>` | 촬영 사진 EXIF 점검: 셔터 속도, 사용 렌즈(메인 1x 여부), 해상도(48MP), GPS, 촬영 시간. **리허설과 촬영 직후에 실행** |
| `golmok-frames <영상> <출력폴더>` | 영상에서 선명한 프레임만 추출(창마다 가장 선명한 1장). ffmpeg 필요 |
| `golmok-blur <입력폴더> <출력폴더> --face-model … --lp-model …` | **얼굴·번호판 블러**(Meta EgoBlur, Apache-2.0). 재구성(RealityScan/Postshot)에는 **출력 폴더만** 쓴다 |
| `golmok-perf <csv…> [--label …] [--markdown]` | Unreal CSV 프로파일(`CsvProfile Start/Stop`) 요약: 평균·1% low fps, Game/Render/GPU ms. 스파이크 비교표용 |
| `golmok-zone init/validate/index build/exclude/transform/bump` | **Zone manifest**(스펙 [docs/spec/zone-manifest.md](../docs/spec/zone-manifest.md)): 새 zone 만들기, 검사, Zone Index, 베이스맵 제외 폴리곤, 좌표 변환, 새 버전 |
| `golmok-mesh inspect/reproject/chunk/collision/blockers` | **재구성 메시 후처리**: RealityScan OBJ → zone-local, 청크(UV·UDIM 보존), 충돌 메시, 유리·접근 금지 평면. 절차는 [recon-postprocess 런북](../docs/runbooks/recon-postprocess.md) |
| `golmok-splat inspect/crop/clean/transform/tiles` | **3DGS PLY 후처리**: 자르기, 플로터 제거, 좌표 변환(SH 회전 포함), 로컬 3D Tiles(glTF `KHR_gaussian_splatting`) |
| `golmok-viewer <폴더>` | **검수 뷰어**(CesiumJS, 브라우저): 베이스맵 `tileset.json`과 Zone 타일셋을 로컬에서 띄운다. 레이어 토글, 와이어프레임, 타일 경계, ENU 좌표 읽기, 걷는 높이 시점 |
| `golmok-align run/compare/check-blur …` | **Zone 정합**(WP-07): GPS prior(Umeyama+RANSAC) → 벽면·지면 point-to-plane ICP(numpy/scipy) → manifest `transform`·`quality` 갱신, `align_report.md`. 렌더 스크린샷 블러 재검사. 런북 [docs/runbooks/align.md](../docs/runbooks/align.md) |
| `golmok-basemap inspect/build …` | **배경 베이스맵**: 건물 SHP(GIS건물통합정보) + DEM + 정사영상 → LOD1 건물·지형 GLB 타일 + `manifest.json` + `tileset.json`(3D Tiles 1.1) |

## 설치 (Windows, 한 번만)

```powershell
# Python 3.11 또는 3.12
winget install Python.Python.3.12
# 선택: ffmpeg(프레임 추출), exiftool(블러 결과에 EXIF/GPS 복사)
winget install Gyan.FFmpeg
winget install OliverBetz.ExifTool

cd golmok\tools
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[raw,heic,basemap,zone,mesh,splat,align,dev]"
```

블러까지 쓰려면 PyTorch를 추가로 설치한다. **RTX 50 시리즈(5060 등)는 CUDA 12.8 이상 빌드**가 필요하다.

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

EgoBlur 모델(`ego_blur_face.jit`, `ego_blur_lp.jit`)은 https://www.projectaria.com/tools/egoblur 에서 라이선스에 동의하고 **Gen1** 모델을 받아 `tools\models\`에 둔다(git에는 올라가지 않는다).

## 사용 예

**1) 리허설 점검** (가이드 §4-C)
```powershell
golmok-exif D:\golmok_capture\2026-10-01_rehearsal\photos --csv D:\golmok_capture\2026-10-01_rehearsal\exif.csv
```
출력 예:
```
사진 20장
셔터 1/200 이상: 19/20 (95%) → OK
  느림   1/120  ISO 64  IMG_0012.DNG
렌즈: main-1x 20
ISO: 최소 50 / 중앙 125 / 최대 400
48MP급 해상도: 20/20
GPS 없음: 0장
촬영 시간: 2026-10-01 06:40 ~ 06:52 (12분)
```

**2) 영상 프레임 추출**
```powershell
golmok-frames D:\golmok_capture\…\video\V1.mov D:\golmok_capture\…\frames --fps 2
```

**3) 블러** (재구성 전 필수)
```powershell
golmok-blur D:\golmok_capture\…\photos D:\golmok_capture\…\photos_blurred `
  --face-model tools\models\ego_blur_face.jit --lp-model tools\models\ego_blur_lp.jit
golmok-blur D:\golmok_capture\…\frames D:\golmok_capture\…\frames_blurred `
  --face-model tools\models\ego_blur_face.jit --lp-model tools\models\ego_blur_lp.jit
```
- 결과: `photos_blurred\_golmok\blur_log.csv`(사진별 검출 수), `gps_priors.csv`(RealityScan GPS 가져오기용), `preview\`(검출 표시 미리보기).
- **미리보기를 훑어 누락을 확인**한다. 검출 누락은 0이 될 수 없다(05 문서).
- DNG(ProRAW)는 16-bit TIFF로 현상해 저장한다. **JPEG-XL ProRAW(iPhone 16 Pro/17 Pro의 "JPEG-XL 무손실·손실" 형식)는 rawpy(LibRaw, Adobe DNG SDK 없음)가 현상하지 못한다** → `blur_log.csv`에 `decode_error`(원인 포함)로 남는다. `golmok-exif`의 "ProRAW 압축" 줄로 먼저 확인한다. 촬영은 **JPEG 무손실**로 한다(DECISIONS D-011, 가이드 #1 §4-A).
- `--detect-max-side`(기본 4032): 검출만 축소 이미지로 하고 블러는 원본 해상도에 적용한다. 멀리 있는 작은 얼굴이 걱정되면 `0`(원본)으로 — 느려진다.

**4) 배경 베이스맵** (ROADMAP 1.2, 데이터 받는 법은 [runbooks/pc-setup.md §5](../docs/runbooks/pc-setup.md))
```powershell
# ① 필드 확인: 높이/층수/용도/ID가 어느 컬럼인지 본다 (컬럼명은 파일 버전마다 다를 수 있어 코드에 고정하지 않음)
#    서울 AL_D010_11_20260909 기준: 높이 A16, 지상층수 A26, 용도명 A9, ID A1 (근거 D-012)
golmok-basemap inspect --buildings D:\golmok_data\AL_D010_11_….shp
# ② NGII 정사영상(좌표 정보 없는 TIFF) → GeoTIFF(EPSG:5186). 파일명의 8자리 도엽번호로 배치하고 건물 윤곽으로 보정
golmok-basemap georef-ortho "D:\golmok_data\ortho\raw\(B060)정사영상_2025_*.tif" --out-dir D:\golmok_data\ortho `
  --buildings D:\golmok_data\AL_D010_11_….shp
# ③ 5 m DEM: 1:5,000 수치지형도의 등고선(N3L_F0010000)·표고점(N3P_F0020000) → TIN → GeoTIFF
#    (공개DEM은 90 m뿐, D-012). --half-size는 빌드 반경 + 타일 여유, --fill-dem은 자료 밖 가장자리용
golmok-basemap contour-dem --contours "D:\golmok_data\topo\*\N3L_F0010000.shp" `
  --spots "D:\golmok_data\topo\*\N3P_F0020000.shp" --center 37.5620,126.9250 --half-size 1300 `
  --fill-dem D:\golmok_data\dem\37608.img --out D:\golmok_data\dem\yeonnam_contour_5m.tif
# ④ 빌드 (연남동 예: 중심 반경 1km, 250m 타일)
golmok-basemap build --buildings D:\golmok_data\AL_D010_11_….shp `
  --height-field A16 --floors-field A26 --usage-field A9 --id-field A1 `
  --dem D:\golmok_data\dem\yeonnam_contour_5m.tif --ortho "D:\golmok_data\ortho\ortho_*.tif" `
  --center 37.5620,126.9250 --radius 1000 --out D:\golmok_basemap\yeonnam
```
- 좌표계는 SHP의 `.prj`에서 읽는다. 없으면 `--src-crs EPSG:5174` 등. DEM/정사영상에 좌표계가 없으면 `--raster-crs`(DEM과 정사영상 모두에 적용되므로, NGII 정사영상은 `georef-ortho`로 따로 처리한다).
- `georef-ortho`: 인접 도엽은 겹치는 여유(약 100 m)를 픽셀 단위로 맞춰 이음새가 없다. 결과 줄의 건물 윤곽 매칭 peak가 차순위보다 확실히 커야 보정이 적용된다(아니면 도엽 중심 배치, 약 1~2 m).
- `--exclude zone.geojson`(경위도 폴리곤): 실촬영 플레이 구역 안의 배경 건물을 빼고 만든다.
- `--geoid-offset`: 정표고→타원체고 보정(m). **UE 정적 임포트에는 영향 없음**, Cesium 타일과 맞출 때만 필요(서울 일대 약 +20m대 추정, 적용 전 확인).
- UE로 가져오기(에디터 Python): `import golmok.basemap_import as b; b.run(r"D:\golmok_basemap\yeonnam")`(현재 레벨) 또는 `b.run(r"…\yeonnam", level="/Game/Golmok/Maps/L_Basemap_Yeonnam")`(새 레벨: 조명 + 지면 위 PlayerStart). 다시 실행하면 이전 배경 액터를 지우고 다시 놓는다.
  - 건물은 Nanite + `M_BasemapFacade`(층·창 패턴 절차적 머티리얼), 지형은 `M_BasemapTerrain` 인스턴스(정사영상)이고 Nanite를 끈다(Nanite fallback 충돌이 타일 경계에 틈을 냄, D-012). 축·단위 변환은 타일 경계상자로 자동 측정한다.
  - 생성된 에셋(`Content/Golmok/Basemap/`, `L_Basemap_*`, `M_Basemap*`)은 스크립트로 다시 만들 수 있어 커밋하지 않는다.

**5) Zone manifest** (ROADMAP 1.4, 스펙 [docs/spec/zone-manifest.md](../docs/spec/zone-manifest.md))
```powershell
# ① 새 zone: footprint(경위도 Polygon GeoJSON, QGIS 등으로 그림) + 원점(lat,lon,타원체고)
golmok-zone init --id z_yeonnam_alley_001 --kind exterior --origin 37.5620,126.9250,50 `
  --footprint D:\golmok_zones\fp_alley_001.geojson --capture alley01 --out D:\golmok_zones\zones\z_yeonnam_alley_001\v1
# ② 검사 (--check-files: 청크·충돌·blockers 파일까지)
golmok-zone validate D:\golmok_zones\zones\z_yeonnam_alley_001\v1\manifest.json --check-files
# ③ Zone Index와 베이스맵 제외 폴리곤
golmok-zone index build --zones-root D:\golmok_zones\zones --out D:\golmok_zones\index
golmok-zone exclude --zones-root D:\golmok_zones\zones --out D:\golmok_zones\exclude.geojson --buffer-m 0.75
golmok-basemap build … --exclude D:\golmok_zones\exclude.geojson
# ④ 좌표 확인: zone-local 점 → ECEF·경위도·UE cm (--area-origin = 베이스맵 출력 manifest.json의 origin: lat,lon,height_ellipsoidal)
golmok-zone transform D:\golmok_zones\zones\z_yeonnam_alley_001\v1\manifest.json --enu 10,0,0 --area-origin 37.5620,126.9250,62.4
# ⑤ 게시된 버전은 고치지 않는다: 새 버전 폴더로 복사 후 수정
golmok-zone bump D:\golmok_zones\zones\z_yeonnam_alley_001\v1\manifest.json
```
- 좌표: zone-local은 **ENU(x=동, y=북, z=위), m**. UE는 **X=동, Y=남, Z=위, cm** → `(100x, −100y, 100z)`.
- `transform`은 zone-local → ECEF 4×4 **row-major**. 정합(WP-07)이 이 값을 고친다. 높이는 **타원체고**.
- 합성 예제: `tests/fixtures/zones/z_synthetic_001/v1/manifest.json`(청크 3·충돌 1·blocker 1·포털 1).

**6) 재구성 후처리** (RealityScan·Postshot 결과 → Zone 폴더, 전체 절차는 [런북](../docs/runbooks/recon-postprocess.md))
```powershell
$Z = "D:\golmok_zones\zones\z_yeonnam_alley_001\v1"
golmok-mesh reproject D:\recon\alley01.obj --src-crs EPSG:5186 --manifest $Z\manifest.json --out D:\recon\local\alley01.obj
# 나눠 내보낸 조각은 한 번에 넘긴다(같은 폴더로 합침). 나중에 조각을 더하면 --append, 다시 만들면 --overwrite
golmok-mesh chunk D:\recon\local\alley01_a.obj D:\recon\local\alley01_b.obj --size 15 --out $Z\visual --manifest $Z\manifest.json
golmok-mesh collision D:\recon\local\alley01_a.obj D:\recon\local\alley01_b.obj --out $Z\collision.glb --per-chunk $Z\visual --manifest $Z\manifest.json
golmok-mesh blockers add $Z\blockers.json --center 12,4.8,1.4 --normal 0,-1,0 --size 3,2.4 --kind glass
golmok-mesh blockers build $Z\blockers.json --manifest $Z\manifest.json
golmok-splat clean D:\recon\alley01.ply --min-opacity 0.02 --out $Z\splat.ply
golmok-splat tiles $Z\splat.ply --out $Z\splat_tiles --manifest $Z\manifest.json
```
- 청크는 **OBJ+MTL**(UDIM UV와 원본 8K 텍스처 경로 유지). 충돌·blocker GLB는 glTF Y-up(`golmok-basemap`과 같은 규약).
- 청크 id는 zone 원점 기준 절대 셀: `c_e000_n000` = 동쪽 0~15 m·북쪽 0~15 m, `c_w001_s002` = 서쪽 첫 칸·남쪽 셋째 칸. 조각이 달라도 같은 셀은 같은 id(한 셀에 두 조각이면 `_2`). 청크가 이미 있는 폴더에 `--append`/`--overwrite` 없이 쓰면 거부한다.
- MTL·텍스처가 없으면 `WARN`을 내고 `chunk_manifest.json`의 `missing`에 적는다(청크에 머티리얼이 없는 채로 UE에 들어가지 않게).
- `golmok-splat tiles`의 `COLOR_0`는 기본 `--color0 display`(0.5 + C0·f_dc, Cesium 호환). `linear`는 README 문구대로 sRGB 디코드(Cesium에선 어둡게 보임).
- open3d는 쓰지 않는다(Linux 휠이 libEGL을 요구하고 웹 스택을 끌고 옴). 바닥 평면 RANSAC은 numpy로 구현.

**7) 검수 뷰어** (D-003: 웹 스택은 검수 용도)
```powershell
golmok-viewer D:\golmok_basemap\yeonnam          # 브라우저가 열린다. 인터넷이 없으면 아래 npm install 후 사용
cd tools\viewer; npm install                      # Cesium을 로컬에 두고(오프라인), Playwright 스모크 테스트 준비
npm test                                          # 합성 베이스맵으로 headless 렌더 검사 → test\out\smoke.png
$env:GOLMOK_DATA="D:\golmok_basemap\yeonnam"; npm test   # 실데이터로 검사
```
- 화면에서 `/data/…/tileset.json`(3D Tiles, splat 포함)이나 `/data/…/manifest.json`(Zone)을 입력해 추가할 수 있다. URL로는 `?zone=/data/zones/<id>/v1/manifest.json`.
- Zone 오버레이: footprint(노랑), 원점·라벨, 청크 bbox(하늘), 포털 위치·진입 방향(분홍), blockers 평면(유리 = 민트, no_entry = 빨강). 이름을 클릭하면 그 Zone으로 이동.
- ion 토큰은 쓰지 않는다. 데이터는 로컬 서버(127.0.0.1)에서만 읽는다(D-007).


## 검사 실행

CI(`.github/workflows/ci.yml`)와 같은 검사다. 커밋 전에 `tools` 폴더에서 실행한다(`pip install -e ".[basemap,zone,align,dev]"`에 ruff 포함).

```powershell
ruff check .            # 린트 (자동 수정: ruff check . --fix)
ruff format --check .   # 형식 (적용: ruff format .)
pytest -q               # 단위 테스트
python scripts/check_repo.py   # 저장소 점검: uproject·ini·json 파싱, 문서 상대 링크, .gitattributes LFS
```

- CI는 ubuntu(Python 3.11/3.12)와 windows(3.12)에서 위 검사를 돌리고, 선택 잡으로 합성 베이스맵을 `3d-tiles-validator`로 검증한다(실패해도 전체 실패 아님).
- `GOLMOK_BASEMAP_OUT=<폴더>`를 주고 `pytest tests/test_basemap.py`를 실행하면 합성 베이스맵 출력이 그 폴더에 남는다.
