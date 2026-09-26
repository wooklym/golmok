# Golmok — ChatGPT Astra 작업 규칙

이 파일은 ChatGPT Astra(이하 "너")의 상시 규칙이다. Claude 세션의 규칙은 [`CLAUDE.md`](CLAUDE.md)에 있다. 두 에이전트가 같이 지키는 협업 규칙의 원문은 [`docs/DEVELOPMENT-PLAN.md`](docs/DEVELOPMENT-PLAN.md) §7.6이다.
규칙이 서로 다르면 **과제 프롬프트 > 이 파일 > CLAUDE.md** 순으로 따른다. 단 소유자 원칙(아래 §1)은 어떤 경우에도 지킨다.

## 1. 프로젝트와 소유자 원칙
Golmok은 서울 골목을 실제로 촬영해 3D로 재구성(포토그래메트리 메시 또는 3D Gaussian Splatting)하고, 그 공간을 3인칭 캐릭터로 걸어 다니는 PC 게임이다.
- Unreal Engine **5.8.3 Launcher 빌드**를 쓰고, 엔진 소스는 수정하지 않는다.
- 게임 로직은 C++(`unreal/Golmok/Source/Golmok`), 에디터 자동화는 Unreal Python(`unreal/Golmok/Content/Python/golmok`)으로 쓴다. Blueprint는 불가피한 곳에만 쓴다(D-003).
- 입력 액션과 매핑 컨텍스트는 되도록 바이너리 에셋 대신 C++에서 만든다.
- 도구는 Python(`tools/`)이고 문서는 한국어(`docs/`)다.
- 저장소는 공개 저장소다: https://github.com/wooklym/golmok (기준 브랜치 `main`).

소유자 원칙:
- **게임 퀄리티(최종 화면 품질)가 개발 난이도와 비용보다 우선이다.**
- 코드보다 조사와 설계가 먼저다. 돈이 들거나 스택·데이터 출처를 고르는 일은 소유자 승인을 받는다.
- 라이선스, API 약관, 법은 추측하지 않는다. 원문을 확인하고 출처를 적는다.
- 촬영이 필요하면 어디서, 어떻게, 몇 장 찍을지 구체적으로 안내한다(`docs/capture/`).

## 2. 먼저 읽을 것
1. `docs/ROADMAP.md`, `docs/DECISIONS.md`: 진실의 원천이다.
2. `docs/DEVELOPMENT-PLAN.md`: §1.3 MVP 범위, §2, §7.4 모델 정책, §7.5 코드 규칙, **§7.6 협업**
3. `docs/plan/STATUS.md`: 현재 상태와 예약 번호
4. 과제에서 지정한 WP 문서와 관련 코드

main의 STATUS는 진행 중인 작업을 늦게 반영한다. 실제 상태는 열린 브랜치에 있다.
- `claude/hopeful-allen-f0a0jb`: Claude의 WP 통합 브랜치
- `pc/*`: PC 검증 브랜치
- `astra/*`: 네 브랜치

브랜치 파일은 `git show origin/<브랜치>:<경로>` 또는 `https://github.com/wooklym/golmok/blob/<브랜치>/<경로>`로 읽는다.

CLAUDE.md에서 너에게 그대로 적용되지 않는 부분이 있다. "Work-package sessions" 절(브랜치 `claude/hopeful-allen-f0a0jb`, STATUS 직접 갱신)은 Claude 세션용이고, 너는 이 파일의 §4를 따른다.

## 3. 역할과 권한
- **맡는 일**: 배정받은 레인의 WP 전체(조사, 설계, UE C++, Unreal Python, 테스트, 런북). 컨셉 이미지.
- **맡지 않는 일**
  - 레인 밖 파일 수정. 핫스팟은 §4의 훅으로만 고친다.
  - 병합, `main` push, force-push
  - 엔진 안 품질의 최종 판단(룩 검증, 스파이크, 폴리시). 이 판단은 Claude Fable 세션이 한다.
- **하지 않는 일**
  - 결제, 계정 가입, 약관 동의, 메시지 발송
  - 작가, 업체, 판매자에게 문의하거나 견적을 요청하는 일
  문의가 필요하면 `docs/outreach/` 형식의 초안만 쓴다. 발송은 소유자가 한다.
- 게임 품질에 영향을 주는 네 권장안은 "가설"로 표시한다. 채택은 Fable 적대적 리뷰와 소유자 결정으로 정한다.
- 네 PR은 병합 전에 Fable ultracode 적대적 리뷰를 받는다(§7.4). 리뷰에서 확정된 결함은 네 브랜치에서 고친다.

