# WP-06 — UE Python 에디터 자동화 2차

상태: ⚪ 대기 · 담당: 클라우드 Claude 세션(**Fable 5.1 ultracode**, 모델 정책 DEVELOPMENT-PLAN §7.4) · 의존: WP-03, WP-05 · 검증: G2/G3(`runbooks/pc-verify-wp06.md`, `runbooks/pc-spike.md`)

## 목표
후처리 결과(WP-03)를 에디터에 넣고 Zone 액터(WP-04)를 배치하는 일, 실내 서브레벨·포털 준비, 스파이크 1.1 측정을 **한 줄 명령**으로 만든다. `unreal` API 호출은 얇게, 계산은 순수 함수로 분리해 클라우드에서 테스트한다.

## 배경
- 기존 `basemap_import.py`(임포트 태스크, 축·단위 측정, Nanite, 충돌), `materials.py`(절차적 머티리얼), `viewpoints.py`, `lighting.py`
- `research/07` §3: 8K UDIM 여러 장 → **Virtual Texture**로 임포트. UE UDIM 규약: 텍스처 파일명 `<name>.1001.png` 형식이면 임포트 시 하나의 UDIM VT로 묶인다[2차: 세션이 공식 문서 확인 후 인용].
- WP-02 스펙 UE 매핑 규약, WP-03 `chunk_manifest.json`, WP-04 `AGolmokZone`/`AGolmokGeoOrigin`, WP-05 `AGolmokPortal`.

## 산출물 (`unreal/Golmok/Content/Python/golmok/`)
1. `_pure.py`(또는 `zone_paths.py`): unreal 비의존 순수 함수 — 에셋 경로 규약(`asset_paths(zone_id, version, chunk_id)`), UDIM 파일명 파싱·검증(`udim_tile_of("T_alley.1002.png") -> 1002`), chunk_manifest → 임포트 계획(dict), 컨택트 시트 HTML 생성. **`tools/tests/test_ue_python_pure.py`**에서 `sys.path`에 Content/Python을 넣고 가짜 `unreal` 모듈(`types.ModuleType`)로 import 되게 테스트.
2. `zone_import.py`: `run(zone_dir, version=None)` — manifest·chunk_manifest 읽기 → 텍스처(UDIM) 임포트(VT 켬, sRGB, 압축 기본) → 마스터 머티리얼 `M_ZoneScan`(materials.py 방식: BaseColor VT 샘플, Roughness 상수 0.8, Normal 없음) 1회 생성 → 청크당 `MI_<chunk_id>` → 청크 메시 임포트(Nanite 켬, 축·단위는 basemap_import의 측정 함수 재사용) + 머티리얼 할당 → 충돌 메시 임포트(complex-as-simple, Nanite 끔) → blockers.glb 임포트 → manifest.json을 `Content/Golmok/Zones/<id>/v<ver>/`로 복사 → `AGolmokGeoOrigin` 확인·생성 → `AGolmokZone` 액터 배치(없으면 스폰) → `RebuildInEditor()` 호출 → 로그 요약. 실패 지점마다 명확한 에러 메시지.
3. `interior_setup.py`: `run(zone_dir)` — 실내 Zone(kind=interior)용: 서브레벨 `L_<zone_id>` 생성(`unreal.EditorLevelUtils.create_new_streaming_level` 또는 동등 API), 그 안에 청크·충돌 배치(zone_import 재사용), 실내 PostProcessVolume(프리셋 interior), 퍼시스턴트 레벨에 `AGolmokPortal` 배치(parent_zone의 `portals[]` 기준, 양방향 2개), 저장.
4. `spike_runner.py`: `prepare(level)`(시점 10곳 저장 안내·검증), `capture_all(tags=["a","b","c","ac"], presets=[...])`(viewpoints.capture 반복 + 태그별 Zone 레이어 토글: `AGolmokZone.SetVisualVisible` 및 XGRIDS/Cesium 액터는 **이름 규약(`Spike_b_*`, `Spike_c_*`)으로 찾아 가시성 토글**), `contact_sheet(tags, presets)` → `Saved/Screenshots/Golmok/contact_sheet.html`(원본 사진 열 포함 옵션), `report_template()` → `research/08`의 표를 채우기 쉬운 마크다운 조각 출력.
5. `basemap_import.py` 보강: 배치한 타일 액터에 태그 `GolmokBasemap`과 `tile:<id>` 추가(WP-04 런타임 숨김용), `AGolmokGeoOrigin` 생성·갱신(Cesium georeference와 병행).
6. `synthetic_zone.py`(WP-04/05에서 만든 것) 정리: `run(interior=False)` 옵션 통일.
7. 런북:
   - `docs/runbooks/pc-verify-wp06.md`: 합성 청크(OBJ+PNG UDIM 3장을 `tools/scripts/make_synthetic_zone.py`로 생성 — **이 스크립트도 이 WP 산출물**, 클라우드에서 실행·테스트 가능) → `zone_import.run` → 에디터에서 청크·머티리얼·충돌 확인 → `interior_setup.run` → 포털 왕복.
   - `docs/runbooks/pc-spike.md`: **스파이크 1.1 전체 절차**(실촬영 → 블러 → RealityScan 정렬·메시·UDIM 내보내기 설정값 → COLMAP/XMP 내보내기 → Postshot 학습 설정(D-006 원칙) → `golmok-mesh`/`golmok-splat` → `zone_import` → (b) Cesium 타일셋 로드 (c) XGRIDS 임포트 → `spike_runner.capture_all` → `golmok.path play --csv` → `golmok-perf` → `research/08` 채우기 → D-010 결정 회의). 각 단계 예상 소요 시간과 실패 시 대안.

## 완료 기준
- `pytest` 통과(순수 함수·합성 생성 스크립트), CI 초록.
- 런북 2개 완비, STATUS `🟡`.

## 주의
- 에디터 Python API 이름은 5.8에서 바뀌었을 수 있다. 확신 없는 호출은 `hasattr` 분기 + 명확한 에러 메시지로 감싸고, 런북 "불확실 API" 목록에 적는다.
- 텍스처 임포트 옵션(VT, UDIM)은 `unreal.TextureFactory`/`AssetImportTask.options`로 설정. 안 되면 임포트 후 `texture.set_editor_property("virtual_texture_streaming", True)`로 후처리.

## 결과
(세션이 작성)
