# 진행 상태 보드 (plan/STATUS)

갱신 규칙: 각 세션이 시작·종료 시 자기 행을 고친다. 상태 기호:
⚪ 대기 · 🔵 진행 중 · 🟡 코드 완료·PC 검증 대기 · 🟢 완료 · 🔴 막힘 · ⏸ 보류

마지막 갱신: 2026-09-24 (WP-02 세션)

## 트랙 1A — 클라우드 코드 (순차)

| WP | 이름 | 상태 | 세션 | 인계 메모 |
|---|---|---|---|---|
| WP-01 | 저장소 기반·CI | 🟢 완료 | session_01QwUxcoWCFmtiJhq3ZWByEJ (Opus) | CI 초록(ubuntu 3.11/3.12, windows 3.12, repo-check, tiles-validate). 커밋 전 `cd tools && ruff check . && ruff format --check . && pytest -q && python scripts/check_repo.py` |
| WP-02 | Zone 데이터 모델·CLI `golmok-zone` | 🟢 완료 | session_014zvy99LzAuVhnHYFtUYfVz (Opus) | 스펙 `docs/spec/zone-manifest.md`(필드·좌표·UE 매핑·수치 예제 표). transform은 **row-major**, UE Yaw = −yaw_deg, ENU→UE `diag(100,−100,100)`. 픽스처 `tools/tests/fixtures/zones/z_synthetic_001/v1/`(WP-04가 복사). 베이스맵 origin 높이는 `--geoid-offset` 없으면 정표고(WP-07 주의) |
| WP-03 | 재구성 후처리 `golmok-mesh` / `golmok-splat` | ⚪ 대기 | | |
| WP-04 | UE C++ 1: Geo·Zone | ⚪ 대기 | | |
| WP-05 | UE C++ 2: 포털·조명·디버그 | ⚪ 대기 | | |
| WP-06 | UE Python 에디터 자동화 2차 | ⚪ 대기 | | |
| WP-07 | 정합·검수 `golmok-align` | ⚪ 대기 | | |
| WP-08 | (선택) 웹 검수 뷰어 | 🟢 완료 | session_01Cgm7f6oD6xSMpZ5jszj8Xi (Fable 5.1) | `golmok-viewer`(CesiumJS 1.145, ion 없음) + `tools/viewer` + Playwright 스모크(`npm test`, 합성 베이스맵 18타일). Zone manifest 오버레이(footprint·청크 bbox·포털·blockers, `?zone=…/manifest.json`) 포함. 충돌 메시 표시는 WP-03 산출물 나오면 추가 |

## 트랙 1B — PC 검증 (PC Claude 세션)

| V | 내용 | 상태 | 메모 |
|---|---|---|---|
| V-01 | PC 셋업·L_Dev·리허설 점검 (`runbooks/pc-setup.md` §0~4) | ⚪ 대기 | 사용자 설치 필요 |
| V-02 | 베이스맵 실데이터 (`pc-setup.md` §5) | ⚪ 대기 | C-03 필요 |
| V-03 | WP-04/05 빌드·PIE 검증 | ⚪ 대기 | M1 이후 |
| V-04 | WP-06 에디터 Python 검증 | ⚪ 대기 | |
| V-05 | 재구성·후처리·스파이크 1.1 | ⚪ 대기 | C-02 필요 |
| V-06 | Zone 통합·튜닝·패키징 | ⚪ 대기 | D-010 이후 |

## 트랙 1C — 사용자

| C | 내용 | 상태 |
|---|---|---|
| C-01 | 아이폰 리허설 | ⚪ |
| C-02 | 골목 촬영(홈 Zone 후보 포함) | ⚪ |
| C-03 | 베이스맵 데이터 다운로드 | ⚪ |
| C-04 | PC 업그레이드 결정, Postshot Studio, XGRIDS 문의 | ⚪ |
| C-05 | 실내 동의·촬영 | ⚪ |
| C-06 | S-Map 문의 발송 | ⚪ |

## 결정 필요 (세션이 발견한 것)
- (없음)

## 세션 로그
| 날짜 | 세션 | 모델 | 대상 | 결과 |
|---|---|---|---|---|
| 2026-09-24 | session_01NM6uvZaVMgq5SUSaduHD1Z | Fable 5.1 | 개발 전체 과정 설계, WP 문서, 오케스트레이션 | PR #2 |
| 2026-09-24 | session_01QwUxcoWCFmtiJhq3ZWByEJ | Opus | WP-01 | 🟢 CI·check_repo·ruff. Actions 실행 36007213938/36007216880 success |
| 2026-09-24 | session_014zvy99LzAuVhnHYFtUYfVz | Opus | WP-02 | 🟢 zone 스펙·스키마·`golmok-zone`·테스트 80개(전체 116 passed) |
| 2026-09-24 | session_01Cgm7f6oD6xSMpZ5jszj8Xi | Fable 5.1 | PR #1·#2 병합(main), WP-08 검수 뷰어, PC 작업 카드 2건 | PR #3 (`claude/golmok-phase-0-research-4kloq6`). 전체 119 passed |
