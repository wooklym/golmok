"""Import audio.json sources and refresh both attribution and distribution credits.

    import golmok.audio_import as a; a.run()

Gain is the SoundWave volume multiplier, not destructive peak normalization.
Source conversion to PCM16/48 kHz is an explicit preprocessing step.
"""

import unreal

from .audio_pure import AUDIO, CONFIG, import_plan, load_config, write_credits


def run(config=CONFIG, root=AUDIO):
    data = load_config(config)
    plan = import_plan(
        data, root
    )  # Validate all sources before mutating any editor asset.
    tasks = []
    for item in plan:
        task = unreal.AssetImportTask()
        for key, value in {
            "filename": item["source"],
            "destination_path": item["folder"],
            "destination_name": item["name"],
            "automated": True,
            "replace_existing": True,
            "save": False,
        }.items():
            task.set_editor_property(key, value)
        tasks.append(task)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    imported = []
    for item, task in zip(plan, tasks, strict=True):
        paths = task.get_editor_property("imported_object_paths")
        if item["asset"] not in paths:
            raise RuntimeError(f"audio import failed: {item['id']} ({paths!r})")
        sound = unreal.load_asset(item["asset"])
        if not isinstance(sound, unreal.SoundWave):
            raise TypeError(f"not a SoundWave: {item['asset']}")
        sound.set_editor_property("looping", item["loop"])
        sound.set_editor_property("volume", item["gain"])
        if not unreal.EditorAssetLibrary.save_loaded_asset(
            sound, only_if_is_dirty=False
        ):
            raise RuntimeError(f"audio save failed: {item['asset']}")
        imported.append(item["asset"])
    write_credits(data, root)
    unreal.log(
        f"WP-13: imported {len(imported)} sounds; refreshed attribution and credits"
    )
    return imported
