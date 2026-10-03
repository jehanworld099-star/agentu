# CLAUDE.md — permanent rules for this project

These rules apply to every future change in `video_editor/`, not just
Phase 0. Read this before adding or modifying anything here.

## Non-negotiables

1. **Never overwrite or modify the original file.** The file in
   `projects/<name>/original/` is untouchable. Every action reads the
   *current* version and writes a brand-new version file
   (`versions/vN.<ext>`); it never edits a file in place.

2. **Always handle videos with no audio track.** Never assume an audio
   stream exists. Check `get_video_info(path)["has_audio"]` before
   doing anything audio-related, and make actions degrade gracefully
   (skip the audio step, don't crash) when it's `False`.

3. **Validate timestamps against duration before using them.** Parse
   user-entered times with `core.timeparse.parse_time_to_seconds` and
   check them with `core.timeparse.validate_against_duration` (or
   equivalent) against the video's actual duration from
   `get_video_info`. Never pass an unvalidated timestamp straight to
   ffmpeg.

4. **Re-encode (libx264 + aac) whenever needed for sync.** Stream
   copy (`-c copy`) is fast but can desync audio/video or produce
   invalid files when cutting on non-keyframes or combining clips with
   different codecs/timebases. Default to re-encoding
   (`-c:v libx264 -c:a aac`) for any action that cuts, trims,
   concatenates, or otherwise changes timing, unless you've verified
   stream copy is safe for that specific operation.

5. **Windows-safe paths, always.** Use `pathlib.Path` everywhere, never
   hand-build paths with string concatenation or forward slashes.
   Project names get sanitized (see `core.project._sanitize_name`)
   before touching the filesystem — don't bypass that.

6. **Readable error messages.** Every user-facing error must say what
   went wrong and, where possible, how to fix it (see
   `core.ffmpeg_utils.FFmpegNotFoundError` for the pattern). Never let
   a raw subprocess traceback or bare exception reach the Streamlit UI
   uncaught.

7. **One action, one file, one test file.** Every new editing feature
   is a new file in `core/actions/`, registered with
   `@register_action("name", params_schema)`, with a matching test in
   `tests/`. Don't put multiple actions in one file, and don't add
   editing logic anywhere outside `core/actions/`.

8. **Don't modify unrelated existing code.** When adding a feature,
   touch only the files that feature needs. Don't refactor, rename, or
   "clean up" other actions/modules as a side effect of an unrelated
   change.

## Conventions

- Actions have the signature
  `run(input_path: str, output_path: str, params: dict) -> str` and
  return the output path.
- Log through `core.logger.get_logger(__name__)`, not `print()`.
- All ffmpeg/ffprobe calls go through `core.ffmpeg_utils.run_ffmpeg()`
  so errors and logging stay consistent.
- New action params must be documented in the `params_schema` passed to
  `@register_action`, since the LLM planner (future phase) reads
  `core.registry.get_actions_schema()` to know what it can call.
