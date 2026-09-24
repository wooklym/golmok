# Golmok — notes for Claude sessions

Read `docs/ROADMAP.md` and `docs/DECISIONS.md` first; they are the source of truth. Then `docs/DEVELOPMENT-PLAN.md` (how the work is split and verified) and `docs/plan/STATUS.md` (current state). Docs are in Korean.

## Work-package sessions
- Phase 1 cloud work is done as work packages `docs/plan/WP-*.md`, one session each, in order, on branch `claude/hopeful-allen-f0a0jb` (see DEVELOPMENT-PLAN §7).
- A session marks its WP in `docs/plan/STATUS.md` on start and end, fills the WP doc's "결과" section, and leaves a PC verification runbook (`docs/runbooks/pc-verify-<wp>.md`) when the output needs the Unreal editor.
- Cloud sessions cannot build UE or reach real captures. UE code is "🟡 코드 완료·PC 검증 대기" until the PC session passes the runbook.

## Rules from the owner
- Research and design before code; get approval for anything that costs money or picks a stack/data source.
- Don't guess about licenses, API terms or law — verify and cite the source. Record decisions in `docs/DECISIONS.md`, progress in `docs/ROADMAP.md`.
- **Quality first** (game visuals) over difficulty and cost.
- When captures are needed, give a concrete guide (where, how, how many); see `docs/capture/`.

## Engineering conventions
- Unreal Engine **5.8.3** (Launcher build, no engine source changes). Game logic in **C++** (`unreal/Golmok/Source/Golmok`), editor automation in **Unreal Python** (`unreal/Golmok/Content/Python/golmok`). Keep Blueprints to the unavoidable minimum.
- Create input actions/mapping contexts in C++ rather than binary assets where practical.
- `.uasset`/`.umap` are Git LFS + lockable. Never commit raw captures, `.ply`, RealityScan projects or model weights.
- Licenses (D-002): no non-commercial code/weights (Inria 3DGS family, MASt3R/DUSt3R, InsightFace weights, …) and no AGPL tools (Ultralytics, OpenMVS, OpenSplat) in the product pipeline.
- Privacy (docs/research/05): every image is blurred with `golmok-blur` before RealityScan/Postshot.

## Commands
- Python tools: `cd tools && pip install -e ".[dev]" && pytest`
- UE (Windows PowerShell): `.\tools\ue\build.ps1`, `.\tools\ue\open-editor.ps1`, `.\tools\ue\package.ps1`
- Dev level (editor Python): `import golmok.setup_dev_level as s; s.run()`
- Basemap: `golmok-basemap inspect|build …`, then editor `import golmok.basemap_import as b; b.run(r"<out>")`
- Review viewer: `golmok-viewer <basemap folder>`; `cd tools/viewer && npm install && npm test` (headless smoke)
- Look-dev/spike: `golmok.lighting.apply("overcast_morning")`, `golmok.viewpoints.save/capture`, `golmok-perf <csv>`
