# Golmok — notes for Claude sessions

Read `docs/ROADMAP.md` and `docs/DECISIONS.md` first; they are the source of truth. Then `docs/DEVELOPMENT-PLAN.md` (how the work is split and verified) and `docs/plan/STATUS.md` (current state). Docs are in Korean.

## Work-package sessions
- Phase 1 cloud work is done as work packages `docs/plan/WP-*.md`, one session each, in order, on branch `claude/hopeful-allen-f0a0jb` (see DEVELOPMENT-PLAN §7).
- A session marks its WP in `docs/plan/STATUS.md` on start and end, fills the WP doc's "결과" section, and leaves a PC verification runbook (`docs/runbooks/pc-verify-<wp>.md`) when the output needs the Unreal editor.
- **Model policy (owner, 2026-09-27, mandatory; replaces the 2026-09-24 rule)**: **coding runs on Claude Opus 5.5 with ultracode** (multi-agent workflows: implement → adversarial verify; this covers UE C++, editor Python, tools, tests, runbooks, CI fixes and code review of Astra PRs). **Only game design uses Claude Fable 5.1**: the design panel and design sections of a WP ("설계 (확정)"), game-feel/visual-quality judgement (look verification, spike verdicts, polish decisions, D-0xx proposals) and the design part of an Astra PR review. A WP session is therefore Opus ultracode; when its WP has a design step, the orchestrator runs that step on Fable first (or in a Fable design sub-session) and hands the confirmed design to the Opus session. Research, downloads, docs and simple tooling/CI may use Sonnet or Opus at the orchestrator's discretion. Astra (owner, 2026-09-26) implements in its own lanes; its PRs get an Opus ultracode adversarial code review before merge, plus a Fable design review when the PR changes game design or quality hypotheses. History: WP-04~09 and WP-12 ran on Fable ultracode under the old rule.
- Cloud sessions cannot build UE or reach real captures. UE code is "🟡 코드 완료·PC 검증 대기" until the PC session passes the runbook.

## Working alongside ChatGPT Astra (owner, 2026-09-26)
- ChatGPT Astra also implements work, including UE C++, in its own **lanes** (DEVELOPMENT-PLAN §7.6; its rules are in `AGENTS.md`). Lane 1 is WP-18 characters: `Source/Golmok/Characters/`, `Config/Golmok/characters.json` and the files listed in §7.6.
- Astra works on `astra/*` branches and never merges. Do not commit to `astra/*` branches, and do not edit files in an Astra lane. Ask through the PR or the owner instead. There is one exception. After owner approval, and once Astra has stopped pushing, the merging Fable session adds one final commit `WP-NN: 병합 시 반영 (Fable)` on the Astra branch. That commit carries the review summary and the PR's "병합 시 반영" text for the shared docs. Then it merges with a merge commit (§7.6).
- Hot-spot code/config files (§7.6: `Player/GolmokCharacter`, `Player/GolmokPlayerController`, `GolmokGameMode`, `Golmok.Build.cs`, `Config/Default*.ini`, `tools/pyproject.toml`, CI, `check_repo.py`, and the registry tests `CONSOLE_COMMANDS`/`BUILD_CS_*` in `tools/tests/test_ue_wp09_fixture.py` and `CONVENTION_FOLDERS` in `tools/tests/test_ue_zone_fixture.py`, …): prefer designs that do not touch them. Otherwise add marked hook blocks in a separate commit: `// [WP-NN hook]` … `// [/WP-NN hook]`, with class members placed before `};`, or `# [WP-NN hook]` on a Python list line. Never reformat or reorder existing lines. In the unity build, put file-scope helpers in a named namespace. Shared docs (STATUS/DECISIONS/ROADMAP/DEVELOPMENT-PLAN) are edited only by Claude sessions, in place as before (§7.2) and only in your own rows, never with hook markers. Astra's rows live in STATUS's "병행 트랙" section.
- Before starting and before a PR, check open branches for overlaps (`git diff --stat origin/main...origin/<branch>`). Whoever merges second resolves conflicts on its own branch with the §7.6 table: the lane owner's version wins, hook blocks keep both sides, shared docs take main and then re-add your own rows, and fixtures are regenerated.
- Before merge, an Astra PR gets an Opus ultracode adversarial code review, plus a Fable design review when it touches game design (use the template in §7.6). PC runbook verification happens after merge, at 🟡, the same as for Claude WPs.

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
- Python tools: `cd tools && pip install -e ".[basemap,zone,mesh,splat,align,dev]" && ruff check . && ruff format --check . && pytest -q && python scripts/check_repo.py` (same checks as CI)
- UE (Windows PowerShell): `.\tools\ue\build.ps1`, `.\tools\ue\open-editor.ps1`, `.\tools\ue\package.ps1`
- UE headless tests: `.\tools\ue\test.ps1 [-SetupDevLevel]` (automation `Golmok.*`); mannequin: `.\tools\ue\add-mannequin.ps1`
- Dev level (editor Python): `import golmok.setup_dev_level as s; s.run()`
- Basemap: `golmok-basemap inspect|build …`, then editor `import golmok.basemap_import as b; b.run(r"<out>")`
- Review viewer: `golmok-viewer <basemap folder>`; `cd tools/viewer && npm install && npm test` (headless smoke)
- Look-dev/spike: `golmok.lighting.apply("overcast_morning")`, `golmok.viewpoints.save/capture`, `golmok-perf <csv>`
