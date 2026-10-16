import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

PROJECT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_DIR / "assets"
OUTPUT_DIR = PROJECT_DIR / "output"

MODEL_NAME = "veo-3.1-generate-preview"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise RuntimeError(
        "Missing GEMINI_API_KEY in your .env file."
    )

client = genai.Client(api_key=api_key)


def load_reference_image(filename: str):
    """Load a PNG/JPG reference image for Veo."""
    path = ASSETS_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Reference image not found: {path}"
        )

    suffix = path.suffix.lower()
    mime_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix)

    if not mime_type:
        raise ValueError(
            f"Unsupported reference image format: {path}"
        )

    return types.Image(
        image_bytes=path.read_bytes(),
        mime_type=mime_type,
    )



def make_reference_images(filenames: list[str]):
    """Build Veo reference images for the current scene only."""
    references = []

    for filename in filenames:
        image = load_reference_image(filename)

        references.append(
            types.VideoGenerationReferenceImage(
                image=image,
                reference_type="asset",
            )
        )

    return references



def generate_scene(scene: dict, force: bool = False) -> Path:
    """Generate one audiovisual Veo scene or reuse an existing file."""
    scene_name = scene["name"]
    output_path = OUTPUT_DIR / f"{scene_name}.mp4"

    if output_path.exists() and output_path.stat().st_size > 0 and not force:
        print(f"Reusing existing scene: {output_path.name}")
        return output_path

    print(f"\nGenerating {scene_name} using {MODEL_NAME}...")

    references = make_reference_images(
    scene.get("refs", ["Female_Doc.png", "Patient1.png", "area.png"])
        )
    operation = client.models.generate_videos(
        model=MODEL_NAME,
        prompt=scene["prompt"],
        config=types.GenerateVideosConfig(
            reference_images=references,
            aspect_ratio="16:9",
            number_of_videos=1,
        ),
    )

    while not operation.done:
        print(f"Waiting for {scene_name}...")
        time.sleep(10)
        operation = client.operations.get(operation)

    if not operation.response:
        raise RuntimeError(
            f"Veo returned no response for {scene_name}."
        )

    generated_videos = getattr(
        operation.response,
        "generated_videos",
        None,
    )

    if not generated_videos:
        raise RuntimeError(
            f"No generated video returned for {scene_name}."
        )

    generated_video = generated_videos[0]

    client.files.download(
        file=generated_video.video,
        destination=str(output_path),
    )

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(
            f"Video download failed for {scene_name}."
        )

    print(f"Saved: {output_path}")
    return output_path


def generate_all_scenes(
    scenes: list,
    force: bool = False,
) -> list[Path]:
    """Generate or reuse scenes in the supplied order."""
    paths = []

    for scene in scenes:
        paths.append(generate_scene(scene, force=force))

    return paths