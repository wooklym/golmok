# WP-17 — 현장 녹음 절차·Zone별 소리 (T4)

상태: **문서 완료·설계 리뷰 대기**(2026-09-28). 브랜치 `astra/wp-17-field-recording`, main `f29a24d` 기준. 담당 ChatGPT Astra. T4는 문서 배정이며 현장 녹음·Zone 오디오 구현 완료를 뜻하지 않는다.

## 목표·산출물

[현장 녹음 절차](../capture/03-field-recording.md): 아이폰/외장·바람막이 비교, 위치·시간대·테이크 분량, 대화 제외 운영 규칙, 파일명·비공개 원본 보존, 정규화·루프 편집·용량, 권리/확인일·청취 기록·WP-13 반입 기준. 녹음 수치와 sounds[] 설계는 Fable이 제안/가설로 승인했다. 실제 채택은 Zone2곳 확보·V-10 통과·Fable 청취 뒤다. 구매·장비/도구 설치·현장 녹음·새 소스/약정 채택은 하지 않았다.

Zone sounds[]는 아래의 **변경 제안**이며 공유 스펙·스키마·런타임은 수정하지 않는다. 현재 v1에 추가하면 알 수 없는 최상위 키 오류가 난다. [현행 Zone 계약](../spec/zone-manifest.md)의 좌표·버전 원칙을 따른다.

## 결과·완료 기준

- 문서2개 작성 완료. Apple/Audacity 공식 자료에서 녹음 입력/iCloud 동기화, Normalize 기능을 확인하고 절차에 확인일·링크를 남겼다. 법령 원문은 과제 지시대로 [확인 필요]이며 법률 판단을 하지 않았다.
- 녹음/음질/루프/소유자 밸런스·스키마 구현·에디터/패키징은 미실행이다. 문서 검토와 실제 실행을 구분한다.
- 새 의존성·공유 파일 수정·훅 없음. 병합 시 반영 문안은 대상별로 아래에 분리했다.
- Fable 검토 요청: 녹음 시간/루프/peak 가설, 환경음 베드와 위치 점의 동시 재생 정책, 권리 계약 확장 경계. 코드 없는 문서 PR이므로 Opus는 명세 일관성·절차 누락을 검토한다.

## 병합 시 반영 — 제안 대상별 완성 문안

### docs/spec/zone-manifest.md — 다음 스키마 버전의 sounds[] 절 신설안

**채택 전 제안**이다. 버전 번호는 스키마 소유자가 예약한다. v1 파일에 조용히 필드를 추가하지 않는다. 새 버전에서 `sounds`를 선택 배열로 정의하고, 누락/빈 배열은 위치 음원 없음으로 처리한다. 현재 WP-13 전역 ambience는 그대로 별도 존재한다.

```json
{
  "sounds": [
    {
      "id": "room_vent_01",
      "audio_id": "interior",
      "position_enu": [2.0, -1.0, 1.5],
      "radius_m": 6.0,
      "gain": 0.3
    }
  ]
}
```

예시는 새 버전 manifest 안의 부분 조각이며 현행 v1 검증기에 넣는 입력이 아니다. `interior`는 참조 형태를 보이는 기존 asset ID이고 실제 위치 음원 채택을 뜻하지 않는다. 채택 구현 시 위치 음원은 mono 자산을 우선하며 stereo ambience를 자동으로 mono화하거나 공간화하지 않는다.

| 필드 | 계약 제안 |
|---|---|
| id | Zone 버전 안에서 유일, 기존 ID 규약 `^[A-Za-z0-9][A-Za-z0-9_]*$`; 대소문자만 다른 충돌도 거절 |
| audio_id | 배포되는 audio.json assets의 ID 참조; 외부 URL/파일 경로 아님 |
| position_enu | 유한 숫자3개, Zone-local ENU m, Z-up; UE cm 좌표 저장 금지 |
| radius_m | 유한 수 >0; 중심에서 이 거리까지 감쇠해0, 거리 밖 무음 |
| gain | 유한 수0~1, SoundWave gain·master에 추가 곱하는 위치 점 배율 |

