# 런북: 사용자 Windows PC 셋업 → 1.0b/1.0c 검증 (로컬 Claude 세션용)

이 문서는 **사용자 PC에서 도는 Claude Code 세션**이 처음부터 끝까지 따라가는 작업 지시서다.

## 운영 규칙 (사용자 지시, 2026-09-24)
- **끝까지 스스로 진행한다.** 막히면 원인을 찾아 고치고 계속한다. 진행 상황은 짧게 보고한다.
- **되돌릴 수 없는 작업만 사용자에게 먼저 확인받는다.**
  - 결제·구독: Postshot Studio, 유료 플러그인, 클라우드 등
  - 라이선스·약관 동의: Epic, EgoBlur 모델, XGRIDS 등. 사용자 본인이 동의해야 한다.
  - 계정 로그인이나 자격 증명 입력
  - 파일·폴더 삭제, 기존 데이터 덮어쓰기
  - `main` 브랜치 push, PR 병합, force-push, 히스토리 재작성
  - 원본 촬영물(사진·영상)을 외부 서비스로 업로드하는 일(D-007)
  - OS 설정 변경 중 보안 관련 항목(방화벽, 실행 정책의 시스템 전체 변경 등)
- 그 밖의 작업(설치 명령 실행, 빌드, 코드 수정, 브랜치 커밋·push, 테스트)은 **확인 없이 진행**한다.
- 코드를 바꿨으면 작업 브랜치 `claude/golmok-phase-0-research-4kloq6`에 커밋·push한다. 진행 상황은 `docs/ROADMAP.md`에 반영한다.
- 규칙과 결정은 `CLAUDE.md`, `docs/DECISIONS.md`를 따른다.

## PC 사양 (D-006)
- CPU: Ryzen 5 7500F
- RAM: 32GB
- GPU: RTX 5060 8GB
- 저장장치: SSD 1TB(약 740GB 여유)
- OS: Windows 11 Home

## 단계

### 0. 저장소
```powershell
winget install --id Git.Git -e
winget install --id GitHub.GitLFS -e
git lfs install
git clone https://github.com/wooklym/golmok.git $HOME\golmok
cd $HOME\golmok
git checkout claude/golmok-phase-0-research-4kloq6
```
- 이미 클론이 있으면 `git fetch` 후 체크아웃한다.

### 1. Python 도구 (1.0c)
```powershell
winget install --id Python.Python.3.12 -e
winget install --id Gyan.FFmpeg -e
winget install --id OliverBetz.ExifTool -e
cd $HOME\golmok\tools
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[raw,heic,dev]"
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
pytest
```
- winget ID가 다르면 `winget search`로 찾는다.
- 완료 기준: `pytest` 전부 통과, `torch.cuda.is_available()`이 True.
- **EgoBlur 모델**: 사용자에게 요청한다. https://www.projectaria.com/tools/egoblur 에서 라이선스에 동의하고 Gen1 모델을 받는 일이다. 파일 위치는 `tools\models\ego_blur_face.jit`, `ego_blur_lp.jit`.

### 2. Unreal Engine (1.0b)
**사용자 작업**
- Epic Games Launcher 로그인
- UE **5.8** 설치
- Visual Studio 2026 설치 시 라이선스 동의

**Claude 작업**
- `winget install --id EpicGames.EpicGamesLauncher -e`
- Visual Studio 2026 Community 설치 명령 실행. 워크로드는 "C++를 사용한 게임 개발"(Microsoft.VisualStudio.Workload.NativeGame)과 Windows SDK다.
- 설치 경로 확인. 기본 경로가 아니면 `$env:UE_ROOT`를 설정한다.
- 빌드:
  ```powershell
  cd $HOME\golmok
  .\tools\ue\build.ps1
  ```
  - **컴파일 에러가 나면 C++ 코드를 고쳐 다시 빌드한다.** UE 5.8 API 변경 가능성이 있다. 특히 `UInputMappingContext::MapKey`, `UInputModifierNegate`를 확인한다.
- 에디터 실행: `.\tools\ue\open-editor.ps1`
- 테스트 레벨 생성: 에디터 Output Log(Python)에서 `import golmok.setup_dev_level as s; s.run()`을 실행한다.
  - 명령줄로 하려면 `UnrealEditor-Cmd.exe <uproject> -ExecutePythonScript="<path>"` 방식을 시도한다. 실패하면 사용자에게 에디터에서 한 줄 실행을 요청한다.
