# Golmok 개발 전체 과정 설계 (Development Plan)

작성일: 2026-09-24 · 상태: **v1, Phase 0 산출물(PR #1) 기반**
근거: `ROADMAP.md`, `DECISIONS.md`(D-001~D-012), `ARCHITECTURE.md`, `research/01~08`
읽는 순서: 이 문서 → `plan/STATUS.md`(현재 상태) → 해당 `plan/WP-*.md`(작업 패키지 상세)

> 이 문서는 "무엇을, 누가, 어디서, 어떤 순서로, 언제 끝났다고 볼지"를 정한다.
> `ROADMAP.md`는 Phase 1의 목표·품질 기준·단계(1.0~1.6)를 정의한 원본이며, 이 문서는 그것을 **실행 단위(작업 패키지)와 검증 게이트**로 풀어 쓴 것이다. 충돌하면 `DECISIONS.md` > `ROADMAP.md` > 이 문서 순으로 우선한다.

---

## 0. 한 장 요약

| 항목 | 내용 |
|---|---|
| 제품 | 실제 서울 골목을 촬영해 3D로 재구성하고, 그 안을 걷고 뛰며 건물 안까지 들어가는 PC 게임 |
| 최우선 원칙 | **게임 퀄리티**(D-003). 난이도·비용보다 최종 화면 품질 |
| 엔진·스택 | UE 5.8.3 + Cesium for Unreal, C++ 로직, Unreal Python 자동화, Python 도구, Git LFS |
| 재구성 | RealityScan(메시) + Postshot(splat), 사용자 PC 처리, 얼굴·번호판 블러 필수 |
| 실행 주체 3곳 | **클라우드 Claude 세션**(코드·도구·문서, UE 없음) / **PC Claude 세션**(UE 빌드·에디터·재구성 실행) / **사용자**(촬영·구매·계정·판단) |
| Phase 1 목표 | 베이스맵 위 3인칭 이동 + 고품질 실촬영 골목 1곳 + 실내 1곳 (품질 목표 fps는 ROADMAP) |
| 진행 방식 | 클라우드에서 **작업 패키지(WP) 단위로 순차 개발** → PC에서 검증 게이트 통과 → 실데이터로 통합 |
| 다음 Phase | 2: 서버 파이프라인·크라우드 촬영 앱 / 3: 법률 자문·공개 베타 |

---

## 1. 비전과 제품 정의

### 1.1 한 줄 정의
"내가 걸었던 서울 골목을, 그대로 걸을 수 있는 게임." 촬영으로 만든 Zone이 서울 지도 위에 하나씩 쌓인다(D-008: 가는 곳마다 찍어 올리는 누적 방식). 최종 비전은 크라우드소싱으로 서울 골목을 채우는 것이다.

### 1.2 플레이어 경험 (MVP)
1. 게임을 켜면 **홈 Zone**(연남동 후보, D-008)의 골목 입구에 선다. 주변은 LOD1 배경 건물과 지형(D-004, D-012), 발밑과 눈앞은 실촬영 골목이다.
2. 걷고 뛰고 점프하며 골목을 끝까지 간다. 턱·계단·주차 차량이 실제 위치에 있고, 캐릭터 그림자가 바닥과 벽에 떨어진다.
3. 시간대를 바꾼다(아침·낮·저녁·밤). 같은 골목이 다르게 보인다.
4. 문 앞에 서면 들어갈 수 있는 가게가 표시된다. 문을 열고 들어가 실내를 둘러보고 다시 나온다.
5. (선택) 포토 모드로 장면을 찍는다.

### 1.3 MVP 범위 (Phase 1, ROADMAP과 동일)
- **들어감**: 3인칭 이동, 배경 베이스맵, 골목 Zone 1곳(실촬영), 실내 Zone 1곳, 시간대 조명, 디버그·측정 도구, 품질 목표 fps
- **안 들어감**: 멀티플레이, 퀘스트·수집, 세이브, 메뉴·설정 UI(최소 키 안내만), 모바일, 서버, 촬영 앱, 공개 배포
- **게임 기능 제안**: D-013~D-017 승인(2026-09-25, `design/game-features-proposal.md`) — 포토 모드, Zone 지도·이동, 시간대·날씨, 환경음, 세이브. **D-018 ① 승인(2026-09-27)**: Phase1의 캐릭터 로스터·콘솔 검증(WP-18a), 최종 에셋은V-08/V-12·② 이후, 선택 UI·세이브·커스터마이즈는Phase2 초반. 수집 요소는 미등록. 위 "안 들어감"의 MVP 범위를 바꾸지 않는다.

### 1.4 품질 정의
ROADMAP "품질 목표"를 그대로 쓴다. 요약하면 (1) 고사양에서 4K 60fps, (2) 중급에서 1440p 60fps, (3) 사용자 PC(RTX 5060, 1080p) 30fps 이상, (4) 근경 0.5m 텍스처 유지, (5) 캐릭터 그림자 자연스러움. 품질은 **스크린샷 비교 + `golmok-perf` 수치**로 판단하고 결과를 `research/08`에 남긴다.

---

## 2. 개발 원칙 (요약, 원문은 CLAUDE.md·DECISIONS.md)
1. **퀄리티 최우선.** 선택지가 갈리면 화면 품질이 높은 쪽.
2. **조사·설계 → 승인 → 코드.** 돈이 들거나 스택·데이터 소스를 고르는 일은 사용자 승인. 라이선스는 원문 확인 후 기록(D-002).
3. **로직은 C++, 에디터 작업은 Unreal Python, Blueprint 최소.** 바이너리 에셋은 LFS. 원본 촬영물·.ply·RealityScan 프로젝트·모델 가중치는 git 금지.
4. **프라이버시 우선.** 모든 이미지는 `golmok-blur` 후 재구성. 블러 전 데이터는 외부 서비스 업로드 금지(D-007).
5. **검증되지 않은 것은 완료가 아니다.** 클라우드에서 쓴 UE 코드는 PC 게이트(§6)를 통과해야 "완료". 클라우드 산출물은 `plan/STATUS.md`에 "🟡 코드 완료·검증 대기"로 표기한다.
6. **문서가 상태의 원본.** 결정은 `DECISIONS.md`, 진행은 `ROADMAP.md` + `plan/STATUS.md`, 작업 상세는 `plan/WP-*.md`.

---

## 3. 전체 로드맵과 마일스톤

```
Phase 0  조사·설계 ─────────────────────────────── ✅ 완료 (PR #1)
Phase 1  MVP
  ├ 1A  클라우드 코드 트랙   WP-01~08 ✅ M1 (2026-09-25) → 후속 WP-09·11·10   ← 지금 여기
  ├ 1B  PC 셋업·검증 트랙    V-01~V-06 (PC Claude 세션 + 사용자)
  ├ 1C  촬영·데이터 트랙     C-01~C-06 (사용자)
  ├ 1D  스파이크 1.1 → D-010 (환경 표현 방식 확정)
  ├ 1E  통합: 골목 Zone + 실내 Zone + 조명·폴리시
  └ 1F  검수·회고 → Phase 2 계획
Phase 2  파이프라인 자동화(COLMAP+gsplat) · Zone 백로그 처리 · 촬영 앱 · 게임 기능 확장
Phase 3  법률 자문 · 약관·신고 · 공개 베타 · 배포
```

| 마일스톤 | 내용 | 완료 기준 | 의존 |
|---|---|---|---|
| **M1 클라우드 코드 완료** — **🟢 2026-09-25** | WP-01~08이 main에 있고 클라우드 테스트(pytest, lint, CI) 통과 | `plan/STATUS.md`에 WP 전부 🟡 이상, CI 초록 (PR #2~#13) | 없음 |
| **M2 PC 빌드·PIE 검증** | UE 5.8.3에서 C++ 빌드 성공, L_Dev에서 이동·시간대·디버그 HUD·Zone 로더(합성 데이터) 동작 | `runbooks/pc-verify-*.md` 체크리스트 통과, 스크린샷 | M1, V-01 |
| **M3 배경 베이스맵** | 실데이터(SHP+DEM+정사)로 홈 Zone 반경 1km 배경 임포트, 캐릭터가 걸음 | ROADMAP 1.2 완료 기준 | M2, C-03 |
| **M4 D-010 확정** | 스파이크 1.1 측정 완료, `research/08` 작성, 환경 표현 방식 결정 | D-010 승인 | M3, C-01, C-02, V-03 |
| **M5 골목 Zone** | 골목 전 구간 걷기·뛰기, 끼임·구멍 없음, 품질 목표 fps | ROADMAP 1.4 완료 기준 | M4 |
| **M6 실내 Zone** | 문 → 실내 → 문 왕복, 노출·조명 전환 자연스러움 | ROADMAP 1.5 완료 기준 | M5, C-05 |
| **M7 MVP 완료** | 폴리시·성능 튜닝, 블러 누락 재검사, 회고, Phase 2 계획 | ROADMAP 1.6 완료 기준 | M6 |

---

## 4. 실행 주체와 역할 분담

| 주체 | 할 수 있는 것 | 할 수 없는 것 |
|---|---|---|
| **클라우드 Claude 세션** (Opus, 이 저장소만 있음) | Python 도구·테스트, UE C++/Python 소스 작성, 문서, CI, 웹 뷰어, 합성 데이터 테스트 | UE 빌드·에디터 실행, GPU 학습, 실데이터 접근, 결제·로그인 |
| **PC Claude 세션** (사용자 Windows PC, Claude Desktop/`claude remote-control`) | UE 빌드·PIE·패키징, 에디터 Python 실행, RealityScan/Postshot 실행, 실데이터 빌드, fps 측정 | 결제·약관 동의·계정 로그인(사용자 확인 필요, `runbooks/pc-setup.md` 규칙) |
| **사용자** | 촬영, 하드웨어·소프트웨어 구매, 계정·약관, 데이터 다운로드(로그인), 동의서 서명, 품질 채점, 결정 승인 | — |

**핸드오프 규칙**
- 클라우드 → PC: WP마다 `runbooks/pc-verify-<wp>.md`를 남긴다. PC 세션은 그 체크리스트대로 검증하고 결과(통과/수정/스크린샷)를 같은 파일 하단 "결과"에 적는다. 수정한 코드는 같은 브랜치에 커밋한다.
- PC → 클라우드: 검증에서 나온 API 수정·설계 변경은 커밋 메시지와 `plan/STATUS.md`에 남긴다. 다음 클라우드 세션은 시작 시 STATUS를 읽는다.
- 사용자 → 세션: 촬영물은 `captures/INDEX.md`에 등록, 결정은 `DECISIONS.md`에 승인 표기.

---

## 5. Phase 1 상세 계획

### 5.1 트랙 1A — 클라우드 코드 (Claude Opus 세션, 순차 실행)

UE 에디터와 실데이터 없이도 만들 수 있고, 합성 데이터로 테스트할 수 있는 것을 먼저 만든다. 각 WP는 **한 세션이 처음부터 끝까지** 맡는다. 순서는 의존 관계 순이다.

| WP | 이름 | 핵심 산출물 | 완료 기준(클라우드) | 검증(PC) | 의존 |
|---|---|---|---|---|---|
| **WP-01** | 저장소 기반·CI | GitHub Actions(pytest, ruff, 설정 파일 검증), ruff 설정, `plan/STATUS.md` 운영 시작 | CI 초록, 기존 테스트 통과 | 없음 | — |
| **WP-02** | Zone 데이터 모델·CLI `golmok-zone` | manifest JSON 스키마(ARCHITECTURE §3.2), `init/validate/index/transform/exclude` 명령, ENU↔ECEF, Zone Index 셀 생성, 스펙 문서 | 합성 Zone으로 테스트 통과, 스키마 검증 | 실 Zone manifest 생성 | WP-01 |
| **WP-03** | 재구성 후처리 도구 `golmok-mesh`, `golmok-splat` | 메시 청크 분할(UDIM 유지), 충돌 메시 생성(단순화·평면 스냅·소요소 제거), blocker 평면, splat PLY 검사·크롭·플로터 제거, **PLY → 3D Tiles(KHR_gaussian_splatting) 로컬 변환기**(스파이크 (b)용, D-007 준수) | 합성 메시·PLY로 테스트, 3d-tiles-validator 통과 | RealityScan/Postshot 실출력으로 실행 | WP-02 |
| **WP-04** | UE C++ 런타임 1: Geo·Zone | `Geo/`(원점·ENU↔UE 변환 서브시스템), `Zones/`(manifest 파서, `AGolmokZone`, `UGolmokZoneSubsystem`: 거리 기반 로드, 우선순위, 배경 숨김·충돌 스왑) | 코드 리뷰 체크리스트, 합성 manifest 픽스처, PC 검증 런북 | **빌드 + PIE**(합성 Zone) | WP-02 |
| **WP-05** | UE C++ 런타임 2: 포털·조명·디버그 | `Portals/`(문 트리거, 실내 레벨 스트리밍, 노출 전환), `Lighting/`(시간대 프리셋 런타임 전환, 실내외 블렌드), `Debug/`(충돌 와이어프레임, 성능 HUD, 카메라 경로 녹화·재생 콘솔 명령) | 동일 | **빌드 + PIE** | WP-04 |
| **WP-06** | UE Python 에디터 자동화 2차 | `zone_import.py`(청크 메시+UDIM VT+충돌 임포트·배치), `interior_setup.py`(실내 서브레벨·포털 배치), `spike_runner.py`(시점·프리셋·경로 일괄 캡처와 CSV 프로파일 안내), `basemap_import` 보강(exclude 반영) | 순수 함수 단위테스트(unreal 모듈 모킹), PC 런북 | 에디터 실행 | WP-03, WP-05 |
| **WP-07** | 정합·검수 도구 `golmok-align` | GPS prior → 유사변환 → 베이스맵 LOD1과 ICP, 품질 지표(ICP RMSE, footprint IoU, 수직 기울기)를 manifest.quality에 기록, 블러 누락 재검사 리포트 | 합성 데이터 테스트 | 실 Zone 정합 | WP-02, WP-03 |
| WP-08 (선택) | 웹 내부 검수 뷰어 `tools/viewer` | 3D Tiles + Zone footprint + 충돌 오버레이(Three.js, MIT 스택) | Playwright 스모크 | 브라우저 | WP-02 |
| **WP-09** | UE C++ 런타임 3: Zone Index 발견·비동기 로드 | `Zones/GolmokZoneIndex`(셀 파서, 3×3 셀 조회, `GolmokGeoMath` 셀 공식), `UGolmokZoneSubsystem::DiscoverZones`(Index 기반 스폰·파괴, `Evaluate()` 밖), `AGolmokZone::LoadAsync`(FStreamableManager, `Loading` 상태·취소), `zone_import --with-index`, 콘솔 `golmok.zone.index`, V-03 디버그 표시 정리(HUD render ms, 실내 `blocked`) | 합성 Index 픽스처 pytest, g++ 셀 공식 교차검증, UE 자동화 5개, PC 런북 | **빌드 + PIE**(배치 액터 없이 발견·로드, 히치 비교) | WP-04, WP-05, WP-06 |
| **WP-10** | 애니메이션 평가·게임 기능 제안(문서) | `research/09-animation-ue58.md`, `runbooks/pc-verify-animation.md`, `design/game-features-proposal.md`(D-013~ 제안), `design/lighting-night-lookdev.md` | 링크 검사, 출처 인용 | PC 평가(런북), 사용자 승인 | — |
| **WP-12** | 포토 모드 최소판(D-013) | `Photo/`(포토 모드 서브시스템·자유 카메라 폰, 반경·footprint 클램프, FOV·노출·DOF·롤, 캐릭터/오버레이 숨김), `Config/Golmok/photo.json`, `golmok.photo*` 콘솔, 사진 PNG + 메타 JSON, 순수 헤더 g++ 교차검증 | UE 자동화 `Golmok.Photo.*`, pytest, 런북 | **빌드 + PIE**(V-09) | WP-05, WP-09 |
| **WP-13** | 환경음 기본(D-016 (a)) | `research/10-ambience-sources.md`(라이선스 원문 인용), `Audio/`(앰비언스 서브시스템 크로스페이드, 발소리 컴포넌트, 콘솔), `Config/Golmok/audio.json`, `audio_import.py`, WAV(LFS, ≤ 40 MB) 또는 플레이스홀더 생성기 | UE 자동화 `Golmok.Audio.*`, pytest, 런북 | **빌드 + PIE**(V-10) | WP-05, WP-12 |
| **WP-11** | 웹 검수 뷰어 2차: 충돌·blocker 오버레이 | `tools/viewer` collision.glb/blockers.glb 오버레이·토글(Cesium.Model, glTF Y-up 변환), 서버 GLB 서빙(경로 탈출 금지), Playwright 스모크 | `npm test`, pytest | 브라우저 | WP-03, WP-06, WP-08 |

- **후속(M1 이후, 2026-09-25 등록)**: 계획서에 남아 있던 항목을 WP-09(Zone Index 런타임 발견·비동기 로드 + V-03 디버그 표시 정리, Fable ultracode), WP-11(뷰어 충돌·blocker 오버레이, Opus), WP-10(애니메이션 평가·게임 기능 제안 문서, Opus)으로 묶었다. 순서 WP-09 → WP-11 → WP-10. `replaces.building_ids` 단위 런타임 숨김은 제외(베이스맵 타일이 건물을 병합하므로 빌드 단계 `golmok-zone exclude`가 정본, D-012).
- **게임 기능(D-013~D-017 승인 2026-09-25, 권장 우선순위대로)**: WP-12 포토 모드 → WP-13 환경음 기본(둘 다 Fable ultracode, 1.6 폴리시의 선택 항목이며 MVP 범위 §1.3은 그대로) → **WP-14** 시간대 폴리시(D-015 (a), D-010 확정 뒤; night look-dev는 PC) → **WP-15** Zone 지도·이동 + 세이브(D-014·D-017, Phase 2 초반: Zone 2곳 이상·V-07 통과) → **WP-16** 날씨 비(D-015 (b), Phase 2 중반, D-010 뒤) → **WP-17** 현장 녹음 절차·Zone별 소리(D-016 (b), 문서·촬영 가이드, Opus). WP-14 이후 스펙은 착수 조건이 충족될 때 쓴다.
- WP-08은 ROADMAP 1.6의 "(웹, 선택)"이었으나 2026-09-24에 CesiumJS 기반으로 **완료**했다(`tools/viewer`, `golmok-viewer`). UE 디버그 도구(WP-05)는 그대로 진행한다.
- Phase 2 서버 파이프라인(COLMAP+gsplat)은 이 트랙에 넣지 않는다(D-005: MVP는 수동).
- **병행(ChatGPT Astra, §7.6 캐릭터 레인, 2026-09-26 등록)**: **WP-18** 플레이어 캐릭터 — 설계(`design/character-concept.md`, `research/11-character-pipeline.md`, `plan/WP-18-characters.md`, D-018 제안) → 18a(`Characters/`, `Config/Golmok/characters.json`, 플레이스홀더 마네킹 교체·콘솔, 핫스팟은 훅만; pytest·g++ 교차검증·UE 자동화 `Golmok.Character.*`, 검증 V-11) → 18b(실제 에셋·리타깃·이모트, V-08·V-12 룩 검증·D-018 ② 뒤).

### 5.2 트랙 1B — PC 셋업·검증 (PC Claude 세션 + 사용자)

| V | 내용 | 런북 | 의존 |
|---|---|---|---|
| V-01 | PC 셋업: Git LFS, Python 도구, UE 5.8.3, VS 2026, 빌드, L_Dev, 리허설 사진 점검 | `runbooks/pc-setup.md` §0~§4 (기존) | 사용자 설치 |
| V-02 | 베이스맵 실데이터 빌드·임포트 | `runbooks/pc-setup.md` §5 (기존) | V-01, C-03 |
| V-03 | WP-04/05 C++ 빌드·PIE 검증(합성 Zone, 포털, 조명, 디버그) | `runbooks/pc-verify-wp04.md`, `pc-verify-wp05.md` | V-01, M1 |
| V-04 | WP-06 에디터 Python 검증(합성 청크 임포트, 실내 서브레벨) | `runbooks/pc-verify-wp06.md` | V-03 |
| V-05 | RealityScan/Postshot 실행 → WP-03·07 도구로 후처리·정합 → 스파이크 1.1 측정 | `runbooks/pc-spike.md`(WP-06에서 작성) | V-04, C-01, C-02 |
| V-06 | 골목 Zone·실내 Zone 통합, 성능 튜닝, 패키징 | `runbooks/pc-integrate.md`(M4 이후 작성) | M4 |
| V-07 | WP-09 Zone Index 발견·비동기 로드 검증(배치 액터 없이 발견·로드, 히치 비교) | `runbooks/pc-verify-wp09.md`(WP-09에서 작성) | V-04 |
| V-08 | 애니메이션 3안 PC 평가(L_Dev, 게임패드) | `runbooks/pc-verify-animation.md`(WP-10에서 작성) | V-01 |

### 5.3 트랙 1C — 촬영·데이터·구매 (사용자)

| C | 내용 | 가이드 | 언제 |
|---|---|---|---|
| C-01 | 아이폰 리허설(사진 20장 + 영상 1분) → EXIF 점검 | `capture/01` §4-C | V-01 직후 |
| C-02 | 골목 촬영 누적(가는 곳마다), 홈 Zone 후보 골목 1곳 이상(사진 약 1,300장, 영상 15분+) | `capture/01`, `captures/INDEX.md` | 리허설 통과 후, 흐린 평일 새벽 |
| C-03 | 베이스맵 데이터 다운로드(GIS건물통합정보 서울 SHP, NGII DEM·정사영상) | `runbooks/pc-setup.md` §5 | V-01 이후 |
| C-04 | 하드웨어·소프트웨어: GPU/저장장치/RAM 업그레이드 여부 결정(D-006), Postshot Studio 구독, XGRIDS 라이선스 문의 | `research/07` §2, D-006, D-009 | 스파이크 전 |
| C-05 | 실내 동의: 카페 등 1곳 서명 → 실내 촬영 | `outreach/interior-consent-form-draft.md`, `capture/02` | 홈 Zone 확정 후 |
| C-06 | S-Map 문의 발송(병행), 회신 관리 | `outreach/smap-inquiry-draft.md` | 아무 때나 |

### 5.4 의존성 그래프 (핵심 경로)

```
WP-01 → WP-02 → WP-03 → WP-06 ─┐
             └→ WP-04 → WP-05 ─┤
             └→ WP-07 ─────────┤
V-01 (PC 셋업) ← 사용자 설치     ├→ V-03/V-04 (PC 검증) → M2
C-03 (데이터) → V-02 → M3       │
C-01 → C-02 (촬영) ─────────────┴→ V-05 (스파이크) → M4 (D-010) → V-06 → M5 → C-05 → M6 → M7
```

- **핵심 경로는 사용자 촬영(C-02)과 PC 셋업(V-01)**이다. 클라우드 트랙(1A)은 이와 독립이라 먼저 끝낼 수 있다.
- D-010이 정해지기 전에는 Zone 시각 레이어 포맷을 코드에 고정하지 않는다. WP-04의 Zone 로더는 **메시(Nanite) 경로를 기본**으로 구현하고, splat 레이어는 플러그인 액터를 붙일 수 있는 확장점만 둔다.

---

## 6. 검증 게이트

| 게이트 | 어디서 | 통과 조건 | 실패 시 |
|---|---|---|---|
| **G1 클라우드** | GitHub Actions + 세션 내 pytest | pytest·ruff 통과, 설정 파일 유효, 문서 링크 유효 | 같은 세션에서 수정 후 재실행 |
| **G2 빌드·PIE** | PC 세션 | `build.ps1` 성공, PIE에서 런북 체크리스트 전부 통과, `Golmok.log` 에러 0 | PC 세션이 수정·커밋. 설계 변경이 필요하면 STATUS에 기록 → 다음 클라우드 세션 |
| **G3 실데이터** | PC 세션 | 실 SHP/DEM/사진/PLY로 도구 실행 성공, 결과 육안 확인 | 도구 수정 |
| **G4 품질·성능** | PC 세션 + 사용자 채점 | ROADMAP 품질 목표 fps, 스크린샷 채점표(`research/08`) | 튜닝 반복, 필요하면 D-010 재검토 |
| **G5 프라이버시·법** | 사용자 + 세션 | 렌더 결과 얼굴·번호판 누락 0(재검사 도구), 동의서 기록, 보안시설 회피 확인 | 재블러·재촬영·Zone 보류 |

---

## 7. 세션 운영 프로토콜 (트랙 1A)

### 7.1 브랜치·PR
- 통합 브랜치: **`claude/hopeful-allen-f0a0jb`** (PR #1 브랜치를 그대로 잇는다. PR #1이 먼저 병합되면 이 PR의 diff는 자기 변경만 남는다. **PR #1은 squash가 아니라 merge commit으로 병합**하는 것을 권장한다. add/add 충돌을 피하기 위해서다.)
- 모든 WP 세션은 이 브랜치에서 시작해 이 브랜치로 push한다. 세션은 순차 실행이므로 충돌이 없다. 새 PR은 만들지 않는다(이미 열린 PR을 쓴다).
- 커밋 단위: WP당 1~3개, 메시지 접두어 `WP-0N:`. `main` push·병합·force-push·히스토리 재작성 금지.

### 7.2 세션 시작·종료 절차 (각 WP 세션이 따른다)
1. 읽기: `CLAUDE.md` → `docs/DEVELOPMENT-PLAN.md` §2·§7 → `docs/plan/STATUS.md` → 자기 `docs/plan/WP-0N-*.md` → 관련 코드.
2. `docs/plan/STATUS.md`의 자기 WP를 `🔵 진행 중`으로 바꾸고 세션 ID를 적어 첫 커밋에 포함한다.
3. 구현·테스트. 라이선스가 있는 새 의존성은 원문을 확인하고 `DECISIONS.md` D-002 표에 추가한다.
4. 완료 기준을 전부 만족하면: 테스트 통과 로그를 WP 문서 "결과"에 요약, `STATUS.md`를 `🟡 코드 완료·PC 검증 대기`(UE 코드) 또는 `🟢 완료`(클라우드에서 완전 검증 가능한 것)로 갱신, `ROADMAP.md`의 해당 행 상태 갱신, PC 검증이 필요하면 `runbooks/pc-verify-<wp>.md` 작성.
5. 마지막 커밋 메시지에 "다음 세션 인계" 3줄(한 것, 남은 것, 주의)을 넣고 push.
6. 완료 기준을 못 채우면 `🔴 막힘`으로 표기하고 원인·시도한 것·필요한 결정을 STATUS에 적는다. 부분 산출물도 push한다.

### 7.3 세션 프롬프트 템플릿
```
당신은 Golmok 프로젝트의 WP-0N 담당 세션이다. 저장소의 CLAUDE.md, docs/DEVELOPMENT-PLAN.md(§2, §7),
docs/plan/STATUS.md, docs/plan/WP-0N-<name>.md를 먼저 읽고, WP-0N을 처음부터 끝까지 구현한다.
브랜치 claude/hopeful-allen-f0a0jb에서 작업하고 같은 브랜치로 push한다. 새 PR을 만들지 않는다.
완료 기준·산출물·검증 방법은 WP 문서를 따른다. 끝나면 STATUS.md와 WP 문서 "결과"를 갱신한다.
사용자 확인이 필요한 일(결제, 약관, 스택 변경)은 하지 말고 STATUS에 "결정 필요"로 적는다.
```

### 7.4 모델·예산·시간
- **모델 정책(2026-09-24 사용자 지시, 반드시 준수)**: Unreal Engine을 다루거나 게임성(비주얼·플레이 감각·성능)에 **직접** 영향을 주는 작업(WP-04·05·06, 이후 Zone 통합·조명·폴리시·스파이크 판단 등)은 **Claude Fable 5.1 + ultracode**(멀티 에이전트 워크플로: 설계 패널 → 구현 → 적대적 검증)로 한다. 조사, 파일 다운로드, 문서 정리, 단순 도구·CI처럼 비교적 단순한 작업은 오케스트레이터가 판단해 **Sonnet 또는 Opus**로 한다. WP-01~03(CI, Zone 스펙, 후처리 도구)은 정책 이전에 Opus로 시작했으므로 **병합 전에 Fable ultracode 적대적 리뷰**를 거친다.
- **ChatGPT Astra 병행(2026-09-26 사용자 결정)**: ChatGPT Astra도 §7.6 레인 안에서 UE C++를 포함한 구현을 맡는다. Unreal이나 게임성에 영향을 주는 Astra 변경은 병합 전에 **Fable ultracode 적대적 리뷰**를 거친다. PC 런북 검증은 Claude WP와 같이 병합 뒤 `🟡 코드 완료·PC 검증 대기` 상태에서 PC 세션이 한다. 엔진 안 품질의 최종 판단(룩 검증, 스파이크, 폴리시)은 계속 Fable이 한다.
- 권한 모드: auto. 세션당 예상 1~3시간(Fable ultracode 세션은 더 길 수 있다).
- 오케스트레이션: 설계 세션(이 문서를 쓴 세션)이 WP 세션을 하나씩 만들고, 끝나면 브랜치를 받아 pytest·STATUS·CI를 확인하고, 조건(CI 초록·충돌 없음·STATUS 🟢/🟡)을 만족하면 PR을 merge commit으로 병합한 뒤(사용자 승인 2026-09-24) 다음 세션을 만든다.
- 실패·중단 시: 같은 WP를 새 세션으로 다시 시작한다. STATUS의 인계 메모 덕분에 이어서 할 수 있다.

### 7.5 코드 규칙 (WP 공통)
- Python: 3.11+, `ruff` 통과, 타입 힌트, 순수 함수 우선, 외부 도구(ffmpeg 등)는 서브프로세스 경계에서만. 테스트는 `tools/tests/`, 합성 데이터는 테스트 코드 안에서 생성(픽스처 파일 최소).
- UE C++: 모듈 `Golmok` 안에 폴더별(`Geo/ Zones/ Portals/ Lighting/ Debug/`). 엔진 5.8 공개 API만, 플러그인(Cesium, XGRIDS)에 **컴파일 의존 금지**(런타임에 클래스 이름으로 찾거나 Python이 연결). `UPROPERTY(Config)`로 ini 설정. 로그 카테고리 `LogGolmok`. 새 모듈 의존은 `Golmok.Build.cs`에 추가하고 WP 문서에 이유를 적는다.
- Unreal Python: `unreal` 모듈 호출은 얇은 어댑터 함수로 감싸고, 계산 로직은 순수 함수로 분리해 클라우드에서 단위테스트한다.
- 문서: 한국어. 사실은 확인 수준 표기([확인]/[2차]/[미확인]).

### 7.6 에이전트 협업: Claude ↔ ChatGPT Astra (2026-09-26 사용자 결정)
사용자는 ChatGPT Astra(이하 Astra)를 Claude(Fable·Opus)와 함께 쓴다. Astra 쪽 상시 규칙은 저장소 루트 [`AGENTS.md`](../AGENTS.md)에 있다. 이 절은 두 쪽이 같이 지킨다. 목표는 두 가지다. **파일이 겹치지 않게 나누고**, 겹치더라도 **기계적으로 풀 수 있게** 한다.

**역할**

| | Claude Fable(ultracode) | ChatGPT Astra |
|---|---|---|
| 맡는 일 | 기존 WP 순서(WP-12~17), Astra PR 적대적 리뷰와 병합, 엔진 안 품질 판단(룩 검증·스파이크·폴리시), 공유 문서 갱신 | 배정받은 레인의 WP(조사·설계·코드·테스트·런북, UE C++ 포함), 컨셉 이미지 |
| 브랜치 | `claude/*`(WP 통합 브랜치 `claude/hopeful-allen-f0a0jb`), PC는 `pc/*` | `astra/<wp>-<주제>`(예: `astra/wp-18-design`) |
| 병합 | §7.4 오케스트레이션 | 스스로 병합하지 않는다. Fable 리뷰 → 사용자 승인 → Fable이 merge commit으로 병합 |

**레인(파일 소유)**: 레인 주인만 그 파일을 고친다. 새 레인은 사용자나 오케스트레이터가 WP를 배정할 때 이 표에 더한다.

| 레인 | 주인 | 경로 |
|---|---|---|
| 캐릭터(WP-18) | Astra | `unreal/Golmok/Source/Golmok/Characters/`, `Source/Golmok/Tests/GolmokCharacterRoster*.cpp`, `unreal/Golmok/Config/Golmok/characters.json`, `tools/tests/test_ue_character_roster*.py`, `tools/tests/test_ue_config_characters.py`, `tools/tests/fixtures/ue/charactermath*`, `docs/design/character-*`, `docs/spec/characters*`, `docs/research/11-*`, `docs/plan/WP-18*`, `docs/runbooks/pc-verify-wp18*`, `docs/outreach/character-*`, `docs/images/characters/` |
| 기존 게임 시스템 | Fable | `Source/Golmok/{Geo,Zones,Portals,Lighting,Debug,Photo,Audio}/`, `Player/`(파일이 모두 핫스팟이라 아래 훅 규칙을 따른다), 그 밖의 `Source/Golmok/Tests/*`, `Config/Golmok/*.json`(위 캐릭터 파일 제외), `unreal/Golmok/Content/Python/golmok/`, 기존 `tools/tests/*`(아래 핫스팟 제외) |
| 파이썬 도구 | 배정한 쪽 | `tools/golmok_tools/<모듈>/` 모듈 단위 |
| 문서 | 작성자 | 자기 WP 문서와 자기가 만든 research·design·runbook 문서 |

**공유 핫스팟 파일**: 두 쪽 모두 고칠 수 있지만 충돌이 잘 나는 파일이다.
- 코드·설정: `Source/Golmok/Player/GolmokCharacter.{h,cpp}`, `Player/GolmokPlayerController.{h,cpp}`, `GolmokGameMode.{h,cpp}`, `Golmok.Build.cs`, `Config/Default*.ini`, `tools/pyproject.toml`, `.github/workflows/ci.yml`, `tools/scripts/check_repo.py`, `.gitattributes`, `.gitignore`
- 등록 목록 테스트: 모듈 전체를 고정 목록과 정확히 비교하는 테스트다. 새 콘솔 명령, 새 모듈 의존, 새 소스 폴더를 더하면 이 목록에 한 줄을 더해야 한다.
  - `tools/tests/test_ue_wp09_fixture.py`의 `CONSOLE_COMMANDS`(모든 `FAutoConsoleCommandWithWorldAndArgs` 이름)와 `BUILD_CS_*`
  - `tools/tests/test_ue_zone_fixture.py`의 `CONVENTION_FOLDERS`
- 문서: `docs/plan/STATUS.md`, `docs/DECISIONS.md`, `docs/ROADMAP.md`, `docs/DEVELOPMENT-PLAN.md`, `CLAUDE.md`, `AGENTS.md`, `README.md`, `tools/README.md`

핫스팟 규칙:
1. **먼저 피한다.** 자기 폴더의 서브시스템, 엔진 델리게이트(예: `APlayerController::OnPossessedPawnChanged`), 자기 콘솔 명령, 자기 JSON 설정(`Config/Golmok/<기능>.json`)으로 해결할 수 있으면 핫스팟을 고치지 않는다.
2. **못 피하면 훅(hook)으로 최소 수정한다.**
   - 기존 줄은 고치거나 옮기거나 다시 포맷하지 않는다. 새 줄만 더한다. 기존 줄을 꼭 고쳐야 하면 PR 설명에 이유를 적는다.
   - 새 줄은 파일이나 섹션의 끝에 표지로 감싸 둔다: C++ `// [WP-NN hook] …` ~ `// [/WP-NN hook]`. 클래스 멤버는 클래스 본문의 끝(`};` 앞)에 둔다. ini는 자기 섹션을 파일 끝에 둔다. Build.cs는 모듈 이름 한 줄과 이유 주석 한 줄이다. Python 목록은 원소 한 줄을 목록 끝에 더하고 줄 끝에 `# [WP-NN hook] <이유>`를 단다.
   - 훅은 **별도 커밋**(`WP-NN: hook <파일>`)으로 둔다. 충돌이 나면 그 커밋만 새 main 위에 다시 적용한다.
3. **공유 문서는 Claude 쪽이 고친다.** Claude WP 세션은 지금처럼(§7.2) STATUS의 자기 행, ROADMAP, D-002 표를 제자리에서 고친다. 공유 문서에는 훅 표지를 쓰지 않는다. Astra는 자기 WP 문서 끝의 "병합 시 반영" 절에 문안을 두고, 병합하는 Fable 세션이 옮긴다. STATUS의 Astra 행은 "병행 트랙" 절에 따로 두어 다른 표와 붙지 않게 한다.
4. **유니티 빌드 이름**: 모듈은 유니티 빌드라 .cpp들이 이어 붙는다. 파일 범위 도우미는 익명 namespace 대신 자기 이름의 namespace(예: `GolmokCharacters`)에 둔다. 두 브랜치가 각자 통과해도 병합 뒤 이름이 겹치면 빌드가 깨진다(`tools/tests/test_lighting_presets.py`의 모듈 전체 검사는 익명 namespace만 잡는다).
5. **번호**(WP, V, D, research 번호)는 STATUS에 예약된 것만 쓴다. 새 번호가 필요하면 "병합 시 반영"에 예약 요청으로 적는다. 두 쪽이 같은 번호를 쓰면 먼저 병합된 쪽이 그 번호를 갖는다.

**동기화**
- 착수할 때와 PR을 올리기 전에 `git fetch origin`을 하고, 열린 브랜치가 같은 파일을 건드리는지 본다: `git diff --stat origin/main...origin/<브랜치>`(특히 `claude/hopeful-allen-f0a0jb`, `pc/*`, `astra/*`). 겹치면 PR 설명에 적는다.
- main을 따라갈 때는 자기 브랜치에 `git merge origin/main`을 한다. push한 브랜치는 rebase나 force-push를 하지 않는다.
- PR은 WP 단계마다 작게 나눈다. 커밋 순서는 ① 자기 레인 파일 ② 훅 ③ 문서다.
- 리뷰를 요청하기 전에 main과 충돌이 없는 상태로 만든다.

**충돌 해결**: 나중에 병합하는 쪽이 자기 브랜치에서 푼다.

| 파일 | 해결 |
|---|---|
| 상대 레인 파일 | 레인 주인의 버전을 그대로 쓴다. 내 의도가 필요하면 훅이나 후속 PR로 다시 넣는다 |
| 핫스팟의 훅 블록 | 양쪽을 다 살린다(서로 독립된 추가 줄이다). main 쪽 블록을 먼저 둔다 |
| STATUS·DECISIONS·ROADMAP·DEVELOPMENT-PLAN | main 버전을 받고 내 행·항목만 다시 넣는다 |
| 생성물·픽스처 | 손으로 합치지 않고 생성기로 다시 만든다(예: `tools/scripts/make_index_fixture.py`, `make_synthetic_zone.py`) |
| 번호 | 먼저 병합된 쪽이 갖는다. 나중 쪽이 번호를 바꾼다 |

해결한 뒤에는 게이트를 다시 돌린다: `ruff check`, `ruff format --check`, `pytest -q`, `check_repo.py`. C++을 건드렸으면 가능할 때 `tools/ue/build.ps1`과 `tools/ue/test.ps1`도 돌린다. 해결 커밋 메시지는 `merge origin/main: <충돌 파일> — <해결 방법>`이다.

**Astra PR 리뷰·병합**
- Astra PR 설명: 요약, 레인 파일 목록, 훅 목록(파일·표지), "병합 시 반영" 위치, 테스트 결과, 겹치는 브랜치.
- 병합 흐름
  1. Fable ultracode 적대적 리뷰를 받는다(Unreal·게임성에 영향이 있으면 필수). 결과는 PR 리뷰 코멘트로 남긴다.
  2. 확정 결함은 Astra가 자기 브랜치에서 고친다. 사용자가 지시하면 Fable이 직접 고친다.
  3. 사용자가 승인한다.
  4. Astra가 push를 멈춘 것을 확인한다. 병합 세션이 Astra 브랜치에 **마지막 커밋 하나**(`WP-NN: 병합 시 반영 (Fable)`)를 더한다. 이 커밋은 리뷰 요약을 WP 문서 "리뷰" 절에, "병합 시 반영" 문안을 STATUS·DECISIONS·ROADMAP·DEVELOPMENT-PLAN에 옮긴다. Claude가 Astra 브랜치와 레인 파일을 고치는 유일한 예외다.
  5. merge commit으로 병합한다. PC 검증은 병합 뒤 🟡 상태에서 한다(§7.4).
- 스택 PR(앞 단계 PR 위에 쌓은 PR)은 앞 단계 브랜치를 base로 연다. 앞 PR부터 병합한다. 앞 PR이 병합되면 base를 `main`으로 바꾸고 `git merge origin/main`을 한다.
- 리뷰 세션 프롬프트 템플릿:
```
당신은 Golmok의 Astra PR 리뷰·병합 세션이다(Fable 5.1 ultracode). CLAUDE.md, DEVELOPMENT-PLAN §7.4·§7.6,
AGENTS.md, 브랜치 astra/<…>의 WP 문서와 diff를 읽는다. 레인·훅 규칙 위반, 정확성, 게임 품질, 라이선스를
적대적으로 검증하고 결과를 PR 리뷰 코멘트로 남긴다. 확정 결함은 Astra에게 돌려보낸다(사용자가 지시하면 직접 고친다).
사용자 승인 뒤, Astra가 push를 멈춘 것을 확인하고 Astra 브랜치에 마지막 커밋 `WP-NN: 병합 시 반영 (Fable)`을 더한다.
이 커밋으로 리뷰 요약을 WP 문서 "리뷰" 절에, "병합 시 반영" 문안을 STATUS·DECISIONS·ROADMAP·DEVELOPMENT-PLAN에 옮긴다.
그다음 merge commit으로 병합한다.
```

---

## 8. 리스크와 대응

| # | 리스크 | 영향 | 대응 | 트리거 |
|---|---|---|---|---|
| R1 | 클라우드에서 쓴 UE C++가 5.8 API와 안 맞음 | 빌드 실패 | 보수적 API만 사용, PC 검증 런북, PC 세션이 수정 권한 | 빌드 에러 |
| R2 | 사용자 PC 사양(RTX 5060 8GB)으로 Postshot 최고 품질 불가 | 스파이크 지연 | AWS g6e 대안(D-006), GPU 업그레이드 결정 | Postshot OOM |
| R3 | 촬영 지연(날씨·시간) | 핵심 경로 지연 | 클라우드 트랙을 먼저 끝내 대기 시간 최소화. 리허설로 재촬영 방지 | C-02 미완 |
| R4 | XGRIDS 배포 라이선스 불명 | D-010 (c) 채택 불가 | 문의(D-009), 대안 Volinga, 최악은 (a) 메시 단독 | 회신 없음 |
| R5 | 메시 경로 텍스처에 구운 조명 → Lumen 부자연 | 품질 | 흐린 날 촬영, delight 도구 평가(스파이크) | 채점 저조 |
| R6 | 홈 Zone 실내 동의 실패 | M6 지연 | 후보 3곳 접촉, 조건(크레딧 표기) 제시 | 거절 |
| R7 | Git LFS 용량·대역폭(10GiB) 초과 | 비용 | 게임용 파생물만 LFS, 대용량은 저장소 밖 | 경고 메일 |
| R8 | 법률(보안시설·초상권·저작권) | 공개 불가 | 비공개 MVP, 05 문서 자문 항목, 공개 전 자문(D-009) | 공개 결정 시 |
| R9 | Opus 세션 실패·중단·요금 한도 | 일정 | 재시작 프로토콜(§7.4), STATUS 인계 | 세션 실패 |

---

## 9. 일정 추정 (사용자 가용 시간에 따라 변동)

| 주차 | 클라우드 트랙 | PC·사용자 트랙 |
|---|---|---|
| 1주 | WP-01~03 | V-01 셋업, C-01 리허설, C-03 데이터 다운로드, C-04 업그레이드 결정 |
| 2주 | WP-04~05 | V-02 베이스맵, C-02 첫 골목 촬영 |
| 3주 | WP-06~07 | V-03/V-04 검증, RealityScan·Postshot 첫 처리 |
| 4~5주 | (수정 대응) | V-05 스파이크 1.1 → **D-010** |
| 6~7주 | 통합 지원 코드 | V-06 골목 Zone 통합, 홈 Zone 확정, C-05 실내 동의·촬영 |
| 8주 | | 실내 Zone, 폴리시, MVP 완료(M7), 회고 |

클라우드 트랙만 보면 약 7세션(1~3시간씩)이라 2~3일 안에 끝날 수 있다. 전체 일정은 촬영과 PC 검증이 정한다.

---

## 10. Phase 2·3 개요

**Phase 2 — 확장 (MVP 회고 후 상세 계획)**
- 서버 자동화 파이프라인: COLMAP 4.2 + gsplat(D-002 준수), 충돌 메시 자동화, 정합·검수 자동 지표 → `pipeline/` (ARCHITECTURE §5). RunPod(Linux) 또는 국내 클라우드.
- Zone 백로그 일괄 처리(C-02에서 쌓인 골목들), Zone Index 서빙(정적 JSON → 필요 시 PostGIS API).
- 게임 기능(D-013~D-017 **승인** 2026-09-25): 포토 모드 확장(시간대 슬라이더·LUT·사진첩), Zone 지도·이동 + 세이브(WP-15), 날씨 비(WP-16), 현장 녹음·Zone별 소리(WP-17). 최소판·기본판(WP-12·13)은 Phase 1 1.6 선택 항목.
- 크라우드 촬영 앱(ARKit 포즈, 촬영 표시, 지오펜스), 업로드·검수 도구, 동의·신고 관리.
- 모바일 재평가.

**Phase 3 — 공개**
- 법률 자문 6항목(05 문서) 일괄, 약관·개인정보처리방침, 위치기반서비스사업 신고, 보안성 검토(제35조의6, 2026-12-03 시행).
- 랜드마크 블랙리스트·옵트아웃 레지스트리, 실내 동의 재취득(변호사 검토 양식).
- 국내 리전 호스팅(D-007), 배포 채널 결정, 공개 베타.

---

## 11. 사용자 결정·행동 대기 목록 (2026-09-24 기준)

| # | 항목 | 어디에 기록 |
|---|---|---|
| 1 | PR #1 병합(merge commit 권장) → 이 PR 리뷰 | GitHub |
| 2 | PC 업그레이드 여부(GPU → 저장장치 → RAM) | D-006 |
| 3 | 홈 Zone 선택(첫 촬영 후) | D-008 |
| 4 | Postshot Studio 구독, XGRIDS 문의 발송 | D-005, D-009 |
| 5 | S-Map 문의 발송 | 1.0e |
| 6 | ~~MVP 이후 게임 기능 우선순위~~ → **2026-09-25 D-013~D-017 전부 승인, 권장 우선순위대로**(WP-12 → 13 → 14 → 15 → 16 → 17, §5.1). 남은 결정: 사운드 라이브러리 유료 구매 여부(WP-13이 후보·가격을 정리한 뒤) | D-013~D-017 (승인) |
| 7 | 실내 동의 후보 가게 접촉 | C-05 |
| 8 | 애니메이션: GASP 라이선스 원문 확인(Fab 리스팅·Fab EULA·UE EULA — 클라우드에서 403) → V-08 평가 뒤 3안 중 채택 | `runbooks/pc-verify-animation.md` §0·§8, D-002 |
| 9 | night 프리셋 look-dev 조합 선택(D-010 뒤 폴리시) | `design/lighting-night-lookdev.md` |
| 10 | D-018 ①(캐릭터 제작 가설·18a) 승인. **② 대기**: V-08/V-12 뒤 최종 룩/명칭·외주 예산/권리 계약·비공개 저장소·필요 라이선스/출시 표시. 지출은② 이후 | [D-018](DECISIONS.md), [WP-18](plan/WP-18-characters.md) |
