# night 프리셋 look-dev 메모

작성: 2026-09-25, WP-10(문서 전용) · 상태: **메모** — 값은 바꾸지 않았다(`Config/Golmok/lighting_presets.json` 그대로). 결정은 **D-010 뒤 폴리시 단계(ROADMAP 1.6)에서 사용자**가 한다. 관련 제안: [`game-features-proposal.md`](game-features-proposal.md) D-015.
표기: [확인] 1차 출처·코드 / [2차] / [미확인] 추정 — PC look-dev에서 확인.

## 1. 증상 (V-03, 2026-09-25)
WP-05 런북 §3 결과: night(키 4)로 바꾸면 태양이 꺼지고 `L_ZoneTest`의 하늘·지면이 **완전 검정**, 노출 +1.5 EV로도 0 [확인: [`runbooks/pc-verify-wp05.md`](../runbooks/pc-verify-wp05.md) 결과 표 §3 메모]. PC 세션 판정: 코드 결함이 아니라 프리셋·조명 설계 문제.

## 2. 원인 (코드·설정에서 확인)
| 고리 | 현재 값 | 결과 |
|---|---|---|
| night 프리셋 | `pitch 15, yaw 0, lux 0, kelvin 4000, sky 0.15, fog 0.03, volumetric true, exposure_bias 1.5` [확인: `lighting_presets.json`] | `pitch +15` = 빛이 **지평선 아래에서 위로** 향함. 켜 두더라도 지면을 비추지 못함 |
| 태양 처리 | `lux 0`이면 전환 끝에 `Sun->SetVisibility(false)` [확인: WP-05 설계 §2·`GolmokTimeOfDay`] | 장면의 유일한 방향광이 사라짐 |
| 하늘 | `SkyAtmosphere` + 태양 `atmosphere_sun_light=True` [확인: `setup_dev_level.py` 56~66행] | 대기를 비추는 빛이 없으니 하늘 휘도 ≈ 0 |
| 스카이라이트 | `real_time_capture=True` [확인: `setup_dev_level.py` 71행]. 문서: Sky Light는 먼 장면(대기 포함)을 캡처해 광원으로 쓴다 — "SLS Captured Scene: Construct the sky light from the captured scene" [확인: https://dev.epicgames.com/documentation/en-us/unreal-engine/sky-lights-in-unreal-engine] | 검은 하늘을 캡처 → `sky 0.15`는 **0에 곱하는 배율**이라 기여 0 |
| 노출 | 자동 노출(히스토그램 기본), `r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange=True` [확인: `DefaultEngine.ini` 16행], 프리셋은 `AutoExposureBias`만 바꿈 | 자동 노출은 Min/Max EV100 사이에서만 적응한다("If Min EV100 is equal to Max EV100, auto exposure is disabled", [확인: https://dev.epicgames.com/documentation/en-us/unreal-engine/auto-exposure-in-unreal-engine]). 휘도가 0인 장면은 어떤 bias로도 밝아지지 않음 |

요약: **빛이 0**이다(태양 숨김 × 하늘 0 × 스카이라이트 0). 노출로는 해결할 수 없고, 무엇이든 빛을 넣어야 한다.

## 3. 단위에 대한 주의
프리셋의 `lux`는 물리값이 아니라 **프로젝트 스케일**이다: 맑은 정오 `clear_noon`이 10, 흐린 아침 2.5 [확인: JSON]. 실제 직사광은 32,000~100,000 lx, 맑은 밤 보름달은 0.05~0.3 lx다 [2차: https://en.wikipedia.org/wiki/Lux 표, 보름달 값은 Kyba et al. 2017 인용]. 실제 비율(약 10⁻⁶)을 그대로 쓰면 자동 노출 범위 밖이라 여전히 검다. WP-10 스펙(`plan/WP-10-animation-features-proposal.md` 산출물 4)이 제안한 **0.05~0.5**(프로젝트 스케일)는 정오의 1/200~1/20로, 게임에서 흔한 "밝은 달밤" 스타일이다 [미확인 — look-dev로 판단].

## 4. look-dev 후보 (조합해서 쓴다)
| # | 후보 | 바꾸는 곳 | 기대 | 리스크 |
|---|---|---|---|---|
| A | **달빛 = 같은 DirectionalLight**: `pitch −25~−45`(달이 떠 있음), `lux 0.05~0.5`, `kelvin 4000~7000`(차가운 톤은 관습적 "밤 느낌"; 실제 달빛 색은 해보다 약간 따뜻하다고 알려짐 [미확인]) | JSON 값만(스키마 그대로, `lux > 0`이라 태양이 숨지 않음) | 그림자 있는 달빛, 스카이라이트가 대기를 다시 캡처해 약한 앰비언트 | 대기가 **어두운 낮 하늘**(파란 하늘)로 그려지고 자동 노출이 그것을 끌어올리면 "낮 같은 밤" → B와 같이 써야 함 |
| B | **노출 상한**: 밤에는 Max EV100을 낮춰(또는 수동 노출) 장면을 어둡게 유지. 최소 밝기를 보장하려면 Min EV100도 | JSON 스키마에 키 추가(`exposure_min_ev100`/`exposure_max_ev100` 등) → C++ `GolmokTimeOfDay`·`lighting.py`·`lighting_presets.py`·테스트 동시 변경(WP-05 규칙) | "어두운데 보이는" 밤을 안정적으로 | 코드 변경 = 별도 WP. 낮 프리셋 값도 정해야 함 |
| C | **최소 `sky`**: 스카이라이트가 검은 하늘을 캡처하지 않게 — 밤에만 지정 큐브맵(밤하늘 HDRI) 또는 하반구 색 지정("Lower Hemisphere is Solid Color", 같은 Sky Light 문서) | 레벨 설정 또는 C++(밤 전환 시 소스 타입 변경) | 그림자 없는 부드러운 앰비언트 최소치 | HDRI 라이선스(D-002), real-time capture와 전환 시 튐 |
| D | **달을 별도 DirectionalLight**로: Sky Atmosphere 문서 "set the Atmosphere Sun Light Index for each; for instance, 0 for the Sun and 1 for the Moon" [확인: https://dev.epicgames.com/documentation/en-us/unreal-engine/sky-atmosphere-component-in-unreal-engine] | 레벨에 두 번째 광원 + `GolmokTimeOfDay`가 두 광원을 보간(코드 변경) | 해 지고 달 뜨는 연속 시간대(D-015)에 자연스러움 | 코드·테스트 변경, 두 광원 그림자 비용 |
| E | **가로등·간판·창문 불빛**(서울 골목 밤의 실제 주광원) | Zone 에셋(발광 머티리얼·포인트/스폿 라이트), 실내 창 발광 | 품질이 가장 높음 — 실제 밤 사진과 비슷 | 낮에 찍은 스캔 텍스처에는 불 켜진 상태가 없음(R5) → 발광 마스크 수작업. 광원이 많으면 5.8 MegaLights("Megalights is now entering Production Ready status with Unreal Engine 5.8" [확인: 5.8 릴리스 노트]) 검토 |

권장 시작점(판단): **A + B**로 "보이는 밤"을 먼저 만들고, Zone이 들어온 뒤 **E**로 품질을 올린다. D는 연속 시간대(D-015)를 채택할 때만. C는 A가 부족할 때.

## 5. PC look-dev 절차 (결정 전, 커밋 없이)
1. `L_Dev`(또는 스파이크 청크 레벨)에서 JSON을 **로컬에서만** 고쳐 night를 A 값 3세트(`lux 0.05/0.2/0.5`, `pitch −35`, `kelvin 4000/5500/7000`)로 바꿔 가며 `golmok.lighting.apply("night")`(에디터) 또는 PIE `golmok.tod night`. 커밋 금지 — `tools/tests/test_lighting_presets.py`에 **값 회귀 테스트**(4 cycle 프리셋 값 고정)가 있어 값 변경은 테스트와 함께 바꿔야 한다 [확인: 테스트 파일 `WP04_PRESETS` 30~39행, `test_cycle_values_equal_wp04_lighting_py` 87행].
2. B는 코드가 없으니 에디터에서 PostProcessVolume의 Metering Mode·Min/Max EV100을 손으로 바꿔 효과만 본다.
3. 같은 시점 3곳(`golmok.viewpoints`)을 캡처해 비교, 좋은 조합과 스크린샷을 이 문서 §6에 적는다.
4. 사용자가 조합을 고르면 → WP(프리셋 값 + 필요 시 스키마 키 추가, Fable ultracode — 게임 비주얼 직접 영향, DEVELOPMENT-PLAN §7.4).

## 6. 결과 (look-dev 세션이 작성)
(비어 있음)
