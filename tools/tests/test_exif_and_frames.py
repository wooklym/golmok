from pathlib import Path

import numpy as np
import piexif
import pytest
from PIL import Image

from golmok_tools.exif import read_exif
from golmok_tools.exif_report import fmt_shutter, lens_class, main, parse_shutter, summarize, collect
from golmok_tools.extract_frames import best_per_window, sharpness


def make_jpeg(path: Path, exposure=(1, 250), iso=400, f35=24, gps=True, size=(64, 48),
              when="2026:10:01 06:45:00"):
    exif = {
        "0th": {piexif.ImageIFD.Make: b"Apple", piexif.ImageIFD.Model: b"iPhone 17 Pro"},
        "Exif": {
            piexif.ExifIFD.ExposureTime: exposure,
            piexif.ExifIFD.ISOSpeedRatings: iso,
            piexif.ExifIFD.FocalLength: (6765, 1000),
            piexif.ExifIFD.FocalLengthIn35mmFilm: f35,
            piexif.ExifIFD.PixelXDimension: size[0],
            piexif.ExifIFD.PixelYDimension: size[1],
            piexif.ExifIFD.DateTimeOriginal: when.encode(),
            piexif.ExifIFD.LensModel: b"iPhone 17 Pro back triple camera",
        },
        "GPS": {},
    }
    if gps:
        exif["GPS"] = {
            piexif.GPSIFD.GPSLatitudeRef: b"N",
            piexif.GPSIFD.GPSLatitude: ((37, 1), (33, 1), (36, 1)),
            piexif.GPSIFD.GPSLongitudeRef: b"E",
            piexif.GPSIFD.GPSLongitude: ((126, 1), (55, 1), (12, 1)),
            piexif.GPSIFD.GPSAltitudeRef: 0,
            piexif.GPSIFD.GPSAltitude: (3500, 100),
        }
    Image.new("RGB", size, (120, 120, 120)).save(path, exif=piexif.dump(exif))


def test_read_exif_parses_fields(tmp_path: Path):
    p = tmp_path / "a.jpg"
    make_jpeg(p)
    info = read_exif(p)
    assert info.model == "iPhone 17 Pro"
    assert info.exposure_time == pytest.approx(1 / 250)
    assert info.iso == 400
    assert info.focal_35mm == 24
    assert info.lat == pytest.approx(37.56, abs=1e-3)
    assert info.lon == pytest.approx(126.92, abs=1e-3)
    assert info.alt == pytest.approx(35.0)
    assert info.datetime_original.hour == 6


def test_shutter_helpers():
    assert parse_shutter("1/200") == pytest.approx(0.005)
    assert fmt_shutter(1 / 125) == "1/125"
    assert fmt_shutter(2.0) == "2s"


def test_summary_flags_slow_other_lens_and_missing_gps(tmp_path: Path):
    make_jpeg(tmp_path / "ok.jpg")
    make_jpeg(tmp_path / "slow.jpg", exposure=(1, 60))
    make_jpeg(tmp_path / "uw.jpg", f35=13)
    make_jpeg(tmp_path / "nogps.jpg", gps=False)
    infos = collect(tmp_path)
    s = summarize(infos, parse_shutter("1/200"))
    assert s["total"] == 4
    assert s["shutter_ok"] == 3
    assert [Path(i.file).name for i in s["slow"]] == ["slow.jpg"]
    assert s["lenses"] == {"main-1x": 3, "ultra-wide": 1}
    assert s["no_gps"] == 1
    assert lens_class(infos[0]) in {"main-1x", "ultra-wide"}


def test_cli_runs(tmp_path: Path, capsys):
    make_jpeg(tmp_path / "a.jpg")
    assert main([str(tmp_path), "--csv", str(tmp_path / "r.csv")]) == 0
    assert "사진 1장" in capsys.readouterr().out
    assert (tmp_path / "r.csv").exists()


def test_best_per_window():
    assert best_per_window([1, 5, 2, 9, 0, 3, 7], 3) == [1, 3, 6]
    with pytest.raises(ValueError):
        best_per_window([1], 0)


def test_sharpness_prefers_detail():
    flat = np.full((64, 64, 3), 128, np.uint8)
    rng = np.random.default_rng(0)
    busy = rng.integers(0, 255, (64, 64, 3), dtype=np.uint8)
    assert sharpness(busy) > sharpness(flat)
