# Local Video Editor (Phase 0: foundation)

A local, zero-budget, CapCut-style video editor for Windows, built in
Python on top of FFmpeg. This phase only builds the **skeleton**: project
storage, versioning, an action registry, and a Streamlit UI. No real
editing feature (trim, cut, captions, etc.) exists yet — those will be
added later as individual files under `core/actions/`.

## Why this shape

- **Originals are sacred.** Every project keeps the uploaded file in
  `original/` and never writes to it. Every action produces a new
  numbered version (`v1`, `v2`, ...) instead of editing in place, so
  Undo is just moving a pointer back.
- **One action, one file.** Every editing feature is a single function
  registered in `core/registry.py` with the signature
  `run(input_path, output_path, params) -> output_path`. The registry
  can also emit a JSON schema of every action, which a future LLM
  planner will use to decide what to call.
- **FFmpeg via a thin, readable wrapper.** `core/ffmpeg_utils.py`
  checks FFmpeg/ffprobe are on PATH (with Windows install
  instructions if not), and wraps every subprocess call so failures
  come back as one readable error instead of a raw traceback.

## Folder structure

```
video_editor/
  app.py                 Streamlit UI
  core/
    registry.py           Action registration + schema export
    project.py             Project + version management
    ffmpeg_utils.py         ffmpeg/ffprobe subprocess wrapper
    timeparse.py             Human time string -> seconds
    logger.py                 Shared logging setup
    actions/
      noop.py                  Demo action: copies the file unchanged
  tests/                  pytest unit tests
  projects/               Created at runtime; one folder per project (git-ignored)
  requirements.txt
  .env.example
  CLAUDE.md               Permanent rules for all future work on this project
```

## Install (Windows, PowerShell or cmd)

```
cd video_editor
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Install FFmpeg if you haven't already (see the error message the app
shows if it's missing, or `core/ffmpeg_utils.py` for the same
instructions): download from https://www.gyan.dev/ffmpeg/builds/,
extract to `C:\ffmpeg`, add `C:\ffmpeg\bin` to your PATH, open a new
terminal, and verify with `ffmpeg -version` and `ffprobe -version`.

## Run

```
streamlit run app.py
```

Then in the browser: create a project by uploading a video, use "Run
noop action" to prove the pipeline (it creates a new version that's an
exact copy), check the version list and Undo in the sidebar, and try
"Download current version".

## Test checklist

Automated:

```
pytest
```

Manual, once FFmpeg is installed:

1. Upload a short `.mp4` and create a project — the original appears
   under `projects/<name>/original/`.
2. The preview player shows the video and its duration/fps/resolution/
   audio caption.
3. Click "Run noop action" — a new version (`v1`) appears in the
   sidebar and becomes current.
4. Click "Run noop action" again — `v2` appears.
5. Click "Undo" — pointer moves back to `v1`; the preview updates.
6. Click "Undo" again — back to the original (`v0`); the Undo button
   becomes disabled.
7. Click "Download current version" — the file downloads correctly.
8. Upload a video with no audio track — the caption shows `audio=no`
   and nothing crashes.
9. Rename `ffmpeg.exe`/remove it from PATH temporarily — the app shows
   the readable install-instructions error instead of crashing.
