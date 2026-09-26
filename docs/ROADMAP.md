# 로드맵 / 진행 상황

마지막 갱신: 2026-09-25
최우선 원칙: **게임 퀄리티**(DECISIONS.md 참고)

> **실행 계획**: Phase 1을 작업 패키지(WP-01~08)·PC 검증(V-01~06)·사용자 작업(C-01~06)으로 풀어 쓴 문서가 [`DEVELOPMENT-PLAN.md`](DEVELOPMENT-PLAN.md)이고, 현재 상태는 [`plan/STATUS.md`](plan/STATUS.md)에 있다. 아래 1.x 단계와 WP의 대응은 DEVELOPMENT-PLAN §5.1 표를 본다.

## Phase 0 — 조사 및 설계 ✅ 완료

| # | 항목 | 산출물 | 상태 |
|---|---|---|---|
| 1 | 베이스맵 데이터 소스 | `research/01-basemap-data.md` | 완료 |
| 2 | 재구성 파이프라인 | `research/02-reconstruction-pipeline.md` | 완료 |
| 3 | 엔진·플랫폼 | `research/03-engine-platform.md` → **D-003에서 UE5로 결정** | 완료 |
| 4 | 아키텍처 | `ARCHITECTURE.md` | 완료(UE 반영) |
| 5 | 법·정책 | `research/05-legal-policy.md` | 완료 |
| + | 파일럿 지역 비교 | `research/06-pilot-area.md` | 완료(최종 선택 대기) |
| + | UE5 툴체인 검증 | `research/07-ue5-toolchain.md` | 완료 |
| + | S-Map 문의 초안 | `outreach/smap-inquiry-draft.md` | 완료(사용자 발송) |
| + | 촬영 가이드 #1 (골목) | `capture/01-alley-capture-guide.md` | 완료 |
| – | 결정 | `DECISIONS.md` D-001~D-011 | **승인 완료.** 남은 것: 사용자 PC 사양 확인(D-006), 홈 Zone 선택(D-008) |

---

## Phase 1 — MVP

