import struct
from pathlib import Path

import pytest

from golmok_tools import dng
from golmok_tools.exif_report import collect, parse_shutter, render, summarize
from golmok_tools.imageio import DecodeError, read_image


def make_dng(path: Path, main_compression: int, little: bool = True) -> Path:
    """Directory layout of an Apple ProRAW DNG (no pixel data): IFD0 = preview, SubIFD0 = 48MP main
    image, SubIFD1 = a semantic mask."""
    e = "<" if little else ">"

    def ifd(entries):
        out = struct.pack(e + "H", len(entries))
        for tag, typ, count, value in sorted(entries):
            field = struct.pack(e + "HH", value, 0) if typ == 3 else struct.pack(e + "I", value)
            out += struct.pack(e + "HHI", tag, typ, count) + field
        return out + struct.pack(e + "I", 0)

    def size(n):
        return 2 + 12 * n + 4

    ifd0_at = 8
    subifd_array_at = ifd0_at + size(5)
    sub0_at = subifd_array_at + 8
    sub1_at = sub0_at + size(4)
    data = (b"II" if little else b"MM") + struct.pack(e + "HI", 42, ifd0_at)
    data += ifd([(254, 4, 1, 1), (256, 4, 1, 1008), (257, 4, 1, 756), (259, 3, 1, dng.JPEG), (330, 4, 2, subifd_array_at)])
    data += struct.pack(e + "II", sub0_at, sub1_at)
    data += ifd([(254, 4, 1, 0), (256, 4, 1, 8064), (257, 4, 1, 6048), (259, 3, 1, main_compression)])
    data += ifd([(254, 4, 1, 4), (256, 4, 1, 2016), (257, 4, 1, 1512), (259, 3, 1, main_compression)])
    path.write_bytes(data)
    return path


@pytest.mark.parametrize("little", [True, False])
def test_raw_compression_reads_main_image_in_subifd(tmp_path: Path, little: bool):
    p = make_dng(tmp_path / "a.dng", dng.JPEG_XL, little)
    ifds = dng.read_ifds(p)
    assert [i["subfile_type"] for i in ifds] == [1, 0, 4]
    assert dng.raw_compression(p) == dng.JPEG_XL
    assert dng.is_jpeg_xl(p)
    assert dng.raw_compression(make_dng(tmp_path / "b.dng", dng.JPEG, little)) == dng.JPEG


def test_is_jpeg_xl_false_for_non_tiff(tmp_path: Path):
    p = tmp_path / "x.dng"
    p.write_bytes(b"not a tiff at all")
    assert not dng.is_jpeg_xl(p)
    assert dng.compression_name(dng.JPEG_XL) == "jpeg-xl"
    assert dng.compression_name(12345) == "12345"


def test_exif_report_counts_formats_and_warns_on_jpeg_xl(tmp_path: Path):
    make_dng(tmp_path / "IMG_0001.dng", dng.JPEG)
    make_dng(tmp_path / "IMG_0002.dng", dng.JPEG_XL)
    s = summarize(collect(tmp_path), parse_shutter("1/200"))
    assert s["raw_formats"] == {"jpeg-lossless": 1, "jpeg-xl": 1}
    text = render(s, parse_shutter("1/200"))
    assert "ProRAW 압축: jpeg-lossless 1, jpeg-xl 1" in text
    assert "JPEG 무손실" in text


def test_jpeg_xl_dng_decode_error_explains_cause(tmp_path: Path):
    pytest.importorskip("rawpy")
    p = make_dng(tmp_path / "IMG_0002.dng", dng.JPEG_XL)
    with pytest.raises(DecodeError, match="JPEG-XL ProRAW"):
        read_image(p)
