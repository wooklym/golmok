# golmok-objcap — Apple Object Capture CLI (WP-21 후보)

RealityKit `PhotogrammetrySession`(Apple Object Capture)을 감싼 작은 Swift 명령줄 도구다. D-022로 Mac이 유일한 개발 기기가 되면서 RealityScan(D-005 메시 단계)을 쓸 수 없게 됐고, 이 도구는 그 **대체 후보**다. 채택 결정이 아니다.

- 이 도구는 공개 API를 호출하고, API가 돌려준 값을 그대로 파일로 쓴다. `colmap` 하위 명령만 예외로, 아래에 적은 측정된 규약으로 좌표를 변환한다.
- 품질이 RealityScan과 같다고 **주장하지 않는다**. 최종 판정은 실촬영 데이터로 하는 D-010 / 카드 V-05의 몫이고, 실촬영 데이터는 아직 없다.
- 외부 패키지 의존성은 없고 Apple OS 프레임워크만 쓴다(RealityKit, Foundation, ImageIO, CoreGraphics, simd). D-002의 비상업/AGPL 금지 목록에 해당하는 코드는 없다. Apple 약관 확인 결과는 [§7](#7-약관-소유자-사실-확인-필요)에 있다.

## 1. 빌드

Xcode 27.2 툴체인으로 빌드한다. sudo는 필요 없다. 빌드 산출물은 repo 밖에 둔다.

```bash
cd tools/mac/objcap
swift build -c release --scratch-path ~/golmok-tools/objcap/build
BIN=~/golmok-tools/objcap/build/release/golmok-objcap
```

- `--scratch-path` 없이 `swift build`를 실행하면 `.build/`가 생긴다. 이 폴더는 `.gitignore`가 막는다.
- 배포 대상은 macOS 14다. macOS 15 API와 macOS 26 API는 `#available` 검사로 감쌌다.

## 2. 사용법

```bash
$BIN limits                      # isSupported, Limits, 기기 정보를 JSON으로 출력
$BIN run <imageFolder> <outDir> [옵션]
$BIN colmap <outDir>/poses.json <colmapDir> [<outDir>/pointcloud.ply]   # 실험적, §5
```

`golmok-objcap limits`는 지원되면 `0`, 지원되지 않으면 `3`으로 끝난다.

`golmok-objcap run` 옵션:

| 옵션 | 값 (기본값) | API |
|---|---|---|
| `--detail` | `preview` `reduced` `medium` `full` `raw` (`medium`) | `Request.Detail` |
| `--format` | `obj` `usdz` `both` (`obj`) | `.modelFile(url:)` (OBJ는 폴더 URL → `<outDir>/obj/`, USDZ → `<outDir>/model-<detail>.usdz`) |
| `--ordering` | `sequential` `unordered` (`unordered`) | `Configuration.sampleOrdering` |
| `--sensitivity` | `normal` `high` (`normal`) | `Configuration.featureSensitivity` |
| `--poses` | — | `.poses` → `<outDir>/poses.json` |
| `--point-cloud` | — | `.pointCloud` → `<outDir>/pointcloud.ply` (binary PLY, xyz float + rgba uchar) |
| `--no-object-masking` | — | `Configuration.isObjectMaskingEnabled = false` |
| `--ignore-bounding-box` | — | `Configuration.ignoreBoundingBox = true` (macOS 15+) |
| `--checkpoint <dir>` | — | `Configuration.checkpointDirectory` |

- 진행 상황(단계, 진행률, 남은 시간 추정)은 stderr에 찍힌다.
- `<outDir>/summary.json`에는 설정, 기기 정보와 Limits, 단계별 시작 시각, `invalidSample`, `skippedSample`, `automaticDownsampling`, `stitchingIncomplete`, 결과 파일과 크기, 오류가 남는다.
- 종료 코드:
  - `0`: 성공
  - `1`: 처리 실패, 또는 요청한 출력이 오지 않음
  - `2`: 사용법 오류
  - `3`: 이 기기에서 `PhotogrammetrySession`이 지원되지 않음
- stderr의 `Warning (secondary thread): ... usdUtils/assetLocalization.cpp` 줄은 프레임워크 내부 USD 경고다. 두 데이터셋 모두 출력에는 영향이 없었다.

데이터는 repo 밖에 둔다. 시험용 입력과 출력은 `~/golmok_data/recon-smoke/objcap/` 아래에 있다. 우리 촬영본은 D-007에 따라 `golmok-blur`를 먼저 거친 뒤 넣는다.

## 3. 출력

OBJ 폴더(`obj/`)에는 다음 파일이 생긴다. 이름의 해시는 실행마다 바뀐다.

- `baked_mesh_<hash>.obj`
- `.mtl`
- `.usda`
- 텍스처 PNG 3장: `_tex0`(diffuse), `_norm0`(normal), `_ao0`(AO)
- `full`/`raw`에서는 추가로 `_roughness0.png`와 `_disp0.exr`(displacement)가 생긴다(Tyrol full에서 확인).

시험한 두 데이터셋에서는 맵마다 1장씩(UDIM 없음) 나왔고, 크기는 medium 4096², full 8192²였다.

`poses.json`의 샘플마다 들어 있는 항목:

- `sample_id`, `image`(`Poses.urlsBySample`의 파일 이름)
- `translation`: `Pose.translation`
- `rotation_quaternion_xyzw`: `Pose.rotation`
- `transform_matrix_rows`: `Pose.transform.matrix`를 행 우선으로 쓴 것
- `intrinsics_rows`: `Pose.intrinsics`, macOS 26+
- `lens_distortion`: `Pose.lensDistortionData`의 `center`와 `radial_lookup_table`, macOS 26+
- `image_file_info`: 이 도구가 ImageIO로 읽은 픽셀 크기와 EXIF 초점거리. API 출력이 아니다.

값은 float32를 double로 넓힌 것이고 변환은 하지 않았다.

## 4. 좌표계: Apple 문서 vs 측정

Apple이 문서화한 것(SDK `RealityFoundation.swiftmodule/arm64e-apple-macos.swiftdoc`, Xcode 27.2):

- `Pose`는 "A 6DOF pose relative to the estimated coordinate system"이고, `Pose.transform`은 "A unit scale transform"이다.
- `Pose.intrinsics`는 "the estimated pinhole camera intrinsics matrix"이고, 없으면 nil이다.
- `LensDistortionData`는 반경 방향 상대 배율 LUT다. 첫 칸은 반경 0, 마지막 칸은 이미지에서 가장 큰 반경에 해당한다. Apple 예제 코드의 보정식은 `rectified = center + (1 + mag(r)) · (p − center)`다.
- 카메라 축 방향, world→camera와 camera→world 중 어느 쪽인지, 단위는 **문서화돼 있지 않다**.
- 공식 문서 페이지: <https://developer.apple.com/documentation/realitykit/photogrammetrysession>, <https://developer.apple.com/documentation/realitykit/photogrammetrysession/request>, <https://developer.apple.com/documentation/realitykit/photogrammetrysession/limits-swift.struct>

**측정한 것**(2026-11-27, 이 Mac). 데이터셋은 AliceVision Buddha 67장이고, 데이터셋에 딸린 카메라별 투영행렬 P(OpenCV 규약)와 비교했다. 데이터셋이 하나뿐이므로 일반화는 [미확인]이다.

- `Pose.transform`은 **camera→world**다. `translation`이 카메라 중심이고, 카메라 축은 **x 오른쪽, y 위, z 뒤**(−Z 방향을 봄, RealityKit/ARKit식)다.
  - 유사변환을 맞춘 뒤 카메라 중심 잔차 RMS는 분산 폭의 0.11%였다.
  - `R_gt ≈ S·R_pose·diag(1,−1,−1)`로 놓았을 때 회전 오차는 평균 0.05°, 최대 0.10°였다.
  - 다른 세 가지 축 가설은 오차가 모두 약 180°였고, world→camera 가설은 잔차가 95%였다.
- `intrinsics`는 **원본 입력 이미지 픽셀 단위**의 3×3 K다. 행은 `[fx 0 cx; 0 fy cy; 0 0 1]`이다.
  - Buddha(2736×1540): fx 1852.7, 데이터셋 값 1860.9(−0.4%), cx·cy 차이 2 px 미만.
  - Tyrol(5472×3648): fx 4289.3. EXIF 35 mm 환산 28 mm에서 계산한 4256과 +0.8% 차이다.
  - 같은 카메라의 모든 샘플이 같은 K를 받았다.
  - `lens_distortion.center`는 K의 주점과 같았다. LUT는 2048칸이고, 최대 배율은 Buddha 0.0044였다.
- 메시(OBJ), 희소 점군, 포즈는 **같은 좌표계**에 있다. Buddha의 메시 bbox와 점군 bbox가 일치했다.
- 위쪽(Y)과 단위:
  - GPS EXIF가 있는 Tyrol(DJI)에서 Apple +Y는 위쪽(ENU 기준 (0.005, 0.005, 1.000))이었고, 카메라 간 거리는 GPS 거리의 중앙값 0.988배로 거의 미터였다.
  - EXIF가 없는 Buddha PNG는 미터가 아니었다. 머리 높이가 1.1 단위로 나왔다.
  - 스케일이 GPS에서 오는지는 [미확인]이다. 대상을 바닥 y=0에 올려 놓고 원점을 대상 bbox 중심으로 다시 잡는 것으로 보인다(두 데이터셋 모두 메시 y 최솟값이 0).
- Unreal로 가져올 때: USD `upAxis = "Y"`, `metersPerUnit = 1`. Y-up → Z-up 변환은 기존 `golmok-mesh` 정렬 단계의 몫이고, 이 도구는 다루지 않는다.

## 5. COLMAP 변환 (`colmap`, 실험적)

`golmok-objcap colmap`은 아래 식으로 `poses.json`을 COLMAP 텍스트 모델로 바꾼다. D-005는 스플랫과 메시가 같은 좌표계를 공유해야 한다고 요구한다. 그래서 Object Capture 포즈로 COLMAP 희소 모델을 만들어 스플랫 트레이너(Brush 등)에 넣는 경로를 확인했다.

```
R_c2w(OpenCV) = R_pose · diag(1, −1, −1)
R_w2c = R_c2w(OpenCV)ᵀ,  t_w2c = −R_w2c · C   (C = Pose.translation)
qvec  = R_w2c 의 쿼터니언 (w, x, y, z)
cameras.txt: PINHOLE W H fx fy cx cy    (Pose.intrinsics, 이미지 픽셀 크기)
points3D.txt: 희소 점군, track 없음, ERROR 0
```

- 검증했다: Buddha에서 내보낸 `images.txt`를 데이터셋 P와 비교했다.
  - 중심 잔차 0.11%, 회전 평균 0.05°.
  - 희소 점이 이미지 안에 투영되는 비율은 평균 96.9%였다.
- [미확인]:
  1. 렌즈 왜곡. LUT는 COLMAP 카메라 모델이 아니므로 적용하지 않는다(PINHOLE). 해결책은 둘 중 하나다.
     - Apple 예제식으로 이미지를 먼저 보정(rectify)해서 PINHOLE을 그대로 쓴다.
     - LUT를 OPENCV `k1, k2`에 맞춘다.
     Buddha 수준(0.44%)에서는 가장자리 오차가 수 px다. 광각·48 MP에서는 클 수 있다.
  2. track 없는 points3D를 Brush 같은 트레이너가 받는지 [미확인]. Brush, COLMAP 모두 이 Mac에 설치돼 있지 않아 시험하지 못했다.
  3. 스플랫을 실제로 학습했을 때 메시와 겹치는지(시각 확인) [미확인].
  4. 희소 점군 밀도(Buddha 18k, Tyrol 36k점)가 스플랫 초기화에 충분한지 [미확인].
  5. Apple 약관 §2.2 C(2)가 이 경로에 걸리는지([§7](#7-약관-소유자-사실-확인-필요)).

## 6. 측정값 (2026-11-27)

측정 환경:

- Apple M5 Max, Mac17,14, 18코어(P6+E12), 128 GB, macOS 27.2.1 (26B131)
- 측정 중에 UE 패키징 작업이 백그라운드에서 함께 돌았다. 시간은 상한 쪽으로 보는 게 맞다.

`golmok-objcap limits` 결과:

| 항목 | 값 |
|---|---|
| `isSupported` | true |
| `maximumNumberOfInputImages` | **2000** |
| `maximumInputImageDimension` | **16384** px |
| macOS 26 포즈 intrinsics / 왜곡 API | 있음 |

실행 결과(시간은 `/usr/bin/time -l`의 real, 피크 메모리는 같은 출력의 peak memory footprint):

| 데이터셋 | 입력 | detail | 시간 | 피크 메모리 | 메시 | 텍스처 | 출력 |
|---|---|---|---|---|---|---|---|
| Buddha | 67장 PNG 2736×1540 (4.2 MP) | medium, OBJ+USDZ, 포즈·점군 | 103 s | 4.9 GB | 25,003 v / 50,000 tri | 3장 4096² | OBJ 폴더 41.5 MB(obj 5.6 MB), USDZ 32.4 MB, 점 18,105 |
| Tyrol 교회(드론) | 76장 JPEG 5472×3648 (20 MP) | medium, OBJ, 포즈·점군 | 671 s | 32.9 GB | 50,673 v / 100,000 tri | 3장 4096² | OBJ 폴더 68.5 MB, 점 35,934 |
| Tyrol 교회(드론) | 같음 | full, OBJ, 포즈, checkpoint(새 폴더) | 645 s | 33.0 GB | 125,678 v / 250,000 tri | 5장 8192²(tex·norm·ao·roughness PNG, disp EXR) | OBJ 폴더 421.7 MB(obj 28.7 MB, disp 170.5 MB, tex 87.3 MB) |

- full이 medium보다 짧았다. 백그라운드 UE 작업의 부하가 달랐기 때문으로 보이며 [미확인], 두 등급의 시간 차이는 이 측정으로 말할 수 없다. 체크포인트 폴더는 full 실행 때 새로 만든 것이라 이전 결과를 재사용하지 않았다.
- **실행마다 좌표계가 조금씩 다르다.** Tyrol medium과 full의 카메라 중심(같은 76장)은 중앙값 0.116, 최대 0.125 단위(분산 폭 약 102 단위의 0.1%) 어긋났다. 메시, 포즈, 점군은 **같은 실행**에서 받은 것끼리만 같은 좌표계로 봐야 한다.
- 세 실행 모두 `invalidSample`, `skippedSample`, `stitchingIncomplete`, `automaticDownsampling`이 0이었다.
- Tyrol medium의 단계별 시작 시각(초):
  - imageAlignment 11
  - pointCloudGeneration 50
  - meshGeneration 133
  - textureMapping 612
  - optimization 640
- Tyrol medium의 메시는 X·Z ±261 × ±249, 높이 151 단위(≈ m)의 마을과 계곡 전체를 덮었다.
  - 정점은 중심 반경 25 m 안(교회)에 3,870개(8%), 25–60 m에 13,244개, 60 m 밖에 33,559개였다.
  - 즉 detail 등급별 폴리곤 예산이 장면 전체에 고르게 퍼진다. 넓은 장면은 bbox를 잘라서(`Request.Geometry`, 아직 옵션 없음) 구역별로 나눠 돌려야 한다.
- 시각 품질은 보지 않았다. Quick Look 썸네일 생성이 멈춰서 시각 확인을 하지 못했다. 품질 판정은 V-05가 한다.

## 7. 약관 (소유자 사실 확인 필요)

- 이 도구는 macOS SDK로 만든 내부 도구다. 근거는 Xcode and Apple SDKs Agreement(Xcode 27.2 동봉본 `/Applications/Xcode.app/Contents/Resources/en.lproj/License.rtf`)다.
  - §2.2 A(ii): "You may use the macOS SDKs to test and develop application and other software"
  - §2.11 F(Your Responsibility): "Apple does not claim any ownership rights in the generated content", 생성물의 권리 침해 책임은 사용자에게 있음. Object Capture에 한정된 조항이 아니라 Apple Software and Services 사용으로 생성된 콘텐츠 일반에 관한 조항이며, Object Capture 출력에 적용되는지 [미확인]
- **확인 필요 1.** 같은 계약 §2.2 C(2)는 "use output generated from an Apple model to train, fine-tune, or improve another artificial intelligence model"을 금지한다. Object Capture 포즈나 메시로 3DGS 스플랫을 학습하는 것이 여기에 해당하는지 [미확인]이다. 스플랫은 보통 'AI 모델'로 부르지 않지만 해석은 소유자가 확인해야 한다.
- macOS 소프트웨어 사용권 계약(로컬 사본 `/Library/Documentation/License.lpdf`)을 검색했다. Live Captions, Personal Voice, Genmoji, Photos 콘텐츠에는 '개인·비상업' 제한이 있지만 RealityKit이나 Object Capture 조항은 찾지 못했다. 사용권 목록: <https://www.apple.com/legal/sla/>
- **확인 필요 2.** Object Capture 출력의 상업적 사용을 명시적으로 허용하거나 금지하는 Apple 공식 문서는 찾지 못했다 [미확인]. 법률 판단이 아니라 사실 확인을 요청하는 항목이다.

## 8. 거리 규모(약 1,300장 × 48 MP)에 대한 위험 — **추정**

아래 숫자는 이 Mac에서 측정한 두 데이터셋을 바탕으로 한 **추정**이고, 검증되지 않았다.

- **한도.** 1,300장은 한도 2000 안이다. 48 MP(8064×6048)는 한도 16384 px 안이다. 한도를 넘는 이미지는 `.invalidSample`로 버려진다(Apple 문서).
- **시간.** Tyrol 기준 약 1,530 MP 입력에 medium 670 s가 걸렸다. 1,300 × 48 MP ≈ 62,400 MP는 그 약 41배다.
  - 선형으로 늘면 medium 약 7–8시간이다.
  - 정합 단계가 선형보다 빨리 늘 수 있어 범위는 수 시간에서 하루 이상이다 [미확인].
- **메모리.** Tyrol medium의 피크가 32.9 GB였다. 128 GB에서 1,300 × 48 MP가 다운샘플 없이 들어가는지 [미확인]이다. 세션이 `automaticDownsampling`을 켜면 해상도를 잃는다.
- **폴리곤 예산.** detail 등급별 삼각형 수가 장면 크기와 상관없이 정해진다(측정: medium 50k–100k, Tyrol full 250k). 골목 한 구역 전체를 한 번에 돌리면 메시가 거칠어진다.
  - 대안: `raw`/`custom`, 또는 bbox 분할 실행, 또는 메시는 거친 충돌용으로만 쓰고 외관은 스플랫이 맡기(D-005의 역할 분담과 맞음).
- **Object Capture는 '물체'용으로 설계됐다.** 마스킹과 자동 bbox 기본값이 실내외 공간(골목 안에서 바깥을 보는 촬영)에서 어떻게 동작하는지 [미확인]. Tyrol은 드론이 물체를 둘러싸는 촬영이었다.
- **재현성.** 블랙박스다. 정합 파라미터를 직접 조정하거나 GCP를 쓸 수 없고, macOS 업데이트로 결과가 바뀔 수 있다.

## 9. 시험 데이터 (repo 밖, 커밋 금지)

| 이름 | 출처 | 라이선스 | 위치 |
|---|---|---|---|
| Buddha (67장 + P 행렬) | <https://github.com/alicevision/dataset_buddha> @ `9067f679` (Gasparini, Castan, Lanthony 2017, doi:10.5281/zenodo.1203283) | CC BY 4.0 (repo `LICENSE.md`) | `~/golmok_data/recon-smoke/objcap/buddha/` |
| Tyrol 교회 드론 (76장) | <https://github.com/IRCSS/Tyrol-Church-Photogrammetry-Dataset> @ `7f4d24c4` (Shahriar Shahrabi, Rein in Taufers, 촬영 14.7.2020) | CC BY 4.0 (repo `LICENSE.md`) | `~/golmok_data/recon-smoke/objcap/tyrol/` |

실행 출력, `summary.json`, 로그도 같은 폴더 아래에 있다(`out-medium/`, `tyrol-medium-default/`, `tyrol-full/`).
