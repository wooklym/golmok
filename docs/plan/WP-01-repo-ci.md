# WP-01 — 저장소 기반·CI

상태: 🟢 완료 · 담당: 클라우드 Claude 세션 · 의존: 없음 · 검증: G1(클라우드)

## 목표
이후 모든 WP가 같은 품질 기준으로 검사받도록 CI와 린트, 설정 파일 검증을 만든다. 작고 확실하게 끝내는 것이 목적이다(오케스트레이션 첫 세션).

## 산출물
1. `.github/workflows/ci.yml`
   - 트리거: push, pull_request(모든 브랜치).
   - job `python`: matrix `ubuntu-latest` × Python 3.11/3.12, `windows-latest` × 3.12(사용자 PC와 같은 OS에서 경로·인코딩 문제를 잡는다).
     `cd tools && pip install -e ".[basemap,dev]"` → `ruff check .` → `ruff format --check .` → `pytest -q`.
     rasterio·shapely 등 휠 설치가 Windows에서 실패하면 그 잡만 `basemap` extra를 빼고 관련 테스트를 skip 마커로 처리한다(테스트에 `pytest.importorskip` 사용).
   - job `repo-check`: `python tools/scripts/check_repo.py` 실행.
   - job `tiles-validate`(선택, 실패해도 전체 실패 아님 `continue-on-error`): `npx 3d-tiles-validator`로 합성 베이스맵 출력 검증. 이미 `tools/tests/test_basemap.py`가 합성 데이터를 만들므로, 테스트에서 `--out`을 남기는 방식이든 별도 스크립트든 간단한 쪽으로.
2. `tools/scripts/check_repo.py` (표준 라이브러리만)
   - `unreal/Golmok/Golmok.uproject` JSON 파싱, `EngineAssociation == "5.8"` 확인.
   - `unreal/Golmok/Config/*.ini` 를 `configparser`(strict=False, `+`/`-` 접두 키 허용)로 파싱.
   - `unreal/Golmok/Config/Golmok/**/*.json`, `docs/**/*.json`(있으면) 파싱.
   - `docs/**/*.md`, `README.md`, `CLAUDE.md`의 **상대 링크**가 존재하는 파일을 가리키는지 검사(외부 URL은 제외).
   - `.gitattributes`에 `*.uasset`, `*.umap`이 LFS로 지정돼 있는지 확인.
   - 실패 항목을 모두 출력하고 exit 1.
3. `tools/pyproject.toml`: `[tool.ruff]`(line-length 110, target py311, select E,F,I,B,UP; per-file-ignores 필요 최소), `dev` extra에 `ruff` 추가. 기존 코드의 린트 위반은 **동작을 바꾸지 않는 범위**에서 고친다(자동 수정 위주). 큰 리팩터링 금지.
4. `.editorconfig`(utf-8, LF, ps1은 CRLF, 파이썬 4칸).
5. `tools/tests/test_check_repo.py`: check_repo의 링크 검사·ini 파싱을 임시 디렉터리로 테스트.
6. 문서: 루트 `README.md`에 CI 배지와 `docs/DEVELOPMENT-PLAN.md` 링크, `tools/README.md`에 "검사 실행" 절(`ruff check .`, `pytest`, `python scripts/check_repo.py`).

## 완료 기준
- 로컬에서 `cd tools && ruff check . && ruff format --check . && pytest -q && python scripts/check_repo.py` 전부 통과.
- 워크플로 YAML이 유효하고(`python -c "import yaml"`로 파싱), 브랜치 push 후 Actions가 초록. Actions 결과는 세션이 GitHub 도구로 확인한다(가능하면). 확인이 안 되면 STATUS에 "Actions 확인 필요"로 남긴다.
- `docs/plan/STATUS.md` WP-01 🟢, 세션 로그 추가.

## 주의
- `ruff format`이 기존 파일을 대량 수정하면 diff가 커진다. 형식 변경 커밋은 **별도 커밋**(`WP-01: ruff format`)으로 분리한다.
- Windows 잡에서 `golmok-blur` 관련 테스트는 torch 없이도 통과해야 한다(이미 그렇게 돼 있는지 확인).