> **M1 클라우드 코드 완료 — 2026-09-25**: WP-01~08 전부 main 병합(PR #2~#13), CI 초록. M2 PC 검증 진행 중(V-01 §0~2·V-02·V-03 🟢, V-04 대기). 후속 클라우드 WP-09(Zone Index 발견·비동기 로드) → WP-11(뷰어 충돌 오버레이) → WP-10(애니메이션 평가·기능 제안) 등록(DEVELOPMENT-PLAN §5.1).

**목표**
1. 파일럿 지역 베이스맵(배경) 위에서 3인칭 캐릭터가 걷고 뛴다.
2. 골목 1곳이 **고품질 실촬영**으로 들어간다. 플레이 구역은 전부 실촬영이다.
3. 건물 1곳의 내부에 들어가 돌아다닌다.

**플랫폼**: 고사양 PC(Windows)
**품질 목표(제안)**:
- RTX 5090, 4K, DLSS Quality에서 60fps 이상
- RTX 4070 Ti급, 1440p, DLSS Quality에서 60fps 이상
- (측정 하한선) 사용자 PC RTX 5060 8GB, 1080p에서 플레이 가능 수준(30fps 이상)
- 근경 0.5m에서 텍스처가 뭉개지지 않을 것
- 캐릭터 그림자가 골목 바닥과 벽에 자연스럽게 떨어질 것

담당: 👤 사용자 / 🤖 Claude / 👥 함께

### 1.0 준비 (병행)

| # | 작업 | 담당 | 완료 기준 |
|---|---|---|---|
| 1.0a | **사용자 PC**: 사양 확인 완료(7500F / 32GB / RTX 5060 8GB / 1TB, D-006) → **업그레이드 여부 결정**(GPU → 저장장치 → RAM 순). 결정 전까지 Postshot 최종 학습은 AWS에서. 툴 설치: UE 5.8.3, VS 2026, Git LFS, RealityScan 2.2, Postshot(Studio), XGRIDS LCC4Unreal. 로컬 Claude Code 세션 준비(D-006) — 🟡 **UE 개발 환경 완료(2026-09-24, PC 세션)**: UE 5.8.3(2026-09-24 기준 최신 핫픽스), VS 2026 Community 18.10.2(C++ 게임 개발 워크로드, MSVC 14.51, Windows SDK 10.0.26100), Git LFS 3.7.1, Python 3.12.10, ffmpeg 9.0.2, ExifTool, **NVIDIA 드라이버 617.14 WHQL**(2026-09-25 591.86에서 업데이트, 사용자 요청. UE 로그의 "610 미만 TSR 16-bit 꺼짐" 경고 사라짐, CUDA·UE 확인). 에디터 실행·C++ 빌드 성공. GitHub 로그인 완료(PC 세션 push 가능). **추가 설치(2026-09-25, PC 세션)**: Postshot 1.1.69(사용자 승인으로 EULA 동의, 무료판 상태 — Studio 구독은 C-04), Cesium for Unreal 2.29.1(GitHub 공식 zip, SHA-256 일치, Apache-2.0), XGRIDS LCC4Unreal 3.4.0(사용자가 developer.xgrids.com에서 받음, UE 5.8 빌드), Node.js 24.19.0 LTS(뷰어·3d-tiles-validator용). Cesium·LCC는 **엔진 플러그인 폴더**(`Engine\Plugins\Marketplace`)에 설치해 저장소는 그대로이고, 프로젝트에서는 아직 켜지 않았다(스파이크 1.1에서 켬). 두 플러그인 모두 UE에서 로드 확인. Cesium은 로드 시 `LogClass: Error: FCesiumMetadataPropertyStatisticValue::Semantic` 1줄을 남긴다(플러그인 내부, 프로젝트 무관). **남은 것(👤)**: 업그레이드 결정, RealityScan 2.2 설치(Epic 런처 → 언리얼 엔진 → 리얼리티스캔 탭, Epic 약관 동의) | 👤 | UE 에디터 실행, C++ 빌드 성공 |
| 1.0b | **저장소·UE 프로젝트 골격** (아래 "구조" 참고) — ✅ **사용자 PC에서 검증 완료(2026-09-24)**. UE 5.8.3에서 C++ 빌드 무수정 통과(5.8 API 변경 영향 없음, 경고는 엔진 헤더의 deprecation뿐). `setup_dev_level`로 L_Dev 생성 → PIE에서 `GolmokGameMode`가 `GolmokCharacter` + 마네킹(`SKM_Manny_Simple`, `ABP_Unarmed`)을 스폰한다(`DefaultGame.ini` 경로 그대로 맞음). **자동 테스트 `Golmok.Player.Movement`**(`tools/ue/test.ps1`, 실제 키 입력 주입): 걷기 W/A/S/D 180 cm/s·방향 일치, Shift 달리기 500 cm/s → 떼면 180, 점프 정점 90 cm·0.87초 후 착지, 마우스 시점(오른쪽→오른쪽, 위→위), 골목 벽 카메라 충돌(벽면 y=−250, 카메라 y=−236). `Golmok.log`에 프로젝트 에러 없음. 스크린샷 `runbooks/pc-setup-L_Dev-pie.jpg`. 남은 것(👤, 선택): 직접 1분 플레이해 조작감 확인 | 🤖 / 👤 검증 | 에디터에서 L_Dev가 뜨고, 캐릭터가 걷고 뛰고 점프한다 |
| 1.0c | **촬영 도구**: `golmok-exif`(EXIF 점검), `golmok-frames`(선명 프레임 추출), `golmok-blur`(EgoBlur 얼굴·번호판 블러, 로그·GPS·미리보기) — 🟡 코드·단위테스트 완료. PC 환경 준비 완료(2026-09-24): `pytest` 34개 통과, torch 2.11 + CUDA 12.8에서 `cuda.is_available()` True(RTX 5060). ⚠ **발견**: rawpy 0.27.1(LibRaw 0.22.1)은 Adobe DNG SDK 없이 빌드돼 **JPEG-XL ProRAW(DNG 1.7)를 현상하지 못한다**. iPhone 16 Pro/17 Pro는 ProRAW 형식으로 JPEG 무손실 / JPEG-XL 무손실 / JPEG-XL 손실을 고를 수 있다 → `golmok-exif`가 ProRAW 압축 형식을 세어 경고하고, `golmok-blur`의 `decode_error`가 원인을 적는다. → ProRAW 형식 **JPEG 무손실**로 결정(D-011 승인, 가이드 #1 v3). **남은 것**: EgoBlur Gen1 모델(👤 라이선스 동의 후 `tools\models\`), 실제 리허설 사진으로 검증 | 🤖 / 👤 검증 | 리허설 사진에서 EXIF 리포트가 나오고, 블러가 적용되고, 누락률을 육안으로 점검 |
| 1.0d | **아이폰 리허설**(가이드 §4-C): 사진 20장 + 영상 1분 → 셔터 속도와 선명도 확인 — ⏳ 사진이 아직 PC에 없음(2026-09-24). ProRAW 형식은 **JPEG 무손실**로 찍는다(D-011 승인, 가이드 #1 v3 §4-A) | 👤 촬영 / 🤖 EXIF 점검 스크립트 | 대부분의 컷이 1/200s 이상이고 흔들림 없음 |
| 1.0e | S-Map 문의 발송 | 👤 | 발송 완료(회신은 병행으로 대기) |
| 1.0f | **촬영 누적(가는 곳마다)**: 가이드 #1 §0 체크 후 골목 촬영 → 원본은 PC와 외장 디스크에 보관, `notes.md` 작성 → 촬영 목록(`captures/INDEX.md`)에 등록 | 👤 | 골목 1곳 이상 촬영(사진 약 1,300장, 영상 15분 이상) |
| 1.0g | **홈 Zone 선정**: 촬영한 골목 중 실내 동의 가능한 가게와 배경이 갖춰진 1곳을 고른다(D-008) | 👥 | D-008에 홈 Zone 기록 |

### 1.1 스파이크 — 환경 표현 방식 확정 (약 2주)

**홈 Zone** 골목 데이터에서 **30~50m 청크 1개**를 골라 세 방식으로 만든다. **조명과 카메라 경로를 똑같이 두고 비교**한다.

| 경로 | 구성 |
|---|---|
| (a) | RealityScan 메시(High detail, 8K UDIM, Virtual Texture) → **Nanite + Lumen** |
| (b) | Postshot splat(원본 해상도, SH3) → 3D Tiles(로컬 변환기) → **Cesium for Unreal splat LOD** |
| (c) | 같은 .ply → **XGRIDS LCC4Unreal(LCC2, Lit + ProxyMesh = (a)의 메시)**. 여유가 있으면 Volinga도 |
| (a+c) | 하이브리드: (a) 메시를 기본으로 두고, 전선·식생·간판 부분만 (c) splat로 보강 |

**측정 항목**(자동화: Unreal Python으로 고정 카메라 경로 재생, 스크린샷, `stat unit`/`stat gpu` 로그)

| 항목 | 방법 |
|---|---|
| 시각 품질 | 고정 시점 10곳(원경·중경·근경 0.5m)의 스크린샷을 원본 사진과 나란히 비교 |
| 캐릭터 그림자·조명 통합 | 캐릭터가 바닥과 벽에 그림자를 떨어뜨리는지, 태양 각도 3단계 변경에 환경이 반응하는지 |
| 이음새 | 청크 경계, 배경 LOD1과의 경계, 메시와 splat의 경계 |
| 얇은 구조물 | 전선, 철망, 난간, 간판 가장자리 |
| 성능 | 4K와 1440p, DLSS 끔/켬에서 평균·1% low fps, GPU ms, VRAM |
| 제작 비용 | 처리 시간(학습·변환), 수작업 시간 |

**준비된 도구**(2026-09-24 PC 에디터 검증):
- 조명 프리셋 `golmok.lighting` — ✅ 4개 프리셋 적용 후 태양 각도·조도·색온도·스카이·안개·노출 값을 되읽어 전부 일치.
- 고정 시점 저장·일괄 캡처 `golmok.viewpoints` — ✅(조건부) save·goto 정상. **버그 수정**: 스크린샷이 빠지거나 **다른 시점 이름으로 저장**됐다(스크린샷은 뷰포트의 다음 그리기에서 찍히는데, 그 그리기가 카메라 이동 뒤에 일어남). 이제 파일이 기록될 때까지 기다리고, 안 나오면 "missing"으로 알린다. 게임 뷰로 찍어 에디터 아이콘이 안 나온다. 재검증: L_Dev 3시점 × 프리셋 2개 = **6/6 저장, 이름·시점 일치**. ⚠ **캡처 중에는 에디터 창을 앞에 둔다** — 백그라운드에 오래 있던 에디터는 뷰포트를 그리지 않아 스크린샷이 안 나온다("백그라운드에서 CPU 덜 쓰기"를 꺼도 같음, UE 5.8.3). 무인 캡처는 PIE/`-game`의 `HighResShot`으로 한다(WP-06 `spike_runner`에 반영 필요).
- 성능 요약 `golmok-perf` — ✅ 실제 UE 5.8.3 CSV로 확인. **버그 2개 수정**: 실제 CSV의 긴 이벤트 필드에서 파싱 실패, `-csvCaptureFrames` 부팅 캡처의 맵 로딩 프레임(7.5초)이 평균에 섞임. `-game` 실행의 CSV는 `%LOCALAPPDATA%\UnrealEngine\5.8\Saved\Profiling\CSV`에 생긴다. 사용자 PC 기준선(빈 L_Dev): 1080p 158 fps, 1440p 128 fps(`research/08` "기준선").
- 스파이크 자동화 `golmok.spike_runner`(WP-06) — 🟡 코드 완료·PC 검증 대기: 시점 10곳 이름 고정(`far_01..03 mid_01..04 near_01..03`), PIE 무인 캡처(`capture_all`: 태그 a/b/c/ac × 프리셋 × 시점, dwell 경로 재생 + `golmok.screenshot`, HUD 끔), `-game -RenderOffscreen` 성능 스크립트(`game_scripts` → `.ps1` → `golmok-perf`), 컨택트 시트 HTML, research/08 표 템플릿. 전체 절차 `runbooks/pc-spike.md`.

**산출물**
- `docs/research/08-spike-results.md`(템플릿 작성됨. 비교 스크린샷과 수치)
- **D-010: 환경 표현 방식 확정**

### 1.2 베이스맵(배경) 빌더 — 🟢 실데이터 빌드·UE 임포트 검증 완료 (2026-09-24), **5 m DEM(수치지형도) 반영 (2026-09-25)**

| 작업 | 담당 | 상태 / 완료 기준 |
|---|---|---|
| `golmok-basemap`: GIS건물통합정보 SHP + NGII DEM·정사영상 → LOD1 건물(층고·용도·색조 정점 데이터)·지형(정사영상 텍스처) GLB 타일 + manifest + 3D Tiles 1.1 tileset | 🤖 | ✅ 합성 데이터 테스트 통과, 3d-tiles-validator 오류 0·경고 0 |
| 데이터 다운로드: V-World(건물), 국토정보플랫폼(DEM·정사영상) | 👤 로그인·신청서 | ✅ 서울 SHP `AL_D010_11_20260909`(기준일 2026-09-09), 수치지형도 1:5,000 Ver2.0 6도엽(2025, 등고선·표고점 → 5 m DEM), 공개DEM `37608`(90 m, 가장자리 채움용), 정사영상 2025 25 cm `37608077`·`37608078`. 절차는 runbook §5 |
| 실제 SHP 필드 확인(`inspect`) → 빌드 | 🤖 (PC 세션) | ✅ 높이 A16, 지상층수 A26, 용도명 A9, ID A1(근거 D-012). 연남동 반경 1 km: **건물 9,447동**(높이 추정 4,258동 = A16 결측 → 층수×3.2 m), 250 m 타일 64개, 10초 |
| **정사영상 좌표 보정** `golmok-basemap georef-ortho` | 🤖 | ✅ NGII 2025 정사영상 TIFF에 좌표 정보가 없음 → 도엽번호로 배치 + 건물 윤곽 매칭(peak 0.26/0.29) + 인접 도엽 겹침 정렬(1.000). 절대 ~1 m, 도엽 간 이음새 0 |
| **5 m DEM** `golmok-basemap contour-dem` | 🤖 | ✅ 수치지형도 등고선·표고점 → TIN → 5 m GeoTIFF(EPSG:5186). 표고점 10% 제외 검증 중앙 0.63 m / RMSE 2.1 m. 지형 5~101 m(궁동산·와우산·성미산이 보임). 근거 D-012 |
| UE 임포트 `basemap_import.py`: Nanite, 복합 충돌, 축·단위 자동 측정, CesiumGeoreference 원점 | 🤖 | ✅ `fit error 18.7`(128메시 합계, cm) → 사실상 0, M=diag(1,−1,1) = **북쪽 −Y** 확인(정사영상 도로·경의선숲길·홍제천 방향이 지도와 같음). 새 레벨 `L_Basemap_Yeonnam`(`run(…, level=…)`: 조명·지면 PlayerStart 자동) |
| **절차적 파사드 머티리얼** `M_BasemapFacade`(층별 창, 상가 1층, 업무 커튼월, 옥상) — Python으로 생성 | 🤖 | ✅ 창·층 띠·상가 1층 패턴 보임(스크린샷 아래). "박스 느낌" 판단은 👤 리뷰 |
| 지형 머티리얼 `M_BasemapTerrain`(정사영상 파라미터, Nanite 사용 플래그) | 🤖 | ✅ glTF 기본 머티리얼(플러그인 `MI_Default_Opaque`)은 Nanite 플래그가 없어 패키징 시 깨질 수 있어 교체 |
| 캐릭터 보행 | 🤖 | ✅ PIE 스크립트 보행: 7초 동안 10.7 m 이동, `is_moving_on_ground` True. 지면 충돌 추적 13×13 격자 169/169, 타일 경계 3 cm 옆 597/597. 지형은 Nanite 끔(Nanite fallback 충돌이 경계에 틈을 냄, D-012) |
| 성능 (RTX 5060, `-game -RenderOffscreen`, PlayerStart 거리 시점, `golmok-perf`) | 🤖 | 1080p **평균 169 fps, 1% low 141**(GPU 5.4 ms, Render 7.4 ms; 5 m DEM·지형 Nanite 끔). 90 m DEM 때 169/137. 1440p는 GPU ms가 거의 같아 해상도 적용 여부 재확인 필요. 에디터 PIE는 ~120 fps(에디터 상한) |
| 원경 안개·대기·조명 프리셋 | 🤖 | 1.3 조명 프리셋과 함께. 현재 기본 안개로 원경이 뿌옇고 지면이 청록빛 — 룩 개발 필요 |
| **검수 뷰어** `golmok-viewer`(CesiumJS): 레이어 토글, 와이어프레임, ENU 좌표, headless 스모크 테스트 | 🤖 | ✅ 합성 베이스맵 렌더 확인(18타일, 오류 0). 1.6의 검수 도구를 앞당겨 완료 |
| 플레이 구역 안 배경 제거 | 🤖 | `--exclude zone.geojson`으로 빌드 단계에서 제외(D-012) |

- 5 m DEM(2026-09-25): 개관(북쪽을 봄, 뒤 언덕이 궁동산) / 사선 / DEM 음영기복도

  ![5 m DEM 개관, 북쪽을 봄](images/basemap-yeonnam-2026-09-25-dem5m/overview-north.jpg)
  ![5 m DEM 사선](images/basemap-yeonnam-2026-09-25-dem5m/oblique.jpg)
  ![수치지형도로 만든 5 m DEM 음영기복도(북쪽 위, ±1.3 km)](images/basemap-yeonnam-2026-09-25-dem5m/dem-5m-hillshade.jpg)

- 90 m DEM 때(2026-09-24) 스크린샷(에디터 PIE, 기본 조명·안개): 북쪽 위 정사 / 사선 / 골목 파사드. 원본 1920×1080과 개관·보행 후 컷은 PC의 `%USERPROFILE%\golmok_data\review\basemap_yeonnam_2026-09-24\`

  ![연남동 베이스맵, 위에서 본 모습(북쪽이 위)](images/basemap-yeonnam-2026-09-24/topdown-north-up.jpg)
  ![사선에서 본 LOD1 건물과 파사드](images/basemap-yeonnam-2026-09-24/oblique.jpg)
  ![골목 높이: 층별 창과 1층 상가 패턴](images/basemap-yeonnam-2026-09-24/street-facades.jpg)
- 생성된 UE 에셋(`Content/Golmok/Basemap/`, `L_Basemap_*`, `M_Basemap*`)은 스크립트로 다시 만들 수 있어 커밋하지 않는다(`.gitignore`, 약 130 MB).

### 1.3 캐릭터·카메라·조명 (C++)

| 작업 | 완료 기준 |
|---|---|
| 3인칭 캐릭터(C++): 걷기, 뛰기, 점프, Enhanced Input, 카메라 붐(충돌 보정) | 키보드·마우스와 게임패드로 조작 |
| 애니메이션: 기본은 UE 5.8 기본 캐릭터·애니메이션 세트(Motion Matching 등 5.8 제공 기능 평가) — 🟢 리서치 완료(WP-10, 2026-09-25) → ⚪ PC 평가 대기(V-08): `research/09-animation-ue58.md`(현행 `ABP_Unarmed` / GASP 이식 / Motion Matching 최소 구성 3안, 5.8 릴리스 노트 인용). **권장: GASP(Game Animation Sample) 로코모션 이식을 먼저 시험**. 단 Fab EULA·UE EULA·GASP 리스팅 라이선스 원문은 컨테이너에서 403 → V-08 §0에서 사용자가 확인. 런북 `runbooks/pc-verify-animation.md`(채점표: 자연스러움·발 미끄러짐·전환·계단·조작감·fps·용량) | 이동이 자연스럽다 |
| 조명 프리셋: 시간대(아침·흐림·저녁) 전환, Lumen, 안개 — 🟢 PC 검증 통과(V-03, 2026-09-25)(WP-05; night 프리셋은 태양 off + real-time SkyLight라 화면이 검어 look-dev에서 달빛/최소 lux 결정 필요 — 원인·후보 메모 `design/lighting-night-lookdev.md`(WP-10), 결정은 D-010 뒤 폴리시): 단일 소스 `Config/Golmok/lighting_presets.json`(4 시간대 + `interior` 오버레이), `Lighting/GolmokTimeOfDay`(2 s 보간, 키 1~4/F5, 콘솔 `golmok.tod`), `lighting.py`가 같은 JSON을 읽음 | 시간대를 바꿔도 환경이 자연스럽다(D-010 결과에 따름) |
| 디버그: 충돌 와이어프레임, 성능 HUD, 고정 카메라 경로 재생 — 🟢 PC 검증 통과(V-03, 2026-09-25)(WP-05; PIE 재생 CSV → `golmok-perf` 119 fps/1% low 104, HUD `render` ms 0.00 표시 문제는 WP-09 🟡에서 정리): `Debug/GolmokDebugSubsystem`+`AGolmokHUD`(F1 HUD: fps 평균·1% low·Game/Render/GPU ms·Zone·프리셋·ENU 좌표, F2 충돌 표시, `golmok.path record/play --csv` → `golmok-perf`, `golmok.screenshot`), 통계·경로 JSON은 순수 헤더 `GolmokStatsMath.h`로 g++ 교차검증. 런북 `runbooks/pc-verify-wp05.md`(V-03) | 스파이크와 회귀 측정에 재사용 |

### 1.4 골목 Zone 통합
- D-010 방식으로 **골목 전체**를 처리하고 청크로 나눈다.
- 충돌: RealityScan 메시를 단순화하고 계단·턱을 정리한다. 유리·쇼윈도는 blocker로 막는다.
- 정합: `golmok-align`(WP-07 ✅ 합성 검증, 실 Zone은 V-05)으로 GPS prior → 벽·지면 ICP → manifest 갱신 → CesiumGlobeAnchor로 배치, 배경 LOD1과 육안 검증.
- 이음새 처리: 배경과의 경계 블렌드, 골목 끝 "출구" 방향의 원경 처리.
- 재구성 후처리 도구 — ✅ `golmok-mesh`(청크·충돌·blocker)·`golmok-splat`(정리·3D Tiles), 절차 `runbooks/recon-postprocess.md`(WP-03).
- Zone 데이터 계약 — ✅ `spec/zone-manifest.md`(manifest·Index 스키마, 좌표·UE 매핑 규약) + `golmok-zone` CLI(WP-02). 배경 제외는 `golmok-zone exclude` → `golmok-basemap --exclude`.
- UE 런타임 Geo·Zone — 🟢 PC 검증 통과(V-03, 2026-09-25; 합성 Zone 좌표·충돌·blocker·거리 로드/언로드·베이스맵 숨김 전부 런북 기대값과 일치)(WP-04): `Geo/`(ENU↔UE 변환, 원점 액터), `Zones/`(manifest 로더, 거리 로드/언로드, priority, 태그 기반 베이스맵 숨김). 검증 런북 `runbooks/pc-verify-wp04.md`(V-03).
- 에디터 임포트 `golmok.zone_import`(WP-06) — 🟡 코드 완료·PC 검증 대기: WP-03 zone 폴더(OBJ 청크 + MTL/UDIM PNG + collision GLB + blockers.json) → 임포터 축 프로브 → 사전변환 사본 임포트(Nanite, bounds 검증) → UDIM VT 텍스처·`M_ZoneScan`·`MI_<material>` 슬롯 할당 → manifest 복사 → `AGolmokZone` 리빌드. 합성 zone 생성기 `tools/scripts/make_synthetic_zone.py`(클라우드 테스트)와 런북 `runbooks/pc-verify-wp06.md`(V-04).
- Zone Index 런타임 발견·비동기 로드(WP-09) — 🟢 PC 검증 통과(V-07, 2026-09-26: 빌드 무수정, 자동화 16/16, 발견·파괴·비동기 로드·포털 대기 런북 전부 ✅, `GOLMOK_RENDER_TIME_SOURCE` 1 유지 — HUD render = `stat unit` Draw, 0.00은 엔진 값; 히치 async ≥ sync; 런북 §12): 레벨에 액터를 놓지 않아도 `Content/Golmok/Zones/index/`(`golmok-zone index build` 출력, `zone_index.sync`)에서 플레이어 주변 3×3 셀의 zone을 Transient 스폰·파괴(배치 액터 우선), 청크 에셋은 `FStreamableManager` 비동기(`Loading` 상태, 완료는 다음 틱, 취소는 세대 검사), 포털은 실내를 선로드하고 `Loading`이면 Pending 유지. V-03 발견(HUD `render` ms 0.00 → `OnBeginFrame` 캐시+직전 유효값 유지, 실내 `blocked` → `portal` 표시) 정리. 콘솔 `golmok.zone.index`. 런북 `runbooks/pc-verify-wp09.md`.
- 완료 기준: 골목 전 구간을 걷고 뛰는 동안 끼임, 떨림, 구멍이 없고, 품질 목표 fps를 달성한다.

### 1.5 실내 1곳
| 작업 | 담당 |
|---|---|
| 소유자 서면 동의서 템플릿 작성 → 사용자가 서명을 받는다 — ✅ 초안 `outreach/interior-consent-form-draft.md` | 🤖 초안 / 👤 |
| **촬영 가이드 #2(실내)** 작성 → 촬영 — ✅ 가이드 `capture/02-interior-capture-guide.md` | 🤖 / 👤 |
| 실내 Zone 제작(D-010 방식), 문 포털, 실외↔실내 전환(레벨 스트리밍, 노출·조명 전환) — 포털·전환은 🟢 PC 검증 통과(V-03, 2026-09-25)(WP-05; 합성 실내 문 왕복·오버레이·언로드 지연·두 스트리밍 경로 확인): `Portals/GolmokPortal`(manifest `portals[]`에서 자동 스폰, 반경 안 선로드, 문 평면 통과로 노출·안개 오버레이, 3 s 지연 언로드), 레벨 스트리밍 `LevelInstance`(기본)/`NamedStreamingLevel`(ini), 합성 실내 픽스처 `z_synthetic_001_interior` + `synthetic_zone.run(interior=True)` | 🤖 |
| 실내 zone 에디터 준비 `golmok.interior_setup`(WP-06) — 🟡 코드 완료·PC 검증 대기: 포털 왕복 검사(같은 점·반대 yaw) → 에셋 임포트 → 서브레벨 `L_<zone_id>`(PointLight만, 레벨 좌표) → 부모 zone 리빌드 | 🤖 |
| 완료 기준: 골목에서 문을 열고 들어가 실내를 돌아다니고 다시 나올 수 있다 | |

### 1.6 폴리시·성능·검수
- 품질 목표 fps를 맞추도록 튜닝한다(Nanite, VSM, Lumen 설정, splat 예산).
- 렌더 결과에서 얼굴·번호판 누락을 재검사한다(05 문서).
- 내부 검수 뷰어(웹, 선택): splat과 충돌을 오버레이해 확인한다. — 🟢 WP-08(`golmok-viewer`: footprint·청크 bbox·포털·blockers 평면) + 🟢 WP-11(2026-09-25, PR #16: 충돌·blocker **GLB 메시** 오버레이·토글, 원점 E·N·U 축, `--zone` 마운트, 축 변환 교차검증). splat 오버레이는 D-010 스파이크(V-05) 뒤.
- (선택, D-013·D-016 승인 2026-09-25) 포토 모드 최소판 **WP-12** ⚪ · 기본 환경음(앰비언스·발소리·실내 전환) **WP-13** ⚪ — MVP 범위 밖 선택 항목, 클라우드 코드 → PC 검증(V-09·V-10). 시간대 폴리시(WP-14)는 D-010 뒤.
- Phase 1 회고를 하고 Phase 2 계획을 세운다.

---

## 저장소 구조 (1.0b에서 생성)

```
golmok/
  docs/
  unreal/Golmok/                 UE 5.8 프로젝트
    Source/Golmok/               C++ 게임 모듈 (캐릭터, 카메라, Zone, 디버그)
    Content/Python/              Unreal Python 에디터 자동화 (임포트, 배치, 측정)
    Config/  Plugins/            (XGRIDS 등 서드파티 플러그인은 라이선스 확인 후)
  tools/
    golmok_tools/                Python 패키지: exif_report, extract_frames, privacy/blur (1.0c)
                                 (이후 basemap: SHP·DEM → 3D Tiles, splat: ply → 3D Tiles 추가 예정)
    ue/                          UE 빌드·에디터·패키징 PowerShell 스크립트
  .gitattributes                 LFS: *.uasset *.umap (lockable), 텍스처·메시
  .gitignore                     Binaries/ Intermediate/ Saved/ DerivedDataCache/ data/
```

- 원천 데이터(사진, 영상, .ply 원본, RealityScan 프로젝트)는 저장소 **밖**에 둔다. 외장 디스크와 비공개 버킷에 보관한다.
- UE 에디터가 없는 클라우드 세션에서는 C++ 컴파일과 에디터 실행 검증을 할 수 없다. 그래서 **빌드 검증은 사용자 PC(Claude Desktop 세션)에서** 한다. 빌드 방법은 루트 README와 `tools/ue/*.ps1`에 있다.

## Phase 2 이후 (방향)
- 서버 자동화 파이프라인(COLMAP + gsplat, D-002 준수, RunPod/국내 클라우드)
- 크라우드 촬영 앱, 업로드와 검수 도구, 동의·신고 관리
- 게임 기능(D-013~D-017 승인 2026-09-25): Zone 지도·이동 + 세이브(WP-15, Zone 2곳 이상), 날씨 비(WP-16, D-010 뒤), 현장 녹음·Zone별 소리(WP-17), 포토 모드 확장
- 모바일 재평가, 확장 지역
- 법률 자문 → 약관, 위치기반서비스사업 신고, 보안성 검토 → 공개 베타
