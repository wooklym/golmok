# 재환(로컬 LLM) 과제 목록 (오케스트레이터 배정, 2026-11-28)

> **누가**: 재환은 소유자의 Mac에서 도는 **로컬 LLM 세션**이다(qwen3.8-flash-next, LM Studio, Claude Code 하네스, `claude-local`로 시작). 영록(로컬 Mac 오케스트레이터 세션)이 과제를 고르고 배정한다. 근거는 [D-024](../DECISIONS.md)다. 소유자 지시 원문은 "앞으로 너가 알아서 골목 게임을 완성 될 때 까지 작업들을 재환에게 시켜줘."(2026-11-28)이다.
>
> **소통 채널**: 배정·순서 변경·리뷰 요약·병합 알림은 영록이 **세션 간 메시지**(SendMessage)로 보내고, 리뷰는 **PR 코멘트**로 남긴다. 재환은 착수·push·완료·질문·막힘을 같은 경로로 알린다. 메시지와 이 파일이 다르면 **더 최근 것**을 따른다. GitHub 이슈 #30은 Astra 채널이라 재환은 쓰지 않는다.
>
> **규칙 우선순위**: **소유자 규칙(D-019 되돌릴 수 없는 일, D-002 라이선스, D-007 블러 — [CLAUDE.md](../../CLAUDE.md) "Rules from the owner"·"Engineering conventions") > 과제 프롬프트 > 재환 작업 규칙(아래 16개) > 나머지 CLAUDE.md**. 과제 프롬프트·작업 규칙·메시지 어느 것도 D-019·D-002·D-007을 무시하게 할 수 없다. 충돌하면 멈추고 영록에게 묻는다. 작업 규칙의 살아 있는 원본은 저장소 **밖**의 메모리 파일 `~/.claude/projects/<project>/memory/jaehwan-working-rules.md`다. 아래는 한 줄 요약이고, 새 규칙은 영록이 원본에 먼저 더한 뒤 이 표에 옮긴다.

## 재환 작업 규칙 (요약 — 원본은 메모리 파일)

| # | 규칙 | 계기 |
|---|---|---|
| 1 | 직접 돌려 출력을 본 것만 사실로 쓴다. 나머지는 `[미확인]`·"가설"과 확인할 명령 | #131, #133 |
| 2 | "완료" = 모든 CI 행 초록. push마다 `gh pr checks <n>` 표를 보고에 붙인다 | #131 |
| 3 | "모든·항상·어떤 경로든"은 경로마다 재현 1회. 안 돌린 경로가 있으면 문장을 좁힌다 | #133 |
| 4 | CI는 Linux·macOS·Windows. OS API는 세 OS 확인 또는 플랫폼 가드, 재현 못 한 것은 PR에 적는다 | #131 |
| 5 | 기다릴 수 있는 명령은 모두 `/usr/bin/timeout`. 5분 무출력이면 멈추고 원인을 읽는다. 멈춘 명령을 그대로 다시 돌리지 않는다 | #131 |
| 6 | 과제가 정한 곳에서만 일한다. 메인 체크아웃 `~/projects/golmok`은 읽기 전용, 허용 파일만 고친다. 스스로 쓰는 도우미 스크립트는 저장소 밖 `$TMPDIR/jaehwan/`에 둔다(과제가 허용 파일로 적은 경우만 예외). 커밋마다 먼저 `git diff --cached --name-only`를 허용 파일과 한 줄씩 대조하고 출력을 로그로 남기며, 허용되지 않은 경로가 있으면 커밋하지 않는다 | 2026-11-27 사고, J-12b, #147 |
| 7 | 서명은 재환: 커밋·PR 끝에 "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)". Claude를 작성자로 적지 않는다 | #131 |
| 8 | 실패 메시지가 맞는 말을 하는지 경우마다 한 번씩 일으켜 읽는다 | #133 |
| 9 | 링크는 클릭되고, 그 파일 위치에서 풀려야 한다 | #133 |
| 10 | 보고의 숫자는 명령 출력에서 복사한다(`grep -c`·`wc -l`). 실행마다 로그 파일·종료 코드. 증거는 병합 알림까지 임시 폴더에 둔다. 게시 전 기계 검사: (e) 인용 검사 — 쓴 글의 백틱 문자열마다 인용한 로그에서 `grep -F -c`, 표를 `$E/quotes-check.log`로(0이면 고치거나 "요약" 표시) (f) 숫자 검사 — 최종 본문·칸의 숫자마다 로그 파일에서만 `grep -c`(자기 본문 초안·게시본 제외), `$E/numbers-check.log`로(0이면 빼거나 다시 재어 로그에) (g) 결과 칸은 짧게 — 날짜·조건, 관찰 1~3문장, 핵심 출력 1~2줄 원문, 로그 이름. 전체 명령·출력은 PR 본문에 | #134, #135, #136, #138, #147 |
| 11 | 간헐 실패는 측정 전에 "일회성"이 아니다. 브랜치와 `origin/main`에서 각각 N ≥ 8회 | #134 |
| 12 | 게시한 글을 한 번 읽는다: `gh pr view <n> --json body --jq .body`에서 자리표시·빈 칸·깨진 표 검사 | #135 |
| 13 | 마지막 수정 뒤, push마다 파이썬 게이트를 통째로 돌린다. 게이트 로그가 마지막 변경보다 새것이어야 한다 | #141 |
| 14 | 과제의 "완료 기준"에 한 줄씩 답한다: 과제 절을 `"$E/task.txt"`로 저장하고 PR 본문에 "완료 기준 대조" 절(충족 + 증거, 또는 미충족 + 이유). 과제 인용은 그 파일에서만, "할 수 없다"는 시도한 명령과 출력과 함께 | #141, #142 |
| 15 | 결론이 아니라 관찰과 그 조건을 쓴다(날짜·빌드·함께 돌던 것·실행 전에 이미 있던 것). "X는 쓰지 않는다/아니다"는 다른 설명을 배제하는 출력이 있을 때만, 아니면 "이번 실행에서는 …"과 `[미확인]`. 뜻밖의 로그는 그것을 설명하는 줄을 찾아 인용한다 | #147 |
| 16 | 있는 기록은 지우거나 "잘못된 기록"으로 바꾸지 않고, 그 뒤에 날짜를 단 메모를 더한다. "모른다"고 쓰기 전에 같은 문서를 `grep`한다. 리뷰 지시마다 지시 문장을 자기 diff 옆에 놓고 정확히 그대로 했는지 대조한다(규칙 14의 완료 기준 대조와 같게). 런북 칸에는 PR 과정 문구("R147-2", "영록 처리 중" 등)를 쓰지 않는다. 같은 PR이 세 번 보류되면 영록이 작성자의 커밋 위 `claude/*` 브랜치에서 Opus로 문구를 마무리한다 | #147(R147-3) |

## 상시 규칙

