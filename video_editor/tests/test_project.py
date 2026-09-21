import json

import pytest

from core import project
from core.actions import noop  # noqa: F401 -- registers "noop"


@pytest.fixture
def sample_video(tmp_path):
    video = tmp_path / "source.mp4"
    video.write_bytes(b"fake video bytes")
    return video


@pytest.fixture(autouse=True)
def isolated_projects_root(tmp_path, monkeypatch):
    monkeypatch.setattr(project, "PROJECTS_ROOT", tmp_path / "projects")
    yield


def test_create_project(sample_video):
    project_dir = project.create_project("demo", sample_video)
    assert project_dir.exists()
    manifest = json.loads((project_dir / "manifest.json").read_text())
    assert manifest["current_version"] == 0
    assert (project_dir / manifest["original_file"]).exists()


def test_create_project_duplicate_raises(sample_video):
    project.create_project("demo", sample_video)
    with pytest.raises(project.ProjectError):
        project.create_project("demo", sample_video)


def test_create_project_missing_source_raises(tmp_path):
    with pytest.raises(project.ProjectError):
        project.create_project("demo", tmp_path / "does-not-exist.mp4")


def test_apply_action_creates_new_version(sample_video):
    project.create_project("demo", sample_video)
    output = project.apply_action("demo", "noop", {})
    assert output.exists()
    versions = project.list_versions("demo")
    assert len(versions) == 2
    assert versions[-1]["is_current"] is True


def test_undo_moves_pointer_back(sample_video):
    project.create_project("demo", sample_video)
    project.apply_action("demo", "noop", {})
    reverted = project.undo("demo")
    assert reverted == project.get_current("demo")
    versions = project.list_versions("demo")
    assert versions[0]["is_current"] is True


def test_undo_with_nothing_to_undo_raises(sample_video):
    project.create_project("demo", sample_video)
    with pytest.raises(project.ProjectError):
        project.undo("demo")


def test_apply_action_after_undo_discards_redo_history(sample_video):
    project.create_project("demo", sample_video)
    project.apply_action("demo", "noop", {})
    v1_path = project.get_current("demo")
    project.undo("demo")
    project.apply_action("demo", "noop", {})

    assert not v1_path.exists()
    versions = project.list_versions("demo")
    assert len(versions) == 2


def test_list_projects(sample_video):
    assert project.list_projects() == []
    project.create_project("demo", sample_video)
    assert project.list_projects() == ["demo"]


def test_original_file_never_modified(sample_video):
    project.create_project("demo", sample_video)
    original_bytes = sample_video.read_bytes()
    project.apply_action("demo", "noop", {})
    project.apply_action("demo", "noop", {})

    project_dir = project._project_dir("demo")
    manifest = json.loads((project_dir / "manifest.json").read_text())
    original_path = project_dir / manifest["original_file"]
    assert original_path.read_bytes() == original_bytes
