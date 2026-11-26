# WP-20 — Mac 단독 개발 환경 전환 (D-022)

상태: 🔵 진행 중(2026-11-27) · 담당: Opus 5.5 ultracode(오케스트레이터) · 의존: D-022 · 검증: V-19(`runbooks/mac-setup.md`)

## 목표
소유자 지시(2026-11-27)에 따라 Windows PC 없이 이 Mac(Apple M5 Max·128 GB·macOS 27.2·arm64)만으로 개발·빌드·검증을 끝낼 수 있게 한다([D-022](../DECISIONS.md)). Windows 파일(`tools/ue/*.ps1`, `pc-*` 런북, ini의 Windows 절)은 이력이자 되돌리기 경로라 지우지 않는다. Mac 쪽을 **더한다**. UE가 아직 설치되지 않았으므로 UE 쪽은 "코드 완료·Mac 검증 대기"까지 만들고, 엔진 경로·플래그 중 확인하지 못한 값은 [미확인]으로 적어 V-19 런북에서 확인한다.

## 분할 근거 (오케스트레이터 결정, D-019, 2026-11-27)
- **20a(이 세션)**: UE 설치 없이 할 수 있는 것 전부다. 기반 도구 설치(uv·Python·git-lfs·gh), CI 검사의 Mac 통과, `tools/ue/*.sh`, 테스트와 저장소 검사의 Mac 대응, 공유 문서 갱신, V-19 런북.
- **V-19(로컬 Mac 세션)**: 소유자 항목(Xcode 라이선스, Epic 로그인·UE 설치, gh 로그인) 뒤에 첫 빌드·자동화·패키지를 확인한다. 런북 [mac-setup.md](../runbooks/mac-setup.md).
- **각 카드의 Mac 재설계**(입력 드라이버·화면 녹화·GPU 측정·패키지 녹음): V-19 통과 뒤 카드마다 한다(런북 §6). 이 WP에서는 대응표와 후보만 적는다.
- **재구성 파이프라인**: Mac에서 지금 도구(RealityScan·Postshot·LCC4Unreal)가 돌지 않는다. 대체는 스택 변경·지출이라 소유자 결정(D-019 ①·⑤)이다. 이 WP는 선택지와 스파이크 순서만 낸다.

## 배경(코드에서 확인할 것)
- `tools/ue/*.ps1`: `common.ps1`의 `UE_ROOT` 기본값이 `C:\Program Files\Epic Games\UE_5.8`이고 `Build.bat`·`RunUAT.bat`·`UnrealEditor-Cmd.exe`를 `Win64`로 부른다. `test.ps1`은 `index.json` 상태 열로 판정하고 실패 > 0 또는 성공 = 0이면 실패한다. `package.ps1`은 `GOLMOK_PKG_DIR`(C-07)을 읽는다. `add-gasp.ps1`은 단계별 JSON 작업 파일로 `gasp_import.py`를 헤드리스로 돌린다.
- (WP-20 전) `Golmok.uproject`는 `"TargetPlatforms": ["Windows"]`(WP-20에서 `"Mac"` 추가), `Config/DefaultEngine.ini`는 Windows 절(DX12 SM5/SM6)만 있다. C++ 소스에는 Windows 전용 코드가 없다(감사, 런북 §4 체크리스트).
- 열린 PC 카드: V-16·V-17·V-18·V-12·V-08b·V-15·V-05·V-01 §3. 전부 Windows 도구(SendInput 드라이버, ffmpeg `ddagrab`+NVENC, GPU-Z, WASAPI loopback, `setx`, 방화벽)를 쓴다.
- PC 기준선(RTX 5060 8 GB, 1080p, DX12 SM6)은 Mac과 비교할 수 없다.
- (WP-20 전) `spike_runner`는 `run_game_perf.ps1`과 `Win64/UnrealEditor.exe`를 만든다(WP-20에서 win32가 아니면 `run_game_perf.sh`). `privacy/detector.py`는 CUDA가 없으면 CPU를 고른다.

