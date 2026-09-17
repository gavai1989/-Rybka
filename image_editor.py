from __future__ import annotations

import base64
from pathlib import Path

from typing import TYPE_CHECKING

from fish import FISH_SPECIES

if TYPE_CHECKING:
    from openai import OpenAI

MODEL = "gpt-image-1.5"
QUALITY = "low"
SIZE = "1024x1024"


def build_prompt(fish: str) -> str:
    return f"""Edit the supplied fishing photograph, preserving the original people and scene.

Add one realistic caught {fish} to the most natural person in the photo, choosing the person who is most plausibly the angler or the person who could naturally hold the catch. If there are multiple people, do not rearrange them.

The edit must look like an ordinary real phone photograph, not an AI-generated image. Preserve faces and identity, body proportions, clothing, poses, background, camera perspective, lighting, colors, and overall composition. Do not change unrelated parts of the photograph.

Place the fish naturally in the person's hands or in the position where a freshly caught fish would realistically be held. Match scale, perspective, occlusion, contact, shadows, reflections, lighting direction, texture, moisture, and image grain to the original photograph. The fish should be a believable normal-sized catch, not an exaggerated trophy.

Do not add text, captions, extra people, extra animals, fishing equipment, or scenery. Only make the minimum changes required to add the fish.

Target fish: {fish}.
Available MVP species: {', '.join(FISH_SPECIES)}.
"""


def edit_fishing_photo(client: OpenAI, image_path: str | Path, fish: str) -> bytes:
    """Edit an input photo and return the generated image bytes."""
    if fish not in FISH_SPECIES:
        raise ValueError(f"Unsupported fish: {fish}")

    from openai import OpenAI

    if not isinstance(client, OpenAI):
        raise TypeError("client must be an OpenAI client")

    with open(image_path, "rb") as image_file:
        result = client.images.edit(
            model=MODEL,
            image=image_file,
            prompt=build_prompt(fish),
            quality=QUALITY,
            size=SIZE,
        )

    if not result.data or not getattr(result.data[0], "b64_json", None):
        raise RuntimeError("OpenAI did not return an image")

    return base64.b64decode(result.data[0].b64_json)
