"""Procedural materials built from Python (no hand-made binary assets).

    import golmok.materials as m; m.build_facade_material(overwrite=True)

M_BasemapFacade reads the vertex data written by golmok-basemap:
    TEXCOORD_0  walls: (distance along wall, height above base) in meters; roofs: ENU x, y in meters
    TEXCOORD_1  (floor height m, category)  category: 0 other, 1 residential, 2 commercial,
                3 office, 4 industrial, 5 public; +100 for roofs
    COLOR_0     per-building wall tint
It draws window bays per floor, shop fronts on commercial ground floors and a concrete roof, so the
LOD1 boxes read as buildings at a distance (D-004).
"""

import unreal

MATERIAL_DIR = "/Game/Golmok/Materials"
FACADE_NAME = "M_BasemapFacade"
TERRAIN_NAME = "M_BasemapTerrain"
ZONE_SCAN_NAME = "M_ZoneScan"  # WP-06 zone scans (virtual-texture sampler)
ZONE_SCAN_NOVT_NAME = "M_ZoneScan_NoVT"  # fallback parent for textures that could not be made VT
DEFAULT_TEXTURE = "/Engine/EngineResources/DefaultTexture.DefaultTexture"

FACADE_HLSL = r"""
float cat = UV1.y;
float fh = max(UV1.x, 2.4);
float3 tintc = Tint.rgb;
if (cat > 99.5)
{
    float2 cell = floor(UV0 * 0.5);
    float n = frac(sin(dot(cell, float2(12.9898, 78.233))) * 43758.5453);
    float3 roof = lerp(float3(0.30, 0.30, 0.29), float3(0.40, 0.39, 0.37), n);
    return float4(roof, 0.9);
}
float u = UV0.x;
float v = UV0.y;
float storey = floor(v / fh);
float fv = frac(v / fh);
float bay = 2.8;
float fu = frac(u / bay);
float win = step(0.22, fu) * step(fu, 0.78) * step(0.32, fv) * step(fv, 0.82);
float commercial = step(1.5, cat) * step(cat, 2.5);
if (commercial > 0.5 && storey < 0.5)
{
    win = step(0.06, fu) * step(fu, 0.94) * step(0.04, fv) * step(fv, 0.86);
}
float office = step(2.5, cat) * step(cat, 3.5);
win = max(win, office * step(0.05, fu) * step(fu, 0.95) * step(0.15, fv) * step(fv, 0.92));
float storeyVar = 0.92 + 0.08 * frac(sin(storey * 17.31 + u * 0.013) * 43758.5453);
float3 wall = tintc * storeyVar;
float3 glass = float3(0.035, 0.045, 0.055);
float3 color = lerp(wall, glass, win);
float rough = lerp(0.85, 0.08, win);
return float4(color, rough);
"""


def _mel():
    return unreal.MaterialEditingLibrary


def _custom_input(name):
    # FCustomInput.InputName is EditAnywhere only, so the struct constructor takes no keywords (UE 5.8).
    ci = unreal.CustomInput()
    ci.set_editor_property("input_name", name)
    return ci


def _new_material(name, overwrite):
    path = f"{MATERIAL_DIR}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        if not overwrite:
            return unreal.EditorAssetLibrary.load_asset(path), False
        unreal.EditorAssetLibrary.delete_asset(path)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    return tools.create_asset(name, MATERIAL_DIR, unreal.Material, unreal.MaterialFactoryNew()), True


