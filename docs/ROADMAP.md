# 로드맵 / 진행 상황

마지막 갱신: 2026-09-24
최우선 원칙: **게임 퀄리티**(DECISIONS.md 참고)

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
| 1.0a | **사용자 PC**: 사양 확인 완료(7500F / 32GB / RTX 5060 8GB / 1TB, D-006) → **업그레이드 여부 결정**(GPU → 저장장치 → RAM 순). 결정 전까지 Postshot 최종 학습은 AWS에서. 툴 설치: UE 5.8.3, VS 2026, Git LFS, RealityScan 2.2, Postshot(Studio), XGRIDS LCC4Unreal. 로컬 Claude Code 세션 준비(D-006) | 👤 | UE 에디터 실행, C++ 빌드 성공 |
| 1.0b | **저장소·UE 프로젝트 골격** (아래 "구조" 참고) — 🟡 코드 작성 완료(C++ 캐릭터·게임모드, 설정, 테스트 레벨 Python, 빌드 스크립트). **사용자 PC에서 빌드·실행 검증 대기** | 🤖 / 👤 검증 | 에디터에서 L_Dev가 뜨고, 캐릭터가 걷고 뛰고 점프한다 |
| 1.0c | **촬영 도구**: `golmok-exif`(EXIF 점검), `golmok-frames`(선명 프레임 추출), `golmok-blur`(EgoBlur 얼굴·번호판 블러, 로그·GPS·미리보기) — 🟡 코드·단위테스트 완료. **실제 아이폰 사진(ProRAW 현상 포함)과 EgoBlur 모델로 검증 대기** | 🤖 / 👤 검증 | 리허설 사진에서 EXIF 리포트가 나오고, 블러가 적용되고, 누락률을 육안으로 점검 |
| 1.0d | **아이폰 리허설**(가이드 §4-C): 사진 20장 + 영상 1분 → 셔터 속도와 선명도 확인 | 👤 촬영 / 🤖 EXIF 점검 스크립트 | 대부분의 컷이 1/200s 이상이고 흔들림 없음 |
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

**산출물**
- `docs/research/08-spike-results.md`(비교 스크린샷과 수치)
- **D-010: 환경 표현 방식 확정**

### 1.2 베이스맵(배경) 빌더 — 🟡 코드·테스트 완료, **실데이터 빌드·UE 임포트 검증 대기**

| 작업 | 담당 | 상태 / 완료 기준 |
|---|---|---|
| `golmok-basemap`: GIS건물통합정보 SHP + NGII DEM·정사영상 → LOD1 건물(층고·용도·색조 정점 데이터)·지형(정사영상 텍스처) GLB 타일 + manifest + 3D Tiles 1.1 tileset | 🤖 | ✅ 합성 데이터 테스트 통과, 3d-tiles-validator 오류 0·경고 0 |
| 데이터 다운로드: V-World(건물), 국토정보플랫폼(DEM·정사영상) | 👤 로그인 | 대기 (runbook §5) |
| 실제 SHP 필드 확인(`inspect`) → 빌드 | 🤖 (PC 세션) | 대기 |
| UE 임포트 `basemap_import.py`: Nanite, 복합 충돌, 축·단위 자동 측정, CesiumGeoreference 원점 | 🤖 | 코드 완료, 에디터 검증 대기 |
| **절차적 파사드 머티리얼** `M_BasemapFacade`(층별 창, 상가 1층, 업무 커튼월, 옥상) — Python으로 생성 | 🤖 | 코드 완료, 에디터 검증 대기 → 스크린샷 리뷰에서 "박스 느낌" 판단(👤) |
| 원경 안개·대기·조명 프리셋 | 🤖 | 1.3 조명 프리셋과 함께 |
| 플레이 구역 안 배경 제거 | 🤖 | `--exclude zone.geojson`으로 빌드 단계에서 제외(D-012) |

### 1.3 캐릭터·카메라·조명 (C++)

| 작업 | 완료 기준 |
|---|---|
| 3인칭 캐릭터(C++): 걷기, 뛰기, 점프, Enhanced Input, 카메라 붐(충돌 보정) | 키보드·마우스와 게임패드로 조작 |
| 애니메이션: 기본은 UE 5.8 기본 캐릭터·애니메이션 세트(Motion Matching 등 5.8 제공 기능 평가) | 이동이 자연스럽다 |
| 조명 프리셋: 시간대(아침·흐림·저녁) 전환, Lumen, 안개 | 시간대를 바꿔도 환경이 자연스럽다(D-010 결과에 따름) |
| 디버그: 충돌 와이어프레임, 성능 HUD, 고정 카메라 경로 재생 | 스파이크와 회귀 측정에 재사용 |

### 1.4 골목 Zone 통합
- D-010 방식으로 **골목 전체**를 처리하고 청크로 나눈다.
- 충돌: RealityScan 메시를 단순화하고 계단·턱을 정리한다. 유리·쇼윈도는 blocker로 막는다.
- 정합: RealityScan GPS/GCP로 좌표를 잡고, CesiumGlobeAnchor로 배치하고, 배경 LOD1과 육안 및 ICP 검증을 한다.
- 이음새 처리: 배경과의 경계 블렌드, 골목 끝 "출구" 방향의 원경 처리.
- 완료 기준: 골목 전 구간을 걷고 뛰는 동안 끼임, 떨림, 구멍이 없고, 품질 목표 fps를 달성한다.

### 1.5 실내 1곳
| 작업 | 담당 |
|---|---|
| 소유자 서면 동의서 템플릿 작성 → 사용자가 서명을 받는다 — ✅ 초안 `outreach/interior-consent-form-draft.md` | 🤖 초안 / 👤 |
| **촬영 가이드 #2(실내)** 작성 → 촬영 — ✅ 가이드 `capture/02-interior-capture-guide.md` | 🤖 / 👤 |
| 실내 Zone 제작(D-010 방식), 문 포털, 실외↔실내 전환(레벨 스트리밍, 노출·조명 전환) | 🤖 |
| 완료 기준: 골목에서 문을 열고 들어가 실내를 돌아다니고 다시 나올 수 있다 | |

### 1.6 폴리시·성능·검수
- 품질 목표 fps를 맞추도록 튜닝한다(Nanite, VSM, Lumen 설정, splat 예산).
- 렌더 결과에서 얼굴·번호판 누락을 재검사한다(05 문서).
- 내부 검수 뷰어(웹, 선택): splat과 충돌을 오버레이해 확인한다.
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
- 모바일 재평가, 확장 지역
- 법률 자문 → 약관, 위치기반서비스사업 신고, 보안성 검토 → 공개 베타