## 설계 (확정, 2026-11-27, Opus)

### 1. 설치 목록·소유자 항목
- sudo·Homebrew 없이 되는 것은 Claude 세션이 설치한다: uv, uv 관리 Python 3.12, git-lfs·gh 릴리스 바이너리(`~/.local/bin`), tools venv, LFS pull, Epic Games Launcher 앱 복사.
- 소유자 항목(D-019 ②: 약관·계정·로그인): Apple ID와 Xcode 설치, `sudo xcodebuild -license accept`, Xcode 첫 실행 구성요소(Metal Toolchain), Epic 로그인·UE EULA·UE 5.8.x 설치, `gh auth login`, (선택) Homebrew, EgoBlur 모델 라이선스, Fab GASP 재다운로드와 D-021 재확인. 목록과 이유는 런북 §1.

### 2. UE 버전
- Launcher의 5.8.x 최신(5.8.4 이상)을 쓴다. 5.8.3 + Xcode 27은 Mac 게임 타깃 빌드가 실패한다(UE-396802, 5.8.4에서 수정). 엔진 패치 수준 변경이므로 D-022에 기록한다. 근거와 출처는 런북 §2.
- macOS 27·Xcode 27은 Epic 검증 범위(macOS 14.5+, Xcode 26.0+, 26.4 불가) 밖이다. 막히면 Xcode 26.6 + `DEVELOPER_DIR` 우회를 쓴다.

### 3. UE 스크립트 Mac판 (`tools/ue/*.sh`, Claude 레인)
- `.ps1`과 1:1로 짝을 둔다: `common.sh`, `build.sh [Config]`, `generate-project-files.sh`, `open-editor.sh`, `test.sh [--filter F] [--setup-dev-level] [--rhi]`, `package.sh [Config] [--out-dir DIR]`, `add-mannequin.sh`, `add-gasp.sh --gasp-project/--verify/--force/--local-files/--manifest`.
- `UE_ROOT` 기본값 `"/Users/Shared/Epic Games/UE_5.8"`(공백 — 전부 따옴표). `set -euo pipefail`. 판정 규칙(`test.sh`의 상태 열, `package.sh`의 `GOLMOK_PKG_DIR`, `add-gasp.sh`의 종료 코드)은 `.ps1`과 같다.
- `.ps1`은 고치지 않는다.

### 4. 런북 대응표
- 새 런북 V-19 [mac-setup.md](../runbooks/mac-setup.md)에 모은다: 이미 한 것, 소유자 항목, 버전 조합, `.ps1`→`.sh`와 Windows 관습→Mac 대응표, 첫 빌드 절차, 로컬 상태, 카드별 계획, 재구성 선택지, [미확인] 표.
- 기존 `pc-verify-*.md`는 이름을 바꾸지 않는다(이력·링크·Astra 레인 런북). 각 카드는 Mac에서 돌 때 대응표를 따른다.
- GUI 잠금 파일은 Mac에서 `"$TMPDIR/claude/gui-foreground.lock"`이다(AGENTS.md와 같은 경로. 한 줄 형식 `<세션> <목적> <ISO 시각>`과 규칙은 Windows와 같다).
- 성능 판정은 같은 세션 기준 측정의 상대값으로 한다. RTX 5060 "저사양 하한 측정기" 자리는 비어 있고 소유자 항목이다.

### 5. 재구성 파이프라인
- RealityScan(Windows, 생성에 CUDA 필요)·Postshot(Windows + NVIDIA)·LCC4Unreal(Windows·Linux, DX/Vulkan)은 Mac에서 쓸 수 없다.
- 후보: COLMAP(BSD) SfM, Brush(Apache-2.0) 스플랫, Apple Object Capture 메시, Metashape(유료), msplat(Apache-2.0, 소스 감사 필요), 또는 클라우드 Windows GPU(AWS g6e, 지출). 금지: gsplat-mps(AGPL)·OpenSplat·OpenMVS·Inria 3DGS.
- 고르는 것은 소유자다. 권하는 스파이크 순서는 런북 §7.