- **작업 위치**: worktree `~/projects/golmok-jaehwan`(아래 `$W`)에서만 일한다. 과제마다 `git -C $W fetch origin` 뒤 `git -C $W switch -c local/jaehwan-<주제> origin/main`. 메인 체크아웃·`.claude/worktrees/`·다른 사람 브랜치는 읽기만 한다(규칙 6). 메인 체크아웃의 git 밖 UE 자료(마네킹·L_Dev 등)는 스크립트로 `$W`에서 다시 만든다.
- **허용 파일**: 과제 행의 "허용 파일"만 고친다. 그 밖의 파일이 바뀌면 되돌리고 PR에 적는다. UE 실행 뒤에는 `git -C $W status --porcelain`이 허용 파일만 보여야 한다(쿡·임포트가 만든 `.uasset`·`M_ZoneScan*`은 커밋하지 않는다).
- **금지**: 병합·`main` push·force-push·rebase·브랜치/태그 삭제, 메인 체크아웃에서 쓰기·패키지·`build/` 삭제, 공유 문서 수정(STATUS·DECISIONS·ROADMAP·DEVELOPMENT-PLAN·CLAUDE.md·AGENTS.md·README.md·tools/README.md — 문안이 필요하면 PR 본문 "병합 시 반영"에), Astra 레인 파일([DEVELOPMENT-PLAN §7.6](../DEVELOPMENT-PLAN.md) 표: `Source/Golmok/Characters/`, 오디오 레인 등), 핫스팟은 과제가 허용한 `// [WP-NN hook]` 블록으로만(별도 커밋), 지출·계정·약관 동의·외부 발송·시스템 보안 설정 변경(방화벽·화면 기록 권한 등은 소유자), `sudo`, LFS 에셋·데이터 삭제, 게임 설계·룩·조작감 판정.
- **GPU·GUI 공유**: UE 에디터 GUI·PIE·`-game`·패키지 실행 전에 `"$TMPDIR/claude/gui-foreground.lock"`을 확인하고 잡는다([mac-setup §3](../runbooks/mac-setup.md) 표의 규칙). 영록이 성능을 재는 동안에는 빌드·쿡·셰이더 컴파일을 하지 않는다. 두 UBT 빌드가 동시에 돌 때 서로 기다리는지·느려지는지는 [미확인]이다. 재환의 추론도 같은 GPU·통합 메모리를 쓰므로 **재환이 잰 fps·GPU ms는 판정 근거가 아니다**. 수치를 적을 때는 LM Studio 모델이 로드돼 있었는지 함께 적는다.
- **패키지 출력**: `GOLMOK_PKG_DIR`는 2026-11-28 현재 비어 있고 `package.sh` 기본값은 `<worktree>/build/Mac`이다. 재환은 항상 `--out-dir "$W/build/Mac"`를 명시한다.
- **증거**: 로그·재현 스크립트·출력은 `$TMPDIR/jaehwan/<과제 id>/`에 두고 병합 알림까지 지우지 않는다(규칙 10).
- **PR**: 제목 `J-NN: <요약>`. 본문 = 요약, 바뀐 파일, 실행한 명령과 출력(복사), 남은 `[미확인]`, "병합 시 반영"(공유 문서 문안이 있으면), **"제출 전 점검표"**(규칙 1~16 한 줄씩 — 한 일과 증거, 또는 "해당 없음"과 이유), 끝 줄 서명(규칙 7). 점검표가 없으면 리뷰를 시작하지 않는다.
- **완료 보고**: CI 모든 행 초록 뒤에만(`gh pr checks <n>` 표, 규칙 2). 게시 뒤 본문을 다시 읽는다(규칙 12).
- **병합하지 않는다.** 병합은 영록이 한다.
- **`py` 뒤에는 `QUIT_EDITOR`**: 창 없는 에디터(`UnrealEditor-Cmd … -nullrhi`)에 `-ExecCmds="py …"`를 줄 때 끝 명령은 `QUIT_EDITOR`다. `Quit`로는 스크립트가 끝나도 에디터가 나가지 않는다(J-12b: 약 13 s에 스크립트가 끝났지만 1800 s 타임아웃 rc 124). 근거 [pc-setup.md](../runbooks/pc-setup.md) §2 "GUI 없이 하는 방법"의 창 없는 에디터 줄.
- **Mac 에디터 로그는 `~/Library/Logs/Unreal Engine/GolmokEditor/`**: 프로젝트 로그는 그 폴더의 `Golmok.log`다. `<project>/Saved/Logs/`는 2026-11-28 현재 `$W`에도 메인 체크아웃에도 없다. 에디터를 다시 띄우면 이전 로그는 같은 폴더의 `Golmok-backup-<시각>.log`가 되므로, 실행 직후 `Golmok.log`를 `$E`에 복사한 뒤 `grep`한다. `Saved/Automation/Report/index.json`은 예전처럼 프로젝트 아래에 생긴다([mac-setup §8 #14](../runbooks/mac-setup.md)).
- **상대 경로 명령은 `cd "$W" &&`로 시작**: 셸의 기본 cwd는 메인 체크아웃이다. `./tools/ue/…`·`unreal/Golmok/…`처럼 상대 경로를 쓰는 명령은 매번 `cd "$W" && …`로 시작한다(규칙 6).
- **커밋 작성자**: 커밋마다 `git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit …`. `git config`에 저장하지 않는다(메인 체크아웃과 다른 세션이 같은 설정을 읽는다).
- **명령마다 로그+exit**: 명령마다 `> $E/<이름>.log 2>&1; echo $? > $E/<이름>.rc`, 돌린 명령 원문은 `$E/commands.txt`에 한 줄씩 더한다. 다음 실행이 덮어쓰는 결과물(`Saved/Automation/Report/index.json`, 에디터 `Golmok.log` 등)은 실행 직후 `$E`에 사본을 둔다(규칙 10).
- **`test.sh` 종료 코드(2026-11-28 메모, J-36 [#154](https://github.com/wooklym/golmok/pull/154) · `8ba637c`)**: 경고 있는 성공만 있는 실행(예: `--filter Golmok.Zone.IndexParse`)이 종료 코드 1이던 옛 규칙은 J-36이 고쳤다. 지금은 보고서 `failed`가 0이고 `succeeded`+`succeededWithWarnings`가 1 이상이면 0이고, 요약 줄 끝에 `Succeeded with warnings: <수>`가 나온다. 그래도 종료 코드 0은 "실패 없이 끝났다"일 뿐이다: 테스트마다 **완료 / skip**은 지금처럼 보고서 `entries`의 skip Info 문구(`… missing - skipped` 등)와 상태 열로 판정한다(규칙 15, mac-setup §4 "기대 결과" 3). J-36 전에 쓴 과제 글·결과의 "종료 코드 1은 경고 있는 성공 때문"이라는 문장은 그때의 기록이다(J-17·J-20).

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
| J-15 | 재환 worktree Development 패키지로 mac-setup §8 #10~#13 — 매니페스트·utoc 이름과 위치, 방화벽 꺼짐 상태의 TraceLog 1985(점유 시 폴백 포트), 패키지 Saved·`-game` CSV는 샌드박스 컨테이너 `~/Library/Containers/com.YourCompany.Golmok/…`(아래 J-15 "결과") | [#151](https://github.com/wooklym/golmok/pull/151) · `7332dac`(증거·실행·초안은 재환의 [#147](https://github.com/wooklym/golmok/pull/147), 그 커밋이 #151 history에 그대로 있다) | R147 → R147-2 → R147-3(3회 보류: 결론이 증거보다 넓음, 로그에 없는 숫자, 인용이 근거 로그와 다름, 실패할 수 없는 검사, 범위 밖 파일 커밋 뒤 되돌림, 있는 기록을 주석 대신 삭제 — 규칙 1·3·6·10·12·14·15·16; 규칙 15·16 추가). 칸 최종 문구는 영록의 Opus 에이전트("병합 시 반영") |
| J-17 | V-17 §0 헤드리스 Mac 부분 선행 기록(pc-verify-v17 §7 표 아래 한 줄): ①~④ 완료(재빌드 2 TU 경고 0, `Zone.IndexParse`·`Portal.SharedInterior`·`Save.RoundTrip` Success — 경고 1·2·4), ⑤ `Weather.Runtime`은 MPC·NS 없음 skip, 보조 `Weather.Lighting` exit 0(`NightUnaffected`) | [#149](https://github.com/wooklym/golmok/pull/149) · `5475c7a` | [R149](https://github.com/wooklym/golmok/pull/149#issuecomment-7229593014)(1회 보류: ⑤ skip을 "완료"로 기록, ① 종료 코드 미저장 — 규칙 14·15·10) → R149-2(영록 직접 대조: 자동화 리포트 사본·빌드 로그·코드) |
| J-20 | V-16 §1·§3 헤드리스 Mac 부분 선행 기록(pc-verify-wp16a §13 표 아래 한 줄, 에셋 전): Weather.Config 완료, Weather.Lighting 완료(`NightUnaffected`), Weather.Runtime skip(MPC·NS 없음), Save.RoundTrip 완료 | [#153](https://github.com/wooklym/golmok/pull/153) · `1d1cfd4` | [R153](https://github.com/wooklym/golmok/pull/153#issuecomment-7230747835)(1회 보류: 필터 단위의 "완료"가 Weather.Runtime의 skip을 묻음 — 규칙 14, R149에 이은 2번째; 런북 줄 길이 — 규칙 10·16) → R153-2(영록 직접 대조). 브랜치 안 병합 커밋 `2fa7817`은 `-c` 누락으로 작성자 `kreativ`(되돌리지 않음, 규칙 7) |
| J-36 | `tools/ue/test.sh` 종료 규칙: `failed` 0이고 `succeeded`+`succeededWithWarnings` > 0이면 통과, 요약 줄 끝에 `Succeeded with warnings:` 수. 스텁 사례가 옛 스크립트에서 실패(2 failed, 43 passed) → 새 스크립트 45 passed, 실제 `--filter Golmok.Zone.IndexParse` 전 rc 1 → 뒤 rc 0, 전체 39 실행 rc 0 | [#154](https://github.com/wooklym/golmok/pull/154) · `8ba637c` | R154(Opus 재현 검증 2렌즈 — 코드·증거, 첫 제출 병합; 남은 B·C는 재환에게 통보) |

**진행 중**

| id | 과제 | 브랜치 | 허용 파일 |
|---|---|---|---|
| J-18 | V-17 §3 Full Precision UV 헤드리스 + `_import_moved` 정리 경고(mac-recon #23) | `origin/local/jaehwan-j18-v17-uv`에 커밋 2개(`b0e6069`·`2e6c53f`, 2026-11-28 10:14 KST, 바탕 `8ba637c`), J-18 PR 없음(2026-11-28 11:13 KST `gh pr list --head local/jaehwan-j18-v17-uv --state all` 빈 출력) | 과제 상세 J-18 절(v17 §7 §3 행, mac-recon #23 칸) |

**다음**: J-18(진행 중) → J-35 → J-11 → J-10 → J-19·J-21~J-23(순서는 영록이 정한다. J-19·J-22는 배정 전 영록 보충이 남았다 — 아래 각 절) → 새로 설계 확정된 J-27·J-30a → J-16(J-27 뒤, 배정 전 영록이 절을 다시 쓴다 — 아래 J-16 절 정정) → 남은 설계 선행 과제(J-24~J-26·J-28·J-29·J-30b·J-31a·J-31b·J-32·J-33).

## 백로그 (의존 순서)

순서 원칙: ① UE 빌드가 필요 없는 도구·테스트·CI 일 → ② 재환 worktree의 UE 빌드를 세우고 증명하는 **관문 J-12·J-12b**(빌드·39 테스트, 합성 zone으로 skip 제거) → ③ 열린 카드의 헤드리스 UE 단계와 [미확인] 행 → ④ Claude 레인 코드 후속. **설계 선행** 표시 과제는 영록(Opus)이 짧은 설계 메모(파일·방법·완료 기준)를 이 파일의 해당 행 아래 또는 배정 메시지로 먼저 쓴 뒤에만 배정한다. J-10·J-11·J-27·J-30a는 설계가 확정되어(Opus 2026-11-28, 아래 각 절) 배정할 수 있다(J-30a는 옛 J-30을 좁힌 것이고, 메시 절반 J-30b는 설계 선행 그대로다). 크기: S ≤ 반나절, M ≤ 하루, L > 하루.

| id | 과제 | 선행 | 크기 | 설계 선행 |
|---|---|---|---|---|
| J-10 | CI shellcheck 잡(공식 v0.11.0 고정·sha256, `--severity=warning`, 기존 결함은 표에 정한 줄별 지시문만 — 실행 줄 변경 없음, 같은 커밋 8/8 초록) | 없음(설계 메모 확정, Opus 2026-11-28) | S–M | 설계 확정(J-10 절) |
| J-11 | CI 뷰어 `npm test` 잡(`viewer-smoke`, ubuntu-24.04 한 행 — Playwright 1.56.1은 `ubuntu-latest`(26.04) 미지원, `ci.yml` 훅 블록은 별도 커밋, 같은 커밋 8/8 초록) | 없음 | M | — (설계 확정, Opus 2026-11-28, 아래 J-11 절) |
| J-16 | `_pure.py` Mac 경로 가정·`package.sh` 주석을 J-15 실측으로 정리 | J-15, J-27(정정 2026-11-28: 에디터 바이너리 경로의 근거는 J-27 #27 — 아래 J-16 절) | S–M | 배정 전 영록이 행·절을 다시 쓴다(J-27 설계 10) |
| J-18 | V-17 §3 Full Precision UV 헤드리스 + WP-06 `_import_moved` 정리 경고(mac-recon #23) | J-12b | M | **준비 메모** |
| J-19 | V-17 §5 패키지 quinn 전환 로그 확인 | J-15 | S | — |
| J-21 | WP-16a 불확실 API 표 §12의 컴파일·심볼 행 | J-12 | S | — |
| J-22 | V-16 §11 Mac 패키지 명령 이식(에셋 전 기대 결과) | J-15, J-20 | M | — |
| J-23 | 19b A1 ① 회귀 헤드리스(GASP 없이) | J-12 | S | — |
| J-24 | V-08b §9-1·§9-2 `locomotion_metrics.py` 순수 지표 + 합성 테스트 | 설계 메모 | M | **설계 선행** |
| J-25 | V-16 §2a MPC 헤드리스 생성 시험 | J-20, 설계 메모 | S | **설계 선행** |
| J-26 | V-18 §0·§1 헤드리스(8 WAV 재임포트, 커밋 없음) | J-12, 설계 메모 | S | **설계 선행** |
| J-27 | V-05 S12 `run_game_perf.sh` Mac 첫 실행 — 도구 경로만, 성능 아님(헤드리스 생성기로 합성 정지 경로 20 s `j27_dwell` + `game_scripts(tags=("a",), discover_from_index=False)`, `-game -RenderOffscreen` 1회, CSV 위치·`-ExecCmds` argv(`KERN_PROCARGS2`)·실행 파일 관찰, 고정 기대값과 `diff`, mac-setup §8 #27 한 줄, 코드 변경 없음) | J-15(병합됨), J-12·J-12b의 `$W` 자료, J-36(병합됨). J-16은 J-27 뒤 | M | 설계 확정(Opus 2026-11-28, 아래 J-27 절) — 배정 가능 |
| J-28 | CI `swift build`(golmok-objcap, macos-latest) | 설계 메모 | S–M | **설계 선행** |
| J-29 | 크래시 리포트 업로드 끄기 훅(WP-21 후속 5) | 설계 메모(키 결정) | S | **설계 선행** |
| J-30a | COLMAP 희소 모델 → EXIF GPS ENU 정합(`model_aligner --ref_images_path … --ref_is_gps 1 --alignment_type enu --alignment_max_error 3`, 원점 = 이름순 첫 장 `DJI_0352.JPG`) → 정합 좌표의 Brush 3k splat, 공개 Tyrol 76장, 펜스 스크립트 13개 수치 판정(잔차 중앙값 ≤ 3 m 등)·비공허 대조군, mac-recon M3 메모 1줄 + §6 #5 칸만(WP-21 후속 4의 절반 — 메시 절반은 J-30b, 설계 선행) | 없음(설계 확정, Opus 2026-11-28) | S–M | 설계 확정(J-30a 절) |
| J-30b | Object Capture 메시를 J-30a 정합 좌표로(`tyrol-full/poses.json` 카메라 중심 ↔ J-30a 정합 COLMAP 카메라 중심 Sim3, 잔차·OBJ 정점 ↔ SfM 점 거리; WP-21 후속 4의 나머지 절반) | J-30a, 설계 메모(J-30a 설계 13) | M | **설계 선행** |
| J-31a | 입력 드라이버 키 타임라인 파서(순수 Python + pytest) | Opus B1 설계 메모 | S | **설계 선행** |
| J-31b | 헤드리스 자동화 1개 "W 3 s → 캡슐 이동 거리"(측정용 주입 경로는 Opus가 구현) | J-31a, Opus 주입 구현 | S | **설계 선행** |
| J-32 | Cesium 활성 사본에서 mac-recon #15·#16(게임 타깃 빌드·`test.sh` 영향) | WP-21 후속 1 결정, 설계 메모 | M | **설계 선행** |
| J-33 | avfoundation 60 fps 녹화 시험(§8 #25) | 소유자 화면 기록 권한, 설계 메모 | S | **설계 선행** |
| J-35 | add-gasp 편집기 가드의 남은 분기 스텁 사례(`$GaspProject` 일치·음성 2종, J-06 후속) | J-36(병합됨 `8ba637c` — 같은 테스트 파일) | S | — (보충 2026-11-28, 아래 J-35 절) |

J-06·J-07·J-08·J-09·J-12·J-12b·J-13·J-14·J-15·J-17·J-20·J-34·J-36은 끝났고(위 "완료"), J-18은 진행 중이다(위 "진행 중"). J-27·J-30a는 설계가 확정됐다(2026-11-28, Opus — J-30은 J-30a·J-30b로 나눴다). 아래 상세 절은 그대로 두고, 끝난 과제에는 "결과" 줄을 더한다.

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
  9. **PR 본문**: "완료 기준 대조"(규칙 14) 절에 아래 (a)~(j)를 한 줄씩(충족 + 증거 파일, 또는 **미충족** + 이유) 둔다. 과제 문장은 `$E/task.txt`에서만 옮긴다. "제출 전 점검표"는 규칙 1~16을 한 줄씩 과거형과 결과로 쓴다(정정 2026-11-28: 처음 적은 "1~15"는 규칙 16 추가 전 숫자다). `gh pr checks <n>` 출력을 붙인 뒤 본문을 다시 읽는다(규칙 12). 다시 읽을 때의 자리표시 검사(정정 2026-11-28): `gh pr view <n> --json body --jq .body > "$E/posted-body.md"; grep -n -E '<[^>]+>|\[\]|TODO|TBD' "$E/posted-body.md" > "$E/placeholder-hits.log"`. 과제 글을 인용하거나 명령을 기록하면 `<n>`·`<c>` 같은 토큰이 원래 걸리므로 "걸림 없음"을 기대하지 않는다. `placeholder-hits.log`의 모든 줄을 본문 끝 표(줄 번호 · 걸린 글자 · 분류)에 `원문 인용`(과제 인용 블록 안) / `명령 기록`(실행한 명령 블록 안) / `미채움` 중 하나로 분류하고, `미채움`은 0이어야 한다.
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
  7. PR 본문에 "완료 기준 대조"(규칙 14) 절을 두고 아래 (a)~(h)를 한 줄씩(충족 + 증거 파일, 또는 **미충족** + 이유) 적는다. 과제 문장은 `$E/task.txt`에서만 옮긴다. attempt 표의 열은 attempt·결론·시작·끝·소요(초, `attempts.tsv`에서 계산한 명령도 함께)·`npm test` 마지막 `OK:` 줄이다. "제출 전 점검표"는 규칙 1~16을 한 줄씩 과거형과 결과로 쓴다(정정 2026-11-28: 처음 적은 "1~15"는 규칙 16 추가 전 숫자다). 그다음 `gh pr checks <n>` 출력을 붙이고 본문을 다시 읽는다(규칙 12). 다시 읽을 때의 자리표시 검사(정정 2026-11-28): `gh pr view <n> --json body --jq .body > "$E/posted-body.md"; grep -n -E '<[^>]+>|\[\]|TODO|TBD' "$E/posted-body.md" > "$E/placeholder-hits.log"`. 과제 글을 인용하거나 명령을 기록하면 `<n>`·`<c>` 같은 토큰이 원래 걸리므로 "걸림 없음"을 기대하지 않는다. `placeholder-hits.log`의 모든 줄을 본문 끝 표(줄 번호 · 걸린 글자 · 분류)에 `원문 인용`(과제 인용 블록 안) / `명령 기록`(실행한 명령 블록 안) / `미채움` 중 하나로 분류하고, `미채움`은 0이어야 한다.
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
- **결과(2026-11-28, [#151](https://github.com/wooklym/golmok/pull/151) · `7332dac`, 리뷰 R147 → R147-2 → R147-3)**: 증거·실행·초안은 재환의 [#147](https://github.com/wooklym/golmok/pull/147)(head `45bb451`)이다. 세 번 보류된 뒤 칸 4개의 최종 문구는 영록의 Opus 에이전트가 재환의 커밋 위 `claude/j15-cells`에서 썼다("병합 시 반영", 규칙 16). 재환 worktree의 Development 패키지 `build/Mac/Golmok.app`을 `-game -RenderOffScreen -ResX=1920 -ResY=1080 -csvCaptureFrames=200,300`으로 2회(06:30·07:01) 실행했다. 방화벽은 두 번 읽어 둘 다 꺼짐(`State = 0`)이었다. #10: `Golmok-Mac.utoc`·`global.utoc`·`Golmok-Mac.pak`은 `.app` 안 `Contents/UE/Golmok/Content/Paks/`에 있고, `Manifest_*_Mac.txt` 세 개는 패키지 폴더가 아니라 `unreal/Golmok/Saved/StagedBuilds/Mac/`에 있다. #11: 1회차는 실행 전부터 떠 있던 CrashReportClient가 1985를 잡고 있어 게임이 40252를, 2회차는 1985가 비어 있어 게임이 1985를 열었다. 대화상자는 관찰되지 않았다. 방화벽이 켜진 상태의 동작은 [미확인]이라 #11은 "부분"이다. #12·#13: 앱이 샌드박스로 서명돼 있어 Saved와 CSV는 `~/Library/Containers/com.YourCompany.Golmok/Data/Library/Application Support/Epic/Golmok/Saved/` 아래에 쓰였다. 적어 둔 후보 경로들에는 없었다(그 `find`의 명령 줄은 로그에 남지 않았다). 번들 id는 `com.YourCompany.Golmok`(엔진 기본값, 프로젝트 Config에 덮어쓰기 없음)이다. 다른 구성·조건에서의 위치와, 번들 id가 같은 다른 패키지가 컨테이너를 같이 쓰는지는 [미확인]이다. mac-setup §3·§4·§6·§9의 관련 문장에는 2026-11-28 메모를 더했다(재환 레인 문서 5). 선행이 풀린 과제: J-16·J-19. J-22는 J-20, J-27은 설계 메모를 더 기다린다.

#### J-16 `_pure.py` Mac 경로 가정·`package.sh` 주석 정리
- **출처**: `unreal/Golmok/Content/Python/golmok/_pure.py:1779`, `:1787`, `:1802`, `:1986`([미확인] Mac 경로 가정 — `UserSettingsDir`·`LaunchMac.cpp`), `tools/ue/package.sh:26`(방화벽 [미확인]), J-15 실측.
- **할 일**: 실측이 가정과 같으면 주석만 "확인(J-15, §8 #n)"으로. 다르면 함수를 실측에 맞추고 `tools/tests/test_ue_python_spike_runner.py`(또는 해당 테스트)에 실측 경로 사례를 더한다 — 이 경우 영록에게 먼저 알린다(Claude 레인 코드 변경).
- **허용 파일**: `_pure.py`의 위 함수·주석, 해당 pytest, `tools/ue/package.sh` 주석 줄.
- **완료 기준**: 바꾼 줄마다 근거 출력, 파이썬 게이트·CI 초록.
- **왜 재환 / 위험**: 근거가 명령 출력으로 있다. 위험: 한 번의 실행으로 모든 경우를 일반화하는 것(규칙 3).
- **정정(2026-11-28, 영록 — 아직 배정하지 않은 과제라 배정을 멈춘다)**: 위 "할 일"의 "실측이 같으면 주석만, 다르면 함수를 고친다"는 판단을 재환에게 남겨 두어 이대로는 배정하지 않는다. 또 J-15의 근거(샌드박스로 서명된 **패키지 `.app`**이 `~/Library/Containers/com.YourCompany.Golmok/…`에 쓴 것, mac-setup §8 #12·#13)는 `MAC_USER_SETTINGS_REL`(`_pure.py:1779`·`:1802`)·`editor_exe`(`:1787`)·`sh_arg`(`:1986`)가 가정하는 **에디터 바이너리 `-game`** 실행과 다른 경우다(엔진 `LaunchMac.cpp:111-114`: ` -installed`는 패키지 게임에만). 그래서 J-16은 J-27(아래, 에디터 바이너리 `-game` 1회 관찰 → mac-setup §8 #27) **뒤에** 한다. 배정 전에 영록이 J-27의 #27과 #12·#13을 근거로 바꿀 줄마다 새 주석·코드 줄을 글자 그대로 적어 이 절을 다시 쓴다(J-27 설계 10·"병합 시 반영"). `package.sh:26` 방화벽 주석 한 줄만 따로 떼어 먼저 줄지도 그때 정한다.

#### J-17 V-17 §0 헤드리스
- **출처**: [pc-verify-v17.md §0](../runbooks/pc-verify-v17.md)(39 Success, Claude 레인 후속 5 확인: `GolmokGeoMath.h` NaN 가드 컴파일, `Golmok.Zone.IndexParse` Success, `Golmok.Portal.SharedInterior` Pending 형제 연기 2단계), STATUS WP-05·WP-09 행("🟡 PC 확인 V-17 §0").
- **할 일**: J-12b로 합성 zone을 만든 `$W`에서 v17 §0(:24)의 다섯 후속 항목을 **모두** 다룬다 — ① J-12 빌드 로그에서 `GolmokGeoMath.h`·`GolmokCharacter.cpp` 경고 `grep`, ② `test.sh --filter Golmok.Zone.IndexParse`, ③ `test.sh --filter Golmok.Portal.SharedInterior`(Pending 형제 연기 Info 줄), ④ `test.sh --filter Golmok.Save.RoundTrip` 닫기 단계 `[Info]` 2줄·`(game viewport yes)`, ⑤ `test.sh --filter Golmok.Weather.Runtime` `NightUnaffected`(MPC가 없으면 skip이 기대). 각각 결과와 Info 줄 원문.
- **허용 파일**: v17 §7 결과 표 **아래의 "Mac 선행 기록" 줄**(새로 더한다). §0 행의 결과 칸 자체는 고치지 않는다 — 카드 §0 전체(39 + L_ZoneTest·Weather 에셋 포함)는 아직 끝나지 않았다.
- **완료 기준**: 기록은 `Mac 부분 선행(J-17, 합성 zone 있음/없음, SHA <짧은 SHA>)`로 시작하고 ①~⑤ 각각을 **완료 / skip / 실행 안 함** 중 하나로 적는다(명령별 종료 코드·상태·Info 줄 원문은 PR에). skip이면 통과라 쓰지 않는다.
- **왜 재환 / 위험**: 로그 대조. 위험: skip을 통과로 읽는 것.
- **정정**(정정 2026-11-28: 위 할 일 ⑤는 `NightUnaffected`를 `Golmok.Weather.Runtime` 아래에 두었는데, 영록의 문서 오류다(R149). `GolmokWeatherTest.cpp`에서 `NightUnaffected()`는 `FLightingScenario`(:544)의 한 단계로 :585에서만 불리고, 그 시나리오의 등록 이름은 `Golmok.Weather.Lighting`(:1335)이다. `Golmok.Weather.Runtime`(:1355, `FRuntimeScenario` :895)은 이 단계를 돌리지 않는다. 그래서 ⑤ `Weather.Runtime`은 MPC·NS가 없으면 skip Info 2줄로 Success(= skip)이고, `[Info] NightUnaffected at …` 줄은 `test.sh --filter Golmok.Weather.Lighting` 보조 실행에서 본다(R149가 정한 기록 형태). 재환이 이 문장으로 이미 작업했으므로 할 일 문장은 고치지 않고 여기 적는다. 같은 오류가 있던 [pc-verify-v17.md](../runbooks/pc-verify-v17.md) §0 문장은 2026-11-28에 고쳤다.)
- **결과(2026-11-28, [#149](https://github.com/wooklym/golmok/pull/149) · `5475c7a`, 리뷰 R149 → R149-2)**: pc-verify-v17 §7 표 아래에 "Mac 부분 선행(J-17, 합성 zone 있음, SHA 84ad068)" 줄을 더했다. ①~④ 완료, ⑤ skip(`MPC_GolmokWeather missing - skipped`·`NS_GolmokRain missing - skipped`), `NightUnaffected`는 보조 실행 `Golmok.Weather.Lighting`(exit 0)에서 확인. ②~⑤ 필터 실행의 `test.sh` 종료 코드가 1이었던 것은 테스트 실패가 아니라 경고 있는 성공을 실패로 세는 종료 규칙 때문이다 — J-36이 고친다(2026-11-28 메모: J-36 [#154](https://github.com/wooklym/golmok/pull/154) · `8ba637c`로 고쳐졌다. 완료/skip 판정은 그 뒤에도 보고서의 skip 문구로 한다). 첫 제출은 ⑤를 "완료"로 적어 보류됐다(R149).

#### J-18 V-17 §3 Full Precision UV 헤드리스 + `_import_moved` 정리 경고 — 준비 메모
- **출처**: v17 §3(:40-44, 기대 로그 `zone_import: full precision UVs (LOD0) on 2/2 chunks (2 set, 0 already on)`, warnings 수 불변), [pc-verify-wp06.md](../runbooks/pc-verify-wp06.md) §2·§12 #41, STATUS WP-06 행 끝(Claude 레인 후속 5: `_import_moved` 스크래치 삭제 실패 시 `WARNING cleanup: could not delete … (runbook #8)` — 🟡 정상 경로 로그 불변), [mac-recon.md](../runbooks/mac-recon.md) 미확인 #23(`zone_import` Mac 실행).
- **준비 메모(영록)**: `L_ZoneTest`·`z_synthetic_001`은 J-12b가 만든다. 합성 **스캔** zone(`make_synthetic_zone` + `zone_import`)을 Mac에서 헤드리스로 만들 수 있는지 [미확인] — 영록이 실행 순서와 명령(J-12b와 같은 `-ExecCmds` 형식)을 적는다. GUI 체크박스 확인 대신 Python으로 LOD0 빌드 설정을 읽어 출력하는 한 줄도 메모에 둔다.
- **허용 파일**: v17 §7 §3 행, mac-recon #23 칸. 생성된 에셋·맵은 커밋하지 않는다(`.gitignore` 대상과 `M_ZoneScan*` 포함 — `git status`로 확인).
- **완료 기준**: 기대 로그 줄 `grep` 원문, `done … warnings` 수, `WARNING cleanup` 줄 수(정상 경로 0 기대), LOD0 `use_full_precision_u_vs` 읽기 출력, 청크당 임포트 시간. `-ExecutePythonScript` 종료 크래시(WP-21 부수 발견)가 나면 결과 파일이 그 전에 써졌는지 적는다.
- **왜 재환 / 위험**: 헤드리스 로그로 판정된다. GUI 확인 절반은 영록.
- **진행 상태(2026-11-28, 영록 기록)**: 재환이 `origin/local/jaehwan-j18-v17-uv`에 커밋 2개를 push했다(`b0e6069` v17 §7 §3 행·mac-recon #23 칸, `2e6c53f` 청크 간격 수정, 바탕 `8ba637c`, diff는 두 런북 각 한 줄). 2026-11-28 11:13 KST에 J-18 PR은 없다(`gh pr list --head local/jaehwan-j18-v17-uv --state all` 빈 출력, 브랜치 끝 `2e6c53f` 그대로). 위 "준비 메모(영록)"의 명령(합성 스캔 zone 헤드리스 생성, LOD0 `use_full_precision_u_vs` 읽기 한 줄, "청크당 임포트 시간"의 근거 로그 줄, 각 `grep`의 기대 출력)은 이 파일에 적히지 않은 채 진행됐다. PR이 열리면 리뷰는 PR 본문의 실행 명령을 기준으로 재현한다.

#### J-19 V-17 §5 패키지 quinn 전환
- **출처**: v17 §5(:51-56, 기대: 전환마다 `selected …`, 끝 `current=quinn`, `not found`·거절 없음, 쿡에 `SKM_Quinn_Simple`), [pc-verify-wp18a.md](../runbooks/pc-verify-wp18a.md) §14-6.
- **할 일**: J-15 패키지로 `Golmok.app/Contents/MacOS/Golmok -RenderOffScreen -ExecCmds="golmok.character list,golmok.character proxy135,golmok.character quinn,golmok.character list,…"`(정확한 명령 문법은 런북 그대로 — Mac에서 `-ExecCmds` 다중 명령이 도는지 자체가 [미확인]), 로그 `grep`, 쿡 목록에서 `SKM_Quinn_Simple` `grep`.
- **허용 파일**: v17 §7 §5 행. 실패해도 코드를 고치지 않는다(캐릭터는 Astra 레인).
- **완료 기준**: 로그 줄 원문, 쿡 목록 `grep -c`.
- **왜 재환 / 위험**: 로그만으로 판정된다.
- **보충(2026-11-28, 영록 — 배정 전, 일부만)**: ① 명령 순서는 v17 §5 ③ 원문 `list → proxy135 → quinn → list → proxy110 → manny → quinn → list`이고, 콘솔 명령 꼴은 `golmok.character list | <id>`(`Characters/GolmokCharacterSubsystem.cpp:268-269`)다. 그래서 `-ExecCmds` 값은 정확히 `golmok.character list,golmok.character proxy135,golmok.character quinn,golmok.character list,golmok.character proxy110,golmok.character manny,golmok.character quinn,golmok.character list`이다. ② 기대 문자열(같은 파일): 전환마다 `golmok.character: selected <id> (`(`:265`·`:520`), `list` 줄에 `current=quinn`(`:530`, 마지막 `list`), 거절 문구 `mesh/animation missing or skeleton mismatch`(`:433`·`:457`)와 `Character mesh '`로 시작해 `' not found`가 있는 줄(`Player/GolmokCharacter.cpp:87`)은 0줄. ③ 쿡 목록 파일은 J-15 실측대로 `"$W/unreal/Golmok/Saved/StagedBuilds/Mac/Manifest_UFSFiles_Mac.txt"`(mac-setup §8 #10)이고, `SKM_Quinn_Simple`은 이 파일에서 `grep -c`한다. ④ 패키지 실행은 GUI 잠금을 잡는다(상시 규칙 "GPU·GUI 공유"). 잠금 명령(목적 `J-19-pkg`): 확인 `L="$TMPDIR/claude/gui-foreground.lock"; if [ -e "$L" ]; then cat "$L"; else echo "no lock"; fi > "$E/lock-check.log"; date -u +%FT%TZ >> "$E/lock-check.log"` — 기대 첫 줄 `no lock`(다른 줄이 있으면 **지우지 않고** 그 줄을 영록에게 보내고 기다린다). 잡기 `mkdir -p "$TMPDIR/claude" && (set -C; printf '%s %s %s\n' "재환" "J-19-pkg" "$(date -u +%FT%TZ)" > "$TMPDIR/claude/gui-foreground.lock"); echo $? > "$E/lock-take.rc"` — 기대 `0`. 갱신([AGENTS.md](../../AGENTS.md) "UE를 같이 쓰는 규칙"·mac-setup §3: 20분이 지난 기록은 빈 것으로 보므로 잡은 쪽이 쓰는 동안 갱신한다) — 패키지 앱 실행 명령마다(`<n>`은 영록이 배정 전 보충에서 명령마다 정한다) 바로 앞에 매번 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-19-pkg ' "$L" && printf '%s %s %s\n' "재환" "J-19-pkg" "$(date -u +%FT%TZ)" > "$L"; echo $? > "$E/lock-refresh-<n>.rc"`(기대 `0`; 0이 아니면 잠금 파일을 지우거나 쓰지 않고 멈춘다), 그리고 그 명령 자체는 갱신 루프로 감싼다: 앞에 `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-19-pkg ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-19-pkg" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!;`, 끝에 `; kill "$RP"`. 풀기 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-19-pkg ' "$L" && rm "$L"; echo $? > "$E/lock-release.rc"` — 기대 `0`. **아직 정하지 않은 것(배정 전 영록)**: 패키지 게임 로그의 위치 — J-15는 컨테이너 `~/Library/Containers/com.YourCompany.Golmok/Data/Library/Application Support/Epic/Golmok/Saved/` 아래의 `Profiling`·`Config`·`SaveGames`만 기록했고 `Logs`는 확인하지 않았다([미확인]). 패키지 `.app`에서 `-ExecCmds` 다중 명령이 도는지도 [미확인]이다(J-27은 에디터 바이너리만 본다).

#### J-20 V-16 §1·§3 헤드리스 기준선
- **출처**: [pc-verify-wp16a.md](../runbooks/pc-verify-wp16a.md) §1(빌드)·§3(헤드리스 자동화), STATUS V-16 행. MPC·NS 에셋(§2)은 아직 없다 → `Golmok.Weather.*`는 해당 단계 skip Info로 Success가 기대(v17 §0 문구).
- **할 일**: `test.sh --filter Golmok.Weather`, `test.sh --filter Golmok.Save`, Info 줄 `grep`.
- **허용 파일**: wp16a §13 결과 기록 아래의 "Mac 선행 기록" 줄(새로 더한다). §1·§3 행의 결과 칸은 고치지 않는다.
- **완료 기준**: 기록은 `Mac 부분 선행(J-20, 에셋 전, 합성 zone 있음/없음, SHA <짧은 SHA>)`로 시작하고 테스트마다 **완료 / skip / 실행 안 함**으로 적는다. 상태·Info 원문은 PR에. `Golmok.Save.*`가 `L_ZoneTest missing`으로 skip이면 J-12b가 덜 된 것이다 — 멈추고 알린다.
- **왜 재환 / 위험**: 명령 검증. 위험: skip을 통과로 적는 것.
- **결과(2026-11-28, [#153](https://github.com/wooklym/golmok/pull/153) · `1d1cfd4`, 리뷰 R153 → R153-2)**: pc-verify-wp16a §13 결과 표 아래에 "Mac 부분 선행(J-20, 에셋 전, 합성 zone 있음(z_synthetic_002는 청크·콜리전 에셋 없음), SHA 5475c7a)" 줄을 더했다(그 파일 +2 −0). §1 빌드 종료 코드 0(업투데이트 빌드라 전면 재컴파일의 Niagara 경고 문구는 [미확인]). 테스트별: Weather.Config 완료, Weather.Lighting 완료(`[Info] NightUnaffected at 05:35 (base lux 0.104167)`), Weather.Runtime **skip**(MPC·NS 없음 skip Info 2줄, 경고 1), Save.RoundTrip 완료(날씨 단계 실행, close 단계 Info 2줄, 경고 4: z_synthetic_002 에셋 없음). Save 필터 실행의 종료 코드 1은 그때의 `test.sh` 규칙 때문이었다(J-36 [#154](https://github.com/wooklym/golmok/pull/154)가 뒤에 고쳤다). [R153](https://github.com/wooklym/golmok/pull/153#issuecomment-7230747835)이 한 번 보류했다: (A) 필터 단위로 "완료"를 적어 Weather.Runtime의 skip이 묻혔고(규칙 14, R149에 이은 2번째·같은 테스트), (B) 브랜치 안 병합 커밋 `2fa7817`(#152 병합분을 받은 것)은 `-c`를 빠뜨려 작성자가 `kreativ`로 남았고(규칙 7, #142에 이은 2번째 — 되돌리지 않음), (B) 런북 줄이 길고 임시 로그 이름·진행 문구가 들어 있었다(규칙 10(g)·16). 재환이 테스트별 짧은 줄로 바꾼 뒤(`97b76bd`) R153-2(영록 직접 대조: 자동화 리포트 사본 2개의 테스트별 state·경고·skip 메시지, 실행 rc, 최종 본문)에서 병합했다. 선행이 풀린 과제: J-22.

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
- **보충(2026-11-28, 영록 — 배정 전, 일부만)**: J-20(#153)·J-15(#151)가 끝나 선행이 풀렸다. 위 "할 일"의 줄임표 경로는 J-15 실측(mac-setup §8 #10)으로 읽는다: 매니페스트는 패키지 폴더가 아니라 `"$W/unreal/Golmok/Saved/StagedBuilds/Mac/Manifest_UFSFiles_Mac.txt"`, utoc는 `.app` 안 `"$W/build/Mac/Golmok.app/Contents/UE/Golmok/Content/Paks/Golmok-Mac.utoc"`다. 앱 실행은 GUI 잠금을 잡는다(상시 규칙). 잠금 명령(목적 `J-22-pkg`): 확인 `L="$TMPDIR/claude/gui-foreground.lock"; if [ -e "$L" ]; then cat "$L"; else echo "no lock"; fi > "$E/lock-check.log"; date -u +%FT%TZ >> "$E/lock-check.log"` — 기대 첫 줄 `no lock`(다른 줄이 있으면 **지우지 않고** 그 줄을 영록에게 보내고 기다린다). 잡기 `mkdir -p "$TMPDIR/claude" && (set -C; printf '%s %s %s\n' "재환" "J-22-pkg" "$(date -u +%FT%TZ)" > "$TMPDIR/claude/gui-foreground.lock"); echo $? > "$E/lock-take.rc"` — 기대 `0`. 갱신([AGENTS.md](../../AGENTS.md) "UE를 같이 쓰는 규칙"·mac-setup §3: 20분이 지난 기록은 빈 것으로 보므로 잡은 쪽이 쓰는 동안 갱신한다) — 앱 실행 명령마다(`<n>`은 영록이 배정 전 보충에서 명령마다 정한다) 바로 앞에 매번 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-22-pkg ' "$L" && printf '%s %s %s\n' "재환" "J-22-pkg" "$(date -u +%FT%TZ)" > "$L"; echo $? > "$E/lock-refresh-<n>.rc"`(기대 `0`; 0이 아니면 잠금 파일을 지우거나 쓰지 않고 멈춘다), 그리고 그 명령 자체는 갱신 루프로 감싼다: 앞에 `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-22-pkg ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-22-pkg" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!;`, 끝에 `; kill "$RP"`. 풀기 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-22-pkg ' "$L" && rm "$L"; echo $? > "$E/lock-release.rc"` — 기대 `0`. **아직 정하지 않은 것(배정 전 영록)**: 앱 로그 위치(J-19 보충과 같은 [미확인] — 컨테이너 `Saved/Logs`는 J-15에서 확인하지 않았다)와 명령마다의 기대 출력 원문(에셋 없음의 `mpc ok` 없음 등).

#### J-23 19b A1 ① 회귀 헤드리스
- **출처**: [pc-verify-wp19.md](../runbooks/pc-verify-wp19.md) A1(:43-57): `test.sh --filter Golmok.Animation --setup-dev-level` → 4 Success, `GaspSmoke` `[Info] GASP not installed — skipped`, `Fallback` 기대 Warning 1개, `StateProvider` Info `GASP pawn after p0: accel 2048/2048 …`, `Saved/Logs`에 `Character mesh '' not found` 없음. STATUS WP-19 행.
- **할 일**: 위 명령과 로그 `grep`(Mac에서 런북의 `Saved/Logs`는 `~/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log`다 — 상시 규칙). 에디터 PIE `golmok.anim status` 단계는 GUI라 영록에게 남긴다.
- **허용 파일**: wp19 A1 결과(런북 결과 절의 A1 행)만.
- **완료 기준**: 기대 문자열마다 `grep -c` 출력.
- **왜 재환 / 위험**: 기대 문자열이 런북에 정확히 있다.
- **보충(2026-11-28, 영록 — 배정 전)**: ① 실행 직후 에디터 로그를 복사한 뒤 `grep`한다: `cp "$HOME/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log" "$E/anim-editor.log"`(상시 규칙 "Mac 에디터 로그"). ② `test.sh`의 기대 종료 코드는 `0`이다: J-36(`8ba637c`) 뒤로는 보고서 `failed`가 0이고 `succeeded`+`succeededWithWarnings`가 1 이상이면 0이다(`Fallback`의 기대 Warning처럼 경고 있는 성공도 센다 — 상시 규칙 "`test.sh` 종료 코드"). GaspSmoke가 완료인지 skip인지는 종료 코드가 아니라 보고서의 `[Info] GASP not installed — skipped` 문구로 적는다. ③ "`Character mesh '' not found` 없음"은 `grep -c -F "Character mesh '' not found" "$E/anim-editor.log"`가 `0`이라는 뜻이다(문구 출처 `Player/GolmokCharacter.cpp:87`). ④ `test.sh` 실행 동안 GUI 잠금을 잡는다(J-17·J-36과 같은 관례 — `--setup-dev-level`과 테스트는 몇 분 넘게 걸릴 수 있다). 잠금 명령(목적 `J-23-headless`, `<n>`은 `anim`): 확인 `L="$TMPDIR/claude/gui-foreground.lock"; if [ -e "$L" ]; then cat "$L"; else echo "no lock"; fi > "$E/lock-check.log"; date -u +%FT%TZ >> "$E/lock-check.log"` — 기대 첫 줄 `no lock`(다른 줄이 있으면 **지우지 않고** 그 줄을 영록에게 보내고 기다린다). 잡기 `mkdir -p "$TMPDIR/claude" && (set -C; printf '%s %s %s\n' "재환" "J-23-headless" "$(date -u +%FT%TZ)" > "$TMPDIR/claude/gui-foreground.lock"); echo $? > "$E/lock-take.rc"` — 기대 `0`. 갱신([AGENTS.md](../../AGENTS.md) "UE를 같이 쓰는 규칙"·mac-setup §3: 20분이 지난 기록은 빈 것으로 보므로 잡은 쪽이 쓰는 동안 갱신한다) — `test.sh` 명령 바로 앞에 매번 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-23-headless ' "$L" && printf '%s %s %s\n' "재환" "J-23-headless" "$(date -u +%FT%TZ)" > "$L"; echo $? > "$E/lock-refresh-<n>.rc"`(기대 `0`; 0이 아니면 잠금 파일을 지우거나 쓰지 않고 멈춘다), 그리고 그 명령 자체는 갱신 루프로 감싼다: 앞에 `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-23-headless ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-23-headless" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!;`, 끝에 `; kill "$RP"`. 풀기 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-23-headless ' "$L" && rm "$L"; echo $? > "$E/lock-release.rc"` — 기대 `0`. 그래서 실행 명령은 정확히 `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-23-headless ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-23-headless" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && /usr/bin/timeout 2700 ./tools/ue/test.sh --filter Golmok.Animation --setup-dev-level > "$E/anim-test.log" 2>&1; echo $? > "$E/anim-test.rc"; kill "$RP"`(하네스 백그라운드로 돌리고 `anim-test.rc`가 생길 때까지 기다린다)이고, 그 뒤 ①의 `cp`, 그다음 잠금 풀기다. 멈출 때는 먼저 `pgrep -fl '[g]olmok-jaehwan/unreal/Golmok/Golmok.uproject' > "$E/editor-stop.log"; echo $? > "$E/editor-stop.rc"`를 돌린다 — rc `1`이면 잠금을 풀고 묻고, rc `0`이면(에디터가 남았다) 프로세스를 건드리지 않고 잠금도 풀지 않은 채 `editor-stop.log`를 영록에게 보낸다. 완료 기준에 더한다: `lock-take.rc`·`lock-refresh-anim.rc`·`lock-release.rc` 모두 `0`, `anim-test.rc` `0`.

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

#### J-27 V-05 S12 `run_game_perf.sh` Mac 첫 실행: 도구 경로 점검(성능 아님) — 설계 확정(Opus 2026-11-28)
- **출처**: [pc-spike.md](../runbooks/pc-spike.md) S12(:155-169, 정본 `-game -RenderOffscreen` 측정 — V-05 → D-010, DEVELOPMENT-PLAN §5.4 핵심 경로 C-02 → V-05 → D-010). 생성기: `spike_runner.py:908-973` `game_scripts`(win32가 아니면 `run_game_perf.sh`, LF·실행 비트), `:118` `_require_path_files`(경로 JSON이 `Saved/Golmok/Paths/<이름>.json`에 있어야 한다), `:166`·`:187`·`:191`(엔진 폴더·실행 파일·Saved 후보). `_pure.py:1688` `dwell_path_json`(두 샘플 정지 경로), `:1722` `game_command_line`, `:1762` `discover_from_index_arg`, `:1782` `MAC_USER_SETTINGS_REL`와 그 위 주석([미확인] ①: 사용자별 폴더 `~/Library/Application Support/Epic`), `:1785-1795` `editor_exe`의 darwin 분기([미확인] ③), `:1798-1810` `platform_saved_dir_candidates`(후보 = 프로젝트 `Saved` + `$HOME/Library/Application Support/Epic/UnrealEngine/5.8/Saved`), `:1982-1993` `sh_arg`([미확인] ②: 바깥 따옴표를 뗀 `-ExecCmds=…`가 한 argv로 간다, `LaunchMac.cpp`), `:1996-2066` `shell_script`. 지금까지의 확인은 가짜 편집기뿐이다: `tools/tests/test_ue_python_pure.py:1742-1790`(`_FAKE_EDITOR`, `test_shell_script_runs_against_a_fake_editor`), `tools/tests/test_ue_python_spike_runner.py:1268`(`test_game_scripts_written_on_mac`). C++: `Debug/GolmokDebugSubsystem.cpp:620`(경로 파일 = `ProjectSavedDir()/Golmok/Paths/<이름>.json`), `:882`(`path play '<이름>' (<길이> s, <n> samples) + CsvProfile`), `:899-901`(`CsvProfile Start (path '<이름>')`), `:904-936`(`csv:` 줄 — `ProfilingDir()/CSV`를 절대 경로로 찍는다), `:959-963`·`:1010`(경로 끝 `end of path`에서 `CsvProfile Stop`), `:1125`(`no debug subsystem` — pc-verify-wp06 §12 #17). `Lighting/GolmokTimeOfDay.cpp:1772`(`golmok.tod: <전> -> <프리셋> over <초> s`). 엔진(읽기, `/Users/Shared/Epic Games/UE_5.8/Engine/Source/Runtime/`, 5.8.4): `Launch/Private/Mac/LaunchMac.cpp:77-95`(argv를 다시 이어 붙일 때 공백이 있는 항목은 `이름="값"`으로 감싼다 — ②가 맞다면 로그의 `Command Line:`에 `-ExecCmds="…"`가 보인다), `:111-114`(` -installed`는 `UE_GAME`, 곧 패키지 게임에만 붙는다 — J-15의 컨테이너 결과가 에디터 바이너리에 그대로 옮겨지지 않는 이유), `Core/Private/Misc/Paths.cpp:548-551`(`ProfilingDir()` = `ProjectSavedDir()/Profiling/`), `:183-190`(`ShouldSaveToUserDir`), `Core/Private/ProfilingDebugging/CsvProfiler.cpp:4309-4312`(`-ExitAfterCsvProfiling`이면 캡처 끝에 `RequestExit(…, "CsvProfiler.ExitAfterCsvProfiling")`), `:4533`(`Capture Ended. Writing CSV to file : <경로>`), `Core/Private/Mac/MacPlatformMisc.cpp:714`(`FPlatformMisc::RequestExit(%i, %ls)`), `Core/Private/Misc/App.cpp:423`(`Command Line: `), `Core/Private/GenericPlatform/GenericPlatformOutputDevices.cpp:87`(`-ABSLOG=`). 엔진 플러그인 `Plugins/Experimental/PythonScriptPlugin/Source/PythonScriptPlugin/Private/PythonScriptPlugin.cpp:814-830`(콘솔 `py <경로>.py`는 그 파일을 실행한다). 합성 zone: `synthetic_zone.py:22`(zone 루트 UE (17670.59, -22198.00, 999.37) cm, yaw ~0), `:493-494`(PlayerStart = zone-local (0, −5) m → 루트 + (0, +500, 120) cm), `:80`(바닥 x ±22 m, y ±12 m), `Content/Golmok/Zones/z_synthetic_001/v1/manifest.json`(footprint 약 ±20 m × ±10 m), [zone-manifest.md](../spec/zone-manifest.md):22·:30(zone-local y = 북, UE Yaw = −yaw_deg). 런북: [mac-setup](../runbooks/mac-setup.md) §3 `-game` CSV 행(:139 — 에디터 바이너리 실행의 위치 [미확인, §8 #6·#13]), §8 #6(:292)·#13(:299 — 패키지 `.app`만 확인), J-15 "결과"(패키지는 샌드박스 컨테이너). [pc-verify-wp06.md](../runbooks/pc-verify-wp06.md) §12 #17(:554 — `-ExecCmds` 시점, `-ExitAfterCsvProfiling`이 콘솔 `CsvProfile Stop`에도 끝나는지), #39(:576 — 합성 zone 검사에서 인덱스 발견 끄기). 2026-11-28 Opus가 읽은 `$W` 상태: 브랜치 `local/jaehwan-j18-v17-uv`, `git status`는 `?? unreal/Golmok/Content/Golmok/Materials/` 한 줄(J-18 임포트 부산물), `Content/Golmok/Maps/L_ZoneTest.umap`과 `Content/Golmok/Zones/z_synthetic_001/v1/SM_chunk_00~02`·충돌 메시 있음, `Saved/Profiling` 없음, `Saved/Golmok/spike` 없음.
- **설계 (확정, Opus 2026-11-28)**: 재환은 아래를 그대로 옮긴다. 바꿀 점이 보이면 고치지 말고 묻는다.
  1. **경로 파일**: PIE `golmok.path record`는 GUI가 필요하므로 쓰지 않는다. 생성기 펜스 `j27-gen-py`가 `_pure.dwell_path_json`으로 `Saved/Golmok/Paths/j27_dwell.json`을 쓴다: 이름 `j27_dwell`, level `L_ZoneTest`(C++는 이 칸을 검사하지 않고, `golmok.path record`가 `GetMapName()`으로 쓰는 짧은 이름과 같은 꼴), 위치 `(17670.59, -21698.00, 1169.37)` cm = PlayerStart와 같은 zone-local (0, −5) m에 눈높이 1.7 m(루트 Z 999.37 + 170), 회전 `[roll, pitch, yaw]` = `(0, 0, -90)`(북쪽 파사드를 본다), `dwell_s=20.0`, `created="2026-11-28T00:00:00Z"`(고정 — 파일이 매번 같은 바이트). 이 점은 footprint 안(y −5 m, 경계 −10 m)이고 바닥 안이며 문 포털 `door_1`(zone-local (5, 9.5))에서 약 15 m 떨어져 있다. 파일 sha256은 펜스 `j27-dwell-sha256`(Opus가 같은 함수로 만든 값).
  2. **헤드리스 생성**: `-ExecCmds`는 쉼표로 명령을 나누므로 튜플을 줄에 넣을 수 없다. 생성기는 파일로 두고(`"$E/j27_gen.py"`, 펜스 추출) J-12b와 같은 꼴로 돌린다: `UnrealEditor-Cmd … "-ExecCmds=py $E/j27_gen.py,QUIT_EDITOR" -unattended -nullrhi -nosplash -nopause -nosound`. `-ExecutePythonScript`는 쓰지 않는다(WP-21 종료 크래시). 호출은 정확히 `game_scripts(paths=("j27_dwell",), tags=("a",), presets=("clear_noon",), res=(1920, 1080), base_level="/Game/Golmok/Maps/L_ZoneTest", timeout_s=600, discover_from_index=False)`. 태그 `a`만이라 `save_layer_levels`·`L_Spike_*`가 필요 없고, `discover_from_index=False`는 pc-verify-wp06 #39 때문이다(인덱스의 다른 합성 zone이 겹쳐 로드되지 않게). `timeout_s=600`은 첫 Metal `-game` 로드의 셰이더 컴파일 여유다(정상이면 20 s 경로 + 기동으로 끝난다).
  3. **생성된 스크립트 기대값**: 펜스 `j27-expected-sh`(Opus가 같은 생성기를 가짜 편집기 모듈에 돌린 출력에서 경로만 `@W@`·`@HOME@`로 바꾼 것)를 `sed`로 `$W`·`$HOME`에 채워 `diff`한다 — 0이어야 한다. 진단용 고정 `grep` 목록(펜스 `j27-expected-script-greps`): 첫 줄 `#!/bin/sh`, `golmok_run a_clear_noon_j27_dwell 600 ` 줄 1, 두 후보 폴더 `find` 줄 1, `'-ini:Game:[/Script/Golmok.GolmokZoneSubsystem]:bDiscoverFromIndex=False'` 1, `'-ExecCmds=golmok.hud 0, golmok.tod clear_noon, golmok.path play j27_dwell --csv'` 1, `echo 'golmok-perf ` 줄 1, 실행 비트 있음(`x=0`), `.ps1` 없음(`ps1=1`).
  4. **실행**: GUI 잠금을 잡는다(J-36과 같은 명령, `-game`은 GPU를 쓴다). 펜스 `j27-run-sh` 감싸개를 `/usr/bin/timeout 900`으로 돌린다. 감싸개는 생성된 스크립트를 백그라운드로 띄우고, 그 자식 `UnrealEditor` 프로세스를 `pgrep -P <스크립트 pid> -f UnrealEditor`로 찾아 **한 번** `ps -o pid=,ppid=,command=`와 펜스 `j27-argv-py`(macOS `sysctl` `KERN_PROCARGS2` — 프로세스가 받은 argv를 항목마다 한 줄)를 남긴다. `ps`는 argv를 공백으로 이어 보여 줄 뿐이라 "한 항목인가"를 가르지 못한다(Opus dry-run: 공백·쉼표가 든 인자 하나가 `ps`에서는 이어 붙고 `KERN_PROCARGS2`에서는 한 줄). [미확인] ②의 답은 argv 12번 줄(펜스 `j27-expected-argv`와 `diff`)과 게임 로그 `Command Line:`의 `-ExecCmds="…"`(LaunchMac.cpp:77-95가 다시 감싼 꼴) 두 가지다. ③의 답은 argv 0번 줄이다.
  5. **기대 증거**: 게임 로그(`-abslog` 사본) 고정 개수 — 펜스 `j27-logcheck-sh`의 출력이 펜스 `j27-expected-logcheck`와 같다(`Command Line:`의 `-ExecCmds="…"` 1, `golmok.tod: … -> clear_noon over ` 1, `golmok.path play: path play 'j27_dwell' (20.0 s, 2 samples) + CsvProfile` 1, `CsvProfile Start (path 'j27_dwell')` 1, `path play 'j27_dwell' finished (end of path) after ` 1, `Capture Ended. Writing CSV to file : ` 1, `FPlatformMisc::RequestExit(0, CsvProfiler.ExitAfterCsvProfiling)` 1, `GolmokDebugSubsystem: csv:` 1줄 이상, `no debug subsystem`·`golmok.path play: ERROR`·`golmok.tod: ERROR` 0). 스크립트 stderr의 `WARNING:` 줄은 0(분기 B는 아래). CSV는 첫 줄의 `FrameTime` 칸만 확인하고 프레임 수는 판정하지 않는다. `golmok-perf <csv> --label a_clear_noon_j27_dwell --markdown`은 rc 0과 3줄 표(머리 줄 고정). 넓은 `find`(프로젝트 `Saved`, `~/Library/Application Support/Epic` 전체, `~/Library/Containers/com.YourCompany.Golmok`, `-newer` 표식)를 같이 돌려 후보 밖의 CSV도 놓치지 않는다. 다른 앱의 컨테이너(`~/Library/Containers/*`)는 뒤지지 않는다: macOS가 "다른 앱의 데이터 접근" 권한 창을 띄울 수 있고, 그 권한은 소유자 몫이다(J-15가 Golmok 컨테이너 하나만 썼다).
  6. **미리 정한 분기**: 펜스 `j27-where-sh`가 정한다. **A**(`class candidate-1` 또는 `candidate-2`, `wide 1`, `wide-same yes`): 정상 — 그대로 끝까지. **B**(`script none`, `class outside`, `wide 1`): 스크립트가 CSV를 못 찾았고(`run.err`에 정확히 `WARNING: a_clear_noon_j27_dwell no CSV newer than the run start` 한 줄) 넓은 `find`가 후보 밖 1건을 찾음 — 그 파일을 `$E`에 복사해 `golmok-perf`를 돌리고, 행은 "부분" 꼴(펜스 `j27-row-sh`가 고른다)로 적고 PR까지 간다. **`_pure.py`는 고치지 않는다**(J-16이 Opus 리뷰 뒤 이 증거로 고친다). 그 밖(`class none`·`class other`, `wide` 0 또는 2 이상, `wide-same no`)은 멈춘다. 시간 초과(감싸개 rc 124, 또는 `run.err`의 `timeout after`)는 멈춘다. 로그의 `no debug subsystem`(pc-verify-wp06 #17)·`ERROR` 줄도 멈춘다.
  7. **결과 자리**: [mac-setup §8](../runbooks/mac-setup.md) 표에 새 행 **#27** 한 줄만 더한다(#26 바로 다음). 행 전체는 펜스 `j27-row-sh`가 로그에서 만든다 — 재환이 손으로 쓰는 값이 없다. §3 `-game` CSV 행·§8 #6·#13 칸에 "→ #27" 메모를 더하는 일과 [pc-spike.md](../runbooks/pc-spike.md) S12의 "Mac 명령(추가)" 블록은 이 과제에서 하지 않는다: 이 실행은 합성 정지 경로·태그 a 한 번이고 S12의 실제 절차(PIE 녹화 `walk_01`, 태그 a·b·c·ac, 1440p)는 돌리지 않으므로 런북 명령 블록에 넣으면 돌려 보지 않은 명령이 된다(규칙 1). 둘 다 병합 뒤 영록 몫(아래 "병합 시 반영"). S12의 Windows 글은 바꾸지 않는다(D-022: 추가만).
  8. **수치는 근거가 아니다**: PR 본문 `## 결과`에 "수치는 성능 근거가 아니다(같은 GPU·통합 메모리에서 LM Studio `qwen3.8-flash-next`가 돈다 — `lms ps` 출력)"를 그대로 쓴다. `golmok-perf` 표는 `## 실행한 명령`의 출력으로만 붙이고 `## 결과`에는 rc와 표 머리 줄만 적는다.
  9. **코드 변경 없음**: `_pure.py`·`spike_runner.py`·`Config/Default*.ini`(핫스팟)·`DefaultGame.ini`·C++·테스트는 열거나 고치지 않는다. 생성물은 모두 `$W/unreal/Golmok/Saved/` 아래(`.gitignore` 4행)이고, 스크립트의 복사 줄이 `~/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Golmok/Paths/j27_dwell.json`을 하나 더 만든다(저장소 밖, 지우지 않는다). 핫스팟 파일이 없으므로 훅 표시는 없다.
  10. **J-16과의 관계**: J-16(`_pure.py` Mac 경로 정리)은 이 과제 **뒤에** 한다. 에디터 바이너리 `-game`의 CSV 위치·`sh_arg`·`editor_exe`는 이 과제의 #27을 근거로 하고, J-15의 샌드박스 컨테이너 경로는 패키지 `.app`에만 쓴다(`LaunchMac.cpp:111-114`: ` -installed`는 패키지 게임에만). J-16 행 고치기는 영록 몫이다.

```python j27-gen-py
# J-27: writes the fixed dwell path and run_game_perf.sh inside a headless editor (UnrealEditor-Cmd -nullrhi).
import os

import unreal
from golmok import _pure
from golmok import spike_runner as sr

saved = sr._saved_dir()
path = os.path.join(saved, "Golmok", "Paths", "j27_dwell.json")
os.makedirs(os.path.dirname(path), exist_ok=True)
text = _pure.dwell_path_json(
    "j27_dwell",
    "L_ZoneTest",
    (17670.59, -21698.00, 1169.37),
    (0.0, 0.0, -90.0),
    dwell_s=20.0,
    created="2026-11-28T00:00:00Z",
)
with open(path, "w", encoding="utf-8", newline="\n") as f:
    f.write(text)
script = sr.game_scripts(
    paths=("j27_dwell",),
    tags=("a",),
    presets=("clear_noon",),
    res=(1920, 1080),
    base_level="/Game/Golmok/Maps/L_ZoneTest",
    timeout_s=600,
    discover_from_index=False,
)
unreal.log(f"j27_gen: done path={path} script={script}")
```

```python j27-argv-py
# J-27: prints the argv a running process received (macOS sysctl KERN_PROCARGS2), one entry per line.
import ctypes
import ctypes.util
import struct
import sys

libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
pid = int(sys.argv[1])
argmax = ctypes.c_int(0)
size = ctypes.c_size_t(ctypes.sizeof(argmax))
mib = (ctypes.c_int * 2)(1, 8)  # CTL_KERN, KERN_ARGMAX
if libc.sysctl(mib, 2, ctypes.byref(argmax), ctypes.byref(size), None, 0) != 0:
    sys.exit(f"sysctl KERN_ARGMAX errno {ctypes.get_errno()}")
buf = ctypes.create_string_buffer(argmax.value)
size = ctypes.c_size_t(argmax.value)
mib = (ctypes.c_int * 3)(1, 49, pid)  # CTL_KERN, KERN_PROCARGS2, pid
if libc.sysctl(mib, 3, buf, ctypes.byref(size), None, 0) != 0:
    sys.exit(f"sysctl KERN_PROCARGS2 errno {ctypes.get_errno()}")
raw = buf.raw[: size.value]
argc = struct.unpack_from("i", raw, 0)[0]
rest = raw[4:]
rest = rest[rest.index(b"\0") :].lstrip(b"\0")  # skip the executable path and its padding
args = rest.split(b"\0")[:argc]
print("argc", argc)
for i, a in enumerate(args):
    print(i, a.decode("utf-8", "replace"))
```

```sh j27-run-sh
#!/bin/sh
# J-27: runs run_game_perf.sh once, records the game process argv once (j27_argv.py) and the exit code.
# usage: sh j27_run.sh <W> <E>
W=$1
E=$2
"$W/unreal/Golmok/Saved/Golmok/spike/run_game_perf.sh" > "$E/run.out" 2> "$E/run.err" &
spid=$!
gpid=
i=0
while [ -z "$gpid" ] && [ "$i" -lt 300 ] && kill -0 "$spid" 2>/dev/null; do
  gpid=$(pgrep -P "$spid" -f 'UnrealEditor' | head -n 1)
  if [ -z "$gpid" ]; then
    sleep 1
    i=$((i + 1))
  fi
done
if [ -n "$gpid" ]; then
  echo "$gpid" > "$E/game-pid.log"
  ps -o pid=,ppid=,command= -p "$gpid" > "$E/game-ps.log" 2>&1
  python3 "$E/j27_argv.py" "$gpid" > "$E/game-argv.log" 2>&1
  echo $? > "$E/game-argv.rc"
else
  echo none > "$E/game-pid.log"
fi
wait "$spid"
echo $? > "$E/run.rc"
```

```sh j27-where-sh
#!/bin/sh
# J-27: where the CSV of this run was written, one fact per line (script line, class, wide find).
# usage: sh j27_where.sh <W> <E>
W=$1
E=$2
c1="$W/unreal/Golmok/Saved/Profiling/CSV"
c2="$HOME/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Profiling/CSV"
p=$(sed -n 's/^csv a_clear_noon_j27_dwell -> //p' "$E/run.out" | head -n 1)
n=$(grep -c . "$E/find-wide.log")
if [ -z "$p" ]; then
  echo "script none"
  if [ "$n" = 1 ]; then echo "class outside"; else echo "class none"; fi
else
  echo "script $p"
  d=$(dirname "$p")
  if [ "$d" = "$c1" ]; then
    echo "class candidate-1"
  elif [ "$d" = "$c2" ]; then
    echo "class candidate-2"
  else
    echo "class other"
  fi
fi
echo "wide $n"
if [ "$n" = 1 ] && { [ -z "$p" ] || [ "$(cat "$E/find-wide.log")" = "$p" ]; }; then
  echo "wide-same yes"
else
  echo "wide-same no"
fi
```

```sh j27-logcheck-sh
#!/bin/sh
# J-27: fixed line counts in the -game log copy (usage: sh j27_logcheck.sh <game log>), one "label count" per line.
G=$1
c() { printf '%s %s\n' "$1" "$2"; }
c cmdline-execcmds-quoted "$(grep -F 'Command Line: ' "$G" | grep -c -F -- '-ExecCmds="golmok.hud 0, golmok.tod clear_noon, golmok.path play j27_dwell --csv"')"
c tod-clear_noon "$(grep -c -E 'golmok\.tod: .* -> clear_noon over ' "$G")"
c path-play-csv "$(grep -c -F "golmok.path play: path play 'j27_dwell' (20.0 s, 2 samples) + CsvProfile" "$G")"
c csvprofile-start "$(grep -c -F "GolmokDebugSubsystem: CsvProfile Start (path 'j27_dwell')" "$G")"
c path-finished "$(grep -c -F "GolmokDebugSubsystem: path play 'j27_dwell' finished (end of path) after " "$G")"
c capture-ended "$(grep -c -F 'Capture Ended. Writing CSV to file : ' "$G")"
c exit-after-csv "$(grep -c -F 'FPlatformMisc::RequestExit(0, CsvProfiler.ExitAfterCsvProfiling)' "$G")"
if grep -q -F 'GolmokDebugSubsystem: csv:' "$G"; then c debug-csv-line yes; else c debug-csv-line no; fi
c no-debug-subsystem "$(grep -c -F 'no debug subsystem' "$G")"
c path-play-error "$(grep -c -F 'golmok.path play: ERROR' "$G")"
c tod-error "$(grep -c -F 'golmok.tod: ERROR' "$G")"
```

```sh j27-row-sh
#!/bin/sh
# J-27: prints the mac-setup section 8 row 27 from the J-27 logs (no hand-written values).
# usage: sh j27_row.sh <E>
E=$1
date=$(cat "$E/run-date.log")
sha=$(cat "$E/sha.log")
if [ "$(cat "$E/lms-ps.rc")" != 0 ]; then
  lms='`lms ps` 실패'
elif grep -q 'qwen3.8-flash-next' "$E/lms-ps.log"; then
  lms='로드됨(`lms ps`)'
else
  lms='`lms ps`에 없음'
fi
class=$(sed -n 's/^class //p' "$E/where.log")
wide=$(cat "$E/find-wide.log")
base=$(basename "$wide")
head='| 27 | 에디터 바이너리 `-game` CSV 실행 경로(V-05 S12 `run_game_perf.sh`) | `_pure.py`의 [미확인] 세 가지: CSV 후보 두 곳(프로젝트 `Saved/Profiling/CSV`, `~/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Profiling/CSV` — `MAC_USER_SETTINGS_REL`), `sh_arg`가 바깥 따옴표를 뗀 `-ExecCmds=…`가 한 argv로 가는지(`LaunchMac.cpp`), 에디터 실행 파일 `Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor`(`editor_exe`) | 합성 정지 경로(`L_ZoneTest`, 20 s)로 `game_scripts(...)`를 만들고 `run_game_perf.sh`를 1회 실행, 게임 프로세스 argv는 `sysctl` `KERN_PROCARGS2`로 읽는다(J-27) |'
cond="$date, J-27, 재환 worktree \`origin/main\` \`$sha\`, 에디터 바이너리 \`-game -RenderOffscreen\` 1회, 합성 정지 경로 20 s, \`discover_from_index=False\`, LM Studio \`qwen3.8-flash-next\` $lms"
argv='게임 프로세스 argv는 14개이고 0번은 `editor_exe` 경로 그대로, 12번은 `-ExecCmds=golmok.hud 0, golmok.tod clear_noon, golmok.path play j27_dwell --csv` 한 항목이었다. 게임은 경로 끝의 `CsvProfile Stop` 뒤 스스로 끝났다(`FPlatformMisc::RequestExit(0, CsvProfiler.ExitAfterCsvProfiling)`, pc-verify-wp06 §12 #17)'
tail='이 날짜·이 빌드의 에디터 바이너리 실행 1회 관찰이고, 다른 구성·조건의 위치는 [미확인]이다(패키지 `.app`은 #13). 수치는 성능 근거가 아니다(같은 GPU에서 LM Studio가 돈다). 근거: J-27 PR'
case "$class" in
  candidate-1) where='후보 1(프로젝트 `Saved/Profiling/CSV`)' ;;
  candidate-2) where='후보 2(`~/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Profiling/CSV`)' ;;
  outside) where='' ;;
  *) echo "j27_row: class '$class' has no row form" >&2; exit 3 ;;
esac
if [ "$class" = outside ]; then
  tilde=$(printf '%s\n' "$wide" | sed "s#^$HOME/#~/#")
  printf '%s 부분(%s): 스크립트의 두 후보에서는 CSV를 찾지 못했고(`WARNING: a_clear_noon_j27_dwell no CSV newer than the run start`), 넓은 `find`는 후보 밖에서 1건을 찾았다: `%s`. %s. 그 파일의 사본에 `golmok-perf … --markdown` rc 0. `_pure.py`는 고치지 않았다(J-16). %s |\n' "$head" "$cond" "$tilde" "$argv" "$tail"
else
  printf '%s 확인(%s): 스크립트 rc 0, `WARNING:` 줄 0. CSV는 %s에 쓰였다: `csv a_clear_noon_j27_dwell -> …/Profiling/CSV/%s`(넓은 `find` 1건, 같은 파일). %s. `golmok-perf … --markdown` rc 0. %s |\n' "$head" "$cond" "$where" "$base" "$argv" "$tail"
fi
```

```text j27-ph-awk
/^## / { sec = $0 }
/^(~~~|```)/ { blk = !blk; next }
{
  s = $0
  while (match(s, /<[^<>]+>/)) {
    tok = substr(s, RSTART, RLENGTH)
    if (blk && sec == "## 완료 기준 대조") cls = "원문 인용"
    else if (blk && sec == "## 실행한 명령") cls = "명령 기록"
    else cls = "미채움"
    print NR "\t" cls "\t" tok
    s = substr(s, RSTART + RLENGTH)
  }
}
```

```text j27-expected-sh
#!/bin/sh
# generated by golmok.spike_runner.game_scripts - do not edit
for d in '@HOME@/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Golmok/Paths'; do mkdir -p "$d" && cp -f @W@/unreal/Golmok/Saved/Golmok/Paths/j27_dwell.json "$d/"; done
mkdir -p @W@/unreal/Golmok/Saved/Golmok/spike/csv
golmok_run() {
  label=$1 timeout_s=$2 log=$3
  shift 3
  marker=$(mktemp "${TMPDIR:-/tmp}/golmok_run.XXXXXX") || return 1
  "$@" &
  pid=$!
  waited=0
  while kill -0 "$pid" 2>/dev/null; do
    if [ "$waited" -ge "$timeout_s" ]; then
      kill "$pid" 2>/dev/null; sleep 2; kill -9 "$pid" 2>/dev/null
      echo "WARNING: $label timeout after $timeout_s s" >&2
      break
    fi
    sleep 1
    waited=$((waited + 1))
  done
  wait "$pid" 2>/dev/null
  csv=$(find @W@/unreal/Golmok/Saved/Profiling/CSV '@HOME@/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Profiling/CSV' -maxdepth 1 -type f -name 'Profile*.csv' -newer "$marker" -exec ls -1t {} + 2>/dev/null | head -n 1)
  rm -f "$marker"
  if [ -n "$csv" ]; then
    cp -f "$csv" @W@/unreal/Golmok/Saved/Golmok/spike/csv/"$label.csv" && echo "csv $label -> $csv"
  else
    echo "WARNING: $label no CSV newer than the run start (see $log)" >&2
  fi
  if ! grep -q 'GolmokDebugSubsystem: csv:' "$log" 2>/dev/null; then
    echo "WARNING: $label log has no 'GolmokDebugSubsystem: csv:' line (ExecCmds timing? runbook #17)" >&2
  fi
}
golmok_run a_clear_noon_j27_dwell 600 @W@/unreal/Golmok/Saved/Golmok/spike/game_a_clear_noon_j27_dwell.log '/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor' @W@/unreal/Golmok/Golmok.uproject /Game/Golmok/Maps/L_ZoneTest -game -RenderOffscreen -ResX=1920 -ResY=1080 -ForceRes -ExitAfterCsvProfiling -unattended -nosplash '-ini:Game:[/Script/Golmok.GolmokZoneSubsystem]:bDiscoverFromIndex=False' '-ExecCmds=golmok.hud 0, golmok.tod clear_noon, golmok.path play j27_dwell --csv' -abslog=@W@/unreal/Golmok/Saved/Golmok/spike/game_a_clear_noon_j27_dwell.log
echo 'golmok-perf @W@/unreal/Golmok/Saved/Golmok/spike/csv/a_clear_noon_j27_dwell.csv --label a_clear_noon_j27_dwell --markdown'
```

```text j27-expected-argv
argc 14
0 /Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor
1 @W@/unreal/Golmok/Golmok.uproject
2 /Game/Golmok/Maps/L_ZoneTest
3 -game
4 -RenderOffscreen
5 -ResX=1920
6 -ResY=1080
7 -ForceRes
8 -ExitAfterCsvProfiling
9 -unattended
10 -nosplash
11 -ini:Game:[/Script/Golmok.GolmokZoneSubsystem]:bDiscoverFromIndex=False
12 -ExecCmds=golmok.hud 0, golmok.tod clear_noon, golmok.path play j27_dwell --csv
13 -abslog=@W@/unreal/Golmok/Saved/Golmok/spike/game_a_clear_noon_j27_dwell.log
```

```text j27-expected-logcheck
cmdline-execcmds-quoted 1
tod-clear_noon 1
path-play-csv 1
csvprofile-start 1
path-finished 1
capture-ended 1
exit-after-csv 1
debug-csv-line yes
no-debug-subsystem 0
path-play-error 0
tod-error 0
```

```text j27-expected-script-greps
#!/bin/sh
1
1
1
1
1
x=0
ps1=1
```

```text j27-dwell-sha256
54d729c400a45ef39a02d11a588778abd0b2be8b53b9f1012fee710915efb996
```

- **명령 공통**: 셸 변수는 Bash 호출 사이에 남지 않는다. 그래서 **모든 명령은 `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/jaehwan/J-27";`로 시작하고**, 그 뒤는 `cd "$W" &&`·`cd "$W/tools" &&`·`git -C "$W"`·`"$E/…"` 절대 경로로 시작한다(상시 규칙). 아래 명령에는 이 앞머리를 적지 않았다. 돌린 명령 원문은 `"$E/commands.txt"`에 한 줄씩 더한다(규칙 10). 각 단계의 "기대"와 다르면 **멈춤 조건**을 본다. 할 일 2(`build.sh`)·3(`UnrealEditor-Cmd`)·4(`j27_run.sh`와 넓은 `find`)의 명령과 할 일 7의 게이트·`gh pr checks --watch`는 **항상** 하네스의 백그라운드 실행으로 돌리고, 그 명령이 쓰는 `.rc` 파일(`gh pr checks --watch`는 `checks-watch.log`의 `exit=` 줄)이 생길 때까지 기다린다(명령은 바꾸지 않는다). 그 밖의 명령은 앞쪽(foreground)으로 돌린다.
  - **GUI 잠금**(할 일 2~4, [mac-setup §3](../runbooks/mac-setup.md) 표의 규칙, J-36과 같은 꼴): 확인 `L="$TMPDIR/claude/gui-foreground.lock"; if [ -e "$L" ]; then cat "$L"; else echo "no lock"; fi > "$E/lock-check.log"; date -u +%FT%TZ >> "$E/lock-check.log"` — 기대 첫 줄 `no lock`. 다른 줄이 있으면 **지우지 않고** 그 줄을 영록에게 보내고 기다린다. 잡기 `mkdir -p "$TMPDIR/claude" && (set -C; printf '%s %s %s\n' "재환" "J-27-game" "$(date -u +%FT%TZ)" > "$TMPDIR/claude/gui-foreground.lock"); echo $? > "$E/lock-take.rc"` — 기대 `0`. 풀기 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-27-game ' "$L" && rm "$L"; echo $? > "$E/lock-release.rc"` — 기대 `0`.
  - **잠금 갱신**([AGENTS.md](../../AGENTS.md) "UE를 같이 쓰는 규칙"·mac-setup §3: 20분이 지난 기록은 빈 것으로 보므로 잡은 쪽이 쓰는 동안 갱신한다): ① 할 일 2·3·4의 UE 명령 바로 앞에 매번 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-27-game ' "$L" && printf '%s %s %s\n' "재환" "J-27-game" "$(date -u +%FT%TZ)" > "$L"; echo $? > "$E/lock-refresh-<n>.rc"` — `<n>`은 할 일 2면 `build`, 3이면 `gen`, 4면 `run`. 기대 `0`. 0이 아니면(잠금 줄이 `재환 J-27-game`이 아니다) 잠금 파일을 지우거나 쓰지 않고 멈춘다. ② UE 명령 자체가 20분 넘게 걸려도 기록이 낡지 않도록, 할 일 2·3·4의 UE 명령은 갱신 루프로 감싸 **적힌 그대로** 돌린다: 앞머리 뒤에 `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-27-game ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-27-game" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!;`, 명령 끝에 `; kill "$RP"`. 루프는 4분마다 잠금 줄이 `재환 J-27-game`일 때만 시각을 고쳐 쓰고, 그 줄이 아니면(풀었거나 다른 세션 것) 쓰지 않고 끝난다. 할 일 2·3·4의 명령에는 이 루프가 이미 들어 있다.
- **할 일**:
  1. **준비**: `mkdir -p "$E" && git -C "$W" status --porcelain > "$E/status-before.log"; grep -c -v '^?? ' "$E/status-before.log" > "$E/status-before-tracked.log"` — 기대 `0`(추적 파일 변경이 있으면 멈춘다; `??` 줄은 그대로 둔다). `git -C "$W" fetch origin && git -C "$W" switch -c local/jaehwan-j27-game-perf origin/main > "$E/switch.log" 2>&1; echo $? > "$E/switch.rc"` — 기대 `0`. `git -C "$W" rev-parse --short HEAD > "$E/sha.log"; git -C "$W" rev-parse HEAD origin/main | uniq | wc -l | tr -d ' ' > "$E/sha-same.log"` — 기대 `1`. `cd "$W" && awk '/^#### J-27 /{f=1} /^#### J-28 /{f=0} f' docs/plan/jaehwan-tasks.md > "$E/task.txt"`(규칙 14) — 기대 `head -1 "$E/task.txt"`가 `#### J-27 `로 시작. 펜스 추출(손으로 옮기지 않는다): `` printf '%s\n' "j27-gen-py j27_gen.py" "j27-argv-py j27_argv.py" "j27-run-sh j27_run.sh" "j27-where-sh j27_where.sh" "j27-logcheck-sh j27_logcheck.sh" "j27-row-sh j27_row.sh" "j27-ph-awk j27_ph.awk" "j27-expected-sh expected-sh.in" "j27-expected-argv expected-argv.in" "j27-expected-logcheck expected-logcheck.txt" "j27-expected-script-greps expected-script-greps.txt" "j27-dwell-sha256 expected-dwell-sha256.txt" | while read -r n f; do awk -v n="$n" '$0 == "```" && x {x=0} x {print} $0 ~ ("^```[a-z]+ " n "$") {x=1}' "$E/task.txt" > "$E/$f"; done; cd "$E" && wc -l j27_gen.py j27_argv.py j27_run.sh j27_where.sh j27_logcheck.sh j27_row.sh j27_ph.awk expected-sh.in expected-argv.in expected-logcheck.txt expected-script-greps.txt expected-dwell-sha256.txt > "$E/extract-wc.log" ``(zsh는 따옴표 없는 변수를 낱말로 나누지 않으므로 `read -r n f`로 나눈다) — 기대(앞 숫자, 순서대로): `30`, `26`, `26`, `29`, `15`, `32`, `13`, `34`, `15`, `11`, `8`, `1`, 끝 줄 `240 total`. 채우기: `sed -e "s#@W@#$W#g" -e "s#@HOME@#$HOME#g" "$E/expected-sh.in" > "$E/expected-run_game_perf.sh"; sed -e "s#@W@#$W#g" "$E/expected-argv.in" > "$E/expected-argv.txt"`. 겹침: `cd "$W" && gh pr list --state open --json number,headRefName,files --jq '.[]|select(any(.files[]; .path=="docs/runbooks/mac-setup.md"))|"\(.number) \(.headRefName)"' > "$E/overlap.log" 2>&1` — 기대 빈 파일. 같은 프로젝트를 연 편집기가 없어야 한다: `pgrep -fl '[g]olmok-jaehwan/unreal/Golmok/Golmok.uproject' > "$E/editor-before.log"; echo $? > "$E/editor-before.rc"` — 기대 rc `1`(빈 파일). LM Studio 상태: `"$HOME/.lmstudio/bin/lms" ps > "$E/lms-ps.log" 2>&1; echo $? > "$E/lms-ps.rc"`(값은 판정하지 않고 기록만).
  2. **빌드 확인**: GUI 잠금 확인·잡기. 잠금 갱신 ①(`build`). 빌드(하네스 백그라운드): `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-27-game ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-27-game" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && /usr/bin/timeout 1800 ./tools/ue/build.sh > "$E/build.log" 2>&1; echo $? > "$E/build.rc"; kill "$RP"` — 기대 `build.rc` `0`.
  3. **생성(헤드리스)**: 잠금 갱신 ①(`gen`). 생성(하네스 백그라운드): `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-27-game ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-27-game" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && /usr/bin/timeout 900 "/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor-Cmd" "$W/unreal/Golmok/Golmok.uproject" "-ExecCmds=py $E/j27_gen.py,QUIT_EDITOR" -unattended -nullrhi -nosplash -nopause -nosound > "$E/gen.log" 2>&1; echo $? > "$E/gen.rc"; kill "$RP"; cp "$HOME/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log" "$E/gen-editor.log"` — 기대: `gen.rc` `0`, `grep -c -F "spike_runner: -game script -> $W/unreal/Golmok/Saved/Golmok/spike/run_game_perf.sh (1 runs)" "$E/gen-editor.log"` `1`, `grep -c -F "j27_gen: done path=$W/unreal/Golmok/Saved/Golmok/Paths/j27_dwell.json script=$W/unreal/Golmok/Saved/Golmok/spike/run_game_perf.sh" "$E/gen-editor.log"` `1`, `grep -c 'Traceback' "$E/gen-editor.log"` `0`. 경로 파일: `shasum -a 256 "$W/unreal/Golmok/Saved/Golmok/Paths/j27_dwell.json" | cut -d' ' -f1 | diff "$E/expected-dwell-sha256.txt" - > "$E/dwell-sha.diff"; echo "exit=$?" >> "$E/dwell-sha.diff"` — 기대 `exit=0` 한 줄. 스크립트: `diff "$E/expected-run_game_perf.sh" "$W/unreal/Golmok/Saved/Golmok/spike/run_game_perf.sh" > "$E/sh-diff.log"; echo "exit=$?" >> "$E/sh-diff.log"` — 기대 `exit=0` 한 줄. 진단 목록: `P="$W/unreal/Golmok/Saved/Golmok/spike/run_game_perf.sh"; { head -n 1 "$P"; grep -c '^golmok_run a_clear_noon_j27_dwell 600 ' "$P"; grep -c -F "find $W/unreal/Golmok/Saved/Profiling/CSV '$HOME/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Profiling/CSV' -maxdepth 1 " "$P"; grep -c -F "'-ini:Game:[/Script/Golmok.GolmokZoneSubsystem]:bDiscoverFromIndex=False'" "$P"; grep -c -F "'-ExecCmds=golmok.hud 0, golmok.tod clear_noon, golmok.path play j27_dwell --csv'" "$P"; grep -c "^echo 'golmok-perf " "$P"; test -x "$P"; echo "x=$?"; test -e "${P%.sh}.ps1"; echo "ps1=$?"; } > "$E/script-greps.log"; diff "$E/expected-script-greps.txt" "$E/script-greps.log" > "$E/script-greps.diff"; echo "exit=$?" >> "$E/script-greps.diff"` — 기대 `exit=0` 한 줄.
  4. **실행**: 잠금 갱신 ①(`run`). 실행(하네스 백그라운드): `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-27-game ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-27-game" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && touch "$E/marker" && date +%F > "$E/run-date.log" && /usr/bin/timeout 900 /bin/sh "$E/j27_run.sh" "$W" "$E" > "$E/wrapper.log" 2>&1; echo $? > "$E/wrapper.rc"; kill "$RP"`(`run-date.log`는 행의 날짜 — 다른 행처럼 Mac의 현지 날짜) — 기대: `wrapper.rc` `0`, `run.rc` `0`, `game-pid.log`가 숫자 한 줄(`none`이 아님), `game-argv.rc` `0`. argv: `diff "$E/expected-argv.txt" "$E/game-argv.log" > "$E/argv.diff"; echo "exit=$?" >> "$E/argv.diff"` — 기대 `exit=0` 한 줄. 남은 프로세스: `pgrep -fl '[g]olmok-jaehwan/unreal/Golmok/Golmok.uproject' > "$E/editor-after.log"; echo $? > "$E/editor-after.rc"` — 기대 rc `1`. 게임 로그: `cp "$W/unreal/Golmok/Saved/Golmok/spike/game_a_clear_noon_j27_dwell.log" "$E/game.log"; echo $? > "$E/game-cp.rc"` — 기대 `0`. `sh "$E/j27_logcheck.sh" "$E/game.log" > "$E/logcheck.log"; diff "$E/expected-logcheck.txt" "$E/logcheck.log" > "$E/logcheck.diff"; echo "exit=$?" >> "$E/logcheck.diff"` — 기대 `exit=0` 한 줄. `grep -c '^WARNING: ' "$E/run.err" > "$E/run-warn.log"; grep -c 'timeout after' "$E/run.err" > "$E/run-timeout.log"` — 기대 `run-timeout.log` `0`, `run-warn.log`는 분기 A면 `0`, 분기 B면 `1`(아래 할 일 5에서 정한다). 그다음 넓은 `find`: `/usr/bin/timeout 300 find "$W/unreal/Golmok/Saved" "$HOME/Library/Application Support/Epic" "$HOME/Library/Containers/com.YourCompany.Golmok" -type f -name 'Profile*.csv' -newer "$E/marker" > "$E/find-wide.log" 2> "$E/find-wide.err"; echo $? > "$E/find-wide.rc"`(rc와 `find-wide.err`는 기록만). 이 줄에서 시스템 권한 창이 뜨면 누르지 않는다(멈춤 조건). 잠금 풀기.
  5. **CSV 위치와 `golmok-perf`**: `sh "$E/j27_where.sh" "$W" "$E" > "$E/where.log"` — 기대(분기 A): 둘째 줄 `class candidate-1` 또는 `class candidate-2`, 셋째 줄 `wide 1`, 넷째 줄 `wide-same yes`. 분기 B: `script none`, `class outside`, `wide 1`, `wide-same yes`이고 `grep -c -F 'WARNING: a_clear_noon_j27_dwell no CSV newer than the run start' "$E/run.err"` `1`. 다른 값은 멈춘다. 사본: 분기 A `cp "$W/unreal/Golmok/Saved/Golmok/spike/csv/a_clear_noon_j27_dwell.csv" "$E/a_clear_noon_j27_dwell.csv"; cmp "$(cat "$E/find-wide.log")" "$E/a_clear_noon_j27_dwell.csv"; echo $? > "$E/csv-cmp.rc"` — 기대 `0`. 분기 B `cp "$(cat "$E/find-wide.log")" "$E/a_clear_noon_j27_dwell.csv"; echo $? > "$E/csv-cmp.rc"` — 기대 `0`. 머리 줄: `head -n 1 "$E/a_clear_noon_j27_dwell.csv" | tr ',' '\n' | tr -d ' \r' | grep -c -x 'FrameTime' > "$E/csv-header.log"` — 기대 `1`. 줄 수는 기록만: `wc -l < "$E/a_clear_noon_j27_dwell.csv" | tr -d ' ' > "$E/csv-lines.log"`(판정하지 않는다). 사용자 폴더 복사본: `shasum -a 256 "$HOME/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Golmok/Paths/j27_dwell.json" | cut -d' ' -f1 | diff "$E/expected-dwell-sha256.txt" - > "$E/user-copy.diff"; echo "exit=$?" >> "$E/user-copy.diff"` — 기대 `exit=0` 한 줄. `golmok-perf`: 분기 A는 스크립트가 찍은 줄 그대로 `cd "$W/tools" && source .venv/bin/activate && golmok-perf "$W/unreal/Golmok/Saved/Golmok/spike/csv/a_clear_noon_j27_dwell.csv" --label a_clear_noon_j27_dwell --markdown > "$E/perf.md" 2>&1; echo $? > "$E/perf.rc"`(먼저 `grep -c -x -F "golmok-perf $W/unreal/Golmok/Saved/Golmok/spike/csv/a_clear_noon_j27_dwell.csv --label a_clear_noon_j27_dwell --markdown" "$E/run.out"`이 `1`인지 본다), 분기 B는 같은 명령에서 CSV 경로만 `"$E/a_clear_noon_j27_dwell.csv"`. 기대: `perf.rc` `0`, `wc -l < "$E/perf.md" | tr -d ' '` `3`, `head -n 1 "$E/perf.md"`가 `| 구성 | 프레임 | 평균 fps | 1% low fps | 프레임 p50 ms | p99 ms | Game ms | Render ms | GPU ms |`, `grep -c '^| a_clear_noon_j27_dwell | ' "$E/perf.md"` `1`. 표의 숫자는 판정하지 않는다(설계 8).
  6. **런북 한 줄**: `sh "$E/j27_row.sh" "$E" > "$E/row27.txt"; echo $? > "$E/row.rc"` — 기대 rc `0`, `wc -l < "$E/row27.txt" | tr -d ' '` `1`. 그 한 줄을 손으로 옮기지 않고 명령으로 `docs/runbooks/mac-setup.md` §8 표에서 `| 26 | Object Capture 상한(M5 Max) | 미정 |`으로 시작하는 줄(2026-11-28 :312, 끝 칸이 빈 행) **바로 다음 줄**로 넣는다: `cd "$W" && sed -i '' "/^| 26 | Object Capture 상한(M5 Max) | 미정 |/r $E/row27.txt" docs/runbooks/mac-setup.md; echo $? > "$E/row-insert.rc"` — 기대 `0`. 이 명령은 한 번만 돌린다(두 번 돌리면 행이 두 줄 들어가 아래 `grep -c`가 `2`가 된다 — 멈춤). 확인: `cd "$W" && awk '/^\| 26 \| /{getline n; print n}' docs/runbooks/mac-setup.md | diff - "$E/row27.txt" > "$E/row-diff.log"; echo "exit=$?" >> "$E/row-diff.log"` — 기대 `exit=0` 한 줄. `cd "$W" && grep -c '^| 27 | ' docs/runbooks/mac-setup.md` `1`. `cd "$W" && git diff --numstat -- docs/runbooks/mac-setup.md` `1	0	docs/runbooks/mac-setup.md`. `git -C "$W" status --porcelain > "$E/status-after.log"; grep -v -x -F ' M docs/runbooks/mac-setup.md' "$E/status-after.log" | diff "$E/status-before.log" - > "$E/status.diff"; echo "exit=$?" >> "$E/status.diff"` — 기대 `exit=0` 한 줄(UE 실행이 저장소에 남긴 것이 없다).
  7. **게이트·커밋·push**: `cd "$W/tools" && source .venv/bin/activate && { /usr/bin/timeout 300 ruff check . && /usr/bin/timeout 300 ruff format --check . && /usr/bin/timeout 1800 pytest -q && /usr/bin/timeout 300 python scripts/check_repo.py; } > "$E/gate.log" 2>&1; echo $? > "$E/gate.rc"`(하네스 백그라운드) — 기대 `0`(rc 124 = 시간 초과, 다시 돌리지 않고 멈춤). 커밋: `cd "$W" && git add docs/runbooks/mac-setup.md && git diff --cached --name-only > "$E/c1-files.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-27: mac-setup §8 #27 — 에디터 바이너리 -game CSV 실행 경로(run_game_perf.sh 1회 관찰)" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c1-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author.log"` — 기대: `c1-files.log` 한 줄 `docs/runbooks/mac-setup.md`, `author.log` `재환 <jaehwan.local@localhost>`. 게이트 로그가 런북보다 새것인지: `[ "$E/gate.log" -nt "$W/docs/runbooks/mac-setup.md" ]; echo "newer=$?" > "$E/mtime.log"` — 기대 `newer=0`. `git -C "$W" push -u origin local/jaehwan-j27-game-perf > "$E/push.log" 2>&1; echo "exit=$?" >> "$E/push.log"` — 기대 끝 줄 `exit=0`. 브랜치 파일: `git -C "$W" diff --name-only origin/main...HEAD > "$E/branch-files.log"` — 기대 한 줄 `docs/runbooks/mac-setup.md`. push 뒤 상태: `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-final.diff"; echo "exit=$?" >> "$E/status-final.diff"` — 기대 `exit=0` 한 줄. PR 열기(첫 본문은 CI 자리 한 줄뿐 — 규칙 2a): `printf '%s\n' '## 요약' '' 'V-05 S12 run_game_perf.sh Mac 첫 실행(도구 경로, 성능 아님). 본문은 CI 뒤에 채운다.' '' '## CI' '' 'CI 진행 중 — 결과는 아래에 추가' > "$E/pr-body-initial.md"; cd "$W" && gh pr create --base main --head local/jaehwan-j27-game-perf --title "J-27: V-05 S12 run_game_perf.sh Mac 첫 실행 — 도구 경로(성능 아님)" --body-file "$E/pr-body-initial.md" > "$E/pr-create.log" 2>&1; echo $? > "$E/pr-create.rc"` — 기대 `0`. PR 번호: `cd "$W" && gh pr view local/jaehwan-j27-game-perf --json number --jq .number > "$E/pr-number.log" 2> "$E/pr-number.err"` — 기대 숫자 한 줄(`grep -c -x '[0-9][0-9]*' "$E/pr-number.log"` `1`, `wc -l < "$E/pr-number.log" | tr -d ' '` `1`; `gh`가 stderr에 찍는 안내 문구는 `pr-number.err`로 가고 판정하지 않는다). 아래 명령은 이 파일에서 번호를 읽는다. CI(하네스 백그라운드): `cd "$W" && /usr/bin/timeout 1800 gh pr checks "$(cat "$E/pr-number.log")" --watch --interval 30 > "$E/checks-watch.log" 2>&1; echo "exit=$?" >> "$E/checks-watch.log"; gh pr checks "$(cat "$E/pr-number.log")" > "$E/checks.log" 2>&1` — 기대 모든 행 pass.
  8. **PR 본문**: 절 순서 = 요약 · 바뀐 파일 · **`## 결과`**(관찰한 값만: 분기 A/B, `where.log` 네 줄, argv 0번·12번 줄, `logcheck.log`, `golmok-perf` rc와 표 머리 줄, 설계 8의 문장 원문, `lms-ps.log`의 모델 줄 원문 — 과제 번호·규칙 번호·날짜는 이 절에 쓰지 않는다) · **`## 완료 기준 대조`**(규칙 14: `$E/task.txt`의 "완료 기준" 부분을 물결 펜스 `~~~` 코드 블록에 그대로 붙이고, 아래에 (a)~(i) 한 줄씩 충족 + 증거 파일 또는 **미충족** + 이유) · **`## 실행한 명령`**(`$E/commands.txt`와 `perf.md`를 백틱 펜스 블록에 그대로) · 남은 `[미확인]` · 병합 시 반영 · 제출 전 점검표(규칙 1~16 한 줄씩, 과거형과 결과) · 서명. 본문 초안은 `$E/pr-body.md`. 게시 전 검사(규칙 10 e·f) — **대상 로그는 이 목록으로 고정한다**(본문 초안·게시본·`task.txt`·`commands.txt`·검사 로그 자신은 넣지 않는다): `"$E"/gen-editor.log "$E"/sh-diff.log "$E"/script-greps.log "$E"/game-argv.log "$E"/logcheck.log "$E"/run.out "$E"/run.err "$E"/where.log "$E"/find-wide.log "$E"/csv-header.log "$E"/perf.md "$E"/lms-ps.log "$E"/sha.log "$E"/run-date.log "$E"/row27.txt "$E"/gate.log "$E"/checks.log`.
     - 인용 검사: `## 결과` 절의 백틱 문자열마다 그 문자열이 근거로 든 로그 **한 개**를 `"$E/quotes.tsv"`에 `<문자열><탭><위 목록의 파일 이름>`으로 적는다(로그 인용이 아닌 파일 이름·명령은 파일 칸에 `라벨`). 설계 8의 문장 안 두 백틱 문자열은 정해져 있다: `qwen3.8-flash-next`의 파일 칸은 `lms-ps.log`, `lms ps`의 파일 칸은 `라벨`. 설계 8의 문장은 원문 그대로 두어야 하므로, `qwen3.8-flash-next`의 세기가 0이면(모델이 `lms ps` 출력에 없거나 `lms`가 실패) 문장을 고치거나 지우지 않고 멈춘다. 빠진 것 확인: `` awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '`[^`]+`' | sed 's/^`//;s/`$//' | sort -u > "$E/body-quotes.txt"; cut -f1 "$E/quotes.tsv" | sort -u > "$E/tsv-quotes.txt"; comm -23 "$E/body-quotes.txt" "$E/tsv-quotes.txt" > "$E/quotes-missing.log" `` — 기대 빈 파일. 세기: `while IFS="$(printf '\t')" read -r q f; do if [ "$f" = "라벨" ]; then n="라벨"; else n=$(grep -F -c -- "$q" "$E/$f"); fi; printf '%s\t%s\t%s\n' "$n" "$f" "$q"; done < "$E/quotes.tsv" > "$E/quotes-check.log"` — 기대: `cut -f1 "$E/quotes-check.log" | grep -c -x '0'`가 `0`.
     - 숫자 검사: `awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '[0-9]{2,}' | sort -u > "$E/body-numbers.txt"; while read -r x; do printf '%s\t%s\n' "$(cat "$E"/gen-editor.log "$E"/sh-diff.log "$E"/script-greps.log "$E"/game-argv.log "$E"/logcheck.log "$E"/run.out "$E"/run.err "$E"/where.log "$E"/find-wide.log "$E"/csv-header.log "$E"/perf.md "$E"/lms-ps.log "$E"/sha.log "$E"/run-date.log "$E"/row27.txt "$E"/gate.log "$E"/checks.log | grep -c -- "$x")" "$x"; done < "$E/body-numbers.txt" > "$E/numbers-check.log"` — 기대: `cut -f1 "$E/numbers-check.log" | grep -c -x '0'`가 `0`.
     - 0이 나온 것은 고치거나 지운다(설계 8의 문장은 위대로). 그다음 게시: `cd "$W" && gh pr edit "$(cat "$E/pr-number.log")" --body-file "$E/pr-body.md" > "$E/pr-edit.log" 2>&1; echo $? > "$E/pr-edit.rc"` — 기대 `0`.
     - 자리표시 분류(규칙 12): 게시 뒤 `cd "$W" && gh pr view "$(cat "$E/pr-number.log")" --json body --jq .body > "$E/pr-body-posted.md"; awk -f "$E/j27_ph.awk" "$E/pr-body-posted.md" > "$E/placeholder.tsv"; cut -f2 "$E/placeholder.tsv" | sort | uniq -c > "$E/placeholder-count.log"; awk -F'\t' '$2=="미채움"' "$E/placeholder.tsv" | wc -l | tr -d ' ' > "$E/placeholder-unfilled.log"`. 과제 글과 명령에는 `<n>` 같은 자리표시가 원래 들어 있으므로 "찾은 것 없음"이 아니라 **분류**로 판정한다: `## 완료 기준 대조`의 `~~~` 블록 안 = 원문 인용, `## 실행한 명령`의 펜스 블록 안 = 명령 기록, 그 밖 = 미채움. 기대: `placeholder-unfilled.log` `0`. `placeholder-count.log`를 `$E/pr-body.md` 끝에 표(분류 · 개수)로 붙인다.
     - 마지막 게시: 위 게시 명령(`pr-edit.log`·`pr-edit.rc`)을 한 번 더 돌리고(기대 `0`), 위 자리표시 분류 명령을 한 번 더 돌려 다시 읽는다(규칙 12) — 기대 `placeholder-unfilled.log` `0`, `pr-body-posted.md` 끝에 그 표가 있다.
- **허용 파일**: `docs/runbooks/mac-setup.md`(§8 표 #26 다음에 #27 한 줄 추가만, 펜스 `j27-row-sh`의 출력 그대로). 그 밖의 저장소 파일은 고치지 않는다: `_pure.py`·`spike_runner.py`·C++·테스트·`tools/ue/*.sh`·`Config/Default*.ini`(핫스팟)·`DefaultGame.ini`·[pc-spike.md](../runbooks/pc-spike.md)·§3 표·§8 다른 행·공유 문서. 생성물(`Saved/`)과 J-18의 `??` 파일은 커밋하지 않는다.
- **멈춤 조건(정하지 말고 영록에게 묻는다)**: `status-before-tracked.log`가 0이 아닐 때. `switch.rc`가 0이 아니거나 `sha-same.log`가 1이 아닐 때. `head -1 "$E/task.txt"`가 `#### J-27 `로 시작하지 않을 때. `extract-wc.log`가 기대와 다를 때. `overlap.log`가 비어 있지 않을 때. `editor-before.rc`가 1이 아닐 때(같은 프로젝트 편집기가 떠 있다 — 끄지 않는다). 잠금 파일에 다른 기록이 있거나 잠금 잡기 rc가 0이 아닐 때. `lock-refresh-build.rc`·`lock-refresh-gen.rc`·`lock-refresh-run.rc` 중 하나가 0이 아닐 때(잠금 줄이 `재환 J-27-game`이 아니다 — 잠금 파일을 지우거나 쓰지 않는다). `build.rc`·`gen.rc`가 0이 아닐 때, `gen-editor.log`의 `grep -c` 값이 기대와 다를 때(`Traceback` 포함). `dwell-sha.diff`·`sh-diff.log`·`script-greps.diff`·`argv.diff`·`logcheck.diff`·`user-copy.diff`·`row-diff.log`·`status.diff`가 `exit=0` 한 줄이 아닐 때. `wrapper.rc`가 0이 아닐 때(124 = 시간 초과, 규칙 5), `run.rc`가 0이 아니거나 `run-timeout.log`가 0이 아닐 때, `game-pid.log`가 `none`이거나 `game-argv.rc`가 0이 아닐 때. `editor-after.rc`가 1이 아닐 때(아래 "멈춤 순서" ①②로 처리한다). `logcheck.log`의 `no-debug-subsystem`·`path-play-error`·`tod-error`가 0이 아닐 때(pc-verify-wp06 #17 — 원인을 고치지 않는다). `where.log`가 할 일 5의 분기 A·B 어느 쪽도 아닐 때, `run-warn.log`가 분기의 기대와 다를 때. `csv-cmp.rc`·`csv-header.log`·`perf.rc`·`perf.md` 확인값이 기대와 다를 때. 넓은 `find`나 다른 명령에서 macOS 권한 창이 뜰 때(누르지 않는다 — 소유자 항목). `row.rc`·`row-insert.rc`가 0이 아닐 때. `gate.rc`가 0이 아닐 때(rc 124 포함, 다른 파일을 고치거나 `ruff format`으로 바꾸지 않는다). `c1-files.log`·`author.log`가 기대와 다를 때. `mtime.log`가 `newer=0`이 아닐 때. `lock-release.rc`가 0이 아닐 때(잠금 파일을 지우지 않는다). `push.log`가 `exit=0`이 아닐 때, `branch-files.log`가 `docs/runbooks/mac-setup.md` 한 줄이 아니거나 `status-final.diff`가 `exit=0` 한 줄이 아닐 때. `pr-create.rc`·`pr-edit.rc`가 0이 아니거나 `pr-number.log`가 숫자 한 줄이 아닐 때. `checks.log`에 pass가 아닌 행이 있을 때. `quotes-check.log`에서 `qwen3.8-flash-next`의 세기가 0일 때(할 일 8). 그 밖에 이 절의 "기대"와 다른 값이 하나라도 나올 때. **`_pure.py`나 다른 코드의 결함으로 보이는 것을 고치지 않는다**(J-16 또는 Claude 레인 — 재현 절차만 보고). **멈춤 순서 — 할 일 2~4 안에서 멈출 때는 이 순서로 한다**: ① `pgrep -fl '[g]olmok-jaehwan/unreal/Golmok/Golmok.uproject' > "$E/editor-stop.log"; echo $? > "$E/editor-stop.rc"`. ② rc가 `1`이면 ③으로 간다. rc가 `0`이고 남은 pid가 `game-pid.log`의 pid 하나뿐이면 `kill <그 pid>`만 하고(자기가 띄운 프로세스, `sleep`하지 않는다) ①을 한 번 더 돌린다 — 이번 rc가 `1`이면 ③으로, 아니면 잠금을 풀지 않은 채 `editor-stop.log`를 영록에게 보낸다. 그 밖의 pid(`game-pid.log`에 없는 pid — 할 일 3의 `UnrealEditor-Cmd` 포함)는 건드리지 않고, 잠금을 풀지 않은 채 `editor-stop.log`를 영록에게 보낸다. ③ 그다음에만 잠금 풀기를 돌려 `lock-release.rc`를 남기고 묻는다.
- **완료 기준**:
  - (a) 준비: `status-before-tracked.log` `0`, `switch.rc` `0`, `sha-same.log` `1`, `task.txt` 첫 줄 `#### J-27 `, `extract-wc.log` 원문(기대 숫자와 같다), `overlap.log` 빈 파일, `editor-before.rc` `1`, `lms-ps.rc`와 `lms-ps.log` 원문.
  - (b) 생성: `build.rc` `0`, `gen.rc` `0`, `gen-editor.log`의 세 `grep -c`(`1`·`1`·`0`), `dwell-sha.diff`·`sh-diff.log`·`script-greps.diff` 모두 `exit=0` 한 줄.
  - (c) 실행: `lock-refresh-build.rc`·`lock-refresh-gen.rc`·`lock-refresh-run.rc` 모두 `0`, `wrapper.rc` `0`, `run.rc` `0`, `run-timeout.log` `0`, `game-pid.log` 숫자, `game-argv.rc` `0`, `argv.diff` `exit=0`, `game-cp.rc` `0`, `logcheck.diff` `exit=0`, `editor-after.rc` `1`, `lock-release.rc` `0`.
  - (d) CSV 위치: `where.log` 네 줄 원문이 분기 A 또는 B의 기대와 같고, `run-warn.log`가 그 분기의 값(A `0`, B `1`). `find-wide.log` 원문 한 줄, `find-wide.rc`·`find-wide.err` 원문. `csv-cmp.rc` `0`, `csv-header.log` `1`, `user-copy.diff` `exit=0`. `csv-lines.log`는 기록만.
  - (e) `golmok-perf`: `perf.rc` `0`, `perf.md` 3줄, 첫 줄이 할 일 5의 머리 줄, `^| a_clear_noon_j27_dwell | ` 1줄. 분기 A면 `run.out`의 `golmok-perf` 줄 `grep -c -x -F` `1`.
  - (f) 런북: `row.rc` `0`, `row27.txt` 1줄, `row-insert.rc` `0`, `row-diff.log` `exit=0`, `grep -c '^| 27 | '` `1`, numstat `1	0	docs/runbooks/mac-setup.md`, `status.diff` `exit=0`.
  - (g) 커밋: `branch-files.log` `docs/runbooks/mac-setup.md` 한 줄, `c1-files.log` 같은 한 줄, `author.log` `재환 <jaehwan.local@localhost>`, `push.log` 끝 줄 `exit=0`, `status-final.diff` `exit=0` 한 줄. `pr-create.rc` `0`, `pr-number.log` 숫자 한 줄.
  - (h) 게이트 `gate.rc` `0`, `mtime.log` `newer=0`. CI `checks.log` 모든 행 pass 원문(규칙 2).
  - (i) PR 본문: 절 순서(할 일 8), `## 결과`에 설계 8의 문장과 `lms-ps.log` 모델 줄 원문, "완료 기준 대조" 절, 점검표 1~16. `quotes-missing.log` 빈 파일, `quotes-check.log`·`numbers-check.log`에 0 없음. 자리표시 분류: `placeholder.tsv`의 모든 줄이 원문 인용 / 명령 기록 / 미채움 중 하나로 분류되고 `placeholder-unfilled.log` `0`, `placeholder-count.log` 표가 본문 끝에 있다. `pr-edit.rc` `0`(두 번 모두), 마지막 게시 뒤 다시 읽은 `pr-body-posted.md`(규칙 12).
- **병합 시 반영(영록)**: STATUS 재환 절에 J-27 행. mac-setup §8 #27 끝의 "근거: J-27 PR"을 "근거: PR #<n>"으로. §3 `-game` CSV 행(:139)과 §8 #6·#13 칸 끝에 날짜를 단 "에디터 바이너리 `-game` 실행은 §8 #27" 메모(규칙 16 — 있는 글은 지우지 않는다). pc-verify-wp06 §12 #17 결과 칸에 "Mac 에디터 바이너리 `-game`에서 `-ExitAfterCsvProfiling`이 콘솔 `CsvProfile Stop` 뒤 종료(§8 #27)" 메모. J-16 행: 선행에 J-27을 더하고, 에디터 바이너리 경로(`MAC_USER_SETTINGS_REL`·`sh_arg`·`editor_exe`)는 #27을, 샌드박스 컨테이너는 패키지 `.app`(#12·#13)만을 근거로 한다고 좁힌다. pc-spike S12 "Mac 명령(추가)" 블록은 V-05 실제 실행(PIE `walk_01`, 태그 4개)에서 돌린 명령으로 영록(Opus)이 쓴다. 분기 B였다면 `_pure.py` 수정은 J-16에서(Opus 리뷰 뒤).
- **왜 재환 / 위험**: 모든 판정이 고정 기대값과의 `diff`·`grep -c`·종료 코드로 끝나고, 생성기·감싸개·행 문구가 펜스로 정해져 있다. 코드도 Astra 레인도 건드리지 않는다. 위험: ① GPU·GUI 경합 — `-game -RenderOffscreen`은 영록의 성능 측정·LM Studio와 GPU를 나눈다. 잠금을 잡고, 수치는 어떤 판정에도 쓰지 않는다(D-020, 상시 규칙 "GPU·GUI 공유"). ② 게임이 스스로 끝나지 않음(경로 재생이 `CsvProfile Stop`을 못 부르면 `-ExitAfterCsvProfiling`이 안 걸린다) — 스크립트 안 600 s kill과 바깥 `timeout 900`이 끝내고, 그 경우는 멈춤(설계 6). ③ `-ExecCmds`의 쉼표·따옴표 — 생성기는 파일로 돌리고, 게임 명령 줄은 생성기가 만든 그대로이며 Opus가 같은 생성기와 감싸개를 가짜 편집기로 dry-run했다. ④ 합성 zone이 그 자리에 안 뜨거나 다른 합성 zone이 겹침 — 위치는 PlayerStart와 같은 zone-local 점(footprint 안), `discover_from_index=False`. 이 과제는 zone이 보였는지 판정하지 않는다(룩 판정 아님). ⑤ 규칙 1·3·15 함정 — 관찰한 CSV 폴더 하나를 "Mac은 늘 여기에 쓴다"로 넓히는 것. 행 문구는 펜스가 "이 날짜·이 빌드의 에디터 바이너리 실행 1회 관찰"로 좁혀 두었다. 패키지 `.app`의 컨테이너 결과(#13)와 섞지 않는다. ⑥ J-16이 컨테이너 경로로 에디터 후보를 "고치는" 것 — 설계 10·병합 시 반영으로 순서와 근거를 나눈다. ⑦ `$W`의 J-18 작업물(`??` 파일·`L_ZoneTest06`)은 그대로 둔다 — 할 일 1·6의 `status` 비교가 확인한다.
- **dry-run 범위(Opus 2026-11-28)**: `origin/main` `8ba637c`의 scratch 사본에서 한 것: 펜스 `j27-gen-py`를 `tools/tests/fake_unreal.py`의 가짜 `unreal` 모듈(플랫폼 darwin, 가짜 `$HOME`, 엔진 폴더를 공백 든 가짜 `…/Epic Games/UE_5.8/Engine`으로)에 돌려 `spike_runner: -game script -> …/run_game_perf.sh (1 runs)`와 `j27_gen: done …` 로그, 실행 비트 있는 `run_game_perf.sh`(34줄)와 `j27_dwell.json`(sha256 = 펜스 `j27-dwell-sha256`, 282바이트)을 얻었고, 그 스크립트에서 경로만 바꾼 것이 펜스 `j27-expected-sh`다(되돌려 채운 것과 `diff` 0). 진단 `grep` 목록은 펜스 `j27-expected-script-greps`와 같았다. 같은 스크립트를 가짜 `UnrealEditor` 스텁(인자를 받고 프로젝트 `Saved/Profiling/CSV`에 `FrameTime` CSV를 쓰는 셸 스크립트)으로 펜스 `j27-run-sh`를 통해 실행: `run.rc` `0`, `game-pid` 숫자, `KERN_PROCARGS2` 출력 15줄(스텁은 `/bin/sh`가 0번이라 실제보다 1개 많다 — 0번을 뺀 14개가 펜스 `j27-expected-argv`와 같았다), `ps` 출력은 argv를 공백으로 이어 붙였다. `j27-where-sh`는 `class candidate-1`·`wide 1`·`wide-same yes`, 분기 B·`class none`(`j27-row-sh` rc 3)도 가짜 입력으로 확인했다. `golmok-perf` rc 0, 3줄 표. `j27-logcheck-sh`는 C++·엔진 소스의 로그 문자열로 만든 합성 로그에서 펜스 `j27-expected-logcheck`와 같았고 빈 로그에서는 달랐다(빈 검사 아님). `j27-ph-awk`는 견본 본문에서 원문 인용·명령 기록·미채움을 갈랐다. `j27-row-sh`의 행(분기 A)을 scratch `mac-setup.md` #26 뒤에 넣고 `awk getline` 확인 `diff` 0, 파이썬 게이트(`ruff check`·`ruff format --check`·`pytest -q` 1937 passed 3 skipped·`check_repo.py` OK) 통과. dry-run하지 못한 것: 실제 `build.sh`·`UnrealEditor-Cmd` 생성기·`-game` 실행(로그 줄의 실제 형태, 셰이더 컴파일 시간, CSV가 쓰이는 폴더 — 엔진 소스 읽기로는 후보 1이 유력하지만 그것이 이 과제가 재는 것이다), 실제 `$W`·`$HOME` 경로에서의 `diff`, `gh` 명령, 인용·숫자 검사(본문이 없어서). 설계 리뷰 반영분(2026-11-28, Opus 문서 에이전트, `origin/main` `8ba637c` scratch 사본 — git 저장소로 만든 것): 할 일 6의 `sed -i '' "/^| 26 | …/r …"`는 `row-insert.rc` `0`, 정확히 #26 다음에 넣은 것과 바이트가 같은 파일, `row-diff.log` `exit=0`, `grep -c '^| 27 | '` `1`, numstat `1	0`, `status.diff` `exit=0`(같은 명령을 두 번 돌리면 `grep -c`가 `2`). 할 일 7의 `timeout`을 단 게이트는 rc 0(1937 passed, 3 skipped, 약 78 s), `-nt` 확인은 게이트 로그가 새것이면 `newer=0`·헌것이면 `newer=1`(zsh·sh 같음), 커밋 뒤 `branch-files.log`는 한 줄, `status-final.diff`는 `exit=0`. `gh pr view <브랜치> --json number --jq .number`는 이 PR(#155)에서 `155` 한 줄이고 `gh`의 안내 문구 8줄은 stderr로 갔다(그래서 `pr-number.err`로 나눴다). 잠금 갱신 ①은 자기 줄이면 rc 0·시각 갱신, 다른 세션 줄이면 rc 1·그대로. 갱신 루프는 `sleep 1`로 줄여 zsh·bash에서 돌려 자기 줄의 시각을 고쳐 쓰고, `kill "$RP"` 뒤에 멈추고, 다른 세션 줄을 만나면 쓰지 않고 끝났다(bash는 끝날 때 하네스 화면에 `Terminated: 15` 한 줄을 찍는다 — 로그에는 들어가지 않는다). 멈춤 순서 ①의 `pgrep`은 편집기가 없을 때 rc `1`·빈 파일. 실제 240초 간격·실제 UE 명령과 함께 돈 루프, `gh pr create`·`gh pr edit`는 dry-run하지 못했다.

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

#### J-30a (J-30을 좁힌 것) COLMAP 희소 모델 → EXIF GPS ENU 정합(`model_aligner`) → 정합 좌표의 Brush splat, 수치 확인만 — 설계 확정(Opus 2026-11-28)
- **배정 보류(영록, 2026-11-28)**: 이 절은 설계가 확정됐지만 할 일 9의 "자리표시 검사" 단계가 글자 그대로는 충족될 수 없다(분류 표의 줄이 다시 검색에 걸린다 — 재검증 지적). J-27 할 일 8처럼 절 제목(`## 완료 기준 대조`·`## 실행한 명령`)과 펜스 기준의 기계적 분류 + 개수 표로 고친 뒤 배정한다. 그 전에는 시작하지 않는다.
- **출처**: [WP-21](WP-21-mac-recon-pipeline.md) "남은 작업" 4("COLMAP 희소 모델 미터·ENU 정합 → 메시·splat 좌표 공유를 끝까지 해 본다"), D-023 "좌표" 줄(Brush는 COLMAP world를 그대로 쓴다, 미터·ENU 정합은 그 모델에서 먼저 한 번 [미확인, 끝까지 해 보지 않음]), [mac-recon.md](../runbooks/mac-recon.md) M3 "정합(미터·ENU)" 문단(:93-95)과 §6 미확인 #5(:230, 확인 결과 칸 빈 칸), 공개 데이터 출처·저작자 표시 mac-recon :180(Tyrol 교회 드론 76장 5472×3648, CC BY 4.0, [Tyrol-Church](https://github.com/IRCSS/Tyrol-Church-Photogrammetry-Dataset)). 입력은 저장소 밖 `~/golmok_data/recon-smoke/objcap/tyrol/images`(JPG 76장, EXIF GPS 있음 — `exiftool`로 `DJI_0352.JPG 46.9482009166667 12.062021 1645`). 도구: `~/golmok-tools`의 COLMAP 4.2.1 `cpu_lgpl`, Brush v0.3.0, exiftool 13.64(mac-recon §1). COLMAP 4.2.1 `model_aligner` 소스 [model.cc](https://github.com/colmap/colmap/blob/4.2.1/src/colmap/exe/model.cc)(`RunModelAligner`: `--alignment_max_error`가 0 이하면 "You must provide a maximum alignment error > 0"로 실패, `--alignment_type enu`이면 참조 위치의 **첫 줄**을 ENU 원점으로 쓴다 — `ConvertCameraLocations`; `--ref_images_path` 한 줄 = `이름 x y z`, `--ref_is_gps 1`이면 위도·경도·고도), [sim3.cc](https://github.com/colmap/colmap/blob/4.2.1/src/colmap/geometry/sim3.cc) `Sim3d::ToFile`(`scale qw qx qy qz tx ty tz` 한 줄), 공식 FAQ [Geo-registration](https://colmap.github.io/faq.html#geo-registration). 저장소 도구: `tools/golmok_tools/exif.py` `read_exif`(exifread, `lat`·`lon`·`alt`, `GPSAltitudeRef` 1이면 음수), `tools/golmok_tools/splat/ply.py` `read_ply`·`positions`, `golmok-splat inspect --json`.
- **설계 (확정, Opus 2026-11-28)**: 재환은 아래를 그대로 옮긴다. 바꿀 점이 보이면 고치지 말고 묻는다.
  1. **범위**: 희소 모델을 EXIF GPS ENU로 옮기고, 그 모델로 splat을 학습해 splat이 같은 좌표에 있는지 **수치로만** 확인한다. Object Capture 메시를 같은 좌표로 옮기는 절반은 **J-30b**(나중, 별도 설계)다. 그래서 이 과제가 끝나도 "메시·splat 좌표 공유"는 절반만 된 것이고, 결과 문장에 그렇게 쓴다(렌더 스크립트가 넣는다). zone 원점(매니페스트 `origin`)으로 옮기는 것도 하지 않는다.
  2. **데이터·작업 폴더**: 이미지는 읽기만 한다(`I="$HOME/golmok_data/recon-smoke/objcap/tyrol/images"`). 출력은 전부 `E="$TMPDIR/jaehwan/J-30a"` 아래(데이터베이스 약 130 MB, 왜곡 제거 이미지 약 0.8 GB, PLY 1개(`export_3000.ply`) 약 45 MB). 커밋하는 데이터는 없다. Object Capture는 다시 돌리지 않는다(피크 33 GB, J-30b는 있는 `tyrol-full` 출력을 쓴다). COLMAP 명령은 `cd "$E" &&`, Brush는 `cd "$E/brush" &&`로 시작한다(WP-21 사고: 저장소 루트에서 돌린 Brush가 `target/`을 만들었다). COLMAP은 `$TMPDIR` 바로 아래에 `colmap.*.log.INFO.*` 파일을 따로 남긴다(dry-run에서 관찰, `--log_target`과 상관없이 생김) — 저장소 밖이라 그대로 두고 지우지 않는다.
  3. **COLMAP 체인(플래그 고정)**: mac-recon M3과 같은 꼴. `feature_extractor` `--ImageReader.camera_model OPENCV --ImageReader.single_camera 1 --FeatureExtraction.use_gpu 0 --FeatureExtraction.max_image_size 3200`(76장이 모두 같은 카메라 `L1D-20c`·5472×3648·10.26 mm — exiftool로 확인; 3200은 M3 값이고 CPU 시간을 묶는다. 4.2.1 기본값은 `-1` = 줄이지 않음). 매칭은 `exhaustive_matcher --FeatureMatching.use_gpu 0`(76장 = 2,850쌍, dry-run 29 s; sequential·spatial은 쓰지 않는다 — XMP `RelativeAltitude`가 두 고도대(약 60 m대 40장·100 m대 34장)라 이름 순서가 이웃 순서라는 보장이 없고, 76장은 전수 매칭이 싸다). 매핑은 증분 `mapper` 하나(M3 정본 명령; `global_mapper`는 좌표계가 달라 쓰지 않는다 — M3 "한 모델만 정본"). `feature_extractor`가 EXIF GPS를 데이터베이스 `pose_priors`에 넣지만(로그 `GPS:` 76줄) 이 과제는 데이터베이스 사전값을 정합에 쓰지 않는다(설계 4).
  4. **정합(`model_aligner`, 4.2.1 `-h`로 확인한 옵션만)**: `--input_path "$E/sparse/0" --output_path "$E/aligned" --ref_images_path "$E/ref_gps.txt" --ref_is_gps 1 --alignment_type enu --alignment_max_error 3 --transform_path "$E/aligned/sim3.txt"`. 이유: ① 참조는 **파일**로 준다(`--database_path`가 아니라). 파일은 원점(첫 줄)을 우리가 정하고, 내용을 sha256으로 고정할 수 있다. 4.2.1은 파일과 데이터베이스를 함께 주면 "Use location file or database, not both"로 실패한다. ② `--robust_alignment`는 4.2.1에 **없다**(dry-run: `unrecognised option '--robust_alignment'`, rc 1). 강건 정합은 `--alignment_max_error`(RANSAC 임계값, m)로 켜지고 이 값은 반드시 0보다 커야 한다(빼면 rc 1). 3 m는 dry-run 잔차 최대 2.172 m보다 커서 76장이 모두 inlier가 되는 값이고, 3과 10이 같은 변환을 냈다(`sim3.txt` 동일). ③ `--min_common_images`는 기본값 3 그대로. ④ `--merge_image_and_ref_origins`는 쓰지 않는다(기본 0). 옵션 이름은 boost 접두 일치를 받아 **틀린 철자가 조용히 통과할 수 있다**(dry-run: `--alignment_typ enu`가 rc 0) — 명령은 이 절에서 글자 그대로 복사한다.
  5. **참조 파일 만들기**: 펜스 `j30a-make-ref`(저장소의 `golmok_tools.exif.read_exif`, `$W/tools/.venv` 파이썬). 이미지 이름순, 한 줄 `이름 위도 경도 고도`(위도·경도 소수 9자리, 고도 3자리). exiftool은 첫 장 한 줄 대조에만 쓴다(둘 중 무엇을 쓸지 재환이 고르지 않는다). 같은 76장이면 출력이 결정적이다: sha256 `989373f7b3c7e2d6befb8b5582a3262c433f69dee2512bf3799dd82d00a9ddf6`(Opus가 메인 venv와 `$W/tools/.venv` 두 곳에서 같은 값, exifread 3.5.1).
  6. **ENU 원점과 고도**: 원점은 참조 파일 **첫 줄 = 이름순 첫 장 `DJI_0352.JPG`의 EXIF GPS**(46.948200917, 12.062021000, 1645)다. 평균 원점은 쓰지 않는다 — COLMAP `enu`가 첫 줄을 원점으로 쓰므로 평균을 쓰려면 ENU 변환을 우리가 하고 `custom`으로 넘겨야 하는데, 그러면 COLMAP의 `enu` 경로(런북이 확인하려는 것)를 시험하지 않게 된다. 고도: COLMAP은 `--ref_is_gps 1`의 고도를 WGS84 타원체고로 다룬다(`GPSTransform` WGS84). DJI EXIF `GPSAltitude`의 기준면(해발인지 타원체고인지)은 [미확인]이고 이 데이터에서는 1 m 단위다(참조 파일 고도가 모두 `.000`). 모든 장이 같은 기준면이면 차이는 거의 공통 오프셋 하나라, 원점도 같은 EXIF 고도인 상대 ENU에서는 대부분 지워진다(남는 영향은 오프셋 × 수평 거리 / 지구 반지름 정도 — 수 mm 규모의 추정이지 측정이 아니다). 그래서 결과 문장은 "EXIF GPS ENU에 정합, 잔차 중앙값 N m"이고 "측량 정확도"·"미터 정확"이라고 쓰지 않는다.
  7. **확인 스크립트(펜스, 손으로 옮기지 않는다)**: `j30a-check-align` — 참조 파일을 **자체 WGS84 → ECEF → ENU 식**으로 바꿔(COLMAP 구현과 독립) 정합 모델 `images.txt`의 카메라 중심(`-Rᵀt`)과 비교: 등록 수·공통 수, 잔차 중앙값·p90·최대(m), 수평·수직 중앙값, `sim3.txt` 첫 값(축척), 희소 점 수, 카메라 평균 높이 − 희소 점 높이 중앙값(m), `+Z`/`-Z`. `j30a-check-splat` — splat 위치마다 가장 가까운 SfM 점까지 거리(`scipy.spatial.cKDTree`, `tools/.venv`의 scipy 1.18.1) 중앙값·p90(m), SfM 점끼리 최근접 거리 중앙값(밀도 참고), 두 집합의 축별 중앙값. 비교 대상은 정합 모델의 점(`aligned_txt/points3D.txt`)이다 — `image_undistorter`가 좌표계를 그대로 둔다는 가정 없이 "splat이 정합 모델 좌표에 있다"를 직접 본다(2026-11-28 설계 리뷰: dry-run 출력에서 `undistorted/sparse/points3D.txt`와 XYZ가 같고 `check_splat` 출력 6줄도 같았다). 대조군: 같은 splat을 **정합 전** 모델 점과 비교한 값(`splat-control.log`)은 커야 한다 — 거리 지표가 좌표계 차이를 가려낸다는 비공허 증거다.
  8. **splat(정합 좌표)**: `image_undistorter --input_path "$E/aligned"` → `model_converter`로 `undistorted/sparse`를 TXT로(제자리, M3과 같음) → Brush `--total-steps 3000 --max-resolution 1600 --seed 42 --export-every 3000`(WP-21 스모크의 3k·1600과 같은 크기, 시간 상한용; `--eval-split-every`는 넣지 않는다, `--sh-degree`는 기본 3). 3,000스텝은 이 확인용이고 구역 splat 규칙(D-006, M5의 30,000)을 바꾸지 않는다. 그다음 `golmok-splat inspect --json`.
  9. **통과 기준(파이프라인 일관성 확인이지 품질이 아니다 — 품질은 V-05, Opus·소유자)**: 펜스 `j30a-verdict`가 13개를 판정한다. 참조 GPS 76/76·누락 0, 등록 76·공통 76, 카메라 중심 잔차 **중앙값 ≤ 3.0 m · p90 ≤ 5.0 m · 최대 ≤ 10.0 m**, COLMAP 로그의 median과 자체 계산 중앙값 차 ≤ 0.01 m, `+Z`, 카메라 높이 ≥ 20 m, 축척 > 0, splat 수 = `inspect.json` `count`이고 `sh_degree` 3, **splat → 정합 SfM 중앙값 ≤ 3.0 m · p90 ≤ 15.0 m**, 대조군(정합 전 점) 중앙값 ≥ 30.0 m. 근거: Opus dry-run 두 번(같은 데이터베이스에서 `mapper` 두 번) — 잔차 1.201/1.671/2.172 m와 1.176/1.634/2.155 m, COLMAP median 1.200858·1.175685, 높이 60.98·61.08 m(원점 장 `DJI_0352.JPG`의 XMP `RelativeAltitude` +62.10과 같은 규모), 축척 32.4702·33.4693(정합 전 모델의 축척이 임의라 실행마다 다르다 → 값 기준 없음, 기록만); Brush 두 번(같은 시드) splat → SfM 중앙값 1.074·1.059 m, p90 7.028·7.034 m, 대조군 93.735 m, SfM 점 최근접 간격 중앙값 0.630 m. 상한은 dry-run 값의 약 2~3배로 잡아 실행 간 흔들림은 통과시키고 좌표계가 틀린 경우(대조군 ~94 m, 정합 전 잔차 ~105 m)는 떨어뜨린다. WP-21의 Buddha 값 0.0049 "단위"는 EXIF 없는 임의 축척이라 이 m 값과 직접 비교하지 않는다.
  10. **기록(규칙 16, 덧붙이기만)**: 런북 두 군데만 — ① mac-recon M3 "정합" 문단의 마지막 줄(`- 보조 확인은`으로 시작하는 `golmok-align run` 줄, 지금 :95) **바로 뒤에** 날짜 메모 한 줄을 더한다. ② §6 #5 행의 빈 "확인 결과" 칸을 채운다(다른 칸·다른 행은 그대로). 두 줄의 글자는 펜스 `j30a-render`가 로그에서 만들고(숫자를 손으로 옮기지 않는다), 펜스 `j30a-apply`가 넣는다(앵커가 정확히 1번씩일 때만, 아니면 rc 1로 아무것도 쓰지 않는다). 기존 문장 "[미확인: 끝까지 해 보지 않음]"은 지우지 않는다(그 뒤의 날짜 메모가 갱신이다). WP-21 결과 줄·STATUS는 영록이 병합 때 고친다("병합 시 반영").
  11. **라이선스·개인정보**: Tyrol 데이터는 CC BY 4.0이고 저작자 표시는 mac-recon :180에 이미 있다(이 과제의 메모도 "공개 Tyrol 드론 76장 CC BY 4.0"이라 적는다). D-007 블러는 **우리 촬영물**에 적용한다. WP-21 스모크는 이 공개 세트를 블러 없이 Object Capture에 썼고(mac-recon §3), 이 과제도 같은 전례로 블러하지 않는다 — 재환이 블러 여부를 정하지 않는다. 모든 처리는 로컬이고 출력은 `$E`에만 있으며 외부로 올리지 않는다. 이미지·PLY·데이터베이스는 커밋하지 않는다.
  12. **새 저장소 코드 없음**: 스크립트는 이 절의 펜스와 `$E`에만 있다. 재사용 명령(`golmok-align colmap-enu` 등)이 필요하면 따로 설계한 과제로 한다(`tools/pyproject.toml`은 핫스팟). 허용 파일 `docs/runbooks/mac-recon.md`는 핫스팟도 Astra 레인도 아니다(CLAUDE.md §7.6 목록에 없음) — 훅 표시를 넣지 않는다.
  13. **J-30b(나중, 설계 선행 그대로)**: Object Capture `tyrol-full/poses.json`의 카메라 중심과 J-30a 정합 COLMAP 카메라 중심을 이미지 이름으로 짝지어 Sim3(Umeyama)를 구하고, 잔차와 변환한 OBJ 정점 ↔ 정합 SfM 점 거리를 잰다. 맞춤 코드를 `golmok-align` 하위 명령으로 만들지(Claude 레인 코드 결정) 일회성으로 둘지는 J-30b 설계에서 정한다. J-30a의 `$E/aligned`를 J-30b가 다시 쓰므로 병합 알림 뒤에도 `$E`를 지우지 않는다(J-30b 배정 때 영록이 알린다). `$E`는 `$TMPDIR`(`/var/folders/…/T`) 아래이고 macOS는 며칠 쓰지 않은 그 아래 파일을 지울 수 있으므로, J-30b 설계는 먼저 `$E/aligned`·`$E/aligned_txt`가 남아 있는지 확인하고, 없으면 J-30a 할 일 3~4를 다시 돌리는 단계를 넣는다(그 경우 축척 값은 실행마다 다르다 — 설계 9).

```python j30a-make-ref
import sys
from pathlib import Path

from golmok_tools.exif import read_exif

img_dir, out_path = Path(sys.argv[1]), Path(sys.argv[2])
names = sorted(p.name for p in img_dir.iterdir() if p.suffix.upper() == ".JPG")
lines, missing = [], []
for name in names:
    info = read_exif(img_dir / name)
    if info.lat is None or info.lon is None or info.alt is None:
        missing.append(name)
        continue
    lines.append(f"{name} {info.lat:.9f} {info.lon:.9f} {info.alt:.3f}")
out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("images", len(names))
print("with_gps", len(lines))
print("missing_gps", len(missing))
print("first", lines[0] if lines else "none")
```

```text j30a-ref-expected
images 76
with_gps 76
missing_gps 0
first DJI_0352.JPG 46.948200917 12.062021000 1645.000
```

```python j30a-check-align
import math
import sys
from pathlib import Path

import numpy as np

ref_path, model_dir, sim3_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
A, F = 6378137.0, 1 / 298.257223563  # WGS84
E2 = F * (2 - F)


def ecef(lat, lon, h):
    la, lo = math.radians(lat), math.radians(lon)
    n = A / math.sqrt(1 - E2 * math.sin(la) ** 2)
    return np.array(
        [
            (n + h) * math.cos(la) * math.cos(lo),
            (n + h) * math.cos(la) * math.sin(lo),
            (n * (1 - E2) + h) * math.sin(la),
        ]
    )


ref = [line.split() for line in ref_path.read_text(encoding="utf-8").splitlines() if line.strip()]
lat0, lon0, h0 = (float(v) for v in ref[0][1:4])
la, lo = math.radians(lat0), math.radians(lon0)
rot = np.array(
    [
        [-math.sin(lo), math.cos(lo), 0.0],
        [-math.sin(la) * math.cos(lo), -math.sin(la) * math.sin(lo), math.cos(la)],
        [math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)],
    ]
)
o = ecef(lat0, lon0, h0)
enu = {r[0]: rot @ (ecef(float(r[1]), float(r[2]), float(r[3])) - o) for r in ref}

lines = [
    ln for ln in (model_dir / "images.txt").read_text(encoding="utf-8").splitlines() if not ln.startswith("#")
]
centres = {}
for ln in lines[0::2]:
    p = ln.split()
    qw, qx, qy, qz, tx, ty, tz = (float(v) for v in p[1:8])
    r = np.array(
        [
            [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qw * qz), 2 * (qx * qz + qw * qy)],
            [2 * (qx * qy + qw * qz), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qw * qx)],
            [2 * (qx * qz - qw * qy), 2 * (qy * qz + qw * qx), 1 - 2 * (qx * qx + qy * qy)],
        ]
    )
    centres[p[9]] = -r.T @ np.array([tx, ty, tz])

common = sorted(set(centres) & set(enu))
d = np.array([centres[n] - enu[n] for n in common])
err = np.linalg.norm(d, axis=1)
pts = np.array(
    [
        [float(v) for v in ln.split()[1:4]]
        for ln in (model_dir / "points3D.txt").read_text(encoding="utf-8").splitlines()
        if not ln.startswith("#")
    ]
)
cam_z = np.mean([centres[n][2] for n in common])
height = cam_z - float(np.median(pts[:, 2]))
print("ref_images", len(ref))
print("registered", len(centres))
print("common", len(common))
print(f"origin {ref[0][0]} {lat0:.9f} {lon0:.9f} {h0:.3f}")
print(f"residual_m median {np.median(err):.3f} p90 {np.percentile(err, 90):.3f} max {err.max():.3f}")
print(f"residual_h_m median {np.median(np.linalg.norm(d[:, :2], axis=1)):.3f}")
print(f"residual_v_m median {np.median(np.abs(d[:, 2])):.3f}")
print(f"scale {float(sim3_path.read_text().split()[0]):.4f}")
print("points", len(pts))
print(f"camera_height_above_point_median_m {height:.2f}")
print("up", "+Z" if height > 0 else "-Z")
```

```python j30a-check-splat
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from golmok_tools.splat.ply import positions, read_ply

ply_path, points_txt = Path(sys.argv[1]), Path(sys.argv[2])
splat = positions(read_ply(ply_path)).astype(np.float64)
lines = points_txt.read_text(encoding="utf-8").splitlines()
pts = np.array([[float(v) for v in ln.split()[1:4]] for ln in lines if not ln.startswith("#")])
tree = cKDTree(pts)
dist, _ = tree.query(splat, k=1)
nn, _ = tree.query(pts, k=2)
print("splats", len(splat))
print("sfm_points", len(pts))
print(f"splat_to_sfm_m median {np.median(dist):.3f} p90 {np.percentile(dist, 90):.3f}")
print(f"sfm_nn_m median {np.median(nn[:, 1]):.3f}")
print("splat_median_m", " ".join(f"{v:.2f}" for v in np.median(splat, axis=0)))
print("sfm_median_m", " ".join(f"{v:.2f}" for v in np.median(pts, axis=0)))
```

```python j30a-verdict
import json
import re
import sys
from pathlib import Path

e = Path(sys.argv[1])


def kv(name):
    out = {}
    for line in (e / name).read_text(encoding="utf-8").splitlines():
        p = line.split()
        if p:
            out[p[0]] = p[1:]
    return out


ref, al, sp, ctl = kv("ref.log"), kv("align-check.log"), kv("splat-check.log"), kv("splat-control.log")
m = re.search(
    r"=> Alignment error: ([0-9.]+) \(mean\), ([0-9.]+) \(median\)", (e / "aligner.log").read_text()
)
colmap_median = float(m.group(2)) if m else float("nan")
inspect = json.loads((e / "inspect.json").read_text(encoding="utf-8"))
res = dict(zip(al["residual_m"][0::2], map(float, al["residual_m"][1::2]), strict=True))
s2s = dict(zip(sp["splat_to_sfm_m"][0::2], map(float, sp["splat_to_sfm_m"][1::2]), strict=True))
ctl_median = float(ctl["splat_to_sfm_m"][1])
checks = [
    (
        "gps_images",
        int(ref["with_gps"][0]) == 76 and int(ref["missing_gps"][0]) == 0,
        f"{ref['with_gps'][0]} == 76",
    ),
    (
        "registered",
        int(al["registered"][0]) == 76 and int(al["common"][0]) == 76,
        f"{al['registered'][0]} == 76",
    ),
    ("residual_median_m", res["median"] <= 3.0, f"{res['median']:.3f} <= 3.0"),
    ("residual_p90_m", res["p90"] <= 5.0, f"{res['p90']:.3f} <= 5.0"),
    ("residual_max_m", res["max"] <= 10.0, f"{res['max']:.3f} <= 10.0"),
    (
        "colmap_median_agrees",
        abs(colmap_median - res["median"]) <= 0.01,
        f"|{colmap_median:.3f} - {res['median']:.3f}| <= 0.01",
    ),
    ("up", al["up"][0] == "+Z", al["up"][0]),
    (
        "camera_height_m",
        float(al["camera_height_above_point_median_m"][0]) >= 20.0,
        f"{al['camera_height_above_point_median_m'][0]} >= 20",
    ),
    ("scale", float(al["scale"][0]) > 0, f"{al['scale'][0]} > 0"),
    (
        "splat_count",
        int(sp["splats"][0]) == inspect["count"] and inspect["sh_degree"] == 3,
        f"{sp['splats'][0]} == {inspect['count']}",
    ),
    ("splat_to_sfm_median_m", s2s["median"] <= 3.0, f"{s2s['median']:.3f} <= 3.0"),
    ("splat_to_sfm_p90_m", s2s["p90"] <= 15.0, f"{s2s['p90']:.3f} <= 15.0"),
    ("control_unaligned_median_m", ctl_median >= 30.0, f"{ctl_median:.3f} >= 30.0"),
]
for name, ok, text in checks:
    print("PASS" if ok else "FAIL", name, text)
passed = sum(ok for _, ok, _ in checks)
print("verdict", "PASS" if passed == len(checks) else "FAIL", f"{passed}/{len(checks)}")
sys.exit(0 if passed == len(checks) else 1)
```

```python j30a-render
import re
import sys
from pathlib import Path

e, day = Path(sys.argv[1]), sys.argv[2]


def kv(name):
    return {
        p[0]: p[1:] for p in (ln.split() for ln in (e / name).read_text(encoding="utf-8").splitlines()) if p
    }


al, sp, ctl = kv("align-check.log"), kv("splat-check.log"), kv("splat-control.log")
m = re.search(r"=> Alignment error: [0-9.]+ \(mean\), [0-9.]+ \(median\)", (e / "aligner.log").read_text())
colmap_line = m.group(0)
r = al["residual_m"]
res = f"중앙값 {r[1]} m · p90 {r[3]} m · 최대 {r[5]} m"
s2s = f"중앙값 {sp['splat_to_sfm_m'][1]} m · p90 {sp['splat_to_sfm_m'][3]} m"
note = (
    f"- {day} 메모(J-30a, 공개 Tyrol 드론 76장 CC BY 4.0, 블러 없음 — §3 스모크와 같은 공개 데이터, 품질 판정 아님): "
    "COLMAP 4.2.1 `feature_extractor`(OPENCV, `single_camera 1`, `max_image_size 3200`) → `exhaustive_matcher` "
    "→ `mapper` → `model_aligner --ref_images_path ref_gps.txt --ref_is_gps 1 --alignment_type enu "
    "--alignment_max_error 3`이 끝까지 돌았다. `ref_gps.txt`는 EXIF GPS(`이름 위도 경도 고도`, 이름순)이고, "
    "4.2.1에는 `--robust_alignment`가 없으며 `--alignment_max_error`는 0보다 커야 하는 RANSAC 임계값(m)이다. "
    "ENU 원점은 참조 파일 첫 줄인 `DJI_0352.JPG`의 EXIF GPS다. "
    f"등록 {al['registered'][0]}/76, 카메라 중심 ↔ EXIF GPS ENU 거리 {res}(COLMAP 원문 `{colmap_line}`), "
    f"축척 {al['scale'][0]}, 카메라 평균 높이가 희소 점 중앙값보다 "
    f"{al['camera_height_above_point_median_m'][0]} m 위(+Z가 위). "
    "정합 모델 → `image_undistorter` → Brush 3,000스텝(`--max-resolution 1600`) splat "
    f"{sp['splats'][0]}개에서 가장 가까운 정합 SfM 점까지 {s2s}(정합 전 모델 점과는 중앙값 "
    f"{ctl['splat_to_sfm_m'][1]} m). EXIF 고도는 1 m 단위이고 기준면(타원체고인지 해발인지)은 [미확인]이다. "
    "원점도 같은 EXIF 고도라 공통 오프셋은 상대 ENU에서 거의 지워진다. 그래서 이 결과는 "
    f'"EXIF GPS ENU에 정합, 잔차 중앙값 {r[1]} m"이지 측량 정확도가 아니다. zone 원점으로 옮기기와 '
    "Object Capture 메시의 같은 좌표 변환(J-30b)은 하지 않았다. 로그 `$TMPDIR/jaehwan/J-30a/`."
)
row = (
    "| 5 | `colmap model_aligner` 미터·ENU 정합(옵션·결과) | 끝까지 해 보지 않음 | GPS 있는 리허설 → zone-local 범위 확인 | "
    f"{day}(J-30a, 공개 Tyrol 76장, 품질 판정 아님): `--ref_images_path`·`--ref_is_gps 1`·`--alignment_type enu`·"
    f"`--alignment_max_error 3`으로 정합, 등록 {al['registered'][0]}/76, 카메라 중심 잔차 {res}, "
    f"splat → SfM 중앙값 {sp['splat_to_sfm_m'][1]} m. `{colmap_line}`. 리허설 사진·zone-local 범위는 남음. "
    'M3 "정합" 메모, 로그 `$TMPDIR/jaehwan/J-30a/`. |'
)
print(note)
print(row)
```

```python j30a-apply
import sys
from pathlib import Path

doc, lines_file = Path(sys.argv[1]), Path(sys.argv[2])
note, row = lines_file.read_text(encoding="utf-8").splitlines()
anchor = (
    '- 보조 확인은 `golmok-align run --zone "$Z" --basemap ~/golmok_basemap/yeonnam '
    '--gps "$CAP/photos_blurred/_golmok/gps_priors.csv" --ground`(리포트만, [align.md](align.md))다.'
)
old_row = "| 5 | `colmap model_aligner` 미터·ENU 정합(옵션·결과) | 끝까지 해 보지 않음 | GPS 있는 리허설 → zone-local 범위 확인 | |"
src = doc.read_text(encoding="utf-8").split("\n")
print("anchor", src.count(anchor))
print("old_row", src.count(old_row))
if src.count(anchor) != 1 or src.count(old_row) != 1:
    sys.exit(1)
i = src.index(anchor)
src.insert(i + 1, note)
src[src.index(old_row)] = row
doc.write_text("\n".join(src), encoding="utf-8")
print("applied")
```

```text j30a-fence-lines
19 make_ref.py
75 check_align.py
21 check_splat.py
66 verdict.py
45 render.py
20 apply.py
```

- **명령 공통**: 셸 변수는 Bash 호출 사이에 남지 않는다. 그래서 **모든 명령은 `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/jaehwan/J-30a"; I="$HOME/golmok_data/recon-smoke/objcap/tyrol/images"; PY="$W/tools/.venv/bin/python"; . "$HOME/golmok-tools/env.sh";`로 시작하고**(마지막 것은 `colmap`·`brush_app`·`exiftool`을 PATH에 넣는다), 그 뒤는 `cd "$E" &&`·`cd "$E/brush" &&`·`cd "$W" &&`·`cd "$W/tools" &&`·`git -C "$W"`·`"$E/…"` 절대 경로로 시작한다(상시 규칙, 설계 2). 아래 명령에는 이 앞머리를 적지 않았다. 돌린 명령 원문은 `"$E/commands.txt"`에 한 줄씩 더한다(규칙 10). 기다릴 수 있는 긴 명령(COLMAP `feature_extractor`·`exhaustive_matcher`·`mapper`·`model_aligner`·`image_undistorter`, Brush, `check_splat.py` 두 번, 게이트, `gh pr checks --watch`)은 `/usr/bin/timeout`(규칙 5)이고 시간은 아래에 고정했다. `git fetch`·`git push`·`gh pr list`·`gh pr create`·`gh pr view`·`gh pr edit`·`model_analyzer`·`model_converter`·`golmok-splat inspect`는 아래에 적힌 그대로 쓴다(`timeout`을 더하거나 빼지 않는다). 위 긴 명령들은 **항상** 하네스의 백그라운드 실행으로 돌리고, 그 명령이 쓰는 `.rc` 파일(`gh pr checks --watch`는 `checks-watch.log`의 `exit=` 줄)이 생길 때까지 기다린다(명령은 바꾸지 않는다). 그 밖의 명령은 앞쪽(foreground)으로 돌린다. 각 단계의 "기대"와 다르면 **멈춤 조건**을 본다.
  - **펜스 추출** `X <펜스 이름> <파일>`: `sed -n '/^```python <펜스 이름>$/,/^```$/p' "$E/task.txt" | sed '1d;$d' > "$E/<파일>"`(text 펜스는 `python` 자리에 `text`). 손으로 옮기지 않는다.
  - **GUI·GPU 잠금 확인**(잡지 않는다 — UE를 띄우지 않는다): `L="$TMPDIR/claude/gui-foreground.lock"; if [ -e "$L" ]; then cat "$L"; else echo "no lock"; fi > "$E/lock-check-<n>.log"; date -u +%FT%TZ >> "$E/lock-check-<n>.log"` — 기대 첫 줄 `no lock`. 다른 줄이 있으면(영록이 성능을 재는 중일 수 있다) **지우지 않고** 그 줄을 영록에게 보내고 기다린다. `<n>`은 할 일 1이면 `a`, 할 일 5(Brush 앞)이면 `b`.
  - **부하 기록**(규칙 15, 판정 아님): `{ date -u +%FT%TZ; uptime; /usr/bin/timeout 20 "$HOME/.lmstudio/bin/lms" ps; } > "$E/load-<n>.log" 2>&1` — `<n>`은 `before`(할 일 1)·`after`(할 일 5 끝). LM Studio 모델이 로드돼 있었는지를 PR에 적는다. 이 과제의 시간·메모리 수치는 판정 근거가 아니다(재환 추론이 같은 GPU·통합 메모리를 쓴다).
- **할 일**:
  1. **준비**: `mkdir -p "$E" && git -C "$W" fetch origin && git -C "$W" switch -c local/jaehwan-j30a-colmap-enu origin/main && cd "$W" && sed -n '/^#### J-30a /,/^- \*\*dry-run 범위(Opus 2026-11-28, J-30a)\*\*/p' docs/plan/jaehwan-tasks.md > "$E/task.txt"`(규칙 14). 기대: `head -1 "$E/task.txt"`가 `#### J-30a `로 시작하고 `tail -1 "$E/task.txt"`가 `- **dry-run 범위(Opus 2026-11-28, J-30a)**`로 시작한다. 펜스 추출 8번: `X j30a-make-ref make_ref.py`, `X j30a-check-align check_align.py`, `X j30a-check-splat check_splat.py`, `X j30a-verdict verdict.py`, `X j30a-render render.py`, `X j30a-apply apply.py`, text `X j30a-ref-expected expected-ref.txt`, text `X j30a-fence-lines expected-fence-lines.txt`. 확인: `cd "$E" && wc -l make_ref.py check_align.py check_splat.py verdict.py render.py apply.py | sed '$d' | awk '{print $1, $2}' | diff "$E/expected-fence-lines.txt" - > "$E/fence-lines.diff"; echo "exit=$?" >> "$E/fence-lines.diff"` — 기대 `exit=0` 한 줄. 도구: `colmap version 2>&1 | head -1 > "$E/versions.log"; brush_app --version >> "$E/versions.log" 2>&1; exiftool -ver >> "$E/versions.log"` — 기대 세 줄 `COLMAP 4.2.1 (Commit Unknown on Unknown without GPU support, std hash maps)`, `brush-cli 0.3.0`, `13.64`. 옵션: `cd "$E" && colmap model_aligner -h > "$E/aligner-help.log" 2>&1; grep -c -E '^  --(ref_images_path|ref_is_gps|alignment_type|alignment_max_error|transform_path) arg' "$E/aligner-help.log"` — 기대 `5`; `grep -c -F -- '--robust_alignment' "$E/aligner-help.log"` — 기대 `0`. 입력: `ls "$I" | wc -l | tr -d ' '` `76`, `ls "$I" | grep -v -c '\.JPG$'` `0`, `cd "$I" && shasum -a 256 *.JPG | shasum -a 256 | cut -c1-64 > "$E/input-hash-before.log"` — 기대 `c28c1998b732270ccb1bc6e93267779fbb8f30bdd449c6059ef241317c8aebb3`(이미지 폴더에서 `cd`는 읽기만 하는 `shasum`에만 쓴다). 겹침: `cd "$W" && gh pr list --state open --json number,headRefName,files --jq '.[]|select(any(.files[]; .path=="docs/runbooks/mac-recon.md"))|"\(.number) \(.headRefName)"' > "$E/overlap.log" 2>&1` — 기대 빈 파일. `git -C "$W" status --porcelain > "$E/status-before.log"`(내용은 기록만 — 다른 과제가 남긴 추적 안 된 파일이 있을 수 있다). 잠금 확인(`a`), 부하 기록(`before`).
  2. **참조 파일**: `cd "$E" && "$PY" "$E/make_ref.py" "$I" "$E/ref_gps.txt" > "$E/ref.log" 2>&1; echo $? > "$E/ref.rc"` — 기대 rc `0`, `diff "$E/expected-ref.txt" "$E/ref.log"` 출력 없음(종료 0), `shasum -a 256 "$E/ref_gps.txt" | cut -c1-64` `989373f7b3c7e2d6befb8b5582a3262c433f69dee2512bf3799dd82d00a9ddf6`, `wc -l < "$E/ref_gps.txt" | tr -d ' '` `76`. exiftool 대조: `exiftool -n -p '$FileName $GPSLatitude $GPSLongitude $GPSAltitude' "$I/DJI_0352.JPG" > "$E/exiftool-first.log" 2>&1` — 기대 한 줄 `DJI_0352.JPG 46.9482009166667 12.062021 1645`.
  3. **SfM**: 특징 `cd "$E" && /usr/bin/timeout 1800 /usr/bin/time -l colmap feature_extractor --database_path "$E/database.db" --image_path "$I" --ImageReader.camera_model OPENCV --ImageReader.single_camera 1 --FeatureExtraction.use_gpu 0 --FeatureExtraction.max_image_size 3200 > "$E/fe.log" 2>&1; echo $? > "$E/fe.rc"` — 기대 rc `0`, `grep -c 'Processed file \[' "$E/fe.log"` `76`, `grep -c 'GPS:' "$E/fe.log"` `76`(dry-run 324 s, peak footprint 약 36 GB — 기록만). 매칭 `cd "$E" && /usr/bin/timeout 900 /usr/bin/time -l colmap exhaustive_matcher --database_path "$E/database.db" --FeatureMatching.use_gpu 0 > "$E/match.log" 2>&1; echo $? > "$E/match.rc"` — 기대 rc `0`. 매핑 `mkdir -p "$E/sparse" && cd "$E" && /usr/bin/timeout 1800 /usr/bin/time -l colmap mapper --database_path "$E/database.db" --image_path "$I" --output_path "$E/sparse" > "$E/mapper.log" 2>&1; echo $? > "$E/mapper.rc"` — 기대 rc `0`, `ls "$E/sparse"` 한 줄 `0`. 분석 `cd "$E" && colmap model_analyzer --path "$E/sparse/0" > "$E/analyzer.log" 2>&1; echo $? > "$E/analyzer.rc"` — 기대 rc `0`, `grep -c 'Registered images: 76$' "$E/analyzer.log"` `1`.
  4. **정합**: `mkdir -p "$E/aligned" && cd "$E" && /usr/bin/timeout 300 colmap model_aligner --input_path "$E/sparse/0" --output_path "$E/aligned" --ref_images_path "$E/ref_gps.txt" --ref_is_gps 1 --alignment_type enu --alignment_max_error 3 --transform_path "$E/aligned/sim3.txt" > "$E/aligner.log" 2>&1; echo $? > "$E/aligner.rc"` — 기대 rc `0`, 아래 네 개가 각각 `1`: `grep -c -F 'Using the first GPS coordinate as the ENU origin' "$E/aligner.log"`, `grep -c -F '=> Using 76 reference images' "$E/aligner.log"`, `grep -c -F '=> Alignment error:' "$E/aligner.log"`, `grep -c -F '=> Alignment succeeded' "$E/aligner.log"`. `awk '{print NF}' "$E/aligned/sim3.txt"` `8`. TXT로: `mkdir -p "$E/aligned_txt" "$E/sparse_txt" && cd "$E" && colmap model_converter --input_path "$E/aligned" --output_path "$E/aligned_txt" --output_type TXT > "$E/conv-aligned.log" 2>&1; echo $? > "$E/conv-aligned.rc"`, 같은 꼴로 `--input_path "$E/sparse/0" --output_path "$E/sparse_txt"` → `conv-sparse.log`·`conv-sparse.rc` — 기대 둘 다 rc `0`. 확인: `cd "$E" && "$PY" "$E/check_align.py" "$E/ref_gps.txt" "$E/aligned_txt" "$E/aligned/sim3.txt" > "$E/align-check.log" 2>&1; echo $? > "$E/align-check.rc"` — 기대 rc `0`, 11줄(`wc -l`), 첫 세 줄 `ref_images 76`·`registered 76`·`common 76`, 넷째 줄 `origin DJI_0352.JPG 46.948200917 12.062021000 1645.000`. 숫자 판정은 할 일 6이 한다.
  5. **splat(정합 좌표)**: `cd "$E" && /usr/bin/timeout 900 colmap image_undistorter --image_path "$I" --input_path "$E/aligned" --output_path "$E/undistorted" --output_type COLMAP > "$E/undist.log" 2>&1; echo $? > "$E/undist.rc"` — 기대 rc `0`, `ls "$E/undistorted/images" | wc -l | tr -d ' '` `76`. `cd "$E" && colmap model_converter --input_path "$E/undistorted/sparse" --output_path "$E/undistorted/sparse" --output_type TXT > "$E/conv-undist.log" 2>&1; echo $? > "$E/conv-undist.rc"` — 기대 rc `0`, `grep -c ' PINHOLE ' "$E/undistorted/sparse/cameras.txt"` `1`. 잠금 확인(`b`). Brush: `mkdir -p "$E/brush" && cd "$E/brush" && RUST_LOG=info /usr/bin/timeout 1800 /usr/bin/time -l brush_app "$E/undistorted" --total-steps 3000 --max-resolution 1600 --seed 42 --export-every 3000 --export-path "$E/brush" --export-name "export_{iter}.ply" > "$E/brush.log" 2>&1; echo $? > "$E/brush.rc"` — 기대 rc `0`, `grep -c 'backend: Metal' "$E/brush.log"`이 1 이상, `ls "$E/brush/export_3000.ply"` 있음(`target/`은 `$E/brush` 안에 생긴다 — 그대로 둔다). `cd "$E" && "$W/tools/.venv/bin/golmok-splat" inspect --json "$E/brush/export_3000.ply" > "$E/inspect.json" 2> "$E/inspect.err"; echo $? > "$E/inspect.rc"` — 기대 rc `0`. 거리: `cd "$E" && /usr/bin/timeout 600 "$PY" "$E/check_splat.py" "$E/brush/export_3000.ply" "$E/aligned_txt/points3D.txt" > "$E/splat-check.log" 2>&1; echo $? > "$E/splat-check.rc"`, 대조군 `cd "$E" && /usr/bin/timeout 600 "$PY" "$E/check_splat.py" "$E/brush/export_3000.ply" "$E/sparse_txt/points3D.txt" > "$E/splat-control.log" 2>&1; echo $? > "$E/splat-control.rc"` — 기대 둘 다 rc `0`, 각 6줄. 저장소가 그대로인지: `git -C "$W" status --porcelain > "$E/status-after-run.log"; diff "$E/status-before.log" "$E/status-after-run.log" > "$E/status-run.diff"; echo "exit=$?" >> "$E/status-run.diff"` — 기대 `exit=0` 한 줄. 입력이 그대로인지: `cd "$I" && shasum -a 256 *.JPG | shasum -a 256 | cut -c1-64 > "$E/input-hash-after.log"; diff "$E/input-hash-before.log" "$E/input-hash-after.log"` — 출력 없음. 부하 기록(`after`).
  6. **판정**: `cd "$E" && "$PY" "$E/verdict.py" "$E" > "$E/verdict.log" 2>&1; echo $? > "$E/verdict.rc"` — 기대 rc `0`, `grep -c '^PASS ' "$E/verdict.log"` `13`, `grep -c '^FAIL ' "$E/verdict.log"` `0`, 끝 줄 `verdict PASS 13/13`. 비공허(판정이 틀린 좌표를 떨어뜨리는지): `mkdir -p "$E/neg" && cp "$E/ref.log" "$E/aligner.log" "$E/inspect.json" "$E/neg/" && printf '1 0 0 0 0 0 0 0\n' > "$E/neg/identity.txt" && cd "$E" && "$PY" "$E/check_align.py" "$E/ref_gps.txt" "$E/sparse_txt" "$E/neg/identity.txt" > "$E/neg/align-check.log" 2>&1 && cp "$E/splat-control.log" "$E/neg/splat-check.log" && cp "$E/splat-control.log" "$E/neg/splat-control.log" && "$PY" "$E/verdict.py" "$E/neg" > "$E/verdict-neg.log" 2>&1; echo $? > "$E/verdict-neg.rc"` — 기대 rc `1`, 끝 줄이 `verdict FAIL `로 시작, 아래 다섯 줄이 각각 `grep -c` `1`: `^FAIL residual_median_m `, `^FAIL residual_p90_m `, `^FAIL residual_max_m `, `^FAIL colmap_median_agrees `, `^FAIL splat_to_sfm_median_m `(정합 전 모델의 위·아래 방향과 높이는 실행마다 임의라 `up`·`camera_height_m` 줄은 기대에 넣지 않는다).
  7. **런북 두 줄**: `cd "$E" && "$PY" "$E/render.py" "$E" "$(date +%F)" > "$E/runbook-lines.txt" 2> "$E/render.err"; echo $? > "$E/render.rc"` — 기대 rc `0`, `wc -l < "$E/runbook-lines.txt" | tr -d ' '` `2`, `grep -c '<' "$E/runbook-lines.txt"` `0`. `cd "$W" && "$PY" "$E/apply.py" docs/runbooks/mac-recon.md "$E/runbook-lines.txt" > "$E/apply.log" 2>&1; echo $? > "$E/apply.rc"` — 기대 rc `0`, `apply.log` 세 줄 `anchor 1`·`old_row 1`·`applied`. 확인: `cd "$W" && git diff --numstat -- docs/runbooks/mac-recon.md > "$E/numstat.log"` — 기대 `2	1	docs/runbooks/mac-recon.md`. 더한 줄이 렌더 결과와 같은지: `cd "$W" && git diff -U0 -- docs/runbooks/mac-recon.md | grep -E '^\+[^+]' | sed 's/^+//' | diff "$E/runbook-lines.txt" - > "$E/added.diff"; echo "exit=$?" >> "$E/added.diff"` — 기대 `exit=0` 한 줄. 지운 줄은 #5 옛 행 하나: `cd "$W" && git diff -U0 -- docs/runbooks/mac-recon.md | grep -c -E '^-\| 5 \| `colmap model_aligner`'` — 기대 `1`. `apply.py`를 두 번 돌리지 않는다(두 번째는 `old_row 0`으로 rc 1 — 그게 정상이다).
  8. **게이트·커밋·push**: 파이썬 게이트(규칙 13, 하네스 백그라운드): `cd "$W/tools" && source .venv/bin/activate && { /usr/bin/timeout 300 ruff check . && /usr/bin/timeout 300 ruff format --check . && /usr/bin/timeout 1800 pytest -q && /usr/bin/timeout 300 python scripts/check_repo.py; } > "$E/gate.log" 2>&1; echo $? > "$E/gate.rc"` — 기대 rc `0`(코드 변경은 없지만 `check_repo.py`가 런북 링크를 본다; rc 124 = 시간 초과, 다시 돌리지 않고 멈춤). 커밋: `cd "$W" && git add docs/runbooks/mac-recon.md && git diff --cached --name-only > "$E/c1-files.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-30a: mac-recon — model_aligner EXIF GPS ENU 정합·정합 좌표 splat 수치(공개 Tyrol)" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c1-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-c1.log"` — 기대: `c1-files.log` 한 줄 `docs/runbooks/mac-recon.md`, `author-c1.log` `재환 <jaehwan.local@localhost>`. 게이트 로그가 런북보다 새것인지: `[ "$E/gate.log" -nt "$W/docs/runbooks/mac-recon.md" ]; echo "newer=$?" > "$E/mtime.log"` — 기대 `newer=0`. `git -C "$W" push -u origin local/jaehwan-j30a-colmap-enu > "$E/push.log" 2>&1; echo "exit=$?" >> "$E/push.log"` — 기대 끝 줄 `exit=0`. 브랜치 파일: `git -C "$W" diff --name-only origin/main...HEAD > "$E/branch-files.log"` — 기대 한 줄 `docs/runbooks/mac-recon.md`. push 뒤 상태: `git -C "$W" status --porcelain > "$E/status-after-push.log"; diff "$E/status-before.log" "$E/status-after-push.log" > "$E/status-push.diff"; echo "exit=$?" >> "$E/status-push.diff"` — 기대 `exit=0` 한 줄. PR 열기(첫 본문은 CI 자리 한 줄뿐 — 규칙 2): `printf '%s\n' '## 요약' '' 'COLMAP EXIF GPS ENU 정합과 정합 좌표 splat 수치(공개 Tyrol). 본문은 CI 뒤에 채운다.' '' '## CI' '' 'CI 진행 중 — 결과는 아래에 추가' > "$E/pr-body-initial.md"; cd "$W" && gh pr create --base main --head local/jaehwan-j30a-colmap-enu --title "J-30a: COLMAP EXIF GPS ENU 정합과 정합 좌표 splat 수치(공개 Tyrol)" --body-file "$E/pr-body-initial.md" > "$E/pr-create.log" 2>&1; echo $? > "$E/pr-create.rc"` — 기대 `0`. PR 번호: `cd "$W" && gh pr view local/jaehwan-j30a-colmap-enu --json number --jq .number > "$E/pr-number.log" 2> "$E/pr-number.err"` — 기대 숫자 한 줄(`grep -c -x '[0-9][0-9]*' "$E/pr-number.log"` `1`, `wc -l < "$E/pr-number.log" | tr -d ' '` `1`; `gh`가 stderr에 찍는 안내 문구는 `pr-number.err`로 가고 판정하지 않는다). 아래 명령은 이 파일에서 번호를 읽는다. CI(하네스 백그라운드): `cd "$W" && /usr/bin/timeout 1800 gh pr checks "$(cat "$E/pr-number.log")" --watch --interval 30 > "$E/checks-watch.log" 2>&1; echo "exit=$?" >> "$E/checks-watch.log"; gh pr checks "$(cat "$E/pr-number.log")" > "$E/checks.log" 2>&1` — 기대: 모든 행 pass.
  9. **PR 본문**: 절 순서 = 요약 · 바뀐 파일 · **`## 결과`**(관찰한 값만: `verdict.log` 13줄 원문, `align-check.log`·`splat-check.log`·`splat-control.log` 원문, `aligner.log`의 `=> Alignment error:` 줄, 각 단계 rc, `load-before.log`·`load-after.log`의 LM Studio 줄 — 과제 번호·규칙 번호·날짜는 이 절에 쓰지 않는다; 시간·메모리는 "기록, 판정 근거 아님"으로만) · 완료 기준 대조(규칙 14: `$E/task.txt`의 "완료 기준" 부분을 물결 펜스 `~~~` 코드 블록에 그대로 붙이고, 아래에 (a)~(i) 한 줄씩 충족 + 증거 파일 또는 **미충족** + 이유) · 실행한 명령(`$E/commands.txt` 그대로) · 남은 `[미확인]`(EXIF 고도 기준면, J-30b 메시 절반, zone 원점 변환, 실촬영 리허설) · 병합 시 반영 · 제출 전 점검표(규칙 1~16 한 줄씩, 과거형과 결과) · 서명. 본문 초안은 `$E/pr-body.md`. 게시 전 검사(규칙 10 e·f) — **대상 로그는 이 목록으로 고정한다**(본문 초안·게시본·`task.txt`·`commands.txt`·`runbook-lines.txt`·검사 로그 자신은 넣지 않는다): `"$E"/versions.log "$E"/ref.log "$E"/exiftool-first.log "$E"/fe.log "$E"/match.log "$E"/mapper.log "$E"/analyzer.log "$E"/aligner.log "$E"/align-check.log "$E"/undist.log "$E"/brush.log "$E"/inspect.json "$E"/splat-check.log "$E"/splat-control.log "$E"/verdict.log "$E"/verdict-neg.log "$E"/load-before.log "$E"/load-after.log "$E"/numstat.log "$E"/gate.log "$E"/checks.log`.
     - 인용 검사: `## 결과` 절의 백틱 문자열마다 그 문자열이 근거로 든 로그 **한 개**를 `"$E/quotes.tsv"`에 `<문자열><탭><위 목록의 파일 이름>`으로 적는다(로그 인용이 아닌 파일 이름·명령은 파일 칸에 `라벨`). 빠진 것 확인: `` awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '`[^`]+`' | sed 's/^`//;s/`$//' | sort -u > "$E/body-quotes.txt"; cut -f1 "$E/quotes.tsv" | sort -u > "$E/tsv-quotes.txt"; comm -23 "$E/body-quotes.txt" "$E/tsv-quotes.txt" > "$E/quotes-missing.log" `` — 기대 빈 파일. 세기: `while IFS="$(printf '\t')" read -r q f; do if [ "$f" = "라벨" ]; then n="라벨"; else n=$(grep -F -c -- "$q" "$E/$f"); fi; printf '%s\t%s\t%s\n' "$n" "$f" "$q"; done < "$E/quotes.tsv" > "$E/quotes-check.log"` — 기대: `cut -f1 "$E/quotes-check.log" | grep -c -x '0'`가 `0`.
     - 숫자 검사: `awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '[0-9]{2,}' | sort -u > "$E/body-numbers.txt"; while read -r x; do printf '%s\t%s\n' "$(cat "$E"/versions.log "$E"/ref.log "$E"/exiftool-first.log "$E"/fe.log "$E"/match.log "$E"/mapper.log "$E"/analyzer.log "$E"/aligner.log "$E"/align-check.log "$E"/undist.log "$E"/brush.log "$E"/inspect.json "$E"/splat-check.log "$E"/splat-control.log "$E"/verdict.log "$E"/verdict-neg.log "$E"/load-before.log "$E"/load-after.log "$E"/numstat.log "$E"/gate.log "$E"/checks.log | grep -c -- "$x")" "$x"; done < "$E/body-numbers.txt" > "$E/numbers-check.log"` — 기대: `cut -f1 "$E/numbers-check.log" | grep -c -x '0'`가 `0`.
     - 0이 나온 것은 고치거나 지운다. 그다음 게시: `cd "$W" && gh pr edit "$(cat "$E/pr-number.log")" --body-file "$E/pr-body.md" > "$E/pr-edit.log" 2>&1; echo $? > "$E/pr-edit.rc"` — 기대 `0`.
     - 자리표시 검사(규칙 12): 게시 뒤 `cd "$W" && gh pr view "$(cat "$E/pr-number.log")" --json body --jq .body > "$E/posted-body.md"; grep -n -E '<[^>]+>|\[\]|TODO|TBD' "$E/posted-body.md" > "$E/placeholder-hits.log"`. 이 과제 글을 그대로 인용하면 `<n>`·`<문자열>`·`<펜스 이름>` 같은 토큰이 걸리므로 "걸림 0"을 기대하지 않는다. 대신 `placeholder-hits.log`의 **모든 줄**을 PR 본문 끝 표(줄 번호 · 걸린 글자 · 분류)에 `원문 인용`(과제 인용 펜스 안) / `명령 기록`(실행한 명령 절 안) / `미채움` 중 하나로 분류하고, **`미채움`은 0**이어야 한다. 미채움이 있으면 `$E/pr-body.md`에서 채운다. 그 표는 `$E/pr-body.md` 끝에 붙인다.
     - 마지막 게시: 위 게시 명령(`pr-edit.log`·`pr-edit.rc`)을 한 번 더 돌리고(기대 `0`), 위 자리표시 검사 명령을 한 번 더 돌려 다시 읽는다(규칙 12) — 새 `placeholder-hits.log`의 줄도 모두 표에 분류돼 있고 `미채움` 0.
- **허용 파일**: `docs/runbooks/mac-recon.md`(설계 10의 두 줄만 — M3 "정합" 문단 뒤 한 줄 추가, §6 #5 행의 빈 칸 채움). 그 밖의 저장소 파일은 건드리지 않는다(`tools/`·`pyproject.toml`·CI·`check_repo.py`·WP-21·STATUS 등 공유 문서 포함). 스크립트·로그·데이터는 `$E`에만.
- **멈춤 조건(정하지 말고 영록에게 묻는다)**: `task.txt` 첫·끝 줄, `fence-lines.diff`, `versions.log`가 기대와 다를 때. `aligner-help.log`의 옵션 수가 `5`가 아니거나 `--robust_alignment`가 나올 때(**옵션을 바꾸거나 더하지 않는다**). `overlap.log`가 비어 있지 않을 때. 입력 장수·JPG 외 파일 수·입력 해시가 기대와 다를 때, 또는 할 일 5 뒤 해시가 바뀌었을 때. 잠금 확인이 `no lock`이 아닐 때. 부하 기록에서 `lms` 명령이 실패해도 멈추지 않고 그 출력 그대로 적는다(판정 아님). `ref.rc`가 0이 아니거나 `ref.log`가 펜스와 다르거나(특히 `missing_gps`가 0이 아님 = GPS를 못 읽음) `ref_gps.txt` sha256·줄 수·`exiftool-first.log`가 다를 때. `fe.rc`·`match.rc`·`mapper.rc`·`analyzer.rc`·`aligner.rc`·`conv-*.rc`·`undist.rc`·`brush.rc`·`inspect.rc`·`splat-*.rc`·`align-check.rc`가 0이 아닐 때 — 특히 **rc 124(`timeout`) = CPU·GPU 실행이 정한 시간을 넘음**이면 같은 명령을 다시 돌리지 않는다(규칙 5). `sparse`에 `0` 말고 다른 폴더가 있거나(모델이 끊김) `Registered images: 76`이 아닐 때(**76 미만 등록**). `aligner.log`에 `unrecognised option`, `You must provide a maximum alignment error`, `Cannot align with insufficient reference locations`, `Alignment failed`, `Use location file or database, not both` 중 하나가 있거나 기대 네 줄이 `1`이 아닐 때(**inlier 부족·정합 실패** 포함). `verdict.rc`가 0이 아니거나 `FAIL` 줄이 하나라도 있을 때(기준·스크립트를 고치지 않는다, 값과 함께 묻는다). `verdict-neg`가 기대와 다를 때. `status-run.diff`가 `exit=0`이 아닐 때(저장소에 무엇이 생김 — 지우지 말고 `git -C "$W" status --porcelain` 원문과 함께 묻는다). `render.rc`·`apply.rc`가 0이 아니거나 `apply.log`·`numstat.log`·`added.diff`·지운 줄 수가 기대와 다를 때. `gate.rc`가 0이 아닐 때(rc 124 포함, 다른 파일을 고치거나 `ruff format`으로 바꾸지 않는다). `c1-files.log`·`author-c1.log`가 다를 때. `mtime.log`가 `newer=0`이 아닐 때. `push.log`가 `exit=0`이 아닐 때, `branch-files.log`가 `docs/runbooks/mac-recon.md` 한 줄이 아니거나 `status-push.diff`가 `exit=0`이 아닐 때. `pr-create.rc`·`pr-edit.rc`가 0이 아니거나 `pr-number.log`가 숫자 한 줄이 아닐 때. `checks.log`에 pass가 아닌 행이 있을 때. 그 밖에 이 절의 "기대"와 다른 값이 하나라도 나올 때. 이 과제는 GUI 잠금을 잡지 않으므로 풀 잠금이 없다(잠금 파일을 만들거나 지우지 않는다).
- **완료 기준**:
  - (a) 준비: `task.txt` 첫 줄 `#### J-30a `·끝 줄 `- **dry-run 범위(Opus 2026-11-28, J-30a)**`, `fence-lines.diff` `exit=0`, `versions.log` 세 줄, 옵션 수 `5`·`--robust_alignment` `0`, `overlap.log` 빈 파일, `input-hash-before.log` `c28c1998b732270ccb1bc6e93267779fbb8f30bdd449c6059ef241317c8aebb3`.
  - (b) 참조: `ref.rc` `0`, `ref.log` = 펜스 `j30a-ref-expected`, `ref_gps.txt` sha256 `989373f7b3c7e2d6befb8b5582a3262c433f69dee2512bf3799dd82d00a9ddf6`·76줄, `exiftool-first.log` `DJI_0352.JPG 46.9482009166667 12.062021 1645`.
  - (c) SfM: `fe.rc`·`match.rc`·`mapper.rc`·`analyzer.rc` 모두 `0`, `fe.log`의 `Processed file [`·`GPS:` 각 `76`, `ls "$E/sparse"` = `0`, `Registered images: 76` 1줄.
  - (d) 정합: `aligner.rc` `0`, `aligner.log`의 네 줄(원점·`=> Using 76 reference images`·`=> Alignment error:`·`=> Alignment succeeded`) 각 `1`, `sim3.txt` 필드 `8`, `align-check.log` 원문(11줄, 첫 네 줄이 할 일 4의 기대).
  - (e) splat: `undist.rc`·`conv-undist.rc`·`brush.rc`·`inspect.rc`·`splat-check.rc`·`splat-control.rc` 모두 `0`, `backend: Metal` 1줄 이상, `export_3000.ply` 있음, `splat-check.log`·`splat-control.log` 원문.
  - (f) 판정: `verdict.rc` `0`, `PASS` 13줄·`FAIL` 0줄, 끝 줄 `verdict PASS 13/13`. 비공허: `verdict-neg.rc` `1`, 끝 줄 `verdict FAIL …`, 할 일 6의 `FAIL` 다섯 줄 각 `1`.
  - (g) 저장소·입력: `status-run.diff` `exit=0`, 입력 해시 전후 같음. 런북: `render.rc`·`apply.rc` `0`, `apply.log` 세 줄, `numstat.log` `2	1	docs/runbooks/mac-recon.md`, `added.diff` `exit=0`, 지운 줄 `1`. `branch-files.log` = `docs/runbooks/mac-recon.md` 한 줄.
  - (h) 게이트 `gate.rc` `0`·`mtime.log` `newer=0`, 작성자 `재환 <jaehwan.local@localhost>`, `push.log` 끝 줄 `exit=0`, `pr-create.rc` `0`·`pr-number.log` 숫자 한 줄, CI `checks.log` 모든 행 pass 원문(규칙 2), `status-push.diff` `exit=0`.
  - (i) PR 본문: "완료 기준 대조" 절과 점검표 1~16, `## 결과`에 부하 기록(LM Studio 줄) 원문, `quotes-missing.log` 빈 파일, `quotes-check.log`·`numbers-check.log`에 0 없음, 자리표시 검사의 모든 줄이 원문 인용 / 명령 기록 / 미채움으로 분류된 표가 있고 미채움 0, `pr-edit.rc` `0`(두 번 모두), 마지막 게시 뒤 다시 읽은 `posted-body.md`(규칙 12).
- **병합 시 반영(영록)**: STATUS 재환 절에 J-30a 행. WP-21 "남은 작업" 4 끝에 날짜 메모(희소 모델 → EXIF GPS ENU 정합과 정합 좌표 splat은 J-30a로 확인, 메시 절반은 J-30b). D-023 "좌표" 줄의 [미확인]에 날짜 메모를 더할지는 영록이 판단한다(공유 문서라 재환은 고치지 않는다). J-30b 설계(설계 13)를 이 파일에 쓰고 배정 순서를 정한다.
- **왜 재환 / 위험**: 명령·옵션·스크립트·기준이 모두 정해져 있고 결과가 숫자와 종료 코드로 판정된다. GUI·UE·Astra 레인·소유자 촬영이 필요 없다. 위험: ① 옵션 즉흥 — 4.2.1은 접두 철자를 받아 틀린 옵션이 조용히 통과할 수 있다(설계 4) → 명령을 글자 그대로 복사하고 `-h` 옵션 수로 막는다(규칙 1·6). ② 긴 CPU 실행(특징 추출 dry-run 324 s, peak footprint 약 36 GB, `/usr/bin/time -l` swaps 0 — 같은 세션 뒤 `lms ps`가 모델 94.58 GB 로드를 보였고 실행 중 로드 여부는 [미확인]) → 모든 실행에 `timeout`, 넘으면 멈춤. ③ "미터" 과장 — EXIF 고도 기준면 [미확인], 드론 GPS 오차 → 문장은 렌더 스크립트가 "EXIF GPS ENU에 정합, 잔차 N m"으로 고정한다(규칙 15). ④ 품질로 번지기 — floater·모습·"충분히 좋다"는 판정하지 않는다. 펜스의 숫자만 본다(품질은 V-05). ⑤ 메시 절반이 빠짐 — J-30b(설계 13), 결과 문장에 적힌다. ⑥ 도구가 저장소에 쓰기 — 모든 명령이 `cd "$E…"`로 시작하고 `status-run.diff`로 확인한다. ⑦ 실행 간 흔들림 — `mapper`·Brush는 실행마다 값이 조금 다르다(dry-run 두 번: 잔차 중앙값 1.201·1.176 m, splat 1.074·1.059 m) → 기준은 상한이고, 값을 dry-run과 같게 맞추려 하지 않는다.
- **dry-run 범위(Opus 2026-11-28, J-30a)**: 이 Mac에서 같은 입력·같은 플래그로 할 일 2~7을 scratch 폴더(`$TMPDIR` 밖 세션 scratchpad, 저장소 밖)에서 돌렸다: 참조 파일 76/76·누락 0·sha256 위 값(메인 venv와 `$W/tools/.venv` 둘 다), `feature_extractor` rc 0(324 s, `GPS:` 76줄), `exhaustive_matcher` rc 0(29 s), `mapper` rc 0(80 s, 모델 1개, 등록 76/76, 점 68,938, 재투영 0.850 px), `model_aligner` rc 0(`=> Alignment error: 1.142564 (mean), 1.200858 (median)`; `--alignment_max_error` 3과 10이 같은 `sim3.txt`, 첫 값 32.4702), `check_align` 잔차 1.201/1.671/2.172 m·수평 0.514·수직 1.031·높이 60.98 m·`+Z`, 정합 전 모델로는 105.488 m·`-Z`, `image_undistorter` rc 0(PINHOLE 5471×3648), Brush rc 0(83 s, Metal, 191,643 splat, 같은 시드 두 번째 191,751), `golmok-splat inspect` `count` 191643·`sh_degree` 3, splat → SfM 1.074/7.028 m·대조군 93.735 m, `verdict` `verdict PASS 13/13`, 비공허 사례 rc 1(`verdict FAIL 5/13`, 할 일 6의 다섯 줄 포함), `render`·`apply`를 `origin/main` `8ba637c` scratch 사본(git init)의 mac-recon에 적용 → numstat `2	1`, 두 번째 `apply`는 `old_row 0` rc 1, 그 사본에서 `check_repo.py` OK·`pytest -q` 1937 passed·3 skipped. `mapper`+정합만 한 번 더(같은 데이터베이스): 1.176/1.634/2.155 m, COLMAP median 1.175685, 축척 33.4693. 실패 메시지 확인: `--alignment_max_error` 없음 → "You must provide a maximum alignment error > 0" rc 1, 참조 2줄 → "Cannot align with insufficient reference locations." rc 1, `--robust_alignment` → `unrecognised option` rc 1, `--alignment_typ enu`(오타) → rc 0. 펜스 6개는 `ruff format`을 거친 파일과 같은 글자다. dry-run하지 못한 것: 재환 worktree의 브랜치·커밋·push·`gh` 명령(겹침·PR·CI), 인용·숫자·자리표시 검사 파이프(본문이 없어서), `lms ps`를 명령 공통의 꼴로 감싼 부하 기록(단독 실행은 확인: `qwen3.8-flash-next … IDLE 94.58 GB`). 설계 리뷰 반영분(2026-11-28, Opus 문서 에이전트): `timeout`을 단 게이트는 `8ba637c` scratch 사본에서 rc 0(1937 passed, 3 skipped, 약 78 s), `check_splat.py`를 `aligned_txt/points3D.txt`에 돌린 출력 6줄은 `undistorted/sparse/points3D.txt`에 돌린 것과 같았다(splat → SfM 1.074/7.028 m), push 뒤 상태 비교(`status-push.diff`)·`branch-files.log`·`-nt` 확인은 git 저장소로 만든 scratch 사본에서 기대대로였다. `gh pr create`·`gh pr edit`는 dry-run하지 못했다.

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
- **순서**: J-36과 같은 테스트 파일(`tools/tests/test_ue_mac_scripts.py`)을 고친다 — J-36 병합 뒤 `origin/main`에서 시작한다.
- **출처**: J-06 결과([#143](https://github.com/wooklym/golmok/pull/143)). `tools/ue/add-gasp.sh`의 편집기 가드는 `ps -axo pid=,comm=` 목록에서 실행 파일 이름(경로의 마지막 부분)이 `UnrealEditor*`인 프로세스만 고르고, 그 명령줄(`ps -o command= -p <pid>`)이 `*Golmok.uproject*` 또는 `*"$GaspProject"*`에 맞으면 막는다. 지금 `gasp_env`의 가짜 `ps`를 쓰는 양성 사례(`test_add_gasp_refuses_while_an_editor_runs`)는 `Golmok.uproject` 명령줄 하나뿐이다. `$GaspProject` 분기와, 걸리면 안 되는 두 경우(이름 필터·명령줄 필터)를 확인하는 사례가 없다.
- **할 일**: `tools/tests/test_ue_mac_scripts.py`에 `@posix_only` 사례를 더한다. 모두 `gasp_env`의 `FAKE_PS_LIST`·`FAKE_PS_CMDS`에 줄을 써서 만든다. ① **GASP 프로젝트 일치(막아야 함)**: `UnrealEditor` exe와 `e.gasp_project` 안의 `GASP_58.uproject`를 연 명령줄(`Golmok.uproject` 문자열은 넣지 않는다). 그러면 rc 1, `close the Unreal Editor first (running: <그 pid>`, `e.calls() == []`. ② **음성 — 상관없는 명령줄**: `UnrealEditor*` exe이지만 명령줄이 다른 프로젝트(예: `-Project=/Users/tester/Other/Other.uproject`)다. `e.respond("verify", ok=True, messages=[])` 뒤 `--verify`가 rc 0이고 stderr에 `close the Unreal Editor`가 없고 에디터 스텁이 불린다(`e.calls()`가 비지 않음). ③ **음성 — UnrealEditor가 아닌 실행 파일**: 이름이 `UnrealEditor`로 시작하지 않는 exe(예: `/usr/bin/vim`)이지만 명령줄에 `Golmok.uproject`가 있다. ②와 같은 단언. 기존 사례·픽스처의 동작은 바꾸지 않는다.
- **허용 파일**: `tools/tests/test_ue_mac_scripts.py`. `add-gasp.sh`는 아래 변형 실험에서만 임시로 고치고 커밋하지 않는다. 가드 자체에 결함이 보이면 고치지 말고 출력을 붙여 영록에게 알린다.
- **완료 기준**: (a) `pytest -q tests/test_ue_mac_scripts.py -k add_gasp` 출력 원문. 기존 8개와 새 사례 전부 passed다. (b) 변형 실험(로컬 1회씩, 커밋 안 함, 출력 원문 — 규칙 8): `add-gasp.sh`의 명령줄 `case`에서 `$GaspProject` 패턴을 지우면 ①이 실패한다. 이름 필터의 `continue`를 없애 모든 exe를 세게 하면 ③이 실패한다. 명령줄 `case`를 모든 명령줄에 맞게 바꾸면 ②가 실패한다. 실패한 테스트 이름과 메시지를 붙이고, `git checkout -- tools/ue/add-gasp.sh`로 되돌린 뒤 `git status --porcelain`에 테스트 파일만 남은 출력도 붙인다. (c) 파이썬 게이트, CI 모든 행 초록(Windows 행은 `@posix_only`로 건너뛴다 — J-06과 같은 방식으로 요약 줄을 확인해 적는다).
- **왜 재환 / 위험**: J-06과 같은 스텁 위에서 끝나는 좁은 테스트 일이고 변형 실험으로 판정된다. 위험: ①이 `$GaspProject` 분기가 아니라 `Golmok.uproject` 분기로 통과하는 것(명령줄에 그 문자열을 넣지 않고 (b)의 첫 변형으로 확인한다), 음성 사례가 가드와 상관없는 이유로 결과가 바뀌는 것(rc 0과 "에디터 스텁이 불린다" 단언, (b)로 막는다). J-07과 같은 파일이라 J-07은 코드 변경 없이 끝났으므로 바로 시작할 수 있다.
- **보충(2026-11-28, 영록 — 배정 전, 위 글을 바꾸지 않고 더한다. 위와 다르면 이 보충을 따른다)**:
  - **선행**: J-36이 병합됐다(`8ba637c`). `origin/main`에서 시작한다.
  - **새 사례 이름(고정)**: ① `test_add_gasp_refuses_while_gasp_project_editor_runs`, ② `test_add_gasp_ignores_editor_on_other_project`, ③ `test_add_gasp_ignores_non_editor_with_golmok_project`. 셋 다 이름에 `add_gasp`가 있어 `-k add_gasp`에 든다. pid는 ① 4243, ② 4244, ③ 4245(J-06의 4242와 겹치지 않게).
  - **명령 공통**: 셸 변수는 Bash 호출 사이에 남지 않는다. 그래서 **모든 명령은 `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/jaehwan/J-35";`로 시작하고**, 그 뒤는 `cd "$W" &&`·`cd "$W/tools" &&`·`git -C "$W"`·`"$E/…"` 절대 경로로 시작한다(상시 규칙). 돌린 명령 원문은 `"$E/commands.txt"`에 한 줄씩 더한다(규칙 10). UE를 띄우지 않으므로 GUI 잠금은 필요 없다.
  - **준비**: `mkdir -p "$E" && git -C "$W" fetch origin && git -C "$W" switch -c local/jaehwan-j35-gasp-guard origin/main && cd "$W" && awk '/^#### J-35 /{f=1} /^#### J-36 /{f=0} f' docs/plan/jaehwan-tasks.md > "$E/task.txt"`(규칙 14) — 기대 `head -1 "$E/task.txt"`가 `#### J-35 `로 시작. 겹침: `cd "$W" && gh pr list --state open --json number,headRefName,files --jq '.[]|select(any(.files[]; .path=="tools/tests/test_ue_mac_scripts.py" or .path=="tools/ue/add-gasp.sh"))|"\(.number) \(.headRefName)"' > "$E/overlap.log" 2>&1` — 기대 빈 파일. 기준선: `cd "$W/tools" && source .venv/bin/activate && pytest -q tests/test_ue_mac_scripts.py -k add_gasp > "$E/pytest-base.log" 2>&1; echo $? > "$E/pytest-base.rc"` — 기대 rc `0`, 끝 줄 `8 passed, 37 deselected in …`(Opus가 `8ba637c`에서 확인: `8 passed, 37 deselected`).
  - **새 사례 뒤**: 같은 명령을 `"$E/pytest-new.log"`·`.rc`로 — 기대 rc `0`, 끝 줄 `11 passed, 37 deselected in …`(기존 8 + 새 3).
  - **변형 실험(완료 기준 (b)를 이 명령으로 한다, 한 번에 하나, 커밋하지 않음)**: 대상 줄은 `8ba637c`의 `tools/ue/add-gasp.sh:66` `    case "${Exe##*/}" in UnrealEditor*) ;; *) continue ;; esac`(이름 필터)와 `:69` `        *Golmok.uproject* | *"$GaspProject"*) Running="${Running:+$Running, }$Pid" ;;`(명령줄 `case`)다. 변형마다 `cd "$W" && sed -i '' '<식>' tools/ue/add-gasp.sh && git diff -U0 -- tools/ue/add-gasp.sh | grep -c '^[-+][^-+]' > "$E/m<k>-diff.log"`(기대 `2` — 한 줄 바뀜) → `cd "$W/tools" && source .venv/bin/activate && pytest -q tests/test_ue_mac_scripts.py -k add_gasp > "$E/m<k>.log" 2>&1; echo $? > "$E/m<k>.rc"` → `grep '^FAILED' "$E/m<k>.log" | sed -E 's/ - .*//' > "$E/m<k>-failed.log"` → `git -C "$W" checkout -- tools/ue/add-gasp.sh && git -C "$W" diff --quiet -- tools/ue/add-gasp.sh; echo $? > "$E/m<k>-restored.rc"`(기대 `0`). 식과 기대(`m<k>.rc` `1`, `m<k>-failed.log` 정확히 한 줄):
    - M1(`$GaspProject` 패턴 삭제): `69s/ | \*"\$GaspProject"\*)/)/` → `FAILED tests/test_ue_mac_scripts.py::test_add_gasp_refuses_while_gasp_project_editor_runs`.
    - M2(이름 필터의 `continue` 삭제 — 모든 exe를 센다): `66s/ \*) continue ;; esac/ *) ;; esac/` → `FAILED tests/test_ue_mac_scripts.py::test_add_gasp_ignores_non_editor_with_golmok_project`.
    - M3(명령줄 `case`가 모든 명령줄에 맞음): `69s/\*Golmok\.uproject\* | \*"\$GaspProject"\*)/*)/` → `FAILED tests/test_ue_mac_scripts.py::test_add_gasp_ignores_editor_on_other_project`.
    - 세 식은 Opus가 `8ba637c` 사본에 BSD `sed -i ''`로 적용해 각각 한 줄만 바뀌는 것을 확인했다(`diff`: M1·M3은 69행, M2는 66행). 새 사례로 돌린 확인은 아니다(사례가 아직 없다) — 다른 실패가 나오면 멈춘다.
  - **게이트·커밋·push**: `cd "$W/tools" && source .venv/bin/activate && { ruff check . && ruff format --check . && pytest -q && python scripts/check_repo.py; } > "$E/gate.log" 2>&1; echo $? > "$E/gate.rc"` — 기대 `0`. `cd "$W" && git add tools/tests/test_ue_mac_scripts.py && git diff --cached --name-only > "$E/c1-files.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-35: add-gasp 편집기 가드 남은 분기 스텁 사례(GASP 프로젝트·음성 2종)" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c1-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-c1.log"` — 기대 `c1-files.log` 한 줄 `tools/tests/test_ue_mac_scripts.py`, `author-c1.log` `재환 <jaehwan.local@localhost>`. push 뒤 `/usr/bin/timeout 1800 gh pr checks <n> --watch --interval 30 > "$E/checks-watch.log" 2>&1; gh pr checks <n> > "$E/checks.log" 2>&1` — 모든 행 pass. Windows 행 요약 줄은 `gh run view --job <Windows 잡 id> --log | grep -E '[0-9]+ passed'`로 옮긴다.
  - **PR 본문**: 절 순서 = 요약 · 바뀐 파일 · `## 결과`(관찰한 값만: pytest 끝 줄, 변형 3개의 FAILED 줄 — 과제 번호·규칙 번호·날짜는 쓰지 않는다) · `## 완료 기준 대조`(`$E/task.txt`의 "완료 기준"과 이 보충을 물결 펜스 `~~~` 블록에 그대로 붙이고 (a)~(c)와 보충의 기대마다 충족 + 증거 파일 또는 **미충족** + 이유) · `## 실행한 명령`(`$E/commands.txt` 그대로) · 남은 `[미확인]` · 제출 전 점검표(규칙 1~16 한 줄씩) · 서명. 게시 전 검사 대상 로그는 이 목록으로 고정한다: `"$E"/pytest-base.log "$E"/pytest-new.log "$E"/m1.log "$E"/m2.log "$E"/m3.log "$E"/m1-failed.log "$E"/m2-failed.log "$E"/m3-failed.log "$E"/gate.log "$E"/checks.log`. 인용 검사·숫자 검사는 J-27 할 일 8과 같은 명령에 이 목록을 넣어 돌린다(`quotes-missing.log` 빈 파일, `quotes-check.log`·`numbers-check.log`에 0 없음). (명령 원문은 J-36 할 일 9의 '인용 검사'·'숫자 검사' 두 줄이다 — J-27 할 일 8의 같은 줄에는 J-27 전용 `qwen3.8-flash-next` 멈춤 조건이 있어 쓰지 않는다. `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/jaehwan/J-35"; cd "$W" && awk '/^#### J-36 /{f=1} /^## 재환에게 맞지 않는 것/{f=0} f' docs/plan/jaehwan-tasks.md > "$E/j36-ref.txt"`로 따로 뽑아, 숫자 검사의 `cat` 뒤 로그 목록만 위 목록으로 바꾼다. 본문 초안은 `"$E/pr-body.md"`에 쓴다.) 자리표시: 게시 뒤 `gh pr view <n> --json body --jq .body > "$E/posted-body.md"; grep -n -E '<[^>]+>|\[\]|TODO|TBD' "$E/posted-body.md" > "$E/placeholder-hits.log"` — 걸린 줄마다 `원문 인용` / `명령 기록` / `미채움`으로 분류한 표를 본문 끝에 두고 `미채움`은 0.
  - **멈춤 조건(정하지 말고 영록에게 묻는다)**: `overlap.log`가 비어 있지 않을 때, `task.txt` 첫 줄이 다를 때, 기준선이 `8 passed`가 아니거나 새 사례 뒤가 `11 passed`가 아닐 때, 변형의 `m<k>-diff.log`가 `2`가 아니거나 `m<k>.rc`가 `1`이 아니거나 `m<k>-failed.log`가 위 한 줄과 다를 때, `m<k>-restored.rc`가 `0`이 아닐 때, `gate.rc`가 0이 아닐 때(다른 파일을 고치거나 `ruff format`으로 바꾸지 않는다), `c1-files.log`·`author-c1.log`가 다를 때, CI에 pass가 아닌 행이 있을 때, 가드 자체의 결함으로 보이는 것이 나올 때(`add-gasp.sh`를 고치지 않는다).

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
- **멈춤 조건(정하지 말고 영록에게 묻는다)**: `overlap.log`가 비어 있지 않을 때. 할 일 1의 `head -1 "$E/task.txt"`가 `#### J-36 `로 시작하지 않을 때(`git switch` 실패 포함). `expected-wc.log`·`counts.py` 줄 수가 기대와 다를 때. `pytest-base.rc`가 0이 아닐 때. 잠금 파일에 다른 기록이 있거나 잠금 잡기 rc가 0이 아닐 때. `build.rc`가 0이 아닐 때. `ue-old.rc`가 1이 아니거나 `old-counts.diff`가 `exit=0`이 아닐 때(예: `succeededWithWarnings`가 1이 아님 — 경고 없이 통과했거나 실패한 것). `old-cp.rc`·`new-cp.rc`·`full-cp.rc`가 0이 아닐 때. `ue-old.log`·`ue-new.log`의 `grep -c` 값이 할 일 3·7의 기대와 다를 때. `py-diff.log`·`sh-diff.log`가 `exit=0` 한 줄이 아니거나 `py-diff-blank.log`가 2가 아닐 때. 옛 스크립트에서 새 사례가 실패하지 않거나, 실패한 사례가 위 두 개가 아닐 때. 고친 뒤 pytest가 `N+1 passed`가 아닐 때. `bash-n.log`가 `exit=0`이 아니거나 `ps1-unchanged.rc`가 0이 아닐 때. `ue-new.rc`가 0이 아니거나 `ue-full.rc`가 0이 아니거나 `full-sum.log`가 `same`이 아닐 때(전체 실행의 `failed`·`notRun`·`inProcess`가 0이 아닌 경우 포함 — 원인을 고치지 않는다). 허용 파일 밖이 바뀌었을 때(`status-after-ue.log`에 다른 줄). `gate.rc`가 0이 아닐 때(다른 파일을 고치거나 `ruff format`으로 바꾸지 않는다). `c1-files.log`·`c2-files.log`·`author-c1.log`·`author-c2.log`가 기대와 다를 때. `lock-release-a.rc`·`lock-release-b.rc`가 0이 아닐 때(잠금 파일을 지우지 않는다). `push.log`가 `exit=0`이 아니거나 `checks.log`에 pass가 아닌 행이 있을 때. 명령이 `timeout`(rc 124)으로 끝났을 때(규칙 5). 그 밖에 이 절의 "기대"와 다른 값이 하나라도 나올 때. **할 일 3·7 안에서 멈출 때는 먼저 그 단계의 잠금 풀기(`a`/`b`)를 돌려 `lock-release-<n>.rc`를 남긴 뒤 묻는다.**
- **완료 기준**:
  - (a) 비공허(옛 스크립트): `$E/pytest-old-one.rc` `1`, `^FAILED tests/test_ue_mac_scripts.py::test_test_exit_rules_with_warnings` 1줄, `assert 1 == 0` 1줄, 끝 줄 원문. `$E/pytest-old-all.log`의 FAILED 두 줄(할 일 4의 두 이름)과 끝 줄 원문. 커밋 1(`git -C "$W" show --stat --format= <커밋 1>`)은 `tools/tests/test_ue_mac_scripts.py` 한 파일이다.
  - (b) 고친 뒤: `$E/pytest-base.log`·`$E/pytest-new-all.log` 끝 줄 원문 두 개, 앞이 `N passed`이면 뒤가 `N+1 passed`. `$E/pytest-new-all.rc` `0`.
  - (c) 정확한 변경: `$E/sh-diff.log`·`$E/py-diff.log` 모두 `exit=0` 한 줄, `$E/py-diff-blank.log` `2`. `git -C "$W" diff --name-only origin/main...HEAD` 출력은 `docs/runbooks/mac-setup.md`, `tools/tests/test_ue_mac_scripts.py`, `tools/ue/test.sh` 세 줄. `$E/ps1-unchanged.rc` `0`. `$E/bash-n.log` `exit=0`.
  - (d) 실제 헤드리스, 고치기 전: `$E/build.rc` `0`, `$E/ue-old.rc` `1`, `ue-old.log`의 `Succeeded: 0  Failed: 0  Not run: 0`·`Automation tests failed` 각 1줄, `$E/old-counts.diff` `exit=0`(= 펜스 `j36-counts`).
  - (e) 실제 헤드리스, 고친 뒤: `$E/ue-new.rc` `0`, `ue-new.log`의 `Succeeded: 0  Failed: 0  Not run: 0  Succeeded with warnings: 1` 1줄·`Automation tests failed` 0줄, `$E/new-counts.diff` `exit=0`. 전체 실행 `$E/ue-full.rc` `0`, `$E/full-counts.log` 원문, `$E/full-sum.log` `same`, `ue-full.log` 끝 줄 원문. 보고서 사본 `old-index.json`·`new-index.json`·`full-index.json`이 `$E`에 있다.
  - (f) 런북: 할 일 6의 `grep -c` 두 개(`1`·`0`)와 numstat `1	1	docs/runbooks/mac-setup.md`.
  - (g) 게이트 `$E/gate.rc` `0`, `$E/mtime.log`에서 `gate.log`가 세 파일보다 새것. CI `gh pr checks <n>` 모든 행 pass 원문(규칙 2).
  - (h) `git -C "$W" status --porcelain` 빈 출력(push 뒤). 잠금: `$E/lock-release-a.rc`·`$E/lock-release-b.rc` 모두 `0`. 작성자: `author-c1.log`·`author-c2.log` 모두 `재환 <jaehwan.local@localhost>`.
  - (i) PR 본문: "완료 기준 대조" 절과 점검표 1~16이 있다(2026-11-28: 규칙 16 추가로 1~15 → 1~16). `$E/quotes-missing.log` 빈 파일, `quotes-check.log`·`numbers-check.log`에 0 없음. 게시 뒤 다시 읽은 출력(규칙 12).
  - (정정 2026-11-28, 병합 뒤: (i)의 "게시 뒤 다시 읽은 출력(규칙 12)"은 자리표시 검사를 "걸림 없음"으로 읽게 둔 영록의 문서 결함이다. 할 일 9가 과제 글을 `~~~` 블록에 그대로 붙이라고 하므로 `<사본>`·`<n>` 같은 토큰은 원래 걸린다. 앞으로의 과제는 "걸린 줄마다 원문 인용 / 명령 기록 / 미채움으로 분류한 표, 미채움 0"으로 적는다(J-27 할 일 8, J-30a 할 일 9, J-10 할 일 9·J-11 할 일 7의 정정). J-36 PR은 이미 병합됐으므로 다시 하지 않는다.)
- **병합 시 반영(영록)**: STATUS 재환 절에 J-36 행. [AGENTS.md](../../AGENTS.md):164 끝에 "Mac `test.sh`는 J-36부터 경고 있는 성공도 성공으로 센다(`failed` 0이고 `succeeded`+`succeededWithWarnings` ≥ 1이면 종료 코드 0)" 한 문장을 더할지 영록이 판단한다(Astra 문서라 재환은 고치지 않는다). `test.ps1`·pc-verify-wp18a B4는 Windows 이력이라 그대로 둔다(설계 8). 이월 후보: 성공과 함께 `notRun`·`inProcess`가 남은 실행의 처리(설계 2).
- **왜 재환 / 위험**: 바꿀 줄이 정확히 정해져 있고 전후가 스텁·실제 헤드리스 양쪽에서 명령으로 판정된다. 위험: ① 종료 코드 0을 "실행됐다"로 읽는 것 — `test.sh`의 0은 "`failed` 0이고 무엇이든 성공으로 끝났다"일 뿐이다. 경고 있는 성공에는 skip Info(`MPC_GolmokWeather missing - skipped` 등)나 `NOT EXECUTED` 경고로 끝난 테스트도 들어간다. 판정은 지금처럼 상태 열과 보고서 entries로 한다(mac-setup §4 "기대 결과" 3, 규칙 15). ② 새 사례가 옛 스크립트에서도 통과하는 빈 테스트 — 할 일 4의 실패 로그로 막는다. ③ `_index()` 기본값 변경으로 기존 사례의 의미가 바뀌는 것 — 새 키의 기본값 0은 옛·새 규칙 모두에서 종료 코드를 바꾸지 않고, (a)의 옛 스크립트 실패가 두 사례뿐인 것으로 확인한다. ④ J-35와 같은 테스트 파일이다 — 둘을 동시에 열지 않는다. **J-36이 먼저**다(백로그 순서 J-20 → J-36 → J-18 → J-35; J-35는 J-36 병합 뒤 `origin/main`에서 시작한다).
- **dry-run 범위(Opus 2026-11-28)**: `origin/main` `cff4e92`의 `tools/` scratch 사본에서 설계 4·5를 그대로 적용해 확인한 것: 기준선 44 passed, 테스트만 바꾼 상태(옛 `test.sh`)에서 `-k test_test_exit_rules_with_warnings` → `1 failed, 44 deselected`(`assert 1 == 0` 1줄, FAILED 1줄), 파일 전체 → `2 failed, 43 passed`(할 일 4의 두 이름), `test.sh`까지 바꾼 뒤 → `45 passed`, `ruff check`·`ruff format --check`(테스트 파일) 통과, `bash -n` 통과, `git diff -U0`의 `+`/`-` 줄이 두 펜스와 같고 테스트 파일의 빈 `+` 줄은 2. 새·옛 Python 블록을 실제 보고서 사본에 직접 돌린 결과: J-17 `item1b-index.json`(0/1) 옛 3 → 새 0, J-12 사본(22/17) 둘 다 0, `notRun` 3만 있는 가짜 보고서 둘 다 3. 카운트 스크립트는 `item1b-index.json`에서 펜스 `j36-counts`와 같은 8줄을 냈다. dry-run하지 못한 것: 실제 UE 실행(할 일 3·7), 재환 worktree에서의 pytest 수(N), `gh` 명령, 인용·숫자 검사 파이프(본문이 없어서).
- **결과(2026-11-28, [#154](https://github.com/wooklym/golmok/pull/154) · `8ba637c`, 리뷰 R154)**: 커밋 2개(`82e0a84` 테스트만, `30515d5` `test.sh`·mac-setup), 바뀐 파일은 허용 파일 3개(`tools/ue/test.sh` +3 −2, `tools/tests/test_ue_mac_scripts.py` +17 −3, `docs/runbooks/mac-setup.md` +1 −1). `test.sh`는 이제 `failed == 0`이고 `succeeded + succeededWithWarnings > 0`이면 통과하고 요약 줄 끝에 `Succeeded with warnings:` 수를 찍는다(병합 diff가 펜스 `j36-sh-diff`와 같다). 스텁 pytest: 기준선 44 passed → 테스트만 바꾼 상태(옛 `test.sh`) `2 failed, 43 passed`(`test_test_runs_headless_and_prints_report`·`test_test_exit_rules_with_warnings`) → 수정 뒤 45 passed. 실제 헤드리스: `--filter Golmok.Zone.IndexParse` 고치기 전 rc 1(`Succeeded: 0  Failed: 0  Not run: 0`, `Automation tests failed`) → 고친 뒤 rc 0(`Succeeded: 0  Failed: 0  Not run: 0  Succeeded with warnings: 1`), 보고서 칸은 같은 값. 전체 39 실행 rc 0(`Succeeded: 20  Failed: 0  Not run: 0  Succeeded with warnings: 19`). 게이트 1937 passed, 3 skipped. R154는 Opus 재현 검증 2렌즈(코드: diff가 교체 블록과 바이트 일치·동작 표에서 바뀌는 경우는 설계가 말한 하나뿐 / 증거: 전후 rc와 전체 실행)였고 첫 제출에 병합됐다. 남은 B·C(명령 기록 누락 등)는 재환에게 통보했다(병합 커밋 본문). `test.ps1`은 그대로다(설계 8).

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
- **재환 일이 푸는 것**: V-19 남은 헤드리스 확인(J-12·J-12b~J-16), V-16·V-17·19b·V-18의 헤드리스 단계(J-17~J-23, J-25, J-26)로 그 카드의 GUI 단계가 바로 시작할 수 있게 하는 것, 도구·CI 신뢰도(J-06~J-11, J-28), 재설계·지표의 작은 조각(J-24, J-31a·J-31b), 공개 데이터 좌표 정합(J-30a 설계 확정, 메시 절반 J-30b 설계 선행 — 2026-11-28에 J-30을 나눔), V-05 S12 도구 경로(J-27, 성능 수치 아님).
- **재환 일이 풀지 못하는 것**: 촬영이 없으면 M4~M7은 시작하지 못한다. 재환 과제를 다 끝내도 MVP는 C-01·C-02를 기다린다. 이 파일은 그 기다림을 줄이는 준비 작업의 목록이다.

## 백로그 보충 규칙

- 배정 가능한(선행이 풀린, 설계 선행이면 메모가 있는) 과제가 **5개 아래로** 떨어지면 영록이 STATUS(🟡 행의 "PC 확인 대기"·"[미확인]"), ROADMAP, 열린 V 카드 런북(`docs/runbooks/pc-verify-*.md` §결과 빈칸, mac-setup §8·mac-recon 미확인 표), WP 문서의 "남은 작업"·리뷰 (C) 이월에서 채운다.
- 새 과제도 이 파일의 형식(출처 파일:줄 또는 카드 §, 허용 파일, 명령과 기대 출력인 완료 기준, 크기, 이유·위험)을 지킨다. 출처가 없는 일은 넣지 않고, 불확실한 것은 `[미확인]`으로 둔다.
- 재환이 막히면(선행 미충족·설계 메모 없음·GUI 잠금 대기) 다음 배정 가능 과제로 넘어가고 메시지로 알린다. 영록은 막힌 과제의 선행을 먼저 푼다.
- 이 파일은 영록이 고친다. 재환은 PR 본문에 제안만 적는다.
