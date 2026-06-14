from __future__ import annotations

import json
import os
from functools import lru_cache


def is_configured() -> bool:
    return bool(os.getenv("PACKETCOURT_NEMOTRON_SPACE"))


@lru_cache(maxsize=1)
def _client():
    from gradio_client import Client

    try:
        return Client(os.environ["PACKETCOURT_NEMOTRON_SPACE"])
    except Exception:
        try:
            return Client(os.environ["PACKETCOURT_NEMOTRON_SPACE"], hf_token=os.getenv("HF_TOKEN"))
        except TypeError:
            return Client(os.environ["PACKETCOURT_NEMOTRON_SPACE"], token=os.getenv("HF_TOKEN"))


def review(snapshot: dict) -> dict:
    result = _client().predict(json.dumps(snapshot), api_name="/predict")
    return json.loads(result)
