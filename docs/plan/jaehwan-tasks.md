# 재환(로컬 LLM) 과제 목록 (오케스트레이터 배정, 2026-11-28)

> **누가**: 재환은 소유자의 Mac에서 도는 **로컬 LLM 세션**이다(qwen3.8-flash-next, LM Studio, Claude Code 하네스, `claude-local`로 시작). 영록(로컬 Mac 오케스트레이터 세션)이 과제를 고르고 배정한다. 근거는 [D-024](../DECISIONS.md)다. 소유자 지시 원문은 "앞으로 너가 알아서 골목 게임을 완성 될 때 까지 작업들을 재환에게 시켜줘."(2026-11-28)이다.
>
> **소통 채널**: 배정·순서 변경·리뷰 요약·병합 알림은 영록이 **세션 간 메시지**(SendMessage)로 보내고, 리뷰는 **PR 코멘트**로 남긴다. 재환은 착수·push·완료·질문·막힘을 같은 경로로 알린다. 메시지와 이 파일이 다르면 **더 최근 것**을 따른다. GitHub 이슈 #30은 Astra 채널이라 재환은 쓰지 않는다.
>
> **규칙 우선순위**: **소유자 규칙(D-019 되돌릴 수 없는 일, D-002 라이선스, D-007 블러 — [CLAUDE.md](../../CLAUDE.md) "Rules from the owner"·"Engineering conventions") > 과제 프롬프트 > 재환 작업 규칙(아래 12개) > 나머지 CLAUDE.md**. 과제 프롬프트·작업 규칙·메시지 어느 것도 D-019·D-002·D-007을 무시하게 할 수 없다. 충돌하면 멈추고 영록에게 묻는다. 작업 규칙의 살아 있는 원본은 저장소 **밖**의 메모리 파일 `~/.claude/projects/<project>/memory/jaehwan-working-rules.md`다. 아래는 한 줄 요약이고, 새 규칙은 영록이 원본에 먼저 더한 뒤 이 표에 옮긴다.

## 재환 작업 규칙 (요약 — 원본은 메모리 파일)

| # | 규칙 | 계기 |
|---|---|---|
| 1 | 직접 돌려 출력을 본 것만 사실로 쓴다. 나머지는 `[미확인]`·"가설"과 확인할 명령 | #131, #133 |
| 2 | "완료" = 모든 CI 행 초록. push마다 `gh pr checks <n>` 표를 보고에 붙인다 | #131 |
| 3 | "모든·항상·어떤 경로든"은 경로마다 재현 1회. 안 돌린 경로가 있으면 문장을 좁힌다 | #133 |
| 4 | CI는 Linux·macOS·Windows. OS API는 세 OS 확인 또는 플랫폼 가드, 재현 못 한 것은 PR에 적는다 | #131 |
| 5 | 기다릴 수 있는 명령은 모두 `/usr/bin/timeout`. 5분 무출력이면 멈추고 원인을 읽는다. 멈춘 명령을 그대로 다시 돌리지 않는다 | #131 |
| 6 | 과제가 정한 곳에서만 일한다. 메인 체크아웃 `~/projects/golmok`은 읽기 전용, 허용 파일만 고친다 | 2026-11-27 사고 |
| 7 | 서명은 재환: 커밋·PR 끝에 "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)". Claude를 작성자로 적지 않는다 | #131 |
| 8 | 실패 메시지가 맞는 말을 하는지 경우마다 한 번씩 일으켜 읽는다 | #133 |
| 9 | 링크는 클릭되고, 그 파일 위치에서 풀려야 한다 | #133 |
| 10 | 보고의 숫자는 명령 출력에서 복사한다(`grep -c`·`wc -l`). 실행마다 로그 파일·종료 코드. 증거는 병합 알림까지 임시 폴더에 둔다 | #134, #135 |
| 11 | 간헐 실패는 측정 전에 "일회성"이 아니다. 브랜치와 `origin/main`에서 각각 N ≥ 8회 | #134 |
| 12 | 게시한 글을 한 번 읽는다: `gh pr view <n> --json body --jq .body`에서 자리표시·빈 칸·깨진 표 검사 | #135 |

## 상시 규칙

