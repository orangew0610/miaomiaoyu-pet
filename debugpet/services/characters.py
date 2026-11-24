from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CharacterManifest:
    character_id: str
    display_name: str
    asset_directory: Path
    prompt_file: Path
    actions: dict[str, str | list[str]]


def _inside(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    if resolved_candidate != resolved_root and resolved_root not in resolved_candidate.parents:
        raise ValueError(f"character path escapes project root: {candidate}")
    return resolved_candidate


def load_character_manifest(path: Path, project_root: Path) -> CharacterManifest:
    values = json.loads(path.read_text(encoding="utf-8"))
    if values.get("schema_version") != 1:
        raise ValueError("unsupported character manifest schema")
    actions = values.get("actions")
    if not isinstance(actions, dict) or "idle" not in actions:
        raise ValueError("character manifest requires an idle action")
    asset_directory = _inside(project_root, project_root / values["asset_directory"])
    prompt_file = _inside(project_root, project_root / values["prompt_file"])
    if not asset_directory.is_dir():
        raise ValueError(f"asset directory does not exist: {asset_directory}")
    if not prompt_file.is_file():
        raise ValueError(f"prompt file does not exist: {prompt_file}")
    for filenames in actions.values():
        names = filenames if isinstance(filenames, list) else [filenames]
        for name in names:
            asset = _inside(asset_directory, asset_directory / name)
            if not asset.is_file():
                raise ValueError(f"character asset does not exist: {asset}")
    return CharacterManifest(
        character_id=str(values["id"]),
        display_name=str(values["display_name"]),
        asset_directory=asset_directory,
        prompt_file=prompt_file,
        actions=actions,
    )
