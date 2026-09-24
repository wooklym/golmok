# 진행 상태 보드 (plan/STATUS)

갱신 규칙: 각 세션이 시작·종료 시 자기 행을 고친다. 상태 기호:
⚪ 대기 · 🔵 진행 중 · 🟡 코드 완료·PC 검증 대기 · 🟢 완료 · 🔴 막힘 · ⏸ 보류

마지막 갱신: 2026-09-24 (WP-01 세션)

## 트랙 1A — 클라우드 코드 (순차)

| WP | 이름 | 상태 | 세션 | 인계 메모 |
|---|---|---|---|---|
| WP-01 | 저장소 기반·CI | 🟢 완료 | session_01QwUxcoWCFmtiJhq3ZWByEJ (Opus) | CI 초록(ubuntu 3.11/3.12, windows 3.12, repo-check, tiles-validate). 커밋 전 `cd tools && ruff check . && ruff format --check . && pytest -q && python scripts/check_repo.py` |
| WP-02 | Zone 데이터 모델·CLI `golmok-zone` | ⚪ 대기 | | |
| WP-03 | 재구성 후처리 `golmok-mesh` / `golmok-splat` | ⚪ 대기 | | |
| WP-04 | UE C++ 1: Geo·Zone | ⚪ 대기 | | |
| WP-05 | UE C++ 2: 포털·조명·디버그 | ⚪ 대기 | | |
| WP-06 | UE Python 에디터 자동화 2차 | ⚪ 대기 | | |
| WP-07 | 정합·검수 `golmok-align` | ⚪ 대기 | | |
| WP-08 | (선택) 웹 검수 뷰어 | ⏸ 보류 | | ROADMAP 1.6 "선택". 사용자가 켤 때 시작 |

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
