# Golmok (골목)

[![CI](https://github.com/wooklym/golmok/actions/workflows/ci.yml/badge.svg)](https://github.com/wooklym/golmok/actions/workflows/ci.yml)

실제 서울 골목을 사진·영상으로 찍어 3D로 재구성하고, 그 안을 걷고 뛰며 건물 내부까지 들어가 볼 수 있는 게임.

- 설계·결정·로드맵: [`docs/`](docs/README.md) (시작점: [ROADMAP](docs/ROADMAP.md), [DECISIONS](docs/DECISIONS.md), [개발 전체 과정](docs/DEVELOPMENT-PLAN.md), [진행 상태](docs/plan/STATUS.md))
- 엔진: Unreal Engine 5.8 (C++ + Unreal Python), 고사양 Windows PC
- 촬영 가이드: [`docs/capture/01-alley-capture-guide.md`](docs/capture/01-alley-capture-guide.md)

## 저장소 구조

```
docs/                 조사·설계·결정·촬영 가이드
unreal/Golmok/        UE 5.8 게임 프로젝트
  Source/Golmok/      C++ (캐릭터, 게임모드 …)
  Content/Python/     에디터 자동화 스크립트
tools/                Python 도구 (EXIF 점검, 프레임 추출, 얼굴·번호판 블러) + UE 빌드 스크립트
```

## 처음 설정 (Windows)

1. 설치: **UE 5.8**(Epic Games Launcher), **Visual Studio 2026**("C++를 사용한 게임 개발" 워크로드), **Git + Git LFS**
2. 저장소 받기
   ```powershell
   git lfs install
   git clone https://github.com/wooklym/golmok.git
   cd golmok
   ```
3. C++ 빌드 후 에디터 열기 (엔진이 기본 경로가 아니면 `$env:UE_ROOT = "D:\Epic\UE_5.8"`)
   ```powershell
   .\tools\ue\build.ps1
   .\tools\ue\open-editor.ps1
   ```
   PowerShell 실행 정책 오류가 나면: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
4. 테스트 레벨 만들기: 에디터 하단 Output Log를 **Python** 모드로 바꾸고
   ```python
   import golmok.setup_dev_level as s; s.run()
   ```
5. **플레이(Alt+P)**: WASD 이동, 마우스 시점, Space 점프, **Shift 누르고 있으면 달리기**. 게임패드도 된다.
6. 캐릭터 외형(마네킹): `.\tools\ue\add-mannequin.ps1`. 에디터의 Content Browser → Add → **Add Feature or Content Pack → Third Person**이 복사하는 마네킹 파일(`/Game/Characters`)과 같다. 없으면 캡슐로 보인다.
   - 경로가 다르면 `unreal/Golmok/Config/DefaultGame.ini`의 `CharacterMeshPath`, `AnimClassPath`를 고친다.
   - 마네킹과 `L_Dev.umap`은 스크립트로 다시 만들 수 있어 git에 넣지 않는다.
7. 이동 자동 테스트(창 없이): `.\tools\ue\test.ps1` (L_Dev가 없으면 `-SetupDevLevel`). 걷기·뛰기·점프·마우스 시점·골목 벽 카메라 충돌을 실제 키 입력으로 확인한다(`Golmok.Player.Movement`).

Python 도구 설정은 [`tools/README.md`](tools/README.md)를 본다.

## 원칙
- 게임 퀄리티 최우선(D-003~). 로직은 C++, 에디터 작업은 Unreal Python, Blueprint 최소화.
- `.uasset`/`.umap`은 Git LFS(lockable).
- **원본 사진·영상·.ply·RealityScan 프로젝트는 git에 넣지 않는다.** 재구성 전에 반드시 얼굴·번호판 블러(`golmok-blur`).
