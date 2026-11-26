# 런북 V-19: Mac 단독 개발·검증 환경 셋업 (로컬 Claude 세션용, D-022·WP-20)

이 문서는 **소유자 Mac에서 도는 Claude Code 세션**이 따라가는 작업 지시서다. [pc-setup.md](pc-setup.md)(Windows PC, V-01)의 짝이다. 소유자는 2026-11-27에 Windows PC 대신 이 Mac을 **유일한** 개발·검증 머신으로 정했다(D-022, [DECISIONS](../DECISIONS.md)). Windows 파일(`tools/ue/*.ps1`, `pc-*` 런북, ini의 Windows 절)은 이력이자 되돌리기 경로라 그대로 둔다. Mac 쪽은 **더한다**.

- **운영 규칙**: D-019(되돌릴 수 없는 일만 소유자에게 묻는다)와 [pc-setup.md](pc-setup.md) "운영 규칙"을 따른다. 아래 §1이 이 Mac에서 소유자만 할 수 있는 일의 전체 목록이다.
- **모델**: 세션과 서브에이전트는 Opus 5.5다(D-020).
- **브랜치**: 검증 결과는 지금처럼 `pc/*` 브랜치에 커밋한다. 이 런북에서 "PC 카드"는 "로컬 검증 머신 카드"로 읽는다. 이름을 `mac/*`로 바꿀지는 D-022에서 정한다.
- **경로 표기**: 저장소 루트는 `~/projects/golmok`다. 엔진 루트 기본값은 `"/Users/Shared/Epic Games/UE_5.8"`이다. **공백이 있으므로 모든 명령에서 따옴표로 감싼다.** 다르면 `export UE_ROOT=…`로 바꾼다.
- [미확인] 표시는 UE 설치 전이라 확인하지 못한 값이다. 전부 §8 표에 모았다. 확인하면 §8의 "확인 결과" 칸과 본문을 같이 고친다.

## 머신 (2026-11-27 확인)
- Apple M5 Max, RAM 128 GB(통합 메모리), arm64
- macOS 27.2.1(빌드 26B131, `sw_vers`)
- 여유 공간 약 750 GB
- Windows PC 사양과 기준선은 [D-006](../DECISIONS.md)·[pc-setup.md](pc-setup.md)에 이력으로 남는다.

## 0. 이 Mac에서 이미 한 것 (2026-11-27, WP-20 세션)

| 항목 | 상태 | 확인 명령 |
|---|---|---|
| uv 0.13.10 | `~/.local/bin/uv`(sudo·Homebrew 없이 공식 설치 스크립트) | `~/.local/bin/uv --version` |
| Python 3.12.16 | uv가 관리(`uv python install 3.12`) | `tools/.venv/bin/python --version` |
| git-lfs 3.8.1 | `~/.local/bin/git-lfs`(darwin arm64 릴리스 바이너리) | `git lfs version` |
| gh 2.106.0 | `~/.local/bin/gh`(로그인 전) | `gh --version` |
| tools venv | `tools/.venv`(Python 3.12, CI와 같은 extras) | 아래 재현 명령 |
| LFS | `git lfs install` 뒤 `git lfs pull` 완료(`.uasset`/`.umap`/jpg가 포인터가 아님) | `git lfs ls-files \| head` |
| Epic Games Launcher | `/Applications/Epic Games Launcher.app`. 서명 "Developer ID Application: Epic Games International, S.a.r.l. (96DBZ92D3Y)", 공증됨 | `codesign -dv --verbose=2 "/Applications/Epic Games Launcher.app"`, `spctl -a -vv "/Applications/Epic Games Launcher.app"` |
| Xcode 27.2 | App Store 다운로드 시작(진행 중, `/Applications/Xcode.appdownload`) | `ls /Applications \| grep -i xcode` |
| Command Line Tools | `/Library/Developer/CommandLineTools`(Apple clang 21) | `xcode-select -p` |
| Unreal Engine | **미설치** | — |

**CI 검사(Mac에서 실행, 2026-11-27)**
- `ruff check .`·`ruff format --check .`·`python scripts/check_repo.py`: 통과
- `pytest -q`: 처음에는 1854 통과 + 실패 3이었다. 실패 3은 arm64에서만 나는 C++ 교차검증 수치 허용오차 문제였고 WP-20에서 고쳤다(결과는 [WP-20](../plan/WP-20-mac-dev-env.md) "결과").
- **Xcode 라이선스 전 우회(sudo 없음)**: Xcode 다운로드가 시작된 뒤로 `/usr/bin/git`·`/usr/bin/g++`·`clang++` 셈(shim)이 "You have not agreed to the Xcode license agreements"를 내고 종료 코드 69로 멈춘다. §1 #2 전에는 git과 pytest 앞에 **`export DEVELOPER_DIR=/Library/Developer/CommandLineTools`**를 준다. 셈이 이미 설치된 Command Line Tools를 쓰고, CLT에는 Xcode 라이선스 관문이 없다. 이 상태로 위 CI 검사 전부가 통과한다: `ruff check .`·`ruff format --check .` 통과, `pytest -q` **1906 통과·3 건너뜀**(80 s), `check_repo.py` "OK (uproject, ini, json, links, gitattributes, conflicts, gasp)"(2026-11-27, git 2.54.0 Apple Git-157). §1 #2 뒤에는 이 export가 필요 없다.

**재현 명령**(새 Mac이나 venv를 다시 만들 때)
```bash
# 셸 PATH (~/.zprofile에 한 번)
export PATH="$HOME/.local/bin:$PATH"

# uv·Python (sudo 불필요)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12

# git-lfs: https://github.com/git-lfs/git-lfs/releases 의 darwin-arm64 zip을 받아 git-lfs 바이너리를 ~/.local/bin에 둔다
git lfs install
cd ~/projects/golmok && git lfs pull

# tools venv와 CI 검사 (CLAUDE.md "Commands"와 같은 검사)
cd ~/projects/golmok/tools
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -e ".[basemap,zone,mesh,splat,align,dev]"
ruff check . && ruff format --check . && pytest -q && python scripts/check_repo.py
```
- 웹 뷰어 스모크(`cd tools/viewer && npm install && npm test`)는 Playwright Chromium 다운로드가 필요하다. 아직 돌리지 않았다.
- **커밋 정보**: 이 Mac의 Claude 세션은 `git -c user.name=Claude -c user.email=noreply@anthropic.com commit …`으로 커밋한다(pc-setup §0과 같다).

## 1. 소유자만 하는 일 (D-019)

D-019는 약관 동의·계정 가입·로그인·지출을 소유자 몫으로 둔다. 아래는 이 Mac에서 그 몫에 드는 일 전부다. 순서대로 하면 된다. 끝나면 Claude 세션에 "§1 n번 끝"이라고 알려 준다.

