"""tools/scripts/check_repo.py on a synthetic repository in a temp dir."""

import configparser
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_repo.py"
_spec = importlib.util.spec_from_file_location("check_repo", SCRIPT)
check_repo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_repo)

UE_INI = """\
[/Script/WindowsTargetPlatform.WindowsTargetSettings]
DefaultGraphicsRHI=DefaultGraphicsRHI_DX12
-D3D12TargetedShaderFormats=PCD3D_SM5
+D3D12TargetedShaderFormats=PCD3D_SM6
+D3D12TargetedShaderFormats=PCD3D_SM6
; comment
.Paths=%GAMEDIR%Content
!ClearArray=ClearArray

[/Script/Golmok.GolmokCharacter]
CharacterMeshPath=/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple
"""


def write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture
def repo(tmp_path):
    write(
        tmp_path, "unreal/Golmok/Golmok.uproject", json.dumps({"FileVersion": 3, "EngineAssociation": "5.8"})
    )
    write(tmp_path, "unreal/Golmok/Config/DefaultEngine.ini", UE_INI)
    write(tmp_path, "unreal/Golmok/Config/Golmok/zones/z.json", '{"id": "z"}')
    write(
        tmp_path,
        ".gitattributes",
        "*.uasset filter=lfs diff=lfs merge=lfs -text lockable\n*.umap filter=lfs -text\n",
    )
    write(tmp_path, "README.md", "[docs](docs/README.md) [plan](docs/plan/STATUS.md#top)\n")
    write(tmp_path, "CLAUDE.md", "[road](/docs/ROADMAP.md)\n")
    write(tmp_path, "docs/README.md", "[up](../README.md) [site](https://example.com/x.md) [a](#sec)\n")
    write(tmp_path, "docs/ROADMAP.md", "# R\n")
    write(tmp_path, "docs/plan/STATUS.md", "[road](../ROADMAP.md 'title') ![img](<../ROADMAP.md>)\n")
    return tmp_path


def test_clean_repo_passes(repo, capsys):
    assert check_repo.run(repo) == []
    assert check_repo.main(["--root", str(repo)]) == 0
    assert "OK" in capsys.readouterr().out


def test_ue_ini_duplicates_and_prefixes():
    cp = check_repo.parse_ue_ini(UE_INI)
    sec = cp["/Script/WindowsTargetPlatform.WindowsTargetSettings"]
    assert sec["+D3D12TargetedShaderFormats"] == "PCD3D_SM6"
    assert sec["-D3D12TargetedShaderFormats"] == "PCD3D_SM5"
    assert sec[".Paths"] == "%GAMEDIR%Content"  # no interpolation
    assert "DefaultGraphicsRHI" in sec  # key case kept


def test_ini_without_section_fails(repo):
    write(repo, "unreal/Golmok/Config/DefaultGame.ini", "Key=Value\n")
    with pytest.raises(configparser.Error):
        check_repo.parse_ue_ini("Key=Value\n")
    errors = check_repo.check_ini(repo)
    assert len(errors) == 1 and "DefaultGame.ini" in errors[0]


def test_broken_links_reported_with_line(repo):
    write(repo, "docs/plan/WP.md", "ok [s](STATUS.md)\n\n[bad](../missing.md) [bad2](nope/x.md#a)\n")
    errors = check_repo.check_links(repo)
    assert errors == [
        "docs/plan/WP.md:3: 깨진 링크 ../missing.md",
        "docs/plan/WP.md:3: 깨진 링크 nope/x.md#a",
    ]


def test_links_in_code_ignored_and_ref_links_checked(repo):
    text = "`[x](missing.md)`\n```\n[y](missing.md)\n```\n[ref]: gone.md\n[ok]: README.md\n"
    write(repo, "docs/code.md", text)
    assert check_repo.check_links(repo) == ["docs/code.md:5: 깨진 링크 gone.md"]


def test_percent_encoded_link(repo):
    write(repo, "docs/한글 문서.md", "x\n")
    write(repo, "docs/enc.md", "[k](%ED%95%9C%EA%B8%80%20%EB%AC%B8%EC%84%9C.md)\n")
    assert check_repo.check_links(repo) == []


def test_uproject_engine_mismatch(repo):
    write(repo, "unreal/Golmok/Golmok.uproject", json.dumps({"EngineAssociation": "5.7"}))
    assert "EngineAssociation" in check_repo.check_uproject(repo)[0]
    write(repo, "unreal/Golmok/Golmok.uproject", "{not json")
    assert "JSON" in check_repo.check_uproject(repo)[0]


def test_bad_json_and_missing_lfs(repo, capsys):
    write(repo, "docs/data/x.json", "{,}")
    write(repo, ".gitattributes", "*.uasset filter=lfs -text\n# *.umap filter=lfs\n")
    errors = check_repo.run(repo)
    assert any("docs/data/x.json" in e for e in errors)
    assert any("*.umap" in e for e in errors)
    assert check_repo.main(["--root", str(repo)]) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out and "2개 실패" in out
