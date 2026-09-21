"""Streamlit UI skeleton for the local video editor.

Phase 0: this only proves the project/version/action pipeline works end
to end, via the 'noop' demo action. No real editing features yet -
those plug into core/actions/ later and show up here automatically via
the registry.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from core import project
from core.actions import noop  # noqa: F401 -- registers the "noop" action
from core.ffmpeg_utils import FFmpegNotFoundError, check_ffmpeg_installed, get_video_info
from core.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="Local Video Editor", layout="wide")


def _ffmpeg_banner() -> None:
    try:
        check_ffmpeg_installed()
    except FFmpegNotFoundError as exc:
        st.error(str(exc))
        st.stop()


def main() -> None:
    st.title("Local Video Editor (Phase 0 skeleton)")
    _ffmpeg_banner()

    with st.sidebar:
        st.header("Projects")
        existing = project.list_projects()
        selected = st.selectbox("Open project", ["<new project>"] + existing)

        if selected == "<new project>":
            new_name = st.text_input("New project name")
            uploaded = st.file_uploader(
                "Upload a video", type=["mp4", "mov", "mkv", "avi", "webm"]
            )
            if st.button("Create project", disabled=not (new_name and uploaded)):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_path = Path(tmp_dir) / uploaded.name
                    tmp_path.write_bytes(uploaded.getbuffer())
                    try:
                        project.create_project(new_name, tmp_path)
                        st.success(f"Created project '{new_name}'.")
                        st.rerun()
                    except project.ProjectError as exc:
                        st.error(str(exc))
            st.stop()

        st.divider()
        st.subheader("Versions")
        versions = project.list_versions(selected)
        current_version_num = next(v["version"] for v in versions if v["is_current"])
        for v in versions:
            marker = "  <- current" if v["is_current"] else ""
            st.write(f"v{v['version']} - {v['label']}{marker}")

        if st.button("Undo", disabled=(current_version_num == 0)):
            try:
                project.undo(selected)
                st.rerun()
            except project.ProjectError as exc:
                st.error(str(exc))

        current_path = project.get_current(selected)
        if current_path.exists():
            st.download_button(
                "Download current version",
                data=current_path.read_bytes(),
                file_name=current_path.name,
            )

    st.subheader(f"Preview: {selected}")
    current_path = project.get_current(selected)
    if current_path.exists():
        st.video(str(current_path))
        try:
            info = get_video_info(current_path)
            st.caption(
                f"{info['width']}x{info['height']} @ {info['fps']:.2f}fps, "
                f"{info['duration']:.1f}s, audio={'yes' if info['has_audio'] else 'no'}"
            )
        except Exception as exc:  # noqa: BLE001 - surface any ffprobe issue to the user
            st.warning(f"Could not read video info: {exc}")
    else:
        st.warning("Current version file is missing.")

    st.divider()
    st.subheader("Test the pipeline")
    st.caption(
        "Runs the demo 'noop' action, which just copies the current version "
        "forward as a new version."
    )
    if st.button("Run noop action"):
        try:
            project.apply_action(selected, "noop", {})
            st.success("Applied 'noop'. New version created.")
            st.rerun()
        except Exception as exc:  # noqa: BLE001 - surface any action failure to the user
            st.error(f"Action failed: {exc}")


if __name__ == "__main__":
    main()
