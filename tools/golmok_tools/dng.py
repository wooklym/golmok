"""Read which compression a DNG's main image uses, without decoding it.

iPhone 16 Pro / 17 Pro can store ProRAW as JPEG lossless (the original format) or as JPEG-XL
(DNG 1.7, lossless or lossy; Settings > Camera > Formats > ProRAW Format). LibRaw decodes JPEG-XL
DNG only when built with the Adobe DNG SDK, which the rawpy wheels are not, so golmok-exif reports
the format and golmok-blur explains the failure instead of a bare LibRaw error.
"""

from __future__ import annotations

import struct
from pathlib import Path

JPEG = 7  # lossless JPEG in DNG (original ProRAW)
JPEG_XL = 52546  # DNG 1.7

COMPRESSION_NAMES = {
    1: "uncompressed",
    JPEG: "jpeg-lossless",
    8: "deflate",
    34892: "lossy-jpeg",
    JPEG_XL: "jpeg-xl",
}

_TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8, 13: 4}
_NEW_SUBFILE_TYPE, _WIDTH, _HEIGHT, _COMPRESSION, _SUB_IFDS = 254, 256, 257, 259, 330
_MAX_IFDS = 64


def compression_name(code: int | None) -> str | None:
    if code is None:
        return None
    return COMPRESSION_NAMES.get(code, str(code))


def read_ifds(path: Path) -> list[dict]:
    """All IFDs (IFD0 chain and SubIFDs) as {subfile_type, width, height, compression}.

    Seeks to the directories only, so a 75 MB ProRAW costs a few KB of reads.
    """
    with open(path, "rb") as f:

        def read(at: int, fmt: str) -> tuple:
            f.seek(at)
            buf = f.read(struct.calcsize(fmt))
            if len(buf) < struct.calcsize(fmt):
                raise ValueError("truncated TIFF/DNG file")
            return struct.unpack(fmt, buf)

        f.seek(0)
        magic = f.read(2)
        if magic == b"II":
            order = "<"
        elif magic == b"MM":
            order = ">"
        else:
            raise ValueError("not a TIFF/DNG file")
        version, first = read(2, order + "HI")
        if version != 42:
            raise ValueError("not a classic TIFF/DNG file")

        def values(entry: int, typ: int, count: int) -> list[int]:
            if typ not in (3, 4, 13) or count == 0 or count > 1024:
                return []
            at = entry + 8
            if _TYPE_SIZES[typ] * count > 4:
                (at,) = read(at, order + "I")
            return list(read(at, order + ("H" if typ == 3 else "I") * count))

        ifds: list[dict] = []
        pending = [first]
        seen: set[int] = set()
        while pending and len(ifds) < _MAX_IFDS:
            offset = pending.pop(0)
            if offset == 0 or offset in seen:
                continue
            seen.add(offset)
            (count,) = read(offset, order + "H")
            ifd = {"subfile_type": 0, "width": None, "height": None, "compression": None}
            for i in range(count):
                entry = offset + 2 + 12 * i
                tag, typ, n = read(entry, order + "HHI")
                if tag == _SUB_IFDS:
                    pending.extend(values(entry, typ, n))
                    continue
                key = {
                    _NEW_SUBFILE_TYPE: "subfile_type",
                    _WIDTH: "width",
                    _HEIGHT: "height",
                    _COMPRESSION: "compression",
                }.get(tag)
                if key and n == 1:
                    vals = values(entry, typ, 1)
                    if vals:
                        ifd[key] = vals[0]
            ifds.append(ifd)
            (next_offset,) = read(offset + 2 + 12 * count, order + "I")
            pending.append(next_offset)
    return ifds


def raw_compression(path: Path) -> int | None:
    """Compression of the full-resolution image (NewSubfileType 0, largest if several)."""
    main = [i for i in read_ifds(path) if i["subfile_type"] == 0 and i["compression"] is not None]
    if not main:
        return None
    main.sort(key=lambda i: (i["width"] or 0) * (i["height"] or 0), reverse=True)
    return main[0]["compression"]


def is_jpeg_xl(path: Path) -> bool:
    try:
        return raw_compression(path) == JPEG_XL
    except (OSError, ValueError, struct.error):
        return False
