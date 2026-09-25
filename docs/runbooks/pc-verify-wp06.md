# PC 검증 런북 — WP-06 UE Python 에디터 자동화 2차: zone_import·interior_setup·spike_runner (V-04)

대상: PC Claude 세션(또는 사용자). 전제: V-03 통과(`runbooks/pc-verify-wp04.md` §1~§3, `runbooks/pc-verify-wp05.md` §1~§8 — 빌드 OK, `L_ZoneTest` 존재, `golmok.tod/path/screenshot` 콘솔 동작 확인).
소요: 합성 zone 생성 1분 + 임포트·실내 20분 + PIE 걷기 15분 + spike_runner 리허설 30분 + -game 성능 20분. 결과는 이 문서 하단 §11 "결과 기록"과 `docs/plan/STATUS.md`(V-04 행, WP-06 행)에 적는다.

클라우드 세션은 Unreal 에디터를 실행할 수 없었다. 모든 `unreal.*` 호출은 "🟡 PC 검증 대기"다. **에디터 Python이 예외를 내거나 기대 로그와 다르면 §12의 표(번호 #1~#30)를 보고 고친 뒤 커밋**한다(`WP-06: PC fix …`). 설계 의도를 바꾸는 수정이면 `docs/plan/WP-06-ue-python-automation.md` "결과"에 한 줄 적는다(DEVELOPMENT-PLAN §4 핸드오프 규칙: 검증 결과는 이 파일 하단, API 수정·설계 변경은 커밋 메시지와 STATUS에).

규칙:
- 이 문서의 기대 로그는 **코드의 `golmok/_pure.py` `LOG` 표에서 옮겨 적은 것**이다(`tools/tests/test_ue_python_pure.py::test_log_formats_are_quoted_in_runbook`이 양방향 드리프트를 잡는다). 로그 문자열을 바꾸면 `_pure.LOG`와 이 문서를 **함께** 고친다. 기대 로그는 항상 ```` ``` ```` 블록 안에 둔다.
- 기대 수치는 생성기가 쓰는 `<out>\zones\<zone_id>\v1\expected.json`이 정본이다(설계 §4-4와 같다; `tools/tests/test_make_synthetic_zone.py`가 생성 파일과 대조한다). 로그의 `…`는 PC에서만 정해지는 실측값(임포터 매핑, 경로, ms)이다.
- `<Project>` = `unreal\Golmok`, `<Saved>` = `<Project>\Saved`. 에디터 Python은 Output Log 창의 Python 입력줄(또는 `py` 콘솔 명령)로 실행한다.

## 0. 대상 파일
| 파일 | 상태 | 내용 |
|---|---|---|
| `Content/Python/golmok/_pure.py` | 신규 | unreal 비의존 순수 함수·상수·`LOG`(경로 규약·UDIM·MTL·임포트 계획·bbox·OBJ/GLB 사전변환·로그 포맷·경로 JSON·명령줄·PowerShell·컨택트 시트·리포트). 클라우드 테스트 완료 |
| `Content/Python/golmok/zone_import.py` | 신규 | `run(zone_dir, version=None, level=None, geo_origin=None, save=True, remeasure=False, reimport_textures=True)`, `import_assets(plan, work_dir, …)`, `ZoneImportError(step, message)` — OBJ 청크·UDIM 텍스처·`M_ZoneScan`/`MI_*`·충돌 GLB 임포트, `manifest.json`·`blockers.json` 복사, GeoOrigin, `AGolmokZone.rebuild_in_editor()` |
| `Content/Python/golmok/interior_setup.py` | 신규 | `run(zone_dir, version=None, level=None, save=True, register=False, remeasure=False, reimport_textures=True)` — 포털 왕복 검사(순수) → 에셋(zone_import 재사용) → 서브레벨 `L_<zone_id>`(PointLight 1개, 태그 `GolmokInteriorSetup`) → 부모 zone 재빌드 |
| `Content/Python/golmok/spike_runner.py` | 신규 | `prepare`, `configure_pie_window`, `apply_layers`, `save_layer_levels`, `capture_all(mode="pie"\|"editor")`, `perf_all`, `game_scripts`, `contact_sheet`, `report_template` — PIE 상태기계 무인 캡처, `-game` CSV 스크립트 |
| `Content/Python/golmok/materials.py` | 수정 | `build_zone_scan_material(default_texture, vt=True, overwrite=False)`, `zone_scan_instance(texture, parent, path)` (`M_ZoneScan`·`M_ZoneScan_NoVT`) |
| `Content/Python/golmok/basemap_import.py` | 수정 | `_set_geo_origin(origin)` + `run()` 한 줄(베이스맵 manifest origin → `AGolmokGeoOrigin`), docstring `--exclude` |
| `Content/Python/golmok/synthetic_zone.py` | 수정 | `_spawn_interior_sublevel(..., specs=None, delete_tag=None, on_removed=None)`, `_spawn_sublevel_actor`가 `spec["tags"]` 적용, `register_interior_sublevel(zone_id=…, version=…)`; `run()` 시그니처 불변 |
| `Content/Python/golmok/viewpoints.py` | 수정 | `capture(tag, names=None, presets=None, game_view=True, on_done=None)` |
| `tools/scripts/make_synthetic_zone.py` | 신규 | 합성 zone 생성기(RealityScan 흉내 원본 + 실제 `golmok-mesh chunk/collision/blockers` 파이프라인 + `expected.json`) |
| `tools/tests/fake_unreal.py`, `tools/tests/test_ue_python_{pure,zone_import,interior_setup,spike_runner}.py`, `tools/tests/test_make_synthetic_zone.py`, `tools/tests/fixtures/ue/chunk_manifest_min.json` | 신규 | 클라우드 테스트(가짜 `unreal`) |
| `docs/runbooks/pc-spike.md` | 신규 | 스파이크 1.1 전체 절차(이 런북 §1~§8 통과가 전제) |

전제 확인:
- [ ] `git pull` 후 `cd tools; .\.venv\Scripts\Activate.ps1; pip install -e ".[zone,mesh,dev]"; pytest -q` 초록(`test_ue_python_*.py`·`test_make_synthetic_zone.py` 포함). 여기서 빨간 것은 PC 문제가 아니라 코드 문제 — 클라우드 세션에 돌려보낸다.
- [ ] 에디터 `.\tools\ue\open-editor.ps1` → `L_ZoneTest`(`/Game/Golmok/Maps/L_ZoneTest`)를 연다. WP-04/05 런북이 만든 `z_synthetic_001` 에셋·액터는 그대로 두어도 된다(zone id가 다르다).
- [ ] 디스크 여유: OBJ 사본(`<Saved>\Golmok\zone_import\…`)은 원본 텍스트 크기와 같다(합성 zone은 수백 KB; 실 zone은 원본의 2배 확보).
- [ ] 작업 폴더(git 밖): `D:\golmok_synth`(없으면 생성기가 만든다).

## 1. 합성 zone 생성 (PowerShell, tools venv)
```powershell
cd <repo>
python tools\scripts\make_synthetic_zone.py --out D:\golmok_synth --interior
golmok-zone validate --check-files --strict D:\golmok_synth\zones\z_synthetic_scan_001\v1\manifest.json
golmok-zone validate --check-files --strict D:\golmok_synth\zones\z_synthetic_scan_001_room\v1\manifest.json
```
기대 stdout(ASCII만; `--interior`면 `wrote` 27줄):
```
wrote recon/z_synthetic_scan_001/scan.obj
wrote recon/z_synthetic_scan_001/scan.mtl
wrote recon/z_synthetic_scan_001/tex/ground.png
wrote recon/z_synthetic_scan_001/tex/facade.1001.png
wrote recon/z_synthetic_scan_001/tex/facade.1002.png
wrote recon/z_synthetic_scan_001/tex/facade.1011.png
wrote zones/z_synthetic_scan_001/v1/manifest.json
…
wrote zones/z_synthetic_scan_001_room/v1/expected.json
next: import golmok.zone_import as zi; zi.run(r"D:\golmok_synth\zones\z_synthetic_scan_001", level="/Game/Golmok/Maps/L_ZoneTest", geo_origin="area")
```
`golmok-zone validate`는 두 manifest 모두 `OK`(경고 0).
- [ ] 파일 목록이 정확히 다음과 같다(대소문자 포함): `recon\z_synthetic_scan_001\{scan.obj, scan.mtl, tex\ground.png, tex\facade.1001.png, tex\facade.1002.png, tex\facade.1011.png}`, `zones\z_synthetic_scan_001\v1\{manifest.json, expected.json, blockers.json, blockers.glb, collision.glb, collision\c_e000_n000.glb, collision\c_w001_n000.glb, visual\c_e000_n000.obj, visual\c_w001_n000.obj, visual\scan.mtl, visual\chunk_manifest.json}`, `recon\z_synthetic_scan_001_room\{room.obj, room.mtl, tex\room.1001.png}`, `zones\z_synthetic_scan_001_room\v1\{manifest.json, expected.json, collision.glb, collision\c_e000_n000.glb, visual\c_e000_n000.obj, visual\room.mtl, visual\chunk_manifest.json}`.
- [ ] 탐색기에서 PNG 4장(+1): `facade.1001.png` **빨강** 바탕, 흰 숫자 `1001`, 좌상단 흰 사각형 **1개**; `facade.1002.png` **초록**, `1002`, 사각형 **2개**; `facade.1011.png` **파랑**, `1011`, 사각형 **3개**; `ground.png` **회색**, 숫자 없음; `room.1001.png` **노랑**, `1001`, 사각형 1개. 모두 256×256, 2 px 검은 테두리.
- [ ] `visual\scan.mtl`의 `map_Kd`가 버전 폴더 **밖**을 가리킨다: `map_Kd ../../../../recon/z_synthetic_scan_001/tex/ground.png`, `map_Kd -bm 1 ../../../../recon/z_synthetic_scan_001/tex/facade.<UDIM>.png`. `visual\chunk_manifest.json`의 `missing`은 `{"mtl": [], "textures": []}`, `total_tris` 132, 청크 `c_w001_n000`(66 tri, tiles [1001, 1002])·`c_e000_n000`(66 tri, tiles [1001, 1011]).
- [ ] `expected.json`(실외)의 값이 아래 §2·§3 표와 같다(생성기가 계산한 정본. 다르면 이 문서가 낡은 것 — 문서를 고친다).

실패 시: pytest가 초록인데 여기서 실패하면 환경 문제(권한·경로·비ASCII 콘솔). 이미 폴더가 있으면 `exists; use --force`(rc 2) → `--force`(네 출력 폴더를 지우고 다시 만든다). `ERROR install tools with pip install -e ".[zone,mesh]"` → extras 설치. 검증 실패(rc 1)는 stderr의 메시지대로.

## 2. `zone_import.run` (에디터 Python, `L_ZoneTest`)
```python
import golmok.zone_import as zi
r = zi.run(r"D:\golmok_synth\zones\z_synthetic_scan_001", level="/Game/Golmok/Maps/L_ZoneTest", geo_origin="area")
```
기대 로그(값은 `expected.json`; `…` = 매핑 실측. 계획 단계는 에디터 호출 0회이므로 첫 줄이 안 나오면 파일 문제다):
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
LogGolmok: Zone z_synthetic_scan_001: chunk c_e000_n000 bbox center -> level (…) cm          (c_w001_n000도 한 줄)
LogGolmok: Zone z_synthetic_scan_001: blocker glass_1 (glass) rel (-800, -500, 150) cm yaw 90.0 extent (5, 150, 125) -> level (16870.59, -22697.99, 1149.37)
LogGolmok: Zone z_synthetic_scan_001: portal door_1 -> z_synthetic_scan_001_room rel (500, -700, 0) cm yaw -90.0 radius 100 cm -> level (18170.58, -22898.01, 999.33) [entry]
LogGolmok: Zone z_synthetic_scan_001 v1 loaded in x ms: chunks 2/2 (0 wire boxes), collision 2/2, blockers 1/1, portals 1 (WP-05)
zone_import: zone Zone_z_synthetic_scan_001 rebuilt
zone_import: done z_synthetic_scan_001 v1: 8 assets, 0 warnings -> <Project>\Saved\Golmok\zone_import\z_synthetic_scan_001\v1\import_result.json
  - chunk /Game/Golmok/Zones/z_synthetic_scan_001/v1/SM_c_e000_n000: ok (…)
  - …
```
표기 차이는 §11 표에 실측을 적는다: 임포터가 텍스처·머티리얼 부산물을 만들면 그 사이에 `zone_import: deleted importer-created asset <path>` 줄이 끼어든다(무해, 개수 기록); `size=`가 `256x256`처럼 다르면 UDIM 병합 판정이 폴백을 탄 것(§12 #4, 아래 실패 항목); `, vt enabled after import`가 붙는지 여부는 임포터 기본값(기록만); 첫 실행 뒤에는 `cache hit`이 되고 `route`·`mapping` 세 줄이 사라진다(`zi.run(..., remeasure=True)`로 다시 측정).
- [ ] 콘텐츠 브라우저 `/Game/Golmok/Zones/z_synthetic_scan_001/v1/`: `SM_c_e000_n000`, `SM_c_w001_n000`, `SM_z_synthetic_scan_001_collision_c_e000_n000`, `SM_z_synthetic_scan_001_collision_c_w001_n000`, `Textures/T_facade`, `Textures/T_ground`, `Materials/MI_facade`, `Materials/MI_ground` — **그 외 없음**(`_probe` 폴더·`Textures/_tiles`·임포터가 만든 `scan`·`facade` 머티리얼/텍스처가 남아 있으면 §12 #1·#6). `/Game/Golmok/Materials/M_ZoneScan` 존재, `M_ZoneScan_NoVT` **없음**.
- [ ] `T_facade` 더블클릭: Virtual Texture Streaming ✔, sRGB ✔, 크기 512×512(UDIM 2×2 캔버스; 정보 패널에 `UDIM`/블록 표시), 미리보기 빨강(좌하 1001)·초록(우하 1002)·파랑(좌상 1011), 숫자가 **바로 읽힌다**(거울·뒤집힘이면 §12 #4에 실제 방향을 적는다 — UE는 UDIM을 세로로 뒤집고 메시 UV도 함께 바꾼다). `T_ground` 256×256, VT ✔, sRGB ✔.
- [ ] `SM_c_e000_n000` 더블클릭: Nanite ✔(Nanite Settings › Enabled), 머티리얼 슬롯 `facade`→`MI_facade`, `ground`→`MI_ground`(슬롯 이름이 `usemtl`과 다르면 §12 #7), Approx Size ≈ 1500×1500×600 cm; `SM_c_w001_n000` ≈ 1500×1500×530 cm. `SM_z_synthetic_scan_001_collision_c_e000_n000`: Collision Complexity "Use Complex Collision As Simple", Nanite ✖, 머티리얼 기본.
- [ ] `MI_facade` 더블클릭: Parent `M_ZoneScan`, 텍스처 파라미터 `BaseColor` = `T_facade`. `M_ZoneScan`: BaseColor 샘플러 Sampler Type **Virtual Color**, Roughness 0.8 상수, Used with Nanite ✔, 컴파일 오류 없음(오류면 §12 #10).
- [ ] 아웃라이너 `Golmok/GeoOrigin`(Latitude 37.56, Longitude 126.923, HeightEllipsoidal 40), `Golmok/Zones/Zone_z_synthetic_scan_001` 위치 (17670.59, −22198.00, 999.37) cm, State = Loaded, LastError 비어 있음, MissingAssetCount 0, Manifest.Portals 1개(door_1). 런타임 컴포넌트(청크 2·충돌 2·`Blocker_glass_1`)는 위 `LogGolmok` 줄로 대조한다.
- [ ] 뷰포트(GeoOrigin에서 동 176.7 m·남 222 m·위 10 m): 회색 경사 지면 30×15 m(서쪽 −0.3 m ~ 동쪽 +0.3 m), 동쪽에 **빨간 벽**(x 1..9 m, 높이 6 m, 문 구멍 x 4..6 m·높이 2.2 m)과 **파란 블록**(x 10..13 m, 2 m 높이), 서쪽에 **초록 벽**(x −11..−5 m, 높이 5 m, 창 구멍 x −9.5..−6.5 m·z 0.25..2.75 m)과 그 창에 시안 와이어 박스(`Blocker_glass_1`, 3×2.5 m). 벽마다 타일 숫자 `1001`/`1002`/`1011`이 보이고 흰 사각형 개수가 1/2/3.
- [ ] `<Saved>\Golmok\zone_import\z_synthetic_scan_001\v1\import_result.json`: `route`, `obj_mapping`·`glb_mapping`의 `scale`·`m`·`err`, `assets` 8개 모두 `"ok": true`, `warnings: []`. `route`와 두 매핑을 §11 표에 옮긴다. 같은 폴더 `visual\SM_c_e000_n000.obj`·`visual\scan.mtl`(절대경로 `map_Kd`)·`collision\*.glb`가 사본이다(에셋의 Source File은 이 사본 — Reimport 대신 `zi.run` 재실행이 정본 워크플로).
- [ ] `<Project>\Content\Golmok\Zones\z_synthetic_scan_001\v1\`에 `manifest.json`·`blockers.json` **두 파일만**(OBJ·PNG·GLB·`chunk_manifest.json` 없음).

수치 대조(`expected.json`; 좌표는 level UE cm, area 원점 37.56/126.923/40):
| 항목 | 기대값 | 어디서 |
|---|---|---|
| zone root 위치 / Yaw | (17670.59, −22198.00, 999.37) / 0.0 (로그 −0.0012°) | `root:` 로그, 액터 디테일 |
| 청크 `c_e000_n000` UE bounds(zone-local) | min (0, −1500, 0) max (1500, 0, 600) | 에셋 Approx Size, `zi.chunk` bounds ok |
| 청크 `c_w001_n000` UE bounds | min (−1500, −1500, −30) max (0, 0, 500) | 같음 |
| blocker `glass_1` | 상대 (−800, −500, 150), extent (5, 150, 125), 레벨 (16870.59, −22697.99, 1149.37) | `blocker glass_1` 로그 |
| 포털 `door_1` | 상대 (500, −700, 0), Yaw −90, 반경 100 cm, 레벨 (18170.58, −22898.01, 999.33) | `portal door_1` 로그 |
| PlayerStart(§3) | (17670.59, −22398.00, 1149.36) | `expected.json.player_start_ue_cm` |

실패 시:
- `zone_import: ERROR plan: …` — 메시지의 접두대로(`chunk_manifest.json missing`·`texture missing`·`bbox mismatch` …): 생성기 출력이 깨진 것 → §1 `--force` 재생성. 에디터는 건드리지 않았으므로 바로 재실행.
- `zone_import: ERROR probe: OBJ import failed on routes fbx, interchange, legacy_flag: …` → §12 #1. Output Log에서 세 route의 임포터 오류를 §11에 옮긴다. `probe: obj importer mapping fit failed (error x cm)` → §12 #2(임포터가 정점을 옮기거나 합침).
- `zone_import: ERROR chunk c_e000_n000: imported bounds … != expected … (error x cm); importer mapping may have changed: run with remeasure=True (runbook #2)` → `zi.run(..., remeasure=True)`; 그래도 실패면 §12 #2·#28(`import_result.json`의 매핑을 §11에).
- 텍스처 줄이 `vt=off` → §12 #5(`M_ZoneScan_NoVT`가 생기고 그 MI의 parent가 NoVT — 렌더는 되지만 기록); `tiles=[1001, 1002, 1011] size=256x256 … (packed from 3 tiles)` → 임포터가 UDIM을 안 묶어 `UDIMTextureFunctionLibrary` 폴백을 탄 것(정상 동작, §12 #4에 기록); `(tile 1001 only (WARNING))` + `zone_import: WARNING texture facade: UDIM tiles not merged; using tile 1001 only (runbook #4)` → 폴백도 없음, 빨간 타일만 보임 → §12 #4.
- `zone_import: WARNING chunk c_e000_n000: slot 'xxx' left with the importer default (runbook #7)` → 슬롯 이름이 `usemtl`도 아님 → §12 #7(`dir(mesh.get_editor_property("static_materials")[0])`로 이름 확인).
- `zone_import: WARNING unexpected asset … left in place` → 임포터가 만든 정체불명 에셋. 종류를 §11에 적고 손으로 삭제.
- 뷰포트에 벽이 안 보이고 `LogGolmok … chunks 0/2` → `MissingAssetCount`; 에셋 이름이 `SM_c_e000_n000`과 다르게 임포트됐다(§12 #6·#29 rename 경로).

## 3. PIE 걷기 (합성 실외)
PlayerStart가 `expected.json.player_start_ue_cm` = (17670.59, −22398.00, 1149.36) cm(zone-local (0, 2, 0) m, 지면 위)에 있는지 확인하고(다르면 옮긴다) PIE. 콘솔(`)에서 `golmok.zone.list` → `z_synthetic_scan_001  v1  prio 10  loaded  dist 0.0 m`(실내 `z_synthetic_scan_001_room`은 §4 전이라 목록에 없다).
- [ ] 북서쪽 **초록 벽**(x −11..−5 m, y 5 m)으로: 창 구멍(x −9.5..−6.5 m, z 0.25..2.75 m)을 통해 너머가 보이지만 **보이지 않는 유리에 막힌다**(`Blocker_glass_1`); 창 옆 벽 조각에도 막힌다. `show collision`으로 시안 박스 확인 가능.
- [ ] 동쪽 **빨간 벽**(x 1..9 m, y 7 m): 문 구멍(x 4..6 m, 높이 2.2 m)은 **통과**, 나머지는 막힘. 문 앞에서 Warning `Portal door_1: no AGolmokZone 'z_synthetic_scan_001_room' in this level; sublevel only`·`LevelStreaming: sublevel package missing` — §4 전에는 정상(무해).
- [ ] **파란 블록**(x 10..13 m, y 2..4 m, 2 m 높이): 올라가지 못하고 막힌다(계단 높이 초과).
- [ ] 경사 지면(서 −0.3 m → 동 +0.3 m)을 30 m 걷는 동안 지면을 뚫지 않는다. 지면 끝(y 0·15 m, x ±15 m)에서 떨어지면 `Zone_Ground`(WP-04가 만든 400 m 지면)로 내려간다.
- [ ] HUD(F1) `pos` 줄이 zone-local (0, 2) m 근처에서 **ENU ≈ (176.7, 224.0, 10.9~11.2)**.
- [ ] PIE 종료 시 에러·ensure 없음.

실패 시: 지면을 뚫으면 충돌 에셋의 Collision Complexity 확인(§2 체크·§12 #9); 유리를 지나가면 `Content\Golmok\Zones\z_synthetic_scan_001\v1\blockers.json` 복사 여부와 `Blocker_glass_1` 컴포넌트 확인; 문이 막히면 청크 임포트가 문 구멍 없는 다른 파일을 읽은 것(사본 폴더 확인).

## 4. `interior_setup.run` (에디터 Python, `L_ZoneTest`)
```python
import golmok.interior_setup as it
r = it.run(r"D:\golmok_synth\zones\z_synthetic_scan_001_room", level="/Game/Golmok/Maps/L_ZoneTest")
```
기대 로그(①~④ 포털 검사·계획까지는 에디터 호출 0회):
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
LogGolmok: Zone z_synthetic_scan_001_room: portal door_out -> z_synthetic_scan_001 rel (400, 20, 0) cm yaw 90.0 radius 100 cm -> level (18170.58, -22898.01, 999.33) [marker]
LogGolmok: Zone z_synthetic_scan_001_room v1 loaded in x ms: chunks 1/1 (0 wire boxes), collision 1/1, blockers 0/0, portals 1 (WP-05)
LogGolmok: Zone z_synthetic_scan_001_room v1 unloaded
interior_setup: sublevel /Game/Golmok/Zones/z_synthetic_scan_001_room/v1/L_z_synthetic_scan_001_room actors=['Interior_Light_z_synthetic_scan_001_room'] (level coordinates)
LogGolmok: Zone z_synthetic_scan_001: portal door_1 -> z_synthetic_scan_001_room rel (500, -700, 0) cm yaw -90.0 radius 100 cm -> level (18170.58, -22898.01, 999.33) [entry]
LogGolmok: Zone z_synthetic_scan_001 v1 loaded in x ms: chunks 2/2 (0 wire boxes), collision 2/2, blockers 1/1, portals 1 (WP-05)
interior_setup: exterior zone Zone_z_synthetic_scan_001 rebuilt
interior_setup: done z_synthetic_scan_001_room v1 -> <Project>\Saved\Golmok\zone_import\z_synthetic_scan_001_room\v1\import_result.json
```
(`T_room`의 `, vt enabled after import` 접미는 §2와 같은 임포터 기본값에 따른다. 실외 zone의 재빌드 줄은 서브레벨 저장 뒤 `L_ZoneTest`를 디스크에서 다시 열었기 때문 — 트랜지언트 컴포넌트·`door_1` 포털 복원.)
- [ ] `door_1`(entry)와 `door_out`(marker)의 `level (…)`이 **같은 점** (18170.58, −22898.01, 999.33)이고 yaw는 −90.0 / 90.0. 실내 zone root (17770.58, −22918.00, 999.34) = 실외 zone-local (1.0, 7.2, 0) m.
- [ ] 콘텐츠 브라우저 `/Game/Golmok/Zones/z_synthetic_scan_001_room/v1/`: `SM_c_e000_n000`, `SM_z_synthetic_scan_001_room_collision_c_e000_n000`, `Textures/T_room`, `Materials/MI_room`, `L_z_synthetic_scan_001_room` — 그 외 없음. `Content\Golmok\Zones\z_synthetic_scan_001_room\v1\manifest.json` 한 파일(blockers 없음).
- [ ] `T_room` 256×256 노랑, VT ✔; `MI_room` parent `M_ZoneScan`; `SM_c_e000_n000`(room) Nanite ✔, 슬롯 `room`→`MI_room`, Approx Size ≈ 800×680×340 cm.
- [ ] 아웃라이너 `Golmok/Zones/Zone_z_synthetic_scan_001_room`(State = Unloaded; PIE에서 문이 로드), `Zone_z_synthetic_scan_001`(Loaded). **Levels 창(Window › Levels)에 서브레벨 등록 없음**(기본 경로 `LevelInstance`; `register=True`는 `NamedStreamingLevel` 전용).
- [ ] 서브레벨 `L_z_synthetic_scan_001_room`을 더블클릭해 열면 `Golmok/Interior/Interior_Light_z_synthetic_scan_001_room` PointLight **하나만**(태그 `GolmokInteriorSetup`, 3000 cd·3000 K, 실내-local (400, −340, 250) cm = 방 중앙 천장 아래 — 레벨 좌표로 놓임), PPV·DirectionalLight·`AGolmokZone`·`AGolmokPortal` 없음. 확인 후 `L_ZoneTest`를 다시 연다.
- [ ] `import_result.json`(room)의 `interior` 블록: `sublevel`, `round_trip.ok true`, `parent z_synthetic_scan_001`, `actors ['Interior_Light_z_synthetic_scan_001_room']`.

실패 시:
- `interior_setup: ERROR manifest: kind must be interior …` → 실외 폴더를 넘긴 것. `ERROR portal: door_out vs door_1: x m apart, yaw error y deg (fix the manifests before importing)` → 생성기 출력이 손상됨 → §1 `--force` 재생성(정상 출력은 0.000 m·0.0°).
- `interior_setup: ERROR parent: no Content manifest for z_synthetic_scan_001: run zone_import.run on the parent zone first` → §2의 `copied` 줄 확인. `ERROR parent: Zone_z_synthetic_scan_001 not in level …` → §2를 먼저(다른 레벨을 연 것).
- `interior_setup: ERROR sublevel: …` → `sz._spawn_interior_sublevel`(WP-05 §11 #45·#46 동일 경로) — `LevelEditorSubsystem.new_level` 저장 프롬프트가 떴으면 §12 #12.
- 서브레벨에 PointLight가 없거나 위치가 실내-local 그대로(레벨 원점 근처) → `zone.get_actor_transform()`이 `unload_in_editor()` 뒤에 무효 → §12 #11.

## 5. PIE 포털 왕복
PIE(HUD F1 켬). PlayerStart에서 **동 5 m·북 5 m**의 빨간 벽 문(x 5, y 7 m; 트리거 반경 1 m)으로 북진. 기대 로그 순서(WP-05 런북 §5와 동일 규칙):
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
- [ ] 문 앞 1 m 안에서 실내 로드 → 문 너머 **노란 방**(8×6.8 m, 높이 3 m, 타일 숫자 `1001`)과 **따뜻한 PointLight**가 보인다(서브레벨 스트림 인). HUD `portals` 줄에 `door_1 (…) active outside; sublevel visible (LevelInstance) | door_out (z_synthetic_scan_001_room -> z_synthetic_scan_001) (marker)`.
- [ ] 문 평면(y 7.0..7.2 m)을 넘으면 2 s 동안 안개 0·노출 +1 EV, HUD `tod: … [interior: door_1]`.
- [ ] 방 안 보행: 서·동·북 벽·천장에 막히고 바닥(방 z 0 = 실외 지면 높이)을 걷는다. 남쪽 벽은 실외 빨간 파사드(문 구멍만 통과). 방과 파사드 사이 틈 없음(방 y ≥ 7.2 m, 파사드 y 7.0..7.2 m).
- [ ] 되돌아 나오면 오버레이 off, 트리거를 벗어난 3 s 뒤 실내 언로드. `golmok.zone.list`에 `z_synthetic_scan_001_room  v1  prio 20  unloaded`.
- [ ] PIE 종료 시 에러·ensure 없음; 에디터에 Transient 포털·재생 폰 잔류 없음.

실패 시: WP-05 런북 §5 표대로(부호 반전이면 그 문서 §11 #8). 실내가 로드되지 않으면(`sublevel package missing`) §4의 서브레벨 패키지 경로가 `L_z_synthetic_scan_001_room`인지 확인(C++ `GolmokZoneManifest::SublevelPackagePath` 규약).

## 6. 재실행 idempotency
1. 서브레벨 `L_z_synthetic_scan_001_room`을 열어 큐브 액터 하나(라벨 `ManualProp`, 태그 없음)를 놓고 저장, `L_ZoneTest`로 복귀.
2. §2를 `zi.run(r"D:\golmok_synth\zones\z_synthetic_scan_001", level="/Game/Golmok/Maps/L_ZoneTest", geo_origin="area", reimport_textures=False)`로 다시, §4를 그대로 다시.
```
zone_import: importer mapping cache hit -> <Project>\Saved\Golmok\zone_import\importer_mapping.json
zone_import: texture /Game/Golmok/Zones/z_synthetic_scan_001/v1/Textures/T_facade tiles=[1001, 1002, 1011] size=512x512 vt=on (skipped: exists)
zone_import: texture /Game/Golmok/Zones/z_synthetic_scan_001/v1/Textures/T_ground tiles=[] size=256x256 vt=on (skipped: exists)
…
interior_setup: removed 1 GolmokInteriorSetup actors from /Game/Golmok/Zones/z_synthetic_scan_001_room/v1/L_z_synthetic_scan_001_room
interior_setup: sublevel /Game/Golmok/Zones/z_synthetic_scan_001_room/v1/L_z_synthetic_scan_001_room actors=['Interior_Light_z_synthetic_scan_001_room'] (level coordinates)
```
- [ ] 에셋이 **덮어써진다**(`SM_c_e000_n000_2`·`T_facade_1` 같은 접미 없음; `replace_existing=True`). 콘텐츠 브라우저 목록이 §2·§4와 동일.
- [ ] 아웃라이너에 `GeoOrigin`·`Zone_z_synthetic_scan_001`·`Zone_z_synthetic_scan_001_room`이 각 1개(중복 스폰 없음).
- [ ] 서브레벨에 `ManualProp`이 **살아남고** `Interior_Light_…`는 1개(태그 `GolmokInteriorSetup`만 지우고 다시 만든다).
- [ ] §5 왕복이 그대로 동작.

## 7. spike_runner 리허설 (합성 zone, `L_ZoneTest`)
시점 10개를 저장한다(이름 고정: research/08 조건 3/4/3). 뷰포트를 옮겨 가며:
```python
import golmok.viewpoints as v
v.save("far_01"); v.save("far_02"); v.save("far_03")          # 원경: 지면 끝에서 벽들을 한눈에
v.save("mid_01"); v.save("mid_02"); v.save("mid_03"); v.save("mid_04")   # 중경: mid_01 프리셋 비교, mid_02 청크 이음새(x 0 m 경계), mid_04 얇은 구조물(창틀)
v.save("near_01"); v.save("near_02"); v.save("near_03")      # 근경 0.5 m: 타일 숫자, near_03 캐릭터 그림자 자리
import golmok.spike_runner as s; s.prepare()
```
```
spike_runner: viewpoints L_ZoneTest: 10 saved, missing=[]
```
(빠진 이름은 `missing=['mid_04']`처럼 나온다. 시점 파일 `Config\Golmok\Viewpoints\L_ZoneTest.json`.)

무인 캡처(PIE 상태기계; 태그 `a`만, 프리셋 2개 → 20장):
```python
s.capture_all(tags=("a",), presets=("clear_noon", "night"), mode="pie")
```
기대 로그(시점마다 `>` 3줄 + `captured` 1줄; 프리셋이 바뀔 때만 `golmok.tod`):
```
spike_runner: layers tag=a zone_visual=True Spike_b=False Spike_c=False (actors 1, editor)
spike_runner: PIE window 1280x720 x2 (LevelEditorPlaySettings)
spike_runner: PIE begin tag=a
spike_runner: > golmok.hud 0
spike_runner: layers tag=a zone_visual=True Spike_b=False Spike_c=False (actors 1, pie)
spike_runner: > golmok.tod clear_noon
spike_runner: > golmok.path play vp_far_01
spike_runner: > golmok.screenshot a far_01
spike_runner: captured <Project>\Saved\Screenshots\Golmok\a\clear_noon\far_01.png (2560x1440)
spike_runner: > golmok.path stopplay
spike_runner: > golmok.path play vp_far_02
…
spike_runner: > golmok.tod night
…
spike_runner: PIE end tag=a
spike_runner: done capture: 20 saved, 0 missing -> <Project>\Saved\Screenshots\Golmok
```
(`actors N`은 가시성을 바꾼 액터 수 — 합성 레벨에는 zone 1개뿐. 새 PIE 창이 뜨고 3 s 워밍업 뒤 카메라가 시점을 차례로 돈다; 시점당 약 5~6 s. 재생 중 캐릭터는 숨는다.)
- [ ] `<Saved>\Screenshots\Golmok\a\clear_noon\` 10장 + `a\night\` 10장, 모두 **2560×1440**, HUD 없음, 캐릭터 없음, 시점 이름과 내용이 맞다(`far_01.png`가 원경).
- [ ] 같은 명령을 **에디터 창을 뒤로 보낸 채**(다른 창을 앞에) 한 번 더 → 결과 동일(백그라운드 PIE는 느릴 뿐 — 8 fps 수준; dwell 경로 600 s가 흡수). 걸린 시간을 §11에.
- [ ] 컨택트 시트:
  ```python
  s.contact_sheet(tags=("a",), presets=("clear_noon", "night"))
  ```
  ```
  spike_runner: contact sheet -> <Project>\Saved\Screenshots\Golmok\contact_sheet.html
  ```
  브라우저로 열면 프리셋별 표 2개(시점 10행 × 열 `(a) 메시 Nanite+Lumen | (b) Cesium splat | (c) XGRIDS LCC | (a+c) 하이브리드`), (a) 열에 20장, 나머지 열은 `missing`.
- [ ] (선택) 유인 경로: 에디터 창을 앞에 두고 `s.capture_all(tags=("a",), presets=("clear_noon",), mode="editor")` → `viewpoints.capture`가 뷰포트에서 10장(`Capturing 10 screenshots -> …` 로그, 같은 폴더에 덮어씀).
- [ ] `s.report_template()` → `<Saved>\Golmok\spike\report_template.md`(표 헤더가 `docs/research/08-spike-results.md`와 같다).

실패 시:
- `spike_runner: WARNING PIE did not start …` / `spike_runner: PIE begin tag=a` 뒤 60 s 침묵 → §12 #16(`LevelEditorSubsystem.editor_request_begin_play()`가 마지막 플레이 모드를 쓴다: Play 드롭다운을 "New Editor Window (PIE)"로 바꾸고 재시도; 안 되면 수동 PIE 뒤 `mode="editor"`).
- `spike_runner: WARNING PIE window: manual: Editor Preferences > Level Editor > Play > New Window Size (runbook #21)` + `spike_runner: PIE window 1280x720 x2 (manual: …)` → §12 #21: 설정에서 New Window Size 1280×720을 손으로 놓고 재시도. `captured … (1280x720)`처럼 크기가 다르면 `ScreenshotMultiplier`가 1로 떨어진 것(WP-05 런북 §8 메시지 확인).
- `spike_runner: missing <path> (timeout)` → 파일이 30 s 안에 안 생김: 콘솔 명령이 PIE 월드에 닿지 않는다(§12 #15; 로그에 `golmok.*: no debug subsystem`이면 월드가 에디터 월드) 또는 `golmok.screenshot`이 `<name>00000.png`으로 썼는데 개명 실패(§12 #30).
- 파일이 `…\a\current\far_01.png`에 생기고 missing 보고 → `golmok.tod`가 `AGolmokTimeOfDay`를 못 찾음(§12 #13; L_ZoneTest 조명 액터 태그 `GolmokLighting` 확인 — WP-05 런북 §3).
- `spike_runner: WARNING viewpoints: … not saved` / `missing=[…]` → `v.save` 누락.
- `golmok.path play: ERROR …` 뒤 검은 화면 → 2샘플 600 s 경로 JSON을 C++ 파서가 거부(§12 #24). `<Saved>\Golmok\Paths\vp_far_01.json`을 §11에 첨부.

## 8. `-game` 성능 (정본)
1. PIE에서 경로 녹화(WP-05 런북 §7과 같은 규칙): 콘솔 `golmok.path record walk_01` → **3 s 제자리** → 약 60 s 걷기(지면 전체·문 왕복 포함) → `golmok.path stop` → `<Saved>\Golmok\Paths\walk_01.json`. PIE 종료.
2. 레이어 맵 저장(태그 b·c·ac; 합성 레벨엔 `Spike_*` 액터가 없으니 zone 가시성만 다르다):
   ```python
   import golmok.spike_runner as s
   s.save_layer_levels()
   ```
   ```
   spike_runner: layers tag=b zone_visual=False Spike_b=True Spike_c=False (actors 1, editor)
   spike_runner: layer level /Game/Golmok/Maps/L_Spike_b saved (tag b)
   spike_runner: layer level /Game/Golmok/Maps/L_Spike_c saved (tag c)
   spike_runner: layer level /Game/Golmok/Maps/L_Spike_ac saved (tag ac)
   ```
   - [ ] `/Game/Golmok/Maps/L_Spike_b`·`L_Spike_c`·`L_Spike_ac` 3개, 끝에 `L_ZoneTest`로 복귀. `L_Spike_b`를 열면 `Zone_z_synthetic_scan_001`의 Visual 레이어가 꺼져 있고(충돌만) 디테일 `AutoManaged` ✖.
3. 스크립트 생성·실행:
   ```python
   s.game_scripts(paths=("walk_01",), tags=("a", "b"))
   ```
   ```
   spike_runner: -game script -> <Project>\Saved\Golmok\spike\run_game_perf.ps1 (2 runs)
   ```
   에디터를 **닫고** PowerShell:
   ```powershell
   & "<Project>\Saved\Golmok\spike\run_game_perf.ps1"
   ```
   기대 출력(run마다 1~2분; `-RenderOffscreen`이라 창이 뜨지 않는다):
   ```
   csv a_clear_noon_walk_01 -> C:\Users\<me>\AppData\Local\UnrealEngine\5.8\Saved\Profiling\CSV\Profile(…).csv
   csv b_clear_noon_walk_01 -> …
   golmok-perf "<Project>\Saved\Golmok\spike\csv\a_clear_noon_walk_01.csv" "<Project>\Saved\Golmok\spike\csv\b_clear_noon_walk_01.csv" --label a_clear_noon_walk_01 --label b_clear_noon_walk_01 --markdown
   ```
   - [ ] `<Saved>\Golmok\spike\csv\a_clear_noon_walk_01.csv`·`b_…csv` 생성. 로그 `<Saved>\Golmok\spike\game_a_clear_noon_walk_01.log`에 `GolmokDebugSubsystem: path play 'walk_01' (60.x s, 60x samples) + CsvProfile` → `CsvProfile Start (path 'walk_01')` → `csv: …` 줄이 있고 프로세스가 스스로 종료했다(`-ExitAfterCsvProfiling`; 타임아웃 900 s kill이면 Warning `… timeout after 900 s`).
   - [ ] **CSV 프레임 수 ≈ 경로 길이 × fps**(60 s × ~150 fps ≈ 9,000; 첫 2 s는 `golmok-perf`가 버린다). 3,000 근처면 `-csvCaptureFrames`가 섞인 것(명령줄에 있어서는 안 된다 — `.ps1` 확인).
   - [ ] 마지막 줄의 `golmok-perf …` 명령을 tools venv에서 실행 → 표 2행(`a_clear_noon_walk_01`, `b_clear_noon_walk_01`; b는 zone 시각 레이어가 꺼져 fps가 더 높다). 표를 §11에 붙인다. CSV 위치(프로젝트 `Saved` vs `%LOCALAPPDATA%`)를 §11에.

실패 시: 로그에 `golmok.*: no debug subsystem in this world (game / PIE only).`가 `path play` 앞에 있고 CSV 없음 → `-ExecCmds`가 맵 로드 전에 실행된 것(§12 #17) → §9의 PIE 참고치로 대체하고 §11에 "PIE"라고 적는다. `run_game_perf.ps1`의 `Write-Warning … no CSV newer than …` → 두 Saved 후보 모두에 CSV가 없음: 로그의 `csv: no Profile*.csv yet in …` 줄과 실제 폴더를 §11에. `UnrealEditor.exe` 경로 오류 → §12 #27(`$env:UE_ROOT` 설정 후 `s.game_scripts` 재생성). `L_Spike_b` 저장 실패 → §12 #18(File › Save Current Level As로 수동 저장 후 `apply_layers("b")` 재실행).

## 9. PIE 성능 참고치 (선택)
에디터에서:
```python
s.perf_all(paths=("walk_01",), tags=("a",))
```
```
spike_runner: PIE begin tag=a
spike_runner: > golmok.hud 0
spike_runner: > golmok.tod clear_noon
spike_runner: > golmok.path play walk_01 --csv
spike_runner: csv <Project>\Saved\Profiling\CSV\Profile(…).csv -> golmok-perf "<Project>\Saved\Profiling\CSV\Profile(…).csv" --label a_clear_noon_walk_01 --markdown
spike_runner: PIE end tag=a
spike_runner: done perf (PIE, reference only): 1 saved, 0 missing -> <Project>\Saved\Profiling\CSV
```
- [ ] PIE(에디터) CSV는 `<Project>\Saved\Profiling\CSV\`. `golmok-perf` 표 1행을 §8의 `-game` 값과 나란히 §11에(에디터 오버헤드만큼 낮다 — 참고치).

## 10. `basemap_import` 보강 (선택; V-02 베이스맵이 있는 PC)
`L_Basemap_Yeonnam`을 열고 WP-04 런북(V-02)과 같은 명령으로 재실행:
```python
import golmok.basemap_import as b; b.run(r"D:\golmok_basemap\yeonnam")
```
```
basemap_import: GeoOrigin lat=… lon=… h=… (basemap origin; ellipsoidal = DEM orthometric + --geoid-offset)
```
- [ ] 아웃라이너 `Golmok/GeoOrigin`의 Latitude/Longitude/HeightEllipsoidal = 베이스맵 `manifest.json`의 `origin`(`CesiumGeoreference`와 같은 값). 이미 있으면 갱신만(중복 없음, §12 #20).
- [ ] `--exclude`는 에디터에서 할 일이 없다(빌드 시 타일에서 제외됨; docstring 확인만).

## 11. 결과 기록
| 항목 | 결과 | 메모·실측 |
|---|---|---|
| 전제(pytest·L_ZoneTest) | | |
| §1 생성(파일 27개·PNG·validate OK) | | |
| §2 route / obj mapping / glb mapping | | `import_result.json`의 `route`, `scale`·`m`·`err` 그대로 |
| §2 텍스처(`size=` 표기, `merged by importer`/`packed`/`tile 1001 only`, VT, 숫자 방향) | | |
| §2 청크(Nanite·슬롯·bounds 오차)·충돌 | | `deleted importer-created asset` 개수 |
| §2 GeoOrigin·Zone 액터·뷰포트 | | |
| §3 PIE 걷기(유리·문·블록·경사) | | |
| §4 실내(포털 왕복 검사·서브레벨·PointLight) | | |
| §5 포털 왕복(로그 순서) | | |
| §6 재실행(덮어쓰기·`ManualProp` 보존·`removed 1`) | | |
| §7 시점 10개·PIE 창 크기·스크린샷 해상도 | | 백그라운드 실행 시간 |
| §7 컨택트 시트·리포트 템플릿 | | |
| §8 `-game` CSV 위치·프레임 수·`golmok-perf` 표 | | 표를 붙인다 |
| §9 PIE 참고치 | | |
| §10 basemap GeoOrigin | | |
| 고친 API(§12 번호) | | 커밋 해시 |
| 설계와 다른 동작 발견 | | 이 문서에 없는 추가분 |

기록 뒤:
1. 이 표를 채우고 커밋(`WP-06: PC 검증 결과`). 스크린샷은 `docs/runbooks/` 옆에 `pc-verify-wp06-*.jpg`(작게).
2. `docs/plan/STATUS.md`: WP-06 행을 🟡 → 🟢(또는 🔴 + 막힌 항목), V-04 행 갱신, 세션 로그 표에 한 줄(날짜·PC 세션·모델·"V-04 WP-06 검증"·결과). 고친 API·설계 변경은 인계 메모에 번호(§12)와 커밋 해시로.
3. `docs/plan/WP-06-ue-python-automation.md` "결과"에 PC 검증 한 줄(통과/수정 건수), `docs/ROADMAP.md` 1.1·1.3 진행 표시. 통과하면 `pc-spike.md`(S0 전제)로 넘어간다.

## 12. 에디터 Python이 실패하면 — 불확실 API 표
클라우드 세션이 에디터에서 실행해 보지 못한 호출 목록(설계 §7 그대로, 번호 유지). 코드는 이 표의 API를 전부 `hasattr` 분기 + `unreal.log_warning(… (runbook #n))`으로 감쌌다. 오류 메시지·경고의 `runbook #n`이 이 표의 행이다. `tools/tests/test_ue_python_pure.py::test_no_unreal_api_outside_touchpoint_list`가 이 표의 `unreal.<Name>` 표기를 화이트리스트로 읽으므로, 새 `unreal.*` 호출을 코드에 더하면 이 표에도 행을 더한다.

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
| 18 | spike_runner | `EditorAssetLibrary.duplicate_asset(level, "/Game/Golmok/Maps/L_Spike_<tag>")`로 맵 복제 | 월드 파티션·외부 액터 | 실패 시 수동 "Save Current Level As" 안내 |
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
| 31 | spike_runner | `unreal.Paths.convert_relative_path_to_full(path)`로 `project_saved_dir()`·`engine_dir()`·`get_project_file_path()`를 절대경로화(`.ps1`의 경로) | 에디터가 바이너리 폴더 기준 상대경로를 줄 수 있음; 함수 노출은 추정 | 없으면 `os.path.abspath`(에디터 작업 폴더 기준); `.ps1` 첫 줄의 경로가 틀리면 손으로 고치고 §11에 기록 |
| 32 | spike_runner | `mode="editor"`: 이전 태그 `viewpoints.capture`의 `on_done`(slate post-tick 콜백 안)에서 다음 태그의 `unreal.register_slate_post_tick_callback`을 다시 등록 | 콜백 안에서의 재등록 허용 여부 | 두 번째 태그가 시작되지 않으면 태그마다 `s.capture_all(tags=("<tag>",), mode="editor")`를 따로 부른다 |
| 33 | spike_runner | 태그 사이 PIE 재시작 간격 `PIE_RESTART_GAP_S = 1.0`(`editor_request_end_play()` 뒤 다음 `editor_request_begin_play()`까지) | 새 PIE 창이 같은 틱 근처에서 다시 뜨는지 | 두 번째 태그의 `PIE begin` 뒤 창이 안 뜨면 상수를 3~5 s로 올려 재시도(§11에 기록) |
