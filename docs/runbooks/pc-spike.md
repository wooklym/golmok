# 런북: 스파이크 1.1 전체 절차 — 환경 표현 방식 비교 → D-010 (V-05)

작성: 2026-09-25 (WP-06) · 대상: PC Claude 세션 + 사용자 · 결과는 `docs/research/08-spike-results.md`에 채우고 D-010을 결정한다.
관련: [ROADMAP §1.1](../ROADMAP.md), [research/07](../research/07-ue5-toolchain.md) §3~§6, [research/08](../research/08-spike-results.md), [recon-postprocess.md](recon-postprocess.md), [align.md](align.md), [pc-verify-wp06.md](pc-verify-wp06.md)(WP-06 검증 런북, 같은 폴더), D-005·D-006·D-007·D-010.

이 런북은 **한 골목 청크(30~50 m)를 세 방식 (a) 메시 Nanite+Lumen (b) Cesium splat (c) XGRIDS LCC(+ (a+c) 하이브리드)으로 만들어 같은 조명·같은 시점·같은 경로로 비교**하는 전 과정이다. 단계마다 입력·명령·예상 시간·실패 시 대안을 적었다. 한 단계가 막히면 대안으로 넘어가고 [미확인] 칸에 관찰을 남긴다.

## 0. 전제·준비 (S0, 약 30분)
| 항목 | 확인 |
|---|---|
| 촬영 | C-02 골목 사진 ≥ 1,000장 + 영상(가이드 #1 §5·§6), `docs/captures/INDEX.md`에 촬영 ID 등록 |
| 결정 | D-006(PC 사양·클라우드 보조), D-005(RealityScan + Postshot), D-007(블러 전 데이터 외부 업로드 금지) |
| PC | 디스크 여유 ≥ 200 GB(원본 100~150 GB + RealityScan 캐시 + UE DDC), UE 5.8.3 빌드 OK(V-03), [pc-verify-wp06.md](pc-verify-wp06.md) §1~§7 통과(합성 zone으로 임포트·PIE 캡처 리허설 완료) |
| 도구 | `cd tools; .\.venv\Scripts\Activate.ps1; pip install -e ".[raw,heic,basemap,zone,mesh,splat,align,dev]"; pytest -q` 초록. EgoBlur 모델 `tools\models\`(사용자 라이선스 동의) |
| 계정·구독 | Postshot **Studio**(CLI·4K 초과 이미지, D-005), XGRIDS 라이선스 문의 결과(C-04·D-009), Cesium ion은 쓰지 않는다(로컬 타일셋) |
| 작업 폴더(git 밖) | `D:\golmok_capture\<촬영ID>\`, `D:\golmok_recon\<촬영ID>\`, `D:\golmok_zones\zones\<zone_id>\v1\`, `D:\golmok_basemap\yeonnam\`(V-02 베이스맵) |

## 1. 단계 요약표
| 단계 | 입력 | 명령·설정 | 예상 시간 | 실패 시 대안 |
|---|---|---|---|---|
| S1 블러 | 원본 JPEG(ProRAW JPEG 무손실, D-011)·영상 프레임 | `golmok-blur <in> <out> --face-model … --lp-model …` | 1~2 h / 1,000장 | 모델 없음 → 다운로드 후 재시도(블러 없이 진행 금지, D-007) |
| S2 RealityScan | 블러 사진(+프레임) | 정렬 → 메시 High → 텍스처 8K **UDIM** → OBJ+MTL 내보내기 | 3~8 h | 정렬 조각남 → 영상 프레임 추가·재촬영 구간; RAM 부족 → 구역 나눠 내보내기 |
| S3 포즈 내보내기 | S2 정렬 | Registration → COLMAP/XMP + undistorted 이미지 | 20분 | XMP 실패 → COLMAP 텍스트 형식 |
| S4 Postshot | S3 | Splat3, `--max-image-size 0`, SH 3, AA 켬, 스텝은 수렴까지 | 1~3 h (8 GB VRAM이면 더) | VRAM OOM → AWS g6e(D-006) 또는 splat 수 상한 축소(품질 원칙 위반은 기록) |
| S5 후처리 | S2·S4 출력 | `golmok-mesh reproject/chunk/collision/blockers`, `golmok-splat crop/clean/tiles` | 30분~1 h | [recon-postprocess.md](recon-postprocess.md) 각 절의 대안 |
| S6 검증·정합 | zone 폴더 | `golmok-zone validate --check-files --strict`, `golmok-align run`(선택) | 5~20분 | 오류 메시지대로; 정합 실패는 위치 오프셋을 수동 기록 |
| S7 UE 임포트 (a) | zone 폴더 | `zi.run(...)` | 10~40분 | bounds 오류 → `remeasure=True`; UDIM 미병합 → 폴백 로그 확인 |
| S8 (b) Cesium splat | S5 `splat_tiles/` | `Cesium3DTileset` 액터, 라벨 `Spike_b_tiles` | 20분 | 로드 안 됨 → `3d-tiles-validator`; 그래도 안 되면 (b) 열 비움 |
| S9 (c) XGRIDS LCC | Postshot PLY → LCC | LCC4Unreal 플러그인 임포트, 라벨 `Spike_c_lcc` | 30분 | 라이선스·플러그인 없음 → (c)·(a+c) 열 비움 |
| S10 시점 저장 | 레벨 | `viewpoints.save` 10개(이름 고정) → `s.prepare()` | 20분 | — |
| S11 캡처 | S7~S10 | `s.capture_all(mode="pie")` → 컨택트 시트 | 40분 | 창을 앞에 두고 `mode="editor"` |
| S12 성능 | 녹화 경로 | `s.save_layer_levels()` → `s.game_scripts()` → `.ps1` → `golmok-perf` | 40분 | `-game` 실패 → `s.perf_all()` PIE 참고치(표에 "PIE" 표기) |
| S13 그림자·조명 채점 | 레벨 | 유인 PIE 걷기(태그별) | 15분 | — |
| S14 리포트 | S11~S13 | `s.report_template(...)` → `research/08` 채우기 | 1 h | — |
| S15 결정 | research/08 | D-010 회의 | — | — |

총 예상: 처리 6~15시간(대부분 대기) + 손 작업 4~5시간. 하루에 S1~S5, 다음 날 S6~S15가 현실적이다.

## 2. 단계별 상세

### S1. 블러 (D-007, research/05)
```powershell
golmok-blur D:\golmok_capture\<ID>\photos D:\golmok_capture\<ID>\photos_blurred --face-model tools\models\ego_blur_face.jit --lp-model tools\models\ego_blur_lp.jit
golmok-frames D:\golmok_capture\<ID>\video\V1.mov D:\golmok_capture\<ID>\frames --fps 2
golmok-blur D:\golmok_capture\<ID>\frames D:\golmok_capture\<ID>\frames_blurred --face-model … --lp-model …
```
- 출력 폴더의 `_golmok/gps_priors.csv`(정합용)와 블러 통계를 보관한다. RealityScan·Postshot에는 **`*_blurred`만** 넣는다.
- 예상: RTX 5060에서 사진 1,000장 ≈ 1~2시간. GPU 미사용(`torch.cuda.is_available()` False)이면 CUDA 12.8 휠 재설치(`tools/README.md`).

### S2. RealityScan 정렬·메시·UDIM 내보내기 (research/07 §3)
| 항목 | 설정값 | 표기 |
|---|---|---|
| 입력 | `photos_blurred` + (선택) `frames_blurred` | |
| 정렬 | 기본. GPS prior 사용(iPhone EXIF). 조각(component)이 여러 개면 영상 프레임을 더해 재정렬 | [확인] |
| 지오레퍼런싱 | GPS 자동 → 출력 좌표계 **EPSG:5186**(방법 A) 또는 로컬(방법 B) — recon-postprocess.md §2 | [미확인: 메뉴 이름] |
| 메시 | **High detail**, Simplify로 스파이크 청크(30~50 m) 기준 **5~15M tri** | 판단 |
| 텍스처 | **8K, UDIM 타일**, PNG(또는 TIF). 파일명이 `<이름>.1001.png` 형식인지 확인(UE UDIM 규약, [확인]: Streaming Virtual Texturing 문서 "UDIM Support") | [확인] |
| 내보내기 | OBJ + MTL, 한 조각 2천만 tri 이하 | |
| 예상 시간 | 정렬 30분~1시간, 메시 1~3시간, 텍스처 1~2시간(6코어·8 GB VRAM 기준, 실측 기록) | [미확인] |
실패 시: 정렬이 두 조각 이상 → 겹치는 구간 사진 추가·재촬영(가이드 #1 P2·P3 패스); 메모리 부족 → 구역을 나눠 내보내고 `chunk`/`collision`에 조각들을 한꺼번에 넘긴다.

### S3. COLMAP/XMP 포즈 내보내기 (D-005: 메시와 splat이 같은 좌표계)
Alignment → Export → Registration: **XMP**(카메라별) + undistorted 이미지, 또는 COLMAP 텍스트(cameras/images/points3D). 예상 20분. [미확인] Postshot이 XMP를 직접 읽는지 → 실패하면 COLMAP 형식으로.

### S4. Postshot 학습 (D-006 설정)
| 설정 | 값 |
|---|---|
| 입력 | S3 포즈 + `photos_blurred` |
| 프로파일 | Splat3(권장). MCMC는 비교용 |
| 이미지 크기 | `--max-image-size 0`(원본; Studio 필요) |
| SH | 3, Anti-Aliasing 켬 |
| 스텝 | 자동 추정값 이상, 프리뷰가 수렴할 때까지 |
| Max Splat Count | VRAM이 허용하는 최대 |
| 내보내기 | PLY(`D:\golmok_recon\<ID>\postshot\<ID>.ply`) |
예상 1~3시간(8 GB VRAM은 splat 상한을 줄여야 할 수 있다 → **품질 원칙 위반 여부를 기록**하고 AWS g6e 대안(D-006)). 결과 PLY는 git에 넣지 않는다.

### S5. 후처리 (WP-03 도구; recon-postprocess.md §2~§6 그대로)
```powershell
$Z = "D:\golmok_zones\zones\z_yeonnam_alley_001\v1"
golmok-zone init --id z_yeonnam_alley_001 --kind exterior --origin <lat>,<lon>,<타원체고> --footprint D:\golmok_zones\fp.geojson --capture <ID> --out $Z
golmok-mesh reproject D:\golmok_recon\<ID>\export\alley.obj --src-crs EPSG:5186 --manifest $Z\manifest.json --out D:\golmok_recon\<ID>\local\alley.obj
golmok-mesh chunk D:\golmok_recon\<ID>\local\alley.obj --size 15 --out $Z\visual --manifest $Z\manifest.json
golmok-mesh collision D:\golmok_recon\<ID>\local\alley.obj --out $Z\collision.glb --target-tris 30000 --per-chunk $Z\visual --manifest $Z\manifest.json --report D:\golmok_zones\collision_report.json
golmok-mesh blockers add $Z\blockers.json --center <x,y,z> --normal <nx,ny,nz> --size <w,h> --kind glass ; golmok-mesh blockers build $Z\blockers.json --manifest $Z\manifest.json
golmok-splat crop D:\golmok_recon\<ID>\postshot\<ID>.ply --manifest $Z\manifest.json --margin-m 2 --out D:\golmok_recon\<ID>\splat_crop.ply
golmok-splat clean D:\golmok_recon\<ID>\splat_crop.ply --knn 16 --std 2.0 --min-opacity 0.02 --max-scale-m 1.0 --out $Z\splat.ply
golmok-splat tiles $Z\splat.ply --out $Z\splat_tiles --manifest $Z\manifest.json --max-splats 500000
```
- 스파이크는 골목 전체가 아니라 **30~50 m 청크 1~3개**면 된다: `--along <중심선 GeoJSON>`으로 구간을 잡거나 격자 청크 중 2~3개만 남긴다(manifest `layers.visual.chunks`를 줄이지 말고 그대로 두되 시점을 그 구간에 둔다).
- `visual/chunk_manifest.json`의 `missing`이 비어 있어야 한다(텍스처를 못 찾으면 UE 임포트가 계획 단계에서 멈춘다).
- `clean` 옵션은 recon-postprocess.md §6과 같다(기본값은 opacity·scale 필터가 꺼져 있으니 생략하지 않는다). 결과 JSON의 floaters 비율이 5%를 넘으면 `--std`를 올려 보고 값을 §4에 적는다((b)·(c)·(a+c) 점수가 같은 정리 조건에서 나와야 한다).
- splat 좌표계가 메시와 다르면(`golmok-splat inspect` 범위 비교) `transform --matrix`로 맞추고 이 런북 §4 [미확인] 칸에 적는다.

### S6. 검증·정합
```powershell
golmok-zone validate $Z\manifest.json --check-files --strict
golmok-align run --zone $Z --basemap D:\golmok_basemap\yeonnam --gps D:\golmok_capture\<ID>\photos_blurred\_golmok\gps_priors.csv --ground      # 리포트만
golmok-align run ... --ground --write                                                                                                       # 확인 후
```
정합(align.md)은 스파이크 품질 비교에 필수는 아니다. 베이스맵과 어긋나 보이면 `GeoOrigin`·`transform`을 의심하기 전에 `golmok-align`의 `correction_area_enu`를 본다.

### S7. UE 임포트 (a) 메시
에디터(`L_Basemap_Yeonnam` 또는 `L_ZoneTest`) Output Log → Python:
```python
import golmok.zone_import as zi
r = zi.run(r"D:\golmok_zones\zones\z_yeonnam_alley_001", level="/Game/Golmok/Maps/L_Basemap_Yeonnam", geo_origin=r"D:\golmok_basemap\yeonnam")
```
- 기대 로그 형식과 확인 항목은 [pc-verify-wp06.md](pc-verify-wp06.md) §2와 같다(합성 zone 대신 실 zone 이름·수치). `geo_origin=<베이스맵 폴더>`는 베이스맵 manifest의 `origin`(타원체고 = DEM 정표고 + `--geoid-offset`)을 `GeoOrigin`에 쓴다.
- 시간: OBJ 사본 쓰기(2천만 tri ≈ 1.5 GB 텍스트, 1~2분) + Nanite 빌드(청크당 수 분) + 8K UDIM VT 빌드. 디스크는 원본 OBJ 크기의 2배.
- 실패: `zone_import: ERROR chunk …` bounds → `zi.run(..., remeasure=True)`; 텍스처 `vt=off` → `M_ZoneScan_NoVT`가 자동 생성되며 8K 여러 장이 VRAM에 통째로 올라오므로 fps가 떨어진다(기록); `tile 1001 only (WARNING)` → [pc-verify-wp06.md](pc-verify-wp06.md) §12 #4.
- 8K UDIM 6장 이상이면 `r.VT.MaxUploadsPerFrame`·VT 풀 크기(`r.VT.PoolSizeScale`) 튜닝이 필요할 수 있다[추정] → 텍스처가 흐리게 남으면 콘솔 `stat virtualtexturing`.

### S8. (b) Cesium for Unreal splat
1. Cesium for Unreal 플러그인 활성(research/07 §5; ion 로그인 불필요).
2. `Cesium3DTileset` 액터 추가 → Source: **From Url**, Url `file:///D:/golmok_zones/zones/z_yeonnam_alley_001/v1/splat_tiles/tileset.json` → 액터 라벨 **`Spike_b_tiles`**(spike_runner가 이 접두로 레이어를 켜고 끈다). `CesiumGeoreference` 원점은 베이스맵 origin(`basemap_import`가 설정).
3. 확인: splat이 메시 위치와 겹쳐 보임(3D Tiles `root.transform` = zone→ECEF). 색이 어두우면 `golmok-splat tiles --color0 display`(기본) 여부부터 확인(recon-postprocess.md §6).
실패: 로드 안 됨 → `npx 3d-tiles-validator --tilesetFile …`; 위치가 틀림 → `golmok-zone transform`으로 root.transform 대조; 안 되면 (b) 열을 비우고 사유 기록.

### S9. (c) XGRIDS LCC (+ (a+c) 하이브리드)
1. Postshot PLY → LCC 변환(XGRIDS 도구; C-04 문의 결과에 따라). 플러그인 LCC4Unreal 설치·프로젝트 활성.
2. 임포트 액터 라벨 **`Spike_c_lcc`**, Lit 모드 + ProxyMesh = (a)의 청크 메시(가능하면).
3. (a+c): 레이어 `ac`는 zone 시각 레이어 + `Spike_c_*`를 함께 켠다(spike_runner가 처리). 전선·식생·간판 부분만 splat로 보강하려면 LCC를 그 영역으로 자른 두 번째 액터 `Spike_c_detail`을 둔다.
실패·미확보: (c)·(a+c) 열을 비우고 D-010 후보에서 제외(대안 Volinga는 research/07 §6).

### S10. 시점 저장 (10개, 이름 고정)
| 이름 | 역할 |
|---|---|
| `far_01..03` | 원경 3곳(골목 끝에서 반대편, 배경 LOD1과의 경계 포함) |
| `mid_01` | 중경, **조명 프리셋 변경 비교**용 |
| `mid_02` | 중경, **청크·배경·메시↔splat 이음새** |
| `mid_03` | 중경 |
| `mid_04` | **얇은 구조물**(전선·철망·난간·간판) |
| `near_01`, `near_02` | 근경 0.5 m(간판 글씨, 벽 질감) |
| `near_03` | 근경 + **캐릭터 그림자** 채점 위치(S13에서 유인 PIE로 본다) |
```python
import golmok.viewpoints as v; v.save("far_01")   # 뷰포트를 옮겨 가며 10번
import golmok.spike_runner as s; s.prepare()      # missing=[] 이어야 한다
```
시점은 `Config/Golmok/Viewpoints/<레벨>.json`(텍스트)에 저장되므로 커밋해 두면 재측정이 같은 시점에서 된다.

### S11. 캡처
```python
import golmok.spike_runner as s
s.capture_all()                                              # a b c ac × overcast_morning clear_noon golden_evening × 10 = 120장
s.capture_all(tags=("a","c"), presets=("night",))            # 선택: 야간
s.contact_sheet(photos_dir=r"D:\golmok_capture\<ID>\reference")   # 시점별 원본 사진 <name>.jpg를 두면 열이 추가된다
```
- PIE는 **레벨 뷰포트 안에서** 돈다(`editor_request_begin_play()`는 플레이 모드·새 창 설정을 보지 않는다). 크기는 `HighResShot 2560x1440`으로 명시하므로 뷰포트 크기와 무관하게 **2560×1440** PNG가 `Saved/Screenshots/Golmok/<tag>/<preset>/<name>.png`에 생긴다(크기가 다르면 `WARNING … expected 2560x1440 (runbook #35)`). 태그마다 PIE를 새로 시작하므로 (b)·(c) 액터가 없는 태그는 zone만 보인다.
- 기대 로그·실패 대응은 [pc-verify-wp06.md](pc-verify-wp06.md) §7. 한 시점이 `missing`이면 그 시점만 `s.capture_all(tags=(...), names=("mid_02",))`로 다시 찍는다.
- 에디터 창을 뒤로 보낸 채 레벨 뷰포트 PIE가 계속 그리는지는 **미확인**이다(V-01: 에디터 뷰포트는 백그라운드에서 멈췄다; pc-verify-wp06 §7·§12 #35의 결과를 따른다). 확인 전에는 창을 앞에 두고 돌리고, 빠지면 `mode="editor"`.
- 무인(밤새) 실행: GUI 에디터에 `quit_editor=True` — `& "$env:UE_ROOT\Engine\Binaries\Win64\UnrealEditor.exe" "<Project>\Golmok.uproject" /Game/Golmok/Maps/L_Basemap_Yeonnam -ExecCmds="py import golmok.spike_runner as s; s.capture_all(quit_editor=True)"`. 끝나면 `spike_runner: capture finished; quitting the editor (quit_editor=True)` 뒤 에디터가 스스로 닫힌다. 끝에 `, Quit`을 붙여도 에디터는 끝나지 않고(V-03), `QUIT_EDITOR`를 붙이면 캡처가 끝나기 전에 닫힌다. PIE는 렌더링이 필요하므로 `UnrealEditor-Cmd`·`-nullrhi`는 쓰지 않는다(§12 #34).
- 컨택트 시트 `Saved/Screenshots/Golmok/contact_sheet.html`을 브라우저로 열어 프리셋별 표(시점 × (a)(b)(c)(a+c))를 채점에 쓴다. 사용자와 함께 1~5점.

### S12. 성능 (정본 = `-game -RenderOffscreen`, research/08 기준선과 같은 방법)
```
(PIE 콘솔) golmok.path record walk_01   →  3초 제자리  →  60초 걷기(청크 전체·문 앞 포함)  →  golmok.path stop
```
```python
import golmok.spike_runner as s
s.save_layer_levels()                       # /Game/Golmok/Maps/L_Spike_b, L_Spike_c, L_Spike_ac (레이어가 켜진 사본 맵)
s.game_scripts(paths=("walk_01",), tags=("a","b","c","ac"), presets=("clear_noon",), res=(1920, 1080))
s.game_scripts(paths=("walk_01",), tags=("a","b","c","ac"), presets=("clear_noon",), res=(2560, 1440))   # 라벨 *_1440p — 1080p CSV·로그를 덮어쓰지 않는다(.ps1만 덮어쓰므로 첫 실행 뒤에 생성)
```
PowerShell(에디터를 닫고): `& "<Project>\Saved\Golmok\spike\run_game_perf.ps1"` → `Saved\Golmok\spike\csv\<tag>_<preset>_<walk>[_<suffix>].csv`(1920×1080이 아니면 suffix 기본값 `<높이>p`, 예: `a_clear_noon_walk_01_1440p.csv`) → 마지막 줄에 출력되는 `golmok-perf … --markdown` 명령을 실행해 표를 얻는다.
- 확인: CSV 프레임 수 ≈ 경로 길이 × fps(60 s × 150 fps ≈ 9,000). 3,000 근처면 `-csvCaptureFrames`가 섞인 것(있어서는 안 된다).
- DLSS 켬/끔은 `-ExecCmds`가 아니라 `DefaultEngine.ini`/콘솔 변수로 두 번 돌린다(연구 08 조건). DLSS 실행용 스크립트는 `label_suffix="1080p_dlss"`·`"1440p_dlss"`처럼 라벨을 붙여 만든다 — 붙이지 않으면 DLSS 없는 CSV를 덮어쓴다. 4K는 클라우드 인스턴스(선택).
- PIE 참고치 `s.perf_all(...)`도 무인 실행이면 `quit_editor=True`(S11과 같은 규칙).
- 실패: 로그에 `golmok.*: no debug subsystem` → `-ExecCmds` 실행 시점 문제([pc-verify-wp06.md](pc-verify-wp06.md) §12 #17) → PIE 참고치 `s.perf_all(paths=("walk_01",))`로 대체하고 표에 "PIE"를 적는다.

### S13. 캐릭터 그림자·조명 반응 (유인)
태그별로(레이어를 손으로 켜고) PIE에서 `near_03` 위치에 서서: 캐릭터 그림자가 바닥·벽에 떨어지는지(1~4 키로 프리셋 바꾸며), splat 레이어는 조명에 반응하지 않는 것이 정상(research/07 §5 — Unlit)임을 감안해 채점. 재생 캡처에는 캐릭터가 없으므로 이 항목만 유인으로 본다. 스크린샷은 `golmok.screenshot shadow_<tag> near_03` — 크기는 게임 뷰포트 × 2이므로, 2560×1440이 필요하면 먼저 `s.configure_pie_window()`(`spike_runner: PIE window 1280x720 x2 (LevelEditorPlaySettings)`)로 새 창 크기·모드를 놓고 Play 버튼(모드 "New Editor Window (PIE)")으로 PIE를 시작한다(§12 #21).

### S14. 리포트
```python
import golmok.spike_runner as s
s.report_template(perf_markdown=open(r"<Project>\Saved\Golmok\spike\perf.md", encoding="utf-8").read())   # golmok-perf --markdown 출력을 저장해 둔 파일
```
`Saved/Golmok/spike/report_template.md`의 표(시각 품질 7행 × 4열, 시점↔행 매핑, 성능, 제작 비용)를 `docs/research/08-spike-results.md` "결과"에 옮겨 채운다. 처리 시간(S2·S4·S5·S7~S9 실측)과 수작업 시간, 라이선스·배포 조건(RealityScan EULA, Cesium Apache-2.0, XGRIDS 회신)을 제작 비용 표에 적는다. 컨택트 시트·CSV·로그는 git 밖(용량)에서 링크만.

### S15. D-010 결정
research/08 "결론 → D-010"에 후보별 장단점을 적고 사용자가 승인하면 `docs/DECISIONS.md` D-010을 "승인"으로 바꾸고 manifest `layers.visual.format`(스펙 enum)과 WP-04 로더 확장 범위를 정한다(V-06 시작 조건).

## 3. 산출물 위치 요약
| 산출물 | 위치 |
|---|---|
| 블러 사진·프레임 | `D:\golmok_capture\<ID>\*_blurred\` (+ `_golmok\gps_priors.csv`) |
| RealityScan 프로젝트·OBJ·UDIM | `D:\golmok_recon\<ID>\` (git 금지) |
| Postshot PLY | `D:\golmok_recon\<ID>\postshot\` (git 금지) |
| Zone 폴더 | `D:\golmok_zones\zones\<zone_id>\v1\` |
| UE 에셋 | `/Game/Golmok/Zones/<zone_id>/v1/`, `/Game/Golmok/Materials/M_ZoneScan` (LFS, 커밋 여부는 용량 보고 결정) |
| 스크린샷·컨택트 시트 | `<Project>\Saved\Screenshots\Golmok\` |
| CSV·-game 로그·리포트 템플릿 | `<Project>\Saved\Golmok\spike\` |
| 시점·경로 | `Config\Golmok\Viewpoints\<레벨>.json`(커밋), `Saved\Golmok\Paths\walk_01.json`(커밋 권장: 재측정용) |

## 4. 기록 (PC 세션이 작성)
| 항목 | 실측·관찰 |
|---|---|
| 촬영 ID / 사진 수 / 영상 분 | |
| S2 RealityScan 시간(정렬/메시/텍스처), 출력 tri·UDIM 장수, 좌표계 메뉴 이름 [미확인] | |
| S3 XMP를 Postshot이 읽었는가 [미확인] | |
| S4 Postshot 설정·시간·splat 수·VRAM 상한 위반 여부 | |
| S5 splat 좌표계가 메시와 같았는가 [미확인] | |
| S5 splat clean 옵션·결과 JSON의 `floaters`·`low_opacity`·`too_large`·`removed`/`input`(floaters 5% 초과 시 `--std` 조정값) | |
| S7 route·매핑(`import_result.json`), UDIM 병합 표기, VT 켜짐, 임포트 시간 | |
| S8/S9 성공 여부·플러그인 버전 | |
| S11 캡처 수(saved/missing), 해상도 | |
| S12 CSV 프레임 수·`golmok-perf` 표 | |
| 막힌 곳과 택한 대안 | |