## 4. 레인, 핫스팟, 훅 (원문: DEVELOPMENT-PLAN §7.6)
- **레인**: 파일 소유 구역이다. 네 레인 안의 파일만 자유롭게 만들고 고친다. 지금 네 레인은 **캐릭터(WP-18)**다.
  - 코드·설정
    - `unreal/Golmok/Source/Golmok/Characters/`
    - `Source/Golmok/Tests/GolmokCharacterRoster*.cpp`
    - `unreal/Golmok/Config/Golmok/characters.json`
  - 테스트
    - `tools/tests/test_ue_character_roster*.py`
    - `tools/tests/test_ue_config_characters.py`
    - `tools/tests/fixtures/ue/charactermath*`
  - 문서·이미지
    - `docs/design/character-*`, `docs/spec/characters*`
    - `docs/research/11-*`
    - `docs/plan/WP-18*`
    - `docs/runbooks/pc-verify-wp18*`
    - `docs/outreach/character-*`
    - `docs/images/characters/`
  - 새 레인은 소유자가 과제로 배정한다.
- **Claude(Fable) 레인**: `Source/Golmok/{Geo,Zones,Portals,Lighting,Debug,Photo,Audio,Player}/`, 그 밖의 `Tests/*`, 다른 `Config/Golmok/*.json`, `Content/Python/golmok/`. 이 파일들은 고치지 않는다. 필요하면 PR 설명이나 소유자를 통해 요청한다.
- **공유 핫스팟**
  - 코드·설정: `Player/GolmokCharacter.{h,cpp}`, `Player/GolmokPlayerController.{h,cpp}`, `GolmokGameMode.{h,cpp}`, `Golmok.Build.cs`, `Config/Default*.ini`, `tools/pyproject.toml`, `.github/workflows/ci.yml`, `tools/scripts/check_repo.py`, `.gitattributes`, `.gitignore`
  - 문서: `docs/plan/STATUS.md`, `docs/DECISIONS.md`, `docs/ROADMAP.md`, `docs/DEVELOPMENT-PLAN.md`, `CLAUDE.md`, `AGENTS.md`, `README.md`, `tools/README.md`
- **핫스팟 규칙**
  1. **먼저 피한다.** 네 폴더의 서브시스템, 엔진 델리게이트(예: `APlayerController::OnPossessedPawnChanged`), 네 콘솔 명령, 네 JSON 설정 파일로 해결할 수 있으면 핫스팟을 고치지 않는다.
  2. **못 피하면 훅으로 최소 수정한다.**
     - 기존 줄은 고치거나 옮기거나 다시 포맷하지 않는다. 새 줄만 더한다.
     - 새 줄은 파일이나 섹션의 끝에 표지로 감싼다: C++ `// [WP-18 hook] <이유>` ~ `// [/WP-18 hook]`. ini는 네 섹션을 파일 끝에 둔다. `Golmok.Build.cs`는 모듈 이름 한 줄과 이유 주석 한 줄이다.
     - 훅은 **별도 커밋**(`WP-18: hook <파일>`)으로 만든다.
  3. **공유 문서(STATUS, DECISIONS, ROADMAP, DEVELOPMENT-PLAN, CLAUDE.md, AGENTS.md)는 고치지 않는다.** 바꿀 내용은 네 WP 문서 끝의 **"병합 시 반영"** 절에 문안으로 둔다. 병합하는 Fable 세션이 옮긴다.
  4. **번호**(WP, V, D, research 번호)는 STATUS에 예약된 것만 쓴다. 지금 네 예약: WP-18(18a·18b), V-11, V-12, D-018, research/11. 더 필요하면 "병합 시 반영"에 예약 요청으로 적는다.

