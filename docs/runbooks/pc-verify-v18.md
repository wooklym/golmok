# V-18 — WP-13 빗소리 레이어 PC 카드 (T24~T29)

상태: ⚪ **카드 발행(2026-10-05, 오케스트레이터 Opus) — PC 대기.** Astra T24~T29(#114~#119, WP-16a 빗소리 레이어)가 클라우드에서 병합됐다. 이 카드는 그 결과의 PC 확인이다. 실제 장치 출력·레벨·전환·mute/Photo·세이브 복원·패키지를 보고, C-08 청취 자료를 남긴다. 절차의 원문은 [`pc-verify-wp13.md` §9](pc-verify-wp13.md)다. 이 카드는 순서·조건·기록 위치만 정한다.

- **브랜치**: `pc/v18-verify-rain-audio`(origin/main에서, 기준 SHA를 §8에 적는다). PR → main. 오케스트레이터가 `claude/v18-merge`로 반입한다.
- **선행**: V-16(`pc-verify-wp16a.md`)을 먼저 끝낸다. 날씨 상태 머신·전환이 PC에서 확인돼야 빗소리 판정이 뜻이 있다. V-16 결과가 main에 아직 없으면, 같은 PC 세션에서 V-16 직후에 이어서 한다. 이때 V-16 브랜치·워크트리를 그대로 쓰고, §8 결과는 이 카드에 따로 적는다.
- **작업 폴더**(AGENTS.md §5): 이 세션의 Claude Desktop 워크트리에서만 일한다. 다른 워크트리와 `C:\Users\user\golmok`은 읽기·복사만 한다.
- **GUI 잠금**: GUI 에디터·PIE·녹음·패키지 실행 전에 `C:\Users\user\AppData\Local\Temp\claude\gui-foreground.lock`을 확인한다(V-17과 같은 규칙: 20분 안 기록이 있으면 기다리고, 쓰는 동안 20분마다 갱신, 끝나면 삭제).
- **소요**: 약 2~3 h.
- **저장소에 넣는 것**: 이 문서 결과 칸, `pc-verify-wp13.md` §9 끝 "V-18 결과"(PC 결과 절, §7.6 예외), STATUS 자기 행·세션 로그. 녹음 원본 WAV·CSV는 PC 로컬에 두고 경로만 적는다(오디오는 저장소에 넣지 않는다).
- **PC fix**: 결함이 나오면 Astra 레인 파일(`Audio/`·`audio.json`·`audio_pure.py`·오디오 테스트)은 **고치지 않는다**. PR 본문에 재현·로그를 적으면 오케스트레이터가 Astra 과제로 넘긴다. 레인 밖 결함만 `WP-NN: PC fix …`로 고친다.
- 돈이 드는 일, 라이선스 동의, 외부 발송은 하지 않는다. 새 음원을 내려받지 않는다(채택 음원은 C-08 뒤 별도 결정).

## 소유자 조치 (C-07, 2026-10-09 갱신)
- [ ] V-17 카드와 같다. 고정 경로 `C:\Users\user\golmok-pkg\Windows\Golmok\Binaries\Win64\Golmok.exe`에서 "Windows 보안" 창이 뜨면 **취소**한다(미리 막으려면 그 exe에 차단 규칙을 한 번 만든다, [pc-setup.md §2a](pc-setup.md)). 세션은 누르지 않고 소유자에게 넘긴다.
- `setx GOLMOK_PKG_DIR …`는 소유자 작업이 아니다. PC 세션이 §0에서 한 번 한다.

## 0. 준비
- [ ] STATUS V-18 행을 🔵로 바꾸고 세션 로그 줄을 단다.
- [ ] `git fetch origin`을 하고, 열린 `pc/*`·`astra/*`와 겹치는지 확인한다(`git diff --stat origin/main...origin/<브랜치>`).
- [ ] `git switch -c pc/v18-verify-rain-audio origin/main`을 실행해 SHA를 기록하고 `git lfs pull`을 한다. `rain.wav`가 2,304,044 bytes(24 s)인지 확인한다.
- [ ] **패키지 출력 경로(§6용, PC 세션이 한 번)**: `[Environment]::GetEnvironmentVariable('GOLMOK_PKG_DIR','User')`가 비어 있으면(앞 카드가 아직 안 했으면) `setx GOLMOK_PKG_DIR C:\Users\user\golmok-pkg\Windows`를 실행하고 새 셸을 연다([pc-setup.md §2a](pc-setup.md)).
- [ ] `.\tools\ue\build.ps1`을 실행한 뒤 `.\tools\ue\test.ps1 -SetupDevLevel -Filter Golmok.` → **39 Success**(`Golmok.Audio.*` 2 포함)를 확인한다.

## 1. 생성·임포트 — [`pc-verify-wp13.md` §1·§9-1](pc-verify-wp13.md)
- [ ] §1 생성·임포트를 다시 실행한다. WAV는 기존 7 + rain 1 = **8개**이고, 임포트 로그에 오류 0·경고 0이어야 한다.
- [ ] `golmok.audio credits`와 `ATTRIBUTION.md`·배포용 txt에 rain 출처(자체 합성, seed 1307)가 있는지 본다.

## 2. 레벨 판정 — [§9-2](pc-verify-wp13.md)
- [ ] **판정 행은 강수 1·밤 하나**다.
  1. `golmok.tod night` → `golmok.weather rain 1` → 전환이 안착할 때까지(20 s 이상) 기다린다.
  2. **정지(발소리 없음)** 상태로 §7-1 master submix 녹음을 73 s 이상 한다.
  3. 안착 뒤 48 s를 §9-2 예시로 잘라(`setpos(int(start_s * rate))`, 녹음 경로는 `stop_recording_output`의 dir/name) `python -m golmok_tools.audio_analysis`의 whole-file RMS를 적는다. 예시의 경로 문자열에 Windows 경로를 넣을 때는 `r"C:\…\rain-night.wav"`(raw 문자열)나 `/` 구분자를 쓴다. 일반 문자열이면 `\u`·`\r` 이스케이프 때문에 SyntaxError나 FileNotFoundError가 난다(R119-2).
  4. 예측 **−42.45 dBFS ± 1 dB** 안이면 기록만 한다(밸런스 합격이 아니다). 밖이면 임포트 gain·master/PhotoGain·녹음 경로를 먼저 확인한다.
- [ ] 참고 행(판정 아님): 강수 1 낮 −39.93, 강수 0.3 낮 −40.77·밤 −44.11 dBFS.
- [ ] 선택 진단: 같은 자리·밤에서 clear와 rain 1의 RMS 차 Δ → rain 층 추정(예측 −46.52 dBFS).
- [ ] HUD `audio:` 줄의 `rain`(실제 강수량)과 `rain_gain`(`rain 0.3 instant` 0.350, `rain 1 instant` 0.800)을 적는다.

## 3. 전환·이음매 — [§9-3](pc-verify-wp13.md)
- [ ] 낮↔밤 전환 중에 빗소리가 끊기지 않는지, 베드를 대신하지 않는지 확인한다.
- [ ] 실제 포털로 실내를 왕복한다. rain 1에서 rain_gain이 0.800 → 0.280 → 0.800이어야 한다. 빠른 왕복도 해 본다(ForceState는 베드만 바꾸므로 대체가 아니다).
- [ ] 클릭·급정지는 **전환 구간(이벤트 ± fade)에서만** 판정한다. 정상 구간 녹음에는 24 s 이음매가 1회 이상 들어가야 하고, 그 z는 원본 자체 z(5.1)와 비교한다.
- [ ] `golmok.weather clear` 뒤 rain 채널이 **정확히 0**이 되는지 본다(T29 R118-1 디지털 0). HUD `rain_gain=0.000`과 무음 구간 파형으로 확인한다.

## 4. mute·Photo·일시정지 — [§9-4](pc-verify-wp13.md)
- [ ] `golmok.audio.mute 1/0`에서 빗소리가 베드와 같은 정책을 따르는지 본다(mute 중 디지털 0).
- [ ] Photo 진입/해제를 GamePause·TimeDilation 두 모드에서 해 본다. `pause_policy=maintain`이면 Photo 동안 강도는 멈추고 소리는 유지돼야 한다.
- [ ] `golmok.weather fx off`는 소리를 끄지 않아야 한다.

## 5. 세이브 복원 — [§9-5](pc-verify-wp13.md)
- [ ] 비 상태에서 저장 → clear → 로드하면 다음 Audio 틱에서 복원된다. 처음부터 비·실내인 시작도 확인한다.
- [ ] 복원·instant·첫 바인딩의 즉시 gain 변화는 **기대 동작**으로 따로 적는다(일반 전환의 클릭 판정과 섞지 않는다).

## 6. 패키지 — [§9-6](pc-verify-wp13.md)
§0의 `GOLMOK_PKG_DIR` 설정 뒤에 한다. `.\tools\ue\package.ps1`을 실행하고 `Package output: C:\Users\user\golmok-pkg\Windows`를 확인한다.
- [ ] `SW_rain`이 쿡됐는지, 크레딧 8항목이 있는지, `rain 1`이 재생되고 이음매를 한 번 넘기는지(24 s 이상 재생) 확인한다.
- [ ] 방화벽 창이 다시 뜨면 세션은 누르지 않고 소유자에게 넘긴다.
- 패키지 창의 콘솔(` 키)은 SendInput으로 열리지 않았다(2026-10-09 V-11 재실행, [wp18a §14-6](pc-verify-wp18a.md)). `golmok.weather rain 1` 같은 명령은 실행 인자 `-ExecCmds=…`로 준다.

## 7. C-08 청취 자료 (판정 아님)
세션은 판정하지 않는다. 소유자가 들을 수 있게 PC 로컬에 남기고 경로만 적는다(저장소에 넣지 않는다).
- [ ] 밤 강한 비 5분 연속 녹음 1개: 24 s 반복과 4–8 kHz 피로를 듣기 위한 것이다.
- [ ] 낮 약한 비(0.3) 60 s: 희미한 쉬익으로만 들리는지 듣기 위한 것이다.
- [ ] 강한 비 실내↔실외 왕복 30 s: ×0.35만으로 충분한지, 저역 통과가 필요한지 듣기 위한 것이다.
- [ ] 세션이 들은 첫인상을 한 줄씩 적는다: 큰 방울이 비로 들리는지 틱으로 들리는지, 반복, 약한 비, 실내. 최종 판단은 C-08(소유자)이다. gain 0.5503 대 약 0.893 비교는 C-08에서 한다(이 카드는 `audio.json`을 바꾸지 않는다).

## 8. 결과
| 항목 | 기대 | 결과/근거 |
|---|---|---|
| 세션/head | 날짜·워크트리·기준 SHA | (대기) |
| §0 빌드·자동화 | 39 Success | (대기) |
| §1 임포트 | 8개, 오류·경고 0, 크레딧 | (대기) |
| §2 판정 행(강수 1 밤) | −42.45 dBFS ± 1 dB | (대기) |
| §3 전환·이음매·clear 0 | 끊김·클릭 없음, rain_gain 0.800/0.280, clear 디지털 0 | (대기) |
| §4 mute·Photo | 정책 일치, mute 디지털 0 | (대기) |
| §5 세이브 | 다음 틱 복원 | (대기) |
| §6 패키지 | SW_rain 쿡·크레딧 8·재생 | (대기) |
| §7 C-08 자료 | 녹음 3개 경로·첫인상 | (대기) |

STATUS 반영(PC 세션이 자기 행만): V-18 행 결과와 세션 로그. 다른 행(WP-13 병행 트랙·C-08·WP-16)은 클라우드 병합 커밋이 옮긴다. PR 본문에 "병합 시 반영" 문안을 적는다.
