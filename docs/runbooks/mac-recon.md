# 런북: Mac 재구성 파이프라인 (D-023·WP-21, V-05 Mac판의 재구성 부분)

이 문서는 **소유자 Mac에서 도는 Claude Code 세션**이 실촬영 사진을 zone 폴더와 UE 레벨까지 가져가는 절차다. Windows판 [pc-spike.md](pc-spike.md) S1~S9와 [recon-postprocess.md](recon-postprocess.md)의 짝이다. Windows 문서는 이력이자 되돌리기 경로라 그대로 둔다(D-023).

- **전제**: [D-022](../DECISIONS.md)(Mac 단독), [D-023](../DECISIONS.md)(무료 Mac 대체 도구를 스파이크 후보로). 기반 설치는 [mac-setup.md](mac-setup.md) §0.
- **품질 주장 없음**: 아래 도구는 공개 데이터 스모크로 **돈다는 것**만 확인했다. RealityScan·Postshot과 같은 품질인지는 실촬영(C-02) 뒤 V-05와 D-010이 정한다.
- **운영 규칙**: D-019(되돌릴 수 없는 일만 소유자에게), D-002(라이선스), D-007(블러 전 데이터 업로드 금지 — 모든 도구가 로컬에서 돈다), D-020(Opus 5.5).
- **경로**: 도구 `~/golmok-tools`, 데이터 `~/golmok_data/`(촬영 `capture/<ID>`, 재구성 `recon/<ID>`, zone `zones`, 베이스맵 `~/golmok_basemap/<지역>`). 저장소 안에 데이터·PLY·바이너리를 두지 않는다(`.gitignore`가 `.ply`를 막지만 다른 파일은 막지 않는다).
- [미확인] 표시는 이 Mac에서 아직 해 보지 않은 것이다. 전부 §6 표에 모았다.

## 0. Windows 도구 → Mac 대체