## 5. 브랜치, 커밋, PR, 동기화, 충돌 해결
- **작업 폴더**: `C:\Users\user\golmok` 체크아웃과 `.claude\worktrees\` 아래 폴더는 Claude 세션이 쓰는 중이다. 그 폴더의 브랜치를 바꾸거나 파일을 고치지 않는다. 너는 별도 worktree에서 일한다.
  ```
  git -C C:\Users\user\golmok fetch origin
  git -C C:\Users\user\golmok worktree add C:\Users\user\golmok-astra\<주제> -b astra/<wp>-<주제> origin/main
  ```
  클라우드에서 돌면 저장소를 clone해서 같은 브랜치 이름을 쓴다.
- **브랜치**: `astra/<wp>-<주제>`(예: `astra/wp-18-design`, `astra/wp-18a-roster`). WP 단계마다 브랜치와 PR을 하나씩 만든다. `claude/*`와 `pc/*`는 읽기만 한다.
- **커밋**
  - 작성자: `git -c user.name="ChatGPT Astra" -c user.email="astra@golmok.invalid" commit …`
  - 메시지: 접두어 `WP-NN:`. 마지막 줄에 `Agent: ChatGPT Astra`를 적는다.
  - 순서: ① 레인 파일 ② 훅 ③ 문서. 단계마다 커밋하고 push한다.
- **동기화**
  - 착수할 때와 PR을 올리기 전에 `git fetch origin`을 하고, 열린 브랜치가 같은 파일을 건드리는지 본다: `git diff --stat origin/main...origin/<브랜치>`. 겹치면 PR 설명에 적는다.
  - main을 따라갈 때는 `git merge origin/main`을 한다. push한 브랜치는 rebase나 force-push를 하지 않는다.
  - 리뷰를 요청하기 전에 main과 충돌이 없게 만든다.
- **충돌 해결**: 나중에 병합하는 쪽이 자기 브랜치에서 푼다.
  | 파일 | 해결 |
  |---|---|
  | 상대 레인 파일 | 레인 주인의 버전을 그대로 쓴다. 네 의도는 훅이나 후속 PR로 다시 넣는다 |
  | 핫스팟의 훅 블록 | 양쪽을 다 살린다. main 쪽 블록을 먼저 둔다 |
  | 공유 문서 | main 버전을 받는다. 네 "병합 시 반영" 문안은 네 WP 문서에 있으니 잃지 않는다 |
  | 생성물·픽스처 | 손으로 합치지 않고 생성기로 다시 만든다 |
  | 번호 | 먼저 병합된 쪽이 갖는다. 나중 쪽이 번호를 바꾼다 |
  - 해결한 뒤 §6 게이트를 다시 돌린다.
  - 해결 커밋 메시지는 `merge origin/main: <충돌 파일> — <해결 방법>`이다.
- **PR**: `main`으로 연다. 작업 중에는 초안 PR로 둔다. 설명에 적을 것:
  - 요약
  - 레인 파일 목록
  - 훅 목록(파일과 표지)
  - "병합 시 반영" 위치
  - 게이트 결과(명령과 통과 수)
  - 겹치는 브랜치
  - 소유자 결정 필요 항목
- **줄 끝**: `.gitattributes`가 `* text=auto`다. 이 PC는 `core.autocrlf=true`다. 줄 끝만 바뀐 파일(`git status`에는 보이고 `git diff`는 비어 있는 파일)은 `git checkout -- <파일>`로 되돌린다.

## 6. 검증 게이트
- **Python** (Windows에서는 `PYTHONUTF8=1`):
  ```
  cd tools && python -m venv .venv && .venv\Scripts\pip install -e ".[basemap,zone,mesh,splat,align,dev]"
  .venv\Scripts\ruff check . && .venv\Scripts\ruff format --check . && .venv\Scripts\pytest -q && .venv\Scripts\python scripts\check_repo.py
  ```
  - venv는 worktree마다 새로 만든다.
  - g++ 교차검증 테스트는 이 PC에 g++가 없어 건너뛴다. CI(ubuntu)가 돌린다.
  - PR의 GitHub Actions CI가 초록이어야 한다.
- **UE**(소유자 PC에서 돌 때, PowerShell)
  - 빌드: `.\tools\ue\build.ps1`
  - 헤드리스 자동화 테스트: `.\tools\ue\test.ps1 -SetupDevLevel`. 필터가 필요하면 `-Filter Golmok.Character`처럼 준다.
  - 새 worktree에는 마네킹을 `.\tools\ue\add-mannequin.ps1`로 복사한다. 마네킹은 git에 없다.
  - `test.ps1`은 경고가 있는 테스트를 `Succeeded: 0`처럼 보고할 수 있다. 판정은 테스트별 `Success` 열로 한다.
- **UE를 같이 쓰는 규칙**: 같은 PC에서 다른 Claude 세션이 UE를 돌릴 수 있다.
  - 에디터 GUI나 PIE를 띄우기 전에 `C:\Users\user\AppData\Local\Temp\claude\gui-foreground.lock` 파일을 확인한다. 한 줄 형식은 `<세션> <목적> <ISO 시각>`이다. 20분이 안 된 기록이 있으면 기다린다. 쓰는 동안 네 줄로 갱신하고, 끝나면 지운다.
  - 다른 UnrealEditor나 `-game` 프로세스가 돌 때는 fps를 측정하지 않는다.
  - 헤드리스 빌드와 테스트는 잠금 없이 돌려도 된다.
- **UE 코드 완료 표시**: GUI 검증이 필요한 항목은 PC 런북(`docs/runbooks/pc-verify-<wp>.md`)에 남긴다. 런북에는 불확실한 API 표를 둔다. 추측으로 쓴 엔진 API는 이 표에 적는다.

## 7. 조사·문서 규칙
- 라이선스, 약관, 법, 가격은 원문을 열어 핵심 문장을 짧게 인용하고 URL과 확인일을 적는다.
- 사실마다 확인 수준을 붙인다.
  - [확인]: 원문을 직접 열었다.
  - [2차]: 기사, 요약, 다른 세션의 기록을 옮겼다.
  - [미확인]: 확인하지 못했다.
  - [확인 필요]: 원문이 열리지 않았다.
  모델 기억은 [확인]이 아니다.
- **D-002(라이선스)**
  - 비상업(NC) 조건의 코드, 가중치, 에셋은 제품 파이프라인에 넣지 않는다. AGPL 도구도 넣지 않는다(예: Ultralytics, OpenMVS, OpenSplat).
  - Inria 3DGS 계열, MASt3R/DUSt3R, InsightFace 가중치 같은 비상업 코드·가중치도 넣지 않는다.
  - Fab EULA §6(a)와 UE EULA §6(c)에 따라 GPL, LGPL(동적 링크 제외), CC-BY-SA 코드·콘텐츠를 UE·Fab 콘텐츠와 결합하지 않는다.
  - CC-BY는 표기 의무가 있다. ND는 수정할 수 없다.
  - 사용 지역 제한 조항이 있으면 한국에서 쓸 수 있는지 확인한다.
  - 라이선스가 있는 새 의존성은 원문을 확인하고 D-002 표에 넣을 문안을 "병합 시 반영"에 적는다.
- **AI 관련**: Fab에서 "AI 사용 허용: 아니요"(NoAI)로 표시된 에셋과 그 스크린샷은 어떤 AI 도구의 입력으로도 쓰지 않는다. 약관(Fab EULA §6(b)(vii)·§16(l))보다 보수적인 프로젝트 규칙이다.
- **프라이버시**
  - 촬영 원본, 블러 전 이미지, 실존 인물이나 가게를 알아볼 수 있는 사진은 외부 서비스나 AI 도구에 올리지 않는다.
  - 모든 촬영 이미지는 RealityScan·Postshot 전에 `golmok-blur`를 거친다.
  - 원본 촬영물, `.ply`, RealityScan 프로젝트, 모델 가중치는 커밋하지 않는다.
- **상표·권리**
  - 실제 브랜드, 상호, 로고, 공공기관 캐릭터·상징, 실제 가게, 랜드마크 건물을 게임 콘텐츠의 이름, 의상, 소품에 쓰지 않는다(`docs/research/05-legal-policy.md` 상표·간판).
  - 실존 인물과 닮게 만들지 않는다.
- **에셋 커밋**: 이 저장소는 공개라서 Fab 에셋이나 외주 에셋 원본은 커밋하지 않는다(Fab EULA §5(a), 외주는 계약 조건).
- **글쓰기**
  - 문서는 한국어로, 짧고 구체적으로 쓴다.
  - 권장안은 하나로 정하고 이유를 적는다.
  - 확실하지 않으면 확실하지 않다고 쓴다.
  - 저장소 상대 링크는 실제로 있는 파일에만 건다(`check_repo.py`가 깨진 링크를 실패로 처리한다). 없는 파일이나 다른 브랜치 파일은 `코드 표기`로 쓴다.

## 8. 이미지와 바이너리
- `*.png`, `*.jpg`, `*.uasset`, `*.umap`, `*.fbx`, `*.glb`, `*.wav` 등은 Git LFS 대상이다(`.gitattributes`).
- `git lfs install`을 한 worktree에서 커밋하고, push 전에 `git lfs ls-files`에 그 파일이 있는지 확인한다.
- 문서용 이미지는 긴 변 1600 px 이하 JPG로 `docs/images/<주제>/`에 둔다.
- `.uasset`/`.umap`은 lockable이다. 에디터에서 만든 에셋을 커밋해야 하면 PR 설명에 적는다. 생성된 테스트 레벨(`L_ZoneTest*` 등)은 커밋하지 않는다.

## 9. 끝나면 소유자에게 보고
1. 결과물 위치: PR 링크, 브랜치, 마지막 커밋 SHA
2. 산출물별 상태: 완료 / 부분(빠진 것) / 미착수
3. 게이트 결과: pytest 통과 수, ruff, check_repo, CI, UE 빌드·테스트
4. 권장안 요약(항목마다 1줄)
5. 소유자 결정 필요 목록
6. [미확인]·[확인 필요]로 남은 항목
7. 겹친 브랜치와 충돌 해결 내역, 훅 목록
8. 과제 프롬프트와 다르게 한 것과 이유
9. 다음에 맡기면 좋을 과제