- 완료 기준:
  - L_Dev에서 PIE(Alt+P)로 걷기, 뛰기(Shift), 점프, 카메라 충돌이 동작한다.
  - `Saved\Logs\Golmok.log`에 에러가 없다.
  - 스크린샷 1장을 `docs/runbooks/`에 남긴다. 파일이 크면 남기지 않는다.
- 마네킹: Content Browser → Add Feature or Content Pack → Third Person을 추가한다. 에디터 GUI 작업이라 사용자 도움이 필요하면 요청한다. 추가된 에셋 경로가 `DefaultGame.ini`와 다르면 ini를 고친다.

### 3. 리허설 사진 점검 (가이드 §4-C)
- 사용자가 아이폰 리허설 사진 20장과 영상 1분을 PC로 옮긴다(원본 유지).
- 실행:
  ```powershell
  golmok-exif <사진폴더> --csv <폴더>\exif.csv
  golmok-blur <사진폴더> <사진폴더>_blurred --face-model tools\models\ego_blur_face.jit --lp-model tools\models\ego_blur_lp.jit
  golmok-frames <영상> <프레임폴더> --fps 2
  ```
- 확인할 것:
  - 셔터 1/200 이상 비율
  - 전부 메인 1x인지
  - 48MP인지
  - GPS가 있는지
  - **DNG 현상이 성공하는지**: `blur_log.csv`에 decode_error가 없어야 한다.
- DNG 현상에 실패하면 원인을 조사하고 대안을 구현한다. 예: 다른 현상 경로, HEIF Max 촬영으로 전환. 촬영 방식을 바꿔야 하면 사용자에게 제안한다.
- 결과를 `docs/captures/INDEX.md`와 `docs/ROADMAP.md`(1.0c, 1.0d)에 기록한다. **사진 자체는 커밋하지 않는다.**

### 4. 보고
- 단계별 결과, 고친 것, 남은 사용자 작업을 짧게 정리해 사용자에게 알린다.
- 다음 단계(1.0f 촬영, 1.2 베이스맵 빌더)로 넘어갈 준비가 됐는지도 함께 알린다.

### 5. 배경 베이스맵 (ROADMAP 1.2) — 2026-09-24 연남동으로 1회 완료(결과는 ROADMAP 1.2, D-012)
데이터는 git 밖에 둔다: `%USERPROFILE%\golmok_data\`(D: 드라이브가 없으면), 빌드 출력은 `%USERPROFILE%\golmok_basemap\<지역>`.

**사용자 작업**
- Claude가 조작하는 Chrome이 **이 PC의 Chrome**인지 확인한다(다른 PC의 Chrome이면 다운로드가 그 PC로 간다). 이 PC의 Chrome에 Claude in Chrome 확장을 설치한다.
- V-World, 국토정보플랫폼에 **로그인**한다.
- 국토정보플랫폼 다운로드 **신청서**(매 다운로드마다): 생년월일, 사용목적(예: 제작 및 활용 → 콘텐츠 제작), 상세용도(**15자 이내**, 예: "게임 배경 지형 텍스처 제작"), 사용자 준수사항 동의. 본인 명의라 사용자가 정하거나 Claude에게 입력을 맡긴다.
- 첫 다운로드 때 대용량 파일전송 프로그램 **INNORIX Agent**(`INNORIX-Agent.exe`, 서명: INNORIX, Seoul) 설치 허락. 다운로드 팝업(Chrome 별도 창)의 [전체 다운로드]·덮어쓰기 확인은 Claude가 누를 수 없으니 사용자가 누른다. **팝업이 열린 채 다른 신청을 하면 진행 중이던 전송이 끊긴다**(하나씩 받는다).

**데이터**
- **건물**: V-World → 공간정보 다운로드 → GIS건물통합정보(`dsId=18`) → 시·도 서울특별시, 구분 **전체데이터** → 최신 행의 [다운로드] → `AL_D010_11_<기준일>.zip`(약 130 MB). 같은 페이지의 "컬럼 정의서 다운로드"(xlsx, 로그인 불필요)도 받는다.
- **DEM**: 국토정보맵 → 공간정보받기 → 간편지도 검색 → 영역 → 사각형으로 지역을 그림 → **공개DEM** → 최신 연도 `서울 37608` → 다운로드. ⚠ 공개DEM은 **90 m 격자**(`37608.img`, EPSG:5179)뿐이다. 5 m는 목록에 없다(D-012, 결정 필요).
- **정사영상**: 같은 영역 → **정사영상** → 최신 연도 25 cm 도엽. 연남동 반경 1 km는 `37608077`·`37608078` 두 장(각 약 320 MB)이면 된다. 도엽 번호 = 1:5만 5자리 + 001~100(1'30" 격자, 북서에서 행 순서).
  - ⚠ TIFF에 **좌표 정보가 없다** → 아래 `georef-ortho`로 GeoTIFF를 만든다.

**Claude 작업**
```powershell
cd tools; .\.venv\Scripts\Activate.ps1          # 없으면: py -3.12 -m venv .venv; pip install -e ".[basemap,zone,dev]"
pytest -q
$D = "$HOME\golmok_data"
golmok-basemap inspect --buildings "$D\vworld\AL_D010_11_20260909\AL_D010_11_20260909.shp"
golmok-basemap georef-ortho "$D\ngii\ortho\raw\(B060)정사영상_2025_376080*.tif" --out-dir "$D\ngii\ortho" `
  --buildings "$D\vworld\AL_D010_11_20260909\AL_D010_11_20260909.shp"
golmok-basemap build --buildings "$D\vworld\AL_D010_11_20260909\AL_D010_11_20260909.shp" `
  --height-field A16 --floors-field A26 --usage-field A9 --id-field A1 `
  --dem "$D\ngii\dem\37608\37608.img" --ortho "$D\ngii\ortho\ortho_*.tif" `
  --center 37.5620,126.9250 --radius 1000 --out "$HOME\golmok_basemap\yeonnam"