각 원소는 위5개 필수 키만 허용한다. loop/저자/라이선스/확인일/소스 경로는 audio.json이 정본이므로 여기서 중복 정의하지 않는다. 1차 위치 점은 loop=true인 채택 자산만 허용한다. 감쇠는 1차 선형→0 가설이며 `falloff`는 청취 뒤 확장할 예약 후보로만 두고 현재 키에는 추가하지 않는다. 원샷 이벤트/시간대별 배치/확률 재생은 후속 스펙으로 분리한다. 하나의 Zone은 최대32점(초기 예산 가설)이며 초과는 조용히 잘라내지 않고 검증 오류로 돌린다.

좌표 변환은 `zone-local → manifest.transform으로 ECEF → area ENU → UE` 순서로 기존 Zone 변환을 재사용한다. 마지막 ENU→UE는 `(100x,-100y,100z)`이며 zone yaw를 중복 적용하지 않는다. 예시의 x/y 부호·단위·비영 yaw·서로 다른 원점·origin shift를 합성 테스트로 대조한다.

일반 스키마 검사는 형식/범위/추가 키를, 통합 검사는 asset 참조 존재·loop/mono·cook 대상·표기 필수 필드를 확인한다. asset이 빠진 배포는 패키징 검증 실패다. 런타임에서 누락이 발견되면 해당 점만 무음과 명확한 진단으로 처리하고 임의 다른 음원으로 대체하지 않는다.

**수명/겹침 정책 가설**: 식별 키는 `(zone_id, version, sound_id)`. Zone 실제 로드 완료 후 활성화하며 취소·실패·unload에서 그 Zone의 컴포넌트를 정리한다. reload 때 이전 세대 콜백이 새 컴포넌트를 만들지 못하도록 세대 토큰을 검사한다. 같은 키의 중복 spawn은 금지한다. Zone 겹침 권위 판단은 현행 Zone 선택 규칙을 재사용하며 비활성 버전의 소리는 재생하지 않는다. 서로 다른 활성 점은 자연스럽게 중첩될 수 있어 총 동시 voice 한도/감쇠는 Fable 청취로 확정한다. 초기에 숨은 Zone 소리만 남는 상태를 허용하지 않는다.

전역 ambience와 위치 음원은 동시에 재생될 수 있으므로 같은 녹음을 두 레이어에 배치하지 않는 편집 규칙을 둔다. 자동 ducking은 이번 제안에 포함하지 않는다. Photo mute/maintain은 WP-13 정책을 재사용하되 위치 점에도 적용하는 테스트를 추가한다. 위치 음원 도입은 환경음 품질 변경이므로 Fable 승인·PC 청취 후 채택한다.

### 스키마/로더 담당자에게 — 이행 작업 묶음

1. 새 버전 예약과 v1 읽기 호환 범위를 결정한다. v1은 sounds 없음으로 처리하며 원본은 수정하지 않는다.
2. docs/spec 원본과 tools 패키지 사본 스키마, Python validator/생성기, UE manifest 로더를 같은 변경 묶음에서 갱신한다. 이전 UE가 새 버전을 읽으면 명시적 미지원 오류를 내야 한다.
3. schema_version은 파일 계약 버전이고 Zone data version은 v<version> 폴더의 불변 데이터 버전이다. 모든 Zone을 일괄 bump하지 않는다. sounds 누락은 위치 음원 없음으로 유지하고 실제 점을 넣는 Zone만 새 data version으로 bump한다(reviewed_* 초기화 후 재검토). 새 schema_version에 맞게 이행하며 좌표/기존 필드를 보존한다.
4. 양/음성 테스트: 빈 배열·중복ID·없는 asset·원샷/stereo 참조·NaN/Inf·0/음수 반경·범위 밖 gain·추가 키·32점 초과·회전/원점변환·로드 취소/재진입·겹친 Zone·Photo·패키지 cook.
5. rollback은 이전 Zone data version/호환 로더로 되돌리는 방식이며 불변 원본을 덮어쓰지 않는다. v1 데이터를 새 스키마로 오인해 재저장하지 않는다.

### docs/plan/STATUS.md — Astra 병행 트랙 WP-17 행

- 상태 칸: `🟢 문서 완료(2026-09-28 #37 병합) — 현장 녹음·sounds[] 스키마/로더 미실행`
- 담당 칸: `**ChatGPT Astra**(T4), 설계 리뷰 Fable·문서 리뷰 Opus·병합 오케스트레이터`
- 메모 칸: `capture/03-field-recording.md(장비·분량·대화 제외·명명/정규화/루프·기록표), WP-17 sounds[] 새 스키마 제안; 실제 녹음·권리 계약 확장·스키마/로더 구현은 후속 배정 대기.`