- **작업 위치**: worktree `~/projects/golmok-jaehwan`(아래 `$W`)에서만 일한다. 과제마다 `git -C $W fetch origin` 뒤 `git -C $W switch -c local/jaehwan-<주제> origin/main`. 메인 체크아웃·`.claude/worktrees/`·다른 사람 브랜치는 읽기만 한다(규칙 6). 메인 체크아웃의 git 밖 UE 자료(마네킹·L_Dev 등)는 스크립트로 `$W`에서 다시 만든다.
- **허용 파일**: 과제 행의 "허용 파일"만 고친다. 그 밖의 파일이 바뀌면 되돌리고 PR에 적는다. UE 실행 뒤에는 `git -C $W status --porcelain`이 허용 파일만 보여야 한다(쿡·임포트가 만든 `.uasset`·`M_ZoneScan*`은 커밋하지 않는다).
- **금지**: 병합·`main` push·force-push·rebase·브랜치/태그 삭제, 메인 체크아웃에서 쓰기·패키지·`build/` 삭제, 공유 문서 수정(STATUS·DECISIONS·ROADMAP·DEVELOPMENT-PLAN·CLAUDE.md·AGENTS.md·README.md·tools/README.md — 문안이 필요하면 PR 본문 "병합 시 반영"에), Astra 레인 파일([DEVELOPMENT-PLAN §7.6](../DEVELOPMENT-PLAN.md) 표: `Source/Golmok/Characters/`, 오디오 레인 등), 핫스팟은 과제가 허용한 `// [WP-NN hook]` 블록으로만(별도 커밋), 지출·계정·약관 동의·외부 발송·시스템 보안 설정 변경(방화벽·화면 기록 권한 등은 소유자), `sudo`, LFS 에셋·데이터 삭제, 게임 설계·룩·조작감 판정.
- **GPU·GUI 공유**: UE 에디터 GUI·PIE·`-game`·패키지 실행 전에 `"$TMPDIR/claude/gui-foreground.lock"`을 확인하고 잡는다([mac-setup §3](../runbooks/mac-setup.md) 표의 규칙). 영록이 성능을 재는 동안에는 빌드·쿡·셰이더 컴파일을 하지 않는다. 두 UBT 빌드가 동시에 돌 때 서로 기다리는지·느려지는지는 [미확인]이다. 재환의 추론도 같은 GPU·통합 메모리를 쓰므로 **재환이 잰 fps·GPU ms는 판정 근거가 아니다**. 수치를 적을 때는 LM Studio 모델이 로드돼 있었는지 함께 적는다.
- **패키지 출력**: `GOLMOK_PKG_DIR`는 2026-11-28 현재 비어 있고 `package.sh` 기본값은 `<worktree>/build/Mac`이다. 재환은 항상 `--out-dir "$W/build/Mac"`를 명시한다.
- **증거**: 로그·재현 스크립트·출력은 `$TMPDIR/jaehwan/<과제 id>/`에 두고 병합 알림까지 지우지 않는다(규칙 10).
- **PR**: 제목 `J-NN: <요약>`. 본문 = 요약, 바뀐 파일, 실행한 명령과 출력(복사), 남은 `[미확인]`, "병합 시 반영"(공유 문서 문안이 있으면), **"제출 전 점검표"**(규칙 1~12 한 줄씩 — 한 일과 증거, 또는 "해당 없음"과 이유), 끝 줄 서명(규칙 7). 점검표가 없으면 리뷰를 시작하지 않는다.
- **완료 보고**: CI 모든 행 초록 뒤에만(`gh pr checks <n>` 표, 규칙 2). 게시 뒤 본문을 다시 읽는다(규칙 12).
- **병합하지 않는다.** 병합은 영록이 한다.
- **`py` 뒤에는 `QUIT_EDITOR`**: 창 없는 에디터(`UnrealEditor-Cmd … -nullrhi`)에 `-ExecCmds="py …"`를 줄 때 끝 명령은 `QUIT_EDITOR`다. `Quit`로는 스크립트가 끝나도 에디터가 나가지 않는다(J-12b: 약 13 s에 스크립트가 끝났지만 1800 s 타임아웃 rc 124). 근거 [pc-setup.md](../runbooks/pc-setup.md) §2 "GUI 없이 하는 방법"의 창 없는 에디터 줄.
- **Mac 에디터 로그는 `~/Library/Logs/Unreal Engine/GolmokEditor/`**: 프로젝트 로그는 그 폴더의 `Golmok.log`다. `<project>/Saved/Logs/`는 2026-11-28 현재 `$W`에도 메인 체크아웃에도 없다. 에디터를 다시 띄우면 이전 로그는 같은 폴더의 `Golmok-backup-<시각>.log`가 되므로, 실행 직후 `Golmok.log`를 `$E`에 복사한 뒤 `grep`한다. `Saved/Automation/Report/index.json`은 예전처럼 프로젝트 아래에 생긴다([mac-setup §8 #14](../runbooks/mac-setup.md)).
- **상대 경로 명령은 `cd "$W" &&`로 시작**: 셸의 기본 cwd는 메인 체크아웃이다. `./tools/ue/…`·`unreal/Golmok/…`처럼 상대 경로를 쓰는 명령은 매번 `cd "$W" && …`로 시작한다(규칙 6).
- **커밋 작성자**: 커밋마다 `git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit …`. `git config`에 저장하지 않는다(메인 체크아웃과 다른 세션이 같은 설정을 읽는다).
- **명령마다 로그+exit**: 명령마다 `> $E/<이름>.log 2>&1; echo $? > $E/<이름>.rc`, 돌린 명령 원문은 `$E/commands.txt`에 한 줄씩 더한다. 다음 실행이 덮어쓰는 결과물(`Saved/Automation/Report/index.json`, 에디터 `Golmok.log` 등)은 실행 직후 `$E`에 사본을 둔다(규칙 10).

## 리뷰·병합 절차

1. 재환이 PR을 열고 세션 메시지로 알린다.
2. 영록이 Opus 서브에이전트로 **적대적 리뷰를 재현으로** 한다(D-020·D-024; 영록 세션 자체의 모델은 D-024 "정직한 기록"): 점검표를 믿지 않고 PR의 명령을 다시 돌려 숫자·경로·실패 메시지를 대조한다. 리뷰 코멘트 id는 `R<PR 번호>`, 항목은 `R<PR>-n`, 등급 (A) 병합 전 필수 · (B) 이번 PR 권장 · (C) 이월. 실수마다 **작업 규칙 번호**를 적고 반복인지 밝힌다. 새 종류의 실수면 영록이 메모리 파일에 규칙을 더하고 재환에게 알린다.
3. 재환이 같은 브랜치에서 고치고, 답글에 고친 항목의 규칙 번호를 적는다.
4. (A) 0·CI 초록·충돌 없음이면 영록(현재 Fable 5.2 세션 — D-022 ⑨와 같은 D-020 편차, 소유자가 바로잡을 수 있다)이 merge commit으로 병합한다. 병합 커밋 본문에 작성자(재환, 로컬 LLM)와 리뷰 id(예: R135)를 적는다. 되돌릴 수 없는 일(D-019)이 얽힌 PR만 소유자 승인 뒤 병합한다.
5. 병합 뒤 영록이 공유 문서(STATUS "병행 트랙 — 재환", 해당 런북 결과 칸, 필요하면 DECISIONS)를 고치고, 이 파일의 "완료" 표에 한 줄을 옮긴 뒤 다음 과제를 배정한다.

## 완료

| id | 과제 | PR · 병합 커밋 | 리뷰 |
|---|---|---|---|
| J-01 | 웹 뷰어 macOS 검증·README, 준비 줄 stdout 버퍼링 회귀 테스트(스레드+큐), 서버 바인딩 `getfqdn` 지연 우회 | [#131](https://github.com/wooklym/golmok/pull/131) · `7686f3b` | R131(2회 보류: 규칙 1·2·4·5·7) |
| J-02 | 스모크 준비 대기 견고화(`PYTHONUNBUFFERED`·30 s·조기 종료 실패), 기동 실패 시 서버 누수 수정 | [#133](https://github.com/wooklym/golmok/pull/133) · `91d8b70` | R133(1회 보류: 규칙 1·3·8·9) |
| J-03 | 스모크 신호 처리 — 정리 네트를 spawn 직후로, SIGINT·SIGTERM·SIGHUP 핸들러 | [#134](https://github.com/wooklym/golmok/pull/134) · `9ac5cbe` | R134(첫 제출 병합; 규칙 10·11 추가) |
| J-04 | 스모크 간헐 실패(ERR_CONNECTION_RESET) 원인 수정 — accept 큐 백로그 5 → 128 | [#135](https://github.com/wooklym/golmok/pull/135) · `6a1a28e` | R135(첫 제출 병합; 규칙 12 추가) |
| J-05 | 뷰어 정리 — 테스트 BrokenPipeError 잡음 제거, 스모크 실패 덤프를 `finally`로, `somaxconn` 주석 | [#136](https://github.com/wooklym/golmok/pull/136) · `a66d615` | R136 |
| J-12 | **관문**: 재환 worktree UE 빌드(`origin/main` `6a1a28e` 새 체크아웃, 로컬 우회 없음) — `build.sh` rc 0(액션 57, 34.35 s, error 줄 0)·`add-mannequin.sh` rc 0·`test.sh --setup-dev-level` rc 0, 39개 상태 Success(Failed 0·Not run 0, `succeeded` 22 + `succeededWithWarnings` 17). **39 중 9는 skip**(아래 J-12 "결과") | [#138](https://github.com/wooklym/golmok/pull/138) · `ee3ef0e` | R138 |
| J-12b | 합성 zone 헤드리스 생성(`QUIT_EDITOR`, rc 0, 14 s) 뒤 `test.sh` rc 0 — 39 Success(`succeeded` 20 + `succeededWithWarnings` 19), zone 계열 skip 0, 남은 skip은 Weather.Runtime·Animation.GaspSmoke(아래 J-12b "결과") | PR 없음(메시지 보고) | 영록이 보고 파일을 읽어 확인 |

**진행 중**

| id | 과제 | 브랜치 | 허용 파일 |
|---|---|---|---|
| J-13 | 39 중 "Warning 있는 성공" 분류(V-19 §4-3) — [#139](https://github.com/wooklym/golmok/pull/139) 리뷰 대기 | `local/jaehwan-j13-warnings` | mac-setup §9 §4-3 행 메모 칸 |
| J-14 | `DEVELOPER_DIR` 전달 확인(§8 #8) — 스텁 pytest (J-13 뒤) | `local/jaehwan-j14-developer-dir` | `tools/tests/test_ue_mac_scripts.py`, mac-setup §8 #8 칸 |

**다음**: J-13 → J-14 → J-06~J-11(UE 빌드 없는 도구·CI)·J-34 → J-15~J-23(J-12b가 풀었다: J-17·J-18·J-20) → 설계 선행 J-24~J-33.

## 백로그 (의존 순서)

순서 원칙: ① UE 빌드가 필요 없는 도구·테스트·CI 일 → ② 재환 worktree의 UE 빌드를 세우고 증명하는 **관문 J-12·J-12b**(빌드·39 테스트, 합성 zone으로 skip 제거) → ③ 열린 카드의 헤드리스 UE 단계와 [미확인] 행 → ④ Claude 레인 코드 후속. **설계 선행** 표시 과제는 영록(Opus)이 짧은 설계 메모(파일·방법·완료 기준)를 이 파일의 해당 행 아래 또는 배정 메시지로 먼저 쓴 뒤에만 배정한다. 크기: S ≤ 반나절, M ≤ 하루, L > 하루.

| id | 과제 | 선행 | 크기 | 설계 선행 |
|---|---|---|---|---|
| J-06 | add-gasp 편집기 가드 테스트의 환경 의존 제거 | J-05 병합 | S | — |
| J-07 | `ruff check` E501 잔여 확인과 WP-21 후속 6 닫기 근거 | 없음 | S | — |
| J-08 | rawpy arm64 휠 설치·`rawpy.flags` 확인(§8 #24 rawpy 절반) | 없음 | S | — |
| J-09 | 확인된 §8 행의 `[미확인]` 주석 정리(셸·geo 테스트) | 없음 | S | — |
| J-10 | CI shellcheck 잡 | 설계 메모 | M | **설계 선행** |
| J-11 | CI 뷰어 `npm test` 잡 | 설계 메모 | M | **설계 선행** |
| J-15 | worktree 패키지로 §8 #10·#11(읽기)·#12·#13 확인 | J-12 | M | — |
| J-16 | `_pure.py` Mac 경로 가정·`package.sh` 주석을 J-15 실측으로 정리 | J-15 | S–M | — |
| J-17 | V-17 §0 헤드리스 Mac 부분 선행(GeoMath·Character 훅 컴파일·IndexParse·SharedInterior·Save.RoundTrip 닫기·Weather.Runtime) | J-12b | S | — |
| J-18 | V-17 §3 Full Precision UV 헤드리스 + WP-06 `_import_moved` 정리 경고(mac-recon #23) | J-12b | M | **준비 메모** |
| J-19 | V-17 §5 패키지 quinn 전환 로그 확인 | J-15 | S | — |
| J-20 | V-16 §1·§3 헤드리스 Mac 부분 선행(`Golmok.Weather`·`Golmok.Save`, 에셋 전 기준선) | J-12b | S | — |
| J-21 | WP-16a 불확실 API 표 §12의 컴파일·심볼 행 | J-12 | S | — |
| J-22 | V-16 §11 Mac 패키지 명령 이식(에셋 전 기대 결과) | J-15, J-20 | M | — |
| J-23 | 19b A1 ① 회귀 헤드리스(GASP 없이) | J-12 | S | — |
| J-24 | V-08b §9-1·§9-2 `locomotion_metrics.py` 순수 지표 + 합성 테스트 | 설계 메모 | M | **설계 선행** |
| J-25 | V-16 §2a MPC 헤드리스 생성 시험 | J-20, 설계 메모 | S | **설계 선행** |
| J-26 | V-18 §0·§1 헤드리스(8 WAV 재임포트, 커밋 없음) | J-12, 설계 메모 | S | **설계 선행** |
| J-27 | V-05 S12 `run_game_perf.sh` Mac 도구 경로 점검(성능 아님) | J-15, 설계 메모 | M | **설계 선행** |
| J-28 | CI `swift build`(golmok-objcap, macos-latest) | 설계 메모 | S–M | **설계 선행** |
| J-29 | 크래시 리포트 업로드 끄기 훅(WP-21 후속 5) | 설계 메모(키 결정) | S | **설계 선행** |
| J-30 | COLMAP 미터·ENU 정합 → 메시·splat 좌표 공유(공개 데이터, WP-21 후속 4) | 설계 메모 | M–L | **설계 선행** |
| J-31a | 입력 드라이버 키 타임라인 파서(순수 Python + pytest) | Opus B1 설계 메모 | S | **설계 선행** |
| J-31b | 헤드리스 자동화 1개 "W 3 s → 캡슐 이동 거리"(측정용 주입 경로는 Opus가 구현) | J-31a, Opus 주입 구현 | S | **설계 선행** |
| J-32 | Cesium 활성 사본에서 mac-recon #15·#16(게임 타깃 빌드·`test.sh` 영향) | WP-21 후속 1 결정, 설계 메모 | M | **설계 선행** |
| J-33 | avfoundation 60 fps 녹화 시험(§8 #25) | 소유자 화면 기록 권한, 설계 메모 | S | **설계 선행** |
| J-34 | `test.sh`·`add-gasp.sh` 오류 문구의 로그 경로를 Mac 실제 경로로 | 없음 | S | — |

J-12·J-12b는 끝났고(위 "완료"), J-13·J-14는 진행 중이다(위 "진행 중"). 아래 상세 절은 그대로 둔다.

### 과제 상세

공통 표기: `W="$HOME/projects/golmok-jaehwan"`, `E="$TMPDIR/jaehwan/<id>"`(경로는 [mac-setup §0](../runbooks/mac-setup.md) "경로 표기"처럼 `~` 기준으로 적는다 — 공개 저장소에 사용자 이름이 든 절대 경로를 쓰지 않는다). 파이썬 게이트 = `cd $W/tools && source .venv/bin/activate && ruff check . && ruff format --check . && pytest -q && python scripts/check_repo.py`(worktree 안의 venv; 없으면 `uv venv` + `uv pip install -e ".[basemap,zone,mesh,splat,align,dev]"`). UE 명령은 모두 `/usr/bin/timeout`으로 감싼다(빌드 1800 s, 테스트 2700 s, 패키지 5400 s 이내 — 넘으면 규칙 5).

#### J-06 add-gasp 편집기 가드 테스트의 환경 의존 제거
- **출처**: [WP-21](WP-21-mac-recon-pipeline.md) "남은 작업" 6과 같은 문서 검사 절(편집기가 떠 있으면 add-gasp 테스트 4건이 "close the Unreal Editor first"로 실패). 가드는 `tools/ue/add-gasp.sh:62-74`(`ps -axo pid=,comm=`), 테스트는 `tools/tests/test_ue_mac_scripts.py:454-588`.
- **할 일**: `gasp_env` 픽스처가 실제 프로세스 목록 대신 가짜 `ps`(픽스처의 `PATH` 앞 스텁)를 쓰게 한다. 양성 사례 `test_add_gasp_refuses_while_an_editor_runs`(:573)는 지금처럼 실제 프로세스로 남기거나, 스텁이 그 PID를 보고하게 바꾸되 의미(가드가 막는다)를 유지한다.
- **허용 파일**: `tools/tests/test_ue_mac_scripts.py`. 스텁만으로 안 되면 이유를 PR에 적고 영록에게 묻는다(`add-gasp.sh`는 그 뒤에만).
- **완료 기준**: (a) 수정 전 재현 — `$E/fake/Golmok.uproject.d/UnrealEditor` → `sleep` 심볼릭 링크를 `sleep 600`으로 띄운 채 `pytest -q tests/test_ue_mac_scripts.py -k add_gasp` → 실패 수를 `grep -c` 출력으로. (b) 수정 뒤 같은 더미 프로세스가 떠 있어도 0 실패, 더미가 없을 때도 0 실패. (c) 양성 사례가 여전히 `close the Unreal Editor first (running: <pid>` 를 단언. (d) 파이썬 게이트, CI 모든 행 초록(규칙 2·4 — Windows 행은 이 테스트를 어떻게 건너뛰는지 확인해 적는다).
- **왜 재환 / 위험**: on/off 재현으로 끝나는 좁은 테스트 일(J-04 방식). 위험: 스텁이 가드 자체를 무력화해 양성 사례까지 통과시키는 것 — (c)로 막는다.

#### J-07 `ruff check` E501 잔여 확인과 WP-21 후속 6 닫기 근거
- **출처**: WP-21 검사 절("E501 1건 `test_ue_mac_scripts.py:352`"). 2026-11-28 조사에서 main `6a1a28e`의 `ruff check .`가 "All checks passed"였다는 보고가 있다 — 재환이 다시 확인한다.
- **할 일**: `origin/main`에서 `ruff check .` 출력과 `git log -L352,352:tools/tests/test_ue_mac_scripts.py --oneline | head`로 언제 고쳐졌는지 찾는다. 남아 있으면 그 줄만 고친다.
- **허용 파일**: `tools/tests/test_ue_mac_scripts.py`(E501 줄만). 이미 고쳐졌으면 코드 변경 없이 J-06 PR 본문에 출력만 붙인다(PR을 따로 만들지 않는다).
- **완료 기준**: `ruff check .` 출력 원문, 고친 커밋 SHA. 영록이 WP-21 후속 6을 닫는다.
- **왜 재환 / 위험**: 명령 하나로 끝난다. 위험: 기억으로 "이미 고쳐짐"이라고 쓰는 것(규칙 1).

#### J-08 rawpy arm64 휠 설치·`rawpy.flags` 확인
- **출처**: [mac-setup §8](../runbooks/mac-setup.md) #24(rawpy arm64 휠), D-022 "이력"(D-011의 `rawpy.flags` 확인을 Mac arm64 휠에서 다시 한다 [미확인]), `tools/pyproject.toml`의 `raw` extra.
- **할 일**: `$W/tools`의 별도 venv에 `/usr/bin/timeout 600 uv pip install -v --only-binary rawpy -e ".[raw]" 2>&1 | tee $E/install.log` — `--only-binary rawpy`라서 맞는 휠이 없으면 소스 빌드로 넘어가지 않고 **오류로 끝난다**(그러면 그 오류 줄을 보고하고 멈춘다; 빌드 도구 설치·플래그 제거 금지). 성공하면 `grep -i -E 'rawpy.*\.whl' $E/install.log`, `uv pip show -f rawpy | grep -i -E 'whl|\.so'`, `python -c "import rawpy,os;print(rawpy.__file__)"`로 찾은 확장 모듈(`_rawpy*.so`)에 `file`, 그다음 `python -c "import rawpy, platform; print(rawpy.__version__, platform.machine()); print(rawpy.flags)"`.
- **허용 파일**: `docs/runbooks/mac-setup.md` §8 #24 "확인 결과" 칸의 **rawpy 절반만**(EgoBlur MPS 절반은 그대로 비운다).
- **완료 기준**: 설치 명령 종료 코드, 로그의 휠 파일 이름 줄 원문(`grep` 출력), 확장 모듈 `file` 출력(`arm64` 포함 여부), `rawpy.flags` 출력 원문을 칸과 PR에. `--only-binary` 오류로 끝나면 그 오류 원문만 적고 "arm64 휠 없음(이 명령·날짜 기준)"으로 좁혀 쓴다(규칙 3).
- **왜 재환 / 위험**: 명령 두 개로 판정된다. MPS 절반은 EgoBlur 모델 동의(소유자)가 필요해 재환 일이 아니다.

#### J-09 확인된 §8 행의 `[미확인]` 주석 정리
- **출처**: mac-setup §8 #1·#2(엔진 루트·`-Cmd` 위치 확인됨), #5(`test.sh`의 `-nullrhi` 확인됨 — **`add-gasp.sh`는 [미확인] 그대로**), §9 FMA 행(`MacToolChain.cs:209`). 대상 주석: `tools/ue/common.sh:4`, `:13`, `:25`, `:43`의 `test.sh` 부분, `tools/ue/test.sh:6`, `tools/tests/test_ue_geo_math.py:79`.
- **할 일**: 확인된 내용만 주석을 "확인(2026-11-27, mac-setup §8 #n)"으로 바꾼다. `add-gasp.sh:24`·`package.sh:26`·`_pure.py`는 건드리지 않는다(아직 미확인 — J-15·J-16).
- **허용 파일**: `tools/ue/common.sh`, `tools/ue/test.sh`, `tools/tests/test_ue_geo_math.py`(주석 줄만).
- **완료 기준**: 바꾼 줄마다 PR 표에 "줄 → 근거 §8 행/파일:줄". `pytest -q tests/test_ue_mac_scripts.py tests/test_ue_python_spike_runner.py tests/test_ue_geo_math.py`(`test_ue_mac_scripts.py:46`은 주석을 지우고 단언한다) + 파이썬 게이트 + CI 초록. `bash -n tools/ue/*.sh`.
- **왜 재환 / 위험**: 근거 대조만 하는 일. 위험: 아직 미확인인 것(#5의 add-gasp 절반)까지 지우는 것 — 규칙 1.

#### J-10 CI shellcheck 잡 — 설계 선행
- **출처**: 2026-11-28 코드 조사(CI `.github/workflows/ci.yml`에 셸 린트 없음, 이 Mac에 shellcheck 없음; 기존 억제 `install-recon-tools.sh:106`·`add-gasp.sh:116`·`test.sh:36`).
- **설계 메모가 정할 것(영록)**: 심각도(`-S warning` 등), `-s bash`, 대상(`tools/ue/*.sh`·`tools/mac/*.sh`), 찾은 결함을 고칠지 억제할지, 러너에 shellcheck가 있는지 [미확인]·로컬 설치 방법 [미확인].
- **허용 파일**: `.github/workflows/ci.yml`(핫스팟 — `# [WP-20 hook]` 블록, 별도 커밋), 설계가 허용한 `.sh` 줄.
- **완료 기준**: 새 CI 행 초록 + 일부러 깨뜨린 커밋 1개에서 그 행이 빨강(그 커밋은 되돌리는 커밋으로 원복, force-push 금지).
- **왜 재환 / 위험**: 명령으로 판정되지만 핫스팟·정책 선택이 있어 설계가 먼저다.

#### J-11 CI 뷰어 `npm test` 잡 — 설계 선행
- **출처**: STATUS WP-11 행("CI에는 `npm test` 잡 없음(로컬 게이트)"), `.gitignore`의 `tools/viewer/package-lock.json`(잠금 파일을 무시한다 — `npm ci` 불가), J-01~J-04의 스모크 간헐 실패 이력.
- **설계 메모가 정할 것**: OS 행, Playwright Chromium 캐시, 타임아웃, 잠금 파일 정책(무시 규칙을 바꿀지 — `.gitignore`는 공유 파일), 실패 시 재시도 금지 여부.
- **허용 파일**: `ci.yml` 훅 블록, 설계가 정한 파일.
- **완료 기준**: CI 같은 커밋 재실행 N ≥ 8회 전부 초록(규칙 11), 실행 시간 표.
- **왜 재환 / 위험**: 재환이 이 스모크를 가장 잘 안다. 위험: 간헐 실패가 CI를 빨갛게 만드는 것.

#### J-12 관문: 재환 worktree UE 빌드 (V-19 §4-1 새 체크아웃)
- **출처**: [mac-setup §9](../runbooks/mac-setup.md) "§4-1 `build.sh`(main 새 체크아웃, #132 뒤) ⚪ 재확인 대기"(:322), STATUS V-19 행, [WP-20](WP-20-mac-dev-env.md) "남은 것". `$W`는 Binaries·Saved·`Content/Characters`가 없는 새 체크아웃이고 `tools/ue/common.sh`는 스크립트 위치로 저장소 루트를 찾는다.
- **할 일**: `git -C $W switch -c local/jaehwan-ue-gate origin/main`, `git -C $W lfs pull`, 그다음 `./tools/ue/build.sh` → `./tools/ue/add-mannequin.sh` → `./tools/ue/test.sh --setup-dev-level`(모두 `$W`에서, 로컬 우회 없이). GUI 잠금은 필요 없다(헤드리스)지만 영록의 성능 측정과 겹치지 않게 시작 전에 알린다.
- **허용 파일**: `docs/runbooks/mac-setup.md` §9 "§4-1 main 새 체크아웃" 행의 날짜·세션·결과·메모 칸과 §8 #4 "확인 결과" 칸의 dylib 절반. 코드는 고치지 않는다.
- **완료 기준**: HEAD SHA, 각 명령 종료 코드, 빌드 로그의 액션 수(`grep` 출력), `python3 -c`로 `Saved/Automation/Report/index.json`(UTF-8 BOM — `encoding='utf-8-sig'`)에서 센 39개 상태(Success 39 · Failed 0 · Not run 0, 그리고 `succeeded` 칸 값)와 **같은 줄에 skip 수**: `python3 -c "import json;d=json.load(open('unreal/Golmok/Saved/Automation/Report/index.json',encoding='utf-8-sig'));s=[t['fullTestPath'] for t in d['tests'] if any('skipped' in e['event']['message'].lower() for e in t.get('entries',[]))];print(len(s));print(*s,sep='\n')"` 출력 원문(새 체크아웃에는 `L_ZoneTest`·합성 zone이 없어 Portal.*·Save.RoundTrip·Travel.Teleport·Zone.IndexDiscover·Zone.InteriorNotBlocked·Weather.Runtime·Animation.GaspSmoke가 skip으로 Success일 것으로 기대 — 이 테스트들은 "통과"가 아니라 "skip"으로 적는다), `file unreal/Golmok/Binaries/Mac/*.dylib | head`(§8 #4 dylib 아키텍처 [미확인]을 채운다), `git status --porcelain` 빈 출력.
- **왜 재환 / 위험**: 순수 명령 검증이고 이후 모든 UE 과제의 관문이다. 위험: 메인 체크아웃 산출물을 복사하는 것(규칙 6) — 모두 `$W`에서 다시 만든다. 빌드가 실패하면 고치지 말고 오류 줄과 파일:줄을 보고한다(Astra 레인 파일이면 특히).
- **결과(2026-11-28, [#138](https://github.com/wooklym/golmok/pull/138) · `ee3ef0e`, 리뷰 R138)**: `$W`의 `origin/main` `6a1a28e` 새 체크아웃, 로컬 우회 없음. `build.sh` rc 0(액션 57, 34.35 s, error 줄 0), `add-mannequin.sh` rc 0, `test.sh --setup-dev-level` rc 0. 보고서 39개 상태 전부 Success, failed 0, notRun 0, `succeeded` 22 + `succeededWithWarnings` 17 = 39 — 보고서의 `succeeded` 칸은 **Warning 없는** 성공만 센다. 39 중 9는 skip Info 줄이 있는 Success다(L_ZoneTest·합성 zone이 없음): Portal.PawnSwap·Portal.RoundTrip·Portal.SharedInterior·Save.RoundTrip·Travel.Teleport·Zone.IndexDiscover·Zone.InteriorNotBlocked·Weather.Runtime·Animation.GaspSmoke. 위 skip 수 명령은 10을 낸다 — `Zone.IndexParse`는 skip되지 않았고 zone index 셀 줄(`z_synthetic_002@v2` vs `zones.json` v1)의 "(skipped)" 문구에 걸린 것이다. 2026-11-27 메인 체크아웃 실행의 "39 Success"도 같은 9 skip을 포함했다(mac-setup §9 §4-3 정정).

#### J-12b 합성 zone 헤드리스 생성 뒤 `test.sh` 재실행
- **출처**: J-12 보고서의 skip Info(`skipped: run synthetic_zone.run(interior=True)` — Portal.PawnSwap·RoundTrip·SharedInterior, `skipped: /Game/Golmok/Maps/L_ZoneTest missing` — Save.RoundTrip·Travel.Teleport, `skipped: run synthetic_zone.run()` — Zone.IndexDiscover·InteriorNotBlocked; 2026-11-28 메인 체크아웃 보고서로 확인). `.gitignore`가 `L_ZoneTest.umap`·합성 zone 에셋을 무시한다(저장소에 없다). [pc-verify-v17.md](../runbooks/pc-verify-v17.md) §0의 "이전 카드 워크트리에서 복사"는 Mac에 그 워크트리가 없어 쓸 수 없다. `synthetic_zone.run()`(`synthetic_zone.py:699`)은 맵을 만들고 저장한다.
- **할 일**: (1) `cd $W && /usr/bin/timeout 1800 "/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor-Cmd" "$W/unreal/Golmok/Golmok.uproject" "-ExecCmds=py import golmok.synthetic_zone as z; z.run(interior=True),QUIT_EDITOR" -unattended -nullrhi -nosplash -nopause -nosound > $E/synth.log 2>&1; echo $? > $E/synth.rc`(`test.sh`와 같은 `-ExecCmds` 형식; 끝 명령은 `QUIT_EDITOR` — 정정 2026-11-28: 처음 적은 `,Quit`로는 에디터가 나가지 않아 1800 s 타임아웃 rc 124가 됐다). `-nullrhi`에서 glTF 임포트·`save_map`이 되는지는 [미확인]이었다 — 안 되면 `~/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log`(정정 2026-11-28: 처음 적은 `Saved/Logs/Golmok.log`는 Mac에 없다)의 오류 줄을 보고하고 멈춘다(`-nullrhi`를 빼는 재시도는 영록에게 묻고 GUI 잠금 아래에서). (2) `cp "$HOME/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log" $E/synth-editor.log && grep -c "synthetic_zone: interior ready" $E/synth-editor.log`(다음 에디터 실행이 이 파일을 `Golmok-backup-*.log`로 돌린다), `ls $W/unreal/Golmok/Content/Golmok/Maps/`. (3) `cd "$W" && ./tools/ue/test.sh` 다시 실행 → J-12의 skip 수 한 줄 명령을 다시 돌린다.
- **허용 파일**: 없음(코드·문서 변경 없음 — 결과는 PR이 아니라 영록에게 보내는 메시지와 `$E`). 영록이 mac-setup·v17 칸에 옮긴다.
- **완료 기준**: Portal.*·Save.RoundTrip·Travel.Teleport·Zone.IndexDiscover·Zone.InteriorNotBlocked의 `skipped` Info 줄 수가 **0**(skip 수 명령 출력 원문; Weather.Runtime·Animation.GaspSmoke는 에셋·GASP가 없어 skip으로 남는 것이 기대 — 그대로 적는다), 39개 상태(Failed 0 · Not run 0), `git -C $W status --porcelain` 빈 출력(생성물은 `.gitignore` 대상이어야 한다 — 다른 파일이 보이면 커밋하지 말고 목록을 보고).
- **왜 재환 / 위험**: 명령과 로그로 판정된다. J-17·J-20·J-18의 선행이다. 위험: skip을 통과로 적는 것(J-12 skip 수 명령으로 막는다), 생성 에셋을 커밋하는 것.
- **결과(2026-11-28, PR 없음 — 메시지 보고, 영록이 보고 파일을 읽어 확인)**: (1) `QUIT_EDITOR` 명령 rc 0, 14 s. `-nullrhi`에서 glTF 임포트와 맵 저장이 Mac에서 된다. `Content/Golmok/Maps/L_ZoneTest.umap`과 `Content/Golmok/Zones/{z_synthetic_001, z_synthetic_001_interior, z_synthetic_002, index}`가 생기고 모두 `.gitignore` 대상이다(`git status --porcelain` 빈 출력). `,Quit`로는 스크립트가 약 13 s에 끝났지만 에디터가 나가지 않아 1800 s 타임아웃(rc 124). (2) 로그는 `~/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log`에 쓰이고 `$W/unreal/Golmok/Saved/Logs/`는 없다. (3) 그 뒤 `test.sh` rc 0: 39 Success, failed 0, notRun 0, `succeeded` 20 + `succeededWithWarnings` 19. skip 수 명령 출력 3 — Weather.Runtime·Animation.GaspSmoke(기대대로 skip)와 Zone.IndexParse(오탐, J-12 "결과"). Portal.*·Save.RoundTrip·Travel.Teleport·Zone.IndexDiscover·Zone.InteriorNotBlocked 다섯 묶음은 이제 Mac에서 실제로 돌고 Success다. 경고 `Zone manifest z_synthetic_001: unknown top-level key 'spawn' (schema error for golmok-zone validate).`(`Golmok.Zone.ManifestV2`, 1회)는 J-12 보고서와 이 보고서에 **둘 다** 있다(새 경고 아님, 분류는 J-13).

#### J-13 39 중 "Warning 있는 성공" 분류
- **출처**: mac-setup §9 §4-3(:324) "보고서 `succeeded` 칸은 23 … 나머지 16은 Warning 있는 성공(원인 [미확인])"(2026-11-27 메인 체크아웃 실행), WP-20 결과 절. 2026-11-28 새 숫자: J-12 보고서 `succeeded` 22 + `succeededWithWarnings` 17, J-12b 뒤 보고서 20 + 19. `succeeded` 칸은 Warning 없는 성공만 센다(두 칸의 합이 39). 2026-11-27의 23과 J-12의 22가 왜 다른지는 [미확인](다른 실행). 진행: [#139](https://github.com/wooklym/golmok/pull/139) 리뷰 대기.
- **할 일**: J-12 보고서에서 테스트마다 경고 수와 첫 경고 문구·출처(파일·카테고리)를 뽑는 1회용 스크립트(`$E`에 둔다, 커밋 안 함).
- **허용 파일**: mac-setup §9 §4-3 행 메모 칸.
- **완료 기준**: 표(테스트 이름 · 경고 수 · 첫 경고 문구 원문)와 합계가 스크립트 출력과 같다(규칙 10). "무해하다"는 판정은 쓰지 않는다 — 영록(Opus) 몫.
- **왜 재환 / 위험**: 데이터 추출만. 위험: 해석을 사실처럼 쓰는 것.

#### J-14 `DEVELOPER_DIR` 전달 확인
- **출처**: mac-setup §8 #8(:294, 확인 결과 빈칸), `tools/ue/common.sh:2-3`(덮어쓰지 않는다는 주석).
- **할 일**: 이 Mac에는 Xcode가 하나뿐이고 `xcode-select -p`가 같은 경로를 가리켜, 실제 빌드 로그로는 전달 여부를 구분할 수 없다. 대신 스텁으로 확인한다: `tools/tests/test_ue_mac_scripts.py`의 스텁(Build.sh·UnrealEditor-Cmd가 argv를 기록)이 `DEVELOPER_DIR`도 기록하게 하고, `DEVELOPER_DIR=<센티널 경로>`로 `build.sh`(그리고 `test.sh`·`package.sh` 스텁 경로)를 돌려 스텁이 그 값을 받았는지 단언하는 pytest를 더한다. 변수를 주지 않았을 때 스크립트가 값을 만들지 않는지도 한 사례로 단언한다. 읽기 증거로 `grep -n DEVELOPER_DIR tools/ue/*.sh` 출력을 붙인다.
- **허용 파일**: `tools/tests/test_ue_mac_scripts.py`, mac-setup §8 #8 칸.
- **완료 기준**: (a) 새 테스트가 통과하고, 스텁의 환경 기록을 일부러 끈 상태(로컬 1회, 커밋 안 함)에서 실패하는 것을 출력으로(규칙 8). (b) `grep -n DEVELOPER_DIR tools/ue/*.sh` 원문. (c) 파이썬 게이트·CI 모든 행 초록. 결론 문장은 "스크립트가 환경 변수를 그대로 넘긴다(스텁 확인)"까지 — 실제 다른 Xcode로 빌드한 확인은 아니라고 적는다(규칙 3).
- **왜 재환 / 위험**: 작고 명령으로 끝난다.

#### J-15 worktree 패키지로 §8 #10·#11·#12·#13 확인
- **출처**: mac-setup §8 #10(:296 매니페스트·utoc 이름), #11(:297 방화벽 상태·TraceLog 1985, "부분"), #12(:298 패키지 Saved 경로), #13(:299 `-game` CSV 위치).
- **할 일**: GUI 잠금을 잡고 `./tools/ue/package.sh Development --out-dir "$W/build/Mac"` → `find "$W/build/Mac" -name 'Manifest_*' -o -name '*.utoc'` → `touch $E/marker` → `.app`을 `-RenderOffScreen -csvCaptureFrames=300` 등으로 짧게 실행(정확한 플래그는 mac-setup §8 #6 형식) → `ls ~/Library/Application\ Support/Epic/Golmok/Saved` · `find ~/Library/Application\ Support/Epic "$W/unreal/Golmok/Saved" -name 'Profile*.csv' -newer $E/marker`. 실행 중 `lsof -nP -iTCP:1985 -sTCP:LISTEN`, 그리고 `/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate`(**읽기만**, 설정 변경 금지 — 소유자 항목).
- **허용 파일**: mac-setup §8 #10~#13 "확인 결과" 칸.
- **완료 기준**: 행마다 명령·출력 원문. 방화벽 창이 뜨면 누르지 않고 멈춰 영록에게 알린다. `build/`는 `$W` 안에만 생긴다(`git status` 깨끗).
- **왜 재환 / 위험**: 재환은 이 Mac에서 패키지·CSV를 돌린 적이 있다. 위험: 2026-11-27 사고처럼 메인 체크아웃에서 돌리는 것(규칙 6) — 명령은 반드시 `cd $W`에서.

#### J-16 `_pure.py` Mac 경로 가정·`package.sh` 주석 정리
- **출처**: `unreal/Golmok/Content/Python/golmok/_pure.py:1779`, `:1787`, `:1802`, `:1986`([미확인] Mac 경로 가정 — `UserSettingsDir`·`LaunchMac.cpp`), `tools/ue/package.sh:26`(방화벽 [미확인]), J-15 실측.
- **할 일**: 실측이 가정과 같으면 주석만 "확인(J-15, §8 #n)"으로. 다르면 함수를 실측에 맞추고 `tools/tests/test_ue_python_spike_runner.py`(또는 해당 테스트)에 실측 경로 사례를 더한다 — 이 경우 영록에게 먼저 알린다(Claude 레인 코드 변경).
- **허용 파일**: `_pure.py`의 위 함수·주석, 해당 pytest, `tools/ue/package.sh` 주석 줄.
- **완료 기준**: 바꾼 줄마다 근거 출력, 파이썬 게이트·CI 초록.
- **왜 재환 / 위험**: 근거가 명령 출력으로 있다. 위험: 한 번의 실행으로 모든 경우를 일반화하는 것(규칙 3).

#### J-17 V-17 §0 헤드리스
- **출처**: [pc-verify-v17.md §0](../runbooks/pc-verify-v17.md)(39 Success, Claude 레인 후속 5 확인: `GolmokGeoMath.h` NaN 가드 컴파일, `Golmok.Zone.IndexParse` Success, `Golmok.Portal.SharedInterior` Pending 형제 연기 2단계), STATUS WP-05·WP-09 행("🟡 PC 확인 V-17 §0").
- **할 일**: J-12b로 합성 zone을 만든 `$W`에서 v17 §0(:24)의 다섯 후속 항목을 **모두** 다룬다 — ① J-12 빌드 로그에서 `GolmokGeoMath.h`·`GolmokCharacter.cpp` 경고 `grep`, ② `test.sh --filter Golmok.Zone.IndexParse`, ③ `test.sh --filter Golmok.Portal.SharedInterior`(Pending 형제 연기 Info 줄), ④ `test.sh --filter Golmok.Save.RoundTrip` 닫기 단계 `[Info]` 2줄·`(game viewport yes)`, ⑤ `test.sh --filter Golmok.Weather.Runtime` `NightUnaffected`(MPC가 없으면 skip이 기대). 각각 결과와 Info 줄 원문.
- **허용 파일**: v17 §7 결과 표 **아래의 "Mac 선행 기록" 줄**(새로 더한다). §0 행의 결과 칸 자체는 고치지 않는다 — 카드 §0 전체(39 + L_ZoneTest·Weather 에셋 포함)는 아직 끝나지 않았다.
- **완료 기준**: 기록은 `Mac 부분 선행(J-17, 합성 zone 있음/없음, SHA <짧은 SHA>)`로 시작하고 ①~⑤ 각각을 **완료 / skip / 실행 안 함** 중 하나로 적는다(명령별 종료 코드·상태·Info 줄 원문은 PR에). skip이면 통과라 쓰지 않는다.
- **왜 재환 / 위험**: 로그 대조. 위험: skip을 통과로 읽는 것.

#### J-18 V-17 §3 Full Precision UV 헤드리스 + `_import_moved` 정리 경고 — 준비 메모
- **출처**: v17 §3(:40-44, 기대 로그 `zone_import: full precision UVs (LOD0) on 2/2 chunks (2 set, 0 already on)`, warnings 수 불변), [pc-verify-wp06.md](../runbooks/pc-verify-wp06.md) §2·§12 #41, STATUS WP-06 행 끝(Claude 레인 후속 5: `_import_moved` 스크래치 삭제 실패 시 `WARNING cleanup: could not delete … (runbook #8)` — 🟡 정상 경로 로그 불변), [mac-recon.md](../runbooks/mac-recon.md) 미확인 #23(`zone_import` Mac 실행).
- **준비 메모(영록)**: `L_ZoneTest`·`z_synthetic_001`은 J-12b가 만든다. 합성 **스캔** zone(`make_synthetic_zone` + `zone_import`)을 Mac에서 헤드리스로 만들 수 있는지 [미확인] — 영록이 실행 순서와 명령(J-12b와 같은 `-ExecCmds` 형식)을 적는다. GUI 체크박스 확인 대신 Python으로 LOD0 빌드 설정을 읽어 출력하는 한 줄도 메모에 둔다.
- **허용 파일**: v17 §7 §3 행, mac-recon #23 칸. 생성된 에셋·맵은 커밋하지 않는다(`.gitignore` 대상과 `M_ZoneScan*` 포함 — `git status`로 확인).
- **완료 기준**: 기대 로그 줄 `grep` 원문, `done … warnings` 수, `WARNING cleanup` 줄 수(정상 경로 0 기대), LOD0 `use_full_precision_u_vs` 읽기 출력, 청크당 임포트 시간. `-ExecutePythonScript` 종료 크래시(WP-21 부수 발견)가 나면 결과 파일이 그 전에 써졌는지 적는다.
- **왜 재환 / 위험**: 헤드리스 로그로 판정된다. GUI 확인 절반은 영록.

#### J-19 V-17 §5 패키지 quinn 전환
- **출처**: v17 §5(:51-56, 기대: 전환마다 `selected …`, 끝 `current=quinn`, `not found`·거절 없음, 쿡에 `SKM_Quinn_Simple`), [pc-verify-wp18a.md](../runbooks/pc-verify-wp18a.md) §14-6.
- **할 일**: J-15 패키지로 `Golmok.app/Contents/MacOS/Golmok -RenderOffScreen -ExecCmds="golmok.character list,golmok.character proxy135,golmok.character quinn,golmok.character list,…"`(정확한 명령 문법은 런북 그대로 — Mac에서 `-ExecCmds` 다중 명령이 도는지 자체가 [미확인]), 로그 `grep`, 쿡 목록에서 `SKM_Quinn_Simple` `grep`.
- **허용 파일**: v17 §7 §5 행. 실패해도 코드를 고치지 않는다(캐릭터는 Astra 레인).
- **완료 기준**: 로그 줄 원문, 쿡 목록 `grep -c`.
- **왜 재환 / 위험**: 로그만으로 판정된다.

#### J-20 V-16 §1·§3 헤드리스 기준선
- **출처**: [pc-verify-wp16a.md](../runbooks/pc-verify-wp16a.md) §1(빌드)·§3(헤드리스 자동화), STATUS V-16 행. MPC·NS 에셋(§2)은 아직 없다 → `Golmok.Weather.*`는 해당 단계 skip Info로 Success가 기대(v17 §0 문구).
- **할 일**: `test.sh --filter Golmok.Weather`, `test.sh --filter Golmok.Save`, Info 줄 `grep`.
- **허용 파일**: wp16a §13 결과 기록 아래의 "Mac 선행 기록" 줄(새로 더한다). §1·§3 행의 결과 칸은 고치지 않는다.
- **완료 기준**: 기록은 `Mac 부분 선행(J-20, 에셋 전, 합성 zone 있음/없음, SHA <짧은 SHA>)`로 시작하고 테스트마다 **완료 / skip / 실행 안 함**으로 적는다. 상태·Info 원문은 PR에. `Golmok.Save.*`가 `L_ZoneTest missing`으로 skip이면 J-12b가 덜 된 것이다 — 멈추고 알린다.
- **왜 재환 / 위험**: 명령 검증. 위험: skip을 통과로 적는 것.

#### J-21 WP-16a §12 컴파일·심볼 행
- **출처**: wp16a §12(:317-340) #1·#2·#3(컴파일만)·#4(API 존재)·#15·#17. 엔진 헤더는 `/Users/Shared/Epic Games/UE_5.8/Engine/Plugins/FX/Niagara/Source`에 있다.
- **할 일**: J-12 빌드 로그(경고 포함) + `grep -rn` 헤더 경로:줄로 각 행의 "컴파일된다 / 심볼이 있다"만 적는다. #5~#7·#11·#12·#16·#19·#20(동작)은 비운다(PIE 필요).
- **허용 파일**: wp16a §12 "PC 결과" 칸의 위 6행.
- **완료 기준**: 행마다 로그 줄 또는 헤더 `파일:줄` 원문. "동작한다"는 쓰지 않는다.
- **왜 재환 / 위험**: grep 대조. 위험: 컴파일을 동작으로 확대 해석.

#### J-22 V-16 §11 Mac 패키지 명령 이식
- **출처**: wp16a §11(:302-316, Windows 명령), [mac-setup §6](../runbooks/mac-setup.md) V-16 행("§11 패키지는 Mac 패키지(`Golmok-Mac.utoc`, `UnrealPak` Mac 경로)").
- **할 일**: 같은 확인을 Mac 명령으로 — `grep 'Config/Golmok/weather.json' …/Manifest_UFSFiles_Mac.txt`, `"/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealPak" -ListContainer=…/Golmok-Mac.utoc -csv=$E/utoc.csv`, 앱 실행 `-ExecCmds="golmok.weather rain heavy,golmok.weather status"` 로그 `grep`. 에셋이 없으니 컨테이너 줄·`mpc ok`는 실패가 기대다(그대로 적는다). 파일 이름은 J-15(§8 #10) 실측을 쓴다.
- **허용 파일**: wp16a §11에 "Mac 명령(추가)" 블록 — Windows 블록은 고치지 않는다(D-022 "Mac 쪽은 추가만").
- **완료 기준**: 명령 블록이 실제로 돈 그대로이고, 각 명령 출력 원문이 PR에.
- **왜 재환 / 위험**: 명령 이식과 실행. 위험: 돌려 보지 않은 명령을 런북에 넣는 것(규칙 1).

#### J-23 19b A1 ① 회귀 헤드리스
- **출처**: [pc-verify-wp19.md](../runbooks/pc-verify-wp19.md) A1(:43-57): `test.sh --filter Golmok.Animation --setup-dev-level` → 4 Success, `GaspSmoke` `[Info] GASP not installed — skipped`, `Fallback` 기대 Warning 1개, `StateProvider` Info `GASP pawn after p0: accel 2048/2048 …`, `Saved/Logs`에 `Character mesh '' not found` 없음. STATUS WP-19 행.
- **할 일**: 위 명령과 로그 `grep`(Mac에서 런북의 `Saved/Logs`는 `~/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log`다 — 상시 규칙). 에디터 PIE `golmok.anim status` 단계는 GUI라 영록에게 남긴다.
- **허용 파일**: wp19 A1 결과(런북 결과 절의 A1 행)만.
- **완료 기준**: 기대 문자열마다 `grep -c` 출력.
- **왜 재환 / 위험**: 기대 문자열이 런북에 정확히 있다.

#### J-24 V-08b §9-1·§9-2 `locomotion_metrics.py` — 설계 선행
- **출처**: [pc-verify-v08b.md](../runbooks/pc-verify-v08b.md) §9-1(파일 표)·§9-2(통일 정의·수락 (a)~(c)), D-021 진행 기록 (7)(지표 정의를 하나로).
- **설계 메모(영록)**: 함수 서명, 틱 JSON 최소 스키마, 합성 사례 목록, `fixtures/ue/locomotionmath_driver.cpp` `planted` 대조 방식(컴파일러 없으면 skip). 수락 (b)·(c)는 V-08·V-11 원자료가 옛 PC에 있어(§5 자료 복사, 소유자) **"미대조"**로 적는다. 드라이버·어댑터(`locomotion_driver.py`, SendInput)는 범위 밖(J-31 뒤).
- **허용 파일**: `tools/golmok_tools/locomotion_metrics.py`(새), `tools/tests/test_locomotion_metrics.py`(새). `pyproject.toml`·드라이버 C++은 고치지 않는다.
- **완료 기준**: 수락 (a) 무작위 대조 1e-9, 합성 테스트, 파이썬 게이트·CI 모든 행 초록. 커밋 제목은 v08b §9-3 관례를 따를지 메모가 정한다.
- **왜 재환 / 위험**: 정의가 표로 정확하다. 위험: 정의 해석 차이 — 메모와 리뷰 재현으로 막는다. 지표의 의미 판단은 Opus.

#### J-25 V-16 §2a MPC 헤드리스 생성 시험 — 설계 선행
- **출처**: wp16a §2a(:68-81), `weather_setup.py:95` `run()`, §12 #9(MPC Python 쓰기 허용 여부 [미확인]). 두 번째 실행이 `… ok (RainIntensity, Wetness, PuddleAmount, default 0)`을 내야 한다.
- **설계 메모**: `-nullrhi`에서 만들 수 있는지 시험 방법, 만든 `.uasset`을 재환이 커밋·잠글지(LFS·잠금 에셋) 아니면 버릴지. 기본안은 **커밋하지 않고 로그만** 보고.
- **허용 파일**: 메모가 정한다(기본: 없음, wp16a §12 #9 칸).
- **완료 기준**: 1·2회 실행 로그 원문.
- **왜 재환 / 위험**: 헤드리스 로그 판정. 위험: LFS 에셋을 실수로 커밋하는 것.

#### J-26 V-18 §0·§1 헤드리스 — 설계 선행
- **출처**: [pc-verify-v18.md](../runbooks/pc-verify-v18.md) §0·§1(빌드·테스트·8 WAV 재임포트, 오류 0·경고 0). 임포트 코드는 Astra 오디오 레인이다.
- **설계 메모**: 재임포트가 Astra 레인 `Content/Golmok/Audio/`를 다시 쓰므로 실행 뒤 `git -C $W checkout -- unreal/Golmok/Content/Golmok/Audio` 같은 원복 절차와 확인 명령.
- **허용 파일**: v18 결과 칸만. 오디오 레인 파일은 커밋하지 않는다.
- **완료 기준**: 임포트 로그 `grep -c` (오류·경고), `git status` 깨끗.
- **왜 재환 / 위험**: 로그 판정. 위험: Astra 레인 파일 변경(가장 큰 위험 — 메모의 원복 단계로 막는다).

#### J-27 V-05 S12 `run_game_perf.sh` Mac 도구 경로 점검 — 설계 선행
- **출처**: [pc-spike.md](../runbooks/pc-spike.md) S12(:155-170), `spike_runner.py`의 `game_scripts`·`_require_path_files`, mac-setup §3 표(`run_game_perf.sh`).
- **설계 메모**: 경로 JSON(정지 경로 또는 합성 경로 — 실촬영 zone이 없다), 기대 출력 파일, `golmok-perf … --markdown`까지.
- **허용 파일**: 메모가 정한다(코드 결함이 나오면 고치지 말고 재현 절차 보고가 기본).
- **완료 기준**: 스크립트가 돌고 CSV가 생기고 `golmok-perf`가 표를 낸다. **수치는 성능 근거가 아니다**(GPU 공유)라고 PR에 적는다.
- **왜 재환 / 위험**: 도구 경로 점검. 위험: 수치를 판정에 쓰는 것.

#### J-28 CI `swift build`(golmok-objcap) — 설계 선행
- **출처**: `tools/mac/objcap/Package.swift`(테스트 타깃 없음), `tools/tests/test_mac_objcap.py:38-65`(텍스트 검사만), CI에 swift 단계 없음(2026-11-28 조사).
- **설계 메모**: `macos-latest` 러너 Xcode SDK에 `PhotogrammetrySession`이 있는지 [미확인]일 때의 처리(빌드만·`limits` 실행 여부), 핫스팟 훅.
- **허용 파일**: `ci.yml` `# [WP-21 hook]` 블록(별도 커밋).
- **완료 기준**: 로컬 `swift build -c release` + `golmok-objcap limits` 출력, CI 새 행 초록.
- **왜 재환 / 위험**: 명령 판정. 위험: 러너 SDK 차이.

#### J-29 크래시 리포트 업로드 끄기 — 설계 선행
- **출처**: WP-21 "부수 발견"·남은 작업 5, D-023 "D-007" 줄(CrashReportClient가 로컬 경로가 든 리포트를 Epic으로 올린다).
- **설계 메모(영록)**: 엔진 `BaseEngine.ini` 또는 CrashReportClient 소스에서 키를 확인해 정한다. **시험으로 크래시를 일으키지 않는다** — 키가 틀리면 업로드가 일어나 외부 발송이 된다(D-019 ③).
- **허용 파일**: 메모가 정한 `Config/Default*.ini` `[WP-21 hook]` 블록(별도 커밋).
- **완료 기준**: 패키지 `Config` 스테이징에 키가 있는지 `grep`, 엔진 소스의 해당 키 `파일:줄`.
- **왜 재환 / 위험**: 구현은 한 블록. 위험이 외부 발송이라 키 선택은 Opus.

#### J-30 COLMAP 미터·ENU 정합 → 메시·splat 좌표 공유 — 설계 선행
- **출처**: WP-21 남은 작업 4, D-023 "좌표" 줄(Brush는 COLMAP world를 그대로 쓴다, Object Capture는 실행마다 좌표계가 다르다, 끝까지 해 보지 않음 [미확인]), [mac-recon.md](../runbooks/mac-recon.md).
- **설계 메모**: 공개 스모크 데이터(`~/golmok_data/recon-smoke/`, 저장소 밖), 기준점·축척 출처, 수치 완료 기준(예: 정합 뒤 메시↔splat 거리 중앙값 상한).
- **허용 파일**: 메모가 정한다(아마 `golmok-align`·mac-recon 문서 절).
- **완료 기준**: 메모의 수치 기준.
- **왜 재환 / 위험**: 수치로 판정할 수 있으면 맞다. 위험: 품질 판단으로 번지는 것 — 품질은 V-05(Opus·소유자).

#### J-31a·J-31b 엔진 안 입력 드라이버의 작은 조각 — 설계 선행
- **출처**: mac-setup §3 표 "Win32 SendInput 드라이버 — 재설계 항목, ① 엔진 안 `InputKey`/Enhanced Input 주입을 먼저 권한다"(:146), STATUS V-17 §1·§2·V-08b·V-12가 이것을 기다린다. V-08b §10 블라인드 채점·V-15 측정이 같은 드라이버 입력을 쓴다.
- **나누는 이유**: 드라이버 전체(M–L)는 크기 척도를 넘고, 타이밍 결함이 D-020이 Opus에 맡긴 품질 판정 자료를 오염시킨다. 그래서 **측정에 직접 쓰이는 주입 경로·어댑터는 Opus(영록)가 구현**하고, 재환은 아래 두 조각만 맡는다. 어느 V 카드든 이 드라이버를 쓰기 전에 영록의 구현 리뷰를 거친다.
- **J-31a**: Opus B1 설계 메모가 정한 키 타임라인 형식의 순수 파서(새 Python 모듈 + pytest, 경계 사례 — 겹친 키·0 길이·정렬 안 된 입력·잘못된 키 이름 — 와 오류 메시지 단언). 허용 파일은 메모가 정한 새 파일 2개. 완료 기준: 파이썬 게이트·CI 모든 행 초록, 오류 경로마다 1회 일으킨 출력(규칙 8).
- **J-31b**: Opus가 만든 주입 경로 위에서 헤드리스 자동화 테스트 1개("W 3 s → 캡슐 이동 거리"가 메모의 기대 범위). 허용 파일은 메모가 정한 새 테스트 파일 1개. 완료 기준: `test.sh --filter <그 테스트>` 상태·Info 원문, 전체 `test.sh` Failed 0.
- **핫스팟 위험**: 입력 주입은 `Player/GolmokPlayerController`(§7.6 핫스팟)에 닿기 쉽다. 재환 조각은 핫스팟을 고치지 않는다. 메모가 핫스팟을 요구하면 그 부분은 영록이 `// [WP-NN hook]` 블록(별도 커밋)으로 넣는다.
- **왜 재환 / 위험**: 순수 파서와 단일 단언 테스트만. 위험: 조작감 판정 — 하지 않는다.

#### J-32 Cesium 활성 사본에서 mac-recon #15·#16 — 설계 선행
- **출처**: mac-recon 미확인 #15(CesiumRuntime 게임 타깃 빌드)·#16(로드 오류 줄이 `test.sh`를 실패시키는지), WP-21 남은 작업 2·3. 저장소 `.uproject` 활성화(남은 작업 1)는 영록 결정·훅이다.
- **설계 메모**: 저장소 밖 프로젝트 사본 위치와 플러그인 배치, 렌더 확인(#14)은 눈이 필요해 영록 몫.
- **허용 파일**: mac-recon #15·#16 칸.
- **완료 기준**: 빌드 종료 코드·`test.sh` 상태·오류 줄 원문.
- **왜 재환 / 위험**: 명령 판정 부분만.

#### J-33 avfoundation 60 fps 녹화 시험 — 설계 선행
- **출처**: mac-setup §8 #25(:311), §3 표 녹화 재설계 항목(:147).
- **선행**: 소유자가 시스템 설정에서 화면 기록 권한을 준다(보안 설정 — 재환·영록이 대신하지 않는다).
- **할 일**: 10 s 녹화(`~/golmok-tools`의 lgpl ffmpeg, `h264_videotoolbox`) → `ffprobe -count_frames`.
- **허용 파일**: §8 #25 칸.
- **완료 기준**: 프레임 수 출력 원문, 녹화 중 LM Studio 부하 여부.
- **왜 재환 / 위험**: 수치 하나. 위험: 권한 없이 시도하다 권한 창을 누르는 것 — 누르지 않는다.

#### J-34 `test.sh`·`add-gasp.sh` 오류 문구의 로그 경로를 Mac 실제 경로로
- **출처**: J-12b 결과(Mac 에디터 로그는 `~/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log`, `<project>/Saved/Logs/`는 없다), [mac-setup §8 #14](../runbooks/mac-setup.md). 지금 문구: `tools/ue/test.sh:34` 주석과 `:42` 오류 `No automation report at $Index (see unreal/Golmok/Saved/Logs/Golmok.log).`, `tools/ue/add-gasp.sh:120` 오류 `… see the editor log under Saved/Logs.`
- **할 일**: 세 줄이 Mac 실제 경로(`~/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log`)를 가리키게 고친다. 오류 문구에 사용자 이름이 든 절대 경로를 하드코딩하지 않는다(`$HOME` 또는 `~`). `tools/tests/test_ue_mac_scripts.py`의 스텁으로 두 오류 경로를 일으켜 새 문구를 단언하는 사례를 더한다(기존 스텁이 보고서를 쓰지 않게 하면 `test.sh` 경로가 난다).
- **허용 파일**: `tools/ue/test.sh`, `tools/ue/add-gasp.sh`, `tools/tests/test_ue_mac_scripts.py`.
- **완료 기준**: (a) 새 사례가 옛 문구에서 실패하고(로컬 1회, 커밋 안 함, 출력 원문 — 규칙 8) 새 문구에서 통과. (b) `grep -n -E 'Saved/Logs' tools/ue/test.sh tools/ue/add-gasp.sh` 출력이 0줄(또는 남은 줄과 이유). (c) `bash -n tools/ue/*.sh`, 파이썬 게이트, CI 모든 행 초록. add-gasp 사례가 편집기 가드(J-06)에 걸리면 그 사실을 적는다.
- **왜 재환 / 위험**: 문구와 스텁 테스트만. 위험: 실제 경로를 한 Mac의 관찰로 일반화하는 것 — 문구는 "Mac 기본 위치"로 좁혀 쓴다(규칙 3).

## 재환에게 맞지 않는 것 (이유)

| 무엇 | 왜 | 누구 |
|---|---|---|
| C-01·C-02·C-05 촬영, C-08 청취, EgoBlur 모델 동의·다운로드, Fab GASP 받기·D-021 원문 재확인, Freesound 계정, PC 자료(베이스맵·녹화) 복사, Windows 빌드 경로·지출 대안, D-018 ② | 소유자만 할 수 있거나 되돌릴 수 없다(D-019 ①②③⑥) | 소유자 |
| WP-18 캐릭터·WP-13/17 오디오 레인 파일, 18b·C-08 튜닝 PR | Astra 레인(DEVELOPMENT-PLAN §7.6) | Astra |
| 룩·조작감·품질 판정(V-19 §4-4 모습 확인, V-12, V-15 채점, V-16 §5·§7·§8, V-17 §1·§2, V-05·D-010), 게임 설계, D-0xx 제안 | D-020: 판단은 Opus | 영록(Opus)·소유자 |
| Niagara `NS_GolmokRain` 저작(V-16 §2b), 19b BP 바인딩, GUI 에디터 저작 | GUI 저작과 품질 판단이 섞인다 | 영록(Opus) |
| 빈 L_Dev Mac 기준선(V-19 §4-6) 등 **정본** 성능 수치 | 재환 추론이 같은 GPU를 써 수치가 오염된다(정도 [미확인]) | 영록(같은 세션 기준선) |
| 공유 문서(STATUS·DECISIONS·ROADMAP·DEVELOPMENT-PLAN·CLAUDE.md·AGENTS.md·README) | Claude 세션만 고친다(§7.6 핫스팟 규칙 3) | 영록 |
| WP-21 후속 1(Cesium `.uproject` 훅·서드파티 소스·`IonQuickAddPanel` 처리), `-ExecutePythonScript` 종료 크래시 조사 | 스택·서드파티 결정, 조사 범위가 넓다 | 영록(Opus) |

## 게임 완성까지의 경로 (재환 일이 풀 수 있는 것과 없는 것)

"완성"의 정의는 Phase 1 MVP = **M7**이다(DEVELOPMENT-PLAN §3·§1.3, ROADMAP Phase 1): 베이스맵 위 걷기·달리기, 실촬영 골목 1곳(전 구간 걸림·떨림·구멍 없이, 목표 fps), 걸어 들어가는 실내 1곳(문 → 실내 → 문 왕복), 게이트 G2~G5(G5 = 렌더에 얼굴·번호판 누락 0, DEVELOPMENT-PLAN §6). 지금(2026-11-28) M1·M2 🟢, M3 🟡, M4 ⚪(STATUS 마일스톤).

핵심 경로(DEVELOPMENT-PLAN §5.4): **C-01 → C-02 → V-05 → D-010 → V-06 → M5 → C-05 → M6 → M7.**
- **소유자가 막고 있다**: C-01 리허설 촬영과 EgoBlur 모델 동의(V-01 §3 블러 점검), C-02 골목 촬영, C-05 실내 동의·촬영, V-05 뒤 제품 재구성 스택 확정과 필요 시 지출(D-023 ④), Windows 빌드 경로(D-022 ③), GASP(D-021 발효).
- **Opus가 막고 있다**: 입력·녹화·GPU 측정 재설계(B1 — V-17 §1·§2, V-08b, V-12, V-15의 선행), V-16 GUI 에셋·룩, V-05 판정과 D-010, 14b·16b·15b.
- **재환 일이 푸는 것**: V-19 남은 헤드리스 확인(J-12·J-12b~J-16), V-16·V-17·19b·V-18의 헤드리스 단계(J-17~J-23, J-25, J-26)로 그 카드의 GUI 단계가 바로 시작할 수 있게 하는 것, 도구·CI 신뢰도(J-06~J-11, J-28), 재설계·지표의 작은 조각(J-24, J-31a·J-31b), 공개 데이터 좌표 정합(J-30).
- **재환 일이 풀지 못하는 것**: 촬영이 없으면 M4~M7은 시작하지 못한다. 재환 과제를 다 끝내도 MVP는 C-01·C-02를 기다린다. 이 파일은 그 기다림을 줄이는 준비 작업의 목록이다.

## 백로그 보충 규칙

- 배정 가능한(선행이 풀린, 설계 선행이면 메모가 있는) 과제가 **5개 아래로** 떨어지면 영록이 STATUS(🟡 행의 "PC 확인 대기"·"[미확인]"), ROADMAP, 열린 V 카드 런북(`docs/runbooks/pc-verify-*.md` §결과 빈칸, mac-setup §8·mac-recon 미확인 표), WP 문서의 "남은 작업"·리뷰 (C) 이월에서 채운다.
- 새 과제도 이 파일의 형식(출처 파일:줄 또는 카드 §, 허용 파일, 명령과 기대 출력인 완료 기준, 크기, 이유·위험)을 지킨다. 출처가 없는 일은 넣지 않고, 불확실한 것은 `[미확인]`으로 둔다.
- 재환이 막히면(선행 미충족·설계 메모 없음·GUI 잠금 대기) 다음 배정 가능 과제로 넘어가고 메시지로 알린다. 영록은 막힌 과제의 선행을 먼저 푼다.
- 이 파일은 영록이 고친다. 재환은 PR 본문에 제안만 적는다.
