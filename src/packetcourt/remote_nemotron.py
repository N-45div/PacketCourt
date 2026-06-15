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
    if isinstance(result, dict):
        return result
    if not isinstance(result, str):
        raise TypeError(f"Unexpected Nemotron response type: {type(result).__name__}")
    payload = json.loads(result)
    if not isinstance(payload, dict):
        raise TypeError(f"Unexpected Nemotron JSON type: {type(payload).__name__}")
    return payload
