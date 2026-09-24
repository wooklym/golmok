# Golmok Python 도구

| 명령 | 하는 일 |
|---|---|
| `golmok-exif <폴더>` | 촬영 사진 EXIF 점검: 셔터 속도, 사용 렌즈(메인 1x 여부), 해상도(48MP), GPS, 촬영 시간. **리허설과 촬영 직후에 실행** |
| `golmok-frames <영상> <출력폴더>` | 영상에서 선명한 프레임만 추출(창마다 가장 선명한 1장). ffmpeg 필요 |
| `golmok-blur <입력폴더> <출력폴더> --face-model … --lp-model …` | **얼굴·번호판 블러**(Meta EgoBlur, Apache-2.0). 재구성(RealityScan/Postshot)에는 **출력 폴더만** 쓴다 |
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
pip install -e ".[raw,heic,basemap,dev]"
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
- DNG(ProRAW)는 16-bit TIFF로 현상해 저장한다. **아이폰 ProRAW 일부 형식은 rawpy(LibRaw)가 못 열 수 있다** → 그 경우 `blur_log.csv`에 `decode_error`로 남는다. 리허설 사진으로 먼저 확인하고, 실패하면 알려줘(대안: HEIF Max 촬영 또는 다른 현상 경로).
- `--detect-max-side`(기본 4032): 검출만 축소 이미지로 하고 블러는 원본 해상도에 적용한다. 멀리 있는 작은 얼굴이 걱정되면 `0`(원본)으로 — 느려진다.

**4) 배경 베이스맵** (ROADMAP 1.2)
```powershell
# ① 필드 확인: 높이/층수/용도/ID가 어느 컬럼인지 본다 (컬럼명은 파일 버전마다 다를 수 있어 코드에 고정하지 않음)
golmok-basemap inspect --buildings D:\golmok_data\AL_D010_11_….shp
# ② 빌드 (연남동 예: 중심 반경 1km, 250m 타일)
golmok-basemap build --buildings D:\golmok_data\AL_D010_11_….shp `
  --height-field <높이필드> --floors-field <지상층수필드> --usage-field <용도명필드> --id-field <건물ID필드> `
  --dem "D:\golmok_data\dem\*.img" --ortho "D:\golmok_data\ortho\*.tif" `
  --center 37.5620,126.9250 --radius 1000 --out D:\golmok_basemap\yeonnam
```
- 좌표계는 SHP의 `.prj`에서 읽는다. 없으면 `--src-crs EPSG:5174` 등. DEM/정사영상에 좌표계가 없으면 `--raster-crs`.
- `--exclude zone.geojson`(경위도 폴리곤): 실촬영 플레이 구역 안의 배경 건물을 빼고 만든다.
- `--geoid-offset`: 정표고→타원체고 보정(m). **UE 정적 임포트에는 영향 없음**, Cesium 타일과 맞출 때만 필요(서울 일대 약 +20m대 추정, 적용 전 확인).
- UE로 가져오기(에디터 Python): `import golmok.basemap_import as b; b.run(r"D:\golmok_basemap\yeonnam")`
  - 건물은 Nanite + `M_BasemapFacade`(층·창 패턴 절차적 머티리얼), 지형은 정사영상 텍스처. 축·단위 변환은 타일 경계상자로 자동 측정한다.

## 테스트
```powershell
pytest
```
