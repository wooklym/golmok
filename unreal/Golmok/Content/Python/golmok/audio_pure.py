"""WP-13 audio manifest and import/credit plan; usable without Unreal."""

import json
import math
import re
import wave
from datetime import date
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[3]
CONFIG = PROJECT / "Config/Golmok/audio.json"
AUDIO = PROJECT / "Content/Golmok/Audio"


def number(value, low, high, field):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{field}: expected finite number in [{low}, {high}]: {value!r}")
    return value


def text(value, field):
    if not isinstance(value, str) or not value.strip() or any(c in value for c in "\r\n\t|"):
        raise ValueError(f"{field}: expected nonempty single-line text without table separators")
    return value


def key_case(data, names, prefix=""):
    """Reject aliases of runtime-known keys; extension keys and dynamic IDs stay untouched."""
    canonical = {name.lower(): name for name in names}
    for key in data:
        expected = canonical.get(key.lower()) if isinstance(key, str) else None
        if expected is not None and key != expected:
            field = f"{prefix}.{key}" if prefix else key
            raise ValueError(f"{field}: expected {expected}")


def parse_config(data):
    """Reject invalid manifests before generating files or touching editor assets."""
    if not isinstance(data, dict):
        raise ValueError("$: expected object")
    key_case(
        data,
        (
            "schema_version",
            "master_volume",
            "crossfade_seconds",
            "pause_policy",
            "photo_mute_fade_seconds",
            "crossfade_seconds_by_state",
            "assets",
            "ambience",
            "preset_states",
            "footsteps",
            "rain",
        ),
    )
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("schema_version: expected integer 1")
    number(data.get("master_volume"), 0, 1, "master_volume")
    number(data.get("crossfade_seconds"), 0, 30, "crossfade_seconds")
    number(data.get("photo_mute_fade_seconds", 0.25), 0, 5, "photo_mute_fade_seconds")
    durations = data.get("crossfade_seconds_by_state", {})
    if not isinstance(durations, dict):
        raise ValueError("crossfade_seconds_by_state: expected object")
    key_case(durations, ("outdoor_day", "outdoor_night", "interior"), "crossfade_seconds_by_state")
    for state, duration in durations.items():
        if state not in ("outdoor_day", "outdoor_night", "interior"):
            raise ValueError(f"crossfade_seconds_by_state.{state}: expected known destination state")
        number(duration, 0, 30, f"crossfade_seconds_by_state.{state}")
    if data.get("pause_policy") not in ("mute", "maintain"):
        raise ValueError("pause_policy: expected mute or maintain")
    assets = data.get("assets")
    if not isinstance(assets, dict) or not assets:
        raise ValueError("assets: expected nonempty object")
    paths, sources = set(), set()
    for key, item in assets.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,47}", key):
            raise ValueError(f"assets.{key}: expected lowercase asset id")
        prefix = f"assets.{key}"
        if not isinstance(item, dict):
            raise ValueError(f"{prefix}: expected object")
        key_case(
            item,
            (
                "asset",
                "loop",
                "gain",
                "title",
                "author",
                "source_url",
                "verified",
                "license",
                "changes",
                "license_url",
                "placeholder",
            ),
            prefix,
        )
        source = text(item.get("source"), f"{prefix}.source")
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
            raise ValueError(f"{prefix}.source: expected src/<category>/<name>.wav")
        asset = text(item.get("asset"), f"{prefix}.asset")
        if not re.fullmatch(
            r"/Game/Golmok/Audio/[A-Za-z0-9_]+/SW_[A-Za-z0-9_]+\.SW_[A-Za-z0-9_]+",
            asset,
        ):
            raise ValueError(f"{prefix}.asset: expected audio object path")
        if asset.rsplit("/", 1)[1].split(".")[0] != asset.rsplit(".", 1)[1]:
            raise ValueError(f"{prefix}.asset: expected matching object and package name")
        if asset.casefold() in paths or source.casefold() in sources:
            raise ValueError(f"{prefix}: expected unique asset and source")
        paths.add(asset.casefold())
        sources.add(source.casefold())
        for field in ("title", "author", "source_url", "changes"):
            text(item.get(field), f"{prefix}.{field}")
        if not item["source_url"].startswith("https://"):
            raise ValueError(f"{prefix}.source_url: expected HTTPS URL")
        if item.get("license") not in ("CC0-1.0", "CC-BY-4.0", "project-generated"):
            raise ValueError(f"{prefix}.license: expected approved audio license")
        for field in ("placeholder", "loop"):
            if type(item.get(field)) is not bool:
                raise ValueError(f"{prefix}.{field}: expected booleans (JSON true or false)")
        if item["license"] == "project-generated":
            if not item["placeholder"]:
                raise ValueError(f"{prefix}.placeholder: expected true for project-generated audio")
            if item.get("license_url") != "":
                raise ValueError(f"{prefix}.license_url: expected empty string for project-generated audio")
            if type(item.get("seed")) is not int or not 0 <= item["seed"] <= 2**32 - 1:
                raise ValueError(f"{prefix}.seed: expected integer in [0, 4294967295]")
        else:
            expected = {
                "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
                "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
            }[item["license"]]
            if item.get("license_url") != expected:
                raise ValueError(f"{prefix}.license_url: expected URL matching declared license")
        for supplied in item:
            for canonical in ("source", "seed", "synthesis", "seconds"):
                if supplied.lower() == canonical and supplied != canonical:
                    raise ValueError(f"{prefix}.{supplied}: expected {canonical}")
        # Python-only generator selection; adopted audio may retain this inert metadata.
        synthesis = item.get("synthesis", "default")
        if not isinstance(synthesis, str) or synthesis not in ("default", "rain"):
            raise ValueError(f"{prefix}.synthesis: expected default or rain")
        if item["license"] == "project-generated" and synthesis == "rain" and not item["loop"]:
            raise ValueError(f"{prefix}.synthesis: rain requires a loop")
        if "seconds" in item:
            if type(item["seconds"]) is not int or not 16 <= item["seconds"] <= 30:
                raise ValueError(f"{prefix}.seconds: expected integer in [16, 30]")
            if item["license"] == "project-generated" and (synthesis != "rain" or not item["loop"]):
                raise ValueError(f"{prefix}.seconds: only supported for rain loops")
        verified = item.get("verified")
        if not isinstance(verified, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", verified):
            raise ValueError(f"{prefix}.verified: expected YYYY-MM-DD")
        try:
            date.fromisoformat(verified)
        except ValueError as exc:
            raise ValueError(f"{prefix}.verified: expected valid calendar date") from exc
        number(item.get("gain"), 0, 1, f"{prefix}.gain")
    if "rain" in data:
        rain = data["rain"]
        if not isinstance(rain, dict):
            raise ValueError("rain: expected object")
        key_case(rain, ("asset", "gain_curve", "interior_gain"), "rain")
        asset = text(rain.get("asset"), "rain.asset")
        if asset not in assets or not assets[asset]["loop"]:
            raise ValueError("rain.asset: expected looping asset id")
        number(rain.get("interior_gain"), 0, 1, "rain.interior_gain")
        curve = rain.get("gain_curve")
        if not isinstance(curve, list) or not 2 <= len(curve) <= 32:
            raise ValueError("rain.gain_curve: expected 2..32 [intensity, gain] points")
        previous = previous_gain = -1
        for point in curve:
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError("rain.gain_curve: expected [intensity, gain]")
            x = number(point[0], 0, 1, "rain.gain_curve.intensity")
            gain = number(point[1], 0, 1, "rain.gain_curve.gain")
            if x <= previous:
                raise ValueError("rain.gain_curve: expected strictly increasing intensities")
            if gain < previous_gain:
                raise ValueError("rain.gain_curve: expected nondecreasing gains")
            previous, previous_gain = x, gain
        if curve[0] != [0, 0] or curve[-1][0] != 1:
            raise ValueError("rain.gain_curve: expected first point [0, 0] and final intensity 1")
    if isinstance(data.get("ambience"), dict):
        key_case(data["ambience"], ("outdoor_day", "outdoor_night", "interior"), "ambience")
    if not isinstance(data.get("ambience"), dict) or set(data["ambience"]) != {
        "outdoor_day",
        "outdoor_night",
        "interior",
    }:
        raise ValueError("ambience: expected three ambience states")
    for state, key in data["ambience"].items():
        text(key, f"ambience.{state}")
        if key not in assets or not assets[key]["loop"]:
            raise ValueError(f"ambience.{state}: expected looping asset id")
    if not isinstance(data.get("preset_states"), dict):
        raise ValueError("preset_states: expected object")
    for preset, state in data["preset_states"].items():
        text(preset, "preset_states.<key>")
        text(state, f"preset_states.{preset}")
        if state not in ("outdoor_day", "outdoor_night"):
            raise ValueError(f"preset_states.{preset}: expected outdoor state")
    steps = data.get("footsteps")
    if not isinstance(steps, dict):
        raise ValueError("footsteps: expected object")
    key_case(
        steps,
        (
            "driver",
            "walk_stride_cm",
            "run_stride_cm",
            "run_threshold_cm_s",
            "teleport_threshold_cm",
            "pitch_range",
            "volume_range",
            "landing",
            "stride_cm_by_character",
            "sets",
            "surface_sets",
        ),
        "footsteps",
    )
    for field in (
        "walk_stride_cm",
        "run_stride_cm",
        "run_threshold_cm_s",
        "teleport_threshold_cm",
    ):
        number(steps.get(field), 1, 10000, f"footsteps.{field}")
    if any(key.lower() == "stride_scale_by_mesh" for key in steps):
        raise ValueError(
            "footsteps.stride_scale_by_mesh: expected absent; superseded by stride_cm_by_character"
        )
    driver = steps.get("driver", "auto")
    if not isinstance(driver, str) or driver not in ("auto", "distance", "notify"):
        raise ValueError("footsteps.driver: expected auto, distance or notify")
    strides = steps.get("stride_cm_by_character", {})
    if not isinstance(strides, dict):
        raise ValueError("footsteps.stride_cm_by_character: expected object")
    for character, pair in strides.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,47}", character):
            raise ValueError(f"footsteps.stride_cm_by_character.{character}: expected lowercase character id")
        if isinstance(pair, dict):
            key_case(pair, ("walk", "run"), f"footsteps.stride_cm_by_character.{character}")
        if not isinstance(pair, dict) or set(pair) != {"walk", "run"}:
            raise ValueError(f"footsteps.stride_cm_by_character.{character}: expected walk and run object")
        number(pair["walk"], 1, 10000, f"footsteps.stride_cm_by_character.{character}.walk")
        number(pair["run"], 1, 10000, f"footsteps.stride_cm_by_character.{character}.run")
    for field, low, high in (("pitch_range", 0.5, 2), ("volume_range", 0, 1)):
        values = steps.get(field)
        if not isinstance(values, list) or len(values) != 2:
            raise ValueError(f"footsteps.{field}: expected array of two numbers")
        number(values[0], low, high, f"footsteps.{field}[0]")
        number(values[1], values[0], high, f"footsteps.{field}[1]")
    sets = steps.get("sets")
    if not isinstance(sets, dict):
        raise ValueError("footsteps.sets: expected object")
    if not {"default", "asphalt", "tile", "stairs"} <= sets.keys():
        raise ValueError("footsteps.sets: expected default/asphalt/tile/stairs sets")
    refs = [(steps.get("landing"), "footsteps.landing")]
    for name, samples in sets.items():
        if not isinstance(samples, list) or not samples:
            raise ValueError(f"footsteps.sets.{name}: expected nonempty array")
        refs.extend((sample, f"footsteps.sets.{name}[{index}]") for index, sample in enumerate(samples))
    for key, field in refs:
        text(key, field)
        if key not in assets or assets[key]["loop"]:
            raise ValueError(f"{field}: expected one-shot asset id")
    surfaces = steps.get("surface_sets")
    if not isinstance(surfaces, dict):
        raise ValueError("footsteps.surface_sets: expected object")
    for surface, name in surfaces.items():
        text(name, f"footsteps.surface_sets.{surface}")
        if not re.fullmatch(r"[0-9]+", surface) or not 0 <= int(surface) <= 62 or name not in sets:
            raise ValueError(f"footsteps.surface_sets.{surface}: expected surface 0..62 mapped to set id")
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
            if wav.getcomptype() != "NONE" or wav.getsampwidth() != 2 or wav.getframerate() != 48000:
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
            f"Verified: {item['verified']}",
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