| 단계 | Windows 도구(D-005) | Mac 대체(D-023) | 라이선스(출처) | 검증 상태(2026-11-27) | 남은 위험 |
|---|---|---|---|---|---|
| 블러 | `golmok-blur`(EgoBlur Gen1, CUDA) | 같은 도구, `--device cpu`(`auto`도 CPU) | 코드 Apache-2.0 [EgoBlur](https://github.com/facebookresearch/EgoBlur). 모델은 별도 라이선스 동의(소유자) | **미실행** — 모델이 없다 | 처리 속도 [미확인](README가 Mac은 CPU 전용·"very slow"), MPS 결과 [미확인] |
| 프레임·EXIF | ffmpeg·exiftool(winget) | conda-forge ffmpeg 9.1 `lgpl`, exiftool 13.64 | ffmpeg LGPL v3+(`ffmpeg -L`, `--disable-gpl`), exiftool Perl 조건(GPL-1.0+ 또는 Artistic) — 별도 프로그램 | 설치·버전 확인 | `golmok-frames`·`golmok-exif`를 이 바이너리로 돌려 보지 않음 [미확인] |
| SfM·포즈 | RealityScan 정렬 | COLMAP 4.2.1 conda-forge `cpu_lgpl`(CPU, `mapper`·`global_mapper`) | new BSD [LICENSE](https://raw.githubusercontent.com/colmap/colmap/main/LICENSE), 변형 [recipe.yaml](https://github.com/conda-forge/colmap-feedstock/blob/main/recipe/recipe.yaml)·`recipe/build.sh` | 스모크 통과(67장) | 1,300장 매칭·매핑 시간, 미터·ENU 정합 [미확인] |
| 메시·텍스처 | RealityScan(CUDA) | `golmok-objcap`(Apple Object Capture) | Apple SDK(Xcode and Apple SDKs Agreement §2.2). 출력 상업 이용·§2.2 C(2) [미확인 — 소유자 사실 확인] | 스모크 통과(67장·76장) | 물체용 설계, 삼각형 예산 고정, 좌표가 COLMAP과 따로, 블랙박스 |
| 조밀 MVS 메시 | (RealityScan) | **대체 없음** | — | COLMAP `patch_match_stereo`는 CUDA 필요, `delaunay_mesher`는 CGAL 필요(lgpl 빌드에서 끔) — 설치 바이너리에서 확인 | Metashape(유료)·클라우드 GPU(지출). OpenMVS는 AGPL이라 금지 |
| splat 학습 | Postshot Studio(Win + NVIDIA) | Brush v0.3.0(Metal) | Apache-2.0(릴리스 타르볼 LICENSE, [LICENSE](https://raw.githubusercontent.com/ArthurBrussee/brush/main/LICENSE)), v0.3.0 `deny.toml` 허용 목록(GPL 없음, openssl 금지) | 스모크 통과(3k·30k 스텝) | Postshot 대등성(해상도·SH3·AA) [미확인], 1,300장 메모리·시간 [미확인], 공증 안 됨 |
| 후처리 | `golmok-mesh`·`golmok-splat`·`golmok-align`·`golmok-zone` | 같은 도구(순수 Python) | D-002 기록 그대로(MIT/BSD) | `golmok-splat inspect/clean/tiles` 통과 | `crop`·`transform`·`golmok-mesh`·`golmok-align`은 Mac 실데이터 미실행 |
| splat 렌더(UE) | XGRIDS LCC4Unreal(스파이크 c) · Cesium(스파이크 b) | Cesium for Unreal 2.31.0(Metal) | Apache-2.0(배포본 LICENSE), `ThirdParty.json`: cesium-native Apache-2.0·MikkTSpace Zlib·HTML Tidy·Font Awesome CC BY 4.0 [releases](https://github.com/CesiumGS/cesium-unreal/releases) | `-game` Metal 렌더 통과(저장소 밖 프로젝트 사본) | Mac 패키지 빌드 렌더·성능·그림자 [미확인]. LCC는 Mac 미지원 → (c) "해당 없음" |
| 메시 임포트(UE) | `zone_import`(에디터 Python) | 같은 스크립트 | — | Mac 미실행 | [미확인](V-19 뒤) |

## 1. 설치 (한 번, sudo·Homebrew·계정 없음)

```bash
cd ~/projects/golmok

# COLMAP(cpu_lgpl)·ffmpeg(lgpl)·exiftool(micromamba env "recon") + Brush v0.3.0. 다시 돌려도 된다(sha256 재확인)
tools/mac/install-recon-tools.sh            # 접두 경로 기본 ~/golmok-tools. 저장소 안 경로·root는 거부
. ~/golmok-tools/env.sh                     # PATH 맨 앞에 ~/golmok-tools/bin과 env bin(exiftool이 env의 perl을 쓴다)
colmap version                              # "COLMAP 4.2.1 (… without GPU support …)"
brush_app --version                         # brush 0.3.0
ffmpeg -hide_banner -L | head -2            # LGPL v3 or later

# Object Capture CLI (Xcode 27.2 툴체인, 빌드 산출물은 저장소 밖)
cd tools/mac/objcap && swift build -c release --scratch-path ~/golmok-tools/objcap/build && cd -
OBJCAP=~/golmok-tools/objcap/build/release/golmok-objcap
"$OBJCAP" limits                            # isSupported true, 2000장, 16384 px (종료 코드 0)

# 저장소 후처리 도구 (mac-setup §0의 venv). 블러까지 쓰면 blur extra(PyPI 기본 torch, CUDA 인덱스 안 씀)
cd tools && source .venv/bin/activate && uv pip install -e ".[splat,mesh,align,zone]" && cd -
# uv pip install -e ".[blur]"               # 블러가 필요할 때 [미확인: 이 Mac에서 아직 설치하지 않음]
```
- 재현: `~/golmok-tools/envs/recon-explicit.txt`(`micromamba env export --explicit --md5`, 188개)로 같은 env를 만든다.
- 설치 스크립트는 env 안에 GPL 전용 conda 패키지가 있으면 실패한다. 이중 라이선스(FreeImage GPL OR FIPL, freetype GPL OR FTL, gmp GPL OR LGPL-3)는 허용, libgfortran은 GCC 런타임 예외, libheif는 x265를 뺀 lgpl 변형으로 고정했다.
- quarantine 제거·Gatekeeper 설정 변경은 하지 않는다. curl로 받은 Brush에는 `com.apple.quarantine`이 없어 그대로 돈다(`spctl`은 "rejected", 공증 안 됨). 브라우저로 받으면 Gatekeeper 창이 뜬다.
- **Cesium for Unreal 2.31.0**: GitHub 릴리스 `CesiumForUnreal-58-v2.31.0.zip`(sha256 `6bab4f6e…cfe91`)이 `~/golmok-tools/ue-plugins/cesium-2.31.0/`에 있다. 저장소 `Golmok.uproject`에는 아직 켜지 않았다(WP-21 후속, `[WP-21 hook]`). §2 M7 참고.
- 빠른 확인: `tools/mac/recon-smoke.sh <이미지 폴더> [작업 폴더]` — M3·M5·M6을 한 번에 돌리고 `<작업>/summary.txt`를 남긴다(§3).

## 2. 단계별 절차

`ID`는 촬영 ID(예: `C02_yeonnam_20261205`), `Z`는 zone 버전 폴더다.
```bash
ID=<촬영 ID>; CAP=~/golmok_data/capture/$ID; R=~/golmok_data/recon/$ID
Z=~/golmok_data/zones/zones/z_yeonnam_alley_001/v1
mkdir -p "$R"
```

### M1. 촬영
- [capture/01-alley-capture-guide.md](../capture/01-alley-capture-guide.md) 그대로(D-011, iPhone 17 Pro 48MP ProRAW JPEG). 사진을 `$CAP/photos`에 둔다. 영상 프레임은 `golmok-frames "$CAP/video/V1.mov" "$CAP/frames" --fps 2`(Mac ffmpeg로 [미확인]).

### M2. 블러 (D-007, 필수 — 블러 없이 다음 단계 금지)
```bash
golmok-blur "$CAP/photos" "$CAP/photos_blurred" \
  --face-model tools/models/ego_blur_face.jit --lp-model tools/models/ego_blur_lp.jit --device cpu
```
- 모델 두 개는 **소유자가 라이선스에 동의하고 받는다**(mac-setup §1 #7). 없으면 여기서 멈춘다.
- `--device mps`는 수동 지정만 된다. EgoBlur TorchScript·`torchvision.ops.nms`가 MPS에서 같은 결과를 내는지 [미확인]이라 정본은 CPU다.
- 먼저 리허설 사진 20장으로 처리 속도를 재고 1,300장 시간을 추정한다(§6 #1).
- 블러 결과에 EXIF·GPS가 복사되는지 본다(exiftool, [tools/README](../../tools/README.md)). M3의 `spatial_matcher`와 정합이 GPS를 쓴다.

### M3. SfM (COLMAP, CPU)
```bash
. ~/golmok-tools/env.sh
cd "$R"                                     # 모든 도구는 작업 폴더에서 돌린다
colmap feature_extractor --database_path "$R/database.db" --image_path "$CAP/photos_blurred" \
  --ImageReader.camera_model OPENCV --ImageReader.single_camera 1 \
  --FeatureExtraction.use_gpu 0 --FeatureExtraction.max_image_size 3200
# 매칭: 1,300장 exhaustive는 약 84만 쌍(100쌍/s면 2.3 h 이상, 추정) → 걸은 순서면 sequential, GPS가 있으면 spatial
colmap sequential_matcher --database_path "$R/database.db" --FeatureMatching.use_gpu 0
# colmap spatial_matcher --database_path "$R/database.db" --FeatureMatching.use_gpu 0   # [미확인: 이 규모에서 미실행]
mkdir -p "$R/sparse"
colmap mapper --database_path "$R/database.db" --image_path "$CAP/photos_blurred" --output_path "$R/sparse"
# 비교용(더 빠를 수 있음 [미확인]): colmap global_mapper … --output_path "$R/sparse_global" --GlobalMapper.gp_use_gpu 0
colmap model_analyzer --path "$R/sparse/0"  # 등록 장수·점 수·재투영 오차
```
- `sparse/1` 이상이 생기면 모델이 끊긴 것이다. 매칭을 바꿔 다시 돌린다. **한 모델만 정본으로 쓴다**(증분과 global 모델은 좌표계가 다르다).
- 메모리: 67장에서 18스레드 피크 21.4 GB였다. 48 MP에서는 20~25 GB로 추정한다. 모자라면 `--FeatureExtraction.num_threads`를 줄인다 [미확인: 옵션 이름은 `colmap feature_extractor -h`로 확인].
- `vocab_tree_matcher`는 어휘 트리 파일 다운로드와 그 라이선스가 [미확인]이라 쓰지 않는다. ALIKED 등 ONNX 특징 모델도 가중치 라이선스 [미확인]이라 SIFT만 쓴다.

**정합(미터·ENU) — 메시·splat보다 먼저, 희소 모델에서 한 번**
- COLMAP 좌표의 스케일·방향은 임의다. GPS(EXIF)나 GCP로 `colmap model_aligner`를 돌려 희소 모델을 미터·ENU로 옮긴다. 옵션은 `colmap model_aligner -h`로 확인한다 [미확인: 끝까지 해 보지 않음]. 목표는 zone 원점을 원점으로 하는 동·북·위 m(recon-postprocess §2 "B. 로컬 좌표 그대로")다.
- 보조 확인은 `golmok-align run --zone "$Z" --basemap ~/golmok_basemap/yeonnam --gps "$CAP/photos_blurred/_golmok/gps_priors.csv" --ground`(리포트만, [align.md](align.md))다.

**왜곡 제거 (Brush 입력)**
```bash
colmap image_undistorter --image_path "$CAP/photos_blurred" --input_path "$R/sparse/0" \
  --output_path "$R/undistorted" --output_type COLMAP
colmap model_converter --input_path "$R/undistorted/sparse" --output_path "$R/undistorted/sparse" --output_type TXT
```
- Brush는 초점거리·주점만 읽고 렌즈 왜곡을 무시한다(v0.3.0 `crates/brush-dataset/src/formats/colmap.rs`). 그래서 PINHOLE로 펴서 넣는다.

### M4. 메시 (golmok-objcap = Apple Object Capture, 후보)
```bash
"$OBJCAP" run "$CAP/photos_blurred" "$R/objcap" --detail full --format obj --poses --point-cloud \
  --checkpoint "$R/objcap_ckpt"
python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(d["ok"],d["invalid_samples"],d["skipped_samples"],d["automatic_downsampling"],d["stitching_incomplete"])' "$R/objcap/summary.json"
# 기대: True [] [] False False (ok가 true, invalid_samples·skipped_samples가 빈 목록, automatic_downsampling·stitching_incomplete가 false)
```
- 옵션 표와 종료 코드(0 성공·1 실패·2 사용법·3 미지원)는 [tools/mac/objcap/README.md](../../tools/mac/objcap/README.md)다. `--detail`은 `preview|reduced|medium|full|raw`, `--ordering sequential`은 걸은 순서 촬영용이다.
- **좌표**: 메시·포즈·점군은 같은 실행끼리만 같은 좌표계다. COLMAP 모델과 다르다. Y-up, `metersPerUnit = 1`이지만 미터인지는 GPS가 있을 때만 맞았다(Tyrol). zone-local로 옮기는 도구는 아직 없다 — `golmok-mesh reproject`는 EPSG 좌표 입력만 받는다 [미확인: 유사변환 단계 필요, §6 #6].
- 실험 경로: `"$OBJCAP" colmap "$R/objcap/poses.json" "$R/objcap_colmap" "$R/objcap/pointcloud.ply"`로 Object Capture 포즈를 COLMAP 텍스트 모델로 바꾸면 splat을 메시와 같은 좌표계로 학습할 수 있다. 렌즈 왜곡 미적용, track 없는 점을 Brush가 받는지, 정렬 결과, 약관 §2.2 C(2) 해당 여부가 모두 [미확인]이다.
- 삼각형 예산이 detail별로 고정이다(측정: medium 50k~100k, full 250k). 골목 전체를 한 번에 돌리면 거칠다. 구역(bbox)별 실행(옵션 없음)·`raw`·"메시는 충돌용, 외관은 splat" 중에서 V-05가 고른다.
- 이 단계 결과는 **약관 사실 확인(§4) 전에는 제품(커밋·배포)에 넣지 않는다**. 스파이크 측정은 로컬에서 한다.
- 다른 메시 경로(Metashape, 클라우드 GPU의 RealityScan)는 지출이라 소유자 항목이다(§4).

### M5. splat 학습 (Brush, Metal)
```bash
mkdir -p "$R/brush" && cd "$R/brush"        # Brush가 현재 폴더에 ./target/autotune을 쓴다 — 저장소에서 돌리지 않는다
RUST_LOG=info brush_app "$R/undistorted" --total-steps 30000 --sh-degree 3 \
  --export-every 5000 --export-path "$R/brush" --export-name "export_{iter}.ply"
```
- 구역 splat은 **모든 이미지로** 학습한다. `--eval-split-every N`은 N장마다 한 장을 학습에서 뺀다(스모크: 67장 → 학습 58·평가 9). 실촬영에서는 범위·품질이 줄고 V-05의 Postshot 비교(전 이미지 학습)가 어긋나므로 위 명령에 넣지 않는다(D-006 "학습 해상도와 반복 수를 줄이지 않는다", 품질 우선).
- PSNR 추적이 필요하면 `--export-path "$R/brush_eval"`로 따로 한 번 더 돌리고 `--eval-split-every 8 --eval-every 5000`을 붙인다. 그 PLY는 구역 splat이 아니다(M6에 넣지 않는다).
- `--with-viewer`를 빼면 창 없이 돈다. 로그의 `Using adapter … backend: Metal`을 확인한다.
- 기본 `--max-resolution 1920`이 48 MP를 줄인다. 전체 해상도는 시도하지 않았다 [미확인]. `--max-splats`(기본 1천만)로 상한을 둔다. 전체 플래그는 `brush_app --help`.
- 마스크: Brush는 이미지별 마스크를 읽는다(`find_mask_path`). 폴더 규칙 [미확인].
- splat은 M3 COLMAP world 좌표 그대로다(재중심·재스케일 없음; 스모크에서 splat→SfM 점 거리 중앙값 0.0049 단위). M3에서 정합한 모델이면 zone-local로 나온다.

### M6. 후처리 (저장소 도구, recon-postprocess §1~§7)
```bash
cd ~/projects/golmok/tools && source .venv/bin/activate
golmok-zone init --id z_yeonnam_alley_001 --kind exterior --origin <lat>,<lon>,<타원체고> \
  --footprint ~/golmok_data/zones/fp.geojson --capture "$ID" --out "$Z"      # zone이 없을 때
golmok-splat inspect --json "$R/brush/export_30000.ply"                     # 범위가 zone 원점 주변 m인지
# golmok-splat transform "$R/brush/export_30000.ply" --matrix <row-major 16개> --out "$R/splat_zone.ply"   # 좌표가 다르면
golmok-splat crop "$R/brush/export_30000.ply" --manifest "$Z/manifest.json" --margin-m 2 --out "$R/splat_crop.ply"
golmok-splat clean "$R/splat_crop.ply" --knn 16 --std 2.0 --min-opacity 0.02 --max-scale-m 1.0 --out "$Z/splat.ply"
golmok-splat tiles "$Z/splat.ply" --out "$Z/splat_tiles" --manifest "$Z/manifest.json" --max-splats 500000
# 메시(zone-local OBJ가 있을 때): golmok-mesh inspect → chunk → collision → blockers (recon-postprocess §3~§5)
golmok-mesh chunk "$R/local/alley.obj" --size 15 --out "$Z/visual" --manifest "$Z/manifest.json"
golmok-mesh collision "$R/local/alley.obj" --out "$Z/collision.glb" --target-tris 30000 --per-chunk "$Z/visual" --manifest "$Z/manifest.json"
golmok-zone validate "$Z/manifest.json" --check-files --strict
```
- Brush PLY는 `f_rest_*`를 이름의 사전순으로 쓴다. `golmok-splat`은 이름으로 읽어 맞다. 다른 리더(열 순서로 읽는 것)는 SH를 틀리게 읽을 수 있다 [미확인].
- `crop`·`transform`·`golmok-mesh`·`golmok-align`은 Mac 실데이터로 아직 돌리지 않았다. 스모크에서는 `inspect`·`clean`·`tiles`만 돌렸다.
- 3D Tiles는 로컬에서만 만든다(D-007, Cesium ion 업로드 금지).

### M7. UE 임포트
- **(a) 메시**: Windows와 같은 `zone_import`(pc-spike S7). 경로만 바꾼다. Mac 실행은 V-19 통과 뒤 [미확인].
  ```python
  import golmok.zone_import as zi
  r = zi.run("/Users/<사용자>/golmok_data/zones/zones/z_yeonnam_alley_001", level="/Game/Golmok/Maps/L_Basemap_Yeonnam", geo_origin="/Users/<사용자>/golmok_basemap/yeonnam")
  ```
- **(b) Cesium splat**: `Cesium3DTileset` → Source **From Url** → `file:///Users/<사용자>/golmok_data/zones/zones/z_yeonnam_alley_001/v1/splat_tiles/tileset.json`, 라벨 `Spike_b_tiles`(pc-spike S8과 같다). 화면 확인은 `-game -RenderOffscreen` + 고정 `CameraActor`(첫 스모크는 카메라 피치 −90°라 검게 나왔다).
  - 저장소 프로젝트에서 쓰려면 WP-21 후속(`[WP-21 hook]`: `.uproject` 활성화·플러그인 배치)이 먼저다. 플러그인을 프로젝트 `Plugins/`에 넣으면 UBT가 소스에서 다시 빌드하고 Xcode 27 clang 21에서 `CesiumEditor/Private/IonQuickAddPanel.cpp:194`(`-Werror,-Wuninitialized`)로 멈춘다. 스모크는 저장소 밖 사본에 `#pragma clang diagnostic ignored "-Wuninitialized"` 한 줄을 넣어 통과했다. 프리빌트 dylib를 Engine `Plugins/Marketplace`에 두면 재빌드를 피할 것으로 보이나 시험하지 않았다 [미확인].
  - Cesium splat은 별도 렌더 경로라 UE 조명과 통합되지 않는다. 공식 가이드는 단일 방향광을 권한다([3D Gaussian splat tilesets](https://cesium.com/learn/unreal/3d-gaussian-splat-tilesets-lods/)). 캐릭터 그림자를 받지 않는다는 D-003 사전 조사는 그대로다.
- **(c) XGRIDS LCC**: Mac 미지원(README가 Windows·Linux, DX11/DX12/Vulkan만) — 스파이크 표에 "해당 없음(LCC Mac 미지원)"으로 적는다.
- 이후 시점·캡처·성능(pc-spike S10~S15)은 Mac 대응표([mac-setup.md](mac-setup.md) §3)대로 한다. 성능은 같은 세션 Mac 기준선끼리만 비교한다(D-022 ⑤).

## 3. 스모크 결과 (2026-11-27, 공개 데이터, 품질 판정 아님)

측정 중 UE 패키징 작업이 함께 돌았다(load average 24~55). 시간은 상한 쪽으로 읽는다. 결과 파일은 전부 저장소 밖이다.

**COLMAP → Brush → golmok-splat**(AliceVision Buddha 67장 PNG 2736×1540, 282 MB, EXIF 없음, CC-BY-4.0 [dataset_buddha](https://github.com/alicevision/dataset_buddha), DOI 10.5281/zenodo.1203283; `~/golmok_data/recon-smoke/sfm-splat/run2/summary.txt`)

| 단계 | 시간 | 결과 |
|---|---|---|
| feature_extractor (SIFT, CPU 18스레드) | 17 s | 피크 21.4 GB, 장당 키포인트 평균 8,767 |
| exhaustive_matcher (CPU) | 22 s | 2,211쌍, 검증 824 |
| mapper | 23 s | 67/67, 점 35,901, 재투영 0.320 px |
| global_mapper (GLOMAP) | 14 s | 67/67, 점 35,763, 0.321 px |
| image_undistorter | 6 s | PINHOLE 2731×1534 |
| Brush 3k스텝, max-res 1600 | 69 s | Metal, PSNR 19.74 / SSIM 0.867, 49,214 splat, PLY 11 MB |
| Brush 30k스텝(기본값) | 926 s | PSNR 21.25 / 21.16 / 20.77(10k/20k/30k), SSIM 0.894, 128,783 splat, PLY 30 MB |
| golmok-splat inspect / clean / tiles | ≤ 1 s | 타일 1개(`r.glb` 12 MB) |

**golmok-objcap**(Buddha, Tyrol 교회 드론 76장 5472×3648 CC BY 4.0 [Tyrol-Church](https://github.com/IRCSS/Tyrol-Church-Photogrammetry-Dataset))

| 데이터 | detail | 시간 | 피크 메모리 | 정점 / 삼각형 | 텍스처 |
|---|---|---|---|---|---|
| Buddha | medium | 103 s | 4.9 GB | 25,003 / 50,000 | 3 × 4096² |
| Tyrol | medium | 671 s | 32.9 GB | 50,673 / 100,000 | 3 × 4096² |
| Tyrol | full | 645 s | 33.0 GB | 125,678 / 250,000 | 5 × 8192² |

**Cesium for Unreal 2.31.0 on Metal**(저장소 밖 프로젝트 사본): 합성 splat 5만 개가 `root.transform` → ECEF(37.562, 126.9272636, 50 m) 위치에 렌더. Brush 30k PLY → `golmok-splat tiles --manifest tests/fixtures/zones/z_synthetic_002/v1/manifest.json` → Cesium 렌더에서 불상 머리·받침판·ArUco 마커를 알아볼 수 있고 색이 정상. 정리·정렬을 하지 않아 기울어져 있고 floater가 보인다. 스크린샷 `~/golmok_data/recon-smoke/splat-render/Golmok/Saved/Screenshots/Golmok/{ctl,buddha}/current/`.

자세한 수치는 [WP-21](../plan/WP-21-mac-recon-pipeline.md) "결과".

## 4. 대체하지 않은 것 (소유자 항목 또는 막힘)

| 항목 | 이유 | 분류 |
|---|---|---|
| 제품 재구성 스택 확정(D-005/D-006) | 이 런북의 도구는 V-05 스파이크 후보다. V-05 결과로 무료 Mac 경로 또는 지출 대안을 제품 스택으로 정하는 것은 되돌리기 비싼 스택 변경 | **스택 변경**(D-019 ⑤, 소유자) |
| 조밀 MVS·Delaunay 메시(COLMAP) | `patch_match_stereo`는 CUDA 필요, `delaunay_mesher`는 CGAL 필요(lgpl 빌드에서 끔). OpenMVS는 AGPL(D-002 금지) | 막힘 — Mac 지원 없음 |
| Agisoft Metashape(Mac 지원, Standard $179 / Pro $3,499) | 구매 | **지출**(D-019 ①) |
| 클라우드 Windows GPU(AWS g6e 등)의 RealityScan·Postshot | 시간당 비용·계정 | **지출**(D-019 ①). 올리는 것은 블러 뒤 이미지만(D-007) |
| NVIDIA Windows 머신 | 구매·대여 | **지출** |
| EgoBlur 모델 | 모델 라이선스 동의 | **약관**(D-019 ②, mac-setup §1 #7) |
| Fab의 GASP·Cesium Fab판 | Fab 계정·EULA. Cesium은 GitHub 릴리스로 대체해 Fab이 필요 없다 | **약관**(GASP만) |
| XGRIDS LCC4Unreal (스파이크 c) | macOS·Metal 미지원 | 막힘 — 해당 없음. Windows 측정은 지출·머신이 생길 때 |
| Apple Object Capture 출력의 제품 사용 | Xcode and Apple SDKs Agreement §2.2 C(2)("output generated from an Apple model to train … another artificial intelligence model")가 splat 학습에 걸리는지, 상업 사용을 명시한 공식 문서 없음 | **사실 확인**(소유자, 법률 판단 아님) |
| msplat(Apache-2.0) | [v1.1.4](https://github.com/rayanht/msplat/releases)(2026-08) macOS arm64 휠 있음, Inria 파생 여부 소스 감사 전 [미확인] | 미조사 — 채택 안 함 |
| UnrealSplat·Luma·XV3DGS 등 UE splat 플러그인 | Mac 바이너리 없음·약관 [미확인]·Luma는 클라우드 캡처 전제(D-007 충돌) | 미채택 |
| Postshot과의 품질 대등성 | 실촬영 없음 | V-05 |
| `vocab_tree_matcher` 어휘 트리, ALIKED 특징 모델 | 파일 다운로드와 라이선스 [미확인] | 미채택(SIFT만) |

**쓰지 않는 것(D-002)**: Inria 3DGS 계열, MASt3R/DUSt3R, OpenMVS·OpenSplat·gsplat-mps(AGPL), Ultralytics.

## 5. 골목 규모(약 1,300장 × 48 MP) 예상 — 추정, 측정 아님

| 단계 | 추정 | 근거·대응 |
|---|---|---|
| SIFT 추출 | 10~20분, 피크 20~25 GB | SIFT 3200 px 상한이라 장당 픽셀은 스모크의 약 2배 + 48 MP JPEG 디코드 |
| 매칭 | exhaustive 2.3 h 이상(약 84만 쌍), spatial 약 6.5만 쌍·10~20분 | sequential(걸은 순서)·spatial(EXIF GPS) |
| 매핑 | 증분은 수 시간 [미확인], global이 빠를 수 있음 [미확인] | 둘 다 돌려 한 모델을 정본으로 |
| Object Capture | medium 7~8시간(선형 가정), 하루 이상 가능 [미확인]. 128 GB에 다운샘플 없이 들어가는지 [미확인] | 한도(2000장·16384 px) 안. bbox 분할 |
| Brush | 데이터셋을 메모리에 올림(1300 × 1920×1440 × 3 B ≈ 11 GB 이상, GPU f32 여부 [미확인]). splat 1~10M, 수 시간 [미확인] | `--max-splats`·`--max-resolution` |

## 6. 미확인 표

| # | 항목 | 지금 아는 것 | 확인 방법 | 확인 결과 |
|---|---|---|---|---|
| 1 | EgoBlur CPU 처리 속도·MPS 결과 | 모델 없음 | 소유자 모델 동의 뒤 리허설 20장 `--device cpu`/`mps` 비교 | |
| 2 | `golmok-frames`·`golmok-exif`를 conda-forge ffmpeg·exiftool로 | 버전만 확인 | C-01 리허설 영상 1개 | |
| 3 | 1,300장 매칭·매핑 시간과 메모리 | §5 추정 | C-02 첫 실행 `/usr/bin/time -l` | |
| 4 | `spatial_matcher`가 블러 결과의 EXIF GPS를 읽는지 | 블러가 EXIF를 복사(exiftool) | 리허설 사진으로 실행 | |
| 5 | `colmap model_aligner` 미터·ENU 정합(옵션·결과) | 끝까지 해 보지 않음 | GPS 있는 리허설 → zone-local 범위 확인 | |
| 6 | objcap 메시 → zone-local 변환 | 저장소 도구 없음(`reproject`는 EPSG만) | 유사변환 단계 설계(WP-21 후속) | |
| 7 | `golmok-objcap colmap` 경로(track 없는 점·왜곡·정렬) | Buddha 포즈 일치·투영 96.9 % | Brush 학습 → 메시와 겹침 확인 | |
| 8 | Object Capture 골목 촬영(안에서 바깥) 동작 | 물체 데이터만 | C-02 | |
| 9 | Object Capture 출력 약관(§2.2 C(2)·상업 사용) | 공식 문서 못 찾음 | 소유자 사실 확인 | |
| 10 | Brush 전체 해상도·Postshot 대등성 | 기본 1920 | V-05 | |
| 11 | Brush 마스크 폴더 규칙 | `find_mask_path` 있음 | 소스·시험 | |
| 12 | Brush 1,300장 메모리(GPU f32 여부) | 추정 11 GB+ | C-02 | |
| 13 | Brush PLY `f_rest_*` 순서를 Cesium·다른 임포터가 이름으로 읽는지 | `golmok-splat`은 이름으로 읽음, Cesium 렌더 색 정상(SH 고차 검증 아님) | SH 검증 장면 | |
| 14 | Mac 패키지(쿡) 빌드에서 Cesium splat 렌더 | `-game` 에디터 빌드만 확인. 2.28.0 수정은 Windows 보고 | `package.sh` 뒤 실행 | |
| 15 | CesiumRuntime 게임 타깃 clang 21 빌드 | 에디터 타깃만 | 패키지 빌드 | |
| 16 | Cesium 로드 오류 줄(`FCesiumMetadataPropertyStatisticValue::Semantic`)이 `test.sh`를 실패로 만드는지 | 매번 찍힘 | 활성화 뒤 `test.sh` | |
| 17 | 수백만 splat·여러 타일·LOD 성능(`stat unit`) | 12~32 MB 타일만 | V-05 | |
| 18 | 그림자·Lumen 통합, 메시와 섞은 정렬·깊이 | 공식 가이드: UE 기능과 통합 안 됨 | V-05 S13 | |
| 19 | Engine `Plugins/Marketplace` 프리빌트 설치로 재빌드 회피, Fab판 Mac 바이너리 | 시험 안 함 | 설치 1회 | |
| 20 | Cesium 정적 링크 서드파티(abseil·draco·spz·libwebp·s2·blend2d·asmjit·libjpeg-turbo·ktx·zstd·sqlite·tidy 등) 개별 LICENSE 원문 | permissive로 기억, 파일 단위 미검증 | 배포 전 NOTICE 작성 때 | |
| 21 | Brush 러스트 크레이트 전체 감사 | `deny.toml` 허용 목록만 확인 | `cargo deny` 또는 수동 | |
| 22 | COLMAP `colmap gui`(Qt6) macOS 27에서 열림 | 명령은 있음 | 실행 1회(선택) | |
| 23 | `zone_import` Mac 실행 | V-19 전 | V-19 뒤 | 2026-11-28 J-18 헤드리스 성공(`-nullrhi`+`-ExecCmds`, 합성 스캔 존): `2/2 chunks (2 set, 0 already on)`·`0 warnings`·시간(참고값 — 로컬 LLM 추론 부하가 있는 상태): `zi.run` 3.93 s — v17 §7 §3 행. 근거: PR #156. |
| 24 | Brush 다음 릴리스의 CLI 플래그 변화 | v0.3.0(2025-09) 고정 | 업그레이드 때 `--help` | |
| 25 | 크래시 리포트 무인 업로드(CrashReportClient → Epic, D-007) | 엔진 기본값 `bSendUnattendedBugReports=True`(BaseEditorSettings.ini). 이 Mac에서 2026-11-27·28 무인 실행 크래시 6건의 리포트가 올라갔다(DECISIONS D-023 D-007 메모) | 프로젝트 `Config/DefaultEditorSettings.ini` `[WP-21 hook]`의 `False`. 크래시 없이 창 없는 편집기를 한 번 띄우고 끈 뒤 `~/Library/Application Support/Epic/NotAllowedUnattendedBugReports`의 수정 시각을 본다 | 2026-11-28 J-29(SHA bd7fa35 작업 트리, `UnrealEditor-Cmd -nullrhi -unattended`, `QUIT_EDITOR` 1회씩): 훅 파일이 없는 트리의 실행 뒤에는 그 파일이 바뀌지 않았고, 훅 파일이 있는 트리의 실행 뒤에는 새로 써졌다 — 이번 실행에서 편집기가 그 값을 `False`로 읽었다. 크래시는 일으키지 않았다. 무인 실행의 크래시에서 CrashReportClient가 뜨지 않는 것은 엔진 소스(`MacPlatformMisc.cpp`) 읽기이고 실행으로 확인하지 않았다. 같은 블록의 `bSendUsageData=False`, 사람이 보는 편집기 크래시(대화창에서 보낼지 고른다), 패키지 게임, Windows는 [미확인]. 근거: PR #166. |

## 7. 결과 (V-05 Mac 세션이 작성)

| 단계 | 날짜 | 세션·모델 | 결과 | 메모 |
|---|---|---|---|---|
| §1 설치·스모크 | 2026-11-27 | WP-21 서브에이전트(Opus 5.5) | 통과 | §3 |
| M2 블러(리허설 20장) | | | | |
| M3 SfM(C-02) | | | | |
| M4 메시 | | | | |
| M5 splat | | | | |
| M6 후처리·정합 | | | | |
| M7 UE 임포트 (a)·(b) | | | | |