행 조립은 병합 세션이 한다.

### docs/ROADMAP.md — D-016(b) 현장 녹음 진행 문안

> WP-17 T4 현장 녹음 절차 문서 완료. 채택 음원의 권리/확인일·루프·배포 크레딧 및 V-10 소유자 밸런스를 통과한 뒤 실제 반입한다. Zone sounds[]는 새 스키마·로더 동시 변경 제안 단계로, 현재 v1에 반영하지 않는다.

### docs/plan/astra-tasks.md — T4 언제 열과 우선순위 줄

- T4 언제 열: `**완료·병합**(#37, 2026-09-28) — 절차 문서만, 현장 녹음·sounds[] 구현 별도`
- 우선순위 줄: 끝의 `→ T4`를 `~~T4~~` 완료 항목으로 옮기고, 남은 순서 `T2 GUI → T5(PC GUI)`를 유지한다.

### 오디오 레인 후속 인계

현행 audio.json 계약으로 자체 녹음은 반입 불가다. 자체 녹음 license 값·license_url·HTTPS source_url 대신 내부 기록 ID 사용 규칙을 Python/C++ 검증과 ATTRIBUTION/크레딧에 함께 확장하는 별도 작업이 필요하다. 공개 CC0/CC-BY 부여는 소유자 승인 사항이며 가짜 URL이나 project-generated로 우회하지 않는다.

통합 검사는 제안 도구 `golmok-zone validate --audio-config <audio.json>`에서 asset 존재/loop/표기와 연결 WAV 헤더의 mono 채널을 검사하는 방식으로 인계한다(현재 구현된 옵션 아님). 경로는 audio.json과 Audio/src를 명시적으로 제공하고 원본 녹음을 자동 탐색하지 않는다. cook 포함은 에디터 Python/패키지 manifest 검증 단계에서 확인한다. audio.json에 channels 필드를 추가하려면 오디오 레인 계약 변경으로 별도 검토한다.

## 검증 기록

2026-09-28 로컬: ruff check/format103, pytest **736 passed/68 skipped/208 warnings,43.90s**, check_repo, diff --check 통과. 변경은 문서2개뿐이며 UE 빌드/GUI/녹음은 실행하지 않았다. CI는 PR 현재 head 결과로 확인한다.

## PR #37 리뷰 수정

F1/F2/F4/F7/F9 반영: 자체 녹음 계약 확장 필수·공개 라이선스 소유자 승인, STATUS 칸별/astra-tasks 열별 문안, asset ID/파일 대응, 자문8 링크·iCloud 동기화 끄기 운영 규칙. F6/F8 이행 버전 구분·통합 검사 도구/mono 근거도 반영했다. Fable 보정대로 원경 stereo20~26초·룸톤 mono30~40초, falloff 예약 후보만 기록. main c16b5a7 병합 충돌 없음.

## 병합 기록 — PR #37 (2026-09-28, 오케스트레이터 세션)

