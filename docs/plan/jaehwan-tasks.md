# 재환(로컬 LLM) 과제 목록 (오케스트레이터 배정, 2026-11-28)

> **누가**: 재환은 소유자의 Mac에서 도는 **로컬 LLM 세션**이다(qwen3.8-flash-next, LM Studio, Claude Code 하네스, `claude-local`로 시작). 영록(로컬 Mac 오케스트레이터 세션)이 과제를 고르고 배정한다. 근거는 [D-024](../DECISIONS.md)다. 소유자 지시 원문은 "앞으로 너가 알아서 골목 게임을 완성 될 때 까지 작업들을 재환에게 시켜줘."(2026-11-28)이다.
>
> **소통 채널**: 배정·순서 변경·리뷰 요약·병합 알림은 영록이 **세션 간 메시지**(SendMessage)로 보내고, 리뷰는 **PR 코멘트**로 남긴다. 재환은 착수·push·완료·질문·막힘을 같은 경로로 알린다. 메시지와 이 파일이 다르면 **더 최근 것**을 따른다. GitHub 이슈 #30은 Astra 채널이라 재환은 쓰지 않는다.
>
> **규칙 우선순위**: **소유자 규칙(D-019 되돌릴 수 없는 일, D-002 라이선스, D-007 블러 — [CLAUDE.md](../../CLAUDE.md) "Rules from the owner"·"Engineering conventions") > 과제 프롬프트 > 재환 작업 규칙(아래 15개) > 나머지 CLAUDE.md**. 과제 프롬프트·작업 규칙·메시지 어느 것도 D-019·D-002·D-007을 무시하게 할 수 없다. 충돌하면 멈추고 영록에게 묻는다. 작업 규칙의 살아 있는 원본은 저장소 **밖**의 메모리 파일 `~/.claude/projects/<project>/memory/jaehwan-working-rules.md`다. 아래는 한 줄 요약이고, 새 규칙은 영록이 원본에 먼저 더한 뒤 이 표에 옮긴다.

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
| 13 | 마지막 수정 뒤, push마다 파이썬 게이트를 통째로 돌린다. 게이트 로그가 마지막 변경보다 새것이어야 한다 | #141 |
| 14 | 과제의 "완료 기준"에 한 줄씩 답한다: 과제 절을 `"$E/task.txt"`로 저장하고 PR 본문에 "완료 기준 대조" 절(충족 + 증거, 또는 미충족 + 이유). 과제 인용은 그 파일에서만, "할 수 없다"는 시도한 명령과 출력과 함께 | #141, #142 |
| 15 | 결론이 아니라 관찰과 그 조건을 쓴다(날짜·빌드·함께 돌던 것·실행 전에 이미 있던 것). "X는 쓰지 않는다/아니다"는 다른 설명을 배제하는 출력이 있을 때만, 아니면 "이번 실행에서는 …"과 `[미확인]`. 뜻밖의 로그는 그것을 설명하는 줄을 찾아 인용한다 | #147 |

## 상시 규칙