### 6. 하지 않는 것
- Windows 파일 삭제·이름 변경, `pc/*` 브랜치 정리.
- 소유자 대신 약관 동의·로그인·결제.
- 배포 타깃(D-003 "고사양 PC(Windows)") 변경. Mac에서 Win64 패키지를 만들 수 있는지는 별도 문제다 [미확인].
- 재구성 스택 선택.
- Astra 레인 파일 수정.

## 산출물
- `tools/ue/*.sh`(§3)
- Mac 대응 테스트·저장소 검사 변경(핫스팟은 `[WP-20 hook]` 블록)
- 공유 문서 갱신(CLAUDE.md, AGENTS.md, DECISIONS D-022, DEVELOPMENT-PLAN, STATUS, ROADMAP, README, tools/README)
- 런북 [mac-setup.md](../runbooks/mac-setup.md)(V-19)
- 이 문서

## 완료 기준
- 이 Mac에서 `ruff check .`·`ruff format --check .`·`pytest -q`·`python scripts/check_repo.py`가 통과한다(Xcode 라이선스 동의 전에는 `DEVELOPER_DIR=/Library/Developer/CommandLineTools`로).
- `tools/ue/*.sh`가 `bash -n`을 통과하고, UE 없이 실행하면 엔진 경로 오류를 내고 종료 코드 1로 끝난다.
- V-19 런북이 소유자 항목·첫 빌드 절차·카드별 계획·[미확인] 표를 담는다.
- UE 쪽 완료(🟢)는 V-19 §4 통과 뒤다.

## 주의
- 엔진이 없어 `.sh`의 엔진 경로·플래그는 실행해 보지 못했다. 런북 §8 표가 확인 목록이다.
- Xcode가 설치되기 시작하면 라이선스 동의 전까지 `/usr/bin/git`·`g++`·`clang++`가 종료 코드 69로 멈춘다(2026-11-27 관찰). 그동안은 `export DEVELOPER_DIR=/Library/Developer/CommandLineTools`로 Command Line Tools를 쓰면 git과 CI 검사가 돈다(런북 §0). 동의는 UE 빌드에만 필요하다.
- Astra 레인 파일에서 Mac 컴파일 경고나 실패가 나면 고치지 않고 이슈 #30·PR로 알린다.
- 핫스팟(`.gitattributes`, `.gitignore`, `check_repo.py`, CI, `Config/Default*.ini`, `.uproject`)은 별도 커밋의 표시된 훅 블록으로만 고친다.

## 결과

### 20a (2026-11-27, 오케스트레이터 세션 Fable 5.2 · 서브에이전트 Opus 5.5 ultracode, 브랜치 `claude/wp20-mac-dev-env`) — 🔵 진행 중
- **모델 기록**: 이 세션의 오케스트레이터는 소유자가 그렇게 시작해서 Fable 5.2로 돌았다. 구현·검증·문서 서브에이전트는 전부 Opus 5.5다(D-020). 이후 세션은 Opus 5.5로 시작한다.
- 기반 도구 설치와 CI 검사 결과는 [mac-setup.md](../runbooks/mac-setup.md) §0에 적었다.

| 항목 | 결과 | 메모 |
|---|---|---|
| 기반 도구(uv·Python 3.12·git-lfs·gh) | 완료 | sudo·Homebrew 없음 |
| tools venv·LFS pull | 완료 | |
| CI 검사(Mac) | 통과 | `DEVELOPER_DIR=/Library/Developer/CommandLineTools`로 ruff 두 검사 통과, `pytest -q` 1906 통과·3 건너뜀, `check_repo.py` OK(2026-11-27). 처음 실패한 arm64 C++ 교차검증 3건은 고쳤다 |
| `tools/ue/*.sh` | | |
| 공유 문서·D-022 | | |
| V-19 런북 | 작성 | `runbooks/mac-setup.md` |
| V-19 §4 첫 빌드 | | UE 설치 대기(소유자 항목) |
