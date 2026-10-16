import argparse
import shutil
import sys
from pathlib import Path
from datetime import datetime
from scene_prompts import SCENES
from video_generator import generate_all_scenes, OUTPUT_DIR
from video_merger import merge_videos


def main():
    parser = argparse.ArgumentParser(
        description="Generate and merge Veo hospital scenes with native audio."
    )

    parser.add_argument(
        "--existing-scenes-only",
        action="store_true",
        help="Merge existing scenes without calling Veo.",
    )

    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate every scene using Veo.",
    )

    args = parser.parse_args()

    if args.existing_scenes_only and args.regenerate:
        parser.error(
            "--existing-scenes-only and --regenerate cannot be used together."
        )

    if not shutil.which("ffmpeg"):
        sys.exit(
            "ERROR: ffmpeg was not found on PATH. "
            "Install FFmpeg or add its bin folder to PATH."
        )

    if not shutil.which("ffprobe"):
        sys.exit(
            "ERROR: ffprobe was not found on PATH. "
            "Add the FFmpeg bin folder to PATH."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.existing_scenes_only:
        scene_paths = [
            OUTPUT_DIR / f"{scene['name']}.mp4"
            for scene in SCENES
        ]

        missing = [str(path) for path in scene_paths if not path.exists()]

        if missing:
            sys.exit(
                "These scenes are missing:\n"
                + "\n".join(missing)
                + "\nGenerate them first, or check your output filenames."
            )

    else:
        scene_paths = generate_all_scenes(
            SCENES,
            force=True,
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_output_path = OUTPUT_DIR / f"final_video_{timestamp}.mp4"

    final_path = merge_videos(
    scene_paths,
    output_path=final_output_path,
    )

    print("\nPipeline completed.")
    print(f"Final video: {final_path}")


if __name__ == "__main__":
    main()