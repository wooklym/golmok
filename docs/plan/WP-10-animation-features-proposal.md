# WP-10 — 애니메이션 평가·게임 기능 제안 (문서·리서치)

상태: ⚪ 대기 · 담당: 클라우드 Claude 세션(**Opus**; UE 코드 변경 없음) · 의존: 없음 · 검증: 사용자 승인(D-013~), PC 평가 런북(`runbooks/pc-verify-animation.md`)

## 목표
ROADMAP 1.3 "애니메이션: UE 5.8 기본 캐릭터·애니메이션 세트(Motion Matching 등 5.8 제공 기능 평가)"를 **리서치 문서 + PC 평가 런북**으로 만들고, DEVELOPMENT-PLAN §11 #6 "MVP 이후 게임 기능 우선순위(D-013~)"의 **제안 문서**를 써서 사용자가 결정할 수 있게 한다. V-03에서 발견된 night 프리셋 문제의 look-dev 메모를 남긴다. 코드는 바꾸지 않는다.

## 배경
- 현재 캐릭터: `Player/GolmokCharacter.cpp`(C++ Enhanced Input, 게임패드 `Gamepad_Left2D/Right2D/FaceButton_Bottom/LeftThumbstick` 매핑 포함), 마네킹 `tools/ue/add-mannequin.ps1`(`SKM_Manny_Simple`, `ABP_Unarmed`, Third Person 템플릿 에셋). V-01에서 L_Dev PIE 이동 확인.
- 조명(WP-05·V-03): `night` 프리셋은 태양 off(`lux 0` → `SetVisibility(false)`) + real-time SkyLight라 화면이 검게 나온다 → 달빛(낮은 lux 태양·색온도)·최소 `sky`·노출 상한 등을 look-dev에서 결정해야 한다(D-010 뒤 폴리시 단계). 프리셋 단일 소스는 `Config/Golmok/lighting_presets.json`.
- DEVELOPMENT-PLAN §11 #6: 포토 모드 등 MVP 이후 게임 기능 우선순위는 D-013~ 제안 대기.

## 산출물
1. `docs/research/09-animation-ue58.md`: UE 5.8이 제공하는 기본 캐릭터·애니메이션 세트(Third Person 템플릿 Manny/Quinn, Game Animation Sample의 Motion Matching·Pose Search·Chooser, 5.8 변경점), 라이선스(Epic Content License / Fab 라이선스 — **원문 확인·인용**), 현재 프로젝트 적용 경로 3안(① 현행 유지 ② Game Animation Sample 에셋 이식 ③ Motion Matching 최소 구성)과 비용·리스크·권장. 출처는 공식 문서 URL 인용(추측 금지, CLAUDE.md 규칙); 컨테이너에서 열리지 않으면 "확인 필요"로 표시.
2. `docs/runbooks/pc-verify-animation.md`: PC 세션이 3안 중 권장안을 L_Dev에서 시험하는 절차(에셋 가져오기, ABP 바인딩, 걷기/뛰기/점프 관찰, 게임패드 조작 확인, 스크린샷·짧은 영상), 채점표(자연스러움·발 미끄러짐·전환·비용), 실패 시 대안.
3. `docs/design/game-features-proposal.md`(D-013~D-017 **제안**): 포토 모드, Zone 지도·이동, 시간대·날씨, 환경음, 세이브 — 각각 한 쪽 분량으로 플레이어 가치, MVP 이후 어느 마일스톤에 넣을지, 구현 규모(C++/Python/에셋), 의존(D-010 등), 리스크. `docs/DECISIONS.md`에 **제안** 상태로 D-013~ 항목 추가(승인은 사용자).
4. `docs/design/lighting-night-lookdev.md`(짧은 메모): night 프리셋이 검게 나오는 원인(WP-05 설계 `lux 0` → 태양 숨김 + real-time SkyLight 기여 0)과 look-dev 후보(달빛 태양 0.05~0.5 lux·4000~7000 K, 최소 `sky`, `exposure_bias` 상한, 가로등은 Zone 에셋), 결정은 D-010 뒤 폴리시 단계(사용자)로 명시. JSON 값은 바꾸지 않는다.
5. STATUS·ROADMAP 1.3 행 갱신, DEVELOPMENT-PLAN §11 #6 상태 갱신.

## 완료 기준
문서 4개 + DECISIONS 제안 항목, `python scripts/check_repo.py`(링크 검사) 통과, CI 초록, STATUS `🟢`(제안 승인은 별도).

## 주의
- 라이선스 D-002 규칙: Fab/Marketplace 에셋 라이선스는 원문 확인 후 인용. 비상업 에셋 제외.
- UE 코드·설정·JSON을 바꾸지 않는다. 비용이 드는 선택(유료 에셋)은 제안만.

## 결과
(세션이 작성)
