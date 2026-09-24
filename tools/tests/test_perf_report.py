from pathlib import Path

import pytest

from golmok_tools.perf_report import main, read_csv, summarize, to_markdown


def write_csv(path: Path, frame_ms, gpu_ms=None):
    header = ["FrameTime", "GameThreadTime", "RenderThreadTime"] + (["GPU/Total"] if gpu_ms else [])
    lines = [",".join(header)]
    for i, f in enumerate(frame_ms):
        row = [f"{f}", "4.0", "5.0"] + ([f"{gpu_ms[i]}"] if gpu_ms else [])
        lines.append(",".join(row))
    lines.append("[HasHeaderRowAtEnd],1,[platform],Windows")
    lines.append(",".join(header))
    path.write_text("\n".join(lines), encoding="utf-8")


def test_summary_skips_warmup_and_computes_fps(tmp_path):
    # 1 s of 100 ms hitches (warm-up) then 10 s at 60 fps with a few 33 ms frames
    frames = [100.0] * 10 + [16.667] * 590 + [33.333] * 10
    write_csv(tmp_path / "a.csv", frames, gpu_ms=[12.0] * len(frames))
    s = summarize(read_csv(tmp_path / "a.csv"), "a", skip_seconds=2.0)
    assert s.fps_avg == pytest.approx(59.0, abs=1.5)
    assert s.fps_1pct_low == pytest.approx(30.0, abs=1.0)
    assert s.gpu_ms == pytest.approx(12.0)
    assert "| a |" in to_markdown([s])


def test_long_loading_frame_is_dropped_as_warmup(tmp_path):
    # Boot captures (-csvCaptureFrames) start with the map load as one multi-second frame.
    write_csv(tmp_path / "boot.csv", [7500.0] + [10.0] * 1000)
    s = summarize(read_csv(tmp_path / "boot.csv"), "boot", skip_seconds=2.0)
    assert s.frames == 1000
    assert s.fps_avg == pytest.approx(100.0)
    assert s.fps_1pct_low <= s.fps_avg


def test_ue58_layout_with_events_column_and_huge_fields(tmp_path):
    # UE 5.8 captures: EVENTS first column, event text in some rows, a trailing header row and a
    # metadata row; event fields can exceed the csv module's default 128 KiB field limit.
    header = ["EVENTS", "FrameTime", "GameThreadTime", "RenderThreadTime", "GPUTime"]
    rows = [",".join(header)]
    for i in range(600):
        event = '"' + "x" * 200_000 + '"' if i == 5 else ""
        rows.append(f"{event},10.0,4.0,5.0,8.0")
    rows.append(",".join(header))
    rows.append("[HasHeaderRowAtEnd],1,[EventTimestamps],1,[platform],Windows")
    (tmp_path / "ue.csv").write_text("\n".join(rows), encoding="utf-8")
    cols = read_csv(tmp_path / "ue.csv")
    assert len(cols["frame"]) == 600
    s = summarize(cols, "ue", skip_seconds=0.0)
    assert s.fps_avg == pytest.approx(100.0)
    assert s.gpu_ms == pytest.approx(8.0)


def test_missing_frame_column(tmp_path):
    (tmp_path / "b.csv").write_text("Foo,Bar\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_csv(tmp_path / "b.csv")


def test_cli(tmp_path, capsys):
    write_csv(tmp_path / "c.csv", [16.0] * 500)
    assert main([str(tmp_path / "c.csv"), "--label", "mesh", "--markdown"]) == 0
    assert "| mesh |" in capsys.readouterr().out
