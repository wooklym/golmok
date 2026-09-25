# Golmok 문서

| 문서 | 내용 |
|---|---|
| [DEVELOPMENT-PLAN.md](DEVELOPMENT-PLAN.md) | **개발 전체 과정 설계**: 비전·마일스톤·실행 주체·작업 패키지(WP)·검증 게이트·세션 프로토콜·리스크·일정 |
| [plan/STATUS.md](plan/STATUS.md) | 진행 상태 보드(WP·PC 검증·사용자 작업). 세션마다 갱신 |
| [plan/WP-01…08](plan/) | 작업 패키지 상세 스펙(산출물·완료 기준·주의·결과) |
| [ROADMAP.md](ROADMAP.md) | 진행 상황과 다음 단계 |
| [DECISIONS.md](DECISIONS.md) | 결정 기록(D-001~D-012 승인. 남은 확인: PC 업그레이드 여부, 홈 Zone 선택) |
| [spec/zone-manifest.md](spec/zone-manifest.md) | **Zone 데이터 계약**: manifest·blockers·Zone Index JSON Schema, 좌표 규약(ENU m ↔ UE cm), UE 매핑 규약, 변환 수치 예제 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 전체 아키텍처: 촬영 → 파이프라인 → 지리 타일 저장 → 클라이언트 스트리밍, 구역 교체 규칙 |
| [research/01-basemap-data.md](research/01-basemap-data.md) | 서울 3D 베이스맵 데이터 소스 비교(S-Map, V-World, OSM, Google, Cesium 등) |
| [research/02-reconstruction-pipeline.md](research/02-reconstruction-pipeline.md) | 포토그래메트리·3DGS 파이프라인, 라이선스, 시각·충돌 분리 설계 |
| [research/03-engine-platform.md](research/03-engine-platform.md) | Unity, Unreal, Godot, 웹 엔진 비교와 추천 |
| [research/05-legal-policy.md](research/05-legal-policy.md) | 개인정보, 초상권, 사유지, 저작권, 공간정보 보안 규제 |
| [research/06-pilot-area.md](research/06-pilot-area.md) | 파일럿 지역 비교(성수 연무장길 vs 연남동) |
| [research/07-ue5-toolchain.md](research/07-ue5-toolchain.md) | UE5 툴체인 검증: 버전, PC 사양, RealityScan, Postshot, splat 플러그인, 클라우드 |
| [capture/01-alley-capture-guide.md](capture/01-alley-capture-guide.md) | 촬영 가이드 #1: 골목 |
| [outreach/smap-inquiry-draft.md](outreach/smap-inquiry-draft.md) | 서울시 S-Map 문의 초안 |
| [research/08-spike-results.md](research/08-spike-results.md) | 스파이크 1.1 결과(템플릿, 측정 전) |
| [capture/02-interior-capture-guide.md](capture/02-interior-capture-guide.md) | 촬영 가이드 #2: 실내 |
| [outreach/interior-consent-form-draft.md](outreach/interior-consent-form-draft.md) | 실내 촬영·게시 동의서 초안(변호사 검토 전) |
| [captures/INDEX.md](captures/INDEX.md) | 촬영 목록(Zone 백로그) |
| [runbooks/recon-postprocess.md](runbooks/recon-postprocess.md) | RealityScan·Postshot 결과 → Zone 폴더(청크·충돌·blocker·splat 3D Tiles) 후처리 절차 |
| [runbooks/pc-setup.md](runbooks/pc-setup.md) | 사용자 PC 셋업·검증 런북(로컬 Claude 세션용) |
| [runbooks/pc-verify-wp04.md](runbooks/pc-verify-wp04.md) · [pc-verify-wp05.md](runbooks/pc-verify-wp05.md) · `pc-verify-wp06.md`(작성 중) | PC 검증 런북(V-03·V-04): UE C++ Geo·Zone / 포털·조명·디버그 / 에디터 Python(합성 zone 임포트·실내·스파이크 리허설) |
| [runbooks/pc-spike.md](runbooks/pc-spike.md) | 스파이크 1.1 전체 절차(촬영 → 블러 → RealityScan → Postshot → 후처리 → UE 임포트 → 캡처·성능 → research/08 → D-010) |
| [runbooks/align.md](runbooks/align.md) | Zone 정합 `golmok-align` 런북(WP-07) |

과업 목록의 4번(전체 아키텍처)은 `ARCHITECTURE.md`로 따로 두었다.
모든 조사 문서는 사실마다 확인 수준([확인]/[2차]/[미확인])과 출처 URL을 적어 두었다.
