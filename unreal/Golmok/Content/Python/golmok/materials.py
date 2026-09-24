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
    custom.set_editor_property("inputs", [
        unreal.CustomInput(input_name="UV0"),
        unreal.CustomInput(input_name="UV1"),
        unreal.CustomInput(input_name="Tint"),
    ])
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

    mel.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    unreal.log(f"Created {MATERIAL_DIR}/{FACADE_NAME}")
    return mat
