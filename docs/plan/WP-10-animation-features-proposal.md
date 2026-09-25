# WP-10 — 애니메이션 평가·게임 기능 제안 (문서·리서치)

상태: 🟢 완료(2026-09-25, 문서; 제안 승인·V-08은 별도) · 담당: 클라우드 Claude 세션(**Opus**; UE 코드 변경 없음) · 의존: 없음 · 검증: 사용자 승인(D-013~), PC 평가 런북(`runbooks/pc-verify-animation.md`)

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
세션: session_011Jdzkehx5EZRAV1kX7PnGD (Opus 5.5, 단일 세션 + 읽기 전용 리뷰어 1명), 2026-09-25. PR #17(draft). UE 코드·설정·JSON·에셋 변경 없음, 새 의존성 없음.

**산출물**
| # | 파일 | 요지 |
|---|---|---|
| 1 | [`research/09-animation-ue58.md`](../research/09-animation-ue58.md) | 현행(템플릿 마네킹 + `ABP_Unarmed`) 정리, Motion Matching(Pose Search)·Chooser·GASP 공식 문서 인용, 5.8 릴리스 노트 변경점 표(Pose Search·Chooser 연동 수정, `MotionMatchMulti` Experimental, Mover는 여전히 Experimental → 제외), 3안 비교·**권장: ② GASP 로코모션 이식을 먼저 시험**(게이트: 라이선스 원문·V-08 채점·LFS 용량) |
| 2 | [`runbooks/pc-verify-animation.md`](../runbooks/pc-verify-animation.md) | V-08: §0 라이선스 확인(사용자) → §1 GASP 둘러보기(저장소 밖) → §2 ① 기준선 녹화 S1~S8 + `csvprofile` → §3 ② Migrate(`Content/Golmok_AnimEval/`, 시험 브랜치, 에셋 커밋 금지) → §4 ③ → §5 채점표 7항목 → §6 실패 대안 → §8 결과 표 |
| 3 | [`design/game-features-proposal.md`](../design/game-features-proposal.md) + DECISIONS D-013~D-017(**제안**) | 포토 모드(M7 최소판) · Zone 지도·이동(Phase 2 초반) · 시간대 폴리시(M7)/날씨(Phase 2 중반, D-010 뒤) · 환경음(기본 M5~M7, 현장 녹음 Phase 2) · 세이브(Phase 2 초반, 경위도로 저장). 권장 우선순위 표 |
| 4 | [`design/lighting-night-lookdev.md`](../design/lighting-night-lookdev.md) | night 검정 원인(태양 숨김 × 대기 0 × real-time SkyLight 0, 노출로는 해결 불가), 프로젝트 lux 스케일 주의, 후보 A~E(권장 A 달빛 + B 노출 상한 → Zone 뒤 E 가로등), PC look-dev 절차(커밋 없이, 값 회귀 테스트 주의) |
| 5 | STATUS·ROADMAP 1.3·DEVELOPMENT-PLAN §1.3·§11 #6(+#8·#9 추가) | 갱신 |

**출처**: Epic 공식 문서 12건을 컨테이너에서 직접 열어 문장 확인 — 5.8 릴리스 노트, Motion Matching, Game Animation Sample, Dynamic Asset Selection(Chooser), Third Person Template, Licenses and Pricing in Fab, Sky Lights, Auto Exposure, Sky Atmosphere, Taking Screenshots, Saving and Loading, MetaSounds. [2차] 1건(Wikipedia Lux 표). 게이트: ruff OK, `python -m pytest -q` 626 passed·3 skipped, `check_repo.py` OK.

**확인 못 한 항목(열리지 않음 → 문서에 [확인 필요])**
1. Fab EULA 원문(https://www.fab.com/eula, 403) — Standard License 조항, Epic 제작/UE 전용 콘텐츠 조건
2. Unreal Engine EULA(https://www.unrealengine.com/eula/unreal, 403) — 템플릿 마네킹 등 엔진 동봉 콘텐츠
3. Epic Content License Agreement(https://www.unrealengine.com/eula/content, 403)
4. GASP Fab 리스팅의 라이선스 표기(fab.com, 403)
5. GASP 5.8 업데이트 블로그(unrealengine.com tech-blog, 403) — 5.8 신규 기능은 [2차]로만 기재
6. 통신비밀보호법 원문(law.go.kr 본문 로드 실패) — 환경음 녹음 리스크
7. (PC에서 실측) Pose Search·Chooser 플러그인 성숙도 표시, GASP 용량·시퀀스 수, 스켈레톤 호환

**사용자 결정 목록**
1. D-013~D-017 각각 승인/수정/보류/폐기, 권장 우선순위 동의 여부(특히 환경음 기본판·포토 모드 최소판을 Phase 1 M7 선택 항목으로)
2. GASP 라이선스 원문 확인(V-08 §0) → 문제없으면 V-08 진행, 이후 ①/②/③ 채택
3. 사운드 라이브러리 구매 여부·현장 녹음을 촬영 가이드에 넣을지
4. 날씨(비)를 Phase 2에 넣을지(D-010 뒤로 미뤄도 됨)
5. night look-dev 조합(D-010 뒤 폴리시 단계)