## 결과
세션: session_01QwUxcoWCFmtiJhq3ZWByEJ (2026-09-24)

**한 일**
- `.github/workflows/ci.yml`: push·pull_request(모든 브랜치)·수동 실행. job `python`(ubuntu 3.11/3.12, windows 3.12; `pip install -e ".[basemap,dev]"` → `ruff check` → `ruff format --check` → `pytest -q`), `repo-check`, `tiles-validate`(`continue-on-error`). 전역 `PYTHONUTF8=1`(Windows 콘솔 한글 출력).
  - Windows에서도 `basemap` extra(rasterio·shapely·pyproj) 휠 설치가 성공해 extra를 빼는 분기는 필요 없었다. torch는 설치하지 않으며 `test_egoblur_wrapper.py`만 `importorskip`으로 skip된다(블러 테스트는 torch 없이 통과).
  - `tiles-validate`: `GOLMOK_BASEMAP_OUT` 환경변수를 주면 `tests/test_basemap.py`가 합성 베이스맵을 그 폴더에 남기고, `npx 3d-tiles-validator@0.6.1 --tilesetFile …`의 출력에서 `"numErrors": 0`을 확인한다(검증기는 이슈가 있어도 exit 0이라 grep으로 판정).
- `tools/scripts/check_repo.py`(표준 라이브러리만): uproject(`EngineAssociation == "5.8"`), `Config/*.ini`(UE식 중복 키·`+ - . !` 접두 키, 보간 없음), `Config/Golmok/**/*.json`·`docs/**/*.json`, `docs/**/*.md`·`README.md`·`CLAUDE.md`·`tools/README.md`의 상대 링크(코드 블록·인라인 코드 제외, 참조형 링크 포함, `%` 인코딩·`#앵커`·`/`루트 상대 처리), `.gitattributes`의 `*.uasset`/`*.umap` LFS. 실패를 모두 출력하고 exit 1.
- `tools/tests/test_check_repo.py` 8개(임시 디렉터리 합성 저장소).
- `tools/pyproject.toml`: `[tool.ruff]`(line-length 110, py311, E/F/I/B/UP, per-file-ignores 없음), `dev`에 `ruff>=0.6`, `requires-python >=3.11`(target py311·§7.5와 일치, `datetime.UTC` 사용).
- 린트 수정(동작 불변): import 정렬, `timezone.utc`→`UTC`, `zip(strict=…)`(길이가 같은 곳은 True, SHP 레코드는 기존 동작 유지 위해 False), 긴 줄 분리, 미사용 루프 변수 `_dec`. 형식 변경은 별도 커밋 `WP-01: ruff format`.
- `.editorconfig`(utf-8, LF, ps1/bat CRLF, 파이썬 4칸, C++/ini 탭), 루트 `README.md` CI 배지, `tools/README.md` "검사 실행" 절, `DECISIONS.md` D-002에 개발 전용 도구 라이선스(ruff MIT, 3d-tiles-validator Apache-2.0, 원문 확인) 기록.

**테스트 로그 요약**
- 로컬(Python 3.11.15, ruff 0.16.8): `ruff check .` All checks passed · `ruff format --check .` 25 files already formatted · `pytest -q` 36 passed, 1 skipped(torch) · `python scripts/check_repo.py` OK.
- 로컬 `3d-tiles-validator@0.6.1`: numErrors 0, numWarnings 0, numInfos 18(TEXCOORD_1 "may be unused" — 파사드 머티리얼용 커스텀 UV라 정상).
- GitHub Actions(커밋 ec5ecd3): push 실행 36007213938, pull_request 실행 36007216880 모두 success. 잡 5개(python ×3, repo-check, tiles-validate) 전부 success, Windows 36 passed 1 skipped.

**남은 것 / 메모**
- Actions가 `actions/checkout@v4`·`setup-python@v5`·`setup-node@v4`의 Node 20 사용 경고를 낸다(현재 Node 24로 강제 실행, 동작 문제 없음). 새 메이저가 나오면 올린다.
- 린트 범위는 `tools/`만이다. `unreal/Golmok/Content/Python`은 WP-06에서 ruff 대상에 넣을지 정한다.