def build_facade_material(overwrite=False):
    mat, created = _new_material(FACADE_NAME, overwrite)
    if not created:
        return mat
    mel = _mel()

    uv0 = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -900, -100)
    uv0.set_editor_property("coordinate_index", 0)
    uv1 = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -900, 50)
    uv1.set_editor_property("coordinate_index", 1)
    tint = mel.create_material_expression(mat, unreal.MaterialExpressionVertexColor, -900, 200)

    custom = mel.create_material_expression(mat, unreal.MaterialExpressionCustom, -550, 0)
    custom.set_editor_property("code", FACADE_HLSL)
    custom.set_editor_property("description", "GolmokFacade")
    custom.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    custom.set_editor_property("inputs", [_custom_input(n) for n in ("UV0", "UV1", "Tint")])
    mel.connect_material_expressions(uv0, "", custom, "UV0")
    mel.connect_material_expressions(uv1, "", custom, "UV1")
    mel.connect_material_expressions(tint, "", custom, "Tint")

    rgb = mel.create_material_expression(mat, unreal.MaterialExpressionComponentMask, -250, -60)
    for ch, on in (("r", True), ("g", True), ("b", True), ("a", False)):
        rgb.set_editor_property(ch, on)
    alpha = mel.create_material_expression(mat, unreal.MaterialExpressionComponentMask, -250, 80)
    for ch, on in (("r", False), ("g", False), ("b", False), ("a", True)):
        alpha.set_editor_property(ch, on)
    mel.connect_material_expressions(custom, "", rgb, "")
    mel.connect_material_expressions(custom, "", alpha, "")
    mel.connect_material_property(rgb, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(alpha, "", unreal.MaterialProperty.MP_ROUGHNESS)
    # Basemap buildings are Nanite; without the saved usage flag the material fails outside the editor.
    mat.set_editor_property("used_with_nanite", True)

    mel.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    unreal.log(f"Created {MATERIAL_DIR}/{FACADE_NAME}")
    return mat


def build_terrain_material(overwrite=False):
    """M_BasemapTerrain: orthophoto texture parameter "BaseColor", matte, Nanite-ready.

    Replaces the glTF importer's per-tile instances of the plugin's MI_Default_Opaque, whose parent
    lacks the Nanite usage flag (it cannot be saved from here and would break in packaged builds)."""
    mat, created = _new_material(TERRAIN_NAME, overwrite)
    if not created:
        return mat
    mel = _mel()
    tex = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -500, 0)
    tex.set_editor_property("parameter_name", "BaseColor")
    tex.set_editor_property("texture", unreal.EditorAssetLibrary.load_asset(DEFAULT_TEXTURE))
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -300, 200)
    rough.set_editor_property("r", 0.9)
    spec = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -300, 300)
    spec.set_editor_property("r", 0.3)
    mel.connect_material_property(tex, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(spec, "", unreal.MaterialProperty.MP_SPECULAR)
    mat.set_editor_property("used_with_nanite", True)
    mel.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    unreal.log(f"Created {MATERIAL_DIR}/{TERRAIN_NAME}")
    return mat


def terrain_instance(texture, parent, path):
    """Material instance of M_BasemapTerrain at `path` showing `texture` (created or updated)."""
    mel = _mel()
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        mic = unreal.EditorAssetLibrary.load_asset(path)
    else:
        folder, name = path.rsplit("/", 1)
        mic = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mic, parent)
    mel.set_material_instance_texture_parameter_value(mic, "BaseColor", texture)
    mel.update_material_instance(mic)
    unreal.EditorAssetLibrary.save_loaded_asset(mic)
    return mic


def build_zone_scan_material(default_texture, vt=True, overwrite=False):
    """M_ZoneScan (vt=True) or M_ZoneScan_NoVT: TextureSampleParameter2D "BaseColor" whose default is
    `default_texture` (a virtual-texture sampler needs a VT texture there; zone_import passes the master's own
    T_ZoneScanDefault[_NoVT], never a zone texture, which a zone re-import would force-delete; design D6,
    runbook #10), sampler type SAMPLERTYPE_VIRTUAL_COLOR or SAMPLERTYPE_COLOR, Roughness 0.8, no normal,
    used_with_nanite. An existing material is only loaded unless overwrite=True (zone_import repairs its
    default in place)."""
    name = ZONE_SCAN_NAME if vt else ZONE_SCAN_NOVT_NAME
    mat, created = _new_material(name, overwrite)
    if not created:
        return mat
    mel = _mel()
    tex = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -500, 0)
    tex.set_editor_property("parameter_name", "BaseColor")
    if default_texture is not None:
        tex.set_editor_property("texture", default_texture)
    sampler = "SAMPLERTYPE_VIRTUAL_COLOR" if vt else "SAMPLERTYPE_COLOR"
    if hasattr(unreal, "MaterialSamplerType") and hasattr(unreal.MaterialSamplerType, sampler):
        tex.set_editor_property("sampler_type", getattr(unreal.MaterialSamplerType, sampler))
    else:
        unreal.log_warning(
            f"materials: MaterialSamplerType.{sampler} unavailable; set the BaseColor sampler type of "
            f"{name} by hand (runbook #10)"
        )
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -300, 200)
    rough.set_editor_property("r", 0.8)
    mel.connect_material_property(tex, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mat.set_editor_property("used_with_nanite", True)  # zone chunks are Nanite meshes
    mel.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    unreal.log(f"Created {MATERIAL_DIR}/{name}")
    return mat


def zone_scan_instance(texture, parent, path):
    """Material instance of M_ZoneScan / M_ZoneScan_NoVT at `path` showing `texture` (created or updated)."""
    return terrain_instance(texture, parent, path)
