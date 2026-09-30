# WP-16 — 날씨(비) 분할 검토 메모 (Fable, 2026-09-29)

상태: ⚪ 검토 메모(착수 아님). D-015 (b)는 "Phase 2 중반, D-010 뒤"로 승인됐다. 이 메모는 WP-14/WP-15와 같은 방식으로 **D-010(환경 표현 방식)과 무관한 부분을 16a로 떼어 낼 수 있는지**를 검토하고, 떼어 낼 때의 설계 골격과 착수 조건을 적는다. 실제 "설계 (확정)"은 착수 세션 전에 Fable이 별도로 확정한다.

## 1. 결론(오케스트레이터 검토, D-019 — 소유자가 뒤집을 수 있음)
- **분할 가능.** 비의 구성 요소 중 *표면 젖음*(러프니스·웅덩이·반사)만 D-010에 묶여 있고, 나머지(날씨 상태·조명 수정자·빗줄기·소리·저장·콘솔/HUD)는 메시든 splat이든 같다.
- **16a(표현 무관, 클라우드 Opus ultracode 가능)**: 날씨 상태 머신 + JSON 날씨 프리셋(조명 수정자) + 빗줄기 파티클 + 젖음 파라미터 **계약**(값만 공급) + 오디오 이벤트 훅 + 세이브 필드 + 콘솔/HUD + 자동화.
- **16b(D-010 뒤, PC look-dev)**: 젖은 표면 머티리얼 레이어(메시일 때)·웅덩이·반사 튜닝·빗줄기 룩·성능 예산 확정. splat이면 젖음 표현은 파티클·조명·소리로 제한된다는 것을 스크린샷으로 확인해 D-015 (b) 범위를 다시 정한다.
- **착수 시점**: 16a는 V-13(WP-14a)·V-14(WP-15a) PC 검증이 끝나 시간대·세이브 계약이 안정된 뒤, 클라우드 여유가 있을 때. 지금은 착수하지 않는다(Phase 1 품질 게이트 D-010·V-08·V-12가 소유자·PC에 걸려 있고, 그 사이 클라우드 후보로 남겨 둔다).

## 2. 16a 설계 골격(초안 — 확정 아님)
1. **상태**: `EGolmokWeather { Clear, Overcast, Rain }` + `RainIntensity 0..1`. 모드는 WP-14a와 같은 형식으로 `fixed`(콘솔/ini 고정)·`scripted`(JSON 시퀀스 재생, 시연용)만 두고, 무작위/실시간 기상 연동은 하지 않는다.
2. **JSON 단일 소스** `Config/Golmok/weather_presets.json`(schema 1): 날씨별 *조명 수정자* — `lighting_presets.json`의 키(`lux`·`sky`·`fog`·`fog_height_falloff`·`kelvin`·`exposure_bias`·`volumetric`)에 곱셈/가산 계수를 적용한다. 시간대 프리셋 값은 바꾸지 않는다(WP-05 규칙 유지). 수정자는 `GolmokTimeOfDay`의 평가 결과 뒤에 한 단계로 끼운다(`ApplyState` 직전, 보간·hold와 독립). Python `lighting_presets.py`와 같은 파서 규칙(schema·타입·범위·미지 키 오류).
3. **빗줄기**: Niagara 시스템 1개(카메라 추종 박스 이미터, 강도 = `RainIntensity`). 프로젝트에 Niagara 플러그인이 아직 없다(uproject `Plugins`: EnhancedInput·PythonScriptPlugin·EditorScriptingUtilities·AndroidFileServer) — 플러그인 활성화는 `Golmok.uproject`·`Build.cs` 변경이라 착수 세션이 별도 커밋으로 하고, 에셋은 에디터 Python으로 생성 가능한 최소 구성(스프라이트·중력·수명)만 둔다. 카메라 근처 빗방울 화면 효과는 16b.
4. **젖음 계약**: `UMaterialParameterCollection` `MPC_GolmokWeather`에 `Wetness`·`RainIntensity`(0..1)·`PuddleLevel`. 16a는 값만 쓴다. 16b가 메시 머티리얼(`M_ZoneScan*`)에 바인딩한다. splat 표현이면 바인딩 대상이 없고 값은 무시된다 — 계약은 그대로 둔다.
5. **이벤트 계약(WP-13 오디오 레인용)**: `AGolmokTimeOfDay`와 같은 방식의 네이티브 멀티캐스트 `OnWeatherChanged(EGolmokWeather, float Intensity)`를 `Weather/GolmokWeatherSubsystem`(월드 서브시스템)에 둔다. Audio 레인은 `outdoor_rain` 상태(빗소리 베드, 실내 우선 규칙 그대로)와 발소리 세트 `wet`(선택)을 이벤트로 붙인다 — Audio 코드는 Astra 레인이므로 계약만 정하고 구현은 Astra 과제로 배정한다.
6. **세이브**: WP-15a `FGolmokSaveTimeOfDay`와 나란히 `FGolmokSaveWeather { uint8 State; float Intensity; }`를 추가(`SaveSchemaVersion` 유지, 필드 추가만; 구 세이브는 Clear).
7. **콘솔·HUD**: `golmok.weather clear|overcast|rain [intensity]|status`, HUD `weather:` 줄(Debug 훅 블록). 포토 모드 중 상태 변경은 허용하되 파티클은 정지 시간 규칙을 따른다(WP-12 GamePause).
8. **테스트**: 순수 헤더 `Weather/GolmokWeatherMath.h`(수정자 적용·강도 램프) g++ 교차검증, UE 자동화 `Golmok.Weather.Modifiers`(시간대 4종 × 날씨 3종 값 검사)·`Golmok.Weather.Events`(이벤트 1회·세이브 왕복) → 총수 +2.
9. **하지 않는 것(16a)**: 젖은 표면·웅덩이·반사, 눈, 실시간 기상 API, 바람/천둥, 날씨 전환 연출(페이드는 조명 수정자 보간 2 s로 갈음).

## 3. 의존·리스크(메모)
- **D-010**: 16b 전체. 16a는 무관.
- **R5(흐린 날 촬영 텍스처)**: Rain·Overcast는 흐린 촬영 텍스처와 잘 맞고, Clear 강한 태양이 오히려 부자연스럽다는 것이 D-015 리스크였다. 16a의 조명 수정자는 이 방향(흐림/비가 기본, 맑음은 약하게)으로 잡는다.
- **성능**: 볼류메트릭 안개 + 빗줄기 + (16b) 반사가 RTX 5060 1080p 30 fps 하한에 부담 — 16a 런북에 `stat gpu` fixed vs rain 비교 단계를 넣고, 16b에서 Lumen Lite(5.8 Beta) 채택 여부를 별도 결정.
- **레인**: `Weather/`는 새 Claude 레인, Audio 훅 구현은 Astra 레인(과제 배정), `Lighting/` 수정은 수정자 삽입 지점 한 곳(훅 블록 아님, Claude 레인).

## 4. 다음 단계
- 16a 착수 결정 시: 이 메모 §2를 "설계 (확정)"으로 승격(Fable), DEVELOPMENT-PLAN §5.1 행·STATUS 행 추가, Opus ultracode 세션 카드, 런북 V-15.
- 그 전에 필요한 것: V-13·V-14 통과(시간대·세이브 계약 안정), Astra 오디오 레인의 `outdoor_rain` 상태 수용 여부 확인(이슈 #30).
