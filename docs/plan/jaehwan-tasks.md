# 재환(로컬 LLM) 과제 목록 (오케스트레이터 배정, 2026-11-28)

> **누가**: 재환은 소유자의 Mac에서 도는 **로컬 LLM 세션**이다(qwen3.8-flash-next, LM Studio, Claude Code 하네스, `claude-local`로 시작). 영록(로컬 Mac 오케스트레이터 세션)이 과제를 고르고 배정한다. 근거는 [D-024](../DECISIONS.md)다. 소유자 지시 원문은 "앞으로 너가 알아서 골목 게임을 완성 될 때 까지 작업들을 재환에게 시켜줘."(2026-11-28)이다.
>
> **소통 채널**: 배정·순서 변경·리뷰 요약·병합 알림은 영록이 **세션 간 메시지**(SendMessage)로 보내고, 리뷰는 **PR 코멘트**로 남긴다. 재환은 착수·push·완료·질문·막힘을 같은 경로로 알린다. 메시지와 이 파일이 다르면 **더 최근 것**을 따른다. GitHub 이슈 #30은 Astra 채널이라 재환은 쓰지 않는다.
>
> **규칙 우선순위**: **소유자 규칙(D-019 되돌릴 수 없는 일, D-002 라이선스, D-007 블러 — [CLAUDE.md](../../CLAUDE.md) "Rules from the owner"·"Engineering conventions") > 과제 프롬프트 > 재환 작업 규칙(아래 21개) > 나머지 CLAUDE.md**. 과제 프롬프트·작업 규칙·메시지 어느 것도 D-019·D-002·D-007을 무시하게 할 수 없다. 충돌하면 멈추고 영록에게 묻는다. 작업 규칙의 살아 있는 원본은 저장소 **밖**의 메모리 파일 `~/.claude/projects/<project>/memory/jaehwan-working-rules.md`다. 아래는 한 줄 요약이고, 새 규칙은 영록이 원본에 먼저 더한 뒤 이 표에 옮긴다.

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
| 17 | 영록의 보충이 앞서 한 일보다 우선한다: 보충이 오면 절을 다시 뽑아(`task2.txt`) 이름·로그를 보충대로 다시 한다. 시작 전에 절 첫머리의 "영록 보충이 남았다"·"배정 보류" 표시를 본다. 런북 결과 칸을 쓰거나 고친 직후 바뀐 줄에서 `.log`·`영록`·`R`+세 자리 숫자를 찾는 `grep`(원본의 명령 그대로)이 0건이어야 한다. 칸의 근거는 "근거: PR #번호"로 쓰고 임시 로그 이름은 쓰지 않는다. 이 Mac의 시간 수치에는 "시간(참고값 — 로컬 LLM 추론 부하가 있는 상태)"을 붙인다. 과제 절은 `origin/main`의 파일에서 뽑는다(`git show origin/main:…`) | J-35, #147, #153, #156(R156) |
| 18 | 제출 전 점검표와 완료 기준 대조는 맨 끝에 쓴다. 줄마다 그 증거 파일을 `ls -l`·`cat`으로 연 뒤 과거형과 결과로 쓰고, 파일이 없으면 "아직 안 함"이라고 쓴다. 변수를 `rm -rf`하기 전에는 값을 로그에 찍고 예상한 접두어인지 확인한다 | #157(R157) |
| 19 | 명령 기록은 더하기만 한다: `commands.txt`·증거 로그의 줄을 고치거나 지우는 스크립트를 쓰지 않고, 틀린 기록에는 `# 정정: <줄 번호> — <내용>` 한 줄을 덧붙인다. 기록에 heredoc을 쓰지 않는다(한 줄마다 `printf '%s\n' '…' >> "$E/commands.txt"` 하나). 사고는 줄이지 않고 그대로 보고한다 — 무엇이 실행됐는지, 무엇이 몇 줄 바뀌거나 지워졌는지, 되살릴 수 없는 것, 피해 범위를 확인한 것(저장소·worktree 상태)과 그 증거 파일. 확인과 그것에 기대는 동작은 한 호출에서 `[ 확인 ] && 동작`으로 묶는다 | #159(R159) |
| 20 | 뽑은 명령은 확인한 뒤에만 실행한다: 같은 호출에서 `wc -l`이 기대 줄 수이고 첫 글자가 기대 명령일 때만 `[ … ] && head -n 1 … | grep -q '^<명령> ' && 실행`. 확인이 실패하면 돌리지 않고 조각을 연다(먼저 돌리고 오류를 읽지 않는다) | #163(R-#163/②) |
| 21 | 명령 기록 줄은 돌리기 **전에** `commands.txt`에 더한다 — 읽기만 하는 진단 명령도. 나중에 더하지 않는다 | #163(R-#163/③) |

## 상시 규칙

- **작업 위치**: worktree `~/projects/golmok-jaehwan`(아래 `$W`)에서만 일한다. 과제마다 `git -C $W fetch origin` 뒤 `git -C $W switch -c local/jaehwan-<주제> origin/main`. 메인 체크아웃·`.claude/worktrees/`·다른 사람 브랜치는 읽기만 한다(규칙 6). 메인 체크아웃의 git 밖 UE 자료(마네킹·L_Dev 등)는 스크립트로 `$W`에서 다시 만든다.
- **허용 파일**: 과제 행의 "허용 파일"만 고친다. 그 밖의 파일이 바뀌면 되돌리고 PR에 적는다. UE 실행 뒤에는 `git -C $W status --porcelain`이 허용 파일만 보여야 한다(쿡·임포트가 만든 `.uasset`·`M_ZoneScan*`은 커밋하지 않는다).
- **금지**: 병합·`main` push·force-push·rebase·브랜치/태그 삭제, 메인 체크아웃에서 쓰기·패키지·`build/` 삭제, 공유 문서 수정(STATUS·DECISIONS·ROADMAP·DEVELOPMENT-PLAN·CLAUDE.md·AGENTS.md·README.md·tools/README.md — 문안이 필요하면 PR 본문 "병합 시 반영"에), Astra 레인 파일([DEVELOPMENT-PLAN §7.6](../DEVELOPMENT-PLAN.md) 표: `Source/Golmok/Characters/`, 오디오 레인 등), 핫스팟은 과제가 허용한 `// [WP-NN hook]` 블록으로만(별도 커밋), 지출·계정·약관 동의·외부 발송·시스템 보안 설정 변경(방화벽·화면 기록 권한 등은 소유자), `sudo`, LFS 에셋·데이터 삭제, 게임 설계·룩·조작감 판정.
- **GPU·GUI 공유**: UE 에디터 GUI·PIE·`-game`·패키지 실행 전에 `"$TMPDIR/claude/gui-foreground.lock"`을 확인하고 잡는다([mac-setup §3](../runbooks/mac-setup.md) 표의 규칙). 영록이 성능을 재는 동안에는 빌드·쿡·셰이더 컴파일을 하지 않는다. 두 UBT 빌드가 동시에 돌 때 서로 기다리는지·느려지는지는 [미확인]이다. 재환의 추론도 같은 GPU·통합 메모리를 쓰므로 **재환이 잰 fps·GPU ms는 판정 근거가 아니다**. 수치를 적을 때는 LM Studio 모델이 로드돼 있었는지 함께 적는다.
- **패키지 출력**: `GOLMOK_PKG_DIR`는 2026-11-28 현재 비어 있고 `package.sh` 기본값은 `<worktree>/build/Mac`이다. 재환은 항상 `--out-dir "$W/build/Mac"`를 명시한다.
- **증거**: 로그·재현 스크립트·출력은 `$TMPDIR/jaehwan/<과제 id>/`에 두고 병합 알림까지 지우지 않는다(규칙 10).
- **PR**: 제목 `J-NN: <요약>`. 본문의 절 순서, **"제출 전 점검표"**(그날 규칙 파일의 규칙마다 한 줄 — 한 일과 증거, 또는 "해당 없음"과 이유), 자리표시 분류, 끝 줄 서명(규칙 7)은 아래 "PR 본문 공통(모든 과제)"이 정한다(2026-11-28 문서 7: 옛 "규칙 1~16 한 줄씩"을 이 소절로 옮겼다). 점검표가 없으면 리뷰를 시작하지 않는다.
- **완료 보고**: CI 모든 행 초록 뒤에만(`gh pr checks <n>` 표, 규칙 2). 게시 뒤 본문을 다시 읽는다(규칙 12).
- **병합하지 않는다.** 병합은 영록이 한다.
- **`py` 뒤에는 `QUIT_EDITOR`**: 창 없는 에디터(`UnrealEditor-Cmd … -nullrhi`)에 `-ExecCmds="py …"`를 줄 때 끝 명령은 `QUIT_EDITOR`다. `Quit`로는 스크립트가 끝나도 에디터가 나가지 않는다(J-12b: 약 13 s에 스크립트가 끝났지만 1800 s 타임아웃 rc 124). 근거 [pc-setup.md](../runbooks/pc-setup.md) §2 "GUI 없이 하는 방법"의 창 없는 에디터 줄.
- **Mac 에디터 로그는 `~/Library/Logs/Unreal Engine/GolmokEditor/`**: 프로젝트 로그는 그 폴더의 `Golmok.log`다. `<project>/Saved/Logs/`는 2026-11-28 현재 `$W`에도 메인 체크아웃에도 없다. 에디터를 다시 띄우면 이전 로그는 같은 폴더의 `Golmok-backup-<시각>.log`가 되므로, 실행 직후 `Golmok.log`를 `$E`에 복사한 뒤 `grep`한다. `Saved/Automation/Report/index.json`은 예전처럼 프로젝트 아래에 생긴다([mac-setup §8 #14](../runbooks/mac-setup.md)).
- **상대 경로 명령은 `cd "$W" &&`로 시작**: 셸의 기본 cwd는 메인 체크아웃이다. `./tools/ue/…`·`unreal/Golmok/…`처럼 상대 경로를 쓰는 명령은 매번 `cd "$W" && …`로 시작한다(규칙 6).
- **커밋 작성자**: 커밋마다 `git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit …`. `git config`에 저장하지 않는다(메인 체크아웃과 다른 세션이 같은 설정을 읽는다).
- **명령마다 로그+exit**: 명령마다 `> $E/<이름>.log 2>&1; echo $? > $E/<이름>.rc`, 돌린 명령 원문은 `$E/commands.txt`에 한 줄씩 더한다(한 줄마다 `printf '%s\n' '…' >> "$E/commands.txt"` 하나, 명령 안의 `'`는 `'\''`로 바꿔 적는다, heredoc 금지, 적은 줄은 고치거나 지우지 않는다 — 규칙 19, 2026-11-28 문서 8; 자세한 것은 "PR 본문 공통" 머리의 **명령 기록**). 다음 실행이 덮어쓰는 결과물(`Saved/Automation/Report/index.json`, 에디터 `Golmok.log` 등)은 실행 직후 `$E`에 사본을 둔다(규칙 10).
- **`test.sh` 종료 코드(2026-11-28 메모, J-36 [#154](https://github.com/wooklym/golmok/pull/154) · `8ba637c`)**: 경고 있는 성공만 있는 실행(예: `--filter Golmok.Zone.IndexParse`)이 종료 코드 1이던 옛 규칙은 J-36이 고쳤다. 지금은 보고서 `failed`가 0이고 `succeeded`+`succeededWithWarnings`가 1 이상이면 0이고, 요약 줄 끝에 `Succeeded with warnings: <수>`가 나온다. 그래도 종료 코드 0은 "실패 없이 끝났다"일 뿐이다: 테스트마다 **완료 / skip**은 지금처럼 보고서 `entries`의 skip Info 문구(`… missing - skipped` 등)와 상태 열로 판정한다(규칙 15, mac-setup §4 "기대 결과" 3). J-36 전에 쓴 과제 글·결과의 "종료 코드 1은 경고 있는 성공 때문"이라는 문장은 그때의 기록이다(J-17·J-20).
- **배정 보류 표시**: 절 첫머리에 '배정 보류' 또는 '영록 보충이 남았다' 표시가 있는 과제는 시작하지 않고 다음 과제로 넘어가며 영록에게 한 줄로 알린다.
- **CI 반복 측정 중 `gh run watch`의 일시 오류(2026-11-28, J-11 attempt 6에서 정함)**: `gh run watch`가 0이 아닌 코드로 끝났고 그 로그에 `HTTP 5`가 있으면 잡 실패가 아니라 GitHub API의 일시 오류다. 그 attempt의 기록 단계로 넘어가지 않고, 그 잡의 상태를 `gh api repos/wooklym/golmok/actions/runs/$RUN/attempts/$n/jobs`의 `.jobs[].status`로 30초마다 읽어 `completed`가 될 때까지 기다린다(`/usr/bin/timeout 1800`을 붙이고, 명령과 종료 코드를 `$E/wait-$n.log`에 남긴다. `RUN`·`n`·`W`·`E`는 그 호출 안에서 다시 정의한다). 그 뒤 기록 단계부터 이어 간다. 그 잡의 결론이 `success`가 아니면 멈추고 묻는다. 기록 단계가 이미 일찍 돌아 빈 줄이나 스터브 로그가 남았으면 그 파일들을 `-before-fix` 사본으로 보존하고 기록 명령을 다시 돌려 채운다(값을 손으로 적지 않는다). `gh run watch`가 0으로 끝나도 성공이 아니다 — `--exit-status` 없이는 실패한 실행에도 0이다. 결론은 위 `.jobs[].conclusion`이나 `gh pr checks` 표로 본다("PR 본문 공통" 12, 2026-11-28 문서 9).
- **CI 감시의 등록 전 경합(2026-11-28, J-21 PR #160 리뷰 R160에서 정함)**: push 바로 뒤의 `gh pr checks --watch`·`gh run watch`는 그 커밋의 실행이 아직 등록되지 않아 `no checks reported`로 끝날 수 있다. 이것은 실패가 아니다. 첫 로그는 그대로 두고, 그 커밋의 두 실행(push·pull_request)이 목록에 나올 때까지 기다린다(하네스 백그라운드): `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/jaehwan/<과제 id>"; H=$(git -C "$W" rev-parse HEAD); cd "$W" && /usr/bin/timeout 600 sh -c 'until [ "$(gh run list --commit "$1" --json event --jq "[.[]|select(.event==\"push\" or .event==\"pull_request\")]|length")" -ge 2 ]; do sleep 30; done' sh "$H" > "$E/run-wait.log" 2>&1; echo $? > "$E/run-wait.rc"` — `W`·`E`는 그 호출 안에서 다시 정의한다(`E`는 과제 절 "명령 공통"의 앞머리 그대로), 기대 `run-wait.rc` `0`(0이 아니면 다시 돌리지 않고 멈추고 묻는다). 그 뒤 과제 절의 watch 명령을 로그 이름만 `-2`를 붙여(예: `checks-watch-2.log`·`checks-2.log`) 한 번 더 돌리고, 이후 `## CI`·완료 기준·멈춤 조건의 `checks.log`는 `checks-2.log`로 읽는다. 과제 절이 대기 절차를 따로 적었으면(J-23·J-24·J-25) 그 절을 따른다. 대기 절차가 없는 CI 감시(J-10·J-19·J-22·J-27·J-30a)에는 이 줄을 쓴다. 이때 그 과제 절의 인용·숫자 검사 대상 로그 목록의 `"$E"/checks.log`도 `"$E"/checks-2.log`로 읽는다.
- **다시 돌린 로그는 번호 접미사(2026-11-28, J-21 PR #160 리뷰 R160에서 정함)**: 과제 절이나 이 파일이 다시 돌리는 이름을 정하지 않은 명령을 다시 돌리면(실패·멈춤 뒤, 영록 지시로 다시 돌리는 명령 등) 그 로그에 번호를 붙인다(`<이름>-2.log`, `<이름>-3.log`, `.rc`도 같다). 그 경우 있는 `.log`·`.rc` 파일은 덮어쓰지도 지우지도 않는다. 예외 — 아래 "PR 본문 공통" 3·4·5·6·7의 검사, 과제 절의 게시 전 검사(사용자 경로 검사 `home-path.log`, 인용 검사 `body-quotes.txt`·`tsv-quotes.txt`·`quotes-missing.log`·`quotes-check.log`, 숫자 검사 `body-numbers.txt`·`numbers-check.log` — 본문을 고친 뒤 다시 돌리는 것), 과제 절이 "같은 명령을 다시 돌린다"·"한 번 더 돌린다"로 적은 명령(J-10 실행 목록 확인, J-27 멈춤 ①), 위 "`gh run watch`의 일시 오류" 줄의 기록 단계는 적힌 파일 이름 그대로 다시 쓰고, 완료 기준·멈춤 조건은 그 이름의 마지막 실행 값을 본다. PR 본문에는 인용한 값마다 몇 번째 실행의 파일인지(파일 이름) 적는다.
- **"모두·전부·첫 실행부터" 같은 말(2026-11-28, J-21 PR #160 리뷰 R160에서 정함)**: 이런 말은 `commands.txt`나 로그를 기록된 명령으로 센 뒤에만 점검표·본문에 쓴다. 세지 않았으면 센 범위를 쓴다(예: "N개 중 N개").
- **문서 9의 공통 동작(2026-11-28, R161·J-19 PR #163)**: 재환의 `task.txt`에는 과제 절과 아래 "PR 본문 공통(모든 과제)" 소절만 들어간다. 그래서 이번에 정한 것은 모두 그 소절에 두었다 — 3(규칙 5 감사 펜스 `common-timeout-awk`), 11(명령은 `task.txt`에서 복사, 뽑은 조각은 확인 && 실행 — 규칙 20), 12(CI 결론은 표·run API에서), 13(되돌림 커밋), 14(인용·숫자 검사의 꼴), 15(완료 기준은 충족·미충족 둘, 작업 트리 상태는 시작 때 기록과의 비교). 이 목록과 그 소절이 다르면 그 소절을 따른다.

### PR 본문 공통(모든 과제)

(2026-11-28 문서 7, Opus) 모든 과제의 PR 본문, 자리표시 분류, 런북 칸 자기 검사, 근거 표기는 이 소절이 정한다. 과제 절은 다음 **고정 문장** 하나로 이 소절을 가리킨다 — PR 본문·자리표시 분류·칸 자기 검사·근거 표기는 상시 규칙 "PR 본문 공통(모든 과제)"을 따른다(이 절과 다르면 그 소절을 따른다). 과제 절에는 과제마다 다른 것만 남는다: `## 결과`에 넣을 것, 인용·숫자 검사의 대상 로그 목록, 런북 줄을 넣는 명령, 커밋 2 명령. 아래 명령도 과제 절 "명령 공통"의 앞머리(`W=…; E=…;`)로 시작한다. 셸 변수는 호출 사이에 남지 않으므로, 한 줄에 적힌 명령은 한 호출로 돌린다. **명령 기록**(2026-11-28 문서 8, 규칙 19): 돌린 명령은 한 줄마다 `printf '%s\n' '<명령>' >> "$E/commands.txt"` 하나로 더한다. 명령 안의 작은따옴표 `'`는 모두 `'\''` 네 글자로 바꿔 적는다(예: `printf '%s\n' 'awk '\''NF {l = $0} END {print l}'\'' "$E/posted-body.md"' >> "$E/commands.txt"`는 `awk 'NF {l = $0} END {print l}' "$E/posted-body.md"` 한 줄을 적는다 — 바꾸지 않으면 따옴표가 닫혀 나머지가 명령으로 돈다). 적은 직후 `tail -n 1 "$E/commands.txt"`가 돌린 명령과 글자 그대로 같은지 보고, 다르면 그 줄을 고치지 않고 `# 정정:` 줄을 덧붙인다. heredoc을 쓰지 않고, 이미 적은 줄을 고치거나 지우지 않는다(`commands.txt`·증거 로그를 고치는 스크립트도 쓰지 않는다). 틀린 기록에는 `printf '%s\n' '# 정정: <줄 번호> — <내용>' >> "$E/commands.txt"` 한 줄을 덧붙인다.

1. **과제 절 뽑기(규칙 14·17 c)**: 과제 절의 할 일 1이 그 과제의 id를 넣은 명령을 글자 그대로 준다. 꼴은 이렇다: `git -C "$W" show origin/main:docs/plan/jaehwan-tasks.md > "$E/tasks-main.md"; git -C "$W" rev-parse origin/main > "$E/main-rev.log"; { awk '/^#### J-19 /{f=1} /^#### J-20 /{f=0} f' "$E/tasks-main.md"; awk '/^### PR 본문 공통\(모든 과제\)$/{f=1} /^## 리뷰·병합 절차$/{f=0} f' "$E/tasks-main.md"; } > "$E/task.txt"`. 기대: `head -1 "$E/task.txt"`가 과제 절 제목, `grep -c -x '### PR 본문 공통(모든 과제)' "$E/task.txt"` `1`. 규칙 17 c의 "main 리비전"은 `task.txt` 첫 줄이 아니라 `main-rev.log`에 둔다(과제 절의 `head -1` 기대를 지키려고). 펜스 `common-ph-awk`(아래 5)는 과제 절의 펜스 추출 목록에 `"common-ph-awk ph.awk"`로 들어 있다.
2. **절 순서**: 절 제목은 모두 `## `로 시작하고 아래 글자 그대로다. `## 요약` · `## 바뀐 파일` · `## 결과`(과제 절이 정한 것만) · `## 완료 기준 대조`(`task.txt`의 "완료 기준" 부분을 물결 펜스 `~~~` 블록에 그대로 붙이고, 블록 아래에 (a)부터 한 줄씩 충족 + 증거 파일, 또는 **미충족** + 이유) · `## 실행한 명령`(`$E/commands.txt`를 백틱 펜스 블록에 그대로. 과제 절이 더 붙이라는 파일도 이 절의 백틱 펜스 블록에. `commands.txt`가 200줄을 넘으면 그 펜스 바로 앞에 `<details>` 한 줄, 바로 뒤에 `</details>` 한 줄을 둔다. **크기**(2026-11-28 문서 8, PR #159): 본문에 통째로 붙이는 로그는 이 `commands.txt`와, 과제 절이 본문에 그대로(원문·전체) 넣으라고 이름을 든 파일뿐이다. 그 밖의 로그는 통째로 붙이지 않는다. 이 절의 펜스 밖 끝에는 과제 절이 '본문에 붙이지 않는다'고 이름을 든 로그와 `## 결과`에서 일부만 인용한 로그만 `- <파일 이름>: <줄 수>줄`처럼 파일 이름과 줄 수를 한 줄씩 적는다(`$E`의 모든 파일을 나열하지 않는다) — 줄 수는 `wc -l < "$E/<파일 이름>" | tr -d ' ' > "$E/<파일 이름>-lines.log"`로 남긴 값을 옮긴다(규칙 10 — 화면에만 찍힌 수를 쓰지 않는다)) · `## CI`(모든 행이 끝난 뒤의 `"$E/checks.log"`를 백틱 펜스 블록에 그대로) · `## 남은 [미확인]` · `## 병합 시 반영`(없으면 "없음") · `## 제출 전 점검표`(아래 3) · `## 자리표시 분류`(아래 6이 만든 표) · 서명 줄 `작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)`. 서명 줄이 본문의 **마지막 비지 않은 줄**이다(규칙 7 — `gh`가 게시본 끝에 빈 줄 하나를 붙이므로 6의 다시 읽기는 마지막 비지 않은 줄을 본다). `## 요약`부터 `## 제출 전 점검표`까지가 초안 `"$E/pr-body.md"`이고, 마지막 두 부분(`## 자리표시 분류`와 서명 줄)은 초안에 쓰지 않는다 — 6의 명령이 붙인다. 쓰는 순서(규칙 2·18): PR은 과제 절의 명령으로 "CI 진행 중 — 결과는 아래에 추가"만 든 첫 본문으로 연다(첫 본문은 정확히 그 한 문장 한 줄이다 — 과제 절의 `printf '%s\n' 'CI 진행 중 — 결과는 아래에 추가' > "$E/pr-body-initial.md"` 그대로 쓰고, 다른 줄·설명·점검표·"CI 뒤에 채운다" 같은 문장을 더하지 않는다. 2026-11-28 문서 9에서 다시 적음. 예외: 문서 9 전에 시작한 J-22는 그때 뽑은 `task.txt`의 PR 열기 명령 그대로 쓴다) → 마지막 push의 CI가 모든 행에서 끝나 `checks.log`가 생긴 뒤에 초안을 쓴다 → `## 제출 전 점검표`는 맨 마지막에 쓴다 → 과제 절의 인용·숫자 검사 → 아래 3·5·6.
3. **제출 전 점검표**: 그날의 규칙 파일에 있는 규칙마다 한 줄, `- 규칙 7: 커밋 두 개를 재환 작성자로 만들었다 — author-c1.log·author-c2.log`처럼 `- 규칙 <번호>: `로 시작하고 과거형 문장과 증거 파일을 적는다(규칙 18: 줄마다 그 증거 파일을 `ls -l`·`cat`으로 연 뒤에 쓴다. 파일이 없으면 "아직 안 함"이라고 쓴다). 규칙 수와 줄 수 대조: `ls -d "$HOME"/.claude/projects/*golmok/memory/jaehwan-working-rules.md > "$E/rules-path.log" 2>&1; wc -l < "$E/rules-path.log" | tr -d ' ' > "$E/rules-path-count.log"; grep -c -E '^[0-9]+\. \*\*' "$(head -n 1 "$E/rules-path.log")" > "$E/rule-count.log"; awk '/^## 제출 전 점검표$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | grep -c -E '^- 규칙 [0-9]+: ' > "$E/checklist-lines.log"; diff "$E/rule-count.log" "$E/checklist-lines.log" > "$E/checklist.diff"; echo "exit=$?" >> "$E/checklist.diff"` — 기대 `rules-path-count.log` `1`, `checklist.diff` `exit=0` 한 줄(2026-11-28 문서 9 현재 규칙 수는 21 — R159 뒤 규칙 19, J-19 PR #163 리뷰 뒤 규칙 20·21이 더해졌다. 점검표 줄 수는 이 숫자가 아니라 그날 규칙 파일에서 센 `rule-count.log`에 맞춘다). **규칙 5 줄(규칙 5의 R161 확장, 2026-11-28 문서 9)**: 이 줄은 기억이 아니라 센 수로 쓴다. 점검표를 쓰기 직전에, 아래 감사 펜스 `common-timeout-awk`를 뽑아 줄 수와 첫 줄을 확인한 같은 호출에서 돌린다(11 — 규칙 20): `awk -v n=common-timeout-awk 'BEGIN {b = sprintf("%c%c%c", 96, 96, 96)} x && $0 == b {x = 0} x {print} !x && index($0, b) == 1 && $0 ~ (" " n "$") {x = 1}' "$E/task.txt" > "$E/timeout.awk"; [ "$(wc -l < "$E/timeout.awk" | tr -d ' ')" = "10" ] && head -n 1 "$E/timeout.awk" | grep -q '^# 규칙 5 감사' && { grep -n -c 'timeout' "$E/commands.txt" > "$E/timeout-count.log"; awk -f "$E/timeout.awk" "$E/commands.txt" > "$E/timeout-audit.log"; }; echo $? > "$E/timeout-audit.rc"` — 기대 `timeout-audit.rc` `0`, `timeout-audit.log` 끝 두 줄이 `wrapped_lines`·`not_wrapped_lines`와 수. 감사는 `commands.txt`에서 `git fetch`·`git push`(`git -C "$W"` 꼴 포함)·`gh `+낱말·`pytest`·`curl `·`until `이 든 줄을 줄 번호마다 `/usr/bin/timeout `이 있는 무리(`wrapped`)와 없는 무리(`not-wrapped`, 명령 원문 함께)로 나누고, `#`로 시작하는 줄(정정)과 이 감사 자신의 기록 줄(`timeout-audit.log`가 든 줄)은 세지 않는다. 한 줄에 감싼 명령과 감싸지 않은 명령이 함께 있으면 그 줄은 `wrapped`로 세므로, 그런 줄은 점검표 줄에 따로 적는다(열린 절은 그런 줄을 만들지 않게 적었다 — 문서 9에서 CI 표 명령에도 `/usr/bin/timeout 120`). 점검표의 규칙 5 줄은 `timeout-audit.log`의 두 수를 그대로 옮기고, `not-wrapped` 줄마다 과제 절이 그 명령을 시간 한도 없이 적었다는 근거(그 절 "명령 공통"의 시간 한도 문장, 또는 아래 6의 `gh pr edit`·`gh pr view`)를 줄 번호와 함께 적는다 — `git fetch`·`git push`·`gh` 호출은 네트워크를 쓰므로 "바로 끝나는 로컬 명령"으로 적지 않는다. 과제 절에 자기 감사 펜스가 있으면(J-30b `j30b-timeout-awk`) 그 펜스를 쓴다. dry-run(문서 9): 견본 `commands.txt` 12줄(감싼 줄·안 감싼 줄·`# 정정:` 줄·감사 자신의 줄)에서 sh·zsh 같은 출력 — `not-wrapped` 4줄(`git -C "$W" fetch`·`gh pr create`·`git -C "$W" push`·`gh pr edit`), `wrapped` 4줄, `# 정정:` 줄과 감사 줄은 세지 않음.
4. **펜스 밖에 쓰지 않는 글자**: 5의 분류는 펜스 블록 밖(설명 문장, 대조 줄, 점검표, `## 남은 [미확인]`, `## 병합 시 반영`)의 `<`…`>`, `[]`, `TODO`·`TBD`·`XXX`·`placeholder`(대소문자 무시)를 모두 "미채움"으로 센다. 그래서 펜스 밖에서는 ① 과제 글의 표기(`<n>`·`<k>`·`<파일>`·`<번호>`)를 실제 이름으로 쓴다(예: `lock-refresh-pkg.rc`·`lock-refresh-run.rc`, `load-before.log`·`load-after.log`, `make_ref.py`). ② 부등호는 "이하·이상·초과·미만"으로 쓴다. ③ 규칙 12 줄과 완료 기준 대조의 공통 완료 기준 (P) 줄(J-19 (h), J-22 (i), J-23 (i), J-24 (i), J-25 (k), J-29 (h), J-30a (i), J-30b (i); 끝난 J-10 (k)·J-11 (i)·J-21 (h)와 재환 과제에서 닫은 J-27 (i)도 같은 꼴이었다 — 정정 2026-11-28 문서 8: 옛 "J-23 (P)"는 설계 확정 전 보충의 표기였다; 문서 9에서 J-29·J-30b를 더하고 J-10·J-27을 옮겼다)은 처음에 `- 규칙 12: 자리표시 분류는 아직 안 함 — ph-unfilled.log`와 `- (k) 공통 완료 기준 (P): 아직 안 함 — checklist.diff·ph-unfilled.log`(괄호 글자는 그 과제의 것)로 쓴다. 3이 `checklist.diff` `exit=0`, 5가 `ph-unfilled.log` `0`을 낸 뒤 그 두 줄만 다음 고정 문장으로 바꾸고 3·5를 한 번 더 돌린다(기대 같음). 규칙 12 줄: `- 규칙 12: 초안의 자리표시 분류 미채움이 0이었다 — ph-unfilled.log. 게시본 다시 읽기는 게시 뒤의 일이라 이 본문 밖(완료 보고 메시지)의 몫이다`. (P) 줄: `- (k) 초안 부분 충족 — checklist.diff exit=0, ph-unfilled.log 0. pr-edit.rc·ph-posted-unfilled.log·ph-table.diff·signature-last.log는 이 본문을 게시한 뒤에 생기는 파일이라 본문에 쓰지 않는다(완료 보고 메시지의 몫)`. ④ 꺾쇠 안의 전자우편 주소(`재환 <jaehwan.local@localhost>`)는 세지 않으므로 그대로 써도 된다. ⑤ 로그 원문은 `## 결과`·`## CI`의 백틱 펜스 블록 안에 둔다. 펜스 블록 안의 원문·명령은 고치지 않는다.
5. **자리표시 분류(규칙 12, 기계적)**: 펜스 `common-ph-awk`(아래)가 줄마다 걸린 글자를 분류한다. `## 완료 기준 대조`의 `~~~` 블록 안 = 원문 인용, `## 실행한 명령`의 펜스 블록 안 = 명령 기록, `## 결과`·`## CI`의 펜스 블록 안 = 로그 원문, 그 밖(펜스 밖, 다른 절의 펜스, 닫히지 않은 펜스) = 미채움이다. 꺾쇠 안의 전자우편 주소와 `<details>`·`</details>`만 있는 줄은 세지 않는다. 블록 안의 `## ` 줄은 절을 바꾸지 않는다. 초안 분류: `awk -v table="$E/ph-table.md" -f "$E/ph.awk" "$E/pr-body.md" > "$E/ph.tsv"; awk -F'\t' '$2=="미채움"' "$E/ph.tsv" | wc -l | tr -d ' ' > "$E/ph-unfilled.log"` — 기대 `ph-unfilled.log` `0`. `ph.tsv`의 열은 `pr-body.md`의 줄 번호 · 분류 · 걸린 글자다. 0이 아니면 그 줄 번호의 줄만 4대로 고친다(빈 자리는 채우고, 자리표시가 아닌 글자는 바꾼다). 그다음 같은 명령을 다시 돌린다. 두 번 고쳐도 0이 아니면 멈춘다. 펜스 안의 원문이 미채움으로 잡혀도 멈춘다(그 펜스가 2의 절 밖에 있다는 뜻이다). `ph-table.md`는 분류 4행의 개수 표이고, 걸린 글자는 표에 옮기지 않는다. 그 표의 줄에는 걸리는 글자가 없다.
6. **조립·게시·다시 읽기**: 조립 `{ cat "$E/pr-body.md"; printf '\n## 자리표시 분류\n\n'; cat "$E/ph-table.md"; printf '\n%s\n' '작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)'; } > "$E/pr-body-final.md"`. 게시 `cd "$W" && gh pr edit "$(cat "$E/pr-number.log")" --body-file "$E/pr-body-final.md" > "$E/pr-edit.log" 2>&1; echo $? > "$E/pr-edit.rc"` — 기대 `0`. 다시 읽기(규칙 12) `cd "$W" && gh pr view "$(cat "$E/pr-number.log")" --json body --jq .body > "$E/posted-body.md"; awk -v table="$E/ph-posted-table.md" -f "$E/ph.awk" "$E/posted-body.md" > "$E/ph-posted.tsv"; awk -F'\t' '$2=="미채움"' "$E/ph-posted.tsv" | wc -l | tr -d ' ' > "$E/ph-posted-unfilled.log"; diff "$E/ph-table.md" "$E/ph-posted-table.md" > "$E/ph-table.diff"; echo "exit=$?" >> "$E/ph-table.diff"; awk 'NF {l = $0} END {print l}' "$E/posted-body.md" | grep -c -x -F '작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)' > "$E/signature-last.log"` — 기대 `ph-posted-unfilled.log` `0`, `ph-table.diff` `exit=0` 한 줄, `signature-last.log` `1`(서명 줄이 게시본의 **마지막 비지 않은 줄**이다. 정정 2026-11-28 문서 8: 처음 쓴 `tail -n 1` 검사는 `gh`가 게시본 끝에 붙이는 빈 줄 하나를 읽어 서명이 끝에 있어도 `0`을 냈다 — PR #159의 게시본에서 `tail -n 1`은 빈 줄이었다. dry-run: 끝에 빈 줄이 없는 견본·빈 줄 하나가 있는 견본 모두 `1`, 서명 뒤에 다른 줄이 있는 견본 `0`, #159 게시본 `1`). 본문을 다시 고치면 3·5·6을 처음부터 다시 돌린다. 게시 뒤 네 값(`pr-edit.rc`·`ph-posted-unfilled.log`·`ph-table.diff`·`signature-last.log`)은 `cat` 출력 그대로 완료 보고 메시지에 넣고, 이 네 값 때문에 본문을 다시 고치지 않는다(규칙 12·18).
7. **런북 칸 자기 검사(규칙 17 b)**: 런북에 줄을 넣거나 고친 직후마다(커밋 1 전, 커밋 2의 바꾸기 뒤) 과제 절이 그 런북 파일과 번호(`1`·`2`)를 넣어 주는 이 꼴의 명령을 돌린다: `cd "$W" && git diff -U0 origin/main -- docs/runbooks/pc-verify-v17.md | grep '^+[^+]' > "$E/cell-lines-1.txt"; wc -l < "$E/cell-lines-1.txt" | tr -d ' ' > "$E/cell-lines-1-count.log"; grep -n -E '\.log|영록|R[0-9]{3}' "$E/cell-lines-1.txt" > "$E/cell-grep-1.log"; wc -l < "$E/cell-grep-1.log" | tr -d ' ' > "$E/cell-grep-1-count.log"`. 기대: `cell-lines-<번호>-count.log`가 과제 절이 적은 더한 줄 수(0이면 빈 검사라 멈춘다, 규칙 15), `cell-grep-<번호>-count.log` `0`. 예외는 없다(규칙 17 b). 손으로 쓴 칸에서 0이 아니면 걸린 글자(로그 이름, 로그 원문 조각)를 칸에서 빼고, 그 원문은 PR 본문 `## 결과`의 백틱 펜스 블록에 둔 뒤 같은 명령을 다시 돌린다(규칙 10 g). 펜스 스크립트가 만든 줄에서 0이 아니면 그 줄을 손으로 고치지 않고 멈춘다.
8. **근거 표기**: 런북 칸·줄은 `근거: PR #<번호>.`로 끝난다(J-15 #151, J-20 #153의 꼴). 임시 로그 이름·`$TMPDIR` 경로·과정 문구("영록", 리뷰 id)는 칸에 쓰지 않는다. 펜스 스크립트는 줄 끝을 `근거: J-<과제 번호> PR.` 표식으로 만들고, `gh pr create`로 번호가 나온 뒤 **커밋 2**가 그 표식을 `근거: PR #<번호>.`로 바꾼다(과제 절의 커밋 2 명령, 그 뒤 7의 번호 `2` 검사, 게이트 다시(규칙 13), push, CI). 이 Mac에서 잰 시간 수치를 칸에 쓰면 "시간(참고값 — 로컬 LLM 추론 부하가 있는 상태)"을 붙인다.
9. **멈춤 조건(공통)**: `rules-path-count.log`가 `1`이 아닐 때, `checklist.diff`가 `exit=0` 한 줄이 아닐 때, 5의 두 번 고친 뒤에도 `ph-unfilled.log`가 `0`이 아닐 때, `pr-edit.rc`가 `0`이 아닐 때, `ph-posted-unfilled.log`·`ph-table.diff`·`signature-last.log`(6의 마지막 비지 않은 줄 검사 — `tail -n 1`로 다시 세지 않는다)가 기대와 다를 때, 7의 두 값이 기대와 다를 때. `checks-watch.log`에 `no checks reported`가 있을 때는 멈추지 않는다 — 상시 규칙 "CI 감시의 등록 전 경합"의 등록 대기와 `-2` 로그로 이어 간다(그 대기의 `run-wait.rc`가 0이 아니면 멈춘다). 대기 명령(하네스 백그라운드, 앞머리 `W=…; E=…;` 뒤): `H=$(git -C "$W" rev-parse HEAD); cd "$W" && /usr/bin/timeout 600 sh -c 'until [ "$(gh run list --commit "$1" --json event --jq "[.[]|select(.event==\"push\" or .event==\"pull_request\")]|length")" -ge 2 ]; do sleep 30; done' sh "$H" > "$E/run-wait.log" 2>&1; echo $? > "$E/run-wait.rc"` — 기대 `0`. 그 뒤 과제 절의 watch 두 명령을 `checks-watch-2.log`·`checks-2.log`로 한 번 더 돌린다(과제 절이 대기 절차를 따로 적었으면 그 절을 따른다).
10. **공통 완료 기준 (P)**: `checklist.diff` `exit=0`(점검표 줄 수 = 그날의 규칙 수), `ph-unfilled.log` `0`, `pr-edit.rc` `0`, `ph-posted-unfilled.log` `0`, `ph-table.diff` `exit=0`, `signature-last.log` `1`(마지막 비지 않은 줄이 서명 줄 — 6), 런북을 쓰는 과제는 `cell-grep-1-count.log`·`cell-grep-2-count.log` `0`. (게시 뒤 네 값은 본문이 아니라 완료 보고 메시지로 확인한다.)
11. **명령은 `task.txt`에서 복사한다(규칙 20, 2026-11-28 문서 9 — J-19 PR #163)**: 돌리는 명령은 `task.txt`의 글자에서 복사하고, 끝에 붙는 기록 꼴(`; echo "exit=$?" >> "$E/<이름>.diff"`, `; echo $? > "$E/<이름>.rc"`)을 손으로 치지 않는다(J-19: 손으로 친 `diff-exit=$?`가 `pkgcheck.diff`의 끝 줄을 바꿔, 그 줄을 `exit=0`으로 읽는 다음 펜스 스크립트가 rc 3으로 멈췄다). 돌리기 전에 그 끝 부분을 로그 이름까지 넣어 센다: `grep -c -F -- '<끝 부분>' "$E/task.txt" > "$E/suffix-<이름>.log"` — 기대 `1` 이상(같은 끝 부분이 절과 이 소절에 여러 번 적혀 있으면 2 이상도 맞다). `0`이면 `task.txt`에 없는 글자를 친 것이니 돌리지 않고 복사를 다시 한다. 뽑은 조각(펜스 스크립트·명령 줄)은 그 조각이 기대 줄 수이고 기대 명령으로 시작하는지 확인한 **같은 호출에서만** 실행한다: `[ "$(wc -l < "$E/<조각>" | tr -d ' ')" = "<줄 수>" ] && head -n 1 "$E/<조각>" | grep -q '^<기대 첫 글자>' && sh "$E/<조각>" …` — 펜스 스크립트는 `sh`로, 한 줄 명령 조각은 규칙 20의 꼴(`… && eval "$(cat "$E/<조각>")"`)로 같은 호출에서 돌린다. `eval`하지 않는 것은 `commands.txt`의 기록 줄이다. 확인이 실패하면 돌리지 않고 조각을 열어 본다(J-19: 과제 글에서 잘못 뽑힌 2~3줄 조각을 먼저 돌려 `command not found`가 세 번 났다). 기록 파일을 `eval`해 실행하는 장치는 쓰지 않는다 — 기록은 머리의 **명령 기록**대로 `printf` 한 줄이고, 실행은 그 명령을 따로 한 번 돌리는 것이다(J-19: 기록 뒤 `eval`이 두 명령을 같은 이름으로 다시 돌려 첫 결과 파일을 덮어썼다).
12. **CI 결론은 표에서(2026-11-28 문서 9, R161)**: `gh run watch`는 `--exit-status`를 주지 않으면 실패한 실행에도 종료 코드 0으로 끝난다. `gh pr checks --watch`의 종료 코드도 결론으로 쓰지 않는다. 결론은 `gh pr checks <번호>` 표(`checks.log` — 행이 1 이상이고 모든 행의 둘째 칸이 `pass`)나 run API의 `conclusion`(`gh run view <실행> --json conclusion --jq .conclusion`, `gh api repos/wooklym/golmok/actions/runs/<실행>/attempts/<n>/jobs`의 `.jobs[].conclusion`이 `success`)으로만 읽는다. watch 로그 끝의 `exit=` 줄은 기록이다. 과제 절이 watch의 `exit=0`을 성공으로 적은 곳이 있으면 이 항목을 따른다(명령은 적힌 그대로 두고 판정만 표·API로 한다).
13. **되돌림 커밋(2026-11-28 문서 9, R161 — J-10 커밋 4)**: 과제가 앞 커밋을 되돌리라고 하면 바로 커밋하는 `git revert --no-edit`를 쓰지 않는다. 먼저 기대 파일 목록을 적고(`printf '%s\n' <허용 파일> > "$E/revert-expected.txt"` — 과제 절이 준 파일 이름을 그 순서로, 한 줄에 하나), 한 호출로: `cd "$W" && git revert --no-commit <되돌릴 커밋> > "$E/revert.log" 2>&1; echo $? > "$E/revert.rc"; git -C "$W" diff --cached --name-only > "$E/revert-files.log"; [ "$(cat "$E/revert.rc")" = 0 ] && cmp -s "$E/revert-files.log" "$E/revert-expected.txt" && git -C "$W" -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "<제목>" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/revert-commit.log" 2>&1; echo $? > "$E/revert-commit.rc"` — `<되돌릴 커밋>`·`<허용 파일>`·`<제목>`은 과제 절이 준 글자다. 기대 `revert.rc`·`revert-commit.rc` `0`, `revert-files.log`가 `revert-expected.txt`와 같다(규칙 6·7·19 d), 그 뒤 `git -C "$W" log -1 --format='%an <%ae>'`가 `재환 <jaehwan.local@localhost>`. 확인이 막아 `revert-commit.rc`가 `1`이면 인덱스를 고치거나 되돌리지 않고 멈춰 `revert-files.log`를 보낸다.
14. **인용·숫자 검사의 꼴(규칙 10 e·f, 2026-11-28 문서 9)**: 과제 절의 게시 전 검사는 **항목마다 한 행**을 쓴다 — 인용은 `quotes.tsv`의 행마다 `<세기><탭><파일><탭><문자열>`(`quotes-check.log`), 숫자는 `## 결과` 펜스 밖의 두 자리 이상 숫자마다 `<세기><탭><숫자>`(`numbers-check.log`). 세기 0인 행이 없어야 한다(0이면 고치거나 지우고 다시 센다). 세는 곳은 과제 절이 고정한 근거 로그 목록뿐이다. `commands.txt`(명령 기록)·`task.txt`·`tasks-main.md`(과제 글)·본문 초안·게시본·검사가 만든 파일(`body-quotes.txt`·`body-numbers.txt` 등)·과제가 만든 덤프와 기대값 파일은 **다른 부류**다 — 근거 로그가 아니므로 목록에 넣지 않고, 그 안에서 찾은 것을 증거로 쓰지 않는다(명령이나 기대값에 그 숫자가 적혀 있다는 것은 출력이 아니다). 백틱이 든 검사 명령은 과제 절의 펜스 스크립트(`<과제>-bodycheck-sh` 등)에 있다 — 펜스 밖 글에서 손으로 옮기지 않는다(펜스 밖 백틱은 펜스 뽑기와 글자 복사를 깨뜨린다, J-19).
15. **완료 기준은 충족·미충족 둘뿐(2026-11-28 문서 9, R163)**: `## 완료 기준 대조`의 줄마다 **충족** + 증거 파일, 또는 **미충족** + 이유다. "부분 충족"·"나중에"·"완료 보고로 보낸다" 같은 셋째 상태를 쓰지 않는다(예외는 4 ③의 고정 (P) 줄 하나 — 그 문장은 정해진 글자다). 게시 전 검사(인용·숫자·사용자 경로)는 게시 전에 돈 것이므로 결과와 함께 과거형으로 쓴다. "작업 트리가 깨끗하다"·"`status --porcelain` 빈 출력" 같은 기준은 할 일 1에서 남긴 `status-before.log`와의 비교로 읽는다: `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-<이름>.diff"; echo "exit=$?" >> "$E/status-<이름>.diff"` — 기대 `exit=0` 한 줄(시작 전부터 있던 `??` 줄은 남아 있어도 된다 — 앞 과제의 생성물일 수 있다). 과제 절이 허용 파일 변경을 기대하는 단계는 그 절의 `grep -v -x -F` 꼴을 그대로 쓴다. 과제 절의 옛 "빈 출력" 기대가 시작 전 `??` 줄 때문에 맞지 않으면 이 비교를 돌려 그 출력으로 충족·미충족을 쓴다.

```text common-ph-awk
# 자리표시 분류(상시 규칙 "PR 본문 공통"). usage: awk -v table=<표 파일> -f ph.awk <본문 파일>
# stdout: 줄 번호 TAB 분류 TAB 걸린 글자. table 파일: 분류마다 개수(4행 고정).
function hit(tok) { print NR "\t" cls "\t" tok; n[cls]++ }
BEGIN { n["원문 인용"] = 0; n["명령 기록"] = 0; n["로그 원문"] = 0; n["미채움"] = 0 }
{
  t = substr($0, 1, 3)
  if (fence == "" && (t == "```" || t == "~~~")) { fence = t; fsec = sec; next }
  if (fence != "" && t == fence && $0 ~ /^(```|~~~)[ \t]*$/) { fence = ""; next }
  if (fence == "" && $0 ~ /^## /) sec = $0
  if (fence == "" && ($0 == "<details>" || $0 == "</details>")) next
  if (fence == "") cls = "미채움"
  else if (fsec == "## 완료 기준 대조" && fence == "~~~") cls = "원문 인용"
  else if (fsec == "## 실행한 명령") cls = "명령 기록"
  else if (fsec == "## 결과" || fsec == "## CI") cls = "로그 원문"
  else cls = "미채움"
  s = $0
  gsub(/<[^<> @]+@[^<> @]+>/, "", s)
  r = s
  while (match(r, /<[^<>]+>|\[\]/)) { hit(substr(r, RSTART, RLENGTH)); r = substr(r, RSTART + RLENGTH) }
  low = tolower(s)
  split("todo tbd xxx placeholder", w, " ")
  for (i = 1; i <= 4; i++) {
    r = low
    while ((k = index(r, w[i])) > 0) { hit(w[i]); r = substr(r, k + length(w[i])) }
  }
}
END {
  if (fence != "") { cls = "미채움"; hit("(닫히지 않은 펜스)") }
  if (table != "") {
    print "| 분류 | 개수 |" > table
    print "|---|---|" > table
    print "| 원문 인용 | " n["원문 인용"] " |" > table
    print "| 명령 기록 | " n["명령 기록"] " |" > table
    print "| 로그 원문 | " n["로그 원문"] " |" > table
    print "| 미채움 | " n["미채움"] " |" > table
  }
}
```

```awk common-timeout-awk
# 규칙 5 감사(상시 규칙 "PR 본문 공통" 3, 문서 9). usage: awk -f timeout.awk commands.txt
# stdout: 줄 번호 TAB wrapped, 또는 줄 번호 TAB not-wrapped TAB 명령. 끝에 개수 두 줄.
# 세지 않는 줄: # 로 시작하는 줄(정정), 이 감사 자신의 기록 줄(timeout-audit.log가 든 줄).
/^#/ { next }
/timeout-audit\.log/ { next }
/git (-C "[$]W" )?(fetch|push)|gh [a-z]|pytest|curl |until / {
  if (index($0, "/usr/bin/timeout ") > 0) { w++; print NR "\twrapped" }
  else { u++; print NR "\tnot-wrapped\t" $0 }
}
END { print "wrapped_lines " w + 0; print "not_wrapped_lines " u + 0 }
```

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
| J-18 | V-17 §3 Full Precision UV 헤드리스 Mac 부분 선행(pc-verify-v17 §7 §3 행) + mac-recon #23 칸: 기대 줄 `2/2 chunks (2 set, 0 already on)`·`8 assets, 0 warnings` 원문 일치, `WARNING cleanup` 0건, 청크 메시 2 `use_full_precision_u_vs=True`, `zi.run` 3.93 s(참고값, 추론 부하 있음), GUI 체크박스는 [미확인] | [#156](https://github.com/wooklym/golmok/pull/156) · `c968c6c` | [R156](https://github.com/wooklym/golmok/pull/156#issuecomment-7232319968)(1회 보류: 칸의 임시 로그 이름·진행 문구·시간 조건 — 규칙 10·16) → R156-2(영록 직접 대조: 엔진 로그·`import_result.json`·rc) |
| J-35 | add-gasp 편집기 가드의 남은 분기 스텁 사례(GASP 프로젝트 일치·음성 2종): `tools/tests/test_ue_mac_scripts.py`에 새 스텁 테스트 3개, 추가만 47줄, `-k add_gasp` 11 passed·파일 48 passed | [#157](https://github.com/wooklym/golmok/pull/157) · `ff77ba8` | [R157](https://github.com/wooklym/golmok/pull/157#issuecomment-7232574198)(1회 보류: 코드는 통과, 본문이 아직 하지 않은 일을 과거형으로 적음 — 규칙 2·12, 규칙 18 추가) → R157-2(영록 본문 확인) |
| J-11 | CI에 리뷰 뷰어 헤드리스 스모크 잡 `viewer-smoke (ubuntu-24.04)`(`ci.yml` 끝 `[J-11 hook]` 블록 37줄, `tools/viewer/README.md` 한 문장). 같은 커밋에서 잡 attempt 1~8이 모두 success | [#159](https://github.com/wooklym/golmok/pull/159) · `366e118`(head `c93474a`) | [R159](https://github.com/wooklym/golmok/pull/159#issuecomment-7233593303)(Opus 재현 검증 2렌즈: 워크플로 변경은 통과 — 추가 줄이 과제 펜스와 바이트 일치, attempt 1~8을 GitHub API로 직접 대조, 경고·재시도 0건; 본문이 명령 기록 사고를 줄여 적음 — 규칙 10·15·16, 규칙 19 추가) → R159-2(영록 본문 확인). attempt 6은 `gh run watch`의 GitHub API HTTP 500으로 기록 단계가 일찍 돌았고(잡은 성공), 영록 승인으로 기록을 보존한 뒤 다시 채웠다 |
| J-21 | WP-16a §12 컴파일·심볼 행(#1·#2·#3·#4·#15·#17) Mac 부분 선행: pc-verify-wp16a §12 표 아래 한 줄(+2 −0) — touch 증분 `build.sh`에서 두 파일 컴파일·dylib 링크·`Result: Succeeded`·경고 0·Niagara 줄 0, `otool -L` Niagara 한 줄, PIE·에셋이 필요한 절반은 [미확인] | [#160](https://github.com/wooklym/golmok/pull/160) · `37b6af8`(head `8232077`) | R160(Opus 검증 2렌즈, 첫 제출 병합 — 병합 커밋 본문에 기록, PR 코멘트 없음). 남은 지적(점검표의 넓게 쓰인 세 줄, 정정 줄 하나)은 재환에게 통보 |
| J-10 | CI shellcheck 잡 `shellcheck`(공식 v0.11.0 고정·sha256 확인, `--severity=warning`, `ci.yml` 끝 `[J-10 hook]` 블록 +30줄) + `tools/ue/common.sh` SC2034 지시문 4줄(스크립트 본문 그대로). 커밋 1·3은 의도한 빨강, 같은 커밋 attempt 8회 success | [#161](https://github.com/wooklym/golmok/pull/161) · `acbd954`(head `5bf3128`) | R161(Opus 재현: 코드·CI 통과 — 훅 블록이 과제 펜스와 바이트 일치, 스크립트 본문은 지시문 4줄 말고 그대로, 커밋 1·3 의도한 빨강, 8회 attempt success; 본문은 점검표의 틀린 규칙 5 줄 등으로 보류 — 작업 규칙 5의 R161 확장) → R161-2(영록: 고친 본문을 명령 기록과 대조). 병합 커밋 본문에 기록, PR 코멘트 없음 |
| J-19 | V-17 §5 ③ 패키지 quinn 전환 로그 확인(Mac) — pc-verify-v17 §7 아래 한 줄 | [#163](https://github.com/wooklym/golmok/pull/163) · `f7a924d`(head `125cda5`) | R163(1회 보류: 본문의 사고 축소·손으로 친 끝 붙임·확인 없는 조각 실행·"부분 충족" — 규칙 10·14·18·19, 규칙 20·21 추가) → R163-2 |

**진행 중**

| id | 과제 | 브랜치 | 허용 파일 |
|---|---|---|---|
| J-22 | V-16 §11 Mac 패키지 명령 이식(에셋 전 기대 결과) | `local/jaehwan-j22-v16-pkg`(재환 worktree가 이 브랜치, 2026-11-28 16:39 KST 현재 push·PR 없음) | `docs/runbooks/pc-verify-wp16a.md`(§13 표 아래 J-20 줄 다음 한 줄) |

**다음**(2026-11-28 문서 9): J-22(진행 중 — `local/jaehwan-j22-v16-pkg`, push·PR 전) → **J-29**(설계 확정 — 크래시 리포트 무인 업로드 끄기, 아래 J-29 절; J-22가 push돼 `$W`에 추적 파일 변경이 없을 때, 다음 UE 과제들보다 먼저. 2026-11-28 14:37 J-27 실행의 크래시 리포트가 CrashReportClient로 Epic에 올라갔다 — 아래 J-27 절) → J-30a → J-23 → J-25(J-22 병합 뒤 — 할 일 1 `pre.log`가 막는다) → J-24 → J-30b(J-30a 병합 뒤 — 할 일 1 `pre.diff`가 막는다). 배정하지 않는 것: J-27(재환 과제는 닫음 — 확인된 절반은 mac-setup §8 #27 "부분" 행으로 문서 9가 기록, 남은 절반은 영록 카드 J-27c: J-29 병합·재환 유휴·모델 내림 뒤 — 아래 J-27 절), J-16(배정 보류: #27 "부분" 행이 병합되고 영록이 바꿀 줄마다 절을 다시 쓴 뒤 — 영록 카드는 기다리지 않는다, 아래 J-16 절). 설계 선행으로 남은 과제: J-26·J-28·J-31a·J-31b·J-32·J-33(J-24b는 J-24 병합 때 행을 더한다 — J-24 "병합 시 반영"). Claude 레인 후속 후보: `run_game_perf.sh`가 게임 크래시에도 rc 0(`_pure.py:2038`·`:2065`, J-27 설계 4 — 백로그 행은 영록이 연다). J-10(#161 `acbd954`)·J-19(#163 `f7a924d`)는 끝났다(위 "완료"). J-29·J-23·J-25는 `$W`에서 편집기·`build.sh`·`test.sh`를 돌리고 J-30a·J-24·J-30b도 같은 `$W`에서 브랜치를 바꾸므로 모두 한 번에 하나씩, 앞 과제가 push돼 `$W`에 추적 파일 변경이 없을 때 배정한다(각 절 할 일 1이 막는다; J-29는 두 편집기 실행 내내 GUI 잠금을 잡는다). 모델이 로드된 채 돈 에디터 바이너리 `-game`이 Metal OutOfMemory로 끝났고(J-27, 원인 [미확인]), J-29 전의 무인 UE 크래시는 리포트를 Epic으로 올린다 — J-29 뒤에 새 GPU `-game` 과제를 배정한다(J-29가 확인하는 것은 편집기 바이너리 무인 실행뿐이다 — 패키지 실행의 크래시 업로드는 [미확인]이라 새 패키지 과제는 따로 정한다). PR 본문·자리표시 분류·런북 칸 자기 검사·근거 표기는 모든 과제가 상시 규칙 "PR 본문 공통(모든 과제)"을 따른다(문서 7·8; 문서 9에서 규칙 5 감사, 명령 복사·조각 확인, CI 결론, 되돌림 커밋, 인용·숫자 검사의 꼴, 두 상태 완료 기준 — 3·11~15).

## 백로그 (의존 순서)

순서 원칙: ① UE 빌드가 필요 없는 도구·테스트·CI 일 → ② 재환 worktree의 UE 빌드를 세우고 증명하는 **관문 J-12·J-12b**(빌드·39 테스트, 합성 zone으로 skip 제거) → ③ 열린 카드의 헤드리스 UE 단계와 [미확인] 행 → ④ Claude 레인 코드 후속. **설계 선행** 표시 과제는 영록(Opus)이 짧은 설계 메모(파일·방법·완료 기준)를 이 파일의 해당 행 아래 또는 배정 메시지로 먼저 쓴 뒤에만 배정한다. J-10·J-11·J-19·J-21·J-22·J-23·J-24·J-25·J-29·J-30a·J-30b는 설계가 확정되어(Opus 2026-11-28, 아래 각 절 — J-23·J-24·J-25는 재환 레인 문서 8, J-29·J-30b는 문서 9) 배정할 수 있다(J-30a는 옛 J-30을 좁힌 것이고, 메시 절반 J-30b는 J-30a 병합 뒤에 한다). J-27은 설계가 확정됐지만 재환 과제에서 닫았다(문서 9 — 남은 절반은 영록 카드, 아래 J-27 절). 크기: S ≤ 반나절, M ≤ 하루, L > 하루.

| id | 과제 | 선행 | 크기 | 설계 선행 |
|---|---|---|---|---|
| J-10 | CI shellcheck 잡(공식 v0.11.0 고정·sha256, `--severity=warning`, 기존 결함은 표에 정한 줄별 지시문만 — 실행 줄 변경 없음, 같은 커밋 8/8 초록) — 끝남(#161 `acbd954`, 위 "완료") | 없음(설계 메모 확정, Opus 2026-11-28) | S–M | 설계 확정(J-10 절) |
| J-11 | CI 뷰어 `npm test` 잡(`viewer-smoke`, ubuntu-24.04 한 행 — Playwright 1.56.1은 `ubuntu-latest`(26.04) 미지원, `ci.yml` 훅 블록은 별도 커밋, 같은 커밋 8/8 초록) — 끝남(#159 `366e118`, 위 "완료") | 없음 | M | — (설계 확정, Opus 2026-11-28, 아래 J-11 절) |
| J-16 | `_pure.py` Mac 경로 가정·`package.sh` 주석을 J-15 실측으로 정리 | J-15, mac-setup §8 #27 "부분" 행(J-27 선행 기록, 2026-11-28 문서 9 — 영록 카드 J-27c는 기다리지 않는다, 아래 J-27 절 설계 5) | S–M | **배정 보류**(절 첫머리, 2026-11-28 문서 7·9) — 배정 전 영록이 행·절을 다시 쓴다(J-27 설계 5) |
| J-18 | V-17 §3 Full Precision UV 헤드리스 + WP-06 `_import_moved` 정리 경고(mac-recon #23) — 끝남(#156 `c968c6c`, 위 "완료") | J-12b | M | **준비 메모** |
| J-19 | V-17 §5 ③ 패키지 quinn 전환 로그 확인(Mac): `origin/main`에서 새 Development 패키지 1회(`package.sh --out-dir "$W/build/Mac"`, 쿡 목록 `SKM_Quinn_Simple` 1줄), 패키지 앱 `-RenderOffScreen -ExecCmds`(③ 8개 + `quit`) 1회, 샌드박스 컨테이너 로그 `…/Data/Library/Logs/Golmok/Golmok.log` 사본의 `golmok.character` 응답 8줄을 고정 기대값과 `diff`, pc-verify-v17 §7 표 아래 한 줄(펜스가 만든다), 코드 변경 없음 | J-15(병합됨). `$W`에 추적 파일 변경이 없을 때(J-35 뒤) | S | 설계 확정(Opus 2026-11-28, 아래 J-19 절) — 끝남(#163 `f7a924d`, 위 "완료") |
| J-21 | WP-16a §12 컴파일·심볼 행 #1·#2·#3·#4·#15·#17(엔진 헤더 고정 `grep` 31줄 `diff`, `GolmokWeatherRainFx.cpp`·`GolmokWeatherTest.cpp` touch 뒤 증분 `build.sh` — 컴파일 2·링크 1·경고 0·Niagara 줄 0, `nm -u`·`otool -L` Niagara 링크 증거, §12 표 아래 "Mac 부분 선행" 한 줄 — 칸·코드 변경 없음) — 끝남(#160 `37b6af8`, 위 "완료") | J-12(병합됨), `$W` 추적 파일 변경 없음(J-35 뒤) | S | — (설계 확정, Opus 2026-11-28, 아래 J-21 절) |
| J-22 | V-16 §11 Mac 패키지 명령 이식(에셋 전 기대 결과): `origin/main`에서 Development 패키지를 새로 만들고(J-15 패키지는 커밋 기록이 없어 다시 쓰지 않는다), 매니페스트 `Config/Golmok/weather.json` 1줄·`Golmok/Weather/` 0줄, `UnrealPak -ListContainer` CSV에 `MPC_GolmokWeather`·`NS_GolmokRain` 0줄(대조 `L_Dev` 있음), 패키지 앱 `-RenderOffScreen -ExecCmds="golmok.weather clear instant,golmok.weather rain heavy,golmok.weather status,quit"` 1회의 컨테이너 로그(`~/Library/Containers/com.YourCompany.Golmok/Data/Library/Logs/Golmok/Golmok.log`) 고정 개수와 `diff`, pc-verify-wp16a §13 표 아래 J-20 줄 다음에 "Mac 부분 선행" 한 줄(펜스 생성, 커밋 2에서 `근거: PR #<n>`), 코드 변경 없음 | J-15, J-20(둘 다 병합됨) | M | 설계 확정(Opus 2026-11-28, 아래 J-22 절) — 진행 중(위 "진행 중") |
| J-23 | 19b A1 ① 회귀 헤드리스(GASP 없이): `origin/main`에서 `build.sh` 1회(rc 0·`Result: Succeeded`), `test.sh --filter Golmok.Animation --setup-dev-level` 1회(rc 0), 출력과 에디터 로그 사본(`~/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log`)을 펜스 `j23-check-sh` 18줄(4 Success·요약 failed 0·GaspSmoke skip 문구·`EXECUTED` 0·StateProvider p0 Info·`Character mesh '` 0·폴백 줄 1·이 실행의 `-ExecCmds` 1)로 고정 기대값과 `diff`, pc-verify-wp19 §A9 `(비어 있음)` 바로 뒤에 "Mac 부분 선행" 한 줄(펜스 생성, 커밋 2에서 `근거: PR #<n>`), 두 번째 명령(39개)·PIE 단계는 범위 밖, 코드 변경 없음 | J-12(병합됨), J-36(병합됨). `$W`에 추적 파일 변경이 없을 때(앞 과제 push 뒤), GASP·로컬 GASP 설정 없음·마네킹 있음 | S | 설계 확정(Opus 2026-11-28, 아래 J-23 절) — 배정 가능 |
| J-24 | V-08b §9-1·§9-2 `locomotion_metrics.py` 순수 지표 1차분(planted·`slip_frames`·`legacy_v11_slip`·표 B 반응·Offset Root Bone·최소 로더·`report` CLI — 새 파일 셋을 펜스 그대로, 헤더 `planted`·`slip` 무작위 대조 1e-9, 변형 8개 고정 FAILED 목록, CI 4행 모두 기준 + 43 passed·skip 그대로, 수락 (b)·(c)는 "미대조", 런북 변경 없음) | 없음(설계 확정, Opus 2026-11-28). `stair_contact`·돌아서기·벽·관통·Offset 복귀·`blind`는 J-24b(설계 선행) | M | 설계 확정(J-24 절) — 배정 가능 |
| J-25 | V-16 §2a `MPC_GolmokWeather` 헤드리스 생성 시험(커밋 없음): `UnrealEditor-Cmd -nullrhi` 별도 프로세스로 `weather_setup.run()` 2회 + 읽기 1회, 분기 A(쓰기 됨)/B(`not writable` — 수동 절차 없이 칸만)/stop을 펜스가 정함. A면 MPC가 있을 때 `test.sh --filter Golmok.Weather.Runtime`·`--filter Golmok.Weather`(보고서 `entries`에서 MPC skip 0·NS skip 1 기계 판정, "MPC 단계 완료 / NS 단계 skip"). 에셋은 커밋·LFS 잠금 없이 `$E/asset/`으로 `mv`, sha256 6회 같음, 상태 사본 `diff`. pc-verify-wp16a §12 #9 칸 + 분기 A면 §13 J-22 줄 다음 한 줄(펜스 생성, 커밋 2에서 `근거: PR #<n>`), 코드 변경 없음 | J-20(병합됨). J-21·J-22 병합 뒤(할 일 1 `pre.log`가 막는다), `$W` 추적 파일 변경 없음 | S–M | 설계 확정(Opus 2026-11-28, 아래 J-25 절) — 배정 가능 |
| J-26 | V-18 §0·§1 헤드리스(8 WAV 재임포트, 커밋 없음) | J-12, 설계 메모 | S | **설계 선행** |
| J-27 | V-05 S12 `run_game_perf.sh` Mac 첫 실행 — 도구 경로만, 성능 아님. **재환 과제는 닫음**(2026-11-28 실행: 할 일 1~3 통과, 할 일 4에서 에디터 바이너리 `-game`이 경로 재생 중 Metal `PatchSplit … OutOfMemory`로 크래시, CrashReportClient가 리포트를 Epic으로 업로드 `All uploads done`). 확인된 절반(argv 14개·`-ExecCmds` 한 항목·`editor_exe`·CSV 후보 1 `Saved/Profiling/CSV`)은 영록이 mac-setup §8 #27 "부분" 행으로 기록(펜스 `j27-row27-prerecord`, 문서 9 PR). 남은 절반(경로 끝·`Capture Ended`·`-ExitAfterCsvProfiling` 종료·온전한 CSV의 `golmok-perf`)은 영록 카드 J-27c(아래 J-27 절, "재환에게 맞지 않는 것") — V-05 S12 실제 실행이 먼저 돌면 그것으로 대신한다 | 영록 카드: J-29 병합·키 재확인, 재환 유휴, `lms ps`에 모델 없음(J-15·J-12b의 `$W` 자료) | S(카드) | — (재환에게 배정하지 않음: 모델 내림이 전제이고 크래시는 외부 발송 — 아래 J-27 절 설계 1) |
| J-28 | CI `swift build`(golmok-objcap, macos-latest) | 설계 메모 | S–M | **설계 선행** |
| J-29 | 크래시 리포트 무인 업로드 끄기: 새 `Config/DefaultEditorSettings.ini` `[WP-21 hook]` 블록(`CrashReportsPrivacySettings` `bSendUnattendedBugReports=False` + `AnalyticsPrivacySettings` `bSendUsageData=False`, 펜스 8줄 그대로, 커밋 1 단독) + 크래시 없는 헤드리스 확인(`UnrealEditor-Cmd -nullrhi -unattended -ExecCmds=QUIT_EDITOR` 2회 — 훅 없는 트리 뒤 마커 `NotAllowedUnattendedBugReports` 수정 시각 그대로 `0`, 훅 있는 트리 뒤 새로 써짐 `1`; CrashReportClient pid·크래시 폴더·CRC 로그 시각 그대로, 다른 UE 프로세스 없음, 고정 기대값 19줄과 `diff`), mac-recon §6 새 행 #25(펜스 생성, 커밋 2에서 `근거: PR #<n>`), 사람이 보는 크래시·`bSendUsageData` 효과·패키지·Windows는 [미확인], 크래시를 일으키지 않는다 | J-22 push 뒤(`$W` 추적 파일 변경 없음), 다른 UE 프로그램·GUI 잠금 없음. 다음 UE 과제(J-30a·J-23·J-25·J-27)보다 먼저 | S | 설계 확정(Opus 2026-11-28, 아래 J-29 절) — 배정 가능 |
| J-30a | COLMAP 희소 모델 → EXIF GPS ENU 정합(`model_aligner --ref_images_path … --ref_is_gps 1 --alignment_type enu --alignment_max_error 3`, 원점 = 이름순 첫 장 `DJI_0352.JPG`) → 정합 좌표의 Brush 3k splat, 공개 Tyrol 76장, 펜스 스크립트 13개 수치 판정(잔차 중앙값 ≤ 3 m 등)·비공허 대조군, mac-recon M3 메모 1줄 + §6 #5 칸만(WP-21 후속 4의 절반 — 메시 절반은 J-30b, 설계 선행) | 없음(설계 확정, Opus 2026-11-28). 배정 순서는 J-29 뒤(위 "다음", 2026-11-28 문서 9 — 옛 'J-27 뒤'는 J-27을 닫아 바꿈) | S–M | 설계 확정(J-30a 절, 2026-11-28 문서 7에서 할 일 9 자리표시 분류 단계 수정) — 배정 가능 |
| J-30b | Object Capture 메시를 J-30a 정합 좌표로(WP-21 후속 4의 나머지 절반, 수치 확인만): `tyrol-full/poses.json`의 `translation`(카메라 중심) ↔ J-30a 정합 COLMAP 카메라 중심을 이미지 이름으로 짝지은 Umeyama Sim3(반사 보정, 회전 미사용), OBJ 정점 125,678개 전부를 옮겨 정합 SfM 점까지 `cKDTree` 거리, 펜스 판정 10개(짝 76·`reflection_guard` 0·축척 0.9~1.1·잔차 중앙값 ≤ 0.5 m·p90 ≤ 1.0 m·최대 ≤ 3.0 m·메시 → SfM 중앙값 ≤ 3.0 m·p90 ≤ 12.0 m·대조군 ≥ 30 m), 틀린 셋 3개(정합 전 모델·이름 뒤집기·x 거울)의 고정 FAIL 줄 `diff`, J-30a 실행 폴더 확인(파일 8개 + 같은 실행 확인 2개, 없으면 J-30a 할 일 2~4를 고정 명령으로 `$E/sfm`에 다시), mac-recon M3 J-30a 메모 바로 뒤 1줄 + §6 #6 칸(펜스 생성, 커밋 2에서 `근거: PR #<n>`), 새 저장소 코드 없음 | J-30a 병합(할 일 1 `pre.diff`가 막는다), `$W` 추적 파일 변경 없음 | S–M | 설계 확정(Opus 2026-11-28, 아래 J-30b 절 — J-36 절 뒤) — J-30a 병합 뒤 배정 가능 |
| J-31a | 입력 드라이버 키 타임라인 파서(순수 Python + pytest) | Opus B1 설계 메모 | S | **설계 선행** |
| J-31b | 헤드리스 자동화 1개 "W 3 s → 캡슐 이동 거리"(측정용 주입 경로는 Opus가 구현) | J-31a, Opus 주입 구현 | S | **설계 선행** |
| J-32 | Cesium 활성 사본에서 mac-recon #15·#16(게임 타깃 빌드·`test.sh` 영향) | WP-21 후속 1 결정, 설계 메모 | M | **설계 선행** |
| J-33 | avfoundation 60 fps 녹화 시험(§8 #25) | 소유자 화면 기록 권한, 설계 메모 | S | **설계 선행** |
| J-35 | add-gasp 편집기 가드의 남은 분기 스텁 사례(`$GaspProject` 일치·음성 2종, J-06 후속) — 끝남(#157 `ff77ba8`, 위 "완료") | J-36(병합됨 `8ba637c` — 같은 테스트 파일) | S | — (보충 2026-11-28, 아래 J-35 절) |

J-06·J-07·J-08·J-09·J-10·J-11·J-12·J-12b·J-13·J-14·J-15·J-17·J-18·J-19·J-20·J-21·J-34·J-35·J-36은 끝났고(위 "완료"), J-22는 진행 중이다(위 "진행 중"). J-29·J-30b는 설계가 확정됐고 J-27은 재환 과제에서 닫았다(2026-11-28, Opus — 재환 레인 문서 9). J-23·J-24·J-25도 설계가 확정됐다(2026-11-28, Opus — 재환 레인 문서 8). J-27·J-30a는 설계가 확정됐다(2026-11-28, Opus — J-30은 J-30a·J-30b로 나눴다). J-19·J-21·J-22도 설계가 확정됐다(2026-11-28, Opus — 재환 레인 문서 7). 아래 상세 절은 그대로 두고, 끝난 과제에는 "결과" 줄을 더한다.

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
     - 브랜치와 과제 원문: `E="$TMPDIR/jaehwan/J-10"; mkdir -p "$E"; git -C "$W" fetch origin && git -C "$W" switch -c local/jaehwan-j10-shellcheck origin/main && git -C "$W" show origin/main:docs/plan/jaehwan-tasks.md > "$E/tasks-main.md"; git -C "$W" rev-parse origin/main > "$E/main-rev.log"; { awk '/^#### J-10 /{f=1} /^#### J-11/{f=0} f' "$E/tasks-main.md"; awk '/^### PR 본문 공통\(모든 과제\)$/{f=1} /^## 리뷰·병합 절차$/{f=0} f' "$E/tasks-main.md"; } > "$E/task.txt"`(규칙 14·17 c, 상시 규칙 "PR 본문 공통" 1). 기대: `head -1 "$E/task.txt"`가 `#### J-10 CI shellcheck 잡 — 설계 확정(Opus 2026-11-28)`, `grep -c -x '### PR 본문 공통(모든 과제)' "$E/task.txt"`가 `1`, 펜스 `common-ph-awk` 추출 `awk -v n="common-ph-awk" '$0 == "```" && x {x=0} x {print} $0 ~ ("^```[a-z]+ " n "$") {x=1}' "$E/task.txt" > "$E/ph.awk"`의 `wc -l < "$E/ph.awk" | tr -d ' '`가 `37`, `sed -n '/^```yaml$/,/^```$/p' "$E/task.txt" | sed '1d;$d' | wc -l | tr -d ' '`가 `30`.
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
  9. **PR 본문**: "완료 기준 대조"(규칙 14) 절에 아래 (a)~(j)를 한 줄씩(충족 + 증거 파일, 또는 **미충족** + 이유) 둔다. 과제 문장은 `$E/task.txt`에서만 옮긴다. PR 본문·자리표시 분류·칸 자기 검사·근거 표기는 상시 규칙 "PR 본문 공통(모든 과제)"을 따른다(이 절과 다르면 그 소절을 따른다). 커밋 1~3의 `gh pr checks` 표 원문은 `## 결과`에 백틱 펜스 블록으로, 커밋 4(HEAD)의 표는 `## CI`에 둔다. (정정 2026-11-28 문서 7: 이 자리에 있던 "점검표 규칙 1~16"과 손으로 만드는 자리표시 분류 표는 그 소절의 점검표 대조·기계적 분류로 바뀌었다.)
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
  - (k) PR 본문: 공통 완료 기준 (P)(상시 규칙 "PR 본문 공통" 10) — `checklist.diff` `exit=0`, `ph-unfilled.log` `0`, `pr-edit.rc` `0`, `ph-posted-unfilled.log` `0`, `ph-table.diff` `exit=0`, `signature-last.log` `1`(2026-11-28 문서 7에 더함).
- **병합 시 반영(영록)**: DECISIONS에 오케스트레이터 결정 1줄(shellcheck v0.11.0 고정, GPL-3.0 CI 전용 도구, `--severity=warning`, 고치지 않고 줄별 지시문으로만 억제, 표 밖 결함은 영록이 판단). mac-setup에 로컬 실행 명령 1줄(선택).
- **왜 재환 / 위험**: 정책은 이 메모가 다 정했고, 재환은 측정하고 표를 적용하고 명령으로 증명하기만 한다. 위험: ① 표 밖 결함을 재환이 "사소하다"며 고치거나 억제하는 것(규칙 1·6) — 멈춤 규칙과 (d)·(e)로 막는다. ② `common.sh`를 따라가지 못했는데 warning 판이 조용한 것 — info 판 `SC1090·SC1091·SC2154` 0으로 막는다. ③ push를 연달아 해서 CI 실행이 취소되는 것 — 할 일 3의 "기다리기". ④ 버전 줄 형식이나 다운로드 URL이 메모와 다른 것 — 할 일 1에서 먼저 드러나며, 그때는 멈춘다. ⑤ 깨뜨린 커밋을 force-push로 지우는 것 — 금지, revert만 한다. ⑥ 내려받기가 있는 새 필수 잡의 간헐 실패 — (j)의 8/8로 막는다.
- **dry-run 범위(Opus 2026-11-28)**: scratch 사본에서 돌려 기대 출력을 확인한 것은 블록 추출 `sed`, `ruby -ryaml`(두 경우), numstat·`grep -c`·블록 `diff`, `git show --stat`, (d)의 본문 `diff` 루프(10개 모두 `exit=0`), (e)·할 일 1의 `grep`·`cut`·`sort`·`sed` 파이프(표본 입력), 할 일 3의 CI 로그 추출(표본 로그 줄), 할 일 6의 `printf`(2줄). GitHub 실행이 필요한 명령(`gh run list/watch/view/rerun`, `gh api …/attempts`, `gh pr checks`)과 shellcheck 실행 자체(이 Mac에 없음)는 dry-run하지 못했다.
- **결과(2026-11-28, [#161](https://github.com/wooklym/golmok/pull/161) · `acbd954`, 리뷰 R161 → R161-2)**: CI에 잡 `shellcheck`가 생겼다(`ci.yml` 끝 `[J-10 hook]` 블록 +30줄 — 공식 릴리스 v0.11.0 고정, 내려받은 tar의 sha256 확인, `--severity=warning`). `tools/ue/common.sh`에는 SC2034 지시문 4줄만 더했고 스크립트 본문은 그대로다(R161 재현: 훅 블록이 이 절의 펜스와 바이트 일치). 커밋 1·3은 의도한 빨강이었고, 같은 커밋에서 잡 attempt 8회가 모두 success였다(R161). R161은 코드·CI를 통과로 보고 본문을 보류했다 — 점검표의 규칙 5 줄이 명령 기록과 맞지 않았다(그 뒤 작업 규칙 5에 R161 확장: 그 줄은 센 수로 쓴다, 상시 규칙 "PR 본문 공통" 3의 감사). 고친 본문은 영록이 명령 기록과 대조했다(R161-2). 병합 커밋 본문에 리뷰를 적었고 PR 코멘트는 없다.

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
  1. `E="$TMPDIR/jaehwan/J-11"; mkdir -p "$E"; git -C "$W" fetch origin && git -C "$W" switch -c local/jaehwan-j11-viewer-ci origin/main && git -C "$W" show origin/main:docs/plan/jaehwan-tasks.md > "$E/tasks-main.md"; git -C "$W" rev-parse origin/main > "$E/main-rev.log"; { awk '/^#### J-11 /{f=1} /^#### J-12/{f=0} f' "$E/tasks-main.md"; awk '/^### PR 본문 공통\(모든 과제\)$/{f=1} /^## 리뷰·병합 절차$/{f=0} f' "$E/tasks-main.md"; } > "$E/task.txt"`(규칙 14·17 c, 상시 규칙 "PR 본문 공통" 1). 기대: `grep -c '^#### J-11 CI 뷰어' "$E/task.txt"`가 `1`, `grep -c -x '### PR 본문 공통(모든 과제)' "$E/task.txt"`가 `1`이고, `sed -n '/^```yaml$/,/^```$/p' "$E/task.txt" | sed '1d;$d' | wc -l | tr -d ' '`가 `37`이다.
  2. 붙이기: `cd "$W" && tail -1 .github/workflows/ci.yml > "$E/ci-tail.log" && sed -n '/^```yaml$/,/^```$/p' "$E/task.txt" | sed '1d;$d' >> .github/workflows/ci.yml`. 기대: `$E/ci-tail.log`가 `          grep -q '"numErrors": 0' validator.log`(J-10이 먼저 병합됐으면 `  # [/J-10 hook]` — 그때도 블록은 파일 끝에 붙는다). 그 밖이면 멈춘다. 다른 줄은 건드리지 않는다.
  3. `tools/viewer/README.md:79`에서 정확히 이 문장 `` CI는 뷰어 스모크를 돌리지 않아(`.github/workflows/ci.yml`의 잡은 python·repo-check·tiles-validate뿐) 드러나지 않았다. ``를 `` 당시(2026-11-27) CI는 뷰어 스모크를 돌리지 않아(잡은 python·repo-check·tiles-validate뿐) 드러나지 않았다. J-11 이후 CI의 `viewer-smoke`(ubuntu-24.04 한 행) 잡이 `npm test`를 돌린다. macOS·Windows 행은 없다. ``로 바꾼다. README의 다른 줄은 바꾸지 않는다.
  4. YAML 구문을 확인한다. `cd "$W" && ruby -ryaml -e 'y=YAML.load_file(".github/workflows/ci.yml"); puts y["jobs"].keys.join(" "); j=y["jobs"]["viewer-smoke"]; puts j["timeout-minutes"]; puts j["steps"].map{|s| s["name"]||s["uses"]}.join(" | ")' > "$E/yaml.log" 2>&1; echo "exit=$?" >> "$E/yaml.log"`(규칙 10). 기대는 완료 기준 (c)다. `/usr/bin/ruby`는 macOS 기본이라 따로 설치하지 않는다. actionlint 같은 도구도 설치하지 않는다.
  5. 커밋 1: `.github/workflows/ci.yml`만(`cd "$W" && git add .github/workflows/ci.yml && git diff --cached --name-only > "$E/c1-files.log"`, 기대: `.github/workflows/ci.yml` 한 줄). 커밋 2: `tools/viewer/README.md`만(같은 방법으로 `"$E/c2-files.log"`, 기대: `tools/viewer/README.md` 한 줄). 두 커밋 모두 규칙 7의 `-c` 작성자로 만들고, 커밋마다 `git -C "$W" log -1 --format='%an <%ae>' > "$E/author-<c>.log"`(`<c>`는 `c1`·`c2`)로 확인한다. 기대: `재환 <jaehwan.local@localhost>` 한 줄. 파이썬 게이트(규칙 13)를 `"$E/gate.log"`로 돌린 뒤 **두 커밋을 한 번에 push**하고 PR을 연다. 본문의 CI 칸에는 "CI 진행 중 — 결과는 아래에 추가"만 쓴다(규칙 2a). 8회 측정(할 일 6)은 커밋 2(HEAD)의 push 실행에서 한다.
  6. 8회 측정:
     - 실행 찾기: `cd "$W" && gh run list --workflow CI --branch local/jaehwan-j11-viewer-ci --event push --limit 1 --json databaseId,headSha --jq '.[0]|[.databaseId,.headSha]|@tsv' > "$E/run.tsv"; git rev-parse HEAD >> "$E/run.tsv"`. 기대: `[ "$(sed -n 1p "$E/run.tsv" | cut -f2)" = "$(sed -n 2p "$E/run.tsv")" ] && echo same || echo DIFFERENT`가 `same`. `DIFFERENT`면(실행이 아직 목록에 없을 때 포함) 30초 뒤 같은 명령을 다시 돌리고, 5분 넘게 `DIFFERENT`면 멈춘다. `RUN=$(cut -f1 "$E/run.tsv" | head -1)`.
     - attempt n(1~8)마다 순서대로: (i) n ≥ 2이면 `JOB=$(gh run view "$RUN" --json jobs --jq '.jobs[]|select(.name=="viewer-smoke (ubuntu-24.04)")|.databaseId'); gh run rerun "$RUN" --job "$JOB"`, 이어서 `until [ "$(gh run view "$RUN" --json attempt --jq .attempt)" = "$n" ]; do sleep 10; done`. (ii) `/usr/bin/timeout 1800 gh run watch "$RUN" --interval 30 > "$E/watch-$n.log" 2>&1; echo "exit=$?" >> "$E/watch-$n.log"`(규칙 5). (iii) `JID=$(gh api repos/wooklym/golmok/actions/runs/$RUN/attempts/$n/jobs --jq '.jobs[]|select(.name=="viewer-smoke (ubuntu-24.04)")|.id')`. (iv) `gh api repos/wooklym/golmok/actions/runs/$RUN/attempts/$n/jobs --jq '.jobs[]|select(.name=="viewer-smoke (ubuntu-24.04)")|[.run_attempt,.conclusion,.started_at,.completed_at]|@tsv' >> "$E/attempts.tsv"`. (v) `gh run view --job "$JID" --log > "$E/viewer-log-$n.txt" 2>&1`. (iv)의 결론이 `success`가 아니면 **멈춘다**. 남은 attempt를 돌리지 않고 실패 로그와 함께 영록에게 묻는다(재시도로 초록을 만들지 않는다).
     - 러너 확인: attempt 1 뒤 `grep -m1 'Image: ubuntu-24.04' "$E/viewer-log-1.txt" > "$E/image.log"`. 기대: 한 줄(`… Image: ubuntu-24.04`). 없거나, watch가 `exit=124`로 끝나거나(러너를 잡지 못한 경우 포함), 러너 레이블 오류가 보이면 멈추고 묻는다.
  7. PR 본문에 "완료 기준 대조"(규칙 14) 절을 두고 아래 (a)~(h)를 한 줄씩(충족 + 증거 파일, 또는 **미충족** + 이유) 적는다. 과제 문장은 `$E/task.txt`에서만 옮긴다. attempt 표의 열은 attempt·결론·시작·끝·소요(초, `attempts.tsv`에서 계산한 명령도 함께)·`npm test` 마지막 `OK:` 줄이다. PR 본문·자리표시 분류·칸 자기 검사·근거 표기는 상시 규칙 "PR 본문 공통(모든 과제)"을 따른다(이 절과 다르면 그 소절을 따른다). attempt 표는 `## 결과`에 둔다. (정정 2026-11-28 문서 7: 이 자리에 있던 "점검표 규칙 1~16"과 손으로 만드는 자리표시 분류 표는 그 소절의 점검표 대조·기계적 분류로 바뀌었다. 이 과제는 PR [#159](https://github.com/wooklym/golmok/pull/159)로 이미 진행 중이므로 규칙 17 a대로 보충으로 읽는다: `git -C "$W" fetch origin && git -C "$W" show origin/main:docs/plan/jaehwan-tasks.md > "$E/tasks-main.md"; awk '/^### PR 본문 공통\(모든 과제\)$/{f=1} /^## 리뷰·병합 절차$/{f=0} f' "$E/tasks-main.md" > "$E/task2.txt"` — 기대 `head -1 "$E/task2.txt"`가 `### PR 본문 공통(모든 과제)`. 펜스 `common-ph-awk`는 `awk -v n="common-ph-awk" '$0 == "```" && x {x=0} x {print} $0 ~ ("^```[a-z]+ " n "$") {x=1}' "$E/task2.txt" > "$E/ph.awk"`로 뽑는다(기대 `wc -l < "$E/ph.awk" | tr -d ' '` `37`). 이미 뽑아 둔 `task.txt`는 다시 뽑지 않는다: `## 완료 기준 대조` 블록에는 그 `task.txt`의 완료 기준을 그대로 붙이고, 블록 아래 대조 줄에 (a)~(h)와 함께 이 문서 7에서 더한 (i) 공통 완료 기준 (P)를 한 줄 더한다.)
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
  (i) PR 본문: 공통 완료 기준 (P)(상시 규칙 "PR 본문 공통" 10) — `checklist.diff` `exit=0`, `ph-unfilled.log` `0`, `pr-edit.rc` `0`, `ph-posted-unfilled.log` `0`, `ph-table.diff` `exit=0`, `signature-last.log` `1`(2026-11-28 문서 7에 더함 — PR #159가 열린 뒤의 보충).
- **왜 재환 / 위험**: 재환이 이 스모크의 실패 경로를 가장 잘 알고, 일은 정해진 블록을 붙이고 정해진 명령으로 8회 측정하는 것이다. 위험: ① 간헐 실패가 CI를 빨갛게 만드는 것. (e)의 8/8과 "실패하면 멈춤"으로 막는다. ② Linux 헤드리스 Chromium의 WebGL. `playwright-core` 1.56.1의 `lib/server/chromium/chromium.js:276-278`은 `--enable-unsafe-swiftshader`를 **darwin에서만** 붙인다. 그래서 GPU 없는 ubuntu 러너에서 Cesium이 WebGL 컨텍스트를 얻는지 [미확인]이다(2026-09 클라우드 Linux 세션의 통과 기록은 있지만 러너 환경과 같은지 [미확인]). 첫 attempt가 WebGL·컨텍스트 오류로 실패하면 `smoke.mjs`에 launch 인자를 더하지 말고 로그를 붙여 묻는다. ③ "CI가 X를 확인했다"는 문장은 (e)·(f) 출력이 나온 뒤에만 쓴다(규칙 1·2). ④ `ubuntu-latest`로 되돌리면 Playwright 1.56.1이 26.04에서 chromium을 받지 못한다(설계 1). 레이블은 설계 그대로 둔다.
- **dry-run 범위(Opus 2026-11-28)**: scratch 사본(`origin/main` `ci.yml` + 이 블록, 커밋 2개)에서 돌려 기대 출력을 확인한 것은 할 일 1·2의 블록 추출 `sed`(37줄), 할 일 4의 `ruby -ryaml`, (a)의 numstat·블록 `diff`, (b)의 `grep -c`, (e)의 `cut | sort | uniq -c | sed`(표본 8줄), (h)의 커밋별 파일 루프, 할 일 6의 `run.tsv` 비교(표본). macOS `wc -l`은 앞에 공백을 붙이므로 `| tr -d ' '`를 붙였다. GitHub 실행이 필요한 명령(`gh run list/watch/view/rerun`, `gh api …/attempts`, `gh pr checks`)과 README 문장 교체 뒤의 (d)는 dry-run하지 못했다.
- **결과(2026-11-28, [#159](https://github.com/wooklym/golmok/pull/159) · `366e118`, 리뷰 [R159](https://github.com/wooklym/golmok/pull/159#issuecomment-7233593303) → R159-2)**: CI가 리뷰 뷰어의 헤드리스 스모크를 잡 `viewer-smoke (ubuntu-24.04)`로 돈다(`ci.yml` 끝 `[J-11 hook]` 블록 37줄 — R159가 이 절의 YAML 펜스와 바이트 일치를 확인, `tools/viewer/README.md` 한 문장). 같은 커밋(head `c93474a`)의 push 실행에서 잡 attempt 1~8이 모두 success였다(R159가 GitHub API로 직접 대조: 8회 로그 모두 `Image: ubuntu-24.04`, 경고·재시도 0건). attempt 6은 `gh run watch`가 GitHub API HTTP 500으로 끝나 기록 단계가 일찍 돌았고(잡은 성공), 영록 승인으로 일찍 남은 기록을 보존한 뒤 다시 채웠다(위 상시 규칙 "CI 반복 측정 중 `gh run watch`의 일시 오류"). R159는 워크플로 변경을 통과시키고, PR 본문이 명령 기록 사고 — heredoc이 일찍 닫혀 기록 줄이 셸 명령으로 실행됐고, `commands.txt`를 고치는 스크립트가 6줄과 34줄을 지웠다 — 를 줄여 적은 것을 고치게 했다 → R159-2(영록 본문 확인). 이 사고로 작업 규칙 19(명령 기록은 더하기만, heredoc 금지, 사고는 그대로 보고)가 생겼다. STATUS WP-11 행에 "2026-11-28부터 CI가 뷰어 스모크를 돈다(#159)" 메모를 더했다(2026-11-28 문서 8).

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
- **배정 보류(영록, 2026-11-28 문서 7 — 문서 9에서 고침)**: mac-setup §8 #27 "부분" 행(J-27 선행 기록 줄, 문서 9 PR — 아래 J-27 절 설계 5: `_pure.py:1787`·`:1986`은 이 증거로 답이 났고 `:1779`·`:1802`는 반쯤; J-16은 영록 카드 J-27c를 기다리지 않는다)이 병합되고, 영록이 아래 "정정"대로 바꿀 줄마다 새 주석·코드 줄을 글자 그대로 적어 이 절을 다시 쓰기 전에는 시작하지 않는다. 열린 점: `_pure.py:1779`·`:1787`·`:1802`·`:1986` 각 줄의 새 글자, `package.sh:26` 방화벽 주석 한 줄을 따로 떼어 먼저 줄지.
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
- **결과(2026-11-28, [#156](https://github.com/wooklym/golmok/pull/156) · `c968c6c`, 리뷰 R156(1회 보류: 칸의 임시 로그 이름·진행 문구·시간 조건 3곳) → R156-2)**: pc-verify-v17 §7 §3 행에 Mac 헤드리스 부분 선행(워크트리 HEAD `8ba637c`, `-nullrhi`+`-ExecCmds=py exec(open(…))`) — 기대 줄 `zone_import: full precision UVs (LOD0) on 2/2 chunks (2 set, 0 already on)`·`zone_import: done z_synthetic_scan_001 v1: 8 assets, 0 warnings` 원문 일치, `WARNING cleanup` 0건, 청크 메시 2 모두 `use_full_precision_u_vs=True`, 시간은 참고값(로컬 LLM 추론 부하 있음) `zi.run` 3.93 s. mac-recon #23 칸에 같은 실행의 헤드리스 성공. GUI 체크박스 절반은 [미확인](V-17 GUI 단계). 브랜치 커밋 3개(`b0e6069`·`2e6c53f`·`61c7f99`).

#### J-19 V-17 §5 ③ 패키지 quinn 전환 로그 확인(Mac) — 설계 확정(Opus 2026-11-28)
- **출처**: [pc-verify-v17.md](../runbooks/pc-verify-v17.md) §5(:51-56, ①②는 2026-10-09 Windows에서 끝났고 남은 것은 ③: `golmok.character list → proxy135 → quinn → list → proxy110 → manny → quinn → list`, 기대 "전환마다 `selected …`, 끝 `current=quinn`, `mesh/animation missing or skeleton mismatch` 거절 없음, 로그에 `Character mesh … not found` 없음", 쿡 결과에 `SKM_Quinn_Simple`), §7 표 §5 행(:70, Windows 선행 기록 — `quinn` 거절은 `SKM_Quinn_Simple` 미쿡 때문이었다), 표 아래 J-17 줄(:73). [pc-verify-wp18a.md](../runbooks/pc-verify-wp18a.md) §14-6(:411-416, 창 없는 `-ExecCmds=…` 실행과 임시 훅으로 해결 확인). 쿡 훅: `unreal/Golmok/Config/DefaultGame.ini:143-146`(`[WP-18 hook]` `+DirectoriesToAlwaysCook=(Path="/Game/Characters/Mannequins")`). 캐릭터 코드(Astra 레인 — 읽기만): `Source/Golmok/Characters/GolmokCharacterSubsystem.cpp:246-270`(콘솔 `golmok.character list | <id>`, 응답은 모두 `UE_LOG(LogGolmok, Log, TEXT("golmok.character: %s"), …)` 한 줄 — :265), `:380-403` `SelectCharacter`(`unknown id '…'` :390, `switch requires an active character view; …` :397), `:405-522` `ApplyEntry`(거절 `mesh/animation missing or skeleton mismatch; keeping current character` :433, `visual mesh/animation missing …` :457, 성공 `selected <id> (<ko> / <en>)` :520 — 메시·애님 교체는 이 호출 안에서 끝난다), `:524-538` `DescribeRoster`(`default=%s abp=%s gasp=%s current=%s`, 그 뒤 줄마다 `  <id> | <ko> | <en>` :530·:535), `:343-378` `OnPlayerPawnChanged`(자동 적용 실패만 `golmok.character: auto …` 줄 — :365·:375, GASP 기본 실패는 Warning :373). `Config/Golmok/characters.json`(`default` `manny`, `default_by_anim_mode` `abp` `manny`·`gasp` `manny_gasp`, id 6개 `manny quinn proxy135 proxy110 manny_gasp uefn_gasp`), `Config/Golmok/animation.json`(`mode` `abp`). `Player/GolmokCharacter.cpp:86-88`(`Character mesh '%s' not found; showing capsule. …`, Warning). 로그 범주 `LogGolmok`(`Golmok.h:5`·`Golmok.cpp:5`). 패키지: `tools/ue/package.sh:28-37`(`--out-dir`가 있으면 그 폴더, `Package output: <폴더>` 한 줄), `:48-50`(`RunUAT BuildCookRun … -build -cook -stage -pak -package -archive`). 엔진(읽기, `/Users/Shared/Epic Games/UE_5.8/Engine/Source/Runtime/`, 5.8.4): `Launch/Private/Mac/LaunchMac.cpp:77-96`(argv를 다시 이을 때 공백이 든 항목은 첫 `=`에서 나눠 `이름="값"`으로 감싼다), `:111-114`(패키지 게임 `UE_GAME`에는 ` -installed`를 붙인다), `:116-117`(`$` → `"`), `Core/Private/Misc/App.cpp:423`(`Command Line: ` 로그 줄), `Engine/Private/ParseExecCommands.cpp:11-55`(`-ExecCmds` 값을 따옴표 밖 쉼표로 나누고 각 명령 앞 공백을 뗀다)·`:57-69`, `Engine/Private/UnrealEngine.cpp:2552`(그 명령들을 `DeferredCommands`에 넣는다 — `#if !(UE_BUILD_SHIPPING)` 안, Development 패키지는 해당), `:2772-2810` `TickDeferredCommands`(쌓인 명령을 **한 프레임에 차례로** `LocalPlayer->Exec`로 돌린다, 오래 걸리면 `UEngine::TickDeferredCommands took …` Warning), `Engine/Private/GameEngine.cpp:1530`(`EXIT`·`QUIT`), `:1679-1687` `HandleExitCommand`(`FPlatformMisc::RequestExit(false, TEXT("UGameEngine::HandleExitCommand"))`), `Core/Public/Mac/MacPlatformProperties.h:102-105`(`SupportsQuit()` true), `Core/Private/Mac/MacPlatformMisc.cpp:712-714`(`FPlatformMisc::RequestExit(%i, %ls)` 로그 줄)·`:738-741`(강제가 아니면 `RequestEngineExit`), `Core/Private/Misc/Paths.cpp:573-595` `ProjectLogDir`(Mac은 `-userdir`가 없으면 `FPlatformProcess::UserLogsDir()` — :581-585), `Core/Private/Mac/MacPlatformProcess.cpp:1223-1235` `UserLogsDir`(사용자 `NSLibraryDirectory` + `/Logs/` + 하위 폴더)·`:1187-1207`(게임이면 하위 폴더 = 프로젝트 이름 `Golmok/`), `Core/Private/Misc/OutputDeviceFile.cpp:394`(`Log file closed, …`)·`:482`(이미 있는 로그는 백업 이름으로 옮긴다). 이 Mac에서 Opus가 읽은 것(2026-11-28, 읽기만): 재환 worktree 패키지 `build/Mac/Golmok.app`은 샌드박스로 서명돼 있다(`codesign -d --entitlements -`의 `com.apple.security.app-sandbox` `[Bool] true` — mac-setup §8 #12와 같다). 샌드박스 앱의 사용자 Library는 컨테이너이므로 위 엔진 경로는 `~/Library/Containers/com.YourCompany.Golmok/Data/Library/Logs/Golmok/`이고, 실제로 그 폴더에 `Golmok.log`(07:06)와 `Golmok-backup-2026.11.26-16.46.24.log` 등 4개가 있으며, 다섯 파일의 `LogInit: Command Line:` 줄이 모두 J-15 등 이전 패키지 실행의 인자로 끝이 ` -installed`다(예: `LogInit: Command Line:  /Game/Golmok/Maps/L_Dev -game -RenderOffScreen -ResX=1920 -ResY=1080 -csvCaptureFrames=200,300 -log -installed`, 줄 앞에 시각 없음, 첫 바이트는 UTF-8 BOM). 같은 파일에서 `LogGolmok:` 줄은 `[2026.11.27-22.01.24:349][  0]LogGolmok: GolmokDebugSubsystem: ready …` 꼴이고 끝은 `Log file closed, 11/28/26 07:06:23`이다. `~/Library/Application Support/Epic/Golmok/Saved/Logs`는 없다. 에디터 로그의 실제 `golmok.character` 줄 꼴: `LogGolmok: golmok.character: selected quinn (퀸 / Quinn)`, `LogGolmok: golmok.character: default=manny abp=manny gasp=manny_gasp current=proxy110`. J-15 패키징 로그 `~/Library/Logs/Unreal Engine/LocalBuildLogs/Log.txt`(06:23:40 시작, 06:27 끝 — 약 4분)는 `GolmokEditor`와 `Golmok`을 함께 빌드했고(`Building GolmokEditor and Golmok...`) `Archiving to <W>/build/Mac`·`BUILD SUCCESSFUL`·`AutomationTool exiting with ExitCode=0 (Success)`를 한 줄씩 냈다. J-15 쿡 목록 `unreal/Golmok/Saved/StagedBuilds/Mac/Manifest_UFSFiles_Mac.txt`에 `Golmok/Content/Characters/Mannequins/Meshes/SKM_Quinn_Simple.uasset` 1줄. 방화벽 `socketfilterfw --getglobalstate` 출력 `Firewall is disabled. (State = 0)`. `$W`에는 마네킹(`Content/Characters/Mannequins/Meshes/SKM_Quinn_Simple.uasset`)과 `Content/Golmok/Maps/L_Dev.umap`이 있고 `Content/GASP`는 없다. 2026-11-28 `$W`는 `local/jaehwan-j35-gasp-guard`에서 ` M tools/tests/test_ue_mac_scripts.py`(J-35 진행 중) — 할 일 1의 준비 검사가 이 상태에서는 멈춘다(J-35가 끝난 뒤 배정). (정정 2026-11-28 문서 7: 위 `$W` 상태는 J-35 진행 중의 것이다. J-35는 [#157](https://github.com/wooklym/golmok/pull/157)로 병합됐고, 배정 때의 상태는 할 일 1의 `status-before-tracked.log`가 다시 본다.)
- **이력**: 이 절은 2026-11-28 영록의 "보충(일부)"을 대신한다. 그 보충의 ① 명령 순서·② 기대 문자열·③ 쿡 목록 위치·④ GUI 잠금은 아래 설계 2·4·5와 명령 공통에 그대로 들어갔고, 남은 두 미정(패키지 로그 위치, 패키지 `.app`에서 `-ExecCmds` 다중 명령이 도는지)은 설계 3·4로 정했다.
- **설계 (확정, Opus 2026-11-28)**: 재환은 아래를 그대로 옮긴다. 바꿀 점이 보이면 고치지 말고 묻는다.
  1. **패키지는 새로 만든다**: `$W/build/Mac`의 J-15 패키지는 패키징한 커밋이 기록되지 않았다(mac-setup §8 #10 "패키징한 커밋은 기록하지 않았다"). 그래서 이 과제는 `origin/main`에서 만든 브랜치에서 `./tools/ue/package.sh Development --out-dir "$W/build/Mac"`를 한 번 돌려 같은 자리를 덮어쓴다(J-15 실측 약 4분, `BuildCookRun -build`가 `GolmokEditor`·`Golmok`을 함께 빌드하므로 `build.sh`는 따로 돌리지 않는다). 새 패키지인지는 UAT 로그 `~/Library/Logs/Unreal Engine/LocalBuildLogs/Log.txt`와 쿡 목록이 패키징 직전 표식보다 새것인지로 본다(실행 파일 mtime은 보관 복사가 보존할 수 있어 쓰지 않는다). 패키징·실행 모두 GUI 잠금 안에서 한다.
  2. **실행 명령(고정)**: `/usr/bin/timeout 600 "$W/build/Mac/Golmok.app/Contents/MacOS/Golmok" /Game/Golmok/Maps/L_Dev -game -RenderOffScreen -ResX=1920 -ResY=1080 -unattended "-ExecCmds=golmok.character list,golmok.character proxy135,golmok.character quinn,golmok.character list,golmok.character proxy110,golmok.character manny,golmok.character quinn,golmok.character list,quit"`. 실행 파일을 직접 띄우는 꼴과 `L_Dev -game -RenderOffScreen -ResX=1920 -ResY=1080`은 J-15(mac-setup §8 #11~#13)와 같고, `-unattended`는 대화상자를 막는다. `-csvCaptureFrames`·`-log`는 쓰지 않는다. 명령 9개는 v17 §5 ③ 원문 8개 뒤에 `quit` 하나를 더한 것이다: 엔진은 `-ExecCmds` 명령을 한 프레임에 차례로 돌리고(`UnrealEngine.cpp:2772-2810`), 캐릭터 교체는 각 명령 안에서 동기로 끝나며(`ApplyEntry`), `quit`은 `HandleExitCommand` → `RequestExit(0, UGameEngine::HandleExitCommand)`로 앱을 스스로 끝낸다(J-15처럼 시간 초과로 끊지 않는다). `timeout 600`은 `-ExecCmds`가 돌지 않아 앱이 끝나지 않는 경우만을 위한 상한이다(rc 124 = 멈춤).
  3. **로그 위치(엔진 소스 + 이 Mac의 이전 파일로 정함, 실행 뒤 한 번 잰다)**: 패키지 게임 로그는 `~/Library/Containers/com.YourCompany.Golmok/Data/Library/Logs/Golmok/Golmok.log`다(`Paths.cpp:581-585` → `MacPlatformProcess.cpp:1223-1235`·`:1187-1207`, 샌드박스 컨테이너 — 출처의 기존 파일 5개). `-abslog`로 `$E`에 쓰게 하지 않는다(샌드박스 앱은 컨테이너 밖에 쓸 수 없다고 보고, 시험하지 않는다). 실행 전에 표식을 만들고, 실행 뒤 `find "$HOME/Library/Containers/com.YourCompany.Golmok/Data/Library/Logs" "$HOME/Library/Logs" -type f -name 'Golmok*.log' -newer "$E/marker"`의 출력이 **정확히 그 한 줄**이어야 한다(이전 `Golmok.log`가 `Golmok-backup-<시각>.log`로 옮겨질 때 mtime은 그대로라 잡히지 않는다 — Opus dry-run). 다른 결과(0줄, 다른 경로, 2줄 이상)는 멈춘다. 그 파일을 실행 직후 `$E/game.log`로 복사하고 모든 판정은 사본으로 한다(다음 실행이 원본을 백업 이름으로 옮긴다).
  4. **`-ExecCmds` 다중 명령 판정 = 응답 줄 순서 대조**: 펜스 `j19-seq-sh`가 사본에서 `LogGolmok: … golmok.character: ` 줄을 로그 순서대로 뽑아 `list` 응답은 `list current=<id>`, 성공 전환은 `selected <id>`, 그 밖(거절·`unknown id`·`switch requires …`·`auto …`·Warning 등)은 `other <원문>`으로 바꾼다. 출력이 펜스 `j19-expected-seq` 8줄과 `diff` 0이어야 한다. 이것 하나로 ① 9개 명령이 모두 그 순서로 돌았는지(첫 명령만 돌면 1줄), ② 전환 5개가 모두 `selected`인지, ③ 첫 `list`가 `current=manny`(기본 적용), 두 번째·세 번째 `list`가 `current=quinn`인지, ④ `auto` 실패나 `last_auto_error=`가 없는지를 함께 본다. `list`의 로스터 줄(`  manny | 매니 | Manny` 등)은 이 접두어가 없어 세지 않는다.
  5. **고정 개수**: 펜스 `j19-logcheck-sh`의 출력이 펜스 `j19-expected-logcheck`와 같다 — `LogInit: Command Line:` 줄이 정확히 `LogInit: Command Line:  /Game/Golmok/Maps/L_Dev -game -RenderOffScreen -ResX=1920 -ResY=1080 -unattended -ExecCmds="<9개 명령>" -installed` 1줄(공백이 든 argv를 `LaunchMac.cpp:77-96`이 `-ExecCmds="…"`로 감싸고 `:111-114`가 ` -installed`를 붙인 꼴), `golmok.character` 응답 8줄, `mesh/animation missing or skeleton mismatch` 0, `Character mesh '`…`' not found` 0, `FPlatformMisc::RequestExit(0, UGameEngine::HandleExitCommand)` 1, `Log file closed, ` 1. 쿡: 펜스 `j19-pkgcheck-sh`가 패키징 로그·쿡 목록을 펜스 `j19-expected-pkgcheck`와 대조한다(쿡 목록의 `Golmok/Content/Characters/Mannequins/Meshes/SKM_Quinn_Simple.uasset` 1줄 포함). 실행 시간·프레임·`TickDeferredCommands took` 같은 수치 줄은 판정하지 않는다.
  6. **방화벽은 읽기만**: 실행 전 `/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate`가 정확히 `Firewall is disabled. (State = 0)`이어야 한다. 다르면(켜짐) 앱을 띄우지 않고 멈춘다 — 켜진 방화벽에서 TraceLog 1985가 창을 띄울 수 있고 그 창과 설정은 소유자 몫이다(mac-setup §8 #11 "부분"). TraceLog 포트·`lsof`는 이 과제에서 보지 않는다(J-15가 했다).
  7. **결과 자리**: [pc-verify-v17.md](../runbooks/pc-verify-v17.md) §7 표 아래의 J-17 줄(`Mac 부분 선행(J-17, `로 시작하는 줄) **바로 뒤**에 빈 줄 하나와 새 줄 하나를 넣는다(`Mac 선행 기록(J-19, …`). 줄 전체는 펜스 `j19-row-sh`가 로그에서 만든다 — 재환이 손으로 쓰는 값이 없다. 줄 끝은 `근거: J-19 PR.` 표식이고, PR 번호가 나온 뒤 커밋 2가 그 끝을 `근거: PR #번호.`로 바꾼다(할 일 5, 상시 규칙 "PR 본문 공통" 8). 로그는 파일 이름 없이 컨테이너 폴더 `~/…/Logs/Golmok/`로만 적는다(규칙 17 b의 칸 자기 검사가 `.log`를 찾는다). §7 표 §5 행의 칸(Windows 선행 기록)은 고치지 않는다(규칙 16: 있는 기록은 그대로, 그 칸 끝의 "→ 아래 Mac 기록" 메모는 병합 시 영록). §5 ①(Windows `package.ps1`·`GOLMOK_PKG_DIR`)과 방화벽 창 항목은 Windows 절차라 다루지 않는다.
  8. **코드 변경 없음**: `Source/Golmok/Characters/`(Astra 레인)·`Player/GolmokCharacter.cpp`·`Config/Default*.ini`(핫스팟)·`characters.json`·`tools/`는 열어 읽기만 하고 고치지 않는다. 전환이 거절되거나 순서가 다르면 원인을 고치지 않고 멈춘다(v17 §5 "실패하면 코드를 고치지 말고 로그와 쿡 목록을 적는다" — 이 과제에서는 적기 전에 영록에게 묻는다). 생성물(`build/`, `unreal/Golmok/Saved/`)은 `.gitignore` 대상이라 커밋하지 않는다.
  9. **수치는 근거가 아니다**: 이 과제는 fps·GPU를 재지 않는다. PR 본문에 시간·프레임 숫자를 판정으로 쓰지 않는다.

```sh j19-pkgcheck-sh
#!/bin/sh
# J-19: fixed checks on the package run (usage: sh j19_pkgcheck.sh <W> <E>), one "label value" per line.
W=$1
E=$2
U="$E/pkg-uat.log"
c() { printf '%s %s\n' "$1" "$2"; }
c package-output "$(grep -c -x -F "Package output: $W/build/Mac" "$E/package.log")"
c uat-cmdline "$(grep -c -F "Parsing command line: BuildCookRun -project=$W/unreal/Golmok/Golmok.uproject " "$U")"
c archiving "$(grep -c -x -F "Archiving to $W/build/Mac" "$U")"
c build-successful "$(grep -c -x -F 'BUILD SUCCESSFUL' "$U")"
c uat-exit-0 "$(grep -c -x -F 'AutomationTool exiting with ExitCode=0 (Success)' "$U")"
c gasp-warning "$(grep -c -F 'WARNING: Content/GASP exists' "$E/package.log")"
c newer-than-marker "$(find "$HOME/Library/Logs/Unreal Engine/LocalBuildLogs/Log.txt" "$W/unreal/Golmok/Saved/StagedBuilds/Mac/Manifest_UFSFiles_Mac.txt" -newer "$E/pkg-marker" | wc -l | tr -d ' ')"
c quinn-in-manifest "$(grep -c -F 'Golmok/Content/Characters/Mannequins/Meshes/SKM_Quinn_Simple.uasset' "$E/manifest-ufs.txt")"
c app-binary "$(test -x "$W/build/Mac/Golmok.app/Contents/MacOS/Golmok"; echo $?)"
```

```sh j19-logcheck-sh
#!/bin/sh
# J-19: fixed line counts in the package game log copy (usage: sh j19_logcheck.sh <game log>), one "label count" per line.
G=$1
EC='golmok.character list,golmok.character proxy135,golmok.character quinn,golmok.character list,golmok.character proxy110,golmok.character manny,golmok.character quinn,golmok.character list,quit'
c() { printf '%s %s\n' "$1" "$2"; }
c cmdline-execcmds "$(grep -a -c -x -F "LogInit: Command Line:  /Game/Golmok/Maps/L_Dev -game -RenderOffScreen -ResX=1920 -ResY=1080 -unattended -ExecCmds=\"$EC\" -installed" "$G")"
c character-replies "$(grep -a -c 'LogGolmok: .*golmok\.character: ' "$G")"
c reject-mesh-anim "$(grep -a -c -F 'mesh/animation missing or skeleton mismatch' "$G")"
c mesh-not-found "$(grep -a -F "Character mesh '" "$G" | grep -c -F "' not found")"
c quit-request "$(grep -a -c -F 'FPlatformMisc::RequestExit(0, UGameEngine::HandleExitCommand)' "$G")"
c log-closed "$(grep -a -c -F 'Log file closed, ' "$G")"
```

```sh j19-seq-sh
#!/bin/sh
# J-19: golmok.character replies in log order, one per line (usage: sh j19_seq.sh <game log>).
# a list reply -> "list current=ID", a switch -> "selected ID", anything else -> "other TEXT".
G=$1
grep -a 'LogGolmok: .*golmok\.character: ' "$G" | sed 's/^.*golmok\.character: //' | awk '
/^default=manny abp=manny gasp=manny_gasp current=[a-z0-9_]*$/ { sub(/^.*current=/, ""); print "list current=" $0; next }
/^selected [a-z0-9_]+ \(/ { print "selected " $2; next }
{ print "other " $0 }'
```

```sh j19-row-sh
#!/bin/sh
# J-19: prints the pc-verify-v17 line (below the section 7 table) from the J-19 logs (no hand-written values).
# usage: sh j19_row.sh <E>; exit 3 when a check it relies on is not as expected.
E=$1
fail() { echo "j19_row: $1 is not as expected" >&2; exit 3; }
[ "$(cat "$E/firewall.log")" = 'Firewall is disabled. (State = 0)' ] || fail firewall.log
for f in pkgcheck.diff find-log.diff logcheck.diff seq.diff; do
  [ "$(cat "$E/$f")" = 'exit=0' ] || fail "$f"
done
date=$(cat "$E/run-date.log")
sha=$(cat "$E/sha.log")
last=$(grep -a 'LogGolmok: .*golmok\.character: default=' "$E/game.log" | tail -n 1 | sed 's/^.*LogGolmok: //')
logdir=$(dirname "$(sed "s#^$HOME/#~/#" "$E/find-log.log")")
printf '%s\n' "Mac 선행 기록(J-19, $date, 재환 worktree \`origin/main\` \`$sha\`에서 새로 만든 Development 패키지, macOS 방화벽 꺼짐, ③만): 쿡 목록 \`Manifest_UFSFiles_Mac.txt\`에 \`SKM_Quinn_Simple\` 1줄. 패키지 앱을 \`-RenderOffScreen -ExecCmds=…\`(③ 순서 8개 뒤 \`quit\`)로 1회 실행하자 \`golmok.character\` 응답 8줄이 순서대로 나왔다(전환 5회 모두 \`selected …\`, \`list\` 3회의 \`current=\`는 manny·quinn·quinn, 거절 \`mesh/animation missing or skeleton mismatch\`와 \`Character mesh '…' not found\`는 0줄). 마지막 \`list\`: \`$last\`, 끝: \`FPlatformMisc::RequestExit(0, UGameEngine::HandleExitCommand)\`. 패키지 게임 로그는 샌드박스 컨테이너 폴더 \`$logdir/\`에 쓰였다(이 날짜·이 패키지의 실행 1회 관찰). 근거: J-19 PR."
```

```text j19-expected-pkgcheck
package-output 1
uat-cmdline 1
archiving 1
build-successful 1
uat-exit-0 1
gasp-warning 0
newer-than-marker 2
quinn-in-manifest 1
app-binary 0
```

```text j19-expected-logcheck
cmdline-execcmds 1
character-replies 8
reject-mesh-anim 0
mesh-not-found 0
quit-request 1
log-closed 1
```

```text j19-expected-seq
list current=manny
selected proxy135
selected quinn
list current=quinn
selected proxy110
selected manny
selected quinn
list current=quinn
```

- **명령 공통**: 셸 변수는 Bash 호출 사이에 남지 않는다. 그래서 **모든 명령은 `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/jaehwan/J-19";`로 시작하고**, 그 뒤는 `cd "$W" &&`·`cd "$W/tools" &&`·`git -C "$W"`·`"$E/…"` 절대 경로로 시작한다(상시 규칙). 아래 명령에는 이 앞머리를 적지 않았다. 돌린 명령 원문(변수 그대로)은 `"$E/commands.txt"`에 한 줄씩 더한다(규칙 10). 각 단계의 "기대"와 다르면 **멈춤 조건**을 본다. 할 일 2(`package.sh`)·3(패키지 앱 실행)의 명령과 할 일 5의 게이트 두 번(`gate`·`gate-2`)·`gh pr checks --watch`는 **항상** 하네스의 백그라운드 실행으로 돌리고, 그 명령이 쓰는 `.rc` 파일(`gh pr checks --watch`는 `checks-watch.log`의 `exit=` 줄)이 생길 때까지 기다린다(명령은 바꾸지 않는다). 그 밖의 명령은 앞쪽(foreground)으로 돌린다. 아래 `pgrep -fl '[g]olmok-jaehwan/(…)'` 패턴은 같은 worktree의 에디터·UAT·`UnrealEditor-Cmd` 쿡·패키지 앱을 잡는다(명령마다 글자 그대로 적었다).
  - **GUI 잠금**(할 일 2~3, [mac-setup §3](../runbooks/mac-setup.md) 표의 규칙, J-27과 같은 꼴): 확인 `L="$TMPDIR/claude/gui-foreground.lock"; if [ -e "$L" ]; then cat "$L"; else echo "no lock"; fi > "$E/lock-check.log"; date -u +%FT%TZ >> "$E/lock-check.log"` — 기대 첫 줄 `no lock`. 다른 줄이 있으면 **지우지 않고** 그 줄을 영록에게 보내고 기다린다. 잡기 `mkdir -p "$TMPDIR/claude" && (set -C; printf '%s %s %s\n' "재환" "J-19-pkg" "$(date -u +%FT%TZ)" > "$TMPDIR/claude/gui-foreground.lock"); echo $? > "$E/lock-take.rc"` — 기대 `0`. 풀기 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-19-pkg ' "$L" && rm "$L"; echo $? > "$E/lock-release.rc"` — 기대 `0`.
  - **잠금 갱신**([AGENTS.md](../../AGENTS.md) "UE를 같이 쓰는 규칙"·mac-setup §3: 20분이 지난 기록은 빈 것으로 보므로 잡은 쪽이 쓰는 동안 갱신한다): ① 할 일 2·3의 UE 명령 바로 앞에 매번 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-19-pkg ' "$L" && printf '%s %s %s\n' "재환" "J-19-pkg" "$(date -u +%FT%TZ)" > "$L"; echo $? > "$E/lock-refresh-<n>.rc"` — `<n>`은 할 일 2면 `pkg`, 3이면 `run`. 기대 `0`. 0이 아니면 잠금 파일을 지우거나 쓰지 않고 멈춘다. ② 할 일 2·3의 UE 명령은 갱신 루프로 감싸 **적힌 그대로** 돌린다(앞머리 뒤 `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-19-pkg ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-19-pkg" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!;`, 끝 `; kill "$RP"` — 아래 명령에 이미 들어 있다).
- **할 일**:
  1. **준비**: `mkdir -p "$E" && git -C "$W" status --porcelain > "$E/status-before.log"; grep -c -v '^?? ' "$E/status-before.log" > "$E/status-before-tracked.log"` — 기대 `0`(추적 파일 변경이 있으면 멈춘다; `??` 줄은 그대로 둔다). `git -C "$W" fetch origin && git -C "$W" switch -c local/jaehwan-j19-pkg-quinn origin/main > "$E/switch.log" 2>&1; echo $? > "$E/switch.rc"` — 기대 `0`. `git -C "$W" rev-parse --short HEAD > "$E/sha.log"; git -C "$W" rev-parse HEAD origin/main | uniq | wc -l | tr -d ' ' > "$E/sha-same.log"` — 기대 `1`. `git -C "$W" show origin/main:docs/plan/jaehwan-tasks.md > "$E/tasks-main.md"; git -C "$W" rev-parse origin/main > "$E/main-rev.log"; { awk '/^#### J-19 /{f=1} /^#### J-20/{f=0} f' "$E/tasks-main.md"; awk '/^### PR 본문 공통\(모든 과제\)$/{f=1} /^## 리뷰·병합 절차$/{f=0} f' "$E/tasks-main.md"; } > "$E/task.txt"`(규칙 14·17 c, 상시 규칙 "PR 본문 공통" 1) — 기대 `head -1 "$E/task.txt"`가 `#### J-19 `로 시작, `grep -c -x '### PR 본문 공통(모든 과제)' "$E/task.txt"` `1`. 펜스 추출(손으로 옮기지 않는다): `` printf '%s\n' "j19-pkgcheck-sh j19_pkgcheck.sh" "j19-logcheck-sh j19_logcheck.sh" "j19-seq-sh j19_seq.sh" "j19-row-sh j19_row.sh" "common-ph-awk ph.awk" "j19-expected-pkgcheck expected-pkgcheck.txt" "j19-expected-logcheck expected-logcheck.txt" "j19-expected-seq expected-seq.txt" | while read -r n f; do awk -v n="$n" '$0 == "```" && x {x=0} x {print} $0 ~ ("^```[a-z]+ " n "$") {x=1}' "$E/task.txt" > "$E/$f"; done; cd "$E" && wc -l j19_pkgcheck.sh j19_logcheck.sh j19_seq.sh j19_row.sh ph.awk expected-pkgcheck.txt expected-logcheck.txt expected-seq.txt > "$E/extract-wc.log" `` — 기대(앞 숫자, 순서대로): `15`, `11`, `8`, `14`, `37`, `9`, `6`, `8`, 끝 줄 `108 total`. 겹침: `cd "$W" && gh pr list --state open --json number,headRefName,files --jq '.[]|select(any(.files[]; .path=="docs/runbooks/pc-verify-v17.md"))|"\(.number) \(.headRefName)"' > "$E/overlap.log" 2>&1` — 기대 빈 파일. 프로세스: `pgrep -fl '[g]olmok-jaehwan/(unreal/Golmok/Golmok\.uproject|build/Mac/Golmok\.app/Contents/MacOS/Golmok)' > "$E/procs-before.log"; echo $? > "$E/procs-before.rc"` — 기대 rc `1`(빈 파일). 자료: `{ test -e "$W/unreal/Golmok/Content/Characters/Mannequins/Meshes/SKM_Quinn_Simple.uasset"; echo "quinn-asset=$?"; test -e "$W/unreal/Golmok/Content/Golmok/Maps/L_Dev.umap"; echo "l_dev=$?"; test -e "$W/unreal/Golmok/Content/GASP"; echo "gasp=$?"; } > "$E/content.log"; printf '%s\n' quinn-asset=0 l_dev=0 gasp=1 | diff - "$E/content.log" > "$E/content.diff"; echo "exit=$?" >> "$E/content.diff"` — 기대 `exit=0` 한 줄(마네킹이나 `L_Dev`가 없거나 `Content/GASP`가 있으면 멈춘다 — `add-mannequin.sh`·`--setup-dev-level`을 스스로 돌리지 않는다). 방화벽(읽기만): `/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate > "$E/firewall.log" 2>&1; echo $? > "$E/firewall.rc"; printf '%s\n' 'Firewall is disabled. (State = 0)' | diff - "$E/firewall.log" > "$E/firewall.diff"; echo "exit=$?" >> "$E/firewall.diff"` — 기대 `firewall.rc` `0`, `firewall.diff` `exit=0` 한 줄.
  2. **패키지**: GUI 잠금 확인·잡기. 잠금 갱신 ①(`pkg`). 패키징(하네스 백그라운드): `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-19-pkg ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-19-pkg" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && touch "$E/pkg-marker" && /usr/bin/timeout 5400 ./tools/ue/package.sh Development --out-dir "$W/build/Mac" > "$E/package.log" 2>&1; echo $? > "$E/package.rc"; kill "$RP"` — 기대 `package.rc` `0`. 바로 사본: `cp "$HOME/Library/Logs/Unreal Engine/LocalBuildLogs/Log.txt" "$E/pkg-uat.log" && cp "$W/unreal/Golmok/Saved/StagedBuilds/Mac/Manifest_UFSFiles_Mac.txt" "$E/manifest-ufs.txt"; echo $? > "$E/pkg-cp.rc"` — 기대 `0`. 확인: `sh "$E/j19_pkgcheck.sh" "$W" "$E" > "$E/pkgcheck.log"; diff "$E/expected-pkgcheck.txt" "$E/pkgcheck.log" > "$E/pkgcheck.diff"; echo "exit=$?" >> "$E/pkgcheck.diff"` — 기대 `exit=0` 한 줄(`Package output:` 줄, UAT 명령 줄, `Archiving to …/build/Mac`, `BUILD SUCCESSFUL`, `ExitCode=0 (Success)`, GASP 경고 0, 두 파일이 `pkg-marker`보다 새것, 쿡 목록의 `SKM_Quinn_Simple` 1, 실행 파일 실행 비트).
  3. **실행**: 잠금 갱신 ①(`run`). 실행(하네스 백그라운드): `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-19-pkg ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-19-pkg" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && touch "$E/marker" && date +%F > "$E/run-date.log" && /usr/bin/timeout 600 "$W/build/Mac/Golmok.app/Contents/MacOS/Golmok" /Game/Golmok/Maps/L_Dev -game -RenderOffScreen -ResX=1920 -ResY=1080 -unattended "-ExecCmds=golmok.character list,golmok.character proxy135,golmok.character quinn,golmok.character list,golmok.character proxy110,golmok.character manny,golmok.character quinn,golmok.character list,quit" > "$E/app.out" 2>&1; echo $? > "$E/app.rc"; kill "$RP"`(`run-date.log`는 줄의 날짜 — Mac의 현지 날짜) — 기대 `app.rc` `0`(124 = 시간 초과). 남은 프로세스: `pgrep -fl '[g]olmok-jaehwan/(unreal/Golmok/Golmok\.uproject|build/Mac/Golmok\.app/Contents/MacOS/Golmok)' > "$E/procs-after.log"; echo $? > "$E/procs-after.rc"` — 기대 rc `1`. 로그 찾기(설계 3): `/usr/bin/timeout 120 find "$HOME/Library/Containers/com.YourCompany.Golmok/Data/Library/Logs" "$HOME/Library/Logs" -type f -name 'Golmok*.log' -newer "$E/marker" > "$E/find-log.log" 2> "$E/find-log.err"; echo $? > "$E/find-log.rc"; printf '%s\n' "$HOME/Library/Containers/com.YourCompany.Golmok/Data/Library/Logs/Golmok/Golmok.log" | diff - "$E/find-log.log" > "$E/find-log.diff"; echo "exit=$?" >> "$E/find-log.diff"` — 기대 `find-log.diff` `exit=0` 한 줄(`find-log.rc`·`find-log.err`는 기록만). 이 명령에서 macOS 권한 창이 뜨면 누르지 않는다(멈춤 조건). 사본: `cp "$HOME/Library/Containers/com.YourCompany.Golmok/Data/Library/Logs/Golmok/Golmok.log" "$E/game.log"; echo $? > "$E/game-cp.rc"` — 기대 `0`. `grep -a -F 'Command Line: ' "$E/game.log" > "$E/cmdline.log"`(기록, 진단용). 판정: `sh "$E/j19_logcheck.sh" "$E/game.log" > "$E/logcheck.log"; diff "$E/expected-logcheck.txt" "$E/logcheck.log" > "$E/logcheck.diff"; echo "exit=$?" >> "$E/logcheck.diff"` — 기대 `exit=0` 한 줄. `sh "$E/j19_seq.sh" "$E/game.log" > "$E/seq.log"; diff "$E/expected-seq.txt" "$E/seq.log" > "$E/seq.diff"; echo "exit=$?" >> "$E/seq.diff"` — 기대 `exit=0` 한 줄. 잠금 풀기.
  4. **런북 한 줄**: `sh "$E/j19_row.sh" "$E" > "$E/row-v17.txt"; echo $? > "$E/row.rc"` — 기대 rc `0`, `wc -l < "$E/row-v17.txt" | tr -d ' '` `1`. 넣을 두 줄(빈 줄 + 그 줄): `{ echo; cat "$E/row-v17.txt"; } > "$E/row-insert.txt"`. 앞 확인: `cd "$W" && grep -c '^Mac 부분 선행(J-17, ' docs/runbooks/pc-verify-v17.md` `1`, `cd "$W" && grep -c '^Mac 선행 기록(J-19, ' docs/runbooks/pc-verify-v17.md` `0`. 넣기(손으로 옮기지 않는다, **한 번만** — 두 번 돌리면 아래 `grep -c`가 `2`): `cd "$W" && sed -i '' "/^Mac 부분 선행(J-17, /r $E/row-insert.txt" docs/runbooks/pc-verify-v17.md; echo $? > "$E/row-insert.rc"` — 기대 `0`. 확인: `cd "$W" && awk '/^Mac 부분 선행\(J-17, /{getline a; getline b; print a; print b}' docs/runbooks/pc-verify-v17.md | diff - "$E/row-insert.txt" > "$E/row-diff.log"; echo "exit=$?" >> "$E/row-diff.log"` — 기대 `exit=0` 한 줄. `cd "$W" && grep -c '^Mac 선행 기록(J-19, ' docs/runbooks/pc-verify-v17.md` `1`. 칸 자기 검사(규칙 17 b): `cd "$W" && git diff -U0 origin/main -- docs/runbooks/pc-verify-v17.md | grep '^+[^+]' > "$E/cell-lines-1.txt"; wc -l < "$E/cell-lines-1.txt" | tr -d ' ' > "$E/cell-lines-1-count.log"; grep -n -E '\.log|영록|R[0-9]{3}' "$E/cell-lines-1.txt" > "$E/cell-grep-1.log"; wc -l < "$E/cell-grep-1.log" | tr -d ' ' > "$E/cell-grep-1-count.log"` — 기대 `cell-lines-1-count.log` `1`, `cell-grep-1-count.log` `0`(상시 규칙 "PR 본문 공통" 7 — 0이 아니면 줄을 손으로 고치지 않고 멈춘다). `cd "$W" && git diff --numstat -- docs/runbooks/pc-verify-v17.md` `2	0	docs/runbooks/pc-verify-v17.md`. `git -C "$W" status --porcelain > "$E/status-after.log"; grep -v -x -F ' M docs/runbooks/pc-verify-v17.md' "$E/status-after.log" | diff "$E/status-before.log" - > "$E/status.diff"; echo "exit=$?" >> "$E/status.diff"` — 기대 `exit=0` 한 줄(패키징·실행이 저장소에 남긴 것이 없다).
  5. **게이트·커밋·push**: `cd "$W/tools" && source .venv/bin/activate && { /usr/bin/timeout 300 ruff check . && /usr/bin/timeout 300 ruff format --check . && /usr/bin/timeout 1800 pytest -q && /usr/bin/timeout 300 python scripts/check_repo.py; } > "$E/gate.log" 2>&1; echo $? > "$E/gate.rc"`(하네스 백그라운드) — 기대 `0`(rc 124 = 시간 초과, 다시 돌리지 않고 멈춤). 커밋: `cd "$W" && git add docs/runbooks/pc-verify-v17.md && git diff --cached --name-only > "$E/c1-files.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-19: pc-verify-v17 §7 아래 Mac 선행 기록 — 패키지 quinn 전환(V-17 §5 ③)" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c1-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author.log"` — 기대: `c1-files.log` 한 줄 `docs/runbooks/pc-verify-v17.md`, `author.log` `재환 <jaehwan.local@localhost>`. 게이트 로그가 런북보다 새것인지: `[ "$E/gate.log" -nt "$W/docs/runbooks/pc-verify-v17.md" ]; echo "newer=$?" > "$E/mtime.log"` — 기대 `newer=0`. `git -C "$W" push -u origin local/jaehwan-j19-pkg-quinn > "$E/push.log" 2>&1; echo "exit=$?" >> "$E/push.log"` — 기대 끝 줄 `exit=0`. 브랜치 파일: `git -C "$W" diff --name-only origin/main...HEAD > "$E/branch-files.log"` — 기대 한 줄 `docs/runbooks/pc-verify-v17.md`. push 뒤 상태: `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-final.diff"; echo "exit=$?" >> "$E/status-final.diff"` — 기대 `exit=0` 한 줄. PR 열기(첫 본문은 CI 자리 한 줄뿐 — 규칙 2): `printf '%s\n' '## 요약' '' 'V-17 §5 ③ Mac 패키지 quinn 전환 로그 확인. 본문은 CI 뒤에 채운다.' '' '## CI' '' 'CI 진행 중 — 결과는 아래에 추가' > "$E/pr-body-initial.md"; cd "$W" && gh pr create --base main --head local/jaehwan-j19-pkg-quinn --title "J-19: V-17 §5 ③ Mac 패키지 quinn 전환 로그 확인" --body-file "$E/pr-body-initial.md" > "$E/pr-create.log" 2>&1; echo $? > "$E/pr-create.rc"` — 기대 `0`. PR 번호: `cd "$W" && gh pr view local/jaehwan-j19-pkg-quinn --json number --jq .number > "$E/pr-number.log" 2> "$E/pr-number.err"` — 기대 숫자 한 줄(`grep -c -x '[0-9][0-9]*' "$E/pr-number.log"` `1`, `wc -l < "$E/pr-number.log" | tr -d ' '` `1`; `pr-number.err`는 판정하지 않는다). **커밋 2(PR 번호, 상시 규칙 "PR 본문 공통" 8)**: `N=$(cat "$E/pr-number.log"); sed "s/ 근거: J-19 PR\.\$/ 근거: PR #$N./" "$E/row-insert.txt" > "$E/row-insert-final.txt"; cd "$W" && sed -i '' "s/ 근거: J-19 PR\.\$/ 근거: PR #$N./" docs/runbooks/pc-verify-v17.md; echo $? > "$E/row-pr.rc"` — 기대 `0`. 확인: `cd "$W" && awk '/^Mac 부분 선행\(J-17, /{getline a; getline b; print a; print b}' docs/runbooks/pc-verify-v17.md | diff - "$E/row-insert-final.txt" > "$E/row-final-diff.log"; echo "exit=$?" >> "$E/row-final-diff.log"` — 기대 `exit=0` 한 줄. `cd "$W" && grep -c ' 근거: J-19 PR\.$' docs/runbooks/pc-verify-v17.md` `0`. `cd "$W" && git diff --numstat origin/main -- docs/runbooks/pc-verify-v17.md` `2	0	docs/runbooks/pc-verify-v17.md`. 칸 자기 검사: `cd "$W" && git diff -U0 origin/main -- docs/runbooks/pc-verify-v17.md | grep '^+[^+]' > "$E/cell-lines-2.txt"; wc -l < "$E/cell-lines-2.txt" | tr -d ' ' > "$E/cell-lines-2-count.log"; grep -n -E '\.log|영록|R[0-9]{3}' "$E/cell-lines-2.txt" > "$E/cell-grep-2.log"; wc -l < "$E/cell-grep-2.log" | tr -d ' ' > "$E/cell-grep-2-count.log"` — 기대 `cell-lines-2-count.log` `1`, `cell-grep-2-count.log` `0`(상시 규칙 "PR 본문 공통" 7 — 0이 아니면 줄을 손으로 고치지 않고 멈춘다). 게이트 다시(규칙 13): `cd "$W/tools" && source .venv/bin/activate && { /usr/bin/timeout 300 ruff check . && /usr/bin/timeout 300 ruff format --check . && /usr/bin/timeout 1800 pytest -q && /usr/bin/timeout 300 python scripts/check_repo.py; } > "$E/gate-2.log" 2>&1; echo $? > "$E/gate-2.rc"`(하네스 백그라운드) — 기대 `0`(rc 124 = 시간 초과, 다시 돌리지 않고 멈춤). `[ "$E/gate-2.log" -nt "$W/docs/runbooks/pc-verify-v17.md" ]; echo "newer=$?" > "$E/mtime-2.log"` — 기대 `newer=0`. 커밋: `cd "$W" && git add docs/runbooks/pc-verify-v17.md && git diff --cached --name-only > "$E/c2-files.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-19: 기록 줄의 근거를 PR 번호로" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c2-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-2.log"` — 기대 `c2-files.log` 한 줄 `docs/runbooks/pc-verify-v17.md`, `author-2.log` `재환 <jaehwan.local@localhost>`. `git -C "$W" push > "$E/push-2.log" 2>&1; echo "exit=$?" >> "$E/push-2.log"` — 기대 끝 줄 `exit=0`. `git -C "$W" diff --name-only origin/main...HEAD > "$E/branch-files-2.log"` — 기대 한 줄 `docs/runbooks/pc-verify-v17.md`. `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-final-2.diff"; echo "exit=$?" >> "$E/status-final-2.diff"` — 기대 `exit=0` 한 줄. CI(하네스 백그라운드, 커밋 2의 push 뒤): `cd "$W" && /usr/bin/timeout 1800 gh pr checks "$(cat "$E/pr-number.log")" --watch --interval 30 > "$E/checks-watch.log" 2>&1; echo "exit=$?" >> "$E/checks-watch.log"; gh pr checks "$(cat "$E/pr-number.log")" > "$E/checks.log" 2>&1` — 기대 모든 행 pass.
  6. **PR 본문**: PR 본문·자리표시 분류·칸 자기 검사·근거 표기는 상시 규칙 "PR 본문 공통(모든 과제)"을 따른다(이 절과 다르면 그 소절을 따른다). `## 결과`에는 관찰한 값만 둔다: `pkgcheck.log`·`logcheck.log`·`seq.log` 원문(백틱 펜스 블록), `cmdline.log` 한 줄과 `firewall.log` 한 줄(백틱 펜스 블록), 로그 위치는 `row-v17.txt`의 `~/…/Logs/Golmok/` 폴더 꼴 그대로(파일 이름은 쓰지 않는다) — 과제 번호·규칙 번호·날짜는 이 절에 쓰지 않는다. `## 완료 기준 대조`는 아래 (a)~(h) 한 줄씩. 본문 초안은 `$E/pr-body.md`. 공개 저장소이므로 본문에 사용자 이름이 든 절대 경로를 쓰지 않는다: `grep -c -F "$HOME" "$E/pr-body.md"` — 기대 `0`. 게시 전 검사(규칙 10 e·f) — **대상 로그는 이 목록으로 고정한다**(본문 초안·게시본·`task.txt`·`commands.txt`·검사 로그 자신·쿡 목록 사본은 넣지 않는다): `"$E"/package.log "$E"/pkg-uat.log "$E"/pkgcheck.log "$E"/firewall.log "$E"/find-log.log "$E"/game.log "$E"/cmdline.log "$E"/logcheck.log "$E"/seq.log "$E"/app.out "$E"/sha.log "$E"/run-date.log "$E"/row-v17.txt "$E"/gate.log "$E"/checks.log`.
     - 인용 검사: `## 결과` 절의 백틱 문자열마다 그 문자열이 근거로 든 로그 **한 개**를 `"$E/quotes.tsv"`에 `<문자열><탭><위 목록의 파일 이름>`으로 적는다(로그 인용이 아닌 파일 이름·명령은 파일 칸에 `라벨`). `~/`로 시작하는 경로의 파일 칸은 `row-v17.txt`다. 빠진 것 확인: `` awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '`[^`]+`' | sed 's/^`//;s/`$//' | sort -u > "$E/body-quotes.txt"; cut -f1 "$E/quotes.tsv" | sort -u > "$E/tsv-quotes.txt"; comm -23 "$E/body-quotes.txt" "$E/tsv-quotes.txt" > "$E/quotes-missing.log" `` — 기대 빈 파일. 세기: `while IFS="$(printf '\t')" read -r q f; do if [ "$f" = "라벨" ]; then n="라벨"; else n=$(grep -a -F -c -- "$q" "$E/$f"); fi; printf '%s\t%s\t%s\n' "$n" "$f" "$q"; done < "$E/quotes.tsv" > "$E/quotes-check.log"` — 기대: `cut -f1 "$E/quotes-check.log" | grep -c -x '0'`가 `0`.
     - 숫자 검사: `awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '[0-9]{2,}' | sort -u > "$E/body-numbers.txt"; while read -r x; do printf '%s\t%s\n' "$(cat "$E"/package.log "$E"/pkg-uat.log "$E"/pkgcheck.log "$E"/firewall.log "$E"/find-log.log "$E"/game.log "$E"/cmdline.log "$E"/logcheck.log "$E"/seq.log "$E"/app.out "$E"/sha.log "$E"/run-date.log "$E"/row-v17.txt "$E"/gate.log "$E"/checks.log | grep -a -c -- "$x")" "$x"; done < "$E/body-numbers.txt" > "$E/numbers-check.log"` — 기대: `cut -f1 "$E/numbers-check.log" | grep -c -x '0'`가 `0`.
     - 0이 나온 것은 고치거나 지운다. 그다음 상시 규칙 "PR 본문 공통" 3(점검표 대조)·5(자리표시 분류)·6(조립·게시·다시 읽기)을 적힌 그대로 돌린다.
- **허용 파일**: `docs/runbooks/pc-verify-v17.md`(§7 표 아래 J-17 줄 바로 뒤에 빈 줄 + 한 줄 추가만, 펜스 `j19-row-sh`의 출력 그대로 — 커밋 2는 그 줄 끝의 근거 표식만 바꾼다). 그 밖의 저장소 파일은 고치지 않는다: `Source/Golmok/Characters/`(Astra 레인)·`Player/GolmokCharacter.cpp`·`Config/Default*.ini`(핫스팟)·`Config/Golmok/*.json`·`tools/`·§7 표의 행과 칸·mac-setup·pc-verify-wp18a·공유 문서. 생성물(`build/`·`Saved/`)과 `$W`의 다른 `??` 파일은 커밋하지 않는다.
- **멈춤 조건(정하지 말고 영록에게 묻는다)**: `status-before-tracked.log`가 0이 아닐 때. `switch.rc`가 0이 아니거나 `sha-same.log`가 1이 아닐 때. `head -1 "$E/task.txt"`가 `#### J-19 `로 시작하지 않을 때. `extract-wc.log`가 기대와 다를 때. `overlap.log`가 비어 있지 않을 때. `procs-before.rc`가 1이 아닐 때(같은 worktree의 에디터·UAT·패키지 앱이 떠 있다 — 끄지 않는다). `content.diff`·`firewall.diff`가 `exit=0` 한 줄이 아니거나 `firewall.rc`가 0이 아닐 때(방화벽을 바꾸지 않는다 — 소유자 항목). 잠금 파일에 다른 기록이 있거나 잠금 잡기 rc가 0이 아닐 때. `lock-refresh-pkg.rc`·`lock-refresh-run.rc` 중 하나가 0이 아닐 때(잠금 파일을 지우거나 쓰지 않는다). `package.rc`가 0이 아닐 때(124 = 시간 초과 포함, 다시 돌리지 않는다), `pkg-cp.rc`가 0이 아닐 때. `pkgcheck.diff`·`find-log.diff`·`logcheck.diff`·`seq.diff`·`row-diff.log`·`status.diff`·`status-final.diff`가 `exit=0` 한 줄이 아닐 때(특히 `seq.log`에 `other …` 줄이 있거나 줄 수가 8이 아닐 때 — 거절·순서·`-ExecCmds`가 일부만 돈 경우로, 원인을 고치지 않고 `seq.log`·`cmdline.log`를 보낸다). `app.rc`가 0이 아닐 때(124 = 시간 초과, 규칙 5). `procs-after.rc`가 1이 아닐 때(아래 "멈춤 순서"). `game-cp.rc`가 0이 아닐 때. 로그 찾기나 다른 명령에서 macOS 권한 창이나 방화벽 창이 뜰 때(누르지 않는다 — 소유자 항목). `row.rc`·`row-insert.rc`·`row-pr.rc`가 0이 아닐 때, 넣기 앞 확인 두 `grep -c`가 `1`·`0`이 아닐 때, `row-final-diff.log`가 `exit=0` 한 줄이 아닐 때. `cell-lines-1-count.log`·`cell-lines-2-count.log`가 `1`이 아니거나 `cell-grep-1-count.log`·`cell-grep-2-count.log`가 `0`이 아닐 때(줄을 손으로 고치지 않는다). `gate.rc`·`gate-2.rc`가 0이 아닐 때(rc 124 포함, 다른 파일을 고치거나 `ruff format`으로 바꾸지 않는다). `c1-files.log`·`author.log`·`c2-files.log`·`author-2.log`가 기대와 다를 때. `mtime.log`·`mtime-2.log`가 `newer=0`이 아닐 때. `lock-release.rc`가 0이 아닐 때(잠금 파일을 지우지 않는다). `push.log`·`push-2.log`가 `exit=0`으로 끝나지 않을 때, `branch-files.log`·`branch-files-2.log`가 `docs/runbooks/pc-verify-v17.md` 한 줄이 아니거나 `status-final-2.diff`가 `exit=0` 한 줄이 아닐 때. 상시 규칙 "PR 본문 공통" 9의 공통 멈춤 조건. `pr-create.rc`·`pr-edit.rc`가 0이 아니거나 `pr-number.log`가 숫자 한 줄이 아닐 때. `checks.log`에 pass가 아닌 행이 있을 때. 본문의 `$HOME` 세기가 0이 아닐 때. 그 밖에 이 절의 "기대"와 다른 값이 하나라도 나올 때. **캐릭터 코드·쿡 설정·스크립트의 결함으로 보이는 것을 고치지 않는다**(Astra 레인·핫스팟 — 재현 절차만 보고). **멈춤 순서 — 할 일 2~3 안에서 멈출 때는 이 순서로 한다**: ① `pgrep -fl '[g]olmok-jaehwan/(unreal/Golmok/Golmok\.uproject|build/Mac/Golmok\.app/Contents/MacOS/Golmok)' > "$E/stop-procs.log"; echo $? > "$E/stop-procs.rc"`. ② rc가 `1`이면 잠금 풀기를 돌려 `lock-release.rc`를 남기고 묻는다. ③ rc가 `0`이면(UAT·쿡·패키지 앱이 남았다) 프로세스를 건드리지 않고(`kill`하지 않는다) 잠금도 풀지 않은 채 `stop-procs.log`를 영록에게 보낸다.
- **완료 기준**:
  - (a) 준비: `status-before-tracked.log` `0`, `switch.rc` `0`, `sha-same.log` `1`, `task.txt` 첫 줄 `#### J-19 `, `extract-wc.log` 원문(기대 숫자와 같다), `overlap.log` 빈 파일, `procs-before.rc` `1`, `content.diff` `exit=0`, `firewall.rc` `0`, `firewall.diff` `exit=0`.
  - (b) 패키지: `lock-take.rc` `0`, `lock-refresh-pkg.rc` `0`, `package.rc` `0`, `pkg-cp.rc` `0`, `pkgcheck.diff` `exit=0`(`pkgcheck.log` 원문 9줄).
  - (c) 실행: `lock-refresh-run.rc` `0`, `app.rc` `0`, `procs-after.rc` `1`, `find-log.diff` `exit=0`, `game-cp.rc` `0`, `logcheck.diff` `exit=0`(`logcheck.log` 원문 6줄), `seq.diff` `exit=0`(`seq.log` 원문 8줄), `cmdline.log` 원문 한 줄, `lock-release.rc` `0`.
  - (d) 런북: `row.rc` `0`, `row-v17.txt` 1줄, 넣기 앞 `grep -c` `1`·`0`, `row-insert.rc` `0`, `row-diff.log` `exit=0`, 넣은 뒤 `grep -c '^Mac 선행 기록(J-19, '` `1`, numstat `2	0	docs/runbooks/pc-verify-v17.md`, `status.diff` `exit=0`, `cell-lines-1-count.log` `1`, `cell-grep-1-count.log` `0`.
  - (e) 커밋: `c1-files.log` `docs/runbooks/pc-verify-v17.md` 한 줄, `author.log` `재환 <jaehwan.local@localhost>`, `push.log` 끝 줄 `exit=0`, `branch-files.log` 같은 한 줄, `status-final.diff` `exit=0` 한 줄. `pr-create.rc` `0`, `pr-number.log` 숫자 한 줄. 커밋 2: `row-pr.rc` `0`, `row-final-diff.log` `exit=0`, `근거: J-19 PR.` 0줄, `origin/main` 대비 numstat `2	0	docs/runbooks/pc-verify-v17.md`, `cell-lines-2-count.log` `1`, `cell-grep-2-count.log` `0`, `gate-2.rc` `0`, `mtime-2.log` `newer=0`, `c2-files.log`·`author-2.log` 기대대로, `push-2.log` 끝 줄 `exit=0`, `branch-files-2.log` 한 줄, `status-final-2.diff` `exit=0`.
  - (f) 게이트 `gate.rc` `0`, `mtime.log` `newer=0`. CI `checks.log` 모든 행 pass 원문(규칙 2).
  - (g) PR 본문: 절 순서(상시 규칙 "PR 본문 공통" 2), `## 결과`에 `pkgcheck.log`·`logcheck.log`·`seq.log`·`cmdline.log`·`firewall.log` 원문, "완료 기준 대조" 절, 점검표(그날 규칙 수만큼, 소절 3). 본문의 `$HOME` 세기 `0`. `quotes-missing.log` 빈 파일, `quotes-check.log`·`numbers-check.log`에 0 없음.
  - (h) 공통 완료 기준 (P)(상시 규칙 "PR 본문 공통" 10): `checklist.diff` `exit=0`, `ph-unfilled.log` `0`, `pr-edit.rc` `0`, `ph-posted-unfilled.log` `0`, `ph-table.diff` `exit=0`, `signature-last.log` `1`.
- **병합 시 반영(영록)**: STATUS 재환 절에 J-19 행. §7 표 §5 행 칸 끝에 날짜를 단 "Mac ③은 표 아래 J-19 기록" 메모(규칙 16 — 있는 글은 지우지 않는다). [mac-setup §8](../runbooks/mac-setup.md) #12 칸 끝에 "패키지 게임 로그는 컨테이너 폴더 `…/Data/Library/Logs/Golmok/`(엔진 `Paths.cpp:581-585`·`MacPlatformProcess.cpp:1223-1235`, J-19 실행)" 메모. J-22 절 설계 1 ⑧·3·8의 로그 위치·`-ExecCmds` 여러 명령 문장 끝에 "J-19로 확인(2026-11-28, PR 번호)" 날짜 메모(J-19 결과가 다르면 J-22 배정 전에 그 절을 고친다). pc-verify-wp18a §14-6 끝에 "③ Mac 재확인은 v17 §7 아래 J-19 기록" 메모. V-17 카드 상태(나머지 §0~§4 GUI 항목)는 바꾸지 않는다.
- **왜 재환 / 위험**: 모든 판정이 고정 기대값과의 `diff`·`grep -c`·종료 코드로 끝나고, 확인 스크립트·기대값·결과 줄 문구가 펜스로 정해져 있다. 코드도 Astra 레인도 건드리지 않는다. 위험: ① 첫 명령이 폰보다 먼저 돌아 `switch requires an active character view`나 `no supported game world`가 나오는 것 — Windows 패키지는 같은 꼴로 돌았지만(wp18a §14-6) Mac은 [미확인]이다. `seq.log`의 `other` 줄로 멈추고, 지연 방법은 영록이 정한다. ② `-ExecCmds` 따옴표 — 앱 argv는 셸 따옴표 하나로 넘기고, 로그의 `Command Line:` 줄을 글자 그대로 대조한다(설계 5). ③ 같은 번들 id의 다른 패키지(메인 체크아웃 등)가 같은 컨테이너 로그를 동시에 쓰는 것 — GUI 잠금과 `procs-before`·로그 찾기의 "정확히 한 줄"이 막는다. ④ 결론을 넓히는 것(규칙 1·3·15) — 줄 문구는 "이 날짜·이 패키지의 실행 1회 관찰"로 좁혀 두었다. ⑤ `$W`의 다른 과제 작업물 — 할 일 1·4·5의 `status` 비교가 확인한다(추적 파일 변경이 있으면 시작하지 않는다).
- **dry-run 범위(Opus 2026-11-28)**: `origin/main` `c968c6c`의 scratch 사본(git 저장소로 만든 것)과 이 Mac의 실제 파일에서 한 것: 펜스 `j19-logcheck-sh`·`j19-seq-sh`를 실제 J-15 패키지 로그(`…/Logs/Golmok/Golmok.log`)에 `Command Line:` 줄을 바꾸고 소스 문구 꼴의 응답 8줄·`RequestExit`·`Log file closed` 줄을 넣은 합성 로그에 돌려 두 기대 펜스와 `diff` 0, 빈 로그·첫 명령만 돈 로그(`list current=manny` 1줄)·`quinn` 거절 로그에서는 달랐다(빈 검사 아님 — 거절은 `other mesh/animation missing …` 줄과 `reject-mesh-anim 2`). 실제 에디터 로그(`~/Library/Logs/Unreal Engine/GolmokEditor/`)의 실제 응답 줄에서 `j19-seq-sh`는 `selected quinn`·`list current=proxy110`·`other switch requires …`·`other auto manny: …`·`other GASP mode default failed: …`(Verbose 줄)로 갈랐다. 펜스 `j19-pkgcheck-sh`는 J-15의 실제 UAT 로그·쿡 목록 사본과 06:00 표식에서 기대 펜스와 `diff` 0, 지금 만든 표식에서는 `newer-than-marker 0`으로 달랐다. 펜스 `j19-row-sh`는 rc 0·한 줄, 기대와 다른 `seq.diff`에서 rc 3. 할 일 4의 `sed -i '' "/^Mac 부분 선행(J-17, /r …"`는 `row-insert.rc` `0`, `awk getline` 확인 `diff` 0, `grep -c` `1`, numstat `2	0`, `status`는 그 파일 한 줄. 로그 찾기 `find`는 실제 두 폴더에서 rc 0·0줄(새 로그 없음, 권한 창 없음), 가짜 `$HOME`(새 `Golmok.log`, 헌 백업·헌 에디터 로그)에서 정확히 한 줄·`diff` 0. `pgrep -fl '[g]olmok-jaehwan/(unreal/Golmok/Golmok\.uproject|build/Mac/Golmok\.app/Contents/MacOS/Golmok)'`는 지금 rc 1, `exec -a`로 이름을 바꾼 `sleep` 하나로 rc 0. `socketfilterfw --getglobalstate`는 `Firewall is disabled. (State = 0)`, `gh pr list --state open`은 `[]`. 펜스 추출 `awk`와 `wc -l`(위 기대 숫자), `j19-ph-awk`(J-27과 같은 것)는 견본 본문에서 세 분류를 갈랐다. 이 절과 위 백로그 행을 넣은 scratch 사본에서 파이썬 게이트(`ruff check`·`ruff format --check`·`pytest -q` 1937 passed 3 skipped·`check_repo.py` `OK (uproject, ini, json, links, gitattributes, conflicts, gasp)`)가 rc 0이었고, 그 사본에서 할 일 1의 `awk` 절 추출(첫 줄 `#### J-19 `)과 펜스 추출 `wc -l`이 위 기대 숫자(`84 total`)와 같았으며 추출된 파일 8개는 시험한 파일과 바이트가 같았다. dry-run하지 못한 것: 실제 `package.sh`(쿡 결과·시간), 실제 패키지 앱 실행 — 첫 프레임의 `-ExecCmds` 시점, 응답 줄의 실제 꼴, `quit` 뒤 종료 코드, 로그가 실제로 컨테이너에 새로 생기는지 — 는 이 과제가 재는 것이다. `gh pr create`·`gh pr edit`, 인용·숫자 검사(본문이 없어서), 실제 240초 간격의 잠금 갱신 루프(J-27 dry-run과 같은 명령)도 돌리지 않았다. 문서 7 수정(2026-11-28, Opus): `j19-row-sh`를 로그 폴더 꼴·`근거: J-19 PR.` 표식으로 바꾼 뒤 견본 입력에서 rc 0·한 줄, 그 줄에 규칙 17 b의 `grep -n -E` 0건(바꾸기 전 줄은 `Golmok.log` 때문에 1건). 할 일 1의 두 `awk` 추출(첫 줄 `#### J-19 `, 공통 소절 머리 1줄)과 펜스 추출 `wc -l`(`108 total`), 할 일 5의 커밋 2 `sed`(가짜 번호)와 `awk getline` 확인 `diff` 0·표식 0줄은 scratch 사본에서 돌렸다. 게시·CI·실제 실행은 돌리지 않았다. 위 문장의 `j19-ph-awk` 결과는 그때의 기록이다. 그 펜스는 지웠고, 지금 분류는 상시 규칙 소절의 `common-ph-awk`다.
- **결과(2026-11-28 문서 9)**: PR [#163](https://github.com/wooklym/golmok/pull/163) 병합 `f7a924d`(2026-11-28 16:55 KST, 리뷰 R163 → R163-2 — 병합 커밋 본문). 아래는 병합 전 기록이다. 재환이 실행했고 PR이 열려 있었다(head `125cda5`, `docs/runbooks/pc-verify-v17.md` +2 −0, `gh pr checks 163` 15행 모두 pass). Opus 리뷰(R163)는 런북 줄을 통과로 보고 PR 본문을 보류했다: 사고를 줄여 적음(기록 줄 뒤 `eval`이 두 명령을 같은 이름으로 다시 돌려 첫 결과를 덮어씀), 손으로 친 끝 붙임 `diff-exit=$?`(이 절의 글자는 `exit=$?`), 과제 글에서 잘못 뽑힌 조각을 확인 없이 실행(`command not found` 3회), 이미 돈 게시 전 검사를 "부분 충족"·미래형으로 적음(규칙 10·14·18·19). 이 리뷰에서 작업 규칙 20(뽑은 명령은 확인 && 실행)·21(기록은 돌리기 전에)이 더해졌고, 과제 글 쪽 교훈은 문서 9가 상시 규칙 "PR 본문 공통" 3·11~15와 열린 절(J-23·J-24·J-25·J-30a의 `-bodycheck-sh` 펜스, CI 표 명령의 시간 한도)에 옮겼다. 이 절의 글은 바꾸지 않았다(이미 실행됨). 2026-11-28 16:39 KST에 R163 지적은 GitHub에 게시되지 않았다(PR 코멘트·리뷰 0건).

#### J-20 V-16 §1·§3 헤드리스 기준선
- **출처**: [pc-verify-wp16a.md](../runbooks/pc-verify-wp16a.md) §1(빌드)·§3(헤드리스 자동화), STATUS V-16 행. MPC·NS 에셋(§2)은 아직 없다 → `Golmok.Weather.*`는 해당 단계 skip Info로 Success가 기대(v17 §0 문구).
- **할 일**: `test.sh --filter Golmok.Weather`, `test.sh --filter Golmok.Save`, Info 줄 `grep`.
- **허용 파일**: wp16a §13 결과 기록 아래의 "Mac 선행 기록" 줄(새로 더한다). §1·§3 행의 결과 칸은 고치지 않는다.
- **완료 기준**: 기록은 `Mac 부분 선행(J-20, 에셋 전, 합성 zone 있음/없음, SHA <짧은 SHA>)`로 시작하고 테스트마다 **완료 / skip / 실행 안 함**으로 적는다. 상태·Info 원문은 PR에. `Golmok.Save.*`가 `L_ZoneTest missing`으로 skip이면 J-12b가 덜 된 것이다 — 멈추고 알린다.
- **왜 재환 / 위험**: 명령 검증. 위험: skip을 통과로 적는 것.
- **결과(2026-11-28, [#153](https://github.com/wooklym/golmok/pull/153) · `1d1cfd4`, 리뷰 R153 → R153-2)**: pc-verify-wp16a §13 결과 표 아래에 "Mac 부분 선행(J-20, 에셋 전, 합성 zone 있음(z_synthetic_002는 청크·콜리전 에셋 없음), SHA 5475c7a)" 줄을 더했다(그 파일 +2 −0). §1 빌드 종료 코드 0(업투데이트 빌드라 전면 재컴파일의 Niagara 경고 문구는 [미확인]). 테스트별: Weather.Config 완료, Weather.Lighting 완료(`[Info] NightUnaffected at 05:35 (base lux 0.104167)`), Weather.Runtime **skip**(MPC·NS 없음 skip Info 2줄, 경고 1), Save.RoundTrip 완료(날씨 단계 실행, close 단계 Info 2줄, 경고 4: z_synthetic_002 에셋 없음). Save 필터 실행의 종료 코드 1은 그때의 `test.sh` 규칙 때문이었다(J-36 [#154](https://github.com/wooklym/golmok/pull/154)가 뒤에 고쳤다). [R153](https://github.com/wooklym/golmok/pull/153#issuecomment-7230747835)이 한 번 보류했다: (A) 필터 단위로 "완료"를 적어 Weather.Runtime의 skip이 묻혔고(규칙 14, R149에 이은 2번째·같은 테스트), (B) 브랜치 안 병합 커밋 `2fa7817`(#152 병합분을 받은 것)은 `-c`를 빠뜨려 작성자가 `kreativ`로 남았고(규칙 7, #142에 이은 2번째 — 되돌리지 않음), (B) 런북 줄이 길고 임시 로그 이름·진행 문구가 들어 있었다(규칙 10(g)·16). 재환이 테스트별 짧은 줄로 바꾼 뒤(`97b76bd`) R153-2(영록 직접 대조: 자동화 리포트 사본 2개의 테스트별 state·경고·skip 메시지, 실행 rc, 최종 본문)에서 병합했다. 선행이 풀린 과제: J-22.

#### J-21 WP-16a §12 컴파일·심볼 행(#1·#2·#3·#4·#15·#17) — 설계 확정(Opus 2026-11-28)
- **출처**: [pc-verify-wp16a.md](../runbooks/pc-verify-wp16a.md) §12 표(:317-339, 열 "PC 결과"는 20행 모두 빈 칸, #8만 `➖ 16a는 레시피`, #2는 대안 칸 끝에 R112-U2 메모), §1 빌드(:51-58: "Niagara 관련 UBT 경고 문구가 있으면 그대로 기록(§12 #1)", 링크 오류면 §12 #2), §13 결과 표 "§12 API" 행(:360, 카드 전체 몫 — 고치지 않는다), §13 표 아래 J-20 줄(:364, 같은 런북의 Mac 선행 기록 꼴), 머리말 :11("컴파일·링크 에러가 나면 §12 표를 보고 고친 뒤 커밋" — PC 세션 규칙이고 재환은 고치지 않는다). 코드(읽기만, 모두 Claude 레인 — [DEVELOPMENT-PLAN §7.6](../DEVELOPMENT-PLAN.md) 표: Astra 레인은 `Characters/`·`Audio/`·`Tests/GolmokCharacterRoster*`·`Tests/GolmokAudio*`): `Source/Golmok/Weather/GolmokWeatherRainFx.cpp`(Niagara를 include하는 유일한 파일 :6-8 — #3 `NewObject`·`SetAsset`·`SetUsingAbsoluteRotation`·`SetRootComponent`·`AddInstanceComponent`·`RegisterComponent` :80-87, #4 `SetVariableFloat`·`SetVariableVec3` :111-120, `GetOverrideParameters`·`FindParameterOffset`·`GetParameterValue<T>` :168-178, `GetExposedParameters` :193-196, #15 `NameMode = Requested`·`RF_Transient` :69-70, `ResetSystem` :151, `DeactivateImmediate` :155), `Source/Golmok/Tests/GolmokWeatherTest.cpp`(#17 `Travel->OnTraveled.IsBoundToObject(W)` :1240, 파일 전체가 `#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR` :32-1375 — 에디터 Development 타깃에서 컴파일된다), `Source/Golmok/Map/GolmokTravelSubsystem.h:14`(`OnTraveled`는 `DECLARE_MULTICAST_DELEGATE_OneParam`), `Golmok.Build.cs:33-35`(`[WP-16 hook]` `PrivateDependencyModuleNames.Add("Niagara");` — 핫스팟, 읽기만), `Golmok.uproject:30`(`{"Name": "Niagara", "Enabled": true},`). 엔진(읽기, 5.8.4 `Build/Build.version` `"PatchVersion": 4,`·`"Changelist": 58902052,`): `Plugins/FX/Niagara/Niagara.uplugin:13`(`"EnabledByDefault" : true,`), `Plugins/FX/Niagara/Source/Niagara/Public/NiagaraComponent.h`(:56 `UCLASS(… MinimalAPI)`·:57, :228 `DeactivateImmediate`, :295 `SetAsset`, :506 `SetVariableVec3`, :533 `SetVariableFloat`, :646 `ResetSystem`, :746 const `GetOverrideParameters`), `…/Public/NiagaraParameterStore.h`(:405 `GetParameterValue<T>`, :510 virtual `FindParameterOffset`), `…/Classes/NiagaraSystem.h`(:237 `MinimalAPI`, :368 const `GetExposedParameters`), `…/Public/NiagaraTypes.h`(:1115 `FloatDef`, :1119 `Vec3Def` — `NIAGARA_API`), `Source/Runtime/Engine/Classes/Engine/World.h`(:496 `ESpawnActorNameMode`, :508 `Requested`, :512 `NameMode`), `Source/Runtime/CoreUObject/Public/UObject/ObjectMacros.h:596`(`RF_Transient`), `Source/Runtime/Engine/Classes/Components/SceneComponent.h:1605`·`GameFramework/Actor.h:2493`·`:4348`·`Components/ActorComponent.h:1322`, `Source/Runtime/Core/Public/Delegates/MulticastDelegateBase.h:150`(public 절 :65 안의 `IsBoundToObject`)·`DelegateSignatureImpl.inl:760`(`TMulticastDelegateRegistration`의 `public:` :756 아래 `using Super::IsBoundToObject;`). **touch한 파일만 따로 컴파일되는 이유**(Opus가 엔진 UBT 소스로 확인): `Source/Programs/UnrealBuildTool/System/SourceFileWorkingSet.cs:335-371`(기본 공급자는 Git → Perforce 순), `:373-402`(Git 작업 집합은 엔진 루트·프로젝트 폴더·그 부모에 `.git`이 있을 때만 — `$W`의 `.git`은 프로젝트 `unreal/Golmok`의 두 단계 위라 해당 없음), `:404-416`(Launcher 설치 엔진이면 Perforce 작업 집합), `:55-87`(읽기 전용이 아닌 파일은 모두 작업 집합), `System/Unity.cs:352-413`(작업 집합 파일은 unity 밖에서 따로 컴파일). 실제 `$W` UBT 로그(Opus 읽음, `~/Library/Application Support/Epic/UnrealBuildTool/`): J-12 전체 빌드 `Log-backup-2026.11.27-18.38.39.txt`는 `[Adaptive Build] Excluded from Golmok unity file:`에 프로젝트 `.cpp` 전부, `[46/57] Compile [Apple] GolmokWeatherRainFx.cpp`·`[50/57] Compile [Apple] GolmokWeatherTest.cpp`·`[56/57] Link [Apple] libUnrealEditor-Golmok.dylib`·`Result: Succeeded`, `grep -c -i niagara` 0, `grep -c -E ': (warning|error):'` 0. J-17 증분 빌드 `Log-backup-2026.11.27-21.52.51.txt`는 `[1/3] Compile [Apple] GolmokCharacter.cpp`·`[2/3] Compile [Apple] GolmokZoneSubsystem.cpp`·`[3/3] Link [Apple] libUnrealEditor-Golmok.dylib`(touch 2개 → 동작 3개). (정정 2026-11-28 문서 7, Opus가 UBT 로그를 다시 읽음) J-17 이후의 UBT 로그 4개(`Log-backup-2026.11.27-21.52.51.txt` :32-33, `Log-backup-2026.11.27-23.15.48.txt`, `Log-backup-2026.11.27-23.56.54.txt`, `Log.txt`)에는 모두 `…/Engine/Source/ThirdParty/Intel/ISPC/bin/Mac/ispc has been deleted since makefile was built.`와 `Invalidating makefile for GolmokEditor (ispc deleted)`가 1번씩 있다. 엔진에 `Source/ThirdParty/Intel/ISPC/bin/Mac/`이 없어서 `build.sh`마다 makefile을 다시 만든다. 그 네 로그와 J-12의 `Creating makefile for GolmokEditor (no existing makefile)` 로그(`Log-backup-2026.11.27-18.38.39.txt` :31)의 `grep -c -i niagara`는 모두 0이다. UBA 캐시 서버 설정 없음(사용자·프로젝트 `BuildConfiguration.xml` 둘 다 빈 `<Configuration>`). 링크 결과: 2026-11-28 06:53의 `$W/unreal/Golmok/Binaries/Mac/libUnrealEditor-Golmok.dylib`에서 `otool -L`의 Niagara 줄은 `@rpath/libUnrealEditor-Niagara.dylib (compatibility version 5.8.0, current version 5511.68.0)` 하나(NiagaraCore 0), `nm -u | c++filt | grep -i niagara`는 11줄(펜스 `j21-expected-imports`). 2026-11-28 Opus가 읽은 `$W` 상태: 브랜치 `local/jaehwan-j35-gasp-guard`(J-35 작업 중, ` M tools/tests/test_ue_mac_scripts.py`·`?? unreal/Golmok/Content/Golmok/Materials/`) — 할 일 1의 준비 검사가 J-35가 끝나기 전 배정을 막는다. (정정 2026-11-28 문서 7: 위 상태는 J-35 진행 중의 것이다. J-35는 [#157](https://github.com/wooklym/golmok/pull/157)로 병합됐고, 배정 때의 상태는 할 일 1의 `status-before-tracked.log`가 다시 본다.)
- **설계 (확정, Opus 2026-11-28)**: 재환은 아래를 그대로 옮긴다. 바꿀 점이 보이면 고치지 말고 묻는다.
  1. **범위**: §12 20행 중 컴파일·심볼로 답이 나오는 부분만 — #1(uplugin 값·uproject 항목·빌드 출력의 Niagara 줄), #2(`Niagara` 하나로 링크되는가), #3(컴파일만), #4(API 존재만), #15(API 존재만), #17(컴파일 — 공개 멤버인가). 다음은 **이 과제에서 다루지 않고 칸도 건드리지 않는다**: #3의 등록·렌더, #4의 `User.` 접두 필요 여부, #15의 텔레포트 뒤 줄무늬(모두 PIE·에셋), #17의 단언 결과(`Golmok.Weather.Runtime`, NS 에셋 필요), #5~#7·#9~#14·#16·#18~#20(PIE·GUI·에셋·패키지·룩 — #10·#11은 API가 컴파일되지만 불확실한 점이 실행 중 값이라 범위 밖), #8(이미 `➖ 16a는 레시피`).
  2. **결과 자리**: §12 표의 "PC 결과" 칸은 고치지 않는다 — PC 카드 V-16 전체(에셋·PIE 포함)의 칸이고, #3·#4·#15는 이 과제가 절반만 답한다. J-17·J-20과 같이 **§12 표 바로 아래에 빈 줄 하나 + "Mac 부분 선행(J-21, …)" 한 줄**을 더한다(표 마지막 행 `| 20 | ` 다음; 빈 줄이 없으면 GFM에서 그 줄이 표 행이 된다). 줄 전체는 펜스 `j21-row-sh`가 로그에서 만든다 — 재환이 손으로 쓰는 값이 없다. 줄 끝은 `근거: J-21 PR.` 표식이고, PR 번호가 나온 뒤 커밋 2가 그 끝을 `근거: PR #번호.`로 바꾼다(할 일 6, 상시 규칙 "PR 본문 공통" 8). §13 "§12 API" 행과 J-20 줄은 그대로 둔다.
  3. **심볼**: 펜스 `j21-symbols-sh`가 엔진 파일 13개(헤더 11개·`Build.version`·`Niagara.uplugin`)와 프로젝트 파일 4개에서 고정 문자열 31줄을 `grep -n`으로 뽑고(공백은 한 칸으로 줄인다), 펜스 `j21-expected-symbols`와 `diff`해 0이어야 한다. 기대값은 Opus가 같은 스크립트를 이 엔진과 `origin/main` `8a4b3c7` scratch 사본에 돌린 출력이다. 엔진 패치나 프로젝트 줄 번호가 바뀌면 `diff`가 0이 아니다 → 멈춘다(기대값을 고치지 않는다).
  4. **빌드**: ① 기준 빌드 `build.sh` 1회(브랜치를 바꾼 뒤 남은 변경을 먼저 흡수 — 결과는 rc와 `Result: Succeeded`만 본다). ② `GolmokWeatherRainFx.cpp`(#2·#3·#4·#15)와 `GolmokWeatherTest.cpp`(#17)만 `touch`(내용 변경 없음, `git status` 불변 확인) → ③ 증분 `build.sh` 1회. ③의 출력은 펜스 `j21-buildcheck-sh`의 9개 세기가 펜스 `j21-expected-buildcheck`와 같아야 한다: `Compile [Apple]` 줄 정확히 2(두 파일 각 1), `Link [Apple] libUnrealEditor-Golmok.dylib` 1, `Result: Succeeded` 1, `Target is up to date` 0, clang 진단(`: warning:`·`: error:`·`: fatal error:`) 0, `Undefined symbols` 0, `niagara`(대소문자 무시) 0. 동작 번호(`[1/3]` 등)의 순서는 병렬이라 보지 않는다. `Golmok.Build.cs`·`Golmok.uproject`는 핫스팟·설정이라 touch하지 않는다. (정정 2026-11-28 문서 7: 처음 적은 "그래서 makefile 재생성 때의 UBT 플러그인 문구는 이 실행이 보지 않는다"는 사실이 아니었다.) 이 Mac에는 엔진 `Source/ThirdParty/Intel/ISPC/bin/Mac/ispc`가 없어서 `build.sh`마다 makefile이 다시 만들어진다(J-17 이후 UBT 로그마다 `Invalidating makefile for GolmokEditor (ispc deleted)`, 그 로그들의 `grep -c -i niagara` 0 — 출처). 다만 그 줄이 `build.sh` 표준 출력(`build-1.log`)에도 나오는지는 dry-run하지 못했으므로, 행 문구는 "빌드 출력의 Niagara 줄 0"만 적고 #1의 UBT 경고 문구 유무는 판정하지 않는다.
  5. **링크 증거(#2)**: ③ 뒤 dylib이 touch 표식보다 새것(`newer=0`), `nm -u … | c++filt | grep -i niagara | LC_ALL=C sort`가 펜스 `j21-expected-imports`(11줄)와 같고, `otool -L … | grep -i niagara`(앞 공백 제거)가 펜스 `j21-expected-otool` 한 줄과 같다. NiagaraCore 의존이 없다는 것은 이 한 줄과 `Build.cs`의 `NiagaraCore` 0(심볼 펜스)로 본다.
  6. **GUI 잠금**: `build.sh`는 헤드리스지만 영록의 성능 측정과 겹치지 않도록 J-27과 같은 꼴로 잠금을 잡는다(목적 `J-21-build`, 상시 규칙 "GPU·GUI 공유").
  7. **코드 변경 없음**: C++·`Build.cs`·uproject·테스트·`tools/`는 고치지 않는다. 빌드가 실패하거나 세기가 다르면 **고치지 말고** 오류 줄과 파일:줄을 보고한다(wp16a 머리말 :11의 "고친 뒤 커밋"은 PC 세션 규칙이다).
  8. **숫자는 근거가 아니다**: 빌드 시간은 판정에 쓰지 않는다.

```sh j21-symbols-sh
#!/bin/sh
# J-21: fixed header/project greps for wp16a section 12 rows 1, 2, 3, 4, 15, 17. One "label path:line:text" per match.
# usage: sh j21_symbols.sh <engine dir> <W>   (engine dir = ".../UE_5.8/Engine")
U=$1
W=$2
NC=Plugins/FX/Niagara/Source/Niagara/Public/NiagaraComponent.h
NS=Plugins/FX/Niagara/Source/Niagara/Classes/NiagaraSystem.h
NT=Plugins/FX/Niagara/Source/Niagara/Public/NiagaraTypes.h
NP=Plugins/FX/Niagara/Source/Niagara/Public/NiagaraParameterStore.h
RT=Source/Runtime
g() {
  # label, root, relative path, fixed string (or ERE when $5 = E)
  if [ "$5" = E ]; then o=-E; else o=-F; fi
  n=$(grep -c $o -- "$4" "$2/$3")
  if [ "$n" = 0 ]; then
    echo "$1 $3:MISSING"
  else
    grep -n $o -- "$4" "$2/$3" | sed -e 's/^\([0-9]*\):[[:space:]]*/\1:/' -e "s#^#$1 $3:#" | tr -d '\r' | tr -s '[:blank:]' ' '
  fi
}
g version "$U" Build/Build.version '"PatchVersion": 4,'
g version "$U" Build/Build.version '"Changelist": 58902052,'
g r1 "$U" Plugins/FX/Niagara/Niagara.uplugin '"EnabledByDefault" : true,'
g r1 "$W" unreal/Golmok/Golmok.uproject '{"Name": "Niagara", "Enabled": true},'
g r2 "$W" unreal/Golmok/Source/Golmok/Golmok.Build.cs 'PrivateDependencyModuleNames.Add("Niagara");'
echo "r2 unreal/Golmok/Source/Golmok/Golmok.Build.cs:NiagaraCore $(grep -c -F NiagaraCore "$W/unreal/Golmok/Source/Golmok/Golmok.Build.cs")"
g r2 "$U" "$NC" 'class UNiagaraComponent : public UFXSystemComponent'
g r2 "$U" "$NS" 'UCLASS(BlueprintType, MinimalAPI, meta = (LoadBehavior = "LazyOnDemand"))'
g r2 "$U" "$NT" 'static NIAGARA_API FNiagaraTypeDefinition FloatDef;'
g r2 "$U" "$NT" 'static NIAGARA_API FNiagaraTypeDefinition Vec3Def;'
g r3 "$U" "$NC" 'NIAGARA_API void SetAsset(UNiagaraSystem* InAsset, bool bResetExistingOverrideParameters = true);'
g r3 "$U" "$RT/Engine/Classes/Components/SceneComponent.h" 'ENGINE_API void SetUsingAbsoluteRotation(const bool bInAbsoluteRotation);'
g r3 "$U" "$RT/Engine/Classes/GameFramework/Actor.h" 'ENGINE_API bool SetRootComponent(USceneComponent* NewRootComponent);'
g r3 "$U" "$RT/Engine/Classes/GameFramework/Actor.h" 'ENGINE_API void AddInstanceComponent(UActorComponent* Component);'
g r3 "$U" "$RT/Engine/Classes/Components/ActorComponent.h" 'ENGINE_API void RegisterComponent();'
g r4 "$U" "$NC" 'NIAGARA_API void SetVariableFloat(FName InVariableName, float InValue);'
g r4 "$U" "$NC" 'NIAGARA_API void SetVariableVec3(FName InVariableName, FVector InValue);'
g r4 "$U" "$NC" 'const FNiagaraParameterStore& GetOverrideParameters() const { return OverrideParameters; }'
g r4 "$U" "$NP" 'NIAGARA_API virtual const int32* FindParameterOffset(const FNiagaraVariableBase& Parameter, bool IgnoreType = false) const;'
g r4 "$U" "$NP" 'inline T GetParameterValue(const FNiagaraVariableBase& Parameter)const'
g r4 "$U" "$NS" 'const FNiagaraUserRedirectionParameterStore& GetExposedParameters() const {'
g r15 "$U" "$NC" 'NIAGARA_API virtual void DeactivateImmediate() override;'
g r15 "$U" "$NC" 'NIAGARA_API void ResetSystem();'
g r15 "$U" "$RT/Engine/Classes/Engine/World.h" 'enum class ESpawnActorNameMode : uint8'
g r15 "$U" "$RT/Engine/Classes/Engine/World.h" '^[[:space:]]*Requested$' E
g r15 "$U" "$RT/Engine/Classes/Engine/World.h" 'ESpawnActorNameMode NameMode;'
g r15 "$U" "$RT/CoreUObject/Public/UObject/ObjectMacros.h" '^[[:space:]]*RF_Transient[[:space:]]*=0x00000040,' E
g r17 "$W" unreal/Golmok/Source/Golmok/Map/GolmokTravelSubsystem.h 'DECLARE_MULTICAST_DELEGATE_OneParam(FGolmokOnTraveled'
g r17 "$W" unreal/Golmok/Source/Golmok/Tests/GolmokWeatherTest.cpp 'Travel->OnTraveled.IsBoundToObject(W)'
g r17 "$U" "$RT/Core/Public/Delegates/MulticastDelegateBase.h" 'inline bool IsBoundToObject(FDelegateUserObjectConst InUserObject) const'
g r17 "$U" "$RT/Core/Public/Delegates/DelegateSignatureImpl.inl" 'using Super::IsBoundToObject;'
```

```sh j21-buildcheck-sh
#!/bin/sh
# J-21: fixed line counts in the build log after touching the two .cpp files, one "label count" per line.
# usage: sh j21_buildcheck.sh <build log>
B=$1
c() { printf '%s %s\n' "$1" "$2"; }
c compile-lines "$(grep -c -E '^\[[0-9]+/[0-9]+\] Compile \[Apple\] ' "$B")"
c compile-rainfx "$(grep -c -E '^\[[0-9]+/[0-9]+\] Compile \[Apple\] GolmokWeatherRainFx\.cpp$' "$B")"
c compile-weathertest "$(grep -c -E '^\[[0-9]+/[0-9]+\] Compile \[Apple\] GolmokWeatherTest\.cpp$' "$B")"
c link-golmok "$(grep -c -E '^\[[0-9]+/[0-9]+\] Link \[Apple\] libUnrealEditor-Golmok\.dylib$' "$B")"
c result-succeeded "$(grep -c -x -F 'Result: Succeeded' "$B")"
c up-to-date "$(grep -c -F 'Target is up to date' "$B")"
c clang-diagnostics "$(grep -c -E ': (warning|error|fatal error):' "$B")"
c undefined-symbols "$(grep -c -F 'Undefined symbols' "$B")"
c niagara-lines "$(grep -c -i 'niagara' "$B")"
```

```sh j21-row-sh
#!/bin/sh
# J-21: prints the two lines (blank, record) that go below the wp16a section 12 table, from the J-21 logs only.
# usage: sh j21_row.sh <E>
E=$1
for f in symbols.diff buildcheck.diff imports.diff otool.diff; do
  if [ "$(cat "$E/$f")" != "exit=0" ]; then echo "j21_row: $f is not exit=0" >&2; exit 3; fi
done
if [ "$(cat "$E/dylib-newer.log")" != "newer=0" ]; then echo "j21_row: dylib-newer.log is not newer=0" >&2; exit 3; fi
date=$(cat "$E/run-date.log")
sha=$(cat "$E/sha.log")
echo
printf 'Mac 부분 선행(J-21, 컴파일·심볼만, %s, SHA %s, UE 5.8.4 CL 58902052): `GolmokWeatherRainFx.cpp`·`GolmokWeatherTest.cpp`를 touch한 증분 `build.sh`에서 두 파일 컴파일과 `libUnrealEditor-Golmok.dylib` 링크, `Result: Succeeded`, 컴파일 경고·오류 줄 0, 빌드 출력의 Niagara 줄 0. #1 `Niagara.uplugin`은 `"EnabledByDefault" : true`, `Golmok.uproject`는 Niagara 명시 항목. #2 `Niagara` 하나로 링크된다(`otool -L`의 Niagara 줄은 `@rpath/libUnrealEditor-Niagara.dylib` 하나, `Golmok.Build.cs`에 NiagaraCore 없음). #3·#17은 컴파일되고, #4·#15가 쓰는 API는 5.8.4 헤더에 있다 — 등록·렌더, `User.` 접두 필요 여부, 바인딩 단언 결과, 텔레포트 뒤 줄무늬는 [미확인]이다(PIE·자동화 몫). #1의 UBT 경고 문구 유무는 이 줄이 판정하지 않는다. 근거: J-21 PR.\n' "$date" "$sha"
```

```text j21-expected-symbols
version Build/Build.version:4:"PatchVersion": 4,
version Build/Build.version:5:"Changelist": 58902052,
r1 Plugins/FX/Niagara/Niagara.uplugin:13:"EnabledByDefault" : true,
r1 unreal/Golmok/Golmok.uproject:30:{"Name": "Niagara", "Enabled": true},
r2 unreal/Golmok/Source/Golmok/Golmok.Build.cs:34:PrivateDependencyModuleNames.Add("Niagara");
r2 unreal/Golmok/Source/Golmok/Golmok.Build.cs:NiagaraCore 0
r2 Plugins/FX/Niagara/Source/Niagara/Public/NiagaraComponent.h:57:class UNiagaraComponent : public UFXSystemComponent
r2 Plugins/FX/Niagara/Source/Niagara/Classes/NiagaraSystem.h:237:UCLASS(BlueprintType, MinimalAPI, meta = (LoadBehavior = "LazyOnDemand"))
r2 Plugins/FX/Niagara/Source/Niagara/Public/NiagaraTypes.h:1115:static NIAGARA_API FNiagaraTypeDefinition FloatDef;
r2 Plugins/FX/Niagara/Source/Niagara/Public/NiagaraTypes.h:1119:static NIAGARA_API FNiagaraTypeDefinition Vec3Def;
r3 Plugins/FX/Niagara/Source/Niagara/Public/NiagaraComponent.h:295:NIAGARA_API void SetAsset(UNiagaraSystem* InAsset, bool bResetExistingOverrideParameters = true);
r3 Source/Runtime/Engine/Classes/Components/SceneComponent.h:1605:ENGINE_API void SetUsingAbsoluteRotation(const bool bInAbsoluteRotation);
r3 Source/Runtime/Engine/Classes/GameFramework/Actor.h:2493:ENGINE_API bool SetRootComponent(USceneComponent* NewRootComponent);
r3 Source/Runtime/Engine/Classes/GameFramework/Actor.h:4348:ENGINE_API void AddInstanceComponent(UActorComponent* Component);
r3 Source/Runtime/Engine/Classes/Components/ActorComponent.h:1322:ENGINE_API void RegisterComponent();
r4 Plugins/FX/Niagara/Source/Niagara/Public/NiagaraComponent.h:533:NIAGARA_API void SetVariableFloat(FName InVariableName, float InValue);
r4 Plugins/FX/Niagara/Source/Niagara/Public/NiagaraComponent.h:506:NIAGARA_API void SetVariableVec3(FName InVariableName, FVector InValue);
r4 Plugins/FX/Niagara/Source/Niagara/Public/NiagaraComponent.h:746:const FNiagaraParameterStore& GetOverrideParameters() const { return OverrideParameters; }
r4 Plugins/FX/Niagara/Source/Niagara/Public/NiagaraParameterStore.h:510:NIAGARA_API virtual const int32* FindParameterOffset(const FNiagaraVariableBase& Parameter, bool IgnoreType = false) const;
r4 Plugins/FX/Niagara/Source/Niagara/Public/NiagaraParameterStore.h:405:inline T GetParameterValue(const FNiagaraVariableBase& Parameter)const
r4 Plugins/FX/Niagara/Source/Niagara/Classes/NiagaraSystem.h:368:const FNiagaraUserRedirectionParameterStore& GetExposedParameters() const { return ExposedParameters; }
r15 Plugins/FX/Niagara/Source/Niagara/Public/NiagaraComponent.h:228:NIAGARA_API virtual void DeactivateImmediate() override;
r15 Plugins/FX/Niagara/Source/Niagara/Public/NiagaraComponent.h:646:NIAGARA_API void ResetSystem();
r15 Source/Runtime/Engine/Classes/Engine/World.h:496:enum class ESpawnActorNameMode : uint8
r15 Source/Runtime/Engine/Classes/Engine/World.h:508:Requested
r15 Source/Runtime/Engine/Classes/Engine/World.h:512:ESpawnActorNameMode NameMode;
r15 Source/Runtime/CoreUObject/Public/UObject/ObjectMacros.h:596:RF_Transient =0x00000040, ///< Don't save object.
r17 unreal/Golmok/Source/Golmok/Map/GolmokTravelSubsystem.h:14:DECLARE_MULTICAST_DELEGATE_OneParam(FGolmokOnTraveled, const FString& /*ZoneId*/);
r17 unreal/Golmok/Source/Golmok/Tests/GolmokWeatherTest.cpp:1240:Test->TestTrue(TEXT("the weather subsystem is bound to OnTraveled"), Travel->OnTraveled.IsBoundToObject(W));
r17 Source/Runtime/Core/Public/Delegates/MulticastDelegateBase.h:150:inline bool IsBoundToObject(FDelegateUserObjectConst InUserObject) const
r17 Source/Runtime/Core/Public/Delegates/DelegateSignatureImpl.inl:760:using Super::IsBoundToObject;
```

```text j21-expected-buildcheck
compile-lines 2
compile-rainfx 1
compile-weathertest 1
link-golmok 1
result-succeeded 1
up-to-date 0
clang-diagnostics 0
undefined-symbols 0
niagara-lines 0
```

```text j21-expected-imports
FNiagaraTypeDefinition::FloatDef
FNiagaraTypeDefinition::IntStruct
FNiagaraTypeDefinition::Vec3Def
FNiagaraTypeDefinitionHandle::Register(FNiagaraTypeDefinition const&) const
FNiagaraTypeDefinitionHandle::Resolve() const
UNiagaraComponent::ResetSystem()
UNiagaraComponent::SetAsset(UNiagaraSystem*, bool)
UNiagaraComponent::SetVariableFloat(FName, float)
UNiagaraComponent::SetVariableVec3(FName, UE::Math::TVector<double>)
Z_Construct_UClass_UNiagaraComponent(ETypeConstructPhase)
Z_Construct_UClass_UNiagaraSystem(ETypeConstructPhase)
```

```text j21-expected-otool
@rpath/libUnrealEditor-Niagara.dylib (compatibility version 5.8.0, current version 5511.68.0)
```

- **명령 공통**: 셸 변수는 Bash 호출 사이에 남지 않는다. 그래서 **모든 명령은 `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/jaehwan/J-21";`로 시작하고**, 그 뒤는 `cd "$W" &&`·`cd "$W/tools" &&`·`git -C "$W"`·`"$E/…"` 절대 경로로 시작한다(상시 규칙). 아래 명령에는 이 앞머리를 적지 않았다. 돌린 명령 원문은 `"$E/commands.txt"`에 한 줄씩 더한다(규칙 10). 각 단계의 "기대"와 다르면 **멈춤 조건**을 본다. 할 일 3·4의 `build.sh`와 할 일 6의 게이트 두 번(`gate`·`gate-2`)·`gh pr checks --watch`는 **항상** 하네스의 백그라운드 실행으로 돌리고, 그 명령이 쓰는 `.rc` 파일(`gh pr checks --watch`는 `checks-watch.log`의 `exit=` 줄)이 생길 때까지 기다린다(명령은 바꾸지 않는다). 그 밖의 명령은 앞쪽(foreground)으로 돌린다.
  - **GUI 잠금**(할 일 3·4, [mac-setup §3](../runbooks/mac-setup.md) 표의 규칙, J-27과 같은 꼴): 확인 `L="$TMPDIR/claude/gui-foreground.lock"; if [ -e "$L" ]; then cat "$L"; else echo "no lock"; fi > "$E/lock-check.log"; date -u +%FT%TZ >> "$E/lock-check.log"` — 기대 첫 줄 `no lock`. 다른 줄이 있으면 **지우지 않고** 그 줄을 영록에게 보내고 기다린다. 잡기 `mkdir -p "$TMPDIR/claude" && (set -C; printf '%s %s %s\n' "재환" "J-21-build" "$(date -u +%FT%TZ)" > "$TMPDIR/claude/gui-foreground.lock"); echo $? > "$E/lock-take.rc"` — 기대 `0`. 풀기 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-21-build ' "$L" && rm "$L"; echo $? > "$E/lock-release.rc"` — 기대 `0`.
  - **잠금 갱신**([AGENTS.md](../../AGENTS.md) "UE를 같이 쓰는 규칙"·mac-setup §3: 20분이 지난 기록은 빈 것으로 보므로 잡은 쪽이 쓰는 동안 갱신한다): ① 할 일 3·4의 `build.sh` 바로 앞에 매번 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-21-build ' "$L" && printf '%s %s %s\n' "재환" "J-21-build" "$(date -u +%FT%TZ)" > "$L"; echo $? > "$E/lock-refresh-<n>.rc"` — `<n>`은 할 일 3이면 `build0`, 4면 `build1`. 기대 `0`. 0이 아니면(잠금 줄이 `재환 J-21-build`가 아니다) 잠금 파일을 지우거나 쓰지 않고 멈춘다. ② `build.sh`는 갱신 루프로 감싸 **적힌 그대로** 돌린다: 앞머리 뒤에 `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-21-build ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-21-build" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!;`, 명령 끝에 `; kill "$RP"`. 할 일 3·4의 명령에는 이 루프가 이미 들어 있다.
- **할 일**:
  1. **준비**: `mkdir -p "$E" && git -C "$W" status --porcelain > "$E/status-before.log"; grep -c -v '^?? ' "$E/status-before.log" > "$E/status-before-tracked.log"` — 기대 `0`(추적 파일 변경이 있으면 멈춘다; `??` 줄은 그대로 둔다). `git -C "$W" fetch origin && git -C "$W" switch -c local/jaehwan-j21-wp16a-api origin/main > "$E/switch.log" 2>&1; echo $? > "$E/switch.rc"` — 기대 `0`. `git -C "$W" rev-parse --short HEAD > "$E/sha.log"; git -C "$W" rev-parse HEAD origin/main | uniq | wc -l | tr -d ' ' > "$E/sha-same.log"` — 기대 `1`. `git -C "$W" show origin/main:docs/plan/jaehwan-tasks.md > "$E/tasks-main.md"; git -C "$W" rev-parse origin/main > "$E/main-rev.log"; { awk '/^#### J-21 /{f=1} /^#### J-22/{f=0} f' "$E/tasks-main.md"; awk '/^### PR 본문 공통\(모든 과제\)$/{f=1} /^## 리뷰·병합 절차$/{f=0} f' "$E/tasks-main.md"; } > "$E/task.txt"`(규칙 14·17 c, 상시 규칙 "PR 본문 공통" 1) — 기대 `head -1 "$E/task.txt"`가 `#### J-21 `로 시작, `grep -c -x '### PR 본문 공통(모든 과제)' "$E/task.txt"` `1`. 펜스 추출(손으로 옮기지 않는다): `` printf '%s\n' "j21-symbols-sh j21_symbols.sh" "j21-buildcheck-sh j21_buildcheck.sh" "j21-row-sh j21_row.sh" "common-ph-awk ph.awk" "j21-expected-symbols expected-symbols.txt" "j21-expected-buildcheck expected-buildcheck.txt" "j21-expected-imports expected-imports.txt" "j21-expected-otool expected-otool.txt" | while read -r n f; do awk -v n="$n" '$0 == "```" && x {x=0} x {print} $0 ~ ("^```[a-z]+ " n "$") {x=1}' "$E/task.txt" > "$E/$f"; done; cd "$E" && wc -l j21_symbols.sh j21_buildcheck.sh j21_row.sh ph.awk expected-symbols.txt expected-buildcheck.txt expected-imports.txt expected-otool.txt > "$E/extract-wc.log" ``(zsh는 따옴표 없는 변수를 낱말로 나누지 않으므로 `read -r n f`로 나눈다) — 기대(앞 숫자, 순서대로): `51`, `14`, `12`, `37`, `31`, `9`, `11`, `1`, 끝 줄 `166 total`. 겹침: `cd "$W" && gh pr list --state open --json number,headRefName,files --jq '.[]|select(any(.files[]; .path=="docs/runbooks/pc-verify-wp16a.md"))|"\(.number) \(.headRefName)"' > "$E/overlap.log" 2>&1` — 기대 빈 파일. 같은 프로젝트를 연 편집기와 도는 UBT가 없어야 한다: `pgrep -fl '[g]olmok-jaehwan/unreal/Golmok/Golmok.uproject' > "$E/editor-before.log"; echo $? > "$E/editor-before.rc"; pgrep -fl '[U]nrealBuildTool' > "$E/ubt-before.log"; echo $? > "$E/ubt-before.rc"` — 기대 두 rc 모두 `1`(빈 파일).
  2. **심볼(엔진 헤더 읽기, UE 실행 없음)**: `sh "$E/j21_symbols.sh" "/Users/Shared/Epic Games/UE_5.8/Engine" "$W" > "$E/symbols.log" 2> "$E/symbols.err"; diff "$E/expected-symbols.txt" "$E/symbols.log" > "$E/symbols.diff"; echo "exit=$?" >> "$E/symbols.diff"` — 기대 `symbols.diff`가 `exit=0` 한 줄, `wc -l < "$E/symbols.log" | tr -d ' '` `31`, `grep -c 'MISSING' "$E/symbols.log"` `0`, `symbols.err` 빈 파일.
  3. **기준 빌드**: GUI 잠금 확인·잡기. 잠금 갱신 ①(`build0`). 빌드(하네스 백그라운드): `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-21-build ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-21-build" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && /usr/bin/timeout 1800 ./tools/ue/build.sh > "$E/build-0.log" 2>&1; echo $? > "$E/build-0.rc"; kill "$RP"` — 기대 `build-0.rc` `0`, `grep -c -x -F 'Result: Succeeded' "$E/build-0.log"` `1`(무엇을 컴파일했는지는 판정하지 않는다).
  4. **touch와 증분 빌드**: `touch "$E/touch-marker" && sleep 1 && cd "$W" && touch unreal/Golmok/Source/Golmok/Weather/GolmokWeatherRainFx.cpp unreal/Golmok/Source/Golmok/Tests/GolmokWeatherTest.cpp; echo $? > "$E/touch.rc"` — 기대 `0`. `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-touch.diff"; echo "exit=$?" >> "$E/status-touch.diff"` — 기대 `exit=0` 한 줄(내용은 그대로다). 잠금 갱신 ①(`build1`). 빌드(하네스 백그라운드): `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-21-build ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-21-build" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && date +%F > "$E/run-date.log" && /usr/bin/timeout 1800 ./tools/ue/build.sh > "$E/build-1.log" 2>&1; echo $? > "$E/build-1.rc"; kill "$RP"`(`run-date.log`는 기록 줄의 날짜 — Mac의 현지 날짜) — 기대 `build-1.rc` `0`. 세기: `sh "$E/j21_buildcheck.sh" "$E/build-1.log" > "$E/buildcheck.log"; diff "$E/expected-buildcheck.txt" "$E/buildcheck.log" > "$E/buildcheck.diff"; echo "exit=$?" >> "$E/buildcheck.diff"` — 기대 `exit=0` 한 줄. 컴파일·링크 줄 원문(기록만, PR 본문용): `grep -E '^\[[0-9]+/[0-9]+\] (Compile|Link) \[Apple\] ' "$E/build-1.log" > "$E/build-1-actions.log"`. 링크 증거: `DY="$W/unreal/Golmok/Binaries/Mac/libUnrealEditor-Golmok.dylib"; [ "$DY" -nt "$E/touch-marker" ]; echo "newer=$?" > "$E/dylib-newer.log"; nm -u "$DY" | c++filt | grep -i niagara | LC_ALL=C sort > "$E/imports.txt"; diff "$E/expected-imports.txt" "$E/imports.txt" > "$E/imports.diff"; echo "exit=$?" >> "$E/imports.diff"; otool -L "$DY" | grep -i niagara | sed 's/^[[:space:]]*//' > "$E/otool-niagara.log"; diff "$E/expected-otool.txt" "$E/otool-niagara.log" > "$E/otool.diff"; echo "exit=$?" >> "$E/otool.diff"` — 기대 `dylib-newer.log` `newer=0`, `imports.diff`·`otool.diff` 모두 `exit=0` 한 줄. 남은 UBT: `pgrep -fl '[U]nrealBuildTool' > "$E/ubt-after.log"; echo $? > "$E/ubt-after.rc"` — 기대 `1`. 잠금 풀기.
  5. **런북 두 줄**: `sh "$E/j21_row.sh" "$E" > "$E/row21.txt"; echo $? > "$E/row.rc"` — 기대 rc `0`, `wc -l < "$E/row21.txt" | tr -d ' '` `2`, `head -n 1 "$E/row21.txt" | grep -c '^$'` `1`. 손으로 옮기지 않고 명령으로 `docs/runbooks/pc-verify-wp16a.md`의 §12 표 마지막 행(`| 20 | `으로 시작하는 줄 — 파일에 하나뿐, 2026-11-28 :339) **바로 다음**에 넣는다: `cd "$W" && sed -i '' "/^| 20 | /r $E/row21.txt" docs/runbooks/pc-verify-wp16a.md; echo $? > "$E/row-insert.rc"` — 기대 `0`. 이 명령은 한 번만 돌린다(두 번 돌리면 아래 `grep -c`가 `2`가 된다 — 멈춤). 확인: `cd "$W" && awk '/^\| 20 \| /{getline a; getline b; print a; print b}' docs/runbooks/pc-verify-wp16a.md | diff - "$E/row21.txt" > "$E/row-diff.log"; echo "exit=$?" >> "$E/row-diff.log"` — 기대 `exit=0` 한 줄. `cd "$W" && grep -c '^Mac 부분 선행(J-21, ' docs/runbooks/pc-verify-wp16a.md` `1`, `cd "$W" && grep -c '^Mac 부분 선행(J-20, ' docs/runbooks/pc-verify-wp16a.md` `1`(있는 기록 그대로, 규칙 16). 칸 자기 검사(규칙 17 b): `cd "$W" && git diff -U0 origin/main -- docs/runbooks/pc-verify-wp16a.md | grep '^+[^+]' > "$E/cell-lines-1.txt"; wc -l < "$E/cell-lines-1.txt" | tr -d ' ' > "$E/cell-lines-1-count.log"; grep -n -E '\.log|영록|R[0-9]{3}' "$E/cell-lines-1.txt" > "$E/cell-grep-1.log"; wc -l < "$E/cell-grep-1.log" | tr -d ' ' > "$E/cell-grep-1-count.log"` — 기대 `cell-lines-1-count.log` `1`, `cell-grep-1-count.log` `0`(상시 규칙 "PR 본문 공통" 7 — 0이 아니면 줄을 손으로 고치지 않고 멈춘다). `cd "$W" && git diff --numstat -- docs/runbooks/pc-verify-wp16a.md | tr '\t' ' '` `2 0 docs/runbooks/pc-verify-wp16a.md`. `git -C "$W" status --porcelain > "$E/status-after.log"; grep -v -x -F ' M docs/runbooks/pc-verify-wp16a.md' "$E/status-after.log" | diff "$E/status-before.log" - > "$E/status.diff"; echo "exit=$?" >> "$E/status.diff"` — 기대 `exit=0` 한 줄(빌드가 저장소에 남긴 것이 없다).
  6. **게이트·커밋·push**: `cd "$W/tools" && source .venv/bin/activate && { /usr/bin/timeout 300 ruff check . && /usr/bin/timeout 300 ruff format --check . && /usr/bin/timeout 1800 pytest -q && /usr/bin/timeout 300 python scripts/check_repo.py; } > "$E/gate.log" 2>&1; echo $? > "$E/gate.rc"`(하네스 백그라운드) — 기대 `0`(rc 124 = 시간 초과, 다시 돌리지 않고 멈춤). `check_repo.py`는 `](`를 링크로 읽는다 — 행 문구에는 `[미확인]이다(`처럼 `](`가 없다(Opus dry-run). 커밋: `cd "$W" && git add docs/runbooks/pc-verify-wp16a.md && git diff --cached --name-only > "$E/c1-files.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-21: pc-verify-wp16a §12 아래 Mac 부분 선행 줄 — #1·#2·#3·#4·#15·#17 컴파일·심볼" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c1-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author.log"` — 기대: `c1-files.log` 한 줄 `docs/runbooks/pc-verify-wp16a.md`, `author.log` `재환 <jaehwan.local@localhost>`. 게이트 로그가 런북보다 새것인지: `[ "$E/gate.log" -nt "$W/docs/runbooks/pc-verify-wp16a.md" ]; echo "newer=$?" > "$E/mtime.log"` — 기대 `newer=0`. `git -C "$W" push -u origin local/jaehwan-j21-wp16a-api > "$E/push.log" 2>&1; echo "exit=$?" >> "$E/push.log"` — 기대 끝 줄 `exit=0`. 브랜치 파일: `git -C "$W" diff --name-only origin/main...HEAD > "$E/branch-files.log"` — 기대 한 줄 `docs/runbooks/pc-verify-wp16a.md`. push 뒤 상태: `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-final.diff"; echo "exit=$?" >> "$E/status-final.diff"` — 기대 `exit=0` 한 줄. PR 열기(첫 본문은 CI 자리 한 줄뿐 — 규칙 2a): `printf '%s\n' '## 요약' '' 'WP-16a §12 컴파일·심볼 행(#1·#2·#3·#4·#15·#17) Mac 부분 선행 기록. 본문은 CI 뒤에 채운다.' '' '## CI' '' 'CI 진행 중 — 결과는 아래에 추가' > "$E/pr-body-initial.md"; cd "$W" && gh pr create --base main --head local/jaehwan-j21-wp16a-api --title "J-21: WP-16a §12 컴파일·심볼 행 Mac 부분 선행(#1·#2·#3·#4·#15·#17)" --body-file "$E/pr-body-initial.md" > "$E/pr-create.log" 2>&1; echo $? > "$E/pr-create.rc"` — 기대 `0`. PR 번호: `cd "$W" && gh pr view local/jaehwan-j21-wp16a-api --json number --jq .number > "$E/pr-number.log" 2> "$E/pr-number.err"` — 기대 숫자 한 줄(`grep -c -x '[0-9][0-9]*' "$E/pr-number.log"` `1`, `wc -l < "$E/pr-number.log" | tr -d ' '` `1`; `pr-number.err`는 판정하지 않는다). **커밋 2(PR 번호, 상시 규칙 "PR 본문 공통" 8)**: `N=$(cat "$E/pr-number.log"); sed "s/ 근거: J-21 PR\.\$/ 근거: PR #$N./" "$E/row21.txt" > "$E/row21-final.txt"; cd "$W" && sed -i '' "s/ 근거: J-21 PR\.\$/ 근거: PR #$N./" docs/runbooks/pc-verify-wp16a.md; echo $? > "$E/row-pr.rc"` — 기대 `0`. 확인: `cd "$W" && awk '/^\| 20 \| /{getline a; getline b; print a; print b}' docs/runbooks/pc-verify-wp16a.md | diff - "$E/row21-final.txt" > "$E/row-final-diff.log"; echo "exit=$?" >> "$E/row-final-diff.log"` — 기대 `exit=0` 한 줄. `cd "$W" && grep -c ' 근거: J-21 PR\.$' docs/runbooks/pc-verify-wp16a.md` `0`. `cd "$W" && git diff --numstat origin/main -- docs/runbooks/pc-verify-wp16a.md | tr '\t' ' '` `2 0 docs/runbooks/pc-verify-wp16a.md`. 칸 자기 검사: `cd "$W" && git diff -U0 origin/main -- docs/runbooks/pc-verify-wp16a.md | grep '^+[^+]' > "$E/cell-lines-2.txt"; wc -l < "$E/cell-lines-2.txt" | tr -d ' ' > "$E/cell-lines-2-count.log"; grep -n -E '\.log|영록|R[0-9]{3}' "$E/cell-lines-2.txt" > "$E/cell-grep-2.log"; wc -l < "$E/cell-grep-2.log" | tr -d ' ' > "$E/cell-grep-2-count.log"` — 기대 `cell-lines-2-count.log` `1`, `cell-grep-2-count.log` `0`(상시 규칙 "PR 본문 공통" 7 — 0이 아니면 줄을 손으로 고치지 않고 멈춘다). 게이트 다시(규칙 13): `cd "$W/tools" && source .venv/bin/activate && { /usr/bin/timeout 300 ruff check . && /usr/bin/timeout 300 ruff format --check . && /usr/bin/timeout 1800 pytest -q && /usr/bin/timeout 300 python scripts/check_repo.py; } > "$E/gate-2.log" 2>&1; echo $? > "$E/gate-2.rc"`(하네스 백그라운드) — 기대 `0`(rc 124 = 시간 초과, 다시 돌리지 않고 멈춤). `[ "$E/gate-2.log" -nt "$W/docs/runbooks/pc-verify-wp16a.md" ]; echo "newer=$?" > "$E/mtime-2.log"` — 기대 `newer=0`. 커밋: `cd "$W" && git add docs/runbooks/pc-verify-wp16a.md && git diff --cached --name-only > "$E/c2-files.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-21: 기록 줄의 근거를 PR 번호로" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c2-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-2.log"` — 기대 `c2-files.log` 한 줄 `docs/runbooks/pc-verify-wp16a.md`, `author-2.log` `재환 <jaehwan.local@localhost>`. `git -C "$W" push > "$E/push-2.log" 2>&1; echo "exit=$?" >> "$E/push-2.log"` — 기대 끝 줄 `exit=0`. `git -C "$W" diff --name-only origin/main...HEAD > "$E/branch-files-2.log"` — 기대 한 줄 `docs/runbooks/pc-verify-wp16a.md`. `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-final-2.diff"; echo "exit=$?" >> "$E/status-final-2.diff"` — 기대 `exit=0` 한 줄. CI(하네스 백그라운드, 커밋 2의 push 뒤): `cd "$W" && /usr/bin/timeout 1800 gh pr checks "$(cat "$E/pr-number.log")" --watch --interval 30 > "$E/checks-watch.log" 2>&1; echo "exit=$?" >> "$E/checks-watch.log"; gh pr checks "$(cat "$E/pr-number.log")" > "$E/checks.log" 2>&1` — 기대 모든 행 pass.
  7. **PR 본문**: PR 본문·자리표시 분류·칸 자기 검사·근거 표기는 상시 규칙 "PR 본문 공통(모든 과제)"을 따른다(이 절과 다르면 그 소절을 따른다). `## 결과`에는 관찰한 값만 둔다: `symbols.diff`의 `exit=0`, `buildcheck.log` 9줄과 `build-1-actions.log` 3줄(백틱 펜스 블록에 그대로), `otool-niagara.log` 한 줄, `imports.txt` 줄 수, 런북에 넣은 `row21-final.txt` 둘째 줄(백틱 펜스 블록에 그대로) — 그 펜스 밖에는 과제 번호·규칙 번호·날짜를 쓰지 않는다. `## 실행한 명령`에는 `commands.txt`와 `symbols.log`를 각각 백틱 펜스 블록에. `## 남은 [미확인]`에는 설계 1의 범위 밖 항목을 행 번호와 함께. `## 완료 기준 대조`는 아래 (a)~(h) 한 줄씩. 본문 초안은 `$E/pr-body.md`. 게시 전 검사(규칙 10 e·f) — **대상 로그는 이 목록으로 고정한다**(본문 초안·게시본·`task.txt`·`commands.txt`·검사 로그 자신은 넣지 않는다): `"$E"/symbols.log "$E"/symbols.diff "$E"/build-0.log "$E"/build-1.log "$E"/build-1-actions.log "$E"/buildcheck.log "$E"/imports.txt "$E"/otool-niagara.log "$E"/dylib-newer.log "$E"/row21.txt "$E"/row21-final.txt "$E"/sha.log "$E"/run-date.log "$E"/gate.log "$E"/checks.log`.
     - 인용 검사: `## 결과` 절의 펜스 밖 백틱 문자열마다 그 문자열이 근거로 든 로그 **한 개**를 `"$E/quotes.tsv"`에 `<문자열><탭><위 목록의 파일 이름>`으로 적는다(로그 인용이 아닌 파일 이름·명령은 파일 칸에 `라벨`). 빠진 것 확인: `` awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '`[^`]+`' | sed 's/^`//;s/`$//' | sort -u > "$E/body-quotes.txt"; cut -f1 "$E/quotes.tsv" | sort -u > "$E/tsv-quotes.txt"; comm -23 "$E/body-quotes.txt" "$E/tsv-quotes.txt" > "$E/quotes-missing.log" `` — 기대 빈 파일. 세기: `while IFS="$(printf '\t')" read -r q f; do if [ "$f" = "라벨" ]; then n="라벨"; else n=$(grep -F -c -- "$q" "$E/$f"); fi; printf '%s\t%s\t%s\n' "$n" "$f" "$q"; done < "$E/quotes.tsv" > "$E/quotes-check.log"` — 기대: `cut -f1 "$E/quotes-check.log" | grep -c -x '0'`가 `0`.
     - 숫자 검사: `awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '[0-9]{2,}' | sort -u > "$E/body-numbers.txt"; while read -r x; do printf '%s\t%s\n' "$(cat "$E"/symbols.log "$E"/symbols.diff "$E"/build-0.log "$E"/build-1.log "$E"/build-1-actions.log "$E"/buildcheck.log "$E"/imports.txt "$E"/otool-niagara.log "$E"/dylib-newer.log "$E"/row21.txt "$E"/row21-final.txt "$E"/sha.log "$E"/run-date.log "$E"/gate.log "$E"/checks.log | grep -c -- "$x")" "$x"; done < "$E/body-numbers.txt" > "$E/numbers-check.log"` — 기대: `cut -f1 "$E/numbers-check.log" | grep -c -x '0'`가 `0`.
     - 0이 나온 것은 고치거나 지운다. 그다음 상시 규칙 "PR 본문 공통" 3(점검표 대조)·5(자리표시 분류)·6(조립·게시·다시 읽기)을 적힌 그대로 돌린다.
- **허용 파일**: `docs/runbooks/pc-verify-wp16a.md`(§12 표 `| 20 | ` 행 다음에 빈 줄 + 기록 한 줄 추가만, 펜스 `j21-row-sh`의 출력 그대로 — 커밋 2는 그 줄 끝의 근거 표식만 바꾼다). 그 밖의 저장소 파일은 고치지 않는다: §12 표의 칸·§13 표·J-20 줄·다른 절, C++(`Weather/`·`Tests/`·`Save/` — touch는 내용 변경이 아니고 `git status`에 나오지 않는다), `Golmok.Build.cs`·`Golmok.uproject`(touch도 하지 않는다), 테스트·`tools/`·공유 문서. 빌드 산출물(`Binaries/`·`Intermediate/`)과 `$W`의 `??` 파일은 커밋하지 않는다.
- **멈춤 조건(정하지 말고 영록에게 묻는다)**: `status-before-tracked.log`가 0이 아닐 때(J-35 등 다른 작업이 `$W`에 남았다). `switch.rc`가 0이 아니거나 `sha-same.log`가 1이 아닐 때. `head -1 "$E/task.txt"`가 `#### J-21 `로 시작하지 않을 때. `extract-wc.log`가 기대와 다를 때. `overlap.log`가 비어 있지 않을 때. `editor-before.rc`·`ubt-before.rc`가 1이 아닐 때(끄지 않는다). `symbols.diff`가 `exit=0` 한 줄이 아니거나 `MISSING` 줄이 있거나 `symbols.err`가 비어 있지 않을 때(엔진 패치·프로젝트 줄 번호가 바뀌었다 — 기대값을 고치지 않는다). 잠금 파일에 다른 기록이 있거나 잠금 잡기 rc가 0이 아닐 때. `lock-refresh-build0.rc`·`lock-refresh-build1.rc` 중 하나가 0이 아닐 때(잠금 파일을 지우거나 쓰지 않는다). `build-0.rc`·`build-1.rc`가 0이 아닐 때(124 = 시간 초과, 규칙 5 — 오류 줄과 파일:줄만 보고, **코드를 고치지 않는다**), `build-0.log`의 `Result: Succeeded`가 1이 아닐 때. `touch.rc`가 0이 아니거나 `status-touch.diff`가 `exit=0` 한 줄이 아닐 때. `buildcheck.diff`·`imports.diff`·`otool.diff`·`row-diff.log`·`status.diff`가 `exit=0` 한 줄이 아닐 때(예: 컴파일 줄이 3 이상 — 다른 파일도 다시 컴파일됐다, 또는 `niagara` 줄이 생겼다: 그 줄들을 보고). `dylib-newer.log`가 `newer=0`이 아닐 때. `ubt-after.rc`가 1이 아닐 때(아래 "멈춤 순서"). `row.rc`·`row-insert.rc`·`row-pr.rc`가 0이 아닐 때, `row-final-diff.log`가 `exit=0` 한 줄이 아닐 때, `cell-lines-1-count.log`·`cell-lines-2-count.log`가 `1`이 아니거나 `cell-grep-1-count.log`·`cell-grep-2-count.log`가 `0`이 아닐 때(줄을 손으로 고치지 않는다), `row21.txt`가 2줄이 아니거나 첫 줄이 비어 있지 않을 때, J-21 줄 `grep -c`가 1이 아니거나 J-20 줄이 1이 아닐 때, numstat이 기대와 다를 때. `gate.rc`·`gate-2.rc`가 0이 아닐 때(rc 124 포함, 다른 파일을 고치거나 `ruff format`으로 바꾸지 않는다). `c1-files.log`·`author.log`·`c2-files.log`·`author-2.log`가 기대와 다를 때. `mtime.log`·`mtime-2.log`가 `newer=0`이 아닐 때. `lock-release.rc`가 0이 아닐 때(잠금 파일을 지우지 않는다). `push.log`·`push-2.log`가 `exit=0`으로 끝나지 않을 때, `branch-files.log`·`branch-files-2.log`가 `docs/runbooks/pc-verify-wp16a.md` 한 줄이 아니거나 `status-final.diff`·`status-final-2.diff`가 `exit=0` 한 줄이 아닐 때. 상시 규칙 "PR 본문 공통" 9의 공통 멈춤 조건. `pr-create.rc`·`pr-edit.rc`가 0이 아니거나 `pr-number.log`가 숫자 한 줄이 아닐 때. `checks.log`에 pass가 아닌 행이 있을 때. macOS 권한 창이 뜰 때(누르지 않는다 — 소유자 항목). 그 밖에 이 절의 "기대"와 다른 값이 하나라도 나올 때. **멈춤 순서 — 할 일 3·4 안에서 멈출 때는 이 순서로 한다**: ① `pgrep -fl '[U]nrealBuildTool' > "$E/ubt-stop.log"; echo $? > "$E/ubt-stop.rc"`. ② rc가 `1`이면 ③으로 간다. rc가 `0`이면(UBT가 남았다) 프로세스를 건드리지 않고, 잠금을 풀지 않은 채 `ubt-stop.log`를 영록에게 보낸다. ③ 그다음에만 잠금 풀기를 돌려 `lock-release.rc`를 남기고 묻는다.
- **완료 기준**:
  - (a) 준비: `status-before-tracked.log` `0`, `switch.rc` `0`, `sha-same.log` `1`, `task.txt` 첫 줄 `#### J-21 `, `extract-wc.log` 원문(기대 숫자와 같다), `overlap.log` 빈 파일, `editor-before.rc` `1`, `ubt-before.rc` `1`.
  - (b) 심볼: `symbols.diff` `exit=0` 한 줄, `symbols.log` 31줄, `MISSING` 0, `symbols.err` 빈 파일.
  - (c) 기준 빌드: `lock-take.rc` `0`, `lock-refresh-build0.rc` `0`, `build-0.rc` `0`, `build-0.log`의 `Result: Succeeded` `1`.
  - (d) 증분 빌드: `touch.rc` `0`, `status-touch.diff` `exit=0`, `lock-refresh-build1.rc` `0`, `build-1.rc` `0`, `buildcheck.diff` `exit=0`, `build-1-actions.log` 원문, `dylib-newer.log` `newer=0`, `imports.diff`·`otool.diff` `exit=0`, `ubt-after.rc` `1`, `lock-release.rc` `0`.
  - (e) 런북: `row.rc` `0`, `row21.txt` 2줄(첫 줄 빈 줄), `row-insert.rc` `0`, `row-diff.log` `exit=0`, J-21 줄 `grep -c` `1`, J-20 줄 `grep -c` `1`, numstat `2 0 docs/runbooks/pc-verify-wp16a.md`, `status.diff` `exit=0`, `cell-lines-1-count.log` `1`, `cell-grep-1-count.log` `0`.
  - (f) 커밋: `branch-files.log` `docs/runbooks/pc-verify-wp16a.md` 한 줄, `c1-files.log` 같은 한 줄, `author.log` `재환 <jaehwan.local@localhost>`, `push.log` 끝 줄 `exit=0`, `status-final.diff` `exit=0` 한 줄, `pr-create.rc` `0`, `pr-number.log` 숫자 한 줄. 커밋 2: `row-pr.rc` `0`, `row-final-diff.log` `exit=0`, `근거: J-21 PR.` 0줄, `origin/main` 대비 numstat `2 0 docs/runbooks/pc-verify-wp16a.md`, `cell-lines-2-count.log` `1`, `cell-grep-2-count.log` `0`, `gate-2.rc` `0`, `mtime-2.log` `newer=0`, `c2-files.log`·`author-2.log` 기대대로, `push-2.log` 끝 줄 `exit=0`, `branch-files-2.log` 한 줄, `status-final-2.diff` `exit=0`.
  - (g) 게이트 `gate.rc` `0`, `mtime.log` `newer=0`. CI `checks.log` 모든 행 pass 원문(규칙 2).
  - (h) PR 본문: 절 순서(상시 규칙 "PR 본문 공통" 2), "완료 기준 대조" 절, 점검표(그날 규칙 수만큼, 소절 3). `quotes-missing.log` 빈 파일, `quotes-check.log`·`numbers-check.log`에 0 없음. 공통 완료 기준 (P)(소절 10): `checklist.diff` `exit=0`, `ph-unfilled.log` `0`, `pr-edit.rc` `0`, `ph-posted-unfilled.log` `0`, `ph-table.diff` `exit=0`, `signature-last.log` `1`.
- **병합 시 반영(영록)**: STATUS 재환 절에 J-21 행. 선택: 같은 줄 뒤에 날짜를 단 메모로 J-12 전체 빌드 UBT 로그(`Log-backup-2026.11.27-18.38.39.txt` 또는 J-21 빌드의 UBT `Log.txt` — 이 Mac은 ispc가 없어 빌드마다 makefile을 다시 만든다)의 `niagara` 0줄을 적어 #1의 "전체 재생성 빌드" 절반을 닫을지 — 그 파일이 병합 때까지 남아 있고 영록이 다시 읽은 경우만(UBT가 오래된 백업을 지운다). §12 칸은 PC 카드 V-16 몫으로 그대로 둔다.
- **왜 재환 / 위험**: 모든 판정이 고정 기대값과의 `diff`·`grep -c`·종료 코드로 끝나고, 기록 줄은 펜스가 만든다. 코드도 Astra 레인도 건드리지 않는다. 위험: ① 컴파일을 동작으로 넓히는 것(규칙 1·3·15) — 행 문구가 등록·렌더·접두·단언·줄무늬를 [미확인]으로 남긴다. ② 엔진 패치 갱신(5.8.5 등)이나 `origin/main`의 소스 변경으로 줄 번호·import 목록이 바뀜 — `diff`가 막고 멈춘다(기대값은 영록이 다시 만든다). ③ 기준 빌드 뒤에도 다른 파일이 다시 컴파일됨(예: 하네스가 다른 파일을 건드림) — `compile-lines 2`가 막는다. ④ 빌드 실패를 "고치는" 것 — 머리말 :11은 PC 세션 규칙이고 재환은 보고만 한다. ⑤ 표 칸을 고치는 것 — 허용 파일이 표 아래 두 줄뿐이다.
- **dry-run 범위(Opus 2026-11-28)**: `origin/main` `8a4b3c7`의 scratch 사본(`git archive`)에서 한 것: 펜스 `j21-symbols-sh`를 실제 엔진 `/Users/Shared/Epic Games/UE_5.8/Engine`(5.8.4 CL 58902052)과 scratch 사본에 zsh·sh로 돌려 31줄(탭 없음, `MISSING` 0, rc 0)을 얻었고 그것이 펜스 `j21-expected-symbols`다(두 셸 출력 같음). `W`를 없는 경로로 주면 출력이 27줄이 되어 `diff`가 0이 아니고(바뀐 줄 6), 엔진 `Build.version`의 `PatchVersion`을 5로 바꾼 사본을 주면 `version Build/Build.version:MISSING` 줄이 나온다(빈 검사 아님). 펜스 `j21-buildcheck-sh`는 J-17의 실제 UBT 로그(`Log-backup-2026.11.27-21.52.51.txt`)에서 두 파일 이름만 바꾼 합성 로그로 `j21-expected-buildcheck`와 같았고, 원래 J-17 로그(다른 두 파일)에서는 `compile-rainfx 0`·`compile-weathertest 0`, 업투데이트 로그(`Log.txt`)에서는 `compile-lines 0`·`up-to-date 1`로 달랐다. 링크 증거 명령(`nm -u | c++filt`, `otool -L`)은 지금 `$W`의 dylib(2026-11-28 06:53 빌드, 읽기만)에 돌려 펜스 `j21-expected-imports`(11줄)·`j21-expected-otool`을 얻었다. `j21-row-sh`는 가짜 `exit=0` 입력에서 2줄(빈 줄 + 기록), `imports.diff`를 `exit=1`로 바꾸면 rc 3. 그 두 줄을 git으로 만든 scratch 사본의 `pc-verify-wp16a.md`에 할 일 5의 `sed -i '' "/^| 20 | /r …"`로 넣어 `row-insert.rc` `0`, `row-diff.log` `exit=0`, J-21 줄 1·J-20 줄 1, numstat `2 0`, `git status`는 ` M docs/runbooks/pc-verify-wp16a.md` 한 줄. 첫 문안의 `[미확인](PIE·자동화)`는 `check_repo.py`가 깨진 링크로 실패시켜(`FAIL … 깨진 링크 PIE·자동화`) `[미확인]이다(PIE·자동화 몫)`로 바꿨고, 바꾼 뒤 파이썬 게이트 전체(`ruff check`·`ruff format --check`·`pytest -q` 1937 passed 3 skipped·`check_repo.py` OK) 통과. 할 일 1의 펜스 추출과 `wc -l`은 이 절을 그대로 담은 파일에서 돌려 기대 숫자를 얻었다. dry-run하지 못한 것: 실제 `build.sh` 두 번(특히 `build.sh` 표준 출력의 줄 꼴 — UBT `Log.txt`와 같은 `[n/N] Compile [Apple] …`·`Result: Succeeded` 줄이라는 것은 J-17 PR #149 본문의 build.log 인용으로만 확인), touch 뒤 정확히 두 TU만 다시 컴파일되는지(J-17 로그가 같은 꼴을 보였다), 새로 링크된 dylib의 import 목록, 실제 `$W` 경로에서의 `diff`, `gh` 명령, 인용·숫자 검사(본문이 없어서), 실제 240초 갱신 루프. 문서 7 수정(2026-11-28, Opus): `j21-row-sh`의 범위 문장과 `근거: J-21 PR.` 표식을 바꾼 뒤 가짜 `exit=0` 입력에서 2줄·rc 0, 기록 줄에 규칙 17 b의 `grep -n -E` 0건. 할 일 1의 두 `awk` 추출과 펜스 추출 `wc -l`(`166 total`), 할 일 6의 커밋 2 `sed`(가짜 번호)와 `awk getline` 확인 `diff` 0은 scratch 사본에서 돌렸다. UBT 로그의 `Invalidating makefile` 줄과 `niagara` 0은 `~/Library/Application Support/Epic/UnrealBuildTool/`의 실제 로그를 읽어 확인했다(읽기만).
- **결과(2026-11-28, [#160](https://github.com/wooklym/golmok/pull/160) · `37b6af8`, 리뷰 R160)**: pc-verify-wp16a §12 표 아래에 "Mac 부분 선행(J-21, 컴파일·심볼만, 2026-11-28, SHA 366e118, UE 5.8.4 CL 58902052)" 줄을 더했다(그 파일 +2 −0, §12 칸·§13 표·J-20 줄은 그대로). 그 줄의 관찰: `GolmokWeatherRainFx.cpp`·`GolmokWeatherTest.cpp`를 touch한 증분 `build.sh`에서 두 파일 컴파일과 `libUnrealEditor-Golmok.dylib` 링크, `Result: Succeeded`, 컴파일 경고·오류 줄 0, 빌드 출력의 Niagara 줄 0. #1 `Niagara.uplugin` `"EnabledByDefault" : true`와 `Golmok.uproject`의 Niagara 명시 항목, #2 `otool -L`의 Niagara 줄은 `@rpath/libUnrealEditor-Niagara.dylib` 하나, #3·#17은 컴파일되고 #4·#15가 쓰는 API는 5.8.4 헤더에 있다. 등록·렌더, `User.` 접두 필요 여부, 바인딩 단언 결과, 텔레포트 뒤 줄무늬, #1의 UBT 경고 문구 유무는 [미확인]으로 남았다(PIE·자동화 몫). R160(Opus 검증 2렌즈 — 빌드 로그의 컴파일·링크 줄, 경고 0, `otool -L`, 5.8.4 헤더 심볼을 리뷰어가 직접 대조)은 첫 제출에 병합을 판정했고(병합 커밋 본문, PR 코멘트 없음), 남은 지적(점검표의 넓게 쓰인 세 줄, 정정 줄 하나)은 재환에게 통보했다.

#### J-22 V-16 §11 Mac 패키지 명령 이식: 에셋 전 기대 결과 — 설계 확정(Opus 2026-11-28)
- **출처**: [pc-verify-wp16a.md](../runbooks/pc-verify-wp16a.md) §11(:302-316, Windows 명령 6줄과 체크 4개), §13 결과 표(:343-364)와 그 아래 J-20의 "Mac 부분 선행" 줄(:366 — J-21 #160이 §12 표 아래에 두 줄을 더한 뒤의 줄 번호), §2(:60-66, 에셋 없을 때의 Warning 2줄과 시작 줄 `mpc missing, fx missing`). [mac-setup](../runbooks/mac-setup.md) §3 표 `UnrealPak.exe`·`Manifest_UFSFiles_Win64.txt`·`Golmok-Windows.utoc` 행(:137)·패키지 Saved 행(:138), §6 V-16 행(:241), §8 #10(:296 — 매니페스트는 `unreal/Golmok/Saved/StagedBuilds/Mac/`, utoc는 `Golmok.app/Contents/UE/Golmok/Content/Paks/`), #12(:298 — 샌드박스 컨테이너). `tools/ue/package.sh:28-36`(`--out-dir`가 있으면 그 폴더, `Package output: <폴더>` 줄 :37), `:39-42`(`Content/GASP`가 있으면 `WARNING: Content/GASP exists …`), `:48-50`(`BuildCookRun … -build -cook -stage -pak -package -archive`, `:43-44` 주석대로 UAT가 에디터 타깃도 빌드한다 — J-15도 `package.sh`만 돌렸으므로 `build.sh`를 따로 돌리지 않는다). 설정: `Config/DefaultGame.ini:19`(`+DirectoriesToAlwaysStageAsUFS=(Path="../Config/Golmok")` — `weather.json`이 매니페스트에 오는 이유), `:141`(`+DirectoriesToAlwaysCook=(Path="/Game/Golmok/Weather")`, §12 #13), `Config/DefaultEngine.ini:3`(`GameDefaultMap=/Game/Golmok/Maps/L_Dev.L_Dev` — 맵 인자 없는 실행이 여는 맵, `L_Dev.umap`은 git 밖 `.gitignore:18`), `Config/Golmok/weather.json:3-5`(`initial` clear·fixed, `transition_seconds` 20.0, `heavy` 1.0)와 `schedule` 10칸. 날씨 코드 `Weather/GolmokWeatherSubsystem.cpp`: `:231`·`:261`(에셋 없음 Warning 2줄, 자동화 밖에서), `:282`(시작 줄 `weather: %s %s, transition %.1f s, %d schedule slots, mpc %s, fx %s`), `:387-397`(`StartTarget`: `FromWeather = Target`, `TransitionElapsed = 0.0`), `:450-457`(`GetTransitionAlpha`), `:678-687`(`already %s`·`%s over %.1f s`·`%s (instant)`), `:84-88`(`TargetText` = `rain %.2f`), `:846-853`·`:855-879`(`mpc missing`·`fx missing`), `:914-944`(`status` 여러 줄, 끝 줄 `  mpc %s | fx %s | interior %s | frozen %s`), `:966-982`(결과는 `LogGolmok` Log 줄, 실패는 Warning). 세이브: `Save/GolmokSaveSubsystem.cpp:417-423`(`quit`의 pre-exit 동기 저장 — 슬롯에 날씨가 남아 다음 실행의 복원이 바뀔 수 있다), `:804-812`(날씨 변경은 dirty 표시만). 엔진(읽기, `/Users/Shared/Epic Games/UE_5.8/Engine/Source/`, 5.8.4): `Runtime/Launch/Private/Mac/LaunchMac.cpp:76-95`(공백이 든 argv 항목은 `이름="값"`으로 다시 이어 `Command Line:`에 찍힌다), `:111-114`(패키지 게임에 ` -installed`), `Runtime/Engine/Private/ParseExecCommands.cpp:11-55`(`-ExecCmds` 값을 쉼표로 나누고 앞 공백을 뗀다), `Runtime/Engine/Private/UnrealEngine.cpp:2552`(시작 때 `DeferredCommands`에 넣는다)·`:2772-2795`(`TickDeferredCommands`가 쌓인 명령을 **한 틱 안에서** 차례로 실행 — 그 사이 서브시스템 틱이 없다), `Runtime/Engine/Private/LocalPlayer.cpp:1594-1601`·`GameViewportClient.cpp:3514-3531`(명령은 결국 `GEngine->Exec`), `Runtime/Engine/Private/GameEngine.cpp:1530-1558`·`:1679-1686`(`quit` → `FPlatformMisc::RequestExit(false, TEXT("UGameEngine::HandleExitCommand"))`), `Runtime/Core/Private/Mac/MacPlatformMisc.cpp:712-714`(`FPlatformMisc::RequestExit(%i, %ls)` 로그 줄), `Runtime/Core/Private/Misc/Paths.cpp:573-594`·`Runtime/Core/Private/Mac/MacPlatformProcess.cpp:1223-1235`(Mac 게임 로그 폴더 = 사용자 `Library` + `/Logs/` + 앱 하위 폴더 — 샌드박스 앱이면 컨테이너 `Data/Library/Logs/Golmok/`), `Runtime/Core/Private/Misc/OutputDeviceHelper.cpp:108-139`(여러 줄 메시지는 그대로 쓰여 `status`의 둘째 줄부터는 접두 없이 한 줄씩), `Developer/PakFileUtilities/Private/PakFileUtilities.cpp:5677-5679`(`-ListContainer=` → `ListIoStoreContainer`), `Developer/IoStoreUtilities/Private/IoStoreUtilities.cpp:6352-6370`(`-ListContainer=`·`-csv=` 필수), `:6280-6345`(`ListContainer` — CSV 파일 하나), `:951`(CSV 머리 줄), `:999-1010`(행 = 순번, ChunkId, PackageId, PackageName, Filename, …), `Runtime/Core/Private/Serialization/Archive.cpp:1489-1501`(ANSI + 줄 끝). 2026-11-28 Opus가 읽은 기계 상태: `$W`의 `build/Mac/Golmok.app`과 `Saved/StagedBuilds/Mac/Manifest_UFSFiles_Mac.txt`(둘 다 `Nov 28 06:26`, J-15가 만든 것 — 패키징 커밋은 기록되지 않았다, §8 #10), 그 매니페스트에 `Golmok/Config/Golmok/weather.json` 1줄·`Golmok/Weather/` 0줄·`Golmok/Content/Golmok/Maps/L_Dev.umap` 1줄, `$W/unreal/Golmok/Content/Golmok/`에 `Weather` 폴더 없음(Audio·Maps·Materials·Zones), `Content/GASP` 없음, 엔진 `Engine/Binaries/Mac/UnrealPak` 실행 비트 있음. J-15 실행이 남긴 컨테이너 로그 `~/Library/Containers/com.YourCompany.Golmok/Data/Library/Logs/Golmok/Golmok.log`(`Nov 28 07:06`)에 `LogGolmok: Warning: weather: MPC missing (…) - wetness / puddles stay in the subsystem only`·`LogGolmok: Warning: weather: rain fx missing (…) - rain is lighting/MPC/audio only`·`LogGolmok: weather: clear fixed, transition 20.0 s, 10 schedule slots, mpc missing, fx missing` 각 1줄, `Command Line:` 줄 끝에 ` -installed`, 줄 끝 `\r` 0개. 컨테이너 `Saved/` 아래에는 `Logs`가 없다(Config·Profiling·SaveGames만).
- **이력**: 이 절은 2026-11-28 영록의 "보충(배정 전, 일부만)"을 대신한다. 그 보충의 매니페스트·utoc 경로(J-15 실측, mac-setup §8 #10)와 GUI 잠금(목적 `J-22-pkg`)은 아래 설계 1 ②와 명령 공통에 들어갔고, 남은 두 미정(앱 로그 위치, 명령마다의 기대 출력)은 설계 1 ⑧·4로 정했다(Opus 2026-11-28, 재환 레인 문서 7).
- **설계 (확정, Opus 2026-11-28)**: 재환은 아래를 그대로 옮긴다. 바꿀 점이 보이면 고치지 말고 묻는다.
  1. **명령 대응(§11의 Windows 줄 → Mac)**: ① `.\tools\ue\package.ps1` → `./tools/ue/package.sh Development --out-dir "$W/build/Mac"`(상시 규칙 "패키지 출력"). ② `$pkg = …` 줄 → 없음: Mac은 위치가 고정이다(§8 #10) — 매니페스트 `"$W/unreal/Golmok/Saved/StagedBuilds/Mac/Manifest_UFSFiles_Mac.txt"`, utoc `"$W/build/Mac/Golmok.app/Contents/UE/Golmok/Content/Paks/Golmok-Mac.utoc"`. ③ `Select-String … -Pattern 'Config/Golmok/weather.json'` → `grep -c -F 'Config/Golmok/weather.json' <매니페스트>`. ④ `$pak = '…\UnrealPak.exe'` → `"/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealPak"`. ⑤ `& $pak "-ListContainer=…utoc" "-csv=$env:TEMP\utoc.csv"` → `"…/UnrealPak" "-ListContainer=<utoc>" "-csv=$E/utoc.csv"`. ⑥ `Select-String utoc.csv -Pattern 'Golmok/Weather/(MPC_GolmokWeather|NS_GolmokRain)'` → `grep -c -E` 같은 패턴. ⑦ 실행 `& "$pkg\Golmok.exe" -windowed -forcelogflush` → `"$W/build/Mac/Golmok.app/Contents/MacOS/Golmok" -RenderOffScreen -ResX=1920 -ResY=1080 -forcelogflush -log "-ExecCmds=…"`(J-15처럼 실행 파일을 직접 띄우고 `-RenderOffScreen -ResX=1920 -ResY=1080`을 주는 꼴에서 J-15의 맵 인자·`-game`·`-csvCaptureFrames`를 뺀 것 — 설계 3. 정정 2026-11-28 문서 7: 처음 적은 "J-15가 쓴 실행 꼴"은 그 차이를 적지 않았다. 창이 없어 소유자 화면을 가리지 않는다. `-log`는 Windows에서 포커스 문제로 뺐지만 Mac J-15 실행에서는 문제가 관찰되지 않았다). ⑧ 로그 `$pkg\Golmok\Saved\Logs\Golmok.log` → `~/Library/Containers/com.YourCompany.Golmok/Data/Library/Logs/Golmok/Golmok.log`(엔진 `Paths.cpp:573-594`·`MacPlatformProcess.cpp:1223-1235`, J-15의 파일이 그 자리에 있다. 컨테이너 `Saved/Logs`가 아니다). ⑨ `~` 콘솔 입력 → `-ExecCmds`(§11 끝 문장의 대안 그대로). "IoStore가 아니면 `.pak -List`" 분기는 쓰지 않는다: Mac 패키지는 utoc가 있는 IoStore다(§8 #10). utoc가 없으면 멈춘다.
  2. **패키지는 새로 만든다(있는 J-15 패키지를 다시 쓰지 않는다)**: ① 기록 줄은 SHA로 시작해야 하는데(J-20 관례), J-15 패키지는 어느 커밋에서 만들었는지 기록이 없다(§8 #10 "패키징한 커밋은 기록하지 않았다"). ② 그 뒤 `$W`는 J-18·J-35 브랜치를 오갔다. ③ 새 패키지가 이 과제 안에서 만든 것인지는 매니페스트·utoc의 mtime이 패키지 직전 표식보다 새것인지로 확인한다(펜스 `j22-check-sh`의 `manifest-new`·`utoc-new`). 이 과제가 `build/Mac`과 `Saved/StagedBuilds/Mac`을 덮어쓴다. J-19는 이 과제보다 먼저 하고 자기 패키지를 따로 새로 만든다(J-19 설계 1, 위 "다음" — 2026-11-28 문서 7). 이 과제도 J-19의 패키지를 다시 쓰지 않는다. `build/`를 지우지 않는다.
  3. **실행 명령 원문**: `-ExecCmds=golmok.weather clear instant,golmok.weather rain heavy,golmok.weather status,quit`(한 argv 항목). ① `clear instant`를 먼저 둔다: 이 앱은 시작 때 세이브 슬롯의 날씨를 복원하고(`GolmokSave: restore on begin play`), `quit`의 pre-exit 동기 저장이 그 슬롯을 다시 쓴다(`GolmokSaveSubsystem.cpp:417-423`). 슬롯에 비가 남아 있어도 `rain heavy`의 답이 늘 `weather: rain 1.00 over 20.0 s`이고 `status` 첫 줄이 `from clear`가 되게 한다. `clear instant`의 답 자체(`already clear`·`clear (instant)`·`clear (transition finished now)` 중 하나)는 판정하지 않고 세기만 한다. ② 네 명령은 한 틱 안에서 차례로 돈다(`UnrealEngine.cpp:2772-2795`) — 그래서 `status`는 전환 시작 직후 값 `alpha 0.00 (0.0 / 20.0 s)`을 찍는다. 날씨 서브시스템 틱이 사이에 끼지 않는다. ③ `quit`이 게임을 스스로 끝낸다(`GameEngine.cpp:1679-1686`) — `/usr/bin/timeout 300`은 안전망이고, 124는 멈춤이다(명령이 돌지 않았거나 끝나지 않았다는 뜻 — 패키지 `.app`에서 `-ExecCmds` 여러 명령이 도는지는 먼저 하는 J-19가 처음 본다(J-19 설계 4)). 맵 인자는 주지 않는다(Windows 명령과 같다, `GameDefaultMap` = `L_Dev`).
  4. **에셋 전 기대값(펜스로 고정)**: 매니페스트 `Config/Golmok/weather.json` **1**줄(`DefaultGame.ini:19`), `Golmok/Weather/` **0**줄(에셋 폴더가 없다), 대조 `Golmok/Maps/L_Dev` 있음. CSV 머리 줄은 `IoStoreUtilities.cpp:951` 그대로, `Golmok/Weather/(MPC_GolmokWeather|NS_GolmokRain)` **0**줄, 대조 `Golmok/Maps/L_Dev` 있음 — 대조가 없으면 "0줄"이 빈 검사라 멈춘다(CSV의 Filename 칸이 비는 패키지일 수 있다 [미확인] — 그때 영록이 `-AllChunksInfo` 등을 정한다). 로그: 시작 줄 `… mpc missing, fx missing` 1, Warning 2줄 각 1, Windows 기대 `mpc ok, fx idle` 0, `rain 1.00 over 20.0 s` 1, `status` 첫 줄·끝 줄 각 1(끝 줄 `  mpc missing | fx missing | interior no | frozen no` — Windows 기대 `mpc ok | fx on` 0), `no game world` 0, `RequestExit(0, UGameEngine::HandleExitCommand)` 1. 펜스 `j22-expected-check`·`j22-expected-logcheck`와 `diff`해 0이어야 한다. Windows 체크 4("빗줄기·HUD")는 이 과제가 보지 않는다(NS가 없고, 화면 판정은 재환 몫이 아니다).
  5. **결과 자리**: [pc-verify-wp16a.md](../runbooks/pc-verify-wp16a.md) §13 표 아래, J-20 줄(`Mac 부분 선행(J-20, `로 시작하는 줄) **바로 다음**에 빈 줄 하나와 한 줄을 더한다(J-20과 같은 +2 −0). 줄은 펜스 `j22-line-sh`가 날짜·SHA만 채워 만든다 — 다른 값은 모두 위 `diff`가 0일 때만 맞는 고정 문구라 재환이 손으로 쓰는 값이 없다. 커밋 1은 끝이 `근거: J-22 PR.`이고, PR 번호가 나온 뒤 커밋 2가 그 끝을 `근거: PR #<번호>.`로 바꾼다(J-20의 `근거: PR #153.` 꼴, 할 일 7). §11 본문·§13 표의 §11 칸·Windows 블록은 고치지 않는다(D-022: Mac은 추가만, 카드 §11은 에셋 뒤에 끝난다).
  6. **코드 변경 없음**: C++·Python·`tools/ue/*.sh`·`Config/`(핫스팟 `Default*.ini` 포함)·테스트는 열거나 고치지 않는다. 생성물(`build/`·`unreal/Golmok/Saved/`)은 `.gitignore:2-11`이고, 앱이 쓰는 컨테이너 파일(로그·`SaveGames/golmok_auto.sav`·`Config`)은 저장소 밖이라 지우지 않는다.
  7. **에셋 뒤는 범위 밖**: §2 MPC·NS 저작(GUI·J-25 설계 선행)과 그 뒤의 §11 기대(`mpc ok, fx idle`, 컨테이너의 두 에셋, `fx on`)는 이 과제가 하지 않는다. 같은 명령을 에셋 뒤에 다시 돌리면 되도록 명령은 바꾸지 않는다.
  8. **J-19와의 관계**: 패키지 게임 로그 위치와 `.app`의 `-ExecCmds` 여러 명령은 먼저 하는 J-19가 관찰한다(J-19 설계 3·4). J-19 결과가 이 절의 설계 1 ⑧·3과 다르면 영록이 배정 전에 이 절을 고친다. (정정 2026-11-28 문서 7: 처음 적은 "J-19 보충의 [미확인]은 이 과제의 관찰로 답이 나온다"는 J-19를 뒤에 하던 순서의 문장이다.)

```sh j22-check-sh
#!/bin/sh
# J-22: fixed checks on the new package before the weather assets exist (usage: sh j22_check.sh <W> <E>), one "label value" per line.
W=$1
E=$2
M="$W/unreal/Golmok/Saved/StagedBuilds/Mac/Manifest_UFSFiles_Mac.txt"
U="$W/build/Mac/Golmok.app/Contents/UE/Golmok/Content/Paks/Golmok-Mac.utoc"
H='OrderInContainer, ChunkId, PackageId, PackageName, Filename, ContainerName, Offset, OffsetOnDisk, Size, CompressedSize, Hash, ChunkType, ClassType, PakChunk, Platform, InstallType, DeliveryType, PartitionIndex, OffsetInPartition'
c() { printf '%s %s\n' "$1" "$2"; }
yn() { if "$@"; then echo yes; else echo no; fi; }
c package-output "$(grep -c -x -F "Package output: $W/build/Mac" "$E/package.log")"
c gasp-warning "$(grep -c -F 'WARNING: Content/GASP exists' "$E/package.log")"
c build-successful "$(yn grep -q -F 'BUILD SUCCESSFUL' "$E/package.log")"
c manifest-new "$(yn [ "$M" -nt "$E/pkg-marker" ])"
c utoc-new "$(yn [ "$U" -nt "$E/pkg-marker" ])"
c manifest-weather-json "$(grep -c -F 'Config/Golmok/weather.json' "$M")"
c manifest-weather-assets "$(grep -c -F 'Golmok/Weather/' "$M")"
c manifest-l_dev "$(yn grep -q -F 'Golmok/Maps/L_Dev' "$M")"
c csv-header "$(yn [ "$(head -n 1 "$E/utoc.csv" | tr -d '\r')" = "$H" ])"
c csv-weather-assets "$(grep -c -E 'Golmok/Weather/(MPC_GolmokWeather|NS_GolmokRain)' "$E/utoc.csv")"
c csv-l_dev "$(yn grep -q -F 'Golmok/Maps/L_Dev' "$E/utoc.csv")"
```

```sh j22-logcheck-sh
#!/bin/sh
# J-22: fixed line counts in the packaged-game log copy (usage: sh j22_logcheck.sh <log>), one "label count" per line.
G=$1
c() { printf '%s %s\n' "$1" "$2"; }
c cmdline-execcmds "$(grep -F 'Command Line: ' "$G" | grep -c -F -- '-ExecCmds="golmok.weather clear instant,golmok.weather rain heavy,golmok.weather status,quit"')"
c mpc-missing-warning "$(grep -c -F 'LogGolmok: Warning: weather: MPC missing (/Game/Golmok/Weather/MPC_GolmokWeather.MPC_GolmokWeather) - wetness / puddles stay in the subsystem only' "$G")"
c fx-missing-warning "$(grep -c -F 'LogGolmok: Warning: weather: rain fx missing (/Game/Golmok/Weather/NS_GolmokRain.NS_GolmokRain) - rain is lighting/MPC/audio only' "$G")"
c start-missing "$(grep -c -F 'LogGolmok: weather: clear fixed, transition 20.0 s, 10 schedule slots, mpc missing, fx missing' "$G")"
c start-ok "$(grep -c -F 'mpc ok, fx idle' "$G")"
c weather-off "$(grep -c -F 'weather: off -' "$G")"
c clear-first "$(grep -c -E 'LogGolmok: weather: (already clear|clear \(instant\)|clear \(transition finished now\))$' "$G")"
c rain-heavy "$(grep -c -E 'LogGolmok: weather: rain 1\.00 over 20\.0 s$' "$G")"
c status-head "$(grep -c -F 'LogGolmok: weather: target rain 1.00 | current from clear, alpha 0.00 (0.0 / 20.0 s)' "$G")"
c status-tail "$(grep -c -x -F '  mpc missing | fx missing | interior no | frozen no' "$G")"
c status-ok "$(grep -c -F 'mpc ok | fx ' "$G")"
c no-game-world "$(grep -c -F 'golmok.weather: no game world' "$G")"
c exit-request "$(grep -c -F 'FPlatformMisc::RequestExit(0, UGameEngine::HandleExitCommand)' "$G")"
```

```sh j22-line-sh
#!/bin/sh
# J-22: prints a blank line and the "Mac 부분 선행" line for pc-verify-wp16a section 13 (usage: sh j22_line.sh <E>).
E=$1
date=$(cat "$E/run-date.log")
sha=$(cat "$E/sha.log")
printf '\n'
printf 'Mac 부분 선행(J-22, 에셋 전, %s, SHA %s에서 새로 만든 Development 패키지): §11 — `package.sh` 종료 코드 0. 매니페스트 `unreal/Golmok/Saved/StagedBuilds/Mac/Manifest_UFSFiles_Mac.txt`에 `Config/Golmok/weather.json` 1줄, `UnrealPak -ListContainer`의 `Golmok-Mac.utoc` 목록에 `MPC_GolmokWeather`·`NS_GolmokRain` 0줄(`L_Dev`는 있다). `-ExecCmds`로 `golmok.weather clear instant`·`rain heavy`·`status`·`quit`을 준 실행의 게임 로그(컨테이너 `~/Library/Containers/com.YourCompany.Golmok/Data/Library/Logs/Golmok/`)에 `weather: clear fixed, transition 20.0 s, 10 schedule slots, mpc missing, fx missing`, `status` 끝 줄 `mpc missing | fx missing | interior no | frozen no`, 종료 코드 0. 에셋 뒤 기대(`mpc ok, fx idle`, 목록의 두 에셋)는 아직 확인하지 않았다. 근거: J-22 PR.\n' "$date" "$sha"
```

```text j22-expected-check
package-output 1
gasp-warning 0
build-successful yes
manifest-new yes
utoc-new yes
manifest-weather-json 1
manifest-weather-assets 0
manifest-l_dev yes
csv-header yes
csv-weather-assets 0
csv-l_dev yes
```

```text j22-expected-logcheck
cmdline-execcmds 1
mpc-missing-warning 1
fx-missing-warning 1
start-missing 1
start-ok 0
weather-off 0
clear-first 1
rain-heavy 1
status-head 1
status-tail 1
status-ok 0
no-game-world 0
exit-request 1
```

- **명령 공통**: 셸 변수는 Bash 호출 사이에 남지 않는다. 그래서 **모든 명령은 `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/jaehwan/J-22";`로 시작하고**, 그 뒤는 `cd "$W" &&`·`cd "$W/tools" &&`·`git -C "$W"`·`"$E/…"` 절대 경로로 시작한다(상시 규칙). 아래 명령에는 이 앞머리를 적지 않았다. 돌린 명령 원문은 `"$E/commands.txt"`에 한 줄씩 더한다(규칙 10). 각 단계의 "기대"와 다르면 **멈춤 조건**을 본다. 할 일 2(`package.sh`)·3(`UnrealPak`)·4(앱 실행)의 명령과 할 일 6·7의 게이트·`gh pr checks --watch`는 **항상** 하네스의 백그라운드 실행으로 돌리고, 그 명령이 쓰는 `.rc` 파일(`gh pr checks --watch`는 `checks-watch.log`의 `exit=` 줄)이 생길 때까지 기다린다(명령은 바꾸지 않는다). 그 밖의 명령은 앞쪽(foreground)으로 돌린다.
  - **GUI 잠금**(할 일 2~4, [mac-setup §3](../runbooks/mac-setup.md) 표의 규칙, 목적 `J-22-pkg`): 확인 `L="$TMPDIR/claude/gui-foreground.lock"; if [ -e "$L" ]; then cat "$L"; else echo "no lock"; fi > "$E/lock-check.log"; date -u +%FT%TZ >> "$E/lock-check.log"` — 기대 첫 줄 `no lock`. 다른 줄이 있으면 **지우지 않고** 그 줄을 영록에게 보내고 기다린다. 잡기 `mkdir -p "$TMPDIR/claude" && (set -C; printf '%s %s %s\n' "재환" "J-22-pkg" "$(date -u +%FT%TZ)" > "$TMPDIR/claude/gui-foreground.lock"); echo $? > "$E/lock-take.rc"` — 기대 `0`. 풀기 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-22-pkg ' "$L" && rm "$L"; echo $? > "$E/lock-release.rc"` — 기대 `0`.
  - **잠금 갱신**([AGENTS.md](../../AGENTS.md) "UE를 같이 쓰는 규칙"·mac-setup §3: 20분이 지난 기록은 빈 것으로 보므로 잡은 쪽이 쓰는 동안 갱신한다): ① 할 일 2·4의 UE 명령 바로 앞에 매번 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-22-pkg ' "$L" && printf '%s %s %s\n' "재환" "J-22-pkg" "$(date -u +%FT%TZ)" > "$L"; echo $? > "$E/lock-refresh-<n>.rc"` — `<n>`은 할 일 2면 `package`, 4면 `app`. 기대 `0`. 0이 아니면(잠금 줄이 `재환 J-22-pkg`가 아니다) 잠금 파일을 지우거나 쓰지 않고 멈춘다. ② 할 일 2·4의 UE 명령은 갱신 루프로 감싸 **적힌 그대로** 돌린다(이미 들어 있다): 앞에 `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-22-pkg ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-22-pkg" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!;`, 끝에 `; kill "$RP"`. 할 일 3(`UnrealPak`, 300 s 이내)은 잠금을 쥔 채 루프 없이 돈다.
- **할 일**:
  1. **준비**: `mkdir -p "$E" && git -C "$W" status --porcelain > "$E/status-before.log"; grep -c -v '^?? ' "$E/status-before.log" > "$E/status-before-tracked.log"` — 기대 `0`(추적 파일 변경이 있으면 멈춘다 — J-35 같은 앞 과제의 작업물일 수 있다; `??` 줄은 그대로 둔다). `git -C "$W" fetch origin && git -C "$W" switch -c local/jaehwan-j22-v16-pkg origin/main > "$E/switch.log" 2>&1; echo $? > "$E/switch.rc"` — 기대 `0`. `git -C "$W" rev-parse --short HEAD > "$E/sha.log"; git -C "$W" rev-parse HEAD origin/main | uniq | wc -l | tr -d ' ' > "$E/sha-same.log"` — 기대 `1`. `git -C "$W" show origin/main:docs/plan/jaehwan-tasks.md > "$E/tasks-main.md"; git -C "$W" rev-parse origin/main > "$E/main-rev.log"; { awk '/^#### J-22 /{f=1} /^#### J-23/{f=0} f' "$E/tasks-main.md"; awk '/^### PR 본문 공통\(모든 과제\)$/{f=1} /^## 리뷰·병합 절차$/{f=0} f' "$E/tasks-main.md"; } > "$E/task.txt"`(규칙 14·17 c, 상시 규칙 "PR 본문 공통" 1) — 기대 `head -1 "$E/task.txt"`가 `#### J-22 `로 시작, `grep -c -x '### PR 본문 공통(모든 과제)' "$E/task.txt"` `1`. 펜스 추출(손으로 옮기지 않는다): `` printf '%s\n' "j22-check-sh j22_check.sh" "j22-logcheck-sh j22_logcheck.sh" "j22-line-sh j22_line.sh" "common-ph-awk ph.awk" "j22-expected-check expected-check.txt" "j22-expected-logcheck expected-logcheck.txt" | while read -r n f; do awk -v n="$n" '$0 == "```" && x {x=0} x {print} $0 ~ ("^```[a-z]+ " n "$") {x=1}' "$E/task.txt" > "$E/$f"; done; cd "$E" && wc -l j22_check.sh j22_logcheck.sh j22_line.sh ph.awk expected-check.txt expected-logcheck.txt > "$E/extract-wc.log" `` — 기대(앞 숫자, 순서대로): `20`, `17`, `7`, `37`, `11`, `13`, 끝 줄 `105 total`. 겹침: `cd "$W" && gh pr list --state open --json number,headRefName,files --jq '.[]|select(any(.files[]; .path=="docs/runbooks/pc-verify-wp16a.md"))|"\(.number) \(.headRefName)"' > "$E/overlap.log" 2>&1` — 기대 빈 파일. 같은 프로젝트의 편집기·쿡·패키지 앱이 없어야 한다: `pgrep -fl '[g]olmok-jaehwan/(unreal/Golmok/Golmok\.uproject|build/Mac/Golmok\.app/)' > "$E/ue-before.log"; echo $? > "$E/ue-before.rc"` — 기대 rc `1`(빈 파일). 전제: `{ test -e "$W/unreal/Golmok/Content/Golmok/Weather"; echo "weather-dir=$?"; test -f "$W/unreal/Golmok/Content/Golmok/Maps/L_Dev.umap"; echo "l_dev=$?"; test -e "$W/unreal/Golmok/Content/GASP"; echo "gasp=$?"; cd "$W" && grep -c '^Mac 부분 선행(J-20, ' docs/runbooks/pc-verify-wp16a.md; grep -c '^Mac 부분 선행(J-22, ' docs/runbooks/pc-verify-wp16a.md; } > "$E/pre.log"` — 기대 다섯 줄 `weather-dir=1`·`l_dev=0`·`gasp=1`·`1`·`0`(에셋 폴더가 이미 있으면 "에셋 전"이 아니다, `L_Dev`가 없으면 `test.sh --setup-dev-level`이 필요하다 — 둘 다 스스로 하지 않고 멈춘다).
  2. **패키지**: GUI 잠금 확인·잡기. 잠금 갱신 ①(`package`). 패키지(하네스 백그라운드): `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-22-pkg ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-22-pkg" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && touch "$E/pkg-marker" && sleep 1 && /usr/bin/timeout 5400 ./tools/ue/package.sh Development --out-dir "$W/build/Mac" > "$E/package.log" 2>&1; echo $? > "$E/package.rc"; kill "$RP"` — 기대 `package.rc` `0`(`sleep 1`은 표식과 산출물의 mtime이 같은 초에 겹치지 않게 한다).
  3. **매니페스트·컨테이너**: `UnrealPak`(하네스 백그라운드): `/usr/bin/timeout 300 "/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealPak" "-ListContainer=$W/build/Mac/Golmok.app/Contents/UE/Golmok/Content/Paks/Golmok-Mac.utoc" "-csv=$E/utoc.csv" > "$E/upak.log" 2>&1; echo $? > "$E/upak.rc"` — 기대 `0`. 판정: `sh "$E/j22_check.sh" "$W" "$E" > "$E/check.log"; diff "$E/expected-check.txt" "$E/check.log" > "$E/check.diff"; echo "exit=$?" >> "$E/check.diff"` — 기대 `exit=0` 한 줄. 기록만(판정하지 않는다): `grep -F 'Config/Golmok/weather.json' "$W/unreal/Golmok/Saved/StagedBuilds/Mac/Manifest_UFSFiles_Mac.txt" > "$E/manifest-weather.log"; grep -c . "$E/utoc.csv" > "$E/csv-lines.log"; grep -m 3 -F 'Golmok/Maps/L_Dev' "$E/utoc.csv" > "$E/csv-l_dev.log"`.
  4. **패키지 실행**: 방화벽(읽기만, J-19 설계 6과 같다): `/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate > "$E/firewall.log" 2>&1; grep -c -x -F 'Firewall is disabled. (State = 0)' "$E/firewall.log" > "$E/firewall-ok.log"` — 기대 `1`. 다르면 앱을 띄우지 않고 멈춘다(아래 "멈춤 순서"대로, 방화벽 설정은 소유자 몫 — 켜진 방화벽에서는 TraceLog 1985가 창을 띄울 수 있다, mac-setup §8 #11). 잠금 갱신 ①(`app`). 실행(하네스 백그라운드): `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-22-pkg ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-22-pkg" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && touch "$E/app-marker" && sleep 1 && date +%F > "$E/run-date.log" && /usr/bin/timeout 300 "$W/build/Mac/Golmok.app/Contents/MacOS/Golmok" -RenderOffScreen -ResX=1920 -ResY=1080 -forcelogflush -log "-ExecCmds=golmok.weather clear instant,golmok.weather rain heavy,golmok.weather status,quit" > "$E/app-stdout.log" 2>&1; echo $? > "$E/app.rc"; kill "$RP"`(`run-date.log`는 기록 줄의 날짜 — Mac의 현지 날짜) — 기대 `app.rc` `0`(124 = 시간 초과 — 멈춤). 로그 사본(곧바로, 다음 실행이 `Golmok-backup-<시각>.log`로 돌린다): `CL="$HOME/Library/Containers/com.YourCompany.Golmok/Data/Library/Logs/Golmok/Golmok.log"; [ "$CL" -nt "$E/app-marker" ]; echo "newer=$?" > "$E/app-log-new.log"; cp "$CL" "$E/app.log"; echo $? > "$E/app-cp.rc"` — 기대 `newer=0`, `0`. 판정: `sh "$E/j22_logcheck.sh" "$E/app.log" > "$E/logcheck.log"; diff "$E/expected-logcheck.txt" "$E/logcheck.log" > "$E/logcheck.diff"; echo "exit=$?" >> "$E/logcheck.diff"` — 기대 `exit=0` 한 줄. 기록만: `grep -E 'Command Line: |LogGolmok: (Warning: )?weather: |^  (modifier|rain now|mode|mpc) |GolmokSave: restore on begin play|RequestExit' "$E/app.log" > "$E/app-weather.log"`. 남은 프로세스: `pgrep -fl '[g]olmok-jaehwan/(unreal/Golmok/Golmok\.uproject|build/Mac/Golmok\.app/)' > "$E/ue-after.log"; echo $? > "$E/ue-after.rc"` — 기대 rc `1`. 잠금 풀기.
  5. **런북 한 줄**: `sh "$E/j22_line.sh" "$E" > "$E/line22.txt"; echo $? > "$E/line.rc"` — 기대 rc `0`, `wc -l < "$E/line22.txt" | tr -d ' '` `2`, `head -n 1 "$E/line22.txt" | grep -c -x ''` `1`. 손으로 옮기지 않고 명령으로 J-20 줄 바로 다음에 넣는다: `cd "$W" && sed -i '' "/^Mac 부분 선행(J-20, /r $E/line22.txt" docs/runbooks/pc-verify-wp16a.md; echo $? > "$E/line-insert.rc"` — 기대 `0`. 이 명령은 한 번만 돌린다(두 번 돌리면 아래 `grep -c`가 `2`가 된다 — 멈춤). 확인: `cd "$W" && awk '/^Mac 부분 선행\(J-20, /{getline a; getline b; print a; print b}' docs/runbooks/pc-verify-wp16a.md | diff - "$E/line22.txt" > "$E/line-diff.log"; echo "exit=$?" >> "$E/line-diff.log"` — 기대 `exit=0` 한 줄. `cd "$W" && grep -c '^Mac 부분 선행(J-22, ' docs/runbooks/pc-verify-wp16a.md` `1`. 칸 자기 검사(규칙 17 b): `cd "$W" && git diff -U0 origin/main -- docs/runbooks/pc-verify-wp16a.md | grep '^+[^+]' > "$E/cell-lines-1.txt"; wc -l < "$E/cell-lines-1.txt" | tr -d ' ' > "$E/cell-lines-1-count.log"; grep -n -E '\.log|영록|R[0-9]{3}' "$E/cell-lines-1.txt" > "$E/cell-grep-1.log"; wc -l < "$E/cell-grep-1.log" | tr -d ' ' > "$E/cell-grep-1-count.log"` — 기대 `cell-lines-1-count.log` `1`, `cell-grep-1-count.log` `0`(상시 규칙 "PR 본문 공통" 7 — 0이 아니면 줄을 손으로 고치지 않고 멈춘다). `cd "$W" && git diff --numstat -- docs/runbooks/pc-verify-wp16a.md` `2	0	docs/runbooks/pc-verify-wp16a.md`. `git -C "$W" status --porcelain > "$E/status-after.log"; grep -v -x -F ' M docs/runbooks/pc-verify-wp16a.md' "$E/status-after.log" | diff "$E/status-before.log" - > "$E/status.diff"; echo "exit=$?" >> "$E/status.diff"` — 기대 `exit=0` 한 줄(패키지·실행이 저장소에 남긴 것이 없다).
  6. **게이트·커밋 1·push·PR**: `cd "$W/tools" && source .venv/bin/activate && { /usr/bin/timeout 300 ruff check . && /usr/bin/timeout 300 ruff format --check . && /usr/bin/timeout 1800 pytest -q && /usr/bin/timeout 300 python scripts/check_repo.py; } > "$E/gate-1.log" 2>&1; echo $? > "$E/gate-1.rc"`(하네스 백그라운드) — 기대 `0`(rc 124 = 시간 초과, 다시 돌리지 않고 멈춤). `[ "$E/gate-1.log" -nt "$W/docs/runbooks/pc-verify-wp16a.md" ]; echo "newer=$?" > "$E/mtime-1.log"` — 기대 `newer=0`. 커밋: `cd "$W" && git add docs/runbooks/pc-verify-wp16a.md && git diff --cached --name-only > "$E/c1-files.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-22: pc-verify-wp16a §13 Mac 부분 선행 — §11 패키지 명령(에셋 전)" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c1-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-1.log"` — 기대 `c1-files.log` 한 줄 `docs/runbooks/pc-verify-wp16a.md`, `author-1.log` `재환 <jaehwan.local@localhost>`. `git -C "$W" push -u origin local/jaehwan-j22-v16-pkg > "$E/push-1.log" 2>&1; echo "exit=$?" >> "$E/push-1.log"` — 기대 끝 줄 `exit=0`. PR 열기(첫 본문은 CI 자리 한 줄뿐 — 규칙 2): `printf '%s\n' '## 요약' '' 'V-16 §11 Mac 패키지 명령(에셋 전). 본문은 CI 뒤에 채운다.' '' '## CI' '' 'CI 진행 중 — 결과는 아래에 추가' > "$E/pr-body-initial.md"; cd "$W" && gh pr create --base main --head local/jaehwan-j22-v16-pkg --title "J-22: V-16 §11 Mac 패키지 명령 이식 — 에셋 전 기대 결과" --body-file "$E/pr-body-initial.md" > "$E/pr-create.log" 2>&1; echo $? > "$E/pr-create.rc"` — 기대 `0`. PR 번호: `cd "$W" && gh pr view local/jaehwan-j22-v16-pkg --json number --jq .number > "$E/pr-number.log" 2> "$E/pr-number.err"` — 기대 `grep -c -x '[0-9][0-9]*' "$E/pr-number.log"` `1`, `wc -l < "$E/pr-number.log" | tr -d ' '` `1`(`pr-number.err`는 판정하지 않는다).
  7. **커밋 2(PR 번호)·push·CI**: `N=$(cat "$E/pr-number.log"); sed "s/ 근거: J-22 PR\.\$/ 근거: PR #$N./" "$E/line22.txt" > "$E/line22-final.txt"; cd "$W" && sed -i '' "s/ 근거: J-22 PR\.\$/ 근거: PR #$N./" docs/runbooks/pc-verify-wp16a.md; echo $? > "$E/line-pr.rc"` — 기대 `0`. 확인: `cd "$W" && awk '/^Mac 부분 선행\(J-20, /{getline a; getline b; print a; print b}' docs/runbooks/pc-verify-wp16a.md | diff - "$E/line22-final.txt" > "$E/line-final-diff.log"; echo "exit=$?" >> "$E/line-final-diff.log"` — 기대 `exit=0` 한 줄. `cd "$W" && grep -c ' 근거: J-22 PR\.$' docs/runbooks/pc-verify-wp16a.md` `0`. 칸 자기 검사: `cd "$W" && git diff -U0 origin/main -- docs/runbooks/pc-verify-wp16a.md | grep '^+[^+]' > "$E/cell-lines-2.txt"; wc -l < "$E/cell-lines-2.txt" | tr -d ' ' > "$E/cell-lines-2-count.log"; grep -n -E '\.log|영록|R[0-9]{3}' "$E/cell-lines-2.txt" > "$E/cell-grep-2.log"; wc -l < "$E/cell-grep-2.log" | tr -d ' ' > "$E/cell-grep-2-count.log"` — 기대 `cell-lines-2-count.log` `1`, `cell-grep-2-count.log` `0`(상시 규칙 "PR 본문 공통" 7 — 0이 아니면 줄을 손으로 고치지 않고 멈춘다). `cd "$W" && git diff --numstat origin/main -- docs/runbooks/pc-verify-wp16a.md` `2	0	docs/runbooks/pc-verify-wp16a.md`. 게이트 다시(규칙 13, 하네스 백그라운드): 할 일 6의 게이트 명령에서 `gate-1`을 `gate-2`로 바꾼 것 — 기대 `gate-2.rc` `0`, `[ "$E/gate-2.log" -nt "$W/docs/runbooks/pc-verify-wp16a.md" ]; echo "newer=$?" > "$E/mtime-2.log"` `newer=0`. 커밋: `cd "$W" && git add docs/runbooks/pc-verify-wp16a.md && git diff --cached --name-only > "$E/c2-files.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-22: 기록 줄의 근거를 PR 번호로" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c2-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-2.log"` — 기대 `c2-files.log` 한 줄 `docs/runbooks/pc-verify-wp16a.md`, `author-2.log` `재환 <jaehwan.local@localhost>`. `git -C "$W" push > "$E/push-2.log" 2>&1; echo "exit=$?" >> "$E/push-2.log"` — 기대 끝 줄 `exit=0`. 브랜치 파일: `git -C "$W" diff --name-only origin/main...HEAD > "$E/branch-files.log"` — 기대 한 줄 `docs/runbooks/pc-verify-wp16a.md`. push 뒤 상태: `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-final.diff"; echo "exit=$?" >> "$E/status-final.diff"` — 기대 `exit=0` 한 줄. CI(하네스 백그라운드): `cd "$W" && /usr/bin/timeout 1800 gh pr checks "$(cat "$E/pr-number.log")" --watch --interval 30 > "$E/checks-watch.log" 2>&1; echo "exit=$?" >> "$E/checks-watch.log"; gh pr checks "$(cat "$E/pr-number.log")" > "$E/checks.log" 2>&1` — 기대 모든 행 pass.
  8. **PR 본문**: PR 본문·자리표시 분류·칸 자기 검사·근거 표기는 상시 규칙 "PR 본문 공통(모든 과제)"을 따른다(이 절과 다르면 그 소절을 따른다). `## 결과`에는 관찰한 값만 둔다: `package.rc`, `check.log` 열한 줄, `manifest-weather.log` 원문, `csv-l_dev.log` 첫 줄, `firewall.log` 한 줄, `app.rc`, `logcheck.log` 열세 줄, `app-weather.log`의 `rain 1.00 over`·`status` 다섯 줄·`RequestExit` 줄 원문(로그 원문은 백틱 펜스 블록에) — 과제 번호·규칙 번호·날짜는 이 절에 쓰지 않는다. `## 완료 기준 대조`는 아래 (a)~(i) 한 줄씩(과제 글에 백틱 펜스가 들어 있어 물결 펜스 `~~~`를 쓴다). 본문 초안은 `$E/pr-body.md`. 게시 전 검사(규칙 10 e·f) — **대상 로그는 이 목록으로 고정한다**(본문 초안·게시본·`task.txt`·`commands.txt`·검사 로그 자신은 넣지 않는다): `"$E"/package.log "$E"/upak.log "$E"/check.log "$E"/manifest-weather.log "$E"/csv-l_dev.log "$E"/csv-lines.log "$E"/firewall.log "$E"/app.log "$E"/app-weather.log "$E"/logcheck.log "$E"/line22-final.txt "$E"/sha.log "$E"/run-date.log "$E"/gate-2.log "$E"/checks.log`.
     - 인용 검사: `## 결과` 절의 백틱 문자열마다 그 문자열이 근거로 든 로그 **한 개**를 `"$E/quotes.tsv"`에 `<문자열><탭><위 목록의 파일 이름>`으로 적는다(로그 인용이 아닌 파일 이름·명령은 파일 칸에 `라벨`). 빠진 것 확인: `` awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '`[^`]+`' | sed 's/^`//;s/`$//' | sort -u > "$E/body-quotes.txt"; cut -f1 "$E/quotes.tsv" | sort -u > "$E/tsv-quotes.txt"; comm -23 "$E/body-quotes.txt" "$E/tsv-quotes.txt" > "$E/quotes-missing.log" `` — 기대 빈 파일. 세기: `while IFS="$(printf '\t')" read -r q f; do if [ "$f" = "라벨" ]; then n="라벨"; else n=$(grep -F -c -- "$q" "$E/$f"); fi; printf '%s\t%s\t%s\n' "$n" "$f" "$q"; done < "$E/quotes.tsv" > "$E/quotes-check.log"` — 기대: `cut -f1 "$E/quotes-check.log" | grep -c -x '0'`가 `0`.
     - 숫자 검사: `awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '[0-9]{2,}' | sort -u > "$E/body-numbers.txt"; while read -r x; do printf '%s\t%s\n' "$(cat "$E"/package.log "$E"/upak.log "$E"/check.log "$E"/manifest-weather.log "$E"/csv-l_dev.log "$E"/csv-lines.log "$E"/firewall.log "$E"/app.log "$E"/app-weather.log "$E"/logcheck.log "$E"/line22-final.txt "$E"/sha.log "$E"/run-date.log "$E"/gate-2.log "$E"/checks.log | grep -c -- "$x")" "$x"; done < "$E/body-numbers.txt" > "$E/numbers-check.log"` — 기대: `cut -f1 "$E/numbers-check.log" | grep -c -x '0'`가 `0`. 한 자리 숫자는 이 검사에 걸리지 않으므로 문맥 문자열(예: `manifest-weather-json 1`)로 인용 검사에 넣는다.
     - 0이 나온 것은 고치거나 지운다. 그다음 상시 규칙 "PR 본문 공통" 3(점검표 대조)·5(자리표시 분류)·6(조립·게시·다시 읽기)을 적힌 그대로 돌린다.
- **허용 파일**: `docs/runbooks/pc-verify-wp16a.md`(§13 표 아래 J-20 줄 다음에 빈 줄 하나와 펜스 `j22-line-sh`의 줄 하나만 — 할 일 5의 `sed`로 넣고 할 일 7의 `sed`로 끝만 바꾼다). 그 밖의 저장소 파일은 고치지 않는다: §11 본문·Windows 블록·§13 표의 칸·J-20 줄, mac-setup(§3·§6·§8), C++·Python·테스트·`tools/ue/*.sh`·`Config/`(핫스팟 `Default*.ini` 포함)·공유 문서·이 과제 파일. 생성물(`build/`·`Saved/`)과 J-18의 `??` 파일은 커밋하지 않는다.
- **멈춤 조건(정하지 말고 영록에게 묻는다)**: `status-before-tracked.log`가 0이 아닐 때. `switch.rc`가 0이 아니거나 `sha-same.log`가 1이 아닐 때. `head -1 "$E/task.txt"`가 `#### J-22 `로 시작하지 않을 때. `extract-wc.log`가 기대와 다를 때. `overlap.log`가 비어 있지 않을 때. `ue-before.rc`가 1이 아닐 때(같은 프로젝트의 편집기·쿡·패키지 앱이 떠 있다 — 끄지 않는다). `pre.log`가 기대 다섯 줄과 다를 때(에셋 폴더가 있다, `L_Dev`가 없다, `Content/GASP`가 있다, J-20 줄이 1개가 아니다, J-22 줄이 이미 있다 — 어느 것도 스스로 고치지 않는다). 잠금 파일에 다른 기록이 있거나 잠금 잡기 rc가 0이 아닐 때. `lock-refresh-package.rc`·`lock-refresh-app.rc` 중 하나가 0이 아닐 때(잠금 파일을 지우거나 쓰지 않는다). `package.rc`가 0이 아닐 때(124 = 시간 초과, 규칙 5 — 쿡 오류를 고치지 않고 `package.log`의 오류 줄을 보낸다). `upak.rc`가 0이 아닐 때. `firewall-ok.log`가 `1`이 아닐 때(앱을 띄우지 않는다 — 방화벽을 바꾸지 않는다). `check.diff`·`logcheck.diff`·`line-diff.log`·`line-final-diff.log`·`status.diff`·`status-final.diff`가 `exit=0` 한 줄이 아닐 때 — 특히 `csv-l_dev no`(목록의 Filename 칸이 비어 "0줄"이 빈 검사다)·`manifest-new no`·`utoc-new no`(새 패키지가 아니다)·`cmdline-execcmds 0`(로그가 이 실행의 것이 아니다)·`rain-heavy 0`(`-ExecCmds`가 돌지 않았다)·`exit-request 0`. `app.rc`가 0이 아닐 때(124 = `quit`이 듣지 않았거나 명령이 돌지 않았다, 그 밖 = 비정상 종료 — 다시 돌리지 않는다: 두 번째 실행은 첫 실행의 세이브를 복원하고 로그를 돌린다), `app-log-new.log`가 `newer=0`이 아니거나 `app-cp.rc`가 0이 아닐 때. `ue-after.rc`가 1이 아닐 때(아래 "멈춤 순서"). 넓은 명령에서 macOS 권한 창·방화벽 창이 뜰 때(누르지 않는다 — 소유자 항목). `line.rc`·`line-insert.rc`·`line-pr.rc`가 0이 아니거나 `line22.txt` 확인값이 기대와 다를 때. `cell-lines-1-count.log`·`cell-lines-2-count.log`가 `1`이 아니거나 `cell-grep-1-count.log`·`cell-grep-2-count.log`가 `0`이 아닐 때(줄을 손으로 고치지 않는다). `gate-1.rc`·`gate-2.rc`가 0이 아닐 때(rc 124 포함, 다른 파일을 고치거나 `ruff format`으로 바꾸지 않는다). `mtime-1.log`·`mtime-2.log`가 `newer=0`이 아닐 때. `c1-files.log`·`c2-files.log`·`author-1.log`·`author-2.log`가 기대와 다를 때. `lock-release.rc`가 0이 아닐 때(잠금 파일을 지우지 않는다). `push-1.log`·`push-2.log`가 `exit=0`으로 끝나지 않을 때, `branch-files.log`가 `docs/runbooks/pc-verify-wp16a.md` 한 줄이 아닐 때. `pr-create.rc`·`pr-edit.rc`가 0이 아니거나 `pr-number.log`가 숫자 한 줄이 아닐 때. `checks.log`에 pass가 아닌 행이 있을 때. 상시 규칙 "PR 본문 공통" 9의 공통 멈춤 조건. 그 밖에 이 절의 "기대"와 다른 값이 하나라도 나올 때. **코드·설정·쿡 결함으로 보이는 것을 고치지 않는다**(Claude 레인 — 재현 절차만 보고). **멈춤 순서 — 할 일 2~4 안에서 멈출 때는 이 순서로 한다**: ① `pgrep -fl '[g]olmok-jaehwan/(unreal/Golmok/Golmok\.uproject|build/Mac/Golmok\.app/)' > "$E/ue-stop.log"; echo $? > "$E/ue-stop.rc"`. ② rc가 `1`이면 잠금 풀기를 돌려 `lock-release.rc`를 남기고 묻는다. rc가 `0`이면(쿡·UAT·앱이 남았다) 프로세스를 건드리지 않고 잠금도 풀지 않은 채 `ue-stop.log`를 영록에게 보낸다.
- **완료 기준**:
  - (a) 준비: `status-before-tracked.log` `0`, `switch.rc` `0`, `sha-same.log` `1`, `task.txt` 첫 줄 `#### J-22 `, `extract-wc.log` 원문(기대 숫자와 같다), `overlap.log` 빈 파일, `ue-before.rc` `1`, `pre.log` 다섯 줄 `weather-dir=1`·`l_dev=0`·`gasp=1`·`1`·`0`.
  - (b) 패키지: `lock-take.rc` `0`, `lock-refresh-package.rc` `0`, `package.rc` `0`.
  - (c) 매니페스트·컨테이너: `upak.rc` `0`, `check.diff` `exit=0`(`check.log` 열한 줄 원문 — `manifest-weather-json 1`·`manifest-weather-assets 0`·`csv-weather-assets 0`·`csv-l_dev yes` 포함), `manifest-weather.log`·`csv-l_dev.log`·`csv-lines.log` 원문(기록).
  - (d) 패키지 실행: `firewall-ok.log` `1`(`firewall.log` 원문 `Firewall is disabled. (State = 0)`), `lock-refresh-app.rc` `0`, `app.rc` `0`, `app-log-new.log` `newer=0`, `app-cp.rc` `0`, `logcheck.diff` `exit=0`(`logcheck.log` 열세 줄 원문), `app-weather.log` 원문, `ue-after.rc` `1`, `lock-release.rc` `0`.
  - (e) 런북 줄: `line.rc` `0`, `line22.txt` 2줄(첫 줄 빈 줄), `line-insert.rc` `0`, `line-diff.log` `exit=0`, `grep -c '^Mac 부분 선행(J-22, '` `1`, numstat `2	0	docs/runbooks/pc-verify-wp16a.md`, `status.diff` `exit=0`, `cell-lines-1-count.log` `1`, `cell-grep-1-count.log` `0`.
  - (f) 커밋 1·PR: `gate-1.rc` `0`, `mtime-1.log` `newer=0`, `c1-files.log`·`author-1.log` 기대대로, `push-1.log` 끝 줄 `exit=0`, `pr-create.rc` `0`, `pr-number.log` 숫자 한 줄.
  - (g) 커밋 2: `line-pr.rc` `0`, `line-final-diff.log` `exit=0`, `근거: J-22 PR.` 0줄, `origin/main` 대비 numstat `2	0	docs/runbooks/pc-verify-wp16a.md`, `cell-lines-2-count.log` `1`, `cell-grep-2-count.log` `0`, `gate-2.rc` `0`, `mtime-2.log` `newer=0`, `c2-files.log`·`author-2.log` 기대대로, `push-2.log` 끝 줄 `exit=0`, `branch-files.log` 한 줄, `status-final.diff` `exit=0`.
  - (h) CI `checks.log` 모든 행 pass 원문(규칙 2).
  - (i) PR 본문: 절 순서(상시 규칙 "PR 본문 공통" 2), "완료 기준 대조" 절, 점검표(그날 규칙 수만큼, 소절 3). `quotes-missing.log` 빈 파일, `quotes-check.log`·`numbers-check.log`에 0 없음. 공통 완료 기준 (P)(소절 10): `checklist.diff` `exit=0`, `ph-unfilled.log` `0`, `pr-edit.rc` `0`, `ph-posted-unfilled.log` `0`, `ph-table.diff` `exit=0`, `signature-last.log` `1`.
- **병합 시 반영(영록)**: STATUS 재환 절에 J-22 행. pc-verify-wp16a §11 Windows 블록 아래에 "Mac 명령(추가, 2026-11-28 J-22에서 돈 그대로)" 블록 — 이 PR `## 실행한 명령`의 할 일 2~4 명령에서 `$E` 리다이렉트·잠금 줄을 뺀 꼴(영록 Opus가 쓴다, 에셋 뒤 같은 명령으로 다시 확인). mac-setup §6 V-16 행 끝에 날짜를 단 "§11 Mac 명령은 pc-verify-wp16a §11 Mac 블록, 에셋 전 기록은 §13 아래 J-22 줄" 메모, §3 `…\Binaries\Win64\Golmok.exe` 행과 패키지 Saved 행 아래 설명에 "패키지 게임 로그는 컨테이너 폴더 `~/Library/Containers/com.YourCompany.Golmok/Data/Library/Logs/Golmok/`(J-22)" 메모(규칙 16 — 있는 글은 지우지 않는다). J-19 절은 고치지 않는다(J-19가 먼저 끝나고 자기 패키지를 쓴다).
- **왜 재환 / 위험**: 모든 판정이 고정 기대값과의 `diff`·종료 코드로 끝나고, 검사·기록 줄이 펜스로 정해져 있다. 코드도 Astra 레인도 건드리지 않는다. 위험: ① 에셋 전 "0줄"을 통과로 읽거나 빈 검사로 만드는 것 — 매니페스트·목록 양쪽에 대조(`L_Dev` 있음)를 두었고, 기록 줄은 "에셋 뒤의 기대는 아직 확인하지 않았다"로 좁혔다(규칙 3·15). ② 옛 패키지·옛 로그를 새것으로 읽는 것 — mtime 표식(`manifest-new`·`utoc-new`·`app-log-new`)과 `Command Line:`의 이 실행 `-ExecCmds`로 막는다. ③ 세이브 복원이 날씨 답을 바꾸는 것 — `clear instant`를 먼저 둔다(설계 3). 두 번째 실행은 첫 실행의 세이브·로그 회전 때문에 같은 조건이 아니라 금지한다. ④ GPU·GUI 경합 — 쿡·앱 실행 동안 잠금을 쥔다. 수치는 재지 않는다. ⑤ 쿡·패키지 실패를 고치려는 것 — 멈추고 보고한다(쿡 경고·`DirectoriesToAlwaysCook`의 없는 `/Game/Golmok/Weather` 폴더 문구는 판정하지 않는다). ⑥ 메인 체크아웃에서 돌리는 것(2026-11-27 사고, 규칙 6) — 모든 명령이 `$W`·`$E` 절대 경로다.
- **dry-run 범위(Opus 2026-11-28)**: `origin/main` `8a4b3c7`의 scratch 사본(`git archive`, git 저장소로 만든 것)에 이 절을 넣고 한 것: 할 일 1의 과제 추출(첫 줄 `#### J-22 `)과 펜스 추출(zsh, `wc -l` 20·17·7·13·11·13, `81 total`), 추출한 스크립트가 이 절의 펜스와 바이트가 같음. `j22-check-sh`는 가짜 `$W`(J-15가 남긴 실제 `Manifest_UFSFiles_Mac.txt` 2520줄과 `Golmok-Mac.utoc`의 사본, 표식 뒤에 복사)와 합성 `package.log`(`Package output: …/build/Mac`·`BUILD SUCCESSFUL`)·합성 CSV(머리 줄은 `IoStoreUtilities.cpp:951` 그대로, `L_Dev.umap` 한 행)에서 펜스 `j22-expected-check`와 `diff` 0 — 실제 매니페스트는 `weather.json` 1줄·`Golmok/Weather/` 0줄·`L_Dev` 있음이었다. 같은 입력에 `Golmok/Weather/MPC_GolmokWeather.uasset` 행을 더하고 utoc mtime을 옛날로 바꾸면 `csv-weather-assets 1`·`utoc-new no`로 달라졌다(빈 검사 아님). `j22-logcheck-sh`는 실제 J-15 컨테이너 로그에서 Warning 2줄·시작 줄이 각 `1`, `mpc ok, fx idle`·`no game world` `0`이고 `-ExecCmds`를 주지 않은 실행(또 `-game`과 맵 인자를 준 실행이라 이 과제의 실행 꼴과도 다르다)이라 `cmdline-execcmds`·`clear-first`·`rain-heavy`·`status-head`·`status-tail`·`exit-request`가 `0`(기대와 다름)이었다. 그 로그의 `Command Line:` 줄을 `LaunchMac.cpp:76-95` 꼴로 바꾸고 코드의 문자열(`:678-687`·`:914-944`·`MacPlatformMisc.cpp:714`)로 만든 줄을 붙인 합성 로그에서는 `diff` 0, 빈 로그에서는 9줄이 달랐다. `pgrep -fl '[g]olmok-jaehwan/(unreal/Golmok/Golmok\.uproject|build/Mac/Golmok\.app/)'`는 두 경로를 인자로 단 더미 셸 프로세스를 둘 다 찾았고(rc 0, macOS `pgrep`의 ERE 교대), 없을 때 rc 1. `j22-line-sh`와 할 일 5의 `sed -i '' "/^Mac 부분 선행(J-20, /r …"`: rc 0, 2줄(첫 줄 빈 줄), 줄 699자·864바이트(문서 7 수정 뒤, 견본 날짜 `2026-11-28`·SHA 7자리 — 처음 판에 적은 "838자"는 바이트 수로 보인다; 같은 견본으로 처음 판의 줄은 684자·836바이트), `awk getline` 확인 `diff` 0, `grep -c '^Mac 부분 선행(J-22, '` 1, numstat `2	0`, `status.diff` `exit=0`(같은 명령을 두 번 돌리면 `2`). 할 일 7의 번호 바꾸기(가짜 번호 157): rc 0, `line-final-diff.log` `exit=0`, `근거: J-22 PR.` 0줄, base 대비 numstat `2	0`, J-20 줄의 `근거: PR #153.`은 그대로. `j22-ph-awk`는 견본 본문에서 원문 인용·명령 기록·미채움을 갈랐고, 인용 검사 명령은 견본 `quotes.tsv`에서 돌았다. 파이썬 게이트(`ruff check`·`ruff format --check`·`pytest -q` 1937 passed 3 skipped·`check_repo.py` OK)는 이 절과 기록 줄이 들어간 scratch 사본에서 통과. dry-run하지 못한 것(이 과제가 재는 것): 실제 `package.sh`(쿡 시간, 새 매니페스트·utoc의 mtime), `UnrealPak` 실행(종료 코드, CSV의 Filename 칸이 차는지 — `csv-l_dev`, 머리 줄은 소스 읽기뿐), 패키지 앱 실행(`.app`에서 `-ExecCmds` 여러 명령이 도는지, `quit`의 종료 코드, 실제 로그의 `status` 여러 줄·`clear instant`의 답·세이브 복원과의 순서, `RequestExit` 줄), 실제 잠금 갱신 루프와 UE 명령, `gh pr create`·`gh pr edit`·`gh pr checks`, 실제 본문의 인용·숫자 검사. 문서 7 수정(2026-11-28, Opus): 기록 줄을 `clear instant` 포함·로그 폴더 꼴로 바꾼 뒤 그 줄에 규칙 17 b의 `grep -n -E` 0건(바꾸기 전 줄은 `Golmok.log` 때문에 1건). 할 일 4의 방화벽 명령은 이 Mac에서 `firewall-ok.log` `1`. 할 일 1의 두 `awk` 추출과 펜스 추출 `wc -l`(`105 total`)은 scratch 사본에서 돌렸다. 위 문장의 `j22-ph-awk` 결과는 그때의 기록이다. 그 펜스는 지웠고, 지금 분류는 상시 규칙 소절의 `common-ph-awk`다.

#### J-23 19b A1 ① 회귀 헤드리스(GASP 없이) — 설계 확정(Opus 2026-11-28)
- **출처**: [pc-verify-wp19.md](../runbooks/pc-verify-wp19.md) §A1(:43-57) — 명령 블록 :45-50(`build.ps1`, `test.ps1 -Filter Golmok.Animation -SetupDevLevel`, `test.ps1 -Filter Golmok.`), 체크 :51(컴파일 성공, 경고는 기록), :52(첫 명령 4개 Success, GaspSmoke `[Info] GASP not installed — skipped (…)`, Fallback 기대 Warning 1개 소비), :53(두 번째 명령 39개), :54(StateProvider `[Error]` 없음·p0 Info 줄), :55(`Saved/Logs/Golmok.log`에 `Character mesh '' not found` 없음, §C #14), :56(PIE `golmok.anim status` — GUI), :57(`-GolmokAnim=bogus`, 선택 — GUI). §A9 "결과 (19b PC 세션이 작성)"(:140-141, 본문 `(비어 있음)` 한 줄 — `(비어 있음)`은 파일에 두 번 있고 다른 하나는 §B9 :186). 같은 꼴의 Mac 기록: [pc-verify-v17.md](../runbooks/pc-verify-v17.md) §7 표 아래 J-17 줄(:73), [pc-verify-wp16a.md](../runbooks/pc-verify-wp16a.md) §13 표 아래 J-20 줄(:364) — 둘 다 결과 절의 표·칸은 그대로 두고 그 아래에 빈 줄 하나와 `Mac 부분 선행(J-NN, …): … 근거: PR #N.` 한 줄을 더했다(+2 −0). 테스트 소스(읽기만): `Source/Golmok/Tests/GolmokAnimationTest.cpp` — 머리 주석 :1-8(넷 다 GASP 없이 통과, GaspSmoke는 skip Info), 등록 이름 :796(`Golmok.Animation.Config`)·:1008(`.StateProvider`)·:1036(`.Fallback`)·:1060(`.GaspSmoke`), p0 Info 꼴 :134, StateProvider의 호출 :283(`GASP pawn after p0`), 마네킹 skip Info :456·:567, Fallback 기대 메시지 :50(`FallbackWarning`)·:1050(`AddExpectedMessagePlain(…, Warning, Contains, 1)`), GaspSmoke skip :1066-1077(설정·매니페스트·폰 클래스 중 하나라도 없으면 `GASP not installed — skipped (config %s, manifest %s, pawn class %s)` Info 뒤 `return true`), :1089(`GASP installed: EXECUTED`). `Animation/GolmokAnimationConfig.cpp` :230(`ParseConfig` — `mode`와 무관한 검사), :348(매니페스트 `Config/Golmok/local/gasp_manifest.json`), :552(폴백 사유 `GASP pawn class missing — add-gasp / 19b (%s)`), :587·`GolmokAnimationSubsystem.cpp:250`(`anim: falling back to ABP pawn (%s)`). `Player/GolmokCharacter.cpp:85-87`(`Character mesh '%s' not found; showing capsule. …`). `Config/Golmok/animation.json`(gasp `pawn_class` `/Game/GolmokLocal/GASP/BP_GolmokCharacter_GASP.BP_GolmokCharacter_GASP_C`). 레인([DEVELOPMENT-PLAN §7.6](../DEVELOPMENT-PLAN.md) 레인 표): `Animation/`·`Tests/GolmokAnimationTest.cpp`는 "기존 게임 시스템"(Claude, :261 "그 밖의 `Source/Golmok/Tests/*`"), `Player/GolmokCharacter.cpp`는 공유 핫스팟(:266) — 이 과제는 둘 다 고치지 않는다(판정은 로그로만 하므로 열 필요도 없다. Astra 레인 :259 `Characters/` 파일도 마찬가지). `tools/ue/test.sh`: :25-26(보고서 폴더를 실행마다 지운다), :29-30(`--setup-dev-level`이면 `py import golmok.setup_dev_level as s; s.run(),Automation RunTests <필터>;Quit`), :40-42(에디터 출력·종료 코드는 버리고 보고서로 판정), :60-64(상태 줄 `{state:<10} {fullTestPath}`, 항목 줄 `    [<type>] <message>`), :68(요약 줄 `Succeeded: … Failed: … Not run: … Succeeded with warnings: …`), :69(J-36 뒤: `failed` 0이고 `succeeded`+`succeededWithWarnings` 1 이상이면 0). `tools/ue/build.sh`(UBT 종료 코드가 0이 아니면 `Build failed`). `Content/Python/golmok/setup_dev_level.py:107-112`(`L_Dev`가 있으면 Warning 한 줄 뒤 불러오기만 하고 저장하지 않는다). `.gitignore:17-18`(`Content/Characters/`·`L_Dev.umap`은 git 밖). 상시 규칙 "Mac 에디터 로그"(`~/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log`, mac-setup §8 #14 :300)·"`test.sh` 종료 코드"(J-36 #154). 2026-11-28 Opus가 읽은 기계 상태: `$W`의 `Content/GASP`·`Content/GolmokLocal`·`Config/Golmok/local` 없음, `Content/Characters/Mannequins`·`Content/Golmok/Maps/L_Dev.umap` 있음. `$W`의 마지막 전체 실행 보고서(`Saved/Automation/Report/index.json`, 2026-11-28 09:42, 39개, `succeeded` 20·`succeededWithWarnings` 19·`failed` 0)에서 Animation 4개가 모두 `Success`, GaspSmoke 항목 `GASP not installed — skipped (config ok, manifest no, pawn class missing)`, StateProvider 항목에 `GASP pawn after p0: accel 2048/2048 braking 2000/2000 friction 8.00/8.00 factor 2.00/2.00 separate 0/0 braking friction 0.00/0.00 (pawn/CDO)`, 마네킹 skip Info 없음. 같은 실행의 에디터 로그(`Golmok.log`, 09:42)에 `Character mesh '` 0줄, 폴백 줄 1줄(`LogGolmok: Verbose: anim: falling back to ABP pawn (GASP pawn class missing — add-gasp / 19b (/Game/GolmokLocal/GASP/BP_Missing.BP_Missing_C))` — 자동화가 기대 메시지로 소비해 Verbose로 찍혔다), `LogInit: Command Line: -ExecCmds="Automation RunTests Golmok.;Quit" …`(공백이 든 인자는 `이름="값"`으로 다시 이어 찍힌다), 줄 끝 `\r` 0개.
- **이력**: 이 절은 2026-11-28 문서 7의 옛 보류 표시(결과 자리·커밋 2 명령이 정해지지 않았다는 표시)와 두 보충(배정 전 보충 ①~④, 문서 7 보충)을 대신한다. 보충의 에디터 로그 사본(①), 기대 종료 코드 `0`(②), `Character mesh '' not found` `grep`(③), GUI 잠금과 갱신 루프(④, 목적 `J-23-headless`), 과제 절 뽑기·칸 자기 검사 1은 아래 명령 공통·할 일 1·3·5에 들어갔고, 남은 미정(결과 자리, 줄을 만드는 펜스, 커밋 2 명령, 칸 자기 검사 2, 인용·숫자 검사 대상 로그)은 설계 4·할 일 5~8로 정했다. 옛 "허용 파일: wp19 A1 결과 행"은 그런 행이 없어 설계 4로 바꿨다. 지금 이 절은 배정할 수 있다.
- **설계 (확정, Opus 2026-11-28)**: 재환은 아래를 그대로 옮긴다. 바꿀 점이 보이면 고치지 말고 묻는다.
  1. **범위**: §A1의 **빌드와 첫 명령**만 한다. 두 번째 명령(`--filter Golmok.`, 39개 — :53)은 이 과제가 하지 않는다: 39개 각각의 완료/skip 분류는 J-13·J-12b가 한 별도 일이고 이 과제의 고정 기대값에 넣지 않았다. PIE `golmok.anim status`(:56)와 `-GolmokAnim=bogus`(:57)는 GUI라 재환 몫이 아니다. 기록 줄은 "두 번째 명령(39개)과 PIE 단계는 하지 않았다"로 범위를 좁힌다(규칙 3·15).
  2. **빌드 먼저**: `test.sh`는 `$W`의 에디터 바이너리를 쓰므로 `origin/main`으로 바꾼 뒤 `build.sh`를 1회 돌려 바이너리를 그 SHA에 맞춘다(:45-47의 `git pull`·`build.ps1`). 판정은 종료 코드 `0`과 `Result: Succeeded` 1줄뿐이다(업투데이트여도 같다 — J-17·J-20 기록). :51의 "경고는 기록"은 `build-warn.log`(`warning: `·`error: ` 줄 원문)와 그 줄 수로만 남기고 판정하지 않는다.
  3. **첫 명령 원문**: `./tools/ue/test.sh --filter Golmok.Animation --setup-dev-level`(:48의 Mac 꼴). `L_Dev`가 이미 있으면 `setup_dev_level`은 Warning 한 줄 뒤 불러오기만 한다(:107-112). 필터는 소스에 있는 등록 이름 넷(:796·:1008·:1036·:1060)에만 맞는다(`git grep '"Golmok\.Animation'` 4줄). 한 번만 돌린다: `test.sh`가 실행마다 보고서 폴더를 지우고(:25-26) 에디터가 로그를 `Golmok-backup-<시각>.log`로 돌리므로, 두 번째 실행은 첫 실행의 증거를 바꾼다.
  4. **결과 자리**: [pc-verify-wp19.md](../runbooks/pc-verify-wp19.md) §A9 머리 줄(`### A9. 결과 `로 시작하는 줄 — 파일에 하나) 다음 줄 `(비어 있음)` **바로 뒤**에 빈 줄 하나와 한 줄을 더한다(J-17·J-20과 같은 +2 −0). `(비어 있음)`은 지우거나 바꾸지 않는다(규칙 16 — 19b PC 세션의 결과 자리는 그대로 비어 있다). §A1의 체크 상자(`- [ ]`)·명령 블록·§B9는 고치지 않는다(D-022: Mac은 추가만, §A1 전체는 GUI 단계가 남아 끝나지 않았다). 줄은 펜스 `j23-line-sh`가 날짜·SHA만 채워 만든다 — 다른 값은 모두 아래 `diff`가 0일 때만 맞는 고정 문구라 재환이 손으로 쓰는 값이 없다. 커밋 1은 끝이 `근거: J-23 PR.`이고 PR 번호가 나온 뒤 커밋 2가 `근거: PR #<번호>.`로 바꾼다(상시 규칙 "PR 본문 공통" 8). 줄에는 `.log`·`영록`·`R`+세 자리 숫자가 없다(Opus dry-run, 칸 자기 검사 0건).
  5. **고정 기대값(펜스 `j23-expected-check`)과 그 근거**: `build-result 1`(설계 2). `state-lines 4`와 `success-<이름> 1` 넷(:60-61의 상태 줄 꼴, 상태 `Success`는 경고 있는 성공도 같다 — J-12 기록). `summary-lines 1`, `summary failed=0 notrun=0 total=4`(:68 요약 줄의 `Failed`·`Not run`·`Succeeded`+`Succeeded with warnings` — 경고 개수는 실행마다 달라 판정하지 않는다). `error-entries 0`(:54 "`[Error]`가 없다"를 네 테스트 모두로 넓힌 것). `gaspsmoke-skip 1`(:1075 꼴 그대로 — 설정은 커밋 파일이 파싱되고 `ParseConfig`는 `mode`와 무관, 매니페스트 없음, 폰 클래스 `/Game/GolmokLocal/…` 없음 — 설계 6의 전제), `gaspsmoke-skip-ascii 1`(줄표 `—`의 인코딩이 다를 때 앞 검사만 0이 되게 가른다), `gaspsmoke-executed 0`. `p0-info 1`(:54 원문). `mannequin-skip 0`(:456·:567 — 마네킹이 있으면 나오지 않는다, 설계 6). 에디터 로그 사본: `editor-cmdline 1`(이 실행의 `-ExecCmds` 값 그대로 — 로그가 이 실행의 것인지), `editor-mesh-empty 0`(:55), `editor-mesh-any 0`(경로가 든 `Character mesh '…' not found`도 0 — 마네킹이 있으면 나오지 않는다), `editor-fallback 1`(:552·:587 꼴의 폴백 사유 전체 — 수준 글자(`Warning:`·`Verbose:`)는 세지 않는다. Fallback 테스트만 `mode gasp` + 없는 폰 클래스를 쓰므로 한 번). Fallback의 "기대 Warning 1개를 소비한다"(:52)는 `success-Fallback 1`이 판정한다(:1050의 기대 개수가 맞지 않으면 테스트가 실패한다). W intent·점프 apex·`land velocity z`(:54 뒷부분)는 테스트가 스스로 단언하므로(`TestTrue` — `jump apex about 90 cm`, `LandVelocity.Z < -300`) 상태 `Success`가 덮고, 이 과제는 그 Info 줄을 기록만 한다.
  6. **GASP 없음 전제**: `Content/GASP`·`Content/GolmokLocal`·`Config/Golmok/local` 셋 다 없고 `Content/Characters/Mannequins`가 있어야 한다(할 일 1의 `pre.log`). 하나라도 다르면 GaspSmoke가 다른 분기로 가거나 마네킹 skip이 생겨 기대값이 맞지 않으므로 시작하지 않고 묻는다. `add-gasp.sh`·`add-mannequin.sh`를 스스로 돌리지 않는다.
  7. **코드 변경 없음**: C++·Python·`tools/ue/*.sh`·`Config/`(핫스팟 `Default*.ini` 포함)·테스트는 고치지 않는다. 생성물(`Saved/`·`Binaries/`·`Intermediate/`)은 `.gitignore:2-4`다.

```sh j23-check-sh
#!/bin/sh
# J-23: fixed counts for pc-verify-wp19 A1 first command (usage: sh j23_check.sh <E>), one "label value" per line.
E=$1
T="$E/anim-test.log"
G="$E/anim-editor.log"
c() { printf '%s %s\n' "$1" "$2"; }
c build-result "$(grep -c -x -F 'Result: Succeeded' "$E/build.log")"
c state-lines "$(grep -c -E '^[A-Za-z]+ +Golmok\.' "$T")"
for t in Config StateProvider Fallback GaspSmoke; do c "success-$t" "$(grep -c -x -E "Success +Golmok\.Animation\.$t" "$T")"; done
c summary-lines "$(grep -c -E '^Succeeded: ' "$T")"
c summary "$(grep -E '^Succeeded: ' "$T" | awk '{print "failed=" $4 " notrun=" $7 " total=" $2 + $NF}')"
c error-entries "$(grep -c -F '    [Error] ' "$T")"
c gaspsmoke-skip "$(grep -c -x -F '    [Info] GASP not installed — skipped (config ok, manifest no, pawn class missing)' "$T")"
c gaspsmoke-skip-ascii "$(grep -c -F 'GASP not installed' "$T")"
c gaspsmoke-executed "$(grep -c -F 'GASP installed: EXECUTED' "$T")"
c p0-info "$(grep -c -x -F '    [Info] GASP pawn after p0: accel 2048/2048 braking 2000/2000 friction 8.00/8.00 factor 2.00/2.00 separate 0/0 braking friction 0.00/0.00 (pawn/CDO)' "$T")"
c mannequin-skip "$(grep -c -F 'mannequin pack missing' "$T")"
c editor-cmdline "$(grep -F 'Command Line: ' "$G" | grep -c -F -- '-ExecCmds="py import golmok.setup_dev_level as s; s.run(),Automation RunTests Golmok.Animation;Quit"')"
c editor-mesh-empty "$(grep -c -F "Character mesh '' not found" "$G")"
c editor-mesh-any "$(grep -c -F "Character mesh '" "$G")"
c editor-fallback "$(grep -c -F 'anim: falling back to ABP pawn (GASP pawn class missing — add-gasp / 19b (/Game/GolmokLocal/GASP/BP_Missing.BP_Missing_C))' "$G")"
```

```sh j23-line-sh
#!/bin/sh
# J-23: prints a blank line and the "Mac 부분 선행" line for pc-verify-wp19 section A9 (usage: sh j23_line.sh <E>).
E=$1
date=$(cat "$E/run-date.log")
sha=$(cat "$E/sha.log")
printf '\n'
printf 'Mac 부분 선행(J-23, GASP 없음, %s, SHA %s): §A1 첫 명령만 — `build.sh` 종료 코드 0. `test.sh --filter Golmok.Animation --setup-dev-level` 종료 코드 0, 4개 모두 Success(실패 0). GaspSmoke는 skip(`GASP not installed — skipped (config ok, manifest no, pawn class missing)`). Fallback은 Success, 에디터 로그의 폴백 줄 1개. StateProvider `GASP pawn after p0` Info 1줄·Error 0, 에디터 로그의 `Character mesh` 줄 0(§C #14). 두 번째 명령(39개)과 PIE 단계는 하지 않았다. 근거: J-23 PR.\n' "$date" "$sha"
```

```text j23-expected-check
build-result 1
state-lines 4
success-Config 1
success-StateProvider 1
success-Fallback 1
success-GaspSmoke 1
summary-lines 1
summary failed=0 notrun=0 total=4
error-entries 0
gaspsmoke-skip 1
gaspsmoke-skip-ascii 1
gaspsmoke-executed 0
p0-info 1
mannequin-skip 0
editor-cmdline 1
editor-mesh-empty 0
editor-mesh-any 0
editor-fallback 1
```

- **명령 공통**: 셸 변수는 Bash 호출 사이에 남지 않는다. 그래서 **모든 명령은 `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/jaehwan/J-23";`로 시작하고**, 그 뒤는 `cd "$W" &&`·`cd "$W/tools" &&`·`git -C "$W"`·`"$E/…"` 절대 경로로 시작한다(상시 규칙). 아래 명령에는 이 앞머리를 적지 않았다. 돌린 명령 원문은 `printf '%s\n' '<명령>' >> "$E/commands.txt"`로 한 줄씩 더한다(규칙 10·19 b — heredoc을 쓰지 않고, 줄을 고치거나 지우지 않는다). 각 단계의 "기대"와 다르면 **멈춤 조건**을 본다. 할 일 2(`build.sh`)·3(`test.sh`)의 명령과 할 일 6·7의 게이트·`gh pr checks --watch`는 **항상** 하네스의 백그라운드 실행으로 돌리고, 그 명령이 쓰는 `.rc` 파일(`gh pr checks --watch`는 `checks-watch.log`의 `exit=` 줄)이 생길 때까지 기다린다(명령은 바꾸지 않는다). 그 밖의 명령은 앞쪽(foreground)으로 돌린다. **시간 한도(2026-11-28 문서 9, 규칙 5)**: 이 절에서 `/usr/bin/timeout` 없이 적힌 네트워크 명령은 할 일의 `git fetch`·`gh pr list`·`git push` 두 번·`gh pr create`·`gh pr view` 다섯 가지다 — 적힌 그대로 쓰고(시간 한도를 더하거나 빼지 않는다), 점검표 규칙 5 줄에서 `not-wrapped` 무리로 적는다(상시 규칙 "PR 본문 공통" 3의 감사). 그 소절 6의 `gh pr edit`·`gh pr view`도 같다. 그 밖의 대기 명령(`build.sh`·`test.sh`·게이트·등록 대기·`gh pr checks` 두 명령)에는 `/usr/bin/timeout`이 붙어 있다.
  - **GUI 잠금**(할 일 2~3, [mac-setup §3](../runbooks/mac-setup.md) 표의 규칙, 목적 `J-23-headless` — `build.sh`·`test.sh`는 헤드리스지만 영록의 성능 측정과 겹치지 않게 J-17·J-21·J-36과 같이 잡는다): 확인 `L="$TMPDIR/claude/gui-foreground.lock"; if [ -e "$L" ]; then cat "$L"; else echo "no lock"; fi > "$E/lock-check.log"; date -u +%FT%TZ >> "$E/lock-check.log"` — 기대 첫 줄 `no lock`. 다른 줄이 있으면 **지우지 않고** 그 줄을 영록에게 보내고 기다린다. 잡기 `mkdir -p "$TMPDIR/claude" && (set -C; printf '%s %s %s\n' "재환" "J-23-headless" "$(date -u +%FT%TZ)" > "$TMPDIR/claude/gui-foreground.lock"); echo $? > "$E/lock-take.rc"` — 기대 `0`. 풀기 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-23-headless ' "$L" && rm "$L"; echo $? > "$E/lock-release.rc"` — 기대 `0`.
  - **잠금 갱신**([AGENTS.md](../../AGENTS.md) "UE를 같이 쓰는 규칙"·mac-setup §3: 20분이 지난 기록은 빈 것으로 보므로 잡은 쪽이 쓰는 동안 갱신한다): ① 할 일 2·3의 UE 명령 바로 앞에 매번 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-23-headless ' "$L" && printf '%s %s %s\n' "재환" "J-23-headless" "$(date -u +%FT%TZ)" > "$L"; echo $? > "$E/lock-refresh-<n>.rc"` — `<n>`은 할 일 2면 `build`, 3이면 `anim`. 기대 `0`. 0이 아니면(잠금 줄이 `재환 J-23-headless`가 아니다) 잠금 파일을 지우거나 쓰지 않고 멈춘다. ② 할 일 2·3의 UE 명령은 갱신 루프로 감싸 **적힌 그대로** 돌린다(이미 들어 있다): 앞에 `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-23-headless ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-23-headless" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!;`, 끝에 `; kill "$RP"`.
- **할 일**:
  1. **준비**: `mkdir -p "$E" && git -C "$W" status --porcelain > "$E/status-before.log"; grep -c -v '^?? ' "$E/status-before.log" > "$E/status-before-tracked.log"` — 기대 `0`(추적 파일 변경이 있으면 멈춘다 — 앞 과제의 작업물일 수 있다; `??` 줄은 그대로 둔다). `git -C "$W" fetch origin && git -C "$W" switch -c local/jaehwan-j23-wp19-a1 origin/main > "$E/switch.log" 2>&1; echo $? > "$E/switch.rc"` — 기대 `0`. `git -C "$W" rev-parse --short HEAD > "$E/sha.log"; git -C "$W" rev-parse HEAD origin/main | uniq | wc -l | tr -d ' ' > "$E/sha-same.log"` — 기대 `1`. `git -C "$W" show origin/main:docs/plan/jaehwan-tasks.md > "$E/tasks-main.md"; git -C "$W" rev-parse origin/main > "$E/main-rev.log"; { awk '/^#### J-23 /{f=1} /^#### J-24 /{f=0} f' "$E/tasks-main.md"; awk '/^### PR 본문 공통\(모든 과제\)$/{f=1} /^## 리뷰·병합 절차$/{f=0} f' "$E/tasks-main.md"; } > "$E/task.txt"`(규칙 14·17 c, 상시 규칙 "PR 본문 공통" 1) — 기대 `head -1 "$E/task.txt"`가 `#### J-23 `로 시작, `grep -c -x '### PR 본문 공통(모든 과제)' "$E/task.txt"` `1`. 펜스 추출(손으로 옮기지 않는다): `printf '%s\n' "j23-check-sh j23_check.sh" "j23-line-sh j23_line.sh" "common-ph-awk ph.awk" "j23-expected-check expected-check.txt" | while read -r n f; do awk -v n="$n" 'BEGIN {b = sprintf("%c%c%c", 96, 96, 96)} $0 == b && x {x=0} x {print} $0 ~ ("^" b "[a-z]+ " n "$") {x=1}' "$E/task.txt" > "$E/$f"; done; cd "$E" && wc -l j23_check.sh j23_line.sh ph.awk expected-check.txt > "$E/extract-wc.log"`(2026-11-28 문서 9: 백틱 세 개를 `sprintf`로 만드는 꼴로 바꿨다 — 뽑는 결과는 같다)(zsh는 따옴표 없는 변수를 낱말로 나누지 않으므로 `read -r n f`로 나눈다) — 기대(앞 숫자, 순서대로): `21`, `7`, `37`, `18`, 끝 줄 `83 total`. 겹침: `cd "$W" && gh pr list --state open --json number,headRefName,files --jq '.[]|select(any(.files[]; .path=="docs/runbooks/pc-verify-wp19.md"))|"\(.number) \(.headRefName)"' > "$E/overlap.log" 2>&1` — 기대 빈 파일. 같은 프로젝트를 연 편집기와 도는 UBT가 없어야 한다: `pgrep -fl '[g]olmok-jaehwan/unreal/Golmok/Golmok.uproject' > "$E/editor-before.log"; echo $? > "$E/editor-before.rc"; pgrep -fl '[U]nrealBuildTool' > "$E/ubt-before.log"; echo $? > "$E/ubt-before.rc"` — 기대 두 rc 모두 `1`(빈 파일). 전제(설계 6): `{ test -e "$W/unreal/Golmok/Content/GASP"; echo "gasp=$?"; test -e "$W/unreal/Golmok/Content/GolmokLocal"; echo "golmoklocal=$?"; test -e "$W/unreal/Golmok/Config/Golmok/local"; echo "local-config=$?"; test -d "$W/unreal/Golmok/Content/Characters/Mannequins"; echo "mannequins=$?"; cd "$W" && grep -c '^### A9\. 결과 ' docs/runbooks/pc-verify-wp19.md; awk '/^### A9\. 결과 /{getline a; print a}' docs/runbooks/pc-verify-wp19.md; grep -c '^Mac 부분 선행(J-23, ' docs/runbooks/pc-verify-wp19.md; } > "$E/pre.log"` — 기대 일곱 줄 `gasp=1`·`golmoklocal=1`·`local-config=1`·`mannequins=0`·`1`·`(비어 있음)`·`0`. 다르면 어느 것도 스스로 고치지 않고 멈춘다.
  2. **빌드**: GUI 잠금 확인·잡기. 잠금 갱신 ①(`build`). 빌드(하네스 백그라운드): `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-23-headless ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-23-headless" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && /usr/bin/timeout 1800 ./tools/ue/build.sh > "$E/build.log" 2>&1; echo $? > "$E/build.rc"; kill "$RP"` — 기대 `build.rc` `0`. 기록만(판정하지 않는다, :51 "경고는 기록"): `grep -E '(warning|error): ' "$E/build.log" > "$E/build-warn.log"; wc -l < "$E/build-warn.log" | tr -d ' ' > "$E/build-warn-count.log"`.
  3. **첫 명령**: 잠금 갱신 ①(`anim`). 실행(하네스 백그라운드): `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-23-headless ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-23-headless" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && touch "$E/anim-marker" && sleep 1 && date +%F > "$E/run-date.log" && /usr/bin/timeout 2700 ./tools/ue/test.sh --filter Golmok.Animation --setup-dev-level > "$E/anim-test.log" 2>&1; echo $? > "$E/anim-test.rc"; kill "$RP"`(`run-date.log`는 기록 줄의 날짜 — Mac의 현지 날짜) — 기대 `anim-test.rc` `0`(124 = 시간 초과 — 멈춤, 다시 돌리지 않는다). 사본(곧바로 — 다음 에디터 실행이 로그를 돌리고 다음 `test.sh`가 보고서를 지운다): `EL="$HOME/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log"; [ "$EL" -nt "$E/anim-marker" ]; echo "newer=$?" > "$E/anim-log-new.log"; cp "$EL" "$E/anim-editor.log"; echo $? > "$E/anim-cp.rc"; cp "$W/unreal/Golmok/Saved/Automation/Report/index.json" "$E/anim-index.json"; echo $? > "$E/anim-index-cp.rc"` — 기대 `newer=0`, `0`, `0`. 남은 프로세스: `pgrep -fl '[g]olmok-jaehwan/unreal/Golmok/Golmok.uproject' > "$E/editor-after.log"; echo $? > "$E/editor-after.rc"; pgrep -fl '[U]nrealBuildTool' > "$E/ubt-after.log"; echo $? > "$E/ubt-after.rc"` — 기대 두 rc 모두 `1`. 잠금 풀기.
  4. **판정**: `sh "$E/j23_check.sh" "$E" > "$E/check.log"; diff "$E/expected-check.txt" "$E/check.log" > "$E/check.diff"; echo "exit=$?" >> "$E/check.diff"` — 기대 `exit=0` 한 줄. 기록만(판정하지 않는다, PR 본문용): `grep -E '^[A-Za-z]+ +Golmok\.|^Succeeded: ' "$E/anim-test.log" > "$E/anim-states.log"; grep -E '\[Info\] (GASP not installed|GASP pawn after p0|W intent|GASP pawn jump apex)' "$E/anim-test.log" > "$E/anim-infos.log"; grep -F 'anim: falling back to ABP pawn' "$E/anim-editor.log" > "$E/anim-fallback.log"`.
  5. **런북 한 줄**: `sh "$E/j23_line.sh" "$E" > "$E/line23.txt"; echo $? > "$E/line.rc"` — 기대 rc `0`, `wc -l < "$E/line23.txt" | tr -d ' '` `2`, `head -n 1 "$E/line23.txt" | grep -c -x ''` `1`. 손으로 옮기지 않고 명령으로 §A9의 `(비어 있음)` 바로 뒤에 넣는다(규칙 19 d — 확인과 같은 호출에서): `cd "$W" && [ "$(grep -c '^Mac 부분 선행(J-23, ' docs/runbooks/pc-verify-wp19.md)" = 0 ] && sed -i '' -e '/^### A9\. 결과 /{' -e 'n' -e "r $E/line23.txt" -e '}' docs/runbooks/pc-verify-wp19.md; echo $? > "$E/line-insert.rc"` — 기대 `0`(`sed`의 `n`이 머리 줄 다음 줄 `(비어 있음)`로 넘어간 뒤 `r`이 그 줄 뒤에 파일을 붙인다. 이미 J-23 줄이 있으면 `[ … ]`가 1을 내고 `sed`는 돌지 않는다 — 멈춤). 확인: `{ printf '%s\n' '(비어 있음)'; cat "$E/line23.txt"; } > "$E/line23-expect.txt"; cd "$W" && awk '/^### A9\. 결과 /{getline a; getline b; getline c; print a; print b; print c}' docs/runbooks/pc-verify-wp19.md | diff - "$E/line23-expect.txt" > "$E/line-diff.log"; echo "exit=$?" >> "$E/line-diff.log"` — 기대 `exit=0` 한 줄. `cd "$W" && grep -c '^Mac 부분 선행(J-23, ' docs/runbooks/pc-verify-wp19.md` `1`, `cd "$W" && grep -c -x '(비어 있음)' docs/runbooks/pc-verify-wp19.md` `2`(§A9·§B9 그대로, 규칙 16). 칸 자기 검사 1(규칙 17 b): `cd "$W" && git diff -U0 origin/main -- docs/runbooks/pc-verify-wp19.md | grep '^+[^+]' > "$E/cell-lines-1.txt"; wc -l < "$E/cell-lines-1.txt" | tr -d ' ' > "$E/cell-lines-1-count.log"; grep -n -E '\.log|영록|R[0-9]{3}' "$E/cell-lines-1.txt" > "$E/cell-grep-1.log"; wc -l < "$E/cell-grep-1.log" | tr -d ' ' > "$E/cell-grep-1-count.log"` — 기대 `cell-lines-1-count.log` `1`, `cell-grep-1-count.log` `0`(상시 규칙 "PR 본문 공통" 7 — 0이 아니면 줄을 손으로 고치지 않고 멈춘다). `cd "$W" && git diff --numstat -- docs/runbooks/pc-verify-wp19.md | tr '\t' ' '` `2 0 docs/runbooks/pc-verify-wp19.md`. `git -C "$W" status --porcelain > "$E/status-after.log"; grep -v -x -F ' M docs/runbooks/pc-verify-wp19.md' "$E/status-after.log" | diff "$E/status-before.log" - > "$E/status.diff"; echo "exit=$?" >> "$E/status.diff"` — 기대 `exit=0` 한 줄(빌드·테스트가 저장소에 남긴 것이 없다).
  6. **게이트·커밋 1·push·PR**: `cd "$W/tools" && source .venv/bin/activate && { /usr/bin/timeout 300 ruff check . && /usr/bin/timeout 300 ruff format --check . && /usr/bin/timeout 1800 pytest -q && /usr/bin/timeout 300 python scripts/check_repo.py; } > "$E/gate-1.log" 2>&1; echo $? > "$E/gate-1.rc"`(하네스 백그라운드) — 기대 `0`(rc 124 = 시간 초과, 다시 돌리지 않고 멈춤). `[ "$E/gate-1.log" -nt "$W/docs/runbooks/pc-verify-wp19.md" ]; echo "newer=$?" > "$E/mtime-1.log"` — 기대 `newer=0`. 커밋: `cd "$W" && git add docs/runbooks/pc-verify-wp19.md && git diff --cached --name-only > "$E/c1-files.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-23: pc-verify-wp19 §A9 Mac 부분 선행 — A1 첫 명령(GASP 없음)" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c1-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-1.log"` — 기대 `c1-files.log` 한 줄 `docs/runbooks/pc-verify-wp19.md`, `author-1.log` `재환 <jaehwan.local@localhost>`. `git -C "$W" push -u origin local/jaehwan-j23-wp19-a1 > "$E/push-1.log" 2>&1; echo "exit=$?" >> "$E/push-1.log"` — 기대 끝 줄 `exit=0`. PR 열기(첫 본문은 이 한 문장뿐 — 상시 규칙 "PR 본문 공통" 2, 규칙 2; 2026-11-28 문서 9 검증 지적: 옛 일곱 줄 꼴을 이 한 줄로 바꿨다, dry-run sh·zsh 모두 한 줄 `CI 진행 중 — 결과는 아래에 추가`): `printf '%s\n' 'CI 진행 중 — 결과는 아래에 추가' > "$E/pr-body-initial.md"; cd "$W" && gh pr create --base main --head local/jaehwan-j23-wp19-a1 --title "J-23: WP-19 §A1 ① 회귀 헤드리스 Mac 부분 선행(GASP 없음)" --body-file "$E/pr-body-initial.md" > "$E/pr-create.log" 2>&1; echo $? > "$E/pr-create.rc"` — 기대 `0`. PR 번호: `cd "$W" && gh pr view local/jaehwan-j23-wp19-a1 --json number --jq .number > "$E/pr-number.log" 2> "$E/pr-number.err"` — 기대 `grep -c -x '[0-9][0-9]*' "$E/pr-number.log"` `1`, `wc -l < "$E/pr-number.log" | tr -d ' '` `1`(`pr-number.err`는 판정하지 않는다).
  7. **커밋 2(PR 번호)·push·CI**: `N=$(cat "$E/pr-number.log"); sed "s/ 근거: J-23 PR\.\$/ 근거: PR #$N./" "$E/line23.txt" > "$E/line23-final.txt"; cd "$W" && [ "$(grep -c ' 근거: J-23 PR\.$' docs/runbooks/pc-verify-wp19.md)" = 1 ] && sed -i '' "s/ 근거: J-23 PR\.\$/ 근거: PR #$N./" docs/runbooks/pc-verify-wp19.md; echo $? > "$E/line-pr.rc"` — 기대 `0`. 확인: `{ printf '%s\n' '(비어 있음)'; cat "$E/line23-final.txt"; } > "$E/line23-final-expect.txt"; cd "$W" && awk '/^### A9\. 결과 /{getline a; getline b; getline c; print a; print b; print c}' docs/runbooks/pc-verify-wp19.md | diff - "$E/line23-final-expect.txt" > "$E/line-final-diff.log"; echo "exit=$?" >> "$E/line-final-diff.log"` — 기대 `exit=0` 한 줄. `cd "$W" && grep -c ' 근거: J-23 PR\.$' docs/runbooks/pc-verify-wp19.md` `0`. `cd "$W" && git diff --numstat origin/main -- docs/runbooks/pc-verify-wp19.md | tr '\t' ' '` `2 0 docs/runbooks/pc-verify-wp19.md`. 칸 자기 검사 2: `cd "$W" && git diff -U0 origin/main -- docs/runbooks/pc-verify-wp19.md | grep '^+[^+]' > "$E/cell-lines-2.txt"; wc -l < "$E/cell-lines-2.txt" | tr -d ' ' > "$E/cell-lines-2-count.log"; grep -n -E '\.log|영록|R[0-9]{3}' "$E/cell-lines-2.txt" > "$E/cell-grep-2.log"; wc -l < "$E/cell-grep-2.log" | tr -d ' ' > "$E/cell-grep-2-count.log"` — 기대 `cell-lines-2-count.log` `1`, `cell-grep-2-count.log` `0`(상시 규칙 "PR 본문 공통" 7 — 0이 아니면 줄을 손으로 고치지 않고 멈춘다). 게이트 다시(규칙 13, 하네스 백그라운드): 할 일 6의 게이트 명령에서 `gate-1`을 `gate-2`로 바꾼 것 — 기대 `gate-2.rc` `0`, `[ "$E/gate-2.log" -nt "$W/docs/runbooks/pc-verify-wp19.md" ]; echo "newer=$?" > "$E/mtime-2.log"` `newer=0`. 커밋: `cd "$W" && git add docs/runbooks/pc-verify-wp19.md && git diff --cached --name-only > "$E/c2-files.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-23: 기록 줄의 근거를 PR 번호로" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c2-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-2.log"` — 기대 `c2-files.log` 한 줄 `docs/runbooks/pc-verify-wp19.md`, `author-2.log` `재환 <jaehwan.local@localhost>`. `git -C "$W" push > "$E/push-2.log" 2>&1; echo "exit=$?" >> "$E/push-2.log"` — 기대 끝 줄 `exit=0`. 브랜치 파일: `git -C "$W" diff --name-only origin/main...HEAD > "$E/branch-files.log"` — 기대 한 줄 `docs/runbooks/pc-verify-wp19.md`. push 뒤 상태: `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-final.diff"; echo "exit=$?" >> "$E/status-final.diff"` — 기대 `exit=0` 한 줄. CI 등록 대기(하네스 백그라운드, 커밋 2의 push 뒤 — 등록 지연으로 watch가 "no checks reported"로 끝나는 것을 막는다): `H=$(git -C "$W" rev-parse HEAD); cd "$W" && /usr/bin/timeout 600 sh -c 'until [ "$(gh run list --commit "$1" --json event --jq "[.[]|select(.event==\"push\" or .event==\"pull_request\")]|length")" -ge 2 ]; do sleep 30; done' sh "$H" > "$E/run-wait.log" 2>&1; echo $? > "$E/run-wait.rc"` — 기대 `0`. CI(하네스 백그라운드, `run-wait.rc` `0` 뒤): `cd "$W" && /usr/bin/timeout 1800 gh pr checks "$(cat "$E/pr-number.log")" --watch --interval 30 > "$E/checks-watch.log" 2>&1; echo "exit=$?" >> "$E/checks-watch.log"; /usr/bin/timeout 120 gh pr checks "$(cat "$E/pr-number.log")" > "$E/checks.log" 2>&1` — 기대 모든 행 pass. 그래도 `checks-watch.log`에 `no checks reported`가 있으면 첫 두 로그는 그대로 두고 같은 두 명령을 `checks-watch-2.log`·`checks-2.log`로 한 번 더 돌린다(이 경우 `## CI`·완료 기준 (h)·멈춤 조건의 `checks.log`는 `checks-2.log`로 읽는다. 할 일 8의 `j23_bodycheck.sh`는 `checks-2.log`가 있으면 숫자 검사에서 `checks.log` 대신 그것을 센다 — 스크립트는 바꾸지 않는다).
  8. **PR 본문**: PR 본문·자리표시 분류·칸 자기 검사·근거 표기는 상시 규칙 "PR 본문 공통(모든 과제)"을 따른다(이 절과 다르면 그 소절을 따른다). `## 결과`에는 관찰한 값만 둔다: `build.rc`, `build-warn-count.log`, `anim-test.rc`, `check.log` 열여덟 줄, `anim-states.log` 다섯 줄, `anim-infos.log`, `anim-fallback.log`, 런북에 넣은 `line23-final.txt` 둘째 줄(로그 원문은 모두 백틱 펜스 블록에 그대로) — 그 펜스 밖에는 과제 번호·규칙 번호·날짜를 쓰지 않는다. `anim-test.log` 전체·`anim-editor.log`·`build.log`는 본문에 붙이지 않는다(엔진 경로가 길다). `## 실행한 명령` 끝의 줄 수 목록(상시 규칙 "PR 본문 공통" 2 크기)은 이 세 파일만이다. `## 완료 기준 대조`는 아래 (a)~(i) 한 줄씩(과제 글에 백틱 펜스가 들어 있어 물결 펜스 `~~~`를 쓴다). 본문 초안은 `$E/pr-body.md`. 사용자 경로 검사(공통 표기 — 공개 저장소에 사용자 이름이 든 절대 경로를 쓰지 않는다): `grep -c -F "$HOME" "$E/pr-body.md" > "$E/home-path.log"` — 기대 `0`(0이 아니면 그 줄을 `~` 기준으로 고쳐 다시 센다. 펜스 안 원문에서 걸리면 고치지 않고 멈춘다). 게시 전 검사(규칙 10 e·f) — **대상 로그는 이 목록으로 고정한다**(본문 초안·게시본·`task.txt`·`commands.txt`·검사 로그 자신은 넣지 않는다): `"$E"/build.log "$E"/build-warn.log "$E"/build-warn-count.log "$E"/anim-test.log "$E"/anim-states.log "$E"/anim-infos.log "$E"/anim-editor.log "$E"/anim-fallback.log "$E"/check.log "$E"/line23-final.txt "$E"/sha.log "$E"/run-date.log "$E"/gate-2.log "$E"/checks.log`.
     - 인용 검사: `## 결과` 절의 백틱 문자열마다 그 문자열이 근거로 든 로그 **한 개**를 `"$E/quotes.tsv"`에 `<문자열><탭><위 목록의 파일 이름>`으로 적는다(로그 인용이 아닌 파일 이름·명령은 파일 칸에 `라벨`). 빠진 것 확인·세기와 아래 숫자 검사는 펜스 `j23-bodycheck-sh`(이 절의 허용 파일 줄 바로 앞)가 한 번에 한다(2026-11-28 문서 9: 백틱이 든 옛 인라인 명령을 글자 그대로 옮긴 스크립트 — 옛 명령과 같은 여섯 파일 `body-quotes.txt`·`tsv-quotes.txt`·`quotes-missing.log`·`quotes-check.log`·`body-numbers.txt`·`numbers-check.log`를 쓴다(`checks-2.log`가 없으면 내용도 같다); 숫자 검사 목록 끝의 `checks.log`는 `checks-2.log`가 있으면 그것; 상시 규칙 "PR 본문 공통" 11·14). `quotes.tsv`를 다 쓴 뒤 뽑기·확인·실행을 한 호출로: `awk -v n=j23-bodycheck-sh 'BEGIN {b = sprintf("%c%c%c", 96, 96, 96)} x && $0 == b {x = 0} x {print} !x && index($0, b) == 1 && $0 ~ (" " n "$") {x = 1}' "$E/task.txt" > "$E/j23_bodycheck.sh"; [ "$(wc -l < "$E/j23_bodycheck.sh" | tr -d ' ')" = "13" ] && head -n 1 "$E/j23_bodycheck.sh" | grep -q -x '#!/bin/sh' && sh "$E/j23_bodycheck.sh" "$E" > "$E/bodycheck.log" 2>&1; echo $? > "$E/bodycheck.rc"` — 기대 `bodycheck.rc` `0`, `bodycheck.log` 빈 파일, `quotes-missing.log` 빈 파일. 세기는 `quotes-check.log`(`quotes.tsv` 행마다 한 행) — 기대: `cut -f1 "$E/quotes-check.log" | grep -c -x '0'`가 `0`.
     - 숫자 검사: 위 `j23_bodycheck.sh`가 쓴 `body-numbers.txt`·`numbers-check.log`(숫자마다 한 행, 대상은 위 고정 목록) — 기대: `cut -f1 "$E/numbers-check.log" | grep -c -x '0'`가 `0`. 한 자리 숫자는 이 검사에 걸리지 않으므로 문맥 문자열(예: `success-Fallback 1`)로 인용 검사에 넣는다.
     - 0이 나온 것은 고치거나 지운다. 그다음 상시 규칙 "PR 본문 공통" 3(점검표 대조)·5(자리표시 분류)·6(조립·게시·다시 읽기)을 적힌 그대로 돌린다.
```sh j23-bodycheck-sh
#!/bin/sh
# J-23: quote and number checks of the PR draft (usage: sh j23_bodycheck.sh <E>); needs E/pr-body.md and E/quotes.tsv.
# Same commands as the inline checks they replace (docs 9); writes body-quotes.txt, tsv-quotes.txt,
# quotes-missing.log, quotes-check.log (one row per quotes.tsv row), body-numbers.txt, numbers-check.log (one row per number).
E=$1
CK=checks.log
if [ -e "$E/checks-2.log" ]; then CK=checks-2.log; fi
awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '`[^`]+`' | sed 's/^`//;s/`$//' | sort -u > "$E/body-quotes.txt"
cut -f1 "$E/quotes.tsv" | sort -u > "$E/tsv-quotes.txt"
comm -23 "$E/body-quotes.txt" "$E/tsv-quotes.txt" > "$E/quotes-missing.log"
while IFS="$(printf '\t')" read -r q f; do if [ "$f" = "라벨" ]; then n="라벨"; else n=$(grep -F -c -- "$q" "$E/$f"); fi; printf '%s\t%s\t%s\n' "$n" "$f" "$q"; done < "$E/quotes.tsv" > "$E/quotes-check.log"
awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '[0-9]{2,}' | sort -u > "$E/body-numbers.txt"
while read -r x; do printf '%s\t%s\n' "$(cat "$E"/build.log "$E"/build-warn.log "$E"/build-warn-count.log "$E"/anim-test.log "$E"/anim-states.log "$E"/anim-infos.log "$E"/anim-editor.log "$E"/anim-fallback.log "$E"/check.log "$E"/line23-final.txt "$E"/sha.log "$E"/run-date.log "$E"/gate-2.log "$E/$CK" | grep -c -- "$x")" "$x"; done < "$E/body-numbers.txt" > "$E/numbers-check.log"
```

- **허용 파일**: `docs/runbooks/pc-verify-wp19.md`(§A9 `(비어 있음)` 바로 뒤에 빈 줄 하나와 펜스 `j23-line-sh`의 줄 하나만 — 할 일 5의 `sed`로 넣고 할 일 7의 `sed`로 끝만 바꾼다). 그 밖의 저장소 파일은 고치지 않는다: §A1 체크 상자·명령 블록, `(비어 있음)` 두 줄, §B·§C·§D, mac-setup, C++(`Animation/`·`Tests/`·`Player/`)·Python·`tools/ue/*.sh`·`Config/`(핫스팟 `Default*.ini`·`animation.json` 포함)·테스트·공유 문서·이 과제 파일. 생성물(`Saved/`·`Binaries/`·`Intermediate/`)과 앞 과제의 `??` 파일은 커밋하지 않는다.
- **멈춤 조건(정하지 말고 영록에게 묻는다)**: `status-before-tracked.log`가 0이 아닐 때. `switch.rc`가 0이 아니거나 `sha-same.log`가 1이 아닐 때. `head -1 "$E/task.txt"`가 `#### J-23 `로 시작하지 않을 때. `extract-wc.log`가 기대와 다를 때. `overlap.log`가 비어 있지 않을 때. `editor-before.rc`·`ubt-before.rc`가 1이 아닐 때(끄지 않는다). `pre.log`가 기대 일곱 줄과 다를 때(GASP·로컬 GASP 설정이 있다, 마네킹이 없다, §A9 꼴이 다르다, J-23 줄이 이미 있다 — 어느 것도 스스로 고치지 않는다). 잠금 파일에 다른 기록이 있거나 잠금 잡기 rc가 0이 아닐 때. `lock-refresh-build.rc`·`lock-refresh-anim.rc` 중 하나가 0이 아닐 때(잠금 파일을 지우거나 쓰지 않는다). `build.rc`가 0이 아닐 때(124 = 시간 초과, 규칙 5 — 컴파일 오류를 고치지 않고 `build.log`의 `error: ` 줄을 보낸다, §A1 :51의 "고치고 커밋"은 PC 세션 규칙이고 재환 몫이 아니다). `anim-test.rc`가 0이 아닐 때(124 포함 — 다시 돌리지 않는다, 설계 3), `anim-log-new.log`가 `newer=0`이 아니거나 `anim-cp.rc`·`anim-index-cp.rc`가 0이 아닐 때. `editor-after.rc`·`ubt-after.rc`가 1이 아닐 때(아래 "멈춤 순서"). `check.diff`가 `exit=0` 한 줄이 아닐 때 — 특히 `editor-cmdline 0`(로그가 이 실행의 것이 아니다 — 이때 `grep -F 'Command Line: ' "$E/anim-editor.log"` 한 줄을 함께 보낸다), `gaspsmoke-skip 0`과 `gaspsmoke-skip-ascii 1`(줄표 인코딩 — 기대 문구를 바꾸지 않는다), `gaspsmoke-executed 1`(GASP가 있다), `p0-info 0`(p0 값이 엔진 기본값과 다르다 — §D #6, 재환은 판단하지 않는다), `editor-mesh-any` 0 초과(§C #14 대안은 Claude 레인), `mannequin-skip` 0 초과. `line.rc`·`line-insert.rc`·`line-pr.rc`가 0이 아니거나 `line23.txt` 확인값·`line-diff.log`·`line-final-diff.log`·`status.diff`·`status-final.diff`가 기대와 다를 때. `cell-lines-1-count.log`·`cell-lines-2-count.log`가 `1`이 아니거나 `cell-grep-1-count.log`·`cell-grep-2-count.log`가 `0`이 아닐 때(줄을 손으로 고치지 않는다). `gate-1.rc`·`gate-2.rc`가 0이 아닐 때(rc 124 포함, 다른 파일을 고치거나 `ruff format`으로 바꾸지 않는다). `mtime-1.log`·`mtime-2.log`가 `newer=0`이 아닐 때. `c1-files.log`·`c2-files.log`·`author-1.log`·`author-2.log`가 기대와 다를 때. `lock-release.rc`가 0이 아닐 때(잠금 파일을 지우지 않는다). `push-1.log`·`push-2.log`가 `exit=0`으로 끝나지 않을 때, `branch-files.log`가 `docs/runbooks/pc-verify-wp19.md` 한 줄이 아닐 때. `pr-create.rc`·`pr-edit.rc`가 0이 아니거나 `pr-number.log`가 숫자 한 줄이 아닐 때. `run-wait.rc`가 0이 아닐 때(124 = 10분 안에 두 실행이 등록되지 않았다 — 다시 돌리지 않는다). `checks.log`에 pass가 아닌 행이 있을 때. `home-path.log`가 두 번 고친 뒤에도 0이 아닐 때. 상시 규칙 "PR 본문 공통" 9의 공통 멈춤 조건. 넓은 명령에서 macOS 권한 창이 뜰 때(누르지 않는다 — 소유자 항목). 그 밖에 이 절의 "기대"와 다른 값이 하나라도 나올 때. **코드·설정·테스트 결함으로 보이는 것을 고치지 않는다**(Claude 레인 — 재현 절차만 보고). **멈춤 순서 — 할 일 2~3 안에서 멈출 때는 이 순서로 한다**: ① `pgrep -fl '[g]olmok-jaehwan/unreal/Golmok/Golmok.uproject' > "$E/editor-stop.log"; echo $? > "$E/editor-stop.rc"; pgrep -fl '[U]nrealBuildTool' > "$E/ubt-stop.log"; echo $? > "$E/ubt-stop.rc"`. ② 두 rc가 모두 `1`이면 잠금 풀기를 돌려 `lock-release.rc`를 남기고 묻는다. 하나라도 `0`이면(에디터·UBT가 남았다) 프로세스를 건드리지 않고 잠금도 풀지 않은 채 `editor-stop.log`·`ubt-stop.log`를 영록에게 보낸다.
- **완료 기준**:
  - (a) 준비: `status-before-tracked.log` `0`, `switch.rc` `0`, `sha-same.log` `1`, `task.txt` 첫 줄 `#### J-23 `, `extract-wc.log` 원문(기대 숫자와 같다), `overlap.log` 빈 파일, `editor-before.rc`·`ubt-before.rc` `1`, `pre.log` 일곱 줄 `gasp=1`·`golmoklocal=1`·`local-config=1`·`mannequins=0`·`1`·`(비어 있음)`·`0`.
  - (b) 빌드: `lock-take.rc` `0`, `lock-refresh-build.rc` `0`, `build.rc` `0`, `build-warn-count.log` 원문(기록).
  - (c) 첫 명령: `lock-refresh-anim.rc` `0`, `anim-test.rc` `0`, `anim-log-new.log` `newer=0`, `anim-cp.rc`·`anim-index-cp.rc` `0`, `editor-after.rc`·`ubt-after.rc` `1`, `lock-release.rc` `0`.
  - (d) 판정: `check.diff` `exit=0`(`check.log` 열여덟 줄 원문 — `success-GaspSmoke 1`·`gaspsmoke-skip 1`·`gaspsmoke-executed 0`·`p0-info 1`·`editor-mesh-empty 0`·`editor-fallback 1` 포함). GaspSmoke는 **skip**으로 적는다(완료라 쓰지 않는다 — 규칙 15, R149·R153). `anim-states.log`·`anim-infos.log`·`anim-fallback.log` 원문(기록).
  - (e) 런북 줄: `line.rc` `0`, `line23.txt` 2줄(첫 줄 빈 줄), `line-insert.rc` `0`, `line-diff.log` `exit=0`, `grep -c '^Mac 부분 선행(J-23, '` `1`, `(비어 있음)` `2`, numstat `2 0 docs/runbooks/pc-verify-wp19.md`, `status.diff` `exit=0`, `cell-lines-1-count.log` `1`, `cell-grep-1-count.log` `0`.
  - (f) 커밋 1·PR: `gate-1.rc` `0`, `mtime-1.log` `newer=0`, `c1-files.log`·`author-1.log` 기대대로, `push-1.log` 끝 줄 `exit=0`, `pr-create.rc` `0`, `pr-number.log` 숫자 한 줄.
  - (g) 커밋 2: `line-pr.rc` `0`, `line-final-diff.log` `exit=0`, `근거: J-23 PR.` 0줄, `origin/main` 대비 numstat `2 0 docs/runbooks/pc-verify-wp19.md`, `cell-lines-2-count.log` `1`, `cell-grep-2-count.log` `0`, `gate-2.rc` `0`, `mtime-2.log` `newer=0`, `c2-files.log`·`author-2.log` 기대대로, `push-2.log` 끝 줄 `exit=0`, `branch-files.log` 한 줄, `status-final.diff` `exit=0`.
  - (h) CI `run-wait.rc` `0`, `checks.log` 모든 행 pass 원문(규칙 2).
  - (i) PR 본문: 절 순서(상시 규칙 "PR 본문 공통" 2), "완료 기준 대조" 절, 점검표(그날 규칙 수만큼, 소절 3). `home-path.log` `0`, `quotes-missing.log` 빈 파일, `quotes-check.log`·`numbers-check.log`에 0 없음. 공통 완료 기준 (P)(소절 10): `checklist.diff` `exit=0`, `ph-unfilled.log` `0`, `pr-edit.rc` `0`, `ph-posted-unfilled.log` `0`, `ph-table.diff` `exit=0`, `signature-last.log` `1`, `cell-grep-1-count.log`·`cell-grep-2-count.log` `0`.
- **병합 시 반영(영록)**: STATUS 재환 절에 J-23 행. WP-19 행(🟡)은 바꾸지 않는다 — §A1의 두 번째 명령·PIE 단계가 남았다. pc-verify-wp19 §A1 명령 블록 아래에 "Mac 명령(추가)" 블록이 필요하면 이 PR `## 실행한 명령`의 할 일 2·3 명령에서 `$E` 리다이렉트·잠금 줄을 뺀 꼴로 영록 Opus가 쓴다(규칙 16 — 있는 글은 지우지 않는다).
- **왜 재환 / 위험**: 모든 판정이 종료 코드와 고정 기대값과의 `diff`로 끝나고, 기록 줄은 펜스가 만든다. 코드도 Astra 레인도 건드리지 않는다. 위험: ① GaspSmoke의 skip을 완료로 읽는 것(R149·R153의 반복) — 기대값이 skip 문구 1과 `EXECUTED` 0을 함께 요구하고, 기록 줄이 "skip"으로 고정돼 있다. ② 옛 로그·보고서를 이 실행의 것으로 읽는 것 — mtime 표식(`anim-log-new`), 이 실행의 `-ExecCmds` 값(`editor-cmdline`), 실행마다 지워지는 보고서 폴더로 막는다. ③ "없다" 검사가 빈 검사가 되는 것 — `editor-cmdline 1`·`editor-fallback 1`이 같은 로그 사본에서 양성으로 맞아야 `editor-mesh-* 0`이 뜻을 갖는다. ④ 두 번째 실행으로 증거를 덮는 것 — 금지(설계 3). ⑤ 빌드·테스트 실패를 고치려는 것 — 멈추고 보고한다. ⑥ 메인 체크아웃에서 돌리는 것(2026-11-27 사고, 규칙 6) — 모든 명령이 `$W`·`$E` 절대 경로다. 수치(시간·fps)는 재지 않는다.
- **dry-run 범위(Opus 2026-11-28)**: `origin/main` `366e118`의 scratch 사본(`git archive`, git 저장소로 만든 것)에 이 절을 넣고 한 것: 할 일 1의 과제 추출(첫 줄 `#### J-23 `, `### PR 본문 공통(모든 과제)` 1)과 펜스 추출(zsh, `wc -l` 21·7·37·18, `83 total`), 추출한 파일이 이 절의 펜스와 바이트가 같음. `j23-check-sh` 입력: `$W`의 마지막 전체 실행 보고서 사본(2026-11-28 09:42)을 Animation 4개로 줄이고 `test.sh`의 :49-70 파이썬 블록을 글자 그대로 돌려 만든 `anim-test.log`, 같은 실행의 에디터 로그 사본, 합성 `build.log`(`Result: Succeeded` 한 줄). 그 로그의 `Command Line:` 줄은 `--setup-dev-level` 없이 돈 실행이라 `editor-cmdline 0`(기대와 다름 — 1줄 차이), 그 줄의 `-ExecCmds` 값만 이 과제의 값으로 바꾼 사본에서 `diff` 0(sh·zsh 같음). 빈 검사가 아님: Fallback을 `Fail`·요약 `Failed: 1`·`[Error]` 한 줄로 바꾸면 3줄, GaspSmoke Info를 `GASP installed: EXECUTED`로 바꾸면 3줄, `Character mesh '' not found` 줄과 마네킹 skip Info를 더하면 3줄, 빈 로그 셋이면 13줄, 줄표를 `?`로 바꾸면 `gaspsmoke-skip 0`·`gaspsmoke-skip-ascii 1`로 1줄이 달랐다. `j23-line-sh`(견본 날짜 `2026-11-28`·SHA 7자리): rc 0, 2줄(첫 줄 빈 줄), 줄 429자·556바이트, 규칙 17 b의 `grep -n -E` 0건. 할 일 5의 `sed -e '/^### A9\. 결과 /{' -e 'n' -e "r …" -e '}'`(macOS `/usr/bin/sed`): rc 0, `(비어 있음)` 바로 뒤에 들어감, `awk getline` 확인 `diff` 0, `grep -c '^Mac 부분 선행(J-23, '` 1, `(비어 있음)` 2, numstat `2 0`, `cell-lines-1-count` 1·`cell-grep-1-count` 0. 같은 `sed`를 확인 없이 두 번 돌리면 `2`(그래서 `[ … = 0 ] &&`로 막았다). 할 일 7의 번호 바꾸기(가짜 번호 161): `line-final-diff` `exit=0`, `근거: J-23 PR.` 0줄, base 대비 numstat `2 0`, `cell-lines-2-count` 1·`cell-grep-2-count` 0. 줄이 들어간 사본에서 `check_repo.py` `OK (uproject, ini, json, links, gitattributes, conflicts, gasp)`, `ruff check` `All checks passed!`, `ruff format --check` 통과, `pytest -q` `1940 passed, 3 skipped`. dry-run하지 못한 것(이 과제가 재는 것): 실제 `build.sh`(종료 코드, `Result: Succeeded`), 실제 `test.sh --filter Golmok.Animation --setup-dev-level`(종료 코드, 네 상태, 요약 줄의 `Not run` 값, `--setup-dev-level`이 든 실행의 `Command Line:` 줄 꼴 — `LaunchMac.cpp`의 다시 잇기와 09:42 로그의 `-ExecCmds="…"` 꼴에서 미룬 것, 필터 실행에서의 폴백 줄 개수), 잠금 갱신 루프, `gh pr create`·`gh pr edit`·`gh pr checks`, 실제 본문의 인용·숫자·사용자 경로 검사.

#### J-24 V-08b §9-1·§9-2 `locomotion_metrics.py` 순수 지표 1차분 — 설계 확정(Opus 2026-11-28)
- **출처**: [pc-verify-v08b.md](../runbooks/pc-verify-v08b.md) §9(:349-389 — §9-1 파일 표 :355-364, 틱 JSON 최소 필드 :366-369, §9-2 통일 정의 표 :371-379, 수락 (a)~(c)와 "미대조" :381-385, §9-3 커밋 :387-), §1-4 적용 확인 (c)(:105, 표 B 크기: 걷기 90 % 0.08~0.09 s, 달리기 0.23 s, 정지 2~3 / 14~15 cm), §2 S3 지표(:136 "root 뼈 yaw − 캡슐 yaw, 메시 기본 yaw 보정"), §6-1 Offset Root Bone(:279-283: 최대·p95·yaw 차 최대·복귀 시간), §7 계단 접지(:307-). [pc-verify-wp18a.md](../runbooks/pc-verify-wp18a.md) §14-5(:383-388: V-11 정의 — "평지 프레임의 2번째 백분위 + 2.5 cm 이내이고 캡슐이 접지 중", "틱마다 딛은 소켓의 수평 이동 중 최솟값을 합해", "15 cm/s보다 빨리 움직인 틱 수"). 헤더(읽기만, Claude 레인): `unreal/Golmok/Source/Golmok/Animation/GolmokLocomotionMath.h` :41-42(`PlantedToleranceCm = 2.5`), :182-188(`FootSample`), :190-234(`PlantedTravelCm`: 표본 2개 미만 0, 바닥 = 접지·유한 z의 최솟값, 디딤 = 접지 ∧ 유한 ∧ z ≤ 바닥 + 2.5, 연속 두 디딤 사이 `sqrt(DX*DX + DY*DY)`가 유한일 때만 더함), :235-243(`PlantedSlipCmPerM`: 비유한 또는 캡슐 < 1 cm면 0). 캡슐 이동의 뜻: `Tests/GolmokAnimationTest.cpp:740`(`CapsuleTravel += FVector::Dist2D(Capsule, LastCapsule)` — 틱 사이 수평 경로 합). 대조 드라이버(고치지 않음): `tools/tests/fixtures/ue/locomotionmath_driver.cpp` :115-134(`planted <n> (x y z on_ground)*n`, `slip <travel> <capsule>`, `setprecision(17)`, `strtod`라 `nan`·`inf` 토큰이 헤더에 닿는다). 기존 테스트(가져다 쓰기만): `tools/tests/test_ue_locomotion_math.py` :20-23(`HEADER_DIR`·`DRIVER`), :26-59(`driver` 픽스처 — g++ → clang++ → c++, `-ffp-contract=off`, 없으면 skip), :62-73(`run`), :312-313(`_planted_command`), :316-321(12.6 > 10 + 2.5 경계), :380-382(비유한 사례 → 1.0). 메시 yaw −90: `unreal/Golmok/Config/Golmok/characters.json:28` 등 `"mesh_yaw_deg": -90`, `Player/GolmokCharacter.cpp:64` `FRotator(0.f, -90.f, 0.f)`. 선례: `tools/golmok_tools/audio_analysis.py`(console script 없이 `python -m`, `main(argv) -> int`), 다른 테스트 모듈에서 이름 가져오기(`tests/test_ue_photo_math.py:23` `from test_ue_stats_math import …`). numpy `percentile`의 `method` 인자는 1.22.0부터, 기본값 `'linear'`([numpy.percentile](https://numpy.org/doc/stable/reference/generated/numpy.percentile.html)). CI(`.github/workflows/ci.yml:20-52`): python 잡 4행(ubuntu 3.11·3.12, windows 3.12, macos 3.12)이 `pytest -q`를 돈다. Windows 러너 이미지에는 gcc 15.2.0이 있다([Windows2025-Readme](https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md)); `origin/main` `366e118`의 CI 실행 46106753000에서 python 행 요약은 macos `1940 passed, 3 skipped`, ubuntu 둘 `1939 passed, 4 skipped`, windows `1897 passed, 46 skipped`였다 — 이 Mac에서 컴파일러를 PATH에서 뺀 실행은 컴파일러 의존 테스트 268개를 skip하므로, Windows의 skip 차이 42는 컴파일러가 없어서가 아니다(Windows는 드라이버를 컴파일한다).
- **이력**: 이 절은 옛 "설계 선행" 메모(함수 서명·스키마·합성 사례·드라이버 대조 방식은 메모가 정한다)를 대신한다(Opus 2026-11-28).
- **설계 (확정, Opus 2026-11-28)**: 재환은 아래를 그대로 옮긴다. 코드·테스트·fixture는 펜스 그대로 복사하고 한 글자도 고치지 않는다. 바꿀 점이 보이면 고치지 말고 묻는다.
  1. **범위(좁힌 1차분)**: 이 과제는 `planted_travel_cm`·`planted_slip_cm_per_m`(헤더와 같음), `slip_frames`, `legacy_v11_slip`, 표 B 반응(`reaction_time_s`·`stop_after_release`), Offset Root Bone(`offset_root_distance_cm`·`offset_yaw_deg`), 최소 로더 `load_ticks`, `report` CLI만 만든다. **J-24b로 미룬다(별도 설계)**: `stair_contact`(L_Dev 계단·턱 높이 상수가 `setup_dev_level`에 있어 §7과 함께 설계), 돌아서기 시간(S3), 벽 최소 거리·관통 근사(§6-2), Offset 복귀 시간(§6-1 넷째 항목), `blind`·`unblind`(§10 — ffmpeg·프레임 시트, 채점 몫). 드라이버·`locomotion_pure.py`·SendInput은 J-31·Opus B1 몫이다. 지표의 의미와 "좋은" 값의 기준은 이 과제가 정하지 않는다(D-020, Opus).
  2. **파일**: 새 파일 셋 — `tools/golmok_tools/locomotion_metrics.py`(펜스 `j24-module-py`), `tools/tests/test_locomotion_metrics.py`(펜스 `j24-test-py`), `tools/tests/fixtures/locomotion/ticks_min.json`(펜스 `j24-fixture-json`, 합성 8틱). `tools/pyproject.toml`(핫스팟)·console script는 건드리지 않는다(`python -m`, `audio_analysis` 선례). numpy는 이미 기본 의존성이다(`pyproject.toml` `dependencies`).
  3. **틱 JSON 최소 로더**(`golmok-locomotion-ticks/1`, §9-1 :366-369): 장면 필드 `schema`(정확히 `golmok-locomotion-ticks/1`)·`scene`·`condition`·`pawn_class`·`profile`·`map`(문자열)·`speeds`(객체, `walk`·`run` 숫자 필수). `ticks`(목록, 2개 이상). 틱 필드 `t`(앞 틱보다 커야 함)·`dt`·`keys`(문자열 목록)·`capsule`(숫자 3개)·`yaw`·`half_height`·`on_ground`(true/false)·`vel`(숫자 3개)·`bones`(객체, `root`·`foot_l`·`foot_r`·`ball_l`·`ball_r` 필수, 각 숫자 3개). 모든 숫자는 유한해야 한다. **선택 필드 `root_yaw`**(root 뼈 월드 yaw, 도): 첫 틱에 있으면 모든 틱에 있어야 하고, 없으면 보고의 yaw 열은 `-`다 — §9-1 최소 필드는 위치만 있어 §2·§6-1의 yaw 차를 낼 수 없으므로 이 모듈이 더한다(최소 필드 목록의 확장이지 변경이 아니다). `cmc`·`visual_bones`·다른 뼈 등 나머지 필드는 읽지 않는다. 오류는 `TicksError`(ValueError)이고 메시지는 `<파일 이름>: <내용>` 꼴이다. 메시지 19종 + 최상위·JSON 2종은 테스트 `test_loader_error_messages`·`test_loader_rejects_non_object_and_bad_json`이 하나씩 일으켜 글자 그대로 본다(규칙 8): 예 `bad.json: missing field ticks[2].vel`, `bad.json: schema is 'golmok-locomotion-ticks/2', expected 'golmok-locomotion-ticks/1'`, `bad.json: non-finite value in ticks[3].capsule[1]`, `bad.json: scene has 1 tick(s), need at least 2`, `bad.json: ticks[6].bones has no ball_r`. 로더는 비유한 값을 거부하지만, 순수 함수 `planted_travel_cm`·`planted_slip_cm_per_m`은 헤더처럼 비유한 입력을 받는다(헤더 대조용).
  4. **정의(작업 숫자는 fixture `ticks_min.json` — 8틱, t = 0.0~0.7 s, 0.1 s 간격, 모두 접지)**:
     - 캡슐 이동 = 틱 사이 수평 거리 `sqrt(dx*dx + dy*dy)`의 합(`GolmokAnimationTest.cpp:740`과 같다). fixture: x 0, 0, 10, 25, 43, 58, 63, 63 → 63 cm = `capsule_m` `0.630`.
     - `planted_travel_cm`(헤더 :190-234와 같음): 뼈마다 바닥 = 접지 틱의 유한 z 최솟값(장면 전체 — 평지 구간 고르기는 호출하는 쪽 몫, §9-2 "평지 장면만 쓴다"). 디딤은 그 틱 하나의 조건(접지 ∧ 유한 ∧ z ≤ 바닥 + 2.5)이고, 이동은 **연속 두 틱이 모두 디딤**일 때만 더한다. fixture `foot_l`: z 10, 10, 10.5, 10, 20, 25, 12, 10(바닥 10, 12.5까지 디딤) → 쌍 0-1 0, 1-2 1, 2-3 0, 6-7 0.5 = 1.5 cm(5-6은 5가 들림). `foot_r`: z 10, 20, 22, 11, 10, 10, 18, 24 → 쌍 3-4 2, 4-5 0 = 2.0 cm. `planted_slip_cm_per_m` = (1.5 + 2.0) / 0.63 = 5.5556 → `5.556`.
     - `slip_frames` = (두 틱 모두 디딘 발 중 하나라도 수평 속도 > 15 cm/s인 틱 쌍 수, 두 틱 모두 디딘 발이 하나라도 있는 틱 쌍 수). 속도 = 이동 ÷ (t[i] − t[i−1]) — `dt` 필드가 아니라 `t` 차를 쓴다. fixture: 디딘 쌍이 있는 틱 1·2·3·7(`foot_l`)·4·5(`foot_r`) = 6, 그중 틱 4(`foot_r` 2 cm / 0.1 s = 20 cm/s)만 15 초과(`foot_l` 1 cm / 0.1 s = 10은 아님) → `1/6`. 분모를 같이 내는 것은 V-11 표의 `353/356` 꼴(wp18a :387)과 맞추려는 것이다.
     - `legacy_v11_slip`(wp18a :385의 글을 이렇게 고정한다): 소켓 = `foot_l`·`foot_r`·`ball_l`·`ball_r` 네 뼈(V-11의 "발목·앞꿈치" 소켓을 틱 JSON의 뼈로 대신한다 — V-11 스크립트와 같은지는 [미확인], 수락 (c) 몫). 기준 = 소켓마다 **장면 전체 접지 틱**의 z에 numpy `percentile(…, 2, method="linear")`(26개 z = 0~25면 0.5 — `lower`면 0). 디딤 = 그 틱 하나에서 접지 ∧ z ≤ 기준 + 2.5(**앞 틱 조건 없음** — 통일 정의와 다른 점). 둘째 틱부터 틱마다, 그 틱에 디딘 소켓들의 앞 틱→이 틱 수평 이동 중 **최솟값**을 더한다(디딘 소켓이 없으면 0). 나누기는 통일 정의와 같은 캡슐 이동(1 cm 미만 0). fixture: 틱 1~7의 최솟값 0, 1, 0, 2, 0, 20, 0.5 = 23.5 cm → 23.5 / 0.63 = 37.3016 → `37.302`(틱 6은 `foot_l`이 들린 틱 5 다음에 20 cm 앞에 내려선 틱이라 통일 정의는 빼고 legacy는 센다).
     - 표 B 반응(§9-2 :378): 누름 틱 k = 키가 들어 있고 앞 틱에는 없던 첫 틱(틱 0에 있으면 0). 반응 = 수평 속도(`vel`의 x·y) ≥ 0.9 × 목표인 k 이후 첫 틱 j의 t[j] − t[k](틱 사이 보간 없음, 못 닿으면 None). 정지: 뗌 틱 r = k 뒤에서 키가 없는 첫 틱, 정지 틱 j = r 이후 수평 속도 < 1 cm/s인 첫 틱. 시간 t[j] − t[r], 거리 = 틱 r부터 j까지의 캡슐 수평 경로(r로 들어오는 이동은 넣지 않는다). fixture: W는 틱 1~4, `vel` x 0, 0, 100, 150, 180, 150, 50, 0.5, 걷기 목표 180 → 162 이상 첫 틱 4 → 0.4 − 0.1 = `0.300`; 뗌 틱 5, 1 미만 첫 틱 7 → `0.200` s, 58 → 63 → 63 = `5.000` cm. `report`는 키 `W`·목표 `speeds.walk` 한 쌍만 낸다(열 이름 `walk_*`). 달리기(Shift) 반응은 V-08b 세션이 함수를 직접 부른다 — 키 이름(SendInput 쪽)이 아직 정해지지 않았다.
     - Offset Root Bone(§9-2 :379, §6-1): 거리 = |root XY − 캡슐 XY|, 보고는 최대·p95(numpy `linear`). yaw 차 = root_yaw − (캡슐 yaw + (−90)), [−180, 180)로 감는다(정렬된 메시는 root_yaw = 캡슐 yaw − 90이라 0). fixture: 거리 0, 0, 1, 2, 3, 4, 2, 0 → 최대 `4.000`, p95 = 3 + 0.65 × (4 − 3) = `3.650`; root_yaw −90, −90, −88, −85, −90, −95, −90, −90(캡슐 yaw 0) → |차| 최대 `5.000`. 감기: 캡슐 −170, root 95 → 95 − (−260) = 355 → −5.
  5. **`report` CLI**: `python -m golmok_tools.locomotion_metrics report <ticks.json>… [--markdown]`. 열(고정 순서): `scene condition ticks capsule_m planted_slip_cm_per_m slip_frames legacy_v11_slip_cm_per_m walk_react_s walk_stop_s walk_stop_cm offset_max_cm offset_p95_cm offset_yaw_max_deg`. 첫 줄은 열 이름, 파일마다 한 줄(명령줄 순서). 기본은 탭 구분, `--markdown`은 `| … |` 표(둘째 줄 `|---|`×13). 실수는 모두 `f"{x:.3f}"`(Python 문자열 형식 — OS와 무관), 없는 값은 `-`, `slip_frames`는 `k/n`, `ticks`는 정수. `TicksError`(틱 파일 형식 오류)는 표준 오류에 `locomotion_metrics: error: <메시지>` 한 줄, 종료 코드 2. argparse 오류도 종료 코드 2이지만 접두어는 argparse의 `python -m golmok_tools.locomotion_metrics: error:`다. 파일이 없거나 읽을 수 없으면 Python 예외 그대로(종료 코드 1) — 이 1차분은 그 경로를 다루지 않는다. fixture의 기대 출력은 펜스 `j24-expected-report-csv`(탭을 쉼표로 바꾼 것 — 문서에 탭을 두지 않으려고)·`j24-expected-report-md`이고, 테스트 `test_report_is_byte_exact`가 바이트 그대로 본다. fixture 값은 셋째 자리 반올림 경계(…5)에 걸리지 않게 골랐다(5.5556, 37.3016, 3.6499999999999995).
  6. **수락 (a) 헤더 대조**: `test_ue_locomotion_math.py`의 `DRIVER`·`HEADER_DIR`·`_planted_command`·`run`을 **가져다 쓴다**(`from test_ue_locomotion_math import DRIVER, HEADER_DIR, _planted_command, run` — 테스트 함수는 가져오지 않으므로 두 번 수집되지 않는다). `driver` 픽스처만 **복사**한다(같은 컴파일러 순서·같은 플래그) — pytest 픽스처를 가져오면 ruff F401/F811과 이름 등록 문제가 생긴다. 대조 사례: 시드 24(유한)·25(10 % 확률로 x·y·z 중 하나를 `nan`/`inf`/`-inf`) 각 40세트, `rel=1e-9, abs=1e-9`; 비유한 고정 사례(:380 → 1.0); `slip` 65쌍(캡슐 0~2 cm 30쌍, 2~500 cm 30쌍, 비유한·경계 5쌍); fixture 두 발이 드라이버로도 1.5·2.0. 컴파일러가 없으면 이 5개(매개변수 포함)가 skip한다 — 이 Mac은 `/usr/bin/clang++`가 있어 돈다(할 일 1이 확인). CI 4행 모두 컴파일러가 있으므로 기대는 행마다 **기준 + 43 passed, skipped 그대로**다(할 일 7). 수락 (b)·(c)는 원자료가 옛 PC에 있어 **"미대조"**로 적는다(통과로 쓰지 않는다).
  7. **비공허 확인(규칙 8·15)**: 펜스 `j24-mutate-sh`가 모듈의 한 줄씩 8가지 변형을 BSD `sed -i ''`로 하나씩 넣고, 새 테스트 파일만 돌려 FAILED 이름을 모은 뒤, 펜스 사본으로 되돌리고 `cmp`한다. 기대 출력은 펜스 `j24-expected-mutations`(줄마다 `diff=2`·`rc=1`·`restored=0`): m1 디딤 허용 2.5 → 3.0, m2 `planted_travel_cm`의 두 틱 조건 삭제, m3 yaw 보정 부호 반전, m4 반응 `>=` → `>`, m5 백분위 `linear` → `lower`, m6 캡슐 최소 1.0 → 0.5 cm, m7 `slip_frames`의 두 틱 조건 삭제, m8 정지 `<` → `<=`. 줄 번호는 펜스 `j24-module-py`의 줄 번호다(펜스를 그대로 복사했으므로 같다 — 스크립트가 처음에 `cmp`로 확인).
  8. **커밋 제목**: v08b §9-3의 `V-08b: tools — …`가 아니라 `J-24: …`로 한다. §9-3 커밋은 드라이버·`locomotion_pure`·장면 정의를 함께 담는 V-08b 세션 몫이고, 이 PR은 그 일부만 먼저 넣는 재환 과제다. 병합 때 영록이 v08b §9-1 표 아래에 "이 함수들은 J-24 PR로 들어왔고, §9-3 커밋은 남은 파일만 담는다"는 메모를 넣는다(재환은 런북을 고치지 않는다).
  9. **GUI 잠금 없음**: UE·패키지 앱·GPU를 쓰지 않는다(Python만). 그래서 GUI 잠금을 잡지 않는다. 시간 수치는 판정에 쓰지 않는다.

```python j24-module-py
"""Locomotion metrics for V-08b / V-15 (pc-verify-v08b.md section 9-2), first slice (J-24).

Pure numpy functions over the tick JSON ``golmok-locomotion-ticks/1`` (section 9-1) and a ``report`` CLI:
``python -m golmok_tools.locomotion_metrics report <ticks.json>... [--markdown]``.

- ``planted_travel_cm`` / ``planted_slip_cm_per_m`` mirror ``PlantedTravelCm`` / ``PlantedSlipCmPerM`` in
  ``unreal/Golmok/Source/Golmok/Animation/GolmokLocomotionMath.h`` (non-finite rules included). Per foot
  bone the floor is its lowest finite z over capsule-on-ground ticks; a tick is planted when the capsule is
  on the ground and z <= floor + 2.5 cm; the horizontal step between two consecutive planted ticks counts.
  The slip is the planted travel of ``foot_l`` + ``foot_r`` per metre of capsule horizontal path, and 0
  when the capsule moved less than 1 cm.
- ``slip_frames``: tick pairs in which a planted foot (same rule) moves faster than 15 cm/s horizontally.
- ``legacy_v11_slip``: the V-11 section 14-5 rule. Per socket (``foot_l``, ``foot_r``, ``ball_l``,
  ``ball_r``) the baseline is the 2nd percentile (numpy ``method="linear"``) of its z over on-ground ticks;
  at each tick from the second on, the sockets planted on that tick alone (on ground, z <= baseline +
  2.5 cm) give their horizontal step from the previous tick, the smallest step is summed, and the sum is
  divided by the capsule path in metres (0 below 1 cm).
- Table B: ``reaction_time_s`` (first press of a key to the first tick with horizontal ``vel`` >= 0.9 x
  target) and ``stop_after_release`` (first release after that press to the first tick below 1 cm/s:
  seconds and capsule horizontal path between those two ticks). No interpolation between ticks.
- Offset Root Bone: ``offset_root_distance_cm`` (|root XY - capsule XY|) and ``offset_yaw_deg``
  (root yaw - (capsule yaw + mesh yaw), mesh yaw -90, wrapped to [-180, 180)).

The meaning of these numbers and any "good" threshold are not decided here.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SCHEMA = "golmok-locomotion-ticks/1"
PLANTED_TOLERANCE_CM = 2.5
MIN_CAPSULE_TRAVEL_CM = 1.0
SLIP_SPEED_CM_S = 15.0
LEGACY_PERCENTILE = 2.0
REACTION_FRACTION = 0.9
STOP_SPEED_CM_S = 1.0
MESH_YAW_DEG = -90.0
FOOT_BONES = ("foot_l", "foot_r")
LEGACY_SOCKETS = ("foot_l", "foot_r", "ball_l", "ball_r")
REQUIRED_BONES = ("root", "foot_l", "foot_r", "ball_l", "ball_r")
SCENE_STRINGS = ("scene", "condition", "pawn_class", "profile", "map")
REPORT_KEY = "W"
REPORT_SPEED = "walk"
COLUMNS = (
    "scene",
    "condition",
    "ticks",
    "capsule_m",
    "planted_slip_cm_per_m",
    "slip_frames",
    "legacy_v11_slip_cm_per_m",
    "walk_react_s",
    "walk_stop_s",
    "walk_stop_cm",
    "offset_max_cm",
    "offset_p95_cm",
    "offset_yaw_max_deg",
)


class TicksError(ValueError):
    """A tick file that does not follow golmok-locomotion-ticks/1."""


@dataclass(frozen=True)
class Scene:
    name: str
    condition: str
    pawn_class: str
    profile: str
    map: str
    speeds: dict[str, float]
    t: np.ndarray
    dt: np.ndarray
    keys: tuple[frozenset[str], ...]
    capsule: np.ndarray
    yaw: np.ndarray
    half_height: np.ndarray
    on_ground: np.ndarray
    vel: np.ndarray
    bones: dict[str, np.ndarray]
    root_yaw: np.ndarray | None


# ---- loader ------------------------------------------------------------------------------------------------


def _need(obj: dict, key: str, where: str, fail):
    if key not in obj:
        fail(f"missing field {where}")
    return obj[key]


def _num(value, where: str, fail) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        fail(f"{where} must be a number")
    if not math.isfinite(value):
        fail(f"non-finite value in {where}")
    return float(value)


def _vec3(value, where: str, fail) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        fail(f"{where} must be a list of 3 numbers")
    return [_num(v, f"{where}[{k}]", fail) for k, v in enumerate(value)]


def load_ticks(path: str | Path) -> Scene:
    path = Path(path)

    def fail(message: str):
        raise TicksError(f"{path.name}: {message}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"not valid JSON (line {exc.lineno})")
    if not isinstance(data, dict):
        fail("top level is not an object")
    schema = _need(data, "schema", "schema", fail)
    if schema != SCHEMA:
        fail(f"schema is {schema!r}, expected {SCHEMA!r}")
    strings = {}
    for key in SCENE_STRINGS:
        value = _need(data, key, key, fail)
        if not isinstance(value, str):
            fail(f"{key} must be a string")
        strings[key] = value
    speeds = _need(data, "speeds", "speeds", fail)
    if not isinstance(speeds, dict):
        fail("speeds must be an object")
    speed_values = {
        k: _num(_need(speeds, k, f"speeds.{k}", fail), f"speeds.{k}", fail) for k in ("walk", "run")
    }
    ticks = _need(data, "ticks", "ticks", fail)
    if not isinstance(ticks, list):
        fail("ticks must be a list")
    if len(ticks) < 2:
        fail(f"scene has {len(ticks)} tick(s), need at least 2")
    has_root_yaw = isinstance(ticks[0], dict) and "root_yaw" in ticks[0]
    t, dt, keys, capsule, yaw, half, ground, vel, root_yaw = [], [], [], [], [], [], [], [], []
    bones: dict[str, list] = {b: [] for b in REQUIRED_BONES}
    for i, tick in enumerate(ticks):
        w = f"ticks[{i}]"
        if not isinstance(tick, dict):
            fail(f"{w} must be an object")
        t.append(_num(_need(tick, "t", f"{w}.t", fail), f"{w}.t", fail))
        if i > 0 and t[i] <= t[i - 1]:
            fail(f"{w}.t is not after ticks[{i - 1}].t")
        dt.append(_num(_need(tick, "dt", f"{w}.dt", fail), f"{w}.dt", fail))
        k = _need(tick, "keys", f"{w}.keys", fail)
        if not isinstance(k, list) or not all(isinstance(s, str) for s in k):
            fail(f"{w}.keys must be a list of strings")
        keys.append(frozenset(k))
        capsule.append(_vec3(_need(tick, "capsule", f"{w}.capsule", fail), f"{w}.capsule", fail))
        yaw.append(_num(_need(tick, "yaw", f"{w}.yaw", fail), f"{w}.yaw", fail))
        half.append(_num(_need(tick, "half_height", f"{w}.half_height", fail), f"{w}.half_height", fail))
        g = _need(tick, "on_ground", f"{w}.on_ground", fail)
        if not isinstance(g, bool):
            fail(f"{w}.on_ground must be true or false")
        ground.append(g)
        vel.append(_vec3(_need(tick, "vel", f"{w}.vel", fail), f"{w}.vel", fail))
        b = _need(tick, "bones", f"{w}.bones", fail)
        if not isinstance(b, dict):
            fail(f"{w}.bones must be an object")
        for bone in REQUIRED_BONES:
            if bone not in b:
                fail(f"{w}.bones has no {bone}")
            bones[bone].append(_vec3(b[bone], f"{w}.bones.{bone}", fail))
        if has_root_yaw:
            root_yaw.append(_num(_need(tick, "root_yaw", f"{w}.root_yaw", fail), f"{w}.root_yaw", fail))
    return Scene(
        name=strings["scene"],
        condition=strings["condition"],
        pawn_class=strings["pawn_class"],
        profile=strings["profile"],
        map=strings["map"],
        speeds=speed_values,
        t=np.array(t),
        dt=np.array(dt),
        keys=tuple(keys),
        capsule=np.array(capsule),
        yaw=np.array(yaw),
        half_height=np.array(half),
        on_ground=np.array(ground, dtype=bool),
        vel=np.array(vel),
        bones={bone: np.array(v) for bone, v in bones.items()},
        root_yaw=np.array(root_yaw) if has_root_yaw else None,
    )


# ---- planted foot (header-identical) -----------------------------------------------------------------------


def _steps_cm(xyz: np.ndarray) -> np.ndarray:
    """Horizontal distance between consecutive samples, sqrt(dx*dx + dy*dy) as in the header."""
    xyz = np.asarray(xyz, dtype=float).reshape(-1, 3)
    with np.errstate(invalid="ignore", over="ignore"):
        dx = np.diff(xyz[:, 0])
        dy = np.diff(xyz[:, 1])
        return np.sqrt(dx * dx + dy * dy)


def planted_mask(z: np.ndarray, on_ground: np.ndarray) -> np.ndarray:
    """Per sample: capsule on the ground, z finite and z <= (lowest finite on-ground z) + 2.5 cm."""
    z = np.asarray(z, dtype=float)
    base = np.asarray(on_ground, dtype=bool) & np.isfinite(z)
    if not base.any():
        return np.zeros(z.shape, dtype=bool)
    floor = z[base].min()
    with np.errstate(invalid="ignore"):
        return base & (z <= floor + PLANTED_TOLERANCE_CM)


def planted_travel_cm(xyz: np.ndarray, on_ground: np.ndarray) -> float:
    """PlantedTravelCm: horizontal travel of one foot bone between consecutive planted samples."""
    xyz = np.asarray(xyz, dtype=float).reshape(-1, 3)
    if len(xyz) < 2:
        return 0.0
    mask = planted_mask(xyz[:, 2], on_ground)
    pair = mask[:-1] & mask[1:]
    step = _steps_cm(xyz)
    keep = pair & np.isfinite(step)
    return float(step[keep].sum())


def planted_slip_cm_per_m(planted_travel_cm_sum: float, capsule_travel_cm: float) -> float:
    """PlantedSlipCmPerM: cm of planted-foot travel per metre of capsule travel; 0 below 1 cm."""
    if (
        not math.isfinite(planted_travel_cm_sum)
        or not math.isfinite(capsule_travel_cm)
        or capsule_travel_cm < MIN_CAPSULE_TRAVEL_CM
    ):
        return 0.0
    return planted_travel_cm_sum / (capsule_travel_cm / 100.0)


def capsule_travel_cm(capsule: np.ndarray) -> float:
    """Horizontal path length of the capsule (sum of the steps between consecutive ticks)."""
    return float(_steps_cm(capsule).sum())


def scene_planted_slip(scene: Scene) -> float:
    travel = sum(planted_travel_cm(scene.bones[b], scene.on_ground) for b in FOOT_BONES)
    return planted_slip_cm_per_m(travel, capsule_travel_cm(scene.capsule))


def slip_frames(scene: Scene) -> tuple[int, int]:
    """(tick pairs with a planted foot faster than 15 cm/s, tick pairs with a planted foot)."""
    dts = np.diff(scene.t)
    slipping = np.zeros(len(dts), dtype=bool)
    planted_any = np.zeros(len(dts), dtype=bool)
    for bone in FOOT_BONES:
        xyz = scene.bones[bone]
        mask = planted_mask(xyz[:, 2], scene.on_ground)
        both = mask[:-1] & mask[1:]
        speed = _steps_cm(xyz) / dts
        planted_any |= both
        slipping |= both & (speed > SLIP_SPEED_CM_S)
    return int(slipping.sum()), int(planted_any.sum())


# ---- V-11 legacy -------------------------------------------------------------------------------------------


def legacy_baseline_cm(z: np.ndarray, on_ground: np.ndarray) -> float | None:
    """2nd percentile (numpy method="linear") of z over on-ground ticks; None without such ticks."""
    z = np.asarray(z, dtype=float)
    g = np.asarray(on_ground, dtype=bool)
    if not g.any():
        return None
    return float(np.percentile(z[g], LEGACY_PERCENTILE, method="linear"))


def legacy_v11_slip(scene: Scene) -> float:
    moves = np.full(len(scene.t) - 1, np.inf)
    for socket in LEGACY_SOCKETS:
        xyz = scene.bones[socket]
        base = legacy_baseline_cm(xyz[:, 2], scene.on_ground)
        if base is None:
            continue
        planted = scene.on_ground & (xyz[:, 2] <= base + PLANTED_TOLERANCE_CM)
        moves = np.minimum(moves, np.where(planted[1:], _steps_cm(xyz), np.inf))
    total = float(moves[np.isfinite(moves)].sum())
    return planted_slip_cm_per_m(total, capsule_travel_cm(scene.capsule))


# ---- table B -----------------------------------------------------------------------------------------------


def horizontal_speed(vel: np.ndarray) -> np.ndarray:
    vel = np.asarray(vel, dtype=float).reshape(-1, 3)
    return np.sqrt(vel[:, 0] * vel[:, 0] + vel[:, 1] * vel[:, 1])


def press_index(keys: Sequence[frozenset[str]], key: str) -> int | None:
    """First tick holding ``key`` whose previous tick did not (tick 0 counts when it holds the key)."""
    for i, held in enumerate(keys):
        if key in held and (i == 0 or key not in keys[i - 1]):
            return i
    return None


def release_index(keys: Sequence[frozenset[str]], key: str, after: int) -> int | None:
    """First tick after ``after`` that does not hold ``key``."""
    for i in range(after + 1, len(keys)):
        if key not in keys[i]:
            return i
    return None


def reaction_time_s(
    t: np.ndarray, speed: np.ndarray, keys: Sequence[frozenset[str]], key: str, target_cm_s: float
) -> float | None:
    k = press_index(keys, key)
    if k is None:
        return None
    hits = np.nonzero(speed[k:] >= REACTION_FRACTION * target_cm_s)[0]
    if len(hits) == 0:
        return None
    return float(t[k + hits[0]] - t[k])


def stop_after_release(
    t: np.ndarray, capsule: np.ndarray, speed: np.ndarray, keys: Sequence[frozenset[str]], key: str
) -> tuple[float, float] | None:
    k = press_index(keys, key)
    if k is None:
        return None
    r = release_index(keys, key, k)
    if r is None:
        return None
    hits = np.nonzero(speed[r:] < STOP_SPEED_CM_S)[0]
    if len(hits) == 0:
        return None
    j = r + int(hits[0])
    return float(t[j] - t[r]), capsule_travel_cm(capsule[r : j + 1])


# ---- Offset Root Bone --------------------------------------------------------------------------------------


def offset_root_distance_cm(capsule: np.ndarray, root: np.ndarray) -> np.ndarray:
    capsule = np.asarray(capsule, dtype=float).reshape(-1, 3)
    root = np.asarray(root, dtype=float).reshape(-1, 3)
    dx = root[:, 0] - capsule[:, 0]
    dy = root[:, 1] - capsule[:, 1]
    return np.sqrt(dx * dx + dy * dy)


def offset_yaw_deg(yaw: np.ndarray, root_yaw: np.ndarray, mesh_yaw_deg: float = MESH_YAW_DEG) -> np.ndarray:
    d = np.asarray(root_yaw, dtype=float) - (np.asarray(yaw, dtype=float) + mesh_yaw_deg)
    return (d + 180.0) % 360.0 - 180.0


# ---- report ------------------------------------------------------------------------------------------------


def _f3(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


def report_row(scene: Scene) -> list[str]:
    speed = horizontal_speed(scene.vel)
    react = reaction_time_s(scene.t, speed, scene.keys, REPORT_KEY, scene.speeds[REPORT_SPEED])
    stop = stop_after_release(scene.t, scene.capsule, speed, scene.keys, REPORT_KEY)
    slipping, planted = slip_frames(scene)
    offset = offset_root_distance_cm(scene.capsule, scene.bones["root"])
    yaw_max = None
    if scene.root_yaw is not None:
        yaw_max = float(np.abs(offset_yaw_deg(scene.yaw, scene.root_yaw)).max())
    return [
        scene.name,
        scene.condition,
        str(len(scene.t)),
        _f3(capsule_travel_cm(scene.capsule) / 100.0),
        _f3(scene_planted_slip(scene)),
        f"{slipping}/{planted}",
        _f3(legacy_v11_slip(scene)),
        _f3(react),
        _f3(None if stop is None else stop[0]),
        _f3(None if stop is None else stop[1]),
        _f3(float(offset.max())),
        _f3(float(np.percentile(offset, 95.0, method="linear"))),
        _f3(yaw_max),
    ]


def format_report(scenes: Sequence[Scene], markdown: bool = False) -> str:
    rows = [report_row(s) for s in scenes]
    if markdown:
        lines = ["| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
        lines += ["| " + " | ".join(r) + " |" for r in rows]
    else:
        lines = ["\t".join(COLUMNS)] + ["\t".join(r) for r in rows]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m golmok_tools.locomotion_metrics", description=__doc__.split("\n")[0]
    )
    sub = p.add_subparsers(dest="command", required=True)
    rep = sub.add_parser("report", help="one row of metrics per tick file")
    rep.add_argument("ticks", nargs="+", type=Path, help="golmok-locomotion-ticks/1 JSON files")
    rep.add_argument("--markdown", action="store_true", help="markdown table instead of tab-separated text")
    args = p.parse_args(argv)
    try:
        scenes = [load_ticks(path) for path in args.ticks]
    except TicksError as exc:
        print(f"locomotion_metrics: error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(format_report(scenes, markdown=args.markdown))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

```python j24-test-py
"""J-24: golmok_tools.locomotion_metrics (pc-verify-v08b.md section 9-2, first slice) on synthetic ticks.

Expected values are closed-form (worked in the docstring of each test). The planted-foot functions are
also compared with GolmokLocomotionMath.h through tools/tests/fixtures/ue/locomotionmath_driver.cpp, built
the same way as test_ue_locomotion_math.py (skipped without g++/clang++/c++ on PATH).
"""

from __future__ import annotations

import json
import math
import random
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from test_ue_locomotion_math import DRIVER, HEADER_DIR, _planted_command, run

from golmok_tools import locomotion_metrics as lm

FIXTURE = Path(__file__).parent / "fixtures/locomotion/ticks_min.json"
TOOLS = Path(__file__).resolve().parents[1]

REPORT_TSV = (
    "scene\tcondition\tticks\tcapsule_m\tplanted_slip_cm_per_m\tslip_frames\tlegacy_v11_slip_cm_per_m\t"
    "walk_react_s\twalk_stop_s\twalk_stop_cm\toffset_max_cm\toffset_p95_cm\toffset_yaw_max_deg\n"
    "S1\tp0\t8\t0.630\t5.556\t1/6\t37.302\t0.300\t0.200\t5.000\t4.000\t3.650\t5.000\n"
)
REPORT_MD = (
    "| scene | condition | ticks | capsule_m | planted_slip_cm_per_m | slip_frames "
    "| legacy_v11_slip_cm_per_m | walk_react_s | walk_stop_s | walk_stop_cm "
    "| offset_max_cm | offset_p95_cm | offset_yaw_max_deg |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    "| S1 | p0 | 8 | 0.630 | 5.556 | 1/6 | 37.302 | 0.300 | 0.200 | 5.000 | 4.000 | 3.650 | 5.000 |\n"
)


def foot(points):
    return np.array(points, dtype=float).reshape(-1, 3)


def scene_from(data: dict, tmp_path: Path, name: str = "scene.json") -> lm.Scene:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return lm.load_ticks(path)


def fixture_data() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


# ---- planted foot ------------------------------------------------------------------------------------------


def test_planted_foot_is_zero():
    """A foot fixed at z 10 for 11 ticks while the capsule moves 100 cm: travel 0, slip 0 cm/m."""
    f = foot([(0, 10, 10)] * 11)
    ground = np.ones(11, dtype=bool)
    assert lm.planted_travel_cm(f, ground) == 0.0
    capsule = foot([(10.0 * i, 0, 92) for i in range(11)])
    assert lm.capsule_travel_cm(capsule) == pytest.approx(100.0, rel=1e-12)
    assert lm.planted_slip_cm_per_m(0.0, 100.0) == 0.0


@pytest.mark.parametrize("rate", [0.03, 0.1])
def test_constant_slip_n_cm_per_m(rate):
    """Both feet planted (z 10) slide `rate` cm per tick while the capsule moves 1 cm per tick for 100 steps:
    each foot travels 100 x rate cm, the capsule 100 cm, so slip = 2 x 100 x rate / 1 m = 200 x rate cm/m."""
    n = 101
    ground = np.ones(n, dtype=bool)
    left = foot([(rate * i, 10, 10) for i in range(n)])
    right = foot([(rate * i, -10, 10) for i in range(n)])
    capsule = foot([(1.0 * i, 0, 92) for i in range(n)])
    travel = lm.planted_travel_cm(left, ground) + lm.planted_travel_cm(right, ground)
    assert travel == pytest.approx(2 * 100 * rate, rel=1e-9)
    assert lm.planted_slip_cm_per_m(travel, lm.capsule_travel_cm(capsule)) == pytest.approx(
        200 * rate, rel=1e-9
    )


def test_lifted_foot_and_airborne_ticks_are_excluded():
    """x moves 1 cm per tick. Tick 2 is lifted (z 20) and ticks 4-5 are airborne (z 0 there does not set the
    floor, which stays 10). Planted pairs: 0-1 and 6-7 only (2-3 has a lifted tick, 3-4/4-5/5-6 an airborne
    one), so the travel is 2 cm."""
    f = foot([(0, 0, 10), (1, 0, 10), (2, 0, 20), (3, 0, 10), (4, 0, 0), (5, 0, 0), (6, 0, 10), (7, 0, 10)])
    ground = np.array([True, True, True, True, False, False, True, True])
    assert lm.planted_mask(f[:, 2], ground).tolist() == [True, True, False, True, False, False, True, True]
    assert lm.planted_travel_cm(f, ground) == pytest.approx(2.0, rel=1e-12)
    assert lm.planted_travel_cm(f, np.zeros(8, dtype=bool)) == 0.0


def test_planted_boundary_12_6_is_not_planted():
    """test_ue_locomotion_math.py:316-321: floor 10, 12.5 is planted, 12.6 > 10 + 2.5 is not: 2.0 + 0.5."""
    samples = [
        (0, 0, 10),
        (1, 0, 10.5),
        (2, 0, 11),
        (20, 0, 30),
        (40, 0, 12.4),
        (40.5, 0, 12.5),
        (41, 0, 12.6),
    ]
    assert lm.planted_travel_cm(foot(samples), np.ones(7, dtype=bool)) == pytest.approx(2.5, rel=1e-12)


def test_capsule_below_one_cm_gives_zero_slip():
    """5 cm of planted travel: 0 when the capsule moved 0.99 cm, 5 / 0.01 m = 500 cm/m at exactly 1 cm."""
    assert lm.planted_slip_cm_per_m(5.0, 0.99) == 0.0
    assert lm.planted_slip_cm_per_m(5.0, 1.0) == pytest.approx(500.0, rel=1e-12)
    assert lm.planted_slip_cm_per_m(math.nan, 200.0) == 0.0
    assert lm.planted_slip_cm_per_m(30.0, math.inf) == 0.0


def test_slip_frames_counts_pairs_faster_than_15_cm_s():
    """Fixture: planted foot pairs at ticks 1, 2, 3, 7 (foot_l) and 4, 5 (foot_r) = 6; only tick 4 (foot_r
    2 cm in 0.1 s = 20 cm/s) is faster than 15 cm/s (foot_l 1 cm in 0.1 s = 10 cm/s is not)."""
    assert lm.slip_frames(lm.load_ticks(FIXTURE)) == (1, 6)


# ---- V-11 legacy -------------------------------------------------------------------------------------------


def test_legacy_baseline_is_numpy_linear_p2():
    """z = 0..25 (26 values): rank 0.02 x 25 = 0.5, linear interpolation 0.5 (lower/nearest would give 0)."""
    z = np.arange(26, dtype=float)
    assert lm.legacy_baseline_cm(z, np.ones(26, dtype=bool)) == pytest.approx(0.5, rel=1e-12)
    assert lm.legacy_baseline_cm(z, np.zeros(26, dtype=bool)) is None


def test_legacy_takes_the_smallest_planted_socket_step(tmp_path):
    """Fixture with ball_l moved 4 cm less than foot_l on tick 6 (step 16 instead of 20): legacy sum
    23.5 - 20 + 16 = 19.5 cm over 0.63 m = 30.952... cm/m; the unified slip stays 3.5 / 0.63."""
    data = fixture_data()
    data["ticks"][6]["bones"]["ball_l"][0] -= 4
    data["ticks"][7]["bones"]["ball_l"][0] -= 4
    scene = scene_from(data, tmp_path)
    assert lm.legacy_v11_slip(scene) == pytest.approx(19.5 / 0.63, rel=1e-9)
    assert lm.scene_planted_slip(scene) == pytest.approx(3.5 / 0.63, rel=1e-9)


def test_legacy_counts_a_tick_planted_alone():
    """Fixture: legacy = (0 + 1 + 0 + 2 + 0 + 20 + 0.5) / 0.63 = 37.30...; tick 6 (foot_l lands 20 cm ahead)
    counts in the legacy rule (planted on that tick alone) but not in the unified one (both ticks)."""
    scene = lm.load_ticks(FIXTURE)
    assert lm.legacy_v11_slip(scene) == pytest.approx(23.5 / 0.63, rel=1e-9)
    assert lm.scene_planted_slip(scene) == pytest.approx(3.5 / 0.63, rel=1e-9)


# ---- table B -----------------------------------------------------------------------------------------------


def test_reaction_reaches_exactly_0_9_of_target():
    """Press on tick 1 (t 0.1), target 180 cm/s, threshold 162: 161.99 on tick 2 is not enough, exactly 162 on
    tick 3 is (>=), so 0.3 - 0.1 = 0.2 s. Without the press or without reaching 162: None."""
    t = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
    speed = np.array([0.0, 0.0, 161.99, 162.0, 180.0])
    keys = (frozenset(), frozenset({"W"}), frozenset({"W"}), frozenset({"W"}), frozenset({"W"}))
    assert lm.reaction_time_s(t, speed, keys, "W", 180.0) == pytest.approx(0.2, rel=1e-9)
    assert lm.reaction_time_s(t, speed, keys, "LeftShift", 180.0) is None
    assert lm.reaction_time_s(t, speed, keys, "W", 500.0) is None


def test_stop_time_and_distance_after_release():
    """Release on tick 2 (t 0.2); speed 0.99 cm/s first on tick 4 (t 0.4): 0.2 s and the capsule path from
    tick 2 to tick 4, 3 + 4 = 7 cm (the step into tick 2 does not count)."""
    t = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5])
    capsule = foot([(0, 0, 92), (10, 0, 92), (20, 0, 92), (23, 0, 92), (27, 0, 92), (27, 0, 92)])
    speed = np.array([0.0, 100.0, 50.0, 1.0, 0.99, 0.0])
    keys = (frozenset({"W"}), frozenset({"W"}), frozenset(), frozenset(), frozenset(), frozenset())
    stop = lm.stop_after_release(t, capsule, speed, keys, "W")
    assert stop is not None
    assert stop[0] == pytest.approx(0.2, rel=1e-9)
    assert stop[1] == pytest.approx(7.0, rel=1e-12)
    held = tuple(frozenset({"W"}) for _ in range(6))
    assert lm.stop_after_release(t, capsule, speed, held, "W") is None


# ---- Offset Root Bone --------------------------------------------------------------------------------------


def test_offset_root_bone_distance_and_yaw_correction():
    """Root 3-4-5 cm from the capsule. Yaw: root = capsule - 90 is 0; +3 and +5 read 3 and 5; capsule -170
    with root 95 is 95 - (-260) = 355, wrapped to -5."""
    capsule = foot([(0, 0, 92), (10, 0, 92)])
    root = foot([(3, 4, 0), (10, 0, 0)])
    assert lm.offset_root_distance_cm(capsule, root).tolist() == [5.0, 0.0]
    yaw = np.array([0.0, 0.0, 179.0, -170.0])
    root_yaw = np.array([-90.0, -87.0, 94.0, 95.0])
    assert lm.offset_yaw_deg(yaw, root_yaw) == pytest.approx([0.0, 3.0, 5.0, -5.0], abs=1e-12)


# ---- loader errors (rule 8: each message triggered once) ---------------------------------------------------


def _drop(key):
    def edit(d):
        del d[key]

    return edit


LOADER_CASES = [
    ("missing-schema", _drop("schema"), "missing field schema"),
    ("schema", lambda d: d.update(schema="golmok-locomotion-ticks/2"),
     "schema is 'golmok-locomotion-ticks/2', expected 'golmok-locomotion-ticks/1'"),
    ("scene", _drop("scene"), "missing field scene"),
    ("map-type", lambda d: d.update(map=3), "map must be a string"),
    ("speeds-type", lambda d: d.update(speeds=[180, 500]), "speeds must be an object"),
    ("speeds-walk", lambda d: d["speeds"].pop("walk"), "missing field speeds.walk"),
    ("ticks-type", lambda d: d.update(ticks={}), "ticks must be a list"),
    ("one-tick", lambda d: d.update(ticks=d["ticks"][:1]), "scene has 1 tick(s), need at least 2"),
    ("tick-type", lambda d: d["ticks"].__setitem__(2, []), "ticks[2] must be an object"),
    ("tick-field", lambda d: d["ticks"][2].pop("vel"), "missing field ticks[2].vel"),
    ("non-finite", lambda d: d["ticks"][3]["capsule"].__setitem__(1, math.nan),
     "non-finite value in ticks[3].capsule[1]"),
    ("number-type", lambda d: d["ticks"][1].update(yaw="0"), "ticks[1].yaw must be a number"),
    ("vec-length", lambda d: d["ticks"][1].update(vel=[0, 0]), "ticks[1].vel must be a list of 3 numbers"),
    ("t-order", lambda d: d["ticks"][4].update(t=0.3), "ticks[4].t is not after ticks[3].t"),
    ("keys-type", lambda d: d["ticks"][0].update(keys="W"), "ticks[0].keys must be a list of strings"),
    ("on-ground", lambda d: d["ticks"][5].update(on_ground=1), "ticks[5].on_ground must be true or false"),
    ("bones-type", lambda d: d["ticks"][3].update(bones=[]), "ticks[3].bones must be an object"),
    ("missing-bone", lambda d: d["ticks"][6]["bones"].pop("ball_r"), "ticks[6].bones has no ball_r"),
    ("root-yaw", lambda d: d["ticks"][7].pop("root_yaw"), "missing field ticks[7].root_yaw"),
]  # fmt: skip


@pytest.mark.parametrize(("case", "edit", "message"), LOADER_CASES, ids=[c[0] for c in LOADER_CASES])
def test_loader_error_messages(tmp_path, case, edit, message):
    data = fixture_data()
    edit(data)
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(lm.TicksError) as info:
        lm.load_ticks(path)
    assert str(info.value) == f"bad.json: {message}"


def test_loader_rejects_non_object_and_bad_json(tmp_path):
    path = tmp_path / "list.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(lm.TicksError, match=r"^list\.json: top level is not an object$"):
        lm.load_ticks(path)
    path.write_text("{\n  nope", encoding="utf-8")
    with pytest.raises(lm.TicksError, match=r"^list\.json: not valid JSON \(line 2\)$"):
        lm.load_ticks(path)


def test_loader_reads_the_fixture():
    scene = lm.load_ticks(FIXTURE)
    assert (scene.name, scene.condition, scene.pawn_class, scene.profile) == ("S1", "p0", "BP_V08b_P0", "p0")
    assert scene.speeds == {"walk": 180.0, "run": 500.0}
    assert scene.capsule.shape == (8, 3) and scene.bones["ball_r"].shape == (8, 3)
    assert scene.keys[1] == frozenset({"W"}) and scene.root_yaw is not None


def test_root_yaw_is_optional(tmp_path):
    data = fixture_data()
    for tick in data["ticks"]:
        del tick["root_yaw"]
    scene = scene_from(data, tmp_path)
    assert scene.root_yaw is None
    assert lm.report_row(scene)[-1] == "-"


# ---- report ------------------------------------------------------------------------------------------------


def test_report_is_byte_exact(capsys):
    assert lm.main(["report", str(FIXTURE)]) == 0
    assert capsys.readouterr().out == REPORT_TSV
    assert lm.main(["report", "--markdown", str(FIXTURE)]) == 0
    assert capsys.readouterr().out == REPORT_MD


def test_report_runs_as_module_with_two_files(tmp_path):
    other = tmp_path / "ticks_b.json"
    data = fixture_data()
    data["scene"] = "S2"
    other.write_text(json.dumps(data), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "golmok_tools.locomotion_metrics", "report", str(FIXTURE), str(other)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=TOOLS,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    second = REPORT_TSV.splitlines()[1].replace("S1\t", "S2\t", 1)
    assert result.stdout == REPORT_TSV + second + "\n"


def test_report_error_exit_code(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    data = fixture_data()
    data["schema"] = "x"
    bad.write_text(json.dumps(data), encoding="utf-8")
    assert lm.main(["report", str(FIXTURE), str(bad)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "locomotion_metrics: error: bad.json: schema is 'x', expected 'golmok-locomotion-ticks/1'\n"
    )


# ---- acceptance (a): the header through the C++ driver -----------------------------------------------------


@pytest.fixture(scope="module")
def driver(tmp_path_factory):
    # Same build as test_ue_locomotion_math.py's driver fixture (copied: a pytest fixture is not imported).
    compiler = next((p for name in ("g++", "clang++", "c++") if (p := shutil.which(name))), None)
    if not compiler:
        pytest.skip("no g++/clang++ on PATH")
    output = tmp_path_factory.mktemp("locomotionmetrics") / (
        "driver.exe" if sys.platform == "win32" else "driver"
    )
    result = subprocess.run(
        [compiler, "-std=c++17", "-ffp-contract=off", "-Wall", "-Wextra", "-Werror", "-pedantic", "-Wshadow",
         f"-I{HEADER_DIR}", str(DRIVER), "-o", str(output)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )  # fmt: skip
    assert result.returncode == 0 and not result.stderr.strip(), result.stdout + result.stderr
    return output


SPECIAL = (math.nan, math.inf, -math.inf)


def _random_samples(rng: random.Random, special: bool):
    samples = []
    for _ in range(rng.randint(0, 60)):
        s = [rng.uniform(-50, 50), rng.uniform(-50, 50), rng.uniform(0, 8), rng.random() > 0.1]
        if special and rng.random() < 0.1:
            s[rng.randrange(3)] = rng.choice(SPECIAL)
        samples.append(tuple(s))
    return samples


def _python_planted(samples) -> float:
    xyz = np.array([s[:3] for s in samples], dtype=float).reshape(-1, 3)
    return lm.planted_travel_cm(xyz, np.array([s[3] for s in samples], dtype=bool))


@pytest.mark.parametrize("special", [False, True], ids=["finite", "non-finite"])
def test_planted_travel_matches_header(driver, special):
    rng = random.Random(24 if not special else 25)
    sets = [_random_samples(rng, special) for _ in range(40)]
    lines = run(driver, [_planted_command(s) for s in sets])
    for samples, line in zip(sets, lines, strict=True):
        assert _python_planted(samples) == pytest.approx(float(line[0]), rel=1e-9, abs=1e-9)
    if special:
        assert sum(any(not math.isfinite(v) for s in x for v in s[:3]) for x in sets) >= 10


def test_planted_non_finite_case_matches_header(driver):
    """test_ue_locomotion_math.py:380: a nan height is neither floor nor planted, a nan x drops its steps."""
    planted = [
        (0, 0, math.nan, True),
        (1, 0, 10, True),
        (2, 0, 10, True),
        (math.nan, 0, 10, True),
        (4, 0, 10, True),
    ]
    (line,) = run(driver, [_planted_command(planted)])
    assert float(line[0]) == _python_planted(planted) == 1.0


def test_planted_slip_matches_header(driver):
    rng = random.Random(26)
    pairs = [(rng.uniform(0, 50), rng.uniform(0, 2)) for _ in range(30)] + [
        (rng.uniform(0, 50), rng.uniform(2, 500)) for _ in range(30)
    ]
    pairs += [(math.nan, 200.0), (30.0, math.inf), (math.inf, 200.0), (5.0, 1.0), (5.0, 0.99)]
    lines = run(driver, [f"slip {a!r} {b!r}" for a, b in pairs])
    for (a, b), line in zip(pairs, lines, strict=True):
        assert lm.planted_slip_cm_per_m(a, b) == pytest.approx(float(line[0]), rel=1e-9, abs=1e-9)


def test_scene_slip_uses_the_header_rule_per_foot(driver):
    """The fixture's two foot bones through the driver: 1.5 + 2.0 = 3.5 cm, as scene_planted_slip uses."""
    scene = lm.load_ticks(FIXTURE)
    commands = []
    for bone in lm.FOOT_BONES:
        xyz = scene.bones[bone]
        commands.append(
            _planted_command([(*p, g) for p, g in zip(xyz.tolist(), scene.on_ground.tolist(), strict=True)])
        )
    left, right = (float(v[0]) for v in run(driver, commands))
    assert (left, right) == (pytest.approx(1.5, rel=1e-12), pytest.approx(2.0, rel=1e-12))
    assert lm.scene_planted_slip(scene) == pytest.approx((left + right) / 0.63, rel=1e-9)
```

```json j24-fixture-json
{
  "schema": "golmok-locomotion-ticks/1",
  "scene": "S1",
  "condition": "p0",
  "pawn_class": "BP_V08b_P0",
  "profile": "p0",
  "speeds": {"walk": 180, "run": 500},
  "map": "/Game/Golmok/Maps/L_Dev",
  "ticks": [
    {"t": 0.0, "dt": 0.1, "keys": [], "capsule": [0, 0, 92], "yaw": 0, "half_height": 92, "on_ground": true, "vel": [0, 0, 0], "bones": {"root": [0, 0, 0], "foot_l": [0, 10, 10], "foot_r": [0, -10, 10], "ball_l": [15, 10, 5], "ball_r": [15, -10, 5]}, "root_yaw": -90},
    {"t": 0.1, "dt": 0.1, "keys": ["W"], "capsule": [0, 0, 92], "yaw": 0, "half_height": 92, "on_ground": true, "vel": [0, 0, 0], "bones": {"root": [0, 0, 0], "foot_l": [0, 10, 10], "foot_r": [5, -10, 20], "ball_l": [15, 10, 5], "ball_r": [20, -10, 15]}, "root_yaw": -90},
    {"t": 0.2, "dt": 0.1, "keys": ["W"], "capsule": [10, 0, 92], "yaw": 0, "half_height": 92, "on_ground": true, "vel": [100, 0, 0], "bones": {"root": [11, 0, 0], "foot_l": [1, 10, 10.5], "foot_r": [20, -10, 22], "ball_l": [16, 10, 5.5], "ball_r": [35, -10, 17]}, "root_yaw": -88},
    {"t": 0.3, "dt": 0.1, "keys": ["W"], "capsule": [25, 0, 92], "yaw": 0, "half_height": 92, "on_ground": true, "vel": [150, 0, 0], "bones": {"root": [27, 0, 0], "foot_l": [1, 10, 10], "foot_r": [30, -10, 11], "ball_l": [16, 10, 5], "ball_r": [45, -10, 6]}, "root_yaw": -85},
    {"t": 0.4, "dt": 0.1, "keys": ["W"], "capsule": [43, 0, 92], "yaw": 0, "half_height": 92, "on_ground": true, "vel": [180, 0, 0], "bones": {"root": [46, 0, 0], "foot_l": [20, 10, 20], "foot_r": [32, -10, 10], "ball_l": [35, 10, 15], "ball_r": [47, -10, 5]}, "root_yaw": -90},
    {"t": 0.5, "dt": 0.1, "keys": [], "capsule": [58, 0, 92], "yaw": 0, "half_height": 92, "on_ground": true, "vel": [150, 0, 0], "bones": {"root": [62, 0, 0], "foot_l": [40, 10, 25], "foot_r": [32, -10, 10], "ball_l": [55, 10, 20], "ball_r": [47, -10, 5]}, "root_yaw": -95},
    {"t": 0.6, "dt": 0.1, "keys": [], "capsule": [63, 0, 92], "yaw": 0, "half_height": 92, "on_ground": true, "vel": [50, 0, 0], "bones": {"root": [65, 0, 0], "foot_l": [60, 10, 12], "foot_r": [40, -10, 18], "ball_l": [75, 10, 7], "ball_r": [55, -10, 13]}, "root_yaw": -90},
    {"t": 0.7, "dt": 0.1, "keys": [], "capsule": [63, 0, 92], "yaw": 0, "half_height": 92, "on_ground": true, "vel": [0.5, 0, 0], "bones": {"root": [63, 0, 0], "foot_l": [60.5, 10, 10], "foot_r": [60, -10, 24], "ball_l": [75.5, 10, 5], "ball_r": [75, -10, 19]}, "root_yaw": -90}
  ]
}
```

```sh j24-mutate-sh
#!/bin/sh
# J-24: eight one-line mutations of locomotion_metrics.py, one at a time, each restored from the fence copy.
# usage: sh j24_mutate.sh <W> <E>   ($E/locomotion_metrics.py is the copy extracted from the task fence)
W=$1
E=$2
M="$W/tools/golmok_tools/locomotion_metrics.py"
if ! cmp -s "$E/locomotion_metrics.py" "$M"; then echo "j24_mutate: module differs from the fence copy" >&2; exit 3; fi
m() {
  sed -i '' "$2" "$M"
  c=$(diff "$E/locomotion_metrics.py" "$M" | grep -c '^[<>]')
  (cd "$W/tools" && "$W/tools/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_locomotion_metrics.py) > "$E/m$1.log" 2>&1
  rc=$?
  cp "$E/locomotion_metrics.py" "$M"
  cmp -s "$E/locomotion_metrics.py" "$M"
  echo "m$1 diff=$c rc=$rc restored=$?"
  grep '^FAILED' "$E/m$1.log" | sed -E 's/ - .*//'
}
m 1 '40s/= 2\.5$/= 3.0/'
m 2 '230s/mask\[:-1\] & mask\[1:\]/mask[1:]/'
m 3 '361s/+ mesh_yaw_deg)/- mesh_yaw_deg)/'
m 4 '327s/>= REACTION_FRACTION/> REACTION_FRACTION/'
m 5 '281s/method="linear"/method="lower"/'
m 6 '41s/= 1\.0$/= 0.5/'
m 7 '265s/both = mask\[:-1\] & mask\[1:\]/both = mask[1:]/'
m 8 '342s/< STOP_SPEED_CM_S/<= STOP_SPEED_CM_S/'
```

```sh j24-ci-sh
#!/bin/sh
# J-24: one "row passed skipped" line per CI python row of a finished run, sorted. usage: sh j24_ci.sh <run id>
gh run view "$1" --log |
  grep -E '^python \([^)]*\)[[:space:]]+pytest[[:space:]].* [0-9]+ passed' |
  sed -E 's/^python \(([^)]*)\)[[:space:]]+pytest[[:space:]].* ([0-9]+) passed, ([0-9]+) skipped.*$/\1 \2 \3/' |
  tr -d ',' | LC_ALL=C sort
```

```text j24-expected-mutations
m1 diff=2 rc=1 restored=0
FAILED tests/test_locomotion_metrics.py::test_planted_boundary_12_6_is_not_planted
FAILED tests/test_locomotion_metrics.py::test_planted_travel_matches_header[finite]
FAILED tests/test_locomotion_metrics.py::test_planted_travel_matches_header[non-finite]
m2 diff=2 rc=1 restored=0
FAILED tests/test_locomotion_metrics.py::test_lifted_foot_and_airborne_ticks_are_excluded
FAILED tests/test_locomotion_metrics.py::test_planted_boundary_12_6_is_not_planted
FAILED tests/test_locomotion_metrics.py::test_legacy_takes_the_smallest_planted_socket_step
FAILED tests/test_locomotion_metrics.py::test_legacy_counts_a_tick_planted_alone
FAILED tests/test_locomotion_metrics.py::test_report_is_byte_exact
FAILED tests/test_locomotion_metrics.py::test_report_runs_as_module_with_two_files
FAILED tests/test_locomotion_metrics.py::test_planted_travel_matches_header[finite]
FAILED tests/test_locomotion_metrics.py::test_planted_travel_matches_header[non-finite]
FAILED tests/test_locomotion_metrics.py::test_planted_non_finite_case_matches_header
FAILED tests/test_locomotion_metrics.py::test_scene_slip_uses_the_header_rule_per_foot
m3 diff=2 rc=1 restored=0
FAILED tests/test_locomotion_metrics.py::test_offset_root_bone_distance_and_yaw_correction
FAILED tests/test_locomotion_metrics.py::test_report_is_byte_exact
FAILED tests/test_locomotion_metrics.py::test_report_runs_as_module_with_two_files
m4 diff=2 rc=1 restored=0
FAILED tests/test_locomotion_metrics.py::test_reaction_reaches_exactly_0_9_of_target
m5 diff=2 rc=1 restored=0
FAILED tests/test_locomotion_metrics.py::test_legacy_baseline_is_numpy_linear_p2
m6 diff=2 rc=1 restored=0
FAILED tests/test_locomotion_metrics.py::test_capsule_below_one_cm_gives_zero_slip
FAILED tests/test_locomotion_metrics.py::test_planted_slip_matches_header
m7 diff=2 rc=1 restored=0
FAILED tests/test_locomotion_metrics.py::test_slip_frames_counts_pairs_faster_than_15_cm_s
FAILED tests/test_locomotion_metrics.py::test_report_is_byte_exact
FAILED tests/test_locomotion_metrics.py::test_report_runs_as_module_with_two_files
m8 diff=2 rc=1 restored=0
FAILED tests/test_locomotion_metrics.py::test_stop_time_and_distance_after_release
```

```text j24-expected-report-csv
scene,condition,ticks,capsule_m,planted_slip_cm_per_m,slip_frames,legacy_v11_slip_cm_per_m,walk_react_s,walk_stop_s,walk_stop_cm,offset_max_cm,offset_p95_cm,offset_yaw_max_deg
S1,p0,8,0.630,5.556,1/6,37.302,0.300,0.200,5.000,4.000,3.650,5.000
```

```text j24-expected-report-md
| scene | condition | ticks | capsule_m | planted_slip_cm_per_m | slip_frames | legacy_v11_slip_cm_per_m | walk_react_s | walk_stop_s | walk_stop_cm | offset_max_cm | offset_p95_cm | offset_yaw_max_deg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | p0 | 8 | 0.630 | 5.556 | 1/6 | 37.302 | 0.300 | 0.200 | 5.000 | 4.000 | 3.650 | 5.000 |
```

```text j24-unverified-md
- 수락 (b) 미대조: V-08 원자료(옛 PC `C:\UE\v08_recordings\scenes\`)가 이 Mac에 없어 표 A ±0.1 대조를 하지 않았다.
- 수락 (c) 미대조: V-11 원자료가 없어 `legacy_v11_slip`을 V-11 §14-5 표와 대조하지 않았다. V-11의 발목·앞꿈치 소켓을 `foot_l`·`foot_r`·`ball_l`·`ball_r` 뼈로, 디딤을 그 틱 하나로 본 해석이 V-11 스크립트와 같은지는 [미확인]이다.
- 범위 밖(J-24b): `stair_contact`, 돌아서기 시간, 벽 최소 거리, 관통 근사, Offset 복귀 시간, `blind`·`unblind`.
- 틱 기록기(`locomotion_pure.py`)가 아직 없어 실제 PIE 틱 파일로는 돌리지 않았다. 선택 필드 `root_yaw`는 이 모듈이 정한 것이다.
```

- **명령 공통**: 셸 변수는 Bash 호출 사이에 남지 않는다. 그래서 **모든 명령은 `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/jaehwan/J-24";`로 시작하고**, 그 뒤는 `cd "$W" &&`·`cd "$W/tools" &&`·`git -C "$W"`·`"$E/…"` 절대 경로로 시작한다(상시 규칙). 아래 명령에는 이 앞머리를 적지 않았다. 돌린 명령 원문은 `"$E/commands.txt"`에 한 줄씩 `printf '%s\n' '…' >> "$E/commands.txt"`로 더한다(규칙 10·19). 각 단계의 "기대"와 다르면 **멈춤 조건**을 본다. 할 일 2의 기준선 `pytest`, 할 일 5의 변형 스크립트, 할 일 6의 게이트, 할 일 7의 `gh pr checks --watch`는 **항상** 하네스의 백그라운드 실행으로 돌리고, 그 명령이 쓰는 `.rc` 파일(`gh pr checks --watch`는 `checks-watch.log`의 `exit=` 줄)이 생길 때까지 기다린다(명령은 바꾸지 않는다). 그 밖의 명령은 앞쪽(foreground)으로 돌린다. `git fetch`·`git push`·`gh pr list`·`gh pr create`·`gh pr view`·`gh pr edit`·`gh run list`·`gh run view`(`j24_ci.sh` 안 포함)는 아래에 적힌 그대로 쓴다(`timeout`을 더하거나 빼지 않는다 — 점검표 규칙 5 줄에는 timeout을 붙인 명령과 붙이지 않은 이 명령들을 이름으로 나눠 적는다. 2026-11-28 문서 9: 그 줄의 수는 상시 규칙 "PR 본문 공통" 3의 감사 `timeout-audit.log`에서 옮긴다. CI 표 명령 `gh pr checks`에는 문서 9에서 `/usr/bin/timeout 120`을 붙였다). GUI 잠금은 쓰지 않는다(설계 9).
- **할 일**:
  1. **준비**: `mkdir -p "$E" && git -C "$W" status --porcelain > "$E/status-before.log"; grep -c -v '^?? ' "$E/status-before.log" > "$E/status-before-tracked.log"` — 기대 `0`(추적 파일 변경이 있으면 멈춘다; `??` 줄은 그대로 둔다). `git -C "$W" fetch origin && git -C "$W" switch -c local/jaehwan-j24-locomotion-metrics origin/main > "$E/switch.log" 2>&1; echo $? > "$E/switch.rc"` — 기대 `0`. `git -C "$W" rev-parse --short HEAD > "$E/sha.log"; git -C "$W" rev-parse HEAD origin/main | uniq | wc -l | tr -d ' ' > "$E/sha-same.log"` — 기대 `1`. `git -C "$W" show origin/main:docs/plan/jaehwan-tasks.md > "$E/tasks-main.md"; git -C "$W" rev-parse origin/main > "$E/main-rev.log"; { awk '/^#### J-24 /{f=1} /^#### J-25/{f=0} f' "$E/tasks-main.md"; awk '/^### PR 본문 공통\(모든 과제\)$/{f=1} /^## 리뷰·병합 절차$/{f=0} f' "$E/tasks-main.md"; } > "$E/task.txt"`(규칙 14·17 c, 상시 규칙 "PR 본문 공통" 1) — 기대 `head -1 "$E/task.txt"`가 `#### J-24 `로 시작, `grep -c -x '### PR 본문 공통(모든 과제)' "$E/task.txt"` `1`. 펜스 추출(손으로 옮기지 않는다): `printf '%s\n' "j24-module-py locomotion_metrics.py" "j24-test-py test_locomotion_metrics.py" "j24-fixture-json ticks_min.json" "j24-mutate-sh j24_mutate.sh" "j24-ci-sh j24_ci.sh" "j24-expected-mutations expected-mutations.txt" "j24-expected-report-csv expected-report.csv" "j24-expected-report-md expected-report.md" "j24-unverified-md unverified.md" "common-ph-awk ph.awk" | while read -r n f; do awk -v n="$n" 'BEGIN {b = sprintf("%c%c%c", 96, 96, 96)} $0 == b && x {x=0} x {print} $0 ~ ("^" b "[a-z]+ " n "$") {x=1}' "$E/task.txt" > "$E/$f"; done; cd "$E" && wc -l locomotion_metrics.py test_locomotion_metrics.py ticks_min.json j24_mutate.sh j24_ci.sh expected-mutations.txt expected-report.csv expected-report.md unverified.md ph.awk > "$E/extract-wc.log"`(2026-11-28 문서 9: 백틱 세 개를 `sprintf`로 만드는 꼴로 바꿨다 — 뽑는 결과는 같다) — 기대(앞 숫자, 순서대로): `427`, `396`, `19`, `25`, `6`, `32`, `2`, `3`, `4`, `37`, 끝 줄 `951 total`. 겹침: `cd "$W" && gh pr list --state open --json number,headRefName,files --jq '.[]|select(any(.files[]; .path|test("^tools/(golmok_tools/locomotion_metrics\\.py|tests/test_locomotion_metrics\\.py|tests/fixtures/locomotion/)")))|"\(.number) \(.headRefName)"' > "$E/overlap.log" 2>&1` — 기대 빈 파일. 새 파일 자리가 비었는지: `cd "$W" && for p in tools/golmok_tools/locomotion_metrics.py tools/tests/test_locomotion_metrics.py tools/tests/fixtures/locomotion; do [ -e "$p" ] && echo "exists $p"; done > "$E/absent.log"` — 기대 빈 파일. 컴파일러: `{ command -v g++; command -v clang++; command -v c++; } > "$E/compilers.log" 2>&1; wc -l < "$E/compilers.log" | tr -d ' ' > "$E/compilers-count.log"` — 기대 `1` 이상(0이면 헤더 대조가 skip된다 — 멈춤). numpy: `"$W/tools/.venv/bin/python" -c "import numpy; v = tuple(int(x) for x in numpy.__version__.split('.')[:2]); print('numpy-ok' if v >= (1, 22) else 'numpy-old', numpy.__version__)" > "$E/numpy.log" 2>&1` — 기대 첫 낱말 `numpy-ok`.
  2. **기준선**(하네스 백그라운드, 새 파일을 넣기 전): `cd "$W/tools" && source .venv/bin/activate && /usr/bin/timeout 1800 pytest -q > "$E/base-pytest.log" 2>&1; echo $? > "$E/base-pytest.rc"` — 기대 `0`(124 = 시간 초과, 다시 돌리지 않고 멈춤). 세기: `grep -E '^[0-9]+ passed, [0-9]+ skipped' "$E/base-pytest.log" | sed -E 's/^([0-9]+) passed, ([0-9]+) skipped.*/\1 \2/' > "$E/base-count.log"` — 기대 `grep -c -x '[0-9][0-9]* [0-9][0-9]*' "$E/base-count.log"` `1`, `wc -l < "$E/base-count.log" | tr -d ' '` `1`(2026-11-28 `366e118`의 이 Mac에서는 `1940 3`).
  3. **파일 넣기**: `cd "$W" && mkdir -p tools/tests/fixtures/locomotion && cp "$E/locomotion_metrics.py" tools/golmok_tools/locomotion_metrics.py && cp "$E/test_locomotion_metrics.py" tools/tests/test_locomotion_metrics.py && cp "$E/ticks_min.json" tools/tests/fixtures/locomotion/ticks_min.json; echo $? > "$E/copy.rc"` — 기대 `0`. `cd "$W" && cmp "$E/locomotion_metrics.py" tools/golmok_tools/locomotion_metrics.py && cmp "$E/test_locomotion_metrics.py" tools/tests/test_locomotion_metrics.py && cmp "$E/ticks_min.json" tools/tests/fixtures/locomotion/ticks_min.json; echo "exit=$?" > "$E/cmp.log"` — 기대 `exit=0` 한 줄. `git -C "$W" status --porcelain > "$E/status-files.log"; grep -v -x -F -f "$E/status-before.log" "$E/status-files.log" > "$E/status-new.log"; printf '%s\n' '?? tools/golmok_tools/locomotion_metrics.py' '?? tools/tests/fixtures/locomotion/' '?? tools/tests/test_locomotion_metrics.py' | diff - "$E/status-new.log" > "$E/status-new.diff"; echo "exit=$?" >> "$E/status-new.diff"` — 기대 `exit=0` 한 줄(`status-before.log`가 비었으면 `-f`가 아무 줄도 빼지 않으므로 같은 기대가 그대로 맞다).
  4. **새 테스트·CLI**: `cd "$W/tools" && /usr/bin/timeout 600 .venv/bin/python -m pytest -q -rs -p no:cacheprovider tests/test_locomotion_metrics.py > "$E/new-tests.log" 2>&1; echo $? > "$E/new-tests.rc"` — 기대 `0`, `tail -n 1 "$E/new-tests.log" | grep -c -E '^43 passed in '` `1`, `grep -c '^SKIPPED' "$E/new-tests.log"` `0`. 컴파일러 없는 PATH(Windows에 컴파일러가 없을 때의 경로를 이 Mac에서 한 번): `cd "$W/tools" && PATH=/bin /usr/bin/timeout 600 .venv/bin/python -m pytest -q -rs -p no:cacheprovider tests/test_locomotion_metrics.py > "$E/nocc-tests.log" 2>&1; echo $? > "$E/nocc-tests.rc"` — 기대 `0`, `tail -n 1 "$E/nocc-tests.log" | grep -c -E '^38 passed, 5 skipped in '` `1`, `grep -c -E '^SKIPPED \[[12]\] tests/test_locomotion_metrics\.py:[0-9]+: no g\+\+/clang\+\+ on PATH$' "$E/nocc-tests.log"` `4`. CLI: `cd "$W/tools" && .venv/bin/python -m golmok_tools.locomotion_metrics report tests/fixtures/locomotion/ticks_min.json > "$E/report.tsv" 2> "$E/report.err"; echo $? > "$E/report.rc"; tr '\t' ',' < "$E/report.tsv" > "$E/report.csv"; diff "$E/expected-report.csv" "$E/report.csv" > "$E/report.diff"; echo "exit=$?" >> "$E/report.diff"` — 기대 `report.rc` `0`, `report.err` 빈 파일, `report.diff` `exit=0` 한 줄. `cd "$W/tools" && .venv/bin/python -m golmok_tools.locomotion_metrics report --markdown tests/fixtures/locomotion/ticks_min.json > "$E/report.md" 2> "$E/report-md.err"; echo $? > "$E/report-md.rc"; diff "$E/expected-report.md" "$E/report.md" > "$E/report-md.diff"; echo "exit=$?" >> "$E/report-md.diff"` — 기대 `0`, 빈 파일, `exit=0` 한 줄. 오류 경로 한 번(규칙 8): `cd "$W/tools" && .venv/bin/python -m golmok_tools.locomotion_metrics report "$E/status-before.log" > "$E/report-bad.out" 2> "$E/report-bad.err"; echo $? > "$E/report-bad.rc"` — 기대 `report-bad.rc` `2`, `report-bad.out` 빈 파일, `report-bad.err` 한 줄 `locomotion_metrics: error: status-before.log: not valid JSON (line 1)`(`status-before.log`가 빈 파일이어도 줄 1이다).
  5. **변형 실험**(하네스 백그라운드, 커밋하지 않음): `/usr/bin/timeout 900 sh "$E/j24_mutate.sh" "$W" "$E" > "$E/mutations.log" 2> "$E/mutations.err"; echo $? > "$E/mutations.rc"` — 기대 `0`. `diff "$E/expected-mutations.txt" "$E/mutations.log" > "$E/mutations.diff"; echo "exit=$?" >> "$E/mutations.diff"` — 기대 `exit=0` 한 줄, `mutations.err` 빈 파일. 되돌림: `cd "$W" && cmp "$E/locomotion_metrics.py" tools/golmok_tools/locomotion_metrics.py; echo "exit=$?" > "$E/mutate-restored.log"; git -C "$W" status --porcelain | diff "$E/status-files.log" - > "$E/status-mutate.diff"; echo "exit=$?" >> "$E/status-mutate.diff"` — 기대 둘 다 `exit=0` 한 줄. 변형마다의 pytest 원문은 `"$E/m1.log"`…`"$E/m8.log"`에 남는다.
  6. **게이트**(하네스 백그라운드, 변형 실험 뒤 — 규칙 13): `cd "$W/tools" && source .venv/bin/activate && { /usr/bin/timeout 300 ruff check . && /usr/bin/timeout 300 ruff format --check . && /usr/bin/timeout 1800 pytest -q && /usr/bin/timeout 300 python scripts/check_repo.py; } > "$E/gate.log" 2>&1; echo $? > "$E/gate.rc"` — 기대 `0`(rc 124 = 시간 초과, 다시 돌리지 않고 멈춤). 세기: `grep -E '^[0-9]+ passed, [0-9]+ skipped' "$E/gate.log" | sed -E 's/^([0-9]+) passed, ([0-9]+) skipped.*/\1 \2/' > "$E/gate-count.log"; awk '{print $1 + 43, $2}' "$E/base-count.log" > "$E/expected-count.log"; test -s "$E/gate-count.log" && diff "$E/expected-count.log" "$E/gate-count.log" > "$E/count.diff"; echo "exit=$?" >> "$E/count.diff"` — 기대 `count.diff` `exit=0` 한 줄(새 테스트 43개가 모두 돌고 skip이 늘지 않았다). 게이트가 세 파일보다 새것인지: `cd "$W" && [ "$E/gate.log" -nt tools/golmok_tools/locomotion_metrics.py ] && [ "$E/gate.log" -nt tools/tests/test_locomotion_metrics.py ] && [ "$E/gate.log" -nt tools/tests/fixtures/locomotion/ticks_min.json ]; echo "newer=$?" > "$E/mtime.log"` — 기대 `newer=0`.
  7. **커밋·push·PR·CI**: `cd "$W" && git add tools/golmok_tools/locomotion_metrics.py tools/tests/test_locomotion_metrics.py tools/tests/fixtures/locomotion/ticks_min.json && git diff --cached --name-only > "$E/c1-files.log"; printf '%s\n' tools/golmok_tools/locomotion_metrics.py tools/tests/fixtures/locomotion/ticks_min.json tools/tests/test_locomotion_metrics.py | diff - "$E/c1-files.log" > "$E/c1-files.diff"; echo "exit=$?" >> "$E/c1-files.diff"` — 기대 `exit=0` 한 줄(규칙 6). 커밋: `cd "$W" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-24: tools — locomotion_metrics 순수 지표 1차분(V-08b §9-2 planted·slip_frames·legacy_v11·표 B·Offset Root Bone, report CLI)" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c1-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author.log"` — 기대 `author.log` `재환 <jaehwan.local@localhost>`. `git -C "$W" push -u origin local/jaehwan-j24-locomotion-metrics > "$E/push.log" 2>&1; echo "exit=$?" >> "$E/push.log"` — 기대 끝 줄 `exit=0`. `git -C "$W" diff --name-only origin/main...HEAD > "$E/branch-files.log"; diff "$E/c1-files.log" "$E/branch-files.log" > "$E/branch-files.diff"; echo "exit=$?" >> "$E/branch-files.diff"` — 기대 `exit=0` 한 줄. `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-final.diff"; echo "exit=$?" >> "$E/status-final.diff"` — 기대 `exit=0` 한 줄. PR 열기(첫 본문은 이 한 문장뿐 — 상시 규칙 "PR 본문 공통" 2, 규칙 2; 2026-11-28 문서 9 검증 지적: 옛 일곱 줄 꼴을 이 한 줄로 바꿨다, dry-run sh·zsh 모두 한 줄 `CI 진행 중 — 결과는 아래에 추가`): `printf '%s\n' 'CI 진행 중 — 결과는 아래에 추가' > "$E/pr-body-initial.md"; cd "$W" && gh pr create --base main --head local/jaehwan-j24-locomotion-metrics --title "J-24: locomotion_metrics 순수 지표 1차분(V-08b §9-2) + 합성 테스트·헤더 대조" --body-file "$E/pr-body-initial.md" > "$E/pr-create.log" 2>&1; echo $? > "$E/pr-create.rc"` — 기대 `0`. PR 번호: `cd "$W" && gh pr view local/jaehwan-j24-locomotion-metrics --json number --jq .number > "$E/pr-number.log" 2> "$E/pr-number.err"` — 기대 숫자 한 줄(`grep -c -x '[0-9][0-9]*' "$E/pr-number.log"` `1`, `wc -l < "$E/pr-number.log" | tr -d ' '` `1`). 런북을 고치지 않으므로 커밋 2(근거 표식)는 없다. CI(하네스 백그라운드): `cd "$W" && /usr/bin/timeout 1800 gh pr checks "$(cat "$E/pr-number.log")" --watch --interval 30 > "$E/checks-watch.log" 2>&1; echo "exit=$?" >> "$E/checks-watch.log"; /usr/bin/timeout 120 gh pr checks "$(cat "$E/pr-number.log")" > "$E/checks.log" 2>&1` — 기대 모든 행 pass. `checks-watch.log`에 `no checks reported`가 있으면 실패가 아니라 등록 지연이다(상시 규칙 "CI 감시의 등록 전 경합"): 첫 두 로그는 그대로 두고, 등록 대기(하네스 백그라운드) `H=$(git -C "$W" rev-parse HEAD); cd "$W" && /usr/bin/timeout 600 sh -c 'until [ "$(gh run list --commit "$1" --json event --jq "[.[]|select(.event==\"push\" or .event==\"pull_request\")]|length")" -ge 2 ]; do sleep 30; done' sh "$H" > "$E/run-wait.log" 2>&1; echo $? > "$E/run-wait.rc"` — 기대 `0`. 그 뒤 같은 watch 두 명령을 `checks-watch-2.log`·`checks-2.log`로 한 번 더 돌리고, 이후(`## CI`·완료 기준 (h)·멈춤 조건) `checks.log` 대신 `checks-2.log`를 쓴다. **CI 행별 수**(Windows 컴파일러 확인 포함): `cd "$W" && gh run list --workflow CI --branch local/jaehwan-j24-locomotion-metrics --event push --commit "$(git -C "$W" rev-parse HEAD)" --json databaseId --jq '.[0].databaseId' > "$E/pr-run.log" 2>&1; gh run list --workflow CI --branch main --event push --commit "$(git -C "$W" merge-base HEAD origin/main)" --json databaseId --jq '.[0].databaseId' > "$E/base-run.log" 2>&1; gh run view "$(cat "$E/base-run.log")" --json conclusion --jq .conclusion > "$E/base-run-conclusion.log" 2>&1` — 기대 `pr-run.log`·`base-run.log` 각각 숫자 한 줄(`grep -c -x '[0-9][0-9]*'` `1`), `base-run-conclusion.log` `success`. `cd "$W" && sh "$E/j24_ci.sh" "$(cat "$E/base-run.log")" > "$E/base-ci.log" 2>&1; sh "$E/j24_ci.sh" "$(cat "$E/pr-run.log")" > "$E/pr-ci.log" 2>&1; awk '{print $1, $2, $3 + 43, $4}' "$E/base-ci.log" > "$E/expected-ci.log"; test -s "$E/base-ci.log" && diff "$E/expected-ci.log" "$E/pr-ci.log" > "$E/ci-count.diff"; echo "exit=$?" >> "$E/ci-count.diff"` — 기대 `wc -l < "$E/base-ci.log" | tr -d ' '` `4`, `ci-count.diff` `exit=0` 한 줄(네 행 모두 +43 passed, skipped 그대로 — 2026-11-28 `366e118` 기준이면 `macos-latest 3.12 1983 3`·`ubuntu-latest 3.11 1982 4`·`ubuntu-latest 3.12 1982 4`·`windows-latest 3.12 1940 46`).
  8. **PR 본문**: PR 본문·자리표시 분류·칸 자기 검사·근거 표기는 상시 규칙 "PR 본문 공통(모든 과제)"을 따른다(이 절과 다르면 그 소절을 따른다). 이 과제는 런북을 고치지 않으므로 소절 7(칸 자기 검사)·8(근거 표식)은 해당 없음이다 — 점검표 규칙 17 줄에 "런북 줄 없음(허용 파일에 런북 없음)"과 `branch-files.log`를 적는다. `## 결과`에는 관찰한 값만, 각각 백틱 펜스 블록에 그대로 둔다: `new-tests.log` 끝 줄, `nocc-tests.log`의 `SKIPPED` 4줄과 끝 줄, `report.csv`, `report.md`, `mutations.log`, `base-count.log`·`gate-count.log`, `base-ci.log`·`pr-ci.log` — 그 펜스 밖에는 과제 번호·규칙 번호·날짜를 쓰지 않는다. `## 실행한 명령`에는 `commands.txt`를 백틱 펜스 블록에. `## 남은 [미확인]`은 펜스 `j24-unverified-md`를 그대로 붙인다: 초안을 절 순서대로 쓰다가 `## 남은 [미확인]` 제목 줄과 빈 줄 하나를 쓴 직후 `cat "$E/unverified.md" >> "$E/pr-body.md"`를 한 번 돌린다. `## 병합 시 반영`은 한 줄 `pc-verify-v08b.md §9-1 표 아래 메모(이 함수들의 위치, §9-3 커밋 범위 축소)는 병합하는 쪽이 넣는다. 이 PR은 런북을 고치지 않는다.` `## 완료 기준 대조`는 아래 (a)~(i) 한 줄씩. 본문 초안은 `$E/pr-body.md`. 게시 전 검사(규칙 10 e·f) — **대상 로그는 이 목록으로 고정한다**(본문 초안·게시본·`task.txt`·`commands.txt`·검사 로그 자신은 넣지 않는다): `"$E"/new-tests.log "$E"/nocc-tests.log "$E"/report.csv "$E"/report.md "$E"/report-bad.err "$E"/mutations.log "$E"/base-count.log "$E"/gate-count.log "$E"/base-ci.log "$E"/pr-ci.log "$E"/sha.log "$E"/gate.log "$E"/checks.log`.
     - 인용 검사: `## 결과` 절의 펜스 밖 백틱 문자열마다 그 문자열이 근거로 든 로그 **한 개**를 `"$E/quotes.tsv"`에 `문자열`(탭)`위 목록의 파일 이름`으로 적는다(로그 인용이 아닌 파일 이름·명령은 파일 칸에 `라벨`). 빠진 것 확인·세기와 아래 숫자 검사는 펜스 `j24-bodycheck-sh`(이 절의 허용 파일 줄 바로 앞)가 한 번에 한다(2026-11-28 문서 9: 백틱이 든 옛 인라인 명령을 글자 그대로 옮긴 스크립트 — 옛 명령과 같은 여섯 파일 `body-quotes.txt`·`tsv-quotes.txt`·`quotes-missing.log`·`quotes-check.log`·`body-numbers.txt`·`numbers-check.log`를 쓴다(`checks-2.log`가 없으면 내용도 같다); 숫자 검사 목록 끝의 `checks.log`는 `checks-2.log`가 있으면 그것; 상시 규칙 "PR 본문 공통" 11·14). `quotes.tsv`를 다 쓴 뒤 뽑기·확인·실행을 한 호출로: `awk -v n=j24-bodycheck-sh 'BEGIN {b = sprintf("%c%c%c", 96, 96, 96)} x && $0 == b {x = 0} x {print} !x && index($0, b) == 1 && $0 ~ (" " n "$") {x = 1}' "$E/task.txt" > "$E/j24_bodycheck.sh"; [ "$(wc -l < "$E/j24_bodycheck.sh" | tr -d ' ')" = "13" ] && head -n 1 "$E/j24_bodycheck.sh" | grep -q -x '#!/bin/sh' && sh "$E/j24_bodycheck.sh" "$E" > "$E/bodycheck.log" 2>&1; echo $? > "$E/bodycheck.rc"` — 기대 `bodycheck.rc` `0`, `bodycheck.log` 빈 파일, `quotes-missing.log` 빈 파일. 세기는 `quotes-check.log`(`quotes.tsv` 행마다 한 행) — 기대: `cut -f1 "$E/quotes-check.log" | grep -c -x '0'`가 `0`.
     - 숫자 검사: 위 `j24_bodycheck.sh`가 쓴 `body-numbers.txt`·`numbers-check.log`(숫자마다 한 행, 대상은 위 고정 목록) — 기대: `cut -f1 "$E/numbers-check.log" | grep -c -x '0'`가 `0`.
     - 0이 나온 것은 고치거나 지운다. 그다음 상시 규칙 "PR 본문 공통" 3(점검표 대조)·5(자리표시 분류)·6(조립·게시·다시 읽기)을 적힌 그대로 돌린다. 공통 4 ③의 (P) 줄 글자는 이 과제에서 `(i)`다.
```sh j24-bodycheck-sh
#!/bin/sh
# J-24: quote and number checks of the PR draft (usage: sh j24_bodycheck.sh <E>); needs E/pr-body.md and E/quotes.tsv.
# Same commands as the inline checks they replace (docs 9); writes body-quotes.txt, tsv-quotes.txt,
# quotes-missing.log, quotes-check.log (one row per quotes.tsv row), body-numbers.txt, numbers-check.log (one row per number).
E=$1
CK=checks.log
if [ -e "$E/checks-2.log" ]; then CK=checks-2.log; fi
awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '`[^`]+`' | sed 's/^`//;s/`$//' | sort -u > "$E/body-quotes.txt"
cut -f1 "$E/quotes.tsv" | sort -u > "$E/tsv-quotes.txt"
comm -23 "$E/body-quotes.txt" "$E/tsv-quotes.txt" > "$E/quotes-missing.log"
while IFS="$(printf '\t')" read -r q f; do if [ "$f" = "라벨" ]; then n="라벨"; else n=$(grep -F -c -- "$q" "$E/$f"); fi; printf '%s\t%s\t%s\n' "$n" "$f" "$q"; done < "$E/quotes.tsv" > "$E/quotes-check.log"
awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '[0-9]{2,}' | sort -u > "$E/body-numbers.txt"
while read -r x; do printf '%s\t%s\n' "$(cat "$E"/new-tests.log "$E"/nocc-tests.log "$E"/report.csv "$E"/report.md "$E"/report-bad.err "$E"/mutations.log "$E"/base-count.log "$E"/gate-count.log "$E"/base-ci.log "$E"/pr-ci.log "$E"/sha.log "$E"/gate.log "$E/$CK" | grep -c -- "$x")" "$x"; done < "$E/body-numbers.txt" > "$E/numbers-check.log"
```

- **허용 파일**: 새 파일 `tools/golmok_tools/locomotion_metrics.py`·`tools/tests/test_locomotion_metrics.py`·`tools/tests/fixtures/locomotion/ticks_min.json`(셋 다 펜스 그대로). 그 밖의 저장소 파일은 고치지 않는다: `tools/pyproject.toml`(핫스팟), `tools/tests/test_ue_locomotion_math.py`(가져다 쓰기만), `tools/tests/fixtures/ue/locomotionmath_driver.cpp`, `unreal/Golmok/Source/Golmok/Animation/GolmokLocomotionMath.h`, `docs/runbooks/pc-verify-v08b.md`(병합 때 영록), 공유 문서, Astra 레인. 변형 실험의 바뀐 모듈은 커밋하지 않는다(스크립트가 되돌린다).
- **멈춤 조건(정하지 말고 영록에게 묻는다)**: `status-before-tracked.log`가 0이 아닐 때. `switch.rc`가 0이 아니거나 `sha-same.log`가 1이 아닐 때. `head -1 "$E/task.txt"`가 `#### J-24 `로 시작하지 않을 때. `extract-wc.log`가 기대와 다를 때. `overlap.log`·`absent.log`가 비어 있지 않을 때. `compilers-count.log`가 `0`일 때. `numpy.log` 첫 낱말이 `numpy-ok`가 아닐 때. `base-pytest.rc`가 0이 아니거나 `base-count.log`가 숫자 두 개 한 줄이 아닐 때(skip이 0이라 요약 꼴이 다를 때도 — 기대를 고치지 않는다). `copy.rc`가 0이 아니거나 `cmp.log`·`status-new.diff`가 `exit=0` 한 줄이 아닐 때. `new-tests.rc`·`nocc-tests.rc`가 0이 아니거나 끝 줄·`SKIPPED` 수가 기대와 다를 때(테스트·모듈을 고치지 않는다 — FAILED 줄을 보고). `report.rc`·`report-md.rc`가 0이 아니거나 `report.diff`·`report-md.diff`가 `exit=0` 한 줄이 아니거나 `report.err`·`report-md.err`가 비어 있지 않을 때. `report-bad.rc`가 2가 아니거나 `report-bad.err`가 기대 한 줄과 다를 때. `mutations.rc`가 0이 아니거나(3 = 모듈이 펜스와 다르다, 124 = 시간 초과) `mutations.diff`·`mutate-restored.log`·`status-mutate.diff`가 `exit=0` 한 줄이 아니거나 `mutations.err`가 비어 있지 않을 때 — 이때 모듈이 바뀐 채면 `cp "$E/locomotion_metrics.py" "$W/tools/golmok_tools/locomotion_metrics.py"`로 되돌리고 `cmp` 결과를 함께 보낸다. `gate.rc`가 0이 아닐 때(rc 124 포함, 다른 파일을 고치거나 `ruff format`으로 바꾸지 않는다). `count.diff`가 `exit=0` 한 줄이 아닐 때. `mtime.log`가 `newer=0`이 아닐 때. `c1-files.diff`·`branch-files.diff`·`status-final.diff`가 `exit=0` 한 줄이 아니거나 `author.log`가 다를 때. `push.log`가 `exit=0`으로 끝나지 않을 때. `pr-create.rc`·`pr-edit.rc`가 0이 아니거나 `pr-number.log`가 숫자 한 줄이 아닐 때. `checks.log`에 pass가 아닌 행이 있을 때. `run-wait.rc`가 있고 0이 아닐 때(다시 돌리지 않는다). `pr-run.log`·`base-run.log`가 숫자 한 줄이 아니거나 `base-run-conclusion.log`가 `success`가 아닐 때, `base-ci.log`가 4줄이 아니거나 `ci-count.diff`가 `exit=0` 한 줄이 아닐 때(예: Windows 행의 skipped가 5 늘었다 — 컴파일러가 없다는 뜻이므로 그 두 줄을 보고하고 기대를 고치지 않는다). 상시 규칙 "PR 본문 공통" 9의 공통 멈춤 조건. 그 밖에 이 절의 "기대"와 다른 값이 하나라도 나올 때.
- **완료 기준**:
  - (a) 준비: `status-before-tracked.log` `0`, `switch.rc` `0`, `sha-same.log` `1`, `task.txt` 첫 줄 `#### J-24 `, `extract-wc.log` 원문(기대 숫자와 같다), `overlap.log`·`absent.log` 빈 파일, `compilers-count.log` 1 이상, `numpy.log` `numpy-ok`.
  - (b) 기준선: `base-pytest.rc` `0`, `base-count.log` 숫자 두 개 한 줄.
  - (c) 파일: `copy.rc` `0`, `cmp.log` `exit=0`, `status-new.diff` `exit=0`(새 `??` 세 줄뿐).
  - (d) 새 테스트·CLI: `new-tests.log` 끝 줄 `43 passed in …`·`SKIPPED` 0, `nocc-tests.log` 끝 줄 `38 passed, 5 skipped in …`·`SKIPPED` 4줄, `report.diff`·`report-md.diff` `exit=0`, `report.err`·`report-md.err` 빈 파일, `report-bad.rc` `2`와 `report-bad.err` 기대 한 줄.
  - (e) 비공허: `mutations.rc` `0`, `mutations.diff` `exit=0`(8변형 모두 `diff=2 rc=1 restored=0`과 기대 FAILED 이름), `mutations.err` 빈 파일, `mutate-restored.log`·`status-mutate.diff` `exit=0`.
  - (f) 게이트: `gate.rc` `0`, `count.diff` `exit=0`(기준 + 43 passed, skipped 그대로), `mtime.log` `newer=0`.
  - (g) 커밋: `c1-files.diff` `exit=0`, `author.log` `재환 <jaehwan.local@localhost>`, `push.log` 끝 줄 `exit=0`, `branch-files.diff` `exit=0`, `status-final.diff` `exit=0`, `pr-create.rc` `0`, `pr-number.log` 숫자 한 줄.
  - (h) CI: `checks.log` 모든 행 pass 원문(규칙 2 — 등록 대기를 돌렸으면 `run-wait.rc` `0`과 `checks-2.log`), `base-run-conclusion.log` `success`, `base-ci.log` 4줄, `ci-count.diff` `exit=0`(네 행 모두 +43 passed, skipped 그대로 — 수락 (a)의 헤더 대조가 Windows에서도 돌았다).
  - (i) PR 본문: 절 순서(상시 규칙 "PR 본문 공통" 2), "완료 기준 대조" 절, 점검표(그날 규칙 수만큼, 소절 3), `## 남은 [미확인]`에 펜스 `j24-unverified-md` 4줄 그대로(`grep -c -x -F -f "$E/unverified.md" "$E/pr-body.md" > "$E/unverified-in-body.log"` — 기대 `4`; 수락 (b)·(c) "미대조" — 통과로 쓰지 않는다). `quotes-missing.log` 빈 파일, `quotes-check.log`·`numbers-check.log`에 0 없음. 공통 완료 기준 (P)(소절 10): `checklist.diff` `exit=0`, `ph-unfilled.log` `0`, `pr-edit.rc` `0`, `ph-posted-unfilled.log` `0`, `ph-table.diff` `exit=0`, `signature-last.log` `1`(런북 줄이 없어 `cell-grep-*`은 해당 없음).
- **병합 시 반영(영록)**: STATUS 재환 절에 J-24 행. `pc-verify-v08b.md` §9-1 표 아래 메모 한 줄: `locomotion_metrics.py`의 `planted_travel_cm`·`planted_slip_cm_per_m`·`slip_frames`·`legacy_v11_slip`·표 B·Offset Root Bone·`report`와 `test_locomotion_metrics.py`는 J-24 PR로 들어왔고(커밋 제목 `J-24: …`), §9-3 `V-08b: tools` 커밋은 `stair_contact` 등 J-24b 몫과 `locomotion_pure.py`·`locomotion_driver.py`·그 테스트만 담는다. 수락 (a)는 이 PR의 CI로 충족, (b)·(c)는 "미대조"(원자료는 §5 자료 복사 뒤). 틱 JSON에 선택 필드 `root_yaw`를 더했다는 것을 §9-1 최소 필드 목록 아래에 적는다(기록기 `locomotion_pure.py`가 쓰게). J-24b(설계 선행) 행을 백로그에 더한다.
- **왜 재환 / 위험**: 코드·테스트·fixture·기대 출력이 모두 펜스로 정해져 있고, 판정은 `cmp`·`diff`·`grep -c`·종료 코드로 끝난다. UE·GPU·GUI·캡처·소유자 항목이 없다. 위험: ① 정의 해석(백분위 방식, legacy의 소켓·한 틱 디딤, 기준이 장면 전체, 반응 시작 틱) — 설계 4가 작업 숫자로 고정했고, 리뷰는 fixture 값을 손으로 다시 계산한다. ② 헤더 표류 — 무작위·비유한 대조(1e-9)와 m1·m2가 막는다. 헤더가 바뀌면 대조가 실패한다(멈춤). ③ 범위 넓히기(드라이버·`locomotion_pure`·블라인드) — 허용 파일 셋이 막는다. ④ OS 차이 — 보고 형식은 Python 문자열 형식만 쓰고, CI 행별 수가 Windows의 대조 실행을 확인한다. ⑤ "미대조"를 통과로 쓰는 것 — `j24-unverified-md`를 그대로 붙인다. ⑥ 크기 — M(새 파일 셋, 펜스 복사). 더 커지면 반응·Offset을 J-24b로 옮긴다. ⑦ 지표의 의미·기준값은 이 과제 밖(Opus).
- **J-24b에 넘길 것(Opus 2026-11-28 검증 지적 — 이 과제에서는 하지 않는다)**: fixture의 `dt`가 모두 `t` 차(0.1)와 같아 `slip_frames`가 `dt` 칸이 아니라 `t` 차를 쓴다는 규칙은 어느 테스트도 확인하지 않는다. J-24b에 `dt` ≠ `t` 차인 테스트 하나(예: fixture의 `dt`를 모두 0.2로 바꾸고 `slip_frames` == (1, 6) 유지)와 그 변형 m9를 넣는다.
- **dry-run 범위(Opus 2026-11-28)**: `origin/main` `366e118`의 scratch 사본(`git archive`)에서 한 것: 이 절의 펜스 셋을 사본에 넣어 `ruff check .`(All checks passed)·`ruff format --check .`(126 files already formatted)·`check_repo.py`(OK) 통과, `pytest -q` 전체 `1983 passed, 3 skipped`(넣기 전 `1940 passed, 3 skipped` — +43), 새 파일만 `43 passed`, `PATH=/bin`에서 `38 passed, 5 skipped`(`SKIPPED` 4줄, `[2]` 한 줄 포함). fixture `report` 출력은 펜스 `j24-expected-report-csv`·`j24-expected-report-md`와 같고, 그 값은 설계 4의 손 계산과 같다. 변형 스크립트를 실제 `$W` 가상환경(`golmok-jaehwan/tools/.venv`, numpy 2.5.5, 링크로 빌림)으로 sh·zsh에서 돌려 같은 출력(md5 같음)을 얻었고 그것이 펜스 `j24-expected-mutations`이다(되돌림 `cmp` 같음). 헤더 대조는 `/usr/bin/clang++`(Apple clang 21.0.0)로 컴파일해 통과했다. CI 행별 수 스크립트 `j24-ci-sh`는 실제 실행 46106753000에 돌려 `macos-latest 3.12 1940 3` 등 4줄, `gh run list --commit 366e118… --event push`는 그 실행 번호를 냈다. 겹침 `jq` 식은 가짜 PR 목록(fixture 경로 하나)으로 그 PR만 고르는 것을 확인했다. 펜스 추출 `awk`와 `wc -l`은 이 절을 담은 파일에서 돌려 기대 숫자를 얻었고, 추출한 세 파일은 사본의 파일과 `cmp` 같다. dry-run하지 못한 것: `$W`에서의 실제 실행(브랜치·커밋·push·PR·CI), PR 브랜치 CI의 행별 수(특히 Windows MinGW에서 새 드라이버 컴파일 — 기존 `test_ue_locomotion_math.py`가 같은 플래그로 그 행에서 도는 것으로만 추정), `gh pr checks --watch`, 인용·숫자 검사(본문이 없어서).

#### J-25 V-16 §2a `MPC_GolmokWeather` 헤드리스 생성 시험 + MPC가 있을 때 Weather.Runtime의 MPC 단계 (커밋 없음) — 설계 확정(Opus 2026-11-28)
- **출처**: [pc-verify-wp16a.md](../runbooks/pc-verify-wp16a.md) §2a(:68-81 — 기대 2줄, Error 분기 `created but … - add …`, 다시 `w.run()` → `ok (…)`, 에셋 창의 스칼라 3개·벡터 0개, 수동 절차), §3(:128-129 — "MPC·NS 단계가 EXECUTED", `-nullrhi`의 다른 Info·Warning은 그대로 적는다), §12 #9(:328, 결과 칸 빈 칸)·#10(:329), §13 결과 표의 §2a·§3 행(:348·:351), J-20 줄(:364). 코드: `Content/Python/golmok/weather_setup.py:60-74`(`_read_scalars`·`_write_scalars` — `unreal.CollectionScalarParameter`, `set_editor_property("scalar_parameters", …)`), `:77-92`(`_create_mpc`: 쓰기 예외는 `scalar_parameters not writable from Python (<예외>: <문구>)` problem이 되고, 빈 에셋도 `save_loaded_asset`로 저장한다), `:95-141`(`run()`: `does_asset_exist`로 있으면 검사만, 없으면 만든다. `created`·`ok` 줄 :125-127, `created but` Error :120-124, `not modified` Error :113-116, NS Warning :134, 반환 dict :135-141), `weather_pure.py:37-40`(`MPC_PARAMETERS`). `Source/Golmok/Tests/GolmokWeatherTest.cpp:23-25`·`:329-330`(skip Info 두 문구), `:925`(`LoadMpc()` 호출), `:957-966`(`LoadMpc` — `DescribeMpc() != "ok"`이면 `MPC_GolmokWeather missing - skipped`, 아니면 `TestNotNull("MPC_GolmokWeather loads")`), `:969-1000`(`CheckMpc` — `TestNotNull("…: MPC instance")`, 세 값 ±1.01e-3), `:1136`·`:1148`(표면 표에서 `CheckMpc` 6회), `:1195`·`:1199`(NS skip Info·`NS_GolmokRain present: EXECUTED`), `:1355-1373`(Runtime은 `L_Dev`가 없으면 Error). `Weather/GolmokWeatherSubsystem.cpp:212-233`(MPC를 soft 경로로 읽고, 없으면 프로세스당 한 번 `weather: MPC missing (…)` — 자동화 중에는 Display), `:250-263`(fx 없음도 프로세스당 한 번), `:282-283`(시작 줄 `…, mpc %s, fx %s`), `:524-553`(`WriteMpc` — `:531`의 `[미확인 §17 #10]` 주석), `:846-853`(`DescribeMpc`), `:169-172`(PIE·Game 월드만). `tools/ue/test.sh:25-26`(보고서 폴더를 실행마다 지운다), `:29-30`(`Automation RunTests <필터>;Quit`), `:58-69`(종료 코드 규칙, J-36). `.gitattributes:18`(`*.uasset filter=lfs … lockable`), `.gitignore:2-18`(`Content/Golmok/Weather/`는 무시 목록에 없다). 엔진(읽기, `/Users/Shared/Epic Games/UE_5.8/Engine/`, `Build.version` 5.8.4 CL 58902052): `Source/Runtime/Engine/Public/Materials/MaterialParameterCollection.h:22-55`(`FCollectionScalarParameter`는 `USTRUCT()` — BlueprintType이 아니다. `ParameterName`·`DefaultValue`는 `EditAnywhere`, 생성자가 `Id` GUID를 만든다), `:90-94`(`ScalarParameters`·`VectorParameters` `EditAnywhere`), `Plugins/Experimental/PythonScriptPlugin/Source/PythonScriptPlugin/Private/PyGenUtil.cpp:1609-1613`·`:1774-1796`·`:1811-1815`(편집기에서는 `CPF_Edit` 속성을 편집기 속성으로 내보낸다), `PyWrapperTypeRegistry.cpp:1165-1190`·`:1405-1415`(내보낸 속성이 가리키는 구조체는 `ForceShouldExport`로 Python 타입이 생긴다), `Source/Editor/UnrealEd/Private/Factories/EditorFactories.cpp:744-751`(팩토리는 빈 컬렉션을 만든다), `Source/Runtime/Engine/Private/Materials/ParameterCollection.cpp:231-258`(`PostEditChangeProperty` → `SanitizeParameters`), `Source/Editor/UnrealEd/Private/Subsystems/EditorAssetSubsystem.cpp:49-64`·`:508-543`(`does_asset_exist`는 자산 레지스트리 검색이 끝날 때까지 기다린 뒤 답한다 — 새 편집기 프로세스의 둘째 실행이 첫 실행의 에셋을 본다), `Source/Runtime/Engine/Private/World.cpp:1936-1952`(`GetParameterCollectionInstance`는 없으면 만든다). 공식 문서(Unreal Python 5.8 Experimental): [CollectionScalarParameter](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/CollectionScalarParameter) — `default_value`·`parameter_name` 읽기·쓰기, [MaterialParameterCollection](https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/MaterialParameterCollection) — `scalar_parameters`·`vector_parameters` 읽기·쓰기. 이 문서와 소스는 "쓸 수 있을 것"이라는 가설일 뿐이고, `-nullrhi` 편집기에서 쓰고 저장하고 다시 읽히는지는 이 과제가 처음 잰다. 2026-11-28 Opus가 읽은 기계 상태: `$W`의 `Content/Golmok/`에 `Weather` 폴더 없음(Audio·Maps·Materials·Zones), `Maps/L_Dev.umap` 있음, `$W/unreal/Golmok/Saved/Automation/Report/index.json`(J-12b, 39개)의 `Golmok.Weather.Runtime` entries 6개 — Warning 3개(`idevice_id` 2줄·`No AGolmokGeoOrigin in L_Dev` 1줄)와 Info `MPC_GolmokWeather missing - skipped`·`NS_GolmokRain missing - skipped`·`end: …`. 에디터 로그 `Golmok.log`는 UTF-8(BOM), `LogInit: Command Line: -ExecCmds="…"` 꼴.
- **이력**: 이 절은 옛 "설계 선행" 메모(기본안 "커밋하지 않고 로그만", 허용 파일 "메모가 정한다")를 대신한다(Opus 2026-11-28).
- **설계 (확정, Opus 2026-11-28)**: 재환은 아래를 그대로 옮긴다. 바꿀 점이 보이면 고치지 말고 묻는다.
  1. **무엇을 닫나**: §12 #9 [미확인](Python이 MPC `scalar_parameters`·`CollectionScalarParameter`를 쓸 수 있는가)을 이 Mac의 창 없는 편집기에서 한 번 잰다. 그리고 MPC가 있을 때 `Golmok.Weather.Runtime`의 MPC 단계(`LoadMpc`·`CheckMpc`)가 `-nullrhi`에서 실제로 도는지를 처음 본다(§12 #10의 첫 관찰). NS 저작(§2b)은 GUI라 범위 밖이고, NS 단계는 계속 skip이다.
  2. **생성 실행 꼴(J-12b·J-27과 같다)**: `UnrealEditor-Cmd "$W/unreal/Golmok/Golmok.uproject" "-ExecCmds=py $E/j25_run.py,QUIT_EDITOR" -unattended -nullrhi -nosplash -nopause -nosound`를 `/usr/bin/timeout 900`으로. 생성기는 파일(펜스 `j25-run-py`)이다 — `-ExecCmds`는 쉼표로 명령을 나눈다(J-27 설계 2). 끝 명령은 `QUIT_EDITOR`(상시 규칙), `-ExecutePythonScript`는 쓰지 않는다(WP-21 종료 크래시). 같은 생성기를 **두 번, 서로 다른 편집기 프로세스로** 돌린다: 둘째 실행은 디스크에서 다시 읽은 에셋에 대해 `run()`의 "있음 → 검사만" 길을 탄다(= 런북의 "다시 `w.run()`"을 다시 띄운 편집기에서 한 것). 생성기는 `run()`의 반환 dict를 `j25_run: mpc=… created=… problems=… rain_fx_exists=…` 한 줄로 남기고, 예외면 `j25_run: exception …`을 Error로 남긴다.
  3. **읽기(셋째 프로세스)와 파일 바이트**: 펜스 `j25-readback-py`가 따로 띄운 편집기에서 에셋을 읽어 `j25_readback: …` 줄을 남긴다(있음, MPC 타입인가, 스칼라마다 순번·이름·기본값, 스칼라·벡터 수, `done`). 기대는 펜스 `j25-expected-readback` 7줄. 런북의 "에셋 수정 표시(*)가 생기지 않는다"는 GUI라 재지 않고, 대신 첫 실행 뒤·둘째 실행 뒤·읽기 뒤·두 테스트 뒤·옮긴 뒤의 `.uasset` sha256이 모두 같은지(`asset-unique-count.log` `1`)를 본다 — 첫 실행만 저장한다(`weather_setup.py:90`).
  4. **분기(미리 정함, 펜스 `j25-branch-sh`)**: 첫 실행의 `logcheck-1.log`가 펜스 `j25-expected-logcheck-1`과 같으면 **A**(Python이 세 스칼라를 썼다 — 할 일 4~6을 하고, 런북 두 곳을 쓴다). `created but scalar_parameters not writable from Python (`로 시작하는 Error 1, `created` 0, 생성기 줄 `created=True problems=1` 1, 예외·`Traceback` 0이면 **B**(쓰기 불가 — 할 일 4~6을 건너뛰고 할 일 7 정리, 할 일 8에서 §12 #9 칸만 B 문구로 쓰고 §13 줄은 쓰지 않는다. **§2a 수동 절차는 하지 않는다**: GUI이고 재환 몫이 아니다). 그 밖(`stop` — 예: 값·순서 불일치의 `created but scalar parameter …`, 예외, 실행 줄 없음)은 멈춘다. B에서 `LogPython: Error:` 줄 수는 판정하지 않는다(엔진이 같은 예외를 따로 찍을 수 있다 [미확인]).
  5. **테스트와 판정(A만)**: `./tools/ue/test.sh --filter Golmok.Weather.Runtime`, 그다음 `./tools/ue/test.sh --filter Golmok.Weather`. 실행마다 `index.json`과 에디터 `Golmok.log`를 곧바로 `$E`에 복사한다(`test.sh:25-26`이 보고서를 지우고, 에디터가 로그를 돌린다). 판정은 종료 코드와 보고서 `entries`에서 기계적으로 뽑은 줄(펜스 `j25-report-py`)이다: Runtime의 Info `MPC_GolmokWeather missing - skipped` **0**, `NS_GolmokRain missing - skipped` **1**, `NS_GolmokRain present: EXECUTED` 0, Error 0, 상태 `Success`, `failed` 0 — 펜스 `j25-expected-report-runtime`·`j25-expected-report-weather`와 `diff`. 기록 문구는 **"MPC 단계 완료 / NS 단계 skip"**이고 "Weather.Runtime 통과"라고 쓰지 않는다(R149·R153의 반복 금지, 규칙 14·15). MPC skip이 0이고 실패가 0이면 `LoadMpc`의 `TestNotNull`과 `CheckMpc` 6회(인스턴스 존재·세 값 ±1.01e-3)가 실패 없이 돈 것이다(통과한 단언은 보고서에 문구가 없다 — `:740` 주석과 같은 사정). 그 테스트의 entries 전체(`entries-<필터>.tsv`)는 §12 #10 근거로 PR 본문에 원문 그대로 둔다. 알려진 Warning 3개(J-12b 보고서의 `idevice_id` 2줄·`No AGolmokGeoOrigin` 1줄, 펜스 안 `KNOWN`) 밖의 Warning은 `unknown-warn-<필터>.log`에 원문으로 모으고 **판정하지 않는다**(수만 런북 줄에, 원문은 PR 본문에). 실패(`test.sh` rc 0 아님, `failed` 0 아님, MPC 단언 실패)는 멈춘다 — `-nullrhi`의 MPC 인스턴스 해석은 Opus 몫이다. 에디터 로그 사실(펜스 `j25-testlog-sh`): `weather: MPC missing (` 0, `weather: rain fx missing (` 1(프로세스당 한 번, `:250-263`), 시작 줄 `, mpc missing, fx ` 0, `, 10 schedule slots, mpc ok, fx missing` 있음.
  6. **에셋 처분(재환에게 선택 없음)**: 만든 `.uasset`은 **커밋하지도 LFS 잠그지도 않는다**(`.gitattributes:18`로 lockable LFS이고 `.gitignore`에 없다 — `git add` 한 번이면 들어간다. 할 일 3이 `check-attr`·`check-ignore`로 그 사실을 기록한다). 테스트 뒤(B면 첫 실행 뒤) 펜스 `j25-cleanup-sh`가 `Content/Golmok/Weather/MPC_GolmokWeather.uasset`을 `$E/asset/`으로 **옮기고**(`mv`, `rm` 아님) 빈 `Weather` 폴더만 `rmdir`한다(다른 파일이 있으면 아무것도 지우지 않고 멈춘다). 옮긴 파일의 sha256은 첫 실행 뒤 값과 같아야 하고, 정리 뒤 `git status --porcelain`은 실행 전 사본과 같아야 한다. `$E/asset/`의 파일은 병합 알림 뒤에도 지우지 않는다. 헤드리스로 만든 MPC를 V-16의 커밋 에셋으로 쓸지는 V-16 세션의 Opus 결정이다("병합 시 반영").
  7. **순서**: J-21·J-22가 병합된 뒤에만 한다. J-22는 패키지 컨테이너에 MPC 0줄("에셋 전")을 확인하므로 `$W`에 남은 MPC가 그 결과를 무효로 만들고, 세 과제 모두 pc-verify-wp16a에 쓴다. 할 일 1이 막는다: `Content/Golmok/Weather`가 이미 있거나 `MPC_GolmokWeather*` 파일이 `Content` 어디에든 있으면, `Mac 부분 선행(J-21, `·`(J-22, ` 줄이 각각 1개가 아니면, J-25 줄이 이미 있으면 멈춘다. 멈출 때도 에셋을 `$W`에 남기지 않는다(아래 "멈춤 순서").
  8. **결과 자리(규칙 16, 추가만)**: ① §12 표 #9 행(:328)의 빈 "PC 결과" 칸 — 행 전체가 펜스 `j25-row9-before`와 같은 줄 하나를, 그 줄의 끝 ` |`를 떼고 ` <칸> |`를 붙인 줄로 바꾼다(`awk`, 손으로 고치지 않는다). 칸 글은 펜스 `j25-cell-sh`가 분기·날짜·SHA로 만든다(`|` 없음). ② 분기 A만: §13 표 아래 J-22 줄(`Mac 부분 선행(J-22, `로 시작) **바로 다음**에 빈 줄 하나와 펜스 `j25-line-sh`의 한 줄. §13 표의 §2a·§3 행, #10 칸, J-20·J-21·J-22 줄은 고치지 않는다. 두 글의 끝은 `근거: J-25 PR.`(칸은 그 뒤에 ` |`)이고, 커밋 2가 `근거: PR #<번호>.`로 바꾼다(상시 규칙 "PR 본문 공통" 8).
  9. **넓게 쓰지 않는다(규칙 3·15)**: 칸과 줄은 날짜·SHA·`UnrealEditor-Cmd -nullrhi`라는 조건을 단다. "Python은 언제나 MPC를 쓸 수 있다"로 쓰지 않는다 — GUI Output Log 실행, 에셋 창의 값, 수정 표시, 다른 장치는 [미확인]으로 남는다.
  10. **빌드 먼저**: 편집기가 `$W`의 `Golmok` 모듈을 읽으므로 할 일 2에서 증분 `build.sh`를 한 번 돌린다(J-27 할 일 2와 같다). 기대 rc `0`.
  11. **코드 변경 없음**: C++·Python(`weather_setup.py` 포함)·`tools/ue/*.sh`·`Config/`·테스트는 고치지 않는다. 생성기·읽기·검사 스크립트는 `$E`에만 있다(규칙 6).

```python j25-run-py
# J-25: one golmok.weather_setup.run() in a headless editor (UnrealEditor-Cmd -nullrhi); logs the returned dict.
import traceback

import golmok.weather_setup as w
import unreal

try:
    r = w.run()
except Exception as e:
    unreal.log_error(f"j25_run: exception {type(e).__name__}: {e}")
    unreal.log_error(traceback.format_exc())
else:
    unreal.log(
        f"j25_run: mpc={r['mpc']} created={r['created']} problems={len(r['problems'])}"
        f" rain_fx_exists={r['rain_fx_exists']}"
    )
```

```python j25-readback-py
# J-25: reads MPC_GolmokWeather back in a separate headless editor; one "j25_readback: ..." line per fact.
import unreal

PACKAGE = "/Game/Golmok/Weather/MPC_GolmokWeather"
lib = unreal.EditorAssetLibrary
exists = bool(lib.does_asset_exist(PACKAGE))
unreal.log(f"j25_readback: exists {exists}")
if exists:
    a = lib.load_asset(PACKAGE)
    unreal.log(f"j25_readback: is-mpc {isinstance(a, unreal.MaterialParameterCollection)}")
    scalars = list(a.get_editor_property("scalar_parameters"))
    for i, p in enumerate(scalars):
        name = str(p.get_editor_property("parameter_name"))
        default = float(p.get_editor_property("default_value"))
        unreal.log(f"j25_readback: scalar {i} {name} {default:g}")
    vectors = list(a.get_editor_property("vector_parameters"))
    unreal.log(f"j25_readback: counts scalars {len(scalars)} vectors {len(vectors)}")
unreal.log("j25_readback: done")
```

```sh j25-logcheck-sh
#!/bin/sh
# J-25: fixed line counts in one headless-editor log copy (usage: sh j25_logcheck.sh <log> <script file name>), one "label count" per line.
G=$1
S=$2
P=/Game/Golmok/Weather/MPC_GolmokWeather
c() { printf '%s %s\n' "$1" "$2"; }
c cmdline "$(grep -F 'Command Line: ' "$G" | grep -c -F -- "$S,QUIT_EDITOR")"
c created "$(grep -c -F "LogPython: weather_setup: $P created (RainIntensity, Wetness, PuddleAmount, default 0)" "$G")"
c ok "$(grep -c -F "LogPython: weather_setup: $P ok (RainIntensity, Wetness, PuddleAmount, default 0)" "$G")"
c created-but "$(grep -c -F "LogPython: Error: weather_setup: $P created but " "$G")"
c not-writable "$(grep -c -F "LogPython: Error: weather_setup: $P created but scalar_parameters not writable from Python (" "$G")"
c not-modified "$(grep -c -F ' - not modified, fix it by hand (' "$G")"
c keeps-more "$(grep -c -F "weather_setup: $P keeps " "$G")"
c ns-missing "$(grep -c -F 'LogPython: Warning: weather_setup: /Game/Golmok/Weather/NS_GolmokRain missing - author it with runbook pc-verify-wp16a ' "$G")"
c python-error "$(grep -c -F 'LogPython: Error: ' "$G")"
c traceback "$(grep -c -F 'Traceback' "$G")"
c j25-created "$(grep -c -F "j25_run: mpc=$P created=True problems=0 rain_fx_exists=False" "$G")"
c j25-ok "$(grep -c -F "j25_run: mpc=$P created=False problems=0 rain_fx_exists=False" "$G")"
c j25-created-problem "$(grep -c -F "j25_run: mpc=$P created=True problems=1 rain_fx_exists=False" "$G")"
c j25-exception "$(grep -c -F 'j25_run: exception ' "$G")"
```

```sh j25-branch-sh
#!/bin/sh
# J-25: the branch after run 1 (usage: sh j25_branch.sh <E>) - prints A (Python wrote the three scalars), B (not writable) or stop.
E=$1
v() { awk -v k="$1" '$1 == k {print $2}' "$E/logcheck-1.log"; }
if diff -q "$E/expected-logcheck-1.txt" "$E/logcheck-1.log" > /dev/null; then
  echo A
elif [ "$(v cmdline)" = 1 ] && [ "$(v created)" = 0 ] && [ "$(v created-but)" = 1 ] && [ "$(v not-writable)" = 1 ] && [ "$(v j25-created-problem)" = 1 ] && [ "$(v j25-exception)" = 0 ] && [ "$(v traceback)" = 0 ]; then
  echo B
else
  echo stop
fi
```

```python j25-report-py
# J-25: fixed facts from one automation report (usage: python -I j25_report.py <index.json> <entries out> <unknown warnings out>).
import json
import sys

KNOWN = (
    'LogHAL: FMacPlatformProcess::CreateProc: posix_spawn("/Users/Shared/Epic Games/UE_5.8/Engine/Extras/ThirdPartyNotUE/libimobiledevice/Mac/idevice_id") failed (86, Bad CPU type in executable)',
    "LogHAL: Failed to launch Tool. (/Users/Shared/Epic Games/UE_5.8/Engine/Extras/ThirdPartyNotUE/libimobiledevice/Mac/idevice_id)",
    "LogGolmok: No AGolmokGeoOrigin in L_Dev: zones are placed with their own origin at the level origin (dev level mode). Place one AGolmokGeoOrigin at (0,0,0) with the basemap area origin for geo-referenced placement.",
)
RUNTIME = "Golmok.Weather.Runtime"
with open(sys.argv[1], encoding="utf-8-sig") as f:
    report = json.load(f)
tests = report.get("tests") or []
print(f"tests {len(tests)}")
print(f"failed {report.get('failed')}")
print(f"notrun {report.get('notRun')}")
for t in sorted(tests, key=lambda t: str(t.get("fullTestPath"))):
    print(f"state {t.get('fullTestPath')} {t.get('state')}")
events = [e.get("event") or {} for t in tests if t.get("fullTestPath") == RUNTIME for e in t.get("entries") or []]


def count(kind, message):
    return sum(1 for ev in events if ev.get("type") == kind and ev.get("message") == message)


print(f"runtime-mpc-skip {count('Info', 'MPC_GolmokWeather missing - skipped')}")
print(f"runtime-ns-skip {count('Info', 'NS_GolmokRain missing - skipped')}")
print(f"runtime-ns-executed {count('Info', 'NS_GolmokRain present: EXECUTED')}")
print(f"runtime-errors {sum(1 for ev in events if ev.get('type') == 'Error')}")
with open(sys.argv[2], "w", encoding="utf-8") as f:
    for ev in events:
        f.write(f"{ev.get('type')}\t{ev.get('message')}\n")
with open(sys.argv[3], "w", encoding="utf-8") as f:
    for ev in events:
        if ev.get("type") == "Warning" and ev.get("message") not in KNOWN:
            f.write(f"{ev.get('message')}\n")
```

```sh j25-testlog-sh
#!/bin/sh
# J-25: fixed facts in the editor log copy of one test.sh run (usage: sh j25_testlog.sh <log> <filter>), one "label value" per line.
G=$1
F=$2
c() { printf '%s %s\n' "$1" "$2"; }
yn() { if "$@"; then echo yes; else echo no; fi; }
c cmdline "$(grep -F 'Command Line: ' "$G" | grep -c -F -- "-ExecCmds=\"Automation RunTests $F;Quit\"")"
c mpc-missing "$(grep -c -F 'weather: MPC missing (' "$G")"
c fx-missing "$(grep -c -F 'weather: rain fx missing (' "$G")"
c start-mpc-missing "$(grep -c -F ', mpc missing, fx ' "$G")"
c start-mpc-ok "$(yn grep -q -F ', 10 schedule slots, mpc ok, fx missing' "$G")"
```

```sh j25-cleanup-sh
#!/bin/sh
# J-25: moves the generated MPC out of the worktree (usage: sh j25_cleanup.sh <W> <E>), one "label value" per line. Deletes no file.
W=$1
E=$2
D="$W/unreal/Golmok/Content/Golmok/Weather"
A="$D/MPC_GolmokWeather.uasset"
if [ -e "$E/asset/MPC_GolmokWeather.uasset" ]; then
  echo "moved target-exists"
elif [ -f "$A" ]; then
  if mkdir -p "$E/asset" && mv "$A" "$E/asset/MPC_GolmokWeather.uasset"; then echo "moved yes"; else echo "moved failed"; fi
else
  echo "moved no"
fi
if [ -d "$D" ]; then
  n=$(ls -A "$D" | wc -l | tr -d ' ')
  echo "left $n"
  if [ "$n" = 0 ] && rmdir "$D"; then echo "rmdir yes"; else echo "rmdir no"; fi
else
  echo "left none"
  echo "rmdir none"
fi
if [ -e "$D" ]; then echo "weather-dir yes"; else echo "weather-dir no"; fi
```

```sh j25-cell-sh
#!/bin/sh
# J-25: prints the pc-verify-wp16a section 12 row 9 result cell (usage: sh j25_cell.sh <E>), one line, no "|".
E=$1
date=$(cat "$E/run-date.log")
sha=$(cat "$E/sha.log")
case "$(cat "$E/branch.log")" in
A) printf 'Mac 헤드리스(J-25, %s, SHA %s, `UnrealEditor-Cmd -nullrhi` 편집기): Python으로 쓸 수 있었다 — 첫 실행 `created (RainIntensity, Wetness, PuddleAmount, default 0)`, 새 편집기 프로세스의 둘째 실행 `ok (RainIntensity, Wetness, PuddleAmount, default 0)`(에셋 파일 바뀜 없음), 셋째 프로세스의 읽기에서 스칼라 3개(이 순서, 기본값 0)·벡터 0개. GUI Output Log 실행은 [미확인]. 에셋은 커밋하지 않았다. 근거: J-25 PR.\n' "$date" "$sha" ;;
B) printf 'Mac 헤드리스(J-25, %s, SHA %s, `UnrealEditor-Cmd -nullrhi` 편집기): Python으로 쓰지 못했다 — 첫 실행이 `created but scalar_parameters not writable from Python (`로 시작하는 Error를 냈다(예외 원문은 PR 본문). 만든 에셋은 커밋하지 않았고 §2a 수동 절차(GUI)는 하지 않았다. 근거: J-25 PR.\n' "$date" "$sha" ;;
*) exit 3 ;;
esac
```

```sh j25-line-sh
#!/bin/sh
# J-25: prints a blank line and the "Mac 부분 선행" line for pc-verify-wp16a section 13, branch A only (usage: sh j25_line.sh <E>).
E=$1
[ "$(cat "$E/branch.log")" = A ] || exit 3
date=$(cat "$E/run-date.log")
sha=$(cat "$E/sha.log")
nr=$(wc -l < "$E/unknown-warn-runtime.log" | tr -d ' ')
nw=$(wc -l < "$E/unknown-warn-weather.log" | tr -d ' ')
printf '\n'
printf 'Mac 부분 선행(J-25, MPC만 있음(헤드리스 생성, 커밋 안 함), NS 없음, %s, SHA %s): §2a — `weather_setup.run()`이 두 편집기 프로세스에서 `created` 다음 `ok`, 스칼라 3개 기본값 0·벡터 0(§12 #9). §3 — `test.sh --filter Golmok.Weather.Runtime`과 `--filter Golmok.Weather` 모두 종료 코드 0, failed 0. Weather.Runtime은 MPC 단계 완료(`MPC_GolmokWeather missing - skipped` 0줄, MPC 인스턴스 값 단언 포함 실패 0 — `-nullrhi`, §12 #10의 첫 관찰), NS 단계 skip(`NS_GolmokRain missing - skipped` 1줄). 알려진 것 밖의 Runtime Warning은 두 실행에서 %s건·%s건(원문은 PR 본문). 에셋 창의 값·수정 표시(*)와 §2b 뒤 `mpc ok, fx idle`은 [미확인]. 근거: J-25 PR.\n' "$date" "$sha" "$nr" "$nw"
```

```text j25-expected-logcheck-1
cmdline 1
created 1
ok 0
created-but 0
not-writable 0
not-modified 0
keeps-more 0
ns-missing 1
python-error 0
traceback 0
j25-created 1
j25-ok 0
j25-created-problem 0
j25-exception 0
```

```text j25-expected-logcheck-2
cmdline 1
created 0
ok 1
created-but 0
not-writable 0
not-modified 0
keeps-more 0
ns-missing 1
python-error 0
traceback 0
j25-created 0
j25-ok 1
j25-created-problem 0
j25-exception 0
```

```text j25-expected-logcheck-rb
cmdline 1
created 0
ok 0
created-but 0
not-writable 0
not-modified 0
keeps-more 0
ns-missing 0
python-error 0
traceback 0
j25-created 0
j25-ok 0
j25-created-problem 0
j25-exception 0
```

```text j25-expected-readback
j25_readback: exists True
j25_readback: is-mpc True
j25_readback: scalar 0 RainIntensity 0
j25_readback: scalar 1 Wetness 0
j25_readback: scalar 2 PuddleAmount 0
j25_readback: counts scalars 3 vectors 0
j25_readback: done
```

```text j25-expected-report-runtime
tests 1
failed 0
notrun 0
state Golmok.Weather.Runtime Success
runtime-mpc-skip 0
runtime-ns-skip 1
runtime-ns-executed 0
runtime-errors 0
```

```text j25-expected-report-weather
tests 3
failed 0
notrun 0
state Golmok.Weather.Config Success
state Golmok.Weather.Lighting Success
state Golmok.Weather.Runtime Success
runtime-mpc-skip 0
runtime-ns-skip 1
runtime-ns-executed 0
runtime-errors 0
```

```text j25-expected-testlog
cmdline 1
mpc-missing 0
fx-missing 1
start-mpc-missing 0
start-mpc-ok yes
```

```text j25-expected-cleanup
moved yes
left 0
rmdir yes
weather-dir no
```

```text j25-row9-before
| 9 | `weather_setup.py` | MPC `scalar_parameters`·`CollectionScalarParameter` Python 쓰기 | 속성 쓰기 허용 | §2a 수동 절차 | |
```

- **명령 공통**: 셸 변수는 Bash 호출 사이에 남지 않는다. 그래서 **모든 명령은 `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/jaehwan/J-25";`로 시작하고**, 그 뒤는 `cd "$W" &&`·`cd "$W/tools" &&`·`git -C "$W"`·`"$E/…"` 절대 경로로 시작한다(상시 규칙). 아래 명령에는 이 앞머리를 적지 않았다. 돌린 명령 원문은 `"$E/commands.txt"`에 한 줄씩 더한다(규칙 10·19 — 더하기만, heredoc 금지). 각 단계의 "기대"와 다르면 **멈춤 조건**을 본다. 할 일 2(`build.sh`)·3·4(편집기)·5·6(`test.sh`)의 UE 명령과 할 일 9·10의 게이트·`gh pr checks --watch`는 **항상** 하네스의 백그라운드 실행으로 돌리고, 그 명령이 쓰는 `.rc` 파일(`gh pr checks --watch`는 `checks-watch.log`의 `exit=` 줄)이 생길 때까지 기다린다(명령은 바꾸지 않는다). 그 밖의 명령은 앞쪽(foreground)으로 돌린다. 편집기 명령의 `UE` 경로는 `"/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor-Cmd"`이고, 아래 명령에 그대로 적혀 있다. **시간 한도(2026-11-28 문서 9, 규칙 5)**: 이 절에서 `/usr/bin/timeout` 없이 적힌 네트워크 명령은 할 일의 `git fetch`·`gh pr list`·`git push` 두 번·`gh pr create`·`gh pr view` 다섯 가지다 — 적힌 그대로 쓰고(시간 한도를 더하거나 빼지 않는다), 점검표 규칙 5 줄에서 `not-wrapped` 무리로 적는다(상시 규칙 "PR 본문 공통" 3의 감사). 그 소절 6의 `gh pr edit`·`gh pr view`도 같다. 그 밖의 대기 명령(`build.sh`·`test.sh`·편집기·게이트·등록 대기·`gh pr checks` 두 명령)에는 `/usr/bin/timeout`이 붙어 있다.
  - **GUI 잠금**(할 일 2~7, [mac-setup §3](../runbooks/mac-setup.md) 표의 규칙, 목적 `J-25-headless` — J-23 보충 ④와 같은 꼴): 확인 `L="$TMPDIR/claude/gui-foreground.lock"; if [ -e "$L" ]; then cat "$L"; else echo "no lock"; fi > "$E/lock-check.log"; date -u +%FT%TZ >> "$E/lock-check.log"` — 기대 첫 줄 `no lock`. 다른 줄이 있으면 **지우지 않고** 그 줄을 영록에게 보내고 기다린다. 잡기 `mkdir -p "$TMPDIR/claude" && (set -C; printf '%s %s %s\n' "재환" "J-25-headless" "$(date -u +%FT%TZ)" > "$TMPDIR/claude/gui-foreground.lock"); echo $? > "$E/lock-take.rc"` — 기대 `0`. 풀기(할 일 7의 **맨 끝**) `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-25-headless ' "$L" && rm "$L"; echo $? > "$E/lock-release.rc"` — 기대 `0`.
  - **잠금 갱신**([AGENTS.md](../../AGENTS.md) "UE를 같이 쓰는 규칙"·mac-setup §3: 20분이 지난 기록은 빈 것으로 본다): ① UE 명령 바로 앞에 매번 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-25-headless ' "$L" && printf '%s %s %s\n' "재환" "J-25-headless" "$(date -u +%FT%TZ)" > "$L"; echo $? > "$E/lock-refresh-<n>.rc"` — `<n>`은 할 일 2 `build`, 3 `gen-1`, 4 `gen-2`·`rb`, 5 `test-runtime`, 6 `test-weather`. 기대 `0`. 0이 아니면 잠금 파일을 지우거나 쓰지 않고 멈춘다. ② UE 명령은 갱신 루프로 감싸 **적힌 그대로** 돌린다(아래 명령에 이미 들어 있다): 앞 `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-25-headless ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-25-headless" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!;`, 끝 `; kill "$RP"`.
- **할 일**:
  1. **준비**: `mkdir -p "$E" && git -C "$W" status --porcelain > "$E/status-before.log"; grep -c -v '^?? ' "$E/status-before.log" > "$E/status-before-tracked.log"` — 기대 `0`(`??` 줄은 그대로 둔다 — 2026-11-28 `$W`에는 J-18의 `?? unreal/Golmok/Content/Golmok/Materials/`가 있다). `git -C "$W" fetch origin && git -C "$W" switch -c local/jaehwan-j25-mpc-headless origin/main > "$E/switch.log" 2>&1; echo $? > "$E/switch.rc"` — 기대 `0`. `git -C "$W" rev-parse --short HEAD > "$E/sha.log"; git -C "$W" rev-parse HEAD origin/main | uniq | wc -l | tr -d ' ' > "$E/sha-same.log"` — 기대 `1`. 과제 절: `git -C "$W" show origin/main:docs/plan/jaehwan-tasks.md > "$E/tasks-main.md"; git -C "$W" rev-parse origin/main > "$E/main-rev.log"; { awk '/^#### J-25 /{f=1} /^#### J-26/{f=0} f' "$E/tasks-main.md"; awk '/^### PR 본문 공통\(모든 과제\)$/{f=1} /^## 리뷰·병합 절차$/{f=0} f' "$E/tasks-main.md"; } > "$E/task.txt"`(규칙 14·17 c, 상시 규칙 "PR 본문 공통" 1) — 기대 `head -1 "$E/task.txt"`가 `#### J-25 `로 시작, `grep -c -x '### PR 본문 공통(모든 과제)' "$E/task.txt"` `1`. 펜스 추출(손으로 옮기지 않는다): `printf '%s\n' "j25-run-py j25_run.py" "j25-readback-py j25_readback.py" "j25-logcheck-sh j25_logcheck.sh" "j25-branch-sh j25_branch.sh" "j25-report-py j25_report.py" "j25-testlog-sh j25_testlog.sh" "j25-cleanup-sh j25_cleanup.sh" "j25-cell-sh j25_cell.sh" "j25-line-sh j25_line.sh" "common-ph-awk ph.awk" "j25-expected-logcheck-1 expected-logcheck-1.txt" "j25-expected-logcheck-2 expected-logcheck-2.txt" "j25-expected-logcheck-rb expected-logcheck-rb.txt" "j25-expected-readback expected-readback.txt" "j25-expected-report-runtime expected-report-runtime.txt" "j25-expected-report-weather expected-report-weather.txt" "j25-expected-testlog expected-testlog.txt" "j25-expected-cleanup expected-cleanup.txt" "j25-row9-before row9-before.txt" | while read -r n f; do awk -v n="$n" 'BEGIN {b = sprintf("%c%c%c", 96, 96, 96)} $0 == b && x {x=0} x {print} $0 ~ ("^" b "[a-z]+ " n "$") {x=1}' "$E/task.txt" > "$E/$f"; done; cd "$E" && wc -l j25_run.py j25_readback.py j25_logcheck.sh j25_branch.sh j25_report.py j25_testlog.sh j25_cleanup.sh j25_cell.sh j25_line.sh ph.awk expected-logcheck-1.txt expected-logcheck-2.txt expected-logcheck-rb.txt expected-readback.txt expected-report-runtime.txt expected-report-weather.txt expected-testlog.txt expected-cleanup.txt row9-before.txt > "$E/extract-wc.log"`(2026-11-28 문서 9: 백틱 세 개를 `sprintf`로 만드는 꼴로 바꿨다 — 뽑는 결과는 같다) — 기대(앞 숫자, 순서대로): `16`, `18`, `20`, `11`, `36`, `11`, `22`, `10`, `10`, `37`, `14`, `14`, `14`, `7`, `8`, `10`, `5`, `4`, `1`, 끝 줄 `268 total`. 겹침: `cd "$W" && gh pr list --state open --json number,headRefName,files --jq '.[]|select(any(.files[]; .path=="docs/runbooks/pc-verify-wp16a.md"))|"\(.number) \(.headRefName)"' > "$E/overlap.log" 2>&1` — 기대 빈 파일. 같은 프로젝트의 편집기·패키지 앱이 없어야 한다: `pgrep -fl '[g]olmok-jaehwan/(unreal/Golmok/Golmok\.uproject|build/Mac/Golmok\.app/)' > "$E/ue-before.log"; echo $? > "$E/ue-before.rc"` — 기대 rc `1`. 전제: `{ test -e "$W/unreal/Golmok/Content/Golmok/Weather"; echo "weather-dir=$?"; find "$W/unreal/Golmok/Content" -name 'MPC_GolmokWeather*' | wc -l | tr -d ' '; test -f "$W/unreal/Golmok/Content/Golmok/Maps/L_Dev.umap"; echo "l_dev=$?"; cd "$W" && grep -c '^Mac 부분 선행(J-20, ' docs/runbooks/pc-verify-wp16a.md; grep -c '^Mac 부분 선행(J-21, ' docs/runbooks/pc-verify-wp16a.md; grep -c '^Mac 부분 선행(J-22, ' docs/runbooks/pc-verify-wp16a.md; grep -c '^Mac 부분 선행(J-25, ' docs/runbooks/pc-verify-wp16a.md; grep -c -x -F -f "$E/row9-before.txt" docs/runbooks/pc-verify-wp16a.md; } > "$E/pre.log"` — 기대 여덟 줄 `weather-dir=1`·`0`·`l_dev=0`·`1`·`1`·`1`·`0`·`1`. LFS 속성(에셋이 생기기 전, 기록): `cd "$W" && git check-attr filter lockable -- unreal/Golmok/Content/Golmok/Weather/MPC_GolmokWeather.uasset > "$E/check-attr.log"; git check-ignore -q unreal/Golmok/Content/Golmok/Weather/MPC_GolmokWeather.uasset; echo "ignored=$?" >> "$E/check-attr.log"` — 기대 세 줄 `unreal/Golmok/Content/Golmok/Weather/MPC_GolmokWeather.uasset: filter: lfs`·`unreal/Golmok/Content/Golmok/Weather/MPC_GolmokWeather.uasset: lockable: set`·`ignored=1`(이 파일은 무시되지 않는 lockable LFS 경로다 — 설계 6).
  2. **빌드**: GUI 잠금 확인·잡기. 잠금 갱신 ①(`build`). `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-25-headless ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-25-headless" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && /usr/bin/timeout 1800 ./tools/ue/build.sh > "$E/build.log" 2>&1; echo $? > "$E/build.rc"; kill "$RP"` — 기대 `build.rc` `0`.
  3. **첫 실행(만들기)**: 잠금 갱신 ①(`gen-1`). `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-25-headless ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-25-headless" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && touch "$E/gen-1-marker" && sleep 1 && date +%F > "$E/run-date.log" && /usr/bin/timeout 900 "/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor-Cmd" "$W/unreal/Golmok/Golmok.uproject" "-ExecCmds=py $E/j25_run.py,QUIT_EDITOR" -unattended -nullrhi -nosplash -nopause -nosound > "$E/gen-1.log" 2>&1; echo $? > "$E/gen-1.rc"; kill "$RP"; cp "$HOME/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log" "$E/gen-1-editor.log"; [ "$HOME/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log" -nt "$E/gen-1-marker" ]; echo "newer=$?" > "$E/gen-1-new.log"`(`run-date.log`는 칸·줄의 날짜 — Mac의 현지 날짜) — 기대 `gen-1.rc` `0`(124 = 시간 초과 — 멈춤), `gen-1-new.log` `newer=0`. 판정: `sh "$E/j25_logcheck.sh" "$E/gen-1-editor.log" j25_run.py > "$E/logcheck-1.log"; sh "$E/j25_branch.sh" "$E" > "$E/branch.log"` — 기대 `branch.log`가 `A` 또는 `B`(`stop`이면 멈춤). 기록만: `grep -E 'LogPython: (Warning: |Error: )?(weather_setup|j25_run): ' "$E/gen-1-editor.log" > "$E/gen-1-lines.log"`. 에셋: `A="$W/unreal/Golmok/Content/Golmok/Weather/MPC_GolmokWeather.uasset"; (cd "$W/unreal/Golmok/Content/Golmok/Weather" && ls -ln MPC_GolmokWeather.uasset) > "$E/asset-ls-1.log" 2>&1; shasum -a 256 "$A" | cut -d' ' -f1 > "$E/asset-sha-1.log"; ls -A "$W/unreal/Golmok/Content/Golmok/Weather" > "$E/weather-dir-1.log"` — 기대 `weather-dir-1.log` 한 줄 `MPC_GolmokWeather.uasset`, `asset-sha-1.log` 64자 한 줄. 상태: `git -C "$W" status --porcelain > "$E/status-run1.log"; grep -c -x -F '?? unreal/Golmok/Content/Golmok/Weather/' "$E/status-run1.log" > "$E/status-run1-weather.log"; grep -v -x -F '?? unreal/Golmok/Content/Golmok/Weather/' "$E/status-run1.log" | diff "$E/status-before.log" - > "$E/status-run1.diff"; echo "exit=$?" >> "$E/status-run1.diff"` — 기대 `status-run1-weather.log` `1`, `status-run1.diff` `exit=0` 한 줄(에셋은 추적되지 않은 폴더 하나로만 보인다). **분기 B면 할 일 4~6을 건너뛰고 할 일 7로 간다.**
  4. **둘째 실행(다시 띄운 편집기)과 읽기(A만)**: 잠금 갱신 ①(`gen-2`). `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-25-headless ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-25-headless" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && touch "$E/gen-2-marker" && sleep 1 && /usr/bin/timeout 900 "/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor-Cmd" "$W/unreal/Golmok/Golmok.uproject" "-ExecCmds=py $E/j25_run.py,QUIT_EDITOR" -unattended -nullrhi -nosplash -nopause -nosound > "$E/gen-2.log" 2>&1; echo $? > "$E/gen-2.rc"; kill "$RP"; cp "$HOME/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log" "$E/gen-2-editor.log"; [ "$HOME/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log" -nt "$E/gen-2-marker" ]; echo "newer=$?" > "$E/gen-2-new.log"` — 기대 `gen-2.rc` `0`, `newer=0`. 판정: `sh "$E/j25_logcheck.sh" "$E/gen-2-editor.log" j25_run.py > "$E/logcheck-2.log"; diff "$E/expected-logcheck-2.txt" "$E/logcheck-2.log" > "$E/logcheck-2.diff"; echo "exit=$?" >> "$E/logcheck-2.diff"; grep -E 'LogPython: (Warning: |Error: )?(weather_setup|j25_run): ' "$E/gen-2-editor.log" > "$E/gen-2-lines.log"; shasum -a 256 "$W/unreal/Golmok/Content/Golmok/Weather/MPC_GolmokWeather.uasset" | cut -d' ' -f1 > "$E/asset-sha-2.log"` — 기대 `exit=0` 한 줄. 잠금 갱신 ①(`rb`). 읽기: `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-25-headless ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-25-headless" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && touch "$E/rb-marker" && sleep 1 && /usr/bin/timeout 900 "/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor-Cmd" "$W/unreal/Golmok/Golmok.uproject" "-ExecCmds=py $E/j25_readback.py,QUIT_EDITOR" -unattended -nullrhi -nosplash -nopause -nosound > "$E/rb.log" 2>&1; echo $? > "$E/rb.rc"; kill "$RP"; cp "$HOME/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log" "$E/rb-editor.log"; [ "$HOME/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log" -nt "$E/rb-marker" ]; echo "newer=$?" > "$E/rb-new.log"` — 기대 `rb.rc` `0`, `newer=0`. 판정: `sh "$E/j25_logcheck.sh" "$E/rb-editor.log" j25_readback.py > "$E/logcheck-rb.log"; diff "$E/expected-logcheck-rb.txt" "$E/logcheck-rb.log" > "$E/logcheck-rb.diff"; echo "exit=$?" >> "$E/logcheck-rb.diff"; grep -o 'j25_readback: .*$' "$E/rb-editor.log" | tr -d '\r' > "$E/readback.log"; diff "$E/expected-readback.txt" "$E/readback.log" > "$E/readback.diff"; echo "exit=$?" >> "$E/readback.diff"; shasum -a 256 "$W/unreal/Golmok/Content/Golmok/Weather/MPC_GolmokWeather.uasset" | cut -d' ' -f1 > "$E/asset-sha-rb.log"` — 기대 두 `diff` 모두 `exit=0` 한 줄.
  5. **테스트 1 — `Golmok.Weather.Runtime`(A만)**: 잠금 갱신 ①(`test-runtime`). `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-25-headless ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-25-headless" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && touch "$E/test-runtime-marker" && sleep 1 && /usr/bin/timeout 2700 ./tools/ue/test.sh --filter Golmok.Weather.Runtime > "$E/test-runtime.log" 2>&1; echo $? > "$E/test-runtime.rc"; kill "$RP"; cp "$W/unreal/Golmok/Saved/Automation/Report/index.json" "$E/index-runtime.json"; echo $? > "$E/index-runtime-cp.rc"; [ "$W/unreal/Golmok/Saved/Automation/Report/index.json" -nt "$E/test-runtime-marker" ]; echo "newer=$?" > "$E/index-runtime-new.log"; cp "$HOME/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log" "$E/test-runtime-editor.log"` — 기대 `test-runtime.rc` `0`, `index-runtime-cp.rc` `0`, `newer=0`. 판정: `"$W/tools/.venv/bin/python" -I "$E/j25_report.py" "$E/index-runtime.json" "$E/entries-runtime.tsv" "$E/unknown-warn-runtime.log" > "$E/report-runtime.log"; diff "$E/expected-report-runtime.txt" "$E/report-runtime.log" > "$E/report-runtime.diff"; echo "exit=$?" >> "$E/report-runtime.diff"; sh "$E/j25_testlog.sh" "$E/test-runtime-editor.log" Golmok.Weather.Runtime > "$E/testlog-runtime.log"; diff "$E/expected-testlog.txt" "$E/testlog-runtime.log" > "$E/testlog-runtime.diff"; echo "exit=$?" >> "$E/testlog-runtime.diff"; shasum -a 256 "$W/unreal/Golmok/Content/Golmok/Weather/MPC_GolmokWeather.uasset" | cut -d' ' -f1 > "$E/asset-sha-t1.log"` — 기대 두 `diff` 모두 `exit=0` 한 줄. `entries-runtime.tsv`·`unknown-warn-runtime.log`는 판정하지 않는다(PR 본문 원문).
  6. **테스트 2 — `Golmok.Weather`(A만)**: 잠금 갱신 ①(`test-weather`). `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-25-headless ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-25-headless" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; cd "$W" && touch "$E/test-weather-marker" && sleep 1 && /usr/bin/timeout 2700 ./tools/ue/test.sh --filter Golmok.Weather > "$E/test-weather.log" 2>&1; echo $? > "$E/test-weather.rc"; kill "$RP"; cp "$W/unreal/Golmok/Saved/Automation/Report/index.json" "$E/index-weather.json"; echo $? > "$E/index-weather-cp.rc"; [ "$W/unreal/Golmok/Saved/Automation/Report/index.json" -nt "$E/test-weather-marker" ]; echo "newer=$?" > "$E/index-weather-new.log"; cp "$HOME/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log" "$E/test-weather-editor.log"` — 기대 `test-weather.rc` `0`, `index-weather-cp.rc` `0`, `newer=0`. 판정: `"$W/tools/.venv/bin/python" -I "$E/j25_report.py" "$E/index-weather.json" "$E/entries-weather.tsv" "$E/unknown-warn-weather.log" > "$E/report-weather.log"; diff "$E/expected-report-weather.txt" "$E/report-weather.log" > "$E/report-weather.diff"; echo "exit=$?" >> "$E/report-weather.diff"; sh "$E/j25_testlog.sh" "$E/test-weather-editor.log" Golmok.Weather > "$E/testlog-weather.log"; diff "$E/expected-testlog.txt" "$E/testlog-weather.log" > "$E/testlog-weather.diff"; echo "exit=$?" >> "$E/testlog-weather.diff"; shasum -a 256 "$W/unreal/Golmok/Content/Golmok/Weather/MPC_GolmokWeather.uasset" | cut -d' ' -f1 > "$E/asset-sha-t2.log"` — 기대 두 `diff` 모두 `exit=0` 한 줄. 기록만: `grep -o 'NightUnaffected at [^"]*' "$E/index-weather.json" > "$E/night-weather.log"; tail -n 1 "$E/test-runtime.log" > "$E/summary-runtime.log"; tail -n 1 "$E/test-weather.log" > "$E/summary-weather.log"`.
  7. **정리(A·B 모두, 잠금은 맨 끝에 푼다)**: `pgrep -fl '[g]olmok-jaehwan/(unreal/Golmok/Golmok\.uproject|build/Mac/Golmok\.app/)' > "$E/ue-after.log"; echo $? > "$E/ue-after.rc"` — 기대 rc `1`(편집기가 남았으면 아래 "멈춤 순서" ②). 옮기기: `sh "$E/j25_cleanup.sh" "$W" "$E" > "$E/cleanup.log"; diff "$E/expected-cleanup.txt" "$E/cleanup.log" > "$E/cleanup.diff"; echo "exit=$?" >> "$E/cleanup.diff"` — 기대 `exit=0` 한 줄(이 명령은 한 번만 — 두 번째는 `moved target-exists`). `shasum -a 256 "$E/asset/MPC_GolmokWeather.uasset" | cut -d' ' -f1 > "$E/asset-sha-moved.log"; cat "$E"/asset-sha-*.log | sort -u | wc -l | tr -d ' ' > "$E/asset-unique-count.log"` — 기대 `1`(A는 여섯 파일, B는 두 파일이 같은 값). `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-clean.diff"; echo "exit=$?" >> "$E/status-clean.diff"` — 기대 `exit=0` 한 줄. 잠금 풀기.
  8. **런북**: 칸: `sh "$E/j25_cell.sh" "$E" > "$E/cell9.txt"; echo $? > "$E/cell.rc"; printf '%s %s |\n' "$(sed 's/ |$//' "$E/row9-before.txt")" "$(cat "$E/cell9.txt")" > "$E/row9-after.txt"` — 기대 `cell.rc` `0`, `wc -l < "$E/cell9.txt" | tr -d ' '` `1`, `grep -c '|' "$E/cell9.txt"` `0`. 바꾸기(손으로 옮기지 않는다): `cd "$W" && awk -v bf="$E/row9-before.txt" -v af="$E/row9-after.txt" 'BEGIN{getline b < bf; getline a < af} $0 == b {print a; n++; next} {print} END{if (n != 1) exit 3}' docs/runbooks/pc-verify-wp16a.md > "$E/wp16a-new.md"; echo $? > "$E/cell-awk.rc"` — 기대 `0`(3 = #9 행이 하나가 아니다 — 멈춤). 그다음에만 `cp "$E/wp16a-new.md" "$W/docs/runbooks/pc-verify-wp16a.md"; echo $? > "$E/cell-cp.rc"` — 기대 `0`. 확인: `cd "$W" && grep -c -x -F -f "$E/row9-after.txt" docs/runbooks/pc-verify-wp16a.md` `1`, `cd "$W" && grep -c -x -F -f "$E/row9-before.txt" docs/runbooks/pc-verify-wp16a.md` `0`. **분기 A만** 줄: `sh "$E/j25_line.sh" "$E" > "$E/line25.txt"; echo $? > "$E/line.rc"` — 기대 rc `0`, `wc -l < "$E/line25.txt" | tr -d ' '` `2`, `head -n 1 "$E/line25.txt" | grep -c -x ''` `1`. `cd "$W" && sed -i '' "/^Mac 부분 선행(J-22, /r $E/line25.txt" docs/runbooks/pc-verify-wp16a.md; echo $? > "$E/line-insert.rc"` — 기대 `0`(한 번만). 확인: `cd "$W" && awk '/^Mac 부분 선행\(J-22, /{getline a; getline b; print a; print b}' docs/runbooks/pc-verify-wp16a.md | diff - "$E/line25.txt" > "$E/line-diff.log"; echo "exit=$?" >> "$E/line-diff.log"` — 기대 `exit=0` 한 줄, `cd "$W" && grep -c '^Mac 부분 선행(J-25, ' docs/runbooks/pc-verify-wp16a.md` `1`. 칸 자기 검사(규칙 17 b, 상시 규칙 "PR 본문 공통" 7, 번호 `1`): `cd "$W" && git diff -U0 origin/main -- docs/runbooks/pc-verify-wp16a.md | grep '^+[^+]' > "$E/cell-lines-1.txt"; wc -l < "$E/cell-lines-1.txt" | tr -d ' ' > "$E/cell-lines-1-count.log"; grep -n -E '\.log|영록|R[0-9]{3}' "$E/cell-lines-1.txt" > "$E/cell-grep-1.log"; wc -l < "$E/cell-grep-1.log" | tr -d ' ' > "$E/cell-grep-1-count.log"` — 기대 `cell-lines-1-count.log` A `2`·B `1`, `cell-grep-1-count.log` `0`(0이 아니면 손으로 고치지 않고 멈춘다). `cd "$W" && git diff --numstat -- docs/runbooks/pc-verify-wp16a.md | tr '\t' ' '` — 기대 A `3 1 docs/runbooks/pc-verify-wp16a.md`, B `1 1 docs/runbooks/pc-verify-wp16a.md`. `git -C "$W" status --porcelain > "$E/status-after.log"; grep -v -x -F ' M docs/runbooks/pc-verify-wp16a.md' "$E/status-after.log" | diff "$E/status-before.log" - > "$E/status.diff"; echo "exit=$?" >> "$E/status.diff"` — 기대 `exit=0` 한 줄.
  9. **게이트·커밋 1·push·PR**: `cd "$W/tools" && source .venv/bin/activate && { /usr/bin/timeout 300 ruff check . && /usr/bin/timeout 300 ruff format --check . && /usr/bin/timeout 1800 pytest -q && /usr/bin/timeout 300 python scripts/check_repo.py; } > "$E/gate-1.log" 2>&1; echo $? > "$E/gate-1.rc"`(하네스 백그라운드) — 기대 `0`(124 = 시간 초과, 다시 돌리지 않고 멈춤). `[ "$E/gate-1.log" -nt "$W/docs/runbooks/pc-verify-wp16a.md" ]; echo "newer=$?" > "$E/mtime-1.log"` — 기대 `newer=0`. 커밋: `cd "$W" && git add docs/runbooks/pc-verify-wp16a.md && git diff --cached --name-only > "$E/c1-files.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-25: pc-verify-wp16a — V-16 §2a MPC 헤드리스 생성 시험 기록(§12 #9 칸, 분기 A면 §13 줄)" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c1-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-1.log"` — 기대 `c1-files.log` 한 줄 `docs/runbooks/pc-verify-wp16a.md`(규칙 6 — `.uasset`이 있으면 커밋하지 않고 멈춘다), `author-1.log` `재환 <jaehwan.local@localhost>`. `git -C "$W" push -u origin local/jaehwan-j25-mpc-headless > "$E/push-1.log" 2>&1; echo "exit=$?" >> "$E/push-1.log"` — 기대 끝 줄 `exit=0`. PR 열기(첫 본문은 이 한 문장뿐 — 상시 규칙 "PR 본문 공통" 2, 규칙 2; 2026-11-28 문서 9 검증 지적: 옛 일곱 줄 꼴을 이 한 줄로 바꿨다, dry-run sh·zsh 모두 한 줄 `CI 진행 중 — 결과는 아래에 추가`): `printf '%s\n' 'CI 진행 중 — 결과는 아래에 추가' > "$E/pr-body-initial.md"; cd "$W" && gh pr create --base main --head local/jaehwan-j25-mpc-headless --title "J-25: V-16 §2a MPC_GolmokWeather 헤드리스 생성 시험(커밋 없음)" --body-file "$E/pr-body-initial.md" > "$E/pr-create.log" 2>&1; echo $? > "$E/pr-create.rc"` — 기대 `0`. `cd "$W" && gh pr view local/jaehwan-j25-mpc-headless --json number --jq .number > "$E/pr-number.log" 2> "$E/pr-number.err"` — 기대 `grep -c -x '[0-9][0-9]*' "$E/pr-number.log"` `1`, `wc -l < "$E/pr-number.log" | tr -d ' '` `1`.
  10. **커밋 2(PR 번호)·push·CI**: `N=$(cat "$E/pr-number.log"); sed "s/ 근거: J-25 PR\. |\$/ 근거: PR #$N. |/" "$E/row9-after.txt" > "$E/row9-final.txt"; if [ "$(cat "$E/branch.log")" = A ]; then sed "s/ 근거: J-25 PR\.\$/ 근거: PR #$N./" "$E/line25.txt" > "$E/line25-final.txt"; fi; cd "$W" && sed -i '' -e "s/ 근거: J-25 PR\. |\$/ 근거: PR #$N. |/" -e "s/ 근거: J-25 PR\.\$/ 근거: PR #$N./" docs/runbooks/pc-verify-wp16a.md; echo $? > "$E/marker-pr.rc"` — 기대 `0`. 확인: `cd "$W" && grep -c -x -F -f "$E/row9-final.txt" docs/runbooks/pc-verify-wp16a.md` `1`, `cd "$W" && grep -c '근거: J-25 PR\.' docs/runbooks/pc-verify-wp16a.md` `0`, `cd "$W" && grep -c "근거: PR #$(cat "$E/pr-number.log")\." docs/runbooks/pc-verify-wp16a.md` A `2`·B `1`, 분기 A만 `cd "$W" && awk '/^Mac 부분 선행\(J-22, /{getline a; getline b; print a; print b}' docs/runbooks/pc-verify-wp16a.md | diff - "$E/line25-final.txt" > "$E/line-final-diff.log"; echo "exit=$?" >> "$E/line-final-diff.log"` `exit=0` 한 줄. 칸 자기 검사(번호 `2`): 할 일 8의 칸 자기 검사에서 `-1`을 `-2`로 바꾼 것 — 기대 `cell-lines-2-count.log` A `2`·B `1`, `cell-grep-2-count.log` `0`. `cd "$W" && git diff --numstat origin/main -- docs/runbooks/pc-verify-wp16a.md | tr '\t' ' '` — 기대 A `3 1 …`, B `1 1 …`. 게이트 다시(규칙 13, 하네스 백그라운드): 할 일 9의 게이트 명령에서 `gate-1`을 `gate-2`로 — 기대 `gate-2.rc` `0`, `[ "$E/gate-2.log" -nt "$W/docs/runbooks/pc-verify-wp16a.md" ]; echo "newer=$?" > "$E/mtime-2.log"` `newer=0`. 커밋: `cd "$W" && git add docs/runbooks/pc-verify-wp16a.md && git diff --cached --name-only > "$E/c2-files.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-25: 기록의 근거를 PR 번호로" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c2-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-2.log"` — 기대 `c2-files.log`·`author-2.log`는 커밋 1과 같은 값. `git -C "$W" push > "$E/push-2.log" 2>&1; echo "exit=$?" >> "$E/push-2.log"` — 기대 끝 줄 `exit=0`. `git -C "$W" diff --name-only origin/main...HEAD > "$E/branch-files.log"` — 기대 한 줄 `docs/runbooks/pc-verify-wp16a.md`. `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-final.diff"; echo "exit=$?" >> "$E/status-final.diff"` — 기대 `exit=0` 한 줄. CI 등록 대기(하네스 백그라운드, 커밋 2의 push 뒤 — 등록 지연으로 watch가 "no checks reported"로 끝나는 것을 막는다): `H=$(git -C "$W" rev-parse HEAD); cd "$W" && /usr/bin/timeout 600 sh -c 'until [ "$(gh run list --commit "$1" --json event --jq "[.[]|select(.event==\"push\" or .event==\"pull_request\")]|length")" -ge 2 ]; do sleep 30; done' sh "$H" > "$E/run-wait.log" 2>&1; echo $? > "$E/run-wait.rc"` — 기대 `0`. CI(하네스 백그라운드, `run-wait.rc` `0` 뒤): `cd "$W" && /usr/bin/timeout 1800 gh pr checks "$(cat "$E/pr-number.log")" --watch --interval 30 > "$E/checks-watch.log" 2>&1; echo "exit=$?" >> "$E/checks-watch.log"; /usr/bin/timeout 120 gh pr checks "$(cat "$E/pr-number.log")" > "$E/checks.log" 2>&1` — 기대 모든 행 pass. 그래도 `checks-watch.log`에 `no checks reported`가 있으면 첫 두 로그는 그대로 두고 같은 두 명령을 `checks-watch-2.log`·`checks-2.log`로 한 번 더 돌린다(이 경우 `## CI`·완료 기준 (j)·멈춤 조건의 `checks.log`는 `checks-2.log`로 읽는다. 할 일 11의 대상 목록 명령과 기대 수 A `33`·B `15`는 바꾸지 않는다 — 첫 `checks.log`가 남아 있다).
  11. **PR 본문**: PR 본문·자리표시 분류·칸 자기 검사·근거 표기는 상시 규칙 "PR 본문 공통(모든 과제)"을 따른다(이 절과 다르면 그 소절을 따른다). `## 결과`에는 관찰한 값만 둔다(로그 원문은 백틱 펜스 블록에): 분기(`branch.log`), `logcheck-1.log`(A면 `logcheck-2.log`·`logcheck-rb.log`도), `gen-1-lines.log`(B면 이것이 §12 #9의 예외 원문), A면 `gen-2-lines.log`·`readback.log`·`report-runtime.log`·`report-weather.log`·`testlog-runtime.log`·`testlog-weather.log`·`summary-runtime.log`·`summary-weather.log`·`night-weather.log`, **`entries-runtime.tsv`·`entries-weather.tsv` 전체**(§12 #10의 근거 — `-nullrhi` MPC 인스턴스에 관한 Info·Warning이 있으면 여기에 원문으로 남는다), `unknown-warn-runtime.log`·`unknown-warn-weather.log`(비어 있으면 "빈 파일"), `check-attr.log`, `asset-ls-1.log`, `asset-sha-1.log`, `cleanup.log` — 과제 번호·규칙 번호·날짜는 이 절에 쓰지 않는다. `## 완료 기준 대조`는 아래 (a)~(k) 한 줄씩(물결 펜스 `~~~`). 분기 B에서 하지 않은 항목은 "해당 없음(분기 B — 설계 4)"로 쓴다. 본문 초안은 `$E/pr-body.md`. 사용자 경로 검사(공개 저장소에 사용자 이름이 든 절대 경로를 쓰지 않는다): `grep -c -F "$HOME" "$E/pr-body.md" > "$E/home-path.log"` — 기대 `0`(0이 아니면 그 줄을 `~` 기준으로 고쳐 다시 센다. 펜스 안 원문에서 걸리면 고치지 않고 멈춘다). 게시 전 검사(규칙 10 e·f) — 대상 목록은 아래 명령이 고정한다(손으로 빼거나 더하지 않는다): `printf '%s\n' build.log gen-1-editor.log gen-1-lines.log logcheck-1.log branch.log gen-2-editor.log gen-2-lines.log logcheck-2.log rb-editor.log readback.log logcheck-rb.log test-runtime.log test-weather.log report-runtime.log report-weather.log entries-runtime.tsv entries-weather.tsv unknown-warn-runtime.log unknown-warn-weather.log testlog-runtime.log testlog-weather.log night-weather.log check-attr.log asset-ls-1.log asset-sha-1.log cleanup.log cell9.txt row9-final.txt line25-final.txt sha.log run-date.log gate-2.log checks.log > "$E/check-list.txt"; while read -r f; do if [ -e "$E/$f" ]; then echo "$f"; fi; done < "$E/check-list.txt" > "$E/check-targets.txt"; while read -r f; do if [ ! -e "$E/$f" ]; then echo "$f"; fi; done < "$E/check-list.txt" > "$E/check-absent.txt"; wc -l < "$E/check-targets.txt" | tr -d ' ' > "$E/check-targets-count.log"; (cd "$E" && xargs cat < check-targets.txt) > "$E/check-corpus.txt"` — 기대 `check-targets-count.log` A `33`·B `15`, `check-absent.txt` A 빈 파일·B 18줄(할 일 4~6의 파일과 `line25-final.txt`). `check-absent.txt`의 이름은 `## 실행한 명령`의 펜스 밖 끝에 `- 분기 B라 만들지 않은 파일: ` 뒤에 `tr '\n' ' ' < "$E/check-absent.txt"`의 출력을 그대로 붙인 한 줄로 옮긴다(B만). 인용 검사: `## 결과` 절의 펜스 밖 백틱 문자열마다 그 문자열이 근거로 든 로그 **한 개**를 `"$E/quotes.tsv"`에 `문자열`(탭)`check-targets.txt의 이름 하나`로 적는다(로그 인용이 아닌 파일 이름·명령은 파일 칸에 `라벨`). 빠진 것 확인·세기와 아래 숫자 검사는 펜스 `j25-bodycheck-sh`(이 절의 허용 파일 줄 바로 앞)가 한 번에 한다(2026-11-28 문서 9: 백틱이 든 옛 인라인 명령을 글자 그대로 옮긴 스크립트 — 옛 명령과 같은 여섯 파일 `body-quotes.txt`·`tsv-quotes.txt`·`quotes-missing.log`·`quotes-check.log`·`body-numbers.txt`·`numbers-check.log`를 같은 내용으로 쓴다; 상시 규칙 "PR 본문 공통" 11·14). `quotes.tsv`를 다 쓴 뒤 뽑기·확인·실행을 한 호출로: `awk -v n=j25-bodycheck-sh 'BEGIN {b = sprintf("%c%c%c", 96, 96, 96)} x && $0 == b {x = 0} x {print} !x && index($0, b) == 1 && $0 ~ (" " n "$") {x = 1}' "$E/task.txt" > "$E/j25_bodycheck.sh"; [ "$(wc -l < "$E/j25_bodycheck.sh" | tr -d ' ')" = "11" ] && head -n 1 "$E/j25_bodycheck.sh" | grep -q -x '#!/bin/sh' && sh "$E/j25_bodycheck.sh" "$E" > "$E/bodycheck.log" 2>&1; echo $? > "$E/bodycheck.rc"` — 기대 `bodycheck.rc` `0`, `bodycheck.log` 빈 파일, `quotes-missing.log` 빈 파일. 세기는 `quotes-check.log`(`quotes.tsv` 행마다 한 행) — 기대 `cut -f1 "$E/quotes-check.log" | grep -c -x '0'`가 `0`. 숫자 검사: 위 `j25_bodycheck.sh`가 쓴 `body-numbers.txt`·`numbers-check.log`(숫자마다 한 행, 대상은 위 고정 목록) — 기대 `cut -f1 "$E/numbers-check.log" | grep -c -x '0'`가 `0`. 한 자리 숫자는 이 검사에 걸리지 않으므로 문맥 문자열(예: `runtime-mpc-skip 0`)로 인용 검사에 넣는다.
```sh j25-bodycheck-sh
#!/bin/sh
# J-25: quote and number checks of the PR draft (usage: sh j25_bodycheck.sh <E>); needs E/pr-body.md and E/quotes.tsv.
# Same commands as the inline checks they replace (docs 9); writes body-quotes.txt, tsv-quotes.txt,
# quotes-missing.log, quotes-check.log (one row per quotes.tsv row), body-numbers.txt, numbers-check.log (one row per number).
E=$1
awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '`[^`]+`' | sed 's/^`//;s/`$//' | sort -u > "$E/body-quotes.txt"
cut -f1 "$E/quotes.tsv" | sort -u > "$E/tsv-quotes.txt"
comm -23 "$E/body-quotes.txt" "$E/tsv-quotes.txt" > "$E/quotes-missing.log"
while IFS="$(printf '\t')" read -r q f; do if [ "$f" = "라벨" ]; then n="라벨"; else n=$(grep -F -c -- "$q" "$E/$f"); fi; printf '%s\t%s\t%s\n' "$n" "$f" "$q"; done < "$E/quotes.tsv" > "$E/quotes-check.log"
awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '[0-9]{2,}' | sort -u > "$E/body-numbers.txt"
while read -r x; do printf '%s\t%s\n' "$(grep -c -- "$x" "$E/check-corpus.txt")" "$x"; done < "$E/body-numbers.txt" > "$E/numbers-check.log"
```

- **허용 파일**: `docs/runbooks/pc-verify-wp16a.md`의 두 곳만 — §12 #9 행의 "PC 결과" 칸(할 일 8의 `awk`로 넣고 할 일 10의 `sed`로 끝만 바꾼다), 분기 A면 §13 표 아래 J-22 줄 다음의 빈 줄 하나와 펜스 `j25-line-sh`의 줄 하나. 그 밖은 고치지 않는다: §2a 본문·수동 절차, §12의 다른 행(#10 포함), §13 표의 칸, J-20·J-21·J-22 줄, mac-setup, C++·Python·테스트·`tools/ue/*.sh`·`Config/`(핫스팟 포함)·공유 문서·이 과제 파일. **생성·읽기만 하고 커밋하지 않는 것**: `unreal/Golmok/Content/Golmok/Weather/MPC_GolmokWeather.uasset`(할 일 7에서 `$E/asset/`으로 옮긴다), `Saved/Automation/Report/index.json`, 에디터 로그.
- **멈춤 조건(정하지 말고 영록에게 묻는다)**: `status-before-tracked.log`가 0이 아닐 때. `switch.rc`가 0이 아니거나 `sha-same.log`가 1이 아닐 때. `task.txt` 첫 줄·`extract-wc.log`가 기대와 다를 때. `overlap.log`가 비어 있지 않을 때. `ue-before.rc`가 1이 아닐 때(끄지 않는다). `pre.log`가 기대 여덟 줄과 다를 때(에셋 폴더·MPC 파일이 이미 있다, `L_Dev`가 없다, J-21·J-22가 아직 병합되지 않았다, J-25 줄이 이미 있다, #9 행이 바뀌었다 — 어느 것도 스스로 고치지 않는다). `check-attr.log`가 기대 세 줄과 다를 때. 잠금 파일에 다른 기록이 있거나 `lock-take.rc`·`lock-refresh-*.rc`가 0이 아닐 때. `build.rc`가 0이 아닐 때(고치지 않는다). `gen-1.rc`·`gen-2.rc`·`rb.rc`가 0이 아니거나(124 = 시간 초과 — 같은 명령을 다시 돌리지 않는다, 규칙 5) `*-new.log`가 `newer=0`이 아닐 때. `branch.log`가 `stop`일 때(값·순서 불일치·예외 — `weather_setup.py`도 에셋도 고치지 않는다). `weather-dir-1.log`·`status-run1-weather.log`·`status-run1.diff`가 기대와 다를 때. `logcheck-2.diff`·`logcheck-rb.diff`·`readback.diff`가 `exit=0` 한 줄이 아닐 때. `test-runtime.rc`·`test-weather.rc`가 0이 아니거나 `index-*-cp.rc`가 0이 아니거나 `index-*-new.log`가 `newer=0`이 아닐 때, `report-*.diff`·`testlog-*.diff`가 `exit=0` 한 줄이 아닐 때 — 특히 `runtime-mpc-skip 1`(MPC가 로드되지 않았다), `failed` 0이 아님·상태 `Fail`(MPC 단언 실패일 수 있다 — `entries-*.tsv`를 보내고, 다시 돌리지 않는다), `runtime-ns-executed 1`. `ue-after.rc`가 1이 아닐 때. `cleanup.diff`·`status-clean.diff`가 `exit=0` 한 줄이 아니거나 `asset-unique-count.log`가 `1`이 아닐 때(무엇이 에셋을 다시 썼다 — 판정하지 않는다). `cell.rc`·`cell-awk.rc`·`cell-cp.rc`·`line.rc`·`line-insert.rc`·`marker-pr.rc`가 0이 아니거나 할 일 8·10의 확인값이 기대와 다를 때. `cell-lines-*-count.log`·`cell-grep-*-count.log`가 기대와 다를 때(줄을 손으로 고치지 않는다). `gate-1.rc`·`gate-2.rc`가 0이 아니거나 `mtime-*.log`가 `newer=0`이 아닐 때. `c1-files.log`·`c2-files.log`·`author-*.log`·`push-*.log`·`branch-files.log`·`status-final.diff`가 기대와 다를 때. `lock-release.rc`가 0이 아닐 때(잠금 파일을 지우지 않는다). `pr-create.rc`·`pr-edit.rc`가 0이 아니거나 `pr-number.log`가 숫자 한 줄이 아닐 때. `run-wait.rc`가 0이 아닐 때(124 = 10분 안에 두 실행이 등록되지 않았다 — 다시 돌리지 않는다). `checks.log`에 pass가 아닌 행이 있을 때. `home-path.log`가 두 번 고친 뒤에도 0이 아닐 때. 넓은 명령에서 macOS 권한 창이 뜰 때(누르지 않는다). 상시 규칙 "PR 본문 공통" 9의 공통 멈춤 조건. 그 밖에 이 절의 "기대"와 다른 값이 하나라도 나올 때. **§2a 수동 절차(GUI)로 넘어가지 않고, 코드·에셋·설정을 고치지 않는다**. **멈춤 순서 — 할 일 2~7 안에서 멈출 때는 이 순서로 한다**: ① `pgrep -fl '[g]olmok-jaehwan/(unreal/Golmok/Golmok\.uproject|build/Mac/Golmok\.app/)' > "$E/ue-stop.log"; echo $? > "$E/ue-stop.rc"`. ② rc가 `1`이면 할 일 7의 옮기기(`j25_cleanup.sh` — 에셋이 없으면 `moved no`)와 `status-clean.diff`를 돌린 뒤 잠금을 풀고 `cleanup.log`·`status-clean.diff`와 함께 묻는다(에셋을 `$W`에 남기지 않는다 — 설계 7). rc가 `0`이면(편집기가 남았다) 프로세스·에셋·잠금을 건드리지 않고 `ue-stop.log`를 영록에게 보낸다.
- **완료 기준**:
  - (a) 준비: `status-before-tracked.log` `0`, `switch.rc` `0`, `sha-same.log` `1`, `task.txt` 첫 줄 `#### J-25 `, `extract-wc.log`(기대 숫자와 같다), `overlap.log` 빈 파일, `ue-before.rc` `1`, `pre.log` 여덟 줄, `check-attr.log` 세 줄.
  - (b) 빌드·첫 실행: `lock-take.rc`·`lock-refresh-build.rc`·`lock-refresh-gen-1.rc` `0`, `build.rc` `0`, `gen-1.rc` `0`, `gen-1-new.log` `newer=0`, `branch.log` `A` 또는 `B`(`logcheck-1.log` 원문), `weather-dir-1.log` 한 줄, `status-run1-weather.log` `1`, `status-run1.diff` `exit=0`.
  - (c) A: 둘째 실행·읽기 — `lock-refresh-gen-2.rc`·`lock-refresh-rb.rc` `0`, `gen-2.rc`·`rb.rc` `0`, `newer=0` 둘, `logcheck-2.diff`·`logcheck-rb.diff`·`readback.diff` `exit=0`(`readback.log` 일곱 줄 원문). B: 해당 없음.
  - (d) A: 테스트 — `lock-refresh-test-runtime.rc`·`lock-refresh-test-weather.rc` `0`, `test-runtime.rc`·`test-weather.rc` `0`, `report-runtime.diff`·`report-weather.diff`·`testlog-runtime.diff`·`testlog-weather.diff` `exit=0`, 기록 문구는 "MPC 단계 완료 / NS 단계 skip"(`runtime-mpc-skip 0`·`runtime-ns-skip 1`), `entries-*.tsv`·`unknown-warn-*.log` 원문. B: 해당 없음.
  - (e) 정리: `ue-after.rc` `1`, `cleanup.diff` `exit=0`(`moved yes`·`left 0`·`rmdir yes`·`weather-dir no`), `asset-unique-count.log` `1`, `status-clean.diff` `exit=0`, `lock-release.rc` `0`.
  - (f) 런북: `cell.rc`·`cell-awk.rc`·`cell-cp.rc` `0`, #9 행 바꿈 확인 `1`·`0`, A면 `line.rc`·`line-insert.rc` `0`·`line-diff.log` `exit=0`·J-25 줄 `1`, numstat(A `3 1`, B `1 1`), `cell-lines-1-count.log`(A `2`, B `1`), `cell-grep-1-count.log` `0`, `status.diff` `exit=0`.
  - (g) 커밋 1·PR: `gate-1.rc` `0`, `mtime-1.log` `newer=0`, `c1-files.log`·`author-1.log` 기대대로, `push-1.log` 끝 줄 `exit=0`, `pr-create.rc` `0`, `pr-number.log` 숫자 한 줄.
  - (h) 커밋 2: `marker-pr.rc` `0`, `근거: J-25 PR.` 0줄, 이 PR 번호의 `근거:` A `2`·B `1`, A면 `line-final-diff.log` `exit=0`, `cell-lines-2-count.log`(A `2`, B `1`), `cell-grep-2-count.log` `0`, `gate-2.rc` `0`, `mtime-2.log` `newer=0`, `c2-files.log`·`author-2.log` 기대대로, `push-2.log` 끝 줄 `exit=0`, `branch-files.log` 한 줄, `status-final.diff` `exit=0`.
  - (i) 에셋을 커밋하지 않았다: `branch-files.log`에 `.uasset` 없음, `$E/asset/MPC_GolmokWeather.uasset` 있음(`asset-sha-moved.log`).
  - (j) CI `run-wait.rc` `0`, `checks.log` 모든 행 pass 원문(규칙 2).
  - (k) PR 본문: 절 순서(상시 규칙 "PR 본문 공통" 2), "완료 기준 대조" 절, 점검표(그날 규칙 수만큼, 소절 3), `home-path.log` `0`, `quotes-missing.log` 빈 파일, `quotes-check.log`·`numbers-check.log`에 0 없음. 공통 완료 기준 (P)(소절 10): `checklist.diff` `exit=0`, `ph-unfilled.log` `0`, `pr-edit.rc` `0`, `ph-posted-unfilled.log` `0`, `ph-table.diff` `exit=0`, `signature-last.log` `1`, `cell-grep-1-count.log`·`cell-grep-2-count.log` `0`.
- **병합 시 반영(영록)**: STATUS 재환 절에 J-25 행(분기 A/B). V-16 세션(Opus)이 정할 것을 STATUS V-16 행에 한 줄: "헤드리스로 만든 `MPC_GolmokWeather`(J-25, `$TMPDIR/jaehwan/J-25/asset/`, sha256은 PR `## 결과`)를 커밋 에셋으로 쓸지, §2a를 GUI에서 다시 할지 — V-16 세션 Opus 결정"(분기 B면 "§2a 수동 절차가 필요하다"). 분기 A면 pc-verify-wp16a §2a 아래에 날짜를 단 "Mac 헤드리스 명령(추가, J-25에서 돈 그대로)" 메모 — 이 PR `## 실행한 명령`의 할 일 3 명령에서 `$E` 리다이렉트·잠금을 뺀 꼴(규칙 16, Windows 글은 지우지 않는다). §12 #10 칸은 Opus가 `entries-runtime.tsv`를 읽고 쓴다(재환은 쓰지 않는다). mac-setup §6 V-16 행 끝에 "§2a 헤드리스 기록은 pc-verify-wp16a §12 #9 칸(J-25)" 메모. 이 과제 뒤로 `$W`에는 MPC가 없으므로 J-22 명령을 에셋 뒤에 다시 돌리는 일은 V-16 에셋 커밋 뒤의 일이다.
- **왜 재환 / 위험**: 판정이 모두 고정 기대값과의 `diff`·종료 코드·보고서에서 기계적으로 뽑은 줄로 끝나고, 분기(A/B/stop)와 칸·줄 문구가 펜스로 미리 정해져 재환이 고르는 것이 없다. 코드도 Astra 레인도 건드리지 않는다. 위험과 대응: ① lockable LFS 이진 파일을 실수로 커밋·잠그거나 `$W`에 남겨 J-22·뒤의 패키지를 흐리는 것 — 실행 전후 상태 사본과 `diff`, `mv`로 `$E`에, 커밋 파일 목록 대조(규칙 6), 순서는 J-22 뒤, 멈출 때도 옮긴다. ② `-nullrhi`에서 저장되지 않거나, 저장은 됐는데 스칼라가 비어 있는 것 — 다른 프로세스의 읽기(펜스 `j25-readback-py`)와 sha256으로 본다. Error 분기면 멈추고 GUI 수동 절차로 넘어가지 않는다(분기 B). ③ "Success"를 "MPC 단계 통과"로, 또 필터 단위 성공을 NS 단계까지 덮어 읽는 것(R149·R153 반복) — skip Info 문구를 보고서 `entries`에서 세고, 칸·줄은 "MPC 단계 완료 / NS 단계 skip"으로 둘 다 적는다(규칙 14·15). ④ `-ExecCmds` 쉼표 나눔 — 생성기는 파일. ⑤ 편집기 종료 — `QUIT_EDITOR`, `-ExecutePythonScript` 금지. ⑥ GUI·GPU 공유 — 잠금(갱신 240 s, 맨 끝에 풀기), 시간 수치는 근거가 아니고 칸·줄에 쓰지 않는다. ⑦ wp16a 충돌 — J-21·J-22 줄을 앵커·전제로 둔다(`pre.log`), #9 행은 줄 전체 일치로만 바꾼다. ⑧ 한 번의 Mac `-nullrhi` 관찰을 "Python은 언제나 쓸 수 있다"로 넓히는 것(규칙 3·15) — 문구에 날짜·SHA·조건, GUI는 [미확인].
- **dry-run 범위(Opus 2026-11-28)**: `origin/main` `366e118`의 scratch 사본(`git archive`, git 저장소로 만든 것)에서 한 것: 펜스 `j25-run-py`·`j25-readback-py`를 `tools/tests/fake_unreal.py`(가짜 `unreal`, 레지스트리가 두 실행 사이에 남는다)에 돌려 로그 꼴(`LogPython: …`, `LogInit: Command Line: -ExecCmds="py …/j25_run.py,QUIT_EDITOR" …`)로 옮긴 합성 로그에서 `j25-logcheck-sh` 출력이 `j25-expected-logcheck-1`·`-2`·`-rb`와 같고 `readback.log`가 `j25-expected-readback`과 같았다. `unreal.CollectionScalarParameter`를 지운 가짜에서는 `created but scalar_parameters not writable from Python (AttributeError: …)` Error가 나와 `j25-branch-sh`가 `B`, 둘째 실행 로그를 첫 실행 자리에 주거나 빈 로그·다른 스크립트 이름을 주면 `stop`(빈 검사 아님). 첫 실행 로그를 둘째 기대값과 비교하면 8줄, 읽기 기대값과 비교하면 7줄이 달랐다. `j25-report-py`는 `$W`의 실제 J-12b 보고서(39개)에서 `runtime-mpc-skip 1`·`runtime-ns-skip 1`(`expected-report-weather`와 40줄 다름), 알려진 Warning 3개가 모두 `KNOWN`과 같아 `unknown` 0줄. 그 보고서에서 Weather 테스트만 남기고 MPC skip Info를 뺀 합성 보고서는 두 기대 펜스와 `diff` 0, 새 Warning 한 줄을 더하면 그 줄만 `unknown`에 나왔다. `j25-testlog-sh`는 실제 J-12b 에디터 로그(`Golmok.log`, UTF-8 BOM)에서 `mpc-missing 1`·`start-mpc-missing 29`·`start-mpc-ok no`, 필터 문구·`MPC missing` 줄·시작 줄을 바꾼 합성 로그에서 `j25-expected-testlog`와 같고, 다른 필터 이름을 주면 `cmdline` 줄이 달랐다. `j25-cleanup-sh`는 가짜 `$W`에서 `moved yes`·`left 0`·`rmdir yes`·`weather-dir no`(= `j25-expected-cleanup`), 다시 돌리면 `moved target-exists`, 다른 파일이 있으면 `rmdir no`·`weather-dir yes`이고 아무것도 지우지 않았다. 런북: scratch 사본에 J-21(합성 한 줄)·J-22(`j22-line-sh` 출력) 줄을 먼저 넣고 커밋한 것을 `origin/main` 대신 두고, 분기 A에서 `j25-cell-sh`·`awk` 바꾸기(rc 0)·`sed` 넣기(rc 0) 뒤 #9 행 확인 `1`, `awk getline` `diff` 0, numstat `3 1`, 칸 자기 검사 더한 줄 `2`·`grep -n -E` 0건, `git status`는 ` M docs/runbooks/pc-verify-wp16a.md` 한 줄. 커밋 2의 `sed`(가짜 번호 163) 뒤 `근거: J-25 PR.` 0줄, 번호 줄 `2`, `근거: PR #153.` 그대로 1, numstat `3 1`, 자기 검사 `2`·0건. 분기 B: `j25-line-sh` rc 3(줄 없음), numstat `1 1`, 자기 검사 `1`·0건, 같은 `awk`를 바뀐 파일에 다시 돌리면 rc 3, 분기 값이 A·B가 아니면 `j25-cell-sh` rc 3. 칸 글 분기 A 502바이트·분기 B 357바이트(B는 정정 2026-11-28 문서 8: "빈 에셋은" → "만든 에셋은" 뒤 다시 잰 값), 줄 773바이트(견본 날짜 `2026-11-28`·SHA 7자리). 펜스 셸 스크립트는 `sh -n`·`bash -n` 통과, 파이썬 펜스는 `py_compile` 통과. 할 일 1의 두 `awk` 추출·펜스 추출 `wc -l`과 추출본 = 이 절의 펜스(바이트 같음), 파이썬 게이트(`ruff check`·`ruff format --check`·`pytest -q`·`check_repo.py`)는 이 절과 분기 A 기록이 들어간 scratch 사본에서 돌렸다. dry-run하지 못한 것(이 과제가 재는 것): 실제 편집기에서 `unreal.CollectionScalarParameter`가 있는지·`set_editor_property`가 되는지·`-nullrhi`에서 저장되는지(분기 A/B 자체), 둘째 프로세스의 `does_asset_exist`, 실제 `.uasset` sha256, `test.sh` 두 번(MPC가 있을 때 Runtime의 상태·entries — `-nullrhi` MPC 인스턴스, Lighting·Runtime의 Warning 배치), 실제 `build.sh`, 잠금 갱신 루프, `gh` 명령, 실제 본문의 인용·숫자 검사.

#### J-26 V-18 §0·§1 헤드리스 — 설계 선행
- **출처**: [pc-verify-v18.md](../runbooks/pc-verify-v18.md) §0·§1(빌드·테스트·8 WAV 재임포트, 오류 0·경고 0). 임포트 코드는 Astra 오디오 레인이다.
- **설계 메모**: 재임포트가 Astra 레인 `Content/Golmok/Audio/`를 다시 쓰므로 실행 뒤 `git -C $W checkout -- unreal/Golmok/Content/Golmok/Audio` 같은 원복 절차와 확인 명령.
- **허용 파일**: v18 결과 칸만. 오디오 레인 파일은 커밋하지 않는다.
- **완료 기준**: 임포트 로그 `grep -c` (오류·경고), `git status` 깨끗.
- **왜 재환 / 위험**: 로그 판정. 위험: Astra 레인 파일 변경(가장 큰 위험 — 메모의 원복 단계로 막는다).

#### J-27 V-05 S12 `run_game_perf.sh` Mac 첫 실행: 도구 경로 점검(성능 아님) — 재환 과제는 닫음, 남은 절반은 영록 카드(Opus 2026-11-28 문서 9)
- **배정 보류 — 재환에게 다시 배정하지 않는다(닫음, 영록 2026-11-28 문서 9)**: 재환은 이 절의 어떤 명령도 돌리지 않는다. 아래 "영록 카드"와 "선행 기록 넣기"는 영록 몫이다. 재환의 2026-11-28 실행 증거(`$TMPDIR/jaehwan/J-27/`)와 크래시 리포트 폴더, `$W/unreal/Golmok/Saved/` 아래의 생성물·CSV, 브랜치 `local/jaehwan-j27-game-perf`(커밋 0, push·PR 없음)는 지우지 않는다(이 Mac의 로컬 상태, D-019 — 지우는 일은 소유자 몫). 옛 절 전문(할 일 1~8, 설계 1~10, 펜스 `j27-row-sh` 포함)은 `origin/main` `acbd954`의 이 절에 그대로 있다.
- **2026-11-28 실행 기록(재환, 14:35~14:43, 재환 worktree `origin/main` `37b6af8`, 증거 `$TMPDIR/jaehwan/J-27/`)**: 할 일 1~3은 기대대로 끝났다 — `build.rc`·`gen.rc` `0`, `dwell-sha.diff`·`sh-diff.log`·`script-greps.diff` `exit=0`. 할 일 4: `wrapper.rc`·`run.rc`·`game-argv.rc` `0`, `game-pid.log` `11197`, `argv.diff` `exit=0`(argv 14개, 0번 `/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor`, 12번 `-ExecCmds=golmok.hud 0, golmok.tod clear_noon, golmok.path play j27_dwell --csv` 한 항목), `editor-after.rc` `1`. `logcheck.diff`는 `exit=1`: `cmdline-execcmds-quoted`·`tod-clear_noon`·`path-play-csv`·`csvprofile-start`는 `1`, `path-finished`·`capture-ended`·`exit-after-csv`는 `0`, `debug-csv-line no`, 오류 세 개는 `0`. 게임 로그 사본(`game.log`, 1534줄)의 끝: 1497행 `LogMetal: Warning: Metal Command Buffer Failure: OutOfMemory`, 1517행 `appError called: Fatal error: [File:./Runtime/Apple/MetalRHI/Private/MetalCommandList.cpp] [Line: 90]`, 다음 줄 `Command Buffer PatchSplit Failed with OutOfMemory Error! … (00000008:kIOGPUCommandBufferCallbackErrorOutOfMemory)`, 1534행 `LogExit: Executing StaticShutdownAfterError` — 캡처 시작(1468행 `Capture started`, `05.37.27:547`) 약 4 s 뒤(`05.37.31:786`, 프레임 305)다. 같은 로그 825행 `VRAM (MB): 98304`, 822행 `Texture pool is 68812 MB (70% of 98304 MB)`. 그때 `lms-ps.log`는 `qwen3.8-flash-next … IDLE 94.58 GB 262144 4 … TTL 60m / 1h`, `stop-mem.log`의 `hw.memsize`는 `137438953472`. CSV: `run.out`의 `csv a_clear_noon_j27_dwell -> …/unreal/Golmok/Saved/Profiling/CSV/Profile(20261128_143727).csv`, 원본과 사본 모두 262144바이트(`stop-mem.log`), 사본 155줄(`stop-mem.log`); 원본 155줄·두 파일 `cmp` 같음은 2026-11-28 Opus 읽기 확인 — 끝까지 쓰인 파일인지는 [미확인](크기가 정확히 256 KiB다). `run.err`(2줄)에는 `[UE4] Shutdown handler: initialize.` 한 줄과 `WARNING: a_clear_noon_j27_dwell log has no 'GolmokDebugSubsystem: csv:' line` 한 줄. 할 일 4의 넓은 `find`·할 일 5 이후는 돌지 않았다(멈춤 조건). **크래시 리포트 업로드**: `stop-crash.log`의 폴더 `~/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Crashes/CrashReport-UE-Golmok-pid-11197-…`가 생겼고, `~/Library/Logs/Unreal Engine/CrashReportClient/CrashReportClient.log`(14:37)는 26행 `Command Line: … -Unattended`, 70행 `Got 7 pending files to upload`, 81행 `Response=204 ConnectedSuccesfully=1`, 82행 `All uploads done`이다 — 게임 로그(사용자 이름이 든 절대 경로 포함)·minidump·`Diagnostics.txt` 등 7개가 Epic datarouter로 올라갔다(D-007 줄과 WP-21 "부수 발견"이 적은 동작, 되돌릴 수 없다).
- **출처**: 옛 절의 출처(`acbd954`)를 그대로 쓴다. 이 판단에 새로 쓴 것: `spike_runner.py:908-973`(`game_scripts`의 인자는 `paths`·`tags`·`presets`·`res`·`base_level`·`timeout_s`·`label_suffix`·`discover_from_index`뿐 — 화질·`r.ScreenPercentage`·창 인자는 없다), `_pure.py:1722-1759`(`game_command_line`의 argv는 고정 목록 + `-ini:` 하나), `_pure.py:2038`(`wait "$pid" 2>/dev/null` — 게임 종료 코드를 버린다)·`:2065`(끝 줄이 `echo`라 스크립트는 늘 0으로 끝난다), `GolmokDebugSubsystem.cpp:899-901`(`CsvProfile Start`에 폴더 인자 없음)·`:955-963`(경로 끝에서 `CsvProfile Stop` 뒤 `LogLatestCsv` — `csv:` 줄은 그때만 찍힌다)·`:992`(`finished`/`stopped` 줄). 엔진(읽기, 5.8.4): `Core/Private/ProfilingDebugging/CsvProfiler.cpp:3972-3978`(파일 이름 `Profile(<시각>)`과 폴더가 **캡처 시작 때** 정해지고 그때 파일을 연다 — 그래서 크래시 전의 파일 위치가 곧 이 실행의 CSV 위치다)·`:4741`(기본 폴더 `ProfilingDir()/CSV/`)·`:4309-4312`·`:4533`, `Core/Private/Misc/Paths.cpp:548-551`(`ProfilingDir()` = `ProjectSavedDir()/Profiling/`), `Core/Private/Mac/MacPlatformMisc.cpp:348`(크래시 폴더 = `GameAgnosticSavedDir()/Crashes`)·`:2419-2445`(`[/Script/UnrealEd.CrashReportsPrivacySettings] bSendUnattendedBugReports`가 false이고 `-unattended`면 CrashReportClient를 띄우지 않는다 — J-29의 키 후보, 정하는 것은 J-29 설계). 런북 [mac-setup](../runbooks/mac-setup.md) §8 #6(:292)·#13(:299)·#26(:312).
- **설계 (확정, Opus 2026-11-28 문서 9)** — 세 안(① 재환이 메모리 요구를 낮춰 다시, ② 영록 카드, ③ 나눔) 중 **②에 확인된 절반의 기록을 더한 것**으로 정한다. 재환 몫은 이미 한 일(할 일 1~4 앞부분)로 끝났고 새 재환 과제는 없다.
  1. **①을 쓰지 않는 이유**: (가) 낮출 손잡이가 사실상 해상도뿐이다. 생성기에는 화질·`r.ScreenPercentage`·`-windowed` 인자가 없고(위 출처), 과제 전용 감싸개로 argv를 바꾸면 이 과제가 재려던 "생성기가 만든 그대로의 명령"이 아니게 된다. `res=(1280, 720)`은 라벨을 `a_clear_noon_j27_dwell_720p`로 바꿀 뿐 메모리가 충분해진다는 근거가 없다. (나) 원인이 메모리 경합이라는 것은 추정이다: 증거는 `VRAM (MB): 98304`와 로드된 모델 94.58 GB, 프레임 305의 `kIOGPUCommandBufferCallbackErrorOutOfMemory` 한 번뿐이다. 같은 날 재환 worktree 패키지 `-game`(J-15, 1080p 2회)은 크래시 없이 끝났다(mac-setup §8 #11~#13 칸 — 재환이 직접 돌린 실행이라 그 모델이 로드돼 있었을 것이나 `lms ps` 기록은 없다) — 경합이 늘 크래시를 내는 것도 아니다. "싼 탐침"이 따로 없다: 메모리가 모자란지를 재는 가장 싼 방법이 같은 30 s 남짓의 `-game` 한 번이다. (다) 다시 크래시하면 리포트가 다시 Epic으로 올라간다(위 업로드 기록). 알면서 그 위험이 있는 실행을 하는 것은 외부 발송(D-019 ③)이라 J-29 전에는 누구도 하지 않는다(J-29 "시험으로 크래시를 일으키지 않는다"). (라) 경합이 GPU를 같이 쓰는 LM Studio 쪽을 먼저 넘어뜨리면 재환 세션이 잠금을 쥔 채 끊길 수 있다 — [미확인]이지만 재환이 스스로 처리할 수 없는 상태다. 그래서 재환 과제로 남기면 판단 없는 절이 되지 않는다(assignable 아님).
  2. **확인된 절반은 지금 기록한다(영록)**: argv(14개, `-ExecCmds` 한 항목, 로그 `Command Line:`의 다시 감싼 꼴), `editor_exe` 경로(argv 0번으로 실행됨), CSV 폴더(후보 1 — `CsvProfiler.cpp:3972-3978`이 폴더를 캡처 시작 때 정하므로 크래시 뒤에도 이 실행의 위치로 쓸 수 있다)는 재실행 없이 증거로 적을 수 있다. 크래시 리포트 폴더가 `GameAgnosticSavedDir()`(`~/Library/Application Support/Epic/UnrealEngine/5.8/Saved`) 아래였다는 것도 관찰이다. 적지 못하는 것: 경로 끝, `Capture Ended`, `-ExitAfterCsvProfiling` 종료(pc-verify-wp06 §12 #17의 절반), 온전한 CSV의 `golmok-perf`, 정상 실행의 `GolmokDebugSubsystem: csv:` 줄. 이 줄은 **영록**이 넣는다: 재환 과제는 닫혔고, 2026-11-28 영록 메시지가 "런북·STATUS 줄은 영록이 쓴다"로 정했으며(`commands.txt`의 끝 안내 줄), 무엇이 확인이고 무엇이 [미확인]인지 고르는 것이 판단이기 때문이다. 줄은 펜스 `j27-row27-prerecord` 그대로이고, 아래 "선행 기록 넣기"가 이 절을 싣는 영록 문서 PR(문서 9)에서 넣는다.
  3. **남은 절반은 영록 카드**(아래). 조건: J-29 병합(크래시 업로드가 꺼진 것을 그 과제의 확인 명령으로 다시 확인), 재환 유휴, `lms ps`에 모델 없음. 같은 생성기·같은 정지 경로·같은 기대값 펜스(옛 펜스를 바꾸지 않고 그대로 쓴다)로 한 번 돌린다. 모델을 내린 상태에서도 OutOfMemory면 메모리 경합 추정이 틀린 것이므로 멈추고 원인을 따로 연다(Claude 레인). V-05 S12 실제 실행(PIE `walk_01`, 영록, 모델 내림, 정본 성능 측정)이 먼저 돌면 그 실행이 같은 질문에 답하므로 카드는 돌리지 않고 그 결과로 #27 칸에 메모를 더한 뒤 닫는다.
  4. **스크립트 종료 코드는 코드 결함 후보다**: `run_game_perf.sh`는 게임이 크래시해도 0으로 끝나고, 크래시 전까지의 CSV를 복사하고 `golmok-perf` 줄을 찍는다(`_pure.py:2038`·`:2065`, 이번 실행의 `run.rc` `0`·`run.out`). 남은 경고는 `csv:` 줄이 없다는 한 줄뿐이다. 고치는 것(게임 종료 코드를 남기고 0이 아니면 `WARNING`, 또는 CSV를 복사하지 않음)은 설계 판단이라 J-16의 주석 정리에 섞지 않고 Claude 레인 후속으로 둔다(백로그 행은 영록이 연다). 카드는 이 결함을 피하려고 스크립트 rc가 아니라 로그의 고정 줄(`j27-logcheck-sh`)과 `appError called` 0건으로 판정한다.
  5. **J-16에 대한 뜻**: J-16의 열린 점 중 `_pure.py:1787`(`editor_exe` darwin 분기 — argv 0번이 그 경로로 실행됨)과 `:1986`(`sh_arg` — `KERN_PROCARGS2` 12번이 한 항목, 로그 `Command Line:`의 `-ExecCmds="…"`)은 이 증거로 답이 났다. `:1779`·`:1802`(`MAC_USER_SETTINGS_REL`·후보 2)는 반쯤: 에디터 바이너리 `-game`의 CSV는 후보 1에 생겼다(스크립트 `find`가 두 후보를 함께 보고 가장 새 파일로 후보 1을 골랐다 — 넓은 `find`는 돌지 않았다). 실행 뒤(같은 날 16시대, Opus의 읽기 전용 `ls`) 후보 2의 루트 `~/Library/Application Support/Epic/UnrealEngine/5.8/Saved`에는 `Profiling` 폴더가 없고, `Golmok`(14:37, 스크립트의 경로 사본)과 `Crashes`(14:37, 크래시 리포트)가 있다. 후보 2를 남길지 지울지(지우지 않아도 해가 없다는 `_pure.py:1778-1781` 주석, `Paths.cpp:183-190`의 `-SaveToUserDir`·설치 빌드 경우)는 영록이 J-16을 다시 쓸 때 정한다 — 재환 판단으로 넘기지 않는다. `package.sh:26`(방화벽)은 J-27과 무관하다(J-15, §8 #11). 그래서 J-16은 **영록 카드를 기다리지 않는다**: #27 선행 기록 줄이 병합되고 영록이 J-16 절을 바꿀 줄마다 새 글자로 다시 쓴 뒤 배정할 수 있다. 카드가 답할 남은 점(`-ExitAfterCsvProfiling` 종료, 온전한 CSV)은 J-16의 줄이 아니라 pc-verify-wp06 §12 #17과 V-05 S12의 몫이다.
  6. **정정할 다른 글(영록, 이 절을 싣는 PR에서)**: 백로그 J-27 행(이 PR의 `backlog_row`), "다음" 줄의 J-27 항목, "재환에게 맞지 않는 것" 표에 펜스 `j27-unfit-row` 한 줄, J-16 절 첫머리의 "J-27 결과(mac-setup §8 #27)" 문장(카드가 아니라 선행 기록 줄을 기다린다). 상시 규칙의 J-27 언급(대기 절차 목록의 `J-27`, 다시 돌리는 이름 예외의 "J-27 멈춤 ①", "PR 본문 공통" 4 ③의 "J-27 (i)")은 닫힌 절을 가리키는 옛 기록이라 그대로 두어도 재환 동작이 바뀌지 않는다. STATUS·DECISIONS: 2026-11-28 14:37 크래시 리포트 업로드(위 기록)를 D-007 줄 아래 날짜 메모로 더하고 소유자에게 사실로 알린다(되돌릴 수 없는 외부 발송이 이미 일어났다 — 승인 요청이 아니라 보고). J-29를 설계 선행 과제 중 맨 앞으로 올린다.
- **펜스**: 아래 `j27-gen-py`부터 `j27-dwell-sha256`까지는 옛 절의 펜스를 한 글자도 바꾸지 않고 둔 것이다(2026-11-28 실행에서 `extract-wc.log`·`dwell-sha.diff`·`sh-diff.log`·`script-greps.diff`·`argv.diff`가 이 펜스로 기대와 같았다). 옛 `j27-row-sh`(재환 행 생성기)는 지웠다 — 행은 `j27-row27-prerecord`, 카드 결과는 `j27c-note-sh`가 만든다. `j27c-*`·`j27-row27-prerecord`·`j27-memo-6`·`j27-unfit-row`는 문서 9에서 더한 것이다.

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

```sh j27c-pre-sh
#!/bin/sh
# J-27 card (yeongrok): facts before the run, one per line. usage: sh j27c_pre.sh <W> <E>
W=$1
E=$2
L="$TMPDIR/claude/gui-foreground.lock"
if [ -e "$L" ]; then echo "lock busy"; else echo "lock none"; fi
if pgrep -f '[g]olmok-jaehwan/unreal/Golmok/Golmok.uproject' > /dev/null; then echo "editor running"; else echo "editor none"; fi
git -C "$W" status --porcelain > "$E/status-before.log"
echo "tracked $(grep -c -v '^?? ' "$E/status-before.log")"
if git -C "$W" diff --quiet origin/main HEAD -- unreal/Golmok/Source unreal/Golmok/Config unreal/Golmok/Content/Python unreal/Golmok/Golmok.uproject; then
  echo "code same"
else
  echo "code differs"
fi
"$HOME/.lmstudio/bin/lms" ps > "$E/lms-ps-before.log" 2>&1
echo "lms-rc $?"
echo "model $(grep -c 'qwen3.8-flash-next' "$E/lms-ps-before.log")"
for f in Maps/L_ZoneTest.umap Zones/z_synthetic_001/v1/SM_chunk_00.uasset; do
  if [ -f "$W/unreal/Golmok/Content/Golmok/$f" ]; then echo "asset yes"; else echo "asset no $f"; fi
done
```

```text j27c-expected-pre
lock none
editor none
tracked 0
code same
lms-rc 0
model 0
asset yes
asset yes
```

```sh j27c-note-sh
#!/bin/sh
# J-27 card (yeongrok): the dated note appended to the mac-setup section 8 row 27 result cell (branch A only).
# usage: sh j27c_note.sh <E>
E=$1
date=$(cat "$E/run-date.log")
sha=$(cat "$E/sha.log")
class=$(sed -n 's/^class //p' "$E/where.log")
base=$(basename "$(cat "$E/find-wide.log")")
case "$class" in
  candidate-1) where='후보 1(프로젝트 `Saved/Profiling/CSV`)' ;;
  candidate-2) where='후보 2(`~/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Profiling/CSV`)' ;;
  *) echo "j27c_note: class '$class' has no note form" >&2; exit 3 ;;
esac
if [ "$(grep -c 'qwen3.8-flash-next' "$E/lms-ps-run.log")" != 0 ]; then
  echo "j27c_note: the model was loaded during the run" >&2
  exit 4
fi
printf '확인(%s, 재환 worktree HEAD `%s`, 같은 생성기·같은 경로, `lms ps`에 모델 없음): 경로 끝(`finished (end of path)`) 뒤 `Capture Ended. Writing CSV to file :`가 찍혔고 CSV는 %s의 `%s`였다. 게임은 `FPlatformMisc::RequestExit(0, CsvProfiler.ExitAfterCsvProfiling)`로 스스로 끝났고 그 CSV에 `golmok-perf … --markdown` rc 0. 근거: J-27 PR.\n' "$date" "$sha" "$where" "$base"
```

```text j27-row27-prerecord
| 27 | 에디터 바이너리 `-game` CSV 실행 경로(V-05 S12 `run_game_perf.sh`) | `_pure.py`의 [미확인] 셋: CSV 후보 두 곳(프로젝트 `Saved/Profiling/CSV`, `~/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Profiling/CSV`), `sh_arg`가 바깥 따옴표를 뗀 `-ExecCmds=…`가 한 argv 항목으로 가는지, `editor_exe`의 `Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor` | `game_scripts(...)`가 만든 `run_game_perf.sh` 1회, 게임 프로세스 argv는 `sysctl` `KERN_PROCARGS2`로 읽는다 | 부분(2026-11-28, 재환 worktree `origin/main` `37b6af8`, 합성 정지 경로 20 s·`L_ZoneTest`·1920×1080·`discover_from_index=False`, LM Studio `qwen3.8-flash-next` 94.58 GB 로드됨): argv는 14개였고 0번은 `editor_exe` 경로 그대로, 12번은 `-ExecCmds=golmok.hud 0, golmok.tod clear_noon, golmok.path play j27_dwell --csv` 한 항목이었다. 게임 로그 `Command Line:`에는 `-ExecCmds="…"`로 다시 감싸여 있었고, 세 콘솔 명령이 돌아 `CsvProfile Start (path 'j27_dwell')`가 찍혔다. CSV는 캡처 시작 때 후보 1(`Saved/Profiling/CSV/Profile(20261128_143727).csv`)에 생겼고 스크립트가 그 파일을 복사했다. 실행 뒤 `ls`로 후보 2 아래에는 `Profiling` 폴더가 없었다. 경로 재생 중 게임이 Metal `Command Buffer PatchSplit Failed with OutOfMemory Error`로 끝나 경로 끝·`Capture Ended`·`-ExitAfterCsvProfiling` 종료·온전한 CSV의 `golmok-perf`는 [미확인]이다(메모리 원인은 판정하지 않았다). 스크립트는 이 비정상 종료에도 rc 0이었다. 크래시 리포트는 `~/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Crashes/`에 생겼고 CrashReportClient가 Epic으로 올렸다(J-29). 근거: J-27 PR. |
```

```text j27-memo-6
(2026-11-28 메모: 에디터 바이너리 `-game` 실행의 CSV 위치는 #27에 적었다.)
```

```text j27-unfit-row
| V-05 S12 `run_game_perf.sh`의 남은 절반(경로 끝·`Capture Ended`·`-ExitAfterCsvProfiling` 종료·온전한 CSV의 `golmok-perf` — J-27 카드) | LM Studio 모델이 로드된 채 돌린 에디터 바이너리 `-game`이 Metal OutOfMemory로 끝났고(원인 [미확인]) 재환은 자기 모델을 내릴 수 없다. 크래시는 CrashReportClient 업로드(외부 발송)가 되므로 J-29 뒤에만 돌린다 | 영록(재환 유휴·모델 내림) |
```

- **선행 기록 넣기(영록, 이 절을 싣는 문서 PR의 작업 브랜치에서 — 그 브랜치의 작업 트리 파일에서 펜스를 뽑는다)**: 모든 명령은 `R="$HOME/projects/golmok"; E="$TMPDIR/yeongrok/J-27-row";`로 시작한다. 이 소절의 명령에는 기다리는 명령이 없다(게이트·`git push`·`gh`는 영록의 문서 PR 절차 그대로, 각각 `/usr/bin/timeout`을 붙인다).
  1. 뽑기: `mkdir -p "$E" && awk '/^#### J-27 /{f=1} /^#### J-28 /{f=0} f' "$R/docs/plan/jaehwan-tasks.md" > "$E/task.txt"; printf '%s\n' "j27-row27-prerecord row27.txt" "j27-memo-6 memo6.txt" "j27-unfit-row unfit-row.txt" | while read -r n f; do awk -v n="$n" 'BEGIN {t = "\140\140\140"} $0 == t && x {x = 0} x {print} index($0, t) == 1 && substr($0, 4) ~ ("^[a-z]+ " n "$") {x = 1}' "$E/task.txt" > "$E/$f"; done; cd "$E" && wc -l row27.txt memo6.txt unfit-row.txt > "$E/extract-wc.log"` — 기대 앞 숫자 `1`·`1`·`1`, 끝 줄 `3 total`(백틱을 쓰지 않으려고 awk가 `\140` 세 개로 펜스 줄을 만든다).
  2. 넣기(한 번만): `cd "$R" && git status --porcelain > "$E/status-before.log"; sed -i '' "/^| 26 | Object Capture 상한(M5 Max) | 미정 |/r $E/row27.txt" docs/runbooks/mac-setup.md; echo $? > "$E/row-insert.rc"; awk -v memo="$(cat "$E/memo6.txt")" '/^\| 6 \| Mac /{sub(/ \|$/, " " memo " |")} {print}' docs/runbooks/mac-setup.md > "$E/mac-setup.new" && cat "$E/mac-setup.new" > docs/runbooks/mac-setup.md; echo $? > "$E/memo6.rc"; sed -i '' "/^| WP-21 후속 1(Cesium /r $E/unfit-row.txt" docs/plan/jaehwan-tasks.md; echo $? > "$E/unfit-insert.rc"` — 기대 세 rc `0`.
  3. 확인: `cd "$R" && { awk '/^\| 26 \| /{getline n; print n}' docs/runbooks/mac-setup.md | diff - "$E/row27.txt"; echo "row27=$?"; grep -c '^| 27 | ' docs/runbooks/mac-setup.md; grep '^| 6 | Mac ' docs/runbooks/mac-setup.md | grep -c -F "$(cat "$E/memo6.txt") |"; awk '/^\| WP-21 후속 1\(Cesium /{getline n; print n}' docs/plan/jaehwan-tasks.md | diff - "$E/unfit-row.txt"; echo "unfit=$?"; git diff --numstat -- docs/runbooks/mac-setup.md; } > "$E/check-1.log" 2>&1` — 기대 `check-1.log`가 다섯 줄 `row27=0`·`1`·`1`·`unfit=0`·`2	1	docs/runbooks/mac-setup.md`. 칸 자기 검사: `cd "$R" && git diff -U0 origin/main -- docs/runbooks/mac-setup.md | grep '^+[^+]' > "$E/cell-lines-1.txt"; wc -l < "$E/cell-lines-1.txt" | tr -d ' ' > "$E/cell-lines-1-count.log"; grep -n -E '\.log|영록|R[0-9]{3}' "$E/cell-lines-1.txt" > "$E/cell-grep-1.log"; wc -l < "$E/cell-grep-1.log" | tr -d ' ' > "$E/cell-grep-1-count.log"` — 기대 `2`·`0`.
  4. PR 번호가 나온 뒤(커밋 2): `N=<PR 번호>; cd "$R" && sed -i '' "s/ 근거: J-27 PR\. |\$/ 근거: PR #$N. |/" docs/runbooks/mac-setup.md; grep -c ' 근거: J-27 PR\. |$' docs/runbooks/mac-setup.md; grep '^| 27 | ' docs/runbooks/mac-setup.md | grep -c " 근거: PR #$N\. |\$"` — 기대 `0`·`1`, 그 뒤 3의 칸 자기 검사를 번호 `2`로(기대 `2`·`0`), 게이트 다시.
- **영록 카드 J-27c(남은 절반 — 재환에게 맞지 않는 것)**: 성능 측정이 아니다. 수치는 기록만 하고 판정하지 않는다.
  - **언제**: 다음이 모두 참일 때만. ① J-29가 병합됐고, C1의 `switch.rc` `0` 뒤에 `grep -c -x 'bSendUnattendedBugReports=False' "$W/unreal/Golmok/Config/DefaultEditorSettings.ini" > "$E/j29-key.log"`가 `1`이다(J-29가 키를 넣기 전에는 카드를 돌리지 않는다 — 크래시가 나면 외부 발송이다). 에디터 바이너리 `-game`도 이 키를 읽는다는 것은 엔진 소스(`ConfigCacheIni.cpp:6638-6652`, `GenericPlatformCrashContext.cpp:800-816`, `MacPlatformMisc.cpp:2419-2445`)로 본 추정이라 [미확인]이다 — 그래서 C4 뒤에 크래시가 날 수 없는 확인(C4b)을 한 번 한다. ② 재환이 유휴다: 이 파일 "진행 중" 표에 행이 없고 배정한 과제가 없다. ③ 아래 C1의 `pre.diff`가 `exit=0`. V-05 S12 실제 실행이 먼저 돌았으면 카드를 돌리지 않는다(설계 3).
  - **명령 공통**: 모든 명령은 `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/yeongrok/J-27"; R="$HOME/projects/golmok";`로 시작한다. `git fetch`·`git push`·`gh`·`find`·`pytest`·UE 명령은 `/usr/bin/timeout`을 붙인 그대로 쓴다. C3·C4·C5의 UE 명령과 게이트는 하네스 백그라운드로 돌리고 `.rc` 파일을 기다린다. 잠금 한 줄은 `영록 J-27-game <시각>`이고, 확인·잡기·갱신 ①·갱신 루프 ②·풀기는 옛 절(`acbd954`) "명령 공통"의 명령에서 `재환`을 `영록`으로만 바꾼 것이다(갱신 루프는 240 s마다, 잠금은 C5 끝에 맨 나중에 푼다). C2·C4·C5·C6의 '옛' 명령은 C1의 `task-acbd954.txt`에서 복사하고, 앞머리 `E="$TMPDIR/jaehwan/J-27"`를 이 카드의 `E`로, 잠금 줄의 `재환 J-27-game`을 `영록 J-27-game`으로만 바꾼다(다른 글자는 바꾸지 않는다).
  - **C1 준비**: `mkdir -p "$E" && /usr/bin/timeout 120 git -C "$W" fetch origin > "$E/fetch.log" 2>&1; echo $? > "$E/fetch.rc"` — 기대 `0`. `$W`를 `origin/main`에: `git -C "$W" branch --show-current > "$E/branch-before.log"; git -C "$W" status --porcelain --untracked-files=no | wc -l | tr -d ' ' > "$E/tracked-before.log"; [ "$(cat "$E/tracked-before.log")" = 0 ] && git -C "$W" switch --detach origin/main > "$E/switch.log" 2>&1; echo $? > "$E/switch.rc"` — 기대 `0`. 옛 절: `git -C "$R" show acbd954:docs/plan/jaehwan-tasks.md | awk '/^#### J-27 /{f=1} /^#### J-28 /{f=0} f' > "$E/task-acbd954.txt"` — 기대 `head -1 "$E/task-acbd954.txt"`가 `#### J-27 `로 시작. `git -C "$W" show origin/main:docs/plan/jaehwan-tasks.md > "$E/tasks-main.md"; git -C "$W" rev-parse origin/main > "$E/main-rev.log"; awk '/^#### J-27 /{f=1} /^#### J-28 /{f=0} f' "$E/tasks-main.md" > "$E/task.txt"` — 기대 `head -1 "$E/task.txt"`가 `#### J-27 `로 시작. 펜스: `printf '%s\n' "j27-gen-py j27_gen.py" "j27-argv-py j27_argv.py" "j27-run-sh j27_run.sh" "j27-where-sh j27_where.sh" "j27-logcheck-sh j27_logcheck.sh" "j27c-pre-sh j27c_pre.sh" "j27c-note-sh j27c_note.sh" "j27-expected-sh expected-sh.in" "j27-expected-argv expected-argv.in" "j27-expected-logcheck expected-logcheck.txt" "j27-expected-script-greps expected-script-greps.txt" "j27-dwell-sha256 expected-dwell-sha256.txt" "j27c-expected-pre expected-pre.txt" | while read -r n f; do awk -v n="$n" 'BEGIN {t = "\140\140\140"} $0 == t && x {x = 0} x {print} index($0, t) == 1 && substr($0, 4) ~ ("^[a-z]+ " n "$") {x = 1}' "$E/task.txt" > "$E/$f"; done; cd "$E" && wc -l j27_gen.py j27_argv.py j27_run.sh j27_where.sh j27_logcheck.sh j27c_pre.sh j27c_note.sh expected-sh.in expected-argv.in expected-logcheck.txt expected-script-greps.txt expected-dwell-sha256.txt expected-pre.txt > "$E/extract-wc.log"` — 기대 앞 숫자 순서대로 `30`·`26`·`26`·`29`·`15`·`20`·`18`·`34`·`15`·`11`·`8`·`1`·`8`, 끝 줄 `241 total`. 채우기: `sed -e "s#@W@#$W#g" -e "s#@HOME@#$HOME#g" "$E/expected-sh.in" > "$E/expected-run_game_perf.sh"; sed -e "s#@W@#$W#g" "$E/expected-argv.in" > "$E/expected-argv.txt"`. 조건: `sh "$E/j27c_pre.sh" "$W" "$E" > "$E/pre.log" 2>&1; diff "$E/expected-pre.txt" "$E/pre.log" > "$E/pre.diff"; echo "exit=$?" >> "$E/pre.diff"` — 기대 `exit=0` 한 줄. 다른 것이 `model 1` 한 줄뿐이고 `grep -c 'qwen3.8-flash-next .* IDLE ' "$E/lms-ps-before.log"`가 `1`(생성 중이 아님)이며 ②가 참일 때만 `/usr/bin/timeout 120 "$HOME/.lmstudio/bin/lms" unload qwen3.8-flash-next > "$E/lms-unload.log" 2>&1; echo $? > "$E/lms-unload.rc"` — 기대 `0`(`lms unload --help`: `lms unload [options] [identifier]`; 되돌릴 수 있는 로컬 동작)을 하고 조건 명령을 `pre-2.log`·`pre-2.diff`로 한 번 더 돌린다 — 기대 `exit=0`. 크래시 폴더 기준: `ls -1 "$HOME/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Crashes" > "$E/crashes-before.log" 2>&1`.
  - **C2 잠금**: 확인(기대 첫 줄 `no lock`), 잡기(기대 `lock-take.rc` `0`).
  - **C3 빌드(백그라운드)**: 갱신 ①(`build`) 뒤 `cd "$W" && /usr/bin/timeout 1800 ./tools/ue/build.sh > "$E/build.log" 2>&1; echo $? > "$E/build.rc"`를 갱신 루프 ②로 감싸 돌린다 — 기대 `0`.
  - **C4 생성(백그라운드)**: 갱신 ①(`gen`) 뒤 옛 할 일 3의 명령 그대로(`UnrealEditor-Cmd … "-ExecCmds=py $E/j27_gen.py,QUIT_EDITOR" -unattended -nullrhi -nosplash -nopause -nosound`, `timeout 900`, 갱신 루프 ②, 끝에 `cp "$HOME/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log" "$E/gen-editor.log"`). 기대도 같다: `gen.rc` `0`, `gen-editor.log`의 세 `grep -c` `1`·`1`·`0`, `dwell-sha.diff`·`sh-diff.log`·`script-greps.diff` `exit=0`.
  - **C4b 마커 확인(크래시가 날 수 없는 실행, 백그라운드)**: 갱신 ①(`marker`) 뒤 `M="$HOME/Library/Application Support/Epic/NotAllowedUnattendedBugReports"; touch "$E/marker-b"; sleep 1; /usr/bin/timeout 300 "/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor" "$W/unreal/Golmok/Golmok.uproject" -game -nullrhi -unattended -nosplash -ExecCmds=quit > "$E/game-marker.log" 2>&1; echo $? > "$E/game-marker.rc"; [ "$M" -nt "$E/marker-b" ]; echo "newer=$?" > "$E/game-marker-newer.log"` — 기대 `game-marker-newer.log` `newer=0`(에디터 바이너리 `-game`이 그 키를 `False`로 읽었다). `newer=0`이 아니면 멈춘다(C5를 돌리지 않는다).
  - **C5 실행(백그라운드)**: 갱신 ①(`run`) 뒤 `cd "$W" && touch "$E/marker" && date +%F > "$E/run-date.log" && git -C "$W" rev-parse --short HEAD > "$E/sha.log" && /usr/bin/timeout 900 /bin/sh "$E/j27_run.sh" "$W" "$E" > "$E/wrapper.log" 2>&1; echo $? > "$E/wrapper.rc"`를 갱신 루프 ②로 감싸 돌린다. 끝나면 바로 `"$HOME/.lmstudio/bin/lms" ps > "$E/lms-ps-run.log" 2>&1`. 기대: `wrapper.rc`·`run.rc`·`game-argv.rc` `0`, `game-pid.log` 숫자 한 줄. 그다음 옛 할 일 4의 확인을 같은 이름으로: `argv.diff`·`logcheck.diff` `exit=0`, `editor-after.rc` `1`, `game-cp.rc` `0`, `run-warn.log`·`run-timeout.log` `0`. 더하는 확인 — 스크립트 rc는 크래시에도 0이므로(설계 4) 로그로 본다: `grep -c 'appError called' "$E/game.log" > "$E/apperror.log"` — 기대 `0`. `ls -1 "$HOME/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Crashes" > "$E/crashes-after.log" 2>&1; diff "$E/crashes-before.log" "$E/crashes-after.log" > "$E/crashes.diff"; echo "exit=$?" >> "$E/crashes.diff"` — 기대 `exit=0` 한 줄. 넓은 `find`(옛 할 일 4 끝의 명령 그대로, `timeout 300`)와 `sh "$E/j27_where.sh" "$W" "$E" > "$E/where.log"` — 기대 분기 A(`class candidate-1` 또는 `candidate-2`, `wide 1`, `wide-same yes`). 잠금 풀기 — 기대 `0`.
  - **C6 CSV·`golmok-perf`**: 옛 할 일 5의 분기 A 명령 그대로(`csv-cmp.rc` `0`, `csv-header.log` `1`, `user-copy.diff` `exit=0`, `perf.rc` `0`, `perf.md` 3줄·머리 줄·라벨 줄 1). 분기 B는 이 카드에서 멈춘다(후보 밖 위치는 J-16 설계를 바꾸는 일이다).
  - **C7 기록(영록 문서 브랜치)**: `sh "$E/j27c_note.sh" "$E" > "$E/note27.txt"; echo $? > "$E/note.rc"` — 기대 `0`, 한 줄. `cd "$R" && awk -v note="$(cat "$E/note27.txt")" '/^\| 27 \| /{sub(/ \|$/, " " note " |")} {print}' docs/runbooks/mac-setup.md > "$E/mac-setup.new" && cat "$E/mac-setup.new" > docs/runbooks/mac-setup.md; echo $? > "$E/note-insert.rc"` — 기대 `0`, `git diff --numstat -- docs/runbooks/mac-setup.md` `1	1	docs/runbooks/mac-setup.md`, "선행 기록 넣기" 3의 칸 자기 검사(번호 `1`, 기대 `1`·`0`)와 4의 근거 바꾸기(번호 `2`). pc-verify-wp06 §12 #17 칸 끝에 날짜 메모 "Mac 에디터 바이너리 `-game`은 §8 #27"을 더한다(규칙 16 — 있는 글은 두고 더한다).
  - **C8 뒤(브랜치 되돌리기·모델 다시 올리기)**: `git -C "$W" switch "$(cat "$E/branch-before.log")" > "$E/switch-back.log" 2>&1; echo $? > "$E/switch-back.rc"` — 기대 `0`. `/usr/bin/timeout 600 "$HOME/.lmstudio/bin/lms" load qwen3.8-flash-next --identifier qwen3.8-flash-next -c 262144 --parallel 4 --ttl 3600 -y > "$E/lms-load.log" 2>&1; echo $? > "$E/lms-load.rc"; "$HOME/.lmstudio/bin/lms" ps > "$E/lms-ps-after.log" 2>&1` — 기대 `lms-load.rc` `0`, `lms-ps-after.log`에 `qwen3.8-flash-next` 줄이 있고 `262144`·`4`(2026-11-28 `lms-ps.log`와 같은 설정). 그 뒤에만 재환에게 다음 과제를 보낸다. 다르면 재환 배정을 멈추고 소유자에게 알린다(LM Studio 설정은 소유자 몫).
  - **멈춤 조건**: "언제"의 ①②③ 중 하나가 거짓. `fetch.rc`·`build.rc`·`gen.rc`·`wrapper.rc`(124 포함)·`run.rc`·`game-argv.rc`·`lock-take.rc`·갱신 rc·`lock-release.rc`·`note.rc`·`note-insert.rc`·`switch.rc`·`switch-back.rc`·`lms-load.rc`가 0이 아님. `game-marker-newer.log`가 `newer=0`이 아님(C5를 돌리지 않는다). `extract-wc.log`·`pre.diff`·`dwell-sha.diff`·`sh-diff.log`·`script-greps.diff`·`argv.diff`·`logcheck.diff`·`crashes.diff`·`user-copy.diff`가 기대와 다름. `apperror.log`가 0이 아님 — 이때는 `CrashReportClient.log`에서 `All uploads done`을 세어 `"$E/crc-upload.log"`에 두고, 1 이상이면 외부 발송이 다시 일어난 것이므로 그 사실을 소유자에게 알리고 J-29를 다시 연다. 모델을 내린 상태의 OutOfMemory면 메모리 경합 추정이 틀린 것이다 — 원인을 Claude 레인 과제로 연다. `where.log`가 분기 A가 아님. macOS 권한 창(누르지 않는다).
  - **완료 기준**: (a) C1 `fetch.rc` `0`, `task.txt` 첫 줄, `extract-wc.log` 기대, `pre.diff`(또는 `pre-2.diff`) `exit=0`. (b) C3·C4 rc `0`과 세 `diff` `exit=0`, C4b `game-marker-newer.log` `newer=0`. (c) C5 rc 셋 `0`, `argv.diff`·`logcheck.diff`·`crashes.diff` `exit=0`, `apperror.log` `0`, `lms-ps-run.log`에 `qwen3.8-flash-next` 0줄, `where.log` 분기 A, `lock-release.rc` `0`. (d) C6 값 모두 기대. (e) C7 `note.rc`·`note-insert.rc` `0`, numstat `1	1`, 칸 자기 검사 두 번 `0`, 근거 `PR #번호`. (f) `switch-back.rc` `0`, `lms-load.rc` `0`, `lms-ps-after.log` 기대.
- **왜 재환이 아닌가 / 위험**: 남은 절반은 모델을 내린 상태가 전제이고, 재환은 자기 모델을 내릴 수 없다. 메모리 경합은 [미확인] 추정이라 재환 절로 쓰면 "다시 크래시하면?"이 판단으로 남고, 그 크래시는 외부 발송이다. 위험: ① J-29가 늦으면 이 카드도 늦는다 — J-16은 이 카드를 기다리지 않으므로(설계 5) 핵심 경로에는 V-05 S12 실제 실행만 남는다. ② `lms unload`·JIT 다시 올림의 CLI 동작은 [미확인] — C1·C8이 rc와 `lms ps`로 잰다. ③ 영록이 재환 worktree에서 UE를 돌린다 — 재환 유휴("언제" ②), `tracked 0`·`code same`(C1)이 막고, 커밋은 하지 않는다(생성물은 `Saved/` 아래, `.gitignore` 4행). ④ 같은 위험(모델 로드 + GPU `-game`·패키지 실행 + 크래시 업로드)은 재환의 J-19·J-22에도 있다 — 2026-11-28 J-27 뒤 새 크래시 폴더는 없다(`~/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Crashes`의 마지막 폴더가 pid 11197), 그래도 J-29를 설계 선행 맨 앞으로 둔다(설계 6).
- **dry-run 범위(Opus 2026-11-28 문서 9, `origin/main` `acbd954` scratch 사본 — git 저장소로 만든 것)**: 이 절을 넣은 `jaehwan-tasks.md`에서 C1의 절 뽑기(`head -1`이 `#### J-27 `)와 펜스 13개 뽑기(`\140` awk, 위 `extract-wc.log` 기대 숫자와 `241 total`)를 돌렸고, 옛 펜스 10개는 재환이 2026-11-28에 뽑아 쓴 파일(`$TMPDIR/jaehwan/J-27/`)과 `cmp`로 바이트가 같았다. `j27c-pre-sh`는 `/bin/sh`·zsh에서 가짜 `HOME`(가짜 `lms`)·가짜 `TMPDIR`·scratch 저장소로 돌려 `expected-pre.txt`와 `diff` 0이었고, 변형마다 그 줄만 달라졌다: 모델 로드(`model 1`), 잠금 파일(`lock busy`), 추적 파일 변경(`tracked 1`), `Source` 아래 커밋(`code differs`), `L_ZoneTest.umap` 없음(`asset no Maps/L_ZoneTest.umap`), `lms` 없음(`lms-rc 127` — `grep`만 보면 `model 0`이 되는 경우를 rc 줄이 잡는다), 인자에 프로젝트 경로가 든 프로세스(`editor running`). `j27c-note-sh`는 두 셸에서 같은 한 줄(rc 0), `class candidate-2`면 후보 2 문구, `class none` rc 3, `lms-ps-run.log`에 모델 줄(2026-11-28 `lms-ps.log` 사본) rc 4였고, 그 줄에 규칙 17 b의 `grep -n -E` 0건, `|`·`&`·역슬래시 0개(awk `sub`에 안전). "선행 기록 넣기" 1~4를 scratch 사본에서 그대로 돌렸다: 세 rc `0`, `check-1.log` 다섯 줄 기대대로(`row27=0`·`1`·`1`·`unfit=0`·`2	1	docs/runbooks/mac-setup.md`), 바뀐 #6 줄 = 옛 #6 줄 끝에 메모를 더한 것, 칸 자기 검사 `2`·`0`, 가짜 번호로 근거 바꾸기 뒤 `0`·`1`, 다시 검사 `2`·`0`. 그 상태를 커밋한 뒤 C7의 메모 붙이기: rc `0`, numstat `1	1`, 바뀐 줄 자기 검사 `0`, 두 번째 근거 바꾸기도 그 줄만 바꿨다. 파이썬 게이트는 이 두 문서를 바꾼 scratch 사본에서 돌렸다: `All checks passed!`, `124 files already formatted`, `1940 passed, 3 skipped`, `OK (uproject, ini, json, links, gitattributes, conflicts, gasp)`(행 문구를 마지막으로 고친 뒤에는 `check_repo.py`·`ruff check`만 다시 돌려 같았다 — 테스트는 이 두 문서를 읽지 않는다). `j27-unfit-row`에는 `영록`이 있지만 런북 칸이 아니라 이 파일의 표라 규칙 17 b 검사 대상이 아니다. dry-run하지 못한 것: 실제 `lms unload`·`lms ps`(모델 없음일 때의 출력과 rc)와 JIT 다시 올림, J-29의 키 확인(키가 아직 없다), 모델을 내린 상태의 실제 `build.sh`·생성·`-game` 실행(로그 줄의 실제 꼴은 2026-11-28 실행의 앞부분만 관찰됨), 넓은 `find`·`j27-where-sh`·`golmok-perf`의 실제 입력, 갱신 루프의 실제 240 s, `gh`·`git push`, shellcheck(이 Mac에 없다 — 이 절의 펜스는 CI가 보는 `tools/ue/*.sh`·`tools/mac/*.sh`가 아니다).

#### J-28 CI `swift build`(golmok-objcap) — 설계 선행
- **출처**: `tools/mac/objcap/Package.swift`(테스트 타깃 없음), `tools/tests/test_mac_objcap.py:38-65`(텍스트 검사만), CI에 swift 단계 없음(2026-11-28 조사).
- **설계 메모**: `macos-latest` 러너 Xcode SDK에 `PhotogrammetrySession`이 있는지 [미확인]일 때의 처리(빌드만·`limits` 실행 여부), 핫스팟 훅.
- **허용 파일**: `ci.yml` `# [WP-21 hook]` 블록(별도 커밋).
- **완료 기준**: 로컬 `swift build -c release` + `golmok-objcap limits` 출력, CI 새 행 초록.
- **왜 재환 / 위험**: 명령 판정. 위험: 러너 SDK 차이.

#### J-29 크래시 리포트 무인 업로드 끄기: 새 `Config/DefaultEditorSettings.ini` 훅 블록 + 크래시 없는 헤드리스 확인 — 설계 확정(Opus 2026-11-28)
- **출처**: [DECISIONS.md](../DECISIONS.md) D-023 "D-007" 줄(:353, "CrashReportClient가 크래시 리포트(로컬 경로 포함)를 Epic으로 자동 업로드한다 … `[WP-21 hook]`"), [WP-21](WP-21-mac-recon-pipeline.md) "부수 발견"(:134)·남은 작업 5(:143 "크래시 업로드 끄기(D-007)"), [STATUS](STATUS.md) WP-21 행(:43)의 후속 목록("CrashReportClient 업로드 끄기(D-007)"), 이 파일의 옛 J-29 설계 메모. 공식 문서: [Configuration Files](https://dev.epicgames.com/documentation/en-us/unreal-engine/configuration-files-in-unreal-engine)(프로젝트 `Config/Default<CATEGORY>.ini`가 엔진 `Base` 파일을 덮는다), [Crash Reporting](https://dev.epicgames.com/documentation/en-us/unreal-engine/crash-reporting-in-unreal-engine)(Launcher 편집기 빌드는 리포트를 Epic에 보낸다, `bSendUnattendedBugReports` 기본 `true`, Editor Preferences > Privacy > Bug Reports). 엔진 소스(읽기만, `/Users/Shared/Epic Games/UE_5.8/Engine`, 2026-11-28 Opus가 읽은 줄): `Config/BaseEditorSettings.ini` :2(프로젝트 `DefaultEditorSettings.ini`가 이 값을 덮는다는 머리 주석)·:10-11(`[/Script/UnrealEd.CrashReportsPrivacySettings]` `bSendUnattendedBugReports=True`)·:13-14(`[/Script/UnrealEd.AnalyticsPrivacySettings]` `bSendUsageData=True`). `Source/Runtime/Core/Private/Mac/MacPlatformMisc.cpp` :2419-2423(크래시 때 그 키를 `GEditorSettingsIni`에서 읽는다, 기본 true)·:2425-2429(`bSendUsageData` 같음)·:2433-2438(라이선시 빌드이고 편집기가 아닐 때만 둘 다 false — Launcher 엔진은 해당하지 않는다는 엔진 주석 :2431-2432)·:2440-2445(무인 실행이고 값이 false면 `bCanRunCrashReportClient = false` — CrashReportClient를 띄우지 않는다)·:2468-2484(사람이 보는 크래시는 `-Unattended` 없이 띄운다 — 대화창, `bSendUsageData`가 false면 `-NoAnalytics`)·:2498-2502(CrashReportClient 실행 파일이 없으면 띄우지 못한다). `Source/Runtime/Core/Private/GenericPlatform/GenericPlatformCrashContext.cpp` :565(설정이 준비되면 `InitializeFromConfig`)·:800-803(`WITH_EDITOR`: 같은 키를 `GEditorSettingsIni`에서 읽는다)·:804-806(편집기가 아니고 분석 기능이 있는 빌드는 true)·:809-816(값이 false면 `ApplicationSettingsDir()/NotAllowedUnattendedBugReports`를 `OpenWrite` — 지우는 코드는 엔진에 없다, `grep -rn NotAllowedUnattendedBugReports Source`는 이 줄과 Windows의 읽기 :799뿐), `Public/GenericPlatform/GenericPlatformCrashContext.h:225`(기본 false — 그래서 편집기가 아닌 엔진 프로그램(UnrealPak 등)은 실행마다 이 마커를 쓴다). `Private/Apple/ApplePlatformFile.cpp:683-736`(`OpenWrite` = `O_CREAT|O_WRONLY` 뒤 `ftruncate(…, 0)`), `Private/Apple/ApplePlatformProcess.cpp:54-66`(`ApplicationSettingsDir` = `~/Library/Application Support/Epic/`), `Public/Misc/ConfigHierarchy.h:25`(`{PROJECT}/Config/Default{TYPE}.ini` 층), `Private/Misc/ConfigCacheIni.cpp:6638-6652`(`WITH_EDITOR` 빌드는 실행 모드와 상관없이 `EditorSettings`를 읽는다)·:6820(그 뒤 설정 준비 알림), `Source/Editor/UnrealEd/Classes/Analytics/CrashReportsPrivacySettings.h:18-25`·`AnalyticsPrivacySettings.h:18-25`(두 클래스 모두 `config=EditorSettings`). 저장소: `unreal/Golmok/Config/`에는 `DefaultEngine.ini`·`DefaultGame.ini`·`DefaultInput.ini`만 있고 `DefaultEditorSettings.ini`는 없다. `Config/Default*.ini`는 핫스팟이다([CLAUDE.md](../../CLAUDE.md) "Working alongside ChatGPT Astra", [DEVELOPMENT-PLAN §7.6](../DEVELOPMENT-PLAN.md)) — 새 파일이라 기존 줄을 바꾸거나 옮기지 않는다. `tools/scripts/check_repo.py:86-98`(`Config/*.ini`를 모두 파싱 — 새 파일도 게이트가 읽는다), :211-212·:308-314(GASP 가드의 ini 글자 검사 — 이 파일의 글자는 걸리지 않는다, Opus dry-run). 2026-11-28 Opus가 읽은 기계 상태(약 16:10 KST): `~/Library/Logs/Unreal Engine/CrashReportClient/CrashReportClient.log`(14:37) :26 `Command Line:` 줄에 `CrashReport-UE-Golmok-pid-11197-…`·`-Unattended`, :67 `DataRouterUrl: https://datarouter.ol.epicgames.com/…`, :70 `Got 7 pending files to upload`, :82 `All uploads done`. 같은 폴더의 로그 6개 모두 `All uploads done`이 있다. CrashReportClient 두 개가 CPU 약 100 %로 떠 있다(pid 16929 — 2026-11-27 02:30부터, pid 69882 — 2026-11-28 14:37부터). 마커 `~/Library/Application Support/Epic/NotAllowedUnattendedBugReports`는 0바이트, 수정 시각 2026-11-28 16:01:49(앞서 14:49) — 같은 분의 UnrealPak 로그(14:49:07, 16:01:50)와 맞는다(편집기가 아닌 프로그램이 쓴다는 위 소스와 같다). 사용자 층 `~/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Config/MacEditor/EditorSettings.ini`에 `PrivacySettings` 줄 0. [mac-recon.md](../runbooks/mac-recon.md) §6 표는 #24(:249, `| 24 | Brush 다음 릴리스의 CLI 플래그 변화 |`)에서 끝나고 그 뒤가 빈 줄·§7이다. mac-setup §8 #27은 J-27 자리다.
- **이력**: 옛 "설계 선행" 메모(키는 `BaseEngine.ini`나 CrashReportClient 소스에서 정한다, 완료 기준 "패키지 `Config` 스테이징에 키가 있는지 `grep`")를 이 절이 대신한다. 키는 `BaseEngine.ini`가 아니라 `EditorSettings` 층에 있고(위 출처), 패키지 게임은 편집기 빌드가 아니라 `EditorSettings`를 읽지 않으므로(:6638 `WITH_EDITOR`) 스테이징 `grep`은 아무것도 증명하지 못한다 — 그래서 완료 기준을 "크래시 없는 헤드리스 마커 확인"으로 바꿨다. "시험으로 크래시를 일으키지 않는다"는 그대로다. 지금 이 절은 배정할 수 있다.
- **설계 (확정, Opus 2026-11-28)**: 재환은 아래를 그대로 옮긴다. 바꿀 점이 보이면 고치지 말고 묻는다.
  1. **키와 파일**: 새 파일 `unreal/Golmok/Config/DefaultEditorSettings.ini`의 내용은 펜스 `j29-hook-ini` 여덟 줄뿐이다(할 일 3이 펜스에서 뽑은 파일을 `cp`로 넣는다 — 손으로 쓰지 않는다). `[/Script/UnrealEd.CrashReportsPrivacySettings]` `bSendUnattendedBugReports=False`가 이 과제의 목적이다(D-007·D-019 — 무인 실행의 크래시가 로컬 경로가 든 리포트를 Epic으로 보내지 않게). 같은 블록의 `[/Script/UnrealEd.AnalyticsPrivacySettings]` `bSendUsageData=False`는 Opus가 넣기로 정했다: Epic으로 나가는 다른 통로(편집기 사용 통계)이고, 사람이 보는 크래시에서는 CrashReportClient에 `-NoAnalytics`가 붙는다(:2481-2484). 같은 층·같은 꼴이라 따로 과제를 둘 이유가 없다. 다만 이 과제의 확인은 첫 키만 본다 — 둘째 키의 효과는 `[미확인]`으로 남긴다(설계 5). 되돌리려면 이 파일을 지우면 된다(영록이 병합 때 D-025로 기록, 소유자가 뒤집을 수 있다).
  2. **크래시 없는 확인**: 편집기 빌드는 시작할 때 이 키를 읽고 값이 false일 때만 마커를 `OpenWrite`한다(:809-816). 마커는 이미 있고 엔진은 지우지 않으므로 파일을 옮기거나 지우지 않고 **수정 시각**으로 본다: 기준 파일을 `touch`하고 1초 뒤 편집기를 한 번 띄워 끈 다음, `find <마커> -newer <기준>`이 마커 경로 한 줄을 내면 `1`, 아니면 `0`이다. `OpenWrite`의 `ftruncate(0)`은 이미 0바이트인 파일의 수정 시각도 바꾼다(Opus가 이 Mac에서 `os.ftruncate`로 확인 — `open`만으로는 바뀌지 않았다; 위 UnrealPak 시각도 같다). **음성 대조를 먼저** 한다: 브랜치를 `origin/main`에서 막 만든 직후, 훅 파일이 없는 트리에서 같은 실행 → `0`이어야 한다. 그다음 훅 파일을 넣고 같은 실행 → `1`이어야 한다. 실행은 펜스 `j29-run-sh`(`UnrealEditor-Cmd … -ExecCmds=QUIT_EDITOR -unattended -nullrhi -nosplash -nopause -nosound`, `/usr/bin/timeout 900`) 하나로 두 번 같은 글자로 돈다(J-12b·J-25 꼴, GPU를 쓰지 않는다). 음성 대조 실행은 아직 끄기 전의 설정으로 돌므로 그 실행에서 크래시가 나면 리포트가 올라간다 — 이 위험은 지난 모든 무인 실행과 같고(14 s 남짓의 `QUIT_EDITOR` 실행), 이 과제 뒤의 실행부터 사라진다. 그래서 J-29는 다음 UE 과제들보다 먼저 배정한다.
  3. **크래시를 일으키지 않는다·CrashReportClient를 돌리지 않는다**: 크래시·`ensure`·`debug crash` 같은 명령, CrashReportClient 실행, 크래시 폴더·CrashReportClient 로그·마커를 고치거나 지우는 것은 모두 금지다. "크래시가 없었다"는 읽기만으로 본다(펜스 `j29-procs-sh`, 세 시점 `t0`·`t1`·`t2`): 떠 있는 CrashReportClient pid 목록이 세 시점에서 같다, `~/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Crashes`의 폴더 목록이 같다, CrashReportClient 로그의 수정 시각이 같다, 편집기 로그 사본에 `=== Critical error` 0줄·`LogExit: Exiting.` 1줄. 지금 떠 있는 CrashReportClient 두 개(출처)는 이 과제의 것이 아니다 — 건드리지 않고 pid만 기록한다(목록이 같으면 된다). 패키지 `.app`은 이 과제가 보지 않는다(설계 5).
  4. **다른 프로그램이 마커를 쓰는 것을 막는다**: 편집기가 아닌 엔진 프로그램(UnrealPak·ShaderCompileWorker·패키지 게임 등)도 실행마다 마커를 쓴다(출처). 그래서 세 시점마다 `Binaries/Mac/(UnrealEditor|UnrealPak|ShaderCompileWorker)`·`UnrealBuildTool`·`Golmok.app/Contents/MacOS/` 프로세스가 없어야 하고(`pgrep` rc `1`), GUI 잠금을 두 실행 내내 잡는다(영록·다른 세션의 패키지·편집기 실행을 막는 신호). 실행 사이에 짧게 돌고 끝난 다른 프로그램은 `pgrep`이 못 잡는다 — 음성 대조가 `0`이어야 하는 것이 그 창의 잡음이 없다는 증거이고, 양성 창의 같은 잡음은 남은 위험이다(왜 재환 / 위험 ②).
  5. **넓게 쓰지 않는다(규칙 1·3·15)**: 기록 줄(펜스 `j29-row-sh`, mac-recon §6 #25 — #24 다음 줄, 새 번호)은 "이번 실행에서 편집기 바이너리의 무인 실행이 그 값을 `False`로 읽었다"까지만 쓴다. "무인 크래시에서 CrashReportClient가 뜨지 않는다"는 엔진 소스 읽기라고 적고 실행으로 확인했다고 쓰지 않는다. 사람이 보는 편집기 크래시(CrashReportClient 대화창이 뜨고 보낼지는 사람이 고른다 — :2476-2484), `bSendUsageData=False`의 효과, 패키지 게임(편집기 빌드가 아니라 이 파일을 읽지 않는다 — 패키지에 CrashReportClient가 있는지는 그 패키지의 SHA와 함께 따로 잰다), Windows는 `[미확인]`이다. 줄의 다른 값은 모두 고정 문구이고 날짜·SHA만 채운다. 줄에는 `.log`·`영록`·`R`+세 자리 숫자가 없다(Opus dry-run, 칸 자기 검사 0건).
  6. **양성 실행이 `0`이면**(층이 먹지 않았다 — 사용자 층이나 다른 층이 덮었을 수 있다): 멈추고 묻는다. `-ini:` 덮어쓰기, 사용자 `EditorSettings.ini` 수정, 편집기 Preferences 바꾸기, 다시 돌리기를 하지 않는다. 음성 대조가 `1`이어도(창 안에 다른 쓰는 쪽이 있었다) 멈추고 묻는다.
  7. **커밋 셋이 아니라 둘**: 커밋 1 = 훅 파일 하나만(핫스팟 규칙 — 별도 커밋). PR은 커밋 1만으로 연다. 커밋 2 = mac-recon §6 #25 한 줄 — 이 과제에서는 PR 번호가 나온 **뒤에** 줄을 넣으므로, 펜스가 만든 `근거: J-29 PR.` 표식을 넣고(칸 자기 검사 1) 같은 커밋 안에서 `근거: PR #<번호>.`로 바꾼다(칸 자기 검사 2). 상시 규칙 "PR 본문 공통" 8의 "커밋 2가 표식을 PR 번호로 바꾼다"와 같은 결과다(커밋 1이 훅이라 줄이 커밋 1에 들어가지 않을 뿐이다).
  8. **코드 변경 없음**: C++·Python·`tools/ue/*.sh`·다른 `Config/` 파일·테스트는 고치지 않는다. 생성물(`Saved/`·`Binaries/`·`Intermediate/`)은 `.gitignore`다.

```ini j29-hook-ini
; [WP-21 hook] D-007 / D-019: unattended editor runs (-unattended) must not send crash reports, which carry local paths, to Epic.
; Engine default is True (Engine/Config/BaseEditorSettings.ini); with False an unattended crash does not start CrashReportClient.
[/Script/UnrealEd.CrashReportsPrivacySettings]
bSendUnattendedBugReports=False
; Editor usage analytics off too (attended crashes then start CrashReportClient with -NoAnalytics).
[/Script/UnrealEd.AnalyticsPrivacySettings]
bSendUsageData=False
; [/WP-21 hook]
```

```sh j29-engine-sh
#!/bin/sh
# J-29: the engine lines the design relies on, counted in this Mac's engine (usage: sh j29_engine.sh), read-only.
G="/Users/Shared/Epic Games/UE_5.8/Engine"
c() { printf '%s %s\n' "$1" "$2"; }
c base-default "$(grep -c -x -F 'bSendUnattendedBugReports=True' "$G/Config/BaseEditorSettings.ini")"
c base-usage "$(grep -c -x -F 'bSendUsageData=True' "$G/Config/BaseEditorSettings.ini")"
c mac-read "$(grep -c -F 'TEXT("bSendUnattendedBugReports"), bSendUnattendedBugReports, GEditorSettingsIni' "$G/Source/Runtime/Core/Private/Mac/MacPlatformMisc.cpp")"
c mac-gate "$(grep -c -F 'if (bUnattended && !bSendUnattendedBugReports)' "$G/Source/Runtime/Core/Private/Mac/MacPlatformMisc.cpp")"
c marker-name "$(grep -c -F 'TEXT("NotAllowedUnattendedBugReports")' "$G/Source/Runtime/Core/Private/GenericPlatform/GenericPlatformCrashContext.cpp")"
c marker-if "$(grep -c -F 'if (!NCached::UserSettings.bSendUnattendedBugReports)' "$G/Source/Runtime/Core/Private/GenericPlatform/GenericPlatformCrashContext.cpp")"
c project-layer "$(grep -c -F 'TEXT("{PROJECT}/Config/Default{TYPE}.ini")' "$G/Source/Runtime/Core/Public/Misc/ConfigHierarchy.h")"
c editorsettings-load "$(grep -c -F 'Context.Load(TEXT("EditorSettings"), GEditorSettingsIni);' "$G/Source/Runtime/Core/Private/Misc/ConfigCacheIni.cpp")"
```

```text j29-expected-engine
base-default 1
base-usage 1
mac-read 1
mac-gate 1
marker-name 1
marker-if 1
project-layer 2
editorsettings-load 1
```

```sh j29-procs-sh
#!/bin/sh
# J-29: machine state that a crash or another UE program would change (usage: sh j29_procs.sh <E> <tag>).
E=$1
T=$2
pgrep -f -l 'Binaries/Mac/(UnrealEditor|UnrealPak|ShaderCompileWorker)|UnrealBuildTool|Golmok\.app/Contents/MacOS/' > "$E/$T-ue.log"
echo $? > "$E/$T-ue.rc"
pgrep -x CrashReportClient | sort -n > "$E/$T-crc.log"
ls -1 "$HOME/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Crashes" > "$E/$T-crash-dirs.log" 2>&1
CL="$HOME/Library/Logs/Unreal Engine/CrashReportClient/CrashReportClient.log"
if [ -f "$CL" ]; then stat -f %m "$CL"; else echo none; fi > "$E/$T-crc-log-mtime.log"
U="$HOME/Library/Application Support/Epic/UnrealEngine/5.8/Saved/Config/MacEditor/EditorSettings.ini"
if [ -f "$U" ]; then grep -c -F 'PrivacySettings' "$U"; else echo missing; fi > "$E/$T-user-privacy.log"
M="$HOME/Library/Application Support/Epic/NotAllowedUnattendedBugReports"
if [ -e "$M" ]; then stat -f '%Sm %z' -t '%FT%T%z' "$M"; else echo none; fi > "$E/$T-marker-stat.log"
```

```sh j29-run-sh
#!/bin/sh
# J-29: one headless editor start and quit, no crash (usage: sh j29_run.sh <E> <tag>); writes <tag>-* files in E.
E=$1
T=$2
W="$HOME/projects/golmok-jaehwan"
UE="/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor-Cmd"
M="$HOME/Library/Application Support/Epic/NotAllowedUnattendedBugReports"
EL="$HOME/Library/Logs/Unreal Engine/GolmokEditor/Golmok.log"
touch "$E/$T-ref"
sleep 1
cd "$W" || { echo 3 > "$E/$T-run.rc"; exit 3; }
/usr/bin/timeout 900 "$UE" "$W/unreal/Golmok/Golmok.uproject" -ExecCmds=QUIT_EDITOR -unattended -nullrhi -nosplash -nopause -nosound > "$E/$T-run.log" 2>&1
echo $? > "$E/$T-run.rc"
find "$M" -newer "$E/$T-ref" > "$E/$T-marker-find.log" 2>&1
grep -c -x -F "$M" "$E/$T-marker-find.log" > "$E/$T-marker-newer.log"
[ "$EL" -nt "$E/$T-ref" ]
echo "newer=$?" > "$E/$T-editor-new.log"
cp "$EL" "$E/$T-editor.log"
echo $? > "$E/$T-editor-cp.rc"
```

```sh j29-check-sh
#!/bin/sh
# J-29: fixed values for the two headless runs (usage: sh j29_check.sh <E>), one "label value" per line.
E=$1
c() { printf '%s %s\n' "$1" "$2"; }
same() { if [ -s "$E/t0-$1.log" ] && cmp -s "$E/t0-$1.log" "$E/t1-$1.log" && cmp -s "$E/t0-$1.log" "$E/t2-$1.log"; then echo same; else echo differ; fi; }
for T in neg pos; do
  c "$T-hook-file" "$(cat "$E/$T-hook.log")"
  c "$T-run-rc" "$(cat "$E/$T-run.rc")"
  c "$T-marker-newer" "$(cat "$E/$T-marker-newer.log")"
  c "$T-editor-new" "$(cat "$E/$T-editor-new.log")"
  c "$T-cmdline" "$(grep -F 'LogInit: Command Line: ' "$E/$T-editor.log" | grep -F 'QUIT_EDITOR' | grep -F -e '-unattended' | grep -c -F -e '-nullrhi')"
  c "$T-exiting" "$(grep -c -F 'LogExit: Exiting.' "$E/$T-editor.log")"
  c "$T-critical" "$(grep -c -F '=== Critical error' "$E/$T-editor.log")"
done
c ue-procs "$(cat "$E/t0-ue.rc") $(cat "$E/t1-ue.rc") $(cat "$E/t2-ue.rc")"
c crc-pids "$(if cmp -s "$E/t0-crc.log" "$E/t1-crc.log" && cmp -s "$E/t0-crc.log" "$E/t2-crc.log"; then echo same; else echo differ; fi)"
c crash-dirs "$(same crash-dirs)"
c crc-log-mtime "$(same crc-log-mtime)"
c user-privacy "$(cat "$E/t0-user-privacy.log") $(cat "$E/t1-user-privacy.log") $(cat "$E/t2-user-privacy.log")"
```

```text j29-expected-check
neg-hook-file hook-file=1
neg-run-rc 0
neg-marker-newer 0
neg-editor-new newer=0
neg-cmdline 1
neg-exiting 1
neg-critical 0
pos-hook-file hook-file=0
pos-run-rc 0
pos-marker-newer 1
pos-editor-new newer=0
pos-cmdline 1
pos-exiting 1
pos-critical 0
ue-procs 1 1 1
crc-pids same
crash-dirs same
crc-log-mtime same
user-privacy 0 0 0
```

```sh j29-row-sh
#!/bin/sh
# J-29: prints mac-recon section 6 row 25 (usage: sh j29_row.sh <E>).
E=$1
date=$(cat "$E/run-date.log")
sha=$(cat "$E/sha.log")
printf '| 25 | 크래시 리포트 무인 업로드(CrashReportClient → Epic, D-007) | 엔진 기본값 `bSendUnattendedBugReports=True`(BaseEditorSettings.ini). 2026-11-28 무인 실행 크래시 1건의 리포트가 올라갔다 | 프로젝트 `Config/DefaultEditorSettings.ini` `[WP-21 hook]`의 `False`. 크래시 없이 창 없는 편집기를 한 번 띄우고 끈 뒤 `~/Library/Application Support/Epic/NotAllowedUnattendedBugReports`의 수정 시각을 본다 | %s J-29(SHA %s 작업 트리, `UnrealEditor-Cmd -nullrhi -unattended`, `QUIT_EDITOR` 1회씩): 훅 파일이 없는 트리의 실행 뒤에는 그 파일이 바뀌지 않았고, 훅 파일이 있는 트리의 실행 뒤에는 새로 써졌다 — 이번 실행에서 편집기가 그 값을 `False`로 읽었다. 크래시는 일으키지 않았다. 무인 실행의 크래시에서 CrashReportClient가 뜨지 않는 것은 엔진 소스(`MacPlatformMisc.cpp`) 읽기이고 실행으로 확인하지 않았다. 같은 블록의 `bSendUsageData=False`, 사람이 보는 편집기 크래시(대화창에서 보낼지 고른다), 패키지 게임, Windows는 [미확인]. 근거: J-29 PR. |\n' "$date" "$sha"
```

```sh j29-quotes-sh
#!/bin/sh
# J-29: quote and number checks of the PR draft (usage: sh j29_quotes.sh <E>); needs E/pr-body.md and E/quotes.tsv.
E=$1
B=$(printf '\140')
awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk -v b="$B" 'index($0, b b b) == 1 {c = !c; next} !c' > "$E/result-prose.txt"
grep -oE "${B}[^${B}]+${B}" "$E/result-prose.txt" | sed "s/^${B}//;s/${B}\$//" | sort -u > "$E/body-quotes.txt"
cut -f1 "$E/quotes.tsv" | sort -u > "$E/tsv-quotes.txt"
comm -23 "$E/body-quotes.txt" "$E/tsv-quotes.txt" > "$E/quotes-missing.log"
while IFS="$(printf '\t')" read -r q f; do if [ "$f" = "라벨" ]; then n="라벨"; else n=$(grep -F -c -- "$q" "$E/$f"); fi; printf '%s\t%s\t%s\n' "$n" "$f" "$q"; done < "$E/quotes.tsv" > "$E/quotes-check.log"
grep -oE '[0-9]{2,}' "$E/result-prose.txt" | sort -u > "$E/body-numbers.txt"
while read -r x; do
  n=0
  for f in check.log engine.log t0-crc.log t0-marker-stat.log t2-marker-stat.log neg-editor.log pos-editor.log row25-final.txt sha.log run-date.log hook-committed.log gate-2.log checks.log; do
    k=$(grep -c -- "$x" "$E/$f"); n=$((n + k))
  done
  printf '%s\t%s\n' "$n" "$x"
done < "$E/body-numbers.txt" > "$E/numbers-check.log"
```

- **명령 공통**: 셸 변수는 Bash 호출 사이에 남지 않는다. 그래서 **모든 명령은 `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/jaehwan/J-29";`로 시작하고**, 그 뒤는 `cd "$W" &&`·`cd "$W/tools" &&`·`git -C "$W"`·`"$E/…"` 절대 경로로 시작한다(상시 규칙). 아래 명령에는 이 앞머리를 적지 않았다. 돌린 명령 원문은 `printf '%s\n' '<명령>' >> "$E/commands.txt"`로 **돌리기 전에** 한 줄씩 더한다(규칙 10·19 b·21 — heredoc을 쓰지 않고, 줄을 고치거나 지우지 않는다). 각 단계의 "기대"와 다르면 **멈춤 조건**을 본다. 할 일 2·4의 편집기 실행(갱신 루프로 감싼 `sh "$E/j29_run.sh" …`)과 할 일 6·7의 게이트·CI 등록 대기·`gh pr checks --watch`는 **항상** 하네스의 백그라운드 실행으로 돌리고, 그 명령이 쓰는 파일(편집기는 `neg-run.rc`·`pos-run.rc`, 게이트는 `gate-<번호>.rc`, 대기는 `run-wait.rc`, watch는 `checks-watch.log`의 `exit=` 줄)이 생길 때까지 기다린다(명령은 바꾸지 않는다). 그 밖의 명령은 앞쪽(foreground)으로 돌린다. **시간 한도**: 이 절의 네트워크·대기 명령(`git fetch`·`git push`·`gh …`·`pytest`·`until` 대기)에는 모두 `/usr/bin/timeout`이 붙어 있다. 예외는 상시 규칙 "PR 본문 공통" 6의 `gh pr edit`·`gh pr view` 두 명령이다 — 그 소절에 적힌 그대로(시간 한도 없이) 돌리고, 규칙 5 확장의 점검표 줄에서 "감싸지 않은 것" 무리에 넣는다.
  - **GUI 잠금**(할 일 2~4, [mac-setup §3](../runbooks/mac-setup.md) 표의 규칙, 목적 `J-29-headless` — `-nullrhi` 편집기는 GPU를 쓰지 않지만 설계 4 때문에 두 실행 내내 잡는다): 확인 `L="$TMPDIR/claude/gui-foreground.lock"; if [ -e "$L" ]; then cat "$L"; else echo "no lock"; fi > "$E/lock-check.log"; date -u +%FT%TZ >> "$E/lock-check.log"` — 기대 첫 줄 `no lock`. 다른 줄이 있으면 **지우지 않고** 그 줄을 영록에게 보내고 기다린다. 잡기 `mkdir -p "$TMPDIR/claude" && (set -C; printf '%s %s %s\n' "재환" "J-29-headless" "$(date -u +%FT%TZ)" > "$TMPDIR/claude/gui-foreground.lock"); echo $? > "$E/lock-take.rc"` — 기대 `0`. 풀기 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-29-headless ' "$L" && rm "$L"; echo $? > "$E/lock-release.rc"` — 기대 `0`.
  - **잠금 갱신**([AGENTS.md](../../AGENTS.md) "UE를 같이 쓰는 규칙"·mac-setup §3: 20분이 지난 기록은 빈 것으로 보므로 잡은 쪽이 쓰는 동안 갱신한다): ① 할 일 2의 편집기 실행 바로 앞에 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-29-headless ' "$L" && printf '%s %s %s\n' "재환" "J-29-headless" "$(date -u +%FT%TZ)" > "$L"; echo $? > "$E/lock-refresh-neg.rc"`, 할 일 4의 편집기 실행 바로 앞에 `L="$TMPDIR/claude/gui-foreground.lock"; grep -q '^재환 J-29-headless ' "$L" && printf '%s %s %s\n' "재환" "J-29-headless" "$(date -u +%FT%TZ)" > "$L"; echo $? > "$E/lock-refresh-pos.rc"` — 기대 각각 `0`. 0이 아니면 잠금 파일을 지우거나 쓰지 않고 멈춘다. ② 편집기 실행은 갱신 루프로 감싸 **적힌 그대로** 돌린다(할 일 2·4의 명령에 이미 들어 있다): 앞에 `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-29-headless ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-29-headless" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!;`, 끝에 `; kill "$RP"`.
- **할 일**:
  1. **준비**: `mkdir -p "$E" && git -C "$W" status --porcelain > "$E/status-before.log"; grep -c -v '^?? ' "$E/status-before.log" > "$E/status-before-tracked.log"` — 기대 `0`(추적 파일 변경이 있으면 멈춘다 — 앞 과제의 작업물일 수 있다; `??` 줄은 그대로 두고, 아래 상태 비교는 모두 이 파일과의 `diff`다). `/usr/bin/timeout 120 git -C "$W" fetch origin > "$E/fetch.log" 2>&1; echo "exit=$?" >> "$E/fetch.log"` — 기대 끝 줄 `exit=0`. `git -C "$W" switch -c local/jaehwan-j29-crash-upload origin/main > "$E/switch.log" 2>&1; echo $? > "$E/switch.rc"` — 기대 `0`. `git -C "$W" rev-parse --short HEAD > "$E/sha.log"; git -C "$W" rev-parse HEAD origin/main | uniq | wc -l | tr -d ' ' > "$E/sha-same.log"` — 기대 `1`. `git -C "$W" show origin/main:docs/plan/jaehwan-tasks.md > "$E/tasks-main.md"; git -C "$W" rev-parse origin/main > "$E/main-rev.log"; { awk '/^#### J-29 /{f=1} /^#### J-30a /{f=0} f' "$E/tasks-main.md"; awk '/^### PR 본문 공통\(모든 과제\)$/{f=1} /^## 리뷰·병합 절차$/{f=0} f' "$E/tasks-main.md"; } > "$E/task.txt"`(규칙 14·17 c, 상시 규칙 "PR 본문 공통" 1) — 기대 `head -1 "$E/task.txt"`가 `#### J-29 `로 시작, `grep -c -x '### PR 본문 공통(모든 과제)' "$E/task.txt"` `1`. 펜스 추출(손으로 옮기지 않는다 — 이 명령에는 백틱이 없다, 백틱 세 개는 `sprintf`로 만든다): `printf '%s\n' "j29-hook-ini hook.ini" "j29-engine-sh j29_engine.sh" "j29-expected-engine expected-engine.txt" "j29-procs-sh j29_procs.sh" "j29-run-sh j29_run.sh" "j29-check-sh j29_check.sh" "j29-expected-check expected-check.txt" "j29-row-sh j29_row.sh" "j29-quotes-sh j29_quotes.sh" "common-ph-awk ph.awk" | while read -r n f; do awk -v n="$n" 'BEGIN {b = sprintf("%c%c%c", 96, 96, 96)} $0 == b && x {x = 0} x {print} !x && $0 ~ ("^" b "[a-z]+ " n "$") {x = 1}' "$E/task.txt" > "$E/$f"; done; cd "$E" && wc -l hook.ini j29_engine.sh expected-engine.txt j29_procs.sh j29_run.sh j29_check.sh expected-check.txt j29_row.sh j29_quotes.sh ph.awk > "$E/extract-wc.log"`(zsh는 따옴표 없는 변수를 낱말로 나누지 않으므로 `read -r n f`로 나눈다) — 기대(앞 숫자, 순서대로): `8`, `12`, `8`, `14`, `19`, `19`, `19`, `6`, `17`, `37`, 끝 줄 `159 total`. 겹침: `cd "$W" && /usr/bin/timeout 120 gh pr list --state open --json number,headRefName,files --jq '.[]|select(any(.files[]; .path=="docs/runbooks/mac-recon.md" or .path=="unreal/Golmok/Config/DefaultEditorSettings.ini"))|"\(.number) \(.headRefName)"' > "$E/overlap.log" 2>&1; echo $? > "$E/overlap.rc"` — 기대 `overlap.rc` `0`, `overlap.log` 빈 파일. 전제: `{ test -e "$W/unreal/Golmok/Config/DefaultEditorSettings.ini"; echo "hook-file=$?"; test -f "$W/unreal/Golmok/Binaries/Mac/libUnrealEditor-Golmok.dylib"; echo "editor-dylib=$?"; test -e "$HOME/Library/Application Support/Epic/NotAllowedUnattendedBugReports"; echo "marker=$?"; cd "$W" && grep -c '^| 24 | Brush ' docs/runbooks/mac-recon.md; grep -c '^| 25 | ' docs/runbooks/mac-recon.md; } > "$E/pre.log"` — 기대 다섯 줄 `hook-file=1`·`editor-dylib=0`·`marker=0`·`1`·`0`. 엔진 줄: `sh "$E/j29_engine.sh" > "$E/engine.log"; diff "$E/expected-engine.txt" "$E/engine.log" > "$E/engine.diff"; echo "exit=$?" >> "$E/engine.diff"` — 기대 `exit=0` 한 줄(엔진이 Opus가 읽은 것과 다르면 키 선택이 흔들린다 — 멈춤). 첫 시점: `sh "$E/j29_procs.sh" "$E" t0` — 기대 `t0-ue.rc` `1`(`t0-ue.log` 빈 파일), `t0-user-privacy.log` `0`. `t0-crc.log`(떠 있는 CrashReportClient pid, 0줄 이상)·`t0-marker-stat.log`는 기록만 한다.
  2. **음성 대조(훅 파일 없음)**: GUI 잠금 확인·잡기. `{ test -e "$W/unreal/Golmok/Config/DefaultEditorSettings.ini"; echo "hook-file=$?"; } > "$E/neg-hook.log"; date +%F > "$E/run-date.log"`(`run-date.log`는 기록 줄의 날짜 — Mac의 현지 날짜) — 기대 `neg-hook.log` `hook-file=1`. 잠금 갱신 ①의 `lock-refresh-neg.rc` 명령. 실행(하네스 백그라운드): `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-29-headless ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-29-headless" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; sh "$E/j29_run.sh" "$E" neg; kill "$RP"` — 기대 `neg-run.rc` `0`(124 = 시간 초과 — 멈춤, 다시 돌리지 않는다), `neg-marker-newer.log` `0`, `neg-editor-new.log` `newer=0`, `neg-editor-cp.rc` `0`. 둘째 시점: `sh "$E/j29_procs.sh" "$E" t1` — 기대 `t1-ue.rc` `1`. 여기서 `neg-marker-newer.log`가 `0`이 아니면 할 일 3으로 가지 않는다(설계 6 — 멈춤 순서).
  3. **훅 파일 넣기**: `cp "$E/hook.ini" "$W/unreal/Golmok/Config/DefaultEditorSettings.ini"; echo $? > "$E/hook-cp.rc"; diff "$E/hook.ini" "$W/unreal/Golmok/Config/DefaultEditorSettings.ini" > "$E/hook-diff.log"; echo "exit=$?" >> "$E/hook-diff.log"; { test -e "$W/unreal/Golmok/Config/DefaultEditorSettings.ini"; echo "hook-file=$?"; } > "$E/pos-hook.log"` — 기대 `hook-cp.rc` `0`, `hook-diff.log` `exit=0` 한 줄, `pos-hook.log` `hook-file=0`. `git -C "$W" status --porcelain | grep -v -x -F '?? unreal/Golmok/Config/DefaultEditorSettings.ini' | diff "$E/status-before.log" - > "$E/status-hook.diff"; echo "exit=$?" >> "$E/status-hook.diff"` — 기대 `exit=0` 한 줄(음성 대조 실행이 저장소에 남긴 것이 없고, 훅 파일은 추적되지 않은 파일 하나로만 보인다).
  4. **양성 실행(훅 파일 있음)**: 잠금 갱신 ①의 `lock-refresh-pos.rc` 명령. 실행(하네스 백그라운드): `L="$TMPDIR/claude/gui-foreground.lock"; ( while sleep 240; do grep -q '^재환 J-29-headless ' "$L" || exit 0; printf '%s %s %s\n' "재환" "J-29-headless" "$(date -u +%FT%TZ)" > "$L"; done ) > /dev/null 2>&1 & RP=$!; sh "$E/j29_run.sh" "$E" pos; kill "$RP"` — 기대 `pos-run.rc` `0`, `pos-marker-newer.log` `1`, `pos-editor-new.log` `newer=0`, `pos-editor-cp.rc` `0`. 셋째 시점: `sh "$E/j29_procs.sh" "$E" t2` — 기대 `t2-ue.rc` `1`. 잠금 풀기.
  5. **판정**: `sh "$E/j29_check.sh" "$E" > "$E/check.log"; diff "$E/expected-check.txt" "$E/check.log" > "$E/check.diff"; echo "exit=$?" >> "$E/check.diff"` — 기대 `exit=0` 한 줄. 기록만(판정하지 않는다, PR 본문용): `grep -F 'LogInit: Command Line: ' "$E/neg-editor.log" > "$E/neg-cmdline.log"; grep -F 'LogInit: Command Line: ' "$E/pos-editor.log" > "$E/pos-cmdline.log"`. `git -C "$W" status --porcelain | grep -v -x -F '?? unreal/Golmok/Config/DefaultEditorSettings.ini' | diff "$E/status-before.log" - > "$E/status-run.diff"; echo "exit=$?" >> "$E/status-run.diff"` — 기대 `exit=0` 한 줄.
  6. **게이트·커밋 1(훅)·push·PR**: `cd "$W/tools" && source .venv/bin/activate && { /usr/bin/timeout 300 ruff check . && /usr/bin/timeout 300 ruff format --check . && /usr/bin/timeout 1800 pytest -q && /usr/bin/timeout 300 python scripts/check_repo.py; } > "$E/gate-1.log" 2>&1; echo $? > "$E/gate-1.rc"`(하네스 백그라운드) — 기대 `0`(rc 124 = 시간 초과, 다시 돌리지 않고 멈춤; `check_repo.py`가 새 ini를 파싱한다). `[ "$E/gate-1.log" -nt "$W/unreal/Golmok/Config/DefaultEditorSettings.ini" ]; echo "newer=$?" > "$E/mtime-1.log"` — 기대 `newer=0`. 커밋(규칙 6·19 d — 확인과 커밋을 한 호출에서): `cd "$W" && git add unreal/Golmok/Config/DefaultEditorSettings.ini && git diff --cached --name-only > "$E/c1-files.log" && [ "$(cat "$E/c1-files.log")" = "unreal/Golmok/Config/DefaultEditorSettings.ini" ] && git diff --cached --numstat | tr '\t' ' ' > "$E/c1-numstat.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-29: [WP-21 hook] DefaultEditorSettings.ini — 무인 크래시 리포트·사용 통계 보내기 끄기" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c1-commit.log" 2>&1; echo $? > "$E/c1-commit.rc"; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-1.log"` — 기대 `c1-files.log` 한 줄 `unreal/Golmok/Config/DefaultEditorSettings.ini`, `c1-numstat.log` `8 0 unreal/Golmok/Config/DefaultEditorSettings.ini`, `c1-commit.rc` `0`, `author-1.log` `재환 <jaehwan.local@localhost>`. 커밋한 파일: `git -C "$W" show HEAD:unreal/Golmok/Config/DefaultEditorSettings.ini > "$E/hook-committed.log"; diff "$E/hook.ini" "$E/hook-committed.log" > "$E/hook-committed.diff"; echo "exit=$?" >> "$E/hook-committed.diff"` — 기대 `exit=0` 한 줄(`diff` 출력 없음 — 숫자·인용 검사는 `task.txt`의 추출본 `hook.ini`가 아니라 이 커밋본을 본다). `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-c1.diff"; echo "exit=$?" >> "$E/status-c1.diff"` — 기대 `exit=0` 한 줄. `/usr/bin/timeout 300 git -C "$W" push -u origin local/jaehwan-j29-crash-upload > "$E/push-1.log" 2>&1; echo "exit=$?" >> "$E/push-1.log"` — 기대 끝 줄 `exit=0`. PR 열기(첫 본문은 이 한 문장뿐 — 상시 규칙 "PR 본문 공통" 2, 규칙 2): `printf '%s\n' 'CI 진행 중 — 결과는 아래에 추가' > "$E/pr-body-initial.md"; cd "$W" && /usr/bin/timeout 120 gh pr create --base main --head local/jaehwan-j29-crash-upload --title "J-29: 크래시 리포트 무인 업로드 끄기([WP-21 hook] DefaultEditorSettings.ini) + 헤드리스 마커 확인" --body-file "$E/pr-body-initial.md" > "$E/pr-create.log" 2>&1; echo $? > "$E/pr-create.rc"` — 기대 `0`. PR 번호: `cd "$W" && /usr/bin/timeout 60 gh pr view local/jaehwan-j29-crash-upload --json number --jq .number > "$E/pr-number.log" 2> "$E/pr-number.err"` — 기대 `grep -c -x '[0-9][0-9]*' "$E/pr-number.log"` `1`, `wc -l < "$E/pr-number.log" | tr -d ' '` `1`(`pr-number.err`는 판정하지 않는다).
  7. **런북 한 줄·커밋 2·push·CI**: `sh "$E/j29_row.sh" "$E" > "$E/row25.txt"; echo $? > "$E/row.rc"` — 기대 rc `0`. `{ wc -l < "$E/row25.txt" | tr -d ' '; awk -F'|' '{print NF}' "$E/row25.txt"; } > "$E/row25-shape.log"` — 기대 두 줄 `1`·`7`(한 줄, 칸 다섯). 손으로 옮기지 않고 명령으로 #24 바로 뒤에 넣는다(규칙 19 d): `cd "$W" && [ "$(grep -c '^| 25 | ' docs/runbooks/mac-recon.md)" = 0 ] && [ "$(grep -c '^| 24 | Brush ' docs/runbooks/mac-recon.md)" = 1 ] && sed -i '' "/^| 24 | Brush /r $E/row25.txt" docs/runbooks/mac-recon.md; echo $? > "$E/row-insert.rc"` — 기대 `0`(같은 명령을 다시 돌리면 `[ … ]`가 1을 내고 `sed`는 돌지 않는다 — 멈춤). 확인: `cd "$W" && awk '/^\| 24 \| Brush /{getline a; print a}' docs/runbooks/mac-recon.md | diff - "$E/row25.txt" > "$E/row-diff.log"; echo "exit=$?" >> "$E/row-diff.log"` — 기대 `exit=0` 한 줄. 칸 자기 검사 1(규칙 17 b, 상시 규칙 "PR 본문 공통" 7): `cd "$W" && git diff -U0 origin/main -- docs/runbooks/mac-recon.md | grep '^+[^+]' > "$E/cell-lines-1.txt"; wc -l < "$E/cell-lines-1.txt" | tr -d ' ' > "$E/cell-lines-1-count.log"; grep -n -E '\.log|영록|R[0-9]{3}' "$E/cell-lines-1.txt" > "$E/cell-grep-1.log"; wc -l < "$E/cell-grep-1.log" | tr -d ' ' > "$E/cell-grep-1-count.log"` — 기대 `cell-lines-1-count.log` `1`, `cell-grep-1-count.log` `0`(0이 아니면 줄을 손으로 고치지 않고 멈춘다). 번호 바꾸기: `N=$(cat "$E/pr-number.log"); sed "s/ 근거: J-29 PR\. |\$/ 근거: PR #$N. |/" "$E/row25.txt" > "$E/row25-final.txt"; cd "$W" && [ "$(grep -c ' 근거: J-29 PR\. |$' docs/runbooks/mac-recon.md)" = 1 ] && sed -i '' "s/ 근거: J-29 PR\. |\$/ 근거: PR #$N. |/" docs/runbooks/mac-recon.md; echo $? > "$E/row-pr.rc"` — 기대 `0`. 확인: `cd "$W" && awk '/^\| 24 \| Brush /{getline a; print a}' docs/runbooks/mac-recon.md | diff - "$E/row25-final.txt" > "$E/row-final-diff.log"; echo "exit=$?" >> "$E/row-final-diff.log"` — 기대 `exit=0` 한 줄. `cd "$W" && grep -c ' 근거: J-29 PR\. |$' docs/runbooks/mac-recon.md > "$E/row-marker-left.log"` — 기대 `0`. `cmp -s "$E/row25.txt" "$E/row25-final.txt"; echo "same=$?" > "$E/row-changed.log"` — 기대 `same=1`(바뀌었다). `cd "$W" && git diff --numstat origin/main -- docs/runbooks/mac-recon.md | tr '\t' ' ' > "$E/row-numstat.log"` — 기대 `1 0 docs/runbooks/mac-recon.md`. 칸 자기 검사 2: `cd "$W" && git diff -U0 origin/main -- docs/runbooks/mac-recon.md | grep '^+[^+]' > "$E/cell-lines-2.txt"; wc -l < "$E/cell-lines-2.txt" | tr -d ' ' > "$E/cell-lines-2-count.log"; grep -n -E '\.log|영록|R[0-9]{3}' "$E/cell-lines-2.txt" > "$E/cell-grep-2.log"; wc -l < "$E/cell-grep-2.log" | tr -d ' ' > "$E/cell-grep-2-count.log"` — 기대 `cell-lines-2-count.log` `1`, `cell-grep-2-count.log` `0`. 상태: `git -C "$W" status --porcelain | grep -v -x -F ' M docs/runbooks/mac-recon.md' | diff "$E/status-before.log" - > "$E/status-row.diff"; echo "exit=$?" >> "$E/status-row.diff"` — 기대 `exit=0` 한 줄. 게이트 다시(규칙 13, 하네스 백그라운드): `cd "$W/tools" && source .venv/bin/activate && { /usr/bin/timeout 300 ruff check . && /usr/bin/timeout 300 ruff format --check . && /usr/bin/timeout 1800 pytest -q && /usr/bin/timeout 300 python scripts/check_repo.py; } > "$E/gate-2.log" 2>&1; echo $? > "$E/gate-2.rc"` — 기대 `gate-2.rc` `0`, `[ "$E/gate-2.log" -nt "$W/docs/runbooks/mac-recon.md" ]; echo "newer=$?" > "$E/mtime-2.log"` `newer=0`. 커밋: `cd "$W" && git add docs/runbooks/mac-recon.md && git diff --cached --name-only > "$E/c2-files.log" && [ "$(cat "$E/c2-files.log")" = "docs/runbooks/mac-recon.md" ] && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-29: mac-recon §6 #25 — 헤드리스 마커 확인(크래시 없음)" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c2-commit.log" 2>&1; echo $? > "$E/c2-commit.rc"; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-2.log"` — 기대 `c2-files.log` 한 줄 `docs/runbooks/mac-recon.md`, `c2-commit.rc` `0`, `author-2.log` `재환 <jaehwan.local@localhost>`. `/usr/bin/timeout 300 git -C "$W" push > "$E/push-2.log" 2>&1; echo "exit=$?" >> "$E/push-2.log"` — 기대 끝 줄 `exit=0`. 브랜치 파일: `git -C "$W" diff --name-only origin/main...HEAD > "$E/branch-files.log"` — 기대 두 줄 `docs/runbooks/mac-recon.md`·`unreal/Golmok/Config/DefaultEditorSettings.ini`(이 순서). push 뒤 상태: `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-final.diff"; echo "exit=$?" >> "$E/status-final.diff"` — 기대 `exit=0` 한 줄. CI 등록 대기(하네스 백그라운드, 커밋 2의 push 뒤): `H=$(git -C "$W" rev-parse HEAD); cd "$W" && /usr/bin/timeout 600 sh -c 'until [ "$(gh run list --commit "$1" --json event --jq "[.[]|select(.event==\"push\" or .event==\"pull_request\")]|length")" -ge 2 ]; do sleep 30; done' sh "$H" > "$E/run-wait.log" 2>&1; echo $? > "$E/run-wait.rc"` — 기대 `0`. CI(하네스 백그라운드, `run-wait.rc` `0` 뒤): `cd "$W" && /usr/bin/timeout 1800 gh pr checks "$(cat "$E/pr-number.log")" --watch --interval 30 > "$E/checks-watch.log" 2>&1; echo "exit=$?" >> "$E/checks-watch.log"; /usr/bin/timeout 120 gh pr checks "$(cat "$E/pr-number.log")" > "$E/checks.log" 2>&1` — 판정은 `checks.log` 표로만 한다(`checks-watch.log`의 `exit=`는 기록만): `{ awk -F'\t' '$2 != "pass"' "$E/checks.log" | wc -l | tr -d ' '; wc -l < "$E/checks.log" | tr -d ' '; } > "$E/checks-count.log"` — 기대 모든 행의 둘째 칸이 `pass`, 곧 첫 줄 `0`, 둘째 줄 1 이상. 그래도 `checks-watch.log`에 `no checks reported`가 있으면 첫 두 로그는 그대로 두고 다음 두 명령을 한 호출로 돌린다(하네스 백그라운드): `cd "$W" && /usr/bin/timeout 1800 gh pr checks "$(cat "$E/pr-number.log")" --watch --interval 30 > "$E/checks-watch-2.log" 2>&1; echo "exit=$?" >> "$E/checks-watch-2.log"; /usr/bin/timeout 120 gh pr checks "$(cat "$E/pr-number.log")" > "$E/checks-2.log" 2>&1` — 그 뒤 `{ awk -F'\t' '$2 != "pass"' "$E/checks-2.log" | wc -l | tr -d ' '; wc -l < "$E/checks-2.log" | tr -d ' '; } > "$E/checks-count-2.log"`(기대 첫 줄 `0`, 둘째 줄 1 이상). 이 경우 `## CI`·완료 기준 (g)·멈춤 조건의 `checks.log`는 `checks-2.log`로, `checks-count.log`는 `checks-count-2.log`로 읽는다(펜스 `j29-quotes-sh`는 바꾸지 않는다 — 첫 `checks.log`가 남아 있다).
  8. **PR 본문**: PR 본문·자리표시 분류·칸 자기 검사·근거 표기는 상시 규칙 "PR 본문 공통(모든 과제)"을 따른다(이 절과 다르면 그 소절을 따른다). `## 결과`에는 관찰한 값만 둔다: `engine.log` 여덟 줄, `check.log` 열아홉 줄, `t0-crc.log`(떠 있던 CrashReportClient pid — 이 과제의 것이 아님), `t0-marker-stat.log`·`t2-marker-stat.log`, `neg-cmdline.log`·`pos-cmdline.log`, `hook-committed.log`(커밋 1에 넣은 여덟 줄), 런북에 넣은 `row25-final.txt` 한 줄(로그 원문은 모두 백틱 펜스 블록에 그대로) — 그 펜스 밖에는 과제 번호·규칙 번호·날짜를 쓰지 않는다. `neg-editor.log`·`pos-editor.log`·`neg-run.log`·`pos-run.log`는 본문에 붙이지 않는다(엔진 경로가 길다). `## 실행한 명령` 끝의 줄 수 목록(상시 규칙 "PR 본문 공통" 2 크기)은 이 네 파일과 `## 결과`에서 일부만 인용한 로그만이다. `## 남은 [미확인]`에는 설계 5의 넷(사람이 보는 크래시, `bSendUsageData=False`의 효과, 패키지 게임, Windows)을 적는다. `## 병합 시 반영`에는 아래 "병합 시 반영(영록)"을 원문으로 옮기지 않고 "영록이 STATUS·DECISIONS·WP-21을 고친다" 한 문장만 쓴다. `## 완료 기준 대조`는 아래 (a)~(h) 한 줄씩(과제 글에 백틱 펜스가 들어 있어 물결 펜스 `~~~`를 쓴다). 본문 초안은 `$E/pr-body.md`. 사용자 경로 검사(공개 저장소에 사용자 이름이 든 절대 경로를 쓰지 않는다): `grep -c -F "$HOME" "$E/pr-body.md" > "$E/home-path.log"` — 기대 `0`(0이 아니면 그 줄을 `~` 기준으로 고쳐 다시 센다. 펜스 안 원문에서 걸리면 그 줄만 `~`로 바꾼 사본임을 펜스 위 한 문장에 적는다 — 엔진 경로 `/Users/Shared/…`는 사용자 이름이 아니라 걸리지 않는다). 게시 전 검사(규칙 10 e·f): `## 결과` 절의 펜스 밖 백틱 문자열마다 근거 로그 **한 개**를 `"$E/quotes.tsv"`에 `<문자열><탭><파일 이름>`으로 적는다 — 파일 이름은 펜스 `j29-quotes-sh` 안의 숫자 검사 목록에 든 것만 쓰고, 로그 인용이 아닌 파일 이름·명령은 파일 칸에 `라벨`. 그다음 `sh "$E/j29_quotes.sh" "$E"; echo $? > "$E/quotes.rc"` — 기대 `quotes.rc` `0`, `quotes-missing.log` 빈 파일, `cut -f1 "$E/quotes-check.log" | grep -c -x '0'` `0`, `cut -f1 "$E/numbers-check.log" | grep -c -x '0'` `0`(대상 로그는 펜스 안 목록으로 고정 — 본문 초안·게시본·`task.txt`·`commands.txt`·검사 로그 자신은 넣지 않는다). 한 자리 숫자는 숫자 검사에 걸리지 않으므로 문맥 문자열(예: `pos-marker-newer 1`)로 인용 검사에 넣는다. 0이 나온 것은 고치거나 지우고 같은 명령을 다시 돌린다. 그다음 상시 규칙 "PR 본문 공통" 3(점검표 대조)·5(자리표시 분류)·6(조립·게시·다시 읽기)을 적힌 그대로 돌린다.
- **허용 파일**: `unreal/Golmok/Config/DefaultEditorSettings.ini`(새 파일, 펜스 `j29-hook-ini` 여덟 줄 그대로 — 커밋 1 단독), `docs/runbooks/mac-recon.md`(§6 #24 바로 뒤에 펜스 `j29-row-sh`의 줄 하나만 — 할 일 7의 `sed`로 넣고 끝만 바꾼다, 커밋 2). 그 밖의 저장소 파일은 고치지 않는다: 다른 `Config/*.ini`·`Golmok.uproject`, mac-recon의 다른 행·§7, mac-setup, C++·Python·`tools/ue/*.sh`·테스트·공유 문서(STATUS·DECISIONS·WP-21 포함)·이 과제 파일. 저장소 밖에서도 아무것도 고치지 않는다: 사용자 `EditorSettings.ini`, 마커, 크래시 폴더, CrashReportClient 로그·프로세스, 엔진 파일. 생성물과 앞 과제의 `??` 항목은 커밋하지 않는다.
- **멈춤 조건(정하지 말고 영록에게 묻는다)**: `status-before-tracked.log`가 0이 아닐 때. `fetch.log`·`push-1.log`·`push-2.log`가 `exit=0`으로 끝나지 않을 때. `switch.rc`가 0이 아니거나 `sha-same.log`가 1이 아닐 때. `head -1 "$E/task.txt"`가 `#### J-29 `로 시작하지 않을 때. `extract-wc.log`가 기대와 다를 때. `overlap.rc`가 0이 아니거나 `overlap.log`가 비어 있지 않을 때. `pre.log`가 기대 다섯 줄과 다를 때(훅 파일이 이미 있다, 편집기 dylib이 없다, 마커가 없다, §6 꼴이 다르다, #25가 이미 있다 — 어느 것도 스스로 고치지 않는다). `engine.diff`가 `exit=0` 한 줄이 아닐 때. `t0-ue.rc`·`t1-ue.rc`·`t2-ue.rc` 중 하나가 1이 아닐 때(다른 UE 프로그램이 돈다 — 끄지 않는다). `t0-user-privacy.log`가 `0`이 아닐 때(사용자 층에 개인정보 설정이 있다 — 설계 6). 잠금 파일에 다른 기록이 있거나 `lock-take.rc`가 0이 아닐 때. `lock-refresh-neg.rc`·`lock-refresh-pos.rc` 중 하나가 0이 아닐 때(잠금 파일을 지우거나 쓰지 않는다). `neg-run.rc`·`pos-run.rc`가 0이 아닐 때(124 포함 — 다시 돌리지 않는다). `neg-marker-newer.log`가 `0`이 아닐 때(할 일 3으로 가지 않는다)·`pos-marker-newer.log`가 `1`이 아닐 때(설계 6 — `-ini:`·사용자 설정·Preferences를 건드리지 않고 다시 돌리지 않는다; 이때 `grep -n -i 'PrivacySettings' "$E/pos-editor.log"` 출력을 함께 보낸다). `neg-editor-new.log`·`pos-editor-new.log`가 `newer=0`이 아니거나 `neg-editor-cp.rc`·`pos-editor-cp.rc`·`hook-cp.rc`가 0이 아닐 때. `hook-diff.log`·`hook-committed.diff`·`status-hook.diff`·`status-run.diff`·`status-c1.diff`·`status-row.diff`·`status-final.diff`가 `exit=0` 한 줄이 아닐 때. `check.diff`가 `exit=0` 한 줄이 아닐 때 — 특히 `*-critical 1`·`crc-pids differ`·`crash-dirs differ`·`crc-log-mtime differ`(크래시나 CrashReportClient 실행이 있었다 — 무엇도 지우지 않고, 크래시 폴더 이름 목록(`t2-crash-dirs.log`)을 보낸다. `crc-pids differ`에서 `t0-crc.log`에 있던 pid가 `t2-crc.log`에서 빠지기만 했으면 앞서 떠 있던 프로세스가 끝난 것일 수 있다 — 그래도 멈추고 두 파일을 함께 보낸다). `row.rc`·`row-insert.rc`·`row-pr.rc`가 0이 아니거나 `row-diff.log`·`row-final-diff.log`가 기대와 다를 때. `row25-shape.log`·`row-marker-left.log`·`row-changed.log`·`row-numstat.log`·`checks-count.log`(다시 돌린 경우 `checks-count-2.log`)가 기대와 다를 때. `cell-lines-1-count.log`·`cell-lines-2-count.log`가 `1`이 아니거나 `cell-grep-1-count.log`·`cell-grep-2-count.log`가 `0`이 아닐 때(줄을 손으로 고치지 않는다). `gate-1.rc`·`gate-2.rc`가 0이 아닐 때(rc 124 포함, 다른 파일을 고치거나 `ruff format`으로 바꾸지 않는다). `mtime-1.log`·`mtime-2.log`가 `newer=0`이 아닐 때. `c1-files.log`·`c1-numstat.log`·`c2-files.log`·`c1-commit.rc`·`c2-commit.rc`·`author-1.log`·`author-2.log`가 기대와 다를 때(`[ … ]`가 막아 커밋이 안 됐으면 `c1-commit.rc`·`c2-commit.rc`가 `1`이다 — 그것도 멈춤). `lock-release.rc`가 0이 아닐 때(잠금 파일을 지우지 않는다). `branch-files.log`가 기대 두 줄이 아닐 때. `pr-create.rc`가 0이 아니거나 `pr-number.log`가 숫자 한 줄이 아닐 때. `run-wait.rc`가 0이 아닐 때(124 = 10분 안에 두 실행이 등록되지 않았다 — 다시 돌리지 않는다). `checks.log`에 `pass`가 아닌 행이 있을 때. `home-path.log`가 두 번 고친 뒤에도 0이 아닐 때. `quotes.rc`가 0이 아닐 때. 상시 규칙 "PR 본문 공통" 9의 공통 멈춤 조건. 넓은 명령에서 macOS 권한 창이 뜰 때(누르지 않는다 — 소유자 항목). 그 밖에 이 절의 "기대"와 다른 값이 하나라도 나올 때. **멈춤 순서 — 할 일 2~4 안에서 멈출 때는 이 순서로 한다**: ① `sh "$E/j29_procs.sh" "$E" stop`. ② `stop-ue.rc`가 `1`이면 잠금 풀기를 돌려 `lock-release.rc`를 남기고 묻는다. `0`이면(편집기·다른 UE 프로그램이 남았다) 프로세스를 건드리지 않고 잠금도 풀지 않은 채 `stop-ue.log`를 영록에게 보낸다. 훅 파일을 이미 넣었으면 지우지 않고 그대로 둔다(커밋하지 않는다).
- **완료 기준**:
  - (a) 준비: `status-before-tracked.log` `0`, `fetch.log` 끝 줄 `exit=0`, `switch.rc` `0`, `sha-same.log` `1`, `task.txt` 첫 줄 `#### J-29 `, `extract-wc.log` 원문(기대 숫자와 같다), `overlap.rc` `0`·`overlap.log` 빈 파일, `pre.log` 다섯 줄 `hook-file=1`·`editor-dylib=0`·`marker=0`·`1`·`0`, `engine.diff` `exit=0`, `t0-ue.rc` `1`, `t0-user-privacy.log` `0`.
  - (b) 음성 대조: `lock-take.rc` `0`, `neg-hook.log` `hook-file=1`, `lock-refresh-neg.rc` `0`, `neg-run.rc` `0`, `neg-marker-newer.log` `0`, `neg-editor-new.log` `newer=0`, `neg-editor-cp.rc` `0`, `t1-ue.rc` `1`.
  - (c) 훅 파일과 양성 실행: `hook-cp.rc` `0`, `hook-diff.log` `exit=0`, `pos-hook.log` `hook-file=0`, `status-hook.diff` `exit=0`, `lock-refresh-pos.rc` `0`, `pos-run.rc` `0`, `pos-marker-newer.log` `1`, `pos-editor-new.log` `newer=0`, `pos-editor-cp.rc` `0`, `t2-ue.rc` `1`, `lock-release.rc` `0`.
  - (d) 판정: `check.diff` `exit=0`(`check.log` 열아홉 줄 원문 — `neg-marker-newer 0`·`pos-marker-newer 1`·`crc-pids same`·`crash-dirs same`·`crc-log-mtime same`·`user-privacy 0 0 0` 포함), `status-run.diff` `exit=0`. 결과는 "이번 실행에서 편집기 무인 실행이 `False`를 읽었다"로만 적는다(설계 5 — "업로드가 꺼졌다"로 넓히지 않는다).
  - (e) 커밋 1·PR: `gate-1.rc` `0`, `mtime-1.log` `newer=0`, `c1-files.log`·`c1-numstat.log`·`c1-commit.rc`·`author-1.log` 기대대로, `hook-committed.diff` `exit=0`, `status-c1.diff` `exit=0`, `push-1.log` 끝 줄 `exit=0`, `pr-create.rc` `0`, `pr-number.log` 숫자 한 줄.
  - (f) 런북 줄·커밋 2: `row.rc` `0`, `row25-shape.log` `1`·`7`, `row-insert.rc` `0`, `row-diff.log` `exit=0`, `cell-lines-1-count.log` `1`, `cell-grep-1-count.log` `0`, `row-pr.rc` `0`, `row-final-diff.log` `exit=0`, `row-marker-left.log` `0`, `row-changed.log` `same=1`, `row-numstat.log` `1 0 docs/runbooks/mac-recon.md`, `cell-lines-2-count.log` `1`, `cell-grep-2-count.log` `0`, `status-row.diff` `exit=0`, `gate-2.rc` `0`, `mtime-2.log` `newer=0`, `c2-files.log`·`c2-commit.rc`·`author-2.log` 기대대로, `push-2.log` 끝 줄 `exit=0`, `branch-files.log` 두 줄, `status-final.diff` `exit=0`.
  - (g) CI: `run-wait.rc` `0`, `checks-count.log` 첫 줄 `0`, `checks.log` 모든 행 `pass` 원문(규칙 2; 할 일 7의 다시 돌린 경우는 `checks-count-2.log`·`checks-2.log`).
  - (h) PR 본문: 절 순서(상시 규칙 "PR 본문 공통" 2), "완료 기준 대조" 절, 점검표(그날 규칙 수만큼, 소절 3). `home-path.log` `0`, `quotes.rc` `0`, `quotes-missing.log` 빈 파일, `quotes-check.log`·`numbers-check.log`에 0 없음. 공통 완료 기준 (P)(소절 10): `checklist.diff` `exit=0`, `ph-unfilled.log` `0`, `pr-edit.rc` `0`, `ph-posted-unfilled.log` `0`, `ph-table.diff` `exit=0`, `signature-last.log` `1`, `cell-grep-1-count.log`·`cell-grep-2-count.log` `0`.
- **병합 시 반영(영록)**: STATUS 재환 절에 J-29 행. STATUS WP-21 행(:43)의 후속 목록에서 "CrashReportClient 업로드 끄기(D-007)"에 날짜를 단 닫음 메모(편집기 무인 실행 — 사람이 보는 크래시·패키지·Windows는 [미확인]). WP-21 남은 작업 5(:143)와 DECISIONS D-023 "D-007" 줄(:353) 뒤에 날짜를 단 한 줄("2026-11-28 J-29 PR #N: 프로젝트 `DefaultEditorSettings.ini` `[WP-21 hook]`으로 끔 — D-025")을 더한다(규칙 16 — 있는 글은 지우지 않는다). DECISIONS에 **D-025**(오케스트레이터 결정, D-019, 되돌릴 수 있음): "편집기의 무인 크래시 리포트(`bSendUnattendedBugReports`)와 편집기 사용 통계(`bSendUsageData`)를 프로젝트 층에서 `False`로 둔다. 근거 D-007·D-019(외부 발송), 엔진 소스 줄(이 절 출처), J-29 마커 확인. 되돌리기: 파일 삭제. 사람이 보는 크래시의 대화창 선택은 사용자에게 남는다." 소유자에게 사실로 알린다(승인 항목이 아니다): 2026-11-28 14:37 KST J-27 실행 크래시의 리포트 7개 파일이 Epic datarouter로 올라갔고(로그 :70·:82), 2026-11-27 리포트 5건의 로그에도 `All uploads done`이 있다. 떠 있는 CrashReportClient 두 개(pid 16929·69882, CPU 약 100 %)를 끌지는 영록이 정한다(로컬 프로세스 — 되돌릴 수 있다; 이 과제는 건드리지 않는다).
- **왜 재환 / 위험**: 파일 내용·실행 명령·판정·기록 줄이 모두 펜스로 정해져 있고, 판정은 종료 코드·`diff`·고정 개수로 끝난다. 크래시를 일으키지 않고 Astra 레인도 건드리지 않는다. 키 선택은 Opus가 엔진 소스로 했다(설계 1). 위험: ① **층이 먹지 않음**(사용자 층·Preferences가 덮음) — 음성 `0`·양성 `1` 짝이 이를 가르고, 양성 `0`이면 멈춘다(설계 6). `t*-user-privacy.log` `0`이 사용자 층이 비어 있음을 매 시점 확인한다. ② **다른 쓰는 쪽**(UnrealPak·ShaderCompileWorker·패키지 게임·다른 세션의 편집기) — `pgrep` 세 시점과 GUI 잠금으로 막고, 음성 창의 잡음은 음성 `0`이 배제한다. 양성 창 안에서 시작하고 끝난 다른 프로그램은 배제하지 못한다(남은 위험 — 잠금이 그 신호다). ③ **넓게 쓰기**(규칙 1·3·15) — 줄 문구가 "이번 실행에서 편집기 무인 실행이 읽었다"로 고정, 나머지는 `[미확인]`. ④ **음성 대조 실행 자체의 업로드 위험** — 끄기 전 설정의 무인 실행 1회(설계 2). 그래서 J-29를 다음 UE 과제보다 먼저 한다. ⑤ **핫스팟 커밋 위생** — 새 파일 하나, 표식 그대로, `[ … ] &&`로 `diff --cached`와 허용 파일을 대조한 뒤에만 커밋. ⑥ **증거 덮어쓰기** — 실행마다 기준 파일·로그 이름이 `neg`/`pos`로 나뉘고, 다시 돌리지 않는다. 수치(시간·fps)는 재지 않는다.
- **dry-run 범위(Opus 2026-11-28)**: `origin/main` `acbd954`의 scratch 사본(`git archive`, git 저장소로 만든 것)에서 한 것: 이 절을 넣은 과제 파일에서 할 일 1의 과제 추출(첫 줄 `#### J-29 `, `### PR 본문 공통(모든 과제)` 1)과 백틱 없는 펜스 추출(zsh·sh, `wc -l` 8·12·8·14·19·19·19·6·17·37, `159 total`), 추출한 파일이 이 절의 펜스와 바이트가 같음. `j29-engine-sh`를 이 Mac의 실제 엔진에 돌림(sh·zsh 같음) — 펜스 `j29-expected-engine`과 같음. 훅 파일을 scratch `Config/`에 넣고 `check_repo.py` `OK (uproject, ini, json, links, gitattributes, conflicts, gasp)`(그 파일 맨 앞에 섹션 없는 `Key=Value`를 넣으면 실패 — 게이트가 새 파일을 읽는다), `parse_ue_ini`가 두 섹션·두 키 `False`를 읽음, `ruff check` 통과, `ruff format --check` 통과, `pytest -q` `1940 passed, 3 skipped`, staged numstat `8 0`. `j29-run-sh`·`j29-procs-sh`·`j29-check-sh`는 가짜 `$HOME`(마커·크래시 폴더·사용자 `EditorSettings.ini`·CrashReportClient 로그)과 가짜 `UnrealEditor-Cmd`(인자를 `LogInit: Command Line:` 줄로 쓰고, 프로젝트 훅 파일이 `False`일 때만 엔진처럼 `O_WRONLY` + `ftruncate(0)`으로 마커를 쓰는 셸 스크립트 — 실행 경로만 바꾼 `j29_run.sh` 사본)로 sh·zsh에서 돌려 펜스 `j29-expected-check`와 같은 열아홉 줄을 얻었다. 빈 검사가 아님(각각 기대와 다른 줄 수): 가짜 엔진이 훅을 무시 → `pos-marker-newer 0`(1줄), 음성 창 안에 다른 쓰는 쪽 → `neg-marker-newer 1`(1줄), 크래시 줄 → `*-critical 1`(2줄), 사용자 층에 개인정보 섹션 → `user-privacy 1 1 1`(1줄), `…/Binaries/Mac/UnrealEditor-Cmd` 경로의 가짜 프로세스 → `ue-procs 0 0 0`(1줄, sh·zsh), 양성 실행 전 새 크래시 폴더 → `crash-dirs differ`(1줄), CrashReportClient 로그 시각 바뀜 → `crc-log-mtime differ`(1줄), pid 목록 한 줄 더함 → `crc-pids differ`(1줄), 편집기 로그·폴더 목록 빈 파일 → 5줄. 이 Mac의 `pgrep -x CrashReportClient`는 이름이 16자를 넘어도 떠 있는 두 pid를 냈다. `j29-row-sh`(견본 날짜 `2026-11-28`·SHA `acbd954`): rc 0, 한 줄, 칸 다섯(`NF` 7), 1168바이트(문서 9 검증 지적의 `작업 트리` 뒤 — 앞은 1154바이트), 규칙 17 b의 `grep -n -E` 0건. 할 일 7의 `sed -i '' "/^| 24 | Brush /r …"`(macOS `/usr/bin/sed`): rc 0, #24 바로 뒤, `awk getline` 확인 `diff` 0, numstat `1 0`, 더한 줄 1. 번호 바꾸기(가짜 번호 999): `row-final-diff` `exit=0`, `근거: J-29 PR.` 0줄, `근거: PR #999.` 1줄, 바뀐 줄 자기 검사 0건. `j29-quotes-sh`는 견본 본문(펜스 안팎 백틱 문자열·숫자)으로 sh·zsh에서 `quotes-missing.log` 빈 파일·0 없는 표를 냈고, 본문에만 있는 문자열을 넣으면 `quotes-missing.log`가 그 한 줄을 냈다. 엔진 `ftruncate`가 이미 0바이트인 파일의 수정 시각을 바꾸는 것은 이 Mac의 `/private/tmp`(APFS)에서 `os.ftruncate`로 확인했다(`open`만으로는 그대로). dry-run하지 못한 것(이 과제가 재는 것): 실제 편집기 실행(종료 코드, `LogInit: Command Line:` 줄의 실제 꼴, `LogExit: Exiting.` 개수, 마커가 정말 바뀌는지 — 엔진 소스와 UnrealPak 시각으로 예상한 것), 실제 `$HOME`·`$W`에서의 `diff`, 잠금 갱신 루프, `gh pr create`·`gh pr edit`·`gh pr checks`, 실제 본문의 인용·숫자·사용자 경로 검사. shellcheck는 이 Mac에 없어 돌리지 않았다(펜스 스크립트는 `$E`에 두어 CI의 `tools/ue/*.sh`·`tools/mac/*.sh` 범위 밖이다; `sh -n`·`bash -n`·`zsh -n`은 모두 통과). 문서 9 검증 지적 반영 뒤(같은 날, Opus): 할 일 1의 과제·펜스 추출을 고친 파일에서 다시 돌려 sh·zsh 모두 `159 total`(앞 숫자 그대로). `j29_run.sh`는 `$W`가 없는 가짜 `HOME`에서 rc 3과 `xs-run.rc` `3`을 남겼다(sh·zsh — 기다릴 파일이 생긴다). 할 일 7의 `row25-shape.log` 명령은 견본 줄에서 `1`·`7`, `checks-count.log` 명령은 pass 2행 표에서 `0`·`2`, fail 한 행을 더하면 `1`·`3`. `j29-row-sh` sh·zsh 같은 출력.

#### J-30a (J-30을 좁힌 것) COLMAP 희소 모델 → EXIF GPS ENU 정합(`model_aligner`) → 정합 좌표의 Brush splat, 수치 확인만 — 설계 확정(Opus 2026-11-28)
- **출처**: [WP-21](WP-21-mac-recon-pipeline.md) "남은 작업" 4("COLMAP 희소 모델 미터·ENU 정합 → 메시·splat 좌표 공유를 끝까지 해 본다"), D-023 "좌표" 줄(Brush는 COLMAP world를 그대로 쓴다, 미터·ENU 정합은 그 모델에서 먼저 한 번 [미확인, 끝까지 해 보지 않음]), [mac-recon.md](../runbooks/mac-recon.md) M3 "정합(미터·ENU)" 문단(:93-95)과 §6 미확인 #5(:230, 확인 결과 칸 빈 칸), 공개 데이터 출처·저작자 표시 mac-recon :180(Tyrol 교회 드론 76장 5472×3648, CC BY 4.0, [Tyrol-Church](https://github.com/IRCSS/Tyrol-Church-Photogrammetry-Dataset)). 입력은 저장소 밖 `~/golmok_data/recon-smoke/objcap/tyrol/images`(JPG 76장, EXIF GPS 있음 — `exiftool`로 `DJI_0352.JPG 46.9482009166667 12.062021 1645`). 도구: `~/golmok-tools`의 COLMAP 4.2.1 `cpu_lgpl`, Brush v0.3.0, exiftool 13.64(mac-recon §1). COLMAP 4.2.1 `model_aligner` 소스 [model.cc](https://github.com/colmap/colmap/blob/4.2.1/src/colmap/exe/model.cc)(`RunModelAligner`: `--alignment_max_error`가 0 이하면 "You must provide a maximum alignment error > 0"로 실패, `--alignment_type enu`이면 참조 위치의 **첫 줄**을 ENU 원점으로 쓴다 — `ConvertCameraLocations`; `--ref_images_path` 한 줄 = `이름 x y z`, `--ref_is_gps 1`이면 위도·경도·고도), [sim3.cc](https://github.com/colmap/colmap/blob/4.2.1/src/colmap/geometry/sim3.cc) `Sim3d::ToFile`(`scale qw qx qy qz tx ty tz` 한 줄), 공식 FAQ [Geo-registration](https://colmap.github.io/faq.html#geo-registration). 저장소 도구: `tools/golmok_tools/exif.py` `read_exif`(exifread, `lat`·`lon`·`alt`, `GPSAltitudeRef` 1이면 음수), `tools/golmok_tools/splat/ply.py` `read_ply`·`positions`, `golmok-splat inspect --json`.
- **이력(2026-11-28 문서 7)**: 문서 6의 보류 메모(할 일 9의 자리표시 검사는 분류 표의 줄이 다시 검색에 걸려 글자 그대로 충족될 수 없다 — 재검증 지적)는 할 일 9를 `## ` 절 제목·펜스 기준의 기계적 분류와 개수 표로 고쳐 해소했다(완료 기준 (i)·멈춤 조건도 같이). 문서 7의 다시 고친 판에서는 그 분류가 상시 규칙 "PR 본문 공통(모든 과제)"의 공통 단계로 옮겨졌다. 이제 배정할 수 있다.
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
  10. **기록(규칙 16, 덧붙이기만)**: 런북 두 군데만 — ① mac-recon M3 "정합" 문단의 마지막 줄(`- 보조 확인은`으로 시작하는 `golmok-align run` 줄, 지금 :95) **바로 뒤에** 날짜 메모 한 줄을 더한다. ② §6 #5 행의 빈 "확인 결과" 칸을 채운다(다른 칸·다른 행은 그대로). 두 줄의 글자는 펜스 `j30a-render`가 로그에서 만들고(숫자를 손으로 옮기지 않는다), 펜스 `j30a-apply`가 넣는다(앵커가 정확히 1번씩일 때만, 아니면 rc 1로 아무것도 쓰지 않는다). 두 줄 끝은 `근거: J-30a PR.` 표식이고, PR 번호가 나온 뒤 커밋 2가 그 표식을 `근거: PR #번호.`로 바꾼다(할 일 8, 상시 규칙 "PR 본문 공통" 8 — 2026-11-28 문서 7: 처음 판의 칸 끝 "로그 `$TMPDIR/jaehwan/J-30a/`"는 규칙 17 b에 맞지 않아 뺐다). 기존 문장 "[미확인: 끝까지 해 보지 않음]"은 지우지 않는다(그 뒤의 날짜 메모가 갱신이다). WP-21 결과 줄·STATUS는 영록이 병합 때 고친다("병합 시 반영").
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
    "Object Capture 메시의 같은 좌표 변환(J-30b)은 하지 않았다. 근거: J-30a PR."
)
row = (
    "| 5 | `colmap model_aligner` 미터·ENU 정합(옵션·결과) | 끝까지 해 보지 않음 | GPS 있는 리허설 → zone-local 범위 확인 | "
    f"{day}(J-30a, 공개 Tyrol 76장, 품질 판정 아님): `--ref_images_path`·`--ref_is_gps 1`·`--alignment_type enu`·"
    f"`--alignment_max_error 3`으로 정합, 등록 {al['registered'][0]}/76, 카메라 중심 잔차 {res}, "
    f"splat → SfM 중앙값 {sp['splat_to_sfm_m'][1]} m. `{colmap_line}`. 리허설 사진·zone-local 범위는 남음. "
    'M3 "정합" 메모. 근거: J-30a PR. |'
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

- **명령 공통**: 셸 변수는 Bash 호출 사이에 남지 않는다. 그래서 **모든 명령은 `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/jaehwan/J-30a"; I="$HOME/golmok_data/recon-smoke/objcap/tyrol/images"; PY="$W/tools/.venv/bin/python"; . "$HOME/golmok-tools/env.sh";`로 시작하고**(마지막 것은 `colmap`·`brush_app`·`exiftool`을 PATH에 넣는다), 그 뒤는 `cd "$E" &&`·`cd "$E/brush" &&`·`cd "$W" &&`·`cd "$W/tools" &&`·`git -C "$W"`·`"$E/…"` 절대 경로로 시작한다(상시 규칙, 설계 2). 아래 명령에는 이 앞머리를 적지 않았다. 돌린 명령 원문은 `"$E/commands.txt"`에 한 줄씩 더한다(규칙 10). 기다릴 수 있는 긴 명령(COLMAP `feature_extractor`·`exhaustive_matcher`·`mapper`·`model_aligner`·`image_undistorter`, Brush, `check_splat.py` 두 번, 게이트, `gh pr checks --watch`)은 `/usr/bin/timeout`(규칙 5)이고 시간은 아래에 고정했다. `git fetch`·`git push`·`gh pr list`·`gh pr create`·`gh pr view`·`gh pr edit`·`model_analyzer`·`model_converter`·`golmok-splat inspect`는 아래에 적힌 그대로 쓴다(`timeout`을 더하거나 빼지 않는다 — 2026-11-28 문서 9: 점검표 규칙 5 줄은 상시 규칙 "PR 본문 공통" 3의 감사 `timeout-audit.log`에서 두 무리의 수를 옮긴다. CI 표 명령 `gh pr checks`에는 문서 9에서 `/usr/bin/timeout 120`을 붙였다). 위 긴 명령들은 **항상** 하네스의 백그라운드 실행으로 돌리고, 그 명령이 쓰는 `.rc` 파일(`gh pr checks --watch`는 `checks-watch.log`의 `exit=` 줄)이 생길 때까지 기다린다(명령은 바꾸지 않는다). 그 밖의 명령은 앞쪽(foreground)으로 돌린다. 각 단계의 "기대"와 다르면 **멈춤 조건**을 본다.
  - **펜스 추출**(2026-11-28 문서 9에서 고침): 할 일 1의 한 명령이 펜스 9개를 이름으로 뽑는다. 백틱 세 개는 `sprintf`로 만들어 명령 글자에 백틱이 없다(옛 `X` 꼴은 백틱 세 개가 든 `sed` 명령이라 펜스 밖 글에서 깨졌다 — J-19의 교훈, 뽑는 결과는 같다). 손으로 옮기지 않는다.
  - **GUI·GPU 잠금 확인**(잡지 않는다 — UE를 띄우지 않는다): `L="$TMPDIR/claude/gui-foreground.lock"; if [ -e "$L" ]; then cat "$L"; else echo "no lock"; fi > "$E/lock-check-<n>.log"; date -u +%FT%TZ >> "$E/lock-check-<n>.log"` — 기대 첫 줄 `no lock`. 다른 줄이 있으면(영록이 성능을 재는 중일 수 있다) **지우지 않고** 그 줄을 영록에게 보내고 기다린다. `<n>`은 할 일 1이면 `a`, 할 일 5(Brush 앞)이면 `b`.
  - **부하 기록**(규칙 15, 판정 아님): `{ date -u +%FT%TZ; uptime; /usr/bin/timeout 20 "$HOME/.lmstudio/bin/lms" ps; } > "$E/load-<n>.log" 2>&1` — `<n>`은 `before`(할 일 1)·`after`(할 일 5 끝). LM Studio 모델이 로드돼 있었는지를 PR에 적는다. 이 과제의 시간·메모리 수치는 판정 근거가 아니다(재환 추론이 같은 GPU·통합 메모리를 쓴다).
- **할 일**:
  1. **준비**: `mkdir -p "$E" && git -C "$W" fetch origin && git -C "$W" switch -c local/jaehwan-j30a-colmap-enu origin/main && git -C "$W" show origin/main:docs/plan/jaehwan-tasks.md > "$E/tasks-main.md"; git -C "$W" rev-parse origin/main > "$E/main-rev.log"; { awk '/^#### J-30a /{f=1} /^#### J-31a/{f=0} f' "$E/tasks-main.md"; awk '/^### PR 본문 공통\(모든 과제\)$/{f=1} /^## 리뷰·병합 절차$/{f=0} f' "$E/tasks-main.md"; } > "$E/task.txt"`(규칙 14·17 c, 상시 규칙 "PR 본문 공통" 1). 기대: `head -1 "$E/task.txt"`가 `#### J-30a `로 시작하고, `grep -c '^- \*\*dry-run 범위(Opus 2026-11-28, J-30a)\*\*' "$E/task.txt"`가 `1`, `grep -c -x '### PR 본문 공통(모든 과제)' "$E/task.txt"`가 `1`이다. 펜스 추출 9개(한 명령): `printf '%s\n' "j30a-make-ref make_ref.py" "j30a-check-align check_align.py" "j30a-check-splat check_splat.py" "j30a-verdict verdict.py" "j30a-render render.py" "j30a-apply apply.py" "j30a-ref-expected expected-ref.txt" "j30a-fence-lines expected-fence-lines.txt" "common-ph-awk ph.awk" | while read -r n f; do awk -v n="$n" 'BEGIN {b = sprintf("%c%c%c", 96, 96, 96)} x && $0 == b {x = 0} x {print} !x && index($0, b) == 1 && $0 ~ (" " n "$") {x = 1}' "$E/task.txt" > "$E/$f"; done`(zsh는 따옴표 없는 변수를 낱말로 나누지 않으므로 `read -r n f`로 나눈다) — 기대 `wc -l < "$E/ph.awk" | tr -d ' '` `37`(상시 규칙 소절의 펜스). 확인: `cd "$E" && wc -l make_ref.py check_align.py check_splat.py verdict.py render.py apply.py | sed '$d' | awk '{print $1, $2}' | diff "$E/expected-fence-lines.txt" - > "$E/fence-lines.diff"; echo "exit=$?" >> "$E/fence-lines.diff"` — 기대 `exit=0` 한 줄. 도구: `colmap version 2>&1 | head -1 > "$E/versions.log"; brush_app --version >> "$E/versions.log" 2>&1; exiftool -ver >> "$E/versions.log"` — 기대 세 줄 `COLMAP 4.2.1 (Commit Unknown on Unknown without GPU support, std hash maps)`, `brush-cli 0.3.0`, `13.64`. 옵션: `cd "$E" && colmap model_aligner -h > "$E/aligner-help.log" 2>&1; grep -c -E '^  --(ref_images_path|ref_is_gps|alignment_type|alignment_max_error|transform_path) arg' "$E/aligner-help.log"` — 기대 `5`; `grep -c -F -- '--robust_alignment' "$E/aligner-help.log"` — 기대 `0`. 입력: `ls "$I" | wc -l | tr -d ' '` `76`, `ls "$I" | grep -v -c '\.JPG$'` `0`, `cd "$I" && shasum -a 256 *.JPG | shasum -a 256 | cut -c1-64 > "$E/input-hash-before.log"` — 기대 `c28c1998b732270ccb1bc6e93267779fbb8f30bdd449c6059ef241317c8aebb3`(이미지 폴더에서 `cd`는 읽기만 하는 `shasum`에만 쓴다). 겹침: `cd "$W" && gh pr list --state open --json number,headRefName,files --jq '.[]|select(any(.files[]; .path=="docs/runbooks/mac-recon.md"))|"\(.number) \(.headRefName)"' > "$E/overlap.log" 2>&1` — 기대 빈 파일. `git -C "$W" status --porcelain > "$E/status-before.log"`(내용은 기록만 — 다른 과제가 남긴 추적 안 된 파일이 있을 수 있다). 잠금 확인(`a`), 부하 기록(`before`).
  2. **참조 파일**: `cd "$E" && "$PY" "$E/make_ref.py" "$I" "$E/ref_gps.txt" > "$E/ref.log" 2>&1; echo $? > "$E/ref.rc"` — 기대 rc `0`, `diff "$E/expected-ref.txt" "$E/ref.log"` 출력 없음(종료 0), `shasum -a 256 "$E/ref_gps.txt" | cut -c1-64` `989373f7b3c7e2d6befb8b5582a3262c433f69dee2512bf3799dd82d00a9ddf6`, `wc -l < "$E/ref_gps.txt" | tr -d ' '` `76`. exiftool 대조: `exiftool -n -p '$FileName $GPSLatitude $GPSLongitude $GPSAltitude' "$I/DJI_0352.JPG" > "$E/exiftool-first.log" 2>&1` — 기대 한 줄 `DJI_0352.JPG 46.9482009166667 12.062021 1645`.
  3. **SfM**: 특징 `cd "$E" && /usr/bin/timeout 1800 /usr/bin/time -l colmap feature_extractor --database_path "$E/database.db" --image_path "$I" --ImageReader.camera_model OPENCV --ImageReader.single_camera 1 --FeatureExtraction.use_gpu 0 --FeatureExtraction.max_image_size 3200 > "$E/fe.log" 2>&1; echo $? > "$E/fe.rc"` — 기대 rc `0`, `grep -c 'Processed file \[' "$E/fe.log"` `76`, `grep -c 'GPS:' "$E/fe.log"` `76`(dry-run 324 s, peak footprint 약 36 GB — 기록만). 매칭 `cd "$E" && /usr/bin/timeout 900 /usr/bin/time -l colmap exhaustive_matcher --database_path "$E/database.db" --FeatureMatching.use_gpu 0 > "$E/match.log" 2>&1; echo $? > "$E/match.rc"` — 기대 rc `0`. 매핑 `mkdir -p "$E/sparse" && cd "$E" && /usr/bin/timeout 1800 /usr/bin/time -l colmap mapper --database_path "$E/database.db" --image_path "$I" --output_path "$E/sparse" > "$E/mapper.log" 2>&1; echo $? > "$E/mapper.rc"` — 기대 rc `0`, `ls "$E/sparse"` 한 줄 `0`. 분석 `cd "$E" && colmap model_analyzer --path "$E/sparse/0" > "$E/analyzer.log" 2>&1; echo $? > "$E/analyzer.rc"` — 기대 rc `0`, `grep -c 'Registered images: 76$' "$E/analyzer.log"` `1`.
  4. **정합**: `mkdir -p "$E/aligned" && cd "$E" && /usr/bin/timeout 300 colmap model_aligner --input_path "$E/sparse/0" --output_path "$E/aligned" --ref_images_path "$E/ref_gps.txt" --ref_is_gps 1 --alignment_type enu --alignment_max_error 3 --transform_path "$E/aligned/sim3.txt" > "$E/aligner.log" 2>&1; echo $? > "$E/aligner.rc"` — 기대 rc `0`, 아래 네 개가 각각 `1`: `grep -c -F 'Using the first GPS coordinate as the ENU origin' "$E/aligner.log"`, `grep -c -F '=> Using 76 reference images' "$E/aligner.log"`, `grep -c -F '=> Alignment error:' "$E/aligner.log"`, `grep -c -F '=> Alignment succeeded' "$E/aligner.log"`. `awk '{print NF}' "$E/aligned/sim3.txt"` `8`. TXT로: `mkdir -p "$E/aligned_txt" "$E/sparse_txt" && cd "$E" && colmap model_converter --input_path "$E/aligned" --output_path "$E/aligned_txt" --output_type TXT > "$E/conv-aligned.log" 2>&1; echo $? > "$E/conv-aligned.rc"`, 같은 꼴로 `--input_path "$E/sparse/0" --output_path "$E/sparse_txt"` → `conv-sparse.log`·`conv-sparse.rc` — 기대 둘 다 rc `0`. 확인: `cd "$E" && "$PY" "$E/check_align.py" "$E/ref_gps.txt" "$E/aligned_txt" "$E/aligned/sim3.txt" > "$E/align-check.log" 2>&1; echo $? > "$E/align-check.rc"` — 기대 rc `0`, 11줄(`wc -l`), 첫 세 줄 `ref_images 76`·`registered 76`·`common 76`, 넷째 줄 `origin DJI_0352.JPG 46.948200917 12.062021000 1645.000`. 숫자 판정은 할 일 6이 한다.
  5. **splat(정합 좌표)**: `cd "$E" && /usr/bin/timeout 900 colmap image_undistorter --image_path "$I" --input_path "$E/aligned" --output_path "$E/undistorted" --output_type COLMAP > "$E/undist.log" 2>&1; echo $? > "$E/undist.rc"` — 기대 rc `0`, `ls "$E/undistorted/images" | wc -l | tr -d ' '` `76`. `cd "$E" && colmap model_converter --input_path "$E/undistorted/sparse" --output_path "$E/undistorted/sparse" --output_type TXT > "$E/conv-undist.log" 2>&1; echo $? > "$E/conv-undist.rc"` — 기대 rc `0`, `grep -c ' PINHOLE ' "$E/undistorted/sparse/cameras.txt"` `1`. 잠금 확인(`b`). Brush: `mkdir -p "$E/brush" && cd "$E/brush" && RUST_LOG=info /usr/bin/timeout 1800 /usr/bin/time -l brush_app "$E/undistorted" --total-steps 3000 --max-resolution 1600 --seed 42 --export-every 3000 --export-path "$E/brush" --export-name "export_{iter}.ply" > "$E/brush.log" 2>&1; echo $? > "$E/brush.rc"` — 기대 rc `0`, `grep -c 'backend: Metal' "$E/brush.log"`이 1 이상, `ls "$E/brush/export_3000.ply"` 있음(`target/`은 `$E/brush` 안에 생긴다 — 그대로 둔다). `cd "$E" && "$W/tools/.venv/bin/golmok-splat" inspect --json "$E/brush/export_3000.ply" > "$E/inspect.json" 2> "$E/inspect.err"; echo $? > "$E/inspect.rc"` — 기대 rc `0`. 거리: `cd "$E" && /usr/bin/timeout 600 "$PY" "$E/check_splat.py" "$E/brush/export_3000.ply" "$E/aligned_txt/points3D.txt" > "$E/splat-check.log" 2>&1; echo $? > "$E/splat-check.rc"`, 대조군 `cd "$E" && /usr/bin/timeout 600 "$PY" "$E/check_splat.py" "$E/brush/export_3000.ply" "$E/sparse_txt/points3D.txt" > "$E/splat-control.log" 2>&1; echo $? > "$E/splat-control.rc"` — 기대 둘 다 rc `0`, 각 6줄. 저장소가 그대로인지: `git -C "$W" status --porcelain > "$E/status-after-run.log"; diff "$E/status-before.log" "$E/status-after-run.log" > "$E/status-run.diff"; echo "exit=$?" >> "$E/status-run.diff"` — 기대 `exit=0` 한 줄. 입력이 그대로인지: `cd "$I" && shasum -a 256 *.JPG | shasum -a 256 | cut -c1-64 > "$E/input-hash-after.log"; diff "$E/input-hash-before.log" "$E/input-hash-after.log"` — 출력 없음. 부하 기록(`after`).
  6. **판정**: `cd "$E" && "$PY" "$E/verdict.py" "$E" > "$E/verdict.log" 2>&1; echo $? > "$E/verdict.rc"` — 기대 rc `0`, `grep -c '^PASS ' "$E/verdict.log"` `13`, `grep -c '^FAIL ' "$E/verdict.log"` `0`, 끝 줄 `verdict PASS 13/13`. 비공허(판정이 틀린 좌표를 떨어뜨리는지): `mkdir -p "$E/neg" && cp "$E/ref.log" "$E/aligner.log" "$E/inspect.json" "$E/neg/" && printf '1 0 0 0 0 0 0 0\n' > "$E/neg/identity.txt" && cd "$E" && "$PY" "$E/check_align.py" "$E/ref_gps.txt" "$E/sparse_txt" "$E/neg/identity.txt" > "$E/neg/align-check.log" 2>&1 && cp "$E/splat-control.log" "$E/neg/splat-check.log" && cp "$E/splat-control.log" "$E/neg/splat-control.log" && "$PY" "$E/verdict.py" "$E/neg" > "$E/verdict-neg.log" 2>&1; echo $? > "$E/verdict-neg.rc"` — 기대 rc `1`, 끝 줄이 `verdict FAIL `로 시작, 아래 다섯 줄이 각각 `grep -c` `1`: `^FAIL residual_median_m `, `^FAIL residual_p90_m `, `^FAIL residual_max_m `, `^FAIL colmap_median_agrees `, `^FAIL splat_to_sfm_median_m `(정합 전 모델의 위·아래 방향과 높이는 실행마다 임의라 `up`·`camera_height_m` 줄은 기대에 넣지 않는다).
  7. **런북 두 줄**: `cd "$E" && "$PY" "$E/render.py" "$E" "$(date +%F)" > "$E/runbook-lines.txt" 2> "$E/render.err"; echo $? > "$E/render.rc"` — 기대 rc `0`, `wc -l < "$E/runbook-lines.txt" | tr -d ' '` `2`, `grep -c '<' "$E/runbook-lines.txt"` `0`. `cd "$W" && "$PY" "$E/apply.py" docs/runbooks/mac-recon.md "$E/runbook-lines.txt" > "$E/apply.log" 2>&1; echo $? > "$E/apply.rc"` — 기대 rc `0`, `apply.log` 세 줄 `anchor 1`·`old_row 1`·`applied`. 확인: `cd "$W" && git diff --numstat -- docs/runbooks/mac-recon.md > "$E/numstat.log"` — 기대 `2	1	docs/runbooks/mac-recon.md`. 더한 줄이 렌더 결과와 같은지: `cd "$W" && git diff -U0 -- docs/runbooks/mac-recon.md | grep -E '^\+[^+]' | sed 's/^+//' | diff "$E/runbook-lines.txt" - > "$E/added.diff"; echo "exit=$?" >> "$E/added.diff"` — 기대 `exit=0` 한 줄. 지운 줄은 #5 옛 행 하나: `cd "$W" && git diff -U0 -- docs/runbooks/mac-recon.md | grep -c -E '^-\| 5 \| `colmap model_aligner`'` — 기대 `1`. 칸 자기 검사(규칙 17 b): `cd "$W" && git diff -U0 origin/main -- docs/runbooks/mac-recon.md | grep '^+[^+]' > "$E/cell-lines-1.txt"; wc -l < "$E/cell-lines-1.txt" | tr -d ' ' > "$E/cell-lines-1-count.log"; grep -n -E '\.log|영록|R[0-9]{3}' "$E/cell-lines-1.txt" > "$E/cell-grep-1.log"; wc -l < "$E/cell-grep-1.log" | tr -d ' ' > "$E/cell-grep-1-count.log"` — 기대 `cell-lines-1-count.log` `2`, `cell-grep-1-count.log` `0`(상시 규칙 "PR 본문 공통" 7 — 0이 아니면 줄을 손으로 고치지 않고 멈춘다). `apply.py`를 두 번 돌리지 않는다(두 번째는 `old_row 0`으로 rc 1 — 그게 정상이다).
  8. **게이트·커밋·push**: 파이썬 게이트(규칙 13, 하네스 백그라운드): `cd "$W/tools" && source .venv/bin/activate && { /usr/bin/timeout 300 ruff check . && /usr/bin/timeout 300 ruff format --check . && /usr/bin/timeout 1800 pytest -q && /usr/bin/timeout 300 python scripts/check_repo.py; } > "$E/gate.log" 2>&1; echo $? > "$E/gate.rc"` — 기대 rc `0`(코드 변경은 없지만 `check_repo.py`가 런북 링크를 본다; rc 124 = 시간 초과, 다시 돌리지 않고 멈춤). 커밋: `cd "$W" && git add docs/runbooks/mac-recon.md && git diff --cached --name-only > "$E/c1-files.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-30a: mac-recon — model_aligner EXIF GPS ENU 정합·정합 좌표 splat 수치(공개 Tyrol)" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c1-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-c1.log"` — 기대: `c1-files.log` 한 줄 `docs/runbooks/mac-recon.md`, `author-c1.log` `재환 <jaehwan.local@localhost>`. 게이트 로그가 런북보다 새것인지: `[ "$E/gate.log" -nt "$W/docs/runbooks/mac-recon.md" ]; echo "newer=$?" > "$E/mtime.log"` — 기대 `newer=0`. `git -C "$W" push -u origin local/jaehwan-j30a-colmap-enu > "$E/push.log" 2>&1; echo "exit=$?" >> "$E/push.log"` — 기대 끝 줄 `exit=0`. 브랜치 파일: `git -C "$W" diff --name-only origin/main...HEAD > "$E/branch-files.log"` — 기대 한 줄 `docs/runbooks/mac-recon.md`. push 뒤 상태: `git -C "$W" status --porcelain > "$E/status-after-push.log"; diff "$E/status-before.log" "$E/status-after-push.log" > "$E/status-push.diff"; echo "exit=$?" >> "$E/status-push.diff"` — 기대 `exit=0` 한 줄. PR 열기(첫 본문은 이 한 문장뿐 — 상시 규칙 "PR 본문 공통" 2, 규칙 2; 2026-11-28 문서 9 검증 지적: 옛 일곱 줄 꼴을 이 한 줄로 바꿨다, dry-run sh·zsh 모두 한 줄 `CI 진행 중 — 결과는 아래에 추가`): `printf '%s\n' 'CI 진행 중 — 결과는 아래에 추가' > "$E/pr-body-initial.md"; cd "$W" && gh pr create --base main --head local/jaehwan-j30a-colmap-enu --title "J-30a: COLMAP EXIF GPS ENU 정합과 정합 좌표 splat 수치(공개 Tyrol)" --body-file "$E/pr-body-initial.md" > "$E/pr-create.log" 2>&1; echo $? > "$E/pr-create.rc"` — 기대 `0`. PR 번호: `cd "$W" && gh pr view local/jaehwan-j30a-colmap-enu --json number --jq .number > "$E/pr-number.log" 2> "$E/pr-number.err"` — 기대 숫자 한 줄(`grep -c -x '[0-9][0-9]*' "$E/pr-number.log"` `1`, `wc -l < "$E/pr-number.log" | tr -d ' '` `1`; `gh`가 stderr에 찍는 안내 문구는 `pr-number.err`로 가고 판정하지 않는다). 아래 명령은 이 파일에서 번호를 읽는다. **커밋 2(PR 번호, 상시 규칙 "PR 본문 공통" 8)**: `N=$(cat "$E/pr-number.log"); sed "s/ 근거: J-30a PR\./ 근거: PR #$N./" "$E/runbook-lines.txt" > "$E/runbook-lines-final.txt"; cd "$W" && sed -i '' "s/ 근거: J-30a PR\./ 근거: PR #$N./" docs/runbooks/mac-recon.md; echo $? > "$E/runbook-pr.rc"` — 기대 `0`. 확인: `cd "$W" && git diff -U0 origin/main -- docs/runbooks/mac-recon.md | grep -E '^\+[^+]' | sed 's/^+//' | diff "$E/runbook-lines-final.txt" - > "$E/added-final.diff"; echo "exit=$?" >> "$E/added-final.diff"` — 기대 `exit=0` 한 줄. `cd "$W" && grep -c ' 근거: J-30a PR\.' docs/runbooks/mac-recon.md` `0`. `cd "$W" && git diff --numstat origin/main -- docs/runbooks/mac-recon.md` `2	1	docs/runbooks/mac-recon.md`. 칸 자기 검사: `cd "$W" && git diff -U0 origin/main -- docs/runbooks/mac-recon.md | grep '^+[^+]' > "$E/cell-lines-2.txt"; wc -l < "$E/cell-lines-2.txt" | tr -d ' ' > "$E/cell-lines-2-count.log"; grep -n -E '\.log|영록|R[0-9]{3}' "$E/cell-lines-2.txt" > "$E/cell-grep-2.log"; wc -l < "$E/cell-grep-2.log" | tr -d ' ' > "$E/cell-grep-2-count.log"` — 기대 `cell-lines-2-count.log` `2`, `cell-grep-2-count.log` `0`(상시 규칙 "PR 본문 공통" 7 — 0이 아니면 줄을 손으로 고치지 않고 멈춘다). 게이트 다시(규칙 13): `cd "$W/tools" && source .venv/bin/activate && { /usr/bin/timeout 300 ruff check . && /usr/bin/timeout 300 ruff format --check . && /usr/bin/timeout 1800 pytest -q && /usr/bin/timeout 300 python scripts/check_repo.py; } > "$E/gate-2.log" 2>&1; echo $? > "$E/gate-2.rc"`(하네스 백그라운드) — 기대 `0`(rc 124 = 시간 초과, 다시 돌리지 않고 멈춤). `[ "$E/gate-2.log" -nt "$W/docs/runbooks/mac-recon.md" ]; echo "newer=$?" > "$E/mtime-2.log"` — 기대 `newer=0`. 커밋: `cd "$W" && git add docs/runbooks/mac-recon.md && git diff --cached --name-only > "$E/c2-files.log" && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-30a: 기록 줄의 근거를 PR 번호로" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c2-commit.log" 2>&1; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-2.log"` — 기대 `c2-files.log` 한 줄 `docs/runbooks/mac-recon.md`, `author-2.log` `재환 <jaehwan.local@localhost>`. `git -C "$W" push > "$E/push-2.log" 2>&1; echo "exit=$?" >> "$E/push-2.log"` — 기대 끝 줄 `exit=0`. `git -C "$W" diff --name-only origin/main...HEAD > "$E/branch-files-2.log"` — 기대 한 줄 `docs/runbooks/mac-recon.md`. `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-final-2.diff"; echo "exit=$?" >> "$E/status-final-2.diff"` — 기대 `exit=0` 한 줄. CI(하네스 백그라운드, 커밋 2의 push 뒤): `cd "$W" && /usr/bin/timeout 1800 gh pr checks "$(cat "$E/pr-number.log")" --watch --interval 30 > "$E/checks-watch.log" 2>&1; echo "exit=$?" >> "$E/checks-watch.log"; /usr/bin/timeout 120 gh pr checks "$(cat "$E/pr-number.log")" > "$E/checks.log" 2>&1` — 기대: 모든 행 pass.
  9. **PR 본문**: PR 본문·자리표시 분류·칸 자기 검사·근거 표기는 상시 규칙 "PR 본문 공통(모든 과제)"을 따른다(이 절과 다르면 그 소절을 따른다). `## 결과`에는 관찰한 값만 둔다: `verdict.log` 13줄 원문, `align-check.log`·`splat-check.log`·`splat-control.log` 원문, `aligner.log`의 `=> Alignment error:` 줄, 각 단계 rc, `load-before.log`·`load-after.log`의 LM Studio 줄(로그 원문은 백틱 펜스 블록에) — 과제 번호·규칙 번호·날짜는 이 절에 쓰지 않는다. 시간·메모리는 "기록, 판정 근거 아님"으로만 쓴다. `## 남은 [미확인]`에는 EXIF 고도 기준면, J-30b 메시 절반, zone 원점 변환, 실촬영 리허설. `## 완료 기준 대조`는 아래 (a)~(i) 한 줄씩. 본문 초안은 `$E/pr-body.md`. 게시 전 검사(규칙 10 e·f) — **대상 로그는 이 목록으로 고정한다**(본문 초안·게시본·`task.txt`·`commands.txt`·`runbook-lines.txt`·검사 로그 자신은 넣지 않는다): `"$E"/versions.log "$E"/ref.log "$E"/exiftool-first.log "$E"/fe.log "$E"/match.log "$E"/mapper.log "$E"/analyzer.log "$E"/aligner.log "$E"/align-check.log "$E"/undist.log "$E"/brush.log "$E"/inspect.json "$E"/splat-check.log "$E"/splat-control.log "$E"/verdict.log "$E"/verdict-neg.log "$E"/load-before.log "$E"/load-after.log "$E"/numstat.log "$E"/gate.log "$E"/checks.log`.
     - 인용 검사: `## 결과` 절의 백틱 문자열마다 그 문자열이 근거로 든 로그 **한 개**를 `"$E/quotes.tsv"`에 `<문자열><탭><위 목록의 파일 이름>`으로 적는다(로그 인용이 아닌 파일 이름·명령은 파일 칸에 `라벨`). 빠진 것 확인·세기와 아래 숫자 검사는 펜스 `j30a-bodycheck-sh`(이 절의 허용 파일 줄 바로 앞)가 한 번에 한다(2026-11-28 문서 9: 백틱이 든 옛 인라인 명령을 글자 그대로 옮긴 스크립트 — 옛 명령과 같은 여섯 파일 `body-quotes.txt`·`tsv-quotes.txt`·`quotes-missing.log`·`quotes-check.log`·`body-numbers.txt`·`numbers-check.log`를 쓴다(`checks-2.log`가 없으면 내용도 같다); 숫자 검사 목록 끝의 `checks.log`는 `checks-2.log`가 있으면 그것; 상시 규칙 "PR 본문 공통" 11·14). `quotes.tsv`를 다 쓴 뒤 뽑기·확인·실행을 한 호출로: `awk -v n=j30a-bodycheck-sh 'BEGIN {b = sprintf("%c%c%c", 96, 96, 96)} x && $0 == b {x = 0} x {print} !x && index($0, b) == 1 && $0 ~ (" " n "$") {x = 1}' "$E/task.txt" > "$E/j30a_bodycheck.sh"; [ "$(wc -l < "$E/j30a_bodycheck.sh" | tr -d ' ')" = "13" ] && head -n 1 "$E/j30a_bodycheck.sh" | grep -q -x '#!/bin/sh' && sh "$E/j30a_bodycheck.sh" "$E" > "$E/bodycheck.log" 2>&1; echo $? > "$E/bodycheck.rc"` — 기대 `bodycheck.rc` `0`, `bodycheck.log` 빈 파일, `quotes-missing.log` 빈 파일. 세기는 `quotes-check.log`(`quotes.tsv` 행마다 한 행) — 기대: `cut -f1 "$E/quotes-check.log" | grep -c -x '0'`가 `0`.
     - 숫자 검사: 위 `j30a_bodycheck.sh`가 쓴 `body-numbers.txt`·`numbers-check.log`(숫자마다 한 행, 대상은 위 고정 목록) — 기대: `cut -f1 "$E/numbers-check.log" | grep -c -x '0'`가 `0`.
     - 0이 나온 것은 고치거나 지운다. 그다음 상시 규칙 "PR 본문 공통" 3(점검표 대조)·5(자리표시 분류)·6(조립·게시·다시 읽기)을 적힌 그대로 돌린다.
```sh j30a-bodycheck-sh
#!/bin/sh
# J-30a: quote and number checks of the PR draft (usage: sh j30a_bodycheck.sh <E>); needs E/pr-body.md and E/quotes.tsv.
# Same commands as the inline checks they replace (docs 9); writes body-quotes.txt, tsv-quotes.txt,
# quotes-missing.log, quotes-check.log (one row per quotes.tsv row), body-numbers.txt, numbers-check.log (one row per number).
E=$1
CK=checks.log
if [ -e "$E/checks-2.log" ]; then CK=checks-2.log; fi
awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '`[^`]+`' | sed 's/^`//;s/`$//' | sort -u > "$E/body-quotes.txt"
cut -f1 "$E/quotes.tsv" | sort -u > "$E/tsv-quotes.txt"
comm -23 "$E/body-quotes.txt" "$E/tsv-quotes.txt" > "$E/quotes-missing.log"
while IFS="$(printf '\t')" read -r q f; do if [ "$f" = "라벨" ]; then n="라벨"; else n=$(grep -F -c -- "$q" "$E/$f"); fi; printf '%s\t%s\t%s\n' "$n" "$f" "$q"; done < "$E/quotes.tsv" > "$E/quotes-check.log"
awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' | grep -oE '[0-9]{2,}' | sort -u > "$E/body-numbers.txt"
while read -r x; do printf '%s\t%s\n' "$(cat "$E"/versions.log "$E"/ref.log "$E"/exiftool-first.log "$E"/fe.log "$E"/match.log "$E"/mapper.log "$E"/analyzer.log "$E"/aligner.log "$E"/align-check.log "$E"/undist.log "$E"/brush.log "$E"/inspect.json "$E"/splat-check.log "$E"/splat-control.log "$E"/verdict.log "$E"/verdict-neg.log "$E"/load-before.log "$E"/load-after.log "$E"/numstat.log "$E"/gate.log "$E/$CK" | grep -c -- "$x")" "$x"; done < "$E/body-numbers.txt" > "$E/numbers-check.log"
```

- **허용 파일**: `docs/runbooks/mac-recon.md`(설계 10의 두 줄만 — M3 "정합" 문단 뒤 한 줄 추가, §6 #5 행의 빈 칸 채움. 커밋 2는 두 줄 끝의 근거 표식만 바꾼다). 그 밖의 저장소 파일은 건드리지 않는다(`tools/`·`pyproject.toml`·CI·`check_repo.py`·WP-21·STATUS 등 공유 문서 포함). 스크립트·로그·데이터는 `$E`에만.
- **멈춤 조건(정하지 말고 영록에게 묻는다)**: `task.txt`의 첫 줄·두 `grep -c`, `ph.awk` 줄 수, `fence-lines.diff`, `versions.log`가 기대와 다를 때. `aligner-help.log`의 옵션 수가 `5`가 아니거나 `--robust_alignment`가 나올 때(**옵션을 바꾸거나 더하지 않는다**). `overlap.log`가 비어 있지 않을 때. 입력 장수·JPG 외 파일 수·입력 해시가 기대와 다를 때, 또는 할 일 5 뒤 해시가 바뀌었을 때. 잠금 확인이 `no lock`이 아닐 때. 부하 기록에서 `lms` 명령이 실패해도 멈추지 않고 그 출력 그대로 적는다(판정 아님). `ref.rc`가 0이 아니거나 `ref.log`가 펜스와 다르거나(특히 `missing_gps`가 0이 아님 = GPS를 못 읽음) `ref_gps.txt` sha256·줄 수·`exiftool-first.log`가 다를 때. `fe.rc`·`match.rc`·`mapper.rc`·`analyzer.rc`·`aligner.rc`·`conv-*.rc`·`undist.rc`·`brush.rc`·`inspect.rc`·`splat-*.rc`·`align-check.rc`가 0이 아닐 때 — 특히 **rc 124(`timeout`) = CPU·GPU 실행이 정한 시간을 넘음**이면 같은 명령을 다시 돌리지 않는다(규칙 5). `sparse`에 `0` 말고 다른 폴더가 있거나(모델이 끊김) `Registered images: 76`이 아닐 때(**76 미만 등록**). `aligner.log`에 `unrecognised option`, `You must provide a maximum alignment error`, `Cannot align with insufficient reference locations`, `Alignment failed`, `Use location file or database, not both` 중 하나가 있거나 기대 네 줄이 `1`이 아닐 때(**inlier 부족·정합 실패** 포함). `verdict.rc`가 0이 아니거나 `FAIL` 줄이 하나라도 있을 때(기준·스크립트를 고치지 않는다, 값과 함께 묻는다). `verdict-neg`가 기대와 다를 때. `status-run.diff`가 `exit=0`이 아닐 때(저장소에 무엇이 생김 — 지우지 말고 `git -C "$W" status --porcelain` 원문과 함께 묻는다). `render.rc`·`apply.rc`·`runbook-pr.rc`가 0이 아니거나 `apply.log`·`numstat.log`·`added.diff`·`added-final.diff`·지운 줄 수가 기대와 다를 때. `cell-lines-1-count.log`·`cell-lines-2-count.log`가 `2`가 아니거나 `cell-grep-1-count.log`·`cell-grep-2-count.log`가 `0`이 아닐 때(줄을 손으로 고치지 않는다, 렌더 스크립트도 고치지 않는다). `gate.rc`·`gate-2.rc`가 0이 아닐 때(rc 124 포함, 다른 파일을 고치거나 `ruff format`으로 바꾸지 않는다). `c1-files.log`·`author-c1.log`·`c2-files.log`·`author-2.log`가 다를 때. `mtime.log`·`mtime-2.log`가 `newer=0`이 아닐 때. `push.log`·`push-2.log`가 `exit=0`으로 끝나지 않을 때, `branch-files.log`·`branch-files-2.log`가 `docs/runbooks/mac-recon.md` 한 줄이 아니거나 `status-push.diff`·`status-final-2.diff`가 `exit=0`이 아닐 때. `pr-create.rc`·`pr-edit.rc`가 0이 아니거나 `pr-number.log`가 숫자 한 줄이 아닐 때. 상시 규칙 "PR 본문 공통" 9의 공통 멈춤 조건. `checks.log`에 pass가 아닌 행이 있을 때. 그 밖에 이 절의 "기대"와 다른 값이 하나라도 나올 때. 이 과제는 GUI 잠금을 잡지 않으므로 풀 잠금이 없다(잠금 파일을 만들거나 지우지 않는다).
- **완료 기준**:
  - (a) 준비: `task.txt` 첫 줄 `#### J-30a `·dry-run 줄 `grep -c` `1`·공통 소절 머리 `grep -c` `1`, `ph.awk` 37줄, `fence-lines.diff` `exit=0`, `versions.log` 세 줄, 옵션 수 `5`·`--robust_alignment` `0`, `overlap.log` 빈 파일, `input-hash-before.log` `c28c1998b732270ccb1bc6e93267779fbb8f30bdd449c6059ef241317c8aebb3`.
  - (b) 참조: `ref.rc` `0`, `ref.log` = 펜스 `j30a-ref-expected`, `ref_gps.txt` sha256 `989373f7b3c7e2d6befb8b5582a3262c433f69dee2512bf3799dd82d00a9ddf6`·76줄, `exiftool-first.log` `DJI_0352.JPG 46.9482009166667 12.062021 1645`.
  - (c) SfM: `fe.rc`·`match.rc`·`mapper.rc`·`analyzer.rc` 모두 `0`, `fe.log`의 `Processed file [`·`GPS:` 각 `76`, `ls "$E/sparse"` = `0`, `Registered images: 76` 1줄.
  - (d) 정합: `aligner.rc` `0`, `aligner.log`의 네 줄(원점·`=> Using 76 reference images`·`=> Alignment error:`·`=> Alignment succeeded`) 각 `1`, `sim3.txt` 필드 `8`, `align-check.log` 원문(11줄, 첫 네 줄이 할 일 4의 기대).
  - (e) splat: `undist.rc`·`conv-undist.rc`·`brush.rc`·`inspect.rc`·`splat-check.rc`·`splat-control.rc` 모두 `0`, `backend: Metal` 1줄 이상, `export_3000.ply` 있음, `splat-check.log`·`splat-control.log` 원문.
  - (f) 판정: `verdict.rc` `0`, `PASS` 13줄·`FAIL` 0줄, 끝 줄 `verdict PASS 13/13`. 비공허: `verdict-neg.rc` `1`, 끝 줄 `verdict FAIL …`, 할 일 6의 `FAIL` 다섯 줄 각 `1`.
  - (g) 저장소·입력: `status-run.diff` `exit=0`, 입력 해시 전후 같음. 런북: `render.rc`·`apply.rc` `0`, `apply.log` 세 줄, `numstat.log` `2	1	docs/runbooks/mac-recon.md`, `added.diff` `exit=0`, 지운 줄 `1`, `cell-lines-1-count.log` `2`, `cell-grep-1-count.log` `0`. `branch-files.log` = `docs/runbooks/mac-recon.md` 한 줄.
  - (h) 게이트 `gate.rc` `0`·`mtime.log` `newer=0`, 작성자 `재환 <jaehwan.local@localhost>`, `push.log` 끝 줄 `exit=0`, `pr-create.rc` `0`·`pr-number.log` 숫자 한 줄, CI `checks.log` 모든 행 pass 원문(규칙 2), `status-push.diff` `exit=0`. 커밋 2: `runbook-pr.rc` `0`, `added-final.diff` `exit=0`, `근거: J-30a PR.` 0줄, `origin/main` 대비 numstat `2	1	docs/runbooks/mac-recon.md`, `cell-lines-2-count.log` `2`, `cell-grep-2-count.log` `0`, `gate-2.rc` `0`, `mtime-2.log` `newer=0`, `c2-files.log`·`author-2.log` 기대대로, `push-2.log` 끝 줄 `exit=0`, `branch-files-2.log` 한 줄, `status-final-2.diff` `exit=0`.
  - (i) PR 본문: 절 순서(상시 규칙 "PR 본문 공통" 2), "완료 기준 대조" 절과 점검표(그날 규칙 수만큼, 소절 3), `## 결과`에 부하 기록(LM Studio 줄) 원문, `quotes-missing.log` 빈 파일, `quotes-check.log`·`numbers-check.log`에 0 없음. 공통 완료 기준 (P)(소절 10): `checklist.diff` `exit=0`, `ph-unfilled.log` `0`, `pr-edit.rc` `0`, `ph-posted-unfilled.log` `0`, `ph-table.diff` `exit=0`, `signature-last.log` `1`.
- **병합 시 반영(영록)**: STATUS 재환 절에 J-30a 행. WP-21 "남은 작업" 4 끝에 날짜 메모(희소 모델 → EXIF GPS ENU 정합과 정합 좌표 splat은 J-30a로 확인, 메시 절반은 J-30b). D-023 "좌표" 줄의 [미확인]에 날짜 메모를 더할지는 영록이 판단한다(공유 문서라 재환은 고치지 않는다). J-30b 설계(설계 13)를 이 파일에 쓰고 배정 순서를 정한다. J-30a 절의 펜스 `j30a-make-ref`·`j30a-check-align`·`j30a-ref-expected`는 J-30b가 끝날 때까지 지우거나 줄이지 않는다(J-30b 할 일 2가 이름으로 뽑는다).
- **왜 재환 / 위험**: 명령·옵션·스크립트·기준이 모두 정해져 있고 결과가 숫자와 종료 코드로 판정된다. GUI·UE·Astra 레인·소유자 촬영이 필요 없다. 위험: ① 옵션 즉흥 — 4.2.1은 접두 철자를 받아 틀린 옵션이 조용히 통과할 수 있다(설계 4) → 명령을 글자 그대로 복사하고 `-h` 옵션 수로 막는다(규칙 1·6). ② 긴 CPU 실행(특징 추출 dry-run 324 s, peak footprint 약 36 GB, `/usr/bin/time -l` swaps 0 — 같은 세션 뒤 `lms ps`가 모델 94.58 GB 로드를 보였고 실행 중 로드 여부는 [미확인]) → 모든 실행에 `timeout`, 넘으면 멈춤. ③ "미터" 과장 — EXIF 고도 기준면 [미확인], 드론 GPS 오차 → 문장은 렌더 스크립트가 "EXIF GPS ENU에 정합, 잔차 N m"으로 고정한다(규칙 15). ④ 품질로 번지기 — floater·모습·"충분히 좋다"는 판정하지 않는다. 펜스의 숫자만 본다(품질은 V-05). ⑤ 메시 절반이 빠짐 — J-30b(설계 13), 결과 문장에 적힌다. ⑥ 도구가 저장소에 쓰기 — 모든 명령이 `cd "$E…"`로 시작하고 `status-run.diff`로 확인한다. ⑦ 실행 간 흔들림 — `mapper`·Brush는 실행마다 값이 조금 다르다(dry-run 두 번: 잔차 중앙값 1.201·1.176 m, splat 1.074·1.059 m) → 기준은 상한이고, 값을 dry-run과 같게 맞추려 하지 않는다.
- **dry-run 범위(Opus 2026-11-28, J-30a)**: 이 Mac에서 같은 입력·같은 플래그로 할 일 2~7을 scratch 폴더(`$TMPDIR` 밖 세션 scratchpad, 저장소 밖)에서 돌렸다: 참조 파일 76/76·누락 0·sha256 위 값(메인 venv와 `$W/tools/.venv` 둘 다), `feature_extractor` rc 0(324 s, `GPS:` 76줄), `exhaustive_matcher` rc 0(29 s), `mapper` rc 0(80 s, 모델 1개, 등록 76/76, 점 68,938, 재투영 0.850 px), `model_aligner` rc 0(`=> Alignment error: 1.142564 (mean), 1.200858 (median)`; `--alignment_max_error` 3과 10이 같은 `sim3.txt`, 첫 값 32.4702), `check_align` 잔차 1.201/1.671/2.172 m·수평 0.514·수직 1.031·높이 60.98 m·`+Z`, 정합 전 모델로는 105.488 m·`-Z`, `image_undistorter` rc 0(PINHOLE 5471×3648), Brush rc 0(83 s, Metal, 191,643 splat, 같은 시드 두 번째 191,751), `golmok-splat inspect` `count` 191643·`sh_degree` 3, splat → SfM 1.074/7.028 m·대조군 93.735 m, `verdict` `verdict PASS 13/13`, 비공허 사례 rc 1(`verdict FAIL 5/13`, 할 일 6의 다섯 줄 포함), `render`·`apply`를 `origin/main` `8ba637c` scratch 사본(git init)의 mac-recon에 적용 → numstat `2	1`, 두 번째 `apply`는 `old_row 0` rc 1, 그 사본에서 `check_repo.py` OK·`pytest -q` 1937 passed·3 skipped. `mapper`+정합만 한 번 더(같은 데이터베이스): 1.176/1.634/2.155 m, COLMAP median 1.175685, 축척 33.4693. 실패 메시지 확인: `--alignment_max_error` 없음 → "You must provide a maximum alignment error > 0" rc 1, 참조 2줄 → "Cannot align with insufficient reference locations." rc 1, `--robust_alignment` → `unrecognised option` rc 1, `--alignment_typ enu`(오타) → rc 0. 펜스 6개는 `ruff format`을 거친 파일과 같은 글자다. dry-run하지 못한 것: 재환 worktree의 브랜치·커밋·push·`gh` 명령(겹침·PR·CI), 인용·숫자·자리표시 검사 파이프(본문이 없어서), `lms ps`를 명령 공통의 꼴로 감싼 부하 기록(단독 실행은 확인: `qwen3.8-flash-next … IDLE 94.58 GB`). 설계 리뷰 반영분(2026-11-28, Opus 문서 에이전트): `timeout`을 단 게이트는 `8ba637c` scratch 사본에서 rc 0(1937 passed, 3 skipped, 약 78 s), `check_splat.py`를 `aligned_txt/points3D.txt`에 돌린 출력 6줄은 `undistorted/sparse/points3D.txt`에 돌린 것과 같았다(splat → SfM 1.074/7.028 m), push 뒤 상태 비교(`status-push.diff`)·`branch-files.log`·`-nt` 확인은 git 저장소로 만든 scratch 사본에서 기대대로였다. `gh pr create`·`gh pr edit`는 dry-run하지 못했다. (보충 2026-11-28, 재환 레인 문서 7: 할 일 9의 자리표시 단계를 재검증 지적대로 분류 판정으로 바꿨다. 그 `awk`를 이 절에서 그대로 떼어 견본 본문 — `## 완료 기준 대조`의 `~~~` 블록에 이 절의 완료 기준, `## 실행한 명령`의 백틱 블록에 `<…>`가 든 명령 두 줄, 끝에 `## 자리표시 분류` 개수 표 — 에 돌리자 `placeholder-unfilled.log` `0`(원문 인용 1·명령 기록 2), 점검표 줄에 `<n>` 하나를 넣은 본문에서는 `1`이었다. 실제 게시 본문에는 돌리지 않았다.) 문서 7 수정(2026-11-28, Opus): `j30a-render`의 두 문자열 끝을 `근거: J-30a PR.` 표식으로 바꾼 뒤(펜스 45줄 그대로) 견본 로그에서 rc 0·2줄, 두 줄에 `$TMPDIR` 0, 규칙 17 b의 `grep -n -E` 0건. 할 일 1의 두 `awk` 추출(첫 줄 `#### J-30a `, dry-run 줄 1, 공통 소절 머리 1)과 `X` 추출 9개, 할 일 8의 커밋 2 `sed`(가짜 번호, 두 줄 모두 바뀜)는 scratch 사본에서 돌렸다. 위 문장의 옛 자리표시 분류 견본 결과는 그때의 기록이고, 지금 분류는 상시 규칙 소절의 `common-ph-awk`다.

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
- **결과(2026-11-28, [#157](https://github.com/wooklym/golmok/pull/157) · `ff77ba8`, 리뷰 R157(1회 보류: 본문만) → R157-2)**: 새 스텁 테스트 3개, `tools/tests/test_ue_mac_scripts.py` 추가만 47줄, `-k add_gasp` 11 passed, 파일 48 passed(R157 재현). 본문이 아직 하지 않은 일을 과거형으로 적은 다섯 줄은 고친 뒤 병합했고, 그 실수로 작업 규칙 18이 생겼다.

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

#### J-30b Object Capture 메시를 J-30a의 GPS-ENU 정합 좌표로: 카메라 중심 Sim3(Umeyama) + OBJ 정점 ↔ 정합 SfM 점 거리, 수치 확인만 — 설계 확정(Opus 2026-11-28)
- **출처**: [WP-21](WP-21-mac-recon-pipeline.md) "남은 작업" 4("COLMAP 희소 모델 미터·ENU 정합 → 메시·splat 좌표 공유를 끝까지 해 본다"), [D-023](../DECISIONS.md) "좌표" 줄(:352 — 메시와 splat이 좌표를 공유하려면 하나의 COLMAP 희소 모델에서 나와야 하고, Object Capture는 실행마다 자기 좌표계를 만든다), [mac-recon.md](../runbooks/mac-recon.md) M4 "좌표" 줄(:113 — 메시·포즈·점군은 같은 실행끼리만 같은 좌표계, zone-local로 옮기는 도구는 없다, §6 #6), §6 #6 행(:231, 확인 결과 칸 빈 칸), objcap 결과 표 Tyrol `full` 행(:186 — 125,678 정점 / 250,000 삼각형), 저작자 표시 :180(Tyrol 교회 드론 76장 CC BY 4.0). 이 절 위의 J-30a 설계 1·12·13(메시 절반은 J-30b, 새 저장소 코드 없음, `$TMPDIR`이 지워질 수 있으니 `aligned`·`aligned_txt`가 있는지 먼저 확인하고 없으면 J-30a 할 일 3~4를 다시 돌린다 — 축척은 실행마다 다르다). 포즈의 뜻: [tools/mac/objcap/README.md](../../tools/mac/objcap/README.md) §4(:80-107 — Apple 문서는 축·방향·단위를 적지 않는다, 측정으로 `Pose.transform`은 camera→world이고 `translation`이 카메라 중심, 메시·점군·포즈는 같은 좌표계, Tyrol에서 +Y가 위·거의 미터). 입력(저장소 밖, 읽기만): `~/golmok_data/recon-smoke/objcap/tyrol-full/poses.json`(`"format" : "golmok-objcap poses v1"`, 샘플 76, 이미지 이름 76개 모두 다름, `translation` 없는 샘플 0 — Opus 확인)과 같은 실행의 `obj/baked_mesh_32dae850.obj`(28,710,632 B, `v ` 줄 125,678개 모두 필드 4개; `summary.json`의 `settings.detail` `full`, `results.poses.sample_count` 76). 유사변환 식: Umeyama, "Least-squares estimation of transformation parameters between two point patterns", IEEE TPAMI 13(4), 1991, [doi:10.1109/34.88573](https://doi.org/10.1109/34.88573)(반사를 막는 `diag(1, 1, -1)` 보정 포함). 최근접 거리: [`scipy.spatial.cKDTree`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.html)(`$W/tools/.venv`의 scipy 1.18.1 — J-30a `j30a-check-splat`와 같은 것).
- **설계 (확정, Opus 2026-11-28)**: 재환은 아래를 그대로 옮긴다. 바꿀 점이 보이면 고치지 말고 묻는다.
  1. **범위**: Object Capture 메시를 J-30a가 만든 EXIF GPS ENU 정합 좌표로 옮기고, 같은 좌표에 놓이는지 **수치로만** 확인한다. 메시 품질·splat과의 이음매·"충분히 맞다"는 판정하지 않는다(V-05, Opus·소유자). zone 원점(매니페스트 `origin`)으로 옮기기, Object Capture 다시 돌리기, 실촬영은 하지 않는다. 결과 문장은 렌더 스크립트가 "공개 Tyrol 76장 CC BY 4.0, 1회 실행, 좌표 일관성 확인이지 품질 판정 아님, zone 원점 안 함"으로 고정한다(규칙 3·15).
  2. **맞추는 것은 카메라 중심뿐**: `poses.json`의 `translation`(카메라 중심 — objcap README §4의 측정)과 정합 모델 `images.txt`의 카메라 중심 `-Rᵀt`를 **이미지 이름**으로 짝짓는다. 회전(`rotation_quaternion_xyzw`·`transform_matrix_rows`)은 쓰지 않는다 — Apple이 축을 문서화하지 않았고, 중심만으로 Sim3가 정해진다. Umeyama는 반사 보정을 넣어 늘 진짜 회전(행렬식 +1)을 낸다. 보정이 필요했는지(`reflection_guard`)를 기록하고, `1`이면(손잡이 방향이 다름) 판정이 FAIL이다 — 축을 뒤집어 맞추지 않는다. Opus dry-run 두 번 모두 `0`, 축척 1.0036(Object Capture 좌표가 이미 거의 미터 — README §4의 "0.988배"와 같은 규모).
  3. **정합 모델은 J-30a의 것을 다시 쓴다**: `J="$TMPDIR/jaehwan/J-30a"`. 펜스 `j30b-source-sh`가 J-30a 폴더의 파일 8개(`ref_gps.txt`·`check_align.py`·`align-check.log`·`splat-check.log`·`aligned/sim3.txt`·`aligned_txt/images.txt`·`aligned_txt/points3D.txt`·`sparse_txt/points3D.txt`)가 모두 비지 않은 파일로 있는지 보고 `source j30a` 또는 `source rerun`을 정한다(재환이 고르지 않는다). `source j30a`이면 같은 실행인지 두 가지로 확인한다: ① J-30a의 `check_align.py`를 같은 입력에 다시 돌린 출력이 J-30a의 `align-check.log`와 바이트로 같다, ② 이 과제의 `sfm_points` 줄이 J-30a `splat-check.log`의 `sfm_points` 줄과 같다(splat 거리를 잰 그 점 파일이다). 다르면 멈춘다(어느 쪽도 고치지 않는다). `source rerun`이면(하나라도 없음 — `$TMPDIR` 정리 등) 할 일 2가 J-30a 할 일 2~4를 **J-30a 절의 펜스와 같은 플래그로** `$E/sfm`에 다시 만든다(J-30a 펜스 셋은 `tasks-main.md`에서 이름으로 뽑는다). 그 경우 축척·잔차·점 수는 실행마다 다르므로 기록만 하고, J-30a의 기준(잔차 중앙값 ≤ 3.0 m · p90 ≤ 5.0 m · 최대 ≤ 10.0 m)만 다시 본다. 렌더 스크립트가 어느 쪽이었는지 문장에 넣는다. J-30a 폴더는 읽기만 하고 아무것도 쓰거나 지우지 않는다.
  4. **확인 스크립트(펜스 `j30b-check-py`, numpy·scipy, `"$PY" -I`)**: 짝 수(`oc_samples`·`colmap_registered`·`common`), `reflection_guard`, `rotation_det`, `scale`, 잔차 중앙값·p90·최대(m), OBJ의 `v ` 줄을 **전부** 읽어(표본 추출 없음 — 125,678개, dry-run 약 3 s) Sim3로 옮긴 정점마다 가장 가까운 정합 SfM 점(`points3D.txt`)까지 거리 중앙값·p90, 대조군(옮기기 **전** 정점 ↔ 같은 점) 중앙값, 두 집합의 축별 중앙값을 고정 이름 13줄로 쓴다. 최근접은 `cKDTree.query(k=1)` 하나로 고정한다(근사·표본·청크 없음 — 시간은 판정하지 않는다).
  5. **통과 기준(펜스 `j30b-verdict-py`, 10개)**: 짝 76·76·76, `reflection_guard` 0, 축척 0.9 이상 1.1 이하, 잔차 **중앙값 ≤ 0.5 m · p90 ≤ 1.0 m · 최대 ≤ 3.0 m**, OBJ 정점 125678, 메시 → SfM **중앙값 ≤ 3.0 m · p90 ≤ 12.0 m**, 대조군 중앙값 ≥ 30.0 m. 근거: Opus dry-run 두 번 — J-30a dry-run의 서로 다른 `mapper` 실행 둘의 정합 모델(`aligned_txt` 점 68,938개, 같은 데이터베이스로 다시 돌린 `al2_txt` 점 68,532개): 축척 1.0036·1.0036, 잔차 0.192/0.318/1.172 m와 0.210/0.334/1.237 m, 메시 → SfM 1.259/5.437 m와 1.278/5.463 m, 대조군 53.651·54.154 m. 상한은 dry-run 값의 약 2~3배(J-30a 설계 9와 같은 잡는 법)로 실행 간 흔들림은 통과시키고, 아래 6의 틀린 좌표 셋은 떨어뜨린다. 축척 범위는 두 실행이 같은 값(1.0036)이라 넣었다 — 정합 **전** 모델을 잘못 고른 경우(축척 0.0309)를 이 줄 하나가 잡는다(그 경우 잔차·거리는 모델 단위라 작게 나와 통과한다). 메시 → SfM 중앙값(약 1.26 m)이 카메라 잔차(약 0.2 m)보다 큰 것은 SfM 점이 성기고(J-30a dry-run 최근접 간격 중앙값 0.630 m) 메시 정점이 SfM 점이 없는 면에도 있기 때문으로 보인다 — 가설이고 판정에 쓰지 않는다.
  6. **비공허(일부러 틀린 셋, 펜스 `j30b-neg-py`·`j30b-negcheck-sh`)**: ① `unaligned` — 같은 포즈를 정합 **전** 모델(`sparse_txt`)에 맞춤 → `scale`만 FAIL(`verdict FAIL 9/10`). ② `reverse` — 이름순 이름을 거꾸로 바꿔 짝을 틀리게(76장이 짝수라 76개 모두 바뀜) → `scale`·잔차 셋·메시 거리 둘 FAIL(`verdict FAIL 4/10`). ③ `mirror` — `translation`의 x 부호를 뒤집음(손잡이 방향이 다름) → `reflection_guard`·잔차 셋·메시 거리 둘 FAIL(`verdict FAIL 4/10`; 축척 0.9147은 범위 안이라 통과한다 — 그래서 `reflection_guard` 줄이 필요하다). FAIL 줄 이름은 펜스 `j30b-expected-neg`와 `diff`한다. Opus dry-run 두 모델 모두 같은 FAIL 줄(값: `reverse` 잔차 중앙값 60.533·60.538 m, `mirror` 43.870·43.887 m, 메시 거리 중앙값 73.055~90.559 m).
  7. **일회성, 새 저장소 코드 없음**: 스크립트는 이 절의 펜스와 `$E`에만 있다. `golmok-align` 하위 명령으로 만들지 않는다 — `tools/pyproject.toml`(콘솔 스크립트 등록)은 핫스팟이고, 실촬영 골목(C-02)의 Object Capture 출력·포즈 형식이 이 공개 세트와 같다는 근거가 아직 없다(J-30a 설계 12와 같은 판단). 저장소 도구가 필요해지면 V-05 앞에서 따로 설계한 과제로 한다(Claude 레인 코드). 허용 파일 `docs/runbooks/mac-recon.md`는 핫스팟도 Astra 레인도 아니다(CLAUDE.md §7.6 목록에 없음) — 훅 표시를 넣지 않는다.
  8. **기록(규칙 16, 덧붙이기만)**: 런북 두 군데만 — ① M3 "정합" 문단의 **J-30a 날짜 메모 줄**(`- 날짜 메모(J-30a, `로 시작하고 `근거: PR #번호.`로 끝나는 줄 — J-30a 병합 뒤에 생긴다) **바로 뒤에** 날짜 메모 한 줄을 더한다. ② §6 #6 행의 빈 "확인 결과" 칸을 채운다(다른 칸·다른 행은 그대로). 두 줄의 글자는 펜스 `j30b-render-py`가 로그에서 만들고(숫자를 손으로 옮기지 않는다), 펜스 `j30b-apply-py`가 넣는다(J-30a 메모 1번·J-30b 메모 0번·#6 옛 행 1번일 때만, 아니면 rc 1로 아무것도 쓰지 않는다). 두 줄 끝은 `근거: J-30b PR.` 표식이고, 커밋 2가 `근거: PR #번호.`로 바꾼다(상시 규칙 "PR 본문 공통" 8). #6의 "지금 아는 것" 칸("저장소 도구 없음")은 그대로 맞으므로 지우지 않는다.
  9. **라이선스·개인정보**: Tyrol 데이터는 CC BY 4.0이고 저작자 표시는 mac-recon :180에 이미 있다(메모도 "공개 Tyrol 드론 76장 CC BY 4.0"이라 적는다). 기본 경로(`source j30a`)는 이미지를 읽지 않고, 다시 만드는 경로는 J-30a와 같은 전례로 블러하지 않는다(J-30a 설계 11 — 재환이 블러 여부를 정하지 않는다). 모든 처리는 로컬이고 출력은 `$E`에만 있으며 외부로 올리지 않는다. 메시·포즈·PLY·데이터베이스는 커밋하지 않는다.
  10. **순서**: J-30a가 **병합된 뒤에만** 한다(같은 파일, 다른 줄 — 할 일 1의 `pre.diff`가 막는다: `origin/main`의 mac-recon에 J-30a 메모 줄이 정확히 1개, `근거: J-30a PR.` 0개여야 한다). 이 절은 J-30a의 추출 경계(`/^#### J-31a/`)를 바꾸지 않으려고 J-36 절 뒤에 둔다.
  11. **J-30b 뒤(이 과제 밖)**: zone 원점으로의 변환(실촬영 C-02의 GPS와 zone 매니페스트 `origin`이 있어야 한다), 같은 Sim3를 OBJ 파일에 적용해 내보내기, 메시와 splat을 한 장면에 올려 보는 확인은 V-05(Opus·소유자)의 몫이다.

```sh j30b-pre-sh
#!/bin/sh
# J-30b: state of mac-recon.md before the task (usage: sh j30b_pre.sh <mac-recon.md>)
DOC=$1
printf 'j30a_memo %s\n' "$(grep -c -E '^- [0-9]{4}-[0-9]{2}-[0-9]{2} 메모\(J-30a, .* 근거: PR #[0-9]+\.$' "$DOC")"
printf 'j30a_marker %s\n' "$(grep -c -F '근거: J-30a PR.' "$DOC")"
printf 'j30b_memo %s\n' "$(grep -c -F '메모(J-30b, ' "$DOC")"
printf 'row6_old %s\n' "$(grep -c -x -F '| 6 | objcap 메시 → zone-local 변환 | 저장소 도구 없음(`reproject`는 EPSG만) | 유사변환 단계 설계(WP-21 후속) | |' "$DOC")"
```

```sh j30b-source-sh
#!/bin/sh
# J-30b: which aligned model to use (usage: sh j30b_source.sh <J-30a folder> <J-30b folder>)
J=$1
E=$2
miss=0
for f in ref_gps.txt check_align.py align-check.log splat-check.log aligned/sim3.txt \
  aligned_txt/images.txt aligned_txt/points3D.txt sparse_txt/points3D.txt; do
  if [ -s "$J/$f" ]; then
    echo "have $f"
  else
    echo "missing $f"
    miss=$((miss + 1))
  fi
done
echo "missing_count $miss"
if [ "$miss" -eq 0 ]; then
  echo "source j30a"
  echo "model $J/aligned_txt"
  echo "unaligned $J/sparse_txt"
else
  echo "source rerun"
  echo "model $E/sfm/aligned_txt"
  echo "unaligned $E/sfm/sparse_txt"
fi
```

```python j30b-check-py
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

poses_path, model_dir, obj_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
samples = json.loads(poses_path.read_text(encoding="utf-8"))["samples"]
oc = {s["image"]: np.array(s["translation"], dtype=np.float64) for s in samples}
lines = [
    ln for ln in (model_dir / "images.txt").read_text(encoding="utf-8").splitlines() if not ln.startswith("#")
]
col = {}
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
    col[p[9]] = -r.T @ np.array([tx, ty, tz])

names = sorted(set(oc) & set(col))
src = np.array([oc[n] for n in names])
dst = np.array([col[n] for n in names])
xs, xd = src - src.mean(axis=0), dst - dst.mean(axis=0)
u, sv, vt = np.linalg.svd(xd.T @ xs / len(names))
reflect = np.linalg.det(u) * np.linalg.det(vt) < 0
fix = np.diag([1.0, 1.0, -1.0 if reflect else 1.0])
rot = u @ fix @ vt
scale = float(np.sum(sv * np.diag(fix)) / np.sum(xs.var(axis=0)))
trans = dst.mean(axis=0) - scale * rot @ src.mean(axis=0)
err = np.linalg.norm(src @ (scale * rot).T + trans - dst, axis=1)

with obj_path.open(encoding="utf-8") as f:
    verts = np.array([[float(v) for v in ln.split()[1:4]] for ln in f if ln.startswith("v ")])
pts = np.array(
    [
        [float(v) for v in ln.split()[1:4]]
        for ln in (model_dir / "points3D.txt").read_text(encoding="utf-8").splitlines()
        if not ln.startswith("#")
    ]
)
tree = cKDTree(pts)
mesh = verts @ (scale * rot).T + trans
dist, _ = tree.query(mesh, k=1)
raw, _ = tree.query(verts, k=1)
print("oc_samples", len(oc))
print("colmap_registered", len(col))
print("common", len(names))
print("reflection_guard", int(reflect))
print(f"rotation_det {np.linalg.det(rot):.6f}")
print(f"scale {scale:.4f}")
print(f"residual_m median {np.median(err):.3f} p90 {np.percentile(err, 90):.3f} max {err.max():.3f}")
print("obj_vertices", len(verts))
print("sfm_points", len(pts))
print(f"mesh_to_sfm_m median {np.median(dist):.3f} p90 {np.percentile(dist, 90):.3f}")
print(f"control_untransformed_m median {np.median(raw):.3f}")
print("mesh_median_m", " ".join(f"{v:.2f}" for v in np.median(mesh, axis=0)))
print("sfm_median_m", " ".join(f"{v:.2f}" for v in np.median(pts, axis=0)))
```

```python j30b-verdict-py
import sys
from pathlib import Path

log = Path(sys.argv[1])
kv = {p[0]: p[1:] for p in (ln.split() for ln in log.read_text(encoding="utf-8").splitlines()) if p}
res = dict(zip(kv["residual_m"][0::2], map(float, kv["residual_m"][1::2]), strict=True))
m2s = dict(zip(kv["mesh_to_sfm_m"][0::2], map(float, kv["mesh_to_sfm_m"][1::2]), strict=True))
scale = float(kv["scale"][0])
ctl = float(kv["control_untransformed_m"][1])
pairs = [int(kv[k][0]) for k in ("oc_samples", "colmap_registered", "common")]
checks = [
    ("pairs", pairs == [76, 76, 76], " ".join(map(str, pairs)) + " == 76 76 76"),
    ("reflection_guard", kv["reflection_guard"][0] == "0", kv["reflection_guard"][0] + " == 0"),
    ("scale", 0.9 <= scale <= 1.1, f"0.9 <= {scale:.4f} <= 1.1"),
    ("residual_median_m", res["median"] <= 0.5, f"{res['median']:.3f} <= 0.5"),
    ("residual_p90_m", res["p90"] <= 1.0, f"{res['p90']:.3f} <= 1.0"),
    ("residual_max_m", res["max"] <= 3.0, f"{res['max']:.3f} <= 3.0"),
    ("obj_vertices", kv["obj_vertices"][0] == "125678", kv["obj_vertices"][0] + " == 125678"),
    ("mesh_to_sfm_median_m", m2s["median"] <= 3.0, f"{m2s['median']:.3f} <= 3.0"),
    ("mesh_to_sfm_p90_m", m2s["p90"] <= 12.0, f"{m2s['p90']:.3f} <= 12.0"),
    ("control_untransformed_median_m", ctl >= 30.0, f"{ctl:.3f} >= 30.0"),
]
for name, ok, text in checks:
    print("PASS" if ok else "FAIL", name, text)
passed = sum(ok for _, ok, _ in checks)
print("verdict", "PASS" if passed == len(checks) else "FAIL", f"{passed}/{len(checks)}")
sys.exit(0 if passed == len(checks) else 1)
```

```python j30b-neg-py
import json
import sys
from pathlib import Path

src, out, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
data = json.loads(src.read_text(encoding="utf-8"))
names = sorted(s["image"] for s in data["samples"])
swap = dict(zip(names, reversed(names), strict=True))
changed = 0
for s in data["samples"]:
    if mode == "reverse":
        changed += swap[s["image"]] != s["image"]
        s["image"] = swap[s["image"]]
    elif mode == "mirror":
        s["translation"][0] = -s["translation"][0]
        changed += 1
    else:
        sys.exit(f"unknown mode {mode}")
out.write_text(json.dumps(data), encoding="utf-8")
print("mode", mode)
print("samples", len(data["samples"]))
print("changed", changed)
```

```sh j30b-negcheck-sh
#!/bin/sh
# J-30b: FAIL lines of the three negative cases (usage: sh j30b_negcheck.sh <E>)
E=$1
for c in unaligned reverse mirror; do
  printf '%s rc %s\n' "$c" "$(cat "$E/verdict-$c.rc")"
  grep '^FAIL ' "$E/verdict-$c.log" | awk -v c="$c" '{print c, "FAIL", $2}'
  printf '%s last %s\n' "$c" "$(tail -n 1 "$E/verdict-$c.log")"
done
```

```python j30b-render-py
import sys
from pathlib import Path

e, day = Path(sys.argv[1]), sys.argv[2]


def kv(name):
    return {
        p[0]: p[1:] for p in (ln.split() for ln in (e / name).read_text(encoding="utf-8").splitlines()) if p
    }


ck, src = kv("check.log"), kv("source.log")
model = {
    "j30a": "J-30a 실행의 정합 모델(위 J-30a 메모와 같은 실행)",
    "rerun": "J-30a와 같은 명령으로 다시 만든 정합 모델"
    "(J-30a 실행 폴더의 파일이 다 남아 있지 않아 다시 만듦, 축척은 실행마다 다름)",
}[src["source"][0]]
r, m = ck["residual_m"], ck["mesh_to_sfm_m"]
res = f"중앙값 {r[1]} m · p90 {r[3]} m · 최대 {r[5]} m"
note = (
    f"- {day} 메모(J-30b, 공개 Tyrol 드론 76장 CC BY 4.0, 1회 실행, 좌표 일관성 확인이지 품질 판정 아님): "
    "Object Capture `tyrol-full`(detail full)의 `poses.json` `translation`(카메라 중심)과 "
    f"{model}의 카메라 중심을 이미지 이름으로 짝지어 유사변환(Umeyama, 반사 없음)을 구했다. "
    f"공통 {ck['common'][0]}/76, 축척 {ck['scale'][0]}, 카메라 중심 잔차 {res}. "
    f"그 변환으로 옮긴 OBJ 정점 {ck['obj_vertices'][0]}개에서 가장 가까운 정합 SfM 점까지 "
    f"중앙값 {m[1]} m · p90 {m[3]} m(옮기기 전 정점과는 중앙값 {ck['control_untransformed_m'][1]} m). "
    "포즈의 회전은 쓰지 않고 카메라 중심만 썼다. 계산은 일회성이고 저장소 도구는 없다. "
    "메시 품질·splat과의 이음매는 판정하지 않았고(V-05), zone 원점으로 옮기기는 하지 않았다. 근거: J-30b PR."
)
row = (
    "| 6 | objcap 메시 → zone-local 변환 | 저장소 도구 없음(`reproject`는 EPSG만) | "
    "유사변환 단계 설계(WP-21 후속) | "
    f"{day}(J-30b, 공개 Tyrol 76장, 1회, 품질 판정 아님): `poses.json` 카메라 중심 → EXIF GPS ENU 정합 "
    f"COLMAP 카메라 중심 유사변환, 공통 {ck['common'][0]}/76, 축척 {ck['scale'][0]}, 잔차 중앙값 {r[1]} m, "
    f"옮긴 OBJ 정점 → 정합 SfM 점 중앙값 {m[1]} m. 일회성 계산(저장소 도구 없음), "
    "zone 원점으로 옮기기는 남음. "
    'M3 "정합" 메모. 근거: J-30b PR. |'
)
print(note)
print(row)
```

```python j30b-apply-py
import re
import sys
from pathlib import Path

doc, lines_file = Path(sys.argv[1]), Path(sys.argv[2])
note, row = lines_file.read_text(encoding="utf-8").splitlines()
memo = re.compile(r"^- \d{4}-\d{2}-\d{2} 메모\(J-30a, .* 근거: PR #\d+\.$")
old_row = (
    "| 6 | objcap 메시 → zone-local 변환 | 저장소 도구 없음(`reproject`는 EPSG만) | "
    "유사변환 단계 설계(WP-21 후속) | |"
)
src = doc.read_text(encoding="utf-8").split("\n")
hits = [i for i, ln in enumerate(src) if memo.match(ln)]
done = sum(1 for ln in src if "메모(J-30b, " in ln)
print("j30a_memo", len(hits))
print("j30b_memo", done)
print("old_row", src.count(old_row))
if len(hits) != 1 or done != 0 or src.count(old_row) != 1:
    sys.exit(1)
src.insert(hits[0] + 1, note)
src[src.index(old_row)] = row
doc.write_text("\n".join(src), encoding="utf-8")
print("applied")
```

```awk j30b-timeout-awk
# J-30b: rule 5 audit of commands.txt (usage: awk -f j30b_timeout.awk commands.txt)
# stdout: line number TAB wrapped|not-wrapped (TAB command for not-wrapped), then two count lines.
/^#/ { next }
/timeout-audit\.log/ { next }
/git (-C "[$]W" )?(fetch|push)|gh [a-z]|pytest|curl |until / {
  if (index($0, "/usr/bin/timeout ") > 0) { w++; print NR "\twrapped" }
  else { u++; print NR "\tnot-wrapped\t" $0 }
}
END { print "wrapped_lines " w + 0; print "not_wrapped_lines " u + 0 }
```

```sh j30b-bodycheck-sh
#!/bin/sh
# J-30b: quotes and numbers check of the PR body draft (usage: sh j30b_bodycheck.sh <E>)
E=$1
CK=checks.log
if [ -e "$E/checks-2.log" ]; then CK=checks-2.log; fi
printf '%s\n' source.log input-sha.log check.log verdict.log check-unaligned.log verdict-unaligned.log \
  neg-reverse.log check-reverse.log verdict-reverse.log neg-mirror.log check-mirror.log verdict-mirror.log \
  negcheck.diff input-sha.diff input-sha-after.diff numstat.log gate.log "$CK" > "$E/body-logs.log"
if grep -q -x 'source rerun' "$E/source.log"; then
  printf '%s\n' sfm/ref.log sfm/analyzer.log sfm/aligner.log sfm/align-check.log >> "$E/body-logs.log"
else
  printf '%s\n' j30a-recheck.diff sfm-points.diff >> "$E/body-logs.log"
fi
awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' \
  | grep -oE '`[^`]+`' | sed 's/^`//;s/`$//' | sort -u > "$E/body-quotes.txt"
cut -f1 "$E/quotes.tsv" | sort -u > "$E/tsv-quotes.txt"
comm -23 "$E/body-quotes.txt" "$E/tsv-quotes.txt" > "$E/quotes-missing.log"
while IFS="$(printf '\t')" read -r q f; do
  if [ "$f" = "라벨" ]; then
    n="라벨"
  elif grep -q -x -F -- "$f" "$E/body-logs.log"; then
    n=$(grep -F -c -- "$q" "$E/$f")
  else
    n="목록밖"
  fi
  printf '%s\t%s\t%s\n' "$n" "$f" "$q"
done < "$E/quotes.tsv" > "$E/quotes-check.log"
awk '/^## 결과$/{f=1;next} /^## /{f=0} f' "$E/pr-body.md" | awk '/^```/{c=!c;next} !c' \
  | grep -oE '[0-9]{2,}' | sort -u > "$E/body-numbers.txt"
while read -r x; do
  n=0
  while read -r f; do
    k=$(grep -c -- "$x" "$E/$f")
    n=$((n + k))
  done < "$E/body-logs.log"
  printf '%s\t%s\n' "$n" "$x"
done < "$E/body-numbers.txt" > "$E/numbers-check.log"
printf 'quotes_missing %s\n' "$(wc -l < "$E/quotes-missing.log" | tr -d ' ')"
printf 'quotes_zero %s\n' "$(cut -f1 "$E/quotes-check.log" | grep -c -x -E '0|목록밖')"
printf 'numbers_zero %s\n' "$(cut -f1 "$E/numbers-check.log" | grep -c -x '0')"
```

```text j30b-expected-pre
j30a_memo 1
j30a_marker 0
j30b_memo 0
row6_old 1
```

```text j30b-expected-sha
2bbb965773d307e365f1752226e4c68950e72135afaf2fcbaf119607a01525f4
bae2c322399e25810b078973e972583bcc808fce790e7a950c90652503e3497e
```

```text j30b-expected-neg
unaligned rc 1
unaligned FAIL scale
unaligned last verdict FAIL 9/10
reverse rc 1
reverse FAIL scale
reverse FAIL residual_median_m
reverse FAIL residual_p90_m
reverse FAIL residual_max_m
reverse FAIL mesh_to_sfm_median_m
reverse FAIL mesh_to_sfm_p90_m
reverse last verdict FAIL 4/10
mirror rc 1
mirror FAIL reflection_guard
mirror FAIL residual_median_m
mirror FAIL residual_p90_m
mirror FAIL residual_max_m
mirror FAIL mesh_to_sfm_median_m
mirror FAIL mesh_to_sfm_p90_m
mirror last verdict FAIL 4/10
```

```text j30b-fence-lines
7 j30b_pre.sh
24 j30b_source.sh
64 j30b_check.py
27 j30b_verdict.py
22 j30b_neg.py
8 j30b_negcheck.sh
41 j30b_render.py
23 j30b_apply.py
9 j30b_timeout.awk
40 j30b_bodycheck.sh
4 expected-pre.txt
2 expected-sha.txt
19 expected-neg.txt
37 ph.awk
```

- **명령 공통**: 셸 변수는 Bash 호출 사이에 남지 않는다. 그래서 **모든 명령은 `W="$HOME/projects/golmok-jaehwan"; E="$TMPDIR/jaehwan/J-30b"; J="$TMPDIR/jaehwan/J-30a"; P="$HOME/golmok_data/recon-smoke/objcap/tyrol-full/poses.json"; O="$HOME/golmok_data/recon-smoke/objcap/tyrol-full/obj/baked_mesh_32dae850.obj"; I="$HOME/golmok_data/recon-smoke/objcap/tyrol/images"; PY="$W/tools/.venv/bin/python"; . "$HOME/golmok-tools/env.sh";`로 시작하고**(마지막 것은 `colmap`을 PATH에 넣는다 — 할 일 2에서만 쓰지만 앞머리는 같게 둔다), 그 뒤는 `cd "$E" &&`·`cd "$E/sfm" &&`·`cd "$W" &&`·`cd "$W/tools" &&`·`git -C "$W"`·`"$E/…"` 절대 경로로 시작한다. 할 일 3 이후에는 정합 모델 폴더를 `M=$(sed -n 's/^model //p' "$E/source.log"); U=$(sed -n 's/^unaligned //p' "$E/source.log");`로 앞머리 뒤에 다시 정의한다. 아래 명령에는 이 앞머리를 적지 않았다. 돌린 명령은 상시 규칙 "PR 본문 공통" 머리의 **명령 기록**대로 돌리기 **전에** 한 줄씩 `"$E/commands.txt"`에 더한다(규칙 19·21). **timeout(규칙 5)**: 이 절의 네트워크·대기 명령(`git fetch`·`git push`·모든 `gh`·`pytest`·`until` 루프·파이썬 확인 스크립트·COLMAP)은 모두 `/usr/bin/timeout`을 단 채로 적혀 있고 시간은 고정이다. 상시 규칙 "PR 본문 공통" 6의 `gh pr edit`·`gh pr view` 두 명령만 그 소절에 적힌 그대로(timeout 없이) 쓴다. 긴 명령(할 일 2의 `feature_extractor`·`exhaustive_matcher`·`mapper`, 할 일 6의 게이트 두 번·등록 대기·`gh pr checks --watch`)은 **항상** 하네스의 백그라운드 실행으로 돌리고, 그 명령이 쓰는 `.rc` 파일(`gh pr checks --watch`는 `checks-watch.log`의 `exit=` 줄)이 생길 때까지 기다린다(명령은 바꾸지 않는다). 그 밖의 명령은 앞쪽(foreground)으로 돌린다. 각 단계의 "기대"와 다르면 **멈춤 조건**을 본다.
  - **펜스 추출**: 할 일 1의 `while read` 명령이 펜스마다 `awk`로 뽑는다(백틱 세 개를 `sprintf("%c%c%c", 96, 96, 96)`로 만들어 명령 글자에 백틱이 없다). 손으로 옮기지 않는다. 뽑은 펜스 스크립트는 할 일 1의 `fence-lines.diff`가 `exit=0`이고 `expected-fence-lines.txt`가 `14`줄일 때만 이 절에 적힌 명령 그대로 돌린다 — 상시 규칙 소절 11의 같은 호출 확인 꼴을 덧붙이지 않는다(열네 개의 줄 수를 할 일 1에서 한 번에 확인했다). 점검표 규칙 20 줄의 증거는 `fence-lines.diff`다.
  - **GUI·GPU 잠금 확인**(잡지 않는다 — UE·GPU를 쓰지 않는다): `L="$TMPDIR/claude/gui-foreground.lock"; if [ -e "$L" ]; then cat "$L"; else echo "no lock"; fi > "$E/lock-check-a.log"; date -u +%FT%TZ >> "$E/lock-check-a.log"` — 기대 첫 줄 `no lock`. 다른 줄이 있으면(영록이 성능을 재는 중일 수 있다) **지우지 않고** 그 줄을 영록에게 보내고 기다린다. 할 일 2(다시 만드는 경로)에서는 이 명령을 돌린다: `L="$TMPDIR/claude/gui-foreground.lock"; if [ -e "$L" ]; then cat "$L"; else echo "no lock"; fi > "$E/lock-check-b.log"; date -u +%FT%TZ >> "$E/lock-check-b.log"` — 기대 첫 줄 `no lock`(다르면 위와 같이 지우지 않고 영록에게 보내고 기다린다).
- **할 일**:
  1. **준비**: `mkdir -p "$E" && git -C "$W" status --porcelain --untracked-files=no | wc -l | tr -d ' ' > "$E/status-before-tracked.log"; git -C "$W" status --porcelain > "$E/status-before.log"` — 기대 `status-before-tracked.log` `0`(`status-before.log`의 내용은 기록만 — 다른 과제가 남긴 추적 안 된 파일이 있을 수 있다). `/usr/bin/timeout 120 git -C "$W" fetch origin > "$E/fetch.log" 2>&1; echo $? > "$E/fetch.rc"` — 기대 `0`. `git -C "$W" switch -c local/jaehwan-j30b-objcap-enu origin/main > "$E/switch.log" 2>&1; echo $? > "$E/switch.rc"` — 기대 `0`. 과제 절(상시 규칙 "PR 본문 공통" 1, 규칙 14·17 c): `git -C "$W" show origin/main:docs/plan/jaehwan-tasks.md > "$E/tasks-main.md"; git -C "$W" rev-parse origin/main > "$E/main-rev.log"; { awk '/^#### J-30b /{f=1} /^## 재환에게 맞지 않는 것/{f=0} f' "$E/tasks-main.md"; awk '/^### PR 본문 공통\(모든 과제\)$/{f=1} /^## 리뷰·병합 절차$/{f=0} f' "$E/tasks-main.md"; } > "$E/task.txt"` — 기대: `head -1 "$E/task.txt"`가 `#### J-30b `로 시작, `grep -c '^- \*\*dry-run 범위(Opus 2026-11-28, J-30b)\*\*' "$E/task.txt"` `1`, `grep -c -x '### PR 본문 공통(모든 과제)' "$E/task.txt"` `1`. 펜스 추출: `printf '%s\n' "j30b-pre-sh j30b_pre.sh" "j30b-source-sh j30b_source.sh" "j30b-check-py j30b_check.py" "j30b-verdict-py j30b_verdict.py" "j30b-neg-py j30b_neg.py" "j30b-negcheck-sh j30b_negcheck.sh" "j30b-render-py j30b_render.py" "j30b-apply-py j30b_apply.py" "j30b-timeout-awk j30b_timeout.awk" "j30b-bodycheck-sh j30b_bodycheck.sh" "j30b-expected-pre expected-pre.txt" "j30b-expected-sha expected-sha.txt" "j30b-expected-neg expected-neg.txt" "j30b-fence-lines expected-fence-lines.txt" "common-ph-awk ph.awk" | while read -r n f; do awk -v n="$n" 'BEGIN {b = sprintf("%c%c%c", 96, 96, 96)} x && $0 == b {x = 0} x {print} !x && index($0, b) == 1 && $0 ~ (" " n "$") {x = 1}' "$E/task.txt" > "$E/$f"; done; cd "$E" && wc -l j30b_pre.sh j30b_source.sh j30b_check.py j30b_verdict.py j30b_neg.py j30b_negcheck.sh j30b_render.py j30b_apply.py j30b_timeout.awk j30b_bodycheck.sh expected-pre.txt expected-sha.txt expected-neg.txt ph.awk | sed '$d' | awk '{print $1, $2}' | diff "$E/expected-fence-lines.txt" - > "$E/fence-lines.diff"; echo "exit=$?" >> "$E/fence-lines.diff"` — 기대 `fence-lines.diff` `exit=0` 한 줄(`expected-fence-lines.txt`가 비었으면 이 비교는 빈 검사다 — `wc -l < "$E/expected-fence-lines.txt" | tr -d ' '` `14`도 본다, 규칙 15). 순서(설계 10): `git -C "$W" show origin/main:docs/runbooks/mac-recon.md > "$E/mac-recon-main.md"; sh "$E/j30b_pre.sh" "$E/mac-recon-main.md" > "$E/pre.log" 2>&1; diff "$E/expected-pre.txt" "$E/pre.log" > "$E/pre.diff"; echo "exit=$?" >> "$E/pre.diff"` — 기대 `exit=0` 한 줄. 겹침: `cd "$W" && /usr/bin/timeout 120 gh pr list --state open --json number,headRefName,files --jq '.[]|select(any(.files[]; .path=="docs/runbooks/mac-recon.md"))|"\(.number) \(.headRefName)"' > "$E/overlap.log" 2>&1; echo $? > "$E/overlap.rc"` — 기대 rc `0`, `overlap.log` 빈 파일. 잠금 확인(`a`). 입력: `shasum -a 256 "$P" "$O" | cut -c1-64 > "$E/input-sha.log"; diff "$E/expected-sha.txt" "$E/input-sha.log" > "$E/input-sha.diff"; echo "exit=$?" >> "$E/input-sha.diff"` — 기대 `exit=0` 한 줄. 정합 모델(설계 3): `sh "$E/j30b_source.sh" "$J" "$E" > "$E/source.log" 2>&1; echo $? > "$E/source.rc"` — 기대 rc `0`, `grep -c -x -E 'source (j30a|rerun)' "$E/source.log"` `1`. `source j30a`이면 같은 실행 확인 ①: `cd "$E" && /usr/bin/timeout 300 "$PY" "$J/check_align.py" "$J/ref_gps.txt" "$J/aligned_txt" "$J/aligned/sim3.txt" > "$E/j30a-recheck.log" 2>&1; echo $? > "$E/j30a-recheck.rc"; diff "$J/align-check.log" "$E/j30a-recheck.log" > "$E/j30a-recheck.diff"; echo "exit=$?" >> "$E/j30a-recheck.diff"` — 기대 rc `0`, `j30a-recheck.diff` `exit=0` 한 줄. 그다음 할 일 2를 건너뛰고 할 일 3으로 간다. `source rerun`이면 할 일 2.
  2. **(`source rerun`일 때만) J-30a 할 일 2~4를 `$E/sfm`에 다시**: 잠금 확인(`b`). J-30a 펜스 셋: `mkdir -p "$E/sfm" && printf '%s\n' "j30a-make-ref make_ref.py" "j30a-check-align check_align.py" "j30a-ref-expected expected-ref.txt" | while read -r n f; do awk -v n="$n" 'BEGIN {b = sprintf("%c%c%c", 96, 96, 96)} x && $0 == b {x = 0} x {print} !x && index($0, b) == 1 && $0 ~ (" " n "$") {x = 1}' "$E/tasks-main.md" > "$E/sfm/$f"; done; cd "$E/sfm" && wc -l make_ref.py check_align.py expected-ref.txt > "$E/sfm/extract-wc.log"` — 기대(앞 숫자, 순서대로) `19`·`75`·`4`, 끝 줄 `98 total`. 입력: `ls "$I" | wc -l | tr -d ' ' > "$E/sfm/input-count.log"; cd "$I" && shasum -a 256 *.JPG | shasum -a 256 | cut -c1-64 > "$E/sfm/input-hash-before.log"` — 기대 `76`, `c28c1998b732270ccb1bc6e93267779fbb8f30bdd449c6059ef241317c8aebb3`(이미지 폴더의 `cd`는 읽기만 하는 `shasum`에만 쓴다). 참조: `cd "$E/sfm" && /usr/bin/timeout 300 "$PY" "$E/sfm/make_ref.py" "$I" "$E/sfm/ref_gps.txt" > "$E/sfm/ref.log" 2>&1; echo $? > "$E/sfm/ref.rc"; diff "$E/sfm/expected-ref.txt" "$E/sfm/ref.log" > "$E/sfm/ref.diff"; echo "exit=$?" >> "$E/sfm/ref.diff"; shasum -a 256 "$E/sfm/ref_gps.txt" | cut -c1-64 > "$E/sfm/ref-sha.log"` — 기대 rc `0`, `ref.diff` `exit=0` 한 줄, `ref-sha.log` `989373f7b3c7e2d6befb8b5582a3262c433f69dee2512bf3799dd82d00a9ddf6`. 특징(백그라운드): `cd "$E/sfm" && /usr/bin/timeout 1800 /usr/bin/time -l colmap feature_extractor --database_path "$E/sfm/database.db" --image_path "$I" --ImageReader.camera_model OPENCV --ImageReader.single_camera 1 --FeatureExtraction.use_gpu 0 --FeatureExtraction.max_image_size 3200 > "$E/sfm/fe.log" 2>&1; echo $? > "$E/sfm/fe.rc"` — 기대 rc `0`, `grep -c 'Processed file \[' "$E/sfm/fe.log"` `76`. 매칭(백그라운드): `cd "$E/sfm" && /usr/bin/timeout 900 /usr/bin/time -l colmap exhaustive_matcher --database_path "$E/sfm/database.db" --FeatureMatching.use_gpu 0 > "$E/sfm/match.log" 2>&1; echo $? > "$E/sfm/match.rc"` — 기대 rc `0`. 매핑(백그라운드): `mkdir -p "$E/sfm/sparse" && cd "$E/sfm" && /usr/bin/timeout 1800 /usr/bin/time -l colmap mapper --database_path "$E/sfm/database.db" --image_path "$I" --output_path "$E/sfm/sparse" > "$E/sfm/mapper.log" 2>&1; echo $? > "$E/sfm/mapper.rc"` — 기대 rc `0`, `ls "$E/sfm/sparse"` 한 줄 `0`. 분석: `cd "$E/sfm" && /usr/bin/timeout 300 colmap model_analyzer --path "$E/sfm/sparse/0" > "$E/sfm/analyzer.log" 2>&1; echo $? > "$E/sfm/analyzer.rc"` — 기대 rc `0`, `grep -c 'Registered images: 76$' "$E/sfm/analyzer.log"` `1`. 정합: `mkdir -p "$E/sfm/aligned" && cd "$E/sfm" && /usr/bin/timeout 300 colmap model_aligner --input_path "$E/sfm/sparse/0" --output_path "$E/sfm/aligned" --ref_images_path "$E/sfm/ref_gps.txt" --ref_is_gps 1 --alignment_type enu --alignment_max_error 3 --transform_path "$E/sfm/aligned/sim3.txt" > "$E/sfm/aligner.log" 2>&1; echo $? > "$E/sfm/aligner.rc"` — 기대 rc `0`, 네 개가 각각 `1`: `grep -c -F 'Using the first GPS coordinate as the ENU origin' "$E/sfm/aligner.log"`, `grep -c -F '=> Using 76 reference images' "$E/sfm/aligner.log"`, `grep -c -F '=> Alignment error:' "$E/sfm/aligner.log"`, `grep -c -F '=> Alignment succeeded' "$E/sfm/aligner.log"`. TXT로: `mkdir -p "$E/sfm/aligned_txt" "$E/sfm/sparse_txt" && cd "$E/sfm" && /usr/bin/timeout 300 colmap model_converter --input_path "$E/sfm/aligned" --output_path "$E/sfm/aligned_txt" --output_type TXT > "$E/sfm/conv-aligned.log" 2>&1; echo $? > "$E/sfm/conv-aligned.rc"; cd "$E/sfm" && /usr/bin/timeout 300 colmap model_converter --input_path "$E/sfm/sparse/0" --output_path "$E/sfm/sparse_txt" --output_type TXT > "$E/sfm/conv-sparse.log" 2>&1; echo $? > "$E/sfm/conv-sparse.rc"` — 기대 둘 다 `0`. 확인: `cd "$E/sfm" && /usr/bin/timeout 300 "$PY" "$E/sfm/check_align.py" "$E/sfm/ref_gps.txt" "$E/sfm/aligned_txt" "$E/sfm/aligned/sim3.txt" > "$E/sfm/align-check.log" 2>&1; echo $? > "$E/sfm/align-check.rc"; awk '$1 == "residual_m" {print ($3 <= 3.0 && $5 <= 5.0 && $7 <= 10.0) ? "rerun-align ok" : "rerun-align bad"}' "$E/sfm/align-check.log" > "$E/sfm/align-gate.log"` — 기대 rc `0`, `wc -l < "$E/sfm/align-check.log" | tr -d ' '` `11`, 첫 세 줄 `ref_images 76`·`registered 76`·`common 76`, `align-gate.log` 한 줄 `rerun-align ok`. 입력이 그대로인지: `cd "$I" && shasum -a 256 *.JPG | shasum -a 256 | cut -c1-64 | diff "$E/sfm/input-hash-before.log" - > "$E/sfm/input-hash.diff"; echo "exit=$?" >> "$E/sfm/input-hash.diff"` — 기대 `exit=0` 한 줄.
  3. **확인**: `cd "$E" && /usr/bin/timeout 300 "$PY" -I "$E/j30b_check.py" "$P" "$M" "$O" > "$E/check.log" 2>&1; echo $? > "$E/check.rc"` — 기대 rc `0`, `wc -l < "$E/check.log" | tr -d ' '` `13`, 첫 세 줄 `oc_samples 76`·`colmap_registered 76`·`common 76`. `source j30a`이면 같은 실행 확인 ②: `grep '^sfm_points ' "$J/splat-check.log" > "$E/sfm-points-j30a.log"; test -s "$E/sfm-points-j30a.log" && grep '^sfm_points ' "$E/check.log" | diff "$E/sfm-points-j30a.log" - > "$E/sfm-points.diff"; echo "exit=$?" >> "$E/sfm-points.diff"` — 기대 `exit=0` 한 줄(`sfm-points-j30a.log`가 비면 `test -s`가 막아 `exit=1`이 남는다 — 규칙 15·19 d).
  4. **판정·비공허**: `cd "$E" && /usr/bin/timeout 120 "$PY" -I "$E/j30b_verdict.py" "$E/check.log" > "$E/verdict.log" 2>&1; echo $? > "$E/verdict.rc"` — 기대 rc `0`, `grep -c '^PASS ' "$E/verdict.log"` `10`, `grep -c '^FAIL ' "$E/verdict.log"` `0`, 끝 줄 `verdict PASS 10/10`. 틀린 셋(설계 6): `mkdir -p "$E/neg" && cd "$E" && /usr/bin/timeout 120 "$PY" -I "$E/j30b_neg.py" "$P" "$E/neg/poses-reverse.json" reverse > "$E/neg-reverse.log" 2>&1; echo $? > "$E/neg-reverse.rc"; /usr/bin/timeout 120 "$PY" -I "$E/j30b_neg.py" "$P" "$E/neg/poses-mirror.json" mirror > "$E/neg-mirror.log" 2>&1; echo $? > "$E/neg-mirror.rc"` — 기대 rc 둘 다 `0`, `neg-reverse.log` 세 줄 `mode reverse`·`samples 76`·`changed 76`, `neg-mirror.log` 세 줄 `mode mirror`·`samples 76`·`changed 76`. 셋을 같은 스크립트로: `cd "$E" && /usr/bin/timeout 300 "$PY" -I "$E/j30b_check.py" "$P" "$U" "$O" > "$E/check-unaligned.log" 2>&1; echo $? > "$E/check-unaligned.rc"; /usr/bin/timeout 300 "$PY" -I "$E/j30b_check.py" "$E/neg/poses-reverse.json" "$M" "$O" > "$E/check-reverse.log" 2>&1; echo $? > "$E/check-reverse.rc"; /usr/bin/timeout 300 "$PY" -I "$E/j30b_check.py" "$E/neg/poses-mirror.json" "$M" "$O" > "$E/check-mirror.log" 2>&1; echo $? > "$E/check-mirror.rc"` — 기대 rc 셋 다 `0`, 각 13줄. 판정: `cd "$E" && for c in unaligned reverse mirror; do /usr/bin/timeout 120 "$PY" -I "$E/j30b_verdict.py" "$E/check-$c.log" > "$E/verdict-$c.log" 2>&1; echo $? > "$E/verdict-$c.rc"; done; sh "$E/j30b_negcheck.sh" "$E" > "$E/negcheck.log" 2>&1; diff "$E/expected-neg.txt" "$E/negcheck.log" > "$E/negcheck.diff"; echo "exit=$?" >> "$E/negcheck.diff"` — 기대 `negcheck.diff` `exit=0` 한 줄. 입력이 그대로인지: `shasum -a 256 "$P" "$O" | cut -c1-64 | diff "$E/expected-sha.txt" - > "$E/input-sha-after.diff"; echo "exit=$?" >> "$E/input-sha-after.diff"` — 기대 `exit=0` 한 줄. 저장소가 그대로인지: `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-run.diff"; echo "exit=$?" >> "$E/status-run.diff"` — 기대 `exit=0` 한 줄.
  5. **런북 두 줄**: `cd "$E" && /usr/bin/timeout 120 "$PY" -I "$E/j30b_render.py" "$E" "$(date +%F)" > "$E/runbook-lines.txt" 2> "$E/render.err"; echo $? > "$E/render.rc"` — 기대 rc `0`, `wc -l < "$E/runbook-lines.txt" | tr -d ' '` `2`, `grep -c '<' "$E/runbook-lines.txt"` `0`. `cd "$W" && /usr/bin/timeout 120 "$PY" -I "$E/j30b_apply.py" docs/runbooks/mac-recon.md "$E/runbook-lines.txt" > "$E/apply.log" 2>&1; echo $? > "$E/apply.rc"` — 기대 rc `0`, `apply.log` 네 줄 `j30a_memo 1`·`j30b_memo 0`·`old_row 1`·`applied`. `apply.py`를 두 번 돌리지 않는다(두 번째는 `j30b_memo 1`로 rc 1 — 그게 정상이다). 확인: `cd "$W" && git diff --numstat -- docs/runbooks/mac-recon.md | tr '\t' ' ' > "$E/numstat.log"` — 기대 `2 1 docs/runbooks/mac-recon.md`. 더한 줄이 렌더 결과와 같은지: `cd "$W" && git diff -U0 -- docs/runbooks/mac-recon.md | grep -E '^\+[^+]' | sed 's/^+//' | diff "$E/runbook-lines.txt" - > "$E/added.diff"; echo "exit=$?" >> "$E/added.diff"` — 기대 `exit=0` 한 줄. 지운 줄은 #6 옛 행 하나: `cd "$W" && git diff -U0 -- docs/runbooks/mac-recon.md | grep -c -E '^-\| 6 \| objcap '` — 기대 `1`. 메모가 J-30a 메모 바로 뒤인지: `cd "$W" && grep -n -E '^- [0-9]{4}-[0-9]{2}-[0-9]{2} 메모\(J-30(a|b), ' docs/runbooks/mac-recon.md | cut -d: -f1 | awk 'NR == 1 {a = $1} NR == 2 {print ($1 == a + 1) ? "adjacent" : "apart"} END {print "memo_lines " NR}' > "$E/memo-order.log"` — 기대 두 줄 `adjacent`·`memo_lines 2`. 칸 자기 검사(상시 규칙 "PR 본문 공통" 7, 번호 `1`): `cd "$W" && git diff -U0 origin/main -- docs/runbooks/mac-recon.md | grep '^+[^+]' > "$E/cell-lines-1.txt"; wc -l < "$E/cell-lines-1.txt" | tr -d ' ' > "$E/cell-lines-1-count.log"; grep -n -E '\.log|영록|R[0-9]{3}' "$E/cell-lines-1.txt" > "$E/cell-grep-1.log"; wc -l < "$E/cell-grep-1.log" | tr -d ' ' > "$E/cell-grep-1-count.log"` — 기대 `cell-lines-1-count.log` `2`, `cell-grep-1-count.log` `0`(펜스가 만든 줄이라 0이 아니면 손으로 고치지 않고 멈춘다). 저장소: `git -C "$W" status --porcelain | grep -v -x -F ' M docs/runbooks/mac-recon.md' | diff "$E/status-before.log" - > "$E/status-apply.diff"; echo "exit=$?" >> "$E/status-apply.diff"` — 기대 `exit=0` 한 줄.
  6. **게이트·커밋·push·PR·커밋 2·CI**: 파이썬 게이트(규칙 13, 백그라운드): `cd "$W/tools" && . .venv/bin/activate && { /usr/bin/timeout 300 ruff check . && /usr/bin/timeout 300 ruff format --check . && /usr/bin/timeout 1800 pytest -q && /usr/bin/timeout 300 python scripts/check_repo.py; } > "$E/gate.log" 2>&1; echo $? > "$E/gate.rc"` — 기대 `0`(코드 변경은 없지만 `check_repo.py`가 런북 링크를 본다; rc 124 = 시간 초과, 다시 돌리지 않고 멈춤). `[ "$E/gate.log" -nt "$W/docs/runbooks/mac-recon.md" ]; echo "newer=$?" > "$E/mtime.log"` — 기대 `newer=0`. 커밋 1: `cd "$W" && git add docs/runbooks/mac-recon.md && git diff --cached --name-only > "$E/c1-files.log" && [ "$(cat "$E/c1-files.log")" = "docs/runbooks/mac-recon.md" ] && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-30b: mac-recon — Object Capture 메시를 EXIF GPS ENU 정합 좌표로(카메라 중심 Umeyama, 공개 Tyrol)" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c1-commit.log" 2>&1; echo $? > "$E/c1-commit.rc"; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-c1.log"` — 기대 `c1-files.log` 한 줄 `docs/runbooks/mac-recon.md`, `c1-commit.rc` `0`, `author-c1.log` `재환 <jaehwan.local@localhost>`(규칙 6·7·19 d). `/usr/bin/timeout 300 git -C "$W" push -u origin local/jaehwan-j30b-objcap-enu > "$E/push.log" 2>&1; echo "exit=$?" >> "$E/push.log"` — 기대 끝 줄 `exit=0`. `git -C "$W" diff --name-only origin/main...HEAD > "$E/branch-files.log"` — 기대 한 줄 `docs/runbooks/mac-recon.md`. `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-push.diff"; echo "exit=$?" >> "$E/status-push.diff"` — 기대 `exit=0` 한 줄. PR 열기(첫 본문은 상시 규칙 "PR 본문 공통" 2의 한 문장뿐 — 규칙 2): `printf '%s\n' 'CI 진행 중 — 결과는 아래에 추가' > "$E/pr-body-initial.md"; cd "$W" && /usr/bin/timeout 120 gh pr create --base main --head local/jaehwan-j30b-objcap-enu --title "J-30b: Object Capture 메시를 EXIF GPS ENU 정합 좌표로 — 카메라 중심 Umeyama, 수치 확인(공개 Tyrol)" --body-file "$E/pr-body-initial.md" > "$E/pr-create.log" 2>&1; echo $? > "$E/pr-create.rc"` — 기대 `0`. PR 번호: `cd "$W" && /usr/bin/timeout 120 gh pr view local/jaehwan-j30b-objcap-enu --json number --jq .number > "$E/pr-number.log" 2> "$E/pr-number.err"` — 기대 `grep -c -x '[0-9][0-9]*' "$E/pr-number.log"` `1`, `wc -l < "$E/pr-number.log" | tr -d ' '` `1`(stderr 안내 문구는 `pr-number.err`로 가고 판정하지 않는다). **커밋 2(PR 번호, 상시 규칙 "PR 본문 공통" 8)**: `N=$(cat "$E/pr-number.log"); sed "s/ 근거: J-30b PR\./ 근거: PR #$N./" "$E/runbook-lines.txt" > "$E/runbook-lines-final.txt"; cd "$W" && sed -i '' "s/ 근거: J-30b PR\./ 근거: PR #$N./" docs/runbooks/mac-recon.md; echo $? > "$E/runbook-pr.rc"` — 기대 `0`. 확인: `cd "$W" && git diff -U0 origin/main -- docs/runbooks/mac-recon.md | grep -E '^\+[^+]' | sed 's/^+//' | diff "$E/runbook-lines-final.txt" - > "$E/added-final.diff"; echo "exit=$?" >> "$E/added-final.diff"` — 기대 `exit=0` 한 줄. `cd "$W" && grep -c ' 근거: J-30b PR\.' docs/runbooks/mac-recon.md` — 기대 `0`. `cd "$W" && git diff --numstat origin/main -- docs/runbooks/mac-recon.md | tr '\t' ' '` — 기대 `2 1 docs/runbooks/mac-recon.md`. 칸 자기 검사(번호 `2`): `cd "$W" && git diff -U0 origin/main -- docs/runbooks/mac-recon.md | grep '^+[^+]' > "$E/cell-lines-2.txt"; wc -l < "$E/cell-lines-2.txt" | tr -d ' ' > "$E/cell-lines-2-count.log"; grep -n -E '\.log|영록|R[0-9]{3}' "$E/cell-lines-2.txt" > "$E/cell-grep-2.log"; wc -l < "$E/cell-grep-2.log" | tr -d ' ' > "$E/cell-grep-2-count.log"` — 기대 `cell-lines-2-count.log` `2`, `cell-grep-2-count.log` `0`. 게이트 다시(규칙 13, 백그라운드): `cd "$W/tools" && . .venv/bin/activate && { /usr/bin/timeout 300 ruff check . && /usr/bin/timeout 300 ruff format --check . && /usr/bin/timeout 1800 pytest -q && /usr/bin/timeout 300 python scripts/check_repo.py; } > "$E/gate-2.log" 2>&1; echo $? > "$E/gate-2.rc"` — 기대 `0`. `[ "$E/gate-2.log" -nt "$W/docs/runbooks/mac-recon.md" ]; echo "newer=$?" > "$E/mtime-2.log"` — 기대 `newer=0`. 커밋 2: `cd "$W" && git add docs/runbooks/mac-recon.md && git diff --cached --name-only > "$E/c2-files.log" && [ "$(cat "$E/c2-files.log")" = "docs/runbooks/mac-recon.md" ] && git -c user.name="재환" -c user.email="jaehwan.local@localhost" commit -m "J-30b: 기록 줄의 근거를 PR 번호로" -m "작성: 재환(로컬 LLM, qwen3.8-flash-next / LM Studio)" > "$E/c2-commit.log" 2>&1; echo $? > "$E/c2-commit.rc"; git -C "$W" log -1 --format='%an <%ae>' > "$E/author-c2.log"` — 기대 `c2-files.log` 한 줄 `docs/runbooks/mac-recon.md`, `c2-commit.rc` `0`, `author-c2.log` `재환 <jaehwan.local@localhost>`. `/usr/bin/timeout 300 git -C "$W" push > "$E/push-2.log" 2>&1; echo "exit=$?" >> "$E/push-2.log"` — 기대 끝 줄 `exit=0`. `git -C "$W" diff --name-only origin/main...HEAD > "$E/branch-files-2.log"` — 기대 한 줄 `docs/runbooks/mac-recon.md`. `git -C "$W" status --porcelain | diff "$E/status-before.log" - > "$E/status-final.diff"; echo "exit=$?" >> "$E/status-final.diff"` — 기대 `exit=0` 한 줄. CI 등록 대기(백그라운드, 커밋 2의 push 뒤 — 이 절의 대기 절차다, 상시 규칙 "CI 감시의 등록 전 경합"은 이 절이 따로 적었으므로 이 절을 따른다): `H=$(git -C "$W" rev-parse HEAD); cd "$W" && /usr/bin/timeout 600 sh -c 'until [ "$(gh run list --commit "$1" --json event --jq "[.[]|select(.event==\"push\" or .event==\"pull_request\")]|length")" -ge 2 ]; do sleep 30; done' sh "$H" > "$E/run-wait.log" 2>&1; echo $? > "$E/run-wait.rc"` — 기대 `0`(0이 아니면 다시 돌리지 않고 멈춘다). CI(백그라운드, `run-wait.rc` `0` 뒤): `cd "$W" && /usr/bin/timeout 1800 gh pr checks "$(cat "$E/pr-number.log")" --watch --interval 30 > "$E/checks-watch.log" 2>&1; echo "exit=$?" >> "$E/checks-watch.log"; /usr/bin/timeout 120 gh pr checks "$(cat "$E/pr-number.log")" > "$E/checks.log" 2>&1; echo $? > "$E/checks.rc"`. 결론은 `--watch`의 종료 코드가 아니라 표에서 읽는다: `awk -F'\t' 'NF' "$E/checks.log" | wc -l | tr -d ' ' > "$E/checks-rows.log"; awk -F'\t' 'NF && $2 != "pass"' "$E/checks.log" | wc -l | tr -d ' ' > "$E/checks-notpass.log"` — 기대 `checks.rc` `0`, `checks-rows.log` 1 이상, `checks-notpass.log` `0`. `checks-watch.log`에 `no checks reported`가 있으면 첫 로그들은 그대로 두고 watch·표 두 명령과 위 두 `awk`를 이름에 `-2`를 붙여(`checks-watch-2.log`·`checks-2.log`·`checks-2.rc`·`checks-rows-2.log`·`checks-notpass-2.log`) 한 번 더 돌린다. 이 경우 `## CI`·완료 기준 (h)·멈춤 조건의 `checks.log`·`checks.rc`·`checks-rows.log`·`checks-notpass.log`는 `-2` 파일로 읽는다(펜스 `j30b-bodycheck-sh`는 `checks-2.log`가 있으면 그것을 대상에 넣는다).
  7. **PR 본문**: PR 본문·자리표시 분류·칸 자기 검사·근거 표기는 상시 규칙 "PR 본문 공통(모든 과제)"을 따른다(이 절과 다르면 그 소절을 따른다). `## 결과`에는 관찰한 값만 둔다(로그 원문은 백틱 펜스 블록에): `source.log`·`input-sha.log`·`check.log`(13줄)·`verdict.log`(11줄) 원문, 틀린 셋의 `check-unaligned.log`·`check-reverse.log`·`check-mirror.log`·`verdict-unaligned.log`·`verdict-reverse.log`·`verdict-mirror.log` 원문, `negcheck.diff`, `source j30a`이면 `j30a-recheck.diff`·`sfm-points.diff`, `source rerun`이면 `sfm/align-check.log` 원문과 `sfm/aligner.log`의 `=> Alignment error:` 줄, 각 단계 rc(`## 결과`의 백틱 펜스 블록 하나에 `파일 이름 값` 줄로 — `.rc` 파일은 인용 검사 대상 목록에 없으므로 펜스 밖에서 백틱으로 인용하지 않는다), `numstat.log`. 과제 번호·규칙 번호·날짜는 이 절에 쓰지 않는다. 시간·메모리는 판정 근거가 아니므로 쓰지 않는다. `## 남은 [미확인]`에는 zone 원점 변환, 메시와 splat을 한 장면에서 보는 확인(V-05), 실촬영(C-02) 데이터에서 같은 방법이 통하는지, 메시 → SfM 거리가 카메라 잔차보다 큰 까닭(설계 5의 가설). `## 완료 기준 대조`는 아래 (a)~(i) 한 줄씩. 본문 초안은 `$E/pr-body.md`. 게시 전 검사(규칙 10 e·f): `## 결과` 절의 펜스 밖 백틱 문자열마다 그 문자열이 근거로 든 로그 **한 개**를 `"$E/quotes.tsv"`에 `문자열<탭>파일 이름`으로 적는다 — 파일 이름은 펜스 `j30b-bodycheck-sh`의 대상 목록(`body-logs.log`에 찍힌다)에 있는 것만 쓰고, 로그 인용이 아닌 파일 이름·명령은 파일 칸에 `라벨`. 대상 목록에는 `commands.txt`·`task.txt`·`tasks-main.md`·본문 초안·게시본·`runbook-lines*.txt`·검사 로그 자신이 들어 있지 않다(규칙 10 f, 고정). 검사: `cd "$E" && sh "$E/j30b_bodycheck.sh" "$E" > "$E/bodycheck.log" 2>&1; echo $? > "$E/bodycheck.rc"` — 기대 rc `0`, 세 줄 `quotes_missing 0`·`quotes_zero 0`·`numbers_zero 0`(0이 아닌 줄은 `quotes-missing.log`·`quotes-check.log`·`numbers-check.log`에서 그 항목을 찾아 본문을 고치거나 지운 뒤 같은 명령을 다시 돌린다 — 상시 규칙 "다시 돌린 로그는 번호 접미사"의 게시 전 검사 예외). 규칙 5 줄(규칙 5 R161 확장): 점검표를 쓰기 직전에 `grep -n -c 'timeout' "$E/commands.txt" > "$E/timeout-count.log"; awk -f "$E/j30b_timeout.awk" "$E/commands.txt" > "$E/timeout-audit.log"; echo $? > "$E/timeout-audit.rc"` — 기대 rc `0`, `timeout-audit.log` 끝 줄 `not_wrapped_lines 0`(이 절의 네트워크·대기 명령은 모두 감싸져 있다). 점검표의 규칙 5 줄은 `timeout-audit.log`의 `wrapped_lines`·`not_wrapped_lines` 두 수와, 그 뒤 게시 단계에서 `gh pr edit`·`gh pr view`(상시 규칙 소절 6)를 timeout 없이 쓴다는 사실을 적는다. 그다음 상시 규칙 "PR 본문 공통" 3(점검표 대조)·5(자리표시 분류)·6(조립·게시·다시 읽기)을 적힌 그대로 돌린다.
- **허용 파일**: `docs/runbooks/mac-recon.md`(설계 8의 두 줄만 — M3 "정합" 문단의 J-30a 메모 줄 바로 뒤에 한 줄 추가, §6 #6 행의 빈 칸 채움. 커밋 2는 두 줄 끝의 근거 표식만 바꾼다). 그 밖의 저장소 파일은 건드리지 않는다(`tools/`·`pyproject.toml`·CI·`check_repo.py`·WP-21·STATUS·DECISIONS 등 공유 문서 포함). 스크립트·로그·데이터는 `$E`에만. J-30a 폴더 `$J`와 입력 폴더는 읽기만 한다.
- **멈춤 조건(정하지 말고 영록에게 묻는다)**: `status-before-tracked.log`가 `0`이 아닐 때. `fetch.rc`·`switch.rc`가 0이 아닐 때. `task.txt`의 첫 줄·두 `grep -c`, `expected-fence-lines.txt` 줄 수, `fence-lines.diff`가 기대와 다를 때. `pre.diff`가 `exit=0`이 아닐 때(특히 `j30a_memo 0` = J-30a가 아직 병합되지 않았다, `j30b_memo 1` = 이미 했다 — 런북을 고치지 않는다). `overlap.rc`가 0이 아니거나 `overlap.log`가 비어 있지 않을 때. 잠금 확인이 `no lock`이 아닐 때. `input-sha.diff`·`input-sha-after.diff`가 `exit=0`이 아닐 때(입력이 바뀌었다). `source.rc`가 0이 아니거나 `source (j30a|rerun)` 줄이 1개가 아닐 때. `source j30a`인데 `j30a-recheck.rc`가 0이 아니거나 `j30a-recheck.diff`·`sfm-points.diff`가 `exit=0`이 아닐 때(J-30a 폴더의 파일이 서로 다른 실행이다 — 다시 만드는 경로로 바꾸지 않고, J-30a 폴더를 고치지 않고 묻는다). `source rerun`인데 할 일 2의 `extract-wc.log`·`input-count.log`·`input-hash-before.log`·`ref.rc`·`ref.diff`·`ref-sha.log`·`fe.rc`·`match.rc`·`mapper.rc`·`analyzer.rc`·`aligner.rc`·`conv-*.rc`·`align-check.rc`·`align-gate.log`·`input-hash.diff`나 `grep` 기대가 다를 때 — 특히 **rc 124(`timeout`) = CPU 실행이 정한 시간을 넘음**이면 같은 명령을 다시 돌리지 않는다(규칙 5), `sparse`에 `0` 말고 다른 폴더가 있거나 `Registered images: 76`이 아닐 때, `aligner.log`에 `unrecognised option`·`Alignment failed`·`Cannot align with insufficient reference locations` 중 하나가 있을 때. `check.rc`·`check-unaligned.rc`·`check-reverse.rc`·`check-mirror.rc`·`neg-reverse.rc`·`neg-mirror.rc`가 0이 아니거나, `check.log`·`check-unaligned.log`·`check-reverse.log`·`check-mirror.log`가 13줄이 아니거나, `neg-reverse.log`·`neg-mirror.log`가 할 일 4의 세 줄과 다를 때. `verdict.rc`가 0이 아니거나 `FAIL` 줄이 하나라도 있을 때 — 특히 `reflection_guard 1`·축척 범위 밖(**축을 뒤집거나 기준·스크립트를 고치지 않는다**, 값과 함께 묻는다). `negcheck.diff`가 `exit=0`이 아닐 때. `status-run.diff`·`status-apply.diff`가 `exit=0`이 아닐 때(저장소에 무엇이 생김 — 지우지 말고 `git -C "$W" status --porcelain` 원문과 함께 묻는다). `render.rc`·`apply.rc`·`runbook-pr.rc`가 0이 아니거나 `apply.log`·`numstat.log`·`added.diff`·`added-final.diff`·지운 줄 수·`memo-order.log`가 기대와 다를 때. `cell-lines-1-count.log`·`cell-lines-2-count.log`가 `2`가 아니거나 `cell-grep-1-count.log`·`cell-grep-2-count.log`가 `0`이 아닐 때(줄을 손으로 고치지 않는다, 렌더 스크립트도 고치지 않는다). `gate.rc`·`gate-2.rc`가 0이 아닐 때(rc 124 포함, 다른 파일을 고치거나 `ruff format`으로 바꾸지 않는다). `mtime.log`·`mtime-2.log`가 `newer=0`이 아닐 때. `c1-files.log`·`c2-files.log`가 `docs/runbooks/mac-recon.md` 한 줄이 아니거나(커밋하지 않는다) `c1-commit.rc`·`c2-commit.rc`가 0이 아니거나 `author-c1.log`·`author-c2.log`가 다를 때. `push.log`·`push-2.log`가 `exit=0`으로 끝나지 않을 때(rc 124 포함 — 다시 돌리지 않는다), `branch-files.log`·`branch-files-2.log`가 한 줄이 아니거나 `status-push.diff`·`status-final.diff`가 `exit=0`이 아닐 때. `pr-create.rc`가 0이 아니거나 `pr-number.log`가 숫자 한 줄이 아닐 때. `run-wait.rc`가 0이 아닐 때(124 = 10분 안에 두 실행이 등록되지 않았다 — 다시 돌리지 않는다). `checks.rc`가 0이 아니거나 `checks-rows.log`가 0이거나 `checks-notpass.log`가 0이 아닐 때(`-2`로 다시 돌린 경우 그 파일). `bodycheck.rc`가 0이 아니거나 두 번 고친 뒤에도 `bodycheck.log`가 세 줄 `0`이 아닐 때. `timeout-audit.rc`가 0이 아니거나 `not_wrapped_lines`가 0이 아닐 때(그 줄 번호와 함께 묻는다). 상시 규칙 "PR 본문 공통" 9의 공통 멈춤 조건. 그 밖에 이 절의 "기대"와 다른 값이 하나라도 나올 때. 이 과제는 GUI 잠금을 잡지 않는다(잠금 파일을 만들거나 지우지 않는다).
- **완료 기준**(각 줄은 충족 또는 미충족뿐이다 — `source`에 따라 갈리는 줄은 두 경우를 다 적었다):
  - (a) 준비: `status-before-tracked.log` `0`, `fetch.rc`·`switch.rc` `0`, `task.txt` 첫 줄 `#### J-30b `·dry-run 줄 `1`·공통 소절 머리 `1`, `expected-fence-lines.txt` 14줄, `fence-lines.diff` `exit=0`, `pre.diff` `exit=0`, `overlap.rc` `0`·`overlap.log` 빈 파일, `lock-check-a.log` 첫 줄 `no lock`, `input-sha.diff` `exit=0`.
  - (b) 정합 모델: `source.rc` `0`, `source (j30a|rerun)` 한 줄. `source j30a`이면 `j30a-recheck.rc` `0`·`j30a-recheck.diff` `exit=0`·`sfm-points.diff` `exit=0`. `source rerun`이면 할 일 2의 모든 기대(`lock-check-b.log` `no lock`, `extract-wc.log` `98 total`, rc 모두 `0`, `ref.diff` `exit=0`, `ref-sha.log` 위 값, `Registered images: 76` 1줄, `aligner.log` 네 줄 각 `1`, `align-check.log` 11줄, `align-gate.log` `rerun-align ok`, `input-hash.diff` `exit=0`).
  - (c) 확인: `check.rc` `0`, `check.log` 13줄, 첫 세 줄 `oc_samples 76`·`colmap_registered 76`·`common 76`.
  - (d) 판정: `verdict.rc` `0`, `PASS` 10줄·`FAIL` 0줄, 끝 줄 `verdict PASS 10/10`.
  - (e) 비공허: `neg-reverse.rc`·`neg-mirror.rc` `0`과 두 로그 각 세 줄(할 일 4), `check-unaligned.rc`·`check-reverse.rc`·`check-mirror.rc` `0`, `negcheck.diff` `exit=0`(펜스 `j30b-expected-neg` 19줄과 같다).
  - (f) 입력·저장소: `input-sha-after.diff` `exit=0`, `status-run.diff` `exit=0`.
  - (g) 런북: `render.rc`·`apply.rc` `0`, `runbook-lines.txt` 2줄·`<` 0, `apply.log` 네 줄, `numstat.log` `2 1 docs/runbooks/mac-recon.md`, `added.diff` `exit=0`, 지운 줄 `1`, `memo-order.log` `adjacent`·`memo_lines 2`, `cell-lines-1-count.log` `2`, `cell-grep-1-count.log` `0`, `status-apply.diff` `exit=0`.
  - (h) 게이트·커밋·CI: `gate.rc` `0`·`mtime.log` `newer=0`, `c1-files.log` 한 줄·`c1-commit.rc` `0`·`author-c1.log` `재환 <jaehwan.local@localhost>`, `push.log` 끝 줄 `exit=0`, `branch-files.log` 한 줄, `status-push.diff` `exit=0`, `pr-create.rc` `0`·`pr-number.log` 숫자 한 줄. 커밋 2: `runbook-pr.rc` `0`, `added-final.diff` `exit=0`, `근거: J-30b PR.` 0줄, `origin/main` 대비 numstat `2 1 docs/runbooks/mac-recon.md`, `cell-lines-2-count.log` `2`, `cell-grep-2-count.log` `0`, `gate-2.rc` `0`, `mtime-2.log` `newer=0`, `c2-files.log` 한 줄·`c2-commit.rc` `0`·`author-c2.log` 기대대로, `push-2.log` 끝 줄 `exit=0`, `branch-files-2.log` 한 줄, `status-final.diff` `exit=0`. CI: `run-wait.rc` `0`, `checks.rc` `0`, `checks-rows.log` 1 이상, `checks-notpass.log` `0`(`-2`로 다시 돌린 경우 그 파일), `checks.log` 원문이 `## CI`에 있다(규칙 2).
  - (i) PR 본문: 절 순서(상시 규칙 "PR 본문 공통" 2), "완료 기준 대조" 절과 점검표(그날 규칙 수만큼, 소절 3), `bodycheck.rc` `0`·`bodycheck.log` 세 줄 `0`, `timeout-audit.log` `not_wrapped_lines 0`. 공통 완료 기준 (P)(소절 10): `checklist.diff` `exit=0`, `ph-unfilled.log` `0`, `pr-edit.rc` `0`, `ph-posted-unfilled.log` `0`, `ph-table.diff` `exit=0`, `signature-last.log` `1`.
- **병합 시 반영(영록)**: STATUS 재환 절에 J-30b 행. WP-21 "남은 작업" 4 끝에 날짜 메모(희소 모델 → EXIF GPS ENU 정합·정합 좌표 splat은 J-30a, Object Capture 메시의 같은 좌표 변환은 J-30b로 수치 확인 — 공개 Tyrol 1회, 품질 판정 아님, zone 원점 변환과 실촬영은 남음). D-023 "좌표" 줄의 [미확인]에 날짜 메모를 더할지는 영록이 판단한다(공유 문서라 재환은 고치지 않는다). 이 파일 백로그의 J-30b 행을 "완료"로 옮긴다.
- **왜 재환 / 위험**: 입력·스크립트·기준·문장이 모두 펜스로 정해져 있고 결과가 숫자와 종료 코드로 판정된다. GPU·UE·GUI·Astra 레인·소유자 촬영이 필요 없다(기본 경로는 파이썬 계산 몇 초). 위험: ① J-30a 출력이 지워졌거나 다른 실행의 것이 섞임 → 설계 3의 파일 8개 확인과 두 가지 같은 실행 확인, 없으면 고정된 다시 만드는 경로(할 일 2), 섞였으면 멈춤. ② 축·규약 모호(Apple이 포즈 축을 문서화하지 않음) → 카메라 중심만 쓰고 회전은 쓰지 않는다. 반사가 필요하거나 축척이 1에서 멀면 FAIL이고 뒤집어 맞추지 않는다(설계 2·5). ③ 다시 만드는 경로의 메모리 — J-30a dry-run의 특징 추출 peak footprint 약 36 GB에 LM Studio 모델 약 94.6 GB가 함께 올라가 있으면 128 GB를 넘을 수 있다 → `timeout`과 rc로만 판정하고, 넘으면 멈춘다(시간·메모리 수치는 판정 근거가 아니다). ④ 과장 — 76장 드론 사진의 교회 하나에서 잔차가 작다는 것은 골목 결과가 아니다 → 문장은 렌더 스크립트가 고정한다(규칙 3·15), 품질·이음매는 V-05. ⑤ 빈 검사 — 기준이 두 dry-run에서 왔고, 틀린 셋 셋이 각각 다른 줄로 떨어진다(설계 6). ⑥ 라이선스 — Tyrol CC BY 4.0, 저작자 표시 :180, 커밋·업로드 없음.
- **dry-run 범위(Opus 2026-11-28, J-30b)**: 이 Mac에서 같은 입력으로 scratch 폴더(세션 scratchpad, 저장소 밖)에서 돌렸다: `poses.json`·OBJ sha256(위 `j30b-expected-sha`), `j30b-check-py`를 J-30a dry-run의 두 정합 모델(`aligned_txt`, 같은 데이터베이스의 두 번째 `mapper` + 정합 `al2_txt`)과 정합 전 모델(`sparse_txt`)에 — 13줄, 값은 설계 5·6(약 3 s, 정합 전 모델 약 10 s — 참고값, LM Studio 모델 로드 여부 기록 안 함), `j30b-verdict-py` 두 정합 모델 `verdict PASS 10/10`, 틀린 셋 셋이 `j30b-expected-neg`와 같은 FAIL 줄(두 모델 모두), `j30b-source-sh`를 파일 8개가 있는 폴더·하나를 지운 폴더에 — `source j30a`·`source rerun`, J-30a 같은 실행 확인 ①(`j30a-check-align`을 J-30a dry-run 폴더에 다시 돌린 출력이 그 폴더의 `align-check.log`와 같음)·②(`sfm_points 68938` 같음), `j30b-render-py`·`j30b-apply-py`를 `origin/main` `acbd954` scratch 사본(git init)에 J-30a 메모 줄을 J-30a 펜스로 넣고 `근거: PR #170.`으로 바꾼 상태의 mac-recon에 적용 → `apply.log` 네 줄, numstat `2 1`, `added.diff` `exit=0`, `memo-order.log` `adjacent`·`memo_lines 2`, 칸 자기 검사 `2`·`0`, 두 번째 적용 `j30b_memo 1` rc 1, 커밋 2 `sed`(가짜 번호) 뒤 `근거: J-30b PR.` 0줄, 그 사본을 clone한 가짜 `$W`에서 할 일 1·3~6의 명령을 이 절의 글자 그대로(`gh` 명령 제외, push는 로컬 원격으로) zsh로 돌려 모든 기대값(펜스 추출·`pre`·`source`·같은 실행 확인·판정·틀린 셋 줄은 `sh`로도 한 번 더 같음) — 파이썬 게이트(timeout을 단 꼴) 두 번 rc 0(1940 passed, 3 skipped), 커밋 두 개 작성자 `재환 <jaehwan.local@localhost>`, `branch-files*.log` 한 줄, `status-*.diff` `exit=0`. CI 표 두 `awk`는 PR #161의 `gh pr checks` 출력(16행 모두 pass)에서 `16`·`0`, pass가 아닌 행 하나를 더하면 `17`·`1`. `j30b-pre-sh`는 그 사본에서 `expected-pre`와 같고, 지금의 `origin/main`(J-30a 미병합)에서는 `j30a_memo 0`(멈춤 조건이 막는다). 셸 펜스 넷은 `sh`·`zsh`로 같은 출력, `bash -n`·`sh -n`·`zsh -n` 통과, shellcheck v0.11.0 `--severity=warning` 0건. 파이썬 펜스 다섯은 `ruff check`·`ruff format --check` 통과(설정 `tools/pyproject.toml`). 할 일 1의 두 `awk` 추출과 펜스 추출을 이 절을 넣은 `jaehwan-tasks.md` scratch 사본에서 돌려 `fence-lines.diff` `exit=0`, 추출본이 이 절의 펜스와 바이트로 같음, 할 일 2 중 COLMAP이 아닌 명령(J-30a 펜스 셋 추출 `98 total`, 입력 76장·해시, `make_ref.py` rc 0·`ref.diff` `exit=0`·sha256 위 값, 입력 해시 전후 같음)과 `align-gate.log` `awk`(J-30a dry-run의 `align-check.log`로 `rerun-align ok`, 중앙값을 3.201로 바꾸면 `rerun-align bad`). `j30b-bodycheck-sh`·`j30b-timeout-awk`는 견본 본문·견본 `commands.txt`(감싼 줄·안 감싼 줄·`# 정정:` 줄)에 돌려 기대값을 냈고, 견본에 0건 인용 하나·없는 숫자 하나를 넣으면 `quotes_zero 1`·`numbers_zero 1`이었다. dry-run하지 못한 것: 재환 worktree에서의 실행과 `gh` 명령(겹침·PR 열기·번호·등록 대기·CI watch)·GitHub으로의 push, 실제 J-30a 실행 폴더(아직 없다 — J-30a 미실행), 다시 만드는 경로의 COLMAP 실행 자체(J-30a dry-run의 같은 명령으로 대신함), 실제 본문의 인용·숫자 검사. 문서 9 검증 지적 반영 뒤(같은 날, Opus): `j30b-bodycheck-sh` 40줄 — 견본 본문의 `negcheck.diff` `exit=0` 인용(`quotes.tsv`에 `exit=0`과 `negcheck.diff`)이 옛 38줄 펜스에서는 `목록밖`·`quotes_zero 1`, 새 펜스에서는 `quotes_zero 0`(sh·zsh, `sh -n`·`zsh -n` 통과). `j30b-timeout-awk` 9줄은 감사 자신의 기록 줄(`timeout-audit.log`가 든 줄)을 세지 않는다. 할 일 1의 과제·펜스 추출을 고친 파일에서 다시 돌려 sh·zsh 모두 `fence-lines.diff` `exit=0`, `expected-fence-lines.txt` 14줄.

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
| V-05 S12 `run_game_perf.sh`의 남은 절반(경로 끝·`Capture Ended`·`-ExitAfterCsvProfiling` 종료·온전한 CSV의 `golmok-perf` — J-27 카드) | LM Studio 모델이 로드된 채 돌린 에디터 바이너리 `-game`이 Metal OutOfMemory로 끝났고(원인 [미확인]) 재환은 자기 모델을 내릴 수 없다. 크래시는 CrashReportClient 업로드(외부 발송)가 되므로 J-29 뒤에만 돌린다 | 영록(재환 유휴·모델 내림) |

## 게임 완성까지의 경로 (재환 일이 풀 수 있는 것과 없는 것)

"완성"의 정의는 Phase 1 MVP = **M7**이다(DEVELOPMENT-PLAN §3·§1.3, ROADMAP Phase 1): 베이스맵 위 걷기·달리기, 실촬영 골목 1곳(전 구간 걸림·떨림·구멍 없이, 목표 fps), 걸어 들어가는 실내 1곳(문 → 실내 → 문 왕복), 게이트 G2~G5(G5 = 렌더에 얼굴·번호판 누락 0, DEVELOPMENT-PLAN §6). 지금(2026-11-28) M1·M2 🟢, M3 🟡, M4 ⚪(STATUS 마일스톤).

핵심 경로(DEVELOPMENT-PLAN §5.4): **C-01 → C-02 → V-05 → D-010 → V-06 → M5 → C-05 → M6 → M7.**
- **소유자가 막고 있다**: C-01 리허설 촬영과 EgoBlur 모델 동의(V-01 §3 블러 점검), C-02 골목 촬영, C-05 실내 동의·촬영, V-05 뒤 제품 재구성 스택 확정과 필요 시 지출(D-023 ④), Windows 빌드 경로(D-022 ③), GASP(D-021 발효).
- **Opus가 막고 있다**: 입력·녹화·GPU 측정 재설계(B1 — V-17 §1·§2, V-08b, V-12, V-15의 선행), V-16 GUI 에셋·룩, V-05 판정과 D-010, 14b·16b·15b.
- **재환 일이 푸는 것**: V-19 남은 헤드리스 확인(J-12·J-12b~J-16), V-16·V-17·19b·V-18의 헤드리스 단계(J-17~J-23, J-25, J-26)로 그 카드의 GUI 단계가 바로 시작할 수 있게 하는 것, 도구·CI 신뢰도(J-06~J-11, J-28), 재설계·지표의 작은 조각(J-24, J-31a·J-31b), 공개 데이터 좌표 정합(J-30a·J-30b 설계 확정 — J-30b는 J-30a 병합 뒤 — 2026-11-28에 J-30을 나눔), V-05 S12 도구 경로(J-27, 성능 수치 아님).
- **재환 일이 풀지 못하는 것**: 촬영이 없으면 M4~M7은 시작하지 못한다. 재환 과제를 다 끝내도 MVP는 C-01·C-02를 기다린다. 이 파일은 그 기다림을 줄이는 준비 작업의 목록이다.

## 백로그 보충 규칙

- 배정 가능한(선행이 풀린, 설계 선행이면 메모가 있는) 과제가 **5개 아래로** 떨어지면 영록이 STATUS(🟡 행의 "PC 확인 대기"·"[미확인]"), ROADMAP, 열린 V 카드 런북(`docs/runbooks/pc-verify-*.md` §결과 빈칸, mac-setup §8·mac-recon 미확인 표), WP 문서의 "남은 작업"·리뷰 (C) 이월에서 채운다.
- 새 과제도 이 파일의 형식(출처 파일:줄 또는 카드 §, 허용 파일, 명령과 기대 출력인 완료 기준, 크기, 이유·위험)을 지킨다. 출처가 없는 일은 넣지 않고, 불확실한 것은 `[미확인]`으로 둔다.
- 재환이 막히면(선행 미충족·설계 메모 없음·GUI 잠금 대기) 다음 배정 가능 과제로 넘어가고 메시지로 알린다. 영록은 막힌 과제의 선행을 먼저 푼다.
- 이 파일은 영록이 고친다. 재환은 PR 본문에 제안만 적는다.
