"""Minimal EXIF reader (exifread) for capture QA and GPS priors."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import exifread

from .dng import compression_name, raw_compression


@dataclass
class ExifInfo:
    file: str
    make: str | None = None
    model: str | None = None
    lens_model: str | None = None
    exposure_time: float | None = None  # seconds
    iso: int | None = None
    focal_length: float | None = None  # mm (physical)
    focal_35mm: float | None = None  # mm (35mm equivalent)
    width: int | None = None
    height: int | None = None
    datetime_original: datetime | None = None
    lat: float | None = None
    lon: float | None = None
    alt: float | None = None
    raw_compression: int | None = None  # DNG main image compression (dng.JPEG / dng.JPEG_XL ...)

    @property
    def megapixels(self) -> float | None:
        if self.width and self.height:
            return self.width * self.height / 1e6
        return None

    def as_row(self) -> dict:
        row = asdict(self)
        row["datetime_original"] = self.datetime_original.isoformat() if self.datetime_original else None
        row["megapixels"] = round(self.megapixels, 1) if self.megapixels else None
        row["raw_compression"] = compression_name(self.raw_compression)
        return row


def _ratio(v) -> float | None:
    try:
        return float(v.num) / float(v.den) if v.den else None
    except AttributeError:
        try:
            return float(v)
        except (TypeError, ValueError):
            return None


def _first(tags, *keys):
    for k in keys:
        if k in tags:
            return tags[k]
    return None


def _num(tag) -> float | None:
    if tag is None:
        return None
    vals = tag.values
    if isinstance(vals, (list, tuple)):
        if not vals:
            return None
        vals = vals[0]
    return _ratio(vals)


def _dms(tag, ref) -> float | None:
    if tag is None:
        return None
    parts = [_ratio(v) for v in tag.values]
    if len(parts) != 3 or any(p is None for p in parts):
        return None
    value = parts[0] + parts[1] / 60 + parts[2] / 3600
    if ref is not None and str(ref.values).strip().upper() in {"S", "W"}:
        value = -value
    return value


def read_exif(path: Path) -> ExifInfo:
    with open(path, "rb") as f:
        tags = exifread.process_file(f, details=False)

    info = ExifInfo(file=str(path))
    make = _first(tags, "Image Make")
    model = _first(tags, "Image Model")
    lens = _first(tags, "EXIF LensModel")
    info.make = str(make).strip() if make else None
    info.model = str(model).strip() if model else None
    info.lens_model = str(lens).strip() if lens else None

    info.exposure_time = _num(_first(tags, "EXIF ExposureTime"))
    iso = _num(_first(tags, "EXIF ISOSpeedRatings", "EXIF PhotographicSensitivity"))
    info.iso = int(iso) if iso is not None else None
    info.focal_length = _num(_first(tags, "EXIF FocalLength"))
    info.focal_35mm = _num(_first(tags, "EXIF FocalLengthIn35mmFilm"))

    w = _num(_first(tags, "EXIF ExifImageWidth", "Image ImageWidth"))
    h = _num(_first(tags, "EXIF ExifImageLength", "Image ImageLength"))
    info.width = int(w) if w else None
    info.height = int(h) if h else None

    dt = _first(tags, "EXIF DateTimeOriginal", "Image DateTime")
    if dt:
        try:
            info.datetime_original = datetime.strptime(str(dt).strip(), "%Y:%m:%d %H:%M:%S")
        except ValueError:
            pass

    info.lat = _dms(_first(tags, "GPS GPSLatitude"), _first(tags, "GPS GPSLatitudeRef"))
    info.lon = _dms(_first(tags, "GPS GPSLongitude"), _first(tags, "GPS GPSLongitudeRef"))
    alt = _num(_first(tags, "GPS GPSAltitude"))
    alt_ref = _first(tags, "GPS GPSAltitudeRef")
    if alt is not None and alt_ref is not None and _num(alt_ref) == 1:
        alt = -alt
    info.alt = alt

    if path.suffix.lower() == ".dng":
        try:
            info.raw_compression = raw_compression(path)
        except (OSError, ValueError):
            pass
    return info
