
import json
import subprocess
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"

# Default output when no custom filename is provided.
FINAL_VIDEO = OUTPUT_DIR / "final_hospital_video.mp4"


def run_command(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )


def get_stream_info(video_path: Path) -> dict:
    """Read video and audio stream information with FFprobe."""
    result = run_command([
        "ffprobe",
        "-v", "error",
        "-show_entries", "stream=codec_type",
        "-of", "json",
        str(video_path),
    ])

    return json.loads(result.stdout)


def verify_scene(video_path: Path) -> None:
    """Ensure the file exists and contains both video and audio."""
    if not video_path.exists() or video_path.stat().st_size == 0:
        raise FileNotFoundError(
            f"Video missing or empty: {video_path}"
        )

    info = get_stream_info(video_path)

    stream_types = {
        stream.get("codec_type")
        for stream in info.get("streams", [])
    }

    if "video" not in stream_types:
        raise RuntimeError(
            f"No video stream in {video_path.name}"
        )

    if "audio" not in stream_types:
        raise RuntimeError(
            f"No audio stream in {video_path.name}. "
            "Regenerate this scene with native audio enabled."
        )


def merge_videos(
    scene_paths: list[Path],
    output_path: Path | None = None,
) -> Path:
    """
    Merge scene videos while preserving audio.

    If output_path is provided, save to that location without
    replacing any previously generated final video.
    """
    if not scene_paths:
        raise ValueError("No scene videos were provided.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Use the provided filename or the original default.
    if output_path is None:
        output_path = FINAL_VIDEO
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    scene_paths = [Path(path).resolve() for path in scene_paths]
    output_path = output_path.resolve()

    print("\nChecking video and audio streams...")

    for path in scene_paths:
        verify_scene(path)
        print(f"OK: {path.name} contains video and audio.")

    concat_file = OUTPUT_DIR / "concat_list.txt"

    # Keep the temporary file beside the final output.
    temporary_output = output_path.with_name(
        f"{output_path.stem}.tmp{output_path.suffix}"
    )

    try:
        # FFmpeg concat-list paths use forward slashes.
        with concat_file.open("w", encoding="utf-8") as file:
            for path in scene_paths:
                path_string = path.as_posix()

                if "'" in path_string:
                    raise ValueError(
                        "A scene path contains a single quote, "
                        "which this concat-list format cannot safely handle."
                    )

                file.write(f"file '{path_string}'\n")

        command = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-map", "0:v:0",
            "-map", "0:a:0",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(temporary_output),
        ]

        print("\nMerging scenes and preserving audio...")
        run_command(command)

        if (
            not temporary_output.exists()
            or temporary_output.stat().st_size == 0
        ):
            raise RuntimeError(
                "FFmpeg produced an empty output file."
            )

        verify_scene(temporary_output)

        # Refuse to overwrite an existing final video.
        if output_path.exists():
            raise FileExistsError(
                f"Output already exists; refusing to overwrite: {output_path}"
            )

        temporary_output.rename(output_path)

        print(f"\nFinal video saved to: {output_path}")
        return output_path

    except subprocess.CalledProcessError as exc:
        print("FFmpeg failed:")
        print(exc.stderr or exc.stdout or str(exc))
        raise

    finally:
        # Remove intermediate files, not the final videos.
        if concat_file.exists():
            concat_file.unlink()

        if temporary_output.exists():
            temporary_output.unlink()


if __name__ == "__main__":
    print("Video merger module loaded successfully.")