대상: [PR #37](https://github.com/wooklym/golmok/pull/37) `astra/wp-17-field-recording` 18aaebc(리뷰) → 80f6f25(수정; 병합 세션이 diff로 (A) 반영 확인). 절차: DEVELOPMENT-PLAN §7.6 — Opus 5.5 ultracode 명세·절차 리뷰(코드 없는 문서 PR: 지적 12건마다 회의론자 2명) + Fable 설계·품질 검토 → PR 코멘트(2026-09-28 04:38Z) → Astra 수정(05:06Z, CI 10/10) → D-019에 따라 소유자 승인 없이 이 커밋(`WP-17: 병합 시 반영 (Fable)`) → merge commit. 전문은 PR #37 코멘트.

- **BLOCKING 없음.** 레인 준수(문서 2개만, 스펙·공유 문서·코드·훅 무변경). `sounds[]` 제안의 좌표(zone-local ENU m·Z-up)·ID 규약·변환 순서(zone-local → transform(ECEF) → area ENU → UE `(100x,-100y,100z)`, yaw 중복 적용 없음)·gain 의미(0~1, SoundWave gain·master에 곱)가 현행 Zone 계약(spec §1·§2·§4·§5)과 `audio.json`/`audio_pure.py`에 맞고, WP-13 반입 예산(항목 5 MB/총 40 MB, 48 kHz PCM16, 스테레오 20 s ≈ 3.84 MB) 계산과 개인정보 운영 규칙(research/05 자문 항목 8)이 정확하다. golmok-zone v1 스키마가 미지정 최상위 키를 거절함을 실행으로 확인.
- **(A) 5건 → 80f6f25 반영**: F1 자체 녹음 권리 표현을 확정 서술로(현행 `audio.json` 계약 — license ∈ {CC0-1.0, CC-BY-4.0, project-generated}·`source_url` https 필수 — 로는 반입 불가, license 값·내부 기록 ID 계약 확장이 반입 전제, 자체 녹음에 CC0 등 공개 라이선스 부여는 소유자 승인 항목) + 오디오 레인 후속 인계 절, F2 STATUS 상태/담당/메모 칸별 문안, F4 astra-tasks '언제' 열·우선순위 줄 분리, F7 파일명 범주 `outdoor_day|outdoor_night|interior|footstep_<asphalt|tile|stairs>|landing`·Zone 밖 `outside_<session_id>` 접두어·반입 파생본 `src/<category>/<asset_id>.wav`·asset ID 규약 대응, F9 research/05 자문 항목 8 링크·문장 정정·iCloud 동기화 끄기 운영 규칙.
- **(B) 반영**: F6 `schema_version`(파일 계약)과 Zone data version(`v<version>` 폴더) 구분, 빈 배열 일괄 bump 제거(실제 점을 넣는 Zone만 bump·`reviewed_*` 초기화), F8 통합 검사 도구(`golmok-zone validate --audio-config <audio.json>` 제안, 현재 미구현)·mono 판정 근거(연결 WAV 헤더). 반박(수정 불필요): F3 ROADMAP 대상 줄(병합 세션이 Phase 2 목록 줄로 결정), F5 v1 UE 로더는 경고만(문서의 "오류"는 golmok-zone 스키마 검사 기준), F10 예시 asset id, F11 오프라인 [확인](Apple/Audacity 링크는 Astra 확인일 유지), F12 PR 링크.
- **Fable 설계·품질**: `sounds[]` 제안(5개 필수 키·loop 자산만·mono 우선·선형→0 감쇠 1차·`falloff` 예약 후보만·32점 예산·Zone 로드 세대 토큰·자동 ducking 없음·Photo mute/maintain 재사용)은 **제안으로 승인** — 채택은 Zone 2곳 확보·V-10 통과·Fable 청취 뒤이고 schema bump·로더·검증기·스펙 동시 변경은 Claude 레인(스펙 소유자)이 한 묶음으로 한다. 녹음 가설 승인(원경 3 min×3·룸톤 2 min×3·발소리 20보×3·착지 10, −6 dBFS peak, 마이크 1.5 m/발소리 0.5 m, 낮 10~16시·밤 20~22시, 앞뒤 10 s 여유, 대화 제외, 크로스페이드 접합 0.1~0.5 s) + 루프 길이 보정(도시 원경 스테레오 20~26 s, 룸톤 mono 30~40 s; 반영됨, V-10 청취로 확정). 외장 마이크·바람막이 구매는 지출이라 소유자 항목(내장 마이크 30 s 시험 실패 시에만 후보 제시). 통신비밀보호법·초상/개인정보는 [확인 필요] 유지, 법률 결론 없음.
- **(C) 옮긴 것**: STATUS 병행 트랙 WP-17 행(⚪ 배정 → 🟢 문서 완료)·마지막 갱신, ROADMAP Phase 2 목록의 WP-17 문구(D-016 (b)), DECISIONS D-016 진행 줄, astra-tasks T4 완료·우선순위, 이 절. Zone 스펙 `sounds[]` 절은 제안 단계이므로 `docs/spec/zone-manifest.md`에는 넣지 않았다(채택 시 Claude 레인이 새 schema_version과 함께).
- 판정: **병합**. 실제 현장 녹음·청취·권리 계약 확장·스키마/로더 구현은 미실행이며 후속 배정 대기(WP-17 문서 "오디오 레인 후속 인계").