- **작업 위치**: worktree `~/projects/golmok-jaehwan`(아래 `$W`)에서만 일한다. 과제마다 `git -C $W fetch origin` 뒤 `git -C $W switch -c local/jaehwan-<주제> origin/main`. 메인 체크아웃·`.claude/worktrees/`·다른 사람 브랜치는 읽기만 한다(규칙 6). 메인 체크아웃의 git 밖 UE 자료(마네킹·L_Dev 등)는 스크립트로 `$W`에서 다시 만든다.
- **허용 파일**: 과제 행의 "허용 파일"만 고친다. 그 밖의 파일이 바뀌면 되돌리고 PR에 적는다. UE 실행 뒤에는 `git -C $W status --porcelain`이 허용 파일만 보여야 한다(쿡·임포트가 만든 `.uasset`·`M_ZoneScan*`은 커밋하지 않는다).
- **금지**: 병합·`main` push·force-push·rebase·브랜치/태그 삭제, 메인 체크아웃에서 쓰기·패키지·`build/` 삭제, 공유 문서 수정(STATUS·DECISIONS·ROADMAP·DEVELOPMENT-PLAN·CLAUDE.md·AGENTS.md·README.md·tools/README.md — 문안이 필요하면 PR 본문 "병합 시 반영"에), Astra 레인 파일([DEVELOPMENT-PLAN §7.6](../DEVELOPMENT-PLAN.md) 표: `Source/Golmok/Characters/`, 오디오 레인 등), 핫스팟은 과제가 허용한 `// [WP-NN hook]` 블록으로만(별도 커밋), 지출·계정·약관 동의·외부 발송·시스템 보안 설정 변경(방화벽·화면 기록 권한 등은 소유자), `sudo`, LFS 에셋·데이터 삭제, 게임 설계·룩·조작감 판정.
- **GPU·GUI 공유**: UE 에디터 GUI·PIE·`-game`·패키지 실행 전에 `"$TMPDIR/claude/gui-foreground.lock"`을 확인하고 잡는다([mac-setup §3](../runbooks/mac-setup.md) 표의 규칙). 영록이 성능을 재는 동안에는 빌드·쿡·셰이더 컴파일을 하지 않는다. 두 UBT 빌드가 동시에 돌 때 서로 기다리는지·느려지는지는 [미확인]이다. 재환의 추론도 같은 GPU·통합 메모리를 쓰므로 **재환이 잰 fps·GPU ms는 판정 근거가 아니다**. 수치를 적을 때는 LM Studio 모델이 로드돼 있었는지 함께 적는다.
- **패키지 출력**: `GOLMOK_PKG_DIR`는 2026-11-28 현재 비어 있고 `package.sh` 기본값은 `<worktree>/build/Mac`이다. 재환은 항상 `--out-dir "$W/build/Mac"`를 명시한다.
- **증거**: 로그·재현 스크립트·출력은 `$TMPDIR/jaehwan/<과제 id>/`에 두고 병합 알림까지 지우지 않는다(규칙 10).
- **PR**: 제목 `J-NN: <요약>`. 본문 = 요약, 바뀐 파일, 실행한 명령과 출력(복사), 남은 `[미확인]`, "병합 시 반영"(공유 문서 문안이 있으면), **"제출 전 점검표"**(규칙 1~15 한 줄씩 — 한 일과 증거, 또는 "해당 없음"과 이유), 끝 줄 서명(규칙 7). 점검표가 없으면 리뷰를 시작하지 않는다.
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
| J-13 | 39 중 경고 있는 성공 분류(V-19 §4-3) — J-12 보고서 기준 경고 있는 성공 17건·경고 53개를 8분류(A·A′·B~G, 판정 없음), J-12b 뒤 보고서는 19건·67개(아래 J-13 "결과") | [#139](https://github.com/wooklym/golmok/pull/139) · `49adc49` | R139(1회 보류: 본문 반복 실수) → R139-2 |
| J-14 | `DEVELOPER_DIR` 전달 스텁 테스트 6개(§8 #8) — 스크립트가 환경 변수를 그대로 넘긴다(스텁 확인), 실제 다른 Xcode 빌드 확인은 아님 | [#141](https://github.com/wooklym/golmok/pull/141) · `30aa96d` | R141(본문 B-1·B-2 수정 뒤 병합) |
| J-06 | `gasp_env`에 가짜 `ps` 스텁 — add-gasp 편집기 가드 테스트가 실제 프로세스에 의존하지 않는다(수정 전 더미 프로세스로 6 failed → 수정 뒤 더미 유무 모두 8 passed) | [#143](https://github.com/wooklym/golmok/pull/143) · `a37b4ef` | R143 |
| J-34 | `test.sh`·`add-gasp.sh` 오류 문구가 Mac 에디터 로그 `~/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log`를 가리키고, 스텁 테스트 assert가 그 경로를 고정 | [#142](https://github.com/wooklym/golmok/pull/142) · `85a09c3` | R142(1회 보류: 완료 기준 테스트 누락·사실 아닌 문장 2개, 규칙 1·2·10·14) → R142-2 |
| J-07 | WP-21이 본 E501 1건(`test_ue_mac_scripts.py:352`)은 `a9a8757`(WP-20 줄 길이 정리)에서 이미 고쳐졌고 main `85a09c3`의 `ruff check .`는 "All checks passed" — 코드 변경 없음 | PR 없음(결과는 [#143](https://github.com/wooklym/golmok/pull/143) 본문 "J-07 결과" 절) | R144(영록 재현: `9f3b64d`의 파일은 E501 116 > 110 1건, `a9a8757`의 파일은 통과) |
| J-09 | 확인된 §8 행의 `[미확인]` 주석 정리 — `common.sh`·`test.sh`·`test_ue_geo_math.py` 주석 줄만(§8 #1·#2·#5, §9 FMA 행), add-gasp 절반은 `[미확인]` 유지 | [#146](https://github.com/wooklym/golmok/pull/146) · `34d0c6f` | R146(코드 통과, 본문 1회 반려: "완료 기준 대조" 절 누락, 규칙 14) |
| J-08 | mac-setup §8 #24 rawpy 절반 — `rawpy-0.28.0-cp312-cp312-macosx_11_0_arm64.whl`, 확장 모듈 arm64, `rawpy.flags` 원문(EgoBlur MPS 절반은 빈 칸 그대로) | [#145](https://github.com/wooklym/golmok/pull/145) · `84ad068` | R145(1회 보류: 비워 둘 EgoBlur 절반에 씀, 칸에 출력 원문 누락, 규칙 1·6·10·14) → R145-2 |

**진행 중**

| id | 과제 | 브랜치 | 허용 파일 |
|---|---|---|---|
| J-15 | worktree 패키지로 §8 #10·#11·#12·#13 확인 | `local/jaehwan-j15-pkg-8checks`([#147](https://github.com/wooklym/golmok/pull/147) 열림, 병합 보류 2회: [R147](https://github.com/wooklym/golmok/pull/147#issuecomment-7228924374)(head `0c84d04`, #11 칸의 결론이 증거보다 넓음·본문에 로그에 없는 숫자 — 이 실수로 규칙 15 추가) → [R147-2](https://github.com/wooklym/golmok/pull/147#issuecomment-7229368051)(head `82d6d9c`, 2026-11-27T22:29Z: #12 칸의 인용 날짜가 근거 로그와 다름, #13 칸이 실패할 수 없는 검사(두 실행이 끝난 뒤 만든 표식)를 근거로 씀, 숫자 검사가 본문 초안까지 셈 — 규칙 1·10·15). 재환 수정 중. 상태는 `gh pr view 147 --comments`(2026-11-28)에서 읽음) | 과제 상세 J-15 절 |
| J-17 | V-17 §0 헤드리스 Mac 부분 선행 | `local/jaehwan-j17-v17s0`([#149](https://github.com/wooklym/golmok/pull/149) 열림, [R149](https://github.com/wooklym/golmok/pull/149#issuecomment-7229593014) 병합 보류(head `d232953`, 2026-11-27T22:45Z): ⑤ `Weather.Runtime`을 "완료"로 적었으나 보고서는 skip, ① `build.sh` 종료 코드가 저장되지 않았는데 "충족", 인용 검사가 다시 자기 초안을 대상에 넣음 — 규칙 14·15·10(e). 재환 수정 중(#147 다음). R149가 찾은 `test.sh` 종료 규칙 결함은 새 과제 J-36. 상태는 `gh pr view 149 --comments`(2026-11-28)에서 읽음) | 과제 상세 J-17 절 |

**다음**: J-15·J-17(진행 중, 둘 다 병합 보류 — 재환 수정 중) → J-20 → J-36 → J-18 → J-35 → 그 뒤 남은 비설계 과제(J-16·J-19·J-21~J-23, 순서는 영록이 정한다) → J-11 → J-10(둘 다 설계 확정, Opus 2026-11-28) → 설계 선행 J-24~J-33.

## 백로그 (의존 순서)

순서 원칙: ① UE 빌드가 필요 없는 도구·테스트·CI 일 → ② 재환 worktree의 UE 빌드를 세우고 증명하는 **관문 J-12·J-12b**(빌드·39 테스트, 합성 zone으로 skip 제거) → ③ 열린 카드의 헤드리스 UE 단계와 [미확인] 행 → ④ Claude 레인 코드 후속. **설계 선행** 표시 과제는 영록(Opus)이 짧은 설계 메모(파일·방법·완료 기준)를 이 파일의 해당 행 아래 또는 배정 메시지로 먼저 쓴 뒤에만 배정한다. J-10·J-11은 설계가 확정되어(Opus 2026-11-28, 아래 각 절) 배정할 수 있다. 크기: S ≤ 반나절, M ≤ 하루, L > 하루.

| id | 과제 | 선행 | 크기 | 설계 선행 |
|---|---|---|---|---|
| J-10 | CI shellcheck 잡(공식 v0.11.0 고정·sha256, `--severity=warning`, 기존 결함은 표에 정한 줄별 지시문만 — 실행 줄 변경 없음, 같은 커밋 8/8 초록) | 없음(설계 메모 확정, Opus 2026-11-28) | S–M | 설계 확정(J-10 절) |
| J-11 | CI 뷰어 `npm test` 잡(`viewer-smoke`, ubuntu-24.04 한 행 — Playwright 1.56.1은 `ubuntu-latest`(26.04) 미지원, `ci.yml` 훅 블록은 별도 커밋, 같은 커밋 8/8 초록) | 없음 | M | — (설계 확정, Opus 2026-11-28, 아래 J-11 절) |
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
| J-35 | add-gasp 편집기 가드의 남은 분기 스텁 사례(`$GaspProject` 일치·음성 2종, J-06 후속) | 없음(J-07은 코드 변경 없이 끝남) | S | — |
| J-36 | `test.sh` 종료 규칙: 경고 있는 성공만 있는 실행도 통과(`failed` 0 · `succeeded`+`succeededWithWarnings` ≥ 1), 요약 줄에 경고 있는 성공 수, 옛 스크립트에서 실패하는 스텁 사례, 실제 `--filter Golmok.Zone.IndexParse` 전후(R149 발견) | 없음. J-35와 같은 테스트 파일(`tools/tests/test_ue_mac_scripts.py`)이라 둘을 동시에 열지 않는다 — **J-36 먼저**, J-35는 그 병합 뒤 | S | — (설계 확정, Opus 2026-11-28, 아래 J-36 절) |

J-06·J-07·J-08·J-09·J-12·J-12b·J-13·J-14·J-34는 끝났고(위 "완료"), J-15·J-17은 진행 중이다(위 "진행 중"). J-36은 새 과제다(2026-11-28, R149 발견, 설계 확정). 아래 상세 절은 그대로 두고, 끝난 과제에는 "결과" 줄을 더한다.

### 과제 상세

공통 표기: `W="$HOME/projects/golmok-jaehwan"`, `E="$TMPDIR/jaehwan/<id>"`(경로는 [mac-setup §0](../runbooks/mac-setup.md) "경로 표기"처럼 `~` 기준으로 적는다 — 공개 저장소에 사용자 이름이 든 절대 경로를 쓰지 않는다). 파이썬 게이트 = `cd $W/tools && source .venv/bin/activate && ruff check . && ruff format --check . && pytest -q && python scripts/check_repo.py`(worktree 안의 venv; 없으면 `uv venv` + `uv pip install -e ".[basemap,zone,mesh,splat,align,dev]"`). UE 명령은 모두 `/usr/bin/timeout`으로 감싼다(빌드 1800 s, 테스트 2700 s, 패키지 5400 s 이내 — 넘으면 규칙 5).

#### J-06 add-gasp 편집기 가드 테스트의 환경 의존 제거
- **출처**: [WP-21](WP-21-mac-recon-pipeline.md) "남은 작업" 6과 같은 문서 검사 절(편집기가 떠 있으면 add-gasp 테스트 4건이 "close the Unreal Editor first"로 실패). 가드는 `tools/ue/add-gasp.sh:62-74`(`ps -axo pid=,comm=`), 테스트는 `tools/tests/test_ue_mac_scripts.py:454-588`.
- **할 일**: `gasp_env` 픽스처가 실제 프로세스 목록 대신 가짜 `ps`(픽스처의 `PATH` 앞 스텁)를 쓰게 한다. 양성 사례 `test_add_gasp_refuses_while_an_editor_runs`(:573)는 지금처럼 실제 프로세스로 남기거나, 스텁이 그 PID를 보고하게 바꾸되 의미(가드가 막는다)를 유지한다.
- **허용 파일**: `tools/tests/test_ue_mac_scripts.py`. 스텁만으로 안 되면 이유를 PR에 적고 영록에게 묻는다(`add-gasp.sh`는 그 뒤에만).
- **완료 기준**: (a) 수정 전 재현 — `$E/fake/Golmok.uproject.d/UnrealEditor` → `sleep` 심볼릭 링크를 `sleep 600`으로 띄운 채 `pytest -q tests/test_ue_mac_scripts.py -k add_gasp` → 실패 수를 `grep -c` 출력으로. (b) 수정 뒤 같은 더미 프로세스가 떠 있어도 0 실패, 더미가 없을 때도 0 실패. (c) 양성 사례가 여전히 `close the Unreal Editor first (running: <pid>` 를 단언. (d) 파이썬 게이트, CI 모든 행 초록(규칙 2·4 — Windows 행은 이 테스트를 어떻게 건너뛰는지 확인해 적는다).
- **왜 재환 / 위험**: on/off 재현으로 끝나는 좁은 테스트 일(J-04 방식). 위험: 스텁이 가드 자체를 무력화해 양성 사례까지 통과시키는 것 — (c)로 막는다.
- **결과(2026-11-28, [#143](https://github.com/wooklym/golmok/pull/143) · `a37b4ef`, 리뷰 R143)**: 허용 파일 하나만 고쳤다. `gasp_env`가 `PATH` 맨 앞(`e.bin`)에 가짜 `ps`를 두고, 제어 파일 `FAKE_PS_LIST`(`"pid exe"` 줄, `ps -axo pid=,comm=` 대신)·`FAKE_PS_CMDS`(`"pid command line"` 줄, `ps -o command= -p <pid>` 대신)를 읽는다. 둘 다 빈 파일이 기본이라 가드는 "떠 있는 에디터 없음"으로 통과한다. 양성 사례는 실제 `sleep` 프로세스 대신 스텁이 보고하는 고정 pid 4242(경로에 공백이 든 `UnrealEditor` exe + `Golmok.uproject` 명령줄)로 바꾸고 `close the Unreal Editor first (running: 4242`와 `e.calls() == []`를 단언한다. `add-gasp.sh`는 건드리지 않았다. 수정 전 더미 프로세스(`UnrealEditor` → `sleep` 링크)를 띄운 채 `-k add_gasp` → 6 failed, 2 passed(과제의 "4건"보다 많은 것은 J-14가 같은 픽스처를 쓰는 `test_add_gasp_passes_developer_dir`를 더했고 양성 사례도 실패했기 때문). 수정 뒤 더미가 있을 때·없을 때 모두 8 passed. 게이트 1936 passed, 3 skipped. Windows CI 행은 `@posix_only`로 건너뛴다(`1897 passed, 42 skipped`). R143 재현: 가드를 무력화하면 양성 테스트가 실패한다. 남은 분기(`$GaspProject` 일치·음성 사례)는 J-35.

#### J-07 `ruff check` E501 잔여 확인과 WP-21 후속 6 닫기 근거
- **출처**: WP-21 검사 절("E501 1건 `test_ue_mac_scripts.py:352`"). 2026-11-28 조사에서 main `6a1a28e`의 `ruff check .`가 "All checks passed"였다는 보고가 있다 — 재환이 다시 확인한다.
- **할 일**: `origin/main`에서 `ruff check .` 출력과 `git log -L352,352:tools/tests/test_ue_mac_scripts.py --oneline | head`로 언제 고쳐졌는지 찾는다. 남아 있으면 그 줄만 고친다.
- **허용 파일**: `tools/tests/test_ue_mac_scripts.py`(E501 줄만). 이미 고쳐졌으면 코드 변경 없이 J-06 PR 본문에 출력만 붙인다(PR을 따로 만들지 않는다).
- **완료 기준**: `ruff check .` 출력 원문, 고친 커밋 SHA. 영록이 WP-21 후속 6을 닫는다.
- **왜 재환 / 위험**: 명령 하나로 끝난다. 위험: 기억으로 "이미 고쳐짐"이라고 쓰는 것(규칙 1).
- **결과**(2026-11-28, R144): 코드 변경 없음. main `85a09c3`에서 `ruff check .` → "All checks passed". 고친 커밋은 `a9a8757`("WP-20: test_ue_mac_scripts 줄 길이 정리 (ruff)"): `9f3b64d`의 파일은 E501 1건(352행, 116 > 110), `a9a8757`의 파일은 통과(영록 재현). 위 "할 일"의 `git log -L352,352`는 현재 352행의 계보만 따라가 답을 내지 못했다(영록의 지시 오류) — 재환이 커밋별 `git show "${sha}:<파일>" | ruff check --stdin-filename <파일> -`로 확정했다. PR은 만들지 않았고 결과는 [#143](https://github.com/wooklym/golmok/pull/143) 본문에 붙였다.

#### J-08 rawpy arm64 휠 설치·`rawpy.flags` 확인
- **출처**: [mac-setup §8](../runbooks/mac-setup.md) #24(rawpy arm64 휠), D-022 "이력"(D-011의 `rawpy.flags` 확인을 Mac arm64 휠에서 다시 한다 [미확인]), `tools/pyproject.toml`의 `raw` extra.
- **할 일**: `$W/tools`의 별도 venv에 `/usr/bin/timeout 600 uv pip install -v --only-binary rawpy -e ".[raw]" 2>&1 | tee $E/install.log` — `--only-binary rawpy`라서 맞는 휠이 없으면 소스 빌드로 넘어가지 않고 **오류로 끝난다**(그러면 그 오류 줄을 보고하고 멈춘다; 빌드 도구 설치·플래그 제거 금지). 성공하면 `grep -i -E 'rawpy.*\.whl' $E/install.log`, `uv pip show -f rawpy | grep -i -E 'whl|\.so'`, `python -c "import rawpy,os;print(rawpy.__file__)"`로 찾은 확장 모듈(`_rawpy*.so`)에 `file`, 그다음 `python -c "import rawpy, platform; print(rawpy.__version__, platform.machine()); print(rawpy.flags)"`.
- **허용 파일**: `docs/runbooks/mac-setup.md` §8 #24 "확인 결과" 칸의 **rawpy 절반만**(EgoBlur MPS 절반은 그대로 비운다).
- **완료 기준**: 설치 명령 종료 코드, 로그의 휠 파일 이름 줄 원문(`grep` 출력), 확장 모듈 `file` 출력(`arm64` 포함 여부), `rawpy.flags` 출력 원문을 칸과 PR에. `--only-binary` 오류로 끝나면 그 오류 원문만 적고 "arm64 휠 없음(이 명령·날짜 기준)"으로 좁혀 쓴다(규칙 3).
- **왜 재환 / 위험**: 명령 두 개로 판정된다. MPS 절반은 EgoBlur 모델 동의(소유자)가 필요해 재환 일이 아니다.
- **결과(2026-11-28, [#145](https://github.com/wooklym/golmok/pull/145) · `84ad068`, 리뷰 R145 → R145-2)**: mac-setup §8 #24 "확인 결과" 칸에 rawpy 절반만 채웠다(Mac arm64, uv, CPython 3.12.16, 별도 venv). 설치 명령은 `pipestatus[1]`=0으로 끝났다. 휠 선택 줄 원문은 `DEBUG Selecting: rawpy==0.28.0 [compatible] (rawpy-0.28.0-cp312-cp312-macosx_11_0_arm64.whl)`이고, 확장 모듈 `_rawpy.cpython-312-darwin.so`의 `file` 출력은 `Mach-O 64-bit bundle arm64`다. `rawpy.flags` 원문도 칸에 있다(GPL2/GPL3 데모자이크 팩은 False). EgoBlur MPS 절반은 빈 칸 그대로다. R145는 병합을 한 번 보류했다. 과제가 비워 두라고 한 EgoBlur 절반에 `[미확인]` 문장을 썼고(규칙 6·14), 본문은 "그대로 뒀다"고 써 diff와 달랐다(규칙 1). 완료 기준이 "칸과 PR에" 요구한 grep 줄과 `rawpy.flags` 원문이 칸에 빠져 있었고(규칙 10·14), 칸의 명령도 실행한 그대로가 아니었다. 고친 커밋 `e6551a9`(EgoBlur 문장 삭제, 원문 기입, 실행한 명령 그대로)를 R145-2에서 영록이 직접 확인했다(diff는 #24 한 행, 칸의 원문이 증거 로그와 일치).

#### J-09 확인된 §8 행의 `[미확인]` 주석 정리
- **출처**: mac-setup §8 #1·#2(엔진 루트·`-Cmd` 위치 확인됨), #5(`test.sh`의 `-nullrhi` 확인됨 — **`add-gasp.sh`는 [미확인] 그대로**), §9 FMA 행(`MacToolChain.cs:209`). 대상 주석: `tools/ue/common.sh:4`, `:13`, `:25`, `:43`의 `test.sh` 부분, `tools/ue/test.sh:6`, `tools/tests/test_ue_geo_math.py:79`.
- **할 일**: 확인된 내용만 주석을 "확인(2026-11-27, mac-setup §8 #n)"으로 바꾼다. `add-gasp.sh:24`·`package.sh:26`·`_pure.py`는 건드리지 않는다(아직 미확인 — J-15·J-16).
- **허용 파일**: `tools/ue/common.sh`, `tools/ue/test.sh`, `tools/tests/test_ue_geo_math.py`(주석 줄만).
- **완료 기준**: 바꾼 줄마다 PR 표에 "줄 → 근거 §8 행/파일:줄". `pytest -q tests/test_ue_mac_scripts.py tests/test_ue_python_spike_runner.py tests/test_ue_geo_math.py`(`test_ue_mac_scripts.py:46`은 주석을 지우고 단언한다) + 파이썬 게이트 + CI 초록. `bash -n tools/ue/*.sh`.
- **왜 재환 / 위험**: 근거 대조만 하는 일. 위험: 아직 미확인인 것(#5의 add-gasp 절반)까지 지우는 것 — 규칙 1.
- **결과(2026-11-28, [#146](https://github.com/wooklym/golmok/pull/146) · `34d0c6f`, 리뷰 R146)**: 주석 줄만 바꿨다(3파일, +12 −8). `common.sh`의 머리말(:4)·설치 배치(:13)·`-Cmd` 위치(:25-27)는 §8 #1·#2, `-nullrhi`(:44-45)와 `test.sh:5-7`은 §8 #5, `test_ue_geo_math.py:79-80`은 §9 FMA 행(`MacToolChain.cs:209`)을 근거로 "확인(2026-11-27, mac-setup §8 #n)"이 되었다. §8 #5의 add-gasp 절반은 `[미확인]` 그대로다(`add-gasp.sh:24`·`package.sh:26`·`_pure.py`는 건드리지 않음). 지정 pytest 3파일 125 passed, 게이트 1936 passed, 3 skipped, `bash -n` 통과, CI 12/12 pass. R146 재현: 주석을 뺀 셸 본문이 전후 같고 Python은 `ast.dump`가 같다. 병합 결과 트리에서도 125 passed. 코드는 통과했지만 본문에 "완료 기준 대조" 절이 없어 한 번 돌려보냈다(규칙 14, #142에 이은 2번째). 과제 인용도 글자 그대로가 아니었다. 재환이 본문만 고친 뒤 병합했다.
- **메모(R146 "참고")**: `common.sh` 머리 주석(:4·:13)은 엔진 경로 전체를 "§8 #1·#2로 확인"이라고 적어서 Build.sh·RunUAT.sh 경로도 그 근거로 읽힌다. 그런데 그 둘을 확인한 근거는 §8 #4와 §9 §4-5다. J-09는 과제가 #1·#2만 지목해 그대로 두었다. 다음에 `common.sh` 주석을 고치는 과제는 §8 #4·§9 §4-5도 함께 적는다. J-16은 `common.sh`를 고치지 않는다. J-10은 `common.sh`에 shellcheck 지시문 줄만 더하고 머리 주석은 허용 범위 밖이라, 이 정정은 영록이 그 뒤 과제에 넣는다.

#### J-10 CI shellcheck 잡 — 설계 확정(Opus 2026-11-28)
- **출처**: 2026-11-28 코드 조사. `.github/workflows/ci.yml`에는 셸 린트가 없다(착수 시점 `wc -l` 값과 `sed -n '/^jobs:/,$p' .github/workflows/ci.yml | grep -E '^  [a-z-]+:$'` 잡 목록을 할 일 1에서 `$E`에 기록한다). 이 Mac에는 shellcheck가 없다(`command -v shellcheck` 빈 출력, `/opt/homebrew/bin`·`/usr/local/bin`에도 없음). 대상 셸 파일은 10개다: `tools/ue/{common,build,generate-project-files,open-editor,package,test,add-mannequin,add-gasp}.sh`, `tools/mac/{install-recon-tools,recon-smoke}.sh`. `tools/mac/objcap`은 Swift라 대상이 아니다. 기존 억제는 3곳이다: `tools/ue/test.sh:39`·`tools/ue/add-gasp.sh:116`(SC2086, RhiArgs)과 `tools/mac/install-recon-tools.sh:106`(SC2086, RECON_SPECS). 예전 표기 `test.sh:36`은 J-34 뒤에 :39로 바뀌었다. bash 3.2 검사와 `bash -n`은 `tools/tests/test_ue_mac_scripts.py:60`·`:278`과 `tools/tests/test_mac_recon_scripts.py:40`·`:128`에 있다. [mac-setup](../runbooks/mac-setup.md)에는 shellcheck 언급이 없다(`grep -i shellcheck` 0줄).
- **설계 (확정, Opus 2026-11-28)**:
  1. **어디서 도는가**: **ubuntu 행 하나짜리 새 CI 잡 `shellcheck`만 둔다.** pytest 테스트는 만들지 않는다. 이유: `ubuntu-latest`(현재 Ubuntu 26.04)에는 apt shellcheck 0.11.0-2가 깔려 있지만 macOS·Windows 러너와 로컬 Mac에는 없다. 그래서 "없으면 skip" 테스트는 행마다 다른 버전으로 돌거나 조용히 건너뛰어 증거가 되지 못한다. 등록 목록 테스트(`CONSOLE_COMMANDS`·`BUILD_CS_*`·`CONVENTION_FOLDERS`)와 `check_repo.py`·`pyproject.toml`은 **건드리지 않는다**. 이 잡은 러너의 apt 판이 아니라 설계 2의 내려받은 바이너리를 쓰므로 `runs-on: ubuntu-latest`를 그대로 둔다(J-11의 `ubuntu-24.04` 고정은 Playwright 때문이고 이 잡과는 상관없다).
  2. **버전 고정**: 러너에 깔린 apt 판 대신 **공식 릴리스 v0.11.0(2025-08-04, 최신 stable)** 정적 바이너리를 sha256으로 확인해 쓴다. 이렇게 하면 로컬 Mac(`darwin.aarch64`)과 CI(`linux.x86_64`)가 같은 업스트림 버전이 되고, 이미지가 바뀌어도 결과가 그대로다. `GITHUB_PATH`는 PATH 맨 앞에 붙으므로 러너의 `/usr/bin/shellcheck`보다 먼저 잡힌다. 그래도 버전 줄을 단언해서 확인한다. 라이선스는 GPL-3.0이다. CI와 `$E`에서 실행만 하는 개발 도구이고 저장소·게임·제품 파이프라인에 들어가지 않는다. D-002의 금지(비상업·AGPL)에 해당하지 않는다.
  3. **플래그(고정)**: `shellcheck --shell=bash --external-sources --source-path=SCRIPTDIR --severity=warning --format=gcc tools/ue/*.sh tools/mac/*.sh`. `--shell=bash`가 있어야 shebang 없는 `common.sh`도 검사된다(그러지 않으면 SC2148). `-x`와 `SCRIPTDIR`를 함께 써야 `source "$(dirname "${BASH_SOURCE[0]}")/common.sh"`를 따라간다(Directive 위키: 앞의 동적 부분 하나를 떼고 나머지를 찾는다). 그래서 소스 지시문은 **더하지 않는다**. 못 따라가면 SC1090·SC1091·SC2154로 드러나고, 그때는 멈춘다(규칙표). 심각도는 **warning 이상**(error+warning)으로 시작한다. info·style(SC2015 등)은 고치려면 코드가 바뀌는 제안이라 이번에는 막지 않는다. 전역 `-e` 제외와 `.shellcheckrc`는 **쓰지 않는다**. 전역 제외는 앞으로 생길 진짜 결함도 숨기기 때문이다.
  4. **기존 결함 처리 — 고치지 않는다, 지시문만 더한다**: J-10은 스크립트의 실행 줄을 한 줄도 바꾸지 않는다. 결함은 아래 표에 있는 것만 **바로 윗줄에 한 줄짜리 지시문**으로 억제한다. 표에 없는 코드나 위치가 나오면 재환은 고치지도 억제하지도 않고 **멈춰서** 출력 원문을 영록에게 보낸다. 영록이 이 표를 늘린 뒤에 다시 진행한다.

     | 코드 | 이 위치에서만 | 더할 줄(그 줄 바로 위, 들여쓰기는 아래 줄과 같게, 문구 그대로) |
     |---|---|---|
     | SC2034 | `tools/ue/common.sh`의 변수 대입 줄(예상: `Project`·`UEBuild`·`UERunUAT`·`GolmokPython` [미확인]) | `# shellcheck disable=SC2034  # used by the scripts that source common.sh` |
     | SC2327·SC2328 | `$(cd -- … >/dev/null … && pwd …)` 꼴 대입 줄(`common.sh:10`, `add-gasp.sh:45`·`:145`, `install-recon-tools.sh:51`·`:68`, `recon-smoke.sh:42`·`:57`·`:58`·`:90` 후보, 실제로 나는지 [미확인]) | `# shellcheck disable=<그 줄에 보고된 코드, 쉼표로>  # cd prints the directory when CDPATH is set; only pwd output is captured` |
     | SC1090·SC1091·SC2154 | 어디든 | **멈춤**(`common.sh`를 따라가지 못한 것: 소스 지시문은 영록이 정한다) |
     | SC2086 | 이미 지시문이 있는 3곳 밖 | **멈춤** |
     | 그 밖 모든 코드, 또는 위 코드가 다른 위치 | — | **멈춤** |

     덧붙이는 규칙: 한 줄에 표의 코드가 둘 나오면 지시문 한 줄에 쉼표로 적는다. 결함 줄이 heredoc 안(`<<'PY'` … `PY`, `<<EOF` … `EOF`)이거나, 앞줄이 `\`로 끝나는 이어진 줄이거나, 셔뱅 첫 줄이면 **멈춘다**. 첫 줄 위에는 아무것도 넣지 않는다(테스트가 `#!/bin/bash\n`·`#!/usr/bin/env bash\n` 시작을 단언한다).
  5. **동작이 바뀌지 않는다는 증명**: 바뀐 줄은 모두 `+`이고 모두 `# shellcheck disable=` 줄이다(완료 기준 (d)). 주석을 뺀 본문은 `origin/main`과 같다(같은 기준). 스텁 테스트 두 파일의 결과는 전과 같다(완료 기준 (f)). 두 테스트 파일의 `_code()`는 주석 줄을 빼고 보므로 지시문은 텍스트 단언에도 걸리지 않는다.
  6. **핫스팟**: `ci.yml`은 핫스팟이다. **파일 끝에만 덧붙인다**: 마지막 줄 뒤다. J-11이 병합됐으면 그 줄은 `  # [/J-11 hook]`이고, 아니면 `          grep -q '"numErrors": 0' validator.log`이다. 붙이기 전에 `tail -1 .github/workflows/ci.yml` 출력을 `$E/ci-tail.log`에 남긴다(할 일 1). 기존 줄은 고치지도 순서를 바꾸지도 않는다. 블록은 `# [J-10 hook]` … `# [/J-10 hook]`로 감싸고 **별도 커밋**(커밋 1, `ci.yml` 한 파일)으로 낸다. 정확한 블록은 아래 펜스 안의 30줄이다(첫 줄은 빈 줄, 나머지는 스페이스 2칸 이상으로 시작, 탭 없음). 손으로 옮기지 않고 할 일 3의 `sed` 명령으로 `$E/task.txt`에서 뽑아 붙인다.

```yaml

  # [J-10 hook] shellcheck for the Mac shell scripts (tools/ue/*.sh, tools/mac/*.sh); pinned official release
  shellcheck:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    defaults:
      run:
        shell: bash
    env:
      SHELLCHECK_VERSION: v0.11.0
      SHELLCHECK_SHA256: 8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198  # linux.x86_64.tar.xz
    steps:
      - uses: actions/checkout@v7
        with:
          lfs: false  # scripts only
      - name: Install shellcheck (pinned release, sha256 checked)
        run: |
          url="https://github.com/koalaman/shellcheck/releases/download/${SHELLCHECK_VERSION}/shellcheck-${SHELLCHECK_VERSION}.linux.x86_64.tar.xz"
          curl -fsSL --retry 3 -o "$RUNNER_TEMP/shellcheck.tar.xz" "$url"
          echo "${SHELLCHECK_SHA256}  $RUNNER_TEMP/shellcheck.tar.xz" | sha256sum -c -
          tar -xJf "$RUNNER_TEMP/shellcheck.tar.xz" -C "$RUNNER_TEMP"
          echo "$RUNNER_TEMP/shellcheck-${SHELLCHECK_VERSION}" >> "$GITHUB_PATH"
      - name: shellcheck --version
        run: |
          command -v shellcheck
          shellcheck --version | tee "$RUNNER_TEMP/shellcheck-version.txt"
          grep -qx "version: ${SHELLCHECK_VERSION#v}" "$RUNNER_TEMP/shellcheck-version.txt"
      - name: shellcheck (warning and above)
        run: shellcheck --shell=bash --external-sources --source-path=SCRIPTDIR --severity=warning --format=gcc tools/ue/*.sh tools/mac/*.sh
  # [/J-10 hook]
```

  `shell: bash`이면 스텝이 `bash --noprofile --norc -eo pipefail {0}`로 돈다. 그래서 `tee` 파이프에서도 실패가 묻히지 않는다. 종료 코드: 결함이 없으면 0, 있으면 1, 파일 오류는 2, 잘못된 호출은 3·4(shellcheck 매뉴얼). 버전 줄 형식 `version: 0.11.0`은 [미확인]이다. 할 일 1에서 로컬 출력으로 확인하고, 다르면 멈춘다. 이 블록은 Opus가 2026-11-28 scratch 사본에서 확인했다: `origin/main` `ci.yml` 끝에 붙이면 Ruby Psych(`/usr/bin/ruby` 2.6.10) 잡 목록이 `python repo-check tiles-validate shellcheck`, J-11 블록 뒤에 붙이면 `python repo-check tiles-validate viewer-smoke shellcheck`이고, 두 경우 모두 `git diff --numstat`이 `30	0`이다.
- **명령 공통**: 아래 명령은 모두 `$W`(절대 경로) 또는 `cd "$W" &&`·`cd "$E/sc" &&`로 시작한다(상시 규칙). 돌린 명령 원문은 `$E/commands.txt`에 한 줄씩 더하고, 출력은 적힌 `$E/…` 파일로 받는다(규칙 10). 각 단계의 "기대"와 다르면 아래 **멈춤 조건**을 본다. 셸 변수는 Bash 호출 사이에 남지 않는다. 그래서 변수를 쓰는 명령은 **같은 호출 안에서** 먼저 정의한다: 모든 명령은 `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/jaehwan/J-10";`로 시작한다. `$SC`를 쓰는 명령은 `SC="$E/sc/shellcheck-v0.11.0/shellcheck";`를, `$RUN`을 쓰는 명령은 그 커밋의 실행 번호를 저장한 `$E/run….tsv` 파일에서 `RUN=$(cut -f1 "<그 파일>" | head -1);`로 다시 읽어 앞에 붙인다. attempt 한 번의 단계 묶음((i)~(iii))은 `n=<번호>;`로 시작하는 **한 번의 호출**로 돌린다.
- **할 일**:
  1. **준비와 측정(커밋 없음)**:
     - 브랜치와 과제 원문: `E="$TMPDIR/jaehwan/J-10"; mkdir -p "$E"; git -C "$W" fetch origin && git -C "$W" switch -c local/jaehwan-j10-shellcheck origin/main && cd "$W" && sed -n '/^#### J-10/,/^#### J-11/p' docs/plan/jaehwan-tasks.md > "$E/task.txt"`(규칙 14). 기대: `head -1 "$E/task.txt"`가 `#### J-10 CI shellcheck 잡 — 설계 확정(Opus 2026-11-28)`, `sed -n '/^```yaml$/,/^```$/p' "$E/task.txt" | sed '1d;$d' | wc -l | tr -d ' '`가 `30`.
     - 착수 시점 `ci.yml`: `cd "$W" && wc -l < .github/workflows/ci.yml | tr -d ' ' > "$E/ci-wc.log"; sed -n '/^jobs:/,$p' .github/workflows/ci.yml | grep -E '^  [a-z-]+:$' > "$E/ci-jobs.log"; tail -1 .github/workflows/ci.yml > "$E/ci-tail.log"`. 기대(J-11 병합 뒤): `131` / `  python:`·`  repo-check:`·`  tiles-validate:`·`  viewer-smoke:` 네 줄 / `  # [/J-11 hook]`. J-11 병합 전이면 `94` / 앞의 세 줄 / `          grep -q '"numErrors": 0' validator.log`. 둘 다 아니면 멈춘다.
     - 내려받기: `mkdir -p "$E/sc" && cd "$E/sc" && /usr/bin/timeout 120 curl -fsSL --retry 3 -o sc.tar.xz https://github.com/koalaman/shellcheck/releases/download/v0.11.0/shellcheck-v0.11.0.darwin.aarch64.tar.xz > "$E/dl.log" 2>&1; echo $? > "$E/dl.rc"`. 기대: `$E/dl.rc`가 `0`.
     - 해시: `cd "$E/sc" && shasum -a 256 sc.tar.xz > "$E/sha.log" 2>&1`. 기대: `56affdd8de5527894dca6dc3d7e0a99a873b0f004d7aabc30ae407d3f48b0a79  sc.tar.xz` 한 줄. 다르면 멈춘다.
     - 풀기·버전: `cd "$E/sc" && tar -xJf sc.tar.xz && SC="$E/sc/shellcheck-v0.11.0/shellcheck" && "$SC" --version > "$E/sc-version.log" 2>&1; echo $? > "$E/sc-version.rc"`. 기대: `grep -x 'version: 0.11.0' "$E/sc-version.log"`가 한 줄. PATH·brew·`sudo`에는 설치하지 않는다(`$E` 안에서만 쓴다). 바이너리가 실행되지 않으면 오류 원문을 적고 멈춰 묻는다.
     - 측정: `cd "$W" && "$SC" --shell=bash --external-sources --source-path=SCRIPTDIR --severity=warning --format=gcc tools/ue/*.sh tools/mac/*.sh > "$E/sc-before.log" 2>&1; echo $? > "$E/sc-before.rc"`. 기대: `$E/sc-before.rc`가 `0`(결함 없음) 또는 `1`(결함 있음). `2`·`3`·`4`면 멈춘다.
     - 집계: `grep -oE '\[SC[0-9]+\]' "$E/sc-before.log" | sort | uniq -c > "$E/sc-codes.log"`(코드별 수), `grep -E '\[SC[0-9]+\]$' "$E/sc-before.log" | sed -E 's/^([^:]+):[0-9]+:[0-9]+: [a-z]+: .*\[(SC[0-9]+)\]$/\2 \1/' | sort | uniq -c > "$E/sc-code-file.log"`(코드·파일별 수). 결함 0이면 두 파일 모두 빈 파일이다.
     - info 판: 측정 명령의 `--severity=warning`만 `--severity=info`로 바꿔 `"$E/sc-before-info.log"`·`"$E/sc-before-info.rc"`로 돌리고, `grep -c -E 'SC109[01]|SC2154' "$E/sc-before-info.log" > "$E/sc-before-info.count"`. 기대: `0`. 0이 아니면 멈춘다.
  2. **스텁 테스트 기준선**: `cd "$W/tools" && source .venv/bin/activate && pytest -q tests/test_ue_mac_scripts.py tests/test_mac_recon_scripts.py > "$E/pytest-before.log" 2>&1; echo $? > "$E/pytest-before.rc"`. 기대: rc `0`, 요약 줄(`tail -1 "$E/pytest-before.log"`)은 `N passed …` 꼴이고 그 원문을 PR에 붙인다.
  3. **커밋 1(훅만)**:
     - 붙이기: `cd "$W" && tail -1 .github/workflows/ci.yml >> "$E/ci-tail.log" && sed -n '/^```yaml$/,/^```$/p' "$E/task.txt" | sed '1d;$d' >> .github/workflows/ci.yml`. 기대: `$E/ci-tail.log`의 두 줄이 같다(할 일 1 뒤 `ci.yml`이 바뀌지 않았다).
     - YAML 구문: `cd "$W" && ruby -ryaml -e 'y=YAML.load_file(".github/workflows/ci.yml"); puts y["jobs"].keys.join(" "); j=y["jobs"]["shellcheck"]; puts j["timeout-minutes"]; puts j["steps"].map{|s| s["name"]||s["uses"]}.join(" | ")' > "$E/yaml.log" 2>&1; echo "exit=$?" >> "$E/yaml.log"`. 기대는 완료 기준 (g)의 네 줄이다. `/usr/bin/ruby`는 macOS 기본이라 따로 설치하지 않는다.
     - 파일 수: `cd "$W" && git diff --name-only > "$E/c1-files.log"`. 기대: `.github/workflows/ci.yml` 한 줄.
     - 커밋·push: `cd "$W" && git add .github/workflows/ci.yml && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-10: CI shellcheck 잡 훅 블록" …`(서명은 규칙 7). 파이썬 게이트(규칙 13)를 돌린 뒤 push하고 PR을 연다. CI 칸에는 "CI 진행 중 — 결과는 아래에 추가"만 쓴다(규칙 2a).
     - 실행 찾기·기다리기(커밋마다 같은 순서, `<c>` = `c1`·`c2`·`c3`·`c4`): `cd "$W" && gh run list --workflow CI --branch local/jaehwan-j10-shellcheck --event push --limit 1 --json databaseId,headSha --jq '.[0]|[.databaseId,.headSha]|@tsv' > "$E/run-<c>.tsv"; git rev-parse HEAD >> "$E/run-<c>.tsv"`. 기대: `[ "$(sed -n 1p "$E/run-<c>.tsv" | cut -f2)" = "$(sed -n 2p "$E/run-<c>.tsv")" ] && echo same || echo DIFFERENT`가 `same`. `DIFFERENT`면(실행이 아직 목록에 없을 때 포함) 30초 뒤 같은 명령을 다시 돌리고, 5분 넘게 `DIFFERENT`면 멈춘다. `RUN=$(cut -f1 "$E/run-<c>.tsv" | head -1)`. `/usr/bin/timeout 1800 gh run watch "$RUN" --interval 30 > "$E/watch-<c>.log" 2>&1; echo "exit=$?" >> "$E/watch-<c>.log"`(규칙 5). 기대: 끝 줄 `exit=0`. `exit=124`면 멈춘다. **다음 push는 이 watch가 끝난 뒤에만 한다**(`concurrency: cancel-in-progress`라서 앞 실행이 취소된다).
     - CI 결함 줄 대조: `JID=$(gh run view "$RUN" --json jobs --jq '.jobs[]|select(.name=="shellcheck")|.databaseId'); gh run view --job "$JID" --log | grep -oE 'tools/(ue|mac)/[^ :]+\.sh:[0-9]+:[0-9]+: [a-z]+: .*\[SC[0-9]+\]$' > "$E/sc-ci1.log"; grep -E '\[SC[0-9]+\]$' "$E/sc-before.log" > "$E/sc-before.issues"; diff "$E/sc-before.issues" "$E/sc-ci1.log" > "$E/sc-diff.log"; echo "exit=$?" >> "$E/sc-diff.log"`. 기대: `$E/sc-diff.log`가 `exit=0` 한 줄. `shellcheck` 행은 할 일 1에 결함이 있으면 빨강, 없으면 초록이다.
  4. **커밋 2(지시문)**: 할 일 1의 결함마다 설계 4의 표를 적용한다. 표 밖의 것이 하나라도 있으면 4~8을 하지 않고 멈춰 보고한다. 지시문 줄만 넣는다. 허용 파일 안에서만, 동작 변경 없이. 커밋(규칙 7 `-c`)·게이트(규칙 13)·push 뒤 할 일 3의 "실행 찾기·기다리기"를 `c2`로 한다.
  5. **로컬 재측정**: 할 일 1의 측정 명령을 `"$E/sc-after.log"`·`"$E/sc-after.rc"`로, info 판을 `"$E/sc-after-info.log"`로 돌린다. 할 일 2의 pytest를 `"$E/pytest-after.log"`·`.rc`로 돌린다. `cd "$W" && for f in tools/ue/*.sh tools/mac/*.sh; do /bin/bash -n "$f" || echo "FAIL $f"; done > "$E/bash-n.log" 2>&1`(기대: 빈 파일). 파이썬 게이트(규칙 13)를 `"$E/gate.log"`로 돌린다.
  6. **커밋 3(일부러 깨뜨림)**: `cd "$W" && printf '#!/usr/bin/env bash\nj10_unused=1\n' > tools/mac/j10-break.sh`(실행 비트 없음). 기대: `wc -l < tools/mac/j10-break.sh | tr -d ' '`가 `2`. 커밋·push 뒤 `c3`로 기다린다. `gh run view "$RUN" --log-failed | grep 'j10-break.sh:2:1: warning: .*\[SC2034\]' > "$E/break.log"`. 기대: `wc -l < "$E/break.log" | tr -d ' '`가 `1`. `gh pr checks <n> > "$E/checks-c3.log"`에서 `shellcheck`만 fail이고 나머지 행은 pass다.
  7. **커밋 4(원복)**: `cd "$W" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" revert --no-edit <커밋 3 sha>`, `git -C "$W" log -1 --format='%an <%ae>' > "$E/author-c4.log"`(기대: `재환 <jaehwan.local@localhost>` 한 줄, 규칙 7). push 뒤 `c4`로 기다리고, 모든 행 초록이다. force-push·rebase는 금지다.
  8. **8회 측정(규칙 11)**: 커밋 4(HEAD)의 push 실행 `RUN=$(cut -f1 "$E/run-c4.tsv" | head -1)`에서 `shellcheck` 잡을 attempt 1 + rerun 7회, 모두 8회 돌린다. `main`에는 이 잡이 없으므로 규칙 11의 main 쪽 횟수는 해당 없음이다. attempt n(1~8)마다 순서대로:
     - (i) n ≥ 2이면 `JOB=$(gh run view "$RUN" --json jobs --jq '.jobs[]|select(.name=="shellcheck")|.databaseId'); gh run rerun "$RUN" --job "$JOB"`, 이어서 `until [ "$(gh run view "$RUN" --json attempt --jq .attempt)" = "$n" ]; do sleep 10; done`.
     - (ii) `/usr/bin/timeout 1800 gh run watch "$RUN" --interval 30 > "$E/sc-watch-$n.log" 2>&1; echo "exit=$?" >> "$E/sc-watch-$n.log"`.
     - (iii) `gh api repos/wooklym/golmok/actions/runs/$RUN/attempts/$n/jobs --jq '.jobs[]|select(.name=="shellcheck")|[.run_attempt,.conclusion]|@tsv' >> "$E/attempts.tsv"`.
     - (iii)의 결론이 `success`가 아니면 멈춘다. 남은 attempt를 돌리지 않고 로그와 함께 묻는다.
  9. **PR 본문**: "완료 기준 대조"(규칙 14) 절에 아래 (a)~(j)를 한 줄씩(충족 + 증거 파일, 또는 **미충족** + 이유) 둔다. 과제 문장은 `$E/task.txt`에서만 옮긴다. "제출 전 점검표"는 규칙 1~15를 한 줄씩 과거형과 결과로 쓴다. `gh pr checks <n>` 출력을 붙인 뒤 본문을 다시 읽는다(규칙 12).
- **허용 파일**: `.github/workflows/ci.yml`(파일 끝의 `# [J-10 hook]` 블록만, 커밋 1 단독). `tools/ue/common.sh`·`tools/ue/add-gasp.sh`·`tools/mac/install-recon-tools.sh`·`tools/mac/recon-smoke.sh`(설계 4 표의 지시문 줄 **추가만**). `tools/mac/j10-break.sh`(커밋 3에서 만들고 커밋 4에서 없앰 — 최종 트리에 없다). 나머지 6개 `.sh`, 테스트 파일, `check_repo.py`, 등록 목록 테스트, `.shellcheckrc`, 공유 문서는 건드리지 않는다. 표가 다른 파일을 가리키면 멈춘다.
- **멈춤 조건(정하지 말고 영록에게 묻는다)**: 해시·버전 줄이 기대와 다를 때. 측정·info·after 명령의 rc가 0·1·2·3·4 밖(예: 127)일 때. `sc-before.rc`가 2~4일 때. info 판에 SC1090·SC1091·SC2154가 있을 때. 설계 4 표 밖의 코드·위치·heredoc·이어진 줄·셔뱅 줄 결함. `ci-wc.log`·`ci-jobs.log`·`ci-tail.log`가 할 일 1의 두 경우 어느 쪽도 아닐 때. `yaml.log`가 (g)와 다를 때. `sc-diff.log`가 `exit=0` 한 줄이 아닐 때. 실행이 5분 넘게 목록에 없거나 watch가 `exit=124`일 때. 커밋 3에서 `break.log`가 한 줄이 아니거나 다른 행이 빨강일 때. 8회 중 하나라도 `success`가 아닐 때. 허용 파일 밖을 바꿔야 할 것 같을 때.
- **완료 기준**:
  - (a) 측정: `$E/dl.rc` `0`, `$E/sha.log`가 위 기대 값과 같다, `$E/sc-version.log`의 `version:` 줄 원문, `$E/sc-before.rc` 값, `$E/sc-codes.log`·`$E/sc-code-file.log` 원문, `$E/sc-before-info.count`가 `0`. 할 일 3의 `$E/sc-diff.log`가 `exit=0` 한 줄이다(다르면 그 내용을 적고 멈춘 기록을 남긴다).
  - (b) 결함 하나하나가 설계 4 표의 어느 행에 해당하는지 PR 표에 "파일:줄 → 코드 → 표 행"으로 적는다. 표 밖의 결함이 있었으면 멈춘 기록만 남기고 (c) 이하는 하지 않는다.
  - (c) 고친 뒤: `$E/sc-after.rc`가 `0`이고 `wc -l < "$E/sc-after.log" | tr -d ' '`가 `0`. `grep -c -E 'SC109[01]|SC2154' "$E/sc-after-info.log"`가 `0`.
  - (d) 지시문만 더했다: `cd "$W" && git diff origin/main...HEAD -- tools/ue tools/mac | grep -E '^[-+]' | grep -v -E '^(\+\+\+|---) ' | grep -v -E '^\+[[:space:]]*# shellcheck disable=SC[0-9]+(,SC[0-9]+)*  # .+$' | wc -l | tr -d ' '` → `0`. `cd "$W" && for f in tools/ue/*.sh tools/mac/*.sh; do diff <(git show origin/main:$f | grep -v '^[[:space:]]*#') <(grep -v '^[[:space:]]*#' $f) > /dev/null || echo "DIFF $f"; done > "$E/body-diff.log" 2>&1; echo "exit=$?" >> "$E/body-diff.log"` → `$E/body-diff.log`는 `exit=0` 한 줄이다. `cd "$W" && ls tools/ue/*.sh tools/mac/*.sh | wc -l | tr -d ' '` 출력은 `10`이다.
  - (e) 지시문 수: `cd "$W" && git diff origin/main...HEAD -- tools/ue tools/mac | grep -c '^+.*# shellcheck disable='`가 `grep -E '\[SC[0-9]+\]$' "$E/sc-before.log" | cut -d: -f1,2 | sort -u | wc -l | tr -d ' '`와 같다. 결함 0이면 둘 다 `0`이다.
  - (f) 동작 불변: `pytest-before`와 `pytest-after`의 요약 줄(passed·skipped 수)이 같다(원문 두 줄). `$E/bash-n.log`가 빈 파일이다. `$E/gate.log`의 파이썬 게이트가 통과한다.
  - (g) `ci.yml`: `cd "$W" && git diff origin/main...HEAD --numstat -- .github/workflows/ci.yml` 출력은 `30	0	.github/workflows/ci.yml`이다(빈 줄 1 + 블록 29). `cd "$W" && git diff origin/main...HEAD -- .github/workflows/ci.yml | grep -c '^-[^-]'` → `0`. `cd "$W" && grep -c -E '^  # \[/?J-10 hook\]' .github/workflows/ci.yml` → `2`. `cd "$W" && diff <(git diff origin/main...HEAD -- .github/workflows/ci.yml | grep '^+' | grep -v '^+++' | cut -c2-) <(sed -n '/^```yaml$/,/^```$/p' "$E/task.txt" | sed '1d;$d')` 출력은 비어 있다. 할 일 3의 `$E/yaml.log`는 `python repo-check tiles-validate viewer-smoke shellcheck` / `5` / `actions/checkout@v7 | Install shellcheck (pinned release, sha256 checked) | shellcheck --version | shellcheck (warning and above)` / `exit=0`이다. J-11이 아직 병합되지 않았으면 첫 줄은 `python repo-check tiles-validate shellcheck`다. `cd "$W" && git show --stat --format= <커밋 1>` 출력은 `ci.yml` 한 줄과 요약 줄(`1 file changed, 30 insertions(+)`)뿐이다.
  - (h) CI: 커밋 1·2·3·4 각각의 `gh pr checks <n>` 표 원문. 커밋 3에서는 `shellcheck` 행(push·pull_request 두 줄)만 fail이고 `$E/break.log`가 한 줄이다. 커밋 4(HEAD)에서는 `shellcheck`를 포함한 모든 행이 pass다. `git -C "$W" ls-tree HEAD tools/mac/j10-break.sh` → 빈 출력.
  - (i) `git -C "$W" status --porcelain` → 빈 출력. 내려받은 shellcheck는 `$E`에만 있다(`command -v shellcheck` → 빈 출력 그대로).
  - (j) 8회: `wc -l < "$E/attempts.tsv" | tr -d ' '`가 `8`, `cut -f2 "$E/attempts.tsv" | sort | uniq -c | sed -E 's/^ +//'` 출력은 `8 success`다. `main` 쪽 횟수는 해당 없음(이 잡이 main에 없다).
- **병합 시 반영(영록)**: DECISIONS에 오케스트레이터 결정 1줄(shellcheck v0.11.0 고정, GPL-3.0 CI 전용 도구, `--severity=warning`, 고치지 않고 줄별 지시문으로만 억제, 표 밖 결함은 영록이 판단). mac-setup에 로컬 실행 명령 1줄(선택).
- **왜 재환 / 위험**: 정책은 이 메모가 다 정했고, 재환은 측정하고 표를 적용하고 명령으로 증명하기만 한다. 위험: ① 표 밖 결함을 재환이 "사소하다"며 고치거나 억제하는 것(규칙 1·6) — 멈춤 규칙과 (d)·(e)로 막는다. ② `common.sh`를 따라가지 못했는데 warning 판이 조용한 것 — info 판 `SC1090·SC1091·SC2154` 0으로 막는다. ③ push를 연달아 해서 CI 실행이 취소되는 것 — 할 일 3의 "기다리기". ④ 버전 줄 형식이나 다운로드 URL이 메모와 다른 것 — 할 일 1에서 먼저 드러나며, 그때는 멈춘다. ⑤ 깨뜨린 커밋을 force-push로 지우는 것 — 금지, revert만 한다. ⑥ 내려받기가 있는 새 필수 잡의 간헐 실패 — (j)의 8/8로 막는다.
- **dry-run 범위(Opus 2026-11-28)**: scratch 사본에서 돌려 기대 출력을 확인한 것은 블록 추출 `sed`, `ruby -ryaml`(두 경우), numstat·`grep -c`·블록 `diff`, `git show --stat`, (d)의 본문 `diff` 루프(10개 모두 `exit=0`), (e)·할 일 1의 `grep`·`cut`·`sort`·`sed` 파이프(표본 입력), 할 일 3의 CI 로그 추출(표본 로그 줄), 할 일 6의 `printf`(2줄). GitHub 실행이 필요한 명령(`gh run list/watch/view/rerun`, `gh api …/attempts`, `gh pr checks`)과 shellcheck 실행 자체(이 Mac에 없음)는 dry-run하지 못했다.

#### J-11 CI 뷰어 `npm test` 잡 (ubuntu-24.04 1행, 훅 블록)
- **출처**: STATUS WP-11 행("CI에는 `npm test` 잡 없음(로컬 게이트)"), [WP-11](WP-11-viewer-collision-overlay.md) 남은 작업("필요하면 별도 WP로 Playwright CI 잡(브라우저 다운로드 포함) 추가"), `tools/viewer/README.md:79`("CI는 뷰어 스모크를 돌리지 않아 … 드러나지 않았다"), 작업 규칙 1의 #136 반복 실수("Linux/Windows의 스모크 동작은 CI로 확인" — CI는 그때도 지금도 `npm test`를 돌리지 않는다), 스모크 이력 #131(준비 줄 버퍼링)·#133(30초 준비 제한·정리)·#134(신호 정리, main에서도 1/8 실패)·#135(accept 큐 백로그 5 → 128, baseline 5/20 → 0/20)·#136(실패 시 서버 출력 덤프를 finally로).
- **설계 (확정, Opus 2026-11-28)**: 재환은 아래를 그대로 옮긴다. 바꿀 점이 보이면 고치지 말고 묻는다.
  1. **OS 행은 `ubuntu-24.04` 하나만 둔다.** `ubuntu-latest`는 2026-11-27 현재 Ubuntu 26.04다(main 실행 46072482646의 `python (ubuntu-latest, …)`·`tiles-validate` "Set up job" 로그 `Image: ubuntu-26.04`, `Version: 20261122.9.1`). Playwright 1.56.1은 Ubuntu 메이저 26 이상을 `ubuntu26.04-x64`로 보고(공식 지원 아님) chromium 다운로드 경로가 없어 `ERROR: Playwright does not support chromium on ubuntu26.04-x64`로 실패한다(playwright v1.56.1 `packages/playwright-core/src/server/utils/hostPlatform.ts:82-90`, `registry/index.ts:1192-1217` — chromium 경로 표에는 `ubuntu20.04`·`22.04`·`24.04`만 있고 `'<unknown>': undefined`). 공식 지원 목록은 Ubuntu 22.04·24.04다(같은 태그 `docs/src/intro-js.md` "System requirements", https://playwright.dev/docs/intro#system-requirements). 레이블 `ubuntu-24.04`는 GitHub 호스트 러너 목록에 있다(https://github.com/actions/runner-images README 표 "Ubuntu 24.04 | x64 | `ubuntu-24.04`"). `package.json`은 허용 파일이 아니므로 Playwright를 올리는 길은 이 과제에 없다. 24.04에서는 `--with-deps`가 OS 의존성까지 설치한다(https://playwright.dev/docs/browsers "System dependencies can get installed automatically. This is useful for CI environments"). **macOS 행은 넣지 않는다.** 개발·검증 기계가 Mac(D-022)이라 이미 로컬에서 매번 돌리고(README "macOS에서 실행"), 이 Mac에서는 `playwright install`의 압축 해제가 멈춘 적이 있다(README "알려진 문제", 원인 [미확인]). CI 첫 행에 그 미확인 문제를 들이지 않는다. **Windows 행도 넣지 않는다.** `smoke.mjs`는 `python`/`python3` 분기, Windows에서 SIGHUP을 빼는 분기, `server.kill()`(Windows에서는 신호가 아니라 강제 종료)을 쓰는데 Windows에서 한 번도 돌린 적이 없다. 첫 잡에 미검증 경로를 섞지 않는다. 두 행과 `ubuntu-latest` 복귀(Playwright를 올린 뒤)는 이 잡이 8/8 초록으로 병합된 뒤 영록이 별도 과제로 판단한다.
  2. **Node는 `node-version: "22"`**(같은 파일 `tiles-validate`와 같은 메이저)로 고정하고 `actions/setup-node@v7`을 쓴다(파일의 `[WP-01 hook]` 메이저와 같다. https://github.com/actions/setup-node 는 v7을 최신으로 설명한다). 저장소에 `.nvmrc`가 없고 `package.json`에 `engines`도 없다. 이 과제에서 새로 만들지 않는다(Mac 로컬은 Node 26.13.1이라 하나로 맞출 근거가 없다).
  3. **`npm ci`는 쓰지 않고 `npm install --no-audit --no-fund`를 쓴다.** `.gitignore:42`가 `tools/viewer/package-lock.json`을 무시해서 잠금 파일이 없는데, `npm ci`는 잠금 파일을 요구한다(https://docs.npmjs.com/cli/commands/npm-ci). `.gitignore`는 바꾸지 않는다(공유 파일, 잠금 정책은 이 과제 범위 밖). 직접 의존성은 정확한 버전으로 고정되어 있다(`cesium 1.145.0`, `playwright 1.56.1`). 이행 의존성이 바뀌는 것은 `npm ls --depth=0` 출력을 로그에 남겨 추적한다. setup-node의 `cache: npm`도 쓰지 않는다. 문서는 잠금 파일을 커밋하라고 "strongly recommended" 하는데 잠금 파일이 없고, 설치는 로컬에서 5초(34 packages)였다.
  4. **Playwright 브라우저는 캐시하지 않는다.** 공식 문서: "Caching browser binaries is not recommended … Especially under Linux, operating system dependencies need to be installed, which are not cacheable."(https://playwright.dev/docs/ci). 설치 명령은 문서의 단일 브라우저 예 `npx playwright install --with-deps chromium`(https://playwright.dev/docs/browsers)을 그대로 쓴다. `--only-shell` 최적화는 이 과제에서 하지 않는다.
  5. **Python 쪽**: `actions/setup-python@v7` 3.12, `cache: pip`, `cache-dependency-path: tools/pyproject.toml`, `pip install -e ".[basemap,zone,mesh,splat,align,dev]"`(python 잡과 같은 줄)을 쓴다. 스모크는 `tests/test_basemap.py` 헬퍼(pyshp·rasterio·pyproj·pytest)로 합성 베이스맵을 만들고, `scripts/make_synthetic_zone.py`와 `golmok_tools.mesh.cli`(trimesh 등)로 zone을 만든 뒤 `python3 -m golmok_tools.viewer_server`를 띄운다. 그래서 외부 데이터·LFS·네트워크 픽스처가 필요 없다(`lfs: false`). 네트워크는 pip·npm·Playwright 다운로드에만 쓴다. Cesium은 `npm install`이 `node_modules`에 받아 서버가 `/cesium/`으로 주므로 CDN(`index.html:55`)을 쓰지 않는다. 24.04 러너에서 setup-python 3.12가 받아지는지는 [미확인]이다(attempt 1 로그에서 드러난다).
  6. **타임아웃**: 잡 `timeout-minutes: 25`(GitHub 기본 360분, https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax). 단계별로는 Python 설치 10, npm install 5, Playwright 설치 10, `npm test` 10분이다. 스모크 자체의 제한(준비 줄 30초, `waitForFunction` 120초 두 번)보다 위에 두라는 Playwright 지침("keep it comfortably above `globalTimeout`")을 따른다. 로컬 `npm test`는 63.41초(M5 Max, 첫 실행)였다. `smoke.mjs`의 제한값은 바꾸지 않는다.
  7. **재시도는 넣지 않는다.** 스텝 반복·retry 액션·`|| npm test`를 쓰지 않는다. #134·#135처럼 재시도는 실제 결함을 "한 번의 flake"로 숨긴다.
  8. **처음부터 필수 행으로 둔다.** `continue-on-error`를 쓰지 않는다. `main`에는 브랜치 보호가 없다(`gh api repos/wooklym/golmok/branches/main/protection` → 404 "Branch not protected"). 그래서 "필수"는 병합 규칙(규칙 2: 모든 행 초록)으로 정해지고, 병합 전 8/8 초록이 그 조건이다. 병합 뒤 실패가 나면 재시도로 넘기지 않고 과제로 연다.
  9. **훅 블록은 `jobs:`의 마지막(`tiles-validate`의 마지막 줄 `grep -q '"numErrors": 0' validator.log` 뒤)에 빈 줄 하나와 함께 덧붙인다.** 기존 줄은 한 글자도 바꾸지 않고, 순서도 바꾸지 않는다. J-10(shellcheck)도 같은 자리에 붙으므로 둘째로 병합하는 쪽이 다른 블록 뒤에 자기 블록을 둔다(둘 다 유지). 순서는 J-11 → J-10이다(J-10 설계 6).
  10. **덧붙일 YAML**: 아래 펜스 안의 37줄이다(첫 줄은 빈 줄, 나머지는 스페이스 2칸 이상으로 시작, 탭 없음). 손으로 옮기지 않고 할 일 2의 `sed` 명령으로 `$E/task.txt`에서 뽑아 붙인다. Opus가 2026-11-28 scratch 사본에서 확인했다: `origin/main` `ci.yml` 끝에 붙이면 Ruby Psych 잡 목록이 `python repo-check tiles-validate viewer-smoke`, `runs-on`이 `ubuntu-24.04`, 파일 131줄, `git diff --numstat`이 `37	0`이다.
```yaml

  # [J-11 hook] review viewer headless smoke (tools/viewer npm test), ubuntu-24.04 only (Playwright 1.56.1 does not support 26.04)
  viewer-smoke:
    name: viewer-smoke (ubuntu-24.04)
    runs-on: ubuntu-24.04
    timeout-minutes: 25
    defaults:
      run:
        working-directory: tools/viewer
    steps:
      - uses: actions/checkout@v7
        with:
          lfs: false  # the smoke builds its own synthetic basemap and zones
      - uses: actions/setup-python@v7
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: tools/pyproject.toml
      - uses: actions/setup-node@v7
        with:
          node-version: "22"
      - name: Install Python tools
        working-directory: tools
        timeout-minutes: 10
        run: python -m pip install -e ".[basemap,zone,mesh,splat,align,dev]"
      - name: npm install
        timeout-minutes: 5
        run: |
          npm install --no-audit --no-fund
          npm ls --depth=0
      - name: Playwright Chromium (with OS deps)
        timeout-minutes: 10
        run: npx playwright install --with-deps chromium
      - name: npm test
        timeout-minutes: 10
        run: npm test
  # [/J-11 hook]
```
  11. **간헐 실패 측정(규칙 11)**: 같은 커밋에서 브랜치 **push 이벤트 실행** 하나의 `viewer-smoke (ubuntu-24.04)` 잡을 attempt 1(push로 생긴 것)과 `gh run rerun <RUN> --job <JOB_ID>`로 만든 attempt 2~8까지 모두 8회 돌린다. 워크플로 `concurrency`가 `cancel-in-progress: true`라서 `gh workflow run`을 연달아 보내면 앞 실행이 취소된다. 그래서 dispatch는 쓰지 않고, rerun도 앞 attempt가 끝난 뒤에만 한다. `main`에는 이 잡이 없으니 규칙 11의 "origin/main 쪽 횟수"는 해당 없음으로 적는다. 같은 push의 pull_request 실행 결과도 표에 따로 한 줄 적는다(8회에 세지 않는다).
- **명령 공통**: 아래 명령은 모두 `git -C "$W"`이거나 `cd "$W" &&`로 시작한다(상시 규칙). 돌린 명령 원문은 `$E/commands.txt`에 한 줄씩 더하고, 출력은 적힌 `$E/…` 파일로 받는다(규칙 10). 각 단계의 "기대"와 다르면 아래 **멈춤 조건**을 본다. 셸 변수는 Bash 호출 사이에 남지 않는다. 그래서 변수를 쓰는 명령은 **같은 호출 안에서** 먼저 정의한다: 모든 명령은 `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/jaehwan/J-11";`로 시작한다. `$RUN`을 쓰는 명령은 그 커밋의 실행 번호를 저장한 `$E/run….tsv` 파일에서 `RUN=$(cut -f1 "<그 파일>" | head -1);`로 다시 읽어 앞에 붙인다. attempt 한 번의 단계 묶음((i)~(v))은 `n=<번호>;`로 시작하는 **한 번의 호출**로 돌린다.
- **할 일**:
  1. `E="$TMPDIR/jaehwan/J-11"; mkdir -p "$E"; git -C "$W" fetch origin && git -C "$W" switch -c local/jaehwan-j11-viewer-ci origin/main && cd "$W" && sed -n '/^#### J-11/,/^#### J-12 /p' docs/plan/jaehwan-tasks.md > "$E/task.txt"`(규칙 14). 기대: `grep -c '^#### J-11 CI 뷰어' "$E/task.txt"`가 `1`이고, `sed -n '/^```yaml$/,/^```$/p' "$E/task.txt" | sed '1d;$d' | wc -l | tr -d ' '`가 `37`이다.
  2. 붙이기: `cd "$W" && tail -1 .github/workflows/ci.yml > "$E/ci-tail.log" && sed -n '/^```yaml$/,/^```$/p' "$E/task.txt" | sed '1d;$d' >> .github/workflows/ci.yml`. 기대: `$E/ci-tail.log`가 `          grep -q '"numErrors": 0' validator.log`(J-10이 먼저 병합됐으면 `  # [/J-10 hook]` — 그때도 블록은 파일 끝에 붙는다). 그 밖이면 멈춘다. 다른 줄은 건드리지 않는다.
  3. `tools/viewer/README.md:79`에서 정확히 이 문장 `` CI는 뷰어 스모크를 돌리지 않아(`.github/workflows/ci.yml`의 잡은 python·repo-check·tiles-validate뿐) 드러나지 않았다. ``를 `` 당시(2026-11-27) CI는 뷰어 스모크를 돌리지 않아(잡은 python·repo-check·tiles-validate뿐) 드러나지 않았다. J-11 이후 CI의 `viewer-smoke`(ubuntu-24.04 한 행) 잡이 `npm test`를 돌린다. macOS·Windows 행은 없다. ``로 바꾼다. README의 다른 줄은 바꾸지 않는다.
  4. YAML 구문을 확인한다. `cd "$W" && ruby -ryaml -e 'y=YAML.load_file(".github/workflows/ci.yml"); puts y["jobs"].keys.join(" "); j=y["jobs"]["viewer-smoke"]; puts j["timeout-minutes"]; puts j["steps"].map{|s| s["name"]||s["uses"]}.join(" | ")' > "$E/yaml.log" 2>&1; echo "exit=$?" >> "$E/yaml.log"`(규칙 10). 기대는 완료 기준 (c)다. `/usr/bin/ruby`는 macOS 기본이라 따로 설치하지 않는다. actionlint 같은 도구도 설치하지 않는다.
  5. 커밋 1: `.github/workflows/ci.yml`만(`cd "$W" && git add .github/workflows/ci.yml && git diff --cached --name-only > "$E/c1-files.log"`, 기대: `.github/workflows/ci.yml` 한 줄). 커밋 2: `tools/viewer/README.md`만(같은 방법으로 `"$E/c2-files.log"`, 기대: `tools/viewer/README.md` 한 줄). 두 커밋 모두 규칙 7의 `-c` 작성자로 만들고, 커밋마다 `git -C "$W" log -1 --format='%an <%ae>' > "$E/author-<c>.log"`(`<c>`는 `c1`·`c2`)로 확인한다. 기대: `재환 <jaehwan.local@localhost>` 한 줄. 파이썬 게이트(규칙 13)를 `"$E/gate.log"`로 돌린 뒤 **두 커밋을 한 번에 push**하고 PR을 연다. 본문의 CI 칸에는 "CI 진행 중 — 결과는 아래에 추가"만 쓴다(규칙 2a). 8회 측정(할 일 6)은 커밋 2(HEAD)의 push 실행에서 한다.
  6. 8회 측정:
     - 실행 찾기: `cd "$W" && gh run list --workflow CI --branch local/jaehwan-j11-viewer-ci --event push --limit 1 --json databaseId,headSha --jq '.[0]|[.databaseId,.headSha]|@tsv' > "$E/run.tsv"; git rev-parse HEAD >> "$E/run.tsv"`. 기대: `[ "$(sed -n 1p "$E/run.tsv" | cut -f2)" = "$(sed -n 2p "$E/run.tsv")" ] && echo same || echo DIFFERENT`가 `same`. `DIFFERENT`면(실행이 아직 목록에 없을 때 포함) 30초 뒤 같은 명령을 다시 돌리고, 5분 넘게 `DIFFERENT`면 멈춘다. `RUN=$(cut -f1 "$E/run.tsv" | head -1)`.
     - attempt n(1~8)마다 순서대로: (i) n ≥ 2이면 `JOB=$(gh run view "$RUN" --json jobs --jq '.jobs[]|select(.name=="viewer-smoke (ubuntu-24.04)")|.databaseId'); gh run rerun "$RUN" --job "$JOB"`, 이어서 `until [ "$(gh run view "$RUN" --json attempt --jq .attempt)" = "$n" ]; do sleep 10; done`. (ii) `/usr/bin/timeout 1800 gh run watch "$RUN" --interval 30 > "$E/watch-$n.log" 2>&1; echo "exit=$?" >> "$E/watch-$n.log"`(규칙 5). (iii) `JID=$(gh api repos/wooklym/golmok/actions/runs/$RUN/attempts/$n/jobs --jq '.jobs[]|select(.name=="viewer-smoke (ubuntu-24.04)")|.id')`. (iv) `gh api repos/wooklym/golmok/actions/runs/$RUN/attempts/$n/jobs --jq '.jobs[]|select(.name=="viewer-smoke (ubuntu-24.04)")|[.run_attempt,.conclusion,.started_at,.completed_at]|@tsv' >> "$E/attempts.tsv"`. (v) `gh run view --job "$JID" --log > "$E/viewer-log-$n.txt" 2>&1`. (iv)의 결론이 `success`가 아니면 **멈춘다**. 남은 attempt를 돌리지 않고 실패 로그와 함께 영록에게 묻는다(재시도로 초록을 만들지 않는다).
     - 러너 확인: attempt 1 뒤 `grep -m1 'Image: ubuntu-24.04' "$E/viewer-log-1.txt" > "$E/image.log"`. 기대: 한 줄(`… Image: ubuntu-24.04`). 없거나, watch가 `exit=124`로 끝나거나(러너를 잡지 못한 경우 포함), 러너 레이블 오류가 보이면 멈추고 묻는다.
  7. PR 본문에 "완료 기준 대조"(규칙 14) 절을 두고 아래 (a)~(h)를 한 줄씩(충족 + 증거 파일, 또는 **미충족** + 이유) 적는다. 과제 문장은 `$E/task.txt`에서만 옮긴다. attempt 표의 열은 attempt·결론·시작·끝·소요(초, `attempts.tsv`에서 계산한 명령도 함께)·`npm test` 마지막 `OK:` 줄이다. "제출 전 점검표"는 규칙 1~15를 한 줄씩 과거형과 결과로 쓴다. 그다음 `gh pr checks <n>` 출력을 붙이고 본문을 다시 읽는다(규칙 12).
- **허용 파일**: `.github/workflows/ci.yml`(위 훅 블록 덧붙이기만), `tools/viewer/README.md`(할 일 3의 한 문장만). (`tools/viewer/README.md`는 상시 규칙의 공유 문서 `README.md`(저장소 루트)·`tools/README.md`가 아니다. 이 과제에서는 할 일 3의 한 문장만 허용한다.) `smoke.mjs`·`package.json`·`.gitignore`·`viewer_server.py`·테스트·공유 문서(STATUS WP-11 행의 "CI에는 `npm test` 잡 없음"은 병합 때 영록이 고친다)는 건드리지 않는다.
- **멈춤 조건(정하지 말고 영록에게 묻는다)**: `ci-tail.log`가 할 일 2의 두 경우가 아닐 때. `yaml.log`가 (c)와 다를 때. 실행이 5분 넘게 목록에 없을 때. watch가 `exit=124`일 때. `image.log`가 비었거나 러너 레이블 오류가 보일 때. 8회 중 하나라도 `success`가 아닐 때(WebGL·컨텍스트 오류 포함 — `smoke.mjs`에 launch 인자를 더하지 않는다). `OK:` 줄이 있는데 타일 수가 18이 아닐 때. 허용 파일 밖(`package.json`의 Playwright 판 등)을 바꿔야 할 것 같을 때.
- **완료 기준**:
  (a) `git -C "$W" diff --numstat origin/main...HEAD -- .github/workflows/ci.yml` 출력은 `37	0	.github/workflows/ci.yml`이다(빈 줄 1 + 블록 36, 삭제 0줄). `git -C "$W" diff origin/main...HEAD --name-only` 출력은 `.github/workflows/ci.yml`과 `tools/viewer/README.md` 두 줄뿐이다. `cd "$W" && diff <(git diff origin/main...HEAD -- .github/workflows/ci.yml | grep '^+' | grep -v '^+++' | cut -c2-) <(sed -n '/^```yaml$/,/^```$/p' "$E/task.txt" | sed '1d;$d')` 출력은 비어 있다.
  (b) `cd "$W" && grep -c -E '^  # \[/?J-11 hook\]' .github/workflows/ci.yml` 출력은 `2`다.
  (c) 할 일 4의 `yaml.log`는 `python repo-check tiles-validate viewer-smoke` / `25` / `actions/checkout@v7 | actions/setup-python@v7 | actions/setup-node@v7 | Install Python tools | npm install | Playwright Chromium (with OS deps) | npm test` / `exit=0`이다(Opus가 scratch 사본에서 이 출력을 확인했다). J-10이 먼저 병합됐으면 첫 줄은 `python repo-check tiles-validate shellcheck viewer-smoke`다.
  (d) `` cd "$W" && grep -c 'J-11 이후 CI의 `viewer-smoke`(ubuntu-24.04 한 행)' tools/viewer/README.md ``는 `1`이고, `` cd "$W" && grep -c 'CI는 뷰어 스모크를 돌리지 않아(`.github' tools/viewer/README.md ``는 `0`이다.
  (e) 같은 커밋(HEAD = 커밋 2)의 push 실행에서 `viewer-smoke (ubuntu-24.04)` attempt 1~8이 **8/8 success**다. `wc -l < "$E/attempts.tsv" | tr -d ' '`가 `8`이고 `cut -f2 "$E/attempts.tsv" | sort | uniq -c | sed -E 's/^ +//'` 출력은 `8 success`다. `grep -l 'OK: 18 tiles loaded, 2 zones with collision/blockers meshes' "$E"/viewer-log-*.txt | wc -l | tr -d ' '` 출력은 `8`이다. `OK:` 줄은 있는데 타일 수가 18이 아니면 성공으로 세지 않고 멈춰서 그 줄을 붙여 묻는다. `$E/image.log`가 한 줄이다.
  (f) 같은 커밋의 다른 모든 행(python 4행·repo-check·tiles-validate)이 초록이다. `gh pr checks <n>` 출력 원문을 붙인다(규칙 2).
  (g) 파이썬 게이트 로그(`$E/gate.log`)가 마지막 변경보다 새것이다(규칙 13). 이 과제는 파이썬 파일을 바꾸지 않으므로 수치는 main과 같아야 한다.
  (h) `cd "$W" && git log --format=%H origin/main..HEAD | while read c; do git show --name-only --format= $c; done` 출력은 `tools/viewer/README.md`, `.github/workflows/ci.yml` 두 줄이다(최신 커밋부터, 커밋마다 파일 한 줄).
- **왜 재환 / 위험**: 재환이 이 스모크의 실패 경로를 가장 잘 알고, 일은 정해진 블록을 붙이고 정해진 명령으로 8회 측정하는 것이다. 위험: ① 간헐 실패가 CI를 빨갛게 만드는 것. (e)의 8/8과 "실패하면 멈춤"으로 막는다. ② Linux 헤드리스 Chromium의 WebGL. `playwright-core` 1.56.1의 `lib/server/chromium/chromium.js:276-278`은 `--enable-unsafe-swiftshader`를 **darwin에서만** 붙인다. 그래서 GPU 없는 ubuntu 러너에서 Cesium이 WebGL 컨텍스트를 얻는지 [미확인]이다(2026-09 클라우드 Linux 세션의 통과 기록은 있지만 러너 환경과 같은지 [미확인]). 첫 attempt가 WebGL·컨텍스트 오류로 실패하면 `smoke.mjs`에 launch 인자를 더하지 말고 로그를 붙여 묻는다. ③ "CI가 X를 확인했다"는 문장은 (e)·(f) 출력이 나온 뒤에만 쓴다(규칙 1·2). ④ `ubuntu-latest`로 되돌리면 Playwright 1.56.1이 26.04에서 chromium을 받지 못한다(설계 1). 레이블은 설계 그대로 둔다.
- **dry-run 범위(Opus 2026-11-28)**: scratch 사본(`origin/main` `ci.yml` + 이 블록, 커밋 2개)에서 돌려 기대 출력을 확인한 것은 할 일 1·2의 블록 추출 `sed`(37줄), 할 일 4의 `ruby -ryaml`, (a)의 numstat·블록 `diff`, (b)의 `grep -c`, (e)의 `cut | sort | uniq -c | sed`(표본 8줄), (h)의 커밋별 파일 루프, 할 일 6의 `run.tsv` 비교(표본). macOS `wc -l`은 앞에 공백을 붙이므로 `| tr -d ' '`를 붙였다. GitHub 실행이 필요한 명령(`gh run list/watch/view/rerun`, `gh api …/attempts`, `gh pr checks`)과 README 문장 교체 뒤의 (d)는 dry-run하지 못했다.

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
- **출처**: mac-setup §9 §4-3(:324) "보고서 `succeeded` 칸은 23 … 나머지 16은 Warning 있는 성공(원인 [미확인])"(2026-11-27 메인 체크아웃 실행), WP-20 결과 절. 2026-11-28 새 숫자: J-12 보고서 `succeeded` 22 + `succeededWithWarnings` 17, J-12b 뒤 보고서 20 + 19. `succeeded` 칸은 Warning 없는 성공만 센다(두 칸의 합이 39). 2026-11-27의 23과 J-12의 22가 왜 다른지는 [미확인](다른 실행).
- **할 일**: J-12 보고서에서 테스트마다 경고 수와 첫 경고 문구·출처(파일·카테고리)를 뽑는 1회용 스크립트(`$E`에 둔다, 커밋 안 함).
- **허용 파일**: mac-setup §9 §4-3 행 메모 칸.
- **완료 기준**: 표(테스트 이름 · 경고 수 · 첫 경고 문구 원문)와 합계가 스크립트 출력과 같다(규칙 10). "무해하다"는 판정은 쓰지 않는다 — 영록(Opus) 몫.
- **왜 재환 / 위험**: 데이터 추출만. 위험: 해석을 사실처럼 쓰는 것.
- **결과(2026-11-28, [#139](https://github.com/wooklym/golmok/pull/139) · `49adc49`, 리뷰 R139 → R139-2)**: J-12 보고서 사본(`succeeded` 22 + `succeededWithWarnings` 17)에서 경고 있는 성공 **17건·경고 53개**를 8분류로 나눴다 — A′ `Failed to launch Tool(idevice_id)` 15, A idevice_id spawn 실패(`Bad CPU type`) 15, B GeoOrigin 없음(dev level) 7, C zone index cell v2/v1 1, D manifest `'spawn'` 키 1, E `NOT EXECUTED` 안내 2, F chunk 에셋 없음(wire box) 9, G collision 에셋 없음(fall-through 안내) 3. 보고서의 `succeeded` 칸이 경고 없는 성공만 센다는 것은 entries를 세어 확인했다(Warning 1개 이상 17, 0개 22). J-12b 뒤 보고서는 경고 있는 성공 19건·경고 67개다. D(`'spawn'`) 경고는 J-12 보고서에도 이미 있었다. 판정(무해/유해)은 쓰지 않았다(영록 몫). mac-setup §9 §4-3 칸에는 요약만 넣고, 내역은 표 아래 "§4-3 경고 분류 내역" 목록에 있다. 2026-11-27 실행의 23·16과 22·17이 1건 다른 원인은 [미확인] 그대로다.

#### J-14 `DEVELOPER_DIR` 전달 확인
- **출처**: mac-setup §8 #8(:294, 확인 결과 빈칸), `tools/ue/common.sh:2-3`(덮어쓰지 않는다는 주석).
- **할 일**: 이 Mac에는 Xcode가 하나뿐이고 `xcode-select -p`가 같은 경로를 가리켜, 실제 빌드 로그로는 전달 여부를 구분할 수 없다. 대신 스텁으로 확인한다: `tools/tests/test_ue_mac_scripts.py`의 스텁(Build.sh·UnrealEditor-Cmd가 argv를 기록)이 `DEVELOPER_DIR`도 기록하게 하고, `DEVELOPER_DIR=<센티널 경로>`로 `build.sh`(그리고 `test.sh`·`package.sh` 스텁 경로)를 돌려 스텁이 그 값을 받았는지 단언하는 pytest를 더한다. 변수를 주지 않았을 때 스크립트가 값을 만들지 않는지도 한 사례로 단언한다. 읽기 증거로 `grep -n DEVELOPER_DIR tools/ue/*.sh` 출력을 붙인다.
- **허용 파일**: `tools/tests/test_ue_mac_scripts.py`, mac-setup §8 #8 칸.
- **완료 기준**: (a) 새 테스트가 통과하고, 스텁의 환경 기록을 일부러 끈 상태(로컬 1회, 커밋 안 함)에서 실패하는 것을 출력으로(규칙 8). (b) `grep -n DEVELOPER_DIR tools/ue/*.sh` 원문. (c) 파이썬 게이트·CI 모든 행 초록. 결론 문장은 "스크립트가 환경 변수를 그대로 넘긴다(스텁 확인)"까지 — 실제 다른 Xcode로 빌드한 확인은 아니라고 적는다(규칙 3).
- **왜 재환 / 위험**: 작고 명령으로 끝난다.
- **결과(2026-11-28, [#141](https://github.com/wooklym/golmok/pull/141) · `30aa96d`, 리뷰 R141)**: 스텁이 호출 당시 `DEVELOPER_DIR`를 기록하게 하고 테스트 6개를 더했다(`-k developer_dir` → 6 passed). `grep -n DEVELOPER_DIR tools/ue/*.sh`는 `common.sh`의 주석 1줄뿐이고, 8개 스크립트 본문에 대입·`export`·`unset`이 없다는 것도 테스트로 고정했다. 공백이 든 센티널 경로는 `build.sh`·`package.sh`(RunUAT)·`test.sh`(UnrealEditor-Cmd)·`generate-project-files.sh`·`open-editor.sh`·`add-gasp.sh`에서 스텁까지 그대로 갔다. 단 `open-editor.sh`는 `open` 프로세스까지만 확인했고, 미설정 사례는 `build.sh`만 검사한다. 스텁의 기록을 끄면 5 failed, 1 passed였다(로컬 1회, 커밋 안 함). 결론은 "스크립트가 환경 변수를 그대로 넘긴다(스텁 확인)"까지이고, 실제 다른 Xcode로 빌드한 확인은 아니다([미확인]). mac-setup §8 #8 칸.

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
- **정정**(정정 2026-11-28: 위 할 일 ⑤는 `NightUnaffected`를 `Golmok.Weather.Runtime` 아래에 두었는데, 영록의 문서 오류다(R149). `GolmokWeatherTest.cpp`에서 `NightUnaffected()`는 `FLightingScenario`(:544)의 한 단계로 :585에서만 불리고, 그 시나리오의 등록 이름은 `Golmok.Weather.Lighting`(:1335)이다. `Golmok.Weather.Runtime`(:1355, `FRuntimeScenario` :895)은 이 단계를 돌리지 않는다. 그래서 ⑤ `Weather.Runtime`은 MPC·NS가 없으면 skip Info 2줄로 Success(= skip)이고, `[Info] NightUnaffected at …` 줄은 `test.sh --filter Golmok.Weather.Lighting` 보조 실행에서 본다(R149가 정한 기록 형태). 재환이 이 문장으로 이미 작업했으므로 할 일 문장은 고치지 않고 여기 적는다. 같은 오류가 있던 [pc-verify-v17.md](../runbooks/pc-verify-v17.md) §0 문장은 2026-11-28에 고쳤다.)

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
- **결과(2026-11-28, [#142](https://github.com/wooklym/golmok/pull/142) · `85a09c3`, 리뷰 R142 → R142-2)**: `test.sh`의 주석과 "No automation report" 오류, `add-gasp.sh`의 "wrote no result" 오류가 이제 `~/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log`를 가리킨다. 이전 로그가 같은 폴더의 `Golmok-backup-*.log`로 밀려난다는 안내도 붙였다. 문자열·주석만 바꿨고 로직은 그대로다. R142는 완료 기준 (a)의 테스트가 빠져 있고 본문에 사실이 아닌 문장이 2개 있어 병합을 보류했다. 고친 판은 기존 두 사례(`test_test_exit_rules`, `test_add_gasp_verify_only`)의 stderr에 assert를 두 줄씩 더했다. 새 경로가 있어야 하고 `Saved/Logs`는 없어야 한다. 옛 스크립트(임시 교체, 커밋 안 함)에서는 2 failed, 새 스크립트에서는 2 passed다. `grep -n -E 'Saved/Logs' tools/ue/test.sh tools/ue/add-gasp.sh`는 0줄, `bash -n` exit 0, 게이트 1936 passed, 3 skipped. 병합 커밋 `402ff5e`(브랜치 안)는 작성자 `-c`를 빠뜨려 `kreativ`로 남았다(되돌리지 않음, 규칙 7). mac-setup §8 #14 칸.

#### J-35 add-gasp 편집기 가드의 남은 분기 스텁 사례 (J-06 후속)
- **출처**: J-06 결과([#143](https://github.com/wooklym/golmok/pull/143)). `tools/ue/add-gasp.sh`의 편집기 가드는 `ps -axo pid=,comm=` 목록에서 실행 파일 이름(경로의 마지막 부분)이 `UnrealEditor*`인 프로세스만 고르고, 그 명령줄(`ps -o command= -p <pid>`)이 `*Golmok.uproject*` 또는 `*"$GaspProject"*`에 맞으면 막는다. 지금 `gasp_env`의 가짜 `ps`를 쓰는 양성 사례(`test_add_gasp_refuses_while_an_editor_runs`)는 `Golmok.uproject` 명령줄 하나뿐이다. `$GaspProject` 분기와, 걸리면 안 되는 두 경우(이름 필터·명령줄 필터)를 확인하는 사례가 없다.
- **할 일**: `tools/tests/test_ue_mac_scripts.py`에 `@posix_only` 사례를 더한다. 모두 `gasp_env`의 `FAKE_PS_LIST`·`FAKE_PS_CMDS`에 줄을 써서 만든다. ① **GASP 프로젝트 일치(막아야 함)**: `UnrealEditor` exe와 `e.gasp_project` 안의 `GASP_58.uproject`를 연 명령줄(`Golmok.uproject` 문자열은 넣지 않는다). 그러면 rc 1, `close the Unreal Editor first (running: <그 pid>`, `e.calls() == []`. ② **음성 — 상관없는 명령줄**: `UnrealEditor*` exe이지만 명령줄이 다른 프로젝트(예: `-Project=/Users/tester/Other/Other.uproject`)다. `e.respond("verify", ok=True, messages=[])` 뒤 `--verify`가 rc 0이고 stderr에 `close the Unreal Editor`가 없고 에디터 스텁이 불린다(`e.calls()`가 비지 않음). ③ **음성 — UnrealEditor가 아닌 실행 파일**: 이름이 `UnrealEditor`로 시작하지 않는 exe(예: `/usr/bin/vim`)이지만 명령줄에 `Golmok.uproject`가 있다. ②와 같은 단언. 기존 사례·픽스처의 동작은 바꾸지 않는다.
- **허용 파일**: `tools/tests/test_ue_mac_scripts.py`. `add-gasp.sh`는 아래 변형 실험에서만 임시로 고치고 커밋하지 않는다. 가드 자체에 결함이 보이면 고치지 말고 출력을 붙여 영록에게 알린다.
- **완료 기준**: (a) `pytest -q tests/test_ue_mac_scripts.py -k add_gasp` 출력 원문. 기존 8개와 새 사례 전부 passed다. (b) 변형 실험(로컬 1회씩, 커밋 안 함, 출력 원문 — 규칙 8): `add-gasp.sh`의 명령줄 `case`에서 `$GaspProject` 패턴을 지우면 ①이 실패한다. 이름 필터의 `continue`를 없애 모든 exe를 세게 하면 ③이 실패한다. 명령줄 `case`를 모든 명령줄에 맞게 바꾸면 ②가 실패한다. 실패한 테스트 이름과 메시지를 붙이고, `git checkout -- tools/ue/add-gasp.sh`로 되돌린 뒤 `git status --porcelain`에 테스트 파일만 남은 출력도 붙인다. (c) 파이썬 게이트, CI 모든 행 초록(Windows 행은 `@posix_only`로 건너뛴다 — J-06과 같은 방식으로 요약 줄을 확인해 적는다).
- **왜 재환 / 위험**: J-06과 같은 스텁 위에서 끝나는 좁은 테스트 일이고 변형 실험으로 판정된다. 위험: ①이 `$GaspProject` 분기가 아니라 `Golmok.uproject` 분기로 통과하는 것(명령줄에 그 문자열을 넣지 않고 (b)의 첫 변형으로 확인한다), 음성 사례가 가드와 상관없는 이유로 결과가 바뀌는 것(rc 0과 "에디터 스텁이 불린다" 단언, (b)로 막는다). J-07과 같은 파일이라 J-07은 코드 변경 없이 끝났으므로 바로 시작할 수 있다.

#### J-36 `test.sh` 종료 규칙: 경고 있는 성공만 있는 실행도 통과 — 설계 확정(Opus 2026-11-28)
- **출처**: [R149](https://github.com/wooklym/golmok/pull/149#issuecomment-7229593014)의 "좋은 발견"(J-17 실행에서 `test.sh`가 경고 있는 성공만 있는 실행을 `succeeded == 0`으로 실패 처리). `tools/ue/test.sh:65-68`(보고서를 읽는 Python 끝 4줄: `failed > 0 or succeeded == 0`이면 3, 셸이 `Automation tests failed`로 1). 엔진 `/Users/Shared/Epic Games/UE_5.8/Engine/Source/Developer/AutomationController/Private/AutomationControllerManager.cpp:162-172`(`UpdateTestResultStatus`: 상태가 Success로 바뀔 때 경고가 있으면 `SucceededWithWarnings++`, 없으면 `Succeeded++`; Fail은 `Failed++`, InProcess·NotRun은 각자 칸, `Skipped`는 세지 않음)과 같은 폴더 `AutomationControllerManager.h:138-150`·`:170`(`GetTotalTests()` = 다섯 칸의 합). 보고서 `index.json` 최상위 키는 `devices reportCreatedOn succeeded succeededWithWarnings failed notRun inProcess totalDuration comparisonExported comparisonExportDirectory tests`, 테스트 객체 키는 `testDisplayName fullTestPath tags state deviceInstance duration dateTime entries warnings errors artifacts`다(2026-11-27 메인 체크아웃 보고서와 J-12 보고서 사본에서 Opus가 읽음). 실제 예: J-17의 `--filter Golmok.Zone.IndexParse` 보고서 사본(재환 `$TMPDIR/jaehwan/J-17/item1b-index.json`)은 `succeeded` 0 · `succeededWithWarnings` 1 · `failed` 0 · `notRun` 0 · `inProcess` 0, 테스트 1개 `Success`(warnings 1 — 테스트가 일부러 내는 `GolmokZoneIndex: cell 16_55872_25381 lists z_synthetic_002@v2 but zones.json has v1 (skipped)` 경고)이고 `test.sh`는 종료 코드 1이었다. 스텁: `tools/tests/test_ue_mac_scripts.py:445-454` `_index()`(가짜 보고서에 `succeeded`·`failed`·`notRun`만 넣는다), `:457-478` `test_test_runs_headless_and_prints_report`(요약 줄을 글자 그대로 단언), `:497-508` `test_test_exit_rules`. 문서: [mac-setup §4](../runbooks/mac-setup.md) "기대 결과" 3(:174)의 괄호 "(`Succeeded:`는 Warning 있는 테스트를 따로 센다)". Windows: `tools/ue/test.ps1:26-27`에 같은 규칙이 있고, [AGENTS.md](../../AGENTS.md):164와 [pc-verify-wp18a.md](../runbooks/pc-verify-wp18a.md):146(B4)이 그 동작을 적어 둔다(Astra가 Windows에서 재현: [WP-18-followup](WP-18-followup.md):129).
- **설계 (확정, Opus 2026-11-28)**: 재환은 아래를 그대로 옮긴다. 바꿀 점이 보이면 고치지 말고 묻는다.
  1. **새 종료 규칙**: `failed == 0`이고 `succeeded + succeededWithWarnings > 0`이면 통과(Python 0 → 셸 0), 아니면 지금처럼 Python 3 → 셸 `Automation tests failed`로 1. 키가 없거나 `null`이면 지금처럼 0으로 읽는다(`or 0`). **바뀌는 경우는 하나뿐이다**: 옛 실패 조건 `f > 0 or s == 0`과 새 실패 조건 `f > 0 or s + w == 0`은 엔진이 줄이지 않는 음 아닌 칸이라 `s + w == 0` ⇔ `s == 0 and w == 0`이다. 그래서 둘이 다른 것은 `f == 0 and s == 0 and w > 0`(경고 있는 성공만 있는 실행) 하나이고, 새 규칙이 옛 규칙보다 더 실패시키는 경우는 없다. 아무것도 돌지 않은 실행(모두 0, 또는 `notRun`만 있는 실행)은 지금처럼 실패한다.
  2. **`notRun`·`inProcess`는 그대로 둔다.** 지금 스크립트는 `notRun`을 출력만 하고 종료 규칙에 쓰지 않으며, `inProcess`는 읽지 않는다. 이 과제는 이 두 칸의 처리를 바꾸지 않는다(결함을 보인 실행이 없다: Opus가 읽은 실제 보고서 4개 — 메인 체크아웃 2026-11-27, J-12 사본, J-17 `item1b`·`item2b` 사본 — 모두 `notRun` 0·`inProcess` 0). 성공과 함께 `notRun`이나 `inProcess`가 남은 실행을 실패로 볼지는 [미확인]이고 영록이 따로 판단한다(이 PR 범위 밖).
  3. **요약 줄**: 지금 줄 끝에 `  Succeeded with warnings: <값>`을 붙인다(`Succeeded: 0  Failed: 0  Not run: 0  Succeeded with warnings: 1`). 앞부분을 그대로 두므로 `test_test_exit_rules`의 부분 문자열 단언(`"Succeeded: 3  Failed: 1  Not run: 0" in failed.stdout`)은 바뀌지 않는다. 줄 전체를 단언하는 `test_test_runs_headless_and_prints_report`의 한 줄만 바뀐다. 키가 없는 옛 보고서면 값 자리는 지금의 `Not run:`처럼 빈 문자열이다(`text(None)`).
  4. **`test.sh` 바꿀 줄(Python 블록 안, bash 문법 변화 없음 — bash 3.2 그대로)**: 지금 `:65-68`의 4줄
     `succeeded = report.get("succeeded") or 0` / `failed = report.get("failed") or 0` / `print(f"Succeeded: {text(report.get('succeeded'))}  Failed: {text(report.get('failed'))}  Not run: {text(report.get('notRun'))}")` / `sys.exit(3 if failed > 0 or succeeded == 0 else 0)`
     를 아래 펜스 `j36-sh-diff`의 `+` 5줄 순서대로 바꾼다(첫 줄 유지, 그 뒤에 `with_warnings` 줄 1개 추가, `failed` 줄 유지, `print`·`sys.exit` 줄 교체). 다른 줄(주석 포함)은 건드리지 않는다.
  5. **스텁 테스트(`tools/tests/test_ue_mac_scripts.py`)**: ① `_index()` 서명에 `with_warnings: int = 0`을 더하고 가짜 보고서에 늘 `"succeededWithWarnings": with_warnings`를 넣는다(실제 보고서에는 이 키가 늘 있다). 기존 호출의 값은 0이라 기존 사례의 종료 코드는 바뀌지 않는다. ② `test_test_runs_headless_and_prints_report`의 기대 줄 하나 `"Succeeded: 5  Failed: 0  Not run: 1",`을 `"Succeeded: 5  Failed: 0  Not run: 1  Succeeded with warnings: 0",`으로 바꾼다. ③ `test_test_exit_rules` 바로 뒤(그 함수의 마지막 줄 `    assert "Saved/Logs" not in missing.stderr` 다음, 빈 줄 2개 뒤)에 새 사례 `test_test_exit_rules_with_warnings`(`@posix_only`)를 넣는다: 경고 있는 성공 1개만 → rc 0과 요약 줄 / `failed` 1 + 경고 있는 성공 1 → rc 1 / `notRun` 2만 → rc 1. `test_test_exit_rules`를 포함한 다른 사례·픽스처·스텁은 바꾸지 않는다. 정확한 줄은 펜스 `j36-py-diff`다(`+`·`-`를 뗀 것이 파일에 들어갈 줄; 새 함수 앞뒤의 빈 줄 2개는 펜스에 넣지 않았다 — 할 일 4의 확인 명령이 따로 센다).
  6. **비공허 증거**: 테스트를 **먼저** 바꾸고 옛 `test.sh`로 돌려 새 사례가 rc 단언(`assert 1 == 0`)에서 실패하는 것을 로그로 남긴 뒤(커밋 1, 테스트 파일만), `test.sh`를 고친다(커밋 2). 두 커밋은 함께 push한다(커밋 1만 push하면 CI가 빨갛다).
  7. **실제 헤드리스 확인도 이 과제에 넣는다**: 고치기 전과 뒤에 `$W`에서 `./tools/ue/test.sh --filter Golmok.Zone.IndexParse`를 한 번씩 돌린다(전: 종료 코드 1, 뒤: 0, 보고서 칸은 같은 값). 고친 뒤 전체 `./tools/ue/test.sh`도 한 번 돌려 전체 실행의 종료 코드가 0 그대로인지 본다. `$W`에는 J-12의 L_Dev·마네킹과 J-12b의 합성 zone이 이미 있다(J-17이 같은 worktree에서 이 필터를 돌렸다 — 보고서 사본 `item1b-index.json`의 `reportCreatedOn` `2026.11.27-22.25.51`). UE 실행 동안에는 GUI 잠금을 잡는다(아래 명령 공통 — J-17·R149와 같은 관례).
  8. **`test.ps1`(Windows)은 고치지 않는다.** 이유: ① D-022부터 Windows 스크립트는 이력이고([AGENTS.md](../../AGENTS.md):162 "아래 PowerShell 줄은 Windows용(이력)이다."), Windows 검증 기계가 없어 바꾼 `.ps1`을 돌려 볼 수 없다(규칙 1). ② `AGENTS.md`:164와 `pc-verify-wp18a.md`:146(B4)이 지금의 `test.ps1` 동작("모든 테스트에 경고가 있으면 `Succeeded: 0`을 찍고 예외")을 적고 있어 그대로 맞는 문장으로 남는다. ③ Windows 경로를 다시 쓰게 되면(D-022 ③) 그때 같은 규칙을 옮긴다(영록 이월 메모). 이 과제에서 `test.ps1`을 열거나 고치지 않는다.
  9. **런북 한 문장**: [mac-setup §4](../runbooks/mac-setup.md) "기대 결과" 3(:174)의 괄호 한 개만 바꾼다(아래 할 일 6, 바꿀 문장 원문과 새 문장). §9 결과 행·§8 표·다른 런북은 그날의 실행 기록이므로 고치지 않는다. 종료 규칙 자체를 적은 문장은 mac-setup에 없다(`grep -n -E 'Automation tests failed|succeeded == 0' docs/runbooks/mac-setup.md` 0줄, Opus 2026-11-28).
  10. **핫스팟 아님**: `tools/ue/test.sh`와 `tools/tests/test_ue_mac_scripts.py`는 [CLAUDE.md](../../CLAUDE.md) 핫스팟 목록(§7.6: `Player/GolmokCharacter`·`GolmokPlayerController`·`GolmokGameMode`·`Golmok.Build.cs`·`Config/Default*.ini`·`tools/pyproject.toml`·CI·`check_repo.py`·`test_ue_wp09_fixture.py`의 `CONSOLE_COMMANDS`/`BUILD_CS_*`·`test_ue_zone_fixture.py`의 `CONVENTION_FOLDERS`)에 없다. 훅 표시를 넣지 않는다.

```text j36-sh-diff
+with_warnings = report.get("succeededWithWarnings") or 0  # J-36: "succeeded" counts only successes without a warning
-print(f"Succeeded: {text(report.get('succeeded'))}  Failed: {text(report.get('failed'))}  Not run: {text(report.get('notRun'))}")
-sys.exit(3 if failed > 0 or succeeded == 0 else 0)
+print(f"Succeeded: {text(report.get('succeeded'))}  Failed: {text(report.get('failed'))}  Not run: {text(report.get('notRun'))}  Succeeded with warnings: {text(report.get('succeededWithWarnings'))}")
+sys.exit(3 if failed > 0 or succeeded + with_warnings == 0 else 0)
```

```text j36-py-diff
-def _index(succeeded: int, failed: int, not_run: int = 0) -> str:
+def _index(succeeded: int, failed: int, not_run: int = 0, with_warnings: int = 0) -> str:
-        "succeeded": succeeded, "failed": failed, "notRun": not_run,
+        "succeeded": succeeded, "succeededWithWarnings": with_warnings, "failed": failed, "notRun": not_run,
-        "Succeeded: 5  Failed: 0  Not run: 1",
+        "Succeeded: 5  Failed: 0  Not run: 1  Succeeded with warnings: 0",
+@posix_only
+def test_test_exit_rules_with_warnings(env):
+    # J-36: the report's "succeeded" counts successes without a warning, "succeededWithWarnings" the
+    # others (UE AutomationControllerManager.cpp); a run whose only test warns still passes
+    only_warned = env.run("test.sh", FAKE_INDEX=_index(0, 0, with_warnings=1))
+    assert only_warned.returncode == 0, only_warned.stderr
+    assert "Succeeded: 0  Failed: 0  Not run: 0  Succeeded with warnings: 1" in only_warned.stdout
+    failed = env.run("test.sh", FAKE_INDEX=_index(0, 1, with_warnings=1))
+    assert failed.returncode == 1 and "Automation tests failed" in failed.stderr
+    assert "Succeeded: 0  Failed: 1  Not run: 0  Succeeded with warnings: 1" in failed.stdout
+    nothing = env.run("test.sh", FAKE_INDEX=_index(0, 0, not_run=2))
+    assert nothing.returncode == 1 and "Automation tests failed" in nothing.stderr
```

```text j36-counts
tests 1
states Success
succeeded 0
succeededWithWarnings 1
failed 0
notRun 0
inProcess 0
sum 1
```

- **명령 공통**: 셸 변수는 Bash 호출 사이에 남지 않는다. 그래서 **모든 명령은 `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/jaehwan/J-36";`로 시작하고**, 그 뒤는 `cd "$W" &&`·`cd "$W/tools" &&`·`git -C "$W"`·`"$E/…"` 절대 경로로 시작한다(상시 규칙). 아래 명령에는 이 앞머리를 적지 않았다. 돌린 명령 원문은 `"$E/commands.txt"`에 한 줄씩 더한다(규칙 10). 각 단계의 "기대"와 다르면 **멈춤 조건**을 본다.
  - **카운트 명령** `C <사본> <로그>`: `python3 "$E/counts.py" "$E/<사본>" > "$E/<로그>" 2>&1`. `$E/counts.py`는 할 일 1에서 `sed -n '/^```python j36-counts-py$/,/^```$/p' "$E/task.txt" | sed '1d;$d' > "$E/counts.py"`로 만든다(아래 펜스, 손으로 옮기지 않는다).
  - **GUI 잠금**(UE를 띄우는 할 일 3·7 앞뒤, [mac-setup §3](../runbooks/mac-setup.md) 표의 규칙): 확인 `L="$TMPDIR/claude/gui-foreground.lock"; if [ -e "$L" ]; then cat "$L"; else echo "no lock"; fi > "$E/lock-check-<n>.log"; date -u +%FT%TZ >> "$E/lock-check-<n>.log"` — 기대 첫 줄 `no lock`. 다른 줄이 있으면 **지우지 않고** 그 줄을 영록에게 보내고 기다린다. 잡기 `mkdir -p "$TMPDIR/claude" && (set -C; printf '%s %s %s\n' "재환" "J-36-headless" "$(date -u +%FT%TZ)" > "$TMPDIR/claude/gui-foreground.lock"); echo $? > "$E/lock-take-<n>.rc"` — 기대 `0`(0이 아니면 누가 먼저 잡은 것: 멈춘다). 풀기 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-36-headless ' "$L" && rm "$L"; echo $? > "$E/lock-release-<n>.rc"` — 기대 `0`. `<n>`은 할 일 3이면 `a`, 할 일 7이면 `b`.

```python j36-counts-py
import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8-sig"))
t = d["tests"]
print("tests", len(t))
print("states", " ".join(sorted(set(x["state"] for x in t))))
for k in ("succeeded", "succeededWithWarnings", "failed", "notRun", "inProcess"):
    print(k, d.get(k))
print("sum", (d.get("succeeded") or 0) + (d.get("succeededWithWarnings") or 0))
```

- **할 일**:
  1. **준비**: `mkdir -p "$E" && git -C "$W" fetch origin && git -C "$W" switch -c local/jaehwan-j36-test-warnings origin/main && cd "$W" && sed -n '/^#### J-36/,/^## 재환에게 맞지 않는 것/p' docs/plan/jaehwan-tasks.md > "$E/task.txt"`(규칙 14). 기대: `head -1 "$E/task.txt"`가 `#### J-36 `로 시작한다. 펜스 추출(세 번, 이름만 다르다): `sed -n '/^```text j36-sh-diff$/,/^```$/p' "$E/task.txt" | sed '1d;$d' > "$E/expected-j36-sh-diff.txt"`, 같은 꼴로 `j36-py-diff` → `"$E/expected-j36-py-diff.txt"`, `j36-counts` → `"$E/expected-j36-counts.txt"`. 그다음 `wc -l "$E"/expected-j36-*.txt > "$E/expected-wc.log"` — 기대: `j36-counts` 8줄, `j36-py-diff` 18줄, `j36-sh-diff` 5줄. 이어서 위 명령 공통의 `counts.py` 추출, 기대: `wc -l < "$E/counts.py" | tr -d ' '`가 `10`. 겹침 확인: `cd "$W" && gh pr list --state open --json number,headRefName,files --jq '.[]|select(any(.files[]; .path=="tools/tests/test_ue_mac_scripts.py" or .path=="tools/ue/test.sh"))|"\(.number) \(.headRefName)"' > "$E/overlap.log" 2>&1` — 기대: 빈 파일(J-35 PR이 열려 있으면 멈춘다).
  2. **스텁 기준선**: `cd "$W/tools" && source .venv/bin/activate && pytest -q tests/test_ue_mac_scripts.py > "$E/pytest-base.log" 2>&1; echo $? > "$E/pytest-base.rc"`. 기대: rc `0`, `tail -1 "$E/pytest-base.log"`가 `N passed in …`(아래 N은 이 수; `origin/main` `cff4e92`의 Opus dry-run에서는 44).
  3. **UE 기준선(고치기 전)**: GUI 잠금 확인·잡기(`a`). `cd "$W" && /usr/bin/timeout 1800 ./tools/ue/build.sh > "$E/build.log" 2>&1; echo $? > "$E/build.rc"` — 기대 `0`. `cd "$W" && /usr/bin/timeout 900 ./tools/ue/test.sh --filter Golmok.Zone.IndexParse > "$E/ue-old.log" 2>&1; echo $? > "$E/ue-old.rc"; cp unreal/Golmok/Saved/Automation/Report/index.json "$E/old-index.json"; echo $? > "$E/old-cp.rc"` — 기대: `ue-old.rc` `1`, `old-cp.rc` `0`, `grep -c -F 'Succeeded: 0  Failed: 0  Not run: 0' "$E/ue-old.log"` `1`, `grep -c -F 'Automation tests failed' "$E/ue-old.log"` `1`. 카운트 `C old-index.json old-counts.log` → `diff "$E/expected-j36-counts.txt" "$E/old-counts.log" > "$E/old-counts.diff"; echo "exit=$?" >> "$E/old-counts.diff"` — 기대: `exit=0` 한 줄. 잠금 풀기(`a`).
  4. **테스트 먼저(커밋 1)**: 설계 5의 세 군데를 편집기(Edit 도구)로 바꾼다 — `-` 줄을 찾아 `+` 줄로, 새 함수는 설계 5 ③의 자리에. 확인: `cd "$W" && git diff -U0 -- tools/tests/test_ue_mac_scripts.py | grep -E '^[-+]' | grep -v -E '^(\+\+\+|---) ' > "$E/py-diff-all.txt"; grep -c -x '+' "$E/py-diff-all.txt" > "$E/py-diff-blank.log"; grep -v -x '+' "$E/py-diff-all.txt" | diff "$E/expected-j36-py-diff.txt" - > "$E/py-diff.log"; echo "exit=$?" >> "$E/py-diff.log"` — 기대: `py-diff-blank.log` `2`, `py-diff.log` `exit=0` 한 줄. 옛 `test.sh`로 새 사례만: `cd "$W/tools" && source .venv/bin/activate && pytest -q tests/test_ue_mac_scripts.py -k test_test_exit_rules_with_warnings > "$E/pytest-old-one.log" 2>&1; echo $? > "$E/pytest-old-one.rc"` — 기대: rc `1`, `grep -c '^FAILED tests/test_ue_mac_scripts.py::test_test_exit_rules_with_warnings' "$E/pytest-old-one.log"` `1`, `grep -c -F 'assert 1 == 0' "$E/pytest-old-one.log"` `1`, 끝 줄 `1 failed, N deselected in …`. 옛 `test.sh`로 파일 전체: `cd "$W/tools" && source .venv/bin/activate && pytest -q tests/test_ue_mac_scripts.py > "$E/pytest-old-all.log" 2>&1; echo $? > "$E/pytest-old-all.rc"` — 기대: rc `1`, `grep -E '^FAILED' "$E/pytest-old-all.log" | sed -E 's/ - .*//'` 출력이 `FAILED tests/test_ue_mac_scripts.py::test_test_runs_headless_and_prints_report`, `FAILED tests/test_ue_mac_scripts.py::test_test_exit_rules_with_warnings` 두 줄, 끝 줄 `2 failed, N-1 passed in …`. 커밋 1: `cd "$W" && git add tools/tests/test_ue_mac_scripts.py && git diff --cached --name-only > "$E/c1-files.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-36: test.sh 경고 있는 성공 스텁 사례(옛 스크립트에서 실패)" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c1-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-c1.log"` — 기대: `c1-files.log` 한 줄 `tools/tests/test_ue_mac_scripts.py`, `author-c1.log` `재환 <jaehwan.local@localhost>`. push는 아직 하지 않는다.
  5. **`test.sh` 수정**: 설계 4대로 편집기로 바꾼다. 확인: `cd "$W" && git diff -U0 -- tools/ue/test.sh | grep -E '^[-+]' | grep -v -E '^(\+\+\+|---) ' | diff "$E/expected-j36-sh-diff.txt" - > "$E/sh-diff.log"; echo "exit=$?" >> "$E/sh-diff.log"` — 기대 `exit=0` 한 줄. `/bin/bash -n "$W/tools/ue/test.sh" > "$E/bash-n.log" 2>&1; echo "exit=$?" >> "$E/bash-n.log"` — 기대 `exit=0` 한 줄. `cd "$W/tools" && source .venv/bin/activate && pytest -q tests/test_ue_mac_scripts.py > "$E/pytest-new-all.log" 2>&1; echo $? > "$E/pytest-new-all.rc"` — 기대: rc `0`, 끝 줄 `N+1 passed in …`. `git -C "$W" diff --quiet origin/main -- tools/ue/test.ps1; echo $? > "$E/ps1-unchanged.rc"` — 기대 `0`.
  6. **mac-setup 한 문장**: `docs/runbooks/mac-setup.md` §4 "기대 결과" 3(지금 :174)에서 정확히 이 문장 `` 판정은 상태 열로 한다(`Succeeded:`는 Warning 있는 테스트를 따로 센다). ``를 `` 판정은 상태 열로 한다(`Succeeded:`는 Warning 없는 성공만 센다. Warning 있는 성공 수는 같은 줄 끝 `Succeeded with warnings:`에 나온다. `test.sh` 종료 코드는 보고서 `failed`가 0이고 `succeeded`와 `succeededWithWarnings`의 합이 1 이상이면 0이다 — J-36. 그 전의 `test.sh`는 `succeeded`만 봐서 경고 있는 성공만 있는 필터 실행(예: `--filter Golmok.Zone.IndexParse`)이 종료 코드 1이었다). ``로 바꾼다. 같은 줄의 다른 글자와 다른 줄은 바꾸지 않는다. 확인: `` cd "$W" && grep -c -F '판정은 상태 열로 한다(`Succeeded:`는 Warning 없는 성공만 센다.' docs/runbooks/mac-setup.md `` `1`, `` cd "$W" && grep -c -F '`Succeeded:`는 Warning 있는 테스트를 따로 센다' docs/runbooks/mac-setup.md `` `0`, `cd "$W" && git diff --numstat -- docs/runbooks/mac-setup.md` `1	1	docs/runbooks/mac-setup.md`.
  7. **UE 확인(고친 뒤)**: GUI 잠금 확인·잡기(`b`). `cd "$W" && /usr/bin/timeout 900 ./tools/ue/test.sh --filter Golmok.Zone.IndexParse > "$E/ue-new.log" 2>&1; echo $? > "$E/ue-new.rc"; cp unreal/Golmok/Saved/Automation/Report/index.json "$E/new-index.json"; echo $? > "$E/new-cp.rc"` — 기대: `ue-new.rc` `0`, `new-cp.rc` `0`, `grep -c -F 'Succeeded: 0  Failed: 0  Not run: 0  Succeeded with warnings: 1' "$E/ue-new.log"` `1`, `grep -c -F 'Automation tests failed' "$E/ue-new.log"` `0`. 카운트 `C new-index.json new-counts.log`, `diff "$E/expected-j36-counts.txt" "$E/new-counts.log"`를 `new-counts.diff`로(할 일 3과 같은 꼴) — 기대 `exit=0` 한 줄. 이어서 전체: `cd "$W" && /usr/bin/timeout 2700 ./tools/ue/test.sh > "$E/ue-full.log" 2>&1; echo $? > "$E/ue-full.rc"; cp unreal/Golmok/Saved/Automation/Report/index.json "$E/full-index.json"; echo $? > "$E/full-cp.rc"` — 기대: `ue-full.rc` `0`. 카운트 `C full-index.json full-counts.log` — 기대: `failed 0`, `notRun 0`, `inProcess 0` 줄이 있고 `sum` 값이 `tests` 값과 같다(`awk '$1=="tests"{t=$2} $1=="sum"{s=$2} END{print (t==s)?"same":"DIFFERENT"}' "$E/full-counts.log" > "$E/full-sum.log"` → `same`). `tail -1 "$E/ue-full.log"`는 `Succeeded: <succeeded>  Failed: 0  Not run: 0  Succeeded with warnings: <succeededWithWarnings>`이고 두 값이 `full-counts.log`와 같다. 잠금 풀기(`b`). `git -C "$W" status --porcelain > "$E/status-after-ue.log"` — 기대: `docs/runbooks/mac-setup.md`와 `tools/ue/test.sh` 두 줄(` M` 표시)뿐.
  8. **게이트·커밋 2·push**: 파이썬 게이트(규칙 13): `cd "$W/tools" && source .venv/bin/activate && { ruff check . && ruff format --check . && pytest -q && python scripts/check_repo.py; } > "$E/gate.log" 2>&1; echo $? > "$E/gate.rc"`(중괄호가 있어야 네 명령의 출력이 모두 로그로 간다) — 기대 rc `0`. 커밋 2: `cd "$W" && git add tools/ue/test.sh docs/runbooks/mac-setup.md && git diff --cached --name-only > "$E/c2-files.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-36: test.sh 종료 규칙 — 경고 있는 성공도 성공으로 센다, 요약 줄에 수" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c2-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-c2.log"` — 기대: `c2-files.log` 두 줄 `docs/runbooks/mac-setup.md`·`tools/ue/test.sh`, `author-c2.log` `재환 <jaehwan.local@localhost>`. 게이트를 커밋 뒤 한 번 더 돌리지 않아도 된다(커밋은 파일을 바꾸지 않는다; 게이트 로그가 마지막 편집보다 새것인지 `ls -lT "$E/gate.log" "$W/tools/ue/test.sh" "$W/docs/runbooks/mac-setup.md" "$W/tools/tests/test_ue_mac_scripts.py" > "$E/mtime.log"`로 남긴다). `git -C "$W" push -u origin local/jaehwan-j36-test-warnings > "$E/push.log" 2>&1; echo "exit=$?" >> "$E/push.log"` — 두 커밋을 한 번에. PR을 연다(제목 `J-36: test.sh 종료 규칙 — 경고 있는 성공만 있는 실행도 통과`, CI 칸은 "CI 진행 중 — 결과는 아래에 추가"만, 규칙 2a). `/usr/bin/timeout 1800 gh pr checks <n> --watch --interval 30 > "$E/checks-watch.log" 2>&1; echo "exit=$?" >> "$E/checks-watch.log"; gh pr checks <n> > "$E/checks.log" 2>&1` — 기대: 모든 행 pass.
  9. **PR 본문**: 절 순서 = 요약 · 바뀐 파일 · **`## 결과`**(관찰한 값만: 종료 코드, 요약 줄, 보고서 칸, pytest 끝 줄 — 과제 번호·규칙 번호·날짜는 이 절에 쓰지 않는다) · 완료 기준 대조(규칙 14: `$E/task.txt`의 "완료 기준" 부분을 물결 펜스 `~~~` 코드 블록에 그대로 붙이고(과제 글에 백틱 펜스가 들어 있다), 아래에 (a)~(i) 한 줄씩 충족 + 증거 파일 또는 **미충족** + 이유) · 실행한 명령(`$E/commands.txt` 그대로) · 남은 `[미확인]` · 병합 시 반영 · 제출 전 점검표(규칙 1~15 한 줄씩, 과거형과 결과) · 서명. 본문 초안은 `$E/pr-body.md`. 게시 전 검사(규칙 10 e·f) — **대상 로그는 이 목록으로 고정한다**(본문 초안·게시본·`task.txt`·`commands.txt`·검사 로그 자신은 넣지 않는다): `"$E"/pytest-base.log "$E"/pytest-old-one.log "$E"/pytest-old-all.log "$E"/pytest-new-all.log "$E"/build.log "$E"/ue-old.log "$E"/ue-new.log "$E"/ue-full.log "$E"/old-counts.log "$E"/new-counts.log "$E"/full-counts.log "$E"/gate.log "$E"/checks.log`.
     - 인용 검사: `## 결과` 절의 백틱 문자열마다 그 문자열이 근거로 든 로그 **한 개**를 `"$E/quotes.tsv"`에 `<문자열><탭><위 목록의 파일 이름>`으로 적는다(로그 인용이 아닌 파일 이름·명령은 파일 칸에 `라벨`). 빠진 것 확인(명령 안에 백틱이 있어 이중 백틱으로 감쌌다 — 안쪽 글자를 그대로 쓴다): `` awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '`[^`]+`' | sed 's/^`//;s/`$//' | sort -u > "$E/body-quotes.txt"; cut -f1 "$E/quotes.tsv" | sort -u > "$E/tsv-quotes.txt"; comm -23 "$E/body-quotes.txt" "$E/tsv-quotes.txt" > "$E/quotes-missing.log" `` — 기대 빈 파일. 세기: `while IFS="$(printf '\t')" read -r q f; do if [ "$f" = "라벨" ]; then n="라벨"; else n=$(grep -F -c -- "$q" "$E/$f"); fi; printf '%s\t%s\t%s\n' "$n" "$f" "$q"; done < "$E/quotes.tsv" > "$E/quotes-check.log"` — 기대: `cut -f1 "$E/quotes-check.log" | grep -c -x '0'`가 `0`.
     - 숫자 검사: `awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '[0-9]{2,}' | sort -u > "$E/body-numbers.txt"; while read -r x; do printf '%s\t%s\n' "$(cat "$E"/pytest-base.log "$E"/pytest-old-one.log "$E"/pytest-old-all.log "$E"/pytest-new-all.log "$E"/build.log "$E"/ue-old.log "$E"/ue-new.log "$E"/ue-full.log "$E"/old-counts.log "$E"/new-counts.log "$E"/full-counts.log "$E"/gate.log "$E"/checks.log | grep -c -- "$x")" "$x"; done < "$E/body-numbers.txt" > "$E/numbers-check.log"` — 기대: `cut -f1 "$E/numbers-check.log" | grep -c -x '0'`가 `0`. 한 자리 숫자는 이 검사에 걸리지 않으므로 문맥 문자열(예: `succeededWithWarnings 1`)로 인용 검사에 넣는다.
     - 0이 나온 것은 고치거나 지운다. 그 뒤 게시하고 `gh pr view <n> --json body --jq .body`로 다시 읽는다(규칙 12).
- **허용 파일**: `tools/ue/test.sh`(설계 4의 Python 줄만), `tools/tests/test_ue_mac_scripts.py`(설계 5의 세 군데만), `docs/runbooks/mac-setup.md`(할 일 6의 한 문장만). `tools/ue/test.ps1`·다른 `.sh`·`common.sh`·`check_repo.py`·`pyproject.toml`·CI·공유 문서(AGENTS.md 포함)는 건드리지 않는다.
- **멈춤 조건(정하지 말고 영록에게 묻는다)**: `overlap.log`가 비어 있지 않을 때. `expected-wc.log`·`counts.py` 줄 수가 기대와 다를 때. 잠금 파일에 다른 기록이 있거나 잠금 잡기 rc가 0이 아닐 때. `build.rc`가 0이 아닐 때. `ue-old.rc`가 1이 아니거나 `old-counts.diff`가 `exit=0`이 아닐 때(예: `succeededWithWarnings`가 1이 아님 — 경고 없이 통과했거나 실패한 것). `py-diff.log`·`sh-diff.log`가 `exit=0` 한 줄이 아니거나 `py-diff-blank.log`가 2가 아닐 때. 옛 스크립트에서 새 사례가 실패하지 않거나, 실패한 사례가 위 두 개가 아닐 때. 고친 뒤 pytest가 `N+1 passed`가 아닐 때. `ue-new.rc`가 0이 아니거나 `ue-full.rc`가 0이 아니거나 `full-sum.log`가 `same`이 아닐 때(전체 실행의 `failed`·`notRun`·`inProcess`가 0이 아닌 경우 포함 — 원인을 고치지 않는다). 허용 파일 밖이 바뀌었을 때(`status-after-ue.log`에 다른 줄). 명령이 `timeout`(rc 124)으로 끝났을 때(규칙 5).
- **완료 기준**:
  - (a) 비공허(옛 스크립트): `$E/pytest-old-one.rc` `1`, `^FAILED tests/test_ue_mac_scripts.py::test_test_exit_rules_with_warnings` 1줄, `assert 1 == 0` 1줄, 끝 줄 원문. `$E/pytest-old-all.log`의 FAILED 두 줄(할 일 4의 두 이름)과 끝 줄 원문. 커밋 1(`git -C "$W" show --stat --format= <커밋 1>`)은 `tools/tests/test_ue_mac_scripts.py` 한 파일이다.
  - (b) 고친 뒤: `$E/pytest-base.log`·`$E/pytest-new-all.log` 끝 줄 원문 두 개, 앞이 `N passed`이면 뒤가 `N+1 passed`. `$E/pytest-new-all.rc` `0`.
  - (c) 정확한 변경: `$E/sh-diff.log`·`$E/py-diff.log` 모두 `exit=0` 한 줄, `$E/py-diff-blank.log` `2`. `git -C "$W" diff --name-only origin/main...HEAD` 출력은 `docs/runbooks/mac-setup.md`, `tools/tests/test_ue_mac_scripts.py`, `tools/ue/test.sh` 세 줄. `$E/ps1-unchanged.rc` `0`. `$E/bash-n.log` `exit=0`.
  - (d) 실제 헤드리스, 고치기 전: `$E/build.rc` `0`, `$E/ue-old.rc` `1`, `ue-old.log`의 `Succeeded: 0  Failed: 0  Not run: 0`·`Automation tests failed` 각 1줄, `$E/old-counts.diff` `exit=0`(= 펜스 `j36-counts`).
  - (e) 실제 헤드리스, 고친 뒤: `$E/ue-new.rc` `0`, `ue-new.log`의 `Succeeded: 0  Failed: 0  Not run: 0  Succeeded with warnings: 1` 1줄·`Automation tests failed` 0줄, `$E/new-counts.diff` `exit=0`. 전체 실행 `$E/ue-full.rc` `0`, `$E/full-counts.log` 원문, `$E/full-sum.log` `same`, `ue-full.log` 끝 줄 원문. 보고서 사본 `old-index.json`·`new-index.json`·`full-index.json`이 `$E`에 있다.
  - (f) 런북: 할 일 6의 `grep -c` 두 개(`1`·`0`)와 numstat `1	1	docs/runbooks/mac-setup.md`.
  - (g) 게이트 `$E/gate.rc` `0`, `$E/mtime.log`에서 `gate.log`가 세 파일보다 새것. CI `gh pr checks <n>` 모든 행 pass 원문(규칙 2).
  - (h) `git -C "$W" status --porcelain` 빈 출력(push 뒤). 잠금: `$E/lock-release-a.rc`·`$E/lock-release-b.rc` 모두 `0`. 작성자: `author-c1.log`·`author-c2.log` 모두 `재환 <jaehwan.local@localhost>`.
  - (i) PR 본문: "완료 기준 대조" 절과 점검표 1~15가 있다. `$E/quotes-missing.log` 빈 파일, `quotes-check.log`·`numbers-check.log`에 0 없음. 게시 뒤 다시 읽은 출력(규칙 12).
- **병합 시 반영(영록)**: STATUS 재환 절에 J-36 행. [AGENTS.md](../../AGENTS.md):164 끝에 "Mac `test.sh`는 J-36부터 경고 있는 성공도 성공으로 센다(`failed` 0이고 `succeeded`+`succeededWithWarnings` ≥ 1이면 종료 코드 0)" 한 문장을 더할지 영록이 판단한다(Astra 문서라 재환은 고치지 않는다). `test.ps1`·pc-verify-wp18a B4는 Windows 이력이라 그대로 둔다(설계 8). 이월 후보: 성공과 함께 `notRun`·`inProcess`가 남은 실행의 처리(설계 2).
- **왜 재환 / 위험**: 바꿀 줄이 정확히 정해져 있고 전후가 스텁·실제 헤드리스 양쪽에서 명령으로 판정된다. 위험: ① 종료 코드 0을 "실행됐다"로 읽는 것 — `test.sh`의 0은 "`failed` 0이고 무엇이든 성공으로 끝났다"일 뿐이다. 경고 있는 성공에는 skip Info(`MPC_GolmokWeather missing - skipped` 등)나 `NOT EXECUTED` 경고로 끝난 테스트도 들어간다. 판정은 지금처럼 상태 열과 보고서 entries로 한다(mac-setup §4 "기대 결과" 3, 규칙 15). ② 새 사례가 옛 스크립트에서도 통과하는 빈 테스트 — 할 일 4의 실패 로그로 막는다. ③ `_index()` 기본값 변경으로 기존 사례의 의미가 바뀌는 것 — 새 키의 기본값 0은 옛·새 규칙 모두에서 종료 코드를 바꾸지 않고, (a)의 옛 스크립트 실패가 두 사례뿐인 것으로 확인한다. ④ J-35와 같은 테스트 파일이다 — 둘을 동시에 열지 않는다. **J-36이 먼저**다(백로그 순서 J-20 → J-36 → J-18 → J-35; J-35는 J-36 병합 뒤 `origin/main`에서 시작한다).
- **dry-run 범위(Opus 2026-11-28)**: `origin/main` `cff4e92`의 `tools/` scratch 사본에서 설계 4·5를 그대로 적용해 확인한 것: 기준선 44 passed, 테스트만 바꾼 상태(옛 `test.sh`)에서 `-k test_test_exit_rules_with_warnings` → `1 failed, 44 deselected`(`assert 1 == 0` 1줄, FAILED 1줄), 파일 전체 → `2 failed, 43 passed`(할 일 4의 두 이름), `test.sh`까지 바꾼 뒤 → `45 passed`, `ruff check`·`ruff format --check`(테스트 파일) 통과, `bash -n` 통과, `git diff -U0`의 `+`/`-` 줄이 두 펜스와 같고 테스트 파일의 빈 `+` 줄은 2. 새·옛 Python 블록을 실제 보고서 사본에 직접 돌린 결과: J-17 `item1b-index.json`(0/1) 옛 3 → 새 0, J-12 사본(22/17) 둘 다 0, `notRun` 3만 있는 가짜 보고서 둘 다 3. 카운트 스크립트는 `item1b-index.json`에서 펜스 `j36-counts`와 같은 8줄을 냈다. dry-run하지 못한 것: 실제 UE 실행(할 일 3·7), 재환 worktree에서의 pytest 수(N), `gh` 명령, 인용·숫자 검사 파이프(본문이 없어서).

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
