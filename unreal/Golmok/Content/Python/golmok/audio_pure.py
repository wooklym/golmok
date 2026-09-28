"""WP-13 audio manifest and import/credit plan; usable without Unreal."""

import json
import math
import re
import wave
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[3]
CONFIG = PROJECT / "Config/Golmok/audio.json"
AUDIO = PROJECT / "Content/Golmok/Audio"


def number(value, low, high):
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or not low <= value <= high
    ):
        raise ValueError(f"expected finite number in [{low}, {high}]: {value!r}")
    return value


def text(value):
    if (
        not isinstance(value, str)
        or not value.strip()
        or any(c in value for c in "\r\n\t|")
    ):
        raise ValueError("expected nonempty single-line text without table separators")
    return value


def parse_config(data):
    """Reject invalid manifests before generating files or touching editor assets."""
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("unsupported audio schema_version")
    number(data["master_volume"], 0, 1)
    number(data["crossfade_seconds"], 0, 30)
    durations = data.get("crossfade_seconds_by_state", {})
    if not isinstance(durations, dict):
        raise ValueError("crossfade_seconds_by_state must be an object")
    for state, duration in durations.items():
        if state not in ("outdoor_day", "outdoor_night", "interior"):
            raise ValueError("unknown crossfade destination state")
        number(duration, 0, 30)
    if data["pause_policy"] not in ("mute", "maintain"):
        raise ValueError("pause_policy must be mute or maintain")
    assets = data["assets"]
    if not isinstance(assets, dict) or not assets:
        raise ValueError("assets must be a nonempty object")
    paths, sources = set(), set()
    for key, item in assets.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,47}", key):
            raise ValueError("invalid asset id")
        source = text(item["source"])
        path = PurePosixPath(source)
        if (
            "\\" in source
            or ":" in source
            or path.is_absolute()
            or ".." in path.parts
            or len(path.parts) != 3
            or path.parts[0] != "src"
            or path.suffix != ".wav"
        ):
            raise ValueError("source must be src/<category>/<name>.wav")
        asset = text(item["asset"])
        if not re.fullmatch(
            r"/Game/Golmok/Audio/[A-Za-z0-9_]+/SW_[A-Za-z0-9_]+\.SW_[A-Za-z0-9_]+",
            asset,
        ):
            raise ValueError("invalid audio object path")
        if asset.rsplit("/", 1)[1].split(".")[0] != asset.rsplit(".", 1)[1]:
            raise ValueError("object and package name differ")
        if asset.casefold() in paths or source.casefold() in sources:
            raise ValueError("duplicate asset or source")
        paths.add(asset.casefold())
        sources.add(source.casefold())
        for field in ("title", "author", "source_url", "changes"):
            text(item[field])
        if not item["source_url"].startswith("https://"):
            raise ValueError("source_url must be HTTPS")
        if item["license"] not in ("CC0-1.0", "CC-BY-4.0", "project-generated"):
            raise ValueError("unapproved audio license")
        if type(item["placeholder"]) is not bool or type(item["loop"]) is not bool:
            raise ValueError("placeholder and loop must be booleans")
        if item["license"] == "project-generated":
            if not item["placeholder"] or item["license_url"] != "":
                raise ValueError("generated placeholder requires explicit provenance")
            if type(item["seed"]) is not int or not 0 <= item["seed"] <= 2**32 - 1:
                raise ValueError("invalid generator seed")
        else:
            expected = {
                "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
                "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
            }[item["license"]]
            if item["license_url"] != expected:
                raise ValueError("license URL does not match the declared license")
        number(item["gain"], 0, 1)
    if set(data["ambience"]) != {"outdoor_day", "outdoor_night", "interior"}:
        raise ValueError("three ambience states required")
    for key in data["ambience"].values():
        if key not in assets or not assets[key]["loop"]:
            raise ValueError("ambience must reference a looping asset")
    for preset, state in data["preset_states"].items():
        text(preset)
        if state not in ("outdoor_day", "outdoor_night"):
            raise ValueError("preset must map to an outdoor state")
    steps = data["footsteps"]
    for field in (
        "walk_stride_cm",
        "run_stride_cm",
        "run_threshold_cm_s",
        "teleport_threshold_cm",
    ):
        number(steps[field], 1, 10000)
    for field, low, high in (("pitch_range", 0.5, 2), ("volume_range", 0, 1)):
        values = steps[field]
        if not isinstance(values, list) or len(values) != 2:
            raise ValueError("range needs two values")
        number(values[0], low, high)
        number(values[1], values[0], high)
    if not {"default", "asphalt", "tile", "stairs"} <= steps["sets"].keys():
        raise ValueError("missing footstep set")
    refs = [steps["landing"]]
    for samples in steps["sets"].values():
        if not isinstance(samples, list) or not samples:
            raise ValueError("empty footstep set")
        refs.extend(samples)
    if any(key not in assets or assets[key]["loop"] for key in refs):
        raise ValueError("footsteps must reference one-shot assets")
    for surface, name in steps["surface_sets"].items():
        if (
            not re.fullmatch(r"[0-9]+", surface)
            or not 0 <= int(surface) <= 62
            or name not in steps["sets"]
        ):
            raise ValueError("invalid physical surface mapping")
    return data


