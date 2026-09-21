"""Project + version management.

Projects live under <PROJECTS_ROOT>/<name>/:
    original/<source file>   -- the untouched upload, never modified
    versions/v1.<ext>, v2.<ext>, ...
    manifest.json            -- version history + current-version pointer

Every action call creates a brand-new version file; nothing is ever
edited or overwritten in place.
"""
from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.logger import get_logger
from core.registry import get_action

logger = get_logger(__name__)

PROJECTS_ROOT = Path(os.getenv("PROJECTS_DIR", "projects"))

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


class ProjectError(Exception):
    """Raised for invalid project operations. Message is user-facing."""


def _sanitize_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise ProjectError("Project name cannot be empty.")
    safe = _SAFE_NAME_RE.sub("_", name)
    if not safe:
        raise ProjectError(f"Project name '{name}' has no valid characters.")
    return safe


def _project_dir(name: str) -> Path:
    return PROJECTS_ROOT / _sanitize_name(name)


def _manifest_path(name: str) -> Path:
    return _project_dir(name) / "manifest.json"


def _load_manifest(name: str) -> Dict[str, Any]:
    path = _manifest_path(name)
    if not path.exists():
        raise ProjectError(f"Project '{name}' does not exist.")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _save_manifest(name: str, manifest: Dict[str, Any]) -> None:
    path = _manifest_path(name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)


def _current_relative_path(manifest: Dict[str, Any]) -> str:
    current = manifest["current_version"]
    if current == 0:
        return manifest["original_file"]
    for entry in manifest["versions"]:
        if entry["version"] == current:
            return entry["file"]
    raise ProjectError(f"Version {current} not found in manifest.")


def create_project(name: str, source_path: Union[str, Path]) -> Path:
    """Create a new project from an uploaded video. Copies the source; never touches it."""
    source = Path(source_path)
    if not source.exists():
        raise ProjectError(f"Source file not found: {source}")

    project_dir = _project_dir(name)
    if project_dir.exists():
        raise ProjectError(f"Project '{name}' already exists.")

    original_dir = project_dir / "original"
    versions_dir = project_dir / "versions"
    original_dir.mkdir(parents=True)
    versions_dir.mkdir(parents=True)

    original_file = original_dir / source.name
    shutil.copy2(source, original_file)

    manifest = {
        "name": _sanitize_name(name),
        "original_file": str(original_file.relative_to(project_dir).as_posix()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "versions": [],
        "current_version": 0,
    }
    _save_manifest(name, manifest)
    logger.info("Created project '%s' from %s", name, source)
    return project_dir


def apply_action(
    name: str, action_name: str, params: Optional[Dict[str, Any]] = None
) -> Path:
    """Run a registered action on the current version, producing a new version.

    If the project has been undone past some versions, applying a new
    action discards that redo history (their files are deleted too).
    """
    params = params or {}
    manifest = _load_manifest(name)
    project_dir = _project_dir(name)

    action_func = get_action(action_name)
    current_path = project_dir / _current_relative_path(manifest)

    next_version = manifest["current_version"] + 1
    suffix = current_path.suffix
    versions_dir = project_dir / "versions"
    output_path = versions_dir / f"v{next_version}{suffix}"

    logger.info(
        "Applying action '%s' to project '%s' (v%s -> v%s)",
        action_name,
        name,
        manifest["current_version"],
        next_version,
    )

    action_func(str(current_path), str(output_path), params)

    kept_versions = []
    for entry in manifest["versions"]:
        if entry["version"] < next_version:
            kept_versions.append(entry)
        else:
            orphan = project_dir / entry["file"]
            if orphan.exists():
                orphan.unlink()

    kept_versions.append(
        {
            "version": next_version,
            "file": str(output_path.relative_to(project_dir).as_posix()),
            "action": action_name,
            "params": params,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    manifest["versions"] = kept_versions
    manifest["current_version"] = next_version
    _save_manifest(name, manifest)

    return output_path


def undo(name: str) -> Path:
    """Move the current-version pointer back by one. Files are kept on disk."""
    manifest = _load_manifest(name)
    if manifest["current_version"] == 0:
        raise ProjectError(f"Project '{name}' has no version to undo.")

    manifest["current_version"] -= 1
    _save_manifest(name, manifest)
    logger.info("Undo on project '%s' -> now at v%s", name, manifest["current_version"])
    return get_current(name)


def list_versions(name: str) -> List[Dict[str, Any]]:
    """Return version history, oldest first, each entry flagged with is_current."""
    manifest = _load_manifest(name)
    versions: List[Dict[str, Any]] = [
        {
            "version": 0,
            "label": "original",
            "action": None,
            "params": {},
            "timestamp": manifest["created_at"],
            "is_current": manifest["current_version"] == 0,
        }
    ]
    for entry in manifest["versions"]:
        versions.append(
            {
                "version": entry["version"],
                "label": f"v{entry['version']} ({entry['action']})",
                "action": entry["action"],
                "params": entry["params"],
                "timestamp": entry["timestamp"],
                "is_current": entry["version"] == manifest["current_version"],
            }
        )
    return versions


def get_current(name: str) -> Path:
    manifest = _load_manifest(name)
    project_dir = _project_dir(name)
    return project_dir / _current_relative_path(manifest)


def list_projects() -> List[str]:
    if not PROJECTS_ROOT.exists():
        return []
    return sorted(
        p.name for p in PROJECTS_ROOT.iterdir() if p.is_dir() and (p / "manifest.json").exists()
    )
