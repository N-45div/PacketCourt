from __future__ import annotations

import os
from functools import lru_cache


def is_configured() -> bool:
    return bool(os.getenv("PACKETCOURT_VISION_SPACE"))


@lru_cache(maxsize=1)
def _client():
    from gradio_client import Client

    try:
        return Client(
            os.environ["PACKETCOURT_VISION_SPACE"],
            hf_token=os.getenv("HF_TOKEN"),
        )
    except TypeError:
        return Client(
            os.environ["PACKETCOURT_VISION_SPACE"],
            token=os.getenv("HF_TOKEN"),
        )


def extract_remote(image_path: str, side: str) -> str:
    from gradio_client import handle_file

    result = _client().predict(handle_file(image_path), side, api_name="/predict")
    if result.startswith("PACKETCOURT_VISION_ERROR:"):
        raise RuntimeError(result.splitlines()[0])
    return result.strip()