def load_config(path=CONFIG):
    return parse_config(json.loads(Path(path).read_text(encoding="utf-8")))


def source_path(root, relative):
    root = Path(root).resolve()
    result = (root / relative).resolve()
    if not result.is_relative_to(root):
        raise ValueError("source escapes Audio directory")
    return result


def import_plan(data, root=AUDIO):
    parse_config(data)
    plan, total = [], 0
    for key, item in data["assets"].items():
        source = source_path(root, item["source"])
        size = source.stat().st_size
        if size > 5_000_000:
            raise ValueError(f"{key}: exceeds 5 MB")
        total += size
        with wave.open(str(source), "rb") as wav:
            if (
                wav.getcomptype() != "NONE"
                or wav.getsampwidth() != 2
                or wav.getframerate() != 48000
            ):
                raise ValueError(f"{key}: expected PCM16 48 kHz")
            if wav.getnchannels() not in (1, 2) or wav.getnframes() == 0:
                raise ValueError(f"{key}: empty/unsupported channel count")
            expected_bytes = wav.getnframes() * wav.getnchannels() * wav.getsampwidth()
            if len(wav.readframes(wav.getnframes())) != expected_bytes:
                raise ValueError(f"{key}: truncated PCM payload")
        package, name = item["asset"].rsplit("/", 1)
        plan.append(dict(id=key, folder=package, name=name.split(".")[0], **item))
        plan[-1]["source"] = str(source)
    if total > 40_000_000:
        raise ValueError("audio sources exceed 40 MB")
    return plan


def attribution(data):
    parse_config(data)
    lines = [
        "# Audio attribution",
        "",
        "Generated from Config/Golmok/audio.json; do not edit by hand.",
        "",
        "Project-generated means synthetic test audio, not a third-party license or CC0 dedication.",
        "",
    ]
    for key, item in data["assets"].items():
        lines += [
            f"## {key}: {item['title']}",
            "",
            f"Author: {item['author']}",
            f"Source: {item['source_url']}",
            f"License: {item['license']} {item['license_url']}".rstrip(),
            f"Changes: {item['changes']}",
            f"Placeholder: {item['placeholder']}",
            "",
        ]
    return "\n".join(lines)


def write_credits(data, root=AUDIO):
    content = attribution(data)
    root = Path(root)
    (root / "Credits").mkdir(parents=True, exist_ok=True)
    (root / "ATTRIBUTION.md").write_text(content, encoding="utf-8")
    (root / "Credits/audio-credits.txt").write_text(content, encoding="utf-8")
