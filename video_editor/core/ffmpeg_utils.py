"""Thin, Windows-friendly wrapper around ffmpeg / ffprobe.

Every future action should call `run_ffmpeg()` instead of invoking
subprocess directly, so errors are consistently logged and reported in a
readable way instead of a raw traceback.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Union

from core.logger import get_logger

logger = get_logger(__name__)

WINDOWS_INSTALL_INSTRUCTIONS = """
FFmpeg was not found on your PATH.

To install it on Windows:
  1. Download a build from https://www.gyan.dev/ffmpeg/builds/ (grab the
     "release full" 7z/zip build).
  2. Extract it somewhere permanent, e.g. C:\\ffmpeg
  3. Add C:\\ffmpeg\\bin to your PATH:
       - Press Win, search "Environment Variables", open
         "Edit the system environment variables"
       - Click "Environment Variables...", select "Path" under
         "User variables", click "Edit" -> "New", add C:\\ffmpeg\\bin
       - Click OK on every dialog, then open a NEW terminal window
  4. Verify with:  ffmpeg -version   and   ffprobe -version

Alternative (if you have winget):
    winget install --id=Gyan.FFmpeg -e

Alternative (if you have Chocolatey):
    choco install ffmpeg
""".strip()


class FFmpegNotFoundError(RuntimeError):
    """Raised when ffmpeg/ffprobe cannot be found on PATH."""


class FFmpegError(RuntimeError):
    """Raised when an ffmpeg/ffprobe invocation fails; message is user-readable."""


def check_ffmpeg_installed() -> None:
    missing = [exe for exe in ("ffmpeg", "ffprobe") if shutil.which(exe) is None]
    if missing:
        raise FFmpegNotFoundError(
            f"Missing required tool(s) on PATH: {', '.join(missing)}.\n\n"
            f"{WINDOWS_INSTALL_INSTRUCTIONS}"
        )


def run_ffmpeg(
    args: List[str], *, description: str = "ffmpeg command"
) -> subprocess.CompletedProcess:
    """Run an ffmpeg/ffprobe command, raising FFmpegError with readable output on failure."""
    check_ffmpeg_installed()
    logger.info("Running %s: %s", description, " ".join(str(a) for a in args))
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise FFmpegError(f"Failed to launch {args[0]!r}: {exc}") from exc

    if result.returncode != 0:
        logger.error(
            "%s failed (exit %s): %s", description, result.returncode, result.stderr
        )
        raise FFmpegError(
            f"{description} failed (exit code {result.returncode}).\n"
            f"Command: {' '.join(str(a) for a in args)}\n"
            f"--- ffmpeg stderr ---\n{result.stderr.strip()}"
        )

    logger.info("%s completed successfully", description)
    return result


def get_video_info(path: Union[str, Path]) -> Dict[str, Any]:
    """Return duration (s), fps, width, height, has_audio for a video file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {path}")

    check_ffmpeg_installed()

    args = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = run_ffmpeg(args, description=f"ffprobe on {path.name}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise FFmpegError(f"Could not parse ffprobe output for {path}: {exc}") from exc

    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if video_stream is None:
        raise FFmpegError(f"No video stream found in {path}")

    fmt = data.get("format", {})
    duration = float(fmt.get("duration") or video_stream.get("duration") or 0.0)

    fps = 0.0
    rate = video_stream.get("r_frame_rate", "0/1")
    try:
        num, den = rate.split("/")
        den = float(den)
        fps = float(num) / den if den else 0.0
    except (ValueError, ZeroDivisionError):
        fps = 0.0

    return {
        "duration": duration,
        "fps": fps,
        "width": int(video_stream.get("width") or 0),
        "height": int(video_stream.get("height") or 0),
        "has_audio": audio_stream is not None,
    }
