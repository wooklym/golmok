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


def test_missing_frame_column(tmp_path):
    (tmp_path / "b.csv").write_text("Foo,Bar\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_csv(tmp_path / "b.csv")


def test_cli(tmp_path, capsys):
    write_csv(tmp_path / "c.csv", [16.0] * 500)
    assert main([str(tmp_path / "c.csv"), "--label", "mesh", "--markdown"]) == 0
    assert "| mesh |" in capsys.readouterr().out