| # | 할 일 | 왜 소유자만 하나 | 끝난 뒤 Claude가 확인할 것 |
|---|---|---|---|
| 1 | **Apple ID로 App Store에서 Xcode 27.2 설치 마무리**(이미 시작함) | Apple 계정 로그인, App Store 약관(D-019 ②) | `ls /Applications/Xcode.app`, `xcodebuild -version` |
| 2 | 터미널에서 **`sudo xcodebuild -license accept`**, 이어서 `sudo xcode-select -s /Applications/Xcode.app/Contents/Developer` | Xcode·Apple SDK 라이선스 동의(②)와 관리자 암호. 동의 전에는 `/usr/bin/git`까지 "You have not agreed to the Xcode license agreements"를 내고 멈춘다(2026-11-27 관찰). 그동안 git·pytest는 §0의 `DEVELOPER_DIR` 우회로 돌린다. UE 빌드에는 동의가 필요하다 | `xcode-select -p`가 `/Applications/Xcode.app/Contents/Developer`, `git status`가 정상 |
| 3 | Xcode를 한 번 열어 **첫 실행 구성요소** 설치. Settings → Components에서 **Metal Toolchain**을 받는다(macOS 플랫폼만 있으면 된다. iOS 시뮬레이터는 필요 없다) | 첫 실행 동의 창과 Apple 다운로드 약관(②). Metal Toolchain이 따로 받는 구성요소라는 것은 검색 요약 수준이다 [미확인, §8 #3] | `xcrun -f metal`이 경로를 낸다 |
| 4 | **Epic Games Launcher 로그인 → UE EULA 동의 → UE 5.8.x 설치**(Launcher가 주는 5.8 최신, §2 결정). 설치 옵션은 기본값에 "Editor symbols for debugging"은 끈다. 설치 위치는 기본값(`/Users/Shared/Epic Games`)을 권한다 | Epic 계정 로그인과 엔진 EULA(②) | `ls "/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac"`, `Engine/Build/Build.version`의 `PatchVersion`이 4 이상 |
| 5 | **`gh auth login`**(GitHub.com → HTTPS → 브라우저) | GitHub 계정 로그인·자격 증명 저장(②) | `gh auth status`, `git push` 시험(작업 브랜치) |
| 6 | (선택) **Homebrew 설치**와 `brew install ffmpeg exiftool colmap` | Homebrew 설치 스크립트가 sudo를 요구한다. ffmpeg·exiftool은 V-01 §3·V-08b·V-17 캡처에, colmap은 §7 스파이크에 쓴다. 설치 자체는 무료다 | `ffmpeg -version`, `exiftool -ver`, `colmap -h` |
| 7 | **EgoBlur 모델 라이선스 동의**와 Gen1 모델 다운로드(https://www.projectaria.com/tools/egoblur) → `tools/models/ego_blur_face.jit`, `ego_blur_lp.jit` | 모델 라이선스 동의(②). Windows 때도 소유자 항목이었고 아직 하지 않았다 | 파일 두 개 존재, `golmok-blur --help` |
| 8 | **Fab에서 GASP(Game Animation Sample) 다시 받기**와 **D-021 라이선스 원문 재확인** | Fab 계정·EULA(②), D-021의 소유자 사실 확인이 아직 남아 있다. PC의 `C:\UE\GASP_58`을 그냥 복사해도 되는지도 [미확인]이라 소유자가 정한다 | `tools/ue/add-gasp.sh --verify`(§4·§6 V-15) |
| 9 | (지출·스택 결정) §7 재구성 경로 선택 | 지출(Metashape·클라우드 GPU)이나 되돌리기 비용이 큰 스택 변경(D-019 ①·⑤) | D-022·D-005 갱신 |
| 10 | (선택) RTX 5060 PC를 "저사양 하한 측정기"로 남길지 결정 | 하드웨어·측정 기준 결정(§6) | STATUS "결정 필요" |

- 1~5가 끝나야 §4(첫 빌드)를 할 수 있다. 6~8은 해당 카드 전에만 있으면 된다.

## 2. 버전 조합과 알려진 문제

**Epic 요구 사항(5.8)** — [F] = 이번 세션에 원문을 열어 확인, [S] = 검색 요약만, [M] = 기억.

| 항목 | Epic이 적은 값 | 이 Mac | 출처 |
|---|---|---|---|
| macOS | 최소 Sonoma 14.5, 권장 "Latest macOS Sequoia 15" | 27.2.1 — **검증 범위 밖**(macOS 26·27은 표에 없다) | [F] [macOS Development Requirements](https://dev.epicgames.com/documentation/en-us/unreal-engine/macos-development-requirements-for-unreal-engine) |
| Xcode | 최소 26.0, 권장 26.1.1. "Xcode 26.4 is not compatible with Unreal Engine." | 27.2 — **검증 범위 밖** | 같은 페이지 [F] |
| 하드웨어 | Apple Silicon M3 권장(기능별 M1/M2 최소), RAM 32 GB 권장 | M5 Max·128 GB — 충족 | 같은 페이지 [F] |
| Lumen GI·반사(소프트웨어 RT), TSR | M1 이상, 지원 | 충족 | 같은 페이지 [F] |
| Nanite·Virtual Shadow Maps | M2 이상, **"Beta"** | 충족, 단 Beta | 같은 페이지 [F] |
| Lumen 하드웨어 RT·MegaLights | M2 이상, **"Experimental"** | 충족, 단 Experimental | 같은 페이지 [F] |

**알려진 문제**
1. **UE-396802 — Xcode 27에서 Mac 게임 타깃 빌드 실패**. 5.8.1~5.8.3에서 Mac 게임 타깃(패키징 포함)이 ApplePostBuildSync 단계("Touch UBT generated tiles", "Bad file descriptor")에서 실패한다. 에디터 타깃은 성공한다. 실패하면 receipt(`Binaries/Mac/<Proj>.target`)가 안 써져 `BuildCookRun -skipbuild`도 실패한다. Epic이 "Fixed for 5.8.4"로 닫았다. [F] [포럼 1](https://forums.unrealengine.com/t/ue5-8-unable-to-build-game-on-macos-27/2746676), [포럼 2](https://forums.unrealengine.com/t/5-8-mac-failed-to-finalize-the-app-with-xcode-on-xcode-27-xcodebuild-started-without-stdin-bad-file-descriptor-in-touch-ubt-generated-tiles/2839864)
2. **5.8.4 핫픽스**(2026-10-20 배포): 노트 문구는 "iOS .app finalize … 'Bad file descriptor' error on macOS 27" 수정과 AutomationTool의 Mac `CreatePaksUsingChunkManifests` 경로 수정이다. [F] [5.8.4 Hotfix released](https://forums.unrealengine.com/t/5-8-4-hotfix-released/2842775). 노트는 **iOS**라고 쓴다. Mac 게임 타깃 수정의 근거는 UE-396802의 "Fixed for 5.8.4" 추적 상태(위 포럼 1·2)다. 5.8.4에서 실제로 고쳐졌는지는 §4-5 패키지 단계로 확인한다.
3. **`DEVELOPER_DIR` 우회**(5.8.3에 묶여야 할 때만): Xcode 26.6을 따로 설치(예: `/Applications/Xcode266.app`)하고 UBT·RunUAT 실행 때 `export DEVELOPER_DIR=/Applications/Xcode266.app/Contents/Developer`를 준다. Epic 직원이 확인한 우회다. [F] 위 포럼 1·2. Xcode 26.6 설치는 Apple 개발자 다운로드(로그인·약관)라 소유자 몫이다. `tools/ue/*.sh`는 `DEVELOPER_DIR`를 덮어쓰지 않으므로 셸에서 export하면 그대로 넘어간다 [미확인, §8 #8 — 스크립트 확정 뒤 확인].
4. **bindless 크래시**(5.8 프리뷰, macOS 26.5 + Xcode 26.5, 실행 직후 크래시). 보고된 우회는 `-BindlessOff` 실행 인자 또는 아래 ini다. 5.8 정식 이후 결과는 엇갈린다. [F] [포럼](https://forums.unrealengine.com/t/ue-5-8-preview-on-macos-xcode-26-5-is-crashing/2722969.md). **먼저 인자로만 시험한다.** ini는 핫스팟(`Config/DefaultEngine.ini`)이라 필요할 때만 `; [WP-20 hook]` 블록으로 넣는다.
   ```ini
   [ShaderPlatformConfig METAL_SM5]
   BindlessConfiguration=Disabled
   [ShaderPlatformConfig METAL_SM6]
   BindlessConfiguration=Disabled
   ```
5. **에디터 메인 창이 안 보임**(5.8.2, macOS 26.6.2, 화면 밖). 우회: Preferences를 열었다 닫고 Window 메뉴에서 메인 창을 고른다. 5.8.3·5.8.4에서 고쳐졌는지 [미확인]. [F] [포럼](https://forums.unrealengine.com/t/macos-5-8-2-editor-main-window-is-never-displayed-on-macos-26-regression-works-in-5-7/2762721)
6. 그 밖의 보고(참고): 5.8.3 Shipping 패키지의 Metal null-deref 크래시 [F] [포럼](https://forums.unrealengine.com/t/crash-null-deref-in-ftaskbase-tryretractandexecute-from-fsceneextensionsupdaters-end-during-async-frdgbuilder-deletion-macos-metal-ue-5-8-3/2835424), Apple Silicon에서 Embree Lightmass 세그폴트 [S] [포럼](https://forums.unrealengine.com/t/lightmass-fails-to-build-on-apple-silicon-macs-in-ue-5-6-when-embree-is-enabled/2736545)(우리는 Lumen이라 영향 적음), 5.8 Mac 패키징이 청크 0 pak만 만든다는 보고 [S] [포럼](https://forums.unrealengine.com/t/ue-5-8-mac-packaging-does-not-create-non-zero-chunk-paks-despite-valid-chunk-manifests/2846062).

**결정: Launcher의 5.8.x 최신(5.8.4 이상)을 쓴다.**
- 근거: Launcher는 5.8 최신 핫픽스만 설치한다. UE-396802는 "Fixed for 5.8.4"로 닫혔다(§2 #1·#2, §4-5에서 확인). 5.8.3을 고집하면 Xcode 26.6 병행 설치와 `DEVELOPER_DIR`가 늘 필요하다.
- 이것은 **엔진 패치 수준 변경**(5.8.3 → 5.8.4+)이다. CLAUDE.md의 "Unreal Engine 5.8.3" 표기와 PC 기록(V-01~V-18은 5.8.3)과 달라지므로 D-022에 기록한다. 같은 5.8 마이너라 에셋 호환은 유지된다고 본다 [M]. 설치 뒤 `Engine/Build/Build.version`의 실제 값을 §9에 적는다.
- macOS 27·Xcode 27이 Epic 검증 범위 밖이라는 위험은 남는다. 빌드가 엔진 쪽 이유로 막히면 우회 3(Xcode 26.6 + `DEVELOPER_DIR`)을 먼저 쓰고, 그래도 안 되면 막힌 단계와 로그를 기록해 오케스트레이터에 넘긴다.

## 3. 명령 대응표 (.ps1 → .sh, Windows 관습 → Mac)

**스크립트**(`tools/ue/*.sh`는 WP-20에서 함께 만든다. 플래그는 각 스크립트의 `--help`가 최종이다)

| Windows (`tools/ue/*.ps1`) | Mac (`tools/ue/*.sh`) | 차이 |
|---|---|---|
| `common.ps1`(`UE_ROOT` 기본 `C:\Program Files\Epic Games\UE_5.8`, `UnrealEditor.exe` 확인) | `common.sh`(소스 전용). `UE_ROOT` 기본 `"/Users/Shared/Epic Games/UE_5.8"`, `Engine/Binaries/Mac/UnrealEditor.app` 확인, `set -euo pipefail` | 엔진 내부 경로 [미확인, §8 #1~#2] |
| `.\tools\ue\build.ps1 [-Config Development]` | `tools/ue/build.sh [Config]` | `Engine/Build/BatchFiles/Mac/Build.sh GolmokEditor Mac <Config> -Project=… -WaitMutex` [미확인, §8 #4] |
| `.\tools\ue\generate-project-files.ps1` | `tools/ue/generate-project-files.sh` | Xcode 워크스페이스 `Golmok (Mac).xcworkspace`를 만든다. 일상 빌드에는 필요 없다 |
| `.\tools\ue\open-editor.ps1` | `tools/ue/open-editor.sh` | `open -a "<엔진>/Engine/Binaries/Mac/UnrealEditor.app" --args "<uproject>"`(기다리지 않음) |
| `.\tools\ue\test.ps1 [-Filter F] [-SetupDevLevel]` | `tools/ue/test.sh [--filter F] [--setup-dev-level] [--rhi]` | `--rhi`는 `-nullrhi` 없이 실제 Metal로 돌린다(nullrhi가 Mac에서 안 되거나 렌더가 필요한 테스트용). 결과 판정(index.json, 상태 열)은 같다 |
| `.\tools\ue\package.ps1 [-Config C] [-OutDir D]` | `tools/ue/package.sh [Config] [--out-dir DIR]` | `RunUAT.sh BuildCookRun -platform=Mac`, 기본 출력 `build/Mac`. `GOLMOK_PKG_DIR` 규칙은 같다(끝의 `/`를 뗀다) |
| `.\tools\ue\add-mannequin.ps1` | `tools/ue/add-mannequin.sh` | 같은 템플릿 폴더(`Templates/TemplateResources/High/Characters/Content`)를 `cp -R` |
| `.\tools\ue\add-gasp.ps1 -GaspProject … [-Verify] [-Force] [-LocalFiles] [-Manifest]` | `tools/ue/add-gasp.sh [--gasp-project DIR] [--verify] [--force] [--local-files] [--manifest]` | `--gasp-project` 기본값은 `~/UE/GASP_58`(`$HOME/UE/GASP_58`)이다. 편집기 실행 확인은 `ps -axo pid=,comm=`. **저장소 경로에 공백이 있으면 거부한다**(`-ExecutePythonScript=`가 첫 공백에서 끊긴다) — 공백 없는 경로에 클론한다. `--rhi` 플래그는 없다. `-nullrhi`를 빼려면 `GOLMOK_TEST_RHI=1`을 준다(`test.sh`도 같은 변수를 읽는다, §8 #5) |
| `UnrealEditor-Cmd.exe <uproject> -ExecutePythonScript=… -nullrhi -unattended` | `"$UE_ROOT/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor-Cmd" "<uproject>" -ExecutePythonScript=… -nullrhi -unattended` | `-Cmd` 바이너리 위치와 Mac `-nullrhi` [미확인, §8 #2·#5] |
| `UnrealEditor.exe <uproject> <맵> -game -RenderOffscreen …` | `".../UnrealEditor.app/Contents/MacOS/UnrealEditor" "<uproject>" <맵> -game -RenderOffscreen …` | Mac `-RenderOffscreen` [미확인, §8 #6] |

**Windows 관습**

| 런북의 Windows 관습 | Mac | 상태 |
|---|---|---|
| `setx GOLMOK_PKG_DIR C:\Users\user\golmok-pkg\Windows` | `~/.zprofile`에 `export GOLMOK_PKG_DIR="$HOME/golmok-pkg/Mac"` 한 줄, 새 셸부터 적용 | Claude 세션이 한다(소유자 작업 아님) |
| 방화벽 대화상자 취소·차단 규칙(C-07, TraceLog TCP 1985) | macOS 애플리케이션 방화벽은 기본 꺼짐이다 [M]. 켜져 있으면 새 서명되지 않은 앱마다 "들어오는 연결 허용?" 창이 뜰 수 있고, 그때는 **거부**를 누른다. 고정 출력 경로(`GOLMOK_PKG_DIR`) 원칙은 그대로다 | [미확인, §8 #11]. 방화벽 설정 변경은 보안 설정이라 소유자 몫 |
| `…\Binaries\Win64\Golmok.exe` | `"$GOLMOK_PKG_DIR"` 아래의 `Golmok.app`(정확한 깊이는 `find "$GOLMOK_PKG_DIR" -maxdepth 3 -name '*.app'`로 찾는다). 실행: `open -W "<…>/Golmok.app" --args …` 또는 `"<…>/Golmok.app/Contents/MacOS/Golmok" …` | [미확인, §8 #9] |
| `UnrealPak.exe`, `Manifest_UFSFiles_Win64.txt`, `Golmok-Windows.utoc` | `Engine/Binaries/Mac/UnrealPak`, `Manifest_UFSFiles_Mac.txt`, `Golmok-Mac.utoc` | 이름 [미확인, §8 #10] |
| 패키지 게임 Saved `%LOCALAPPDATA%\Golmok\Saved` 류 | `~/Library/Application Support/Epic/Golmok/Saved` | [미확인, §8 #12] |
| `-game` CSV `%LOCALAPPDATA%\UnrealEngine\5.8\Saved\Profiling\CSV\` | 프로젝트 `Saved/Profiling/CSV` 또는 `~/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Profiling/CSV` | [미확인, §8 #13]. `spike_runner`는 WP-20에서 win32가 아니면 `run_game_perf.sh`를 쓰도록 바뀌었다. Mac에서 실제로 도는지는 V-05에서 확인한다 |
| 에디터 로그 `Saved\Logs\Golmok.log` | 프로젝트 `Saved/Logs/Golmok.log`, 엔진 쪽은 `~/Library/Logs/Unreal Engine/GolmokEditor/` | [S] [미확인, §8 #14] |
| `.venv\Scripts\Activate.ps1`, `py -3.12` | `source tools/.venv/bin/activate`, `uv` | 완료(§0) |
| `winget install …` | `uv`·릴리스 바이너리(sudo 없음) 또는 Homebrew(§1 #6) | — |
| `Get-FileHash` | `shasum -a 256` | — |
| PowerShell `Start-Process … ; WaitForExit(t); Kill` | `/usr/bin/timeout <초> <명령>`(macOS 27.2.1에 있다. 시간 초과 때 종료 코드 124, 2026-11-27 확인). 다른 macOS 버전에 있는지는 [미확인]이라, 없으면 백그라운드 실행 + kill 루프로 대신한다 | 드라이버 재작성 시 |
| Windows Focus Assist(V-08b) | macOS 집중 모드(방해 금지) | 소유자가 켜거나 Claude가 안내 |
| **Win32 SendInput 드라이버**(ctypes, V-03/V-08/V-09c/V-17) | **재설계 항목.** 후보 ① 엔진 안 입력 드라이버(에디터 Python 또는 C++에서 `InputKey`/Enhanced Input 주입 — OS 권한이 필요 없고 창 포커스와 무관하다) ② macOS `CGEvent`(손쉬운 사용 권한이 필요하다 — 권한 부여는 소유자). ①을 먼저 권한다 | 재설계(카드 §6) |
| **ffmpeg `ddagrab` + `h264_nvenc`** 1080p60 녹화 | **재설계 항목.** 후보 ① `ffmpeg -f avfoundation -capture_cursor 0 -framerate 60 -i "<화면 번호>"` + `h264_videotoolbox`/`hevc_videotoolbox` ② ScreenCaptureKit(`screencapture -v`) ③ 엔진 안 프레임 덤프. 화면 기록 권한이 필요하다(소유자가 시스템 설정에서 허용) | 재설계. 60 fps 유지 [미확인] |
| **GPU-Z**(V-12 GPU ms·VRAM) | **재설계 항목.** GPU ms는 엔진 `stat gpu`/`stat unit`·우리 HUD(`RHIGetGPUFrameCycles`, Metal에서 값 유효성 [미확인]), 전원·GPU 사용률은 `sudo powermetrics --samplers gpu_power`(sudo라 소유자가 실행하거나 허용), 프레임 HUD는 Metal Performance HUD(`MTL_HUD_ENABLED=1`). 통합 메모리라 "VRAM" 기준(8 GB, `MaxMultiplier=2`)은 그대로 옮겨지지 않는다 | 재설계 |
| **WASAPI loopback**(V-10/V-18 패키지 녹음) | **재설계 항목.** 마스터 서브믹스 녹음(`AudioMixerLibrary`, PIE와 패키지 모두 OS 무관)을 1순위로 쓴다. OS 출력 캡처가 꼭 필요하면 ScreenCaptureKit 오디오나 가상 오디오 장치(설치는 소유자) | 재설계 |
| GUI 잠금 `C:\Users\user\AppData\Local\Temp\claude\gui-foreground.lock` | **`"$TMPDIR/claude/gui-foreground.lock"`**([AGENTS.md](../../AGENTS.md)와 같은 경로. 규칙도 같다: 한 줄 형식 `<세션> <목적> <ISO 시각>`, 20분 안 기록이 있으면 기다리고, 쓰는 동안 갱신, 끝나면 삭제). `mkdir -p "$TMPDIR/claude"` 뒤 `printf '%s %s %s\n' "<세션>" "<목적>" "$(date -u +%FT%TZ)" > "$TMPDIR/claude/gui-foreground.lock"`. `$TMPDIR`는 사용자별 폴더(`/var/folders/…/T/`)라 `/tmp`와 다른 파일이다. 다른 경로를 쓰면 상호 배제가 깨진다 | AGENTS.md·D-022와 같은 규칙 |
| 디버그 F 키 F1~F10 | Mac 키보드에서는 미디어 키다. `fn`을 같이 누르거나 시스템 설정 → 키보드 → "F1, F2 등의 키를 표준 기능 키로 사용"을 켠다. F3는 Mission Control일 수 있다 | §4 체크리스트 |

## 4. 첫 빌드와 검증 (UE 설치 뒤)

선행: §1 #1~#5. 순서대로 한다. 각 단계 결과를 §9에 적는다.

```bash
cd ~/projects/golmok
export UE_ROOT="/Users/Shared/Epic Games/UE_5.8"   # 기본값과 같으면 생략
cat "$UE_ROOT/Engine/Build/Build.version"           # 5.8.x 확인(PatchVersion ≥ 4)
xcodebuild -version && xcode-select -p

tools/ue/build.sh                      # 1. GolmokEditor Mac Development
tools/ue/add-mannequin.sh              # 2. Content/Characters (이미 있으면 "Already present")
tools/ue/test.sh --setup-dev-level     # 3. L_Dev 생성 + Golmok.* 자동화
tools/ue/open-editor.sh                # 4. GUI 에디터, L_Dev PIE
tools/ue/package.sh                    # 5. Mac Development 패키지 → $GOLMOK_PKG_DIR 또는 build/Mac
# 6. 빈 L_Dev Mac 기준선 (아래 "기대 결과 6")
```

**기대 결과**
1. `build.sh`: 성공(종료 코드 0). 실패하면 아래 "첫 컴파일 체크리스트"를 보고 **C++를 고쳐 다시 빌드한다**(pc-setup §2와 같은 원칙). Astra 레인 파일(`Characters/`, `Audio/`, `Tests/GolmokCharacterRoster*`)에서 나면 고치지 않고 이슈 #30·PR로 알린다.
2. `add-mannequin.sh`: `Content/Characters/Mannequins/…`가 생기고 `git status`에 추적 파일 변화가 없다(`.gitignore` 대상).
3. `test.sh --setup-dev-level`: 자동화 **39개** 전부 `Success`(V-16 기준 목록, [pc-verify-wp16a.md](pc-verify-wp16a.md) §3 "세 번째 명령"). 판정은 상태 열로 한다(`Succeeded:`는 Warning 있는 테스트를 따로 센다). `-nullrhi`에서 렌더 의존 테스트가 실패하면 `--rhi`로 다시 돌려 비교하고 둘 다 적는다.
4. `open-editor.sh`: 창이 안 보이면 §2 알려진 문제 5의 우회를 쓴다. 시작 직후 크래시면 `-BindlessOff`(§2 #4)를 시험한다. L_Dev PIE에서 걷기·달리기(Shift)·점프·카메라 충돌이 동작한다. `Saved/Logs/Golmok.log`에 Error가 없다. 스크린샷 1장(960×540 JPEG)을 `docs/runbooks/mac-setup-L_Dev-pie.jpg`로 남긴다(LFS).
5. `package.sh`: 첫 줄 `Package output: …`가 기대 경로다. 실패가 ApplePostBuildSync "Bad file descriptor"면 UE-396802다(§2 #1). 엔진이 5.8.4 이상인지 다시 보고, 그래도 나면 `DEVELOPER_DIR` 우회를 쓴다. `.app`이 뜨고 L_Dev로 걸을 수 있다.
6. **빈 L_Dev Mac 기준선**(V-19의 마지막 단계, §6 기준선 재설정의 출발점). PC 값(빈 L_Dev 158 fps)과 비교하지 않는다.
   - 조건: 1920×1080 창 모드, Development 빌드, 시작 위치(PlayerStart)에서 카메라를 움직이지 않는 고정 시점, 기본 시간대·날씨. 디스플레이(내장 Retina인지 외장인지, 주사율), 창 크기·배율, 전원 연결과 저전력 모드 꺼짐을 같이 적는다.
   - 방법 ①(필수): 패키지 `.app`을 `-windowed -ResX=1920 -ResY=1080`으로 띄우고 콘솔에서 `stat unit`·`stat gpu`를 켠다. 30초 안정된 뒤 Frame·Game·Draw·GPU ms와 fps를 3번 읽어 평균을 적는다. 스크린샷 1장을 `docs/runbooks/mac-setup-L_Dev-baseline.jpg`(960×540 JPEG, LFS)로 남긴다.
   - 방법 ②(가능하면): 같은 실행에서 [research/08](../research/08-spike-results.md) 절차대로 `CsvProfile Start` → 60초 → `CsvProfile Stop`을 하고 `golmok-perf <csv> --label "L_Dev Mac 1080p" --markdown`으로 요약한다. `-csvCaptureFrames`는 섞지 않는다([pc-spike.md](pc-spike.md)의 CSV 프레임 수 "확인" 줄). CSV 위치는 §8 #13이다. 막히면 ①만 적고 막힌 이유를 메모에 적는다.
   - HUD GPU 열이 `stat gpu`와 크게 다르면 §8 #20에 적는다.
- `Golmok.uproject`의 `TargetPlatforms`에는 WP-20에서 `"Mac"`을 더했다(`["Windows", "Mac"]`). 이 목록으로 Mac 패키지가 통과하는지 확인한다 [미확인, §8 #15].

**첫 컴파일 체크리스트**(WP-20 감사, 소스 스캔만 했고 컴파일은 못 했다)
- (A) 빌드 전 확인
  - `Config/DefaultEngine.ini`에는 `[/Script/WindowsTargetPlatform.WindowsTargetSettings]`(DX12 SM5/SM6)만 있다. Mac은 엔진 기본 RHI를 쓴다. Lumen·Nanite·VSM·VT가 SM6 Metal을 요구하면 `[/Script/MacTargetPlatform.MacTargetSettings]`에 `+TargetedRHIs=SF_METAL_SM6`을 `; [WP-20 hook]` 블록으로 더한다. 키 이름은 엔진의 `Engine/Config/Mac/*Engine.ini`·`BaseEngine.ini`로 먼저 확인한다 [미확인, §8 #16]. Windows 줄은 고치지 않는다.
  - UBT가 프로젝트 루트에 `Golmok (Mac).xcworkspace`를 만든다. WP-20이 `.gitignore`의 `[WP-20 hook]` 블록에 `unreal/Golmok/*.xcworkspace`와 `.DS_Store`를 넣었다. `generate-project-files.sh` 뒤 `git status`에 워크스페이스가 안 보이는지만 확인한다.
- (B) clang 경고 위험(스캔에서는 발견 없음, 컴파일로 확인)
  - `-Wshadow`(MSVC C4456~4459가 이미 오류라 위험 낮음), `-Wsometimes-uninitialized`, `-Wunused-but-set-variable`, `-Wreorder-ctor`
  - `-Wmisleading-indentation`: `Tests/GolmokCharacterRoster*.cpp`의 한 줄 압축 스타일(Astra 레인 — 고치지 않고 알린다)
  - `SIZE_T`(Mac `unsigned long`)와 `uint64`(`unsigned long long`) 섞기, 형식 문자열 폭(`%llu`는 이미 명시 캐스트)
  - 엔진 헤더 대소문자(APFS 기본은 대소문자 무시라 Mac에서는 안 드러난다)
  - 테스트의 비ASCII 리터럴(`TEXT("매니")`, `—`, `①`): TCHAR가 char16_t라 위험 낮음
- (C) 실행해서 볼 것
  - HUD GPU 열(`RHIGetGPUFrameCycles`)과 렌더 열(`GRenderThreadTime`)이 Metal에서 유효한 값인지. PC 기준선과는 비교하지 않는다(§6).
  - Retina에서 `HighResShot`·포토 모드 배율 출력 크기(픽셀 대 포인트), HUD `MarginPx`/`HudScale`
  - 패키지에 `Config/Golmok/*.json`이 들어가고(`DirectoriesToAlwaysStageAsUFS`) 시간대·날씨·애니메이션·캐릭터 설정이 읽히는지
  - 디버그 F 키(§3 표 마지막 줄), 트랙패드 시점 감각, 게임패드(Apple GameController의 `Special_Left/Right`·트리거 축)
  - Lumen·VSM·Nanite·VT·TSR·Niagara 비가 Metal에서 보이는지. PC 판정과 같은 모습인지는 다시 판정한다.
  - 오디오 재생(CoreAudio 믹서), 마스터 서브믹스 녹음
  - `Debug/GolmokDebugSubsystem.cpp`의 CSV 안내 문자열은 WP-20에서 `%LOCALAPPDATA%` 대신 중립 문구("per-user engine Saved/Profiling/CSV")로 고쳤다. 실제 CSV 위치는 §8 #13으로 확인한다

## 5. 로컬 상태: 다시 만드는 것과 PC에서 가져올 것

**Mac에서 스크립트로 다시 만든다**
- 마네킹 팩 `Content/Characters/`: `tools/ue/add-mannequin.sh`
- `L_Dev`: `tools/ue/test.sh --setup-dev-level`(또는 `golmok.setup_dev_level`)
- `L_ZoneTest` + 합성 실내: `synthetic_zone.run(interior=True)`
- `z_synthetic_scan` zone: `make_synthetic_zone.py` + `zone_import`
- `L_ZoneTest06/09` 복사본: 해당 런북 절차
- SoundWave `SW_*`: LFS WAV에서 `audio_import`(Astra 레인 스크립트, 실행만 한다)
- 베이스맵 UE 에셋과 `L_Basemap_*`: `basemap_import` — **베이스맵 빌드 출력이 있을 때만**
- tools venv: §0

**PC를 정리하기 전에 소유자가 Mac으로 복사할 것**(외장 디스크나 네트워크 공유. 원본은 PC에 남긴다)

| 항목 | PC 위치 | 쓰는 곳 | 비고 |
|---|---|---|---|
| 베이스맵 원천 데이터 | `%USERPROFILE%\golmok_data\`(V-World SHP `AL_D010_11_20260909`, NGII 등고선·표고점 도엽, 90 m DEM `37608.img`, 25 cm 정사영상) | ROADMAP 1.2 재빌드, V-17 §4 | 다시 받으려면 소유자 로그인 + INNORIX Agent(Windows exe, Mac 지원 [미확인]). 복사가 가장 싸다 |
| 베이스맵 빌드 출력 | `%USERPROFILE%\golmok_basemap\yeonnam` | `basemap_import` → `L_Basemap_Yeonnam` | 원천 데이터가 있으면 Mac에서 `golmok-basemap build`로 다시 만들 수 있다 |
| V-08 녹화 | `C:\UE\v08_recordings\`(장면별 원본·틱 샘플 `scenes`) | V-08b §9-2(b) | 대체 불가 |
| 그 밖의 녹화·원본 | `C:\Users\user\golmok-pc-recordings\v11-2026-10-04\`, V-10/V-10b/V-11 WAV·CSV·PNG 원본 | 비교 기준(참고) | — |
| 구 세이브 | `golmok_auto.sav`(PC의 프로젝트 `Saved/SaveGames/`) | V-16 §9 Rule 0, V-15 레거시 확인 | 없으면 그 확인을 "자료 없음"으로 적는다 |
| 검증 드라이버 | PC 워크트리 스크래치패드의 V-03/V-09c `pie_driver.py`, V-08 드라이버(`awesome-cohen-31f894`, `upbeat-mccarthy-343277` 등) | V-08b·V-17 드라이버 재설계의 출발점 | SendInput 부분은 어차피 다시 쓴다(§3) |
| GASP 로컬 사본 | `C:\UE\GASP_58`(5.6 GB), 백업 `C:\UE\golmok_animeval_backup`, 로컬 `Config/Golmok/local`·`Config/Tags/GASP*.ini`·`Content/GASP` | V-08b·V-15 | **복사 대신 Fab 재다운로드를 권한다**(§1 #8). 머신 간 복사의 라이선스는 [미확인] |
| EgoBlur 모델 | `tools\models\ego_blur_*.jit` | V-01 §3, V-05 | PC에서도 아직 받지 않았다 → §1 #7 |

- **git에 이미 있는 것**: GASP 테스트 설정 커밋 `b61eea0`("병합 금지")은 `origin/pc/v08-animation`에 있다. Mac에서 `git fetch origin pc/v08-animation && git show b61eea0`으로 바로 본다. 다른 `pc/*` 브랜치는 main보다 앞선 커밋이 없다.
- 캡처(C-01/C-02)는 아직 없다.

## 6. 카드별 Mac 계획

**기준선 재설정 규칙**
- PC GPU 예산과 기준선은 RTX 5060 8 GB·1080p·DX12 SM6 값이다(예: 빈 L_Dev 158 fps, 연남동 169 fps·GPU 5.4 ms, V-16 비 FX ≤ 0.5 ms GPU·날씨 합계 ≤ +1.0 ms, V-09 `MaxMultiplier=2`). **Mac 수치와 비교하지 않는다.**
- 각 카드는 **같은 세션 안의 기준 측정**(같은 레벨·해상도·시점에서 기능 끔 상태)을 먼저 재고, 예산을 **상대값**(+ms, %)으로 판정한다. 절대 fps 하한이 있는 기준(예: V-15 "≥ 60 fps")은 Mac 값으로 같이 적되 판정은 상대값을 우선한다.
- ROADMAP의 "RTX 5060 1080p ≥ 30 fps 측정 하한" 역할(저사양 하한 측정기)은 **비어 있다.** M5 Max는 하한 측정기가 될 수 없다. PC를 이 용도로 남길지, 다른 기준을 둘지는 소유자 항목이다(§1 #10).
- 결과는 `pc/<카드>` 브랜치에 커밋하고 런북 결과 칸에 "Mac(M5 Max)"을 명시한다.

| 카드 | 런북 | Mac에서 그대로 되는 것 | 바꾸거나 다시 만들 것 | 선행 |
|---|---|---|---|---|
| V-16 | [pc-verify-wp16a.md](pc-verify-wp16a.md) | 빌드(Niagara), MPC Python 작성, 39 자동화, PIE §4~§9 | Niagara 에디터 GUI(GPUCompute on Metal [미확인]), §10 성능은 같은 세션 기준 재측정, §11 패키지는 Mac 패키지(`Golmok-Mac.utoc`, `UnrealPak` Mac 경로), `setx`·방화벽 줄은 §3 표로 | §4 통과 |
| V-17 | [pc-verify-v17.md](pc-verify-v17.md) | §3 Full Precision UV 임포트(헤드리스+GUI) | §1·§2 60 fps 캡처와 4캐릭터 입력은 캡처·입력 재설계(§3) 뒤, §4는 베이스맵 복사(§5) 뒤 같은 세션 기준으로, §5 패키지 확인은 Mac `.app` + `-RenderOffscreen -ExecCmds` [미확인] | §4, V-16, 드라이버 |
| V-18 | [pc-verify-v18.md](pc-verify-v18.md) | PIE 마스터 서브믹스 녹음(`AudioMixerLibrary`, OS 무관 — Mac 동작 [미확인]). −42.45 dBFS ± 1 dB 예측은 장치 무관이라 그대로 쓴다 | 패키지 단계의 WASAPI loopback → 서브믹스 녹음 또는 §3 대안. C-08 청취는 Mac 출력 장치로 새로 정한다(DELL U2724D 고정 볼륨 기준은 이력) | V-16 |
| V-12 | [pc-verify-v12.md](pc-verify-v12.md) | 96장 포토 모드 촬영 절차, 소유자 채점 | 드라이버(피치 −15°)는 엔진 안 입력으로, GPU-Z → `stat gpu`·powermetrics·Metal HUD(§3), VRAM 판정은 통합 메모리라 기준을 새로 둔다. 툰 머티리얼용 별도 로컬 프로젝트 복사본은 Mac에 새로 만든다 | §4 |
| V-08b | [pc-verify-v08b.md](pc-verify-v08b.md) | 설정 `git show b61eea0`, 자식 BP·리타깃·`.uplugin` 표, 블라인드 채점 절차 | SendInput 드라이버와 ffmpeg `ddagrab`+`h264_nvenc` 녹화는 재설계(§3), `Get-FileHash` → `shasum`, GASP는 Fab 재다운로드(§1 #8, Mac 지원 [미확인]), §9-2(b)는 V-08 녹화 복사(§5)가 필요하다. Dev·Shipping 패키지 스모크는 Mac 패키지로 | §1 #8, 드라이버, §5 복사 |
| V-15 / 19b | [pc-verify-wp19.md](pc-verify-wp19.md) A/B | BPI 구현 BP·T3D 붙여넣기 GUI 절차, 최종 `animation.json` | `add-gasp.ps1 -GaspProject C:\UE\GASP_58` → `tools/ue/add-gasp.sh --gasp-project ~/UE/GASP_58`(헤드리스 3회), B절은 V-08b와 같은 드라이버, 성능 기준(D-021 "fps 하락 ≤ 5 % 또는 ≥ 60 fps")은 같은 세션 ① 기준으로 | V-08b, D-021 소유자 재확인 |
| V-05 | [pc-spike.md](pc-spike.md) | Cesium(5.8 Mac 지원은 cesium-unreal v2.28.0+ 릴리스에 macOS 포함 [F] [releases](https://github.com/CesiumGS/cesium-unreal/releases), Fab 빌드의 Mac 바이너리 [미확인]), `-game` 성능 CSV(경로 §8 #13, WP-20의 `run_game_perf.sh`) | RealityScan·Postshot·LCC4Unreal은 Mac 불가(§7), DLSS on/off는 Mac 불가(해당 없음으로 적는다), EgoBlur는 CPU(§7), `D:\golmok_*` 경로 → `~/golmok_data` | §7 소유자 결정, C-02 |
| V-01 §3 | [pc-setup.md](pc-setup.md) §3 | `golmok-exif`·`golmok-frames`(순수 Python + exiftool·ffmpeg) | `golmok-blur`는 `--device cpu`(자동 선택도 CPU)로 돈다. 처리 속도를 잰다. MPS는 [미확인]. rawpy arm64 휠 [미확인] | §1 #6·#7, C-01 |

## 7. 재구성 파이프라인 (Mac)

> **2026-11-27 갱신([D-023](../DECISIONS.md), [WP-21](../plan/WP-21-mac-recon-pipeline.md))**: 소유자 지시("대체할 수 있는 것들은 대체해.")로 무료 대체 도구를 스파이크 후보로 설치·스모크했다. 절차와 대체표·미확인 표는 **[mac-recon.md](mac-recon.md)**다. 아래 본문은 그 전의 조사 기록이다.
> - 설치: `tools/mac/install-recon-tools.sh`(sudo·Homebrew 없음, `~/golmok-tools`) — COLMAP 4.2.1 conda-forge `cpu_lgpl`, ffmpeg 9.1 `lgpl`, exiftool 13.64, Brush v0.3.0. §1 #6(Homebrew)은 재구성용으로는 필요 없다. `golmok-objcap`(Object Capture)은 `swift build`, Cesium for Unreal 2.31.0은 GitHub 릴리스.
> - 스모크(공개 데이터, 품질 근거 아님): Buddha 67장 COLMAP → Brush(Metal) → `golmok-splat` 끝까지 통과, objcap 메시(Buddha·Tyrol 76장) 통과, Brush PLY → 3D Tiles → Cesium on Metal 렌더 통과(저장소 밖 프로젝트 사본).
> - Mac에서 대체하지 못한 것: 조밀 MVS 메시(COLMAP은 CUDA·CGAL 필요), XGRIDS LCC4Unreal. 지출 대안(Metashape·클라우드 GPU)과 EgoBlur 모델 동의, Object Capture 출력 약관 확인은 소유자 항목이다.
> - §8 #26 Object Capture 상한은 확인됐다: 2000장·16384 px(`golmok-objcap limits`).

**지금 파이프라인(D-005)은 Mac에서 돌지 않는다.**
- RealityScan 2.x: Epic 요구 사항 페이지가 "RealityScan runs primarily on Windows"라고 쓰고, Linux는 CLI 전용으로만 권한다. macOS는 없다. NVIDIA CUDA GPU(CC ≥ 3.5)가 없으면 모델·텍스처를 만들 수 없다. Mac의 Windows ARM VM에도 CUDA가 없다. [F] [RealityScan hardware and software requirements](https://dev.epicgames.com/documentation/realityscan/hardware-and-software-requirements)
- Postshot(Jawset): "Windows 10 or later, Nvidia GPU CC 7.5 or higher". macOS 빌드가 없다. [F] [jawset.com](https://www.jawset.com/), [research/07](../research/07-ue5-toolchain.md)
- XGRIDS LCC4Unreal: README가 "Windows, Linux (cross-compile)"와 DX11·DX12·Vulkan만 적는다. macOS·Metal이 없다. **Mac에서 스플랫을 UE로 띄우는 데 막힌다.** [F] [LCC-3DGS-Unreal-Plugin](https://github.com/xgrids/LCC-3DGS-Unreal-Plugin)

**Mac 후보**(D-002: 비상업·AGPL 금지를 지킨다)

| 단계 | 후보 | 라이선스·비용 | 알려진 한계 |
|---|---|---|---|
| 블러 | `golmok-blur`(EgoBlur) CPU | Apache-2.0 [F] [EgoBlur](https://github.com/facebookresearch/EgoBlur) | EgoBlur README가 Mac은 CPU 전용이라 "very slow"라고 쓴다. 우리 코드는 `auto`가 CUDA 없으면 CPU를 고른다(`tools/golmok_tools/privacy/detector.py`). MPS [미확인] |
| SfM·포즈 | COLMAP 4.x(GLOMAP `global_mapper` 포함), CPU | new BSD [F] [LICENSE](https://raw.githubusercontent.com/colmap/colmap/main/LICENSE), `brew install colmap`. Homebrew 빌드 의존성 라이선스 [미확인] | 조밀 스테레오(MVS)는 CUDA 전용이다 [F] [FAQ](https://colmap.github.io/faq.html). SfM과 특징 추출은 CPU로 된다 |
| 메시·텍스처 | Apple Object Capture(RealityKit `PhotogrammetrySession`, OBJ/USDZ, `poses` 요청) | OS API, 무료. 출력 이용 조건 [미확인] [F] [PhotogrammetrySession](https://developer.apple.com/documentation/realitykit/photogrammetrysession.md) | 장당·해상도 상한이 기기별이다(M5 Max 값 [미확인]). 골목 규모(약 1,300장·48MP) 품질 [미확인], 영역 모드 오류 보고 있음 |
| 메시·텍스처 | Agisoft Metashape(Apple M1/M2 CPU 지원 명시) | 유료: Standard $179, Pro $3,499 [F] [store](https://www.agisoft.com/buy/online-store/). 서비스 연동은 별도 라이선스(research/02) | Metal 가속·macOS 27 빌드 [미확인]. **지출** |
| 스플랫 학습 | Brush(arm64 바이너리 `brush-app-aarch64-apple-darwin`, COLMAP 입력) | Apache-2.0 [F] [LICENSE](https://raw.githubusercontent.com/ArthurBrussee/brush/main/LICENSE), [README](https://github.com/ArthurBrussee/brush) | PLY 출력 세부·Postshot 품질 대등(전체 해상도·SH3·AA) [미확인] |
| 스플랫 학습 | msplat(Metal 전용, COLMAP 입력, PLY 출력) | Apache-2.0 [F] [LICENSE](https://raw.githubusercontent.com/rayanht/msplat/main/LICENSE) | 작은 저장소. 릴리스 v1.1.4(2026-08-25, macOS arm64 휠) 있음(2026-11-27 재확인, r5의 "릴리스 없음"은 정정). Inria 파생 코드 여부를 **소스 감사한 뒤에만** 쓴다 |
| (대안) 클라우드 Windows GPU | AWS g6e(L40S 48 GB) 원격 데스크톱 + RealityScan·Postshot 그대로 | 시간당 비용·계정 = **지출**. 서울 리전·Windows AMI [미확인] [F] [g6e](https://aws.amazon.com/ec2/instance-types/g6e/) | 블러된 이미지(`*_blurred`)만 올린다(D-007). 지금 파이프라인과 좌표계 공유 방식을 그대로 쓴다 |

**쓰지 않는 것(D-002)**: gsplat-mps(AGPLv3, OpenSplat 파생) [F] [gsplat-mps](https://github.com/iffyloop/gsplat-mps), OpenSplat(AGPL), OpenMVS(AGPL), Inria 3DGS 계열(비상업). gsplat 본체는 Apache-2.0이지만 CUDA 커널이라 Mac에서 쓸 수 없다 [F] [gsplat](https://github.com/nerfstudio-project/gsplat).

**결정은 소유자 몫이다**(D-019 ①·⑤: 스택 변경과 지출). 이 런북은 고르지 않는다. 권하는 스파이크 순서만 적는다. 각 단계는 무료이고 되돌릴 수 있다.
1. EgoBlur CPU 처리량을 리허설 사진 20장으로 잰다(V-01 §3과 같이). 1,300장 처리 시간을 추정한다.
2. COLMAP SfM(CPU) → Brush 스플랫을 합성 데이터나 블러된 리허설 사진으로 돌린다. 포즈가 COLMAP 하나에서 나오므로 메시와 스플랫이 같은 좌표계를 쓸 수 있는지 본다.
3. 같은 사진으로 Object Capture 메시를 만들고, COLMAP 포즈와 맞출 수 있는지(포즈 내보내기) 본다.
4. 1~3 결과로 ① Mac 전용 무료 스택 ② Mac + 유료 Metashape ③ Mac + 클라우드 Windows GPU 중에서 소유자가 고른다. 스플랫을 UE에 띄우는 플러그인(LCC4Unreal 대체)은 어느 경우에도 따로 조사해야 한다 [미확인].

## 8. 미확인 표

| # | 항목 | 지금 적어 둔 값 | UE 설치 뒤 확인 방법 | 확인 결과 |
|---|---|---|---|---|
| 1 | Launcher 엔진 루트 | `"/Users/Shared/Epic Games/UE_5.8"` | Launcher → 라이브러리 → 엔진 버전 ▾ → "Show in Finder" / `ls` | |
| 2 | 에디터·`-Cmd` 바이너리 | `Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor`, 같은 폴더의 `UnrealEditor-Cmd` | `ls "$UE_ROOT/Engine/Binaries/Mac" "$UE_ROOT/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS"` | |
| 3 | Metal Toolchain 별도 구성요소 | Xcode Settings → Components | `xcrun -f metal`, 첫 셰이더 컴파일 로그 | |
| 4 | 빌드 명령 | `Engine/Build/BatchFiles/Mac/Build.sh GolmokEditor Mac Development -Project=… -WaitMutex`(아키텍처 기본 arm64) | `build.sh` 실행 로그, `file unreal/Golmok/Binaries/Mac/*.dylib` | |
| 5 | Mac `-nullrhi` 헤드리스 실행 | `test.sh`·`add-gasp.sh` 기본값. 끄는 방법은 `test.sh --rhi` 또는 환경 변수 `GOLMOK_TEST_RHI=1`(`add-gasp.sh`는 변수만 받는다) | `test.sh` 결과 39/39, 실패 시 `--rhi`와 비교. `add-gasp.sh`가 `-nullrhi`에서 실패하면 `GOLMOK_TEST_RHI=1 tools/ue/add-gasp.sh …` | |
| 6 | Mac `-game -RenderOffscreen` | pc-setup §5·V-17 §5 방식 | 짧은 `-game` 실행 1회, 창 없이 CSV가 남는지 | |
| 7 | 실제 설치 패치 버전 | 5.8.4 이상 | `Engine/Build/Build.version` | |
| 8 | `DEVELOPER_DIR` 전달 | `tools/ue/*.sh`가 덮어쓰지 않는다 | 스크립트 읽기 + `DEVELOPER_DIR=… tools/ue/build.sh` 로그의 Xcode 경로 | |
| 9 | 패키지 `.app` 위치 | `$GOLMOK_PKG_DIR` 아래 `Golmok.app`(깊이 미정) | `find "$GOLMOK_PKG_DIR" -maxdepth 3 -name '*.app'` | |
| 10 | 패키지 매니페스트·utoc 이름 | `Manifest_UFSFiles_Mac.txt`, `Golmok-Mac.utoc`, `Engine/Binaries/Mac/UnrealPak` | 패키지 폴더 `find … -name 'Manifest_*' -o -name '*.utoc'` | |
| 11 | macOS 방화벽과 TraceLog 1985 | 기본 꺼짐이면 창 없음, 켜져 있으면 거부 | `/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate`, 패키지 실행 중 `lsof -nP -iTCP:1985 -sTCP:LISTEN` | |
| 12 | 패키지 게임 Saved | `~/Library/Application Support/Epic/Golmok/Saved` | 패키지 실행 뒤 `ls` | |
| 13 | `-game` CSV 위치 | 프로젝트 `Saved/Profiling/CSV` 또는 `~/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Profiling/CSV` | `-csvCaptureFrames` 실행 뒤 `find ~/Library/Application\ Support/Epic unreal/Golmok/Saved -name 'Profile*.csv' -newer <표식>` | |
| 14 | 에디터 로그 위치 | 프로젝트 `Saved/Logs/Golmok.log`, `~/Library/Logs/Unreal Engine/GolmokEditor/` | 에디터 실행 뒤 `ls` | |
| 15 | `.uproject` `TargetPlatforms` | WP-20에서 `"Mac"` 추가함(`["Windows", "Mac"]`) | `package.sh`가 이 목록으로 통과하는지 | |
| 16 | Mac RHI ini 키 | `[/Script/MacTargetPlatform.MacTargetSettings]` `+TargetedRHIs=SF_METAL_SM6` | `grep -rn TargetedRHIs "$UE_ROOT/Engine/Config"`, Project Settings → Platforms → Mac | |
| 17 | `-BindlessOff` 필요 여부 | 크래시가 나면만 | 에디터 실행 1회 | |
| 18 | 메인 창 화면 밖 문제(5.8.4+) | 우회만 적음 | 에디터 실행 1회 | |
| 19 | Niagara GPUCompute·VT on Metal | 지원으로 가정 | V-16 §4 PIE | |
| 20 | `RHIGetGPUFrameCycles`가 Metal에서 유효한지 | 미정 | HUD GPU 값과 `stat gpu` 합계 비교 | |
| 21 | 마스터 서브믹스 녹음(Mac) | 동작 가정 | V-18 PIE 녹음 1회 | |
| 22 | GASP Mac 지원·PoseSearch 등 플러그인 | 가정 | `add-gasp.sh --verify` | |
| 23 | Cesium Fab 빌드의 Mac 바이너리 | GitHub 릴리스에는 macOS 포함 | Fab/Launcher 설치 뒤 `Plugins/Marketplace/CesiumForUnreal/Binaries/Mac` | |
| 24 | EgoBlur on MPS, rawpy arm64 휠 | CPU 사용 | `golmok-blur --device mps` 시험, `pip install -e ".[raw]"` | |
| 25 | ffmpeg avfoundation 60 fps 녹화 | 후보 | 10초 시험 녹화의 프레임 수 | |
| 26 | Object Capture 상한(M5 Max) | 미정 | `PhotogrammetrySession` limits 값 출력 | |

## 9. 결과

| 단계 | 날짜 | 세션·모델 | 결과 | 메모 |
|---|---|---|---|---|
| §0 기반 도구 | 2026-11-27 | WP-20 세션 | 완료 | 위 §0 표 |
| §1 소유자 항목 1~5 | | | | |
| §2 엔진 버전(`Build.version`) | | | | |
| §4-1 `build.sh` | | | | |
| §4-2 `add-mannequin.sh` | | | | |
| §4-3 `test.sh --setup-dev-level`(39) | | | | |
| §4-4 `open-editor.sh`·L_Dev PIE | | | | |
| §4-5 `package.sh`·`.app` 실행 | | | | |
| §4-6 빈 L_Dev Mac 기준선(1080p, `stat unit`/`stat gpu`, CsvProfile) | | | | fps·GPU ms·디스플레이·창 설정 |
| §5 PC 자료 복사 | | | | |
| §8 미확인 해소 | | | | |