```
- `georef-ortho` 출력에서 건물 윤곽 매칭 peak가 차순위보다 확실히 크고(1.3배 이상), 인접 도엽 겹침 매칭이 0.9 이상인지 본다. 아니면 도엽 중심 배치로 남는다(약 1~2 m 오차).
- 빌드 출력의 "건물 N동 (높이 추정 M동)"이 반경 1 km에서 수천 동인지 본다(연남동 9,447 / 4,258).
- UE 임포트(에디터 Python 또는 명령줄):
  ```powershell
  # 명령줄(창 없이): 스크립트가 끝나면 에디터가 종료된다
  UnrealEditor-Cmd.exe <uproject> -ExecutePythonScript=<import.py> -nullrhi -unattended
  ```
  `import golmok.basemap_import as b; b.run(r"<out>\yeonnam", level="/Game/Golmok/Maps/L_Basemap_Yeonnam")`
  - 로그 `glTF import mapping … M=((1,0,0),(0,-1,0),(0,0,1)) (fit error …)`: M이 이 값이면 북쪽 = UE −Y. fit error는 메시 전체 합계(cm)로 수십 이하면 된다.
  - 새 레벨에 조명과 지면 위 PlayerStart가 자동으로 들어간다. 다시 실행하면 이전 배경 액터를 지우고 새로 놓는다.
- GUI 에디터에서 틱마다 도는 스크립트는 `-ExecCmds="py <파일>"`로 실행한다(`-ExecutePythonScript`는 스크립트가 돌아오자마자 에디터를 닫는다). PIE 스크린샷은 `HighResShot`이 확실하다. 에디터가 뒤에 있으면 PIE fps가 8 정도로 제한되니 fps는 아래로 잰다.
- fps: `UnrealEditor.exe <uproject> /Game/Golmok/Maps/L_Basemap_Yeonnam -game -RenderOffscreen -ResX=1920 -ResY=1080 -csvCaptureFrames=1500 -ExitAfterCsvProfiling` → CSV는 `%LOCALAPPDATA%\UnrealEngine\5.8\Saved\Profiling\CSV\` → `golmok-perf <csv> --markdown`.
- 완료 기준:
  - L_Dev(또는 새 레벨)에서 배경 건물과 지형이 보인다.
  - 파사드 창 패턴이 보인다.
  - 캐릭터가 배경 지면 위를 걸을 수 있다.
  - fps와 스크린샷을 ROADMAP 1.2에 기록한다. 정사영상이 보이는 스크린샷은 법률 확인 전까지 저장소에 올리지 않는다(D-012).
