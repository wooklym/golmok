# WP-06 — UE Python 에디터 자동화 2차

상태: 🟢 완료(V-04 2026-09-28, [#41](https://github.com/wooklym/golmok/pull/41); 후속 V-04b 2026-09-29·V-04c 2026-10-04 PC 확인 🟢, 아래 "병합 기록"·"결과") · 남은 PC 확인: Full Precision UV([#107](https://github.com/wooklym/golmok/pull/107), V-17 §3·V-05 S7), 태그 판정 뒤 UDIM 팩 폴백([#122](https://github.com/wooklym/golmok/pull/122) 리뷰 (B)) — 이전: 🟡 코드 완료·PC 검증 대기 · 담당: 클라우드 Claude 세션(**Fable 5.1 ultracode**, 모델 정책 DEVELOPMENT-PLAN §7.4) · 의존: WP-03, WP-05 · 검증: G2/G3(`runbooks/pc-verify-wp06.md`, `runbooks/pc-spike.md`)

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

## 설계 (확정, 2026-09-24)

근거: `docs/plan/WP-06-ue-python-automation.md` 산출물 1~7, 오케스트레이터 브리프(하드 팩트 1~14, 애드덤·`citations.md`의 5.8 확인 API), `docs/spec/zone-manifest.md` §1·§2·§5, WP-03 "다음 WP에 알릴 것", WP-04·05 "WP-06에 알릴 것", `pc-setup.md`(백그라운드 PIE ≈ 8 fps), `research/08`(-game -RenderOffscreen 기준선). 세 후보 설계(API 현실성 A / 데이터·경로 B / 검증 가능성 C)를 심판 2명이 채점해 **C(검증 가능성)안을 기준**으로 A·B의 장점을 이식하고 심판이 지적한 결함을 전부 닫은 최종안이다(§9). 선택지는 남기지 않았다. 식별자·로그 문자열·파일 배치는 이 문서가 정본이며, 구현 세션은 모듈별로 이 문서만 보고 구현한다.

### 0. 확정 결정 요약
| # | 주제 | 결정 | 근거·대안 |
|---|---|---|---|
| D1 | 순수 모듈 | `golmok/_pure.py` 하나에 순수 함수 전부(경로 규약·UDIM·MTL·임포트 계획·bbox·OBJ/GLB 사전변환·로그 포맷·경로 JSON·명령줄·PowerShell·컨택트 시트·리포트). `unreal`·`numpy`·`golmok_tools` import 금지(소스에 `unreal` 문자열 자체가 없음, 테스트가 검사). 스펙 이름 `asset_paths()`도 제공 | 테스트 대상 한 파일. `zone_paths.py` 분리 안 함 |
| D2 | 어댑터 모듈 | **새 어댑터 모듈 없음**. `zone_import`→`synthetic_zone as sz`, `basemap_import as bm`; `interior_setup`→`zone_import`, `sz`; `spike_runner`→`viewpoints`, `lighting`, `_pure`. `basemap_import._set_geo_origin`은 함수 안에서 `from . import synthetic_zone`(지연) → 순환 없음(sz는 모듈 상단에서 bm을 import) | A·B의 `zone_editor/editor_util` 이동은 V-03 런북 기대 로그·테스트를 흔든다 |
| D3 | OBJ/GLB 기하 경로 | **항상 사전변환 사본**을 임포트한다: 프로브로 임포터 매핑 `(s, M)` 측정 → `A=(sM)⁻¹·TARGET`로 `v`(위치)·`vn`(법선은 `U=A/k`)을 다시 쓰고 `det(A)<0`이면 `f` 정점 순서 반전 → 임포트 → `get_bounding_box()`를 `bbox_enu`의 UE 변환값과 대조(허용 `max(5 cm, 0.5 %)`). GLB도 같은 방식(`pretransform_glb`: POSITION·NORMAL 재작성 + `G·A·G⁻¹` 켤레, det<0이면 인덱스 삼각형 반전, accessor min/max 갱신, 메시·노드 이름 = 목표 에셋 이름). 임포트 옵션의 회전·스케일에는 기대지 않는다 | A의 rotator/음수 스케일 경로는 검증 불가라 채택 안 함(§9 A-7) |
| D4 | OBJ 임포터 사다리 | 프로브 1회로 임포터를 확정하고 캐시한다: `fbx`(`task.factory=unreal.FbxFactory()` + `FbxImportUI` 머티리얼·텍스처 off) → 실패 시 `interchange`(팩토리 없음 + `InterchangeGenericAssetsPipeline` 머티리얼·텍스처 off) → 실패 시 `legacy_flag`(콘솔 `Interchange.FeatureFlags.Import.OBJ 0` 뒤 팩토리 없음 + `FbxImportUI`). 결과 route와 `(s, M)`을 `<Saved>/Golmok/zone_import/importer_mapping.json`(엔진 버전 키)에 캐시, `remeasure=True`로 갱신. 어느 route든 기하는 D3 | A 이식(§9 그래프트 A-3·A-4) |
| D5 | 텍스처(UDIM) | 그룹의 최소 타일 파일(원본 위치, `<base>.1001.png`)을 `AssetImportTask`(`destination_name=T_<base>`, ~~스크래치 `Textures/_import`에 임포트 후 이동(V-03, 런북 #37)~~ → **수정(V-04b F3·R69-11)**: 규약 경로 `Textures/`에 `replace_existing=True`로 제자리 임포트(재임포트 때 같은 에셋 — MI 참조 유지), 다른 이름으로 놓이면 옮기고 WARNING, 옮기지 못해 실패하면 그 실행에서 임포트된 사본을 지우고 못 지운 것은 WARNING 뒤 다음 실행 cleanup 단계(`_cleanup_folder`)가 지운다, 옵션 `material_pipeline.texture_pipeline.import_udi_ms=True`(단일 텍스처는 False — 런북 #38)·`material_pipeline.import_materials=False`, hop마다 hasattr)로 임포트 → `srgb=True`, `virtual_texture_streaming=True` 강제 → 크기로 병합 판정 → 병합 안 됐으면 타일 각각 `Textures/_tiles/`에 임포트 후 `UDIMTextureFunctionLibrary.make_udim_virtual_texture_from_texture2_ds`로 묶고 `_tiles` 삭제 → 그것도 없으면 첫 타일 + WARNING. UDIM 파일명은 공식 규약 `BaseName.####.ext`만 인정(1001..1999), `_####`는 경고 후 단일 텍스처 | citations UDIM 인용; `_####`는 인정하지 않음(심판 불일치 → §9). 수정(리뷰 L2-02): 엔진 규칙은 `UTextureFactory::UdimRegexPattern` 기본값 `(.+?)[._](\d{4})$`(≥ 1001)로 확인 — 그 이름의 단일 텍스처는 경고 + UDIM 감지 off로 임포트 |
| D6 | 머티리얼 | `M_ZoneScan`(VT 샘플러, **기본 텍스처 = 그 실행에서 처음 임포트한 VT 텍스처**)은 첫 텍스처 임포트 뒤에 만든다. VT를 못 켠 텍스처가 하나라도 있으면 `M_ZoneScan_NoVT`(일반 샘플러)도 만들고 그 텍스처의 MI는 NoVT를 부모로. 인스턴스는 **MTL 머티리얼 이름당** `MI_<safe(material)>`(zone 폴더 안). 슬롯 할당: 정확 이름 → 대소문자 무시 → OBJ `usemtl` 등장 순서(스트리밍 스캔). `chunk_manifest.materials`(정렬 집합)는 순서 근거로 쓰지 않는다 | VT 샘플러+비VT 기본 텍스처 = 컴파일 오류(§9 B-3) |
| D7 | 충돌 | `layers.collision.chunks`가 있으면 **그것만** `SM_<zone_id>_collision_<chunk_id>`로 임포트(`collision_mode="chunks"`; C++는 chunks가 있으면 전체 파일을 읽지 않는다), 없으면 `collision.glb` 하나(`"single"`). complex-as-simple, Nanite off | B 이식 |
| D8 | Content 복사 | **정확히 두 파일**: `manifest.json`, `layers.blockers.uri`(있으면). 에셋 임포트가 모두 성공한 **뒤**에 복사. `chunk_manifest.json`·OBJ·MTL·PNG·GLB·`blockers.glb`는 절대 복사·임포트하지 않는다(UFS 스테이징 폴더) | 하드 팩트 1, B 이식 |
| D9 | 포털 | Python은 `AGolmokPortal`을 놓지 않는다. `interior_setup`은 부모·실내 manifest의 왕복(같은 점 ≤ 5 cm, 반대 yaw ≤ 1°)을 순수 함수로 검사하고 실패하면 **임포트·스폰 0회로 중단**(오류; 부모 액터의 `version`을 읽으려 레벨만 연다 — 리뷰 R1-04) | WP-05 인계; B의 "경고" 대신 오류(§9) |
| D10 | 실내 서브레벨 | `L_<zone_id>` 안에는 `Interior_Light_<zone_id>` PointLight 1개(레벨 좌표, 태그 `GolmokInteriorSetup`)만. PPV·DirectionalLight·AGolmokZone·AGolmokPortal 없음. 재실행은 태그 `GolmokInteriorSetup` 액터만 지우고 다시 만든다(손으로 놓은 소품 보존). `GolmokLighting` 태그는 붙이지 않는다(프리셋 대상 아님) | WP-05 인계 + B §6-3(§9) |
| D11 | 무인 캡처 | **PIE 상태기계**(`spike_runner.capture_all(mode="pie")`, slate post-tick, 시간 기반 대기): `LevelEditorPlaySettings` 새 창 1280×720 → `editor_request_begin_play()` → PlayerController 폴링 → `golmok.hud 0` → 레이어 → 프리셋마다 `golmok.tod` → 시점마다 2샘플 **600 s dwell 경로** `golmok.path play vp_<name>`(C++가 캐릭터를 숨기고 카메라를 정확히 그 포즈에 둠) → `golmok.screenshot <tag> <name>` → 파일 대기(`<name>.png` 또는 `<name>00000.png`) → **항상** `golmok.path stopplay` → 다음. 태그마다 PIE 1회. C++ `golmok.later`는 추가하지 않는다 | 애드덤 (a); A·B의 CameraActor/폰 텔레포트 기각(§9) |
| D12 | 성능 측정 | **`-game`이 정본**: `-game -RenderOffscreen -ResX -ResY -ForceRes -ExitAfterCsvProfiling -unattended -nosplash -ExecCmds="golmok.hud 0, golmok.tod <p>, golmok.path play <walk> --csv" -abslog=<log>`(**`-csvCaptureFrames` 없음**: 경로가 CsvProfile Start/Stop을 낸다). 레이어는 `save_layer_levels()`가 만든 `L_Spike_<tag>` 맵으로. 경로 JSON은 실행 전에 Saved 후보 **둘 다**의 `Golmok/Paths/`에 복사, CSV도 둘 다에서 찾는다. `.ps1`이 프로세스를 타임아웃 감시하고 로그의 `GolmokDebugSubsystem: csv:` 줄을 확인한다. PIE `perf_all()`은 **참고치**(편집기 오버헤드·백그라운드 8 fps) | research/08 방법; A 이식(Saved 후보) |
| D13 | 시점·프리셋 | 시점 10개 이름 고정 `far_01..03 mid_01..04 near_01..03`(research/08 조건 3/4/3). 얇은 구조물=`mid_04`, 이음새=`mid_02`, 프리셋 반응=`mid_01`, 캐릭터 그림자=`near_03`(**유인 PIE 걷기에서 채점**: 재생 중 캐릭터는 숨김). 기본 프리셋 `("overcast_morning","clear_noon","golden_evening")` = cycle − night; night는 인자로만 | research/08 조건 |
| D14 | 스크린샷 폴더 | 태그 그대로 `Saved/Screenshots/Golmok/<tag>/<preset>/<name>.png`(`a b c ac`); `spike_` 접두 없음(스펙 경로·C++ 규약과 동일) | §9 |
| D15 | 합성 zone 생성기 | `tools/scripts/make_synthetic_zone.py --out <dir>`: RealityScan 흉내 원본을 `<out>/recon/<id>/`에 쓰고(텍스처가 **버전 폴더 밖**), `golmok_tools.mesh.cli.main`으로 chunk(15 m 격자) → collision(`--per-chunk`, `--no-snap-ground`) → blockers를 **실제 파이프라인**으로 돌려 `<out>/zones/<id>/v1/`을 만든다. 파사드는 얇은 벽(0.2 m) + 문 구멍·창 구멍, `--interior`는 문 뒤 방 zone(겹침 없음). `expected.json`이 런북·테스트 숫자의 정본. PNG는 순수 파이썬(zlib+struct), 타일 번호를 5×7 비트맵 글꼴로 그린다 | B·C 이식; A·C의 실내 결함 해소(§9) |
| D16 | 로그·런북 드리프트 | 로그 형식은 `_pure.LOG` 한 곳. `test_log_formats_are_quoted_in_runbook`(양방향)과 `test_no_unreal_api_outside_touchpoint_list`(모듈의 `unreal.X`가 런북 §7 표 또는 KNOWN_OK에 있어야 함)가 문서와 코드를 묶는다 | C + A 이식 |
| D17 | 가짜 unreal | `tools/tests/fake_unreal.py`: 인메모리 레지스트리 + 실제 파일을 파싱하는 가짜 임포터 + 호출 기록 + 가짜 시계. 기존 스텁 모듈 객체(`sys.modules["unreal"]`)에 **속성을 덮어쓰고 테스트 뒤 복원**(function-scope) | 다른 테스트와 같은 객체 공유 |
| D18 | 기존 모듈 변경 최소 | `synthetic_zone.run` 시그니처 불변. `_spawn_interior_sublevel(..., specs=None, delete_tag=None)`, `register_interior_sublevel(zone_id=…, version=…)`만 일반화. `viewpoints.capture(..., on_done=None)`. `materials.build_zone_scan_material/zone_scan_instance` 추가. `basemap_import.run`에 `_set_geo_origin` 한 줄 | 산출물 5·6 |

### 1. 파일 목록
| 파일 | 상태 | 내용 |
|---|---|---|
| `unreal/Golmok/Content/Python/golmok/_pure.py` | 신규 | §3-1 순수 함수·상수·`LOG` |
| `unreal/Golmok/Content/Python/golmok/zone_import.py` | 신규 | §3-2 `run`, `import_assets`, 어댑터 |
| `unreal/Golmok/Content/Python/golmok/interior_setup.py` | 신규 | §3-3 |
| `unreal/Golmok/Content/Python/golmok/spike_runner.py` | 신규 | §3-4 |
| `unreal/Golmok/Content/Python/golmok/materials.py` | 수정 | `build_zone_scan_material(default_texture, vt=True, overwrite=False)`, `zone_scan_instance(texture, parent, path)` (§3-6) |
| `unreal/Golmok/Content/Python/golmok/basemap_import.py` | 수정 | `_set_geo_origin(origin)` + `run()` 한 줄, docstring `--exclude` (§3-5) |
| `unreal/Golmok/Content/Python/golmok/synthetic_zone.py` | 수정 | `_spawn_interior_sublevel(..., specs=None, delete_tag=None)`, `_spawn_sublevel_actor`가 `spec["tags"]` 적용, `register_interior_sublevel(zone_id=INTERIOR_ZONE_ID, version=INTERIOR_VERSION)`, docstring (§3-6) |
| `unreal/Golmok/Content/Python/golmok/viewpoints.py` | 수정 | `capture(tag, names=None, presets=None, game_view=True, on_done=None)`; `_Capture._finish`가 `on_done(saved, missing)` 호출 |
| `tools/scripts/make_synthetic_zone.py` | 신규 | §3-7 |
| `tools/tests/fake_unreal.py` | 신규 | §5-0 (헬퍼, 테스트 아님) |
| `tools/tests/test_ue_python_pure.py` | 신규 | §5-1 |
| `tools/tests/test_make_synthetic_zone.py` | 신규 | §5-2 |
| `tools/tests/test_ue_python_zone_import.py` | 신규 | §5-3 |
| `tools/tests/test_ue_python_interior_setup.py` | 신규 | §5-4 |
| `tools/tests/test_ue_python_spike_runner.py` | 신규 | §5-5 |
| `tools/tests/fixtures/ue/chunk_manifest_min.json` | 신규(≈1 KB) | WP-03 형식 chunk_manifest 예제(청크 2·MTL 머티리얼 2·타일 3·`missing` 빈 것); 순수 테스트 입력 |
| `docs/runbooks/pc-verify-wp06.md` | 신규 | §6-1 |
| `docs/runbooks/pc-spike.md` | 신규 | §6-2 |
| `docs/plan/WP-06-ue-python-automation.md` "결과", `docs/plan/STATUS.md`, `docs/ROADMAP.md` | 수정 | 세션 규칙(DEVELOPMENT-PLAN §7.2). "판단한 것" 항목은 §8 끝에 목록 |

에디터 Python 모듈 규칙(테스트 `test_modules_import_with_empty_stub`가 강제): 모듈 import 시점에 `unreal.X`를 만지지 않는다(기본 인자에 `unreal.Vector` 금지). `_pure.py`는 표준 라이브러리(`json math os re struct zlib html posixpath time`)만. 새 의존성 없음.

### 2. 규약
- **좌표**: zone-local ENU(m, Z-up) → UE cm `TARGET = diag(100, −100, 100)`(X=동, Y=남, Z=위). 청크 정점은 임포트 뒤 zone-local UE cm; 액터 배치는 C++ `AGolmokZone`이 한다(Python은 `rebuild_in_editor()`만 호출). GLB는 glTF Y-up `(동, 위, −북)`; ENU→glTF `G: (x, y, z) → (x, z, −y)`.
- **에셋 경로**(스펙 §5 = `GolmokZoneManifest.cpp`): 폴더 `/Game/Golmok/Zones/<zone_id>/v<n>`, 청크 `SM_<chunk_id>`, 충돌 `SM_<zone_id>_collision[_<chunk_id>]`, 서브레벨 `L_<zone_id>`, 텍스처 `…/v<n>/Textures/T_<safe(base)>`, 인스턴스 `…/v<n>/Materials/MI_<safe(material)>`, 마스터 `/Game/Golmok/Materials/M_ZoneScan`·`M_ZoneScan_NoVT`, 프로브 `…/v<n>/_probe`(끝나면 삭제). 오브젝트 경로 `<pkg>/SM_x.SM_x`.
- **파일(디스크→에디터)**: `zones/<id>/v<n>/{manifest.json, visual/<chunk>.obj, visual/<mtl>, visual/chunk_manifest.json, collision.glb, collision/<chunk>.glb, blockers.json}` 읽기; Content에는 `Golmok/Zones/<id>/v<n>/{manifest.json, blockers.json}`만 쓰기; 작업 파일은 `<Saved>/Golmok/zone_import/<id>/v<n>/{visual/SM_<chunk>.obj, visual/<mtl>, collision/*.glb, _probe.obj, _probe.glb, import_result.json}`, 캐시 `<Saved>/Golmok/zone_import/importer_mapping.json`; 스파이크 `<Saved>/Golmok/spike/{run_game_perf.ps1, csv/, report_template.md, game_<tag>_<preset>_<walk>.log}`, 경로 `<Saved>/Golmok/Paths/vp_<name>.json`, 스크린샷 `<Saved>/Screenshots/Golmok/<tag>/<preset>/<name>.png`, 컨택트 시트 `<Saved>/Screenshots/Golmok/contact_sheet.html`.
- **이름 규칙**: `zone_id` `^z_[a-z0-9]+(_[a-z0-9]+)*$`; 청크·포털·blocker id `^[A-Za-z0-9][A-Za-z0-9_]*$`; 콘솔 이름(태그·시점·경로) `^[A-Za-z0-9_-]{1,64}$`(C++ `IsValidPathName`); `asset_name_safe`: `[^A-Za-z0-9_]`→`_`, 선행 숫자면 `_` 접두, 빈 문자열 ValueError.
- **UDIM**: 파일명 `<base>.<tile>.<ext>`(tile 1001..1999)만 UDIM; `u=(t−1001)%10`, `v=(t−1001)//10`; 캔버스 `(max u+1, max v+1)`. MTL `map_Kd`: 상대경로는 **MTL 파일 폴더 기준**, 절대경로 그대로, `<UDIM>`(대소문자 무관) 토큰은 4자리 glob, 명시 타일 한 장이면 같은 폴더 형제 타일 전부가 한 세트(UE와 같음).
- **로그**: 모든 로그는 `_pure.LOG[key]`를 `fmt()`로 포맷해 `unreal.log/log_warning/log_error`로. 접두 `zone_import:`, `interior_setup:`, `spike_runner:`, `basemap_import:`. 런북의 기대 로그는 항상 ```` ``` ```` 블록 안(드리프트 테스트 대상).
- **오류**: `ZoneImportError(step, message)`(RuntimeError 서브클래스, `str()` = `fmt("zi.error", …)`). 계획 단계 오류는 에디터 호출 0회로 끝난다. 부분 임포트된 에셋은 남긴다(재실행이 `replace_existing=True`로 덮음).
- **hasattr 분기**: §7 표의 API는 전부 `hasattr` 분기 + `unreal.log_warning(fmt("zi.warn"/"sr.warn", …))`(메시지에 `runbook #n`)로 대안 경로.
- **Windows·CI**: `pathlib`, 파일 `encoding="utf-8"`, 텍스트 출력 `newline="\n"`, 서브프로세스 `encoding="utf-8"`, stdout ASCII만, argv는 짧게(경로 1개), 큰 입력은 파일. 테스트는 비ASCII 경로(`"합성 zone"`)를 일부러 쓴다. mtime 해상도 → 파일 대기는 `requested_at − 1.0`.

### 3. 모듈별 API

#### 3-1. `_pure.py` (unreal 비의존)
파일 시스템 접근은 인자로 주입(`exists`, `listdir`, `isfile`, `isdir`, `read_text`, `read_bytes`)해 테스트가 파일 없이 돌린다. 모든 경로 문자열은 `'/'` 결합(`posixpath`) 후 호출자가 `os.path.normpath`.

```python
# ---- 상수 ----
ZONES_ROOT = "/Game/Golmok/Zones"
MATERIAL_DIR = "/Game/Golmok/Materials"                 # == materials.MATERIAL_DIR (테스트 비교)
MASTER_MATERIAL = f"{MATERIAL_DIR}/M_ZoneScan"
MASTER_MATERIAL_NOVT = f"{MATERIAL_DIR}/M_ZoneScan_NoVT"
CONTENT_ZONES_REL = "Golmok/Zones"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_]*$")
ZONE_ID_RE = re.compile(r"^z_[a-z0-9]+(_[a-z0-9]+)*$")
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
VERSION_DIR_RE = re.compile(r"^v([1-9][0-9]*)$")
UDIM_RE = re.compile(r"^(?P<base>.+)\.(?P<tile>1\d{3})\.(?P<ext>[A-Za-z0-9]+)$")     # 공식 규약 BaseName.####.ext
UDIM_SUSPECT_RE = re.compile(r"^(?P<base>.+)_(?P<tile>1\d{3})\.(?P<ext>[A-Za-z0-9]+)$")  # 경고만
UDIM_TOKEN_RE = re.compile(r"<udim>", re.IGNORECASE)
TARGET = ((100.0, 0.0, 0.0), (0.0, -100.0, 0.0), (0.0, 0.0, 100.0))   # == basemap_import.TARGET
PROBE_BOX = ((1.0, 2.0, 3.0), (5.0, 9.0, 15.0))                         # ENU m, 세 변이 모두 달라 순열·부호 모호성 없음
INTERIOR_SETUP_TAG = "GolmokInteriorSetup"
FORBIDDEN_SUBLEVEL_CLASSES = ("GolmokZone", "PostProcessVolume", "DirectionalLight", "GolmokPortal")
_MAP_KEYS = ("map_", "bump", "disp", "decal", "norm", "refl")          # == objio._MAP_KEYS
_MAP_OPTS = {"-blendu": 1, "-blendv": 1, "-bm": 1, "-boost": 1, "-cc": 1, "-clamp": 1, "-imfchan": 1,
             "-mm": 2, "-o": 3, "-s": 3, "-t": 3, "-texres": 1, "-type": 1}   # == objio._MAP_OPTS (테스트 동일성)
VIEWPOINT_NAMES = ("far_01", "far_02", "far_03", "mid_01", "mid_02", "mid_03", "mid_04", "near_01", "near_02", "near_03")
QUALITY_ROWS = (("원경", ("far_01", "far_02", "far_03")), ("중경", ("mid_01", "mid_02", "mid_03", "mid_04")),
                ("근경 0.5m", ("near_01", "near_02", "near_03")), ("얇은 구조물(전선·철망·난간)", ("mid_04",)),
                ("캐릭터 그림자가 바닥·벽에 떨어지는지", ("near_03",)), ("조명 프리셋 변경에 반응하는지", ("mid_01",)),
                ("이음새(청크·배경·메시↔splat)", ("mid_02",)))
COST_ROWS = ("처리 시간(재구성·학습·변환)", "수작업 시간", "라이선스·배포 조건")
TAGS = ("a", "b", "c", "ac")
TAG_COLUMNS = {"a": "(a) 메시 Nanite+Lumen", "b": "(b) Cesium splat", "c": "(c) XGRIDS LCC", "ac": "(a+c) 하이브리드"}
DEFAULT_PRESETS = ("overcast_morning", "clear_noon", "golden_evening")   # lighting cycle − night (research/08 조건)
PIE_WINDOW = (1280, 720)          # × ScreenshotMultiplier 2 = 2560×1440 = viewpoints.RES_X/RES_Y
DWELL_S = 600.0                   # dwell 경로 길이(백그라운드 PIE 8 fps에서도 경로가 먼저 끝나지 않게)
ENGINE_VERSION_KEY = "5.8"        # LOCALAPPDATA Saved 후보 폴더

# ---- 경로 규약 ----
def asset_folder(zone_id: str, version: int) -> str            # "/Game/Golmok/Zones/<id>/v<n>"
def chunk_asset(zone_id, version, chunk_id) -> str              # ".../SM_<chunk_id>"
def collision_asset(zone_id, version, chunk_id=None) -> str     # ".../SM_<zone_id>_collision[_<chunk_id>]"
def sublevel_package(zone_id, version) -> str                   # ".../L_<zone_id>"
def texture_asset(zone_id, version, base) -> str                # ".../Textures/T_<asset_name_safe(base)>"
def material_instance_asset(zone_id, version, material) -> str  # ".../Materials/MI_<asset_name_safe(material)>"
def content_manifest_rel(zone_id, version) -> str               # "Golmok/Zones/<id>/v<n>"  ('/' 구분, ContentDir 기준)
def asset_paths(zone_id: str, version: int, chunk_id: str | None = None) -> dict
    """스펙 산출물 1의 이름. {"folder", "chunk"(chunk_id 있을 때), "collision", "collision_chunk"(chunk_id 있을 때),
    "sublevel", "textures_folder", "materials_folder", "manifest_rel": "Golmok/Zones/<id>/v<n>/manifest.json", "probe"}.
    zone_id·chunk_id 규칙 위반은 ValueError."""
def asset_name_safe(text: str) -> str
def object_path(asset_path: str) -> str                         # "/Game/A/B" → "/Game/A/B.B"

# ---- UDIM ----
def udim_tile_of(filename: str) -> int | None      # "T_alley.1002.png"→1002, "x.png"→None, "a.1000.png"→None, "a.2001.png"→None, "a.1001.PNG"→1001, "a.b.1001.png"→1001(base "a.b"), "a_1002.png"→None
def udim_split(filename: str) -> tuple[str, int, str] | None       # (base, tile, ext) 또는 None
def udim_suspect(filename: str) -> bool                            # "a_1002.png" → True (경고용)
def udim_block_coords(tile: int) -> tuple[int, int]                # 1001→(0,0) 1002→(1,0) 1010→(9,0) 1011→(0,1) 1020→(9,1) 1999→(8,99); 1001..1999 밖 ValueError
def udim_canvas_blocks(tiles: list[int]) -> tuple[int, int]        # (max u+1, max v+1); [] → (1, 1)
def udim_group(map_path: str, listdir) -> dict
    """절대화된 map_Kd 경로 하나 → 세트. '<UDIM>' 토큰: 폴더를 listdir해 같은 base·ext(ext 대소문자 무시)의 4자리 파일을 모음.
    'name.1001.png' 명시: 그 파일의 세트(형제 타일 포함). UDIM 아님('name.png'): tiles=[].
    반환 {"base", "ext", "dir", "tiles": [정렬], "files": {str(tile): abs} | {"single": abs}, "anchor": abs(최소 타일 또는 단일 파일)}.
    같은 타일 번호 파일 둘(확장자 대소문자 차이)이면 ValueError("duplicate tile <n>"); 토큰인데 파일 0개면 tiles=[]·files={}·anchor=None."""

# ---- MTL ----
def split_map_line(line: str) -> tuple[str, str] | None     # objio.split_map_line과 같은 규칙(테스트가 같은 입력 10개로 대조)
def parse_mtl(text: str) -> dict[str, dict]                 # {material: {"map_Kd": "<쓰인 그대로>" | None, "Kd": [r,g,b] | None}}, newmtl 순서 유지, BOM 허용
def resolve_map_path(map_kd: str, mtl_dir: str) -> str      # 절대경로면 그대로, 아니면 posixpath.normpath(mtl_dir + '/' + map_kd) ('\\'→'/')
def mtl_with_absolute_textures(text: str, mtl_dir: str) -> str   # map_* 줄의 경로를 절대경로로(옵션 접두 유지), 나머지 줄 그대로, '\n' 종결

# ---- OBJ 스트리밍 ----
def obj_mtllibs(lines: Iterable[str]) -> list[str]          # 첫 'f ' 전까지의 mtllib 이름들(공백 포함 이름은 나머지 전체가 하나)
def usemtl_order(lines: Iterable[str]) -> list[str]         # usemtl 등장 순서(중복 제거), 전체 스캔(폴백에서만 호출)
def parse_obj_bounds(lines: Iterable[str]) -> tuple[tuple, tuple]   # 'v' 줄 min/max; v 없으면 ValueError
def probe_obj_text(box=PROBE_BOX) -> str                    # 8정점·12삼각형 박스 OBJ(머티리얼·vn 없음, 'o probe', vt 없음)

# ---- 계획 ----
def resolve_zone_dir(zone_dir: str, version: int | None, listdir, isdir, isfile) -> tuple[str, int]
    """(version_dir, version). zone_dir가 '.../v<n>'(manifest.json 있음)이면 그대로(version 지정 시 일치 검사);
    '.../<id>'면 version(None=manifest.json이 있는 최대 v<n>) 선택; '.../manifest.json' 경로면 그 폴더.
    오류(ValueError): "no v<n> folder with manifest.json under <dir>", "version <n> requested but <dir>/v<n>/manifest.json is missing",
    "<path> is not a zone folder (expected .../<zone_id>/v<n>)"."""
def import_plan(manifest: dict, chunk_manifest: dict | None, version_dir: str, *, exists, listdir, read_text) -> dict
    """§4-1의 dict. 예외를 던지지 않고 problems/warnings에 모은다. 규칙 §4-1."""
def plan_problems(plan: dict) -> list[str]                  # plan["problems"] (호출자 편의)
def slot_assignment(slot_names: list[str], wanted: dict[str, str], usemtl: list[str] | None) -> tuple[list[tuple[int, str]], list[str]]
    """[(slot_index, mi_name)], unmatched_slot_names. 정확 일치 → 대소문자 무시 → usemtl 순서(슬롯 i ↔ usemtl[i], wanted에 있을 때만)."""

# ---- bbox·좌표 ----
def expected_ue_bounds(bbox_enu) -> tuple[tuple, tuple]      # 8 꼭짓점에 TARGET, min/max 재정렬 (sz.expected_ue_bounds와 같은 값)
def bounds_error_cm(got, want) -> float                       # 6 성분 최대 절대차
def bounds_tolerance_cm(want) -> float                        # max(5.0, 0.005 * 최대 변 길이)
def measure_mapping(samples) -> tuple[float, float, tuple]    # basemap_import._measure_import_mapping의 순수 사본 (err, scale, M); 테스트 동일성
def resolve_geo_origin(arg, existing: tuple | None, manifest: dict, read_json) -> tuple[tuple[float, float, float], str]
    """arg None: existing 있으면 (existing, "kept"), 없으면 (manifest origin, "spawned from zone origin (zone at level origin)");
    "area": ((37.56, 126.923, 40.0), "spec area origin"); "zone": (manifest origin, "zone origin"); (lat, lon, h): (…, "given");
    문자열 경로: (<path>/manifest.json의 origin, "basemap <path>")."""

# ---- 사전변환 ----
def inverse_mapping_matrix(scale: float, m) -> tuple           # A = (s·M)⁻¹·TARGET = Mᵀ·TARGET/s (sz.pretransform_box와 같은 식)
def det3(a) -> float
def normal_matrix(a) -> tuple                                  # U = A / k, k = |A 첫 행| (A는 부호 순열의 스칼라 배)
def gltf_conjugate(a) -> tuple                                 # G·A·G⁻¹, G = ((1,0,0),(0,0,1),(0,-1,0))
def pretransform_obj_lines(lines: Iterable[str], a) -> Iterator[str]
    """'v x y z [w|r g b]' → A 적용('%.6f', 뒤 값 유지); 'vn x y z' → U 적용; det(A)<0이면 'f' 토큰 순서 반전(v/vt/vn 묶음 유지);
    'mtllib'·'usemtl'·'vt'·'o'·'g'·'s'·주석·빈 줄은 바이트 그대로. 줄 끝(\\n, \\r\\n) 보존."""
def pretransform_obj_file(src: str, dst: str, a, mtllib: str | None = None) -> int
    """스트리밍(줄 단위, 메모리 상수). mtllib가 주어지면 'mtllib' 줄을 'mtllib <mtllib>'로 바꿔 쓴다. 반환 v 개수.
    open(encoding='utf-8', errors='surrogateescape', newline='')."""
def glb_bounds_enu(data: bytes) -> tuple[tuple, tuple]         # 모든 primitive POSITION accessor의 float32 → ENU(x, −z, y) min/max
def glb_triangle_count(data: bytes) -> int                     # indices accessor count 합 / 3
def pretransform_glb(data: bytes, a_enu, rename: str | None = None) -> bytes
    """모든 primitive의 POSITION(float32 VEC3)을 G·A·G⁻¹로, NORMAL을 G·U·G⁻¹로 다시 쓰고 해당 accessor의 min/max 갱신(있는 것만).
    det(A)<0이면 indices(uint16/uint32) 삼각형마다 [i0,i2,i1]. rename이 있으면 모든 mesh.name·node.name = rename.
    JSON 청크 길이가 바뀌면 4바이트 패딩(공백)·헤더 길이 재계산. 공유 bufferView·byteStride는 ValueError."""
def png_size(head: bytes) -> tuple[int, int]                   # 시그니처+IHDR 24바이트 → (w, h); 아니면 ValueError

# ---- 로그 ----
LOG = {...}   # §4-6 그대로(문자열 정본)
def fmt(key: str, **kw) -> str            # LOG[key].format(**kw); 없는 키 KeyError
def log_prefixes() -> dict[str, str]      # key → 첫 '{' 앞 고정 접두

# ---- 결과 ----
def result_json(plan, mappings: dict, assets: list[dict], warnings: list[str], route: str) -> dict   # §4-3
def importer_cache_valid(cache: dict | None, engine_version: str) -> bool   # cache and cache.get("engine") == engine_version and "obj" in cache and "glb" in cache
def summary_lines(result: dict) -> list[str]                    # 에셋 한 줄씩(런북 §6-1 체크 순서: chunk → collision → texture → material → file)

# ---- 실내 ----
def portal_pair(parent: dict, interior: dict) -> tuple[dict, dict]   # parent.portals 중 to_zone==interior.zone_id 하나, interior.portals 중 to_zone==parent.zone_id 하나; 0개·2개 이상 ValueError
def enu_to_ecef(transform16: list[float], p) -> tuple               # 4×4 row-major · (x, y, z, 1)
def heading_ecef(transform16: list[float], yaw_deg: float) -> tuple # R·(cos, sin, 0) 단위벡터
def portal_round_trip_check(parent: dict, interior: dict, max_dist_m=0.05, max_yaw_err_deg=1.0) -> dict
    # {"parent_portal", "interior_portal", "dist_m", "yaw_err_deg", "ok"}; yaw_err = |180 − angle(h_parent, h_interior)|
def interior_sublevel_specs(interior_manifest: dict) -> list[dict]
    # [{"label": f"Interior_Light_{zone_id}", "kind": "point_light", "location_cm": (100·cx, −100·cy, min(250.0, 100·(zmax−0.5))),
    #   "intensity_cd": 3000.0, "kelvin": 3000.0, "tags": ["GolmokInteriorSetup"]}]  (visual.chunks bbox 합집합 중심, 실내-local UE cm)

# ---- 스파이크 ----
def missing_viewpoints(saved: dict, names=VIEWPOINT_NAMES) -> list[str]     # 정렬
def layer_state(tag: str) -> dict          # {"zone_visual": tag in ("a","ac"), "spike_b": tag=="b", "spike_c": tag in ("c","ac")}; 그 외 ValueError
def spike_actor_group(label: str) -> str | None     # "Spike_b_xgrids"→"spike_b", "Spike_c_tiles"→"spike_c", "Spike_x"→None (접두 규약 Spike_b_*, Spike_c_*)
def capture_jobs(tags, presets, names) -> list[tuple[str, str, str]]   # tag-major → preset → name
def screenshot_path(saved_dir: str, tag: str, preset: str | None, name: str) -> str   # <saved>/Screenshots/Golmok/<tag>/<preset or "current">/<name>.png
def screenshot_fallback_path(path: str) -> str                         # ".../far_01.png" → ".../far_0100000.png" (C++ HighResShot 폴백 이름)
def dwell_path_json(name: str, level: str, location_cm, rotation_rpy_deg, dwell_s=DWELL_S, hz=10, created="") -> str
    """GolmokStatsMath::FormatPathJson 레이아웃 그대로(§4-7). viewpoints.py의 rotation [roll, pitch, yaw] → r=[pitch, yaw, roll]."""
def validate_name(name: str) -> str            # NAME_RE 아니면 ValueError (콤마·공백은 ExecCmds를 깨뜨린다)
def exec_cmds(commands: list[str]) -> str      # '-ExecCmds="a, b, c"'; 명령에 ','나 '"'가 있으면 ValueError
def game_command_line(exe: str, uproject: str, map_path: str, *, walk: str, preset: str, res=(1920, 1080), log_path: str) -> list[str]   # §4-8
def saved_dir_candidates(project_saved_dir: str, local_app_data: str | None, engine_version=ENGINE_VERSION_KEY) -> list[str]
    # [project_saved_dir] + ([f"{local_app_data}/UnrealEngine/{engine_version}/Saved"] if local_app_data else [])
def csv_dirs(candidates: list[str]) -> list[str]                        # 각 + "/Profiling/CSV"
def path_dirs(candidates: list[str]) -> list[str]                       # 각 + "/Golmok/Paths"
def newest_file(candidates: list[str], pattern: str, not_before: float, isfile, mtime, glob) -> str | None
def ps_quote(arg: str) -> str        # 공백 포함·'"' 없음 → '"…"'로 감싼 뒤 전체를 '…'(내부 ' → '')
def powershell_script(runs: list[dict], path_files: list[str], candidates: list[str], out_dir: str, timeout_s: int) -> str   # §4-8
def perf_label(tag: str, preset: str, walk: str) -> str                 # "a_clear_noon_walk_01"
def file_uri(path: str) -> str                                          # "file:///D:/x/y.jpg"
def contact_sheet_html(tags, presets, names, image_rel, photo_rel=None, title="Golmok spike 1.1") -> str   # §4-9
def report_template(tags=TAGS, presets=DEFAULT_PRESETS, perf_markdown: str = "", csv_labels: list[str] = ()) -> str   # §4-10
```

#### 3-2. `zone_import.py`
```python
"""Import a golmok-mesh zone folder (docs/spec/zone-manifest.md §2) into the editor and rebuild its AGolmokZone.

    import golmok.zone_import as zi; r = zi.run(r"D:\\golmok\\zones\\z_yeonnam_alley_001")          # highest v*
    zi.run(r"D:\\golmok\\zones\\z_yeonnam_alley_001\\v2", level="/Game/Golmok/Maps/L_Basemap_Yeonnam")
    zi.run(r"D:\\golmok_synth\\zones\\z_synthetic_scan_001", level="/Game/Golmok/Maps/L_ZoneTest", geo_origin="area")  # runbook
    zi.run(…, geo_origin=r"D:\\golmok_basemap\\yeonnam")     # GeoOrigin from the basemap manifest origin
    zi.run(…, reimport_textures=False)                        # re-run: keep T_* assets that already exist
    zi.run(…, remeasure=True)                                 # ignore Saved/Golmok/zone_import/importer_mapping.json
"""
class ZoneImportError(RuntimeError):
    def __init__(self, step: str, message: str): super().__init__(_pure.fmt("zi.error", step=step, message=message)); self.step = step

def run(zone_dir, version=None, level=None, geo_origin=None, save=True, remeasure=False, reimport_textures=True) -> dict
def import_assets(plan: dict, work_dir: str, remeasure=False, reimport_textures=True) -> tuple[dict, list[dict], list[str], str]
    """run()의 에셋 부분(interior_setup 재사용): (mappings, assets, warnings, route). 레벨·GeoOrigin·Zone 액터는 건드리지 않음."""
```
**`run` 순서**(가짜 unreal 테스트가 이 순서를 그대로 단언):
1. `version_dir, version = _pure.resolve_zone_dir(zone_dir, version, os.listdir, os.path.isdir, os.path.isfile)`; `manifest = json(version_dir/manifest.json)`; `chunk_manifest = json(version_dir/visual/chunk_manifest.json)`(없으면 None); `plan = _pure.import_plan(...)`; `plan["problems"]`가 비어 있지 않으면 `ZoneImportError("plan", "\n".join(problems))`. **여기까지 unreal 호출 0회.** `plan["warnings"]`는 `zi.warn`으로. `unreal.log(fmt("zi.plan", zone_id, version, chunks=len, collision=len, collision_mode, textures=len, materials=len, blockers=planes))`.
2. `level`이 주어지면 `sz.open_or_create_level(level)`.
3. `work_dir = <Saved>/Golmok/zone_import/<zone_id>/v<n>/` 생성(`visual/`, `collision/` 하위 포함).
4. `mappings, assets, warnings, route = import_assets(plan, work_dir, remeasure, reimport_textures)`.
5. GeoOrigin: `existing = _find_geo_origin()`(레벨의 첫 `unreal.GolmokGeoOrigin`의 (lat, lon, h) 또는 None) → `(lat, lon, h), how = _pure.resolve_geo_origin(geo_origin, existing, manifest, read_json)` → `sz.find_or_spawn_geo_origin(lat, lon, h)` → `zi.geo`.
6. `zone = sz.find_or_spawn_zone(zone_id, version)`; `zone.rebuild_in_editor()`; `zi.zone`.
7. `save`면 `LevelEditorSubsystem.save_current_level()`. `result = _pure.result_json(plan, mappings, assets, warnings, route)` → `<work>/import_result.json`(`ensure_ascii=False, indent=2`); `zi.done`(assets = 에셋 항목 수, kind "file" 제외); `for line in _pure.summary_lines(result): unreal.log(line)`. 반환 result.

**`import_assets` 순서**:
1. **임포터 매핑**: `cache = json(importer_mapping.json)`(없으면 None); `engine = _engine_version()`(`unreal.SystemLibrary.get_engine_version()`; 없으면 `"unknown"` → 캐시 무효). `if not remeasure and _pure.importer_cache_valid(cache, engine)`: `zi.cache` state=`hit`만 로그하고 route·(s, M)을 재사용(프로브 임포트·`zi.route`·`zi.mapping` 없음). 아니면 `zi.cache` state=`miss` → `route, obj_mapping = _measure_obj_mapping(work_dir, plan["asset_folder"])`, `glb_mapping = _measure_glb_mapping(work_dir, plan["asset_folder"])`, 캐시 저장(§4-2), `zi.route`, `zi.mapping`(kind `obj`, `glb`) 로그. 프로브 폴더 `<asset_folder>/_probe`는 `try/finally`에서 `EditorAssetLibrary.delete_directory`.
   - `_measure_obj_mapping`: `<work>/_probe.obj`에 `_pure.probe_obj_text()`를 쓰고 사다리(D4) 순서로 `_import_task(_probe.obj, <asset_folder>/_probe, destination_name="SM_probe", options, factory)` 시도; 첫 성공 route 채택(`how="probe imported 1 static mesh"`); 모두 실패 → `ZoneImportError("probe", "OBJ import failed on routes fbx, interchange, legacy_flag: <마지막 예외>")`. `err, scale, m = _pure.measure_mapping([(bm._mesh_bounds(mesh), PROBE_BOX)])`; `err > 1.0` → `ZoneImportError("probe", f"obj importer mapping fit failed (error {err:.2f} cm)")`.
   - `_measure_glb_mapping`: `sz.boxes_glb([PROBE_BOX], "SM_probe_glb")` → `<work>/_probe.glb` → `_import_task(…, destination_name="SM_probe_glb")` → 같은 측정.
2. **텍스처**(plan 순서): `_import_texture(tex, reimport_textures)`:
   - `reimport_textures=False`이고 `EditorAssetLibrary.does_asset_exist(tex["asset"])` → 로드해 반환, `zi.texture` how=`skipped: exists`.
   - `_import_task(tex["anchor"], f"{asset_folder}/Textures", destination_name=tex["name"], options=_texture_options())` → `Texture2D` 1개 선택. 경로가 `tex["asset"]`이 아니면(`facade_1001` 등) `EditorAssetLibrary.rename_asset(old, tex["asset"])`. 나머지 임포트 부산물(`Texture2D`/`Material`)은 `_delete_assets` + `zi.cleanup`.
   - `set_editor_property("srgb", True)`; `vt = get_editor_property("virtual_texture_streaming")`; False면 True로 설정하고 다시 읽음(여전히 False면 `vt=off`·NoVT 부모 대상).
   - 병합 판정(`len(tiles) > 1`일 때만): `w, h = blueprint_get_size_x(), blueprint_get_size_y()`(hasattr 없으면 판정 생략·`merged by importer (size unknown)`), 첫 타일 PNG의 IHDR(`_pure.png_size`)과 같으면 **병합 안 됨** → 3. (후속: #69에서 `-nullrhi`·크기 0이면 팩 생략, 태그 우선 [PR #122](https://github.com/wooklym/golmok/pull/122)에서 크기는 먼저 에셋 태그 `Dimensions`(`EditorAssetLibrary.get_tag_values`, 런북 §12 #42) — 아래 "결과 — Claude 후속: UDIM 병합 판정 `Dimensions` 태그 우선" 절.)
   - `save_loaded_asset`; `zi.texture`(`how` = 병합 상태 ∈ {`merged by importer`, `packed from N tiles`, `tile 1001 only (WARNING)`, `single texture`, `skipped: exists`} + VT를 켰으면 `, vt enabled after import`).
3. **UDIM 폴백**: 타일마다 `_import_task(file, f"{asset_folder}/Textures/_tiles", destination_name=f"{name}_{tile}")` → `hasattr(unreal, "UDIMTextureFunctionLibrary")`면 `unreal.UDIMTextureFunctionLibrary.make_udim_virtual_texture_from_texture2_ds(tex["asset"], [textures], [unreal.IntPoint(u, v) …], keep_existing_settings=False, check_out_and_save=True)` → `_tiles` 폴더 `delete_directory` → how=`packed from N tiles`. 라이브러리 없음: 첫 타일을 `tex["asset"]`으로 `rename_asset`(다른 타일 삭제) + `zi.warn("texture <name>: UDIM tiles not merged; using tile 1001 only (runbook #4)")`, how=`tile 1001 only (WARNING)`.
4. **마스터 머티리얼**: VT 텍스처가 있으면 `materials.build_zone_scan_material(T_ZoneScanDefault, vt=True)`; vt=False 텍스처가 있으면 `materials.build_zone_scan_material(T_ZoneScanDefault_NoVT, vt=False)`. VT 텍스처가 하나도 없으면 NoVT만. (수정, 리뷰 F4·L2-01·L2-04: 기본 텍스처는 zone 텍스처가 아니라 마스터 전용 `/Game/Golmok/Materials/T_ZoneScanDefault[_NoVT]`(생성 PNG 256×256 회색); 이미 있는 마스터는 BaseColor 샘플러 기본을 제자리에서 고친다 — 런북 #10.)
5. **MI**(plan 순서): `materials.zone_scan_instance(texture, parent(텍스처의 vt에 따라), mi["asset"])`; `zi.material`.
6. **청크**(plan 순서): `n = _pure.pretransform_obj_file(chunk["obj"], f"{work}/visual/{chunk['name']}.obj", A_obj, mtllib=" ".join(chunk["mtllib"]))`; MTL 사본 `f"{work}/visual/<mtl>"` = `_pure.mtl_with_absolute_textures(text, mtl_dir)`(청크마다 같은 내용을 다시 써도 무해) → `_import_task(copy, asset_folder, destination_name=chunk["name"], options=_obj_options(route), factory=_obj_factory(route))` → StaticMesh 1개; 경로가 `chunk["asset"]`이 아니면 `rename_asset`; 부산물(`Material`/`MaterialInstance*`/`Texture2D`) 삭제 + `zi.cleanup` → `err = _pure.bounds_error_cm(bm._mesh_bounds(mesh), chunk["expected_ue_bounds_cm"])`; `err > _pure.bounds_tolerance_cm(want)` → `ZoneImportError(f"chunk {id}", f"imported bounds {got} != expected {want} (error {err:.2f} cm); importer mapping may have changed: run with remeasure=True (runbook #2)")` → `bm._set_nanite(mesh, True)` → 슬롯 `_assign_slots(mesh, chunk, mi_assets)` → `save_loaded_asset` → `zi.chunk`(tris = plan 값, slots = `"facade=MI_facade,ground=MI_ground"` 슬롯 이름순 `k=v` 콤마 결합).
   - `_assign_slots`: `names = [str(sm.get_editor_property("material_slot_name")) for sm in mesh.get_editor_property("static_materials")]`; `pairs, unmatched = _pure.slot_assignment(names, chunk["slots"], None)`; unmatched가 있으면 `usemtl = _pure.usemtl_order(open(chunk["obj"]))`로 재시도; 남은 unmatched마다 `zi.warn("chunk <id>: slot '<name>' left with the importer default (runbook #7)")`; `mesh.set_material(i, mi)`.
7. **폴더 정리**: `EditorAssetLibrary.list_assets(asset_folder, recursive=True, include_folder=False)`(경로는 `.split(".")[0]` 정규화) 중 plan 기대 집합(청크·충돌·`Textures/T_*`·`Materials/MI_*`·`L_<zone_id>`) 밖의 에셋 가운데 **`Material`/`MaterialInstanceConstant`/`Texture2D`만** 삭제(`zi.cleanup`); 그 외는 `zi.warn("unexpected asset <path> left in place")`.
8. **충돌**(plan 순서): `data = read_bytes(glb)`; `want = _pure.expected_ue_bounds(_pure.glb_bounds_enu(data))`; `_pure.pretransform_glb(data, A_glb, rename=col["name"])` → `<work>/collision/<name>.glb` → `_import_task(…, destination_name=col["name"])`(옵션 없음: V-02 검증 경로) → 이름 검증·rename → bounds 검증(청크와 같은 규칙, step `collision <id|single>`) → `bm._complex_collision(mesh)`, `bm._set_nanite(mesh, False)` → 부산물 정리 → `save_loaded_asset` → `zi.collision`.
9. **파일 복사**: `dest = <ContentDir>/<content_rel>/`; `copy_files`마다 읽어서 `json.loads`로 파싱 확인 후 `shutil.copyfile`; `zi.copied`(files = 정렬 이름 `", "` 결합). assets에 kind `file` 항목 추가.
10. 반환 `(mappings, assets, warnings, route)`.

에러 처리: 1단계 오류는 에디터를 건드리기 전에 끝난다. 이후 예외는 `ZoneImportError(step, message)`로 감싸고, 프로브 폴더는 finally에서 삭제, **Zone 액터는 스폰되지 않는다**(테스트 `test_bounds_mismatch_raises_and_places_no_zone`).

**어댑터**(모듈 내부 `_` 함수, 전부 hasattr 분기):
```python
def _import_task(filename, destination_path, destination_name=None, options=None, factory=None) -> list[str]
    # AssetImportTask: automated=True, replace_existing=True, save=False, async_=False(hasattr), destination_name(있을 때), options(있을 때), factory(있을 때);
    # AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]); 반환 imported_object_paths(list[str]); 비어 있으면 RuntimeError(f"no asset imported from {filename}")
def _obj_factory(route) -> object | None        # route=="fbx" and hasattr(unreal, "FbxFactory") → unreal.FbxFactory(); 그 외 None
def _obj_options(route) -> object | None
    # "fbx"/"legacy_flag": unreal.FbxImportUI: is_obj_import=True, import_mesh=True, import_materials=False, import_textures=False, import_as_skeletal=False,
    #   automated_import_should_detect_type=False, mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,
    #   static_mesh_import_data: build_nanite=True, combine_meshes=True, auto_generate_collision=False, generate_lightmap_u_vs=False (속성마다 try/except + zi.warn)
    # "interchange": unreal.InterchangeGenericAssetsPipeline(): common_meshes_properties.force_all_mesh_as_type=IFMT_STATIC_MESH, mesh_pipeline.import_static_meshes=True,
    #   mesh_pipeline.build_nanite=True, material_pipeline.import_materials=False, material_pipeline.texture_pipeline.import_textures=False (hop마다 hasattr)
    # 클래스가 없으면 None + zi.warn("FbxImportUI unavailable: OBJ imported with default options (runbook #1)")
def _texture_options() -> object | None         # InterchangeGenericAssetsPipeline: material_pipeline.texture_pipeline.import_udi_ms=True, material_pipeline.import_materials=False; 없으면 None
def _console(cmd: str)                          # unreal.SystemLibrary.execute_console_command(editor_world, cmd) (legacy_flag route)
def _engine_version() -> str
def _measure_obj_mapping(work_dir, asset_folder) -> tuple[str, tuple[float, tuple, float]]   # (route, (scale, m, err))
def _measure_glb_mapping(work_dir, asset_folder) -> tuple[float, tuple, float]
def _assign_slots(mesh, chunk, mi_by_name) -> list[str]        # unmatched
def _delete_assets(paths: list[str], keep: set[str]) -> list[str]
def _find_geo_origin() -> tuple | None
def _pick(paths: list[str], cls) -> object                     # imported_object_paths 중 isinstance(load_asset, cls) 첫 것; 없으면 RuntimeError
```

#### 3-3. `interior_setup.py`
```python
"""Interior zone (kind=interior) → assets + AGolmokZone + sublevel L_<zone_id> with one PointLight, then rebuild the parent zone.

    import golmok.interior_setup as it; it.run(r"D:\\golmok_synth\\zones\\z_synthetic_scan_001_room", level="/Game/Golmok/Maps/L_ZoneTest")
    it.run(…, register=True)     # NamedStreamingLevel path only (DefaultGame.ini InteriorStreamingMode)
"""
def run(zone_dir, version=None, level=None, save=True, register=False, remeasure=False, reimport_textures=True) -> dict
```
순서(테스트가 단언; 리뷰 수정 R1-04·F3 반영 — ①은 unreal 호출 0회, ②~⑤는 레벨 열기와 부모 액터 `version` 읽기뿐이고 실패해도 임포트·스폰 0회):
1. `resolve_zone_dir` → manifest. `kind != "interior"` → `ZoneImportError("manifest", "kind must be interior (use zone_import.run for exterior zones)")`; `parent_zone`이 없으면 `ZoneImportError("manifest", "parent_zone missing")`.
2. `level`이 있으면 `sz.open_or_create_level(level)`. 부모 zone 액터(`unreal.GolmokZone` with `zone_id == parent`)가 레벨에 없으면 `ZoneImportError("parent", f"Zone_{parent} not in level: run zone_import.run on the parent zone first")`. `parent_version` = 그 액터의 `version`(레벨이 고른 버전; Content의 최신 v<n>이 아님).
3. 부모 manifest = `<ContentDir>/Golmok/Zones/<parent>/v<parent_version>/manifest.json`(zone_import가 복사해 둔 것; 없으면 `ZoneImportError("parent", f"Zone_{parent} is v{n} but <Content>/Golmok/Zones/{parent}/v{n}/manifest.json is missing: run zone_import.run on that version")`). 이어서 `check = _pure.portal_round_trip_check(parent, interior)`; `portal_pair` ValueError → `ZoneImportError("portal", str(e))`; `not check["ok"]` → `ZoneImportError("portal", f"{interior_portal} vs {parent_portal}: {dist_m:.3f} m apart, yaw error {yaw_err_deg:.1f} deg (fix the manifests before importing)")`. 통과하면 `is.portal`.
4. (3에 합침)
5. `plan = import_plan(...)`; problems → `ZoneImportError("plan", …)`.
6. `mappings, assets, warnings, route = zone_import.import_assets(plan, work_dir, remeasure, reimport_textures)`(work_dir = `<Saved>/Golmok/zone_import/<zone_id>/v<n>/`).
7. `zone = sz.find_or_spawn_zone(zone_id, version)`; `zone.rebuild_in_editor()`; `t = zone.get_actor_transform()`; `zone.unload_in_editor()`(PIE에서는 부모 문의 포털이 로드).
8. `specs = _pure.interior_sublevel_specs(manifest)`; `package = sz.sublevel_path(manifest)`; `sz._spawn_interior_sublevel(manifest, t, return_level=level or sz._current_level_path(), specs=specs, delete_tag=_pure.INTERIOR_SETUP_TAG, on_removed=lambda n: unreal.log(fmt("is.rerun", n=n, package=package)))`(반환값 == package). 서브레벨이 이미 있으면 sz가 태그 `GolmokInteriorSetup` 액터만 지우고 `on_removed(n)`을 부른다(새 레벨이면 부르지 않음). 스폰 전 `spec["kind"]`가 전부 `point_light`인지 확인(아니면 `ZoneImportError("sublevel", …)`). `is.sublevel`(actors = 라벨 목록 `[Interior_Light_<zone_id>]`).
9. 다시 연 레벨의 부모 액터를 찾아 `rebuild_in_editor()`(서브레벨 저장 뒤 퍼시스턴트 레벨을 다시 열어 트랜지언트 컴포넌트·포털이 사라짐; `version`은 건드리지 않는다); `is.exterior`.
10. `save`면 `save_current_level()`(퍼시스턴트 레벨이 current).
11. `register`면 마지막 에디터 단계로 `sz.register_interior_sublevel(zone_id, version)` — `add_level_to_world`가 서브레벨을 current로 만들므로 sz가 `set_current_level_by_name`으로 되돌리고 퍼시스턴트 맵을 `save_map`으로 경로 저장(V-03, pc-findings #4; 그 뒤 `save_current_level()` 금지, 런북 §12 #36). `result = _pure.result_json(...)` + `result["interior"] = {"sublevel": package, "round_trip": check, "parent": parent_id, "parent_version": n, "actors": [labels]}` → `<work>/import_result.json`; `is.done`.

#### 3-4. `spike_runner.py`
```python
"""Spike 1.1 capture and measurement helpers (research/08). Unattended screenshots run in PIE (D11); performance runs in -game (D12).

    import golmok.spike_runner as s
    s.prepare()                                              # which of the 10 viewpoints are missing
    s.capture_all()                                          # tags a b c ac × 3 presets × 10 viewpoints in PIE → Saved/Screenshots/Golmok/<tag>/<preset>/<name>.png
    s.capture_all(tags=("a",), presets=("clear_noon", "night"), mode="editor")   # attended editor-viewport path
    s.save_layer_levels(); s.game_scripts(paths=("walk_01",))                    # -game CSV runs → Saved/Golmok/spike/run_game_perf.ps1
    s.perf_all(paths=("walk_01",))                                               # PIE CSV (reference only)
    s.contact_sheet(); s.report_template(perf_markdown=open(...).read())
"""
_now = time.monotonic          # 테스트가 가짜 시계로 바꿈
PIE_START_TIMEOUT_S = 60.0; PIE_STOP_TIMEOUT_S = 30.0; WARMUP_S = 3.0; TOD_WAIT_S = 3.0; SETTLE_S = 1.5; FILE_TIMEOUT_S = 30.0; STOPPLAY_WAIT_S = 0.3

def prepare(level=None, names=_pure.VIEWPOINT_NAMES) -> list[str]
    # viewpoints._load() 이름 집합 vs names → missing(정렬) 반환; sr.prepare(level=viewpoints._level_name()); 이름마다 _pure.validate_name
def configure_pie_window(size=_pure.PIE_WINDOW) -> str
    # hasattr(unreal, "get_default_object") and hasattr(unreal, "LevelEditorPlaySettings"):
    #   s = unreal.get_default_object(unreal.LevelEditorPlaySettings); s.set_editor_property("new_window_width", w); ("new_window_height", h);
    #   hasattr(unreal, "PlayModeType"): s.set_editor_property("last_executed_play_mode_type", unreal.PlayModeType.PLAY_MODE_TYPE_PLAY_IN_EDITOR_FLOATING)
    #   how = "LevelEditorPlaySettings"; 예외/부재 → how = "manual: Editor Preferences > Level Editor > Play > New Window Size (runbook #21)" + sr.warn
    # sr.window(w, h, multiplier=2, how); 반환 how
def apply_layers(tag, world=None) -> dict
    # state = _pure.layer_state(tag). world None(에디터): EditorActorSubsystem.get_all_level_actors(); PIE 월드: GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
    # AGolmokZone → set_visual_visible(state["zone_visual"]); 라벨 _pure.spike_actor_group ∈ {spike_b, spike_c} → set_actor_hidden_in_game(not state[group]) + (에디터에서만) set_is_temporarily_hidden_in_editor(not state[group]);
    # 실패 시 set_editor_property("hidden", …) 폴백. sr.layers(where="editor"|"pie"). 반환 {"zone_visual","spike_b","spike_c","actors": n}
def save_layer_levels(tags=("b", "c", "ac"), base_level=None) -> list[str]
    # base = base_level or sz._current_level_path(); 태그마다 dst=f"/Game/Golmok/Maps/L_Spike_{tag}": EditorAssetLibrary.duplicate_asset(base, dst)(있으면 delete 후) → load_level(dst) → apply_layers(tag) (2026-09-28 Save As로 대체 — 결과 절)
    # → AGolmokZone.set_editor_property("auto_managed", state["zone_visual"])(b/c는 False: -game에서 거리 로드 금지) → save_current_level → sr.level; 끝에 load_level(base). 반환 패키지 목록
def capture_all(tags=_pure.TAGS, presets=_pure.DEFAULT_PRESETS, names=None, mode="pie") -> object
    # names None → prepare()가 missing 없을 때 VIEWPOINT_NAMES, 있으면 저장된 것 중 names 교집합 + sr.warn. mode="pie": _PieCapture(jobs); mode="editor": 태그별 apply_layers → viewpoints.capture(tag, names, presets, on_done=next_tag) 연쇄
def perf_all(paths=("walk_01",), tags=_pure.TAGS, presets=("clear_noon",)) -> object       # _PiePerf (PIE 참고치)
def game_scripts(paths=("walk_01",), tags=_pure.TAGS, presets=("clear_noon",), res=(1920, 1080), base_level=None, timeout_s=900) -> str
    # 경로 파일 <Saved>/Golmok/Paths/<walk>.json이 없으면 RuntimeError("record it first: golmok.path record <walk>")
    # runs = [{"label": perf_label(tag, preset, walk), "argv": _pure.game_command_line(exe, uproject, map(tag), walk=, preset=, res=, log_path=<Saved>/Golmok/spike/game_<label>.log)} …]
    #   map(tag) = base_level(tag "a") 또는 f"/Game/Golmok/Maps/L_Spike_{tag}"; exe = <engine_dir>/Binaries/Win64/UnrealEditor.exe (engine_dir: unreal.Paths.engine_dir() → 없으면 os.environ["UE_ROOT"] → 없으면 RuntimeError, §7 #27); uproject = unreal.Paths.get_project_file_path() → 없으면 <ContentDir>/../Golmok.uproject (정규화)
    # text = _pure.powershell_script(runs, path_files=[<Saved>/Golmok/Paths/<walk>.json …], candidates=_pure.saved_dir_candidates(<Saved>, os.environ.get("LOCALAPPDATA")), out_dir=<Saved>/Golmok/spike/csv, timeout_s)
    # → <Saved>/Golmok/spike/run_game_perf.ps1 (encoding utf-8-sig, newline "\r\n"); sr.script; 반환 경로
def contact_sheet(tags=_pure.TAGS, presets=_pure.DEFAULT_PRESETS, names=None, photos_dir=None) -> str
    # root=<Saved>/Screenshots/Golmok; image_rel(tag,preset,name) = f"{tag}/{preset}/{name}.png" if exists else None; photo_rel(name) = photos_dir/<name>.(jpg|jpeg|png) → 상대(root 아래) 또는 file_uri
    # → root/contact_sheet.html (utf-8); sr.sheet
def report_template(tags=_pure.TAGS, presets=_pure.DEFAULT_PRESETS, perf_markdown="") -> str
    # _pure.report_template(...) → <Saved>/Golmok/spike/report_template.md; unreal.log 출력; 반환 텍스트
def _pie_world()
    # unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() (확인); None이고 hasattr(unreal, "EditorLevelLibrary") and hasattr(EditorLevelLibrary, "get_pie_worlds")면 get_pie_worlds(False)[0] (deprecated 폴백, sr.warn); 그래도 None → None
def _console(world, cmd)              # sr.cmd 로그 후 unreal.SystemLibrary.execute_console_command(world, cmd)
```
**`_PieCapture` 상태기계**(slate post-tick, `tick(dt)` public — 테스트가 직접 호출; 모든 대기는 `_now()` 기준 초):
`IDLE → LAYERS(에디터 월드 apply_layers(tag)) → WINDOW(configure_pie_window, 태그당 1회) → BEGIN_PIE(경로 JSON을 먼저 전부 `<Saved>/Golmok/Paths/vp_<name>.json`에 씀; `LevelEditorSubsystem.editor_request_begin_play()`; sr.pie state=begin) → WAIT_PIE(`is_in_play_in_editor()` and `_pie_world()` and `GameplayStatics.get_player_controller(world, 0)`; PIE_START_TIMEOUT_S 초과 → `_finish("PIE did not start", warn)`) → WARMUP(WARMUP_S) → HUD_OFF(`golmok.hud 0`) → LAYERS_PIE(apply_layers(tag, world)) → [job] TOD(프리셋이 바뀔 때만 `golmok.tod <preset>`; TOD_WAIT_S) → PATH(`golmok.path play vp_<name>`; SETTLE_S) → SHOT(`golmok.screenshot <tag> <name>`; requested_at=time.time()−1.0) → WAIT_FILE(`_pure.screenshot_path` 또는 `screenshot_fallback_path`가 존재하고 mtime ≥ requested_at → 폴백 이름이면 `os.replace`로 `<name>.png`; PNG IHDR로 (w, h) 읽어 sr.captured; FILE_TIMEOUT_S 초과 → sr.missing(why="timeout") → 계속) → STOPPLAY(**항상** `golmok.path stopplay`; STOPPLAY_WAIT_S) → 다음 job; 태그가 바뀌면 END_PIE(`editor_request_end_play()`; `not is_in_play_in_editor()`까지 PIE_STOP_TIMEOUT_S) → LAYERS …; 끝나면 END_PIE → DONE(sr.done what="capture")`.
- 예외는 `_finish(message, warn=True)`로(틱마다 raise 금지): 콜백 해제 + PIE 중이면 `editor_request_end_play()`.
- `Fake`/실제 모두 `unreal.register_slate_post_tick_callback(self.tick)`으로 등록, `unregister_slate_post_tick_callback(handle)`로 해제.
- 스크린샷 폴더의 `<preset>`은 C++가 `CurrentPreset`으로 정한다: `golmok.tod`가 실패하면 파일이 `current/`에 생기고 missing으로 보고된다(런북이 원인 지목).

**`_PiePerf`**(참고치): 태그마다 `LAYERS → BEGIN_PIE → WAIT_PIE → WARMUP → HUD_OFF → LAYERS_PIE → [preset] TOD → [path] PLAY(\`golmok.path play <walk> --csv\`) → WAIT_CSV(`_pure.newest_file(csv_dirs, "Profile*.csv", not_before)`; 타임아웃 = 경로 길이(JSON 마지막 t) + 60 s) → sr.csv(label=perf_label) → 다음 → END_PIE`. 끝에 sr.done what="perf (PIE, reference only)".

#### 3-5. `basemap_import.py` 보강
- `_set_geo_origin(origin: dict)`: 함수 안에서 `from . import synthetic_zone as sz`; `sz.find_or_spawn_geo_origin(origin["lat"], origin["lon"], origin["height_ellipsoidal"])`; `unreal.log(_pure.fmt("bm.geo", lat=…, lon=…, h=…))`. `run()`에서 `_set_georeference(manifest["origin"])` **바로 다음 줄**에 호출.
- 모듈 docstring 한 줄 추가: "`golmok-basemap build --exclude`로 제외한 건물은 타일에 없다(에디터에서 할 일 없음); 겹치는 zone은 `GolmokBasemap` 태그 런타임 숨김이 보조(D-012)." 태그(`GolmokBasemap`/`tile:<id>`/`GolmokBasemapTerrain`)는 WP-04가 이미 함 — 변경 없음.

#### 3-6. `synthetic_zone.py` 정리, `materials.py`, `viewpoints.py`
- `synthetic_zone.run(geo_origin="area", move_player_start=True, import_assets=True, level=ZONE_TEST_MAP, interior=False)` **시그니처 불변**. docstring: "`interior=True`는 WP-05 픽스처 전용(문 구멍·`SM_room`·서브레벨). 실제 zone은 `zone_import.run`/`interior_setup.run`. WP-06 재사용 헬퍼: `find_or_spawn_geo_origin`, `find_or_spawn_zone`, `open_or_create_level`, `_current_level_path`, `_spawn_interior_sublevel`, `sublevel_path`, `register_interior_sublevel`, `boxes_glb`, `expected_ue_bounds`."
- `_spawn_interior_sublevel(int_manifest, zone_transform, return_level, specs=None, delete_tag=None, on_removed=None) -> str`: `specs None` → `sublevel_actor_specs(int_manifest)`(기존 동작). 재오픈 시 삭제 대상: `delete_tag`가 있으면 `unreal.Name(delete_tag) in actor.get_editor_property("tags")`인 액터, 없으면 기존처럼 라벨 일치; 삭제 수 n으로 `on_removed(n)` 호출(있을 때).
- `_spawn_sublevel_actor(spec, location)`: 끝에 `if spec.get("tags"): actor.set_editor_property("tags", [unreal.Name(t) for t in spec["tags"]])`.
- `register_interior_sublevel(zone_id=INTERIOR_ZONE_ID, version=INTERIOR_VERSION)`: 본문 그대로, manifest는 `_load_manifest(zone_id, version)`.
- `materials.py`: `ZONE_SCAN_NAME = "M_ZoneScan"`, `ZONE_SCAN_NOVT_NAME = "M_ZoneScan_NoVT"`.
  ```python
  def build_zone_scan_material(default_texture, vt=True, overwrite=False):
      """M_ZoneScan (vt) / M_ZoneScan_NoVT: TextureSampleParameter2D "BaseColor" (texture=default_texture — VT 샘플러면 반드시 VT 텍스처),
      sampler_type = MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR (vt) / SAMPLERTYPE_COLOR (hasattr 없으면 미설정 + log_warning),
      Roughness 상수 0.8, Normal 없음, used_with_nanite=True, recompile, save. 있으면(overwrite=False) 로드만."""
  def zone_scan_instance(texture, parent, path):   # == terrain_instance(texture, parent, path)
  ```
- `viewpoints.capture(tag, names=None, presets=None, game_view=True, on_done=None)`; `_Capture.__init__(..., on_done)`; `_finish`가 끝에 `if self.on_done: self.on_done(self.saved, self.missing)`. 기존 호출 호환.

#### 3-7. `tools/scripts/make_synthetic_zone.py`
```
python tools/scripts/make_synthetic_zone.py --out <dir> [--zone-id z_synthetic_scan_001] [--interior] [--tile-px 256] [--force] [--check] [--quiet]
```
- 의존: `golmok_tools.mesh.{objio,cli}`, `golmok_tools.zone.{manifest,transform,cli}`, `numpy`(즉 `pip install -e ".[zone,mesh]"`; CI는 전부 설치). `PIL`·`trimesh`·`fast_simplification`·`pygltflib`를 **직접 import하지 않는다**(테스트가 소스 검사). 없으면 stderr `ERROR install tools with pip install -e ".[zone,mesh]"` 후 종료 2.
- `--out`: `<out>/recon/…`(원본 흉내)와 `<out>/zones/…`(WP-03 결과)를 만든다. `<out>/zones/<zone_id>`가 있고 `--force` 없으면 종료 2·stderr `exists; use --force`. `--check`: 임시 폴더에 다시 생성해 기존 출력과 비교(텍스트: `\r\n`→`\n`, 절대경로 `<out>` 접두를 `<OUT>`으로 치환 후 바이트 비교; PNG: `zlib.decompress`한 픽셀 비교) → 0/1. `--quiet`: `wrote` 줄 생략. stdout은 ASCII만(`wrote <relpath>` 줄 + 마지막 `next: import golmok.zone_import as zi; zi.run(r"<out>\zones\<zone_id>", level="/Game/Golmok/Maps/L_ZoneTest", geo_origin="area")`(비ASCII는 `backslashreplace`)). 텍스트 파일 `encoding="utf-8", newline="\n"`, JSON `ensure_ascii=False`. 타임스탬프·난수 없음.
- **원본**(`<out>/recon/<zone_id>/`): `scan.obj`(`v/vt/f v/vt`, `mtllib scan.mtl`, `usemtl ground` 먼저·`usemtl facade` 다음, 소수 6자리, Z-up zone-local m), `scan.mtl`:
  ```
  newmtl ground
  Kd 1 1 1
  map_Kd tex/ground.png

  newmtl facade
  Kd 1 1 1
  map_Kd -bm 1 tex/facade.<UDIM>.png
  ```
  `tex/ground.png`(회색 120,120,120; **UDIM 아님** = 단일 텍스처 경로), `tex/facade.1001.png`(빨강 200,60,60), `tex/facade.1002.png`(초록 60,200,60), `tex/facade.1011.png`(파랑 60,60,200). `--interior`: `<out>/recon/<zone_id>_room/room.obj`, `room.mtl`(`newmtl room / Kd 1 1 1 / map_Kd tex/room.1001.png` — 명시 타일 한 장 = 그룹 1개 경로), `tex/room.1001.png`(노랑 200,200,60).
- **기하**(ENU m, Z-up; `--interior`와 무관하게 실외는 항상 같다 — 문 구멍은 항상 있다):
  | 요소 | 위치 | 머티리얼·타일 | 삼각형 |
  |---|---|---|---|
  | 지면 격자 | x −15..15, y 0..15, 5 m 셀(6×3), z = 0.02·x (−0.3..0.3); UV u=(x+15)/30, v=y/15 | `ground` 1001 | 36 |
  | 파사드 A(빨강) | 얇은 벽 x 1..9, y 7.0..7.2, z 0..6에 **문 구멍 x 4..6, z 0..2.2**(`door_openings` 규칙: door_1 x 5 ± 1.0, z 0..2.2) → 왼쪽(x1..4)·오른쪽(x6..9)·상인방(x4..6, z2.2..6) 3박스 | `facade` 1001 | 36 |
  | 파사드 B(초록) | 얇은 벽 x −11..−5, y 5.0..5.2, z 0..5에 **창 구멍 x −9.5..−6.5, z 0.25..2.75** → 왼쪽·오른쪽·상인방(z 2.75..5)·문턱(z 0..0.25) 4박스 | `facade` 1002 | 48 |
  | 블록 C(파랑) | x 10..13, y 2..4, z 0..2 (속이 찬 박스) | `facade` 1011 | 12 |
  박스 UV = `tests/mesh_util.box` 규칙(타일 오프셋 + 0.1..0.9, u∝x, v∝z). 총 132 tri. 15 m 격자 → 청크 **2개**: `c_w001_n000`(지면 18 + B 48 = **66** tri, bbox `[[-15,0,-0.3],[0,15,5]]`, tiles [1001, 1002]), `c_e000_n000`(지면 18 + A 36 + C 12 = **66** tri, bbox `[[0,0,0],[15,15,6]]`, tiles [1001, 1011]); 두 청크 모두 materials `["facade","ground"]`.
- **실내**(`--interior`, 실내-local m; 원점 = 방 남서 바닥 모서리 = 실외 (1.0, 7.2, 0.0)): 바닥 x0..8, y0..6.8, z −0.2..0 / 서벽 x0..0.2 / 동벽 x7.8..8 / 북벽 y6.6..6.8(x0..8, z0..3) / 천장 z3..3.2 → 5박스 **60** tri, 머티리얼 `room` 1001, bbox `[[0,0,-0.2],[8,6.8,3.2]]`, 청크 1개 `c_e000_n000`. 남쪽 벽은 실외 파사드 A(겹침 없음: A는 y 7.0..7.2, 방은 y ≥ 7.2). 방은 어떤 실외 박스와도 교차하지 않는다(테스트).
- **파이프라인**(인프로세스 `mesh_main`/`zone_main`, `test_mesh_zone_integration.py`와 같은 호출):
  1. 실외 manifest: `zm.new_manifest(zone_id, "exterior", 37.5620, 126.9250, 50.0, rect_footprint(37.5620, 126.9250, 32.0, 17.0, dx=0.0, dy=7.5), priority=10)`(`rect_footprint`는 `tests/zone_util.py`의 10줄 사본, dx/dy 지원) → `sources=[{"capture_id":"synthetic","note":"make_synthetic_zone.py"}]`, `attribution=["합성 테스트 데이터 (WP-06)"]` → `--interior`면 `portals=[{"id":"door_1","to_zone":"<zone_id>_room","pose_enu":{"position":[5.0,7.0,0.0],"yaw_deg":90.0},"radius_m":1.0,"kind":"door"}]` → `zm.save(<out>/zones/<zone_id>/v1/manifest.json)`.
  2. `mesh_main(["chunk", scan.obj, "--size", "15", "--out", vdir/visual, "--manifest", manifest])` → `visual/{c_w001_n000.obj, c_e000_n000.obj, scan.mtl, chunk_manifest.json}`; `visual/scan.mtl`의 `map_Kd`는 `../../../../recon/<zone_id>/tex/…`(버전 폴더 **밖** 4단계 상대경로; `-bm 1` 유지), `chunk_manifest.textures`는 절대경로(`<UDIM>` 토큰 그대로), `missing`은 둘 다 빈 목록.
  3. `mesh_main(["collision", scan.obj, "--out", vdir/collision.glb, "--target-tris", "1000", "--min-component-m2", "0.1", "--no-snap-ground", "--per-chunk", vdir/visual, "--manifest", manifest])` → `collision.glb`(132 tri) + `collision/c_w001_n000.glb`(66), `collision/c_e000_n000.glb`(66) + `layers.collision.chunks`. (`--no-snap-ground`: 바닥 스냅이 박스 밑면을 옮겨 수치가 흔들리는 것을 막는다; 132 < 1000이라 데시메이션 없음.)
  4. `mesh_main(["blockers", "add", vdir/blockers.json, "--center", "-8,5,1.5", "--normal", "0,-1,0", "--size", "3,2.5", "--kind", "glass", "--id", "glass_1"])` + `mesh_main(["blockers", "build", vdir/blockers.json, "--manifest", manifest])`(창 구멍 위 유리; `blockers.glb`는 생기지만 zone_import는 쓰지 않는다).
  5. `--interior`: 실내 원점 `lon, lat, _ = transform.enu_to_lonlat([[1.0, 7.2, 0.0]], (37.5620, 126.9250, 50.0))`, h = 50.0 → `zm.new_manifest("<zone_id>_room", "interior", lat, lon, 50.0, rect_footprint(lat, lon, 8.0, 6.8, dx=4.0, dy=3.4), parent_zone=zone_id, priority=20)` → `portals=[{"id":"door_out","to_zone":zone_id,"pose_enu":{"position":[4.0,-0.2,0.0],"yaw_deg":-90.0},"radius_m":1.0,"kind":"door"}]`, `consent={"type":"owner_consent","record_id":"synthetic-consent-002"}`, sources·attribution 동일 → chunk/collision 같은 단계(blockers 없음).
  6. `zone_main(["validate", "--check-files", "--strict", manifest])`(+ 실내) ≠ 0 → stderr 출력, 종료 1.
  7. `expected.json`(§4-4)을 각 zone의 `v1/`에 쓴다(값은 생성 데이터에서 계산; UE 레벨 좌표는 `golmok_tools.zone.transform`으로 area 원점 (37.56, 126.923, 40) 기준 소수 2자리).
- **PNG**(`write_png_rgb(path, w, h, rows: list[bytes])`: 시그니처, IHDR(8-bit RGB), IDAT=`zlib.compress(b"".join(b"\x00"+row), 6)`, IEND, CRC=`zlib.crc32`): 배경 단색, 2 px 검은 테두리, **좌상단 흰 정사각형**(12 px, 4 px 간격) 개수 = 세트 안 순서(facade 1001→1, 1002→2, 1011→3; ground·room 1), 타일 번호 4자리를 **5×7 비트맵 글꼴**(아래 상수, ×8 = 40×56 px, 글자 간격 8 px, 가로 중앙·세로 y 100..156)로 흰색 — `ground.png`(UDIM 아님)은 숫자 없음. 비트맵(행 문자열, `1`=흰색):
  ```
  0: 01110 10001 10011 10101 11001 10001 01110   1: 00100 01100 00100 00100 00100 00100 01110
  2: 01110 10001 00001 00010 00100 01000 11111   3: 11111 00010 00100 00010 00001 10001 01110
  4: 00010 00110 01010 10010 11111 00010 00010   5: 11111 10000 11110 00001 00001 10001 01110
  6: 00110 01000 10000 11110 10001 10001 01110   7: 11111 00001 00010 00100 01000 01000 01000
  8: 01110 10001 10001 01110 10001 10001 01110   9: 01110 10001 10001 01111 00001 00010 01100
  ```
  UE는 UDIM을 임포트하며 세로로 뒤집고 메시 UV도 맞춰 바꾼다(citations) → 뷰포트에서 숫자가 바로 읽혀야 정상, 거울·뒤집힘이면 §7 #4에 기록.
- **출력 파일 목록**(정확히 이것만; 대소문자 포함):
  ```
  <out>/recon/z_synthetic_scan_001/{scan.obj, scan.mtl, tex/ground.png, tex/facade.1001.png, tex/facade.1002.png, tex/facade.1011.png}
  <out>/zones/z_synthetic_scan_001/v1/{manifest.json, expected.json, blockers.json, blockers.glb, collision.glb,
        collision/c_e000_n000.glb, collision/c_w001_n000.glb, visual/c_e000_n000.obj, visual/c_w001_n000.obj, visual/scan.mtl, visual/chunk_manifest.json}
  --interior 추가:
  <out>/recon/z_synthetic_scan_001_room/{room.obj, room.mtl, tex/room.1001.png}
  <out>/zones/z_synthetic_scan_001_room/v1/{manifest.json, expected.json, collision.glb, collision/c_e000_n000.glb, visual/c_e000_n000.obj, visual/room.mtl, visual/chunk_manifest.json}
  ```

### 4. 데이터 구조

#### 4-1. 임포트 계획 dict (`_pure.import_plan`)
키 순서 고정, 리스트는 id/이름순 정렬(테스트가 dict 동등 비교). 예시는 합성 zone(실외):
```json
{
  "schema": 1,
  "zone_id": "z_synthetic_scan_001", "version": 1, "kind": "exterior", "parent_zone": null,
  "zone_dir": "<abs …/zones/z_synthetic_scan_001/v1>", "asset_folder": "/Game/Golmok/Zones/z_synthetic_scan_001/v1",
  "content_rel": "Golmok/Zones/z_synthetic_scan_001/v1",
  "copy_files": ["blockers.json", "manifest.json"],
  "textures": [
    {"name": "T_facade", "asset": "/Game/Golmok/Zones/z_synthetic_scan_001/v1/Textures/T_facade", "base": "facade", "ext": "png",
     "dir": "<abs …/recon/z_synthetic_scan_001/tex>", "tiles": [1001, 1002, 1011],
     "files": {"1001": "<abs>/facade.1001.png", "1002": "<abs>/facade.1002.png", "1011": "<abs>/facade.1011.png"},
     "anchor": "<abs>/facade.1001.png", "block_coords": [[0, 0], [1, 0], [0, 1]], "canvas_blocks": [2, 2], "used_by": ["facade"]},
    {"name": "T_ground", "asset": ".../Textures/T_ground", "base": "ground", "ext": "png", "dir": "<abs …/tex>", "tiles": [],
     "files": {"single": "<abs>/ground.png"}, "anchor": "<abs>/ground.png", "block_coords": [], "canvas_blocks": [1, 1], "used_by": ["ground"]}
  ],
  "materials": [
    {"name": "MI_facade", "asset": ".../Materials/MI_facade", "mtl_material": "facade", "mtl": "<abs …/visual/scan.mtl>", "texture": "T_facade"},
    {"name": "MI_ground", "asset": ".../Materials/MI_ground", "mtl_material": "ground", "mtl": "<abs …/visual/scan.mtl>", "texture": "T_ground"}
  ],
  "chunks": [
    {"id": "c_e000_n000", "name": "SM_c_e000_n000", "asset": ".../SM_c_e000_n000", "obj": "<abs …/visual/c_e000_n000.obj>", "mtllib": ["scan.mtl"],
     "bbox_enu": [[0.0, 0.0, 0.0], [15.0, 15.0, 6.0]], "expected_ue_bounds_cm": [[0.0, -1500.0, 0.0], [1500.0, 0.0, 600.0]], "tris": 66,
     "materials": ["facade", "ground"], "slots": {"facade": "MI_facade", "ground": "MI_ground"}, "udim_tiles": [1001, 1011]},
    {"id": "c_w001_n000", "name": "SM_c_w001_n000", "asset": ".../SM_c_w001_n000", "obj": "<abs …/visual/c_w001_n000.obj>", "mtllib": ["scan.mtl"],
     "bbox_enu": [[-15.0, 0.0, -0.3], [0.0, 15.0, 5.0]], "expected_ue_bounds_cm": [[-1500.0, -1500.0, -30.0], [0.0, 0.0, 500.0]], "tris": 66,
     "materials": ["facade", "ground"], "slots": {"facade": "MI_facade", "ground": "MI_ground"}, "udim_tiles": [1001, 1002]}
  ],
  "collision_mode": "chunks",
  "collision": [
    {"id": "c_e000_n000", "name": "SM_z_synthetic_scan_001_collision_c_e000_n000", "asset": ".../SM_z_synthetic_scan_001_collision_c_e000_n000",
     "glb": "<abs …/collision/c_e000_n000.glb>", "bbox_enu": [[0.0, 0.0, 0.0], [15.0, 15.0, 6.0]]},
    {"id": "c_w001_n000", "name": "SM_z_synthetic_scan_001_collision_c_w001_n000", "asset": "...", "glb": "<abs …/collision/c_w001_n000.glb>", "bbox_enu": [[-15.0, 0.0, -0.3], [0.0, 15.0, 5.0]]}
  ],
  "blockers": {"json": "<abs …/blockers.json>", "planes": 1},
  "sublevel": null,
  "problems": [],
  "warnings": []
}
```
규칙:
- 청크 정본은 `manifest.layers.visual.chunks`(id·uri); 각 청크는 `chunk_manifest.chunks`에서 같은 id로 `tris·materials·udim_tiles·bbox_enu`를 가져온다(chunk_manifest bbox가 정본, manifest bbox와 소수 4자리에서 다르면 problem). `mtllib`는 OBJ 첫 `f` 전 `mtllib` 줄(`obj_mtllibs(read_text(obj) 줄)`; 청크 OBJ 헤더 몇 줄만 읽도록 호출자는 첫 200줄만 넘겨도 된다).
- MTL은 `<zone_dir>/visual/<mtllib>`에서 `parse_mtl`; `map_Kd`는 `resolve_map_path(map_kd, mtl_dir)`; 세트는 `udim_group` 결과를 `(dir, base, ext)`로 중복 제거하고 `used_by`에 머티리얼 나열; `name = "T_" + asset_name_safe(base)`; 서로 다른 세트가 같은 `name`이면 problem.
- `materials`는 청크들이 실제로 쓰는 머티리얼 이름 합집합(`chunk_manifest.chunks[].materials`)만; 각 항목의 `texture`는 세트 이름(map_Kd 없음 → problem).
- `collision_mode`: `layers.collision.chunks`가 비어 있지 않으면 `"chunks"`(그 항목만, `bbox_enu`는 manifest 값 또는 null), 아니면 `"single"`([{"id": null, "name": "SM_<zone_id>_collision", "asset", "glb", "bbox_enu": null}]).
- `copy_files` = `["manifest.json"]` + `layers.blockers.uri`(있으면), 정렬. `blockers.planes` = blockers.json의 `planes` 길이(파일 없으면 problem).
- `sublevel` = `kind == "interior"`일 때 `sublevel_package(...)`.
- `kind == "interior"`도 같은 계획(서브레벨·포털 검사는 interior_setup 몫).

#### 4-2. `importer_mapping.json` (캐시)
```json
{"schema": 1, "engine": "5.8.3-…", "obj": {"route": "fbx", "scale": 100.0, "m": [[1,0,0],[0,0,1],[0,-1,0]], "err": 0.0},
 "glb": {"scale": 100.0, "m": [[1,0,0],[0,0,-1],[0,1,0]], "err": 0.0}}
```
(`m` 값은 예시. PC 측정값을 런북 결과 표에 적는다.)

#### 4-3. `import_result.json` (`_pure.result_json`)
```json
{"schema": 1, "zone_id": "…", "version": 1, "asset_folder": "/Game/…", "route": "fbx",
 "obj_mapping": {"scale": 100.0, "m": [[…]], "err": 0.0}, "glb_mapping": {…},
 "assets": [{"kind": "texture|material|chunk|collision|file", "asset": "/Game/… 또는 Content 상대경로", "ok": true,
             "detail": {"tiles": [...], "size": [w, h], "vt": true, "how": "…"} | {"parent": "…", "texture": "…"} | {"tris": n, "bounds_error_cm": 0.0, "slots": {...}, "unmatched": [], "full_precision_uvs": "set"|"on"|null} | {"bounds_error_cm": 0.0} | {"bytes": n}}],
 "warnings": ["…"], "interior": null}
```

#### 4-4. `expected.json` (생성기가 쓰는 정본; 런북·테스트가 인용)
```json
{"schema": 1, "zone_id": "z_synthetic_scan_001", "version": 1,
 "asset_folder": "/Game/Golmok/Zones/z_synthetic_scan_001/v1",
 "content_manifest": "Golmok/Zones/z_synthetic_scan_001/v1/manifest.json",
 "chunks": {
   "c_e000_n000": {"asset": "/Game/Golmok/Zones/z_synthetic_scan_001/v1/SM_c_e000_n000", "tris": 66,
                   "bbox_enu": [[0.0, 0.0, 0.0], [15.0, 15.0, 6.0]], "ue_bounds_cm": [[0.0, -1500.0, 0.0], [1500.0, 0.0, 600.0]],
                   "materials": ["facade", "ground"], "udim_tiles": [1001, 1011], "look": "red facade with door hole (1001), blue block (1011), grey ground"},
   "c_w001_n000": {"asset": "/Game/Golmok/Zones/z_synthetic_scan_001/v1/SM_c_w001_n000", "tris": 66,
                   "bbox_enu": [[-15.0, 0.0, -0.3], [0.0, 15.0, 5.0]], "ue_bounds_cm": [[-1500.0, -1500.0, -30.0], [0.0, 0.0, 500.0]],
                   "materials": ["facade", "ground"], "udim_tiles": [1001, 1002], "look": "green facade with glass window (1002), grey ground"}},
 "collision": {"mode": "chunks", "total_tris": 132,
   "chunks": {"c_e000_n000": {"asset": ".../SM_z_synthetic_scan_001_collision_c_e000_n000", "tris": 66, "ue_bounds_cm": [[0.0, -1500.0, 0.0], [1500.0, 0.0, 600.0]]},
              "c_w001_n000": {"asset": ".../SM_z_synthetic_scan_001_collision_c_w001_n000", "tris": 66, "ue_bounds_cm": [[-1500.0, -1500.0, -30.0], [0.0, 0.0, 500.0]]}}},
 "textures": {"T_facade": {"tiles": [1001, 1002, 1011], "tile_px": 256, "canvas_blocks": [2, 2], "canvas_px": [512, 512],
                           "colors": {"1001": [200, 60, 60], "1002": [60, 200, 60], "1011": [60, 60, 200]}},
              "T_ground": {"tiles": [], "tile_px": 256, "canvas_blocks": [1, 1], "canvas_px": [256, 256], "colors": {"single": [120, 120, 120]}}},
 "materials": ["MI_facade", "MI_ground"], "master_material": "/Game/Golmok/Materials/M_ZoneScan",
 "blockers": {"glass_1": {"center_enu": [-8.0, 5.0, 1.5], "normal_enu": [0.0, -1.0, 0.0], "size_m": [3.0, 2.5],
                          "ue_rel_center_cm": [-800.0, -500.0, 150.0], "ue_extent_cm": [5.0, 150.0, 125.0], "level_ue_cm": [16870.59, -22697.99, 1149.37]}},
 "area_origin": [37.56, 126.923, 40.0], "zone_origin": [37.562, 126.925, 50.0],
 "zone_root_ue_cm": [17670.59, -22198.0, 999.37], "zone_root_yaw_deg": 0.0,
 "player_start_ue_cm": [17670.59, -22398.0, 1149.36],
 "walk": "from PlayerStart (0,2) m: north-west to the green wall (x -11..-5, y 5) - the glass window at x -9.5..-6.5 blocks you although you see through it; east to the red facade (x 1..9, y 7) - the door hole at x 4..6 lets you through (door_1 portal with --interior); the blue block at x 10..13 is a 2 m obstacle",
 "interior": null}
```
`--interior`면 `"interior"`:
```json
{"zone_id": "z_synthetic_scan_001_room", "version": 1, "asset_folder": "/Game/Golmok/Zones/z_synthetic_scan_001_room/v1",
 "origin_in_parent_m": [1.0, 7.2, 0.0], "origin": [37.562064871247316, 126.9250113182482, 50.0],
 "chunks": {"c_e000_n000": {"asset": ".../SM_c_e000_n000", "tris": 60, "bbox_enu": [[0.0, 0.0, -0.2], [8.0, 6.8, 3.2]],
                            "ue_bounds_cm": [[0.0, -680.0, -20.0], [800.0, 0.0, 320.0]], "materials": ["room"], "udim_tiles": [1001], "look": "yellow room (1001)"}},
 "collision": {"mode": "chunks", "total_tris": 60, "chunks": {"c_e000_n000": {"asset": ".../SM_z_synthetic_scan_001_room_collision_c_e000_n000", "tris": 60, "ue_bounds_cm": [[0.0, -680.0, -20.0], [800.0, 0.0, 320.0]]}}},
 "textures": {"T_room": {"tiles": [1001], "tile_px": 256, "canvas_blocks": [1, 1], "canvas_px": [256, 256], "colors": {"1001": [200, 200, 60]}}},
 "materials": ["MI_room"], "sublevel": "/Game/Golmok/Zones/z_synthetic_scan_001_room/v1/L_z_synthetic_scan_001_room",
 "light": {"label": "Interior_Light_z_synthetic_scan_001_room", "interior_local_cm": [400.0, -340.0, 250.0]},
 "zone_root_ue_cm": [17770.58, -22918.0, 999.34],
 "portal_pair": {"parent_portal": "door_1", "interior_portal": "door_out", "parent_enu": [5.0, 7.0, 0.0], "interior_enu": [4.0, -0.2, 0.0],
                 "yaw_deg": [90.0, -90.0], "level_ue_cm": [18170.58, -22898.01, 999.33]}}
```
좌표 수치는 이 문서 작성 시 `golmok_tools.zone.transform`으로 계산한 값(area 원점 37.56/126.923/40; `zone_root_ue_cm`은 스펙 §4 표 C 첫 행과 같다). 테스트가 같은 방식으로 재계산해 ±0.01 cm 안에서 일치를 요구한다.

#### 4-5. `plan_problems` 문자열(정확한 접두; 하나라도 있으면 `ZoneImportError("plan", …)`)
`zone_id invalid: <id>` · `manifest: folder <name> != zone_id <id>` · `manifest: folder v<n> != version <m>` · `visual.format <fmt> is not nanite_mesh (D-010: only nanite_mesh is importable)` · `chunk_manifest.json missing (run golmok-mesh chunk)` · `chunk <id>: invalid id` · `chunk <id>: uri <uri> is not .obj (WP-04/05 GLB fixtures: use synthetic_zone.run())` · `chunk <id>: file missing <path>` · `chunk <id>: not in chunk_manifest.json` · `chunk <id>: bbox mismatch manifest vs chunk_manifest` · `chunk <id>: mtl missing <path>` · `material <m>: not in <mtl> (chunk <id>)` · `material <m>: no map_Kd (chunk <id>)` · `material <m>: texture missing <path>` · `texture <base>: duplicate tile <n>` · `texture <base>: asset name collision T_<name>` · `collision: file missing <path>` · `collision chunk <id>: file missing <path>` · `blockers: file missing <path>` · `chunk_manifest.missing: mtl=[…] textures=[…]` · `interior: parent_zone missing`.
`plan["warnings"]`(계속 진행, `zi.warn`): `texture <name>: '<file>' matches the engine UDIM name rule ([._]####, >= 1001) but not BaseName.1001..1999.ext; imported as a single texture with UDIM detection off (runbook #38)` · `chunk <id>: udim tile <n> not in texture <base> tiles [...]` · `texture <base>: tile 1001 missing; anchor is tile <n>`.

#### 4-6. 로그 형식(`_pure.LOG`, 단일 소스 — 런북 인용과 양방향 드리프트 테스트)
```python
LOG = {
 "zi.plan":      "zone_import: plan {zone_id} v{version}: chunks={chunks} collision={collision} ({collision_mode}) textures={textures} materials={materials} blockers={blockers}",
 "zi.cache":     "zone_import: importer mapping cache {state} -> {path}",
 "zi.route":     "zone_import: obj importer route={route} ({how})",
 "zi.mapping":   "zone_import: {kind} importer mapping scale={scale:.3f} M={m} (fit error {err:.2f} cm)",
 "zi.texture":   "zone_import: texture {asset} tiles={tiles} size={w}x{h} vt={vt} ({how})",
 "zi.material":  "zone_import: material {asset} parent={parent} texture={texture}",
 "zi.chunk":     "zone_import: chunk {asset} tris={tris} bounds ok (error {err:.2f} cm) slots={slots}",
 "zi.collision": "zone_import: collision {asset} bounds ok (error {err:.2f} cm) complex-as-simple nanite=off",
 "zi.cleanup":   "zone_import: deleted importer-created asset {asset}",
 "zi.copied":    "zone_import: copied {files} -> {dest}",
 "zi.geo":       "zone_import: geo origin lat={lat:.6f} lon={lon:.6f} h={h:.3f} ({how})",
 "zi.zone":      "zone_import: zone Zone_{zone_id} rebuilt",
 "zi.done":      "zone_import: done {zone_id} v{version}: {assets} assets, {warnings} warnings -> {result}",
 "zi.warn":      "zone_import: WARNING {message}",
 "zi.error":     "zone_import: ERROR {step}: {message}",
 "is.portal":    "interior_setup: portal {interior_portal}<->{parent_portal} same point (err {dist_m:.3f} m), opposite yaw (err {yaw_err:.1f} deg)",
 "is.rerun":     "interior_setup: removed {n} GolmokInteriorSetup actors from {package}",
 "is.sublevel":  "interior_setup: sublevel {package} actors={actors} (level coordinates)",
 "is.exterior":  "interior_setup: exterior zone Zone_{zone_id} rebuilt",
 "is.done":      "interior_setup: done {zone_id} v{version} -> {result}",
 "is.error":     "interior_setup: ERROR {step}: {message}",
 "sr.prepare":   "spike_runner: viewpoints {level}: {saved} saved, missing={missing}",
 "sr.window":    "spike_runner: PIE window {w}x{h} x{multiplier} ({how})",
 "sr.layers":    "spike_runner: layers tag={tag} zone_visual={zone_visual} Spike_b={spike_b} Spike_c={spike_c} (actors {n}, {where})",
 "sr.level":     "spike_runner: layer level {package} saved (tag {tag})",
 "sr.pie":       "spike_runner: PIE {state} tag={tag}",
 "sr.cmd":       "spike_runner: > {command}",
 "sr.captured":  "spike_runner: captured {path} ({w}x{h})",
 "sr.missing":   "spike_runner: missing {path} ({why})",
 "sr.csv":       "spike_runner: csv {path} -> golmok-perf \"{path}\" --label {label} --markdown",
 "sr.done":      "spike_runner: done {what}: {saved} saved, {missing} missing -> {root}",
 "sr.sheet":     "spike_runner: contact sheet -> {path}",
 "sr.script":    "spike_runner: -game script -> {path} ({runs} runs)",
 "sr.warn":      "spike_runner: WARNING {message}",
 "bm.geo":       "basemap_import: GeoOrigin lat={lat:.6f} lon={lon:.6f} h={h:.3f} (basemap origin; ellipsoidal = DEM orthometric + --geoid-offset)",
}
```
`vt` 값은 `on`/`off`, `tiles`는 `[1001, 1002, 1011]`처럼 파이썬 리스트 repr, `slots`는 `facade=MI_facade,ground=MI_ground`, `files`는 `blockers.json, manifest.json`, `m`은 3×3 튜플 repr, `missing`은 리스트 repr, `actors`는 라벨 리스트 repr.

#### 4-7. dwell 경로 JSON(`_pure.dwell_path_json`, `GolmokStatsMath::FormatPathJson`과 같은 레이아웃; 파서는 version 1·`samples[].t/p/r`·t 단조만 요구)
```
{"version": 1, "name": "vp_far_01", "level": "L_ZoneTest", "hz": 10, "created": "2026-09-24T00:00:00Z", "samples": [
{"t": 0.000, "p": [17670.59, -22398.00, 1149.36], "r": [-10.000, 90.000, 0.000]},
{"t": 600.000, "p": [17670.59, -22398.00, 1149.36], "r": [-10.000, 90.000, 0.000]}
]}
```
(`p` cm 소수 2자리, `r` = [pitch, yaw, roll] 소수 3자리; viewpoints 파일의 `rotation` = [roll, pitch, yaw]를 재배열. `created`는 인자로 주입, 기본 `""`이면 현재 UTC ISO.)

#### 4-8. `-game` 명령줄과 `.ps1`
`_pure.game_command_line(exe, uproject, map_path, walk="walk_01", preset="clear_noon", res=(1920, 1080), log_path=L)` =
```
[exe, uproject, map_path, "-game", "-RenderOffscreen", "-ResX=1920", "-ResY=1080", "-ForceRes", "-ExitAfterCsvProfiling", "-unattended", "-nosplash",
 '-ExecCmds="golmok.hud 0, golmok.tod clear_noon, golmok.path play walk_01 --csv"', "-abslog=" + L]
```
`_pure.powershell_script(runs, path_files, candidates, out_dir, timeout_s)`(각 argv 원소는 `ps_quote`; `runs[i]["argv"][0]`이 exe):
```powershell
# generated by golmok.spike_runner.game_scripts - do not edit
$ErrorActionPreference = 'Continue'
$pathDirs = @('<cand0>\Golmok\Paths', '<cand1>\Golmok\Paths')
$csvDirs = @('<cand0>\Profiling\CSV', '<cand1>\Profiling\CSV')
foreach ($d in $pathDirs) { New-Item -ItemType Directory -Force -Path $d | Out-Null; Copy-Item -Force '<Saved>\Golmok\Paths\walk_01.json' $d }
New-Item -ItemType Directory -Force -Path '<out_dir>' | Out-Null
function Invoke-GolmokRun($label, $exe, $argv, $timeoutSec, $log) {
  $t0 = Get-Date
  $p = Start-Process -FilePath $exe -ArgumentList $argv -PassThru -NoNewWindow
  if (-not $p.WaitForExit($timeoutSec * 1000)) { $p.Kill(); Write-Warning "$label timeout after $timeoutSec s" }
  $csv = Get-ChildItem -Path $csvDirs -Filter 'Profile*.csv' -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -ge $t0 } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($csv) { Copy-Item $csv.FullName (Join-Path '<out_dir>' "$label.csv"); Write-Output "csv $label -> $($csv.FullName)" } else { Write-Warning "$label no CSV newer than $t0 (see $log)" }
  if (-not (Select-String -Path $log -Pattern 'GolmokDebugSubsystem: csv:' -Quiet)) { Write-Warning "$label log has no 'GolmokDebugSubsystem: csv:' line (ExecCmds timing? runbook #17)" }
}
Invoke-GolmokRun 'a_clear_noon_walk_01' '<exe>' @('<uproject>', '/Game/Golmok/Maps/L_ZoneTest', '-game', '-RenderOffscreen', '-ResX=1920', '-ResY=1080', '-ForceRes', '-ExitAfterCsvProfiling', '-unattended', '-nosplash', '-ExecCmds="golmok.hud 0, golmok.tod clear_noon, golmok.path play walk_01 --csv"', '-abslog=<Saved>\Golmok\spike\game_a_clear_noon_walk_01.log') 900 '<Saved>\Golmok\spike\game_a_clear_noon_walk_01.log'
Write-Output 'golmok-perf "<out_dir>\a_clear_noon_walk_01.csv" --label a_clear_noon_walk_01 --markdown'
```
(마지막 줄은 모든 run의 CSV·라벨을 한 명령으로 묶는다. `<cand1>` = `%LOCALAPPDATA%\UnrealEngine\5.8\Saved`; LOCALAPPDATA가 없으면 후보 1개.)

#### 4-9. 컨택트 시트 HTML(`_pure.contact_sheet_html`)
`<!doctype html>`, `<meta charset="utf-8">`, 인라인 CSS(어두운 배경, 격자, `img{max-width:320px}`), `<h1>` 제목, 프리셋마다 `<h2>preset</h2>` + `<table>`: 헤더 `viewpoint | photo(옵션) | (a) 메시 Nanite+Lumen | (b) Cesium splat | (c) XGRIDS LCC | (a+c) 하이브리드`, 행 = 시점 이름(VIEWPOINT_NAMES 순), 셀 `<a href="REL"><img src="REL" loading="lazy" alt="tag/preset/name"></a>`, 없는 이미지 `<td class="missing">missing</td>`; 경로는 `/`만, `html.escape`; 외부 자원 없음. 끝에 `<p>`에 생성 시각 없음(결정적).

#### 4-10. 리포트 템플릿(`_pure.report_template`)
마크다운: `## 조건`(해상도 2560×1440, 프리셋 목록, 시점 10개 이름, 경로 이름) → `### 시각 품질` 표(헤더 `| 항목 | (a) 메시 Nanite+Lumen | (b) Cesium splat | (c) XGRIDS LCC | (a+c) 하이브리드 |`, 행 = `QUALITY_ROWS` 7행, 빈 칸) → `### 시점↔행 매핑` 표(행 이름 → 시점 이름) → `### 성능` (헤더 `| 구성 | 프레임 | 평균 fps | 1% low fps | 프레임 p50 ms | p99 ms | Game ms | Render ms | GPU ms |` = `perf_report.to_markdown` 첫 줄; 아래에 `perf_markdown` 인자를 그대로 붙이고, 비어 있으면 `golmok-perf "<csv>" … --label … --markdown` 명령 한 줄) → `### 제작 비용` 표(`COST_ROWS`) → `### 컨택트 시트`(프리셋별 `Saved/Screenshots/Golmok/contact_sheet.html#<preset>` 링크). 표 헤더·행 이름은 `docs/research/08-spike-results.md`와 문자열이 같아야 한다(테스트가 문서를 파싱).

### 5. 테스트 목록
전체 게이트: `cd tools && ruff check . && ruff format --check . && python -m pytest -q && python scripts/check_repo.py`. 새 의존성 없음. 실행 시간 목표 < 25 s(서브프로세스 1회, PNG 256 px, 가짜 임포터는 파일 파싱만).

#### 5-0. `tools/tests/fake_unreal.py` (스크립트형 가짜 `unreal`; 테스트 헬퍼)
```python
class Fake:
    calls: list[tuple]         # 순서 기록: ("import", basename, dest, dest_name, route), ("delete_directory", path), ("delete_asset", path), ("rename", old, new),
                               # ("save", path), ("create_asset", name, folder, cls), ("set_material", mesh_path, i, mat_path), ("set_nanite", mesh_path, bool),
                               # ("spawn", class_name, label), ("destroy", label), ("rebuild_in_editor", zone_id), ("unload_in_editor", zone_id),
                               # ("set_visual_visible", zone_id, bool), ("hidden_in_game", label, bool), ("console", cmd), ("begin_play",), ("end_play",),
                               # ("load_level", path), ("new_level", path), ("save_current_level",), ("duplicate_asset", src, dst), ("play_settings", w, h)
    registry: dict[str, FakeAsset]     # "/Game/..." → asset (FakeStaticMesh | FakeTexture2D | FakeMaterial | FakeMaterialInstanceConstant | FakeLevel)
    actors: list[FakeActor]; levels: dict[str, list[FakeActor]]; current_level: str
    saved_dir, content_dir, config_dir: str          # tmp_path 아래
    obj_mapping = (100.0, M_OBJ); glb_mapping = (100.0, M_GLB)   # 가짜 임포터가 "적용"하는 매핑(테스트가 바꿈; 기본 M_OBJ=Y-up 변환, M_GLB=glTF 변환)
    obj_routes_ok = {"fbx", "interchange", "legacy_flag"}         # 성공하는 route 집합(사다리 테스트가 줄임)
    udim_merge = True; texture_vt_default = True; importer_makes_materials = True; slot_names_from_usemtl = True
    fail_import: set[str] = set(); bounds_offset: dict[str, tuple] = {}
    pie = False; screenshot_delay_s = 0.3; csv_delay_s = 0.5; screenshot_fallback_name = False; clock = 0.0
    logs: list[tuple[str, str]]     # ("log"|"warning"|"error", text)
def install(monkeypatch, tmp_path, **cfg) -> Fake   # sys.modules.setdefault("unreal", ModuleType("unreal")) 객체에 monkeypatch.setattr(raising=False)로 이름을 덮어씀(테스트 뒤 복원)
def tick(fake, n: int, dt: float = 0.1)           # 등록된 slate 콜백을 n번 호출, clock += dt마다 증가, 지연 파일(스크린샷·CSV)을 만든다; spike_runner._now를 fake 시계로 바꾼다
```
- 가짜 임포터 `AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)`: 태스크 `filename` 확장자로 분기. `.obj`: `task.factory`/`options` 종류로 route를 판정(`FbxFactory` 있음→`fbx`; `InterchangeGenericAssetsPipeline`→`interchange`; 콘솔 `Interchange.FeatureFlags.Import.OBJ 0`이 기록된 뒤 factory 없음→`legacy_flag`), route ∉ `obj_routes_ok`면 빈 결과; 파일을 읽어 `_pure.parse_obj_bounds`에 `scale·M` 적용(+`bounds_offset[basename]`) → `FakeStaticMesh(bounds, slots=usemtl 순서 이름)`; `importer_makes_materials`면 usemtl마다 `FakeMaterial` `<dest>/<name>` 등록·경로 반환. `.glb`: `_pure.glb_bounds_enu`의 **glTF 좌표 그대로**(x, y, z) min/max에 `scale·M` 적용 → `FakeStaticMesh`; 이름 = `destination_name` 우선, 없으면 glTF mesh name. `.png`: IHDR 크기 → `FakeTexture2D(size, vt=texture_vt_default)`; `udim_merge`이고 폴더에 같은 base 타일이 더 있으면 크기 = tile × canvas_blocks; `screenshot`은 무관. 이름 충돌: `replace_existing`이면 덮어씀, 아니면 `_2`. `fail_import`에 basename이 있으면 빈 결과. `imported_object_paths`는 오브젝트 경로(`/Game/A/B.B`) — `list_assets`도 같은 형식(정규화 검사용).
- 클래스: `FakeStaticMesh`(`get_bounding_box()`→`.min/.max`가 `.x/.y/.z`인 객체, `get_path_name`, `get_name`, `get_editor_property("static_materials")`→`[FakeStaticMaterial(material_slot_name)]`, `set_material`, `get_material_index`, `nanite_settings`/`body_setup` 프로퍼티), `FakeTexture2D`(`blueprint_get_size_x/y`, `virtual_texture_streaming`, `srgb` 프로퍼티; vt 설정 시 `Fake.vt_settable`가 False면 무시), `FakeMaterial`, `FakeMaterialInstanceConstant`, `FakeActor`(label, folder, tags, class_name, `get_actor_transform()`→`FakeTransform`(`translation`, `rotation.rotator().yaw`, `transform_location` = 이동만), `set_actor_hidden_in_game`, `set_is_temporarily_hidden_in_editor`, `set_editor_property("tags")`), `FakeZoneActor`(`zone_id`·`version`·`auto_managed` 프로퍼티, `rebuild_in_editor/unload_in_editor/set_visual_visible` 기록; rebuild 시 `get_actor_transform` = `Fake.zone_transform`), `FakeGeoOrigin`, `FakePointLight`, `FakeWorld("editor"|"pie")`, `FakePlaySettings`.
- 서브시스템(`get_editor_subsystem(cls)`는 `cls is module.X` 동일성으로 분기): `EditorActorSubsystem`(`get_all_level_actors`, `spawn_actor_from_class`(클래스 이름으로 Fake 액터 생성·기록), `spawn_actor_from_object`, `destroy_actor(s)`), `LevelEditorSubsystem`(`load_level`(levels 스왑), `new_level`, `save_current_level`, `editor_request_begin_play`→`pie=True`, `editor_request_end_play`→`pie=False`, `is_in_play_in_editor`, `editor_set_viewport_realtime`, `editor_get/set_game_view`, `editor_invalidate_viewports`), `UnrealEditorSubsystem`(`get_editor_world`, `get_game_world`→pie면 `FakeWorld("pie")` 아니면 None, `get_level_viewport_camera_info`), `StaticMeshEditorSubsystem`(`set_nanite_settings` 기록).
- 라이브러리: `EditorAssetLibrary`(`does_asset_exist, load_asset, save_loaded_asset, delete_asset, delete_directory, rename_asset, list_assets(prefix, recursive, include_folder), duplicate_asset, make_directory, does_directory_exist`; 후속 [PR #122](https://github.com/wooklym/golmok/pull/122): `get_tag_values` — Texture2D에 `Dimensions` = 캔버스, 키 `_TagName`, 노브 `dimensions_tag`), `MaterialEditingLibrary`(기록), `MaterialFactoryNew`, `MaterialInstanceConstantFactoryNew`, `MaterialExpression*`(`create_material_expression`→`Recorder`), `SystemLibrary.execute_console_command(world, cmd)`(기록; `golmok.screenshot <tag> <name>` → `screenshot_delay_s` 뒤 `Saved/Screenshots/Golmok/<tag>/<preset>/<name>.png`(`screenshot_fallback_name`이면 `<name>00000.png`) 1바이트+IHDR 헤더 파일, preset = 마지막 `golmok.tod` 인자 또는 `current`; `golmok.path play <p> --csv` → `csv_delay_s` 뒤 `Saved/Profiling/CSV/Profile(<n>).csv`; `golmok.path play vp_x`는 파일 `Saved/Golmok/Paths/vp_x.json` 존재를 검사해 없으면 `Fake.logs`에 error), `SystemLibrary.get_engine_version()`→`"5.8.3-fake"`, `GameplayStatics.get_all_actors_of_class(world, cls)`, `get_player_controller(world, 0)`(pie면 객체), `UDIMTextureFunctionLibrary.make_udim_virtual_texture_from_texture2_ds(...)`→`FakeTexture2D(canvas, vt=True)` 등록+기록, `get_default_object(cls)`→`FakePlaySettings`, `Paths.project_saved_dir/project_content_dir/project_config_dir`, `register_slate_post_tick_callback`/`unregister_…`, `log/log_warning/log_error`→`Fake.logs`, `ScopedSlowTask` no-op, 단순 클래스 `Vector, Rotator, Transform, Name, IntPoint, Box, Actor, AssetImportTask, FbxFactory, FbxImportUI, FbxStaticMeshImportData, FBXImportType, InterchangeGenericAssetsPipeline(중첩 속성 객체), InterchangeForceMeshType, CollisionTraceFlag, MaterialSamplerType, MaterialProperty, TextureCompressionSettings, LevelEditorPlaySettings, PlayModeType, GolmokZone, GolmokGeoOrigin, PointLight, PointLightComponent, ComponentMobility, LightUnits, StaticMesh, Texture2D, Material, MaterialInstanceConstant, LevelStreamingDynamic, EditorLevelUtils.add_level_to_world`. `EditorLevelLibrary`는 기본 **없음**(폴백 테스트가 추가).

#### 5-1. `tools/tests/test_ue_python_pure.py` (가짜 = 빈 `ModuleType("unreal")`)
| 테스트 | 단언 |
|---|---|
| `test_modules_import_with_empty_stub` | 빈 스텁만으로 `_pure, zone_import, interior_setup, spike_runner` import; `_pure.py` 소스에 `unreal`·`numpy`·`golmok_tools` 문자열 없음; `run` 시그니처 3개(`inspect`) |
| `test_asset_paths_match_cpp_manifest_and_synthetic_zone` | `asset_folder/chunk_asset/collision_asset/sublevel_package` == `sz.asset_folder/sublevel_path`(픽스처 manifest); `GolmokZoneManifest.cpp`에 `"/Game/Golmok/Zones/%s/v%d"`, `SM_%s_collision`, `SM_%s_collision_%s`, `L_%s` 존재; `MATERIAL_DIR == materials.MATERIAL_DIR`; `asset_paths()` 키 집합·값 |
| `test_asset_name_safe_and_object_path` | `"my tex.v2"→"my_tex_v2"`, `"1001x"→"_1001x"`, `""`→ValueError; `object_path` |
| `test_udim_tile_of_official_rule_only` | `T_alley.1002.png`→1002, `x.png`→None, `a.1000.png`→None, `a.2001.png`→None, `a.1001.PNG`→1001, `a.b.1001.png`→(base `a.b`), `a_1002.png`→None + `udim_suspect` True |
| `test_udim_block_coords_and_canvas` | 1001→(0,0) 1002→(1,0) 1010→(9,0) 1011→(0,1) 1020→(9,1) 1999→(8,99); `canvas([1001,1002,1011])==(2,2)`, `canvas([])==(1,1)`; 1000·2000 ValueError |
| `test_udim_group_token_explicit_plain` | listdir 주입: 토큰 → tiles [1001,1002,1011], anchor 1001; `room.1001.png` 명시 → tiles [1001]; `ground.png` → tiles [], files {"single"}; 중복 타일 ValueError; 토큰인데 파일 0 → tiles [] anchor None |
| `test_split_map_line_matches_objio` | 10개 줄(`-bm 1`, `-o 1 2`, 공백 파일명, 절대 Windows 경로, `map_Ka`, 비텍스처 줄)에서 `_pure.split_map_line == objio.split_map_line`; `_MAP_OPTS`·`_MAP_KEYS` 동일 |
| `test_parse_mtl_and_resolve` | 순서 유지, Kd, map_Kd None; `resolve_map_path` 상대/절대/`\\` |
| `test_mtl_with_absolute_textures` | map 줄만 절대화, 옵션 접두 유지, 나머지 바이트 동일 |
| `test_obj_streaming_helpers` | `obj_mtllibs`(공백 이름), `usemtl_order`(중복 제거), `parse_obj_bounds`, `probe_obj_text` 8 v·12 f |
| `test_resolve_zone_dir` | v 폴더/zone 폴더+None→최대/version 지정/manifest.json 경로/없음 ValueError 3종 문구 |
| `test_import_plan_shape_from_fixture` | `fixtures/ue/chunk_manifest_min.json` + 만든 manifest + 주입 FS → §4-1 리터럴 dict와 **동일**(정렬·키 순서) — collision_mode `chunks`와 `single` 두 경우 |
| `test_plan_problems_each_case` | §4-5 항목마다 정확히 문자열 1개(21 케이스 parametrize) |
| `test_plan_warnings` | `_####` 이름 경고, 타일 불일치 경고, 1001 없음 경고 |
| `test_slot_assignment_three_stages` | 정확 → 대소문자 → usemtl 순서; unmatched 반환 |
| `test_expected_ue_bounds_matches_spec_and_synthetic_zone` | `[[0,10,0],[10,20,1]]`→`((0,-2000,0),(1000,-1000,100))`; `TARGET == bm.TARGET`; `== sz.expected_ue_bounds([box])`; `bounds_tolerance_cm` |
| `test_measure_mapping_matches_basemap_import` | 48개 부호 순열 × scale {1, 100}: `_pure.measure_mapping(samples) == bm._measure_import_mapping(samples)`(가짜 unreal로 bm import) |
| `test_resolve_geo_origin` | None+existing→kept; None+없음→zone origin; "area"; "zone"; 튜플; basemap 경로(read_json 주입) |
| `test_pretransform_obj_roundtrip_48_mappings` | 매핑 48종 × scale(1, 100): `v` 변환 후 가짜 임포터(scale·M) 적용 = TARGET·enu(±1e-4); `vt/usemtl/mtllib/# 한글 주석` 바이트 동일; `v x y z r g b` 색 유지 |
| `test_pretransform_obj_normals_and_winding` | det(A)<0 매핑: `vn`이 `U·n`, `f 1/1/1 2/2/2 3/3/3` → `f 3/3/3 2/2/2 1/1/1`; det>0이면 순서 유지; `mtllib` 치환 |
| `test_pretransform_glb_positions_normals_indices` | `sz.boxes_glb` 2박스: 변환 후 `read_glb`(기존 헬퍼)로 위치·법선·accessor min/max 일치, det<0이면 인덱스 반전(기하 법선·저장 법선 부호 일치 유지), 길이 4배수, rename 적용, 다른 accessor 불변 |
| `test_glb_bounds_and_triangle_count` | boxes_glb([box]) → bounds == box, tris 12 |
| `test_gltf_conjugate` | `G·A·G⁻¹`가 glTF 좌표에서 같은 변환(ENU 왕복) |
| `test_png_size` | `write_png_rgb` 출력 IHDR 파싱; 잘못된 헤더 ValueError |
| `test_log_formats_are_quoted_in_runbook` | 두 런북 본문에 `log_prefixes()` 값 전부 등장; 런북 ```` ``` ```` 블록 안 `zone_import:|interior_setup:|spike_runner:|basemap_import:` 줄의 접두가 모두 `log_prefixes()`에 있음 |
| `test_result_json_and_cache_shape` | 키 집합; `importer_cache_valid` 참/거짓 4경우 |
| `test_portal_pair_and_round_trip_on_fixtures` | z_synthetic_001 / _interior 픽스처: dist < 0.01 m, yaw_err < 0.01°; interior yaw −80 → ok False; 포털 0개·2개 ValueError |
| `test_interior_sublevel_specs` | 실내 픽스처: 라벨 `Interior_Light_z_synthetic_001_interior`, 위치 (0, 0, 250), tags `["GolmokInteriorSetup"]`, 3000 cd/3000 K |
| `test_viewpoints_presets_match_research_08` | `VIEWPOINT_NAMES` 3/4/3, `QUALITY_ROWS` 행 이름·`TAG_COLUMNS`·`COST_ROWS`가 `docs/research/08-spike-results.md` 표와 같음; `DEFAULT_PRESETS == tuple(lighting_presets.load_presets()[0])[:3]`이고 문서 "조건" 줄에 나열 |
| `test_layer_state_actor_group_jobs` | 4태그 표; `Spike_b_lcc`→spike_b; `Spike_x`→None; 태그 `d` ValueError; `capture_jobs` tag-major |
| `test_dwell_path_json_matches_cpp_layout` | 정규식 `^\{"version": 1, "name": "…", "level": "…", "hz": 10, "created": "…", "samples": \[\n\{"t": 0\.000, "p": \[…\], "r": \[…\]\},\n\{"t": 600\.000, …\}\n\]\}\n$`; `json.loads`; r 순서 pitch,yaw,roll; `GolmokStatsMath.h`에 `"version"`, `"samples"`, `"t"`, `"p"`, `"r"` 문자열 존재 |
| `test_validate_name_exec_cmds_game_command_line` | `walk 01`, `a,b` ValueError; `exec_cmds` 정확 문자열; `game_command_line` argv 리터럴(§4-8), `-csvCaptureFrames` 없음 |
| `test_saved_dir_candidates_newest_file` | LOCALAPPDATA 있음/없음; `newest_file`이 not_before 뒤 파일 중 최신 |
| `test_powershell_script_quoting_and_layout` | 공백·`'` 경로가 `'"…"'`로, `-ExecCmds="…"`는 그대로 한 원소; 스크립트에 `Copy-Item` 후보 2곳, `Invoke-GolmokRun` 줄 수 = runs, 마지막 `golmok-perf` 줄 |
| `test_screenshot_paths` | `screenshot_path` C++ 규칙(`DefaultGame.ini`의 `ScreenshotFolder` 읽어 대조), `screenshot_fallback_path` |
| `test_contact_sheet_html` | 4태그×2프리셋×3시점 → `<table>` 2개, `<img` 수 = 존재 이미지 수, missing 셀 수, 경로 `/`만, `<`·`&` 이스케이프, 사진 열·`file:///` |
| `test_report_template_matches_research_08` | 세 표 헤더·행 이름 == 문서; 성능 헤더 == `perf_report.to_markdown([])` 첫 줄 |
| `test_summary_lines_mention_every_asset` | result의 모든 asset 경로가 한 줄씩 |
| `test_no_unreal_api_outside_touchpoint_list` | `zone_import.py`·`interior_setup.py`·`spike_runner.py`·`materials.py`(신규 함수 범위)에서 `unreal\.([A-Za-z_]\w*)` 식별자 집합 ⊆ `KNOWN_OK`(테스트가 기존 모듈 `basemap_import/synthetic_zone/viewpoints/lighting/materials/setup_dev_level.py` 소스에서 같은 정규식으로 모은 이름 ∪ 상수 `{"log", "log_warning", "log_error"}`) ∪ `pc-verify-wp06.md` §12 표(=이 문서 §7)에 `unreal.<Name>`으로 적힌 이름; 위반 메시지는 이름과 파일:줄 |

#### 5-2. `tools/tests/test_make_synthetic_zone.py` (`pytest.importorskip("scipy")`, `("fast_simplification")` — CI는 설치)
| 테스트 | 단언 |
|---|---|
| `test_script_runs_in_subprocess_with_unicode_path` | `subprocess.run([sys.executable, script, "--out", str(tmp/"합성 zone"), "--interior"], encoding="utf-8", capture_output=True)` → rc 0, stdout ASCII, §3-7 파일 목록과 **정확히** 같은 집합(대소문자, 여분 없음) |
| `test_output_validates_strict` | `zone_main(["validate","--check-files","--strict", m]) == 0` 실외·실내 |
| `test_expected_json_matches_files` | OBJ `f` 줄 수·`parse_obj_bounds`, chunk_manifest tris/bbox/udim_tiles/materials, PNG IHDR·중앙 픽셀 색(zlib 디코드), collision GLB tri 수(`read_glb`), blockers.json == expected |
| `test_geometry_numbers` | 청크 2개 id, 66/66 tri, bbox 리터럴, 실내 60 tri, `chunk_manifest.missing == {"mtl": [], "textures": []}`, `visual/scan.mtl`에 `../../../../recon/z_synthetic_scan_001/tex/facade.<UDIM>.png`와 `-bm 1`, `tex/ground.png` 절대경로가 `chunk_manifest.textures`에 |
| `test_ue_bounds_in_expected_are_target_of_bbox` | `_pure.expected_ue_bounds(bbox_enu) == ue_bounds_cm` 청크·충돌 |
| `test_level_coordinates_match_spec_table_c` | `golmok_tools.zone.transform`로 재계산 == expected `zone_root_ue_cm`(17670.59, −22198.00, 999.37), `portal_pair.level_ue_cm`, 실내 `zone_root_ue_cm`, blocker `level_ue_cm`(±0.01) |
| `test_door_hole_and_room_do_not_overlap` | 실외 OBJ·collision.glb의 어떤 면 중심도 문 구멍(x 4..6, y 7..7.2, z 0..2.2)·창 구멍(x −9.5..−6.5, y 5..5.2, z 0.25..2.75) 안에 없음; 방 bbox(실외 좌표 x1..9, y7.2..14, z−0.2..3.2)가 실외 박스(A·B·C 조각) 어느 것과도 교차하지 않음; door_1 위치가 구멍 x 중앙 |
| `test_interior_portal_round_trip` | 두 manifest에 `_pure.portal_round_trip_check` ok, dist < 0.005 m; 실내 origin == 실외 (1, 7.2, 0) 1 mm 안 |
| `test_png_tiles_named_colored_numbered` | 파일명, 배경색, 좌상단 흰 사각형 개수 1/2/3, 숫자 영역에 흰 픽셀 있음(ground.png는 없음), 2 px 테두리 |
| `test_deterministic_and_check_mode` | 두 번 생성 텍스트 바이트 동일(`<out>` 치환) + PNG 픽셀 동일; `--check` 0; 파일 수정 → `--check` 1; `--force` 없이 재실행 2 |
| `test_round_trip_plan` | `_pure.import_plan`(실제 FS) → `problems == []`, `collision_mode == "chunks"`, 에셋 집합 == expected(chunks/collision/textures/materials), canvas_blocks 일치 |
| `test_no_dev_only_imports` | 소스에 `PIL`, `trimesh`, `fast_simplification`, `pygltflib` import 없음; 5×7 글꼴 10자 모두 7행×5열 |

#### 5-3. `tools/tests/test_ue_python_zone_import.py` (fake_unreal + 생성기 출력)
| 테스트 | 단언 |
|---|---|
| `test_run_call_order_and_registry` | `Fake.calls` 종류 순서: import `_probe.obj`(route fbx) → delete_directory(_probe) → import `_probe.glb` → delete_directory → import `facade.1001.png` → import `ground.png` → create `M_ZoneScan` → create `MI_facade`, `MI_ground` → import `SM_c_e000_n000.obj` → delete_asset(임포터 머티리얼 2) → set_nanite True → set_material×2 → save → import `SM_c_w001_n000.obj` … → import `SM_z_synthetic_scan_001_collision_c_e000_n000.glb` → set_nanite False → save → … → copy(파일 2개 존재) → spawn GeoOrigin → spawn GolmokZone → rebuild_in_editor → save_current_level. 레지스트리 == expected 에셋 집합 ∪ {M_ZoneScan}; `_probe`·`_tiles` 없음; `collision.glb`(단일)는 임포트되지 않음 |
| `test_bounds_are_zone_local_ue_cm` (parametrize 매핑 3종 × obj/glb) | 각 SM 에셋 `bounds == ue_bounds_cm`(±0.01) |
| `test_route_ladder` | `obj_routes_ok={"interchange"}` → route interchange, `zi.route` 로그; `{"legacy_flag"}` → 콘솔 `Interchange.FeatureFlags.Import.OBJ 0` 기록 뒤 성공; `set()` → `ZoneImportError` probe 메시지에 세 route 이름 |
| `test_importer_cache_hit_and_remeasure` | 두 번째 run은 프로브 import 없음(`zi.cache` hit); `remeasure=True`면 다시 측정; 엔진 버전 다르면 miss |
| `test_plan_problem_aborts_before_any_editor_call` | 청크 파일 삭제 → 메시지에 `file missing`; `Fake.calls == []` |
| `test_bounds_mismatch_raises_and_places_no_zone` | `bounds_offset["SM_c_e000_n000.obj"]=(50,0,0)` → 메시지에 청크 id·`50.00 cm`·`remeasure=True`; `("spawn","GolmokZone",…)` 없음; `_probe` 삭제됨 |
| `test_texture_vt_enabled_after_import` | `texture_vt_default=False` → vt True, 로그 `vt=on (single texture, vt enabled after import)` |
| `test_udim_pack_fallback` | `udim_merge=False` → 타일 3개 `_tiles` 임포트 + `make_udim…` block_coords `[(0,0),(1,0),(0,1)]`; `_tiles` 삭제; `T_ground`는 폴백 안 탐; 로그 `packed from 3 tiles` |
| `test_udim_fallback_without_library_warns` | + 라이브러리 제거 → `zi.warn`, `T_facade` = 1001 타일, 예외 없음 |
| `test_novt_master_when_vt_cannot_be_enabled` | `vt_settable=False` → `M_ZoneScan_NoVT` 생성, 그 텍스처의 MI parent가 NoVT |
| `test_importer_materials_deleted_and_slots_assigned` | 임포터 부산물 삭제 기록; 각 청크 `set_material(i, MI_<slot>)` |
| `test_slot_fallback_usemtl_order` | `slot_names_from_usemtl=False`(슬롯 이름 `Material_0/1`) → usemtl 순서로 할당 + warn 0; 알 수 없는 슬롯 `stray` → warn 1 |
| `test_texture_options_hops` | `_texture_options()`가 `material_pipeline.texture_pipeline.import_udi_ms=True`, `material_pipeline.import_materials=False`를 설정; 클래스 없으면 None |
| `test_geo_origin_rules` | 액터 없음+None → 스폰·manifest origin·how; 있음+None → kept; `"area"` → 스펙 값 |
| `test_content_copy_exact_two_files` | `<content>/Golmok/Zones/<id>/v1/` 안에 정확히 `manifest.json`·`blockers.json`(바이트 동일), 그 외 없음 |
| `test_rerun_replaces_not_duplicates` | 두 번 run → 레지스트리 크기 동일, `_2` 없음, 모든 태스크 `replace_existing`; `reimport_textures=False`면 텍스처 import 0회 + `skipped: exists` |
| `test_hasattr_branches` | `FbxImportUI` 제거 → options None + warn; `StaticMeshEditorSubsystem.set_nanite_settings` 제거 → 프로퍼티 경로; `get_engine_version` 제거 → 캐시 항상 miss |
| `test_result_json_written` | 파일 존재·형태·route·매핑 |
| `test_import_failure_message_names_file` | `fail_import={"SM_c_w001_n000.obj"}` → 메시지에 `no asset imported from …SM_c_w001_n000.obj` |
| `test_single_collision_mode` | manifest에서 `collision.chunks` 제거 → `SM_<id>_collision` 하나 임포트 |
| `test_basemap_import_sets_geo_origin` | `bm._set_geo_origin({...})` → 없으면 스폰·값, 있으면 갱신, `bm.geo` 로그 |

#### 5-4. `tools/tests/test_ue_python_interior_setup.py`
| 테스트 | 단언 |
|---|---|
| `test_requires_interior_kind_and_parent_manifest` | 실외 폴더 → `kind must be interior`; 부모 content manifest 없음 → `run zone_import.run on the parent zone first`; 둘 다 `Fake.calls == []` |
| `test_portal_mismatch_aborts_before_editor` | 실내 포털 yaw 수정 → `ZoneImportError` step `portal`, calls 비어 있음 |
| `test_run_sequence` | import_assets 호출들 → spawn Zone(room) → rebuild → unload → save_current_level → new_level(L_…room) → spawn PointLight(위치 = transform(spec), tags) → save_current_level → load_level(원 레벨) → rebuild(부모) → save_current_level 순서 |
| `test_sublevel_contains_only_allowed_classes` | 서브레벨이 열린 동안 스폰 클래스 ⊆ {PointLight}; `FORBIDDEN_SUBLEVEL_CLASSES` 없음 |
| `test_rerun_deletes_only_tagged_actors` | 레지스트리에 L_ 있음, 서브레벨에 `Interior_Light_*`(태그 있음)·`Prop_chair`(태그 없음) → 태그 액터만 destroy, `is.rerun` n=1, `Prop_chair` 생존 |
| `test_parent_zone_actor_missing_errors` | `Zone_<parent> not in level` |
| `test_register_path_b` | `register=True` → `add_level_to_world` 기록 |

#### 5-5. `tools/tests/test_ue_python_spike_runner.py`
| 테스트 | 단언 |
|---|---|
| `test_prepare_reports_missing` | 시점 JSON 4개 → missing 6개 정렬, `sr.prepare` |
| `test_configure_pie_window` | `play_settings` 호출 (1280, 720) + `sr.window`; 클래스 없으면 how=`manual…` + warn |
| `test_apply_layers_editor_and_pie` | 액터 `Zone_x`, `Spike_b_lcc`, `Spike_c_tiles`, `Other` → 태그별 호출 표(에디터·PIE 월드) |
| `test_pie_capture_sequence_and_files` | tags ("a","b"), presets 2, names 2 → `tick(fake, 5000)` 뒤 콘솔 순서(태그당 begin/end 1회, `golmok.hud 0` 1회, `golmok.tod` 프리셋 바뀔 때만, `golmok.path play vp_<n>`·`golmok.screenshot <tag> <n>`·`golmok.path stopplay` 매 시점), 경로 JSON 8개 == `dwell_path_json`(t 600), PNG 8개, `sr.captured` 크기 포함, `sr.done` "8 saved, 0 missing" |
| `test_pie_capture_accepts_fallback_filename` | `screenshot_fallback_name=True` → `<name>00000.png`가 `<name>.png`로 개명, saved 8 |
| `test_pie_capture_missing_file_continues` | `screenshot_delay_s=10_000` → 타임아웃 → `sr.missing (timeout)` 뒤 다음 job, 끝에 end_play |
| `test_pie_capture_exception_finishes_cleanly` | `execute_console_command` 예외 → `_finish(warn)` + end_play + 콜백 해제 |
| `test_pie_start_timeout` | `begin_play`가 pie를 켜지 않음 → 60 s 뒤 `_finish("PIE did not start")` |
| `test_pie_world_fallback` | `get_game_world` None + `EditorLevelLibrary.get_pie_worlds` 추가 → 사용 + warn |
| `test_editor_capture_chains_tags` | `viewpoints.capture` monkeypatch(즉시 on_done) → 태그 4개 순서·apply_layers 4회 |
| `test_pie_perf_waits_for_csv` | `golmok.path play walk_01 --csv` 후 CSV 생성까지 대기 → `sr.csv` 명령 문자열 `golmok-perf "<path>" --label a_clear_noon_walk_01 --markdown` |
| `test_game_scripts_written` | `.ps1` utf-8-sig·`\r\n`, run 수 = tags×presets×paths, 본문 == `powershell_script(...)`; 경로 파일 없으면 RuntimeError |
| `test_save_layer_levels` | duplicate_asset(L_ZoneTest → L_Spike_b) → load → 레이어 → auto_managed False → save → 원 레벨 load 순서 (2026-09-28 Save As로 대체 — 결과 절) |
| `test_contact_sheet_and_report_written` | HTML 존재·`a/clear_noon/far_01.png` 상대경로; report md에 research/08 헤더 |

#### 5-6. Windows CI 위험과 회피
| 위험 | 회피 |
|---|---|
| cp1252 콘솔 | 스크립트 stdout ASCII만; 테스트 subprocess `encoding="utf-8"`, `PYTHONUTF8=1` 상속 |
| 경로 구분자·대소문자 | `pathlib`; 에셋 경로·MTL은 `/`; 파일 목록은 정확한 이름 집합 비교 |
| argv 32 KiB | 인자는 `--out` 1개 |
| `newline` | 텍스트 출력 `newline="\n"`; `.ps1`만 `\r\n`; `--check`는 정규화 후 비교 |
| zlib 버전 차이(PNG 바이트) | 테스트·`--check`는 픽셀 비교 |
| 비ASCII tmp 경로 | 일부러 `"합성 zone"` |
| 파일 잠금 | 가짜 unreal은 파일을 `with`로만 연다 |
| 시간 | `dwell_path_json(created=)` 주입; `spike_runner._now` 가짜 시계; 생성기 출력에 타임스탬프 없음 |

### 6. 런북 골자

#### 6-1. `docs/runbooks/pc-verify-wp06.md` (V-04; 각 항목 = 명령 · 기대 로그 · 기대 상태 · 실패 시)
0. **대상 파일 표**(§1) · 전제: V-03(WP-04/05 런북) 통과, `L_ZoneTest` 존재, `cd tools; pip install -e ".[zone,mesh,dev]"; pytest -q` 초록, 디스크 여유(OBJ 사본 = 원본 텍스트 크기). 규칙: 기대 로그는 코드의 `_pure.LOG`에서 옮겨 적은 것(테스트가 드리프트를 잡음), 수정 커밋은 `WP-06: PC fix …`, 로그 문자열을 바꾸면 `_pure.LOG`와 이 문서를 함께.
1. **합성 zone 생성(PowerShell, tools venv)** — `python tools\scripts\make_synthetic_zone.py --out D:\golmok_synth --interior` → `wrote zones/z_synthetic_scan_001/v1/manifest.json` … `next: …` · `golmok-zone validate --check-files --strict D:\golmok_synth\zones\z_synthetic_scan_001\v1\manifest.json` → `OK` · 탐색기: `recon\z_synthetic_scan_001\tex\facade.1001.png`(빨강, 숫자 1001, 흰 사각형 1개)·`1002.png`(초록, 2개)·`1011.png`(파랑, 3개)·`ground.png`(회색, 숫자 없음) · 실패: pytest가 초록이면 환경(권한·경로); `--force`.
2. **`zone_import.run`** — Output Log(Python): `import golmok.zone_import as zi; r = zi.run(r"D:\golmok_synth\zones\z_synthetic_scan_001", level="/Game/Golmok/Maps/L_ZoneTest", geo_origin="area")` · 기대 로그(값은 `expected.json`; `…` = 매핑 실측):
   ```
   zone_import: plan z_synthetic_scan_001 v1: chunks=2 collision=2 (chunks) textures=2 materials=2 blockers=1
   zone_import: importer mapping cache miss -> <Project>\Saved\Golmok\zone_import\importer_mapping.json
   zone_import: obj importer route=fbx (probe imported 1 static mesh)
   zone_import: obj importer mapping scale=… M=… (fit error 0.00 cm)
   zone_import: glb importer mapping scale=… M=… (fit error 0.00 cm)
   zone_import: texture /Game/Golmok/Zones/z_synthetic_scan_001/v1/Textures/T_facade tiles=[1001, 1002, 1011] size=512x512 vt=on (merged by importer)
   zone_import: texture /Game/Golmok/Zones/z_synthetic_scan_001/v1/Textures/T_ground tiles=[] size=256x256 vt=on (single texture, vt enabled after import)
   zone_import: material /Game/Golmok/Zones/z_synthetic_scan_001/v1/Materials/MI_facade parent=/Game/Golmok/Materials/M_ZoneScan texture=T_facade
   zone_import: material /Game/Golmok/Zones/z_synthetic_scan_001/v1/Materials/MI_ground parent=/Game/Golmok/Materials/M_ZoneScan texture=T_ground
   zone_import: chunk /Game/Golmok/Zones/z_synthetic_scan_001/v1/SM_c_e000_n000 tris=66 bounds ok (error 0.00 cm) slots=facade=MI_facade,ground=MI_ground
   zone_import: chunk /Game/Golmok/Zones/z_synthetic_scan_001/v1/SM_c_w001_n000 tris=66 bounds ok (error 0.00 cm) slots=facade=MI_facade,ground=MI_ground
   zone_import: collision /Game/Golmok/Zones/z_synthetic_scan_001/v1/SM_z_synthetic_scan_001_collision_c_e000_n000 bounds ok (error 0.00 cm) complex-as-simple nanite=off
   zone_import: collision /Game/Golmok/Zones/z_synthetic_scan_001/v1/SM_z_synthetic_scan_001_collision_c_w001_n000 bounds ok (error 0.00 cm) complex-as-simple nanite=off
   zone_import: copied blockers.json, manifest.json -> <Project>\Content\Golmok\Zones\z_synthetic_scan_001\v1
   zone_import: geo origin lat=37.560000 lon=126.923000 h=40.000 (spec area origin)
   LogGolmok: Zone z_synthetic_scan_001 v1 root: zone-local (0,0,0) -> UE (17670.59, -22198.00, 999.37) cm; (10,0,0) m -> (18670.59, -22198.02, 999.34) cm; yaw -0.0012 deg
   LogGolmok: Zone z_synthetic_scan_001 v1 loaded in x ms: chunks 2/2 (0 wire boxes), collision 2/2, blockers 1/1, portals 1 (WP-05)
   zone_import: zone Zone_z_synthetic_scan_001 rebuilt
   zone_import: done z_synthetic_scan_001 v1: 8 assets, 0 warnings -> <Project>\Saved\Golmok\zone_import\z_synthetic_scan_001\v1\import_result.json
   ```
   (`size=` 표기가 `256x256`처럼 다르면 §7 #4에 실제 표기를 적는다; `vt enabled after import`가 붙는지 여부는 임포터 기본값 기록.)
   - [ ] 콘텐츠 브라우저 `/Game/Golmok/Zones/z_synthetic_scan_001/v1/`: `SM_c_e000_n000`, `SM_c_w001_n000`, `SM_z_synthetic_scan_001_collision_c_e000_n000`, `SM_z_synthetic_scan_001_collision_c_w001_n000`, `Textures/T_facade`, `Textures/T_ground`, `Materials/MI_facade`, `Materials/MI_ground` — **그 외 없음**(`_probe`·`_tiles`·임포터 머티리얼 남아 있으면 §7 #1·#6). `/Game/Golmok/Materials/M_ZoneScan` 존재(`_NoVT` 없음).
   - [ ] `T_facade`: Virtual Texture Streaming ✔, sRGB ✔, 512×512(UDIM 2×2), 미리보기 빨강(좌하)·초록(우하)·파랑(좌상), 숫자가 바로 읽힘(거울/뒤집힘이면 §7 #4).
   - [ ] `SM_c_e000_n000`: Nanite ✔, 슬롯 `facade`→`MI_facade`, `ground`→`MI_ground`, Approx Size 1500×1500×600 cm; `SM_…_collision_c_e000_n000`: Collision Complexity "Use Complex Collision As Simple", Nanite ✖.
   - [ ] 아웃라이너 `Golmok/GeoOrigin`(37.56/126.923/40), `Golmok/Zones/Zone_z_synthetic_scan_001` 위치 (17670.59, −22198.00, 999.37) cm, 청크 컴포넌트 2·충돌 2·`Blocker_glass_1`(상대 (−800, −500, 150), extent (5, 150, 125)).
   - [ ] 뷰포트: 회색 경사 지면 30×15 m, 동쪽 빨간 벽(문 구멍)·파란 블록, 서쪽 초록 벽(창 구멍 + 시안 blocker 와이어), 벽마다 타일 숫자.
   - 실패: `ZoneImportError plan:` → 메시지대로; `probe` → §7 #1(route 사다리 로그 확인); `chunk … imported bounds` → §7 #2(`import_result.json` mapping을 결과 표에); 텍스처 `vt=off`·`tile 1001 only (WARNING)` → §7 #3·#4·#5.
3. **PIE 걷기** — PlayerStart를 `expected.json.player_start_ue_cm`(17670.59, −22398.00, 1149.36)에 · `golmok.zone.list` → `z_synthetic_scan_001 … loaded` · 북서쪽 초록 벽 창(x −9.5..−6.5 m)에서 유리에 막힘(보이지만 못 지나감), 벽 조각에도 막힘 · 동쪽 빨간 벽 문 구멍(x 4..6 m)은 통과 · 파란 블록 위로 못 올라감 · 지면 경사 보행 OK · 실패: 지면을 뚫으면 충돌 에셋 Complexity; 유리를 지나가면 `blockers.json` 복사·`Blocker_glass_1` 확인.
4. **`interior_setup.run`** — `import golmok.interior_setup as it; it.run(r"D:\golmok_synth\zones\z_synthetic_scan_001_room", level="/Game/Golmok/Maps/L_ZoneTest")` · 기대:
   ```
   interior_setup: portal door_out<->door_1 same point (err 0.000 m), opposite yaw (err 0.0 deg)
   zone_import: plan z_synthetic_scan_001_room v1: chunks=1 collision=1 (chunks) textures=1 materials=1 blockers=0
   zone_import: importer mapping cache hit -> <Project>\Saved\Golmok\zone_import\importer_mapping.json
   zone_import: texture /Game/Golmok/Zones/z_synthetic_scan_001_room/v1/Textures/T_room tiles=[1001] size=256x256 vt=on (single texture)
   zone_import: material /Game/Golmok/Zones/z_synthetic_scan_001_room/v1/Materials/MI_room parent=/Game/Golmok/Materials/M_ZoneScan texture=T_room
   zone_import: chunk /Game/Golmok/Zones/z_synthetic_scan_001_room/v1/SM_c_e000_n000 tris=60 bounds ok (error 0.00 cm) slots=room=MI_room
   zone_import: collision /Game/Golmok/Zones/z_synthetic_scan_001_room/v1/SM_z_synthetic_scan_001_room_collision_c_e000_n000 bounds ok (error 0.00 cm) complex-as-simple nanite=off
   zone_import: copied manifest.json -> <Project>\Content\Golmok\Zones\z_synthetic_scan_001_room\v1
   LogGolmok: Zone z_synthetic_scan_001_room v1 root: zone-local (0,0,0) -> UE (17770.58, -22918.00, 999.34) cm; …
   LogGolmok: Zone z_synthetic_scan_001_room v1 loaded in x ms: chunks 1/1 (0 wire boxes), collision 1/1, blockers 0/0, portals 1 (WP-05)
   LogGolmok: Zone z_synthetic_scan_001_room v1 unloaded
   interior_setup: sublevel /Game/Golmok/Zones/z_synthetic_scan_001_room/v1/L_z_synthetic_scan_001_room actors=['Interior_Light_z_synthetic_scan_001_room'] (level coordinates)
   LogGolmok: Zone z_synthetic_scan_001: portal door_1 -> z_synthetic_scan_001_room rel (500, -700, 0) cm yaw -90.0 radius 100 cm -> level (18170.58, -22898.01, 999.33) [entry]
   interior_setup: exterior zone Zone_z_synthetic_scan_001 rebuilt
   interior_setup: done z_synthetic_scan_001_room v1 -> <Project>\Saved\Golmok\zone_import\z_synthetic_scan_001_room\v1\import_result.json
   ```
   - [ ] 콘텐츠 브라우저 `…/z_synthetic_scan_001_room/v1/`: `SM_c_e000_n000`, `SM_z_synthetic_scan_001_room_collision_c_e000_n000`, `Textures/T_room`, `Materials/MI_room`, `L_z_synthetic_scan_001_room`; Levels 창에 등록 **없음**(LevelInstance). 서브레벨을 열면 `Golmok/Interior/Interior_Light_z_synthetic_scan_001_room`(태그 `GolmokInteriorSetup`)만, PPV·DirectionalLight·Zone 없음.
   - 실패: `ERROR portal:` → 생성기 재실행(`--force`); `Zone_z_synthetic_scan_001 not in level` → §2 먼저; `ERROR parent: no Content manifest` → §2의 copied 로그 확인.
5. **PIE 포털 왕복** — 빨간 벽 문(x 5, y 7 m; PlayerStart에서 동 5 m·북 5 m)으로 북진 → WP-05 런북 §5와 같은 순서:
   ```
   LogGolmok: Zone z_synthetic_scan_001_room v1 loaded in x ms: chunks 1/1 (0 wire boxes), collision 1/1, blockers 0/0, portals 1 (WP-05)
   LogGolmok: Portal door_1 (z_synthetic_scan_001 -> z_synthetic_scan_001_room): player within 100 cm -> load [zone z_synthetic_scan_001_room loaded (pinned)]; sublevel /Game/Golmok/Zones/z_synthetic_scan_001_room/v1/L_z_synthetic_scan_001_room (LevelInstance)
   LogGolmok: TimeOfDay: interior overlay on (source door_1, base (level))
   LogGolmok: Portal door_1: crossed inward
   LogGolmok: TimeOfDay: interior overlay off -> (level)
   LogGolmok: Portal door_1: crossed outward
   LogGolmok: Zone z_synthetic_scan_001_room v1 unloaded
   LogGolmok: Portal door_1: player left -> unload z_synthetic_scan_001_room; sublevel out
   ```
   노란 방(8×6.8 m)·따뜻한 PointLight; 서·동·북 벽·천장에 막힘, 남쪽은 빨간 벽(문 구멍만 통과). 실패: WP-05 §5 표대로(부호 반전이면 §11 #8 그 문서).
6. **재실행 idempotency** — §2를 `zi.run(..., reimport_textures=False)`로, §4를 다시: 에셋 덮어쓰기(`_2` 없음), `texture … (skipped: exists)`, 아웃라이너 액터 중복 없음, 서브레벨에 손으로 놓은 큐브가 살아남고 `interior_setup: removed 1 GolmokInteriorSetup actors from …` 로그.
7. **spike_runner 리허설(합성 zone)** — `import golmok.viewpoints as v; v.save("far_01")` … 10개(§0 D13 이름; `s.prepare()` → `spike_runner: viewpoints L_ZoneTest: 10 saved, missing=[]`) · `import golmok.spike_runner as s; s.capture_all(tags=("a",), presets=("clear_noon", "night"), mode="pie")` · 기대: `spike_runner: PIE window 1280x720 x2 (LevelEditorPlaySettings)` → `spike_runner: PIE begin tag=a` → `spike_runner: > golmok.hud 0` → `> golmok.tod clear_noon` → `> golmok.path play vp_far_01` → `> golmok.screenshot a far_01` → `spike_runner: captured <Project>\Saved\Screenshots\Golmok\a\clear_noon\far_01.png (2560x1440)` → `> golmok.path stopplay` … → `spike_runner: PIE end tag=a` → `spike_runner: done capture: 20 saved, 0 missing -> …\Screenshots\Golmok` · 에디터 창을 **뒤로 보낸 채** 한 번 더(백그라운드 PIE가 그리는지 기록) · `s.contact_sheet(tags=("a",), presets=("clear_noon","night"))` → `spike_runner: contact sheet -> …\contact_sheet.html`(브라우저 20장; 캐릭터가 안 보여야 함) · 실패: `missing (timeout)` → §7 #15·#16; 크기가 2560×1440이 아니면 §7 #21(수동 New Window Size); `current` 폴더 → TimeOfDay 없음(#13).
8. **-game 성능(정본)** — PIE에서 `golmok.path record walk_01`(3 s 정지 후 60 s) → `stop` · `s.save_layer_levels()` → `spike_runner: layer level /Game/Golmok/Maps/L_Spike_b saved (tag b)` ×3(실패 시 §7 #18 수동 Save As) · `s.game_scripts(paths=("walk_01",), tags=("a","b"))` → `spike_runner: -game script -> <Project>\Saved\Golmok\spike\run_game_perf.ps1 (2 runs)` · PowerShell에서 실행 → `csv a_clear_noon_walk_01 -> …\Profile(…).csv` · 로그 `game_a_clear_noon_walk_01.log`에 `GolmokDebugSubsystem: path play 'walk_01'`·`CsvProfile Start`·`csv:` 줄 · **CSV 프레임 수 ≈ 경로 길이 × fps**(60 s·~150 fps ≈ 9000; 3000 근처면 `-csvCaptureFrames`가 섞인 것) · `golmok-perf … --markdown` 표 1행 · 실패: 로그에 `golmok.*: no debug subsystem` → §7 #17(PIE `s.perf_all()` 참고치로 대체).
9. **PIE 성능 참고치(선택)** — `s.perf_all(paths=("walk_01",), tags=("a",))` → `spike_runner: csv <path> -> golmok-perf "<path>" --label a_clear_noon_walk_01 --markdown`.
10. **basemap_import 보강(선택)** — `L_Basemap_Yeonnam`에서 `b.run(...)` 재실행 → `basemap_import: GeoOrigin lat=… lon=… h=… (basemap origin; ellipsoidal = DEM orthometric + --geoid-offset)`; GeoOrigin 값 = 베이스맵 manifest origin.
11. **결과 기록 표**(항목별 ✔/✖, 실측: route, obj/glb mapping, 텍스처 크기 표기, PIE 창 크기, 스크린샷 해상도, -game CSV 위치·프레임 수).
12. **불확실 API 표** = §7 그대로(번호 유지).

#### 6-2. `docs/runbooks/pc-spike.md` (스파이크 1.1 전체; 단계마다 산출물 위치·[미확인] 기록칸)
| 단계 | 입력 | 명령·설정 | 예상 시간 | 실패 시 대안 |
|---|---|---|---|---|
| S0 준비 | C-02 촬영, D-006·D-010 | 디스크 200 GB, `pip install -e ".[basemap,zone,mesh,splat,align,dev]"`, pc-verify-wp06 §1~§7 통과 | 30분 | — |
| S1 블러 | 원본 JPEG | `golmok-blur <in> <out>`(research/05) | 1~2 h/1000장 | EgoBlur 모델 없으면 OpenCV 폴백 |
| S2 RealityScan | 블러 이미지 | 정렬 기본, 메시 High, 텍스처 8K **UDIM(`<name>.1001.png`)**, OBJ+MTL, 좌표 로컬 또는 EPSG:5186 — `recon-postprocess.md` §2 | 3~8 h | 정렬 실패 → 재촬영 구간; 메모리 → 조각 내보내기 |
| S3 COLMAP/XMP | RealityScan | Registration(XMP) + undistorted | 20분 | — |
| S4 Postshot | S3 | D-006 설정값(스텝·해상도·SH 3) | 1~3 h | GPU 메모리 → 해상도 절반 |
| S5 후처리 | S2·S4 | `golmok-mesh reproject/chunk --size 15/collision --per-chunk/blockers`, `golmok-splat crop/clean/tiles` — `recon-postprocess.md` §3~§6 | 30분 | [미확인] 기록 |
| S6 검증 | zone 폴더 | `golmok-zone validate --check-files --strict`, `golmok-align run`(선택) | 5분 | 메시지대로 |
| S7 UE 임포트 (a) | zone 폴더 | `zi.run(zone_dir, level="/Game/Golmok/Maps/L_Basemap_Yeonnam", geo_origin=r"<basemap 폴더>")` — 기대 로그 형식 = pc-verify-wp06 §2 | 10~40분(OBJ 사본·Nanite 빌드) | bounds 오류 → `remeasure=True`, `import_result.json` mapping 기록; UDIM 미병합 → §7 #4 |
| S8 (b) Cesium | S5 splat tiles | Cesium3DTileset 액터, url `tileset.json`, 라벨 **`Spike_b_tiles`** | 20분 | 3d-tiles-validator |
| S9 (c) XGRIDS | LCC | 플러그인 임포트, 라벨 **`Spike_c_lcc`** | 30분(C-04 의존) | 플러그인 없음 → (c) 열 비움 |
| S10 시점 | 레벨 | `viewpoints.save` 10개(D13 이름·역할: `mid_04` 전선·난간, `mid_02` 청크 이음새, `mid_01` 프리셋 비교), `s.prepare()` | 20분 | — |
| S11 캡처 | S7~S10 | `s.capture_all(mode="pie")` → 120장(4태그×3프리셋×10) + 선택 `presets=(…,"night")`; `s.contact_sheet(photos_dir=<원본 사진>)` | 40분 | 창 앞 `mode="editor"` |
| S12 성능 | `golmok.path record walk_01` | `s.save_layer_levels()` → `s.game_scripts()` → `.ps1` 실행 → `golmok-perf … --markdown`(정본); `s.perf_all()`은 참고치 | 40분 | -game 문제 → PIE 값만(표에 "PIE" 표기) |
| S13 그림자 채점 | 레벨 | 유인 PIE에서 태그별로 캐릭터 그림자 확인(`near_03` 위치; 재생 캡처에는 캐릭터가 없다) | 15분 | — |
| S14 리포트 | S11~S13 | `s.report_template(perf_markdown=…)` → `research/08` 채우기 | 1 h | — |
| S15 결정 | research/08 | D-010 회의 | — | — |

### 7. 불확실 API 표 (런북 §12 그대로; 번호 유지. `test_no_unreal_api_outside_touchpoint_list`가 이 표의 `unreal.<Name>` 표기를 화이트리스트로 읽는다)
| # | 파일 | API | 불확실한 점 | 대안 |
|---|---|---|---|---|
| 1 | zone_import | `unreal.AssetImportTask` + `factory=unreal.FbxFactory()` + `unreal.FbxImportUI`(`is_obj_import=True`, `import_materials/import_textures=False`, `mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH`, `static_mesh_import_data.build_nanite/combine_meshes`)가 OBJ에 적용되는지 | 5.8에서 OBJ가 레거시 FBX인지 Interchange인지(citations: Interchange 문서에 OBJ 없음, `FbxImportUI.is_obj_import`는 있음); `factory` 지정이 Interchange 라우팅을 우회하는지 | 사다리(D4): 프로브가 비면 `interchange` → 콘솔 `Interchange.FeatureFlags.Import.OBJ 0` 뒤 `legacy_flag`; 옵션이 무시돼도 부산물 삭제·슬롯 재할당으로 결과 동일 |
| 2 | zone_import | OBJ 임포터 축·단위(Z-up 유지? cm 변환?) | 측정으로 상쇄(프로브) | fit error > 1 cm → `ZoneImportError probe`; 청크 bounds 오류면 `remeasure=True`; 실측 (s, M)·route를 결과 표에 |
| 3 | zone_import | `unreal.InterchangeGenericAssetsPipeline` 하위 `material_pipeline.texture_pipeline.import_udi_ms`, `material_pipeline.import_materials`, `mesh_pipeline.import_static_meshes/build_nanite`, `common_meshes_properties.force_all_mesh_as_type=unreal.InterchangeForceMeshType.IFMT_STATIC_MESH` | 속성 이름은 citations 확인, `AssetImportTask.options`로 전달되는지는 미확인 | hop마다 hasattr; 옵션 None(프로젝트 기본 UDIM 감지) → 병합 판정 → #4 폴백 |
| 4 | zone_import | UDIM 자동 병합·`blueprint_get_size_x()`가 캔버스(512)인지 타일(256)인지; 결과 이름이 `T_<base>`(`destination_name`) | Python에 UDIM 크기 API 없음; UDIM 접미사 제거 규칙 | 크기로 판정하되 런북에 실제 표기 기록; `unreal.UDIMTextureFunctionLibrary.make_udim_virtual_texture_from_texture2_ds(name, textures, [unreal.IntPoint…])` 폴백; 이름 다르면 `EditorAssetLibrary.rename_asset`; 최후 첫 타일 + WARNING |
| 5 | zone_import | `Texture2D.set_editor_property("virtual_texture_streaming", True)`·`("srgb", True)` 뒤 재빌드 필요 여부 | 저장으로 충분한지 | `save_loaded_asset` 후 `MaterialEditingLibrary.recompile_material(M_ZoneScan)`; 못 켜면 `M_ZoneScan_NoVT` |
| 6 | zone_import | `EditorAssetLibrary.list_assets(folder, recursive=True)` 반환 형식(`/Game/A/B.B` vs `/Game/A/B`), `imported_object_paths` 형식 | 문자열 형식 | `.split(".")[0]` 정규화(둘 다 처리) |
| 7 | zone_import | `StaticMesh.get_editor_property("static_materials")[i].get_editor_property("material_slot_name")`, `set_material(i, mi)`; 머티리얼 임포트 off일 때 슬롯 이름이 `usemtl`인지 | 슬롯 이름 규약(2차) | 정확 → 대소문자 → usemtl 순서 폴백 + warn; `get_material_index(name)` 병행 |
| 8 | zone_import | `EditorAssetLibrary.rename_asset(old, new)`, `delete_directory`, `duplicate_asset` | 안정(WP-04 동일) | 실패는 warn; rename 실패 시 `duplicate_asset`+`delete_asset` |
| 9 | zone_import | `bm._set_nanite`(`unreal.StaticMeshEditorSubsystem.set_nanite_settings`), `bm._complex_collision`(`unreal.CollisionTraceFlag`) | V-02 확인 | 기존 hasattr 분기 |
| 10 | materials | `unreal.MaterialExpressionTextureSampleParameter2D.sampler_type = unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR`; **VT 샘플러의 기본 텍스처는 VT여야 한다**(비VT `DefaultTexture`면 컴파일 오류) | enum 이름은 citations 확인; 기본 텍스처 제약은 엔진 규칙 | 첫 임포트 VT 텍스처를 `default_texture`로; enum 없으면 미설정 + warn(수동 설정) |
| 11 | interior_setup | `AGolmokZone.unload_in_editor()` 뒤 `get_actor_transform()` 유효 | WP-05 동일 | rebuild 직후 transform 취득(현재 순서) |
| 12 | interior_setup | `LevelEditorSubsystem.new_level(path)`가 현재 레벨을 닫으며 저장 프롬프트 | `save_current_level()` 선행 | sz와 동일 |
| 13 | spike_runner | PIE 세계에서 `golmok.tod`가 `AGolmokTimeOfDay`를 찾는지(조명 액터 태그 `GolmokLighting`) | 스크린샷 폴더 `<preset>` | `current` 폴더면 missing 처리·런북 안내 |
| 14 | spike_runner | `unreal.GameplayStatics.get_all_actors_of_class(pie_world, unreal.Actor)`(라벨 스캔)·`(pie_world, unreal.GolmokZone)`·`get_player_controller(world, 0)`·`set_visual_visible` Python 호출 | PIE 액터 접근 | `golmok.zone.unload <id>` 콘솔 폴백(충돌도 사라짐; 재생은 충돌 무관) |
| 15 | spike_runner | `unreal.SystemLibrary.execute_console_command(get_game_world(), cmd)`가 PIE 콘솔에 닿는지 | citations에 시그니처만 | `unreal.UnrealEditorSubsystem.get_game_world()` None이면 `unreal.EditorLevelLibrary.get_pie_worlds(False)`(deprecated) + warn; 최후 `viewpoints.capture` 에디터 모드 |
| 16 | spike_runner | `LevelEditorSubsystem.editor_request_begin_play()/editor_request_end_play()/is_in_play_in_editor()` 뒤 PIE가 뜨는 틱 수·기본 플레이 모드 | 비동기; 모드는 `LevelEditorPlaySettings` 마지막 값 | 60 s 폴링; 시작 안 되면 `_finish`+런북(Alt+P 대신 수동 New Editor Window 실행 뒤 `mode="editor"`) |
| 17 | spike_runner | `-game -ExecCmds` 실행 시점(맵 로드 전이면 `golmok.*` 월드 명령 무효), `-ExitAfterCsvProfiling`이 콘솔 `CsvProfile Stop`에도 종료하는지 | 엔진 동작 | `.ps1` 타임아웃 kill + 로그 `GolmokDebugSubsystem: csv:` 검사; 실패면 PIE `perf_all()` 참고치 |
| 18 | spike_runner | `EditorAssetLibrary.duplicate_asset(level, "/Game/Golmok/Maps/L_Spike_<tag>")`로 맵 복제 (2026-09-28 Save As로 대체 — 결과 절) | 월드 파티션·외부 액터 | 실패 시 수동 "Save Current Level As" 안내 |
| 19 | spike_runner | `set_is_temporarily_hidden_in_editor` / `set_actor_hidden_in_game` on Cesium3DTileset·XGRIDS 액터 | 플러그인 액터 가시성 구현 | `set_editor_property("hidden", True)`; Cesium은 `set_editor_property("enabled", False)`(있으면) |
| 20 | basemap_import | `unreal.GolmokGeoOrigin` 프로퍼티 `latitude/longitude/height_ellipsoidal` | WP-04 sz와 동일 | sz 재사용 |
| 21 | spike_runner | `unreal.get_default_object(unreal.LevelEditorPlaySettings)`의 `new_window_width/new_window_height`, `last_executed_play_mode_type=unreal.PlayModeType.PLAY_MODE_TYPE_PLAY_IN_EDITOR_FLOATING` | 클래스·속성·enum 노출(추정) | Editor Preferences > Level Editor > Play > New Window Size 1280×720, Play 모드 "New Editor Window (PIE)" 수동; `sr.captured`의 실제 크기로 확인 |
| 22 | zone_import | `AssetImportTask.save=False` 후 `save_loaded_asset`; `async_` 속성 | 안정 | `save=True`로 전환; `async_`는 hasattr |
| 23 | zone_import | OBJ 사본 임포트 시 `mtllib`·절대경로 `map_Kd` 무시(import_textures=False) | 경고 로그 | 무해; 경고 수 기록. 임포터가 그래도 텍스처/머티리얼을 만들면 부산물 삭제(`zi.cleanup`) |
| 24 | spike_runner | `golmok.path play <name>`이 2샘플 600 s 경로를 받아들이는지(version 1·t 단조) | C++ 파서 | `dwell_path_json`이 FormatPathJson 레이아웃 그대로; 거부되면 `golmok.path play: ERROR …` → 3샘플로 |
| 25 | viewpoints | `capture(..., on_done=)` 추가 | 기존 호출 호환 | 기본 None |
| 26 | zone_import | `unreal.SystemLibrary.get_engine_version()` | 존재(확인에 가까움) | 없으면 캐시 항상 miss(재측정) |
| 27 | zone_import | `unreal.Paths.project_saved_dir/project_content_dir/project_config_dir`, spike: `unreal.Paths.engine_dir()`·`get_project_file_path()` | 앞 3개 확인(WP-04), 뒤 2개 2차 | `os.environ["UE_ROOT"]`(`tools/ue/common.ps1` 규약) + `<ContentDir>/../Golmok.uproject` |
| 28 | zone_import | `StaticMesh.get_bounding_box()`가 Nanite 청크에서 원본 정점 bbox를 주는지 | `ExtendedBounds` 원천 | 허용 오차 `max(5 cm, 0.5 %)`; 반복 초과면 2 %로 올리고 기록 |
| 29 | zone_import | GLB 임포트(`bm._import_glb` 경로, 옵션 없음)의 에셋 이름이 glTF mesh/node 이름을 따르는지(`destination_name`과 함께 둘 다 목표 이름으로) | V-02·WP-04는 mesh 이름으로 확인 | 다르면 `rename_asset` |
| 30 | spike_runner | C++ `golmok.screenshot` 폴백 파일명 `<name>00000.png`(뷰포트 크기 없을 때) | HighResShot 경로 | `screenshot_fallback_path`를 받아 `<name>.png`로 개명 |

### 8. 위험·트레이드오프
1. **OBJ 사본 디스크·시간**: 2천만 tri OBJ ≈ 1.5 GB 텍스트 → 사본 쓰기 1~2분·디스크 2배. 옵션(회전·스케일)으로 축을 지정하는 대안은 검증 불가라 택하지 않았다. 런북에 디스크 조건. 사본은 `<Saved>/Golmok/zone_import/`에 남아 재실행 시 덮어쓴다(청소는 사용자).
2. **리임포트 원본이 사본**: 에셋의 Source File이 `Saved/…` 사본 → "Reimport"는 사본을 읽는다. `zone_import.run` 재실행이 정본 워크플로(로그·런북에 명시).
3. **가짜 임포터는 진짜가 아니다**: 순서·오류 경로·계산은 증명되지만 실제 축·UDIM 병합·슬롯 이름은 PC에서만 확인 → bounds·크기·슬롯을 **런타임에 검증**하고 실패를 명확한 메시지로 낸다(그 검증 코드 자체를 가짜로 테스트).
4. **임포터 사다리 3단**: 단순성 비용. 프로브 1회로 확정·캐시하므로 청크 임포트에는 분기가 없다.
5. **VT 샘플러 기본 텍스처**: ~~`M_ZoneScan`의 기본 텍스처가 첫 zone의 VT에 묶인다 … 공용 VT 더미 에셋은 만들지 않는다.~~ → 수정(리뷰 F4·L2-01·L2-04): zone 재임포트의 강제 삭제가 마스터 기본을 None으로 만들어(VT 샘플러 컴파일 오류 → 모든 MI가 기본 머티리얼) 마스터 전용 `T_ZoneScanDefault`(VT)·`T_ZoneScanDefault_NoVT`를 만든다. 기존 마스터는 `get_material_property_input_node(MP_BASE_COLOR)`로 제자리 수리(런북 #10).
6. **PIE 캡처의 한계**: 창이 뒤에 있으면 8 fps 수준(dwell 600 s로 흡수); 스크린샷 해상도는 PIE 창 크기 × 2에 의존(§7 #21). 품질 비교엔 영향 없고 fps 절대값은 `-game`이 정본.
7. **`-game` 무인 스크린샷은 없다**(`golmok.later` 미채택). 필요해지면 WP-06b에서 C++ 40줄 + 자동화 테스트.
8. **`-game` Saved 위치 불확실**: 후보 두 곳을 뒤지고 경로 JSON을 두 곳에 복사한다(V-01 관측 근거). 스크린샷은 -game에서 쓰지 않으므로 무관.
9. **MI 이름 = MTL 머티리얼 이름**: RealityScan이 `material_0`처럼 붙이면 여러 zone에서 이름이 겹치지만 폴더가 zone별이라 충돌 없음. 청크별 텍스처가 필요해지면 `MI_<chunk>_<material>`로 확장(계획 dict에 이름이 있어 에디터 코드 변경 없음).
10. **테스트 수 ≈ 90개**, 실행 < 25 s 목표. 런북 드리프트 테스트의 취약성: 기대 로그는 항상 코드블록 안(규칙).
11. **합성 zone 생성기가 mesh extras(scipy 등)를 요구**: CI는 전부 설치(ci.yml), 로컬은 `importorskip`. 단순 파이썬만으로 도는 `--no-collision` 모드는 두지 않는다(validate --check-files가 실패하는 산출물은 의미가 없다).
12. **포털 불일치를 오류로**: 정합(WP-07) 뒤 manifest가 바뀌면 다시 돌리면 된다. 경고로 두면 PIE 왕복 실패의 원인을 늦게 안다.

**WP-06 "결과 — 판단한 것(스펙과 다른 점)"에 적을 항목**
- `blockers.glb`는 임포트하지 않는다(C++는 `blockers.json`만 읽음). `manifest.json`·`blockers.json`만 Content로 복사.
- 머티리얼 인스턴스는 청크당이 아니라 **MTL 머티리얼 이름당**(`MI_<material>`); 슬롯 이름으로 할당.
- `collision.chunks`가 있으면 단일 `collision.glb`는 임포트하지 않는다(C++가 읽지 않음).
- 실내 서브레벨에 **PostProcessVolume을 두지 않는다**: WP-05가 실내 룩을 `AGolmokTimeOfDay::EnterInterior/ExitInterior`의 부분 프리셋 오버레이(`lighting_presets.json`의 `interior`: 안개 0·노출 바이어스)로 구현했고 포털의 문 평면 통과가 그것을 켜고 끈다. 서브레벨에 또 하나의 PPV(unbound 또는 방 크기 bound)를 두면 (i) 퍼시스턴트 unbound PPV와 우선순위·블렌드가 겹쳐 C++가 복원하는 "레벨 값"이 오염되고 (ii) `lighting.apply("interior")`가 잡는 "첫 unbound PPV"가 레벨 로드 순서에 따라 달라진다. 실내 전용 색보정이 필요해지면 `lighting_presets.json`의 `interior`에 키를 더한다(JSON만).
- Python은 `AGolmokPortal`을 배치하지 않는다(C++가 manifest `portals[]`에서 스폰); `interior_setup`은 왕복 검사만.
- 스크린샷 태그는 `spike_` 접두 없이 `a b c ac` 그대로; 시점 이름은 `far_01..03 mid_01..04 near_01..03`(research/08 조건 3/4/3); 기본 프리셋은 night 제외 3개.
- `-game`은 CSV 전용(스크린샷은 PIE); C++ `golmok.later`는 추가하지 않았다.
- UDIM 파일명은 공식 규약 `BaseName.####.ext`만 인정(`_####`는 경고 후 단일 텍스처).
- 합성 실내 zone의 원점은 방 중앙이 아니라 **방 남서 바닥 모서리**(청크 1개로 떨어지게); WP-05 픽스처(중앙 원점)와 다르다.

### 9. 심판 지적 반영표
| # | 심판·대상 | 지적 | 닫은 방법 |
|---|---|---|---|
| J1 | 1·C major | `--interior` 문이 속이 찬 박스 A 남면에 있고 방이 A와 겹침 → 포털 왕복 불가 | §3-7: 파사드 A를 0.2 m 벽으로 바꾸고 문 구멍(x 4..6, z 0..2.2, `door_openings` 규칙) 절단; 방은 y ≥ 7.2에 두어 겹침 0; `test_door_hole_and_room_do_not_overlap`(구멍 안 면 중심 없음·bbox 비교차) |
| J2 | 1·C major | `-csvCaptureFrames=3000`과 `golmok.path play --csv`가 충돌 | §4-8: `-csvCaptureFrames` 제거, `-ExecCmds="golmok.hud 0, golmok.tod <p>, golmok.path play <walk> --csv"`; 런북 §8에 "CSV 프레임 ≈ 경로 길이 × fps" 검사 |
| J3 | 1·C major | -game Saved 위치(`%LOCALAPPDATA%…`) 미처리 | `_pure.saved_dir_candidates/csv_dirs/path_dirs`; `.ps1`이 경로 JSON을 두 후보 `Golmok/Paths`에 복사하고 CSV를 두 후보에서 찾음(§4-8) |
| J4 | 1·C major | PIE 스크린샷 크기가 창 크기에 의존 | `configure_pie_window()`(`LevelEditorPlaySettings` 1280×720, 새 창 모드, hasattr) + 수동 폴백 §7 #21; `sr.captured`에 실제 PNG 크기 |
| J5 | 1·C minor | `texture_pipeline` hop 위치 | `_texture_options`: `material_pipeline.texture_pipeline.import_udi_ms`, `material_pipeline.import_materials=False`, hop마다 hasattr(§3-2, 테스트 `test_texture_options_hops`) |
| J6 | 1·C minor | dwell 30 s < WAIT 300틱(8 fps) → 경로가 먼저 끝남 | `DWELL_S=600`, 대기는 초 단위(`_now`), `golmok.path stopplay`를 항상 전송(§3-4) |
| J7 | 1·C minor | 시점 2/3/2가 research/08의 3/4/3과 다름, night 기본 포함 | D13: `far_01..03 mid_01..04 near_01..03`, `DEFAULT_PRESETS` = cycle − night; `test_viewpoints_presets_match_research_08` |
| J8 | 1·C minor | 단색 타일이라 V 뒤집힘이 안 보임 | 5×7 비트맵 숫자 + 좌상단 흰 사각형 개수(§3-7); 런북 §2 체크 |
| J9 | 1·C minor | 청크별 충돌 모드 미검증 | D7 `collision_mode="chunks"`, 생성기 `collision --per-chunk`, `test_single_collision_mode`·`test_run_call_order`(단일 파일 미임포트) |
| J10 | 1·C minor | `udim_tile_of` 1100 상한 | 1001..1999, `udim_block_coords` 공식(1010→(9,0), 1020→(9,1)); 1000·2000 ValueError |
| J11 | 1·B major | PIE를 사용자가 Alt+P로 | C의 `_PieCapture`(`editor_request_begin_play`) 채택 |
| J12 | 1·B major | 폰 텔레포트(320 cm 붐, 캐릭터 노출) | dwell 경로 재생(`AGolmokPathPawn`, `bHidePlayerDuringPlayback`) |
| J13 | 1·B major | VT 샘플러 + 비VT 기본 텍스처 | D6: 첫 VT 텍스처 뒤에 마스터 생성, `M_ZoneScan_NoVT` 폴백, §7 #10 |
| J14 | 1·B major | UDIM 미병합이 RuntimeError | D5 폴백 사슬(`_tiles` → `make_udim…` → 1001 + WARNING); 테스트 2개 |
| J15 | 1·B major | PIE CSV가 정본 | D12: `-game` 정본 + `L_Spike_<tag>` 맵, PIE는 참고치 |
| J16 | 1·B minor | GLB 보정을 ENU로 직접 적용 | `pretransform_glb`가 `G·A·G⁻¹` 켤레(`gltf_conjugate`), `test_gltf_conjugate` |
| J17 | 1·B minor | `get_pie_worlds` 우선 | `get_game_world()` 우선, deprecated는 폴백 + warn(§7 #15) |
| J18 | 1·A major | `editor_play_simulate`(SIE) + Alt+P | J11과 동일 |
| J19 | 1·A major | CameraActor 지연 스폰(BlueprintInternalUseOnly) | 채택 안 함; dwell 경로만 |
| J20 | 1·A major | `-windowed` 없이 `-RenderOffscreen` 부재 | §4-8 명령줄(`-RenderOffscreen -ForceRes`) |
| J21 | 1·A major | 합성 실내 없음(WP-05 픽스처 폴백 불가) | `--interior` 생성(§3-7), `test_interior_portal_round_trip`, `test_round_trip_plan` |
| J22 | 1·A minor | `import_udims` 이름 | `import_udi_ms`(§3-2) |
| J23 | 1·A minor | `CsvProfile Stop` 로그 대기 | `.ps1`: `-ExitAfterCsvProfiling` + 타임아웃 + `GolmokDebugSubsystem: csv:` 줄 검사 |
| J24 | 1·A minor | 옵션 회전·음수 스케일 경로 | 채택 안 함(D3 항상 재작성); 회전 행렬 수학 없음 |
| J25 | 1·A minor | "Windows CI는 mesh 미설치" 오류 전제, `_####` 허용 | 전제 삭제(ci.yml 확인); `_####`는 경고만(D5) |
| J26 | 1·A minor | 사용자 레벨의 hidden 플래그 저장·복원 | `save_layer_levels()`의 `L_Spike_<tag>` 복제 맵 |
| K1 | 2·C blocker | J1과 동일(문 평면을 넘을 수 없음) | J1 |
| K2 | 2·C major | `pretransform_obj_lines`가 `v`만(법선·감김 미처리) | `vn`에 `U`, det<0이면 `f` 반전; GLB는 NORMAL·인덱스; `test_pretransform_obj_normals_and_winding`, `test_pretransform_glb_positions_normals_indices` |
| K3 | 2·C major | PIE 창 크기 미고정, `<name>00000.png` 미수용 | J4 + `screenshot_fallback_path`·개명(§3-4), `test_pie_capture_accepts_fallback_filename` |
| K4 | 2·C minor | `-csvCaptureFrames` + `--csv` 없음 | J2 |
| K5 | 2·C minor | 단일 collision.glb만, 텍스처가 버전 폴더 안 | J9 + 텍스처를 `<out>/recon/<id>/tex`에(4단계 `../` 상대경로), `test_geometry_numbers` |
| K6 | 2·C minor | 원본 MTL 위치 모호 | §3-7 명시(`recon/<id>/scan.mtl` + `tex/`), `chunk_manifest.missing` 빈 것 테스트 |
| K7 | 2·C minor | `asset_paths()` 없음, `spike_<tag>` 접두 | `_pure.asset_paths()` 추가; 태그 그대로(D14) |
| K8 | 2·C minor | blocker가 벽면과 겹쳐 구분 불가; `png_size` 시그니처 누락; 가짜 가정 표시 | 창 구멍 위 유리(파사드 B); `png_size` §3-1; 가짜 임포터의 가정(UDIM 크기·슬롯 이름)은 §7 #4·#7 번호로 표시 |
| K9 | 2·B major | Alt+P + 폰 이동 | J11·J12 |
| K10 | 2·B major | VT 기본 텍스처 | J13 |
| K11 | 2·B major | `transform_obj_lines`가 `v`만 | K2 |
| K12 | 2·B major | 런북 기대 수치 없음 | `expected.json`(§4-4) + 런북 §2·§4 인용, `test_expected_json_matches_files`·`test_level_coordinates_match_spec_table_c` |
| K13 | 2·B minor | manifest를 에셋 전에 복사, -game 자동화 없음, MTL 깊이 오류, `rect_footprint` 시그니처, 헬퍼 이동 | 복사는 에셋 뒤(D8); `game_scripts()`; `../../../../recon`(4단계); 생성기 자체 `rect_footprint(lat, lon, w, h, dx, dy)`; 헬퍼는 sz에 남김(D2) |
| K14 | 2·A major | 합성 실내 없음 | J21 |
| K15 | 2·A major | `editor_play_simulate`, `import_udims` | J18·J22 |
| K16 | 2·A major | 손으로 쓴 청크·chunk_manifest(격자 의미 불일치) | 실제 `golmok-mesh chunk/collision/blockers` 인프로세스(§3-7) |
| K17 | 2·A major | UDIM 크기 기대값 모순 | `udim_canvas_blocks` + `expected.json.textures[].canvas_px`(512×512) 한 곳 |
| K18 | 2·A minor | 의존성 문구 오류, 동기 -game 실행으로 에디터 정지, `?` 테스트 상수 | `.[zone,mesh]` 명시; `.ps1` 외부 실행; 회전 행렬 테스트 없음(D3) |
| G1 | 그래프트 A | PIE 창 크기 | J4 |
| G2 | 그래프트 A | Saved 후보 두 곳 | J3 |
| G3 | 그래프트 A | `FbxFactory` 강제 + Interchange + 플래그 사다리, route 기록 | D4, `test_route_ladder` |
| G4 | 그래프트 A | `importer_mapping.json` 캐시 + `remeasure` | §3-2 1단계, §4-2, `test_importer_cache_hit_and_remeasure` |
| G5 | 그래프트 A | 터치포인트 화이트리스트 테스트 | `test_no_unreal_api_outside_touchpoint_list`(§7 표의 `unreal.<Name>`) |
| G6 | 그래프트 A | VT 기본 텍스처를 표에 | §7 #10 |
| G7 | 그래프트 A | 단일 비UDIM 텍스처 포함 | `ground.png`(UDIM 아님) + `room.1001.png`(명시 한 장) + `facade.<UDIM>` 세 경로 모두 |
| G8 | 그래프트 B | MTL 폴더 기준 map_Kd, 버전 폴더 밖 텍스처, 실제 파이프라인 | `resolve_map_path`, §3-7 |
| G9 | 그래프트 B | `collision_mode` chunks | D7 |
| G10 | 그래프트 B | 슬롯 3단 폴백 | D6, `slot_assignment` |
| G11 | 그래프트 B | format≠nanite_mesh·비OBJ uri 오류 | §4-5 |
| G12 | 그래프트 B | 정확히 두 파일 복사 | D8, `test_content_copy_exact_two_files` |
| G13 | 그래프트 B | 타일 번호 비트맵 | §3-7 |
| G14 | 그래프트 B | `GolmokInteriorSetup` 태그 재실행 규칙 + idempotency 런북 | D10, `test_rerun_deletes_only_tagged_actors`, 런북 §6 |
| G15 | 그래프트 B | §6-3 PPV 판단 기록 | §8 "판단한 것" |
| G16 | 그래프트 B | `resolve_zone_dir`가 manifest.json 경로·불일치 오류 | §3-1·§4-5 |
| G17 | 그래프트 B | parity 테스트(`split_map_line`, `_MAP_OPTS`, `TARGET`, `measure_mapping`) | §5-1 |
| G18 | 그래프트 B | 복사는 에셋 뒤, 부모 manifest는 Content 사본 | D8, §3-3 2단계 |

심판이 갈린 곳과 결정: ① UDIM `_####` — 심판 1(A 결함)은 "`.####`만, `_####`는 경고", 심판 2(그래프트)는 "`_####` 허용" → **`.####`만 인정, `_####`는 경고**(공식 문서 인용이 `.####`뿐이고 UE 정규식 기본값은 미확인). ② `-game` 종료 감지 — 심판 2는 `CsvProfile Stop` 로그 마커(A), 심판 1은 A의 그 마커가 실제로 찍히지 않는다고 지적 → **`-ExitAfterCsvProfiling` + 타임아웃 + `GolmokDebugSubsystem: csv:` 줄**. ③ 포털 불일치 — B는 경고, C는 오류 → **오류**(§8 12). ④ 스크린샷 폴더 접두 — "그대로 또는 문서화" → **접두 없음**.

## 결과
세션: session_011qpTa7U7onDnW7L9jNSgwA (Fable 5.1 ultracode; 심판·회의론자·수정 에이전트는 모델 정책대로 Opus 5.5) · 2026-09-24~25 · 상태 **🟡 코드 완료·PC 검증 대기** (G2 `runbooks/pc-verify-wp06.md`, V-04; 스파이크는 `runbooks/pc-spike.md`, V-05) → **🟢 V-04 통과**(2026-09-28, 아래 "병합 기록 — T5 PR #41"). PR #12.

**진행 방식(ultracode)** — ① 설계 패널: API 현실성 / 데이터·경로 규약 / 검증 가능성 3안(Fable) → Opus 심판 2명 채점(검증 가능성안 41/50 승) → 종합해 위 "설계 (확정)"(심판 지적 44건 반영표 §9). 설계 전에 5.8 Python API 레퍼런스 40여 클래스와 UDIM 공식 문서를 이 컨테이너에서 직접 확인해 `citations`로 고정했다. ② 구현: A단계 `_pure.py`+생성기(병렬) → B단계 가짜 `unreal`·런북 → `zone_import`‖`spike_runner` → `interior_setup` → 통합. 중간에 main의 V-03 결과(PR #13, PC 수정 4건)를 병합해 반영. ③ 적대적 검증 1라운드: 리뷰어 4관점(API 정확성 / UDIM·VT 규약 / 스펙·경로·C++ 계약 / 런북·PC 발견 준수, Fable) → 소견마다 Opus 회의론자 2명(엔진 사실·코드 맥락) 반박 → 둘 다 반박한 것만 기각 → 파일 그룹별 Opus 수정(테스트 먼저) → Opus 게이트. 2라운드는 리뷰어 3명이 소견 6건을 낸 시점에서 오케스트레이터 지시(비용)로 중단했고, 그 6건은 미검증 상태로 아래 표에 남긴다(병합 전 Opus 보완 리뷰에서 이어짐).

**한 것** (`unreal/Golmok/Content/Python/golmok/` 기준)
- `_pure.py`(1.8k줄, `unreal`·numpy 비의존): 에셋 경로 규약(`asset_paths`)·UDIM 파싱/블록 좌표/그룹·MTL 파싱·OBJ 스트리밍(mtllib/usemtl/bounds/프로브)·임포트 계획 `import_plan`(§4-1 dict, 문제/경고 문자열 §4-5)·bbox/허용오차·임포터 매핑 측정(basemap_import와 동일성 테스트)·OBJ/GLB 사전변환(법선·감김 반전, `G·A·G⁻¹`)·로그 형식 `LOG`(단일 소스)·결과 JSON·포털 왕복 검사·실내 서브레벨 스펙·스파이크(시점/태그/dwell 경로 JSON/`-game` 명령줄/PowerShell/컨택트 시트 HTML/리포트 템플릿).
- `zone_import.py`: `run(zone_dir, version=None, level=None, geo_origin=None, save=True, remeasure=False, reimport_textures=True)` — 계획(에디터 호출 0회) → 프로브로 OBJ 임포터 사다리(`fbx`→`interchange`→`legacy_flag`)·매핑 측정·캐시 → 텍스처(UDIM VT, 병합 판정, `make_udim_virtual_texture_from_texture2_ds` 폴백) → `M_ZoneScan`/`M_ZoneScan_NoVT`(마스터 소유 기본 텍스처 `T_ZoneScanDefault*`) → `MI_<material>` → 청크(사전변환 사본, Nanite, bounds 검증, 슬롯 3단 할당) → 충돌(`collision.chunks` 우선, complex-as-simple) → `manifest.json`·`blockers.json` 복사 → GeoOrigin → `AGolmokZone` 리빌드 → `import_result.json`. 모든 임포트는 V-03 발견대로 `<folder>/_import` 스크래치 → 규약 경로로 이동.
- `interior_setup.py`: 포털 왕복 검사(같은 점 ≤ 5 cm·반대 yaw ≤ 1°, 실패 시 에디터 호출 0회) → 부모 Content manifest(레벨의 부모 액터 버전) → `zone_import.import_assets` 재사용 → 실내 zone 리빌드/언로드 → 서브레벨 `L_<zone_id>`(태그 `GolmokInteriorSetup` PointLight 1개, 레벨 좌표, 재실행은 태그 액터만 교체) → 부모 리빌드 → 저장 → (선택) 경로 B 등록(`save_map`).
- `spike_runner.py`: `prepare`(시점 10개 이름 고정) · `capture_all(mode="pie"|"editor", quit_editor=False)`(PIE 상태기계: `golmok.hud 0` → 프리셋 → 시점별 600 s dwell 경로 재생 → `HighResShot 2560x1440` → 파일 대기 → `stopplay`; 헤드리스는 `quit_editor()`) · `perf_all`(PIE 참고치) · `save_layer_levels`(`L_Spike_<tag>`) · `game_scripts`(`-game -RenderOffscreen … golmok.path play <walk> --csv` `.ps1`, Saved 후보 2곳, `label_suffix`) · `contact_sheet` · `report_template`.
- 보강: `materials.build_zone_scan_material/zone_scan_instance`, `basemap_import._set_geo_origin`(베이스맵 origin → `AGolmokGeoOrigin`), `synthetic_zone`(`_spawn_interior_sublevel(specs, delete_tag, on_removed)`, 태그 스펙, `register_interior_sublevel(zone_id, version)` 재실행 안전), `viewpoints.capture(on_done=)`·출력 폴더 normpath.
- `tools/scripts/make_synthetic_zone.py`: RealityScan 흉내 원본(OBJ+MTL, UDIM PNG 1001/1002/1011 + 단일 PNG + 명시 타일 1장, 순수 파이썬 PNG·5×7 비트맵 숫자) → 실제 `golmok-mesh chunk/collision --per-chunk/blockers` → `zones/z_synthetic_scan_001/v1/`(+`--interior` 방 zone, door_1↔door_out 왕복) + `expected.json`(런북·테스트 정본: 청크 `c_w001_n000`/`c_e000_n000` 66/66 tri, 레벨 좌표 = 스펙 표 C). 결정적 출력·`--check`.
- 테스트(`tools/tests/`): `fake_unreal.py`(스크립트형 가짜 `unreal`: 실제 파일을 읽는 가짜 임포터·인메모리 레지스트리·호출 기록·가짜 시계·엄격한 옵션 속성) + `test_ue_python_pure.py` 60 · `test_make_synthetic_zone.py` 19 · `test_fake_unreal.py` 14 · `test_ue_python_zone_import.py` 35 · `test_ue_python_interior_setup.py` 13 · `test_ue_python_spike_runner.py` 30 = **+171개**(전체 **494 passed, 3 skipped**). 런북 드리프트 테스트(런북에 인용된 로그 ↔ `_pure.LOG` 양방향, 가짜가 만든 로그 블록 ↔ 런북 §2/§4/§8/§9 줄 단위)와 터치포인트 화이트리스트 테스트(`unreal.<Name>`이 런북 §12 표 또는 기존 모듈에 있어야 함)가 문서와 코드를 묶는다.
- 문서: `runbooks/pc-verify-wp06.md`(체크리스트 §1~§11, 불확실 API 표 §12 38행), `runbooks/pc-spike.md`(S0~S15, 예상 시간·실패 시 대안), README 2곳, ROADMAP 1.1·1.4·1.5, `.gitignore`(합성 zone 에셋·`L_Spike_*`).

**테스트 로그(클라우드)**: `ruff check .` All checks passed · `ruff format --check .` 86 files already formatted · `python -m pytest -q` **494 passed, 3 skipped**(skip = torch/rawpy/타일 검증기 환경) · `check_repo.py` OK. CI: Windows 잡에서 경로 구분자·`rglob` 순서 실패 4건을 오케스트레이터 메모로 받아 즉시 수정(테스트는 `os.path.normpath`·`sorted` 규칙, `viewpoints.capture`는 모듈에서 normpath). 최종 커밋 결과는 PR #12 체크 참조.

**적대적 검증 표**
| 라운드 | 원시 소견 | 확정(수정) | 반박(기각) | 비고 |
|---|---|---|---|---|
| 1 | 33 (major 18 · minor 15) | 28 | 5 | 확정 전부 수정, 테스트 먼저 작성(+26). 반박 5: Nanite 폴백 100 % 강제(basemap과 같은 설정이 의도), UDIM 크기 판정의 0×0 경합(에디터 동기 임포트), UDIM 팩 경로 런북 검사 누락(§2 체크가 이미 공통), Full Precision UV 미설정(단순 정밀도로 충분·설계 범위 밖), HUD 포함 §12 행 누락(월드 서브시스템이라 다음 PIE에 잔류 없음) |
| 2 | 6 (udim 3안 중 3명 완료 시점 중단) | — | — | **미검증·미반영**: ① UDIM 병합 판정이 컴파일 전 크기를 읽을 가능성 ② Full Precision UV(1라운드 기각과 같은 논점) ③ TIF/JPG 앵커의 크기 판정(PNG만 IHDR) ④ `MI_<safe(material)>` 이름 충돌 미검출 ⑤ 비인덱스 TRIANGLES의 감김 반전 ⑥ 설계 본문 §3-1/§3-2의 UDIM 문구가 코드와 다름(아래 "설계 대비 변경") |

**설계 대비 변경(구현·리뷰에서 확정; 설계 본문은 원안 그대로, 이 표가 우선)**
| 항목 | 설계 | 구현 | 이유 |
|---|---|---|---|
| PIE 캡처 창(D11, §3-4 WINDOW) | `LevelEditorPlaySettings` 1280×720 새 창, 스크린샷 = 창×2 | `editor_request_begin_play()`는 항상 레벨 뷰포트에서 재생 → WINDOW 상태 제거, 스크린샷은 `HighResShot 2560x1440 filename=…`으로 해상도 고정; `configure_pie_window`는 유인 새 창 PIE 보조 | 리뷰 F1 |
| `PlayModeType` 멤버 | `PLAY_MODE_TYPE_PLAY_IN_EDITOR_FLOATING` | `PLAY_MODE_IN_EDITOR_FLOATING`(getattr 가드) | 리뷰 F6 |
| 마스터 기본 텍스처(D6) | 그 실행의 첫 VT 텍스처 | 마스터 소유 `T_ZoneScanDefault`(VT)·`_NoVT`(생성 256 px 회색) | zone 삭제·재임포트 시 댕글링(F4·L2-01·L2-04) |
| 임포트 배치 | `destination_name`으로 규약 경로 직접 | `<folder>/_import` 스크래치 → `_move_asset` → 스크래치 삭제(`zi.moved` 로그) | V-03 Interchange 배치(`<dest>/<소스명>/StaticMeshes/…`) |
| UDIM 의심 이름 | `_####` 경고 | 엔진 규칙 `[._]####`(≥1001)로 경고 범위 확대, 단일 텍스처는 `import_udi_ms=False`, 크기 불일치 시 파일명 변경 안내(#38) | L2-02 |
| `interior_setup` 등록 경로 B | 8단계 뒤 `register` | 마지막 단계(부모 리빌드·저장 뒤), `save_map` 패턴, 이미 등록된 항목 재사용 | V-03 #4, F3/F8 |
| 부모 버전 | Content 최신 v | 레벨의 `Zone_<parent>` 액터 버전 | R1-04 |
| `capture_all` 인자 | `mode` | + `quit_editor=False`(헤드리스는 `SystemLibrary.quit_editor()`) | V-03 #3 |
| `game_scripts` | 라벨 `<tag>_<preset>_<walk>` | + `label_suffix`(1080p 외 해상도·DLSS 구분) | L4-03 |
| 경로 상수 | 3곳 하드코딩 | `_pure.PATH_FOLDER`/`SCREENSHOT_FOLDER`(ini와 대조 테스트) | R1-06 |
| 합성 박스 UV | — | u∝+x·v∝z 고정 규칙: 숫자는 남면(−y)에서만 바로 읽힘(런북 §2 명시) | L2-06 |

**불확실 API**: 5.8 Python API 레퍼런스가 이번엔 열려 이름·시그니처는 확인했다(`citations`: AssetImportTask, Interchange 파이프라인 속성 `import_udi_ms`, Texture2D `virtual_texture_streaming`, StaticMeshEditorSubsystem, MaterialEditingLibrary, MaterialSamplerType, LevelEditorSubsystem PIE, EditorLevelUtils, UDIMTextureFunctionLibrary 등). 확인 못 한 것은 **동작**(OBJ가 레거시 FBX인지, `factory` 지정이 Interchange를 우회하는지, UDIM 자동 병합·크기 표기, 슬롯 이름 규약, PIE 시작 틱, `-ExecCmds` 시점, 임포트 후 텍스처/OBJ 배치 폴더 등) — 런북 §12 표 38행에 대안과 함께.

**판단한 것(스펙과 다른 점, 되돌리기 쉬움)** — 설계 §8 끝 목록 그대로: `blockers.glb` 미임포트(C++는 `blockers.json`만 읽음)·Content 복사는 `manifest.json`+`blockers.json`뿐 · MI는 청크당이 아니라 MTL 머티리얼당 · `collision.chunks`가 있으면 단일 `collision.glb` 미임포트 · 실내 서브레벨에 PostProcessVolume 없음(WP-05 오버레이가 실내 룩 담당) · Python은 `AGolmokPortal`을 놓지 않음 · 시점 이름 3/4/3·기본 프리셋 night 제외 · `-game`은 CSV 전용(스크린샷은 PIE; C++ `golmok.later` 미추가) · UDIM 파일명은 공식 규약만 인정 · 합성 실내 원점 = 방 남서 모서리.

**병합 전 보완 리뷰(오케스트레이터, Opus 읽기 전용, 2026-09-25)** — 위 2라운드 미검증 6건 판정과 추가 발견. 블로킹 2건은 병합 전에 수정했다.
| # | 발견 | 판정 | 조치 |
|---|---|---|---|
| A1 | 합성 zone(`ZONE_ORIGIN` = 스펙 §4 B)이 `L_ZoneTest`의 WP-04/05 픽스처 `z_synthetic_001`과 같은 원점·겹치는 footprint → PIE에서 겹침 해소(우선순위·버전 동률 → id 순)로 WP-06 zone의 시각 레이어가 숨겨지고 WP-04 벽·`door_1`이 §3/§5/§7에 섞임 | **블로킹** | 런북 §0: `L_ZoneTest`를 `L_ZoneTest06`으로 복제하고 픽스처 zone 액터 2개를 지운 사본에서 검증(`ZONE_TEST_MAP`, `.gitignore`, `actors 2` 로그 갱신). 원본 맵은 WP-05 자동화 테스트용으로 유지 |
| A2 | `legacy_flag` 경로가 캐시 적중 시 콘솔 플래그를 다시 보내지 않음 → 새 에디터 세션에서 청크 임포트가 Interchange로 가서 실패(V-05에서 드러남) | **블로킹** | `_importer_mappings` 캐시 적중 분기에서 `Interchange.FeatureFlags.Import.OBJ 0` 재전송 + 테스트 `test_legacy_flag_rearmed_on_cache_hit` |
| ① | UDIM 병합 판정이 컴파일 전 크기를 읽을 가능성 | 결함 아님(에디터 빌드의 `GetPlatformData`는 비동기 컴파일을 기다림; 타일 크기를 돌려줘도 중복 팩 1회뿐 — **V-04b에서 번복**: 중복 팩은 엔진 assert, 아래 "후속 V-04b F1~F3") | (0, 0)만 유해 → `size`에 0이 있으면 "unknown"으로 처리 |
| ② | Full Precision UV 미설정(half-float UV, UDIM u/v ≤ 10에서 8K 타일 기준 8~64 texel 계단) | 실제·잠재 품질 문제(V-04 256 px에서는 안 보임; Nanite 외 소비자 — 폴백 메시·HWRT·Lumen hit lighting) | **V-05 전** `StaticMeshEditorSubsystem.get/set_lod_build_settings`로 LOD0 `use_full_precision_u_vs=True`(hasattr 가드, 런북 §12 #41) — 반영(PR #107, PC 확인은 V-05 S7): `zone_import._full_precision_uvs`(청크마다 Nanite 전; 이미 True면 호출 없음; API·필드 없음·되읽기 실패는 임포트당 WARNING 1줄 뒤 계속), 요약 줄 `zone_import: full precision UVs (LOD0) on N/N chunks (…)`, 충돌 메시는 제외(위치만 씀) |
| ③ | TIF/JPG UDIM 앵커 크기 판정(PNG IHDR만) | 실제(pc-spike가 TIF를 허용했음) | pc-spike.md 텍스처 행을 **PNG만**으로, `_pure.import_plan`이 PNG 아닌 UDIM 세트에 경고 |
| ④ | `MI_<safe(material)>` 이름 충돌 미검출(대소문자만 다른 MTL 재질이 한 MI를 공유 → 뒤 텍스처가 이김) | 실제(드묾) | `tex_names`/`mi_names`를 소문자 키로, 충돌은 plan problem |
| ⑤ | 비인덱스 TRIANGLES의 감김 반전 누락 | 실제이나 현재 도달 불가(golmok-mesh GLB는 항상 인덱스) | 거울 매핑 + 비인덱스 프리미티브면 `ValueError` |
| ⑥ | 설계 §3-1/§3-2 UDIM 문구 ≠ 코드 | 코드 결함 아님 | "설계 대비 변경" 표가 우선(그대로) |
| B2 | `spike_runner._screenshot_ready`의 `os.replace`가 Windows에서 파일이 열려 있으면 PermissionError → 전체 캡처 중단 | 실제(드묾) | `OSError`면 다음 틱 재시도 |
| B4 | `synthetic_zone.unregister_interior_sublevel()`이 WP-05 픽스처 고정 | 사소 | `zone_id`/`version` 인자 추가(register와 대칭) |

V-04/V-05 메모(코드 미변경): (B3) `ResolveOverlaps`는 로드/언로드 이벤트마다 `apply_layers`가 숨긴 zone을 다시 보이게 할 수 있으므로 태그 b/c 캡처 중 zone 로드·언로드가 없어야 한다(`BasemapRescanSeconds=0`); (B5) `route=fbx`에서 임포터가 옵션을 무시하면 청크마다 MTL의 8K 텍스처를 임포트했다 지운다 — 실데이터에서 느리면 Saved MTL 사본에서 `map_*` 줄을 빼는 방안; (B6) `_set_nanite(mesh, True)`는 100 % 폴백 메시(5~15M tri 청크에서 디스크·메모리 2배) — 스파이크 수치에 반영; (B8) `legacy_flag` 경로는 그 에디터 세션 동안 OBJ CVar를 0으로 남긴다(런북 §12 #1).

**남은 것 / PC 인계(V-04, `pc-verify-wp06.md`)**
- §1 생성기 → §2 `zi.run(...)`(route·매핑 실측·UDIM 병합 표기·Nanite 청크 bbox를 결과 표에) → §3 PIE 걷기 → §4 `it.run(...)` → §5 포털 왕복 → §6 재실행 → §7 `capture_all` 리허설(에디터 창 뒤로 보낸 채 한 번 더) → §8 `-game` 성능 스크립트 → §11 결과 표. 컴파일/실행 오류는 §12 표 번호로 고치고 `WP-06: PC fix …` 커밋.
- 미검증 2라운드 소견 6건(위 표)은 병합 전 Opus 보완 리뷰 또는 V-04에서 판정. 특히 ③(TIF UDIM)·④(MI 이름 충돌)는 실데이터에서 먼저 드러날 수 있다.
- 스파이크(V-05)는 `pc-spike.md` S0~S15; `night` 프리셋 화면 검정·HUD render ms 0·언로드 뒤 `blocked` 표시는 WP-09/D-010 몫(V-03 발견).
- 2026-09-28 (PR #43): 런북 §0의 duplicate_asset→load_level fatal(Astra T5 2026-09-28, EditorServer.cpp:2544 World Memory Leaks) — save_layer_levels가 같은 패턴이라 Save As로 선제 수정, PC 미검증(V-04 §8 2단계에서 확인). `spike_runner.save_layer_levels`는 태그마다 원본을 다시 열고 `EditorLoadingAndSavingUtils.save_map`으로 `L_Spike_<tag>`에 저장한 뒤 그 맵이 열린 상태에서만 레이어를 적용하며, 원본은 쓰지 않는다: 에디터 호출 전에 태그를 검사하고 `L_Spike_*` 원본은 오류, 원본(외부 액터·오브젝트 패키지 포함)에 저장 안 된 변경이 있으면 오류(`capture_all`이 남긴 레이어 플래그가 사용자 맵에 저장되지 않게, J26), 열린 맵이 원본과 다르면 경고 후 진행, `base_level`은 객체 경로도 받는다(`_current_level_path`와 같은 정규화). `save_map`이 열린 월드 이름을 바꾸는지는 V-04 §8 2단계·런북 §12 #18에서 확인(V-07 wp09 §4 사전 단계가 이름 바꾸기 쪽 근거).
- 2026-09-28 (후속 #28, V-04 T5 소견 3건; 제품 동작·ini·C++ 변경 없음, PC 미검증): ① `_PiePerf` WAIT_CSV 조기 완료(런북 §11 인계 6 — 엔진은 `CsvProfile Start` 즉시 `Profile(<stamp>).csv`를 만들고 경로가 끝날 때까지 쓴다) → 새 순수 판정 `_pure.csv_complete`: 가장 새 CSV의 (mtime, 크기)가 `CSV_SETTLE_S` 2 s 동안 안 바뀌고, 경로 길이를 알면 PLAY + 길이가 지났고 그 끝 − `CSV_END_SLACK_S` 1 s 이후에 바뀐(= Stop flush) 파일만 완료. 변경 시각은 상태기계 시계(`_now`)로 관측해 파일 시계와 섞지 않는다. 길이 0/미상은 경로 조건 없이 settle만, 타임아웃(길이 + 60 s)·`sr.missing`은 종전(파일이 있으면 why에 이름·마지막 변경 시각). ② `run_game_perf.ps1` 자기 복사 경고(런북 §11 `-game` 성능) → `_pure.copy_path_dirs`: 모든 경로 JSON이 이미 있는 후보 폴더(Windows 경로 정규화·대소문자 무시)는 `$pathDirs`에서 빼고, 남는 후보가 없으면 `$pathDirs = @()`에 복사 블록 생략. ③ Zone 인덱스 발견 격리(인계 7, 리뷰 T2) → `_pure.game_command_line(..., discover_from_index=None|True|False)`·`spike_runner.game_scripts(..., discover_from_index=)`: bool이면 `-ini:Game:[/Script/Golmok.GolmokZoneSubsystem]:bDiscoverFromIndex=<값>`을 `-ExecCmds` 바로 앞에(None = 종전 argv). 런북 §0 에디터 실행 줄(같은 `-ini:` 인자, `open-editor.ps1`은 인자 없음)·§8 3단계 `discover_from_index=False`·§9 대기 설명·§12 #39. 실 스파이크(`pc-spike.md`)는 인덱스 발견을 켜 둔다(기본 None). 테스트: `fake_unreal`의 CSV가 엔진처럼 생성 → `csv_flush_s`마다 증가 → 경로 끝 `csv_stop_s` 뒤 마감, `csv_complete` 경계값 표, CSV 없음·계속 기록·길이 0·조용한 캡처·두 후보 폴더·`.ps1` 복사 블록·`-ini:` 위치.
- 2026-09-28 (후속 #29, PR #44 리뷰 F1/F3; `spike_runner` WAIT_CSV만, 제품 동작 불변, PC 미검증): settle = min(max(`CSV_SETTLE_S` 2 s, 1.5 × 같은 파일의 연속 변경 간 최대 간격(출현은 제외)), `CSV_SETTLE_MAX_S` 10 s)(`_pure.csv_settle_s`), 폴더 glob·stat은 `CSV_POLL_S` 0.25 s마다(판정이 최대 한 폴 늦음). fake_unreal `csv_lag_s`(경로 끝 뒤 지연 종료). 재현: flush 3 s·lag 8 s → 종전 +8.6 s(기록 중 채택) → +17.8 s(Stop 뒤). PR #47 리뷰(Opus): BLOCKING·major 없음 — R29-1 런북 §9 문구 확장, R29-2 파일 전환 의미 테스트 고정, R29-3 테스트 경계 폴 간격 반영(병합 커밋), R29-4 폴링 양자화 +0.1~0.27 s(허용), 남은 한계: 첫 쓰기가 경로 끝 − 1 s 이후에 처음 오면 2 s settle이 먼저 끝날 수 있음(경로 < flush 주기 + 1.5 s일 때만).
- 2026-09-29 (**후속 V-04b F1~F3**, "병합 기록 — V-04b"의 후속 과제; `zone_import`·`interior_setup`·`synthetic_zone`·`viewpoints`와 테스트 fake만, C++·ini 변경 없음, PC 미검증): **F1 UDIM 폴백 안전화**(런북 §12 #4·#38) — `unreal.SystemLibrary.get_command_line()`에 `-nullrhi`가 있거나(`-AllowCommandletRendering` 없는 `-run=` 커맨드릿 포함) 크기가 0이면 `_pack_udim_tiles`를 부르지 않고 `how="merged by importer (size unverifiable without RHI)"` + WARNING(`… not verifiable without RHI (-nullrhi|size WxH); pack fallback skipped …`); `get_command_line`이 없으면 크기 판정대로 팩하되 WARNING. 폴백 타일은 원본 `name.1001.png`가 아니라 work 폴더 `<Saved>/Golmok/zone_import/<id>/v<n>/textures/<T_name>_u<u>v<v>.png` 사본(엔진 UDIM 규칙 `[._]####` 밖 이름)에서 임포트한다. **보완 리뷰 ① 판정 번복**: "타일 크기를 돌려줘도 중복 팩 1회뿐(무해)"은 틀렸다 — `make_udim_virtual_texture_from_texture2_ds`는 입력마다 `Source.GetNumLayers() == 1 && GetNumBlocks() == 1`을 `check`하므로 병합된 텍스처(또는 multi-block으로 들어온 타일)를 다시 묶으면 헤드리스에서 appError로 에디터가 끝난다(`_pack_udim_tiles` docstring에 기록). fake `FakeUdimLibrary`가 multi-block 입력과 `[._]####` 이름 타일에 이 assert를 흉내 내고, `nullrhi=True` 노브는 병합 UDIM이 첫 블록(타일) 크기를 보고하게 한다. **F2 작업 경로 절대화**(#31 확대) — 공용 `synthetic_zone.abs_project_path`(`spike_runner._abs`와 같은 규칙: `hasattr` 가드 `convert_relative_path_to_full` → `normpath(abspath)`)를 `zone_import._saved_dir/_content_dir`(→ `work_dir`·매핑 캐시·프로브·OBJ/MTL·충돌 GLB 사본·Content 복사), `interior_setup._parent_manifest`, `synthetic_zone._saved_dir/_content_dir`, `viewpoints.capture`의 saved dir에 적용(`spike_runner._abs`는 그대로). fake `relative_paths=True`는 `../../../../Saved/`(CWD `UE_5.8/Engine/Binaries/Win64` 기준)를 돌려준다. **F3 재임포트 교체 보강**(#8·#37) — `_ensure_path`는 `delete_asset`이 True를 돌려준 뒤에도 `does_asset_exist(target)`이면 rename·duplicate를 하지 않고 `zone_import: ERROR replace: <target> still exists after delete_asset returned True (…; on disk <…>.uasset: present|absent) … Work-around (runbook #8): …`를 `log_error`로 남긴 뒤 `ZoneImportError("replace")`; zone 텍스처는 스크래치 없이 규약 경로에 `replace_existing=True`로 제자리 임포트(재임포트 시 같은 객체 — MI 참조 유지, 삭제·rename 없음; 임포터가 다른 이름을 붙이면 `_ensure_path`로 옮기고 경고 #4), 메시·`T_ZoneScanDefault`는 스크래치 유지, `reimport_textures=True` 기본값 유지. fake `_register`는 `replace_existing`이면 같은 클래스의 기존 객체를 제자리 갱신한다(에셋 설정 `props` 유지). 범위 밖으로 남긴 것: `zone_index._content_dir`(WP-09, `with_index=True` 경로)도 같은 상대 경로 패턴 — 별도 후속. 런북 §2(임시 주의 → 수정됨)·§6 3단계(`moved` 줄 수·PC 재현 카드)·§12 #4·#8·#31·#37·#38 갱신, #40(`get_command_line`) 신설. 테스트 +15(`test_ue_python_zone_import.py`: nullrhi 병합/비병합·0×0·GUI 팩과 `get_command_line` 부재·명령줄 판정 6종·타일 사본 이름·상대 경로 2종(CWD를 바꿔 `convert_relative_path_to_full`·`interior_setup`·`viewpoints`까지 확인)·삭제 뒤 잔존·텍스처 제자리 재임포트·임포터 이름 다름) + 기존 5개 갱신(호출 순서·타일 이름·잔존 단계·interior 순서·fake UDIM assert). PC 확인: 헤드리스 `zi.run` 스모크(`-nullrhi`), 새 에디터 프로세스에서 §6 3단계, 긴 worktree 경로 재현.

## 병합 기록 — T5 PR #41 (2026-09-28, 오케스트레이터 세션; V-04 결과)

**V-04 결과**: 🟢. 2026-09-28 ChatGPT Astra T5(PC, 브랜치 `astra/v04-verify-wp06`, [#41](https://github.com/wooklym/golmok/pull/41), head 937d028)가 런북 `runbooks/pc-verify-wp06.md`를 실행했다. 필수 §0~§8 기능 통과(§2 텍스처·청크, §4 실내, §6 재실행은 자동 단언 통과·사람 눈 관찰 미완 = "부분 확인"), §3·§5는 InputKey 드라이버(`Tests/GolmokCharacterRosterZoneWalk.cpp`, RenderEvidence `-GolmokZoneWalk` opt-in, 등록 28 유지) 6코스 25단언 통과, §7 20장×전경/백그라운드 2560×1440·누락 0, §8 b·c·ac 레이어 맵 생성(Save As, `save_map`은 열린 맵 이름을 바꾸지 않아 §12 #18 ④ 디스크 재열기 경로 확인)·`-game` a 139.1 fps(1% low 11.1)·b 164.6 fps(1% low 12.4, 단일 측정·품질 판정 아님). 선택 §9는 실행 실패(`_PiePerf` WAIT_CSV가 생성 중 CSV를 완료로 판단, 2프레임), §10 미실행. 제품 코드 수정 없음. 결과 표·재현·인계는 런북 §11, 스크린샷 `runbooks/pc-verify-wp06-*.jpg` 4장.

**병합 전 리뷰(Opus 읽기 전용, 2026-09-28)**: BLOCKING·major 없음. 확인: 변경 7파일(런북·JPG 4·테스트 2)만으로 레인 준수, 제품 Python/C++·공유 문서·hot-spot 변경 없음, `IMPLEMENT_*_AUTOMATION_TEST` 28=28, §0 Save As 블록이 08:44Z 지시와 동일, main의 §8 2단계·§9·§12 #18 바이트 단위 유지, §11 표기가 본문·PR 본문·코드 단언 집계·JPG(LFS sha256 일치)와 일치, ZoneWalk 드라이버가 결정 조건(실제 폰·`InputKey`·초기 배치 1회·nullrhi/맵 누락/인덱스 zone/PlayerStart 편차/타임아웃 시 명시적 실패)을 지킴, 천장 trace 대체 타당(점프 정점 274 cm < 300 cm). minor 5·note 4:
- (T1) STATUS 인계 문안이 칸별이 아님 → 병합 커밋에서 병행 트랙·트랙 1B 행을 칸별로 작성, "해시 불변"은 §8 전후로 한정.
- (T2) 설계와 다른 동작: WP-09 zone 인덱스 발견이 WP-04/05 합성 zone을 `L_ZoneTest06`에 겹쳐 로드 → 최종 프로세스에만 `-ini:Game:[/Script/Golmok.GolmokZoneSubsystem]:bDiscoverFromIndex=False` 적용, `-game`은 Saved 아래 실행 사본 스크립트로 측정. 병합 커밋에서 런북 "재현과 인계" 7번·§8 행에 기록. 런북 §0/§8·`spike_runner.game_scripts` 격리 반영은 Claude 레인 후속(#28).
- (T3) §5 포털 로그 발췌가 축약본 → 병합 커밋에 명기, 원문은 Astra가 PR 코멘트로 제공하면 후속에서 반영.
- (T4) 코스 0·1의 1 s 압박 측정이 W 입력 뒤 고정 2 s 시작으로 접촉 시점과 겹침 → 재실행 시 거짓 FAIL 가능(거짓 PASS는 접촉면 단언이 막음). Astra 레인 후속.
- (T5) §8 레이어 상태(Visual off·AutoManaged ✖·복귀) 직접 확인 기록 없음 → 병합 커밋에 "미기록(fps 차이로 간접)".
- (T6) `Fail()`의 `golmok.path stop`이 잘린 녹화로 `walk_01.json`을 덮어쓸 수 있음, (T7) `-GolmokZoneWalk` 분기가 다른 opt-in 플래그를 말없이 건너뜀 → Astra 레인 후속. (T8) §5 "2회 확인"은 단언 1 + 로그 1(참고). (T9) §12 #18 불확실한 점에 T5 결과 반영(병합 커밋).

**병합**: 오케스트레이터 결정(D-019). `V-04: 병합 시 반영 (Fable)` 커밋으로 위 문서 반영 뒤 merge commit. 다음: V-05 스파이크는 `runbooks/pc-spike.md`(PC), Claude 후속 #28(`_PiePerf` WAIT_CSV·PS 자기 복사·인덱스 격리), Astra 후속 T4/T6/T7은 다음 배정에.

## 병합 기록 — 후속 #28 PR #44 (2026-09-28, 오케스트레이터 세션)

**후속 #28 내용**: T5(PR #41) 소견 3건 — ① `_PiePerf` WAIT_CSV 기록 완료 판정(`_pure.csv_complete`: 경로 길이 경과 + 경로 끝 − 1 s 이후 변경 + 2 s 정지), ② `run_game_perf.ps1` 자기 복사 제거(`_pure.copy_path_dirs`), ③ `game_scripts(discover_from_index=)` → `-ini:Game:[/Script/Golmok.GolmokZoneSubsystem]:bDiscoverFromIndex=<값>`(기본 `None` = 종전 argv), 런북 §0/§8/§9/§12 #39. 제품 동작·ini·C++ 변경 없음, PC 미검증(다음 PC §8·§9가 첫 확인). Opus 구현, pytest 837 → 864 passed.

**병합 전 리뷰(Opus 읽기 전용, 2026-09-28)**: BLOCKING·major 없음. 확인: 시계 혼용 없음(`_now` 관측 시각만 비교, `not_before`는 후보 필터), 이전 작업의 CSV를 다음 작업이 가져갈 수 없음, 변이 테스트로 새 테스트가 옛 동작(존재만 확인)을 잡음, fake CSV 동작이 C++(첫 틱 `BeginCsv`·`EndPlayback` Stop·`Deinitialize` 'world ending')와 일치, 생성 `.ps1`이 pwsh 7.4에서 파싱 오류 0·`$pathDirs = @()` 실행 정상·자기 복사 경고 없음, `-ini:` 인자가 `-ExecCmds` 바로 앞 한 토큰·`None`이면 argv 바이트 동일, 엔진 `-ini:<File>:[Section]:Key=Value` 문법·T5 실측(HUD `0 discovered`)과 일치, §0 `Start-Process` 따옴표 정상, `_pure.LOG`·런북 기대 로그 불변. minor 2·note 1:
- (F1, minor) 엔진이 2 s 넘는 간격으로 CSV를 쓰고 히치로 게임 시간이 실제 시간보다 늦어져 재생이 JSON 길이를 넘기면, 아직 쓰는 중인 CSV를 완료로 볼 수 있다(fake 재현: flush 3 s·지연 8 s). 피해는 참고치 PIE CSV의 꼬리 몇 초. 오케스트레이터 결정: 코드는 그대로, 런북 §9에 한 줄(프레임 수가 길이 × fps에 못 미치면 히치·재실행) 추가; 적응형 settle(관측 최대 변경 간격 × 1.5, 상한 10 s)은 (B) 후속.
- (F2, minor) 런북 §7 무인 실행 줄에 `-ini:` 인자가 없어 그 단계는 인덱스 발견이 켜진 채 돈다 → 병합 커밋에서 추가, #39 행에 §7 명시.
- (F3, note) WAIT_CSV가 캡처 내내 매 틱 두 폴더를 glob·stat(0.18 ms/폴 Linux, Windows는 더 느림) — 참고치 CSV라 그대로 둠; 0.25 s 간격 폴링은 (B) 후속.

**병합**: 오케스트레이터 결정(D-019). `WP-06: 병합 시 반영 (Fable)` 커밋으로 F2·F1 런북 반영 뒤 merge commit. PC 확인 항목: 다음 PC 세션의 §8(`.ps1` `$pathDirs`·`-ini:`)·§9(`csv` 줄 시각 ≈ 길이 + 2 s, 프레임 수).

## 병합 기록 — V-04b [#67](https://github.com/wooklym/golmok/pull/67) → [#68](https://github.com/wooklym/golmok/pull/68) (2026-09-29, 오케스트레이터 세션)

**V-04b 결과**: 🟢. Claude PC 세션(워크트리 `wonderful-herschel-567471`, 브랜치 `pc/v04b-verify-wp06-followup`, head 4f7b7c1)이 후속 #28 [#44](https://github.com/wooklym/golmok/pull/44)·#29 [#47](https://github.com/wooklym/golmok/pull/47)을 main `5f6c810`과 `87e13d8` 두 빌드에서 §8·§9로 확인했다: §12 #39 격리(HUD `0 discovered`, `-game` 로그에 `discovered from index` 없음), §8 3단계 `.ps1`(`$pathDirs`는 경로 JSON 원본 폴더를 제외해 `%LOCALAPPDATA%` 항목만·`-ini:…bDiscoverFromIndex=False`가 run마다 `-ExecCmds` 앞 1회·`-csvCaptureFrames` 없음·자기 복사 경고 0줄·a/b CSV 생성·`ExitAfterCsvProfiling` 자기 종료, 두 빌드 생성본 바이트 동일), §8 2단계 b·c·ac 저장·`L_Spike_b` `Auto Managed` ✖ 눈 확인, §9 `csv` 수락 = 경로 73.0 s + 2.1 s(`5f6c810`)/2.3 s(`87e13d8`)·`golmok-perf` 8,348/8,381프레임. 문서만 커밋(STATUS 자기 행·런북 §11 인계 8).

**병합 전 리뷰(Opus 읽기 전용, R67-1~15, 2026-09-29)**: (A) 없음. 확인: 변경 2파일과 5묶음 규칙 준수, PR 본문·런북·STATUS 수치 일치, main 코드와 일치(`_pure.game_command_line`·`copy_path_dirs`·`csv_complete`, settle = max(2, 1.5 × 최대 간격)·폴링 0.25 s), 프레임 수 산술(perf 프레임/평균 fps ≈ 73 − 2 s), D1 관찰이 옳음(`bVisualVisible`은 UPROPERTY가 아니고 `bAutoManaged`만 저장). 정정(R67-3): #47 적응형 settle 확대는 이 PC에서 발동하지 않았다(기본 경로 확인). 리뷰 게이트 pytest 1211 passed/3 skipped·CI 10/10. UE 실행 산출물은 클라우드에서 확인 불가.

**준비 단계 결함(V-04b 판정 범위 밖, `zone_import` Claude 레인) → 후속 과제 "WP-06 후속 V-04b F1~F3"(Opus ultracode, V-05 전)**
- **F1** zone_import UDIM 폴백 안전화: `-nullrhi`(`unreal.SystemLibrary.get_command_line()`)이거나 크기를 판정할 수 없으면 `_pack_udim_tiles`를 생략하고 `how="merged by importer (size unverifiable without RHI)"` + WARNING(#4); 타일은 work 폴더의 UDIM 규칙(`[._]####`) 밖 이름 사본(예: `<name>_u0v0.png`)에서 임포트; `FakeUdimLibrary`가 multi-block 입력에 예외를 내도록 해 엔진 assert를 흉내 내고 테스트 추가. **보완 리뷰 ① 판정 번복**: "타일 크기를 돌려줘도 중복 팩 1회뿐(무해)"는 틀렸다 — 헤드리스에서 중복 팩은 엔진 assert(appError)로 끝나고, 폴백 경로는 PC에서 성공한 적이 없다(T5·V-04b 모두 importer 병합). 임시 조치: 런북 §2 주의(GUI 전용).
- **F2** zone_import·interior_setup 작업 경로 절대화: `_saved_dir`/`_content_dir`(`unreal.Paths.project_*_dir()`의 `..` 상대 경로, CWD `Engine\Binaries\Win64` 기준 269자 > 260)를 `spike_runner._abs`(§12 #31) 규칙으로 공용화(`convert_relative_path_to_full` + `normpath(abspath)`), `interior_setup._parent_manifest`에도 적용, FakePaths 상대 경로 테스트, 런북 §12 #31 파일 칸 확대.
- **F3** zone_import 재임포트 교체 경로 보강: `_ensure_path`에서 강제 삭제 뒤 `does_asset_exist(target)` 재검사·잔존 시 rename/duplicate 대신 명확한 ERROR와 우회(#8); 텍스처는 규약 경로에 `replace_existing=True` 제자리 재임포트(스크래치·rename 불필요, MI 참조 유지 — PNG가 `<dest>/<name>`에 바로 놓이는 것이 V-04·V-04b 로그로 확인돼 #37 텍스처 의문 해소), 메시는 스크래치 유지; fake "삭제 뒤 잔존" 시나리오; PC 재현 카드(새 에디터에서 §6 3단계). `reimport_textures=True` 기본값은 유지.
- **F4**(Astra 레인 `Tests/GolmokCharacterRosterZoneWalk.cpp`): 창 포커스를 잃으면 `FlushPressedKeys`로 W가 떼져 `waypoint blocked or no input`로 멈춤 → Astra T7 RHI 실행 과제에 포함(astra-tasks T7 행, 이슈 #30).
- D1·D2·R67-1/3/11 문구는 이 병합 커밋에서 런북·STATUS·ROADMAP에 반영. R67-12(`87e13d8` §9 원시 시각)는 PC 세션 코멘트 대기(병합을 막지 않음). R67-15(추적 안 되는 `M_ZoneScan`·`T_ZoneScanDefault` 커밋 여부)는 V-05/V-06에서 결정.

**병합**: 오케스트레이터 결정(D-019). PC 브랜치 push 없음; 클라우드 병합 브랜치 `claude/v04b-merge`에 `V-04b: 병합 시 반영 (Fable)` 커밋 뒤 merge commit, PC PR #67은 close. 다음: F1~F3 후속(클라우드, V-05 전) → V-05 `runbooks/pc-spike.md`; Astra T7 RHI는 C-07 뒤.

## 병합 기록 — 후속 V-04b F1~F3 [#69](https://github.com/wooklym/golmok/pull/69) (2026-09-29, 오케스트레이터 세션)

**내용**: "병합 기록 — V-04b"의 후속 과제 F1~F3을 Opus ultracode 세션(session_01EBy6HrphMJGPbANi4KZKiN, 구현 + 검증 에이전트 3)이 Claude 레인 파일만으로 구현했다(`zone_import.py`·`interior_setup.py`·`synthetic_zone.py`·`viewpoints.py`, fake·테스트, 런북 §2/§6/§12, 이 문서 결과 절). F1: `_without_rhi()`가 `unreal.SystemLibrary.get_command_line()`의 `-nullrhi`/`/nullrhi` 토큰 또는 `-AllowCommandletRendering` 없는 `-run=` 커맨드릿을 RHI 없음으로 판정하고, RHI가 없거나 크기가 0이면 `_pack_udim_tiles`를 생략해 `how="merged by importer (size unverifiable without RHI)"`+WARNING 1줄(#4); `get_command_line`이 없으면 종전대로 팩하고 #40 WARNING; 타일은 `<work>/textures/<T_name>_u<u>v<v>.<ext>` 사본(UDIM 규칙 `[._]####` 밖)에서 임포트; `FakeUdimLibrary`가 multi-block·UDIM 이름 타일에 엔진 assert를 흉내 냄. F2: 공용 `synthetic_zone.abs_project_path`(`spike_runner._abs`와 같은 규칙)를 `zone_import._saved_dir/_content_dir`·`interior_setup._parent_manifest`·`synthetic_zone`·`viewpoints.capture`에 적용(`zone_index._content_dir`는 범위 밖). F3: `_ensure_path`가 강제 삭제 뒤 `does_asset_exist`를 재검사해 잔존이면 rename·duplicate 없이 `zone_import: ERROR replace: …`(대상·디스크 `.uasset` 유무·우회 #8) → `ZoneImportError("replace")`; zone 텍스처는 규약 경로에 `replace_existing=True` 제자리 재임포트(MI 참조 유지), 메시·`T_ZoneScanDefault`는 스크래치 유지, `reimport_textures=True` 기본값 유지.

**병합 전 리뷰(Opus 읽기 전용, R69-1~11, 2026-09-29)**: (A) 없음. 확인: 레인 준수·병합 기록 절 불변·시험 병합 no-op, 명령줄 판정 21개 입력이 UE `FParse::Param`과 일치(따옴표 안 `-nullrhi`만 안전 방향 거짓 양성), RHI가 있을 때 팩 판정은 main과 동일, 타일 사본 이름이 UDIM 규칙에 절대 걸리지 않음, `abs_project_path`가 `spike_runner._abs`와 동일·순환 import 없음·R67 호출 지점 전부 절대 경로화, 잔존 검사 뒤 rename/duplicate 없음, fake 재임포트가 UE 팩토리의 객체 재사용과 일치(5.8.3 미확인). (B) R69-1 우회 안내 폴더를 `Zones/<zone>` 전체에서 `Zones/<zone>/v<n>`으로 한정(실데이터의 다른 버전·부모 manifest 보호) → 리뷰 반영 push 78398dc(R69-3/4 명령줄 파라미터 `/nullrhi`·`-nullrhi=1`·빈 문자열+ids, R69-5 docstring, R69-7 #40 경고 호출당 1회, R69-9 재실행 `moved` 단언 포함); R69-2 런북 §6 카드에 `could not rename` 경우 기록 한 줄(이 병합 커밋). (C) 후속: R69-6 WARNING `why` 세분화, R69-8 `zone_index._content_dir`·`viewpoints._store_path`·`spike_runner._viewpoints`의 같은 상대 경로 패턴과 `spike_runner._abs` 중복·`import_assets(work_dir)` normpath만, R69-11 `_import_in_place` 실패 시 잔존 텍스처(다음 실행 `_cleanup_folder`)·설계 §0 D5 문구. R69-10(경로 길이 1자 차이)은 조치 불필요.

**게이트**: 리뷰 worktree pytest 1226 passed/3 skipped(main 1211 + 15), 리뷰 반영 push 뒤 1229 passed/3 skipped; ruff·format·check_repo·diff --check 통과; CI 10/10; 변이 15개 중 14개 잡힘(M14 `/nullrhi` 분기 제거 생존 → R69-3으로 해소). **클라우드에서 확인 불가**(UE 5.8.3 실행 전부): `-nullrhi`에서 `blueprint_get_size_x` 실제 값, `get_command_line` Python 노출 여부, `replace_existing=True` 제자리 재임포트 때 같은 UObject 재사용, `delete_asset` 뒤 `does_asset_exist` 실제 값, MAX_PATH 실측.

**PC 카드(V-04c, C-07 뒤; V-05 착수 전)**: ① 헤드리스 스모크 — `Content\Golmok\Zones\z_synthetic_scan_001` 삭제 뒤 V-04b F1 재현 명령(`UnrealEditor-Cmd.exe <uproject> -ExecCmds="py <zi.run 스크립트>" -unattended -nullrhi -nosplash -nopause -nosound`)으로 실행; 기대(태그 우선 [PR #122](https://github.com/wooklym/golmok/pull/122) 뒤): assert 없이 종료, `zone_import: texture …/Textures/T_facade tiles=[1001, 1002, 1011] size=512x512 vt=on (merged by importer)`, 텍스처 WARNING 0줄, `done … 8 assets, 0 warnings` — 크기는 `Dimensions` 태그(런북 §12 #42)라 `-nullrhi`에서도 GUI와 같은 판정이다. V-04c 실행 때(#69 기준)의 기대 `zone_import: WARNING texture T_facade: UDIM merge not verifiable without RHI (-nullrhi); pack fallback skipped - check the texture in a GUI editor (runbook #4)` 1줄·`(merged by importer (size unverifiable without RHI))`·`done … 8 assets, 1 warnings`·`size=256x256`(첫 블록)은 이제 태그를 읽지 못할 때만 나온다(나오면 §12 #42에 기록). #40 경고가 나오면 `get_command_line` 미노출(태그가 있으면 나오지 않음); 이어 GUI에서 `T_facade` 512×512·3색. ② 새 에디터 프로세스에서 런북 §6 3단계 + 실내 `it.run` 재실행 1회 — 기대 `done … 0 warnings`·`moved` 4줄·`size=512x512 (merged by importer)`·`MI_*` BaseColor 유지·텍스처 `deleted`/`renamed` 줄 없음; 실패 시 `ERROR replace` 또는 `could not rename` 줄 전체·디스크 `.uasset`·`LogAssetRegistry`·`LogUObjectGlobals`. ③ 긴 worktree 경로(`.claude\worktrees\…`, junction 없이)에서 §2·§4 — 로그 경로에 `..` 없음, 실내 충돌 GLB 사본 성공. 실내 `it.run`은 WARNING 1줄로 끝난다: Interchange가 50자 충돌 메시 `SM_z_synthetic_scan_001_room_collision_c_e000_n000`을 41자 `SM_z_synthetic_scan__ollision_c_e000_n000`으로 줄여 임포트하고, 코드가 `rename_asset`으로 규약 이름을 되돌리며 `… renamed to …/SM_z_synthetic_scan_001_room_collision_c_e000_n000 (importer naming; runbook #29)`를 남긴다 — `interior_setup`은 warnings 1개(V-04 `.claude\worktrees\focused-herschel-9c2aa9`에서 관찰, V-04c에서 재현; 무해, 런북 §4·§12 #29). ④ (가능하면) GUI 폴백 PC에서 `Textures/_tiles/T_facade_u0v0` 팩·§6 재실행 제자리 재임포트 뒤 재팩. ⑤ 선택: `-run=pythonscript` 커맨드릿 1회(커맨드릿 규칙 True, 문구 `(commandlet -run=pythonscript without -AllowCommandletRendering)` — R69-6, [PR #81](https://github.com/wooklym/golmok/pull/81)에서 원인별 문구로 바뀜) 태그 우선 [PR #122](https://github.com/wooklym/golmok/pull/122) 뒤로는 커맨드릿도 태그로 판정하므로 이 WARNING 대신 `size=512x512 … (merged by importer)`가 기대다(문구는 태그가 없을 때만). 2026-10-09 측정에서 그대로 나왔다. 다만 커맨드릿에는 #41 API가 없어 `done … 1 warnings`(#41 WARNING)다(런북 §11 인계 10). ⑥ (태그 우선 [PR #122](https://github.com/wooklym/golmok/pull/122)) GUI 에디터에서 `T_facade`의 `Dimensions` 태그(`{str(k): str(v) for k, v in unreal.EditorAssetLibrary.get_tag_values(p).items()}["Dimensions"]`)와 `blueprint_get_size_x/y`를 에디터 시작 직후와 텍스처 컴파일 뒤(≈20 s)에 기록 — 기대: 태그는 처음부터 `512x512`, `blueprint_get_size_x/y`는 컴파일 뒤 512×512(직후엔 32×32일 수 있음), §2 텍스처 줄 `size=512x512 … (merged by importer)`(런북 §12 #4·#42, §11 인계 10) → **2026-10-09 확인(§11 인계 10)**: 시작 직후 태그 `512x512`·blueprint 32×32, 재임포트 뒤 둘 다 512×512. 헤드리스 ①도 같은 날 새 기대대로 통과.

**병합**: 오케스트레이터 결정(D-019). `WP-06: 병합 시 반영 (Fable)` 커밋(STATUS WP-06·V-05 행·마지막 갱신·세션 로그, ROADMAP zone_import 줄, 런북 R69-2/9, 이 절) 뒤 merge commit. 다음: V-04c PC 카드(C-07 뒤) → V-05 `runbooks/pc-spike.md`; R69-6/8/11은 다음 Claude 레인 push.

## 결과 — Claude 레인 (C) 후속 R69-6·8·11 (2026-09-30, Opus 5.5 ultracode, 세션 `session_018jS3GS3eQh6nV78bWyUb1m`, 브랜치 `claude/claude-lane-c-followups`) — 🟡 코드 완료·PC 확인은 V-04c 카드에 합침
"병합 기록 — 후속 V-04b F1~F3 #69"의 (C) 후속 3건을 처리했다. 설계 변경은 없다(§0 D5는 실제 동작에 맞춘 문구 수정뿐).

| 항목 | 변경 | 테스트 |
|---|---|---|
| R69-6 WARNING 원인 | `_no_rhi_reason()`이 원인 문자열을 준다: `-nullrhi`, `/nullrhi`, `commandlet -run=<x> without -AllowCommandletRendering`; RHI가 있으면 `''`, `get_command_line`이 없으면 `None`. `_without_rhi()`는 이것으로 판정한다(True/False/None 의미 불변). WARNING은 `UDIM merge not verifiable without RHI (<원인>)`이고, 크기 0은 `UDIM merge not verifiable: the editor reports size 0x0 (no texture data yet)`으로 문장을 나눴다. `-nullrhi` 문구는 그대로라 V-04c 카드 ①의 기대 줄은 바뀌지 않는다. ⑤ 커맨드릿의 기대 문구는 `(commandlet -run=pythonscript without -AllowCommandletRendering)`로 바뀐다 | `test_no_rhi_warning_names_its_cause`(4), `test_without_rhi_reads_the_command_line`에 원인 일치 단언(9), `test_no_rhi_reason_is_none_without_get_command_line`, 크기 0 문구 |
| R69-8 경로 도우미 | `synthetic_zone.abs_project_path` 하나로 모았다. `spike_runner._abs`는 그 별칭이다(중복 구현 삭제). `zone_index._content_dir()` 기본값은 `zone_import._content_dir()`이고, 명시 폴더는 CWD 기준 `abspath`다. `viewpoints.store_file(level)`(새 함수, 절대 경로)를 `_store_path`와 `spike_runner._viewpoints`가 같이 쓴다. `import_assets(work_dir)`는 `normpath(abspath)`다. 순환 import 없음(`spike_runner → synthetic_zone → basemap_import`) | `test_every_project_dir_goes_through_abs_project_path`(상대 편집기 경로 + 바이너리 폴더가 아닌 CWD(공백 포함), `..`, 명시 폴더) + 기존 `test_relative_project_dirs_are_made_absolute` |
| R69-11 실패 임포트 잔재 | `_import_in_place`가 `_pick`·`_ensure_path`에서 실패하면 `_discard_failed_import`가 그 임포트가 만든 에셋 중 `target` 밖의 것을 지우고(실제로 지운 것만 `zi.cleanup` 줄 — 검증 V1로 `_delete_assets`가 `delete_asset`의 반환값을 본다) 원래 예외를 다시 던진다. 지우지 못한 by-product(Texture2D·Material·MIC)는 `WARNING texture import failed; could not delete <path> - the next run's cleanup step removes it (runbook #8)`이다. 다음 실행의 `_cleanup_folder`가 계획 밖 Texture2D를 지운다. 런북 §12 #37, 설계 §0 D5 문구 | `test_failed_in_place_texture_import_removes_what_it_imported`, `test_undeletable_leftover_is_warned_and_swept_by_the_next_run`, `test_failed_texture_import_keeps_the_previous_target`, `test_cleanup_errors_never_hide_the_import_error`(2), `test_unpickable_import_warns_once_per_leftover` |

**판단**
1. 명시 `content_dir`/`work_dir`는 사용자가 준 경로라 편집기 바이너리 폴더가 아니라 CWD 기준으로 절대화한다(`abspath`). 전의 `normpath`만 한 상대 경로도 OS가 CWD 기준으로 열었으므로 가리키는 파일은 같다.
2. `zone_index`·`viewpoints`·`spike_runner._viewpoints`의 기본 경로는 이제 바이너리 폴더 기준이다(R67·F2와 같은 규칙). 편집기에서는 CWD가 바이너리 폴더라 전과 같은 파일이고, CWD가 다를 때만 달라진다(의도한 수정).
3. `_abs` 이름은 호출 지점 4곳을 바꾸지 않으려고 별칭으로 남겼다.
4. 정리는 `target` 자체는 지우지 않는다(이전 실행의 에셋이거나 `_ensure_path`가 이미 지운 것). 정리 중 예외(삭제·존재 확인 모두)는 경고 한 줄로 남기고 원래 오류를 가리지 않는다. by-product가 아닌 잔재는 `_delete_assets`의 `unexpected asset … left in place` 한 줄만 남긴다(중복 경고 없음).
5. `_delete_assets`가 지우지 못한 것을 `deleted` 줄로 적던 것(메시 스크래치 정리에도 쓰임)을 고쳤다. 지우지 못한 by-product는 줄이 없고, 호출한 쪽이 보고한다(텍스처 실패 정리는 위 WARNING, 메시는 뒤이은 `_import` 폴더 삭제). → R81-6: 경고하는 호출자는 `_discard_failed_import` 하나다. 메시(`_import_moved`)와 UDIM 타일(`_pack_udim_tiles`)은 뒤이은 폴더 삭제(`_import`·`Textures/_tiles`)가, 텍스처 제자리 임포트의 **성공 경로**(`_import_in_place`)는 같은 실행의 cleanup 단계(`_cleanup_folder`, 마지막 임포트 뒤)가 지운다(그 단계의 `zi.cleanup` 줄). 실패 경로는 그 실행이 cleanup 단계 전에 끝나므로 다음 실행의 cleanup 단계다. `_delete_assets` docstring을 이대로 고쳤다.

**게이트**: `ruff check`·`ruff format --check` 통과, pytest **1384 passed / 3 skipped**(main 1344 + 40), `check_repo.py` OK, `git diff --check` 깨끗. 새 가드는 main과 원격 브랜치 53개(worktree) 모두 OK. 뮤테이션: 1차 14/14, 검증 반영 뒤 9/9 잡힘(검증 에이전트가 찾은 생존 2개 M7 `keep=set()`·M16 예외 삼킴 제거 포함).

**적대 검증 1라운드(별도 에이전트, 읽기 전용) — (A) 0 · (B) 3 · (C) 7, 확정 결함 반영**

| # | 지적 | 등급 | 처리 |
|---|---|---|---|
| V1 | `_delete_assets`가 삭제 실패에도 `deleted` 줄을 적음; 다음 실행 sweep 테스트의 로그 단언이 1회차에서 이미 참 | B | 반환값 확인, 2회차 전에 로그 비움 + 1회차에 `deleted` 줄 없음 단언 |
| V5 | `keep={target}`·예외 삼킴 경로가 테스트 없음(뮤테이션 생존) | C | 이전 대상 유지·정리 예외 테스트 3개 |
| V6 | 정리의 존재 확인 루프가 try 밖이라 원래 오류를 가릴 수 있음 | C | 같은 try 안으로 |
| V7 | by-product가 아닌 잔재에 경고 2줄 | C | by-product만 `could not delete` 경고 |
| — | 경로 도우미 전후 동일성(상대·절대·`..`·공백·`C:/`·`C:\\`), `_without_rhi` 2381개 명령줄 동일, 순환 import 없음 | 확인 | — |

GASP 가드 쪽 지적(V2·V3·V4·V8·V9·V10)은 WP-19 "19a-2 후속" 절에 적었다.

**병합 시 반영(문안)**
- STATUS WP-06 행 비고 끝에 `· R69 (C) 후속(R69-6·8·11) PR #<번호> 병합, V-04c 카드 ⑤ 기대 문구 갱신`.
- ROADMAP zone_import 줄: 바꿀 것 없음(동작 범위 불변).
- "병합 기록 — 후속 V-04b F1~F3 #69"의 PC 카드 ⑤ `문구 (-nullrhi) R69-6` → `문구 (commandlet -run=pythonscript without -AllowCommandletRendering)`.

**병합**: [PR #81](https://github.com/wooklym/golmok/pull/81) → main(오케스트레이터 결정 D-019; 리뷰 [R81](https://github.com/wooklym/golmok/pull/81#issuecomment-5910698240) (A)·(B) 0). 위 "병합 시 반영(문안)"은 STATUS WP-06 행과 V-04c 카드 ⑤에 옮겼다. 남은 (C)는 다음 Claude 레인 push: R81-4 새 WARNING이 가리키는 런북 #8 행·§2 로그 목록에 설명 추가(지금은 #37에만), R81-6 `_delete_assets` 주석(호출자 3곳 중 2곳과 맞지 않음), R81-7 RHI가 있는데 크기 0인 경우 텍스처 줄 문구와 테스트 전용이 된 `_without_rhi()` 정리. → R81-4·6·7은 [PR #87](https://github.com/wooklym/golmok/pull/87)에서 해소.

## 결과 — Claude 레인 (C) 후속 2: R81-4·6·7 (2026-09-30, Opus 5.5 ultracode, 세션 `session_01Mt8twTiFwhqobsBxS1ddFN`, 브랜치 `claude/claude-lane-c-followups2`) — 🟡 코드 완료·PC 확인은 V-04c 카드에 합침
PR #81 병합 리뷰 R81의 WP-06 쪽 (C) 3건과 적대 검증 F3을 처리했다. 설계 변경은 없다.

| 항목 | 변경 | 테스트 |
|---|---|---|
| R81-4 런북 #8 | 런북 §2 로그 해석 목록에 `WARNING texture import failed; could not delete <path> - the next run's cleanup step removes it (runbook #8)` 한 줄(원인은 앞의 `ERROR`; 그것을 해결하고 재실행하면 cleanup 단계가 지움; 그래도 남으면 새 `cleanup: could not delete` WARNING과 수동 삭제). §12 #8 행 끝에 R69-11 설명 한 문장. WARNING의 `runbook #8`은 이제 설명이 있는 행을 가리킨다 | 문구는 코드·기존 테스트(`test_undeletable_leftover_…`)와 글자 단위 일치 |
| R81-6 `_delete_assets` 주석 | docstring을 실제 호출자에 맞춤: 실패한 delete는 `deleted` 줄도 반환값도 없다. 경고는 `_discard_failed_import`만 한다. `_import_moved`는 스크래치 폴더 삭제(`finally`), `_pack_udim_tiles`는 `Textures/_tiles` 삭제(팩 실패 시엔 다음 실행의 cleanup), `_import_in_place` 성공 경로는 **같은 실행**의 cleanup 단계(`_cleanup_folder`, 마지막 임포트 뒤)가, 뒤 단계가 실패하면 다음 실행의 cleanup 단계가 지운다. 위 판단 5에 성공 경로를 더함 | — (주석) |
| R81-7 크기 0 문구 | RHI가 있는데 크기에 0이 있으면 `how = "merged by importer (size WxH)"`(`HOW_SIZE_ZERO`, 예 `(size 0x0)`). RHI가 없으면 크기와 무관하게 종전 `(size unverifiable without RHI)`가 우선. WARNING 문구는 그대로. `_without_rhi()` docstring에 "Kept for tests only" 한 줄(제품 코드는 `_no_rhi_reason()`만 부름). 런북 §2 머리 주의·로그 목록·§12 #4 갱신. V-04c 카드는 ①이 `-nullrhi`, ②가 `(merged by importer)`라 바꿀 것 없음 | `test_zero_size_skips_udim_pack_fallback`에 `how`·텍스처 줄·"without RHI" 없음 단언, `test_zero_size_without_rhi_keeps_the_no_rhi_wording` |
| 검증 F3 cleanup 단계 | `_cleanup_folder`도 `delete_asset` 반환값을 본다(R69-11의 `_delete_assets`와 같은 규칙). 지우지 못하면 `deleted` 줄 대신 `WARNING cleanup: could not delete <path> (runbook #8)` | `test_cleanup_step_that_cannot_delete_warns_instead_of_a_deleted_line` |

**판단**
1. F3은 동작 변경이다(삭제 실패 시 WARNING 1줄 추가, 정상 경로는 동일). 새 런북 §2 줄과 R81-6 주석이 "cleanup 단계가 지운다"에 기대므로, 지우지 못했는데 `deleted`라고 적는 것을 그대로 둘 수 없었다. `_import_moved`의 스크래치 폴더 줄(삭제 전에 `zi.cleanup`을 적고 `delete_directory` 결과를 보지 않음)은 범위 밖으로 남긴다(후속 후보).
2. 크기 문구는 `0x0`만이 아니라 실제 `WxH`를 쓴다(한 변만 0인 경우도 사실대로).

**게이트·검증**: WP-19 "19a-2 후속 2" 절과 같은 게이트(pytest 1432 passed / 3 skipped)·적대 검증 라운드. 이 절 해당 지적: F3(B, 반영), F4(C, 주석의 "같은 실행"은 맞음; 뒤 단계 실패·팩 실패 시 다음 실행 — 주석에 반영), F5(C, `_without_rhi` 주석 "callers outside this module" 삭제), F10(C, 런북에 `size 512x0` 예 추가). 문자열 대조(런북 §2·§12 #4·#8, V-04c 카드 ①·②, 코드, 테스트) 일치 확인.

**병합 시 반영(문안)**
- STATUS WP-06 행 비고 끝에 `· R81 (C) 후속(R81-4·6·7, cleanup 삭제 실패 WARNING) PR #<번호> 병합`.
- ROADMAP zone_import 줄: 바꿀 것 없음.
- 위 "Claude 레인 (C) 후속 R69-6·8·11" 절의 **병합** 줄 끝에 `→ R81-4·6·7은 PR #<번호>에서 해소`.

**병합**: [PR #87](https://github.com/wooklym/golmok/pull/87) → main(오케스트레이터 결정 D-019; 리뷰 [R87](https://github.com/wooklym/golmok/pull/87#issuecomment-5915909161)). 위 "병합 시 반영(문안)"은 STATUS WP-06 행에 옮겼다. ROADMAP은 바꿀 것이 없다. PC 확인은 V-04c 카드에 합친다(크기 0 줄 `merged by importer (size WxH)`, cleanup 삭제 실패 `WARNING cleanup: could not delete <path> (runbook #8)`). 남은 (C)는 다음 Claude 레인 push: R87-3 `WxH`를 `(512, 0)`로도 시험(뮤테이션 `0x0` 고정·w/h 뒤바꿈 생존), R87-4 `get_command_line`이 없을 때(#40) 크기 0 경로의 주석·런북 149행 "RHI 있음" 단정, R87-5 새 cleanup WARNING을 런북 §12 #8 행에도 설명. → R87-3·4·5는 [PR #89](https://github.com/wooklym/golmok/pull/89)에서 해소.

## 결과 — Claude 레인 (C) 후속 3: R87-3·4·5 (2026-09-30, Opus 5.5 ultracode, 세션 `session_01LNapjfuvf1835C2KSwFpoV`, 브랜치 `claude/claude-lane-c-followups3`) — 🟡 코드 완료·PC 확인은 V-04c 카드에 합침
PR #87 병합 리뷰 R87의 WP-06 쪽 (C) 3건을 처리했다. 설계·동작 변경은 없다(주석·테스트·런북만).

| 항목 | 변경 | 테스트 |
|---|---|---|
| R87-3 `WxH` | 코드 변경 없음 | `test_zero_size_skips_udim_pack_fallback`을 크기 `(0, 0)`·`(512, 0)`로 parametrize, `how`·텍스처 줄·WARNING을 `f"{w}x{h}"`로 단언. 뮤테이션 4개(`how`·WARNING 각각 `0x0` 고정·w/h 뒤바꿈) 모두 잡힘 |
| R87-4 #40에서 크기 0 | `zone_import.py` 주석 `# R81-7: RHI present (or not detectable, #40); the size is not yet (R87-4)`. 런북 §2 "RHI가 있는데(또는 #40으로 판정 불가) 크기가 아직 0이라 건너뛴 것(R81-7·R87-4)". 동작은 그대로다: `get_command_line`이 없고 크기에 0이 있으면 크기 WARNING 한 줄만 나오고(#40 WARNING 없음), 팩도 하지 않는다 | `test_zero_size_without_get_command_line_names_the_size`(크기 `0x512`: WARNING 한 줄, `how` `(size 0x512)`, `make_udim` 호출 없음) |
| R87-5 런북 #8 | §12 #8 행 끝에 한 문장: cleanup 단계(`_cleanup_folder`)가 계획 밖 by-product(Texture2D·Material)를 지우지 못하면 텍스처 실패가 없어도 `zone_import: WARNING cleanup: could not delete <path> (runbook #8)`이 나온다. 기록한 뒤 에디터를 닫고 손으로 삭제한다 | 문구는 코드(`_cleanup_folder`, `zi.warn`)·기존 테스트 `test_cleanup_step_that_cannot_delete_…`와 글자 단위로 같다 |

**게이트·검증**: WP-19 "19a-2 후속 3" 절과 같은 게이트(pytest 1479 passed / 3 skipped)와 적대 검증 라운드를 거쳤다(한 PR). 이 절에 해당하는 결과는 다음과 같다.
- 문구 대조: 런북 §2·§12 #8·#40과 코드가 일치한다.
- 뮤테이션: `WxH` 4종과 "크기 0 경로에서도 #40 WARNING"이 모두 잡힌다.
- 검증 V4(C): §12 #40 행이 크기 0 경로를 빠뜨렸다. 그 행에 한 구절을 넣었다(이 경고는 팩 폴백을 탈 때만 나온다).

**병합 시 반영(문안)**
- STATUS WP-06 행 비고 끝에 `· R87 (C) 후속(R87-3·4·5, 테스트·주석·런북) PR #<번호> 병합`.
- ROADMAP zone_import 줄: 바꿀 것 없음. V-04c 카드: 바꿀 것 없음(기대 문구 불변).
- 위 "(C) 후속 2" 절의 **병합** 줄 끝에 `→ R87-3·4·5는 PR #<번호>에서 해소`.

**병합**: [PR #89](https://github.com/wooklym/golmok/pull/89) → main(오케스트레이터 결정 D-019; 리뷰 [R89](https://github.com/wooklym/golmok/pull/89#issuecomment-5917306038)). 위 "병합 시 반영(문안)"은 STATUS WP-06 행에 옮겼다. ROADMAP·V-04c 카드는 바꿀 것이 없다. 리뷰 (C) R89-4(런북 §12 #4 행의 크기 0 문구를 §2·#40 행과 같게 "(또는 #40으로 판정 불가)"·`WxH`로)는 이 병합 커밋에서 정정했다. 이 절 쪽에 남은 (C)는 없다.

## 결과 — V-04c PC 확인: 후속 V-04b F1~F3 [#69](https://github.com/wooklym/golmok/pull/69) (2026-10-04, Claude PC 세션 Opus 5.5, 워크트리 `adoring-newton-f2023a`, 브랜치 `pc/v04c-verify-wp06-f1f3`, main `8e7cfc5`) — 🟢 통과, 제품 코드 수정 없음
"병합 기록 — 후속 V-04b F1~F3"의 PC 카드 ①~⑤를 실행했다. 실측과 로그 발췌는 런북 §11 인계 9에, 행별 PC 확인은 §12 #4·#8·#31·#40에 있다.

| 카드 | 결과 | 실측 |
|---|---|---|
| ① 헤드리스 스모크(F1) | 통과 | `-nullrhi` `zi.run`은 assert 없이 38 s, exit 0으로 끝났다. `(-nullrhi)` WARNING 1줄, `(merged by importer (size unverifiable without RHI))`, `done … 8 assets, 1 warnings`. `size=256x256`(첫 블록 가설 확인, 태그 `Dimensions` `512x512`), #40 경고 없음. GUI에서 `T_facade`는 512×512·3색·숫자 정방향 |
| ② 새 에디터 재임포트(F3) | 통과 | 새 GUI 프로세스에서 §6 3단계와 `it.run`을 돌렸다. `done … 0 warnings`, `moved` 4줄, `size=512x512 (merged by importer)`, 텍스처 `deleted`·`renamed` 0, `ERROR replace`·`could not rename` 0, `MI_*` BaseColor 유지, `, vt enabled after import` 없음 |
| ③ 긴 경로(F2) | 통과 | junction 없이 `LongPathsEnabled=0`에서 §2·§4를 헤드리스와 GUI로 돌렸다. 로그 경로 줄 43줄에 `..` 0. 실내 충돌 GLB 사본은 193자(상대 형식이었다면 265자) |
| ④ GUI 폴백 PC | 해당 없음 | 이 PC는 GUI에서 importer가 병합한다. 폴백 팩은 PC 미확인 |
| ⑤ 커맨드릿 | 통과 | `-run=pythonscript`(`-nullrhi` 없음)에서 `(commandlet -run=pythonscript without -AllowCommandletRendering)` WARNING, `done … 1 warnings` |

관찰(제품 코드 무관, 런북 §11 인계 9): 검증 드라이버가 텍스처 에디터 창을 연 채 `quit_editor()`를 부르면 종료 중 `TextureEditor.dll` access violation이 난다(엔진). 실내 충돌의 Interchange 이름 축약 `#29` WARNING은 V-04 때와 같다. 잔존 검사 분기(F3 `ERROR replace`)와 R69-11·R87-5 WARNING은 발동하지 않아 PC에서 관찰되지 않았다.

## 병합 기록 — V-04c [#99](https://github.com/wooklym/golmok/pull/99) (2026-10-04, 오케스트레이터 세션)

**판정**: F1·F2·F3 통과, 선택 (b) 커맨드릿 통과, 선택 (a) 해당 없음 — WP-06 🟢 유지. Opus 읽기 전용 리뷰 [P04c](https://github.com/wooklym/golmok/pull/99#issuecomment-5979578856) 결과는 (A) 0 · (B) 2 · (C) 5다. PC 브랜치는 그대로 두고 클라우드 병합 브랜치 `claude/v04c-merge`(PC head `da89fb0` + main 병합 + `V-04c: 병합 시 반영 (Opus)`)로 병합했다.

- **정합 확인**: 인용된 로그 줄(`(merged by importer (size unverifiable without RHI))`, `(-nullrhi)`·커맨드릿 WARNING, `moved`·`renamed … (runbook #29)`, `interior_setup: done … ->` 절대 경로)이 main `zone_import.py`·`_pure.py`·`interior_setup.py`의 형식·분기와 맞는다. F2 경로 길이(193·183·265자)를 `zone_import.py` 규칙으로 다시 계산해 같았다. 빌드 기준 `8e7cfc5` 이후 `Content/Python`·`tools/` 변경이 없어 결과는 현재 main에 그대로 적용된다.
- **이름 대응**: 런북 §11 인계 9의 선택 (a)·(b)는 위 카드의 ④·⑤다 — (a)=④ GUI 폴백 PC, (b)=⑤ 커맨드릿 (P04c-6).
- **(B) P04c-1**: ROADMAP zone_import 줄을 "PC 확인 통과"로 바꿨다(GUI 폴백 팩만 PC 미확인).
- **(B) P04c-2 → Claude 레인 후속(V-05 전)**: 2라운드 ② Full Precision UV(LOD0 `use_full_precision_u_vs=True`)가 아직 `zone_import.py`에 없다(fake 필드만 있음). `StaticMeshEditorSubsystem` LOD 빌드 설정 경로에 `hasattr` 가드로 넣고, fake·테스트·런북 §12 새 행을 더한다. PC 확인은 V-05 S7에 합친다. STATUS V-05 행에 남은 착수 전 항목으로 적었다.
- **(C)**
  - P04c-3: 이 절을 덧붙이며 파일 끝 개행을 되살렸다.
  - P04c-4: STATUS M2·V-04 행에 V-04c를 적었다.
  - P04c-5: `quit_editor()` 전 에셋 에디터 닫기와 `Start-Process`의 `-ExecCmds` 따옴표를 `pc-setup.md` 공용 팁에 한 줄로 옮겼다. 저장소 코드는 바꾸지 않는다(저장소에서 `quit_editor()`를 부르는 두 곳은 에셋 에디터를 열지 않고, 생성 `.ps1`은 이미 한 인자로 넘긴다).
  - P04c-6: 런북 §12 #37에 V-04c 포인터를 달았다.
  - P04c-7: STATUS V-05 행에 C-01·C-04·EgoBlur 동의를 더했다.
- **관찰 처리**: TextureEditor 크래시는 PC 드라이버 쪽이라 저장소 조치 없음. 방화벽 알림 창은 V-11 몫이다. GUI 폴백 팩(§12 #4)과 잔존 검사 분기(`ERROR replace`)는 PC에서 발동하지 않아 미확인으로 남긴다.

## 결과 — Claude 후속: UDIM 병합 판정 `Dimensions` 태그 우선(헤드리스도 판정) (2026-10-09, Claude PC 세션 Opus 5.5, 워크트리 `infallible-noyce-1fb7a9`, 브랜치 `claude/infallible-noyce-1fb7a9`, [PR #122](https://github.com/wooklym/golmok/pull/122)) — 🟢 헤드리스·GUI PC 확인
배경은 다음과 같다. #69(V-04b F1) 뒤 `-nullrhi`·커맨드릿에서는 UDIM 팩 폴백을 건너뛰고 WARNING 1줄을 남겼다. `blueprint_get_size_x/y`가 병합된 UDIM에서도 첫 블록(256)을 주어 병합 여부를 가릴 수 없었기 때문이다. V-04 프로브(2026-09-26)와 V-04c(2026-10-04)는 같은 시점의 에셋 태그 `Dimensions`가 캔버스(`512x512`)임을 보였다. 이 후속은 그 태그를 먼저 읽어 헤드리스에서도 GUI와 같은 판정을 한다.

| 항목 | 변경 | 테스트 |
|---|---|---|
| `zone_import._texture_size` | `_dimensions_tag`(`EditorAssetLibrary.get_tag_values(<패키지 경로>)`를 `{str(k): str(v)}`로 읽고 `Dimensions` 파싱) → 없으면 `blueprint_get_size_x/y`. 둘 다 `hasattr` 가드. `_texture_size_and_source`가 출처(`tag`/`blueprint`)를 함께 준다. `get_tag_values` 예외는 `WARNING EditorAssetLibrary.get_tag_values failed (<예외>); texture sizes read from blueprint_get_size_x/y (runbook #42)` 호출당 1회(R69-7 규칙) 뒤 blueprint로 대체 | `test_nullrhi_reads_the_dimensions_tag`, `test_tag_reads_the_package_path`, `test_get_tag_values_failure_warns_once_and_falls_back`, `test_tag_without_blueprint_size_still_decides` |
| `_import_texture` UDIM 분기 | 크기가 태그에서 오면 RHI 판정을 쓰지 않는다(`reason = ""`). 그래서 `-nullrhi`에서도 병합이면 `(merged by importer)`, 미병합이면 팩 폴백이다. #40 WARNING도 없다. 태그가 없을 때만 종전 규칙(`-nullrhi`·크기 0이면 팩 생략 + `#4` WARNING, #40)이다. 로그 문구·`how`·`import_result.json` 스키마는 그대로다 | `test_nullrhi_packs_unmerged_tiles_by_the_tag`, `test_nullrhi_without_the_tag_skips_udim_pack_fallback`(태그 없음·API 없음·형식 오류·`0x512` 4종), `test_no_size_from_either_source_warns_and_skips`(RHI 유무 2종), `test_tag_beats_a_placeholder_blueprint_size`(GUI 32×32), 기존 폴백 테스트는 `dimensions_tag=False`로 의미 유지 |
| `_pure.parse_dimensions_tag` | `"WxH"` 앞의 두 수만 읽는다(`512x512x6`·`512x512 (VT)` 허용, 앞 접두사·0·다른 형식은 `None`) | `test_parse_dimensions_tag`(18) |
| fake | `FakeEditorAssetLibrary.get_tag_values`는 Texture2D에 `HasAlphaChannel`과 `Dimensions` = 캔버스를 준다(`nullrhi`와 무관). 키는 `_TagName`이다(str과 해시가 달라 str 조회가 빗나간다 — 실제 `unreal.Map`보다 엄격한 dict 사본). 새 노브 `dimensions_tag=True`를 추가했다. `nullrhi`의 blueprint 첫 블록 동작은 그대로다 | `test_texture_dimensions_tag_and_nullrhi_block_size` |
| 런북 | §2 머리 주의(태그 우선 → 헤드리스 `0 warnings`), §2 실패 목록(태그 문구·새 WARNING), §4 긴 경로 #29 WARNING, §11 인계 10(PC 확인), §12 #4·#29·#40 갱신, 새 행 #42 | 문구는 코드·테스트와 글자 단위로 같다 |
| 카드 | V-04c 카드 ① 기대(헤드리스 `size=512x512 … (merged by importer)`·`0 warnings`), ③ 긴 경로의 `interior_setup` WARNING 1줄(#29), ⑤ 커맨드릿도 태그 판정, ⑥ GUI 태그 비교(2026-10-09 확인). `pc-verify-v17.md` §3에 헤드리스 기대 변경 한 줄 | — |

**판단**
1. 태그는 엔진 소스상 RHI와 무관하다(5.8.3 `UTexture2D::GetAssetRegistryTags` → `GetImportedSize()` → 쿠킹 전 `Source.GetLogicalSize()` = 블록 격자 × 최대 블록 크기). `Blueprint_GetSizeX`는 플랫폼 데이터가 없으면 `Source.SizeX >> LODBias`(첫 블록)다. 그래서 태그 판정에는 RHI 판정을 섞지 않는다. 태그 값은 `UEditorAssetSubsystem::GetTagValues` → `GetAssetByObjectPath`가 로드된 객체에서 그 자리에서 모으므로, 제자리 재임포트 직후도 현재 값이다(디스크의 오래된 값이 아님).
2. 태그가 다른 형식이거나 0이면 "태그 없음"으로 보고 종전 규칙으로 간다. 팩은 엔진 assert 위험이 있으므로, 믿을 수 없는 크기로는 팩하지 않는다는 #69 원칙을 지킨다.
3. `AssetRegistryHelpers.create_asset_data(tex).get_tag_value("Dimensions")`는 같은 값이라(헤드리스·GUI 모두) 두 번째 경로로 넣지 않았다. 불확실 호출은 하나(#42)로 둔다.
4. 크기 출처는 로그·`import_result.json`에 남기지 않는다. 기대 로그 줄이 GUI와 헤드리스에서 같아지는 것이 목적이고, 출처는 WARNING 유무로 드러난다(태그를 못 읽은 헤드리스만 #4 WARNING).
5. 단일 텍스처 분기(엔진이 `[._]####` 이름을 UDIM으로 넣은 경우, #38)도 태그 크기를 쓰게 된다. 헤드리스에서도 `512x256 != 256x256` 경고가 나오게 된 것은 의도한 개선이다.
6. 사용자 설명의 "키가 `unreal.Name`이라 str 조회가 빗나간다"는 5.8.3 GUI 측정에서 `unreal.Map`에는 해당하지 않았다(`in`·`get`·`[]` 모두 성공). 다만 `hash(Name) != hash(str)`라 dict 사본에는 해당한다. 코드는 두 경우 모두 맞게 읽고, fake는 더 엄격한 쪽을 흉내 낸다.

**PC 확인(이 세션)**: 런북 §11 인계 10. 헤드리스 `-nullrhi`는 `size=512x512 vt=on (merged by importer)`·`done … 8 assets, 0 warnings`이고, 태그 `512x512`·blueprint 256×256이었다. GUI는 시작 직후 태그 `512x512`·blueprint 32×32였고, 재임포트 뒤 둘 다 512×512였다. 긴 경로 `it.run`은 #29 WARNING 1줄로 끝났다. `-run=pythonscript` 커맨드릿도 `size=512x512 … (merged by importer)`이다. 다만 커맨드릿에는 #41 `StaticMeshEditorSubsystem` LOD 빌드 설정 API가 없어 `1 warnings`이고, 이는 이 PR과 무관하다(런북 §12 #41 관찰). 빌드 성공(306 s, C++ 무수정).

**게이트**: `ruff check`·`ruff format --check` 통과, pytest **1565 passed / 274 skipped**(이 PC — g++ 없음 등으로 C++ 교차 테스트 skip; `PYTHONUTF8=1`), `check_repo.py` OK, `git diff --check` 깨끗. 열린 브랜치와 파일 겹침 없음.

**적대 검증(별도 에이전트, 읽기 전용 + scratch 뮤테이션) — (A) 0 · (B) 2 · (C) 6, 반영**
- 확인: 병합된 multi-block 텍스처가 `make_udim_virtual_texture_from_texture2_ds`로 갈 경로 없음(태그는 살아 있는 객체에서 모으고, `len(tiles) > 1`인 병합 캔버스는 적어도 한 변이 타일의 2배라 태그 == 타일일 수 없다; 엔진 `check(GetNumBlocks()==1)`은 입력 타일에만 걸린다). 태그 경로는 RHI 판정·#40 경고를 쓰지 않고, 최종 로그·`detail.size`도 태그다. `skipped: exists`·`tiles == [1001]`·`interior_setup`(호출마다 `_warned_once` 초기화)은 HEAD와 같다. GUI 경로는 32×32 임시 크기가 더는 가짜 "merged"나 #38 경고를 내지 않는다는 점만 다르다. 런북 행 번호 1~42 연속, 코드의 #4·#29·#38·#40·#41·#42와 일치.
- 뮤테이션 32개 중 28개가 잡혔다. 생존 3개는 테스트로 막았다: `except Exception` → `RuntimeError`(→ `get_tag_values`가 `None`을 주는 경우), 중복 경고 키 공유(→ 태그 실패 + #40 같이), 최소 변 2(→ `1x1`). 나머지 1개(`str(v)` 제거)는 동치다.
- (B) 런북 §2 팩 줄 `size=256x256 … (packed from 3 tiles)` → `size=512x512`(태그). 이 문서에 결과 절·§3-2 설계 메모·fake 목록 갱신. → 반영.
- (C) 런북 #4의 `>> LODBias`를 쿠킹 LOD 바이어스(`CalculateLODBias`)로 정정. 카드 ⑤ 커맨드릿 기대는 측정해서 확인. fake docstring 줄바꿈 정리. → 반영. 생성 에셋(`Maps/L_ZoneTagProbe`·`Materials/*`)은 gitignore 밖이라 커밋하지 않았다.
- (C) 남김(후속 후보): `zone_import.py`의 `_without_rhi`·`_pack_udim_tiles` docstring "병합된 텍스처를 다시 팩하면 에디터가 끝난다"는 엔진상 multi-block **입력**만 assert이므로 부정확하다(이 PR 전부터의 문구). fake `_reported_size`는 `nullrhi`에서 한 블록이 (1,0)에 놓인 단일 텍스처에 캔버스를 주지만 실제는 `Source.SizeX`(256)다(태그가 가리므로 영향 없음).

**병합 시 반영(문안)**
- STATUS WP-06 행 비고 끝에 `· 태그 우선 PR #122 병합(헤드리스 UDIM 판정 Dimensions 태그, PC 헤드리스·GUI·커맨드릿 확인 2026-10-09)`. V-05 행: 바꿀 것 없음.
- ROADMAP zone_import 줄의 "헤드리스 `-nullrhi` `zi.run` assert 없음" 뒤에 `; 헤드리스 UDIM 판정은 PR #122부터 Dimensions 태그(2026-10-09 PC 확인)`.
- DECISIONS: 없음(구현 수정, 설계·스택 변경 아님).

**병합**: [PR #122](https://github.com/wooklym/golmok/pull/122) → main(오케스트레이터 결정 D-019; 리뷰 [R122](https://github.com/wooklym/golmok/pull/122#issuecomment-6065848475) (A) 0 · (B) 1 · (C) 6). 위 문안은 STATUS WP-06 행·ROADMAP zone_import 줄에 옮겼다. ROADMAP은 리뷰 제안대로 "긴 worktree 경로" 뒤에 넣고, "GUI 폴백 팩만 PC 미확인"을 "폴백 팩(GUI·헤드리스)만 PC 미확인"으로 바꿨다. R122-B1(태그 판정 뒤 헤드리스 팩 `_pack_udim_tiles`는 PC 미실행)은 이 병합 커밋에서 런북 §2 머리 주의·§12 #4·#42에 반영했다. (C) R122-C1~C6(`parse_dimensions_tag` 초장 자릿수, fake `_TagName` docstring, 테스트 주석, 헤드리스 #38 테스트, §2 커맨드릿 `1 warnings`(#41), 위 "열린 브랜치와 파일 겹침 없음" — #121도 `pc-verify-v17.md`를 고침, 줄 충돌 없음)는 후속 후보로 남긴다.
