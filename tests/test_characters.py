from pathlib import Path

from debugpet.services.characters import load_character_manifest


def test_bundled_character_manifest_is_valid() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = load_character_manifest(root / "characters" / "miaomiao.json", root)
    assert manifest.character_id == "miaomiao"
    assert manifest.asset_directory.name == "miaomiao-all-actions"
